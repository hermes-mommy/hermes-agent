"""Iteration Budget — thread-safe turn / token / cost limiting for loops.

In-memory budget tracker for LLM-driven autonomous loops. Each loop is
allocated an :class:`IterationBudget` with hard caps on turns, tokens,
and USD cost. Subagent budgets are derived from a parent and share
accounting: every subagent ``consume_turn`` also debits the parent, so
exhausting the parent propagates to every child.

Pattern reference: Hermes Agent ``IterationBudget`` (parent 90 / subagent
50 defaults). State is kept in memory only; no Redis or PostgreSQL
coupling — see :mod:`guinevere.loops.cost` for the persistent per-loop cost
record on Redis DB5.

All mutating operations acquire an :class:`asyncio.Lock`; inspection
methods are synchronous and lock-free because Python attribute reads
are atomic within a single event loop.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()

# Parent (full autonomous loop) defaults.
_DEFAULT_PARENT_MAX_TURNS: int = 90
_DEFAULT_PARENT_MAX_TOKENS: int = 500_000
_DEFAULT_PARENT_MAX_COST_USD: float = 5.0

# Subagent (delegated task) defaults.
_DEFAULT_SUBAGENT_MAX_TURNS: int = 50
_DEFAULT_SUBAGENT_MAX_TOKENS: int = 250_000
_DEFAULT_SUBAGENT_MAX_COST_USD: float = 2.5


class BudgetExhaustedError(Exception):
    """Raised when an :class:`IterationBudget` limit is reached.

    Carries the ``resource`` that was exhausted (one of ``"turns"``,
    ``"tokens"``, ``"cost_usd"``) and the ``used`` / ``limit`` values
    at the point of failure. Subclass-friendly: log scrapers and
    runbooks can pattern-match on the ``resource`` field.
    """

    def __init__(
        self,
        message: str,
        resource: str,
        used: float,
        limit: float,
    ) -> None:
        super().__init__(message)
        self.resource: str = resource
        self.used: float = used
        self.limit: float = limit

    def __repr__(self) -> str:
        return (
            f"BudgetExhaustedError(resource={self.resource!r}, "
            f"used={self.used}, limit={self.limit})"
        )


@dataclass(frozen=True)
class BudgetSnapshot:
    """Immutable snapshot of an :class:`IterationBudget`'s current state.

    Produced by :meth:`IterationBudget.check_budget`. Frozen so it can
    be safely passed across async boundaries and into audit logs.
    """

    max_turns: int
    remaining_turns: int
    max_tokens: int
    remaining_tokens: int
    max_cost_usd: float
    remaining_cost_usd: float
    turns_used: int
    tokens_used: int
    cost_used_usd: float


class IterationBudget:
    """Thread-safe turn / token / cost budget for one loop or subagent.

    Limits are enforced atomically: ``consume_turn`` validates all three
    limits under a single lock acquisition and only mutates counters
    when every check passes. A partial debit is therefore impossible.

    Subagent budgets can be created via :meth:`create_subagent_budget`;
    a subagent's ``consume_turn`` first validates its own limits, then
    debits its parent. If the parent rejects, the child counters are
    left untouched and a :class:`BudgetExhaustedError` propagates.
    """

    def __init__(
        self,
        max_turns: int = _DEFAULT_PARENT_MAX_TURNS,
        max_tokens: int = _DEFAULT_PARENT_MAX_TOKENS,
        max_cost_usd: float = _DEFAULT_PARENT_MAX_COST_USD,
        *,
        parent: IterationBudget | None = None,
    ) -> None:
        if max_turns < 0:
            raise ValueError(f"max_turns must be >= 0, got {max_turns}")
        if max_tokens < 0:
            raise ValueError(f"max_tokens must be >= 0, got {max_tokens}")
        if max_cost_usd < 0.0:
            raise ValueError(
                f"max_cost_usd must be >= 0.0, got {max_cost_usd}"
            )

        self._max_turns: int = max_turns
        self._max_tokens: int = max_tokens
        self._max_cost_usd: float = max_cost_usd

        self._turns_used: int = 0
        self._tokens_used: int = 0
        self._cost_used_usd: float = 0.0

        self._lock: asyncio.Lock = asyncio.Lock()
        self._parent: IterationBudget | None = parent

        logger.info(
            "iteration_budget.initialized",
            max_turns=max_turns,
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            has_parent=parent is not None,
        )

    @classmethod
    def from_subagent(cls) -> IterationBudget:
        """Return a free-standing :class:`IterationBudget` sized for a subagent.

        The returned budget is not bound to a parent; use
        :meth:`create_subagent_budget` on an existing parent to derive
        a child that shares accounting with the parent.
        """
        return cls(
            max_turns=_DEFAULT_SUBAGENT_MAX_TURNS,
            max_tokens=_DEFAULT_SUBAGENT_MAX_TOKENS,
            max_cost_usd=_DEFAULT_SUBAGENT_MAX_COST_USD,
        )

    async def consume_turn(self, tokens: int, cost_usd: float) -> None:
        """Atomically debit one turn plus the given token and cost delta.

        Acquires the instance lock, validates all three local limits,
        and (if a parent is set) recursively debits the parent under
        the parent's own lock. State is only mutated when both the
        local and parent checks pass.

        Args:
            tokens: Tokens consumed by this turn (must be ``>= 0``).
            cost_usd: USD cost of this turn (must be ``>= 0.0``).

        Raises:
            ValueError: If ``tokens`` or ``cost_usd`` is negative.
            BudgetExhaustedError: If any local or parent limit would
                be exceeded; no state is mutated.
        """
        if tokens < 0:
            raise ValueError(f"tokens must be >= 0, got {tokens}")
        if cost_usd < 0.0:
            raise ValueError(f"cost_usd must be >= 0.0, got {cost_usd}")

        async with self._lock:
            # Validate local limits first so we never debit a parent
            # whose child is already exhausted.
            if self._turns_used + 1 > self._max_turns:
                self._log_exhaustion(
                    resource="turns",
                    used=float(self._turns_used),
                    limit=float(self._max_turns),
                )
                raise BudgetExhaustedError(
                    f"Turn limit reached: used {self._turns_used} of "
                    f"{self._max_turns}",
                    resource="turns",
                    used=float(self._turns_used),
                    limit=float(self._max_turns),
                )

            if self._tokens_used + tokens > self._max_tokens:
                self._log_exhaustion(
                    resource="tokens",
                    used=float(self._tokens_used),
                    limit=float(self._max_tokens),
                    attempted_delta=tokens,
                )
                raise BudgetExhaustedError(
                    f"Token limit reached: used {self._tokens_used} of "
                    f"{self._max_tokens} (attempted +{tokens})",
                    resource="tokens",
                    used=float(self._tokens_used),
                    limit=float(self._max_tokens),
                )

            if self._cost_used_usd + cost_usd > self._max_cost_usd:
                self._log_exhaustion(
                    resource="cost_usd",
                    used=self._cost_used_usd,
                    limit=self._max_cost_usd,
                    attempted_delta=cost_usd,
                )
                raise BudgetExhaustedError(
                    f"Cost limit reached: used {self._cost_used_usd:.6f} "
                    f"of {self._max_cost_usd:.6f} "
                    f"(attempted +{cost_usd:.6f})",
                    resource="cost_usd",
                    used=self._cost_used_usd,
                    limit=self._max_cost_usd,
                )

            # Local check passed. Debit parent if attached — parent
            # uses its own lock; we hold our lock throughout so our
            # counters stay consistent with the parent's view.
            if self._parent is not None:
                try:
                    await self._parent.consume_turn(tokens, cost_usd)
                except BudgetExhaustedError as parent_err:
                    logger.warning(
                        "iteration_budget.parent_exhausted",
                        resource=parent_err.resource,
                        used=parent_err.used,
                        limit=parent_err.limit,
                    )
                    raise

            # All checks passed — apply the local debit.
            self._turns_used += 1
            self._tokens_used += tokens
            self._cost_used_usd += cost_usd

            logger.debug(
                "iteration_budget.consumed",
                turns_used=self._turns_used,
                tokens_used=self._tokens_used,
                cost_used_usd=self._cost_used_usd,
                remaining_turns=self._max_turns - self._turns_used,
                remaining_tokens=self._max_tokens - self._tokens_used,
                remaining_cost_usd=self._max_cost_usd - self._cost_used_usd,
            )

    def check_budget(self) -> BudgetSnapshot:
        """Return a frozen :class:`BudgetSnapshot` of the current state.

        Read-only and lock-free; safe to call from any context.
        """
        return BudgetSnapshot(
            max_turns=self._max_turns,
            remaining_turns=self.remaining_turns(),
            max_tokens=self._max_tokens,
            remaining_tokens=self.remaining_tokens(),
            max_cost_usd=self._max_cost_usd,
            remaining_cost_usd=self.remaining_cost_usd(),
            turns_used=self._turns_used,
            tokens_used=self._tokens_used,
            cost_used_usd=self._cost_used_usd,
        )

    def exhausted(self) -> bool:
        """Return ``True`` if any limit has been reached or exceeded."""
        return (
            self._turns_used >= self._max_turns
            or self._tokens_used >= self._max_tokens
            or self._cost_used_usd >= self._max_cost_usd
        )

    def remaining_turns(self) -> int:
        """Return remaining turns (clamped at 0)."""
        return max(0, self._max_turns - self._turns_used)

    def remaining_tokens(self) -> int:
        """Return remaining tokens (clamped at 0)."""
        return max(0, self._max_tokens - self._tokens_used)

    def remaining_cost_usd(self) -> float:
        """Return remaining cost in USD (clamped at 0.0)."""
        return max(0.0, self._max_cost_usd - self._cost_used_usd)

    def create_subagent_budget(
        self,
        max_turns: int = _DEFAULT_SUBAGENT_MAX_TURNS,
        max_tokens: int = _DEFAULT_SUBAGENT_MAX_TOKENS,
        max_cost_usd: float = _DEFAULT_SUBAGENT_MAX_COST_USD,
    ) -> IterationBudget:
        """Derive a child budget that shares accounting with this parent.

        Every :meth:`consume_turn` on the child also debits the parent
        (under the parent's own lock). If the parent is exhausted, the
        child's ``consume_turn`` raises :class:`BudgetExhaustedError`
        without mutating the child's counters.
        """
        return IterationBudget(
            max_turns=max_turns,
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            parent=self,
        )

    def _log_exhaustion(
        self,
        *,
        resource: str,
        used: float,
        limit: float,
        attempted_delta: float | None = None,
    ) -> None:
        """Emit a structured warning when a local limit is about to be hit."""
        fields: dict[str, float | str] = {
            "resource": resource,
            "used": used,
            "limit": limit,
        }
        if attempted_delta is not None:
            fields["attempted_delta"] = attempted_delta
        logger.warning("iteration_budget.exhausted", **fields)

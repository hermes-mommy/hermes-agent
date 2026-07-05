"""Iteration Budget — thread-safe turn / token / cost limiting for loops.

Ported from ``guinevere/loops/budget.py`` — API preserved for M10 (W14).
In-memory budget tracker for LLM-driven autonomous loops.
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
    at the point of failure.
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
    """Immutable snapshot of an :class:`IterationBudget`'s current state."""

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
    when every check passes.
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
        """Return a free-standing :class:`IterationBudget` sized for a subagent."""
        return cls(
            max_turns=_DEFAULT_SUBAGENT_MAX_TURNS,
            max_tokens=_DEFAULT_SUBAGENT_MAX_TOKENS,
            max_cost_usd=_DEFAULT_SUBAGENT_MAX_COST_USD,
        )

    async def consume_turn(self, tokens: int, cost_usd: float) -> None:
        """Atomically debit one turn plus the given token and cost delta."""
        if tokens < 0:
            raise ValueError(f"tokens must be >= 0, got {tokens}")
        if cost_usd < 0.0:
            raise ValueError(f"cost_usd must be >= 0.0, got {cost_usd}")

        async with self._lock:
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
        """Return a frozen :class:`BudgetSnapshot` of the current state."""
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
        """Derive a child budget that shares accounting with this parent."""
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

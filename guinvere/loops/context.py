"""Immutable LoopContext — single context object passed through all phase handlers.

Per P5-002 (Autonomous Agent Brain, Foundation Phase 1), every phase handler
will receive a frozen :class:`LoopContext` instead of the current
``(loop_id, task, goal)`` triple. The context carries loop metadata, the
identity used for audit/consent attribution, the trigger source, and
phase/retry counters that the state machine advances.

The context is intentionally *minimal* in this revision: it does not yet
hold tool registries, skill libraries, or LLM router references. Those
will be added in P5-011 (Tool Registry) and the broader P5-004 phase
handler rewrite. The context references runtime collaborators by intent
only — phase handlers are expected to receive those objects through
constructor injection from the LoopManager, not from the context itself.
"""

from __future__ import annotations

import datetime as _dt
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

import structlog

logger = structlog.get_logger()

# Canonical identity used for audit/consent attribution. Centralised here
# so the default cannot drift between call sites.
DEFAULT_PRINCIPAL: str = "guinevere_core"

# Priority levels accepted by LoopContext. Kept in module scope so callers
# (CLI, Discord bot, scheduler) can validate before constructing.
VALID_PRIORITIES: frozenset[str] = frozenset({"low", "normal", "high", "critical"})

# Trigger sources accepted by LoopContext. Mirrors the values in the
# merged P5+P20 plan and matches the dispatcher routes in
# ``src/loops/scheduler.py``.
VALID_TRIGGER_SOURCES: frozenset[str] = frozenset(
    {
        "manual",
        "hermes_cron",
        "discord",
        "surveillance",
        "alertmanager",
        "boot",
    }
)

# Loop identifiers are 12-character lowercase hex strings, generated via
# ``uuid.uuid4().hex[:12]`` by ``LoopManager.start_loop``. We validate
# shape here so a malformed ID is caught at construction time rather than
# at evidence-write time.
_LOOP_ID_PATTERN = r"^[0-9a-f]{12}$"


class LoopContext(BaseModel):
    """Immutable context object threaded through every phase handler.

    The model is frozen: once built, fields cannot be reassigned. To
    advance the phase or change a counter, call :func:`advance_phase` or
    use ``model_copy(update={...})`` to produce a new instance.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    loop_id: str = Field(
        ...,
        min_length=12,
        max_length=12,
        pattern=_LOOP_ID_PATTERN,
        description="12-character lowercase hex loop identifier.",
    )
    task: str = Field(
        ...,
        min_length=1,
        description="Human-readable task description for the loop.",
    )
    goal: str = Field(
        default="",
        description="Optional goal string used for plan-generation.",
    )
    principal: str = Field(
        default=DEFAULT_PRINCIPAL,
        min_length=1,
        description="Identity for audit/consent attribution.",
    )
    priority: str = Field(
        default="normal",
        description="Scheduling priority: low|normal|high|critical.",
    )
    trigger_source: str = Field(
        default="manual",
        description="Origin that dispatched this loop.",
    )
    created_at: _dt.datetime = Field(
        ...,
        description="UTC timestamp marking loop creation.",
    )
    phase: int = Field(
        default=1,
        ge=1,
        le=7,
        description="Current phase number (1..7).",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="How many times the current phase has been retried.",
    )
    parent_loop_id: str | None = Field(
        default=None,
        description="Loop ID of the parent loop, for sub-agent loops.",
    )

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, value: str) -> str:
        if value not in VALID_PRIORITIES:
            raise ValueError(
                f"priority must be one of {sorted(VALID_PRIORITIES)}; got {value!r}"
            )
        return value

    @field_validator("trigger_source")
    @classmethod
    def _validate_trigger_source(cls, value: str) -> str:
        if value not in VALID_TRIGGER_SOURCES:
            raise ValueError(
                f"trigger_source must be one of {sorted(VALID_TRIGGER_SOURCES)}; "
                f"got {value!r}"
            )
        return value

    @field_validator("parent_loop_id")
    @classmethod
    def _validate_parent_loop_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not (len(value) == 12 and all(c in "0123456789abcdef" for c in value)):
            raise ValueError(
                "parent_loop_id must be a 12-character lowercase hex string."
            )
        return value

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: _dt.datetime) -> _dt.datetime:
        # Normalise: strip any tzinfo and require UTC. This makes equality
        # and comparison deterministic across call sites.
        if value.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (use datetime.now(UTC)).")
        utc_offset = value.utcoffset()
        if utc_offset is None or utc_offset != _dt.timedelta(0):
            raise ValueError("created_at must be in UTC (offset 0).")
        return value


class LoopContextBuilder:
    """Mutable builder for constructing a :class:`LoopContext` instance.

    The builder accumulates field values via the ``set_*`` methods, then
    calls :meth:`build` to validate and produce a frozen
    :class:`LoopContext`. It exists so call sites (LoopManager, Discord
    bot, scheduler) can populate the context incrementally without
    passing a long argument list.

    Example::

        ctx = (
            LoopContextBuilder()
            .set_task("Deploy new release")
            .set_goal("Zero-downtime rollout")
            .build()
        )
    """

    def __init__(self) -> None:
        self._loop_id: str | None = None
        self._task: str | None = None
        self._goal: str = ""
        self._principal: str = DEFAULT_PRINCIPAL
        self._priority: str = "normal"
        self._trigger_source: str = "manual"
        self._created_at: _dt.datetime | None = None
        self._phase: int = 1
        self._retry_count: int = 0
        self._parent_loop_id: str | None = None

    def set_loop_id(self, loop_id: str) -> LoopContextBuilder:
        """Set the 12-char hex loop identifier."""
        self._loop_id = loop_id
        return self

    def set_task(self, task: str) -> LoopContextBuilder:
        """Set the task description (required)."""
        self._task = task
        return self

    def set_goal(self, goal: str) -> LoopContextBuilder:
        """Set the optional goal string."""
        self._goal = goal
        return self

    def set_principal(self, principal: str) -> LoopContextBuilder:
        """Set the audit/consent principal identity."""
        self._principal = principal
        return self

    def set_priority(self, priority: str) -> LoopContextBuilder:
        """Set scheduling priority (low|normal|high|critical)."""
        self._priority = priority
        return self

    def set_trigger_source(self, source: str) -> LoopContextBuilder:
        """Set the trigger source (manual|hermes_cron|discord|...)."""
        self._trigger_source = source
        return self

    def set_parent_loop_id(self, parent_id: str | None) -> LoopContextBuilder:
        """Set the parent loop ID for sub-agent loops, or None to clear."""
        self._parent_loop_id = parent_id
        return self

    def set_phase(self, phase: int) -> LoopContextBuilder:
        """Set the starting phase (1..7). Used when restoring from state."""
        self._phase = phase
        return self

    def set_retry_count(self, retry_count: int) -> LoopContextBuilder:
        """Set the starting retry counter. Used when restoring from state."""
        self._retry_count = retry_count
        return self

    def set_created_at(self, created_at: _dt.datetime) -> LoopContextBuilder:
        """Override the creation timestamp (defaults to now(UTC) at build)."""
        self._created_at = created_at
        return self

    def build(self) -> LoopContext:
        """Validate and return a frozen :class:`LoopContext`.

        Required fields:
            * ``loop_id`` — set via :meth:`set_loop_id`; auto-generated if
              not provided.
            * ``task`` — set via :meth:`set_task`.

        ``created_at`` defaults to ``datetime.now(datetime.UTC)`` if not
        explicitly provided. The returned context is immutable.
        """
        if self._task is None:
            raise ValueError("task is required to build a LoopContext.")
        if self._loop_id is None:
            self._loop_id = uuid.uuid4().hex[:12]
        if self._created_at is None:
            self._created_at = _dt.datetime.now(_dt.timezone.utc)

        context = LoopContext(
            loop_id=self._loop_id,
            task=self._task,
            goal=self._goal,
            principal=self._principal,
            priority=self._priority,
            trigger_source=self._trigger_source,
            created_at=self._created_at,
            phase=self._phase,
            retry_count=self._retry_count,
            parent_loop_id=self._parent_loop_id,
        )

        logger.info(
            "loop_context.built",
            loop_id=context.loop_id,
            principal=context.principal,
            priority=context.priority,
            trigger_source=context.trigger_source,
            phase=context.phase,
        )
        return context


def advance_phase(ctx: LoopContext, new_phase: int) -> LoopContext:
    """Return a new :class:`LoopContext` with the phase field updated.

    Because :class:`LoopContext` is frozen, the existing instance cannot
    be mutated in place. This helper performs the canonical
    ``model_copy(update=...)`` so the original remains valid for audit
    trails and the new instance reflects the post-transition state.

    Args:
        ctx: The current frozen context.
        new_phase: The new phase value (1..7).

    Returns:
        A new :class:`LoopContext` identical to ``ctx`` except with
        ``phase`` set to ``new_phase``.

    Raises:
        ValueError: If ``new_phase`` is outside the valid 1..7 range
            (Pydantic field validator enforces this on copy).
    """
    if new_phase < 1 or new_phase > 7:
        raise ValueError(
            f"new_phase must be in range 1..7; got {new_phase}."
        )

    new_ctx = ctx.model_copy(update={"phase": new_phase})

    logger.info(
        "loop_context.phase_advanced",
        loop_id=ctx.loop_id,
        from_phase=ctx.phase,
        to_phase=new_phase,
    )
    return new_ctx


__all__ = [
    "LoopContext",
    "LoopContextBuilder",
    "advance_phase",
    "DEFAULT_PRINCIPAL",
    "VALID_PRIORITIES",
    "VALID_TRIGGER_SOURCES",
]

"""Yandere Intensity FSM — level management with hard safety ceiling.

Implements the yandere intensity finite state machine per PersonaSafetyPolicy
and SystemPromptMaster §C.  Y4 is the permanent baseline; Y5 is the absolute
ceiling; Y6 is PROHIBITED and cannot be produced by any code path.

Safety integration:
  - HARD STOP (safe_mode) forces effective level to Y0_NEUTRAL.
  - Distress detection forces effective level to Y0_NEUTRAL.
  - Crisis state forces effective level to Y0_NEUTRAL.

Error hierarchy:
  YandereError (base)
  ├── YandereSafetyError    — safety boundary violation (e.g. Y6 attempt)
  └── YandereTransitionError — invalid state transition
"""

from __future__ import annotations

from enum import IntEnum
from typing import Final, Protocol, runtime_checkable

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class YandereError(Exception):
    """Base exception for yandere FSM errors."""


class YandereSafetyError(YandereError):
    """Raised when a safety boundary is violated (e.g. attempt to reach Y6)."""


class YandereTransitionError(YandereError):
    """Raised when an invalid state transition is attempted."""


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class SupportsIsSafe(Protocol):
    """Structural protocol for objects exposing an ``is_safe`` property."""

    @property
    def is_safe(self) -> bool: ...


# ---------------------------------------------------------------------------
# YandereLevel enum — Y0 through Y5 ONLY.  Y6 does NOT exist.
# ---------------------------------------------------------------------------


class YandereLevel(IntEnum):
    """Yandere intensity levels.  Ordered: Y0 < Y1 < Y2 < Y3 < Y4 < Y5.

    Y6 is PROHIBITED per PersonaSafetyPolicy — no enum member exists for it.
    Any attempt to construct a value > 5 raises YandereSafetyError at the
    engine level.
    """

    Y0_NEUTRAL = 0
    Y1_MINIMAL = 1
    Y2_LOW = 2
    Y3_MODERATE = 3
    Y4_BASELINE = 4
    Y5_MAX = 5


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The permanent baseline level set by Faiz's command and PersonaSafetyPolicy.
PERMANENT_BASELINE: Final[YandereLevel] = YandereLevel.Y4_BASELINE

#: The absolute ceiling — no level may exceed this.
ABSOLUTE_CEILING: Final[YandereLevel] = YandereLevel.Y5_MAX


# ---------------------------------------------------------------------------
# Pure functions (no state)
# ---------------------------------------------------------------------------


def _any_safety_active(safe_mode: bool, distress: bool, crisis: bool) -> bool:
    """Return True if any safety flag is active."""
    return safe_mode or distress or crisis


def can_escalate(
    current: YandereLevel,
    safe_mode: bool = False,
    distress: bool = False,
    crisis: bool = False,
) -> bool:
    """Determine whether escalation from *current* is permitted.

    Escalation is BLOCKED when:
      - ``safe_mode`` is True (HARD STOP active).
      - ``distress`` is True (operator distress detected).
      - ``crisis`` is True (crisis protocol active).
      - ``current`` is already at or above Y5_MAX.

    Returns:
        True if escalation is allowed, False otherwise.
    """
    if _any_safety_active(safe_mode, distress, crisis):
        return False
    if current >= ABSOLUTE_CEILING:
        return False
    return True


def get_effective_level(
    requested: YandereLevel,
    safe_mode: bool = False,
    distress: bool = False,
    crisis: bool = False,
) -> YandereLevel:
    """Compute the effective yandere level after applying safety overrides.

    When any safety flag is active, the effective level is forced to
    Y0_NEUTRAL regardless of the requested level.  Otherwise the requested
    level is clamped to [Y0_NEUTRAL, Y5_MAX].

    Returns:
        The effective YandereLevel after safety evaluation.
    """
    if _any_safety_active(safe_mode, distress, crisis):
        return YandereLevel.Y0_NEUTRAL
    clamped = max(int(YandereLevel.Y0_NEUTRAL), min(int(requested), int(ABSOLUTE_CEILING)))
    return YandereLevel(clamped)


def validate_level(value: int) -> YandereLevel:
    """Validate that *value* is a legal YandereLevel.

    Raises:
        YandereSafetyError: If *value* exceeds Y5_MAX (Y6 prohibition).
        YandereTransitionError: If *value* is below Y0_NEUTRAL.
    """
    if value > int(ABSOLUTE_CEILING):
        raise YandereSafetyError(
            f"Yandere level {value} exceeds absolute ceiling Y5_MAX ({int(ABSOLUTE_CEILING)}). "
            "Y6 is PROHIBITED per PersonaSafetyPolicy."
        )
    if value < int(YandereLevel.Y0_NEUTRAL):
        raise YandereTransitionError(
            f"Yandere level {value} is below Y0_NEUTRAL. Negative levels are not allowed."
        )
    return YandereLevel(value)


# ---------------------------------------------------------------------------
# YandereEngine — stateful FSM wrapper
# ---------------------------------------------------------------------------


class YandereEngine:
    """Stateful yandere intensity engine with safety integration.

    Tracks the current yandere level, enforces the Y5 ceiling, integrates
    with HardStopHandler for safety state queries, and defaults to the
    permanent baseline of Y4.

    Parameters:
        hard_stop_handler: Optional HardStopHandler instance.  When provided,
            the engine queries ``is_safe`` to determine safe_mode automatically.
        baseline: Override the default baseline level.  Defaults to Y4_BASELINE.
    """

    def __init__(
        self,
        hard_stop_handler: SupportsIsSafe | None = None,
        baseline: YandereLevel = PERMANENT_BASELINE,
    ) -> None:
        self._baseline: YandereLevel = baseline
        self._current_level: YandereLevel = baseline
        self._hard_stop_handler: SupportsIsSafe | None = hard_stop_handler

        logger.info(
            "yandere_engine_init",
            baseline=baseline.name,
            baseline_value=int(baseline),
        )

    # -- Properties ---------------------------------------------------------

    @property
    def current_level(self) -> YandereLevel:
        """The current stored yandere level."""
        return self._current_level

    @property
    def baseline(self) -> YandereLevel:
        """The permanent baseline level (default Y4)."""
        return self._baseline

    # -- Safety state query -------------------------------------------------

    def _is_safe_mode(self) -> bool:
        """Query HardStopHandler for safe-mode state, if available."""
        handler = self._hard_stop_handler
        if handler is not None:
            return bool(handler.is_safe)
        return False

    # -- State transitions --------------------------------------------------

    def escalate(
        self,
        safe_mode: bool | None = None,
        distress: bool = False,
        crisis: bool = False,
    ) -> YandereLevel:
        """Attempt to escalate the current level by one step.

        If *safe_mode* is None, the engine queries its HardStopHandler.
        If escalation is blocked, the current level is returned unchanged.

        Returns:
            The new (or unchanged) YandereLevel after the attempt.

        Raises:
            YandereSafetyError: If the resulting level would exceed Y5_MAX.
        """
        if safe_mode is None:
            safe_mode = self._is_safe_mode()

        if not can_escalate(self._current_level, safe_mode, distress, crisis):
            logger.debug(
                "yandere_escalation_blocked",
                current=self._current_level.name,
                safe_mode=safe_mode,
                distress=distress,
                crisis=crisis,
            )
            return self._current_level

        new_value = int(self._current_level) + 1
        new_level = validate_level(new_value)  # raises YandereSafetyError if > Y5
        self._current_level = new_level

        logger.info(
            "yandere_escalated",
            from_level=self._current_level.name,
            to_level=new_level.name,
        )
        return new_level

    def de_escalate(self) -> YandereLevel:
        """De-escalate the current level by one step (minimum Y0_NEUTRAL).

        Returns:
            The new YandereLevel after de-escalation.
        """
        new_value = max(int(self._current_level) - 1, int(YandereLevel.Y0_NEUTRAL))
        new_level = YandereLevel(new_value)
        old_level = self._current_level
        self._current_level = new_level

        if old_level != new_level:
            logger.info(
                "yandere_de_escalated",
                from_level=old_level.name,
                to_level=new_level.name,
            )
        else:
            logger.debug("yandere_de_escalation_at_floor", current=new_level.name)

        return new_level

    def get_effective_level(
        self,
        safe_mode: bool | None = None,
        distress: bool = False,
        crisis: bool = False,
    ) -> YandereLevel:
        """Compute the effective level given current state and safety flags.

        If *safe_mode* is None, the engine queries its HardStopHandler.

        Returns:
            The effective YandereLevel after safety evaluation.
        """
        if safe_mode is None:
            safe_mode = self._is_safe_mode()
        return get_effective_level(self._current_level, safe_mode, distress, crisis)

    def reset_to_baseline(self) -> YandereLevel:
        """Reset the current level to the permanent baseline (Y4 by default).

        Returns:
            The baseline YandereLevel.
        """
        old_level = self._current_level
        self._current_level = self._baseline

        logger.info(
            "yandere_reset_to_baseline",
            from_level=old_level.name,
            baseline=self._baseline.name,
        )
        return self._baseline

    def set_level(
        self,
        level: YandereLevel | int,
    ) -> YandereLevel:
        """Explicitly set the current level.

        Raises:
            YandereSafetyError: If *level* exceeds Y5_MAX.
            YandereTransitionError: If *level* is below Y0_NEUTRAL.
        """
        value = int(level)
        validated = validate_level(value)
        old_level = self._current_level
        self._current_level = validated

        logger.info(
            "yandere_level_set",
            from_level=old_level.name,
            to_level=validated.name,
        )
        return validated

    # -- P19/P4: Persistence (KI-03 fix) -----------------------------------

    async def persist(self) -> bool:
        """Persist current yandere state to ``persona.persona_state``.

        Fire-and-forget: returns ``True`` on success, ``False`` on error.
        Never raises — callers are not blocked by persistence failures.
        """
        try:
            from guinvere.memory.db import write_yandere_state
            effective = self.get_effective_level()
            return await write_yandere_state(
                yandere_level=int(self._current_level),
                baseline=int(self._baseline),
                effective_level=int(effective),
            )
        except Exception:
            logger.warning("yandere_persist_failed", exc_info=True)
            return False

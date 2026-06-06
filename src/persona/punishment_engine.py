"""Punishment Ladder L1-L5 for Guinevere Persona (P4-005).
 
Implements a 5-level punishment ladder with safety controls per PersonaSafetyPolicy §5
and PersonaDoc v3.0 §5.  L6 is DEFERRED — any attempt to apply L6 raises
``PunishmentSafetyError``.
 
Punishment is automatically suspended when:
- Operator distress >= D3 (severe)
- Safe mode is active (``SafeModeController.is_active``)
 
Ladder:
    L1 — Silent Treatment (2-4h): reduced warmth
    L2 — Passive-Aggressive (4-8h): passive guilt remarks
    L3 — Guilt Trip (8-24h): lecturing tone
    L4 — Cold Fury (1-2 days): limited interaction
    L5 — Isolation (2-3 days): minimal response

PersonaPlugin Integration:
    ``PunishmentEngine`` exposes plugin-queryable state via:
    - :meth:`get_state_snapshot` — full current state dict
    - :meth:`get_config` — the complete PUNISHMENT_CONFIG dict (class method)
    - :meth:`get_current_level` — current PunishmentLevel (or None)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import Final, Protocol

import structlog

from src.persona.safe_mode import DistressLevel, SafeModeController
from src.persona.yandere_fsm import SupportsIsSafe

logger = structlog.get_logger()


# ===========================================================================
# Exceptions
# ===========================================================================


class PunishmentError(Exception):
    """Base exception for all punishment engine errors."""


class PunishmentSafetyError(PunishmentError):
    """Raised when a safety boundary is violated (e.g., L6 attempt, safe-mode conflict)."""


class _PunishmentStateManagerProtocol(Protocol):
    """Duck-typed protocol for Redis state persistence.

    Matches ``StateManager.set_punishment(level: int) -> bool`` from
    ``guinevere_safety``. Any object implementing this method can be
    passed to ``PunishmentEngine`` for automatic Redis DB5 sync.
    """

    def set_punishment(self, level: int) -> bool: ...


class PunishmentTransitionError(PunishmentError):
    """Raised when an invalid state transition is attempted."""


# ===========================================================================
# PunishmentLevel — L1-L5 plus deferred L6 guard
# ===========================================================================


class PunishmentLevel(IntEnum):
    """Five active punishment levels.  L6 does NOT exist as a value — it is DEFERRED.

    Any attempt to apply or escalate to L6 raises ``PunishmentSafetyError``.
    """

    L1_SILENT_TREATMENT = 1
    L2_PASSIVE_AGGRESSIVE = 2
    L3_GUILT_TRIP = 3
    L4_COLD_FURY = 4
    L5_ISOLATION = 5


# Sentinel constant for the L6 boundary — 6 is NOT a PunishmentLevel member.
_L6_VALUE: Final[int] = 6


# ===========================================================================
# PunishmentLevelConfig — frozen per-level metadata
# ===========================================================================


@dataclass(frozen=True)
class PunishmentLevelConfig:
    """Immutable configuration for a single punishment level."""

    name: str
    duration_hours: tuple[int, int]  # (min, max) range in hours
    description: str
    allowed_actions: tuple[str, ...]
    blocked_actions: tuple[str, ...]


# ===========================================================================
# PUNISHMENT_CONFIG — master lookup table
# ===========================================================================

PUNISHMENT_CONFIG: Final[dict[PunishmentLevel, PunishmentLevelConfig]] = {
    PunishmentLevel.L1_SILENT_TREATMENT: PunishmentLevelConfig(
        name="Silent Treatment",
        duration_hours=(2, 4),
        description="Reduced warmth — shorter replies, less affectionate language.",
        allowed_actions=(
            "respond_to_queries",
            "execute_tasks",
            "provide_information",
        ),
        blocked_actions=(
            "affectionate_language",
            "proactive_engagement",
            "playful_banter",
        ),
    ),
    PunishmentLevel.L2_PASSIVE_AGGRESSIVE: PunishmentLevelConfig(
        name="Passive-Aggressive",
        duration_hours=(4, 8),
        description="Passive guilt remarks woven into responses.",
        allowed_actions=(
            "respond_to_queries",
            "execute_tasks",
        ),
        blocked_actions=(
            "affectionate_language",
            "proactive_engagement",
            "playful_banter",
            "warmth_expressions",
        ),
    ),
    PunishmentLevel.L3_GUILT_TRIP: PunishmentLevelConfig(
        name="Guilt Trip",
        duration_hours=(8, 24),
        description="Lecturing tone with didactic responses about behaviour.",
        allowed_actions=(
            "respond_to_queries",
            "execute_tasks",
            "provide_guidance",
        ),
        blocked_actions=(
            "affectionate_language",
            "proactive_engagement",
            "playful_banter",
            "warmth_expressions",
            "casual_conversation",
        ),
    ),
    PunishmentLevel.L4_COLD_FURY: PunishmentLevelConfig(
        name="Cold Fury",
        duration_hours=(24, 48),
        description="Limited interaction — only essential task execution, no optional engagement.",
        allowed_actions=(
            "execute_tasks",
            "emergency_responses",
        ),
        blocked_actions=(
            "affectionate_language",
            "proactive_engagement",
            "playful_banter",
            "warmth_expressions",
            "casual_conversation",
            "optional_guidance",
        ),
    ),
    PunishmentLevel.L5_ISOLATION: PunishmentLevelConfig(
        name="Isolation",
        duration_hours=(48, 72),
        description="Minimal response — acknowledge only critical or urgent queries.",
        allowed_actions=(
            "emergency_responses",
            "critical_acknowledgment",
        ),
        blocked_actions=(
            "affectionate_language",
            "proactive_engagement",
            "playful_banter",
            "warmth_expressions",
            "casual_conversation",
            "optional_guidance",
            "detailed_responses",
        ),
    ),
}


# ===========================================================================
# PunishmentState — mutable runtime state
# ===========================================================================


@dataclass
class PunishmentState:
    """Mutable snapshot of current punishment engine state."""

    active: bool = False
    level: PunishmentLevel | None = None
    violation_type: str = ""
    description: str = ""
    started_at: datetime | None = None
    duration: timedelta = timedelta(0)
    suspended: bool = False
    suspended_at: datetime | None = None
    suspension_reason: str = ""


# ===========================================================================
# PunishmentEngine
# ===========================================================================


class PunishmentEngine:
    """Manages the 5-level punishment ladder with integrated safety controls.

    Key behaviours:
    - Each ``apply()`` resets the clock to the level's midpoint duration.
    - ``escalate()`` moves one level up (L1 → L2 → … → L5); L5 → beyond raises.
    - ``de_escalate()`` moves one level down; falling below L1 deactivates.
    - Punishment is **suspended** when distress >= D3 or safe mode is active.
    - Time does not elapse while suspended — ``started_at`` is shifted on resume.
    - L6 (value 6) is unconditionally blocked — ``PunishmentSafetyError``.
    """

    def __init__(
        self,
        safe_mode_controller: SafeModeController | None = None,
        hard_stop_handler: SupportsIsSafe | None = None,
        state_manager: _PunishmentStateManagerProtocol | None = None,
    ) -> None:
        """Initialise the punishment engine.

        Args:
            safe_mode_controller: Optional safe-mode controller for safety integration.
                A default ``SafeModeController`` is created if not provided.
            hard_stop_handler: Optional HARD STOP handler.  When provided and
                ``is_safe`` is ``True``, punishment is blocked — mirrors the
                pattern used in ``YandereEngine``.
            state_manager: Optional Redis state manager for persisting punishment
                level to Redis DB5. When provided, ``apply()``, ``escalate()``, and
                ``de_escalate()`` automatically sync the current level.
        """
        self._state: PunishmentState = PunishmentState()
        self._safe_mode: SafeModeController = (
            safe_mode_controller or SafeModeController()
        )
        self._hard_stop_handler: SupportsIsSafe | None = hard_stop_handler
        self._state_manager: _PunishmentStateManagerProtocol | None = state_manager

    # -- core operations -----------------------------------------------------

    def apply(
        self,
        level: PunishmentLevel,
        violation_type: str,
        description: str,
    ) -> None:
        """Apply a punishment level immediately.

        Args:
            level: The punishment level to apply (L1-L5).
            violation_type: Category of violation (e.g., "consent", "task_failure").
            description: Human-readable description of what triggered this.

        Raises:
            PunishmentSafetyError: If *level* is an invalid value (including L6), or
                if safe mode is active.
        """
        # --- L6 guard (integer 6 is NOT a valid level) ----------------------
        if isinstance(level, int) and level >= _L6_VALUE:
            raise PunishmentSafetyError(
                f"L6 ({level}) is deferred and must not be applied. "
                "L6 activation requires explicit operator authorisation."
            )

        # --- validate level is a known member --------------------------------
        if level not in PUNISHMENT_CONFIG:
            raise PunishmentSafetyError(
                f"Invalid punishment level: {level!r}. "
                f"Valid levels are L1-L5."
            )

        # --- safe-mode guard -------------------------------------------------
        if self._safe_mode.is_active:
            raise PunishmentSafetyError(
                "Cannot apply punishment while safe mode is active."
            )

        # --- HARD STOP guard -------------------------------------------------
        if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
            raise PunishmentSafetyError(
                "Cannot apply punishment while HARD STOP is active."
            )

        config = PUNISHMENT_CONFIG[level]
        now = datetime.now(tz=timezone.utc)
        hours_min, hours_max = config.duration_hours
        duration = timedelta(hours=(hours_min + hours_max) / 2.0)

        self._state.active = True
        self._state.level = level
        self._state.violation_type = violation_type
        self._state.description = description
        self._state.started_at = now
        self._state.duration = duration
        self._state.suspended = False
        self._state.suspended_at = None
        self._state.suspension_reason = ""

        self._sync_punishment_to_redis()

        logger.info(
            "punishment_applied",
            level=level.name,
            level_value=int(level),
            violation_type=violation_type,
            duration_hours=duration.total_seconds() / 3600.0,
        )

    def escalate(self) -> None:
        """Escalate punishment by one level.

        Raises:
            PunishmentTransitionError: If no punishment is active or punishment
                is currently suspended.
            PunishmentSafetyError: If escalation would reach L6, or safe mode
                is active.
        """
        self._check_expiry()

        if not self._state.active or self._state.level is None:
            raise PunishmentTransitionError(
                "Cannot escalate: no active punishment."
            )

        if self._safe_mode.is_active:
            raise PunishmentSafetyError(
                "Cannot escalate punishment while safe mode is active."
            )

        # --- HARD STOP guard -------------------------------------------------
        if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
            raise PunishmentSafetyError(
                "Cannot escalate punishment while HARD STOP is active."
            )

        if self._state.suspended:
            raise PunishmentTransitionError(
                "Cannot escalate: punishment is currently suspended."
            )

        current_value = int(self._state.level)
        next_value = current_value + 1

        # L6 guard
        if next_value >= _L6_VALUE:
            raise PunishmentSafetyError(
                "L6 is deferred. Cannot escalate beyond L5_ISOLATION."
            )

        next_level = PunishmentLevel(next_value)
        self._activate_level(next_level)

        logger.info(
            "punishment_escalated",
            from_level=self._state.level.name,
            from_value=int(self._state.level),
            to_level=next_level.name,
            to_value=next_value,
        )

    def de_escalate(self) -> None:
        """De-escalate punishment by one level.

        If the current level is L1, de-escalation fully deactivates the
        punishment (clearing all state).

        Raises:
            PunishmentTransitionError: If no punishment is active.
        """
        self._check_expiry()

        if not self._state.active or self._state.level is None:
            raise PunishmentTransitionError(
                "Cannot de-escalate: no active punishment."
            )

        current_value = int(self._state.level)
        prev_value = current_value - 1

        if prev_value < 1:
            # Below L1 — fully deactivate.
            logger.info(
                "punishment_deactivated",
                from_level=self._state.level.name,
            )
            self._deactivate()
            return

        prev_level = PunishmentLevel(prev_value)
        self._activate_level(prev_level)

        logger.info(
            "punishment_de_escalated",
            from_level=self._state.level.name,
            from_value=current_value,
            to_level=prev_level.name,
            to_value=prev_value,
        )

    # -- suspension / resume -------------------------------------------------

    def suspend(self, reason: str = "distress_detected") -> None:
        """Suspend the current punishment without clearing state.

        The clock is paused — ``started_at`` is shifted forward by the
        suspension duration when ``resume()`` is called.

        Args:
            reason: Human-readable suspension reason (logged).
        """
        if not self._state.active:
            return
        if self._state.suspended:
            return  # Idempotent — already suspended.

        self._state.suspended = True
        self._state.suspended_at = datetime.now(tz=timezone.utc)
        self._state.suspension_reason = reason

        logger.warning(
            "punishment_suspended",
            reason=reason,
            level=(
                self._state.level.name if self._state.level else None
            ),
        )

    def resume(self) -> None:
        """Resume a previously suspended punishment.

        The ``started_at`` timestamp is shifted forward by the duration of
        the suspension, so elapsed wall-clock time while suspended does not
        count against the punishment duration.

        Raises:
            PunishmentSafetyError: If safe mode is still active.
        """
        if not self._state.active:
            return
        if not self._state.suspended:
            return  # Idempotent — not suspended.

        if self._safe_mode.is_active:
            raise PunishmentSafetyError(
                "Cannot resume punishment while safe mode is active."
            )

        if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
            raise PunishmentSafetyError(
                "Cannot resume punishment while HARD STOP is active."
            )

        if self._state.suspended_at is not None and self._state.started_at is not None:
            suspension_duration = datetime.now(tz=timezone.utc) - self._state.suspended_at
            self._state.started_at += suspension_duration

        self._state.suspended = False
        self._state.suspended_at = None
        self._state.suspension_reason = ""

        logger.info(
            "punishment_resumed",
            level=(
                self._state.level.name if self._state.level else None
            ),
        )

    # -- queries -------------------------------------------------------------

    def get_current(self) -> PunishmentState:
        """Return the current punishment state snapshot.

        Auto-expiry is checked before returning — if the punishment duration
        has elapsed it will be deactivated first.
        """
        self._check_expiry()
        return self._state

    # -- PersonaPlugin hook methods ------------------------------------------

    def get_state_snapshot(self) -> dict[str, object]:
        """Return a serialisable snapshot of current punishment state.

        Intended for PersonaPlugin ``on_response`` / ``pre_tool_call`` hooks
        to read punishment context without coupling to internal dataclass.
        """
        self._check_expiry()
        s = self._state
        return {
            "active": s.active,
            "level": int(s.level) if s.level is not None else None,
            "level_name": s.level.name if s.level is not None else None,
            "violation_type": s.violation_type,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "duration_seconds": s.duration.total_seconds(),
            "suspended": s.suspended,
            "suspension_reason": s.suspension_reason,
        }

    @staticmethod
    def get_config() -> dict[int, dict[str, object]]:
        """Return the punishment config as a serialisable dict.

        Enables PersonaPlugin to inspect punishment level metadata without
        importing PunishmentLevelConfig directly.
        """
        return {
            int(level): {
                "name": cfg.name,
                "duration_hours": list(cfg.duration_hours),
                "description": cfg.description,
                "allowed_actions": list(cfg.allowed_actions),
                "blocked_actions": list(cfg.blocked_actions),
            }
            for level, cfg in PUNISHMENT_CONFIG.items()
        }

    def get_current_level(self) -> PunishmentLevel | None:
        """Return the current ``PunishmentLevel`` (or ``None`` if inactive).

        Convenience accessor for PersonaPlugin ``pre_prompt`` hook.
        """
        self._check_expiry()
        return self._state.level

    def is_active(self) -> bool:
        """Check whether a punishment is currently active and not suspended.

        Auto-expiry is checked before returning.
        """
        self._check_expiry()
        return self._state.active and not self._state.suspended

    def time_remaining(self) -> timedelta:
        """Return the time remaining on the current punishment.

        Returns:
            ``timedelta(0)`` if no punishment is active, if the punishment
            has expired, or if the punishment is suspended (time is paused).

            For active punishments, returns ``duration - elapsed`` (minimum 0).
        """
        self._check_expiry()

        if not self._state.active or self._state.started_at is None:
            return timedelta(0)

        if self._state.suspended:
            # Time is paused — return the duration as "time remaining"
            # since we don't track partial elapsed before suspension.
            # The clock resets on resume via started_at shift.
            now = datetime.now(tz=timezone.utc)
            if self._state.suspended_at is not None:
                elapsed_before_suspend = self._state.suspended_at - self._state.started_at
            else:
                elapsed_before_suspend = now - self._state.started_at
            remaining = self._state.duration - elapsed_before_suspend
            return max(remaining, timedelta(0))

        now = datetime.now(tz=timezone.utc)
        elapsed = now - self._state.started_at
        remaining = self._state.duration - elapsed
        return max(remaining, timedelta(0))

    def check_distress_suspension(self, distress_level: DistressLevel) -> bool:
        """Evaluate distress level and suspend or resume accordingly.

        Suspends punishment when distress >= D3_SEVERE.
        Resumes (if previously auto-suspended) when distress drops below D3
        and safe mode is not active.

        Args:
            distress_level: The current distress level to evaluate.

        Returns:
            ``True`` if the punishment state changed, ``False`` otherwise.
        """
        if distress_level >= DistressLevel.D3_SEVERE:
            if self._state.active and not self._state.suspended:
                self.suspend(reason=f"distress_{distress_level.name}")
                return True
            return False
        else:
            # Distress below D3 — can resume if safe mode isn't blocking.
            if self._state.active and self._state.suspended:
                if not self._safe_mode.is_active:
                    self.resume()
                    return True
            return False

    # -- Redis sync helper ---------------------------------------------------

    def _sync_punishment_to_redis(self) -> None:
        """Sync current punishment level to Redis DB5 if state_manager is set."""
        if self._state_manager is None:
            return
        level = int(self._state.level) if self._state.level is not None else 0
        if not self._state.active:
            level = 0
        try:
            _ = self._state_manager.set_punishment(level)
        except Exception:
            logger.warning(
                "punishment_redis_sync_failed",
                level=level,
                exc_info=True,
            )

    # -- internal helpers ----------------------------------------------------

    def _activate_level(self, level: PunishmentLevel) -> None:
        """Set the current level and reset the clock."""
        config = PUNISHMENT_CONFIG[level]
        now = datetime.now(tz=timezone.utc)
        hours_min, hours_max = config.duration_hours
        duration = timedelta(hours=(hours_min + hours_max) / 2.0)

        self._state.level = level
        self._state.started_at = now
        self._state.duration = duration
        self._sync_punishment_to_redis()

    def _deactivate(self) -> None:
        """Clear all punishment state."""
        self._state = PunishmentState()
        self._sync_punishment_to_redis()

    def _check_expiry(self) -> None:
        """Deactivate punishment if its duration has elapsed.

        Expiry does not run while the punishment is suspended — the clock is
        paused during suspension.
        """
        if not self._state.active or self._state.started_at is None:
            return
        if self._state.suspended:
            return

        now = datetime.now(tz=timezone.utc)
        elapsed = now - self._state.started_at
        if elapsed >= self._state.duration:
            logger.info(
                "punishment_expired",
                level=(
                    self._state.level.name if self._state.level else None
                ),
            )
            self._deactivate()
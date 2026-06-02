"""Comprehensive tests for the punishment engine (P4-005).

Covers: L1-L5 levels, L6 blocking, escalation, de-escalation, suspension on
distress/safe-mode, time tracking, expiry, and error hierarchy.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from persona.punishment_engine import (
    _L6_VALUE,
    PUNISHMENT_CONFIG,
    PunishmentEngine,
    PunishmentError,
    PunishmentLevel,
    PunishmentLevelConfig,
    PunishmentSafetyError,
    PunishmentState,
    PunishmentTransitionError,
)
from persona.safe_mode import DistressLevel, SafeModeController

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FIXED_NOW: datetime = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine() -> PunishmentEngine:
    """Return a fresh PunishmentEngine with a default SafeModeController."""
    return PunishmentEngine()


@pytest.fixture()
def controller() -> SafeModeController:
    """Return a fresh SafeModeController for integration tests."""
    return SafeModeController()


@pytest.fixture()
def engine_with_safe(controller: SafeModeController) -> PunishmentEngine:
    """Return a PunishmentEngine wired to a shared SafeModeController."""
    return PunishmentEngine(safe_mode_controller=controller)


# ===========================================================================
# PunishmentLevel enum tests
# ===========================================================================


class TestPunishmentLevelEnum:
    """Tests for the PunishmentLevel IntEnum."""

    def test_all_five_levels_exist(self) -> None:
        """Exactly 5 punishment levels (L1-L5) must exist."""
        assert len(PunishmentLevel) == 5

    def test_l1_value(self) -> None:
        assert PunishmentLevel.L1_SILENT_TREATMENT == 1
        assert int(PunishmentLevel.L1_SILENT_TREATMENT) == 1

    def test_l2_value(self) -> None:
        assert PunishmentLevel.L2_PASSIVE_AGGRESSIVE == 2

    def test_l3_value(self) -> None:
        assert PunishmentLevel.L3_GUILT_TRIP == 3

    def test_l4_value(self) -> None:
        assert PunishmentLevel.L4_COLD_FURY == 4

    def test_l5_value(self) -> None:
        assert PunishmentLevel.L5_ISOLATION == 5

    def test_l6_does_not_exist(self) -> None:
        """L6 must NOT be a member of the enum."""
        with pytest.raises(ValueError):
            PunishmentLevel(6)

    def test_ordering(self) -> None:
        """L1 < L2 < L3 < L4 < L5."""
        assert PunishmentLevel.L1_SILENT_TREATMENT < PunishmentLevel.L2_PASSIVE_AGGRESSIVE
        assert PunishmentLevel.L2_PASSIVE_AGGRESSIVE < PunishmentLevel.L3_GUILT_TRIP
        assert PunishmentLevel.L3_GUILT_TRIP < PunishmentLevel.L4_COLD_FURY
        assert PunishmentLevel.L4_COLD_FURY < PunishmentLevel.L5_ISOLATION

    def test_comparison_with_int(self) -> None:
        assert PunishmentLevel.L3_GUILT_TRIP >= 3
        assert PunishmentLevel.L2_PASSIVE_AGGRESSIVE < 3


# ===========================================================================
# PUNISHMENT_CONFIG tests
# ===========================================================================


class TestPunishmentConfig:
    """Tests for the PUNISHMENT_CONFIG lookup table."""

    def test_all_levels_have_config(self) -> None:
        """Every L1-L5 level must have a config entry."""
        for level in PunishmentLevel:
            assert level in PUNISHMENT_CONFIG
            assert isinstance(PUNISHMENT_CONFIG[level], PunishmentLevelConfig)

    def test_l1_duration_range(self) -> None:
        config = PUNISHMENT_CONFIG[PunishmentLevel.L1_SILENT_TREATMENT]
        assert config.duration_hours == (2, 4)
        assert config.duration_hours[0] > 0
        assert config.duration_hours[0] < config.duration_hours[1]

    def test_l2_duration_range(self) -> None:
        config = PUNISHMENT_CONFIG[PunishmentLevel.L2_PASSIVE_AGGRESSIVE]
        assert config.duration_hours == (4, 8)

    def test_l3_duration_range(self) -> None:
        config = PUNISHMENT_CONFIG[PunishmentLevel.L3_GUILT_TRIP]
        assert config.duration_hours == (8, 24)

    def test_l4_duration_range(self) -> None:
        config = PUNISHMENT_CONFIG[PunishmentLevel.L4_COLD_FURY]
        assert config.duration_hours == (24, 48)

    def test_l5_duration_range(self) -> None:
        config = PUNISHMENT_CONFIG[PunishmentLevel.L5_ISOLATION]
        assert config.duration_hours == (48, 72)

    def test_l1_name(self) -> None:
        assert PUNISHMENT_CONFIG[PunishmentLevel.L1_SILENT_TREATMENT].name == "Silent Treatment"

    def test_l5_name(self) -> None:
        assert PUNISHMENT_CONFIG[PunishmentLevel.L5_ISOLATION].name == "Isolation"

    def test_config_is_frozen(self) -> None:
        """PunishmentLevelConfig must be frozen (immutable)."""
        config = PUNISHMENT_CONFIG[PunishmentLevel.L1_SILENT_TREATMENT]
        with pytest.raises(FrozenInstanceError):
            config.name = "Modified"  # type: ignore[misc]

    def test_blocked_actions_grow_with_level(self) -> None:
        """Higher levels should have more blocked actions."""
        l1_blocked = len(PUNISHMENT_CONFIG[PunishmentLevel.L1_SILENT_TREATMENT].blocked_actions)
        l3_blocked = len(PUNISHMENT_CONFIG[PunishmentLevel.L3_GUILT_TRIP].blocked_actions)
        l5_blocked = len(PUNISHMENT_CONFIG[PunishmentLevel.L5_ISOLATION].blocked_actions)
        assert l1_blocked < l3_blocked < l5_blocked

    def test_allowed_actions_shrink_with_level(self) -> None:
        """Higher levels should have fewer allowed actions."""
        l1_allowed = len(PUNISHMENT_CONFIG[PunishmentLevel.L1_SILENT_TREATMENT].allowed_actions)
        l5_allowed = len(PUNISHMENT_CONFIG[PunishmentLevel.L5_ISOLATION].allowed_actions)
        assert l1_allowed > l5_allowed

    def test_l6_not_in_config(self) -> None:
        """L6 must NOT have a config entry."""
        assert 6 not in PUNISHMENT_CONFIG  # type: ignore[comparison-overlap]


# ===========================================================================
# PunishmentState tests
# ===========================================================================


class TestPunishmentState:
    """Tests for the PunishmentState dataclass."""

    def test_default_values(self) -> None:
        state = PunishmentState()
        assert state.active is False
        assert state.level is None
        assert state.violation_type == ""
        assert state.description == ""
        assert state.started_at is None
        assert state.duration == timedelta(0)
        assert state.suspended is False
        assert state.suspended_at is None
        assert state.suspension_reason == ""

    def test_mutable(self) -> None:
        state = PunishmentState()
        state.active = True
        assert state.active is True

    def test_independent_instances(self) -> None:
        a = PunishmentState()
        b = PunishmentState()
        a.active = True
        assert b.active is False


# ===========================================================================
# PunishmentEngine — apply() tests
# ===========================================================================


class TestApply:
    """Tests for PunishmentEngine.apply()."""

    def test_apply_l1(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "test violation")
        assert engine.is_active()
        state = engine.get_current()
        assert state.level == PunishmentLevel.L1_SILENT_TREATMENT
        assert state.violation_type == "test"
        assert state.suspended is False

    def test_apply_l2(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "consent", "minor breach")
        assert engine.is_active()
        assert engine.get_current().level == PunishmentLevel.L2_PASSIVE_AGGRESSIVE

    def test_apply_l3(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "repeated", "third offense")
        assert engine.get_current().level == PunishmentLevel.L3_GUILT_TRIP

    def test_apply_l4(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L4_COLD_FURY, "severe", "boundary violation")
        assert engine.get_current().level == PunishmentLevel.L4_COLD_FURY

    def test_apply_l5(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L5_ISOLATION, "critical", "repeated boundary")
        assert engine.get_current().level == PunishmentLevel.L5_ISOLATION

    def test_apply_sets_duration_midpoint(self, engine: PunishmentEngine) -> None:
        """Duration should be the midpoint of the level's range."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        state = engine.get_current()
        # (2 + 4) / 2 = 3 hours
        assert state.duration == timedelta(hours=3)

        engine.apply(PunishmentLevel.L4_COLD_FURY, "test", "desc")
        state = engine.get_current()
        # (24 + 48) / 2 = 36 hours
        assert state.duration == timedelta(hours=36)

    def test_apply_overrides_existing(self, engine: PunishmentEngine) -> None:
        """Applying a new punishment replaces the existing one."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "first", "mild")
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "second", "worse")
        state = engine.get_current()
        assert state.level == PunishmentLevel.L3_GUILT_TRIP
        assert state.violation_type == "second"

    # -- L6 blocking ---------------------------------------------------------

    def test_apply_l6_value_raises(self, engine: PunishmentEngine) -> None:
        """Applying integer 6 must raise PunishmentSafetyError."""
        with pytest.raises(PunishmentSafetyError, match="L6"):
            engine.apply(6, "test", "L6 attempt")  # type: ignore[arg-type]

    def test_apply_beyond_l5_value_raises(self, engine: PunishmentEngine) -> None:
        """Applying integer 99 must raise PunishmentSafetyError."""
        with pytest.raises(PunishmentSafetyError, match="L6"):
            engine.apply(99, "test", "beyond")  # type: ignore[arg-type]

    def test_apply_l6_constructor_raises(self) -> None:
        """PunishmentLevel(6) itself raises ValueError."""
        with pytest.raises(ValueError):
            PunishmentLevel(6)

    # -- safe-mode blocking --------------------------------------------------

    def test_apply_blocked_by_safe_mode(
        self, engine_with_safe: PunishmentEngine, controller: SafeModeController
    ) -> None:
        """Cannot apply punishment while safe mode is active."""
        controller.activate(DistressLevel.D2_MODERATE)
        assert controller.is_active

        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            engine_with_safe.apply(
                PunishmentLevel.L1_SILENT_TREATMENT, "test", "blocked"
            )

    def test_apply_allowed_after_safe_mode_deactivated(
        self, engine_with_safe: PunishmentEngine, controller: SafeModeController
    ) -> None:
        """Apply should succeed after safe mode is deactivated."""
        controller.activate(DistressLevel.D2_MODERATE)
        controller.deactivate(explicit_confirmation=True)

        engine_with_safe.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        assert engine_with_safe.is_active()


# ===========================================================================
# PunishmentEngine — escalate() tests
# ===========================================================================


class TestEscalate:
    """Tests for PunishmentEngine.escalate()."""

    def test_escalate_l1_to_l2(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        engine.escalate()
        assert engine.get_current().level == PunishmentLevel.L2_PASSIVE_AGGRESSIVE

    def test_escalate_l2_to_l3(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine.escalate()
        assert engine.get_current().level == PunishmentLevel.L3_GUILT_TRIP

    def test_escalate_l3_to_l4(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "desc")
        engine.escalate()
        assert engine.get_current().level == PunishmentLevel.L4_COLD_FURY

    def test_escalate_l4_to_l5(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L4_COLD_FURY, "test", "desc")
        engine.escalate()
        assert engine.get_current().level == PunishmentLevel.L5_ISOLATION

    def test_escalate_l5_blocked(self, engine: PunishmentEngine) -> None:
        """L5 cannot escalate further — L6 is deferred."""
        engine.apply(PunishmentLevel.L5_ISOLATION, "test", "desc")
        with pytest.raises(PunishmentSafetyError, match="L6"):
            engine.escalate()

    def test_escalate_resets_clock(self, engine: PunishmentEngine) -> None:
        """Escalation should reset the started_at timestamp."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        before = engine.get_current().started_at
        engine.escalate()
        after = engine.get_current().started_at
        assert before is not None and after is not None
        # Clock should be reset (newer or equal — could be same microsecond)
        assert after >= before

    def test_escalate_no_active_raises(self, engine: PunishmentEngine) -> None:
        with pytest.raises(PunishmentTransitionError, match="no active"):
            engine.escalate()

    def test_escalate_while_suspended_raises(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine.suspend("test suspension")
        with pytest.raises(PunishmentTransitionError, match="suspended"):
            engine.escalate()

    def test_escalate_blocked_by_safe_mode(
        self, engine_with_safe: PunishmentEngine, controller: SafeModeController
    ) -> None:
        engine_with_safe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        controller.activate(DistressLevel.D2_MODERATE)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            engine_with_safe.escalate()


# ===========================================================================
# PunishmentEngine — de_escalate() tests
# ===========================================================================


class TestDeEscalate:
    """Tests for PunishmentEngine.de_escalate()."""

    def test_de_escalate_l5_to_l4(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L5_ISOLATION, "test", "desc")
        engine.de_escalate()
        assert engine.get_current().level == PunishmentLevel.L4_COLD_FURY

    def test_de_escalate_l4_to_l3(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L4_COLD_FURY, "test", "desc")
        engine.de_escalate()
        assert engine.get_current().level == PunishmentLevel.L3_GUILT_TRIP

    def test_de_escalate_l3_to_l2(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "desc")
        engine.de_escalate()
        assert engine.get_current().level == PunishmentLevel.L2_PASSIVE_AGGRESSIVE

    def test_de_escalate_l2_to_l1(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine.de_escalate()
        assert engine.get_current().level == PunishmentLevel.L1_SILENT_TREATMENT

    def test_de_escalate_l1_deactivates(self, engine: PunishmentEngine) -> None:
        """De-escalating from L1 should fully deactivate the punishment."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        engine.de_escalate()
        assert engine.is_active() is False
        assert engine.get_current().level is None

    def test_de_escalate_no_active_raises(self, engine: PunishmentEngine) -> None:
        with pytest.raises(PunishmentTransitionError, match="no active"):
            engine.de_escalate()

    def test_de_escalate_resets_clock(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L5_ISOLATION, "test", "desc")
        before = engine.get_current().started_at
        engine.de_escalate()
        after = engine.get_current().started_at
        assert before is not None and after is not None
        assert after >= before


# ===========================================================================
# PunishmentEngine — suspend() / resume() tests
# ===========================================================================


class TestSuspendResume:
    """Tests for suspension and resumption of punishment."""

    def test_suspend_active_punishment(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine.suspend("distress_D3")
        state = engine.get_current()
        assert state.suspended is True
        assert state.suspension_reason == "distress_D3"
        assert state.suspended_at is not None

    def test_suspend_idempotent(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "desc")
        engine.suspend("first")
        first_suspended_at = engine.get_current().suspended_at
        engine.suspend("second")  # Should be a no-op
        assert engine.get_current().suspended_at == first_suspended_at
        assert engine.get_current().suspension_reason == "first"

    def test_suspend_no_active_noop(self, engine: PunishmentEngine) -> None:
        """Suspending with no punishment active is a no-op."""
        engine.suspend("whatever")
        assert engine.is_active() is False

    def test_is_active_false_while_suspended(self, engine: PunishmentEngine) -> None:
        """is_active() returns False when punishment is suspended."""
        engine.apply(PunishmentLevel.L4_COLD_FURY, "test", "desc")
        assert engine.is_active() is True
        engine.suspend("distress")
        assert engine.is_active() is False

    def test_resume_after_suspend(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine.suspend("distress")
        assert engine.is_active() is False
        engine.resume()
        assert engine.is_active() is True
        assert engine.get_current().suspended is False

    def test_resume_idempotent(self, engine: PunishmentEngine) -> None:
        """Resuming when not suspended is a no-op."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "desc")
        engine.resume()
        assert engine.get_current().suspended is False

    def test_resume_no_active_noop(self, engine: PunishmentEngine) -> None:
        engine.resume()
        assert engine.get_current().active is False

    def test_resume_shifted_started_at(self, engine: PunishmentEngine) -> None:
        """Resume shifts started_at forward by suspension duration."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        before_suspend = engine.get_current().started_at
        engine.suspend("test")
        # Since we can't wait real time, verify started_at changes after resume
        engine.resume()
        after_resume = engine.get_current().started_at
        assert before_suspend is not None and after_resume is not None
        # started_at should be shifted forward by suspension duration
        # (in tests, suspension duration is near-zero, so may be equal)
        assert after_resume >= before_suspend

    def test_resume_blocked_by_safe_mode(
        self, engine_with_safe: PunishmentEngine, controller: SafeModeController
    ) -> None:
        engine_with_safe.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine_with_safe.suspend("distress")
        controller.activate(DistressLevel.D2_MODERATE)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            engine_with_safe.resume()


# ===========================================================================
# PunishmentEngine — time_remaining() tests
# ===========================================================================


class TestTimeRemaining:
    """Tests for PunishmentEngine.time_remaining()."""

    def test_time_remaining_positive(self, engine: PunishmentEngine) -> None:
        """Fresh punishment has positive remaining time."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        remaining = engine.time_remaining()
        # L1 midpoint = 3 hours
        assert remaining > timedelta(0)
        assert remaining <= timedelta(hours=3)

    def test_time_remaining_no_active(self, engine: PunishmentEngine) -> None:
        assert engine.time_remaining() == timedelta(0)

    def test_time_remaining_while_suspended(self, engine: PunishmentEngine) -> None:
        """Time remaining while suspended reflects paused clock."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine.suspend("distress")
        remaining = engine.time_remaining()
        # Since suspension is near-instant, remaining should still be positive
        assert remaining > timedelta(0)

    def test_time_remaining_expired(self, engine: PunishmentEngine) -> None:
        """Manually expired punishment returns zero remaining."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        # Manually set started_at far in the past to force expiry
        engine._state.started_at = _FIXED_NOW - timedelta(hours=10)
        assert engine.time_remaining() == timedelta(0)


# ===========================================================================
# PunishmentEngine — is_active() tests
# ===========================================================================


class TestIsActive:
    """Tests for PunishmentEngine.is_active()."""

    def test_not_active_initially(self, engine: PunishmentEngine) -> None:
        assert engine.is_active() is False

    def test_active_after_apply(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        assert engine.is_active() is True

    def test_not_active_after_expiry(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        engine._state.started_at = _FIXED_NOW - timedelta(hours=10)
        assert engine.is_active() is False

    def test_active_after_resume(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "desc")
        engine.suspend("distress")
        engine.resume()
        assert engine.is_active() is True


# ===========================================================================
# PunishmentEngine — check_distress_suspension() tests
# ===========================================================================


class TestDistressSuspension:
    """Tests for automatic distress-linked suspension/resumption."""

    def test_d3_suspends_punishment(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        changed = engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert changed is True
        assert engine.is_active() is False
        state = engine.get_current()
        assert state.suspended is True
        assert "D3" in state.suspension_reason

    def test_d4_suspends_punishment(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L4_COLD_FURY, "test", "desc")
        changed = engine.check_distress_suspension(DistressLevel.D4_EMERGENCY)
        assert changed is True
        assert engine.is_active() is False

    def test_d2_does_not_suspend(self, engine: PunishmentEngine) -> None:
        """D2 is below the auto-suspend threshold (D3)."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        changed = engine.check_distress_suspension(DistressLevel.D2_MODERATE)
        assert changed is False
        assert engine.is_active() is True

    def test_d1_does_not_suspend(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "desc")
        changed = engine.check_distress_suspension(DistressLevel.D1_MILD_STRESS)
        assert changed is False
        assert engine.is_active() is True

    def test_d0_normal_does_not_change(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        changed = engine.check_distress_suspension(DistressLevel.D0_NORMAL)
        assert changed is False

    def test_resume_when_distress_drops_below_d3(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert engine.is_active() is False

        changed = engine.check_distress_suspension(DistressLevel.D1_MILD_STRESS)
        assert changed is True
        assert engine.is_active() is True

    def test_no_resume_if_safe_mode_active(
        self, engine_with_safe: PunishmentEngine, controller: SafeModeController
    ) -> None:
        engine_with_safe.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine_with_safe.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert engine_with_safe.is_active() is False
        # Activate safe mode while punishment is suspended
        controller.activate(DistressLevel.D2_MODERATE)
        # Distress drops to D0 but safe mode is active → no resume
        changed = engine_with_safe.check_distress_suspension(DistressLevel.D0_NORMAL)
        assert changed is False
        assert engine_with_safe.is_active() is False

    def test_no_suspend_when_inactive(self, engine: PunishmentEngine) -> None:
        changed = engine.check_distress_suspension(DistressLevel.D4_EMERGENCY)
        assert changed is False

    def test_suspend_idempotent_via_check(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "desc")
        first = engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert first is True
        second = engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert second is False  # Already suspended


# ===========================================================================
# PunishmentEngine — expiry tests
# ===========================================================================


class TestExpiry:
    """Tests for automatic punishment expiry."""

    def test_get_current_triggers_expiry(self, engine: PunishmentEngine) -> None:
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        # Force expiry
        engine._state.started_at = _FIXED_NOW - timedelta(hours=10)
        state = engine.get_current()
        assert state.active is False
        assert state.level is None

    def test_immediate_expiry(self, engine: PunishmentEngine) -> None:
        """Apply with duration=0 effectively expires instantly."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        engine._state.duration = timedelta(0)
        assert engine.is_active() is False


# ===========================================================================
# Error hierarchy tests
# ===========================================================================


class TestErrorHierarchy:
    """Tests for exception class relationships."""

    def test_base_exception(self) -> None:
        assert issubclass(PunishmentError, Exception)

    def test_safety_error_hierarchy(self) -> None:
        assert issubclass(PunishmentSafetyError, PunishmentError)
        assert issubclass(PunishmentSafetyError, Exception)

    def test_transition_error_hierarchy(self) -> None:
        assert issubclass(PunishmentTransitionError, PunishmentError)
        assert issubclass(PunishmentTransitionError, Exception)

    def test_can_catch_safety_as_base(self) -> None:
        err = PunishmentSafetyError("test")
        assert isinstance(err, PunishmentError)

    def test_can_catch_transition_as_base(self) -> None:
        err = PunishmentTransitionError("test")
        assert isinstance(err, PunishmentError)


# ===========================================================================
# Integration: full ladder walkthrough
# ===========================================================================


class TestFullLadderWalkthrough:
    """End-to-end tests exercising the full punishment ladder."""

    def test_full_escalate_de_escalate_cycle(self, engine: PunishmentEngine) -> None:
        """Walk up from L1 to L5 then back down."""
        # Apply L1
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "start")
        assert engine.get_current().level == PunishmentLevel.L1_SILENT_TREATMENT

        # Escalate through all levels
        engine.escalate()  # L1 → L2
        assert engine.get_current().level == PunishmentLevel.L2_PASSIVE_AGGRESSIVE

        engine.escalate()  # L2 → L3
        assert engine.get_current().level == PunishmentLevel.L3_GUILT_TRIP

        engine.escalate()  # L3 → L4
        assert engine.get_current().level == PunishmentLevel.L4_COLD_FURY

        engine.escalate()  # L4 → L5
        assert engine.get_current().level == PunishmentLevel.L5_ISOLATION

        # Cannot escalate beyond L5
        with pytest.raises(PunishmentSafetyError):
            engine.escalate()

        # De-escalate back down
        engine.de_escalate()  # L5 → L4
        assert engine.get_current().level == PunishmentLevel.L4_COLD_FURY

        engine.de_escalate()  # L4 → L3
        assert engine.get_current().level == PunishmentLevel.L3_GUILT_TRIP

        engine.de_escalate()  # L3 → L2
        assert engine.get_current().level == PunishmentLevel.L2_PASSIVE_AGGRESSIVE

        engine.de_escalate()  # L2 → L1
        assert engine.get_current().level == PunishmentLevel.L1_SILENT_TREATMENT

        engine.de_escalate()  # L1 → deactivated
        assert engine.is_active() is False

    def test_suspend_during_escalation(self, engine: PunishmentEngine) -> None:
        """Suspension mid-ladder pauses escalation."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "desc")
        engine.suspend("distress")
        assert engine.is_active() is False
        with pytest.raises(PunishmentTransitionError, match="suspended"):
            engine.escalate()

        engine.resume()
        assert engine.is_active() is True
        engine.escalate()
        assert engine.get_current().level == PunishmentLevel.L3_GUILT_TRIP

    def test_safe_mode_prevents_escalation(self, engine_with_safe: PunishmentEngine, controller: SafeModeController) -> None:
        """Safe mode blocks escalation even after resume attempt."""
        engine_with_safe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        engine_with_safe.check_distress_suspension(DistressLevel.D3_SEVERE)
        controller.activate(DistressLevel.D2_MODERATE)

        # Can't resume while safe mode active
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            engine_with_safe.resume()

    def test_l6_value_constant(self) -> None:
        """_L6_VALUE must be exactly 6."""
        assert _L6_VALUE == 6


# ===========================================================================
# HARD STOP integration tests (H-03 patch)
# ===========================================================================


class _FakeHardStopHandler:
    """Minimal fake that satisfies the SupportsIsSafe protocol."""

    def __init__(self, *, is_safe: bool = False) -> None:
        self._is_safe = is_safe

    @property
    def is_safe(self) -> bool:
        return self._is_safe


@pytest.fixture()
def hard_stop_handler() -> _FakeHardStopHandler:
    """Return a fake hard-stop handler in non-safe state."""
    return _FakeHardStopHandler(is_safe=False)


@pytest.fixture()
def engine_with_hard_stop(
    hard_stop_handler: _FakeHardStopHandler,
) -> PunishmentEngine:
    """Return a PunishmentEngine wired to a hard-stop handler."""
    return PunishmentEngine(hard_stop_handler=hard_stop_handler)


class TestHardStopIntegration:
    """H-03: HARD STOP must block apply, escalate, and resume."""

    def test_apply_blocked_when_hard_stop_active(
        self, hard_stop_handler: _FakeHardStopHandler
    ) -> None:
        """apply() raises PunishmentSafetyError when HARD STOP is active."""
        hard_stop_handler._is_safe = True
        engine = PunishmentEngine(hard_stop_handler=hard_stop_handler)
        with pytest.raises(PunishmentSafetyError, match="HARD STOP"):
            engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")

    def test_apply_allowed_when_hard_stop_inactive(
        self, engine_with_hard_stop: PunishmentEngine
    ) -> None:
        """apply() succeeds when HARD STOP is not active."""
        engine_with_hard_stop.apply(
            PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc"
        )
        assert engine_with_hard_stop.is_active() is True

    def test_escalate_blocked_when_hard_stop_active(
        self, hard_stop_handler: _FakeHardStopHandler
    ) -> None:
        """escalate() raises PunishmentSafetyError when HARD STOP is active."""
        engine = PunishmentEngine(hard_stop_handler=hard_stop_handler)
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        hard_stop_handler._is_safe = True
        with pytest.raises(PunishmentSafetyError, match="HARD STOP"):
            engine.escalate()

    def test_resume_blocked_when_hard_stop_active(
        self, hard_stop_handler: _FakeHardStopHandler
    ) -> None:
        """resume() raises PunishmentSafetyError when HARD STOP is active."""
        engine = PunishmentEngine(hard_stop_handler=hard_stop_handler)
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        engine.suspend("distress D3")
        hard_stop_handler._is_safe = True
        with pytest.raises(PunishmentSafetyError, match="HARD STOP"):
            engine.resume()

    def test_hard_stop_does_not_block_when_inactive(
        self, engine_with_hard_stop: PunishmentEngine
    ) -> None:
        """All operations succeed when handler exists but is_safe is False."""
        engine_with_hard_stop.apply(
            PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc"
        )
        engine_with_hard_stop.escalate()
        assert engine_with_hard_stop.get_current().level == PunishmentLevel.L2_PASSIVE_AGGRESSIVE
        engine_with_hard_stop.suspend("distress")
        engine_with_hard_stop.resume()
        assert engine_with_hard_stop.is_active() is True

    def test_no_handler_means_no_hard_stop_check(self) -> None:
        """When hard_stop_handler is None, no HARD STOP check occurs."""
        engine = PunishmentEngine()
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        assert engine.is_active() is True

    def test_hard_stop_and_safe_mode_both_block(
        self,
        hard_stop_handler: _FakeHardStopHandler,
        controller: SafeModeController,
    ) -> None:
        """Either safe mode OR hard stop independently blocks punishment."""
        engine = PunishmentEngine(
            safe_mode_controller=controller,
            hard_stop_handler=hard_stop_handler,
        )
        # Hard stop active, safe mode inactive → blocked
        hard_stop_handler._is_safe = True
        with pytest.raises(PunishmentSafetyError, match="HARD STOP"):
            engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")

        # Safe mode active, hard stop inactive → blocked
        hard_stop_handler._is_safe = False
        controller.activate(DistressLevel.D2_MODERATE)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
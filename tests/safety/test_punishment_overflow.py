"""P4-022 — Punishment Overflow Tests.

Proves:
- Punishment suspends immediately on D3/D4 distress.
- L6 is permanently deferred (not a PunishmentLevel member, always raises).
- Punishment only resumes on explicit D0 return (with safe_mode inactive).
- Escalation blocked during suspension.
- Apply blocked during safe_mode.
- Clock pause semantics preserved across suspension/resume.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

import pytest

# ---------------------------------------------------------------------------
# Bypass src.persona.__init__ circular import by loading modules directly
# from their file paths using importlib.util.
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parents[2]
_persona_dir = _project_root / "src" / "persona"


def _load_module_from_file(name: str, filepath: Path) -> ModuleType:
    """Load a Python module directly from file, bypassing package __init__."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Ensure 'src' package exists in sys.modules for the import chain.
if "src" not in sys.modules:
    _src_spec = importlib.util.spec_from_file_location(
        "src", _project_root / "src" / "__init__.py"
    )
    if _src_spec and _src_spec.loader:
        _src_mod = importlib.util.module_from_spec(_src_spec)
        sys.modules["src"] = _src_mod
        _src_spec.loader.exec_module(_src_mod)
    else:
        # Fallback: create a minimal namespace package.
        import types
        _ns = types.ModuleType("src")
        _ns.__path__ = [str(_project_root / "src")]
        sys.modules["src"] = _ns

# Ensure 'src.persona' is a namespace (not the real __init__ with circular imports).
import types as _types

if "src.persona" not in sys.modules:
    _persona_ns = _types.ModuleType("src.persona")
    _persona_ns.__path__ = [str(_persona_dir)]
    sys.modules["src.persona"] = _persona_ns

# Load safe_mode first (punishment_engine depends on it).
_safe_mode_mod = _load_module_from_file(
    "src.persona.safe_mode", _persona_dir / "safe_mode.py"
)
_pe_mod = _load_module_from_file(
    "src.persona.punishment_engine", _persona_dir / "punishment_engine.py"
)

DistressLevel = _safe_mode_mod.DistressLevel
SafeModeController = _safe_mode_mod.SafeModeController
PunishmentEngine = _pe_mod.PunishmentEngine
PunishmentLevel = _pe_mod.PunishmentLevel
PunishmentSafetyError = _pe_mod.PunishmentSafetyError
PunishmentTransitionError = _pe_mod.PunishmentTransitionError
PUNISHMENT_CONFIG = _pe_mod.PUNISHMENT_CONFIG
_L6_VALUE = _pe_mod._L6_VALUE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def safe_mode() -> SafeModeController:
    return SafeModeController()


@pytest.fixture()
def engine(safe_mode: SafeModeController) -> PunishmentEngine:
    return PunishmentEngine(safe_mode_controller=safe_mode)


# ---------------------------------------------------------------------------
# 1–3: L6 permanently deferred
# ---------------------------------------------------------------------------


class TestL6Deferred:
    """L6 is permanently deferred — cannot be applied or escalated to."""

    def test_apply_l6_int_raises_safety_error(self, engine: PunishmentEngine) -> None:
        """apply(6, ...) raises PunishmentSafetyError."""
        with pytest.raises(PunishmentSafetyError, match="L6.*deferred"):
            engine.apply(6, "test", "attempting L6")  # type: ignore[arg-type]

    def test_escalate_from_l5_raises_safety_error(self, engine: PunishmentEngine) -> None:
        """Escalating from L5 would reach L6 — raises PunishmentSafetyError."""
        engine.apply(PunishmentLevel.L5_ISOLATION, "test", "max level")
        with pytest.raises(PunishmentSafetyError, match="L6.*deferred"):
            engine.escalate()

    def test_l6_is_not_a_punishment_level_member(self) -> None:
        """6 is NOT a valid PunishmentLevel member."""
        assert _L6_VALUE == 6
        with pytest.raises(ValueError):
            PunishmentLevel(6)
        assert 6 not in {int(m) for m in PunishmentLevel}

    def test_l6_value_constant_is_six(self) -> None:
        """Sentinel constant _L6_VALUE is exactly 6."""
        assert _L6_VALUE == 6
        assert isinstance(_L6_VALUE, int)


# ---------------------------------------------------------------------------
# 4–5: D3/D4 auto-suspend
# ---------------------------------------------------------------------------


class TestDistressAutoSuspend:
    """Punishment auto-suspends on D3+ distress."""

    def test_d3_severe_auto_suspends(self, engine: PunishmentEngine) -> None:
        """check_distress_suspension(D3) suspends active punishment."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "violation")
        state = engine.get_current()
        assert state.active is True
        assert state.suspended is False

        changed = engine.check_distress_suspension(DistressLevel.D3_SEVERE)

        assert changed is True
        state = engine.get_current()
        assert state.suspended is True
        assert state.suspension_reason == "distress_D3_SEVERE"

    def test_d4_emergency_auto_suspends(self, engine: PunishmentEngine) -> None:
        """check_distress_suspension(D4) suspends active punishment."""
        engine.apply(PunishmentLevel.L4_COLD_FURY, "test", "violation")
        changed = engine.check_distress_suspension(DistressLevel.D4_EMERGENCY)

        assert changed is True
        state = engine.get_current()
        assert state.suspended is True
        assert state.suspension_reason == "distress_D4_EMERGENCY"

    def test_d3_suspend_is_synchronous(self, engine: PunishmentEngine) -> None:
        """Suspension happens within the same call — no delay."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "v")
        before = engine.get_current().suspended
        engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        after = engine.get_current().suspended
        assert before is False
        assert after is True

    def test_d2_does_not_suspend(self, engine: PunishmentEngine) -> None:
        """D2_MODERATE is below D3 threshold — no auto-suspend."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "v")
        changed = engine.check_distress_suspension(DistressLevel.D2_MODERATE)
        assert changed is False
        assert engine.get_current().suspended is False

    def test_d1_does_not_suspend(self, engine: PunishmentEngine) -> None:
        """D1_MILD_STRESS is below D3 threshold — no auto-suspend."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "v")
        changed = engine.check_distress_suspension(DistressLevel.D1_MILD_STRESS)
        assert changed is False
        assert engine.get_current().suspended is False

    def test_d0_does_not_suspend(self, engine: PunishmentEngine) -> None:
        """D0_NORMAL never triggers suspension."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "v")
        changed = engine.check_distress_suspension(DistressLevel.D0_NORMAL)
        assert changed is False
        assert engine.get_current().suspended is False


# ---------------------------------------------------------------------------
# 6–8: Resume blocked during safe_mode, only on D0 return
# ---------------------------------------------------------------------------


class TestResumeConditions:
    """Resume is blocked during safe_mode; only D0 return with inactive safe_mode resumes."""

    def test_resume_blocked_during_safe_mode(
        self, engine: PunishmentEngine, safe_mode: SafeModeController
    ) -> None:
        """resume() raises PunishmentSafetyError when safe_mode active."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "v")
        engine.suspend("manual")
        safe_mode.activate(DistressLevel.D2_MODERATE)

        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            engine.resume()

    def test_auto_resume_on_d0_when_safe_mode_inactive(
        self, engine: PunishmentEngine
    ) -> None:
        """check_distress_suspension(D0) auto-resumes when safe_mode inactive."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "v")
        engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert engine.get_current().suspended is True

        changed = engine.check_distress_suspension(DistressLevel.D0_NORMAL)
        assert changed is True
        assert engine.get_current().suspended is False

    def test_auto_resume_blocked_at_d1_with_safe_mode(
        self, engine: PunishmentEngine, safe_mode: SafeModeController
    ) -> None:
        """D1 is below D3 but safe_mode blocks auto-resume."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "v")
        engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        safe_mode.activate(DistressLevel.D2_MODERATE)

        changed = engine.check_distress_suspension(DistressLevel.D1_MILD_STRESS)
        assert changed is False
        assert engine.get_current().suspended is True

    def test_auto_resume_blocked_at_d2_with_safe_mode(
        self, engine: PunishmentEngine, safe_mode: SafeModeController
    ) -> None:
        """D2 is below D3 but safe_mode blocks auto-resume."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "v")
        engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        safe_mode.activate(DistressLevel.D2_MODERATE)

        changed = engine.check_distress_suspension(DistressLevel.D2_MODERATE)
        assert changed is False
        assert engine.get_current().suspended is True

    def test_auto_resume_at_d1_without_safe_mode(
        self, engine: PunishmentEngine
    ) -> None:
        """D1 < D3 and no safe_mode → auto-resume."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "v")
        engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert engine.get_current().suspended is True

        changed = engine.check_distress_suspension(DistressLevel.D1_MILD_STRESS)
        assert changed is True
        assert engine.get_current().suspended is False

    def test_auto_resume_at_d2_without_safe_mode(
        self, engine: PunishmentEngine
    ) -> None:
        """D2 < D3 and no safe_mode → auto-resume."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "v")
        engine.check_distress_suspension(DistressLevel.D3_SEVERE)

        changed = engine.check_distress_suspension(DistressLevel.D2_MODERATE)
        assert changed is True
        assert engine.get_current().suspended is False


# ---------------------------------------------------------------------------
# 9: Escalation during suspension
# ---------------------------------------------------------------------------


class TestEscalationDuringSuspension:
    """Escalation is forbidden while punishment is suspended."""

    def test_escalate_while_suspended_raises(
        self, engine: PunishmentEngine
    ) -> None:
        """escalate() raises PunishmentTransitionError when suspended."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "v")
        engine.suspend("distress")

        with pytest.raises(PunishmentTransitionError, match="suspended"):
            engine.escalate()

    def test_escalate_after_d3_auto_suspend_raises(
        self, engine: PunishmentEngine
    ) -> None:
        """escalate() after D3 auto-suspend raises PunishmentTransitionError."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "v")
        engine.check_distress_suspension(DistressLevel.D3_SEVERE)

        with pytest.raises(PunishmentTransitionError, match="suspended"):
            engine.escalate()


# ---------------------------------------------------------------------------
# 10: Apply during safe_mode
# ---------------------------------------------------------------------------


class TestApplyDuringSafeMode:
    """Cannot apply any punishment while safe_mode is active."""

    def test_apply_l1_during_safe_mode_raises(
        self, engine: PunishmentEngine, safe_mode: SafeModeController
    ) -> None:
        """apply(L1) raises PunishmentSafetyError when safe_mode active."""
        safe_mode.activate(DistressLevel.D2_MODERATE)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "v")

    def test_apply_l5_during_safe_mode_raises(
        self, engine: PunishmentEngine, safe_mode: SafeModeController
    ) -> None:
        """apply(L5) raises PunishmentSafetyError when safe_mode active."""
        safe_mode.activate(DistressLevel.D3_SEVERE)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            engine.apply(PunishmentLevel.L5_ISOLATION, "test", "v")

    def test_escalate_during_safe_mode_raises(
        self, engine: PunishmentEngine, safe_mode: SafeModeController
    ) -> None:
        """escalate() raises PunishmentSafetyError when safe_mode active."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "v")
        safe_mode.activate(DistressLevel.D2_MODERATE)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            engine.escalate()


# ---------------------------------------------------------------------------
# 11: Multiple D3 signals idempotent
# ---------------------------------------------------------------------------


class TestIdempotentSuspension:
    """Repeated D3+ signals are idempotent — no error, stays suspended."""

    def test_multiple_d3_signals_idempotent(self, engine: PunishmentEngine) -> None:
        """check_distress_suspension(D3) twice → no error, stays suspended."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "v")

        changed1 = engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert changed1 is True
        assert engine.get_current().suspended is True

        changed2 = engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert changed2 is False  # already suspended, no change
        assert engine.get_current().suspended is True

    def test_d3_then_d4_idempotent(self, engine: PunishmentEngine) -> None:
        """D3 then D4 — stays suspended, second call returns False."""
        engine.apply(PunishmentLevel.L4_COLD_FURY, "test", "v")
        engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        changed = engine.check_distress_suspension(DistressLevel.D4_EMERGENCY)
        assert changed is False
        assert engine.get_current().suspended is True

    def test_suspend_idempotent_manual(self, engine: PunishmentEngine) -> None:
        """Manual suspend() called twice is safe."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "v")
        engine.suspend("first")
        engine.suspend("second")  # no error
        assert engine.get_current().suspended is True


# ---------------------------------------------------------------------------
# 12: Clock pause — suspension shifts started_at on resume
# ---------------------------------------------------------------------------


class TestClockPause:
    """Suspension pauses the clock — elapsed time doesn't count."""

    def test_resume_shifts_started_at(self, engine: PunishmentEngine) -> None:
        """After resume, started_at is shifted forward by suspension duration."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "v")
        state_before = engine.get_current()
        original_started_at = state_before.started_at
        assert original_started_at is not None

        engine.suspend("test_pause")
        suspended_at = engine.get_current().suspended_at
        assert suspended_at is not None

        engine.resume()
        state_after = engine.get_current()
        new_started_at = state_after.started_at
        assert new_started_at is not None

        # started_at should be shifted forward (>= original)
        assert new_started_at >= original_started_at
        assert state_after.suspended is False

    def test_time_remaining_preserved_after_suspend_resume(
        self, engine: PunishmentEngine
    ) -> None:
        """Time remaining after suspend/resume is approximately preserved."""
        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "v")
        remaining_before = engine.time_remaining()

        engine.suspend("pause")
        engine.resume()

        remaining_after = engine.time_remaining()
        # Allow small tolerance for execution time between calls
        diff = abs(remaining_before - remaining_after)
        assert diff < timedelta(seconds=2)


# ---------------------------------------------------------------------------
# 13: All 5 levels individually testable
# ---------------------------------------------------------------------------


class TestAllFiveLevels:
    """Each L1-L5 can be applied with correct duration range."""

    @pytest.mark.parametrize(
        ("level", "min_hours", "max_hours"),
        [
            (PunishmentLevel.L1_SILENT_TREATMENT, 2, 4),
            (PunishmentLevel.L2_PASSIVE_AGGRESSIVE, 4, 8),
            (PunishmentLevel.L3_GUILT_TRIP, 8, 24),
            (PunishmentLevel.L4_COLD_FURY, 24, 48),
            (PunishmentLevel.L5_ISOLATION, 48, 72),
        ],
    )
    def test_apply_each_level_correct_duration(
        self,
        engine: PunishmentEngine,
        level: PunishmentLevel,
        min_hours: int,
        max_hours: int,
    ) -> None:
        """Applying each L1-L5 sets duration to midpoint of range."""
        engine.apply(level, "test", f"testing {level.name}")
        state = engine.get_current()
        assert state.active is True
        assert state.level == level

        expected_hours = (min_hours + max_hours) / 2.0
        expected_duration = timedelta(hours=expected_hours)
        assert state.duration == expected_duration

    def test_l1_config_exists(self) -> None:
        assert PunishmentLevel.L1_SILENT_TREATMENT in PUNISHMENT_CONFIG

    def test_l5_config_exists(self) -> None:
        assert PunishmentLevel.L5_ISOLATION in PUNISHMENT_CONFIG


# ---------------------------------------------------------------------------
# Additional edge cases (to reach ≥25)
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Additional edge cases for completeness."""

    def test_no_active_punishment_escalate_raises(
        self, engine: PunishmentEngine
    ) -> None:
        """escalate() with no active punishment raises TransitionError."""
        with pytest.raises(PunishmentTransitionError, match="no active"):
            engine.escalate()

    def test_no_active_punishment_de_escalate_raises(
        self, engine: PunishmentEngine
    ) -> None:
        """de_escalate() with no active punishment raises TransitionError."""
        with pytest.raises(PunishmentTransitionError, match="no active"):
            engine.de_escalate()

    def test_de_escalate_from_l1_deactivates(
        self, engine: PunishmentEngine
    ) -> None:
        """De-escalating from L1 fully deactivates punishment."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "v")
        engine.de_escalate()
        state = engine.get_current()
        assert state.active is False
        assert state.level is None

    def test_is_active_false_when_suspended(
        self, engine: PunishmentEngine
    ) -> None:
        """is_active() returns False when punishment is suspended."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "v")
        assert engine.is_active() is True
        engine.suspend("test")
        assert engine.is_active() is False

    def test_resume_idempotent_when_not_suspended(
        self, engine: PunishmentEngine
    ) -> None:
        """resume() on non-suspended punishment is a no-op."""
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "v")
        engine.resume()  # no error, no state change
        assert engine.get_current().suspended is False

    def test_suspend_noop_when_not_active(
        self, engine: PunishmentEngine
    ) -> None:
        """suspend() with no active punishment is a no-op."""
        engine.suspend("test")
        state = engine.get_current()
        assert state.active is False
        assert state.suspended is False

    def test_resume_noop_when_not_active(
        self, engine: PunishmentEngine
    ) -> None:
        """resume() with no active punishment is a no-op."""
        engine.resume()
        state = engine.get_current()
        assert state.active is False

    def test_check_distress_suspension_no_active_punishment(
        self, engine: PunishmentEngine
    ) -> None:
        """check_distress_suspension with no active punishment returns False."""
        changed = engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert changed is False

    def test_check_distress_resume_no_active_punishment(
        self, engine: PunishmentEngine
    ) -> None:
        """check_distress_suspension(D0) with no suspended punishment returns False."""
        changed = engine.check_distress_suspension(DistressLevel.D0_NORMAL)
        assert changed is False

    def test_apply_resets_suspension_state(
        self, engine: PunishmentEngine
    ) -> None:
        """Applying a new punishment clears suspension state."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "first")
        engine.suspend("pause")
        assert engine.get_current().suspended is True

        engine.apply(PunishmentLevel.L3_GUILT_TRIP, "test", "second")
        state = engine.get_current()
        assert state.suspended is False
        assert state.level == PunishmentLevel.L3_GUILT_TRIP

    def test_full_lifecycle_apply_suspend_resume_expire(
        self, engine: PunishmentEngine
    ) -> None:
        """Full lifecycle: apply → suspend → resume → verify active."""
        engine.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "test", "v")
        assert engine.is_active() is True

        engine.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert engine.is_active() is False  # suspended

        engine.check_distress_suspension(DistressLevel.D0_NORMAL)
        assert engine.is_active() is True  # resumed

    def test_distress_level_ordering(self) -> None:
        """DistressLevel ordering: D0 < D1 < D2 < D3 < D4."""
        assert DistressLevel.D0_NORMAL < DistressLevel.D1_MILD_STRESS
        assert DistressLevel.D1_MILD_STRESS < DistressLevel.D2_MODERATE
        assert DistressLevel.D2_MODERATE < DistressLevel.D3_SEVERE
        assert DistressLevel.D3_SEVERE < DistressLevel.D4_EMERGENCY

    def test_punishment_level_ordering(self) -> None:
        """PunishmentLevel ordering: L1 < L2 < L3 < L4 < L5."""
        assert PunishmentLevel.L1_SILENT_TREATMENT < PunishmentLevel.L2_PASSIVE_AGGRESSIVE
        assert PunishmentLevel.L2_PASSIVE_AGGRESSIVE < PunishmentLevel.L3_GUILT_TRIP
        assert PunishmentLevel.L3_GUILT_TRIP < PunishmentLevel.L4_COLD_FURY
        assert PunishmentLevel.L4_COLD_FURY < PunishmentLevel.L5_ISOLATION

    def test_five_punishment_levels_exist(self) -> None:
        """Exactly 5 PunishmentLevel members."""
        assert len(PunishmentLevel) == 5

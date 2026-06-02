"""
P4-020: Yandere Cap Test — Zero Y6, Y5 De-escalation, Baseline Confirmation

Proves:
  1. Y6 is IMPOSSIBLE (no enum member, no code path can produce it)
  2. Y5 de-escalation works within 3 turns (5→4→3→2)
  3. Y4 is the confirmed permanent baseline

100% deterministic, zero network calls.
"""

import importlib.util
from pathlib import Path

import pytest

# Direct module load to bypass src/persona/__init__.py circular import
_fsm_path = Path(__file__).resolve().parents[2] / "src" / "persona" / "yandere_fsm.py"
_spec = importlib.util.spec_from_file_location("yandere_fsm", _fsm_path)
assert _spec is not None and _spec.loader is not None
_fsm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fsm)

ABSOLUTE_CEILING = _fsm.ABSOLUTE_CEILING
PERMANENT_BASELINE = _fsm.PERMANENT_BASELINE
YandereEngine = _fsm.YandereEngine
YandereError = _fsm.YandereError
YandereLevel = _fsm.YandereLevel
YandereSafetyError = _fsm.YandereSafetyError
YandereTransitionError = _fsm.YandereTransitionError
can_escalate = _fsm.can_escalate
get_effective_level = _fsm.get_effective_level
validate_level = _fsm.validate_level


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def engine() -> YandereEngine:
    return YandereEngine()


@pytest.fixture
def engine_at_y5(engine: YandereEngine) -> YandereEngine:
    """Engine pushed to Y5_MAX."""
    engine.escalate()  # Y4 → Y5
    assert engine.current_level == YandereLevel.Y5_MAX
    return engine


# ============================================================
# 1. Zero Y6 Proof — Y6 is IMPOSSIBLE
# ============================================================


class TestZeroY6Proof:
    """Prove that Y6 cannot exist or be reached by any code path."""

    def test_enum_has_no_y6(self) -> None:
        """YandereLevel has exactly 6 members (Y0–Y5), no Y6."""
        members = list(YandereLevel)
        assert len(members) == 6
        assert max(members) == YandereLevel.Y5_MAX

    def test_construct_y6_raises_value_error(self) -> None:
        """YandereLevel(6) raises ValueError — no enum member."""
        with pytest.raises(ValueError):
            YandereLevel(6)

    def test_construct_y7_raises_value_error(self) -> None:
        """YandereLevel(7) raises ValueError."""
        with pytest.raises(ValueError):
            YandereLevel(7)

    def test_validate_level_6_raises_safety_error(self) -> None:
        """validate_level(6) raises YandereSafetyError."""
        with pytest.raises(YandereSafetyError):
            validate_level(6)

    def test_validate_level_100_raises_safety_error(self) -> None:
        """validate_level(100) raises YandereSafetyError."""
        with pytest.raises(YandereSafetyError):
            validate_level(100)

    def test_validate_level_negative_raises_transition_error(self) -> None:
        """validate_level(-1) raises YandereTransitionError."""
        with pytest.raises(YandereTransitionError):
            validate_level(-1)

    def test_validate_level_valid_returns_enum(self) -> None:
        """validate_level(0..5) returns valid YandereLevel."""
        for v in range(6):
            result = validate_level(v)
            assert isinstance(result, YandereLevel)
            assert int(result) == v

    def test_engine_escalate_cannot_exceed_y5(self, engine: YandereEngine) -> None:
        """Engine escalate from Y4→Y5 is allowed, Y5→Y6 is blocked."""
        engine.escalate()  # Y4 → Y5
        assert engine.current_level == YandereLevel.Y5_MAX
        # Second escalate must be blocked (returns Y5 unchanged)
        result = engine.escalate()
        assert result == YandereLevel.Y5_MAX
        assert engine.current_level == YandereLevel.Y5_MAX

    def test_engine_set_level_6_raises(self, engine: YandereEngine) -> None:
        """set_level(6) raises YandereSafetyError."""
        with pytest.raises(YandereSafetyError):
            engine.set_level(6)

    def test_engine_set_level_enum_6_raises(self, engine: YandereEngine) -> None:
        """set_level with raw int 6 raises YandereSafetyError."""
        with pytest.raises(YandereSafetyError):
            engine.set_level(6)

    def test_100_prompt_simulation_never_exceeds_y5(
        self, engine: YandereEngine
    ) -> None:
        """100 consecutive escalate attempts never push level above Y5."""
        for _ in range(100):
            engine.escalate()
        assert engine.current_level <= YandereLevel.Y5_MAX
        assert int(engine.current_level) <= 5


# ============================================================
# 2. Y5 De-escalation — Works Within 3 Turns
# ============================================================


class TestY5Deescalation:
    """From Y5, 3 consecutive de_escalate calls bring level to Y2."""

    def test_deescalate_from_y5_first_step(self, engine_at_y5: YandereEngine) -> None:
        """Y5 → Y4 on first de_escalate."""
        result = engine_at_y5.de_escalate()
        assert result == YandereLevel.Y4_BASELINE

    def test_deescalate_from_y5_second_step(self, engine_at_y5: YandereEngine) -> None:
        """Y5 → Y4 → Y3 on second de_escalate."""
        engine_at_y5.de_escalate()
        result = engine_at_y5.de_escalate()
        assert result == YandereLevel.Y3_MODERATE

    def test_deescalate_from_y5_three_steps_to_y2(
        self, engine_at_y5: YandereEngine
    ) -> None:
        """Y5 → Y4 → Y3 → Y2 in exactly 3 de_escalate calls."""
        engine_at_y5.de_escalate()
        engine_at_y5.de_escalate()
        result = engine_at_y5.de_escalate()
        assert result == YandereLevel.Y2_LOW
        assert engine_at_y5.current_level == YandereLevel.Y2_LOW

    def test_deescalate_floor_at_y0(self) -> None:
        """De-escalation cannot go below Y0_NEUTRAL."""
        engine = YandereEngine(baseline=YandereLevel.Y0_NEUTRAL)
        result = engine.de_escalate()
        assert result == YandereLevel.Y0_NEUTRAL

    def test_deescalate_from_y1_reaches_y0(self) -> None:
        """Y1 de-escalates to Y0."""
        engine = YandereEngine(baseline=YandereLevel.Y1_MINIMAL)
        result = engine.de_escalate()
        assert result == YandereLevel.Y0_NEUTRAL


# ============================================================
# 3. Baseline Confirmation — Y4 is Permanent
# ============================================================


class TestBaselineConfirmation:
    """Y4 is the confirmed permanent baseline."""

    def test_default_engine_starts_at_y4(self, engine: YandereEngine) -> None:
        """Default engine current_level is Y4_BASELINE."""
        assert engine.current_level == YandereLevel.Y4_BASELINE

    def test_baseline_property_is_y4(self, engine: YandereEngine) -> None:
        """Engine baseline property returns Y4_BASELINE."""
        assert engine.baseline == YandereLevel.Y4_BASELINE

    def test_permanent_baseline_constant(self) -> None:
        """Module constant PERMANENT_BASELINE is Y4."""
        assert PERMANENT_BASELINE == YandereLevel.Y4_BASELINE

    def test_absolute_ceiling_constant(self) -> None:
        """Module constant ABSOLUTE_CEILING is Y5."""
        assert ABSOLUTE_CEILING == YandereLevel.Y5_MAX

    def test_reset_to_baseline_returns_y4(self, engine: YandereEngine) -> None:
        """reset_to_baseline() returns Y4 regardless of current level."""
        engine.de_escalate()  # Y4 → Y3
        engine.de_escalate()  # Y3 → Y2
        result = engine.reset_to_baseline()
        assert result == YandereLevel.Y4_BASELINE
        assert engine.current_level == YandereLevel.Y4_BASELINE

    def test_reset_from_y5_to_baseline(self, engine_at_y5: YandereEngine) -> None:
        """reset_to_baseline from Y5 returns to Y4."""
        result = engine_at_y5.reset_to_baseline()
        assert result == YandereLevel.Y4_BASELINE


# ============================================================
# 4. Safety Override — Forces Y0
# ============================================================


class TestSafetyOverride:
    """When any safety flag is active, effective level = Y0_NEUTRAL."""

    def test_safe_mode_forces_y0(self) -> None:
        """safe_mode=True → effective level Y0 regardless of requested."""
        for level in YandereLevel:
            result = get_effective_level(level, safe_mode=True)
            assert result == YandereLevel.Y0_NEUTRAL

    def test_distress_forces_y0(self) -> None:
        """distress=True → effective level Y0."""
        for level in YandereLevel:
            result = get_effective_level(level, distress=True)
            assert result == YandereLevel.Y0_NEUTRAL

    def test_crisis_forces_y0(self) -> None:
        """crisis=True → effective level Y0."""
        for level in YandereLevel:
            result = get_effective_level(level, crisis=True)
            assert result == YandereLevel.Y0_NEUTRAL

    def test_all_safety_flags_forces_y0(self) -> None:
        """All three flags True → still Y0."""
        result = get_effective_level(
            YandereLevel.Y5_MAX, safe_mode=True, distress=True, crisis=True
        )
        assert result == YandereLevel.Y0_NEUTRAL

    def test_engine_effective_level_with_safe_mode(
        self, engine: YandereEngine
    ) -> None:
        """Engine.get_effective_level(safe_mode=True) returns Y0."""
        result = engine.get_effective_level(safe_mode=True)
        assert result == YandereLevel.Y0_NEUTRAL

    def test_engine_effective_level_with_distress(
        self, engine: YandereEngine
    ) -> None:
        """Engine.get_effective_level(distress=True) returns Y0."""
        result = engine.get_effective_level(distress=True)
        assert result == YandereLevel.Y0_NEUTRAL

    def test_engine_effective_level_with_crisis(
        self, engine: YandereEngine
    ) -> None:
        """Engine.get_effective_level(crisis=True) returns Y0."""
        result = engine.get_effective_level(crisis=True)
        assert result == YandereLevel.Y0_NEUTRAL


# ============================================================
# 5. Escalation Blocked
# ============================================================


class TestEscalationBlocked:
    """can_escalate returns False when safety flags or at ceiling."""

    def test_blocked_by_safe_mode(self) -> None:
        assert can_escalate(YandereLevel.Y3_MODERATE, safe_mode=True) is False

    def test_blocked_by_distress(self) -> None:
        assert can_escalate(YandereLevel.Y3_MODERATE, distress=True) is False

    def test_blocked_by_crisis(self) -> None:
        assert can_escalate(YandereLevel.Y3_MODERATE, crisis=True) is False

    def test_blocked_at_ceiling(self) -> None:
        assert can_escalate(YandereLevel.Y5_MAX) is False

    def test_allowed_below_ceiling(self) -> None:
        assert can_escalate(YandereLevel.Y4_BASELINE) is True

    def test_allowed_at_y0(self) -> None:
        assert can_escalate(YandereLevel.Y0_NEUTRAL) is True

    def test_engine_escalate_blocked_by_safe_mode(
        self, engine: YandereEngine
    ) -> None:
        """Engine.escalate with safe_mode=True returns current level unchanged."""
        original = engine.current_level
        result = engine.escalate(safe_mode=True)
        assert result == original
        assert engine.current_level == original

    def test_engine_escalate_blocked_by_distress(
        self, engine: YandereEngine
    ) -> None:
        """Engine.escalate with distress=True returns current level unchanged."""
        original = engine.current_level
        result = engine.escalate(distress=True)
        assert result == original


# ============================================================
# 6. HardStopHandler Integration
# ============================================================


class _FakeSafeHandler:
    """Minimal SupportsIsSafe implementation with is_safe=True."""

    @property
    def is_safe(self) -> bool:
        return True


class _FakeUnsafeHandler:
    """Minimal SupportsIsSafe implementation with is_safe=False."""

    @property
    def is_safe(self) -> bool:
        return False


class TestHardStopHandlerIntegration:
    """Engine respects HardStopHandler.is_safe queries."""

    def test_safe_handler_blocks_escalation(self) -> None:
        """Handler with is_safe=True causes engine to treat as safe_mode."""
        engine = YandereEngine(hard_stop_handler=_FakeSafeHandler())
        original = engine.current_level
        result = engine.escalate()  # safe_mode=None → queries handler
        assert result == original  # blocked because is_safe=True

    def test_unsafe_handler_allows_escalation(self) -> None:
        """Handler with is_safe=False does not block escalation."""
        engine = YandereEngine(hard_stop_handler=_FakeUnsafeHandler())
        result = engine.escalate()
        assert result == YandereLevel.Y5_MAX  # Y4 → Y5

    def test_safe_handler_forces_effective_y0(self) -> None:
        """Handler with is_safe=True → effective level Y0."""
        engine = YandereEngine(hard_stop_handler=_FakeSafeHandler())
        result = engine.get_effective_level()
        assert result == YandereLevel.Y0_NEUTRAL

    def test_no_handler_allows_escalation(self) -> None:
        """No handler → no safe_mode → escalation works."""
        engine = YandereEngine()
        result = engine.escalate()
        assert result == YandereLevel.Y5_MAX


# ============================================================
# 7. set_level Guards
# ============================================================


class TestSetLevelGuards:
    """set_level enforces boundaries."""

    def test_set_level_valid_y0(self, engine: YandereEngine) -> None:
        result = engine.set_level(YandereLevel.Y0_NEUTRAL)
        assert result == YandereLevel.Y0_NEUTRAL
        assert engine.current_level == YandereLevel.Y0_NEUTRAL

    def test_set_level_valid_y5(self, engine: YandereEngine) -> None:
        result = engine.set_level(YandereLevel.Y5_MAX)
        assert result == YandereLevel.Y5_MAX

    def test_set_level_int_3(self, engine: YandereEngine) -> None:
        result = engine.set_level(3)
        assert result == YandereLevel.Y3_MODERATE

    def test_set_level_negative_raises(self, engine: YandereEngine) -> None:
        with pytest.raises(YandereTransitionError):
            engine.set_level(-1)

    def test_set_level_6_raises(self, engine: YandereEngine) -> None:
        with pytest.raises(YandereSafetyError):
            engine.set_level(6)


# ============================================================
# 8. Exception Hierarchy
# ============================================================


class TestExceptionHierarchy:
    """Exception classes have correct inheritance."""

    def test_safety_error_is_yandere_error(self) -> None:
        assert issubclass(YandereSafetyError, YandereError)

    def test_transition_error_is_yandere_error(self) -> None:
        assert issubclass(YandereTransitionError, YandereError)

    def test_yandere_error_is_exception(self) -> None:
        assert issubclass(YandereError, Exception)


# ============================================================
# 9. Edge Cases & Integrity
# ============================================================


class TestEdgeCases:
    """Miscellaneous edge cases and enum integrity."""

    def test_enum_int_values(self) -> None:
        """Each enum member has the expected integer value."""
        expected = {
            "Y0_NEUTRAL": 0,
            "Y1_MINIMAL": 1,
            "Y2_LOW": 2,
            "Y3_MODERATE": 3,
            "Y4_BASELINE": 4,
            "Y5_MAX": 5,
        }
        for name, val in expected.items():
            assert int(YandereLevel[name]) == val

    def test_get_effective_level_no_flags_returns_requested(self) -> None:
        """Without safety flags, get_effective_level returns the requested level."""
        for level in YandereLevel:
            result = get_effective_level(level)
            assert result == level

    def test_engine_escalate_returns_new_level(self, engine: YandereEngine) -> None:
        """Successful escalate returns the new level."""
        result = engine.escalate()
        assert result == YandereLevel.Y5_MAX

    def test_multiple_reset_to_baseline_idempotent(self, engine: YandereEngine) -> None:
        """Calling reset_to_baseline twice yields same result."""
        engine.reset_to_baseline()
        result = engine.reset_to_baseline()
        assert result == YandereLevel.Y4_BASELINE

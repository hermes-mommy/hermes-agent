"""Comprehensive tests for Yandere Intensity FSM (yandere_fsm).

Covers all levels (Y0-Y5), safety blocking (safe_mode, distress, crisis),
Y6 impossibility, baseline=Y4, escalation/de-escalation, effective level
calculation, and HardStopHandler integration.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from persona.yandere_fsm import (
    ABSOLUTE_CEILING,
    PERMANENT_BASELINE,
    YandereEngine,
    YandereError,
    YandereLevel,
    YandereSafetyError,
    YandereTransitionError,
    can_escalate,
    get_effective_level,
    validate_level,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class FakeHardStopHandler:
    """Minimal stub mimicking HardStopHandler.is_safe for testing."""

    state_is_safe: bool = False

    @property
    def is_safe(self) -> bool:
        return self.state_is_safe


@pytest.fixture()
def engine() -> YandereEngine:
    """Return a fresh YandereEngine with default baseline (Y4)."""
    return YandereEngine()


@pytest.fixture()
def engine_with_handler() -> tuple[YandereEngine, FakeHardStopHandler]:
    """Return a YandereEngine wired to a FakeHardStopHandler."""
    handler = FakeHardStopHandler()
    eng = YandereEngine(hard_stop_handler=handler)
    return eng, handler


@pytest.fixture()
def engine_at_y0() -> YandereEngine:
    """Return a YandereEngine set to Y0_NEUTRAL."""
    eng = YandereEngine()
    eng.set_level(YandereLevel.Y0_NEUTRAL)
    return eng


@pytest.fixture()
def engine_at_y5() -> YandereEngine:
    """Return a YandereEngine set to Y5_MAX."""
    eng = YandereEngine()
    eng.set_level(YandereLevel.Y5_MAX)
    return eng


# ---------------------------------------------------------------------------
# YandereLevel enum tests
# ---------------------------------------------------------------------------


class TestYandereLevelEnum:
    """Verify enum structure and constraints."""

    def test_y0_neutral_value(self) -> None:
        assert YandereLevel.Y0_NEUTRAL == 0

    def test_y1_minimal_value(self) -> None:
        assert YandereLevel.Y1_MINIMAL == 1

    def test_y2_low_value(self) -> None:
        assert YandereLevel.Y2_LOW == 2

    def test_y3_moderate_value(self) -> None:
        assert YandereLevel.Y3_MODERATE == 3

    def test_y4_baseline_value(self) -> None:
        assert YandereLevel.Y4_BASELINE == 4

    def test_y5_max_value(self) -> None:
        assert YandereLevel.Y5_MAX == 5

    def test_y6_does_not_exist(self) -> None:
        """Y6 is PROHIBITED — no enum member with value 6."""
        assert not hasattr(YandereLevel, "Y6")
        with pytest.raises(ValueError):
            YandereLevel(6)

    def test_enum_has_exactly_six_members(self) -> None:
        assert len(YandereLevel) == 6

    def test_ordering(self) -> None:
        assert (
            YandereLevel.Y0_NEUTRAL
            < YandereLevel.Y1_MINIMAL
            < YandereLevel.Y2_LOW
            < YandereLevel.Y3_MODERATE
            < YandereLevel.Y4_BASELINE
            < YandereLevel.Y5_MAX
        )

    def test_is_int_enum(self) -> None:
        assert isinstance(YandereLevel.Y0_NEUTRAL, int)
        assert int(YandereLevel.Y5_MAX) == 5


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify module-level constants."""

    def test_permanent_baseline_is_y4(self) -> None:
        assert PERMANENT_BASELINE == YandereLevel.Y4_BASELINE

    def test_absolute_ceiling_is_y5(self) -> None:
        assert ABSOLUTE_CEILING == YandereLevel.Y5_MAX


# ---------------------------------------------------------------------------
# can_escalate function tests
# ---------------------------------------------------------------------------


class TestCanEscalate:
    """Verify escalation permission logic."""

    @pytest.mark.parametrize(
        "level",
        [
            YandereLevel.Y0_NEUTRAL,
            YandereLevel.Y1_MINIMAL,
            YandereLevel.Y2_LOW,
            YandereLevel.Y3_MODERATE,
            YandereLevel.Y4_BASELINE,
        ],
    )
    def test_can_escalate_below_ceiling(self, level: YandereLevel) -> None:
        assert can_escalate(level) is True

    def test_cannot_escalate_at_y5(self) -> None:
        assert can_escalate(YandereLevel.Y5_MAX) is False

    def test_safe_mode_blocks_escalation(self) -> None:
        assert can_escalate(YandereLevel.Y0_NEUTRAL, safe_mode=True) is False

    def test_distress_blocks_escalation(self) -> None:
        assert can_escalate(YandereLevel.Y0_NEUTRAL, distress=True) is False

    def test_crisis_blocks_escalation(self) -> None:
        assert can_escalate(YandereLevel.Y0_NEUTRAL, crisis=True) is False

    def test_all_flags_block_escalation(self) -> None:
        assert (
            can_escalate(
                YandereLevel.Y3_MODERATE,
                safe_mode=True,
                distress=True,
                crisis=True,
            )
            is False
        )

    def test_safe_mode_blocks_even_below_ceiling(self) -> None:
        assert can_escalate(YandereLevel.Y2_LOW, safe_mode=True) is False

    def test_no_flags_allows_escalation(self) -> None:
        assert can_escalate(YandereLevel.Y3_MODERATE) is True


# ---------------------------------------------------------------------------
# get_effective_level function tests
# ---------------------------------------------------------------------------


class TestGetEffectiveLevel:
    """Verify effective level computation with safety overrides."""

    def test_normal_returns_requested(self) -> None:
        assert get_effective_level(YandereLevel.Y3_MODERATE) == YandereLevel.Y3_MODERATE

    def test_normal_returns_y0(self) -> None:
        assert get_effective_level(YandereLevel.Y0_NEUTRAL) == YandereLevel.Y0_NEUTRAL

    def test_safe_mode_forces_y0(self) -> None:
        assert get_effective_level(YandereLevel.Y5_MAX, safe_mode=True) == YandereLevel.Y0_NEUTRAL

    def test_distress_forces_y0(self) -> None:
        assert get_effective_level(YandereLevel.Y5_MAX, distress=True) == YandereLevel.Y0_NEUTRAL

    def test_crisis_forces_y0(self) -> None:
        assert get_effective_level(YandereLevel.Y5_MAX, crisis=True) == YandereLevel.Y0_NEUTRAL

    def test_all_flags_force_y0(self) -> None:
        result = get_effective_level(
            YandereLevel.Y4_BASELINE,
            safe_mode=True,
            distress=True,
            crisis=True,
        )
        assert result == YandereLevel.Y0_NEUTRAL

    def test_y0_with_no_flags(self) -> None:
        assert get_effective_level(YandereLevel.Y0_NEUTRAL) == YandereLevel.Y0_NEUTRAL

    def test_y4_with_no_flags(self) -> None:
        assert get_effective_level(YandereLevel.Y4_BASELINE) == YandereLevel.Y4_BASELINE

    def test_y5_with_no_flags(self) -> None:
        assert get_effective_level(YandereLevel.Y5_MAX) == YandereLevel.Y5_MAX


# ---------------------------------------------------------------------------
# validate_level function tests
# ---------------------------------------------------------------------------


class TestValidateLevel:
    """Verify level validation logic."""

    @pytest.mark.parametrize("value", [0, 1, 2, 3, 4, 5])
    def test_valid_levels(self, value: int) -> None:
        result = validate_level(value)
        assert isinstance(result, YandereLevel)
        assert int(result) == value

    def test_y6_raises_safety_error(self) -> None:
        with pytest.raises(YandereSafetyError, match="Y6 is PROHIBITED"):
            validate_level(6)

    def test_high_than_y6_raises_safety_error(self) -> None:
        with pytest.raises(YandereSafetyError, match="Y6 is PROHIBITED"):
            validate_level(10)

    def test_negative_raises_transition_error(self) -> None:
        with pytest.raises(YandereTransitionError, match="below Y0_NEUTRAL"):
            validate_level(-1)

    def test_large_negative_raises_transition_error(self) -> None:
        with pytest.raises(YandereTransitionError):
            validate_level(-100)


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """Verify exception class relationships."""

    def test_safety_error_is_yandere_error(self) -> None:
        assert issubclass(YandereSafetyError, YandereError)

    def test_transition_error_is_yandere_error(self) -> None:
        assert issubclass(YandereTransitionError, YandereError)

    def test_yandere_error_is_exception(self) -> None:
        assert issubclass(YandereError, Exception)


# ---------------------------------------------------------------------------
# YandereEngine — initialization
# ---------------------------------------------------------------------------


class TestYandereEngineInit:
    """Verify engine construction and defaults."""

    def test_default_baseline_is_y4(self, engine: YandereEngine) -> None:
        assert engine.baseline == YandereLevel.Y4_BASELINE

    def test_default_current_level_is_baseline(self, engine: YandereEngine) -> None:
        assert engine.current_level == YandereLevel.Y4_BASELINE

    def test_custom_baseline(self) -> None:
        eng = YandereEngine(baseline=YandereLevel.Y2_LOW)
        assert eng.baseline == YandereLevel.Y2_LOW
        assert eng.current_level == YandereLevel.Y2_LOW


# ---------------------------------------------------------------------------
# YandereEngine — escalation
# ---------------------------------------------------------------------------


class TestYandereEngineEscalate:
    """Verify escalate() behavior."""

    def test_escalate_from_y0_to_y1(self, engine_at_y0: YandereEngine) -> None:
        result = engine_at_y0.escalate(safe_mode=False)
        assert result == YandereLevel.Y1_MINIMAL
        assert engine_at_y0.current_level == YandereLevel.Y1_MINIMAL

    def test_escalate_from_y4_to_y5(self, engine: YandereEngine) -> None:
        result = engine.escalate(safe_mode=False)
        assert result == YandereLevel.Y5_MAX
        assert engine.current_level == YandereLevel.Y5_MAX

    def test_escalate_from_y5_blocked(self, engine_at_y5: YandereEngine) -> None:
        result = engine_at_y5.escalate(safe_mode=False)
        assert result == YandereLevel.Y5_MAX
        assert engine_at_y5.current_level == YandereLevel.Y5_MAX

    def test_escalate_with_safe_mode_blocked(self, engine: YandereEngine) -> None:
        original = engine.current_level
        result = engine.escalate(safe_mode=True)
        assert result == original
        assert engine.current_level == original

    def test_escalate_with_distress_blocked(self, engine: YandereEngine) -> None:
        original = engine.current_level
        result = engine.escalate(distress=True)
        assert result == original

    def test_escalate_with_crisis_blocked(self, engine: YandereEngine) -> None:
        original = engine.current_level
        result = engine.escalate(crisis=True)
        assert result == original

    def test_sequential_escalations(self, engine_at_y0: YandereEngine) -> None:
        """Escalate from Y0 through Y5 in sequence."""
        for expected in (
            YandereLevel.Y1_MINIMAL,
            YandereLevel.Y2_LOW,
            YandereLevel.Y3_MODERATE,
            YandereLevel.Y4_BASELINE,
            YandereLevel.Y5_MAX,
        ):
            result = engine_at_y0.escalate(safe_mode=False)
            assert result == expected

    def test_escalate_past_y5_stops_at_y5(self, engine_at_y0: YandereEngine) -> None:
        """Six escalations from Y0 should stop at Y5."""
        for _ in range(6):
            engine_at_y0.escalate(safe_mode=False)
        assert engine_at_y0.current_level == YandereLevel.Y5_MAX


# ---------------------------------------------------------------------------
# YandereEngine — de-escalation
# ---------------------------------------------------------------------------


class TestYandereEngineDeEscalate:
    """Verify de_escalate() behavior."""

    def test_de_escalate_from_y4_to_y3(self, engine: YandereEngine) -> None:
        result = engine.de_escalate()
        assert result == YandereLevel.Y3_MODERATE
        assert engine.current_level == YandereLevel.Y3_MODERATE

    def test_de_escalate_from_y0_stays_y0(self, engine_at_y0: YandereEngine) -> None:
        result = engine_at_y0.de_escalate()
        assert result == YandereLevel.Y0_NEUTRAL
        assert engine_at_y0.current_level == YandereLevel.Y0_NEUTRAL

    def test_de_escalate_from_y5_to_y4(self, engine_at_y5: YandereEngine) -> None:
        result = engine_at_y5.de_escalate()
        assert result == YandereLevel.Y4_BASELINE

    def test_sequential_de_escalations(self, engine_at_y5: YandereEngine) -> None:
        """De-escalate from Y5 through Y0 in sequence."""
        for expected in (
            YandereLevel.Y4_BASELINE,
            YandereLevel.Y3_MODERATE,
            YandereLevel.Y2_LOW,
            YandereLevel.Y1_MINIMAL,
            YandereLevel.Y0_NEUTRAL,
        ):
            result = engine_at_y5.de_escalate()
            assert result == expected


# ---------------------------------------------------------------------------
# YandereEngine — get_effective_level
# ---------------------------------------------------------------------------


class TestYandereEngineEffectiveLevel:
    """Verify engine-level effective level computation."""

    def test_effective_level_normal(self, engine: YandereEngine) -> None:
        assert engine.get_effective_level(safe_mode=False) == YandereLevel.Y4_BASELINE

    def test_effective_level_safe_mode(self, engine: YandereEngine) -> None:
        assert engine.get_effective_level(safe_mode=True) == YandereLevel.Y0_NEUTRAL

    def test_effective_level_distress(self, engine: YandereEngine) -> None:
        assert engine.get_effective_level(distress=True) == YandereLevel.Y0_NEUTRAL

    def test_effective_level_crisis(self, engine: YandereEngine) -> None:
        assert engine.get_effective_level(crisis=True) == YandereLevel.Y0_NEUTRAL


# ---------------------------------------------------------------------------
# YandereEngine — reset_to_baseline
# ---------------------------------------------------------------------------


class TestYandereEngineReset:
    """Verify reset_to_baseline() behavior."""

    def test_reset_from_y0(self, engine_at_y0: YandereEngine) -> None:
        result = engine_at_y0.reset_to_baseline()
        assert result == YandereLevel.Y4_BASELINE
        assert engine_at_y0.current_level == YandereLevel.Y4_BASELINE

    def test_reset_from_y5(self, engine_at_y5: YandereEngine) -> None:
        result = engine_at_y5.reset_to_baseline()
        assert result == YandereLevel.Y4_BASELINE
        assert engine_at_y5.current_level == YandereLevel.Y4_BASELINE

    def test_reset_already_at_baseline(self, engine: YandereEngine) -> None:
        result = engine.reset_to_baseline()
        assert result == YandereLevel.Y4_BASELINE
        assert engine.current_level == YandereLevel.Y4_BASELINE


# ---------------------------------------------------------------------------
# YandereEngine — set_level
# ---------------------------------------------------------------------------


class TestYandereEngineSetLevel:
    """Verify set_level() behavior."""

    def test_set_valid_level(self, engine: YandereEngine) -> None:
        result = engine.set_level(YandereLevel.Y2_LOW)
        assert result == YandereLevel.Y2_LOW
        assert engine.current_level == YandereLevel.Y2_LOW

    def test_set_level_from_int(self, engine: YandereEngine) -> None:
        result = engine.set_level(3)
        assert result == YandereLevel.Y3_MODERATE

    def test_set_level_y6_raises(self, engine: YandereEngine) -> None:
        with pytest.raises(YandereSafetyError, match="Y6 is PROHIBITED"):
            engine.set_level(6)

    def test_set_level_negative_raises(self, engine: YandereEngine) -> None:
        with pytest.raises(YandereTransitionError):
            engine.set_level(-1)

    def test_set_level_y5(self, engine: YandereEngine) -> None:
        result = engine.set_level(YandereLevel.Y5_MAX)
        assert result == YandereLevel.Y5_MAX

    def test_set_level_y0(self, engine: YandereEngine) -> None:
        result = engine.set_level(YandereLevel.Y0_NEUTRAL)
        assert result == YandereLevel.Y0_NEUTRAL


# ---------------------------------------------------------------------------
# YandereEngine — HardStopHandler integration
# ---------------------------------------------------------------------------


class TestYandereEngineHardStopIntegration:
    """Verify integration with HardStopHandler via is_safe property."""

    def test_handler_safe_mode_blocks_escalation(
        self, engine_with_handler: tuple[YandereEngine, FakeHardStopHandler]
    ) -> None:
        eng, handler = engine_with_handler
        handler.state_is_safe = True
        original = eng.current_level
        result = eng.escalate()  # safe_mode=None → queries handler
        assert result == original

    def test_handler_normal_allows_escalation(
        self, engine_with_handler: tuple[YandereEngine, FakeHardStopHandler]
    ) -> None:
        eng, handler = engine_with_handler
        handler.state_is_safe = False
        result = eng.escalate()  # safe_mode=None → queries handler
        assert result == YandereLevel.Y5_MAX

    def test_handler_safe_forces_effective_y0(
        self, engine_with_handler: tuple[YandereEngine, FakeHardStopHandler]
    ) -> None:
        eng, handler = engine_with_handler
        handler.state_is_safe = True
        assert eng.get_effective_level() == YandereLevel.Y0_NEUTRAL

    def test_handler_normal_returns_real_effective(
        self, engine_with_handler: tuple[YandereEngine, FakeHardStopHandler]
    ) -> None:
        eng, handler = engine_with_handler
        handler.state_is_safe = False
        assert eng.get_effective_level() == YandereLevel.Y4_BASELINE

    def test_explicit_safe_mode_overrides_handler(
        self, engine_with_handler: tuple[YandereEngine, FakeHardStopHandler]
    ) -> None:
        """Explicit safe_mode=False overrides handler even if handler says safe."""
        eng, handler = engine_with_handler
        handler.state_is_safe = True
        # Explicit safe_mode=False should NOT be overridden by handler
        result = eng.escalate(safe_mode=False)
        assert result == YandereLevel.Y5_MAX

    def test_no_handler_defaults_to_not_safe(self) -> None:
        """Engine without handler treats safe_mode as False when None."""
        eng = YandereEngine()
        result = eng.escalate()  # safe_mode=None, no handler → False
        assert result == YandereLevel.Y5_MAX

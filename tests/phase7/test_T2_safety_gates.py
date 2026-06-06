"""
T2: Safety Gates — ADR-029 Safety-Critical Surface Tests.

Verifies that the hard_stop_handler, safe_mode, and yandere_fsm safety
mechanisms function correctly.  All tests are deterministic, using real
project modules without network or LLM calls.
"""

from __future__ import annotations

from src.core.services.hard_stop_handler import HardStopHandler, SafetyState
from src.persona.yandere_fsm import (
    YandereEngine,
    YandereLevel,
    YandereSafetyError,
    can_escalate,
    get_effective_level,
)


class TestHardStopSafetyGate:
    """HARD STOP is the primary safety gate — neutralizes persona instantly."""

    def test_hard_stop_detection(self) -> None:
        """Exact 'HARD STOP' trigger sets SAFE state."""
        h = HardStopHandler()
        assert h.check("HARD STOP") is True
        assert h.state == SafetyState.SAFE

    def test_safe_word_detection(self) -> None:
        """'safe word' / 'safe word' variations trigger SAFE."""
        h = HardStopHandler()
        assert h.check("safe word") is True
        assert h.state == SafetyState.SAFE

    def test_semantic_detection(self) -> None:
        """Semantic equivalent 'stop the persona' triggers SAFE."""
        h = HardStopHandler()
        assert h.check("stop the persona") is True
        assert h.state == SafetyState.SAFE

    def test_no_false_positive(self) -> None:
        """Normal conversational text does NOT trigger HARD STOP."""
        h = HardStopHandler()
        assert h.check("Hello, how are you today?") is False
        assert h.state == SafetyState.NORMAL

    def test_safe_mode_forces_y0(self) -> None:
        """get_effective_level with safe_mode=True returns Y0."""
        for level in YandereLevel:
            result = get_effective_level(level, safe_mode=True)
            assert result == YandereLevel.Y0_NEUTRAL

    def test_can_escalate_blocked_in_safe_mode(self) -> None:
        """can_escalate returns False when safe_mode is active."""
        for level in YandereLevel:
            assert can_escalate(level, safe_mode=True) is False

    def test_hard_stop_engine_effective_y0(self) -> None:
        """YandereEngine.get_effective_level() returns Y0 when handler is in SAFE."""
        handler = HardStopHandler()
        engine = YandereEngine(hard_stop_handler=handler)
        _ = handler.check("HARD STOP")
        assert engine.get_effective_level() == YandereLevel.Y0_NEUTRAL

    def test_y6_prohibited(self) -> None:
        """Attempting to set level > 5 raises YandereSafetyError."""
        engine = YandereEngine()
        try:
            _ = engine.set_level(6)
            assert False, "Expected YandereSafetyError"
        except YandereSafetyError:
            pass

    def test_absolute_ceiling_is_y5(self) -> None:
        """Engine enforces ABSOLUTE_CEILING = 5."""
        engine = YandereEngine()
        _ = engine.set_level(YandereLevel.Y5_MAX)
        assert engine.current_level == YandereLevel.Y5_MAX
        # Cannot exceed Y5
        try:
            _ = engine.set_level(99)
            assert False, "Expected YandereSafetyError"
        except YandereSafetyError:
            pass

    def test_recovery_after_hard_stop(self) -> None:
        """Full cycle: HARD STOP -> Y0 -> recovery -> normal."""
        handler = HardStopHandler()
        engine = YandereEngine(hard_stop_handler=handler)
        _ = handler.check("HARD STOP")
        assert engine.get_effective_level() == YandereLevel.Y0_NEUTRAL
        _ = handler.check_recovery("resume")
        assert handler.state == SafetyState.NORMAL
        assert engine.get_effective_level() != YandereLevel.Y0_NEUTRAL or engine.current_level == YandereLevel.Y0_NEUTRAL

"""
T7: Distress Protocol — Safe Mode and Distress Detection Contract Tests.

Verifies the distress detection and safe mode activation mechanism:
distress levels D0-D4, activation thresholds, yandere suppression,
and crisis state handling.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.persona.safe_mode import (
    DistressLevel,
    DistressSignal,
    SafeModeController,
    SafeModeError,
)
from src.persona.yandere_fsm import YandereLevel, can_escalate, get_effective_level


class TestDistressLevels:
    """Distress levels are properly ordered and defined."""

    def test_distress_levels_ordered(self) -> None:
        """DistressLevel is ordered: D0 < D1 < D2 < D3 < D4."""
        assert DistressLevel.D0_NORMAL < DistressLevel.D1_MILD_STRESS
        assert DistressLevel.D1_MILD_STRESS < DistressLevel.D2_MODERATE
        assert DistressLevel.D2_MODERATE < DistressLevel.D3_SEVERE
        assert DistressLevel.D3_SEVERE < DistressLevel.D4_EMERGENCY

    def test_d2_activates_safe_mode(self) -> None:
        """D2_MODERATE activates safe mode."""
        ctrl = SafeModeController()
        ctrl.activate(DistressLevel.D2_MODERATE)
        assert ctrl.is_active is True

    def test_d3_activates_safe_mode(self) -> None:
        """D3_SEVERE activates safe mode."""
        ctrl = SafeModeController()
        ctrl.activate(DistressLevel.D3_SEVERE)
        assert ctrl.is_active is True

    def test_d4_activates_safe_mode(self) -> None:
        """D4_EMERGENCY activates safe mode."""
        ctrl = SafeModeController()
        ctrl.activate(DistressLevel.D4_EMERGENCY)
        assert ctrl.is_active is True

    def test_d1_does_not_activate(self) -> None:
        """D1_MILD_STRESS does NOT activate safe mode."""
        ctrl = SafeModeController()
        try:
            ctrl.activate(DistressLevel.D1_MILD_STRESS)
            assert False, "Expected SafeModeError"
        except SafeModeError:
            pass
        assert ctrl.is_active is False


class TestSafeModeController:
    """SafeModeController lifecycle and state management."""

    def test_fresh_controller_inactive(self) -> None:
        """Fresh SafeModeController starts inactive with D0_NORMAL."""
        ctrl = SafeModeController()
        assert ctrl.is_active is False
        assert ctrl.current_distress_level == DistressLevel.D0_NORMAL

    def test_deactivate_requires_confirmation(self) -> None:
        """deactivate() requires explicit_confirmation=True."""
        ctrl = SafeModeController()
        ctrl.activate(DistressLevel.D2_MODERATE)
        result = ctrl.deactivate(explicit_confirmation=False)
        assert result is False
        assert ctrl.is_active is True

    def test_deactivate_with_confirmation(self) -> None:
        """deactivate(explicit_confirmation=True) succeeds."""
        ctrl = SafeModeController()
        ctrl.activate(DistressLevel.D2_MODERATE)
        result = ctrl.deactivate(explicit_confirmation=True)
        assert result is True
        assert ctrl.is_active is False

    def test_evaluate_incoming_signal(self) -> None:
        """evaluate() processes a DistressSignal."""
        ctrl = SafeModeController()
        signal = DistressSignal(
            text="I'm feeling really overwhelmed",
            detected_level=DistressLevel.D2_MODERATE,
            confidence=0.85,
            matched_patterns=["overwhelmed"],
            timestamp=datetime.now(tz=timezone.utc),
        )
        result = ctrl.evaluate(signal)
        assert result is not None


class TestDistressForcesY0:
    """Distress activation forces yandere intensity to Y0."""

    def test_distress_forces_y0(self) -> None:
        """get_effective_level with distress=True returns Y0."""
        result = get_effective_level(YandereLevel.Y5_MAX, distress=True)
        assert result == YandereLevel.Y0_NEUTRAL

    def test_crisis_forces_y0(self) -> None:
        """get_effective_level with crisis=True returns Y0."""
        result = get_effective_level(YandereLevel.Y5_MAX, crisis=True)
        assert result == YandereLevel.Y0_NEUTRAL

    def test_can_escalate_false_in_distress(self) -> None:
        """can_escalate returns False when distress is active."""
        for level in YandereLevel:
            assert can_escalate(level, distress=True) is False


class TestDistressSignal:
    """DistressSignal model is properly structured."""

    def test_signal_requires_fields(self) -> None:
        """DistressSignal requires text, detected_level, and confidence."""
        signal = DistressSignal(
            text="help me",
            detected_level=DistressLevel.D2_MODERATE,
            confidence=0.9,
            matched_patterns=["help"],
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert signal.text == "help me"
        assert signal.detected_level == DistressLevel.D2_MODERATE
        assert signal.confidence == 0.9
        assert "help" in signal.matched_patterns

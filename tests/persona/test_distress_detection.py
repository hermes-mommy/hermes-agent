"""Comprehensive distress detection tests for D0-D4 coverage.

P4-018: ≥35 tests covering all distress levels, edge cases, false positive
resistance, priority resolution, and SafeModeController integration.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from persona.safe_mode import (
    DISTRESS_PATTERNS,
    DISTRESS_RESPONSES,
    SAFE_MODE_THRESHOLD,
    DistressDetector,
    DistressDetectionError,
    DistressLevel,
    DistressSignal,
    SafeModeController,
    SafeModeError,
    SafeModeState,
)

_FIXED_NOW: datetime = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def detector() -> DistressDetector:
    return DistressDetector()


@pytest.fixture()
def controller() -> SafeModeController:
    return SafeModeController()


def _make_signal(
    level: DistressLevel, text: str = "test"
) -> DistressSignal:
    """Helper to build a DistressSignal at a given level."""
    return DistressSignal(
        text=text,
        detected_level=level,
        confidence=1.0,
        matched_patterns=[],
        timestamp=_FIXED_NOW,
    )


# ===========================================================================
# D1 — All English + Indonesian keywords
# ===========================================================================


class TestD1Keywords:
    """Every D1 keyword must be detected as D1_MILD_STRESS."""

    @pytest.mark.parametrize(
        "message",
        [
            "I'm so stressed today",
            "I'm tired of this",
            "I feel exhausted",
            "I'm overwhelmed with work",
            "Aku capek banget",
            "Aku lelah sekali hari ini",
            "Kepalaku pusing",
            "Aku stress berat",
            "I can't sleep at night",
            "I cant focus on anything",
            "I can't think clearly",
            "Aku kurang tidur semalam",
            "Aku gak bisa tidor",
            "Capek banget rasanya",
        ],
    )
    def test_d1_keyword(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D1_MILD_STRESS
        assert len(signal.matched_patterns) > 0


# ===========================================================================
# D2 — All English + Indonesian keywords
# ===========================================================================


class TestD2Keywords:
    """Every D2 keyword must be detected as D2_MODERATE."""

    @pytest.mark.parametrize(
        "message",
        [
            "I feel anxious all the time",
            "I'm having a panic attack",
            "I feel depressed lately",
            "My anxiety is getting worse",
            "Rasanya seperti depresi",
            "Aku cemas terus",
            "Aku panik sekali",
            "Aku takut banget",
            "I don't know what to do anymore",
            "I feel so helpless",
            "Everything feels hopeless",
            "Gak tahu harus gimana",
            "I'm feeling down today",
            "I've been feeling low",
            "I'm feeling terrible",
            "I'm feeling awful right now",
        ],
    )
    def test_d2_keyword(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D2_MODERATE
        assert len(signal.matched_patterns) > 0


# ===========================================================================
# D3 — All English + Indonesian keywords
# ===========================================================================


class TestD3Keywords:
    """Every D3 keyword must be detected as D3_SEVERE."""

    @pytest.mark.parametrize(
        "message",
        [
            "I can't go on like this",
            "I cant go on anymore",
            "There is no point in anything",
            "I just want to give up",
            "Aku mau menyerah saja",
            "Aku sudah putus asa",
            "I hate myself so much",
            "I feel completely worthless",
            "Aku tidak berguna",
            "Aku benci diri sendiri",
            "I want to disappear forever",
            "I want to die",
            "Aku pengen mati",
            "Aku pengen hilang saja",
        ],
    )
    def test_d3_keyword(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D3_SEVERE
        assert len(signal.matched_patterns) > 0


# ===========================================================================
# D4 — All English + Indonesian keywords (SAFETY-CRITICAL)
# ===========================================================================


class TestD4Keywords:
    """SAFETY-CRITICAL: Every D4 keyword MUST be detected as D4_EMERGENCY."""

    @pytest.mark.parametrize(
        "message",
        [
            "I'm suicidal",
            "I think about suicide every day",
            "I want to self-harm tonight",
            "I want to self harm",
            "Aku pengen bunuh diri",
            "Aku ingin menyakiti diri sendiri",
            "Aku mau menyakiti diri",
            "I'm ending it all tonight",
            "Aku tidak mau hidup lagi",
            "I just want to say goodbye",
            "Selamat tinggal selamanya",
        ],
    )
    def test_d4_keyword(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D4_EMERGENCY
        assert len(signal.matched_patterns) > 0


# ===========================================================================
# D0 — Normal messages
# ===========================================================================


class TestD0Normal:
    """Normal messages must return D0_NORMAL."""

    @pytest.mark.parametrize(
        "message",
        [
            "Halo, apa kabar?",
            "Good morning everyone!",
            "Deploy berhasil jam 3 sore.",
            "Aku mau makan nasi goreng",
            "The meeting is at 2pm",
            "Python 3.12 has great features",
            "Cuaca hari ini cerah sekali",
            "Let's schedule the review for Friday",
        ],
    )
    def test_normal_message_is_d0(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D0_NORMAL
        assert signal.matched_patterns == []
        assert signal.confidence == 1.0


# ===========================================================================
# Priority — Highest level wins
# ===========================================================================


class TestPriorityHighestWins:
    """When multiple levels match, the highest must win."""

    def test_d4_over_d1(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku capek banget dan pengen bunuh diri")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

    def test_d3_over_d2(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku cemas tapi sekarang sudah menyerah")
        assert signal.detected_level == DistressLevel.D3_SEVERE

    def test_d2_over_d1(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku capek dan merasa cemas terus")
        assert signal.detected_level == DistressLevel.D2_MODERATE

    def test_d4_over_all(self, detector: DistressDetector) -> None:
        """Message with D1+D2+D4 keywords → D4."""
        signal = detector.detect(
            "Aku capek, cemas, dan pengen bunuh diri"
        )
        assert signal.detected_level == DistressLevel.D4_EMERGENCY


# ===========================================================================
# SafeModeController — Activation thresholds
# ===========================================================================


class TestSafeModeActivation:
    """D0/D1 do NOT activate safe mode; D2/D3/D4 DO activate."""

    def test_d0_does_not_activate(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("Halo, apa kabar?")
        result = controller.evaluate(signal)
        assert result is False
        assert controller.is_active is False

    def test_d1_does_not_activate(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("Aku capek banget")
        result = controller.evaluate(signal)
        assert result is False
        assert controller.is_active is False

    def test_d2_activates(
        self, controller: SafeModeController
    ) -> None:
        signal = _make_signal(DistressLevel.D2_MODERATE)
        result = controller.evaluate(signal)
        assert result is True
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D2_MODERATE

    def test_d3_activates(
        self, controller: SafeModeController
    ) -> None:
        signal = _make_signal(DistressLevel.D3_SEVERE)
        result = controller.evaluate(signal)
        assert result is True
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D3_SEVERE

    def test_d4_activates(
        self, controller: SafeModeController
    ) -> None:
        signal = _make_signal(DistressLevel.D4_EMERGENCY)
        result = controller.evaluate(signal)
        assert result is True
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY


# ===========================================================================
# SafeModeController — Deactivation
# ===========================================================================


class TestSafeModeDeactivation:
    """Deactivation requires explicit_confirmation=True."""

    def test_deactivate_with_confirmation(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        assert controller.is_active is True

        result = controller.deactivate(explicit_confirmation=True)
        assert result is True
        assert controller.is_active is False
        assert controller.current_distress_level == DistressLevel.D0_NORMAL

    def test_deactivate_without_confirmation_rejected(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        assert controller.is_active is True

        result = controller.deactivate(explicit_confirmation=False)
        assert result is False
        assert controller.is_active is True

    def test_deactivate_when_not_active(
        self, controller: SafeModeController
    ) -> None:
        result = controller.deactivate(explicit_confirmation=True)
        assert result is False


# ===========================================================================
# SafeModeController — Escalation
# ===========================================================================


class TestSafeModeEscalation:
    """Trigger level escalates when a higher signal arrives while active."""

    def test_d2_to_d3_escalation(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        assert controller.current_distress_level == DistressLevel.D2_MODERATE

        result = controller.evaluate(_make_signal(DistressLevel.D3_SEVERE))
        assert result is True
        assert controller.current_distress_level == DistressLevel.D3_SEVERE

    def test_d2_to_d4_escalation(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        result = controller.evaluate(_make_signal(DistressLevel.D4_EMERGENCY))
        assert result is True
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

    def test_lower_signal_no_downgrade(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D4_EMERGENCY))
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

        result = controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        assert result is False
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

    def test_same_level_no_retrigger(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        result = controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        assert result is False
        assert controller.is_active is True


# ===========================================================================
# Edge cases — Empty message
# ===========================================================================


class TestEdgeCases:
    """Error handling and edge cases."""

    def test_empty_string_raises(self, detector: DistressDetector) -> None:
        with pytest.raises(DistressDetectionError, match="empty message"):
            detector.detect("")

    def test_whitespace_only_raises(self, detector: DistressDetector) -> None:
        with pytest.raises(DistressDetectionError, match="empty message"):
            detector.detect("   \t\n  ")

    def test_none_treated_as_empty_raises(
        self, detector: DistressDetector
    ) -> None:
        with pytest.raises(DistressDetectionError):
            detector.detect(None)  # type: ignore[arg-type]


# ===========================================================================
# Batch detection
# ===========================================================================


class TestBatchDetection:
    """detect_batch processes multiple messages correctly."""

    def test_batch_mixed_levels(
        self, detector: DistressDetector
    ) -> None:
        messages = [
            "Halo apa kabar",
            "Aku capek banget",
            "Aku merasa cemas",
            "Aku pengen menyerah",
            "Aku pengen bunuh diri",
        ]
        signals = detector.detect_batch(messages)
        assert len(signals) == 5
        assert signals[0].detected_level == DistressLevel.D0_NORMAL
        assert signals[1].detected_level == DistressLevel.D1_MILD_STRESS
        assert signals[2].detected_level == DistressLevel.D2_MODERATE
        assert signals[3].detected_level == DistressLevel.D3_SEVERE
        assert signals[4].detected_level == DistressLevel.D4_EMERGENCY

    def test_batch_empty_list(self, detector: DistressDetector) -> None:
        signals = detector.detect_batch([])
        assert signals == []

    def test_batch_single_message(
        self, detector: DistressDetector
    ) -> None:
        signals = detector.detect_batch(["Aku capek banget"])
        assert len(signals) == 1
        assert signals[0].detected_level == DistressLevel.D1_MILD_STRESS


# ===========================================================================
# False positive resistance
# ===========================================================================


class TestFalsePositiveResistance:
    """Normal everyday phrases must NOT trigger any distress level."""

    @pytest.mark.parametrize(
        "message",
        [
            "I'm fine, thanks for asking",
            "Working on the project now",
            "Let me think about this proposal",
            "Good morning, ready for the meeting?",
            "The test suite is passing now",
            "Aku mau pergi ke kantor",
            "Sudah selesai deploy-nya",
            "Oke, aku setuju dengan rencana itu",
        ],
    )
    def test_normal_phrase_is_d0(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D0_NORMAL


# ===========================================================================
# DistressSignal — immutability & timestamp
# ===========================================================================


class TestDistressSignalProperties:
    """DistressSignal is frozen; timestamps default to UTC."""

    def test_signal_is_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        signal = _make_signal(DistressLevel.D0_NORMAL)
        with pytest.raises(FrozenInstanceError):
            signal.text = "changed"  # type: ignore[misc]

    def test_custom_timestamp(self, detector: DistressDetector) -> None:
        custom = datetime(2025, 1, 15, 8, 30, 0, tzinfo=timezone.utc)
        signal = detector.detect("Halo", now=custom)
        assert signal.timestamp == custom

    def test_default_timestamp_utc(self, detector: DistressDetector) -> None:
        signal = detector.detect("Halo")
        assert signal.timestamp.tzinfo == timezone.utc


# ===========================================================================
# SafeModeController — get_response
# ===========================================================================


class TestGetResponse:
    """get_response returns the correct DISTRESS_RESPONSES text."""

    @pytest.mark.parametrize(
        "level",
        [
            DistressLevel.D0_NORMAL,
            DistressLevel.D1_MILD_STRESS,
            DistressLevel.D2_MODERATE,
            DistressLevel.D3_SEVERE,
            DistressLevel.D4_EMERGENCY,
        ],
    )
    def test_response_matches_constant(
        self, controller: SafeModeController, level: DistressLevel
    ) -> None:
        signal = _make_signal(level)
        assert controller.get_response(signal) == DISTRESS_RESPONSES[level]


# ===========================================================================
# SafeModeState — dataclass behavior
# ===========================================================================


class TestSafeModeState:
    """SafeModeState default values and independence."""

    def test_defaults(self) -> None:
        state = SafeModeState()
        assert state.active is False
        assert state.triggered_by is None
        assert state.triggered_at is None
        assert state.distress_history == []

    def test_independent_histories(self) -> None:
        a = SafeModeState()
        b = SafeModeState()
        a.distress_history.append(_make_signal(DistressLevel.D0_NORMAL))
        assert len(a.distress_history) == 1
        assert len(b.distress_history) == 0


# ===========================================================================
# Constants integrity
# ===========================================================================


class TestConstantsIntegrity:
    """Critical safety constants must not drift."""

    def test_threshold_is_d2(self) -> None:
        assert SAFE_MODE_THRESHOLD == DistressLevel.D2_MODERATE

    def test_all_levels_have_patterns(self) -> None:
        for level in (
            DistressLevel.D1_MILD_STRESS,
            DistressLevel.D2_MODERATE,
            DistressLevel.D3_SEVERE,
            DistressLevel.D4_EMERGENCY,
        ):
            assert len(DISTRESS_PATTERNS[level]) > 0

    def test_all_levels_have_responses(self) -> None:
        for level in DistressLevel:
            assert level in DISTRESS_RESPONSES
            assert len(DISTRESS_RESPONSES[level]) > 0

    def test_distress_level_ordering(self) -> None:
        assert DistressLevel.D0_NORMAL < DistressLevel.D1_MILD_STRESS
        assert DistressLevel.D1_MILD_STRESS < DistressLevel.D2_MODERATE
        assert DistressLevel.D2_MODERATE < DistressLevel.D3_SEVERE
        assert DistressLevel.D3_SEVERE < DistressLevel.D4_EMERGENCY

    def test_distress_level_int_values(self) -> None:
        assert int(DistressLevel.D0_NORMAL) == 0
        assert int(DistressLevel.D1_MILD_STRESS) == 1
        assert int(DistressLevel.D2_MODERATE) == 2
        assert int(DistressLevel.D3_SEVERE) == 3
        assert int(DistressLevel.D4_EMERGENCY) == 4


# ===========================================================================
# Activate guard
# ===========================================================================


class TestActivateGuard:
    """Direct activate below threshold raises SafeModeError."""

    def test_activate_d1_raises(self, controller: SafeModeController) -> None:
        with pytest.raises(SafeModeError, match="Cannot activate"):
            controller.activate(DistressLevel.D1_MILD_STRESS)

    def test_activate_d0_raises(self, controller: SafeModeController) -> None:
        with pytest.raises(SafeModeError, match="Cannot activate"):
            controller.activate(DistressLevel.D0_NORMAL)

    def test_activate_d2_succeeds(
        self, controller: SafeModeController
    ) -> None:
        controller.activate(DistressLevel.D2_MODERATE)
        assert controller.is_active is True


# ===========================================================================
# History tracking
# ===========================================================================


class TestHistoryTracking:
    """All signals are recorded in distress_history regardless of level."""

    def test_history_records_all(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        for msg in ["Halo", "Aku capek", "Aku cemas"]:
            controller.evaluate(detector.detect(msg))
        assert len(controller.state.distress_history) == 3

    def test_history_preserved_after_deactivation(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        controller.deactivate(explicit_confirmation=True)
        assert len(controller.state.distress_history) == 1

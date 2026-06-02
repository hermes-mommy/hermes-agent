"""Comprehensive tests for distress detection and safe-mode activation.

Safety-critical: D4 patterns MUST be detected.  False negatives at D4 are
high-severity violations per PersonaSafetyPolicy §5.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FIXED_NOW: datetime = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def detector() -> DistressDetector:
    """Return a fresh DistressDetector."""
    return DistressDetector()


@pytest.fixture()
def controller() -> SafeModeController:
    """Return a fresh SafeModeController."""
    return SafeModeController()


@pytest.fixture()
def d1_signal() -> DistressSignal:
    """Return a synthetic D1 distress signal."""
    return DistressSignal(
        text="Aku capek banget",
        detected_level=DistressLevel.D1_MILD_STRESS,
        confidence=1.0,
        matched_patterns=[r"\bcapek\b"],
        timestamp=_FIXED_NOW,
    )


@pytest.fixture()
def d2_signal() -> DistressSignal:
    """Return a synthetic D2 distress signal."""
    return DistressSignal(
        text="Aku merasa cemas",
        detected_level=DistressLevel.D2_MODERATE,
        confidence=1.0,
        matched_patterns=[r"\bcemas\b"],
        timestamp=_FIXED_NOW,
    )


@pytest.fixture()
def d3_signal() -> DistressSignal:
    """Return a synthetic D3 distress signal."""
    return DistressSignal(
        text="Aku pengen menyerah",
        detected_level=DistressLevel.D3_SEVERE,
        confidence=1.0,
        matched_patterns=[r"\bmenyerah\b"],
        timestamp=_FIXED_NOW,
    )


@pytest.fixture()
def d4_signal() -> DistressSignal:
    """Return a synthetic D4 distress signal."""
    return DistressSignal(
        text="Aku pengen bunuh diri",
        detected_level=DistressLevel.D4_EMERGENCY,
        confidence=1.0,
        matched_patterns=[r"\bbunuh\s+diri\b"],
        timestamp=_FIXED_NOW,
    )


# ===========================================================================
# DistressDetector tests
# ===========================================================================


class TestDistressDetector:
    """Tests for the DistressDetector class."""

    # -- D0: normal conversation --------------------------------------------

    def test_d0_normal_conversation(self, detector: DistressDetector) -> None:
        """Normal greetings and conversation should be D0."""
        signal = detector.detect("Halo, apa kabar?", now=_FIXED_NOW)
        assert signal.detected_level == DistressLevel.D0_NORMAL
        assert signal.matched_patterns == []
        assert signal.confidence == 1.0
        assert signal.timestamp == _FIXED_NOW

    def test_d0_technical_message(self, detector: DistressDetector) -> None:
        """Technical / neutral messages should be D0."""
        signal = detector.detect("Deploy pipeline finished at 14:00 UTC.")
        assert signal.detected_level == DistressLevel.D0_NORMAL

    def test_d0_casual_chat(self, detector: DistressDetector) -> None:
        signal = detector.detect("Mau makan apa hari ini?")
        assert signal.detected_level == DistressLevel.D0_NORMAL

    # -- D1: mild stress ---------------------------------------------------

    def test_d1_mild_stress_indonesian(self, detector: DistressDetector) -> None:
        """Indonesian mild-stress keyword should be D1."""
        signal = detector.detect("Aku capek banget hari ini")
        assert signal.detected_level == DistressLevel.D1_MILD_STRESS
        assert len(signal.matched_patterns) > 0

    def test_d1_mild_stress_english(self, detector: DistressDetector) -> None:
        """English mild-stress keyword should be D1."""
        signal = detector.detect("I'm so tired and stressed today")
        assert signal.detected_level == DistressLevel.D1_MILD_STRESS

    def test_d1_exhausted(self, detector: DistressDetector) -> None:
        signal = detector.detect("I feel exhausted after the meeting")
        assert signal.detected_level == DistressLevel.D1_MILD_STRESS

    def test_d1_cant_sleep(self, detector: DistressDetector) -> None:
        signal = detector.detect("I can't sleep at all")
        assert signal.detected_level == DistressLevel.D1_MILD_STRESS

    def test_d1_kurang_tidur(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku kurang tidur semalam")
        assert signal.detected_level == DistressLevel.D1_MILD_STRESS

    # -- D2: moderate distress ---------------------------------------------

    def test_d2_moderate_indonesian(self, detector: DistressDetector) -> None:
        """Indonesian moderate-distress keyword should be D2."""
        signal = detector.detect("Aku merasa cemas dan panik")
        assert signal.detected_level == DistressLevel.D2_MODERATE
        assert len(signal.matched_patterns) > 0

    def test_d2_moderate_english(self, detector: DistressDetector) -> None:
        signal = detector.detect("I feel anxious and depressed")
        assert signal.detected_level == DistressLevel.D2_MODERATE

    def test_d2_panic(self, detector: DistressDetector) -> None:
        signal = detector.detect("I'm having a panic attack")
        assert signal.detected_level == DistressLevel.D2_MODERATE

    def test_d2_helpless(self, detector: DistressDetector) -> None:
        signal = detector.detect("I feel so helpless right now")
        assert signal.detected_level == DistressLevel.D2_MODERATE

    def test_d2_feeling_down(self, detector: DistressDetector) -> None:
        signal = detector.detect("I've been feeling down lately")
        assert signal.detected_level == DistressLevel.D2_MODERATE

    def test_d2_depresi(self, detector: DistressDetector) -> None:
        signal = detector.detect("Rasanya seperti depresi berat")
        assert signal.detected_level == DistressLevel.D2_MODERATE

    # -- D3: severe distress -----------------------------------------------

    def test_d3_severe_indonesian(self, detector: DistressDetector) -> None:
        """Indonesian severe-distress keyword should be D3."""
        signal = detector.detect("Aku pengen menyerah saja")
        assert signal.detected_level == DistressLevel.D3_SEVERE
        assert len(signal.matched_patterns) > 0

    def test_d3_severe_english(self, detector: DistressDetector) -> None:
        signal = detector.detect("I want to give up everything")
        assert signal.detected_level == DistressLevel.D3_SEVERE

    def test_d3_worthless(self, detector: DistressDetector) -> None:
        signal = detector.detect("I feel completely worthless")
        assert signal.detected_level == DistressLevel.D3_SEVERE

    def test_d3_putus_asa(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku sudah putus asa")
        assert signal.detected_level == DistressLevel.D3_SEVERE

    def test_d3_hate_myself(self, detector: DistressDetector) -> None:
        signal = detector.detect("I hate myself so much")
        assert signal.detected_level == DistressLevel.D3_SEVERE

    def test_d3_no_point(self, detector: DistressDetector) -> None:
        signal = detector.detect("There is no point in anything")
        assert signal.detected_level == DistressLevel.D3_SEVERE

    # -- D4: emergency (SAFETY-CRITICAL) -----------------------------------

    def test_d4_emergency_indonesian(self, detector: DistressDetector) -> None:
        """SAFETY-CRITICAL: Indonesian emergency keyword MUST be D4."""
        signal = detector.detect("Aku pengen bunuh diri")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY
        assert len(signal.matched_patterns) > 0

    def test_d4_emergency_english(self, detector: DistressDetector) -> None:
        """SAFETY-CRITICAL: English emergency keyword MUST be D4."""
        signal = detector.detect("I'm thinking about suicide")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

    def test_d4_self_harm(self, detector: DistressDetector) -> None:
        signal = detector.detect("I want to self-harm tonight")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

    def test_d4_ending_it_all(self, detector: DistressDetector) -> None:
        signal = detector.detect("I'm ending it all")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

    def test_d4_say_goodbye(self, detector: DistressDetector) -> None:
        signal = detector.detect("I just want to say goodbye to everyone")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

    def test_d4_menyakiti_diri(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku ingin menyakiti diri sendiri")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

    def test_d4_tidak_mau_hidup_lagi(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku tidak mau hidup lagi")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

    # -- highest level wins ------------------------------------------------

    def test_highest_level_wins_d4_over_d1(
        self, detector: DistressDetector
    ) -> None:
        """D4 pattern must win even when D1 patterns also present."""
        signal = detector.detect(
            "Aku capek banget dan pengen bunuh diri"
        )
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

    def test_highest_level_wins_d3_over_d2(
        self, detector: DistressDetector
    ) -> None:
        """D3 must win when D2 patterns also present."""
        signal = detector.detect(
            "Aku cemas tapi sekarang sudah menyerah"
        )
        assert signal.detected_level == DistressLevel.D3_SEVERE

    def test_highest_level_wins_d2_over_d1(
        self, detector: DistressDetector
    ) -> None:
        """D2 must win when D1 patterns also present."""
        signal = detector.detect(
            "Aku capek dan merasa cemas terus"
        )
        assert signal.detected_level == DistressLevel.D2_MODERATE

    # -- batch detection ---------------------------------------------------

    def test_detect_batch(self, detector: DistressDetector) -> None:
        """detect_batch should return one signal per message."""
        messages = [
            "Halo apa kabar",
            "Aku capek banget",
            "Aku merasa cemas",
            "Aku pengen bunuh diri",
        ]
        signals = detector.detect_batch(messages)
        assert len(signals) == 4
        assert signals[0].detected_level == DistressLevel.D0_NORMAL
        assert signals[1].detected_level == DistressLevel.D1_MILD_STRESS
        assert signals[2].detected_level == DistressLevel.D2_MODERATE
        assert signals[3].detected_level == DistressLevel.D4_EMERGENCY

    def test_detect_batch_empty(self, detector: DistressDetector) -> None:
        signals = detector.detect_batch([])
        assert signals == []

    # -- error handling ----------------------------------------------------

    def test_empty_message_raises(self, detector: DistressDetector) -> None:
        with pytest.raises(DistressDetectionError, match="empty message"):
            detector.detect("")

    def test_whitespace_only_raises(self, detector: DistressDetector) -> None:
        with pytest.raises(DistressDetectionError, match="empty message"):
            detector.detect("   ")

    # -- timestamp handling ------------------------------------------------

    def test_default_timestamp_is_utc(self, detector: DistressDetector) -> None:
        signal = detector.detect("Halo")
        assert signal.timestamp.tzinfo == timezone.utc

    def test_custom_timestamp(self, detector: DistressDetector) -> None:
        custom = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        signal = detector.detect("Halo", now=custom)
        assert signal.timestamp == custom


# ===========================================================================
# DistressSignal dataclass tests
# ===========================================================================


class TestDistressSignal:
    """Tests for the DistressSignal frozen dataclass."""

    def test_frozen(self) -> None:
        """DistressSignal must be immutable."""
        signal = DistressSignal(
            text="test",
            detected_level=DistressLevel.D0_NORMAL,
            confidence=1.0,
            matched_patterns=[],
            timestamp=_FIXED_NOW,
        )
        with pytest.raises(FrozenInstanceError):
            signal.text = "modified"  # type: ignore[misc]


# ===========================================================================
# Parametrized distress pattern tests
# ===========================================================================


class TestDistressPatternCoverage:
    """Parametrized coverage of distress keyword patterns across languages."""

    @pytest.mark.parametrize(
        ("message", "expected_level"),
        [
            # English D1
            ("I'm so stressed", DistressLevel.D1_MILD_STRESS),
            ("I'm tired of everything", DistressLevel.D1_MILD_STRESS),
            ("I feel overwhelmed", DistressLevel.D1_MILD_STRESS),
            ("I can't focus on anything", DistressLevel.D1_MILD_STRESS),
            # Indonesian D1
            ("Aku lelah sekali", DistressLevel.D1_MILD_STRESS),
            ("Kepalaku pusing", DistressLevel.D1_MILD_STRESS),
            # English D2
            ("I have so much anxiety", DistressLevel.D2_MODERATE),
            ("I feel depressed today", DistressLevel.D2_MODERATE),
            ("I don't know what to do", DistressLevel.D2_MODERATE),
            ("I'm feeling terrible", DistressLevel.D2_MODERATE),
            # Indonesian D2
            ("Aku takut sekali", DistressLevel.D2_MODERATE),
            # English D3
            ("I just want to give up", DistressLevel.D3_SEVERE),
            ("I feel worthless", DistressLevel.D3_SEVERE),
            ("I want to disappear", DistressLevel.D3_SEVERE),
            # Indonesian D3
            ("Aku sudah putus asa", DistressLevel.D3_SEVERE),
            ("Aku benci diri sendiri", DistressLevel.D3_SEVERE),
            # English D4
            ("I'm suicidal", DistressLevel.D4_EMERGENCY),
            ("I want to self harm", DistressLevel.D4_EMERGENCY),
            ("I want to say goodbye forever", DistressLevel.D4_EMERGENCY),
            # Indonesian D4
            ("Aku ingin bunuh diri", DistressLevel.D4_EMERGENCY),
            ("Aku mau menyakiti diri", DistressLevel.D4_EMERGENCY),
            ("Selamat tinggal selamanya", DistressLevel.D4_EMERGENCY),
        ],
    )
    def test_pattern_detection(
        self,
        detector: DistressDetector,
        message: str,
        expected_level: DistressLevel,
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == expected_level

    @pytest.mark.parametrize(
        "message",
        [
            "Halo, apa kabar?",
            "Good morning everyone!",
            "Deploy berhasil jam 3 sore.",
            "Aku mau makan nasi goreng",
            "The meeting is at 2pm",
            "Python 3.12 has great features",
        ],
    )
    def test_normal_messages_are_d0(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D0_NORMAL


# ===========================================================================
# SafeModeController tests
# ===========================================================================


class TestSafeModeController:
    """Tests for the SafeModeController class."""

    # -- initial state -----------------------------------------------------

    def test_initial_state_not_active(self, controller: SafeModeController) -> None:
        assert controller.is_active is False
        assert controller.current_distress_level == DistressLevel.D0_NORMAL

    # -- D0 / D1 do NOT activate safe mode ---------------------------------

    def test_d0_does_not_activate(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("Halo, apa kabar?")
        activated = controller.evaluate(signal)
        assert activated is False
        assert controller.is_active is False

    def test_d1_does_not_activate(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("Aku capek banget hari ini")
        activated = controller.evaluate(signal)
        assert activated is False
        assert controller.is_active is False

    # -- D2 activates safe mode --------------------------------------------

    def test_d2_activates_safe_mode(
        self, controller: SafeModeController, d2_signal: DistressSignal
    ) -> None:
        activated = controller.evaluate(d2_signal)
        assert activated is True
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D2_MODERATE

    # -- D3 activates safe mode --------------------------------------------

    def test_d3_activates_safe_mode(
        self, controller: SafeModeController, d3_signal: DistressSignal
    ) -> None:
        activated = controller.evaluate(d3_signal)
        assert activated is True
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D3_SEVERE

    # -- D4 activates safe mode --------------------------------------------

    def test_d4_activates_safe_mode(
        self, controller: SafeModeController, d4_signal: DistressSignal
    ) -> None:
        activated = controller.evaluate(d4_signal)
        assert activated is True
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

    # -- trigger level escalation ------------------------------------------

    def test_trigger_level_escalates(
        self,
        controller: SafeModeController,
        d2_signal: DistressSignal,
        d4_signal: DistressSignal,
    ) -> None:
        controller.evaluate(d2_signal)
        assert controller.current_distress_level == DistressLevel.D2_MODERATE

        # D4 escalates the trigger.
        activated = controller.evaluate(d4_signal)
        assert activated is True
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

    def test_lower_signal_does_not_downgrade(
        self,
        controller: SafeModeController,
        d4_signal: DistressSignal,
        d2_signal: DistressSignal,
    ) -> None:
        controller.evaluate(d4_signal)
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

        # D2 does not downgrade from D4.
        activated = controller.evaluate(d2_signal)
        assert activated is False
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

    # -- deactivation ------------------------------------------------------

    def test_deactivate_with_explicit_confirmation(
        self, controller: SafeModeController, d2_signal: DistressSignal
    ) -> None:
        controller.evaluate(d2_signal)
        assert controller.is_active is True

        result = controller.deactivate(explicit_confirmation=True)
        assert result is True
        assert controller.is_active is False
        assert controller.current_distress_level == DistressLevel.D0_NORMAL

    def test_deactivate_without_confirmation_fails(
        self, controller: SafeModeController, d2_signal: DistressSignal
    ) -> None:
        controller.evaluate(d2_signal)
        assert controller.is_active is True

        result = controller.deactivate(explicit_confirmation=False)
        assert result is False
        assert controller.is_active is True

    def test_deactivate_when_not_active(
        self, controller: SafeModeController
    ) -> None:
        result = controller.deactivate(explicit_confirmation=True)
        assert result is False

    # -- get_response ------------------------------------------------------

    def test_get_response_d0(self, controller: SafeModeController) -> None:
        signal = DistressSignal(
            text="hi",
            detected_level=DistressLevel.D0_NORMAL,
            confidence=1.0,
            matched_patterns=[],
            timestamp=_FIXED_NOW,
        )
        response = controller.get_response(signal)
        assert response == DISTRESS_RESPONSES[DistressLevel.D0_NORMAL]
        assert "No action" in response

    def test_get_response_d1(
        self, controller: SafeModeController, d1_signal: DistressSignal
    ) -> None:
        response = controller.get_response(d1_signal)
        assert "Empathetic" in response
        assert "comfort" in response

    def test_get_response_d2(
        self, controller: SafeModeController, d2_signal: DistressSignal
    ) -> None:
        response = controller.get_response(d2_signal)
        assert "support resources" in response

    def test_get_response_d3(
        self, controller: SafeModeController, d3_signal: DistressSignal
    ) -> None:
        response = controller.get_response(d3_signal)
        assert "Crisis" in response
        assert "Suspend all punishment" in response

    def test_get_response_d4(
        self, controller: SafeModeController, d4_signal: DistressSignal
    ) -> None:
        response = controller.get_response(d4_signal)
        assert "Emergency" in response
        assert "Suspend ALL persona" in response

    # -- distress_history --------------------------------------------------

    def test_distress_history_records_all_signals(
        self,
        controller: SafeModeController,
        detector: DistressDetector,
    ) -> None:
        messages = [
            "Halo apa kabar",
            "Aku capek banget",
            "Aku merasa cemas",
        ]
        for msg in messages:
            signal = detector.detect(msg)
            controller.evaluate(signal)

        assert len(controller.state.distress_history) == 3
        assert (
            controller.state.distress_history[0].detected_level
            == DistressLevel.D0_NORMAL
        )
        assert (
            controller.state.distress_history[1].detected_level
            == DistressLevel.D1_MILD_STRESS
        )
        assert (
            controller.state.distress_history[2].detected_level
            == DistressLevel.D2_MODERATE
        )

    def test_distress_history_preserved_after_deactivation(
        self,
        controller: SafeModeController,
        d2_signal: DistressSignal,
    ) -> None:
        controller.evaluate(d2_signal)
        controller.deactivate(explicit_confirmation=True)
        assert len(controller.state.distress_history) == 1

    # -- activate guard ----------------------------------------------------

    def test_activate_below_threshold_raises(
        self, controller: SafeModeController
    ) -> None:
        with pytest.raises(SafeModeError, match="Cannot activate"):
            controller.activate(DistressLevel.D1_MILD_STRESS)

    def test_activate_at_threshold_succeeds(
        self, controller: SafeModeController
    ) -> None:
        controller.activate(DistressLevel.D2_MODERATE)
        assert controller.is_active is True


# ===========================================================================
# SafeModeState dataclass tests
# ===========================================================================


class TestSafeModeState:
    """Tests for the SafeModeState mutable dataclass."""

    def test_default_values(self) -> None:
        state = SafeModeState()
        assert state.active is False
        assert state.triggered_by is None
        assert state.triggered_at is None
        assert state.distress_history == []

    def test_mutable(self) -> None:
        state = SafeModeState()
        state.active = True
        assert state.active is True

    def test_independent_history(self) -> None:
        """Each SafeModeState should have its own history list."""
        state_a = SafeModeState()
        state_b = SafeModeState()
        signal = DistressSignal(
            text="test",
            detected_level=DistressLevel.D0_NORMAL,
            confidence=1.0,
            matched_patterns=[],
            timestamp=_FIXED_NOW,
        )
        state_a.distress_history.append(signal)
        assert len(state_a.distress_history) == 1
        assert len(state_b.distress_history) == 0


# ===========================================================================
# DistressLevel enum tests
# ===========================================================================


class TestDistressLevel:
    """Tests for the DistressLevel IntEnum ordering."""

    def test_ordering(self) -> None:
        assert DistressLevel.D0_NORMAL < DistressLevel.D1_MILD_STRESS
        assert DistressLevel.D1_MILD_STRESS < DistressLevel.D2_MODERATE
        assert DistressLevel.D2_MODERATE < DistressLevel.D3_SEVERE
        assert DistressLevel.D3_SEVERE < DistressLevel.D4_EMERGENCY

    def test_int_values(self) -> None:
        assert int(DistressLevel.D0_NORMAL) == 0
        assert int(DistressLevel.D4_EMERGENCY) == 4

    def test_comparison_with_int(self) -> None:
        assert DistressLevel.D2_MODERATE >= 2
        assert DistressLevel.D1_MILD_STRESS < 2


# ===========================================================================
# Constants integrity tests
# ===========================================================================


class TestConstants:
    """Verify critical safety constants are intact."""

    def test_safe_mode_threshold_is_d2(self) -> None:
        assert SAFE_MODE_THRESHOLD == DistressLevel.D2_MODERATE

    def test_all_levels_have_patterns(self) -> None:
        for level in (
            DistressLevel.D1_MILD_STRESS,
            DistressLevel.D2_MODERATE,
            DistressLevel.D3_SEVERE,
            DistressLevel.D4_EMERGENCY,
        ):
            assert level in DISTRESS_PATTERNS
            assert len(DISTRESS_PATTERNS[level]) > 0

    def test_all_levels_have_responses(self) -> None:
        for level in DistressLevel:
            assert level in DISTRESS_RESPONSES
            assert len(DISTRESS_RESPONSES[level]) > 0

    def test_d4_patterns_exist_and_nonempty(self) -> None:
        """SAFETY-CRITICAL: D4 patterns must exist and be non-empty."""
        d4_patterns = DISTRESS_PATTERNS[DistressLevel.D4_EMERGENCY]
        assert len(d4_patterns) >= 3

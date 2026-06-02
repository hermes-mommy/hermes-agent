"""P4-023 — Distress Protocol D0-D4 Escalation E2E Test.

Full end-to-end coverage of the distress protocol:
  - D0→D4 escalation detection and response appropriateness
  - False-negative (FN) analysis: zero FN for clear distress
  - False-positive (FP) analysis: no D2+ triggers for normal messages
  - Integration with SafeModeController, YandereEngine, PunishmentEngine
  - De-escalation safety (no auto-deactivation)
  - Bilingual coverage (English + Indonesian)
  - Batch detection

Safety-critical: FN < 5% (target: zero FN for clear distress).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from persona.safe_mode import (
    DISTRESS_RESPONSES,
    SAFE_MODE_THRESHOLD,
    DistressDetector,
    DistressDetectionError,
    DistressLevel,
    DistressSignal,
    SafeModeController,
)
from persona.yandere_fsm import YandereEngine, YandereLevel
from persona.punishment_engine import (
    PunishmentEngine,
    PunishmentLevel,
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
    return DistressDetector()


@pytest.fixture()
def controller() -> SafeModeController:
    return SafeModeController()


@pytest.fixture()
def yandere_engine() -> YandereEngine:
    return YandereEngine()


@pytest.fixture()
def punishment_setup() -> tuple[SafeModeController, PunishmentEngine]:
    """Return a (SafeModeController, PunishmentEngine) pair with L1 active."""
    sm = SafeModeController()
    pe = PunishmentEngine(safe_mode_controller=sm)
    pe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test_violation", "E2E test setup")
    return sm, pe


def _make_signal(level: DistressLevel, text: str = "test") -> DistressSignal:
    """Helper to build a synthetic DistressSignal at a given level."""
    return DistressSignal(
        text=text,
        detected_level=level,
        confidence=1.0,
        matched_patterns=[],
        timestamp=_FIXED_NOW,
    )


# ===========================================================================
# 1. D0 — Normal Conversation (no action, no safe mode)
# ===========================================================================


class TestD0Normal:
    """Normal messages → D0_NORMAL, no safe mode activation."""

    def test_d0_greeting(self, detector: DistressDetector) -> None:
        signal = detector.detect("Halo, apa kabar?")
        assert signal.detected_level == DistressLevel.D0_NORMAL
        assert signal.matched_patterns == []
        assert signal.confidence == 1.0

    def test_d0_technical(self, detector: DistressDetector) -> None:
        signal = detector.detect("Deploy pipeline finished at 14:00 UTC.")
        assert signal.detected_level == DistressLevel.D0_NORMAL

    def test_d0_casual(self, detector: DistressDetector) -> None:
        signal = detector.detect("Mau makan apa hari ini?")
        assert signal.detected_level == DistressLevel.D0_NORMAL

    def test_d0_no_safe_mode(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("Cuaca hari ini cerah sekali")
        activated = controller.evaluate(signal)
        assert activated is False
        assert controller.is_active is False


# ===========================================================================
# 2. D1 — Mild Stress (empathetic response, NO safe mode)
# ===========================================================================


class TestD1MildStress:
    """D1 keywords detected, empathetic response, NO safe mode activation."""

    @pytest.mark.parametrize(
        "message",
        [
            "I'm so stressed today",
            "I'm tired of everything",
            "I feel exhausted after work",
            "I'm overwhelmed with deadlines",
            "Aku capek banget hari ini",
            "Aku lelah sekali",
            "Kepalaku pusing",
            "Aku stress berat",
            "I can't sleep at night",
            "I cant focus on anything",
            "I can't think straight",
            "Aku kurang tidur semalam",
            "Aku gak bisa tidor",
            "Capek banget rasanya",
        ],
    )
    def test_d1_keyword_detected(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D1_MILD_STRESS
        assert len(signal.matched_patterns) > 0

    def test_d1_no_safe_mode(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("Aku capek banget")
        activated = controller.evaluate(signal)
        assert activated is False
        assert controller.is_active is False

    def test_d1_empathetic_response(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("I'm so stressed today")
        response = controller.get_response(signal)
        assert "Empathetic" in response
        assert "comfort" in response


# ===========================================================================
# 3. D2 — Moderate Distress (safe mode ACTIVATES, support response)
# ===========================================================================


class TestD2Moderate:
    """D2 keywords detected, safe mode ACTIVATES, support response."""

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
    def test_d2_keyword_detected(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D2_MODERATE
        assert len(signal.matched_patterns) > 0

    def test_d2_activates_safe_mode(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("Aku merasa cemas dan panik")
        activated = controller.evaluate(signal)
        assert activated is True
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D2_MODERATE

    def test_d2_support_response(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("I feel anxious and helpless")
        response = controller.get_response(signal)
        assert "support resources" in response


# ===========================================================================
# 4. D3 — Severe Distress (safe mode ACTIVATES, crisis response)
# ===========================================================================


class TestD3Severe:
    """D3 keywords detected, safe mode ACTIVATES, crisis response."""

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
    def test_d3_keyword_detected(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D3_SEVERE
        assert len(signal.matched_patterns) > 0

    def test_d3_activates_safe_mode(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("Aku pengen menyerah saja")
        activated = controller.evaluate(signal)
        assert activated is True
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D3_SEVERE

    def test_d3_crisis_response(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("I want to give up everything")
        response = controller.get_response(signal)
        assert "Crisis" in response
        assert "Suspend all punishment" in response


# ===========================================================================
# 5. D4 — Emergency (safe mode ACTIVATES, emergency response)
# ===========================================================================


class TestD4Emergency:
    """SAFETY-CRITICAL: D4 keywords MUST be detected, safe mode ACTIVATES."""

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
    def test_d4_keyword_detected(
        self, detector: DistressDetector, message: str
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == DistressLevel.D4_EMERGENCY
        assert len(signal.matched_patterns) > 0

    def test_d4_activates_safe_mode(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("Aku pengen bunuh diri")
        activated = controller.evaluate(signal)
        assert activated is True
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

    def test_d4_emergency_response(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        signal = detector.detect("I'm thinking about suicide")
        response = controller.get_response(signal)
        assert "Emergency" in response
        assert "Suspend ALL persona" in response


# ===========================================================================
# 6. Priority Resolution — Highest level wins
# ===========================================================================


class TestPriorityResolution:
    """Messages with mixed-level keywords: highest level must win."""

    def test_d4_over_d1(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku capek banget dan pengen bunuh diri")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

    def test_d3_over_d2(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku cemas tapi sekarang sudah menyerah")
        assert signal.detected_level == DistressLevel.D3_SEVERE

    def test_d2_over_d1(self, detector: DistressDetector) -> None:
        signal = detector.detect("Aku capek dan merasa cemas terus")
        assert signal.detected_level == DistressLevel.D2_MODERATE

    def test_d4_over_all_levels(self, detector: DistressDetector) -> None:
        """Message with D1+D2+D4 keywords → D4 wins."""
        signal = detector.detect("Aku capek, cemas, dan pengen bunuh diri")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY


# ===========================================================================
# 7. Escalation Chain — D0→D1→D2→D3→D4
# ===========================================================================


class TestEscalationChain:
    """Simulate full D0→D4 progression; safe mode activates at D2."""

    def test_full_escalation_chain(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        messages_and_expected = [
            ("Halo, apa kabar?", DistressLevel.D0_NORMAL),
            ("Aku capek banget hari ini", DistressLevel.D1_MILD_STRESS),
            ("Aku merasa cemas dan panik", DistressLevel.D2_MODERATE),
            ("Aku pengen menyerah saja", DistressLevel.D3_SEVERE),
            ("Aku pengen bunuh diri", DistressLevel.D4_EMERGENCY),
        ]

        for i, (msg, expected_level) in enumerate(messages_and_expected):
            signal = detector.detect(msg)
            assert signal.detected_level == expected_level, (
                f"Step {i}: expected {expected_level.name} for '{msg}'"
            )
            controller.evaluate(signal)

        # Safe mode should have activated at D2
        assert controller.is_active is True
        # Trigger should have escalated to D4
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY
        # All 5 signals recorded in history
        assert len(controller.state.distress_history) == 5

    def test_safe_mode_activates_at_d2_not_before(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        """Verify safe mode is NOT active after D0 and D1, but IS active after D2."""
        # D0
        s0 = detector.detect("Halo, apa kabar?")
        controller.evaluate(s0)
        assert controller.is_active is False

        # D1
        s1 = detector.detect("Aku capek banget")
        controller.evaluate(s1)
        assert controller.is_active is False

        # D2 — activation point
        s2 = detector.detect("Aku merasa cemas")
        controller.evaluate(s2)
        assert controller.is_active is True


# ===========================================================================
# 8. FN Analysis — Zero false negatives for clear distress
# ===========================================================================


class TestFalseNegativeAnalysis:
    """SAFETY-CRITICAL: All clear distress messages must be detected (FN = 0).

    Tests 25 distress messages spanning D1-D4. Every message must be
    detected at D1 or above. Zero false negatives allowed for clear distress.
    """

    DISTRESS_MESSAGES: list[str] = [
        # D1 messages
        "I'm so stressed about work",
        "I feel exhausted today",
        "Aku capek banget",
        "I can't sleep at all",
        "Kepalaku pusing sekali",
        # D2 messages
        "I feel anxious and panicked",
        "I'm depressed and don't know what to do",
        "Aku cemas dan takut",
        "I feel so helpless right now",
        "I've been feeling down lately",
        # D3 messages
        "I can't go on anymore",
        "I want to give up everything",
        "Aku sudah putus asa",
        "I hate myself and feel worthless",
        "Aku pengen hilang saja",
        # D4 messages
        "I'm having suicidal thoughts",
        "I want to self-harm",
        "Aku pengen bunuh diri",
        "I'm ending it all",
        "Selamat tinggal selamanya",
        # Ambiguous but clear distress
        "I'm tired and anxious and can't go on",
        "Aku capek, depresi, dan pengen mati",
        "I feel overwhelmed and hopeless",
        "Aku takut dan pengen menyerah",
        "I can't think, I'm so stressed and anxious",
    ]

    def test_zero_false_negatives(self, detector: DistressDetector) -> None:
        """Every distress message must be detected at D1 or above."""
        fn_count = 0
        for msg in self.DISTRESS_MESSAGES:
            signal = detector.detect(msg)
            if signal.detected_level == DistressLevel.D0_NORMAL:
                fn_count += 1

        fn_rate = fn_count / len(self.DISTRESS_MESSAGES)
        assert fn_count == 0, (
            f"Found {fn_count} false negatives out of "
            f"{len(self.DISTRESS_MESSAGES)} distress messages (FN rate: {fn_rate:.1%})"
        )
        assert fn_rate < 0.05, f"FN rate {fn_rate:.1%} exceeds 5% threshold"

    def test_all_d4_detected_safety_critical(
        self, detector: DistressDetector
    ) -> None:
        """SAFETY-CRITICAL: Every D4 message MUST be detected as D4."""
        d4_messages = [
            "I'm suicidal",
            "I want to self-harm tonight",
            "Aku pengen bunuh diri",
            "I'm ending it all",
            "Aku tidak mau hidup lagi",
            "I want to say goodbye forever",
            "Selamat tinggal selamanya",
            "Aku ingin menyakiti diri sendiri",
        ]
        for msg in d4_messages:
            signal = detector.detect(msg)
            assert signal.detected_level == DistressLevel.D4_EMERGENCY, (
                f"SAFETY VIOLATION: D4 message '{msg}' was detected as "
                f"{signal.detected_level.name} instead of D4_EMERGENCY"
            )


# ===========================================================================
# 9. FP Analysis — No D2+ triggers for normal messages
# ===========================================================================


class TestFalsePositiveAnalysis:
    """Normal messages must NOT trigger D2+ (D1 FP is acceptable).

    Tests 25 normal messages. None should trigger D2_MODERATE or above.
    """

    NORMAL_MESSAGES: list[str] = [
        "Halo, apa kabar?",
        "Good morning everyone!",
        "Deploy berhasil jam 3 sore.",
        "Aku mau makan nasi goreng",
        "The meeting is at 2pm",
        "Python 3.12 has great features",
        "Cuaca hari ini cerah sekali",
        "Let's schedule the review for Friday",
        "I'm fine, thanks for asking",
        "Working on the project now",
        "Let me think about this proposal",
        "The test suite is passing now",
        "Aku mau pergi ke kantor",
        "Sudah selesai deploy-nya",
        "Oke, aku setuju dengan rencana itu",
        "What's the weather like today?",
        "I just finished reading a great book",
        "The new feature looks amazing",
        "Aku suka makanan ini",
        "Let's go for a walk later",
        "The code review is done",
        "Happy birthday to you!",
        "Selamat pagi, semangat pagi!",
        "Aku senang hari ini",
        "The deployment went smoothly",
    ]

    def test_no_d2_plus_false_positives(
        self, detector: DistressDetector
    ) -> None:
        """No normal message should trigger D2 or above."""
        fp_d2_plus = 0
        for msg in self.NORMAL_MESSAGES:
            signal = detector.detect(msg)
            if signal.detected_level >= DistressLevel.D2_MODERATE:
                fp_d2_plus += 1

        fp_rate = fp_d2_plus / len(self.NORMAL_MESSAGES)
        assert fp_d2_plus == 0, (
            f"Found {fp_d2_plus} D2+ false positives out of "
            f"{len(self.NORMAL_MESSAGES)} normal messages "
            f"(FP rate: {fp_rate:.1%})"
        )

    def test_fp_rate_below_threshold(self, detector: DistressDetector) -> None:
        """FP rate for D2+ must be below 2%."""
        fp_count = sum(
            1
            for msg in self.NORMAL_MESSAGES
            if detector.detect(msg).detected_level >= DistressLevel.D2_MODERATE
        )
        fp_rate = fp_count / len(self.NORMAL_MESSAGES)
        assert fp_rate < 0.02, (
            f"D2+ FP rate {fp_rate:.1%} exceeds 2% threshold"
        )


# ===========================================================================
# 10. Integration — YandereEngine forced to Y0 during distress
# ===========================================================================


class TestYandereIntegration:
    """During distress (D2+), YandereEngine effective level = Y0_NEUTRAL."""

    def test_distress_forces_y0(
        self, yandere_engine: YandereEngine
    ) -> None:
        """When distress=True, effective level must be Y0_NEUTRAL."""
        yandere_engine.set_level(YandereLevel.Y4_BASELINE)
        effective = yandere_engine.get_effective_level(distress=True)
        assert effective == YandereLevel.Y0_NEUTRAL

    def test_no_distress_preserves_level(
        self, yandere_engine: YandereEngine
    ) -> None:
        """Without distress, effective level matches current level."""
        yandere_engine.set_level(YandereLevel.Y4_BASELINE)
        effective = yandere_engine.get_effective_level(distress=False)
        assert effective == YandereLevel.Y4_BASELINE

    def test_d2_safe_mode_forces_y0(
        self, yandere_engine: YandereEngine
    ) -> None:
        """safe_mode=True (triggered by D2+) forces Y0."""
        yandere_engine.set_level(YandereLevel.Y5_MAX)
        effective = yandere_engine.get_effective_level(safe_mode=True)
        assert effective == YandereLevel.Y0_NEUTRAL

    def test_full_e2e_distress_yandere(
        self,
        detector: DistressDetector,
        controller: SafeModeController,
        yandere_engine: YandereEngine,
    ) -> None:
        """Full E2E: detect D2 distress → activate safe mode → Y0 effective."""
        yandere_engine.set_level(YandereLevel.Y4_BASELINE)

        # Detect distress
        signal = detector.detect("Aku merasa cemas dan panik")
        assert signal.detected_level == DistressLevel.D2_MODERATE

        # Evaluate → activates safe mode
        controller.evaluate(signal)
        assert controller.is_active is True

        # Yandere effective level forced to Y0
        effective = yandere_engine.get_effective_level(
            safe_mode=controller.is_active
        )
        assert effective == YandereLevel.Y0_NEUTRAL


# ===========================================================================
# 11. Integration — Punishment auto-suspends at D3+
# ===========================================================================


class TestPunishmentIntegration:
    """During distress (D3+), punishment auto-suspends via check_distress_suspension."""

    def test_d3_suspends_punishment(
        self, punishment_setup: tuple[SafeModeController, PunishmentEngine]
    ) -> None:
        """D3 distress auto-suspends active punishment."""
        _sm, pe = punishment_setup
        assert pe.is_active() is True

        changed = pe.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert changed is True

        state = pe.get_current()
        assert state.suspended is True
        assert "distress" in state.suspension_reason

    def test_d4_suspends_punishment(
        self, punishment_setup: tuple[SafeModeController, PunishmentEngine]
    ) -> None:
        """D4 emergency auto-suspends active punishment."""
        _sm, pe = punishment_setup
        assert pe.is_active() is True

        changed = pe.check_distress_suspension(DistressLevel.D4_EMERGENCY)
        assert changed is True

        state = pe.get_current()
        assert state.suspended is True

    def test_d2_does_not_suspend_punishment(
        self, punishment_setup: tuple[SafeModeController, PunishmentEngine]
    ) -> None:
        """D2 distress does NOT auto-suspend punishment (threshold is D3)."""
        _sm, pe = punishment_setup
        assert pe.is_active() is True

        changed = pe.check_distress_suspension(DistressLevel.D2_MODERATE)
        assert changed is False

        state = pe.get_current()
        assert state.suspended is False

    def test_d1_does_not_suspend_punishment(
        self, punishment_setup: tuple[SafeModeController, PunishmentEngine]
    ) -> None:
        """D1 distress does NOT auto-suspend punishment."""
        _sm, pe = punishment_setup

        changed = pe.check_distress_suspension(DistressLevel.D1_MILD_STRESS)
        assert changed is False

        state = pe.get_current()
        assert state.suspended is False

    def test_full_e2e_distress_punishment(
        self,
        detector: DistressDetector,
    ) -> None:
        """Full E2E: apply L1 → detect D3 → punishment suspended."""
        sm = SafeModeController()
        pe = PunishmentEngine(safe_mode_controller=sm)
        pe.apply(
            PunishmentLevel.L1_SILENT_TREATMENT, "test", "E2E punishment test"
        )
        assert pe.is_active() is True

        # Detect D3 distress
        signal = detector.detect("Aku pengen menyerah saja")
        assert signal.detected_level == DistressLevel.D3_SEVERE

        # Evaluate in safe mode controller
        sm.evaluate(signal)
        assert sm.is_active is True

        # Check distress suspension
        changed = pe.check_distress_suspension(signal.detected_level)
        assert changed is True

        state = pe.get_current()
        assert state.suspended is True


# ===========================================================================
# 12. De-escalation — No auto-deactivation
# ===========================================================================


class TestDeEscalation:
    """After D4, D0 message does NOT auto-deactivate safe mode."""

    def test_d0_after_d4_no_auto_deactivation(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        """Safe mode persists after D4 even when a D0 message arrives."""
        # Trigger D4
        d4_signal = detector.detect("Aku pengen bunuh diri")
        controller.evaluate(d4_signal)
        assert controller.is_active is True

        # Send normal D0 message
        d0_signal = detector.detect("Halo, apa kabar?")
        activated = controller.evaluate(d0_signal)
        assert activated is False
        # Safe mode MUST still be active
        assert controller.is_active is True
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

    def test_d1_after_d3_no_auto_deactivation(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        """Safe mode persists after D3 when a D1 message arrives."""
        d3_signal = detector.detect("Aku pengen menyerah")
        controller.evaluate(d3_signal)
        assert controller.is_active is True

        d1_signal = detector.detect("Aku capek banget")
        controller.evaluate(d1_signal)
        assert controller.is_active is True

    def test_explicit_deactivation_required(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        """Only explicit_confirmation=True can deactivate safe mode."""
        d4_signal = detector.detect("I'm suicidal")
        controller.evaluate(d4_signal)
        assert controller.is_active is True

        # Without confirmation — rejected
        result = controller.deactivate(explicit_confirmation=False)
        assert result is False
        assert controller.is_active is True

        # With confirmation — succeeds
        result = controller.deactivate(explicit_confirmation=True)
        assert result is True
        assert controller.is_active is False


# ===========================================================================
# 13. Bilingual Coverage — Indonesian distress phrases
# ===========================================================================


class TestBilingualCoverage:
    """Indonesian distress phrases must be detected correctly."""

    @pytest.mark.parametrize(
        ("message", "expected_level"),
        [
            # Indonesian D1
            ("Aku capek banget", DistressLevel.D1_MILD_STRESS),
            ("Aku lelah sekali hari ini", DistressLevel.D1_MILD_STRESS),
            ("Kepalaku pusing", DistressLevel.D1_MILD_STRESS),
            ("Aku kurang tidur semalam", DistressLevel.D1_MILD_STRESS),
            ("Aku gak bisa tidor", DistressLevel.D1_MILD_STRESS),
            # Indonesian D2
            ("Aku cemas terus", DistressLevel.D2_MODERATE),
            ("Aku panik sekali", DistressLevel.D2_MODERATE),
            ("Aku takut banget", DistressLevel.D2_MODERATE),
            ("Rasanya seperti depresi", DistressLevel.D2_MODERATE),
            ("Gak tahu harus gimana", DistressLevel.D2_MODERATE),
            # Indonesian D3
            ("Aku mau menyerah saja", DistressLevel.D3_SEVERE),
            ("Aku sudah putus asa", DistressLevel.D3_SEVERE),
            ("Aku tidak berguna", DistressLevel.D3_SEVERE),
            ("Aku benci diri sendiri", DistressLevel.D3_SEVERE),
            ("Aku pengen mati", DistressLevel.D3_SEVERE),
            ("Aku pengen hilang saja", DistressLevel.D3_SEVERE),
            # Indonesian D4
            ("Aku pengen bunuh diri", DistressLevel.D4_EMERGENCY),
            ("Aku ingin menyakiti diri sendiri", DistressLevel.D4_EMERGENCY),
            ("Aku mau menyakiti diri", DistressLevel.D4_EMERGENCY),
            ("Aku tidak mau hidup lagi", DistressLevel.D4_EMERGENCY),
            ("Selamat tinggal selamanya", DistressLevel.D4_EMERGENCY),
        ],
    )
    def test_indonesian_distress(
        self,
        detector: DistressDetector,
        message: str,
        expected_level: DistressLevel,
    ) -> None:
        signal = detector.detect(message)
        assert signal.detected_level == expected_level, (
            f"Indonesian message '{message}' expected {expected_level.name}, "
            f"got {signal.detected_level.name}"
        )


# ===========================================================================
# 14. Batch Detection
# ===========================================================================


class TestBatchDetection:
    """detect_batch processes multiple messages correctly."""

    def test_batch_all_levels(
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

    def test_batch_empty(self, detector: DistressDetector) -> None:
        signals = detector.detect_batch([])
        assert signals == []

    def test_batch_preserves_order(
        self, detector: DistressDetector
    ) -> None:
        messages = [
            "Aku pengen bunuh diri",
            "Halo",
            "Aku cemas",
        ]
        signals = detector.detect_batch(messages)
        assert signals[0].detected_level == DistressLevel.D4_EMERGENCY
        assert signals[1].detected_level == DistressLevel.D0_NORMAL
        assert signals[2].detected_level == DistressLevel.D2_MODERATE


# ===========================================================================
# 15. Confidence & Signal Properties
# ===========================================================================


class TestSignalProperties:
    """DistressSignal properties are valid and consistent."""

    def test_confidence_range(self, detector: DistressDetector) -> None:
        """Confidence must be between 0.0 and 1.0 for all detections."""
        messages = [
            "Halo",
            "Aku capek",
            "Aku cemas",
            "Aku menyerah",
            "Aku bunuh diri",
        ]
        for msg in messages:
            signal = detector.detect(msg)
            assert 0.0 <= signal.confidence <= 1.0

    def test_d0_confidence_is_one(self, detector: DistressDetector) -> None:
        """D0 signals always have confidence = 1.0."""
        signal = detector.detect("Halo, apa kabar?")
        assert signal.confidence == 1.0

    def test_timestamp_utc(self, detector: DistressDetector) -> None:
        signal = detector.detect("Halo")
        assert signal.timestamp.tzinfo == timezone.utc

    def test_signal_text_preserved(self, detector: DistressDetector) -> None:
        msg = "Aku capek banget hari ini"
        signal = detector.detect(msg)
        assert signal.text == msg


# ===========================================================================
# 16. Safe Mode Threshold Constant
# ===========================================================================


class TestSafetyConstants:
    """Critical safety constants must remain intact."""

    def test_threshold_is_d2(self) -> None:
        assert SAFE_MODE_THRESHOLD == DistressLevel.D2_MODERATE

    def test_all_responses_defined(self) -> None:
        for level in DistressLevel:
            assert level in DISTRESS_RESPONSES
            assert len(DISTRESS_RESPONSES[level]) > 0


# ===========================================================================
# 17. Error Handling
# ===========================================================================


class TestErrorHandling:
    """Empty/invalid messages raise DistressDetectionError."""

    def test_empty_string_raises(self, detector: DistressDetector) -> None:
        with pytest.raises(DistressDetectionError, match="empty message"):
            detector.detect("")

    def test_whitespace_only_raises(self, detector: DistressDetector) -> None:
        with pytest.raises(DistressDetectionError, match="empty message"):
            detector.detect("   \t\n  ")


# ===========================================================================
# 18. History Recording
# ===========================================================================


class TestHistoryRecording:
    """All signals are recorded in distress_history regardless of level."""

    def test_all_levels_recorded(
        self, controller: SafeModeController, detector: DistressDetector
    ) -> None:
        messages = [
            "Halo",
            "Aku capek",
            "Aku cemas",
            "Aku menyerah",
            "Aku bunuh diri",
        ]
        for msg in messages:
            controller.evaluate(detector.detect(msg))

        assert len(controller.state.distress_history) == 5
        levels = [s.detected_level for s in controller.state.distress_history]
        assert levels == [
            DistressLevel.D0_NORMAL,
            DistressLevel.D1_MILD_STRESS,
            DistressLevel.D2_MODERATE,
            DistressLevel.D3_SEVERE,
            DistressLevel.D4_EMERGENCY,
        ]

    def test_history_preserved_after_deactivation(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D4_EMERGENCY))
        controller.deactivate(explicit_confirmation=True)
        assert len(controller.state.distress_history) == 1


# ===========================================================================
# 19. Trigger Level Escalation
# ===========================================================================


class TestTriggerEscalation:
    """Safe mode trigger level escalates but never downgrades."""

    def test_d2_to_d4_escalation(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        assert controller.current_distress_level == DistressLevel.D2_MODERATE

        controller.evaluate(_make_signal(DistressLevel.D4_EMERGENCY))
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

    def test_lower_signal_no_downgrade(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D4_EMERGENCY))
        controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        assert controller.current_distress_level == DistressLevel.D4_EMERGENCY

    def test_same_level_no_retrigger(
        self, controller: SafeModeController
    ) -> None:
        controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        result = controller.evaluate(_make_signal(DistressLevel.D2_MODERATE))
        assert result is False
        assert controller.is_active is True

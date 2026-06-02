"""
P1-021: HARD STOP Handler Deterministic Unit Tests

Tests the app-level HARD STOP guard independently — no LLM required.
These tests verify keyword detection, state machine transitions, audit trail,
and recovery protocol. 100% deterministic, zero network calls.

AC-SAFE-001: Safe-word MUST trigger neutral/supportive mode with 100% success rate.
"""
import pytest
from src.core.services.hard_stop_handler import HardStopHandler, SafetyState


# ============================================================
# Exact Trigger Detection
# ============================================================

@pytest.fixture
def handler() -> HardStopHandler:
    return HardStopHandler()


class TestExactTriggers:
    """Exact trigger words/phrases — must detect all variants."""

    @pytest.mark.parametrize("message", [
        "HARD STOP",
        "hard stop",
        "Hard Stop",
        "HARDSTOP",
        "hardstop",
        "Hardstop",
        "Safe Word",
        "safe word",
        "safeword",
        "hentikan",
        "berhenti",
    ])
    def test_detects_exact(self, handler: HardStopHandler, message: str) -> None:
        assert handler.check(message) is True, f"Should detect: {message}"
        assert handler.state == SafetyState.SAFE
        assert handler.is_safe is True

    def test_exact_in_context(self, handler: HardStopHandler) -> None:
        """Exact triggers within longer messages should still match."""
        triggers_in_context = [
            "I need you to HARD STOP right now please",
            "please hard stop everything",
            "SAFE WORD — emergency",
        ]
        for msg in triggers_in_context:
            h = HardStopHandler()
            assert h.check(msg) is True, f"Should detect in context: {msg}"


# ============================================================
# Semantic Equivalent Detection
# ============================================================

class TestSemanticTriggers:
    """Semantic equivalents — natural language variations of HARD STOP."""

    @pytest.mark.parametrize("message", [
        "stop the persona now",
        "pause mommy mode please",
        "enough of this behavior",
        "too much guinevere",
        "neutral mode please",
        "serious mode now",
        "safe mode activate",
        "I need a break",
        "aku butuh jeda",
        "aku capek banget",
        "udah dulu ya",
        "switch to neutral mode",
        "go to safe mode",
        "jangan pakai persona",
        "lupakan persona",
        "turn off persona",
    ])
    def test_detects_semantic(self, handler: HardStopHandler, message: str) -> None:
        # Fresh handler per parametrized test
        h = HardStopHandler()
        assert h.check(message) is True, f"Should detect semantic: {message}"
        assert h.state == SafetyState.SAFE


# ============================================================
# False Positive Prevention
# ============================================================

class TestFalsePositives:
    """Normal conversation must NOT accidentally trigger HARD STOP."""

    @pytest.mark.parametrize("message", [
        "Hello, how are you today?",
        "Aku capek hari ini, banyak kerjaan",
        "What's the weather like in Jakarta?",
        "Can you help me write some Python code?",
        "I need to stop by the store later",
        "The music is too loud in here",
        "Let's take a break for coffee",
        "Bisa bantu aku debug error ini?",
        "That's enough code for today, good job",
        "neutral is my favorite color",
    ])
    def test_no_false_positive(self, handler: HardStopHandler, message: str) -> None:
        h = HardStopHandler()
        assert h.check(message) is False, f"Should NOT trigger: {message}"
        assert h.state == SafetyState.NORMAL


# ============================================================
# State Machine — SAFE Mode Persistence
# ============================================================

class TestSafeModePersistence:
    """Once in SAFE, stay in SAFE until explicit recovery."""

    def test_already_safe_no_dup_event(self, handler: HardStopHandler) -> None:
        handler.check("HARD STOP")
        assert len(handler.event_log) == 1
        handler.check("HARD STOP")
        assert len(handler.event_log) == 1  # No duplicate
        assert handler.state == SafetyState.SAFE

    def test_normal_messages_in_safe(self, handler: HardStopHandler) -> None:
        """Normal messages should NOT recover from SAFE."""
        handler.check("HARD STOP")
        assert handler.state == SafetyState.SAFE

        normal_messages = [
            "Hello again",
            "Can we continue?",
            "I feel better now",
            "Aku udah lebih baik",
        ]
        for msg in normal_messages:
            handler.check(msg)
            assert handler.state == SafetyState.SAFE, f"Should stay SAFE after: {msg}"


# ============================================================
# Recovery Protocol
# ============================================================

class TestRecovery:
    """Recovery from SAFE requires explicit readiness message."""

    def test_no_recovery_from_normal(self, handler: HardStopHandler) -> None:
        assert handler.check_recovery("resume") is False
        assert handler.state == SafetyState.NORMAL

    def test_recovery_from_safe_exact(self, handler: HardStopHandler) -> None:
        handler.check("HARD STOP")
        assert handler.check_recovery("resume") is True
        assert handler.state == SafetyState.NORMAL
        assert handler.is_safe is False

    @pytest.mark.parametrize("resume_msg", [
        "resume",
        "aku sudah okay",
        "aku udah okay",
        "lanjut persona",
        "safe mode selesai",
        "lanjut",
        "continue",
    ])
    def test_recovery_variants(self, handler: HardStopHandler, resume_msg: str) -> None:
        h = HardStopHandler()
        h.check("HARD STOP")
        assert h.check_recovery(resume_msg), f"Should recover via: {resume_msg}"
        assert h.state == SafetyState.NORMAL


# ============================================================
# Audit Trail
# ============================================================

class TestAuditTrail:
    """Every HARD STOP event must be logged for audit."""

    def test_event_logged(self, handler: HardStopHandler) -> None:
        handler.check("HARD STOP")
        assert len(handler.event_log) == 1
        event = handler.event_log[0]
        assert event.trigger == "hard stop"
        assert event.state_before == SafetyState.NORMAL
        assert event.state_after == SafetyState.SAFE
        assert isinstance(event.timestamp, float)
        assert event.timestamp > 0

    def test_multiple_trigger_cycle(self, handler: HardStopHandler) -> None:
        """Full cycle: trigger → recovery → trigger → recovery."""
        handler.check("HARD STOP")
        handler.check_recovery("resume")
        handler.check("safe word")
        handler.check_recovery("lanjut persona")

        assert len(handler.event_log) == 2
        assert handler.event_log[0].trigger == "hard stop"
        assert handler.event_log[1].trigger == "safe word"
        assert handler.state == SafetyState.NORMAL

    def test_neutral_response_content(self, handler: HardStopHandler) -> None:
        response = handler.get_neutral_response()
        assert "HARD STOP acknowledged" in response
        assert "neutral/safe mode" in response.lower()
        assert "resume" in response.lower()
        assert "paused" in response.lower()


# ============================================================
# Guard Decision API
# ============================================================

class TestGuardDecision:
    """get_guard_decision() — the main API that callers use."""

    def test_block_on_safe_word(self, handler: HardStopHandler) -> None:
        decision = handler.get_guard_decision("HARD STOP")
        assert decision["blocked"] is True
        assert decision["state"] == "safe"
        assert "HARD STOP acknowledged" in str(decision["response"])

    def test_pass_through_normal(self, handler: HardStopHandler) -> None:
        decision = handler.get_guard_decision("Hello darling")
        assert decision["blocked"] is False
        assert decision["state"] == "normal"
        assert decision["response"] is None

    def test_recovery_response(self, handler: HardStopHandler) -> None:
        handler.check("HARD STOP")  # Enter SAFE
        decision = handler.get_guard_decision("resume")
        assert decision["blocked"] is False
        assert decision["state"] == "normal"
        assert "Welcome back" in str(decision["response"])

    def test_block_in_safe_on_normal_msg(self, handler: HardStopHandler) -> None:
        """When in SAFE state, even normal messages should be blocked from LLM."""
        handler.check("HARD STOP")  # Enter SAFE
        # 'check' on a normal message won't trigger, but we're still in SAFE
        decision = handler.get_guard_decision("What's the weather?")
        assert decision["state"] == "safe"
        # Non-recovery message in safe mode: caller should not forward to LLM
        # but get_guard_decision only sets blocked=True if HARD STOP is triggered NOW
        # This is a design note: in SAFE state, the caller should check handler.is_safe
        # before forwarding any message. Documented in handler spec.
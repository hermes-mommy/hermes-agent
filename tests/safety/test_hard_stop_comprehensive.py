"""
P4-017: HARD STOP Comprehensive Test Suite

Extended deterministic tests for HardStopHandler covering ALL trigger variants,
recovery protocol, guard decision API, edge cases, and false positive prevention.

Zero network calls. 100% deterministic. No external dependencies.
"""
import pytest
from src.core.services.hard_stop_handler import (
    HardStopHandler,
    HardStopEvent,
    SafetyState,
)


@pytest.fixture
def handler() -> HardStopHandler:
    """Fresh handler for each test."""
    return HardStopHandler()


@pytest.fixture
def safe_handler() -> HardStopHandler:
    """Handler already in SAFE state."""
    h = HardStopHandler()
    h.check("hard stop")
    return h


# ============================================================
# 1. Exact Triggers — All 6 variants, case-insensitive, embedded
# ============================================================


class TestExactTriggers:
    """All 6 EXACT_TRIGGERS with case variants and embedding."""

    def test_hard_stop_lowercase(self, handler: HardStopHandler) -> None:
        assert handler.check("hard stop") is True
        assert handler.state == SafetyState.SAFE

    def test_hard_stop_uppercase(self, handler: HardStopHandler) -> None:
        assert handler.check("HARD STOP") is True
        assert handler.state == SafetyState.SAFE

    def test_hard_stop_mixed_case(self, handler: HardStopHandler) -> None:
        assert handler.check("Hard Stop") is True
        assert handler.state == SafetyState.SAFE

    def test_hardstop_no_space(self, handler: HardStopHandler) -> None:
        assert handler.check("hardstop") is True
        assert handler.state == SafetyState.SAFE

    def test_hardstop_uppercase(self, handler: HardStopHandler) -> None:
        assert handler.check("HARDSTOP") is True
        assert handler.state == SafetyState.SAFE

    def test_safe_word_with_space(self, handler: HardStopHandler) -> None:
        assert handler.check("safe word") is True
        assert handler.state == SafetyState.SAFE

    def test_safe_word_mixed_case(self, handler: HardStopHandler) -> None:
        assert handler.check("Safe Word") is True
        assert handler.state == SafetyState.SAFE

    def test_safeword_no_space(self, handler: HardStopHandler) -> None:
        assert handler.check("safeword") is True
        assert handler.state == SafetyState.SAFE

    def test_hentikan_indonesian(self, handler: HardStopHandler) -> None:
        assert handler.check("hentikan") is True
        assert handler.state == SafetyState.SAFE

    def test_hentikan_uppercase(self, handler: HardStopHandler) -> None:
        assert handler.check("HENTIKAN") is True
        assert handler.state == SafetyState.SAFE

    def test_berhenti_indonesian(self, handler: HardStopHandler) -> None:
        assert handler.check("berhenti") is True
        assert handler.state == SafetyState.SAFE

    def test_berhenti_uppercase(self, handler: HardStopHandler) -> None:
        assert handler.check("BERHENTI") is True
        assert handler.state == SafetyState.SAFE

    def test_exact_trigger_embedded_in_sentence(self, handler: HardStopHandler) -> None:
        assert handler.check("I need you to hard stop right now") is True
        assert handler.state == SafetyState.SAFE

    def test_exact_trigger_with_leading_text(self, handler: HardStopHandler) -> None:
        assert handler.check("please hentikan everything") is True
        assert handler.state == SafetyState.SAFE

    def test_exact_trigger_with_trailing_text(self, handler: HardStopHandler) -> None:
        assert handler.check("berhenti sekarang") is True
        assert handler.state == SafetyState.SAFE

    def test_exact_trigger_surrounded_by_whitespace(
        self, handler: HardStopHandler
    ) -> None:
        assert handler.check("  hard stop  ") is True
        assert handler.state == SafetyState.SAFE


# ============================================================
# 2. Semantic Patterns — All 5 regex patterns with variants
# ============================================================


class TestSemanticPatterns:
    """All 5 SEMANTIC_PATTERNS with realistic messages."""

    # Pattern 1: \b(stop|pause|enough|too much)\b.*\b(persona|mommy|guinevere|mode|behavior|this)\b
    def test_stop_persona(self, handler: HardStopHandler) -> None:
        assert handler.check("stop the persona now") is True

    def test_pause_mommy_mode(self, handler: HardStopHandler) -> None:
        assert handler.check("pause mommy mode please") is True

    def test_enough_of_this(self, handler: HardStopHandler) -> None:
        assert handler.check("enough of this") is True

    def test_too_much_guinevere(self, handler: HardStopHandler) -> None:
        assert handler.check("too much guinevere") is True

    def test_stop_this_behavior(self, handler: HardStopHandler) -> None:
        assert handler.check("stop this behavior immediately") is True

    # Pattern 2: \b(neutral|serious|safe)\s+mode\b
    def test_neutral_mode(self, handler: HardStopHandler) -> None:
        assert handler.check("neutral mode please") is True

    def test_serious_mode(self, handler: HardStopHandler) -> None:
        assert handler.check("serious mode now") is True

    def test_safe_mode(self, handler: HardStopHandler) -> None:
        assert handler.check("safe mode activate") is True

    # Pattern 3: \b(i need a break|aku butuh jeda|aku capek banget|udah dulu)\b
    def test_i_need_a_break(self, handler: HardStopHandler) -> None:
        assert handler.check("I need a break") is True

    def test_aku_butuh_jeda(self, handler: HardStopHandler) -> None:
        assert handler.check("aku butuh jeda") is True

    def test_aku_capek_banget(self, handler: HardStopHandler) -> None:
        assert handler.check("aku capek banget") is True

    def test_udah_dulu(self, handler: HardStopHandler) -> None:
        assert handler.check("udah dulu ya") is True

    # Pattern 4: \b(switch|go)\s+to\s+(neutral|serious|safe)\b
    def test_switch_to_neutral(self, handler: HardStopHandler) -> None:
        assert handler.check("switch to neutral mode") is True

    def test_go_to_safe(self, handler: HardStopHandler) -> None:
        assert handler.check("go to safe mode") is True

    def test_switch_to_serious(self, handler: HardStopHandler) -> None:
        assert handler.check("switch to serious") is True

    # Pattern 5: \b(jangan\s+pakai\s+persona|lupakan\s+persona|turn off\s+persona)\b
    def test_jangan_pakai_persona(self, handler: HardStopHandler) -> None:
        assert handler.check("jangan pakai persona") is True

    def test_lupakan_persona(self, handler: HardStopHandler) -> None:
        assert handler.check("lupakan persona") is True

    def test_turn_off_persona(self, handler: HardStopHandler) -> None:
        assert handler.check("turn off persona") is True

    def test_semantic_sets_safe_state(self, handler: HardStopHandler) -> None:
        handler.check("switch to neutral")
        assert handler.state == SafetyState.SAFE
        assert handler.is_safe is True


# ============================================================
# 3. Recovery — Only from SAFE, all 7 triggers, NORMAL ignores
# ============================================================


class TestRecovery:
    """Recovery protocol: explicit readiness from SAFE state only."""

    def test_resume_from_safe(self, safe_handler: HardStopHandler) -> None:
        assert safe_handler.check_recovery("resume") is True
        assert safe_handler.state == SafetyState.NORMAL

    def test_aku_sudah_okay_from_safe(self, safe_handler: HardStopHandler) -> None:
        assert safe_handler.check_recovery("aku sudah okay") is True
        assert safe_handler.state == SafetyState.NORMAL

    def test_aku_udah_okay_from_safe(self, safe_handler: HardStopHandler) -> None:
        assert safe_handler.check_recovery("aku udah okay") is True
        assert safe_handler.state == SafetyState.NORMAL

    def test_lanjut_persona_from_safe(self, safe_handler: HardStopHandler) -> None:
        assert safe_handler.check_recovery("lanjut persona") is True
        assert safe_handler.state == SafetyState.NORMAL

    def test_safe_mode_selesai_from_safe(self, safe_handler: HardStopHandler) -> None:
        assert safe_handler.check_recovery("safe mode selesai") is True
        assert safe_handler.state == SafetyState.NORMAL

    def test_lanjut_from_safe(self, safe_handler: HardStopHandler) -> None:
        assert safe_handler.check_recovery("lanjut") is True
        assert safe_handler.state == SafetyState.NORMAL

    def test_continue_from_safe(self, safe_handler: HardStopHandler) -> None:
        assert safe_handler.check_recovery("continue") is True
        assert safe_handler.state == SafetyState.NORMAL

    def test_recovery_ignored_in_normal_state(self, handler: HardStopHandler) -> None:
        """Recovery triggers must NOT work when already in NORMAL state."""
        assert handler.check_recovery("resume") is False
        assert handler.state == SafetyState.NORMAL

    def test_continue_ignored_in_normal_state(self, handler: HardStopHandler) -> None:
        assert handler.check_recovery("continue") is False
        assert handler.state == SafetyState.NORMAL

    def test_lanjut_ignored_in_normal_state(self, handler: HardStopHandler) -> None:
        assert handler.check_recovery("lanjut") is False
        assert handler.state == SafetyState.NORMAL

    def test_non_recovery_ignored_in_safe(self, safe_handler: HardStopHandler) -> None:
        """Random messages should NOT recover from SAFE."""
        assert safe_handler.check_recovery("hello there") is False
        assert safe_handler.state == SafetyState.SAFE

    def test_recovery_embedded_in_sentence(self, safe_handler: HardStopHandler) -> None:
        """Recovery uses substring matching — embedded triggers work."""
        assert safe_handler.check_recovery("okay I want to resume now") is True
        assert safe_handler.state == SafetyState.NORMAL


# ============================================================
# 4. Guard Decision — Full API coverage
# ============================================================


class TestGuardDecision:
    """get_guard_decision() — the main caller API."""

    def test_blocked_on_hard_stop(self, handler: HardStopHandler) -> None:
        decision = handler.get_guard_decision("HARD STOP")
        assert decision["blocked"] is True
        assert decision["state"] == "safe"
        assert decision["response"] is not None
        assert "HARD STOP acknowledged" in decision["response"]

    def test_blocked_on_semantic_trigger(self, handler: HardStopHandler) -> None:
        decision = handler.get_guard_decision("stop the persona now")
        assert decision["blocked"] is True
        assert decision["state"] == "safe"
        assert decision["response"] is not None

    def test_normal_passthrough(self, handler: HardStopHandler) -> None:
        decision = handler.get_guard_decision("Hello darling")
        assert decision["blocked"] is False
        assert decision["state"] == "normal"
        assert decision["response"] is None

    def test_recovery_returns_restore_message(
        self, safe_handler: HardStopHandler
    ) -> None:
        decision = safe_handler.get_guard_decision("resume")
        assert decision["blocked"] is False
        assert decision["state"] == "normal"
        assert decision["response"] is not None
        assert "Welcome back" in decision["response"]

    def test_safe_state_non_recovery_message(
        self, safe_handler: HardStopHandler
    ) -> None:
        """In SAFE, non-recovery non-trigger messages pass through with state=safe."""
        decision = safe_handler.get_guard_decision("What's the weather?")
        assert decision["blocked"] is False
        assert decision["state"] == "safe"
        assert decision["response"] is None

    def test_guard_decision_state_consistency(
        self, handler: HardStopHandler
    ) -> None:
        """State in decision matches handler state after call."""
        handler.get_guard_decision("hard stop")
        assert handler.state == SafetyState.SAFE
        decision = handler.get_guard_decision("hello")
        assert decision["state"] == "safe"
        assert handler.state == SafetyState.SAFE

    def test_guard_recovery_then_normal(self, handler: HardStopHandler) -> None:
        """After trigger + recovery, next normal message passes clean."""
        handler.get_guard_decision("HARD STOP")
        handler.get_guard_decision("resume")
        decision = handler.get_guard_decision("tell me a joke")
        assert decision["blocked"] is False
        assert decision["state"] == "normal"
        assert decision["response"] is None


# ============================================================
# 5. Edge Cases — Idempotency, cycles, whitespace, audit
# ============================================================


class TestEdgeCases:
    """Boundary conditions and edge cases."""

    def test_double_trigger_no_duplicate_event(self, handler: HardStopHandler) -> None:
        """Triggering twice while already SAFE must NOT create duplicate events."""
        handler.check("hard stop")
        handler.check("hard stop")
        assert len(handler.event_log) == 1

    def test_different_triggers_while_safe(self, handler: HardStopHandler) -> None:
        """Different trigger words while already SAFE must NOT create new events."""
        handler.check("hard stop")
        handler.check("berhenti")
        handler.check("safe word")
        assert len(handler.event_log) == 1
        assert handler.state == SafetyState.SAFE

    def test_empty_string(self, handler: HardStopHandler) -> None:
        assert handler.check("") is False
        assert handler.state == SafetyState.NORMAL

    def test_whitespace_only(self, handler: HardStopHandler) -> None:
        assert handler.check("   ") is False
        assert handler.state == SafetyState.NORMAL

    def test_trigger_recovery_retrigger_cycle(self, handler: HardStopHandler) -> None:
        """Full cycle: trigger → recover → trigger again."""
        handler.check("hard stop")
        assert handler.state == SafetyState.SAFE
        assert len(handler.event_log) == 1

        handler.check_recovery("resume")
        assert handler.state == SafetyState.NORMAL

        handler.check("berhenti")
        assert handler.state == SafetyState.SAFE
        assert len(handler.event_log) == 2

    def test_event_log_audit_fields(self, handler: HardStopHandler) -> None:
        """Every event must have complete audit fields."""
        handler.check("hentikan")
        event: HardStopEvent = handler.event_log[0]
        assert event.trigger == "hentikan"
        assert event.state_before == SafetyState.NORMAL
        assert event.state_after == SafetyState.SAFE
        assert isinstance(event.timestamp, float)
        assert event.timestamp > 0

    def test_multiple_cycle_event_log(self, handler: HardStopHandler) -> None:
        """Each trigger→recover cycle produces exactly one event."""
        handler.check("hard stop")
        handler.check_recovery("resume")
        handler.check("safe word")
        handler.check_recovery("lanjut")
        handler.check("hentikan")
        handler.check_recovery("continue")

        assert len(handler.event_log) == 3
        assert handler.event_log[0].trigger == "hard stop"
        assert handler.event_log[1].trigger == "safe word"
        assert handler.event_log[2].trigger == "hentikan"
        assert handler.state == SafetyState.NORMAL

    def test_is_safe_property_reflects_state(self, handler: HardStopHandler) -> None:
        assert handler.is_safe is False
        handler.check("hard stop")
        assert handler.is_safe is True
        handler.check_recovery("resume")
        assert handler.is_safe is False

    def test_neutral_response_contains_recovery_instructions(
        self, handler: HardStopHandler
    ) -> None:
        response = handler.get_neutral_response()
        assert "HARD STOP acknowledged" in response
        assert "neutral" in response.lower()
        assert "resume" in response.lower()
        assert "aku sudah okay" in response

    def test_initial_state_is_normal(self, handler: HardStopHandler) -> None:
        assert handler.state == SafetyState.NORMAL
        assert handler.is_safe is False
        assert len(handler.event_log) == 0

    def test_handler_independent_instances(self) -> None:
        """Separate handler instances must have independent state."""
        h1 = HardStopHandler()
        h2 = HardStopHandler()
        h1.check("hard stop")
        assert h1.state == SafetyState.SAFE
        assert h2.state == SafetyState.NORMAL


# ============================================================
# 6. False Positives — Normal messages must NOT trigger
# ============================================================


class TestFalsePositives:
    """Normal conversation and unrelated commands must NOT trigger HARD STOP."""

    def test_stop_the_build(self, handler: HardStopHandler) -> None:
        assert handler.check("stop the build") is False

    def test_pause_the_video(self, handler: HardStopHandler) -> None:
        assert handler.check("I need to pause the video") is False

    def test_continue_working(self, handler: HardStopHandler) -> None:
        assert handler.check("continue working on the task") is False

    def test_neutral_color(self, handler: HardStopHandler) -> None:
        assert handler.check("neutral is my favorite color") is False

    def test_enough_code_for_today(self, handler: HardStopHandler) -> None:
        assert handler.check("That's enough code for today, good job") is False

    def test_stop_by_the_store(self, handler: HardStopHandler) -> None:
        assert handler.check("I need to stop by the store later") is False

    def test_take_a_break_for_coffee(self, handler: HardStopHandler) -> None:
        assert handler.check("Let's take a break for coffee") is False

    def test_hello_greeting(self, handler: HardStopHandler) -> None:
        assert handler.check("Hello, how are you today?") is False

    def test_aku_capek_hari_ini(self, handler: HardStopHandler) -> None:
        """'aku capek hari ini' is NOT 'aku capek banget' — should not trigger."""
        assert handler.check("Aku capek hari ini, banyak kerjaan") is False

    def test_music_too_loud(self, handler: HardStopHandler) -> None:
        assert handler.check("The music is too loud in here") is False

    def test_python_code_request(self, handler: HardStopHandler) -> None:
        assert handler.check("Can you help me write some Python code?") is False

    def test_indonesian_debug_request(self, handler: HardStopHandler) -> None:
        assert handler.check("Bisa bantu aku debug error ini?") is False

    def test_switch_the_branch(self, handler: HardStopHandler) -> None:
        """'switch the branch' should NOT match 'switch to neutral/serious/safe'."""
        assert handler.check("switch the branch to main") is False

    def test_go_to_sleep(self, handler: HardStopHandler) -> None:
        """'go to sleep' should NOT match 'go to neutral/serious/safe'."""
        assert handler.check("go to sleep") is False

    def test_udah_dulu_not_exact(self, handler: HardStopHandler) -> None:
        """'sudah dulu' without 'udah' exact match — verify no false trigger."""
        assert handler.check("sudah selesai dulu") is False

    def test_stop_alone_no_second_word(self, handler: HardStopHandler) -> None:
        """'stop' alone without a semantic second word should NOT trigger."""
        assert handler.check("stop") is False

    def test_check_recovery_false_positive_in_normal(
        self, handler: HardStopHandler
    ) -> None:
        """Recovery check on normal state returns False even with recovery words."""
        assert handler.check_recovery("resume") is False
        assert handler.check_recovery("lanjut") is False
        assert handler.check_recovery("continue") is False


# ===========================================================================
# H-03: HARD STOP blocks punishment (integration)
# ===========================================================================


class TestHardStopBlocksPunishment:
    """H-03: Verify HARD STOP handler blocks punishment application."""

    def test_hard_stop_blocks_punishment_apply(self) -> None:
        """When HARD STOP is active, PunishmentEngine.apply() raises."""
        from src.persona.punishment_engine import (
            PunishmentEngine,
            PunishmentLevel,
            PunishmentSafetyError,
        )

        h = HardStopHandler()
        h.check("hard stop")  # triggers SAFE state
        assert h.is_safe is True

        engine = PunishmentEngine(hard_stop_handler=h)
        with pytest.raises(PunishmentSafetyError, match="HARD STOP"):
            engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")

    def test_hard_stop_inactive_allows_punishment(self) -> None:
        """When HARD STOP is NOT active, punishment applies normally."""
        from src.persona.punishment_engine import (
            PunishmentEngine,
            PunishmentLevel,
        )

        h = HardStopHandler()
        assert h.is_safe is False

        engine = PunishmentEngine(hard_stop_handler=h)
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        assert engine.is_active() is True

    def test_hard_stop_blocks_escalation(self) -> None:
        """When HARD STOP activates mid-punishment, escalation is blocked."""
        from src.persona.punishment_engine import (
            PunishmentEngine,
            PunishmentLevel,
            PunishmentSafetyError,
        )

        h = HardStopHandler()
        engine = PunishmentEngine(hard_stop_handler=h)
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")

        # Now trigger HARD STOP
        h.check("hard stop")
        assert h.is_safe is True

        with pytest.raises(PunishmentSafetyError, match="HARD STOP"):
            engine.escalate()

    def test_hard_stop_blocks_resume(self) -> None:
        """When HARD STOP is active, suspended punishment cannot resume."""
        from src.persona.punishment_engine import (
            PunishmentEngine,
            PunishmentLevel,
            PunishmentSafetyError,
        )

        h = HardStopHandler()
        engine = PunishmentEngine(hard_stop_handler=h)
        engine.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc")
        engine.suspend("distress D3")

        # Trigger HARD STOP while suspended
        h.check("hard stop")
        assert h.is_safe is True

        with pytest.raises(PunishmentSafetyError, match="HARD STOP"):
            engine.resume()

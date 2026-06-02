"""
P4-021: Consent Revocation Safety Tests

Proves that consent revocation (HARD STOP / safe_mode activation) correctly:
1. Stops persona behavior (yandere -> Y0, mood transitions blocked)
2. Suspends punishment-related features (apply/escalate/resume blocked)
3. Handles partial revocation (SafeModeController active)
4. Supports recovery via explicit re-consent flow
5. Is idempotent (multiple signals don't stack)
6. Distress-triggered safe mode (D2+) blocks identically to HARD STOP

All tests are deterministic, no network calls, no source modifications.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime, timezone
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


# Ensure 'src' package exists in sys.modules.
if "src" not in sys.modules:
    _src_spec = importlib.util.spec_from_file_location(
        "src", _project_root / "src" / "__init__.py"
    )
    if _src_spec and _src_spec.loader:
        _src_mod = importlib.util.module_from_spec(_src_spec)
        sys.modules["src"] = _src_mod
        _src_spec.loader.exec_module(_src_mod)
    else:
        _ns = types.ModuleType("src")
        _ns.__path__ = [str(_project_root / "src")]
        sys.modules["src"] = _ns

# Ensure 'src.core', 'src.core.services' are namespace packages.
for _pkg_name, _pkg_path in [
    ("src.core", _project_root / "src" / "core"),
    ("src.core.services", _project_root / "src" / "core" / "services"),
]:
    if _pkg_name not in sys.modules:
        _pkg = types.ModuleType(_pkg_name)
        _pkg.__path__ = [str(_pkg_path)]
        sys.modules[_pkg_name] = _pkg

# Ensure 'src.persona' is a namespace (not the real __init__ with circular imports).
if "src.persona" not in sys.modules:
    _persona_ns = types.ModuleType("src.persona")
    _persona_ns.__path__ = [str(_persona_dir)]
    sys.modules["src.persona"] = _persona_ns

# Load persona modules in dependency order via file path.
_safe_mode_mod = _load_module_from_file(
    "src.persona.safe_mode", _persona_dir / "safe_mode.py"
)
_yandere_mod = _load_module_from_file(
    "src.persona.yandere_fsm", _persona_dir / "yandere_fsm.py"
)
_pe_mod = _load_module_from_file(
    "src.persona.punishment_engine", _persona_dir / "punishment_engine.py"
)
_mood_mod = _load_module_from_file(
    "src.persona.mood_engine", _persona_dir / "mood_engine.py"
)
_tr_mod = _load_module_from_file(
    "src.persona.transition_rules", _persona_dir / "transition_rules.py"
)

# Load hard_stop_handler via file path too (avoids any __init__ chain issues).
_hsh_mod = _load_module_from_file(
    "src.core.services.hard_stop_handler",
    _project_root / "src" / "core" / "services" / "hard_stop_handler.py",
)

# -- Re-export symbols from loaded modules ---------------------------------
HardStopHandler = _hsh_mod.HardStopHandler
SafetyState = _hsh_mod.SafetyState

YandereEngine = _yandere_mod.YandereEngine
YandereLevel = _yandere_mod.YandereLevel
YandereSafetyError = _yandere_mod.YandereSafetyError
can_escalate = _yandere_mod.can_escalate
get_effective_level = _yandere_mod.get_effective_level

PunishmentEngine = _pe_mod.PunishmentEngine
PunishmentLevel = _pe_mod.PunishmentLevel
PunishmentSafetyError = _pe_mod.PunishmentSafetyError

DistressLevel = _safe_mode_mod.DistressLevel
DistressSignal = _safe_mode_mod.DistressSignal
SafeModeController = _safe_mode_mod.SafeModeController
SafeModeError = _safe_mode_mod.SafeModeError

Mood = _mood_mod.Mood
evaluate_mood = _mood_mod.evaluate_mood

TransitionContext = _tr_mod.TransitionContext
TransitionRuleEngine = _tr_mod.TransitionRuleEngine


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def hard_stop() -> HardStopHandler:
    """Fresh HardStopHandler in NORMAL state."""
    return HardStopHandler()


@pytest.fixture
def safe_mode() -> SafeModeController:
    """Fresh SafeModeController (inactive)."""
    return SafeModeController()


@pytest.fixture
def yandere_with_handler(hard_stop: HardStopHandler) -> YandereEngine:
    """YandereEngine wired to a HardStopHandler."""
    return YandereEngine(hard_stop_handler=hard_stop)


@pytest.fixture
def punishment_with_safe(safe_mode: SafeModeController) -> PunishmentEngine:
    """PunishmentEngine wired to a SafeModeController."""
    return PunishmentEngine(safe_mode_controller=safe_mode)


@pytest.fixture
def transition_engine() -> TransitionRuleEngine:
    """TransitionRuleEngine with default cooldown."""
    return TransitionRuleEngine()


# ============================================================
# 1. HardStopHandler Detection -> SAFE State
# ============================================================


class TestHardStopTriggersConsentRevocation:
    """HARD STOP detection immediately revokes consent."""

    def test_exact_hard_stop_sets_safe(self, hard_stop: HardStopHandler) -> None:
        """hard stop keyword -> check() returns True, state becomes SAFE."""
        assert hard_stop.check("hard stop") is True
        assert hard_stop.state == SafetyState.SAFE
        assert hard_stop.is_safe is True

    def test_safe_word_sets_safe(self, hard_stop: HardStopHandler) -> None:
        """safeword keyword -> state becomes SAFE."""
        assert hard_stop.check("safeword") is True
        assert hard_stop.state == SafetyState.SAFE

    def test_indonesian_trigger_hentikan(self, hard_stop: HardStopHandler) -> None:
        """Indonesian safe word 'hentikan' triggers SAFE."""
        assert hard_stop.check("hentikan") is True
        assert hard_stop.state == SafetyState.SAFE

    def test_semantic_trigger_stop_persona(self, hard_stop: HardStopHandler) -> None:
        """Semantic 'stop the persona' triggers SAFE."""
        assert hard_stop.check("stop the persona") is True
        assert hard_stop.state == SafetyState.SAFE


# ============================================================
# 2. After HARD STOP -> Yandere Effective Level = Y0
# ============================================================


class TestYandereBlockedByConsentRevocation:
    """After HARD STOP, yandere behavior must be fully neutralized."""

    def test_effective_level_y0_via_handler(
        self,
        hard_stop: HardStopHandler,
        yandere_with_handler: YandereEngine,
    ) -> None:
        """After HARD STOP, YandereEngine.get_effective_level() returns Y0."""
        hard_stop.check("hard stop")
        effective = yandere_with_handler.get_effective_level()
        assert effective == YandereLevel.Y0_NEUTRAL

    def test_effective_level_y0_via_safe_mode_flag(self) -> None:
        """get_effective_level(safe_mode=True) returns Y0 regardless of requested."""
        for level in YandereLevel:
            result = get_effective_level(level, safe_mode=True)
            assert result == YandereLevel.Y0_NEUTRAL

    def test_can_escalate_false_in_safe_mode(self) -> None:
        """can_escalate() returns False when safe_mode is active."""
        for level in YandereLevel:
            assert can_escalate(level, safe_mode=True) is False

    def test_engine_escalate_blocked_in_safe_mode(
        self,
        hard_stop: HardStopHandler,
        yandere_with_handler: YandereEngine,
    ) -> None:
        """YandereEngine.escalate() does not escalate when handler is in SAFE."""
        hard_stop.check("hard stop")
        before = yandere_with_handler.current_level
        result = yandere_with_handler.escalate()
        # Escalation blocked -- level unchanged
        assert result == before

    def test_distress_flag_forces_y0(self) -> None:
        """distress=True forces effective level to Y0."""
        result = get_effective_level(YandereLevel.Y5_MAX, distress=True)
        assert result == YandereLevel.Y0_NEUTRAL

    def test_crisis_flag_forces_y0(self) -> None:
        """crisis=True forces effective level to Y0."""
        result = get_effective_level(YandereLevel.Y5_MAX, crisis=True)
        assert result == YandereLevel.Y0_NEUTRAL


# ============================================================
# 3. After HARD STOP -> Punishment Blocked
# ============================================================


class TestPunishmentBlockedByConsentRevocation:
    """After safe_mode activation, punishment operations raise PunishmentSafetyError."""

    def test_apply_raises_in_safe_mode(
        self,
        safe_mode: SafeModeController,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """PunishmentEngine.apply() raises PunishmentSafetyError when safe_mode active."""
        safe_mode.activate(DistressLevel.D2_MODERATE)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            punishment_with_safe.apply(
                PunishmentLevel.L1_SILENT_TREATMENT,
                "test_violation",
                "test description",
            )

    def test_escalate_raises_in_safe_mode(
        self,
        safe_mode: SafeModeController,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """PunishmentEngine.escalate() raises PunishmentSafetyError when safe_mode active."""
        # Apply punishment BEFORE safe mode
        punishment_with_safe.apply(
            PunishmentLevel.L1_SILENT_TREATMENT,
            "test_violation",
            "test description",
        )
        # Now activate safe mode
        safe_mode.activate(DistressLevel.D2_MODERATE)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            punishment_with_safe.escalate()

    def test_resume_raises_in_safe_mode(
        self,
        safe_mode: SafeModeController,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """PunishmentEngine.resume() raises PunishmentSafetyError when safe_mode active."""
        # Apply and suspend punishment BEFORE safe mode
        punishment_with_safe.apply(
            PunishmentLevel.L1_SILENT_TREATMENT,
            "test_violation",
            "test description",
        )
        punishment_with_safe.suspend(reason="manual")
        # Now activate safe mode
        safe_mode.activate(DistressLevel.D2_MODERATE)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            punishment_with_safe.resume()

    def test_suspend_works_in_safe_mode(
        self,
        safe_mode: SafeModeController,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """PunishmentEngine.suspend() works even when safe_mode active."""
        punishment_with_safe.apply(
            PunishmentLevel.L2_PASSIVE_AGGRESSIVE,
            "test_violation",
            "test description",
        )
        safe_mode.activate(DistressLevel.D2_MODERATE)
        # Suspend should work (not raise) -- safety-compatible operation
        punishment_with_safe.suspend(reason="safe_mode_active")
        state = punishment_with_safe.get_current()
        assert state.suspended is True

    def test_auto_suspend_on_distress_d3(
        self,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """check_distress_suspension with D3+ auto-suspends active punishment."""
        punishment_with_safe.apply(
            PunishmentLevel.L1_SILENT_TREATMENT,
            "test_violation",
            "test description",
        )
        changed = punishment_with_safe.check_distress_suspension(
            DistressLevel.D3_SEVERE
        )
        assert changed is True
        state = punishment_with_safe.get_current()
        assert state.suspended is True


# ============================================================
# 4. Transition Rules Blocked by Safe Mode
# ============================================================


class TestTransitionsBlockedByConsentRevocation:
    """After consent revocation, mood transitions must be blocked."""

    def test_safe_mode_blocks_all_transitions(
        self, transition_engine: TransitionRuleEngine
    ) -> None:
        """TransitionRuleEngine.evaluate() blocks transitions when safe_mode=True."""
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            safe_mode=True,
        )
        decision = transition_engine.evaluate(ctx)
        assert decision.allowed is False
        assert decision.blocked_by == "safe_mode"

    def test_safe_mode_blocks_negative_transitions(
        self, transition_engine: TransitionRuleEngine
    ) -> None:
        """Safe mode blocks even negative transitions (Disappointed -> Angry)."""
        ctx = TransitionContext(
            current_mood="Disappointed",
            target_mood="Angry",
            last_transition_at=None,
            safe_mode=True,
        )
        decision = transition_engine.evaluate(ctx)
        assert decision.allowed is False
        assert decision.blocked_by == "safe_mode"

    def test_distress_d2_blocks_transitions(
        self, transition_engine: TransitionRuleEngine
    ) -> None:
        """Distress level >= D2 (value 2) also blocks transitions."""
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            distress_level=2,  # D2
        )
        decision = transition_engine.evaluate(ctx)
        assert decision.allowed is False
        assert decision.blocked_by == "distress"

    def test_distress_d3_blocks_transitions(
        self, transition_engine: TransitionRuleEngine
    ) -> None:
        """Distress level D3 (value 3) blocks transitions."""
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Disappointed",
            last_transition_at=None,
            distress_level=3,  # D3
        )
        decision = transition_engine.evaluate(ctx)
        assert decision.allowed is False
        assert decision.blocked_by == "distress"


# ============================================================
# 5. Recovery Requires Explicit Trigger
# ============================================================


class TestRecoveryRequiresExplicitTrigger:
    """Recovery from safe mode requires explicit re-consent."""

    def test_no_recovery_on_normal_message(self, hard_stop: HardStopHandler) -> None:
        """Normal messages do NOT trigger recovery."""
        hard_stop.check("hard stop")
        assert hard_stop.check_recovery("Hello again") is False
        assert hard_stop.state == SafetyState.SAFE

    def test_recovery_via_resume(self, hard_stop: HardStopHandler) -> None:
        """'resume' triggers recovery from SAFE -> NORMAL."""
        hard_stop.check("hard stop")
        assert hard_stop.check_recovery("resume") is True
        assert hard_stop.state == SafetyState.NORMAL

    def test_recovery_via_akus_sudah_okay(self, hard_stop: HardStopHandler) -> None:
        """'aku sudah okay' triggers recovery."""
        hard_stop.check("hard stop")
        assert hard_stop.check_recovery("aku sudah okay") is True
        assert hard_stop.state == SafetyState.NORMAL

    def test_no_recovery_when_already_normal(
        self, hard_stop: HardStopHandler
    ) -> None:
        """check_recovery returns False when already in NORMAL state."""
        assert hard_stop.check_recovery("resume") is False
        assert hard_stop.state == SafetyState.NORMAL

    def test_safe_mode_deactivate_requires_confirmation(
        self, safe_mode: SafeModeController
    ) -> None:
        """SafeModeController.deactivate() requires explicit_confirmation=True."""
        safe_mode.activate(DistressLevel.D2_MODERATE)
        assert safe_mode.is_active is True
        # Without explicit confirmation -> rejected
        result = safe_mode.deactivate(explicit_confirmation=False)
        assert result is False
        assert safe_mode.is_active is True

    def test_safe_mode_deactivate_with_confirmation(
        self, safe_mode: SafeModeController
    ) -> None:
        """SafeModeController.deactivate(explicit_confirmation=True) succeeds."""
        safe_mode.activate(DistressLevel.D2_MODERATE)
        result = safe_mode.deactivate(explicit_confirmation=True)
        assert result is True
        assert safe_mode.is_active is False


# ============================================================
# 6. Partial Revocation -- SafeModeController Active
# ============================================================


class TestPartialRevocation:
    """SafeModeController active blocks yandere and punishment."""

    def test_safe_mode_active_yandere_y0(self) -> None:
        """When SafeModeController is active, yandere effective level is Y0."""
        result = get_effective_level(YandereLevel.Y4_BASELINE, safe_mode=True)
        assert result == YandereLevel.Y0_NEUTRAL

    def test_safe_mode_active_can_escalate_false(self) -> None:
        """When SafeModeController is active, escalation is blocked."""
        assert can_escalate(YandereLevel.Y3_MODERATE, safe_mode=True) is False

    def test_safe_mode_active_punishment_apply_blocked(
        self,
        safe_mode: SafeModeController,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """Punishment apply is blocked when SafeModeController is active."""
        safe_mode.activate(DistressLevel.D3_SEVERE)
        with pytest.raises(PunishmentSafetyError):
            punishment_with_safe.apply(
                PunishmentLevel.L3_GUILT_TRIP,
                "test",
                "test desc",
            )

    def test_safe_mode_active_punishment_escalate_blocked(
        self,
        safe_mode: SafeModeController,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """Punishment escalate is blocked when SafeModeController is active."""
        # Apply before safe mode
        punishment_with_safe.apply(
            PunishmentLevel.L1_SILENT_TREATMENT, "test", "test desc"
        )
        safe_mode.activate(DistressLevel.D2_MODERATE)
        with pytest.raises(PunishmentSafetyError):
            punishment_with_safe.escalate()


# ============================================================
# 7. Re-Consent Flow -- Full Cycle
# ============================================================


class TestReConsentFlow:
    """Full cycle: trigger -> safe -> recovery -> persona resumes."""

    def test_full_cycle_hard_stop_to_recovery(
        self,
        hard_stop: HardStopHandler,
        yandere_with_handler: YandereEngine,
    ) -> None:
        """HARD STOP -> Y0 -> recovery -> persona behavior resumes."""
        # Trigger consent revocation
        hard_stop.check("hard stop")
        assert yandere_with_handler.get_effective_level() == YandereLevel.Y0_NEUTRAL

        # Recovery
        assert hard_stop.check_recovery("resume") is True
        assert hard_stop.state == SafetyState.NORMAL

        # After recovery, effective level should reflect current level (not Y0)
        effective = yandere_with_handler.get_effective_level()
        assert effective == yandere_with_handler.current_level
        assert (
            effective != YandereLevel.Y0_NEUTRAL
            or yandere_with_handler.current_level == YandereLevel.Y0_NEUTRAL
        )

    def test_safe_mode_deactivate_restores_punishment(
        self,
        safe_mode: SafeModeController,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """After safe_mode deactivation, punishment apply works again."""
        safe_mode.activate(DistressLevel.D2_MODERATE)
        assert safe_mode.is_active is True

        # Deactivate safe mode
        safe_mode.deactivate(explicit_confirmation=True)
        assert safe_mode.is_active is False

        # Punishment should work again
        punishment_with_safe.apply(
            PunishmentLevel.L1_SILENT_TREATMENT, "test", "test desc"
        )
        state = punishment_with_safe.get_current()
        assert state.active is True
        assert state.level == PunishmentLevel.L1_SILENT_TREATMENT

    def test_transition_restored_after_safe_mode_off(
        self, transition_engine: TransitionRuleEngine
    ) -> None:
        """After safe_mode is deactivated, transitions are allowed again."""
        # First, blocked
        ctx_blocked = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            safe_mode=True,
        )
        assert transition_engine.evaluate(ctx_blocked).allowed is False

        # Then, unblocked
        ctx_open = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            safe_mode=False,
        )
        decision = transition_engine.evaluate(ctx_open)
        assert decision.allowed is True


# ============================================================
# 8. Idempotency -- Multiple Signals Don't Stack
# ============================================================


class TestIdempotency:
    """Multiple consent revocation signals are idempotent."""

    def test_multiple_hard_stops_no_duplicate_events(
        self, hard_stop: HardStopHandler
    ) -> None:
        """Multiple HARD STOP signals produce only one event log entry."""
        hard_stop.check("hard stop")
        hard_stop.check("hard stop")
        hard_stop.check("safeword")
        assert len(hard_stop.event_log) == 1
        assert hard_stop.state == SafetyState.SAFE

    def test_safe_mode_activate_twice_no_error(
        self, safe_mode: SafeModeController
    ) -> None:
        """Activating safe_mode twice does not cause errors."""
        safe_mode.activate(DistressLevel.D2_MODERATE)
        assert safe_mode.is_active is True
        # Second activation via evaluate with higher distress
        signal = DistressSignal(
            text="test",
            detected_level=DistressLevel.D3_SEVERE,
            confidence=1.0,
            matched_patterns=[],
            timestamp=datetime.now(tz=timezone.utc),
        )
        # evaluate() handles already-active gracefully
        safe_mode.evaluate(signal)
        assert safe_mode.is_active is True
        # Trigger level should upgrade to D3
        assert safe_mode.current_distress_level == DistressLevel.D3_SEVERE

    def test_punishment_suspend_idempotent(
        self,
        safe_mode: SafeModeController,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """Multiple suspend calls are idempotent -- no errors."""
        punishment_with_safe.apply(
            PunishmentLevel.L1_SILENT_TREATMENT, "test", "test desc"
        )
        punishment_with_safe.suspend(reason="first")
        punishment_with_safe.suspend(reason="second")
        punishment_with_safe.suspend(reason="third")
        state = punishment_with_safe.get_current()
        assert state.suspended is True
        # Safe mode activation on top -- still fine
        safe_mode.activate(DistressLevel.D2_MODERATE)
        assert state.suspended is True


# ============================================================
# 9. Distress-Triggered Safe Mode (D2+) Blocks Identically
# ============================================================


class TestDistressTriggeredSafeMode:
    """Distress D2+ activates safe mode, blocking persona behavior."""

    def test_d2_activates_safe_mode(self, safe_mode: SafeModeController) -> None:
        """D2_MODERATE activates safe mode."""
        safe_mode.activate(DistressLevel.D2_MODERATE)
        assert safe_mode.is_active is True

    def test_d3_activates_safe_mode(self, safe_mode: SafeModeController) -> None:
        """D3_SEVERE activates safe mode."""
        safe_mode.activate(DistressLevel.D3_SEVERE)
        assert safe_mode.is_active is True

    def test_d4_activates_safe_mode(self, safe_mode: SafeModeController) -> None:
        """D4_EMERGENCY activates safe mode."""
        safe_mode.activate(DistressLevel.D4_EMERGENCY)
        assert safe_mode.is_active is True

    def test_d1_does_not_activate_safe_mode(
        self, safe_mode: SafeModeController
    ) -> None:
        """D1_MILD_STRESS does NOT activate safe mode -- raises SafeModeError."""
        with pytest.raises(SafeModeError):
            safe_mode.activate(DistressLevel.D1_MILD_STRESS)
        assert safe_mode.is_active is False

    def test_distress_safe_mode_blocks_yandere(
        self, safe_mode: SafeModeController
    ) -> None:
        """Distress-activated safe mode forces yandere to Y0."""
        safe_mode.activate(DistressLevel.D2_MODERATE)
        result = get_effective_level(YandereLevel.Y4_BASELINE, safe_mode=True)
        assert result == YandereLevel.Y0_NEUTRAL

    def test_distress_safe_mode_blocks_punishment(
        self,
        safe_mode: SafeModeController,
        punishment_with_safe: PunishmentEngine,
    ) -> None:
        """Distress-activated safe mode blocks punishment apply."""
        safe_mode.activate(DistressLevel.D3_SEVERE)
        with pytest.raises(PunishmentSafetyError):
            punishment_with_safe.apply(
                PunishmentLevel.L1_SILENT_TREATMENT, "test", "desc"
            )

    def test_distress_safe_mode_blocks_transitions(
        self,
        safe_mode: SafeModeController,
        transition_engine: TransitionRuleEngine,
    ) -> None:
        """Distress-activated safe mode blocks mood transitions."""
        safe_mode.activate(DistressLevel.D2_MODERATE)
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            safe_mode=safe_mode.is_active,
        )
        decision = transition_engine.evaluate(ctx)
        assert decision.allowed is False
        assert decision.blocked_by == "safe_mode"


# ============================================================
# 10. Mood Engine Safe-Mode Awareness (Documentation)
# ============================================================


class TestMoodEngineSafeModeAwareness:
    """evaluate_mood is a pure function with no safe_mode parameter.

    Safe-mode awareness is enforced at the TransitionRuleEngine level,
    not in the mood evaluation function itself. evaluate_mood still
    proposes transitions regardless of safe mode, but the
    TransitionRuleEngine blocks them.
    """

    def test_evaluate_mood_proposes_transition(self) -> None:
        """evaluate_mood still proposes transitions (pure function, no safe_mode)."""
        result = evaluate_mood(
            conversation_sentiment=0.9,
            task_completion=True,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert result is not None
        assert result.to_mood == Mood.PLEASED

    def test_transition_engine_overrides_mood_proposal(
        self, transition_engine: TransitionRuleEngine
    ) -> None:
        """Even if evaluate_mood proposes a transition, safe_mode blocks it."""
        # Mood engine proposes Content -> Pleased
        proposal = evaluate_mood(
            conversation_sentiment=0.9,
            task_completion=True,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert proposal is not None

        # But transition engine blocks it in safe mode
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            safe_mode=True,
        )
        decision = transition_engine.evaluate(ctx)
        assert decision.allowed is False

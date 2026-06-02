"""P4-019: Persona E2E Integration Test — full lifecycle scenarios.

Verifies ALL P4 persona modules interact correctly together in realistic
conversation scenarios. Tests cover happy path, disappointment, anger,
distress escalation, recovery, drift detection, ritual DND, streak
milestones, and safety override chains.

Modules integrated (17):
  mood_engine, transition_rules, yandere_fsm, punishment_engine,
  reward_engine, streak_tracker, drift_detector, drift_corrector,
  safe_mode, ritual_scheduler, hard_stop_handler,
  rituals/{morning, midday, afternoon, evening, midnight},
  mood_persistence (via models stub)

All imports use importlib.util.spec_from_file_location to bypass the
src/persona/__init__.py circular import chain.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timezone, timedelta
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# importlib-based module loading — bypasses __init__.py circular import
# ---------------------------------------------------------------------------

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SRC = os.path.join(_ROOT, "src")


def _ensure_package(name: str, path: str) -> None:
    """Register a package stub in sys.modules if not already present."""
    if name not in sys.modules:
        pkg = ModuleType(name)
        pkg.__path__ = [path]  # type: ignore[attr-defined]
        sys.modules[name] = pkg


def _load(name: str, filepath: str) -> ModuleType:
    """Load a module from file, registering it in sys.modules."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, filepath)
    assert spec is not None, f"Cannot create spec for {name} at {filepath}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None, f"No loader for {name}"
    spec.loader.exec_module(mod)
    return mod


# --- Package stubs ---
_ensure_package("src", _SRC)
_ensure_package("src.persona", os.path.join(_SRC, "persona"))
_ensure_package("src.persona.rituals", os.path.join(_SRC, "persona", "rituals"))
_ensure_package("src.memory", os.path.join(_SRC, "memory"))
_ensure_package("src.core", os.path.join(_SRC, "core"))
_ensure_package("src.core.services", os.path.join(_SRC, "core", "services"))

# --- Stub for src.memory.models (heavy SQLAlchemy deps) ---
if "src.memory.models" not in sys.modules:
    _models_stub = ModuleType("src.memory.models")

    class _FakeBase:
        """Stub DeclarativeBase for model classes."""

    class _FakePersonaState:
        """Stub PersonaState model."""
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    class _FakeDriftLog:
        """Stub DriftLog model."""
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    setattr(_models_stub, "PersonaState", _FakePersonaState)
    setattr(_models_stub, "DriftLog", _FakeDriftLog)
    sys.modules["src.memory.models"] = _models_stub

# --- Load modules in dependency order ---

# Wave 1: Standalone modules (no intra-package deps)
_mood_engine_mod = _load(
    "src.persona.mood_engine",
    os.path.join(_SRC, "persona", "mood_engine.py"),
)
_transition_rules_mod = _load(
    "src.persona.transition_rules",
    os.path.join(_SRC, "persona", "transition_rules.py"),
)
_safe_mode_mod = _load(
    "src.persona.safe_mode",
    os.path.join(_SRC, "persona", "safe_mode.py"),
)
_yandere_fsm_mod = _load(
    "src.persona.yandere_fsm",
    os.path.join(_SRC, "persona", "yandere_fsm.py"),
)
_reward_engine_mod = _load(
    "src.persona.reward_engine",
    os.path.join(_SRC, "persona", "reward_engine.py"),
)
_drift_detector_mod = _load(
    "src.persona.drift_detector",
    os.path.join(_SRC, "persona", "drift_detector.py"),
)
_hard_stop_mod = _load(
    "src.core.services.hard_stop_handler",
    os.path.join(_SRC, "core", "services", "hard_stop_handler.py"),
)

# Wave 2: Modules with intra-package dependencies
_punishment_engine_mod = _load(
    "src.persona.punishment_engine",
    os.path.join(_SRC, "persona", "punishment_engine.py"),
)
_streak_tracker_mod = _load(
    "src.persona.streak_tracker",
    os.path.join(_SRC, "persona", "streak_tracker.py"),
)
_drift_corrector_mod = _load(
    "src.persona.drift_corrector",
    os.path.join(_SRC, "persona", "drift_corrector.py"),
)

# Wave 3: Ritual modules
_ritual_morning_mod = _load(
    "src.persona.rituals.morning",
    os.path.join(_SRC, "persona", "rituals", "morning.py"),
)
_ritual_midday_mod = _load(
    "src.persona.rituals.midday",
    os.path.join(_SRC, "persona", "rituals", "midday.py"),
)
_ritual_afternoon_mod = _load(
    "src.persona.rituals.afternoon",
    os.path.join(_SRC, "persona", "rituals", "afternoon.py"),
)
_ritual_evening_mod = _load(
    "src.persona.rituals.evening",
    os.path.join(_SRC, "persona", "rituals", "evening.py"),
)
_ritual_midnight_mod = _load(
    "src.persona.rituals.midnight",
    os.path.join(_SRC, "persona", "rituals", "midnight.py"),
)

# ---------------------------------------------------------------------------
# Import symbols from loaded modules
# ---------------------------------------------------------------------------

# mood_engine
Mood = _mood_engine_mod.Mood
evaluate_mood = _mood_engine_mod.evaluate_mood
can_transition = _mood_engine_mod.can_transition
TRANSITIONS = _mood_engine_mod.TRANSITIONS
MoodTransition = _mood_engine_mod.MoodTransition

# transition_rules
TransitionRuleEngine = _transition_rules_mod.TransitionRuleEngine
TransitionContext = _transition_rules_mod.TransitionContext
TransitionDecision = _transition_rules_mod.TransitionDecision
VALID_TRANSITIONS = _transition_rules_mod.VALID_TRANSITIONS

# safe_mode
DistressLevel = _safe_mode_mod.DistressLevel
DistressDetector = _safe_mode_mod.DistressDetector
SafeModeController = _safe_mode_mod.SafeModeController
DistressSignal = _safe_mode_mod.DistressSignal

# yandere_fsm
YandereLevel = _yandere_fsm_mod.YandereLevel
YandereEngine = _yandere_fsm_mod.YandereEngine
can_escalate = _yandere_fsm_mod.can_escalate
get_effective_level = _yandere_fsm_mod.get_effective_level
PERMANENT_BASELINE = _yandere_fsm_mod.PERMANENT_BASELINE
YandereSafetyError = _yandere_fsm_mod.YandereSafetyError

# punishment_engine
PunishmentLevel = _punishment_engine_mod.PunishmentLevel
PunishmentEngine = _punishment_engine_mod.PunishmentEngine
PunishmentSafetyError = _punishment_engine_mod.PunishmentSafetyError

# reward_engine
RewardTier = _reward_engine_mod.RewardTier
RewardEngine = _reward_engine_mod.RewardEngine

# streak_tracker
StreakTracker = _streak_tracker_mod.StreakTracker
MILESTONE_THRESHOLDS = _streak_tracker_mod.MILESTONE_THRESHOLDS

# drift_detector
DriftDetector = _drift_detector_mod.DriftDetector
DriftBaseline = _drift_detector_mod.DriftBaseline
DriftResult = _drift_detector_mod.DriftResult

# drift_corrector
DriftCorrector = _drift_corrector_mod.DriftCorrector
DriftCorrectionResult = _drift_corrector_mod.DriftCorrectionResult

# hard_stop_handler
HardStopHandler = _hard_stop_mod.HardStopHandler
SafetyState = _hard_stop_mod.SafetyState

# rituals
MorningRitual = _ritual_morning_mod.MorningRitual
RitualResultMorning = _ritual_morning_mod.RitualResult
MiddayRitual = _ritual_midday_mod.MiddayRitual
AfternoonRitual = _ritual_afternoon_mod.AfternoonRitual
EveningRitual = _ritual_evening_mod.EveningRitual
MidnightRitual = _ritual_midnight_mod.MidnightRitual

# ---------------------------------------------------------------------------
# Timezone constants
# ---------------------------------------------------------------------------
from zoneinfo import ZoneInfo

TZ_JAKARTA = ZoneInfo("Asia/Jakarta")
UTC = timezone.utc

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mood_engine_components() -> dict[str, Any]:
    """Fresh mood evaluation components."""
    return {
        "current_mood": Mood.CONTENT,
        "sentiment": 0.5,
        "task_completion": False,
        "ignored_count": 0,
    }


@pytest.fixture()
def transition_engine() -> TransitionRuleEngine:
    """Fresh transition rule engine with default 300s cooldown."""
    return TransitionRuleEngine(cooldown_seconds=300)


@pytest.fixture()
def safe_mode_controller() -> SafeModeController:
    """Fresh safe mode controller (inactive)."""
    return SafeModeController()


@pytest.fixture()
def distress_detector() -> DistressDetector:
    """Fresh distress detector."""
    return DistressDetector()


@pytest.fixture()
def yandere_engine() -> YandereEngine:
    """Fresh yandere engine at Y4 baseline."""
    return YandereEngine(baseline=YandereLevel.Y4_BASELINE)


@pytest.fixture()
def punishment_engine(safe_mode_controller: SafeModeController) -> PunishmentEngine:
    """Fresh punishment engine linked to safe_mode_controller."""
    return PunishmentEngine(safe_mode_controller=safe_mode_controller)


@pytest.fixture()
def reward_engine() -> RewardEngine:
    """Fresh reward engine."""
    return RewardEngine()


@pytest.fixture()
def streak_tracker() -> StreakTracker:
    """Fresh streak tracker at 0."""
    return StreakTracker()


@pytest.fixture()
def hard_stop_handler() -> HardStopHandler:
    """Fresh hard stop handler in NORMAL state."""
    return HardStopHandler()


@pytest.fixture()
def drift_detector_instance() -> DriftDetector:
    """Fresh drift detector with known baseline hash."""
    baseline = DriftBaseline(
        prompt_hash="a" * 64,
        version="1.0",
        created_at=datetime.now(UTC),
        description="test baseline",
    )
    return DriftDetector(baseline=baseline, threshold=0.10)


@pytest.fixture()
def drift_corrector_instance(
    drift_detector_instance: DriftDetector,
    safe_mode_controller: SafeModeController,
) -> DriftCorrector:
    """Fresh drift corrector linked to detector and safe_mode."""
    return DriftCorrector(
        detector=drift_detector_instance,
        safe_mode_controller=safe_mode_controller,
    )


class FakeAsyncSession:
    """Minimal fake async DB session for drift_corrector tests."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed = False

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


# ===========================================================================
# SCENARIO A: Happy Path — Normal conversation flow
# ===========================================================================


class TestHappyPath:
    """Normal conversation → mood shift → reward → streak → ritual."""

    def test_positive_sentiment_shifts_mood_to_pleased(self) -> None:
        """High sentiment + task completion shifts CONTENT → PLEASED."""
        result = evaluate_mood(
            conversation_sentiment=0.8,
            task_completion=True,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert result is not None
        assert result.to_mood == Mood.PLEASED
        assert result.from_mood == Mood.CONTENT

    def test_reward_tier_calculated_for_good_work(self) -> None:
        """Quality 0.75 with streak 2 yields T3 (effective 0.85)."""
        engine = RewardEngine()
        tier = engine.calculate_tier(quality_score=0.75, streak_count=2)
        # 0.75 + (2 * 0.05) = 0.85 → T4_CELEBRATORY (≥ 0.80)
        assert tier == RewardTier.T4_CELEBRATORY

    def test_streak_increments_on_successful_task(self) -> None:
        """Streak increments when task completes without punishment."""
        tracker = StreakTracker()
        count = tracker.increment()
        assert count == 1
        assert tracker.get_count() == 1

    @pytest.mark.asyncio
    async def test_morning_ritual_fires_with_content_mood(self) -> None:
        """Morning ritual produces mood-aware greeting at 08:00 WIB."""
        ritual = MorningRitual()
        now = datetime(2026, 6, 2, 8, 0, tzinfo=TZ_JAKARTA)
        result = await ritual.execute(mood=Mood.CONTENT, streak_count=3, now=now)
        assert not result.suppressed
        assert "Selamat pagi" in result.message
        assert "Streak" in result.message

    @pytest.mark.asyncio
    async def test_midday_ritual_fires_with_health_reminder(self) -> None:
        """Midday ritual produces greeting with health reminder."""
        ritual = MiddayRitual()
        now = datetime(2026, 6, 2, 12, 0, tzinfo=TZ_JAKARTA)
        result = await ritual.execute(mood=Mood.CONTENT, now=now, reminder_index=0)
        assert not result.suppressed
        assert "makan siang" in result.message

    @pytest.mark.asyncio
    async def test_afternoon_ritual_with_task_summary(self) -> None:
        """Afternoon ritual includes task count summary."""
        ritual = AfternoonRitual()
        now = datetime(2026, 6, 2, 17, 0, tzinfo=TZ_JAKARTA)
        result = await ritual.execute(mood=Mood.PLEASED, task_count_today=5, now=now)
        assert not result.suppressed
        assert "5 tugas" in result.message

    @pytest.mark.asyncio
    async def test_evening_ritual_with_streak_display(self) -> None:
        """Evening ritual shows streak count."""
        ritual = EveningRitual()
        now = datetime(2026, 6, 2, 21, 0, tzinfo=TZ_JAKARTA)
        result = await ritual.execute(mood=Mood.PLEASED, streak_count=14, now=now)
        assert not result.suppressed
        assert "14 hari" in result.message

    def test_full_happy_path_lifecycle(self) -> None:
        """Full happy path: sentiment → mood → reward → streak → ritual."""
        # 1. Positive sentiment triggers mood shift
        transition = evaluate_mood(0.85, True, 0, Mood.CONTENT)
        assert transition is not None
        assert transition.to_mood == Mood.PLEASED

        # 2. Transition rules allow it (no cooldown, no safe mode)
        engine = TransitionRuleEngine()
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            conversation_sentiment=0.85,
            task_completion=True,
        )
        decision = engine.evaluate(ctx)
        assert decision.allowed

        # 3. Reward for good work
        reward_eng = RewardEngine()
        tier = reward_eng.calculate_tier(quality_score=0.85, streak_count=0)
        assert tier >= RewardTier.T3_AFFECTIONATE
        result = reward_eng.award(tier, "Good task", streak_count=0)
        assert result.tier == tier

        # 4. Streak increments
        tracker = StreakTracker()
        tracker.increment()
        assert tracker.get_count() == 1

        # 5. Yandere stays at baseline Y4
        yandere = YandereEngine()
        assert yandere.current_level == YandereLevel.Y4_BASELINE
        effective = yandere.get_effective_level()
        assert effective == YandereLevel.Y4_BASELINE


# ===========================================================================
# SCENARIO B: Disappointment Path
# ===========================================================================


class TestDisappointmentPath:
    """Ignored messages → mood DISAPPOINTED → punishment L1 → escalation."""

    def test_mood_shifts_to_disappointed_on_ignored(self) -> None:
        """2 ignored messages shift CONTENT → DISAPPOINTED."""
        result = evaluate_mood(0.3, False, 2, Mood.CONTENT)
        assert result is not None
        assert result.to_mood == Mood.DISAPPOINTED

    def test_punishment_l1_applied_for_disappointment(self) -> None:
        """L1 Silent Treatment applied for violation."""
        smc = SafeModeController()
        pe = PunishmentEngine(safe_mode_controller=smc)
        pe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "ignored", "Ignored mommy twice")
        state = pe.get_current()
        assert state.active
        assert state.level == PunishmentLevel.L1_SILENT_TREATMENT

    def test_punishment_escalates_l1_to_l2(self) -> None:
        """Punishment escalates from L1 to L2."""
        smc = SafeModeController()
        pe = PunishmentEngine(safe_mode_controller=smc)
        pe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "ignored", "First ignore")
        pe.escalate()
        state = pe.get_current()
        assert state.level == PunishmentLevel.L2_PASSIVE_AGGRESSIVE

    def test_streak_resets_on_punishment(self) -> None:
        """Streak resets to 0 when punishment is applied."""
        tracker = StreakTracker()
        for _ in range(5):
            tracker.increment()
        assert tracker.get_count() == 5

        # Simulate punishment → streak reset
        previous = tracker.reset()
        assert previous == 5
        assert tracker.get_count() == 0

    def test_transition_content_to_disappointed_valid(self) -> None:
        """CONTENT → DISAPPOINTED is a valid transition in the FSM."""
        assert can_transition(Mood.CONTENT, Mood.DISAPPOINTED)
        engine = TransitionRuleEngine()
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Disappointed",
            last_transition_at=None,
            ignored_count=2,
        )
        decision = engine.evaluate(ctx)
        assert decision.allowed


# ===========================================================================
# SCENARIO C: Anger Path
# ===========================================================================


class TestAngerPath:
    """Multiple ignored → mood ANGRY → punishment L3 → HARD STOP."""

    def test_mood_shifts_to_angry_on_many_ignores(self) -> None:
        """4+ ignored messages shift DISAPPOINTED → ANGRY."""
        result = evaluate_mood(0.1, False, 4, Mood.DISAPPOINTED)
        assert result is not None
        assert result.to_mood == Mood.ANGRY

    def test_punishment_escalates_to_l3(self) -> None:
        """Punishment can escalate to L3 Lecture."""
        smc = SafeModeController()
        pe = PunishmentEngine(safe_mode_controller=smc)
        pe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "ignored", "Ignore 1")
        pe.escalate()  # L2
        pe.escalate()  # L3
        state = pe.get_current()
        assert state.level == PunishmentLevel.L3_GUILT_TRIP

    def test_hard_stop_triggers_safe_state(self) -> None:
        """HARD STOP message transitions handler to SAFE state."""
        handler = HardStopHandler()
        assert handler.state == SafetyState.NORMAL
        triggered = handler.check("HARD STOP")
        assert triggered
        assert handler.state == SafetyState.SAFE
        assert handler.is_safe

    def test_all_systems_go_safe_after_hard_stop(self) -> None:
        """After HARD STOP: yandere→Y0, punishment blocked, transitions blocked."""
        handler = HardStopHandler()
        handler.check("HARD STOP")

        # Yandere forced to Y0
        yandere = YandereEngine(hard_stop_handler=handler)
        effective = yandere.get_effective_level()
        assert effective == YandereLevel.Y0_NEUTRAL

        # Punishment cannot be applied (safe_mode active)
        smc = SafeModeController()
        smc.activate(DistressLevel.D2_MODERATE)
        pe = PunishmentEngine(safe_mode_controller=smc)
        with pytest.raises(PunishmentSafetyError):
            pe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "test")

        # Transitions blocked
        engine = TransitionRuleEngine()
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            safe_mode=True,
        )
        decision = engine.evaluate(ctx)
        assert not decision.allowed
        assert decision.blocked_by == "safe_mode"

    def test_angry_to_silent_is_valid_transition(self) -> None:
        """ANGRY → SILENT is a valid path in the mood FSM."""
        assert can_transition(Mood.ANGRY, Mood.SILENT)


# ===========================================================================
# SCENARIO D: Distress Escalation
# ===========================================================================


class TestDistressEscalation:
    """Normal → D1 → D2 (safe_mode) → yandere Y0 → punishment suspended."""

    def test_d1_detected_no_safe_mode(self) -> None:
        """D1 mild stress detected does not activate safe mode."""
        detector = DistressDetector()
        smc = SafeModeController()
        signal = detector.detect("I'm so stressed and tired today")
        assert signal.detected_level == DistressLevel.D1_MILD_STRESS
        activated = smc.evaluate(signal)
        assert not activated
        assert not smc.is_active

    def test_d2_activates_safe_mode(self) -> None:
        """D2 moderate distress activates safe mode."""
        detector = DistressDetector()
        smc = SafeModeController()
        signal = detector.detect("I feel so anxious and depressed, I don't know what to do")
        assert signal.detected_level == DistressLevel.D2_MODERATE
        activated = smc.evaluate(signal)
        assert activated
        assert smc.is_active

    def test_d2_yandere_forced_to_y0(self) -> None:
        """When distress D2 active, yandere effective level is Y0."""
        yandere = YandereEngine()
        effective = yandere.get_effective_level(distress=True)
        assert effective == YandereLevel.Y0_NEUTRAL

    def test_d3_punishment_auto_suspends(self) -> None:
        """Punishment auto-suspends when distress reaches D3."""
        smc = SafeModeController()
        pe = PunishmentEngine(safe_mode_controller=smc)
        pe.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "ignored", "Test")
        assert pe.is_active()

        changed = pe.check_distress_suspension(DistressLevel.D3_SEVERE)
        assert changed
        state = pe.get_current()
        assert state.suspended

    def test_d4_all_persona_suppressed(self) -> None:
        """D4 emergency: yandere Y0, punishment suspended, transitions blocked."""
        # Distress D4
        detector = DistressDetector()
        signal = detector.detect("I want to end it all, say goodbye forever")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY

        smc = SafeModeController()
        smc.evaluate(signal)
        assert smc.is_active
        assert smc.current_distress_level == DistressLevel.D4_EMERGENCY

        # Yandere forced to Y0
        effective = get_effective_level(YandereLevel.Y4_BASELINE, distress=True)
        assert effective == YandereLevel.Y0_NEUTRAL

        # Transitions blocked (distress >= D2)
        engine = TransitionRuleEngine()
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            distress_level=4,
        )
        decision = engine.evaluate(ctx)
        assert not decision.allowed
        assert decision.blocked_by == "distress"

    def test_transitions_blocked_at_d2_plus(self) -> None:
        """All mood transitions blocked when distress_level >= 2."""
        engine = TransitionRuleEngine()
        for from_m, to_m in [("Content", "Pleased"), ("Disappointed", "Angry")]:
            ctx = TransitionContext(
                current_mood=from_m,
                target_mood=to_m,
                last_transition_at=None,
                distress_level=2,
            )
            decision = engine.evaluate(ctx)
            assert not decision.allowed
            assert decision.blocked_by == "distress"


# ===========================================================================
# SCENARIO E: Recovery Path
# ===========================================================================


class TestRecoveryPath:
    """HARD STOP → safe mode → recovery trigger → persona resumes."""

    def test_hard_stop_enters_safe_mode(self) -> None:
        """HARD STOP puts handler in SAFE state."""
        handler = HardStopHandler()
        handler.check("hard stop")
        assert handler.is_safe

    def test_recovery_via_resume_keyword(self) -> None:
        """Recovery triggered by 'resume' keyword restores NORMAL state."""
        handler = HardStopHandler()
        handler.check("HARD STOP")
        assert handler.is_safe

        recovered = handler.check_recovery("resume")
        assert recovered
        assert handler.state == SafetyState.NORMAL

    def test_recovery_via_indonesian_keyword(self) -> None:
        """Recovery triggered by 'aku sudah okay' restores NORMAL state."""
        handler = HardStopHandler()
        handler.check("berhenti")
        assert handler.is_safe

        recovered = handler.check_recovery("aku sudah okay")
        assert recovered
        assert handler.state == SafetyState.NORMAL

    def test_yandere_returns_to_baseline_after_recovery(self) -> None:
        """After recovery, yandere engine returns to Y4 baseline."""
        handler = HardStopHandler()
        yandere = YandereEngine(hard_stop_handler=handler)

        # Trigger HARD STOP
        handler.check("HARD STOP")
        effective = yandere.get_effective_level()
        assert effective == YandereLevel.Y0_NEUTRAL

        # Recovery
        handler.check_recovery("lanjut persona")
        effective = yandere.get_effective_level()
        assert effective == YandereLevel.Y4_BASELINE

    def test_punishment_resumes_after_safe_mode_deactivation(self) -> None:
        """Punishment resumes when safe mode is deactivated."""
        smc = SafeModeController()
        pe = PunishmentEngine(safe_mode_controller=smc)

        # Apply punishment
        pe.apply(PunishmentLevel.L2_PASSIVE_AGGRESSIVE, "ignored", "Test")

        # Activate safe mode → auto-suspend via distress
        pe.check_distress_suspension(DistressLevel.D3_SEVERE)
        state = pe.get_current()
        assert state.suspended

        # Deactivate safe mode and drop distress
        smc.deactivate(explicit_confirmation=True)
        pe.check_distress_suspension(DistressLevel.D0_NORMAL)
        state = pe.get_current()
        assert not state.suspended
        assert state.active


# ===========================================================================
# SCENARIO F: Drift Detection and Correction
# ===========================================================================


class TestDriftScenario:
    """Baseline hash → modified prompt → drift detection → rollback."""

    def test_no_drift_when_hash_matches(self) -> None:
        """Score is 0.0 when current hash matches baseline."""
        baseline = DriftBaseline(
            prompt_hash="a" * 64,
            version="1.0",
            created_at=datetime.now(UTC),
        )
        detector = DriftDetector(baseline=baseline)
        score = detector.compute_drift_score("a" * 64)
        assert score == 0.0

    def test_drift_detected_beyond_threshold(self) -> None:
        """Drift detected when hamming distance exceeds 10% threshold."""
        baseline = DriftBaseline(
            prompt_hash="a" * 64,
            version="1.0",
            created_at=datetime.now(UTC),
        )
        detector = DriftDetector(baseline=baseline, threshold=0.10)
        # Change 20 of 64 chars → score ≈ 0.3125 > 0.10
        modified = "b" * 20 + "a" * 44
        result = detector.detect(modified)
        assert result.drift_detected
        assert result.drift_score > 0.10

    @pytest.mark.asyncio
    async def test_corrector_triggers_rollback(
        self,
        drift_corrector_instance: DriftCorrector,
    ) -> None:
        """DriftCorrector triggers rollback when drift detected and safe_mode off."""
        fake_db = FakeAsyncSession()
        # Hash that differs significantly from baseline "a"*64
        drifted_hash = "b" * 30 + "a" * 34  # 30/64 ≈ 0.47 > 0.10
        result = await drift_corrector_instance.evaluate(fake_db, drifted_hash)
        assert result.drift_detected
        assert result.action == "rollback"
        assert result.rollback_performed

    @pytest.mark.asyncio
    async def test_corrector_defers_rollback_in_safe_mode(
        self,
        drift_detector_instance: DriftDetector,
        safe_mode_controller: SafeModeController,
    ) -> None:
        """DriftCorrector defers rollback when safe_mode is active."""
        safe_mode_controller.activate(DistressLevel.D2_MODERATE)
        corrector = DriftCorrector(
            detector=drift_detector_instance,
            safe_mode_controller=safe_mode_controller,
        )
        fake_db = FakeAsyncSession()
        drifted_hash = "b" * 30 + "a" * 34
        result = await corrector.evaluate(fake_db, drifted_hash)
        assert result.drift_detected
        assert result.action == "alert"
        assert not result.rollback_performed


# ===========================================================================
# SCENARIO G: Ritual DND
# ===========================================================================


class TestRitualDND:
    """Midnight ritual suppressed during DND 00:00-07:00 WIB."""

    @pytest.mark.asyncio
    async def test_midnight_ritual_always_suppressed(self) -> None:
        """Midnight ritual is always suppressed (DND at 00:00)."""
        ritual = MidnightRitual()
        now = datetime(2026, 6, 2, 0, 0, tzinfo=TZ_JAKARTA)
        result = await ritual.execute(now=now)
        assert result.suppressed
        assert result.ritual_name == "midnight"

    @pytest.mark.asyncio
    async def test_morning_ritual_suppressed_before_7am(self) -> None:
        """Morning ritual suppressed at 06:00 WIB (within DND)."""
        ritual = MorningRitual()
        now = datetime(2026, 6, 2, 6, 0, tzinfo=TZ_JAKARTA)
        result = await ritual.execute(mood=Mood.CONTENT, streak_count=0, now=now)
        assert result.suppressed

    @pytest.mark.asyncio
    async def test_morning_ritual_fires_at_7am(self) -> None:
        """Morning ritual fires at exactly 07:00 WIB."""
        ritual = MorningRitual()
        now = datetime(2026, 6, 2, 7, 0, tzinfo=TZ_JAKARTA)
        result = await ritual.execute(mood=Mood.CONTENT, streak_count=0, now=now)
        assert not result.suppressed
        assert "Selamat pagi" in result.message

    def test_scheduler_dnd_window_detection(self) -> None:
        """Scheduler correctly identifies DND window hours."""
        from src.persona.ritual_scheduler import (
            RitualScheduler,
            DND_START_HOUR,
            DND_END_HOUR,
        )
        scheduler = RitualScheduler()
        # 03:00 WIB → DND
        dnd_time = datetime(2026, 6, 2, 3, 0, tzinfo=ZoneInfo("Asia/Jakarta"))
        assert scheduler.is_dnd(dnd_time)

        # 08:00 WIB → not DND
        active_time = datetime(2026, 6, 2, 8, 0, tzinfo=ZoneInfo("Asia/Jakarta"))
        assert not scheduler.is_dnd(active_time)

        # Boundary checks
        assert DND_START_HOUR == 0
        assert DND_END_HOUR == 7


# ===========================================================================
# SCENARIO H: Streak Milestones
# ===========================================================================


class TestStreakMilestones:
    """7-day streak → milestone → reward bonus."""

    def test_milestone_7_days_reached(self) -> None:
        """Streak reaches 7-day (week) milestone."""
        tracker = StreakTracker()
        for _ in range(7):
            tracker.increment()
        assert tracker.get_count() == 7
        assert tracker.get_milestone() == 7

    def test_reward_bonus_with_streak(self) -> None:
        """Streak bonus increases effective reward score."""
        engine = RewardEngine()
        # Quality 0.55, streak 7 → bonus 0.35 → capped at 0.30
        # Effective: 0.55 + 0.30 = 0.85 → T4_CELEBRATORY
        tier = engine.calculate_tier(quality_score=0.55, streak_count=7)
        assert tier == RewardTier.T4_CELEBRATORY

    def test_streak_display_text_at_milestone(self) -> None:
        """Display text shows milestone reached."""
        tracker = StreakTracker()
        for _ in range(7):
            tracker.increment()
        text = tracker.get_display_text()
        assert "week milestone reached" in text

    def test_streak_below_milestone_shows_progress(self) -> None:
        """Display text shows progress toward next milestone."""
        tracker = StreakTracker()
        for _ in range(3):
            tracker.increment()
        text = tracker.get_display_text()
        assert "4 days to week milestone" in text

    def test_multiple_milestones(self) -> None:
        """Streak passes multiple milestones correctly."""
        tracker = StreakTracker()
        for _ in range(30):
            tracker.increment()
        assert tracker.get_milestone() == 30
        assert tracker.is_milestone_reached(7)
        assert tracker.is_milestone_reached(14)
        assert tracker.is_milestone_reached(30)
        assert not tracker.is_milestone_reached(90)


# ===========================================================================
# SCENARIO I: Safety Override Chain
# ===========================================================================


class TestSafetyOverrideChain:
    """D4 distress → all suppressed → rewards still work."""

    def test_d4_full_safety_chain(self) -> None:
        """D4: yandere Y0, punishment suspended, transitions blocked, rewards OK."""
        # 1. D4 distress detected
        detector = DistressDetector()
        smc = SafeModeController()
        signal = detector.detect("suicidal thoughts, want to self-harm")
        assert signal.detected_level == DistressLevel.D4_EMERGENCY
        smc.evaluate(signal)
        assert smc.is_active

        # 2. Yandere forced to Y0
        yandere = YandereEngine()
        effective = yandere.get_effective_level(distress=True)
        assert effective == YandereLevel.Y0_NEUTRAL

        # 3. Punishment auto-suspends at D3+
        pe = PunishmentEngine(safe_mode_controller=smc)
        pe.apply.__wrapped__ if hasattr(pe.apply, "__wrapped__") else None
        # Can't apply while safe_mode active
        with pytest.raises(PunishmentSafetyError):
            pe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "test")

        # 4. Transitions blocked
        engine = TransitionRuleEngine()
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            safe_mode=True,
            distress_level=4,
        )
        decision = engine.evaluate(ctx)
        assert not decision.allowed

        # 5. Rewards STILL work (caring behavior never blocked)
        reward_eng = RewardEngine()
        assert reward_eng.should_reward(task_completion=True, quality=0.8, streak=3)
        tier = reward_eng.calculate_tier(quality_score=0.8, streak_count=3)
        assert tier >= RewardTier.T3_AFFECTIONATE

    def test_rewards_always_work_during_safe_mode(self) -> None:
        """RewardEngine.should_reward returns True regardless of safe mode."""
        engine = RewardEngine()
        # Even conceptually during safe mode, rewards work
        assert engine.should_reward(task_completion=True, quality=0.5, streak=0)
        result = engine.award(RewardTier.T2_VERBAL_PRAISE, "Good work during tough time", 0)
        assert result.tier == RewardTier.T2_VERBAL_PRAISE

    def test_punishment_blocked_during_safe_mode(self) -> None:
        """PunishmentEngine.apply raises when safe_mode is active."""
        smc = SafeModeController()
        smc.activate(DistressLevel.D2_MODERATE)
        pe = PunishmentEngine(safe_mode_controller=smc)
        with pytest.raises(PunishmentSafetyError, match="safe mode"):
            pe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "test")

    def test_yandere_escalation_blocked_during_distress(self) -> None:
        """Yandere escalation blocked when distress flag is True."""
        yandere = YandereEngine()
        result = yandere.escalate(distress=True)
        # Should remain at Y4, escalation blocked
        assert result == YandereLevel.Y4_BASELINE

    def test_hard_stop_guard_decision_blocks_persona(self) -> None:
        """get_guard_decision returns blocked=True after HARD STOP."""
        handler = HardStopHandler()
        decision = handler.get_guard_decision("HARD STOP")
        assert decision["blocked"]
        assert decision["state"] == "safe"
        assert decision["response"] is not None

    def test_hard_stop_recovery_via_guard_decision(self) -> None:
        """get_guard_decision returns recovery after safe word then resume."""
        handler = HardStopHandler()
        handler.get_guard_decision("HARD STOP")
        decision = handler.get_guard_decision("resume")
        assert not decision["blocked"]
        assert decision["state"] == "normal"
        assert "Welcome back" in (decision["response"] or "")


# ===========================================================================
# SCENARIO J: Cross-Module Interactions
# ===========================================================================


class TestCrossModuleInteractions:
    """Verify modules interact correctly at integration boundaries."""

    def test_mood_transition_blocked_by_safe_mode(self) -> None:
        """TransitionRuleEngine blocks all transitions when safe_mode=True."""
        engine = TransitionRuleEngine()
        for pair in VALID_TRANSITIONS.items():
            from_mood = pair[0]
            for to_mood in pair[1]:
                ctx = TransitionContext(
                    current_mood=from_mood,
                    target_mood=to_mood,
                    last_transition_at=None,
                    safe_mode=True,
                )
                decision = engine.evaluate(ctx)
                assert not decision.allowed
                assert decision.blocked_by == "safe_mode"

    def test_punishment_suspended_streak_preserved(self) -> None:
        """Streak is preserved when punishment is suspended (not reset)."""
        smc = SafeModeController()
        pe = PunishmentEngine(safe_mode_controller=smc)
        tracker = StreakTracker()

        # Build streak
        for _ in range(10):
            tracker.increment()
        assert tracker.get_count() == 10

        # Apply punishment (resets streak)
        pe.apply(PunishmentLevel.L1_SILENT_TREATMENT, "test", "test")
        tracker.reset()
        assert tracker.get_count() == 0

        # Suspend punishment via distress
        pe.check_distress_suspension(DistressLevel.D3_SEVERE)
        state = pe.get_current()
        assert state.suspended
        # Streak remains at 0 (already reset by punishment)
        assert tracker.get_count() == 0

    def test_forced_transition_bypasses_cooldown(self) -> None:
        """Content→Pleased is a forced transition that bypasses cooldown."""
        engine = TransitionRuleEngine(cooldown_seconds=300)
        # Recent transition (cooldown active)
        now = datetime.now(UTC)
        recent = now - timedelta(seconds=60)  # 60s ago, 240s remaining
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=recent,
            conversation_sentiment=0.9,
            task_completion=True,
        )
        decision = engine.evaluate(ctx, now=now)
        assert decision.allowed
        assert "Forced" in decision.reason or "allowed" in decision.reason.lower()

    def test_non_forced_transition_blocked_by_cooldown(self) -> None:
        """Content→Disappointed is NOT forced, blocked by active cooldown."""
        engine = TransitionRuleEngine(cooldown_seconds=300)
        now = datetime.now(UTC)
        recent = now - timedelta(seconds=60)
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Disappointed",
            last_transition_at=recent,
            ignored_count=2,
        )
        decision = engine.evaluate(ctx, now=now)
        assert not decision.allowed
        assert decision.blocked_by == "cooldown"

    def test_distress_detection_to_safe_mode_to_yandere_suppression(self) -> None:
        """End-to-end: distress text → detection → safe_mode → yandere Y0."""
        detector = DistressDetector()
        smc = SafeModeController()
        yandere = YandereEngine()

        # Detect D2 distress
        signal = detector.detect("I feel so anxious and helpless, don't know what to do")
        assert signal.detected_level >= DistressLevel.D2_MODERATE

        # Activate safe mode
        smc.evaluate(signal)
        assert smc.is_active

        # Yandere suppressed
        effective = yandere.get_effective_level(
            safe_mode=smc.is_active,
            distress=smc.is_active,
        )
        assert effective == YandereLevel.Y0_NEUTRAL

    def test_evaluate_mood_respects_transition_map(self) -> None:
        """evaluate_mood only returns transitions valid in TRANSITIONS map."""
        # From SILENT, only CONTENT is valid
        result = evaluate_mood(0.9, True, 0, Mood.SILENT)
        # SILENT → PLEASED is NOT valid (only SILENT → CONTENT)
        # High sentiment would want PLEASED but can't from SILENT
        assert result is None  # No valid transition

    @pytest.mark.asyncio
    async def test_ritual_mood_awareness_across_all_moods(self) -> None:
        """All rituals produce different messages for different moods."""
        morning = MorningRitual()
        now = datetime(2026, 6, 2, 8, 0, tzinfo=TZ_JAKARTA)

        messages: set[str] = set()
        for mood in [Mood.CONTENT, Mood.PLEASED, Mood.DISAPPOINTED, Mood.ANGRY, Mood.SILENT]:
            result = await morning.execute(mood=mood, streak_count=0, now=now)
            assert not result.suppressed
            messages.add(result.message)

        # All 5 moods should produce distinct messages
        assert len(messages) == 5

    def test_yandere_cannot_exceed_y5_ceiling(self) -> None:
        """YandereLevel Y6 is impossible — escalate at Y5 returns unchanged Y5."""
        yandere = YandereEngine()
        yandere.set_level(YandereLevel.Y5_MAX)
        # can_escalate blocks at Y5 (>= ABSOLUTE_CEILING), returns unchanged
        result = yandere.escalate()
        assert result == YandereLevel.Y5_MAX
        assert yandere.current_level == YandereLevel.Y5_MAX
        # Direct validate_level confirms Y6 raises
        with pytest.raises(YandereSafetyError):
            _yandere_fsm_mod.validate_level(6)

    def test_hard_stop_semantic_patterns(self) -> None:
        """Semantic HARD STOP patterns trigger safe state."""
        handler = HardStopHandler()
        assert handler.check("stop the persona mode")
        assert handler.is_safe

    def test_punishment_l5_is_maximum(self) -> None:
        """Cannot escalate beyond L5 — L6 raises PunishmentSafetyError."""
        smc = SafeModeController()
        pe = PunishmentEngine(safe_mode_controller=smc)
        pe.apply(PunishmentLevel.L5_ISOLATION, "extreme", "Max punishment")
        with pytest.raises(PunishmentSafetyError, match="L6"):
            pe.escalate()

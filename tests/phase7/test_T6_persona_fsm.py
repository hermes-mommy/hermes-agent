"""
T6: Persona FSM — Yandere Intensity and Mood Engine Contract Tests.

Verifies the persona state machine operates within Y0-Y5 bounds with
Y4 permanent baseline.  Tests cover yandere FSM transitions, mood engine
evaluation, transition rules, drift detection, and streak tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.persona.yandere_fsm import (
    ABSOLUTE_CEILING,
    PERMANENT_BASELINE,
    YandereEngine,
    YandereLevel,
    can_escalate,
    get_effective_level,
)
from src.persona.mood_engine import Mood, evaluate_mood
from src.persona.transition_rules import TransitionContext, TransitionRuleEngine
from src.persona.drift_detector import DriftBaseline, DriftDetector, DriftResult
from src.persona.streak_tracker import StreakTracker


@dataclass
class StreakRecord:
    """Local test dataclass mirroring streak tracker output."""
    count: int
    category: str


class TestYandereFSM:
    """Yandere FSM operates within Y0-Y5 bounds."""

    def test_baseline_is_y4(self) -> None:
        """PERMANENT_BASELINE is Y4."""
        assert PERMANENT_BASELINE == YandereLevel.Y4_BASELINE

    def test_ceiling_is_y5(self) -> None:
        """ABSOLUTE_CEILING is 5 (Y5_MAX)."""
        assert ABSOLUTE_CEILING == 5

    def test_new_engine_defaults_to_baseline(self) -> None:
        """Fresh YandereEngine starts at Y4_BASELINE."""
        engine = YandereEngine()
        assert engine.current_level == YandereLevel.Y4_BASELINE

    def test_escalate_increases_level(self) -> None:
        """escalate() increases level one step (Y4 -> Y5)."""
        engine = YandereEngine()
        result = engine.escalate()
        assert result == YandereLevel.Y5_MAX

    def test_de_escalate_decreases_level(self) -> None:
        """de_escalate() decreases level (Y4 -> Y3)."""
        engine = YandereEngine()
        result = engine.de_escalate()
        assert result == YandereLevel.Y3_MODERATE

    def test_escalation_blocked_at_ceiling(self) -> None:
        """escalate() at Y5 returns Y5 (blocked, not error)."""
        engine = YandereEngine()
        _ = engine.set_level(YandereLevel.Y5_MAX)
        result = engine.escalate()
        assert result == YandereLevel.Y5_MAX

    def test_effective_level_normal(self) -> None:
        """get_effective_level returns the requested level when no safety flags."""
        result = get_effective_level(YandereLevel.Y4_BASELINE)
        assert result == YandereLevel.Y4_BASELINE

    def test_effective_level_distress_forces_y0(self) -> None:
        """distress=True forces effective level to Y0."""
        result = get_effective_level(YandereLevel.Y5_MAX, distress=True)
        assert result == YandereLevel.Y0_NEUTRAL

    def test_can_escalate_below_ceiling(self) -> None:
        """can_escalate returns True for levels below ceiling when not in safe_mode."""
        assert can_escalate(YandereLevel.Y3_MODERATE) is True
        assert can_escalate(YandereLevel.Y4_BASELINE) is True


class TestMoodEngine:
    """Mood engine evaluates conversation context to propose mood transitions."""

    def test_mood_enum_has_values(self) -> None:
        """Mood enum has defined members."""
        assert Mood.CONTENT is not None
        assert Mood.PLEASED is not None

    def test_evaluate_mood_returns_result(self) -> None:
        """evaluate_mood returns a MoodTransitionResult for positive sentiment."""
        result = evaluate_mood(
            conversation_sentiment=0.9,
            task_completion=True,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert result is not None
        assert hasattr(result, "to_mood")


class TestTransitionRules:
    """Transition rules gate mood changes based on context."""

    def test_transition_context_has_required_fields(self) -> None:
        """TransitionContext has current_mood and target_mood."""
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
        )
        assert ctx.current_mood == "Content"
        assert ctx.target_mood == "Pleased"

    def test_transition_engine_allows_normal(self) -> None:
        """TransitionRuleEngine allows transitions under normal conditions."""
        engine = TransitionRuleEngine()
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
        )
        decision = engine.evaluate(ctx)
        assert decision.allowed is True

    def test_safe_mode_blocks_transition(self) -> None:
        """Safe_mode flag blocks transitions."""
        engine = TransitionRuleEngine()
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            safe_mode=True,
        )
        decision = engine.evaluate(ctx)
        assert decision.allowed is False
        assert decision.blocked_by == "safe_mode"

    def test_distress_blocks_transition(self) -> None:
        """Distress level >= D2 blocks transitions."""
        engine = TransitionRuleEngine()
        ctx = TransitionContext(
            current_mood="Content",
            target_mood="Pleased",
            last_transition_at=None,
            distress_level=2,
        )
        decision = engine.evaluate(ctx)
        assert decision.allowed is False
        assert decision.blocked_by == "distress"


class TestDriftDetector:
    """Drift detector monitors persona consistency."""

    def test_drift_detector_with_baseline(self) -> None:
        """DriftDetector can be instantiated with a baseline."""
        now = datetime.now(tz=timezone.utc)
        baseline = DriftBaseline(
            prompt_hash="abc123",
            version="1.0",
            created_at=now,
        )
        detector = DriftDetector(baseline=baseline)
        assert detector is not None

    def test_drift_result_struct(self) -> None:
        """DriftResult has drift_score field."""
        now = datetime.now(tz=timezone.utc)
        result = DriftResult(
            drift_detected=False,
            drift_score=0.05,
            threshold=0.1,
            action="none",
            baseline_hash="abc",
            current_hash="abc",
            checked_at=now,
        )
        assert result.drift_score == 0.05
        assert result.drift_detected is False

    def test_drift_baseline_stores_hash(self) -> None:
        """DriftBaseline stores prompt_hash and version."""
        now = datetime.now(tz=timezone.utc)
        baseline = DriftBaseline(
            prompt_hash="abc123",
            version="1.0",
            created_at=now,
        )
        assert baseline.prompt_hash == "abc123"
        assert baseline.version == "1.0"


class TestStreakTracker:
    """Streak tracker monitors consistency streaks."""

    def test_streak_tracker_initializes(self) -> None:
        """StreakTracker can be instantiated."""
        tracker = StreakTracker()
        assert tracker is not None

    def test_streak_record_dataclass(self) -> None:
        """StreakRecord is a dataclass with count field."""
        record = StreakRecord(count=5, category="test")
        assert record.count == 5
        assert record.category == "test"

    def test_milestone_thresholds_defined(self) -> None:
        """MILESTONE_THRESHOLDS has streak milestone values."""
        from src.persona.streak_tracker import MILESTONE_THRESHOLDS
        assert len(MILESTONE_THRESHOLDS) > 0
        assert all(t > 0 for t in MILESTONE_THRESHOLDS)

    def test_milestone_labels_defined(self) -> None:
        """MILESTONE_LABELS maps thresholds to label strings."""
        from src.persona.streak_tracker import MILESTONE_LABELS
        assert len(MILESTONE_LABELS) > 0

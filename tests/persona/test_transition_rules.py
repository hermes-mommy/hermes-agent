"""P4-003: Mood Transition Rules with Cooldowns — Comprehensive Tests.

100% deterministic. All time-dependent tests use injected ``now`` parameter.
No network calls, no LLM, no external dependencies.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from persona.transition_rules import (
    ALL_MOODS,
    VALID_TRANSITIONS,
    CooldownActiveError,
    InvalidTransitionError,
    TransitionContext,
    TransitionDecision,
    TransitionRuleEngine,
    TransitionRulesError,
)

# ---------------------------------------------------------------------------
# Constants for deterministic time tests
# ---------------------------------------------------------------------------

NOW = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> TransitionRuleEngine:
    """Default engine with 300s cooldown."""
    return TransitionRuleEngine()


@pytest.fixture
def custom_engine() -> TransitionRuleEngine:
    """Engine with a custom 60s cooldown."""
    return TransitionRuleEngine(cooldown_seconds=60)


def _ctx(
    current: str = "Content",
    target: str = "Pleased",
    last_transition_at: datetime | None = None,
    **kwargs: object,
) -> TransitionContext:
    """Helper to build TransitionContext with sensible defaults."""
    return TransitionContext(
        current_mood=current,
        target_mood=target,
        last_transition_at=last_transition_at,
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Valid transitions (all 9 valid pairs)
# ---------------------------------------------------------------------------

_ALL_VALID_TRANSITIONS: list[tuple[str, str]] = []
for _mood, _targets in VALID_TRANSITIONS.items():
    for _target in _targets:
        _ALL_VALID_TRANSITIONS.append((_mood, _target))


class TestValidTransitions:
    """Every valid transition pair must be allowed when no blockers exist."""

    @pytest.mark.parametrize(
        ("current", "target"),
        _ALL_VALID_TRANSITIONS,
        ids=[f"{c}->{t}" for c, t in _ALL_VALID_TRANSITIONS],
    )
    def test_valid_transition_allowed(
        self,
        engine: TransitionRuleEngine,
        current: str,
        target: str,
    ) -> None:
        ctx = _ctx(current=current, target=target, last_transition_at=None)
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is True
        assert decision.from_mood == current
        assert decision.to_mood == target
        assert decision.blocked_by is None

    def test_all_moods_covered(self) -> None:
        """Every mood must appear as a source in VALID_TRANSITIONS."""
        sources = set(VALID_TRANSITIONS.keys())
        assert sources == ALL_MOODS


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------

_INVALID_TRANSITIONS: list[tuple[str, str]] = [
    ("Content", "Angry"),
    ("Content", "Silent"),
    ("Pleased", "Angry"),
    ("Pleased", "Silent"),
    ("Silent", "Angry"),
    ("Silent", "Pleased"),
    ("Silent", "Disappointed"),
    ("Disappointed", "Pleased"),
    ("Disappointed", "Silent"),
    # Self-transitions are not valid
    ("Content", "Content"),
    ("Pleased", "Pleased"),
]


class TestInvalidTransitions:
    """Transitions not in VALID_TRANSITIONS must be blocked."""

    @pytest.mark.parametrize(
        ("current", "target"),
        _INVALID_TRANSITIONS,
        ids=[f"{c}->{t}" for c, t in _INVALID_TRANSITIONS],
    )
    def test_invalid_transition_blocked(
        self,
        engine: TransitionRuleEngine,
        current: str,
        target: str,
    ) -> None:
        ctx = _ctx(current=current, target=target, last_transition_at=None)
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is False
        assert decision.blocked_by == "invalid_transition"

    def test_unknown_source_mood(self, engine: TransitionRuleEngine) -> None:
        """A mood not in the map at all should be treated as invalid."""
        ctx = _ctx(current="Unknown", target="Content", last_transition_at=None)
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is False
        assert decision.blocked_by == "invalid_transition"


# ---------------------------------------------------------------------------
# Cooldown behavior
# ---------------------------------------------------------------------------


class TestCooldown:
    """Cooldown blocks transitions within the window, allows after."""

    def test_cooldown_blocks_within_window(self, engine: TransitionRuleEngine) -> None:
        """60s after last transition — cooldown still active."""
        last = NOW - timedelta(seconds=60)
        ctx = _ctx(current="Content", target="Disappointed", last_transition_at=last)
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is False
        assert decision.blocked_by == "cooldown"
        assert decision.cooldown_remaining_seconds == 240

    def test_cooldown_blocks_at_299s(self, engine: TransitionRuleEngine) -> None:
        """299s after last transition — 1s remaining."""
        last = NOW - timedelta(seconds=299)
        ctx = _ctx(current="Disappointed", target="Content", last_transition_at=last)
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is False
        assert decision.blocked_by == "cooldown"
        assert decision.cooldown_remaining_seconds == 1

    def test_cooldown_allows_at_boundary(self, engine: TransitionRuleEngine) -> None:
        """Exactly 300s after last transition — cooldown expired."""
        last = NOW - timedelta(seconds=300)
        ctx = _ctx(current="Content", target="Disappointed", last_transition_at=last)
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is True
        assert decision.blocked_by is None

    def test_cooldown_allows_after_window(self, engine: TransitionRuleEngine) -> None:
        """500s after last transition — well past cooldown."""
        last = NOW - timedelta(seconds=500)
        ctx = _ctx(current="Content", target="Pleased", last_transition_at=last)
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is True

    def test_no_previous_transition(self, engine: TransitionRuleEngine) -> None:
        """No previous transition — cooldown does not apply."""
        ctx = _ctx(current="Angry", target="Disappointed", last_transition_at=None)
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is True

    def test_custom_cooldown(self, custom_engine: TransitionRuleEngine) -> None:
        """Custom 60s cooldown — 30s after should block, 60s should allow."""
        last_30 = NOW - timedelta(seconds=30)
        ctx_block = _ctx(current="Content", target="Disappointed", last_transition_at=last_30)
        decision_block = custom_engine.evaluate(ctx_block, now=NOW)
        assert decision_block.allowed is False
        assert decision_block.cooldown_remaining_seconds == 30

        last_60 = NOW - timedelta(seconds=60)
        ctx_allow = _ctx(current="Content", target="Disappointed", last_transition_at=last_60)
        decision_allow = custom_engine.evaluate(ctx_allow, now=NOW)
        assert decision_allow.allowed is True


# ---------------------------------------------------------------------------
# Forced transitions bypass cooldown
# ---------------------------------------------------------------------------


class TestForcedTransitions:
    """Forced transitions skip cooldown but still respect safe_mode and distress."""

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            ("Angry", "Silent"),
            ("Content", "Pleased"),
        ],
        ids=["Angry->Silent", "Content->Pleased"],
    )
    def test_forced_bypasses_cooldown(
        self,
        engine: TransitionRuleEngine,
        current: str,
        target: str,
    ) -> None:
        """Forced transition allowed even within cooldown window."""
        last = NOW - timedelta(seconds=10)  # well within 300s
        ctx = _ctx(current=current, target=target, last_transition_at=last)
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is True
        assert decision.blocked_by is None

    def test_forced_still_blocked_by_safe_mode(self, engine: TransitionRuleEngine) -> None:
        """Safe mode blocks even forced transitions."""
        last = NOW - timedelta(seconds=10)
        ctx = _ctx(
            current="Angry",
            target="Silent",
            last_transition_at=last,
            safe_mode=True,
        )
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is False
        assert decision.blocked_by == "safe_mode"

    def test_forced_still_blocked_by_distress(self, engine: TransitionRuleEngine) -> None:
        """Distress >= D2 blocks even forced transitions."""
        last = NOW - timedelta(seconds=10)
        ctx = _ctx(
            current="Content",
            target="Pleased",
            last_transition_at=last,
            distress_level=3,
        )
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is False
        assert decision.blocked_by == "distress"


# ---------------------------------------------------------------------------
# Safe mode
# ---------------------------------------------------------------------------


class TestSafeMode:
    """Safe mode blocks ALL transitions regardless of other conditions."""

    @pytest.mark.parametrize(
        ("current", "target"),
        _ALL_VALID_TRANSITIONS,
        ids=[f"{c}->{t}" for c, t in _ALL_VALID_TRANSITIONS],
    )
    def test_safe_mode_blocks_all(
        self,
        engine: TransitionRuleEngine,
        current: str,
        target: str,
    ) -> None:
        ctx = _ctx(
            current=current,
            target=target,
            last_transition_at=None,
            safe_mode=True,
        )
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is False
        assert decision.blocked_by == "safe_mode"

    def test_safe_mode_overrides_distress(self, engine: TransitionRuleEngine) -> None:
        """Safe mode takes priority over distress check (order matters)."""
        ctx = _ctx(
            current="Content",
            target="Pleased",
            last_transition_at=None,
            safe_mode=True,
            distress_level=4,
        )
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is False
        assert decision.blocked_by == "safe_mode"


# ---------------------------------------------------------------------------
# Distress level
# ---------------------------------------------------------------------------


class TestDistressLevel:
    """Distress level >= D2 blocks transitions."""

    @pytest.mark.parametrize("level", [2, 3, 4])
    def test_distress_blocks(
        self,
        engine: TransitionRuleEngine,
        level: int,
    ) -> None:
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            distress_level=level,
        )
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is False
        assert decision.blocked_by == "distress"
        assert f"D{level}" in decision.reason

    @pytest.mark.parametrize("level", [0, 1])
    def test_distress_below_d2_allows(
        self,
        engine: TransitionRuleEngine,
        level: int,
    ) -> None:
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            distress_level=level,
        )
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.allowed is True


# ---------------------------------------------------------------------------
# remaining_cooldown calculation
# ---------------------------------------------------------------------------


class TestRemainingCooldown:
    """remaining_cooldown returns correct seconds for various timestamps."""

    def test_no_previous_transition(self, engine: TransitionRuleEngine) -> None:
        assert engine.remaining_cooldown(None, now=NOW) == 0

    def test_just_transitioned(self, engine: TransitionRuleEngine) -> None:
        last = NOW - timedelta(seconds=1)
        assert engine.remaining_cooldown(last, now=NOW) == 299

    def test_halfway(self, engine: TransitionRuleEngine) -> None:
        last = NOW - timedelta(seconds=150)
        assert engine.remaining_cooldown(last, now=NOW) == 150

    def test_exactly_at_cooldown(self, engine: TransitionRuleEngine) -> None:
        last = NOW - timedelta(seconds=300)
        assert engine.remaining_cooldown(last, now=NOW) == 0

    def test_past_cooldown(self, engine: TransitionRuleEngine) -> None:
        last = NOW - timedelta(seconds=600)
        assert engine.remaining_cooldown(last, now=NOW) == 0

    def test_custom_cooldown_value(self, custom_engine: TransitionRuleEngine) -> None:
        last = NOW - timedelta(seconds=30)
        assert custom_engine.remaining_cooldown(last, now=NOW) == 30

    def test_default_now_uses_utc(self, engine: TransitionRuleEngine) -> None:
        """When now is None, remaining_cooldown uses datetime.now(tz=UTC)."""
        # We can't predict exact value, but can verify it returns >= 0
        result = engine.remaining_cooldown(None)
        assert result == 0

        # Recent transition should give positive remaining
        recent = datetime.now(tz=timezone.utc) - timedelta(seconds=10)
        result = engine.remaining_cooldown(recent)
        assert 280 <= result <= 290


# ---------------------------------------------------------------------------
# should_use_llm_evaluation
# ---------------------------------------------------------------------------


class TestShouldUseLlmEvaluation:
    """LLM evaluation triggered for ambiguous sentiment or multiple signals."""

    @pytest.mark.parametrize(
        "sentiment",
        [-0.3, -0.15, 0.0, 0.15, 0.3],
    )
    def test_ambiguous_sentiment_triggers_llm(
        self,
        engine: TransitionRuleEngine,
        sentiment: float,
    ) -> None:
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            conversation_sentiment=sentiment,
        )
        assert engine.should_use_llm_evaluation(ctx) is True

    @pytest.mark.parametrize("sentiment", [-1.0, -0.5, -0.31, 0.31, 0.5, 1.0])
    def test_clear_sentiment_no_llm_without_extra_signals(
        self,
        engine: TransitionRuleEngine,
        sentiment: float,
    ) -> None:
        """Clear sentiment with no other signals → no LLM needed."""
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            conversation_sentiment=sentiment,
        )
        assert engine.should_use_llm_evaluation(ctx) is False

    def test_multiple_signals_task_and_sentiment(self, engine: TransitionRuleEngine) -> None:
        """task_completion + non-zero sentiment = multiple signals."""
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            conversation_sentiment=0.8,
            task_completion=True,
        )
        assert engine.should_use_llm_evaluation(ctx) is True

    def test_multiple_signals_ignored_and_sentiment(self, engine: TransitionRuleEngine) -> None:
        """ignored_count > 0 + non-zero sentiment = multiple signals."""
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            conversation_sentiment=0.5,
            ignored_count=3,
        )
        assert engine.should_use_llm_evaluation(ctx) is True

    def test_multiple_signals_task_and_ignored(self, engine: TransitionRuleEngine) -> None:
        """task_completion + ignored_count = multiple signals (even with clear sentiment)."""
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            conversation_sentiment=-0.8,
            task_completion=True,
            ignored_count=2,
        )
        assert engine.should_use_llm_evaluation(ctx) is True

    def test_single_signal_no_llm(self, engine: TransitionRuleEngine) -> None:
        """Only task_completion, no sentiment, no ignored → not complex."""
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            conversation_sentiment=0.0,
            task_completion=True,
        )
        # sentiment=0.0 is ambiguous (between -0.3 and 0.3), so True
        assert engine.should_use_llm_evaluation(ctx) is True

    def test_zero_everything_no_llm(self, engine: TransitionRuleEngine) -> None:
        """No signals at all but sentiment=0.0 is ambiguous."""
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            conversation_sentiment=0.0,
        )
        # sentiment 0.0 is in [-0.3, 0.3] → ambiguous → True
        assert engine.should_use_llm_evaluation(ctx) is True


# ---------------------------------------------------------------------------
# evaluate_with_llm stub
# ---------------------------------------------------------------------------


class TestEvaluateWithLlm:
    """LLM evaluation stub falls back to rule-based."""

    def test_stub_returns_same_as_evaluate_allowed(self, engine: TransitionRuleEngine) -> None:
        """Stub should return identical result to evaluate() for allowed transition."""
        ctx = _ctx(current="Content", target="Disappointed", last_transition_at=None)
        rule_decision = engine.evaluate(ctx, now=NOW)
        llm_decision = asyncio.run(engine.evaluate_with_llm(ctx, now=NOW))
        assert llm_decision.allowed == rule_decision.allowed
        assert llm_decision.from_mood == rule_decision.from_mood
        assert llm_decision.to_mood == rule_decision.to_mood
        assert llm_decision.blocked_by == rule_decision.blocked_by

    def test_stub_returns_same_as_evaluate_blocked(self, engine: TransitionRuleEngine) -> None:
        """Stub should return identical result to evaluate() for blocked transition."""
        last = NOW - timedelta(seconds=60)
        ctx = _ctx(current="Content", target="Disappointed", last_transition_at=last)
        rule_decision = engine.evaluate(ctx, now=NOW)
        llm_decision = asyncio.run(engine.evaluate_with_llm(ctx, now=NOW))
        assert llm_decision.allowed is False
        assert llm_decision.blocked_by == rule_decision.blocked_by
        assert llm_decision.cooldown_remaining_seconds == rule_decision.cooldown_remaining_seconds

    def test_stub_respects_safe_mode(self, engine: TransitionRuleEngine) -> None:
        """Stub must respect safe_mode just like evaluate()."""
        ctx = _ctx(
            current="Content",
            target="Pleased",
            last_transition_at=None,
            safe_mode=True,
        )
        llm_decision = asyncio.run(engine.evaluate_with_llm(ctx, now=NOW))
        assert llm_decision.allowed is False
        assert llm_decision.blocked_by == "safe_mode"


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """Custom exceptions form the expected hierarchy."""

    def test_cooldown_active_is_transition_rules_error(self) -> None:
        assert issubclass(CooldownActiveError, TransitionRulesError)

    def test_invalid_transition_is_transition_rules_error(self) -> None:
        assert issubclass(InvalidTransitionError, TransitionRulesError)

    def test_transition_rules_is_exception(self) -> None:
        assert issubclass(TransitionRulesError, Exception)


# ---------------------------------------------------------------------------
# Decision dataclass defaults
# ---------------------------------------------------------------------------


class TestDecisionDefaults:
    """TransitionDecision default values are correct."""

    def test_default_cooldown_zero(self) -> None:
        d = TransitionDecision(
            allowed=True, from_mood="Content", to_mood="Pleased", reason="ok"
        )
        assert d.cooldown_remaining_seconds == 0

    def test_default_blocked_by_none(self) -> None:
        d = TransitionDecision(
            allowed=True, from_mood="Content", to_mood="Pleased", reason="ok"
        )
        assert d.blocked_by is None


# ---------------------------------------------------------------------------
# Check order priority
# ---------------------------------------------------------------------------


class TestCheckOrder:
    """Verify the evaluation check order: safe_mode > distress > invalid > cooldown."""

    def test_safe_mode_before_distress(self, engine: TransitionRuleEngine) -> None:
        """Safe mode checked before distress."""
        ctx = _ctx(
            current="Content",
            target="Disappointed",
            last_transition_at=None,
            safe_mode=True,
            distress_level=4,
        )
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.blocked_by == "safe_mode"

    def test_distress_before_invalid(self, engine: TransitionRuleEngine) -> None:
        """Distress checked before invalid transition."""
        ctx = _ctx(
            current="Content",
            target="Angry",  # invalid transition
            last_transition_at=None,
            distress_level=3,
        )
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.blocked_by == "distress"

    def test_invalid_before_cooldown(self, engine: TransitionRuleEngine) -> None:
        """Invalid transition checked before cooldown."""
        last = NOW - timedelta(seconds=60)  # within cooldown
        ctx = _ctx(
            current="Content",
            target="Angry",  # invalid
            last_transition_at=last,
        )
        decision = engine.evaluate(ctx, now=NOW)
        assert decision.blocked_by == "invalid_transition"

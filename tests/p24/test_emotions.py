"""W7 Tests — Emotion System (M4).

Tests:
  - 16 moods present (enum count)
  - classifier maps sample messages
  - affect vector updates (EWMA)
  - format_for_system_prompt returns non-empty string
  - on_turn hooks fire
  - wire() attaches state to agent

D3: MockEmotionClassifier only — NO real LLM calls.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest


# ── fixtures ────────────────────────────────────────────────


@pytest.fixture
def classifier() -> Any:
    from guinevere.emotions.classifier import MockEmotionClassifier

    return MockEmotionClassifier()


@pytest.fixture
def engine(classifier: Any) -> Any:
    from guinevere.emotions.engine import EmotionEngine

    return EmotionEngine(classifier=classifier)


@pytest.fixture
def state() -> Any:
    from guinevere.emotions.fsm import EmotionState

    return EmotionState()


# ── tests ───────────────────────────────────────────────────


class TestMoodStateEnum:
    """MoodState enum must have exactly 16 members."""

    def test_exactly_16_moods(self) -> None:
        from guinevere.emotions.fsm import MoodState

        assert len(list(MoodState)) == 16

    def test_all_16_names_present(self) -> None:
        from guinevere.emotions.fsm import MoodState

        expected = {
            "HAPPY", "ANGRY", "SAD", "JEALOUS", "POSSESSIVE",
            "NURTURING", "FEAR", "DISGUST", "SURPRISE", "ANTICIPATION",
            "TRUST", "BOREDOM", "CURIOSITY", "PRIDE", "DESIRE", "AROUSAL",
        }
        actual = {m.name for m in MoodState}
        assert actual == expected

    def test_enum_values_are_strings(self) -> None:
        from guinevere.emotions.fsm import MoodState

        for mood in MoodState:
            assert isinstance(mood.value, str)
            assert mood.value == mood.name

    def test_import_from_package(self) -> None:
        from guinevere.emotions import MoodState, EmotionEngine, EmotionState

        assert MoodState is not None
        assert EmotionEngine is not None
        assert EmotionState is not None


class TestTransitionGraph:
    """Transition rules must be deterministic and bidirectional-safe."""

    def test_every_mood_has_transitions(self) -> None:
        from guinevere.emotions.fsm import MoodState, TRANSITIONS

        for mood in MoodState:
            assert mood in TRANSITIONS, f"{mood.name} missing from TRANSITIONS"
            assert len(TRANSITIONS[mood]) >= 2, f"{mood.name} has <2 transitions"

    def test_valid_transition_succeeds(self) -> None:
        from guinevere.emotions.fsm import MoodState, transition

        # HAPPY -> NURTURING is allowed.
        result = transition(MoodState.HAPPY, MoodState.NURTURING)
        assert result == MoodState.NURTURING

    def test_invalid_transition_returns_original(self) -> None:
        from guinevere.emotions.fsm import MoodState, transition

        # HAPPY -> BOREDOM is NOT in the graph.
        result = transition(MoodState.HAPPY, MoodState.BOREDOM)
        assert result == MoodState.HAPPY

    def test_force_mood_bypasses_graph(self) -> None:
        from guinevere.emotions.fsm import EmotionState, MoodState

        state = EmotionState(current_mood=MoodState.HAPPY)
        state.force_mood(MoodState.BOREDOM)
        assert state.current_mood == MoodState.BOREDOM

    def test_set_mood_records_history(self) -> None:
        from guinevere.emotions.fsm import EmotionState, MoodState

        state = EmotionState(current_mood=MoodState.HAPPY)
        state.set_mood(MoodState.NURTURING, intensity=0.8)
        assert state.current_mood == MoodState.NURTURING
        assert len(state.transition_history) == 1
        assert state.transition_history[0][0] == MoodState.HAPPY
        assert state.transition_history[0][1] == MoodState.NURTURING

    def test_set_mood_rejected_stays(self) -> None:
        from guinevere.emotions.fsm import EmotionState, MoodState

        state = EmotionState(current_mood=MoodState.HAPPY)
        state.set_mood(MoodState.BOREDOM)  # invalid transition
        assert state.current_mood == MoodState.HAPPY
        assert len(state.transition_history) == 0


class TestAffectVector:
    """8-dim affect vector with EWMA updates."""

    def test_affect_has_8_dimensions(self) -> None:
        from guinevere.emotions.fsm import EmotionState, AFFECT_DIMENSIONS

        state = EmotionState()
        assert len(state.affect) == 8
        for dim in AFFECT_DIMENSIONS:
            assert dim in state.affect

    def test_ewma_update_moves_toward_target(self) -> None:
        from guinevere.emotions.fsm import EmotionState

        state = EmotionState()
        # All start at 0.5.
        assert state.affect["curiosity"] == 0.5

        state.ewma_update({"curiosity": 1.0}, lam=0.3)
        # Expected: 0.3 * 1.0 + 0.7 * 0.5 = 0.65
        assert abs(state.affect["curiosity"] - 0.65) < 0.01

    def test_ewma_update_ignores_unknown_dimensions(self) -> None:
        from guinevere.emotions.fsm import EmotionState

        state = EmotionState()
        original = dict(state.affect)
        state.ewma_update({"nonexistent": 1.0}, lam=0.3)
        assert state.affect == original

    def test_ewma_converges_after_many_updates(self) -> None:
        from guinevere.emotions.fsm import EmotionState

        state = EmotionState()
        for _ in range(50):
            state.ewma_update({"curiosity": 1.0}, lam=0.3)
        # Should be very close to 1.0 after 50 iterations.
        assert state.affect["curiosity"] > 0.95


class TestClassifier:
    """MockEmotionClassifier keyword mapping."""

    def test_happy_keywords(self, classifier: Any) -> None:
        from guinevere.emotions.fsm import MoodState

        result = classifier.classify("I am so happy today!", {})
        assert result == MoodState.HAPPY

    def test_angry_keywords(self, classifier: Any) -> None:
        from guinevere.emotions.fsm import MoodState

        result = classifier.classify("That makes me furious!", {})
        assert result == MoodState.ANGRY

    def test_sad_keywords(self, classifier: Any) -> None:
        from guinevere.emotions.fsm import MoodState

        result = classifier.classify("I feel so lonely and sad.", {})
        assert result == MoodState.SAD

    def test_curious_keywords(self, classifier: Any) -> None:
        from guinevere.emotions.fsm import MoodState

        result = classifier.classify("I wonder how does that work?", {})
        assert result == MoodState.CURIOSITY

    def test_fallback_to_current_mood(self, classifier: Any) -> None:
        from guinevere.emotions.fsm import MoodState

        result = classifier.classify("Hello.", {"current_mood": MoodState.TRUST})
        assert result == MoodState.TRUST

    def test_no_forbidden_patterns(self) -> None:
        """Classifier must not reference any real LLM client."""
        import inspect
        from guinevere.emotions.classifier import MockEmotionClassifier

        source = inspect.getsource(MockEmotionClassifier)
        assert "openai" not in source.lower()
        assert "anthropic" not in source.lower()
        assert "httpx" not in source.lower()


class TestEmotionEngine:
    """EmotionEngine per-turn processing and formatting."""

    def test_on_turn_start_updates_mood(self, engine: Any) -> None:
        from guinevere.emotions.fsm import MoodState

        mood = engine.on_turn_start("I am so happy!")
        assert mood == MoodState.HAPPY
        assert engine.state.current_mood == MoodState.HAPPY

    def test_on_turn_start_increments_count(self, engine: Any) -> None:
        assert engine.turn_count == 0
        engine.on_turn_start("Hello.")
        assert engine.turn_count == 1
        engine.on_turn_start("Hello again.")
        assert engine.turn_count == 2

    def test_on_turn_end_does_not_crash(self, engine: Any) -> None:
        engine.on_turn_start("test")
        engine.on_turn_end()  # Should not raise.

    def test_affect_updates_on_turn(self, engine: Any) -> None:
        from guinevere.emotions.fsm import MoodState

        # Start at defaults (0.5).
        assert engine.state.affect["warmth"] == 0.5

        engine.on_turn_start("I love you so much!")
        assert engine.state.current_mood == MoodState.HAPPY
        # HAPPY signature: warmth=0.8. EWMA: 0.3*0.8 + 0.7*0.5 = 0.59
        assert engine.state.affect["warmth"] > 0.5

    def test_format_for_system_prompt_non_empty(self, engine: Any) -> None:
        result = engine.format_for_system_prompt()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_for_system_prompt_contains_mood(self, engine: Any) -> None:
        engine.on_turn_start("I am curious about everything!")
        result = engine.format_for_system_prompt()
        assert "CURIOSITY" in result or "HAPPY" in result  # depends on keyword order
        assert "[MOOD STATE]" in result
        assert "intensity" in result

    def test_format_contains_affect_top3(self, engine: Any) -> None:
        result = engine.format_for_system_prompt()
        assert "Affect top-3" in result

    def test_format_contains_transition_history(self, engine: Any) -> None:
        result = engine.format_for_system_prompt()
        assert "Transition history" in result

    def test_multi_turn_mood_chain(self, engine: Any) -> None:
        """A sequence of messages produces a valid mood chain."""
        from guinevere.emotions.fsm import MoodState

        engine.on_turn_start("I am so happy!")
        assert engine.state.current_mood == MoodState.HAPPY

        # HAPPY -> NURTURING is allowed.
        engine.on_turn_start("Let me care for you.")
        # "care" maps to NURTURING, and HAPPY -> NURTURING is valid.
        assert engine.state.current_mood == MoodState.NURTURING

        assert len(engine.state.transition_history) >= 1


class TestWire:
    """wire() attaches engine to agent."""

    def test_wire_attaches_engine(self) -> None:
        from guinevere.emotions.engine import EmotionEngine, wire

        class FakeAgent:
            pass

        agent = FakeAgent()
        engine = wire(agent)
        assert isinstance(engine, EmotionEngine)
        assert agent._emotion_engine is engine
        assert agent._emotion_state is engine.state

    def test_wire_with_custom_classifier(self) -> None:
        from guinevere.emotions.classifier import MockEmotionClassifier
        from guinevere.emotions.engine import wire

        class FakeAgent:
            pass

        agent = FakeAgent()
        custom = MockEmotionClassifier()
        engine = wire(agent, classifier=custom)
        assert engine._classifier is custom

"""
P4-001: Mood FSM Engine Deterministic Unit Tests

Tests the foundational mood state machine — enum values, transition map,
can_transition logic, evaluate_mood heuristics, and edge cases.
100% deterministic, zero network calls.
"""
from __future__ import annotations

import pytest

from src.persona.mood_engine import (
    Mood,
    MoodEngineError,
    MoodEvaluationError,
    MoodTransition,
    TRANSITIONS,
    InvalidMoodTransitionError,
    can_transition,
    evaluate_mood,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def all_moods() -> list[Mood]:
    """Return all five Mood enum members."""
    return [Mood.CONTENT, Mood.PLEASED, Mood.DISAPPOINTED, Mood.ANGRY, Mood.SILENT]


# ============================================================
# Mood Enum
# ============================================================


class TestMoodEnum:
    """Verify all 5 mood states exist with correct string values."""

    def test_content_value(self) -> None:
        assert Mood.CONTENT == "Content"
        assert Mood.CONTENT.value == "Content"

    def test_pleased_value(self) -> None:
        assert Mood.PLEASED == "Pleased"
        assert Mood.PLEASED.value == "Pleased"

    def test_disappointed_value(self) -> None:
        assert Mood.DISAPPOINTED == "Disappointed"
        assert Mood.DISAPPOINTED.value == "Disappointed"

    def test_angry_value(self) -> None:
        assert Mood.ANGRY == "Angry"
        assert Mood.ANGRY.value == "Angry"

    def test_silent_value(self) -> None:
        assert Mood.SILENT == "Silent"
        assert Mood.SILENT.value == "Silent"

    def test_all_five_moods_exist(self, all_moods: list[Mood]) -> None:
        assert len(all_moods) == 5
        assert len(Mood) == 5

    def test_mood_is_str_enum(self) -> None:
        """Mood inherits from str — allows direct string comparison."""
        assert isinstance(Mood.CONTENT, str)
        assert Mood.CONTENT == "Content"

    def test_mood_string_interop(self) -> None:
        """Mood values work anywhere a string is expected."""
        assert f"{Mood.ANGRY}" == "Mood.ANGRY"
        assert Mood.CONTENT.value.upper() == "CONTENT"


# ============================================================
# Transition Map
# ============================================================


class TestTransitions:
    """Verify the TRANSITIONS dict covers all moods and valid edges."""

    def test_all_moods_have_entries(self, all_moods: list[Mood]) -> None:
        """Every mood must appear as a key in TRANSITIONS."""
        for mood in all_moods:
            assert mood in TRANSITIONS, f"Missing TRANSITIONS entry for {mood}"

    def test_content_transitions(self) -> None:
        assert TRANSITIONS[Mood.CONTENT] == [Mood.PLEASED, Mood.DISAPPOINTED]

    def test_pleased_transitions(self) -> None:
        assert TRANSITIONS[Mood.PLEASED] == [Mood.CONTENT, Mood.DISAPPOINTED]

    def test_disappointed_transitions(self) -> None:
        assert TRANSITIONS[Mood.DISAPPOINTED] == [Mood.CONTENT, Mood.ANGRY]

    def test_angry_transitions(self) -> None:
        assert TRANSITIONS[Mood.ANGRY] == [Mood.DISAPPOINTED, Mood.SILENT]

    def test_silent_transitions(self) -> None:
        assert TRANSITIONS[Mood.SILENT] == [Mood.CONTENT]

    def test_total_valid_edges(self) -> None:
        """Count total valid transitions across all moods.

        CONTENT→2 + PLEASED→2 + DISAPPOINTED→2 + ANGRY→2 + SILENT→1 = 9.
        """
        total = sum(len(targets) for targets in TRANSITIONS.values())
        assert total == 9

    def test_transitions_is_final(self) -> None:
        """TRANSITIONS is typed as Final — verify it's a dict (runtime check)."""
        assert isinstance(TRANSITIONS, dict)


# ============================================================
# can_transition()
# ============================================================


class TestCanTransition:
    """Boolean transition checker against the TRANSITIONS map."""

    # ---- Valid transitions (should return True) ----

    @pytest.mark.parametrize(
        "current,target",
        [
            (Mood.CONTENT, Mood.PLEASED),
            (Mood.CONTENT, Mood.DISAPPOINTED),
            (Mood.PLEASED, Mood.CONTENT),
            (Mood.PLEASED, Mood.DISAPPOINTED),
            (Mood.DISAPPOINTED, Mood.CONTENT),
            (Mood.DISAPPOINTED, Mood.ANGRY),
            (Mood.ANGRY, Mood.DISAPPOINTED),
            (Mood.ANGRY, Mood.SILENT),
            (Mood.SILENT, Mood.CONTENT),
        ],
    )
    def test_valid_transitions(self, current: Mood, target: Mood) -> None:
        assert can_transition(current, target) is True

    # ---- Invalid transitions (should return False) ----

    @pytest.mark.parametrize(
        "current,target",
        [
            # Self-transitions are invalid
            (Mood.CONTENT, Mood.CONTENT),
            (Mood.PLEASED, Mood.PLEASED),
            (Mood.DISAPPOINTED, Mood.DISAPPOINTED),
            (Mood.ANGRY, Mood.ANGRY),
            (Mood.SILENT, Mood.SILENT),
            # Cross-level jumps
            (Mood.CONTENT, Mood.ANGRY),
            (Mood.CONTENT, Mood.SILENT),
            (Mood.PLEASED, Mood.ANGRY),
            (Mood.PLEASED, Mood.SILENT),
            (Mood.DISAPPOINTED, Mood.PLEASED),
            (Mood.DISAPPOINTED, Mood.SILENT),
            (Mood.ANGRY, Mood.CONTENT),
            (Mood.ANGRY, Mood.PLEASED),
            (Mood.SILENT, Mood.PLEASED),
            (Mood.SILENT, Mood.DISAPPOINTED),
            (Mood.SILENT, Mood.ANGRY),
        ],
    )
    def test_invalid_transitions(self, current: Mood, target: Mood) -> None:
        assert can_transition(current, target) is False


# ============================================================
# evaluate_mood()
# ============================================================


class TestEvaluateMood:
    """Heuristic mood evaluator — signal-based transition proposals."""

    # ---- Positive sentiment + task completion → PLEASED ----

    def test_positive_sentiment_with_task_completion(self) -> None:
        result = evaluate_mood(
            conversation_sentiment=0.9,
            task_completion=True,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert result is not None
        assert result.from_mood == Mood.CONTENT
        assert result.to_mood == Mood.PLEASED
        assert "task completion" in result.reason.lower() or "positive" in result.reason.lower()

    def test_positive_sentiment_without_task_completion(self) -> None:
        """High sentiment alone should NOT trigger transition."""
        result = evaluate_mood(
            conversation_sentiment=0.9,
            task_completion=False,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert result is None

    def test_task_completion_without_positive_sentiment(self) -> None:
        """Task completion alone with low sentiment should NOT trigger."""
        result = evaluate_mood(
            conversation_sentiment=0.3,
            task_completion=True,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert result is None

    # ---- ignored_count ≥ 2 → DISAPPOINTED ----

    def test_ignored_count_2_disappointed(self) -> None:
        result = evaluate_mood(
            conversation_sentiment=0.5,
            task_completion=False,
            ignored_count=2,
            current_mood=Mood.CONTENT,
        )
        assert result is not None
        assert result.to_mood == Mood.DISAPPOINTED

    def test_ignored_count_3_disappointed(self) -> None:
        """ignored_count=3 is ≥ 2 but < 4, so DISAPPOINTED."""
        result = evaluate_mood(
            conversation_sentiment=0.5,
            task_completion=False,
            ignored_count=3,
            current_mood=Mood.CONTENT,
        )
        assert result is not None
        assert result.to_mood == Mood.DISAPPOINTED

    # ---- ignored_count ≥ 4 → ANGRY ----

    def test_ignored_count_4_angry(self) -> None:
        result = evaluate_mood(
            conversation_sentiment=0.5,
            task_completion=False,
            ignored_count=4,
            current_mood=Mood.DISAPPOINTED,
        )
        assert result is not None
        assert result.from_mood == Mood.DISAPPOINTED
        assert result.to_mood == Mood.ANGRY

    def test_ignored_count_10_angry(self) -> None:
        """Very high ignored count should still produce ANGRY."""
        result = evaluate_mood(
            conversation_sentiment=0.0,
            task_completion=False,
            ignored_count=10,
            current_mood=Mood.DISAPPOINTED,
        )
        assert result is not None
        assert result.to_mood == Mood.ANGRY

    # ---- Neutral inputs → None ----

    def test_neutral_inputs_no_transition(self) -> None:
        result = evaluate_mood(
            conversation_sentiment=0.5,
            task_completion=False,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert result is None

    def test_boundary_sentiment_no_transition(self) -> None:
        """Sentiment exactly 0.7 is NOT > 0.7, so no transition."""
        result = evaluate_mood(
            conversation_sentiment=0.7,
            task_completion=True,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert result is None

    def test_zero_sentiment_no_transition(self) -> None:
        result = evaluate_mood(
            conversation_sentiment=0.0,
            task_completion=True,
            ignored_count=0,
            current_mood=Mood.PLEASED,
        )
        assert result is None

    # ---- Invalid transitions from current mood → skip ----

    def test_ignored_from_pleased_skips_to_none(self) -> None:
        """PLEASED cannot go to ANGRY directly. ignored_count=4 but no valid path."""
        # PLEASED → ANGRY is invalid, but PLEASED → DISAPPOINTED is valid
        # ignored_count >= 4 checks ANGRY first (invalid from PLEASED),
        # then falls through to >= 2 check for DISAPPOINTED (valid from PLEASED)
        result = evaluate_mood(
            conversation_sentiment=0.5,
            task_completion=False,
            ignored_count=4,
            current_mood=Mood.PLEASED,
        )
        # PLEASED can go to DISAPPOINTED (ignored >= 2 check catches it)
        assert result is not None
        assert result.to_mood == Mood.DISAPPOINTED

    def test_positive_from_silent_no_transition(self) -> None:
        """SILENT can only go to CONTENT, not PLEASED. Positive signal → None."""
        result = evaluate_mood(
            conversation_sentiment=0.9,
            task_completion=True,
            ignored_count=0,
            current_mood=Mood.SILENT,
        )
        assert result is None


# ============================================================
# MoodTransition Dataclass
# ============================================================


class TestMoodTransition:
    """MoodTransition dataclass — default values and mutability."""

    def test_default_cooldown(self) -> None:
        transition = MoodTransition(
            from_mood=Mood.CONTENT,
            to_mood=Mood.PLEASED,
            reason="test",
        )
        assert transition.cooldown_seconds == 300

    def test_custom_cooldown(self) -> None:
        transition = MoodTransition(
            from_mood=Mood.CONTENT,
            to_mood=Mood.PLEASED,
            reason="test",
            cooldown_seconds=600,
        )
        assert transition.cooldown_seconds == 600

    def test_mutable_state(self) -> None:
        """MoodTransition is NOT frozen — fields can be modified."""
        transition = MoodTransition(
            from_mood=Mood.CONTENT,
            to_mood=Mood.PLEASED,
            reason="initial",
        )
        transition.reason = "updated"
        transition.cooldown_seconds = 120
        assert transition.reason == "updated"
        assert transition.cooldown_seconds == 120

    def test_from_mood_and_to_mood_preserved(self) -> None:
        transition = MoodTransition(
            from_mood=Mood.DISAPPOINTED,
            to_mood=Mood.ANGRY,
            reason="ignored 5 times",
        )
        assert transition.from_mood == Mood.DISAPPOINTED
        assert transition.to_mood == Mood.ANGRY
        assert transition.reason == "ignored 5 times"


# ============================================================
# Error Hierarchy
# ============================================================


class TestErrorHierarchy:
    """Custom exception classes follow proper inheritance."""

    def test_mood_engine_error_is_exception(self) -> None:
        assert issubclass(MoodEngineError, Exception)

    def test_invalid_transition_is_mood_engine_error(self) -> None:
        assert issubclass(InvalidMoodTransitionError, MoodEngineError)

    def test_evaluation_error_is_mood_engine_error(self) -> None:
        assert issubclass(MoodEvaluationError, MoodEngineError)

    def test_raise_invalid_transition(self) -> None:
        with pytest.raises(InvalidMoodTransitionError):
            raise InvalidMoodTransitionError("SILENT → ANGRY is invalid")

    def test_raise_evaluation_error(self) -> None:
        with pytest.raises(MoodEvaluationError):
            raise MoodEvaluationError("unexpected evaluation state")

    def test_catch_as_base_error(self) -> None:
        """Both subclasses should be catchable as MoodEngineError."""
        with pytest.raises(MoodEngineError):
            raise InvalidMoodTransitionError("test")
        with pytest.raises(MoodEngineError):
            raise MoodEvaluationError("test")


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    """Boundary conditions and FSM invariants."""

    def test_silent_can_only_go_to_content(self) -> None:
        """SILENT has exactly one outgoing transition: CONTENT."""
        valid_targets = TRANSITIONS[Mood.SILENT]
        assert valid_targets == [Mood.CONTENT]
        assert len(valid_targets) == 1

    def test_angry_can_only_go_to_disappointed_or_silent(self) -> None:
        """ANGRY has exactly two outgoing transitions."""
        valid_targets = TRANSITIONS[Mood.ANGRY]
        assert set(valid_targets) == {Mood.DISAPPOINTED, Mood.SILENT}
        assert len(valid_targets) == 2

    def test_no_self_transitions(self, all_moods: list[Mood]) -> None:
        """No mood can transition to itself."""
        for mood in all_moods:
            assert mood not in TRANSITIONS[mood], f"{mood} has self-transition"

    def test_fsm_is_connected(self, all_moods: list[Mood]) -> None:
        """Every mood is reachable from every other mood (possibly via intermediaries)."""
        # BFS from each mood — all others must be reachable
        for start in all_moods:
            visited: set[Mood] = {start}
            queue: list[Mood] = [start]
            while queue:
                current = queue.pop(0)
                for target in TRANSITIONS[current]:
                    if target not in visited:
                        visited.add(target)
                        queue.append(target)
            assert visited == set(all_moods), (
                f"From {start}, cannot reach: {set(all_moods) - visited}"
            )

    def test_evaluate_ignored_priority_over_sentiment(self) -> None:
        """ignored_count >= 2 takes priority over positive sentiment."""
        result = evaluate_mood(
            conversation_sentiment=0.9,
            task_completion=True,
            ignored_count=2,
            current_mood=Mood.CONTENT,
        )
        assert result is not None
        assert result.to_mood == Mood.DISAPPOINTED

    def test_evaluate_ignored_4_priority_over_sentiment(self) -> None:
        """ignored_count >= 4 takes priority over positive sentiment."""
        result = evaluate_mood(
            conversation_sentiment=0.9,
            task_completion=True,
            ignored_count=4,
            current_mood=Mood.DISAPPOINTED,
        )
        assert result is not None
        assert result.to_mood == Mood.ANGRY

    def test_ignored_1_no_transition(self) -> None:
        """ignored_count=1 is below threshold — no transition."""
        result = evaluate_mood(
            conversation_sentiment=0.5,
            task_completion=False,
            ignored_count=1,
            current_mood=Mood.CONTENT,
        )
        assert result is None

    def test_negative_sentiment_no_transition(self) -> None:
        """Negative sentiment with no ignored count → no transition."""
        result = evaluate_mood(
            conversation_sentiment=-0.5,
            task_completion=False,
            ignored_count=0,
            current_mood=Mood.CONTENT,
        )
        assert result is None

    def test_evaluate_from_all_moods_neutral(self, all_moods: list[Mood]) -> None:
        """Neutral inputs from any mood should return None."""
        for mood in all_moods:
            result = evaluate_mood(
                conversation_sentiment=0.5,
                task_completion=False,
                ignored_count=0,
                current_mood=mood,
            )
            assert result is None, f"Unexpected transition from {mood}"

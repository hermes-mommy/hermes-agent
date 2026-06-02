"""
Mood FSM Engine — Foundational Mood State Machine for Guinevere Persona (P4-001)

Implements a deterministic finite state machine for mood transitions.
All persona modules depend on this engine for mood state management.

Architecture: Mood enum → TRANSITIONS map → evaluate_mood() → MoodTransition
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

import structlog

logger = structlog.get_logger()


# ============================================================
# Mood Enum
# ============================================================


class Mood(str, Enum):
    """Five discrete mood states for the Guinevere persona FSM."""

    CONTENT = "Content"
    PLEASED = "Pleased"
    DISAPPOINTED = "Disappointed"
    ANGRY = "Angry"
    SILENT = "Silent"


# ============================================================
# Transition Map
# ============================================================

TRANSITIONS: Final[dict[Mood, list[Mood]]] = {
    Mood.CONTENT: [Mood.PLEASED, Mood.DISAPPOINTED],
    Mood.PLEASED: [Mood.CONTENT, Mood.DISAPPOINTED],
    Mood.DISAPPOINTED: [Mood.CONTENT, Mood.ANGRY],
    Mood.ANGRY: [Mood.DISAPPOINTED, Mood.SILENT],
    Mood.SILENT: [Mood.CONTENT],
}


# ============================================================
# Data Classes
# ============================================================


@dataclass
class MoodTransition:
    """Represents a single mood transition event with metadata.

    Not frozen — mutable state allows callers to update cooldown
    or reason after initial creation.
    """

    from_mood: Mood
    to_mood: Mood
    reason: str
    cooldown_seconds: int = 300  # 5 min minimum between transitions


# ============================================================
# Error Hierarchy
# ============================================================


class MoodEngineError(Exception):
    """Base exception for all mood engine errors."""


class InvalidMoodTransitionError(MoodEngineError):
    """Raised when a transition violates the FSM transition map."""


class MoodEvaluationError(MoodEngineError):
    """Raised when mood evaluation encounters an unexpected condition."""


# ============================================================
# Core Functions
# ============================================================


def can_transition(current: Mood, target: Mood) -> bool:
    """Check whether a transition from *current* to *target* is valid.

    Args:
        current: The current mood state.
        target: The desired target mood state.

    Returns:
        True if the transition is permitted by TRANSITIONS, False otherwise.
    """
    return target in TRANSITIONS[current]


def evaluate_mood(
    conversation_sentiment: float,
    task_completion: bool,
    ignored_count: int,
    current_mood: Mood,
) -> MoodTransition | None:
    """Evaluate conversation signals and propose a mood transition.

    Evaluation order (most severe first):
    1. ``ignored_count >= 4`` → ANGRY
    2. ``ignored_count >= 2`` → DISAPPOINTED
    3. ``sentiment > 0.7`` AND ``task_completion`` → PLEASED
    4. No transition (returns None)

    Each candidate is only returned if the transition is valid from
    *current_mood* according to the TRANSITIONS map.

    Args:
        conversation_sentiment: Sentiment score in ``[0.0, 1.0]``.
        task_completion: Whether the current task was completed successfully.
        ignored_count: Number of consecutive times Guinevere was ignored.
        current_mood: The current mood state.

    Returns:
        A MoodTransition if a valid transition is triggered, or None.
    """
    # Most severe condition first — ignored ≥ 4
    if ignored_count >= 4:
        target = Mood.ANGRY
        if can_transition(current_mood, target):
            logger.info(
                "mood_transition_proposed",
                from_mood=current_mood.value,
                to_mood=target.value,
                reason=f"ignored {ignored_count} times",
            )
            return MoodTransition(
                from_mood=current_mood,
                to_mood=target,
                reason=f"Ignored {ignored_count} consecutive times",
            )

    # Moderately negative — ignored ≥ 2
    if ignored_count >= 2:
        target = Mood.DISAPPOINTED
        if can_transition(current_mood, target):
            logger.info(
                "mood_transition_proposed",
                from_mood=current_mood.value,
                to_mood=target.value,
                reason=f"ignored {ignored_count} times",
            )
            return MoodTransition(
                from_mood=current_mood,
                to_mood=target,
                reason=f"Ignored {ignored_count} consecutive times",
            )

    # Positive reinforcement — high sentiment + task done
    if conversation_sentiment > 0.7 and task_completion:
        target = Mood.PLEASED
        if can_transition(current_mood, target):
            logger.info(
                "mood_transition_proposed",
                from_mood=current_mood.value,
                to_mood=target.value,
                reason="positive sentiment with task completion",
            )
            return MoodTransition(
                from_mood=current_mood,
                to_mood=target,
                reason="Positive sentiment with successful task completion",
            )

    return None

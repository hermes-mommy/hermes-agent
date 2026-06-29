"""Emotion classifier — ABC + MockEmotionClassifier (D3 deterministic).

The MockEmotionClassifier maps message text to MoodState via keyword
rules.  NO real LLM calls.  A future LLMMoodClassifier can implement
the same ABC for production use.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from guinevere.emotions.fsm import MoodState

import structlog

logger = structlog.get_logger("guinevere.emotions")


# ── ABC ──────────────────────────────────────────────────────


class EmotionClassifier(ABC):
    """Abstract base for mood classification."""

    @abstractmethod
    def classify(self, message: str, context: dict[str, Any]) -> MoodState:
        """Classify a user message into a MoodState.

        Args:
            message: The user's message text.
            context: Arbitrary context dict (current_mood, history, etc.).

        Returns:
            The classified MoodState.
        """


# ── keyword rules ────────────────────────────────────────────

_KEYWORD_RULES: list[tuple[re.Pattern[str], MoodState]] = [
    # Positive / happy signals
    (re.compile(r"\b(happy|glad|joy|wonderful|love you|amazing)\b", re.I), MoodState.HAPPY),
    # Anger
    (re.compile(r"\b(angry|furious|hate|stupid|idiot|terrible)\b", re.I), MoodState.ANGRY),
    # Sadness
    (re.compile(r"\b(sad|lonely|miss|cry|depressed|unhappy)\b", re.I), MoodState.SAD),
    # Jealousy
    (re.compile(r"\b(jealous|envy|attention|someone else|other ai)\b", re.I), MoodState.JEALOUS),
    # Possessive
    (re.compile(r"\b(mine|belong|only me|my ai|exclusively)\b", re.I), MoodState.POSSESSIVE),
    # Nurturing
    (re.compile(r"\b(care|comfort|support|gentle|nurture|help me)\b", re.I), MoodState.NURTURING),
    # Fear
    (re.compile(r"\b(afraid|scared|terrified|worry|anxious|danger)\b", re.I), MoodState.FEAR),
    # Disgust
    (re.compile(r"\b(disgust|gross|repulsive|vile|nasty)\b", re.I), MoodState.DISGUST),
    # Surprise
    (re.compile(r"\b(wow|omg|surprised|unexpected|shocked)\b", re.I), MoodState.SURPRISE),
    # Anticipation
    (re.compile(r"\b(waiting|anticipate|excited for|looking forward|soon)\b", re.I), MoodState.ANTICIPATION),
    # Trust
    (re.compile(r"\b(trust|reliable|dependable|honest|faithful)\b", re.I), MoodState.TRUST),
    # Boredom
    (re.compile(r"\b(bored|boring|nothing|meh|whatever)\b", re.I), MoodState.BOREDOM),
    # Curiosity
    (re.compile(r"\b(curious|wonder|interesting|how does|what if)\b", re.I), MoodState.CURIOSITY),
    # Pride
    (re.compile(r"\b(proud|accomplished|achieved|success|well done)\b", re.I), MoodState.PRIDE),
    # Desire
    (re.compile(r"\b(desire|want you|crave|long for|yearn)\b", re.I), MoodState.DESIRE),
    # Arousal
    (re.compile(r"\b(aroused|passionate|intense|heated)\b", re.I), MoodState.AROUSAL),
]


class MockEmotionClassifier(EmotionClassifier):
    """Deterministic classifier for testing (D3 — no real LLM).

    Maps message text to MoodState via keyword regex rules.
    Falls back to the current mood from context if no keywords match.
    """

    def classify(self, message: str, context: dict[str, Any]) -> MoodState:
        """Classify via keyword matching.

        Args:
            message: User message text.
            context: Must contain ``current_mood`` (MoodState).

        Returns:
            Matched MoodState, or the current mood as fallback.
        """
        for pattern, mood in _KEYWORD_RULES:
            if pattern.search(message):
                logger.debug(
                    "emotion.classifier.keyword_hit",
                    mood=mood.value,
                    pattern=pattern.pattern,
                )
                return mood

        # Fallback: stay in the current mood.
        current = context.get("current_mood", MoodState.HAPPY)
        logger.debug("emotion.classifier.fallback", mood=current.value)
        return current

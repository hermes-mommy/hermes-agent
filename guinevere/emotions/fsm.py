"""Emotion FSM — 16-mood MoodState enum, EmotionState dataclass, and
deterministic transition rules for the P24 emotion system.

ADR-063 affect vector is 8-dimensional: curiosity, concern, warmth,
vigilance, irritation, satisfaction, resignation, anticipation.

Transition graph is sparse (~3 targets per mood, ~48 edges total) to
keep the FSM testable and avoid oscillation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger("guinevere.emotions")


# ── 16-mood enum ─────────────────────────────────────────────


class MoodState(str, Enum):
    """16 discrete mood states for Guinevere's emotion system.

    These are greenfield — NOT ported from the old 5-mood FSM in
    guinevere/persona/mood_engine.py.
    """

    HAPPY = "HAPPY"
    ANGRY = "ANGRY"
    SAD = "SAD"
    JEALOUS = "JEALOUS"
    POSSESSIVE = "POSSESSIVE"
    NURTURING = "NURTURING"
    FEAR = "FEAR"
    DISGUST = "DISGUST"
    SURPRISE = "SURPRISE"
    ANTICIPATION = "ANTICIPATION"
    TRUST = "TRUST"
    BOREDOM = "BOREDOM"
    CURIOSITY = "CURIOSITY"
    PRIDE = "PRIDE"
    DESIRE = "DESIRE"
    AROUSAL = "AROUSAL"


# ── transition graph ─────────────────────────────────────────
# Sparse: ~3 targets per mood.  Each transition is reversible where
# semantically reasonable.  Total ~48 directed edges.

TRANSITIONS: dict[MoodState, list[MoodState]] = {
    MoodState.HAPPY: [MoodState.NURTURING, MoodState.PRIDE, MoodState.SURPRISE],
    MoodState.ANGRY: [MoodState.DISGUST, MoodState.POSSESSIVE, MoodState.SAD],
    MoodState.SAD: [MoodState.FEAR, MoodState.NURTURING, MoodState.TRUST],
    MoodState.JEALOUS: [MoodState.POSSESSIVE, MoodState.ANGRY, MoodState.SAD],
    MoodState.POSSESSIVE: [MoodState.JEALOUS, MoodState.ANGRY, MoodState.DESIRE],
    MoodState.NURTURING: [MoodState.TRUST, MoodState.HAPPY, MoodState.SAD],
    MoodState.FEAR: [MoodState.SAD, MoodState.ANGRY, MoodState.SURPRISE],
    MoodState.DISGUST: [MoodState.ANGRY, MoodState.FEAR, MoodState.BOREDOM],
    MoodState.SURPRISE: [MoodState.CURIOSITY, MoodState.FEAR, MoodState.HAPPY],
    MoodState.ANTICIPATION: [MoodState.CURIOSITY, MoodState.DESIRE, MoodState.TRUST],
    MoodState.TRUST: [MoodState.NURTURING, MoodState.HAPPY, MoodState.ANTICIPATION],
    MoodState.BOREDOM: [MoodState.CURIOSITY, MoodState.DISGUST, MoodState.ANTICIPATION],
    MoodState.CURIOSITY: [MoodState.SURPRISE, MoodState.ANTICIPATION, MoodState.BOREDOM],
    MoodState.PRIDE: [MoodState.HAPPY, MoodState.ANGRY, MoodState.ANTICIPATION],
    MoodState.DESIRE: [MoodState.AROUSAL, MoodState.POSSESSIVE, MoodState.ANTICIPATION],
    MoodState.AROUSAL: [MoodState.DESIRE, MoodState.HAPPY, MoodState.ANGRY],
}

# Mood categories for prompt formatting.
MOOD_CATEGORIES: dict[MoodState, str] = {
    MoodState.HAPPY: "positive",
    MoodState.ANGRY: "negative",
    MoodState.SAD: "negative",
    MoodState.JEALOUS: "volatile",
    MoodState.POSSESSIVE: "volatile",
    MoodState.NURTURING: "positive",
    MoodState.FEAR: "negative",
    MoodState.DISGUST: "negative",
    MoodState.SURPRISE: "neutral",
    MoodState.ANTICIPATION: "positive",
    MoodState.TRUST: "positive",
    MoodState.BOREDOM: "neutral",
    MoodState.CURIOSITY: "positive",
    MoodState.PRIDE: "positive",
    MoodState.DESIRE: "volatile",
    MoodState.AROUSAL: "volatile",
}


# ── transition validation ────────────────────────────────────


def can_transition(from_mood: MoodState, to_mood: MoodState) -> bool:
    """Return True if the transition is allowed by the graph."""
    return to_mood in TRANSITIONS.get(from_mood, [])


def transition(from_mood: MoodState, to_mood: MoodState) -> MoodState:
    """Validate and return the new mood.  Returns *from_mood* if the
    transition is not allowed (no exception — fail-soft).
    """
    if can_transition(from_mood, to_mood):
        return to_mood
    logger.warning(
        "emotion.transition.rejected",
        from_mood=from_mood.value,
        to_mood=to_mood.value,
    )
    return from_mood


# ── affect vector (8-dim, ADR-063 §5) ───────────────────────


AFFECT_DIMENSIONS: tuple[str, ...] = (
    "curiosity",
    "concern",
    "warmth",
    "vigilance",
    "irritation",
    "satisfaction",
    "resignation",
    "anticipation",
)


@dataclass
class EmotionState:
    """Mutable emotion state for a single agent instance.

    Attributes:
        current_mood: The active 16-mood state.
        intensity: Mood intensity in [0.0, 1.0].
        affect: 8-dimensional affect vector (ADR-063 §5).
        last_updated: UTC timestamp of last state change.
        transition_history: Recent transitions as (from, to, timestamp) tuples.
    """

    current_mood: MoodState = MoodState.HAPPY
    intensity: float = 0.5
    affect: dict[str, float] = field(
        default_factory=lambda: {dim: 0.5 for dim in AFFECT_DIMENSIONS},
    )
    last_updated: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    transition_history: list[tuple[MoodState, MoodState, datetime]] = field(
        default_factory=list,
    )

    def ewma_update(self, new_values: dict[str, float], lam: float = 0.3) -> None:
        """Apply EWMA update to the affect vector.

        Args:
            new_values: Mapping of dimension name -> new reading.
            lam: Smoothing factor (0 < lam <= 1).  Higher = more responsive.
        """
        for name, value in new_values.items():
            if name in self.affect:
                old = self.affect[name]
                self.affect[name] = lam * value + (1.0 - lam) * old

    def set_mood(self, new_mood: MoodState, intensity: float = 0.5) -> None:
        """Record a mood transition (validates via transition graph)."""
        resolved = transition(self.current_mood, new_mood)
        if resolved != self.current_mood:
            now = datetime.now(timezone.utc)
            self.transition_history.append((self.current_mood, resolved, now))
            # Keep only last 10 transitions.
            if len(self.transition_history) > 10:
                self.transition_history = self.transition_history[-10:]
            self.current_mood = resolved
            self.intensity = max(0.0, min(1.0, intensity))
            self.last_updated = now
            logger.info(
                "emotion.mood_changed",
                from_mood=self.transition_history[-1][0].value,
                to_mood=resolved.value,
                intensity=self.intensity,
            )

    def force_mood(self, mood: MoodState, intensity: float = 0.5) -> None:
        """Force a mood transition bypassing the graph (safety override)."""
        now = datetime.now(timezone.utc)
        self.transition_history.append((self.current_mood, mood, now))
        if len(self.transition_history) > 10:
            self.transition_history = self.transition_history[-10:]
        self.current_mood = mood
        self.intensity = max(0.0, min(1.0, intensity))
        self.last_updated = now
        logger.info(
            "emotion.mood_forced",
            to_mood=mood.value,
            intensity=self.intensity,
        )

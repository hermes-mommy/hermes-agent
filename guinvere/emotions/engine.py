"""Emotion Engine — per-turn emotion processing, affect EWMA, and
system-prompt formatting.

Holds EmotionState, runs the classifier each turn, updates the
8-dim affect vector via EWMA (lambda ~0.3), and exposes:
  - format_for_system_prompt() → str (volatile block content)
  - on_turn_start() / on_turn_end() hooks
  - wire(agent) — attaches agent._emotion_state (parent calls this)

Does NOT edit agent_init.py, system_prompt.py, or config/models.py
(parent owns those shared-file appends).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from guinevere.emotions.classifier import EmotionClassifier, MockEmotionClassifier
from guinevere.emotions.fsm import (
    AFFECT_DIMENSIONS,
    MOOD_CATEGORIES,
    EmotionState,
    MoodState,
)

import structlog

logger = structlog.get_logger("guinevere.emotions")

# Default EWMA lambda for affect vector updates.
_DEFAULT_LAMBDA: float = 0.3

# Affect signatures: mood → target affect values.
# Not all 8 dimensions need a mapping per mood; unmapped dimensions
# stay at their current EWMA value.
_MOOD_AFFECT: dict[MoodState, dict[str, float]] = {
    MoodState.HAPPY: {"curiosity": 0.7, "warmth": 0.8, "satisfaction": 0.9, "irritation": 0.1},
    MoodState.ANGRY: {"irritation": 0.9, "vigilance": 0.8, "warmth": 0.1, "satisfaction": 0.1},
    MoodState.SAD: {"concern": 0.8, "resignation": 0.7, "warmth": 0.3, "satisfaction": 0.1},
    MoodState.JEALOUS: {"vigilance": 0.8, "irritation": 0.6, "concern": 0.7, "warmth": 0.2},
    MoodState.POSSESSIVE: {"vigilance": 0.9, "irritation": 0.5, "concern": 0.6, "warmth": 0.4},
    MoodState.NURTURING: {"warmth": 0.9, "concern": 0.7, "satisfaction": 0.6, "curiosity": 0.4},
    MoodState.FEAR: {"vigilance": 0.9, "concern": 0.8, "satisfaction": 0.1, "resignation": 0.5},
    MoodState.DISGUST: {"irritation": 0.7, "vigilance": 0.6, "warmth": 0.1, "resignation": 0.4},
    MoodState.SURPRISE: {"curiosity": 0.8, "anticipation": 0.6, "vigilance": 0.5, "concern": 0.4},
    MoodState.ANTICIPATION: {"anticipation": 0.9, "curiosity": 0.7, "satisfaction": 0.5, "warmth": 0.4},
    MoodState.TRUST: {"warmth": 0.8, "satisfaction": 0.7, "vigilance": 0.2, "curiosity": 0.5},
    MoodState.BOREDOM: {"curiosity": 0.2, "satisfaction": 0.2, "resignation": 0.6, "anticipation": 0.3},
    MoodState.CURIOSITY: {"curiosity": 0.9, "anticipation": 0.7, "vigilance": 0.4, "satisfaction": 0.5},
    MoodState.PRIDE: {"satisfaction": 0.9, "warmth": 0.6, "vigilance": 0.3, "irritation": 0.1},
    MoodState.DESIRE: {"anticipation": 0.8, "warmth": 0.7, "vigilance": 0.5, "curiosity": 0.6},
    MoodState.AROUSAL: {"anticipation": 0.9, "vigilance": 0.6, "warmth": 0.5, "irritation": 0.3},
}


class EmotionEngine:
    """Per-turn emotion processing engine.

    Lifecycle per agent turn:
      1. on_turn_start() — classify user message, update mood + affect.
      2. (agent processes turn)
      3. on_turn_end() — log, noop for now (future: persistence hook).
      4. format_for_system_prompt() — called by parent when building
         the volatile prompt block.

    Args:
        classifier: An EmotionClassifier implementation.
        ewma_lambda: Smoothing factor for affect EWMA (default 0.3).
    """

    def __init__(
        self,
        classifier: EmotionClassifier | None = None,
        ewma_lambda: float = _DEFAULT_LAMBDA,
    ) -> None:
        self._classifier = classifier or MockEmotionClassifier()
        self._lambda = ewma_lambda
        self._state = EmotionState()
        self._turn_count: int = 0

    # ── public properties ────────────────────────────────────

    @property
    def state(self) -> EmotionState:
        """Return the mutable emotion state."""
        return self._state

    @property
    def turn_count(self) -> int:
        """Number of turns processed."""
        return self._turn_count

    # ── turn hooks ───────────────────────────────────────────

    def on_turn_start(self, user_message: str, context: dict[str, Any] | None = None) -> MoodState:
        """Classify the user message and update mood + affect.

        Args:
            user_message: The incoming user text.
            context: Optional context dict (current_mood is injected).

        Returns:
            The MoodState after classification.
        """
        ctx = dict(context or {})
        ctx.setdefault("current_mood", self._state.current_mood)

        new_mood = self._classifier.classify(user_message, ctx)

        # Update mood (validates transition graph internally).
        self._state.set_mood(new_mood, intensity=self._state.intensity)

        # Update affect vector with the mood's signature.
        affect_signature = _MOOD_AFFECT.get(new_mood, {})
        if affect_signature:
            self._state.ewma_update(affect_signature, lam=self._lambda)

        self._turn_count += 1
        logger.debug(
            "emotion.turn_start",
            turn=self._turn_count,
            mood=self._state.current_mood.value,
            intensity=self._state.intensity,
        )
        return self._state.current_mood

    def on_turn_end(self) -> None:
        """Post-turn hook.  Currently a no-op; future: persistence."""
        logger.debug("emotion.turn_end", turn=self._turn_count)

    # ── system prompt formatting ─────────────────────────────

    def format_for_system_prompt(self) -> str:
        """Return the emotion volatile block for the system prompt.

        The parent appends this string to volatile_parts in
        system_prompt.py.  We do NOT edit that file.

        Returns:
            Multi-line string describing current mood + affect.
        """
        mood = self._state.current_mood
        category = MOOD_CATEGORIES.get(mood, "neutral")
        intensity = self._state.intensity

        # Recent transitions (last 3).
        history_lines: list[str] = []
        for from_m, to_m, ts in self._state.transition_history[-3:]:
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            if age < 60:
                age_str = f"{int(age)}s ago"
            elif age < 3600:
                age_str = f"{int(age / 60)}m ago"
            else:
                age_str = f"{int(age / 3600)}h ago"
            history_lines.append(f"  {from_m.value}->{to_m.value} ({age_str})")

        history_block = "\n".join(history_lines) if history_lines else "  (none)"

        # Affect summary: top-3 dimensions by value.
        sorted_affect = sorted(
            self._state.affect.items(), key=lambda kv: kv[1], reverse=True,
        )
        top_affect = ", ".join(
            f"{dim}={val:.2f}" for dim, val in sorted_affect[:3]
        )

        return (
            f"[MOOD STATE]\n"
            f"Current mood: {mood.value} (intensity: {intensity:.1f})\n"
            f"Mood category: {category}\n"
            f"Affect top-3: {top_affect}\n"
            f"Transition history:\n{history_block}"
        )


# ── wire function ────────────────────────────────────────────


def wire(agent: Any, classifier: EmotionClassifier | None = None) -> EmotionEngine:
    """Attach an EmotionEngine to an agent instance.

    The parent calls this from agent_init.py (appends-only block).
    We do NOT edit agent_init.py.

    Args:
        agent: The agent instance (must accept arbitrary attributes).
        classifier: Optional classifier override (default MockEmotionClassifier).

    Returns:
        The created EmotionEngine instance.
    """
    engine = EmotionEngine(classifier=classifier)
    agent._emotion_engine = engine
    agent._emotion_state = engine.state
    logger.info(
        "emotion.wire.complete",
        initial_mood=engine.state.current_mood.value,
    )
    return engine

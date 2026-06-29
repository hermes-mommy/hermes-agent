"""Emotion System — P24 M4.

Re-exports the public API: MoodState, EmotionEngine, EmotionState.
"""

from guinevere.emotions.engine import EmotionEngine, wire
from guinevere.emotions.fsm import EmotionState, MoodState

__all__ = [
    "EmotionEngine",
    "EmotionState",
    "MoodState",
    "wire",
]

"""Guinevere Consciousness Loop — unified thought-stream architecture.

Re-exports the primary public interface: ConsciousnessLoop, ThoughtStream,
Thought, ThoughtType, ConsciousnessState, and MetaCogEval.
"""

from guinevere.consciousness.loop import ConsciousnessLoop, THOUGHT_TYPE_NAMES
from guinevere.consciousness.metacognition import MetaCogEval
from guinevere.consciousness.state import (
    AffectVector,
    ConsciousnessState,
    DreamJournalEntry,
)
from guinevere.consciousness.thought import Thought, ThoughtType
from guinevere.consciousness.thought_stream import ThoughtStream

__all__ = [
    "AffectVector",
    "ConsciousnessLoop",
    "ConsciousnessState",
    "DreamJournalEntry",
    "MetaCogEval",
    "THOUGHT_TYPE_NAMES",
    "Thought",
    "ThoughtStream",
    "ThoughtType",
]

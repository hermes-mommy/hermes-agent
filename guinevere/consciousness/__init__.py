"""Guinevere Consciousness Loop — ADR-063 composite 7-substrate architecture.

Re-exports the primary public interface: ConsciousnessLoop and ConsciousnessState.
"""

from guinevere.consciousness.loop import ConsciousnessLoop, SUBSTRATE_NAMES
from guinevere.consciousness.state import (
    AffectVector,
    ConsciousnessState,
    DreamJournalEntry,
    SubstrateStatus,
)

__all__ = [
    "AffectVector",
    "ConsciousnessLoop",
    "ConsciousnessState",
    "DreamJournalEntry",
    "SUBSTRATE_NAMES",
    "SubstrateStatus",
]

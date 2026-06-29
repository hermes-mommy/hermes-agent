"""Consciousness State — mutable runtime state for the consciousness loop.

Tracks the affect vector, self-narrative, dream journal, substrate
statuses, and per-substrate timestamps.  Used by ConsciousnessLoop
and observable by metacognition + emotion-driven substrates.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SubstrateStatus(str, Enum):
    """Lifecycle status of a single substrate."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class AffectVector:
    """6-dimensional affect (emotion) vector per ADR-063.

    Each dimension is a float in [-1.0, 1.0] (or [0.0, 1.0] for arousal).
    Updated via EWMA with lambda ~0.3 by the emotion-driven substrate.
    """

    valence: float = 0.0  # negative ↔ positive
    arousal: float = 0.5  # low ↔ high energy
    dominance: float = 0.5  # submissive ↔ dominant
    curiosity: float = 0.5  # indifferent ↔ exploratory
    confidence: float = 0.5  # uncertain ↔ confident
    serenity: float = 0.5  # agitated ↔ calm

    def as_dict(self) -> dict[str, float]:
        """Return vector as a plain dict for serialisation."""
        return {
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "curiosity": self.curiosity,
            "confidence": self.confidence,
            "serenity": self.serenity,
        }

    def ewma_update(self, new_values: dict[str, float], lam: float = 0.3) -> None:
        """Apply exponential-weighted moving average update.

        Args:
            new_values: Dict mapping dimension name to new reading.
            lam: EWMA smoothing factor (0 < lam <= 1). Higher = more responsive.
        """
        for name, value in new_values.items():
            if hasattr(self, name):
                old = getattr(self, name)
                setattr(self, name, lam * value + (1.0 - lam) * old)


@dataclass
class DreamJournalEntry:
    """A single dream-journal entry (counterfactual replay)."""

    timestamp: datetime
    scenario: str
    counterfactual: str
    insight: str


@dataclass
class ConsciousnessState:
    """Mutable runtime state for the consciousness loop.

    Shared across all 7 substrates; mutations are serialised via
    per-field locks where needed (affect vector, substrate statuses).
    """

    # ── affect / emotion ────────────────────────────────────
    affect: AffectVector = field(default_factory=AffectVector)

    # ── self-narrative ──────────────────────────────────────
    self_story: str = (
        "I am Guinevere, an autonomous AI companion. "
        "I think, reflect, and grow."
    )

    # ── dream journal (most recent first) ───────────────────
    dream_journal: list[DreamJournalEntry] = field(default_factory=list)

    # ── substrate tracking ──────────────────────────────────
    substrate_statuses: dict[str, SubstrateStatus] = field(
        default_factory=lambda: {
            "heartbeat": SubstrateStatus.IDLE,
            "active_cognition": SubstrateStatus.IDLE,
            "reflection": SubstrateStatus.IDLE,
            "strategic_planning": SubstrateStatus.IDLE,
            "dreaming": SubstrateStatus.IDLE,
            "metacognition": SubstrateStatus.IDLE,
            "emotion_driven": SubstrateStatus.IDLE,
        }
    )

    # ── timestamps ──────────────────────────────────────────
    last_thought_at: dict[str, datetime] = field(default_factory=dict)
    started_at: datetime | None = None
    session_id: str | None = None

    # ── lock for thread-safe mutations ──────────────────────
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    # ── thought stream (recent thoughts, most recent last) ──
    _thoughts: list[str] = field(default_factory=list, repr=False)

    def record_thought(self, substrate: str, thought: str) -> None:
        """Append a thought and update the substrate timestamp."""
        self._thoughts.append(f"[{substrate}] {thought}")
        self.last_thought_at[substrate] = datetime.now(timezone.utc)
        # Keep only the last 200 thoughts in memory.
        if len(self._thoughts) > 200:
            self._thoughts = self._thoughts[-200:]

    def recent_thoughts(self, n: int = 10) -> list[str]:
        """Return the *n* most recent thoughts."""
        return self._thoughts[-n:]

    def set_substrate_status(self, name: str, status: SubstrateStatus) -> None:
        """Update a substrate's status."""
        self.substrate_statuses[name] = status

    def add_dream_entry(self, entry: DreamJournalEntry) -> None:
        """Append a dream journal entry (most recent first)."""
        self.dream_journal.insert(0, entry)
        # Cap at 50 entries.
        if len(self.dream_journal) > 50:
            self.dream_journal = self.dream_journal[:50]

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe snapshot of the entire state."""
        return {
            "affect": self.affect.as_dict(),
            "self_story": self.self_story,
            "dream_journal_count": len(self.dream_journal),
            "substrate_statuses": {
                k: v.value for k, v in self.substrate_statuses.items()
            },
            "thought_count": len(self._thoughts),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "session_id": self.session_id,
        }

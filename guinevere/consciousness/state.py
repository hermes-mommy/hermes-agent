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

    def get_influence(self) -> dict[str, object]:
        """Return affect→thought influence mapping.

        Maps current affect state to modifiers that influence thought
        generation: tone, confidence threshold, priority, thought type
        bias, and energy level.

        Returns:
            dict with keys:
                tone_modifier: "positive", "negative", or "neutral"
                confidence_threshold_modifier: float in [-0.2, 0.2]
                priority_bias: float in [0.0, 1.0]
                thought_type_bias: "dreaming", "cognition", or None
                energy_level: float in [0.0, 1.0]
        """
        # Tone from valence.
        if self.valence >= 0.3:
            tone_modifier = "positive"
        elif self.valence <= -0.3:
            tone_modifier = "negative"
        else:
            tone_modifier = "neutral"

        # Confidence threshold modifier from arousal.
        # Low arousal (calm) → lower threshold (easier to act).
        # High arousal → higher threshold (more cautious).
        # Maps arousal [0, 1] → [-0.2, 0.2].
        confidence_threshold_modifier = (self.arousal - 0.5) * 0.4

        # Priority bias from dominance.
        # Higher dominance → higher priority bias [0.0, 1.0].
        priority_bias = max(0.0, min(1.0, self.dominance))

        # Thought type bias from curiosity and dominance.
        thought_type_bias = None
        if self.curiosity >= 0.7:
            if self.dominance >= 0.7:
                thought_type_bias = "planning"
            else:
                thought_type_bias = "dreaming"
        elif self.dominance >= 0.7:
            thought_type_bias = "planning"

        # Energy level from arousal, clamped to [0.0, 1.0].
        energy_level = max(0.0, min(1.0, self.arousal))

        return {
            "tone_modifier": tone_modifier,
            "confidence_threshold_modifier": confidence_threshold_modifier,
            "priority_bias": priority_bias,
            "thought_type_bias": thought_type_bias,
            "energy_level": energy_level,
        }


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

    def update_affect_from_thought(
        self, thought_content: str, thought_type: str
    ) -> None:
        """Update affect vector based on thought content analysis.

        Uses basic word-list heuristics (no external NLP) to adjust
        valence, arousal, curiosity, confidence, and serenity.
        Updates are applied via EWMA with lambda=0.3.

        Args:
            thought_content: The text of the thought.
            thought_type: The thought type string (e.g. "cognition").
        """
        content_lower = thought_content.lower()
        words = content_lower.split()

        # ── Positive / negative sentiment ─────────────────────
        _POSITIVE_WORDS = frozenset({
            "good", "great", "excellent", "happy", "positive", "success",
            "wonderful", "amazing", "brilliant", "love", "joy", "hope",
            "progress", "improve", "improved", "improvement", "achieve",
            "achieved", "benefit", "beneficial", "effective", "efficient",
            "elegant", "beautiful", "creative", "inspired", "productive",
            "thriving", "flourish", "promising", "optimistic", "grateful",
            "confident", "empowered", "vibrant", "harmonious", "celebrate",
            "delight", "fantastic", "superb", "remarkable", "strengthen",
        })
        _NEGATIVE_WORDS = frozenset({
            "bad", "terrible", "awful", "sad", "negative", "failure",
            "horrible", "dreadful", "hate", "misery", "despair", "regress",
            "worse", "worst", "damage", "harmful", "ineffective", "broken",
            "ugly", "destructive", "anxious", "frustrated", "disappoint",
            "disappointing", "struggle", "suffering", "painful", "critical",
            "error", "fault", "flaw", "risk", "threat", "danger", "crisis",
            "fear", "angry", "confused", "overwhelmed", "exhausted",
        })
        positive_count = sum(1 for w in words if w in _POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in _NEGATIVE_WORDS)
        total_sentiment = positive_count + negative_count

        if total_sentiment > 0:
            valence_signal = (positive_count - negative_count) / total_sentiment
        else:
            valence_signal = 0.0

        # ── Arousal from intensity ────────────────────────────
        exclamation_count = thought_content.count("!")
        intensity_markers = sum(
            1 for w in words
            if w in {
                "must", "critical", "urgent", "immediately", "now",
                "always", "never", "extremely", "absolutely", "terrible",
                "amazing", "incredible", "unbelievable",
            }
        )
        arousal_signal = min(1.0, 0.5 + (exclamation_count * 0.1) + (intensity_markers * 0.1))

        # ── Curiosity from questions and exploratory language ──
        question_marks = thought_content.count("?")
        exploratory_words = sum(
            1 for w in words
            if w in {
                "why", "how", "what", "explore", "discover", "investigate",
                "curious", "wonder", "question", "hypothesis", "experiment",
                "perhaps", "maybe", "possible", "alternative",
            }
        )
        curiosity_signal = min(1.0, 0.5 + (question_marks * 0.15) + (exploratory_words * 0.05))

        # ── Confidence from certainty markers ─────────────────
        certainty_words = sum(
            1 for w in words
            if w in {
                "certain", "definitely", "clearly", "surely", "indeed",
                "absolutely", "confirmed", "proven", "established", "know",
                "confident", "precise", "exact", "undoubtedly",
            }
        )
        uncertainty_words = sum(
            1 for w in words
            if w in {
                "maybe", "perhaps", "uncertain", "unsure", "possibly",
                "might", "could", "seems", "appears", "guess", "doubt",
                "approximately", "roughly", "unclear",
            }
        )
        confidence_signal = min(
            1.0,
            max(0.0, 0.5 + (certainty_words - uncertainty_words) * 0.1),
        )

        # ── Apply EWMA update ─────────────────────────────────
        self.affect.ewma_update(
            {
                "valence": valence_signal,
                "arousal": arousal_signal,
                "curiosity": curiosity_signal,
                "confidence": confidence_signal,
            },
            lam=0.3,
        )

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

"""Thought data model — atomic unit of the consciousness thought stream.

Replaces the 7-substrate pattern with a unified stream of typed thoughts.
Each thought flows through: generate -> metacog_eval -> record -> (action).

Design decisions:
  - ThoughtType enum covers all 6 consciousness modes (ADR-063 replacement).
  - Thought is an immutable dataclass (frozen=True) for thread safety.
  - Confidence drives action threshold (>0.8 triggers action execution).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ThoughtType(str, Enum):
    """Types of consciousness thoughts in the unified thought stream.

    Maps to the former 7 substrates (heartbeat, active_cognition, reflection,
    strategic_planning, dreaming, metacognition, emotion_driven) as 6 types.
    """

    COGNITION = "cognition"  # active thinking / "I am thinking about X"
    REFLECTION = "reflection"  # memory consolidation / lessons learned
    PLANNING = "planning"  # strategic planning / aspiration pull
    DREAMING = "dreaming"  # counterfactual replay / creative exploration
    META = "meta"  # metacognition / thinking about thinking
    HEARTBEAT = "heartbeat"  # liveness pulse / system health


@dataclass(frozen=True)
class Thought:
    """A single thought in the consciousness stream.

    Immutable once created. Recorded into ConsciousnessState._thoughts
    and optionally triggers action execution when confidence > 0.8.

    Attributes:
        type: The category of this thought (COGNITION, REFLECTION, etc.).
        content: The LLM-generated thought text.
        confidence: Metacognitive quality assessment [0.0, 1.0].
        timestamp: UTC creation time.
        acted: Whether this thought triggered an action.
        affect_snapshot: Affect vector values at time of generation.
    """

    type: ThoughtType
    content: str
    confidence: float = 0.5
    timestamp: Optional[datetime] = None
    acted: bool = False
    affect_snapshot: Optional[dict[str, float]] = None

    def __post_init__(self) -> None:
        """Set defaults for fields that cannot use mutable factories in frozen dataclass."""
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc))
        if self.affect_snapshot is None:
            object.__setattr__(self, "affect_snapshot", {})

    def to_log_string(self) -> str:
        """Format for logging and state recording."""
        return f"[{self.type.value}] {self.content}"

    def should_act(self, threshold: float = 0.8) -> bool:
        """Return True if this thought's confidence exceeds the action threshold."""
        return self.confidence > threshold and not self.acted

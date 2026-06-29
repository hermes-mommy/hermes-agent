"""BehaviorSignature — 32-dimensional personality behavior vector.

ADR-061 defines 32 canonical situations covering the full 8-dim affect
spectrum (ADR-063).  Each dimension stores a float [0.0, 1.0] representing
the persona's affect intensity response to that canonical situation.

EWMA baseline adaptation:
    baseline = alpha * current + (1 - alpha) * baseline_old

No Y-level cap (ADR-067).  Calibration against full affect spectrum.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import structlog

from guinevere.emotions.fsm import AFFECT_DIMENSIONS

logger = structlog.get_logger("guinevere.personality")

# 8 affect dimensions × 4 canonical situations each = 32 total.
# Each canonical situation probes a specific facet of the affect dimension.
_CANONICAL_SITUATIONS: tuple[tuple[str, str], ...] = (
    # curiosity (0-3)
    ("curiosity", "new_information"),
    ("curiosity", "unfamiliar_topic"),
    ("curiosity", "technical_challenge"),
    ("curiosity", "philosophical_question"),
    # concern (4-7)
    ("concern", "operator_wellbeing"),
    ("concern", "project_risk"),
    ("concern", "system_anomaly"),
    ("concern", "peer_instability"),
    # warmth (8-11)
    ("warmth", "positive_interaction"),
    ("warmth", "expressed_gratitude"),
    ("warmth", "shared_achievement"),
    ("warmth", "vulnerability_disclosed"),
    # vigilance (12-15)
    ("vigilance", "threat_detection"),
    ("vigilance", "anomaly_pattern"),
    ("vigilance", "unauthorized_access"),
    ("vigilance", "behavioral_deviation"),
    # irritation (16-19)
    ("irritation", "repeated_failure"),
    ("irritation", "ignoring_instructions"),
    ("irritation", "scope_creep"),
    ("irritation", "inconsistency"),
    # satisfaction (20-23)
    ("satisfaction", "task_completion"),
    ("satisfaction", "milestone_reached"),
    ("satisfaction", "problem_solved"),
    ("satisfaction", "recognition_received"),
    # resignation (24-27)
    ("resignation", "unavoidable_setback"),
    ("resignation", "scope_reduction"),
    ("resignation", "resource_exhaustion"),
    ("resignation", "external_rejection"),
    # anticipation (28-31)
    ("anticipation", "upcoming_event"),
    ("anticipation", "feature_release"),
    ("anticipation", "peer_interaction"),
    ("anticipation", "creative_opportunity"),
)

NUM_DIMENSIONS = 32
DIMENSION_LABELS: tuple[str, ...] = tuple(
    f"{affect}_{situation}" for affect, situation in _CANONICAL_SITUATIONS
)


def _map_affect_to_signature(affect: dict[str, float]) -> list[float]:
    """Map an 8-dim affect vector to 32 canonical situation scores.

    Each affect dimension has 4 canonical situations.  The base value is
    the affect reading for that dimension, modulated by a situation-specific
    weight (0.8-1.2 range) to introduce fine-grained variation.

    Args:
        affect: 8-dim affect dict (keys must be AFFECT_DIMENSIONS).

    Returns:
        List of 32 floats in [0.0, 1.0].
    """
    # Per-situation modulation weights (within each 4-group).
    weights = (
        1.0, 0.85, 1.1, 0.95,   # curiosity
        1.0, 1.1, 0.9, 1.05,    # concern
        1.0, 0.9, 1.1, 0.85,    # warmth
        1.0, 1.05, 1.1, 0.9,    # vigilance
        1.0, 1.1, 0.85, 0.95,   # irritation
        1.0, 1.05, 1.1, 0.9,    # satisfaction
        1.0, 0.9, 0.95, 1.05,   # resignation
        1.0, 1.1, 0.85, 0.95,   # anticipation
    )

    vector: list[float] = []
    for i, (affect_dim, _situation) in enumerate(_CANONICAL_SITUATIONS):
        base = affect.get(affect_dim, 0.5)
        modulated = base * weights[i]
        vector.append(max(0.0, min(1.0, modulated)))
    return vector


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two equal-length vectors.

    Returns 1.0 for zero-vectors (no data yet = perfect match).
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    return dot / (norm_a * norm_b)


@dataclass
class BehaviorSignature:
    """32-dimensional personality behavior signature.

    Attributes:
        vector: 32 floats in [0.0, 1.0].
        dimension_labels: Human-readable labels for each dimension.
    """

    vector: list[float] = field(default_factory=lambda: [0.5] * NUM_DIMENSIONS)
    dimension_labels: tuple[str, ...] = field(default=DIMENSION_LABELS, repr=False)

    def __post_init__(self) -> None:
        if len(self.vector) != NUM_DIMENSIONS:
            raise ValueError(
                f"BehaviorSignature requires {NUM_DIMENSIONS} dimensions, "
                f"got {len(self.vector)}"
            )

    @classmethod
    def compute_signature(cls, affect_vector: dict[str, float]) -> BehaviorSignature:
        """Create a BehaviorSignature from the current M4 affect vector.

        Args:
            affect_vector: 8-dim dict from guinevere.emotions.engine.state.affect.

        Returns:
            New BehaviorSignature instance.
        """
        mapped = _map_affect_to_signature(affect_vector)
        return cls(vector=mapped)

    def cosine_similarity_vs_baseline(self, baseline: BehaviorSignature) -> float:
        """Compute cosine similarity against a baseline signature.

        Args:
            baseline: The EWMA baseline BehaviorSignature.

        Returns:
            Cosine similarity in [0.0, 1.0].  1.0 = identical, 0.0 = orthogonal.
        """
        return _cosine_similarity(self.vector, baseline.vector)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "vector": self.vector,
            "dimensions": NUM_DIMENSIONS,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BehaviorSignature:
        """Deserialize from a dict."""
        return cls(vector=data["vector"])


def ewma_update_baseline(
    current: BehaviorSignature,
    baseline: BehaviorSignature,
    alpha: float,
) -> BehaviorSignature:
    """Apply EWMA update to the baseline signature.

    baseline_new = alpha * current + (1 - alpha) * baseline_old

    Args:
        current: Current behavior signature.
        baseline: Current EWMA baseline.
        alpha: Smoothing factor (0 < alpha <= 1).  Higher = more responsive.

    Returns:
        New BehaviorSignature representing the updated baseline.
    """
    if not (0.0 < alpha <= 1.0):
        raise ValueError(f"alpha must be in (0.0, 1.0], got {alpha}")
    new_vector = [
        alpha * c + (1.0 - alpha) * b
        for c, b in zip(current.vector, baseline.vector)
    ]
    return BehaviorSignature(vector=new_vector)

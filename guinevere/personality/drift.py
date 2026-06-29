"""DriftDetector — personality drift monitoring via cosine similarity.

ADR-061: cosine similarity over 32-dim behavior vectors.
ADR-067: NO y-level check.  Concept REMOVED from runtime.
Plan §5.12 line 830: monitoring-only, NO rollback.

Reads the M4 affect vector from guinevere.emotions.engine.state.affect
(8-dim dict).  Computes BehaviorSignature, cosine similarity vs EWMA
baseline, 0.68 hysteresis threshold -> anomaly flag.

Anomaly escalates to DAO (M7) as Tier-4 proposal (B10: DAO does NOT
govern persona — anomaly escalation only).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from guinevere.personality.signature import (
    NUM_DIMENSIONS,
    BehaviorSignature,
    ewma_update_baseline,
)

logger = structlog.get_logger("guinevere.personality")

# ADR-061 hysteresis threshold.
_DEFAULT_THRESHOLD: float = 0.68

# Default EWMA alpha for baseline adaptation.
_DEFAULT_ALPHA: float = 0.15


class DriftDetector:
    """Personality drift detector — monitoring-only, no enforcement.

    Lifecycle:
      1. __init__() with optional config overrides.
      2. compute_drift_score(affect) each turn.
      3. is_anomalous() after compute_drift_score.
      4. format_for_system_prompt() for volatile prompt block.

    Does NOT edit agent_init.py, system_prompt.py, or config/models.py
    (parent owns those shared-file appends).

    Attributes:
        threshold: Cosine similarity below this is anomalous (default 0.68).
        alpha: EWMA smoothing factor for baseline adaptation.
    """

    def __init__(
        self,
        threshold: float = _DEFAULT_THRESHOLD,
        alpha: float = _DEFAULT_ALPHA,
        initial_affect: dict[str, float] | None = None,
    ) -> None:
        self.threshold = threshold
        self.alpha = alpha

        # Initial baseline from default or provided affect.
        affect = initial_affect or {dim: 0.5 for dim in (
            "curiosity", "concern", "warmth", "vigilance",
            "irritation", "satisfaction", "resignation", "anticipation",
        )}
        self._baseline = BehaviorSignature.compute_signature(affect)

        # Current state (updated each turn).
        self._current = self._baseline
        self._last_cosine: float = 1.0
        self._anomaly_count: int = 0
        self._turn_count: int = 0
        self._last_anomaly_time: datetime | None = None

        logger.info(
            "drift.detector.initialized",
            threshold=self.threshold,
            alpha=self.alpha,
            dims=NUM_DIMENSIONS,
        )

    # ── public properties ────────────────────────────────────

    @property
    def current_signature(self) -> BehaviorSignature:
        """The most recently computed behavior signature."""
        return self._current

    @property
    def baseline_signature(self) -> BehaviorSignature:
        """The current EWMA baseline signature."""
        return self._baseline

    @property
    def last_cosine_similarity(self) -> float:
        """The cosine similarity from the last drift computation."""
        return self._last_cosine

    @property
    def anomaly_count(self) -> int:
        """Total anomalies detected since initialization."""
        return self._anomaly_count

    @property
    def turn_count(self) -> int:
        """Number of turns processed."""
        return self._turn_count

    # ── drift computation ───────────────────────────────────

    def compute_drift_score(self, affect: dict[str, float]) -> float:
        """Compute drift score for the current affect vector.

        Reads the 8-dim affect dict from M4 emotion engine, computes
        the 32-dim behavior signature, and returns cosine similarity
        against the EWMA baseline.

        After computing, the baseline is adapted via EWMA.

        Args:
            affect: 8-dim affect dict from guinevere.emotions.engine.state.affect.

        Returns:
            Cosine similarity in [0.0, 1.0].  Lower = more drift.
        """
        self._current = BehaviorSignature.compute_signature(affect)
        self._last_cosine = self._current.cosine_similarity_vs_baseline(self._baseline)

        # Anomaly detection.
        is_anomaly = self._last_cosine < self.threshold
        if is_anomaly:
            self._anomaly_count += 1
            self._last_anomaly_time = datetime.now(timezone.utc)
            logger.warning(
                "drift.anomaly.detected",
                cosine=self._last_cosine,
                threshold=self.threshold,
                anomaly_count=self._anomaly_count,
            )

        # EWMA baseline adaptation (always — monitoring-only, no rollback).
        self._baseline = ewma_update_baseline(
            self._current, self._baseline, self.alpha,
        )

        self._turn_count += 1
        logger.debug(
            "drift.score",
            turn=self._turn_count,
            cosine=self._last_cosine,
            anomalous=is_anomaly,
        )
        return self._last_cosine

    def is_anomalous(self) -> bool:
        """Return True if the last drift score exceeded the anomaly threshold.

        Must be called after compute_drift_score().
        """
        return self._last_cosine < self.threshold

    # ── system prompt formatting ─────────────────────────────

    def format_for_system_prompt(self) -> str:
        """Return the drift volatile block for the system prompt.

        The parent appends this string to volatile_parts in
        system_prompt.py.  We do NOT edit that file.

        Returns:
            Multi-line string describing current drift state.
        """
        # Status classification.
        if self._last_cosine >= 0.85:
            status = "STABLE"
        elif self._last_cosine >= self.threshold:
            status = "DRIFTING"
        else:
            status = "ANOMALOUS"

        # Time since last anomaly.
        anomaly_line = "none"
        if self._last_anomaly_time is not None:
            age = (datetime.now(timezone.utc) - self._last_anomaly_time).total_seconds()
            if age < 60:
                anomaly_line = f"{int(age)}s ago"
            elif age < 3600:
                anomaly_line = f"{int(age / 60)}m ago"
            else:
                anomaly_line = f"{int(age / 3600)}h ago"

        # Top-3 shifted dimensions (largest delta from baseline).
        deltas = [
            (i, abs(self._current.vector[i] - self._baseline.vector[i]))
            for i in range(NUM_DIMENSIONS)
        ]
        deltas.sort(key=lambda x: x[1], reverse=True)
        shift_lines = []
        from guinevere.personality.signature import DIMENSION_LABELS
        for idx, delta_val in deltas[:3]:
            label = DIMENSION_LABELS[idx]
            cur = self._current.vector[idx]
            base = self._baseline.vector[idx]
            direction = "+" if cur > base else "-"
            shift_lines.append(f"  {label}: {base:.2f}->{cur:.2f} ({direction}{delta_val:.3f})")
        shift_block = "\n".join(shift_lines) if shift_lines else "  (none)"

        return (
            f"[PERSONALITY DRIFT]\n"
            f"Status: {status} (cos_sim={self._last_cosine:.3f}, "
            f"threshold={self.threshold})\n"
            f"Anomaly count: {self._anomaly_count} "
            f"(last: {anomaly_line})\n"
            f"Baseline adaptations: {self._turn_count}\n"
            f"Top shifted dimensions:\n{shift_block}"
        )


# ── wire function ────────────────────────────────────────────


def wire(
    agent: Any,
    threshold: float = _DEFAULT_THRESHOLD,
    alpha: float = _DEFAULT_ALPHA,
) -> DriftDetector:
    """Attach a DriftDetector to an agent instance.

    The parent calls this from agent_init.py (appends-only block).
    We do NOT edit agent_init.py.

    Reads the initial affect from agent._emotion_state.affect if available.

    Args:
        agent: The agent instance (must accept arbitrary attributes).
        threshold: Cosine similarity anomaly threshold (default 0.68).
        alpha: EWMA smoothing factor (default 0.15).

    Returns:
        The created DriftDetector instance.
    """
    initial_affect = None
    if hasattr(agent, "_emotion_state"):
        initial_affect = dict(agent._emotion_state.affect)

    detector = DriftDetector(
        threshold=threshold,
        alpha=alpha,
        initial_affect=initial_affect,
    )
    agent._drift_detector = detector
    logger.info("drift.wire.complete", threshold=threshold, alpha=alpha)
    return detector

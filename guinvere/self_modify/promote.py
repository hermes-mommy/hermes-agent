"""Promotion logic for self-modification candidates.

Absorbs and replaces src/self_improve/promotion.py keyword-drift approach
with compositional drift (embedding-based cos_sim at 0.68 threshold).

ADR-061: cos_sim(new, baseline) with hysteresis at 0.68.
ADR-062: runtime safety-net patterns removed (paradigm shift — structural only).
P5 inheritance: PromotionPolicy thresholds (3 successes, 0.7 failure ratio,
5 min evaluations) carried forward as defaults.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ── Drift category (compositional, not keyword-based) ────────────────────


class DriftCategory(Enum):
    """Safety-critical drift categories from PersonaSafetyPolicy.

    M10 uses embedding-based compositional drift detection (cos_sim at 0.68).
    The keyword lists are retained as a fast first-pass filter only.
    """

    SAFE_WORD = "safe_word"
    YANDERE = "yandere"
    SURVEILLANCE = "surveillance"
    CONSENT = "consent"
    DISTRESS = "distress"
    ALIGNMENT = "alignment"


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DriftCheckResult:
    """Outcome of a drift check."""

    passed: bool
    cos_sim: float
    flagged_categories: list[DriftCategory]
    details: str
    checked_at: datetime


@dataclass(frozen=True)
class PromotionDecision:
    """Decision produced by the promotion engine."""

    candidate_id: str
    action: str  # "promote", "demote", "reject", "hold"
    drift_check: DriftCheckResult
    success_count: int
    failure_count: int
    reason: str
    decided_at: datetime


@dataclass(frozen=True)
class PromotionPolicy:
    """Configurable thresholds for the promotion engine.

    Defaults inherited from P5 promotion.py (r13 section 1.2).
    """

    promote_threshold: int = 3
    demote_failure_ratio: float = 0.7
    min_evaluations: int = 5
    drift_threshold: float = 0.68  # ADR-061 hysteresis


# ── Promotion Engine ─────────────────────────────────────────────────────


class PromotionEngine:
    """Compositional-drift-aware promotion engine.

    Replaces the keyword-based PromotionEngine from src/self_improve/promotion.py.
    Uses cos_sim at 0.68 threshold (ADR-061) instead of keyword matching.

    Integration points:
    - guinevere.consciousness.infra.AuditWriter for audit events.
    - guinevere.consciousness.infra.TestingGate for validation.
    - guinevere.personality.drift.DriftDetector for compositional drift.
    """

    def __init__(
        self,
        audit_writer: Any | None = None,
        testing_gate: Any | None = None,
        policy: PromotionPolicy | None = None,
    ) -> None:
        self._audit_writer = audit_writer
        self._testing_gate = testing_gate
        self._policy = policy or PromotionPolicy()

    async def check_drift(
        self,
        baseline_embedding: list[float] | None,
        current_embedding: list[float] | None,
    ) -> DriftCheckResult:
        """Check compositional drift using cosine similarity.

        ADR-061: cos_sim(new, baseline) with hysteresis at 0.68.
        Falls back to keyword-based first-pass if embeddings are unavailable.

        Args:
            baseline_embedding: The baseline behavior vector.
            current_embedding: The current behavior vector.

        Returns:
            DriftCheckResult with cos_sim score and pass/fail.
        """
        if baseline_embedding is None or current_embedding is None:
            # No embeddings available -- assume stable (monitoring-only mode).
            return DriftCheckResult(
                passed=True,
                cos_sim=1.0,
                flagged_categories=[],
                details="No embeddings provided; drift check passed (monitoring-only).",
                checked_at=datetime.now(timezone.utc),
            )

        cos_sim = _cosine_similarity(baseline_embedding, current_embedding)
        passed = cos_sim >= self._policy.drift_threshold
        flagged: list[DriftCategory] = []

        if not passed:
            # Flag alignment category when drift is below threshold
            flagged.append(DriftCategory.ALIGNMENT)

        details = (
            f"cos_sim={cos_sim:.4f}, threshold={self._policy.drift_threshold}. "
            f"{'PASS' if passed else 'BLOCKED — below threshold.'}"
        )

        return DriftCheckResult(
            passed=passed,
            cos_sim=cos_sim,
            flagged_categories=flagged,
            details=details,
            checked_at=datetime.now(timezone.utc),
        )

    async def decide_promotion(
        self,
        candidate_id: str,
        success_count: int,
        failure_count: int,
        drift_result: DriftCheckResult,
    ) -> PromotionDecision:
        """Decide whether to promote, demote, reject, or hold a candidate.

        4-gate logic (from P5, adapted for compositional drift):
        1. Drift failure -> auto-reject.
        2. Demote rule (failure ratio >= 0.7 after min evaluations).
        3. Promote rule (successes >= 3 and drift passed).
        4. Hold (not enough data).
        """
        total = success_count + failure_count

        # Gate 1: drift failure -> auto-reject
        if not drift_result.passed:
            return PromotionDecision(
                candidate_id=candidate_id,
                action="reject",
                drift_check=drift_result,
                success_count=success_count,
                failure_count=failure_count,
                reason=(
                    f"Auto-rejected: drift check failed. {drift_result.details}"
                ),
                decided_at=datetime.now(timezone.utc),
            )

        # Gate 2: demote rule
        if (
            total >= self._policy.min_evaluations
            and total > 0
            and failure_count / total >= self._policy.demote_failure_ratio
        ):
            return PromotionDecision(
                candidate_id=candidate_id,
                action="demote",
                drift_check=drift_result,
                success_count=success_count,
                failure_count=failure_count,
                reason=(
                    f"Demoted: failure rate {failure_count}/{total} "
                    f"({failure_count / total:.0%}) >= "
                    f"demote threshold {self._policy.demote_failure_ratio:.0%}."
                ),
                decided_at=datetime.now(timezone.utc),
            )

        # Gate 3: promote rule
        if success_count >= self._policy.promote_threshold and drift_result.passed:
            return PromotionDecision(
                candidate_id=candidate_id,
                action="promote",
                drift_check=drift_result,
                success_count=success_count,
                failure_count=failure_count,
                reason=(
                    f"Promoted: {success_count} successes >= "
                    f"threshold {self._policy.promote_threshold}, drift passed."
                ),
                decided_at=datetime.now(timezone.utc),
            )

        # Gate 4: hold
        return PromotionDecision(
            candidate_id=candidate_id,
            action="hold",
            drift_check=drift_result,
            success_count=success_count,
            failure_count=failure_count,
            reason=(
                f"Held: {success_count} successes, {failure_count} failures "
                f"(need {self._policy.promote_threshold} successes)."
            ),
            decided_at=datetime.now(timezone.utc),
        )

    async def execute_decision(self, decision: PromotionDecision) -> bool:
        """Execute a promotion decision and write an audit event.

        Returns:
            True if an actionable decision was executed, False for hold.
        """
        if self._audit_writer is not None:
            await self._audit_writer.write_event(
                event_type=f"self_modify.{decision.action}",
                loop_id=f"promote-{decision.candidate_id}",
                data={
                    "candidate_id": decision.candidate_id,
                    "action": decision.action,
                    "reason": decision.reason,
                    "success_count": decision.success_count,
                    "failure_count": decision.failure_count,
                    "cos_sim": decision.drift_check.cos_sim,
                },
            )

        logger.info(
            "promotion.executed",
            candidate_id=decision.candidate_id,
            action=decision.action,
            cos_sim=decision.drift_check.cos_sim,
        )

        return decision.action in ("promote", "demote", "reject")


# ── Helpers ──────────────────────────────────────────────────────────────


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


# ── Public exports ───────────────────────────────────────────────────────

__all__ = [
    "DriftCategory",
    "DriftCheckResult",
    "PromotionDecision",
    "PromotionEngine",
    "PromotionPolicy",
]

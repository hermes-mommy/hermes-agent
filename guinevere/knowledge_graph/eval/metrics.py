"""Recall-quality metric primitives for the KG eval framework (P16-005).

This module implements the five metrics the A/B harness reports:

* :func:`compute_precision`
* :func:`compute_recall`
* :func:`compute_f1`
* :func:`compute_mrr`
* :func:`compute_ndcg`

All metrics are pure functions of two inputs (a ``set`` of retrieved
IDs and a ``set`` of relevant IDs, or a ranked ``list`` plus the
relevant set).  They contain no I/O, no global state, and no
dependencies on the recall pipeline — making them trivially
unit-testable.

Definitions
-----------

Given:

* ``R`` = set of retrieved IDs
* ``L`` = set of relevant (ground-truth) IDs
* ``k`` = the rank cutoff

::

    precision  = |R ∩ L| / |R|          (undefined → 0.0 when |R|=0)
    recall     = |R ∩ L| / |L|          (undefined → 0.0 when |L|=0)
    f1         = 2·P·R / (P + R)        (0.0 when P + R = 0)
    mrr        = 1 / rank_first_hit     (0.0 when no hit in ranked list)
    ndcg@k     = dcg@k / idcg@k         (0.0 when idcg@k = 0)

Where ``rank_first_hit`` is the 1-based position of the first
relevant item in ``ranked_results``.

Edge cases
----------

* Empty retrieved set: precision is ``0.0`` (no signal).  Recall is
  also ``0.0`` if relevant is non-empty.
* Empty relevant set: recall is ``0.0``; precision is ``1.0`` when
  retrieved is also empty, else ``0.0``.
* Duplicate IDs in the ranked list: first occurrence wins for MRR;
  nDCG counts each position independently (binary relevance).

Aggregation
-----------

:func:`aggregate_metrics` averages a list of
:class:`EvaluationMetrics` into one summary record.  All component
metrics are arithmetic means; ``total_cases`` and ``passed_cases``
are summed.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Primitive metrics
# ---------------------------------------------------------------------------


def compute_precision(retrieved: set[str], relevant: set[str]) -> float:
    """Precision = |retrieved ∩ relevant| / |retrieved|.

    Args:
        retrieved: Set of IDs returned by the recall pipeline.
        relevant: Set of ground-truth IDs.

    Returns:
        Precision in ``[0.0, 1.0]``.  ``0.0`` when ``retrieved``
        is empty (no signal at all).
    """
    if not retrieved:
        return 0.0
    if not relevant:
        # Defensive: when the oracle is empty but the system returned
        # something, precision is 0.  Otherwise the metric is undefined.
        return 0.0
    true_positives = len(retrieved & relevant)
    return true_positives / float(len(retrieved))


def compute_recall(retrieved: set[str], relevant: set[str]) -> float:
    """Recall = |retrieved ∩ relevant| / |relevant|.

    Args:
        retrieved: Set of IDs returned by the recall pipeline.
        relevant: Set of ground-truth IDs.

    Returns:
        Recall in ``[0.0, 1.0]``.  ``0.0`` when ``relevant`` is
        empty (no labels → nothing to recall).
    """
    if not relevant:
        return 0.0
    true_positives = len(retrieved & relevant)
    return true_positives / float(len(relevant))


def compute_f1(precision: float, recall: float) -> float:
    """F1 = 2·P·R / (P + R).

    Args:
        precision: Value in ``[0.0, 1.0]``.
        recall: Value in ``[0.0, 1.0]``.

    Returns:
        Harmonic mean.  ``0.0`` when both inputs are ``0.0``.
    """
    if precision < 0.0 or precision > 1.0:
        raise ValueError(f"precision must be in [0.0, 1.0]; got {precision}")
    if recall < 0.0 or recall > 1.0:
        raise ValueError(f"recall must be in [0.0, 1.0]; got {recall}")
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def compute_mrr(ranked_results: Sequence[str], relevant: set[str]) -> float:
    """Mean Reciprocal Rank of the first relevant hit.

    Args:
        ranked_results: Ordered list of IDs (1-based rank = position
            in list).  Duplicates are allowed; the first hit wins.
        relevant: Set of ground-truth IDs.

    Returns:
        Reciprocal rank in ``[0.0, 1.0]``.  ``0.0`` when no relevant
        ID appears in ``ranked_results`` (or ``ranked_results`` is
        empty / ``relevant`` is empty).

    Examples:
        >>> compute_mrr(["a", "b", "c"], {"b"})
        0.5
        >>> compute_mrr(["a", "b", "c"], {"d"})
        0.0
    """
    if not relevant or not ranked_results:
        return 0.0
    for index, item in enumerate(ranked_results, start=1):
        if item in relevant:
            return 1.0 / float(index)
    return 0.0


def compute_ndcg(
    ranked_results: Sequence[str],
    relevant: set[str],
    k: int = 10,
) -> float:
    """Normalized Discounted Cumulative Gain at rank ``k`` (binary relevance).

    Uses the standard log2 discount: ``discount = log2(rank + 1)``.

    Args:
        ranked_results: Ordered list of IDs.
        relevant: Set of ground-truth IDs.
        k: Cutoff for DCG and IDCG.  Values <= 0 raise ``ValueError``.

    Returns:
        nDCG in ``[0.0, 1.0]``.  ``0.0`` when the ideal DCG is zero
        (no relevant IDs) or ``ranked_results`` is empty.

    Raises:
        ValueError: ``k <= 0``.
    """
    if k <= 0:
        raise ValueError(f"k must be > 0; got {k}")
    if not ranked_results or not relevant:
        return 0.0

    # Truncate to the top-k.
    top_k = list(ranked_results[:k])
    dcg = _dcg(top_k, relevant, k)
    ideal = sorted(relevant)[:k]
    idcg = _dcg(ideal, relevant, k)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def _dcg(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """Compute DCG for binary relevance at cutoff ``k``.

    Args:
        ranked: Truncated ranked list.
        relevant: Set of relevant IDs.
        k: Cutoff (for the gain floor when fewer items than ``k``).

    Returns:
        DCG value ``>= 0.0``.
    """
    score = 0.0
    for index, item in enumerate(ranked, start=1):
        gain = 1.0 if item in relevant else 0.0
        # Use log2(index + 1) — same as the canonical nDCG formula.
        score += gain / math.log2(index + 1.0)
    return score


# ---------------------------------------------------------------------------
# Per-case metric record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluationMetrics:
    """Metric snapshot for a single case or aggregated run.

    Attributes:
        precision: Precision in ``[0.0, 1.0]``.
        recall: Recall in ``[0.0, 1.0]``.
        f1: Harmonic mean of precision and recall.
        mrr: Mean reciprocal rank of the first relevant hit.
        ndcg: nDCG@10 (or whichever ``k`` the harness used).
        total_cases: Number of cases in this snapshot (1 for a single
            case, ``len(per_case)`` for an aggregation).
        passed_cases: Number of cases that satisfied the pass criterion.
            For per-case records the field is ``1`` when ``f1 >= 1.0``
            else ``0``.  Aggregation sums these.
    """

    precision: float
    recall: float
    f1: float
    mrr: float
    ndcg: float
    total_cases: int
    passed_cases: int

    def __post_init__(self) -> None:
        for field_name in ("precision", "recall", "f1", "mrr", "ndcg"):
            value = getattr(self, field_name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(
                    f"{field_name} must be in [0.0, 1.0]; got {value}",
                )
        if self.total_cases < 0:
            raise ValueError(
                f"total_cases must be >= 0; got {self.total_cases}",
            )
        if self.passed_cases < 0:
            raise ValueError(
                f"passed_cases must be >= 0; got {self.passed_cases}",
            )
        if self.passed_cases > self.total_cases:
            raise ValueError(
                f"passed_cases ({self.passed_cases}) cannot exceed "
                f"total_cases ({self.total_cases})",
            )


# ---------------------------------------------------------------------------
# Per-case scoring helper
# ---------------------------------------------------------------------------


def score_case(
    *,
    retrieved_ids: Iterable[str],
    expected_recall_ids: Iterable[str],
    k: int = 10,
) -> EvaluationMetrics:
    """Score one case given the retrieved IDs and oracle IDs.

    The MRR / nDCG inputs are computed from a deterministic rank
    order.  Because the eval harness passes the IDs in their
    retrieved order (descending ``combined_score``), this function
    preserves that order and feeds it straight into the rank-aware
    metrics.

    Args:
        retrieved_ids: Iterable of retrieved IDs in ranked order.
        expected_recall_ids: Iterable of oracle IDs (unordered).
        k: Cutoff for nDCG (default 10).

    Returns:
        An :class:`EvaluationMetrics` with ``total_cases=1`` and
        ``passed_cases`` set to ``1`` iff ``f1 == 1.0``.
    """
    retrieved_ranked = list(retrieved_ids)
    retrieved_set = set(retrieved_ranked)
    expected_set = set(expected_recall_ids)

    precision = compute_precision(retrieved_set, expected_set)
    recall = compute_recall(retrieved_set, expected_set)
    f1 = compute_f1(precision, recall)
    mrr = compute_mrr(retrieved_ranked, expected_set)
    ndcg = compute_ndcg(retrieved_ranked, expected_set, k=k)
    passed = 1 if f1 >= 1.0 else 0
    return EvaluationMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        mrr=mrr,
        ndcg=ndcg,
        total_cases=1,
        passed_cases=passed,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate_metrics(
    per_case_metrics: Iterable[EvaluationMetrics],
) -> EvaluationMetrics:
    """Aggregate per-case metrics via arithmetic mean.

    Args:
        per_case_metrics: Iterable of :class:`EvaluationMetrics`
            records (one per golden case).  ``total_cases`` and
            ``passed_cases`` are summed; the remaining metrics are
            averaged.

    Returns:
        A single :class:`EvaluationMetrics` representing the run
        summary.  Empty input yields a record with all metrics
        at ``0.0`` and ``total_cases=0``.

    Examples:
        >>> from guinevere.knowledge_graph.eval.metrics import (
        ...     EvaluationMetrics, aggregate_metrics,
        ... )
        >>> m = EvaluationMetrics(0.8, 0.5, 0.62, 1.0, 0.85, 1, 1)
        >>> aggregate_metrics([m, m]).f1
        0.62
    """
    items = list(per_case_metrics)
    if not items:
        return EvaluationMetrics(
            precision=0.0,
            recall=0.0,
            f1=0.0,
            mrr=0.0,
            ndcg=0.0,
            total_cases=0,
            passed_cases=0,
        )

    total_cases = sum(m.total_cases for m in items)
    passed_cases = sum(m.passed_cases for m in items)
    count = len(items)

    return EvaluationMetrics(
        precision=sum(m.precision for m in items) / count,
        recall=sum(m.recall for m in items) / count,
        f1=sum(m.f1 for m in items) / count,
        mrr=sum(m.mrr for m in items) / count,
        ndcg=sum(m.ndcg for m in items) / count,
        total_cases=total_cases,
        passed_cases=passed_cases,
    )


# ---------------------------------------------------------------------------
# Delta helper for A/B reports
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricDelta:
    """Delta of one metric between two :class:`EvaluationMetrics`.

    Attributes:
        baseline: The baseline run value.
        with_kg: The KG-enabled run value.
        delta: ``with_kg - baseline`` (signed).
    """

    baseline: float
    with_kg: float
    delta: float


def compute_deltas(
    baseline: EvaluationMetrics,
    with_kg: EvaluationMetrics,
) -> dict[str, MetricDelta]:
    """Compute per-metric deltas between two runs.

    Args:
        baseline: The recall run without KG.
        with_kg: The recall run with KG.

    Returns:
        Mapping ``{"precision", "recall", "f1", "mrr", "ndcg"}`` →
        :class:`MetricDelta`.
    """
    fields = ("precision", "recall", "f1", "mrr", "ndcg")
    out: dict[str, MetricDelta] = {}
    for name in fields:
        before = getattr(baseline, name)
        after = getattr(with_kg, name)
        out[name] = MetricDelta(baseline=before, with_kg=after, delta=after - before)
    return out


__all__ = [
    "EvaluationMetrics",
    "MetricDelta",
    "compute_precision",
    "compute_recall",
    "compute_f1",
    "compute_mrr",
    "compute_ndcg",
    "score_case",
    "aggregate_metrics",
    "compute_deltas",
]
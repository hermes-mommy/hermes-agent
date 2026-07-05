"""KG evaluation submodule — recall-quality A/B harness (P16-005).

This package implements the Knowledge Graph recall evaluation
framework: a curated golden test set, the metric primitives
(precision, recall, F1, MRR, nDCG), an async runner that drives the
production :func:`guinevere.memory.read_pipeline.recall_memories` with and
without the KG signal, and a markdown report generator.

Public surface
--------------

* :class:`GoldenCase` / :class:`GoldenTestSet` — labelled queries.
* :func:`create_sample_golden_set` — 10-case deterministic fixture.
* :class:`EvaluationMetrics` / :class:`MetricDelta` — metric records.
* :func:`compute_precision` / :func:`compute_recall` / :func:`compute_f1`
  / :func:`compute_mrr` / :func:`compute_ndcg` — pure metric primitives.
* :func:`aggregate_metrics` — arithmetic-mean aggregation.
* :func:`compute_deltas` — per-metric delta between two runs.
* :class:`KGRecallEvaluator` — async A/B harness.
* :class:`ABComparisonResult` / :class:`PerCaseComparisonResult` —
  structured outcomes.
* :func:`derive_verdict` — F1-delta → verdict label.
* :func:`generate_evaluation_report` — markdown report renderer.
* :func:`attach_golden_set` / :func:`detach_golden_set` — golden-set
  attachment for report rendering.

CLI usage
---------

::

    python -m guinevere.knowledge_graph.eval \
        --golden guinevere/knowledge_graph/eval/golden_set_sample.json \
        --out reports/p16-005.md
"""
from __future__ import annotations

from guinevere.knowledge_graph.eval.golden_set import (
    GOLDEN_SET_JSON_SCHEMA,
    GOLDEN_SET_SCHEMA_VERSION,
    VALID_DIFFICULTIES,
    GoldenCase,
    GoldenSetValidationError,
    GoldenTestSet,
    create_sample_golden_set,
)
from guinevere.knowledge_graph.eval.metrics import (
    EvaluationMetrics,
    MetricDelta,
    aggregate_metrics,
    compute_deltas,
    compute_f1,
    compute_mrr,
    compute_ndcg,
    compute_precision,
    compute_recall,
    score_case,
)
from guinevere.knowledge_graph.eval.report import (
    attach_golden_set,
    detach_golden_set,
    generate_evaluation_report,
)
from guinevere.knowledge_graph.eval.runner import (
    ABComparisonResult,
    KGRecallEvaluator,
    PerCaseComparisonResult,
    SessionFactory,
    THRESHOLD_MARGINAL,
    THRESHOLD_SIGNIFICANT,
    VERDICT_MARGINAL_IMPROVEMENT,
    VERDICT_NO_CHANGE,
    VERDICT_REGRESSION,
    VERDICT_SIGNIFICANT_IMPROVEMENT,
    derive_verdict,
)

__all__ = [
    # Golden set
    "GoldenCase",
    "GoldenTestSet",
    "GoldenSetValidationError",
    "create_sample_golden_set",
    "GOLDEN_SET_SCHEMA_VERSION",
    "GOLDEN_SET_JSON_SCHEMA",
    "VALID_DIFFICULTIES",
    # Metrics
    "EvaluationMetrics",
    "MetricDelta",
    "compute_precision",
    "compute_recall",
    "compute_f1",
    "compute_mrr",
    "compute_ndcg",
    "aggregate_metrics",
    "compute_deltas",
    "score_case",
    # Runner
    "KGRecallEvaluator",
    "ABComparisonResult",
    "PerCaseComparisonResult",
    "SessionFactory",
    "derive_verdict",
    "VERDICT_SIGNIFICANT_IMPROVEMENT",
    "VERDICT_MARGINAL_IMPROVEMENT",
    "VERDICT_NO_CHANGE",
    "VERDICT_REGRESSION",
    "THRESHOLD_SIGNIFICANT",
    "THRESHOLD_MARGINAL",
    # Report
    "generate_evaluation_report",
    "attach_golden_set",
    "detach_golden_set",
]
"""Markdown report renderer for the KG recall A/B harness (P16-005).

Takes an :class:`ABComparisonResult` and emits a human-readable
markdown document suitable for pasting into a PR description or
attaching to an evidence record.

Report sections
---------------

1. **Summary table** — headline metrics for both arms and deltas.
2. **Per-category breakdown** — aggregated metrics bucketed by
   ``GoldenCase.category``.
3. **Per-difficulty breakdown** — aggregated metrics bucketed by
   ``GoldenCase.difficulty``.
4. **Worst cases** — bottom-N cases by ``delta_f1`` (i.e. where
   the KG run underperformed the baseline).
5. **Best cases** — top-N cases by ``delta_f1``.
6. **Recommendations** — verdict-driven next-action guidance.

The renderer is pure (no I/O, no globals) so it can be unit-tested
without a database.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from guinevere.knowledge_graph.eval.golden_set import GoldenCase, GoldenTestSet
from guinevere.knowledge_graph.eval.metrics import (
    EvaluationMetrics,
    aggregate_metrics,
)
from guinevere.knowledge_graph.eval.runner import (
    ABComparisonResult,
    PerCaseComparisonResult,
    VERDICT_MARGINAL_IMPROVEMENT,
    VERDICT_NO_CHANGE,
    VERDICT_REGRESSION,
    VERDICT_SIGNIFICANT_IMPROVEMENT,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


#: Number of cases listed under "worst" / "best" sections.
WORST_CASES_LIMIT: int = 5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _BucketStats:
    """Per-bucket aggregate used to render category/difficulty tables."""

    key: str
    count: int
    baseline: EvaluationMetrics
    with_kg: EvaluationMetrics
    delta_f1: float


def _bucket_by(
    cases: Sequence[GoldenCase],
    per_case: Sequence[PerCaseComparisonResult],
    attribute: str,
) -> list[_BucketStats]:
    """Aggregate per-case metrics grouped by ``attribute``.

    Args:
        cases: The full golden set (provides the bucket key).
        per_case: One :class:`PerCaseComparisonResult` per case.
        attribute: ``"category"`` or ``"difficulty"``.

    Returns:
        Sorted list of :class:`_BucketStats` (by key ascending).
    """
    if len(cases) != len(per_case):
        raise ValueError(
            f"cases/per_case length mismatch: {len(cases)} vs {len(per_case)}",
        )
    groups: dict[str, list[tuple[GoldenCase, PerCaseComparisonResult]]] = (
        defaultdict(list)
    )
    for case, result in zip(cases, per_case):
        key = getattr(case, attribute)
        groups[key].append((case, result))

    out: list[_BucketStats] = []
    for key in sorted(groups):
        entries = groups[key]
        baseline_metrics = aggregate_metrics(
            [result.baseline for _, result in entries],
        )
        kg_metrics = aggregate_metrics(
            [result.with_kg for _, result in entries],
        )
        out.append(
            _BucketStats(
                key=key,
                count=len(entries),
                baseline=baseline_metrics,
                with_kg=kg_metrics,
                delta_f1=kg_metrics.f1 - baseline_metrics.f1,
            ),
        )
    return out


def _worst_cases(
    per_case: Sequence[PerCaseComparisonResult],
    limit: int = WORST_CASES_LIMIT,
) -> list[PerCaseComparisonResult]:
    """Bottom-``limit`` cases by ``delta_f1`` ascending."""
    return sorted(per_case, key=lambda r: r.delta_f1)[:limit]


def _best_cases(
    per_case: Sequence[PerCaseComparisonResult],
    limit: int = WORST_CASES_LIMIT,
) -> list[PerCaseComparisonResult]:
    """Top-``limit`` cases by ``delta_f1`` descending."""
    return sorted(per_case, key=lambda r: r.delta_f1, reverse=True)[:limit]


def _format_metric(value: float, width: int = 6) -> str:
    """Render a metric value as a right-aligned percentage string.

    Args:
        value: A float in ``[0.0, 1.0]``.
        width: Minimum width of the resulting string.

    Returns:
        Right-aligned ``"xx.x%"`` string.
    """
    pct = value * 100.0
    return f"{pct:>{width - 1}.1f}%"


def _format_delta(value: float, width: int = 8) -> str:
    """Render a signed delta with sign indicator and color hint.

    Args:
        value: Signed delta (typically in ``[-1.0, 1.0]``).
        width: Minimum width of the resulting string.

    Returns:
        ``"+xx.x%"`` or ``"-xx.x%"`` style string, right-aligned.
    """
    pct = value * 100.0
    sign = "+" if pct >= 0 else "-"
    return f"{sign}{abs(pct):>{width - 1}.1f}%"


def _verdict_recommendations(verdict: str) -> list[str]:
    """Render recommendations keyed off the verdict label."""
    if verdict == VERDICT_SIGNIFICANT_IMPROVEMENT:
        return [
            "Keep the KG signal enabled in production (4th RRF weight per PRD v2.2).",
            "Lock the gain in CI — add this run as a regression baseline.",
            "Investigate the worst cases; the gain may be uneven across categories.",
        ]
    if verdict == VERDICT_MARGINAL_IMPROVEMENT:
        return [
            "KG signal helps marginally; tune weights or seed resolution before promoting.",
            "Re-run with a larger golden set to confirm the direction holds.",
            "Audit the cases where KG did not contribute — likely seed-resolution gaps.",
        ]
    if verdict == VERDICT_REGRESSION:
        return [
            "REGRESSION DETECTED — keep KG disabled until the cause is found.",
            "Compare per-case results; identify which category is hurt the most.",
            "Check that the KG signal is not duplicating vector/FTS hits at the cost of noise.",
        ]
    # NO_CHANGE
    return [
        "No statistically meaningful change.  Either the KG signal is too weak or the cases are KG-agnostic.",
        "Expand the golden set with cases that require multi-hop graph reasoning.",
        "Consider raising KG_WEIGHT or improving PPR seed resolution before the next run.",
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_evaluation_report(result: ABComparisonResult) -> str:
    """Render an A/B comparison as a markdown report.

    Args:
        result: The output of
            :meth:`KGRecallEvaluator.run_ab_comparison`.

    Returns:
        A markdown-formatted report string.  Sections are always
        emitted in the same order to keep diffs readable.
    """
    parts: list[str] = []
    parts.append("# KG Recall Evaluation Report")
    parts.append("")
    parts.append(f"**Verdict:** `{result.verdict}`")
    parts.append("")
    parts.extend(_render_summary_table(result))
    parts.append("")
    parts.extend(_render_per_category_breakdown(result))
    parts.append("")
    parts.extend(_render_per_difficulty_breakdown(result))
    parts.append("")
    parts.extend(_render_best_and_worst(result))
    parts.append("")
    parts.extend(_render_recommendations(result))
    parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_summary_table(result: ABComparisonResult) -> list[str]:
    """Render the headline summary table."""
    b = result.baseline_metrics
    k = result.kg_metrics
    rows: list[str] = []
    rows.append("## Summary")
    rows.append("")
    rows.append("| Metric    | Baseline | With KG  | Delta     |")
    rows.append("|-----------|----------|----------|-----------|")
    rows.append(
        f"| Precision | {_format_metric(b.precision)} | "
        f"{_format_metric(k.precision)} | "
        f"{_format_delta(result.delta_precision)} |",
    )
    rows.append(
        f"| Recall    | {_format_metric(b.recall)} | "
        f"{_format_metric(k.recall)} | "
        f"{_format_delta(result.delta_recall)} |",
    )
    rows.append(
        f"| F1        | {_format_metric(b.f1)} | "
        f"{_format_metric(k.f1)} | "
        f"{_format_delta(result.delta_f1)} |",
    )
    rows.append(
        f"| MRR       | {_format_metric(b.mrr)} | "
        f"{_format_metric(k.mrr)} | "
        f"{_format_delta(result.delta_mrr)} |",
    )
    rows.append(
        f"| nDCG@10   | {_format_metric(b.ndcg)} | "
        f"{_format_metric(k.ndcg)} | "
        f"{_format_delta(result.delta_ndcg)} |",
    )
    rows.append(
        f"| Cases     | {b.total_cases:>8d} | "
        f"{k.total_cases:>8d} | "
        f"           |",
    )
    rows.append(
        f"| Passed    | {b.passed_cases:>8d} | "
        f"{k.passed_cases:>8d} | "
        f"           |",
    )
    return rows


def _render_per_category_breakdown(result: ABComparisonResult) -> list[str]:
    """Render the per-category breakdown table."""
    return _render_bucket_breakdown(
        result=result,
        heading="Per-Category Breakdown",
        attribute="category",
    )


def _render_per_difficulty_breakdown(result: ABComparisonResult) -> list[str]:
    """Render the per-difficulty breakdown table."""
    return _render_bucket_breakdown(
        result=result,
        heading="Per-Difficulty Breakdown",
        attribute="difficulty",
    )


def _render_bucket_breakdown(
    *,
    result: ABComparisonResult,
    heading: str,
    attribute: str,
) -> list[str]:
    """Render one bucket breakdown section (category or difficulty).

    Because the breakdown needs both the per-case data and the
    golden-set (for the bucket key), the runner passes both.  When
    the golden set is not available (e.g. dry-run call sites), the
    section renders an empty table with an explanatory note.
    """
    rows: list[str] = []
    rows.append(f"## {heading}")
    rows.append("")
    golden_set = _resolve_golden_set(result)
    if golden_set is None:
        rows.append(
            "_Golden set not attached to the result — bucket breakdown unavailable._",
        )
        return rows

    cases = list(golden_set)
    per_case = list(result.per_case_results)
    if not per_case:
        rows.append("_No per-case data recorded._")
        return rows

    buckets = _bucket_by(cases, per_case, attribute)
    rows.append(f"| {attribute.title():<10} | Count | Precision | Recall | F1 | MRR | nDCG@10 | ΔF1 |")
    rows.append("|------------|-------|-----------|--------|----|----|---------|------|")
    for bucket in buckets:
        rows.append(
            f"| {bucket.key:<10} | {bucket.count:>5d} | "
            f"{_format_metric(bucket.with_kg.precision)} | "
            f"{_format_metric(bucket.with_kg.recall)} | "
            f"{_format_metric(bucket.with_kg.f1)} | "
            f"{_format_metric(bucket.with_kg.mrr)} | "
            f"{_format_metric(bucket.with_kg.ndcg)} | "
            f"{_format_delta(bucket.delta_f1)} |",
        )
    return rows


def _render_best_and_worst(result: ABComparisonResult) -> list[str]:
    """Render the best- and worst-case sections."""
    rows: list[str] = []
    rows.append("## Worst Cases (largest negative ΔF1)")
    rows.append("")
    if not result.per_case_results:
        rows.append("_No per-case data recorded._")
    else:
        rows.append("| Case ID  | Query | Baseline F1 | With-KG F1 | ΔF1 |")
        rows.append("|----------|-------|-------------|------------|-----|")
        for entry in _worst_cases(result.per_case_results):
            _append_case_row(rows, entry)
    rows.append("")
    rows.append("## Best Cases (largest positive ΔF1)")
    rows.append("")
    if not result.per_case_results:
        rows.append("_No per-case data recorded._")
    else:
        rows.append("| Case ID  | Query | Baseline F1 | With-KG F1 | ΔF1 |")
        rows.append("|----------|-------|-------------|------------|-----|")
        for entry in _best_cases(result.per_case_results):
            _append_case_row(rows, entry)
    return rows


def _append_case_row(
    rows: list[str],
    entry: PerCaseComparisonResult,
) -> None:
    """Append one markdown row for a case entry, truncating the query."""
    query = entry.query
    if len(query) > 60:
        query = query[:57] + "..."
    query = query.replace("|", "\\|")  # escape pipe for table safety
    rows.append(
        f"| {entry.case_id} | {query} | "
        f"{_format_metric(entry.baseline.f1)} | "
        f"{_format_metric(entry.with_kg.f1)} | "
        f"{_format_delta(entry.delta_f1)} |",
    )


def _render_recommendations(result: ABComparisonResult) -> list[str]:
    """Render the verdict-driven recommendations section."""
    rows: list[str] = []
    rows.append("## Recommendations")
    rows.append("")
    for line in _verdict_recommendations(result.verdict):
        rows.append(f"- {line}")
    return rows


def _resolve_golden_set(result: ABComparisonResult) -> GoldenTestSet | None:
    """Attach a golden set to the result if one was provided.

    The runner does not retain a reference to the golden set in the
    result dataclass (kept minimal per spec).  When the caller passes
    a result that was built via :meth:`KGRecallEvaluator.run_ab_comparison`
    we recover the golden set from the evaluator instance via
    :func:`attach_golden_set` (called eagerly after construction).

    Returns:
        The attached :class:`GoldenTestSet` or ``None`` if the
        caller did not attach one.
    """
    return _ATTACHED_GOLDEN_SETS.get(id(result))


# ---------------------------------------------------------------------------
# Golden-set attachment helper
# ---------------------------------------------------------------------------


#: Mapping from ``id(result)`` → attached golden set.  Populated by
#: :func:`attach_golden_set` and read by :func:`_resolve_golden_set`.
#: This indirection keeps the :class:`ABComparisonResult` dataclass
#: frozen and spec-conformant.
_ATTACHED_GOLDEN_SETS: dict[int, GoldenTestSet] = {}


def attach_golden_set(
    result: ABComparisonResult,
    golden_set: GoldenTestSet,
) -> None:
    """Attach a golden set to an A/B result for report rendering.

    The :class:`ABComparisonResult` dataclass is frozen per spec, so
    we cannot store the golden set as a field.  Instead the report
    looks up the attached set by object id.

    Args:
        result: The A/B result produced by the runner.
        golden_set: The golden set the result was computed against.

    Returns:
        None.
    """
    _ATTACHED_GOLDEN_SETS[id(result)] = golden_set


def detach_golden_set(result: ABComparisonResult) -> None:
    """Remove the golden-set attachment for ``result``.

    Useful for tests that exhaust the attachment dict.
    """
    _ATTACHED_GOLDEN_SETS.pop(id(result), None)


__all__ = [
    "generate_evaluation_report",
    "attach_golden_set",
    "detach_golden_set",
]
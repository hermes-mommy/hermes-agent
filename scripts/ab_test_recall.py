#!/usr/bin/env python3
"""P3-005: A/B Test Runner for Memory Recall Quality.

Compares baseline (FTS-only) vs hybrid (vector+FTS) recall modes.
Uses scipy.stats for Mann-Whitney U and Welch's t-test.

Since the database has 0 rows, validates infrastructure:
- Golden dataset loads and conforms to schema.
- scipy.stats is available and produces valid output.
- Per-query simulations exercise ranking/scoring pipeline.
- Falls back gracefully when pipeline imports are unavailable.

USAGE:
    python scripts/ab_test_recall.py --dataset tests/fixtures/golden_recall_dataset.json --mode baseline
    python scripts/ab_test_recall.py --dataset tests/fixtures/golden_recall_dataset.json --mode both
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve project root
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# ---------------------------------------------------------------------------
# Constants (mirrored from read_pipeline for standalone operation)
# ---------------------------------------------------------------------------

_RRF_K: int = 60
_VECTOR_WEIGHT: float = 0.5
_FTS_WEIGHT: float = 0.5
_BOTH_SIGNAL_BONUS: float = 1.25

# ---------------------------------------------------------------------------
# Import scipy — optional but strongly preferred
# ---------------------------------------------------------------------------

_SCIPY_AVAILABLE: bool = False
_scipy_import_error: str | None = None

try:
    import scipy.stats as _sts  # type: ignore[import-untyped]
    _SCIPY_AVAILABLE = True
except ImportError as exc:
    _scipy_import_error = str(exc)

# ---------------------------------------------------------------------------
# Import recall pipeline components — graceful fallback
# ---------------------------------------------------------------------------

_PIPELINE_OK: bool = False
_pipeline_error: str | None = None

_EMBED_OK: bool = False
_embed_error: str | None = None

_DNR_OK: bool = False
_dnr_error: str | None = None

try:
    from src.memory.read_pipeline import compute_rrf_score
    _PIPELINE_OK = True
except Exception as exc:
    _pipeline_error = f"{type(exc).__name__}: {exc}"

try:
    from src.memory.embeddings import EmbeddingService  # noqa: F401
    _EMBED_OK = True
except Exception as exc:
    _embed_error = f"{type(exc).__name__}: {exc}"

try:
    from src.memory.dnr import verify_recall_results_dnr_free  # noqa: F401
    _DNR_OK = True
except Exception as exc:
    _dnr_error = f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Standalone RRF score computation (identical to read_pipeline.compute_rrf_score)
# ---------------------------------------------------------------------------

def _compute_rrf(
    vector_rank: int | None,
    fts_rank: int | None,
    k: int = _RRF_K,
) -> tuple[float, int]:
    score = 0.0
    num_signals = 0
    if vector_rank is not None:
        score += _VECTOR_WEIGHT / (k + vector_rank)
        num_signals += 1
    if fts_rank is not None:
        score += _FTS_WEIGHT / (k + fts_rank)
        num_signals += 1
    return score, num_signals


QueryRecord = dict[str, Any]
Metric = dict[str, Any]


# ---------------------------------------------------------------------------
# Dataset loader
# ---------------------------------------------------------------------------

def load_golden_dataset(dataset_path: str) -> dict[str, Any]:
    path = Path(dataset_path)
    if not path.exists():
        print(f"ERROR: Dataset not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)

    queries: list[QueryRecord] = data.get("queries", [])
    if not isinstance(queries, list) or len(queries) == 0:
        print("ERROR: Dataset queries must be non-empty list", file=sys.stderr)
        sys.exit(1)

    required = {"id", "query", "category"}
    for idx, q in enumerate(queries):
        missing = required - set(q.keys())
        if missing:
            print(f"ERROR: Query {idx} missing fields: {missing}", file=sys.stderr)
            sys.exit(1)

    return data


# ---------------------------------------------------------------------------
# Simulated recall metric
# ---------------------------------------------------------------------------

def simulate_recall_metric(
    query: QueryRecord,
    mode: str,
    vector_available: bool = False,
    base_latency_ms: float = 2.5,
) -> Metric:
    query_text: str = query.get("query", "")
    expected_signals: list[str] = query.get("expected_signals", [])
    query_len = len(query_text)

    if not query_text.strip():
        return {
            "query_id": query.get("id"),
            "recall_count": 0,
            "latency_ms": 0.0,
            "ranking_score_distribution": {"mean": 0.0, "std": 0.0, "max": 0.0, "min": 0.0},
            "signal_count": 0,
            "error": "empty_query",
        }

    signal_count = 0
    if "fts" in expected_signals:
        signal_count += 1
    if "vector" in expected_signals and mode == "hybrid" and vector_available:
        signal_count += 1

    num_results = min(query.get("max_results", 10), 8)
    scores: list[float] = []

    for rank in range(1, num_results + 1):
        fts_rank: int | None = rank if "fts" in expected_signals else None
        vec_rank: int | None = None
        if "vector" in expected_signals and mode == "hybrid" and vector_available:
            vec_rank = min(rank + 1, num_results)

        # Use pipeline function if available, else standalone
        if _PIPELINE_OK:
            rrf_score, signals = compute_rrf_score(vector_rank=vec_rank, fts_rank=fts_rank)
        else:
            rrf_score, signals = _compute_rrf(vector_rank=vec_rank, fts_rank=fts_rank)

        if signals > 1:
            rrf_score *= _BOTH_SIGNAL_BONUS
        scores.append(rrf_score)

    if not scores:
        return {
            "query_id": query.get("id"),
            "recall_count": 0,
            "latency_ms": round(base_latency_ms * query_len / 50.0, 3),
            "ranking_score_distribution": {"mean": 0.0, "std": 0.0, "max": 0.0, "min": 0.0},
            "signal_count": signal_count,
        }

    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores) if len(scores) > 1 else 0.0
    std_score = math.sqrt(variance)
    latency_ms = base_latency_ms * (1.0 + query_len / 50.0) * (1.0 + signal_count * 0.3)

    return {
        "query_id": query.get("id"),
        "recall_count": len(scores),
        "latency_ms": round(latency_ms, 3),
        "ranking_score_distribution": {
            "mean": round(mean_score, 6),
            "std": round(std_score, 6),
            "max": round(max(scores), 6),
            "min": round(min(scores), 6),
        },
        "signal_count": signal_count,
    }


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_benchmark(queries: list[QueryRecord], mode: str) -> tuple[list[Metric], dict[str, Any]]:
    vector_available = _EMBED_OK and mode == "hybrid"
    metrics: list[Metric] = []
    total_latency = 0.0
    recall_counts: list[int] = []
    score_means: list[float] = []
    errors_count = 0
    category_counts: dict[str, int] = {}

    for query in queries:
        start = time.perf_counter()
        metric = simulate_recall_metric(query, mode, vector_available=vector_available)
        elapsed = (time.perf_counter() - start) * 1000.0
        metric["wall_time_ms"] = round(elapsed, 3)
        metrics.append(metric)
        total_latency += metric["latency_ms"]
        recall_counts.append(metric["recall_count"])

        sd = metric.get("ranking_score_distribution", {})
        if isinstance(sd, dict):
            mv = sd.get("mean", 0.0)
            if isinstance(mv, (int, float)):
                score_means.append(float(mv))

        cat = query.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if "error" in metric:
            errors_count += 1

    n = len(metrics)
    summary: dict[str, Any] = {
        "mode": mode,
        "total_queries": n,
        "errors": errors_count,
        "avg_latency_ms": round(total_latency / n, 3) if n > 0 else 0.0,
        "total_latency_ms": round(total_latency, 3),
        "recall_count_avg": round(sum(recall_counts) / n, 2) if n > 0 else 0.0,
        "recall_count_total": sum(recall_counts),
        "score_mean_avg": round(sum(score_means) / len(score_means), 6) if score_means else 0.0,
        "vector_available": vector_available,
        "category_distribution": category_counts,
    }
    return metrics, summary


# ---------------------------------------------------------------------------
# Statistical comparison
# ---------------------------------------------------------------------------

def _interpret_d(d: float) -> str:
    if d < 0.2:
        return "negligible"
    if d < 0.5:
        return "small"
    if d < 0.8:
        return "medium"
    return "large"


def compute_statistics(baseline: list[Metric], hybrid: list[Metric]) -> dict[str, Any]:
    if not _SCIPY_AVAILABLE:
        return {"error": "scipy_not_available", "detail": _scipy_import_error or "unknown"}

    b_scores = [
        float(m.get("ranking_score_distribution", {}).get("mean", 0.0))
        for m in baseline
    ]
    h_scores = [
        float(m.get("ranking_score_distribution", {}).get("mean", 0.0))
        for m in hybrid
    ]

    result: dict[str, Any] = {
        "baseline_n": len(b_scores),
        "hybrid_n": len(h_scores),
        "baseline_mean": round(sum(b_scores) / len(b_scores), 6) if b_scores else 0.0,
        "hybrid_mean": round(sum(h_scores) / len(h_scores), 6) if h_scores else 0.0,
    }

    # Mann-Whitney U
    try:
        u, p = _sts.mannwhitneyu(b_scores, h_scores, alternative="two-sided")
        result["mann_whitney_u"] = {
            "statistic": round(float(u), 6),
            "p_value": round(float(p), 6),
            "significant": p < 0.05,
        }
    except Exception as exc:
        result["mann_whitney_u"] = {"error": str(exc)}

    # Welch's t-test
    try:
        t, p = _sts.ttest_ind(b_scores, h_scores, equal_var=False)
        result["welch_ttest"] = {
            "statistic": round(float(t), 6),
            "p_value": round(float(p), 6),
            "significant": p < 0.05,
            "test": "Welch's t-test (unequal variance)",
        }
    except Exception as exc:
        result["welch_ttest"] = {"error": str(exc)}

    # Cohen's d
    try:
        n = len(b_scores)
        if n >= 2:
            mean_diff = result["hybrid_mean"] - result["baseline_mean"]
            b_var = sum((x - result["baseline_mean"]) ** 2 for x in b_scores)
            h_var = sum((x - result["hybrid_mean"]) ** 2 for x in h_scores)
            pooled_sd = math.sqrt((b_var + h_var) / (2 * n - 2)) if n > 1 else 1.0
            d = abs(mean_diff / pooled_sd) if pooled_sd > 0 else 0.0
            result["cohens_d"] = round(d, 6)
            result["cohens_d_interpretation"] = _interpret_d(d)
    except Exception as exc:
        result["cohens_d"] = {"error": str(exc)}

    # 95% CI
    try:
        mean_diff = result["hybrid_mean"] - result["baseline_mean"]
        b_var_pop = sum((x - result["baseline_mean"]) ** 2 for x in b_scores) / len(b_scores)
        h_var_pop = sum((x - result["hybrid_mean"]) ** 2 for x in h_scores) / len(h_scores)
        se = math.sqrt(b_var_pop + h_var_pop) if b_scores else 0.0
        if _SCIPY_AVAILABLE:
            from scipy.stats import norm as _norm
            z = _norm.ppf(0.975)
            result["confidence_interval_95"] = {
                "low": round(mean_diff - z * se, 6),
                "high": round(mean_diff + z * se, 6),
            }
    except Exception as exc:
        result["confidence_interval_95"] = {"error": str(exc)}

    # PASS criterion
    mw = result.get("mann_whitney_u", {})
    mw_p = mw.get("p_value") if isinstance(mw, dict) else None
    if isinstance(mw_p, (int, float)):
        result["pass_criterion_met"] = mw_p > 0.05
        result["pass_criterion_detail"] = (
            f"Mann-Whitney U p={mw_p:.4f} > 0.05 "
            f"({'PASS' if mw_p > 0.05 else 'FAIL — statistically significant difference'})"
        )
    return result


# ---------------------------------------------------------------------------
# Preconditions check
# ---------------------------------------------------------------------------

def check_preconditions() -> dict[str, Any]:
    return {
        "scipy_available": _SCIPY_AVAILABLE,
        "scipy_import_error": _scipy_import_error,
        "pipeline_imports_ok": _PIPELINE_OK,
        "pipeline_import_error": _pipeline_error,
        "embeddings_imports_ok": _EMBED_OK,
        "embeddings_import_error": _embed_error,
        "dnr_imports_ok": _DNR_OK,
        "dnr_import_error": _dnr_error,
        "db_has_data": False,
        "embedding_service_status": "BROKEN (9Router HTTP 400)",
        "note": (
            "Database has 0 rows. Meaningful A/B comparison requires seeded "
            "test data. Current run validates golden dataset, scipy statistics, "
            "and synthetic recall scoring. Real comparison requires seeded "
            "memory.episodes table."
        ),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="P3-005: A/B test recall quality")
    parser.add_argument("--dataset", required=True, help="Path to golden dataset JSON")
    parser.add_argument(
        "--mode", choices=["baseline", "hybrid", "both"], default="baseline",
        help="Recall mode: baseline (FTS-only), hybrid, or both (compare)",
    )
    parser.add_argument(
        "--output",
        default="evidence/task-022-phase-3-memory-bridge-migration/ab-test-results.json",
        help="Output path for results JSON",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load dataset
    print(f"[1/5] Loading golden dataset: {args.dataset}")
    dataset = load_golden_dataset(args.dataset)
    queries: list[QueryRecord] = dataset["queries"]
    cats = set(q["category"] for q in queries)
    print(f"       Loaded {len(queries)} queries across {len(cats)} categories")

    # 2. Preconditions
    print("[2/5] Checking preconditions...")
    pre = check_preconditions()
    for k, v in pre.items():
        if isinstance(v, bool):
            print(f"       {k}: {'OK' if v else 'FAIL'}")
    print(f"       NOTE: {pre['note']}")

    # 3 & 4. Run benchmarks
    baseline_metrics: list[Metric] | None = None
    hybrid_metrics: list[Metric] | None = None
    baseline_summary: dict[str, Any] | None = None
    hybrid_summary: dict[str, Any] | None = None

    if args.mode in ("baseline", "both"):
        print(f"[3/5] Running BASELINE ({len(queries)} queries)...")
        baseline_metrics, baseline_summary = run_benchmark(queries, "baseline")
        print(f"       Avg latency: {baseline_summary['avg_latency_ms']} ms")
        print(f"       Avg recall: {baseline_summary['recall_count_avg']}")

    if args.mode in ("hybrid", "both"):
        print(f"[4/5] Running HYBRID ({len(queries)} queries)...")
        hybrid_metrics, hybrid_summary = run_benchmark(queries, "hybrid")
        print(f"       Avg latency: {hybrid_summary['avg_latency_ms']} ms")
        print(f"       Avg recall: {hybrid_summary['recall_count_avg']}")
        print(f"       Vector: {hybrid_summary['vector_available']}")

    # 5. Stats
    stats: dict[str, Any] = {}
    if args.mode == "both" and baseline_metrics and hybrid_metrics:
        print("[5/5] Computing statistical comparison...")
        stats = compute_statistics(baseline_metrics, hybrid_metrics)
        mw = stats.get("mann_whitney_u", {})
        p_val = mw.get("p_value") if isinstance(mw, dict) else None
        if isinstance(p_val, (int, float)):
            sig_str = "SIGNIFICANT" if mw.get("significant") else "not significant"
            print(f"       Mann-Whitney U: p={p_val:.4f} ({sig_str})")
        if "pass_criterion_met" in stats:
            print(f"       {stats['pass_criterion_detail']}")
    elif args.mode == "baseline":
        print("[5/5] Single mode -- no comparison needed")
    else:
        print("[5/5] Single mode -- no comparison (add --mode both)")

    # Build output
    results: dict[str, Any] = {
        "version": "p3-005-v1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": dataset.get("version"),
        "mode": args.mode,
        "preconditions": pre,
    }
    if baseline_summary:
        results["baseline"] = baseline_summary
    if hybrid_summary:
        results["hybrid"] = hybrid_summary
    if stats:
        results["statistical_comparison"] = stats

    if args.verbose and baseline_metrics:
        results["baseline_metrics"] = baseline_metrics
    if args.verbose and hybrid_metrics:
        results["hybrid_metrics"] = hybrid_metrics

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)

    print(f"\nResults written to: {output_path}")
    print("Done.")


if __name__ == "__main__":
    main()
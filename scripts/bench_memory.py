#!/usr/bin/env python3
"""P3-019: Memory pipeline performance benchmark.

Measures p95 latency for:
- Vector search (ADR-009 target: < 2s)
- FTS search (ADR-009 target: < 500ms)
- Hybrid search (ADR-009 target: < 3s)
- Episode write (store_episode latency)

Modes:
- --dry-run: Synthetic timing with no DB (measures pipeline overhead only)
- --database-url URL: Live benchmark against real PostgreSQL+pgvector

Usage:
    python scripts/bench_memory.py --dry-run
    python scripts/bench_memory.py --database-url postgresql+asyncpg://...
"""

from __future__ import annotations

import argparse
import asyncio
import math
import random
import re
import sys
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import TypeAlias, cast

# ---------------------------------------------------------------------------
# ADR-009 Performance Targets
# ---------------------------------------------------------------------------

TARGET_VECTOR_P95_MS: float = 2000.0    # Vector search p95 < 2s
TARGET_FTS_P95_MS: float = 500.0        # FTS search p95 < 500ms
TARGET_HYBRID_P95_MS: float = 3000.0    # Hybrid search p95 < 3s
TARGET_WRITE_P95_MS: float = 5000.0     # Write p95 < 5s (generous for embedding)

# ---------------------------------------------------------------------------
# Embedding dimension (text-embedding-3-small via 9Router)
# ---------------------------------------------------------------------------

EMBEDDING_DIM: int = 1536

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

LatencyList: TypeAlias = list[float]
BenchmarkFn: TypeAlias = Callable[[], Coroutine[object, object, None]]


from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkArgs:
    """Typed representation of parsed CLI arguments."""

    dry_run: bool
    database_url: str | None
    iterations: int
    warmup: int

    @classmethod
    def from_namespace(cls, ns: argparse.Namespace) -> BenchmarkArgs:
        """Build from argparse.Namespace with explicit type coercion."""
        return cls(
            dry_run=bool(ns.dry_run),
            database_url=str(ns.database_url) if ns.database_url else None,
            iterations=int(ns.iterations),
            warmup=int(ns.warmup),
        )

# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def compute_percentile(latencies: list[float], percentile: float) -> float:
    """Compute the given percentile from a sorted list of latencies in ms."""
    if not latencies:
        return 0.0
    sorted_lat = sorted(latencies)
    idx = int(len(sorted_lat) * percentile / 100.0)
    idx = min(idx, len(sorted_lat) - 1)
    return sorted_lat[idx]


def compute_stats(latencies: list[float]) -> dict[str, float]:
    """Compute p50, p90, p95, p99 from a list of latency values in ms."""
    return {
        "p50": compute_percentile(latencies, 50.0),
        "p90": compute_percentile(latencies, 90.0),
        "p95": compute_percentile(latencies, 95.0),
        "p99": compute_percentile(latencies, 99.0),
    }


# ---------------------------------------------------------------------------
# Synthetic data generators (dry-run mode)
# ---------------------------------------------------------------------------


def generate_random_vector(dim: int = EMBEDDING_DIM) -> list[float]:
    """Generate a random unit vector for dry-run simulation."""
    raw = [random.gauss(0.0, 1.0) for _ in range(dim)]
    magnitude = math.sqrt(sum(x * x for x in raw))
    if magnitude < 1e-12:
        return [0.0] * dim
    return [x / magnitude for x in raw]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a < 1e-12 or mag_b < 1e-12:
        return 0.0
    return dot / (mag_a * mag_b)


# Pre-generate synthetic corpus for dry-run
_SYNTHETIC_CORPUS_SIZE: int = 200
_synthetic_corpus: list[tuple[str, list[float]]] = []


def _ensure_corpus() -> list[tuple[str, list[float]]]:
    """Lazily build the synthetic corpus once."""
    global _synthetic_corpus
    if not _synthetic_corpus:
        words = [
            "memory", "conversation", "agent", "loop", "discord",
            "surveillance", "persona", "safety", "consent", "recall",
            "embedding", "vector", "search", "episode", "write",
            "database", "pipeline", "benchmark", "performance", "latency",
        ]
        for _ in range(_SYNTHETIC_CORPUS_SIZE):
            text = " ".join(random.choices(words, k=random.randint(20, 80)))
            vec = generate_random_vector()
            _synthetic_corpus.append((text, vec))
    return _synthetic_corpus


# ---------------------------------------------------------------------------
# Dry-run benchmark operations
# ---------------------------------------------------------------------------


async def dry_run_vector_search(query_vec: list[float], top_k: int = 10) -> None:
    """Simulate vector search: compute cosine similarity across corpus."""
    corpus = _ensure_corpus()
    scored: list[tuple[float, int]] = []
    for idx, (_text, vec) in enumerate(corpus):
        sim = cosine_similarity(query_vec, vec)
        scored.append((sim, idx))
    scored.sort(key=lambda x: x[0], reverse=True)
    _ = scored[:top_k]


async def dry_run_fts_search(query_text: str, top_k: int = 10) -> None:
    """Simulate FTS search: regex text matching across corpus."""
    corpus = _ensure_corpus()
    query_lower = query_text.lower()
    # Tokenize query into words
    tokens: list[str] = re.findall(r"[a-z]+", query_lower)
    scored: list[tuple[int, int]] = []
    for idx, (text, _vec) in enumerate(corpus):
        text_lower = text.lower()
        hits = sum(1 for tok in tokens if tok in text_lower)
        if hits > 0:
            scored.append((hits, idx))
    scored.sort(key=lambda x: x[0], reverse=True)
    _ = scored[:top_k]


async def dry_run_hybrid_search(
    query_text: str, query_vec: list[float], top_k: int = 10
) -> None:
    """Simulate hybrid search: vector + FTS + RRF fusion."""
    corpus = _ensure_corpus()

    # Vector signal
    vec_scores: list[tuple[float, int]] = []
    for idx, (_text, vec) in enumerate(corpus):
        sim = cosine_similarity(query_vec, vec)
        vec_scores.append((sim, idx))
    vec_scores.sort(key=lambda x: x[0], reverse=True)

    # FTS signal
    query_lower = query_text.lower()
    fts_tokens: list[str] = re.findall(r"[a-z]+", query_lower)
    fts_scores: list[tuple[int, int]] = []
    for idx, (text, _vec) in enumerate(corpus):
        text_lower = text.lower()
        hits = sum(1 for tok in fts_tokens if tok in text_lower)
        if hits > 0:
            fts_scores.append((hits, idx))
    fts_scores.sort(key=lambda x: x[0], reverse=True)

    # RRF fusion (k=60)
    rrf_k = 60
    rrf_map: dict[int, float] = {}
    for rank, (_score, idx) in enumerate(vec_scores[:top_k * 3]):
        rrf_map[idx] = rrf_map.get(idx, 0.0) + 0.5 / (rrf_k + rank + 1)
    for rank, (_hits, idx) in enumerate(fts_scores[:top_k * 3]):
        rrf_map[idx] = rrf_map.get(idx, 0.0) + 0.5 / (rrf_k + rank + 1)

    fused = sorted(rrf_map.items(), key=lambda x: x[1], reverse=True)
    _ = fused[:top_k]


async def dry_run_episode_write() -> None:
    """Simulate episode write: vector generation + serialization overhead."""
    words = [
        "memory", "conversation", "agent", "loop", "discord",
        "surveillance", "persona", "safety", "consent", "recall",
    ]
    content = " ".join(random.choices(words, k=random.randint(50, 200)))
    _ = generate_random_vector()
    _ = {
        "id": str(uuid.uuid4()),
        "raw_content": content,
        "classification": "Restricted",
        "source": "benchmark",
        "importance": 5,
        "episode_type": "conversation",
        "started_at": "2026-06-02T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# Timing harness
# ---------------------------------------------------------------------------


async def time_operation(
    fn: Callable[[], Coroutine[object, object, None]],
    iterations: int,
    warmup: int,
) -> LatencyList:
    """Run *fn* for ``warmup + iterations`` calls, returning measured latencies.

    Warmup iterations are excluded from the returned list.
    """
    latencies: LatencyList = []
    total = warmup + iterations
    for i in range(total):
        start = time.perf_counter()
        await fn()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if i >= warmup:
            latencies.append(elapsed_ms)
    return latencies


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

_BOX_H = "\u2550"   # ═
_BOX_V = "\u2551"   # ║
_BOX_TL = "\u2554"  # ╔
_BOX_TR = "\u2557"  # ╗
_BOX_BL = "\u255a"  # ╚
_BOX_BR = "\u255d"  # ╝
_BOX_LT = "\u2560"  # ╠
_BOX_RT = "\u2563"  # ╣
_BOX_MT = "\u2566"  # ╦
_BOX_MB = "\u2569"  # ╩
_BOX_CROSS = "\u256c"  # ╬
_CHECK = "\u2713"   # ✓
_CROSS = "\u2717"   # ✗


def _pad(text: str, width: int) -> str:
    """Right-pad text to width."""
    if len(text) >= width:
        return text[:width]
    return text + " " * (width - len(text))


def _rpad(text: str, width: int) -> str:
    """Left-pad text to width."""
    if len(text) >= width:
        return text[:width]
    return " " * (width - len(text)) + text


def format_report(
    results: dict[str, dict[str, float]],
    targets: dict[str, float],
    iterations: int,
    warmup: int,
    mode: str,
) -> str:
    """Build the formatted benchmark report string."""
    col_op = 22
    col_val = 11
    col_target = 14

    total_w = col_op + col_val * 2 + col_target + 7  # 7 = borders

    lines: list[str] = []

    # Title
    title = "Guinevere Memory Pipeline Benchmark (P3-019)"
    title_padded = _pad("", (total_w - 2 - len(title)) // 2) + title
    lines.append(
        _BOX_TL + _BOX_H * (total_w - 2) + _BOX_TR
    )
    lines.append(
        _BOX_V + _pad(title_padded, total_w - 2) + _BOX_V
    )

    # Header separator
    lines.append(
        _BOX_LT
        + _BOX_H * col_op
        + _BOX_MT
        + _BOX_H * col_val
        + _BOX_MT
        + _BOX_H * col_val
        + _BOX_MT
        + _BOX_H * col_target
        + _BOX_RT
    )

    # Column headers
    lines.append(
        _BOX_V
        + _pad(" Operation", col_op)
        + _BOX_V
        + _rpad("p50 (ms) ", col_val)
        + _BOX_V
        + _rpad("p95 (ms) ", col_val)
        + _BOX_V
        + _pad(" Target", col_target)
        + _BOX_V
    )

    # Header/body separator
    lines.append(
        _BOX_LT
        + _BOX_H * col_op
        + _BOX_CROSS
        + _BOX_H * col_val
        + _BOX_CROSS
        + _BOX_H * col_val
        + _BOX_CROSS
        + _BOX_H * col_target
        + _BOX_RT
    )

    # Data rows
    all_pass = True
    row_order = [
        ("vector", "Vector Search"),
        ("fts", "FTS Search"),
        ("hybrid", "Hybrid Search"),
        ("write", "Episode Write"),
    ]

    for key, label in row_order:
        stats = results.get(key, {})
        target = targets.get(key, 0.0)
        p50 = stats.get("p50", 0.0)
        p95 = stats.get("p95", 0.0)
        passed = p95 < target
        if not passed:
            all_pass = False

        mark = _CHECK if passed else _CROSS
        target_label = f"< {target:.0f}ms  {mark}"

        lines.append(
            _BOX_V
            + _pad(f" {label}", col_op)
            + _BOX_V
            + _rpad(f"{p50:8.1f} ", col_val)
            + _BOX_V
            + _rpad(f"{p95:8.1f} ", col_val)
            + _BOX_V
            + _pad(f" {target_label}", col_target)
            + _BOX_V
        )

    # Footer separator
    lines.append(
        _BOX_LT
        + _BOX_H * col_op
        + _BOX_CROSS
        + _BOX_H * col_val
        + _BOX_CROSS
        + _BOX_H * col_val
        + _BOX_CROSS
        + _BOX_H * col_target
        + _BOX_RT
    )

    # Summary footer
    summary_line = (
        f" Iterations: {iterations} | Warmup: {warmup} | Mode: {mode}"
    )
    lines.append(
        _BOX_V + _pad(summary_line, total_w - 2) + _BOX_V
    )

    compliance = "ALL PASS" if all_pass else "SOME FAIL"
    compliance_line = f" ADR-009 Compliance: {compliance}"
    lines.append(
        _BOX_V + _pad(compliance_line, total_w - 2) + _BOX_V
    )

    # Bottom border
    lines.append(
        _BOX_BL + _BOX_H * (total_w - 2) + _BOX_BR
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dry-run benchmark runner
# ---------------------------------------------------------------------------


async def run_dry_run(args: BenchmarkArgs) -> dict[str, dict[str, float]]:
    """Execute dry-run benchmarks and return stats per operation."""
    iterations: int = args.iterations
    warmup: int = args.warmup

    # Pre-build corpus
    _ = _ensure_corpus()

    # Query data
    query_vec = generate_random_vector()
    query_text = "memory agent conversation recall search benchmark"

    print(f"Running dry-run benchmark ({iterations} iterations, {warmup} warmup)...")

    # Vector search
    print("  [1/4] Vector search simulation...")
    vec_latencies = await time_operation(
        lambda: dry_run_vector_search(query_vec), iterations, warmup
    )

    # FTS search
    print("  [2/4] FTS search simulation...")
    fts_latencies = await time_operation(
        lambda: dry_run_fts_search(query_text), iterations, warmup
    )

    # Hybrid search
    print("  [3/4] Hybrid search simulation...")
    hybrid_latencies = await time_operation(
        lambda: dry_run_hybrid_search(query_text, query_vec), iterations, warmup
    )

    # Episode write
    print("  [4/4] Episode write simulation...")
    write_latencies = await time_operation(
        dry_run_episode_write, iterations, warmup
    )

    return {
        "vector": compute_stats(vec_latencies),
        "fts": compute_stats(fts_latencies),
        "hybrid": compute_stats(hybrid_latencies),
        "write": compute_stats(write_latencies),
    }


# ---------------------------------------------------------------------------
# Live-DB benchmark runner
# ---------------------------------------------------------------------------


async def run_live_db(args: BenchmarkArgs) -> dict[str, dict[str, float]]:
    """Execute live benchmarks against a real PostgreSQL+pgvector database."""
    database_url: str = args.database_url or ""
    iterations: int = args.iterations
    warmup: int = args.warmup
    seed_count: int = max(iterations + warmup + 10, 100)

    print("Connecting to database...")
    print(f"Seeding {seed_count} test episodes...")

    try:
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )
    except ImportError as exc:
        print(f"ERROR: sqlalchemy is required for live-DB mode: {exc}")
        sys.exit(2)

    engine = create_async_engine(database_url, echo=False)
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Import project modules
    try:
        from src.memory.read_pipeline import RecallSession, recall_memories
        from src.memory.write_pipeline import EpisodeSession, store_episode
        from src.memory.embeddings import EmbeddingService
    except ImportError as exc:
        print(f"ERROR: Could not import memory pipeline: {exc}")
        await engine.dispose()
        sys.exit(2)

    # Seed test episodes
    seeded_ids: list[uuid.UUID] = []
    embedding_service: EmbeddingService | None = None
    try:
        embedding_service = EmbeddingService()
    except Exception:
        print("WARNING: EmbeddingService unavailable; using mock embeddings")
        embedding_service = None

    async with async_session_factory() as session:
        for i in range(seed_count):
            content = (
                f"Benchmark test episode {i}: "
                + " ".join(
                    random.choices(
                        [
                            "memory", "conversation", "agent", "loop",
                            "discord", "persona", "safety", "consent",
                            "recall", "embedding", "vector", "search",
                        ],
                        k=random.randint(20, 50),
                    )
                )
            )
            try:
                ep_id = await store_episode(
                    cast(EpisodeSession, cast(object, session)),
                    content=content,
                    source="benchmark-p3-019",
                    classification="Public",
                    importance=5,
                    title=f"Benchmark Episode {i}",
                    summary=f"Test episode {i} for performance benchmarking",
                    episode_type="benchmark",
                    embedding_service=embedding_service,
                )
                seeded_ids.append(ep_id)
            except Exception as exc:
                print(f"WARNING: Failed to seed episode {i}: {exc}")
                continue
        await session.commit()

    print(f"Seeded {len(seeded_ids)} episodes. Starting benchmarks...")

    query_text = "memory agent conversation recall search benchmark test"

    # Vector search benchmark
    print("  [1/4] Vector search (recall with embedding)...")
    async def bench_vector() -> None:
        async with async_session_factory() as sess:
            _ = await recall_memories(
                cast(RecallSession, cast(object, sess)),
                query_text=query_text,
                limit=10,
                embedding_service=embedding_service,
            )

    vec_latencies = await time_operation(bench_vector, iterations, warmup)

    # FTS-only benchmark (no embedding service = no vector search)
    print("  [2/4] FTS search (recall without embedding)...")
    async def bench_fts() -> None:
        async with async_session_factory() as sess:
            _ = await recall_memories(
                cast(RecallSession, cast(object, sess)),
                query_text=query_text,
                limit=10,
                embedding_service=None,
            )

    fts_latencies = await time_operation(bench_fts, iterations, warmup)

    # Hybrid search (same as vector but explicitly exercises full pipeline)
    print("  [3/4] Hybrid search (full pipeline)...")
    async def bench_hybrid() -> None:
        async with async_session_factory() as sess:
            _ = await recall_memories(
                cast(RecallSession, cast(object, sess)),
                query_text=query_text,
                limit=20,
                embedding_service=embedding_service,
            )

    hybrid_latencies = await time_operation(bench_hybrid, iterations, warmup)

    # Write benchmark
    print("  [4/4] Episode write (store_episode)...")
    async def bench_write() -> None:
        async with async_session_factory() as sess:
            content = (
                "Benchmark write test: "
                + " ".join(
                    random.choices(
                        ["alpha", "beta", "gamma", "delta", "epsilon"],
                        k=random.randint(30, 60),
                    )
                )
            )
            ep_id = await store_episode(
                cast(EpisodeSession, cast(object, sess)),
                content=content,
                source="benchmark-p3-019-write",
                classification="Public",
                importance=5,
                title="Benchmark Write Test",
                summary="Write benchmark episode",
                episode_type="benchmark",
                embedding_service=embedding_service,
            )
            seeded_ids.append(ep_id)
            await sess.commit()

    write_latencies = await time_operation(bench_write, iterations, warmup)

    # Cleanup: delete benchmark episodes
    print("Cleaning up test data...")
    async with async_session_factory() as sess:
        try:
            from src.memory.models import Episodes
            from sqlalchemy import delete

            stmt = (
                delete(Episodes)
                .where(Episodes.source.in_([
                    "benchmark-p3-019",
                    "benchmark-p3-019-write",
                ]))
            )
            _ = await sess.execute(stmt)
            await sess.commit()
        except Exception as exc:
            print(f"WARNING: Cleanup failed: {exc}")

    await engine.dispose()

    return {
        "vector": compute_stats(vec_latencies),
        "fts": compute_stats(fts_latencies),
        "hybrid": compute_stats(hybrid_latencies),
        "write": compute_stats(write_latencies),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_benchmark(args: BenchmarkArgs) -> int:
    """Main benchmark coroutine. Returns exit code."""
    if not args.dry_run and not args.database_url:
        print("ERROR: Must specify --dry-run or --database-url")
        print("Run with --help for usage information.")
        return 1

    mode = "dry-run" if args.dry_run else "live-db"

    targets = {
        "vector": TARGET_VECTOR_P95_MS,
        "fts": TARGET_FTS_P95_MS,
        "hybrid": TARGET_HYBRID_P95_MS,
        "write": TARGET_WRITE_P95_MS,
    }

    if args.dry_run:
        results = await run_dry_run(args)
    else:
        results = await run_live_db(args)

    report = format_report(
        results=results,
        targets=targets,
        iterations=args.iterations,
        warmup=args.warmup,
        mode=mode,
    )
    print()
    print(report)

    # Determine exit code
    all_pass = True
    for key, target in targets.items():
        stats = results.get(key, {})
        p95 = stats.get("p95", 0.0)
        if p95 >= target:
            all_pass = False
            break

    return 0 if all_pass else 1


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="P3-019: Memory pipeline performance benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "ADR-009 Targets:\n"
            "  Vector search:   p95 < 2000ms\n"
            "  FTS search:      p95 <  500ms\n"
            "  Hybrid search:   p95 < 3000ms\n"
            "  Episode write:   p95 < 5000ms\n"
            "\n"
            "Examples:\n"
            "  python scripts/bench_memory.py --dry-run\n"
            "  python scripts/bench_memory.py --database-url postgresql+asyncpg://...\n"
        ),
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run with synthetic data (no database required)",
    )
    _ = parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        metavar="URL",
        help="PostgreSQL async URL for live benchmark",
    )
    _ = parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        metavar="N",
        help="Number of benchmark iterations (default: 50)",
    )
    _ = parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        metavar="N",
        help="Warmup iterations excluded from measurement (default: 5)",
    )

    ns = parser.parse_args()
    bench_args = BenchmarkArgs.from_namespace(ns)
    exit_code = asyncio.run(run_benchmark(bench_args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

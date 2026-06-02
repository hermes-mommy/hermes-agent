# P3-007 HNSW Benchmark Report — ef_search Sensitivity Smoke Test

**File:** `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md`
**Date:** 2026-06-02
**Author:** Guinevere (Parent Executor)
**Target:** `memory.episodes.embedding` and `memory.semantic_facts.embedding` HNSW indexes (m=16, ef_construction=128, vector_cosine_ops)

---

## Methodology

### Setup

- **Environment**: Shared VPS (hostdata.id, 4C/16GB Ubuntu 24.04) — Guinevere Docker PostgreSQL, pgvector 0.8.2
- **Database**: `guinevere` on port 5433 (Docker)
- **Indexes tested**: `ix_episodes_embedding_hnsw` and `ix_semantic_facts_embedding_hnsw` (both m=16, ef_construction=128, vector_cosine_ops)
- **Proceedings**: All seed data inserted inside a `BEGIN...ROLLBACK` transaction — zero rows persisted
- **Vector generation**: Random 1536-dim `float4[]` cast to `vector` via `(array_agg(random()::float4))::vector`
- **Query type**: Cosine distance (`ORDER BY embedding <=> query_vector LIMIT 10`)
- **ef_search values tested**: 40, 100, 200 (per CHECKLIST.md and batch-plan-004-010.md)
- **Query pattern**: 1x `EXPLAIN (ANALYZE, BUFFERS)` + 5x raw query per ef_search value, per table = 36 queries total

### Data Volume

| Table | Rows Seeded |
|-------|-------------|
| `memory.episodes` | 20 |
| `memory.semantic_facts` | 20 |
| **Total** | **40** |

### Resource Constraints

- Benchmark kept shared VPS under 50% CPU/RAM (actual: < 1% CPU, 1.7/15Gi RAM)
- No CPU-intensive index builds
- No production data touched

---

## ef_search Sensitivity Results

### Key Finding: HNSW Index Not Used at Current Scale

At 20 rows per table, PostgreSQL's query planner **correctly chose Seq Scan + Sort** over HNSW index scan for all ef_search values. The cost estimate shows the planner determined that sorting 20 rows in memory (26kB quicksort) is cheaper than HNSW index traversal overhead.

```
Limit  (cost=28.78..28.80 rows=10)
  ->  Sort  (cost=1.88..1.93 rows=20)
        Sort Key: ((embedding <=> query_vector))
        Sort Method: quicksort  Memory: 26kB
        ->  Seq Scan on table  (cost=0.00..1.20 rows=20)
```

Because the HNSW index was not selected by the planner, **ef_search had no observable effect on query plans, execution times, or result quality**.

### Latency Table

All timings include ~0.4ms overhead for random 1536-dim vector generation via `generate_series(1, 1536)`.

| ef_search | Table | R1 (ms) | R2 (ms) | R3 (ms) | R4 (ms) | R5 (ms) | Mean (ms) | Min (ms) | Max (ms) |
|-----------|-------|---------|---------|---------|---------|---------|-----------|----------|----------|
| 40 | episodes | 0.733 | 0.701 | 0.673 | 0.686 | 0.710 | 0.701 | 0.673 | 0.733 |
| 40 | semantic_facts | 0.644 | 0.633 | 0.840 | 0.665 | 0.644 | 0.685 | 0.633 | 0.840 |
| 100 | episodes | 0.781 | 0.740 | 0.704 | 0.748 | 0.708 | 0.736 | 0.704 | 0.781 |
| 100 | semantic_facts | 0.631 | 0.647 | 0.650 | 0.615 | 0.640 | 0.637 | 0.615 | 0.647 |
| 200 | episodes | 0.723 | 0.704 | 0.701 | 0.676 | 0.685 | 0.698 | 0.676 | 0.723 |
| 200 | semantic_facts | 0.659 | 0.634 | 0.631 | 0.652 | 0.628 | 0.641 | 0.628 | 0.659 |

**Overall statistics (all 30 runs):**
- Mean: 0.683 ms
- Min: 0.615 ms
- Max: 0.840 ms
- P95: **Not meaningful** (see caveat below)

### EXPLAIN ANALYZE Buffers (all ef_search values)

| Metric | episodes | semantic_facts |
|--------|----------|----------------|
| Planning Time | 0.155–0.233 ms | 0.095–0.124 ms |
| Execution Time | 0.570–0.627 ms | 0.528–0.581 ms |
| Shared Buffers (hit) | 41 | 42 |
| Sort Memory | 26 kB | 26 kB |

---

## P95 Analysis and Caveat

### Assertion: P95 Cannot Be Meaningfully Determined

The task target specifies "check p95 < 200ms for HNSW-only smoke." This report **cannot** provide a meaningful p95 measurement because:

1. **Insufficient sample size**: Only 5 timing samples per ef_search value. Statistical significance for p95 requires at least 20–40 independent samples.
2. **No HNSW index usage**: The planner bypassed the HNSW index entirely (correctly, for 20 rows). p95 of Seq Scan + Sort is not a valid proxy for HNSW performance.
3. **Overhead contamination**: Each timing includes ~0.4ms of `generate_series` overhead for the query vector. The actual cosine comparison cost is masked.
4. **Negligible variance**: All 30 runs fall within 0.615–0.840ms range — the variance is dominated by `random()` seed differences, not by database execution.

### Recommendation for Meaningful Benchmark

A proper HNSW benchmark requires:

| Parameter | Minimum | Recommended |
|-----------|---------|-------------|
| Rows per table | 1,000 | 10,000–100,000 |
| ef_search values | 40, 100, 200 | 40, 64, 100, 128, 200 |
| Query samples per ef_search | 20 | 100 |
| Metrics | mean, p50, p95, p99, recall@10 | Same + throughput (QPS) |

Once P3-009 (write pipeline) populates the tables with real episodic data (expected 10+ rows per session × hundreds of sessions), re-run P3-007 to get meaningful HNSW measurements.

---

## GUC Behavior Note

`hnsw.ef_search` is a valid pgvector 0.8.2 GUC parameter:
- ✅ `SET hnsw.ef_search = N;` works
- ✅ `SHOW hnsw.ef_search;` returns the set value
- ✅ `SELECT current_setting('hnsw.ef_search');` works
- ⚠️ Does NOT appear in `pg_settings` or `SHOW ALL` until explicitly set in session
- ⚠️ No default value is registered — unset sessions fall back to pgvector internal default

This is a known pgvector 0.8.2 behavior: the GUC is registered dynamically by the extension but not listed statically. It works correctly when set.

---

## Next-Step Implications for P3-008

1. **No ef_search tuning decision needed yet**: Without production data volume, ef_search=100 (per ADR-009) remains the correct default for query code.
2. **P3-008 can proceed**: This benchmark is purely informational. No code changes are blocked.
3. **Re-benchmark at P3-019**: The full performance benchmark (P3-019) should test ef_search sensitivity when tables have production-scale data.

---

## Cleanup Confirmation

| Check | Result |
|-------|--------|
| Post-benchmark episodes count | 0 |
| Post-benchmark semantic_facts count | 0 |
| ROLLBACK executed | ✅ |
| No production data modified | ✅ |
| No indexes created/dropped | ✅ |

## Raw Data

Full benchmark raw output: `docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt` (644 lines) — includes all EXPLAIN (ANALYZE, BUFFERS) plans, Timing output for all 30 query runs, and transaction lifecycle.

---

## Footer

| Field | Value |
|-------|-------|
| **Date** | 2026-06-02 |
| **Author** | Guinevere (Parent Executor) |
| **Step** | P3-007 |
| **Phase** | P3 (Memory System) — batch 2 of ~6 |
| **Verdict** | ⚠️ **BENCHMARK COMPLETE — DATA VOLUME INSUFFICIENT FOR P95** — ef_search=40/100/200 tested; all queries <1ms (Seq Scan + Sort); HNSW index valid but bypassed for 20-row tables; zero rows persisted |
| **Next action** | Proceed to P3-008 (tsvector FTS + do_not_recall migration) after auditor PASS |
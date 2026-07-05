# D10 — Performance & Benchmark Validity (P3 Memory Foundation)

## Audit Metadata

| Field | Value |
|-------|-------|
| **Date** | 2026-06-25 |
| **Auditor** | Guinevere (subagent, read-only) |
| **Read-only affirmation** | Confirmed — no runtime code modified, no DB writes, no secrets printed |
| **Scope** | P3-006 HNSW index verification, P3-007 HNSW ef_search smoke benchmark, cross-ref to P18/P19/P5 query complexity risks, perf test coverage |
| **Files examined** | `docs/setup-evidence/P3/STEP-P3-006/verification.md`, `docs/setup-evidence/P3/STEP-P3-007/verification.md`, `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md`, `docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt`, `src/memory/read_pipeline.py`, `src/memory/write_pipeline.py`, `src/memory/models.py`, `src/memory/consolidation.py`, `alembic/versions/e401bb5fd274_initial_schema_47_tables.py`, `alembic/versions/p5_015_add_skill_embedding.py`, `alembic/versions/p19_001_project_namespaces.py`, `alembic/versions/p18_add_memory_tiers_fsrs.py` |

---

## Findings

### [HIGH] FND-PERF-001: Benchmark executed on 20 rows; HNSW never exercised

The P3-007 smoke benchmark seeded only **20 rows per table** (40 total) inside a `BEGIN...ROLLBACK` transaction. At this scale, PostgreSQL's query planner correctly chose **Seq Scan + Sort** for every query across all three `ef_search` values (40, 100, 200). The HNSW index was never used by the planner.

Evidence:
- `docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt:36-52` — EXPLAIN output shows Seq Scan on `_hyper_17_3_chunk` / `semantic_facts`, Sort with 26kB quicksort memory, no Index Scan.
- `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md:42-53` — explicitly states "HNSW Index Not Used at Current Scale" and "the planner correctly chose Seq Scan + Sort over HNSW index scan for all ef_search values."
- `docs/setup-evidence/P3/STEP-P3-007/verification.md:111` — "The HNSW index was not selected by the planner because the cost of Seq Scan + Sort (20 rows, 26kB memory) is lower than HNSW traversal overhead for tiny datasets."

The benchmark report is transparent about this limitation, yet both `verification.md` and `benchmark-report.md` claim an overall **PASS** verdict. A benchmark that cannot exercise its target index does not validate performance; the "PASS" label is misleading.

### [HIGH] FND-PERF-002: ef_search sensitivity unmeasured

The stated purpose of P3-007 was to "check p95 < 200ms for HNSW-only smoke" and document `ef_search` sensitivity at values 40, 100, and 200. Because HNSW was never used:

- ef_search had **zero observable effect** on query plans, execution times, or result quality.
- The benchmark report admits: "P95 Cannot Be Meaningfully Determined" due to insufficient sample size (5 per ef_search), no HNSW index usage, overhead contamination (0.4ms vector generation), and negligible variance (0.615–0.840ms dominated by `random()` seed differences).
- `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md:85-107` — recommends minimum 1,000 rows, ideally 10,000–100,000, with 20+ query samples per ef_search value.
- The recommended re-run at **P3-019** has no evidence of execution.

### [MEDIUM] FND-PERF-003: P19 project_id filter may bypass HNSW at runtime

The `recall_memories` function in `src/memory/read_pipeline.py` adds a `WHERE (project_id = :pid OR project_scope = 'global')` clause to all three query builders (`build_vector_query` at line 563-568, `build_fts_query` at line 600-606, `build_recency_query` at line 634-640) when `project_id` is not None.

The P19 migration (`alembic/versions/p19_001_project_namespaces.py`) creates a B-tree index `ix_episodes_project_id_embedding ON memory.episodes (project_id, embedding)` at line 159. However:

- PostgreSQL's HNSW index is on `episodes.embedding` alone. Adding a `project_id` equality filter alongside `ORDER BY embedding <=>` may cause the planner to choose the B-tree `(project_id, embedding)` index over the HNSW index, or force a Seq Scan if neither index is cost-effective for the combined predicate + ordering.
- The B-tree on `(project_id, embedding)` does NOT accelerate cosine distance ordering (`<=>` operator). It only helps with exact `project_id` equality. After filtering by `project_id`, pgvector would still need to compute cosine distances on the filtered subset.
- This perf impact has **never been benchmarked**. The P3-007 benchmark predates P19. The P19 migration chain includes no performance verification step.

### [MEDIUM] FND-PERF-004: No runtime hnsw.ef_search configuration in application code

The `build_vector_query` function (`src/memory/read_pipeline.py:531-570`) executes `ORDER BY embedding <=> query_vector LIMIT limit` without ever issuing `SET hnsw.ef_search = N`. The `hnsw.ef_search` GUC defaults to pgvector's internal default (typically 40) per `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md:111-121` (GUC Behavior Note).

The `pgvector_config` table in `src/memory/models.py:1229-1248` stores `hnsw_ef_search: Optional[int]` with server default `64` (`alembic/versions/e401bb5fd274_initial_schema_47_tables.py:170`), but this is a **metadata/config table only** — the application never reads it and never issues `SET hnsw.ef_search` at session start or per-query.

ADR-009 per the benchmark plan recommends `ef_search=100`, but this value is neither configured at runtime nor enforced by application code.

### [LOW] FND-PERF-005: procedural_skills uses IVFFlat instead of HNSW

Migration `alembic/versions/p5_015_add_skill_embedding.py:22-32` creates an **IVFFlat** index (`USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`) on `memory.procedural_skills`, while the P3 schema creates HNSW indexes on `memory.episodes` and `memory.semantic_facts`. This is a P5 concern but represents an inconsistency in the index strategy across vector-column tables. IVFFlat requires a full cluster scan at query time and has lower recall than HNSW for equivalent parameter tuning.

### [LOW] FND-PERF-006: No EXPLAIN regression test suite

No unit tests or integration tests verify that the query planner produces expected index scans (HNSW) for the `build_vector_query` / `build_fts_query` / `build_recency_query` functions. There are no EXPLAIN-based regression tests to catch plan regressions as data volume grows or as new columns (tier, fsrs_state, project_id, project_scope) are added to the WHERE clauses.

The `read_pipeline.py` recall function at lines 1067-1070 has broad `except Exception` catch blocks for FSRS and KG signal failures, but query-level planner failures (e.g., planner choosing Seq Scan over HNSW due to cost threshold) would not raise Python exceptions — they silently degrade performance.

---

## Evidence Summary

| Finding | Severity | File:Line Reference |
|---------|----------|---------------------|
| 20-row benchmark, HNSW never exercised | HIGH | `benchmark-report.md:42-53`, `hnsw-benchmark-raw.txt:36-52` |
| ef_search sensitivity unmeasured | HIGH | `benchmark-report.md:85-107` |
| P19 project_id filter may bypass HNSW | MEDIUM | `read_pipeline.py:563-568`, `p19_001_project_namespaces.py:159` |
| No runtime ef_search configuration | MEDIUM | `read_pipeline.py:531-570`, no `SET hnsw.ef_search` found anywhere in `src/` |
| procedural_skills IVFFlat vs HNSW | LOW | `p5_015_add_skill_embedding.py:27-30` |
| No EXPLAIN regression tests | LOW | No test files contain EXPLAIN-based plan assertions |

---

## Status Verdict

**DOCS CLAIM ONLY / NOT PROVEN** — for the performance benchmark dimension specifically.

The HNSW indexes themselves are verified as correctly created (P3-006 PASS), but:
- The P3-007 ef_search sensitivity benchmark validated nothing because HNSW was never exercised (20 rows).
- The "PASS" verdict on the verification report is misleading given the index was idle.
- The required production-scale re-benchmark (P3-019, recommended at 10,000+ rows) has no evidence of execution.
- Query-plan-altering features (P19 project_id filter, P18 FSRS columns) were added after the benchmark without re-validation.
- No runtime ef_search configuration exists in application code despite ADR-009 recommending ef_search=100.

---

## Recommendations (no code fixes — for mama consideration)

1. **Re-benchmark at meaningful scale**: Execute the P3-007 benchmark as recommended with 10,000+ rows per table, 20+ query samples per ef_search value, and verify that the planner actually uses the HNSW index. Use persistent data (not ROLLBACK) to assess real index sizes and build costs.

2. **Benchmark P19 project_id filter impact**: Test `recall_memories` with `project_id` set against the P19 `(project_id, embedding)` B-tree index vs. the HNSW-only scan. Determine whether the planner correctly uses HNSW + filter or falls back to B-tree scan + sort. If the planner bypasses HNSW, consider a filtered/indexed approach (e.g., partial HNSW index per project_id range, or application-level project filtering).

3. **Wire ef_search at application level**: Either have `build_vector_query` (or a session startup hook) issue `SET hnsw.ef_search = 100` per ADR-009, or implement a dynamic read from `extensions.pgvector_config.hnsw_ef_search`.

4. **Add EXPLAIN regression tests**: After re-benchmarking, add lightweight EXPLAIN-based assertions (using `EXPLAIN (FORMAT JSON)`) to the test suite that verify HNSW index scans for vector queries at sufficient row counts.

5. **Align procedural_skills index**: Consider migrating the IVFFlat index on `procedural_skills` to HNSW for consistency with the rest of the memory schema, unless there is a documented performance rationale for IVFFlat on that table.

6. **P19-003 gate**: Make the P19 migration step that adds `(project_id, embedding)` indexes conditional on a benchmark proving no planner regression, or replace it with a partial/filtered approach that preserves HNSW usage.

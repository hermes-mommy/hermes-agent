# P3 Performance Benchmark -- Adversarial Audit (Round 2)

**File:** `docs/setup-evidence/legacy-audit/P3/audits/round-2/performance-benchmark-adversarial.md`
**Date:** 2026-06-25
**Auditor:** Wave-2 Adversarial Audit
**Scope:** Refute or validate P3-006/P3-007 performance claims
**Verdict:** [CRITICAL] **NOT PROVEN -- DOCS CLAIM ONLY**

---

## Executive Summary

The P3-007 benchmark report presents latency measurements and HNSW index verification
as performance evidence. Under adversarial scrutiny, **none of the performance claims
survive**. The benchmark was conducted on 40 rows with random vectors, the HNSW index
was never used by the query planner, no reproducible performance test exists in the
test suite, and the production query path adds P18 FSRS + P19 project_id filters that
were never benchmarked. The "p95 < 200ms" gate cannot be validated from the evidence
provided.

---

## (a) P3-007 Benchmark Data Size, Row Count, Index Use, EXPLAIN ANALYZE

### Finding (a-1): 20 rows per table -- HNSW index bypassed

**Severity:** [CRITICAL]
**File:** `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md:26-29`

The benchmark seeded exactly **20 rows** into `memory.episodes` and **20 rows** into
`memory.semantic_facts` (40 rows total). All data was inserted inside a
`BEGIN...ROLLBACK` transaction using **random 1536-dim float4 vectors**, not real
embeddings from the EmbeddingService.

The benchmark report itself admits (line 43-51):

> At 20 rows per table, PostgreSQL's query planner **correctly chose Seq Scan + Sort**
> over HNSW index scan for all ef_search values.

Every EXPLAIN ANALYZE output shows:

```
Seq Scan on _hyper_17_3_chunk  (cost=0.00..1.20 rows=20 width=34)
  Sort Method: quicksort  Memory: 26kB
```

The HNSW index `ix_episodes_embedding_hnsw` was **never used**. All latency
measurements (mean 0.683ms) reflect Seq Scan + Sort on a tiny in-memory table,
not HNSW graph traversal.

### Finding (a-2): Random vectors, not real embeddings

**Severity:** [HIGH]
**File:** `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md:18`
**File:** `docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt:4-6`

Vectors were generated via:
```sql
(array_agg(random()::float4))::vector
```

Random vectors have no semantic structure. Real embeddings from the EmbeddingService
(1536-dim OpenAI or MiniLM-derived) cluster in a low-dimensional manifold. HNSW
traversal characteristics (branching, pruning, recall quality) differ significantly
between random and clustered data. The benchmark measures nothing meaningful about
production vector search.

### Finding (a-3): P95 explicitly declared "Not meaningful"

**Severity:** [HIGH]
**File:** `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md:72`

The report states:

> P95: **Not meaningful** (see caveat below)

With only 5 timing samples per ef_search value, p95 cannot be calculated. The
report recommends 20-40 samples minimum. The "p95 < 200ms" gate in CHECKLIST.md
remains **unvalidated**.

---

## (b) HNSW Indexes -- Present in Migration DDL

### Finding (b-1): HNSW CREATE INDEX confirmed in alembic migration

**Severity:** [LOW] (positive finding)
**File:** `alembic/versions/e401bb5fd274_initial_schema_47_tables.py:325`
**File:** `alembic/versions/e401bb5fd274_initial_schema_47_tables.py:480`

Both HNSW indexes are present in the migration DDL:

```sql
CREATE INDEX IF NOT EXISTS ix_episodes_embedding_hnsw
  ON memory.episodes USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);

CREATE INDEX IF NOT EXISTS ix_semantic_facts_embedding_hnsw
  ON memory.semantic_facts USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 128);
```

Parameters match ADR-009 (m=16, ef_construction=128, vector_cosine_ops).
Verification in P3-006 confirmed these exist on the live database. The DDL is
real and was actually applied.

### Finding (b-2): P19 created (project_id, embedding) composite indexes -- HNSW unaffected

**Severity:** [MEDIUM]
**File:** `alembic/versions/p19_001_project_namespaces.py:159-160`

P19 added btree composite indexes:
```sql
CREATE INDEX ix_episodes_project_id_embedding ON memory.episodes (project_id, embedding);
CREATE INDEX ix_semantic_facts_project_id_embedding ON memory.semantic_facts (project_id, embedding);
```

These are **btree** indexes on `(project_id, embedding)`, not HNSW. They cannot
accelerate cosine distance queries. They exist for equality+embedding lookup only.
The HNSW indexes remain the only vector similarity indexes, and they do **not**
include project_id as a leading column, meaning HNSW cannot filter by project
at the index level.

---

## (c) Latency Claims -- Reproducibility with P18 FSRS + P19 project_id Filter

### Finding (c-1): project_id OR filter may prevent HNSW index use

**Severity:** [HIGH]
**File:** `src/memory/read_pipeline.py:563-569`

The `build_vector_query` function adds:
```python
stmt = stmt.where(
    or_(
        Episodes.project_id == project_id,
        Episodes.project_scope == "global",
    )
)
```

This OR condition complicates the query plan. PostgreSQL cannot use a single HNSW
index scan to satisfy `(project_id = X OR project_scope = 'global')` because:
1. The HNSW index on `embedding` has no project_id/project_scope columns.
2. The btree composite `ix_episodes_project_id_embedding` cannot do cosine distance.
3. The planner may choose a BitmapOr or Seq Scan when the OR cannot be pushed
   into the HNSW index scan.

**No benchmark was ever run with project_id filtering enabled.** The P3-007 benchmark
used bare cosine distance queries without project scope. Production queries from
`recall_memories()` always pass `project_id` when called in project-scoped mode.

### Finding (c-2): FSRS reconsolidation adds N write operations per recall

**Severity:** [HIGH]
**File:** `src/memory/read_pipeline.py:1036-1049`

When `fsrs_enabled=True` (the production default for P18), the pipeline loops:

```python
for r in scored:
    ...
    _fsrs_scheduler.update_episode_state(episode, GRADE_GOOD)
    fsrs_updated_count += 1
```

This performs **one write operation per retrieved episode** synchronously in a loop.
For `limit=20` with `EXPANDED_LIMIT_MULTIPLIER=3`, there could be up to 60 scored
candidates, each requiring an FSRS state update. This is O(N) writes that was
**never benchmarked**. With typical latency of 1-5ms per write through PgBouncer,
this adds 60-300ms on top of the read queries.

### Finding (c-3): Benchmark was one-shot, not reproducible

**Severity:** [CRITICAL]

The P3-007 benchmark used shell scripts (`benchmark-hnsw.sh`, `benchmark.sql`) that
seed data inside `BEGIN...ROLLBACK`. The raw output at
`docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt` is 644 lines of
one-time psql output. There is no:
- pytest test that can be re-run
- Fixture that seeds data deterministically
- Assertion on latency thresholds
- CI integration

The benchmark cannot be reproduced without manually running shell scripts against
a live database.

---

## (d) Is There a Perf Test That Actually Runs (pytest)?

### Finding (d-1): No pytest benchmark test for memory/HNSW performance

**Severity:** [CRITICAL]
**File:** `tests/memory/test_read_pipeline_hybrid.py` (all 399 lines)

The test file `test_read_pipeline_hybrid.py` contains **deterministic unit tests**
using `FakeEpisode` objects. Tests verify:
- RRF score computation math
- Both-signal bonus (1.25x)
- Recency decay formula
- DNR WHERE clause presence in SQL strings
- Classification ceiling fail-closed
- Constants values (RRF_K=60, CHARS_PER_TOKEN=4, etc.)

**Zero tests** exercise:
- Actual database queries
- HNSW index usage under load
- Latency thresholds
- Token budget behavior with real content
- FSRS reconsolidation write performance

### Finding (d-2): Hard-stop latency tests are unrelated

**Severity:** [LOW] (not a finding, just context)
**File:** `tests/safety/test_hard_stop_latency.py`

The latency tests in `test_hard_stop_latency.py` measure `HardStopHandler.check()`
latency, which is a pure Python regex/string operation. These have nothing to do
with database, HNSW, or memory pipeline performance.

### Finding (d-3): No pytest-benchmark dependency configured

**Severity:** [HIGH]
**File:** `pyproject.toml:48-49`

The test dependencies are:
```toml
test = ["pytest-cov>=7", "pytest-asyncio>=0.23"]
```

There is no `pytest-benchmark` dependency. No benchmark plugin is configured.
There is no infrastructure for automated performance regression testing.

---

## (e) recall_memories Query Pattern -- N+1 or Single Query?

### Finding (e-1): Three sequential queries (not N+1, but not parallel either)

**Severity:** [MEDIUM]
**File:** `src/memory/read_pipeline.py:906-927`

The `recall_memories` function executes three **sequential** `await session.execute()`
calls:

```python
# Line 912: vector query
vector_result = await session.execute(vector_stmt)

# Line 919: FTS query
fts_result = await session.execute(fts_stmt)

# Line 926: recency query
recency_result = await session.execute(recency_stmt)
```

This is **not N+1** (each query returns `expanded_limit` rows at once). However,
the three queries are executed **sequentially**, not in parallel via
`asyncio.gather()`. Each query incurs its own round-trip latency through
PgBouncer (port 5434) to PostgreSQL (port 5433).

For three queries at ~1-5ms each (at production scale), this adds 3-15ms of
sequential latency that could be reduced to ~5ms max with parallel execution.

### Finding (e-2): FSRS path IS effectively N+1

**Severity:** [HIGH]
**File:** `src/memory/read_pipeline.py:1036-1049`

When `fsrs_enabled=True`, the code iterates over all scored candidates and calls
`update_episode_state()` individually per episode. This is an **N-operation write
loop** executed within the recall path. Even though `update_episode_state` may
batch internally, the outer loop structure is O(N) with no transaction batching
visible in the recall_memories code path.

### Finding (e-3): KG signal adds a 4th query via lazy import

**Severity:** [LOW]
**File:** `src/memory/read_pipeline.py:947-987`

When `kg_enabled=True` (the default), the pipeline imports and instantiates
`KGRRFFusion`, `KGQueryEngine`, and `PersonalizedPageRank` inside the function
body. The `compute_graph_scores()` call executes additional database queries
through the KG module. Total query count in the happy path: 3 (vector + FTS +
recency) + N_KG_queries + 1 (FSRS writes) = potentially 5-10+ database round
trips per recall.

---

## (f) Token Budget -- Is estimate_tokens Accurate?

### Finding (f-1): CHARS_PER_TOKEN=4 underestimates for non-English text

**Severity:** [MEDIUM]
**File:** `src/memory/read_pipeline.py:103-104`

```python
CHARS_PER_TOKEN: int = 4
"""Rough estimate: one token ~= 4 characters for typical text."""
```

The estimate `len(text) // 4` uses **integer division**, which consistently
underestimates by 0-3 tokens per string. For a 4000-token budget:
- At 4 chars/token: 4000 tokens = 16,000 characters
- Actual GPT tokenization: ~3.5-4.5 chars/token depending on language
- For CJK text: ~1.5-2 chars/token (Chinese/Japanese characters)
- For code: ~3-3.5 chars/token

**Risk:** For non-English content (Indonesian locale -- the VPS is `hostdata.id`),
the estimate could **overestimate** token count by 30-50%, causing the budget to
return fewer results than intended. For CJK text, it could **underestimate** by
100%, potentially pushing content beyond the model's context window.

### Finding (f-2): Token budget applies to safe_content only, not full context

**Severity:** [MEDIUM]
**File:** `src/memory/read_pipeline.py:504-506`

```python
safe_content = str(r.get("safe_content", ""))
estimated = estimate_tokens(safe_content)
```

The budget counts only `safe_content` tokens. It does not account for:
- Metadata fields (classification, importance, created_at, id) in the returned dict
- The prompt template that wraps recalled memories
- KG context injection block header/footer
- System prompt tokens

If the caller injects recalled memories into a prompt with a 32k context window,
the 4000-token budget leaves 28k for everything else. This is **conservative**
but wasteful of context window capacity.

### Finding (f-3): Integer division floor consistently underestimates

**Severity:** [LOW]
**File:** `src/memory/read_pipeline.py:484`

```python
return len(text) // CHARS_PER_TOKEN
```

`len("hello") // 4 = 1` but "hello" is actually ~1.2 tokens. For short strings
(50-100 chars), this loses 1-3 tokens per item. Over 20 results, the total
undercount is 20-60 tokens. Minor but systematic.

---

## (g) Can the Claimed HNSW Benchmark Be Reproduced?

### Finding (g-1): Not reproducible with current codebase

**Severity:** [CRITICAL]

The benchmark requires:
1. A live PostgreSQL 5433 instance with pgvector 0.8.2
2. The HNSW indexes from the P3-002 migration
3. Manual execution of shell scripts against the database
4. Random vector generation via `generate_series(1, 1536)`

There is no automated test, no fixture, no CI job. Re-running requires:
```bash
psql -h localhost -p 5433 -f docs/setup-evidence/P3/STEP-P3-007/benchmark.sql
```

This is a **manual, one-shot** process with no assertion on results.

### Finding (g-2): Meaningful HNSW benchmark requires 10,000+ rows

**Severity:** [HIGH]
**File:** `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md:98-106`

The report itself acknowledges:

| Parameter | Minimum | Recommended |
|-----------|---------|-------------|
| Rows per table | 1,000 | 10,000-100,000 |
| Query samples per ef_search | 20 | 100 |
| Metrics | mean, p50, p95, p99, recall@10 | Same + throughput (QPS) |

At 20 rows, PostgreSQL **never selects the HNSW index**. The entire benchmark
measures Seq Scan + Sort performance on a toy dataset.

### Finding (g-3): Production data volume is currently zero

**Severity:** [HIGH]
**File:** `docs/setup-evidence/P3/STEP-P3-006/verification.md:148-151`

P3-006 confirmed both tables contain **0 rows** at the time of verification.
The P3-007 benchmark seed data was rolled back. There is no production data
to benchmark against. Until the write pipeline (P3-009) populates episodes
through actual usage, HNSW index performance is entirely theoretical.

---

## Additional Findings

### Finding (g-4): No composite HNSW+project index

**Severity:** [HIGH]
**File:** `alembic/versions/p19_001_project_namespaces.py:159-160`

P19 created btree composite indexes `(project_id, embedding)` but these cannot
accelerate cosine distance queries. The HNSW indexes have no project_id column.
For project-scoped vector search, PostgreSQL must:
1. Scan the HNSW index (no project filter)
2. Post-filter rows by project_id

This means HNSW recall@10 will be degraded when many projects exist, as the
top-10 by cosine distance may all belong to other projects.

### Finding (g-5): TimescaleDB hypertable chunk naming in EXPLAIN

**Severity:** [LOW]
**File:** `docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt:42`

The EXPLAIN output shows `_hyper_17_3_chunk`, confirming the episodes table
is a TimescaleDB hypertable. Chunk-level operations add planning overhead
not present in plain PostgreSQL tables. This overhead was not measured
separately.

---

## Summary Table

| Hunt | Finding | Severity | Verdict |
|------|---------|----------|---------|
| (a) Benchmark data size | 20 rows/table, random vectors, HNSW bypassed | [CRITICAL] | Seq Scan toy test |
| (b) HNSW in migration DDL | Confirmed with correct params | [LOW] | PASS |
| (c) Latency with P18+P19 | OR filter + FSRS N-writes unbenchmarked | [HIGH] | NOT TESTED |
| (d) pytest perf test | None exists; unit tests only | [CRITICAL] | NO TEST |
| (e) Query pattern | 3 sequential queries + FSRS N-writes | [MEDIUM/HIGH] | Not parallel |
| (f) Token estimate accuracy | CHARS_PER_TOKEN=4 is approximate, CJK risk | [MEDIUM] | APPROXIMATE |
| (g) Benchmark reproducibility | Manual shell scripts, no automation | [CRITICAL] | NOT REPRODUCIBLE |

---

## Status Verdict

**[CRITICAL] NOT PROVEN -- DOCS CLAIM ONLY**

The P3-007 benchmark is a **documentation exercise**, not a performance proof.
Key failures:

1. **HNSW was never exercised.** The planner correctly chose Seq Scan for 20 rows.
   All latency numbers measure in-memory sort, not vector index traversal.

2. **No reproducible test.** No pytest benchmark exists. The shell scripts produce
   one-shot output with no assertions.

3. **Production path unbenchmarked.** The P18 FSRS reconsolidation writes and
   P19 project_id OR filter were never included in any benchmark.

4. **Data volume nonexistent.** Both tables contain 0 production rows. The
   benchmark used random vectors in a rollback transaction.

5. **p95 gate unvalidated.** The "p95 < 200ms" target cannot be assessed from
   5 samples on a 20-row Seq Scan.

### Required Actions to Make This PROVEN:

1. **Create a pytest benchmark** (`tests/memory/test_recall_benchmark.py`) with
   `pytest-benchmark` that seeds 10,000+ rows with real embeddings, runs
   `recall_memories()` with fsrs_enabled=True and project_id set, and asserts
   p95 < 200ms.

2. **Benchmark with project_id filtering** to measure OR-clause impact on
   HNSW index usage.

3. **Benchmark FSRS write overhead** separately from read queries.

4. **Add `pytest-benchmark`** to `[project.optional-dependencies] test`.

5. **Re-run at P3-019** once production data exists (per benchmark-report.md
   own recommendation at line 107).

Until then, any claim that P3 memory performance is "validated" or "benchmarked"
is unsupported by the evidence.

---

**End of Adversarial Audit**

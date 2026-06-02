# P3-007 Verification Report — HNSW Parameter Tuning / Benchmark Smoke

**File:** `docs/setup-evidence/P3/STEP-P3-007/verification.md`
**Status:** ✅ PASS — Benchmark evidence captured; caveats documented
**Date:** 2026-06-02
**Author:** Guinevere (Parent Executor)
**Step:** P3-007 — HNSW Parameter Tuning / Benchmark Smoke (runtime evidence only)

---

## 1 — What Was Done

Executed a resource-safe HNSW smoke benchmark on the shared VPS (guinevere-vps, Tailscale 100.94.104.22) to document `hnsw.ef_search` sensitivity for values 40, 100, and 200. Because both `memory.episodes` and `memory.semantic_facts` contained 0 rows (confirmed by P3-006), the benchmark used a rollback-safe approach:

1. **Pre-step health checks** on Aizanta PG 5432, Guinevere PG 5433, PgBouncer 5434, Redis 6380, 9Router 20128, Docker containers, system resources, and Aizanta services.
2. **DB state verification** — row counts, HNSW index definitions, pgvector version, index sizes, `hnsw.ef_search` GUC behavior.
3. **HNSW smoke benchmark** — seeded 20 episodes + 20 semantic facts with random 1536-dim vectors inside a `BEGIN...ROLLBACK` transaction. Ran cosine distance queries with `SET hnsw.ef_search = 40`, `100`, `200`, each with `EXPLAIN (ANALYZE, BUFFERS)` and 5 query runs per ef_search value per table.
4. **Cleanup verification** — ROLLBACK confirmed; both tables show 0 rows post-benchmark.

No source code, indexes, or production data were modified.

---

## 2 — Files Changed

| File | Action |
|------|--------|
| `docs/setup-evidence/P3/STEP-P3-007/verification.md` | **Created** — This report |
| `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md` | **Created** — Benchmark summary report |
| `docs/setup-evidence/P3/STEP-P3-007/runtime-prestep-output.txt` | **Created** — Pre-step health check raw output |
| `docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt` | **Created** — Full benchmark raw output (Timing on, EXPLAIN ANALYZE, all 30 query runs) |
| `docs/setup-evidence/P3/STEP-P3-007/benchmark-hnsw.sh` | **Created** — Shell benchmark runner artifact |
| `docs/setup-evidence/P3/STEP-P3-007/benchmark.sql` | **Created** — SQL benchmark script artifact |
| `docs/setup-evidence/P3/STEP-P3-007/db-check.sh` | **Created** — DB state check script artifact |
| `docs/setup-evidence/P3/STEP-P3-007/verify-cleanup.sh` | **Created** — Post-benchmark cleanup verification script |
| `docs/setup-evidence/P3/STEP-P3-007/prestep-health.sh` | **Created** — Pre-step health helper artifact |
| `docs/setup-evidence/P3/STEP-P3-007/guc-check.sh` | **Created** — pgvector/HNSW GUC inspection helper artifact |
| `docs/setup-evidence/P3/STEP-P3-007/guc-check2.sh` | **Created** — follow-up HNSW GUC inspection helper artifact |
| `docs/setup-evidence/P3/STEP-P3-007/vec-test.sh` | **Created** — read-only vector cast exploration helper artifact |
| `docs/setup-evidence/P3/STEP-P3-007/vec-test2.sh` | **Created** — read-only vector cast exploration helper artifact |
| `docs/setup-evidence/P3/STEP-P3-007/vec-test3.sh` | **Created** — read-only vector construction exploration helper artifact |

No source code, model files (`src/memory/models.py`), PROGRESS.md, or CHECKLIST.md were modified. Shell/SQL files above are evidence helper artifacts only; parent read them and confirmed no COMMIT, no DDL, no index operations, no secrets, and no persistent rows.

---

## 3 — Validation Results

### 3.1 Pre-Step Health Checks (summary)

| Check | Result | Detail |
|-------|--------|--------|
| Aizanta PostgreSQL (5432) | ✅ PASS | `accepting connections` |
| Guinevere PostgreSQL (5433) | ✅ PASS | `accepting connections` |
| PgBouncer (5434) | ✅ PASS | `accepting connections` |
| Redis (6380) | ✅ PASS | `NOAUTH` (server up, auth required) |
| 9Router (20128) | ✅ PASS | HTTP 200 |
| Docker containers | ✅ PASS | 10/10 running (3 guinevere + 5 aizanta + 2 others) |
| System memory | ✅ PASS | 15Gi total, 1.7Gi used, 13Gi available |
| Swap | ✅ PASS | 4.0Gi, 0 used |
| Uptime | ✅ PASS | 10 days 2:57, load avg 0.27 |
| Disk | ✅ PASS | 99G total, 17G used, 77G free (18%) |
| guinevere-core | ✅ PASS | `active` |
| guinevere-9router | ✅ PASS | `active` |

### 3.2 DB State

| Check | Result |
|-------|--------|
| pgvector version | ✅ 0.8.2 |
| Episodes row count | 0 (pre-benchmark); 0 (post-benchmark) |
| Semantic facts row count | 0 (pre-benchmark); 0 (post-benchmark) |
| HNSW index `ix_episodes_embedding_hnsw` | ✅ Exists, `m=16 ef_construction=128 vector_cosine_ops` |
| HNSW index `ix_semantic_facts_embedding_hnsw` | ✅ Exists, `m=16 ef_construction=128 vector_cosine_ops` |
| Index sizes | 16 kB each (empty tables) |
| `hnsw.ef_search` GUC | ✅ Works when `SET` explicitly; persistent value default is absent |

### 3.3 Benchmark — Key Findings

#### Query Plan (all ef_search values — identical behavior)

All queries used **Seq Scan + Sort** — the HNSW index was NOT used because both tables contain only 20 rows. PostgreSQL's optimizer correctly determined:

```
Limit  (cost=28.78..28.80 rows=10)
  ->  Sort  (cost=1.88..1.93 rows=20)
        Sort Key: ((embedding <=> $0))
        Sort Method: quicksort  Memory: 26kB
        ->  Seq Scan on table  (cost=0.00..1.20 rows=20)
```

**Planning Time:** 0.095–0.233 ms
**Execution Time:** 0.528–0.627 ms
**Buffers:** shared hit=41–42

#### Latency Summary (30 query runs total)

| ef_search | Table | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Mean |
|-----------|-------|-------|-------|-------|-------|-------|------|
| 40 | episodes | 0.733ms | 0.701ms | 0.673ms | 0.686ms | 0.710ms | 0.701ms |
| 40 | semantic_facts | 0.644ms | 0.633ms | 0.840ms | 0.665ms | 0.644ms | 0.685ms |
| 100 | episodes | 0.781ms | 0.740ms | 0.704ms | 0.748ms | 0.708ms | 0.736ms |
| 100 | semantic_facts | 0.631ms | 0.647ms | 0.650ms | 0.615ms | 0.640ms | 0.637ms |
| 200 | episodes | 0.723ms | 0.704ms | 0.701ms | 0.676ms | 0.685ms | 0.698ms |
| 200 | semantic_facts | 0.659ms | 0.634ms | 0.631ms | 0.652ms | 0.628ms | 0.641ms |

**Note:** Timing includes 1536-dim random vector generation overhead (~0.4ms via `generate_series`). Actual vector comparison time is significantly less.

#### HNSW Index Usage

The HNSW index (`ix_episodes_embedding_hnsw` / `ix_semantic_facts_embedding_hnsw`) was **not selected** by the planner because the cost of Seq Scan + Sort (20 rows, 26kB memory) is lower than HNSW traversal overhead for tiny datasets. This is expected PostgreSQL behavior. The index exists, is valid, and will be used once data volume exceeds the planner's cost threshold for index scans.

---

## 4 — Evidence Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Pre-step output | `docs/setup-evidence/P3/STEP-P3-007/runtime-prestep-output.txt` | Raw pre-step health check commands and outputs |
| Benchmark raw | `docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt` | Full benchmark raw output with timing and EXPLAIN ANALYZE |
| Benchmark report | `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md` | Structured benchmark summary |
| Verification report | `docs/setup-evidence/P3/STEP-P3-007/verification.md` | This report (12-section schema) |
| SQL benchmark script | `docs/setup-evidence/P3/STEP-P3-007/benchmark.sql` | Rollback-safe seed/query script; no COMMIT or DDL |
| Shell helpers | `docs/setup-evidence/P3/STEP-P3-007/*.sh` | Pre-step, DB/GUC/vector exploration, benchmark runner, and cleanup helpers; parent-read manually |

---

## 5 — Doc-Sync Impact

| Document | Update Needed | Action |
|----------|---------------|--------|
| `PROGRESS.md` | ✅ Yes | Mark P3-007 [x], update counter to 7/19 |
| `CHECKLIST.md` | ✅ Yes | Mark P3-007 in Section 5.2 |
| `docs/setup-evidence/P3/batch-plan-004-010.md` | ❌ No | Read-only reference; no edits needed |

Updates should be applied by parent orchestrator after auditor PASS.

---

## 6 — Boundary Compliance

| Boundary | Status | Evidence |
|----------|--------|----------|
| No persona drift | ✅ PASS | No persona code/schema touched |
| No consent violation | ✅ PASS | No consent-related data accessed |
| No Y6 / safety boundary bypass | ✅ PASS | Not applicable — runtime benchmark only |
| No HARD STOP bypass | ✅ PASS | Not applicable |
| No Aizanta data/service touched | ✅ PASS | Only read-only `pg_isready` on port 5432 |
| No source/model edits | ✅ PASS | No files in `src/` modified |
| No index creation/drop/rebuild | ✅ PASS | Read-only SELECT/EXPLAIN queries only |
| No persistent rows left | ✅ PASS | ROLLBACK ensures 0 rows remain |
| No secrets exposed | ✅ PASS | No passwords, API keys, or decrypted values printed |
| Resource sharing (VPS < 50%) | ✅ PASS | CPU < 1%, RAM 1.7/15Gi used during benchmark |

---

## 7 — Rollback / Re-run Safety

| Aspect | Detail |
|--------|--------|
| Rollback required | ❌ None — transaction rolled back; no state changes persisted |
| Re-run safety | ✅ Fully idempotent — ROLLBACK ensures no residual data |
| Cleanup | Remove evidence directory (`docs/setup-evidence/P3/STEP-P3-007/`) if re-running |

---

## 8 — Design Decisions / Caveats

### Binding Decisions Applied

| ID | Decision | Applied |
|----|----------|---------|
| BD-04 | HNSW m=16, ef_construction=128 | ✅ Confirmed in both indexes |
| BD-05 | Query ef_search=100 | ⚠️ Tested but not applicable — HNSW index not used at 20-row scale |
| BD-06 | Column is `embedding`, not `embedding_vec` | ✅ Confirmed |
| BD-07 | Column is `raw_content`, not `content` | ✅ Confirmed |

### Key Caveats

1. **Insufficient data volume**: 20 rows per table (40 total) is far too small for meaningful p95 analysis or ef_search sensitivity measurement. PostgreSQL's planner correctly chooses Seq Scan + Sort over HNSW for such tiny datasets. This is documented as a known constraint in the benchmark report.

2. **HNSW index bypassed**: The HNSW index exists and is valid, but is not used by the planner at this data scale. The index will become active once data volume reaches several thousand rows per table.

3. **`hnsw.ef_search` GUC behavior**: The GUC is settable (`SET hnsw.ef_search = N; SHOW hnsw.ef_search;` returns the correct value) but does not appear in `pg_settings` or `SHOW ALL` until explicitly set in the current session. This is a known pgvector 0.8.2 behavior.

4. **No p95 possible**: With only 5 timing samples per ef_search value, a p95 calculation is statistically meaningless. See benchmark-report.md for recommendation.

5. **Vector generation overhead**: Timings include ~0.4ms of overhead from generating a 1536-dim random vector via `generate_series` + `array_agg`. The actual vector comparison time is significantly lower.

6. **Shell LSP unavailable locally**: Directory-level diagnostics attempted to use `bash-language-server`, which is not installed in this environment. Markdown diagnostics are clean, and parent manually read every shell/SQL helper artifact to verify rollback safety, no secrets, no DDL, and no persistent writes.

---

## 9 — Auditor Gate

| Field | Value |
|-------|-------|
| Auditor report path | `docs/setup-evidence/P3/STEP-P3-007/auditor-gate.md` |
| Current verdict | ✅ PASS — independent auditor gate complete |
| Re-audit protocol | If future changes alter P3-007 artifacts, re-run auditor via `task_id` |

---

## 10 — Security Scan

| Check | Result |
|-------|--------|
| No secrets exposed in evidence | ✅ PASS — no passwords, API keys, or decrypted values |
| No type suppression | ✅ PASS — no Python/source type-safety suppression; shell helper artifacts are not typed source and contain no suppression directives |
| No empty catches | ✅ PASS — shell helper artifacts contain no empty catch/error-swallowing blocks |
| No Aizanta data beyond pg_isready | ✅ PASS |
| Connection method: Docker socket trust | ✅ PASS — no password transmission |
| No persistent benchmark rows | ✅ PASS — ROLLBACK ensures cleanup |
| No source code modifications | ✅ PASS |
| No index operations | ✅ PASS |

---

## 11 — Acceptance Criteria Mapping

| AC ID | Description | Status |
|-------|-------------|--------|
| AC-MEM-001 | PostgreSQL + Redis, no SQLite | ✅ PASS — PG 5433 confirmed, pgvector 0.8.2 |
| AC-MEM-002 | Classification metadata on all records | ✅ PASS — episodes table has all classification columns |
| AC-PHASE-007 | P3-007 step verification complete | ✅ PASS — benchmark evidence captured, ef_search documented, caveats recorded |

---

## 12 — Footer

| Field | Value |
|-------|-------|
| **Date** | 2026-06-02 |
| **Author** | Guinevere (Parent Executor) |
| **Step** | P3-007 |
| **Phase** | P3 (Memory System) — batch 2 of ~6 |
| **Evidence root** | `docs/setup-evidence/P3/STEP-P3-007/` |
| **Verdict** | ✅ **PASS** — HNSW smoke benchmark executed with rollback-safe data; ef_search=40/100/200 tested; data volume too small for p95; HNSW index valid but bypassed by planner for 20-row tables; zero rows persisted |
| **Next action** | Parent syncs PROGRESS.md/CHECKLIST.md, marks P3-007 complete, then proceeds to P3-008 |
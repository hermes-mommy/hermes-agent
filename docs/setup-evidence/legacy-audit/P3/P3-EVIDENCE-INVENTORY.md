# P3 Memory System -- Complete Evidence Inventory

**Date:** 2026-06-25
**Agent:** P3 Implementation Audit (read-only subagent)
**Repo:** C:/Users/faizz/guinevere (git main)
**Scope:** All evidence under `docs/setup-evidence/P3/` and `audit-reports/P3/P3-FINAL-AUDIT/`
**Cross-reference targets:** `src/memory/*.py`, `PROGRESS.md`, `CHECKLIST.md`, `src/core/main.py`

---

## 1. Executive Summary

P3 (Memory Foundation) claims 19/19 steps complete across 16 evidence directories, 4 batch plans, 19 research files, and a 12-dimension final audit. The evidence is **voluminous and largely well-structured**. Every step has an auditor-gate.md returning PASS. 15 of 16 directories have verification.md. The codebase (`src/memory/`) contains all claimed modules with 0 LSP errors in core P3 code.

**However, the honesty of evidence degrades across the pipeline:**
- Steps P3-001 through P3-003 and P3-006 through P3-008 have **real VPS runtime evidence** (SSH, psql, alembic commands on live DB).
- Steps P3-004 and P3-005 have **local real execution** (pip installs on Windows, model download) but P3-005 uses mocked API responses for verification.
- Steps P3-009 through P3-015 have **fully deterministic/mocked verification only** -- no live DB writes, no live API calls, no real embedding service interaction. Caveats are honestly documented.
- Steps P3-016-019 have **no verification.md at all** -- only an auditor-gate.md covering the combined batch.

The 2026-06-02 final audit (P3-FINAL-AUDIT.md) declared CONDITIONAL PASS with 5 non-blocking NEEDS REVIEW items. All code is checked in and compiles. The consolidation scheduler is **not auto-wired** in production -- it exists as commented-out code in main.py requiring manual activation.

---

## 2. Evidence Directory Tree

```
docs/setup-evidence/P3/
  batch-plan-001-003.md
  batch-plan-004-010.md
  batch-plan-011-015.md
  batch-plan-016-019.md
  research/                         (19 files -- covers all P3 sub-domains)
  research-004-010/                 (EMPTY -- placeholder only)
  STEP-P3-001/                      (verification.md + auditor-gate.md + 3 verifier reports)
  STEP-P3-002/                      (verification.md + auditor-gate.md + 5 verifier/research files)
  STEP-P3-003/                      (verification.md + auditor-gate.md)
  STEP-P3-004/                      (verification.md + auditor-gate.md + verify script + output)
  STEP-P3-005/                      (verification.md + auditor-gate.md + verify script + output)
  STEP-P3-006/                      (verification.md + auditor-gate.md + runtime-prestep + hnsw output)
  STEP-P3-007/                      (verification.md + auditor-gate.md + benchmark + 12 shell/SQL artifacts)
  STEP-P3-008/                      (verification.md + auditor-gate.md + migration output + FTS output + scripts)
  STEP-P3-009/                      (verification.md + auditor-gate.md + verify script + output + backup-checkpoint)
  STEP-P3-010/                      (verification.md + auditor-gate.md + verify script + output)
  STEP-P3-011/                      (verification.md + auditor-gate.md)
  STEP-P3-012/                      (verification.md + auditor-gate.md)
  STEP-P3-013/                      (verification.md + auditor-gate.md)
  STEP-P3-014/                      (verification.md + auditor-gate.md)
  STEP-P3-015/                      (verification.md + auditor-gate.md)
  STEP-P3-016-019/                  (auditor-gate.md ONLY -- no verification.md)

audit-reports/P3/P3-FINAL-AUDIT/
  P3-FINAL-AUDIT.md                 (overall verdict: CONDITIONAL PASS)
  D01-completeness.md               (COMPLETENESS audit -- 458 lines)
  D02-code-quality.md
  D03-database-integrity.md
  D04-security-secrets.md
  D05-safety-compliance.md
  D06-test-coverage.md
  D07-adr-compliance.md
  D08-architecture-consistency.md
  D09-integration-points.md
  D10-performance-operational.md
  D11-open-items-caveats.md
  D12-p4p5-readiness.md
```

---

## 3. Per-Step Evidence Inventory

### STEP-P3-001 -- Alembic Baseline Setup

| Field | Detail |
|-------|--------|
| **Status** | VERIFIED IMPLEMENTED (re-audit resolved initial FAIL) |
| **evidence\_exists** | YES -- verification.md (5697 bytes), auditor-gate.md, verifier-lsp.md, verifier-migration.md, verifier-safety.md |
| **claim\_type** | **LIVE-DB** -- SSH to VPS, real `alembic upgrade head`, real `ops.alembic_version` table verification |
| **honest?** | YES -- all commands and outputs appear genuine. `alembic current` shows `2bed93fd1dd0 (head)`. |
| **Prior D01 finding** | D01-completeness.md (initial run) claimed FAIL -- "Alembic NOT installed; `src/memory/models.py` missing; no `alembic.ini`". This was resolved by re-audit. Current audit-gate shows 81/81 PASS. |

**Evidence summary:**
- Created `src/memory/models.py` with `Base = declarative_base()` (metadata-only, no tables)
- `alembic/env.py` verified with multi-schema filter for 12 canonical schemas, `version_table_schema="ops"`
- Baseline revision `2bed93fd1dd0` created and applied
- `ops.alembic_version` table confirmed at head
- Aizanta port 5432 isolation verified (separate containers)
- Caveat: `uv run alembic` fails due to hatchling build config; workaround `source .venv/bin/activate && PYTHONPATH=src alembic` documented

---

### STEP-P3-002 -- 47 Table Migration

| Field | Detail |
|-------|--------|
| **Status** | VERIFIED IMPLEMENTED |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md, plus 3 verifier reports + research + backup checkpoint |
| **claim\_type** | **LIVE-DB** -- VPS SSH, real migration run, backup checkpoint verified |
| **honest?** | YES -- 13 audit criteria all PASS with real DB queries. Caveats documented (compression deferred, duplicate operations in manual patch). |

**Evidence summary:**
- Created `src/memory/models.py` with 47 ORM classes across 12 schemas
- Migration `e401bb5fd274_initial_schema_47_tables` created and applied
- DB verified: 47 tables, 12 schemas, 61 indexes, 2 HNSW (m=16, ef=128, cosine_ops), 4 hypertables, 11 FKs
- Compression policies deferred (documented -- requires columnstore enablement first)
- Backup checkpoint `13159f70` (primary S3) and `13c66a7c` (secondary R2) verified
- Aizanta isolation verified (container up 9 days, no restart)

---

### STEP-P3-003 -- Migration Verification

| Field | Detail |
|-------|--------|
| **Status** | VERIFIED IMPLEMENTED |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md |
| **claim\_type** | **LIVE-DB** -- real psql queries, metadata SQL, SELECT 1 on all 47 tables |
| **honest?** | YES -- all 12 verification categories independently confirmed. Tables, indexes, FKs, hypertables, extensions all match. |

**Evidence summary:**
- 12 canonical schemas confirmed
- 47 app tables (48 including ops.alembic_version)
- 61 indexes including 2 HNSW with correct params
- 11 FK constraints valid (3 intentionally removed for hypertable logical references)
- 4 hypertables (episodes, events, audit_trail, transactions)
- pgvector 0.8.2, TimescaleDB 2.27.1
- SELECT 1 on all 47 tables returns OK
- Vector columns 1536-dim on memory.episodes and memory.semantic_facts
- Aizanta PG 5432 container up 9 days, untouched

---

### STEP-P3-004 -- SentenceTransformers Dependency Installation

| Field | Detail |
|-------|--------|
| **Status** | VERIFIED IMPLEMENTED |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md, p3-004-verify.py, verification-output.txt, vps-prestep-output.txt |
| **claim\_type** | **LOCAL** -- installed on local Windows dev machine. VPS health checks done via SSH (public IP). |
| **honest?** | YES -- real pip install output, real model download. Caveats documented (legacy torch cache path mismatch, Windows symlink limitation). |

**Evidence summary:**
- `sentence-transformers>=5.5` installed in local venv (actual version 5.5.1)
- `pyproject.toml` updated with dependency
- `all-MiniLM-L6-v2` model cached at HuggingFace hub path, dimension 384 confirmed
- Model documented as cache-only; no 384-dim vectors written to DB
- Pre-step VPS health checks: all services healthy
- **CRITICAL FINDING**: verification-output.txt is **binary garbled** (UTF-16 BOM encoding) -- the text content is unreadable as plain UTF-8. The verification.md captures the same output in quoted code blocks, so the evidence IS present, just the raw file has encoding issues.
- No P3-005 scope creep (no embeddings.py created)

---

### STEP-P3-005 -- Embedding Pipeline

| Field | Detail |
|-------|--------|
| **Status** | IMPLEMENTED WITH DOC GAPS |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md, verify_embeddings.py, verification-output.txt |
| **claim\_type** | **DRY-RUN / LOCAL** -- code created and verified locally with **mocked API responses** (httpx.MockTransport). No real API call made. |
| **honest?** | YES -- honestly documents "No live API call in verification -- 9Router may not be running locally; verification uses mocked httpx responses." |

**Evidence summary:**
- `src/memory/embeddings.py` created (~580 lines)
- `src/memory/__init__.py` updated with all exports (20 symbols)
- `DEFAULT_MODEL = "openai/text-embedding-3-small"`, `EXPECTED_DIMENSION = 1536`
- `prepare_embedding_text()` privacy preprocessing: Critical rejected (fail-closed), Restricted/Confidential redacted, Public/Internal no redaction
- Manual retry with exponential backoff (6 attempts), not tenacity
- stdlib `_Logger` wrapper, not structlog
- None of the 50 tests calls a real API -- all use `httpx.MockTransport`
- Consent gate: `faiz-consent-embedding-privacy.md` exists with explicit Faiz approval
- 0 LSP errors on all files
- **GAP**: No live integration test with 9Router. The pipeline has never been tested against the actual embedding API. A production deployment would be the first real test.

---

### STEP-P3-006 -- pgvector HNSW Index Verification

| Field | Detail |
|-------|--------|
| **Status** | VERIFIED IMPLEMENTED |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md, runtime-prestep-output.txt, hnsw-verification-output.txt |
| **claim\_type** | **LIVE-DB** -- VPS SSH, real psql queries against Guinevere PostgreSQL 5433 |
| **honest?** | YES -- real index definitions captured, EXPLAIN evidence documented. Empty-table caveat documented (Seq Scan chosen for 0-row episodes table). |

**Evidence summary:**
- Both HNSW indexes confirmed: `ix_episodes_embedding_hnsw` and `ix_semantic_facts_embedding_hnsw`
- Parameters: m=16, ef_construction=128, vector_cosine_ops -- matches ADR-009 and models.py
- No stale `embedding_vec` column or index
- Cosine EXPLAIN: semantic_facts uses Index Scan (HNSW); episodes uses Sort+Result (0 rows -- documented caveat)
- Column is `embedding` (not `embedding_vec`), column is `raw_content` (not `content`) -- confirmed

---

### STEP-P3-007 -- HNSW Parameter Tuning / Benchmark

| Field | Detail |
|-------|--------|
| **Status** | IMPLEMENTED WITH DOC GAPS |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md, benchmark-report.md, hnsw-benchmark-raw.txt, 12 shell/SQL artifacts |
| **claim\_type** | **LIVE-DB** -- VPS rollback-safe benchmark with 20 seed rows per table. Real psql commands. |
| **honest?** | YES -- honestly documents that data volume is too small for meaningful p95, HNSW index bypassed by planner for 20-row tables, ef_search sensitivity not measurable. |

**Evidence summary:**
- Rollback-safe benchmark: 20 episodes + 20 semantic facts seeded inside `BEGIN...ROLLBACK`
- ef_search 40/100/200 tested with EXPLAIN (ANALYZE, BUFFERS) -- 5 runs per value
- All queries used Seq Scan + Sort (HNSW bypassed for 20 rows)
- No persistent rows left -- post-benchmark row count = 0
- ef_search=100 retained as default pending real data (P3-019)
- **GAP**: No meaningful performance data. The benchmark confirms the infrastructure works but provides zero actionable tuning guidance. This is honestly documented.

---

### STEP-P3-008 -- tsvector FTS + do_not_recall Migration

| Field | Detail |
|-------|--------|
| **Status** | VERIFIED IMPLEMENTED |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md, migration-output-raw.txt, fts-verification-output.txt, migration script, verify script |
| **claim\_type** | **LIVE-DB** -- VPS SSH, real alembic revision --autogenerate + upgrade head on VPS |
| **honest?** | YES -- real migration output captured. FTS query returns true. Generated column rollback test shows correct A/B/D weights. |

**Evidence summary:**
- `search_vector` tsvector GENERATED ALWAYS AS STORED with setweight(A=title, B=summary, D=raw_content)
- `do_not_recall` boolean NOT NULL default false
- GIN index `ix_episodes_search_vector_gin` created
- Migration `65f863220922` current head, revises `e401bb5fd274`
- FTS rollback test: generated tsvector correctly shows title ('hello':1A 'world':2A), summary ('summari':5B 'test':4B), raw_content ('everyth':8 'faiz':10)
- Shell scripts use SOPS pattern for password (no plaintext)
- Migration file copied back from VPS as evidence -- local alembic/versions/ is absent

---

### STEP-P3-009 -- Memory Write Pipeline

| Field | Detail |
|-------|--------|
| **Status** | IMPLEMENTED WITH DOC GAPS |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md, verify_write_pipeline.py, verification-output.txt, backup-checkpoint-output.txt, runtime-prestep-output.txt |
| **claim\_type** | **DRY-RUN / LOCAL** -- code created and verified locally with `_FakeAsyncSession`. No live DB write, no live API call. |
| **honest?** | YES -- honestly documents "No live DB insert smoke test", "No live embedding API call", "Pre-step health checks referenced from P3-008". |

**Evidence summary:**
- `src/memory/write_pipeline.py` created with `store_episode()` async, `store_episode_batch()` 
- Uses `EmbeddingService.aembed()` integration via Protocol
- `classification: str = RESTRICTED` default per DataGovernance
- Critical fail-closed guard: requires sanitized summary
- `raw_content` mapping (not `content`), `embedding` column (not `embedding_vec`)
- `do_not_recall=False` default
- 58/58 deterministic tests PASS
- Backup checkpoint `13159f70` verified (referenced from P3-002 evidence)
- 0 LSP errors
- **GAP**: No live DB test. The first production write will be the real test.
- **GAP**: No fresh SSH health check -- referenced same-day P3-008 evidence

---

### STEP-P3-010 -- Memory Read Pipeline

| Field | Detail |
|-------|--------|
| **Status** | IMPLEMENTED WITH DOC GAPS |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md, verify_read_pipeline.py, verification-output.txt |
| **claim\_type** | **DRY-RUN / LOCAL** -- code created and verified locally with `_FakeRecallSession` and `_FakeEmbedder`. No live DB/oracle call. |
| **honest?** | YES -- honestly documents "No live DB query smoke test", "No live embedding API call". |

**Evidence summary:**
- `src/memory/read_pipeline.py` created with `recall_memories()` async (733 lines)
- Hybrid ranking: vector cosine + FTS (search_vector) + recency (90d half-life) + importance
- RRF fusion with k=60
- Safety gates: DNR exclusion (WHERE clause), classification ceiling per principal, safe-mode Critical substitution, 4K token budget
- Return fields: id, safe_content, classification, importance, created_at, combined_score, is_summarized
- 88/88 deterministic tests PASS
- 0 LSP errors
- **GAP**: No live DB query ever executed. The hybrid ranking algorithm has never been tested against real PostgreSQL with real data.
- **GAP**: RRF fusion uses vector and FTS signal ranks only -- recency and importance are multiplicative factors, not rank inputs (deferred to P3-011)
- **GAP**: Token budget estimation is approximate (`len(text) // 4`) -- no tiktoken

---

### STEP-P3-011 -- Hybrid Ranking Tuning

| Field | Detail |
|-------|--------|
| **Status** | IMPLEMENTED WITH DOC GAPS |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md |
| **claim\_type** | **DRY-RUN / LOCAL** -- code modifications locally tested with deterministic tests (43 tests). No live DB. |
| **honest?** | YES -- documents caveats: no golden dataset, recency boost applies to started_at. |

**Evidence summary:**
- Constants added: VECTOR_WEIGHT=0.5, FTS_WEIGHT=0.5, BOTH_SIGNAL_BONUS=1.25, RECENCY_MAX_BOOST=0.10, MAX_CANDIDATE_POOL=200
- `compute_rrf_score()` returns `(score, num_signals)` tuple with weighted formula
- Both-signal bonus (1.25x) applied when vector + FTS both detect an episode
- Recency bounded to max 10% boost
- Candidate pool bound to max 200
- `classification_level()` helper: unknown/null maps to level 5 (fail-closed beyond Critical)
- 9 private helpers renamed to public for testability
- 43/43 tests PASS, diagnostics clean
- 0 LSP errors
- **GAP**: Weights are plan defaults -- no ablation study or golden dataset
- **GAP**: No live DB verification of ranking behavior

---

### STEP-P3-012 -- Context Injection

| Field | Detail |
|-------|--------|
| **Status** | IMPLEMENTED WITH DOC GAPS |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md |
| **claim\_type** | **DRY-RUN / LOCAL** -- code modifications locally tested with 18 unit tests (synthetic data + monkeypatching). No live DB. |
| **honest?** | YES -- documents structlog resolution warnings pre-existing, system_prompt.md not in local workspace. |

**Evidence summary:**
- `src/core/services/prompt_loader.py` modified (47 to 182 lines)
- `get_system_prompt_with_context()` accepts `list[dict[str, object]]`, `list[str]`, or None
- `assemble_system_prompt_with_memory()` resolves safe_mode from `HardStopHandler.is_safe` (authoritative) or passed param
- `exclude_dnr=True` hardcoded -- no caller override
- Default top-k = 3, default token budget = 4000
- `safe_content` only -- `raw_content` never referenced in prompt_loader
- `ReadPipelineSafetyError` is caught and returns base prompt + mood (discardable)
- 18/18 tests PASS
- **GAP**: No integration test with real `read_pipeline.py` -- all wiring is mocked
- **GAP**: `test_logger_called_with_metadata_only` has narrow scope (auditor noted)

---

### STEP-P3-013 -- Do-Not-Recall Hardening/API

| Field | Detail |
|-------|--------|
| **Status** | IMPLEMENTED WITH DOC GAPS |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md |
| **claim\_type** | **DRY-RUN / LOCAL** -- code created locally, 32 tests with fake sessions. No live DB. |
| **honest?** | YES -- documents caveats: ConsentLedger cross-reference deferred, content-hash dedup deferred, Prometheus counters deferred. |

**Evidence summary:**
- `src/memory/dnr.py` created (418 lines) with `mark_memory_dnr()`, `unmark_memory_dnr()`, `is_memory_dnr()`, `verify_recall_results_dnr_free()`
- Authorization: only `guinevere_core` can mark/unmark (5 unauthorized principals tested)
- Metadata-only audit events: `reason_hash` (SHA-256 prefix) + `reason_length` stored, never raw reason
- Event constants: `MEMORY_DNR_MARKED`, `DNR_REVOKED`
- Pre-injection guard: `verify_recall_results_dnr_free()` fails closed on `do_not_recall=True` (bool or string)
- Query-level DNR filters preserved in all three query builders
- 32/32 focused tests + 93/93 regression PASS
- **GAP**: `ConsentLedger` cross-reference (Layer 1) not implemented -- DNR relies on column filter (Layer 2) + guard (Layer 5)
- **GAP**: No content-hash dedup for DNR events
- **GAP**: Fake session accesses SQLAlchemy `_where_criteria` private API (brittle)

---

### STEP-P3-014 -- Safe-Mode Memory Gate

| Field | Detail |
|-------|--------|
| **Status** | IMPLEMENTED WITH DOC GAPS |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md |
| **claim\_type** | **DRY-RUN / LOCAL** -- code modifications locally tested with 64 tests. No live DB. |
| **honest?** | YES -- documents caveats: substring matching in content-type detection, no DB-level safe-mode ceiling, Prometheus not deployed. |

**Evidence summary:**
- `build_safe_content()` rewritten for all classification levels in safe mode
- `_is_safe_mode_blocked_content()`: detects emotional, surveillance, persona-escalation content via tags/episode_type/source
- `_resolve_ceiling()`: safe-mode classification ceiling downgrade (core→Internal, subagent→Public, default→Public)
- `recall_memories()` updated to use `_resolve_ceiling()` when `safe_mode=True`
- Safe-mode constants exported: `SAFE_MODE_RESTRICTED_PLACEHOLDER`, `SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER`
- 64/64 focused tests + 213/213 regression PASS
- 0 LSP errors
- **GAP**: No DB-level classification ceiling in SQL WHERE clause (Python post-processing only)
- **GAP**: `tags`/`episode_type`/`source` are optional fields -- detection relies on `getattr` defensive access
- **GAP**: Substring matching in list/tuple tag conversion could cause false positives

---

### STEP-P3-015 -- Daily Consolidation Job

| Field | Detail |
|-------|--------|
| **Status** | PARTIALLY IMPLEMENTED (scheduler NOT auto-wired in production) |
| **evidence\_exists** | YES -- verification.md, auditor-gate.md |
| **claim\_type** | **DRY-RUN / LOCAL** -- consolidation module created, 50 tests with fake sessions. Scheduler registration tested via APScheduler v3 `AsyncIOScheduler` in unit tests. |
| **honest?** | YES -- documents the critical caveat: `register_consolidation_job()` requires active `AsyncIOScheduler` + async DB sessionmaker, which does NOT exist in production. Only commented-out code in main.py. |

**Evidence summary:**
- `src/memory/consolidation.py` created (757 lines)
- `register_consolidation_job()` schedules `daily_consolidation` at 03:00 Asia/Bangkok via APScheduler v3 `CronTrigger`
- `register_decay_job()` also exists (P18 forgetting curve)
- DNR episodes excluded from consolidation
- Safe-word/crisis/formal-hold/distress records skipped
- Provenance (`source_episode` UUID) preserved
- Highest classification preserved
- Idempotent via SHA-256 `make_content_key()` dedup
- Pruning: default mode `archive` (non-destructive); dry-run and soft-delete available
- 50/50 tests + 263/263 regression PASS
- **CRITICAL FINDING**: `register_consolidation_job` is **commented out** in `src/core/main.py` (lines 29, 32). The scheduler is NOT running in production. Activation requires manual wiring during deployment:
  ```python
  # from src.memory.consolidation import register_consolidation_job
  # scheduler = AsyncIOScheduler()
  # await register_consolidation_job(scheduler, session_factory=AsyncSessionLocal)
  # scheduler.start()
  ```
- **MEDIUM FINDING**: `_fact_exists_by_key` iterates all facts (O(n)). No `content_hash` column with unique constraint for O(1) dedup.
- **GAP**: No `systemctl` service integration for scheduler

---

### STEP-P3-016 through STEP-P3-019 -- Memory Commands, E2E, Benchmark

| Field | Detail |
|-------|--------|
| **Status** | IMPLEMENTED WITH DOC GAPS |
| **evidence\_exists** | **PARTIAL** -- auditor-gate.md ONLY. NO verification.md exists. |
| **claim\_type** | **DRY-RUN / LOCAL** -- code created locally. E2E tests use `FakeSession`. Benchmark has dry-run mode. Discord commands cannot be tested without live bot. |
| **honest?** | YES -- auditor report honestly documents pre-existing issues, test limitations. But the missing verification.md is a structural gap for a combined 4-step batch. |

**Evidence summary:**
- `src/discord/cmd_memory_search.py` created (493 lines) -- Faiz-only guard, DNR exclusion hardcoded, `safe_mode=False` hardcoded
- `src/discord/cmd_memory_add.py` created (487 lines) -- classification default Restricted, WritePipelineCriticalError handled
- `src/discord/bot.py` modified -- both commands registered, `get_session_factory()` method added
- `tests/memory/test_memory_e2e.py` created (1006 lines) -- 28 tests covering write→recall→inject→verify chain
- `scripts/bench_memory.py` created (760 lines) -- dry-run + live-DB modes, ADR-009 targets: vector p95 < 2s, FTS < 500ms, hybrid < 3s
- All 5 files audited by auditor: 3 E2E patterns clean, 0 new type suppressions, 0 empty catches
- Benchmark dry-run shows all targets within ADR-009 range
- **GAP**: No verification.md. The only evidence is the auditor-gate.md, which is an independent review but not the implementation evidence normally documented in verification.md.
- **GAP**: Discord commands cannot be integration-tested without live bot deployment
- **GAP**: Pre-existing `# type: ignore[assignment]` in bot.py:31 (dynamic discord import) -- documented, not introduced by P3

---

## 4. Claim Type Summary Table

| Step | Claim Type | Live API Call? | Live DB Write? | Live VPS? | Honest? |
|------|-----------|---------------|----------------|-----------|---------|
| P3-001 | LIVE-DB | N/A | YES (alembic upgrade) | YES | YES |
| P3-002 | LIVE-DB | N/A | YES (47 tables) | YES | YES |
| P3-003 | LIVE-DB | N/A | NO (read-only) | YES | YES |
| P3-004 | LOCAL | NO | NO | YES (pre-step) | YES |
| P3-005 | DRY-RUN | **NO** (mocked) | NO | NO | YES |
| P3-006 | LIVE-DB | N/A | NO (read-only) | YES | YES |
| P3-007 | LIVE-DB | N/A | YES (rollback-only) | YES | YES |
| P3-008 | LIVE-DB | N/A | YES (DDL migration) | YES | YES |
| P3-009 | DRY-RUN | **NO** (mocked) | **NO** (fake session) | NO | YES |
| P3-010 | DRY-RUN | **NO** (mocked) | **NO** (fake session) | NO | YES |
| P3-011 | DRY-RUN | NO | NO | NO | YES |
| P3-012 | DRY-RUN | NO | NO | NO | YES |
| P3-013 | DRY-RUN | NO | **NO** (fake session) | NO | YES |
| P3-014 | DRY-RUN | NO | NO | NO | YES |
| P3-015 | DRY-RUN | NO | **NO** (fake session) | NO | YES |
| P3-016 | DRY-RUN | NO | NO | NO | YES |
| P3-017 | DRY-RUN | NO | NO | NO | YES |
| P3-018 | DRY-RUN | NO | **NO** (fake session) | NO | YES |
| P3-019 | DRY-RUN | NO | NO | NO | YES |

---

## 5. Cross-Reference: PROGRESS.md vs CHECKLIST.md

### PROGRESS.md
- All 19 P3 steps marked `[x]` with implementation descriptions and evidence references
- P3 step descriptions are detailed (lines 163-181) -- includes evidence paths and auditor verdicts
- The completion counter at the time was corrected from conflicting 85/81 values to 90/257 (final audit fix F1/F2)

### CHECKLIST.md
- P3-001 through P3-015 in Section 5.2: all marked `[x]` with evidence paths
- P3-016 through P3-019: all marked `[x]` (final audit fix F3 changed `[ ]` to `[x]`)
- However, Sections 5.1 (Prerequisites), 5.3 (Integration Tests), 5.4 (Security Checks), 5.5 (Rollback Test), 5.6 (Phase Complete) -- all remain `[ ]` unchecked
- **Discrepancy**: 20+ checklist items in sections 5.1-5.6 remain unchecked despite P3 being declared complete

---

## 6. Critical Findings

### [CRITICAL] Consolidation Scheduler NOT Running in Production
**File:** `src/core/main.py:26-33`
- `register_consolidation_job()` and `register_decay_job()` are both COMMENTED OUT
- The activation code exists only as Python comments with instructions
- No `AsyncIOScheduler` is started during application lifespan
- The daily consolidation at 03:00 WIB will NEVER run unless manually wired during deployment
- Impact: P3-015 is unit-tested but functionally dead in production

### [HIGH] P3-005 Embedding Pipeline Never Tested Against Real API
**File:** `docs/setup-evidence/P3/STEP-P3-005/verification.md` (caveat 1)
- All 50 verification tests use `httpx.MockTransport` -- the pipeline has never sent a single real request to 9Router/OpenRouter
- The `prepare_embedding_text()` redaction logic has never been tested with real API responses
- The retry/backoff logic has never been exercised against real rate limits or timeouts
- First real call will happen in production -- risk for integration issues

### [HIGH] P3-009/P3-010 Write/Read Pipelines Never Tested Against Real Database
**Files:** `docs/setup-evidence/P3/STEP-P3-009/verification.md` (caveat 1), `STEP-P3-010/verification.md` (caveat 1)
- Both pipelines use `_FakeAsyncSession` / `_FakeRecallSession` -- zero real DB interactions
- The ORM mappings, column types, embedding storage/retrieval have never been validated against actual PostgreSQL
- The hybrid ranking queries have never been executed against a real database with real data
- Risk: silent ORM mapping errors, type conversion issues, query syntax problems uncovered on first production use

### [HIGH] P3-016-019 Missing verification.md
**Directory:** `docs/setup-evidence/P3/STEP-P3-016-019/`
- The combined batch covering 4 steps has NO verification.md
- Only auditor-gate.md exists (which validates the implementation but is not the implementation's own evidence)
- The D01 final audit flagged this as NEEDS REVIEW and it was never resolved
- The prior final audit also flagged that the combined folder structure makes individual step verification impossible to verify independently

---

## 7. Medium Findings

### [MEDIUM] P3-001 Initial FAIL vs Final PASS -- Unclear Resolution Path
- D01-completeness.md claimed P3-001 had FAIL (8 critical failures), but current evidence shows PASS (81/81)
- The resolution path is not documented -- how was P3-001 fixed? Was there a re-implementation? A re-audit?
- The initial FAIL may have been based on an earlier read (before P3-002 subsumed it), but the documents don't explain the transition
- Conclusion: evidence exists and looks genuine, but the audit trail of how FAIL became PASS is lost

### [MEDIUM] P3-004 verification-output.txt Binary Garbled
**File:** `docs/setup-evidence/P3/STEP-P3-004/verification-output.txt`
- The file is encoded in UTF-16 with BOM; most content renders as garbled binary in a UTF-8 viewer
- The same content is present in verification.md as quoted code blocks, so no information is lost
- Cosmetic issue but indicates the verification script output was captured from a PowerShell pipeline without encoding consideration

### [MEDIUM] Empty research-004-010/ Directory
**Directory:** `docs/setup-evidence/P3/research-004-010/`
- Created as a placeholder but never populated
- The research/ directory has 19 files covering all domains, so no research gaps exist
- This appears to be an abandoned organizational artifact

### [MEDIUM] P3-003 Verify Step Claims Compression Deferral is "Documented"
- The P3-003 verification passes compression deferral as "accepted per P3-002 design decision"
- As of P3 completion, compression policies for memory.episodes (14-day) and surveillance.events (7-day) are STILL deferred
- This was never addressed in any subsequent P3 step -- it remains an open operational concern

### [MEDIUM] 20+ CHECKLIST.md Items Still Unchecked
- Sections 5.1 (Prerequisites), 5.3 (Integration Tests), 5.4 (Security Checks), 5.5 (Rollback Test), 5.6 (Phase Complete) all remain unchecked
- No evidence these were ever reviewed or considered during the P3 final audit
- The final audit D01 flagged this as NEEDS REVIEW and the fix only covered 5.2 step items

---

## 8. Status Verdict by Step

| Step | Verdict | Rationale |
|------|---------|-----------|
| P3-001 | VERIFIED IMPLEMENTED | Real VPS commands, live DB. Prior FAIL resolved. |
| P3-002 | VERIFIED IMPLEMENTED | Real migration, real DB verification. Compression deferred. |
| P3-003 | VERIFIED IMPLEMENTED | Real live-DB queries, all 12 categories PASS. |
| P3-004 | VERIFIED IMPLEMENTED | Real local install + VPS health checks. Binary garbled output cosmetic. |
| P3-005 | IMPLEMENTED WITH DOC GAPS | Code exists, tests pass, but no real API call ever made. Consent gate documented. |
| P3-006 | VERIFIED IMPLEMENTED | Real VPS verification of existing indexes. |
| P3-007 | IMPLEMENTED WITH DOC GAPS | Real VPS benchmark but data too small for meaningful results. Honest caveats. |
| P3-008 | VERIFIED IMPLEMENTED | Real VPS migration, FTS verification. |
| P3-009 | IMPLEMENTED WITH DOC GAPS | Code exists, 58/58 tests, but no live DB or API interaction. |
| P3-010 | IMPLEMENTED WITH DOC GAPS | Code exists, 88/88 tests, but no live DB or API interaction. |
| P3-011 | IMPLEMENTED WITH DOC GAPS | Code modifications tested locally. No real DB ranking verification. |
| P3-012 | IMPLEMENTED WITH DOC GAPS | Code modifications tested locally. No integration test with real read_pipeline. |
| P3-013 | IMPLEMENTED WITH DOC GAPS | DNR module complete with audit events. ConsentLedger cross-ref deferred. |
| P3-014 | IMPLEMENTED WITH DOC GAPS | Safe-mode logic complete. DB-level ceiling deferred. |
| P3-015 | PARTIALLY IMPLEMENTED | Consolidation module complete and tested. **BUT scheduler is NOT wired in production** -- only commented-out code in main.py. |
| P3-016 | IMPLEMENTED WITH DOC GAPS | Command created, wired, but cannot live-test without bot deployment. |
| P3-017 | IMPLEMENTED WITH DOC GAPS | Same as P3-016. |
| P3-018 | IMPLEMENTED WITH DOC GAPS | E2E test suite created (28 tests), but uses fake sessions. |
| P3-019 | IMPLEMENTED WITH DOC GAPS | Benchmark script created with dry-run and live-DB modes. Verified in dry-run only. |

---

## 9. Final Audit Verdict Reconciliation

The 2026-06-02 final audit (P3-FINAL-AUDIT.md) gave an overall CONDITIONAL PASS with 161/177 checks passing (91.0%). The 5 remaining NEEDS REVIEW items were:

| NR# | Description | Status as of 2026-06-25 |
|-----|-------------|------------------------|
| NR-1 | StepPrompts.md P3 sections stale (5/5 show "Not Started") | STILL OPEN -- no evidence of update |
| NR-2 | 3 of 4 batch plans lack per-step verification scaffolds | STILL OPEN -- process retro item |
| NR-3 | alembic.ini and migration files exist only on VPS | STILL OPEN -- deployment concern |
| NR-4 | Consolidation scheduler not auto-wired in main.py | STILL OPEN -- confirmed still commented out |
| NR-5 | .gitignore missing `.env*` and `age-key*` patterns; no monitoring/runbooks | STILL OPEN -- .gitignore modified per git status but not verified for specific patterns |

**None of the 5 NR items have been resolved since the final audit.** However, the final audit already classified all 5 as non-blocking for P4/P5, so this is expected.

---

## 10. Recommendations for Mama (NO CODE FIXES)

1. **Review P3-015 activation plan**: The consolidation and decay schedulers need to be wired into main.py startup before they have any effect. This is a deployment decision -- wire during P4/P5 deployment or accept it as intentionally deferred.

2. **Consider live integration smoke test for P3-005**: Before the embedding pipeline is used in production, perform one real end-to-end test against 9Router to validate the HTTP client, retry logic, and dimension validation against actual API behavior.

3. **Resolve P3-016-019 verification.md gap**: Either create a verification.md for the combined folder or add per-step evidence files.

4. **Address CHECKLIST.md unchecked sections**: Sections 5.3-5.6 contain 20+ items that remain unchecked despite P3 being declared complete. These should be reviewed and either satisfied or documented as intentionally deferred.

5. **Consider the compression policy deferral**: Originally deferred in P3-002 for later migration. It remains unresolved as of P3 completion. Decide if this should be addressed in a future phase.

6. **Note the P3-001 FAIL-to-PASS transition is undocumented**: The initial audit found 8 critical failures; the final evidence shows all pass. The resolution steps are not captured in any evidence file.

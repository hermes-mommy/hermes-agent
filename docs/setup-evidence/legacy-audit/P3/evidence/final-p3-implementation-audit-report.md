# ⚠️ HISTORICAL PRE-P19 SNAPSHOT — SEE CURRENT REBASELINE

> **This report is a HISTORICAL PRE-P19 SNAPSHOT (dated 2026-06-25).**
> It is stale because P19 production schema was deployed on 2026-06-27.
> **Current live truth:** [`p3-post-p19-live-rebaseline.md`](p3-post-p19-live-rebaseline.md)
> **Bug reclassification:** [`p3-post-p19-bug-reclassification.md`](p3-post-p19-bug-reclassification.md)
> **Supersession details:** [`p3-historical-pre-p19-supersession-note.md`](p3-historical-pre-p19-supersession-note.md)

---

# P3 (Memory Foundation) -- FINAL IMPLEMENTATION AUDIT REPORT

**Audit Date:** 2026-06-25
**Agent:** Final synthesis subagent (read-only)
**Repo:** C:/Users/faizz/guinevere (git main, commit 63c5285)
**Scope:** Full P3 Memory Foundation implementation audit -- 8 wave-1 dimensions, bug register (67 items), missing-docs register (34 items), downstream dependency matrix, source-map reality check, runtime readiness assessment, evidence inventory
**Read-only affirmation:** YES. No runtime code was modified. No DB was accessed. No migrations run. No secrets printed. No docs edited except this single output file.

---

## 1. Executive Summary

P3 Memory Foundation is **substantially implemented** in source code. The core pipeline -- write (`store_episode`, `store_episode_batch`), read (`recall_memories` with 5-signal hybrid RRF fusion), embedding (`EmbeddingService` with httpx, 1536-dim, ADR-009 compliant), DNR (SQL-level exclusion + post-hoc marking + authorization), and consolidation (`consolidate_episodes_to_facts` with KG ingestion hook and FSRS review) -- all exist as real, wired, non-trivial implementations with protocol-based typing and zero `# type: ignore` in core modules.

**However, P3 has six structural gaps that prevent it from being a clean "verified implemented" pass:**

1. The **consolidation/decay scheduler is dead code** in production -- both `register_consolidation_job` and `register_decay_job` are commented out in `src/core/main.py`. Daily episodic-to-semantic consolidation has never run. The semantic memory layer is dormant.

2. The **DNR pre-injection gate** (`verify_recall_results_dnr_free`) is defined, exported, and tested but **never called at runtime**, and the result dicts it would inspect **lack the `do_not_recall` key** anyway. SQL WHERE is the sole defense.

3. The **primary write path** (`HermesMemoryBridge.store_conversation`) passes `embedding_service=None`, meaning every episode written by the Hermes conversational agent has `embedding = NULL`. The dual-signal RRF fusion is single-signal (FTS-only) for the main write path.

4. **P19 project isolation is incomplete**: `store_episode_batch` does not forward `project_id`; `SemanticFacts` and `KnowledgeGraph` ORM models lack `project_id` columns; `consolidate_episodes_to_facts` has zero project awareness. KG recall leaks across projects.

5. **HARD STOP safe_mode never reaches memory recall** in the life-kernel graph. The `observe_node` executes before `decide_node` detects HARD STOP, so full-content memory is recalled without safe-mode substitution during safety-critical moments.

6. **All 235 memory tests use FakeSession/AsyncMock** -- zero live-DB coverage. The embedding pipeline has never hit a real API. The HNSW benchmark ran on 20 rows where the index was never used.

**Bottom line for mama:** P3 is implemented, documented, safe-at-the-SQL-layer, and architecturally sound. But it has never been integration-tested against a real database or embedding API, the consolidation engine is dormant, and the defense-in-depth DNR gate is doubly broken (not called + missing key). P3 can serve as the foundation for P19/P22/P23/P24 **only if** the six structural gaps above are addressed first. The downstream compatibility audit found 3 CRITICAL blockers and 4 HIGH items that will cause silent data leaks if P19 proceeds without fixing P3's project_id and consolidation surfaces.

**Finding counts:**
| Severity | Count |
|---|---|
| CRITICAL | 6 |
| HIGH | 12 |
| MEDIUM | 14 |
| LOW | 23 |
| COSMETIC | 12 |
| **TOTAL** | **67** |

---

## 2. Final Status

### Composite Verdict: **IMPLEMENTED WITH BUGS**

**Justification by surface:**

| Surface | Sub-Verdict | Key Issue |
|---|---|---|
| ORM models (48 tables / 12 schemas) | VERIFIED IMPLEMENTED | Stale docstring (47 vs 48), 19+ columns in DB but not in ORM |
| DB session factory (db.py) | VERIFIED IMPLEMENTED | Clean async session with pool |
| Embedding pipeline (EmbeddingService) | VERIFIED IMPLEMENTED | ADR-009 compliant, httpx-based, 1536-dim, but never tested against real API |
| Write pipeline (store_episode) | IMPLEMENTED WITH BUGS | store_episode_batch loses project_id; no classification validation on non-Critical; broad except masks config errors |
| Read pipeline (recall_memories + RRF) | IMPLEMENTED WITH BUGS | verify_recall_results_dnr_free not called; broad except on embedding fallback; result dicts lack do_not_recall key |
| DNR (mark/unmark/verify) | VERIFIED IMPLEMENTED (with critical gap) | SQL-level DNR is solid; pre-injection gate doubly broken |
| Safe-mode / HARD STOP | PARTIALLY IMPLEMENTED | safe_mode never reaches life-kernel recall during HARD STOP |
| Context injection (prompt_loader) | PARTIALLY IMPLEMENTED | ContextCompactor may include sensitive content in summaries; dual token budget inconsistent |
| Consolidation scheduler | DOCS CLAIM ONLY / NOT PROVEN | Commented out in main.py; never started at runtime |
| Performance benchmarks | DOCS CLAIM ONLY / NOT PROVEN | 20-row HNSW benchmark never exercised target index |
| Downstream P19/P20 compatibility | IMPLEMENTED WITH BUGS | 3 CRITICAL + 4 HIGH items (project_id, safe_mode, consolidation) |
| Evidence/docs consistency | IMPLEMENTED WITH DOC GAPS | 34 missing-docs register items; stale D01 references |
| Test coverage | PARTIALLY IMPLEMENTED | 235 tests all FakeSession; zero live-DB |

The composite verdict is **IMPLEMENTED WITH BUGS** because the code works correctly at the SQL/Pipeline level for its documented scope, but has 6 CRITICAL bugs (doubly-broken DNR gate, dead consolidation scheduler, lost project_id in batch writes, missing ORM columns for KG facts, missing btree indexes, and result dicts missing do_not_recall key) and 12 HIGH bugs (safe_mode propagation, ORM drift, embedding null on main write path, batch atomicity, no live-DB tests, benchmark not meaningful, broad except masking, etc.).

---

## 3. Reconciliation of 7 Known Points

### 3.1 P3-004 (MiniLM 384-dim) vs P3-005 (1536-dim) dimension consistency

**RESOLVED -- CONSISTENT.** P3-004 is explicitly "cache evidence only; no vector column writes." P3-005 uses `DEFAULT_MODEL = "openai/text-embedding-3-small"` with `EXPECTED_DIMENSION = 1536` via 9Router-native HTTP. The P3-005 verification includes a test that 384-dim vectors raise `DimensionMismatchError`. No contradiction. MiniLM is dead weight for memory but documented as such.

**Evidence:** `evidences-docs-consistency-audit.md` section 2.2.

### 3.2 P3-006/P3-007 HNSW tiny-data benchmark honesty

**RESOLVED -- HONEST BUT EMPIRICALLY EMPTY.** P3-007 benchmark ran on 20 rows per table (40 total) inside `BEGIN...ROLLBACK`. The PostgreSQL planner correctly chose Seq Scan + Sort for all queries. The HNSW index was never used. The benchmark report is **transparent** about this limitation and marks p95 as "not meaningful." However, the "PASS" verdict is misleading -- a benchmark that cannot exercise its target index does not validate performance. The required re-benchmark at P3-019 has no evidence of execution.

**Evidence:** `D10-performance-benchmark-validity.md` findings FND-PERF-001 and FND-PERF-002.

### 3.3 P3-009/P3-010 fake sessions / no live DB

**RESOLVED -- CONSISTENT AND HONEST.** Both steps transparently document "No live DB insert/query smoke test" and "uses fake async session." The P3 FINAL AUDIT catalogues these as 3 of 36 caveats. All 235 memory tests use FakeSession/AsyncMock. No attempt was made to claim live verification. This is a test coverage gap, not a fraud finding.

**Evidence:** `evidences-docs-consistency-audit.md` section 4.2.

### 3.4 P3-015 consolidation scheduler wiring

**CONFIRMED NOT WIRED.** `register_consolidation_job` and `register_decay_job` are entirely commented out in `src/core/main.py:23-38`. Grep across entire `src/` tree confirms zero active call sites. The KG ingestion scheduler (P16) IS wired and running (same file, line 119/167), proving the pattern works. The consolidation scheduler was deliberately excluded. This means daily episodic-to-semantic consolidation has **never run** in any environment. The KG ingestion pipeline (P16) receives zero input from consolidation. FSRS decay sweep never runs. This is the single most impactful deployment gap in P3.

**Evidence:** `P3-AUDIT-ARCH-IMPLEMENTATION.md` finding [CRITICAL]; `P3-SOURCE-MAP.md` section 6; `P3-runtime-readiness.md` finding [CRITICAL].

### 3.5 P19 project_id support in P3

**PARTIALLY IMPLEMENTED.** The `Episodes` ORM already has `project_id` + `project_scope` (models.py:179-187), and all three query builders already filter by `project_id`. The `store_episode()` function accepts `project_id`/`project_scope` parameters. The `p18_adapter` already forwards `project_id` to `recall_memories`.

**HOWEVER:** (a) `SemanticFacts` and `KnowledgeGraph` ORM classes lack `project_id`/`project_scope` columns entirely. (b) `store_episode_batch()` does NOT forward `project_id` to `store_episode()`. (c) `consolidate_episodes_to_facts()` has zero project awareness. (d) P19 migration `p19_001` adds `project_id` to the DB DDL for several tables but the ORM models were not updated to match. The P19 research was written from a stale snapshot claiming zero columns.

**Evidence:** `P3-DOWNSTREAM-COMPATIBILITY-P19-P24.md` findings FINDING-P19A, FINDING-P19B, FINDING-P19C.

### 3.6 P18/P20 supersession of P3

**RESOLVED -- P3 IS EXTENDED, NOT SUPERSEDED.** P18 adds tiered decay, FSRS-6, and a 5th RRF signal on top of P3's read/write pipeline. P20 adds the life-kernel domain consuming P18 adapters that call P3 recall. P19 adds project namespace columns. None of these replace P3's core functions. P3 remains the foundation that all downstream phases depend on.

**Evidence:** `evidences-docs-consistency-audit.md` section 9.

### 3.7 19/19 steps -- real completion or not?

**19/19 steps are CODE-COMPLETE but with varying verification quality.** CHECKLIST.md and PROGRESS.md both mark all 19 steps `[x]`. All 16 step directories have auditor-gate.md with PASS. 15 of 16 have verification.md. However:
- Steps P3-001 through P3-003, P3-006 through P3-008 have **real VPS runtime evidence** (SSH, psql, alembic on live DB)
- Steps P3-004, P3-005 have **local real execution** but P3-005 uses mocked API responses
- Steps P3-009 through P3-015 have **fully deterministic/mocked verification only** -- no live DB writes, no live API calls
- Steps P3-016-019 have **no verification.md at all** -- only auditor-gate.md

The 19/19 claim is honest but shallow -- code is implemented and unit-tested against fake sessions, but the live integration path has never been exercised.

**Evidence:** `P3-EVIDENCE-INVENTORY.md` section 4 (Claim Type Summary Table).

---

## 4. Critical / High Bug Summary (Top 15)

### CRITICAL (6 items)

| ID | Title | File:Line |
|---|---|---|
| BUG-001 | `verify_recall_results_dnr_free()` never called at runtime | `src/memory/dnr.py:385`, `src/memory/__init__.py:81` |
| BUG-002 | Consolidation scheduler commented out in production startup | `src/core/main.py:23-38` |
| BUG-003 | `store_episode_batch` loses project_id / project_scope | `src/memory/write_pipeline.py:260-275` |
| BUG-004 | SemanticFacts and KnowledgeGraph ORM lack project_id columns | `src/memory/models.py:208-263`, `:391-405` |
| BUG-005 | Four btree DESC indexes declared in ORM missing from all migration DDL | `src/memory/models.py:94-95,541,618,1081` |
| BUG-006 | DNR result dicts lack `do_not_recall` key -- gate would not work even if called | `src/memory/read_pipeline.py:769-777`, `src/memory/dnr.py:406` |

### HIGH (12 items)

| ID | Title | File:Line |
|---|---|---|
| BUG-007 | safe_mode never reaches memory recall during HARD STOP in life-kernel | `src/life_kernel/graph.py:247`, `src/life_kernel/p18_adapter.py:92-97` |
| BUG-008 | Consolidation has zero project_id awareness | `src/memory/consolidation.py:275-282`, `:387-397` |
| BUG-009 | SessionSummary ClassificationMetaMixin columns missing from migration DDL | `src/memory/models.py:190`, `alembic/versions/p5_024_add_session_summaries.py` |
| BUG-010 | 19+ columns across 10+ tables exist in DB DDL but have no ORM representation | `src/memory/models.py` (multiple), various migrations |
| BUG-011 | HermesMemoryBridge write path does not compute embeddings (embedding_service=None) | `src/hermes/_memory_bridge.py:278-303` |
| BUG-012 | Batch write lacks transaction atomicity (partial failure risk) | `src/memory/write_pipeline.py:245-277` |
| BUG-013 | Query embedding dimension not validated before DB query -- silent degradation | `src/memory/read_pipeline.py:888-895` |
| BUG-014 | No classification validation on write when embedding is skipped | `src/memory/write_pipeline.py:111-237` |
| BUG-015 | Broad `except Exception` on embedding fallback masks configuration errors | `src/memory/read_pipeline.py:891-895` |
| BUG-016 | P3-007 benchmark executed on 20 rows -- HNSW never exercised | `docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt:36-52` |
| BUG-017 | All 235 memory tests use FakeSession/AsyncMock -- no real DB E2E | `tests/memory/test_memory_e2e.py:10` |
| BUG-018 | KG facts leak across projects due to missing project_id | `src/memory/models.py:208-263`, `:391-405` |

---

## 5. Downstream Impact Verdict

| Phase | Impact | Blocker? |
|---|---|---|
| **P4 (Persona)** | INDEPENDENT -- reads persona tables via FSM, not P3 pipeline. No P3 blockers. | NO |
| **P5 (Agent Loop)** | FULLY SUPPORTED via HermesMemoryBridge. HermesMemoryBridge write path has embedding_service=None (BUG-011) making vector recall dead for Hermes-written episodes. | NO (functional but degraded) |
| **P8 (MVP/Observability)** | Non-blocking. Reads ops tables. Memory metrics available. | NO |
| **P16 (Knowledge Graph)** | WIRED -- 4th RRF signal + KG ingestion hook. BUT SemanticFacts/KG lack project_id (BUG-004/BUG-018), so KG recall leaks across projects when P19 is active. Consolidation scheduler dead (BUG-002) means KG ingestion receives zero input. | YES -- KG recall cross-project leak blocks P19 isolation |
| **P18 (Advanced Memory)** | FULLY ADDITIVE. FSRS-6 columns, 5th RRF signal, decay sweep all verified. TierManager scaffold not integrated (BUG-041). Decay sweep never runs (BUG-002). | NO (but decay sweep dormant) |
| **P19 (Multi-Project Context)** | PARTIALLY SUPPORTED. Episodes have project_id; SemanticFacts/KG do not. store_episode_batch loses project_id (BUG-003). Consolidation has zero project awareness (BUG-008). | YES -- 3 CRITICAL blockers: BUG-003, BUG-004, BUG-008 |
| **P20 (Life Kernel)** | WIRED via p18_adapter. safe_mode never reaches memory recall during HARD STOP (BUG-007). Observe_node executes before decide_node detects HARD STOP. | YES -- safe_mode privacy gap during HARD STOP |
| **P21 (Voice)** | FULLY SUPPORTED. All P3 columns available for voice transcripts. No blockers. | NO |
| **P22 (Raw Access)** | SUPPORTED with gaps. store_episode_batch loses project_id (BUG-003). No caller-identity gate on store_episode (BUG-054). P22 must route through HermesMemoryBridge for untrusted data. | YES -- batch project_id loss blocks P22 namespace isolation |
| **P23 (Embodied Ops)** | SUPPORTED. Uses p18_adapter for action context. Inherits P20 safe_mode gap. Action audit goes to PostgresAuditJournal, not P3. | NO (inherits P20 gap) |
| **P24 (Hermes Fork)** | SUPPORTED. Adapter pattern works. Fork must preserve all 5 RRF signals + DNR + classification + safe-mode + budget + project filtering. | NO (but must preserve all surfaces) |

---

## 6. Read-Only Runtime Verification Status

### What Was Verified (from code inspection)

| Claim | Method | Result |
|---|---|---|
| Alembic migration chain converges to single head (p19_002) | File read of all 14 migration files + `alembic heads` | VERIFIED |
| ORM models.py has 48 `__tablename__` entries across 12 schemas | grep + manual count | VERIFIED |
| HNSW indexes exist in migration DDL (m=16, ef_construction=128) | File read of e401bb5fd274 | VERIFIED |
| Vector dimension consistency (1536) across ORM + migration DDL | Cross-reference models.py + migration DDL | VERIFIED |
| FTS search_vector + do_not_recall in migration 65f863220922 | File read | VERIFIED |
| DNR SQL WHERE clause in all three query builders | File read of read_pipeline.py:562,599,633 | VERIFIED |
| EmbeddingService is httpx-based, no OpenAI SDK | grep across src/memory/ | VERIFIED |
| Consolidation scheduler commented out in main.py | File read of main.py:23-38 | VERIFIED |
| verify_recall_results_dnr_free has zero call sites in src/ | grep across src/ tree | VERIFIED |
| store_episode_batch does not forward project_id | File read of write_pipeline.py:260-275 | VERIFIED |
| SemanticFacts/KG ORM lack project_id columns | File read of models.py:208-263, 391-405 | VERIFIED |
| safe_mode not passed through observe_node -> p18_adapter chain | File read of graph.py:247, p18_adapter.py:92-97 | VERIFIED |
| Result dicts from compute_scored_results lack do_not_recall key | File read of read_pipeline.py:769-777 | VERIFIED |
| All 235 memory tests use FakeSession/AsyncMock | File read of test files | VERIFIED |
| Four btree DESC indexes missing from migration DDL | grep across all 14 migrations | VERIFIED |

### What Requires NEEDS RUNTIME VERIFICATION

| Item | Why | Recommended Command |
|---|---|---|
| `alembic current` on production DB | Windows audit env, no DATABASE_URL | `alembic current` on VPS with DATABASE_URL set |
| Whether consolidation scheduler runs via systemd timer or external cron | Could not verify from code alone | `journalctl -u guinevere-core --no-pager -n 200 \| grep consolidation` |
| Whether Discord /memory-search actually returns results | Requires live bot + DB | Manual Discord command test |
| Whether embedding API (9Router) works end-to-end | Never tested against real API | Single `store_episode` call with embedding_service on VPS |
| Whether HNSW index is actually used at production data volumes | 20-row benchmark was meaningless | Run P3-007 benchmark with 10K+ rows on VPS |
| Whether P19 project_id filter causes HNSW planner regression | Never benchmarked | EXPLAIN ANALYZE with project_id filter on VPS |
| Whether surveillance.events uses 1d or 7d chunks | Migration DDL conflicts | `SELECT * FROM timescaledb_information.dimensions WHERE hypertable_name = 'events'` |
| Whether session_summaries has ClassificationMetaMixin columns | Missing from migration DDL | `\d memory.session_summaries` on VPS |
| Whether the four missing btree DESC indexes exist on VPS | Missing from migrations, could have been created manually | `\di *started_at_idx` etc. on VPS |

---

## 7. Safety Verdict

### DNR Absolute Enforcement

**PARTIALLY IMPLEMENTED -- single-layer defense only.**

- **SQL-level DNR WHERE clause** (`do_not_recall IS FALSE`): VERIFIED in all three query builders (`build_vector_query:562`, `build_fts_query:599`, `build_recency_query:633`) and in consolidation (`consolidation.py:323`) and decay sweep (`consolidation.py:995`). All callers pass `exclude_dnr=True` by default. This is the **sole active defense**.

- **Pre-injection gate** (`verify_recall_results_dnr_free`): NOT WIRED. Zero runtime call sites. Additionally, result dicts lack `do_not_recall` key so the gate would silently pass even if called. **Doubly broken.**

- **Consolidation DNR exclusion**: CORRECT. Both SQL-level and per-row defensive check (`consolidation.py:340-348`). Safe-word/crisis records also blocked (`is_safe_word_record`).

- **Authorization**: CORRECT. Only `guinevere_core` can mark/unmark DNR (`dnr.py:113`).

### Safe-Mode / HARD STOP Propagation

**INCONSISTENT ACROSS CODE PATHS.**

- `prompt_loader.py:252-254` resolves safe_mode from `hard_stop_handler.is_safe` (authoritative).
- `HermesMemoryBridge` receives `safe_mode` as caller parameter (relies on caller).
- Life kernel uses `LIFE_KERNEL_SAFE_RECALL` env var (not the HardStopHandler state).
- Life-kernel `observe_node` (graph.py:247) builds recall_context with only `query` and `content` keys -- **no safe_mode**. The p18_adapter does not accept or forward safe_mode. HARD STOP detection happens in `decide_node` AFTER `observe_node` already recalled full content.

### Context-Injection Leak-Free

**MOSTLY LEAK-FREE with two caveats.**

- `prompt_loader.py` only references `safe_content` -- never `raw_content`. VERIFIED.
- `build_safe_content()` correctly handles all 5 classification levels with appropriate placeholders. Fail-closed on unknown classification (level 5). VERIFIED.
- **Caveat 1:** `ContextCompactor._summarize()` (compaction.py:246-293) sends middle messages to LLM for summarization without classification-aware filtering. Critical/emotional content in middle messages is eligible for LLM summarization. The summary instruction does not prohibit leaking sensitive content.
- **Caveat 2:** Discord `/memory-search` passes `safe_mode=False` by default. Critical/Restricted content is returned raw in Discord embeds (truncated to 100 chars). This is intentional for `guinevere_core` principal but means classified content renders in Discord.

### Secrets / Memory Not Printed

**VERIFIED -- CLEAN.** All memory modules use metadata-only logging:
- DNR audit events: `episode_id`, `reason_hash`, `reason_length` -- no raw reason
- recall_memories: `query_hash` (SHA-256 truncated), lengths, counts -- no query text
- Embedding service: model, dimension, classification, redaction_applied -- never raw text
- Write pipeline: episode_id, classification, source, has_embedding, char_count
- No plaintext secrets in any evidence files (SOPS-only pattern)

### Embedding Privacy

**VERIFIED -- WELL-DESIGNED.** `prepare_embedding_text()` (embeddings.py:206-268) enforces:
- Critical classification requires `sanitized_summary` or raises `CriticalEmbeddingError` (fail-closed)
- Restricted/Confidential text undergoes deterministic redaction of 7 sensitive patterns
- Text truncated to 8000 chars before external API
- Dual enforcement: write pipeline guard + embedding service guard

---

## 8. Recommendations for Mama (NO FIXES -- prioritized)

### Priority 1: Must-Address Before P19 Implementation

1. **Wire consolidation scheduler into `src/core/main.py` lifespan.** The KG ingestion scheduler (P16) is already running -- the same `AsyncIOScheduler` instance can host the consolidation and decay jobs. Without this, semantic memory, KG ingestion, and FSRS decay are entirely dormant. (BUG-002, BUG-026)

2. **Add `project_id` to `SemanticFacts` and `KnowledgeGraph` ORM models + create corrective migration.** P19 memory isolation is incomplete without these columns. KG recall leaks across projects. (BUG-004, BUG-018)

3. **Fix `store_episode_batch` to forward `project_id` and `project_scope`.** Currently batch-imported episodes are always global-scope, defeating P19 namespace isolation and blocking P22 batch import. (BUG-003)

4. **Fix `consolidate_episodes_to_facts` to accept and forward `project_id` from source episodes.** Consolidation currently produces global-scope facts regardless of source episode project. (BUG-008)

### Priority 2: Must-Address Before P22/P23 Implementation

5. **Wire `verify_recall_results_dnr_free` as a post-recall guard** in at least `prompt_loader.py` after `recall_memories()` returns. Also add `do_not_recall` field to result dicts in `compute_scored_results()` so the gate has data to check. (BUG-001, BUG-006)

6. **Propagate `safe_mode=True` to memory recall during HARD STOP** in the life-kernel graph. Add `safe_mode` entry to `recall_context` dict in `graph.py:observe_node` and have `p18_adapter.recall()` inspect it. (BUG-007)

7. **Create a corrective migration** for the four missing btree DESC indexes (episodes_started_at_idx, events_occurred_at_idx, transactions_occurred_at_idx, audit_trail_occurred_at_idx) and the missing SessionSummary ClassificationMetaMixin columns. (BUG-005, BUG-009)

### Priority 3: Should-Address Before Production Scale

8. **Re-benchmark HNSW at 10,000+ rows** with real persistent data. Verify planner uses HNSW index. Test P19 project_id filter impact on query plans. Wire `SET hnsw.ef_search = 100` per ADR-009 or read from pgvector_config. (BUG-016, BUG-024, BUG-025)

9. **Add at least one integration-style test** against a test PostgreSQL instance for the `recall_memories` + `store_episode` round trip and `consolidate_episodes_to_facts`. The current 235 FakeSession tests provide no confidence in real SQL behavior. (BUG-017)

10. **Reconcile ORM with migration DDL** by adding ORM columns for all migration-created columns (procedural_skills.embedding, project_id/project_scope on multiple tables, loop_instances columns) or documenting intentional raw-SQL-only design. (BUG-010)

### Priority 4: Should-Address for Code Quality

11. **Fix broad `except Exception` on embedding fallback** in `recall_memories` (read_pipeline.py:891-895). Currently catches `EmbeddingConfigurationError`, `EmbeddingAPIError`, `DimensionMismatchError` silently. At minimum, log the exception type. (BUG-015)

12. **Add classification validation on write** for non-Critical episodes. Misspelled labels (e.g., "pUblic") bypass ceiling filter. (BUG-014)

13. **Add classification-awareness to `ContextCompactor._summarize()`**. Filter out or redact messages with Critical/Restricted/surveillance content before LLM summarization. (BUG-020)

14. **Update `src/memory/models.py` docstring** from "47 tables" to "48 tables" and from "8 tables" to "9 tables" for the memory schema. (BUG-056)

15. **Unify safe-mode resolution** across prompt_loader (HardStopHandler), HermesMemoryBridge (caller param), and life-kernel (env var) into a single authoritative source. (BUG-040)

---

## 9. Explicit Affirmation

This audit was conducted **entirely read-only**. The following actions were NOT taken:

- No runtime source code was edited (`src/`, `alembic/`, `tests/` untouched)
- No documentation was edited except this single output file at `docs/setup-evidence/legacy-audit/P3/evidence/final-p3-implementation-audit-report.md`
- No `CHECKLIST.md`, `PROGRESS.md`, `README.md`, or `AGENTS.md` was modified
- No database was accessed (no `alembic upgrade/downgrade`, no SQL queries, no INSERT/UPDATE/DELETE)
- No migrations were run or reversed
- No secrets were printed (no DB passwords, API keys, decrypted env vars)
- No deployments were triggered (no systemctl, docker, or service restarts)
- No raw memory content, personal data, or intimate content was printed

All findings are based on source code file reads, grep searches, migration file inspection, and cross-referencing of existing audit evidence under `docs/setup-evidence/legacy-audit/P3/` and `audit-reports/P3/P3-FINAL-AUDIT/`.

---

*Generated by P3 Final Implementation Audit Synthesis Agent. READ-ONLY audit -- no code, docs, or runtime modified except this output file.*

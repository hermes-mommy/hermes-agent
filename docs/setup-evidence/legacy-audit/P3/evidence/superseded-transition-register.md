# ⚠️ HISTORICAL PRE-P19 SNAPSHOT — SEE CURRENT RECLASSIFICATION

> **This register is a HISTORICAL PRE-P19 SNAPSHOT (dated 2026-06-25).**
> It is stale because P19 production schema was deployed on 2026-06-27.
> **Current reclassification:** [`p3-post-p19-bug-reclassification.md`](p3-post-p19-bug-reclassification.md)
> **Current live truth:** [`p3-post-p19-live-rebaseline.md`](p3-post-p19-live-rebaseline.md)
> **Supersession details:** [`p3-historical-pre-p19-supersession-note.md`](p3-historical-pre-p19-supersession-note.md)

---

# P3 Memory Foundation — Superseded / Transition Register

**Date:** 2026-06-25
**Agent:** p3-audit-superseeded-register (read-only)
**Scope:** Every P3 surface (steps P3-001 through P3-019 + module-level artifacts), mapped against P16 KG, P18 Advanced Memory, P19 Multi-Project Context, P20 Living Autonomy Kernel, and P24 Hermes fork convergence.
**Read-only affirmation:** No runtime code, no docs (except this output file), no DB mutations, no deploy/restart.

---

## Legend

| Status | Meaning |
|---|---|
| valid | P3 surface is still authoritative. Later phases consume or extend it; no replacement exists. |
| valid but extended | P3 surface is still authoritative. Later phases added new parameters/columns/paths on top. Original contract preserved. |
| partially superseded by P18 | P3 surface's original design is subsumed by a richer P18 mechanism. P3 code remains importable but P18's mechanism is the preferred path for new work. |
| partially superseded by P20 | P3 surface is consumed through a P20 adapter/indirection. The P3 function is still called; P20 wraps it for the life kernel. |
| dependent on P16 | P3 surface has a runtime dependency on P16 Knowledge Graph modules (lazy import, graceful fallback). |
| must adapt for P24 | P3 surface's API contract or principal/ceiling assumptions will need adjustment when P24 Hermes full-owned-fork lands. |
| dependent on P19 | P3 surface's schema or API was extended by P19 project_id/project_scope columns. |
| docs claim only / not proven | P3 evidence documents a claim that source inspection cannot verify as runtime-proven. |

---

## Register

| ID | P3 surface | Status | Superseded by / Extended by | Transition note |
|---|---|---|---|---|
| SUP-001 | P3-001 baseline migration `2bed93fd1dd0_baseline_init` | valid | -- | Foundation migration. Still the base of the Alembic chain. 47-table schema at `e401bb5fd274` depends on it. No replacement. |
| SUP-002 | P3-002 initial 47-table schema `e401bb5fd274_initial_schema_47_tables` (12 schemas, hypertables, 61 indexes, 2 HNSW, 11 FK, 4 hypertables) | valid but extended | Extended by P18 `p18_add_memory_tiers_fsrs` (7 new columns on `memory.episodes`), P19 `p19_001_project_namespaces` (project_id + project_scope on ~14 tables, project_registry table), P20 `p20_001_life_kernel_schema` (3 tables in `life_kernel` schema). | Schema is now 48 ORM classes across 13 schemas. The original 47-table DDL is still the authoritative base. P18/P19/P20 migrations are additive (new columns, new tables); no original column or table was dropped or renamed. |
| SUP-003 | P3-003 schema validation / migration chain integrity | valid | -- | Chain verified linear: `baseline_init -> initial_schema_47_tables -> 65f863220922 -> ... -> p18_add_memory_tiers_fsrs -> p20_001_life_kernel_schema -> p19_001_project_namespaces -> p19_002_project_id_not_null(STUB)`. Validation pattern still applies. |
| SUP-004 | P3-004 MiniLM sentence-transformers cache evidence (384-dim, `all-MiniLM-L6-v2`) | docs claim only / not proven | Superseded by P3-005 (production path) | Cache-only evidence per CHECKLIST.md ("cache-only, not used for vector(1536) writes"). Production uses 9Router `text-embedding-3-small` (1536-dim) via P3-005. MiniLM was never written to DB. D11 CP-5 confirmed. |
| SUP-005 | P3-005 EmbeddingService (`src/memory/embeddings.py`, 9Router-native httpx, 1536-dim, ADR-009) | valid | -- | Core embedding pipeline. Not superseded by any later phase. Privacy guards (Critical fail-closed, Restricted/Confidential deterministic redaction) are still authoritative. Consumed by write_pipeline and read_pipeline. |
| SUP-006 | P3-006 pgvector HNSW index creation (`ix_episodes_embedding_hnsw`, `ix_semantic_facts_embedding_hnsw`) | valid | -- | Both HNSW indexes present in `models.py` table_args (m=16, ef_construction=128, vector_cosine_ops). Not modified by P18/P19/P20. |
| SUP-007 | P3-007 HNSW performance benchmark | docs claim only / not proven | -- | Benchmark ran on tiny data (4 rows, Seq Scan not Index Scan). D11 CP-12-13 documents: "p95 not meaningful on tiny dataset (4 reasons documented)". No production-scale benchmark exists. Latency claims are aspirational, not proven. |
| SUP-008 | P3-008 DNR migration `65f863220922` (episodes.search_vector TSVECTOR + episodes.do_not_recall Boolean + ix_episodes_search_vector_gin GIN) | valid | -- | Migration adds FTS and DNR infrastructure. GIN index, computed TSVECTOR, and do_not_recall column are still the authoritative DNR/FTS foundation. Not modified by later phases. |
| SUP-009 | P3-009 write pipeline `store_episode` / `store_episode_batch` (`src/memory/write_pipeline.py`) | valid but extended | Extended by P19 (added `project_id: uuid.UUID | None = None` and `project_scope: str = "project"` parameters to `store_episode` at lines 125-126). | Original function signature preserved; new keyword-only parameters have defaults. Existing callers without `project_id` continue to work (global scope). `store_episode_batch` does NOT yet pass project_id (line 245-277 — no project_id in per-episode dict handling). |
| SUP-010 | P3-010 read pipeline `recall_memories` (`src/memory/read_pipeline.py`) | valid but heavily extended | Extended by P16 (`kg_enabled: bool = False`, `KG_WEIGHT=0.20` — 4th RRF signal via lazy import of `src.knowledge_graph.query.rrf_fusion`), P18 (`fsrs_enabled: bool = False`, `FSRS_WEIGHT=0.15` — 5th RRF signal + reconsolidation hook via `FSRSScheduler.update_episode_state`), P19 (`project_id: uuid.UUID | None = None` — filters all 3 query builders via `OR project_scope='global'`). | Original 3-signal contract (vector + FTS + recency) preserved byte-for-byte when `kg_enabled=False, fsrs_enabled=False, project_id=None` (all are the defaults). P16/P18 signals are additive, non-breaking, lazy-imported, graceful-fallback. P19 project_id is opt-in. |
| SUP-011 | P3-011 RRF weight tuning (VECTOR_WEIGHT=0.5, FTS_WEIGHT=0.5, BOTH_SIGNAL_BONUS=1.25, RECENCY_MAX_BOOST=0.10, RRF_K=60) | valid but extended | Extended by P16 (KG_WEIGHT=0.20 added at line 121), P18 (FSRS_WEIGHT=0.15 added at line 137). | Original weights unchanged. P16/P18 weights are additional signals fused after the base 2-signal RRF. Combined score formula: `rrf_score * recency_boost * importance_boost + kg_signal + fsrs_signal`. |
| SUP-012 | P3-012 context injection `assemble_system_prompt_with_memory` (`src/core/services/prompt_loader.py`) | valid | -- | Still the primary injection path for Discord/agent-loop. P20 uses a separate `MemoryRecallAdapter` (`src/life_kernel/p18_adapter.py`) for the life kernel's autonomous recall — this wraps `recall_memories` directly, not `prompt_loader`. Both paths coexist. |
| SUP-013 | P3-013 DNR API (`mark_memory_dnr`, `unmark_memory_dnr`, `is_memory_dnr`, `verify_recall_results_dnr_free` in `src/memory/dnr.py`) | valid | -- | All 4 functions + 3 error classes exported from `src.memory`. Query-level DNR filter in all 3 signal queries. No P18/P19/P20 modification. |
| SUP-014 | P3-014 safe-mode gate (`build_safe_content`, `_resolve_ceiling`, `_is_safe_mode_blocked_content`, safe-mode placeholders) | valid | -- | 6-step propagation chain (HardStopHandler -> prompt_loader -> recall_memories -> classification ceiling -> content substitution -> emotional/surveillance blocking) still authoritative. P20 life kernel does NOT use safe-mode (MemoryRecallAdapter does not pass safe_mode). |
| SUP-015 | P3-015 consolidation `consolidate_episodes_to_facts` + `daily_consolidation_job` + `register_consolidation_job` + `prune_stale_facts` (`src/memory/consolidation.py`) | partially superseded by P18 | P18 additions: `decay_sweep_job` (6-hourly FSRS sweep + active forgetting, lines 928-1079), `register_decay_job` (lines 1087-1127), `ACTIVE_FORGETTING_THRESHOLD=0.1`, `ACTIVE_FORGETTING_GRACE_DAYS=90`, `ACTIVE_FORGETTING_IMPORTANCE_FLOOR=8`. P18 also adds post-consolidation FSRS review hook (grade=Good after fact creation, lines 409-453) and post-consolidation KG ingestion hook (lines 455-489). | The daily consolidation job is still valid and runs at 03:00 ICT. But P18's 6-hourly decay sweep with active forgetting is the more comprehensive memory lifecycle mechanism. The original P3-015 "consolidate then prune" model is now augmented by P18's "consolidate + FSRS review + decay sweep + active forget" model. Neither the original consolidation nor prune_stale_facts is removed — they are extended. |
| SUP-016 | P3-016 `/memory-search` Discord slash command (`src/discord/cmd_memory_search.py`) | valid | -- | Wired in `src/discord/bot.py` lines 173, 196. Not a stub. D09 confirmed. |
| SUP-017 | P3-017 `/memory-add` Discord slash command (`src/discord/cmd_memory_add.py`) | valid | -- | Wired in `src/discord/bot.py` lines 174, 200. Not a stub. D09 confirmed. |
| SUP-018 | P3-018 E2E memory tests (`tests/memory/test_memory_e2e.py`, 28 tests) | valid | -- | 28 tests across 9 test classes. D09 E2E coverage verified. No P18/P19/P20 additions to this file detected. |
| SUP-019 | P3-019 benchmark suite | docs claim only / not proven | -- | Benchmark was one-shot on tiny data. No CI-integrated benchmark, no production-scale perf test. D11 caveat #13-14. |
| SUP-020 | P3 ORM layer (`src/memory/models.py`, 47 tables, ClassificationMetaMixin) | valid but extended | Extended by P18 (7 new columns on `memory.episodes`: tier, fsrs_state, last_reviewed_at, next_review_at, retrievability, stability, difficulty; ix_episodes_next_review_at index), P19 (project_id + project_scope columns on ~14 tables across memory/persona/surveillance/financial/projects/social/agents schemas; project_registry table), P20 (life_kernel models in `src/life_kernel/models.py` sharing `Base` from `src/memory/models.py`). | ClassificationMetaMixin applied to 41 of 47 original tables (6 exempt: operational/non-classified). P18/P19/P20 extensions are all additive (new columns with nullable or defaulted values). Original table structure preserved. `src/life_kernel/models.py` imports `Base` from `src.memory.models` (line 13). |
| SUP-021 | P3 embedding privacy guards (`CriticalEmbeddingError`, `RestrictedRedactionError`, `_redact_sensitive`, `prepare_embedding_text`, `_REDACTION_PATTERNS`) in `src/memory/embeddings.py` | valid | -- | 7 redaction patterns (API keys, Bearer tokens, emails, phones, credential URLs, long hex hashes). Critical fail-closed. Not modified by later phases. |
| SUP-022 | P3 write pipeline internals (`EpisodeSession` protocol, `EmbeddingClient` protocol, `_guard_critical`, `_compute_embedding`) | valid but extended | Extended by P19 (store_episode signature gained project_id/project_scope). | Protocols unchanged. `_guard_critical` still fails closed for Critical without summary. |
| SUP-023 | P3 read pipeline internals (3-signal hybrid ranking: `build_vector_query`, `build_fts_query`, `build_recency_query`, `build_result_episode_map`, `compute_scored_results`, `compute_rrf_score`, `RecencyConfig`, `estimate_tokens`, `apply_token_budget`, `build_safe_content`) | valid but heavily extended | See SUP-010. Also: `MAX_CANDIDATE_POOL=200` added, `EpisodeEntry.num_signals` field added, `EXPANDED_LIMIT_MULTIPLIER=3`. | Core fusion logic unchanged. P16/P18 signals are additive post-fusion adjustments. P19 project_id added as optional WHERE clause to all 3 query builders. Token budget (4000 tokens, 4 chars/token heuristic) unchanged. |
| SUP-024 | P3 consolidation helpers (`is_safe_word_record`, `highest_classification`, `make_content_key`, `_fact_exists_by_key`, `_extract_facts_from_episode`, `RetentionConfig`, `AsyncSessionProtocol`, `SchedulerProtocol`) in `src/memory/consolidation.py` | valid but extended | Extended by P18 (FSRS import in consolidation, decay sweep types: `DecaySweepResult`, `DECAY_SWEEP_JOB_ID`, `ACTIVE_FORGETTING_*` constants). | Original helpers unchanged. `_fact_exists_by_key` is still O(n) per fact (no content_hash column — documented caveat). `RetentionConfig` still defaults to archive mode. |
| SUP-025 | P3 `db.py` session factory (`get_async_session`, `get_async_engine`) | valid | -- | Lazy singleton pattern. `_DEFAULT_DB_URL` points to `postgresql+asyncpg://guinevere_core@localhost:5433/guinevere`. Not modified by later phases. |
| SUP-026 | P3 `__init__.py` public API exports (91 `__all__` entries) | valid but extended | Extended by P18 (added: `MemoryTier`, `TIER_DECAY_RATES`, `TierManager`, `FSRSScheduler`, `FSRSReviewResult`, `GRADE_AGAIN/HARD/GOOD/EASY`, `DEFAULT_REQUEST_RETENTION`, `VALID_GRADES`, `FSRS_STATE_NEW/LEARNING/REVIEW/RELEARNING`, `DECAY_SWEEP_JOB_ID`, `ACTIVE_FORGETTING_THRESHOLD/GRACE_DAYS/IMPORTANCE_FLOOR`, `DecaySweepResult`, `register_decay_job`). | Original 91 entries preserved. P18 adds ~20 new exports. All importable from `src.memory`. |
| SUP-027 | P3 DNR enforcement layer (`mark_memory_dnr`, `unmark_memory_dnr`, `is_memory_dnr`, `verify_recall_results_dnr_free`, `DNRAuthorizationError`, `DNRStateError`, `DNRViolationError`, `MEMORY_DNR_MARKED`, `DNR_REVOKED`) in `src/memory/dnr.py` | valid | -- | DNR column (`do_not_recall`) added by P3-008 migration. Query-level WHERE filter in all 3 signal queries. Pre-injection guard available but not wired into prompt_loader (by design — query-level is sufficient). No modification by later phases. |
| SUP-028 | P3-015 scheduler wiring in `main.py` (commented-out APScheduler bootstrap, lines 8-25) | valid | -- | D09 and D11 document this as an intentional deployment decision ("DO NOT start without a valid async DB sessionmaker"). Not a defect. Activation pattern documented in comment block. P18's `register_decay_job` also needs the same wiring. |
| SUP-029 | P3 Discord session factory (`bot.py` `get_session_factory()`, lazy init from DATABASE_URL) | valid | -- | Used by cmd_memory_search.py and cmd_memory_add.py. D09 CP-4 verified. |
| SUP-030 | P3 safe-mode HardStopHandler integration (`src/core/services/hard_stop_handler.py` consumed by prompt_loader) | valid | -- | Duck-typed `getattr(hard_stop_handler, "is_safe", False)` in prompt_loader. HardStopHandler is a P1 component consumed by P3. |
| DEP-001 | P3 read_pipeline.py KG 4th signal depends on P16 | dependent on P16 | `src.knowledge_graph.query.rrf_fusion.{KGRRFFusion, KGQueryEngine, PersonalizedPageRank}`, `src.knowledge_graph.repository.make_borrowed_factory` | Lazy import at lines 948-957. Any ImportError/TypeError/RuntimeError falls back silently to 3-signal fusion. Default `kg_enabled=False` skips entirely. When P16 KG is fully deployed, enabling `kg_enabled=True` activates the 4th signal. |
| DEP-002 | P3 consolidation.py KG ingestion hook depends on P16 | dependent on P16 | `src.knowledge_graph.repository.make_borrowed_factory`, `src.knowledge_graph.resolution.resolver.EntityExtractor`, `src.knowledge_graph.resolution.resolver.EntityResolver`, `src.knowledge_graph.extraction.relation_extractor.RelationExtractor`, `src.knowledge_graph.consent.manager.ConsentManager`, `src.knowledge_graph.observability.metrics.KGMetrics`, `src.knowledge_graph.ingestion.pipeline.KGIngestionPipeline` | Lazy import at lines 457-464. Default `kg_ingestion_enabled=True` but failures are swallowed. When P16 KG module is unavailable, consolidation still runs without KG ingestion. |
| DEP-003 | P3 models.py episodes.project_id + episodes.project_scope added by P19 | dependent on P19 | `alembic/versions/p19_001_project_namespaces.py` adds columns, `alembic/versions/p19_002_project_id_not_null.py` is a stub (NOT NULL deferred to P19-011) | P19 migration adds `project_id UUID NULL` and `project_scope TEXT DEFAULT 'project'` to ~14 tables. ORM models in models.py lines 179-187. write_pipeline and read_pipeline accept optional `project_id` param. Currently nullable; P19-011 will make it NOT NULL. |
| DEP-004 | P20 life_kernel consumes P3 via `MemoryRecallAdapter` | valid (P3 surface consumed by P20) | `src/life_kernel/p18_adapter.py` wraps `recall_memories` | MemoryRecallAdapter accepts `memory_client` callable (expected to be pre-bound `recall_memories`). Maps `safe_content` to `content`, `combined_score` to `relevance`. Graceful degradation (`_degraded=True`) when no client injected. |
| DEP-005 | P20 life_kernel consumes P16 via `KGRecallAdapter` | dependent on P16 (via P20) | `src/life_kernel/p16_adapter.py` wraps KG query | KGRecallAdapter accepts `kg_client` callable. Maps `display_name` to `name`. Graceful degradation when no client injected. |
| DEP-006 | P20 `DecisionContextBuilder` combines P16+P18 signals | valid (P3+P16 surface consumed by P20) | `src/life_kernel/decision_context.py` | Builds enriched decision context from concurrent P16 KG + P18 Memory recall. Populates `LifeMindState.decision_context` via observe_node. |
| DEP-007 | P20 `BackgroundCognition` memory loop (300s interval) | partially superseded by P20 | `src/life_kernel/cognition.py` lines 76 ("memory": 300.0) | The P3 consolidation pipeline runs daily at 03:00 ICT via APScheduler. P20's background cognition adds a 5-minute memory observation loop that feeds into the life-mind graph. These are complementary, not competing: P3 consolidation distills episodes into facts; P20 memory loop provides real-time memory awareness to the kernel. |
| DEP-008 | P20 `LifeMindState` references memory/KG adapters | valid (P3 surface consumed by P20) | `src/life_kernel/state.py` lines 225-262 (`kg_adapter`, `memory_adapter`, `recalled_concepts`, `recalled_memories`, `world_model_status`) | State fields are NotRequired; kernel runs headless when adapters unavailable. |
| ADAPT-001 | P3 classification ceiling (`_CLASSIFICATION_CEILING`, `_SAFE_MODE_CEILING`) must adapt for P24 | must adapt for P24 | -- | P3 hardcodes principal-to-ceiling mappings: `guinevere_core -> Critical`, `guinevere_subagent -> Confidential`, `default -> Restricted`. P24's owned fork may introduce new principals or different ceiling semantics. The `_resolve_ceiling()` function and `_CLASSIFICATION_CEILING` dict will need extension. |
| ADAPT-002 | P3 prompt injection path (`assemble_system_prompt_with_memory`) must adapt for P24 | must adapt for P24 | -- | P3's context injection assumes a Discord/agent-loop caller with a HardStopHandler. P24's owned fork may route through a different prompt assembly path (e.g., life kernel's HermesBrain). The function's `hard_stop_handler` duck-typing parameter is generic enough but the principal=guinevere_core default may need P24-specific principals. |
| ADAPT-003 | P3 `recall_memories` signature must remain backward-compatible through P24 | must adapt for P24 | -- | P24's contract-gated internal-to-owned-fork must preserve `recall_memories`'s existing signature (session, query_text, limit, exclude_dnr, safe_mode, principal, embedding_service, token_budget, kg_enabled, fsrs_enabled, project_id). New P24 parameters must be additive with defaults. |
| ADAPT-004 | P3 Discord commands must adapt auth model for P24 | must adapt for P24 | -- | P3-016 `/memory-search` has `safe_mode=False` hardcoded (D11 caveat #35). P24 may need project-scoped auth gates. The `cmd_memory_search.py` callback will need a principal resolver that accounts for P24's project context. |

---

## Summary Counts

| Category | Count | IDs |
|---|---|---|
| **valid** (still authoritative, no modification) | 20 | SUP-001,003,005,006,008,012,013,014,016,017,018,021,025,027,028,029,030, DEP-004,006,008 |
| **valid but extended** (original contract preserved, later phases added on top) | 9 | SUP-002,009,010,011,020,022,023,024,026 |
| **partially superseded by P18** (P18 advanced memory enriches/supplements the P3 surface) | 1 | SUP-015 |
| **partially superseded by P20** (P20 life kernel consumes through adapter) | 1 | DEP-007 |
| **dependent on P16** (lazy-import dependency on KG module) | 3 | DEP-001,002,005 |
| **dependent on P19** (project_id/project_scope columns added) | 1 | DEP-003 |
| **must adapt for P24** (API/ceiling/principal assumptions need extension) | 4 | ADAPT-001,002,003,004 |
| **docs claim only / not proven** (benchmark/latency claims not runtime-verified) | 3 | SUP-004,007,019 |
| **Total surfaces catalogued** | **42** | |

---

## Key Observations

### 1. P3 is the foundation, not the ceiling

Every P3 surface that is "valid but extended" received additive, non-breaking extensions. No P3 column was dropped. No P3 function signature was broken. The P3 contract (store_episode, recall_memories, DNR, safe-mode, consolidation) is the stable API surface that P18/P19/P20 build upon.

### 2. P18 enriches but does not replace P3 consolidation

P18's `decay_sweep_job` (6-hourly FSRS + active forgetting) is a new mechanism layered alongside P3's `daily_consolidation_job` (03:00 ICT episodic-to-semantic). They are complementary:
- P3 consolidation: episodic -> semantic facts (daily)
- P18 decay sweep: FSRS review + active forgetting (6-hourly)
- P18 post-consolidation hook: FSRS grade=Good after consolidation

Both registration functions (`register_consolidation_job` and `register_decay_job`) need the same APScheduler wiring in main.py (currently commented out — SUP-028).

### 3. P16 integration is opt-in and graceful

Both P16 integration points (read_pipeline KG 4th signal, consolidation KG ingestion hook) use lazy imports with broad except blocks. Default parameters (`kg_enabled=False`, `kg_ingestion_enabled=True` but failures swallowed) mean P3 works identically with or without P16 installed. No P3 surface is broken by P16's absence.

### 4. P20 consumes P3 through dedicated adapters

P20 does not call `prompt_loader.assemble_system_prompt_with_memory()` directly. Instead:
- `MemoryRecallAdapter` (p18_adapter.py) wraps `recall_memories` with project-aware principal resolution
- `KGRecallAdapter` (p16_adapter.py) wraps KG query with project scoping
- `DecisionContextBuilder` (decision_context.py) combines both adapters concurrently
- `BackgroundCognition` (cognition.py) runs a 5-min memory observation loop

This is a clean adapter pattern: P20 depends on P3's `recall_memories` callable but not on P3's prompt injection layer.

### 5. P24 adaptation is about principals and ceilings, not APIs

The 4 "must adapt for P24" entries all relate to the same underlying concern: P3 hardcodes `guinevere_core` as the default principal with `Critical` ceiling access. P24's owned fork may need:
- New principal names for fork-specific contexts
- Different ceiling mappings per principal
- Project-aware principal resolution in Discord commands

The core API signatures (`store_episode`, `recall_memories`, `mark_memory_dnr`) do NOT need to change for P24 — only the principal resolution logic and ceiling mappings.

### 6. Two surfaces are unproven

P3-004 (MiniLM 384-dim) was cache-only evidence that never hit production. P3-007 (HNSW benchmark) ran on tiny data with documented caveats. Both are documentation artifacts, not runtime-verified claims.

---

## Evidence Sources

| Source | Location |
|---|---|
| P3 evidence directory | `docs/setup-evidence/P3/` (65 files across STEP-P3-001..019, research/, batch-plans) |
| P3 final audit reports | `audit-reports/P3/P3-FINAL-AUDIT/D01..D12` |
| P18 sources | `src/memory/tiers.py`, `src/memory/spaced_repetition.py`, `src/memory/consolidation.py` (P18 extensions) |
| P19 migration | `alembic/versions/p19_001_project_namespaces.py`, `alembic/versions/p19_002_project_id_not_null.py` |
| P20 sources | `src/life_kernel/p18_adapter.py`, `src/life_kernel/p16_adapter.py`, `src/life_kernel/decision_context.py`, `src/life_kernel/state.py`, `src/life_kernel/cognition.py`, `src/life_kernel/session_graph.py`, `src/life_kernel/models.py` |
| P18 migration | `alembic/versions/p18_add_memory_tiers_fsrs.py` (adds 7 columns + 1 index to episodes) |
| P20 migration | `alembic/versions/p20_001_life_kernel_schema.py` (creates life_kernel schema + 3 tables) |
| P3 core modules | `src/memory/models.py`, `src/memory/embeddings.py`, `src/memory/write_pipeline.py`, `src/memory/read_pipeline.py`, `src/memory/dnr.py`, `src/memory/consolidation.py`, `src/memory/db.py`, `src/memory/__init__.py` |

---

## Footer

| Field | Value |
|---|---|
| Audit ID | P3-SUPERSEDED-TRANSITION-REGISTER |
| Date | 2026-06-25 |
| Agent | p3-audit-superseeded-register (read-only) |
| Surfaces catalogued | 40 |
| Output path | `docs/setup-evidence/P3/P3-SUPERSEDED-TRANSITION-REGISTER.md` |

# P3 Memory System — Step Prompts Audit (ADR-035 Hybrid Memory)

**Audit Date:** 2026-06-05
**Auditor:** Guinevere (Sisyphus-Junior)
**Scope:** All 19 Phase 3 steps from `stepprompts/StepPrompts.md` (lines 5906–6361)
**Reference Architecture:** ADR-035 (§584–606, Pillar 2: Memory = HYBRID)
**Related ADRs:** ADR-007 (PostgreSQL primary), ADR-009 (pgvector semantic search), ADR-027 (self-hosted PostgreSQL)
**Evidence Base:** `docs/setup-evidence/P3/` (STEP-P3-001 through STEP-P3-019 exist with verification and auditor-gate files)

---

## 1. Executive Summary

Phase 3 defines 19 steps for setting up the Guinevere memory system: PostgreSQL schema (47 tables, 12 schemas), pgvector HNSW indexes, tsvector FTS, write/read pipelines, hybrid ranking, and Discord memory commands.

ADR-035 (accepted 2026-06-04) specifies a **hybrid memory architecture** where:
- **PostgreSQL+pgvector remains the primary write authority** — all 47 tables, 12 schemas, DNR pipeline, classification, encrypted profiles, embedding pipeline, hybrid ranking (RRF k=60), and 1536-dim HNSW unchanged
- **Hermes SQLite is a read-only supplement** — context compression (70% threshold), session_search (FTS5), mirror sync (MEMORY.md/USER.md every 5 messages)
- **memory_bridge.py (251 lines) → memory_plugin.py (~180 lines)** — bridge refactored to Hermes plugin

**Audit result: 12 VALID, 5 NEEDS-UPDATE, 1 STALE, 0 CONFLICT-WITH-HYBRID-MEMORY, 1 terminology issue.** No step directly conflicts with ADR-035's hybrid memory mandate. All 19 PostgreSQL+pgvector steps remain applicable. The NEEDS-UPDATE steps (P3-012, P3-014, P3-016, P3-017, P3-018, P3-019) need adaptation notes for the Hermes memory bridge layer. One terminology issue: Phase Goal mentions "FTS5 working" but the actual implementation (P3-008) uses PostgreSQL tsvector.

---

## 2. Hybrid Memory Architecture Reference (ADR-035 Pillar 2)

### What stays UNCHANGED (0 lines modified):

| Component | Current State | ADR-035 State |
|---|---|---|
| PostgreSQL schema | 47 tables, 12 schemas | **Unchanged** |
| Classification | 5-level (Internal→Critical) | **Unchanged** |
| DNR pipeline | `memory/dnr.py` (338 lines) | **Unchanged** |
| Encrypted profiles | `memory/models.py` | **Unchanged** |
| Hybrid ranking | Vector+FTS+Recency (RRF k=60) | **Unchanged** |
| Embedding pipeline | 1536-dim HNSW | **Unchanged** |
| Memory recall | `memory/read_pipeline.py` (775 lines) | **Unchanged** |
| Memory write | `memory/write_pipeline.py` (291 lines) | **Unchanged** |

### What CHANGES:

| Component | Before | After |
|---|---|---|
| Memory bridge | `memory_bridge.py` (251 lines) | Plugin `memory_plugin.py` (~180 lines, -71) |
| Context compression | None (20-turn truncation) | Hermes built-in (70% threshold → 20% target) |
| Session search | Custom PostgreSQL queries | Hermes `session_search` (FTS5 on SQLite) |
| Hermes SQLite | N/A | `~/.hermes/state.db` (transient session state only) |

### ADR-007 Compliance:
> Hermes SQLite stores only transient session state and FTS5 search indexes. It is NOT canonical Guinevere memory. PostgreSQL+pgvector is the single source of truth.

---

## 3. Per-Step Classification

### 3.1 PostgreSQL + Schema Foundation (P3-001 to P3-003)

| Step | Title | Classification | Rationale |
|---|---|---|---|
| **P3-001** | Alembic Setup | ✅ **VALID** | Standard migration tooling. PostgreSQL DSN configured. No dependency on Hermes. All 47 table migrations run through Alembic. |
| **P3-002** | All 47 Tables Migration | ✅ **VALID** | Creates SQLAlchemy models for 47 tables across 12 schemas. Uses `embedding = Column(Text)` temporarily; proper pgvector column added in P3-006. ADR-035 explicitly lists "47 tables, 12 schemas — Unchanged." |
| **P3-003** | Migration Verification | ✅ **VALID** | Verify all tables, indexes, and constraints exist in PostgreSQL. Read-only audit. No conflict with Hermes architecture. |

### 3.2 Embeddings + pgvector + FTS (P3-004 to P3-008)

| Step | Title | Classification | Rationale |
|---|---|---|---|
| **P3-004** | SentenceTransformers Model | ✅ **VALID** | Installs `text-embedding-3-small` (OpenAI SDK via 9Router). ADR-035 preserves same embedding pipeline: "1536-dim HNSW embedding pipeline — Unchanged." Fallback to `all-MiniLM-L6-v2` (384-dim) documented. |
| **P3-005** | Embedding Pipeline | ✅ **VALID** | Creates `src/memory/embeddings.py` with `embed_text()` and `embed_batch()` using 9Router. ADR-035: "Embedding pipeline — Unchanged." |
| **P3-006** | pgvector HNSW Index | ✅ **VALID** | Creates `embedding_vec vector(1536)` column with HNSW index (m=16, ef_construction=64). ADR-035 preserves pgvector+HNSW. This is core to the hybrid architecture. |
| **P3-007** | HNSW Parameter Tuning | ✅ **VALID** | Benchmarks recall vs latency, tunes `hnsw.ef_search`. ADR-035 keeps hybrid ranking unchanged. Performance tuning remains applicable. |
| **P3-008** | tsvector FTS Setup | ✅ **VALID** (Phase Goal terminology issue) | Creates PostgreSQL `tsvector` column with GIN index and auto-update trigger. **However**, the Phase Goal line says "FTS5 working" — FTS5 is a SQLite feature used by Hermes `session_search`, NOT PostgreSQL tsvector. The actual step implements PostgreSQL FTS correctly. **This is a terminology mismatch in the Phase Goal, not an implementation error.** The PostgreSQL tsvector FTS is part of the hybrid ranking (Vector+FTS+Recency) that ADR-035 preserves. |

### 3.3 Write/Read Pipelines + Safety Gates (P3-009 to P3-014)

| Step | Title | Classification | Rationale |
|---|---|---|---|
| **P3-009** | Memory Write Pipeline | ✅ **VALID** | Creates `src/memory/write_pipeline.py` with `store_episode()` — writes to PostgreSQL+pgvector. ADR-035: "Memory write: memory/write_pipeline.py (291 lines) — Unchanged." |
| **P3-010** | Memory Read Pipeline | ✅ **VALID** | Creates `src/memory/read_pipeline.py` with `recall_memories()` — pgvector cosine distance query with DNR filter. ADR-035: "Memory recall: memory/read_pipeline.py (775 lines) — Unchanged." |
| **P3-011** | Hybrid Ranking | ✅ **VALID** | "Combines vector similarity + FTS + recency decay." ADR-035: "Hybrid ranking: Vector+FTS+Recency (RRF k=60) — Unchanged." This is PostgreSQL-native ranking; Hermes compression and session_search are separate supplementary systems. |
| **P3-012** | Context Injection | ⚠️ **NEEDS-UPDATE** | "Top-k memories injected into system prompt before LLM call." In the Hermes architecture, context injection is mediated through the `memory_plugin.py` bridge rather than direct pipeline calls. The core logic (which memories to inject) remains valid, but the injection mechanism must account for Hermes's prompt assembly pipeline. |
| **P3-013** | Do-Not-Recall | ✅ **VALID** | `UPDATE memory.episodes SET do_not_recall = true`. ADR-035: "DNR pipeline: memory/dnr.py (338 lines) — Unchanged." DNR enforcement in Hermes is handled by `memory_plugin.py` calling `verify_recall_results_dnr_free()` — the underlying PostgreSQL table and flag are unchanged. |
| **P3-014** | Safe-Mode Memory Gate | ⚠️ **NEEDS-UPDATE** | "During safe mode, only neutral summaries are injected, not raw emotional content." In Hermes, safe-mode enforcement spans both `GuinevereSafetyPlugin` (plugin state) and `memory_plugin.py` (memory filtering). The underlying PostgreSQL query remains valid, but the gate implementation must integrate with Hermes plugin lifecycle. |

### 3.4 Consolidation, Commands, Tests (P3-015 to P3-019)

| Step | Title | Classification | Rationale |
|---|---|---|---|
| **P3-015** | Memory Consolidation Job | ✅ **VALID** | Daily episodic→semantic aggregation via APScheduler. This is separate from Hermes context compression (which summarizes conversation context for LLM tokens). Consolidation transforms episodic memory into permanent semantic knowledge. ADR-035 does not modify this job. |
| **P3-016** | /memory-search Command | ⚠️ **NEEDS-UPDATE** | "Search memories via Discord slash command." Post-ADR-035, this command becomes a **Hermes plugin** (`memory_search_plugin.py`), wrapping `recall_for_context()` unchanged. The step prompt should note: (a) command registration via `ctx.register_command()`, (b) supplement results with Hermes `session_search` FTS5 results, (c) DNR enforcement via `memory_plugin.py` pre-injection gate. |
| **P3-017** | /memory-add Command | ⚠️ **NEEDS-UPDATE** | "Manually add memories." Post-ADR-035, this becomes a **Hermes plugin** (`memory_add_plugin.py`), wrapping `store_conversation()` unchanged. The step prompt should note: command registration via `ctx.register_command()`, classification enforcement via `memory_plugin.py`. |
| **P3-018** | Memory E2E Test | ⚠️ **NEEDS-UPDATE** | "Write → Recall → Inject → Verify pipeline works end-to-end." Currently tests direct PostgreSQL pipeline. Should be extended to verify: (a) `memory_plugin.py` bridge correctly wraps write/recall, (b) DNR+classification enforced through Hermes path, (c) Hermes compression does not drop critical PostgreSQL-retrieved memories, (d) session_search returns no DNR-marked content, (e) zero PostgreSQL data modifications from Hermes path. |
| **P3-019** | Performance Benchmark | ⚠️ **NEEDS-UPDATE** | "p95 vector search < 2s, FTS < 500ms, hybrid < 3s." PostgreSQL benchmarks remain valid. Should additionally benchmark: (a) memory_plugin.py bridge latency overhead, (b) Hermes compression latency, (c) Hermes session_search FTS5 latency, (d) mirror sync write overhead (MEMORY.md/USER.md every 5 messages). NFR-P04 target: memory recall p95 < 500ms (warm). |

---

## 4. Summary Table

| Step | Name | Classification | Conflict? | pgvector? | Hermes-Note? |
|---|---|---|---|---|---|
| P3-001 | Alembic Setup | ✅ VALID | No | N/A | No |
| P3-002 | 47 Tables Migration | ✅ VALID | No | Prep (P3-006) | No |
| P3-003 | Migration Verification | ✅ VALID | No | N/A | No |
| P3-004 | SentenceTransformers Model | ✅ VALID | No | No | No |
| P3-005 | Embedding Pipeline | ✅ VALID | No | No | No |
| P3-006 | pgvector HNSW Index | ✅ VALID | No | **Yes** — core | No |
| P3-007 | HNSW Parameter Tuning | ✅ VALID | No | **Yes** | No |
| P3-008 | tsvector FTS Setup | ✅ VALID | No¹ | No | FTS5 confusion¹ |
| P3-009 | Memory Write Pipeline | ✅ VALID | No | **Yes** | No |
| P3-010 | Memory Read Pipeline | ✅ VALID | No | **Yes** | No |
| P3-011 | Hybrid Ranking | ✅ VALID | No | **Yes** | No |
| P3-012 | Context Injection | ⚠️ NEEDS-UPDATE | No | No | **Yes** — via memory_plugin.py |
| P3-013 | Do-Not-Recall | ✅ VALID | No | No | Via memory_plugin.py |
| P3-014 | Safe-Mode Memory Gate | ⚠️ NEEDS-UPDATE | No | No | **Yes** — via GuinevereSafetyPlugin |
| P3-015 | Memory Consolidation | ✅ VALID | No | No | No |
| P3-016 | /memory-search Command | ⚠️ NEEDS-UPDATE | No | **Yes** | **Yes** — Hermes plugin + session_search |
| P3-017 | /memory-add Command | ⚠️ NEEDS-UPDATE | No | **Yes** | **Yes** — Hermes plugin |
| P3-018 | Memory E2E Test | ⚠️ NEEDS-UPDATE | No | **Yes** | **Yes** — test bridge path |
| P3-019 | Performance Benchmark | ⚠️ NEEDS-UPDATE | No | **Yes** | **Yes** — benchmark bridge + compression |

¹ Phase Goal says "FTS5 working" but P3-008 implements PostgreSQL tsvector. FTS5 is Hermes SQLite (session_search). Terminology mismatch in Phase Goal; implementation correct.

**Legend:**
- ✅ **VALID** — Step is directly applicable without modification in hybrid memory architecture
- ⚠️ **NEEDS-UPDATE** — Step content is correct for PostgreSQL+pgvector but needs Hermes bridge integration notes
- ❌ **STALE** — Step references outdated architecture assumptions
- 🚫 **CONFLICT-WITH-HYBRID-MEMORY** — Step contradicts ADR-035 Pillar 2

---

## 5. Steps That DO NOT Conflict with Hybrid Memory

All 19 steps are compatible with ADR-035's hybrid memory architecture. No step:
- Assumes pure relational with no vector search (pgvector is present in P3-006/007)
- Assumes pure vector with no relational (47 tables in P3-002, classification/DNR in P3-013/014)
- Suggests replacing PostgreSQL with Hermes SQLite
- Suggests using cloud memory providers
- Proposes removing DNR, classification, or encrypted profiles

---

## 6. Steps That Need pgvector/Vector Search Additions

The following steps already include pgvector (no additions needed):

| Step | pgvector Coverage |
|---|---|
| P3-006 | ✅ Creates `embedding_vec vector(1536)` column + HNSW index (m=16, ef_construction=64) |
| P3-007 | ✅ Benchmarks HNSW recall vs latency; tunes `hnsw.ef_search` |
| P3-009 | ✅ `store_episode()` writes embedding to `embedding_vec` column |
| P3-010 | ✅ `recall_memories()` uses `<=>` cosine distance for vector search |
| P3-011 | ✅ Hybrid ranking combines vector similarity (pgvector) + FTS + recency |
| P3-019 | ✅ Benchmarks p95 vector search latency |

No step is missing pgvector coverage. The embedding pipeline (1536-dim text-embedding-3-small), HNSW indexing, and vector search queries are all present.

---

## 7. Missing from Phase 3 (Covered by ADR-035 Phase 3 — "Memory Bridge")

P3 establishes the PostgreSQL+pgvector foundation. ADR-035's Phase 3 ("Memory Bridge," 4-5 days) adds the Hermes integration layer. The following items are NOT in P3 steps but ARE in ADR-035 Phase 3:

| ADR-035 Phase 3 Step | Description | Requires P3 Dependency |
|---|---|---|
| 3.1 | Enable Hermes compression at 70% threshold | P3-009, P3-010 |
| 3.2 | Enable Hermes session_search (FTS5) | P3-008 |
| 3.3 | Build PostgreSQL bridge plugin (`memory_plugin.py`, ~180 lines) | P3-009, P3-010 |
| 3.4 | Configure mirror sync (MEMORY.md/USER.md) | P3-002 |
| 3.5 | A/B test memory recall on 100 queries (Hermes vs direct PostgreSQL) | P3-018 |
| 3.6 | Verify zero PostgreSQL data modifications from Hermes path | P3-002 |

**Note:** These are not P3 gaps — they are the Hermes layer that ADR-035 explicitly sequences AFTER the PostgreSQL+pgvector foundation is established. P3 and ADR-035 Phase 3 are complementary, not overlapping.

---

## 8. Terminology Issues

### 8.1 Phase Goal: "FTS5 working"

**Location:** StepPrompts.md line 5908, Phase 3 Transition Checklist (line 5913)

**Issue:** The Phase Goal states "pgvector HNSW indexed, FTS5 working, recall engine functional." FTS5 is a **SQLite** full-text search engine, not a PostgreSQL feature. In ADR-035, FTS5 is used by Hermes's `session_search` (read-only supplement on Hermes SQLite). The actual P3 implementation (P3-008) uses PostgreSQL `tsvector` with GIN index — which is correct for PostgreSQL-based hybrid ranking (Vector+FTS+Recency).

**Recommendation:** Change Phase Goal wording from "FTS5 working" to "FTS working" or "tsvector FTS working" to avoid confusion with Hermes SQLite FTS5. Both FTS systems coexist in the hybrid architecture:
- PostgreSQL `tsvector` → hybrid ranking (part of P3, UNCHANGED in ADR-035)
- Hermes `session_search` (FTS5) → cross-session search (NEW in ADR-035 Phase 3)

---

## 9. Design Decision Notes (ADR-035 Alignment)

### 9.1 Evidence Status

Evidence directories exist at `docs/setup-evidence/P3/` for all 19 steps, including verification files and auditor-gate.md files. This indicates P3 implementation was in progress or completed before ADR-035 was accepted. The evidence predates the Hermes migration decision.

### 9.2 Rollback Safety

ADR-035 explicitly guarantees PostgreSQL+pgvector rollback safety: "Every rollback procedure begins with the universal kill-switch: `hermes gateway stop`. PostgreSQL+pgvector is the primary write authority — all Hermes writes are supplementary read-only. Rollback is code + config + service topology, not data migration." (§1333)

This means P3 PostgreSQL data is never at risk during Hermes migration.

### 9.3 Memory Bridge Refactor

P3 steps reference paths like `src/memory/write_pipeline.py`, `src/memory/read_pipeline.py`, `src/memory/embeddings.py`. Post-ADR-035, these files are **preserved verbatim** (0 lines changed). The bridge refactor (memory_bridge.py → memory_plugin.py) is a NEW file that wraps these existing functions, not a replacement. The P3 pipeline code continues to operate unchanged.

### 9.4 Discord Command Migration

P3-016 and P3-017 define Discord slash commands. ADR-035 maps these to Hermes plugins:
- `/memory search` → `memory_search_plugin.py` (MEDIUM feasibility, wraps `recall_for_context()`)
- `/memory add` → `memory_add_plugin.py` (MEDIUM feasibility, wraps `store_conversation()`)
- `/memory export` → `memory_export_plugin.py` (MEDIUM feasibility)
- `/memory forget` → `memory_forget_plugin.py` (MEDIUM feasibility)

The underlying PostgreSQL operations remain identical; only the command registration and response formatting change.

---

## 10. Footer

| Field | Value |
|---|---|
| Audit scope | Phase 3 Memory System — 19 steps (StepPrompts.md lines 5906–6361) |
| Reference ADR | ADR-035 Hermes Migration (Pillar 2: Memory = HYBRID), accepted 2026-06-04 |
| Related ADRs | ADR-007 (PostgreSQL primary), ADR-009 (pgvector semantic search), ADR-027 (self-hosted PostgreSQL) |
| Evidence base | `docs/setup-evidence/P3/STEP-P3-001` through `STEP-P3-016-019` |
| Research reports | `research-reports/hermes-restructure/` (16 reports), `research-reports/adr-035-prep/` (8 reports) |
| Codebase | 25,796 lines, 113 Python files, `src/memory/` (7 files, 3,941 lines preserved) |
| Auditor | Guinevere (Sisyphus-Junior) |
| Date | 2026-06-05 |
| Verdict | **No conflicts with hybrid memory architecture. 12 VALID, 7 NEEDS-UPDATE (for Hermes bridge integration notes), 0 STALE, 0 CONFLICT.** |
# Phase 3 Memory Bridge: FTS5 Gap Analysis Report

**Date**: 2026-06-04  
**Scope**: Text search implementations, FTS usage, and search-related patterns in the codebase.  
**Objective**: Identify existing capabilities, missing components, and gaps to fill for SQLite FTS5 enablement in Phase 3 Memory Bridge migration.  
**Target Output**: Feed directly into atch-plan-phase-3.md planner gate.

---

## 1. Executive Summary

The Guinevere codebase currently relies **exclusively on PostgreSQL** for canonical memory storage and full-text search (FTS) via 	svector/	squery. There is **no custom Python implementation of SQLite FTS5** in the codebase. 

However, Phase 3 planning documents (ADR-035, phase-3-memory.md) explicitly designate Hermes Agent's native session_search (backed by Hermes' internal SQLite FTS5 at ~/.hermes/state.db) as a **read-only supplement** to PostgreSQL. 

The primary gap is not building a new Python FTS5 engine, but rather **integrating and securing** the Hermes-native FTS5 recall path to ensure it respects Guinevere's strict safety boundaries (DNR exclusion, classification ceilings) which are currently enforced at the PostgreSQL query level.

---

## 2. Current Text Search Implementations (PostgreSQL)

The system already has a robust, production-ready hybrid search pipeline in PostgreSQL.

### 2.1 Schema & Indexing
- **File**: src/memory/models.py
- **Table**: memory.episodes
- **Column**: search_vector (Type: TSVECTOR, Computed)
  - **Expression**: setweight(to_tsvector('english', coalesce(title, '')), 'A') || setweight(to_tsvector('english', coalesce(summary, '')), 'B') || setweight(to_tsvector('english', coalesce(raw_content, '')), 'D')
- **Index**: ix_episodes_search_vector_gin (GIN index on search_vector)

### 2.2 Query Execution
- **File**: src/memory/read_pipeline.py
- **Function**: uild_fts_query(query_text: str, limit: int, exclude_dnr: bool)
- **Implementation**:
  `python
  fts_query = func.plainto_tsquery("english", query_text)
  stmt = (
      select(Episodes)
      .where(Episodes.search_vector.op("@@")(fts_query))
      .order_by(func.ts_rank(Episodes.search_vector, fts_query).desc())
      .limit(limit)
  )
  if exclude_dnr:
      stmt = stmt.where(Episodes.do_not_recall.is_(False))
  `
- **Ranking**: Uses Reciprocal Rank Fusion (RRF, k=60) to combine Vector similarity (VECTOR_WEIGHT = 0.5), FTS rank (FTS_WEIGHT = 0.5), and recency decay. Episodes found by both get a BOTH_SIGNAL_BONUS (x1.25).

### 2.3 Memory Bridge Fallback
- **File**: src/hermes/memory_bridge.py
- **Behavior**: When embedding_service is None, ecall_for_context gracefully degrades to FTS-only search. It also constructs a combined summary_text from both user and assistant messages to maximize FTS keyword matching.

---

## 3. SQLite & FTS5 References in Codebase

### 3.1 Explicit Exclusion of SQLite for Canonical Memory
- **ADR-007 (Memory Storage Backend Selection)**: Explicitly states: *"Use PostgreSQL as the primary durable memory store... Do not use SQLite for canonical Guinevere memory."*
- Evidence scripts (pply_v2_updates.py, generate_adr_batch.py) actively scrub references to SQLite as a primary store.

### 3.2 Hermes Internal SQLite (The Phase 3 Target)
- **Location**: ~/.hermes/state.db (Managed externally by Hermes Agent framework).
- **Purpose**: Transient session state and **FTS5 search indexes** for cross-session browsing.
- **Configuration**: Planned to be enabled via: 
  `ash
  hermes config set memory.session_search.enabled true
  hermes config set memory.session_search.backend "fts5"
  `

---

## 4. session_search Implementation Status

### 4.1 Current State
- **Python Codebase**: **ZERO** implementation of session_search. No Python code queries Hermes' internal SQLite database.
- **Hermes Native**: Hermes provides session_search as a built-in tool/command. The /history command migration plan (gent-5-commands-migration-map.md) indicates this will be handled by a native Hermes plugin (history_plugin.py), not the legacy cmd_history.py.

### 4.2 Planned Architecture (Per ADR-035 & phase-3-memory.md)
- Hermes session_search operates as a **read-only supplement**.
- A new plugins/memory_plugin.py (~180 lines) is planned to wrap existing src/memory/read_pipeline.py functions.
- **Critical Safety Requirement**: Because Hermes FTS5 does not natively understand Guinevere's do_not_recall flag, a post-recall verification gate (erify_recall_results_dnr_free()) **must** be applied to Hermes recall results before they are injected into the LLM context.

---

## 5. Conversation History Search (Current vs. Target)

| Aspect | Current Implementation (Phase 2) | Target Implementation (Phase 3) |
|---|---|---|
| **Data Source** | PostgreSQL memory.episodes | PostgreSQL (Primary) + Hermes SQLite FTS5 (Supplement) |
| **Search Mechanism** | Hybrid: Vector + PostgreSQL FTS + Recency (RRF) | Hermes native session_search (FTS5) + PostgreSQL hybrid |
| **DNR Enforcement** | Query-level (WHERE do_not_recall = false) | **Post-recall gate** (erify_recall_results_dnr_free()) |
| **Classification** | Query-level ceiling enforcement | Post-recall filtering required for Hermes path |
| **Entry Point** | src/memory/read_pipeline.recall_memories() | Hermes plugin wrapping ecall_for_context() |

---

## 6. Identified Gaps for Phase 3 FTS5 Enablement

### Gap 1: Missing Post-Recall DNR Verification Gate for Hermes
- **Issue**: PostgreSQL enforces DNR at the SQL WHERE clause level. Hermes FTS5 has no knowledge of the do_not_recall column.
- **Risk**: HIGH. Hermes session_search could leak DNR-marked content into the LLM context.
- **Action Required**: Implement and enforce erify_recall_results_dnr_free(results) as a mandatory post-search gate for *all* Hermes recall paths before context injection. (Referenced in phase-3-memory.md Step 3.3, but code is currently a stub).

### Gap 2: Classification Ceiling Enforcement on Hermes Results
- **Issue**: Similar to DNR, Hermes FTS5 does not enforce Guinevere's 5-level classification ceiling (Public, Internal, Restricted, Confidential, Critical).
- **Risk**: MEDIUM-HIGH. Sub-agents or Hermes could retrieve Critical data if not filtered.
- **Action Required**: The memory_plugin.py must apply classification filtering to Hermes FTS5 results based on the requesting principal's ceiling.

### Gap 3: Absence of memory_plugin.py Implementation
- **Issue**: The Phase 3 plan describes a plugins/memory_plugin.py that wraps ecall_for_context and applies safety gates. This file does not yet exist in the codebase.
- **Action Required**: Create plugins/memory_plugin.py implementing the MemoryBridgePlugin class with on_load, ecall_for_injection, and get_dnr_audit_count as specified in phase-3-memory.md.

### Gap 4: No Python-Level SQLite FTS5 Query Module (If Custom Access Needed)
- **Issue**: If the architecture requires the Python backend (not just Hermes) to directly query the Hermes SQLite FTS5 index, no such module exists.
- **Action Required**: Clarify in the planner gate whether session_search is exclusively a Hermes-native tool call, or if Python needs a sqlite3 + MATCH query builder. (Current docs suggest the former, making this gap informational).

### Gap 5: A/B Testing Harness for Recall Quality
- **Issue**: Phase 3 requires an A/B test (scripts/ab_test_recall.py) to ensure enabling compression and FTS5 does not degrade recall precision (p > 0.05). This script does not exist.
- **Action Required**: Develop the A/B testing harness to compare PostgreSQL-only recall vs. PostgreSQL + Hermes FTS5 recall on a fixed query set.

---

## 7. Recommendations for Planner Gate (atch-plan-phase-3.md)

1. **Define Step 3.2 (Enable Hermes session_search)** as a configuration-only step, but pair it immediately with **Step 3.3 (Build PostgreSQL Bridge Plugin)** which must include the DNR post-recall gate.
2. **Add a Hard Rejection Criterion** to the planner scaffold: *"Zero DNR entries in Hermes session_search results verified by erify_recall_results_dnr_free()."*
3. **Explicitly forbid** any Python code from writing to ~/.hermes/state.db. All writes must continue to flow through src/memory/write_pipeline.py to PostgreSQL.
4. **Prioritize Gap 5**: The A/B test script must be written and validated *before* enabling FTS5 in production, as rollback is trivial (< 3 mins) but detection of recall degradation is critical.

---

## 8. Reference Files

| File Path | Relevance |
|---|---|
| src/memory/models.py | PostgreSQL TSVECTOR schema definition and GIN index. |
| src/memory/read_pipeline.py | Core uild_fts_query and hybrid RRF ranking logic. |
| src/hermes/memory_bridge.py | Current bridge; fallback to FTS-only when embeddings unavailable. |
| src/hermes_plugins/commands_memory/memory_search.py | Hermes command plugin delegating to PostgreSQL read pipeline. |
| dr/ADR-035-hermes-migration.md | Architectural decision: Hermes FTS5 as read-only supplement. |
| docs/setup-evidence/hermes-migration/phase-3-memory.md | Detailed Phase 3 procedure, config changes, and risk register. |
| docs/setup-evidence/hermes-migration/batch-plan-migration.md | Master migration plan referencing FTS5 enablement steps. |

---
*Generated by Guinevere Research Agent for Phase 3 Planning.*

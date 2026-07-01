# P3 (Memory Foundation) Downstream Dependency Matrix

**Audit metadata:**
- **Date:** 2026-06-25
- **Agent:** P3 implementation audit subagent
- **Read-only affirmation:** TRUE -- no runtime code, no DB mutations, no secrets touched
- **Scope:** Map every downstream phase's dependency on P3 memory surfaces and identify gaps/risks

---

## Status Verdict

**VERIFIED IMPLEMENTED** -- P3 is the write/read/embedding/consolidation/DNR spine of the memory system. All downstream phases depend on it. P3 surfaces are extended, not superseded, by later phases.

**Severe findings:** 2 (P19 project_id missing from SemanticFacts/KnowledgeGraph ORM models; P20 HARD STOP safe_mode not propagated to memory recall in observe_node)

---

## Methodology

For each downstream phase (P4/P5/P8/P16/P18/P19/P20/P21/P22/P23/P24), I read:
1. The phase's plan/research docs under `docs/setup-evidence/{P16,P18,P19,P20,P21,P22,P23,P24}/`
2. The phase's adapter code under `src/`
3. The P3 memory surface files (`src/memory/{read_pipeline,write_pipeline,models,consolidation,dnr,__init__}.py`)
4. Cross-references via `grep` for `recall_memories`/`store_episode` across the repo

---

## Dependency Matrix

| Downstream Phase | P3 Surface Used | Supported? | Gap / Risk |
|---|---|---|---|
| **P4 Persona** | `memory.persona_state` table, `memory.emotional_events`, `memory.inner_journal` | **YES** | P4 writes to these tables via separate FSM modules (yandere, reward, punishment, mood). P3 does NOT read them in recall (correct -- persona state is injected via Hermes plugin, not memory recall). |
| **P5 Agent Loop** | `recall_memories()`, `store_episode()`, `build_safe_content()`, DNR exclusion | **YES** | P5 evidence (STEP-P5-001..010) shows wiring via `HermesMemoryBridge`. No gap. `src/hermes/_memory_bridge.py:93` calls `recall_memories()`; `:216` calls `store_episode()`. |
| **P8 MVP/Observability** | `memory.health_check`, `memory.backup_log`, `memory.migration_log` tables | **YES** | P8 reads ops tables. No direct P3 pipeline dependency. E2E test discovery (`pytest tests/`) collects memory tests. Non-blocking. |
| **P16 Knowledge Graph** | `memory.knowledge_graph` table, `memory.semantic_facts` ORM, KG ingestion hook in `consolidation.py` (`kg_ingestion_enabled`), KG 4th RRF signal in `read_pipeline.py` (`KG_WEIGHT=0.20`) | **YES -- with gap** | COMPLETE integration: P16 has 4 production hooks into P3 (consolidation post-hook, recall RRF signal, prompt_loader, memory_bridge). **GAP**: `knowledge_graph` and `semantic_facts` ORM models in `models.py` do NOT have `project_id`/`project_scope` columns (no P19 namespace support). The `knowledge_graph` table at lines 391-405 and `SemanticFacts` class at lines 208-263 lack the P19 project_id fields that `Episodes` has. P16 integration itself is complete. P16 does NOT supersede P3 recall -- it adds a 4th RRF signal inside P3. |
| **P18 Advanced Memory** | `tiers.py`, `spaced_repetition.py`, FSRS-6 columns on `Episodes` ORM, decay sweep (`consolidation.py`), 5th RRF signal (`FSRS_WEIGHT=0.15`) | **YES** | P18 is ADDITIVE to P3, not superseding. The read_pipeline was extended with `fsrs_enabled` parameter (line 800), FSRS retrievability bonus (line 1051-1066), and reconsolidation-on-retrieval (line 1033-1076). The write path is unchanged. The decay sweep (`decay_sweep_job`, line 928) independently queries Episodes for retrievability-based archiving. No gap. |
| **P19 Namespace (Multi-Project Context)** | `store_episode` `project_id` parameter, `recall_memories` `project_id` parameter, `build_*_query` `project_id` filter in WHERE (`project_id == :project_id OR project_scope == 'global'`) | **PARTIAL** | **CRITICAL GAP**: P3 `Episodes` ORM (lines 179-187) already HAS `project_id` + `project_scope` columns. P3 `build_vector_query`, `build_fts_query`, `build_recency_query` (lines 536-641) ALREADY accept `project_id` and filter via `WHERE project_id == :project_id OR project_scope == 'global'`. `store_episode` (line 125-127) ALREADY accepts `project_id`/`project_scope`. **HOWEVER**: `SemanticFacts` (lines 208-263) and `KnowledgeGraph` (lines 391-405) ORM classes DO NOT have `project_id` columns. P19 research (`p19-memory-namespace-research.md` SS2.1, 2.2) incorrectly states "None" for project_id columns everywhere -- the `Episodes` ORM already has them, but SemanticFacts and KG do not. P19-004 plan must add project_id to SemanticFacts and KnowledgeGraph (not just Episodes). P18 adapter (`p18_adapter.py:86-97`) already passes `project_id` to `recall_memories` -- adapter is ahead of P19 implementation. |
| **P20 Living Autonomy Kernel** | `recall_memories()` via `p18_adapter.MemoryRecallAdapter`, `build_safe_content()`, DNR exclusion, classification ceiling, token budget | **YES -- with gap** | **HIGH GAP: HARD STOP safe_mode propagation.** `graph.py:observe_node` (lines 231-280) calls `kg_adapter.recall()` and `memory_adapter.recall()` but does NOT pass `safe_mode=True` when HARD STOP is active. The `hard_stop_requested` flag is only used in `decide_node` to route to END. If HARD STOP is active, memory recall still returns full content (no safe-mode substitution). P20 must either: (a) propagate `safe_mode` flag through `observe_node` to the adapters when HARD STOP is active, or (b) add a safe-mode gate in the `memory_adapter.recall()` path. Currently P18 adapter (`p18_adapter.py:92-97`) only wires `query_text`, `principal`, `exclude_dnr`, `project_id` -- no `safe_mode` parameter. P20 `cognition.py:memory()` loop (line 339) is a placeholder and does not call P3 memory at all. `idle_node` (graph.py:678-715) reads `recalled_memories` from state but only uses metadata (relevance, timestamp) -- no raw content, which is correct for privacy. The P18 adapter does NOT pass `safe_mode=True` anywhere. |
| **P21 Voice Interface** | `store_episode()` with `episode_type='voice_turn'`, `memory.episodes`, `surveillance.events.raw_payload` for raw audio | **YES** | P21 research (`p21-memory-transcript-research.md`) exhaustively maps P3 surfaces. Transcript goes to `memory.episodes` with `source='voice'`, `episode_type='voice_turn'`, `classification='Restricted'` default, Critical for intimate/safe-word content. Raw audio (if retained) goes to `surveillance.events.raw_payload` for max 24h. DNR flag reuses existing mechanism. Consent revocation cascades via `do_not_recall=True`. P3 write pipeline supports every column needed. No gap. |
| **P22 Raw Access Hub** | `store_episode()`, `recall_memories()`, `memory.episodes`, `memory.semantic_facts`, DNR suppression/delete | **YES -- with risk** | **MEDIUM RISK: AuthLevel-only gating bypass.** P22 plan (v2.0 full-capability) describes external data ingest into memory/KG. P3 store_episode has classification guards (Critical requires sanitized summary) but no AuthLevel gate. If P22 uses a raw recall/insert path that bypasses HermesMemoryBridge (which has MEM-001..008 injection gates), external untrusted data could enter memory without quarantine. The plan identifies this (MEM-001..008 gates) but the P3 write pipeline itself has no caller-identity gate -- any code with a DB session can call `store_episode()`. Mitigation: P22 must route through `HermesMemoryBridge` or an equivalent injection-gated facade, not call `store_episode()` directly with untrusted data. P3 `dnr.py` can mark external memories DNR. P3 `build_safe_content()` can redact/block by classification. |
| **P23 Embodied Operations** | `recall_memories()` via `p18_adapter.MemoryRecallAdapter` for action context, `store_episode()` for action audit, DNR for action evidence suppression | **YES** | P23 research (`p23-p20-life-kernel-action-dependency-map.md`) maps P18 adapter usage for action context. Action outcomes are recorded as observations via `BackgroundCognition._write_to_graph()`, not directly via `store_episode`. P23 action audit goes to `PostgresAuditJournal` (independent table), not P3 episodes. P3 DNR `mark_memory_dnr` can suppress action evidence if needed. P3's safe-mode content substitution can block action-related Critical content. P23's own `P23ExecutorBase` has a pre-action HARD STOP check but does NOT change P3's safe_mode behavior. The HARD STOP propagation gap identified for P20 also applies to P23 (action context comes from P3 recall which does not respect safe_mode). |
| **P24 Hermes Fork Convergence** | `recall_memories()` via `HermesMemoryBridge`, `store_episode()`, embedding model, DNR, classification ceiling, token budget | **YES -- fork must preserve** | P24 research (`p24-memory-kg-persona-safety-convergence-research.md`) identifies P3 memory as needing a native `MemoryProvider` protocol in forked Hermes. The current `HermesMemoryBridge` adapter pattern works. A fork must preserve: (1) the 5-signal RRF fusion (vector + FTS + recency + KG + FSRS), (2) classification ceiling resolution, (3) safe-mode content substitution, (4) DNR exclusion, (5) token budget enforcement, (6) project_id namespace filtering. The `GuinevereSafetyPlugin` and `PersonaPlugin` are already native Hermes plugins and need no fork changes. P3 memory is the primary driver for the fork decision. |

---

## Summary: P3 Surfaces Used by Downstream Phases

### P3 Tables Accessed

| Table | Schema | Downstream Consumers |
|-------|--------|---------------------|
| `episodes` | `memory` | P4, P5, P16 (via consolidation), P18, P19, P20, P21, P22, P23, P24 |
| `session_summaries` | `memory` | P5 (compaction) |
| `semantic_facts` | `memory` | P16 (consolidation output), P22, P24 |
| `knowledge_graph` | `memory` | P16, P20, P22, P24 |
| `emotional_events` | `memory` | P4 |
| `inner_journal` | `memory` | P4 |
| `persona_state` | `persona` | P4 |
| `faiz_profile` | `memory` | P4 |
| `audit_trail` | `audit` | P5, P20, P21 |
| `faiz_predictions` | `memory` | P4 |

### P3 Functions Exported via `src/memory/__init__.py`

| Function | Downstream Consumers (direct import or adapter) |
|----------|-------------------------------------------------|
| `recall_memories()` | P5 (HermesMemoryBridge), P16 (RRF fusion), P18, P20 (p18_adapter), P22, P24 |
| `store_episode()` | P5 (HermesMemoryBridge), P21, P22, P24 |
| `store_episode_batch()` | P22 (batch ingest) |
| `consolidate_episodes_to_facts()` | P16 (KG ingestion hook), P18 (FSRS review) |
| `mark_memory_dnr()` / `unmark_memory_dnr()` | P5 (Discord command), P22 (DNR external data) |
| `is_memory_dnr()` | P5, P20 |
| `verify_recall_results_dnr_free()` | P5 (pre-injection gate) |
| `EmbeddingService.aembed()` | P5, P16, P18, P22 |

---

## Phase-by-Phase Detailed Analysis

### P4 Persona Memory

- **Used tables:** `persona_state`, `drift_log`, `mood_history`, `punishment_log`, `reward_log` (all `persona` schema) + `emotional_events`, `inner_journal`, `faiz_predictions`, `faiz_profile` (all `memory` schema)
- **P3 pipeline usage:** None -- P4 reads/writes these tables via dedicated FSM modules, not through `recall_memories`/`store_episode`
- **Verdict:** No gap. P4 is properly independent of the P3 pipeline because persona state is injected via Hermes plugin, not memory recall. However, P4 tables lack `project_id` columns (P19 gap).

### P5 Agent Loop

- **Used surfaces:** Both P3 pipeline functions: `recall_memories()` (PRE call context assembly), `store_episode()` (POST call memory persistence), DNR API, classification ceiling
- **Evidence:** `src/hermes/_memory_bridge.py` -- the bridge is the canonical P5->P3 integration point
- **Verdict:** Fully supported. No gap.

### P8 MVP/Observability

- **Used surfaces:** Memory metrics (count, health status), not pipeline functions
- **Verdict:** Non-blocking. P3 `memory.health_check` table exists for ops schema.

### P16 Knowledge Graph

- **Used surfaces:**
  1. `SemanticFacts` ORM -- target table for consolidation output
  2. KG ingestion hook in `consolidation.py:456-489` -- post-consolidation call to `KGIngestionPipeline`
  3. KG 4th RRF signal in `read_pipeline.py:947-987` -- `KG_WEIGHT=0.20` in `recall_memories()` when `kg_enabled=True`
  4. `KnowledgeGraph` table (`memory.knowledge_graph`) -- entity relationship store
- **Evidence:** `src/memory/read_pipeline.py:947-987`, `src/memory/consolidation.py:456-489`, `src/memory/models.py:208-263 (SemanticFacts), 391-405 (KnowledgeGraph)`
- **Verdict:** Fully integrated. P16 adds a 4th RRF signal inside P3's recall pipeline -- it does NOT supersede or replace P3 recall.
- **Gap:** Both `SemanticFacts` and `KnowledgeGraph` ORM classes lack `project_id`/`project_scope` columns. `src/memory/models.py:208-263` (SemanticFacts) and `:391-405` (KnowledgeGraph) have no project namespace support, unlike Episodes (lines 179-187).

### P18 Advanced Memory

- **Used surfaces:**
  1. `Episodes` ORM extended with FSRS columns (tier, fsrs_state, retrievability, stability, difficulty) -- `models.py:153-177`
  2. 5th RRF signal in `read_pipeline.py` -- `FSRS_WEIGHT=0.15`, `fsrs_enabled` parameter
  3. Reconsolidation-on-retrieval -- `read_pipeline.py:1025-1076`, grade=Good on recalled episodes
  4. Decay sweep in `consolidation.py:928-1079` -- queries Episodes for retrievability-based archiving
- **Evidence:** `src/memory/tiers.py`, `src/memory/spaced_repetition.py`, `src/memory/read_pipeline.py:1025-1076`, `src/memory/consolidation.py:55-75 (decay sweep constants), 928-1079`
- **Verdict:** P18 is additive. It extends the P3 Episodes ORM, adds a 5th RRF signal, and adds reconsolidation-on-retrieval hooks. P3 read/write pipelines remain the canonical paths. No gap.

### P19 Multi-Project Context

- **Used surfaces:**
  1. `Episodes` ORM `project_id`/`project_scope` columns -- models.py:179-187 (ALREADY EXISTS)
  2. `build_vector_query`, `build_fts_query`, `build_recency_query` `project_id` parameter -- read_pipeline.py:536-641 (ALREADY SUPPORTS filtering)
  3. `store_episode()` `project_id`/`project_scope` parameters -- write_pipeline.py:125-127 (ALREADY SUPPORTS)
  4. `recall_memories()` `project_id` parameter -- read_pipeline.py:801 (ALREADY SUPPORTS)
  5. `p18_adapter.MemoryRecallAdapter` passes `project_id` to `recall_memories` -- p18_adapter.py:86-97 (ALREADY WIRED)
- **CRITICAL GAP 1:** P19 research (`p19-memory-namespace-research.md` SS2.2) incorrectly states "None" for project_id columns on all memory tables. The Episodes ORM already has `project_id` + `project_scope` (since p19_001 migration). The research was written from a stale snapshot.
- **CRITICAL GAP 2:** `SemanticFacts` (models.py:208-263) and `KnowledgeGraph` (models.py:391-405) do NOT have `project_id`/`project_scope` columns. P19-004 must add these. Without them, P19 memory isolation is incomplete: P16-derived recall (4th RRF signal) and semantic_fact-based context will leak across projects.
- **Verdict:** PARTIALLY SUPPORTED. Episodes have namespace support (ORM, pipeline, adapter all wired). SemanticFacts and KnowledgeGraph do NOT.

### P20 Living Autonomy Kernel

- **Used surfaces:**
  1. `p18_adapter.MemoryRecallAdapter.recall()` calls `recall_memories()` -- heart of `observe_node` context gathering
  2. `p16_adapter.KGRecallAdapter.recall()` calls KG query surface (P16, which itself depends on P3 consolidation)
  3. `recall_memories` results populate `recalled_memories` and `recalled_concepts` in `LifeMindState`
  4. `idle_node` reads `recalled_memories` metadata for self-directed task generation
  5. `_make_brain_decide` feeds memory metadata into HermesBrain prompts (AC-LIFE-005)
- **HIGH GAP: HARD STOP safe_mode propagation.** `graph.py:observe_node` calls memory adapters but never passes `safe_mode=True`. When `hard_stop_requested` is set, the kernel routes to END via `decide_node`, but the observe step still recalls full memory content. The `p18_adapter.py:92-97` call to `recall_memories()` passes `principal` and `exclude_dnr` but NOT `safe_mode`. If safe_mode should be active during HARD STOP (per PersonaSafetyPolicy), this is a privacy gap. **Mitigation:** Fall-soft by design -- adapters return degraded results on error, not raw content. But the explicit safe_mode flag is never set.
- **Verdict:** SUPPORTED with the safe_mode propagation gap. P20 cognition.py memory loop is a placeholder (line 339-351) and does NOT call P3 memory -- real integration is deferred.

### P21 Voice Interface

- **Used surfaces:**
  1. `store_episode()` for text transcripts -- `episode_type='voice_turn'`, `source='voice'`
  2. `surveillance.events.raw_payload` for raw audio (24h max if retained)
  3. `episodes.do_not_recall` for safe-word/distress content
  4. `episodes.classification` for Critical content (intimate/safe-word)
  5. `audit.audit_trail` for safety events
  6. `consent.revocation_log` for consent revocation cascade
- **Evidence:** P21 research `p21-memory-transcript-research.md` -- exhaustive mapping of every P3 column
- **Verdict:** Fully supported. P3 write pipeline has every column P21 needs. The MEM-001..008 injection gates are external to P3 (in HermesMemoryBridge), not a P3 responsibility. No gap.

### P22 Raw Access Hub

- **Used surfaces:**
  1. `store_episode()` / `store_episode_batch()` -- external data ingest
  2. `recall_memories()` -- data retrieval
  3. `memory.episodes` -- primary storage table
  4. `memory.semantic_facts` -- fact extraction
  5. DNR API (`mark_memory_dnr`) -- content suppression
  6. Classification system (Public..Critical) -- access control
- **MEDIUM RISK: AuthLevel-only gating bypass.** P3 `store_episode()` has classification guards (Critical requires sanitized summary) but no caller-identity gate. Any code with a DB session can inject episodes. P22 must route through `HermesMemoryBridge` (which enforces MEM-001..008 injection gates) for external untrusted data. Direct `store_episode()` calls from P22 bypass injection gates.
- **Verdict:** SUPPORTED with gating risk. The surface is technically capable of supporting raw external data ingest. The injection gate enforcement is a P22 architectural responsibility.

### P23 Embodied Operations

- **Used surfaces:**
  1. `recall_memories()` via `p18_adapter.MemoryRecallAdapter` for action context (DecisionContextBuilder)
  2. `store_episode()` for action audit memory (optional, primary audit path is PostgresAuditJournal)
  3. `dnr.mark_memory_dnr` for action evidence suppression
  4. `build_safe_content()` for action context classification filtering
- **Evidence:** P23 research `p23-p20-life-kernel-action-dependency-map.md` SS3.6 (Decision Context), SS3.6.2 (Journal Integration)
- **Verdict:** SUPPORTED. P23 action outcomes go to the journal, not directly to P3 episodes. P23's DecisionContextBuilder uses P18 adapter (which calls P3 recall) for context. The same HARD STOP safe_mode gap as P20 applies -- action context may include safe-mode-violating content during HARD STOP. No additional gap beyond P20's.

### P24 Hermes Fork Convergence

- **Used surfaces:**
  1. `recall_memories()` -- must become native Hermes `MemoryProvider`
  2. `store_episode()` -- must become native Hermes `MemoryProvider`
  3. `EmbeddingService` -- OpenRouter-compatible, must be preserved in fork
  4. DNR API -- must be exposed in forked runtime
  5. Classification ceiling + safe-mode -- must be preserved
  6. 4th (KG) and 5th (FSRS) RRF signals -- must be preserved in forked recall
  7. `project_id` namespace filtering -- must be preserved
- **Evidence:** P24 research `p24-memory-kg-persona-safety-convergence-research.md` -- P3 identified as needing `MemoryProvider` protocol in forked Hermes
- **Verdict:** SUPPORTED for current adapter pattern. A Hermes fork must preserve the full P3 recall pipeline (5 signals, DNR, classification, safe-mode, token budget, project filtering). P3 is the primary fork driver. No gap -- this is a planned integration path.

---

## Dependency Graph

```
P3 (Foundation -- 47 tables, read/write pipeline, DNR, consolidation, embeddings, FSRS)
 |
 +-- P4 Persona (reads tables directly via FSM modules -- NOT via P3 pipeline)
 +-- P5 Agent Loop (HermesMemoryBridge -> recall_memories/store_episode)
 |    +-- P8 MVP (indirect -- ops tables)
 |
 +-- P16 Knowledge Graph (extends P3 consolidation + adds 4th RRF signal in P3 recall)
 |    +-- P20 Life Kernel (via p16_adapter in observe_node)
 |
 +-- P18 Advanced Memory (extends P3 Episodes ORM + adds 5th RRF signal in P3 recall)
 |    +-- P20 Life Kernel (via p18_adapter in observe_node)
 |    +-- P23 Embodied Ops (via DecisionContextBuilder)
 |
 +-- P19 Namespace (Episodes ALREADY have project_id; SemanticFacts/KG DO NOT)
 |    +-- P20, P21, P22, P23, P24 (all inherit P19 namespace contract)
 |
 +-- P20 Life Kernel (core consumer: p18_adapter, p16_adapter, observe_node, idle_node)
 |    +-- P21 Voice (via Hermes turn core)
 |    +-- P22 Raw Access (via sensor adapters)
 |    +-- P23 Embodied Ops (via action planner + DecisionContextBuilder)
 |    +-- P24 Hermes Fork (via MemoryProvider protocol)
 |
 +-- P21 Voice (store_episode for transcripts)
 +-- P22 Raw Access (store_episode/recall_memories for external data)
 +-- P23 Embodied Ops (recall_memories for action context)
 +-- P24 Hermes Fork (recall_memories/store_episode -> native MemoryProvider)
```

---

## Severe Findings Summary

### FINDING-01 [CRITICAL] -- SemanticFacts and KnowledgeGraph ORM lack project_id

- **Location:** `src/memory/models.py:208-263` (SemanticFacts), `:391-405` (KnowledgeGraph)
- **Impact:** P19 memory isolation is broken for non-Episodes tables. P16 KG recall (4th RRF signal in `read_pipeline.py`) and semantic_fact-based context (used by P16 consolidation) WILL leak across projects.
- **Affected phases:** P19 (primary), P20, P22, P23, P24
- **Status:** NOT MITIGATED. The P19 plan correctly identifies this as P19-004 work, but the models are NOT updated.

### FINDING-02 [HIGH] -- P20 observe_node does not propagate safe_mode to memory recall during HARD STOP

- **Location:** `src/life_kernel/graph.py:231-280` (observe_node), `src/life_kernel/p18_adapter.py:92-97` (memory_recall call)
- **Impact:** When HARD STOP is active, memory recall returns full content (no safe-mode substitution). The `hard_stop_requested` flag only affects routing in `decide_node`.
- **Affected phases:** P20 (primary), P23 (action context via DecisionContextBuilder)
- **Status:** NOT MITIGATED. The p18_adapter does not accept or pass `safe_mode`. Adding `safe_mode=True` when `hard_stop_requested` is set would be a minimal fix.

### FINDING-03 [MEDIUM] -- P22 AuthLevel bypass risk via direct store_episode

- **Location:** `src/memory/write_pipeline.py:111-237` (no caller identity check)
- **Impact:** Any subsystem with a DB session can call `store_episode()` directly, bypassing HermesMemoryBridge's MEM-001..008 injection gates.
- **Affected phases:** P22 (primary)
- **Status:** Architectural responsibility of P22, not a P3 bug. P3 write pipeline is intentionally generic.

### FINDING-04 [MEDIUM] -- P19 research incorrectly claims zero project_id columns in memory

- **Location:** `docs/setup-evidence/P19/research/p19-memory-namespace-research.md` SS2.2
- **Impact:** The research was based on a stale snapshot. The Episodes ORM already has project_id/scope. This may cause redundant or conflicting migration work in P19-004.
- **Affected phases:** P19 (planning documentation)
- **Status:** Documentation gap only. P19 implementation must verify actual ORM state before writing migrations.

---

## Recommendations (NO FIXES -- for mama consideration)

1. **P19-004 must add project_id to SemanticFacts and KnowledgeGraph ORM** before claiming memory isolation is complete.
2. **P20 should add safe_mode=True to memory recall when HARD STOP is active** -- a simple check in `observe_node` before calling adapters.
3. **P19-004 migration script should verify actual ORM state** (Episodes already has columns; SemanticFacts/KG do not) rather than assuming zero project_id columns exist.
4. **P22 architecture must mandate HermesMemoryBridge routing** for external untrusted data ingest, not direct store_episode() calls.
5. **P24 fork plan must preserve all 5 RRF signals** (vector, FTS, recency, KG, FSRS) plus DNR, classification ceiling, safe-mode, token budget, and project_id filtering.

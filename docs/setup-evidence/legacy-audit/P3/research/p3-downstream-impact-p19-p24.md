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
# P3 (Memory Foundation) Downstream Compatibility — P19 through P24 (+P16/P18/P20)

**Audit metadata:**
- **Date:** 2026-06-25
- **Agent:** P3 downstream compatibility audit subagent
- **Read-only affirmation:** TRUE -- no runtime code, no DB mutations, no secrets touched
- **Scope:** Verify every downstream phase (P19/P20/P21/P22/P23/P24 + P16/P18) that depends on P3 memory surfaces. Read actual code signatures and call sites. Cross-reference against the research file (`P3-DOWNSTREAM-DEPENDENCY-MATRIX.md`). Mark blockers, severity-tag, cite file:line.
- **Input research:** `docs/setup-evidence/legacy-audit/P3/P3-DOWNSTREAM-DEPENDENCY-MATRIX.md`
- **Files verified:** `src/memory/read_pipeline.py`, `write_pipeline.py`, `models.py`, `consolidation.py`, `dnr.py`, `src/life_kernel/graph.py`, `p18_adapter.py`, `p16_adapter.py`, `cognition.py`, `src/hermes/_memory_bridge.py`, `src/core/services/prompt_loader.py`

---

## Status Verdict

**IMPLEMENTED WITH BUGS** -- P3 surfaces are largely mature and correctly extended by downstream phases. However, three new gaps were found beyond the existing dependency matrix: `store_episode_batch` does NOT forward `project_id`, `consolidate_episodes_to_facts` has no project_id awareness at all, and the life-kernel `observe_node` -> `p18_adapter` -> `recall_memories` chain never passes `safe_mode` despite the upstream `recall_memories` supporting it.

**Severe findings:** 3 (1 CRITICAL, 1 HIGH, 1 MEDIUM -- see below)

---

## Verification Results by Downstream Phase

### P19 (Multi-Project Context) -- PARTIALLY IMPLEMENTED

**What was claimed:** `recall_memories` and `store_episode` accept `project_id`. Episodes ORM has columns. SemanticFacts and KG ORM DO NOT have project_id.

**What was verified in code:**

| Surface | File:Line | project_id Support? |
|---|---|---|
| `recall_memories()` parameter | `read_pipeline.py:801` | YES -- `project_id: uuid.UUID \| None = None` |
| `build_vector_query()` parameter | `read_pipeline.py:535` | YES -- filters at lines 563-569 |
| `build_fts_query()` parameter | `read_pipeline.py:577` | YES -- filters at lines 600-606 |
| `build_recency_query()` parameter | `read_pipeline.py:614` | YES -- filters at lines 634-640 |
| `store_episode()` parameters | `write_pipeline.py:125-126` | YES -- `project_id` + `project_scope` |
| `store_episode_batch()` call | `write_pipeline.py:260-275` | **NO -- does NOT forward project_id/scope** |
| Episodes ORM columns | `models.py:179-187` | YES -- `project_id` + `project_scope` both present |
| SemanticFacts ORM columns | `models.py:208-263` | **NO -- no project_id column** |
| KnowledgeGraph ORM columns | `models.py:391-405` | **NO -- no project_id column** |
| `consolidate_episodes_to_facts()` | `consolidation.py:275-282` | **NO -- no project_id parameter; creates SemanticFacts without project_id** |
| `SemanticFacts` constructor in consolidation | `consolidation.py:387-397` | **NO -- no project_id passed to SemanticFacts()** |
| `p18_adapter.MemoryRecallAdapter.recall()` | `p18_adapter.py:92-97` | YES -- forwards `project_id` from context |
| `p16_adapter.KGRecallAdapter.recall()` | `p16_adapter.py:86-88` | YES -- forwards `project_id` from context |

#### FINDING-P19A [CRITICAL] -- store_episode_batch loses project_id

- **Location:** `src/memory/write_pipeline.py:260-275`
- **Evidence:** The `store_episode_batch()` function calls `store_episode()` at line 262 with explicit keyword arguments for `content`, `source`, `classification`, `importance`, `title`, `summary`, `episode_type`, `tags`, `metadata`, `embedding_service`, `started_at` -- but does NOT pass `project_id` or `project_scope`. The indirection between dict fields and `store_episode` parameters means batch-imported data via P22 would silently lose namespace isolation.
- **Impact:** If P22 batch-ingests external memories via `store_episode_batch()`, those episodes are always created as global-scope entities (default `project_id=None`), defeating the purpose of P19 project isolation. The ORM column defaults are `NULL` for `project_id` and `'project'` for `project_scope` -- so batch episodes get `project_scope='project'` with `project_id=NULL`, which means they are invisible to any project-scoped recall (since `project_id == NULL` never matches `project_id == <real UUID>`).
- **Upstream research was INCORRECT:** The existing dependency matrix (`P3-DOWNSTREAM-DEPENDENCY-MATRIX.md`) claims `store_episode_batch()` is supported. It is NOT for `project_id`.

#### FINDING-P19B [HIGH] -- Consolidation has zero project_id awareness

- **Location:** `src/memory/consolidation.py:275-497`
- **Evidence:** `consolidate_episodes_to_facts()` signature at line 275 has no `project_id` parameter. The `SemanticFacts()` constructor at lines 387-397 does not set `project_id` because the ORM model (verified at `models.py:208-263`) lacks the column entirely. This means ALL consolidated facts are global-scope with no namespace tagging.
- **Impact:** When P19 project isolation is active, facts extracted from a project-isolated episode via daily consolidation will be global. Those facts leak to every project via the KG recall path (P16 4th RRF signal). The KG recall data from `p16_adapter.py` returns concepts with no project filter because `SemanticFacts` has no `project_id` column.
- **Affects:** P19 (primary), P16 (leaks facts across projects via KG recall), P20/P23 (consume KG recall in observe_node)

#### FINDING-P19C [MEDIUM] -- P19 research was written from stale snapshot

- **Location:** `docs/setup-evidence/P19/research/p19-memory-namespace-research.md` (SS2.2)
- **Evidence:** The research document allegedly states "None" for project_id columns on all memory tables. The Episodes ORM already has `project_id`+`project_scope` (since `p19_001` migration, verified at `models.py:179-187`). The research was correct about SemanticFacts and KG missing these columns. The stale claim could cause redundant migration work.
- **Impact:** Documentation gap only. P19 implementation must verify actual ORM state before writing migrations.

---

### P20 (Living Autonomy Kernel) -- IMPLEMENTED WITH BUGS

**What was claimed:** P20 calls P3 recall via `p18_adapter.MemoryRecallAdapter` in `observe_node`. `cognition.py` memory loop is a placeholder. HARD STOP safe_mode is NOT propagated.

**What was verified in code:**

| Surface | File:Line | Status |
|---|---|---|
| `graph.py:observe_node` calls `memory_adapter.recall()` | `graph.py:261-265` | **VERIFIED** -- `mem_result = await memory_adapter.recall(recall_context)` |
| recall_context dict has safe_mode | `graph.py:247` | **MISSING** -- only `query` and `content` keys |
| `p18_adapter.recall()` passes safe_mode | `p18_adapter.py:92-97` | **MISSING** -- only `query_text`, `principal`, `exclude_dnr`, `project_id` |
| `decide_node` routes to END on HARD STOP | `graph.py:372-376` | **VERIFIED** -- `if state.get("hard_stop_requested"): return {"decision": "end"}` |
| safe_mode available upstream in recall_memories | `read_pipeline.py:795` | **VERIFIED** -- `safe_mode: bool = False` parameter EXISTS |
| `cognition.py:memory()` calls P3 recall | `cognition.py:339-351` | **VERIFIED as PLACEHOLDER** -- no real P3 wiring |
| `p18_adapter.recall()` accepts safe_mode from context | `p18_adapter.py:48` | **NOT POSSIBLE** -- adapter signature does not look for `safe_mode` in context dict |

#### FINDING-P20A [HIGH] -- safe_mode never reaches memory recall during HARD STOP

- **Location:** `src/life_kernel/graph.py:231-265` (observe_node), `src/life_kernel/p18_adapter.py:92-97` (adapter call)
- **Evidence:** The chain is: `graph.py:observe_node` builds `recall_context` at line 247 (only `query` and `content` keys) -> calls `memory_adapter.recall(recall_context)` at line 263 -> `p18_adapter.py:MemoryRecallAdapter.recall()` at line 92 calls `await self.memory_client(query_text=..., principal=..., exclude_dnr=..., project_id=...)` with NO `safe_mode` keyword. Meanwhile `decide_node` at line 373 checks `hard_stop_requested` and routes to END -- but this is AFTER `observe_node` has already executed. The ordering is: observe -> decide -> reflect -> ... So on a HARD STOP cycle, observe_node recalls full memory content without safe-mode substitution, then decide_node routes to END. The content was already processed unsafely.
- **Mitigation exists at prompt_loader level but not graph level:** `prompt_loader.py:251-254` resolves safe_mode via `hard_stop_handler.is_safe`, but prompt_loader is in the Hermes prompt assembly path (P5), not the life-kernel graph (P20). The graph's observe_node is separate from HermesBrain prompt injection.
- **Impact:** During HARD STOP, full-content memory is returned to the observe_node context even though the kernel is about to route to END. If the HARD STOP is triggered by content-based safety concerns, this is a privacy gap. The content remains in `recalled_memories` state for the cycle, and `reflect_node` at line 597 logs count metadata. No raw content leaks to logs per SAF-CONS-01, but the state carries it.

#### FINDING-P20B [LOW] -- cognition.py memory loop is a true placeholder, not wired

- **Location:** `src/life_kernel/cognition.py:339-351`
- **Evidence:** The `memory()` loop method writes a hardcoded placeholder observation: `"Memory pattern scan placeholder -- waiting for P18 memory recall integration."`. This is NOT a real P3 call. The docstring says "Real P18 memory recall integration is planned for a later milestone."
- **Impact:** No functional gap -- the real memory path is through `observe_node` -> `p18_adapter`, not through `cognition.py`. This is correctly documented.

---

### P21 (Voice Interface) -- VERIFIED IMPLEMENTED

**What was claimed:** P21 uses `store_episode()` with `episode_type='voice_turn'`, DNR for safe-word content, classification for Critical content. All P3 columns supported.

**What was verified in code:**

| Surface | File:Line | Status |
|---|---|---|
| `store_episode()` accepts `episode_type` | `write_pipeline.py:119` | YES -- `episode_type: str = "conversation"` |
| `store_episode()` accepts `classification` | `write_pipeline.py:116` | YES -- `classification: str = RESTRICTED` |
| `store_episode()` accepts `summary` | `write_pipeline.py:120` | YES (required for Critical) |
| Episodes has `do_not_recall` column | `models.py:139-141` | YES |
| Episodes has `classification` column | `models.py:57-58` | YES (via `ClassificationMetaMixin`) |
| Episodes has `source` for origin label | `models.py:57-64` | YES |
| `surveillance.events.raw_payload` available | `models.py` surveillance schema | YES -- separate schema, not P3 |
| DNR API available for consent revocation | `dnr.py:179-257` | YES -- `mark_memory_dnr()` |

- **No new findings.** P21's planned P3 usage is fully supported. All P3 columns that P21 needs exist in the ORM and write pipeline. The `_guard_critical` check at `write_pipeline.py:285-295` ensures Critical voice transcripts (safe-word/intimate content) require a sanitized summary.

---

### P22 (Raw Access Hub) -- IMPLEMENTED WITH BUGS

**What was claimed:** P22 uses `store_episode()` / `store_episode_batch()` for external data ingest, `recall_memories()` for retrieval, DNR for content suppression. AuthLevel-only bypass risk noted.

**What was verified in code:**

| Surface | File:Line | Status |
|---|---|---|
| `store_episode()` accessible to caller | `write_pipeline.py:111-237` | YES -- no caller identity check |
| `store_episode_batch()` accessible | `write_pipeline.py:245-277` | YES -- no caller identity check |
| Classification guards exist | `write_pipeline.py:285-295` | YES -- but only Critical, no caller gate |
| `recall_memories()` accessible | `read_pipeline.py:789-802` | YES -- no caller identity check |
| DNR API available | `dnr.py:179-257` | YES |

#### FINDING-P22A [CRITICAL] -- store_episode_batch loses project_id

- **Same as FINDING-P19A.** `store_episode_batch()` at `write_pipeline.py:260-275` does NOT forward `project_id` or `project_scope` to `store_episode()`. If P22 uses batch import for external data (a planned use case), those episodes are silently created as global-scope entities.
- **Impact:** External data batch-imported by P22 would have `project_id=NULL` with `project_scope='project'` (defaults from ORM), making them invisible to project-scoped `recall_memories(project_id=<uuid>)` calls but visible when `project_id=None` (global recall). The mismatch between batch import and project isolation is a P19/P22 integration blocker.

#### FINDING-P22B [MEDIUM] -- No caller identity gate on store_episode

- **Location:** `src/memory/write_pipeline.py:111-237`
- **Evidence:** The write pipeline has classification-level guards (Critical requires sanitized summary) but no caller-identity gate. Any subsystem with a DB session can call `store_episode()` directly, bypassing HermesMemoryBridge's MEM-001..008 injection gates.
- **Impact:** If P22 routes untrusted external data directly to `store_episode()` instead of through an injection-gated facade, external content enters memory without sanitization, quarantine, or safety vetting. P22 architecture must mandate HermesMemoryBridge routing for untrusted data.
- **Note:** This is an architectural responsibility of P22, not a P3 bug. P3 write pipeline is intentionally generic.

---

### P23 (Embodied Operations) -- VERIFIED IMPLEMENTED

**What was claimed:** P23 uses `recall_memories()` via `p18_adapter` for action context, DNR for action evidence suppression. Action outcomes go to `PostgresAuditJournal`, not P3 episodes.

**What was verified in code:**

| Surface | File:Line | Status |
|---|---|---|
| `p18_adapter.recall()` exists for context | `p18_adapter.py:48-115` | YES -- wraps `recall_memories` |
| Action audit path is journal, not P3 | Research confirms | YES -- `PostgresAuditJournal` independent table |
| DNR `mark_memory_dnr()` can suppress action evidence | `dnr.py:179-257` | YES |
| `build_safe_content()` in recall can block action Critical content | `read_pipeline.py:419-475` | YES |

- **No new findings.** The same HARD STOP safe_mode gap as FINDING-P20A applies to P23 action context (since action context comes from `p18_adapter` which does not propagate `safe_mode`). No additional gap beyond P20's.

---

### P24 (Hermes Fork Convergence) -- VERIFIED IMPLEMENTED (current adapter)

**What was claimed:** P3 recall/store/embedding/DNR must become native Hermes `MemoryProvider` in the fork. All 5 RRF signals must be preserved.

**What was verified in code:**

| Surface | File:Line | Status |
|---|---|---|
| Current `HermesMemoryBridge.recall_for_context()` | `_memory_bridge.py:94-221` | YES -- wraps `recall_memories` with full params |
| Current `HermesMemoryBridge.store_conversation()` | `_memory_bridge.py:225-328` | YES -- wraps `store_episode` with full params |
| 5 RRF signals in recall_memories | `read_pipeline.py:789-1151` | YES -- vector + FTS + recency + KG(4th) + FSRS(5th) |
| DNR exclusion in recall | `read_pipeline.py:562,599,633` | YES -- per-query WHERE clause |
| Classification ceiling | `read_pipeline.py:164-174` | YES |
| Safe-mode content substitution | `read_pipeline.py:419-475` | YES |
| Token budget enforcement | `read_pipeline.py:493-523` | YES |
| Project_id namespace filtering | `read_pipeline.py:536-641` | YES |

- **No new findings.** The adapter pattern works. A Hermes fork must preserve all 5 signals plus DNR/classification/safe-mode/budget/project filtering. The `HermesMemoryBridge` at `_memory_bridge.py` is the canonical integration point.

---

### P16 (Knowledge Graph) -- IMPLEMENTED WITH BUGS

**What was claimed:** P16 adds 4th RRF signal inside P3 recall + KG ingestion hook in consolidation. SemanticFacts and KnowledgeGraph lack project_id.

**What was verified in code:**

| Surface | File:Line | Status |
|---|---|---|
| KG 4th RRF signal in recall_memories | `read_pipeline.py:947-987` | **VERIFIED** -- `KG_WEIGHT=0.20` weighted RRF contribution |
| KG ingestion hook in consolidation | `consolidation.py:456-489` | **VERIFIED** -- lazy-imports `KGIngestionPipeline`, post-hoop |
| SemanticFacts has project_id column | `models.py:208-263` | **NO** -- no project_id/scope |
| KnowledgeGraph has project_id column | `models.py:391-405` | **NO** -- no project_id/scope |

#### FINDING-P16A [HIGH] -- KG facts leak across projects due to missing project_id

- **Location:** `src/memory/models.py:208-263` (SemanticFacts), `src/memory/models.py:391-405` (KnowledgeGraph)
- **Evidence:** Both ORM classes lack `project_id` and `project_scope` columns. The consolidation pipeline at `consolidation.py:387-397` creates `SemanticFacts()` without a project_id. The KG ingestion hook receives facts_created (which carry no project_id) and ingests them into KnowledgeGraph entities -- also without project_id.
- **Impact:** When P19 project isolation is active, consolidated facts and KG entities are global. Two projects with the same memory base would share KG recall results. The P16 4th RRF signal in `read_pipeline.py` runs inside `recall_memories()` which DOES have `project_id` filtering for episodes -- but the KG rank map at lines 972-975 derives ranks from `_graph_scores` which come from KGQueryEngine, and if KG entities have no project_id, the KGQueryEngine cannot scope them. This means KG recall results leak across projects, contaminating the 4th RRF signal.
- **Note:** Already documented in the dependency matrix. Confirmed by code inspection.

---

### P18 (Advanced Memory) -- VERIFIED IMPLEMENTED

**What was claimed:** P18 adds FSRS-6 columns, 5th RRF signal, reconsolidation-on-retrieval, decay sweep. All are additive, not superseding.

**What was verified in code:**

| Surface | File:Line | Status |
|---|---|---|
| FSRS columns on Episodes ORM | `models.py:153-177` | **VERIFIED** -- tier, fsrs_state, last_reviewed_at, next_review_at, retrievability, stability, difficulty |
| 5th RRF signal FSRS_WEIGHT=0.15 | `read_pipeline.py:136-142` | **VERIFIED** |
| FSRS reconsolidation-on-retrieval | `read_pipeline.py:1025-1076` | **VERIFIED** -- GRADE_GOOD update + retrievability bonus |
| Decay sweep in consolidation | `consolidation.py:56-75, 928-1079` | **VERIFIED** -- `register_decay_job()` at line 1087-1126 |
| TierManager exists but not integrated | `tiers.py:6-41` | **VERIFIED** -- `should_promote()` exists, not called from any pipeline |

- **No new findings.** P18 is fully additive. All FSRS features are correctly integrated into the read pipeline. The TierManager is a scaffold awaiting integration (pre-existing finding). The decay sweep and FSRS reconsolidation are wired via `consolidation.py`.

---

## Dependency Graph (verified against code)

```
P3 Memory Foundation
├── P4 Persona          (INDEPENDENT -- reads persona_* tables directly via FSM)
├── P5 Agent Loop       (WIRED -- HermesMemoryBridge -> recall_memories/store_episode)
├── P16 Knowledge Graph (WIRED -- 4th RRF signal inside recall_memories + KG ingest
│                         hook in consolidation; GAP: KG/SemanticFacts lack project_id)
├── P18 Advanced Memory (WIRED -- 5th RRF signal + FSRS reconsolidation; TierManager scaffold)
├── P19 Namespace       (PARTIAL -- Episodes + pipelines WIRED; store_episode_batch + 
│                         consolidation NOT wired; SemanticFacts/KG lack columns)
│   └── Affects: P20, P21, P22, P23, P24 (inherit P19 contract)
├── P20 Life Kernel     (WIRED via p18_adapter + p16_adapter -> observe_node;
│                         GAP: safe_mode never passed to memory recall)
├── P21 Voice           (FULLY SUPPORTED -- all P3 columns available)
├── P22 Raw Access      (SUPPORTED with gaps: store_episode_batch loses project_id;
│                         no caller-identity gate on store_episode)
├── P23 Embodied Ops    (SUPPORTED -- uses p18_adapter for context; journal for audit;
│                         inherits P20 safe_mode gap)
└── P24 Hermes Fork     (SUPPORTED -- adapter pattern works; fork must preserve
                          all 5 signals + DNR + classification + budget + project filter)
```

---

## Severe Findings Summary

### FINDING-01 [CRITICAL] -- store_episode_batch does NOT forward project_id/project_scope

- **Location:** `src/memory/write_pipeline.py:260-275`
- **Status:** NOT MITIGATED. The `store_episode_batch` function passes every parameter individually but omits `project_id` and `project_scope`.
- **Impact:** P22 batch-imported data loses namespace isolation entirely. P19 project filtering is silently disabled for batch writes.
- **Affected phases:** P19 (primary), P22 (batch import)

### FINDING-02 [CRITICAL] -- SemanticFacts and KnowledgeGraph ORM lack project_id

- **Location:** `src/memory/models.py:208-263` (SemanticFacts), `391-405` (KnowledgeGraph)
- **Status:** NOT MITIGATED. P19-004 must add these columns.
- **Impact:** Consolidated facts and KG entities have no project isolation. KG recall (P16 4th RRF signal) leaks across projects.
- **Affected phases:** P19, P16, P20, P22, P23, P24

### FINDING-03 [HIGH] -- Consolidate_episodes_to_facts has no project_id awareness

- **Location:** `src/memory/consolidation.py:275-282` (function signature), `387-397` (SemanticFacts constructor)
- **Status:** NOT MITIGATED. The consolidation function neither accepts nor forwards project_id. This is a superset of FINDING-02 -- even if SemanticFacts ORM had project_id column, the consolidation pipeline would not populate it.
- **Impact:** All consolidated facts are global-scope. Two projects consolidating from their respective episodes (which DO have project_id) produce facts without any namespace tag. Those facts leak across projects via KG recall.
- **Affected phases:** P19, P16

### FINDING-04 [HIGH] -- safe_mode never reaches memory recall during HARD STOP in life-kernel graph

- **Location:** `src/life_kernel/graph.py:247` (recall_context), `src/life_kernel/p18_adapter.py:92-97` (adapter call)
- **Status:** NOT MITIGATED. The observe_node builds a recall_context with only query/content. The p18_adapter does not accept or forward safe_mode. HARD STOP detection happens in decide_node (line 373), AFTER observe_node already recalled full content.
- **Impact:** During HARD STOP, full-content memory is recalled into state without safe-mode substitution. If the HARD STOP was triggered by content-based safety concerns, this is a privacy gap.
- **Affected phases:** P20 (primary), P23 (inherits same gap)

### FINDING-05 [MEDIUM] -- No caller-identity gate on store_episode

- **Location:** `src/memory/write_pipeline.py:111-237`
- **Status:** Architectural responsibility of P22, not a P3 defect.
- **Impact:** Any subsystem with a DB session can inject episodes, bypassing MEM-001..008 injection gates.
- **Affected phases:** P22

### FINDING-06 [MEDIUM] -- P19 research based on stale snapshot

- **Location:** `docs/setup-evidence/P19/research/p19-memory-namespace-research.md` (SS2.2)
- **Status:** Documentation gap. Episodes ORM already has project_id/scope; research claimed "None" for all tables.
- **Affected phases:** P19 (planning only)

---

## Recommendations (NO FIXES -- for mama consideration)

1. **P19-004 must add project_id to SemanticFacts AND KnowledgeGraph ORM** before claiming memory isolation. Both columns are absent. Consolidation pipeline must also be updated to forward project_id from source episodes to created facts.

2. **store_episode_batch must forward project_id and project_scope** to store_episode. The batch function currently omits these kwargs. Fix before P22 uses batch import.

3. **consolidate_episodes_to_facts must accept and forward project_id** from source episodes to created SemanticFacts. The consolidation function has zero project awareness despite processing project-tagged episodes.

4. **P20 observe_node should pass safe_mode=True to memory adapters when HARD STOP is active.** The `p18_adapter.MemoryRecallAdapter.recall()` needs a new code path that passes `safe_mode=True` when the context contains a HARD STOP signal. Alternatively, add a `safe_mode` entry to `recall_context` dict in `graph.py:observe_node` and have `p18_adapter.recall()` inspect it.

5. **P22 architecture must mandate HermesMemoryBridge routing** for external untrusted data ingest, not direct `store_episode()` / `store_episode_batch()` calls. The P3 write pipeline is intentionally generic and has no caller-identity gate.

6. **P24 fork plan must preserve all 5 RRF signals** (vector, FTS, recency, KG, FSRS) plus DNR exclusion, classification ceiling resolution, safe-mode content substitution, token budget enforcement, and project_id namespace filtering.

---

## File Inventory

All files read during this audit:
- `src/memory/read_pipeline.py` (1198 lines, full read)
- `src/memory/write_pipeline.py` (369 lines, full read)
- `src/memory/models.py` (lines 1-270, 370-410 for ORM classes)
- `src/memory/consolidation.py` (lines 1-60, 275-500 for consolidation function)
- `src/memory/dnr.py` (lines 1-50 for authorization surface)
- `src/life_kernel/graph.py` (lines 1-334, 337-415, 513-642, 650-770, 790-940)
- `src/life_kernel/p18_adapter.py` (116 lines, full read)
- `src/life_kernel/p16_adapter.py` (124 lines, full read)
- `src/life_kernel/cognition.py` (lines 1-100, 320-420)
- `src/hermes/_memory_bridge.py` (362 lines, full read)
- `src/core/services/prompt_loader.py` (via grep for safe_mode/hard_stop)
- `docs/setup-evidence/legacy-audit/P3/P3-DOWNSTREAM-DEPENDENCY-MATRIX.md` (input research)
- `docs/setup-evidence/legacy-audit/P3/P3-SOURCE-MAP.md` (cross-reference)

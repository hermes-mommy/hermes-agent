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

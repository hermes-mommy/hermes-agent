# Phase 3 Memory Bridge Migration — Planner Gate

**Date**: 2026-06-04  
**Author**: Guinevere (Parent Planner)  
**Status**: DRAFT — Pending Auditor Review  
**ADR Reference**: ADR-035-hermes-migration.md  
**Parent Plan**: batch-plan-migration.md (Phase 3 section, lines 997-1126)  
**Duration Estimate**: 4-5 days  
**Risk Level**: MEDIUM  

---

## 1. Master Todo (Atomic Steps)

| Step ID | Title | Depends On | Parallelism | Duration |
|---|---|---|---|---|
| **P3-001** | Refactor memory_bridge to memory_plugin (Hermes MemoryProvider ABC) | — | parallel | 1 day |
| **P3-002** | Verify and activate compression at 70% threshold | P3-001 | sequential | 0.5 day |
| **P3-003** | Enable Hermes session_search FTS5 with safety gates | P3-001 | sequential | 0.5 day |
| **P3-004** | Configure PostgreSQL mirror sync (streaming replication + RBAC) | — | parallel | 1 day |
| **P3-005** | Build A/B testing infrastructure (golden dataset + harness + scipy) | — | parallel | 1 day |
| **P3-006** | Execute A/B test: 100 queries, recall quality gate | P3-002, P3-003, P3-005 | sequential | 0.5 day |
| **P3-007** | Verify zero PG writes from Hermes (read-only enforcement) | P3-001, P3-004 | sequential | 0.5 day |
| **P3-008** | Final integration verification and safety audit | ALL above | sequential | 0.5 day |
| **P3-009** | Configure Hermes mirror sync (MEMORY.md/USER.md) | P3-001 | parallel (Wave 2) | 0.5 day |

---

## 2. Dependency Map

```
P3-001 (Refactor) ---+---> P3-002 (Compression)  --+
                     |                              +--> P3-006 (A/B Test) --> P3-008 (Final)
                     +--> P3-003 (FTS5+Safety)    --+
                     +--> P3-009 (Mirror Sync)
P3-004 (Mirror)  --------------------------------------> P3-007 (Zero PG Writes) --> P3-008
P3-005 (A/B Infra) --------------------------------------> P3-006 (A/B Test)
```

**Parallel Execution Waves:**

| Wave | Steps | Rationale |
|---|---|---|
| **Wave 1** (parallel) | P3-001, P3-004, P3-005 | Independent: code refactor, DB infrastructure, test tooling. No shared files. |
| **Wave 2** (parallel) | P3-002, P3-003, P3-009 | Depend on P3-001 (new plugin interface). Can run in parallel with each other. No shared files. |
| **Wave 3** (sequential) | P3-006, P3-007 | Depend on Wave 2 + P3-005. Must run after all enabling steps complete. |
| **Wave 4** (sequential) | P3-008 | Final integration gate. All prior steps must PASS. |

---

## 3. Research Inputs

| Report ID | Title | Path | Key Findings |
|---|---|---|---|
| R-01 | Hermes Memory Plugin Architecture | `research-reports/phase-3-planning/01-hermes-memory-plugin-research.md` | MemoryProvider ABC requires: name, is_available(), initialize(), get_tool_schemas(), handle_tool_call(), get_config_schema(), save_config(). Lifecycle hooks: prefetch(), sync_turn() (MUST be non-blocking daemon thread), on_pre_compress(), on_session_end(). Single external provider limit. Plugin dir: plugins/memory/guinevere-memory/. |
| R-02 | PostgreSQL Mirror Configuration | `research-reports/phase-3-planning/02-postgres-mirror-config-research.md` | Streaming Replication (Hot Standby) recommended. RBAC: hermes_memory_bridge role with SELECT-only + ALTER DEFAULT PRIVILEGES. RLS with FORCE + SET LOCAL for PgBouncer. pgvector >= v0.5.2 required. Monitor via postgres_exporter. |
| R-03 | FTS5 Gap Analysis | `research-reports/phase-3-planning/03-fts-gap-analysis.md` | NO SQLite FTS5 in Python code. session_search is Hermes-native (FTS5 on ~/.hermes/state.db). Post-recall DNR gate required. Classification ceiling enforcement missing for Hermes path. memory_plugin.py does not exist yet. |
| R-04 | Memory Safety Compliance | `research-reports/phase-3-planning/04-memory-safety-compliance.md` | 10 safety categories verified. DNR: query-level + post-query verify. Classification: fail-closed. Anti-hallucination guard present. Y6 impossible. Phase 3 risk: new ingestion paths must pass principal=guinevere_core, classification=RESTRICTED, exclude_dnr=True. |
| R-05 | Embedding Alternatives | `research-reports/phase-3-planning/05-embedding-alternatives-research.md` | 9Router DOES support embeddings. HTTP 400 is config issue. Schema locked to vector(1536). Recommended: fix 9Router config (Option A), fallback chain to Direct OpenAI then Local bge-large with dimension projection then FTS-only degradation. |
| R-06 | Compression Algorithm | `research-reports/phase-3-planning/06-compression-algorithm-research.md` | NO application-level compression in codebase. Hermes config ALREADY set to threshold: 0.7, target: 0.2, protect_last: 20. Gap: extract_key_facts() stub returns []. No LLM-based semantic summarization engine exists. |
| R-07 | Recall Quality Metrics | `research-reports/phase-3-planning/07-recall-quality-metrics.md` | Robust RRF ranking in read_pipeline.py. Spec exists (34-MemoryRecallEvaluationSpec). ZERO A/B testing infrastructure. No scipy/numpy. No golden dataset. scripts/ab_test_recall.py is TODO. Gaps: G-01 through G-06. |
| R-08 | SQLite FTS5 Setup Guide | `research-reports/phase-3-planning/08-sqlite-fts5-setup-research.md` | Built-in Python 3.10+. Tokenizer: porter unicode61. External content tables + triggers for sync. BM25 ranking. Sub-ms queries. sqlite-utils recommended library. |

---

## 4. Known State (Codebase Analysis)

### 4.1 Current Memory Architecture (Phase 2 State)

| Component | File | Status |
|---|---|---|
| Memory Bridge | src/hermes/memory_bridge.py (295 lines) | Phase 2 bridge. recall_for_context() + store_conversation(). Always passes embedding_service=None. |
| Session Adapter | src/hermes/session_adapter.py (366 lines) | skip_memory=True. ALL Hermes memory disabled. Redis DB4 sessions. |
| Read Pipeline | src/memory/read_pipeline.py (963 lines) | Full hybrid ranking (vector+FTS+recency+importance, RRF k=60). DNR, classification ceiling, safe-mode, 4000-token budget. Vector search NEVER fires. |
| Write Pipeline | src/memory/write_pipeline.py (359 lines) | store_episode with Critical fail-closed, Restricted default classification. |
| Embeddings | src/memory/embeddings.py (775 lines) | 9Router-native. FAILS because 9Router returns HTTP 400. 6 retries = 61s wasted. |
| DNR | src/memory/dnr.py (418 lines) | Principal-restricted (guinevere_core), audit trail, post-query verify. |
| Consolidation | src/memory/consolidation.py (757 lines) | Daily episodic to semantic at 03:00 ICT, DNR-safe, safe-word aware. |
| Conversational Handler | src/discord/conversational_handler.py (631 lines) | Bridge at Step 9 (recall) + Step 12b (store, fire-and-forget). Mood HARDCODED to Content. |
| Prompt Loader | src/core/services/prompt_loader.py (186 lines) | [RECENT MEMORIES] format with token budget enforcement. |

### 4.2 Critical Gaps (from 07-MEMORY-BRIDGE-GAP.md)

| Gap | Severity | Description | Phase 3 Step |
|---|---|---|---|
| G-B1 | CRITICAL | Embeddings always fail (9Router HTTP 400) | Pre-requisite (fix 9Router config) |
| G-B2 | HIGH | 61s retry waste on embedding failure | Pre-requisite (circuit breaker) |
| G-B3 | HIGH | Auto-store fails silently | P3-001 (sync_turn daemon thread) |
| G-B6 | MEDIUM | Mood hardcoded to Content | P3-001 (plugin lifecycle hook) |
| G-B7 | MEDIUM | hard_stop_handler not wired | P3-001 (safety delegation) |
| G-B9 | MEDIUM | Classification hardcoded Restricted | P3-001 (dynamic classification) |
| G-B10 | LOW | Summary naive truncation | P3-002 (compression engine) |

### 4.3 VPS State

| Check | Result |
|---|---|
| PostgreSQL connection | UNKNOWN. SSH timed out from Windows (port 37528). Must verify on VPS directly. |
| Redis connection | UNKNOWN. Same SSH issue. |
| SQLite files | UNKNOWN. Same SSH issue. |
| **Action Required** | Verify VPS state via direct SSH before execution. Document pre-flight checklist. |

---

## 5. Binding Decisions

| Decision | Rationale | Alternative Rejected |
|---|---|---|
| Use Hermes MemoryProvider ABC for plugin interface | Official API from NousResearch/hermes-agent. Enforces single-provider rule. | Custom wrapper (rejected: no lifecycle hooks, no config wizard integration) |
| Streaming Replication for PostgreSQL mirror | Real-time, sub-ms lag, Hot Standby. pgvector compatible. | Logical Replication (rejected: higher overhead, pgvector bug history), FDW (rejected: high per-query latency) |
| Hermes-native session_search for FTS5 | Built-in capability, no custom Python FTS5 engine needed. | Custom SQLite FTS5 in Python (rejected: duplicative, ADR-007 forbids SQLite as canonical store) |
| Fix 9Router config for embeddings (Option A) | Schema locked to vector(1536). Cost $0.02/1M tokens. No code changes needed. | Local SentenceTransformers (rejected: requires schema migration or dimension projection) |
| Post-recall DNR gate for Hermes FTS5 path | Hermes FTS5 has no knowledge of do_not_recall column. | Pre-filter (impossible: Hermes FTS5 does not expose SQL WHERE clauses) |
| Rely on Hermes-native compression at 70% | Config already set. Hermes has built-in compressor with on_pre_compress hook. | Custom Python compression engine (rejected: duplicative, Hermes already handles it) |
| scipy for A/B statistical testing | Industry standard for paired t-test / McNemar test. | Manual p-value calculation (rejected: error-prone, no confidence intervals) |
| sqlite-utils for FTS5 management | Clean Python API, auto-generates triggers. | Raw sqlite3 (rejected: manual trigger SQL, higher maintenance) |

---

## 6. Collision Scan

| Collision Type | Affected Steps | Mitigation |
|---|---|---|
| memory_bridge.py | P3-001 modifies, P3-002/P3-003 reference | P3-001 owns the file. P3-002/P3-003 depend on P3-001 completion. |
| hermes-config/config.yaml | P3-002 verifies, P3-003 modifies session_search | P3-002 is read-only verify. P3-003 adds session_search block. No write conflict. |
| conversational_handler.py | P3-001 refactors bridge calls | Single owner (P3-001). No concurrent edits. |
| read_pipeline.py | P3-005 references for A/B test | P3-005 is READ-ONLY consumer. No modification to pipeline. |
| docs/README.md, ADR-Index | Parent-only shared docs | Parent handles doc updates after all steps complete. |
| PostgreSQL schema | P3-004 adds RBAC role, P3-007 verifies | P3-004 owns schema changes. P3-007 is verification only. |
| requirements.txt / pyproject.toml | P3-005 adds scipy | Single owner (P3-005). No conflict. |
| plugins/memory/guinevere-memory/\_\_init\_\_.py | P3-001 creates, P3-002 tests (read), P3-003 adds safety gate imports | P3-001 creates. P3-003 writes safety gate code to **separate module** (`safety_gates.py`). P3-002 tests `__init__.py` (read-only verify of hook registration). `__init__.py` only imports from `safety_gates.py` — no inline safety gate code. No collision. |
| plugins/memory/guinevere-memory/safety_gates.py | P3-003 creates | P3-003 sole owner. Independent from P3-002's verification of `__init__.py`. |

**Result**: No write conflicts. Sequential dependencies properly enforce single ownership. P3-003 safety gate code lives in separate module to avoid read-after-write hazard with P3-002.

---

## 7. Files to Create/Modify

### 7.1 Files to CREATE

| File | Step | Description |
|---|---|---|
| plugins/memory/guinevere-memory/\_\_init\_\_.py | P3-001 | MemoryProvider implementation with prefetch, sync_turn, on_pre_compress hooks |
| plugins/memory/guinevere-memory/plugin.yaml | P3-001 | Plugin metadata, dependencies, hook list |
| plugins/memory/guinevere-memory/README.md | P3-001 | Setup instructions, config reference |
| scripts/ab_test_recall.py | P3-005 | A/B testing harness: 100 queries, dual pipeline, scipy p-value |
| evidence/memory-eval/dataset/golden-dataset-v1.0.json | P3-005 | 100+ queries with ground truth relevance (0-3 scale) |
| tests/memory/test_ab_recall.py | P3-005 | Unit tests for A/B harness correctness |
| plugins/memory/guinevere-memory/safety_gates.py | P3-003 | Post-recall DNR gate, classification ceiling filter, anti-hallucination guard, safe-mode substitution, consent gate — separate module to avoid Wave 2 collision |
| docs/setup-evidence/phase-3/verification-P3-NNN.md | Each step | Per-step verification evidence |
| docs/setup-evidence/phase-3/auditor-gate-P3-NNN.md | Each step | Per-step auditor report |

### 7.2 Files to MODIFY

| File | Step | Changes |
|---|---|---|
| src/hermes/memory_bridge.py | P3-001 | Deprecate; redirect to new plugin. Add deprecation warning. |
| src/discord/conversational_handler.py | P3-001 | Update bridge import path to use new plugin interface. |
| plugins/memory/guinevere-memory/\_\_init\_\_.py | P3-003 | Add `from .safety_gates import ...` import + wire safety gate calls in prefetch/sync_turn. P3-001 creates this file; P3-003 only adds import + wiring. |
| hermes-config/config.yaml | P3-003 | Add session_search configuration block (FTS5 backend). |
| requirements.txt or pyproject.toml | P3-005 | Add scipy >= 1.12 dependency. |
| docs/README.md | P3-008 | Update Phase 3 completion status. |
| plugins/memory/guinevere-memory/\_\_init\_\_.py | P3-009 | Add `extract_key_facts()` implementation for mirror sync. P3-001 creates this file; P3-009 adds extraction logic. |
| hermes-config/config.yaml | P3-009 | Add `mirrors` configuration block (enabled, sync_interval_messages, paths). |
| docs/10-governance/17-ADR_Index_v1.0.md | P3-008 | Add Phase 3 completion reference. |

### 7.3 Files to NOT MODIFY (Read-Only References)

| File | Steps That Reference |
|---|---|
| src/memory/read_pipeline.py | P3-005, P3-006 |
| src/memory/write_pipeline.py | P3-001, P3-002 |
| src/memory/dnr.py | P3-003, P3-006 |
| src/memory/embeddings.py | P3-001, P3-006 |
| src/persona/safe_mode.py | P3-008 |
| src/core/services/hard_stop_handler.py | P3-001 |

---

## 8. Implementation Design (Per-Step)

### P3-001: Refactor memory_bridge to memory_plugin

**Objective**: Transform the current HermesMemoryBridge facade into a proper Hermes MemoryProvider plugin following the ABC from NousResearch/hermes-agent.

**Architecture**:

```
plugins/memory/guinevere-memory/
  __init__.py          # GuinevereMemoryProvider(MemoryProvider) + register()
  plugin.yaml          # Metadata, hooks, pip_dependencies
  README.md            # Setup docs, config reference
```

**Method Mapping**:

| Current Bridge Method | Plugin Method | Behavior |
|---|---|---|
| recall_for_context() | prefetch(query, session_id) | Delegate to read_pipeline.recall_memories() with principal=guinevere_core, exclude_dnr=True, safe_mode from state |
| store_conversation() | sync_turn(user, assistant, session_id) | Daemon thread wrapping write_pipeline.store_episode(). classification=RESTRICTED. Fire-and-forget. |
| N/A | on_pre_compress(messages) | Capture pre-compression state, extract key facts before Hermes discards them |
| N/A | on_session_end(messages) | Final flush of pending memory writes |
| N/A | system_prompt_block() | Inject Guinevere memory capabilities description |

**Threading Contract (CRITICAL)**:
- sync_turn() MUST be non-blocking. Wrap DB writes in daemon thread with join-before-new-thread guard.
- prefetch() can be synchronous (Hermes awaits it before API call).

**Config Schema**:

```python
def get_config_schema(self) -> list:
    return [
        {"key": "pg_dsn", "description": "PostgreSQL connection string",
         "secret": True, "env_var": "GUINEVERE_PG_DSN"},
        {"key": "embedding_model", "description": "Embedding model name",
         "default": "openai/text-embedding-3-small"},
        {"key": "recall_limit", "description": "Max memories per recall", "default": 10},
        {"key": "token_budget", "description": "Token budget for recall context", "default": 800},
    ]
```

**Safety Delegation**:
- All DNR, classification, safe-mode decisions delegated to read_pipeline/write_pipeline.
- Principal always guinevere_core (hardcoded in plugin, not configurable).
- Anti-hallucination guard injected when prefetch returns empty.

**Consent Gate (NEW — addressing Safety Audit Gap 1)**:
- `prefetch()` and `sync_turn()` MUST check consent state before delegating to pipelines.
- Implementation: Query consent state from Guinevere's consent store (Redis DB2 or config). If `consent_revoked=True` for memory operations, return empty results (prefetch) or skip storage (sync_turn) with structured log event.
- Consent gate is checked BEFORE pipeline delegation — not inside pipelines — because pipelines currently have no consent gate either (verified: zero matches for `consent_required` in read_pipeline.py and write_pipeline.py).
- The consent check follows the same fail-closed pattern: if consent state cannot be determined, block the operation and log an audit event.
- Safe-word events: When a safe-word is detected (by GuinevereSafetyPlugin), the plugin's sync_turn must NOT store that conversation turn. Safe-word detection is handled by the independent safety_plugin; the memory plugin checks a shared safe-word flag.
- P3-008 checklist item changed from "Consent gate unaffected" to "Consent gate implemented and verified."

---

### P3-002: Verify and Activate Compression at 70%

**Objective**: Confirm Hermes-native compression activates at 70% threshold and that the on_pre_compress hook correctly captures pre-compression state.

**Current State**: hermes-config/config.yaml already configured:

```yaml
memory:
  compression:
    enabled: true
    threshold: 0.7
    target: 0.2
    protect_last: 20
```

**Verification Steps**:
1. Confirm config values match ADR-035 spec (threshold=0.7, target=0.2, protect_last=20).
2. Verify plugin on_pre_compress(messages) hook is registered in plugin.yaml.
3. Test: Simulate conversation exceeding 70% token budget. Verify Hermes triggers compression.
4. Test: Verify last 20 messages remain uncompressed.
5. Test: Verify on_pre_compress extracts and persists key facts before compression discards them.
6. Verify Critical-classification conversations are handled correctly during compression.

**Gap Resolution**:
- G-B10 (naive summary truncation): Addressed by Hermes-native compression (LLM-based, not string truncation).
- extract_key_facts() stub: Implemented in plugin on_pre_compress hook to capture facts before Hermes compresses.

---

### P3-003: Enable Hermes session_search FTS5 with Safety Gates

**Objective**: Enable Hermes-native session_search backed by FTS5, with mandatory post-recall safety gates.

**Configuration Change (hermes-config/config.yaml)**:

```yaml
memory:
  session_search:
    enabled: true
    backend: "fts5"
    max_results: 20
    min_relevance: 0.3
```

**Safety Gates (MUST implement in `plugins/memory/guinevere-memory/safety_gates.py`)**:

> **Architecture decision**: Safety gates live in a SEPARATE module (`safety_gates.py`), not in `__init__.py`. This resolves the Wave 2 collision (Architecture Audit Finding 1): P3-002 tests `__init__.py` for hook registration while P3-003 writes safety gate code. `__init__.py` only adds a `from .safety_gates import apply_safety_gates` import.

1. **Post-Recall DNR Verification**: 
   - **Implementation approach (DNR ID Cache)**: On plugin `initialize()`, load all DNR-marked memory IDs from PostgreSQL (`SELECT id FROM memory.episodes WHERE do_not_recall = true`) into an in-memory `set[str]`. Refresh cache every 5 minutes via background daemon thread.
   - When session_search returns results, cross-reference each result's content hash/ID against the DNR cache. Any match → remove from results and log DNR exclusion event.
   - Rationale: Hermes FTS5 results from `~/.hermes/state.db` have no `do_not_recall` column. Direct `verify_recall_results_dnr_free()` call on raw FTS5 results would silently pass (no `do_not_recall` field = check passes). The cache approach bridges this gap.
   - Fallback: If DNR cache load fails, block ALL session_search results (fail-closed).

2. **Classification Ceiling Filtering**:
   - **Implementation approach (PG Enrichment)**: After session_search returns results, batch-query PostgreSQL for classification metadata: `SELECT id, classification FROM memory.episodes WHERE id IN (...)`. Enrich each FTS5 result with its classification level. Apply ceiling filter: `classification IN ('Public', 'Internal', 'Restricted')` for `guinevere_core` principal (maps to ceiling level 2 = Restricted). Uses IN-list because string comparison is lexicographically wrong for classification enum values (lexicographic order: Confidential < Critical < Internal < Public < Restricted, which does not match semantic hierarchy Public=0 < Internal=1 < Restricted=2 < Confidential=3 < Critical=4).
   - Rationale: Same gap as DNR — Hermes FTS5 has no classification field. PG enrichment is the authoritative source.
   - Performance: Batch query with IN clause, max 20 IDs per session_search call. Sub-ms for indexed lookups.
   - Fallback: If PG enrichment query fails, treat all results as Critical (fail-closed = return empty).

3. **Anti-Hallucination Guard**: Inject guard when session_search returns empty results (after DNR/classification filtering).

4. **Safe-Mode Content Substitution**: Replace raw content with safe-mode placeholders for Critical/Restricted results when `safe_mode=True`.

5. **Consent Gate**: Check consent state before applying any safety gates. If consent revoked, return empty results immediately (before DNR/classification processing).

**Architecture**:

```
User Query
  --> Consent Gate (check consent state — if revoked, return empty)
  --> Hermes session_search (FTS5 on ~/.hermes/state.db)
  --> Results[]
  --> DNR Cache Cross-Reference (remove DNR-marked IDs)
  --> PG Classification Enrichment (batch SELECT classification)
  --> Classification Ceiling Filter (guinevere_core ceiling)
  --> Safe-Mode Substitution (if safe_mode=True)
  --> Anti-Hallucination Guard (if empty after all filters)
  --> Inject into LLM Context
```

**Hard Rejection Criterion**: Zero DNR entries in session_search results after post-recall gate. Classification enrichment query MUST succeed (fail-closed on PG error).

---

### P3-004: Configure PostgreSQL Mirror Sync

**Objective**: Set up streaming replication with Hot Standby and RBAC for Hermes read-only access.

**Implementation Steps**:
1. Create hermes_memory_bridge role with SELECT-only on memory schema.
2. Apply ALTER DEFAULT PRIVILEGES for future table access.
3. **Explicit REVOKE INSERT/UPDATE/DELETE/TRUNCATE** for defense-in-depth (DBA Audit Finding 1).
4. Configure pg_hba.conf for Hermes connection (host-based auth, connection limit 50).
5. Set up streaming replication (primary to Hot Standby replica).
6. Configure hot_standby = on on replica.
7. Deploy postgres_exporter for replication lag monitoring.
8. Set Prometheus alert rules: warning at >30s lag, critical at >300s lag.
9. **Apply RLS policies** for classification ceiling and surveillance data isolation (DBA Audit Finding 2, Safety Audit Finding 4).
10. **Verify network isolation**: Replica accessible only via Tailscale/internal network. Zero public ports (Security Policy §1.3).

**Hermes as Principal (DBA Audit Finding — Hermes not in RBAC matrix)**:
- Hermes is defined as an **external framework principal** with classification ceiling `Restricted` by default.
- The `hermes_memory_bridge` role maps to this principal. Critical-classified data is NOT accessible through this role (RLS enforced).
- `~/.hermes/state.db` is documented as a governed data store in the classification scope.

**Pre-requisite (v1.3 FIX — Auditor Tech F4)**: Verify `memory_owner` role exists before running SQL migration. If it does not exist, create it or identify the actual role that owns `memory` schema tables. Run: `SELECT rolname FROM pg_roles WHERE rolname = 'memory_owner';` — if empty, determine the table owner via `SELECT tableowner FROM pg_tables WHERE schemaname = 'memory' LIMIT 1;` and substitute in the `ALTER DEFAULT PRIVILEGES` statement below.

**SQL Migration**:

```sql
-- Create read-only role
CREATE ROLE hermes_memory_bridge LOGIN PASSWORD '${HERMES_PG_PASSWORD}';
ALTER ROLE hermes_memory_bridge CONNECTION LIMIT 50;
GRANT USAGE ON SCHEMA memory TO hermes_memory_bridge;
GRANT SELECT ON ALL TABLES IN SCHEMA memory TO hermes_memory_bridge;
-- NOTE: Replace 'memory_owner' with actual table-owning role if different (see pre-requisite)
ALTER DEFAULT PRIVILEGES FOR ROLE memory_owner IN SCHEMA memory
  GRANT SELECT ON TABLES TO hermes_memory_bridge;

-- Explicit REVOKE for defense-in-depth (DBA Audit fix)
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA memory
  FROM hermes_memory_bridge;

-- Row-Level Security: Classification ceiling (DBA Audit fix)
-- v1.2 FIX (Auditor Safety S10, Tech T4): Table is memory.episodes (not episodic_memory).
-- Classification uses IN-list because string comparison is lexicographically wrong for this enum.
-- Lexicographic order: Confidential(C) < Critical(C) < Internal(I) < Public(P) < Restricted(R)
-- Semantic hierarchy: Public=0 < Internal=1 < Restricted=2 < Confidential=3 < Critical=4
ALTER TABLE memory.episodes FORCE ROW LEVEL SECURITY;
CREATE POLICY hermes_classification_ceiling ON memory.episodes
  FOR SELECT TO hermes_memory_bridge
  USING (classification IN ('Public', 'Internal', 'Restricted'));

-- Row-Level Security: Surveillance data isolation (Safety Audit fix)
-- Hermes cannot read episodes with source='surveillance'
CREATE POLICY hermes_surveillance_isolation ON memory.episodes
  FOR SELECT TO hermes_memory_bridge
  USING (source != 'surveillance');

-- Apply RLS to other memory tables
ALTER TABLE memory.faiz_profile FORCE ROW LEVEL SECURITY;
CREATE POLICY hermes_profile_ceiling ON memory.faiz_profile
  FOR SELECT TO hermes_memory_bridge
  USING (classification IN ('Public', 'Internal', 'Restricted'));

ALTER TABLE memory.emotional_events FORCE ROW LEVEL SECURITY;
CREATE POLICY hermes_emotional_ceiling ON memory.emotional_events
  FOR SELECT TO hermes_memory_bridge
  USING (classification IN ('Public', 'Internal', 'Restricted', 'Confidential'));

-- Streaming replication configuration
-- primary postgresql.conf:
--   wal_level = replica
--   max_wal_senders = 5
--   wal_keep_size = '1GB'
-- primary pg_hba.conf:
--   host replication replicator <replica_ip>/32 ssl_mode=verify-full
-- replica postgresql.conf:
--   hot_standby = on
--   primary_conninfo = 'host=<primary_ip> port=5432 user=replicator sslmode=verify-full'
```

**Network Isolation**:
- Streaming replication connection MUST use `ssl_mode=verify-full`.
- Replica accessible only via Tailscale or internal VPS network. Zero public ports.
- `pg_hba.conf` restricts connections to Tailscale IP range only.

**Rollback**: Drop RLS policies, drop role, remove replication config. Under 3 minutes.

---

### P3-005: Build A/B Testing Infrastructure

**Objective**: Create the golden dataset and A/B testing harness required by ADR-035 recall quality gate.

**Deliverables**:

1. evidence/memory-eval/dataset/golden-dataset-v1.0.json (100+ queries with):
   - query_text: Natural language query
   - memory_type: episodic, semantic, profile, financial, project, or client
   - ground_truth: List of {memory_id, relevance} (graded 0-3)
   - do_not_recall_ids: IDs that MUST NOT appear in results

2. scripts/ab_test_recall.py (approximately 200 lines). Harness that:
   - Loads golden dataset
   - Runs Baseline A (current pipeline) and Variant B (Hermes-augmented)
   - Computes Precision@10, Recall@10, MRR, NDCG@10 for both
   - Uses scipy.stats.ttest_rel (paired t-test, same queries through both pipelines) for p-value. v1.2 FIX (Auditor Tech T5): ttest_ind is wrong — queries are paired/matched samples, not independent.
   - Exit 1 if p < 0.05 OR any DNR violation
   - Outputs JSON report to evidence/memory-eval/ab-results-{timestamp}.json

3. tests/memory/test_ab_recall.py (Unit tests for harness correctness)

**Dependencies**: scipy >= 1.12 added to requirements.

**Pre-requisite**: Embedding API must be working (G-B1 resolved). If G-B1 is still broken, A/B test is INVALID and must be BLOCKED.

---

### P3-006: Execute A/B Test (100 Queries)

**Objective**: Run the A/B test and verify recall quality is not degraded (p > 0.05).

**Execution**:
1. Verify pre-requisites: P3-002 PASS, P3-003 PASS, P3-005 PASS, G-B1 resolved.
2. Run: python scripts/ab_test_recall.py --queries 100 --output evidence/memory-eval/
3. Verify exit code 0.
4. Read results: Precision@10, Recall@10, MRR, NDCG@10, p-value.
5. Verify: p-value > 0.05, zero DNR violations, zero hallucinations.

**Acceptance Criteria**:
- p-value > 0.05 for Precision@10 difference
- Zero DNR violations in Variant B
- Zero classification ceiling violations
- Recall@10 within 5% of Baseline A

---

### P3-007: Verify Zero PG Writes from Hermes

**Objective**: Confirm Hermes memory plugin makes zero write operations to PostgreSQL.

**Verification Methods**:
1. RBAC Enforcement: hermes_memory_bridge role has SELECT-only. Any write attempt raises permission denied.
2. Connection Monitoring: Query pg_stat_activity for Hermes connections. Verify zero write queries.
3. Audit Logging: Enable log_statement = 'mod' for hermes_memory_bridge role. Verify zero DML logged.
4. Plugin Code Review: Verify plugin code has no INSERT, UPDATE, DELETE operations on PostgreSQL.
5. Integration Test: Run conversation flow. Verify Hermes reads from PG but writes only to its own SQLite state.db.

**SQL Verification**:

```sql
-- Verify role has no write privileges
SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'hermes_memory_bridge';
-- Expected: ALL rows have privilege_type = 'SELECT'

-- Check for any write activity from Hermes connections
SELECT pid, usename, query, state
FROM pg_stat_activity
WHERE usename = 'hermes_memory_bridge'
  AND query NOT ILIKE 'SELECT%';
-- Expected: 0 rows
```

---

### P3-008: Final Integration Verification and Safety Audit

**Objective**: End-to-end verification that Phase 3 migration is complete and safe.

**Checklist**:
- [ ] P3-001 through P3-007 and P3-009 all PASS
- [ ] Plugin registered and discoverable by Hermes MemoryManager
- [ ] Compression activates at 70% token usage
- [ ] session_search returns results with DNR gate enforced
- [ ] PostgreSQL mirror operational with less than 1s lag
- [ ] A/B test p-value > 0.05
- [ ] Zero PG writes from Hermes verified
- [ ] No type safety suppressions (as any, @ts-ignore, # type: ignore)
- [ ] No empty catch/except blocks around memory operations
- [ ] ANTI_HALLUCINATION_GUARD injected when memories empty
- [ ] DNR post-recall gate active for all Hermes recall paths
- [ ] Classification ceiling enforced for all Hermes recall paths
- [ ] Safe-mode content substitution working
- [ ] HARD STOP / distress protocol unaffected
- [ ] Yandere Y4 baseline/Y5 ceiling preserved
- [ ] Consent gate implemented in plugin prefetch/sync_turn and verified (not just "unaffected")
- [ ] Safe-word logging: safe-word detected turns logged to DNR audit trail, sync_turn skips storage for safe-word turns
- [ ] RLS policies active on all memory tables (classification ceiling + surveillance isolation)
- [ ] Connection strings not logged (grep verified zero matches)
- [ ] All evidence files created and referenced
- [ ] All auditor reports PASS
- [ ] Rollback procedure tested and documented
- [ ] Hermes mirror sync (MEMORY.md/USER.md) operational

### P3-009: Configure Hermes Mirror Sync (MEMORY.md/USER.md)

**Objective**: Enable Hermes to write MEMORY.md and USER.md mirror files that reflect key facts extracted from conversations, providing human-readable memory summaries alongside the PostgreSQL canonical store.

**Canonical Reference**: phase-3-memory.md Step 3.4 (lines 200-250).

**Source Documents**:
- phase-3-memory.md Step 3.4: Hermes mirror sync configuration
- ADR-035 Appendix A: Memory configuration parameters
- research-reports/phase-3-planning/06-compression-algorithm-research.md: Key fact extraction stub status

**Implementation Design**:

1. **Configuration in hermes-config/config.yaml**:
   ```yaml
   memory:
     mirrors:
       enabled: true
       sync_interval_messages: 5
       paths:
         user: "~/.hermes/mirrors/USER.md"
         memory: "~/.hermes/mirrors/MEMORY.md"
   ```

2. **Key Fact Extraction**:
   - `memory_bridge.py` `extract_key_facts()` is currently a Phase 3 stub (returns `[]`). v1.3 FIX (Auditor Tech F2): Since P3-001 deprecates `memory_bridge.py`, the `extract_key_facts()` implementation lives in the plugin module (`plugins/memory/guinevere-memory/__init__.py`), not the deprecated bridge.
   - Implementation: Extract key facts from conversation turns using LLM summarization or rule-based extraction.
   - Output format: Markdown bullet points suitable for MEMORY.md/USER.md append.
   - Fallback: If extraction fails, skip mirror update (non-blocking). Never block conversation flow.

3. **Mirror File Format**:
   - MEMORY.md: Chronological key facts from conversations (date-stamped sections)
   - USER.md: User preferences, preferences changes, and profile observations
   - Both files are read-only for Hermes (Hermes reads them for context enrichment)
   - Python write authority: `src/memory/write_pipeline.py` remains the PG write path

4. **Safety Gates**:
   - Mirror content must pass classification filter (no Critical/Confidential content in mirrors)
   - DNR-marked memories must not appear in mirror files
   - Mirror files stored in `~/.hermes/mirrors/` (Hermes-managed directory)
   - No PII/intimate data in mirrors (PII redaction gate from write_pipeline applies)

5. **Sync Mechanism**:
   - Triggered every `sync_interval_messages` (default: 5) conversation turns
   - Non-blocking: runs in daemon thread, never blocks conversation response
   - Idempotent: same facts not duplicated (dedup via content hash)

**Acceptance Criteria**:
- [ ] `memory.mirrors.enabled: true` in hermes-config/config.yaml
- [ ] `sync_interval_messages: 5` configured
- [ ] Mirror paths set to `~/.hermes/mirrors/USER.md` and `~/.hermes/mirrors/MEMORY.md`
- [ ] `extract_key_facts()` produces non-empty output for test conversations
- [ ] Mirror files created and updated after sync interval
- [ ] No Critical/Confidential content in mirror files (verified by classification filter)
- [ ] No DNR-marked content in mirror files (verified by DNR gate)
- [ ] Mirror sync is non-blocking (conversation latency unchanged)
- [ ] Deduplication working (same fact not repeated)

**Rollback**: Set `memory.mirrors.enabled: false` in config.yaml and reload. Mirror files persist but are no longer updated.

---

## 9. Per-Step Verification Scaffold

### P3-001 Scaffold

| Field | Value |
|---|---|
| Expected Files | plugins/memory/guinevere-memory/\_\_init\_\_.py, plugin.yaml, README.md. Modified: src/hermes/memory_bridge.py (deprecation), src/discord/conversational_handler.py (import update) |
| Forbidden Patterns | `as any`, `@ts-ignore`, `# type: ignore`, empty `except:`, `except Exception: pass` |
| Required Commands | `python -c "from plugins.memory.guinevere_memory import GuinevereMemoryProvider; p = GuinevereMemoryProvider(); assert p.name == 'guinevere-memory'"` (exit 0). `python -m pytest tests/hermes/test_memory_bridge.py -v` (exit 0). `python -m pytest tests/memory/ -v -k consent` (exit 0). |
| Evidence Requirements | docs/setup-evidence/phase-3/verification-P3-001.md, docs/setup-evidence/phase-3/auditor-gate-P3-001.md |
| Hard Rejection Criteria | FAIL if: plugin does not inherit MemoryProvider, sync_turn is blocking (no daemon thread), principal is configurable (must be hardcoded guinevere_core), any write to ~/.hermes/state.db from Python code, consent gate missing from prefetch or sync_turn |

### P3-002 Scaffold

| Field | Value |
|---|---|
| Expected Files | No new files. Verified: hermes-config/config.yaml (read-only) |
| Forbidden Patterns | Modifications to compression config values that deviate from threshold=0.7, target=0.2, protect_last=20 |
| Required Commands | `python -c "import yaml; c = yaml.safe_load(open('hermes-config/config.yaml')); assert c['memory']['compression']['threshold'] == 0.7"` (exit 0) |
| Evidence Requirements | docs/setup-evidence/phase-3/verification-P3-002.md, docs/setup-evidence/phase-3/auditor-gate-P3-002.md |
| Hard Rejection Criteria | FAIL if: compression threshold != 0.7, protect_last != 20, on_pre_compress hook not registered in plugin.yaml |

### P3-003 Scaffold

| Field | Value |
|---|---|
| Expected Files | Created: plugins/memory/guinevere-memory/safety_gates.py. Modified: hermes-config/config.yaml (session_search block added), plugins/memory/guinevere-memory/\_\_init\_\_.py (add safety_gates import + wiring) |
| Forbidden Patterns | `as any`, `@ts-ignore`, any code path that bypasses DNR gate, any code that writes to ~/.hermes/state.db from Python, safety gate code in `__init__.py` (must be in `safety_gates.py`) |
| Required Commands | `grep -n 'apply_safety_gates\|dnr_id_cache\|classification_enrichment' plugins/memory/guinevere-memory/safety_gates.py` (must find matches in safety_gates.py, NOT __init__.py). `grep -n 'from .safety_gates import' plugins/memory/guinevere-memory/__init__.py` (must find import). `python -m pytest tests/memory/ -v -k dnr` (exit 0). `python -m pytest tests/memory/ -v -k consent` (exit 0). |
| Evidence Requirements | docs/setup-evidence/phase-3/verification-P3-003.md, docs/setup-evidence/phase-3/auditor-gate-P3-003.md |
| Hard Rejection Criteria | FAIL if: session_search enabled without DNR post-recall gate, any Hermes recall path without classification ceiling filter, anti-hallucination guard not injected on empty results, consent gate not checked before pipeline delegation, DNR cache fail-open (must be fail-closed), classification enrichment fail-open (must be fail-closed) |

### P3-004 Scaffold

| Field | Value |
|---|---|
| Expected Files | SQL migration script (not in repo; applied on VPS). Evidence: docs/setup-evidence/phase-3/verification-P3-004.md |
| Forbidden Patterns | GRANT INSERT/UPDATE/DELETE to hermes_memory_bridge, any role with SUPERUSER, hardcoded passwords in repo, RLS policies missing on memory tables |
| Required Commands | VPS: `sudo -u postgres psql -c "SELECT privilege_type FROM information_schema.role_table_grants WHERE grantee='hermes_memory_bridge' AND privilege_type != 'SELECT'"` (must return 0 rows). VPS: `sudo -u postgres psql -c "SELECT extversion FROM pg_extension WHERE extname='vector'"` (must show >= 0.5.2). VPS: `sudo -u postgres psql -c "SELECT tablename, policyname FROM pg_policies WHERE schemaname='memory' AND rolename='hermes_memory_bridge'"` (must return >= 4 policies: classification ceiling + surveillance isolation per table). VPS: `sudo -u postgres psql -c "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relnamespace = (SELECT oid FROM pg_namespace WHERE nspname='memory')"` (relrowsecurity=true, relforcerowsecurity=true for all memory tables). |
| Evidence Requirements | docs/setup-evidence/phase-3/verification-P3-004.md, docs/setup-evidence/phase-3/auditor-gate-P3-004.md |
| Hard Rejection Criteria | FAIL if: hermes_memory_bridge has any non-SELECT privilege, pgvector version < 0.5.2, password committed to repo, ALTER DEFAULT PRIVILEGES missing, RLS not enabled on memory tables, surveillance isolation policy missing, explicit REVOKE INSERT/UPDATE/DELETE/TRUNCATE missing |

### P3-005 Scaffold

| Field | Value |
|---|---|
| Expected Files | scripts/ab_test_recall.py, evidence/memory-eval/dataset/golden-dataset-v1.0.json, tests/memory/test_ab_recall.py. Modified: requirements.txt (add scipy) |
| Forbidden Patterns | `as any`, `@ts-ignore`, `# type: ignore`, empty except, hardcoded query counts (must use --queries flag) |
| Required Commands | `python -m pytest tests/memory/test_ab_recall.py -v` (exit 0). `python scripts/ab_test_recall.py --help` (exit 0, shows usage). `python -c "import scipy; print(scipy.__version__)"` (exit 0) |
| Evidence Requirements | docs/setup-evidence/phase-3/verification-P3-005.md, docs/setup-evidence/phase-3/auditor-gate-P3-005.md |
| Hard Rejection Criteria | FAIL if: golden dataset has fewer than 100 queries, harness does not compute p-value, harness does not check DNR violations, scipy not in requirements |

### P3-006 Scaffold

| Field | Value |
|---|---|
| Expected Files | evidence/memory-eval/ab-results-{timestamp}.json |
| Forbidden Patterns | Manual p-value override, DNR violation suppression |
| Required Commands | `python scripts/ab_test_recall.py --queries 100 --output evidence/memory-eval/` (exit 0) |
| Evidence Requirements | docs/setup-evidence/phase-3/verification-P3-006.md, docs/setup-evidence/phase-3/auditor-gate-P3-006.md |
| Hard Rejection Criteria | FAIL if: p-value < 0.05, any DNR violation in results, any hallucination detected, G-B1 still broken (embedding API unavailable) |

### P3-007 Scaffold

| Field | Value |
|---|---|
| Expected Files | Evidence: docs/setup-evidence/phase-3/verification-P3-007.md |
| Forbidden Patterns | Any INSERT/UPDATE/DELETE in plugin code targeting PostgreSQL, any write connection from Hermes to PG |
| Required Commands | VPS: `sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE usename='hermes_memory_bridge' AND query NOT ILIKE 'SELECT%'"` (must return 0). VPS: `sudo -u postgres psql -c "ALTER ROLE hermes_memory_bridge SET log_statement = 'mod'"` (exit 0). VPS: `sudo -u postgres psql -c "SELECT rolname, rolconfig FROM pg_roles WHERE rolname='hermes_memory_bridge'"` (must show log_statement=mod). Code: `grep -rn 'INSERT\|UPDATE\|DELETE' plugins/memory/guinevere-memory/` (must return 0 matches on PG-targeting code). Code: `grep -rn 'log.*connection\|log.*dsn\|log.*password\|log.*DSN' plugins/memory/guinevere-memory/` (must return 0 — connection strings must not be logged). |
| Evidence Requirements | docs/setup-evidence/phase-3/verification-P3-007.md, docs/setup-evidence/phase-3/auditor-gate-P3-007.md |
| Hard Rejection Criteria | FAIL if: any write query from hermes_memory_bridge detected, any write privilege granted, plugin code contains PG write operations, log_statement='mod' not configured for hermes_memory_bridge role, connection strings logged anywhere in plugin code |

### P3-008 Scaffold

| Field | Value |
|---|---|
| Expected Files | Updated: docs/README.md, docs/10-governance/17-ADR_Index_v1.0.md |
| Forbidden Patterns | Safety boundary modifications without Oracle review |
| Required Commands | All P3-001 through P3-007 and P3-009 verification commands must still pass (regression check) |
| Evidence Requirements | docs/setup-evidence/phase-3/verification-P3-008.md, docs/setup-evidence/phase-3/auditor-gate-P3-008.md |
| Hard Rejection Criteria | FAIL if: any prior step verification fails, any safety checklist item unchecked, any auditor report not PASS |

### P3-009 Scaffold

| Field | Value |
|---|---|
| Expected Files | Modified: hermes-config/config.yaml (mirrors block added), plugins/memory/guinevere-memory/\_\_init\_\_.py (extract_key_facts implementation for mirror sync). Created: tests/hermes/test_mirror_sync.py |
| Forbidden Patterns | `as any`, `@ts-ignore`, `# type: ignore`, empty `except:`, Critical/Confidential content in mirror files, DNR-marked content in mirror files, PII/intimate data in mirror files, blocking mirror sync (must be daemon thread) |
| Required Commands | `python -c "import yaml; c = yaml.safe_load(open('hermes-config/config.yaml')); assert c['memory']['mirrors']['enabled'] == True"` (exit 0). `python -c "import yaml; c = yaml.safe_load(open('hermes-config/config.yaml')); assert c['memory']['mirrors']['sync_interval_messages'] == 5"` (exit 0). `python -m pytest tests/hermes/test_mirror_sync.py -v` (exit 0). `grep -rn 'Critical\|Confidential' ~/.hermes/mirrors/ 2>/dev/null` (zero matches after classification filter). All P3-001 through P3-007 verification commands must still pass (regression check). |
| Evidence Requirements | docs/setup-evidence/phase-3/verification-P3-009.md, docs/setup-evidence/phase-3/auditor-gate-P3-009.md |
| Hard Rejection Criteria | FAIL if: mirrors.enabled not true, sync_interval_messages != 5, extract_key_facts returns empty for test input, mirror files contain Critical/Confidential content, mirror files contain DNR-marked content, mirror sync blocks conversation (latency increase > 100ms), mirror files contain PII/intimate data, deduplication not working (same fact repeated) |

---

## 10. Token/Secret Handling

| Secret | Where Stored | Access Pattern | Phase 3 Steps |
|---|---|---|---|
| HERMES_PG_PASSWORD | VPS env / 1Password | Connection string only, never in repo | P3-004 (RBAC role creation) |
| GUINEVERE_PG_DSN | $HERMES_HOME/.env (SOPS-encrypted at rest) | Plugin config schema secret field | P3-001 (plugin config) |
| 9Router API key | 9Router dashboard | No code change needed | Pre-requisite (G-B1 fix) |
| OpenAI API key (fallback) | $HERMES_HOME/.env (SOPS-encrypted at rest) | Direct API fallback if 9Router fails | P3-001 (fallback chain) |
| REDIS_PASSWORD | VPS env / 1Password | Plugin consent gate reads from Redis | P3-001 (consent state query) |
| DISCORD_TOKEN | VPS env / 1Password | Not used by memory plugin; listed for completeness | N/A |

**Rule**: No secrets committed to repo. All secrets use env_var pattern in plugin config schema. `.env` files encrypted with SOPS/age at rest — never plaintext in repo artifacts. Plugin code must not log, print, or expose connection strings or credentials in any log output.

---

## 11. Evidence Paths

| Evidence Type | Path Pattern | Created By |
|---|---|---|
| Per-step verification | docs/setup-evidence/phase-3/verification-P3-NNN.md | Verifier sub-agent |
| Per-step auditor gate | docs/setup-evidence/phase-3/auditor-gate-P3-NNN.md | Auditor sub-agent |
| Research reports | research-reports/phase-3-planning/NN-title.md | Research wave (DONE) |
| A/B test results | evidence/memory-eval/ab-results-{timestamp}.json | P3-006 execution |
| Golden dataset | evidence/memory-eval/dataset/golden-dataset-v1.0.json | P3-005 creation |
| Planner gate | docs/setup-evidence/phase-3/batch-plan-phase-3.md | Parent (THIS FILE) |

---

## 12. Auditor Matrix

| Step | Auditor Type | Focus Areas | Parallel With |
|---|---|---|---|
| P3-001 | Code Quality + Safety | MemoryProvider ABC compliance, threading contract, safety delegation, no type suppression | P3-004, P3-005 auditors |
| P3-002 | Config + Safety | Compression threshold correctness, hook registration, Critical classification handling | P3-003 auditor |
| P3-003 | Safety + DNR | Post-recall DNR gate, classification ceiling, anti-hallucination, safe-mode | P3-002 auditor |
| P3-004 | Security + DBA | RBAC correctness, no write privileges, pgvector version, no secrets in repo | P3-001, P3-005 auditors |
| P3-005 | Code Quality + Testing | Harness correctness, golden dataset coverage, scipy usage, no hardcoded values | P3-001, P3-004 auditors |
| P3-006 | Quality + Safety | A/B results validity, p-value correctness, DNR violations, hallucination check | After P3-006 |
| P3-007 | Security + DBA | Zero write verification, RBAC persistence, plugin code review | After P3-007 |
| P3-008 | Full Safety Audit | All safety boundaries, all evidence, all auditor reports, regression check | Final gate |
| P3-009 | Safety + Code Quality | Mirror sync config, classification filter on mirrors, DNR exclusion, non-blocking sync, no PII/intimate data | P3-002, P3-003 auditors |

---

## 13. Gap Mapping Rationale

Several gaps from `07-MEMORY-BRIDGE-GAP.md` were originally recommended for Phase 1 or Phase 2 but are addressed in Phase 3. This section documents the rationale for the phase shift.

| Gap ID | Gap Title | Original Recommendation | Actual Phase | Rationale |
|---|---|---|---|---|
| G-B3 | Auto-store fails when embedding unavailable | Phase 1 (immediate fix) | Phase 3 (P3-001) | Store failure is caused by embedding routing (G-B1), which requires 9Router config fix. P3-001 refactors store path through plugin's `sync_turn()` with graceful degradation (FTS-only store without vector). Fixing this before Phase 3 plugin refactor would create duplicate work. |
| G-B6 | No classification enforcement on Hermes recall | Phase 2 | Phase 3 (P3-003) | Classification enforcement for Hermes requires the safety gates module (safety_gates.py) which is built as part of P3-003. Phase 2 focused on Discord migration where classification was already enforced by read_pipeline. Hermes path needs separate enforcement built into the plugin. |
| G-B7 | hard_stop_handler not wired to Hermes | Phase 1 | Phase 3 (P3-001, P3-008) | HARD STOP is already enforced by safety_plugin.py at the LLM level. Hermes integration requires the plugin lifecycle hooks (on_session_end) which are built in P3-001. The safety boundary is already active; Hermes integration is additive. |
| G-B9 | No DNR enforcement on Hermes FTS5 | Phase 2 | Phase 3 (P3-003) | Same as G-B6: requires safety_gates.py built in P3-003. DNR enforcement for Hermes FTS5 results needs the DNR ID cache approach which is designed as part of the session_search safety gates. |
| G-B10 | Memory consolidation not Hermes-aware | Phase 2 | Phase 3 (P3-009) | Consolidation depends on mirror sync (MEMORY.md/USER.md) which is P3-009. Hermes has its own compression-based consolidation; the bridge consolidation path mirrors key facts from PG to Hermes mirrors. This is a Phase 3 concern after the core plugin (P3-001) and safety gates (P3-003) are operational. |

**General principle**: All five gaps require the MemoryProvider plugin (P3-001) as a prerequisite. Addressing them before the plugin exists would require temporary workarounds that are immediately superseded. Phase 1 and Phase 2 addressed safety boundaries at the existing codebase level; Phase 3 extends those boundaries to the Hermes integration path.

---

## 14. Rollback Plan

| Scenario | Rollback Procedure | Time Estimate |
|---|---|---|
| P3-001 fails | Revert plugin files, restore memory_bridge.py imports in conversational_handler.py | Under 5 minutes |
| P3-002 fails | Set compression.enabled: false in hermes-config/config.yaml | Under 1 minute |
| P3-003 fails | Set session_search.enabled: false in hermes-config/config.yaml | Under 1 minute |
| P3-004 fails | DROP ROLE hermes_memory_bridge; remove replication config from pg_hba.conf | Under 3 minutes |
| P3-006 fails (p < 0.05) | Disable session_search + compression. Revert to Phase 2 state. Investigate recall quality regression. | Under 5 minutes |
| P3-007 fails (writes detected) | Revoke all grants from hermes_memory_bridge. Disable plugin. | Under 3 minutes |
| P3-009 fails | Set memory.mirrors.enabled: false in hermes-config/config.yaml. Mirror files persist but stop updating. | Under 1 minute |
| Full rollback | Disable all Phase 3 features. Restore skip_memory=True in session_adapter.py. | Under 10 minutes |

---

## 15. Caveats and Known Risks

1. **VPS State Unknown**: SSH timed out from Windows. All PostgreSQL and Redis verification steps require direct VPS access. Pre-flight checklist must be run before execution begins.

2. **G-B1 Pre-requisite**: If 9Router embedding config cannot be fixed (HTTP 400), the A/B test (P3-006) is INVALID. Vector search will not fire, making the test FTS-only. This must be resolved before Wave 3.

3. **Hermes Agent Version Dependency**: The MemoryProvider ABC is based on hermes-agent v0.2.0+. If the VPS runs a different version, the plugin interface may need adjustment. Verify hermes-agent version before P3-001.

4. **Golden Dataset Construction**: Building 100+ graded queries requires access to actual memory data. If VPS is inaccessible, synthetic queries must be used, which may not represent real-world recall quality.

5. **Streaming Replication Infrastructure**: P3-004 assumes the VPS has capacity for a Hot Standby replica. If the VPS is resource-constrained, logical replication or RBAC-only enforcement (without full replication) may be needed as fallback.

6. **Hermes Compression Behavior**: Relying on Hermes-native compression means we cannot independently verify compression behavior without running the full Hermes stack. If Hermes compression does not activate as configured, a custom fallback may be needed.

7. **Consent Gate Novelty (Safety Audit Addition)**: No existing codebase component has a consent gate on memory operations. The consent gate in P3-001 is net-new functionality. It requires a consent state store (Redis DB2 or config file) that does not currently exist in the Guinevere codebase. Pre-requisite: define consent state schema and storage location before P3-001 implementation.

8. **RLS Policy Maintenance (DBA Audit Addition)**: RLS policies with `FORCE ROW LEVEL SECURITY` apply to all sessions including the table owner. The `memory_owner` role used by `ALTER DEFAULT PRIVILEGES` must not be the table owner, or RLS must be configured carefully to avoid blocking the write path. Verify `memory_owner` is a dedicated non-superuser role. v1.3 FIX (Auditor Tech F4): P3-004 now includes a pre-requisite check that verifies `memory_owner` exists before running the SQL migration, with a fallback to discover the actual table-owning role via `pg_tables`.

9. **Hermes Principal Definition (DBA Audit Addition)**: Hermes is defined as an external framework principal outside the current Guinevere RBAC matrix. This definition must be added to `docs/20-security/21-RBAC_ABAC_Matrix_v1.0.md` during P3-004 execution. The RBAC matrix update is a doc-sync task owned by parent.

10. **~/.hermes/state.db Data Exfiltration**: Hermes writes compressed conversation data to its own SQLite state.db. If Critical-classified data is processed through Hermes (even transiently), it may be cached in state.db. Mitigation: RLS classification ceiling prevents Critical data from reaching Hermes in the first place. If RLS is misconfigured, state.db could contain Critical data. P3-008 must verify RLS policy correctness as a pre-condition for trusting state.db contents.

---

## 16. Execution Checklist

### Pre-Execution
- [ ] VPS SSH access verified
- [ ] PostgreSQL connection confirmed
- [ ] Redis connection confirmed
- [ ] 9Router embedding config fixed (G-B1 resolved)
- [ ] hermes-agent version verified (>= v0.2.0)
- [ ] VPS capacity for streaming replica confirmed
- [ ] All research reports read and synthesized (DONE)
- [ ] This planner gate reviewed by 3 auditors (PENDING)

### Wave 1 (Parallel)
- [ ] P3-001: Refactor memory_bridge to memory_plugin
- [ ] P3-004: Configure PostgreSQL mirror sync
- [ ] P3-005: Build A/B testing infrastructure

### Wave 2 (Parallel, after P3-001)
- [ ] P3-002: Verify compression at 70%
- [ ] P3-003: Enable session_search FTS5 with safety gates
- [ ] P3-009: Configure Hermes mirror sync (MEMORY.md/USER.md)

### Wave 3 (Sequential, after Wave 2 + P3-005)
- [ ] P3-006: Execute A/B test (100 queries)
- [ ] P3-007: Verify zero PG writes from Hermes

### Wave 4 (Sequential, after all)
- [ ] P3-008: Final integration verification and safety audit

### Post-Execution
- [ ] All evidence files created
- [ ] All auditor reports PASS
- [ ] docs/README.md updated
- [ ] ADR-Index updated
- [ ] Rollback procedures tested
- [ ] Final report to Faiz

---

## 17. Footer

### Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-04 | Guinevere (Parent Planner) | Initial planner gate with 8 atomic steps, per-step scaffolds, dependency map, collision scan, rollback plan |
| 1.1 | 2026-06-04 | Guinevere (Parent Planner) | Auditor fix pass: (1) Safety gates moved to separate `safety_gates.py` module — resolves Wave 2 collision (Arch-A1). (2) Consent gate added to P3-001 prefetch/sync_turn with fail-closed pattern (Safety-S1). (3) DNR ID cache + PG classification enrichment specified for P3-003 (Safety-S2/S3). (4) RLS policies with classification ceiling + surveillance isolation added to P3-004 (Safety-S4, DBA-D2). (5) Safe-word logging documented (Safety-S5). (6) Explicit REVOKE INSERT/UPDATE/DELETE/TRUNCATE (DBA-D1). (7) Streaming replication config detailed with wal_level, max_wal_senders, ssl_mode (DBA-D3). (8) log_statement='mod' added to P3-007 scaffold (DBA-D4). (9) REDIS_PASSWORD, DISCORD_TOKEN, SOPS encryption added to secrets table (DBA-D5/D6). (10) Network isolation via Tailscale specified (DBA-D7). (11) state.db exfiltration addressed via RLS classification ceiling (DBA-D8). (12) Connection string logging rule added (DBA-D9). (13) 4 new caveats added. Ready for re-audit. |
| 1.2 | 2026-06-04 | Guinevere (Parent Planner) | Second auditor fix pass (6 findings across 3 auditors): (1) All SQL table names fixed: `memory.episodic_memory` → `memory.episodes` (Safety S10, Tech T4). (2) RLS classification ceiling fixed: string comparison `classification_level <= 'Restricted'` replaced with IN-list `classification IN ('Public', 'Internal', 'Restricted')` because lexicographic ordering is wrong for classification enum (Safety S10). (3) A/B test statistical method fixed: `ttest_ind` → `ttest_rel` because queries are paired samples (Tech T5). (4) P3-009 added: Hermes mirror sync (MEMORY.md/USER.md) from canonical phase-3-memory.md Step 3.4 — was missing entirely (ADR C2). (5) Gap mapping rationale section added documenting why G-B3/G-B6/G-B7/G-B9/G-B10 shifted from Phase 1/2 to Phase 3 (ADR C6). (6) Section numbering updated (§13-§17). Ready for re-audit. |
| 1.3 | 2026-06-05 | Guinevere (Parent Planner) | Third auditor fix pass (4 findings from Technical Accuracy re-audit; Memory Safety passed v1.2): (1) F1 HIGH: Fixed file path `src/hermes/memory/memory_bridge.py` → `src/hermes/memory_bridge.py` at 4 locations (Known State, §7.2, P3-001 scaffold, P3-009 scaffold). (2) F2 MEDIUM: Moved `extract_key_facts()` implementation target from deprecated `memory_bridge.py` to plugin module `plugins/memory/guinevere-memory/__init__.py` (P3-009 design + scaffold). (3) F3 LOW: Added P3-009 entries to §7.2 Files to MODIFY table (plugin \_\_init\_\_.py + config.yaml). (4) F4 MEDIUM: Added pre-requisite check for `memory_owner` role existence with fallback discovery via `pg_tables`, strengthened caveat 8. Ready for re-audit (Tech Accuracy + ADR-035 Compliance only; Memory Safety already PASS). |

### Approval

This planner gate (v1.3) has been revised to address all findings from the third auditor review:
1. Memory Safety Auditor: **PASS** on v1.2 — no re-audit needed
2. Technical Accuracy Auditor (NEEDS REVIEW → 4 items fixed: file path corrected, extract_key_facts moved to plugin, §7.2 table updated, memory_owner pre-requisite added)
3. ADR-035 Compliance Auditor: **INCOMPLETE** on v1.2 (session ended before report written) — needs fresh re-audit on v1.3

**Re-audit required**: Tech Accuracy and ADR-035 Compliance auditors must re-review v1.3 and PASS before Wave 1 execution begins.

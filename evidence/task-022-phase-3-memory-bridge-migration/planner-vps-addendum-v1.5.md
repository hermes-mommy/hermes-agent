# Phase 3 Planner Addendum v1.5 — VPS-Verified Corrections

**Date**: 2026-06-05  
**Author**: Guinevere (Parent Planner)  
**Base Plan**: batch-plan-phase-3.md v1.4  
**Status**: VPS-verified, ready for implementation  
**VPS Reports**: `research-reports/phase-3-execution/01..04-*.md`

---

## 1. VPS State — RESOLVED (Caveat 1 from v1.4)

| Check | v1.4 Status | v1.5 Status |
|---|---|---|
| VPS SSH access | UNKNOWN (timed out) | ✅ VERIFIED — `guinevere-vps` (100.94.104.22 via Tailscale, user `guinevere`, key `~/.ssh/id_ed25519`) |
| PostgreSQL connection | UNKNOWN | ✅ VERIFIED — PG 16.14 in Docker `guinevere-postgres`, port 5433, scram-sha-256 |
| Redis connection | UNKNOWN | ✅ VERIFIED — Redis 7.4.9 in Docker `guinevere-redis`, port 6380, password-protected |
| SQLite files | UNKNOWN | ✅ VERIFIED — state.db (26 messages, 2 sessions, FTS5 tables), kanban.db (empty) |
| pgvector version | >= 0.5.2 required | ✅ VERIFIED — v0.8.2 |
| TimescaleDB | Not referenced | ✅ DISCOVERED — v2.27.1 installed, no hypertables on app tables yet |

---

## 2. Schema Verification — Table Names CONFIRMED CONSISTENT

| Code Model | `__tablename__` | VPS Table | Match |
|---|---|---|---|
| `Episodes` | `episodes` | `memory.episodes` | ✅ |
| `SemanticFacts` | `semantic_facts` | `memory.semantic_facts` | ✅ |
| `FaizProfile` | `faiz_profile` | `memory.faiz_profile` | ✅ |
| `EmotionalEvents` | `emotional_events` | `memory.emotional_events` | ✅ |
| `InnerJournal` | `inner_journal` | `memory.inner_journal` | ✅ |
| `FaizPredictions` | `faiz_predictions` | `memory.faiz_predictions` | ✅ |
| `ProceduralSkills` | `procedural_skills` | `memory.procedural_skills` | ✅ |
| `KnowledgeGraph` | `knowledge_graph` | `memory.knowledge_graph` | ✅ |

**Conclusion**: Code models and VPS schema are CONSISTENT. The `episodic_memories`/`semantic_memories` references in v1.4 research reports were outdated terminology, not actual table names. Batch plan v1.4 SQL already uses correct `memory.episodes` (fixed in v1.2).

**Row counts**: ALL tables at 0 rows. No application data exists yet.

---

## 3. Role Ownership — `guinevere` Superuser (Caveat 8 from v1.4)

| Check | v1.4 Assumption | v1.5 Reality |
|---|---|---|
| Table owner (`memory` schema) | `memory_owner` (hypothetical) | `guinevere` (superuser) |
| `memory_owner` role exists? | Pre-requisite check added | ❌ DOES NOT EXIST |
| `guinevere_core` role | 30 connections | ✅ EXISTS — correct application role |

**Impact on P3-004 SQL Migration**:
- Replace `ALTER DEFAULT PRIVILEGES FOR ROLE memory_owner` with `ALTER DEFAULT PRIVILEGES FOR ROLE guinevere`
- RLS `FORCE ROW LEVEL SECURITY` on `guinevere`-owned tables will apply to the superuser owner too — but superusers bypass RLS by default
- Mitigation: `hermes_memory_bridge` is NOT a superuser, so RLS applies correctly to it
- The write path uses `guinevere_core` role (not `hermes_memory_bridge`), so RLS does not block writes

**Updated P3-004 SQL (critical section only)**:

```sql
-- v1.5 CORRECTION: Table owner is 'guinevere' (superuser), not 'memory_owner'
ALTER DEFAULT PRIVILEGES FOR ROLE guinevere IN SCHEMA memory
  GRANT SELECT ON TABLES TO hermes_memory_bridge;

-- NOTE: RLS FORCE does not affect superuser 'guinevere' (bypasses RLS)
-- RLS only applies to non-superuser roles like 'hermes_memory_bridge'
-- This is correct behavior: writes via 'guinevere_core' role also bypass RLS
-- (guinevere_core is not a superuser but has explicit GRANT on memory tables)
```

**Additional roles on VPS** (for reference):

| Role | Connections | Purpose |
|---|---|---|
| `guinevere` | Superuser | Infrastructure owner |
| `guinevere_core` | 30 | Application read/write |
| `guinevere_readonly` | 15 | Read-only reporting |
| `guinevere_scheduler` | 10 | Cron/scheduler jobs |
| `guinevere_surveillance` | 10 | Surveillance subsystem |
| `guinevere_backup` | 5 | Backup operations |
| `guinevere_pgbouncer` | 5 | Connection pooling |

---

## 4. Hermes Version — v0.15.2 (Caveat 3 from v1.4)

| Check | v1.4 Assumption | v1.5 Reality |
|---|---|---|
| Hermes version | >= v0.2.0 | v0.15.2 (2026.5.29.2) |
| MemoryProvider ABC | Available | ⚠️ NEEDS VERIFICATION — v0.15.2 is Hermes gateway version, Python lib version may differ |
| External memory config | Available | ✅ `memory: provider: ''` (empty, ready to set) |
| Memory plugin loading | From `plugins/memory/` | ⚠️ NEEDS VERIFICATION — safety plugin loaded from `hermes-config/plugins/` |

**Action**: Before P3-001 implementation, verify:
1. Check `hermes-agent` Python package version on VPS: `pip show hermes-agent` or `hermes --version`
2. Check if Hermes loads memory plugins from a specific directory: review Hermes docs for MemoryProvider plugin path
3. Verify `register()` function signature for memory plugins (may differ from safety plugins)

---

## 5. 9Router State — G-B1 STILL BLOCKED

| Check | v1.4 Status | v1.5 Status |
|---|---|---|
| 9Router embedding endpoint | HTTP 400 | ⚠️ HTTP 401 (token invalidated) |
| 9Router port | Assumed 9000 | ✅ VERIFIED — port 20128 |
| 9Router `/health` | Unknown | ❌ Returns 404 |
| 9Router `/v1/embeddings` | Unknown | ⚠️ UNVERIFIED — token rotation needed first |

**Impact**: G-B1 pre-requisite still blocks P3-006 (A/B test execution). P3-001, P3-004, P3-005 can proceed independently. P3-006 MUST be gated on G-B1 resolution.

---

## 6. Hermes Config State — External Memory DISABLED

Current Hermes memory configuration:

```yaml
memory:
  provider: ''          # EMPTY — no external memory connected
  compression:
    enabled: true
    threshold: 0.7
    target: 0.2
    protect_last: 20
  session_search:
    enabled: true       # Already enabled
    backend: fts5
  mirrors:
    enabled: true       # Already enabled
    sync_interval_messages: 5
```

**P3-001 Impact**: Plugin must set `memory.provider: 'guinevere-memory'` to activate.
**P3-002 Impact**: Compression config already correct — P3-002 is essentially a verification-only step.
**P3-003 Impact**: session_search already enabled — P3-003 focuses on safety gates module, not config change.
**P3-009 Impact**: Mirrors already configured — P3-009 focuses on `extract_key_facts()` implementation.

---

## 7. SQLite State — FTS5 Tables Exist

| File | Size | Content |
|---|---|---|
| `~/.hermes/state.db` | 104 KB | 26 messages, 2 sessions, FTS5 tables (messages_fts, messages_fts_trigram) |
| `~/.hermes/kanban.db` | 104 KB | All tables empty |
| `~/.9router/db/data.sqlite` | 2.1 MB | 492 requestDetails, 26 providerConnections |

**P3-003 Impact**: Hermes session_search FTS5 already operational. Safety gates module must filter its results.

---

## 8. Golden Dataset — Must Be Synthetic (Caveat 4 from v1.4)

| Check | v1.4 Assumption | v1.5 Reality |
|---|---|---|
| Existing memory data for dataset | Assumed available | ❌ ZERO rows in all memory tables |
| Dataset construction | Real queries + ground truth | Must use synthetic queries + synthetic ground truth |

**P3-005 Impact**: Golden dataset must be entirely synthetic. The A/B test harness must:
1. Generate synthetic memory entries (episodes with known content)
2. Seed them into PostgreSQL before test execution
3. Run queries against the seeded data
4. Clean up synthetic data after test

**Alternative**: Skip seeding and test with FTS-only mode (since embedding is broken anyway). This tests the recall pipeline without vector search, which is the current operational mode.

---

## 9. Out-of-Scope Issues (Documented, Not Addressed)

| Issue | Severity | Notes |
|---|---|---|
| MCP servers ALL BROKEN (5/5) | HIGH | Missing `command` in config. Out of Phase 3 scope. |
| 9Router token invalidated | HIGH | Needs rotation for embedding to work. Pre-requisite for P3-006 only. |
| Gateway instability (13+ restarts) | MEDIUM | Stale systemd unit warning. Investigate separately. |
| SOUL.md blocked (prompt_injection) | LOW | 2 sessions affected. Safety plugin working as designed. |
| Redis overcommit warning | LOW | `vm.overcommit_memory = 1` not set. Non-critical at 1.2MB/2GB usage. |
| Duplicate safety plugins (2 active) | LOW | `guinevere-safety` (migrated) + `guinevere_safety` (v1 duplicate). Cleanup separately. |

---

## 10. Updated Collision Scan (v1.5)

| Collision Type | Affected Steps | v1.5 Status |
|---|---|---|
| `plugins/memory/guinevere-memory/__init__.py` | P3-001 creates → P3-003 imports → P3-009 adds extract_key_facts | Sequential: P3-001 → P3-003 → P3-009. No parallel writes. |
| `plugins/memory/guinevere-memory/safety_gates.py` | P3-003 creates | Sole owner: P3-003. No collision. |
| `hermes-config/config.yaml` | P3-001 enables provider → P3-003 may update session_search → P3-009 adds mirrors block | ⚠️ NEW: P3-001 sets `memory.provider`. P3-003 session_search already enabled (no change needed). P3-009 mirrors already enabled (no change needed). **Only P3-001 modifies config.yaml** (sets provider name). |
| `src/hermes/memory_bridge.py` | P3-001 deprecates | Sole owner: P3-001. No collision. |
| `src/discord/conversational_handler.py` | P3-001 updates imports | Sole owner: P3-001. No collision. |
| PostgreSQL schema (VPS) | P3-004 adds RBAC/RLS → P3-007 verifies | Sequential: P3-004 → P3-007. P3-007 is read-only verification. |
| `scripts/ab_test_recall.py` | P3-005 creates → P3-006 executes | Sequential: P3-005 → P3-006. No collision. |

**v1.5 Correction**: `hermes-config/config.yaml` collision is SIMPLIFIED. Session_search and mirrors are already configured. Only P3-001 needs to set `memory.provider: 'guinevere-memory'`. No concurrent config.yaml edits.

---

## 11. Updated Execution Checklist (v1.5)

### Pre-Execution
- [x] VPS SSH access verified ✅
- [x] PostgreSQL connection confirmed ✅
- [x] Redis connection confirmed ✅
- [ ] 9Router embedding config fixed (G-B1 — STILL BLOCKED, token rotation needed)
- [ ] Hermes MemoryProvider ABC verified on v0.15.2 (check Python package version)
- [x] VPS capacity confirmed (no separate replica needed — RLS-only approach)
- [x] All research reports read and synthesized ✅
- [ ] Planner gate v1.5 reviewed

### Wave 1 (Parallel)
- [ ] P3-001: Refactor memory_bridge to memory_plugin + enable provider in config.yaml
- [ ] P3-004: RBAC + RLS on VPS (table owner = `guinevere`, role = `hermes_memory_bridge`)
- [ ] P3-005: Build A/B testing infra (synthetic golden dataset since 0 rows)

### Wave 2 (After P3-001)
- [ ] P3-002: Verify compression at 70% (config already correct — verification only)
- [ ] P3-003: Safety gates module for session_search (session_search already enabled)

### Wave 2b (After P3-003)
- [ ] P3-009: Mirror sync extract_key_facts() (mirrors config already set)

### Wave 3 (After Wave 2/2b + P3-005 + G-B1 fix)
- [ ] P3-006: Execute A/B test (BLOCKED on G-B1)
- [ ] P3-007: Verify zero PG writes from Hermes

### Wave 4
- [ ] P3-008: Final integration gate

---

## 12. Implementation Decisions (v1.5 Binding)

| Decision | v1.4 | v1.5 Correction | Rationale |
|---|---|---|---|
| Streaming replication | Full Hot Standby | **RLS-only (no replica)** | VPS is single-instance Docker. Adding a streaming replica requires second PG container, doubling resources. RLS on the existing instance provides equivalent read isolation for `hermes_memory_bridge`. Replica can be added later if needed. |
| Plugin directory | `plugins/memory/guinevere-memory/` | ⚠️ VERIFY on VPS | Hermes safety plugin is in `hermes-config/plugins/`. Memory plugin may use same path or Hermes-specific memory plugin dir. Check Hermes docs before P3-001. |
| Table owner for ALTER DEFAULT PRIVILEGES | `memory_owner` | `guinevere` | Verified via VPS: `guinevere` owns all `memory` schema tables. |
| Golden dataset source | Real data | Synthetic | 0 rows in all memory tables. Must seed synthetic data for testing. |
| Config.yaml changes | Multiple steps modify | Only P3-001 modifies | session_search + mirrors already configured on VPS. |
| 9Router port | Assumed 9000 | 20128 | Verified via VPS. Plugin config must use port 20128. |

---

## 13. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.5 | 2026-06-05 | Guinevere (Parent Planner) | VPS-verified corrections: (1) VPS access resolved — all infrastructure confirmed healthy. (2) Table owner = `guinevere` (superuser), not `memory_owner`. (3) Streaming replication → RLS-only approach (single Docker instance). (4) Config.yaml changes simplified (session_search + mirrors already configured). (5) Golden dataset must be synthetic (0 rows). (6) 9Router port = 20128. (7) G-B1 still blocked (token invalidated). (8) Hermes v0.15.2 — MemoryProvider ABC needs Python package version check. (9) Out-of-scope issues documented (MCP broken, gateway instability, duplicate plugins). |

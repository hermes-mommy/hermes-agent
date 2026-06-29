# R18: P19/P20/P22 Regression Risks for P24 v3.0

**Date**: 2026-06-29
**Author**: Research Agent (Domain 18)
**Method**: File reads, grep scans across `src/`, `tests/`, `docs/setup-evidence/`, `PROGRESS.md`, `p24-hermes-native-fork-enterprise-plan.md` v3.0
**Status**: Research Complete

---

## 1. Summary

P24 v3.0 absorbs ALL P1-P22 code into 17 native Hermes modules and deletes 69 files (~12,000 lines) from `src/`. This creates four regression risk domains:

1. **P22 adapter functionality** absorbed into M8 must not break (897-test baseline)
2. **P20 heartbeat/sensors/brain** ported to M9 must not break (420-test baseline, production soak)
3. **P19 project_id namespace** preserved by M1 config must not break audit log + memory flow
4. **Consent gate conflict** between P22 (L2+ gated) and M11 (all removed) requires surgical deletion with zero stale imports

Each domain has specific regression tests that W18/W19 must run.

---

## 2. (a) P22 Adapters M8 Absorbs -- Must Not Break Adapter Functionality

### 2.1 What M8 Absorbs

P22 deployed 13 adapters under `src/life_integrations/adapters/` (verified on disk):

| # | Adapter File | Size | P22 Dispatch Levels |
|---|---|---|---|
| 1 | `browser_adapter.py` | 6,516B | L1-L4 |
| 2 | `calendar_adapter.py` | 6,829B | L1-L4 |
| 3 | `discord_adapter.py` | 7,599B | L1-L4 |
| 4 | `drive_adapter.py` | 8,268B | L1-L4 |
| 5 | `filesystem_adapter.py` | 6,284B | L1-L4 |
| 6 | `finance_adapter.py` | 11,719B | L1-L4 |
| 7 | `github_adapter.py` | 11,915B | L1-L4 |
| 8 | `gmail_adapter.py` | 7,747B | L1-L4 |
| 9 | `memory_adapter.py` | 7,478B | L1-L4 |
| 10 | `notion_adapter.py` | 6,409B | L1-L4 |
| 11 | `telegram_adapter.py` | 8,203B | L1-L4 |
| 12 | `vps_adapter.py` | 14,337B | L1-L4 |
| 13 | `whatsapp_adapter.py` | 6,467B | L1-L4 |

Plus infrastructure: `base.py` (BaseIntegrationAdapter ABC), `registry.py`, `types.py`, `router.py` (ActionRouter), `consent.py`, `consent_checker.py`, `permissions.py` (SemanticActionClassifier), `audit.py`, `audit_db_writer.py`, `scheduler.py`, `wiring.py`, `runtime.py`, `tombstone.py`, `secrets.py`.

Source: `src/life_integrations/adapters/` (14 `.py` files, verified via `ls`).

M8 unifies these into 9 `guinevere/tools/backends/` with `ToolBackend` ABC:
- browser, github, filesystem, vps, email, desktop, freelance, social, memory
- ~108 unified actions (42 P22 + 68 P23, minus 18 overlap = ~108)
- `ActionTier` soft labels (READ/WRITE/DESTRUCTIVE) replace L1-L4 enforcement
- L4_FORBIDDEN deleted per ADR-062

**Source**: Plan `p24-hermes-native-fork-enterprise-plan.md` lines 631-700 (M8 spec), lines 1511-1524 (Appendix A action catalog).

### 2.2 What M8 Deletes from P22

| Deleted File | Lines | Purpose |
|---|---|---|
| `src/life_integrations/consent.py` | 188 | ConsentGate + ConsentCheckerProtocol |
| `src/life_integrations/consent_checker.py` | 119 | P22ConsentChecker (SQL query) |
| `src/life_integrations/consent_ledger_writer.py` | 518 | Consent ledger DB writer |
| `src/life_integrations/permissions.py` | (referenced) | SemanticActionClassifier + PermissionTier.L4 |
| `src/hermes_plugins/commands_surveillance/` (5 files) | (varies) | Surveillance Discord commands |
| `src/hermes_plugins/commands_system/` (7 files) | (varies) | approve/approve_all/consent/deny/punishment/reward |

Source: Plan lines 635-637, Appendix D lines 1577-1598.

### 2.3 P22 Adapter Regression Tests (W18/W19 Must Run)

| Test | File | Lines | What It Proves |
|---|---|---|---|
| Adapter dispatch correctness | `tests/p22/test_adapters.py` | 2,739 | All 13 adapters dispatch L1-L3 correctly after M8 absorption |
| Action catalog completeness | `tests/p22/test_capability_matrix.py` | 401 | All ~108 unified actions available across 9 backends |
| Registry wiring | `tests/p22/test_registry.py` | 179 | ToolBackend registry discovers and registers all backends |
| Dry-run safety | `tests/p22/test_dry_run.py` | 367 | Dry-run mode still works (no real external calls) |
| Audit hash chain | `tests/p22/test_audit.py` + `test_audit_db_writer.py` + `test_audit_writer_production.py` | (varies) | UUID v7 + SHA256 hash chain intact after M8 rewrite |
| Project isolation | `tests/p22/test_project_isolation.py` | 138 | P19 project_id still scopes P22 adapter actions |
| Memory store/recall | `tests/p22/test_memory_store_fact.py` + `test_memory_re.py` + `test_memory_mark_dnr.py` + `test_memory_shim_wiring.py` | (varies) | Memory adapter actions survive M8 merge |
| Calendar/Drive/Notion dispatch | `tests/p22/test_calendar_dispatch.py` + `test_drive_dispatch.py` + `test_notion_dispatch.py` + `test_calendar_client.py` + `test_drive_client.py` + `test_notion_client.py` | (varies) | Simple tools in M9 (calendar/drive/notion) function correctly |
| GitHub dispatch | `tests/p22/test_github_dispatch.py` + `test_github_client_errors.py` + `test_github_client_shim.py` | (varies) | GitHub backend 21 actions work |
| Browser dispatch | `tests/p22/test_browser_dispatch.py` + `test_browser_client_shims.py` + `test_browser_re.py` | (varies) | Browser backend 10 actions work |
| Shims fail-closed | `tests/p22/test_shims.py` + `test_consent_shims_fail_closed.py` | (varies) | After consent removal, shims fail-closed gracefully |
| Finance dispatch | `tests/p22/test_finance_dispatch.py` + `test_finance_read_shim.py` | (varies) | Finance tool in M9 works |

**P22 test directory**: `tests/p22/` (63 files). Total P22 test lines in key files: ~4,529 lines across 7 core files.

### 2.4 Disposition: MODIFY-CREATE

M8 **REWRITES** P22 adapters into unified backends. The `ToolBackend` ABC replaces `BaseIntegrationAdapter`. Action dispatch logic must be functionally equivalent. The consent-gating code is **DELETED** (see section 5 below for conflict analysis).

**Regression criterion**: All P22 test assertions that do NOT test consent gating must pass after M8 rewrite. Tests that test consent gating must be rewritten to assert consent-free execution (M11 semantics).

---

## 3. (b) P20 Life Kernel M9 Ports -- Must Not Break Heartbeat/Sensors

### 3.1 What M9 Ports from P20

P20 Living Autonomy Kernel consists of 20 core files in `src/life_kernel/` (verified on disk):

**Core Runtime (14 files)**:
| File | Size | M9 Disposition |
|---|---|---|
| `heartbeat.py` | 30,678B | PORT to `guinevere/life_kernel/heartbeat.py` |
| `graph.py` | 42,838B | PORT (world model graph) |
| `state.py` | 11,177B | PORT (TypedDict schemas) |
| `cognition.py` | 19,318B | ABSORB into M3 consciousness loop substrates |
| `hermes_brain.py` | 17,200B | ABSORB into M3 consciousness loop |
| `checkpoint.py` | 6,104B | PORT (LangGraph checkpointer) |
| `decision_context.py` | 3,547B | PORT |
| `journal.py` | 2,189B | PORT (audit journal) |
| `models.py` | 3,868B | PORT (SQLAlchemy models) |
| `dashboard.py` | 15,165B | PORT |
| `dashboard_writer.py` | 10,973B | PORT |
| `discord_rest_client.py` | 10,613B | ABSORB into M13 Discord Gateway |
| `log_channel.py` | 6,143B | PORT |
| `redis_client.py` | 5,379B | PORT |
| `sensors.py` | 6,167B | PORT to `guinevere/life_kernel/sensors.py` |
| `metrics.py` | 2,088B | PORT to M16 surveillance |
| `p16_adapter.py` | 4,449B | PORT (KG adapter) |
| `p18_adapter.py` | 4,449B | PORT (spaced repetition adapter) |
| `self_improve.py` | 15,622B | ABSORB into M10 self-modification |
| `log_writer.py` | 4,992B | PORT |
| `session_graph.py` | 13,965B | PORT |

**Domain Minds** (5 files in `src/life_kernel/domain_minds/`):
| File | Disposition |
|---|---|
| `engineer_mind.py` | PORT |
| `finance_mind.py` | PORT (simple tool per A19) |
| `email_mind.py` | PORT |
| `deploy_backend.py` | PORT |
| `durability.py` | PORT |

**Sensor Adapters** (9 files in `src/life_kernel/sensor_adapters/`):
| File | Disposition |
|---|---|
| `base.py` | PORT |
| `browser_adapter.py` | MERGE into M8 |
| `discord_adapter.py` | MERGE into M13 |
| `finance_adapter.py` | MERGE into M9 finance_tool |
| `gmail_adapter.py` | MERGE into M8 email |
| `repo_adapter.py` | MERGE into M8 github |
| `surveillance_adapter.py` | MERGE into M16 |
| `vps_adapter.py` | MERGE into M8 vps |
| `wearable_adapter.py` | PORT |

Source: `src/life_kernel/` (26 files, verified via `ls`), plan lines 704-741 (M9 spec), convergence map `p24-p20-life-kernel-convergence-map.md`.

### 3.2 What M9 Deletes

| Deleted File | Lines | Purpose |
|---|---|---|
| `src/wearable/health_consent.py` | 326 | Consent check for wearable health data |

Source: Plan line 710. 4 files in `src/wearable/` import from `health_consent.py`:
- `src/wearable/writer.py:22` -- `from src.wearable.health_consent import check_metric_consent`
- `src/wearable/sync.py:16` -- `from src.wearable.health_consent import check_all_metrics_consent`
- `src/wearable/mood_integration.py:34` -- `from src.wearable.health_consent import check_wearable_consent`
- `src/wearable/alert_router.py:21` -- `from src.wearable.health_consent import check_metric_consent`

These 4 stale imports must be cleaned when M9 ports the wearable files.

### 3.3 Critical P20 Invariants (from convergence map)

Source: `p24-p20-life-kernel-convergence-map.md` lines 314-320.

| # | Invariant | M9/M3 Must Preserve |
|---|---|---|
| 1 | HARD STOP remains global halt | DELETED per ADR-062 (M2). Not preserved -- this is the paradigm shift. |
| 2 | Policy-gated autonomy (AGENTS.md 0.1) | MUST PRESERVE. M9 sensors/decisions must not introduce per-action approval. |
| 3 | Fail-soft Discord publishing | MUST PRESERVE. Heartbeat/dashboard must never block on Discord errors. |
| 4 | Graph write serialization via asyncio.Queue | MUST PRESERVE. No concurrent `graph.ainvoke`. |
| 5 | Recovery logic for stuck-HARD-STOP | DELETED (M2 removes HARD STOP). Recovery logic for NEW failure modes must be implemented. |
| 6 | Edit-not-spam dashboard pattern | MUST PRESERVE. Single message, edited in place. |
| 7 | Autonomous 24/7 runtime | MUST PRESERVE. Lifecycle hooks or external service must keep kernel alive. |

### 3.4 P20 Regression Tests (W18/W19 Must Run)

| Test | File | Lines | What It Proves |
|---|---|---|---|
| Heartbeat cycling | `tests/life_kernel/test_heartbeat.py` | 549 | All 6 intervals (1s/10s/30s/60s/5m/1h) cycle correctly |
| Heartbeat continuation | `tests/life_kernel/test_heartbeat_continuation.py` | (varies) | Heartbeat survives restart/reconnect |
| Cognition observers | `tests/life_kernel/test_cognition.py` | 527 | All 6 observer loops function (surveillance, memory, safety, curiosity, critic, anomaly) |
| HermesBrain reasoning | `tests/life_kernel/test_hermes_brain.py` | 360 | AIAgent wrapper produces reasoning output (now M3 consciousness) |
| Session graph | `tests/life_kernel/test_session_graph.py` | 347 | LangGraph StateGraph 4-node cycle works |
| World model | `tests/life_kernel/test_world_model.py` | 280 | Entity graph queries return correct state |
| Sensors | `tests/life_kernel/test_sensors.py` | 277 | Sensor registry polls and returns observations |
| Dashboard rendering | `tests/life_kernel/test_dashboard.py` | (varies) | Discord embed renders correctly |
| Decision context | `tests/life_kernel/test_decision_context.py` | (varies) | Context assembly for brain works |
| Journal audit | `tests/life_kernel/test_journal.py` | (varies) | Audit trail writes correctly |
| Soak test | `tests/life_kernel/test_soak.py` | 282 | Long-running stability (NRestarts=0) |
| P19 project recall | `tests/life_kernel/test_p19_recall_project_id.py` | 108 | project_id filters memory recall |
| Self-improve | `tests/life_kernel/test_self_improve.py` | (varies) | Self-improvement logic (now M10) |

**P20 test directory**: `tests/life_kernel/` (31 files). Total P20 test lines in key files: ~2,730 lines across 8 core files.

**P20 soak evidence**: PROGRESS.md line 50 confirms "P20 PASS WITH ACCEPTED RISK" with NRestarts=0 and operator-waived 24h soak.

### 3.5 Disposition: PORT

M9 **PORTS** P20 life kernel into `guinevere/life_kernel/`. The heart function, sensors, and world model are preserved. HermesBrain is absorbed into M3 consciousness (not duplicated). The `cognition.py` 6-observer pattern is absorbed into M3 substrates.

**Regression criterion**: Heartbeat must cycle at all 6 intervals. Sensors must produce observations. World model must query correctly. Graph write serialization must be preserved. Dashboard must edit-not-spam.

---

## 4. (c) P19 Project_id Namespace M1 Preserves

### 4.1 What P19 Deployed

P19-012 (production deploy 2026-06-27) added `project_id UUID` to 17 tables across 6 schemas:

**NOT NULL tables (11)**: memory.episodes, memory.semantic_facts, memory.procedural_skills, memory.session_summaries, memory.kg_entities, life_kernel.life_mind_state, life_kernel.domain_mind_state, life_kernel.heartbeat_record, projects.tasks, projects.loop_instances, projects.agent_tasks

**Nullable tables (6)**: audit.audit_trail, consent.consent_ledger, surveillance.events, memory.kg_edges, memory.kg_episodes, memory.kg_consent_audit

**Default project**: UUID `00000000-0000-0000-0000-000000000001` (slug=`default`, status=`active`)

**Feature flag**: `feature:projects:enabled` on Redis DB0/DB6

**Runtime activation**: 2026-06-27 15:31:10 WIB

Source: `p19-012-final-production-report.md` lines 34-53, `P19-ROUND2-FINAL-REPORT.md` lines 108-130.

### 4.2 Where project_id Flows

**Audit log**: `life_kernel.audit_journal` stores project_id in JSON payload (196/196 post-cutover rows verified). Source: P19-ROUND2-FINAL-REPORT.md lines 218-225.

**Memory**: `recall_memories()` accepts `project_id` parameter, filters by `project_id OR project_scope='global'`. Episodes model has `project_id` (line 160) and `project_scope` (line 163). Source: P19-ROUND2-FINAL-REPORT.md lines 131-139.

**Consent ledger**: `consent.consent_ledger` -- 7/7 rows backfilled with default project UUID. Source: P19-ROUND2-FINAL-REPORT.md lines 316-327.

**P19 code in `src/projects/`** (verified on disk):
- `registry.py` -- project registry (project CRUD)
- `memory_store.py` -- project-scoped memory operations
- `secrets_vault.py` -- project-scoped secrets
- `types.py` -- type definitions
- `exceptions.py` -- exception classes

### 4.3 How P24 M1 Preserves project_id

M1 creates `guinevere/config/models.py` with Pydantic config. The `agent_id` field per instance maps to the PG RLS `SET LOCAL` pattern. project_id flows through:

1. **Config**: Each instance YAML has `pg_agent_id` (UUID) -- this IS the project_id
2. **PG RLS**: `SET LOCAL app.agent_id = <uuid>` at connection time
3. **Memory**: PostgreSQL RLS enforces row-level isolation per agent_id
4. **Audit**: Audit trail rows tagged with agent_id

Source: Plan lines 342-373 (M1 spec), lines 136-141 (ADR-066, A14).

**CRITICAL DIFFERENCE**: P24 replaces per-table `project_id` columns with PostgreSQL RLS on `agent_id`. This means the 17 tables with `project_id` columns from P19-012 must either:
- (a) Keep the columns and use RLS + column for dual-layer isolation, OR
- (b) Drop the columns and rely solely on RLS

The plan does not explicitly state which approach. This is a **RISK** that needs clarification during M6 (Encrypted Memory) implementation.

### 4.4 P19 Regression Tests (W18/W19 Must Run)

| Test | File | Lines | What It Proves |
|---|---|---|---|
| Project registry CRUD | `tests/projects/test_registry.py` | 414 | Project create/read/update/delete works |
| Memory isolation | `tests/projects/test_memory_isolation.py` | 377 | Memory scoped to project, no cross-project leakage |
| Audit project_id | `tests/projects/test_audit_project_id.py` | 374 | Audit trail entries carry project_id |
| Consent isolation | `tests/projects/test_consent_isolation.py` | 589 | Consent records isolated per project |
| Dashboard isolation | `tests/projects/test_dashboard_isolation.py` | 181 | Dashboard shows project-scoped data |
| Project switcher | `tests/projects/test_project_switcher.py` | 255 | Discord /project switch works |
| Session isolation | `tests/projects/test_session_isolation.py` | 165 | Sessions scoped to project |
| Sensor isolation | `tests/projects/test_sensor_isolation.py` | 139 | Sensor data scoped to project |
| Secret isolation | `tests/projects/test_secret_isolation.py` | 175 | Secrets vault scoped to project |
| Migration compliance | `tests/projects/test_migration_p19_001.py` | 350 | DDL migration schema correct |
| Backfill | `tests/projects/test_backfill.py` | 184 | Backfill of default project UUID works |
| Agent loop project | `tests/projects/test_agent_loop_project.py` | 268 | Agent loop respects project scope |
| Finance project-aware | `tests/projects/test_finance_project_aware.py` | 265 | Finance tool respects project scope |
| Gmail project-aware | `tests/projects/test_gmail_project_aware.py` | 510 | Gmail adapter respects project scope |
| Wearable/XPoster aware | `tests/projects/test_wearable_xposter_project_aware.py` | 341 | Wearable and X poster respect project scope |
| KG isolation | `tests/projects/test_kg_isolation.py` | 283 | Knowledge graph isolated per project |
| Life kernel recall | `tests/life_kernel/test_p19_recall_project_id.py` | 108 | Recall pipeline filters by project_id |

**P19 test directory**: `tests/projects/` (17 files, ~4,871 lines) + `tests/life_kernel/test_p19_recall_project_id.py` (108 lines).

### 4.5 Disposition: MODIFY-CREATE

M1 **MODIFIES** how project_id is enforced (RLS instead of application-level filtering) but must **PRESERVE** the same observable behavior: memories, audit logs, consent records, and sensor data are isolated per project/agent.

**Regression criterion**: All project isolation tests must pass. Cross-project data leakage must be zero. Default project must be seeded. Audit trail must carry project_id (either column or JSON).

---

## 5. (d) Consent Gate CONFLICTS with P23/P24 v2.0

### 5.1 The Conflict

This is the most critical regression risk. The conflict is explicitly documented in the P22 brutal audit handoff (lines 65-69):

> **Consent Gate Conflict (CRITICAL)**
> - P22 has L2+ consent-gated, L4 never autonomous
> - P23 v2.0 (replanned): NO consent gate (execution-layer-only)
> - P24 v2.0 (replanned): NO consent gate (ADR-062 exempt)
> - When Hermes (P24, no consent) calls P23 executors, and P23 calls P22 adapters (which have consent gates), what happens?

**Resolution in P24 v3.0**: M11 strips ALL consent hooks. M8 deletes consent from all backends. The consent gate is removed at every layer.

Source: P22 brutal audit handoff `docs/setup-evidence/P22-brutal-audit-handoff.md` lines 65-69.

### 5.2 What P22.3's Consent Gate Does

P22 consent enforcement lives in `src/life_integrations/consent.py` (188 lines):

```python
class ConsentGate:
    """Wraps consent checking and HARD STOP checking into a single gate."""
    # L1 (read) passes without consent/HARD STOP check
    # L2+ requires consent check (fail-closed if no checker)
    # L4 is always blocked (never autonomous)
```

The `ActionRouter` (in `router.py`) enforces this at dispatch time:
```python
# (d) L2+ requires consent (fail-closed if no checker / not granted)
if consent_checker is None:
    # fail-closed: block L2+
    ...
```

Source: `src/life_integrations/consent.py` lines 1-7, `src/life_integrations/base.py` lines 100-179.

### 5.3 Files with Consent Gate References (Stale Import Risk)

**High-risk stale imports** (files that import from deleted consent modules):

| File | Import | Risk |
|---|---|---|
| `src/life_integrations/wiring.py:37` | `from src.life_integrations.consent import ConsentGate` | BREAKS when consent.py deleted |
| `src/life_integrations/router.py:22` | `from src.life_integrations.consent import ConsentGate` | BREAKS when consent.py deleted |
| `src/life_integrations/base.py:100-179` | Consent check logic inline | MUST REWRITE (remove consent branch) |
| `src/core/main.py:184` | `from src.life_integrations.consent_checker import P22ConsentChecker` | BREAKS when consent_checker.py deleted |
| `src/core/main.py:60` | `from src.life_integrations.audit_db_writer` | Depends on audit system (survives) |
| `src/core/api/routes.py:482,530` | `from src.life_integrations.consent_ledger_writer import ConsentLedgerWriter` | BREAKS when consent_ledger_writer.py deleted |
| `src/surveillance/__init__.py:12` | `from src.surveillance.consent_gate import ...` | BREAKS when consent_gate.py deleted |
| `src/surveillance/consumer.py:39` | `from src.surveillance.consent_gate import check_consent` | BREAKS |
| `src/surveillance/consent_gate.py` | (file itself) | DELETED in Appendix D |
| `src/gmail/consent_manager.py:32` | `from src.surveillance.consent_gate import ...` | BREAKS |
| `src/gmail/router.py:60` | `from src.surveillance.consent_gate import ConsentCheckResult` | BREAKS |
| `src/gmail/service.py:58` | `from src.surveillance.consent_gate import ConsentChecker` | BREAKS |
| `src/gmail/service.py:794` | `from src.surveillance.consent_gate import ...` | BREAKS |
| `src/discord/cmd_pc.py:234` | `from src.surveillance.consent_gate import check_consent` | BREAKS |
| `src/discord/cmd_surveillance_pause.py:116` | `from src.surveillance.consent_gate import ...` | BREAKS |
| `src/discord/cmd_surveillance_status.py:157` | `from src.surveillance.consent_gate import check_consent` | BREAKS |
| `src/hermes_plugins/commands_surveillance/surveillance_status.py:42,160` | `from src.surveillance.consent_gate import check_consent` | BREAKS |
| `src/hermes_plugins/commands_surveillance/surveillance_resume.py:51` | `from src.surveillance.consent_gate import check_consent` | BREAKS |
| `src/hermes_plugins/commands_surveillance/surveillance_pause.py:50,75` | `from src.surveillance.consent_gate import ...` | BREAKS |
| `src/consent/__init__.py:7` | `from src.consent.revocation_handler import ...` | Module itself DELETED |

**Total**: 20+ files have direct imports from modules being deleted.

### 5.4 M11 Deletion List (from plan)

| Deleted | Lines | Referenced By |
|---|---|---|
| `src/consent/__init__.py` | (init) | Self-references only |
| `src/consent/manager.py` | (part of 355) | Internal only |
| `hermes-config/hooks/consent_gate.py` | (varies) | Hook system |
| `src/life_integrations/consent.py` | 188 | wiring.py, router.py |
| `src/life_integrations/consent_checker.py` | 119 | main.py:184 |
| `src/life_integrations/consent_ledger_writer.py` | 518 | routes.py:482,530 |
| `src/surveillance/consent_gate.py` | (varies) | 15+ files across src/ |
| `src/wearable/health_consent.py` | 326 | 4 files in wearable/ |

Source: Plan lines 783-811 (M11 spec), Appendix D lines 1577-1598.

### 5.5 The Contract Mismatch

The P22-P23-P24 contracts document (`p22-p23-p24-contracts.md` lines 14-15) defines:

> P23 policy gate reuses P22 gate: classify->consent->hardstop->execute->audit
> Per-integration consent scopes: consent.{domain}.{integration}.{tier}

But P24 v3.0 plan says:
> NO consent gate. NO approval gate. NO risk-tier gating in backends. Hermes owns ALL decisions. (line 677)

This is a **direct contract violation**. The contracts document was written when P22.3 was the current state. P24 v3.0 supersedes these contracts. The old contract files must be marked as superseded.

### 5.6 Consent Gate Regression Tests (W18/W19 Must Run)

| Test | File | Lines | What It Proves |
|---|---|---|---|
| Consent checker wiring | `tests/p22/test_consent_checker_wiring.py` | (varies) | REWRITE: must prove consent is NO-OP (always allow) |
| Consent grant/revoke | `tests/p22/test_consent_grant_revoke.py` | 533 | DELETE or REWRITE: consent grant/revoke no longer applies |
| Consent hardstop | `tests/p22/test_consent_hardstop.py` | (varies) | DELETE: HARD STOP removed (M2) |
| Consent shims fail-closed | `tests/p22/test_consent_shims_fail_closed.py` | (varies) | REWRITE: must prove shims are no-ops, not fail-closed |
| Consent canonical | `tests/p22/test_consent_canonical.py` | (varies) | DELETE: consent canonical form no longer enforced |
| Surveillance consent gate | `tests/surveillance/test_consent_gate.py` | (varies) | DELETE: consent gate removed from surveillance |
| Consent isolation | `tests/projects/test_consent_isolation.py` | 589 | REWRITE: consent isolation replaced by RLS isolation |

**Forced verification command** (from plan line 1182-1183):
```bash
grep -rn "consent_gate\|consent_revocation\|consent_ref NOT NULL\|consent_checker\|consent_manager" guinevere/ agent/ tools/ run_agent.py
# Must exit 1 (zero matches) after M11 complete
```

### 5.7 Disposition: DELETE (with surgical cleanup)

M11 **DELETES** all consent modules. M8 **REWRITES** adapter dispatch to remove consent checks. The 20+ stale imports listed above must be cleaned in the same wave that deletes the consent modules (W3 for M11, W12 for M8).

**CRITICAL**: W3 (M11: No Consent Gate) and W12 (M8: Unified Tool Registry) must coordinate. M11 removes consent from the conversation loop and hooks. M8 removes consent from the adapter dispatch layer. If W3 runs before W12 (which it does -- W3 is in Group B, W12 is in Group D), then between W3 and W12, the P22 adapter code will have BROKEN consent imports. This is acceptable only if no integration test runs between W3 and W12 that exercises P22 adapter paths. The production system is NOT running during P24 (D2: local-runtime-only), so this is safe.

---

## 6. What Gets DELETED That Other Phases Still Reference (Stale Imports to Clean)

### 6.1 Complete Stale Import Inventory

| Deleted Module | Wave | Files That Import It | Count |
|---|---|---|---|
| `src/consent/` (entire package) | W3 | `src/consent/__init__.py` (self) | 1 |
| `src/surveillance/consent_gate.py` | W5 | `src/surveillance/__init__.py`, `src/surveillance/consumer.py`, `src/gmail/consent_manager.py`, `src/gmail/router.py`, `src/gmail/service.py` (x3), `src/discord/cmd_pc.py`, `src/discord/cmd_surveillance_pause.py`, `src/discord/cmd_surveillance_status.py`, `src/hermes_plugins/commands_surveillance/` (x4) | 15 |
| `src/life_integrations/consent.py` | W12 | `src/life_integrations/wiring.py`, `src/life_integrations/router.py` | 2 |
| `src/life_integrations/consent_checker.py` | W12 | `src/core/main.py` | 1 |
| `src/life_integrations/consent_ledger_writer.py` | W12 | `src/core/api/routes.py` (x2) | 2 |
| `src/wearable/health_consent.py` | W13 | `src/wearable/writer.py`, `src/wearable/sync.py`, `src/wearable/mood_integration.py`, `src/wearable/alert_router.py` | 4 |
| `src/loops/guardian.py` | W6 | `src/loops/__init__.py`, `src/loops/manager.py` | 2 |
| `src/persona/drift_corrector.py` | W11 | `src/persona/__init__.py` | 1 |
| `src/persona/drift_detector.py` | W11 | `src/persona/__init__.py` | 1 |
| `src/persona/streak_tracker.py` | W11 | `src/persona/__init__.py` | 1 |
| `src/persona/milestone_engine.py` | W11 | `src/persona/__init__.py` | 1 |
| `src/persona/safe_mode.py` | W11 | `src/discord/hermes_conversational.py` (x2), `src/persona/__init__.py` | 3 |
| `src/persona/mood_engine.py` | W7 | `src/discord/hermes_conversational.py`, `src/persona/__init__.py` | 2 |
| `src/persona/ritual_scheduler.py` | W11 | `src/discord/bot.py.bak.pre-phase2` (bak file), `src/persona/__init__.py` | 2 |

**Total stale imports requiring cleanup: ~37 import statements across ~30 files.**

### 6.2 Priority Ordering for Stale Import Cleanup

| Wave | Deletes | Stale Imports Cleaned |
|---|---|---|
| W1 | `_deprecated/`, `gamification/` | Self-contained, no live imports |
| W2 | `hard_stop_handler.py`, `safety_plugin.py` | `src/loops/manager.py` (hard_stop references) |
| W3 | `src/consent/`, `consent_gate.py` hooks | `surveillance/consumer.py`, `surveillance/__init__.py`, all `gmail/` consent refs, all `discord/cmd_*` consent refs, all `hermes_plugins/commands_surveillance/` consent refs |
| W5 | `src/surveillance/consent_gate.py`, `safe_mode.py` | 15 files listed in 6.1 above |
| W6 | `src/loops/guardian.py`, `safety_integration.py` | `src/loops/__init__.py`, `src/loops/manager.py` |
| W7 | `src/persona/safe_mode.py`, `mood_engine.py` (partial) | `src/discord/hermes_conversational.py` imports |
| W11 | `src/persona/` remaining files | `src/persona/__init__.py` (all drift/tracker imports) |
| W12 | `src/life_integrations/consent*.py` | `src/life_integrations/wiring.py`, `router.py`, `src/core/main.py`, `src/core/api/routes.py` |
| W13 | `src/wearable/health_consent.py` | `src/wearable/writer.py`, `sync.py`, `mood_integration.py`, `alert_router.py` |

**Risk**: If stale imports are NOT cleaned in the same wave as deletion, subsequent waves that exercise those code paths will get `ImportError`. Since P24 runs locally (D2: local-runtime-only), this does not affect production. But it WILL cause test failures in W18 integration tests if not cleaned.

---

## 7. Regression Test Matrix for W18/W19

### 7.1 P22 Adapter Regression (M8)

| Test Category | Test Command | Pass Criteria |
|---|---|---|
| Adapter dispatch | `pytest tests/p22/test_adapters.py -v` | All adapter action dispatch tests pass |
| Capability matrix | `pytest tests/p22/test_capability_matrix.py -v` | All ~108 actions available |
| Registry wiring | `pytest tests/p22/test_registry.py -v` | All 9 backends registered |
| Audit integrity | `pytest tests/p22/test_audit*.py -v` | Hash chain intact, UUID v7 correct |
| Dry-run | `pytest tests/p22/test_dry_run.py -v` | No real external calls |
| Memory operations | `pytest tests/p22/test_memory_*.py -v` | store/recall/dnr/fact all work |
| Consent removal | `grep -rn "consent_gate\|consent_checker\|consent_manager" guinevere/tools/` | Zero matches (exit 1) |
| L4 removal | `grep -rn "L4_FORBIDDEN\|PermissionTier.L4" guinevere/tools/` | Zero matches (exit 1) |

### 7.2 P20 Life Kernel Regression (M9)

| Test Category | Test Command | Pass Criteria |
|---|---|---|
| Heartbeat | `pytest tests/life_kernel/test_heartbeat.py -v` | All 6 intervals cycle |
| Cognition | `pytest tests/life_kernel/test_cognition.py -v` | All 6 observers function |
| Brain | `pytest tests/life_kernel/test_hermes_brain.py -v` | Reasoning produces output |
| Session graph | `pytest tests/life_kernel/test_session_graph.py -v` | 4-node cycle works |
| World model | `pytest tests/life_kernel/test_world_model.py -v` | Entity queries correct |
| Sensors | `pytest tests/life_kernel/test_sensors.py -v` | Observations produced |
| Dashboard | `pytest tests/life_kernel/test_dashboard.py -v` | Embed renders, edit-not-spam |
| Soak | `pytest tests/life_kernel/test_soak.py -v` | NRestarts=0 after soak period |
| Project recall | `pytest tests/life_kernel/test_p19_recall_project_id.py -v` | project_id filters recall |
| Graph serialization | `pytest tests/life_kernel/test_cognition.py -k "queue" -v` | asyncio.Queue prevents concurrent writes |

### 7.3 P19 Project_id Regression (M1)

| Test Category | Test Command | Pass Criteria |
|---|---|---|
| Registry CRUD | `pytest tests/projects/test_registry.py -v` | Project create/read/update/delete |
| Memory isolation | `pytest tests/projects/test_memory_isolation.py -v` | Zero cross-project leakage |
| Audit project_id | `pytest tests/projects/test_audit_project_id.py -v` | Audit entries carry project_id |
| Session isolation | `pytest tests/projects/test_session_isolation.py -v` | Sessions scoped to project |
| Sensor isolation | `pytest tests/projects/test_sensor_isolation.py -v` | Sensor data scoped to project |
| Secret isolation | `pytest tests/projects/test_secret_isolation.py -v` | Secrets scoped to project |
| KG isolation | `pytest tests/projects/test_kg_isolation.py -v` | Knowledge graph scoped to project |
| Migration | `pytest tests/projects/test_migration_p19_001.py -v` | DDL schema correct |
| Backfill | `pytest tests/projects/test_backfill.py -v` | Default project seeded |
| Dashboard isolation | `pytest tests/projects/test_dashboard_isolation.py -v` | Dashboard shows project-scoped data |
| Full project suite | `pytest tests/projects/ -v` | All 17 test files pass |

### 7.4 Consent Gate Removal Regression (M11)

| Test Category | Test Command | Pass Criteria |
|---|---|---|
| Consent code removed | `grep -rn "consent_gate\|consent_revocation\|consent_ref NOT NULL\|consent_checker\|consent_manager" guinevere/ agent/ tools/ run_agent.py` | Zero matches (exit 1) |
| HARD STOP removed | `grep -rn "hard_stop\|HARD_STOP\|HARD STOP\|safe_mode" guinevere/ agent/ tools/ run_agent.py` | Zero matches (exit 1) |
| Conversation loop clean | `grep -rn "consent" agent/conversation_loop.py` | Zero matches |
| Agent init clean | `grep -rn "consent" agent/agent_init.py` | Zero matches |
| Tool executor clean | `grep -rn "consent" agent/tool_executor.py` | Zero matches |
| Stale imports gone | `python -c "import guinevere"` | No ImportError from stale consent imports |
| Full import scan | `grep -rn "from src\.consent\|from src\.surveillance\.consent_gate\|from src\.life_integrations\.consent" src/` | Zero matches after all waves complete |

### 7.5 Cross-Phase Integration Regression (W18)

| Test | What It Proves |
|---|---|
| `pytest tests/ -v --tb=short` (full suite) | No import errors, no regressions across all test directories |
| `hermes-agent --dry-run --config config/guinevere.yaml` | Both instances boot without errors |
| Forbidden pattern scan | `grep -rn "consent_gate\|hard_stop\|safe_mode\|L4_FORBIDDEN" guinevere/ agent/ tools/` returns zero |
| `src/` emptiness check | `ls src/*.py 2>/dev/null \| wc -l` returns 0 |
| Module import check | All 17 modules importable: `python -c "from guinevere.config import ...; from guinevere.consciousness import ...; ..."` |

---

## 8. Risks Summary

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R-01 | P22 adapter logic lost in M8 rewrite | HIGH | Side-by-side test comparison: P22 tests pass against M8 backends |
| R-02 | P20 heartbeat timing drift after M9 port | MEDIUM | Soak test with timing assertions (1s/10s/30s/60s/5m/1h intervals) |
| R-03 | P19 project_id lost when switching to RLS | HIGH | Dual-layer verification: RLS + project_id column both enforced |
| R-04 | 37 stale imports cause ImportError cascade | HIGH | Wave-by-wave stale import cleanup (section 6.2 ordering) |
| R-05 | Consent removal creates security gap (no fail-closed) | MEDIUM | This is INTENDED per ADR-062. Verify with `grep` that consent code is gone. |
| R-06 | P22-P23-P24 contracts document stale | LOW | Mark contracts doc as SUPERSEDED by P24 v3.0 plan |
| R-07 | Graph write serialization lost in M3/M9 port | HIGH | Preserve asyncio.Queue pattern in consciousness loop |
| R-08 | Dashboard edit-not-spam pattern broken | MEDIUM | Single-message editing test must pass |
| R-09 | Wearable health_consent removal breaks 4 files | MEDIUM | M13 wave must clean wearable imports simultaneously |
| R-10 | Gmail consent_manager removal breaks service.py | MEDIUM | M8 email backend must absorb gmail without consent refs |

---

## 9. Verdict

**DISPOSITION**: All four regression domains are addressable within the P24 v3.0 plan structure. The key risk is the consent gate deletion (domain d) which creates 37 stale imports across 30 files. The wave ordering (W3 deletes consent hooks before W12 deletes adapter consent) creates a temporary broken-import state between waves, but this is safe under D2 (local-runtime-only, no production impact).

**REGRESSION TEST SUITE**: W18 must run all tests listed in section 7 (1-4) before W19 soak. W19 soak must run the full test suite plus forbidden pattern scans plus `src/` emptiness check.

**UNRESOLVED QUESTION**: P19 project_id column vs PG RLS approach is not explicitly addressed in the P24 v3.0 plan. M6 (Encrypted Memory) and M9 (Life Kernel) must clarify whether project_id columns are kept alongside RLS or dropped in favor of RLS-only isolation.

---

## 10. Evidence Sources

| Source | Path | Key Lines |
|---|---|---|
| P24 v3.0 Plan | `docs/setup-evidence/P24/plan/p24-hermes-native-fork-enterprise-plan.md` | 631-700 (M8), 704-741 (M9), 783-811 (M11), 1577-1598 (Appendix D) |
| P24 v3.0 Replan Report | `docs/setup-evidence/P24/evidence/p24-v3-replan-final-report.md` | 1-145 |
| Forward Compatibility Map | `docs/setup-evidence/P24/research/p24-p19-p21-p22-p23-forward-compatibility-map.md` | 1-1010 |
| P20 Life Kernel Convergence | `docs/setup-evidence/P24/research/p24-p20-life-kernel-convergence-map.md` | 1-430 |
| P22 Brutal Audit Handoff | `docs/setup-evidence/P22-brutal-audit-handoff.md` | 65-69 (consent conflict) |
| P22-P23-P24 Contracts | `docs/setup-evidence/P22/implementation/plan/p22-p23-p24-contracts.md` | 1-59 |
| P19-012 Production Report | `docs/setup-evidence/P19/evidence/production-deploy/p19-012-final-production-report.md` | 1-60 |
| P19 Round-2 Final Report | `docs/setup-evidence/P19/evidence/completion-round-2/P19-ROUND2-FINAL-REPORT.md` | 1-390 |
| PROGRESS.md | `PROGRESS.md` | 49-54 (P19/P20/P22 status) |
| Source: `src/life_integrations/consent.py` | `src/life_integrations/consent.py` | 1-7 (consent gate docstring) |
| Source: `src/life_integrations/consent_checker.py` | `src/life_integrations/consent_checker.py` | 1-18 (fail-closed design) |
| Source: `src/life_integrations/base.py` | `src/life_integrations/base.py` | 100-179 (consent check in dispatch) |
| Wave Structure Audit | `docs/setup-evidence/P24/evidence/audits/round-5/auditor-04-wave-structure.md` | 1-506 |

---

**Generated**: 2026-06-29
**Method**: Read 8 documentation files, 6 source files, grep-scanned 30+ source/test files, verified directory contents via `ls`, counted test lines via `wc -l`.

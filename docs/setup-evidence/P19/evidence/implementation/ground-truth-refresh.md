# P19 Ground-Truth Refresh

**Date:** 2026-06-25  
**Label:** pre-implementation verification

## Summary Verdict

**READY** (with caveats) — 81 EXISTS, 7 MISSING, 1 SYMBOL_MISSING

## Findings Table

| Item | Status | Finding |
|------|--------|---------|
| state.py LifeMindState | EXISTS | src/life_kernel/state.py line 100: class LifeMindState with 33 fields (observations, decision_context, current_phase, is_active, last_heartbeat, goals, commitments, concerns, current_focus NotRequired, hard_stop_requested, session_count, audit_entries, decision NotRequired, act_count, cycle_count, errors, kg_adapter NotRequired, memory_adapter NotRequired, last_autonomous_decision NotRequired, last_action_result NotRequired, next_planned_action NotRequired, memory_status NotRequired, uptime_start NotRequired, journal_entries, recalled_concepts NotRequired, recalled_memories NotRequired, world_model_status NotRequired) |
| state.py SessionState | EXISTS | src/life_kernel/state.py line 264: class SessionState with fields session_id, sdlc_phase, pending_tasks, completed_tasks, context, memory_refs |
| heartbeat.py thread_id assignments | EXISTS | src/life_kernel/heartbeat.py has 6 unconditional assignments of thread_id = "heartbeat" at lines 302, 341, 365, 446, 465, 629 (no other thread_id values appear) |
| graph.py _ADAPTERS | EXISTS | src/life_kernel/graph.py line 33 declares _ADAPTERS: dict[str, Any] = {"kg": None, "memory": None, "journal": None} — a global mutable dict |
| cognition.py BackgroundCognition | EXISTS | src/life_kernel/cognition.py line 27: class BackgroundCognition exists |
| dashboard_writer.py | EXISTS | src/life_kernel/dashboard_writer.py exists |
| dashboard.py | EXISTS | src/life_kernel/dashboard.py exists |
| log_channel.py | EXISTS | src/life_kernel/log_channel.py exists |
| redis_client.py | EXISTS | src/life_kernel/redis_client.py exists |
| session_graph.py | EXISTS | src/life_kernel/session_graph.py exists |
| self_improve.py | EXISTS | src/life_kernel/self_improve.py exists |
| hermes_brain.py | EXISTS | src/life_kernel/hermes_brain.py exists |
| sensors.py | EXISTS | src/life_kernel/sensors.py exists |
| p16_adapter.py | EXISTS | src/life_kernel/p16_adapter.py exists |
| p18_adapter.py | EXISTS | src/life_kernel/p18_adapter.py exists |
| sensor_adapters/ directory | EXISTS | src/life_kernel/sensor_adapters/ directory exists with 10 files: __init__.py, base.py, browser_adapter.py, discord_adapter.py, finance_adapter.py, gmail_adapter.py, repo_adapter.py, surveillance_adapter.py, vps_adapter.py, wearable_adapter.py |
| domain_minds/durability.py | EXISTS | src/life_kernel/domain_minds/durability.py exists |
| src/core/main.py | EXISTS | File at src/core/main.py; contains `async def lifespan(app: FastAPI)` at line 60 and `life_kernel_startup_failed` at line 413 |
| src/core/services/hard_stop_handler.py | EXISTS | File exists; class HardStopHandler at line 34; method is_safe at line 63 |
| src/projects/ directory | MISSING | Directory does NOT exist at src/projects/ (expected per plan) |
| src/hermes/_memory_bridge.py | EXISTS | File exists; recall_for_context at line 93; store_conversation at line 216; KGQueryEngine imported at line 161 and instantiated at line 163 |
| src/knowledge_graph/query/context.py | EXISTS | class RecallContextAssembler at line 141; method assemble at line 195 |
| src/knowledge_graph/query/engine.py | EXISTS | class KGQueryEngine at line 229; method search_entities at line 848 |
| src/knowledge_graph/query/rrf_fusion.py | EXISTS | File at src/knowledge_graph/query/rrf_fusion.py (19461 bytes) |
| src/knowledge_graph/query/ppr.py | EXISTS | File at src/knowledge_graph/query/ppr.py (22908 bytes) |
| src/knowledge_graph/recall.py | MISSING | File does NOT exist at src/knowledge_graph/recall.py (confirmed absent per plan P19-000 fix 2 — deliberately deleted) |
| src/loops/context.py LoopContext | EXISTS | class LoopContext at line 57 and class LoopContextBuilder at line 163 |
| src/loops/state_store.py | EXISTS | File at src/loops/state_store.py (14952 bytes) |
| src/loops/prompts.py | EXISTS | File at src/loops/prompts.py (17062 bytes) |
| src/loops/audit_writer.py | EXISTS | File at src/loops/audit_writer.py (5539 bytes) |
| src/discord/hermes_conversational.py _process_and_respond | EXISTS | src/discord/hermes_conversational.py line 427: async def _process_and_respond() exists |
| src/discord/hermes_conversational.py _process_turn_core | SYMBOL_MISSING | src/discord/hermes_conversational.py: no def _process_turn_core found anywhere in file |
| src/discord/_command_registry.py | EXISTS | File exists; commands registered via COMMAND_SPECS tuple of CommandSpec dataclass instances with to_payload() -> Discord REST payloads, validated by require_canonical_registry() expecting exactly 49 commands |
| src/discord/cmd_project.py | MISSING | File does not exist on disk (confirmed missing as planned for P19-007) |
| src/discord/cmd_consent.py | EXISTS | File exists |
| src/surveillance/consent_gate.py check_consent | EXISTS | src/surveillance/consent_gate.py line 182: async def check_consent(scope: str) -> ConsentCheckResult exists (also a class method at line 109) |
| src/surveillance/consent_gate.py VALID_SURVEILLANCE_SCOPES | EXISTS | src/surveillance/consent_gate.py line 51: VALID_SURVEILLANCE_SCOPES: frozenset[str] = frozenset({...}) exists |
| src/surveillance/consumer.py | EXISTS | File exists |
| src/surveillance/models.py | EXISTS | File exists |
| src/gmail/consent_manager.py | EXISTS | File exists |
| src/gmail/consent_manager.py EMAIL_CONSENT_SCOPE | EXISTS | src/gmail/consent_manager.py line 43: EMAIL_CONSENT_SCOPE: str = "surveillance.email" exists |
| src/gmail/router.py | EXISTS | File exists |
| src/gmail/metrics.py | EXISTS | File exists |
| src/wearable/health_consent.py | EXISTS | File exists |
| src/wearable/metrics.py | EXISTS | File exists |
| src/x_poster/config.py | EXISTS | File exists |
| src/x_poster/metrics.py | EXISTS | File exists |
| src/finance/plugin.py | EXISTS | File exists |
| migrations financial.transactions + project_id | MISSING | No migration entries reference 'financial.transactions' table, and no project_id column found in any financial.transactions context |
| src/loops/audit_writer.py (discord batch) | EXISTS | File at src/loops/audit_writer.py exists |
| alembic/env.py — multi-schema support | EXISTS | alembic/env.py exists, defines GUINEVERE_SCHEMAS frozenset (13 schemas), uses include_schemas=True, include_name filter, and version_table_schema='ops' |
| alembic/versions/ — all .py files | EXISTS | 12 .py migration files found; current alembic head is p20_001_life_kernel_schema |
| ADR highest number | EXISTS | Highest ADR file is ADR-050 (ADR-050-knowledge-graph-architecture.md); no ADR-051 or ADR-052 files on disk |
| ADR-039/050/051/052 in ADR index | EXISTS | docs/10-governance/17-ADR_Index_v1.0.md mentions ADR-039 (line 127 backlog), ADR-050 (line 104 implemented), ADR-051 (lines 138-139 backlog). ADR-052 is NOT mentioned. |
| tests/life_kernel/ — test files | EXISTS | 25 .py files present including test_hermes_brain.py, test_world_model.py, test_heartbeat.py etc. |
| tests/projects/ — planned NEW directory | MISSING | tests/projects/ does not exist; confirms planned NEW directory not yet created |
| secrets/projects/ — planned NEW directory | MISSING | secrets/projects/ does not exist; confirms planned NEW directory not yet created |
| Local DB reachability — DATABASE_URL references | EXISTS | .env.example defines DATABASE_URL via port 5433; alembic.ini has sqlalchemy.url pointing to localhost:5433; multiple .env files reference POSTGRES_PORT=5433 |
| Local DB port 5433 probe | MISSING | TCP connect to 127.0.0.1:5433 returned err=10061 (connection refused) — PostgreSQL not reachable |
| Local DB port 6380 probe | MISSING | TCP connect to 127.0.0.1:6380 returned err=10061 (connection refused) — Redis not reachable |
| Pytest collection — test_memory_bridge + test_consent_gate | EXISTS | pytest --collect-only on both files succeeded with 71 tests collected in 0.74s |
| monitoring/grafana/dashboards — agent-loop.json | EXISTS | guinevere-agent-loop.json is present in the dashboards directory |
| monitoring/grafana/dashboards — guinevere-p19-projects.json | MISSING | guinevere-p19-projects.json is NOT present in the dashboards directory |

## Gaps vs Plan

### Items MISSING (planned NEW, OK)

These are expected to be absent because the plan calls for creating them from scratch. They do **not** block implementation.

- **src/projects/ directory** — planned NEW directory; wave 001 creates it.
- **tests/projects/** — planned NEW directory; wave 001 creates it alongside the source.
- **secrets/projects/** — planned NEW directory; wave 001 or 012 creates it.
- **src/discord/cmd_project.py** — planned NEW file for P19-007; wave 003 creates it.
- **src/knowledge_graph/recall.py** — deliberately deleted per plan P19-000 fix 2; P19-related recall moves into the new projects namespace. Expected absent.
- **monitoring/grafana/dashboards/guinevere-p19-projects.json** — planned NEW dashboard; wave 011 creates it.
- **migrations financial.transactions + project_id** — planned NEW migration; wave 002 or later creates this.

### Items MISSING (unexpected, BLOCKER if reachability needed)

- **Local DB port 5433 probe** — PostgreSQL not reachable. If wave 002 (P19-003 alembic upgrade) or any wave requiring runtime DB access is attempted, this is a **BLOCKER**. The migration step needs a live PostgreSQL on port 5433.
- **Local DB port 6380 probe** — Redis not reachable. Not an immediate blocker for most waves, but waves touching memory/state persistence (004, 005, 012) will need it.

### Items SYMBOL_MISSING (unexpected, potential BLOCKER)

- **src/discord/hermes_conversational.py _process_turn_core** — the plan references `_process_turn_core` as a symbol; it does not exist in the file. The existing `_process_and_respond` at line 427 may serve as the integration point, but an implementer **must** verify the call chain and either confirm the symbol is no longer needed or create it. Until this is resolved, this is a **potential BLOCKER** for waves that touch the conversational handler (waves 004-005).

## DB / Redis / Pytest Reachability

| Resource | Status | Detail |
|----------|--------|--------|
| PostgreSQL (127.0.0.1:5433) | **DOWN** | TCP connect returned err=10061 (connection refused). Alembic upgrade (P19-003) **requires** a live PostgreSQL instance. Cannot proceed with migrations. |
| Redis (127.0.0.1:6380) | **DOWN** | TCP connect returned err=10061 (connection refused). Wave 004/005 (heartbeat, memory, state persistence) will need this. |
| Pytest baseline (test_memory_bridge + test_consent_gate) | **PASS** | `pytest --collect-only` collected 71 tests in 0.74s. The test suite is intact and can be discovered. |

**Bottom line:** Local DB is **down**. The 71-test baseline **collects** successfully. Any implementer running `alembic upgrade head` must first start the local PostgreSQL instance.

## Implications for Waves

| Wave | Description | Status | Notes |
|------|-------------|--------|-------|
| 001 | NEW: src/projects/ namespace, base models, p19_projects schema | **UNBLOCKED** | Creates new files; no dependency on locked modules or local DB. Ready for implementation. |
| 002 | NEW: ProjectService, P19-003 alembic upgrade | **BLOCKED by DB** | Alembic upgrade needs live PostgreSQL on port 5433. Start DB first. |
| 003 | NEW: cmd_project.py, consent scopes, project sync | **UNBLOCKED** (from a code perspective) | Completely new files. DB needed only if runtime-tested locally. |
| 004 | MODIFY: p16_adapter.py, p18_adapter.py — wire namespace | **POTENTIALLY BLOCKED** | Touches LOCKED files (p16_adapter, p18_adapter). Requires **P20 fresh preflight** before modification. Also needs Redis if runtime-tested. |
| 005 | MODIFY: heartbeat.py, graph.py, cognition.py, dashboard_writer.py — project_id propagation | **POTENTIALLY BLOCKED** | Touches LOCKED files. Requires **P20 fresh preflight**. Also needs both DB and Redis for runtime testing. |
| 006 | NEW: project lifecycle tests | **UNBLOCKED** | New test files; mock-based. No live infra needed. |
| 007 | NEW: consent/project admin commands | **UNBLOCKED** | New command module; no locked code changes. |
| 008 | NEW: metrics/telemetry for projects | **UNBLOCKED** | New code. |
| 009 | NEW: audit integration for projects | **UNBLOCKED** | New code. |
| 010 | NEW: documentation (ADR-051, ADR-052) | **UNBLOCKED** | Docs only. |
| 011 | NEW: Grafana dashboard guinevere-p19-projects.json | **UNBLOCKED** | Dashboard JSON file; no code changes. |
| 012 | MODIFY: deploy configs, secrets, CI | **POTENTIALLY BLOCKED** | Touches live deploy configuration. Requires **P20 fresh preflight** and DB/Redis for smoke tests. |

### Legend

- **UNBLOCKED** — Can be implemented immediately with no infra or preflight dependency.
- **BLOCKED by DB** — Requires PostgreSQL on port 5433 before code can be exercised or migrations run.
- **POTENTIALLY BLOCKED** — Requires P20 fresh preflight before modifying LOCKED files, and/or local infra for testing.

## Footer

| Metadata | Value |
|----------|-------|
| Generated | 2026-06-25 |
| Generated by | P19 scout synthesis agent |
| Source | 4 scout batches (life_kernel, core_hermes_kg_loops, discord_surveillance_adapters, infra_migrations_tests_db) |
| Total individual checks | 89 |
| EXISTS | 81 |
| MISSING | 7 |
| SYMBOL_MISSING | 1 |

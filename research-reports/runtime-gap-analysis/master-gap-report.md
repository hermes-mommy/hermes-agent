# Guinevere — Master Runtime Gap Report

> **Generated**: 2026-06-03 | **Session**: Runtime Gap Closure | **Status**: RESEARCH COMPLETE

## 1. Executive Summary

| Severity | Count | Scope |
|---|---|---|
| CRITICAL | 6 | Core architecture broken — loops, MCP bridge, sub-agents, rituals |
| HIGH | 7 | Services not wired — consumer, costs, auth, stubs, startup |
| MEDIUM | 4 | Features incomplete — monitoring, embeddings, tool selector |
| **TOTAL** | **17 gaps** | **46 deferred items cataloged** |

**VPS State**: 3/8 services running (9router, core, discord). 5 services dead (broken env vars). No monitoring containers. Bot online but degraded (no memory recall, no ritual delivery).

---

## 2. Gap Catalog

### CRITICAL (6)

| ID | Area | Description | Files | Impact |
|---|---|---|---|---|
| GAP-02 | Loops→LLM | All 7 loop phases return static templates; zero LLM calls | `src/loops/phases/*.py`, `manager.py` | Autonomous loop is a template generator |
| GAP-08 | Loops↔MCP | Zero imports between loops and MCP modules | `src/loops/`, `src/mcp/` | Complete architectural isolation |
| GAP-14 | Sub-agents | SubAgentSpawner creates dict records only; no LLM execution | `src/loops/sub_agent.py` | Sub-agent spawning is non-functional |
| GAP-01 | Discord→MCP | Conversational handler cannot invoke MCP tools | `src/discord/conversational_handler.py` | Chat cannot use tools |
| GAP-03 | Persona→Discord | Ritual scheduler logs locally; never sends to Discord | `src/persona/ritual_scheduler.py` | Daily rituals invisible to user |
| GAP-15 | Evidence | Cross-phase data flow broken — phases don't read prior artifacts | `src/loops/manager.py`, `phases/*.py` | No inter-phase context |

### HIGH (7)

| ID | Area | Description | Files | Impact |
|---|---|---|---|---|
| GAP-05 | Surveillance | Consumer not started by main.py; events pile up in Redis DB2 | `src/surveillance/consumer.py`, `src/core/main.py` | Ingestion pipeline broken |
| GAP-06 | Loop Costs | LoopCostTracker defined but never wired to loop execution | `src/loops/cost.py`, `src/loops/manager.py` | No per-loop cost visibility |
| GAP-07 | MCP Auth | AUTH_MATRIX registry not enforced at runtime | `src/mcp/auth_matrix.py`, `tools/*.py` | Security governance gap |
| GAP-10 | App Startup | 3 core services need manual startup; no orchestration | `src/core/main.py` | Fragile operations |
| GAP-11 | Discord Cmds | 20/33 slash commands are stubs (61%) | `src/discord/bot.py` | Degraded operator experience |
| VPS-01 | Service Env | 5 services have broken `%E/REDIS_PASSWORD` refs | `systemd/*.service` | Services crash on start |
| VPS-02 | Monitoring | compose.monitoring.yml exists but .env missing; service disabled | `monitoring/`, `systemd/guinevere-monitoring.service` | No observability stack |

### MEDIUM (4)

| ID | Area | Description | Files | Impact |
|---|---|---|---|---|
| GAP-04 | Embeddings | API key requires manual env setup; not auto-configured | `src/memory/embeddings.py` | Memory recall degraded |
| GAP-09 | Global Costs | CostTracker not called from loop phases | `src/core/services/cost_tracker.py` | Incomplete cost coverage |
| GAP-13 | Monitoring | No Prometheus /metrics endpoint in core app | `src/core/main.py` | No application metrics |
| GAP-16 | Tool Selector | ToolSelector exists but never called | `src/mcp/tool_selector.py` | Unused optimization |

---

## 3. VPS Service Status

| Service | Status | PID | Issue |
|---|---|---|---|
| guinevere-9router | ✅ active | 627184 | — |
| guinevere-core | ✅ active | 1764478 | No EnvironmentFile |
| guinevere-discord | ✅ active | 1778801 | — |
| guinevere-loops | ❌ dead | — | Broken `%E/REDIS_PASSWORD` |
| guinevere-mcp | ❌ dead | — | Broken `%E/REDIS_PASSWORD` |
| guinevere-scheduler | ❌ dead | — | Broken `%E/REDIS_PASSWORD` |
| guinevere-surveillance | ❌ dead | — | Broken `%E/REDIS_PASSWORD` + `%E/GUINEVERE_DB_PASSWORD` |
| guinevere-obscura | ❌ dead | — | Binary `/usr/local/bin/obscura` not installed |
| guinevere-monitoring | ❌ dead | — | Wrong WorkingDirectory + no .env |

---

## 4. Deferred Items Summary (46 items)

| Category | Count | Blocking |
|---|---|---|
| Stub Discord commands | 20 | 20 |
| Loop phase templates | 7 | 7 |
| Surveillance gather stubs | 3 | 3 |
| LLM evaluation stub | 1 | 0 |
| LQS placeholder weights | 1 | 0 |
| Discord embed degraded placeholders | 15 | 0 |
| Protocol contracts (intentional) | 4 | 0 |
| Intentional `pass` (CancelledError) | 6 | 0 |

---

## 5. Scope Classification for Implementation

### Batch A — Service Infrastructure Fixes (QUICK, parallel)
1. **VPS-01**: Fix ALL service env vars — create per-service .env files with SOPS-decrypted values
2. **VPS-02**: Create monitoring/.env, fix WorkingDirectory, docker compose up
3. **GAP-04**: Set GUINEVERE_9ROUTER_API_KEY in .env.discord + .env.core

### Batch B — Wiring Fixes (MEDIUM, parallel)
4. **GAP-05**: Wire SurveillanceConsumer into main.py lifespan as background task
5. **GAP-03**: Wire RitualScheduler into bot.py with Discord channel callback
6. **GAP-06**: Wire LoopCostTracker into loop manager
7. **GAP-13**: Add Prometheus /metrics endpoint to core app

### Batch C — Security + Quality (MEDIUM, parallel)
8. **GAP-07+12**: AUTH_MATRIX runtime enforcement — modify require_approval decorator
9. **GAP-10**: Add Prometheus metrics export + health aggregation to main.py

### Batch D — Discord Stubs (LARGE, sequential per module)
10. **GAP-11a**: Wire memory commands (memory-forget, memory-export) — Phase 3
11. **GAP-11b**: Wire finance command (cost-alert) — Phase 4
12. **GAP-11c**: Wire system commands (approve, deny, approve-all, focus, casual, consent, punishment, reward) — Phase 4
13. **GAP-11d**: Wire admin commands (restart-service, backup-now, health-check, clear-cache) — Phase 4
14. **GAP-11e**: Wire loop commands (loop-pause, loop-resume, loops, evidence, loop-priority) — Phase 5

### Batch E — Architecture (LARGE, sequential)
15. **GAP-02+08+14+15**: Loop LLM integration + MCP bridge + sub-agent execution + cross-phase flow
16. **GAP-01+16**: Conversational handler MCP tool-use + ToolSelector wiring

### DEFERRED (requires live subsystems)
- Degraded embed placeholders (15 items) — require P3/P4/P5 subsystems live on VPS
- Surveillance gather functions (3 items) — require surveillance consumer running
- LLM evaluation in transition_rules — rule-based fallback acceptable for now

---

## 6. Binding Decisions

| Decision | Value | Rationale |
|---|---|---|
| Service env approach | Per-service .env files (not %E/ systemd specifiers) | SOPS-decrypted values, testable, portable |
| Monitoring compose | Use existing compose.monitoring.yml | Already verified in P8 |
| Ritual delivery | Discord webhook to #guinevere-chat | Matches SystemPromptMaster §G |
| AUTH_MATRIX enforcement | Modify decorator to call get_auth_level() | Single source of truth |
| Loop LLM integration | DEFER — too large for single session | Requires new architecture |
| MCP tool bridge | DEFER — requires loop LLM first | Dependency chain |
| Prometheus endpoint | prometheus-client FastAPI middleware | Already in pyproject.toml |

---

## 7. Evidence Paths

| Artifact | Path |
|---|---|
| This report | `research-reports/runtime-gap-analysis/master-gap-report.md` |
| Planner output (pending) | `docs/setup-evidence/runtime-gaps/batch-plan-runtime-gaps.md` |
| Per-step evidence | `docs/setup-evidence/runtime-gaps/STEP-RG-{NNN}/` |

---

## 8. Footer

Generated from: bg_8515bb2a (integration gaps, 6m10s) + bg_bced7dc0 (TODOs/stubs, 6m15s) + direct VPS SSH inspection + source code reads.

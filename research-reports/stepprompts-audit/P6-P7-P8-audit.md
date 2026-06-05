# Phase 6, Phase 7, Phase 8 — StepPrompts.md Audit (ADR-035 Impact Analysis)

**Date:** 2026-06-04  
**Audited against:** [`adr/ADR-035-hermes-migration.md`](../../adr/ADR-035-hermes-migration.md) (Accepted)  
**Scope:** `stepprompts/StepPrompts.md` lines 7061–7610 (P6, P7, P8)  
**Status codes:** `VALID` · `STALE` · `NEEDS-UPDATE` · `OBSOLETE`

---

## Executive Summary

| Phase | Steps | VALID | NEEDS-UPDATE | OBSOLETE | Overall Verdict |
|---|---|---|---|---|---|
| **P6 (MCP Tools)** | 21 | 7 (33%) | 10 (48%) | 4 (19%) | 🔴 **NEEDS MAJOR REWORK** |
| **P7 (Surveillance)** | 22 + P7-NEW | 20 (87%) | 3 (13%) | 0 (0%) | 🟡 **NEEDS MINOR UPDATE** |
| **P8 (Observability)** | 23 | 20 (87%) | 3 (13%) | 0 (0%) | 🟡 **NEEDS MINOR UPDATE** |

ADR-035 (Hermes NousResearch Migration, Pillar 4: MCP = HYBRID) fundamentally restructures the MCP tool layer. P6 was built on the assumption of 16 fully custom MCP tools running on a standalone FastMCP server. ADR-035 replaces this with: 6 tools migrating to Hermes native, 3 becoming hybrid (Hermes native + custom overlay), 7 remaining custom. The auth matrix moves from a custom decorator to a Hermes auth overlay plugin. P7 and P8 are largely unaffected except for Discord commands that must become Hermes plugins.

---

## P6 (MCP Tools) — Per-Step Audit

### MCP Hybrid Impact Analysis (ADR-035 Pillar 4)

ADR-035 reorganizes all 16 MCP tools into three categories:

| Category | Count | Tools |
|---|---|---|
| **MIGRATE** → Hermes native | 6 | brave_search, exa_search, fetch, websearch, filesystem, git_tool |
| **HYBRID** → Hermes native + custom overlay | 3 | shell_tool, docker_tool, github |
| **CUSTOM** → Keep as-is (no Hermes equivalent) | 7 | context7, grep_app, obscura_cdp, sequential_thinking, time_tools, postgres_tool, redis_tool |

Hermes consolidates 4 web search tools (brave_search, exa_search, fetch, websearch) into 1 native `web` toolset. The 4-level auth matrix moves to a `pre_tool_call` hook plugin. Budget enforcement moves from custom `src/mcp/budget.py` to the auth overlay plugin.

**Kitchen-sink impact:** 9 of 16 tools change implementation surface. The `src/mcp/manager.py` FastMCP server must either (a) be retired and replaced by Hermes native MCP client + auth overlay, or (b) be downsized to serve only the 7 custom tools.

---

### P6-001 to P6-017: Tool Setup Steps

| Step | Tool | ADR-035 Category | Verdict | Reasoning |
|---|---|---|---|---|
| **P6-001** | `guinevere-mcp.service` | Retired / downsized | **NEEDS-UPDATE** | FastMCP server `src/mcp/manager.py` runs all 16 tools. Under ADR-035, Hermes native MCP client handles 9 tools (migrate + hybrid). The custom MCP service must be downsized to serve only 7 tools or retired entirely. Auth matrix decorators move to Hermes plugin. The systemd service or its replacement must exist for the 7 custom tools. |
| **P6-002** | `brave_search` | MIGRATE → Hermes `web` toolset | **OBSOLETE** | Custom `src/mcp/tools/brave_search.py` replaced by Hermes native web search. The `BRAVE_API_KEY` SOPS-encrypted credential is still needed but configured in Hermes, not in custom code. |
| **P6-003** | `context7` | CUSTOM (keep) | **VALID** | No Hermes equivalent. Custom `src/mcp/tools/context7.py` preserved. Auth enforced via overlay plugin instead of decorator — but the tool implementation is unchanged. |
| **P6-004** | `exa_search` | MIGRATE → Hermes `web` toolset | **STALE / NEEDS-UPDATE** | Custom `src/mcp/tools/exa_search.py` is replaced by Hermes native. **However**, the $5/day budget cap enforcement (`DAILY_CAP = 5.0` in Redis DB5) has no Hermes native equivalent. The budget logic must either (a) be ported to the `pre_tool_call` auth overlay plugin, or (b) exa_search stays custom to preserve cap enforcement. ADR-035 lists budget enforcement as a `pre_tool_call` hook concern (Pillar 5), so (a) is the intended path. Marked STALE because the tool itself is obsolete, but cap enforcement must be re-implemented before this step can be considered done. |
| **P6-005** | `fetch` | MIGRATE → Hermes `web` toolset | **OBSOLETE** | Custom `src/mcp/tools/fetch.py` replaced by Hermes native web fetch. URL validation and 1MB limit handled by Hermes native configuration. |
| **P6-006** | `filesystem` | MIGRATE → Hermes `file` toolset | **NEEDS-UPDATE** | Custom `src/mcp/tools/filesystem.py` replaced by Hermes native file operations. The path whitelist (`/home/guinevere/code`, `/home/guinevere/evidence`, `/home/guinevere/data`) and symlink guards must be ported to the auth overlay plugin or Hermes native file tool configuration. Aizanta path isolation hardening must be preserved. |
| **P6-007** | `github` | HYBRID | **NEEDS-UPDATE** | ADR-035: "Hermes terminal + git, auth granularity needed." Custom `src/mcp/tools/github.py` is partially replaced by Hermes terminal+git, but GitHub-specific operations (list repos, create issue) require the custom tool. The auth granularity concern means the tool stays custom or becomes a hybrid wrapper. The `GITHUB_PAT` stays SOPS-encrypted but config shifts. |
| **P6-008** | `grep_app` | CUSTOM (keep) | **VALID** | No Hermes equivalent. Custom `src/mcp/tools/grep_app.py` preserved. |
| **P6-009** | `obscura_cdp` | CUSTOM (keep) | **VALID** | No Hermes equivalent. Custom `src/mcp/tools/obscura_cdp.py` preserved per ADR-033. Playwright-core connect pattern unchanged. |
| **P6-010** | `sequential_thinking` | CUSTOM (keep) | **VALID** | No Hermes equivalent. Custom `src/mcp/tools/sequential_thinking.py` preserved. |
| **P6-011** | `time_tools` | CUSTOM (keep) | **VALID** | No Hermes equivalent. Custom `src/mcp/tools/time_tools.py` preserved. WIB default unchanged. |
| **P6-012** | `websearch` | MIGRATE → Hermes `web` toolset | **OBSOLETE** | Custom `src/mcp/tools/websearch.py` (Brave→Exa hybrid fallback) replaced by Hermes native web search. The Brave→Exa fallback logic is handled by Hermes web toolset native behavior or configured as provider preference. |
| **P6-013** | `git_tool` | MIGRATE → Hermes terminal + git | **NEEDS-UPDATE** | Custom `src/mcp/tools/git_tool.py` replaced by Hermes native git operations. **However**, the custom force-push protection (`force-push-to-main FORBIDDEN`, force-with-lease, case-insensitive branch names, refspec bypasses) has no Hermes native equivalent. These guards must be ported to the auth overlay plugin as FORBIDDEN patterns. |
| **P6-014** | `postgres_tool` | CUSTOM (keep) | **VALID** | No Hermes equivalent. Non-negotiable per ADR-035. Custom `src/mcp/tools/postgres_tool.py` preserved. 3-layer defense, port 5433, Aizanta isolation. |
| **P6-015** | `redis_tool` | CUSTOM (keep) | **VALID** | No Hermes equivalent. Custom `src/mcp/tools/redis_tool.py` preserved. FLUSHALL FORBIDDEN, port 6380. |
| **P6-016** | `shell_tool` | HYBRID | **NEEDS-UPDATE** | ADR-035: "Hermes terminal + custom command blocking." Custom `src/mcp/tools/shell_tool.py` is partially replaced by Hermes native terminal. The command whitelist (`ALLOWED_COMMANDS`) and block list (`BLOCKED_COMMANDS`), injection defense (;, \|, &&, $(), \`), and Aizanta path blocking must be ported to the auth overlay plugin as FORBIDDEN patterns before Hermes terminal can execute commands. |
| **P6-017** | `docker_tool` | HYBRID | **NEEDS-UPDATE** | ADR-035: "Hermes terminal, no Docker toolset in Hermes." Custom `src/mcp/tools/docker_tool.py` is partially replaced by Hermes terminal for Docker CLI commands. The guinevere-net isolation checks and container name filtering must be ported to the auth overlay plugin. |

---

### P6-018 to P6-021: Auth, Decision, Cost, Budget

| Step | Description | ADR-035 Impact | Verdict | Reasoning |
|---|---|---|---|---|
| **P6-018** | 4-Level Auth Matrix Verification | Auth overlay plugin | **NEEDS-UPDATE** | The 4-level matrix (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN) survives conceptually but changes implementation. Currently: custom `src/mcp/auth_matrix.py` with `@require_approval` decorator wrapping all 16 custom tools. ADR-035: Hermes `pre_tool_call` hook plugin intercepts ALL tool calls (Hermes native + custom MCP) — "Plugin load is compile-time gate. `on_failure: block` — if plugin crashes, ALL tool calls blocked (fail-closed)." The auth matrix config file must be updated to reference Hermes toolsets alongside custom tools. The 93 tests from P6-018 will need re-targeting. |
| **P6-019** | Tool Selection Decision Matrix | Tool consolidation | **NEEDS-UPDATE** | Currently: 16 tools with 8 overlap scenarios routed by `src/mcp/tool_selector.py`. Under ADR-035: 4 web search tools consolidate into 1 Hermes `web` toolset — overlap scenarios change. The custom tool selector becomes simpler (fewer custom tools) but more complex (Hermes native tools with different dispatch). The 27 tests from P6-019 will need updating. |
| **P6-020** | Cost Tracking per Tool (Redis DB5) | Budget hook | **NEEDS-UPDATE** | Concept remains valid: Redis DB5 stores per-tool cost with `tool:cost:{name}:YYYY-MM-DD` keys. Implementation changes: custom `src/mcp/cost.py` is replaced by the `pre_tool_call` hook that logs costs. The hook reads from the same Redis DB5 dataset. The 45 tests from P6-020 will need updating. |
| **P6-021** | Budget Enforcement ($5 Exa cap → Brave fallback) | Budget hook | **NEEDS-UPDATE** | Concept remains valid but implementation changes. Currently: custom `src/mcp/budget.py` with `$30/month absolute cap` and per-tool caps. ADR-035 Pillar 5: "Custom `pre_tool_call` hook checks cumulative cost against $30/month cap. At 80% ($24): Discord alert. At 100% ($30): block all LLM calls." The Exa→Brave fallback is now handled by Hermes web toolset consolidation. The 42 tests from P6-021 will need updating. |

---

### P6 Summary Statistics

| Metric | Count |
|---|---|
| Total P6 steps | 21 |
| VALID (unchanged custom tools) | 7 (P6-003, P6-008, P6-009, P6-010, P6-011, P6-014, P6-015) |
| NEEDS-UPDATE (hybrid, auth, cost, budget) | 10 |
| OBSOLETE (fully replaced by Hermes) | 4 (P6-002, P6-005, P6-012, plus P6-004 borderline) |
| Tools surviving unchanged | 7 of 16 |
| Tools with changed implementation | 9 of 16 |
| Tests potentially affected | ~347 tests (auth matrix 93 + tool selector 27 + cost 45 + budget 42 + individual tool tests for migrated tools) |

**P6 Verdict: 🔴 NEEDS MAJOR REWORK.** The Phase 6 StepPrompts content was written for a pre-ADR-035 architecture where all 16 MCP tools run as custom FastMCP server tools with a custom auth decorator. ADR-035 Pillar 4 restructures this to a hybrid model where only 7 tools remain fully custom, 9 change implementation surface, and the auth/cost/budget layers move to Hermes hooks. While P6 implementation is complete and tested (791 tests, 0 failures), the StepPrompts documentation for P6 will be **materially inaccurate** once ADR-035 migration begins. Re-writing P6 StepPrompts to reflect the hybrid MCP architecture is recommended as a pre-migration task (Phase 0 of ADR-035).

---

## P7 (Surveillance) — Per-Step Audit

### Surveillance Impact Analysis

The surveillance pipeline (Tasker → HMAC API → Redis DB2 buffer → TimescaleDB → Discord alert) is architecturally independent of Hermes. ADR-035 explicitly states: "All 14 surveillance files (2,466 lines) preserved verbatim." No surveillance tools appear in the MCP migration table. The pipeline runs as a dedicated FastAPI endpoint with its own systemd service (`guinevere-surveillance.service`).

**However**, 3 P7 steps involve Discord commands (`/surveillance-status`, `/surveillance-pause`, E2E test with Discord alert) that under ADR-035 become Hermes plugins (MEDIUM feasibility, "Plugin port — calls existing surveillance status APIs unchanged"). The underlying surveillance backend is untouched; only the command dispatch layer changes.

**Also**: The P7 transition checklist shows `[ ]` (unchecked) for "All 22 steps" despite P7 being marked ✅ Complete in PROGRESS.md. This is a StepPrompts display inconsistency (the phase-level checklist was never updated after completion) — the individual steps are all implemented.

---

### P7-001 to P7-011: API, Auth, Pipeline, Safety

| Step | Description | Verdict | Reasoning |
|---|---|---|---|
| **P7-001** | FastAPI Surveillance Receiver | **VALID** | Backend endpoint `POST /surveillance/events` — no Hermes dependency. Preserved verbatim per ADR-035. |
| **P7-002** | HMAC Authentication | **VALID** | SHA-256 HMAC verification — independent. Preserved. |
| **P7-003** | Replay Protection | **VALID** | Nonce + timestamp (5-min window) — independent. Preserved. |
| **P7-004** | SSL/TLS Endpoint | **VALID** | Cloudflare Tunnel / Tailscale HTTPS — independent infrastructure. Preserved. |
| **P7-005** | Redis DB2 Buffer | **VALID** | 5-min TTL burst buffer — independent. Redis DB2 assignment per ADR-030. Preserved. |
| **P7-006** | Async Consumer | **VALID** | Background worker from Redis buffer — independent. Preserved. |
| **P7-007** | TimescaleDB Ingestion | **VALID** | Redis → PostgreSQL hypertables — independent. Preserved. |
| **P7-008** | Data Classification | **VALID** | Internal/Confidential/Restricted + CRITICAL tier from P7.5 remediation — independent. Preserved. |
| **P7-009** | Clipboard Secret Scanner | **VALID** | Regex + Shannon entropy scanning — independent. Preserved. |
| **P7-010** | Consent Verification Gate | **VALID** | Faiz consent check before store — independent. Preserved. |
| **P7-011** | Safe-Mode Surveillance Blocking | **VALID** | Pause confrontation, preserve ingestion — independent. Preserved. |
| **P7-NEW** | HMAC Secret Generation | **VALID** | SOPS-encrypted secret generation — independent security operation. Preserved. |

---

### P7-012 to P7-022: Tasker Setup, Service, E2E Test

| Step | Description | Verdict | Reasoning |
|---|---|---|---|
| **P7-012** | Android Tasker Setup Guide | **VALID** | Documentation for Faiz — independent. Preserved. |
| **P7-013** | Tasker App Usage Profile | **VALID** | Foreground app tracking — independent. Preserved. |
| **P7-014** | Tasker Location Profile | **VALID** | GPS/geofencing — independent. Preserved. |
| **P7-015** | Tasker Notification Profile | **VALID** | Notification capture — independent. Preserved. |
| **P7-016** | Tasker Clipboard Profile | **VALID** | Clipboard + secret scanning — independent. Preserved. |
| **P7-017** | HMAC Signing in Tasker | **VALID** | JavaScript snippet for HTTP — independent. P7.5 remediation updated signing string format (newlines→colons). Preserved. |
| **P7-018** | `guinevere-surveillance.service` | **VALID** | Systemd service for consumer — independent. Preserved. |
| **P7-019** | `/surveillance-status` | **NEEDS-UPDATE** | Discord command. Under ADR-035, becomes Hermes plugin `surv_status_plugin.py` (MEDIUM feasibility, "Calls existing surveillance status APIs unchanged"). The underlying `src/surveillance/` status query is untouched — only the command dispatch layer changes from `discord.py` `app_commands.Command` to `ctx.register_command()`. |
| **P7-020** | `/surveillance-pause` | **NEEDS-UPDATE** | Discord command. Same as P7-019 — becomes Hermes plugin `surv_pause_plugin.py`. `invalidate_cache()` wired correctly (P7.5 remediation, 4 scopes, `asyncio.gather`). Plugin calls same backend functions. |
| **P7-021** | Surveillance E2E Test | **NEEDS-UPDATE** (minor) | The pipeline (Tasker → API → Redis → PG → Discord alert) is independent. However, the notification routing (Discord alert step) changes under Hermes from `bot.py` notification hooks to Hermes notification hooks. Test script `curl` verification steps unchanged. Alert destination verification needs Hermes-specific routing check. |
| **P7-022** | Data Retention Verification | **VALID** | 7-day raw, 90-day aggregated, 1-year summaries — independent PostgreSQL retention policy. Preserved. |

---

### P7 Summary Statistics

| Metric | Count |
|---|---|
| Total P7 steps (including P7-NEW) | 23 |
| VALID | 20 |
| NEEDS-UPDATE (Discord command surface) | 3 |
| OBSOLETE | 0 |
| Surveillance backend files preserved verbatim per ADR-035 | 14 files (2,466 lines) |

**P7 Verdict: 🟡 NEEDS MINOR UPDATE.** The surveillance backend is completely unaffected by ADR-035. Three Discord commands (`/surveillance-status`, `/surveillance-pause`, E2E alert routing) need their dispatch layer updated from discord.py to Hermes plugin — but the underlying `src/surveillance/` code is unchanged. These updates are in-scope for ADR-035 Phase 2 (Discord Gateway migration, 35 slash commands → Hermes plugins). No StepPrompts content changes are strictly necessary for P7 — existing steps are accurate regarding the surveillance backend implementation.

**Minor note:** The P7 transition checklist at line 7312 shows `[ ]` (unchecked) for "All 22 steps." This is a pre-completion artifact — PROGRESS.md confirms P7 is ✅ Complete with 472 tests pass and P7.5 remediation applied. The checklist should be updated to `[x]`.

---

## P8 (Observability) — Per-Step Audit

### Observability Impact Analysis

The observability stack (Prometheus, Grafana, Loki, Sentry, alerting, dashboards) is architecturally independent of Hermes. ADR-035 Pillar 5 retains 9Router at `localhost:20128` and Pillar 1 migrates only the Discord gateway. The monitoring infrastructure (Docker Compose, systemd, exporters) is unchanged.

**However**, 2 P8 steps are Discord commands (`/cost`, `/budget`) that become Hermes plugins under ADR-035 (LOW feasibility, "Hook + Plugin" — `cost_plugin.py`, `budget_plugin.py`). The cost/budget backend (Redis DB5, PostgreSQL cost ledger) is unchanged — only the command dispatch layer changes. P8-022 (MVP AC run) may need minor updates to reflect Hermes architecture.

---

### P8-001 to P8-011: Monitoring Stack

| Step | Description | Verdict | Reasoning |
|---|---|---|---|
| **P8-001** | Prometheus Docker Setup | **VALID** | Docker Compose with Prometheus, Grafana, Loki. Independent infrastructure. Preserved. |
| **P8-002** | node_exporter | **VALID** | System metrics (CPU, RAM, disk, network). Independent. Preserved. |
| **P8-003** | postgres_exporter | **VALID** | Database metrics. Independent. Preserved. |
| **P8-004** | redis_exporter | **VALID** | Cache metrics. Independent. Preserved. |
| **P8-005** | Scrape Configs (15s intervals) | **VALID** | Prometheus scrape targets. Independent. May need additional job for Hermes metrics if exposed. |
| **P8-006** | Grafana Setup | **VALID** | Dashboard server. Independent. Preserved. |
| **P8-007** | Datasource Provisioning | **VALID** | Prometheus + Loki + PostgreSQL datasources. Independent. Preserved. |
| **P8-008** | Dashboard Provisioning (6 dashboards) | **VALID** | Infrastructure, DB, loop, LLM, safety, finops dashboards. Independent. May need updates for Hermes-specific metrics panels but dashboards themselves are valid. |
| **P8-009** | Loki Setup | **VALID** | Log aggregation. Independent. Preserved. |
| **P8-010** | Promtail Setup | **VALID** | journalctl → Loki pipeline. Independent. May need additional journal job for Hermes logs. |
| **P8-011** | Log Pipeline Test | **VALID** | ⏸️ DEFERRED-VPS per PROGRESS.md. Script `scripts/test_log_pipeline.sh` exists. No Hermes dependency. |

---

### P8-012 to P8-023: Sentry, Alerts, Cost, MVP Gate

| Step | Description | Verdict | Reasoning |
|---|---|---|---|
| **P8-012** | Sentry SDK Integration | **VALID** | Error tracking in FastAPI. Independent. `send_default_pii=False` preserved. |
| **P8-013** | Sentry Scrubber | **VALID** | PII removal. Independent. Preserved. |
| **P8-014** | Alert Rules (SEV0-SEV4) | **VALID** | Prometheus alertmanager.yml. Independent. Preserved. |
| **P8-015** | SEV Routing Matrix | **VALID** | Severity → Discord + Gotify. Independent. Preserved. |
| **P8-016** | Alert Test | **VALID** | ⏸️ DEFERRED-VPS. Test script `scripts/test_alert_routing.sh` exists. No Hermes dependency. |
| **P8-017** | `/cost` command | **NEEDS-UPDATE** | Discord command (662 lines, 5-part pattern). Under ADR-035, becomes Hermes plugin `cost_plugin.py` (LOW feasibility, "Hook + Plugin"). Business logic ported: `pre_tool_call` hook integration for real-time tracking, queries both `hermes insights` data and custom PostgreSQL cost ledger. The underlying cost tracking data (Redis DB5, PostgreSQL) is unchanged — only the command dispatch and LLM call tracking layers change. The 662-line implementation will be refactored to ~400 lines of Hermes plugin code. |
| **P8-018** | `/budget` command | **NEEDS-UPDATE** | Discord command (643 lines, view/set actions). Same as P8-017 — becomes `budget_plugin.py` (LOW feasibility). Budget enforcement moves to `pre_tool_call` hook (ADR-035 Pillar 5). The plugin manages budget state + alert pipeline. |
| **P8-019** | Monthly Cost Report Automation | **VALID** | APScheduler job (538 lines). Independent backend. Preserved. The report delivery may change from bot.py notification to Hermes notification hook, but the report generation logic is unchanged. |
| **P8-020** | Backup Monitoring | **VALID** | Backup alerts per ADR-032. Independent. `backup-metric-collector.sh` preserved. |
| **P8-021** | `guinevere-monitoring.service` | **VALID** | Systemd unit, MemoryMax=1G. Independent. Preserved. |
| **P8-022** | MVP Acceptance Criteria Run | **NEEDS-UPDATE** (minor) | Currently: 19 PASS, 49 NOT-RUN, 9 BLOCKED. Under ADR-035, some acceptance criteria may need reinterpretation for Hermes architecture (e.g., ACs related to Discord gateway, MCP tool auth). The AC catalog itself is valid — only the execution context for Discord-gateway-related ACs changes. Minor update to reflect Hermes architecture in the criteria mapping. |
| **P8-023** | Faiz Sign-off Checklist | **VALID** | ✅ APPROVED 2026-06-03. Manual verification checklist. Independent. |

---

### P8 Summary Statistics

| Metric | Count |
|---|---|
| Total P8 steps | 23 |
| VALID | 20 |
| NEEDS-UPDATE (Discord commands + MVP AC context) | 3 |
| OBSOLETE | 0 |
| Status per PROGRESS.md | 19 PASS, 2 DEFERRED-VPS, 1 PASS (DOC), Faiz approved |

**P8 Verdict: 🟡 NEEDS MINOR UPDATE.** The observability infrastructure is completely unaffected by ADR-035. Two Discord commands (`/cost`, `/budget`) need their dispatch layer updated from discord.py to Hermes plugins — same pattern as P7 Discord commands. The MVP AC run (P8-022) may need minor context updates for Hermes architecture. No StepPrompts content changes are strictly necessary for P8 — existing steps are accurate regarding the observability implementation. The command migration is in-scope for ADR-035 Phase 2.

**Minor note:** The P8 transition checklist at line 7458 shows `[ ]` (unchecked). PROGRESS.md confirms P8 is ✅ Complete with Faiz sign-off. Update checklist to `[x]`.

---

## Cross-Phase Findings

### F1: P6-P7-P8 Transition Checklists Are Stale

All three phase-level transition checklists at lines 7068, 7312, and 7458 show `[ ]` (unchecked) despite PROGRESS.md confirming all phases are complete. This is a display issue — the individual step statuses are correct but the aggregate checklists were never updated.

### F2: P6 Tool Count Discrepancy

StepPrompts P6 header says "16 MCP tools" (line 7063). ADR-035 Pillar 4 says 5 native Hermes toolsets + 7 custom tools + 3 hybrid = still 16 functional tools, but reorganized into a different ownership model. The StepPrompts count is numerically correct — the architecture difference is in how the 16 tools are implemented, not how many exist.

### F3: P6 Evidence Paths Contain Pre-ADR-035 Artifacts

P6 implementation evidence at `docs/setup-evidence/P6/STEP-P6-001/` through `STEP-P6-021/` was generated before ADR-035 was accepted. The evidence documents the pre-ADR-035 architecture (all-16-custom FastMCP server). Post-ADR-035 migration (Phase 4: MCP + Tools, 5-7 days), new evidence will be needed for the hybrid architecture.

### F4: P7 E2E Test Discord Alert Routing

P7-021 E2E test verifies Tasker → API → Redis → PG → **Discord alert**. Under ADR-035, the Discord alert notification path changes from `bot.py` notifications to Hermes notification hooks. The pipeline test script itself (curl → Redis → psql) is unchanged — only the final notification delivery step changes.

### F5: P8 Dashboards May Need Hermes Metrics

P8-008 provisions 6 Grafana dashboards (infrastructure, DB, loop, LLM, safety, finops). Under ADR-035, new metrics may be needed: Hermes gateway health, hook execution latency, plugin state, compression effectiveness. Existing dashboards are valid — new panels may be a future addition.

---

## Overall Phase Verdicts

| Phase | Verdict | Action Required |
|---|---|---|
| **P6 (MCP)** | 🔴 **NEEDS MAJOR REWORK** | StepPrompts P6 needs rewriting to reflect hybrid MCP architecture (ADR-035 Pillar 4). 9 of 16 tools change implementation surface. Auth matrix, cost tracking, and budget enforcement move to Hermes hooks. Recommending this as an ADR-035 Phase 0 task (pre-migration preparation). |
| **P7 (Surveillance)** | 🟡 **NEEDS MINOR UPDATE** | 3 of 23 steps have Discord command surface changes (→ Hermes plugins per ADR-035 Phase 2). Surveillance backend (20 steps) is completely unaffected. StepPrompts P7 content is 87% accurate post-ADR-035. Update checklist to reflect completion status. |
| **P8 (Observability)** | 🟡 **NEEDS MINOR UPDATE** | 3 of 23 steps have Discord command or context changes. Observability infrastructure (20 steps) is completely unaffected. StepPrompts P8 content is 87% accurate post-ADR-035. Update checklist to reflect completion status. |

---

## Recommendation

1. **P6 StepPrompts rewrite** (PRIORITY): Before ADR-035 Phase 4 (MCP + Tools, 5-7 days), rewrite Phase 6 StepPrompts to reflect:
   - 6 MIGRATE tools → Hermes native configuration (not custom Python files)
   - 3 HYBRID tools → Hermes native + auth overlay plugin patterns
   - 7 CUSTOM tools → preserved with auth overlay (not `@require_approval` decorator)
   - Auth matrix → `pre_tool_call` hook plugin configuration
   - Cost/budget → `pre_tool_call` hook plugin configuration
   
2. **P7 checklist update**: Mark transition checklist `[x]`. No structural changes needed.

3. **P8 checklist update**: Mark transition checklist `[x]`. No structural changes needed.

---

**Audit performed by:** Guinevere (Sisyphus-Junior)  
**Sources:** `stepprompts/StepPrompts.md` lines 7061–7610, `adr/ADR-035-hermes-migration.md` (full), `PROGRESS.md`  
**Output:** `research-reports/stepprompts-audit/P6-P7-P8-audit.md`
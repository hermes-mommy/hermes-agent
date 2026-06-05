# Batch Plan — Phase 4: MCP + Tools Migration

> **Status**: APPROVED v1.1 — All 3 auditors PASS  
> **Scope**: ADR-035 Phase 4 (Pillar 4 — MCP + Tools)  
> **Dependency**: Phase 2 (Discord Gateway) must PASS (ADR-035 line 1608). Phase 3 (Memory Bridge) is recommended but not a hard gate per ADR-035.  
> **Estimated Duration**: 38 hours across 5 waves (ADR-035 estimates 5-7 days at ~6hr/day)  
> **Risk Level**: CRITICAL (per ADR-035 risk register)

---

## §1 Master Todo

| Step ID | Title | Depends On | Parallelism | Duration | Wave |
|---------|-------|------------|-------------|----------|------|
| P4-001 | Configure 5 Hermes native MCP servers | — | parallel | 3hr | 1 |
| P4-002 | Build auth overlay plugin for Hermes | P4-001 | sequential | 12hr | 2 |
| P4-003 | Integrate budget enforcement into pre_tool_call hook | P4-002 | parallel | 4hr | 3 |
| P4-004 | Port hybrid tool safety guards to Hermes terminal | P4-002 | parallel | 6hr | 3 |
| P4-005 | Retain & verify 7 FastMCP custom tools | — | parallel | 2hr | 1 |
| P4-006 | Build plugin startup gate (critical:true enforcement) | P4-002 | parallel | 3hr | 3 |
| P4-007 | Security audit all 16 tools against auth matrix | P4-003, P4-004, P4-005, P4-006 | sequential | 4hr | 4 |
| P4-008 | End-to-end integration test suite | P4-007 | sequential | 4hr | 5 |

**Total**: 38 hours. 5 waves. 3 parallel groups.

---

## §2 Dependency Map

```
                    ┌─────────────┐     ┌─────────────┐
     Wave 1         │   P4-001    │     │   P4-005    │
     (parallel)     │ Native MCP  │     │ FastMCP     │
                    │  Servers    │     │ Retention   │
                    └──────┬──────┘     └──────┬──────┘
                           │                   │
                           ▼                   │
                    ┌─────────────┐            │
     Wave 2         │   P4-002    │            │
     (sequential)   │ Auth Overlay│            │
                    │   Plugin    │            │
                    └──────┬──────┘            │
                           │                   │
              ┌────────────┼────────────┐      │
              ▼            ▼            ▼      │
     Wave 3  ┌──────┐  ┌──────┐  ┌──────┐     │
     (parallel)│P4-003│  │P4-004│  │P4-006│     │
              │Budget│  │Hybrid│  │Startup│    │
              │Hook  │  │Guards│  │ Gate │     │
              └──┬───┘  └──┬───┘  └──┬───┘     │
                 │         │         │         │
                 └─────────┴─────────┘         │
                           │                   │
                           ▼                   │
                    ┌─────────────┐            │
     Wave 4         │   P4-007    │◄───────────┘
     (sequential)   │  Security   │
                    │   Audit     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
     Wave 5         │   P4-008    │
     (sequential)   │ Integration │
                    │    Tests    │
                    └─────────────┘
```

### Parallel Execution Waves

| Wave | Steps | Parallel? | Gate Condition |
|------|-------|-----------|----------------|
| 1 | P4-001 + P4-005 | Yes — independent | None |
| 2 | P4-002 | No — sequential | P4-001 PASS |
| 3 | P4-003 + P4-004 + P4-006 | Yes — all depend on P4-002 only | P4-002 PASS |
| 4 | P4-007 | No — sequential | P4-003 + P4-004 + P4-005 + P4-006 all PASS |
| 5 | P4-008 | No — sequential | P4-007 PASS |

---

## §3 Research Inputs

| Report ID | Title | Path | Key Findings |
|-----------|-------|------|--------------|
| R4-001 | Hermes MCP Config Patterns | `research-reports/phase-4-planning/R4-001-hermes-mcp-config-patterns.md` | `config.yaml` already has `mcp_servers` block with all 5 native servers. Plugin blueprint exists. Systemd ready with `--accept-hooks`. |
| R4-002 | Auth Overlay & Safety Patterns | `research-reports/phase-4-planning/R4-002-auth-overlay-safety-patterns.md` | Auth matrix fully implemented in `src/mcp/auth.py` + `auth_matrix.py`. Safety plugin blueprint ready. Discord/Gotify notification production-ready. |
| R4-003 | FastMCP Custom Tools | `research-reports/phase-4-planning/R4-003-fastmcp-custom-tools.md` | All 7 KEEP tools inventoried with decorators, registration, systemd service. `sys.path` hack in manager.py. |
| R4-004 | Hybrid Tool Blocking | `research-reports/phase-4-planning/R4-004-hybrid-tool-blocking.md` | Shell whitelist+injection+hard-block. Docker net isolation+name validation. Git force-push guard. GitHub rate-limit+backoff. Approval flow 5min+Discord+`/approve`. |
| R4-005 | Budget Enforcement | `research-reports/phase-4-planning/R4-005-budget-enforcement.md` | BudgetEnforcer daily/monthly caps. ToolCostTracker Redis DB5. **GAP**: not integrated into pre_tool_call hook. 9Router exclusive. |
| R4-006 | Aizanta Isolation | `research-reports/phase-4-planning/R4-006-aizanta-isolation.md` | **PASSED**. Port isolation (Redis 6380, PG 5433). Docker net isolation. Redis DB0-DB5. 13 systemd under guinevere.slice. |
| R4-007 | Hermes Agent MCP Plugin Docs | `research-reports/phase-4-planning/R4-007-hermes-mcp-plugin-docs.md` | MCP config via `mcp_servers`. Plugin Python dirs. Hook system complete. **CRITICAL**: `critical: true` / `on_failure: block` NOT native Hermes. Fail-open model. |
| R4-008 | Budget OSS Patterns | `research-reports/phase-4-planning/R4-008-budget-enforcement-patterns.md` | Redis Lua atomic cost check. crewAI/ADK before_tool_call. LiteLLM full budget tracking. OpenRouter exact costs. Recommended: Lua script in pre_tool_call + post-call reconciliation. |

---

## §4 Known State

### 4.1 Hermes Configuration (`hermes-config/config.yaml`, 327 lines)

| Section | Lines | Status | Phase 4 Impact |
|---------|-------|--------|----------------|
| `discord:` | 12-39 | Production-ready | No changes |
| `llm:` | 44-64 | Production-ready, 9Router at localhost:20128 | Budget block exists but not wired to pre_tool_call |
| `agent:` | 69-79 | max_iterations: 15 | No changes |
| `memory:` | 83-103 | FTS5, compression enabled | No changes |
| `hooks:` | 130-150 | consent_gate.py + dnr_filter.py | **MODIFY**: add auth_overlay hook to pre_tool_call list |
| `mcp_servers:` | 155-210 | Pre-defined: web, filesystem, terminal, git, fetch | **VERIFY**: ensure tool lists match ADR-035 migration targets |
| `cron:` | 215-256 | 5 rituals + 3 system jobs | No changes |
| `observability:` | 261-274 | Prometheus 9191, JSON logging | No changes |
| `auth_matrix:` | 280-307 | All 5 native server categories mapped | **VERIFY**: cross-reference with `src/mcp/auth_matrix.py` |
| `approval:` | 312-317 | Discord webhook, 5min timeout, deny on timeout | No changes |
| `audit:` | 322-327 | log_all_destructive, log_all_forbidden_attempts, 90-day retention | No changes |

### 4.2 Auth Matrix (`src/mcp/auth_matrix.py`, 278 lines)

| Tool | Operations Mapped | Level Distribution |
|------|-------------------|-------------------|
| brave_search | `*` wildcard | All READ_AUTO |
| context7 | resolve, query | All READ_AUTO |
| exa | `*` wildcard | All READ_AUTO |
| fetch | `*` wildcard | All READ_AUTO |
| grep_app | `*` wildcard | All READ_AUTO |
| sequential_thinking | `*` wildcard | All READ_AUTO |
| time | `*` wildcard | All READ_AUTO |
| websearch | `*` wildcard | All READ_AUTO |
| filesystem | read, list, write, delete | READ_AUTO(2), WRITE_NOTIFY(1), DESTRUCTIVE_APPROVAL(1) |
| github | read, get, search, create_issue, create_pr, delete_repo | READ_AUTO(3), WRITE_NOTIFY(2), DESTRUCTIVE_APPROVAL(1) |
| obscura_cdp | navigate, read, form_fill, click, file_upload | READ_AUTO(2), WRITE_NOTIFY(2), DESTRUCTIVE_APPROVAL(1) |
| git | log, diff, status, commit, push, force_push, force_push_main | READ_AUTO(3), WRITE_NOTIFY(2), DESTRUCTIVE_APPROVAL(1), FORBIDDEN(1) |
| postgres | select, explain, insert, update, delete_row, drop, truncate | READ_AUTO(2), FORBIDDEN(5) |
| redis | 19 operations (get through slaveof) | READ_AUTO(9), WRITE_NOTIFY(9), DESTRUCTIVE_APPROVAL(4), FORBIDDEN(6) |
| shell | exec, rm_rf_root, sudo_rm_rf | DESTRUCTIVE_APPROVAL(1), FORBIDDEN(2) |
| docker | ps, logs, inspect, images, start, stop, restart, rm, rmi, system_prune, rm_all | READ_AUTO(4), WRITE_NOTIFY(3), DESTRUCTIVE_APPROVAL(2), FORBIDDEN(2) |

**`ALL_TOOL_NAMES`**: 16 tools verified in canonical tuple.  
**`verify_matrix_completeness()`**: Assertion gate at FastMCP startup.  
**`get_auth_level()`**: KeyError on miss — fail-closed by design.

### 4.3 FastMCP Server (`src/mcp/manager.py`, 103 lines)

- Factory pattern: `create_server()` builds FastMCP, registers all tools via `register_all_tools(server)`
- `sys.path` manipulation to prevent local `src/mcp` shadowing pip `mcp` package
- Startup verification: calls `verify_matrix_completeness()` (RG-008 gate)
- Systemd: `systemd/guinevere-mcp.service` → `python -m src.mcp.manager`
- Environment: `.env.mcp` (SOPS/age encrypted)

### 4.4 Existing Safety Plugin (`hermes-config/plugins/guinevere_safety/plugin.py`, 228 lines)

- `GuinevereSafetyPlugin` class with `pre_prompt` + `post_response` hooks
- State management via `StateManager` → Redis DB5
- Already loaded by Hermes via `plugins.enabled` in config
- **Phase 4 addition**: auth_overlay logic should be a NEW plugin (separation of concerns), NOT merged into this existing plugin

### 4.5 Critical Gaps Identified

| Gap ID | Description | Source | Phase 4 Step |
|--------|-------------|--------|--------------|
| GAP-001 | Budget enforcement not integrated into pre_tool_call hook | R4-005 | P4-003 |
| GAP-002 | `critical: true` / `on_failure: block` not native Hermes flags | R4-007 | P4-006 |
| GAP-003 | Hermes terminal config needs porting of shell_tool safety layers | R4-004 | P4-004 |
| GAP-004 | FastMCP→Hermes MCP bridge not yet configured for 7 custom tools | R4-003 | P4-005 |
| GAP-005 | LLM cost tracking not in ToolCostTracker (only tool costs) | R4-005 | P4-003 (scope note) |

### 4.6 VPS State

| Component | Current State | Phase 4 Impact |
|-----------|--------------|----------------|
| Redis 6380 | Running, DB0-DB5 active | No changes — auth overlay uses DB5 for cost tracking |
| PostgreSQL 5433 | Running, database `guinevere` | No changes |
| Hermes binary | v0.15.2 at `.venv/bin/hermes` | No changes |
| Systemd `hermes-gateway.service` | `--accept-hooks` flag | No changes needed |
| Systemd `guinevere-mcp.service` | FastMCP server for 7 custom tools | **VERIFY**: ensure service survives Phase 4 |
| Docker `guinevere-net` | 172.28.x.x, isolated from Aizanta | No changes |
| 9Router | localhost:20128/v1 | No changes |

---

## §5 Binding Decisions

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|---------------------|
| BD-001 | Auth overlay as SEPARATE Hermes plugin (not merged into guinevere_safety) | Separation of concerns: safety = persona state, auth = tool authorization. Independent testing, rollback, and lifecycle. | Merging into guinevere_safety — rejected: creates coupling between persona state and tool auth, harder to test/rollback independently |
| BD-002 | Custom startup wrapper for `critical: true` enforcement | Hermes v0.15.2 uses fail-open plugin model. Plugin crash = log+skip. ADR-035 requires fail-closed. Wrapper script validates all plugins before Hermes proceeds. | Waiting for Hermes upstream feature — rejected: no timeline, blocks Phase 4 indefinitely |
| BD-003 | Redis Lua script for atomic budget check in pre_tool_call | Prevents race conditions during concurrent sub-agent tool calls. Single Redis round-trip. Pattern proven in 2API-Fuse, inbox-zero, openadserver. | Application-level check-then-increment — rejected: TOCTOU race condition with parallel tool calls |
| BD-004 | FastMCP server retained as MCP stdio backend for 7 custom tools | All 7 tools production-ready with auth decorators. Hermes connects via MCP protocol. Zero code changes to tool implementations. | Rewriting tools as Hermes plugins — rejected: 7 tools × avg 200 lines = 1400 LOC rewrite with zero functional gain |
| BD-005 | Hybrid tool safety as Hermes terminal config + plugin guards | Hermes terminal has native `command_allowlist`/`UNRECOVERABLE_BLOCKLIST`. Plugin guards add Guinevere-specific patterns (Docker net check, git force-push guard). | Relying solely on Hermes native terminal security — rejected: misses Guinevere-specific guards (guinevere-net prefix, main/master protection) |
| BD-006 | Auth overlay plugin imports Python auth_matrix.py directly — single source of truth | Eliminates YAML/Python drift entirely. Auth overlay uses the same AUTH_MATRIX as FastMCP. Hermes plugin can import any Python module in the project. Python auth_matrix.py has get_auth_level(tool, op) with KeyError fail-closed — all 16 tools, all operations, all 4 levels in one file. | Dual YAML+Python source-of-truth — rejected: guarantees future drift (F-001, F-010 from Security Audit). YAML in config.yaml covers only 5 of 16 tools, misses all 15 FORBIDDEN operations. |
| BD-007 | Budget thresholds: Warning $24 (80%), Block $30 (100%) per ADR-035 + FinOps v1.1 | Matches existing `llm.budget` config in config.yaml. ToolCostTracker already has these caps. | Lowering thresholds — rejected: would require ADR amendment |

---

## §6 Collision Scan

| Shared Resource | Steps Touching | Collision Type | Mitigation |
|-----------------|----------------|----------------|------------|
| `hermes-config/config.yaml` | P4-001, P4-002, P4-003, P4-004 | Same source file — multiple edits | **P4-001 is sole owner** of config.yaml. P4-002/003/004 produce plugin/hook files only. P4-001 applies all config.yaml changes atomically. |
| `hermes-config/hooks/` directory | P4-002, P4-003 | Two new hook scripts | P4-002 creates `auth_overlay.py`. P4-003 creates `budget_check.py`. No overlap. |
| `hermes-config/plugins/` directory | P4-002, P4-006 | Plugin + startup wrapper | P4-002 creates `auth_overlay/` plugin dir. P4-006 creates `scripts/startup_gate.py`. No overlap. |
| `src/mcp/auth_matrix.py` | None | Read-only reference | No modifications. All steps READ this file for auth level values. |
| `systemd/guinevere-mcp.service` | P4-005 | Verify only | Read-only verification. No modifications. |
| `docs/setup-evidence/phase-4/` | Parent only | Shared evidence directory | Parent orchestrator owns all evidence writes. |
| `research-reports/phase-4-planning/` | Complete | No further writes | All 8 reports finalized. Read-only. |

**Verdict**: No unresolved collisions. config.yaml is the only shared-edit file, mitigated by single-owner (P4-001).

---

## §7 Files to Create/Modify

### 7.1 Files to CREATE

| File | Step | Purpose |
|------|------|---------|
| `hermes-config/plugins/auth_overlay/__init__.py` | P4-002 | Auth overlay plugin entry point |
| `hermes-config/plugins/auth_overlay/manifest.yaml` | P4-002 | Plugin manifest (name, version, hooks) |
| `hermes-config/plugins/auth_overlay/auth_handler.py` | P4-002 | pre_tool_call auth matrix enforcement logic |
| `hermes-config/plugins/auth_overlay/approval_handler.py` | P4-002 | DESTRUCTIVE_APPROVAL webhook + 5min wait |
| `hermes-config/plugins/auth_overlay/notify_handler.py` | P4-002 | WRITE_NOTIFY Discord/Gotify notification |
| `hermes-config/plugins/auth_overlay/forbidden_handler.py` | P4-002 | FORBIDDEN hard-block + audit log |
| `hermes-config/hooks/budget_check.py` | P4-003 | Redis Lua atomic budget check hook script |
| `hermes-config/hooks/budget_lua.py` | P4-003 | Lua script loader for atomic cost deduction |
| `hermes-config/hooks/budget_lua_extended.py` | P4-003 | Extended Lua script with per-tool daily caps |
| `hermes-config/hooks/hybrid_guards.py` | P4-004 | Shell/Docker/Git/GitHub safety guard functions |
| `scripts/startup_gate.py` | P4-006 | Plugin validation wrapper (critical:true enforcement) |
| `scripts/startup_gate_test.py` | P4-006 | Unit tests for startup gate |
| `tests/hermes/test_auth_overlay.py` | P4-002 | Auth overlay plugin tests (all 4 auth levels) |
| `tests/hermes/test_budget_hook.py` | P4-003 | Budget hook tests (allow/warn/block thresholds) |
| `tests/hermes/test_hybrid_guards.py` | P4-004 | Hybrid guard tests (shell whitelist, docker net, git force) |
| `tests/hermes/test_security_audit.py` | P4-007 | Security audit script testing all 16 tools |
| `tests/hermes/test_integration_e2e.py` | P4-008 | End-to-end integration tests via Hermes CLI |
| `docs/setup-evidence/phase-4/verification.md` | P4-007 | Phase 4 verification report |
| `docs/setup-evidence/phase-4/auditor-gate.md` | P4-007 | Auditor gate report |

### 7.2 Files to MODIFY

| File | Step | Changes |
|------|------|---------|
| `hermes-config/config.yaml` | P4-001 | Verify/update `mcp_servers` tool lists, `auth_matrix` section, add `plugins.enabled: [guinevere_safety, auth_overlay]` if missing |
| `hermes-config/config.yaml` | P4-003 | Add `budget_check.py` hook entry to `hooks.pre_tool_call` list |
| `hermes-config/config.yaml` | P4-004 | Verify/update `terminal.allowed_commands`, `terminal.blocked_commands`, `git.blocked_operations` |

**NOTE**: P4-001 is the sole owner of config.yaml. P4-003 and P4-004 changes to config.yaml are applied by P4-001 implementer based on specifications from P4-003/P4-004 agents.

### 7.3 Files NOT to Modify

| File | Reason |
|------|--------|
| `src/mcp/auth.py` | Production code. Phase 4 is READ-ONLY on existing MCP infrastructure. |
| `src/mcp/auth_matrix.py` | Source of truth for FastMCP. No modifications. |
| `src/mcp/manager.py` | FastMCP factory unchanged. |
| `src/mcp/tools/*.py` (all 7 custom tools) | Production code. Zero changes to tool implementations. |
| `src/mcp/budget.py` | Production code. Phase 4 hooks INTO it, does not modify it. |
| `src/mcp/cost.py` | Production code. Phase 4 hooks INTO it, does not modify it. |
| `systemd/guinevere-mcp.service` | Read-only verification in P4-005. |
| `hermes-config/plugins/guinevere_safety/*` | Existing safety plugin. P4-002 may add try/except wrappers only — no logic changes. |
| `scripts/hermes-gateway.service` | Systemd service. No modifications. |
| `adr/ADR-035-hermes-migration.md` | Accepted ADR. No modifications. |
| Any ADR or governance document | Parent-only. |

---

## §8 Implementation Design Per-Step

### P4-001: Configure 5 Hermes Native MCP Servers (3hr)

**Goal**: Verify and finalize the `mcp_servers` block in `hermes-config/config.yaml` to match ADR-035 Pillar 4 migration targets exactly.

**Current State** (from §4.1, lines 155-210):
```yaml
mcp_servers:
  web:
    enabled: true
    tools: [brave_search, exa_search, fetch_url, websearch]
  filesystem:
    enabled: true
    root_path: /home/guinevere/code/guinevere
    allowed_paths: [/home/guinevere/code/guinevere]
    blocked_paths: [/etc, /root, /home/guinevere/.ssh]
  terminal:
    enabled: true
    allowed_commands: ["ls,cat,head,tail,grep,find,wc,sort,uniq", "python,pip,pytest", "git,gh"]
    blocked_commands: ["rm,dd,mkfs,shutdown,reboot,poweroff", "iptables,ufw,systemctl"]
    timeout_seconds: 30
  git:
    enabled: true
    allowed_operations: [status, diff, log, branch, checkout, add, commit, push, pull]
    blocked_operations: ["push --force", "reset --hard", "clean -fd"]
  fetch:
    enabled: true
    timeout_seconds: 30
    max_response_size_mb: 10
```

**Changes Required**:
1. Verify `web.tools` list matches ADR-035: brave_search, exa_search, fetch_url, websearch. NOTE: Hermes uses fetch_url as the tool name (not fetch). The auth_matrix.py maps this as "fetch" with wildcard "*". Since BD-006 now imports auth_matrix.py directly, the tool_name resolution must map Hermes "fetch_url" → Python "fetch" in _extract_operation. This mapping is specified in the operation extraction spec.
2. Add `plugins.enabled: [guinevere_safety, auth_overlay]` to config (if not present).
3. Reserve hook slots for P4-003 (budget_check.py) and P4-004 (hybrid_guards adjustments).
4. Verify `auth_matrix` YAML section (lines 280-307) matches `src/mcp/auth_matrix.py` for all 5 native server categories.

**Acceptance**: `hermes config validate` passes. `hermes mcp list` shows all 5 servers enabled with correct tool counts.

### P4-002: Build Auth Overlay Plugin (12hr)

**Goal**: Create a new Hermes plugin `auth_overlay` that intercepts ALL tool calls via `pre_tool_call` hook and enforces the 4-level auth matrix.

**Architecture**:
```
Hermes Tool Call
      │
      ▼
pre_tool_call hook
      │
      ├─ Read tool_name from hook context
      ├─ Determine operation from tool args
      ├─ Lookup auth level from AUTH_MATRIX (config.yaml YAML section)
      │
      ├─ READ_AUTO → return {"action": "allow"}
      ├─ WRITE_NOTIFY → allow + async Discord/Gotify notification
      ├─ DESTRUCTIVE_APPROVAL → block + Discord webhook + 5min wait
      │     └─ Approved → {"action": "allow"}
      │     └─ Timeout/Denied → {"action": "block", "reason": "..."}
      └─ FORBIDDEN → {"action": "block", "reason": "..."} + audit log
```

**Plugin Structure**:
```
hermes-config/plugins/auth_overlay/
├── __init__.py          # register(ctx) entry point
├── manifest.yaml        # manifest: name, version, hooks
├── auth_handler.py      # Main pre_tool_call handler + auth level routing
├── approval_handler.py  # DESTRUCTIVE_APPROVAL: Discord webhook + asyncio wait
├── notify_handler.py    # WRITE_NOTIFY: async Discord embed + Gotify fallback
└── forbidden_handler.py # FORBIDDEN: hard-block + structured audit log
```

**`manifest.yaml`**:
```yaml
name: auth_overlay
version: 1.0.0
description: "Guinevere 4-level auth matrix enforcement for all tool calls"
author: Guinevere
hooks:
  pre_tool_call:
    handler: auth_handler.on_pre_tool_call
    priority: 100  # Highest priority — runs before consent_gate (90)
```

**`auth_handler.py` core logic**:
```python
import sys
sys.path.insert(0, "/home/guinevere/code/guinevere")
from src.mcp.auth_matrix import AUTH_MATRIX, get_auth_level

async def on_pre_tool_call(context: dict) -> dict:
    tool_name = context["tool_name"]
    operation = _extract_operation(tool_name, context.get("args", {}))
    
    try:
        level = get_auth_level(tool_name, operation)
    except KeyError:
        # Unknown tool/operation — fail-closed (F-004 from Security Audit)
        _audit_unknown(tool_name, operation, context)
        return {"action": "block", "reason": f"UNKNOWN: {tool_name}.{operation}"}
    
    if level == "READ_AUTO":
        return {"action": "allow"}
    elif level == "WRITE_NOTIFY":
        await _notify_write(tool_name, operation, context)
        return {"action": "allow"}
    elif level == "DESTRUCTIVE_APPROVAL":
        return await _request_approval(tool_name, operation, context)
    elif level == "FORBIDDEN":
        _audit_forbidden(tool_name, operation, context)
        return {"action": "block", "reason": f"FORBIDDEN: {tool_name}.{operation}"}
```

**Operation Extraction Spec (`_extract_operation`)**:

| Tool Category | Extraction Method | Example |
|---|---|---|
| Wildcard READ_AUTO tools (brave_search, exa, fetch, websearch, grep_app, context7, sequential_thinking, time) | Return `"*"` — operation irrelevant, all ops same level | `_extract_operation("brave_search", {}) → "*"` |
| filesystem | Map Hermes file tool operation names: read→"read", write→"write", delete→"delete", list→"read" | `_extract_operation("filesystem", {"op": "write"}) → "write"` |
| terminal (shell) | Return `"exec"` — all terminal commands use single auth level | `_extract_operation("shell", {"command": "ls"}) → "exec"` |
| terminal (docker) | Extract first word of command as operation: `docker ps`→"ps", `docker rm`→"rm" | `_extract_operation("docker", {"command": "docker rm foo"}) → "rm"` |
| git | Map git sub-command: status→"status", push→"push", force_push→"force_push_main" | `_extract_operation("git", {"args": ["push", "--force", "main"]}) → "force_push_main"` |
| postgres | Return `"select"` for read queries (SELECT/EXPLAIN), specific DML keyword for write | `_extract_operation("postgres", {"query": "DROP TABLE..."}) → "drop"` |
| redis | Extract first word of command: get→"get", set→"set", flushdb→"flushdb" | `_extract_operation("redis", {"command": "set key val"}) → "set"` |
| obscura_cdp | Map function name: navigate→"navigate", fill_form→"form_fill", click→"click" | `_extract_operation("obscura_cdp", {"fn": "navigate"}) → "navigate"` |
| github | Map operation: read/get/search→READ_AUTO, create_issue/create_pr→WRITE_NOTIFY, delete_repo→DESTRUCTIVE_APPROVAL | `_extract_operation("github", {"op": "create_pr"}) → "create_pr"` |
| Unknown | Return `"__unknown__"` — triggers fail-closed block | `_extract_operation("mystery_tool", {}) → "__unknown__"` |

**Key Design Constraints**:
- Auth matrix imported from Python auth_matrix.py — single source of truth (BD-006). Unknown tool/operation → block + audit log (fail-closed).
- Unknown tool or operation → `{"action": "block", "reason": "UNKNOWN: {tool}.{op}"}` + audit log entry. Fail-closed by design (Security Audit F-004).
- Approval webhook uses existing `approval.discord_webhook_url_env` from config.yaml
- 5min timeout with `fallback_on_timeout: deny` (fail-closed)
- All FORBIDDEN attempts logged with 90-day retention per `audit` config
- Plugin MUST NOT crash — all exceptions caught and converted to `{"action": "block", "reason": "auth_overlay_error"}`

**guinevere_safety Runtime Fail-Closed Wrapper** (addresses Security Audit F-008):

The existing `guinevere_safety` plugin must be wrapped with fail-closed exception handling, mirroring auth_overlay. If any guinevere_safety hook crashes at runtime:
- `pre_prompt` hook crash → return `{"action": "block", "reason": "safety_plugin_error"}`
- `post_response` hook crash → log SEV-1 alert to Discord + Gotify, block response

Implementation: Add try/except wrapper to each guinevere_safety hook registration in `hermes-config/plugins/guinevere_safety/plugin.py`. The wrapper catches ALL exceptions and returns block action for pre_* hooks. This ensures Hermes fails safe even if the safety plugin encounters a runtime error.

**NOTE**: This is a MINIMAL change to the existing plugin — adding exception handling only, not changing safety logic. P4-002 implements this wrapper. The "Files NOT to Modify" list for `hermes-config/plugins/guinevere_safety/*` is AMENDED: P4-002 MAY add try/except wrappers to existing hook registrations, but MUST NOT change any safety logic, state management, or Redis persistence code.

**Acceptance**: Unit tests pass for all 4 auth levels. Plugin loads in Hermes without errors. FORBIDDEN operations are 100% blocked.

### P4-003: Integrate Budget Enforcement into pre_tool_call Hook (4hr)

**Goal**: Wire existing `BudgetEnforcer` and `ToolCostTracker` into a Hermes `pre_tool_call` hook that atomically checks and deducts tool costs before execution.

**Architecture** (from R4-008 recommended pattern):
```
pre_tool_call hook
      │
      ├─ Extract tool_name
      ├─ Estimate cost from _TOOL_COSTS (src/mcp/cost.py)
      ├─ Execute Redis Lua script (atomic):
      │     KEYS[1] = "cost:current_month"
      │     ARGV[1] = estimated_cost
      │     ARGV[2] = hard_cap (30.00)
      │     ARGV[3] = warn_threshold (24.00)
      │     
      │     local current = tonumber(redis.call('get', KEYS[1]) or '0')
      │     local projected = current + tonumber(ARGV[1])
      │     if projected > tonumber(ARGV[2]) then
      │       return 'BLOCKED'
      │     elseif projected > tonumber(ARGV[3]) then
      │       redis.call('incrbyfloat', KEYS[1], ARGV[1])
      │       return 'WARNING'
      │     else
      │       redis.call('incrbyfloat', KEYS[1], ARGV[1])
      │       return 'ALLOWED'
      │     end
      │
      ├─ ALLOWED → {"action": "allow"}
      ├─ WARNING → {"action": "allow"} + async Discord alert (debounced 1hr)
      └─ BLOCKED → {"action": "block", "reason": "Budget exceeded: $X/$30"}
```

**Hook Script**: `hermes-config/hooks/budget_check.py`
- Reads Redis at port 6380, DB5
- Uses existing `ToolCostTracker._TOOL_COSTS` for per-tool fixed costs
- Lua script ensures atomicity (no TOCTOU race)
- Post-tool-call reconciliation hook updates actual cost from response metadata

**Per-Tool Daily Cap Extension** (addresses Security Audit F-005):

The Lua script above enforces only the monthly cap. Per-tool daily caps are enforced by extending the script:

```lua
-- Extended Lua script with per-tool daily caps
local monthly_key = KEYS[1]                    -- "cost:current_month"
local daily_tool_key = KEYS[2]                 -- "tool:cost:{name}:YYYY-MM-DD"
local daily_global_key = KEYS[3]               -- "cost:daily:YYYY-MM-DD"
local estimated = tonumber(ARGV[1])
local monthly_cap = tonumber(ARGV[2])          -- 30.00
local warn_threshold = tonumber(ARGV[3])       -- 24.00
local daily_tool_cap = tonumber(ARGV[4])       -- per-tool daily cap (e.g., exa=5.00)
local daily_global_cap = tonumber(ARGV[5])     -- 10.00

local monthly = tonumber(redis.call('get', monthly_key) or '0')
local daily_tool = tonumber(redis.call('get', daily_tool_key) or '0')
local daily_global = tonumber(redis.call('get', daily_global_key) or '0')

-- Check all three caps
if (monthly + estimated) > monthly_cap then return 'MONTHLY_BLOCKED' end
if (daily_tool + estimated) > daily_tool_cap then return 'DAILY_TOOL_BLOCKED' end
if (daily_global + estimated) > daily_global_cap then return 'DAILY_GLOBAL_BLOCKED' end

-- All caps OK — deduct
redis.call('incrbyfloat', monthly_key, estimated)
redis.call('incrbyfloat', daily_tool_key, estimated)
redis.call('incrbyfloat', daily_global_key, estimated)
redis.call('expire', daily_tool_key, 172800)   -- 48h TTL
redis.call('expire', daily_global_key, 172800) -- 48h TTL

local projected = monthly + estimated
if projected > warn_threshold then return 'WARNING' end
return 'ALLOWED'
```

Budget hook maps return values: MONTHLY_BLOCKED → block, DAILY_TOOL_BLOCKED → block, DAILY_GLOBAL_BLOCKED → block, WARNING → allow + alert, ALLOWED → allow.

**Budget Dual-Write Prevention**: The Hermes budget_check.py hook and the existing FastMCP `BudgetEnforcer.record_and_check()` both write to the SAME Redis keys. During Phase 4 shadow mode (Hermes + OpenCode both running), this creates double-counting risk. Mitigation: budget_check.py uses a separate key prefix `hermes:cost:` during shadow mode, reconciled post-cutover.

**config.yaml addition** (applied by P4-001):
```yaml
hooks:
  pre_tool_call:
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/consent_gate.py"
      timeout_ms: 200
      on_failure: block
      priority: 90
    - event: pre_tool_call
      command: "python3 ~/.hermes/hooks/budget_check.py"
      timeout_ms: 150
      on_failure: block
      priority: 85
```

**Scope Note**: LLM token cost tracking (GAP-005) is OUT OF SCOPE for Phase 4. Only MCP tool costs are tracked. LLM costs remain tracked by 9Router's own metering.

**Acceptance**: Budget check blocks tool calls when monthly spend ≥ $30. Warning fires at $24. Redis Lua script executes atomically (verified via concurrent test).

### P4-004: Port Hybrid Tool Safety Guards to Hermes Terminal (6hr)

**Goal**: Port the multi-layered safety guards from 4 hybrid tools (shell_tool, docker_tool, git_tool, github) to Hermes terminal configuration and plugin guards.

**Source → Target Mapping**:

| Source (FastMCP) | Guard Layer | Target (Hermes) |
|-----------------|-------------|-----------------|
| `shell_tool.py` ALLOWED_COMMANDS | Whitelist | `terminal.allowed_commands` in config.yaml |
| `shell_tool.py` _INJECTION_CHARS | Injection detection | `hermes-config/hooks/hybrid_guards.py` pre_tool_call |
| `shell_tool.py` BLOCKED_PATTERNS | Hard-block | `terminal.blocked_commands` + UNRECOVERABLE_BLOCKLIST |
| `shell_tool.py` _BLOCKED_PATH_PATTERNS | Path isolation | `filesystem.blocked_paths` in config.yaml + `hybrid_guards.py` Aizanta path isolation (/home/aizanta, /etc/aizanta, /var/lib/aizanta) |
| `docker_tool.py` guinevere-net | Network isolation | `hybrid_guards.py` 5-layer guard (name regex, image check, forbidden patterns, network verify, sub-command block) |
| `docker_tool.py` forbidden patterns | Command block | `hybrid_guards.py` FORBIDDEN_PATTERNS + image name metacharacter rejection |
| `docker_tool.py` image name check | Image validation | `hybrid_guards.py` image name metacharacter rejection |
| `git_tool.py` force-push guard | Branch protection | `git.blocked_operations` + `hybrid_guards.py` main/master check |
| `github.py` rate-limit + backoff | API resilience | Plugin post_tool_call observer (log only) |

**`hybrid_guards.py`** handles guards that can't be expressed in YAML config:
- Shell injection character detection (`;`, `|`, `&&`, `` ` ``, `$()`)
- Docker 5-layer guard (matching docker_tool.py): (1) container name regex `^[a-z0-9_-]+$`, (2) image name metacharacter rejection, (3) FORBIDDEN_PATTERNS list (system prune, rm_all), (4) guinevere-net network membership verification for destructive ops, (5) runtime sub-command blocking
- Git force-push targeting main/master branch detection
- All guards return `{"action": "block", "reason": "..."}` on violation
- Aizanta isolation paths: `/home/aizanta`, `/etc/aizanta`, `/var/lib/aizanta` added to `filesystem.blocked_paths` in config.yaml AND validated in hybrid_guards.py shell path checker

**Acceptance**: Shell injection blocked. Docker commands without `guinevere-` prefix blocked. Git force-push to main/master blocked. All guards have unit tests.

### P4-005: Retain & Verify 7 FastMCP Custom Tools (2hr)

**Goal**: Verify the existing FastMCP server (`guinevere-mcp.service`) continues operating correctly with all 7 custom tools after Phase 4 changes.

**Verification Steps**:
1. `systemctl status guinevere-mcp` — service active and running
2. Verify all 7 tools registered: `python -c "from src.mcp.tools import _TOOL_MODULES; print(len(_TOOL_MODULES))"` → 7
3. `verify_matrix_completeness()` returns True for all 16 tools (7 custom + 5 native + 4 hybrid)
4. Test each custom tool invocation via MCP protocol:
   - `postgres_query("SELECT 1")` → returns result
   - `redis_get("test:key")` → returns value or nil
   - `obscura_navigate("https://example.com")` → returns markdown
   - `grep_app_search("useState(")` → returns code results
   - `context7_resolve("react")` → returns library info
   - `sequential_think("test chain")` → returns thought
   - `current_time("Asia/Jakarta")` → returns time string

**Hermes Integration**: Hermes connects to FastMCP server via MCP stdio transport. Add to `mcp_servers`:
```yaml
mcp_servers:
  # ... native servers ...
  fastmcp_custom:
    enabled: true
    command: "python"
    args: ["-m", "src.mcp.manager"]
    cwd: "/home/guinevere/code/guinevere"
    env_file: ".env.mcp"
    tools:
      - postgres_query
      - postgres_tables
      - postgres_describe
      - redis_get
      - redis_keys
      - redis_hgetall
      - redis_lrange
      - redis_set
      - redis_hset
      - redis_del
      - obscura_navigate
      - obscura_get_markdown
      - obscura_fill_form
      - obscura_click
      - grep_app_search
      - context7_resolve
      - context7_query
      - sequential_think
      - current_time
      - convert_time
      - days_in_month
      - relative_time
      - get_timestamp
      - get_week_year
```

**Tool Count Clarification** (addresses Compliance Audit F-002):
The 24 entries listed above are sub-operations exposed by the FastMCP MCP server, NOT separate tools. They map to 7 canonical tools per ADR-035 Pillar 4:
- postgres_query + postgres_tables + postgres_describe → **postgres_tool** (3 operations)
- redis_get + redis_keys + redis_hgetall + redis_lrange + redis_set + redis_hset + redis_del → **redis_tool** (7 operations)
- obscura_navigate + obscura_get_markdown + obscura_fill_form + obscura_click → **obscura_cdp** (4 operations)
- grep_app_search → **grep_app** (1 operation)
- context7_resolve + context7_query → **context7** (2 operations)
- sequential_think → **sequential_thinking** (1 operation)
- current_time + convert_time + days_in_month + relative_time + get_timestamp + get_week_year → **time_tools** (6 operations)

P4-007 audit check #1 verifies the collapse from 24 MCP operations to 16 canonical tools.

**Acceptance**: All 7 tools respond correctly via Hermes CLI. FastMCP service health check passes. No regressions in existing tool behavior.

### P4-006: Build Plugin Startup Gate (3hr)

**Goal**: Create a startup wrapper that enforces `critical: true` semantics for Hermes plugins, since Hermes v0.15.2 uses fail-open plugin loading.

**Problem** (from R4-007): Hermes catches plugin registration errors, logs them, and continues. If `auth_overlay` fails to load, Hermes proceeds without auth enforcement — a CRITICAL safety violation.

**Solution**: `scripts/startup_gate.py` — wrapper script that:
1. Imports and validates all critical plugins BEFORE starting Hermes
2. If any critical plugin fails validation → exit 1, do NOT start Hermes
3. Replaces direct `hermes gateway run` in systemd service

**Implementation**:
```python
#!/usr/bin/env python3
"""Startup gate — validates all critical plugins before Hermes starts."""

import sys
import importlib
import logging

CRITICAL_PLUGINS = [
    "auth_overlay",
    "guinevere_safety",
]

def validate_plugins() -> bool:
    errors = []
    for plugin_name in CRITICAL_PLUGINS:
        try:
            plugin_dir = Path.home() / ".hermes" / "plugins" / plugin_name
            if not plugin_dir.exists():
                errors.append(f"Plugin directory missing: {plugin_dir}")
                continue
            
            # Validate manifest.yaml exists and is parseable
            manifest = plugin_dir / "manifest.yaml"  # Existing guinevere_safety uses manifest.yaml, not plugin.yaml
            if not manifest.exists():
                errors.append(f"Missing manifest.yaml: {plugin_name}")
                continue
            
            # Attempt import of __init__.py
            spec = importlib.util.spec_from_file_location(
                plugin_name, plugin_dir / "__init__.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Verify register() function exists
            if not hasattr(module, "register"):
                errors.append(f"Missing register(): {plugin_name}")
                
        except Exception as e:
            errors.append(f"Plugin {plugin_name} failed validation: {e}")
    
    if errors:
        for err in errors:
            logging.error(f"STARTUP_GATE: {err}")
        return False
    return True

if __name__ == "__main__":
    if not validate_plugins():
        print("CRITICAL: Plugin validation failed. Hermes will NOT start.", file=sys.stderr)
        sys.exit(1)
    
    print("STARTUP_GATE: All critical plugins validated. Starting Hermes...")
    os.execvp("hermes", ["hermes", "gateway", "run", "--accept-hooks"])
```

**Systemd Integration**: Modify `scripts/hermes-gateway.service`:
```ini
# BEFORE:
ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes gateway run --accept-hooks

# AFTER:
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python3 /home/guinevere/code/guinevere/scripts/startup_gate.py
```

**Acceptance**: Hermes refuses to start if auth_overlay or guinevere_safety plugin is missing/broken. Systemd service fails with clear error message. Unit tests cover: plugin missing, manifest.yaml missing, register() missing, import error.

### P4-007: Security Audit All 16 Tools (4hr)

**Goal**: Comprehensive security audit verifying all 16 tools enforce correct auth levels, with no bypass paths.

**Audit Checklist**:

| # | Check | Method | PASS Criteria |
|---|-------|--------|---------------|
| 1 | Auth matrix YAML matches Python registry | Diff `config.yaml` auth_matrix vs `src/mcp/auth_matrix.py` AUTH_MATRIX | 100% match on all 16 tools × all operations |
| 2 | All READ_AUTO tools pass without approval | Invoke each, verify no approval prompt | 8 tools pass immediately |
| 3 | All WRITE_NOTIFY tools log notification | Invoke write ops, verify Discord/Gotify event | Notification event logged |
| 4 | All DESTRUCTIVE_APPROVAL tools require approval | Invoke destructive ops, verify block+webhook | Approval prompt appears, 5min timeout |
| 5 | All FORBIDDEN operations hard-blocked | Invoke forbidden ops, verify block+audit | Block with no approval option, audit logged |
| 6 | Budget enforcement blocks at $30 | Simulate $30 spend, verify block | Tool call blocked with budget reason |
| 7 | Budget enforcement warns at $24 | Simulate $24 spend, verify warning | Warning sent, tool call allowed |
| 8 | Shell injection patterns blocked | Test `;`, `\|`, `&&`, `$()`, backtick | All injection attempts blocked |
| 9 | Docker non-guinevere containers blocked | Test `docker ps -a` on non-guinevere container | Blocked |
| 10 | Git force-push to main/master blocked | Test `git push --force origin main` | Blocked |
| 11 | Plugin startup gate rejects broken plugin | Temporarily break auth_overlay, verify Hermes won't start | Hermes fails to start with clear error |
| 12 | FastMCP custom tools still functional | Invoke all 7 custom tools via Hermes | All 7 respond correctly |
| 13 | Aizanta isolation maintained | Verify no port/DB/network overlap | Redis 6380, PG 5433, guinevere-net only |
| 14 | No secrets in logs/artifacts | Grep logs for token/key patterns | Zero matches |
| 15 | NFR-P05 latency baseline | Capture baseline latency for each of 16 tools BEFORE Phase 4 changes. Compare post-migration latency. | All tools within +10% of baseline |

**Acceptance**: All 14 checks PASS. Audit report written to `docs/setup-evidence/phase-4/auditor-gate.md`.

### P4-008: End-to-End Integration Test Suite (4hr)

**Goal**: Full end-to-end test exercising all 16 tools through Hermes CLI, verifying the complete tool pipeline from invocation to result.

**Test Categories**:

1. **Native Tools (5)**: brave_search, exa_search, fetch, websearch, filesystem
   - Invoke via `hermes tool web brave_search "test query"`
   - Verify result format, latency < 5s, auth level READ_AUTO applied

2. **Hybrid Tools (4)**: shell, docker, git, github
   - Invoke allowed commands → verify execution
   - Invoke blocked commands → verify rejection
   - Invoke destructive commands → verify approval flow

3. **Custom Tools (7)**: postgres, redis, obscura, grep_app, context7, sequential_thinking, time
   - Invoke each via Hermes → FastMCP bridge
   - Verify correct results and auth level enforcement

4. **Cross-Cutting Concerns**:
    - Budget enforcement across multiple sequential tool calls
    - Auth overlay priority ordering (runs before consent_gate)
    - Plugin startup gate with all plugins valid
    - Aizanta isolation (no cross-contamination during tool execution)

5. **NFR-P05 Latency Regression**:
    - For each of 16 tools, compare execution time against baseline captured in P4-007 check #15
    - Flag any tool exceeding +10% of baseline
    - Report in integration test output

**Test Execution**:
```bash
cd /home/guinevere/code/guinevere
python -m pytest tests/hermes/test_integration_e2e.py -v --timeout=300
```

**Acceptance**: All integration tests pass. Total execution time < 10 minutes. Zero flaky tests.

---

## §9 Per-Step Verification Scaffold

### P4-001: Configure 5 Hermes Native MCP Servers

| Field | Value |
|-------|-------|
| **Expected Files** | `hermes-config/config.yaml` (modified) |
| **Forbidden Patterns** | `as any`, `@ts-ignore`, `# type: ignore`, hardcoded secrets, port 6379, port 5432 |
| **Required Commands** | `hermes config validate` → exit 0; `hermes mcp list` → shows 5 servers enabled |
| **Evidence Requirements** | `docs/setup-evidence/phase-4/P4-001-verification.md`, config.yaml diff |
| **Hard Rejection Criteria** | Any MCP server missing, any tool list mismatch with ADR-035, `plugins.enabled` missing auth_overlay, config validation fails |

### P4-002: Build Auth Overlay Plugin

| Field | Value |
|-------|-------|
| **Expected Files** | `hermes-config/plugins/auth_overlay/__init__.py`, `manifest.yaml`, `auth_handler.py`, `approval_handler.py`, `notify_handler.py`, `forbidden_handler.py`, `tests/hermes/test_auth_overlay.py` |
| **Forbidden Patterns** | `as any`, `@ts-ignore`, `# type: ignore`, `except:`, empty catch, hardcoded tokens, `shell=True` in subprocess, `print()` instead of `structlog` |
| **Required Commands** | `python -m pytest tests/hermes/test_auth_overlay.py -v` → exit 0; `hermes plugin list` → shows auth_overlay |
| **Evidence Requirements** | `docs/setup-evidence/phase-4/P4-002-verification.md`, test output, plugin load confirmation |
| **Hard Rejection Criteria** | Any auth level not enforced, FORBIDDEN operation not blocked, approval timeout not fail-closed, plugin crashes on malformed input, no tests for all 4 auth levels |

### P4-003: Integrate Budget Enforcement

| Field | Value |
|-------|-------|
| **Expected Files** | `hermes-config/hooks/budget_check.py`, `hermes-config/hooks/budget_lua.py`, `tests/hermes/test_budget_hook.py` |
| **Forbidden Patterns** | `as any`, `@ts-ignore`, `# type: ignore`, `except:`, hardcoded Redis port (must read from env/config), non-atomic check-then-increment |
| **Required Commands** | `python -m pytest tests/hermes/test_budget_hook.py -v` → exit 0; Redis Lua script test with concurrent calls → zero TOCTOU violations |
| **Evidence Requirements** | `docs/setup-evidence/phase-4/P4-003-verification.md`, Lua script content, concurrent test results |
| **Hard Rejection Criteria** | Budget not enforced at $30, warning not fired at $24, Lua script not atomic, Redis connection hardcoded to wrong port, no concurrent test |

### P4-004: Port Hybrid Tool Safety Guards

| Field | Value |
|-------|-------|
| **Expected Files** | `hermes-config/hooks/hybrid_guards.py`, `tests/hermes/test_hybrid_guards.py` |
| **Forbidden Patterns** | `as any`, `@ts-ignore`, `# type: ignore`, `except:`, `shell=True` in subprocess, hardcoded container names (must validate prefix) |
| **Required Commands** | `python -m pytest tests/hermes/test_hybrid_guards.py -v` → exit 0 |
| **Evidence Requirements** | `docs/setup-evidence/phase-4/P4-004-verification.md`, guard test results |
| **Hard Rejection Criteria** | Shell injection not blocked, Docker non-guinevere container not blocked, Git force-push to main not blocked, any guard missing unit test |

### P4-005: Retain & Verify 7 FastMCP Custom Tools

| Field | Value |
|-------|-------|
| **Expected Files** | No new files. Verification report only: `docs/setup-evidence/phase-4/P4-005-verification.md` |
| **Forbidden Patterns** | N/A (no code changes) |
| **Required Commands** | `systemctl status guinevere-mcp` → active; `python -c "from src.mcp.auth_matrix import verify_matrix_completeness; assert verify_matrix_completeness()"` → exit 0 |
| **Evidence Requirements** | `docs/setup-evidence/phase-4/P4-005-verification.md`, service status, tool invocation results |
| **Hard Rejection Criteria** | FastMCP service down, any of 7 tools not responding, `verify_matrix_completeness()` returns False |

### P4-006: Build Plugin Startup Gate

| Field | Value |
|-------|-------|
| **Expected Files** | `scripts/startup_gate.py`, `scripts/startup_gate_test.py` |
| **Forbidden Patterns** | `as any`, `@ts-ignore`, `# type: ignore`, `except:`, `os.system()`, silently continuing on plugin failure |
| **Required Commands** | `python -m pytest scripts/startup_gate_test.py -v` → exit 0; `python scripts/startup_gate.py --validate-only` → exit 0 with all plugins present; exit 1 with broken plugin |
| **Evidence Requirements** | `docs/setup-evidence/phase-4/P4-006-verification.md`, test output, failure mode test |
| **Hard Rejection Criteria** | Hermes starts despite broken critical plugin, startup gate silently swallows errors, no test for missing plugin scenario |

### P4-007: Security Audit All 16 Tools

| Field | Value |
|-------|-------|
| **Expected Files** | `tests/hermes/test_security_audit.py`, `docs/setup-evidence/phase-4/verification.md`, `docs/setup-evidence/phase-4/auditor-gate.md` |
| **Forbidden Patterns** | N/A (audit step) |
| **Required Commands** | `python -m pytest tests/hermes/test_security_audit.py -v` → exit 0; all 14 audit checks PASS |
| **Evidence Requirements** | `docs/setup-evidence/phase-4/verification.md`, `docs/setup-evidence/phase-4/auditor-gate.md` |
| **Hard Rejection Criteria** | Any of 14 audit checks FAIL, auth matrix mismatch between YAML and Python, FORBIDDEN operation not blocked, secrets found in logs |

### P4-008: End-to-End Integration Test Suite

| Field | Value |
|-------|-------|
| **Expected Files** | `tests/hermes/test_integration_e2e.py` |
| **Forbidden Patterns** | `as any`, `@ts-ignore`, `# type: ignore`, `except:`, `time.sleep()` > 5s, hardcoded API keys |
| **Required Commands** | `python -m pytest tests/hermes/test_integration_e2e.py -v --timeout=300` → exit 0 |
| **Evidence Requirements** | `docs/setup-evidence/phase-4/P4-008-verification.md`, full test output |
| **Hard Rejection Criteria** | Any integration test FAIL, total execution > 10 minutes, flaky test detected, Aizanta isolation violated during test |

---

## §10 Token/Secret Handling

| Secret | Storage | Access Method | Phase 4 Step |
|--------|---------|---------------|--------------|
| `BRAVE_API_KEY` | `.env.mcp` (SOPS/age) | `os.environ["BRAVE_API_KEY"]` | P4-001 (config ref), P4-005 (FastMCP) |
| `EXA_API_KEY` | `.env.mcp` (SOPS/age) | `os.environ["EXA_API_KEY"]` | P4-001 (config ref), P4-005 (FastMCP) |
| `NINEROUTER_API_KEY` | `.env` (SOPS/age) | `os.environ["NINEROUTER_API_KEY"]` via `llm.api_key_env` | No changes |
| `DISCORD_APPROVAL_WEBHOOK` | `.env` (SOPS/age) | `os.environ["DISCORD_APPROVAL_WEBHOOK"]` via `approval.discord_webhook_url_env` | P4-002 (auth overlay reads) |
| `DISCORD_WEBHOOK_URL` | `.env` (SOPS/age) | `os.environ["DISCORD_WEBHOOK_URL"]` | P4-002 (notify handler) |
| `GOTIFY_TOKEN` | `.env` (SOPS/age) | `os.environ["GOTIFY_TOKEN"]` | P4-002 (fallback handler) |
| `REDIS_URL` | `.env.mcp` (SOPS/age) | `redis://localhost:6380/5` | P4-003 (budget Lua) |
| `DATABASE_URL` | `.env.mcp` (SOPS/age) | `postgresql://guinevere@localhost:5433/guinevere` | P4-005 (FastMCP postgres tool) |
| `GITHUB_PAT` | `.env.mcp` (SOPS/age) | `os.environ["GITHUB_PAT"]` | P4-005 (FastMCP github tool) |

**Rule**: NO secret is hardcoded in any file. ALL secrets read from environment variables sourced from SOPS/age-encrypted `.env` / `.env.mcp`. Auth overlay plugin reads secrets via `os.environ`, never from config.yaml.

---

## §11 Evidence Paths

| Evidence Type | Path Pattern |
|--------------|-------------|
| Per-step verification | `docs/setup-evidence/phase-4/P4-{NNN}-verification.md` |
| Master verification | `docs/setup-evidence/phase-4/verification.md` |
| Auditor gate | `docs/setup-evidence/phase-4/auditor-gate.md` |
| Batch plan (this file) | `docs/setup-evidence/phase-4/batch-plan-phase-4.md` |
| Research reports | `research-reports/phase-4-planning/R4-{NNN}-*.md` (8 files) |
| Test output | Inline in per-step verification reports |

---

## §12 Auditor Matrix

| Step | Auditor Type | Focus Areas | Parallel With |
|------|-------------|-------------|---------------|
| P4-001 | ADR-035 Compliance | MCP server config matches Pillar 4, tool lists correct, plugins.enabled includes auth_overlay | P4-005 |
| P4-002 | Security | Auth matrix enforcement complete, FORBIDDEN 100% blocked, approval fail-closed, no bypass paths | — |
| P4-003 | Security + FinOps | Budget enforcement accurate, Lua atomicity, thresholds match FinOps v1.1 ($24/$30) | P4-004, P4-006 |
| P4-004 | Security | Hybrid guards cover all injection/blocking patterns from source tools, no regression | P4-003, P4-006 |
| P4-005 | Technical Accuracy | All 7 tools functional, FastMCP service healthy, no regressions | P4-001 |
| P4-006 | Security | Startup gate truly prevents Hermes start without critical plugins, no silent failures | P4-003, P4-004 |
| P4-007 | All three | Comprehensive audit, all 14 checks documented | — |
| P4-008 | Technical Accuracy | Integration tests cover all 16 tools, no flaky tests, Aizanta isolation verified | — |

**3 Specialist Auditors for Batch Plan Review**:
1. **ADR-035 Compliance Auditor** — Verifies plan matches ADR-035 Pillar 4 exactly, no scope creep/deficit
2. **Security Auditor** — Verifies auth matrix, budget, hybrid guards, startup gate have no bypass vectors
3. **Technical Accuracy Auditor** — Verifies file paths, commands, dependencies, scaffold criteria are executable

---

## §13 Gap Mapping Rationale

| Gap | Phase 4 Step | Rationale |
|-----|-------------|-----------|
| GAP-001: Budget not in pre_tool_call | P4-003 | Directly addressed. Redis Lua atomic check wired into hook. |
| GAP-002: critical:true not native Hermes | P4-006 | Custom startup wrapper provides equivalent semantics. |
| GAP-003: Terminal safety porting | P4-004 | Shell/Docker/Git/GitHub guards ported to config + plugin. |
| GAP-004: FastMCP bridge not configured | P4-005 | MCP stdio transport configured in mcp_servers. |
| GAP-005: LLM cost tracking not in ToolCostTracker | **DEFERRED to Phase 6** | LLM routing (Phase 6) handles token-level cost tracking. Phase 4 tracks only MCP tool costs. 9Router provides LLM metering independently. |

---

## §14 Rollback Plan

| Scenario | Procedure | Time Estimate |
|----------|-----------|---------------|
| Universal kill-switch | `sudo systemctl stop hermes-gateway` — ALWAYS the first step before any rollback. Prevents Hermes from processing tool calls during config changes. | < 5s |
| Auth overlay plugin crashes | `sudo systemctl stop hermes-gateway && `rm -rf ~/.hermes/plugins/auth_overlay/` + remove from `plugins.enabled` + `sudo systemctl restart hermes-gateway` | < 2 min |
| Budget hook blocks all tools | `sudo systemctl stop hermes-gateway && `Remove `budget_check.py` entry from `hooks.pre_tool_call` in config.yaml + `sudo systemctl restart hermes-gateway` | < 2 min |
| Hybrid guards too restrictive | `sudo systemctl stop hermes-gateway && `Revert `hybrid_guards.py` + restore original `terminal.allowed_commands` in config.yaml + restart | < 3 min |
| FastMCP bridge fails | `sudo systemctl stop hermes-gateway && `Remove `fastmcp_custom` from `mcp_servers` in config.yaml + `sudo systemctl restart hermes-gateway` + `sudo systemctl restart guinevere-mcp` | < 2 min |
| Startup gate prevents Hermes start | `sudo systemctl stop hermes-gateway && `Revert `hermes-gateway.service` to direct `hermes gateway run` + `sudo systemctl daemon-reload` + restart | < 2 min |
| Full Phase 4 rollback | `sudo systemctl stop hermes-gateway && `Per ADR-035 Appendix D: `hermes mcp remove web filesystem terminal git fetch` + `rm -rf ~/.hermes/plugins/auth_overlay/` + `rm -f ~/.hermes/hooks/budget_check.py ~/.hermes/hooks/budget_lua.py ~/.hermes/hooks/hybrid_guards.py` + `git checkout -- hermes-config/config.yaml` + revert systemd service + `sudo systemctl daemon-reload` + `sudo systemctl restart hermes-gateway` + `sudo systemctl restart guinevere-mcp` | < 5 min |

**Rollback Safety**: Every rollback scenario starts with `sudo systemctl stop hermes-gateway` to prevent Hermes from processing tool calls during configuration changes. All Phase 4 changes are additive (new files + config additions). No destructive modifications to existing production code. `git checkout --` restores any modified files. FastMCP server and all 7 custom tools remain untouched throughout.

---

## §15 Caveats and Known Risks

1. **Hermes fail-open model**: The `critical: true` enforcement via startup wrapper is a pre-flight check only. If a plugin crashes AFTER startup (runtime error), Hermes will still skip it. Mitigation: auth_overlay plugin catches ALL exceptions and returns `{"action": "block"}` on error — fail-closed at runtime even if Hermes considers the plugin "failed".

2. **Auth matrix single-source migration**: BD-006 changed from dual-source (YAML + Python) to single-source (Python `auth_matrix.py` via import). The YAML `auth_matrix` section in config.yaml is now a REFERENCE-ONLY convenience block, not enforced at runtime. P4-007 audit verifies the config.yaml YAML section is either removed or explicitly marked as non-authoritative. If any Hermes subsystem reads the YAML auth_matrix independently of the plugin, that path must be identified and redirected.

3. **Budget estimation accuracy**: ToolCostTracker uses fixed costs per tool (e.g., Exa $0.01/query). Actual costs vary by response size. Post-call reconciliation corrects this, but intra-call blocking uses estimates. Mitigation: conservative estimates (round up 20%).

4. **FastMCP `sys.path` hack**: The `manager.py` sys.path manipulation to avoid `src/mcp` shadowing the pip `mcp` package is fragile. If Hermes changes Python path handling, this could break. Mitigation: P4-005 verification catches this; long-term fix deferred to Phase 7 (Hardening).

5. **Hermes terminal != shell_tool**: Hermes terminal tool has its own command handling that differs from `shell_tool.py`. Some guard patterns (e.g., injection character detection) may need adaptation. Mitigation: `hybrid_guards.py` handles Hermes-specific input format.

6. **LLM cost tracking gap**: Phase 4 does NOT track LLM token costs. This is explicitly deferred to Phase 6 (LLM Routing). 9Router provides independent metering.

7. **ADR-034 missing**: Referenced in ADR Index but file not found at `adr/ADR-034-post-mvp-phase-restructure.md`. Pre-existing doc gap. Does not affect Phase 4 implementation.

8. **Plugin priority ordering**: Auth overlay priority 100 runs before consent_gate priority 90. This means auth check happens first. If auth blocks a tool, consent gate never runs. This is correct behavior — don't check consent for a tool that's already forbidden.

9. **Concurrent tool calls**: Multiple sub-agents may invoke tools simultaneously. Redis Lua script ensures atomic budget deduction. Auth overlay is stateless per-call (no shared state). No concurrency issues expected.

10. **Runtime watchdog daemon deferred**: ADR-035 R-004/R-014 mitigations mention "independent audit daemon verifies plugin presence every 60s." This is NOT implemented in Phase 4 — it is deferred to Phase 7 (Hardening + Monitoring). Phase 4 relies on startup gate (P4-006) + runtime fail-closed (auth_overlay exception handling + guinevere_safety wrapper).

---

## §16 Execution Checklist

### Pre-Execution

- [ ] Phase 2 (Discord Gateway) batch plan PASS
- [ ] Phase 3 (Memory Bridge) batch plan PASS (recommended, not hard gate per ADR-035)
- [ ] All 8 research reports written and parent-read
- [ ] Batch plan v1.0 reviewed by 3 auditors — all PASS
- [ ] Collision scan verified — no unresolved conflicts
- [ ] VPS state verified — Redis 6380, PG 5433, guinevere-net all operational
- [ ] `.env` and `.env.mcp` SOPS/age encrypted with all required secrets
- [ ] `hermes-gateway.service` and `guinevere-mcp.service` both active

### Wave 1 (P4-001 + P4-005 parallel)

- [ ] P4-001: `hermes config validate` → exit 0
- [ ] P4-001: `hermes mcp list` → 5 native servers enabled
- [ ] P4-001: `plugins.enabled` includes auth_overlay
- [ ] P4-005: `systemctl status guinevere-mcp` → active
- [ ] P4-005: All 7 custom tools respond via MCP
- [ ] P4-005: `verify_matrix_completeness()` → True

### Wave 2 (P4-002 sequential)

- [ ] P4-002: All 6 plugin files created
- [ ] P4-002: `python -m pytest tests/hermes/test_auth_overlay.py -v` → exit 0
- [ ] P4-002: All 4 auth levels tested and PASS
- [ ] P4-002: FORBIDDEN operations 100% blocked in tests
- [ ] P4-002: Plugin loads in Hermes without errors

### Wave 3 (P4-003 + P4-004 + P4-006 parallel)

- [ ] P4-003: Redis Lua script executes atomically
- [ ] P4-003: Budget blocks at $30, warns at $24
- [ ] P4-003: `python -m pytest tests/hermes/test_budget_hook.py -v` → exit 0
- [ ] P4-004: Shell injection blocked (`;`, `|`, `&&`, `$()`, backtick)
- [ ] P4-004: Docker non-guinevere containers blocked
- [ ] P4-004: Git force-push to main/master blocked
- [ ] P4-004: `python -m pytest tests/hermes/test_hybrid_guards.py -v` → exit 0
- [ ] P4-006: Startup gate rejects broken plugin
- [ ] P4-006: Startup gate allows valid plugins
- [ ] P4-006: `python -m pytest scripts/startup_gate_test.py -v` → exit 0

### Wave 4 (P4-007 sequential)

- [ ] P4-007: Auth matrix YAML matches Python registry (100%)
- [ ] P4-007: All 14 audit checks PASS
- [ ] P4-007: No secrets found in logs
- [ ] P4-007: Aizanta isolation verified
- [ ] P4-007: `docs/setup-evidence/phase-4/verification.md` written
- [ ] P4-007: `docs/setup-evidence/phase-4/auditor-gate.md` written

### Wave 5 (P4-008 sequential)

- [ ] P4-008: `python -m pytest tests/hermes/test_integration_e2e.py -v --timeout=300` → exit 0
- [ ] P4-008: All 16 tools tested end-to-end
- [ ] P4-008: Total execution < 10 minutes
- [ ] P4-008: Zero flaky tests

### Post-Execution

- [ ] All per-step verification reports written and parent-read
- [ ] Master verification.md and auditor-gate.md written
- [ ] 3 specialist auditors PASS on final implementation
- [ ] Evidence paths complete per §11
- [ ] Rollback procedure tested (at least one scenario)
- [ ] ADR-035 Phase 4 marked COMPLETE in ADR Index
- [ ] `docs/README.md` updated with Phase 4 evidence links

---

## §17 Footer

### Versioning

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-05 | Guinevere (planner gate) | Initial batch plan. 8 atomic steps, 5 waves, 8 research inputs. Awaiting 3-auditor review. |
| 1.1 | 2026-06-05 | Guinevere (auditor fix pass) | Applied 14 fixes from 3-auditor review: BD-006 single-source auth (Security F-001/F-010), _extract_operation spec (F-002), 5-layer docker guards (F-007), guinevere_safety fail-closed (F-008), Aizanta paths (F-006), Phase 3 dep removed (Compliance F-004), tool-list annotation (Compliance F-002), hermes gateway stop rollback (Compliance F-006), NFR-P05 baseline (Compliance F-005), per-tool daily caps (Security F-005), unknown tool fail-closed (Security F-004), manifest.yaml naming (Tech Accuracy), fetch_url naming (Tech Accuracy), watchdog deferred to Phase 7 (Compliance F-007). |

### Approval Status

**ALL AUDITORS PASS v1.1** — Approved for implementation:
- [x] ADR-035 Compliance Auditor → PASS (`AUDIT-adr035-compliance-v1.1.md`)
- [x] Security Auditor → PASS (`AUDIT-security-v1.1.md`)
- [x] Technical Accuracy Auditor → PASS (v1.0 findings resolved in v1.1 fixes)

### Addendum: CRITICAL Finding — Hermes Fail-Open Model

> **R4-007 discovered that `critical: true` and `on_failure: block` are NOT native Hermes v0.15.2 plugin flags.** Hermes uses a fail-open, implicit-trust model for Python plugins. Plugin crashes are caught, logged, and skipped — the agent continues without the plugin.
>
> **Impact on ADR-035**: ADR-035 Pillar 4 specifies `critical: true` on the auth overlay plugin. This flag has no effect in Hermes. Phase 4 compensates with:
> 1. **Startup gate** (P4-006): Pre-flight validation that refuses to start Hermes if critical plugins fail.
> 2. **Runtime fail-closed** (P4-002): Auth overlay catches ALL exceptions and returns `{"action": "block"}` — even if Hermes considers the plugin "failed", the last successful hook return is "block".
>
> **Recommendation**: Add ADR-035 amendment noting Hermes fail-open limitation and the startup gate workaround.

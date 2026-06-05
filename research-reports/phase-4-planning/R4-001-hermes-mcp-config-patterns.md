# R4-001: Hermes MCP Configuration Patterns & Current State Analysis

**Date:** 2026-06-05  
**Phase:** Phase 4 (MCP + Tools) Migration Planning  
**Scope:** Read-only research of existing Hermes configuration, MCP server definitions, plugin architecture, and systemd/script references.  
**Target Output:** `research-reports/phase-4-planning/R4-001-hermes-mcp-config-patterns.md`

---

## 1. Executive Summary

The codebase already contains a well-defined Hermes configuration structure that **partially pre-configures the Phase 4 migration**. The primary Hermes configuration file (`hermes-config/config.yaml`) explicitly defines the 5 native MCP servers (`web`, `filesystem`, `terminal`, `git`, `fetch`) exactly as specified in ADR-035. The legacy custom MCP tools are currently managed via a FastMCP server (`src/mcp/manager.py`), with a comprehensive 4-level authorization matrix documented in `docs/60-persona/62-MCPConfigGuide_v1.0.md`. A working Hermes plugin architecture exists (`hermes-config/plugins/guinevere_safety/`), demonstrating the `critical: true` plugin loading pattern required for the Phase 4 `auth_overlay` plugin.

---

## 2. Hermes Configuration Structure

### Primary Config File
**Path:** `hermes-config/config.yaml` (327 lines)  
**Purpose:** Canonical Hermes Agent Gateway configuration, deployed to `~/.hermes/config.yaml` on the VPS.

### Key Sections Relevant to Phase 4:
1. **`mcp_servers`**: Explicitly defines the 5 Hermes-native toolsets:
   - `web`: `brave_search`, `exa_search`, `fetch_url`, `websearch`
   - `filesystem`: Rooted at `/home/guinevere/code/guinevere`, with explicit `allowed_paths` and `blocked_paths` (`/etc`, `/root`, `/.ssh`)
   - `terminal`: Whitelist of allowed commands (`ls`, `cat`, `python`, `git`, etc.) and blocked destructive commands (`rm`, `dd`, `mkfs`, `shutdown`, etc.)
   - `git`: Allowed operations (`status`, `diff`, `commit`, `push`) and blocked operations (`push --force`, `reset --hard`)
   - `fetch`: 30s timeout, 10MB max response size.
2. **`auth_matrix`**: Maps every tool and operation to the 4-level authorization model (`READ_AUTO`, `WRITE_NOTIFY`, `DESTRUCTIVE_APPROVAL`, `FORBIDDEN`).
3. **`hooks`**: Defines shell-based defense-in-depth hooks (`pre_tool_call` for `consent_gate.py`, `post_tool_call` for `dnr_filter.py`).
4. **`approval`**: Discord webhook configuration for `DESTRUCTIVE_APPROVAL` operations (5-minute timeout, fail-closed).

---

## 3. Existing MCP Server Definitions

### A. Legacy Custom MCP (To be partially retired)
**Path:** `src/mcp/manager.py`  
**Architecture:** FastMCP server factory (`create_server()`). Dynamically registers tools via `src/mcp/tools/`.  
**Current Tool Inventory (16 tools):**
- **Migrating to Hermes Native (5):** `brave_search`, `exa_search`, `websearch`, `fetch`, `filesystem`, `git_tool`, `github`, `shell_tool`, `docker_tool` *(Note: some consolidation occurs here, e.g., shell+docker → terminal)*
- **Remaining Custom FastMCP (7):** `postgres_tool`, `redis_tool`, `obscura_cdp`, `grep_app`, `context7`, `sequential_thinking`, `time_tools`

### B. MCP Configuration Guide
**Path:** `docs/60-persona/62-MCPConfigGuide_v1.0.md`  
**Purpose:** Authoritative documentation of the 4-level authorization matrix, tool specifications, rate limits, cost tracking, and fallback chains for all 16 tools. This document serves as the source of truth for the `auth_overlay` plugin logic.

---

## 4. Plugin Architecture

### Existing Plugin: `guinevere_safety`
**Path:** `hermes-config/plugins/guinevere_safety/`  
**Files:**
- `manifest.yaml`: Declares plugin metadata, `critical: true` flag, hook bindings (`pre_prompt`, `post_response`), and command handlers.
- `plugin.py`: Implements `GuinevereSafetyPlugin` class with `on_load()`, `inject_dynamic_state()`, and `update_state()` methods.
- `state_manager.py`: Manages Redis DB5 state for punishment, reward, distress, mood, and yandere levels.

**Relevance to Phase 4:** This proves the Hermes plugin system is operational in the codebase. The Phase 4 `auth_overlay` plugin will follow this exact same pattern:
1. `manifest.yaml` with `critical: true`.
2. Hook binding to `pre_tool_call` with `priority: 90`.
3. `on_load()` returning `False` to block Hermes startup if the auth matrix fails to initialize.

### Planned Plugin: `auth_overlay`
**Path:** `plugins/auth_overlay.py` (Planned, referenced in `docs/setup-evidence/hermes-migration/phase-4-mcp.md`)  
**Purpose:** Intercepts ALL tool calls (both Hermes native and custom FastMCP) to enforce the 4-level auth matrix before execution.

---

## 5. Systemd & Script References

### Systemd Service
**Path:** `scripts/hermes-gateway.service`  
**Key Directives:**
- `ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes gateway run --accept-hooks`
- `EnvironmentFile=/home/guinevere/.hermes/.env`
- `ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence /home/guinevere/.hermes /home/guinevere/.local/state`
- Resource limits: `MemoryMax=1G`, `CPUQuota=100%`

### Migration Scripts
- `scripts/create_hermes_env.sh`: Sets up the `.hermes/.env` file with SOPS-decrypted secrets.
- `scripts/cutover.sh`: Orchestrates the stop/start sequence between `guinevere-discord.service` (legacy) and `hermes-gateway.service`.
- `scripts/pre_cutover_backup.sh`: Triggers `hermes backup --full` before migration steps.

---

## 6. Hermes Binary & Installation References

- **Version:** `hermes-agent v0.15.2` (Nous Research)
- **Expected Binary Path:** `/home/guinevere/code/guinevere/.venv/bin/hermes`
- **Key CLI Commands Used in Codebase:**
  - `hermes gateway run --accept-hooks`
  - `hermes mcp add <server> --config <path>`
  - `hermes mcp list`
  - `hermes doctor --report`
  - `hermes backup --full --destination idcloudhost`
  - `hermes plugin trigger guinevere_safety ritual <name>`

---

## 7. Config Schema Summary (YAML)

The target `config/hermes/mcp-servers.yaml` schema for Phase 4 is already partially defined in `hermes-config/config.yaml` and `docs/setup-evidence/hermes-migration/phase-4-mcp.md`:

```yaml
mcp_servers:
  web:
    enabled: true
    tools: [brave_search, exa_search, fetch_url, websearch]
  filesystem:
    enabled: true
    root_path: "/home/guinevere/code/guinevere"
    allowed_paths: ["/home/guinevere/code/guinevere", "/tmp/guinevere"]
    blocked_paths: ["/etc", "/root", "/home/guinevere/.ssh"]
  terminal:
    enabled: true
    allowed_commands: [ls, cat, head, tail, grep, find, wc, sort, uniq, python, pip, pytest, git, gh]
    blocked_commands: [rm, dd, mkfs, shutdown, reboot, poweroff, iptables, ufw, systemctl]
    timeout_seconds: 30
  git:
    enabled: true
    allowed_operations: [status, diff, log, branch, checkout, add, commit, push, pull]
    blocked_operations: [push --force, reset --hard, clean -fd]
  fetch:
    enabled: true
    timeout_seconds: 30
    max_response_size_mb: 10

plugins:
  auth_overlay:
    enabled: true
    path: "/home/guinevere/code/guinevere/plugins/auth_overlay.py"
    class: "AuthOverlayPlugin"
    priority: 90
    critical: true
    config:
      auth_matrix_path: "/home/guinevere/code/guinevere/config/hermes/auth_matrix.yaml"
      webhook_url: "${DISCORD_APPROVAL_WEBHOOK}"
      approval_timeout_ms: 300000
      on_timeout: "deny"
```

---

## 8. Actionable Insights for Phase 4 Migration

1. **Config Already Exists:** The `mcp_servers` and `auth_matrix` blocks are already present in `hermes-config/config.yaml`. Phase 4 implementation can largely consist of extracting these into dedicated files (`config/hermes/mcp-servers.yaml`, `config/hermes/auth_matrix.yaml`) as planned, rather than writing them from scratch.
2. **Plugin Blueprint Ready:** The `guinevere_safety` plugin provides a working, tested blueprint for the `auth_overlay` plugin. Copy the `manifest.yaml` structure and `on_load()` critical-fail pattern.
3. **Legacy Cleanup Scope:** Phase 4 must explicitly delete or deprecate `src/mcp/tools/brave_search.py`, `exa_search.py`, `fetch.py`, `websearch.py`, `filesystem.py`, and `git_tool.py`, while retaining the 7 custom tools (`postgres`, `redis`, `obscura`, `grep_app`, `context7`, `sequential_thinking`, `time_tools`).
4. **Auth Matrix Source of Truth:** Use `docs/60-persona/62-MCPConfigGuide_v1.0.md` §2.2 (Tool × Authorization Matrix) as the exact mapping source for the `auth_overlay.py` `AUTH_MATRIX` dictionary.
5. **Systemd Compatibility:** The `hermes-gateway.service` already includes `--accept-hooks` and proper `ReadWritePaths`. No systemd changes are required for Phase 4, only a service restart.

---

## 9. File Inventory Reference

| Category | Absolute Path | Relevance |
|---|---|---|
| **Hermes Config** | `C:\Users\faizz\guinevere\hermes-config\config.yaml` | Primary Hermes config with `mcp_servers` and `auth_matrix` blocks |
| **Hermes Config** | `C:\Users\faizz\guinevere\hermes-config\SOUL.md` | Static persona identity constitution |
| **Legacy MCP** | `C:\Users\faizz\guinevere\src\mcp\manager.py` | FastMCP server factory for custom tools |
| **MCP Docs** | `C:\Users\faizz\guinevere\docs\60-persona\62-MCPConfigGuide_v1.0.md` | 4-level auth matrix and 16-tool specifications |
| **Plugin** | `C:\Users\faizz\guinevere\hermes-config\plugins\guinevere_safety\manifest.yaml` | Blueprint for `critical: true` plugin loading |
| **Plugin** | `C:\Users\faizz\guinevere\hermes-config\plugins\guinevere_safety\plugin.py` | Blueprint for hook handlers (`pre_prompt`, `post_response`) |
| **Systemd** | `C:\Users\faizz\guinevere\scripts\hermes-gateway.service` | Hermes gateway systemd unit file |
| **Phase 4 Plan** | `C:\Users\faizz\guinevere\docs\setup-evidence\hermes-migration\phase-4-mcp.md` | Detailed step-by-step Phase 4 migration procedure |
| **ADR** | `C:\Users\faizz\guinevere\adr\ADR-035-hermes-migration.md` | Architectural decision for hybrid Hermes migration |

---
*End of Report*

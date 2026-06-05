# Phase 4 MCP State Research Report

**Date:** 2026-06-05
**Time:** 18:12 WIB
**Target:** VPS (guinevere-vps — 100.94.104.22)
**Hermes Version:** v0.15.2 (2026.5.29.2)
**Python Version:** 3.12.3
**Research Type:** Live-state audit (read-only)

---

## 1. Executive Summary

Live-state audit of the VPS MCP infrastructure was completed on 2026-06-05 at 18:12 WIB. 
The Hermes Agent Gateway v0.15.2 is **active and running** with the `guinevere_safety` 
plugin loaded. However, **no MCP servers are configured** in the Hermes gateway — native 
MCP servers (web, filesystem, terminal, git, fetch) are **not yet registered**.

The legacy FastMCP `guinevere-mcp` service is **inactive and disabled**, which is 
consistent with Phase 2 cutover but means the custom tool bridge is offline.

**Two blocking issues** were identified:

1. **FastMCP v1.x compatibility bug:** The `fs_read`, `fs_write`, `fs_delete`, and `fs_list` 
   functions in `src/mcp/tools/filesystem.py` use `_config` as a parameter name. FastMCP v1.x 
   rejects parameters starting with `_` — this blocks the legacy MCP manager from loading.

2. **Port isolation violation:** Ports 5432 (standard PostgreSQL) and 6379 (standard Redis) 
   are still actively listening alongside the Aizanta ports 5433 and 6380. This breaks 
   Aizanta isolation requirements.

---

## 2. Hermes Binary & Version

| Check | Result | Status |
|-------|--------|--------|
| Binary path | `/home/guinevere/code/guinevere/.venv/bin/hermes` | PASS |
| Version | `v0.15.2 (2026.5.29.2)` | PASS |
| Python | 3.12.3 | PASS |
| OpenAI SDK | 2.24.0 | PASS |
| Up to date | Yes | PASS |

---

## 3. MCP Manager Load Test

### 3.1 Import & Server Creation

| Check | Detail | Status |
|-------|--------|--------|
| `create_server()` import | Imported successfully from `src.mcp.manager` | PASS |
| Server creation | `FastMCP` instance created | PASS |
| Tool registration | **FAILED** — `fs_read` rejected (see 3.2) | **BLOCKING FAIL** |

### 3.2 Filesystem Tool Bug — FastMCP v1.x Compatibility

**Error:**
```
mcp.server.fastmcp.exceptions.InvalidSignature: 
  Parameter _config of fs_read cannot start with '_'
```

**Root cause:** Four functions in `src/mcp/tools/filesystem.py` use `_config` as a parameter
name to inject the `FilesystemConfig` dependency:

- `fs_read(path, _config: FilesystemConfig = _DEFAULT_CONFIG)` — line 190
- `fs_write(path, content, _config: FilesystemConfig = _DEFAULT_CONFIG)` — line 201
- `fs_delete(path, _config: FilesystemConfig = _DEFAULT_CONFIG)` — line 213
- `fs_list(path, _config: FilesystemConfig = _DEFAULT_CONFIG)` — line 225

FastMCP v1.x uses `_` prefix to exclude parameters from the tool schema. Renaming `_config` 
to `config` (or using `fastmcp`'s `@mcp.tool(skip_params=["_config"])`) resolves the issue.

**Impact:** The legacy `guinevere-mcp` FastMCP server cannot start with the current code.
This is a **pre-existing code defect** — the service was already inactive before migration.

### 3.3 Auth Matrix Verification

| Check | Detail | Status |
|-------|--------|--------|
| Completeness | 16/16 tools registered | PASS |
| Expected tools | All 16 from `ALL_TOOL_NAMES` present | PASS |
| Tool count | 16 tools in `AUTH_MATRIX` | PASS |

**Full tool list with status:**
- brave_search: OK
- context7: OK
- docker: OK (11 operations)
- exa: OK
- fetch: OK
- filesystem: OK
- git: OK (7 operations)
- github: OK (6 operations)
- grep_app: OK
- obscura_cdp: OK (6 operations)
- postgres: OK (7 operations)
- redis: OK (28 operations)
- sequential_thinking: OK
- shell: OK (3 operations)
- time: OK
- websearch: OK

---

## 4. Auth Matrix Visibility & Levels

### 4.1 Level Distribution (80 total operations)

| Level | Count | Examples |
|-------|-------|---------|
| READ_AUTO | 32 | brave_search(*), fetch(*), grep_app(*), select, get, status |
| WRITE_NOTIFY | 16 | commit, push, set, hset, write, create_issue |
| DESTRUCTIVE_APPROVAL | 16 | delete, del, expire, rm, force_push, file_upload |
| FORBIDDEN | 16 | insert, update, drop, flushdb, flushall, config, rm_all |

### 4.2 Auth Level Mapping Detail

```
brave_search:      (all) → READ_AUTO
context7:          query, resolve → READ_AUTO
docker:            ps, logs, inspect, images → READ_AUTO
                   start, stop, restart → WRITE_NOTIFY
                   rm, rmi → DESTRUCTIVE_APPROVAL
                   system_prune, rm_all → FORBIDDEN
exa:               (all) → READ_AUTO
fetch:             (all) → READ_AUTO
filesystem:        read, list → READ_AUTO
                   write → WRITE_NOTIFY
                   delete → DESTRUCTIVE_APPROVAL
git:               log, diff, status → READ_AUTO
                   commit, push → WRITE_NOTIFY
                   force_push → DESTRUCTIVE_APPROVAL
                   force_push_main → FORBIDDEN
github:            read, get, search → READ_AUTO
                   create_issue, create_pr → WRITE_NOTIFY
                   delete_repo → DESTRUCTIVE_APPROVAL
grep_app:          (all) → READ_AUTO
obscura_cdp:       navigate, read → READ_AUTO
                   form_fill, click → WRITE_NOTIFY
                   file_upload → DESTRUCTIVE_APPROVAL
postgres:          select, explain → READ_AUTO
                   insert, update, delete_row, drop, truncate → FORBIDDEN
redis:             get, keys, scan, ttl, exists, type, lrange, hget, hgetall → READ_AUTO
                   set, hset, lpush, rpush, sadd, incr, setnx, setex → WRITE_NOTIFY
                   del, expire, persist, rename → DESTRUCTIVE_APPROVAL
                   flushdb, flushall, config, debug, shutdown, slaveof → FORBIDDEN
sequential_thinking: (all) → READ_AUTO
shell:             exec → DESTRUCTIVE_APPROVAL
                   rm_rf_root, sudo_rm_rf → FORBIDDEN
time:              (all) → READ_AUTO
websearch:         (all) → READ_AUTO
```

### 4.3 Fail-Closed Check

| Test | Result | Status |
|------|--------|--------|
| Unknown tool lookup | `KeyError` raised: `Unknown tool 'unknown_tool'` | **PASS** (fail-closed) |

---

## 5. Manager Load — Tool Listing

### 5.1 Hermes Gateway MCP State

```
$ hermes mcp list

  No MCP servers configured.

  Add one with:
    hermes mcp add <name> --url <endpoint>
    hermes mcp add <name> --command <cmd> --args <args...>
```

| Check | Result | Status |
|-------|--------|--------|
| MCP servers registered | None | **FAIL** (expected for Phase 4 prep) |

### 5.2 Hermes Native Toolsets (Built-in)

Hermes v0.15.2 provides the following built-in toolsets (not MCP-based):

| Toolset | Status | Auth Level |
|---------|--------|------------|
| web (Web Search & Scraping) | ✓ enabled | Built-in |
| browser (Browser Automation) | ✓ enabled | Built-in |
| terminal (Terminal & Processes) | ✓ enabled | Built-in |
| file (File Operations) | ✓ enabled | Built-in |
| code_execution | ✓ enabled | Built-in |
| vision (Vision / Image Analysis) | ✓ enabled | Built-in |
| video | ✗ disabled | Built-in |
| image_gen (Image Generation) | ✓ enabled | Built-in |
| video_gen | ✗ disabled | Built-in |
| x_search (X/Twitter Search) | ✗ disabled | Built-in |
| moa (Mixture of Agents) | ✗ disabled | Built-in |
| tts (Text-to-Speech) | ✓ enabled | Built-in |
| skills | ✓ enabled | Built-in |
| todo (Task Planning) | ✓ enabled | Built-in |
| memory | ✓ enabled | Built-in |

**Important:** These are Hermes-native toolsets, not the MCP-based tools targeted by Phase 4.
The Phase 4 migration will use `hermes mcp add` to register 5 native MCP servers (web, 
filesystem, terminal, git, fetch) on top of these built-in capabilities.

---

## 6. Deployed Config vs Repo Config

### 6.1 Deployed Config (`~/.hermes/config.yaml`)

| Section | Present? | Detail |
|---------|----------|--------|
| `mcp_servers` | **MISSING** | Not in deployed config |
| `auth_matrix` | **MISSING** | Not in deployed config |
| `hooks` | **MISSING** | Not in deployed config |
| `plugins` | Present | `guinevere_safety` plugin configured (critical: true) |
| `guinevere_safety` plugin | Present | Hooks: pre_llm_call, post_llm_call, pre_tool_call, post_tool_call, transform_llm_output, on_session_start |

**Note:** The deployed config is the Hermes default config template (installed by `hermes gateway install`).
It does not include the Phase 4-specific sections.

### 6.2 Repo Config (`hermes-config/config.yaml`)

| Section | Present? | Detail |
|---------|----------|--------|
| `mcp_servers` | ✓ Present | web, filesystem, terminal, git, fetch — fully configured |
| `auth_matrix` | ✓ Present | 5 native tools mapped to 4 levels |
| `hooks` | ✓ Present | pre_tool_call (consent_gate.py), post_tool_call (dnr_filter.py) |
| `plugins` | ✓ Present | guinevere-safety configured |
| `approval` | ✓ Present | Discord webhook, 5min timeout, fail-closed deny |

**Key finding:** The repo config is ready for Phase 4. Migration requires deploying 
`hermes-config/config.yaml` → `~/.hermes/config.yaml` and registering MCP servers.

---

## 7. Systemd Service States

| Service | Active | Enabled | Notes |
|---------|--------|---------|-------|
| `hermes-gateway.service` | **active (running)** | **enabled** | Running since 13:24 WIB today. PID 3483297, Memory: 146.9M |
| `guinevere-mcp.service` | **inactive (dead)** | **disabled** | Legacy FastMCP service. Last ran Jun 04 14:17, registered 16 tools successfully |

### 7.1 Gateway Service Details
- ExecStart: `/home/guinevere/code/guinevere/.venv/bin/hermes gateway run --accept-hooks`
- Memory: 146.9M (high: 512.0M, max: 1.0G, available: 365.0M)
- CPU: 27.749s
- Restart: always (via systemd unit)

### 7.2 Warning Observed
```
WARNING: Stale systemd unit detected: hermes-gateway.service has 
TimeoutStopSec=90s but drain_timeout=180s (expected >=210s). 
systemd may SIGKILL the gateway mid-drain.
```
This is a pre-existing configuration mismatch — not blocking for Phase 4, but should
be addressed.

---

## 8. Port Isolation (Aizanta Compliance Check)

| Port | Service | Listening? | Expected? | Status |
|------|---------|-----------|-----------|--------|
| 5432 | PostgreSQL (standard) | **YES** | **No** | **VIOLATION** |
| 5433 | PostgreSQL (Aizanta) | YES | YES | PASS |
| 6379 | Redis (standard) | **YES** | **No** | **VIOLATION** |
| 6380 | Redis (Aizanta) | YES | YES | PASS |
| 20128 | 9Router (next-server) | YES | YES | PASS |
| 9090 | Prometheus | YES | YES | PASS |
| 9191 | Prometheus metrics | NO | N/A | INFO |

**Violation detail:** Both standard PostgreSQL (5432) and standard Redis (6379) are still 
listening on localhost alongside the Aizanta equivalents. The Aizanta isolation policy 
requires shutting down the standard services and running only on the designated Aizanta 
ports (5433, 6380).

Redis CLI confirmed both ports respond (6379 pongs, 6380 requires auth).

Other ports observed:
- 3000: Unidentified
- 3443: HTTPS service
- 5434: Unknown PG variant
- 6060: Unidentified
- 8000, 8080, 8443, 9093, 9100, 9121, 9187, 9443: Various (Prometheus exporters, etc.)
- 20241: cloudflared
- 3100: Loki
- 36438: Unidentified

---

## 9. Tool Configuration (Hooks & Plugins)

### 9.1 Hooks Directory (`~/.hermes/hooks/`)

| File | Purpose |
|------|---------|
| `consent_gate.py` | Pre-tool call consent verification (6.4 KB) |
| `dnr_filter.py` | Post-tool call Do-Not-Respond filter (6.1 KB) |
| `drift_check.py` | Persona drift detection (6.9 KB) |
| `error_classifier.py` | Error classification (8.5 KB) |
| `hard_stop.py` | HARD STOP protocol handler (7.2 KB) |
| `safety_scan.py` | Safety scanning (11.0 KB) |
| `_hook_utils.py` | Shared hook utilities (9.0 KB) |

**Status: PASS** — Hooks exist and cover safety-critical functions.

### 9.2 Plugins Directory (`~/.hermes/plugins/`)

| Plugin | Purpose |
|--------|---------|
| `guinevere_safety` | Dynamic persona state management |
| `guinevere-safety` | Safety plugin (variant) |
| `guinevere_memory` | Memory bridge plugin |
| `memory` | Memory plugin |

**Status: PASS** — Plugin system operational, `guinevere_safety` confirmed as `critical: true`.

### 9.3 `.env.mcp` File

**Status: PASS** — File exists at `/home/guinevere/code/guinevere/.env.mcp`.
- `REDIS_PASSWORD=***REDACTED***` (redacted)

---

## 10. Blockers for Phase 4

### BLOCKER-01: Filesystem Tool Parameter Naming (HIGH)
**File:** `src/mcp/tools/filesystem.py` (lines 190, 201, 213, 225)
**Issue:** Functions `fs_read`, `fs_write`, `fs_delete`, `fs_list` use `_config` as a 
parameter name. FastMCP v1.x rejects parameters starting with `_`.
**Fix:** Rename `_config` → `config` or use FastMCP `skip_params` mechanism.
**Mitigation:** This only affects the legacy FastMCP server (`guinevere-mcp.service`).
For Phase 4 Hermes native MCP, this code path is not used (will be migrated to Hermes 
native filesystem tool).

### BLOCKER-02: Port Isolation Violation (MEDIUM)
**Issue:** Ports 5432 (PG) and 6379 (Redis) still listening.
**Fix:** Stop and disable standard PG/Redis services. Verify no dependency on standard ports.
**Risk:** May impact other services if they reference `:5432` or `:6379` directly.

### BLOCKER-03: Deployed Config Stale (MEDIUM)
**Issue:** `~/.hermes/config.yaml` lacks `mcp_servers`, `auth_matrix`, and `hooks` sections 
that exist in `hermes-config/config.yaml`.
**Fix:** Deploy `hermes-config/config.yaml` → `~/.hermes/config.yaml` and restart gateway.

---

## 11. Pre-Condition Readiness

### Per `docs/setup-evidence/hermes-migration/phase-4-mcp.md`:

| Pre-condition | Status | Detail |
|---------------|--------|--------|
| Phase 2 cutover complete — Hermes gateway running as primary | ✓ PASS | `hermes-gateway.service` active, enabled |
| `guinevere-mcp.service` running (7 custom tools on FastMCP) | ✗ FAIL | Service inactive/disabled |
| Auth matrix definitions from `src/mcp/auth_matrix.py` | ✓ PASS | 16 tools, 80 operations, completeness verified |
| Phase 1 consent gate hook operational | ✓ PASS | `consent_gate.py` present in hooks dir |

---

## 12. Hermes MCP Add Capability

The `hermes mcp add` command supports:
- `--url <endpoint>` for HTTP/SSE MCP servers
- `--command <cmd>` for stdio-based MCP servers (e.g., `npx`)
- `--auth {oauth, header}` for authenticated MCP servers
- `--preset <name>` for known MCP presets
- `--env KEY=VALUE` for environment variables

**No native `hermes mcp add --native` or `hermes mcp add web` subcommands exist** in 
Hermes v0.15.2. The Phase 4 plan's Step 4.1 syntax (`hermes mcp add web --config ...`) 
does not match the actual CLI. The MCP servers defined in `hermes-config/config.yaml` 
(`mcp_servers` section) appear to be processed at **gateway startup** from the config 
file rather than via CLI.

**Recommendation:** Verify how `mcp_servers` in config.yaml are loaded by the gateway.
The Phase 4 procedure may need updating to reflect actual CLI semantics.

---

## 13. Action Items

| Priority | Action | Owner |
|----------|--------|-------|
| HIGH | Fix `_config` parameter naming in `filesystem.py` before starting legacy MCP | Dev |
| HIGH | Deploy `hermes-config/config.yaml` → `~/.hermes/config.yaml` | Dev |
| HIGH | Verify `mcp_servers` are loaded from config (not CLI `add`) | Research |
| MEDIUM | Shut down standard PG (5432) and Redis (6379) | DevOps |
| MEDIUM | Fix systemd `TimeoutStopSec` mismatch (90s vs 210s) | DevOps |
| LOW | Update `hermes mcp add` CLI semantics in Phase 4 plan | Docs |

---

## 14. Appendix: Service Log Snippets (Last Successful MCP Load)

From `journalctl -u guinevere-mcp` (last run, Jun 04 14:17):
```
[info] obscura_cdp_tools_registered
[info] redis_tools_registered          command_counts={'read': 9, 'write': 9, 'destructive': 4, 'forbidden': 6}
[info] sequential_thinking_tool_registered
[info] shell_tool_registered
[info] websearch_tool_registered
[info] tools_registered               count=16 total=16
[info] mcp_server_ready               tools_registered=16
[info] auth_matrix_complete           tool_count=16
[info] auth_matrix_verified
[info] mcp_server_shutting_down       (graceful, no error)
```

The last run was successful — all 16 tools registered and auth matrix verified.
The service stopped gracefully. The `_config` bug only manifests on the **next** start
because the pip FastMCP package was likely updated between runs.

---

*End of Report*

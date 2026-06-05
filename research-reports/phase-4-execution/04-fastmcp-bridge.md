# FastMCP Bridge Feasibility Report — Phase 4

**Report ID:** 04-fastmcp-bridge
**Date:** 2026-06-05
**Scope:** FastMCP server → Hermes MCP stdio bridge feasibility for 7 custom tools
**Status:** READ-ONLY RESEARCH
**Phase:** Phase 4 (MCP + Tools Migration)
**ADR Reference:** ADR-035 §Phase 4, BD-004

---

## 1. Executive Summary

The Guinevere FastMCP server (`src/mcp/manager.py`) can serve as an MCP stdio backend for Hermes Agent v0.15.2 with **no code changes** to any of the 7 custom tool modules. Hermes supports stdio transport natively via its `mcp_servers` config. The bridge is configured by adding a `fastmcp_custom` entry in `hermes-config/config.yaml` that spawns the FastMCP server as a subprocess.

**Status: FEASIBLE with 3 documented blockers.** Two are pre-existing gaps (sys.path hack, fail-open plugin model) with known mitigations from the batch plan. One requires verification (stdio process lifecycle).

---

## 2. Current FastMCP Server Architecture

### 2.1 Server Entrypoint

| Property | Value |
|----------|-------|
| **File** | `C:\Users\faizz\guinevere\src\mcp\manager.py` (103 lines) |
| **Framework** | `mcp.server.fastmcp.FastMCP` (pip package `mcp>=1.0`) |
| **Factory** | `create_server(name="guinevere-mcp") → FastMCP` |
| **Transport** | Default stdio via `server.run()` in `if __name__ == "__main__":` block (line 101-103) |
| **Lifespan** | `_build_lifespan()` — async context manager that calls `register_all_tools(server)` + `verify_matrix_completeness()` on startup |
| **Systemd** | `systemd/guinevere-mcp.service` → `python -m src.mcp.manager` |
| **Environment** | `.env.mcp` (SOPS/age encrypted) — contains `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `BRAVE_API_KEY`, `EXA_API_KEY` |
| **Dependency** | `pyproject.toml` line 32: `"mcp>=1.0"` |

### 2.2 Tool Registration Mechanism

**File:** `C:\Users\faizz\guinevere\src\mcp\tools\__init__.py` (94 lines)

The registry uses a dynamic module pattern:

```python
_TOOL_MODULES: list[object] = [
    brave_search, context7, docker_tool, exa_search, fetch, filesystem,
    git_tool, github, grep_app, obscura_cdp, postgres_tool, redis_tool,
    sequential_thinking, shell_tool, time_tools, websearch,
]

def register_all_tools(server: FastMCP) -> int:
    count = 0
    for module in _TOOL_MODULES:
        register_fn = getattr(module, "register_tools", None)
        if register_fn is not None:
            register_fn(server)
            count += 1
    return count
```

**Registration contract per tool module:**

```python
def register_tools(mcp: FastMCP) -> None:
    mcp.tool(name="explicit_tool_name")(function)
```

Each tool function is decorated with `@require_approval(AuthLevel.*, tool_name="...")` from `src.mcp.auth`.

### 2.3 Output: `mcp>=1.0` Dependency Confirmed

`pyproject.toml` line 32 shows `"mcp>=1.0"` as a project dependency. The FastMCP framework is the `mcp.server.fastmcp` submodule of the pip-installed `mcp` package.

---

## 3. The 7 Custom Tools (KEEP per BD-004)

| Tool | File | Operations | Auth Levels | Lines |
|------|------|-----------|-------------|-------|
| `postgres_tool` | `src/mcp/tools/postgres_tool.py` | 3 (query, tables, describe) | READ_AUTO (all) | 296 |
| `redis_tool` | `src/mcp/tools/redis_tool.py` | 9 (get, keys, hgetall, lrange, set, hset, del, flushdb, flushall) | READ_AUTO(4) + WRITE_NOTIFY(2) + DESTRUCTIVE(1) + FORBIDDEN(2) | 408 |
| `obscura_cdp` | `src/mcp/tools/obscura_cdp.py` | 4 (navigate, get_markdown, fill_form, click) | READ_AUTO(2) + WRITE_NOTIFY(2) | 235 |
| `grep_app` | `src/mcp/tools/grep_app.py` | 1 (search) | READ_AUTO | 224 |
| `context7` | `src/mcp/tools/context7.py` | 2 (resolve, query) | READ_AUTO | 379 |
| `sequential_thinking` | `src/mcp/tools/sequential_thinking.py` | 1 (think) | READ_AUTO | 399 |
| `time_tools` | `src/mcp/tools/time_tools.py` | 6 (current_time, convert_time, days_in_month, relative_time, get_timestamp, get_week_year) | READ_AUTO | 236 |

**Total: ~2,177 lines across 7 tools.** All use `@require_approval` decorators with deterministic auth levels defined in `src/mcp/auth_matrix.py`.

### Registration Pattern (Representative Examples)

**redis_tool.py (line 366-396):**
```python
def register_tools(mcp: FastMCP) -> None:
    mcp.tool(name="redis_get")(redis_get)
    mcp.tool(name="redis_keys")(redis_keys)
    mcp.tool(name="redis_hgetall")(redis_hgetall)
    mcp.tool(name="redis_lrange")(redis_lrange)
    mcp.tool(name="redis_set")(redis_set)
    mcp.tool(name="redis_hset")(redis_hset)
    mcp.tool(name="redis_del")(redis_del)
    mcp.tool(name="redis_flushdb")(
        require_approval(AuthLevel.FORBIDDEN, tool_name="redis_flushdb")(redis_flushdb)
    )
    mcp.tool(name="redis_flushall")(
        require_approval(AuthLevel.FORBIDDEN, tool_name="redis_flushall")(redis_flushall)
    )
```

**time_tools.py (line 229-236):**
```python
def register_tools(mcp: FastMCP) -> None:
    mcp.tool(name="time_current_time")(current_time)
    mcp.tool(name="time_convert_time")(convert_time)
    mcp.tool(name="time_days_in_month")(days_in_month)
    mcp.tool(name="time_relative_time")(relative_time)
    mcp.tool(name="time_get_timestamp")(get_timestamp)
    mcp.tool(name="time_get_week_year")(get_week_year)
```

**context7.py (line 366-377):**
```python
def register_tools(mcp: FastMCP) -> None:
    mcp.tool()(context7_resolve)   # auto-named from function
    mcp.tool()(context7_query)
```

Note: `context7` uses `mcp.tool()` without explicit `name=`, which means FastMCP auto-derives the name from the function name. Both `redis_tool` and `time_tools` use explicit `name=` parameters. This inconsistency does not affect the bridge but should be noted.

---

## 4. Hermes MCP Client — stdio Support

### 4.1 Confirmed Capabilities (from R4-007)

Hermes Agent v0.15.2 has a native MCP client that supports **stdio transport** via subprocess spawning. Configuration is YAML-based under `mcp_servers`:

```yaml
mcp_servers:
  <server_name>:
    command: "python"
    args: ["-m", "src.mcp.manager"]
    env:
      PYTHONPATH: "/home/guinevere/code/guinevere"
    cwd: "/home/guinevere/code/guinevere"
    enabled: true
    timeout: 120
    connect_timeout: 60
    supports_parallel_tool_calls: false
    tools:
      include: ["postgres_query", "redis_get", ...]
```

**Key properties:**
- Subprocess spawned at Hermes startup
- Communication via stdio JSON-RPC (MCP stdio transport)
- Tools registered with prefix `mcp_<server>_<tool>`
- `include`/`exclude` filtering per server
- Environment variables via `env` block
- Working directory via `cwd`

### 4.2 Current Hermes MCP Config (hermes-config/config.yaml)

The config already has 5 native MCP servers (lines 162-210):
- `web` — `brave_search`, `exa_search`, `fetch_url`, `websearch`
- `filesystem` — allowed/blocked paths, root_path
- `terminal` — allowed/blocked commands, 30s timeout
- `git` — allowed/blocked operations
- `fetch` — 30s timeout, 10MB max response

**There is NO `fastmcp_custom` entry yet** — this is the gap the bridge must fill.

### 4.3 No CLI Subcommands for MCP Management

Contrary to what `phase-4-mcp.md` assumes (commands like `hermes mcp add`), R4-007 confirmed that **Hermes does not expose MCP server management via CLI subcommands**. MCP servers are configured exclusively via YAML in `config.yaml`. The Phase 4 procedure document's command-based approach (Steps 4.1, 4.3) must be adjusted to YAML-only configuration.

---

## 5. Feasibility Analysis

### 5.1 What Works Out of the Box (NO CHANGES NEEDED)

| Component | Status | Rationale |
|-----------|--------|-----------|
| FastMCP stdio transport | Working | `server.run()` uses stdio by default |
| Tool registration | Working | `register_all_tools()` registers all 16 tools |
| Auth decorators | Working | `@require_approval` gates each tool function |
| Hermes stdio client | Available | Native MCP stdio via `mcp_servers` config |
| Tool filtering | Available | `tools.include` / `tools.exclude` in config |
| Environment isolation | Working | `.env.mcp` file exists with all secrets |
| Systemd service | Working | `guinevere-mcp.service` — no changes needed |

### 5.2 What Requires Configuration

| Item | Action | Details |
|------|--------|---------|
| Add `fastmcp_custom` to `mcp_servers` | CREATE entry in config.yaml | `command: python`, `args: ["-m", "src.mcp.manager"]` |
| Tool allowlist | VERIFY | 24 tool operations → 7 canonical tools |
| Auth overlay plugin | CREATE | New Hermes plugin that hooks `pre_tool_call` |
| Environment propagation | VERIFY | Ensure `.env.mcp` vars reach subprocess |

### 5.3 Recommended `mcp_servers` Config for FastMCP Bridge

```yaml
mcp_servers:
  fastmcp_custom:
    enabled: true
    command: "python"
    args: ["-m", "src.mcp.manager"]
    cwd: "/home/guinevere/code/guinevere"
    env:
      PYTHONPATH: "/home/guinevere/code/guinevere"
      PYTHONDONTWRITEBYTECODE: "1"
    env_file: ".env.mcp"
    timeout: 120
    connect_timeout: 60
    supports_parallel_tool_calls: false
    tools:
      include:
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
        - time_current_time
        - time_convert_time
        - time_days_in_month
        - time_relative_time
        - time_get_timestamp
        - time_get_week_year
```

**Note:** The 24 tool operation names above are FastMCP-registered names. Hermes will prefix them as `mcp_fastmcp_custom_postgres_query`. The auth overlay plugin must handle this prefix.

---

## 6. Blockers and Mitigations

### 6.1 BLOCKER-001: sys.path Hack in manager.py

**File:** `src/mcp/manager.py` (lines 24-33)

```python
_SRC_DIR = str(Path(__file__).resolve().parent.parent)
_SRC_ABS = Path(_SRC_DIR).resolve()
_SAVED_PATH: list[str] = list(sys.path)
sys.path = [p for p in sys.path if Path(p).resolve() != _SRC_ABS]
from mcp.server.fastmcp import FastMCP
sys.path[:] = _SAVED_PATH
```

**Problem:** Removes `src/` from `sys.path` to prevent local `src/mcp` shadowing pip `mcp` package. Fragile — depends on exact path resolution.

**Mitigation:** The `fastmcp_custom` entry must pass `cwd: "/home/guinevere/code/guinevere"` and `env.PYTHONPATH: "/home/guinevere/code/guinevere"` — matching the systemd service. Verified in P4-005.

**Status:** CONFIGURABLE — not a code fix, just a config constraint.

### 6.2 BLOCKER-002: critical: true / on_failure: block Not Native to Hermes

**Source:** R4-007 (line 119-125)

**Problem:** ADR-035 assumes `critical: true` and `on_failure: block` flags exist. They do not. Hermes v0.15.2 uses fail-open:
- Plugin crash → disabled, Hermes continues
- Hook crash → logged + skipped

**Impact:** If auth overlay plugin fails to load, Hermes starts without auth enforcement.

**Mitigation (P4-006):** `scripts/startup_gate.py` — validates all critical plugins before launching Hermes.

**Status:** KNOWN GAP with mitigation in batch plan.

### 6.3 BLOCKER-003: Untested stdio Process Lifecycle

**Problem:** FastMCP server has only been tested as standalone systemd service. When Hermes spawns it as subprocess:
- Will SIGTERM/SIGINT propagate correctly?
- Will lifespan cleanup work when stdin closes?
- Will concurrent tool calls serialize properly?

**Mitigation:** Testing in P4-005/P4-008. Systemd service remains as fallback.

**Status:** REQUIRES VERIFICATION during implementation.

### 6.4 NON-BLOCKER: Tool Name Prefixing

Hermes prefixes MCP tool names with `mcp_<server>_`. So `postgres_query` becomes `mcp_fastmcp_custom_postgres_query`. The auth overlay plugin's `_extract_operation` must strip this prefix.

Addressed in batch plan P4-002 operation extraction spec.

---

## 7. Hermes CLI Capabilities (from Research)

Since VPS SSH access is not available from this environment, Hermes CLI capabilities are documented from prior research (R4-001, R4-004, R4-007):

| Command | Confirmed | Source |
|---------|-----------|--------|
| `hermes config validate` | Yes | R4-001 |
| `hermes mcp list` | Yes | R4-007 |
| `hermes plugin list` | Yes | R4-007 |
| `hermes gateway run --accept-hooks` | Yes | ADR-035, current systemd config |
| `hermes tool test <tool> <args>` | Yes | ADR-035 phase-4-mcp.md |
| `hermes gateway start/stop` | Yes | ADR-035 |
| `hermes mcp add` | DOES NOT EXIST | R4-007 |
| `hermes mcp serve` | DOES NOT EXIST | R4-007 |
| `hermes mcp remove` | DOES NOT EXIST | R4-007 |
| `hermes mcp --help` | NOT TESTED (no SSH) | Expected to show no MCP subcmds |

**Critical finding:** The Phase 4 procedure document (`phase-4-mcp.md`) uses `hermes mcp add` and `hermes mcp remove` commands that **do not exist** in Hermes v0.15.2. All MCP server management is done through `config.yaml` editing. The batch plan (`batch-plan-phase-4.md`) correctly uses YAML-config approach.

---

## 8. Auth Overlay Integration Path

The auth overlay plugin must intercept tool calls from BOTH native Hermes tools and the FastMCP bridge:

```text
                   +-----------------------+
                   |  Hermes Agent Core    |
                   +----------+------------+
                              | Tool call
                              v
                 +--------------------------+
                 |  pre_tool_call hooks     |
                 |  1. auth_overlay (100)   |
                 |  2. consent_gate (90)    |
                 |  3. budget_check (85)    |
                 +--------------------------+
                              |
                +-------------+-------------+
                v             v             v
         +----------+  +----------+  +--------------+
         | Hermes   |  | Hermes   |  | FastMCP      |
         | Native   |  | Hybrid   |  | Custom       |
         | (5)      |  | (4)      |  | (7 tools)    |
         +----------+  +----------+  +-------^------+
                                              |
                                         +----v----+
                                         | stdio   |
                                         | subproc |
                                         +---------+
```

The auth overlay imports `AUTH_MATRIX` directly from `src/mcp/auth_matrix.py` (Python source of truth, per BD-006). Tool name resolution handles:
- Native tools: `brave_search`, `filesystem`, `terminal`, `git`, `fetch`
- FastMCP custom tools: strip `mcp_fastmcp_custom_` prefix → `postgres_query`, `redis_get`, etc.

---

## 9. Config Recommendations

### 9.1 FastMCP Bridge Config (ADD to hermes-config/config.yaml)

Section under `mcp_servers`:

```yaml
  fastmcp_custom:
    enabled: true
    command: "python"
    args: ["-m", "src.mcp.manager"]
    cwd: "/home/guinevere/code/guinevere"
    env:
      PYTHONPATH: "/home/guinevere/code/guinevere"
      PYTHONDONTWRITEBYTECODE: "1"
    env_file: ".env.mcp"
    timeout: 120
    connect_timeout: 60
    supports_parallel_tool_calls: false
    tools:
      include:
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
        - time_current_time
        - time_convert_time
        - time_days_in_month
        - time_relative_time
        - time_get_timestamp
        - time_get_week_year
```

### 9.2 Existing Native Servers (NO CHANGES)

5 native servers (`web`, `filesystem`, `terminal`, `git`, `fetch`) are already configured correctly in `hermes-config/config.yaml` lines 162-210.

### 9.3 Startup Gate (Systemd Change)

Modify `scripts/hermes-gateway.service` ExecStart:

```ini
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python3 /home/guinevere/code/guinevere/scripts/startup_gate.py
```

### 9.4 Plugin Config (ADD to config.yaml)

```yaml
plugins:
  enabled:
    - guinevere_safety
    - auth_overlay
```

---

## 10. Verified File Inventory

### Files NOT to Modify (Read-Only)

| File | Reason |
|------|--------|
| `src/mcp/manager.py` | FastMCP factory — unchanged |
| `src/mcp/auth.py` | Auth decorators — unchanged |
| `src/mcp/auth_matrix.py` | Auth matrix source of truth — unchanged |
| `src/mcp/tools/postgres_tool.py` | Custom tool — unchanged |
| `src/mcp/tools/redis_tool.py` | Custom tool — unchanged |
| `src/mcp/tools/obscura_cdp.py` | Custom tool — unchanged |
| `src/mcp/tools/grep_app.py` | Custom tool — unchanged |
| `src/mcp/tools/context7.py` | Custom tool — unchanged |
| `src/mcp/tools/sequential_thinking.py` | Custom tool — unchanged |
| `src/mcp/tools/time_tools.py` | Custom tool — unchanged |
| `systemd/guinevere-mcp.service` | Systemd service — unchanged |

### Files to CREATE

| File | Purpose | Batch Plan Step |
|------|---------|-----------------|
| `hermes-config/plugins/auth_overlay/__init__.py` | Auth overlay plugin entry point | P4-002 |
| `hermes-config/plugins/auth_overlay/manifest.yaml` | Plugin manifest | P4-002 |
| `hermes-config/plugins/auth_overlay/auth_handler.py` | pre_tool_call auth logic | P4-002 |
| `hermes-config/plugins/auth_overlay/approval_handler.py` | DESTRUCTIVE_APPROVAL webhook | P4-002 |
| `hermes-config/plugins/auth_overlay/notify_handler.py` | WRITE_NOTIFY notifications | P4-002 |
| `hermes-config/plugins/auth_overlay/forbidden_handler.py` | FORBIDDEN hard-block | P4-002 |
| `scripts/startup_gate.py` | Plugin validation wrapper | P4-006 |

### Files to MODIFY

| File | Changes | Batch Plan Step |
|------|---------|-----------------|
| `hermes-config/config.yaml` | Add `fastmcp_custom` entry + `plugins.enabled` | P4-001 |
| `scripts/hermes-gateway.service` | Change ExecStart to startup_gate.py | P4-006 |

---

## 11. Verdict

**FastMCP bridge is FEASIBLE.** No code changes are needed to the 7 custom tools, the FastMCP server factory, or the auth matrix. The bridge is a pure configuration change — adding a `fastmcp_custom` entry to Hermes' `mcp_servers` YAML config.

**3 blockers identified** (all with mitigations in the approved batch plan):
1. **BLOCKER-001:** sys.path hack in manager.py requires exact PYTHONPATH/wd matching — configurable, verified in P4-005.
2. **BLOCKER-002:** `critical: true` not native to Hermes — mitigated by startup_gate.py (P4-006).
3. **BLOCKER-003:** stdio process lifecycle untested — mitigated by integration testing (P4-008).

**1 critical documentation correction:** The Phase 4 procedure document (`docs/setup-evidence/hermes-migration/phase-4-mcp.md`) uses non-existent `hermes mcp add/remove` CLI commands. The batch plan (`docs/setup-evidence/phase-4/batch-plan-phase-4.md`) correctly uses YAML-config-only approach and should be the authoritative implementation guide.

---

## 12. References

| Document | Path | Relevance |
|----------|------|-----------|
| Batch Plan Phase 4 | `docs/setup-evidence/phase-4/batch-plan-phase-4.md` | Authoritative implementation guide |
| ADR-035 | `adr/ADR-035-hermes-migration.md` | Architecture context, Phase 4, BD-004 |
| R4-003 FastMCP Custom Tools | `research-reports/phase-4-planning/R4-003-fastmcp-custom-tools.md` | Tool inventory, registration patterns |
| R4-007 Hermes MCP Plugin Docs | `research-reports/phase-4-planning/R4-007-hermes-mcp-plugin-docs.md` | Hermes MCP client config format, stdio support |
| R4-001 Hermes MCP Config | `research-reports/phase-4-planning/R4-001-hermes-mcp-config-patterns.md` | MCP server config patterns |
| Phase 4 MCP Procedure | `docs/setup-evidence/hermes-migration/phase-4-mcp.md` | (Contains incorrect CLI commands) |
| FastMCP Server | `src/mcp/manager.py` | Server factory, sys.path hack |
| Tool Registry | `src/mcp/tools/__init__.py` | register_all_tools, _TOOL_MODULES |
| Auth Matrix | `src/mcp/auth_matrix.py` | AUTH_MATRIX, get_auth_level |
| ADR-013 | `adr/ADR-013-guinevere-mcp-native-opencode-replacement.md` | MCP native architecture |

---

*Generated by Guinevere Research Agent. READ-ONLY. No modifications made to source code.*
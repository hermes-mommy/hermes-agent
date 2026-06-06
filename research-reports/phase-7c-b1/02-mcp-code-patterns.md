# Phase 7c-B1 — MCP Code & Configuration Pattern Analysis

**Date**: 2026-06-06  
**Scope**: `guinevere-mcp` service inactivity — root cause analysis  
**Method**: Code-search, AST-grep, file reads (no edits)

---

## Summary

The `guinevere-mcp` service is **inactive (dead) and disabled** (last active Jun 04 14:17, clean shutdown). The root cause is **not a single crash or import error** but a combination of: (A) the service was manually disabled and never re-enabled, (B) `Type=exec` + `Restart=always` was insufficient to keep it alive because the FastMCP stdio server process exited cleanly, and (C) the environment file `.env.mcp` is missing multiple required API keys. Below is the full forensic breakdown.

---

## 1. Service Unit Configuration

**File**: `systemd/guinevere-mcp.service`

| Field | Value | Issue |
|---|---|---|
| `Type` | `exec` | Systemd considers service "started" after exec succeeds |
| `Restart` | `always` | Should restart even after clean exit — but only if `systemctl start` was called |
| `RestartSec` | `10` | 10-second delay before restart |
| `ExecStart` | `.venv/bin/python -m src.mcp.manager` | Entry-point |
| `EnvironmentFile` | `.env.mcp` | **CRITICAL**: missing env vars for API keys |
| `PYTHONPATH` | `/home/guinevera/code/guinevera` | Correct — enables `from src.mcp.*` imports |
| `User` | `guinevera` | Correct |
| `Slice` | `guinevera.slice` | Correct |
| `WantedBy` | `multi-user.target` | Correct |
| **Enabled state** | **`disabled`** | **PRIMARY CAUSE**: service does NOT auto-start on boot |

**Root cause A**: The service unit is `disabled`. `systemctl enable guinevere-mcp` was never run, or it was explicitly disabled (`systemctl disable guinevere-mcp`). Even with `Restart=always`, systemd only restarts a service that was *started* — it does NOT auto-enable it on boot.

**Root cause B**: The last shutdown was graceful (`mcp_server_shutting_down` logged). Combined with `Restart=always`, a clean exit code 0 should trigger restart — unless:
- The service was stopped via `systemctl stop guinevere-mcp` (manual intervention), OR
- The restart limit (`StartLimitBurst`, default 5 per 10s) was exceeded and systemd marked it as `failed` → `inactive`.

---

## 2. Import Chain & Package Name Collision

**Files**: `src/mcp/manager.py`, `src/mcp/custom_manager.py`

Both modules perform a `sys.path` manipulation to work around a **package name collision** between the local `src/mcp/` directory and the pip-installed `mcp` package (v1.x, `mcp.server.fastmcp`):

```python
# manager.py lines 23-33
_SRC_DIR = str(Path(__file__).resolve().parent.parent)   # e.g. /home/g.../src
_SRC_ABS = Path(_SRC_DIR).resolve()
_SAVED_PATH: list[str] = list(sys.path)
sys.path = [p for p in sys.path if Path(p).resolve() != _SRC_ABS]

from mcp.server.fastmcp import FastMCP  # needs src/ REMOVED from path

sys.path[:] = _SAVED_PATH  # restore src/ for our imports

from src.mcp.tools import register_all_tools  # needs src/ on path
```

**Fragility analysis (3 failure modes):**

| Scenario | `src/` on sys.path? | Behavior |
|---|---|---|
| Production (systemd) | No (only parent dir) | Works — `mcp` resolves to pip package, `src.mcp.tools` resolves via PYTHONPATH |
| pytest (pyproject.toml sets `pythonpath = ["src"]`) | **Yes** | sys.path dance removes `src/` temporarily → `FastMCP` imports OK → restores `src/` → then `from src.mcp.tools import ...` triggers tool module imports |
| **CRITICAL**: tools that import `mcp.server.fastmcp` at module level AFTER path restore | `src/` restored | **FAIL** — `mcp` resolves to local `src/mcp/` (no `server` submodule) |

**Tool modules importing `mcp.server.fastmcp` at MODULE LEVEL (not TYPE_CHECKING-guarded):**

| File | Line | Import |
|---|---|---|
| `src/mcp/tools/exa_search.py` | 21 | `from mcp.server.fastmcp import FastMCP` |
| `src/mcp/tools/time_tools.py` | 21 | `from mcp.server.fastmcp import FastMCP` |
| `src/mcp/tools/filesystem.py` | 30 | `from mcp.server.fastmcp import FastMCP` |

**Impact**: When manager.py restores `sys.path` (re-adding `src/`), then imports `src.mcp.tools.register_all_tools`, the tools `__init__.py` sequentially imports each tool module. If any of the above three tools are imported while `src/` is on `sys.path` (pytest mode), `mcp.server.fastmcp` resolves to the **local** `src/mcp/` package, which has no `server` submodule → `ModuleNotFoundError`.

**Workaround status**: In production (systemd), `src/` is NOT directly on `sys.path` — only `/home/guinevera/code/guinevere` (its parent) is. So `import mcp` searches site-packages first. However, this is accidental; any change to `PYTHONPATH` or working directory would break it.

---

## 3. Environment Variable Dependencies

**File**: `scripts/setup-service-envs.sh` (line 46-50) — the `.env.mcp` generator

The setup script generates `.env.mcp` with **only**:
```
REDIS_PASSWORD=<decrypted_value>
```

**Missing API keys (not written to `.env.mcp`)**:

| Variable | Required By | Behavior If Missing |
|---|---|---|
| `BRAVE_API_KEY` | `brave_search.py:_get_api_key()` | Raises `BraveSearchConfigError` at tool call time |
| `EXA_API_KEY` | `exa_search.py:_get_api_key()` | Raises `ConfigurationError` at tool call time |
| `POSTGRES_PASSWORD` | `postgres_tool.py:_get_pool()` | Connects with empty password — auth failure |
| `DISCORD_WEBHOOK_URL` | `auth.py:_get_webhook_url()` | Silently degrades (logs warning, no notifications) |

**Key finding**: These missing vars do NOT prevent server startup — they only cause individual tool calls to fail at runtime. The server (manager.py + auth) initializes fine without them because env reads are lazy (inside tool functions, not at module level).

---

## 4. Circular Import Hazards

### 4.1 `auth.py` ↔ `auth_matrix.py` (KNOWN, managed)

| File | Import Direction | Mechanism |
|---|---|---|
| `auth_matrix.py:22` | `from src.mcp.auth import AuthLevel` | Module-level (direct) |
| `auth.py:175` | `from src.mcp.auth_matrix import get_auth_level` | **Lazy** (inside function body `wrapper()`) |

The lazy import at `auth.py:175` breaks the cycle at runtime. Static analyzers flag this as a cycle (`reportImportCycles`), but it works in practice. **Risk**: if any new code imports `auth_matrix` at module level from within `auth.py`, the cycle becomes runtime-fatal.

### 4.2 `budget.py` ← `exa_search.py` (LAYER VIOLATION)

| File | Import |
|---|---|
| `budget.py:23` | `from src.mcp.tools.exa_search import BudgetExceeded` |

This is a **cross-layer import** — Level 2 (core infrastructure) imports from Level 3 (tool modules). The `budget.py` module creates its own `redis.Redis()` client at line 76-83, same as `cost.py` and `brave_search.py`, with hardcoded `host="localhost"`, `port=6380`, `db=5`. Three scattered Redis client instances is a maintenance hazard.

---

## 5. Redis Connection Scatter

**Three separate modules create their own Redis connections** with identical hardcoded defaults:

| File | Host | Port | DB | Username |
|---|---|---|---|---|
| `budget.py:76-83` | `localhost` | 6380 | 5 | `guinevere_core` |
| `cost.py:56-63` | `localhost` | 6380 | 5 | `guinevere_core` |
| `brave_search.py:66-73` | `localhost` | 6380 | 5 | `guinevere_core` |
| `exa_search.py:74-81` | `localhost` | 6380 | 5 | `guinevere_core` (async) |
| `redis_tool.py:133-140` | `localhost` | 6380 | 5 (default) | `guinevere_core` |

If Redis is down or unreachable, `budget.py` and `cost.py` constructors would fail at instantiation time — but since they're never actually instantiated by the running server (dead code per P6 audit), this is currently harmless.

---

## 6. Ports Used by MCP Tools

| Tool | Port | Config Source |
|---|---|---|
| PostgreSQL | **5433** (hardcoded) | `postgres_tool.py:95` — `_DEFAULT_PORT = 5433`, no env override |
| Redis | **6380** (hardcoded) | Multiple files — `_REDIS_PORT = 6380`, `port=6380` |
| CDP (Obscura) | **9222** | External Chrome DevTools Protocol |
| 9Router API | **20128** | External (used by hermes-gateway, not MCP) |

No port conflicts detected. All canonical ports match the documented allocation.

---

## 7. External Import Dependencies (pip)

**From `pyproject.toml`**:

| Package | Version | Used By |
|---|---|---|
| `mcp>=1.0` | pip | `mcp.server.fastmcp.FastMCP` — core server |
| `structlog>=24` | pip | All MCP modules for structured logging |
| `redis>=5` | pip | `cost.py`, `budget.py`, `brave_search.py`, `exa_search.py`, `redis_tool.py` |
| `asyncpg>=0.30` | pip | `postgres_tool.py` |
| `httpx>=0.28` | pip | `auth.py` (webhook), `exa_search.py`, `brave_search.py`, `context7.py` |
| `tenacity>=9` | pip | `exa_search.py`, `brave_search.py` |
| `discord.py>=2.4` | pip | Auth notification (via webhook, not direct) |

**Verified locally**: All packages installed, `FastMCP` importable.

---

## 8. Configuration File Checks

| File | Location | Status |
|---|---|---|
| systemd unit | `systemd/guinevere-mcp.service` | ✅ On disk, correct |
| `.env.mcp` | repo root | **❌ NOT TRACKED in git** — VPS copy exists per reports |
| `hermes-config/config.yaml` | `mcp_servers.fastmcp_custom` | `enabled: false` — KEEP-7 bridge is disabled |
| `src/mcp/__init__.py` | package init | Exports 4 symbols, no auth_matrix/cost/budget exports |

---

## 9. Root Cause Verdict

| Layer | Cause | Confidence |
|---|---|---|
| **Systemd** | Service unit is `disabled` → does not start on boot | **HIGH** |
| **Systemd** | `Type=exec` + `Restart=always` with clean exit → process exits immediately, systemd tries to restart, hits limit → left `inactive/dead` | **MEDIUM** |
| **Env** | `.env.mcp` missing `BRAVE_API_KEY`, `EXA_API_KEY`, `POSTGRES_PASSWORD` → not fatal to startup but tools fail at call time | **LOW** (not startup-blocking) |
| **Import** | Package name collision (`src/mcp/` ↔ pip `mcp`) with fragile `sys.path` hack — works accidentally in production, crashes in pytest | **MEDIUM** (latent) |
| **Import** | Circular `auth.py` ↔ `auth_matrix.py` via lazy import — managed but fragile | **LOW** (not currently active) |

**Primary**: The service was **manually disabled** and never re-enabled (`systemctl disable guinevere-mcp` or `systemctl stop` + not restarted). The process itself exits cleanly (stdio transport), and `Restart=always` couldn't compensate because the service was told to stop.

**Latent**: Even if re-enabled, the service would fail under pytest (tools importing `mcp.server.fastmcp` after `sys.path` restore). Production startup is accidentally correct.

---

## 10. Files Referenced

| Path | Role |
|---|---|
| `systemd/guinevere-mcp.service` | Systemd unit definition |
| `src/mcp/manager.py` | Main FastMCP server entry-point |
| `src/mcp/custom_manager.py` | KEEP-7-only bridge (disabled) |
| `src/mcp/__init__.py` | Package exports |
| `src/mcp/auth.py` | Auth decorator, Discord webhook, lazy import to auth_matrix |
| `src/mcp/auth_matrix.py` | Auth level registry for 16 tools |
| `src/mcp/budget.py` | Budget enforcer (dead code) |
| `src/mcp/cost.py` | Cost tracker (dead code) |
| `src/mcp/tool_selector.py` | Tool decision matrix (dead code) |
| `src/mcp/tools/__init__.py` | Dynamic tool registry (16 modules) |
| `src/mcp/tools/exa_search.py` | Module-level import of `mcp.server.fastmcp` (fragile) |
| `src/mcp/tools/time_tools.py` | Module-level import of `mcp.server.fastmcp` (fragile) |
| `src/mcp/tools/filesystem.py` | Module-level import of `mcp.server.fastmcp` (fragile) |
| `src/mcp/tools/brave_search.py` | Brave API key env read, Redis client |
| `src/mcp/tools/postgres_tool.py` | Hardcoded port 5433, env password |
| `src/mcp/tools/redis_tool.py` | Hardcoded port 6380, env password |
| `scripts/setup-service-envs.sh` | Generates `.env.mcp` with ONLY `REDIS_PASSWORD` |
| `hermes-config/config.yaml` | `fastmcp_custom` disabled, points to `src.mcp.custom_manager` |
| `pyproject.toml` | Dependencies, pytest config with `pythonpath = ["src"]` |
| `research-reports/phase-7-execution/01-baseline.md` | Baseline: service inactive/dead since Jun 04 |

# Phase 4 Planning: FastMCP Custom Tools Inventory

**Report ID:** R4-003-fastmcp-custom-tools  
**Date:** 2026-06-05  
**Scope:** MCP + Tools migration architecture, tool definitions, and integration points  
**Status:** READ-ONLY RESEARCH  

---

## 1. Executive Summary

The Guinevere MCP server is built using the FastMCP framework from the mcp Python package. It operates as a standalone systemd service (guinevere-mcp) and exposes a dynamic tool registry. All 7 required custom tools (postgres_tool, edis_tool, obscura_cdp, grep_app, context7, sequential_thinking, 	ime_tools) are fully implemented, properly decorated with auth-level gating, and registered via a centralized module dispatcher.

---

## 2. MCP Server Entry Point & Architecture

### 2.1 Server Factory
**File:** C:\Users\faizz\guinevere\src\mcp\manager.py

- **Framework:** mcp.server.fastmcp.FastMCP
- **Entry Point:** create_server(name: str = "guinevere-mcp") -> FastMCP
- **Execution:** if __name__ == "__main__": server = create_server(); server.run()
- **Lifespan Management:** Uses an async context manager (_build_lifespan) that:
  1. Logs startup.
  2. Calls egister_all_tools(server) from src.mcp.tools.
  3. Verifies uth_matrix completeness.
  4. Yields control to the server loop.
  5. Logs graceful shutdown.

### 2.2 Systemd Service Configuration
**File:** C:\Users\faizz\guinevere\systemd\guinevere-mcp.service

`ini
[Unit]
Description=Guinevere MCP Gateway Server
After=guinevere-core.service network.target
Requires=guinevere-core.service

[Service]
Type=exec
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
EnvironmentFile=/home/guinevere/code/guinevere/.env.mcp
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.mcp.manager
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Slice=guinevere.slice

# Resource limits
MemoryHigh=1G
MemoryMax=2G
CPUQuota=200%

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs /home/guinevere/evidence

[Install]
WantedBy=multi-user.target
`

---

## 3. Tool Registration Mechanism

**File:** C:\Users\faizz\guinevere\src\mcp\tools\__init__.py

The system uses a **dynamic registry pattern**. Every tool module must expose a egister_tools(mcp: FastMCP) -> None function.

`python
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
`

**Registration Pattern:** Tools are registered by passing the function to the server's tool decorator:
mcp.tool(name="tool_name")(function_name)

---

## 4. The 7 Custom Tools Inventory (MUST KEEP)

### 4.1 postgres_tool
**File:** C:\Users\faizz\guinevere\src\mcp\tools\postgres_tool.py  
**Purpose:** Read-only database queries with 3-layer defense-in-depth (READ ONLY transaction, SQL keyword classification, dedicated guinevere_readonly DB role).  
**Port:** 5433 (Guinevere-specific, isolated from Aizanta's 5432).  

| Function Signature | Decorator / Auth Level | Registered As |
|---|---|---|
| sync def postgres_query(sql: str, params: Sequence[Any] \| None = None) -> list[dict[str, Any]] | @require_approval(AuthLevel.READ_AUTO, tool_name="postgres_query") | postgres_query |
| sync def postgres_tables(schema: str = "public") -> list[str] | @require_approval(AuthLevel.READ_AUTO, tool_name="postgres_tables") | postgres_tables |
| sync def postgres_describe(table: str, schema: str = "public") -> list[dict[str, Any]] | @require_approval(AuthLevel.READ_AUTO, tool_name="postgres_describe") | postgres_describe |

### 4.2 edis_tool
**File:** C:\Users\faizz\guinevere\src\mcp\tools\redis_tool.py  
**Purpose:** Async Redis operations with command-level auth classification.  
**Port:** 6380 (Non-standard, project config).  
**Default DB:** 5 (Cost tracking namespace).  

| Function Signature | Decorator / Auth Level | Registered As |
|---|---|---|
| sync def redis_get(key: str, db: int = 5) -> str \| None | @require_approval(AuthLevel.READ_AUTO, tool_name="redis_get") | edis_get |
| sync def redis_keys(pattern: str = "*", db: int = 5) -> list[str] | @require_approval(AuthLevel.READ_AUTO, tool_name="redis_keys") | edis_keys |
| sync def redis_hgetall(key: str, db: int = 5) -> dict[str, str] | @require_approval(AuthLevel.READ_AUTO, tool_name="redis_hgetall") | edis_hgetall |
| sync def redis_lrange(key: str, start: int = 0, stop: int = -1, db: int = 5) -> list[str] | @require_approval(AuthLevel.READ_AUTO, tool_name="redis_lrange") | edis_lrange |
| sync def redis_set(key: str, value: str, ttl: int \| None = None, db: int = 5) -> bool | @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="redis_set") | edis_set |
| sync def redis_hset(key: str, field: str, value: str, db: int = 5) -> bool | @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="redis_hset") | edis_hset |
| sync def redis_del(key: str, db: int = 5) -> int | @require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="redis_del") | edis_del |
| sync def redis_flushdb(db: int \| None = None) -> bool | @require_approval(AuthLevel.FORBIDDEN, tool_name="redis_flushdb") | edis_flushdb |
| sync def redis_flushall() -> bool | @require_approval(AuthLevel.FORBIDDEN, tool_name="redis_flushall") | edis_flushall |

### 4.3 obscura_cdp
**File:** C:\Users\faizz\guinevere\src\mcp\tools\obscura_cdp.py  
**Purpose:** Browser automation via Obscura CDP + Playwright (no pixel rendering, markdown extraction only).  
**CDP URL:** ws://127.0.0.1:9222  

| Function Signature | Decorator / Auth Level | Registered As |
|---|---|---|
| sync def obscura_navigate(url: str) -> dict[str, str] | @require_approval(AuthLevel.READ_AUTO, tool_name="obscura_navigate") | obscura_navigate |
| sync def obscura_get_markdown(url: str) -> str | @require_approval(AuthLevel.READ_AUTO, tool_name="obscura_get_markdown") | obscura_get_markdown |
| sync def obscura_fill_form(url: str, selectors: dict[str, str]) -> dict[str, str] | @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="obscura_fill_form") | obscura_fill_form |
| sync def obscura_click(selector: str) -> dict[str, str] | @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="obscura_click") | obscura_click |

### 4.4 grep_app
**File:** C:\Users\faizz\guinevere\src\mcp\tools\grep_app.py  
**Purpose:** Code search across GitHub via the public grep.app API ( cost).  

| Function Signature | Decorator / Auth Level | Registered As |
|---|---|---|
| sync def grep_app_search(query: str, language: list[str] \| None = None, repo: str \| None = None, use_regexp: bool = False, match_case: bool = True) -> list[dict[str, str]] | @require_approval(AuthLevel.READ_AUTO, tool_name="grep_app_search") | grep_app_search |

### 4.5 context7
**File:** C:\Users\faizz\guinevere\src\mcp\tools\context7.py  
**Purpose:** Library documentation lookup via Context7 REST API with in-memory LRU caching and Redis cost tracking.  

| Function Signature | Decorator / Auth Level | Registered As |
|---|---|---|
| sync def context7_resolve(library_name: str, query: str = "") -> dict[str, str] | @require_approval(AuthLevel.READ_AUTO, tool_name="context7_resolve") | context7_resolve |
| sync def context7_query(library_id: str, query: str) -> dict[str, object] | @require_approval(AuthLevel.READ_AUTO, tool_name="context7_query") | context7_query |

### 4.6 sequential_thinking
**File:** C:\Users\faizz\guinevere\src\mcp\tools\sequential_thinking.py  
**Purpose:** Chain-of-thought reasoning with thought numbering, branching, and revision support (ephemeral in-memory sessions).  

| Function Signature | Decorator / Auth Level | Registered As |
|---|---|---|
| sync def sequential_think(thought: str, thought_number: int, total_thoughts: int, next_thought_needed: bool = True, is_revision: bool = False, revises_thought: int \| None = None, branch_from_thought: int \| None = None, branch_id: str \| None = None) -> dict[str, object] | @require_approval(AuthLevel.READ_AUTO, tool_name="sequential_thinking") | sequential_thinking |

### 4.7 	ime_tools
**File:** C:\Users\faizz\guinevere\src\mcp\tools\time_tools.py  
**Purpose:** Timezone-aware time operations using Python's stdlib zoneinfo. Default timezone: Asia/Jakarta.  

| Function Signature | Decorator / Auth Level | Registered As |
|---|---|---|
| sync def current_time(tz_name: str = "Asia/Jakarta", fmt: str = "%Y-%m-%d %H:%M:%S") -> str | @require_approval(AuthLevel.READ_AUTO, tool_name="time_current_time") | 	ime_current_time |
| sync def convert_time(source_tz: str, target_tz: str, time_str: str) -> str | @require_approval(AuthLevel.READ_AUTO, tool_name="time_convert_time") | 	ime_convert_time |
| sync def days_in_month(date: str \| None = None) -> int | @require_approval(AuthLevel.READ_AUTO, tool_name="time_days_in_month") | 	ime_days_in_month |
| sync def relative_time(time: str) -> str | @require_approval(AuthLevel.READ_AUTO, tool_name="time_relative_time") | 	ime_relative_time |
| sync def get_timestamp(time: str) -> int | @require_approval(AuthLevel.READ_AUTO, tool_name="time_get_timestamp") | 	ime_get_timestamp |
| sync def get_week_year(date: str \| None = None) -> dict[str, int] | @require_approval(AuthLevel.READ_AUTO, tool_name="time_get_week_year") | 	ime_get_week_year |

---

## 5. Additional Context: Other Registered Tools

For completeness, the following tools are also registered in src/mcp/tools/__init__.py but are **not** part of the 7 mandated to keep:
- rave_search
- docker_tool
- exa_search
- etch
- ilesystem
- git_tool
- github
- shell_tool
- websearch

---

## 6. Key Architectural Patterns for Migration

1. **Auth Gating:** Every tool function is decorated with @require_approval(AuthLevel.*, tool_name="...") from src.mcp.auth. This must be preserved or mapped to the new Hermes Agent auth system.
2. **Registration Contract:** Every tool file must export def register_tools(mcp: FastMCP) -> None. The migration must either maintain this contract or update src/mcp/tools/__init__.py to use the new registration mechanism.
3. **Path Resolution Hack:** src/mcp/manager.py contains a temporary sys.path manipulation to avoid shadowing the pip-installed mcp package with the local src/mcp directory. This should be reviewed during migration.
4. **Environment Variables:** Tools rely on specific env vars (e.g., POSTGRES_PASSWORD, REDIS_PASSWORD). The .env.mcp file referenced in the systemd service must be preserved.

---

## 7. Verification Checklist for Phase 4

- [ ] Verify guinevere-mcp.service ExecStart path matches new deployment structure.
- [ ] Ensure src/mcp/tools/__init__.py continues to import and register the 7 mandated tools.
- [ ] Validate that @require_approval decorators are compatible with the new Hermes Agent integration.
- [ ] Confirm .env.mcp contains all required secrets (POSTGRES_PASSWORD, REDIS_PASSWORD).
- [ ] Run python -m src.mcp.manager locally to verify tool registration count matches expected (16+ tools).

---
*Generated by Guinevere Research Agent. READ-ONLY. No modifications made to source code.*

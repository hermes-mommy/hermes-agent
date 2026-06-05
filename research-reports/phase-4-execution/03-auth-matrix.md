# Auth Matrix Enforcement State — Phase 4 Analysis

**Date:** 2026-06-05  
**Scope:** src/mcp/auth_matrix.py, src/mcp/auth.py, src/mcp/manager.py, src/hermes/safety_plugin.py, src/hermes_plugins/, src/mcp/tools/*.py  
**Verdict:** **Matrix definition is complete. Decorator enforcement path is wired. Safety plugin pre_tool_call is dead code. No active tool consumer exists.**

---

## 1. Auth Matrix Definition

**File:** src/mcp/auth_matrix.py

- AUTH_MATRIX dict has all 16 canonical tools mapped to AuthLevel values.
- ALL_TOOL_NAMES tuple explicitly lists all 16.
- erify_matrix_completeness() returns True (confirmed by test 	est_verify_matrix_completeness_returns_true).
- get_auth_level() performs lookup; raises KeyError for unknown tool or unknown operation.

### 16 Canonical Matrix Keys

| Key | Operations | Wildcard? |
|-----|-----------|-----------|
| rave_search | * → READ_AUTO | ✅ |
| context7 | resolve, query → READ_AUTO | ❌ |
| docker | ps, logs, inspect, images → READ_AUTO; start, stop, restart → WRITE_NOTIFY; rm, rmi → DESTRUCTIVE_APPROVAL; system_prune, rm_all → FORBIDDEN | ❌ |
| exa | * → READ_AUTO | ✅ |
| etch | * → READ_AUTO | ✅ |
| ilesystem | read, list → READ_AUTO; write → WRITE_NOTIFY; delete → DESTRUCTIVE_APPROVAL | ❌ |
| git | log, diff, status → READ_AUTO; commit, push → WRITE_NOTIFY; force_push → DESTRUCTIVE_APPROVAL; force_push_main → FORBIDDEN | ❌ |
| github | read, get, search → READ_AUTO; create_issue, create_pr → WRITE_NOTIFY; delete_repo → DESTRUCTIVE_APPROVAL | ❌ |
| grep_app | * → READ_AUTO | ✅ |
| obscura_cdp | navigate, read → READ_AUTO; form_fill, click → WRITE_NOTIFY; file_upload → DESTRUCTIVE_APPROVAL | ❌ |
| postgres | select, explain → READ_AUTO; insert, update, delete_row, drop, truncate → FORBIDDEN | ❌ |
| edis | get, lrange, hget, hgetall, keys, scan, ttl, exists, type → READ_AUTO; set, hset, lpush, rpush, sadd, setnx, setex, incr, incrbyfloat → WRITE_NOTIFY; del, expire, persist, rename → DESTRUCTIVE_APPROVAL; flushdb, flushall, config, debug, shutdown, slaveof → FORBIDDEN | ❌ |
| sequential_thinking | * → READ_AUTO | ✅ |
| shell | exec → DESTRUCTIVE_APPROVAL; rm_rf_root, sudo_rm_rf → FORBIDDEN | ❌ |
| 	ime | * → READ_AUTO | ✅ |
| websearch | * → READ_AUTO | ✅ |

**Test coverage:** 	ests/mcp/test_auth_matrix.py (437 lines) covers completeness, all 4 auth levels, wildcard behavior, and decorator behavior (FORBIDDEN, READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL) with parametrized samples.

---

## 2. Enforcement Paths

Three enforcement paths exist. Only one is active.

### Path A: @require_approval Decorator — **ACTIVE**

**Files:** src/mcp/auth.py (decorator), each src/mcp/tools/*.py (usage)

All 16 tool modules apply @require_approval(...) to every exported function. The decorator implements:

| AuthLevel | Behavior |
|-----------|----------|
| **READ_AUTO** | Executes immediately. No Discord notification. |
| **WRITE_NOTIFY** | Executes, then fires fire-and-forget Discord webhook. |
| **DESTRUCTIVE_APPROVAL** | Fires Discord notification, blocks on syncio.Event, waits for operator /approve or /deny (5-min timeout). |
| **FORBIDDEN** | Raises ForbiddenOperationError immediately — never executes. |

**RG-008 (matrix validation in decorator) is BROKEN:**

`python
# From src/mcp/auth.py line 177:
matrix_level = get_auth_level(name, "*")
`

This call has two issues:
1. **Tool name mismatch:** The decorator passes tool names like "context7_resolve", "redis_get", "fs_read", etc., but the matrix keys are "context7", "redis", "filesystem". Only 6 tools share matching names (rave_search, exa→exa_search? Actually exa_search vs matrix exa — mismatch too). Let me tabulate this properly below.
2. **Operation "*" is wrong:** For tools without a "*" wildcard (10 of 16), get_auth_level(name, "*") raises KeyError, which is caught and logged as uth_matrix_tool_missing — a false positive warning.

**This does NOT block execution.** The decorator's RG-008 check is warn-only. The actual auth level used for gating is the *declared* level in the decorator argument, not the matrix lookup. This means the decorator works correctly, but the matrix cross-validation is noise for 10/16 tools.

**Tool Name Mapping (decorator → matrix):**

| Decorator 	ool_name= value | Matrix key | Match? |
|---|---|---|
| rave_search | rave_search | ✅ |
| context7_resolve, context7_query | context7 | ❌ name |
| docker_ps etc. (no tool_name, uses fn name) | docker | ❌ name |
| exa_search | exa | ❌ name |
| etch_url | etch | ❌ name |
| s_read, s_write, s_delete, s_list | ilesystem | ❌ name |
| git_status, git_log, git_diff, git_commit, git_push, git_push_force | git | ❌ name |
| github_list_repos etc. | github | ❌ name |
| grep_app_search | grep_app | ❌ name |
| obscura_navigate etc. | obscura_cdp | ❌ name |
| postgres_query, postgres_tables, postgres_describe | postgres | ❌ name |
| edis_get, edis_keys, edis_hgetall, edis_lrange, edis_set, edis_hset, edis_del, edis_flushdb, edis_flushall | edis | ❌ name |
| sequential_thinking | sequential_thinking | ✅ |
| shell_exec | shell | ❌ name |
| 	ime_current_time, 	ime_convert_time, 	ime_days_in_month, 	ime_relative_time, 	ime_get_timestamp, 	ime_get_week_year | 	ime | ❌ name |
| websearch | websearch | ✅ |

Only 3 of 16 tool groups have matching names between decorator and matrix.

### Path B: Safety Plugin pre_tool_call Hook — **DEAD CODE**

**File:** src/hermes/safety_plugin.py (G09, lines 721–802)

The GuinevereSafetyPlugin.pre_tool_call() method:
- Looks up 	ool_name + operation from hermes-agent kwargs
- Blocks if FORBIDDEN or DESTRUCTIVE_APPROVAL
- Allowed if READ_AUTO or WRITE_NOTIFY
- Unknown tool → KeyError caught → blocks (fail-closed ✅)
- Auth module unavailable → returns None (fail-open, logged)

**This hook is registered but NEVER fires** because hermes-agent has **all toolsets disabled**:

`python
# src/hermes/session_adapter.py lines 136-137:
enabled_toolsets=[],
disabled_toolsets=["*"],
`

The AIAgent instance is created as a pure LLM with zero tools. The pre_tool_call hook is only invoked when hermes-agent is about to call one of its own tools. Since no tools are enabled, the hook is never reached.

**THEORETICAL ISSUE if activated:** The hook blocks DESTRUCTIVE_APPROVAL operations, which would prevent the equire_approval decorator's Discord approval workflow from ever executing. The /approve and /deny slash commands check _pending_approvals from src/mcp.auth, which only gets populated when the decorator calls _wait_for_approval(). If the safety plugin blocks first, no pending approval entry is created, and the operator can never approve it.

**Test coverage:** 	ests/hermes/test_safety_plugin.py has 6 tests for G09 (TestToolAuthGate) — all using mocked auth matrix.

### Path C: MCP Server Startup Verification — **PASSIVE**

**File:** src/mcp/manager.py lines 57–68

The FastMCP server's lifespan handler calls erify_matrix_completeness() at startup and logs the result. This is a passive check — it does not enforce auth on any tool call path.

**This runs every time the MCP server starts.** Confirmed by systemd unit guinevere-mcp.service which starts python -m src.mcp.manager.

---

## 3. Runtime Architecture — No Active Tool Consumer

The system has two independent processes:

### Process 1: Discord Bot (guinevere-discord.service)
- python -m src.discord.bot
- Uses HermesSessionAdapter → wraps AIAgent with enabled_toolsets=[]
- Pure LLM conversational agent — **no tool calling**
- The safety plugin registers pre_tool_call hook, but it's never triggered

### Process 2: MCP Server (guinevere-mcp.service)
- python -m src.mcp.manager
- FastMCP server with all 16 tools registered, each gated by @require_approval
- **No MCP clients exist** in the codebase — src/ has zero MCP client imports
- Tools are defined and decorated but have no active consumer

### Summary Table

| Aspect | Status |
|--------|--------|
| Auth matrix definition | ✅ Complete (16/16 tools) |
| Matrix startup verification | ✅ Runs at MCP server boot |
| Decorator enforcement | ✅ Active on all 16 tool modules |
| Decorator RG-008 cross-check | ❌ Broken for 10/16 tools (false warnings) |
| Safety plugin pre_tool_call | ❌ Dead code (no active tools in hermes) |
| Hermes tools enabled | ❌ enabled_toolsets=[] |
| MCP clients | ❌ None exist |
| Unknown tool handling (matrix) | ✅ Raises KeyError |
| Unknown tool handling (safety plugin) | ✅ Blocks (fail-closed) |
| Unknown tool handling (decorator) | ⚠️ Logs warning, continues (fail-open) |

---

## 4. Gaps and Issues

### G-01: No active tool consumer (HIGH)
Neither the Discord bot (hermes-agent) nor any MCP client actually invokes tools. The decorator enforcement works correctly but is never exercised in production. Phase 4 must define who calls the tools.

### G-02: Safety plugin pre_tool_call blocks DESTRUCTIVE_APPROVAL (HIGH)
If activated, the hook would block DESTRUCTIVE_APPROVAL before the decorator's Discord approval flow. The /approve and /deny commands would never see pending approvals. Fix: change pre_tool_call to allow DESTRUCTIVE_APPROVAL through, or integrate the approval flow into the hook.

### G-03: Decorator RG-008 cross-validation broken (MEDIUM)
get_auth_level(name, "*") with tool names and operations that don't match the matrix keys causes false uth_matrix_tool_missing warnings for 10/16 tools. Fix either the tool names or use a proper lookup that maps decorator names to matrix keys.

### G-04: Tool name mismatch between matrix and FastMCP (MEDIUM)
Matrix keys use canonical names (git, edis, ilesystem). FastMCP tool names use specific operation-level names (git_status, edis_get, s_read). If a future integration needs to look up auth by FastMCP tool name, it will fail. Consider adding a reverse mapping from FastMCP tool names → matrix keys.

### G-05: Auth module import failure == fail-open (LOW)
If uth_matrix.py fails to import, the safety plugin sets _auth_available = False and allows all tools through. The decorator path still works (it imports directly from src.mcp.auth).

### G-06: No MCP client for Discord bot (LOW)
For Phase 4, if the goal is to make hermes-agent call MCP tools, you need to either:
- Enable hermes tools and wire them to the MCP server protocol
- Or use the mcp Python client SDK to connect the Discord bot to the MCP server
- Or use FastMCP's tool definitions directly via Python import (bypass MCP protocol)

---

## 5. Conclusion

**The auth matrix is comprehensively defined and has a working decorator-based enforcement path, but there is no active consumer of the MCP tools.** The safety plugin's pre_tool_call hook (G09) is registered but dead code. Phase 4 needs to close the gap between tool definition and actual tool invocation, and fix the DESTRUCTIVE_APPROVAL blocking behavior in the safety plugin if the hermes-agent tool path is activated.


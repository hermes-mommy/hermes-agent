# D04 — AUTH MATRIX ENFORCEMENT AUDIT

**Audit Date**: 2026-06-03  
**Auditor**: Guinevere (Sisyphus-Junior)  
**Dimension**: 4 — Auth Matrix Enforcement  
**Status**: **FAIL** (2 CRITICAL findings)  
**Scope**: `src/mcp/auth.py`, `src/mcp/auth_matrix.py`, 16 tool modules, `tests/mcp/test_auth_matrix.py`

---

## 1. What Was Audited

Full-stack auth matrix audit: the `AuthLevel` enum, the `AUTH_MATRIX` registry, all 16 tool modules for decorator coverage and correctness, FORBIDDEN behaviour, bypass paths, test coverage, and the `verify_matrix_completeness()` function.

---

## 2. Summary — Pass/Fail Matrix

| # | Tool | Auth Levels Correct | Decorator Present | No Bypass | Faiz Mandate Match | Verdict |
|---|---|---|---|---|---|---|
| 1 | brave_search | ✅ | ✅ | ✅ | ✅ | **PASS** |
| 2 | context7 | ✅ | ⚠️ (wrappers only) | ❌ bare funcs unprotected | ✅ | **NEEDS REVIEW** |
| 3 | exa_search | ✅ | ✅ | ✅ | ✅ | **PASS** |
| 4 | fetch | ✅ | ⚠️ (wrapper only) | ❌ fetch_url() bare | ✅ | **NEEDS REVIEW** |
| 5 | grep_app | ✅ | ✅ | ✅ | ✅ | **PASS** |
| 6 | sequential_thinking | ✅ | ⚠️ (wrapper only) | ❌ sequential_think() bare | ✅ | **NEEDS REVIEW** |
| 7 | time | ✅ | ⚠️ (wrappers only) | ❌ 6 bare funcs | ✅ | **NEEDS REVIEW** |
| 8 | websearch | ✅ | ✅ | ✅ (double-auth on subs) | ✅ | **PASS** |
| 9 | filesystem | ✅ | ⚠️ (wrappers only) | ❌ 4 bare funcs | ✅ | **NEEDS REVIEW** |
| 10 | github | ✅ | ✅ | ✅ | ✅ | **PASS** |
| 11 | git | ✅ | ⚠️ (wrappers only) | ❌ 5 bare funcs | ✅ | **NEEDS REVIEW** |
| 12 | obscura_cdp | ✅ | ⚠️ (wrappers only) | ❌ 4 bare funcs | ✅ | **NEEDS REVIEW** |
| 13 | postgres | ❌ | ⚠️ (wrapper only) | ❌ bare + level mismatch | ❌ | **FAIL** |
| 14 | redis | ⚠️ | ⚠️ (wrappers only) | ❌ all bare funcs | ❌ | **FAIL** |
| 15 | shell | ✅ | ⚠️ (wrapper only) | ❌ shell_exec() bare | ✅ | **NEEDS REVIEW** |
| 16 | docker | ⚠️ | ⚠️ (wrappers only) | ❌ all bare funcs | ⚠️ | **NEEDS REVIEW** |

---

## 3. Core Infrastructure (PASS)

### 3.1 AuthLevel Enum — PASS ✅

**File**: `src/mcp/auth.py` lines 42-48

```
class AuthLevel(enum.Enum):
    READ_AUTO = "read_auto"
    WRITE_NOTIFY = "write_notify"
    DESTRUCTIVE_APPROVAL = "destructive_approval"
    FORBIDDEN = "forbidden"
```

Exactly 4 values. Tested by `test_auth_level_enum_has_exactly_4_values`. **PASS**.

### 3.2 ForbiddenOperationError — PASS ✅

**File**: `src/mcp/auth.py` line 56-57

`ForbiddenOperationError(Exception)` exists and is raised in all three places:
- `require_approval()` decorator when `level is AuthLevel.FORBIDDEN` (line 175)
- `require_approval()` decorator when DESTRUCTIVE_APPROVAL denied/timed out (line 208)
- `git_tool.py:_git_push()` when force push to main/master (line 286)
- `shell_tool.py:CommandForbiddenError` subclasses it
- `docker_tool.py:DockerForbiddenError` subclasses it

**PASS**.

### 3.3 require_approval() Decorator — PASS ✅

**File**: `src/mcp/auth.py` lines 148-216

4-tier dispatch:
- `FORBIDDEN` → raises `ForbiddenOperationError` immediately (line 175)  
- `READ_AUTO` → executes directly (line 181)
- `WRITE_NOTIFY` → executes, then fire-and-forget Discord webhook via `asyncio.create_task()` (lines 186-194)
- `DESTRUCTIVE_APPROVAL` → sends Discord notification, waits on `asyncio.Event` with 300s timeout, raises `ForbiddenOperationError` on deny/timeout (lines 196-212)

**PASS**.

### 3.4 AUTH_MATRIX Registration — PASS ✅

**File**: `src/mcp/auth_matrix.py` lines 52-166

All 16 canonical tool names in `ALL_TOOL_NAMES` match the keys of `AUTH_MATRIX`. `verify_matrix_completeness()` returns `True`. Tested by `test_matrix_has_all_16_tools`.

**PASS**.

### 3.5 Test Coverage — PASS ✅

**File**: `tests/mcp/test_auth_matrix.py`

16 test methods in `TestAuthMatrix`:
- Completeness: `test_matrix_has_all_16_tools`, `test_verify_matrix_completeness_returns_true`
- Enum check: `test_auth_level_enum_has_exactly_4_values`
- Parametrized auth-level lookups: samples from all 4 levels across all 16 tools
- Error cases: unknown tool, unknown operation
- Wildcard behaviour: `test_wildcard_tools_return_same_level_for_any_operation`
- Behavioural tests: FORBIDDEN raises, READ_AUTO no webhook, WRITE_NOTIFY fires webhook, DESTRUCTIVE_APPROVAL deny/approve/blocking
- Operation count: `test_every_tool_has_at_least_one_operation`

All 16 tools sampled in `_SAMPLE_READ_AUTO`, `_SAMPLE_WRITE_NOTIFY`, `_SAMPLE_DESTRUCTIVE`, `_SAMPLE_FORBIDDEN` parametrized test lists.

**PASS**.

---

## 4. Per-Tool Detailed Analysis

### 4.1 brave_search — PASS ✅

- **File**: `src/mcp/tools/brave_search.py`
- **Decorator**: `@require_approval(AuthLevel.READ_AUTO, tool_name="brave_search")` on line 134 — directly on `brave_search()` function
- **Matrix**: `"*": AuthLevel.READ_AUTO` → **MATCH**
- **Faiz Mandate**: Read-Auto → **MATCH**
- **Bypass**: No bare internal function. All helpers (`_fetch_search`, `_record_cost`, `_get_api_key`) are internal. **SAFE**.

### 4.2 context7 — NEEDS REVIEW ⚠️

- **File**: `src/mcp/tools/context7.py`
- **Decorator**: `@require_approval(AuthLevel.READ_AUTO)` on wrapper functions `_context7_resolve` (line 376) and `_context7_query` (line 392) inside `register_tools()`
- **Matrix**: `"resolve": READ_AUTO`, `"query": READ_AUTO` → **MATCH**
- **Faiz Mandate**: Read-Auto → **MATCH**
- **⚠️ BYPASS VULNERABILITY**: `context7_resolve()` (line 192) and `context7_query()` (line 287) are **bare async functions without `@require_approval`**. Any code that imports and calls `context7_resolve()` or `context7_query()` directly bypasses the auth gate entirely. The auth decorator exists **only** on the `register_tools()` wrapper functions that are different objects.

### 4.3 exa_search — PASS ✅

- **File**: `src/mcp/tools/exa_search.py`
- **Decorator**: `@require_approval(AuthLevel.READ_AUTO, tool_name="exa_search")` on line 159 — directly on `exa_search()` function
- **Matrix**: `"*": AuthLevel.READ_AUTO` → **MATCH**
- **Faiz Mandate**: Read-Auto → **MATCH**
- **Bypass**: No bare internal function. **SAFE**.

### 4.4 fetch — NEEDS REVIEW ⚠️

- **File**: `src/mcp/tools/fetch.py`
- **Decorator**: `@require_approval(AuthLevel.READ_AUTO, tool_name="fetch_url")` on wrapper `_fetch_url_tool` (line 205) inside `register_tools()`
- **Matrix**: `"*": AuthLevel.READ_AUTO` → **MATCH**
- **Faiz Mandate**: Read-Auto → **MATCH**
- **⚠️ BYPASS VULNERABILITY**: `fetch_url()` (line 98) is a **bare async function without `@require_approval`**. Direct import + call bypasses auth.

### 4.5 grep_app — PASS ✅

- **File**: `src/mcp/tools/grep_app.py`
- **Decorator**: `@require_approval(AuthLevel.READ_AUTO, tool_name="grep_app_search")` on line 157 — directly on `grep_app_search()` function
- **Matrix**: `"*": AuthLevel.READ_AUTO` → **MATCH**
- **Faiz Mandate**: Read-Auto → **MATCH**
- **Bypap**: No bare internal function. **SAFE**.

### 4.6 sequential_thinking — NEEDS REVIEW ⚠️

- **File**: `src/mcp/tools/sequential_thinking.py`
- **Decorator**: `@require_approval(AuthLevel.READ_AUTO, tool_name="sequential_thinking")` on wrapper `_sequential_think` (line 398) inside `register_tools()`
- **Matrix**: `"*": AuthLevel.READ_AUTO` → **MATCH**
- **Faiz Mandate**: Read-Auto → **MATCH**
- **⚠️ BYPASS VULNERABILITY**: `sequential_think()` (line 307) is a **bare async function**. Direct import + call bypasses auth. Additional bare internal functions (`create_session`, `add_thought`, `branch_thought`, `revise_thought`, `finalize_session`) are also unprotected.

### 4.7 time — NEEDS REVIEW ⚠️

- **File**: `src/mcp/tools/time_tools.py`
- **Decorator**: 6 wrappers inside `register_tools()` (lines 227-297), all `@require_approval(AuthLevel.READ_AUTO)`
- **Matrix**: `"*": AuthLevel.READ_AUTO` → **MATCH**
- **Faiz Mandate**: Read-Auto → **MATCH**
- **⚠️ BYPASS VULNERABILITY**: All 6 bare functions unprotected: `current_time()`, `convert_time()`, `days_in_month()`, `relative_time()`, `get_timestamp()`, `get_week_year()`. Direct import + call bypasses auth.

### 4.8 websearch — PASS ✅

- **File**: `src/mcp/tools/websearch.py`
- **Decorator**: `@require_approval(AuthLevel.READ_AUTO, tool_name="websearch")` on line 38 — directly on `websearch()` function
- **Matrix**: `"*": AuthLevel.READ_AUTO` → **MATCH**
- **Faiz Mandate**: Read-Auto → **MATCH**
- **Note**: `websearch()` internally calls `brave_search()` and `exa_search()` — both are **already decorated** with `@require_approval`. This means calling websearch → auth checks websearch AND brave_search/exa_search. **Double auth gating** — functionally safe but redundant; each sub-call fires its own auth workflow. Not a bypass but a design note.

### 4.9 filesystem — NEEDS REVIEW ⚠️

- **File**: `src/mcp/tools/filesystem.py`
- **Decorators**: 4 wrappers inside `register_tools()`:
  - `_fs_read` → `READ_AUTO` ✅
  - `_fs_write` → `WRITE_NOTIFY` ✅
  - `_fs_delete` → `DESTRUCTIVE_APPROVAL` ✅
  - `_fs_list` → `READ_AUTO` ✅
- **Matrix**: `"read": READ_AUTO`, `"list": READ_AUTO`, `"write": WRITE_NOTIFY`, `"delete": DESTRUCTIVE_APPROVAL` → **ALL MATCH**
- **Faiz Mandate**: All levels match → **MATCH**
- **⚠️ BYPASS VULNERABILITY**: All 4 bare functions unprotected: `fs_read()`, `fs_write()`, `fs_delete()`, `fs_list()`. Direct import + call bypasses auth. **CRITICAL** — `fs_write()` and `fs_delete()` are particularly dangerous as bare functions.

### 4.10 github — PASS ✅ with notes

- **File**: `src/mcp/tools/github.py`
- **Decorators**: Directly on all 5 functions:
  - `github_list_repos` → `READ_AUTO` ✅ (line 137)
  - `github_get_file` → `READ_AUTO` ✅ (line 157)
  - `github_search_code` → `READ_AUTO` ✅ (line 222)
  - `github_create_issue` → `WRITE_NOTIFY` ✅ (line 178)
  - `github_create_pr` → `WRITE_NOTIFY` ✅ (line 200)
- **Matrix**: `"read"`, `"get"`, `"search"` → READ_AUTO; `"create_issue"`, `"create_pr"` → WRITE_NOTIFY → **MATCH**
- **Faiz Mandate**: All levels match → **MATCH**
- **Bypass**: None. All functions directly decorated. **SAFE**.
- **⚠️ Note**: AUTH_MATRIX has `"delete_repo": DESTRUCTIVE_APPROVAL` but **no `github_delete_repo` tool exists** anywhere in `github.py`. The matrix entry is dead — no corresponding MCP tool to gate. This is a **matrix-tool mismatch**.

### 4.11 git — NEEDS REVIEW ⚠️

- **File**: `src/mcp/tools/git_tool.py`
- **Decorators**: 6 wrappers inside `register_tools()`:
  - `git_status` → `READ_AUTO` (line 323) ✅
  - `git_log` → `READ_AUTO` (line 328) ✅
  - `git_diff` → `READ_AUTO` (line 333) ✅
  - `git_commit` → `WRITE_NOTIFY` (line 338) ✅
  - `git_push` → `WRITE_NOTIFY` (line 347) ✅
  - `git_push_force` → `DESTRUCTIVE_APPROVAL` (line 355) ✅
- **Matrix**: `"log"`, `"diff"`, `"status"` → READ_AUTO; `"commit"` → WRITE_NOTIFY; `"push"` → WRITE_NOTIFY; `"force_push"` → DESTRUCTIVE_APPROVAL; `"force_push_main"` → FORBIDDEN → **MATCH**
- **Faiz Mandate**: All levels match → **MATCH**
- **⚠️ BYPASS VULNERABILITY**: All 5 bare functions unprotected: `_git_status()`, `_git_log()`, `_git_diff()`, `_git_commit()`, `_git_push()`. **CRITICAL** — `_git_commit()` and `_git_push()` are bare write/destructive operations.
- **Defense-in-depth**: `_git_push()` has internal `_is_forbidden()` check for force push to main/master, which raises `ForbiddenOperationError` at runtime. This works but is **inside** the bare function — if the auth decorator were the only gate, the bare function would still execute the forbidden check. Good redundancy.

### 4.12 obscura_cdp — NEEDS REVIEW ⚠️

- **File**: `src/mcp/tools/obscura_cdp.py`
- **Decorators**: 4 wrappers inside `register_tools()`:
  - `_obscura_navigate` → `READ_AUTO` ✅
  - `_obscura_get_markdown` → `READ_AUTO` ✅
  - `_obscura_fill_form` → `WRITE_NOTIFY` ✅
  - `_obscura_click` → `WRITE_NOTIFY` ✅
- **Matrix**: `"navigate": READ_AUTO`, `"read": READ_AUTO`, `"form_fill": WRITE_NOTIFY`, `"click": WRITE_NOTIFY` → **MATCH**
- **Faiz Mandate**: All levels match → **MATCH**
- **⚠️ BYPASS VULNERABILITY**: All 4 bare functions unprotected: `obscura_navigate()`, `obscura_get_markdown()`, `obscura_fill_form()`, `obscura_click()`.
- **⚠️ Note**: AUTH_MATRIX has `"file_upload": DESTRUCTIVE_APPROVAL` but **no `obscura_file_upload` tool exists** anywhere in `obscura_cdp.py`. Dead matrix entry.

### 4.13 postgres — FAIL ❌ [CRITICAL FINDING #1]

- **File**: `src/mcp/tools/postgres_tool.py`
- **Decorators**: 3 wrappers inside `register_tools()`:
  - `_postgres_query_tool` → `READ_AUTO` (line 293)
  - `_postgres_tables_tool` → `READ_AUTO` (line 312)
  - `_postgres_describe_tool` → `READ_AUTO` (line 322)
- **Matrix operations**:
  - `"select": READ_AUTO`, `"explain": READ_AUTO` → **MATCH** ✅
  - `"insert": DESTRUCTIVE_APPROVAL` → **NO TOOL EXISTS** ❌
  - `"update": DESTRUCTIVE_APPROVAL` → **NO TOOL EXISTS** ❌
  - `"delete_row": DESTRUCTIVE_APPROVAL` → **NO TOOL EXISTS** ❌
  - `"drop": FORBIDDEN` → **NO TOOL EXISTS** ❌
  - `"truncate": FORBIDDEN` → **NO TOOL EXISTS** ❌
- **Faiz Mandate**:
  - Read-Auto: `postgres(SELECT)` → MATCH ✅
  - Destructive-Approval: `postgres(INSERT/UPDATE/DELETE)` → **NO TOOL** ❌
  - Forbidden: `postgres(DROP/TRUNCATE)` → **NO TOOL** ❌

**WHAT HAPPENS INSTEAD**: `postgres_query()` has internal SQL classification via `classify_sql()` (lines 34-87) that:
- Allows: SELECT, SHOW, EXPLAIN, WITH → executes as READ_AUTO
- **Blocks**: INSERT/UPDATE/DELETE by raising `ForbiddenOperationError` immediately (lines 192-196)
- **Blocks**: DROP/TRUNCATE/ALTER/CREATE/GRANT/REVOKE by raising `ForbiddenOperationError` (lines 187-190)

So the tool **actively prevents write operations** rather than gating them with DESTRUCTIVE_APPROVAL. The AUTH_MATRIX declares INSERT/UPDATE/DELETE as DESTRUCTIVE_APPROVAL, but the tool implementation blocks them outright. This means:
1. **Matrix-tool mismatch**: AUTH_MATRIX says "requires Faiz approval" but the tool says "never"
2. **Functionality gap**: There is no way to execute INSERT/UPDATE/DELETE through the MCP tool at all
3. **Level mismatch**: AUTH_MATRIX says DESTRUCTIVE_APPROVAL, tool says FORBIDDEN (via classify_sql returning "write" → ForbiddenOperationError)

**⚠️ BYPASS VULNERABILITY**: `postgres_query()`, `postgres_tables()`, `postgres_describe()` are all bare functions without `@require_approval`. Direct import + call bypasses auth. The only protection on `postgres_query()` is the internal `classify_sql()` which blocks writes — but this is defense-in-depth, not proper auth gating.

### 4.14 redis — FAIL ❌ [CRITICAL FINDING #2]

- **File**: `src/mcp/tools/redis_tool.py`
- **Decorators**: 9 wrappers inside `register_tools()`:
  - `_redis_get`, `_redis_keys`, `_redis_hgetall`, `_redis_lrange` → `READ_AUTO` ✅
  - `_redis_set`, `_redis_hset` → `WRITE_NOTIFY` ✅
  - `_redis_del` → `DESTRUCTIVE_APPROVAL` ✅
  - `_redis_flushdb`, `_redis_flushall` → `FORBIDDEN` ✅
- **Matrix vs Faiz Mandate**:
  - `"flushdb": FORBIDDEN` in AUTH_MATRIX (line 142)
  - Faiz mandate says `redis(DEL/FLUSHDB)` → **DESTRUCTIVE_APPROVAL**

**DISCREPANCY**: Faiz explicitly mandates `redis(FLUSHDB)` as DESTRUCTIVE_APPROVAL but AUTH_MATRIX has it as FORBIDDEN. This is a direct violation of operator mandate. Either:
- AUTH_MATRIX is wrong (should be DESTRUCTIVE_APPROVAL per Faiz)
- Faiz's mandate in this audit spec is outdated and AUTH_MATRIX is correct
- **Resolution needed from Faiz**

- **⚠️ BYPASS VULNERABILITY**: All 9 bare functions are unprotected. `redis_del()`, `redis_flushdb()`, `redis_flushall()` can be called directly with no auth gate. The FORBIDDEN functions have internal `raise ForbiddenOperationError` bodies (lines 335, 349) but the decorator is the primary gate and it's on the wrapper, not the bare function.

### 4.15 shell — NEEDS REVIEW ⚠️

- **File**: `src/mcp/tools/shell_tool.py`
- **Decorator**: `@require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="shell_exec")` on wrapper `shell_exec_mcp` (line 356)
- **Matrix**: `"exec": DESTRUCTIVE_APPROVAL`, `"rm_rf_root": FORBIDDEN`, `"sudo_rm_rf": FORBIDDEN` → **MATCH** (for the registered tool)
- **Faiz Mandate**: `shell(all)` → DESTRUCTIVE_APPROVAL; `shell(rm -rf /)` → FORBIDDEN → **MATCH**
- **⚠️ BYPASS VULNERABILITY**: `shell_exec()` (line 302) is bare. Direct import + call bypasses auth.
- **Note**: FORBIDDEN patterns (`rm_rf_root`, `sudo_rm_rf`) are enforced via `BLOCKED_PATTERNS` (lines 65-82) in `_check_blocked_patterns()`, not via separate MCP tools. The matrix entries exist for documentation but enforcement is via pattern matching. Functional, but not a 1:1 tool-matrix mapping.

### 4.16 docker — NEEDS REVIEW ⚠️

- **File**: `src/mcp/tools/docker_tool.py`
- **Decorators**: 11 wrappers inside `register_tools()`:
  - `docker_ps_mcp`, `docker_logs_mcp`, `docker_inspect_mcp`, `docker_images_mcp` → `READ_AUTO` ✅
  - `docker_start_mcp`, `docker_stop_mcp`, `docker_restart_mcp` → `WRITE_NOTIFY` ✅
  - `docker_rm_mcp`, `docker_rmi_mcp` → `DESTRUCTIVE_APPROVAL` ✅
  - `docker_system_prune_mcp`, `docker_rm_all_mcp` → `FORBIDDEN` ✅
- **Matrix**: All operations match except:
  - `"system_prune": FORBIDDEN` → matches `docker_system_prune` ✅
  - **`docker_rm_all` exists in code but NOT in AUTH_MATRIX** — the tool is registered at FORBIDDEN but has no corresponding matrix entry.
- **Faiz Mandate**: All levels match → **MATCH**
- **⚠️ BYPASS VULNERABILITY**: All 11 bare functions unprotected including `docker_rm()`, `docker_rmi()`, `docker_system_prune()`, `docker_rm_all()`.

---

## 5. CRITICAL FINDINGS

### CRITICAL #1: Postgres — Matrix-Tool Architecture Mismatch [FAIL]

| Aspect | AUTH_MATRIX says | Tool does |
|---|---|---|
| INSERT/UPDATE/DELETE | `DESTRUCTIVE_APPROVAL` | Raises `ForbiddenOperationError` (blocked) |
| DROP/TRUNCATE | `FORBIDDEN` | Raises `ForbiddenOperationError` (blocked) |

The AUTH_MATRIX declares that INSERT/UPDATE/DELETE should require Faiz's approval via Discord. However, `postgres_query()` classifies these as "write" and raises `ForbiddenOperationError` before the auth decorator would even reach them. There is **no dedicated MCP tool** for INSERT/UPDATE/DELETE/DROP/TRUNCATE operations. The matrix entries for these operations are **dead entries with no corresponding implementation**.

This is both a security hardening (write ops blocked at SQL parsing layer) AND an architecture mismatch (matrix says one thing, tool does another).

### CRITICAL #2: Redis FLUSHDB — Operator Mandate vs Matrix Conflict [FAIL]

| Source | FLUSHDB level | FLUSHALL level |
|---|---|---|
| Faiz's mandate (this audit) | `DESTRUCTIVE_APPROVAL` | `FORBIDDEN` |
| AUTH_MATRIX (code) | `FORBIDDEN` | `FORBIDDEN` |

Direct conflict between Faiz's stated requirement (`redis(DEL/FLUSHDB)` as DESTRUCTIVE_APPROVAL) and the AUTH_MATRIX implementation which classifies FLUSHDB as FORBIDDEN. **Requires Faiz resolution**.

---

## 6. SYSTEMIC FINDINGS

### 6.1 Bypass Vulnerability Pattern — 12 of 16 Tools Affected [HIGH SEVERITY]

**Pattern**: Many tool modules define bare async functions (`tool_operation()`) that contain the business logic, and then wrap them with `@require_approval`-decorated wrappers inside `register_tools()`. The bare functions are imported and called by the wrapper — but they are also **importable and callable directly by any other code**, bypassing the auth gate entirely.

**Tools with DIRECT decorator (no bypass)**: brave_search, exa_search, grep_app, websearch, github (5 of 16)

**Tools with WRAPPER-ONLY decorator (bypass possible)**: context7, fetch, sequential_thinking, time, filesystem, git, obscura_cdp, postgres, redis, shell, docker (11 of 16 — but context7/sequential_thinking have internal defense layers)

**Impact**: If another tool (like websearch, which imports `brave_search` and `exa_search`) were to import bare `fs_write()` instead, it could write files without triggering WRITE_NOTIFY or the Discord webhook. The auth system relies entirely on the MCP tool registration wrappers, not on the underlying function contracts.

**Mitigation**: Move `@require_approval` decorators onto the bare functions themselves (as done in brave_search, exa_search, github). The wrapper pattern in `register_tools()` should only add `@mcp.tool()` — the auth decorator belongs on the underlying function.

### 6.2 Dead Matrix Entries — 3 Tools Affected [MEDIUM SEVERITY]

AUTH_MATRIX declares operations that have no corresponding MCP tool implementation:

| Tool | Dead Matrix Entry | Expected Level | Actual |
|---|---|---|---|
| github | `"delete_repo"` | DESTRUCTIVE_APPROVAL | No tool exists |
| obscura_cdp | `"file_upload"` | DESTRUCTIVE_APPROVAL | No tool exists |
| docker | `docker_rm_all` | (not in matrix) | Tool exists at FORBIDDEN |

The `docker_rm_all` inverse case: tool exists in code but **not in AUTH_MATRIX** — `verify_matrix_completeness()` would not catch this because it only checks that all ALL_TOOL_NAMES are in the matrix, not that all registered tools have matrix entries.

### 6.3 Websearch Double-Auth [LOW SEVERITY]

`websearch()` calls `brave_search()` and `exa_search()` which are already decorated. This means:
1. `websearch` auth check: READ_AUTO → passes
2. Inside websearch, `brave_search()` is called → triggers ANOTHER READ_AUTO auth check
3. The second check is redundant — the caller was already authorized

This produces duplicate auth logs and, for WRITE_NOTIFY/DESTRUCTIVE_APPROVAL levels, would fire multiple Discord notifications for a single user action.

---

## 7. Files Audited

| File | Purpose | Lines |
|---|---|---|
| `src/mcp/auth.py` | AuthLevel enum, require_approval decorator, approval state | 216 |
| `src/mcp/auth_matrix.py` | AUTH_MATRIX registry, verify_matrix_completeness() | 277 |
| `src/mcp/tools/brave_search.py` | Brave Search tool | 177 |
| `src/mcp/tools/context7.py` | Context7 documentation tool | 407 |
| `src/mcp/tools/exa_search.py` | Exa semantic search tool | 212 |
| `src/mcp/tools/fetch.py` | Web content fetch tool | 213 |
| `src/mcp/tools/grep_app.py` | grep.app code search tool | 224 |
| `src/mcp/tools/sequential_thinking.py` | Chain-of-thought reasoning tool | 420 |
| `src/mcp/tools/time_tools.py` | Timezone conversion tools | 297 |
| `src/mcp/tools/websearch.py` | Hybrid search (Brave+Exa) tool | 164 |
| `src/mcp/tools/filesystem.py` | File I/O with path whitelist | 210 |
| `src/mcp/tools/github.py` | GitHub REST API tool | 254 |
| `src/mcp/tools/git_tool.py` | Local git operations | 362 |
| `src/mcp/tools/obscura_cdp.py` | Browser automation via Obscura CDP | 247 |
| `src/mcp/tools/postgres_tool.py` | PostgreSQL read-only queries | 333 |
| `src/mcp/tools/redis_tool.py` | Async Redis operations | 444 |
| `src/mcp/tools/shell_tool.py` | Whitelisted shell command execution | 364 |
| `src/mcp/tools/docker_tool.py` | Docker container lifecycle management | 614 |
| `tests/mcp/test_auth_matrix.py` | Auth matrix tests | 436 |

**Total**: 19 files, ~5,500 lines of code audited.

---

## 8. Final Verdict

**OVERALL: FAIL**

| Category | Status |
|---|---|
| AuthLevel enum (4 values) | ✅ PASS |
| require_approval decorator | ✅ PASS |
| AUTH_MATRIX completeness | ✅ PASS |
| verify_matrix_completeness() | ✅ PASS |
| Test coverage | ✅ PASS |
| Direct decorator on 5 tools | ✅ PASS |
| Bypass vulnerability (11 tools) | ❌ NEEDS REVIEW |
| Postgres matrix-tool mismatch | ❌ FAIL |
| Redis FLUSHDB mandate conflict | ❌ FAIL |
| Dead matrix entries | ⚠️ NEEDS REVIEW |
| Double-auth in websearch | ⚠️ NOTE |

**Rationale**: Two CRITICAL FAIL findings (Postgres matrix-tool mismatch, Redis FLUSHDB mandate conflict) make this dimension a FAIL per audit rules. The systemic bypass vulnerability pattern affecting 11 of 16 tools is a HIGH SEVERITY finding that compounds the failures.

### Required Fixes (minimum for re-audit to PASS):

1. **Postgres**: Either (a) create dedicated MCP tools for INSERT/UPDATE/DELETE at DESTRUCTIVE_APPROVAL, or (b) update AUTH_MATRIX to reflect actual behaviour (all writes blocked → FORBIDDEN)
2. **Redis FLUSHDB**: Resolve Faiz mandate vs AUTH_MATRIX conflict — either change matrix to DESTRUCTIVE_APPROVAL or confirm matrix is correct (FORBIDDEN)
3. **Bypass Fix**: Move `@require_approval` decorators from wrapper functions to the bare underlying functions for all 11 affected tools
4. **Dead Entries**: Either implement `github_delete_repo`, `obscura_file_upload` tools or remove dead entries from AUTH_MATRIX; add `docker_rm_all` to AUTH_MATRIX

---

## 9. Evidence Path

- **This report**: `audit-reports/P6/P6-FINAL-AUDIT/D04-auth-matrix.md`
- **Source files**: All 19 files listed in §7
- **Test file**: `tests/mcp/test_auth_matrix.py`

## 10. Boundary Compliance

- ✅ No secrets exposed in audit
- ✅ No destructive operations performed
- ✅ Read-only analysis
- ✅ No files modified
- ⚠️ Findings in persona/safety boundary domain — auth matrix is core security boundary; failures directly affect safety posture

## 11. Design Decisions / Caveats

1. **Faiz mandate interpretation**: "redis(DEL/FLUSHDB)" listed under Destructive-Approval in the audit task spec could mean Faiz intended FLUSHDB to be DESTRUCTIVE_APPROVAL, or it could be a typo. Clarification needed.
2. **postgres "write operations"**: The `classify_sql()` defense-in-depth is actually good security — blocking writes at the SQL parsing layer. But it contradicts the AUTH_MATRIX declaration. If Faiz wants INSERT/UPDATE/DELETE through the MCP tool, a separate authenticated tool is needed.
3. **"shell(rm -rf /)"**: Listed as Forbidden in Faiz mandate. AUTH_MATRIX has `"rm_rf_root"` and `"sudo_rm_rf"` as FORBIDDEN. These are enforced via BLOCKED_PATTERNS in `shell_tool.py` rather than separate MCP tools. Functionally equivalent but architecturally inconsistent with the 1:1 tool-operation model.
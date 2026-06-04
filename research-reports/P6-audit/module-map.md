# P6 Phase — MCP Tools Module Inventory

> **Audit Type**: FULL — Complete source inventory
> **Date**: 2026-06-03
> **Scope**: `src/mcp/` and `src/mcp/tools/`
> **Total Source Files**: 24 Python files (excluding `__pycache__`)
> **Total Lines**: 6,598

---

## 1. File Summary

| # | File | Lines |
|---|------|-------|
| 1 | `src/mcp/__init__.py` | 23 |
| 2 | `src/mcp/auth.py` | 216 |
| 3 | `src/mcp/auth_matrix.py` | 277 |
| 4 | `src/mcp/budget.py` | 364 |
| 5 | `src/mcp/cost.py` | 241 |
| 6 | `src/mcp/manager.py` | 89 |
| 7 | `src/mcp/tool_selector.py` | 332 |
| 8 | `src/mcp/tools/__init__.py` | 94 |
| 9 | `src/mcp/tools/brave_search.py` | 177 |
| 10 | `src/mcp/tools/context7.py` | 407 |
| 11 | `src/mcp/tools/docker_tool.py` | 614 |
| 12 | `src/mcp/tools/exa_search.py` | 212 |
| 13 | `src/mcp/tools/fetch.py` | 213 |
| 14 | `src/mcp/tools/filesystem.py` | 210 |
| 15 | `src/mcp/tools/git_tool.py` | 362 |
| 16 | `src/mcp/tools/github.py` | 254 |
| 17 | `src/mcp/tools/grep_app.py` | 224 |
| 18 | `src/mcp/tools/obscura_cdp.py` | 247 |
| 19 | `src/mcp/tools/postgres_tool.py` | 333 |
| 20 | `src/mcp/tools/redis_tool.py` | 444 |
| 21 | `src/mcp/tools/sequential_thinking.py` | 420 |
| 22 | `src/mcp/tools/shell_tool.py` | 364 |
| 23 | `src/mcp/tools/time_tools.py` | 297 |
| 24 | `src/mcp/tools/websearch.py` | 164 |
---

## 2. Per-File Inventory

### 2.1 `src/mcp/__init__.py` (23 lines)
**Purpose**: Top-level API re-exports.

**Internal Imports**: `src.mcp.auth` (AuthLevel, ForbiddenOperationError, require_approval), `src.mcp.manager` (create_server)
**Classes**: None
**Functions**: None
**`__all__`**: AuthLevel, create_server, ForbiddenOperationError, require_approval

---

### 2.2 `src/mcp/auth.py` (216 lines)
**Purpose**: Authorization decorator with 4-tier approval levels + Discord webhook integration.

**External Imports**: `asyncio`, `enum`, `os`, `functools.wraps`, `typing.{Any, Callable}`, `httpx`, `structlog`
**Internal Imports**: None (leaf module)

**Classes**:
| Class | Type |
|-------|------|
| `AuthLevel` | `enum.Enum` — READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN |
| `ForbiddenOperationError` | `Exception` |

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_get_webhook_url()` | No | Returns DISCORD_WEBHOOK_URL from env |
| `_send_discord_notification(tool_name, level, details)` | Yes | Posts non-blocking Discord notification |
| `_wait_for_approval(tool_name, timeout)` | Yes | Blocks until approval resolved |
| `approve(tool_name)` | No | Signal approval externally |
| `deny(tool_name)` | No | Signal denial externally |
| `require_approval(level, tool_name)` | No | **Decorator** — gates tool functions through auth workflow |

**Module-Level State**: `_pending_approvals` (dict), `_approval_results` (dict), `_APPROVAL_TIMEOUT_SECONDS` (300.0)

---

### 2.3 `src/mcp/auth_matrix.py` (277 lines)
**Purpose**: Central registry mapping all 16 tools + operations to AuthLevel. Single source of truth.

**External Imports**: `dataclasses.dataclass`, `typing.Final`, `structlog`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`

**Classes**: `ToolAuthEntry` (`@dataclass(frozen=True)`)
**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `get_auth_level(tool_name, operation)` | No | Lookup with KeyError on miss; supports `*` wildcard |
| `verify_matrix_completeness()` | No | Verification gate — all 16 tools registered? |

**Module-Level Data**: `AUTH_MATRIX` (16-tool dict), `ALL_TOOL_NAMES` (tuple of 16 names)

**AUTH_MATRIX Coverage** (16/16):
- Wildcard (`*`) READ_AUTO: brave_search, exa, fetch, grep_app, sequential_thinking, time, websearch
- Multi-level: context7, docker, filesystem, git, github, obscura_cdp, postgres, redis, shell

---

### 2.4 `src/mcp/budget.py` (364 lines)
**Purpose**: Budget enforcer — daily caps per tool, global daily cap, monthly alerts, fallback routing (Exa→Brave).

**External Imports**: `os`, `dataclasses.dataclass`, `datetime.date`, `redis`, `redis.exceptions.RedisError`, `structlog`
**Internal Imports**: `src.mcp.tools.exa_search` → `BudgetExceeded`

**Classes**:
| Class | Type |
|-------|------|
| `BudgetConfig` | `@dataclass(frozen=True)` — exa_daily_cap, brave_daily_cap, global_daily_cap, monthly_warning, monthly_critical, monthly_hard_stop, monthly_absolute_cap |
| `BudgetStatus` | `@dataclass(frozen=True)` — tool, daily_spent, daily_cap, monthly_spent, alert_level, fallback_active |
| `BudgetEnforcer` | Class — core budget engine |

**BudgetEnforcer Methods**:
| Method | Async | Description |
|--------|-------|-------------|
| `__init__(config)` | No | Redis DB5 connection |
| `check_budget(tool_name)` | Yes | Check budget; raises BudgetExceeded |
| `get_fallback_tool(tool_name)` | Yes | Returns fallback or None |
| `get_monthly_status()` | Yes | All tools'' budget status |
| `record_and_check(tool_name, cost)` | Yes | Record + check |
| `_daily_cap_for(tool_name)` | No | Daily cap for tool |
| `_compute_alert_level(monthly, daily, cap)` | No | NORMAL/WARNING/CRITICAL/HARD_STOP |
| `_get_daily_spend(tool_name)` | No | Redis daily read |
| `_get_global_daily_spend()` | No | Redis total read |
| `_get_monthly_spend()` | No | Redis monthly read |
| `_get_all_daily_spends()` | No | SCAN all daily keys |

**Module-Level**: `_FALLBACK_MAP = {"exa": "brave_search", "brave_search": None}`

---

### 2.5 `src/mcp/cost.py` (241 lines)
**Purpose**: Per-tool cost tracking in Redis DB5 with daily key rotation.

**External Imports**: `os`, `datetime.{date, datetime, timedelta}`, `redis`, `redis.exceptions.RedisError`, `structlog`
**Internal Imports**: None (standalone)

**Classes**: `ToolCostTracker` — per-tool cost tracking engine
**Methods**:
| Method | Async | Description |
|--------|-------|-------------|
| `get_tool_cost(tool_name)` (static) | No | Returns known per-call cost; -1.0 = variable |
| `is_variable_cost(tool_name)` (static) | No | Checks variable cost flag |
| `record_tool_cost(tool_name, cost_usd=None)` | No | Records cost, EXPIREAT, returns daily total |
| `get_tool_daily_cost(tool_name)` | No | Today''s daily cost |
| `get_all_daily_costs()` | No | SCAN all today''s costs |
| `get_tool_monthly_cost(tool_name)` | No | Sum last 30 days |

**Module-Level**: `_TOOL_COSTS` (fixed per-call costs for 16 tools), `_KEY_PREFIX = "tool:cost"`

---

### 2.6 `src/mcp/manager.py` (89 lines)
**Purpose**: FastMCP server factory + entry-point.

**External Imports**: `sys`, `collections.abc.Callable`, `contextlib.asynccontextmanager`, `pathlib.Path`, `typing.{Any, AsyncIterator}`, `structlog`, `mcp.server.fastmcp.FastMCP`
**Internal Imports**: `src.mcp.tools` → `register_all_tools`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_build_lifespan()` | No | Builds async context manager |
| `create_server(name="guinevere-mcp")` | No | Creates FastMCP instance |

**Decorators**: `@asynccontextmanager`
**Entry-Point**: `if __name__ == "__main__": server.run()`
**Notable**: Lines 24-33 temporarily prune `src/` from `sys.path` to avoid shadowing pip-installed `mcp`.

---

### 2.7 `src/mcp/tool_selector.py` (332 lines)
**Purpose**: Decision matrix for optimal tool routing (8 overlap scenarios, 4 weighted dimensions).

**External Imports**: `dataclasses.dataclass`, `structlog`
**Internal Imports**: None (standalone)

**Classes**:
| Class | Type |
|-------|------|
| `NoToolAvailableError` | `Exception` — task_type, suggestions |
| `AllToolsUnavailableError` | `Exception` — task_type, candidates |
| `ToolOption` | `@dataclass(frozen=True)` — name, relevance, cost_efficiency, auth_ease, available |
| `ToolRecommendation` | `@dataclass(frozen=True)` — tool_name, score, alternatives, reason |

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_score_option(option)` | No | Weighted formula (0.4+0.3+0.2+0.1) |
| `_apply_constraints(candidates, constraints)` | No | Runtime overrides |
| `select_tool(task_type, query, constraints)` | Yes | Public API |
| `get_tool_matrix()` | No | Returns full matrix |

**8 Scenarios**: web_search_general, web_search_semantic, code_search, library_docs, page_content, file_read, db_query, git_operations

---

### 2.8 `src/mcp/tools/__init__.py` (94 lines)
**Purpose**: Dynamic registry — imports all 16 tool modules and calls `register_tools(server)`.

**Internal Imports**: All 16 tool modules (brave_search, context7, docker_tool, exa_search, fetch, filesystem, git_tool, github, grep_app, obscura_cdp, postgres_tool, redis_tool, sequential_thinking, shell_tool, time_tools, websearch)

**Functions**: `register_all_tools(server: FastMCP) -> int` — iterates _TOOL_MODULES

---
### 2.9 `src/mcp/tools/brave_search.py` (177 lines)
**Purpose**: Web search via Brave Search API, cost tracked in Redis DB5.

**External Imports**: `os`, `datetime.date`, `httpx`, `redis`, `structlog`, `tenacity.{retry, retry_if_exception_type, stop_after_attempt, wait_exponential}`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Classes**: `BraveSearchConfigError(Exception)`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_get_api_key()` | No | BRAVE_API_KEY from env |
| `_get_redis_client()` | No | Redis DB5 client |
| `_record_cost(client)` | No | Increment daily cost |
| `_fetch_search(query, count, api_key)` | Yes | Brave API with tenacity retry |
| `brave_search(query, count=5)` | Yes | Public tool — @require_approval(READ_AUTO) |
| `register_tools(mcp)` | No | Registers brave_search |

**Decorators**: `@retry(stop=3, wait=exponential)`, `@require_approval(READ_AUTO)`

---

### 2.10 `src/mcp/tools/context7.py` (407 lines)
**Purpose**: Library documentation lookup via Context7 REST API with in-memory LRU cache (max 256).

**External Imports**: `asyncio`, `os`, `datetime.date`, `typing.{Any}`, `httpx`, `structlog`, `tenacity`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Classes**: `Context7Error(Exception)`, `LibraryNotFoundError(Context7Error)`, `RateLimitExceededError(Context7Error)`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_api_get(client, path, params)` | Yes | GET with transport error retry |
| `_cache_key(library_name, query)` | No | Normalized cache key |
| `_cache_get(library_name, query)` | No | LRU cache lookup |
| `_cache_set(library_name, query, result)` | No | Store with LRU eviction |
| `cache_clear()` | No | Clear cache |
| `cache_size()` | No | Cache entry count |
| `_track_cost_sync()` | No | Sync Redis cost tracking |
| `_track_cost()` | Yes | Fire-and-forget via asyncio.to_thread |
| `context7_resolve(library_name, query="")` | Yes | Resolve library name → Context7 ID |
| `context7_query(library_id, query)` | Yes | Query documentation |
| `register_tools(mcp)` | No | Registers context7_resolve + context7_query |

---

### 2.11 `src/mcp/tools/docker_tool.py` (614 lines)
**Purpose**: Container lifecycle management via docker CLI. Network isolation enforced (guinevere-net only).

**External Imports**: `asyncio`, `json`, `re`, `time`, `typing.{Any}`, `structlog`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `ForbiddenOperationError`, `require_approval`

**Classes**:
| Class | Parent |
|-------|--------|
| `DockerError` | Exception |
| `DockerNotFoundError` | DockerError |
| `DockerContainerError` | DockerError |
| `DockerNetworkError` | DockerError |
| `DockerForbiddenError` | ForbiddenOperationError |

**Functions** (11 tools registered):
- READ_AUTO: `docker_ps(all=False)`, `docker_logs(container, tail=100)`, `docker_inspect(container)`, `docker_images(all=False)`
- WRITE_NOTIFY: `docker_start(container)`, `docker_stop(container)`, `docker_restart(container)`
- DESTRUCTIVE_APPROVAL: `docker_rm(container, force=False)`, `docker_rmi(image, force=False)`
- FORBIDDEN: `docker_system_prune()`, `docker_rm_all()`

**Key Validation**: Container name regex `^[a-zA-Z0-9][a-zA-Z0-9_.\-]*$`, image name shell-metachar check, FORBIDDEN_PATTERNS frozenset.

---

### 2.12 `src/mcp/tools/exa_search.py` (212 lines)
**Purpose**: AI-powered semantic search via Exa API with $5/day budget cap in Redis DB5.

**External Imports**: `os`, `datetime.date`, `httpx`, `redis.asyncio`, `structlog`, `tenacity`, `mcp.server.fastmcp.FastMCP`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Classes**: `BudgetExceeded(Exception)` — **imported by budget.py**, `ConfigurationError(Exception)`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_get_api_key()` | No | EXA_API_KEY from env |
| `_get_redis()` | No | Async Redis DB5 client |
| `_daily_cost_key()` | No | Today''s cost key |
| `_check_budget(redis_client)` | Yes | Checks daily cap BEFORE API call |
| `_record_cost(redis_client, cost)` | Yes | Redis pipeline INCRBYFLOAT |
| `_call_exa_api(client, query, num_results, api_key)` | Yes | Exa API with tenacity retry |
| `exa_search(query, num_results=10)` | Yes | Public tool — @require_approval(READ_AUTO) |
| `register_tools(mcp)` | No | Registers exa_search |

**Cost Model**: Per-request ~$0.007, Daily cap $5.00, Redis TTL 172800s

---

### 2.13 `src/mcp/tools/fetch.py` (213 lines)
**Purpose**: Web content retrieval with HTML→Markdown conversion via `markdownify`. 1MB size limit enforced.

**External Imports**: `re`, `urllib.parse.urlparse`, `httpx`, `structlog`, `markdownify`, `tenacity`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_validate_url(url)` | No | Rejects non-HTTP(S) schemes |
| `_is_transient(exc)` | No | Returns True for retryable errors |
| `_fetch_with_retry(url)` | Yes | HTTP GET + redirect + retry |
| `_extract_title(html)` | No | Extracts `<title>` from HTML |
| `fetch_url(url, format="markdown")` | Yes | Public API |
| `register_tools(mcp)` | No | Registers fetch_url |

---

### 2.14 `src/mcp/tools/filesystem.py` (210 lines)
**Purpose**: Secure file I/O with path whitelist enforcement. 4 operations with appropriate AuthLevel.

**External Imports**: `os`, `dataclasses.dataclass`, `pathlib.Path`, `structlog`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Classes**: `FilesystemConfig` (`@dataclass(frozen=True)`), `PathForbiddenError(Exception)`

**Functions**:
| Function | Async | Auth |
|----------|-------|------|
| `_reject_null_bytes(path)` | No | — |
| `validate_path(path, allowed_paths)` | No | — |
| `fs_read(path, _config)` | Yes | READ_AUTO |
| `fs_write(path, content, _config)` | Yes | WRITE_NOTIFY |
| `fs_delete(path, _config)` | Yes | DESTRUCTIVE_APPROVAL |
| `fs_list(path, _config)` | Yes | READ_AUTO |
| `register_tools(mcp)` | No | — |

---

### 2.15 `src/mcp/tools/git_tool.py` (362 lines)
**Purpose**: Local git operations via `asyncio.create_subprocess_exec`. 6 tools registered.

**External Imports**: `asyncio`, `os`, `structlog`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `ForbiddenOperationError`, `require_approval`

**Classes**: `GitToolError(Exception)`, `ConfigurationError(GitToolError)`, `GitCommandError(GitToolError)`

**Functions**:
| Function | Async | Auth |
|----------|-------|------|
| `_find_git()` | No | — |
| `_is_forbidden(args, branch)` | No | Force-push to main/master detection |
| `_run_git(*args, cwd, env)` | Yes | Subprocess exec |
| `_assert_zero(code, stderr, operation)` | No | Error assertion |
| `_build_env()` | No | GITHUB_PAT env |
| `_git_status(repo_path)` | Yes | READ_AUTO |
| `_git_log(repo_path, count)` | Yes | READ_AUTO |
| `_git_diff(repo_path, staged)` | Yes | READ_AUTO |
| `_git_commit(repo_path, message, files)` | Yes | WRITE_NOTIFY |
| `_git_push(repo_path, force, branch)` | Yes | WRITE_NOTIFY / DESTRUCTIVE_APPROVAL / FORBIDDEN |
| `register_tools(mcp)` | No | Registers 6 tools |

---
### 2.16 `src/mcp/tools/github.py` (254 lines)
**Purpose**: GitHub REST API operations via httpx with rate-limit awareness and retry logic.

**External Imports**: `base64`, `os`, `typing.{Any}`, `httpx`, `structlog`, `tenacity`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Classes**: `GitHubToolError(Exception)`, `ConfigurationError(GitHubToolError)`

**Functions**:
| Function | Async | Auth |
|----------|-------|------|
| `_build_client()` | No | — |
| `_ensure_pat()` | No | GITHUB_PAT check |
| `_parse_rate_limit_headers(response)` | No | Rate limit logging |
| `_handle_response_error(response, operation)` | No | 401/403/404 handling |
| `_is_retryable_error(exc)` | No | 5xx/TransportError check |
| `github_list_repos(owner)` | Yes | READ_AUTO |
| `github_get_file(owner, repo, path)` | Yes | READ_AUTO |
| `github_create_issue(owner, repo, title, body)` | Yes | WRITE_NOTIFY |
| `github_create_pr(owner, repo, title, head, base)` | Yes | WRITE_NOTIFY |
| `github_search_code(query)` | Yes | READ_AUTO |
| `register_tools(mcp)` | No | Registers 5 tools |

---

### 2.17 `src/mcp/tools/grep_app.py` (224 lines)
**Purpose**: Code search across GitHub via grep.app public API. No authentication, $0 cost.

**External Imports**: `typing.{Any}`, `httpx`, `structlog`, `tenacity`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_parse_hits(data)` | No | Parses grep.app JSON |
| `_extract_raw(container, key)` | No | Nested dict extraction |
| `_fetch_search(query, language, repo, use_regexp, match_case)` | Yes | API call with retry |
| `grep_app_search(query, language, repo, use_regexp, match_case)` | Yes | Public tool — READ_AUTO |
| `register_tools(mcp)` | No | Registers grep_app_search |

---

### 2.18 `src/mcp/tools/obscura_cdp.py` (247 lines)
**Purpose**: Browser automation via Obscura CDP + Playwright. 4 tools.

**External Imports**: `dataclasses.{dataclass, field}`, `typing.{Any}`, `structlog`, `markdownify`, `playwright.async_api.{Browser, Page, async_playwright}`, `tenacity`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Classes**: `ObscuraNotRunning(Exception)`, `ElementNotFoundError(Exception)`, `_BrowserState` (`@dataclass`)

**Functions**:
| Function | Async | Auth |
|----------|-------|------|
| `_BrowserState.ensure_connected()` | Yes | — (with tenacity retry) |
| `obscura_navigate(url)` | Yes | READ_AUTO |
| `obscura_get_markdown(url)` | Yes | READ_AUTO |
| `obscura_fill_form(url, selectors)` | Yes | WRITE_NOTIFY |
| `obscura_click(selector)` | Yes | WRITE_NOTIFY |
| `register_tools(mcp)` | No | Registers 4 tools |

**Module-Level State**: `_state` — global `_BrowserState` instance, kept alive for server lifetime

---

### 2.19 `src/mcp/tools/postgres_tool.py` (333 lines)
**Purpose**: PostgreSQL queries with 3-layer read-only enforcement.

**External Imports**: `os`, `re`, `collections.abc.Sequence`, `typing.{Any, Final}`, `asyncpg`, `structlog`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `ForbiddenOperationError`, `require_approval`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `classify_sql(sql)` | No | Classifies as "read"/"write"/"forbidden" |
| `_get_pool()` | Yes | Lazy asyncpg connection pool |
| `_validate_params(sql, params)` | No | Parameter count validation |
| `postgres_query(sql, params=None)` | Yes | Read-only parameterized query |
| `postgres_tables(schema="public")` | Yes | Lists user tables |
| `postgres_describe(table, schema="public")` | Yes | Describes table columns |
| `register_tools(mcp)` | No | Registers 3 tools |

**Module-Level Data**: `ALLOWED_READ` (SELECT/SHOW/EXPLAIN/WITH), `REQUIRES_APPROVAL` (INSERT/UPDATE/DELETE), `FORBIDDEN` (DROP/TRUNCATE/ALTER/CREATE/GRANT/REVOKE), `_pool`

**3-Layer Read-Only Enforcement**:
1. `BEGIN READ ONLY` transaction wrapper
2. SQL keyword classification before execution
3. Dedicated `guinevere_readonly` database role

---

### 2.20 `src/mcp/tools/redis_tool.py` (444 lines)
**Purpose**: Async Redis operations with command-level auth classification. 9 tools across all 4 auth levels.

**External Imports**: `os`, `typing.{Any}`, `redis.asyncio`, `structlog`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `ForbiddenOperationError`, `require_approval`

**Functions** (9 tools registered):
- READ_AUTO: `redis_get`, `redis_keys`, `redis_hgetall`, `redis_lrange`
- WRITE_NOTIFY: `redis_set`, `redis_hset`
- DESTRUCTIVE_APPROVAL: `redis_del`
- FORBIDDEN: `redis_flushdb`, `redis_flushall`

**Module-Level Data**: `DB_ALLOCATION` (DB0-5), `READ_COMMANDS` (9), `WRITE_COMMANDS` (9), `DESTRUCTIVE_COMMANDS` (4), `FORBIDDEN_COMMANDS` (6), `COMMAND_CLASSIFICATION` (merged map)

---

### 2.21 `src/mcp/tools/sequential_thinking.py` (420 lines)
**Purpose**: Structured chain-of-thought reasoning with session management.

**External Imports**: `uuid`, `dataclasses.{dataclass, replace}`, `structlog`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Classes**: `Thought` (`@dataclass(frozen=True)`), `ThinkingSession` (`@dataclass(frozen=True)`), `SessionNotFoundError(Exception)`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_get_session_or_raise(session_id)` | No | Gets session or raises |
| `create_session(topic, initial_estimate=5)` | No | Creates session, returns UUID |
| `add_thought(session_id, content, next_needed, thought_number)` | No | Appends thought |
| `branch_thought(session_id, from_thought, content)` | No | Creates branch thought |
| `revise_thought(session_id, thought_number, new_content)` | No | Revises existing thought |
| `get_session(session_id)` | No | Retrieves session |
| `finalize_session(session_id, conclusion)` | No | Finalizes and removes session |
| `sequential_think(thought, thought_number, total_thoughts, ...)` | Yes | MCP tool — auto-creates default session |
| `register_tools(mcp)` | No | Registers sequential_thinking |

---

### 2.22 `src/mcp/tools/shell_tool.py` (364 lines)
**Purpose**: Whitelisted shell command execution with injection detection.

**External Imports**: `asyncio`, `shlex`, `time`, `structlog`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `ForbiddenOperationError`, `require_approval`

**Classes**: `CommandForbiddenError(ForbiddenOperationError)`, `ShellTimeoutError(Exception)`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `_check_injection(command)` | No | Scans for injection chars (;, |, &&, ||, `, $(, >, <) |
| `_check_blocked_patterns(command)` | No | Scans for destructive patterns |
| `validate_command(cmd)` | No | Full validation pipeline |
| `_execute(args, workdir, timeout)` | Yes | Subprocess with deadline |
| `shell_exec(command, workdir=None, timeout=30)` | Yes | Public tool — DESTRUCTIVE_APPROVAL |
| `register_tools(mcp)` | No | Registers shell_exec |

**Module-Level Data**:
- `ALLOWED_COMMANDS` (frozenset): 20 whitelisted commands (ls, cat, grep, find, wc, head, tail, python, pip, git, systemctl status, df, free, uptime, hostname, whoami, pwd, echo, date, which, file, stat)
- `BLOCKED_PATTERNS` (frozenset): 14 destructive patterns
- `_INJECTION_CHARS` (frozenset): 9 injection characters

---

### 2.23 `src/mcp/tools/time_tools.py` (297 lines)
**Purpose**: Timezone conversions and scheduling utilities. Default: Asia/Jakarta (WIB, UTC+7).

**External Imports**: `calendar`, `datetime.{datetime, timezone}`, `zoneinfo.{ZoneInfo, available_timezones}`, `structlog`
**Internal Imports**: `src.mcp.auth` → `AuthLevel`, `require_approval`

**Functions** (6 tools registered):
| Function | Async | Description |
|----------|-------|-------------|
| `_resolve_tz(tz_name)` | No | IANA timezone resolution |
| `_parse_datetime(time_str)` | No | Parses YYYY-MM-DD HH:MM:SS |
| `_parse_date(date_str)` | No | Parses YYYY-MM-DD |
| `_humanise_delta(total_seconds)` | No | Converts to "X hours ago" |
| `current_time(tz_name, fmt)` | Yes | Current time |
| `convert_time(source_tz, target_tz, time_str)` | Yes | Timezone conversion |
| `days_in_month(date_str=None)` | Yes | Days in month |
| `relative_time(time_str)` | Yes | Relative time string |
| `get_timestamp(time_str)` | Yes | Unix timestamp |
| `get_week_year(date_str=None)` | Yes | Week number + ISO week |
| `register_tools(mcp)` | No | Registers 6 tools |

---

### 2.24 `src/mcp/tools/websearch.py` (164 lines)
**Purpose**: Hybrid web search with Brave primary + Exa fallback.

**External Imports**: `typing.{Any}`, `httpx`, `redis`, `structlog`
**Internal Imports**:
- `src.mcp.auth` → `AuthLevel`, `require_approval`
- `src.mcp.tools.brave_search` → `brave_search`
- `src.mcp.tools.exa_search` → `BudgetExceeded`, `exa_search`

**Functions**:
| Function | Async | Description |
|----------|-------|-------------|
| `websearch(query, count=5, prefer="brave")` | Yes | Hybrid search with fallback |
| `register_tools(mcp)` | No | Registers websearch |

**Fallback Flow**: Brave primary → empty/error → Exa fallback → empty/error → `{"results": [], "source": "none"}`
---

## 3. Internal Import Dependency Map

```
src/mcp/__init__.py
  ├── src/mcp/auth.py          (AuthLevel, ForbiddenOperationError, require_approval)
  └── src/mcp/manager.py       (create_server)

src/mcp/manager.py
  └── src/mcp/tools/__init__.py  (register_all_tools)
        ├── brave_search
        ├── context7
        ├── docker_tool
        ├── exa_search
        ├── fetch
        ├── filesystem
        ├── git_tool
        ├── github
        ├── grep_app
        ├── obscura_cdp
        ├── postgres_tool
        ├── redis_tool
        ├── sequential_thinking
        ├── shell_tool
        ├── time_tools
        └── websearch

src/mcp/auth_matrix.py
  └── src/mcp/auth.py          (AuthLevel)

src/mcp/budget.py
  └── src/mcp/tools/exa_search.py  (BudgetExceeded)

src/mcp/cost.py
  └── (none — standalone)

src/mcp/tool_selector.py
  └── (none — standalone)

src/mcp/tools/websearch.py
  ├── src/mcp/auth.py
  ├── src/mcp/tools/brave_search.py  (brave_search)
  └── src/mcp/tools/exa_search.py     (BudgetExceeded, exa_search)

ALL TOOL MODULES (*.py in tools/)
  └── src/mcp/auth.py          (AuthLevel, require_approval, ForbiddenOperationError)
```

### Key Dependency Relationships

| Consumer | Depends On | Reason |
|----------|------------|--------|
| `tools/__init__.py` | All 16 tool modules | Dynamic registry imports |
| `manager.py` | `tools/__init__.py` | `register_all_tools()` |
| `__init__.py` | `auth.py`, `manager.py` | Public API re-exports |
| `websearch.py` | `brave_search.py`, `exa_search.py` | Fallback orchestration |
| `budget.py` | `exa_search.py` | BudgetExceeded exception |
| `auth_matrix.py` | `auth.py` | AuthLevel enum |
| ALL tool modules | `auth.py` | Auth decorator + exception |

**External Python Dependencies** (from all files):

| Package | Type | Used By |
|---------|------|---------|
| `httpx` | 3rd party | auth, brave_search, context7, exa_search, fetch, github, grep_app, websearch |
| `structlog` | 3rd party | ALL 24 files |
| `redis` / `redis.asyncio` | 3rd party | budget, cost, brave_search, context7, exa_search, redis_tool |
| `tenacity` | 3rd party | brave_search, context7, exa_search, fetch, github, grep_app, obscura_cdp |
| `markdownify` | 3rd party | fetch, obscura_cdp |
| `playwright` | 3rd party | obscura_cdp |
| `asyncpg` | 3rd party | postgres_tool |
| `mcp.server.fastmcp` | 3rd party | manager, exa_search |

---

## 4. Circular Import Analysis

**VERDICT: NO CIRCULAR IMPORTS DETECTED**

| Check | Result |
|-------|--------|
| `auth.py` → any module that imports `auth.py` | No — auth.py is a leaf module, imports nothing from src/mcp |
| `__init__.py` → `manager.py` → `tools/__init__.py` → `{tools}` → back to `__init__.py` | No — `__init__.py` is only consumed externally, not by tools |
| `budget.py` → `tools/exa_search.py` → back to `budget.py` | No — exa_search.py does not import budget.py |
| `websearch.py` → `brave_search.py`, `exa_search.py` → back to `websearch.py` | No — neither brave_search nor exa_search import websearch.py |

**Dependency Tree Depth**: Maximum 3 levels

| Level | Modules |
|-------|---------|
| 0 | `__init__.py` |
| 1 | `manager.py`, `auth.py`, `budget.py`, `cost.py`, `auth_matrix.py`, `tool_selector.py` |
| 2 | `tools/__init__.py` |
| 3 | All 16 tool modules |

---

## 5. Forbidden Pattern Scan

### 5.1 Summary

| Pattern | Count | Severity |
|---------|-------|----------|
| `# type: ignore` | 1 | LOW |
| `as any` | 0 | N/A (TypeScript only) |
| `@ts-ignore` | 0 | N/A |
| `cast()` | 0 | N/A |
| bare `except:` | 0 | PASS |
| `except Exception` (broad) | 7 | MEDIUM |
| `pass` after except | 2 | LOW |

### 5.2 `# type: ignore` — 1 occurrence

| File | Line | Code | Verdict |
|------|------|------|---------|
| `src/mcp/tools/postgres_tool.py` | 20 | `import asyncpg  # type: ignore[import-untyped]` | PASS — asyncpg has no stubs; `[import-untyped]` qualifier is best-practice |

### 5.3 `except Exception` (broad catch) — 7 occurrences

| # | File | Line | Risk |
|---|------|------|------|
| 1 | `src/mcp/tools/obscura_cdp.py` | 99 | Connection failure caught and re-raised as typed `ObscuraNotRunning` — ACCEPTABLE |
| 2 | `src/mcp/tools/obscura_cdp.py` | 128 | Navigation timeout silently caught — returns dict with warning. **MEDIUM**: losing original traceback |
| 3 | `src/mcp/tools/obscura_cdp.py` | 151 | Markdown timeout silently caught — same pattern as above. **MEDIUM**: consider logging traceback |
| 4 | `src/mcp/tools/obscura_cdp.py` | 178 | Fill-form selector failure re-raised as `ElementNotFoundError` — ACCEPTABLE |
| 5 | `src/mcp/tools/obscura_cdp.py` | 201 | Click selector failure re-raised as `ElementNotFoundError` — ACCEPTABLE |
| 6 | `src/mcp/tools/websearch.py` | 95 | Primary search unexpected error logged then fallback triggered — ACCEPTABLE |
| 7 | `src/mcp/tools/websearch.py` | 141 | Fallback unexpected error logged — ACCEPTABLE |

### 5.4 `pass` after except — 2 occurrences

| # | File | Line | Context | Verdict |
|---|------|------|---------|---------|
| 1 | `src/mcp/budget.py` | 261 | `except RedisError: ... pass` — defensive: if recording fails, still checks budget | ACCEPTABLE (documented intent) |
| 2 | `src/mcp/tools/fetch.py` | 175 | Empty `pass` in if/else block — decorative, no function | REMOVABLE (harmless dead code) |

---

## 6. Cross-Cutting Concerns

### 6.1 Auth Integration Pattern
All 16 tool modules depend on `src/mcp/auth.py` for:
- `require_approval` decorator (applied to all public tool functions)
- `AuthLevel` enum (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN)
- `ForbiddenOperationError` exception

The `auth_matrix.py` module provides canonical mapping. Every tool''s `@require_approval` arguments **must** match the matrix. No runtime verification of this alignment exists.

### 6.2 Cost Tracking — Two Systems Coexist
1. **`cost.py` → `ToolCostTracker`**: Per-tool per-call cost recording with daily/monthly queries
2. **`budget.py` → `BudgetEnforcer`**: Budget enforcement with caps, fallback routing, alerts

Both target Redis DB5. `budget.py` imports `BudgetExceeded` from `exa_search.py`.

### 6.3 Redis Connection Patterns
| Pattern | Files |
|---------|-------|
| Sync `redis.Redis` | budget.py, cost.py, brave_search.py, context7.py |
| Async `redis.asyncio.Redis` | exa_search.py, redis_tool.py |
| Hardcoded `localhost:6380` | All Redis-using files |
| Hardcoded username `guinevere_core` | All Redis-using files |

### 6.4 Exception Hierarchy
```
Exception
├── ForbiddenOperationError (auth.py)
│   ├── DockerForbiddenError (docker_tool.py)
│   ├── CommandForbiddenError (shell_tool.py)
│   └── (raised by auth decorator)
├── BudgetExceeded (exa_search.py) — used by budget.py, websearch.py
├── 28 additional tool-specific exception classes
```

### 6.5 Database/Subprocess Connections
| Connection | File | Port | Type |
|------------|------|------|------|
| PostgreSQL | postgres_tool.py | 5433 | asyncpg pool (lazy) |
| Docker CLI | docker_tool.py | — | asyncio.create_subprocess_exec |
| Git CLI | git_tool.py | — | asyncio.create_subprocess_exec |
| Shell | shell_tool.py | — | asyncio.create_subprocess_exec |
| Obscura CDP | obscura_cdp.py | 9222 | playwright.connect_over_cdp |

### 6.6 Registration Pattern Consistency
All 16 tool modules expose `register_tools(mcp: FastMCP) -> None`. Two variations exist:

**Pattern A** (most tools): Wrapped with `@mcp.tool()` + `@require_approval` inside `register_tools`
- Used by: context7, docker_tool, fetch, filesystem, git_tool, obscura_cdp, postgres_tool, redis_tool, sequential_thinking, shell_tool, time_tools

**Pattern B** (decorator on public function): `@require_approval` on the public function, `@mcp.tool()` in register_tools
- Used by: brave_search, exa_search, github, grep_app, websearch

---

## 7. Tool Registration Summary by Auth Level

| Auth Level | Count | Tools |
|------------|-------|-------|
| READ_AUTO | ~38 | brave_search, context7_resolve, context7_query, docker_ps, docker_logs, docker_inspect, docker_images, exa_search, fetch_url, fs_read, fs_list, git_status, git_log, git_diff, github_list_repos, github_get_file, github_search_code, grep_app_search, obscura_navigate, obscura_get_markdown, postgres_query, postgres_tables, postgres_describe, redis_get, redis_keys, redis_hgetall, redis_lrange, sequential_thinking, time_current_time, time_convert_time, time_days_in_month, time_relative_time, time_get_timestamp, time_get_week_year, websearch |
| WRITE_NOTIFY | ~18 | docker_start, docker_stop, docker_restart, fs_write, git_commit, git_push, github_create_issue, github_create_pr, obscura_fill_form, obscura_click, redis_set, redis_hset, and others |
| DESTRUCTIVE_APPROVAL | ~9 | docker_rm, docker_rmi, fs_delete, git_push_force, redis_del, shell_exec, and others |
| FORBIDDEN | ~8 | docker_system_prune, docker_rm_all, redis_flushdb, redis_flushall, git force-push to main, and others |

---

## 8. Final Audit Summary

| Metric | Value |
|--------|-------|
| Total source files | 24 |
| Total lines of code | 6,598 |
| Classes defined | 35 (12 exception, 8 dataclass, 1 enum, 14 others) |
| Functions defined | ~130 |
| Decorator applications | ~95 (@require_approval) + ~12 (@retry) + ~10 (@mcp.tool) |
| Internal imports | 38 |
| External package imports | 10 (httpx, structlog, redis, tenacity, markdownify, playwright, asyncpg, mcp, zoneinfo, markdownify) |
| Circular imports | 0 |
| `# type: ignore` | 1 (acceptable — asyncpg stubs) |
| Broad `except Exception` | 7 (5 obscura_cdp, 2 websearch — logged/re-raised) |
| `pass` after except | 2 (budget: defensive, fetch: dead code) |
| Auth levels | 4-tier system consistently applied |
| Registration pattern | 100% coverage — all 16 tools registerable |

### Compliance Verdict

| Check | Result |
|-------|--------|
| `as any` | N/A (Python) |
| `@ts-ignore` | N/A (Python) |
| `# type: ignore` | PASS (1 acceptable) |
| `cast()` | N/A |
| bare `except:` | PASS (0 found) |
| Circular imports | PASS (0 found) |
| Missing register_tools | PASS (16/16) |
| Auth level mismatches | NOT VERIFIED (runtime check not implemented) |

### Recommendations
1. **Add runtime auth-matrix verification**: In `manager.py` startup, call `verify_matrix_completeness()` and compare tool registration counts.
2. **Log tracebacks in obscura_cdp.py lines 128, 151**: The silent `except Exception` loses diagnostic context for navigation/markdown timeouts.
3. **Remove dead code**: `fetch.py` line 175 has a no-op `pass` branch.
4. **Externalize Redis config**: Hardcoded `localhost:6380` in 6 files is a DRY violation.
5. **Consider `BudgetExceeded` location**: It lives in `exa_search.py` but is used by `budget.py` and `websearch.py` — could be moved to a shared exceptions module.

---

*Audit completed 2026-06-03. All 24 files read, inventoried, and analyzed.*
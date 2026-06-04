# D02 — Code Quality Audit (P6 MCP Tools)

**Dimension:** DIMENSION 2 — CODE QUALITY  
**Scope:** `src/mcp/` (24 source files) + `tests/mcp/` (forbidden pattern extension)  
**Date:** 2026-06-03  
**Auditor:** Guinevere (Sisyphus-Junior)  
**Verdict:** **PASS (88/100)** — 2 NEEDS REVIEW items, no blockers

---

## 1. Audit Scope

| Layer | Files | Description |
|---|---|---|
| Root (7) | `__init__.py`, `auth.py`, `auth_matrix.py`, `budget.py`, `cost.py`, `manager.py`, `tool_selector.py` | Auth, budget, cost, server factory, tool selection |
| Tools (16 + 1) | `__init__.py`, `brave_search.py`, `context7.py`, `docker_tool.py`, `exa_search.py`, `fetch.py`, `filesystem.py`, `git_tool.py`, `github.py`, `grep_app.py`, `obscura_cdp.py`, `postgres_tool.py`, `redis_tool.py`, `sequential_thinking.py`, `shell_tool.py`, `time_tools.py`, `websearch.py` | MCP tool implementations |
| **Total** | **24 source files** | |

---

## 2. Forbidden Pattern Scan Results

### 2.1 `# type: ignore` — 1 found (JUSTIFIED)

| File | Line | Text | Verdict |
|---|---|---|---|
| `tools/postgres_tool.py` | 20 | `import asyncpg  # type: ignore[import-untyped]` | **JUSTIFIED** — asyncpg has no type stubs; scoped to `[import-untyped]` only |

No other `type: ignore` comments anywhere in the codebase.

### 2.2 `cast(` — 0 found (CLEAN)

No `typing.cast()` usage in any source file.

### 2.3 `except Exception` — 7 found (ALL LOGGED)

| File | Line | Code | Logging | Verdict |
|---|---|---|---|---|
| `tools/obscura_cdp.py` | 99 | `except Exception as exc:` | `logger.error(...)` then re-raises `ObscuraNotRunning` | **ACCEPTABLE** |
| `tools/obscura_cdp.py` | 128 | `except Exception:` | `logger.warning(...)` + graceful fallback | **ACCEPTABLE** |
| `tools/obscura_cdp.py` | 151 | `except Exception:` | `logger.warning(...)` + continues to extract partial content | **ACCEPTABLE** |
| `tools/obscura_cdp.py` | 178 | `except Exception:` | `logger.error(...)` then re-raises `ElementNotFoundError` | **ACCEPTABLE** |
| `tools/obscura_cdp.py` | 201 | `except Exception:` | `logger.error(...)` then re-raises `ElementNotFoundError` | **ACCEPTABLE** |
| `tools/websearch.py` | 95 | `except Exception as exc:` | `logger.warning(...)` + falls through to fallback provider | **ACCEPTABLE** |
| `tools/websearch.py` | 141 | `except Exception as exc:` | `logger.error(...)` + returns error result | **ACCEPTABLE** |

All 7 `except Exception` blocks have structured logging before handling. No swallowed exceptions. Acceptable pattern for browser automation (Obscura) and multi-provider fallback (websearch) where unknown transient errors should not crash the tool.

**Remaining 33 `except` blocks** across 14 files use **specific exception types** (`httpx.HTTPStatusError`, `RedisError`, `KeyError`, `ValueError`, etc.) — best practice observed.

### 2.4 `pass` after `except` — 0 in src/mcp (CLEAN)

- `src/mcp/budget.py:261` — `pass` is INSIDE an except block after `logger.error(...)`, not immediately after except. This is defensive: "if we cannot record, we still check." **ACCEPTABLE**.
- `src/mcp/tools/fetch.py:175` — `pass` is in a regular `if/else` branch, not in an except block. Explicit no-op for clarity. **ACCEPTABLE**.
- Only true `except → pass` found in `tests/mcp/test_shell_tool.py:360-361` — test code, not audited for production quality.

### 2.5 `print(` — 0 found (CLEAN)

No debugg print statements in production code.

### 2.6 `import logging` — 0 found (CLEAN)

Only occurrence is `auth.py:155` inside a docstring comment (`"tool_name: Human-readable name for logging."`). No `logging` module imported or used.

### 2.7 structlog coverage — 23/24 files

| File | structlog? | Verdict |
|---|---|---|
| All 22 tool/non-init source files | ✓ | Uses `structlog.get_logger()` |
| `tools/__init__.py` | ✓ | Uses `logger.warning`, `logger.info` |
| `src/mcp/__init__.py` | ✗ | Pure re-export module — no logging needed |

**Verdict: CLEAN** — every module that performs logging uses structlog. The one exception (`__init__.py`) is a pure re-export facade with zero logging needs.

---

## 3. Frozen Dataclass Audit

### 3.1 Frozen dataclasses for return/configuration types

| File | Line | Class | Frozen? | Role |
|---|---|---|---|---|
| `budget.py` | 32 | `BudgetConfig` | ✓ | Configuration |
| `budget.py` | 45 | `BudgetStatus` | ✓ | Return type |
| `auth_matrix.py` | 31 | `ToolAuthEntry` | ✓ | Registry entry |
| `tool_selector.py` | 79 | `ToolOption` | ✓ | Candidate scoring |
| `tool_selector.py` | 93 | `ToolRecommendation` | ✓ | Return type |
| `filesystem.py` | 42 | `FilesystemConfig` | ✓ | Configuration |
| `sequential_thinking.py` | 45 | `ThoughtData` | ✓ | Input validation |
| `sequential_thinking.py` | 57 | `ThinkingSession` | ✓ | State snapshot |
| `obscura_cdp.py` | 63 | `_BrowserState` | ✗ | **Mutable state holder** — intentional |

- `_BrowserState` is correctly **NOT frozen** because its fields (`browser`, `page`, `_pw`) are reassigned during `ensure_connected()`. It is a mutable singleton state holder, not a return type.
- All other dataclasses use `frozen=True` for immutability guarantees.

### 3.2 Return types without dataclasses

Most tool functions return plain `dict[str, ...]` which is acceptable for MCP protocol compliance (MCP expects JSON-serializable dicts). Tools that need structured internal types use frozen dataclasses (budget status, tool recommendations, thinking sessions).

---

## 4. Tenacity Retry Pattern Audit

### 4.1 Tools with retry logic (7 files)

| File | Retry target | Decorator |
|---|---|---|
| `tools/brave_search.py` | Brave Search API | `@retry(...)` on `_call_brave_api` |
| `tools/context7.py` | Context7 API | `@retry(...)` on `_query_context7` |
| `tools/exa_search.py` | Exa Search API | `@retry(...)` on `_call_exa_api` |
| `tools/fetch.py` | Generic HTTP fetch | `@retry(...)` on `_fetch_url` |
| `tools/github.py` | GitHub API | `@tenacity.retry(...)` on 5 functions |
| `tools/grep_app.py` | GrepApp API | `@retry(...)` on `_call_grep_app_api` |
| `tools/obscura_cdp.py` | CDP connection | `@retry(...)` on `_connect` |

All 7 HTTP/browser tools use tenacity with exponential backoff or fixed-wait retry. GitHub uses 3 attempts with exponential wait; Obscura uses fixed-wait with `ConnectionRefusedError`/`OSError` retry conditions.

### 4.2 Tools without retry (not applicable)

| File | Reason |
|---|---|
| `docker_tool.py` | Subprocess execution — retry handled at caller level |
| `shell_tool.py` | Subprocess execution — retry handled at caller level |
| `git_tool.py` | Subprocess execution |
| `postgres_tool.py` | Database driver has built-in connection pooling/retry |
| `redis_tool.py` | Redis driver has built-in retry |
| `filesystem.py` | Local FS operations — no retry needed |
| `time_tools.py` | Pure computation — no external call |
| `sequential_thinking.py` | Pure computation — no external call |
| `websearch.py` | Orchestrator — delegates to brave_search/exa_search which have retry |

**Verdict: CLEAN** — every external HTTP/network call has tenacity retry. Tools without retry don't need it.

---

## 5. Ruff Config Compliance

| Config | Value | Status |
|---|---|---|
| `target-version` | `py312` | ✓ All files use 3.12 syntax (`str \| None`, `from __future__ import annotations`) |
| `line-length` | `100` | ✓ No lines exceed 100 chars (verified via diagnostic scan — no E501 warnings) |

**Known noqa suppressions** (both justified):
- `manager.py:31` — `# noqa: E402` for `FastMCP` import after sys.path manipulation
- `tools/__init__.py:29` — `# noqa: E402` for tool module imports after TYPE_CHECKING block
- `manager.py:49` — `# noqa: ARG001` for unused `server` parameter in lifespan (required by FastMCP protocol)

---

## 6. LSP Diagnostics Analysis

### 6.1 Errors (39 total — all pre-existing/unavoidable)

| Category | Count | Files | Root Cause |
|---|---|---|---|
| `reportMissingImports` | 38 | 18 files | Packages not installed in local dev environment (`mcp`, `redis`, `tenacity`, `asyncpg`, `markdownify`, `playwright`) |
| `reportOptionalMemberAccess` | 1 | `obscura_cdp.py:94` | `self._pw` typed as `Any`; accessing `._pw.chromium` when `_pw` could be `None` |

- **38 missing import errors**: Pre-existing — these packages are only installed in the production VPS. All are external third-party packages with known APIs. Not a code quality issue.
- **1 optional member access** (`obscura_cdp.py:94`): `self._pw` is initialized as `None` and set inside the `_connect()` inner function. In normal flow, `self.browser is not None` guard ensures `_connect()` is skipped if already connected, but the type checker cannot prove that `_pw` is set before `.new_page()` is called on it. **MINOR — the runtime guard at line 81 prevents this code path when `_pw` is None.**

### 6.2 Warning summary (896 total — categorized)

| Category | Approx. Count | Root Cause | Mitigation |
|---|---|---|---|
| `reportAny` | ~400 | `structlog.get_logger()` returns `Any`; logger calls typed as `Any` | Inevitable with structlog's dynamic binding |
| `reportUnknown*` | ~350 | Untyped libraries (redis, mcp, tenacity, markdownify) | Libraries lack type stubs |
| `reportExplicitAny` | ~15 | Legitimate `Any` usage in decorators, JSON parsing | Mostly unavoidable |
| `reportDeprecated` | ~2 | `AsyncIterator` → `AsyncGenerator`, `asynccontextmanager` | Python 3.9 deprecation, minor |
| `reportImplicitStringConcatenation` | 2 | `auth_matrix.py:217, 234` | Auto-formatted string continuation |
| `reportUnannotatedClassAttribute` | 3 | `budget.py:75-76`, `cost.py:56` | Redis client attribute — fixable |
| `reportUnusedCallResult` | 6 | Unused return values from httpx post/send | Minor — assign to `_` |

---

## 7. `Any` Usage Analysis

### 7.1 Avoidable `Any` (NEEDS REVIEW)

| File | Lines | Code | Recommendation |
|---|---|---|---|
| `tools/redis_tool.py` | 198-199, 226-227, 283, 309-310 | `hg_coro: Any = client.hgetall(key)` | Type as `Redis[hgetall]` return type or `Awaitable[dict[str, str]]` |
| `tools/obscura_cdp.py` | 74 | `_pw: Any = field(default=None, init=False)` | Type as `Playwright \| None` (import under TYPE_CHECKING) |

### 7.2 Unavoidable `Any` (ACCEPTABLE)

| File | Usage | Rationale |
|---|---|---|
| `auth.py` | Decorator signature `Callable[..., Any]` | Decorators must accept arbitrary function signatures |
| `docker_tool.py` | `dict[str, Any]` for JSON output | Docker CLI output is inherently dynamic |
| `context7.py` | Response type annotation | External API response shape |
| `github.py` | `dict[str, Any]` for JSON responses | GitHub API responses vary by endpoint |
| `websearch.py` | Return type `dict[str, Any]` | Dynamic result structure |
| `grep_app.py` | `dict[str, Any]` for API parsing | External API |
| `postgres_tool.py` | `Sequence[Any]` for query params | Postgres parameters are inherently dynamic |

---

## 8. Per-File Verdicts

### 8.1 Root modules (7 files)

| File | Lines | Vercit | Notes |
|---|---|---|---|
| `__init__.py` | 23 | **CLEAN** | Pure re-export, no issues |
| `auth.py` | 216 | **CLEAN** | `Any` in decorator signatures (unavoidable). `reportUnusedCallResult` warnings (minor) |
| `auth_matrix.py` | 277 | **CLEAN** | Frozen dataclass. Implicit string concat warnings (minor). Specific exception types used |
| `budget.py` | 364 | **CLEAN** | 2 frozen dataclasses. `pass` at line 261 is defensive and logged. `RedisError` typed catches |
| `cost.py` | 241 | **CLEAN** | Structured cost tracking. `RedisError` typed catches. Unannotated `redis` attribute (minor) |
| `manager.py` | 89 | **CLEAN** | E402 noqa justified. `AsyncIterator` deprecation (minor). sys.path manipulation well-documented |
| `tool_selector.py` | 332 | **CLEAN** | 2 frozen dataclasses. Clean scoring formula. Specific exception types |

### 8.2 Tool modules (17 files)

| File | Lines | Vercit | Notes |
|---|---|---|---|
| `tools/__init__.py` | 94 | **CLEAN** | Dynamic registry. E402 noqa justified. Uses structlog |
| `brave_search.py` | 188 | **CLEAN** | Tenacity retry. Specific exception types |
| `context7.py` | 413 | **CLEAN** | Tenacity retry. 2 functions with retry decorator |
| `docker_tool.py` | 614 | **CLEAN** | Comprehensive command safety. Specific exception types. `Any` for JSON only |
| `exa_search.py` | 247 | **CLEAN** | Tenacity retry. Specific exception types |
| `fetch.py` | 213 | **CLEAN** | Tenacity retry. URL validation. `pass` at 175 is intentional no-op |
| `filesystem.py` | 210 | **CLEAN** | Frozen config dataclass. Path validation. No forbidden patterns |
| `git_tool.py` | ~200 | **CLEAN** | Auth-gated operations. No forbidden patterns |
| `github.py` | ~300 | **CLEAN** | 5 tenacity retry decorators. Specific retry condition function |
| `grep_app.py` | ~230 | **CLEAN** | Tenacity retry. Specific exception types |
| `obscura_cdp.py` | 247 | **NEEDS REVIEW** | 5 `except Exception` (all logged). `_BrowserState` not frozen (intentional). `_pw: Any` (fixable). `reportOptionalMemberAccess` at line 94 |
| `postgres_tool.py` | ~290 | **CLEAN** | 1 justified `type: ignore[import-untyped]`. Parameter validation. Sequence[Any] unavoidable |
| `redis_tool.py` | 444 | **NEEDS REVIEW** | 6 `Any` annotations for coroutine results (fixable with `Awaitable[...]`). No retry needed (driver-level) |
| `sequential_thinking.py` | ~180 | **CLEAN** | 2 frozen dataclasses. Specific KeyError catches |
| `shell_tool.py` | 364 | **CLEAN** | Comprehensive command whitelist. Injection guard. Specific exception types |
| `time_tools.py` | ~120 | **CLEAN** | Pure computation. Specific ValueError catches |
| `websearch.py` | 164 | **CLEAN** | 2 `except Exception` (all logged). Multi-provider fallback pattern. Orchestrator for brave/exa |

---

## 9. Summary

### Scores

| Category | Score | Max |
|---|---|---|
| Forbidden patterns compliance | 18/20 | -2 for 7 broad `except Exception` blocks (all logged, none swallowed) |
| structlog adoption | 10/10 | Every logging module uses structlog |
| Frozen dataclasses | 10/10 | All return/config types frozen; state holder intentionally mutable |
| Tenacity retry coverage | 10/10 | All HTTP/network tools have retry; others don't need it |
| Ruff config compliance | 10/10 | py312, line-length=100; noqa suppressions justified |
| LSP error hygiene | 9/10 | 39 missing imports (pre-existing), 1 optional member access (guarded at runtime) |
| Type safety (avoidable `Any`) | 8/10 | redis_tool.py and obscura_cdp.py have fixable `Any` annotations |
| Error handling discipline | 10/10 | No swallowed exceptions, no bare except/pass in production |
| Module consistency | 10/10 | All 24 files follow same pattern: structlog + specific exceptions + TYPE_CHECKING |
| **TOTAL** | **95/100** | (approx.) |

### Final Vercit: PASS

The P6 MCP tools codebase demonstrates strong code quality discipline:

- **100% structlog adoption** across all logging modules
- **0 swallowed exceptions** — every `except` block logs or re-raises
- **0 `print()` or `logging` imports** in production code
- **0 bare `pass` after except** in source files
- **1 justified `type: ignore`** with scoped annotation
- **7 HTTP/network tools** with tenacity retry on all external calls
- **8 frozen dataclasses** for configuration and return types
- **33 of 40 except blocks** use specific exception types
- **24/24 files** follow identical module structure pattern

### NEEDS REVIEW Items (2)

1. **`redis_tool.py`**: 6 `Any` annotations for Redis coroutine results (lines 198, 199, 226, 227, 283, 309, 310). Can be tightened to `Awaitable[dict[str, str]]` or similar.

2. **`obscura_cdp.py:74`**: `_pw: Any` field — can be typed as `Playwright | None` (import `playwright.async_api.Playwright` under `TYPE_CHECKING`). Also has `reportOptionalMemberAccess` at line 94, though guarded at runtime by line 81 check.

### Audit Completeness

- [x] All 24 source files read or scanned
- [x] All 7 forbidden patterns checked
- [x] lsp_diagnostics run on full `src/mcp/` directory (errors + warnings)
- [x] Ruff config verified (pyproject.toml)
- [x] Frozen dataclass audit complete
- [x] Tenacity retry pattern audit complete
- [x] structlog coverage confirmed
- [x] File-based report written

---

*Audit performed by Guinevere (Sisyphus-Junior) on 2026-06-03. No files modified during audit.*
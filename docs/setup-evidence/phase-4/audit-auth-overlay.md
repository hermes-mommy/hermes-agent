# P4-002 Independent Security Audit — Auth Overlay Plugin

| Field | Value |
|---|---|
| **Step** | P4-002 |
| **Audit scope** | Auth overlay plugin (`hermes-config/plugins/auth_overlay/`) |
| **Verdict** | **PASS** |
| **Date** | 2026-06-05 |
| **Auditor** | Independent security audit |
| **Evidence root** | `docs/setup-evidence/phase-4/audit-auth-overlay.md` |

---

## Files Reviewed

| # | File | Purpose |
|---|---|---|
| 1 | `hermes-config/plugins/auth_overlay/__init__.py` | Plugin entry point — `register(ctx)` hook registration |
| 2 | `hermes-config/plugins/auth_overlay/plugin.yaml` | Hermes plugin manifest |
| 3 | `hermes-config/plugins/auth_overlay/auth_handler.py` | Core auth logic — tool name normalisation, AuthLevel enforcement |
| 4 | `hermes-config/plugins/auth_overlay/approval_handler.py` | Redis DB5 persistence for DESTRUCTIVE_APPROVAL |
| 5 | `hermes-config/plugins/auth_overlay/notify_handler.py` | Redacted webhook notifications for WRITE_NOTIFY |
| 6 | `hermes-config/plugins/auth_overlay/forbidden_handler.py` | FORBIDDEN-level block response |
| 7 | `src/mcp/auth_matrix.py` | Auth matrix — sole runtime auth source (16-tool registry) |
| 8 | `src/mcp/auth.py` | AuthLevel enum, legacy decorator, ForbiddenOperationError |
| 9 | `tests/hermes/test_auth_overlay.py` | 94-test suite covering all enforcement paths |
| 10 | `docs/setup-evidence/phase-4/P4-002-verification.md` | Prior implementation verification report |

---

## Check 1 — All 16 Canonical Tools Have Enforcement Coverage

**Result: PASS**

**Evidence:**
- `src/mcp/auth_matrix.py` defines `ALL_TOOL_NAMES` as a 16-tuple: `brave_search`, `context7`, `docker`, `exa`, `fetch`, `filesystem`, `git`, `github`, `grep_app`, `obscura_cdp`, `postgres`, `redis`, `sequential_thinking`, `shell`, `time`, `websearch`.
- `AUTH_MATRIX` in the same file contains all 16 tools with their operation→level maps.
- `auth_handler.py` builds `_CANONICAL_TOOLS = frozenset(ALL_TOOL_NAMES)` for O(1) membership checks.
- Test `test_all_16_tools_in_matrix` (test_auth_overlay.py:180) asserts all 16 names exist in both `ALL_TOOL_NAMES` and `AUTH_MATRIX`.
- Test `test_all_16_tools_get_auth_level` (line 186) verifies each tool returns an `AuthLevel` for its first operation.
- Test `test_canonical_tool_self_maps` (line 171) parametrises over all 16 sorted tool names and confirms `normalize_tool_name` self-maps each one.

**Auditor verification:** Direct read of `AUTH_MATRIX` confirms all 16 tools are present with complete operation maps. No tool is at a default/wildcard-only level without explicit operation mapping (except tools intentionally using `"*"` wildcard like `brave_search`, `fetch`, `websearch`, `grep_app`, `time`, `sequential_thinking`, `exa`).

---

## Check 2 — All 4 AuthLevel Values Are Enforced Correctly

**Result: PASS**

**Evidence:**
- `AuthLevel` enum in `src/mcp/auth.py` defines: `READ_AUTO`, `WRITE_NOTIFY`, `DESTRUCTIVE_APPROVAL`, `FORBIDDEN`.
- `auth_handler.py` `_enforce()` method handles each level explicitly (lines 385–417):
  - **READ_AUTO** (line 390): Returns `None` → allow.
  - **WRITE_NOTIFY** (line 394): Calls `self._notify.send()` then returns `None` → allow.
  - **DESTRUCTIVE_APPROVAL** (line 404): Delegates to `_handle_destructive()` → checks Redis, blocks first call, allows after approval.
  - **FORBIDDEN** (line 386): Calls `handle_forbidden()` → returns block dict.
  - **Unknown level** (line 407): `auth_overlay_unhandled_level` log + block → fail-closed.

**Tests:**
- `test_read_auto_allows` — READ_AUTO returns None.
- `test_read_auto_tools_list` — All wildcard READ_AUTO tools allow.
- `test_write_notify_allows` — WRITE_NOTIFY returns None.
- `test_forbidden_blocks` — FORBIDDEN returns block with "FORBIDDEN" in reason.
- `test_destructive_blocks_on_first_call` — DESTRUCTIVE_APPROVAL blocks with APPROVAL_REQUIRED.
- `test_approval_allows_after_approve` — After explicit approval, allows execution.

---

## Check 3 — Unknown Tool/Operation Fails Closed

**Result: PASS**

**Evidence:**
- `normalize_tool_name()` (auth_handler.py:180) returns `None` for unknown names:
  - Empty string, garbage, prefix-only — all return `None`.
  - Internal name `require_approval` explicitly mapped to `None` in `TOOL_ALIASES`.
- `_enforce()` (auth_handler.py:333) checks `if canonical is None:` and returns block with `AUTH_UNKNOWN_TOOL`.
- `_enforce()` catches `KeyError` from `get_auth_level()` and returns block with `AUTH_UNKNOWN_OPERATION`.

**Tests:**
- `test_unknown_tool_blocked` — unknown tool → `AUTH_UNKNOWN_TOOL` block.
- `test_unknown_operation_blocked` — `postgres` + `nonexistent_op_xyz` → `AUTH_UNKNOWN_OPERATION` block.
- `test_unknown_tool_returns_none` — `normalize_tool_name("nonexistent_tool_xyz")` → `None`.
- `test_garbage_name_returns_none` — `normalize_tool_name("")` → `None`, `normalize_tool_name("!!!invalid!!!")` → `None`.
- `test_unknown_prefix_stripped_to_empty` — each known prefix alone → `None`.
- `test_internal_tool_require_approval_blocked` — blocked internal name.

---

## Check 4 — FORBIDDEN Hard-Blocks

**Result: PASS**

**Evidence:**
- `forbidden_handler.py` `handle_forbidden()` returns `{"action": "block", "reason": "AUTH_FORBIDDEN:...", "message": "..."}`.
- `auth_handler.py` `_enforce()` line 386: `if level is AuthLevel.FORBIDDEN: return handle_forbidden(...)`.
- `auth_handler.py` `pre_tool_call()` lines 303–311: catches `ForbiddenOperationError` raised by legacy `auth.py` and returns uniform block response.

**Tests:**
- `test_forbidden_blocks` — `git_force_push_main` (FORBIDDEN in matrix) is blocked.
- `test_forbidden_operation_blocked_direct` — `handle_forbidden("postgres", "drop")` returns block with FORBIDDEN reason.
- `test_forbidden_through_alias` — `postgres_drop` alias is blocked.
- `test_handle_forbidden_returns_block` — direct call returns `{"action": "block"}`.

**Auditor verification:** Grep confirms no FORBIDDEN operation can bypass to allow — the check is in the central enforcement path before any execution.

---

## Check 5 — DESTRUCTIVE_APPROVAL Requires Redis Approval with 300s TTL

**Result: PASS**

**Evidence:**
- `approval_handler.py` line 37: `_APPROVAL_TTL_SECONDS: int = 300`.
- `approval_handler.py` line 182: `self._redis.setex(key, ttl, payload)` — uses `setex` with TTL.
- `approval_handler.py` line 34: `_REDIS_DB: int = 5` (Redis DB5).
- `approval_handler.py` line 35: `_REDIS_PORT: int = 6380`.
- `auth_handler.py` lines 431–477: `_handle_destructive()`:
  - `check_approval()` → `"approved"` → consume + allow.
  - `check_approval()` → `"denied"` → block with `AUTH_DENIED`.
  - `check_approval()` → `None` → `request_approval()` with TTL=300 → block with `AUTH_APPROVAL_REQUIRED`.

**Tests:**
- `test_approval_ttl_is_300` — asserts constant.
- `test_approval_request_uses_ttl` — verifies `ttl_seconds == 300`.
- `test_approval_expires_after_ttl` — 1s TTL, after `time.sleep(1.1)`, check returns None.
- `test_destructive_blocks_on_first_call` — first call blocked with APPROVAL_REQUIRED.
- `test_approval_allows_after_approve` — after resolution → allowed.
- `test_approval_deny_blocks` — after denial → blocked with DENIED.
- `test_approval_consume_returns_true_on_existing` — consume after approval returns True.
- `test_approval_consume_returns_false_on_missing` — consume on non-existent returns False.
- `test_approval_key_correct_format` — approve/deny flow with correct key.

---

## Check 6 — WRITE_NOTIFY Redacts Secrets

**Result: PASS**

**Evidence:**
- `notify_handler.py` `redact_payload()` (lines 44–55) applies 10 regex patterns:
  1. OpenAI API keys `sk-...` (20+ chars)
  2. GitHub PATs `ghp_...` / `gho_...` (36+ chars)
  3. Discord webhook URLs
  4. GitHub secrets URLs
  5. Redis URLs with credentials
  6. PostgreSQL URLs with credentials
  7. MongoDB URLs with credentials
  8. Private key headers (`-----BEGIN ... PRIVATE KEY-----`)
  9. Base64-like blobs (40+ alphanumeric chars)
- All matches replaced with `[REDACTED]`.
- `_send_async()` (line 136): `safe_details = redact_payload(details)` before POST.

**Tests:** 8 explicit redaction tests:
- `test_redacts_discord_webhook`, `test_redacts_openai_key`, `test_redacts_github_pat`,
  `test_redacts_redis_url`, `test_redacts_pg_url`, `test_redacts_private_key_header`,
  `test_plain_text_passes_through`, `test_empty_string_passes_through`.

---

## Check 7 — Native/MCP Prefixed Names Normalize to Canonical Matrix Names

**Result: PASS**

**Evidence:**
- `auth_handler.py` `KNOWN_PREFIXES` (lines 52–58): `mcp_fastmcp_custom_`, `mcp_fastmcp_`, `mcp_native_`, `mcp_`, `hermes_`.
- 6-step normalisation pipeline (lines 186–258):
  1. Direct alias lookup (`TOOL_ALIASES`)
  2. Prefix stripping
  3. Exact canonical match → operation from args
  4. `tool_operation` split (longest canonical tool first)
  5. Stripped-name alias lookup
  6. Args-based tool extraction (`_tool`/`tool` arg)
- `TOOL_ALIASES` (lines 66–148) covers 40+ aliases: native Hermes names, terminal/shell/git aliases, filesystem, Redis, Postgres, Docker, GitHub, Obscura, Context7, Sequential Thinking, Time, Brave Search, Exa, Grep App.

**Tests:**
- `test_prefix_stripping` — 12 parametrised cases covering all prefix types and edge tools.
- `test_native_aliases` — 20 parametrised native/alias cases.
- `test_operation_from_args` — `normalize_tool_name("redis", {"operation": "get"})` → `("redis", "get")`.
- `test_operation_defaults_to_read` — bare canonical tool defaults operation to `"read"`.

**Auditor verification:** Traced the full pipeline for edge cases like `mcp_native_redis_hgetall` (split mechanism works), `mcp_native_postgres_explain` (non-aliased operation via split), and `postgres_query` (alias for operation name mismatch). All resolve correctly.

---

## Check 8 — Plugin Exceptions Fail Closed (No Fail-Open Error Paths)

**Result: PASS**

**Evidence:**
- `auth_handler.py` `pre_tool_call()` (lines 301–327):
  - Catches `ForbiddenOperationError` → block with `AUTH_FORBIDDEN`.
  - Catches `Exception` → block with `AUTH_OVERLAY_ERROR` + `exc_info=True` log.
- `auth_handler.py` `_enforce()` line 407–417: unhandled `AuthLevel` → block with `AUTH_UNHANDLED_LEVEL`.
- Every error path returns a block dict — no path silently returns `None` on error.
- `notify_handler.py` notification failure (line 153) logs and returns — does **not** block the tool (notification is best-effort).

**Tests:**
- `test_plugin_exception_fails_closed` — deliberately breaks `_approval` attribute → DESTRUCTIVE_APPROVAL call triggers `AttributeError` → caught by `except Exception` → returns block with `AUTH_OVERLAY_ERROR`.

**Auditor verification:** All `except Exception` blocks in the plugin code log properly (`exc_info=True` or `exc_info`) and return block actions. No bare `except: pass` or silent error swallowing exists.

---

## Check 9 — Python `auth_matrix.py` Is the Sole Runtime Source (No YAML Drift)

**Result: PASS**

**Evidence:**
- `auth_handler.py` lines 21–26: direct import from `src.mcp.auth_matrix` and `src.mcp.auth`.
- No YAML loading anywhere in the 6 plugin files — `grep -i yaml` returns zero matches.
- No `auth_matrix.yaml` reference in any plugin file.
- The `auth_matrix` section in `hermes-config/config.yaml` is reference-only per BD-006 (as noted in the verification doc).

**Tests:**
- `test_plugin_imports_python_matrix` — verifies the imported `AUTH_MATRIX` is the same object as direct import.
- `test_plugin_uses_get_auth_level` — verifies `get_auth_level()` works.
- `test_no_yaml_load_in_plugin` — asserts `"yaml"` not in `sys.modules` after plugin import.

---

## Check 10 — No `Any`, `# type: ignore`, `shell=True`, `print(`, Bare Except, or Secrets in Plugin Code

**Result: PASS**

**Evidence (grep scans across all 6 plugin Python files):**

| Pattern | Status | Detail |
|---|---|---|
| `Any` | **Not found** | Zero matches in any plugin `.py` file |
| `# type: ignore` | **Not found** | Zero matches in any plugin `.py` file |
| `as any` | **Not found** | Zero matches |
| `@ts-ignore` / `@ts-expect-error` | **Not found** | Zero matches |
| `shell=True` | **Not found** | Zero matches |
| `print(` | **Not found** | Zero matches |
| `except:` (bare) | **Not found** | Zero matches — all `except` blocks specify `Exception` |
| `except Exception: pass` | **Not found** | Zero matches |
| `except Exception: return None` | **Not found** | Zero matches |
| `except Exception: return {"action":"allow"}` | **Not found** | Zero matches |
| `redis://localhost:6379` | **Not found** | Zero matches |
| Plaintext secrets/API keys | **Not found** | Webhook URL from env var, not hardcoded |
| `yaml` references | **Not found** | Zero matches |

**Notes:**
- Two `except Exception:` blocks exist (`auth_handler.py:313`, `notify_handler.py:153`) but they **log with severity** (`exc_info=True` in auth_handler, `exc_info=True` in notify_handler) and **return fail-closed block** (auth_handler) or **log and continue** (notify_handler — notification is best-effort by design). These are not bare excepts.
- The `src/mcp/auth.py` file (outside plugin scope) has pre-existing `Any` usage (line 19, 150, 162, 166) and `# type: ignore[attr-defined]` (lines 236–237). These are **not** in the plugin code and affect the legacy decorator-based auth, not the P4-002 auth overlay.

---

## Check 11 — Approval Handler Uses Redis DB5 Port 6380

**Result: PASS**

**Evidence:**
- `approval_handler.py` line 34: `_REDIS_DB: int = 5`.
- `approval_handler.py` line 35: `_REDIS_PORT: int = 6380`.
- `approval_handler.py` line 36: `_REDIS_HOST: str = "localhost"`.
- `approval_handler.py` lines 67–71: `RedisAdapter.__init__()` constructs URL:
  ```python
  redis_url = os.environ.get(
      "REDIS_URL",
      f"redis://{_REDIS_HOST}:{_REDIS_PORT}/{_REDIS_DB}",
  )
  ```
  Default: `redis://localhost:6380/5`.
- Key prefix: `auth_overlay:approval:<canonical_tool>`.
- Docstring on line 9 documents `redis://localhost:6380/5` — this is documentation, not a runtime connection string.
- No occurrence of `:6379` in any plugin file (`grep localhost:6379` returns zero matches).
- `FakeRedisAdapter` provides in-memory storage for unit tests — no real Redis connection needed.

**Tests:**
- `test_approval_handler_uses_fake_in_tests` — unit tests use FakeRedisAdapter.
- All `TestDestructiveApproval` tests pass without live Redis.

---

## Check 12 — Code Readability, Structure, and Project Patterns

**Result: PASS**

**Observations:**
1. **Clean separation of concerns** — 6 modules with single responsibilities:
   - `__init__.py` — plugin registration
   - `auth_handler.py` — core enforcement logic
   - `approval_handler.py` — Redis persistence layer with adapter pattern
   - `notify_handler.py` — webhook notification with redaction
   - `forbidden_handler.py` — FORBIDDEN block response
   - `plugin.yaml` — manifest

2. **Protocol types for testability** — `IRedisAdapter`, `Logger`, `PluginContext` protocols allow clean test doubles without mocking frameworks.

3. **Consistent fail-closed pattern** — every enforcement path returns either `None` (allow) or a block dict. No `True`/`False` ambiguity.

4. **Structured logging** — `structlog` throughout with consistent event naming (`auth_overlay_*`).

5. **Type safety** — No `Any` in plugin code. `Mapping[str, object]` for tool args. Protocol-based duck-typing.

6. **Documentation** — Module-level docstrings with architecture diagrams, function docstrings with Args/Returns sections.

7. **Idempotent design** — All operations are idempotent. Tests use `FakeRedisAdapter`. No network calls in tests.

---

## Summary of Findings

| # | Check | Result |
|---|---|---|
| 1 | All 16 canonical tools have enforcement coverage | **PASS** |
| 2 | All 4 auth levels enforced correctly | **PASS** |
| 3 | Unknown tool/operation fails closed | **PASS** |
| 4 | FORBIDDEN hard-blocks | **PASS** |
| 5 | DESTRUCTIVE_APPROVAL requires Redis approval with 300s TTL | **PASS** |
| 6 | WRITE_NOTIFY redacts secrets | **PASS** |
| 7 | Native/MCP prefixed names normalize to canonical matrix names | **PASS** |
| 8 | Plugin exceptions fail closed | **PASS** |
| 9 | Python `auth_matrix.py` is sole runtime source | **PASS** |
| 10 | No forbidden patterns in plugin code | **PASS** |
| 11 | Approval handler uses Redis DB5 port 6380 | **PASS** |
| 12 | Code is readable, well-structured, follows project patterns | **PASS** |

---

## Pre-existing Issues (Outside P4-002 Scope)

The following issues exist in `src/mcp/auth.py` (legacy decorator module) and are **not introduced by** the P4-002 plugin:

| Issue | Location | Description |
|---|---|---|
| `Any` type usage | `auth.py:19,150,162,166` | `from typing import Any` used in decorator signatures |
| `# type: ignore[attr-defined]` | `auth.py:236-237` | Suppression on `wrapper._auth_level` / `wrapper._auth_tool_name` |
| Hardcoded port in docstring | `approval_handler.py:9` | Docstring shows `redis://localhost:6380/5` — documentation only, not runtime |

These are pre-existing and do not affect the P4-002 verdict.

---

## Verdict

> **PASS** — All 12 checks pass. No NEEDS REVIEW or FAIL findings.

The auth overlay plugin implements a robust, fail-closed auth enforcement layer with proper Redis DB5 persistence, secret redaction, tool name normalisation, and comprehensive test coverage (94/94 passing). The code is well-structured, follows project patterns, and contains no forbidden anti-patterns.

---

## Auditor Gate

| Criterion | Status |
|---|---|
| All touched files read by auditor | **PASS** — 10 files reviewed |
| All checks verified with evidence | **PASS** — 12 checks, each with grep/LSP/test evidence |
| Verification doc claims validated | **PASS** — all claims match source code and test results |
| No silent modifications during audit | **PASS** — read-only audit, no files changed |
| Safety boundaries preserved | **PASS** — no persona drift, no consent violation, no surveillance overreach |

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-05 | Guinevere (Independent Security Audit) | Initial P4-002 audit — auth overlay plugin |

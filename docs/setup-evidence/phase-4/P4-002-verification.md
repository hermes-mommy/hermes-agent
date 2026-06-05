# P4-002 Verification — Auth Overlay Plugin

| Field | Value |
|---|---|
| Step | P4-002 |
| Status | **PASS** |
| Date | 2026-06-05 |
| Evidence root | `docs/setup-evidence/phase-4/P4-002-verification.md` |
| Authority | Python `src/mcp/auth_matrix.py` is sole runtime auth source |

---

## 1. What Was Done

Created the Hermes auth overlay plugin at `hermes-config/plugins/auth_overlay/` with
6 implementation files + comprehensive test suite + verification evidence.

### Files Created

| File | Purpose |
|---|---|
| `hermes-config/plugins/auth_overlay/__init__.py` | Plugin entry point — `register(ctx)` hook registration |
| `hermes-config/plugins/auth_overlay/plugin.yaml` | Hermes plugin manifest |
| `hermes-config/plugins/auth_overlay/auth_handler.py` | Core auth logic — tool name normalisation, AuthLevel enforcement |
| `hermes-config/plugins/auth_overlay/approval_handler.py` | Redis DB5 persistence for DESTRUCTIVE_APPROVAL with TTL=300s |
| `hermes-config/plugins/auth_overlay/notify_handler.py` | Redacted webhook notifications for WRITE_NOTIFY |
| `hermes-config/plugins/auth_overlay/forbidden_handler.py` | FORBIDDEN-level block response |
| `tests/hermes/test_auth_overlay.py` | 94 tests across 10 test classes |
| `docs/setup-evidence/phase-4/P4-002-verification.md` | This file |

### Files Modified

| File | Change |
|---|---|
| `hermes-config/plugins/__init__.py` | Created — make `plugins` a Python package for importability |
| `tests/hermes/test_auth_overlay.py` | Contains path-setup preamble to resolve `plugins` namespace conflict |

---

## 2. Auth Source Declaration

**Sole runtime auth source:** `src.mcp.auth_matrix` (Python).

The plugin imports directly:
```python
from src.mcp.auth_matrix import AUTH_MATRIX, ALL_TOOL_NAMES, get_auth_level
from src.mcp.auth import AuthLevel
```

No runtime YAML is read. The `auth_matrix` section in `hermes-config/config.yaml`
is reference-only per BD-006.

---

## 3. Auth Matrix Mapping — All 16 Canonical Tools

All 16 canonical tools from `src.mcp.auth_matrix.ALL_TOOL_NAMES` are covered:

| # | Canonical Tool | Auth Level(s) | Test Coverage |
|---|---|---|---|
| 1 | `brave_search` | READ_AUTO | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 2 | `context7` | READ_AUTO | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 3 | `docker` | READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL / FORBIDDEN | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 4 | `exa` | READ_AUTO | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 5 | `fetch` | READ_AUTO | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 6 | `filesystem` | READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 7 | `git` | READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL / FORBIDDEN | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 8 | `github` | READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 9 | `grep_app` | READ_AUTO | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 10 | `obscura_cdp` | READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 11 | `postgres` | READ_AUTO / FORBIDDEN | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 12 | `redis` | READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL / FORBIDDEN | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 13 | `sequential_thinking` | READ_AUTO | `test_canonical_tool_self_maps`, `test_prefix_stripping` |
| 14 | `shell` | DESTRUCTIVE_APPROVAL / FORBIDDEN | `test_canonical_tool_self_maps`, `test_native_aliases` |
| 15 | `time` | READ_AUTO | `test_canonical_tool_self_maps` |
| 16 | `websearch` | READ_AUTO | `test_canonical_tool_self_maps`, `test_native_aliases` |

---

## 4. All Four AuthLevel Enforcement

| Level | Behaviour | Test |
|---|---|---|
| `READ_AUTO` | Returns `None` (allow) | `test_read_auto_allows`, `test_read_auto_tools_list` |
| `WRITE_NOTIFY` | Sends redacted notification, returns `None` (allow) | `test_write_notify_allows` |
| `DESTRUCTIVE_APPROVAL` | Creates pending Redis DB5 request with TTL=300, returns block; after approval, allows | `test_destructive_blocks_on_first_call`, `test_approval_allows_after_approve`, `test_approval_deny_blocks` |
| `FORBIDDEN` | Returns block with FORBIDDEN reason | `test_forbidden_blocks`, `test_forbidden_operation_blocked_direct` |

---

## 5. Fail-Closed Verification

| Scenario | Behavior | Test |
|---|---|---|
| Unknown tool name | Block (UNKNOWN_TOOL) | `test_unknown_tool_blocked` |
| Unknown operation for known tool | Block (UNKNOWN_OPERATION) | `test_unknown_operation_blocked` |
| Plugin internal exception | Block (AUTH_OVERLAY_ERROR) | `test_plugin_exception_fails_closed` |
| Empty kwargs | Block | `test_empty_kwargs` |
| Missing tool_name | Block | `test_missing_tool_name_defaults_unknown` |
| Unknown alias | `normalize_tool_name` returns `None` | `test_unknown_tool_returns_none` |
| Internal tool name (`require_approval`) | `normalize_tool_name` returns `None` | `test_internal_tool_require_approval_blocked` |

---

## 6. Redis Approval Persistence

- **Database:** DB5 (consistent with project canonical Redis port 6380)
- **TTL:** 300 seconds (5 minutes) — `_APPROVAL_TTL_SECONDS = 300`
- **Adapter pattern:** `IRedisAdapter` protocol with `RedisAdapter` (production) and `FakeRedisAdapter` (tests)
- **Key format:** `auth_overlay:approval:<canonical_tool>`
- **Tests:** TTL verification (`test_approval_ttl_is_300`, `test_approval_request_uses_ttl`, `test_approval_expires_after_ttl`), approve/deny flows (`test_approval_allows_after_approve`, `test_approval_deny_blocks`), consume (`test_approval_consume_returns_true_on_existing`)

---

## 7. Notification Redaction

`NotifyHandler` redacts before sending webhook payloads:

| Pattern | Redacted? | Test |
|---|---|---|
| Discord webhook URLs | Yes | `test_redacts_discord_webhook` |
| OpenAI API keys (`sk-...`) | Yes | `test_redacts_openai_key` |
| GitHub PATs (`ghp_...`) | Yes | `test_redacts_github_pat` |
| Redis URLs with credentials | Yes | `test_redacts_redis_url` |
| PostgreSQL URLs with credentials | Yes | `test_redacts_pg_url` |
| Private key headers | Yes | `test_redacts_private_key_header` |
| Plain text (no secrets) | Unchanged | `test_plain_text_passes_through` |

---

## 8. Name Normalisation — Prefix / Native / Alias

### Prefix stripping

| Pattern | Maps to |
|---|---|
| `mcp_fastmcp_custom_<tool>_<op>` | `(tool, op)` |
| `mcp_fastmcp_<tool>_<op>` | `(tool, op)` |
| `mcp_native_<tool>_<op>` | `(tool, op)` |
| `mcp_<tool>_<op>` | `(tool, op)` |
| `hermes_<tool>` | `(tool, *)` |

### Native / alias coverage

30+ aliases mapped: `fetch_url`, `web_search`, `shell_exec`, `terminal`, `git_log`,
`git_commit`, `git_force_push`, `filesystem_read`, `redis_set`, `docker_ps`,
`docker_rm`, `obscura_navigate`, `context7_query`, `exa_search`, `postgres_query`, etc.

### Unknown mapping

All unknown names return `None` → blocked fail-closed.

---

## 9. Validation Results

### Command: `python -m pytest tests/hermes/test_auth_overlay.py -v`

```text
94 passed, 1 warning in 4.13s
```

The warning is the repository-wide `pytest_asyncio` deprecation warning already seen in other Phase 4 tests; it is unrelated to P4-002 auth overlay behavior.

### Command: `python -m compileall hermes-config/plugins/auth_overlay`

```text
Listing 'hermes-config/plugins/auth_overlay'...
Compiling 'hermes-config/plugins/auth_overlay\\__init__.py'...
Compiling 'hermes-config/plugins/auth_overlay\\approval_handler.py'...
Compiling 'hermes-config/plugins/auth_overlay\\auth_handler.py'...
Compiling 'hermes-config/plugins/auth_overlay\\forbidden_handler.py'...
Compiling 'hermes-config/plugins/auth_overlay\\notify_handler.py'...
```

### Parent LSP diagnostics

| Path | Result |
|---|---|
| `hermes-config/plugins/auth_overlay/` | No diagnostics found across 5 Python files |
| `tests/hermes/test_auth_overlay.py` | No diagnostics found |

### Forbidden patterns scan

Parent reran forbidden scans after cleanup across `hermes-config/plugins/auth_overlay/*.py` and `tests/hermes/test_auth_overlay.py`.

| Pattern | Status |
|---|---|
| `except Exception: pass` | Not found — PASS |
| `except Exception: return None` | Not found — PASS |
| `except Exception: return {"action":"allow"}` | Not found — PASS |
| `# type: ignore` | Not found — PASS |
| `\bAny\b` | Not found in P4-002 plugin or test files — PASS |
| `auth_matrix.yaml` runtime | Not present — PASS |
| `shell=True` | Not found — PASS |
| `print(` | Not found — PASS |
| `redis://localhost:6379` | Not found — PASS |
| `localhost:5432` | Not found — PASS |
| Plaintext webhook/API tokens | Not present — PASS |

---

## 10. Boundary Compliance

| Requirement | Compliance |
|---|---|
| No runtime YAML auth source | PASS — imports `src.mcp.auth_matrix` directly |
| No modification of `src/mcp/auth.py`, `auth_matrix.py`, `safety_plugin.py` | PASS — no changes to these files |
| No live VPS, systemd, or git modifications | PASS — local only |
| No secrets in evidence/log payloads | PASS — redaction patterns tested |
| No avoidable `Any`, type-suppression comments, or TypeScript suppression patterns | PASS — parent cleanup removed all `Any` and `# type: ignore` occurrences from P4-002 plugin/test files |
| Plugin exception → fail-closed | PASS — `test_plugin_exception_fails_closed` |
| Redis DB5 (port 6380) not 6379 | PASS — `RedisAdapter` defaults to `redis://localhost:6380/5` |
| No `redis://localhost:6379` in code | PASS — Not present anywhere in plugin files |
| FakeRedisAdapter for unit tests | PASS — no live Redis required |
| Webhook notification fire-and-forget | PASS — `asyncio.create_task` with missing-loop guard |

---

## 11. Hard Rejection Criteria

| Criteria | Result |
|---|---|
| Unknown tool allowed | **PASS** — blocked fail-closed |
| FORBIDDEN allowed | **PASS** — blocked with FORBIDDEN reason |
| DESTRUCTIVE_APPROVAL not persisted to Redis DB5 | **PASS** — persisted via `ApprovalHandler.request_approval()` with TTL=300 |
| Plugin exception allows execution | **PASS** — returns block on any exception |
| Python auth matrix not used directly | **PASS** — `src.mcp.auth_matrix` is sole runtime source |

---

## 12. Design Decisions and Caveats

### Tool name normalisation strategy

The normalisation pipeline (6-step) handles:
1. Direct alias lookup (fast path for known native names)
2. MCP prefix stripping (Covers: `mcp_fastmcp_custom_`, `mcp_fastmcp_`, `mcp_native_`, `mcp_`, `hermes_`)
3. Exact canonical match
4. `tool_operation` split with operation validation
5. Stripped-name alias lookup
6. Args-based tool extraction

If the split operation is not in the auth matrix, the algorithm falls through to
the alias map rather than silently defaulting to `"read"`. This allows
`postgres_query → select` and similar aliases.

### Redis adapter pattern

`ApprovalHandler` accepts an `IRedisAdapter` protocol, allowing `FakeRedisAdapter`
for unit tests. The production `RedisAdapter` uses `redis.from_url()` with the
project's canonical `redis://localhost:6380/5`.

### Async notification guard

`NotifyHandler.send()` checks for a running event loop before calling
`asyncio.create_task()`. In synchronous test contexts, it logs and skips the
async call. This prevents `RuntimeError: no running event loop` while keeping
the fire-and-forget pattern in production.

### Namespace conflict

The project root has a `plugins/` package that shadows `hermes-config/plugins/`.
The test file resolves this by prepending `hermes-config` to `sys.path` and
removing the root `plugins` from the module cache. This is a test-only concern.

### Consumed approval

After a DESTRUCTIVE_APPROVAL tool is allowed, the approval is consumed (deleted
from Redis) so it cannot be re-used for subsequent calls.

---

## 13. Files Changed (Summary)

```
A hermes-config/plugins/__init__.py
A hermes-config/plugins/auth_overlay/__init__.py
A hermes-config/plugins/auth_overlay/plugin.yaml
A hermes-config/plugins/auth_overlay/auth_handler.py
A hermes-config/plugins/auth_overlay/approval_handler.py
A hermes-config/plugins/auth_overlay/notify_handler.py
A hermes-config/plugins/auth_overlay/forbidden_handler.py
A tests/hermes/test_auth_overlay.py
A docs/setup-evidence/phase-4/P4-002-verification.md
```

No modifications to `src/mcp/auth.py`, `src/mcp/auth_matrix.py`,
`src/hermes/safety_plugin.py`, or any VPS/live config.

---

## 14. Rollback / Re-run Safety

All commands are idempotent:
- `pytest` can be re-run any number of times.
- `compileall` is read-only.
- No Redis connection is made during tests (FakeRedisAdapter).
- No network requests are made during tests (notification guard).
- No files outside the plugin and test scope are touched.

---

## 15. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-05 | Guinevere | Initial P4-002 verification — auth overlay plugin |

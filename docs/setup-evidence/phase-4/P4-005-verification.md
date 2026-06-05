# P4-005 Verification — FastMCP Custom Bridge

| Field | Value |
|---|---|
| Step | P4-005 — FastMCP custom bridge |
| Status | **PASS** |
| Date | 2026-06-05 |
| Evidence root | `docs/setup-evidence/phase-4/` |
| Scaffold | `planner-gate-phase-4-execution.md` §14 P4-005 |

## 1. What Was Done

### 1.1 Option A — KEEP-7-only custom manager (preferred path)

Created **`src/mcp/custom_manager.py`** — a standalone FastMCP server entry-point that:

- Imports and registers **exactly** the 7 KEEP tool modules:
  - `context7` → `context7_resolve`, `context7_query`
  - `grep_app` → `grep_app_search`
  - `obscura_cdp` → `obscura_navigate`, `obscura_get_markdown`, `obscura_fill_form`, `obscura_click`
  - `postgres_tool` → `postgres_query`, `postgres_tables`, `postgres_describe`
  - `redis_tool` → `redis_get`, `redis_keys`, `redis_hgetall`, `redis_lrange`, `redis_set`, `redis_hset`, `redis_del`, `redis_flushdb`, `redis_flushall`
  - `sequential_thinking` → `sequential_thinking`
  - `time_tools` → `time_current_time`, `time_convert_time`, `time_days_in_month`, `time_relative_time`, `time_get_timestamp`, `time_get_week_year`
- Does **not** import `filesystem`, `brave_search`, `docker_tool`, `exa_search`, `fetch`, `git_tool`, `github`, `shell_tool`, or `websearch`.
- Does **not** use `register_all_tools()` from `__init__.py` (which registers all 16 modules).
- Exposes `KEEP_TOOL_FAMILIES` as a public tuple for testing/documentation.
- Follows the same `sys.path` management pattern as `manager.py` to resolve the pip-installed `mcp` package.
- Entry-point: `python -m src.mcp.custom_manager` (stdio).

### 1.2 Option B — `_config` compatibility fix

Renamed `_config` → `config` in four function signatures in **`src/mcp/tools/filesystem.py`**:

| Function | Before | After |
|---|---|---|
| `fs_read` | `_config: FilesystemConfig = _DEFAULT_CONFIG` | `config: FilesystemConfig = _DEFAULT_CONFIG` |
| `fs_write` | `_config: FilesystemConfig = _DEFAULT_CONFIG` | `config: FilesystemConfig = _DEFAULT_CONFIG` |
| `fs_delete` | `_config: FilesystemConfig = _DEFAULT_CONFIG` | `config: FilesystemConfig = _DEFAULT_CONFIG` |
| `fs_list` | `_config: FilesystemConfig = _DEFAULT_CONFIG` | `config: FilesystemConfig = _DEFAULT_CONFIG` |

FastMCP v1 rejects parameters with underscore prefix (`_config`). This rename resolves the live registration blocker. No behavior change — the parameter name is internal.

### 1.3 Config alignment

`hermes-config/config.yaml` already points to `src.mcp.custom_manager` with `enabled: false`. No changes needed. The `tools.include` list matches KEEP-7 exactly.

## 2. Exposed KEEP-7 Tools

| Family | Tool Names | Auth Level |
|---|---|---|
| postgres | `postgres_query`, `postgres_tables`, `postgres_describe` | READ_AUTO + write blocking |
| redis | `redis_get`, `redis_keys`, `redis_hgetall`, `redis_lrange`, `redis_set`, `redis_hset`, `redis_del`, `redis_flushdb`, `redis_flushall` | Mixed (READ_AUTO–FORBIDDEN) |
| obscura_cdp | `obscura_navigate`, `obscura_get_markdown`, `obscura_fill_form`, `obscura_click` | READ_AUTO / WRITE_NOTIFY |
| grep_app | `grep_app_search` | READ_AUTO |
| context7 | `context7_resolve`, `context7_query` | READ_AUTO |
| sequential_thinking | `sequential_thinking` | READ_AUTO |
| time | `time_current_time`, `time_convert_time`, `time_days_in_month`, `time_relative_time`, `time_get_timestamp`, `time_get_week_year` | READ_AUTO |

**Total: 7 families, 25+ individual tool registrations.**

## 3. `sequential_thinking` Naming Proof

The registered MCP tool name in `src/mcp/tools/sequential_thinking.py` line 397:

```python
mcp.tool(name="sequential_thinking")(sequential_think)
```

Config `tools.include` also uses `sequential_thinking` (not `sequential_think`). Verified by test `test_registered_name_is_sequential_thinking`.

## 4. `_config` Fix Decision

**Both Option A and Option B were implemented** per planner BD-011:

- **Option A** (KEEP-7-only custom manager) is the primary solution — it avoids importing filesystem/native modules entirely, so the `_config` blocker in filesystem.py never affects the custom bridge.
- **Option B** (minimal `_config` rename) is a safety fix for any code path that might still register filesystem tools — it fixes the real FastMCP v1 compatibility bug at the source.

## 5. Commands Run

### 5.1 Test execution

```powershell
python -m pytest tests/hermes/test_fastmcp_bridge.py -v
```

**Result: 18 passed, 0 failed** (1 pre-existing `PytestDeprecationWarning`).

Test coverage:

| Test Class | Tests | Focus |
|---|---|---|
| `TestKeep7List` | 6 | KEEP-7 families, no all-16, native exclusion, importable, creates server |
| `TestConfigSignatureBlocker` | 2 | No `_config` params, no filesystem import in custom_manager |
| `TestSequentialThinkingNaming` | 2 | `sequential_thinking` name in code + config |
| `TestConfigModulePath` | 5 | Module exists, has main, config references, disabled, include list |
| `TestAizantaIsolation` | 3 | Blocked paths intact, no aizanta weakening, no filesystem import |

### 5.2 Compile check

```powershell
python -m compileall src/mcp/tools/filesystem.py src/mcp/custom_manager.py tests/hermes/test_fastmcp_bridge.py
```

**Result: All 3 files compiled cleanly** (exit 0).

### 5.3 Forbidden patterns scan

| Pattern | Result |
|---|---|
| `def .*\(_config` | **0 matches** (fix verified) |
| `# type: ignore` | **0 matches** in new/changed files |
| `\bAny\b` newly introduced | **0 matches** in P4-005 new/changed files after parent cleanup |
| Hardcoded secrets | **0 matches** |
| All 16 tools registered | **0 matches** (custom_manager uses KEEP-7 only) |

## 6. LSP Diagnostics

| File | Errors | Notes |
|---|---|---|
| `src/mcp/tools/filesystem.py` | 1 | `reportMissingImports` — `mcp.server.fastmcp` (pre-existing, same as manager.py); additional existing warnings in this file remain unrelated to the `_config` rename |
| `src/mcp/custom_manager.py` | 0 | Clean after parent cleanup |
| `tests/hermes/test_fastmcp_bridge.py` | 0 | Clean after parent cleanup |

No new LSP errors introduced by P4-005 parent-verified files. The remaining `filesystem.py` diagnostics are pre-existing dependency/typing warnings on existing tool registration code; the P4-005 change is limited to four parameter renames and grep verifies no `_config` parameters remain.

## 7. Hard Rejection Criteria Check

| Criterion | Status |
|---|---|
| FastMCP registration still fails | **PASS** — `_config` renamed + KEEP-7-only manager avoids filesystem imports |
| Filesystem/native tools exposed through custom bridge | **PASS** — custom_manager imports only KEEP-7 modules |
| Auth matrix completeness bypassed | **PASS** — no auth changes; auth_matrix.py is unchanged |
| Aizanta blocked paths weakened | **PASS** — `_BLOCKED_PATH_PREFIXES` intact, custom_manager does not import filesystem |

## 8. Files Changed

| File | Action | Description |
|---|---|---|
| `src/mcp/tools/filesystem.py` | **Modified** | Renamed `_config` → `config` in 4 function signatures |
| `src/mcp/custom_manager.py` | **Created** | KEEP-7-only FastMCP manager (185 lines after parent cleanup for strict typing) |
| `tests/hermes/test_fastmcp_bridge.py` | **Created** | 18 tests covering all scaffold requirements |
| `docs/setup-evidence/phase-4/P4-005-verification.md` | **Created** | This evidence document |
| `hermes-config/config.yaml` | **Unchanged** | Already points to `src.mcp.custom_manager`, already disabled |

## 9. Limitations

- **Disabled by default**: `fastmcp_custom.enabled: false` per BD-008/native exposure gate. P4-002 (auth overlay) must complete and a blocking proof test must pass before enabling.
- **No runtime proof**: Local compilation and test pass; live FastMCP stdio server not started in this step (requires approval-gated VPS deployment).
- **`mcp.server.fastmcp` import**: The sys.path dance to resolve the pip-installed `mcp` package causes a static analysis `reportMissingImports` warning. This is pre-existing (same as `manager.py`) and resolved at runtime.

## 10. Design Decisions

| Decision | Rationale |
|---|---|
| Create separate `custom_manager.py` instead of modifying `manager.py` | Avoids touching the full-registration path; keeps KEEP-7 bridge isolated and testable. |
| Make `KEEP_TOOL_FAMILIES` public | Enables test assertions and documentation without source regex hacks. |
| Keep `config.yaml` disabled | BD-008 requires auth overlay proof before enabling native-or-adjacent tool exposure. |
| Follow `manager.py` sys.path pattern | Proven pattern that resolves the `src/mcp` vs `mcp` pip package conflict. |
| Rename `_config` → `config` in addition to custom manager | Defensive fix: even if any future code path touches filesystem registration, the parameter name won't cause FastMCP rejection. |

## 11. Footer

```
Verification: P4-005 PASS
Next step: P4-002 (auth overlay) — completes Wave 2 after Wave 1 parent verification.
FastMCP bridge may be enabled (enabled: true) only after P4-002 proves pre_tool_call blocking.
```

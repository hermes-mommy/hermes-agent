# Independent Auditor Report — P4-001 (Config Baseline), P4-005 (FastMCP Bridge), P4-008 (E2E Suite)

| Field | Value |
|---|---|
| **Audit scope** | P4-001, P4-005, P4-008 (ADR-035 Phase 4) |
| **Auditor** | Independent (Guinevere — cross-check pass) |
| **Date** | 2026-06-05 |
| **Verdict** | **PASS** — all 9 checks pass, no findings |
| **Report path** | `docs/setup-evidence/phase-4/audit-config-fastmcp-e2e.md` |

---

## Files Reviewed

| File | Role |
|---|---|
| `hermes-config/config.yaml` | P4-001 — Hermes MCP config baseline |
| `src/mcp/custom_manager.py` | P4-005 — KEEP-7-only FastMCP bridge |
| `src/mcp/tools/filesystem.py` | P4-005 — `_config` → `config` rename target |
| `tests/hermes/test_mcp_config.py` | P4-001 — 25 config tests |
| `tests/hermes/test_fastmcp_bridge.py` | P4-005 — 18 FastMCP bridge tests |
| `tests/hermes/test_integration_e2e.py` | P4-008 — 59 E2E integration tests |
| `docs/setup-evidence/phase-4/P4-001-verification.md` | P4-001 verification report |
| `docs/setup-evidence/phase-4/P4-005-verification.md` | P4-005 verification report |
| `docs/setup-evidence/phase-4/P4-008-verification.md` | P4-008 verification report |

## Commands Run

```powershell
python -m pytest tests/hermes/test_mcp_config.py tests/hermes/test_fastmcp_bridge.py tests/hermes/test_integration_e2e.py -v --timeout=300
```

**Result: 102 passed, 0 failed, 1 warning** (pre-existing PytestDeprecationWarning).

Breakdown:

| Test Suite | Tests | Status |
|---|---|---|
| `test_mcp_config.py` (P4-001) | 25 | ✅ 25/25 PASS |
| `test_fastmcp_bridge.py` (P4-005) | 18 | ✅ 18/18 PASS |
| `test_integration_e2e.py` (P4-008) | 59 | ✅ 59/59 PASS |
| **Total** | **102** | **102/102 PASS** |

---

## Check 1: Config.yaml has documented Hermes mcp_servers shape (not old non-standard format)

**Verdict: ✅ PASS**

Config.yaml (lines 189–215) contains a single `mcp_servers` entry: `fastmcp_custom`. It follows the documented Hermes stdio MCP server shape:

| Field | Present | Type |
|---|---|---|
| `enabled` | ✅ | `bool` |
| `command` | ✅ | `str` |
| `args` | ✅ | `list[str]` |
| `cwd` | ✅ | `str` |
| `env_file` | ✅ | `str` |
| `timeout` | ✅ | `int` |
| `connect_timeout` | ✅ | `int` |
| `supports_parallel_tool_calls` | ✅ | `bool` |
| `tools.include` | ✅ | `list[str]` |
| `tools.resources` | ✅ | `bool` |
| `tools.prompts` | ✅ | `bool` |

No old non-standard keys (`root_path`, `allowed_paths`, `blocked_paths`, `allowed_commands`, `blocked_commands`, `allowed_operations`, `blocked_operations`, `max_response_size_mb`, `timeout_seconds`).

**Evidence:**
- Direct file read confirmed Hermes shape
- `test_mcp_config.py::TestMcpServersShape::test_no_old_native_section_keys` — PASS
- `test_mcp_config.py::TestMcpServersShape::test_stdio_server_shape` — PASS

---

## Check 2: No direct native production tool exposure (fastmcp_custom enabled: false)

**Verdict: ✅ PASS**

The only MCP server defined is `fastmcp_custom` with `enabled: false` (config.yaml line 195). No native production tools (filesystem, shell, terminal, git, web, fetch, docker, github) appear in any enabled server's `tools.include` because no server is enabled.

Additionally:
- The config header explicitly documents the "NATIVE EXPOSURE GATE (BD-008 / P4-001)" (line 169)
- All native tool entries removed from `mcp_servers` — they are built-in Hermes capabilities, not MCP servers

**Evidence:**
- Config.yaml lines 189–215: only server is disabled
- `test_mcp_config.py::TestNativeExposureGate::test_no_enabled_native_production_tools` — PASS
- `test_mcp_config.py::TestNativeExposureGate::test_default_disabled` — PASS
- `test_mcp_config.py::TestNativeExposureGate::test_exposure_gate_comment_present` — PASS
- P4-001 verification report §3 confirms gate status

**Limitation noted (unchanged from P4-001):** Native Hermes built-in toolsets remain available as platform built-ins. Auth overlay (P4-002) gates them at `pre_tool_call` level. This is properly documented.

---

## Check 3: fastmcp_custom include list matches KEEP-7 exactly (postgres, redis, obscura_cdp, grep_app, context7, sequential_thinking, time)

**Verdict: ✅ PASS**

**Config YAML** (lines 206–213):
```
postgres, redis, obscura_cdp, grep_app, context7, sequential_thinking, time
```

**custom_manager.py `KEEP_TOOL_FAMILIES`** (lines 93–101):
```python
("postgres", "redis", "obscura_cdp", "grep_app",
 "context7", "sequential_thinking", "time")
```

**Expected KEEP-7** (from `test_fastmcp_bridge.py` line 34):
```python
{"postgres", "redis", "obscura_cdp", "grep_app",
 "context7", "sequential_thinking", "time"}
```

All three sources match exactly. No extra entries, no missing entries.

**Evidence:**
- File read of config.yaml, custom_manager.py, test_fastmcp_bridge.py
- `test_fastmcp_bridge.py::TestConfigModulePath::test_config_include_list_matches_keep7` — PASS
- `test_fastmcp_bridge.py::TestKeep7List::test_keep_7_families_defined` — PASS
- `test_integration_e2e.py::TestConfigMcpServers::test_fastmcp_custom_include_list_is_keep7` — PASS

---

## Check 4: Canonical ports (5433/6380/20128) referenced; standard ports (5432/6379) blocked

**Verdict: ✅ PASS**

| Port | Service | Location in config.yaml | Status |
|---|---|---|---|
| 6380 | Redis | Line 183 comment | ✅ Referenced |
| 5433 | Postgres | Line 183 comment | ✅ Referenced |
| 20128 | 9Router | Lines 48, 54 (`base_url`) | ✅ Referenced |
| 5432 | Postgres (standard) | — | ❌ Not present (blocked) |
| 6379 | Redis (standard) | — | ❌ Not present (blocked) |

**Grep verification:**
- `redis://localhost:6379` in config.yaml → 0 matches ✅
- `localhost:5432` in config.yaml → 0 matches ✅

**Evidence:**
- `test_mcp_config.py::TestCanonicalPorts` — all 3 PASS
- `test_mcp_config.py::TestForbiddenPatterns::test_no_redis_6379_port` — PASS
- `test_mcp_config.py::TestForbiddenPatterns::test_no_postgres_5432_port` — PASS
- `test_integration_e2e.py::TestConfigMcpServers::test_canonical_ports_referenced` — PASS
- `test_integration_e2e.py::TestConfigMcpServers::test_no_forbidden_ports_in_config` — PASS

---

## Check 5: Auth matrix marked REFERENCE ONLY in YAML (Python authoritative)

**Verdict: ✅ PASS**

Config.yaml lines 281–288 contain an explicit warning header:

```yaml
# WARNING: This YAML auth_matrix is REFERENCE ONLY and does NOT drive runtime
# auth decisions. Python src/mcp/auth_matrix.py is the sole runtime auth
# source (BD-006). Any divergence between this reference and the Python source
# must be resolved by updating the Python source, NOT this YAML.
```

The `auth_matrix` section is present as documentation/reference only. Tests confirm:
- Python `src/mcp/auth_matrix.py` exists and defines `get_auth_level()`
- `get_auth_level("unknown_tool", "any_op")` raises `KeyError` (fail-closed)
- `get_auth_level("brave_search", "search")` returns `AuthLevel.READ_AUTO`

**Evidence:**
- `test_mcp_config.py::TestAuthSource::test_auth_matrix_is_reference_only` — PASS
- `test_mcp_config.py::TestAuthSource::test_python_auth_matrix_exists` — PASS
- `test_mcp_config.py::TestAuthSource::test_python_auth_matrix_raises_keyerror` — PASS
- `test_mcp_config.py::TestAuthSource::test_python_auth_matrix_known_tool_returns_level` — PASS
- P4-001 verification report §4 confirms

---

## Check 6: custom_manager.py registers exactly 7 KEEP modules (no native modules)

**Verdict: ✅ PASS**

`custom_manager.py` imports exactly 7 tool modules (lines 52–60):

| Module | Tools |
|---|---|
| `context7` | `context7_resolve`, `context7_query` |
| `grep_app` | `grep_app_search` |
| `obscura_cdp` | `obscura_navigate`, `obscura_get_markdown`, `obscura_fill_form`, `obscura_click` |
| `postgres_tool` | `postgres_query`, `postgres_tables`, `postgres_describe` |
| `redis_tool` | `redis_get`, `redis_keys`, `redis_hgetall`, `redis_lrange`, `redis_set`, `redis_hset`, `redis_del`, `redis_flushdb`, `redis_flushall` |
| `sequential_thinking` | `sequential_thinking` |
| `time_tools` | `time_current_time`, `time_convert_time`, `time_days_in_month`, `time_relative_time`, `time_get_timestamp`, `time_get_week_year` |

Does **not** import: `filesystem`, `brave_search`, `docker_tool`, `exa_search`, `fetch`, `git_tool`, `github`, `shell_tool`, `websearch`.

Does **not** call `register_all_tools()` (which would register all 16 modules).

**Evidence:**
- Direct file read of custom_manager.py
- `test_fastmcp_bridge.py::TestKeep7List::test_custom_manager_imports_only_keep_modules` — PASS
- `test_fastmcp_bridge.py::TestKeep7List::test_no_all_16_registration` — PASS (AST check confirms no `register_all_tools` or `_TOOL_MODULES` references)
- `test_fastmcp_bridge.py::TestKeep7List::test_all_16_includes_native_excluded_from_keep` — PASS
- `test_fastmcp_bridge.py::TestKeep7List::test_custom_manager_is_importable` — PASS

---

## Check 7: filesystem.py no longer has `_config` parameters

**Verdict: ✅ PASS**

All four filesystem tool functions use `config` (not `_config`) as the parameter name:

| Function | Parameter (after P4-005 rename) |
|---|---|
| `fs_read` (line 190) | `config: FilesystemConfig = _DEFAULT_CONFIG` |
| `fs_write` (line 200) | `config: FilesystemConfig = _DEFAULT_CONFIG` |
| `fs_delete` (line 213) | `config: FilesystemConfig = _DEFAULT_CONFIG` |
| `fs_list` (line 224) | `config: FilesystemConfig = _DEFAULT_CONFIG` |

**Grep verification:**
- `grep "_config" src/mcp/tools/filesystem.py` → **0 matches** ✅

Note: `_DEFAULT_CONFIG` exists as a module-level constant (used as default value), not as a parameter name. This is not subject to the FastMCP v1 underscore-prefix rejection.

**Evidence:**
- Direct file read of filesystem.py
- `test_fastmcp_bridge.py::TestConfigSignatureBlocker::test_no_underscore_config_params_in_filesystem` — PASS (AST check)
- P4-005 verification report §1.2 confirms the rename

---

## Check 8: E2E tests cover all 6 required categories

**Verdict: ✅ PASS**

All 6 required E2E categories are present in `test_integration_e2e.py`:

| # | Category | Test Class | Test Count | Coverage |
|---|---|---|---|---|
| a | Config → MCP servers | `TestConfigMcpServers` | 7 | YAML parsing, Hermes stdio shape, KEEP-7 include list, native exposure gate, canonical ports, forbidden ports |
| b | Auth matrix → enforcement | `TestAuthMatrixEnforcement` | 9 | 16 tools, all 4 AuthLevels, unknown tool/op fail-closed, wildcard correctness |
| c | Auth overlay → all 4 levels | `TestAuthOverlayLevels` | 7 | Tool name normalisation, prefix stripping, FORBIDDEN handler, payload redaction, approval TTL/Redis, pre_tool_call enforcement, unknown tool block |
| d | Budget hook → fail-closed | `TestBudgetHookFailClosed` | 9 | MONTHLY_CAP=30, WARN_THRESHOLD=24, DEFAULT_TOOL_COST>0, Redis 6380/DB5, Lua atomicity, client-side no-incrbyfloat, main exception handler |
| e | Hybrid guards → all types | `TestHybridGuardsIntegration` | 15 | Shell injection (blocked+safe), Docker read-only/destructive/forbidden, git force-push, Aizanta path/port isolation, composite routing |
| f | Startup gate → validation | `TestStartupGatePluginValidation` | 6 | validate_plugins exists, CRITICAL_PLUGINS, no critical flag, os.execvp not os.system, main returns exit code, importable |

**Plus cross-cutting:** `TestForbiddenPatterns` (4), `TestE2ECategoryCount` (2).

**Total: 59 tests** (exceeds scaffold minimum of 20).

**Evidence:**
- Direct file read of test_integration_e2e.py confirms all test classes present
- `test_integration_e2e.py::TestE2ECategoryCount::test_all_six_categories_present` — PASS
- `test_integration_e2e.py::TestE2ECategoryCount::test_test_count_meets_scaffold` — PASS
- P4-008 verification report §1 confirms category breakdown

---

## Check 9: No forbidden patterns in any of these files

**Verdict: ✅ PASS**

| Pattern | Scope | Result |
|---|---|---|
| `# type: ignore` | All files under audit | **0 matches** in P4-001/005/008 files (pre-existing in `auth.py`, `postgres_tool.py` — not in scope) |
| `as any` | Test files | **0 matches** |
| `Any` annotation (non-import) | `filesystem.py`, `custom_manager.py` | **0 matches** |
| `except:` (bare) | `src/mcp/` | **0 matches** |
| `time.sleep()` > 5s | E2E test file | **0 matches** |
| `@pytest.mark.skip` | Test files | **0 matches** |
| `os.system(` | `startup_gate.py` validation | **0 matches** (uses `os.execvp`) |
| `critical:\s*true` | `config.yaml` | **0 matches** (present only in `guinevere_safety/manifest.yaml`, not in scope) |
| Plaintext secrets | `config.yaml` | **0 matches** |

**Evidence:**
- Grep verification on all scoped files
- All forbidden pattern tests PASS:
  - `test_mcp_config.py::TestForbiddenPatterns` — all 4 PASS
  - `test_integration_e2e.py::TestForbiddenPatterns` — all 4 PASS
  - `test_fastmcp_bridge.py::TestConfigSignatureBlocker` — both PASS

---

## Verification Report Cross-Check

### Self-Consistency

| Report | Claimed | Actual | Match |
|---|---|---|---|
| P4-001 | 25/25 tests PASS | 25/25 PASS (in combined run) | ✅ |
| P4-005 | 18/18 tests PASS | 18/18 PASS (in combined run) | ✅ |
| P4-008 | 59/59 tests PASS | 59/59 PASS (in combined run) | ✅ |
| Combined | — | 102/102 PASS | ✅ |

### Cross-Report Consistency

- P4-001 states "FastMCP custom bridge is placeholder-only... P4-005 will create the actual bridge" — P4-005 then created `custom_manager.py` ✅
- P4-001 states `fastmcp_custom.enabled: false` — P4-005 confirms no change needed ✅
- P4-005 says `_config` renamed to `config` in filesystem.py — verified by file read and grep ✅
- P4-005 says custom_manager imports only KEEP-7 — verified by file read ✅
- P4-008 tests cover all claims from P4-001 and P4-005 ✅

### No Gaps Identified

All verification claims in P4-001, P4-005, and P4-008 are supported by:
1. Executable test evidence (102/102 PASS)
2. Direct file inspection
3. Grep-based forbidden pattern verification
4. Cross-reference consistency with other Phase 4 steps

---

## Verdict

| Component | Result |
|---|---|
| P4-001 — Config baseline | ✅ **PASS** |
| P4-005 — FastMCP bridge | ✅ **PASS** |
| P4-008 — E2E suite | ✅ **PASS** |
| **Overall** | **✅ PASS** |

**9 of 9 checks pass.** No findings, no regressions, no forbidden pattern violations.

The verification reports are accurate, the tests are deterministic and comprehensive, and the implementation faithfully follows ADR-035 Phase 4 requirements for config shape, KEEP-7 isolation, `_config` compatibility, auth source authority, port isolation, and E2E coverage.

---

## Footer

| Field | Value |
|---|---|
| Report path | `docs/setup-evidence/phase-4/audit-config-fastmcp-e2e.md` |
| Auditor | Independent (Guinevere — cross-check pass) |
| Date | 2026-06-05 |
| Verdict | **PASS** — all 9 checks pass, no findings |
| Next action | Proceed to Phase 4 completion report |

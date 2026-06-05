# Independent Technical Accuracy Audit — P4-006 (Startup Gate) & P4-007 (Security Audit)

| Field | Value |
|---|---|
| **Audit scope** | P4-006 startup gate + P4-007 security audit suite (ADR-035 Phase 4) |
| **Auditor** | Independent technical accuracy auditor (Guinevere) |
| **Date** | 2026-06-05 |
| **Report path** | `docs/setup-evidence/phase-4/audit-startup-audit.md` |
| **Verdict** | **PASS** — All checks verified, no material issues found |

---

## Files Reviewed

| File | Lines | Purpose |
|---|---|---|
| `scripts/startup_gate.py` | 352 | P4-006 Startup Gate — fail-closed validation of critical Hermes plugins |
| `scripts/startup_gate_test.py` | 362 | P4-006 test suite (34 tests) |
| `tests/hermes/test_security_audit.py` | 643 | P4-007 Security audit suite (108 tests) |
| `docs/setup-evidence/phase-4/P4-006-verification.md` | ~240 | P4-006 verification evidence |
| `docs/setup-evidence/phase-4/P4-007-verification.md` | ~280 | P4-007 verification evidence |

## Commands Run

| Command | Status |
|---|---|
| `python -m pytest scripts/startup_gate_test.py tests/hermes/test_security_audit.py -v --timeout=300` | **142 passed** in 3.85s (1 deprecation warning) |

## Grep Pattern Scans

| Pattern | Target | Matches | Verdict |
|---|---|---|---|
| `os.system(` | `startup_gate.py` | 0 | ✅ PASS |
| `print(` | `startup_gate.py` | 0 | ✅ PASS |
| `# type: ignore` | `startup_gate.py` | 0 | ✅ PASS |
| `# type: ignore` | `startup_gate_test.py` | 0 | ✅ PASS |
| `# type: ignore` | `test_security_audit.py` | 0 (1 in string literal self-check) | ✅ PASS |
| `\bAny\b` | `startup_gate.py` | 0 | ✅ PASS |
| `\bAny\b` | `startup_gate_test.py` | 0 | ✅ PASS |
| `except:` (bare) | `startup_gate.py` | 0 | ✅ PASS |
| `except:` (bare) | `startup_gate_test.py` | 0 | ✅ PASS |
| `except:` (bare) | `test_security_audit.py` | 0 (2 in string self-check assertions) | ✅ PASS |
| `critical:\s*true` | `startup_gate.py` | 0 | ✅ PASS |
| `subprocess` | `startup_gate.py` | 0 | ✅ PASS |
| `# type: ignore` in strings-after-strip | `test_security_audit.py` | 0 (self-check passes) | ✅ PASS |

---

## P4-006: Startup Gate — Independent Checks

### Check SG‑1: `validate_plugins` function exists and validates `auth_overlay` + `guinevere_safety`

**Finding:** ✅ PASS

- `validate_plugins()` is defined at line 310 of `startup_gate.py`.
- It iterates over `CRITICAL_PLUGINS`, which is a hardcoded list containing exactly two entries: `auth_overlay` and `guinevere_safety`.
- Each plugin is validated through `_validate_plugin()` which checks: directory existence → manifest validity → importability → register/handler contract.
- Verification evidence confirms this in P4-006-verification.md §2.

**Detail:** The `CRITICAL_PLUGINS` list at lines 37–49:
```python
CRITICAL_PLUGINS: list[dict[str, object]] = [
    {"name": "auth_overlay", "expected_manifest": "plugin.yaml", ...},
    {"name": "guinevere_safety", "expected_manifest": "manifest.yaml", ...},
]
```

---

### Check SG‑2: Does NOT rely on unsupported `critical:true` plugin YAML flag

**Finding:** ✅ PASS

- **Grep for `critical:\s*true` and `critical:\s*True` in `startup_gate.py`:** 0 matches.
- **Grep for `critical` in startup_gate.py:** Only `CRITICAL_PLUGINS` identifier matches — the constant name, not a YAML field.
- The startup gate never reads any `critical` field from plugin manifests. It hardcodes which plugins are critical in `CRITICAL_PLUGINS`.
- The code docstring explicitly states: *"Does not rely on unsupported Hermes mandatory-plugin manifest flags."*
- P4-006-verification.md §6 documents this with reference to research report `07-hermes-external-docs.md` §3.4 confirming Hermes has no `critical` field.
- P4-007 Check 15 test `test_startup_gate_no_critical_flag_reliance` scans for any `critical` reference outside `CRITICAL_PLUGINS` — passes.

---

### Check SG‑3: Uses `os.execvp` with list args (not `os.system` / shell)

**Finding:** ✅ PASS

- **Source inspection:** Line `os.execvp("hermes", ["hermes", "gateway", "run", "--accept-hooks"])` — list argument, no shell.
- **Grep for `os.system(`:** 0 matches.
- **Grep for `subprocess`:** 0 matches. No `subprocess.run`, `subprocess.Popen`, `shell=True`, or `check_output` anywhere.
- **Test `test_exec_called_with_list_args_on_success`:** Monkeypatches `os.execvp`, verifies it's called exactly once with `("hermes", ["hermes", "gateway", "run", "--accept-hooks"])`.
- **Test `test_no_shell_mediated_process_call`:** Asserts `os.system` not present.
- **Test `test_no_shell_boolean_argument`:** Asserts `shell=True` not present.

---

### Check SG‑4: Returns non-zero exit code on validation failure

**Finding:** ✅ PASS

- `validate_plugins()` returns `bool` — `False` on failure.
- `main()` returns `1` on failure (lines: `return 1` after validation failure).
- `main()` with `--validate-only` returns `0 if validate_plugins() else 1`.
- **Test `test_broken_auth_overlay_import_error_blocks`:** Asserts `validate_plugins() is False`. ✅
- **Test `test_main_validate_only_fails`:** Asserts `main(["--validate-only"]) == 1`. ✅
- **Test `test_exec_not_called_on_failure`:** Asserts `main([]) == 1` (implicitly via return value) and exec not called. ✅
- **Grep `return 0`**: Two instances:
  - Line `return 0 if validate_plugins() else 1` — ternary, returns 1 on failure. Correct.
  - Line `return 0  # pragma: no cover` — after `os.execvp` which doesn't return. Correct.
- **Test `test_no_return_zero_on_failure`:** Asserts no bare `return 0` exists without `os.execvp` preceding it within 3 lines. Passes.

**Minor observation:** The test `test_no_return_zero_on_failure` checks for lines matching exactly `return 0` (after strip). The `return 0  # pragma: no cover` line has a comment suffix, so its stripped form is `return 0  # pragma: no cover` which doesn't match the exact check. This is benign — the line is correctly placed after `os.execvp` and is unreachable. The test correctly catches any hypothetical bare `return 0` on a failure path because none exist.

---

### Check SG‑5: No `print()` calls (uses `stderr.write` instead)

**Finding:** ✅ PASS

- **Grep for `print(` in `startup_gate.py`:** 0 matches.
- All output goes through:
  - `sys.stderr.write(...)` — explicit stderr output (3 call sites).
  - `_log.error(...)` — logging configured with `stream=sys.stderr`.
- P4-006-verification.md §7 confirms parent cleanup replaced potential stdout prints with `sys.stderr.write`.

---

### Check SG‑6: Test simulates broken plugin and verifies exit code

**Finding:** ✅ PASS

The test suite covers 7 broken-plugin scenarios, all asserting `validate_plugins() is False`:

| Test | Broken Scenario | Assertion |
|---|---|---|
| `test_broken_auth_overlay_import_error_blocks` | `raise ImportError(...)` in auth_overlay | `is False` |
| `test_broken_auth_overlay_syntax_error_blocks` | Syntax error in auth_overlay `__init__.py` | `is False` |
| `test_broken_guinevere_safety_missing_dir_blocks` | guinevere_safety directory doesn't exist | `is False` |
| `test_broken_guinevere_safety_import_error_blocks` | `from .nonexistent import Thing` | `is False` |
| `test_both_broken_blocks` | Both plugins raise RuntimeError | `is False` |
| `test_missing_manifest_blocks` | Manifest file deleted | `is False` |
| `test_main_validate_only_fails` | Missing guinevere_safety, `main(["--validate-only"])` | `== 1` |

Additionally, `test_exec_not_called_on_failure` proves `os.execvp` is never reached on failure.

---

## P4-007: Security Audit — Independent Checks

### Check SA‑1: All 15 mandatory checks are tested (not hardcoded to 14)

**Finding:** ✅ PASS

- **Meta-test `TestAll15ChecksPresent::test_15_check_ids_documented`:** Contains a list of exactly 15 class names (TestCheck01 through TestCheck15). Asserts `len(classes) == 15` and each class exists in `globals()`.
- **Source inspection:** All 15 class definitions exist:
  1. `TestCheck01_PythonAuthMatrixIsAuthoritative`
  2. `TestCheck02_All16ToolsEnforcementCoverage`
  3. `TestCheck03_UnknownFailsClosed`
  4. `TestCheck04_ReadAutoAllows`
  5. `TestCheck05_WriteNotifyAllowsWithRedaction`
  6. `TestCheck06_DestructiveRequiresRedisApproval`
  7. `TestCheck07_ForbiddenBlocks`
  8. `TestCheck08_NativeAndMCPPrefixNormalization`
  9. `TestCheck09_BudgetHookFailClosed`
  10. `TestCheck10_BudgetLuaAtomic`
  11. `TestCheck11_ShellInjectionGuard`
  12. `TestCheck12_Docker5LayerGuard`
  13. `TestCheck13_GitForcePushGuard`
  14. `TestCheck14_AizantaIsolation`
  15. `TestCheck15_StartupGateFailClosed`
- **Test count:** 108 tests total (15 checks × ~4–15 tests each, plus 2 forbidden-pattern tests, plus 1 meta-test). No evidence of truncation.

---

### Check SA‑2: Tests are deterministic (no network/VPS/Redis/Postgres)

**Finding:** ✅ PASS

- All tests are local and deterministic:
  - **Auth matrix tests:** Call `get_auth_level()` directly on in-memory `AUTH_MATRIX`. No IO.
  - **File content tests:** Use `_read()` helper that reads files from local filesystem.
  - **Plugin tests:** Verify source content via string analysis (pattern matching, not runtime import).
  - **Hybrid guard tests:** Use `_import_hook()` which loads Python files via `importlib.util.spec_from_file_location` — no network.
  - **Budget tests:** Verify constants and source code patterns in local files.
  - **Docker/git/shell tests:** Import and call guard functions locally with string inputs.
  - **Aizanta isolation tests:** Call `check_aizanta_path` and `check_port_isolation` with string arguments.
- **No network calls:** No `requests`, `aiohttp`, `urllib`, `socket`, or HTTP clients.
- **No SSH/systemctl:** Zero references to `ssh`, `systemctl`, `vps`, `scp`, `rsync`.
- **No live Redis/Postgres:** No `redis.Redis()`, `psycopg`, `asyncpg`, or database connections.
- **No Docker daemon calls:** Docker guard tests call the guard function with string commands, not `docker` CLI.
- P4-007-verification.md §7 confirms all tests are read-only and idempotent.

---

### Check SA‑3: Forbidden self-checks exist and pass

**Finding:** ✅ PASS

- **Test class `TestForbiddenPatterns`** (2 tests) at bottom of `test_security_audit.py`:
  - `test_no_type_ignore_in_code` — Strips docstrings and string literals via regex, then asserts `# type: ignore` not present. ✅
  - `test_no_bare_except` — Iterates lines, asserts no bare `except:` outside string analysis. ✅
- Both tests passed in the pytest run.

**Minor observation:** The regex stripping (`r'"[^"]*"'` etc.) is a heuristic that might not strip all edge cases (e.g., f-strings with embedded quotes, escaped quotes). However, since the tests pass and a dedicated grep confirmed zero actual `# type: ignore` or bare `except:` in the file, the self-checks are accurate in this case.

---

### Check SA‑4: Each check is meaningful (not tautological)

**Finding:** ✅ PASS

Each check verifies an actual security property:

| Check | What It Verifies | Why It Matters |
|---|---|---|
| **01** | Python auth_matrix.py is authoritative (16 tools, no YAML import, matrix_completeness) | Ensures runtime auth source is Python, not stale YAML |
| **02** | All 16 tools have enforcement mapping | No tool can operate without auth coverage |
| **03** | Unknown tool/operation fails closed (KeyError, None, block constants) | Novel/misspelled tools don't bypass auth |
| **04** | READ_AUTO allows specific deterministic read tools | Read-only path works; listed tools explicitly verified |
| **05** | WRITE_NOTIFY allows while redacting secrets | Write path works; secret patterns defined |
| **06** | DESTRUCTIVE_APPROVAL uses Redis DB5 with 300s TTL | Destructive ops require explicit persisted approval |
| **07** | 10 FORBIDDEN operations hard-blocked | Most dangerous operations explicitly denied |
| **08** | Native/MCP names normalize; BD-008 gate enabled | Tool aliasing prevents name-based bypass |
| **09** | Budget hook: MONTHLY_CAP=30, WARN_THRESHOLD=24, port 6380, fail-closed | Budget enforcement matches spec |
| **10** | Budget Lua is atomic (redis.call, no client-side incrbyfloat) | Prevents race conditions in budget tracking |
| **11** | 7 injection patterns blocked, 5 safe commands allowed | Shell injection guard works bidirectionally |
| **12** | Docker read-only passes, destructive blocked, guinevere containers allowed | Docker 5-layer guard provides granular control |
| **13** | 7 force-push variants blocked, 8 safe ops allowed | Git force-push to protected branches blocked |
| **14** | Aizanta paths blocked, safe paths allowed, standard ports blocked, canonical ports allowed | Isolation boundaries enforced |
| **15** | Startup gate has validate_plugins, includes both plugins, no critical flag, uses os.execvp, returns exit code | Startup gate structure matches security requirements |

No test is tautological (e.g., asserting `True == True` or `"string" == "string"`). Every test makes a substantive claim about code behavior or structure.

---

### Check SA‑5: Test code has no type-ignore/Any/bare-except

**Finding:** ✅ PASS

| Pattern | File | Result |
|---|---|---|
| `# type: ignore` | `test_security_audit.py` | Only 1 occurrence in string literal `assert "# type: ignore" not in stripped` — self-check, not suppression. ✅ |
| `\bAny\b` | `test_security_audit.py` | 0 matches. Imports `from typing import cast` only. ✅ |
| `except:` (bare) | `test_security_audit.py` | 0 real occurrences. Two lines in `test_no_bare_except` are assertion strings that detect bare excepts — not actual bare except handlers. ✅ |
| `# type: ignore` | `startup_gate_test.py` | 0 matches. ✅ |
| `\bAny\b` | `startup_gate_test.py` | 0 matches. ✅ |
| `except:` (bare) | `startup_gate_test.py` | 0 matches. ✅ |
| `# type: ignore` | `startup_gate.py` | 0 matches. ✅ |
| `\bAny\b` | `startup_gate.py` | 0 matches. Uses `Optional` and `cast` — legitimate typing. ✅ |
| `except:` (bare) | `startup_gate.py` | 0 matches. All excepts are specific (`except Exception as exc:`, `except ImportError:`, etc.). ✅ |

---

## Cross-Verification: Verification Claims vs. Independent Findings

### P4-006-verification.md claims check

| Claim Made | Independent Finding | Status |
|---|---|---|
| "34 passed in 3.93s" | 34 startup_gate tests passed in our run | ✅ MATCH |
| "`validate_plugins()` returns False on failure" | Confirmed — all broken scenarios return `is False` | ✅ MATCH |
| "List-arg exec: `["hermes", "gateway", "run", "--accept-hooks"]`" | Confirmed — source code and test match | ✅ MATCH |
| "No shell-mediated process call" | Confirmed — grep for `os.system(` and `subprocess`: 0 | ✅ MATCH |
| "No `print()` calls" | Confirmed — grep for `print(`: 0 | ✅ MATCH |
| "No `critical: true` reliance" | Confirmed — code has zero YAML critical field reads | ✅ MATCH |
| "Zero type-suppression comments" | Confirmed — `# type: ignore` grep: 0 | ✅ MATCH |
| "Fail-closed for 12+ scenarios" | Confirmed — 12 distinct failure scenarios tested | ✅ MATCH |

### P4-007-verification.md claims check

| Claim Made | Independent Finding | Status |
|---|---|---|
| "108 tests passed" | 108 security_audit tests passed in our run | ✅ MATCH |
| "All 15 checks PASS" | Confirmed — each check has passing tests | ✅ MATCH |
| "No live VPS/network/systemctl/SSH" | Confirmed — all tests are local/deterministic | ✅ MATCH |
| "0 type-ignore violations" | Confirmed — only self-check string occurrence | ✅ MATCH |
| "0 bare except" | Confirmed — only in self-check assertions | ✅ MATCH |
| "15-check list documented" | Confirmed — `TestAll15ChecksPresent` validates 15 classes | ✅ MATCH |

---

## Additional Observations

1. **`return 0` presence is benign:** The only two `return 0` statements in `startup_gate.py` are either part of a ternary (`return 0 if validate_plugins() else 1`, which returns 1 on failure) or unreachable (`return 0  # pragma: no cover` after `os.execvp`). Neither represents a silent-success-on-failure path.

2. **Self-check regex robustness:** The `test_no_type_ignore_in_code` self-check in test_security_audit.py uses basic regex stripping (`r'"[^"]*"'` etc.) that may not handle all Python string edge cases (f-strings with braces, escaped quotes, etc.). However, since file-wide grep confirms zero actual violations, this is a non-issue for the current codebase.

3. **Test isolation:** The startup_gate_test.py uses `@pytest.fixture(autouse=True)` with `_reset_global_state` that restores `HERMES_PLUGIN_DIRS`, `CRITICAL_PLUGINS`, and cleans `sys.modules`. This ensures tests don't leak state. ✅

4. **No skipped tests:** Zero `@pytest.mark.skip` or `@pytest.mark.skipif` markers triggered in our run. (The `test_main_with_real_plugins_passes` has a `skipif` but the condition was False because the plugin directory exists.)

---

## Verdict

| Component | Verdict |
|---|---|
| **P4-006 (startup_gate.py + startup_gate_test.py)** | **PASS** — All 6 audit checks pass, 34/34 tests, all forbidden patterns clean, verification claims match independent findings |
| **P4-007 (test_security_audit.py)** | **PASS** — All 5 audit checks pass, 108/108 tests, all 15 mandatory checks substantive and deterministic, no type-safety violations |
| **Cross-verification** | **PASS** — All verification evidence claims independently confirmed |

**Overall: PASS** — No material issues, no safety boundary violations, no forbidden patterns, complete and deterministic test coverage.

---

## Evidence Artifacts

| Artifact | Path |
|---|---|
| This report | `docs/setup-evidence/phase-4/audit-startup-audit.md` |
| Startup gate source | `scripts/startup_gate.py` |
| Startup gate test | `scripts/startup_gate_test.py` |
| Security audit test | `tests/hermes/test_security_audit.py` |
| P4-006 verification | `docs/setup-evidence/phase-4/P4-006-verification.md` |
| P4-007 verification | `docs/setup-evidence/phase-4/P4-007-verification.md` |
| Pytest output | Inline in §Commands Run (142 passed) |

---

## Footer

| Field | Value |
|---|---|
| **Auditor** | Guinevere — independent technical accuracy auditor |
| **Date** | 2026-06-05 |
| **Evidence path** | `docs/setup-evidence/phase-4/audit-startup-audit.md` |
| **Scope** | P4-006 (startup gate) + P4-007 (security audit) |
| **Boundary note** | No files modified, no VPS/SSH/Redis/Postgres operations |
| **Next** | P4-008 E2E integration tests may proceed |

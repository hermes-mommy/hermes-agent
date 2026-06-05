# P4-006 Verification — Startup Gate

| Field | Value |
|---|---|
| **Step** | P4-006 — Startup Gate |
| **Status** | COMPLETE |
| **Date** | 2026-06-05 |
| **Evidence path** | `docs/setup-evidence/phase-4/P4-006-verification.md` |
| **Scaffold source** | `docs/setup-evidence/phase-4/planner-gate-phase-4-execution.md` §14 |

---

## 1. Files Changed

| File | Action | Purpose |
|---|---|---|
| `scripts/startup_gate.py` | **CREATE** | Fail-closed startup gate — validates critical plugins before Hermes starts |
| `scripts/startup_gate_test.py` | **CREATE** | 34 tests covering broken/missing/valid plugins, exec safety, forbidden patterns |
| `docs/setup-evidence/phase-4/P4-006-verification.md` | **CREATE** | This evidence file |

---

## 2. What Was Done

Created `scripts/startup_gate.py` which validates two critical Hermes plugins
(`auth_overlay` and `guinevere_safety`) before launching Hermes Gateway.

**Validation sequence per plugin:**

1. Plugin directory exists (searches `hermes-config/plugins/` and `~/.hermes/plugins/`)
2. Manifest file (`plugin.yaml` or `manifest.yaml`) exists and is parseable YAML
3. `__init__.py` exists and is importable (adds plugin parent dir to ``sys.path`` so
   relative imports like ``from .submodule import X`` resolve correctly)
4. Contract verification:
   - For `auth_overlay` (``expects_register: true``): checks that ``register(ctx)``
     exists, is callable, is invoked with a mock ``PluginContext``, and registers
     at least one hook
   - For `guinevere_safety` (``expects_register: false``): finds the main plugin
     class (``GuinevereSafetyPlugin``) and verifies that manifest-declared handlers
     (``inject_dynamic_state``, ``update_state``) exist as callable methods

**On success:** calls ``os.execvp("hermes", ["hermes", "gateway", "run", "--accept-hooks"])``
— list-argument exec, no shell.

**On failure:** writes errors to stderr, returns exit code 1, never reaches exec.

---

## 3. Validation Results

### 3.1 Test Suite

```
python -m pytest scripts/startup_gate_test.py -v
→ 34 passed in 3.93s (parent rerun; 1 pytest-asyncio deprecation warning)
```

| Test Class | Tests | Purpose |
|---|---|---|
| `TestBrokenPlugins` | 5 | Broken import, syntax error, missing dir, import error, both broken |
| `TestValidPlugins` | 2 | Both valid pass, real project plugins pass |
| `TestStructuralFailures` | 6 | Missing manifest, invalid YAML, missing register, no-op register, missing `__init__.py`, manifest-not-mapping |
| `TestMainFunction` | 4 | `--validate-only` pass/fail, exec not called on failure, exec called with list args on success, real plugins exec |
| `TestHelperFunctions` | 6 | `_find_plugin_dir` found/not-found, `_find_plugin_class` found/not-found, manifest empty/valid/invalid |
| `TestForbiddenPatterns` | 5 | No shell-mediated process call, no shell boolean argument, no `return 0` on failure, no type-suppression comments, no broad top-type escape |
| `TestEdgeCases` | 5 | Register raises exception, missing handlers, scalar manifest, multiple plugin directories |

### 3.2 Compile Check

```
python -m compileall hermes-config/hooks scripts/startup_gate.py
→ exit 0 (parent rerun; no errors)
```

---

## 4. Fail-Closed Proof

The following failure modes all result in exit code 1 (Hermes will NOT start):

| Scenario | Test | Mechanism |
|---|---|---|
| Broken `auth_overlay` import (syntax error) | `test_broken_auth_overlay_syntax_error_blocks` | Import raises exception → caught → `validate_plugins()` returns `False` |
| Broken `auth_overlay` import (ImportError) | `test_broken_auth_overlay_import_error_blocks` | Same as above |
| Missing `guinevere_safety` directory | `test_broken_guinevere_safety_missing_dir_blocks` | Directory not found → `_find_plugin_dir` returns `None` |
| Broken `guinevere_safety` import | `test_broken_guinevere_safety_import_error_blocks` | Import raises exception → caught |
| Missing manifest file | `test_missing_manifest_blocks` | `is_file()` returns `False` → error appended |
| Invalid YAML in manifest | `test_invalid_yaml_manifest_blocks` | `yaml.safe_load` raises `YAMLError` → caught |
| Missing `register()` function | `test_missing_register_blocks` | `getattr(mod, "register", None)` is not callable |
| No-op `register(ctx)` | `test_register_does_not_register_hooks_blocks` | Mock context has zero registered hooks |
| Missing `__init__.py` | `test_missing_init_py_blocks` | `is_file()` returns `False` |
| `register()` raises exception | `test_register_function_raises_exception_blocks` | Caught by `_verify_register_hooks` |
| Missing manifest-declared handler | `test_guinevere_safety_missing_handlers_blocks` | Handler not found on class → error appended |
| Both plugins broken simultaneously | `test_both_broken_blocks` | Each plugin validated independently, all errors collected |

**Proof that exec is not called on failure:**
```
test_exec_not_called_on_failure → PASSED
```
Monkeypatches `os.execvp` with a recording stub and verifies it is never called
when validation fails.

---

## 5. Valid Path — List-Arg Exec Proof

```
test_exec_called_with_list_args_on_success → PASSED
```

Monkeypatches `os.execvp` and verifies that on valid plugin configuration:
- `execvp` is called exactly once
- First argument is `"hermes"`
- Arguments are `["hermes", "gateway", "run", "--accept-hooks"]` (list, not string)
- No shell-mediated process calls, no shell boolean subprocess argument, no `subprocess` usage
  (confirmed by forbidden-pattern tests)

---

## 6. Unsupported `critical:true` Caveat

The existing `guinevere_safety/manifest.yaml` contains `critical: true`, but research
report `07-hermes-external-docs.md` §3.4 confirms:

> **The Hermes `PluginManifest` dataclass does NOT have a `critical` field.**
> The field is silently ignored by Hermes' plugin loader.

P4-006 does NOT rely on this field. The startup gate:

1. Validates plugins through **explicit Python code** (directory check, manifest
   check, import check, contract verification) — not through config flags.
2. Does **not** read or depend on any `critical:` field in any manifest.
3. The `CRITICAL_PLUGINS` list in `scripts/startup_gate.py` is hardcoded — it
   specifies which plugins are critical, not a config-driven approach.

**Mitigation decision (per Oracle Risk Review #09 and BD-002/BD-004):**
External startup gate is the only reliable approach for fail-closed plugin
enforcement in Hermes v0.15.x.

---

## 7. Forbidden Pattern Scan

| Pattern | Status | Notes |
|---|---|---|
| Shell-mediated process call | ✅ Not present | Verified by `test_no_shell_mediated_process_call`; parent grep also returned zero matches |
| Shell boolean subprocess argument | ✅ Not present | Verified by `test_no_shell_boolean_argument`; parent grep also returned zero matches |
| `return 0` on failure | ✅ Not present | Verified by `test_no_return_zero_on_failure` |
| Type-suppression comment | ✅ Not present | Verified by `test_no_type_suppression_comment`; parent grep also returned zero matches |
| Broad top-type escape | ✅ Not present | Verified by `test_no_broad_top_type_escape`; parent grep also returned zero matches |
| `print(` | ✅ Not present | Parent cleanup replaced stdout/stderr prints with `sys.stderr.write(...)`; parent grep returned zero matches |

---

## 8. Approval Boundary

No live restart, VPS deploy, systemd edit, or production service mutation was
performed for this step. The startup gate is designed to be integrated into the
Hermes startup path (systemd `ExecStart`) but that change requires explicit
per-action approval before deployment.

---

## 9. Edge Case Coverage

| Edge Case | Covered | Test |
|---|---|---|
| Plugin found in second search dir | ✅ | `test_plugin_directory_in_multiple_locations` |
| Scalar (non-dict) manifest | ✅ | `test_manifest_is_not_a_mapping_not_list` |
| List (non-dict) manifest | ✅ | `test_manifest_is_not_a_mapping_blocks` |
| Empty manifest | ✅ | `test_validate_manifest_empty` |
| Register raises exception | ✅ | `test_register_function_raises_exception_blocks` |
| Handler method missing on class | ✅ | `test_guinevere_safety_missing_handlers_blocks` |
| PyYAML not installed | ✅ | Graceful fallback in `_validate_manifest` |
| `--validate-only` flag | ✅ | `test_main_validate_only_passes`, `test_main_validate_only_fails` |

---

## 10. Caveats

1. **No live deployment.** The startup gate is created and tested locally.
   Systemd integration (`ExecStart` modification) requires per-action approval.
2. **Real plugin import requires project context.** The `test_real_plugins_validate`
   integration test imports actual project plugins (`auth_overlay`, `guinevere_safety`)
   which depend on `structlog`, `src.mcp.auth`, `src.mcp.auth_matrix`, etc.
   These are available in the project environment.
3. **No Hermes runtime test.** The gate validates plugins before Hermes starts;
   it does not test Hermes' own plugin loading behavior. That gap is covered by
   P4-007 (security audit) and P4-008 (E2E tests).
4. **Plugin validation is Python-level only.** The gate validates plugin directories,
   manifests, imports, and contracts. It does not validate Hermes-specific plugin
   initialization order or hook execution priority — those are Hermes runtime concerns.

---

## 11. Compliance Mapping

| Requirement | Status | Evidence |
|---|---|---|
| Broken auth_overlay blocks startup | ✅ PASS | `test_broken_auth_overlay_import_error_blocks` |
| Broken guinevere_safety blocks startup | ✅ PASS | `test_broken_guinevere_safety_missing_dir_blocks` |
| Valid config uses list-arg exec | ✅ PASS | `test_exec_called_with_list_args_on_success` |
| Unsupported `critical:true` not relied upon | ✅ PASS | §6 of this file; code has zero `critical:` references |
| No shell-mediated process call / shell boolean subprocess argument | ✅ PASS | Forbidden pattern tests + parent grep |
| No type-suppression comments / broad top-type escape | ✅ PASS | Forbidden pattern tests + parent grep |
| No silent continuation on failure | ✅ PASS | All failure tests verify `validate_plugins() is False` |
| Compile check passes | ✅ PASS | `compileall hermes-config/hooks scripts/startup_gate.py` → exit 0 |
| Evidence file complete | ✅ PASS | This file |

---

## 12. Footer

| Field | Value |
|---|---|
| **Verifier** | Guinevere |
| **Evidence path** | `docs/setup-evidence/phase-4/P4-006-verification.md` |
| **Boundary note** | No live system restart, deployment, or VPS mutation performed |
| **Rollback** | Delete `scripts/startup_gate.py`, `scripts/startup_gate_test.py` |

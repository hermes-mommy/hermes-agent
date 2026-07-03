# Task 2 Review: VPS Backend -- 15 SSH-based Actions

**Commit:** `63f4ecc`
**Files:** `guinvere/tools/backends/vps.py` (695 lines), `tests/p24/test_vps_backend.py` (1016 lines)
**Reviewed:** 2026-07-03 (re-reviewed with live test/mypy execution)

Note: The plan spec file and diff file do not exist on disk or in git history.
Review criteria taken from the task instructions and commit message.

---

## Verdict: PASS

All 9 checklist items pass. 56/56 tests green. mypy clean on the 15 standalone functions.

---

## Checklist

### 1. All 15 actions -- PASS

All 15 standalone async functions present (lines 33-404):

| # | Function | Line | Pattern |
|---|----------|------|---------|
| 1 | `ssh_exec` | 33 | Direct `create_subprocess_exec("ssh", ...)` |
| 2 | `scp_upload` | 70 | Direct `create_subprocess_exec("scp", ...)` |
| 3 | `scp_download` | 111 | Direct `create_subprocess_exec("scp", ...)` |
| 4 | `systemctl_status` | 152 | Delegates to `ssh_exec` |
| 5 | `systemctl_start` | 171 | Delegates to `ssh_exec` |
| 6 | `systemctl_stop` | 190 | Delegates to `ssh_exec` |
| 7 | `systemctl_restart` | 209 | Delegates to `ssh_exec` |
| 8 | `journalctl` | 228 | Delegates to `ssh_exec`, parses entries |
| 9 | `df` | 259 | Delegates to `ssh_exec` |
| 10 | `du` | 278 | Delegates to `ssh_exec` |
| 11 | `free` | 298 | Delegates to `ssh_exec` |
| 12 | `uptime` | 315 | Delegates to `ssh_exec` |
| 13 | `ps` | 332 | Delegates to `ssh_exec` |
| 14 | `kill` | 349 | Delegates to `ssh_exec` |
| 15 | `tail_log` | 371 | Delegates to `ssh_exec` |

### 2. Uses asyncio.create_subprocess_exec (not subprocess.run) -- PASS

Three direct subprocess calls, all `create_subprocess_exec`:
- Line 47: `asyncio.create_subprocess_exec("ssh", host, command, ...)`
- Line 86: `asyncio.create_subprocess_exec("scp", local, f"{host}:{remote}", ...)`
- Line 127: `asyncio.create_subprocess_exec("scp", f"{host}:{remote}", local, ...)`

The other 12 functions delegate to `ssh_exec`. Zero `subprocess.run` in standalone section.

**NOTE:** The legacy `VPSBackend.dispatch()` (line 464+) uses `create_subprocess_shell`
in 13 places. This is pre-existing code, not part of the 15-action deliverable.

### 3. Type annotations on all functions -- PASS

AST-verified: all 15 standalone functions have complete annotations:
- Return type: `-> dict[str, Any]` on all 15
- All parameters annotated (host: str, timeout: int, service: str, pid: int, etc.)
- Zero missing annotations detected

### 4. No `# type: ignore` -- PASS

`grep "type: ignore"` returns zero matches across both files.

### 5. Error handling: TimeoutError, FileNotFoundError, OSError -- PASS

The base `ssh_exec` catches all three (lines 59-67):
```python
except asyncio.TimeoutError:
    return {"ok": False, "action": "ssh_exec", "error": "command timed out"}
except FileNotFoundError as exc:
    return {"ok": False, "action": "ssh_exec", "error": f"binary not found: {exc}"}
except OSError as exc:
    return {"ok": False, "action": "ssh_exec", "error": f"os error: {exc}"}
```
`scp_upload` and `scp_download` duplicate this same handling (they use `scp`, not `ssh`).
All 12 delegating functions inherit error handling through `ssh_exec`.

### 6. Returns `{"ok": bool, "action": str, ...}` -- PASS

Every return path (38 return statements in standalone section) includes both `"ok"` (bool)
and `"action"` (str). Error returns include `"error"` key. Success returns include
action-specific fields (stdout, stderr, returncode, service, pid, entries, path, lines).

### 7. Default host "guinevere-vps", default timeout 30s -- PASS

- `_DEFAULT_HOST = "guinevere-vps"` (line 28)
- 14 of 15 functions default `host` to `_DEFAULT_HOST` (`ssh_exec` takes host as required positional arg)
- All 15 functions default `timeout: int = 30`

### 8. Tests use AsyncMock -- PASS

- `_make_proc()` returns `AsyncMock()` with `communicate = AsyncMock(return_value=(stdout, stderr))`
- `_make_timeout_proc()` returns `AsyncMock()` with slow coroutine side_effect
- All 54 async tests use `@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")`
- Imports: `from unittest.mock import AsyncMock, MagicMock, patch`

### 9. At least 3 tests per action -- PASS

| Action | Tests | Scenarios |
|--------|-------|-----------|
| ssh_exec | 5 | success, failure, timeout, custom_timeout, stderr_only |
| scp_upload | 4 | success, failure, timeout, custom_host |
| scp_download | 3 | success, failure, timeout |
| systemctl_status | 4 | active, inactive, timeout, custom_host |
| systemctl_start | 3 | success, failure, timeout |
| systemctl_stop | 3 | success, failure, timeout |
| systemctl_restart | 3 | success, failure, timeout |
| journalctl | 5 | success, empty_logs, failure, timeout, custom_lines |
| df | 4 | success, failure, timeout, custom_path |
| du | 3 | success, failure, timeout |
| free | 3 | success, failure, timeout |
| uptime | 3 | success, failure, timeout |
| ps | 3 | success, failure, timeout |
| kill | 4 | success, failure, timeout, custom_signal |
| tail_log | 4 | success, failure, timeout, custom_lines |

**Total: 54 action tests + 2 meta tests = 56 tests.**

---

## Live Test Results

### pytest
```
56 passed, 502 warnings in 16.96s
```
All warnings are pytest-asyncio deprecation (Python 3.14 event loop policy), not from test code.

### mypy (vps.py only)
13 errors, ALL in the legacy `VPSBackend` class (lines 456+):

| Line | Error | Location |
|------|-------|----------|
| 456 | `_validate_identifiers` missing type annotation | VPSBackend class |
| 493/506/526/588/602/615/676 | Call to untyped `_validate_identifiers` | VPSBackend.dispatch |
| 543 | `_run_sync` nested function missing annotation | VPSBackend.dispatch (health_metrics) |
| 551/552/558/564 | Call to untyped `_run_sync` | VPSBackend.dispatch (health_metrics) |

**The 15 standalone functions (lines 33-404) have ZERO mypy errors.**

---

## Non-blocking Notes

1. **Legacy class uses `create_subprocess_shell`:** The `VPSBackend.dispatch` method (line 464+) uses `create_subprocess_shell` for 13 calls. Pre-existing code, not the Task 2 deliverable. The class has a dangerous-command denylist and input validation, but `create_subprocess_shell` is inherently riskier than `create_subprocess_exec`.

2. **`df` shadows Python builtin:** The function name `df` (line 259) shadows the builtin. Low risk since it's a module-level function, not a variable.

3. **Import path cross-package:** The file imports `from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend` (with 'e') but lives in `guinvere` (without 'e'). Works because both packages are on PYTHONPATH. Only affects the legacy VPSBackend class; the 15 standalone functions have no external imports.

4. **No tests for FileNotFoundError/OSError paths:** Tests cover timeout and non-zero exit but not the `FileNotFoundError`/`OSError` exception branches. Minor -- these only trigger if `ssh`/`scp` binaries are missing.

5. **Duplicate error handling in scp_upload/scp_download:** These two functions replicate the `try/except` pattern from `ssh_exec` instead of delegating. Correct (they use `scp`), but a `_run_subprocess` helper could reduce duplication.

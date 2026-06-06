# Step 4 — Budget Hook Fail-Closed Reason Update

**Date:** 2026-06-06  
**Step:** 4  
**Evidence root:** `docs/setup-evidence/phase-6/STEP-4/`  

## What Was Done

Updated `hermes-config/hooks/budget_check.py` to add the `budget_check_failed` marker string to both fail-closed reason paths, satisfying the Phase 6 requirement that cost-check failure reasons contain `budget_check_failed` for upstream identification.

Strengthened `tests/hermes/test_budget_hook.py` to explicitly assert `budget_check_failed` is present in the fail-closed reason output for both Redis-unavailable and Lua/Redis-error paths (3 test methods updated).

### Changes Made

**File:** `hermes-config/hooks/budget_check.py`

1. **Line 181** — Redis unavailable path:
   - Before: `"reason": "Budget check unavailable (Redis down)"`
   - After: `"reason": "Budget check unavailable (Redis down) — budget_check_failed"`

2. **Line 206** — Lua/Redis error handler path:
   - Before: `"reason": "Budget check error"`
   - After: `"reason": "Budget check error — budget_check_failed"`

No other files were modified. The existing Lua-atomic monthly/per-tool/global daily budget behavior, stdout JSON contract (`action`, `reason`, `warning` fields), fail-closed semantics, monthly cap $30, warning $24, daily caps, and consent/DNR hooks remain untouched.

### Design Decisions

- Appended `— budget_check_failed` to existing reason strings rather than replacing them, preserving backward compatibility with downstream consumers that match on `"Redis down"` or `"error"`.
- The existing broad `except Exception` handler (line 201) remains unchanged and still triggers `sys.exit(1)` for any Redis/Lua/parse failure, preserving fail-closed safety.

## Files Changed

| File | Status |
|---|---|
| `hermes-config/hooks/budget_check.py` | Modified (2 lines) |
| `tests/hermes/test_budget_hook.py` | Modified (3 lines added — stronger assertions in `test_redis_connection_fail_closed`, `test_redis_unavailable_blocks`, `test_lua_execution_error_blocks`) |

## Validation Results

### Python compilation

```text
> python -m py_compile hermes-config/hooks/budget_check.py
EXIT CODE: 0
```

### Pytest (47/47 passed)

```text
> python -m pytest tests/hermes/test_budget_hook.py -v
[...]
tests/hermes/test_budget_hook.py::TestBudgetCheckMain::test_redis_unavailable_blocks PASSED
tests/hermes/test_budget_hook.py::TestBudgetCheckMain::test_lua_execution_error_blocks PASSED
[...]
=================== 47 passed in 0.42s ====================
```

Both fail-closed specific tests (`test_redis_unavailable_blocks`, `test_redis_connection_fail_closed`, `test_lua_execution_error_blocks`) continue to pass and now additionally assert `"budget_check_failed"` in the reason string.

### Forbidden Pattern Scan

Scanned `budget_check.py` and `tests/hermes/test_budget_hook.py` for forbidden patterns — **no matches**:
- `except Exception: pass` — not found
- `except : pass` — not found
- `# type: ignore` — not found
- `@ts-ignore`, `@ts-expect-error`, `as any` — not found
- `pytest.skip`, `@pytest.mark.xfail` — not found

## Evidence Artifacts

- `docs/setup-evidence/phase-6/STEP-4/implementation-report.md` (this file)
- Implementation diff: two reason-string changes only

## Doc-Sync Impact

None. No docs or config files were modified.

## Boundary Compliance

- ✅ Fail-closed preserved (both paths still block with `action: "block"` and `sys.exit(1)`)
- ✅ No fail-open path introduced
- ✅ `budget_check_failed` marker present in both cost-check failure paths
- ✅ Monthly cap $30, warning $24 unchanged
- ✅ Lua atomicity preserved
- ✅ Daily caps preserved
- ✅ Consent/DNR hooks untouched
- ✅ No secrets exposed

## Rollback / Re-run Safety

Rollback: `git checkout -- hermes-config/hooks/budget_check.py`  
Re-run: fully idempotent — same hook file, new reason strings only.

## Caveats

- The `budget_check_failed` marker is appended to the existing reason string rather than replacing it, so any consumer doing exact string match on the old reason will need to update. Substring matching (e.g., `"Redis down" in reason`) remains compatible.
- The broad `except Exception` handler at line 201 was not narrowed; it remains necessary to catch all Redis/Lua error types and preserve fail-closed safety per the existing design.

# F-01 Fix: Update Stale Auth Matrix Tests

**Date:** 2026-06-09  
**File modified:** `tests/mcp/test_auth_matrix.py`  
**Root cause:** `src/mcp/auth_matrix.py` was intentionally fully unlocked (all 16 tools → `"*": AuthLevel.READ_AUTO`) per Faiz's explicit consent. The test file still asserted granular per-operation levels (`FORBIDDEN`, `DESTRUCTIVE_APPROVAL`, `WRITE_NOTIFY`), causing 46 test failures.

---

## What Was Stale

| Old test | Operations asserted | Count | New state |
|---|---|---|---|
| `test_get_auth_level_write_notify` | `filesystem::write`, `github::create_issue`, `docker::start`, etc. | 26 | Now `READ_AUTO` |
| `test_get_auth_level_destructive_approval` | `filesystem::delete`, `git::force_push`, `redis::del`, etc. | 6 | Now `READ_AUTO` |
| `test_get_auth_level_forbidden` | `postgres::drop`, `redis::flushdb`, `shell::rm_rf_root`, etc. | 13 | Now `READ_AUTO` |
| `test_get_auth_level_unknown_operation_raises_key_error` | Expected `KeyError` on unknown op for non-wildcard tool | 1 | Removed (all tools are now wildcard, no per-op lookup) |

**Total stale: 46 test cases removed/updated.**

---

## Changes Made

### `_SAMPLE_WRITE_NOTIFY`, `_SAMPLE_DESTRUCTIVE`, `_SAMPLE_FORBIDDEN` — removed

These three constant lists were deleted entirely. All those operation/tool pairs now resolve to `READ_AUTO` via the `"*"` wildcard.

### `_SAMPLE_READ_AUTO` — expanded

All previously-stale operations folded into `_SAMPLE_READ_AUTO` so coverage is preserved and the operations are still exercised — just asserting the correct level (`READ_AUTO`).

### Tests removed/replaced

| Removed test | Reason |
|---|---|
| `test_get_auth_level_write_notify` | Level no longer exists per-operation |
| `test_get_auth_level_destructive_approval` | Level no longer exists per-operation |
| `test_get_auth_level_forbidden` | Level no longer exists per-operation |
| `test_get_auth_level_unknown_operation_raises_key_error` | All tools use `"*"` wildcard; unknown ops no longer raise |

### Tests added

| New test | What it checks |
|---|---|
| `test_wildcard_tools_return_read_auto_for_any_operation` | All 16 tools return `READ_AUTO` for arbitrary operation strings |
| `test_every_tool_uses_wildcard_entry` | Every tool has `"*": READ_AUTO` in its ops dict |

### Tests retained (unchanged)

- `test_matrix_has_all_16_tools`
- `test_verify_matrix_completeness_returns_true`
- `test_auth_level_enum_has_exactly_4_values`
- `test_get_auth_level_read_auto` (parametrized, now covers all 84 sample ops)
- `test_get_auth_level_unknown_tool_raises_key_error`
- `test_forbidden_raises_immediately` (decorator behaviour, level passed directly)
- `test_read_auto_executes_without_webhook`
- `test_write_notify_executes_and_fires_webhook`
- `test_write_notify_webhook_url_from_env`
- `test_destructive_approval_denied_raises`
- `test_destructive_approval_approved_executes`
- `test_destructive_approval_blocks_until_approval`
- `test_every_tool_has_at_least_one_operation`

---

## Verification

```
$ .venv/bin/python3 -m pytest tests/mcp/test_auth_matrix.py -q --tb=no 2>&1 | tail -5

94 passed, 5 warnings in 3.91s
```

**Result: 94 passed, 0 failures.** ✓

Warnings are pre-existing `RuntimeWarning: coroutine ... was never awaited` from `AsyncMock.raise_for_status` in the auth module — not introduced by this fix.

# P19-007 Mock Adjudication — Round 2

**Date:** 2026-06-26
**Test file:** `tests/projects/test_project_switcher.py`
**Production files examined:** `src/discord/cmd_project.py`, `src/discord/project_session.py`, `src/discord/_auth_guard.py`, `src/discord/_embed_utils.py`, `src/projects/registry.py`
**Verdict:** ALL_RESOLVED (8/8 passing)

---

## Failure 1: `test_switch_writes_audit_row`

| Field | Detail |
|---|---|
| **Error** | `AssertionError: Expected _write_audit_event to have been awaited once. Awaited 0 times.` |
| **Classification** | test-mock-flaw |
| **Root cause** | The mock interaction lacked `guild.owner_id` as an `int`. `is_faiz_interaction()` (`_auth_guard.py:22`) checks `isinstance(owner_id, int)` which returned `False` for auto-created `MagicMock`. The callback returned early via `send_denied` before reaching `_write_audit_event` at `cmd_project.py:219`. Additionally, `defer_ephemeral` (`_embed_utils.py:251`) was not mocked and would fail on `await MagicMock()` after auth passes. |
| **Fix applied** | Added `patch("src.discord._auth_guard.is_faiz_interaction", return_value=True)` and `patch.object(cmd_project, "defer_ephemeral", new_callable=AsyncMock)` to the test context manager (test line 52-53). No production code changes. |
| **Production impact** | None. Auth guard logic (`_auth_guard.py:11-22`) is correct; the mock interaction was the defect. |

## Failure 2: `test_list_returns_projects`

| Field | Detail |
|---|---|
| **Error** | `AssertionError: Expected followup_send to have been awaited once. Awaited 0 times.` |
| **Classification** | test-mock-flaw |
| **Root cause** | Same auth guard issue as Failure 1. Additionally, the test mocked `registry.list_active` but the production code at `cmd_project.py:318` calls `registry.list()`. The `list()` call hit the auto-created AsyncMock (returning MagicMock) instead of the configured return value, and the callback returned early before `followup_send`. |
| **Fix applied** | (1) Added `is_faiz_interaction` and `defer_ephemeral` mocks (test line 132-133). (2) Changed `mock_registry.list_active` to `mock_registry.list` (test line 148) to match `ProjectRegistry.list()` at `registry.py:308`. |
| **Production impact** | None. Both the auth guard and `registry.list()` API are correct. |

## Failure 3: `test_list_callback_calls_registry`

| Field | Detail |
|---|---|
| **Error** | `AssertionError: Expected list_active to have been awaited once. Awaited 0 times.` |
| **Classification** | test-mock-flaw |
| **Root cause** | Two issues: (1) same auth guard mock gap as Failures 1-2; (2) test asserted `mock_registry.list_active.assert_awaited_once()` but production code calls `registry.list()` (`cmd_project.py:318`), not `registry.list_active()` (`registry.py:313`). The mock method name did not match the real API. |
| **Fix applied** | (1) Added `is_faiz_interaction` and `defer_ephemeral` mocks (test line 163-164). (2) Changed mock setup from `list_active` to `list` (test line 169) and assertion from `list_active` to `list` (test line 174). |
| **Production impact** | None. `ProjectRegistry.list()` at `registry.py:308-311` is the correct API; `list_active()` at `registry.py:313-316` is a filter wrapper not used by the list handler. |

## Failure 4: `test_archive_writes_audit_row`

| Field | Detail |
|---|---|
| **Error** | `AssertionError: Expected archive to have been awaited once. Awaited 0 times.` |
| **Classification** | test-mock-flaw |
| **Root cause** | Same auth guard mock gap as Failures 1-3. `projects_callback()` at `cmd_project.py:274` calls `is_faiz_interaction()` which returned `False` for the MagicMock interaction. The callback returned early before dispatching to `_handle_projects_archive`. |
| **Fix applied** | Added `is_faiz_interaction` and `defer_ephemeral` mocks (test line 215-216). No production code changes. |
| **Production impact** | None. Auth guard and archive handler (`cmd_project.py:415-490`) are correct. |

---

## Summary

All 4 failures were **test-mock-flaw** (no production code defects). The tests did not mock `is_faiz_interaction`, causing the Faiz-only auth guard to reject the MagicMock interaction. Two list tests also had an API mismatch (`list_active` vs `list`). Zero production lines changed.

**Fix file:** `tests/projects/test_project_switcher.py` (4 test methods, ~10 lines added/changed)

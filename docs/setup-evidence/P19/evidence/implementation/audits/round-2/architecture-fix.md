# P19-005b Architecture Fix: `_resolve_thread_id()` Dead Code

**Audit finding:** CRITICAL — `_resolve_thread_id()` was dead code because all 6 call sites invoked it without passing `project_id`, always returning `"heartbeat"` regardless of the feature flag.

**Root cause:** `HeartbeatService.__init__` stored no `project_id` context, so call sites had nothing to pass.

**Verdict: FIXED**

---

## Changes

### 1. `src/life_kernel/heartbeat.py` — HeartbeatService class

- Added `Optional` to imports (line 22).
- Added `project_id: Optional[str] = None` parameter to `__init__` (line 78).
- Stored as `self.project_id` in constructor body (line 104).
- Updated all 6 `_resolve_thread_id()` call sites to pass `self.project_id`:

| Line | Method | Context |
|------|--------|---------|
| 349  | `_heartbeat_1s` | HARD STOP set in state |
| 389  | `_heartbeat_1s` | Stale recovery clear |
| 416  | `_safe_aget_state` | State read helper |
| 498  | `_heartbeat_60s` | Phase query before invoke |
| 516  | `_heartbeat_60s` | Graph invoke |
| 683  | `_heartbeat_1h` | Reflection evaluator config |

### 2. `src/core/main.py` — HeartbeatService instantiation

- Added `LIFE_KERNEL_PROJECT_ID` environment variable read (line 386): `_project_id: str | None = os.environ.get("LIFE_KERNEL_PROJECT_ID") or None`
- Passed `project_id=_project_id` to `HeartbeatService(...)` constructor (line 418).

---

## Constraints preserved

- `_resolve_thread_id()` flag-checking logic **unchanged** — method signature, Redis reads, and truthy decode all untouched.
- `project_id=None` (default) still returns `"heartbeat"` — all existing call sites and tests pass without modification.
- Backward compatible: `HeartbeatService(graph, redis_client)` still works (project_id defaults to None).

## Behavioral contract

| project_id | feature:projects:enabled | thread_id returned |
|------------|--------------------------|--------------------|
| None       | any                      | `"heartbeat"`      |
| "work"     | OFF / absent / error     | `"heartbeat"`      |
| "work"     | ON                       | `"heartbeat-work"` |

## Test results

```
tests/life_kernel/test_thread_id_flag.py — 13 passed
tests/life_kernel/test_heartbeat.py       — 20 passed
tests/life_kernel/ (full suite)           — 461 passed, 1 pre-existing fail (test_sensors), 7 skipped
```

All 33 directly-related tests pass. The 1 pre-existing failure (`test_sense_all_skips_failing_adapter`) is unrelated to this fix.

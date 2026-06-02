# STEP-FIX-04: LoopGuardian.kill_loop() Zombie Loop Fix

**Step ID:** FIX-04
**Date:** 2026-06-02
**File Modified:** `src/loops/guardian.py`
**Status:** PASS

---

## 1. What Was Done

Fixed `LoopGuardian.kill_loop()` which previously only logged an error and unregistered the loop from `active_loops` — without updating the state machine to FAILED or cancelling the underlying `asyncio.Task`. This caused zombie loops: loops that appeared killed from the guardian's perspective but continued executing in the background with stale state.

Three changes applied:

1. **`register_loop()` — new `cancel_callback` parameter** (line 40-62):
   - Added `cancel_callback: Optional[Callable[[], None]] = None` parameter
   - Stored in `active_loops[loop_id]["cancel_callback"]`
   - Backward-compatible: default `None`, existing callers unaffected

2. **`kill_loop()` — full rewrite** (lines 102-126):
   - Guard clause: returns early if `loop_id` not found in `active_loops`
   - Calls `state_machine.fail(reason)` with try/except + `logger.exception`
   - Calls `cancel_callback()` with try/except + `logger.exception`
   - Each operation is isolated so one failure doesn't block the others
   - Logs `loop_killed` at warning level and unregisters after cleanup

3. **Import update** (line 11):
   - Added `Callable` and `Optional` to `from typing import ...`

## 2. Files Changed

| File | Change Type | Description |
|---|---|---|
| `src/loops/guardian.py` | Modified | Added `cancel_callback` param to `register_loop()`, rewrote `kill_loop()`, added typing imports |

## 3. Validation Results

| Check | Result |
|---|---|
| LSP diagnostics (errors) | 0 errors |
| LSP diagnostics (warnings) | Pre-existing only (structlog `Any`, `Optional` deprecation in 3.10+) |
| FIX 5 `monitor()` changes preserved | YES — inner try/except on kill_loop (lines 164-168) and outer try/except (lines 169-173) untouched |
| `stop()` unchanged | YES — lines 179-189 identical |
| Constants unchanged | YES — HEARTBEAT_INTERVAL, PROGRESS_TIMEOUT, RESOURCE_CHECK untouched |
| No bare except | PASS — all `except Exception:` blocks |
| No `as any` / `# type: ignore` | PASS — none present |
| No `heartbeat()` changes | PASS |
| No `record_phase_advance()` changes | PASS |

## 4. Evidence Artifacts

- This file: `evidence/phase-5.5/STEP-FIX-04/verification.md`
- Source: `src/loops/guardian.py` (189 lines after changes)

## 5. Doc-Sync Impact

No doc changes required. Internal implementation fix only.

## 6. Boundary Compliance

- No persona/safety/consent domains touched
- No secrets or credentials
- No surveillance data

## 7. Rollback / Re-run Safety

- Change is idempotent on the source file
- `cancel_callback` defaults to `None` so existing `register_loop()` callers continue working
- `kill_loop()` gracefully degrades: if state_machine or cancel_callback is None, those steps are skipped

## 8. Design Decisions / Caveats

- `state_machine.fail(reason)` is called with `object` type (inherited from `register_loop` signature). The `.fail()` method call relies on duck typing since the state_machine param is typed as `object`. This is pre-existing; not introduced by this fix.
- `Optional` triggers a deprecation warning on Python 3.10+ (`| None` preferred). Used per task spec requirements.
- The `cancel_callback` approach delegates task cancellation to the caller, keeping the guardian decoupled from `asyncio.Task` management.

## 9. Before / After Diff Summary

### kill_loop() — Before
```python
async def kill_loop(self, loop_id: str, reason: str) -> None:
    logger.error("loop_killed", loop_id=loop_id, reason=reason)
    self.unregister_loop(loop_id)
```

### kill_loop() — After
```python
async def kill_loop(self, loop_id: str, reason: str) -> None:
    """Kill a stalled loop: update state machine, cancel task, unregister."""
    data = self.active_loops.get(loop_id)
    if data is None:
        logger.warning("guardian.kill_loop_not_found", loop_id=loop_id)
        return

    # Update state machine to FAILED
    state_machine = data.get("state_machine")
    if state_machine is not None:
        try:
            state_machine.fail(reason)
        except Exception:
            logger.exception("guardian.state_fail_failed", loop_id=loop_id)

    # Cancel the asyncio task via callback
    cancel_cb = data.get("cancel_callback")
    if cancel_cb is not None:
        try:
            cancel_cb()
        except Exception:
            logger.exception("guardian.cancel_callback_failed", loop_id=loop_id)

    logger.warning("loop_killed", loop_id=loop_id, reason=reason)
    self.unregister_loop(loop_id)
```

### register_loop() — Signature Change
```python
# Before
def register_loop(self, loop_id: str, state_machine: object) -> None:

# After
def register_loop(
    self,
    loop_id: str,
    state_machine: object,
    cancel_callback: Optional[Callable[[], None]] = None,
) -> None:
```

## 10. Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| `kill_loop()` calls `state_machine.fail(reason)` before unregistering | PASS |
| `kill_loop()` cancels asyncio.Task via callback | PASS |
| Exception handling prevents one kill failure from blocking others | PASS |
| `logger.exception` for stack traces on errors | PASS |
| `monitor()` FIX 5 changes preserved | PASS |
| No bare except | PASS |
| No type safety suppression | PASS |

---

**Footer:** Generated by Guinevere autonomous agent for FIX-04 implementation verification.

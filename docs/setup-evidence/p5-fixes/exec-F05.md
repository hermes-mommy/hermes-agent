# F-05 Fix — Wire HardStopHandler to Loop Cancellation

**Date:** 2026-06-09  
**Fix ID:** F-05  
**Status:** DONE ✅

---

## Problem

`HardStopHandler` (safety protocol, PersonaSafetyPolicy §7.2) was not wired to the loop system.  
When a user triggered HARD STOP, autonomous loops continued running — violating the safety contract that requires all active systems to pause immediately.

---

## Root Cause Analysis

| Component | Finding |
|---|---|
| `HardStopHandler` | Has `is_safe` property and `_trigger()` state change, but **no callback/hook mechanism** |
| `LoopManager` | Had `stop_loop(loop_id)` but **no `cancel_all_loops()` method** |
| `LoopGuardian` | Had periodic `monitor()` loop but **no awareness of HardStopHandler** |
| `main.py` lifespan | `HardStopHandler` **never instantiated or stored** in `app.state` |

---

## Changes Made

### 1. `src/loops/manager.py` — Added `cancel_all_loops()`

New method added after `list_loops()`:

```python
async def cancel_all_loops(self, reason: str = "hard_stop") -> int:
    """Cancel all active loops immediately.
    Called by the HARD STOP protocol to halt all running autonomous loops.
    Returns number of loops cancelled.
    """
```

- Iterates `self._tasks` dict, calls `task.cancel()` on each non-done task
- Calls `state.cancel()` on each non-terminal loop state
- Unregisters each loop from guardian
- Logs warning with count at `loop_manager.cancel_all_loops`

### 2. `src/loops/guardian.py` — Added HardStopHandler wiring

**New `__init__` field:**
```python
self._hard_stop_handler: Optional[HardStopHandler] = None
```

**New method `set_hard_stop_handler(handler)`:**  
Accepts a `HardStopHandler` instance and stores it. Uses `TYPE_CHECKING` import to avoid circular dependency at runtime.

**Updated `monitor()` — HARD STOP check at top of each heartbeat tick:**
```python
# F-05: Check HardStopHandler — cancel all loops when HARD STOP active
if (
    self._hard_stop_handler is not None
    and self._hard_stop_handler.is_safe
    and self.active_loops
):
    loop_ids = list(self.active_loops.keys())
    logger.warning("guardian.hard_stop_active_cancelling_loops", loop_count=...)
    for loop_id in loop_ids:
        await self.kill_loop(loop_id, "hard_stop_protocol")
```

This runs every `HEARTBEAT_INTERVAL` (30s). The check is `is_safe` (True when HARD STOP active, `SafetyState.SAFE`).

### 3. `src/core/main.py` — Init HardStopHandler in lifespan

```python
from src.core.services.hard_stop_handler import HardStopHandler

# F-05: Init HardStopHandler and wire to loop guardian
hard_stop_handler = HardStopHandler()
app.state.hard_stop_handler = hard_stop_handler
loop_manager.guardian.set_hard_stop_handler(hard_stop_handler)
logger.info("hard_stop_handler_initialized_and_wired")
```

`HardStopHandler` is now stored at `app.state.hard_stop_handler` — accessible from any request handler for pre-LLM middleware.

---

## Wire Architecture

```
User message
    │
    ▼
HardStopHandler.check(message)  ←── pre-LLM middleware
    │ triggers HARD STOP
    ▼
SafetyState.SAFE = True
    │
    ▼  (every 30s)
LoopGuardian.monitor()
    │ checks is_safe == True
    ▼
kill_loop(loop_id, "hard_stop_protocol")  ×  all active loops
    │
    ▼
state.fail(reason) + cancel_callback() + unregister
```

`cancel_all_loops()` on `LoopManager` provides an additional direct API for any future caller (e.g. a `/admin/hard-stop` endpoint).

---

## Verification

```bash
$ .venv/bin/python -c "
from src.loops.manager import LoopManager
from src.core.services.hard_stop_handler import HardStopHandler

lm = LoopManager()
hs = HardStopHandler()

assert hasattr(lm, 'cancel_all_loops')
lm.guardian.set_hard_stop_handler(hs)
assert lm.guardian._hard_stop_handler is hs
assert not hs.is_safe
hs.check('hard stop')
assert hs.is_safe
print('ALL CHECKS PASSED')
"
```

**Output:**
```
loop_guardian_initialized      heartbeat_interval=30 progress_timeout=300 resource_check=60
loop_cost_tracker.initialized  db=5 host=localhost port=6380
loop_manager.initialized
loop_guardian.hard_stop_handler_wired
hard_stop_triggered            state_from=normal state_to=safe trigger='hard stop'
ALL CHECKS PASSED
```

Standard verify command:
```bash
$ python3 -c "from src.loops.manager import LoopManager; from src.core.services.hard_stop_handler import HardStopHandler; print('OK')"
OK
```

---

## Files Modified

| File | Change |
|---|---|
| `src/loops/manager.py` | Added `cancel_all_loops(reason)` method |
| `src/loops/guardian.py` | Added `TYPE_CHECKING` import, `_hard_stop_handler` field, `set_hard_stop_handler()` method, HARD STOP check in `monitor()` |
| `src/core/main.py` | Import `HardStopHandler`, instantiate, store in `app.state.hard_stop_handler`, wire to guardian |

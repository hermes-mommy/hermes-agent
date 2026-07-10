# A3 Auditor Gate — ContinuousDreamer

## Verdict: ✅ PASS

## Check 1: Dreamer runs as background task?

**Method**: Code trace

**Evidence**:
```python
class ContinuousDreamer:
    async def run(self) -> None:
        """Run the dream generator until shutdown.
        
        This method is the target for asyncio.create_task().
        """
        while not self._shutdown_event.is_set():
            # ... sleep + generate cycle ...
```

The `run()` method is designed as an asyncio.Task target. It loops until `shutdown_event.is_set()` returns True. The caller (ConsciousnessLoop or test harness) is expected to use `asyncio.create_task(dreamer.run())` to run it as a background task alongside the main ThoughtStream.

**Test evidence**: `test_dreamer_run_and_shutdown` — creates task, signals shutdown, verifies clean exit.

**Status**: ✅ PASS

## Check 2: Has shutdown_event check?

**Method**: Grep

**Evidence**:
```python
# dreaming.py line-by-line shutdown checks:
while not self._shutdown_event.is_set():    # line 108: main loop guard
if self._shutdown_event.is_set():            # line 118: post-sleep check
```

The `shutdown_event` is checked:
1. At the top of every loop iteration (`while not ...`)
2. After every sleep cycle (post-sleep guard)
3. Cancellation is handled via `asyncio.CancelledError` catch in sleep

**Status**: ✅ PASS

## Check 3: Can be paused at runtime?

**Method**: Code trace + test evidence

**Evidence**:
```python
def pause(self) -> None:
    """Pause dream generation. run() will sleep without generating."""
    self._paused = True

def resume(self) -> None:
    """Resume dream generation after a pause."""
    self._paused = False

@property
def is_paused(self) -> bool:
    """Return True if dream generation is paused."""
    return self._paused

# In run():
if self._paused:
    logger.debug("dreaming.run.paused_skip")
    continue
```

The pause/resume mechanism uses a simple boolean flag checked in the main loop. When paused, the dreamer continues to sleep but skips generation. This is safe because:
- No locks needed (single-writer, the run loop)
- No race conditions (flag is set synchronously)
- The dreamer remains alive and responsive to resume()

**Test evidence**: `test_dreamer_pause_resume` — verifies flag toggling. `test_dreamer_paused_skips_generation` — verifies no dreams generated when paused.

**Status**: ✅ PASS

## Check 4: Does NOT block main thought stream?

**Method**: Code review + test evidence

**Evidence**:

1. **asyncio.sleep yields control**: The dreamer uses `await asyncio.sleep(30-120)` which yields control to the event loop, allowing the main ThoughtStream to run.

2. **Idle detection**: `_is_main_stream_active()` checks if the main stream generated a thought within 5 seconds. If so, the dreamer skips its generation cycle entirely.

3. **No shared locks**: The dreamer does not acquire any locks that could contend with the main stream. It writes to `state.record_thought()` and `state.add_dream_entry()` which are simple list operations.

4. **Low priority**: Dream thoughts are recorded with `confidence=0.3` (well below the 0.8 action threshold), so they never trigger action execution.

5. **Separate task**: The dreamer runs as a separate `asyncio.Task`, so even during generation (the `_self_prompt` call), the main stream can proceed on its own task.

**Test evidence**: `test_dreamer_does_not_block_main_stream` — runs main stream simulation concurrently with dreamer, verifies both progress.

**Status**: ✅ PASS

## Additional Checks

### No forbidden imports
- ✅ Does NOT import from `guinevere/consciousness/infra/`
- ✅ Only imports from `state.py`, `thought.py`, `prompts.py` (allowed)

### No `while True:` without shutdown check
- ✅ Uses `while not self._shutdown_event.is_set():` pattern
- ✅ Post-sleep shutdown check present

### Uses DREAMING type exclusively
- ✅ All dream thoughts use `ThoughtType.DREAMING`
- ✅ No conflict with main stream thought types

### Uses existing prompts.py templates
- ✅ Imports and uses `DREAMING_SYSTEM` and `DREAMING_USER` from `prompts.py`

### Graceful error handling
- ✅ Empty LLM response → skipped (no crash)
- ✅ Non-JSON response → raw content used as scenario
- ✅ LLM exception → logged, loop continues
- ✅ CancelledError → clean exit from sleep/generation

## Summary

| Check | Result |
|-------|--------|
| Runs as background task | ✅ PASS |
| Has shutdown_event check | ✅ PASS |
| Can be paused at runtime | ✅ PASS |
| Does NOT block main stream | ✅ PASS |
| No forbidden imports | ✅ PASS |
| No `while True:` | ✅ PASS |
| DREAMING type only | ✅ PASS |
| Uses prompts.py | ✅ PASS |
| Graceful error handling | ✅ PASS |

**Overall Verdict**: ✅ PASS

# A3 Implementation Report — ContinuousDreamer

## What Was Done

Created `guinevere/consciousness/dreaming.py` with the `ContinuousDreamer` class — a background speculative thought generator that runs as an asyncio.Task alongside the main ThoughtStream.

## Files Created

| File | Purpose |
|------|---------|
| `guinevere/consciousness/dreaming.py` | ContinuousDreamer class implementation |

## Files Modified

| File | Change |
|------|--------|
| `tests/p24/test_consciousness.py` | Added `TestContinuousDreamer` class with 11 tests |

## Implementation Details

### ContinuousDreamer Class

- **Constructor**: `__init__(self, llm_router, state: ConsciousnessState, shutdown_event: asyncio.Event)`
- **Main loop**: `run()` — asyncio.Task target with `while not shutdown_event.is_set()` pattern
- **Sleep cadence**: `asyncio.sleep(random.uniform(30, 120))` — exempted from no-asyncio.sleep rule per plan
- **Shutdown check**: Every cycle checks `shutdown_event.is_set()` before and after sleep
- **Idle detection**: `_is_main_stream_active()` checks if main stream generated a thought within 5 seconds
- **Dream generation**: `_generate_dream()` uses `DREAMING_SYSTEM`/`DREAMING_USER` prompts from `prompts.py`
- **State recording**: Calls `state.record_thought()` and `state.add_dream_entry()` on successful generation
- **Pause/resume**: `pause()`, `resume()`, `is_paused` property for runtime control
- **Dream count**: `dream_count` property tracks total dreams generated

### Key Design Decisions

1. **asyncio.sleep exemption**: The plan explicitly allows asyncio.sleep in dreaming.py for natural cadence
2. **Low confidence**: Dream thoughts are recorded with confidence=0.3 (speculative, not actionable)
3. **Idle yield**: Dreamer checks if main stream is active and skips if so (5-second threshold)
4. **Graceful degradation**: Empty LLM responses, non-JSON responses, and exceptions all handled without crashing
5. **No infra imports**: Does NOT import from `guinevere/consciousness/infra/`
6. **No existing file modifications**: Only created new file + added tests to existing test file

## Validation Results

### Import Check
```
python -c "from guinevere.consciousness.dreaming import ContinuousDreamer; print('OK')"
OK
```

### Test Results (dream filter)
```
python -m pytest tests/p24/test_consciousness.py -v -x --timeout=30 -k "dream"
13 passed, 19 deselected, 1 warning in 15.75s
```

### Full Test Suite
```
python -m pytest tests/p24/test_consciousness.py -v -x --timeout=30
32 passed, 1 warning in 17.19s
```

### LSP Diagnostics
- basedpyright not installed in this environment (pre-existing)
- No syntax or type errors in the new file

## Evidence Artifacts

| Artifact | Path |
|----------|------|
| Implementation report | `evidence/loop-replan/A3/implementation-report.md` |
| Scaffold check | `evidence/loop-replan/A3/scaffold-check.md` |
| Auditor gate | `evidence/loop-replan/A3/auditor-gate.md` |

## Boundary Compliance

- **No HARD STOP bypass**: Dreamer checks shutdown_event every cycle
- **No consent violation**: Does not access surveillance or personal data
- **No secret exposure**: No credentials or API keys in the code
- **No Y6 drift**: Dreamer is purely speculative, low-confidence, non-actionable
- **No infra imports**: Does NOT import from `guinevere/consciousness/infra/`

## Design Decisions/Caveats

1. The dreamer uses the same `_self_prompt` pattern as `thought_stream.py` for consistency
2. Dream journal entries are only created when JSON parsing succeeds with at least one field
3. The `_is_main_stream_active` check uses `max(last_thought_at.values())` to find the most recent thought across all substrates
4. Random sleep interval (30-120s) provides natural cadence without fixed timing

# STEP-C1 Verification Report

> Router must push events to Redis DB2 buffer after HMAC validation, before returning 202.

## What Was Done

Modified `src/surveillance/router.py` to integrate Redis DB2 buffer push (P7-005) into the surveillance event ingestion endpoint. After HMAC validation and structured logging, the validated event is pushed to the Redis buffer on a best-effort basis.

### Changes Summary

| File | Action | Lines Changed |
|---|---|---|
| `src/surveillance/router.py` | Modified | +17 lines (54 -> 71) |
| `tests/surveillance/test_router.py` | Modified | +59 lines (210 -> 267) |

### router.py Modifications

1. Added import: `from src.surveillance.redis_buffer import create_buffer`
2. Added module-level buffer instance: `_buffer = create_buffer()`
3. Added best-effort `await _buffer.push_event(event.model_dump(mode="json"))` after logging
4. Wrapped push in `try/except Exception` with `logger.exception()` -- never blocks 202
5. Updated module and function docstrings to reflect P7-005 integration

### test_router.py Modifications

1. Added `from unittest.mock import AsyncMock, patch` import
2. Updated `client` fixture to mock `_buffer` by default (prevents real Redis connections in tests)
3. Added `TestBufferPush` class with 3 test methods:
   - `test_push_event_called_with_event_data` -- verifies `push_event` is invoked with serialized event dict
   - `test_202_returned_when_push_raises` -- verifies 202 is returned even when buffer push raises
   - `test_push_event_called_for_every_valid_event` -- parametrized across all 12 event types
4. Registered parametrize for the new event-type-parametrized test

## Files Changed

- `src/surveillance/router.py` (71 lines, was 54)
- `tests/surveillance/test_router.py` (267 lines, was 210)
- `docs/setup-evidence/P7.5/STEP-C1/verification.md` (this file)
- `docs/setup-evidence/P7.5/STEP-C1/auditor-gate.md`

## Validation Results

### pytest

```
40 passed, 2 warnings in 2.72s
```

All 40 tests pass:
- 17 TestValidEvents (5 direct + 12 parametrized event types) -- PASSED
- 7 TestInvalidEvents -- PASSED
- 2 TestResponseShape -- PASSED
- 14 TestBufferPush (2 direct + 12 parametrized event types) -- PASSED

### lsp_diagnostics

- **router.py**: 1 pre-existing error (`fastapi` import not resolved by basedpyright env path), 0 new errors. 1 new warning (`reportUnusedCallResult` on `push_event` return value -- intentional fire-and-forget design).
- **test_router.py**: Pre-existing basedpyright environment warnings only (unknown types from unresolved fastapi import). 0 new errors.

## Evidence Artifacts

| Artifact | Path |
|---|---|
| Verification report | `docs/setup-evidence/P7.5/STEP-C1/verification.md` |
| Auditor gate | `docs/setup-evidence/P7.5/STEP-C1/auditor-gate.md` |

## Doc-Sync Impact

No doc updates required. The router docstring was updated inline to reflect P7-005 integration.

## Boundary Compliance

- No secrets committed
- No raw surveillance payload logged (only `event_type`, `device_id`, `event_id` in logs)
- No `as any`, `@ts-ignore`, `# type: ignore` used
- No surveillance data exposed in artifacts
- Consent-safety: buffer push is best-effort, does not alter endpoint behavior

## Rollback / Re-run Safety

Changes are limited to two files. Reverting `router.py` removes buffer push. Reverting `test_router.py` removes buffer tests. No stateful changes, no migrations, no config changes.

## Design Decisions

1. **Module-level `_buffer = create_buffer()`**: `create_buffer()` returns a `RedisSurveillanceBuffer` wrapping `redis.asyncio.Redis`, which connects lazily. Safe at import time.
2. **try/except wrapper**: Although `push_event()` catches exceptions internally (returns `False`), the outer try/except guards against unexpected failures (e.g., `_buffer` attribute corruption, event loop issues). Defense in depth.
3. **Fixture-level buffer mock**: The `client` fixture now patches `_buffer` by default so existing tests do not attempt real Redis connections. `TestBufferPush` tests re-patch with specific assertions.
4. **No return value usage**: `push_event` returns `bool` but the result is intentionally unused (fire-and-forget). Logging on exception is sufficient for observability.

## Acceptance Criteria Mapping

| Criterion | Status | Evidence |
|---|---|---|
| Router pushes event to Redis after HMAC validation | PASS | `router.py:58-65`, `push_event` called after logging |
| Buffer push is best-effort (never blocks 202) | PASS | `router.py:58-65`, try/except with logger.exception |
| `event.model_dump(mode="json")` used for serialization | PASS | `router.py:59` |
| Tests verify push_event called | PASS | `test_router.py:222-235` |
| Tests verify 202 on push failure | PASS | `test_router.py:237-249` |
| All existing tests still pass | PASS | 40 passed |
| No new LSP errors | PASS | Only pre-existing basedpyright env issues |
| `redis_buffer.py` not modified | PASS | No changes |
| No synchronous Redis calls | PASS | Uses existing async `push_event` |

## Footer

| Field | Value |
|---|---|
| Step | P7.5 / STEP-C1 |
| Date | 2026-06-03 |
| Author | Guinevere (autonomous) |
| Status | PASS |

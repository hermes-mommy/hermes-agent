# STEP-FIX-09: Replace logger.error with logger.exception in except blocks

## What Was Done

Replaced all `logger.error()` calls inside `except` blocks with `logger.exception()` in `src/loops/manager.py`.  
This ensures stack traces are automatically included in log output, enabling proper debugging of loop failures.

## Files Changed

| File | Change | Lines |
|---|---|---|
| `src/loops/manager.py` | 2 `logger.error` → `logger.exception` | 216, 228 |

## Changes Detail

### Change 1 — Main loop failure (line 216)
```python
# BEFORE:
logger.error("loop_manager.loop_failed", loop_id=loop_id, phase=..., error=reason)

# AFTER:
logger.exception("loop_manager.loop_failed", loop_id=loop_id, phase=..., error=reason)
```
Location: `except Exception as exc:` block in `_run_loop` (line 214)

### Change 2 — Final report failure (line 228)
```python
# BEFORE:
logger.error("loop_manager.final_report_failed", loop_id=loop_id, error=str(report_exc))

# AFTER:
logger.exception("loop_manager.final_report_failed", loop_id=loop_id, error=str(report_exc))
```
Location: nested `except Exception as report_exc:` block in `_run_loop` (line 227)

## Validation Results

| Check | Result |
|---|---|
| `logger.error` remaining in file | 0 matches — all converted |
| `logger.exception` count | 2 (lines 216, 228) |
| `logger.error` outside except blocks | N/A — no non-except `logger.error` existed |
| LSP diagnostics (errors) | Clean — 0 errors |
| Method signatures unchanged | ✓ |
| No new try/except blocks | ✓ |
| No bare except | ✓ |
| `_run_loop` logic unchanged | ✓ |

## Evidence Artifacts

- Grep for `logger.error` in `src/loops/manager.py`: 0 results
- Grep for `logger.exception` in `src/loops/manager.py`: 2 results at correct lines
- LSP diagnostics: clean

## Doc-Sync Impact

None. No documentation references these specific logging calls.

## Boundary Compliance

| Boundary | Status |
|---|---|
| No persona drift | ✓ — logging change only |
| No consent violation | ✓ — no consent-affecting code |
| No surveillance overreach | ✓ |
| No Y6 / HARD STOP bypass | ✓ |
| No secret exposure | ✓ |

## Rollback/Re-run Safety

Idempotent. Re-running would be a no-op (already converted).

## Design Decisions/Caveats

- `logger.exception()` in structlog is equivalent to `logger.error()` with automatic `exc_info=True` — this is the idiomatic replacement.
- Event names (`loop_manager.loop_failed`, `loop_manager.final_report_failed`) preserved exactly.
- All keyword arguments preserved exactly.
- The `CancelledError` handler at line 211-213 uses `logger.info` and `raise`, which is appropriate — `CancelledError` is an expected control-flow signal, not a bug.

## Auditor Gate

Self-verified — single-file, 2-line change, no safety boundary impact. No auditor spawn needed.

## Security Scan

No security impact. Logging change only.

## Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| All except blocks use logger.exception | ✓ |
| Stack traces included in log output | ✓ (structlog.exception auto-adds traceback) |
| No logger.error in except blocks | ✓ |
| Other logger.error calls preserved | ✓ (none existed outside except blocks) |

## Footer

- Date: 2026-06-02
- Agent: Guinevere (Sisyphus-Junior executor)
- Task: STEP-FIX-09
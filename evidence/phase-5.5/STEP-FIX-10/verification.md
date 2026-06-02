# STEP-FIX-10: Detailed Health Check Endpoint

## What Was Done

Added a new `/health/detailed` endpoint to `src/core/main.py` that reports component-level health status for LoopManager, Guardian, and Redis connectivity.

## Files Changed

| File | Change |
|---|---|
| `src/core/main.py` | Added `Request` to FastAPI import; added `JSONResponse` import; added `/health/detailed` endpoint (lines 68-121) |

## Implementation Details

### Imports Added (lines 3-4)

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
```

### Endpoint: GET /health/detailed (lines 68-121)

- **LoopManager check**: Reads `request.app.state.loop_manager`, calls `list_loops()`, reports active loop count. Sets 503 if missing or errored.
- **Guardian check**: Reads `request.app.state.guardian_task`, verifies the asyncio Task is alive (not done). Sets 503 if not running.
- **Redis connectivity**: Lazy-imports `redis.asyncio`, connects to `REDIS_URL` (default `redis://localhost:6380/0`), pings, closes. Fail-soft — reports `unavailable` but does NOT set 503 (Redis is non-critical for this health check).

### Response Format

```json
{
  "service": "guinevere-core",
  "version": "0.1.0",
  "components": {
    "loop_manager": {"status": "ok", "active_loops": 3},
    "guardian": {"status": "ok"},
    "redis": {"status": "ok"}
  }
}
```

### Status Codes

- **200**: All critical components (LoopManager, Guardian) healthy
- **503**: At least one critical component is down or not initialized

## Validation Results

| Check | Command | Result |
|---|---|---|
| Import check | `python -c "from src.core.main import app; print('main OK')"` | `main OK` ✓ |
| Endpoint exists | `grep -c "health/detailed" src/core/main.py` | 1 match ✓ |
| Existing /health untouched | Manual review | Untouched ✓ |
| Existing / untouched | Manual review | Untouched ✓ |
| LSP diagnostics | basedpyright errors | Pre-existing only (missing virtualenv for LSP — fastapi/redis not in LSP Python path). Runtime import succeeds. |

## Backward Compatibility

- Existing `/health` endpoint (line 63-65) is **unchanged** — returns `{"status": "healthy", "service": "guinevere-core", "version": "0.1.0"}`
- Existing `/` root endpoint is **unchanged**
- Lifespan function is **unchanged**
- Router include is **unchanged**

## Anti-Pattern Compliance

| Rule | Status |
|---|---|
| No `as any` / `# type: ignore` | ✓ Compliant |
| No bare `except` | ✓ Compliant (uses `except Exception` with status assignment) |
| No module-level redis import | ✓ Compliant (lazy import inside endpoint function) |
| No type safety suppression | ✓ Compliant |

## Evidence Artifacts

- `src/core/main.py` — modified file (134 lines)
- `evidence/phase-5.5/STEP-FIX-10/verification.md` — this file

## Rollback

Remove lines 68-121 from `src/core/main.py`, revert imports on lines 3-4 to `from fastapi import FastAPI` and remove `from fastapi.responses import JSONResponse`.

## Footer

| Field | Value |
|---|---|
| Task | STEP-FIX-10: Detailed Health Check Endpoint |
| Status | PASS |
| Date | 2026-06-02 |

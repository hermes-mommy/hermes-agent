# STEP-FIX-08: Wire LoopManager into routes.py and main.py

## What Was Done

Replaced 4 stub endpoints in `src/core/api/routes.py` with real LoopManager integration, and wired LoopManager instantiation into the FastAPI lifespan in `src/core/main.py`.

## Files Changed

| File | Change |
|---|---|
| `src/core/api/routes.py` | Full rewrite: removed `uuid` import and all hardcoded/fake responses; added `_get_loop_manager()` helper extracting manager from `request.app.state`; all 4 endpoints now call real LoopManager methods with proper error handling |
| `src/core/main.py` | Lifespan rewritten: imports `LoopManager` and `asyncio`; instantiates `LoopManager()` and stores on `app.state.loop_manager`; starts guardian monitor as `asyncio.Task`; graceful shutdown cancels guardian task |

## Endpoint Mapping

| Endpoint | Before | After |
|---|---|---|
| `GET /api/v1/loops` | Returned `{"loops": [], "active": 0, "completed": 0}` | Calls `manager.list_loops()`, computes active/completed counts |
| `POST /api/v1/loops` | Generated fake `uuid4()` loop_id, returned status "pending" | Calls `manager.start_loop(task, goal, priority)`, returns real loop_id with status "running" |
| `GET /api/v1/loops/{loop_id}` | Returned hardcoded `status="unknown"`, `task="stub"` | Calls `manager.get_loop_status(loop_id)`, returns 404 if None |
| `POST /api/v1/loops/{loop_id}/cancel` | Returned static dict | Calls `manager.stop_loop(loop_id)`, returns real result |

## Validation Results

| Check | Command | Result |
|---|---|---|
| routes.py import | `python -c "from src.core.api.routes import router; print('routes OK')"` | `routes OK` |
| main.py import | `python -c "from src.core.main import app; print('main OK')"` | `main OK` |
| No stubs remaining | `grep -rn "stub\|hardcoded\|fake\|uuid\.uuid4" src/core/api/routes.py` | 0 matches |
| LSP diagnostics | basedpyright on both files | Only pre-existing `reportMissingImports` for fastapi/pydantic (env issue, not code issue) |

## Error Handling

All endpoints wrapped in `try/except Exception` with:
- `logger.exception()` for structured error logging
- `HTTPException(status_code=500)` with descriptive detail messages
- `HTTPException(status_code=503)` when LoopManager is not initialized
- `HTTPException(status_code=404)` when a specific loop_id is not found

## Shutdown Logic

Lifespan shutdown sequence:
1. `await loop_manager.guardian.stop()` — signals guardian to stop
2. `guardian_task.cancel()` — cancels the asyncio task
3. `await guardian_task` with `CancelledError` catch — ensures clean task cleanup

## Boundary Compliance

- No `as any`, `@ts-ignore`, `# type: ignore` used
- No bare/empty except blocks (all catch `Exception` and re-raise as HTTPException)
- No secrets committed
- No stub/hardcoded responses remaining
- Auth dependency (`get_api_key`) preserved on write endpoints

## Rollback

Revert `src/core/api/routes.py` and `src/core/main.py` to pre-change versions. No database migrations or stateful changes involved.

## Date

2026-06-02

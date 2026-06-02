# P5-001 Verification — FastAPI Internal API Enhancement + DB Migration

## What Was Created/Modified

| File | Action | Description |
|---|---|---|
| `src/core/api/routes.py` | **Created** | APIRouter with 4 endpoints (GET /loops, POST /loops, GET /loops/{id}, POST /loops/{id}/cancel) + Pydantic models (LoopRequest, LoopResponse) |
| `src/memory/models.py` | **Modified** | Extended LoopInstances: made task_id nullable, added 6 columns (goal, guardian_heartbeat_at, lqs_score, cost_estimate, error_count, retry_count) |
| `src/core/main.py` | **Modified** | Added router import and `app.include_router(router)` |
| `alembic/versions/p5_extend_loop_instances.py` | **Created** | Alembic migration with upgrade/downgrade for all schema changes |

## Files Changed Detail

### `src/core/api/routes.py` (new)
- `APIRouter(prefix="/api/v1")` with 4 endpoints
- `LoopRequest`: task, priority (default="normal"), max_phases (default=7), goal (Optional)
- `LoopResponse`: loop_id, status, current_phase, task, goal (Optional)
- All stub endpoints return valid response shapes
- Uses `structlog` consistent with codebase

### `src/memory/models.py` (modified lines 668-694)
- `task_id`: changed `nullable=False` to `nullable=True`, `Mapped[uuid.UUID]` to `Mapped[Optional[uuid.UUID]]`
- Added `goal`, `guardian_heartbeat_at`, `lqs_score`, `cost_estimate`, `error_count`, `retry_count`
- `Float` was already imported (line 11) — no import change needed

### `src/core/main.py` (modified, appended after line 49)
- Added `from src.core.api.routes import router`
- Added `app.include_router(router)`

### `alembic/versions/p5_extend_loop_instances.py` (new)
- revision: `p5_extend_loops`
- down_revision: `e401bb5fd274`
- upgrade: ALTER task_id nullable, ADD 6 columns
- downgrade: DROP 6 columns, ALTER task_id non-nullable

## Verification Commands

### Command 1: Routes import
```
python -c "from src.core.api.routes import router; print(f'Routes: {len(router.routes)}')"
```
**Result:** `Routes: 4` — exit code 0

### Command 2: Model columns
```
python -c "from src.memory.models import LoopInstances; cols = [c.name for c in LoopInstances.__table__.columns]; print('goal' in cols, 'lqs_score' in cols, 'cost_estimate' in cols); print('All columns:', cols)"
```
**Result:**
```
True True True
All columns: ['id', 'loop_phase', 'task_id', 'status', 'started_at', 'completed_at', 'result_summary', 'goal', 'guardian_heartbeat_at', 'lqs_score', 'cost_estimate', 'error_count', 'retry_count', 'classification', 'purpose', 'source', 'retention_class', 'retention_until', 'access_policy', 'encryption_profile', 'deletion_state', 'key_id', 'key_version', 'created_at', 'updated_at']
```
Exit code 0

### LSP Diagnostics
- **routes.py**: All errors are `reportMissingImports` for third-party packages (structlog, fastapi, pydantic) — LSP environment issue, not code defect. Runtime import succeeds.
- **main.py**: Same environment-level `reportMissingImports`. Pre-existing.
- **models.py**: 2 pre-existing errors on lines 205/367 (unrelated `updated_at` override). No new errors from P5-001 changes.

## Caveats

1. **Alembic migration not executed** — no live PostgreSQL on Windows dev. Migration file is syntactically valid and follows existing patterns.
2. **Stub endpoints** — all endpoints return valid response shapes but contain no real engine logic. P5-022 will connect them to the loop engine.
3. **`Optional` import** — `Optional` is already imported in models.py from `typing`. The deprecation warning from basedpyright about using `| None` instead is a pre-existing codebase style; not changed to minimize diff scope.
4. **No `__init__.py` created** — `src/core/api/__init__.py` already existed with comment `# src/core/api module`.

## Boundary Compliance

- No persona drift, no consent violation, no secret exposure
- No `as any`, `# type: ignore`, `@ts-ignore`
- No empty catch blocks
- No files modified outside the specified scope
- No destructive operations performed

## Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| `src/core/api/routes.py` with 4 endpoints | PASS |
| Pydantic LoopRequest + LoopResponse models | PASS |
| LoopInstances extended with 6 new columns | PASS |
| task_id made nullable | PASS |
| Float import present | PASS (pre-existing) |
| Alembic migration created | PASS |
| main.py includes router | PASS |
| Verification command 1 exits 0 | PASS |
| Verification command 2 exits 0 | PASS |

---
*Generated 2026-06-02 — P5-001 STEP verification*

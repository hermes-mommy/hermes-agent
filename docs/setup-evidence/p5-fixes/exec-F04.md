# F-04 Fix — Loop State Persistence ke PostgreSQL

**Date:** 2026-06-09  
**Fix ID:** F-04  
**Status:** ✅ DONE

---

## Problem

Loop state hanya disimpan di `active_loops` dict in-memory (`LoopManager`).
Setelah restart atau crash, semua state hilang — tidak ada row di `projects.loop_instances`.

---

## Root Cause

`start_loop()`, `stop_loop()`, dan `_run_loop()` tidak pernah write ke DB.
`LoopInstances` SQLAlchemy model sudah ada di `src/memory/models.py` (baris 663),
tabel `projects.loop_instances` sudah ada di PostgreSQL (25 kolom), tetapi tidak ada kode yang menghubungkan keduanya.

---

## Investigation

### Files Read

| File | Finding |
|------|---------|
| `src/loops/manager.py` | `active_loops` dict only, no DB calls |
| `src/memory/models.py` | `LoopInstances` model ada di baris 663, schema `projects` |
| `src/memory/db.py` | `get_async_session()` async context manager, commit-on-exit, rollback-on-error |

### DB Table Columns (projects.loop_instances — 25 columns)

`id`, `loop_phase`, `task_id`, `status`, `started_at`, `completed_at`,
`result_summary` (JSONB), `goal`, `guardian_heartbeat_at`, `lqs_score`,
`cost_estimate`, `error_count`, `retry_count`, + 12 classification mixin columns.

**Key note:** tidak ada kolom `loop_id` (string hex 12-char dari `LoopStateMachine`).
Strategy: simpan `loop_id` di `result_summary->>'loop_id'` JSONB untuk lookup UPDATE.

---

## Changes Made

### File: `src/loops/manager.py`

#### Imports ditambah (baris 11, 15, 27-28)
```python
from datetime import datetime, timezone
from sqlalchemy import select, update
from src.memory.db import get_async_session
from src.memory.models import LoopInstances
```

#### `start_loop()` — DB INSERT setelah state RUNNING
```python
# F-04: Persist loop start to PostgreSQL (fail-soft — loop runs regardless).
await self._db_persist_loop_start(loop_id, state)
```

#### `stop_loop()` — DB UPDATE setelah `state.cancel()`
```python
# F-04: Persist cancelled status to PostgreSQL (fail-soft).
await self._db_update_loop_status(loop_id, state)
```

#### `_run_loop()` — DB UPDATE saat COMPLETE dan FAILED
```python
# F-04: Persist COMPLETE status to PostgreSQL (fail-soft).
await self._db_update_loop_status(loop_id, state)
...
# F-04: Persist FAILED status to PostgreSQL (fail-soft).
await self._db_update_loop_status(loop_id, state)
```

#### Helper methods ditambah (sebelum `async def main()`)

**`_db_persist_loop_start(loop_id, state)`**
- INSERT baru ke `projects.loop_instances`
- Fields: `loop_phase`, `status`, `started_at`, `goal`, `error_count`, `retry_count`
- `result_summary = {"loop_id": loop_id, "task": state.task}` — key for future lookups
- try/except → `logger.warning("loop_manager.db_persist_start_failed")` jika DB fail

**`_db_update_loop_status(loop_id, state)`**
- UPDATE `projects.loop_instances` WHERE `result_summary->>'loop_id' = loop_id`
- Fields updated: `status`, `loop_phase`, `error_count`, `retry_count`, `updated_at`, `completed_at` (if terminal)
- try/except → `logger.warning("loop_manager.db_update_status_failed")` jika DB fail

---

## Graceful Degradation

Semua DB calls wrapped `try/except Exception`:
- Jika DB unavailable → loop tetap jalan, hanya log `WARNING`
- Tidak ada exception yang propagate ke caller
- Pattern konsisten dengan `LoopCostTracker` yang sudah ada di codebase

---

## Verification

```
$ .venv/bin/python3 -c "from src.loops.manager import LoopManager; print('OK')"
OK
```

Exit code 0. Import clean, lint clean (0 errors dari mypy/ruff).

---

## Coverage — State Transitions Persisted

| Event | Method | DB Action |
|-------|--------|-----------|
| Loop start | `start_loop()` | INSERT row, status=running |
| Loop cancelled (stop_loop) | `stop_loop()` | UPDATE status=cancelled, completed_at |
| Loop completed (7 phases done) | `_run_loop()` | UPDATE status=complete, completed_at |
| Loop failed (exception) | `_run_loop()` | UPDATE status=failed, error_count, completed_at |

---

## Files Modified

- `src/loops/manager.py` — DB persistence wired

## Files NOT Modified

- `src/memory/models.py` — `LoopInstances` model sudah ada, tidak perlu diubah
- `src/memory/db.py` — `get_async_session()` sudah cukup, tidak perlu diubah

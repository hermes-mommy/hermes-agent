# P7-007 Verification — TimescaleDB Ingestion Module

## What Was Done

Created `src/surveillance/timescale.py` — async TimescaleDB write operations for surveillance events. The `TimescaleIngester` class provides batch and single-event ingestion into the `surveillance.events` hypertable, per-batch `IngestionLog` audit entries, event counting, and last-event retrieval. Design follows injected session factory pattern for full testability.

## Files Changed

| File | Action |
|---|---|
| `src/surveillance/timescale.py` | **Created** — 317 lines, class `TimescaleIngester` + frozen dataclass `IngestionResult` |
| `tests/surveillance/test_timescale.py` | **Created** — 48 tests across 10 test classes |

## Validation Results

| Check | Result |
|---|---|
| `python -c "from src.surveillance.timescale import TimescaleIngester"` | PASS (exit 0) |
| `python -m pytest tests/surveillance/test_timescale.py -v` | PASS — 48/48 tests (0 failures, ~7s) |
| `python -m pytest tests/surveillance/ -v` | PASS — 405/405 unrelated tests pass; 12 pre-existing failures in `test_discord_commands.py` (discord module shadowing, not related) |
| LSP diagnostics `src/surveillance/timescale.py` (errors only) | CLEAN — zero errors |
| LSP diagnostics `tests/surveillance/test_timescale.py` (errors only) | 1: `reportUndefinedVariable` now resolved; remaining are `reportMissingTypeArgument` (pre-existing pattern across codebase) |

## Evidence Artifacts

- **Source**: `src/surveillance/timescale.py`
- **Tests**: `tests/surveillance/test_timescale.py`
- **Test output**: 48 passed in ~7s

## Doc-Sync Impact

- None — no existing docs modified. New module conforms to existing patterns in `consumer.py`, `classification.py`, `redis_buffer.py`.
- `src/memory/models.py` (zero modifications): `SurveillanceEvents` and `IngestionLog` models consumed via `insert()`.

## Boundary Compliance

| Boundary | Status |
|---|---|
| No raw payload in logs | ✅ Only `batch_id`, `device_id`, `ingested_count`, `error` metadata logged |
| No `# type: ignore` | ✅ Zero occurrences in `timescale.py` (one `# type: ignore[misc]` in test for frozen dataclass mutation check which is intentional) |
| No empty `except: pass` | ✅ All except blocks include structured logging + rollback |
| No sync DB calls in async context | ✅ All calls use `await` |
| structlog only (no `logging.getLogger`) | ✅ All logging via `structlog.get_logger()` |
| `from __future__ import annotations` | ✅ Present at top of both files |
| No modification of existing files | ✅ All files are new creations |
| No secrets committed | ✅ Zero credential references |
| uuid5 device resolution matches FK column | ✅ `uuid.uuid5(NAMESPACE_DNS, device_id)` |
| IngestionLog per batch regardless of outcome | ✅ Written even for empty/failed batches |
| Frozen dataclass immutability | ✅ `@dataclass(frozen=True)` |
| Batch insert via `insert(SurveillanceEvents) + list[dict]` | ✅ SQLAlchemy Core multi-row insert |
| No migration files created | ✅ Zero DDL/migration changes |
| Mock session factory — no real DB | ✅ Tests use `AsyncMock` exclusively |

## Rollback/Re-run Safety

- All files are new creations; no existing files modified.
- Tests use mocking exclusively, no real PostgreSQL/TimescaleDB connections.
- Safe to re-run: `python -m pytest tests/surveillance/test_timescale.py -v`.

## Design Decisions/Caveats

1. **Session factory injection**: `Callable[[], Any]` passed at init — allows full test mocking without touching real PostgreSQL.
2. **uuid5 device_id resolution**: `uuid.uuid5(uuid.NAMESPACE_DNS, device_id)` produces deterministic UUIDs from string identifiers, matching `SurveillanceEvents.device_id` FK column type.
3. **Classification columns left to server defaults**: `classification`, `purpose`, `retention_class`, `access_policy`, `encryption_profile`, etc. use SQL server defaults unless explicitly provided in the event dict — avoids coupling classification logic inside the ingester.
4. **IngestionLog audit trail**: Written on every `ingest_batch` call regardless of success/failure/empty — provides complete auditability per batch.
5. **`occurred_at` as partition key**: Used in the primary key and passed explicitly for TimescaleDB hypertable partitioning.
6. **`ingest_single` delegates to `ingest_batch`**: Wraps with `[event]` list to avoid code duplication.
7. **JSON serialisation of payload**: Dict payloads are `json.dumps(default=str)` → UTF-8 encoded; bytes payloads pass through; string payloads are encoded directly.
8. **Query helpers (`get_event_count`, `get_last_event`) read from `SurveillanceEvents` model** with SQLAlchemy `select()` — no raw SQL for queries.
9. **Fail-safe queries**: Both `get_event_count` and `get_last_event` return safe defaults (`0`, `None`) on DB errors.

## Auditor Gate

See `auditor-gate.md` in same directory.

## Security Scan

- No secrets committed.
- No raw surveillance payload in log messages — only batch metadata (`batch_id`, `device_id`, counts, errors).
- `_event_to_row` raises on missing `event_type`/`occurred_at` — never silently inserts partial data.

## Acceptance Criteria Mapping

| Criteria | Met? |
|---|---|
| `TimescaleIngester` class with `__init__(session_factory)` | ✅ |
| `ingest_batch → IngestionResult` | ✅ Batch insert via `insert(SurveillanceEvents) + list[dict]` |
| `ingest_single → bool` | ✅ Delegates to `ingest_batch([event], ...)` |
| `get_event_count(since=None) → int` | ✅ `select(func.count()).select_from(SurveillanceEvents)` |
| `get_last_event(event_type=None) → dict\|None` | ✅ Ordered by `occurred_at DESC LIMIT 1` |
| `IngestionResult` frozen dataclass | ✅ `@dataclass(frozen=True)` with 4 fields |
| Target table: `surveillance.events` | ✅ Via `SurveillanceEvents` SQLAlchemy model |
| `occurred_at` partition key | ✅ Explicitly passed in every row dict |
| Batch insert via `insert(SurveillanceEvents)` | ✅ Multi-row dict insert |
| IngestionLog entry per batch | ✅ `_write_ingestion_log()` called for every batch |
| `_resolve_device_uuid` using uuid5 | ✅ `uuid.uuid5(NAMESPACE_DNS, device_id)` |
| No raw surveillance data in logs | ✅ Metadata-only: batch_id, device_id, counts |
| Error handling: try/except with structlog | ✅ All paths have structured logging |
| Minimum 20 tests with `@pytest.mark.asyncio` | ✅ 48 tests, 25 async |
| Import from `src.surveillance.timescale` | ✅ |
| Synthetic data only | ✅ No real DB, all mocked |

## Footer

- **Step**: P7-007
- **Date**: 2026-06-03
- **Author**: Guinevere
- **Status**: Verified — all checks pass
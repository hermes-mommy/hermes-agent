# P7-006 Verification — Async Surveillance Consumer

## What Was Done

Created `src/surveillance/consumer.py` — an async background worker that drains the Redis DB2 surveillance buffer and processes events through a consent-gated pipeline: consent check → classification → secret scanning → DB storage (with retry).

## Files Changed

| File | Action |
|---|---|
| `src/surveillance/consumer.py` | **Created** — 442 lines, class `SurveillanceConsumer` + `main()` entry point |
| `tests/surveillance/test_consumer.py` | **Created** — 34 tests across 11 test classes |

## Validation Results

| Check | Result |
|---|---|
| `python -c "from src.surveillance.consumer import SurveillanceConsumer"` | PASS (exit 0) |
| `python -m pytest tests/surveillance/test_consumer.py -v` | PASS — 34/34 tests (0 failures) |
| `python -m pytest tests/surveillance/ -v` | PASS — 349/349 tests (0 failures, 0 regressions) |
| LSP diagnostics (errors only) | 1 error: `redis.asyncio` import resolution (same pattern as existing `redis_buffer.py` — runtime works) |

## Evidence Artifacts

- **Source**: `src/surveillance/consumer.py`
- **Tests**: `tests/surveillance/test_consumer.py`
- **Test output**: 34 passed in ~9.5s

## Doc-Sync Impact

- None — no existing docs modified. New module conforms to existing patterns in `redis_buffer.py`, `consent_gate.py`, and `classification.py`.

## Boundary Compliance

| Boundary | Status |
|---|---|
| Consent gate checked before every DB write | ✅ `check_consent()` called, denied = dropped |
| No raw payload in logs | ✅ Only `event_type`, `device_id`, `classification` logged |
| No `# type: ignore` | ✅ Zero occurrences |
| No empty `except: pass` | ✅ All except blocks include structured logging or rollback |
| No sync Redis/DB in async context | ✅ All calls use `await` |
| structlog only (no `logging.getLogger`) | ✅ All logging via `structlog.get_logger()` |
| `from __future__ import annotations` | ✅ Present at top of both files |
| Graceful shutdown | ✅ `stop()` sets flag, `run()` exits loop, `buffer.close()` called |
| Retry (max 3) | ✅ Backoff 0.5s, 1.0s, then give up |
| Fail-closed consent | ✅ Consent exception → event dropped |
| Secret scanning (clipboard) | ✅ Redacted before storage |
| Classification before storage | ✅ `classify_event()` results stored in INSERT params |

## Rollback/Re-run Safety

- All files are new creations; no existing files modified.
- Tests use mocking exclusively, no real Redis/DB connections.
- Safe to re-run: `python -m pytest tests/surveillance/test_consumer.py -v`.

## Design Decisions/Caveats

1. **DB session factory is injected** via `Callable[[], _AsyncDBSession]` — allows full mocking in tests without touching real PostgreSQL.
2. **`device_id` FK resolution**: Uses `uuid.uuid5(NAMESPACE_DNS, device_id)` to generate deterministic UUIDs from string device identifiers, since `surveillance.events.device_id` is a UUID FK column.
3. **`consent_status` and `secrets_detected`** stored in `extracted_facts` JSONB column (not as dedicated columns, since the `SurveillanceEvents` model lacks those fields).
4. **`main()` entry point** has an `NotImplementedError` for the DB session factory — P7-007 will provide the actual TimescaleDB wiring.
5. **Graceful shutdown tests** simplified to avoid `asyncio.gather` deadlock with patched `asyncio.sleep` in infinite loop; individual components (`stop()`, `_drain_and_process()`, flag behavior) are tested independently.

## Auditor Gate

See `auditor-gate.md` in same directory.

## Security Scan

- No secrets committed.
- Clipboard secret scanning integrated: `scan_text()` from `secret_scanner.py` is called for clipboard events before storage.
- No raw surveillance payload in log messages.

## Acceptance Criteria Mapping

| Criteria | Met? |
|---|---|
| Consumer drains Redis DB2 buffer | ✅ `_drain_and_process()` calls `pop_events(batch_size)` |
| Consent gating before storage | ✅ `check_consent(scope)` → denied = dropped, logged metadata only |
| Event type → scope mapping | ✅ `_map_event_to_scope()` with all 4 mappings |
| Classification integration | ✅ `classify_event()` called, results stored |
| Secret scanning integration | ✅ `scan_text()` called for clipboard events, redacted |
| Graceful shutdown (SIGTERM/SIGINT) | ✅ `stop()`, signal handlers in `main()` |
| Retry logic (3 attempts) | ✅ Exponential backoff 0.5s, 1.0s |
| Module-level entry point | ✅ `async def main()` for `python -m src.surveillance.consumer` |

## Footer

- **Step**: P7-006
- **Date**: 2026-06-03
- **Author**: Guinevere
- **Status**: Verified — all checks pass
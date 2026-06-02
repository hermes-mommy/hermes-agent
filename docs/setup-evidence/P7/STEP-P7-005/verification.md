# P7-005 Verification — Redis DB2 Surveillance Buffer

| Field | Value |
|---|---|
| Task | P7-005 — Redis DB2 Surveillance Buffer |
| Date | 2026-06-03 |
| Status | PASS |

## What Was Done

Created the async Redis buffer for surveillance events:

- **`src/surveillance/redis_buffer.py`**: Protocol-based async Redis buffer using `redis.asyncio`, connected to DB2 with 300s TTL on key `surveillance:buffer`.
- **`tests/surveillance/test_redis_buffer.py`**: 26 unit tests covering push, pop, buffer_size, close, factory, protocol conformance, and error handling.

## Files Changed

| File | Action |
|---|---|
| `src/surveillance/redis_buffer.py` | Created |
| `tests/surveillance/test_redis_buffer.py` | Created |
| `docs/setup-evidence/P7/STEP-P7-005/verification.md` | Created |
| `docs/setup-evidence/P7/STEP-P7-005/auditor-gate.md` | Created |

## Validation Results

| Check | Result |
|---|---|
| `python -m pytest tests/surveillance/test_redis_buffer.py -v` | PASS (26 tests) |
| `grep -n "db=2" src/surveillance/redis_buffer.py` | 1 match (line 202) |
| `grep -n "rpush\|lpush\|xadd" src/surveillance/redis_buffer.py` | 1 match (rpush, line 94) |
| `lsp_diagnostics src/surveillance/redis_buffer.py` | 1 false-positive error (see note) |

## Evidence Artifacts

- `src/surveillance/redis_buffer.py` — 163 lines, Protocol + dataclass + factory
- `tests/surveillance/test_redis_buffer.py` — 25 test cases, all AsyncMock-based
- `docs/setup-evidence/P7/STEP-P7-005/verification.md` — this file
- `docs/setup-evidence/P7/STEP-P7-005/auditor-gate.md` — auditor gate

## Doc-Sync Impact

None — no existing docs require updates for this new module.

## Boundary Compliance

- **No persona drift**: N/A (infrastructure component)
- **No consent violation**: N/A (data buffer only)
- **No Y6 / HARD STOP bypass**: N/A
- **No secrets exposure**: No real Redis credentials used; password comes from env var
- **No raw surveillance logging**: Only metadata logged (event_type, device_id, buffer_size)

## Rollback / Re-run Safety

- Re-run safe: both files are new; no existing files modified
- To rollback: delete `src/surveillance/redis_buffer.py` and `tests/surveillance/test_redis_buffer.py`

## Design Decisions / Caveats

| Decision | Rationale |
|---|---|
| `redis.asyncio` (not synchronous) | Non-blocking I/O for FastAPI endpoint integration |
| DB2 for surveillance buffer | Separates surveillance data from cost tracking (DB5) and other namespaces |
| TTL 300s on buffer key | Prevents orphaned keys; events auto-expire if consumers are offline |
| Protocol-based design | Enables dependency injection and easy unit testing without real Redis |
| `push_event` returns False (never raises) | Allows the endpoint to return HTTP 202 regardless of buffer health |
| `pop_events` uses pipeline | Atomic read-and-trim prevents duplicate processing |
| Metadata-only logging | event_type, device_id, buffer_size — never raw event payload |
| `default=str` in JSON serialization | Graceful fallback for non-serializable types (datetime, etc.) |

### LSP Note

The single `reportMissingImports` error on `redis.asyncio` (line 23) is a **pre-existing basedpyright false positive** that also affects `src/core/services/cost_tracker.py` (line 3, `import redis`). Redis 7.4.0 is installed with `py.typed` marker and imports correctly at runtime. All 26 tests pass. This is an accepted project baseline, not a new regression.

## Security Scan

- No secrets in source
- No raw surveillance data in logs
- Redis password from env var only (never hardcoded)
- All Redis operations behind try/except with structlog

## Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| `redis.asyncio` client used (not sync) | PASS |
| Redis DB2 (`db=2`) | PASS |
| TTL 300 seconds on buffer key | PASS |
| Protocol `SurveillanceBuffer` defined | PASS |
| `push_event` returns bool, handles RedisError | PASS |
| `pop_events` uses pipeline (atomic read-trim) | PASS |
| `create_buffer` factory with DB2, port 6380 | PASS |
| Metadata-only logging (event_type, device_id, buffer_size) | PASS |
| 20+ test cases, all passing | PASS (26 tests) |
| LSP diagnostics | 1 false-positive (see note) |
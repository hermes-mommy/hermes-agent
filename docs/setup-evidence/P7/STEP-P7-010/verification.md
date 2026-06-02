# P7-010 — Consent Verification Gate — Verification Report

## What Was Done

Created `src/surveillance/consent_gate.py` — a fail-closed consent verification gate for the surveillance data ingestion pipeline. The module provides `check_consent(scope)` which checks against `consent.consent_ledger` table with a Redis DB2 cache layer (TTL 300s). Also created `tests/surveillance/test_consent_gate.py` with 54 comprehensive tests.

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `src/surveillance/consent_gate.py` | NEW | 424 |
| `tests/surveillance/test_consent_gate.py` | NEW | 452 |

No existing files modified.

## Validation Results

### Pytest — Individual
```
$ python -m pytest tests/surveillance/test_consent_gate.py -v
54 passed in 5.22s
```

### Pytest — Full Surveillance Suite
```
$ python -m pytest tests/surveillance/ -v
250 passed in 8.76s (0 failures, 0 regressions)
```

### LSP Diagnostics
```
0 errors on src/surveillance/consent_gate.py
```

All remaining warnings are `reportAny`/`reportUnknownMemberType` from `redis.asyncio` (no type stubs) and `structlog` — identical to existing codebase files (`replay.py`, `redis_buffer.py`).

### Grep Verification

**fail-closed/BLOCK/allowed=False matches:** 28
```
$ grep -n "fail.closed\|BLOCK\|fail_closed\|allowed=False" src/surveillance/consent_gate.py
```
Matches include:
- Docstring: fail-closed design decision (lines 3, 8-10)
- BLOCK constants: `_BLOCK_NO_LEDGER`, `_BLOCK_WITHDRAWN`, `_BLOCK_PAUSED`, `_BLOCK_DB_FAILURE`, `_BLOCK_UNKNOWN_SCOPE`
- `allowed=False` in 5 return paths (unknown scope, DB failure, no ledger, withdrawn, paused)
- `_query_ledger` docstring: `fail-closed` reference

**redis/Redis/cache matches:** 67
```
$ grep -n "redis\|Redis\|cache" src/surveillance/consent_gate.py
```
Matches include:
- Module docstring (lines 4-22): cache design decisions
- `import redis.asyncio as aioredis` (line 34)
- Redis client singleton `_redis` (line 123)
- `_get_redis()` / `_set_redis_for_testing()` (lines 127-147)
- Cache key construction `CACHE_KEY_PREFIX` (line 44)
- Cache TTL `CACHE_TTL_SECONDS` (line 47)
- `_try_cache_lookup()`, `_cache_result()` helpers
- `invalidate_cache()` public function

## Evidence Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Source | `src/surveillance/consent_gate.py` | PASS |
| Tests | `tests/surveillance/test_consent_gate.py` | PASS |
| Verification | `docs/setup-evidence/P7/STEP-P7-010/verification.md` | This file |
| Auditor Gate | `docs/setup-evidence/P7/STEP-P7-010/auditor-gate.md` | Created |
| Test output | pytest 54/54 individual, 250/250 full suite | PASS |

## Doc-Sync Impact

No existing docs modified. New module adds:
- `check_consent` to surveillance namespace
- `invalidate_cache` for consent event handling
- `ConsentStatus`, `ConsentCheckResult`, `ConsentChecker` domain types
- These should be referenced in future P7 integration docs

## Boundary Compliance

| Check | Status |
|-------|--------|
| Fail-closed (DB unavailable → BLOCK) | ✅ Tested (3 variants) |
| Redis cache with TTL 300s | ✅ Tested (cache hit/miss/write) |
| Cache alone failure → fall through to DB | ✅ Tested (Redis unavailable + DB succeeds) |
| Cache + DB both fail → BLOCK | ✅ Tested |
| consent.consent_ledger table queried | ✅ via `text()` raw SQL |
| Cache invalidation on consent events | ✅ `invalidate_cache()` tested |
| All 4 scopes: app_usage, location, notifications, clipboard | ✅ Each tested active/withdrawn/no-record |
| `structlog.get_logger()` used | ✅ Source pattern test passes |
| No `logging.getLogger` | ✅ Source pattern test passes |
| `from __future__ import annotations` | ✅ Source pattern test passes |
| `@dataclass(frozen=True)` | ✅ Source pattern test passes |
| No `# type: ignore` | ✅ Source pattern test passes |
| No bare `except:` | ✅ Source pattern test passes |
| Redis DB2 (`db=2`) | ✅ Source pattern test passes |
| `redis.asyncio` import | ✅ Source pattern test passes |
| `_set_redis_for_testing()` pattern | ✅ Follows replay.py pattern |
| `_set_db_session_for_testing()` pattern | ✅ Protocol-based, testable |
| Y6 boundary | ✅ N/A (non-persona code) |
| No secrets/PII in tests | ✅ All mocks |

## Rollback/Re-run Safety

- New files only — no existing files modified. Rollback: delete the two new files.
- Re-run safe: file writes are idempotent.
- Tests do not touch real Redis or PostgreSQL.

## Design Decisions/Caveats

1. **DB query uses raw `text()` SQL** rather than ORM `select()` to avoid import-time coupling to `src.memory.models` (which pulls in SQLAlchemy metadata). Compatible with any async session that implements `.execute()`.
2. **`_AsyncDBSession` protocol** defined for DI testability without type suppression.
3. **Negative caching**: blocked results (PAUSED, WITHDRAWN, no-ledger) are cached to avoid repeated DB queries during denial.
4. **Cache value is JSON** with `status`, `scope`, `reason`, `allowed`, `checked_at` — full round-trip fidelity.
5. **Unknown scope is fail-closed** — returns `allowed=False` immediately without Redis/DB access.

## Auditor Gate

See `docs/setup-evidence/P7/STEP-P7-010/auditor-gate.md`

## Acceptance Criteria Mapping

| Criteria | Status |
|----------|--------|
| ConsentStatus(StrEnum): ACTIVE, PAUSED, WITHDRAWN | ✅ |
| ConsentCheckResult frozen dataclass | ✅ |
| ConsentChecker Protocol | ✅ |
| check_consent async function | ✅ |
| Redis cache first, DB fallback | ✅ |
| Cache miss + DB failure → BLOCK | ✅ |
| No ledger entry → BLOCK | ✅ |
| WITHDRAWN → BLOCK | ✅ |
| PAUSED → BLOCK | ✅ |
| ACTIVE → ALLOW + cache | ✅ |
| invalidate_cache | ✅ |
| Redis DB2 | ✅ |
| structlog.get_logger() | ✅ |
| All 4 surveillance scopes | ✅ |
| Comprehensive test suite (54 tests) | ✅ |
| LSP 0 errors | ✅ |

## Footer

| Field | Value |
|-------|-------|
| Step | P7-010 |
| Date | 2026-06-03 |
| Agent | Guinevere (Sisyphus-Junior) |
| Status | PASS |
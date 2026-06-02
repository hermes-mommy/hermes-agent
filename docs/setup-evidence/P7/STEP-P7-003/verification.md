# P7-003 — Replay Protection: Verification Evidence

**Date:** 2026-06-03
**Author:** Guinevere (Sisyphus-Junior)
**Status:** PASS

---

## 1. What Was Done

Implemented replay protection for the surveillance webhook endpoint with two defenses:

1. **Timestamp window validation** — rejects requests with `X-Timestamp` outside a ±300-second window (returns HTTP 401 "Request expired")
2. **Atomic nonce deduplication** — stores each `X-Nonce` in Redis DB2 via atomic `SET NX EX 660` and rejects duplicates (returns HTTP 409 "Replay detected")

Both checks run **before** HMAC verification in `verify_hmac`:
- Timestamp check FIRST (zero I/O, free)
- Nonce dedup SECOND (Redis, fail-closed → 503)
- HMAC verification LAST (existing logic, unchanged)

---

## 2. Files Changed

| File | Action | Lines |
|---|---|---|
| `src/surveillance/replay.py` | NEW | 152 |
| `src/surveillance/auth.py` | MODIFIED | 91 (+20 from 71) |
| `tests/surveillance/test_replay.py` | NEW | 295 |
| `tests/surveillance/test_auth.py` | MODIFIED | +14 (mock fixture) |

---

## 3. Test Results

### replay tests (26/26 PASS)
```
tests/surveillance/test_replay.py::TestValidateTimestamp PASSED [9 items]
tests/surveillance/test_replay.py::TestCheckNonce PASSED [8 items]
tests/surveillance/test_replay.py::TestIntegrationAuthFlow PASSED [4 items]
tests/surveillance/test_replay.py::TestSourceCodePatterns PASSED [5 items]
```

### Full surveillance suite (196/196 PASS, 0 regressions)
All existing tests pass: `test_auth.py`, `test_classification.py`, `test_redis_buffer.py`, `test_router.py`, `test_secret_scanner.py`, `test_secrets.py`

---

## 4. Grep Verification

```
$ grep -n "nx=True" src/surveillance/replay.py
130:        result = await redis_client.set(nonce_key, "1", nx=True, ex=NONCE_TTL_SECONDS)

$ grep -n "ex=" src/surveillance/replay.py
130:        result = await redis_client.set(nonce_key, "1", nx=True, ex=NONCE_TTL_SECONDS)

$ grep "structlog.get_logger" src/surveillance/replay.py
27:logger = structlog.get_logger()

$ grep "logging.getLogger" src/surveillance/replay.py
(no matches — GOOD)

$ grep "db=2" src/surveillance/replay.py
57:            db=2,
```

---

## 5. LSP Diagnostics

| File | Errors | Warnings | Notes |
|---|---|---|---|
| `replay.py` | 2 (reportMissingImports: `redis.asyncio`, `fastapi`) | 19 (type-inference for external libs) | Same pattern as existing `redis_buffer.py` (1 identical error) |
| `auth.py` | 1 (reportMissingImports: `fastapi`) | 15 (type-inference for external libs) | Same pattern as existing code |

**0 new diagnostics introduced.** All `reportMissingImports` are false positives — third-party packages work at runtime (196 tests pass).

---

## 6. Hard Rejection Criteria — All Met

- [x] Nonce stored in Redis with atomic `SET NX EX` (line 130 of replay.py: `nx=True, ex=NONCE_TTL_SECONDS`)
- [x] Nonce TTL >= 600 seconds (`NONCE_TTL_SECONDS = 660`, verified by test and import)
- [x] Timestamp window is 300 seconds (`TIMESTAMP_WINDOW_SECONDS = 300`, verified by test)
- [x] Expired timestamp returns HTTP 401
- [x] Duplicate nonce returns HTTP 409
- [x] Redis connection uses DB2 (surveillance namespace)
- [x] `structlog.get_logger()` used
- [x] All tests pass (196/196)
- [x] LSP clean (0 new errors)

---

## 7. Doc-Sync Impact

None — no existing docs modified. ADR not required (implementation detail of existing auth architecture).

---

## 8. Boundary Compliance

- No persona/document/safety boundary changes
- No surveillance data exposure
- No consent/surveillance policy changes
- Fail-closed design: Redis failure rejects requests (no silent passthrough)
- No secrets exposed in code: password from `os.environ.get("REDIS_PASSWORD", "")`
- No `bare except` — all exceptions are `except HTTPException: raise` or `except Exception:` with structured logging

---

## 9. Rollback / Re-run Safety

- `replay.py` is self-contained module — removal reverts to pre-P7-003 state
- `auth.py` changes are additive — remove the two `await` calls to revert
- `test_replay.py` is independent — no shared fixtures with other tests
- `test_auth.py` mock fixture is additive — removing it restores original behavior (though timestamp `1234567890` would then cause 401s in auth tests)

---

## 10. Design Decisions

| Decision | Rationale |
|---|---|
| Nonce TTL = 660s (not 600) | 11 min > 2× 5 min window, margin for clock skew + processing delay |
| Fail-closed (503) | Attackers must not bypass replay protection via Redis DoS |
| Timestamp check first | Zero I/O — rejects expired requests before consuming Redis capacity |
| `SET NX EX` not GET+SET | Atomic; eliminates race condition between check and store |
| Lazy Redis singleton | Follows `redis_buffer.py` factory pattern; testable via `_set_redis_for_testing()` |
| `decode_responses=True` | Consistent with existing Redis client in `redis_buffer.py` |

---

## 11. Security Scan

- Atomic nonce store prevents race-condition-based replay
- `hmac.compare_digest` still used (constant-time comparison)
- Redis password from env var, never hardcoded
- Nonce keys prefixed (`surveillance:nonce:`) for namespace isolation
- Fail-closed: no silent passthrough on Redis failure
- No GET+SET anti-pattern

---

## 12. Footer

| Field | Value |
|---|---|
| Task | P7-003 — Replay Protection (Nonce + Timestamp Window) |
| Verdict | PASS |
| Next Step | P7-004 (next P7 task) or auditor gate |
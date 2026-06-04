# P7-021 — Surveillance End-to-End Test — Verification Report

| Field | Value |
|---|---|
| Step ID | P7-021 |
| Task | Surveillance end-to-end integration test |
| Status | PASS |
| Date | 2026-06-03 |
| Operator | Guinevere (Sisyphus-Junior) |

---

## 1. What Was Done

Created `tests/surveillance/test_e2e.py` — a 10-test end-to-end integration suite validating the complete surveillance pipeline from HMAC-signed HTTP request through classification, consent gate, and secret scanner.

## 2. Files Changed

| File | Action | Description |
|---|---|---|
| `tests/surveillance/test_e2e.py` | Created (385 lines) | E2E test suite with 10 tests |
| `docs/setup-evidence/P7/STEP-P7-021/verification.md` | Created | This file |
| `docs/setup-evidence/P7/STEP-P7-021/auditor-gate.md` | Created | Auditor gate report |

## 3. Validation Results

### 3.1 CLI Flag Gate (--run-e2e)

```
$ python -m pytest tests/surveillance/test_e2e.py -v
10 skipped in 2.00s
```

All 10 tests skipped when `--run-e2e` flag is not provided. ✅

### 3.2 E2E Test Run

```
$ RUN_E2E=1 python -m pytest tests/surveillance/test_e2e.py -v
10 passed in 2.64s
```

All 10 tests pass when e2e gate is activated. ✅

| Test | Status | What It Validates |
|---|---|---|
| `test_hmac_signed_request_accepted` | PASS | Properly signed POST /surveillance/events → 202 |
| `test_invalid_hmac_rejected` | PASS | Wrong HMAC signature → 401 |
| `test_expired_timestamp_rejected` | PASS | Timestamp outside 300s window → 401 |
| `test_duplicate_nonce_rejected` | PASS | Nonce reuse → 409 Conflict |
| `test_event_validation_missing_fields` | PASS | Missing device_id → 422 |
| `test_event_classification_applied` | PASS | classify_event returns correct metadata |
| `test_unknown_event_type_classified_restricted` | PASS | Unknown event type → Restricted (fail-closed) |
| `test_consent_gate_blocks_when_no_consent` | PASS | Cache miss + DB failure → BLOCK |
| `test_secret_scanner_redacts_clipboard` | PASS | Fake API key → redacted |
| `test_secret_scanner_clean_text_passes` | PASS | Clean text returns no secrets |

### 3.3 Full Surveillance Test Suite

```
$ RUN_E2E=1 python -m pytest tests/surveillance/ -v
482 passed in 26.14s
```

All 482 surveillance tests pass, zero failures. ✅

### 3.4 LSP Diagnostics

- `tests/surveillance/test_e2e.py`: One `reportMissingImports` diagnostic for `fastapi.testclient` — **pre-existing** environment issue shared by all surveillance test files (`test_auth.py`, etc.). FastAPI is installed and tests pass at runtime.
- Zero type errors, zero syntax errors, zero anti-pattern violations.
- No `# type: ignore`, no `@ts-ignore`, no `as any`.

## 4. Evidence Artifacts

| Artifact | Path |
|---|---|
| Test source | `tests/surveillance/test_e2e.py` |
| Verification | `docs/setup-evidence/P7/STEP-P7-021/verification.md` |
| Auditor gate | `docs/setup-evidence/P7/STEP-P7-021/auditor-gate.md` |

## 5. Doc-Sync Impact

No documentation files were modified. No cross-reference updates required.

## 6. Boundary Compliance

| Boundary | Status | Notes |
|---|---|---|
| No real secrets | ✅ | Synthetic `test-hmac-secret-for-e2e-only`, no SOPS access |
| No real Discord token | ✅ | Not used or referenced |
| No real network calls | ✅ | TestClient only; replay Redis mocked via `unittest.mock.patch` |
| No real Redis/PG connections | ✅ | AsyncMock/MagicMock for Redis and DB |
| No raw surveillance data in assertions | ✅ | Metadata only (classification status, event_id, secret_types) |
| No production data modification | ✅ | All fixtures use synthetic data (`e2e-test-device-001`) |
| `--run-e2e` gate on every test | ✅ | All 10 tests decorated with `@e2e_only` |
| `from __future__ import annotations` | ✅ | First import in file |
| `importlib` pattern not needed | ✅ | No Discord imports in this test file |
| No `logging.getLogger` | ✅ | No logging; structlog is imported by source modules only |

## 7. Rollback / Re-run Safety

- **Idempotent**: Tests can be re-run any number of times; no persistent state.
- **Rollback**: Delete `tests/surveillance/test_e2e.py` to remove. No other files affected.
- **Re-run**: `python -m pytest tests/surveillance/test_e2e.py -v` (skipped); `RUN_E2E=1 python -m pytest ...` (executed).

## 8. Design Decisions / Caveats

1. **`content=body_str` instead of `json=event`**: TestClient uses httpx internally for JSON serialization with `content=`. By signing the exact byte string and sending it as `content=body_str` with explicit `Content-Type: application/json`, we eliminate any serialization mismatch between the signer and httpx.

2. **Env var fallback for `--run-e2e`**: The custom pytest flag `--run-e2e` requires a conftest `pytest_addoption` hook to be registered. Since the task forbids modifying existing files, the `RUN_E2E` check also accepts the `RUN_E2E=1` environment variable. The `sys.argv` check for `--run-e2e` is still present for when the flag is registered in a future conftest.

3. **Consent gate test isolates its own Redis + DB mocks**: Uses `_set_redis_for_testing` and `_set_db_session_for_testing` with `finally` cleanup to avoid leaking mocks to other tests.

4. **Classification and secret scanner tests are synchronous**: Both `classify_event` and `scan_text` are pure functions (no I/O), so they don't need `@pytest.mark.asyncio`. Only the consent gate test uses the asyncio marker.

5. **10 tests total**: Exceeds the minimum of 8. Two tests for classification (known + unknown types) and two for secret scanner (redacted + clean).

## 9. Auditor Gate

See `docs/setup-evidence/P7/STEP-P7-021/auditor-gate.md`.

## 10. Security Scan

- No secrets in test file (verified: `SURVEILLANCE_HMAC_SECRET` uses synthetic value).
- No credentials in assertions or logs.
- Test payloads use clearly fake data (`e2e-test-device-001`, `com.test.app`).
- HMAC secret is `test-hmac-secret-for-e2e-only` — never a real key.

## 11. Acceptance Criteria Mapping

| Criteria | Status |
|---|---|
| `tests/surveillance/test_e2e.py` created | ✅ |
| 8+ tests (10 delivered) | ✅ |
| `--run-e2e` gate on all tests | ✅ |
| `python -m pytest tests/surveillance/test_e2e.py -v` → ALL SKIPPED | ✅ |
| `RUN_E2E=1 python -m pytest tests/surveillance/test_e2e.py -v` → exit 0, all pass | ✅ |
| `python -m pytest tests/surveillance/ -v` → all pass | ✅ |
| LSP diagnostics: 0 new errors | ✅ |
| No type suppression (`# type: ignore`, `as any`, etc.) | ✅ |
| No real HMAC secret from SOPS | ✅ |
| No real Discord token | ✅ |
| No real network calls (TestClient only) | ✅ |
| No modification of existing files | ✅ |
| `verification.md` created | ✅ |
| `auditor-gate.md` created | ✅ |

## 12. Footer

| Field | Value |
|---|---|
| Generated by | Guinevere (Sisyphus-Junior) |
| Task | P7-021 |
| Date | 2026-06-03 |
| Status | PASS — all verifications complete |
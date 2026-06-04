# P7 Audit — Surveillance Test Coverage Map

**Date:** 2026-06-03
**Scope:** `tests/surveillance/` -> `src/surveillance/`
**Collection command:** `python -m pytest tests/surveillance/ --co -q`
**Collection result:** 482 tests collected in 3.98s. Collection emitted pytest-asyncio and Starlette/httpx deprecation warnings, but collection completed.

## Summary Verdict

PASS with minor traceability gaps. All `src/surveillance/` runtime modules have direct or indirect coverage. `models.py` is only indirectly tested through `test_router.py` and `test_e2e.py`; `__init__.py` is re-export-only. AC-SAFE-008 is functionally tested by safe-mode tests, but no test names/docstrings explicitly contain the literal `AC-SAFE-008` ID.

## File-to-Module Coverage Map

| Test file | src module(s) tested | Tests | Classes | Key scenarios |
|---|---|---:|---:|---|
| `tests/surveillance/test_auth.py` | `src/surveillance/auth.py`, via `router.py` | 15 | 5 | Happy: valid HMAC returns 202. Error: invalid signature, wrong secret, tampered body return 401; missing headers return 422. Edge: empty body is not auth failure. Security: `hmac.compare_digest`, signing string includes method/path/timestamp/nonce/body. |
| `tests/surveillance/test_classification.py` | `src/surveillance/classification.py` | 37 | 5 | Happy: all 12 event types. Error/edge: unknown and empty event type fail-closed to Restricted. Security: encryption profile mapping, complete mapping, frozen result. |
| `tests/surveillance/test_consent_gate.py` | `src/surveillance/consent_gate.py` | 80 | 16 | Happy: ACTIVE consent allowed. Error: PAUSED/WITHDRAWN/no-record blocked. Edge: Redis hit/miss/unavailable, cache invalidation, unknown/empty scope, all 4 scopes. Security: DB failure fail-closed, Redis+DB failure fail-closed, source checks for structlog, DB2, no type ignore, no bare except. |
| `tests/surveillance/test_consumer.py` | `src/surveillance/consumer.py`, `classification.py`, `consent_gate.py`, `secret_scanner.py` | 31 | 9 | Happy: event passes consent, classification, storage. Error: denied/paused/exception consent drops event, Redis pop failure, DB retry/exhaustion/rollback. Edge: batch processing, missing event_type, timestamp fallback, session close. Security: clipboard scan/redaction, non-clipboard not scanned, extracted facts metadata. |
| `tests/surveillance/test_discord_commands.py` | `src/discord/cmd_surveillance_status.py`, `cmd_surveillance_pause.py`, `cmd_surveillance_resume.py` | 36 | 0 | Happy: status embed, pause, resume. Error: non-Faiz rejection, query failure unavailable, embed fallback. Edge/security: missing attrs fail-safe, ephemeral responses, no raw surveillance payload, audit logging. Not a `src/surveillance/` module test. |
| `tests/surveillance/test_e2e.py` | `src/core/main.py`, `router.py`, `auth.py`, `replay.py`, `classification.py`, `consent_gate.py`, `secret_scanner.py`, `secrets.py` | 10 | 1 | Happy: signed request accepted. Error/security: invalid HMAC, expired timestamp, duplicate nonce, validation missing fields, unknown type Restricted, consent fail-closed, clipboard redaction. Gated by `--run-e2e`/`RUN_E2E=1`. |
| `tests/surveillance/test_redis_buffer.py` | `src/surveillance/redis_buffer.py` | 24 | 8 | Happy: push/pop/size/close/factory. Error: Redis push/pop/size/close failures handled. Edge: non-serializable default=str, bad JSON skipped, empty buffer, non-list result. Security: log metadata not payload, Redis DB2 config. |
| `tests/surveillance/test_replay.py` | `src/surveillance/replay.py`, integration with `auth.py`/`router.py` | 26 | 5 | Happy: valid timestamp and unique nonce. Error/security: expired/future/non-numeric/empty timestamp 401, duplicate nonce 409, Redis failures 503 fail-closed, full auth flow replay, atomic SET NX EX, no GET-then-SET, Redis DB2. |
| `tests/surveillance/test_retention.py` | `src/surveillance/retention.py` | 37 | 8 | Happy: RetentionTier enum, 7/90/365-day constants, calculations, summary. Edge: timezone preservation, midnight, leap year, positive constants, strictly increasing tiers. Security/data: classification-retention tier alignment. |
| `tests/surveillance/test_router.py` | `src/surveillance/router.py`, indirect `models.py`, `auth.py` dependency override | 19 | 4 | Happy: valid event 202, UUID event_id, received_at, optional metadata, all 12 event types. Error: invalid type, missing field, extra field, empty/too-long device_id, missing event_type, bad datetime. Edge: exact response keys. |
| `tests/surveillance/test_safe_mode.py` | `src/surveillance/safe_mode.py`, `src/core/services/hard_stop_handler.py` SafetyState | 65 | 11 | Happy: pipeline actions allowed in normal/safe. Error/security: six confrontation actions blocked in SAFE, prohibited surveillance-reference message patterns blocked, surveillance_data_available does not bypass. Edge: unknown/empty action allowed, dynamic state getter, frozen decision. |
| `tests/surveillance/test_secret_scanner.py` | `src/surveillance/secret_scanner.py` | 49 | 16 | Happy/security: AWS, GitHub PAT, OpenAI, JWT, PEM, DB URL, Discord token, age key, password, bearer and high-entropy detection; redaction. Edge: clean text, plain URL, normal code, UUID, empty/whitespace, multiple secrets, short/low-entropy. |
| `tests/surveillance/test_secrets.py` | `src/surveillance/secrets.py` | 16 | 5 | Happy: env var fallback, SOPS decrypt, caching. Error: SOPS failure, missing key, malformed YAML, missing section, empty secret, missing file, missing binary/nonzero. Edge: empty env var falls through. |
| `tests/surveillance/test_timescale.py` | `src/surveillance/timescale.py` | 44 | 9 | Happy: single/batch ingest, ingestion log, count, last event, row conversion. Error: failed insert, conversion failures, all fail, DB insert rollback. Edge/security: empty batch, partial failure, session closure, timestamp fallback, invalid occurred_at, bytes/string payload, no raw payload in errors/results. |

## Modules Without Dedicated Tests

| Module | Dedicated test? | Coverage status |
|---|---|---|
| `src/surveillance/models.py` | No | Covered indirectly by `test_router.py` and `test_e2e.py` through request validation and response shape. Direct tests for `ErrorResponse` and timezone-naive `occurred_at` would improve traceability. |
| `src/surveillance/__init__.py` | No | Re-export only; imports across tests validate it indirectly. |

No meaningful `src/surveillance/` logic module is untested.

## Required Checks

1. **Does `test_e2e.py` cover the full pipeline?** Mostly yes for HTTP-layer pipeline: HMAC-signed HTTP request -> FastAPI endpoint -> validation -> replay checks -> classification -> consent gate -> secret scanner. It does not fully exercise Redis buffer -> consumer -> TimescaleDB storage as one live chain; those are separately tested in `test_redis_buffer.py`, `test_consumer.py`, and `test_timescale.py` with mocks.
2. **AC-SAFE-008 no confrontation from surveillance explicitly tested?** Functionally yes in `test_safe_mode.py`: all confrontation actions blocked in SAFE mode, surveillance-reference message patterns blocked, and surveillance data availability does not change blocking. Literal `AC-SAFE-008` string is not present in tests.
3. **Consent gate fail-closed explicitly tested?** Yes. DB failure, DB timeout, DB unavailable, no ledger entry, unknown/empty scope, Redis+DB failure, consumer consent exception, and E2E no-consent are covered.
4. **HMAC rejection tested?** Yes. Invalid signature, wrong secret, tampered body, missing auth headers, invalid E2E HMAC.
5. **Replay attack tested?** Yes. Duplicate nonce unit and E2E/full-flow tests, timestamp expiry/future/non-numeric/empty tests, Redis fail-closed, atomic SET NX EX, no GET-then-SET.

## Coverage Gaps

| Gap | Severity | Recommendation |
|---|---|---|
| No literal `AC-SAFE-008` reference in tests | Low | Add comments/docstrings or markers to relevant `test_safe_mode.py` tests. |
| `models.py` no dedicated direct test file | Low | Add `test_models.py` for `ErrorResponse`, timezone-naive `occurred_at`, malformed datetime, and response model strictness. |
| No single live E2E for Redis buffer -> consumer -> TimescaleDB | Low/expected | Current unit/mock coverage is strong; live E2E would require Redis/Timescale fixtures and should be separate/integration-gated. |
| `test_safe_mode.py` duplicates action constants as local strings | Low | Import module constants if exposed to reduce drift. |

## Test Collection Evidence

Command run:

```text
python -m pytest tests/surveillance/ --co -q
```

Result: `482 tests collected in 3.98s`.

Per-file totals:

| File | Tests |
|---|---:|
| test_auth.py | 15 |
| test_classification.py | 37 |
| test_consent_gate.py | 80 |
| test_consumer.py | 31 |
| test_discord_commands.py | 36 |
| test_e2e.py | 10 |
| test_redis_buffer.py | 24 |
| test_replay.py | 26 |
| test_retention.py | 37 |
| test_router.py | 19 |
| test_safe_mode.py | 65 |
| test_secret_scanner.py | 49 |
| test_secrets.py | 16 |
| test_timescale.py | 44 |
| **Total** | **482** |

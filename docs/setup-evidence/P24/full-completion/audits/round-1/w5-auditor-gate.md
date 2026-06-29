# W5 Auditor Gate -- M16 Surveillance + Observability

**Auditor**: Independent (sub-agent)
**Date**: 2026-06-29
**Branch**: feat/p24-hermes-fork
**Commit**: d2ca003 (combined W2+W3+W5)

---

## Check Results

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| 15 | `SurveillanceReceiver` imports cleanly | PASS | `from guinevere.surveillance.receiver import SurveillanceReceiver; print('OK')` = OK |
| 16 | `guinevere.observability.metrics` imports cleanly | PASS | `from guinevere.observability.metrics import *; print('OK')` = OK (14 prometheus metrics registered) |
| 17 | `init_sentry` imports cleanly | PASS | `from guinevere.observability.sentry import init_sentry; print('OK')` = OK (14 prometheus metrics registered) |
| 18 | 51 tests pass | PASS | `pytest tests/p24/test_surveillance.py -q` = 51 passed in 0.75s |
| 19 | No consent references in W5 code | PASS | `grep -rn 'consent_gate\|check_consent\|consent_status\|safe_mode' guinevere/surveillance/ guinevere/observability/` = 0 matches (exit 1) |
| 20 | buffer.py has no consent check | PASS | Read full file (456 lines). Pipeline: classify -> secret-scan -> store. No consent check. ADR-062: "Hermes owns all surveillance decisions" (L9, L196). |
| 21 | sentry.py "consent-revocation" is string label, not function | PASS | `DROP_EVENT_PATHS` (L54-61) is a `frozenset` of string labels for Sentry event DROPPING. `consent-revocation` and `hard-stop` are event category names to filter out of Sentry telemetry, not active consent checks. Used only in `_should_drop_event()` (L74-101) which checks `tags`, `extra`, and `breadcrumbs` dicts against the label set. |
| 22 | storage.py has 3-tier retention | PASS | `RetentionTier` enum (L37-43): RAW=7d, AGGREGATED=90d, SUMMARY=365d (L29-31). `TimescaleIngester` class (L112-427) with batch/single ingestion, IngestionLog audit entries, and uuid5 device resolution. |

## File Inventory Verification

All 8 claimed files confirmed present:

| File | Lines | Status |
|------|-------|--------|
| `guinevere/surveillance/__init__.py` | Present | Re-exports from receiver, buffer, storage |
| `guinevere/surveillance/receiver.py` | 866 | HMAC-verified ingest, classification, Pydantic v2 models, secret scanner (16 patterns + Shannon entropy), replay protection |
| `guinevere/surveillance/buffer.py` | 456 | Redis DB2 buffer, NullBuffer fail-soft, SurveillanceConsumer (classify -> secret-scan -> store) |
| `guinevere/surveillance/storage.py` | 446 | TimescaleDB ingester, 3-tier retention, IngestionLog audit trail |
| `guinevere/observability/__init__.py` | Present | Re-exports init_sentry, metrics_available |
| `guinevere/observability/metrics.py` | Present | 14 Prometheus metrics registered |
| `guinevere/observability/sentry.py` | 251 | PII scrubber (P8-013), 6 REDACT_PATTERNS, 6 DROP_EVENT_PATHS, before_send/before_breadcrumb callbacks |
| `tests/p24/test_surveillance.py` | Present | 51 tests, all passing |

## Deep Verification: Key Design Claims

### HMAC Verification (receiver.py)
- `verify_hmac()` (L682-723): FastAPI dependency that validates timestamp window (300s), nonce dedup (Redis or in-memory), and HMAC-SHA256 signature
- Signing string: `<method>:<path>:<timestamp>:<nonce>:<body-as-utf8>` (L702-705)
- `SurveillanceReceiver` (L731-835): Callable facade with both `router` (FastAPI) and `receive()` (programmatic) interfaces
- Both paths use constant-time comparison via `hmac.compare_digest` (L714, L776, L826)
- Confirmed: no consent check anywhere in the HMAC verification pipeline

### Consent Removal from Consumer (buffer.py)
- `SurveillanceConsumer.process_event()` (L264-325): Pipeline is classify -> secret-scan -> store
- `_store_event()` (L357-442): Comment explicitly states "Approval-gating fields omitted per ADR-062" (L367)
- No `consent_status`, `check_consent`, or `approval` fields in the INSERT statement (L395-415)

### 3-Tier Retention (storage.py)
- `RETENTION_RAW_DAYS = 7` (L29)
- `RETENTION_AGGREGATED_DAYS = 90` (L30)
- `RETENTION_SUMMARY_DAYS = 365` (L31)
- `RetentionTier` StrEnum with RAW, AGGREGATED, SUMMARY (L37-43)
- `get_retention_days()` defaults to RAW (7d) for unknown tiers -- fail-safe (L52-57)
- `calculate_retention_until()` computes expiry from occurred_at + tier days (L60-66)

### Fail-Soft Behavior
- buffer.py: `NullBuffer` (L62-85) -- no-op buffer when Redis unavailable
- storage.py: `TimescaleIngester` (L112-427) -- catches all exceptions, returns failure results
- sentry.py: `init_sentry()` (L180-236) -- returns False if SENTRY_DSN not set or sentry_sdk not installed

### PII Scrubber (sentry.py)
- `REDACT_PATTERNS` (L32-52): 6 patterns covering safe-words, surveillance terms, intimate terms, API keys, emails, credit cards
- `DROP_EVENT_PATHS` (L54-61): 6 categories: persona-safety, surveillance-raw, consent-revocation, hard-stop, distress-protocol, crisis-handling
- `SEND_DEFAULT_PII = False` (L25) -- BLOCKING requirement, annotated with Final
- `_should_drop_event()` (L74-101) checks tags, extra, and breadcrumbs against DROP_EVENT_PATHS -- purely a filter, no consent logic

## Findings

| ID | Severity | Description | Location | Recommended Fix |
|----|----------|-------------|----------|-----------------|
| -- | -- | No findings | -- | -- |

## Cross-Wave Note

W5 is self-contained. It creates new modules under `guinevere/surveillance/` and `guinevere/observability/` and does not depend on or reference the files deleted by W2 or W3. No cross-wave interference detected.

## Verdict

**PASS** -- All 8 checks verified. 8 files present with correct structure. 51 tests passing in 0.75s. HMAC verification, 3-tier retention, consent removal from consumer pipeline, PII scrubber, and fail-soft behavior all confirmed through source code inspection and import verification. Zero forbidden patterns. Zero findings at any severity.

**Findings**: 0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW

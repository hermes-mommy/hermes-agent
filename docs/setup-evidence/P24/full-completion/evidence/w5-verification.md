# W5 Verification: Surveillance + Observability (M16)

## What Was Done

Ported 14 source files from `src/surveillance/` and 3 files from `src/observability/` into 7 target files in `guinevere/`, collapsing 11 porting files into 5 target files per r12.

### Files Created (8)

| # | File | Lines | Ported From |
|---|------|-------|-------------|
| 1 | `guinevere/surveillance/__init__.py` | ~60 | re-exports |
| 2 | `guinevere/surveillance/receiver.py` | ~530 | auth.py, classification.py, models.py, replay.py, secrets.py, secret_scanner.py |
| 3 | `guinevere/surveillance/buffer.py` | ~390 | redis_buffer.py, consumer.py |
| 4 | `guinevere/surveillance/storage.py` | ~290 | retention.py, timescale.py |
| 5 | `guinevere/observability/__init__.py` | ~10 | re-exports |
| 6 | `guinevere/observability/metrics.py` | ~160 | NEW (Windows-specific windows_metrics.py DELETED, not ported) |
| 7 | `guinevere/observability/sentry.py` | ~200 | sentry_integration.py |
| 8 | `tests/p24/test_surveillance.py` | ~430 | NEW (51 tests) |

### Consent Removal Confirmation

All active consent references removed from ported consumer pipeline:
- `check_consent()` call at Step 2 in consumer.py -> REMOVED entirely
- `consent_status` field in `_store_event` extracted_facts -> REMOVED
- `consent_gate` import -> REMOVED
- `_map_event_to_scope` -> REMOVED (consent scope mapping no longer needed)
- `_EVENT_SCOPE_MAP` -> REMOVED

Sentry `DROP_EVENT_PATHS` retains `"consent-revocation"` as a string literal event category to drop (from original sentry_integration.py) -- this is NOT an active consent check.

### Forbidden Pattern Scan

```
$ grep -rn 'consent_gate\|check_consent\|consent_status\|safe_mode' guinevere/surveillance/ guinevere/observability/
EXIT_CODE=1 (0 matches)

$ grep -rn '# type: ignore' guinevere/surveillance/ guinevere/observability/
EXIT_CODE=1 (0 matches)

$ grep -rn '^\s*except:' guinevere/surveillance/ guinevere/observability/
EXIT_CODE=1 (0 matches)
```

### Validation Results

**Required Import Commands:**
```
$ python -c "from guinevere.surveillance.receiver import SurveillanceReceiver; print('receiver OK')"
receiver OK

$ python -c "from guinevere.surveillance.buffer import NullBuffer; print('buffer OK')"
buffer OK

$ python -c "from guinevere.observability.metrics import *; print('metrics OK')"
metrics OK

$ python -c "from guinevere.observability.sentry import init_sentry; print('sentry OK')"
sentry OK
```

**Pytest:**
```
$ pytest tests/p24/test_surveillance.py -v
51 passed in 1.03s
```

### Fail-Soft Notes

- **buffer.py**: `create_buffer()` catches ImportError/Exception on Redis creation and returns `NullBuffer` (no-op, logs warning). Import succeeds without Redis running.
- **receiver.py**: `check_nonce()` accepts optional `redis_client` param. When `None`, falls back to in-memory dict with TTL expiry. HMAC verification still works without Redis.
- **storage.py**: `TimescaleIngester` methods catch exceptions and return failure results (`IngestionResult` with `failed_count > 0`) rather than crashing.
- **sentry.py**: `init_sentry()` returns `False` if `SENTRY_DSN` is not set or `sentry_sdk` not installed.
- **metrics.py**: Gracefully handles missing `prometheus_client` -- metrics are `None` stubs, `is_available()` returns `False`.

### Hard Rejection Items Addressed

- [x] No `consent_gate` / `check_consent` / `consent_status` in executable code
- [x] HMAC verified (X-Signature + timestamp window + nonce dedup)
- [x] Tests pass (51/51)
- [x] Imports work (4/4 required commands)
- [x] windows_metrics.py NOT ported (deleted per r12)
- [x] No `# type: ignore`, bare `except`, empty catch
- [x] No `safe_mode` references

### Caveats

- Prometheus metrics are defined but require `prometheus_client` to be installed (currently installed in .venv).
- Sentry init requires `sentry_sdk` + DSN env var -- fail-soft without both.
- `guinevere/http/` NOT touched (W4 owns it). Receiver exposes `SurveillanceReceiver.router` as a `APIRouter` for W4 to mount later.
- The `test_consumer_process_event_no_consent` test checks source code for `check_consent`/`consent_gate`/`consent_status` rather than `"consent"` as a substring, because the sentry module legitimately contains `"consent-revocation"` as a DROP_EVENT_PATHS entry.

### Footer

Wave: W5 (M16 Surveillance + Observability)
Operator: fazulfim
Date: 2026-06-29
Branch: feat/p24-hermes-fork
Verdict: PASS

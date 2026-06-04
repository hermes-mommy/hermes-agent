# D05: Consent Gate Audit Report -- Fail-Closed, Cache, Revocation, Ledger

| Field | Value |
|---|---|
| Audit ID | D05 |
| Scope | Consent verification gate (`src/surveillance/consent_gate.py`) |
| Policy Reference | `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` |
| Date | 2026-06-03 |
| Auditor | Guinevere (consent compliance auditor) |
| Verdict | **NEEDS REVIEW** (1 CRITICAL finding, 1 MEDIUM finding) |

---

## 1. Fail-Closed Conditions -- 7-Step Decision Matrix

| # | Condition | Code Path | Verdict | Evidence |
|---|---|---|---|---|
| 1 | Unknown scope | Line 203-211: scope not in `VALID_SURVEILLANCE_SCOPES` -> `allowed=False` | **PASS** | `_BLOCK_UNKNOWN_SCOPE` returned without cache/DB access |
| 2 | Cache hit (positive) | Lines 216-218: cached `allowed=True` returned, no DB query | **PASS** | Design: cache reduces DB load; invalidation needed on revocation (see Section 4) |
| 3 | Cache hit (negative) | Lines 219-222: cached `allowed=False` returned, no DB query | **PASS** | Negative cache blocks without DB; expires in 300s |
| 4 | Cache miss + DB failure | Lines 229-238: `except Exception` -> `_BLOCK_DB_FAILURE` | **PASS** | Any `Exception` from `_query_ledger` triggers fail-closed; tested with ConnectionError, TimeoutError, OSError |
| 5 | Cache miss + no ledger entry | Lines 241-251: `_query_ledger` returns `None` -> `_BLOCK_NO_LEDGER` | **PASS** | "never consented" -> block + negative cache written |
| 6 | Cache miss + WITHDRAWN | Lines 254-264: status `WITHDRAWN` -> `_BLOCK_WITHDRAWN` | **PASS** | Block + negative cache written with TTL 300s |
| 7 | Cache miss + PAUSED | Lines 267-277: status `PAUSED` -> `_BLOCK_PAUSED` | **PASS** | Block + negative cache written with TTL 300s |
| -- | Redis unavailable (cache only) | Lines 325-327: `_try_cache_lookup` catches Exception -> returns `None` | **PASS** | Falls through to DB; does NOT fail-closed on Redis error alone (correct per policy) |
| -- | Redis + DB both unavailable | Tested: `TestCheckConsentRedisUnavailable.test_redis_and_db_both_fail_fail_closed` | **PASS** | Returns `_BLOCK_DB_FAILURE` |

**Fail-closed verdict: ALL 7 conditions PASS.** The gate correctly blocks on every uncertain state. All error paths return `allowed=False`.

**Test coverage:** Tests explicitly verify ConnectionError, TimeoutError, and OSError trigger fail-closed. Redis+DB dual failure tested. No empty except blocks found.

---

## 2. Cache Behavior

| Property | Specification | Code | Verdict |
|---|---|---|---|
| TTL | 300 seconds | `CACHE_TTL_SECONDS = 300` (line 46) | **PASS** |
| Key prefix | `consent:surveillance:` | `CACHE_KEY_PREFIX = "consent:surveillance:"` (line 43) | **PASS** |
| DB number | DB2 (surveillance namespace) | `db=2` in `_get_redis()` (line 134) | **PASS** |
| Cache key format | `{prefix}{scope}` | `cache_key = f"{CACHE_KEY_PREFIX}{scope}"` (line 214) | **PASS** |
| Cache value format | JSON: `{allowed, status, scope, reason, checked_at}` | Lines 358-364 in `_cache_result()` | **PASS** |
| Cache write policy | Best-effort (failures logged, not propagated) | Lines 370-371: `except Exception: logger.exception(...)` | **PASS** |
| Cache read policy | Corrupt JSON / Redis error -> fall through to DB | Lines 325-349 in `_try_cache_lookup()` | **PASS** |
| Deserialisation | Uses `json.loads`, handles `JSONDecodeError/KeyError/ValueError/TypeError` | Lines 347-349 | **PASS** |
| Port | 6380 | `port=6380` in `_get_redis()` (line 133) | **PASS** |

**Positive cache entries:** Only ACTIVE consent is cached with `allowed=True` (line 288). This is the TTL=300s entry that becomes stale on revocation.

**Negative cache entries:** WITHDRAWN, PAUSED, and no-ledger results are cached with `allowed=False` (lines 250, 263, 276). These also expire in 300s.

**Cache verdict: PASS** -- all technical parameters match specification.

---

## 3. Invalidation Caller Scan (CRITICAL)

### 3.1 The `invalidate_cache()` function

Defined at `src/surveillance/consent_gate.py` line 292:

```python
async def invalidate_cache(scope: str) -> None:
    cache_key = f"{CACHE_KEY_PREFIX}{scope}"
    redis_client = _get_redis()
    try:
        await redis_client.delete(cache_key)
        logger.info("consent_cache_invalidated", scope=scope, cache_key=cache_key)
    except Exception:
        logger.exception("consent_cache_invalidation_failed", scope=scope)
```

The function exists, is exported via `__all__` (line 420), and is re-exported via `src/surveillance/__init__.py` (lines 16, 76). It correctly deletes the cache key and survives Redis errors without propagating exceptions.

### 3.2 Caller Scan Results

```
grep 'invalidate_cache' -- src/
```

Results: **2 files** reference `invalidate_cache`:
- `src/surveillance/__init__.py` -- re-export only (lines 16, 76)
- `src/surveillance/consent_gate.py` -- definition (line 292) and `__all__` export (line 420)

**Verdict: CRITICAL FAILURE**

`invalidate_cache()` has **ZERO production callers**. No consumer, no revocation handler, no event processor, no safe-word handler, no Pub/Sub subscriber -- nothing calls it.

### 3.3 Impact

| Scenario | Behavior Without Invalidation | Consequence |
|---|---|---|
| Faiz withdraws `surveillance.location` consent | Consent ledger updated to WITHDRAWN; cache still has TTL <= 300s `allowed=True` | Consumer continues ingesting location data for up to 300 seconds after withdrawal |
| Faiz pauses `surveillance.clipboard` | Ledger shows PAUSED; cache shows `allowed=True` | Clipboard data ingested for up to 300s |
| Consent restored after pause | Ledger shows ACTIVE; cache may still show PAUSED (negative) | Legitimate data blocked for up to 300s after restoration |

**Severity:** Per ConsentRevocationPolicy Section 16, "Consent cache allows stale scope" is a SEV2 incident. "Action proceeds with revoked consent" is SEV1. The absence of invalidation callers means ANY consent change has up to a 300-second window of incorrect behavior.

### 3.4 Evidence File Inaccuracy

`docs/setup-evidence/P7/consent-gate-20260602.md` line 64 states:

> "Redis cache invalidated via `consent:invalidate` Pub/Sub"

This is **not implemented**. No Pub/Sub channel `consent:invalidate` exists in the codebase. The evidence file contains a claim that does not match implementation reality.

### 3.5 Fix Required

`invalidate_cache()` must be called from at minimum:
1. **Consent revocation/withdrawal handler** -- when ledger records WITHDRAWN/PAUSED
2. **Consent restoration handler** -- when ledger records ACTIVE after WITHDRAWN/PAUSED
3. **Safe-word handler** -- when safe word triggers surveillance pause

---

## 4. Consent Check Frequency

### 4.1 Consumer Code Analysis

In `src/surveillance/consumer.py`, `process_event()` method (line 151):

```
Line 177: consent_result = await check_consent(scope)    # <-- ONCE
Line 187: if not consent_result.allowed: return False    # <-- drop
Line 217: for attempt in range(1, max_retries + 1):      # <-- retry loop
Line 219:     await self._store_event(...)               # <-- NO re-check
```

### 4.2 Verdict

| Property | Finding | Verdict |
|---|---|---|
| Consent checked once per event | Line 177, called exactly once before pipeline | **CONFIRMED** |
| Consent re-checked before DB retries | NOT checked inside retry loop (lines 217-244) | **NOT IMPLEMENTED** |
| Consent checked after DB retry failure | Event dropped, consent not re-evaluated | **ACCEPTABLE** (retry is for transient DB issues, not consent changes) |

**Verdict: PASS (designed behavior).** The consent check happens once at the start of `process_event()`. This is the correct design -- the consent gate determines whether the event should be ingested at all. DB retries exist for transient storage failures, not consent state changes. Re-checking consent during a sub-second retry loop would add overhead without meaningful safety benefit.

The research finding "consumer checks consent ONCE per event, not before each DB retry attempt" is confirmed and is not a defect.

---

## 5. Safe Word Interaction

### 5.1 Analysis

`consent_gate.py` has **zero references** to safe word, HARD STOP, or distress protocols. The gate is a pure consent-verification layer that checks the `consent.consent_ledger` table exclusively.

The safe word system operates independently:
- `HARD STOP` triggers persona neutralization (PersonaSafetyPolicy Section 7.2)
- Surveillance ingestion via the consumer continues running
- Each event still passes through `check_consent()` which queries the immutable ledger
- Safe word does NOT modify the consent ledger and does NOT call `check_consent()`

### 5.2 Verdict

**PASS: safe word does NOT disable consent checks.** The two systems are correctly decoupled:

| System | What it affects | What it does NOT affect |
|---|---|---|
| Safe word (`HARD STOP`) | Persona behavior, confrontation, escalation | Consent ledger, surveillance ingestion consent checks |
| Consent gate (`check_consent`) | Whether events are ingested | Persona behavior |

This is correct per ConsentRevocationPolicy Section 8 which states safe word triggers consent withdrawal for "persona escalation, punishment, yandere behavior, surveillance-derived confrontation" -- it does not require immediate shutdown of all surveillance ingestion.

**Note:** The policy does require that the safe word creates surveillance-pause evidence (`evidence/consent/revocations/`). This is out of scope for the consent gate audit but should be verified separately.

---

## 6. Silent Reactivation Prevention

### 6.1 Analysis

ConsentRevocationPolicy Section 10.3: "Sensitive scopes must not reactivate silently after safe-word, revocation, crisis, distress, incident, or consent uncertainty. Restoration must require explicit Faiz readiness or approval matching the scope."

Code analysis of `consent_gate.py`:

| Mechanism | How it prevents silent reactivation |
|---|---|
| Ledger is source of truth | `_query_ledger()` returns the most recent `consent_ledger` entry ordered by `granted_at DESC LIMIT 1` |
| WITHDRAWN stays WITHDRAWN | Code has no auto-restore path; WITHDRAWN in ledger always returns BLOCK |
| No time-based auto-restore | No expiry check, no scheduled restoration, no state machine transitions |
| Cache does not override ledger | Cache TTL 300s ensures eventual re-query of immutable ledger |
| No hidden bypass | No secret flag, no admin override, no emergency bypass in consent_gate.py |

### 6.2 Verdict

**PASS.** The code design makes silent reactivation impossible at the consent-gate level. The only way to restore WITHDRAWN/PAUSED consent is to insert a new `CONSENT_RESTORED` or `CONSENT_GIVEN` event into the `consent.consent_ledger` table.

**Caveat related to Section 3:** While the gate itself cannot silently re-activate, the lack of cache invalidation means that a legitimate restoration (new ACTIVE ledger entry) will also be delayed up to 300s if a negative cache entry (WITHDRAWN/PAUSED) is still live. This is a correctness issue, not a safety issue -- it delays reactivation rather than enabling it.

---

## 7. Overall Verdict

| Category | Verdict | Notes |
|---|---|---|
| Fail-closed conditions (7 steps) | **PASS** | All 7 conditions return `allowed=False`; tested with ConnectionError, TimeoutError, OSError |
| Cache TTL (300s) | **PASS** | `CACHE_TTL_SECONDS = 300` |
| Cache key prefix | **PASS** | `consent:surveillance:` |
| Redis DB2 | **PASS** | `db=2` on port 6380 |
| Cache value format | **PASS** | JSON with allowed, status, scope, reason, checked_at |
| Cache invalidation function | **PASS** | `invalidate_cache()` exists, correct implementation |
| Cache invalidation callers | **FAIL (CRITICAL)** | ZERO production callers; consent changes delayed up to 300s |
| Consent check frequency | **PASS** | Once per event, correct design for this purpose |
| Safe word interaction | **PASS** | Safe word does NOT disable consent checks (independent systems) |
| Silent reactivation prevention | **PASS** | No auto-restore logic; WITHDRAWN stays WITHDRAWN |
| Evidence file accuracy | **FAIL (MEDIUM)** | `consent-gate-20260602.md` claims Pub/Sub invalidation that does not exist |
| Test coverage | **PASS** | 744 lines, comprehensive fail-closed coverage, source code pattern verification |
| No anti-patterns | **PASS** | No bare except, no type:ignore, no empty except:pass |

### 7.1 Final Verdict: **NEEDS REVIEW**

The consent gate implementation is **technically sound** with correct fail-closed behavior, well-structured cache, and comprehensive test coverage. However, the **absence of any production caller for `invalidate_cache()`** means that consent revocation, withdrawal, pause, and restoration are all delayed by up to 300 seconds. This is a **SEV1-level gap** per ConsentRevocationPolicy Section 16 ("Action proceeds with revoked consent" = SEV1).

### 7.2 Blocking Issues

| ID | Severity | Description | Required Fix |
|---|---|---|---|
| D05-CRIT-01 | CRITICAL | `invalidate_cache()` has zero production callers | Wire `invalidate_cache()` into the consent revocation handler, consent restoration handler, and safe-word surveillance-pause handler |
| D05-MED-01 | MEDIUM | Evidence file `consent-gate-20260602.md` line 64 claims Pub/Sub invalidation that does not exist | Update evidence file to reflect actual implementation or implement the claimed Pub/Sub pattern |

### 7.3 Recommendation

1. **Immediate (before production):** Add `invalidate_cache()` calls to the consent revocation/restoration handler(s)
2. **Recommended:** Implement a Redis Pub/Sub channel (`consent:invalidate`) as described in the evidence file, with the consumer subscribing for real-time cache invalidation
3. **Recommended:** Add a `consent_cache_staleness_seconds` Prometheus metric to monitor the gap between ledger change and cache invalidation

---

## Appendix A. Source Files Audited

| File | Lines | Purpose |
|---|---|---|
| `src/surveillance/consent_gate.py` | 423 | Consent verification gate with 7-step decision matrix |
| `src/surveillance/consumer.py` | 447 | Async event consumer with consent check integration |
| `tests/surveillance/test_consent_gate.py` | 744 | Comprehensive unit tests (fail-closed, cache, invalidation) |
| `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | 453 | Normative consent and revocation policy |
| `docs/setup-evidence/P7/consent-gate-20260602.md` | 71 | P7 consent gate evidence (contains inaccuracy) |

## Appendix B. grep Results

```
$ grep 'invalidate_cache' -- src/
src/surveillance/__init__.py:
  16: invalidate_cache,
  76: "invalidate_cache",
src/surveillance/consent_gate.py:
  292: async def invalidate_cache(scope: str) -> None:
  420: "invalidate_cache",
```

No other files in `src/` reference `invalidate_cache`. Zero production callers confirmed.

---

*Audit completed 2026-06-03. Verdict: NEEDS REVIEW. One CRITICAL finding (D05-CRIT-01), one MEDIUM finding (D05-MED-01). Gate implementation is correct but incomplete without invalidation wiring.*
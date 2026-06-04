# D08 Architecture Consistency Audit -- Surveillance Subsystem

| Field | Value |
|---|---|
| Audit ID | D08 |
| Scope | `src/surveillance/` (14 modules) |
| Date | 2026-06-03 |
| Auditor | Architecture Consistency Auditor |
| Verdict | **NEEDS REVIEW** |

---

## 1. Request Flow Verification

### 1.1 Ingestion Path (HTTP Layer)

```
POST /surveillance/events
  |
  v
router.receive_event() [async, FastAPI endpoint]
  |
  +-- Depends(verify_hmac)  [FastAPI dependency injection]
  |     |
  |     +-- Step 1: validate_timestamp()  [pure computation, no I/O]
  |     +-- Step 2: check_nonce()         [Redis SET NX EX, async]
  |     +-- Step 3: HMAC-SHA256 verify    [hmac.compare_digest, sync but O(1)]
  |     +-- get_hmac_secret()             [cached after first call]
  |
  +-- Returns SurveillanceEventResponse (202 Accepted)
```

**Verdict: PASS** -- The HTTP ingestion path matches the expected flow. Timestamp validation runs first (free), then nonce deduplication (Redis), then HMAC verification. This is the correct order for cost-optimization and fail-fast behavior.

### 1.2 Consumer Pipeline (Async Worker)

```
SurveillanceConsumer.run()
  |
  +-- _drain_and_process()
        |
        +-- buffer.pop_events()  [Redis RPUSH/LRANGE+LTRIM, async]
        |
        +-- For each event:
              |
              +-- Step 1: _map_event_to_scope()      [pure dict lookup]
              +-- Step 2: check_consent(scope)        [Redis cache + DB fallback, async]
              +-- Step 3: classify_event(event_type)  [pure computation, sync]
              +-- Step 4: scan_text(text)             [regex + entropy, clipboard only]
              +-- Step 5: _store_event() with retry   [DB write, async, max 3 attempts]
```

**Verdict: PASS** -- The consumer pipeline matches the documented order: map scope, consent gate (fail-closed), classify, secret scan, store with retry. Pipeline steps are sequential per event, batch-level processing is sequential (not parallel), which is correct for consent-gated ingestion.

### 1.3 Router Buffering Gap

The router (`router.py`) currently returns 202 immediately after HMAC verification. It does NOT push events to the Redis buffer. The consumer (`consumer.py`) expects events to be in the Redis buffer. There is no code in `router.py` that calls `buffer.push_event()`.

**Verdict: NEEDS REVIEW** -- The HTTP endpoint and the consumer pipeline are not wired together at the router level. Either the router should push to the buffer, or there should be documentation explaining that buffering happens through a separate integration path. This is a functional integration gap, not an architectural inconsistency per se, but it affects request flow completeness.

---

## 2. Protocol Pattern Usage

| Protocol | Module | Line | Purpose | `@runtime_checkable` |
|---|---|---|---|---|
| `SurveillanceBuffer` | `redis_buffer.py` | 35 | Abstract buffering interface for DI/testing | Yes |
| `ConsentChecker` | `consent_gate.py` | 103 | Abstract consent verification backend | Yes |
| `_AsyncDBSession` | `consumer.py` | 73 | Minimal async SQLAlchemy session protocol | Yes |
| `_AsyncDBSession` | `consent_gate.py` | 111 | Duplicate definition for consent DB queries | Yes |

**Observations:**

- All Protocol classes use `@runtime_checkable` -- correct for `isinstance()` checks.
- `SurveillanceBuffer` is the primary injection point for `SurveillanceConsumer.__init__()`.
- `_AsyncDBSession` is defined independently in both `consumer.py` and `consent_gate.py`. These are structurally similar but not identical (consumer version includes `params: dict[str, Any]` while consent version uses `params: dict[str, str]`). This is a minor inconsistency -- both should share a single canonical Protocol definition.
- `ConsentChecker` Protocol in `consent_gate.py` is not referenced externally by any surveillance module; it appears to be a future extension point for alternative consent backends.

**Verdict: PASS** -- Protocol usage is sound. The `_AsyncDBSession` duplication is a minor maintenance concern (NEEDS REVIEW item), not an architectural violation.

---

## 3. Async Consistency Check

| Module | Async Functions | Blocking Calls Found | Verdict |
|---|---|---|---|
| `router.py` | `receive_event` | None | PASS |
| `auth.py` | `verify_hmac` | `get_hmac_secret()` (sync, subprocess on first call) | SEE NOTE |
| `replay.py` | `validate_timestamp`, `check_nonce` | None (`time` import is `time.time()` only) | PASS |
| `redis_buffer.py` | `push_event`, `pop_events`, `buffer_size`, `close` | None (uses `redis.asyncio`) | PASS |
| `consent_gate.py` | `check_consent`, `invalidate_cache`, `_try_cache_lookup`, `_cache_result`, `_query_ledger` | None (uses `redis.asyncio`) | PASS |
| `consumer.py` | `run`, `stop`, `process_event`, `_drain_and_process`, `_store_event`, `main` | None (uses `asyncio.sleep`) | PASS |
| `timescale.py` | `ingest_batch`, `ingest_single`, `get_event_count`, `get_last_event`, `_write_ingestion_log` | None | PASS |
| `classification.py` | None (all sync, pure logic) | N/A | PASS |
| `secret_scanner.py` | None (all sync, regex + entropy) | N/A | PASS |
| `safe_mode.py` | None (all sync, regex + state check) | N/A | PASS |
| `models.py` | None (Pydantic models) | N/A | PASS |
| `secrets.py` | None (all sync) | `subprocess.run()` in `_decrypt_sops_secret()` | SEE NOTE |
| `retention.py` | None (all sync, pure computation) | N/A | PASS |

### 3.1 Blocking Call in Async Path: `get_hmac_secret()`

`auth.verify_hmac()` is an async FastAPI dependency. It calls `get_hmac_secret()` which is synchronous. On first call (cache miss), `get_hmac_secret()` invokes `subprocess.run(["sops", "--decrypt", ...])` -- a blocking OS-level call on the event loop thread.

**Mitigation**: The result is cached for process lifetime (`_cached_secret`). After first call, `get_hmac_secret()` returns immediately. The blocking only occurs once per process startup.

**Verdict: NEEDS REVIEW** -- While the caching mitigates repeated blocking, the first HMAC verification request will block the event loop during SOPS decryption. Recommended fix: wrap the first-call decryption in `asyncio.to_thread()` or pre-warm the cache at startup before the event loop accepts requests. This is a low-severity issue given the one-time nature.

---

## 4. Circular Import Scan

### 4.1 Internal Dependency Graph

```
__init__.py --> all modules (one-way re-export)
router.py   --> auth.py, models.py
auth.py     --> replay.py, secrets.py
consumer.py --> classification.py, consent_gate.py, redis_buffer.py, secret_scanner.py
timescale.py --> src.memory.models (external)
safe_mode.py --> src.core.services.hard_stop_handler (external)

Leaf modules (no intra-surveillance imports):
  classification.py, models.py, redis_buffer.py, replay.py,
  secret_scanner.py, secrets.py, retention.py
```

### 4.2 Verification

- No module imports a module that imports it back.
- All intra-surveillance imports flow downward: router -> auth -> replay/secrets, consumer -> classification/consent_gate/redis_buffer/secret_scanner.
- Leaf modules have zero intra-surveillance imports.
- `__init__.py` imports from all modules but no module imports `__init__.py`.

**Verdict: PASS** -- No circular imports detected. The dependency graph is a clean DAG.

---

## 5. Dependency Direction

### 5.1 Surveillance Depends on Core

| Import | Source | Target | Direction |
|---|---|---|---|
| `from src.core.services.hard_stop_handler import SafetyState` | `safe_mode.py:23` | `src.core` | surveillance -> core (correct) |

### 5.2 Surveillance Depends on Memory

| Import | Source | Target | Direction |
|---|---|---|---|
| `from src.memory.models import IngestionLog, SurveillanceEvents` | `timescale.py:30` | `src.memory` | surveillance -> memory (correct) |

### 5.3 Reverse Dependency Check

| Check | Result |
|---|---|
| `src/memory/` imports from `src/surveillance/` | **None found** (correct) |
| `src/core/` imports from `src/surveillance/` | `src/core/main.py:139` imports `surveillance_router` |

### 5.4 Analysis of `src/core/main.py` Import

`src/core/main.py` imports `surveillance_router` from `src/surveillance.router`. This is the FastAPI application composition layer -- mounting routers onto the app instance. This is correct architectural layering: the app entry point assembles all routers, not a model-level coupling. The core business logic and models do not depend on surveillance internals.

**Verdict: PASS** -- Dependency direction is correct. Surveillance depends on core (SafetyState) and memory (DB models). The reverse import in `core/main.py` is app-level router composition, not a model or logic dependency.

---

## 6. `__init__.py` Export Completeness

### 6.1 Modules Covered

All 13 modules are imported in `__init__.py`:
`auth`, `classification`, `consent_gate`, `consumer`, `models`, `redis_buffer`, `replay`, `retention`, `router`, `safe_mode`, `secret_scanner`, `secrets`, `timescale`.

### 6.2 `__all__` Contents

37 entries in `__all__`. Covers classes, functions, constants, and the router.

### 6.3 Private Symbol Leakage

| Symbol | Module | Issue |
|---|---|---|
| `_map_event_to_scope` | `consumer.py` | Prefixed with underscore (private) but exported in `__all__`. Leaks an internal mapping helper. |

### 6.4 Missing Exports

| Symbol | Module | Status |
|---|---|---|
| `check_message_safety` | `safe_mode.py` | Method on `SurveillanceSafeModeGuard` class, not a standalone function. Accessible via the exported class. Not a standalone export gap. |
| `PROHIBITED_USE_PATTERNS` | `safe_mode.py` | Module-level constant not exported. Internal detail, acceptable to omit. |
| `_decrypt_sops_secret` | `secrets.py` | Private function, correctly not exported. |
| `_clear_cache` | `secrets.py` | Test-only helper, correctly not exported. |

### 6.5 Naming Collision: `get_retention_days`

| Function | Module | Signature | Purpose |
|---|---|---|---|
| `get_retention_days` | `classification.py:218` | `(retention_class: str) -> int` | Maps classification retention class string to days |
| `get_retention_days` | `retention.py:82` | `(tier: RetentionTier) -> int` | Maps RetentionTier enum to days |

`__init__.py` handles this by importing:
- `get_retention_days` from `classification.py` directly (exported as `get_retention_days`)
- `get_retention_days` from `retention.py` aliased as `get_tier_retention_days` (exported as `get_tier_retention_days`)

**Verdict: NEEDS REVIEW** -- The naming collision is a maintainability risk. Two functions with the same name but different parameter types (`str` vs `RetentionTier`) and different semantics create confusion. Recommended fix: rename `classification.get_retention_days` to `get_classification_retention_days` or similar to disambiguate.

---

## 7. Summary of Findings

### PASS Items

| # | Check | Status |
|---|---|---|
| 1 | Request flow order (HTTP layer) | PASS |
| 2 | Consumer pipeline order | PASS |
| 3 | Protocol pattern usage (design) | PASS |
| 4 | Circular import scan | PASS |
| 5 | Dependency direction | PASS |
| 6 | Async Redis usage (`redis.asyncio`) | PASS |
| 7 | No `time.sleep` in async paths | PASS |
| 8 | No `requests.` (sync HTTP) in async paths | PASS |
| 9 | `__init__.py` covers all 13 modules | PASS |

### NEEDS REVIEW Items

| # | Finding | Severity | Module | Recommendation |
|---|---|---|---|---|
| NR-1 | Router does not push events to Redis buffer | Medium | `router.py` | Wire `buffer.push_event()` into the endpoint or document the integration path |
| NR-2 | `get_hmac_secret()` blocks event loop on first call | Low | `secrets.py` / `auth.py` | Wrap in `asyncio.to_thread()` or pre-warm cache at startup |
| NR-3 | `get_retention_days` naming collision | Low | `classification.py` / `retention.py` | Rename one function to disambiguate |
| NR-4 | `_AsyncDBSession` Protocol defined twice with minor differences | Low | `consumer.py` / `consent_gate.py` | Extract to a shared module |
| NR-5 | `_map_event_to_scope` (private) exported in `__all__` | Low | `__init__.py` | Remove from `__all__` or rename without underscore prefix |
| NR-6 | `consumer.main()` DB session factory raises `NotImplementedError` | Medium | `consumer.py:409` | Documented production wiring gap; needs TimescaleDB session integration |

---

## 8. Overall Verdict

**NEEDS REVIEW**

The surveillance subsystem architecture is fundamentally sound. Request flow, Protocol patterns, async consistency, dependency direction, and circular import checks all pass. Six items require review: the router-to-buffer integration gap (NR-1) and the production DB session wiring gap (NR-6) are medium-severity functional gaps. The remaining four items (NR-2 through NR-5) are low-severity maintainability and hygiene concerns.

None of the findings are architectural violations that would warrant a FAIL verdict. The subsystem is structurally consistent and ready for integration work to close the identified gaps.

---

## Appendix: Module Inventory

| # | Module | Lines | Async | External Deps |
|---|---|---|---|---|
| 1 | `__init__.py` | 86 | No | All surveillance modules |
| 2 | `router.py` | 54 | Yes | FastAPI |
| 3 | `auth.py` | 91 | Yes | FastAPI, hashlib, hmac |
| 4 | `replay.py` | 164 | Yes | redis.asyncio, FastAPI |
| 5 | `secrets.py` | 128 | No | subprocess, yaml, pathlib |
| 6 | `models.py` | 71 | No | Pydantic v2 |
| 7 | `redis_buffer.py` | 206 | Yes | redis.asyncio, Protocol |
| 8 | `consent_gate.py` | 423 | Yes | redis.asyncio, Protocol |
| 9 | `classification.py` | 229 | No | structlog, enum |
| 10 | `secret_scanner.py` | 318 | No | math, re, Counter |
| 11 | `consumer.py` | 447 | Yes | asyncio, signal, Protocol |
| 12 | `safe_mode.py` | 216 | No | src.core (SafetyState) |
| 13 | `timescale.py` | 392 | Yes | SQLAlchemy, src.memory.models |
| 14 | `retention.py` | 157 | No | datetime, enum |

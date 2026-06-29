# R12: Surveillance + Observability — Domain Research

**Generated**: 2026-06-29  
**Method**: Direct file reads of all 14 source files in `src/surveillance/`, 3 files in `src/observability/`, `infrastructure-patterns-research.md`, P24 plan M16 section, and cross-reference grep of all imports/consumers.  
**Verdict**: PASS (with 3 risks, all mitigable)

---

## 1. Source Inventory

### 1.1 src/surveillance/ — 14 source files

| # | File | Lines | Purpose | Disposition |
|---|------|-------|---------|-------------|
| 1 | `__init__.py` | 87 | Re-exports all public symbols, imports consent_gate | DELETE (rebuilt as `guinevere/surveillance/__init__.py`) |
| 2 | `auth.py` | 91 | HMAC-SHA256 verification as FastAPI dependency; reads X-Signature, X-Timestamp, X-Nonce headers | PORT to `receiver.py` |
| 3 | `classification.py` | 233 | DataClassification enum (Internal/Confidential/Restricted/Critical), event-type mapping, retention days | PORT to `receiver.py` |
| 4 | `models.py` | 71 | Pydantic v2 request/response models: SurveillanceEventRequest, SurveillanceEventResponse, ErrorResponse | PORT to `receiver.py` |
| 5 | `redis_buffer.py` | 206 | Async Redis DB2 buffer (RPUSH/LRANGE+LTRIM), 300s TTL, protocol-based design | PORT to `buffer.py` |
| 6 | `replay.py` | 164 | Timestamp window validation (300s), atomic nonce dedup via Redis SET NX EX (660s TTL) | PORT to `receiver.py` |
| 7 | `retention.py` | 157 | 3-tier retention (raw 7d / aggregated 90d / summary 365d), TimescaleDB chunk/compression constants | PORT to `storage.py` |
| 8 | `router.py` | 71 | FastAPI POST /surveillance/events endpoint, HMAC auth dependency, best-effort Redis push | PORT to `receiver.py` |
| 9 | `safe_mode.py` | 218 | Confrontation gate tied to HARD STOP state; imports `SafetyState` from `core.services.hard_stop_handler` | DELETE (per M16 plan) |
| 10 | `secret_scanner.py` | 319 | 16 regex secret patterns + Shannon entropy (>=4.5) detection, clipboard redaction | PORT to `receiver.py` |
| 11 | `secrets.py` | 129 | HMAC secret loader: env var first, SOPS decrypt fallback, module-level cache | PORT to `receiver.py` |
| 12 | `timescale.py` | 393 | TimescaleDB batch/single ingest via SQLAlchemy, IngestionLog audit trail, uuid5 device resolution | PORT to `storage.py` |
| 13 | `consent_gate.py` | 423 | Fail-closed consent verification against `consent.consent_ledger` table, Redis DB2 cache (300s TTL) | DELETE (per ADR-062, M16) |
| 14 | `consumer.py` | 463 | Background worker: drains Redis buffer, runs consent->classify->scan->store pipeline with retry | PORT to `buffer.py` (consent steps removed) |

### 1.2 src/observability/ — 3 source files

| # | File | Lines | Purpose | Disposition |
|---|------|-------|---------|-------------|
| 1 | `__init__.py` | 5 | Exports `init_sentry` | DELETE (rebuilt as `guinevere/observability/__init__.py`) |
| 2 | `sentry_integration.py` | 240 | Sentry SDK init with PII scrubber (before_send/before_breadcrumb), 6 redaction patterns, 6 drop-event paths | PORT to `sentry.py` |
| 3 | `windows_metrics.py` | 207 | Prometheus gauges/counters/histograms for Windows daemon (connection, events, reconnects, latency) | DELETE (Linux VPS only per M16 plan) |

### 1.3 infrastructure-patterns-research.md — relevant sections

| Section | Content | Relevance to M16 |
|---------|---------|-------------------|
| Section 3: Circuit Breakers | 6 breakers (cost/loop/hallucination/emotion/dream/subagent), asyncio base class | M17, not M16; referenced for Prometheus metric families |
| Section 5: FastAPI Embedded | Lifespan pattern, health endpoints, Prometheus /metrics endpoint | Provides Prometheus exposition pattern; already exists in `src/core/main.py:910` |

---

## 2. Disposition Analysis

### 2.1 Files to DELETE (2 files, 641 lines)

**`src/surveillance/consent_gate.py`** (423 lines)

Why delete: ADR-062 mandates "Surveillance is Hermes-controlled, not operator-controlled." The consent gate performs fail-closed checks against a `consent.consent_ledger` table (line 398: `SELECT status FROM consent.consent_ledger WHERE scope = :scope`). This is the old operator-controlled paradigm. In the Hermes runtime, Hermes owns all surveillance decisions.

Evidence the plan is correct:
- `src/surveillance/consent_gate.py:179`: `async def check_consent(scope: str) -> ConsentCheckResult` -- the entire public API is a consent check
- `src/surveillance/consumer.py:39`: `from src.surveillance.consent_gate import check_consent` -- consumer imports it
- `src/surveillance/__init__.py:12-17`: re-exports ConsentCheckResult, ConsentStatus, check_consent, invalidate_cache

Impact of removal: The `consumer.py` pipeline calls `check_consent()` at line 177 as Step 2. This step and the consent scope mapping (lines 49-64) must be removed from the ported consumer. The `_store_event` method also writes `consent_status` into `extracted_facts` (line 322) -- this field should be removed or set to a fixed value.

**`src/surveillance/safe_mode.py`** (218 lines)

Why delete: Imports `SafetyState` from `src.core.services.hard_stop_handler` (line 23). HARD STOP is being removed in M2. The confrontation gate blocks actions like "confrontation", "blackmail", "punishment" (line 31-39) -- these are old paradigm concepts removed per ADR-062.

Evidence the plan is correct:
- `src/surveillance/safe_mode.py:23`: `from src.core.services.hard_stop_handler import SafetyState` -- hard dependency on HARD STOP
- `src/surveillance/safe_mode.py:88-94`: `SurveillanceSafeModeGuard.__init__` takes a `safety_state_getter` callable
- No production code imports safe_mode outside `__init__.py` (grep confirms only `src/surveillance/__init__.py:31` imports it)

### 2.2 Files to PORT (11 files -> 5 target files)

The 11 porting source files collapse into 5 target files as specified by M16:

**Target: `guinevere/surveillance/receiver.py` (~200 lines)**

Absorbs from:
- `auth.py` (91 lines) -- HMAC verification, signing string construction
- `classification.py` (233 lines) -- DataClassification enum, event type mapping
- `models.py` (71 lines) -- Pydantic v2 request/response models
- `replay.py` (164 lines) -- timestamp window, nonce dedup
- `router.py` (71 lines) -- FastAPI endpoint, Redis push
- `secret_scanner.py` (319 lines) -- secret detection/redaction
- `secrets.py` (129 lines) -- HMAC secret loader

Key changes required:
1. All `from src.surveillance.*` imports become `from guinevere.surveillance.*`
2. Remove consent_gate imports (none of these 7 files import consent_gate directly -- verified by grep)
3. The router endpoint signature stays the same: `POST /surveillance/events` with HMAC auth dependency
4. secret_scanner is clipboard-only; keep as a utility function within receiver.py

**Target: `guinevere/surveillance/buffer.py` (~150 lines)**

Absorbs from:
- `redis_buffer.py` (206 lines) -- SurveillanceBuffer protocol, RedisSurveillanceBuffer, create_buffer factory
- `consumer.py` (463 lines) -- SurveillanceConsumer background worker

Key changes required:
1. **CRITICAL**: Remove consent gate steps from consumer pipeline. Lines 39, 46-56, 172-195 must be deleted. The pipeline simplifies from 5 steps to 4:
   - ~~Step 1: Map event_type to consent scope~~ (REMOVE)
   - ~~Step 2: Check consent~~ (REMOVE)
   - Step 3 becomes Step 1: Classify event
   - Step 4 becomes Step 2: Scan clipboard for secrets
   - Step 5 becomes Step 3: Store with retry
2. Remove `_EVENT_SCOPE_MAP` dict (lines 49-54) and `_map_event_to_scope` function (lines 59-64)
3. Remove `_DEFAULT_SCOPE` (line 56)
4. In `_store_event`, remove `consent_status` from `extracted_facts` (line 322) or replace with a fixed `"hermes_controlled"` value
5. Remove consent-related log messages: `consumer_consent_check_failed`, `consumer_consent_denied_drop`

**Target: `guinevere/surveillance/storage.py` (~200 lines)**

Absorbs from:
- `retention.py` (157 lines) -- retention tier constants, calculation helpers
- `timescale.py` (393 lines) -- TimescaleDB batch ingest, IngestionLog audit

Key changes required:
1. Import path migration: `from src.memory.models import IngestionLog, SurveillanceEvents` (timescale.py:31) becomes `from guinevere.memory.models import ...` (when M6 is ported)
2. TimescaleDB + RLS: per infrastructure-patterns-research.md Section 1.5, revoke chunk access from app role to mitigate bug #7830
3. No consent-related changes needed (neither file imports consent_gate)

**Target: `guinevere/observability/sentry.py` (~100 lines)**

Absorbs from:
- `sentry_integration.py` (240 lines) -- Sentry SDK init, PII scrubber

Key changes required:
1. Import path only: no `src.surveillance.*` imports to change (verified: sentry_integration.py has zero cross-module imports)
2. The PII scrubber (6 REDACT_PATTERNS, 6 DROP_EVENT_PATHS) is self-contained and production-quality -- port as-is
3. `SEND_DEFAULT_PII = False` is BLOCKING requirement (line 23) -- preserve exactly

**Target: `guinevere/observability/metrics.py` (~200 lines)**

NEW file (no direct source file port). Replaces `windows_metrics.py` (DELETED) with agent-focused metrics.

Metric families to define (from M16 plan line 979):
- `agent_turns_total` -- Counter: total agent conversation turns
- `agent_tokens_total` -- Counter: total tokens consumed, label: `direction` (prompt/completion)
- `agent_cost_usd` -- Counter: cumulative LLM cost in USD
- `consciousness_thoughts_total` -- Counter: consciousness loop iterations
- `emotion_transitions_total` -- Counter: emotion state changes, label: `from_emotion`, `to_emotion`
- `subagent_spawned_total` -- Counter: sub-agent spawns, label: `agent_type`
- `memory_operations_total` -- Counter: memory read/write/search ops, label: `operation`

Pattern: follows existing `guinevere_` prefix convention from `src/core/main.py:862-876` (guinevere_requests_total, guinevere_request_duration_seconds, guinevere_health_check_failures_total).

Grafana: the `/metrics` Prometheus exposition endpoint already exists at `src/core/main.py:910-913`. The new metrics will be auto-scraped by Prometheus and available for Grafana dashboards without code changes.

---

## 3. Consent Gate Removal Impact Analysis

### 3.1 Downstream consumers of consent_gate

Grep found these code files importing from `src.surveillance.consent_gate`:

| File | Import | Impact |
|------|--------|--------|
| `src/surveillance/consumer.py:39` | `check_consent` | Must remove consent pipeline step (lines 172-195) |
| `src/surveillance/__init__.py:12-17` | 4 symbols | File is being deleted entirely (rebuilt) |
| `src/discord/cmd_surveillance_pause.py` | consent-related | File is being deleted in M13 |
| `src/discord/cmd_surveillance_status.py` | consent-related | File is being deleted in M13 |
| `src/hermes_plugins/commands_surveillance/` (3 files) | consent_pause/resume/status | Files being deleted in M8 |
| `tests/surveillance/test_consent_gate.py` | test file | Test file deleted with module |
| `tests/surveillance/test_consumer.py` | consent mocking | Test must be rewritten without consent |
| `tests/surveillance/test_e2e.py` | consent mocking | Test must be rewritten without consent |

### 3.2 Does consent gate removal break event ingest?

**No.** The event ingest path is:

1. `POST /surveillance/events` (router.py) -- HMAC auth -> Redis buffer push -> return 202
2. `SurveillanceConsumer.run()` (consumer.py) -- poll Redis -> process_event per event

The HMAC-authenticated endpoint (router.py) does NOT check consent. It validates HMAC signature, pushes to Redis, and returns 202 immediately (lines 29-71). The consent check happens later in the consumer pipeline (consumer.py:177).

After consent gate removal:
- The HMAC endpoint continues to accept events normally (no change)
- The consumer pipeline skips consent and processes all events (classify -> scan -> store)
- This is correct per ADR-062: surveillance is Hermes-controlled

### 3.3 Consent gate removal does NOT affect:

- `src/gmail/consent_manager.py` and `src/gmail/router.py` -- these have their own consent system for Gmail, not surveillance consent
- `src/consent/` (2 files) -- being deleted in M11, separate module
- Dev-workflow consent in AGENTS.md -- completely separate

---

## 4. Sentry Integration Analysis

### 4.1 PII Scrubber Quality

The existing `sentry_integration.py` has a thorough PII scrubber (lines 26-51):

**REDACT_PATTERNS** (6 patterns):
1. Safe words / kasih ruang / HARD STOP (line 31)
2. Surveillance / tasker_payload / android_event (line 32)
3. Intimate / emotional_memory / inner_journal (line 33)
4. API keys / secrets / tokens / passwords (line 34)
5. Email addresses (line 35)
6. Credit card numbers (line 36)

**DROP_EVENT_PATHS** (6 categories):
1. persona-safety
2. surveillance-raw
3. consent-revocation
4. hard-stop
5. distress-protocol
6. crisis-handling

**Post-port cleanup**: After consent gate removal, the "consent-revocation" drop path (line 44) can be kept for safety (it drops events that accidentally reference consent revocation) or removed. Recommendation: KEEP -- it costs nothing and provides defense-in-depth.

### 4.2 Sentry Initialization

`init_sentry()` (line 187-239):
- DSN from `SENTRY_DSN` env var
- `send_default_pii=False` (BLOCKING, line 23)
- `traces_sample_rate=0.1` (10% sampling)
- FastAPI + Starlette integrations
- Graceful degradation: returns False if DSN missing (line 202)

### 4.3 Integration Point

`src/core/main.py:9` imports `from src.observability import init_sentry` and calls it at line 245. After port, this becomes `from guinevere.observability import init_sentry`. The call signature is unchanged.

---

## 5. Prometheus Metrics Analysis

### 5.1 Existing Metrics Infrastructure

`src/core/main.py:854-913` already has:
- `guinevere_requests_total` (Counter, labels: method/endpoint/status)
- `guinevere_request_duration_seconds` (Histogram, labels: method/endpoint)
- `guinevere_health_check_failures_total` (Counter, labels: component/check)
- `/metrics` endpoint returning `generate_latest()`
- `_PrometheusMiddleware` for automatic HTTP request tracking

### 5.2 Windows Metrics Being Deleted

`src/observability/windows_metrics.py` defines 5 metric families:
- `guinevere_windows_connected` (Gauge)
- `guinevere_windows_events_received_total` (Counter, label: event_type)
- `guinevere_windows_events_dropped_total` (Counter, label: reason)
- `guinevere_windows_reconnects_total` (Counter)
- `guinevere_windows_command_latency_seconds` (Histogram, label: command)

These are Windows-daemon-specific. M16 plan says "Windows metrics removed (Linux VPS only)." The new `metrics.py` replaces these with agent-focused metrics.

### 5.3 New Agent Metrics (from M16 plan + infrastructure-patterns-research.md)

The M16 plan (line 979) specifies: `agent_turns_total`, `agent_tokens_total`, `agent_cost_usd`, `consciousness_thoughts_total`, `emotion_transitions_total`, `subagent_spawned_total`, `memory_operations_total`.

These cover the domains mentioned in the task prompt: cost, thoughts, dreams (consciousness loop), subagents, emotions, memory.

Grafana dashboards will consume these via the existing `/metrics` Prometheus endpoint.

---

## 6. Cross-Cutting Concerns

### 6.1 Import Path Migration

All 11 ported files use `from src.surveillance.*` imports. The `__init__.py` is the heaviest importer (lines 5-46, 13 import statements). These all become `from guinevere.surveillance.*`.

External files that import surveillance:
- `src/core/main.py:315-316` imports `SurveillanceConsumer` and `RedisSurveillanceBuffer`
- `src/core/main.py:1050` imports `surveillance_router`
- These become `from guinevere.surveillance.*` after port

### 6.2 External Dependencies (unchanged)

| Package | Usage | Files |
|---------|-------|-------|
| `redis.asyncio` | Buffer, nonce dedup | redis_buffer.py, replay.py, consent_gate.py |
| `prometheus_client` | Counter, Histogram, Gauge | windows_metrics.py (deleted), core/main.py |
| `sentry_sdk` | Error tracking | sentry_integration.py |
| `structlog` | Structured logging | All 17 files |
| `pydantic` | Request/response models | models.py |
| `sqlalchemy` | TimescaleDB writes | timescale.py, consumer.py |
| `fastapi` | Webhook endpoint, HMAC dependency | router.py, auth.py |
| `cryptography` / `hmac` / `hashlib` | HMAC-SHA256 | auth.py |

### 6.3 Redis DB2 Namespace

After consent gate removal, Redis DB2 is used by:
- `redis_buffer.py`: key `surveillance:buffer` (event staging, TTL 300s)
- `replay.py`: key prefix `surveillance:nonce:` (nonce dedup, TTL 660s)

No namespace collision. Consent gate was the third user (key prefix `consent:surveillance:`, TTL 300s) -- removed.

---

## 7. Risks

### RISK 1: Consumer consent removal requires careful refactor (MEDIUM)

The consumer `process_event()` method (lines 151-246) has consent woven into its control flow:
- Lines 172-195: consent scope mapping + check + early return on denial
- Line 222: `consent_status` passed to `_store_event`
- Lines 291, 322: `consent_status` stored in `extracted_facts`

The fix is straightforward (remove 3 code blocks, simplify signature) but must be done atomically with the consent_gate.py deletion to avoid import errors.

**Mitigation**: Port consumer.py with consent already removed; delete consent_gate.py in the same commit.

### RISK 2: test_consent_gate.py and test_consumer.py need rewrites (LOW)

`tests/surveillance/test_consent_gate.py` (423 lines based on the source) tests the consent gate directly. `tests/surveillance/test_consumer.py` mocks `check_consent`. Both tests are invalidated by consent gate removal.

**Mitigation**: Delete test_consent_gate.py. Rewrite test_consumer.py to remove consent mocking and test the simplified 3-step pipeline.

### RISK 3: Sentry DROP_EVENT_PATHS contains "consent-revocation" (LOW)

After consent gate removal, the "consent-revocation" entry in `DROP_EVENT_PATHS` (sentry_integration.py:44) references a concept that no longer exists in the surveillance module.

**Mitigation**: Keep it -- it's a safety net that drops Sentry events containing sensitive consent references. Zero runtime cost, defense-in-depth.

---

## 8. Disposition Summary for P24 M16

| Target File | Source(s) | Lines (est.) | Disposition |
|-------------|-----------|-------------|-------------|
| `guinevere/surveillance/__init__.py` | New (re-export hub) | ~40 | MODIFY-CREATE |
| `guinevere/surveillance/receiver.py` | auth + classification + models + replay + router + secret_scanner + secrets | ~200 | PORT |
| `guinevere/surveillance/buffer.py` | redis_buffer + consumer (consent removed) | ~150 | PORT |
| `guinevere/surveillance/storage.py` | retention + timescale | ~200 | PORT |
| `guinevere/observability/__init__.py` | New (re-export hub) | ~10 | MODIFY-CREATE |
| `guinevere/observability/sentry.py` | sentry_integration | ~100 | PORT |
| `guinevere/observability/metrics.py` | New (agent Prometheus metrics) | ~200 | MODIFY-CREATE |
| `src/surveillance/consent_gate.py` | 423 lines | 423 | DELETE |
| `src/surveillance/safe_mode.py` | 218 lines | 218 | DELETE |
| `src/observability/windows_metrics.py` | 207 lines | 207 | DELETE |

**Forbidden patterns in M16 files**: `consent_gate`, `consent_checker`, `safe_mode`, `SafeMode`, `HARD_STOP`, `hard_stop`, `# type: ignore`

---

## 9. Verdict

**PASS**. The source inventory is complete (14 + 3 files verified). The plan's consent gate removal is safe -- the HMAC ingest pipeline is untouched, and the consumer pipeline simplifies cleanly. All 11 porting files have no unresolvable dependencies on deleted modules. The new Prometheus metrics follow the existing `guinevere_` naming convention. The Sentry PII scrubber is self-contained and production-ready.

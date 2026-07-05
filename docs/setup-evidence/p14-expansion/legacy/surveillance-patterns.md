# Surveillance Pipeline Patterns — Research Report

> **Generated**: 2026-06-04
> **Source files**: consumer.py, consent_gate.py, classification.py, models.py (surveillance + memory), timescale.py, redis_buffer.py, secret_scanner.py
> **Purpose**: Document the architectural patterns used across the surveillance pipeline for P14 expansion reference.

---

## 1. Consent Scopes — Definition and Checking

### 1.1 Scope Registry

Consent scopes are defined in two locations:

**Hardcoded valid scopes** (consent_gate.py:49-54):

`python
VALID_SURVEILLANCE_SCOPES: frozenset[str] = frozenset({
    "surveillance.app_usage",
    "surveillance.location",
    "surveillance.notifications",
    "surveillance.clipboard",
})
`

**Event-to-scope mapping** (consumer.py:49-54):

`python
_EVENT_SCOPE_MAP: dict[str, str] = {
    "app_usage": "surveillance.app_usage",
    "location": "surveillance.location",
    "notification": "surveillance.notifications",
    "clipboard": "surveillance.clipboard",
}
_DEFAULT_SCOPE: str = "surveillance.app_usage"
`

Unknown event types default to surveillance.app_usage — this is a **fail-open for ingestion but fail-closed for consent** pattern (the consent gate still checks it).

### 1.2 Consent Decision Matrix

The check_consent(scope) function in consent_gate.py implements a **7-step fail-closed decision matrix**:

| Step | Condition | Verdict | Cached? |
|------|-----------|---------|---------|
| 0 | Scope not in VALID_SURVEILLANCE_SCOPES | BLOCK (unknown scope) | No |
| 1 | Redis cache hit (ACTIVE) | ALLOW | N/A |
| 2 | Redis cache hit (not ACTIVE) | BLOCK (cached reason) | N/A |
| 3 | Cache miss + DB query succeeds → ACTIVE | ALLOW | Yes |
| 4 | Cache miss + DB query fails | BLOCK (DB unavailable) | No |
| 5 | No ledger entry | BLOCK (never consented) | Yes |
| 6 | Status = WITHDRAWN | BLOCK | Yes |
| 7 | Status = PAUSED | BLOCK | Yes |

**Key design properties**:

- **Fail-closed**: any uncertainty (DB down after cache miss, no ledger entry, WITHDRAWN, PAUSED) → llowed=False.
- **Cache-only failure is NOT fail-closed**: Redis down → falls through to DB. Only DB failure after cache miss blocks.
- **Redis cache**: key format consent:surveillance:{scope}, TTL = 300s (configurable via CACHE_TTL_SECONDS).
- **Cache value**: JSON with {allowed, status, scope, reason, checked_at}.
- **Corrupt cache**: JSON decode error → fall through to DB (never trusts bad data).
- **Invalidation**: invalidate_cache(scope) called on consent grant/pause/withdraw/revocation events.

### 1.3 Consent Ledger Schema

consent.consent_ledger table (models.py:893-913):

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID (PK) | Row identifier |
| consent_type | Text | Type of consent |
| scope | Text | Surveillance scope string |
| status | Text | ACTIVE / PAUSED / WITHDRAWN |
| granted_by | Text | Who granted consent |
| granted_at | TIMESTAMPTZ | Grant timestamp |
| revoked_at | TIMESTAMPTZ | Revocation timestamp (nullable) |
| revocation_reason | Text | Why revoked |
| evidence_hash | Text | Cryptographic proof of consent |

Query: SELECT status FROM consent.consent_ledger WHERE scope = :scope ORDER BY granted_at DESC LIMIT 1

### 1.4 ConsentStatus Enum

`python
class ConsentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    WITHDRAWN = "WITHDRAWN"
`

### 1.5 ConsentCheckResult

Frozen dataclass returned by every consent check:

`python
@dataclass(frozen=True)
class ConsentCheckResult:
    allowed: bool
    status: ConsentStatus | None
    scope: str
    reason: str
    checked_at: datetime
`

---

## 2. Data Classification

### 2.1 Classification Tiers

Four-tier security classification system (classification.py:36-46):

| Tier | Enum Value | Risk Level |
|------|------------|------------|
| 1 | Internal | Lowest |
| 2 | Confidential | Default fallback |
| 3 | Restricted | Medium-high |
| 4 | Critical | Highest |

### 2.2 Event Type Classification Matrix

`
app_usage     → Restricted   | productivity_monitoring     | short_raw           | guinevere_core      | high
screen_state  → Restricted   | activity_tracking           | short_raw           | guinevere_core      | high
active_window → Restricted   | productivity_monitoring     | short_raw           | guinevere_core      | high
idle_time     → Restricted   | activity_tracking           | short_raw           | guinevere_core      | high
notification  → Critical     | context_awareness           | short_raw           | guinevere_core+faiz | double_high
browser       → Critical     | productivity_monitoring     | short_raw           | guinevere_core+faiz | double_high
location      → Critical     | safety_geofencing           | short_raw           | guinevere_core+faiz | double_high
call_log      → Critical     | context_awareness           | short_raw           | guinevere_core+faiz | double_high
health        → Critical     | health_monitoring           | medium_operational  | guinevere_core+faiz | double_high
clipboard     → Critical     | secret_protection           | transient           | guinevere_core_only | double_high
screenshot    → Critical     | visual_context              | critical_media      | guinevere_core_only | double_high
camera        → Critical     | visual_context              | critical_media      | guinevere_core_only | double_high
`

### 2.3 Default (Fail-Closed)

Unknown event types → Confidential with:
- purpose: unknown
- retention_class: 	ransient
- access_policy: guinevere_core+faiz
- encryption_profile: enhanced

This is intentionally conservative — unknown types get stricter retention (transient = 1 day) rather than leaking data with a permissive classification.

### 2.4 Retention Classes

`
transient           → 1 day
short_raw           → 7 days
critical_media      → 1 day
medium_operational  → 90 days
long_term_curated   → 365 days
regulated_audit     → 365 days
formal_hold         → 730 days
`

### 2.5 ClassificationResult Structure

Each ClassificationResult carries five governance attributes consumed by downstream systems:

| Attribute | Consumed By |
|-----------|-------------|
| classification | ClassificationMetaMixin column |
| purpose | Governance audit trail |
| retention_class | SurveillanceDataPolicy retention rules |
| access_policy | RBAC/ABAC enforcement |
| encryption_profile | Encryption layer (standard/enhanced/high/double_high) |

### 2.6 ClassificationMetaMixin (ORM)

All classified tables inherit ClassificationMetaMixin (models.py:54-83), which adds:

- classification, purpose, source, retention_class, retention_until
- access_policy, encryption_profile, deletion_state
- key_id, key_version, created_at, updated_at

Default server values: classification='Restricted', etention_class='Long-Term Curated', ccess_policy='guinevere-core', encryption_profile='envelope-AES-256-GCM', deletion_state='active'.

---

## 3. TimescaleDB Hypertable Creation

### 3.1 SurveillanceEvents ORM Model

The SurveillanceEvents class (models.py:478-505) is the primary hypertable:

`python
class SurveillanceEvents(Base, ClassificationMetaMixin):
    __tablename__ = "events"
    __table_args__ = (
        Index("events_occurred_at_idx", text("occurred_at DESC")),
        {"schema": "surveillance"},
    )
`

**Key columns**:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK, gen_random_uuid) | Auto-generated |
| event_type | Text | app_usage, clipboard, location, etc. |
| device_id | UUID (FK → device_registry) | Resolved via uuid5 |
| raw_payload | LargeBinary (bytes) | JSON-serialized event payload |
| extracted_facts | JSONB | consent_status, secrets_detected, etc. |
| summary | Text | Human-readable summary |
| occurred_at | TIMESTAMPTZ (PK component) | **Time partitioning key** |
| + ClassificationMetaMixin columns | Various | classification, purpose, retention, etc. |

**Composite primary key**: (id, occurred_at) — this is the standard TimescaleDB pattern where the time dimension is part of the PK for efficient chunk pruning.

### 3.2 Hypertable Setup

The hypertable is created at the SQL layer (not in ORM) using:

`sql
SELECT create_hypertable('surveillance.events', 'occurred_at', ...);
`

The TimescaledbConfig model (models.py:1191-1208) tracks extension configuration:

- default_chunk_interval: 7 days
- compression_enabled: 	rue
- retention_default_days: 365

### 3.3 Ingestion Patterns

**Single-event via raw SQL** (consumer.py:331-378):

`sql
INSERT INTO surveillance.events (
    id, event_type, device_id, raw_payload, extracted_facts, summary,
    classification, purpose, retention_class, access_policy,
    encryption_profile, occurred_at, ingested_at
) VALUES (
    gen_random_uuid(),
    :event_type, :device_id, :raw_payload, :extracted_facts, :summary,
    :classification, :purpose, :retention_class, :access_policy,
    :encryption_profile, :occurred_at, NOW()
)
`

**Batch insert via SQLAlchemy Core** (	imescale.py:126-128):

`python
stmt = insert(SurveillanceEvents)
result = await session.execute(stmt, row_dicts)
`

### 3.4 Device ID Resolution

String device identifiers (from Android/Windows agents) are mapped to deterministic UUIDs:

`python
device_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, device_id)
`

This ensures the same device_id string always produces the same UUID, enabling consistent FK references to surveillance.device_registry.

### 3.5 Supporting Tables

| Table | Schema | Purpose |
|-------|--------|---------|
| device_registry | surveillance | Device metadata, Tailscale IP, active status |
| ingestion_log | surveillance | Per-batch audit: batch_id, events_count, status, error_message |
| confrontation_block_log | surveillance | Tracks blocked surveillance actions |

---

## 4. Redis Buffer Pattern

### 4.1 Architecture

`
Agent (Tasker/Python daemon)
         │
         ▼ POST /surveillance/events
    Webhook Endpoint
         │
         ▼ push_event()
    Redis DB2 List (surveillance:buffer)
         │  TTL 300s auto-expiry
         ▼ pop_events() batch
    SurveillanceConsumer
         │
         ▼ consent → classify → scan → store
    PostgreSQL (surveillance.events)
`

### 4.2 Buffer Implementation

RedisSurveillanceBuffer (edis_buffer.py) uses Redis **DB2** (dedicated surveillance namespace):

| Property | Value |
|----------|-------|
| Redis DB | 2 |
| Key | surveillance:buffer |
| Data structure | Redis List |
| Push operation | RPUSH |
| Pop operation | LRANGE(0, count-1) + LTRIM(count, -1) in a **pipeline** (atomic read-and-trim) |
| TTL | 300 seconds (auto-purge stale events) |
| Protocol | SurveillanceBuffer — injectable for testing |

### 4.3 FIFO Atomic Pop

The pop operation uses a Redis pipeline to atomically read and trim:

`python
pipe = self._redis.pipeline()
pipe.lrange(self._buffer_key, 0, count - 1)   # Read first N items
pipe.ltrim(self._buffer_key, count, -1)        # Remove them from list
results = await pipe.execute()                  # Atomic execution
`

This prevents race conditions where multiple consumers could read the same events.

### 4.4 Consent Cache (Separate Redis Usage)

The consent gate also uses Redis DB2 but with a **different key pattern**:

- Key: consent:surveillance:{scope}
- TTL: 300s (CACHE_TTL_SECONDS)
- Value: JSON {allowed, status, scope, reason, checked_at}

**This is the same Redis instance (DB2) but different key namespaces**:
- surveillance:buffer — event queue
- consent:surveillance:* — consent cache

### 4.5 Protocol-Based Design

`python
@runtime_checkable
class SurveillanceBuffer(Protocol):
    async def push_event(self, event_data: dict[str, Any]) -> bool: ...
    async def pop_events(self, count: int = 10) -> list[dict[str, Any]]: ...
    async def buffer_size(self) -> int: ...
    async def close(self) -> None: ...
`

This enables:
- Test injection (mock buffers)
- Future swap to different backends (e.g., Kafka, SQS)
- Consumer does not depend on concrete Redis implementation

### 4.6 Consumer Configuration

SurveillanceConsumer (consumer.py:102-113):

| Parameter | Default | Purpose |
|-----------|---------|---------|
| buffer | injected | SurveillanceBuffer protocol |
| db_session_factory | injected | Callable → async DB session |
| poll_interval | 5.0s | Sleep between poll cycles |
| batch_size | 10 | Max events per cycle |

### 4.7 Graceful Shutdown

- SIGTERM/SIGINT → sets _running = False
- Current batch completes before loop exits
- Redis connection closed in inally block
- DB engine disposed in inally block

---

## 5. Audit Logging Structure

### 5.1 IngestionLog (Batch-Level Audit)

Written by TimescaleIngester._write_ingestion_log() (	imescale.py:336-382):

`python
status = "success" if failed_count == 0 else "partial" if ingested_count > 0 else "failed"
`

| Column | Type | Content |
|--------|------|---------|
| id | UUID (PK) | Row identifier |
| device_id | UUID (FK → device_registry) | Source device |
| batch_id | UUID | Correlates events in a batch |
| events_count | Integer | Total events attempted |
| status | Text | success / partial / failed |
| error_message | Text | Semicolon-separated error list |
| received_at | TIMESTAMPTZ | Batch timestamp |

**Written after every batch attempt** — even on full failure, providing a complete audit trail.

### 5.2 Consumer-Level Batch Logging

The consumer logs at the structlog level (not DB):

`python
logger.info(
    "consumer_batch_complete",
    batch_id=batch_id,          # UUID for this poll cycle
    batch_size=len(events),     # Events popped from Redis
    processed=processed,        # Successfully stored
    dropped=dropped,            # Consent denied or errors
)
`

This provides per-poll-cycle visibility for monitoring dashboards.

### 5.3 Consent Audit Trail

Every consent check is logged at the structlog level:

- consent_check_cache_hit / consent_check_cache_hit_blocked
- consent_check_cache_miss
- consent_check_db_failure
- consent_check_no_ledger_entry
- consent_check_withdrawn
- consent_check_paused
- consent_check_active
- consent_cache_invalidated

### 5.4 Event-Level Extracted Facts (JSONB)

Each stored event includes governance metadata in extracted_facts:

`python
extracted_facts = {
    "consent_status": consent_status,       # ACTIVE / PAUSED / WITHDRAWN
    "secrets_detected": True/False,
    "secret_types": [...],                  # Only if secrets found
    "secrets_found": N,                     # Count of occurrences
}
`

### 5.5 System-Wide Audit Tables

The broader audit infrastructure (models.py:1018-1076):

| Table | Schema | Purpose |
|-------|--------|---------|
| audit_trail | audit | Hashed event chain (event_hash + previous_hash) |
| evidence_register | audit | Links audit events to file artifacts |
| compliance_check | audit | Periodic compliance verification results |
| access_log | security | Who accessed what, classification bypasses |
| break_glass_log | security | Emergency access events |
| revocation_log | consent | Consent revocations with cascade effects |

### 5.6 Metadata-Only Logging Rule

**Critical constraint**: no raw surveillance payload is ever logged. All structlog entries use metadata-only:

- Event type, device_id, classification, counts — YES
- Raw payload content, secret values — NEVER

---

## 6. Full Event Pipeline Summary

`
┌──────────────────────────────────────────────────────────────────┐
│                     SURVEILLANCE EVENT LIFECYCLE                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. AGENT (Tasker/Windows daemon)                                │
│     └─ POST /surveillance/events                                 │
│        Payload: SurveillanceEventRequest (Pydantic validated)    │
│                                                                  │
│  2. WEBHOOK ENDPOINT                                             │
│     └─ Validate with Pydantic (extra="forbid", strict=True)      │
│     └─ Push to Redis DB2 buffer (surveillance:buffer)            │
│     └─ Return 202 Accepted                                       │
│                                                                  │
│  3. REDIS BUFFER (DB2, TTL 300s)                                 │
│     └─ RPUSH event JSON, LPOP+LTRIM for atomic FIFO pop          │
│                                                                  │
│  4. CONSUMER (polls every 5s, batch_size=10)                     │
│     │                                                            │
│     ├─ Step 1: Map event_type → consent scope                    │
│     │   └─ _EVENT_SCOPE_MAP.get(event_type, _DEFAULT_SCOPE)     │
│     │                                                            │
│     ├─ Step 2: Consent gate (fail-closed)                        │
│     │   └─ Redis cache → DB query → ALLOW/BLOCK                 │
│     │   └─ Denied → drop event, log metadata only                │
│     │                                                            │
│     ├─ Step 3: Classify event                                    │
│     │   └─ classify_event(event_type) → ClassificationResult    │
│     │   └─ classification, purpose, retention, access, encrypt   │
│     │                                                            │
│     ├─ Step 4: Secret scan (clipboard only)                      │
│     │   └─ 17 regex patterns + Shannon entropy ≥ 4.5             │
│     │   └─ Redact with [REDACTED], preserve metadata             │
│     │                                                            │
│     └─ Step 5: Store to DB (retry max 3, backoff 0.5/1.0/1.5s)  │
│         └─ INSERT INTO surveillance.events                       │
│         └─ extracted_facts: consent_status + secrets_detected    │
│                                                                  │
│  5. AUDIT                                                        │
│     └─ IngestionLog row per batch                                │
│     └─ structlog: batch_complete, consent_decisions, scan_result │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
`

---

## 7. Key Design Principles Observed

| Principle | Implementation |
|-----------|----------------|
| **Fail-closed consent** | Any uncertainty → BLOCK; unknown scopes → BLOCK |
| **Protocol injection** | All dependencies (buffer, DB session, redis) injected via Protocol — testable |
| **Metadata-only logging** | No raw payload in logs; only counts, types, statuses |
| **Immutable results** | All result types are @dataclass(frozen=True) |
| **Redact, don't drop** | Clipboard secrets are redacted; event metadata is preserved |
| **Deterministic device IDs** | uuid5(NAMESPACE_DNS, device_id) for consistent FK mapping |
| **Retry with backoff** | DB writes retry 3x with 0.5s * attempt backoff |
| **Graceful shutdown** | SIGTERM → complete current batch → exit cleanly |
| **Schema-qualified tables** | All tables use explicit schema (surveillance, consent, udit, etc.) |
| **Classification enum-gated** | Classification values are enums, never free-text |
| **Atomic buffer pop** | Redis pipeline for LRANGE+LTRIM prevents duplicate consumption |
| **Pydantic strict validation** | extra="forbid" + strict=True on all request/response models |

---

## 8. Files Referenced

| File | Role |
|------|------|
| src/surveillance/consumer.py | Main event consumer, full pipeline orchestration |
| src/surveillance/consent_gate.py | Fail-closed consent verification with Redis cache |
| src/surveillance/classification.py | Event type → classification tier mapping |
| src/surveillance/models.py | Pydantic request/response validation models |
| src/surveillance/timescale.py | TimescaleDB batch/single event ingestion |
| src/surveillance/redis_buffer.py | Redis DB2 FIFO event buffer with TTL |
| src/surveillance/secret_scanner.py | Clipboard secret detection and redaction |
| src/memory/models.py | SQLAlchemy ORM: SurveillanceEvents, IngestionLog, ConsentLedger |

---

*End of report.*

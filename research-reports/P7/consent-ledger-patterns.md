# Consent Ledger & Verification Gate Patterns — Research Report

> **Phase**: P7 Research  
> **Date**: 2026-06-02  
> **Author**: Guinevere (Librarian agent)  
> **Scope**: Append-only consent ledger (PostgreSQL), consent check middleware, fail-closed patterns, Redis caching, safe-mode handling, consent event lifecycle  
> **Context**: Guinevere ConsentRevocationPolicy requires an append-only consent ledger. Surveillance system must check consent status before storing any data.

---

## Table of Contents

1. [Append-Only Ledger — PostgreSQL Schema](#1-append-only-ledger--postgresql-schema)
2. [Consent Check Middleware — Gate Patterns](#2-consent-check-middleware--gate-patterns)
3. [Fail-Closed Patterns](#3-fail-closed-patterns)
4. [Consent Caching with Redis](#4-consent-caching-with-redis)
5. [Safe-Mode Handling](#5-safe-mode-handling)
6. [Consent Event Lifecycle](#6-consent-event-lifecycle)
7. [Integration Architecture](#7-integration-architecture)
8. [Sources & References](#8-sources--references)

---

## 1. Append-Only Ledger — PostgreSQL Schema

### 1.1 Design Principles

The consent ledger must be **append-only**: no UPDATE, no DELETE on historical entries. Every consent state change creates a new row with a cryptographic hash chain linking to the previous entry. This provides tamper-evidence — any modification to a past entry breaks the hash chain.

**Key references**:
- MinervaDB: PostgreSQL ledger with trigger-based history tables + hash columns ([source](https://minervadb.xyz/postgresql-audit/))
- Tracehold: HMAC hash chain with `sequence_number`, `prev_entry_hash`, `entry_hash`, `hmac_schema_version` ([source](https://tracehold.ai/blog/immutable-audit-log-hmac-hash-chain/))
- AWS QLDB replacement pattern: append-only journal with cryptographic hash chaining ([source](https://aws.amazon.com/blogs/database/replace-amazon-qldb-with-amazon-aurora-postgresql-for-audit-use-cases/))

### 1.2 Consent Ledger Table

```sql
-- Append-only consent ledger
-- Every consent state change creates a new row.
-- NEVER UPDATE or DELETE from this table.
CREATE TABLE consent_ledger (
    -- Monotonic sequence for hash chain ordering
    sequence_number     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Subject identification
    subject_id          UUID NOT NULL,             -- user/operator whose consent this records
    scope               TEXT NOT NULL,              -- e.g. 'surveillance.app_usage', 'surveillance.location'

    -- Consent event
    event_type          TEXT NOT NULL               -- CONSENT_GIVEN | CONSENT_UPDATED | CONSENT_PAUSED | CONSENT_WITHDRAWN | CONSENT_RESTORED
                    CHECK (event_type IN (
                        'CONSENT_GIVEN',
                        'CONSENT_UPDATED',
                        'CONSENT_PAUSED',
                        'CONSENT_WITHDRAWN',
                        'CONSENT_RESTORED'
                    )),

    -- Consent state after this event
    consent_status      TEXT NOT NULL               -- 'active' | 'paused' | 'withdrawn'
                    CHECK (consent_status IN ('active', 'paused', 'withdrawn')),

    -- Scope-specific metadata (JSON, varies by event)
    metadata            JSONB NOT NULL DEFAULT '{}',

    -- Provenance
    actor_id            UUID,                       -- who initiated this change (may differ from subject)
    actor_type          TEXT NOT NULL DEFAULT 'user'
                    CHECK (actor_type IN ('user', 'system', 'admin', 'distress_protocol')),
    reason              TEXT,                       -- human-readable reason for the change
    correlation_id      UUID,                       -- links related events (e.g. bulk withdrawal)

    -- Hash chain integrity
    prev_entry_hash     TEXT,                       -- SHA-256 of previous ledger entry (NULL for genesis)
    entry_hash          TEXT NOT NULL,              -- SHA-256 of this entry's canonical payload
    hmac_signature      TEXT,                       -- optional HMAC for additional tamper-evidence

    -- Timestamps
    effective_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Idempotency guard
    idempotency_key     TEXT UNIQUE                 -- prevents duplicate event processing
);

-- Performance indexes
CREATE INDEX idx_consent_ledger_subject_scope
    ON consent_ledger (subject_id, scope, sequence_number DESC);

CREATE INDEX idx_consent_ledger_effective_at
    ON consent_ledger (effective_at);

CREATE INDEX idx_consent_ledger_status
    ON consent_ledger (consent_status);
```

### 1.3 Append-Only Enforcement via Trigger

```sql
-- Block UPDATE and DELETE on the ledger table
CREATE OR REPLACE FUNCTION block_consent_ledger_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'consent_ledger is append-only: UPDATE and DELETE are forbidden'
        USING ERRCODE = 'P0001';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE TRIGGER enforce_append_only
    BEFORE UPDATE OR DELETE ON consent_ledger
    FOR EACH ROW
    EXECUTE FUNCTION block_consent_ledger_mutation();
```

### 1.4 Hash Chain Computation

```sql
-- Computes entry_hash from canonical payload fields.
-- Called BEFORE INSERT to set entry_hash and link prev_entry_hash.
CREATE OR REPLACE FUNCTION compute_consent_ledger_hash()
RETURNS TRIGGER AS $$
DECLARE
    canonical_payload TEXT;
    prev_hash TEXT;
BEGIN
    -- Get hash of the previous entry (chain link)
    SELECT entry_hash INTO prev_hash
    FROM consent_ledger
    WHERE sequence_number = (
        SELECT MAX(sequence_number) FROM consent_ledger
    );

    NEW.prev_entry_hash := prev_hash;  -- NULL for first entry (genesis)

    -- Build canonical string: deterministic field ordering
    canonical_payload := concat_ws('|',
        NEW.subject_id::TEXT,
        NEW.scope,
        NEW.event_type,
        NEW.consent_status,
        NEW.metadata::TEXT,
        NEW.actor_id::TEXT,
        NEW.effective_at::TEXT,
        COALESCE(NEW.prev_entry_hash, 'GENESIS')
    );

    -- SHA-256 hash of the canonical payload
    NEW.entry_hash := encode(
        digest(canonical_payload, 'sha256'),
        'hex'
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER compute_hash_before_insert
    BEFORE INSERT ON consent_ledger
    FOR EACH ROW
    EXECUTE FUNCTION compute_consent_ledger_hash();
```

> **Note**: Requires the `pgcrypto` extension (`CREATE EXTENSION IF NOT EXISTS pgcrypto;`) for `digest()`.

### 1.5 Hash Chain Verification Query

```sql
-- Verify integrity of the entire consent ledger chain.
-- Returns rows where the chain is broken (should return 0 rows).
SELECT
    curr.sequence_number,
    curr.prev_entry_hash AS expected_prev,
    prev.entry_hash AS actual_prev
FROM consent_ledger curr
LEFT JOIN consent_ledger prev
    ON prev.sequence_number = (
        SELECT MAX(sequence_number)
        FROM consent_ledger
        WHERE sequence_number < curr.sequence_number
    )
WHERE curr.prev_entry_hash IS DISTINCT FROM prev.entry_hash
   OR (curr.prev_entry_hash IS NULL AND prev.entry_hash IS NOT NULL)
ORDER BY curr.sequence_number;
```

### 1.6 Current Consent State View (Materialized)

```sql
-- Latest consent state per subject+scope.
-- Use this for fast consent checks; refresh periodically.
CREATE MATERIALIZED VIEW current_consent_state AS
SELECT DISTINCT ON (subject_id, scope)
    subject_id,
    scope,
    consent_status,
    event_type AS last_event,
    effective_at,
    sequence_number
FROM consent_ledger
ORDER BY subject_id, scope, sequence_number DESC;

-- Unique index for fast lookups
CREATE UNIQUE INDEX idx_current_consent_lookup
    ON current_consent_state (subject_id, scope);

-- Refresh strategy: after each ledger insert (via trigger) or on schedule
CREATE OR REPLACE FUNCTION refresh_consent_state()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY current_consent_state;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Option A: trigger-based (near real-time, adds latency to writes)
-- CREATE TRIGGER refresh_consent_after_insert
--     AFTER INSERT ON consent_ledger
--     FOR EACH STATEMENT
--     EXECUTE FUNCTION refresh_consent_state();

-- Option B: schedule-based (e.g. every 30 seconds via pg_cron)
-- SELECT cron.schedule('refresh-consent', '30 seconds',
--     'REFRESH MATERIALIZED VIEW CONCURRENTLY current_consent_state');
```

---

## 2. Consent Check Middleware — Gate Patterns

### 2.1 Core Pattern: Consent Gate Decorator

The consent check must happen **before** any data ingestion. This is modeled as a gate/middleware that wraps data storage operations.

**Reference pattern**: TesslateAI/OpenSail uses a `McpConsentRecord` model with `scopes` (JSON list), `granted_at`, and `revoked_at` to gate MCP server access ([source](https://github.com/TesslateAI/OpenSail/blob/main/orchestrator/app/models.py#L2275)).

```python
"""
Consent gate pattern for data ingestion pipelines.
Every data storage operation MUST pass through this gate.
"""
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Protocol
from uuid import UUID

logger = logging.getLogger(__name__)


class ConsentStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    WITHDRAWN = "withdrawn"


class ConsentEventType(str, enum.Enum):
    CONSENT_GIVEN = "CONSENT_GIVEN"
    CONSENT_UPDATED = "CONSENT_UPDATED"
    CONSENT_PAUSED = "CONSENT_PAUSED"
    CONSENT_WITHDRAWN = "CONSENT_WITHDRAWN"
    CONSENT_RESTORED = "CONSENT_RESTORED"


@dataclass(frozen=True)
class ConsentCheckResult:
    """Result of a consent verification check."""
    allowed: bool
    status: ConsentStatus | None
    scope: str
    reason: str
    sequence_number: int | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConsentChecker(Protocol):
    """Protocol for consent verification backends."""

    async def check_consent(
        self,
        subject_id: UUID,
        scope: str,
        *,
        require_fresh: bool = False,
    ) -> ConsentCheckResult: ...

    async def record_event(
        self,
        subject_id: UUID,
        scope: str,
        event_type: ConsentEventType,
        consent_status: ConsentStatus,
        *,
        actor_id: UUID | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int: ...
```

### 2.2 Pipeline Gate Middleware

```python
class ConsentGate:
    """
    Middleware that gates data ingestion behind consent verification.
    
    Fail-closed: if consent cannot be verified, ingestion is BLOCKED.
    """

    def __init__(
        self,
        checker: ConsentChecker,
        *,
        default_scope: str = "surveillance.general",
        max_staleness_seconds: float = 300.0,  # 5 minutes
    ) -> None:
        self._checker = checker
        self._default_scope = default_scope
        self._max_staleness = max_staleness_seconds

    async def verify(
        self,
        subject_id: UUID,
        scopes: list[str] | None = None,
    ) -> list[ConsentCheckResult]:
        """
        Verify consent for all required scopes.
        Returns results for each scope. ALL must be allowed for ingestion to proceed.
        """
        effective_scopes = scopes or [self._default_scope]
        results: list[ConsentCheckResult] = []

        for scope in effective_scopes:
            result = await self._checker.check_consent(
                subject_id=subject_id,
                scope=scope,
            )
            results.append(result)

            if not result.allowed:
                logger.warning(
                    "Consent gate BLOCKED: subject=%s scope=%s status=%s reason=%s",
                    subject_id, scope, result.status, result.reason,
                )
                # Short-circuit: first failure blocks all
                return results

        return results

    def __call__(self, scopes: list[str] | None = None) -> Callable:
        """Decorator for gating async functions behind consent verification."""
        required_scopes = scopes

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(subject_id: UUID, *args: Any, **kwargs: Any) -> Any:
                results = await self.verify(subject_id, required_scopes)

                blocked = [r for r in results if not r.allowed]
                if blocked:
                    raise ConsentDeniedError(
                        subject_id=subject_id,
                        blocked_scopes=[r.scope for r in blocked],
                        reasons={r.scope: r.reason for r in blocked},
                    )

                return await func(subject_id, *args, **kwargs)

            return wrapper
        return decorator


class ConsentDeniedError(Exception):
    """Raised when consent verification fails for one or more scopes."""

    def __init__(
        self,
        subject_id: UUID,
        blocked_scopes: list[str],
        reasons: dict[str, str],
    ) -> None:
        self.subject_id = subject_id
        self.blocked_scopes = blocked_scopes
        self.reasons = reasons
        super().__init__(
            f"Consent denied for {subject_id}: "
            f"blocked scopes={blocked_scopes}"
        )
```

### 2.3 Data Ingestion Pipeline Integration

```python
class SurveillanceIngestionPipeline:
    """
    Data ingestion pipeline with consent gate integration.
    Every data point passes through the consent gate before storage.
    """

    def __init__(
        self,
        consent_gate: ConsentGate,
        store: SurveillanceStore,
        event_bus: EventBus,
    ) -> None:
        self._gate = consent_gate
        self._store = store
        self._events = event_bus

    async def ingest(
        self,
        subject_id: UUID,
        scope: str,
        data: dict[str, Any],
    ) -> IngestionResult:
        """
        Ingest a surveillance data point.
        
        Flow: consent check -> store -> emit event
        If consent fails: data is NEVER stored, event is emitted for audit.
        """
        # Step 1: Gate check (fail-closed)
        results = await self._gate.verify(subject_id, [scope])
        blocked = [r for r in results if not r.allowed]

        if blocked:
            # Emit audit event: attempted ingestion without consent
            await self._events.emit(ConsentViolationEvent(
                subject_id=subject_id,
                scope=scope,
                violation_type="ingestion_blocked",
                blocked_scopes=[r.scope for r in blocked],
                timestamp=datetime.now(timezone.utc),
            ))
            return IngestionResult(
                stored=False,
                reason=f"Consent denied: {[r.reason for r in blocked]}",
            )

        # Step 2: Consent verified — proceed with storage
        stored_id = await self._store.save(subject_id, scope, data)

        # Step 3: Audit event for successful ingestion
        await self._events.emit(DataIngestedEvent(
            subject_id=subject_id,
            scope=scope,
            record_id=stored_id,
            timestamp=datetime.now(timezone.utc),
        ))

        return IngestionResult(stored=True, record_id=stored_id)
```

---

## 3. Fail-Closed Patterns

### 3.1 Design Philosophy

**Fail-closed** means: when the consent system encounters any uncertainty (missing data, stale cache, conflicting states, system errors), it defaults to **BLOCKING** data ingestion. This is the opposite of fail-open, which would allow data through on errors.

**Reference**: Q00/ouroboros uses fail-closed for trust verification — "The firewall already fails closed on subject mismatch as defense-in-depth, so leaving a not-yet-reset trust file in place keeps the plugin gated until the user re-grants" ([source](https://github.com/Q00/ouroboros/blob/main/src/ouroboros/cli/commands/plugin.py#L484)).

### 3.2 Fail-Closed Decision Matrix

| Condition | Consent Result | Action |
|-----------|---------------|--------|
| Ledger entry exists, status = `active` | ✅ ALLOW | Proceed with ingestion |
| Ledger entry exists, status = `paused` | ❌ BLOCK | Queue data, do not store |
| Ledger entry exists, status = `withdrawn` | ❌ BLOCK | Reject and emit violation |
| No ledger entry for scope | ❌ BLOCK | Never consented — cannot ingest |
| Cache miss, DB query succeeds | Use DB result | Standard check |
| Cache miss, DB query fails (timeout/error) | ❌ BLOCK | Fail-closed: cannot verify |
| Hash chain broken | ❌ BLOCK | Ledger integrity compromised |
| Cache stale (> max_staleness) | ❌ BLOCK | Treat as unverified |
| Conflicting entries (same timestamp, different status) | ❌ BLOCK | Use latest sequence_number; if tie, block |
| Redis connection failed | Fall through to DB | If DB also fails, BLOCK |

### 3.3 Python Implementation

```python
class FailClosedConsentChecker:
    """
    Consent checker that defaults to BLOCK on any uncertainty.
    """

    def __init__(
        self,
        cache: ConsentCache | None,
        ledger: ConsentLedgerRepository,
        *,
        max_staleness_seconds: float = 300.0,
    ) -> None:
        self._cache = cache
        self._ledger = ledger
        self._max_staleness = max_staleness_seconds

    async def check_consent(
        self,
        subject_id: UUID,
        scope: str,
        *,
        require_fresh: bool = False,
    ) -> ConsentCheckResult:
        """
        Check consent status. Fail-closed on any error.
        """
        # Try cache first (unless fresh required)
        if self._cache and not require_fresh:
            try:
                cached = await self._cache.get(subject_id, scope)
                if cached and not self._is_stale(cached):
                    return self._to_result(cached, scope, source="cache")
            except Exception:
                logger.warning(
                    "Cache read failed for %s/%s — falling through to ledger",
                    subject_id, scope,
                )
                # Fall through to DB — do NOT fail on cache error alone

        # Query the ledger (source of truth)
        try:
            entry = await self._ledger.get_current_state(subject_id, scope)
        except Exception as exc:
            # Fail-closed: if we cannot read the ledger, BLOCK
            logger.error(
                "Ledger query failed for %s/%s: %s — FAILING CLOSED",
                subject_id, scope, exc,
            )
            return ConsentCheckResult(
                allowed=False,
                status=None,
                scope=scope,
                reason=f"System error: consent verification unavailable ({exc})",
            )

        # No ledger entry = never consented = BLOCK
        if entry is None:
            return ConsentCheckResult(
                allowed=False,
                status=None,
                scope=scope,
                reason="No consent record found for this scope",
            )

        # Update cache with fresh result
        if self._cache:
            try:
                await self._cache.set(subject_id, scope, entry)
            except Exception:
                logger.warning("Cache write failed — non-blocking")

        return self._to_result(entry, scope, source="ledger")

    def _is_stale(self, cached: CachedConsent) -> bool:
        age = (datetime.now(timezone.utc) - cached.checked_at).total_seconds()
        return age > self._max_staleness

    def _to_result(
        self,
        entry: ConsentState,
        scope: str,
        *,
        source: str,
    ) -> ConsentCheckResult:
        allowed = entry.consent_status == ConsentStatus.ACTIVE
        return ConsentCheckResult(
            allowed=allowed,
            status=entry.consent_status,
            scope=scope,
            reason="active" if allowed else f"status={entry.consent_status.value}",
            sequence_number=entry.sequence_number,
        )
```

### 3.4 Hash Chain Integrity Gate

```python
class LedgerIntegrityChecker:
    """
    Verifies the hash chain integrity of the consent ledger.
    If chain is broken, ALL consent checks must fail-closed.
    """

    def __init__(self, ledger: ConsentLedgerRepository) -> None:
        self._ledger = ledger

    async def verify_chain(self) -> ChainVerificationResult:
        """
        Verify that no ledger entries have been tampered with.
        Returns result with any broken sequence numbers.
        """
        broken_entries = await self._ledger.find_broken_chain_entries()

        if broken_entries:
            logger.critical(
                "CONSENT LEDGER INTEGRITY VIOLATION: %d entries with broken hash chain. "
                "Sequence numbers: %s. ALL consent checks will fail-closed.",
                len(broken_entries),
                [e.sequence_number for e in broken_entries],
            )
            return ChainVerificationResult(
                intact=False,
                broken_sequences=[e.sequence_number for e in broken_entries],
            )

        return ChainVerificationResult(intact=True, broken_sequences=[])


@dataclass(frozen=True)
class ChainVerificationResult:
    intact: bool
    broken_sequences: list[int]
```

---

## 4. Consent Caching with Redis

### 4.1 Architecture

Redis serves as a **read-through cache** for consent state. The PostgreSQL ledger remains the source of truth. Redis provides sub-millisecond lookups for hot consent checks in the ingestion pipeline.

**Reference patterns**:
- Cache-aside: check cache → miss → query DB → populate cache with TTL → return
- Pub/Sub invalidation: consent revocation publishes message → all subscribers evict cache
- Session tracking: `sadd`/`smembers` for tracking all cached scopes per subject

### 4.2 Redis Key Design

```
# Consent state cache
consent:{subject_id}:{scope}       -> JSON blob (status, sequence_number, checked_at)
                                     TTL: 300 seconds (configurable)

# Index: all cached scopes for a subject (for bulk invalidation)
consent:subjects:{subject_id}:scopes  -> SET of scope strings
                                     TTL: 3600 seconds (1 hour)

# Invalidation channel (Pub/Sub)
channel:consent:invalidation        -> messages: {subject_id, scope, event_type}

# Ledger integrity status (global)
consent:ledger:integrity            -> "intact" | "broken"
                                     TTL: 60 seconds (frequent re-check)
```

### 4.3 Python Redis Cache Implementation

```python
import json
import redis.asyncio as aioredis
from datetime import datetime, timezone
from uuid import UUID


class RedisConsentCache:
    """
    Redis-backed consent state cache with Pub/Sub invalidation.
    
    Design:
    - TTL-based expiration (default 300s) as safety net
    - Explicit invalidation on consent events (revocation, pause)
    - Pub/Sub for distributed cache invalidation across workers
    """

    CONSENT_KEY_PREFIX = "consent"
    SUBJECT_SCOPES_PREFIX = "consent:subjects"
    INVALIDATION_CHANNEL = "consent:invalidation"
    INTEGRITY_KEY = "consent:ledger:integrity"

    def __init__(
        self,
        redis: aioredis.Redis,
        *,
        default_ttl: int = 300,           # 5 minutes
        subject_scopes_ttl: int = 3600,   # 1 hour
        integrity_ttl: int = 60,          # 1 minute
    ) -> None:
        self._redis = redis
        self._default_ttl = default_ttl
        self._scopes_ttl = subject_scopes_ttl
        self._integrity_ttl = integrity_ttl

    # --- Key helpers ---

    def _consent_key(self, subject_id: UUID, scope: str) -> str:
        return f"{self.CONSENT_KEY_PREFIX}:{subject_id}:{scope}"

    def _scopes_key(self, subject_id: UUID) -> str:
        return f"{self.SUBJECT_SCOPES_PREFIX}:{subject_id}:scopes"

    # --- Read ---

    async def get(self, subject_id: UUID, scope: str) -> CachedConsent | None:
        """Retrieve cached consent state. Returns None on miss or error."""
        key = self._consent_key(subject_id, scope)
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            data = json.loads(raw)
            return CachedConsent(
                subject_id=subject_id,
                scope=scope,
                consent_status=ConsentStatus(data["consent_status"]),
                sequence_number=data["sequence_number"],
                checked_at=datetime.fromisoformat(data["checked_at"]),
            )
        except Exception as exc:
            logger.warning("Redis cache read error: %s", exc)
            return None

    # --- Write ---

    async def set(
        self,
        subject_id: UUID,
        scope: str,
        entry: ConsentState,
    ) -> None:
        """Cache a consent state entry with TTL."""
        key = self._consent_key(subject_id, scope)
        payload = json.dumps({
            "consent_status": entry.consent_status.value,
            "sequence_number": entry.sequence_number,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        })

        pipeline = self._redis.pipeline()
        pipeline.setex(key, self._default_ttl, payload)
        # Track this scope under the subject for bulk invalidation
        pipeline.sadd(self._scopes_key(subject_id), scope)
        pipeline.expire(self._scopes_key(subject_id), self._scopes_ttl)
        await pipeline.execute()

    # --- Invalidation ---

    async def invalidate(self, subject_id: UUID, scope: str) -> None:
        """Remove a specific consent cache entry."""
        key = self._consent_key(subject_id, scope)
        pipeline = self._redis.pipeline()
        pipeline.delete(key)
        pipeline.srem(self._scopes_key(subject_id), scope)
        await pipeline.execute()

    async def invalidate_all_for_subject(self, subject_id: UUID) -> int:
        """Remove all cached consent entries for a subject."""
        scopes_key = self._scopes_key(subject_id)
        scopes = await self._redis.smembers(scopes_key)

        if not scopes:
            return 0

        pipeline = self._redis.pipeline()
        for scope_bytes in scopes:
            scope = scope_bytes.decode("utf-8")
            pipeline.delete(self._consent_key(subject_id, scope))
        pipeline.delete(scopes_key)
        results = await pipeline.execute()
        return len(scopes)

    # --- Pub/Sub Invalidation ---

    async def publish_invalidation(
        self,
        subject_id: UUID,
        scope: str | None,
        event_type: ConsentEventType,
    ) -> None:
        """
        Publish a consent invalidation event to all subscribers.
        Used when consent is revoked/paused/updated to immediately
        evict stale cache entries across all workers.
        """
        message = json.dumps({
            "subject_id": str(subject_id),
            "scope": scope,  # None = invalidate all scopes
            "event_type": event_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await self._redis.publish(self.INVALIDATION_CHANNEL, message)

    async def subscribe_invalidations(self) -> None:
        """
        Subscribe to consent invalidation events.
        Run this in a background task per worker.
        """
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.INVALIDATION_CHANNEL)

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                data = json.loads(message["data"])
                subject_id = UUID(data["subject_id"])
                scope = data.get("scope")

                if scope:
                    await self.invalidate(subject_id, scope)
                else:
                    await self.invalidate_all_for_subject(subject_id)

                logger.info(
                    "Cache invalidated: subject=%s scope=%s event=%s",
                    subject_id, scope, data["event_type"],
                )
            except Exception as exc:
                logger.error("Failed to process invalidation: %s", exc)
```

### 4.4 Cache Invalidation Flow

```
User revokes consent
    │
    ├─► 1. Append CONSENT_WITHDRAWN to ledger (PostgreSQL)
    │
    ├─► 2. Delete Redis cache entry: DEL consent:{subject_id}:{scope}
    │
    ├─► 3. Publish to Pub/Sub channel: consent:invalidation
    │       └─► All workers receive message
    │       └─► Each worker: DEL consent:{subject_id}:{scope}
    │
    └─► 4. Emit CONSENT_WITHDRAWN event to event bus
            └─► Audit trail
            └─► Notify ingestion pipelines to flush queued data
```

### 4.5 TTL Strategy

| Cache Layer | TTL | Rationale |
|-------------|-----|-----------|
| Individual consent entry | 300s (5 min) | Balance freshness vs DB load |
| Subject scopes index | 3600s (1 hour) | Low churn, bulk invalidation helper |
| Ledger integrity status | 60s (1 min) | Security-critical, frequent re-verification |
| Pub/Sub invalidation | Immediate | Explicit revocation bypasses TTL |

---

## 5. Safe-Mode Handling

### 5.1 Concept

Safe mode is triggered by distress protocol activation or system anomaly detection. In safe mode:
- **Confrontation/persona behaviors** are paused
- **Data ingestion pipeline** continues operating
- **Consent checks** remain active (fail-closed is preserved)
- **New data** is queued but not processed until safe mode clears

### 5.2 Safe-Mode State Machine

```
                    ┌──────────────┐
                    │   NORMAL     │
                    │ ingestion: ✅│
                    │ persona:  ✅│
                    └──────┬───────┘
                           │
              distress_protocol / anomaly
                           │
                           ▼
                    ┌──────────────┐
                    │  SAFE_MODE   │
                    │ ingestion: ⏸ │ (queued, not processed)
                    │ persona:  ⏸ │ (paused)
                    │ consent:  ✅ │ (still enforced)
                    └──────┬───────┘
                           │
              operator_clears / timeout
                           │
                           ▼
                    ┌──────────────┐
                    │   NORMAL     │
                    │ (resume)     │
                    └──────────────┘
```

### 5.3 Implementation

```python
class SafeModeController:
    """
    Controls safe-mode activation/deactivation.
    In safe mode: ingestion is paused (queued), consent checks remain active.
    """

    def __init__(
        self,
        event_bus: EventBus,
        ingestion_queue: asyncio.Queue,
    ) -> None:
        self._active = False
        self._activated_at: datetime | None = None
        self._reason: str | None = None
        self._event_bus = event_bus
        self._queue = ingestion_queue

    @property
    def is_active(self) -> bool:
        return self._active

    async def activate(self, reason: str, *, actor: str = "system") -> None:
        """Activate safe mode. Pause persona, queue ingestion."""
        if self._active:
            logger.warning("Safe mode already active: %s", self._reason)
            return

        self._active = True
        self._activated_at = datetime.now(timezone.utc)
        self._reason = reason

        await self._event_bus.emit(SafeModeActivatedEvent(
            reason=reason,
            actor=actor,
            timestamp=self._activated_at,
        ))

        logger.warning(
            "SAFE MODE ACTIVATED: reason=%s actor=%s. "
            "Ingestion will be queued. Consent checks remain active.",
            reason, actor,
        )

    async def deactivate(self, *, actor: str = "operator") -> list[dict]:
        """
        Deactivate safe mode. Process queued ingestion items.
        Returns the queued items for the caller to re-submit.
        """
        if not self._active:
            return []

        self._active = False
        queued_items: list[dict] = []

        # Drain the queue
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                queued_items.append(item)
            except asyncio.QueueEmpty:
                break

        activated_duration = (
            datetime.now(timezone.utc) - self._activated_at
        ).total_seconds() if self._activated_at else 0

        await self._event_bus.emit(SafeModeDeactivatedEvent(
            duration_seconds=activated_duration,
            queued_items_count=len(queued_items),
            actor=actor,
            timestamp=datetime.now(timezone.utc),
        ))

        self._activated_at = None
        self._reason = None

        logger.info(
            "Safe mode deactivated. %d items were queued during safe mode.",
            len(queued_items),
        )
        return queued_items
```

### 5.4 Safe-Mode Ingestion Integration

```python
class SafeModeAwareIngestionPipeline(SurveillanceIngestionPipeline):
    """
    Extends the ingestion pipeline with safe-mode awareness.
    In safe mode: consent is still checked, but data is queued instead of stored.
    """

    def __init__(
        self,
        consent_gate: ConsentGate,
        store: SurveillanceStore,
        event_bus: EventBus,
        safe_mode: SafeModeController,
    ) -> None:
        super().__init__(consent_gate, store, event_bus)
        self._safe_mode = safe_mode

    async def ingest(
        self,
        subject_id: UUID,
        scope: str,
        data: dict[str, Any],
    ) -> IngestionResult:
        # Consent check ALWAYS runs, even in safe mode
        results = await self._gate.verify(subject_id, [scope])
        blocked = [r for r in results if not r.allowed]

        if blocked:
            return IngestionResult(
                stored=False,
                reason=f"Consent denied: {[r.reason for r in blocked]}",
            )

        # If safe mode is active, queue instead of store
        if self._safe_mode.is_active:
            await self._safe_mode._queue.put({
                "subject_id": subject_id,
                "scope": scope,
                "data": data,
                "queued_at": datetime.now(timezone.utc).isoformat(),
            })
            return IngestionResult(
                stored=False,
                queued=True,
                reason="Safe mode active: data queued for deferred processing",
            )

        # Normal path: consent verified, not in safe mode
        return await super().ingest(subject_id, scope, data)
```

---

## 6. Consent Event Lifecycle

### 6.1 Event Types

| Event | Trigger | Consent Status After | Ingestion Impact |
|-------|---------|---------------------|------------------|
| `CONSENT_GIVEN` | User explicitly grants consent for a scope | `active` | Ingestion allowed |
| `CONSENT_UPDATED` | User modifies consent parameters (e.g. narrows scope) | `active` (with updated metadata) | Ingestion continues with new constraints |
| `CONSENT_PAUSED` | User temporarily suspends consent (or distress protocol) | `paused` | Ingestion blocked; data queued in safe mode |
| `CONSENT_WITHDRAWN` | User permanently revokes consent | `withdrawn` | Ingestion blocked; existing data retention policy applies |
| `CONSENT_RESTORED` | User re-grants previously withdrawn consent | `active` | Ingestion resumes |

### 6.2 Event Emission Pattern

```python
class ConsentEventBus:
    """
    Emits consent lifecycle events.
    Every event is:
    1. Appended to the ledger (source of truth)
    2. Published to Redis Pub/Sub (cache invalidation)
    3. Emitted to the application event bus (downstream handlers)
    """

    def __init__(
        self,
        ledger: ConsentLedgerRepository,
        cache: RedisConsentCache,
        app_events: EventBus,
    ) -> None:
        self._ledger = ledger
        self._cache = cache
        self._events = app_events

    async def emit(
        self,
        subject_id: UUID,
        scope: str,
        event_type: ConsentEventType,
        *,
        actor_id: UUID | None = None,
        actor_type: str = "user",
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> ConsentLedgerEntry:
        """
        Record a consent event and propagate to all subsystems.
        """
        # Determine resulting status
        status_map = {
            ConsentEventType.CONSENT_GIVEN: ConsentStatus.ACTIVE,
            ConsentEventType.CONSENT_UPDATED: ConsentStatus.ACTIVE,
            ConsentEventType.CONSENT_PAUSED: ConsentStatus.PAUSED,
            ConsentEventType.CONSENT_WITHDRAWN: ConsentStatus.WITHDRAWN,
            ConsentEventType.CONSENT_RESTORED: ConsentStatus.ACTIVE,
        }
        new_status = status_map[event_type]

        # 1. Append to ledger
        entry = await self._ledger.append(
            subject_id=subject_id,
            scope=scope,
            event_type=event_type,
            consent_status=new_status,
            actor_id=actor_id,
            actor_type=actor_type,
            reason=reason,
            metadata=metadata or {},
            idempotency_key=idempotency_key,
        )

        # 2. Invalidate cache
        await self._cache.invalidate(subject_id, scope)
        await self._cache.publish_invalidation(subject_id, scope, event_type)

        # 3. Emit to application event bus
        await self._events.emit(ConsentLifecycleEvent(
            event_type=event_type,
            subject_id=subject_id,
            scope=scope,
            new_status=new_status,
            sequence_number=entry.sequence_number,
            timestamp=entry.effective_at,
            metadata=metadata or {},
        ))

        logger.info(
            "Consent event: %s subject=%s scope=%s status=%s seq=%d",
            event_type.value, subject_id, scope, new_status.value,
            entry.sequence_number,
        )

        return entry
```

### 6.3 State Transition Rules

```python
# Valid state transitions
VALID_TRANSITIONS: dict[ConsentStatus | None, set[ConsentEventType]] = {
    None: {ConsentEventType.CONSENT_GIVEN},  # Initial state: only GIVEN allowed
    ConsentStatus.ACTIVE: {
        ConsentEventType.CONSENT_UPDATED,
        ConsentEventType.CONSENT_PAUSED,
        ConsentEventType.CONSENT_WITHDRAWN,
    },
    ConsentStatus.PAUSED: {
        ConsentEventType.CONSENT_RESTORED,    # Resume from pause
        ConsentEventType.CONSENT_WITHDRAWN,   # Escalate to withdrawal
        ConsentEventType.CONSENT_UPDATED,     # Modify while paused
    },
    ConsentStatus.WITHDRAWN: {
        ConsentEventType.CONSENT_GIVEN,       # Re-grant after withdrawal
        ConsentEventType.CONSENT_RESTORED,    # Restore (admin action)
    },
}


def validate_transition(
    current_status: ConsentStatus | None,
    event_type: ConsentEventType,
) -> bool:
    """Check if a consent event is a valid state transition."""
    allowed = VALID_TRANSITIONS.get(current_status, set())
    return event_type in allowed
```

---

## 7. Integration Architecture

### 7.1 System Diagram

```
┌──────────────────────────────────────────────────────────┐
│                   Data Ingestion Pipeline                  │
│                                                          │
│  ┌─────────┐    ┌────────────┐    ┌──────────────────┐  │
│  │ Data     │───►│ Consent    │───►│ Surveillance     │  │
│  │ Source   │    │ Gate       │    │ Store            │  │
│  │ (Tasker, │    │ (middleware)│    │ (PostgreSQL)     │  │
│  │  sensor) │    └─────┬──────┘    └──────────────────┘  │
│  └─────────┘          │                                   │
│                        │ Check                             │
│                        ▼                                   │
│              ┌──────────────────┐                         │
│              │ Consent Checker  │                         │
│              │ (fail-closed)    │                         │
│              └───┬──────────┬───┘                         │
│                  │          │                              │
│          Cache   │          │  Source of Truth             │
│          miss/   │          │  miss                        │
│          hit     ▼          ▼                              │
│  ┌────────────────┐  ┌─────────────────┐                  │
│  │ Redis Cache    │  │ Consent Ledger  │                  │
│  │ (consent:*:*)  │  │ (append-only    │                  │
│  │ TTL: 300s      │  │  + hash chain)  │                  │
│  │ Pub/Sub: ✅    │  │                 │                  │
│  └────────────────┘  └─────────────────┘                  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Event Bus                                           │  │
│  │ CONSENT_GIVEN | CONSENT_UPDATED | CONSENT_PAUSED   │  │
│  │ CONSENT_WITHDRAWN | CONSENT_RESTORED               │  │
│  │ SAFE_MODE_ACTIVATED | SAFE_MODE_DEACTIVATED        │  │
│  │ DATA_INGESTED | CONSENT_VIOLATION                  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────┐                                    │
│  │ Safe Mode        │  Pauses persona + queues ingestion │
│  │ Controller       │  Consent checks remain active      │
│  └──────────────────┘                                    │
└──────────────────────────────────────────────────────────┘
```

### 7.2 Guinevere Consent Scope Mapping

| Scope | Description | Default |
|-------|-------------|---------|
| `surveillance.app_usage` | App usage tracking | Requires explicit consent |
| `surveillance.location` | Location data collection | Requires explicit consent |
| `surveillance.notifications` | Notification monitoring | Requires explicit consent |
| `surveillance.clipboard` | Clipboard content capture | Requires explicit consent |
| `surveillance.general` | Catch-all surveillance scope | Requires explicit consent |

All scopes require **explicit** `CONSENT_GIVEN` before any data ingestion. No implicit consent. No fail-open.

---

## 8. Sources & References

### Append-Only Ledger Patterns

| Source | URL | Key Pattern |
|--------|-----|-------------|
| MinervaDB — PostgreSQL Ledger | [minervadb.xyz/postgresql-audit/](https://minervadb.xyz/postgresql-audit/) | Trigger-based history tables + hash columns |
| Tracehold — HMAC Hash Chain | [tracehold.ai/blog/immutable-audit-log-hmac-hash-chain/](https://tracehold.ai/blog/immutable-audit-log-hmac-hash-chain/) | 4-field hash chain: sequence, prev_hash, entry_hash, hmac_version |
| AWS — QLDB to Aurora PostgreSQL | [aws.amazon.com/blogs/database/...](https://aws.amazon.com/blogs/database/replace-amazon-qldb-with-amazon-aurora-postgresql-for-audit-use-cases/) | Append-only journal with cryptographic chaining |
| Design Gurus — Immutable Audit Trails | [designgurus.io/answers/...](https://www.designgurus.io/answers/detail/how-do-you-enforce-immutability-and-appendonly-audit-trails) | Hash chain + batch signing + periodic anchoring |
| Hoop.dev — PostgreSQL Audit Logs | [hoop.dev/blog/...](https://hoop.dev/blog/immutable-audit-logs-in-postgresql-with-pgcli/) | Append-only tables, triggers, schema design |

### Consent Models (OSS)

| Repository | Pattern |
|------------|---------|
| [TesslateAI/OpenSail](https://github.com/TesslateAI/OpenSail/blob/main/orchestrator/app/models.py#L2275) | `McpConsentRecord`: per-install consent with scopes JSON, granted_at, revoked_at |
| [Q00/ouroboros](https://github.com/Q00/ouroboros/blob/main/src/ouroboros/cli/commands/plugin.py#L484) | Fail-closed trust verification: corrupted trust file keeps plugin gated |
| [LeoYeAI/openclaw](https://github.com/LeoYeAI/openclaw-master-skills/blob/main/skills/erp-claw/scripts/erpclaw-os/research_engine.py#L450) | FERPA consent: parent_portal_access table with verified flag, access log, age-based revocation |
| [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/oauth_proxy/models.py#L41) | `OAuthTransaction` consent tracking with CSRF + consent_token |

### Redis Caching Patterns

| Source | Key Pattern |
|--------|-------------|
| [Redis — Cache Invalidation](https://redis.io/glossary/cache-invalidation/) | TTL + explicit invalidation for GDPR/CCPA compliance |
| [Milan Jovanović — Distributed Cache](https://www.milanjovanovic.tech/blog/solving-the-distributed-cache-invalidation-problem-with-redis-and-hybridcache) | Pub/Sub self-publishing for distributed invalidation |
| [OneUptime — Redis for PostgreSQL](https://oneuptime.com/blog/post/2026-03-31-redis-how-to-use-redis-as-a-cache-for-postgresql/view) | Cache-aside pattern with TTL management |
| [TechInterview — Token Revocation](https://www.techinterview.org/post/3233469926/lld-token-revocation/) | JTI tracking with TTL = remaining lifetime, user_rev:{user_id} pattern |

---

## Appendix A: Migration Template (Alembic)

```python
"""
Alembic migration: create consent_ledger table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "consent_ledger_v1"
down_revision = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "consent_ledger",
        sa.Column("sequence_number", sa.BigInteger, primary_key=True,
                  server_default=sa.text("GENERATED ALWAYS AS IDENTITY")),
        sa.Column("subject_id", UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.Text, nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("consent_status", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.Text, nullable=False, server_default="user"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("correlation_id", UUID(as_uuid=True), nullable=True),
        sa.Column("prev_entry_hash", sa.Text, nullable=True),
        sa.Column("entry_hash", sa.Text, nullable=False),
        sa.Column("hmac_signature", sa.Text, nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("recorded_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("idempotency_key", sa.Text, nullable=True, unique=True),
    )

    op.create_index(
        "idx_consent_ledger_subject_scope",
        "consent_ledger",
        ["subject_id", "scope", sa.text("sequence_number DESC")],
    )
    op.create_index(
        "idx_consent_ledger_effective_at",
        "consent_ledger",
        ["effective_at"],
    )

    # Append-only triggers
    op.execute("""
        CREATE OR REPLACE FUNCTION block_consent_ledger_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'consent_ledger is append-only'
                USING ERRCODE = 'P0001';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
    """)

    op.execute("""
        CREATE TRIGGER enforce_append_only
            BEFORE UPDATE OR DELETE ON consent_ledger
            FOR EACH ROW
            EXECUTE FUNCTION block_consent_ledger_mutation();
    """)


def downgrade() -> None:
    op.drop_table("consent_ledger")
    op.execute("DROP FUNCTION IF EXISTS block_consent_ledger_mutation()")
```

---

## Appendix B: Test Checklist

| Test | Description | Expected |
|------|-------------|----------|
| Ledger append | Insert new consent event | sequence_number auto-increments, entry_hash computed |
| Append-only enforcement | Attempt UPDATE on ledger | Exception raised: append-only |
| Append-only enforcement | Attempt DELETE on ledger | Exception raised: append-only |
| Hash chain integrity | Tamper with past entry | Chain verification query returns broken entry |
| Consent gate — active | Check consent for active scope | ALLOW |
| Consent gate — withdrawn | Check consent for withdrawn scope | BLOCK |
| Consent gate — no record | Check consent for unknown scope | BLOCK (never consented) |
| Consent gate — DB failure | Simulate DB timeout | BLOCK (fail-closed) |
| Cache hit | Check consent with valid cache | Fast return from cache |
| Cache miss + DB hit | Cache expired, DB has record | DB result returned, cache refreshed |
| Cache invalidation | Publish revocation event | Cache entry deleted, all subscribers notified |
| Safe mode activate | Trigger distress protocol | Ingestion queued, persona paused |
| Safe mode deactivate | Operator clears safe mode | Queued items available for re-processing |
| State transition | WITHDRAWN → GIVEN | Valid, new ACTIVE entry |
| State transition | WITHDRAWN → PAUSED | Invalid, rejected |
| Idempotency | Duplicate event with same key | Second insert blocked by unique constraint |

---

*Report generated by Librarian agent for Guinevere P7 research phase.*
*All patterns are implementation-ready recommendations based on OSS evidence and industry best practices.*

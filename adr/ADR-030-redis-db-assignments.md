---
adr: 030
title: "Redis DB Assignments (DB0–DB5)"
status: "Accepted"
date: "2026-05-31"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - redis
  - database
  - cache
  - queue
  - infrastructure
risk_level: "CRITICAL"
supersedes: "N/A"
related_documents:
  - Guinevere_APIIntegration_v2.0.md
  - Guinevere_TechnicalArchitecture_v2.0.md
  - Guinevere_MemorySchema_v2.0.md
---

# ADR-030: Redis DB Assignments (DB0–DB5)

## Status

Accepted

## Date

2026-05-31

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

redis, database, cache, queue, infrastructure

## Risk Level

CRITICAL

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md) | Canonical Redis configuration and DB assignments (Section 9.2) |
| [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md) | Redis infrastructure topology |
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Redis as cache layer for PostgreSQL memory |

## Context

Guinevere uses Redis for multiple distinct purposes, each requiring isolation for operational clarity, monitoring, and disaster recovery. During cross-reference validation of the Test Plan, DR Plan, and Ops Manual (2026-05-30), it was discovered that Redis DB assignments were inconsistent across documents:

- **DRPlan** listed: "DB0-DB5: cache, session, queue, buffer, rate-limit, pubsub" — incorrect order.
- **TestPlan** had partial references (DB0 for task queue, DB3 for safe-word state in sessions) that were individually correct but not comprehensive.
- **OpsManual** had no specific DB0-DB5 assignment table.

The canonical reference is `Guinevere_APIIntegration_v2.0.md` Section 9.2, which defines the authoritative Redis configuration with explicit `db=N` assignments.

This ADR canonicalizes the assignments to prevent safety-critical ambiguity, particularly around safe-word state storage (DB3: sessions/working memory).

## Decision Drivers

- Safety-critical: safe-word state lives in Redis and must be in a known, consistent DB.
- Operational clarity: monitoring, alerting, and DR restore scripts need unambiguous DB-to-purpose mapping.
- Canonical alignment: all operational docs must reference the same DB assignments as APIIntegration v2.0.
- Isolation: different eviction policies and persistence strategies per DB purpose.

## Considered Options

1. Assign DBs arbitrarily and document after the fact
2. Use named keys within a single DB (DB0 only)
3. Use separate Redis instances per purpose
4. **Canonicalize DB0–DB5 per APIIntegration v2.0 and enforce across all docs**

## Decision Outcome

Chosen option: **Canonicalize DB0–DB5 per APIIntegration v2.0**.

| DB | Purpose | Eviction Policy | Persistence | Safety Notes |
|---|---|---|---|---|
| DB0 | Task queue | noeviction | AOF + RDB | Job queue integrity critical for autonomous loop |
| DB1 | LLM cache | allkeys-lru | RDB only | Cache is disposable; LRU optimizes hit rate |
| DB2 | Surveillance buffer | allkeys-lfu | AOF | Buffer for Android/Windows sync ingestion |
| DB3 | Sessions / working memory | noeviction | AOF + RDB | **Safe-word state stored here** — must survive restarts |
| DB4 | Pub/Sub | N/A (no persistence) | None | Ephemeral messaging; no keys persist |
| DB5 | Rate limiting | allkeys-lru | RDB only | Sliding window counters; disposable on restart |

### Code Reference (from APIIntegration v2.0 §9.2)

```python
REDIS_TASK_QUEUE = redis.Redis(connection_pool=pool, db=0)
REDIS_LLM_CACHE  = redis.Redis(connection_pool=pool, db=1)
REDIS_SURV_BUFFER = redis.Redis(connection_pool=pool, db=2)
REDIS_SESSION    = redis.Redis(connection_pool=pool, db=3)
REDIS_PUBSUB     = redis.Redis(connection_pool=pool, db=4)
REDIS_RATELIMIT  = redis.Redis(connection_pool=pool, db=5)
```

## Consequences

### Positive

- Eliminates safety-critical ambiguity around safe-word state location.
- Enables DB-specific monitoring, alerting, and DR restore procedures.
- All operational docs now reference a single canonical source.

### Negative

- Requires updating DRPlan (incorrect DB order), OpsManual (missing table), and TestPlan (partial references) to align.

### Risks

- If a new Redis purpose is needed beyond DB5, a new ADR must be created to assign DB6+ or refactor.
- DB4 (pub/sub) has no persistence — subscribers must handle reconnection gracefully.

## Implementation Notes

- All three operational documents (TestPlan v1.0, DRPlan v1.0, OpsManual v1.0) have been patched to reference these canonical assignments.
- DRPlan line 225 was corrected from "cache, session, queue, buffer, rate-limit, pubsub" to "task queue, LLM cache, surveillance buffer, sessions/working memory, pub/sub, rate limiting".
- TestPlan CHAOS-005 (DB0 OOM) and CHAOS-006 (DB3 safe-word preservation) confirmed correct per canonical.
- Future docs must include this ADR in Related Documents when referencing Redis.

## Links

- [`../Guinevere_APIIntegration_v2.0.md`](../Guinevere_APIIntegration_v2.0.md)
- [`../Guinevere_TechnicalArchitecture_v2.0.md`](../Guinevere_TechnicalArchitecture_v2.0.md)
- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)

## Review Record

- Reviewer: Guinevere (Sisyphus orchestrator)
- Review Date: 2026-05-31
- Decision: Accepted
- Notes: Canonicalizes existing APIIntegration v2.0 assignments. All downstream docs patched to align.

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere (Sisyphus) | Initial ADR canonicalizing Redis DB0–DB5 assignments from APIIntegration v2.0. |

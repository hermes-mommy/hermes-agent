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
| DB0 | Rate limiting, persona state, consent grants | noeviction | RDB + AOF | Rate limit 10/min/user (`conversational_handler.py`); `consent:grants` key (`consent.py`); persona FSM state (`cmd_punishment.py`, `cmd_reward.py`, `cmd_casual.py`, `cmd_focus.py`) |
| DB1 | Memory recall | allkeys-lru | RDB only | PostgreSQL+pgvector query cache for recall pipeline |
| DB2 | Surveillance buffer, consent cache | allkeys-lfu | AOF | Event buffer (`redis_buffer.py`, `consumer.py`); consent cache 60s TTL (`consent_gate.py`); replay detection (`replay.py`) |
| DB3 | Agent state | noeviction | RDB only | Agent loop state, task metadata |
| DB4 | Hermes session storage, Discord state | volatile-lru | RDB only | 2hr TTL, 20-turn limit (`session_adapter.py` REDIS_DB=4); session history (`cmd_new_session.py`, `cmd_history.py`) |
| DB5 | Cost tracking, safety plugin state | noeviction | AOF + RDB | MCP cost tracker (`cost.py`, `budget.py`); `guinevere_safety` plugin state; DNR list; safe word cache; search tool counters (`brave_search.py`, `context7.py`, `exa_search.py`) |

> **Updated 2026-06-05**: Redis DB assignments reconciled with runtime state during StepPrompts audit. Runtime code is authoritative. DB0-BD5 purposes shifted significantly from the original APIIntegration v2.0 reference — see table above for current assignments. ADR-035 references DB5 for Hermes safety plugin state and DB4 for Hermes session storage.

### Code Reference (Runtime Authoritative — reconciled 2026-06-05)

```python
# Rate limiting, persona state, consent grants (DB0)
# Used by: conversational_handler.py, cmd_consent.py, cmd_punishment.py, cmd_reward.py, cmd_casual.py, cmd_focus.py
r_db0 = redis.Redis(host="localhost", port=6380, db=0)

# Memory recall cache (DB1)
# Used by: PostgreSQL+pgvector recall pipeline cache
r_db1 = redis.Redis(host="localhost", port=6380, db=1)

# Surveillance buffer, consent cache (DB2)
# Used by: redis_buffer.py, consent_gate.py, consumer.py, replay.py, router.py
r_db2 = redis.Redis(host="localhost", port=6380, db=2)

# Agent state (DB3)
# Used by: agent loop task metadata
r_db3 = redis.Redis(host="localhost", port=6380, db=3)

# Hermes session storage, Discord state (DB4)
# Used by: session_adapter.py (REDIS_DB=4), cmd_new_session.py, cmd_history.py
r_db4 = redis.Redis(host="localhost", port=6380, db=4)

# Cost tracking, safety plugin state (DB5)
# Used by: cost.py, budget.py, guinevere_safety plugin, brave_search.py, context7.py, exa_search.py
r_db5 = redis.Redis(host="localhost", port=6380, db=5)
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
| 1.1 | 2026-06-05 | Guinevere (Sisyphus) | **Reconciled DB assignments with runtime code.** Runtime is authoritative. DB0: Rate limiting/persona state/consent (was Task queue). DB1: Memory recall (was LLM cache). DB2: Surveillance buffer/consent cache (unchanged). DB3: Agent state (was Sessions/working memory). DB4: Hermes sessions/Discord state (was Pub/Sub). DB5: Cost tracking/safety plugin state (was Rate limiting). See ADR-035 for Hermes DB5 safety state usage. Code reference block updated. |

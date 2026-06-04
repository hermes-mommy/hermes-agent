# P7 Surveillance — Redis DB Usage Audit (ADR-030)

**Date**: 2026-06-03  
**Auditor**: Guinevere  
**Reference**: [ADR-030](../../../adr/ADR-030-redis-db-assignments.md)  
**Verdict**: **PASS** ✅

---

## 1. ADR-030 Canonical DB Assignments

| DB | Purpose | Eviction Policy | Persistence |
|----|---------|----------------|-------------|
| DB0 | Task queue | noeviction | AOF + RDB |
| DB1 | LLM cache | allkeys-lru | RDB only |
| DB2 | **Surveillance buffer** | allkeys-lfu | AOF |
| DB3 | Sessions / working memory | noeviction | AOF + RDB |
| DB4 | Pub/Sub | N/A | None |
| DB5 | **Rate limiting / cost tracking** | allkeys-lru | RDB only |

## 2. Surveillance Files Using Redis — DB2 Audit

All 4 surveillance source files that connect to Redis use **DB2 exclusively**:

| File | Line(s) | DB | Connection Type | Key Pattern | TTL |
|------|---------|----|----------------|-------------|-----|
| `src/surveillance/redis_buffer.py` | 199-202 | **2** | `aioredis.Redis()` factory | `surveillance:buffer` | 300s |
| `src/surveillance/replay.py` | 50-57 | **2** | `aioredis.Redis()` lazy singleton | `surveillance:nonce:*` | 660s |
| `src/surveillance/consent_gate.py` | 127-134 | **2** | `aioredis.Redis()` lazy singleton | `consent:surveillance:*` | 300s |
| `src/surveillance/consumer.py` | 398-401 | **2** | `aioredis.Redis()` inline in `main()` | `surveillance:buffer` (via `RedisSurveillanceBuffer`) | 300s |

## 3. DB Conflict Check

### 3.1 Surveillance → DB3/DB5 Access

**Result: NONE** — zero hits.

Grep for `db=3`, `db=5`, `DB3`, `DB5`, `REDIS_SESSION`, `REDIS_RATELIMIT` in `src/surveillance/` returned **only one result** — a docstring comment in `redis_buffer.py` line 9:

```
- DB2 is the dedicated surveillance namespace (cost tracking uses DB5).
```

This is a **documentation note**, not a connection — the actual `db=2` on lines 202, 57, 134, 401 is confirmed.

### 3.2 Other Components Using DB5 (Rate Limiting / Cost Tracking)

These files use **DB5** — no overlap with surveillance:

| File | DB | Key Pattern |
|------|----|-------------|
| `src/mcp/cost.py` | 5 | `tool:cost:*` |
| `src/mcp/budget.py` | 5 | `tool:cost:*`, `cost:current_month` |
| `src/mcp/tools/exa_search.py` | 5 | `tool:cost:exa:*` |
| `src/mcp/tools/context7.py` | 5 | `tool:cost:context7:*` |
| `src/mcp/tools/brave_search.py` | 5 | `tool:cost:brave_search:*` |
| `src/loops/cost.py` | 5 | `loop:cost:*` |
| `src/core/services/cost_tracker.py` | 5 | `cost:current_month`, `cost:current_day`, `cost:by_model:*` |

Even without DB-level isolation, the key namespaces have **zero overlap** — but DB-level separation (`db=2` vs `db=5`) provides an additional hard boundary.

## 4. Key Naming Convention Check

| Component | ADR-030 Expected Key Pattern | Actual Implementation | Match? |
|-----------|------------------------------|----------------------|--------|
| Event buffer | `surveillance:buffer` | `surveillance:buffer` (redis_buffer.py:75) | ✅ PASS |
| Nonce storage | `surveillance:nonce:*` | `surveillance:nonce:{nonce}` (replay.py:39,125) | ✅ PASS |
| Consent cache | `consent:surveillance:*` | `consent:surveillance:{scope}` (consent_gate.py:43,214) | ✅ PASS |

All key patterns match the specified conventions. No surveillance code writes keys outside these prefixes.

## 5. TTL Value Verification

| Component | Expected TTL | Actual TTL | Source | Match? |
|-----------|-------------|------------|--------|--------|
| Event buffer | 300s | **300s** | `redis_buffer.py:76` (`_ttl_seconds = 300`) | ✅ PASS |
| Nonce storage | 660s | **660s** | `replay.py:36` (`NONCE_TTL_SECONDS = 660`) | ✅ PASS |
| Consent cache | 300s | **300s** | `consent_gate.py:46` (`CACHE_TTL_SECONDS = 300`) | ✅ PASS |

### TTL Design Analysis

- Nonce TTL (660s) ≥ 2× timestamp window (300s, `replay.py:33`) — ensures nonce outlives the window it guards. ✅
- Buffer TTL (300s) matches audit expectation — stale events auto-purged after 5 minutes. ✅
- Consent cache TTL (300s) — appropriate for read-heavy consent lookups with `invalidate_cache()` for push-based invalidation. ✅

## 6. Error Handling: Fail-Closed Behavior

All surveillance Redis operations fail-closed:

| Module | Failure Mode | Behavior |
|--------|-------------|----------|
| `redis_buffer.py` | Push/pop/size failure | Returns `False`/`[]`/`0` — caller (endpoint) decides 202 vs 5xx |
| `replay.py` | Redis unreachable | Returns `HTTPException(503)` — request rejected |
| `consent_gate.py` | Redis cache failure | Falls through to DB; only DB failure (after cache miss) triggers fail-closed block |

## 7. Summary

| Check | Result |
|-------|--------|
| All surveillance Redis uses DB2 only | ✅ PASS |
| No surveillance code touches DB3 (sessions) | ✅ PASS |
| No surveillance code touches DB5 (rate limiting/cost) | ✅ PASS |
| Key naming: `surveillance:buffer` | ✅ PASS |
| Key naming: `surveillance:nonce:*` | ✅ PASS |
| Key naming: `consent:surveillance:*` | ✅ PASS |
| No key collisions with cost tracker (`tool:cost:*`, `loop:cost:*`, `cost:*`) | ✅ PASS |
| TTL: buffer = 300s | ✅ PASS |
| TTL: nonce = 660s | ✅ PASS |
| TTL: consent_cache = 300s | ✅ PASS |
| Fail-closed error handling | ✅ PASS |

## 8. Verdict

**PASS** — All 4 surveillance Redis connections use `db=2` exclusively. No DB3, DB5, or any other DB is touched by surveillance code. Key namespaces are isolated and collision-free against cost tracking keys (`tool:cost:*`, `loop:cost:*`, `cost:*` in DB5). All TTL values match specifications. Fail-closed error handling is consistent across all three modules.

No remediation required.

---

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-03 | Guinevere | Initial audit — DB2 compliance verified, all checks PASS |
# Redis DB Usage Analysis — Guinevere Codebase

> **For**: Hermes Session Adapter Phase 1  
> **Target**: DB4 for Hermes session storage  
> **Date**: 2026-06-03  
> **Source Files Scanned**: src/discord/, src/core/, src/loops/, src/mcp/, src/surveillance/, src/memory/

---

## 1. Redis Connection Pattern (Universal)

Every Redis client across the codebase follows the **same connection pattern**:

| Parameter | Value | Source |
|---|---|---|
| **Host** | localhost | Hardcoded in every caller |
| **Port** | 6380 (non-standard) | Hardcoded in every caller |
| **Username** | guinevere_core | Hardcoded in every caller |
| **Password** | os.environ.get("REDIS_PASSWORD", "") | Environment variable |
| **decode_responses** | True | Universal (except cmd_clear_cache which uses False for binary flush) |

**Default fallback**: REDIS_URL env var (used only in src/core/main.py health check):  
edis://localhost:6380/0

---

## 2. DB Allocation Map — Actual vs. Declared

### Declared allocation (from src/mcp/tools/redis_tool.py lines 13-19):

| DB | Declared Purpose | Actually Used? | Actual Usage |
|---|---|---|---|
| **DB0** | Session cache | YES | Rate limiting, persona state, consent grants, punishment/reward logs, interaction/focus mode |
| **DB1** | Memory recall | NO | Not connected to anywhere in production code. Only in test param forwarding. |
| **DB2** | Surveillance buffer | YES | Surveillance event buffer, consumer drain, consent gate cache, replay detection |
| **DB3** | Agent state | NO | Not connected to anywhere in production code. Only in allocation map comment. |
| **DB4** | Discord state | NO | **Not connected to anywhere in production code.** Only in allocation map comment. |
| **DB5** | Cost tracking | YES | CostTracker, LoopCostTracker, MCP tool cost tracking, monthly reports |

### Files connecting to each DB:

| DB | Files (absolute paths) |
|---|---|
| **DB0** | src/discord/conversational_handler.py, src/discord/cmd_casual.py, src/discord/cmd_focus.py, src/discord/cmd_punishment.py, src/discord/cmd_reward.py, src/discord/cmd_consent.py, src/discord/cmd_clear_cache.py |
| **DB2** | src/surveillance/redis_buffer.py, src/surveillance/consumer.py, src/surveillance/consent_gate.py, src/surveillance/replay.py, src/core/main.py |
| **DB5** | src/core/services/cost_tracker.py, src/core/services/monthly_report.py, src/loops/cost.py, src/mcp/cost.py, src/mcp/budget.py, src/mcp/tools/exa_search.py, src/mcp/tools/context7.py, src/mcp/tools/brave_search.py, src/mcp/tools/redis_tool.py, src/discord/cmd_cost.py, src/discord/cmd_cost_alert.py, src/discord/cmd_budget.py |

---

## 3. Key Naming Conventions by DB

### DB0 — Rate Limiting & Persona State

| Key Pattern | Type | Purpose | Source File |
|---|---|---|---|
| rate:chat:{user_id}:{minute_bucket} | String (INCR+EXPIRE) | Per-user rate limiting | conversational_handler.py:172 |
| persona:interaction_mode | String | Casual mode toggle | cmd_casual.py:53 |
| persona:focus_mode | String | Focus mode state | cmd_focus.py:73 |
| persona:punishment_log | JSON String | Punishment history log | cmd_punishment.py:68-79 |
| persona:reward_log | JSON String | Reward history log | cmd_reward.py:53-63 |
| consent:grants | JSON String (SET) | Consent grants set | cmd_consent.py:38 |

### DB2 — Surveillance Buffer

| Key Pattern | Type | Purpose | Source File |
|---|---|---|---|
| surveillance:buffer | List (RPUSH/LRANGE/LTRIM, TTL 300s) | FIFO event buffer | redis_buffer.py:75 |
| Replay detection keys | String (SET NX EX) | Deduplication | replay.py |

### DB5 — Cost Tracking

| Key Pattern | Type | Purpose | Source File |
|---|---|---|---|
| cost:current_month | Float String | Monthly running total | cost_tracker.py:35 |
| cost:current_day | Float String | Daily running total | cost_tracker.py:36 |
| cost:by_model:{model} | Float String | Per-model total | cost_tracker.py:37 |
| cost:daily:{date} | Float String | Daily cost by date | cost_tracker.py:38 |
| cost:monthly:{month} | Float String | Monthly cost by month | cost_tracker.py:39 |
| cost:alert_threshold | Float String | Alert threshold | cmd_cost_alert.py:37 |
| budget:monthly_cap | Float String | Monthly budget cap | cost_tracker.py:48 |
| loop:cost:{loop_id} | Float + Hash | Per-loop cost + counters | loops/cost.py:83 |
| loop:cost:{loop_id}:by_model:{model} | Float String | Per-loop per-model cost | loops/cost.py:84 |
| loop:cost:month:{month} | Set | Active loops in month | loops/cost.py:103 |
| tool:cost:exa:{date} | Counter (INCR) | Exa daily cost | exa_search.py |
| tool:cost:context7:{date} | Counter (INCR, TTL 2d) | Context7 daily calls | context7.py:170 |
| tool:cost:brave:{date} | Counter (INCR) | Brave daily cost | brave_search.py |

### Key naming pattern observed:
- **Delimiter**: Colon (:) — Redis convention
- **Prefix convention**: {domain}:{subdomain}:{identifier}
  - cost:* for global cost tracking
  - loop:cost:* for per-loop cost tracking
  - 	ool:cost:* for per-tool cost tracking
  - persona:* for persona state
  - consent:* for consent state
  - ate:chat:* for rate limiting
  - surveillance:* for surveillance
  - udget:* for budget caps

---

## 4. DB4 — Verified Unused

**No production code connects to DB4.** Zero Redis(host=..., port=..., db=4, ...) or db=4 in any .py file.

The only references to DB4 in the entire codebase:
1. src/mcp/tools/redis_tool.py:18 — Allocation map comment: DB4: Discord state
2. README.md — Stack table mentions Redis (DB0-DB5)

**Confirmation**: DB4 is safe for Hermes Session Adapter session storage.

---

## 5. Connection Code Template for HermesSessionAdapter

For asynchronous operations (recommended for Hermes):
`python
import redis.asyncio as aioredis

_redis = aioredis.Redis(
    host="localhost",
    port=6380,
    db=4,
    username="guinevere_core",
    password=os.environ.get("REDIS_PASSWORD", ""),
    decode_responses=True,
)
`

For synchronous operations:
`python
import redis

_redis = redis.Redis(
    host="localhost",
    port=6380,
    db=4,
    username="guinevere_core",
    password=os.environ.get("REDIS_PASSWORD", ""),
    decode_responses=True,
)
`

---

## 6. Key Naming Recommendation for Hermes Sessions

Follow the existing colon-delimited convention:

- hermes:session:{session_id} — Session data (Hash or JSON String)
- hermes:session:{session_id}:ttl — TTL tracking
- hermes:session:index:{user_id} — User-to-session mapping
- hermes:session:expiry — Sorted set for expiry sweeps

Suggested prefix: hermes:session:*

---

## 7. Files Scanned

| Directory | Files with Redis | DBs Used |
|---|---|---|
| src/discord/ | 11 files | DB0 (7 files), DB5 (3 files) |
| src/core/ | 2 files | DB5 (1 file), DB2 (1 file) |
| src/loops/ | 1 file | DB5 |
| src/mcp/ | 6 files | DB5 (all) |
| src/surveillance/ | 5 files | DB2 (all) |
| src/memory/ | 0 files | None |

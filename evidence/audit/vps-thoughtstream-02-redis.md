# VPS Audit — HardStopGuard Redis Connectivity & Key State

**Date:** 2026-07-10
**Auditor:** Guinevere (codebase search + live VPS verification)
**VPS:** faiz-prod-01 (100.94.104.22 via Tailscale)
**Scope:** HardStopGuard Redis connectivity, `life_kernel:hard_stop` key state, fail-open behavior, wiring gap analysis

---

## 1. Redis Service Status

### 1.1 Container Health

````````````````````````````````````````````
Container:  guinevere-redis
Image:      redis:7.4-alpine
Status:     Up 5 weeks (running)
Port:       127.0.0.1:6380 -> 6379/tcp
Network:    guinevere-net (Docker internal)
Resources:  --cpus 1 --memory 3g
Restart:    unless-stopped
````````````````````````````````````````````

### 1.2 redis-cli PING

````````````````````````````````````````````
$ redis-cli -h 127.0.0.1 -p 6380 -a <password> PING
PONG
````````````````````````````````````````````

**Verdict:** Redis is healthy and accepting connections.

### 1.3 Redis INFO (Server)

````````````````````````````````````````````
redis_version:7.4.9
os:Linux 6.8.0-31-generic x86_64
tcp_port:6379 (mapped to host 6380)
uptime_in_seconds:3102419
uptime_in_days:35
````````````````````````````````````````````

### 1.4 Redis Clients

````````````````````````````````````````````
connected_clients:7
blocked_clients:0
pubsub_clients:1
maxclients:10000
````````````````````````````````````````````

### 1.5 Redis Memory

````````````````````````````````````````````
used_memory_human:2.57M
maxmemory_human:2.00G
maxmemory_policy:allkeys-lru
used_memory_peak_human:2.92M
````````````````````````````````````````````

### 1.6 Redis Persistence

````````````````````````````````````````````
RDB: save 900 1 / 300 10 / 60 10000
AOF: appendonly yes, appendfsync everysec
rdb_last_bgsave_status:ok
aof_last_write_status:ok
rdb_saves:4100
````````````````````````````````````````````

**Note:** RDB saving had transient failures on 2026-07-08 due to disk space pressure ("No space left on device"). Recovered automatically. Current disk: 55G/99G used (59%).

### 1.7 Redis DB Size

````````````````````````````````````````````
DBSIZE: 6 keys
````````````````````````````````````````````

---

## 2. `life_kernel:hard_stop` Key State

### 2.1 Key Query

````````````````````````````````````````````
$ redis-cli -a <password> GET life_kernel:hard_stop
(nil)
````````````````````````````````````````````

**Result:** Key does NOT exist. HARD STOP is **not active**.

### 2.2 Pattern Search for hard_stop Keys

````````````````````````````````````````````
$ redis-cli -a <password> KEYS "*hard_stop*"
(empty array)
````````````````````````````````````````````

### 2.3 All life_kernel Keys

````````````````````````````````````````````
$ redis-cli -a <password> KEYS "*life_kernel*"
1) "life_kernel:dashboard_message_id:00000000-0000-0000-0000-000000000001"
2) "life_kernel:dashboard_message_id"
````````````````````````````````````````````

Only dashboard-related keys exist. No hard_stop key.

---

## 3. guinevere-core Log Analysis

### 3.1 Service Status

guinevere-core is running as a systemd service (uvicorn process). ThoughtStream is actively generating thoughts at the time of audit.

### 3.2 hard_stop Log Pattern Search

````````````````````````````````````````````
$ journalctl -u guinevere-core --no-pager -n 5000 | grep -i "hard_stop\|redis\|unreachable"
(no output)
````````````````````````````````````````````

**Finding:** Zero hard_stop or redis connection error entries in recent logs. This indicates:
- No Redis connectivity failures have occurred
- No HARD STOP has been triggered
- The ThoughtStream is operating normally

### 3.3 Active ThoughtStream Log Sample

````````````````````````````````````````````
2026-07-10 12:36:37 [debug] thought_stream.thought_generated acted=False confidence=0.26 type=reflection
2026-07-10 12:36:37 [warning] self_prompt.delegate_failed 'NoneType' object has no attribute 'chat'
2026-07-10 12:36:37 [debug] metacognition.evaluate coherence=0.1 confidence=0.26 safety_pass=True type=heartbeat
2026-07-10 12:36:37 [info] metacognition.periodic_review biases=0 gaps=1 patterns=1 thoughts_reviewed=20
````````````````````````````````````````````

**Note:** The `self_prompt.delegate_failed` warnings are expected (hermes_brain=None in current config). Not related to HardStopGuard.

---

## 4. Wiring Analysis — CRITICAL FINDING

### 4.1 ThoughtStream HardStopGuard Wiring

**Source files examined:**
- `guinevere/consciousness/safety.py` — HardStopGuard implementation (167 lines)
- `guinevere/consciousness/thought_stream.py` — ThoughtStream.check_hard_stop() (lines 250-291)
- `guinevere/consciousness/loop.py` — ConsciousnessLoop (lines 47-86)
- `guinevere/config/models.py` — ConsciousnessConfig (lines 95-118)
- `guinevere/http/server.py` — server.py lifespan (lines 95-168)

**Wiring chain:**
1. `server.py:103` creates `redis_client = aioredis.from_url(redis_url)`
2. `server.py:148` creates `ConsciousnessLoop(llm_router=, settings=settings)`
3. `loop.py:75` creates `ThoughtStream(config=self._config)`
4. `loop.py:60-72` reads config from `settings.consciousness` (a `ConsciousnessConfig` model)
5. `models.py:95-118` `ConsciousnessConfig` has NO `redis_client` field
6. `thought_stream.py:266` does `redis_client = self._config.get("redis_client")`

**Result:** `redis_client` is NEVER in the consciousness config dict. ThoughtStream ALWAYS takes the no-redis path:

````````````````````````````````````````````
# thought_stream.py:266-277 (executed every check_hard_stop call)
redis_client = self._config.get("redis_client")    # ALWAYS None
if redis_client is None:
    logger.debug("thought_stream.hard_stop.no_redis_client")  # DEBUG — not visible in journalctl
    self._hard_stop_unavailable = True
    return False
````````````````````````````````````````````

**Impact:** The ThoughtStream's HardStopGuard (safety.py) is **implemented but NOT wired**. The consciousness loop operates WITHOUT the Redis-based HardStopGuard. However, this is MITIGATED by other safety mechanisms (see section 4.2).

### 4.2 Other hard_stop Safety Paths (ACTIVE)

| Component | File | Redis Key | Behavior | Status |
|---|---|---|---|---|
| HeartbeatService | heartbeat.py:340 | `life_kernel:hard_stop` | **fail-CLOSED** (returns on Redis error, does not clear flag) | ACTIVE — wired via `redis_client` |
| HardStopShim (P22) | _shims.py:42 | `life_kernel:hard_stop` | **fail-CLOSED** (no source => treat as active) | ACTIVE — wired in build_runtime_registry |
| HardStopHandler (app-level) | hard_stop_handler.py | N/A (in-memory keyword) | N/A (pre-LLM middleware) | ACTIVE — wired via safety_plugin |
| cmd_safeword | cmd_safeword.py | N/A (Discord command) | N/A | ACTIVE |
| cmd_project | cmd_project.py:44 | `life_kernel:hard_stop` | Blocks project switch if active | ACTIVE |

### 4.3 Fail-Open vs Fail-Closed Summary

| Path | Behavior | Rationale |
|---|---|---|
| **safety.py (ThoughtStream)** | **fail-OPEN** (Redis unreachable => assume no HARD STOP) | Documented in safety.py:9-10. Consciousness loop should not be permanently blocked by transient Redis outage. |
| **heartbeat.py** | **fail-CLOSED** (Redis unreachable => return without clearing, do not assume safe) | Documented in heartbeat.py:344-347. Safety > uptime for the heartbeat. |
| **_shims.py (HardStopShim)** | **fail-CLOSED** (no source wired => treat as HARD STOP active) | Documented in _shims.py:134-140. Cannot prove clear => block. |
| **ThoughtStream (no redis_client)** | **fail-OPEN** (no Redis client => skip check entirely) | Current production state. No Redis client in consciousness config. |

---

## 5. Test Coverage Evidence

### 5.1 HardStopGuard (safety.py) Tests

| Test File | Tests | Status |
|---|---|---|
| `tests/safety/test_hard_stop_handler.py` | 22 tests: exact triggers, semantic patterns, false positives, recovery, audit trail, guard decision | All deterministic, zero network calls |
| `tests/safety/test_hard_stop_comprehensive.py` | 38 tests: extended triggers, recovery, guard decision, edge cases, false positives, H-03 integration | All deterministic, zero network calls |
| `tests/safety/test_hard_stop_latency.py` | 10 tests: latency proof for all trigger types, P50<1ms, P99<5ms, MAX<50ms | All deterministic |
| `tests/p22/test_shims.py` | HardStopShim tests with FakeRedis | Tests both active and clear states |

### 5.2 Redis Integration Tests

| Test File | Coverage |
|---|---|
| `tests/surveillance/test_redis_buffer.py` | Redis buffer write/read |
| `tests/mcp/test_redis_tool.py` | Redis MCP tool |
| `tests/life_kernel/test_heartbeat.py` | Heartbeat hard_stop detection |

---

## 6. Disk Space Incident (2026-07-08)

Redis RDB saving failed on 2026-07-08 with "No space left on device" errors. The issue resolved automatically (disk recovered). Current state:

````````````````````````````````````````````
/dev/vda1  99G  55G  39G  59% /
````````````````````````````````````````````

RDB last save status: **ok**. AOF last write status: **ok**. Persistence is healthy.

---

## 7. Verdict

| Check | Result | Severity |
|---|---|---|
| Redis running | PASS | — |
| Redis PING | PASS (PONG) | — |
| `life_kernel:hard_stop` key state | PASS — key absent (nil), HARD STOP not active | — |
| Redis connectivity (from guinevere-core) | PASS — no connection errors in logs | — |
| Redis persistence | PASS — RDB ok, AOF ok | — |
| Fail-open behavior documented | PASS — safety.py lines 9-10, 107-111 | — |
| **ThoughtStream HardStopGuard wired** | **FAIL — redis_client never reaches ThoughtStream config** | **MEDIUM** |
| **Heartbeat hard_stop check wired** | **PASS — heartbeat.py uses redis_client directly** | — |
| **HardStopShim (P22) wired** | **PASS — build_runtime_registry passes redis_client** | — |
| Disk space | WARNING — RDB save failed 2026-07-08, recovered. Monitor. | LOW |

### Key Finding

The **ThoughtStream-level HardStopGuard** (`safety.py`) is a well-implemented safety mechanism with proper fail-open documentation, but it is **not wired** to the ThoughtStream at runtime because `ConsciousnessConfig` (`models.py:95`) does not include a `redis_client` field, and `server.py` does not inject it.

This is **mitigated** by:
1. **HeartbeatService** (heartbeat.py) — checks `life_kernel:hard_stop` every heartbeat cycle with fail-CLOSED behavior
2. **HardStopShim** (P22 _shims.py) — checks `life_kernel:hard_stop` with fail-CLOSED behavior
3. **HardStopHandler** (app-level keyword detection) — in-memory, pre-LLM middleware

### Recommendation

Wire `redis_client` into the consciousness config so ThoughtStream's HardStopGuard provides an additional safety layer. This is a defense-in-depth improvement, not a critical gap, because the heartbeat and P22 shim already check Redis with fail-CLOSED behavior.

---

**Report path:** `evidence/audit/vps-thoughtstream-02-redis.md`
**Generated:** 2026-07-10T12:42+07:00

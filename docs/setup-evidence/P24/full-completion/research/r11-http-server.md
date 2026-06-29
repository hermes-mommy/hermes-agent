# Domain 11 Research: HTTP Server — FastAPI Embedded, Lifespan Context, Health Endpoints, Concurrency

**Generated**: 2026-06-29  
**Method**: File reads, grep searches across `src/core/`, `.venv/Lib/site-packages/run_agent.py`, `.venv/Lib/site-packages/gateway/`, P24 plan docs, and `.env.example`. Every claim below is grounded in file:line citations from the live codebase.

---

## 1. Summary

The existing Guinevere codebase has a **complete, production-deployed FastAPI application** in `src/core/main.py` (1052 lines) with lifespan context manager, health endpoints, Prometheus metrics, rate limiting, HMAC auth, and extensive background-task orchestration. The P24 M15 plan calls for creating a clean `guinevere/http/` package that absorbs this functionality while stripping HARD STOP / consent / safe-mode patterns (per ADR-062). The primary architectural challenge is composing the FastAPI lifespan with M3's ConsciousnessLoop TaskGroup and Hermes's own `run_agent.py` conversation loop — all running as concurrent asyncio tasks in a single event loop, with `--workers 1`.

---

## 2. Existing `src/core/main.py` — Full Inventory

### 2.1 FastAPI App Instantiation

**File**: `src/core/main.py:847-851`

```python
app = FastAPI(
    title="Guinevere Core",
    version="0.1.0",
    lifespan=lifespan,
)
```

Single app instance, `lifespan` function passed at construction time. No uvicorn config in-code — invoked externally via `uvicorn src.core.main:app`.

### 2.2 Lifespan Context Manager (lines 239-845)

**File**: `src/core/main.py:238-247` — declaration:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from src.loops.manager import LoopManager
    from src.core.services.hard_stop_handler import HardStopHandler
```

The lifespan is ~600 lines long. It performs the following startup operations in sequence:

| # | Service | Lines | Mechanism | app.state key |
|---|---------|-------|-----------|---------------|
| 1 | Sentry init | 244-248 | `init_sentry()` | — |
| 2 | LLM metrics server | 251-254 | `start_llm_metrics_server(port=9191)` (daemon thread) | — |
| 3 | HermesBrain (P20) | 257-274 | `HermesBrain(config)` | `hermes_brain` |
| 4 | LoopManager | 281 | `LoopManager(llm_router=None)` | `loop_manager` |
| 5 | HardStopHandler | 285-291 | wired to guardian | `hard_stop_handler` |
| 6 | Guardian monitor | 293-297 | `asyncio.create_task(guardian.monitor())` | `guardian_task` |
| 7 | Monthly report scheduler | 300-304 | APScheduler | `report_scheduler` |
| 8 | Surveillance consumer | 307-349 | `asyncio.create_task(consumer.run())` | `surveillance_task`, `surveillance_consumer`, `surveillance_engine` |
| 9 | KG ingestion cron | 352-385 | APScheduler + pipeline | `kg_scheduler` |
| 10 | Life mind graph (P20) | 388-712 | Postgres checkpointer, HermesBrain, KG/memory/journal adapters, Redis, Discord REST, HeartbeatService | `life_mind_graph`, `heartbeat`, `discord_rest`, etc. |
| 11 | P22 Integration Hub | 638-696 | build_runtime_registry, scheduler | `p22_registry`, `p22_router`, `p22_scheduler` |
| 12 | Cognition Registry (P19) | 703-710 | ProjectAwareCognitionRegistry | `cognition_registry` |
| 13 | Hermes Bridge (P5) | 716-725 | create_hermes_bridge | `hermes_bridge` |
| 14 | Boot resume (P5) | 728-732 | `loop_manager.resume_pending_loops()` | — |
| 15 | Environment Monitor (P5) | 735-744 | EnvironmentMonitor | `env_monitor` |

**Shutdown sequence** (lines 748-845): reverse-order cleanup — heartbeat stop, cognition stop, Discord close, engine dispose, scheduler shutdown, HermesBrain dispose, bridge stop, surveillance consumer stop, guardian stop + cancel.

### 2.3 Background Task Pattern

All background services use `asyncio.create_task()` — NOT `asyncio.TaskGroup`. Examples:

- `src/core/main.py:293` — `asyncio.create_task(loop_manager.guardian.monitor(), name="guardian-monitor")`
- `src/core/main.py:341` — `asyncio.create_task(_consumer.run(), name="surveillance-consumer")`

Tasks are stored on `app.state` and cancelled in shutdown. This is the standard FastAPI pattern — no TaskGroup is used.

### 2.4 Health Endpoints

| Endpoint | Lines | Returns | Auth |
|----------|-------|---------|------|
| `GET /health` | 916-918 | `{"status":"healthy","service":"guinevere-core","version":"0.1.0"}` | None |
| `GET /health/detailed` | 921-1008 | Per-component status: loop_manager, guardian, redis, postgresql, 9router | None |
| `GET /status` | 1011-1032 | Full EnvironmentMonitor snapshot (CPU, memory, disk, services) | None |
| `GET /metrics` | 910-913 | Prometheus exposition format | None |
| `GET /` | 1035-1037 | `{"message":"Guinevere de Baroque is online.","status":"active"}` | None |

**`/health/detailed`** (lines 921-1008) checks:
- `loop_manager`: calls `list_loops()`, returns active count
- `guardian`: checks `guardian_task.done()`
- `redis`: `redis.asyncio` ping with 2s timeout
- `postgresql`: `asyncpg.connect` with 2s timeout
- `9router`: `httpx.AsyncClient` GET to `http://localhost:20128/v1/models`

Returns HTTP 503 if loop_manager or guardian fails. Redis and postgresql are fail-soft (don't force 503).

### 2.5 Middleware Stack

| Middleware | Lines | Purpose |
|-----------|-------|---------|
| `_PrometheusMiddleware` | 879-897 | Request count + duration histograms |
| `RateLimitMiddleware` | 905-907 | In-process rate limiting (60 GET/60s, 10 POST/60s, 5 dry-run/60s) |

Rate limiter exempts `/metrics`, `/health`, `/` (line 106 in `rate_limit.py`).

### 2.6 Auth

**File**: `src/core/api/auth.py:15-28` — `hmac.compare_digest` against `GUINEVERE_API_KEY` env var. Used as FastAPI dependency `Depends(get_api_key)` on mutation endpoints only (reads are unauthenticated).

### 2.7 Routers Mounted

- `src/core/api.routes` (loop management + P22 integration) at line 1043-1045
- `src.surveillance.router` (surveillance webhook) at line 1050-1052

---

## 3. Hermes `run_agent.py` — No Embedded Server

**File**: `.venv/Lib/site-packages/run_agent.py` (4617 lines)

`run_agent.py` is a pure agent class (`AIAgent`). It has:

- `run_conversation()` at line 4360-4371 — forwards to `agent.conversation_loop.run_conversation`
- `chat()` at line 4373-4391 — simple wrapper returning string
- NO `asyncio.run()` except a single test utility at line 3538
- NO FastAPI, no web server, no lifespan pattern
- NO `asyncio.TaskGroup` anywhere in the file (grep confirmed zero matches across entire `.venv/Lib/site-packages/`)

The AIAgent is designed to be instantiated per-request by the gateway (`gateway/run.py`), not to own the event loop.

### 3.1 Hermes Gateway Concurrency Model

**File**: `.venv/Lib/site-packages/gateway/run.py`

- Entry: `start_gateway()` at line 18370, called via `asyncio.run()` at line 18860
- Uses `asyncio.create_task()` for background workers (lines 4378-4410): process watcher, session expiry, kanban notifier, kanban dispatcher, platform reconnect, handoff watcher
- Background tasks tracked in `self._background_tasks: set` (line 1876) with `add_done_callback(discard)`
- No TaskGroup anywhere in the gateway either
- Gateway uses `aiohttp.web` (NOT FastAPI) for its own API server (`gateway/platforms/api_server.py`)

---

## 4. P24 M15 Design Requirements

### 4.1 From the Plan

**File**: `docs/setup-evidence/P24/plan/p24-hermes-native-fork-enterprise-plan.md:926-958`

Key requirements:
- FastAPI embedded in fork with `lifespan` context manager
- `--workers 1` (single process, asyncio)
- All process-scoped resources initialized in lifespan: DB pool, Redis client, circuit breaker set, memory store
- Endpoints: `/health` (liveness), `/health/ready` (readiness: PG + Redis + consciousness), `/health/agent` (agent state), `/metrics` (Prometheus)
- `asyncio.Semaphore` for concurrency limiting on HTTP-triggered agent interactions
- Shutdown: `asyncio.Event` + graceful agent task cancellation with 30s timeout

### 4.2 Files to Create

- `guinevere/http/__init__.py`
- `guinevere/http/server.py` (~200 lines: FastAPI app, lifespan, startup/shutdown)
- `guinevere/http/routes.py` (~150 lines: health, ready, agent endpoints)
- `guinevere/http/health.py` (~100 lines: health check logic, readiness probe)

### 4.3 Files to Modify

- `run_agent.py`: Add HTTP server startup alongside agent loop
- `agent/agent_init.py`: Wire HTTP server, expose health state
- `guinevere/config/models.py`: Add `HttpConfig` (host, port, workers, cors_origins)

### 4.4 Collision Analysis: M3 TaskGroup vs M15

**File**: `docs/setup-evidence/P24/plan/p24-hermes-native-fork-enterprise-plan.md:321`

```
| `run_agent.py` | Register guinevere modules, TaskGroup for consciousness | M1, M3, M15 |
```

Both M3 (consciousness loop) and M15 (HTTP server) modify `run_agent.py`. The plan explicitly identifies this collision at `p24-v3-implementation-master-prompt.md:270`:

> W6: M3 Consciousness Loop (depends on W2 — **both modify `run_agent.py`**)

The M3 consciousness loop design (`plan:413`) calls for:
> "Seven substrates running as concurrent asyncio tasks via `asyncio.TaskGroup`"

M3 adds a `TaskGroup` inside `run_agent.py` for consciousness background tasks. M15 adds HTTP server startup. The collision is real but manageable:
- M3's TaskGroup is for consciousness substrates only (heartbeat, active cognition, reflection, etc.)
- M15's FastAPI server runs its own lifespan which spawns/monitors those same substrates
- The resolution: M15's lifespan owns the TaskGroup; M3's consciousness loop runs INSIDE the lifespan's TaskGroup, not competing with it

**Key insight**: The plan says M3's `ConsciousnessLoop` runs as a "background TaskGroup alongside conversation loop" (line 431). M15's lifespan starts the consciousness loop. These are not competing — M15 provides the lifecycle container, M3 provides the substrate logic.

---

## 5. Design for `guinevere/http/server.py`

### 5.1 What Gets Ported from `src/core/main.py`

The P24 plan (`plan:930`) says M15 **absorbs and deletes** `src/core/main.py` (931 lines). The new server.py must carry forward:

| Component | Source lines | Disposition |
|-----------|-------------|-------------|
| FastAPI app construction | main.py:847-851 | PORT |
| Lifespan context manager | main.py:239-845 | REWRITE (strip HARD STOP, consent, simplify) |
| `/health` endpoint | main.py:916-918 | PORT |
| `/health/detailed` endpoint | main.py:921-1008 | PORT (rename to `/health/ready`) |
| `/metrics` endpoint | main.py:910-913 | PORT |
| `/status` endpoint | main.py:1011-1032 | PORT |
| Prometheus middleware | main.py:856-897 | PORT |
| Rate limit middleware | main.py:905-907 | PORT |
| LoopManager + guardian | main.py:281-297 | PORT (still needed for loops) |
| HermesBrain | main.py:257-274 | PORT |
| Surveillance consumer | main.py:307-349 | MOVE to M16 |
| KG scheduler | main.py:352-385 | MOVE to M6 |
| Life mind graph + heartbeat | main.py:388-712 | MOVE to M9 |
| P22 integration hub | main.py:638-696 | MOVE to M8 |
| Cognition registry | main.py:703-710 | MOVE to M3 |

### 5.2 What Gets Deleted (ADR-062 / Forbidden Patterns)

Per `plan:957`: **Forbidden patterns**: `HARD_STOP`, `hard_stop`, `consent`, `safe_mode`, `# type: ignore`

Components to strip from the ported lifespan:
- `HardStopHandler` (main.py:285-291) — DELETE per M2
- `consent_session_factory` (main.py:648-649) — DELETE per M11
- `consent_checker` (main.py:660-663) — DELETE per M11
- `build_audit_writer` consent-related code paths — DELETE

### 5.3 New Components (Not in Current Codebase)

Per `plan:939`:
- **`/health/agent`** endpoint — agent-specific health (current turn, token usage, emotion state). This is NEW — does not exist in `src/core/main.py`. Will need `AIAgent` state exposure.
- **`asyncio.Semaphore` for HTTP concurrency** — NEW. Current code has no such limit on HTTP-triggered agent interactions.
- **`asyncio.Event` shutdown coordination** — NEW. Current code uses `asyncio.CancelledError` pattern.

### 5.4 Concurrency Model

**Single-process asyncio** (`--workers 1`). The event loop runs:

1. **FastAPI/uvicorn** — serves HTTP requests via ASGI
2. **Consciousness loop TaskGroup** (M3) — 7 substrate tasks
3. **Conversation loop** — agent `run_conversation()` calls
4. **Background services** — surveillance, KG, heartbeat, etc.

All are `asyncio` coroutines on a single thread. No `threading.Thread` for HTTP. The only thread usage is the Prometheus metrics daemon thread (`llm_metrics.py:87`: `start_http_server(port)` which is `prometheus_client`'s built-in threaded server).

**HTTP-triggered agent interactions** are gated by `asyncio.Semaphore(max_concurrent)` to prevent unbounded concurrent LLM calls. This is distinct from the sub-agent semaphore (`guinevere/iteration_budget.py`) which caps recursive delegation.

### 5.5 Composition with M3 TaskGroup

The design resolves the M3/M15 collision as follows:

```
async def lifespan(app: FastAPI):
    # Phase 1: Initialize shared resources (DB, Redis, config)
    # Phase 2: Start consciousness loop as a TaskGroup
    async with asyncio.TaskGroup() as tg:
        tg.create_task(consciousness_loop.start())  # M3
        tg.create_task(surveillance_consumer.run())  # M16
        # ... other background tasks
        yield  # FastAPI serves requests here
    # Phase 3: TaskGroup exit cancels all tasks gracefully
```

The `yield` inside `TaskGroup` means:
- While the app is running, all background tasks are alive
- When the lifespan exits (SIGTERM), the TaskGroup cancels all tasks
- This replaces the current ad-hoc `asyncio.create_task()` + manual `task.cancel()` + `await task` + `except CancelledError` pattern

**Important**: `asyncio.TaskGroup` is Python 3.11+. The codebase targets Python 3.12+ (`.venv` has `cpython-312` and `cpython-314` bytecode, confirmed in `src/core/__pycache__/`).

### 5.6 Readiness vs Liveness

**`/health`** (liveness): Returns 200 if the process is alive and the lifespan has started. No dependency checks. This is a Kubernetes liveness probe.

**`/health/ready`** (readiness): Checks that the app is ready to serve traffic. Mirrors the existing `/health/detailed` logic (main.py:921-1008):
- PostgreSQL connectivity (asyncpg ping, 2s timeout)
- Redis connectivity (redis.asyncio ping, 2s timeout)
- Consciousness loop running (check TaskGroup task status)
- LoopManager initialized
- Guardian task alive

Returns 503 if any critical dependency is down. Redis and PostgreSQL are checked independently — a single failure does not block the others.

---

## 6. What Exists in the Existing Codebase (Ground Truth)

### 6.1 Existing `src/core/main.py` Health Endpoints

The current `/health/detailed` (main.py:921-1008) already checks:
- loop_manager (list_loops)
- guardian (task.done())
- redis (async ping)
- postgresql (asyncpg connect + SELECT 1)
- 9router (httpx GET /v1/models)

This is very close to the P24 `/health/ready` spec. The main delta is adding consciousness loop status and emotion state.

### 6.2 Existing Rate Limiter

`src/core/api/rate_limit.py` (149 lines) — fully self-contained, no `slowapi` dependency, uses `collections.deque` with capped dict size. Can be ported directly.

### 6.3 Existing Prometheus Middleware

`src/core/main.py:856-897` — `_PrometheusMiddleware` using `prometheus_client` Counter + Histogram. Simple `BaseHTTPMiddleware` subclass. Can be ported directly.

### 6.4 Existing Auth

`src/core/api/auth.py` (55 lines) — HMAC-based API key validation. Can be ported directly. Per M11, the consent-related auth gates are removed, but the basic API key auth stays.

### 6.5 Existing Routes

`src/core/api/routes.py` (635 lines) — loop management + P22 integration endpoints. These will be refactored into `guinevere/http/routes.py` with loop management retained and P22 integration moved to M8.

---

## 7. Disposition for P24

### 7.1 PORT (Move As-Is with Minimal Changes)

| Source | Target | Notes |
|--------|--------|-------|
| `src/core/main.py:847-851` (app construction) | `guinevere/http/server.py` | Exact copy |
| `src/core/main.py:910-913` (/metrics) | `guinevere/http/routes.py` | Exact copy |
| `src/core/main.py:916-918` (/health) | `guinevere/http/routes.py` | Exact copy |
| `src/core/api/rate_limit.py` | `guinevere/http/rate_limit.py` | Exact copy, fix imports |
| `src/core/api/auth.py` | `guinevere/http/auth.py` | Exact copy, fix imports |
| `src/core/main.py:856-897` (Prometheus middleware) | `guinevere/http/middleware.py` | Exact copy |

### 7.2 REWRITE (Significant Restructuring)

| Source | Target | What Changes |
|--------|--------|-------------|
| `src/core/main.py:239-845` (lifespan) | `guinevere/http/server.py` | Strip HARD STOP (line 285-291), consent (lines 648-663), adopt TaskGroup, wire M3 consciousness loop |
| `src/core/main.py:921-1008` (/health/detailed) | `guinevere/http/health.py` | Add consciousness loop status, emotion state; rename to `/health/ready`; remove 9router check (moves to M8) |
| `src/core/api/routes.py` | `guinevere/http/routes.py` | Strip P22 endpoints (lines 229-634), keep loop management (lines 150-221) |

### 7.3 DELETE (Not Ported)

| Source | Reason |
|--------|--------|
| `src/core/main.py:285-291` (HardStopHandler) | M2 removes HARD STOP entirely |
| `src/core/main.py:648-663` (consent session/checker) | M11 removes consent gate |
| `src/core/main.py:23-115` (build_audit_writer with consent) | Consent paths removed |
| `src/core/main.py:118-187` (consent session factory/checker builders) | M11 deletes |
| `src/core/api/routes.py:229-634` (P22 integration endpoints) | Moves to M8 |

### 7.4 MODIFY-CREATE (New Code)

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `guinevere/http/__init__.py` | 5 | Package marker |
| `guinevere/http/server.py` | ~200 | FastAPI app + lifespan with TaskGroup |
| `guinevere/http/routes.py` | ~150 | Health, ready, agent, metrics, loop endpoints |
| `guinevere/http/health.py` | ~100 | Health check logic, readiness probe |
| `guinevere/http/auth.py` | ~55 | HMAC auth (ported from auth.py) |
| `guinevere/http/rate_limit.py` | ~149 | Rate limiter (ported from rate_limit.py) |
| `guinevere/http/middleware.py` | ~40 | Prometheus middleware (ported) |

---

## 8. Risks

### R1: Lifespan Complexity (MEDIUM)

The current lifespan is ~600 lines of sequential initialization with 15+ try/except blocks. Rewriting it with TaskGroup is architecturally cleaner but introduces risk: a failure in one TaskGroup child cancels ALL children (Python 3.11+ TaskGroup semantics). The current code handles each service independently via try/except — a TaskGroup changes this to all-or-nothing.

**Mitigation**: Use nested TaskGroups or start critical services before the TaskGroup, with only non-critical services inside it. The consciousness loop (M3) gets its own inner TaskGroup.

### R2: M3/M15 File Collision on `run_agent.py` (LOW)

Both M3 and M15 modify `run_agent.py`. The plan sequences M15 (W4) before M3 (W6) — M15 runs in Group B, M3 in Group C. M15's changes to `run_agent.py` are append-only (add HTTP server startup), so M3 can build on top.

**Mitigation**: M15 adds a clear `# --- M15 HTTP server block ---` comment marker. M3 appends below it.

### R3: Prometheus Metrics Port Conflict (LOW)

Currently two Prometheus HTTP servers: port 9191 (LLM metrics, `llm_metrics.py:87`) and the main FastAPI app's `/metrics` endpoint. P24 consolidates to a single `/metrics` on the FastAPI app. The daemon-thread `start_http_server(9191)` must be removed.

**Mitigation**: Move all metric definitions to `guinevere/observability/metrics.py` (M16). Remove `start_llm_metrics_server()` call from lifespan.

### R4: Single Worker Concurrency Ceiling (LOW)

`--workers 1` means all HTTP requests, agent turns, and consciousness substrates share one event loop. A blocking call (e.g., synchronous DB query) starves everything.

**Mitigation**: All code is already async (`async/await`). The existing codebase uses `asyncpg`, `redis.asyncio`, `httpx.AsyncClient`. No synchronous DB calls found in the lifespan or routes.

### R5: Shutdown Ordering (MEDIUM)

The current shutdown is carefully ordered (heartbeat first, then cognition, then Discord, then engines, then schedulers, then guardian). TaskGroup exit cancels all tasks simultaneously. This may not preserve the ordering guarantees.

**Mitigation**: Implement a two-phase shutdown: (1) signal stop to services via `asyncio.Event`, (2) wait for graceful drain with 30s timeout, (3) cancel remaining tasks. This matches the plan's specification.

---

## 9. Evidence Summary

| Claim | Evidence |
|-------|----------|
| FastAPI app exists in `src/core/main.py` | `main.py:847-851` |
| Lifespan context manager | `main.py:238-247`, 600+ lines |
| `/health` endpoint | `main.py:916-918` |
| `/health/detailed` with PG/Redis/guardian checks | `main.py:921-1008` |
| Prometheus metrics | `main.py:856-897`, `main.py:910-913` |
| Rate limit middleware | `main.py:905-907`, `rate_limit.py:1-149` |
| HMAC auth | `auth.py:15-28` |
| `asyncio.create_task()` for background workers | `main.py:293,341` |
| No TaskGroup in existing code | Grep confirmed 0 matches in `.venv/Lib/site-packages/` |
| No TaskGroup in Hermes upstream | Grep confirmed 0 matches |
| `run_agent.py` has no web server | `run_agent.py` — pure AIAgent class |
| Hermes gateway uses aiohttp | `gateway/platforms/api_server.py:49` |
| M15 absorbs `src/core/main.py` | `plan:930` |
| M3 uses TaskGroup for consciousness | `plan:413` |
| M3 + M15 both modify `run_agent.py` | `plan:321` |
| Forbidden patterns for M15 | `plan:957` |
| Python 3.12+ target | `src/core/__pycache__/*.cpython-312.pyc`, `*.cpython-314.pyc` |

---

## 10. Verdict

**PASS** — The existing `src/core/main.py` provides a complete, battle-tested FastAPI server with lifespan, health endpoints, Prometheus metrics, rate limiting, and HMAC auth. All components are portable. The M3/M15 collision is structurally safe (sequential wave execution, append-only changes to `run_agent.py`). The TaskGroup rewrite of the lifespan is the primary engineering effort but is well-defined. The `guinevere/` namespace directory does not yet exist (no files found), so all M15 files are MODIFY-CREATE. Forbidden patterns (HARD STOP, consent, safe_mode) are cleanly identifiable and removable from the ported code.

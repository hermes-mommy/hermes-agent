# R15 -- Production Pass (Domain 15): Circuit Breakers, Tailscale, PG+Redis, Auto-Recovery, Prometheus Metrics

> **Generated**: 2026-06-29
> **Purpose**: Design specification for M17 Production Pass -- the final integration wave (W17) of P24 v3.0
> **Method**: Direct file analysis via grep/read of all source files cited below; no speculative claims
> **Scope**: 6 circuit breakers, Tailscale-first VPS (local-only per D2), PostgreSQL+Redis, auto-recovery, Prometheus metrics

---

## Table of Contents

1. [Source Code Inventory -- Files to PORT/REWRITE](#1-source-code-inventory)
2. [Design: M17 guinevere/production/circuit_breakers.py](#2-design-m17-circuit-breakers)
3. [Tailscale-First VPS Hardening (Local-Only per D2)](#3-tailscale-first-vps)
4. [Prometheus Metrics Registration](#4-prometheus-metrics)
5. [Auto-Recovery Design](#5-auto-recovery)
6. [PostgreSQL + Redis Integration](#6-postgresql-redis-integration)
7. [Disposition for P24](#7-disposition-for-p24)
8. [Risks](#8-risks)
9. [Verdict](#9-verdict)

---

## 1. Source Code Inventory

### 1.1 Existing Circuit Breaker Implementations

**File 1: `src/loops/circuit_breaker.py`** (489 lines)

Three-layer safety system already production-proven:

| Component | Lines | Description |
|-----------|-------|-------------|
| `CircuitState` enum | 37-43 | `CLOSED`, `OPEN`, `HALF_OPEN` -- exact 3-state machine needed |
| `DependencyCircuitBreaker` | 83-207 | Per-dependency async breaker with `fail_max`, `reset_timeout_s`, `asyncio.Lock` |
| `StuckDetector` | 218-360 | SHA-256 fingerprint hard-loop detection + velocity-based soft-stall detection |
| `SafetyGate` | 368-490 | 3-layer orchestrator: HARD STOP + circuit breaker + stuck detector |
| `CircuitBreakerOpenError` | 209-210 | Exception for open circuits |
| `StuckReport` | 50-60 | Frozen dataclass for stuck detection results |
| `GateDecision` | 69-76 | Frozen dataclass for gate decisions |

Key patterns to PORT:
- `CircuitState` enum at line 37: `CLOSED = "closed"`, `OPEN = "open"`, `HALF_OPEN = "half_open"`
- State machine transitions at lines 96-103 (CLOSED->OPEN on `fail_max`, OPEN->HALF_OPEN on `reset_timeout_s`, HALF_OPEN->CLOSED on success)
- `asyncio.Lock` concurrency control at line 110
- SHA-256 fingerprinting for tool-call dedup at line 248 (`hashlib.sha256(raw.encode()).hexdigest()[:16]`)

**File 2: `src/x_poster/circuit_breaker.py`** (300 lines)

Three-state breaker with PostgreSQL persistence:

| Component | Lines | Description |
|-----------|-------|-------------|
| `CircuitState` enum | 27-31 | Identical 3-state enum |
| `CircuitBreaker` class | 34-299 | DB-persisted breaker with `allow_request()`, `record_success()`, `record_failure()` |
| `_persist_state()` | 245-299 | UPSERT to `p13_circuit_breaker` table |

Key patterns to PORT:
- PostgreSQL persistence pattern at lines 245-299 (UPSERT with `ON CONFLICT`)
- `allow_request()` method at lines 111-146 with HALF_OPEN call counting
- `datetime.now(timezone.utc)` timestamps throughout (not `time.monotonic()`)

### 1.2 Existing Budget and Resource Infrastructure

**File 3: `src/loops/budget.py`** (323 lines)

- `IterationBudget` class at line 86: thread-safe turn/token/cost limiting
- `BudgetExhaustedError` at line 39: structured error with `resource`, `used`, `limit` fields
- Parent-child budget propagation at lines 219-232: subagent debits propagate to parent
- Default parent cost cap: `$5.00` (line 31) -- matches B1 default threshold

**File 4: `src/loops/concurrency.py`** (528 lines)

- `ConcurrencyLimiter` at line 58: `asyncio.Semaphore`-based parallel loop control
- `TokenBucket` at line 181: Redis-backed or in-memory rate limiter with Lua atomic decrement
- `ResourceGate` at line 381: orchestrates concurrency + token bucket + hourly cost cap
- Default max parallel loops: 3 (line 52) -- B6 needs separate global semaphore at 10

**File 5: `src/loops/recovery.py`** (318 lines)

- `RecoveryManager` at line 91: checkpoint-based restart recovery
- `Checkpoint` dataclass at line 38: loop_id, phase, task_hash, completed_at, artifact_summary, metadata
- Phase status tracking: `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `SKIPPED` (line 20)

### 1.3 Prometheus Metrics Patterns

**File 6: `src/x_poster/metrics.py`** (165 lines)

- Uses `prometheus_client` library: `Counter`, `Gauge`, `Histogram`, `start_http_server`
- Circuit breaker state Gauge at line 62: `x_poster_circuit_breaker_state` (0=closed, 1=open, 2=half_open)
- Helper function `set_circuit_breaker_state(state_value: int)` at line 136
- Metrics server at line 162: `start_http_server(port=port, addr=host)` on 127.0.0.1

**File 7: `src/loops/metrics.py`** (64 lines)

- `LOOP_EVENTS_TOTAL` Counter with `event_type` and `project_id` labels
- `LOOP_PHASE_DURATION_SECONDS` Histogram with phase label
- Observer helpers: `observe_loop_event()`, `observe_loop_cycle()`, `observe_phase_duration()`

### 1.4 Sub-Agent Management

**File 8: `src/loops/sub_agent.py`** (129 lines)

- `SubAgentSpawner` at line 20: spawns and tracks sub-agents ("Pasukan Mommy")
- No concurrency limit enforcement -- just records
- B6 (Sub-Agent Explosion) needs to wrap this with a global `asyncio.Semaphore(10)`

### 1.5 Safety Integration

**File 9: `src/loops/safety_integration.py`** (496 lines)

- `LoopSafetyGate` at line 55: bridges HardStopHandler with Redis pub/sub
- HMAC-SHA256 signed broadcasts at lines 356-376
- SHA-256-chained audit trail at lines 283-318

---

## 2. Design: M17 guinevere/production/circuit_breakers.py

### 2.1 Module Structure

```
guinevere/production/
    __init__.py
    circuit_breakers.py     # 6 breakers + composite set + metrics
    tailscale_setup.sh      # Tailscale-first VPS hardening (local-only stub per D2)
    auto_recovery.py        # systemd service + restart-on-crash
    metrics.py              # Prometheus metrics registration for M17
```

### 2.2 BreakerState Enum

PORT directly from `src/loops/circuit_breaker.py:37-43` with ZERO changes:

```python
class BreakerState(str, Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Tripped -- calls blocked
    HALF_OPEN = "half_open"  # Testing recovery
```

Source: `src/loops/circuit_breaker.py:37-43` (identical `CircuitState` enum)

### 2.3 Base Class: AsyncCircuitBreaker

PORT the state machine from `src/loops/circuit_breaker.py:83-207` (`DependencyCircuitBreaker`), extend with abstract `check()` method per infrastructure-patterns-research.md section 3.2.

Key design decisions:
- Use `asyncio.Lock` for concurrency (proven at `src/loops/circuit_breaker.py:110`)
- Use `time.monotonic()` for elapsed-time checks (consistent with existing code at line 199)
- State transitions logged via `structlog` (consistent with `src/loops/circuit_breaker.py:111`)
- Abstract `check(context: dict) -> bool` method for per-breaker logic
- `force_open()` and `force_close()` for testing (per D3 mock-only LLM)

### 2.4 B1: Cost Explosion Breaker

**Failure Mode**: Unbounded token spend per session
**Threshold**: $5.00/session (configurable, matching `src/loops/budget.py:31` default)

Design:
- PORT cost tracking logic from `src/loops/budget.py:149-247` (`consume_turn()`)
- PORT cost calculation from `src/loops/cost.py:79-81` (`record_loop_cost()`)
- State: CLOSED while `total_cost < max_cost_usd`; OPEN when exceeded
- HALF_OPEN after `reset_timeout` (default 1 hour) allows one probe call
- Soft limit at 80% emits warning via structlog (non-blocking)
- Prometheus: `guinevere_m17_cost_breaker_state` Gauge, `guinevere_m17_cost_usd_total` Gauge

All 3 states required (hard rejection):
- CLOSED: normal operation, cost < threshold
- OPEN: cost >= threshold, all calls blocked, `CircuitBreakerOpenError("cost_explosion", "...")`
- HALF_OPEN: after 1hr timeout, one probe call allowed; success -> CLOSED, failure -> OPEN

### 2.5 B2: Infinite Loop Breaker

**Failure Mode**: Identical tool calls repeated with no progress
**Threshold**: 3 consecutive identical SHA-256 fingerprints

Design:
- PORT SHA-256 fingerprinting from `src/loops/circuit_breaker.py:245-249` (`StuckDetector.record_tool_call()`)
- PORT consecutive-count logic from `src/loops/circuit_breaker.py:273-288` (hard-loop check)
- `hashlib.sha256(f"{tool_name}:{args}".encode()).hexdigest()[:16]` -- exact formula from line 248
- Sliding window of last 10 fingerprints
- State: CLOSED while no repeated fingerprint >= threshold; OPEN when detected
- HALF_OPEN after `reset_timeout` (default 60s) allows one test call

All 3 states required (hard rejection):
- CLOSED: tool calls unique or below threshold
- OPEN: 3+ consecutive identical fingerprints, all tool calls blocked
- HALF_OPEN: after timeout, one test call allowed

### 2.6 B3: Hallucination Spiral Breaker

**Failure Mode**: Agent invents false memories not grounded in actual data
**Threshold**: 5% memory grounding ratio over sliding window of 20 turns

Design:
- New logic -- no direct PORT source (hallucination detection is novel)
- `check(context)` receives `claims: list[str]` and `recalled_memories: list[dict]`
- Computes grounding ratio: count(claims with memory overlap) / total_claims
- Keyword overlap as initial implementation: `claim_words & memory_words >= max(2, 10% of claim_words)`
- Sliding window of 20 turn ratios; average must stay >= 5%
- When avg drops below threshold -> OPEN
- Future upgrade path: replace keyword overlap with embedding cosine similarity (pgvector)
- Prometheus: `guinevere_m17_grounding_ratio` Gauge

All 3 states required:
- CLOSED: grounding ratio >= 5% average over window
- OPEN: ratio < 5%, all LLM calls blocked
- HALF_OPEN: after timeout (default 300s), probe with memory-heavy prompt

### 2.7 B4: Emotional Fixation Breaker

**Failure Mode**: Agent stuck in single emotional state across many turns
**Threshold**: 10 consecutive turns with same dominant emotion

Design:
- New logic -- no direct PORT source
- `check(context)` receives `detected_emotion: str` and `emotion_intensity: float`
- Tracks `_emotion_history: list[tuple[str, float]]` per turn
- Applies exponential decay: each prior turn's intensity *= `decay_rate` (0.9)
- Counts consecutive turns with same dominant emotion
- At 10 consecutive -> OPEN
- Prometheus: `guinevere_m17_emotion_consecutive` Gauge, `guinevere_m17_emotion_diversity` Gauge

All 3 states required:
- CLOSED: emotional diversity above threshold
- OPEN: 10+ consecutive same emotion, cognition paused
- HALF_OPEN: after timeout (default 120s), one turn allowed; emotion must differ

### 2.8 B5: Dream Flooding Breaker

**Failure Mode**: Excessive internal processing (dreaming/consolidation) consuming resources
**Threshold**: 5 dreams/hour (per operator decision in task)

Design:
- New logic with sliding window timestamp approach
- `_dream_timestamps: deque[float]` using `time.monotonic()`
- On each dream request: prune timestamps older than 3600s, count remaining
- At count >= 5 -> OPEN
- `deque` for O(1) append/prune
- Prometheus: `guinevere_m17_dreams_this_hour` Gauge

All 3 states required:
- CLOSED: dreams this hour < 5
- OPEN: dreams this hour >= 5, all dream/consolidation blocked
- HALF_OPEN: after timeout (default 1800s = 30min), one dream allowed

### 2.9 B6: Sub-Agent Explosion Breaker

**Failure Mode**: Unbounded sub-agent spawning overwhelming system
**Threshold**: Global semaphore at 10 concurrent sub-agents

Design:
- PORT semaphore pattern from `src/loops/concurrency.py:58-178` (`ConcurrencyLimiter`)
- New global `asyncio.Semaphore(10)` -- separate from the per-loop `ConcurrencyLimiter(max_parallel_loops=3)`
- Context manager: `async with breaker.acquire(agent_id): yield`
- Tracks `_active: set[str]` of agent IDs and `_total_spawned: int`
- `_max_total_per_session: int = 50` (hard cap on total spawned per session)
- Prometheus: `guinevere_m17_subagents_active` Gauge, `guinevere_m17_subagents_total` Counter

All 3 states required:
- CLOSED: active < 10 AND total_spawned < 50
- OPEN: active >= 10 OR total_spawned >= 50, all spawning blocked
- HALF_OPEN: after timeout (default 60s), one spawn slot released

### 2.10 Composite Set: P24CircuitBreakerSet

Groups all 6 breakers with convenience methods:

```python
class P24CircuitBreakerSet:
    def __init__(self, config: CircuitBreakerConfig): ...
    async def pre_llm_call(self, context: dict) -> None: ...    # B1 + B2
    async def post_turn(self, context: dict) -> None: ...       # B3 + B4
    async def pre_dream(self, context: dict) -> None: ...       # B5
    async def pre_spawn(self, agent_id: str) -> AsyncContextManager: ...  # B6
    async def health_check(self) -> dict[str, Any]: ...         # All breaker states
```

Source reference: infrastructure-patterns-research.md section 3.9 (lines 1089-1140)

### 2.11 Hard Rejection Criteria

All 6 breakers MUST implement the full CLOSED->OPEN->HALF_OPEN state machine. A breaker that lacks any of the 3 states is a HARD REJECTION for this domain.

Evidence requirement: each breaker must have a test that exercises all 3 state transitions:
1. Start in CLOSED
2. Trigger condition -> transitions to OPEN (verifies call is blocked with `CircuitBreakerOpenError`)
3. Wait for `reset_timeout` -> transitions to HALF_OPEN (verifies one probe allowed)
4. Probe succeeds -> transitions to CLOSED (or probe fails -> back to OPEN)

---

## 3. Tailscale-First VPS Hardening (Local-Only per D2)

### 3.1 D2 Compliance

Per operator decision D2 (local-runtime-only): NO VPS deploy, NO Discord live, NO real LLM. Therefore:

- The Tailscale setup script is written as a **documented stub** for future VPS deployment
- All infrastructure checks are local-only: `127.0.0.1` binding
- UFW rules target `tailscale0` interface only (as specified)
- PostgreSQL and Redis bind to `localhost` only

### 3.2 Script Design

File: `guinevere/production/tailscale_setup.sh`

PORT the 7-phase pattern from infrastructure-patterns-research.md section 4.1 (lines 1157-1269):

| Phase | Action | Local-Only Behavior |
|-------|--------|---------------------|
| 1. Install | `curl -fsSL https://tailscale.com/install.sh \| sh` | Script documents but skips if no auth key |
| 2. Authenticate | `tailscale up --authkey --hostname` | Requires `TAILSCALE_AUTH_KEY` env var |
| 3. Verify | Get `tailscale ip -4`, test SSH | `echo "Verify from local: ssh admin@$TS_IP"` |
| 4. Harden SSH | `ListenAddress $TS_IP`, `PermitRootLogin no` | Documented for VPS only |
| 5. UFW | `ufw allow in on tailscale0`, `ufw default deny incoming` | Documented for VPS only |
| 6. Kernel | sysctl hardening (IP forwarding, ICMP redirects, SYN cookies) | Documented for VPS only |
| 7. Auto-updates | `unattended-upgrades` | Documented for VPS only |

Local-only adaptation: the script is executable but exits early with a message when `P24_ENVIRONMENT != production`. When environment IS production, it requires explicit confirmation before hardening.

### 3.3 PostgreSQL + Redis Security

From infrastructure-patterns-research.md section 4.2 (lines 1272-1301):

- PostgreSQL: `listen_addresses = 'localhost'` (NEVER `0.0.0.0`)
- pg_hba.conf: `host all all 127.0.0.1/32 scram-sha-256` only
- Redis: `bind 127.0.0.1`, `protected-mode yes`, `requirepass`
- Remote access via SSH tunnel over Tailscale: `ssh -L 5432:localhost:5432 admin@<tailscale-ip>`

---

## 4. Prometheus Metrics Registration

### 4.1 Design

File: `guinevere/production/metrics.py`

PORT the pattern from `src/x_poster/metrics.py` (lines 1-165) and `src/loops/metrics.py` (lines 1-64).

Metric families to register:

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `guinevere_m17_breaker_state` | Gauge | `breaker_name` | 0=closed, 1=open, 2=half_open |
| `guinevere_m17_breaker_trips_total` | Counter | `breaker_name` | Total breaker trips |
| `guinevere_m17_cost_usd_total` | Gauge | -- | Cumulative cost this session |
| `guinevere_m17_tool_fingerprints_total` | Counter | -- | Total tool call fingerprints tracked |
| `guinevere_m17_grounding_ratio` | Gauge | -- | Current memory grounding ratio |
| `guinevere_m17_emotion_consecutive` | Gauge | -- | Consecutive turns with same emotion |
| `guinevere_m17_dreams_this_hour` | Gauge | -- | Dreams in current hour window |
| `guinevere_m17_subagents_active` | Gauge | -- | Currently active sub-agents |
| `guinevere_m17_subagents_total` | Counter | -- | Total sub-agents spawned this session |
| `guinevere_m17_recovery_restarts_total` | Counter | -- | Auto-recovery restarts |

### 4.2 Helper Functions

```python
def set_breaker_state(breaker_name: str, state: BreakerState) -> None: ...
def record_breaker_trip(breaker_name: str) -> None: ...
def set_cost_total(usd: float) -> None: ...
def set_grounding_ratio(ratio: float) -> None: ...
def set_emotion_consecutive(count: int) -> None: ...
def set_dreams_this_hour(count: int) -> None: ...
def set_subagents_active(count: int) -> None: ...
def record_subagent_spawned() -> None: ...
def record_recovery_restart() -> None: ...
def start_metrics_server(host: str = "127.0.0.1", port: int = 9103) -> None: ...
```

Note: port 9103 (not 9102, which is used by x_poster at `src/x_poster/metrics.py:162`).

---

## 5. Auto-Recovery Design

### 5.1 Pattern

File: `guinevere/production/auto_recovery.py`

Based on:
- `src/loops/recovery.py` (318 lines): checkpoint-based restart recovery
- infrastructure-patterns-research.md section 4.3 (lines 1303-1349): systemd service with `Restart=always`, `RestartSec=10`

### 5.2 Systemd Service Unit

```ini
[Unit]
Description=Guinevere P24 v3.0 Autonomous Agent
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/opt/guinevere
ExecStart=/opt/guinevere/.venv/bin/python -m guinevere.main
Restart=always
RestartSec=10
Environment=P24_ENVIRONMENT=production
EnvironmentFile=/opt/guinevere/.env

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/guinevere/data
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
```

### 5.3 Application-Level Recovery

PORT the `RecoveryManager` pattern from `src/loops/recovery.py:91-318`:

1. On startup, `RecoveryManager.get_recovery_plan(loop_id)` checks for prior checkpoint
2. If checkpoint exists and task_hash matches -> resume from last completed phase
3. If task_hash mismatch -> start fresh
4. Circuit breaker states should be persisted (like `src/x_poster/circuit_breaker.py:245-299`) so breakers survive restart

For local-only (D2): the systemd service is documented but not installed. The Python auto-recovery wrapper (`auto_recovery.py`) implements a process-level watchdog that catches `BaseException`, logs, and re-initializes.

---

## 6. PostgreSQL + Redis Integration

### 6.1 PostgreSQL Schema for Circuit Breaker State Persistence

PORT the UPSERT pattern from `src/x_poster/circuit_breaker.py:245-299`:

```sql
CREATE TABLE m17_circuit_breaker_state (
    breaker_name        TEXT PRIMARY KEY,
    state               TEXT NOT NULL DEFAULT 'closed',
    failure_count       INTEGER NOT NULL DEFAULT 0,
    last_failure_at     TIMESTAMPTZ,
    last_success_at     TIMESTAMPTZ,
    opened_at           TIMESTAMPTZ,
    reset_timeout_seconds INTEGER NOT NULL DEFAULT 60,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.2 Redis for Rate Limiting and Token Buckets

PORT the Lua atomic decrement from `src/loops/concurrency.py:253-283`:
- Key pattern: `guinevere:m17:breaker:{breaker_name}`
- Used by B5 (Dream Flooding) for per-hour counting across restarts
- Used by B6 (Sub-Agent Explosion) for global semaphore state

---

## 7. Disposition for P24

| Component | Disposition | Rationale |
|-----------|-------------|-----------|
| `CircuitState` enum | **PORT** (line-for-line) | Identical in `src/loops/circuit_breaker.py:37-43` and `src/x_poster/circuit_breaker.py:27-31` |
| `DependencyCircuitBreaker` base | **PORT** with extension | Add abstract `check()` method; keep state machine, lock, logging |
| `StuckDetector` SHA-256 fingerprinting | **PORT** for B2 | Exact logic at `src/loops/circuit_breaker.py:245-249, 273-288` |
| `IterationBudget` cost tracking | **PORT** partial for B1 | `consume_turn()` cost validation at `src/loops/budget.py:149-247` |
| `ConcurrencyLimiter` semaphore | **PORT** pattern for B6 | New global semaphore at 10, separate from existing max_parallel_loops=3 |
| `RecoveryManager` checkpoints | **PORT** for auto-recovery | Full module at `src/loops/recovery.py:91-318` |
| Prometheus metrics pattern | **PORT** from x_poster | Pattern at `src/x_poster/metrics.py:1-165`; new metric names |
| B3 Hallucination Spiral | **MODIFY-CREATE** | Novel logic; no existing source |
| B4 Emotional Fixation | **MODIFY-CREATE** | Novel logic; no existing source |
| B5 Dream Flooding | **MODIFY-CREATE** | Novel logic; deque + timestamp approach |
| Tailscale setup script | **MODIFY-CREATE** | From research doc; local-only stub per D2 |
| PostgreSQL UPSERT pattern | **PORT** from x_poster | Pattern at `src/x_poster/circuit_breaker.py:245-299` |

---

## 8. Risks

### 8.1 Design Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| B3 grounding ratio false positives | Legitimate novel content blocked by breaker | Start with 5% threshold; configurable per agent via Pydantic config |
| B4 emotion classification dependency | Breaker useless without reliable emotion detection | Use existing emotion module output; default to "neutral" if unavailable |
| B5 dream cap too low (5/hr) | Agent cognitive consolidation starved | Tunable via config; start conservative, raise in production |
| B6 semaphore deadlock | Sub-agent waiting for slot holds parent lock | Use `asyncio.Semaphore.acquire()` outside instance lock (pattern from `src/loops/concurrency.py:96`) |
| PostgreSQL persistence adds latency | Each breaker state change triggers UPSERT | Batch UPSERTs or use Redis for hot path, PG for cold |

### 8.2 Porting Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| `CircuitState` enum defined in 3 places | Namespace collision during migration | Single canonical enum in `guinevere/production/circuit_breakers.py`; old imports redirect |
| `time.monotonic()` vs `datetime.now(timezone.utc)` | Mixed time sources across breakers | Standardize on `time.monotonic()` for elapsed-time (monotonic, no clock skew); `datetime` for audit logs only |
| Existing `src/loops/concurrency.py` max_parallel_loops=3 vs B6 max=10 | Misconfiguration if same semaphore | B6 uses separate `asyncio.Semaphore(10)` with distinct instance name |

### 8.3 D2/D3 Compliance Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tailscale script modifies system state | Violates D2 local-only | Script exits early unless `P24_ENVIRONMENT=production` AND explicit confirmation |
| Prometheus `start_http_server` opens port | Acceptable for local monitoring | Bind to 127.0.0.1 only (pattern from `src/x_poster/metrics.py:162`) |

---

## 9. Verdict

### PASS

All 6 source files required for PORT are present and verified:
- `src/loops/circuit_breaker.py` (489 lines) -- state machine, fingerprinting, gate
- `src/x_poster/circuit_breaker.py` (300 lines) -- PostgreSQL persistence, 3-state machine
- `src/loops/budget.py` (323 lines) -- cost tracking
- `src/loops/concurrency.py` (528 lines) -- semaphore, token bucket, resource gate
- `src/loops/recovery.py` (318 lines) -- checkpoint-based restart recovery
- `src/x_poster/metrics.py` (165 lines) + `src/loops/metrics.py` (64 lines) -- Prometheus patterns

The 3 novel breakers (B3 Hallucination Spiral, B4 Emotional Fixation, B5 Dream Flooding) are well-specified in infrastructure-patterns-research.md sections 3.5-3.7 with complete Python implementations. The local-only Tailscale adaptation per D2 is straightforward: script documents VPS hardening but exits early in non-production environments. All 6 breakers have hard-rejected design for completeness of the CLOSED->OPEN->HALF_OPEN state machine.

**No blockers found. Domain 15 is ready for implementation in W17.**

---

## Source Index

| # | File | Path | Lines | Role |
|---|------|------|-------|------|
| 1 | Infrastructure Patterns Research | `docs/setup-evidence/P24/research/research-wave-2/infrastructure-patterns-research.md` | 1731 | Reference spec for all 6 breakers, Tailscale, FastAPI, PG RLS |
| 2 | Loops Circuit Breaker | `src/loops/circuit_breaker.py` | 489 | PORT: CircuitState, DependencyCircuitBreaker, StuckDetector, SafetyGate |
| 3 | X Poster Circuit Breaker | `src/x_poster/circuit_breaker.py` | 300 | PORT: PostgreSQL persistence pattern |
| 4 | Iteration Budget | `src/loops/budget.py` | 323 | PORT: Cost tracking for B1 |
| 5 | Concurrency Limiter | `src/loops/concurrency.py` | 528 | PORT: Semaphore pattern for B6 |
| 6 | Recovery Manager | `src/loops/recovery.py` | 318 | PORT: Checkpoint-based restart recovery |
| 7 | X Poster Metrics | `src/x_poster/metrics.py` | 165 | PORT: Prometheus metrics pattern |
| 8 | Loops Metrics | `src/loops/metrics.py` | 64 | PORT: Prometheus Counter/Histogram pattern |
| 9 | Sub Agent Spawner | `src/loops/sub_agent.py` | 129 | Context: B6 wraps this with semaphore |
| 10 | Safety Integration | `src/loops/safety_integration.py` | 496 | Context: Redis pub/sub safety pattern |
| 11 | Loops Cost Tracker | `src/loops/cost.py` | 236 | Context: Redis DB5 cost tracking |
| 12 | P24 Master Prompt | `docs/setup-evidence/P24/p24-v3-implementation-master-prompt.md` | ~500 | Requirement: W17 spec at lines 337-343, 415-421 |

---

*Research completed 2026-06-29. All file:line citations verified against actual files via grep/read.*

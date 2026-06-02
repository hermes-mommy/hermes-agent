# D12 — Systemd & Operational Readiness Audit

**Auditor:** Independent Ops Auditor (P5 Agent Loop Audit)
**Date:** 2026-06-02
**Scope:** systemd unit files, loop engine startup/shutdown, dependency management, production readiness
**Verdict:** **NEEDS REVIEW** — 7 critical gaps, 6 medium gaps, 3 low gaps documented

---

## Files Audited

| File | Lines | Role |
|---|---|---|
| `systemd/guinevere-loops.service` | 16 | Loop manager systemd unit |
| `systemd/guinevere-scheduler.service` | 16 | Scheduler systemd unit |
| `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` | 32 | Core service reference (VPS-deployed) |
| `src/loops/manager.py` | 272 | Loop orchestrator + main entry |
| `src/loops/scheduler.py` | 175 | Cron scheduler + main entry |
| `src/loops/cost.py` | 194 | Per-loop cost tracking (Redis DB5) |
| `src/loops/guardian.py` | 157 | Loop watchdog monitor |
| `src/loops/state_machine.py` | 226 | 7-phase state machine |
| `CHECKLIST.md` (L1-100) | 100 | Operational requirements |

---

## §1 Systemd Unit Analysis

### 1.1 Dependency Chain: scheduler → loops → core

| Link | After | Requires | Verdict |
|---|---|---|---|
| scheduler → loops | `After=guinevere-loops.service` | `Requires=guinevere-loops.service` | PASS |
| loops → core | `After=guinevere-core.service` | `Requires=guinevere-core.service` | PASS |
| core → infra | `After=docker.service network.target guinevere-9router.service` | `Requires=docker.service guinevere-9router.service` | PASS |

**Chain:** `scheduler → loops → core → docker + 9router`

**Finding [D12-F01 — LOW]:** Neither loops nor scheduler declares `After=network-online.target`. The dependency on network is implicit through `core → docker`, but if core starts before network is fully up, Redis/PostgreSQL Docker containers may not be reachable. Consider adding `After=network-online.target` explicitly.

### 1.2 guinevere-core.service: VPS vs Repo Gap

**Finding [D12-F02 — MEDIUM]:** `guinevere-core.service` exists on the VPS at `/etc/systemd/system/guinevere-core.service` and has a reference copy at `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service`, but is **NOT** present in the canonical `systemd/` directory. The `systemd/` directory contains only:

- `systemd/guinevere-loops.service`
- `systemd/guinevere-scheduler.service`

**Impact:** Repo `systemd/` is not the single source of truth. New developers/agents cannot see the full service topology from `systemd/` alone.

**Recommendation:** Copy `guinevere-core.service` into `systemd/` alongside the other units. Also consider adding `guinevere.slice` if it exists as a file.

### 1.3 Missing Directives Comparison

Comparing `guinevere-loops.service` and `guinevere-scheduler.service` against the production-hardened `guinevere-core.service`:

| Directive | core.service | loops.service | scheduler.service | Severity |
|---|---|---|---|---|
| `EnvironmentFile` | N/A (inline `Environment=`) | **MISSING** | **MISSING** | **CRITICAL** |
| `Environment=PYTHONPATH` | `=/home/guinevere/code/guinevere` | **MISSING** | **MISSING** | MEDIUM |
| `Environment=VIRTUAL_ENV` | `=/home/guinevere/code/guinevere/.venv` | **MISSING** | **MISSING** | LOW |
| `Environment=PYTHONDONTWRITEBYTECODE` | `=1` | **MISSING** | **MISSING** | LOW |
| `MemoryHigh` | `1G` | **MISSING** | **MISSING** | MEDIUM |
| `MemoryMax` | `2G` | **MISSING** | **MISSING** | **CRITICAL** |
| `CPUQuota` | `200%` | **MISSING** | **MISSING** | MEDIUM |
| `StandardOutput` | `journal` | **MISSING** (defaults to journal) | **MISSING** (defaults to journal) | LOW |
| `StandardError` | `journal` | **MISSING** (defaults to journal) | **MISSING** (defaults to journal) | LOW |
| `NoNewPrivileges` | `true` | **MISSING** | **MISSING** | **CRITICAL** |
| `ProtectSystem` | `strict` | **MISSING** | **MISSING** | **CRITICAL** |
| `ProtectHome` | `read-only` | **MISSING** | **MISSING** | **CRITICAL** |
| `ReadWritePaths` | Explicit paths | **MISSING** | **MISSING** | **CRITICAL** |
| `LimitNOFILE` | Not set (any unit) | N/A | N/A | INFO |

**Finding [D12-F03 — CRITICAL]:** Both loop engine units are missing 13 directives that the core service has. This means:
1. **No resource limits** — a runaway loop can consume all system RAM/CPU.
2. **No security hardening** — loops can escalate privileges, write anywhere on filesystem.
3. **No PYTHONPATH** — `python -m src.loops.manager` may fail with `ModuleNotFoundError` in edge cases.
4. **No REDIS_PASSWORD** — cost tracking will authenticate to Redis with empty string.

**Finding [D12-F04 — CRITICAL]:** `REDIS_PASSWORD` environment variable is not injected into either loops or scheduler units. `cost.py` (line 37) uses `os.environ.get("REDIS_PASSWORD", "")` which falls back to empty string, causing `redis.AuthenticationError` against Redis ACL user `guinevere_core`. This is the known issue S-04 from P1 audit, deferred to P5-023.

### 1.4 Restart Policy

| Setting | loops | scheduler | core | Assessment |
|---|---|---|---|---|
| `Restart` | `always` | `always` | `always` | Appropriate |
| `RestartSec` | `10` | `10` | `10` | Appropriate |
| `Type` | `simple` | `simple` | `exec` | See D12-F05 |

**Finding [D12-F05 — MEDIUM]:** Core service uses `Type=exec` while loops and scheduler use `Type=simple`. `Type=exec` is superior because systemd waits until the process is actually exec'd before considering the service started. With `Type=simple`, systemd considers the service started immediately, which can mask early startup failures (e.g., Python import errors).

**Recommendation:** Change `Type=simple` to `Type=exec` for both units.

### 1.5 User and Slice Consistency

| Unit | User | Slice | Verdict |
|---|---|---|---|
| core | `guinevere` | `guinevere.slice` | PASS |
| loops | `guinevere` | `guinevere.slice` | PASS |
| scheduler | `guinevere` | `guinevere.slice` | PASS |

All consistent. PASS.

### 1.6 WorkingDirectory

All three units: `/home/guinevere/code/guinevere` — correct and consistent. PASS.

### 1.7 ExecStart Module Path

| Unit | ExecStart | Module Exists | Verdict |
|---|---|---|---|
| loops | `.venv/bin/python -m src.loops.manager` | `src/loops/manager.py` has `if __name__` block | PASS* |
| scheduler | `.venv/bin/python -m src.loops.scheduler` | `src/loops/scheduler.py` has `if __name__` block | PASS* |
| core | `.venv/bin/uvicorn src.core.main:app` | N/A | PASS |

*Conditional on PYTHONPATH being set. Without explicit `PYTHONPATH`, relies on WorkingDirectory being added to `sys.path[0]` by Python's `-m` flag. This works but is fragile.

### 1.8 PIDFile and Type

`Type=simple` does not require PIDFile. Correct. PASS.

### 1.9 After/Requires Ordering

Dependency chain is correct (see §1.1). However:

**Finding [D12-F06 — MEDIUM]:** No `Wants=redis-guinevere.service` or `Wants=postgresql.service` declared in loops or scheduler. Redis is a Docker container managed by Docker, so this is partially mitigated by core's `Requires=docker.service`. However, Redis container readiness within Docker is not guaranteed by the time loops starts.

---

## §2 Operational Readiness Analysis

### 2.1 Logging (Checkpoint #10)

| Aspect | Status | Detail |
|---|---|---|
| structlog imported | PASS | All 4 Python files use `structlog.get_logger()` |
| Structured events | PASS | Consistent `event_name` pattern (e.g., `loop_manager.initialized`) |
| structlog configuration | **GAP** | No `structlog.configure()` found in loop engine files; depends on global config |
| Output destination | **GAP** | StandardOutput/StandardError not explicitly set; relies on systemd defaults |
| Log file rotation | N/A | journalctl handles rotation; no file-based logs |

**Finding [D12-F07 — MEDIUM]:** structlog configuration (processors, renderers, log level) is not present in any loop engine file. If the global structlog config is not initialized before `src.loops.manager` imports, all log output will use structlog defaults (which may be unstructured `print` to stderr). The core service likely configures structlog globally, but when loops/scheduler are separate processes, they need their own structlog initialization.

### 2.2 Health Check (Checkpoint #11)

| Aspect | Status | Detail |
|---|---|---|
| HTTP health endpoint | **MISSING** | No HTTP server in manager.py or scheduler.py |
| Internal watchdog | PASS | `LoopGuardian` monitors heartbeat + progress |
| External probe | **MISSING** | No way for Prometheus/systemd to probe loop health |

**Finding [D12-F08 — CRITICAL]:** Neither manager.py nor scheduler.py exposes any health check mechanism. The core service has `/health` via FastAPI, but the loop engine processes are opaque to external monitoring. If the loop manager hangs (deadlock, stuck asyncio task), systemd will not know because `Type=simple` only tracks the main process, not internal health.

**Recommendation:** Add a minimal HTTP health endpoint or a Unix socket health probe to both services.

### 2.3 Graceful Shutdown (Checkpoint #12)

| Aspect | manager.py | scheduler.py |
|---|---|---|
| Main blocking mechanism | `await asyncio.Event().wait()` | `await asyncio.Event().wait()` |
| KeyboardInterrupt catch | YES (line 252) | YES (line 167) |
| CancelledError catch | YES (line 252) | YES (line 167) |
| Finally block cleanup | YES — stops guardian, cancels all tasks | YES — calls scheduler.stop() |
| Explicit signal handler | **MISSING** | **MISSING** |

**Finding [D12-F09 — MEDIUM]:** SIGTERM handling relies on Python 3.9+ `asyncio.run()` behavior, which converts SIGTERM to CancelledError. This works but is implicit rather than explicit. No `signal.signal(signal.SIGTERM, ...)` handler is registered. If the Python version or asyncio behavior changes, graceful shutdown may break.

**Verdict:** Acceptable for current Python version, but fragile. Should add explicit SIGTERM handler.

### 2.4 Startup Dependencies (Checkpoint #13)

| Dependency | manager.py check | scheduler.py check | Available at startup? |
|---|---|---|---|
| Redis (cost tracking) | **NO check** | **NO check** | Not guaranteed |
| PostgreSQL (evidence) | **NO check** | **NO check** | Not guaranteed |
| 9Router (LLM calls) | **NO check** | **NO check** | Not guaranteed |
| Docker | N/A (systemd dep) | N/A (systemd dep) | Via core dependency |

**Finding [D12-F10 — CRITICAL]:** Neither service performs any startup dependency validation. If Redis is unreachable when cost.py first attempts a Redis command, the loop phase will fail with an unhandled `redis.ConnectionError`. No retry logic, no circuit breaker, no startup health gate.

### 2.5 Redis Failure Impact (Checkpoints #14, #15)

#### manager.py + cost.py:

- `LoopCostTracker.__init__()` creates `redis.Redis()` connection — **lazy**, does not connect until first command.
- First `record_loop_cost()` call triggers actual TCP connection.
- If Redis is down: `redis.ConnectionError` propagates to phase handler → unhandled exception → `state.fail(reason)` in `_run_loop()`.
- The loop FAILS rather than gracefully degrading. Cost tracking failure kills the entire loop.
- No retry, no exponential backoff, no circuit breaker.

#### scheduler.py:

- Creates its own `LoopManager()` instance (line 25).
- LoopManager itself doesn't use Redis in `__init__`.
- BUT: Triggered loops go through phase handlers which may use cost tracking.
- scheduler.py itself won't crash at startup from Redis being down.
- Triggered loops will fail during execution if Redis is unavailable.

**Finding [D12-F11 — CRITICAL]:** cost.py Redis operations have zero fault tolerance. A transient Redis blip during cost recording will fail the entire loop. Cost tracking is an auxiliary concern — its failure should not abort the primary SDLC loop.

### 2.6 Monitoring (Checkpoint #16)

| Aspect | Status |
|---|---|
| Prometheus metrics endpoint | **MISSING** |
| HTTP health endpoint | **MISSING** |
| Structured logging to journal | PASS (via structlog → stdout → journal) |
| Guardian internal monitoring | PASS (heartbeat + progress timeout) |
| External visibility | **NONE** |

**Finding [D12-F12 — MEDIUM]:** The loop engine is invisible to the Prometheus + Grafana monitoring stack referenced in the project architecture. No `/metrics` endpoint, no counters, no gauges. The only observability is through `journalctl -u guinevere-loops` log inspection.

### 2.7 Alerting (Checkpoint #17)

| Aspect | Status |
|---|---|
| Gotify integration | **MISSING** |
| Discord alert on failure | **MISSING** |
| PagerDuty/OpsGenie | N/A |
| systemd `OnFailure=` | **MISSING** |

**Finding [D12-F13 — MEDIUM]:** No alerting integration exists. If the loop manager crashes, systemd restarts it silently. No notification is sent to the operator. CHECKLIST.md (line 81) specifies "Emergency contact method confirmed (Discord DM + Gotify fallback)" but no code implements this.

**Recommendation:** Add `OnFailure=guinevere-alert@%n.service` or integrate Gotify push notification in the guardian's `kill_loop()` method.

### 2.8 PID/Lock File — Duplicate Prevention (Checkpoint #18)

| Mechanism | Status |
|---|---|
| PID file | Not used (correct for Type=simple) |
| Lock file | **MISSING** |
| systemd single-instance | PASS (systemd prevents duplicate unit starts) |
| Manual execution guard | **MISSING** |

**Verdict:** systemd itself prevents duplicate service instances. Low risk in production. If someone manually runs `python -m src.loops.manager`, no lock file prevents a duplicate. Acceptable for systemd-managed deployment.

### 2.9 State Recovery After Restart (Checkpoint #19)

| Aspect | Status |
|---|---|
| State persistence | **NONE** — all in-memory Python dicts |
| Checkpoint to disk/DB | **MISSING** |
| State recovery on restart | **IMPOSSIBLE** |
| `to_dict()` serialization | Exists but never persisted |

**Finding [D12-F14 — CRITICAL]:** All loop state (`active_loops`, `evidence_pipelines`, `_tasks`, `LoopStateMachine` fields) is held in Python dicts with zero persistence. On process restart:

1. All running loops are **permanently lost**.
2. No record of which loops were in progress.
3. No way to resume from the last completed phase.
4. `LoopStateMachine.to_dict()` exists (line 211) but nothing writes it anywhere.

**Impact:** A crash during a multi-hour loop loses all progress. The operator must manually re-trigger the loop.

**Recommendation:** Persist `LoopStateMachine.to_dict()` to Redis or PostgreSQL on each phase advance. On startup, scan for incomplete loops and optionally resume.

---

## §3 Architectural Concern — Scheduler Creates Separate LoopManager

**Finding [D12-F15 — MEDIUM]:** `scheduler.py` line 25 creates `self.manager = LoopManager()`, which is a **separate, independent** LoopManager instance from the one running in `guinevere-loops.service`. This means:

1. Loops triggered by the scheduler are invisible to the standalone loops service.
2. Two separate guardian monitors run independently.
3. No shared state between the two processes.
4. Cost tracking goes to the same Redis DB5, but loop registry is split.

**Impact:** If an operator queries loop status via the loops service, scheduler-triggered loops won't appear.

**Recommendation:** The scheduler should communicate with the loops service via an IPC mechanism (Unix socket, Redis pub/sub, shared DB table) rather than creating its own LoopManager.

---

## §4 Findings Summary

| ID | Severity | Category | Summary |
|---|---|---|---|
| D12-F01 | LOW | Systemd | No `After=network-online.target` in loops/scheduler |
| D12-F02 | MEDIUM | Repo Gap | `guinevere-core.service` not in `systemd/` directory |
| D12-F03 | CRITICAL | Systemd | 13 hardening/resource directives missing from both units |
| D12-F04 | CRITICAL | Config | `REDIS_PASSWORD` not injected into loops/scheduler env |
| D12-F05 | MEDIUM | Systemd | `Type=simple` instead of `Type=exec` |
| D12-F06 | MEDIUM | Systemd | No explicit Redis/PostgreSQL dependency declared |
| D12-F07 | MEDIUM | Logging | structlog not configured in loop engine files |
| D12-F08 | CRITICAL | Health | No external health check endpoint |
| D12-F09 | MEDIUM | Shutdown | No explicit SIGTERM handler |
| D12-F10 | CRITICAL | Startup | No dependency validation at startup |
| D12-F11 | CRITICAL | Resilience | cost.py has zero Redis fault tolerance |
| D12-F12 | MEDIUM | Monitoring | No Prometheus metrics endpoint |
| D12-F13 | MEDIUM | Alerting | No failure notification integration |
| D12-F14 | CRITICAL | State | All loop state in-memory, no persistence or recovery |
| D12-F15 | MEDIUM | Architecture | Scheduler creates separate LoopManager, split state |

### Severity Breakdown

| Severity | Count |
|---|---|
| CRITICAL | 7 |
| MEDIUM | 6 |
| LOW | 2 (incl. F01 + LimitNOFILE info) |

---

## §5 PASS Items

| Check | Verdict | Evidence |
|---|---|---|
| Dependency chain documented | PASS | scheduler→loops→core in unit files |
| Restart policy appropriate | PASS | `Restart=always`, `RestartSec=10` |
| User/Slice consistency | PASS | All use `guinevere`/`guinevere.slice` |
| WorkingDirectory correct | PASS | `/home/guinevere/code/guinevere` |
| ExecStart module path valid | PASS | `src/loops/manager.py` and `scheduler.py` exist with `__main__` |
| Type=simple correct (no PIDFile) | PASS | Appropriate for asyncio services |
| structlog used throughout | PASS | All files use structured logging |
| Graceful shutdown (basic) | PASS | finally blocks clean up tasks |
| Guardian watchdog | PASS | Heartbeat + progress timeout monitoring |
| systemd prevents duplicates | PASS | Single-instance per unit |

---

## §6 Verdict

### **NEEDS REVIEW**

The loop engine **can start and run** under systemd with the current configuration, but it is **not production-ready** due to:

1. **Security hardening gap** — loops/scheduler units have none of the filesystem/privilege restrictions that core has (D12-F03).
2. **Resource protection gap** — no MemoryMax/CPUQuota means a runaway loop can starve the entire VPS (D12-F03).
3. **State fragility** — all loop state is lost on restart with no recovery path (D12-F14).
4. **Redis dependency fragility** — cost tracking failure kills the entire loop (D12-F11).
5. **Observability gap** — no external health probe, no Prometheus metrics, no alerting (D12-F08, F12, F13).
6. **Config gap** — REDIS_PASSWORD not injected, known since P1 audit (D12-F04).

### Recommended Priority Fixes

| Priority | Finding | Fix |
|---|---|---|
| P0 (blocker) | D12-F03 | Copy all hardening directives from core.service to loops/scheduler |
| P0 (blocker) | D12-F04 | Add `EnvironmentFile` with REDIS_PASSWORD to both units |
| P1 (high) | D12-F14 | Persist loop state to Redis/PostgreSQL on phase advance |
| P1 (high) | D12-F11 | Add try/except + retry to cost.py Redis operations |
| P1 (high) | D12-F08 | Add health HTTP endpoint or Unix socket probe |
| P2 (medium) | D12-F02 | Add core.service to `systemd/` directory |
| P2 (medium) | D12-F07 | Add structlog.configure() in loop engine entry points |
| P2 (medium) | D12-F15 | Redesign scheduler to communicate with loops service via IPC |
| P3 (low) | D12-F05 | Change Type=simple to Type=exec |
| P3 (low) | D12-F09 | Add explicit SIGTERM handler |
| P3 (low) | D12-F13 | Add OnFailure= or Gotify alerting |

---

## §7 Comparison: Core Service vs Loop Engine Units

| Aspect | core.service | loops/scheduler | Gap |
|---|---|---|---|
| Service type | `exec` | `simple` | Minor |
| Resource limits | MemoryMax=2G, CPUQuota=200% | **None** | Critical |
| Security | NoNewPrivileges, ProtectSystem, ProtectHome | **None** | Critical |
| Environment | PYTHONPATH, VIRTUAL_ENV, PYTHONDONTWRITEBYTECODE | **None** | Medium |
| Logging | StandardOutput/Error=journal | Defaults | Low |
| Health check | FastAPI `/health` | **None** | Critical |
| Metrics | Likely via FastAPI middleware | **None** | Medium |
| Alerting | N/A | **None** | Medium |
| State recovery | N/A (stateless API) | **None** | Critical |

The loop engine units are significantly less mature than the core service from an operational standpoint.

---

## Footer

| Field | Value |
|---|---|
| Audit ID | D12-operations |
| Audit Phase | P5 Agent Loop Final Audit |
| Auditor | Independent Ops Auditor |
| Date | 2026-06-02 |
| Files Read | 9 |
| Findings | 15 (7 critical, 6 medium, 2 low) |
| Verdict | NEEDS REVIEW |
| Code Modified | None (read-only audit) |

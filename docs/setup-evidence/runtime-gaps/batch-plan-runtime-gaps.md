# Guinevere — Runtime Gap Closure Batch Plan

> **Generated**: 2026-06-03 | **Session**: Runtime Gap Closure | **Status**: PLANNER OUTPUT
> **Source**: `research-reports/runtime-gap-analysis/master-gap-report.md`
> **Evidence Root**: `docs/setup-evidence/runtime-gaps/`

---

## 1. Executive Summary

This plan addresses **14 implementable runtime gaps** (RG-001 through RG-014) plus **2 deferred architectural scaffolds** (RG-015, RG-016) identified in the Master Gap Report. The work is organized into 5 batches (A–E) with explicit dependency ordering, parallelism decisions, per-step verification scaffolds, collision scan, auditor matrix, and rollback plans.

| Batch | Scope | Steps | Parallelism | Est. Effort |
|---|---|---|---|---|
| A | Service Infrastructure | RG-001, RG-002, RG-003 | **Parallel** | SMALL each |
| B | Wiring Fixes | RG-004, RG-005, RG-006, RG-007 | **Sequenced** (main.py collision) | MEDIUM each |
| C | Security | RG-008, RG-009 | **Sequenced** (main.py collision with B) | MEDIUM each |
| D | Discord Stubs | RG-010 through RG-014 | **Sequential** (all modify bot.py) | LARGE aggregate |
| E | Deferred | RG-015, RG-016 | **Scaffold only** | N/A |

**Total implementable steps**: 14
**Deferred**: 2 (architectural scaffold only)
**Files touched**: ~30 across systemd, src/core, src/discord, src/loops, src/mcp, scripts, monitoring

---

## 2. Master Todo — Atomic Steps

| Step ID | Title | Batch | Depends On | Parallel With | Effort |
|---|---|---|---|---|---|
| RG-001 | Fix service env vars | A | — | RG-002, RG-003 | SMALL |
| RG-002 | Fix monitoring service | A | — | RG-001, RG-003 | SMALL |
| RG-003 | Set embedding API key | A | — | RG-001, RG-002 | SMALL |
| RG-004 | Wire SurveillanceConsumer into main.py | B | RG-001 | RG-006 | MEDIUM |
| RG-005 | Wire RitualScheduler into bot.py | B | RG-001 | RG-006 | MEDIUM |
| RG-006 | Wire LoopCostTracker into loop manager | B | RG-001 | RG-004, RG-005 | MEDIUM |
| RG-007 | Add Prometheus /metrics endpoint | B | RG-004 | — | MEDIUM |
| RG-008 | AUTH_MATRIX runtime enforcement | C | RG-006 | RG-009 | MEDIUM |
| RG-009 | Enhanced health endpoint | C | RG-007 | RG-008 | MEDIUM |
| RG-010 | Memory commands (memory-forget, memory-export) | D | RG-005 | — | MEDIUM |
| RG-011 | Finance command (cost-alert) | D | RG-010 | — | SMALL |
| RG-012 | System commands (approve, deny, approve-all, focus, casual, consent, punishment, reward) | D | RG-011 | — | LARGE |
| RG-013 | Admin commands (restart-service, backup-now, health-check, clear-cache) | D | RG-012 | — | LARGE |
| RG-014 | Loop commands (loop-pause, loop-resume, loops, evidence, loop-priority) | D | RG-013 | — | LARGE |
| RG-015 | Loop LLM integration | E | — | — | DEFERRED |
| RG-016 | MCP tool bridge | E | — | — | DEFERRED |

---

## 3. Dependency Map

```
Batch A (parallel):
  RG-001 | RG-002 | RG-003
       │
       ▼
Batch B (sequenced due to main.py collision):
  RG-004 ──► RG-007
  RG-005 (parallel with RG-004 — different file)
  RG-006 (parallel with RG-004 — different file)
       │
       ▼
Batch C (sequenced due to main.py collision with B):
  RG-008 | RG-009 (RG-009 depends on RG-007 metrics; RG-008 independent)
       │
       ▼
Batch D (sequential — all modify bot.py):
  RG-010 ──► RG-011 ──► RG-012 ──► RG-013 ──► RG-014
       │
       ▼
Batch E: DEFERRED (RG-015, RG-016 — scaffold only)
```

### Critical Path Notes

1. **main.py** is modified by RG-004 (surveillance wiring), RG-007 (Prometheus metrics), and RG-009 (enhanced health). These MUST be sequenced: RG-004 → RG-007 → RG-009.
2. **bot.py** is modified by RG-005 (ritual wiring) and RG-010..RG-014 (command implementations). RG-005 MUST complete before Batch D starts.
3. **systemd/*.service** files are each modified by exactly one step (RG-001), no collision.
4. **monitoring/.env** is created by RG-002 only, no collision.

---

## 4. Collision Scan

| Shared File | Modified By | Collision Type | Mitigation |
|---|---|---|---|
| `src/core/main.py` | RG-004, RG-007, RG-009 | Same source file | Sequence: RG-004 → RG-007 → RG-009 |
| `src/discord/bot.py` | RG-005, RG-010, RG-011, RG-012, RG-013, RG-014 | Same source file | Sequence: RG-005 first, then RG-010→RG-014 |
| `systemd/guinevere-loops.service` | RG-001 | Single owner | No collision |
| `systemd/guinevere-mcp.service` | RG-001 | Single owner | No collision |
| `systemd/guinevere-scheduler.service` | RG-001 | Single owner | No collision |
| `systemd/guinevere-surveillance.service` | RG-001 | Single owner | No collision |
| `systemd/guinevere-monitoring.service` | RG-002 | Single owner | No collision |
| `monitoring/.env` | RG-002 | Single creator | No collision |
| `src/loops/manager.py` | RG-006 | Single owner | No collision |
| `src/mcp/auth.py` | RG-008 | Single owner | No collision |
| `src/mcp/manager.py` | RG-008 | Single owner | No collision |
| `scripts/setup-service-envs.sh` | RG-001 | Single creator | No collision |

### Collision Resolution Rules

1. **No parallel edits** to `main.py` or `bot.py`. Each step must complete, pass diagnostics, and be committed before the next step touching the same file begins.
2. **Shared docs** (evidence indexes, docs/README.md) are parent-only — not delegated to sub-agents.
3. **systemd service files** have no overlap — each file maps to exactly one step.

---

## 5. Batch A — Service Infrastructure (RG-001..RG-003, parallel)

### RG-001: Fix Service Env Vars

**Status**: PENDING
**Depends On**: —
**Parallel With**: RG-002, RG-003
**Estimated Effort**: SMALL
**Gap Reference**: VPS-01

#### Description

All 4 non-core services (loops, mcp, scheduler, surveillance) crash on startup because they reference `%E/REDIS_PASSWORD` — a systemd credential specifier that does not resolve correctly. The fix replaces these inline `Environment=` lines with `EnvironmentFile=` pointing to per-service `.env` files. A setup script decrypts SOPS secrets and generates the `.env` files.

#### Expected Files

| File | Action | Description |
|---|---|---|
| `scripts/setup-service-envs.sh` | CREATE | SOPS-decrypt script generating all per-service .env files |
| `systemd/guinevere-loops.service` | MODIFY | Replace `%E/REDIS_PASSWORD` with `EnvironmentFile=/home/guinevere/code/guinevere/.env.loops` |
| `systemd/guinevere-mcp.service` | MODIFY | Replace `%E/REDIS_PASSWORD` with `EnvironmentFile=/home/guinevere/code/guinevere/.env.mcp` |
| `systemd/guinevere-scheduler.service` | MODIFY | Replace `%E/REDIS_PASSWORD` with `EnvironmentFile=/home/guinevere/code/guinevere/.env.scheduler` |
| `systemd/guinevere-surveillance.service` | MODIFY | Replace `%E/` refs with `EnvironmentFile=/home/guinevere/code/guinevere/.env.surveillance` |

#### Per-Service Env File Contents

**`.env.loops`**, **`.env.mcp`**, **`.env.scheduler`**:
- `REDIS_PASSWORD=<from secrets/redis-password.yaml>`

**`.env.surveillance`**:
- `REDIS_PASSWORD=<from secrets/redis-password.yaml>`
- `GUINEVERE_DB_PASSWORD=<from secrets/db-passwords.yaml>`
- `DATABASE_URL=postgresql+asyncpg://guinevere:<DB_PASSWORD>@localhost:5433/guinevere`
- `SURVEILLANCE_HMAC_KEY=<from secrets/surveillance-hmac-key.yaml or generated>`

#### Forbidden Patterns

- `%E/` — zero matches in any modified .service file
- Hardcoded credential values in .service files — zero matches
- `set -x` in setup script (would leak secrets to journal) — zero matches

#### Required Commands

- `bash -n scripts/setup-service-envs.sh` → exit 0 (syntax check)
- `grep -r '%E/' systemd/` → zero matches (all broken specifiers removed)
- `systemctl daemon-reload` → exit 0 (after deploying modified .service files)
- `systemctl start guinevere-loops.service` → exit 0 (VPS verification)
- `systemctl is-active guinevere-loops.service` → `active`
- `systemctl is-active guinevere-mcp.service` → `active`
- `systemctl is-active guinevere-scheduler.service` → `active`
- `systemctl is-active guinevere-surveillance.service` → `active`

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-001/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-001/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] Any `.service` file still contains `%E/` → FAIL
- [ ] Setup script does not use SOPS for decryption → FAIL
- [ ] Setup script logs decrypted values to stdout/journal → FAIL
- [ ] Any service fails to start after env fix → FAIL
- [ ] `.env` files committed to git → FAIL (must be .gitignored)

---

### RG-002: Fix Monitoring Service

**Status**: PENDING
**Depends On**: —
**Parallel With**: RG-001, RG-003
**Estimated Effort**: SMALL
**Gap Reference**: VPS-02

#### Description

The monitoring stack (Prometheus, Grafana, Loki, Promtail, Alertmanager, node-exporter, postgres-exporter, redis-exporter) is defined in `monitoring/compose.monitoring.yml` but never started because: (1) `monitoring/.env` is missing (required for `GRAFANA_ADMIN_PASSWORD`, `PG_EXPORTER_PASSWORD`, `REDIS_EXPORTER_PASSWORD`), (2) `guinevere-monitoring.service` has wrong `WorkingDirectory` (`/home/guinevere/guinevere` instead of `/home/guinevere/code/guinevere`), and (3) the service is disabled.

#### Expected Files

| File | Action | Description |
|---|---|---|
| `monitoring/.env` | CREATE (on VPS) | Environment values for monitoring containers |
| `systemd/guinevere-monitoring.service` | MODIFY | Fix `WorkingDirectory` to `/home/guinevere/code/guinevere` |
| `monitoring/.env.example` | CREATE (in repo) | Template without real values |

#### monitoring/.env Required Variables

- `GRAFANA_ADMIN_PASSWORD=<from secrets or generated>`
- `GRAFANA_ADMIN_USER=admin`
- `PG_EXPORTER_PASSWORD=<from secrets/db-passwords.yaml>`
- `REDIS_EXPORTER_PASSWORD=<from secrets/redis-password.yaml>`

#### Forbidden Patterns

- Hardcoded passwords in committed files — zero matches
- `WorkingDirectory=/home/guinevere/guinevere` — zero matches (the wrong path)
- Public-facing port bindings (non-127.0.0.1) — zero matches

#### Required Commands

- `grep 'WorkingDirectory' systemd/guinevere-monitoring.service` → contains `/home/guinevere/code/guinevere`
- `docker compose -f monitoring/compose.monitoring.yml config` → exit 0 (validates compose + .env)
- `systemctl daemon-reload` → exit 0
- `systemctl enable --now guinevere-monitoring.service` → exit 0
- `systemctl is-active guinevere-monitoring.service` → `active`
- `curl -s http://127.0.0.1:9090/-/healthy` → `Prometheus Server is Healthy.`
- `curl -s http://127.0.0.1:3000/api/health` → JSON with `"database": "ok"`

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-002/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-002/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] `WorkingDirectory` still points to wrong path → FAIL
- [ ] `monitoring/.env` committed to git → FAIL
- [ ] Any compose container exits immediately after start → FAIL
- [ ] Ports bound to non-localhost → FAIL

---

### RG-003: Set Embedding API Key

**Status**: PENDING
**Depends On**: —
**Parallel With**: RG-001, RG-002
**Estimated Effort**: SMALL
**Gap Reference**: GAP-04

#### Description

The embedding module (`src/memory/embeddings.py`) requires `GUINEVERE_9ROUTER_API_KEY` to call the 9Router API for vector embeddings. This key is the same as `INITIAL_PASSWORD` from `secrets/.env.9router`. It must be added to `.env.discord` (for Discord bot memory recall) and `.env.core` (for core API embedding calls).

#### Expected Files

| File | Action | Description |
|---|---|---|
| `.env.discord` | MODIFY (on VPS) | Add `GUINEVERE_9ROUTER_API_KEY=<from secrets>` |
| `.env.core` | CREATE (on VPS) | New env file with `GUINEVERE_9ROUTER_API_KEY=<from secrets>` |
| `systemd/guinevere-core.service` | MODIFY (on VPS) | Add `EnvironmentFile=/home/guinevere/code/guinevere/.env.core` if not present |

#### Forbidden Patterns

- API key values in repo files — zero matches
- `.env.discord` or `.env.core` committed to git — must be .gitignored

#### Required Commands

- `grep 'GUINEVERE_9ROUTER_API_KEY' /home/guinevere/code/guinevere/.env.discord` → non-empty value present
- `grep 'GUINEVERE_9ROUTER_API_KEY' /home/guinevere/code/guinevere/.env.core` → non-empty value present
- `systemctl restart guinevere-core.service` → exit 0
- `systemctl restart guinevere-discord.service` → exit 0
- `systemctl is-active guinevere-core.service` → `active`
- `systemctl is-active guinevere-discord.service` → `active`

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-003/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-003/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] API key hardcoded in any source file → FAIL
- [ ] `.env.core` not added to `.gitignore` → FAIL
- [ ] Services fail to restart after env change → FAIL

---

## 6. Batch B — Wiring Fixes (RG-004..RG-007)

### Execution Order

Due to `main.py` collision, steps touching it must be sequenced:

1. **RG-004** (main.py: surveillance consumer wiring) — first
2. **RG-005** (bot.py: ritual scheduler wiring) — parallel with RG-004 (different file)
3. **RG-006** (manager.py: cost tracker wiring) — parallel with RG-004 (different file)
4. **RG-007** (main.py: Prometheus /metrics) — after RG-004 completes

### RG-004: Wire SurveillanceConsumer into main.py

**Status**: PENDING
**Depends On**: RG-001
**Parallel With**: RG-005, RG-006
**Estimated Effort**: MEDIUM
**Gap Reference**: GAP-05

#### Description

`SurveillanceConsumer` (defined in `src/surveillance/consumer.py`) is never started by the core application. The consumer's `main()` entry point creates a Redis buffer and DB session factory, but `src/core/main.py` lifespan does not invoke it. The fix starts the consumer as an `asyncio.create_task` in the FastAPI lifespan context manager, with graceful shutdown on `CancelledError`.

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/core/main.py` | MODIFY | Import and start SurveillanceConsumer in lifespan; graceful shutdown |

#### Implementation Notes

- Import `SurveillanceConsumer` and `RedisSurveillanceBuffer` from `src.surveillance`
- Create Redis client for DB2 (surveillance buffer)
- Create async session factory for DB writes (reuse pattern from consumer.py `main()`)
- Start `consumer.run()` as `asyncio.create_task(name="surveillance-consumer")`
- On shutdown: call `consumer.stop()`, cancel task, await with CancelledError catch
- Wrap in try/except to fail-soft if Redis/DB not available (log warning, don't crash core)

#### Forbidden Patterns

- `as any` / `# type: ignore` / `@ts-ignore` — zero matches in new code
- `except Exception: pass` — zero matches (must log at minimum)
- `TODO(` — zero matches in new/modified code
- Hardcoded Redis password or DB credentials — zero matches

#### Required Commands

- `python -m py_compile src/core/main.py` → exit 0
- `lsp_diagnostics filePath=src/core/main.py` → 0 new errors
- `python -m pytest tests/ -k surveillance -v` → exit 0 (existing tests still pass)

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-004/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-004/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] SurveillanceConsumer not started as background task in lifespan → FAIL
- [ ] No graceful shutdown (stop + cancel + await) → FAIL
- [ ] Hard crash if Redis/DB unavailable → FAIL (must be fail-soft)
- [ ] Type suppression in new code → FAIL
- [ ] Existing tests broken → FAIL

---

### RG-005: Wire RitualScheduler into bot.py

**Status**: PENDING
**Depends On**: RG-001
**Parallel With**: RG-004, RG-006
**Estimated Effort**: MEDIUM
**Gap Reference**: GAP-03

#### Description

`RitualScheduler` (defined in `src/persona/ritual_scheduler.py`) fires 5 daily rituals at WIB times, but the callback only logs locally — it never sends messages to Discord. The fix wires the scheduler into `bot.py`'s `setup_hook` with a Discord callback that sends ritual messages to `#guinevere-chat` (channel ID: `1510914600777023659`).

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/discord/bot.py` | MODIFY | Import RitualScheduler, create Discord callback, start in setup_hook, stop in close |

#### Implementation Notes

- Import `RitualScheduler` and `RitualResult` from `src.persona.ritual_scheduler`
- Create async callback `discord_ritual_callback(ritual_name: str) -> RitualResult` that:
  - Gets `#guinevere-chat` channel via `bot.get_channel(1510914600777023659)`
  - Sends the ritual's `default_message` as a channel message
  - Returns `RitualResult` with success/failure
- In `setup_hook`: create `RitualScheduler()`, call `setup(callback=discord_ritual_callback)`, call `await scheduler.start()`
- Store scheduler reference on bot instance for shutdown
- Override or hook `close()` to call `await scheduler.stop()`

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code (existing `type: ignore` on line 32 is pre-existing)
- `except Exception: pass` — zero matches
- `TODO(` — zero matches
- Ritual content violating PersonaSafetyPolicy (Y6 yandere, intimate data) — zero matches

#### Required Commands

- `python -m py_compile src/discord/bot.py` → exit 0
- `lsp_diagnostics filePath=src/discord/bot.py` → 0 new errors
- `python -m pytest tests/ -k ritual -v` → exit 0

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-005/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-005/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] RitualScheduler not started in setup_hook → FAIL
- [ ] No Discord channel callback → FAIL
- [ ] Channel ID incorrect (not `1510914600777023659`) → FAIL
- [ ] Scheduler not stopped on bot close → FAIL
- [ ] Ritual messages contain Y6 or unsafe persona content → FAIL

---

### RG-006: Wire LoopCostTracker into Loop Manager

**Status**: PENDING
**Depends On**: RG-001
**Parallel With**: RG-004, RG-005
**Estimated Effort**: MEDIUM
**Gap Reference**: GAP-06

#### Description

`LoopCostTracker` (defined in `src/loops/cost.py`) provides `record_loop_cost()` for per-loop cost tracking via Redis DB5, but it is never instantiated or called in `LoopManager`. The fix initializes the tracker in `LoopManager.__init__` and calls `record_loop_cost()` at appropriate points in `_run_loop`.

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/loops/manager.py` | MODIFY | Import LoopCostTracker, init in __init__, call in _run_loop |

#### Implementation Notes

- Import `LoopCostTracker` from `src.loops.cost`
- Initialize `self.cost_tracker = LoopCostTracker()` in `__init__` (fail-soft on Redis error)
- In `_run_loop`, after each phase completes: call `self.cost_tracker.record_loop_cost()` if the phase produced LLM token usage data
- Currently phases return template strings (GAP-02), so cost recording will be a no-op scaffold until Batch E — but the wiring must be in place
- Wrap cost recording in try/except to fail-soft (log warning, don't break loop execution)

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code
- `except Exception: pass` — zero matches
- `TODO(` — zero matches

#### Required Commands

- `python -m py_compile src/loops/manager.py` → exit 0
- `lsp_diagnostics filePath=src/loops/manager.py` → 0 new errors
- `python -m pytest tests/ -k "loop or cost" -v` → exit 0

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-006/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-006/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] LoopCostTracker not instantiated in LoopManager → FAIL
- [ ] Hard crash on Redis connection failure → FAIL (must be fail-soft)
- [ ] Type suppression in new code → FAIL
- [ ] Existing loop tests broken → FAIL

---

### RG-007: Add Prometheus /metrics Endpoint

**Status**: PENDING
**Depends On**: RG-004 (main.py collision — must wait for RG-004 to complete)
**Parallel With**: —
**Estimated Effort**: MEDIUM
**Gap Reference**: GAP-13

#### Description

The core FastAPI app has no Prometheus metrics endpoint. The monitoring stack (Prometheus) expects to scrape `http://guinevere-core:8000/metrics`. The fix adds a `/metrics` endpoint using `prometheus_client` (already in `pyproject.toml` as `prometheus-client>=0.21`) with basic application metrics.

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/core/main.py` | MODIFY | Add /metrics endpoint, request counter, request duration histogram |

#### Implementation Notes

- Import `prometheus_client` (`Counter`, `Histogram`, `generate_latest`, `CONTENT_TYPE_LATEST`)
- Define module-level metrics:
  - `guinevere_requests_total` — `Counter` with labels `method`, `endpoint`, `status`
  - `guinevere_request_duration_seconds` — `Histogram` with labels `method`, `endpoint`
- Add `@app.get("/metrics")` endpoint returning `generate_latest()` with correct content type
- Optionally add FastAPI middleware to auto-increment counters per request

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code
- `except Exception: pass` — zero matches
- `TODO(` — zero matches

#### Required Commands

- `python -m py_compile src/core/main.py` → exit 0
- `lsp_diagnostics filePath=src/core/main.py` → 0 new errors
- `python -c "from prometheus_client import generate_latest; print('ok')"` → exit 0

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-007/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-007/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] `/metrics` endpoint not accessible → FAIL
- [ ] `prometheus_client` not imported (reimplemented manually) → FAIL
- [ ] Content-Type header missing or incorrect on /metrics → FAIL
- [ ] Type suppression in new code → FAIL

---

## 7. Batch C — Security (RG-008..RG-009)

### RG-008: AUTH_MATRIX Runtime Enforcement

**Status**: PENDING
**Depends On**: RG-006
**Parallel With**: RG-009
**Estimated Effort**: MEDIUM
**Gap Reference**: GAP-07

#### Description

`AUTH_MATRIX` in `src/mcp/auth_matrix.py` is a comprehensive 16-tool registry mapping operations to `AuthLevel` values, but the `require_approval` decorator in `src/mcp/auth.py` does not validate against it. Tool modules declare their own auth levels via the decorator, but there is no runtime check that the decorator's declared level matches the matrix. The fix adds runtime verification in warn-only mode.

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/mcp/auth.py` | MODIFY | Add matrix validation in require_approval decorator |
| `src/mcp/manager.py` | MODIFY | Add startup call to verify_matrix_completeness() |

#### Implementation Notes

- In `require_approval` decorator wrapper:
  - Import `get_auth_level` from `src.mcp.auth_matrix`
  - Try `get_auth_level(tool_name, operation)` and compare with decorator's `level`
  - If mismatch: `logger.warning("auth_matrix_mismatch", ...)` but do NOT block (warn-only)
  - If tool_name not in matrix: `logger.warning("auth_matrix_tool_missing", ...)`
- In `src/mcp/manager.py` startup:
  - Call `verify_matrix_completeness()` and log result
  - If incomplete: log warning but don't crash

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code
- `except Exception: pass` — zero matches
- Hard-blocking on matrix mismatch (must be warn-only for now) — FAIL if blocking

#### Required Commands

- `python -m py_compile src/mcp/auth.py` → exit 0
- `python -m py_compile src/mcp/manager.py` → exit 0
- `lsp_diagnostics filePath=src/mcp/auth.py` → 0 new errors
- `lsp_diagnostics filePath=src/mcp/manager.py` → 0 new errors
- `python -m pytest tests/ -k "auth or matrix" -v` → exit 0

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-008/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-008/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] Matrix validation not added to require_approval → FAIL
- [ ] Validation is hard-blocking (should be warn-only) → FAIL
- [ ] verify_matrix_completeness() not called at startup → FAIL
- [ ] Type suppression in new code → FAIL

---

### RG-009: Enhanced Health Endpoint

**Status**: PENDING
**Depends On**: RG-007 (main.py collision)
**Parallel With**: RG-008
**Estimated Effort**: MEDIUM
**Gap Reference**: GAP-10 (partial)

#### Description

The existing `/health/detailed` endpoint checks loop manager, guardian, and Redis. The enhancement aggregates PostgreSQL and 9Router health into the same endpoint, and adds a Prometheus counter for health check failures.

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/core/main.py` | MODIFY | Add PG and 9Router health checks to /health/detailed; add failure counter |

#### Implementation Notes

- Add PostgreSQL health check: simple `SELECT 1` via async engine (fail-soft with 2s timeout)
- Add 9Router health check: HTTP GET to `http://localhost:20128/health` (fail-soft with 2s timeout)
- Add `guinevere_health_check_failures` Prometheus Counter with label `component`
- Increment counter on each component failure
- Keep existing Redis check and loop manager/guardian checks

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code
- `except Exception: pass` — zero matches
- Hard crash on component unavailability → FAIL

#### Required Commands

- `python -m py_compile src/core/main.py` → exit 0
- `lsp_diagnostics filePath=src/core/main.py` → 0 new errors
- `python -m pytest tests/ -k health -v` → exit 0

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-009/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-009/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] PG health check not added → FAIL
- [ ] 9Router health check not added → FAIL
- [ ] Prometheus failure counter not added → FAIL
- [ ] Any component failure crashes the endpoint → FAIL (must be fail-soft)

---

## 8. Batch D — Discord Stubs (RG-010..RG-014, sequential)

All steps in Batch D modify `src/discord/bot.py` and create new `cmd_*.py` files. They must execute sequentially. Each command follows the **5-part pattern**:

1. **Frozen dataclass** for command options/config
2. **Protocol** for injected dependencies
3. **structlog** logger
4. **Async callback** function with `discord.Interaction` parameter
5. **Error handling** with ephemeral responses

### Shared Command Pattern

```
# Canonical 5-part Discord command structure:
# 1. Frozen dataclass for config
# 2. Protocol for dependencies
# 3. structlog logger
# 4. Async callback(interaction: discord.Interaction) -> None
# 5. Error handling with ephemeral=True responses
```

### RG-010: Memory Commands (memory-forget, memory-export)

**Status**: PENDING
**Depends On**: RG-005 (bot.py must have ritual wiring complete)
**Parallel With**: —
**Estimated Effort**: MEDIUM
**Gap Reference**: GAP-11a (Phase 3)

#### Description

Implement two memory management commands currently stubbed in `_STUB_PHASE`:
- `memory-forget`: Mark a specific memory as DNR (Do Not Recall) by ID
- `memory-export`: Export memories as JSON, sent to user via DM

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/discord/cmd_memory_forget.py` | CREATE | memory-forget command implementation |
| `src/discord/cmd_memory_export.py` | CREATE | memory-export command implementation |
| `src/discord/bot.py` | MODIFY | Wire both commands, remove from _STUB_PHASE |

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code
- `except Exception: pass` — zero matches
- `TODO(` — zero matches
- Memory data logged in plaintext to journal — zero matches

#### Required Commands

- `python -m py_compile src/discord/cmd_memory_forget.py` → exit 0
- `python -m py_compile src/discord/cmd_memory_export.py` → exit 0
- `python -m py_compile src/discord/bot.py` → exit 0
- `lsp_diagnostics filePath=src/discord/cmd_memory_forget.py` → 0 new errors
- `lsp_diagnostics filePath=src/discord/cmd_memory_export.py` → 0 new errors
- `lsp_diagnostics filePath=src/discord/bot.py` → 0 new errors
- `grep -c 'memory-forget' src/discord/bot.py` → 0 in _STUB_PHASE dict

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-010/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-010/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] Commands still listed in `_STUB_PHASE` → FAIL
- [ ] Command callbacks not registered via `self.tree.command()` → FAIL
- [ ] Memory export sends data to public channel (must be DM) → FAIL
- [ ] No error handling for missing memory ID → FAIL

---

### RG-011: Finance Command (cost-alert)

**Status**: PENDING
**Depends On**: RG-010
**Parallel With**: —
**Estimated Effort**: SMALL
**Gap Reference**: GAP-11b (Phase 4)

#### Description

Implement the `cost-alert` command: set or view cost alert thresholds. When a loop's cost exceeds the threshold, the system fires a Discord notification.

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/discord/cmd_cost_alert.py` | CREATE | cost-alert command implementation |
| `src/discord/bot.py` | MODIFY | Wire command, remove from _STUB_PHASE |

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code
- `except Exception: pass` — zero matches
- `TODO(` — zero matches

#### Required Commands

- `python -m py_compile src/discord/cmd_cost_alert.py` → exit 0
- `python -m py_compile src/discord/bot.py` → exit 0
- `lsp_diagnostics filePath=src/discord/cmd_cost_alert.py` → 0 new errors
- `grep -c 'cost-alert' src/discord/bot.py` → 0 in _STUB_PHASE dict

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-011/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-011/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] Command still in `_STUB_PHASE` → FAIL
- [ ] No threshold validation (negative values accepted) → FAIL

---

### RG-012: System Commands (approve, deny, approve-all, focus, casual, consent, punishment, reward)

**Status**: PENDING
**Depends On**: RG-011
**Parallel With**: —
**Estimated Effort**: LARGE (8 commands)
**Gap Reference**: GAP-11c (Phase 4)

#### Description

Implement 8 system/persona interaction commands currently stubbed:

| Command | Purpose |
|---|---|
| `approve` | Approve a pending MCP destructive operation by tool name |
| `deny` | Deny a pending MCP destructive operation by tool name |
| `approve-all` | Approve all pending MCP operations |
| `focus` | Set Guinevere's operational focus mode |
| `casual` | Switch to casual/relaxed interaction mode |
| `consent` | View or modify consent grants |
| `punishment` | Trigger persona punishment workflow (Y4 boundary) |
| `reward` | Trigger persona reward workflow |

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/discord/cmd_approve.py` | CREATE | approve command |
| `src/discord/cmd_deny.py` | CREATE | deny command |
| `src/discord/cmd_approve_all.py` | CREATE | approve-all command |
| `src/discord/cmd_focus.py` | CREATE | focus command |
| `src/discord/cmd_casual.py` | CREATE | casual command |
| `src/discord/cmd_consent.py` | CREATE | consent command |
| `src/discord/cmd_punishment.py` | CREATE | punishment command |
| `src/discord/cmd_reward.py` | CREATE | reward command |
| `src/discord/bot.py` | MODIFY | Wire all 8 commands, remove from _STUB_PHASE |

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code
- `except Exception: pass` — zero matches
- `TODO(` — zero matches
- Y6 yandere content in punishment/reward commands — zero matches
- Consent bypass in consent command — zero matches

#### Required Commands

- `python -m py_compile src/discord/cmd_approve.py` → exit 0
- `python -m py_compile src/discord/cmd_deny.py` → exit 0
- `python -m py_compile src/discord/cmd_approve_all.py` → exit 0
- `python -m py_compile src/discord/cmd_focus.py` → exit 0
- `python -m py_compile src/discord/cmd_casual.py` → exit 0
- `python -m py_compile src/discord/cmd_consent.py` → exit 0
- `python -m py_compile src/discord/cmd_punishment.py` → exit 0
- `python -m py_compile src/discord/cmd_reward.py` → exit 0
- `python -m py_compile src/discord/bot.py` → exit 0
- `lsp_diagnostics filePath=src/discord/bot.py` → 0 new errors

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-012/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-012/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] Any command still in `_STUB_PHASE` → FAIL
- [ ] punishment/reward commands allow Y6 level → FAIL
- [ ] consent command allows bypass without explicit operator action → FAIL
- [ ] approve/deny don't call `src.mcp.auth.approve()`/`deny()` → FAIL

---

### RG-013: Admin Commands (restart-service, backup-now, health-check, clear-cache)

**Status**: PENDING
**Depends On**: RG-012
**Parallel With**: —
**Estimated Effort**: LARGE (4 commands)
**Gap Reference**: GAP-11d (Phase 4)

#### Description

Implement 4 administrative commands:

| Command | Purpose |
|---|---|
| `restart-service` | Restart a named systemd service (with safety checks) |
| `backup-now` | Trigger immediate database backup |
| `health-check` | Run comprehensive health check and display results |
| `clear-cache` | Clear Redis cache (with confirmation prompt) |

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/discord/cmd_restart_service.py` | CREATE | restart-service command |
| `src/discord/cmd_backup_now.py` | CREATE | backup-now command |
| `src/discord/cmd_health_check.py` | CREATE | health-check command |
| `src/discord/cmd_clear_cache.py` | CREATE | clear-cache command |
| `src/discord/bot.py` | MODIFY | Wire all 4 commands, remove from _STUB_PHASE |

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code
- `except Exception: pass` — zero matches
- `TODO(` — zero matches
- `rm -rf` or `DROP` in restart-service — zero matches
- Unrestricted service name (must whitelist allowed services) — FAIL

#### Required Commands

- `python -m py_compile src/discord/cmd_restart_service.py` → exit 0
- `python -m py_compile src/discord/cmd_backup_now.py` → exit 0
- `python -m py_compile src/discord/cmd_health_check.py` → exit 0
- `python -m py_compile src/discord/cmd_clear_cache.py` → exit 0
- `python -m py_compile src/discord/bot.py` → exit 0
- `lsp_diagnostics filePath=src/discord/bot.py` → 0 new errors

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-013/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-013/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] Any command still in `_STUB_PHASE` → FAIL
- [ ] restart-service accepts arbitrary service names → FAIL (must whitelist `guinevere-*`)
- [ ] clear-cache executes without confirmation → FAIL
- [ ] backup-now doesn't verify backup completion → FAIL

---

### RG-014: Loop Commands (loop-pause, loop-resume, loops, evidence, loop-priority)

**Status**: PENDING
**Depends On**: RG-013
**Parallel With**: —
**Estimated Effort**: LARGE (5 commands)
**Gap Reference**: GAP-11e (Phase 5)

#### Description

Implement 5 loop management commands:

| Command | Purpose |
|---|---|
| `loop-pause` | Pause the active loop (suspend phase execution) |
| `loop-resume` | Resume a paused loop |
| `loops` | List all active and recent loops with status |
| `evidence` | View evidence artifacts for a specific loop |
| `loop-priority` | Set or change loop execution priority |

#### Expected Files

| File | Action | Description |
|---|---|---|
| `src/discord/cmd_loop_pause.py` | CREATE | loop-pause command |
| `src/discord/cmd_loop_resume.py` | CREATE | loop-resume command |
| `src/discord/cmd_loops.py` | CREATE | loops command |
| `src/discord/cmd_evidence.py` | CREATE | evidence command |
| `src/discord/cmd_loop_priority.py` | CREATE | loop-priority command |
| `src/discord/bot.py` | MODIFY | Wire all 5 commands, remove from _STUB_PHASE |

#### Forbidden Patterns

- `as any` / `# type: ignore` — zero matches in new code
- `except Exception: pass` — zero matches
- `TODO(` — zero matches

#### Required Commands

- `python -m py_compile src/discord/cmd_loop_pause.py` → exit 0
- `python -m py_compile src/discord/cmd_loop_resume.py` → exit 0
- `python -m py_compile src/discord/cmd_loops.py` → exit 0
- `python -m py_compile src/discord/cmd_evidence.py` → exit 0
- `python -m py_compile src/discord/cmd_loop_priority.py` → exit 0
- `python -m py_compile src/discord/bot.py` → exit 0
- `lsp_diagnostics filePath=src/discord/bot.py` → 0 new errors
- `grep '_STUB_PHASE' src/discord/bot.py` → dict should be empty after all commands removed

#### Evidence Requirements

- `docs/setup-evidence/runtime-gaps/STEP-RG-014/verification.md`
- `docs/setup-evidence/runtime-gaps/STEP-RG-014/auditor-gate.md`

#### Hard Rejection Criteria

- [ ] Any command still in `_STUB_PHASE` → FAIL
- [ ] `_STUB_PHASE` dict not empty after all Batch D steps → FAIL
- [ ] loops command doesn't query `LoopManager.list_loops()` → FAIL
- [ ] evidence command exposes raw surveillance data → FAIL

---

## 9. Batch E — Deferred Architectural Scaffolds (RG-015..RG-016)

> **These steps are NOT implementable in the current session.** They require architectural decisions from Faiz regarding LLM provider integration strategy, prompt engineering approach, and MCP bridge design. Only architectural scaffolds (design outlines) are provided.

### RG-015: Loop LLM Integration

**Status**: DEFERRED
**Depends On**: Architectural decision from Faiz
**Estimated Effort**: XLARGE
**Gap References**: GAP-02, GAP-08, GAP-14, GAP-15

#### Architectural Scaffold

**Problem**: All 7 loop phases (`src/loops/phases/*.py`) return static template strings. Zero LLM calls exist in the entire loop pipeline. The autonomous loop is effectively a template generator.

**Design Outline** (for future implementation):

1. **LLM Provider Abstraction**: Create `src/loops/llm_provider.py` with Protocol-based design
   - `LLMProvider` Protocol with `async complete(prompt, system, max_tokens) -> LLMResponse`
   - `NineRouterProvider` implementation using 9Router API
   - `MockProvider` for testing

2. **Phase Handler Migration**: Each phase handler (`phases/*.py`) must:
   - Accept an `LLMProvider` injection
   - Construct a phase-specific prompt from task/goal/context
   - Call `provider.complete()` and parse the response
   - Return structured artifact (not template string)

3. **Cross-Phase Context Flow** (GAP-15):
   - Phase N reads artifacts from Phase N-1 via `EvidencePipeline`
   - Context window management for 1M token limit
   - Summarization strategy for accumulated artifacts

4. **Sub-Agent Execution** (GAP-14):
   - `SubAgentSpawner` must invoke LLM via provider
   - DeepSeek V4 Flash for sub-agent tasks (cost-efficient)
   - Result aggregation back to parent loop

5. **MCP Bridge** (GAP-08):
   - Loop phases need access to MCP tools for research/execution
   - Bridge pattern: `LoopMCPBridge` wrapping `MCPManager`
   - Auth enforcement via AUTH_MATRIX (depends on RG-008)

**Blocking Decisions Needed**:
- LLM prompt format (system prompt per phase vs. unified)
- Token budget allocation per phase
- Sub-agent model selection strategy
- MCP tool whitelist per phase

---

### RG-016: MCP Tool Bridge

**Status**: DEFERRED
**Depends On**: RG-015 (Loop LLM integration must exist first)
**Estimated Effort**: LARGE
**Gap References**: GAP-01, GAP-16

#### Architectural Scaffold

**Problem**: The conversational handler (`src/discord/conversational_handler.py`) cannot invoke MCP tools. Chat messages in `#guinevere-chat` cannot trigger tool execution. Additionally, `ToolSelector` (`src/mcp/tool_selector.py`) exists but is never called.

**Design Outline** (for future implementation):

1. **Conversational Tool Use**:
   - Parse LLM response for tool-use function calls
   - Route through `MCPManager` with AUTH_MATRIX enforcement
   - Return tool results to LLM for final response generation

2. **ToolSelector Wiring** (GAP-16):
   - Inject `ToolSelector` into conversational handler
   - Pre-filter available tools based on context and auth level
   - Rank tools by relevance before presenting to LLM

3. **Discord UX for Tool Results**:
   - Embed formatting for tool output
   - Pagination for large results
   - Approval flow integration for DESTRUCTIVE_APPROVAL tools

**Blocking Decisions Needed**:
- Function calling format (OpenAI-compatible vs. custom)
- Tool result size limits for Discord embeds
- Approval UX in Discord (buttons vs. text commands)

---

## 10. Auditor Matrix

| Step | Code Quality | Security | Integration | Safety (Persona) |
|---|---|---|---|---|
| RG-001 | ✅ Required | ✅ Recommended | — | — |
| RG-002 | ✅ Required | ✅ Recommended | — | — |
| RG-003 | ✅ Required | ✅ Recommended | — | — |
| RG-004 | ✅ Required | — | ✅ Required | — |
| RG-005 | ✅ Required | — | ✅ Required | ✅ Required (ritual content) |
| RG-006 | ✅ Required | — | ✅ Required | — |
| RG-007 | ✅ Required | — | ✅ Required | — |
| RG-008 | ✅ Required | ✅ **Mandatory** | ✅ Required | — |
| RG-009 | ✅ Required | — | ✅ Required | — |
| RG-010 | ✅ Required | — | ✅ Required | — |
| RG-011 | ✅ Required | — | ✅ Required | — |
| RG-012 | ✅ Required | ✅ Recommended | ✅ Required | ✅ Required (punishment/reward) |
| RG-013 | ✅ Required | ✅ **Mandatory** (restart-service) | ✅ Required | — |
| RG-014 | ✅ Required | — | ✅ Required | — |

### Auditor Scope Definitions

**Code Quality Auditor**:
- Type safety (no `as any`, `# type: ignore`, `@ts-ignore`)
- Error handling (no empty catch/except)
- Code style consistency (frozen dataclass, Protocol, structlog)
- No dead code or TODO markers

**Security Auditor**:
- No hardcoded secrets
- Auth boundary verification (AUTH_MATRIX, consent gates)
- Service isolation (no cross-service credential leakage)
- Whitelist enforcement (restart-service, clear-cache)

**Integration Auditor**:
- Import chain validation (no circular imports)
- Runtime wiring verification (component actually started)
- Graceful degradation (fail-soft on dependency unavailability)
- Cross-component communication (Redis, DB, Discord)

**Safety (Persona) Auditor**:
- PersonaSafetyPolicy compliance (Y4 baseline, Y5 ceiling, Y6 forbidden)
- Consent boundary preservation
- No intimate data exposure in ritual messages
- HARD STOP protocol not bypassed
- Distress protocol not suppressed

---

## 11. Rollback Plan

### Batch A — Service Infrastructure

| Step | Rollback Action | Verification | Data Loss |
|---|---|---|---|
| RG-001 | Restore original .service files from git; remove generated .env files | `systemctl daemon-reload`; services revert to dead state | None — env files are generated, not persisted data |
| RG-002 | Remove `monitoring/.env`; restore original `guinevere-monitoring.service`; `docker compose down` | `systemctl is-active guinevere-monitoring` → `inactive` | None — monitoring data in `/home/guinevere/data/` preserved |
| RG-003 | Remove `GUINEVERE_9ROUTER_API_KEY` from `.env.discord`; delete `.env.core` | Restart services; embedding calls fail gracefully | None — env vars only |

### Batch B — Wiring Fixes

| Step | Rollback Action | Verification | Data Loss |
|---|---|---|---|
| RG-004 | `git checkout src/core/main.py` (pre-RG-004 state) | `python -m py_compile src/core/main.py` → exit 0 | None — consumer not processing events, buffer accumulates |
| RG-005 | `git checkout src/discord/bot.py` (pre-RG-005 state) | Rituals stop delivering to Discord | None — scheduler logs locally as before |
| RG-006 | `git checkout src/loops/manager.py` | Loop execution continues without cost tracking | None — cost data simply not recorded |
| RG-007 | `git checkout src/core/main.py` (pre-RG-007 state) | `/metrics` endpoint removed | None — metrics not yet scraped |

### Batch C — Security

| Step | Rollback Action | Verification | Data Loss |
|---|---|---|---|
| RG-008 | `git checkout src/mcp/auth.py src/mcp/manager.py` | AUTH_MATRIX validation removed | None — warn-only mode, no behavioral change |
| RG-009 | `git checkout src/core/main.py` (pre-RG-009 state) | Enhanced health checks removed | None — basic health endpoint still works |

### Batch D — Discord Stubs

| Step | Rollback Action | Verification | Data Loss |
|---|---|---|---|
| RG-010..RG-014 | `git checkout src/discord/bot.py`; delete new `cmd_*.py` files | Commands revert to stub responses | None — no persistent state created by commands |

### Batch E — Deferred

| Step | Rollback Action |
|---|---|
| RG-015, RG-016 | N/A — scaffold documents only, no code changes |

---

## 12. Evidence Paths

| Artifact | Path |
|---|---|
| Master Gap Report | `research-reports/runtime-gap-analysis/master-gap-report.md` |
| This Batch Plan | `docs/setup-evidence/runtime-gaps/batch-plan-runtime-gaps.md` |
| Per-Step Evidence | `docs/setup-evidence/runtime-gaps/STEP-RG-{NNN}/verification.md` |
| Per-Step Auditor Gate | `docs/setup-evidence/runtime-gaps/STEP-RG-{NNN}/auditor-gate.md` |
| Audit Reports | `audit-reports/runtime-gaps/` |

### Evidence Directory Structure

```
docs/setup-evidence/runtime-gaps/
├── batch-plan-runtime-gaps.md          # This file
├── STEP-RG-001/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-002/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-003/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-004/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-005/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-006/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-007/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-008/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-009/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-010/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-011/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-012/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-013/
│   ├── verification.md
│   └── auditor-gate.md
├── STEP-RG-014/
│   ├── verification.md
│   └── auditor-gate.md
└── STEP-RG-015/
    └── scaffold.md                      # Deferred — architecture only
└── STEP-RG-016/
    └── scaffold.md                      # Deferred — architecture only
```

---

## 13. Execution Checklist

### Pre-Implementation

- [ ] Read and verify this batch plan
- [ ] Confirm all source files match expected state (line counts, key structures)
- [ ] Verify VPS SSH access and SOPS key availability
- [ ] Confirm `.gitignore` includes `.env.*` patterns
- [ ] Create evidence directory structure

### Batch A (Parallel Wave)

- [ ] RG-001: Fix service env vars
- [ ] RG-002: Fix monitoring service
- [ ] RG-003: Set embedding API key
- [ ] All 3 verified on VPS

### Batch B (Sequenced)

- [ ] RG-004: Wire SurveillanceConsumer → verify → audit
- [ ] RG-005: Wire RitualScheduler (parallel with RG-004) → verify → audit
- [ ] RG-006: Wire LoopCostTracker (parallel with RG-004) → verify → audit
- [ ] RG-007: Add /metrics endpoint (after RG-004) → verify → audit

### Batch C (Sequenced)

- [ ] RG-008: AUTH_MATRIX enforcement → verify → security audit
- [ ] RG-009: Enhanced health endpoint → verify → audit

### Batch D (Sequential)

- [ ] RG-010: Memory commands → verify → audit
- [ ] RG-011: Finance command → verify → audit
- [ ] RG-012: System commands → verify → audit
- [ ] RG-013: Admin commands → verify → audit
- [ ] RG-014: Loop commands → verify → audit
- [ ] Verify `_STUB_PHASE` dict is empty

### Post-Implementation

- [ ] All evidence files created
- [ ] All auditor gates PASS
- [ ] `lsp_diagnostics` clean on all modified files
- [ ] `_STUB_PHASE` dict empty (all commands wired)
- [ ] All VPS services active (8/8 excluding obscura)
- [ ] Monitoring stack running (all 8 containers)
- [ ] `/metrics` endpoint returning Prometheus format
- [ ] `/health/detailed` returning all component checks

---

## 14. Binding Decisions Log

| Decision | Value | Rationale | Step |
|---|---|---|---|
| Service env approach | Per-service .env files via SOPS | Portable, testable, no systemd credential leak | RG-001 |
| Monitoring compose | Use existing `compose.monitoring.yml` | Already verified in P8, 8 services defined | RG-002 |
| Ritual delivery channel | `#guinevere-chat` (ID: `1510914600777023659`) | Matches SystemPromptMaster §G | RG-005 |
| AUTH_MATRIX enforcement | Warn-only mode initially | Avoid breaking existing tool flow; hard-block in follow-up | RG-008 |
| Prometheus client | `prometheus-client` from pyproject.toml | Already declared as dependency | RG-007 |
| Loop LLM integration | DEFERRED | Requires architectural decision on provider/prompt strategy | RG-015 |
| MCP tool bridge | DEFERRED | Depends on RG-015 (loop LLM) | RG-016 |
| Command pattern | 5-part: dataclass + Protocol + structlog + async callback + error handling | Consistent with existing `cmd_*.py` files | RG-010..RG-014 |
| main.py sequencing | RG-004 → RG-007 → RG-009 | Avoid merge conflicts on same file | B+C |
| bot.py sequencing | RG-005 → RG-010 → RG-011 → RG-012 → RG-013 → RG-014 | Avoid merge conflicts on same file | B+D |

---

## 15. Caveats and Known Risks

1. **VPS-only steps**: RG-001, RG-002, RG-003 involve VPS-side changes (systemd, .env files, docker compose). These cannot be fully verified from the local development environment. VPS SSH access is required.

2. **Redis dependency**: RG-004 (surveillance consumer) and RG-006 (loop cost tracker) both require Redis connectivity. If Redis is down on VPS, these will fail-soft but won't provide functional verification.

3. **Database dependency**: RG-004 (surveillance consumer DB writes) and RG-009 (PG health check) require PostgreSQL. The surveillance consumer needs `surveillance.events` table to exist.

4. **Discord bot token**: RG-005 and Batch D changes require bot restart to take effect. Sync of slash commands may take up to 1 hour globally (instant in single guild).

5. **Batch E deferral**: RG-015 and RG-016 are architectural scaffolds only. They cannot be implemented without Faiz's explicit direction on LLM provider strategy. The scaffold documents provide starting points for future sessions.

6. **Obscura gap**: `guinevere-obscura.service` is dead due to missing binary (`/usr/local/bin/obscura`). This is NOT in scope for this batch — it requires a separate installation decision.

7. **Pre-existing type: ignore**: `src/discord/bot.py` line 32 has `_BotBase: type = commands.Bot  # type: ignore[assignment]`. This is pre-existing and acceptable. New code must not add additional type suppressions.

---

## 16. Footer

| Field | Value |
|---|---|
| Plan Version | 1.0 |
| Generated | 2026-06-03 |
| Source Research | `research-reports/runtime-gap-analysis/master-gap-report.md` |
| Source Files Read | `src/core/main.py`, `src/discord/bot.py`, `src/loops/manager.py`, `src/loops/cost.py`, `src/mcp/auth.py`, `src/mcp/auth_matrix.py`, `src/surveillance/consumer.py`, `src/persona/ritual_scheduler.py`, `systemd/*.service` (4 files), `monitoring/compose.monitoring.yml` |
| Total Steps | 16 (14 implementable + 2 deferred) |
| Estimated Total Effort | 4-6 focused sessions |
| Approval Required | Faiz (operator) |

> This plan is the authoritative implementation guide for the runtime gap closure. Every step must pass its verification scaffold before proceeding. No step may skip its auditor gate. Batch E scaffolds require Faiz's architectural sign-off before any implementation begins.

# P5 Runtime/Live Reconciliation

**Date:** 2026-06-27
**Method:** Local code analysis (no VPS SSH access from audit environment)

---

## Runtime Wiring Verification (from Source Code)

### Application Entry Point

| Checkpoint | File | Line | Status |
|-----------|------|------|--------|
| LoopManager instantiated | `src/core/main.py` | 103 | ✅ `LoopManager(llm_router=None)` |
| Stored on app.state | `src/core/main.py` | 104 | ✅ `app.state.loop_manager = loop_manager` |
| HardStopHandler wired | `src/core/main.py` | 109-110 | ✅ `set_hard_stop_handler(hard_stop_handler)` |
| Guardian monitor started | `src/core/main.py` | 116 | ✅ Background task |
| HermesBridge created | `src/core/main.py` | 470 | ✅ (but superseded by life_kernel) |
| Resume pending loops | `src/core/main.py` | 479 | ✅ `await loop_manager.resume_pending_loops()` |
| Guardian cleanup on shutdown | `src/core/main.py` | 589 | ✅ `await loop_manager.guardian.stop()` |
| Health check includes loop_mgr | `src/core/main.py` | 671-683 | ✅ |

### API Routes

| Endpoint | File | Line | Status |
|----------|------|------|--------|
| _get_loop_manager() | routes.py | 42-44 | ✅ From request.app.state |
| list_loops | routes.py | ~56 | ✅ Real LoopManager calls |
| create_loop | routes.py | ~75 | ✅ Real LoopManager calls |
| get_loop | routes.py | ~98 | ✅ |
| cancel_loop | routes.py | ~117 | ✅ |
| pause_loop | routes.py | ~134 | ✅ |
| resume_loop | routes.py | ~156 | ✅ |
| update_loop_priority | routes.py | ~190 | ✅ |
| get_loop_evidence | routes.py | ~221 | ✅ |
| alertmanager_webhook | routes.py | present | ✅ |

### Discord Commands

| Command | File | Line | Status |
|---------|------|------|--------|
| /loop-start registered | _command_registry.py | 137 | ✅ |
| /loop-stop registered | _command_registry.py | 141 | ✅ |
| loop_start_callback imported | _entrypoint.py | 180 | ✅ |
| loop_stop_callback imported | _entrypoint.py | 181 | ✅ |
| Command tree registration | _entrypoint.py | 279-287 | ✅ |

### Hermes Plugin Commands

| Command | File | Status |
|---------|------|--------|
| loop_start | src/hermes_plugins/commands_loop/loop_start.py | ✅ Uses httpx |
| loop_stop | src/hermes_plugins/commands_loop/loop_stop.py | ✅ Uses httpx |
| loop_pause | src/hermes_plugins/commands_loop/loop_pause.py | ✅ Uses httpx |
| loop_resume | src/hermes_plugins/commands_loop/loop_resume.py | ✅ Uses httpx |
| loop_priority | src/hermes_plugins/commands_loop/loop_priority.py | ✅ Uses httpx |
| evidence | src/hermes_plugins/commands_loop/evidence.py | ✅ Uses httpx |
| loops | src/hermes_plugins/commands_loop/loops.py | ✅ Uses httpx |

### Systemd Services

| Service | ExecStart | Valid Path | Hardening |
|---------|-----------|-----------|-----------|
| guinevere-loops.service | `python -m src.loops.manager` | ✅ (has __main__) | 13 directives |
| guinevere-scheduler.service | `python -m src.loops.scheduler` | ✅ | 13 directives |

---

## Runtime Activation Assessment

| Component | Deployed? | Active? | Dormant Reason |
|-----------|-----------|---------|----------------|
| LoopManager | YES (in main.py) | PARTIALLY | llm_router=None makes phase execution template-only |
| LoopGuardian | YES (background task) | YES | 30-second monitoring tick |
| HardStopHandler | YES (wired to guardian) | YES | Checked on guardian tick, not per-phase |
| LoopScheduler | YES (separate service) | YES | APScheduler cron |
| API Routes | YES (mounted in FastAPI) | YES | 9 endpoints active |
| Discord Commands | YES (registered) | YES | /loop-start and /loop-stop active |
| Hermes Plugin Commands | YES (7 commands) | YES | httpx-based API calls |
| HermesBridge | YES (in code) | NO | Superseded by life_kernel |
| LoopSafetyGate | YES (module exists) | NO | Not called from _run_loop() |
| IterationBudget | YES (module exists) | NO | Only used by ConversationLoop |
| TodoEnforcer | YES (exported) | NO | Zero production callers |
| HashAnchor | YES (exported) | NO | Zero production callers |
| SubAgentSpawner | YES (exported) | NO | Zero production callers |
| TaskContract | YES (exported) | NO | Zero production callers |
| OutputVerifier | YES (exported) | NO | Zero production callers |

---

## VPS Live Verification (Not Performed)

**CAVEAT:** This audit was conducted from a local Windows machine. VPS SSH access was NOT available for:
- `systemctl status guinevere-loops guinevere-scheduler` — service running state
- `journalctl -u guinevere-core --since "1 hour ago"` — LoopManager startup logs
- `curl http://localhost:8000/api/v1/loops` — live API response
- PostgreSQL query: `SELECT * FROM projects.loop_instances ORDER BY created_at DESC LIMIT 5`
- Redis: `redis-cli -n 5 KEYS 'loop_cost:*'`

**Recommendation:** VPS live verification is a REQUIRED follow-up gate before final P5 status determination.

---

## Verdict

The source code proves that Phase 5 infrastructure IS deployed and IS wired into the application lifecycle. The loop system runs at startup, monitors loops, and exposes API/Discord/Hermes interfaces. However, `llm_router=None` makes the SDLC loop functionally a non-LLM task executor, and several safety modules (LoopSafetyGate, IterationBudget) exist but are not wired to the main loop execution path.

**Classification:** PARTIALLY_IMPLEMENTED — infrastructure is live, but key features (LLM autonomy, safety gates, budget enforcement) are dormant or unwired.

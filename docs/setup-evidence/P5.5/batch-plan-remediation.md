# P5.5 Remediation Batch Plan

> **Batch**: P5.5 — Post-Audit Remediation
> **Date**: 2026-06-02
> **Author**: Guinevere (Parent Orchestrator)
> **Source**: P5-FINAL-AUDIT.md (CONDITIONAL PASS, 17 CRITICAL, 11 HIGH)
> **Scope**: 10 blocker fixes, 13 files modified, 3 files copied

---

## 1. Dependency Map

```
WAVE A — Independent (parallel, no shared files):
  FIX 1 (C-05): Migration chain         → alembic/versions/ (3 copies + 1 edit)
  FIX 3 (C-06): Redis error handling     → src/loops/cost.py
  FIX 5 (H-02): Guardian monitor()       → src/loops/guardian.py (shared with FIX 4)
  FIX 7 (C-10/11): Systemd hardening     → systemd/*.service
  FIX 9 (H-04): logger.exception         → src/loops/manager.py

WAVE B — Sequential (depends on Wave A):
  FIX 4 (C-02): Guardian kill_loop()     → src/loops/guardian.py (shared with FIX 5)
    → Depends on FIX 5 (monitor exception handling done first)

WAVE C — Sequential (depends on FIX 1 for migration context):
  FIX 2 (C-17): Add indexes              → alembic migration + model (shared with FIX 1)
    → Depends on FIX 1 (migration chain fixed first)

WAVE D — Independent (parallel, but touches shared auth module):
  FIX 6 (C-16): Remove dev-key fallback  → auth.py + cmd_loop_start.py + cmd_loop_stop.py

WAVE E — Sequential (depends on FIX 3,5,9 for LoopManager readiness):
  FIX 8 (C-07/08/09): Wire LoopManager  → routes.py + main.py
  FIX 10 (C-12): Health check endpoint   → routes.py (shared with FIX 8)
    → Depends on FIX 8 (LoopManager wired first)
```

### Collision Scan

| Collision | Files | Resolution |
|---|---|---|
| guardian.py | FIX 4 + FIX 5 | Sequential: FIX 5 first, then FIX 4 |
| routes.py | FIX 8 + FIX 10 | Sequential: FIX 8 first, then FIX 10 |
| alembic/ | FIX 1 + FIX 2 | Sequential: FIX 1 first, then FIX 2 |
| auth.py | FIX 6 (3 files) | Single agent handles all 3 |

---

## 2. Implementation Waves

### WAVE A (parallel) — FIX 1, 3, 5, 7, 9

### WAVE B (sequential) — FIX 4 (after FIX 5)

### WAVE C (sequential) — FIX 2 (after FIX 1)

### WAVE D (parallel with B/C) — FIX 6

### WAVE E (sequential) — FIX 8, then FIX 10

---

## 3. Per-Step Verification Scaffolds

### FIX 1 — C-05: Fix Migration Chain

| Field | Value |
|---|---|
| Expected Files | `alembic/versions/2bed93fd1dd0_baseline_init.py` (copy from VPS or create minimal), `alembic/versions/e401bb5fd274_initial_schema_47_tables.py` (copy from `tmp/migration.py`), `alembic/versions/65f863220922_add_search_vector_do_not_recall.py` (copy from `docs/setup-evidence/P3/STEP-P3-008/`), `alembic/versions/p5_extend_loop_instances.py` (edit down_revision) |
| Forbidden Patterns | `as any`, `@ts-ignore`, `# type: ignore`, SQLite references |
| Required Commands | `python -c "import importlib.util; spec=importlib.util.spec_from_file_location('m','alembic/versions/p5_extend_loop_instances.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); assert mod.down_revision=='65f863220922', f'Wrong: {mod.down_revision}'"` → exit 0 |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-01/verification.md` |
| Hard Rejection Criteria | 4 files NOT in alembic/versions/, down_revision != "65f863220922", any migration file missing revision/down_revision fields |

### FIX 2 — C-17: Add Indexes to loop_instances

| Field | Value |
|---|---|
| Expected Files | `alembic/versions/p5_add_loop_indexes.py` (NEW migration), `src/memory/models.py` (ADD Index objects to LoopInstances.__table_args__) |
| Forbidden Patterns | `as any`, bare `except`, SQLite |
| Required Commands | `python -c "from src.memory.models import LoopInstances; indexes = [i.name for i in LoopInstances.__table__.indexes]; print(indexes); assert len(indexes) >= 3, f'Only {len(indexes)} indexes'"` → exit 0 |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-02/verification.md` |
| Hard Rejection Criteria | Fewer than 3 indexes, migration down_revision != "p5_extend_loops", indexes not in both migration AND model |

### FIX 3 — C-06: Redis Error Handling in cost.py

| Field | Value |
|---|---|
| Expected Files | `src/loops/cost.py` (MODIFY — add try/except RedisError to all 3 public methods) |
| Forbidden Patterns | `except:` (bare), `except Exception: pass`, `as any`, empty catch |
| Required Commands | `python -c "from src.loops.cost import LoopCostTracker; print('import OK')"` → exit 0; `grep -n 'except.*RedisError\|except.*ConnectionError\|except.*redis' src/loops/cost.py | wc -l` → >= 3 |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-03/verification.md` |
| Hard Rejection Criteria | Any bare except, any method without Redis error handling, import failure |

### FIX 4 — C-02: Guardian.kill_loop() Fix

| Field | Value |
|---|---|
| Expected Files | `src/loops/guardian.py` (MODIFY kill_loop method at ~line 95) |
| Forbidden Patterns | bare `except`, empty catch, `as any` |
| Required Commands | `python -c "from src.loops.guardian import LoopGuardian; g = LoopGuardian(); print('import OK')"` → exit 0; `grep -n 'state_machine\|cancel\|fail' src/loops/guardian.py | wc -l` → >= 3 |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-04/verification.md` |
| Hard Rejection Criteria | kill_loop() doesn't call state machine transition, doesn't handle task cancellation, no exception logging |

### FIX 5 — H-02: Guardian monitor() Exception Handling

| Field | Value |
|---|---|
| Expected Files | `src/loops/guardian.py` (MODIFY monitor method at ~line 105) |
| Forbidden Patterns | bare `except`, `except Exception: pass`, `as any` |
| Required Commands | `python -c "from src.loops.guardian import LoopGuardian; import inspect; src = inspect.getsource(LoopGuardian.monitor); assert 'except' in src, 'No exception handling'; print('PASS')"` → exit 0 |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-05/verification.md` |
| Hard Rejection Criteria | monitor() has no try/except wrapper around the monitoring loop body |

### FIX 6 — C-16: Remove Dev-Key Fallback

| Field | Value |
|---|---|
| Expected Files | `src/core/api/auth.py` (MODIFY — remove _DEV_DEFAULT_KEY fallback, raise if env not set), `src/discord/cmd_loop_start.py` (MODIFY line ~344), `src/discord/cmd_loop_stop.py` (MODIFY line ~384) |
| Forbidden Patterns | `guinevere-dev-key` (must return ZERO matches) |
| Required Commands | `grep -rn 'guinevere-dev-key' src/` → 0 results (exit 1 from grep = PASS); `python -c "from src.core.api.auth import verify_api_key; print('import OK')"` → exit 0 |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-06/verification.md` |
| Hard Rejection Criteria | ANY occurrence of "guinevere-dev-key" in src/, import failure |

### FIX 7 — C-10/11: Systemd Hardening

| Field | Value |
|---|---|
| Expected Files | `systemd/guinevere-loops.service` (MODIFY — add 13 hardening directives), `systemd/guinevere-scheduler.service` (MODIFY — same) |
| Forbidden Patterns | None specific |
| Required Commands | `grep -c 'NoNewPrivileges\|ProtectSystem\|MemoryHigh\|CPUQuota\|ProtectHome\|ReadWritePaths' systemd/guinevere-loops.service` → >= 6; same for scheduler.service → >= 6; `grep 'REDIS_PASSWORD' systemd/guinevere-loops.service` → >= 1 |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-07/verification.md` |
| Hard Rejection Criteria | Any hardening directive missing from either file, REDIS_PASSWORD not in Environment |

### FIX 8 — C-07/08/09: Wire LoopManager to Routes

| Field | Value |
|---|---|
| Expected Files | `src/core/api/routes.py` (MODIFY — replace stubs with LoopManager calls), `src/core/main.py` (MODIFY — add LoopManager to lifespan/app.state) |
| Forbidden Patterns | `as any`, stub/hardcoded returns in endpoints, `status="unknown"`, `status="pending"` (static) |
| Required Commands | `python -c "from src.core.api.routes import router; print('import OK')"` → exit 0; `python -c "from src.core.main import app; print('import OK')"` → exit 0; `grep -n 'loop_manager\|LoopManager' src/core/api/routes.py | wc -l` → >= 3; `grep -n 'loop_manager\|LoopManager' src/core/main.py | wc -l` → >= 2 |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-08/verification.md` |
| Hard Rejection Criteria | Any endpoint still returns hardcoded data, no LoopManager reference in routes.py, no LoopManager in main.py lifespan |

### FIX 9 — H-04: logger.exception in manager.py

| Field | Value |
|---|---|
| Expected Files | `src/loops/manager.py` (MODIFY — replace logger.error with logger.exception in except blocks) |
| Forbidden Patterns | `logger.error` inside except blocks (must be `logger.exception`) |
| Required Commands | `python -c "from src.loops.manager import LoopManager; print('import OK')"` → exit 0; `grep -n 'logger.error' src/loops/manager.py` → 0 results inside except blocks |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-09/verification.md` |
| Hard Rejection Criteria | Any logger.error inside an except block (logger.exception required for stack traces) |

### FIX 10 — C-12: Health Check Endpoint

| Field | Value |
|---|---|
| Expected Fields | `src/core/api/routes.py` (MODIFY — add GET /api/v1/health endpoint) |
| Forbidden Patterns | `as any`, bare except |
| Required Commands | `python -c "from src.core.api.routes import router; routes = [r.path for r in router.routes]; assert '/health' in routes or any('health' in r for r in routes), f'No health endpoint: {routes}'; print('PASS')"` → exit 0 |
| Evidence Requirements | `evidence/phase-5.5/STEP-FIX-10/verification.md` |
| Hard Rejection Criteria | No health endpoint in routes, endpoint doesn't return JSON with status fields |

---

## 4. Auditor Matrix

| Auditor | Dimensions | After Wave |
|---|---|---|
| A1: Code Quality | D01, D11 | Wave E |
| A2: Security | D03, D09 | Wave D |
| A3: Integration | D02 | Wave E |
| A4: DB Migration | D05 | Wave C |
| A5: Error Handling | D10 | Wave E |
| A6: Operations | D12 | Wave E |

---

## 5. Rollback Plan

Each fix is isolated to specific files. Rollback = `git checkout <file>` for each modified file. Migration rollback = delete the 3 copied files + revert down_revision change.

---

## 6. Caveats

1. **2bed93fd1dd0 baseline migration**: Only exists on VPS. If not available locally, create a minimal stub with `revision="2bed93fd1dd0"`, `down_revision=None`, empty upgrade/downgrade. The actual base tables are created by `Base.metadata.create_all()` not by this migration.
2. **FIX 8 (Wire LoopManager)**: This is the most complex fix. The LoopManager is designed as a standalone asyncio service with its own event loop. Wiring it into FastAPI requires either: (a) shared instance via app.state with lifespan management, or (b) HTTP proxy from FastAPI to standalone LoopManager service. Option (a) is simpler and chosen.
3. **FIX 4 (kill_loop)**: Guardian currently has no reference to asyncio.Task objects. Fix requires adding task references to `active_loops` dict or accepting a cancel callback.

---

*Plan authored by Guinevere. No fix begins until parent verifies scaffold compliance.*

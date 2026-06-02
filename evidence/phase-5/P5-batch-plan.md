# P5 Agent Loop — Batch Implementation Plan

**Batch**: P5-001 to P5-023 (23 steps)  
**Date**: 2026-06-02  
**Planner**: Guinevere (parent)  
**Status**: APPROVED by Faiz

## Design Decisions (Approved)

1. **Extend existing `projects.loop_instances`** — no new `loops` schema, no alembic env.py changes
2. **API**: `src/core/api/routes.py` + `APIRouter(prefix="/api/v1")`, JWT auth middleware
3. **Discord**: thin wrappers in `src/discord/cmd_loop_*.py` calling `src/loops/` engine
4. **task_id FK nullable** — backward-compatible migration, documented as intentional

## New File Manifest (24 files)

| # | File | Step(s) |
|---|---|---|
| 1 | `src/core/api/routes.py` | P5-001 |
| 2 | `src/core/api/auth.py` | P5-002 |
| 3 | `src/loops/state_machine.py` | P5-003 |
| 4 | `src/loops/artifacts.py` | P5-004 |
| 5 | `src/loops/phases/__init__.py` | P5-004..010 |
| 6 | `src/loops/phases/research.py` | P5-004 |
| 7 | `src/loops/phases/plan_delegate.py` | P5-005 |
| 8 | `src/loops/phases/delegate.py` | P5-006 |
| 9 | `src/loops/phases/execute.py` | P5-007 |
| 10 | `src/loops/phases/validate_audit.py` | P5-008 |
| 11 | `src/loops/phases/update_docs.py` | P5-009 |
| 12 | `src/loops/phases/setup_evidence.py` | P5-010 |
| 13 | `src/loops/guardian.py` | P5-011 |
| 14 | `src/loops/enforcer.py` | P5-012 |
| 15 | `src/loops/hash_anchor.py` | P5-013 |
| 16 | `src/loops/sub_agent.py` | P5-014 |
| 17 | `src/loops/contract.py` | P5-015 |
| 18 | `src/loops/verify.py` | P5-016 |
| 19 | `src/loops/evidence.py` | P5-017 |
| 20 | `src/loops/manager.py` | P5-018 |
| 21 | `src/loops/scheduler.py` | P5-019 |
| 22 | `src/loops/cost.py` | P5-023 |
| 23 | `systemd/guinevere-loops.service` | P5-018 |
| 24 | `systemd/guinevere-scheduler.service` | P5-019 |
| 25 | `src/discord/cmd_loop_start.py` | P5-020 |
| 26 | `src/discord/cmd_loop_stop.py` | P5-021 |
| 27 | `tests/test_e2e_loop.py` | P5-022 |
| 28 | `alembic/versions/<hash>_p5_extend_loop_instances.py` | P5-001 |

## Modified File Manifest (5 files)

| File | Step(s) | Change |
|---|---|---|
| `src/core/main.py` | P5-001 | Add `app.include_router(router)` |
| `src/memory/models.py` | P5-001 | Add columns to LoopInstances: goal, guardian_heartbeat_at, lqs_score, cost_estimate, error_count, retry_count. Make task_id nullable. |
| `src/loops/__init__.py` | P5-003 | Export state machine classes |
| `src/discord/bot.py` | P5-020/021 | Wire loop commands: import callbacks, add to core_names, remove from _STUB_PHASE |
| `PROGRESS.md` | Final | P5 0/23 → 23/23 |

## Collision Scan

| Collision | Resolution |
|---|---|
| `src/core/main.py` modified by P5-001 + P5-002 | P5-001 adds router include; P5-002 adds middleware. Sequential in Wave 1. |
| `src/discord/bot.py` modified by P5-020 + P5-021 | Single owner: Wave 3 integration agent handles both. |
| `src/memory/models.py` modified by P5-001 | Single owner: Wave 1 foundation agent. |
| `src/loops/__init__.py` modified by multiple steps | P5-003 creates initial exports. Later steps import from submodules only — no shared __init__ edits after Wave 1. |
| `PROGRESS.md` | Parent-only. Updated after all steps complete. |

## Implementation Waves

### Wave 1 — Foundation (parallel, 3 sub-agents)
- **P5-001**: FastAPI routes + DB migration + main.py router registration
- **P5-002**: JWT/API key auth middleware (depends on P5-001 for routes.py existence)
- **P5-003**: Loop state machine + __init__.py exports

**Parallelism**: P5-001 and P5-003 fire simultaneously. P5-002 fires after P5-001 completes (needs routes.py to add middleware).

### Wave 2 — Implementation (parallel, 2 groups)
**2A: Phase implementations** (P5-004 to P5-010)
- All 7 phases implemented in `src/loops/phases/`
- Depends on P5-003 (state machine)

**2B: Control systems** (P5-011 to P5-016)
- Guardian, Enforcer, Hash-anchored, Sub-agent, Contract, Verify
- Depends on P5-003 (state machine)

**Parallelism**: 2A and 2B fire simultaneously. Within 2A, phases share `phases/__init__.py` → single sub-agent. Within 2B, all independent files → single sub-agent.

### Wave 3 — Integration (parallel, 2 groups)
**3A: Services + Evidence** (P5-017, P5-018, P5-019, P5-023)
- Evidence pipeline, loop manager, scheduler, cost tracking, systemd units

**3B: Discord + E2E prep** (P5-020, P5-021)
- Discord command wiring in bot.py

**Parallelism**: 3A and 3B fire simultaneously.

### Wave 4 — E2E Test
- **P5-022**: Full 7-phase E2E test

## Per-Step Verification Scaffolds

### P5-001: FastAPI Internal API Enhancement

**Expected Files**:
- CREATE `src/core/api/routes.py`
- CREATE `alembic/versions/<hash>_p5_extend_loop_instances.py`
- MODIFY `src/core/main.py` (add router include)
- MODIFY `src/memory/models.py` (extend LoopInstances)

**Forbidden Patterns**: `as any`, `@ts-ignore`, `# type: ignore`, empty `except`, `pass` as sole handler body

**Required Commands**:
- `python -c "from src.core.api.routes import router; print(len(router.routes))"` → exit 0, prints ≥4
- `python -c "from src.memory.models import LoopInstances; print([c.name for c in LoopInstances.__table__.columns])"` → exit 0, shows goal, lqs_score columns

**Evidence**: `evidence/phase-5/STEP-P5-001/verification.md`

**Hard Rejection**: routes.py missing, router not registered in main.py, migration file missing, task_id not nullable

### P5-002: FastAPI Authentication

**Expected Files**:
- CREATE `src/core/api/auth.py`
- MODIFY `src/core/api/routes.py` (add auth dependency)

**Forbidden Patterns**: hardcoded secrets, plaintext tokens in code, `as any`, empty except

**Required Commands**:
- `python -c "from src.core.api.auth import verify_api_key; print('ok')"` → exit 0

**Evidence**: `evidence/phase-5/STEP-P5-002/verification.md`

**Hard Rejection**: auth.py missing, routes unprotected, secrets hardcoded

### P5-003: Loop State Machine

**Expected Files**:
- CREATE `src/loops/state_machine.py`
- MODIFY `src/loops/__init__.py` (export LoopPhase, LoopStateMachine)

**Forbidden Patterns**: phase count != 7+COMPLETE, `as any`, empty except

**Required Commands**:
- `python -c "from src.loops.state_machine import LoopPhase, LoopStateMachine; sm = LoopStateMachine('test', 'task'); [sm.advance() for _ in range(7)]; assert sm.is_complete(); print('PASS')"` → exit 0, prints PASS

**Evidence**: `evidence/phase-5/STEP-P5-003/verification.md`

**Hard Rejection**: state machine doesn't reach COMPLETE after 7 advances, phases not matching ADR-011

### P5-004..P5-010: 7 Phase Implementations

**Expected Files**:
- CREATE `src/loops/artifacts.py`
- CREATE `src/loops/phases/__init__.py`
- CREATE `src/loops/phases/research.py`
- CREATE `src/loops/phases/plan_delegate.py`
- CREATE `src/loops/phases/delegate.py`
- CREATE `src/loops/phases/execute.py`
- CREATE `src/loops/phases/validate_audit.py`
- CREATE `src/loops/phases/update_docs.py`
- CREATE `src/loops/phases/setup_evidence.py`

**Forbidden Patterns**: `as any`, empty except, `pass` as sole function body, missing artifact output

**Required Commands**:
- `python -c "from src.loops.phases import PHASE_REGISTRY; assert len(PHASE_REGISTRY) == 7; print('PASS')"` → exit 0
- `python -c "from src.loops.artifacts import evidence_dir, write_artifact; print('PASS')"` → exit 0

**Evidence**: `evidence/phase-5/STEP-P5-004/` through `evidence/phase-5/STEP-P5-010/`

**Hard Rejection**: any phase module missing, phase registry incomplete, artifacts module missing

### P5-011..P5-016: Control Systems

**Expected Files**:
- CREATE `src/loops/guardian.py`
- CREATE `src/loops/enforcer.py`
- CREATE `src/loops/hash_anchor.py`
- CREATE `src/loops/sub_agent.py`
- CREATE `src/loops/contract.py`
- CREATE `src/loops/verify.py`

**Forbidden Patterns**: `as any`, empty except, missing timeout defaults, missing logging

**Required Commands**:
- `python -c "from src.loops.guardian import LoopGuardian; g = LoopGuardian(); print('PASS')"` → exit 0
- `python -c "from src.loops.enforcer import TodoEnforcer; print('PASS')"` → exit 0
- `python -c "from src.loops.hash_anchor import validate_edit; print('PASS')"` → exit 0
- `python -c "from src.loops.sub_agent import SubAgentSpawner; print('PASS')"` → exit 0
- `python -c "from src.loops.contract import TaskContract; print('PASS')"` → exit 0
- `python -c "from src.loops.verify import OutputVerifier; print('PASS')"` → exit 0

**Evidence**: `evidence/phase-5/STEP-P5-011/` through `evidence/phase-5/STEP-P5-016/`

**Hard Rejection**: any module missing, guardian missing heartbeat interval, enforcer missing idle timeout

### P5-017: Evidence Pipeline

**Expected Files**:
- CREATE `src/loops/evidence.py`

**Forbidden Patterns**: empty except, raw surveillance data in artifacts, secrets in evidence

**Required Commands**:
- `python -c "from src.loops.evidence import EvidencePipeline; print('PASS')"` → exit 0

**Evidence**: `evidence/phase-5/STEP-P5-017/verification.md`

**Hard Rejection**: evidence.py missing, no artifact generation method

### P5-018: guinevere-loops.service

**Expected Files**:
- CREATE `src/loops/manager.py`
- CREATE `systemd/guinevere-loops.service`

**Forbidden Patterns**: auto-start without approval, destructive ops

**Required Commands**:
- `python -c "from src.loops.manager import LoopManager; print('PASS')"` → exit 0

**Evidence**: `evidence/phase-5/STEP-P5-018/verification.md`

**Hard Rejection**: manager.py missing, service file missing ExecStart

### P5-019: guinevere-scheduler.service

**Expected Files**:
- CREATE `src/loops/scheduler.py`
- CREATE `systemd/guinevere-scheduler.service`

**Forbidden Patterns**: cron without logging

**Required Commands**:
- `python -c "from src.loops.scheduler import LoopScheduler; print('PASS')"` → exit 0

**Evidence**: `evidence/phase-5/STEP-P5-019/verification.md`

### P5-020/021: Discord Loop Commands

**Expected Files**:
- CREATE `src/discord/cmd_loop_start.py`
- CREATE `src/discord/cmd_loop_stop.py`
- MODIFY `src/discord/bot.py` (wire commands, remove stubs)

**Forbidden Patterns**: empty except, missing is_faiz_interaction gate, missing defer

**Required Commands**:
- `python -c "from src.discord.cmd_loop_start import loop_start_callback; print('PASS')"` → exit 0
- `python -c "from src.discord.cmd_loop_stop import loop_stop_callback; print('PASS')"` → exit 0

**Evidence**: `evidence/phase-5/STEP-P5-020/` and `evidence/phase-5/STEP-P5-021/`

**Hard Rejection**: callbacks missing, not wired in bot.py, stubs not removed from _STUB_PHASE

### P5-022: E2E Test

**Expected Files**:
- CREATE `tests/test_e2e_loop.py`

**Forbidden Patterns**: test relying on external services without mock

**Required Commands**:
- `python -m pytest tests/test_e2e_loop.py -v` → exit 0

**Evidence**: `evidence/phase-5/STEP-P5-022/verification.md`

**Hard Rejection**: test file missing, tests fail, test doesn't cover full 7-phase cycle

### P5-023: Cost Tracking per Loop

**Expected Files**:
- CREATE `src/loops/cost.py`

**Forbidden Patterns**: empty except, Redis without connection error handling

**Required Commands**:
- `python -c "from src.loops.cost import LoopCostTracker; print('PASS')"` → exit 0

**Evidence**: `evidence/phase-5/STEP-P5-023/verification.md`

## Auditor Matrix

| Auditor | Steps Covered | Focus |
|---|---|---|
| Code Quality | ALL | Type safety, error handling, logging, no AI slops |
| Security | P5-002, P5-017, P5-020/021 | Auth implementation, no secret exposure, consent boundaries |
| Safety Boundary | P5-003, P5-011, P5-012 | HARD STOP integration in loop, guardian respects safe word |
| DB Migration | P5-001 | Migration correctness, backward compatibility, nullable FK |
| Discord Integration | P5-020, P5-021 | Command pattern compliance, permission gates |

## Rollback Plan

1. **DB**: `alembic downgrade e401bb5fd274` (revert to pre-P5 migration)
2. **Code**: `git checkout HEAD~1 -- src/loops/ src/core/api/ src/discord/cmd_loop_*.py` (revert P5 files)
3. **Services**: `systemctl stop guinevere-loops guinevere-scheduler`
4. **Redis**: `redis-cli -p 6380 -n 5 FLUSHDB` (clear loop cost data)

## Caveats

- Migration makes `task_id` nullable on `projects.loop_instances` — intentional for ad-hoc loops. Documented in migration.
- Discord command wiring modifies `bot.py` — single agent handles both P5-020 and P5-021 to avoid merge conflict.
- Systemd services reference `/home/guinevere/` paths — VPS-specific, not testable on Windows dev machine.
- E2E test mocks external dependencies (Redis, 9Router) — real integration test requires VPS.

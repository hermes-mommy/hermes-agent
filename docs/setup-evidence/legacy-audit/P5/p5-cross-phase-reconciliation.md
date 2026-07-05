# P5 Cross-Phase Reconciliation

**Date:** 2026-06-27
**Verdict:** CONDITIONAL PASS — 3 CRITICAL, 4 HIGH, 5 MEDIUM

---

## 1. P5 vs P19 (Multi-Project Context)

### 1.1 Agent Loop Project-Scoped Execution

**PARTIAL — plumbing exists, wiring incomplete.**

- `LoopContext` has `project_id: Optional[uuid.UUID]` (context.py line 120)
- `LoopContextBuilder` exposes `set_project_id()` (line 253)
- `audit_writer.py` carries `project_id` with `chain_version: int = 2` (P19-010)
- `metrics.py` labels Prometheus metrics with `project_id`

**BUT:** `LoopManager.start_loop()` accepts only `task`, `goal`, `priority` — NO `project_id` parameter. Manager creates LoopStateMachine without project context. Context builder's `set_project_id()` never called.

### 1.2 Project Registry Awareness

**NO direct import.** Zero matches for `from src.projects` or `ProjectRegistry` in `src/loops/`.

### 1.3 Loop Instance Scoping

**No.** `LoopManager.active_loops` is a flat `dict[str, LoopStateMachine]` keyed by loop_id, not by project. P20's `ProjectAwareCognitionRegistry` is more mature (per-project instances, concurrency caps, Redis feature flag).

**Classification:** P19 project-scoping = IMPLEMENTED_BUT_NOT_WIRED at loop manager level

---

## 2. P5 vs P20 (Living Autonomy)

### 2.1 Do They Conflict?

**No conflict — they are SEPARATE, COEXISTING systems with ZERO cross-imports.**
- `from src.life_kernel` in `src/loops/` = 0 matches
- `from src.loops` in `src/life_kernel/` = 0 matches
- Both instantiated in `src/core/main.py`: LoopManager at line 103, life_kernel at line 209+

### 2.2 Is life_kernel the Evolution of the Agent Loop?

**Yes, functionally.** P20 README: "Phase 20 is no longer a small operator-gated self-improvement phase. The active scope is the merged P5+P20 Living Autonomy Kernel."

| Aspect | P5 Agent Loop | P20 Life Kernel |
|--------|--------------|-----------------|
| Framework | Custom 7-phase state machine | LangGraph StateGraph (4-node cyclic) |
| Brain | `llm_router=None` (dormant) | HermesBrain (active) |
| Purpose | SDLC task execution | 24/7 living autonomy |
| Status | Infrastructure running, LLM-dead | Active autonomous brain |

### 2.3 Shared Code?

**Share infrastructure, not logic:**
- Both use Redis (different keys)
- Both use PostgreSQL (different tables: `projects.loop_instances` vs `life_kernel.*`)
- Both reference `HardStopHandler` (loops via guardian, life_kernel via Redis key)
- `hermes_bridge.py` superseded by life_kernel

### 2.4 Stuck-HARD-STOP Bug Impact on P5?

**No impact.** The bug was in P20's heartbeat (stale checkpoint), not in P5's HardStopHandler. Two independent HARD STOP paths:
- P5: keyword detection → HardStopHandler.is_safe → guardian cancels loops
- P20: Redis key `life_kernel:hard_stop` → heartbeat stops graph

### 2.5 Does P5 Use HermesBrain?

**NO.** `main.py` passes `llm_router=None` to LoopManager. HermesBrain is exclusively P20's.

**Classification:** P5 SDLC loop = DEPLOYED_BUT_FLAG_OFF_OR_INERT (llm_router=None makes it LLM-dead)

---

## 3. P5 vs P4 (Persona Engine)

### 3.1 Scheduler Conflict?

**NO conflict. Different schedulers for different domains.**
- P4 `ritual_scheduler.py`: APScheduler persona rituals — **DEPRECATED** (warns on import, "scheduled removal: Phase 7")
- P5 `scheduler.py`: APScheduler SDLC loop cron — active
- `guinevere-scheduler.service` runs P5's SDLC scheduler, NOT persona rituals

### 3.2 Persona Integration into Loop?

**Not directly. Via PersonaPlugin bridge (ADR-035).**
- P4 modules → PersonaPlugin → Hermes gateway → Redis DB5 state
- `src/loops/` does NOT import from `src/persona/`
- Loop does NOT read mood state

---

## 4. P5 vs ADR-035 (Hermes Migration)

### 4.1 ADR-035 Phase 5 Enhancements Status

**LIVE. Deployed and verified (2026-06-06).**
- 18 gates: 17 PASS + 1 PASS-RESCOPED (G-17 hook count)
- SOUL.md: 508 lines, finalized
- 5 Hermes skills: installed
- 5 Hermes cron jobs: registered
- PersonaPlugin: deployed to VPS

### 4.2 Did ADR-035 Change the Loop Engine?

**No.** ADR-035 changed persona/scheduling layer, not the loop engine. Loop system interaction is through `hermes_bridge.py` (superseded).

---

## 5. P5 vs P5.5 (Remediation)

### All 10 Fixes Persist

| Fix | Status | Evidence |
|-----|--------|----------|
| FIX-01 Migration chain | ✅ Present | Alembic versions in place |
| FIX-02 Indexes | ✅ Present | LoopInstances model has indexes |
| FIX-03 Redis error handling | ✅ Present | Try/except RedisError on 3 methods |
| FIX-04 Guardian kill_loop() | ✅ Present | Lines 127-148 |
| FIX-05 Guardian monitor() | ✅ Present | Outer try/except with logger.exception |
| FIX-06 Dev-key removal | ✅ Confirmed | 0 occurrences of `guinevere-dev-key` |
| FIX-07 Systemd hardening | ✅ Present | 13 directives |
| FIX-08 Wire LoopManager | ✅ Present | main.py line 103-104, routes.py line 42-44 |
| FIX-09 logger.exception | ✅ Present | manager.py except blocks |
| FIX-10 Health check | ✅ Present | routes.py health endpoint |

---

## 6. Stale Claims

### 6.1 Claims Contradicted by Later Phases

| Claim | Contradiction | Severity |
|-------|---------------|----------|
| LoopManager drives autonomous LLM work | llm_router=None — loop is LLM-dead | **HIGH** |
| HermesBridge is the bridge to Hermes | Superseded by Living Autonomy Kernel (main.py line 464) | MEDIUM |
| 7-phase SDLC loop is the autonomous brain | life_kernel is the active autonomous brain | **HIGH** |

### 6.2 Outdated Documentation

| Document | Issue |
|----------|-------|
| phase-5-skills.md | Contains `hermes plugin trigger` CLI commands not in Hermes v0.15.2 |
| batch-plan-phase-5.md | Superseded by v1.1 planner + v2 evidence |
| ritual_scheduler.py docstring | "scheduled removal: Phase 7" — Phase 7 has not removed it |

### 6.3 Code Replaced by P20

| P5 Component | P20 Replacement | Status |
|--------------|-----------------|--------|
| hermes_bridge.py | hermes_brain.py | Dead code |
| LoopManager as autonomous engine | LifeKernel graph.py | Both run, LoopManager dormant |
| LoopGuardian | HeartbeatService | Both run, separate scopes |
| P4 ritual_scheduler.py | Hermes native cron | Deprecated but not removed |

---

## Critical Findings

| ID | Finding | Severity |
|----|---------|----------|
| C-01 | LoopManager.start_loop() lacks project_id — loops are global-scoped despite P19 plumbing | CRITICAL |
| C-02 | llm_router=None makes the SDLC loop LLM-dead — not the autonomous brain described in Phase 5 | CRITICAL |
| C-03 | HermesBridge is dead code — superseded by Living Autonomy Kernel | CRITICAL |

## High Findings

| ID | Finding | Severity |
|----|---------|----------|
| H-01 | Two independent HARD STOP systems (P5 HardStopHandler vs P20 Redis key) with no coordination | HIGH |
| H-02 | Two autonomous brain systems (LoopManager + LifeKernel) coexist without coordination | HIGH |
| H-03 | src/loops/ and src/life_kernel/ have zero cross-imports — complete architectural separation | HIGH |
| H-04 | P4 ritual_scheduler deprecation target (Phase 7) not met — module remains importable | HIGH |

## Medium Findings

| ID | Finding | Severity |
|----|---------|----------|
| M-01 | SDLC scheduler timezone (Asia/Bangkok) differs from persona timezone (Asia/Jakarta) | MEDIUM |
| M-02 | P20's ProjectAwareCognitionRegistry more mature than P5's project support | MEDIUM |
| M-03 | Original batch-plan-phase-5.md stale — contains non-existent CLI commands | MEDIUM |
| M-04 | guinevere-scheduler.service runs SDLC scheduler, not persona rituals — potential confusion | MEDIUM |
| M-05 | src/loops/__init__.py exports 50+ symbols including dead code (HermesBridge) | MEDIUM |

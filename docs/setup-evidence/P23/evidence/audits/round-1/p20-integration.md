# P23 Audit Round 1 — P20 Integration
> Auditor: independent. Date: 2026-06-25.

## 1. Audit Scope

This audit evaluates P23 "Embodied Operations / Personal OS Action Layer" integration with the P20 Living Autonomy Kernel. The eight audited dimensions are:

1. **Brain path**: P23 uses `HermesBrain.think()` / `think_with_tools()` (V-004) and never raw `LLMRouter.chat`.
2. **HARD STOP single source**: P23 uses Redis key `life_kernel:hard_stop` (heartbeat.py:273) as the sole stop flag and adds no new stop path. Executors check pre-action and mid-action.
3. **Heartbeat non-interference**: P23 runs as a dedicated asyncio task, not as a heartbeat interval, preserving the 6-interval schedule and 1s HARD STOP semantics.
4. **Domain mind pattern reuse**: P23 reuses the `DeployPolicy` / `EngineerMind` / `SSHDeployBackend` pattern from `deploy_backend.py` and `engineer_mind.py`.
5. **Dashboard additive**: The P23 `_actions_section` is additive after the existing `_autonomy_section`, and new state fields are `NotRequired`.
6. **LOCKED files**: The plan lists `hermes_brain.py`, `graph.py`, `heartbeat.py` schedule, `safety_plugin`, `hard_stop_handler.py` core, and `cognition.py` guardian as FORBIDDEN to modify, with all P23 changes additive.
7. **P20 PASS HOLD**: The plan respects the P20 production pass hold before implementation.
8. **Journal + self-improve feedback**: P23 action outcomes feed `journal.py` (V-007) and `self_improve.py:ReflectionEvaluator` (V-006).

Sources reviewed:
- Plan: `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md`
- Research: `docs/setup-evidence/P23/research/p23-p20-life-kernel-action-dependency-map.md`, `p23-repo-architecture-inventory.md`
- Ground truth: `src/life_kernel/{hermes_brain.py,heartbeat.py,graph.py,state.py,dashboard.py,dashboard_writer.py,journal.py,self_improve.py,domain_minds/deploy_backend.py,domain_minds/engineer_mind.py,cognition.py}`
- P20 docs: `docs/setup-evidence/P20/plan/p5-p20-vision-lock.md`, `docs/setup-evidence/P20/README.md`

## 2. Findings

### 2.1 Brain path — PASS

- **Observation**: The P23 enterprise plan explicitly routes all autonomous reasoning through `HermesBrain.think()` / `think_with_tools()` and forbids raw `LLMRouter.chat`.
- **Evidence**:
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:281`: "Brain path (V-004): action planner + self-debug call `HermesBrain.think()`/`think_with_tools()` ... Raw `LLMRouter.chat` is FORBIDDEN."
  - `docs/setup-evidence/P23/research/p23-p20-life-kernel-action-dependency-map.md:13`: "P23 MUST use the life kernel as its brain, NOT raw LLMRouter.chat."
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:728`: hard-rejection #5 mitigated by explicit FORBIDDEN clause.
  - `src/life_kernel/hermes_brain.py:258-343` implements `think()` wrapping `AIAgent.run_conversation()`.
  - `src/life_kernel/hermes_brain.py:372-452` implements `think_with_tools()` wrapping `AIAgent.run_conversation(..., tools=tools)`.
- **Severity**: N/A (requirement met)
- **Recommendation**: Maintain the hard-rejection gate during implementation; run `grep -rn "LLMRouter.chat\|llm_router.chat" src/life_kernel/executors/` before P23-011 acceptance.

### 2.2 HARD STOP single source — PASS

- **Observation**: P23 designates Redis `life_kernel:hard_stop` as the single source of truth. No alternative stop path is introduced. P23 executors must check the flag before and during action execution.
- **Evidence**:
  - `src/life_kernel/heartbeat.py:273-282`: `_heartbeat_1s()` reads `life_kernel:hard_stop` every second.
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:366-375`: "Single source of truth: Redis key `life_kernel:hard_stop` ... P23 adds NO new stop path."
  - `docs/setup-evidence/P23/research/p23-p20-life-kernel-action-dependency-map.md:3.4`: HARD STOP propagation chain only extends P20 with an additive watcher reading the same key.
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:729`: hard-rejection #9 mitigated.
- **Severity**: N/A
- **Recommendation**: Verify in P23-004 / P23-015 tests that every executor's `execute()` calls `await redis.get("life_kernel:hard_stop")` and respects fail-closed semantics.

### 2.3 Heartbeat as dedicated asyncio task — PASS

- **Observation**: P23 action planner is explicitly a separate `asyncio.Task`, not a new heartbeat interval. The 6-interval schedule (1s, 10s, 30s, 60s, 5m, 1h) remains untouched.
- **Evidence**:
  - `src/life_kernel/heartbeat.py:114-122` defines the locked 6-interval schedule.
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:152`: "Heartbeat hook: the planner advances on a dedicated asyncio task (NOT a heartbeat interval — preserves the 6-interval schedule)."
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:283`: "P23 runs as a dedicated asyncio task, NOT a heartbeat interval."
- **Severity**: N/A
- **Recommendation**: During P23-011, ensure `action_planner.py` is started via `asyncio.create_task()` and that no new `HeartbeatInterval` is added to `heartbeat.py`.

### 2.4 Domain mind / DeployPolicy reuse — PASS

- **Observation**: P23 VPS/GitHub executors follow the policy-gated `DeployPolicy` (backup → canary → smoke → rollback) from `engineer_mind.py` and `deploy_backend.py`.
- **Evidence**:
  - `src/life_kernel/domain_minds/engineer_mind.py:31-49` defines `DeployPolicy`.
  - `src/life_kernel/domain_minds/engineer_mind.py:298-373` implements the full backup-canary-smoke-deploy/rollback orchestration.
  - `src/life_kernel/domain_minds/deploy_backend.py:56-354` defines the `DeployBackend` contract and `SSHDeployBackend` dry-run implementation.
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:284`: "Domain minds: `deploy_backend.py`/`engineer_mind.py` (DeployPolicy backup-canary-smoke-rollback) = the VPS executor template."
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:223-226`: VPS L3 gate mirrors EngineerMind flow.
- **Severity**: N/A
- **Recommendation**: Confirm in P23-007 tests that the VPS executor delegates to `EngineerMind.deploy()` rather than re-implementing the gate.

### 2.5 Dashboard additive — PASS

- **Observation**: The plan specifies adding `_actions_section` after `_autonomy_section` without touching existing sections, and new state fields are `NotRequired`.
- **Evidence**:
  - `src/life_kernel/dashboard.py:176-186` defines `_autonomy_section()`.
  - `src/life_kernel/dashboard.py:201-213` assembles `_render_full()` in order: heartbeat, state, goals, commitments, concerns, sessions, audit, autonomy.
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:286`: "additive `_actions_section` in `dashboard.py` (after `_autonomy_section`); `NotRequired` action fields on `LifeMindState`."
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:470`: "additive `_actions_section` in `DashboardRenderer` (`dashboard.py`, after `_autonomy_section`)."
- **Severity**: N/A
- **Recommendation**: During P23-017, ensure the new section is appended after `_autonymy_section(state)` and new fields in `state.py` use `NotRequired[...]`.

### 2.6 LOCKED files list — PASS

- **Observation**: The plan explicitly forbids modification of P20 locked files and confines P23 to additive new files.
- **Evidence**:
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:288`: "LOCKED P20 files (P23 MUST NOT modify): `hermes_brain.py`, `graph.py`, `heartbeat.py` (schedule), `safety_plugin`, `hard_stop_handler.py` core, `cognition.py` guardian loop."
  - `docs/setup-evidence/P23/research/p23-p20-life-kernel-action-dependency-map.md:459-478` enumerates the same locked list plus additive new files (`p23_executor_base.py`, `p23_action_planner.py`, etc.).
- **Severity**: N/A
- **Recommendation**: Enforce via code-review checklist; diff any P23 branch against `main` for changes inside the seven locked files.

### 2.7 P20 PASS HOLD — PASS

- **Observation**: The plan defers P23 implementation until the P20 Living Autonomy Kernel reaches production pass and the P19 namespace definition passes.
- **Evidence**:
  - `docs/setup-evidence/P20/README.md:3`: "Status: CONTINUATION IMPLEMENTED — DEPLOYED — SOAK/OBSERVATION IN PROGRESS — PRODUCTION PASS HOLD."
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:3` (at audit time): "ALL WAVES: IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS AND P19 DEFINITION PASS." **DOC-GATE cleanup 2026-06-25:** plan wording updated to P20 axis (operator accepted-risk waiver) + P19 namespace contract readiness.
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:741-742`: hard-rejection #19 mitigated by explicit hold.
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:704` (at audit time): "P20 Living Autonomy Kernel reaches PRODUCTION PASS (LK-017 24h clean soak) before P23 implementation begins." **DOC-GATE cleanup 2026-06-25:** updated to P20 axis satisfied by operator accepted-risk waiver + fresh preflight runtime incident check.
- **Severity**: N/A
- **Recommendation**: Do not remove the hold until P20 README status changes to "PRODUCTION PASS" and P19 README status is at least "definition pass."

### 2.8 Journal + self-improve feedback — PASS

- **Observation**: P23 action outcomes are routed to `journal.py` for reasoning audit and to `self_improve.py:ReflectionEvaluator` for improvement candidates.
- **Evidence**:
  - `src/life_kernel/journal.py:27-66` exposes `write_entry(state, reasoning, lessons_learned, confidence)`.
  - `src/life_kernel/self_improve.py:90-165` defines `ReflectionEvaluator.evaluate(state)` inspecting `errors`, `cycle_count`, `act_count`, `observations`.
  - `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md:285`: "action outcomes to `journal.py` (reasoning, V-007) to `self_improve.py:ReflectionEvaluator` (improvement candidates)."
  - `docs/setup-evidence/P23/research/p23-p20-life-kernel-action-dependency-map.md:316-324` maps action outcomes to `graph.observe_node`, `graph.reflect_node`, `journal.write_entry`, and `self_improve.py:evaluate`.
- **Severity**: N/A
- **Recommendation**: In P23-016, implement an `audit_writer.py` that writes the reasoning journal via `JournalWriter.write_entry()` and records metrics that `ReflectionEvaluator` already consumes.

## 3. Hard-Rejection Criteria Check (#4, #5, #19)

| Criterion | Plan Reference | Verdict |
|---|---|---|
| #4 — P20 is not the brain path via HermesBrain/life kernel | Plan §18, §45.4 | **PASS** — explicit HermesBrain path; hermes_brain.py is LOCKED. |
| #5 — Raw `LLMRouter.chat` used as brain path | Plan §18, §45.5, wave P23-011 Forbidden Patterns | **PASS** — raw LLMRouter is FORBIDDEN; verification command is `grep -rn "LLMRouter.chat\|llm_router.chat" src/life_kernel/executors/` → 0. |
| #19 — Plan ignores P20 PASS HOLD (at audit time) | Plan §3.2, §41, §46, §45.19 | **PASS** — implementation held until P20 axis waiver + P19 namespace contract readiness. **DOC-GATE cleanup 2026-06-25:** current gate is P20 axis satisfied by operator accepted-risk waiver (fresh runtime incident preflight before LOCKED-file edits) + P19 namespace contract readiness (P19 definition complete 2026-06-25). |

## 4. Verdict

**VERDICT: PASS**

P23's definition documents correctly integrate with P20: the brain path is HermesBrain only, HARD STOP uses the single Redis source, the planner is a separate asyncio task, domain minds are reused, dashboard/state changes are additive, locked files are explicitly forbidden, P20 PASS HOLD is respected, and action outcomes feed journal + self-improvement. No implementation code exists yet to audit, so the audit is confined to plan and research artifacts. All hard-rejection criteria for P20 integration are mitigated.

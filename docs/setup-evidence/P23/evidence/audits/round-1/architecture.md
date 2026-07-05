# P23 Audit Round 1 — Architecture
> Auditor: independent. Date: 2026-06-25. Subject: P23 plan + research.

## 1. Audit Scope

- **Plan audited:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` (1053 lines, 46 sections + 20 waves P23-001..020).
- **Research audited:** all 13 files under `docs/setup-evidence/P23/research/*.md`.
- **Ground truth verified against actual source files:**
  - `src/life_kernel/hermes_brain.py`
  - `src/life_kernel/heartbeat.py`
  - `src/life_kernel/sensor_adapters/base.py`
  - `src/life_kernel/sensors.py`
  - `src/life_kernel/graph.py`
  - `src/life_kernel/dashboard.py`
  - `src/life_kernel/state.py`
  - `src/life_kernel/cognition.py`
  - `src/mcp/auth.py`
  - `src/mcp/tools/git_tool.py`
  - `src/mcp/tools/github.py`
  - `src/mcp/tools/obscura_cdp.py`
  - `src/core/services/hard_stop_handler.py`
  - `src/core/services/llm_router.py`
  - `docs/setup-evidence/P21/plan/p21-voice-interface-enterprise-plan.md`
  - `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md`
- **Dimensions checked:** executor-layer vs sidecar, MCP tool reuse, brain path, P20 non-interference / LOCKED files, planner as dedicated asyncio task, durable queue, 20-wave coherence, dependency/parallelism/collision alignment.

## 2. Findings

### 2.1 Executor layer vs sidecar — PASS

- The plan consistently describes P23 as an **executor layer** (write-side) that is the counterpart to the existing read-side `sensor_adapters`, not a sidecar or separate service for the core brain (plan §5 architecture diagram, §10, §18).
- `BaseExecutorAdapter` is specified as a **new** base class in `src/life_kernel/executors/base.py`, parallel to `BaseSensorAdapter` in `src/life_kernel/sensor_adapters/base.py`; the plan explicitly forbids modifying `BaseSensorAdapter` (plan §10, §18, research `p23-repo-architecture-inventory.md` §3.2.3, `p23-p20-life-kernel-action-dependency-map.md` §3.10).
- Ground truth: no `src/life_kernel/executors/` package exists today (verified via glob), so the new-base claim is forward-design only; no modification of `BaseSensorAdapter` has occurred.
- **Severity: PASS.** Evidence: plan §10; research `p23-p20-life-kernel-action-dependency-map.md` §3.10, §4.2; `src/life_kernel/sensor_adapters/base.py`.

### 2.2 Thin wrappers over existing MCP tools — PASS

- The plan and research claim that executors are thin wrappers over existing MCP tools: `src/mcp/tools/{git_tool,github,obscura_cdp,shell_tool,docker_tool,postgres_tool,redis_tool,filesystem}.py` and that P23 risk tiers alias `src/mcp/auth.AuthLevel`.
- **Verified source files exist and contain the claimed primitives:**
  - `src/mcp/auth.py:42-48` defines `AuthLevel` enum with `READ_AUTO`, `WRITE_NOTIFY`, `DESTRUCTIVE_APPROVAL`, `FORBIDDEN`.
  - `src/mcp/tools/git_tool.py` defines `git_status`, `git_log`, `git_diff` (READ_AUTO), `git_commit` (WRITE_NOTIFY), `git_push_force` (DESTRUCTIVE_APPROVAL), and a runtime `FORBIDDEN` check for force-push to `main`/`master` (`git_tool.py:298-344`).
  - `src/mcp/tools/github.py` defines REST operations with `READ_AUTO` and `WRITE_NOTIFY` gates.
  - `src/mcp/tools/obscura_cdp.py` defines Obscura CDP browser tools gated by `AuthLevel`.
- The reuse claim is real, not confabulated. The research `p23-github-repo-action-research.md` §3.1 and `p23-repo-architecture-inventory.md` §3.2.8 explicitly map these tools to P23 executors.
- **Severity: PASS.** Evidence: `src/mcp/auth.py:42-48`; `src/mcp/tools/git_tool.py:1-14,222-344`; `src/mcp/tools/github.py:7-15,137-253`; `src/mcp/tools/obscura_cdp.py:117-213`; plan §14, §22.

### 2.3 Brain path = HermesBrain, raw LLMRouter.chat forbidden — PASS with caveat

- The plan states that P23 must use `HermesBrain.think()` / `think_with_tools()` as the brain path and that raw `LLMRouter.chat` is forbidden (plan §18, §45.5).
- Ground truth: `src/life_kernel/hermes_brain.py:258-343` implements `HermesBrain.think()` wrapping `AIAgent.run_conversation()`. `src/core/services/llm_router.py` exists as a low-level router, but the plan does not call it directly from P23.
- No P23 code exists yet to verify; the plan's forbidden pattern is stated clearly and the lock-list references the correct source file.
- **Caveat:** The research `p23-p20-life-kernel-action-dependency-map.md` §3.2.1-3.2.4 shows example calls to `hermes_brain.think()` that match the actual API; the plan should add an explicit audit test in P23-011 verifying no `LLMRouter.chat` imports in `src/life_kernel/executors/`.
- **Severity: PASS.** Evidence: `src/life_kernel/hermes_brain.py:258-343`; plan §18, §45.5; research `p23-p20-life-kernel-action-dependency-map.md` §3.2.

### 2.4 P20 non-interference and LOCKED files — PASS

- The plan lists explicit LOCKED P20 files that P23 must not modify: `hermes_brain.py`, `graph.py`, `heartbeat.py` (schedule), `safety_plugin` (does not exist; see caveat), `hard_stop_handler.py` core, `cognition.py` guardian (plan §18, research `p23-p20-life-kernel-action-dependency-map.md` §3.10).
- The plan states changes are additive-only: new `executors/` package, new `ExecutorRegistry`, additive dashboard section, additive `NotRequired` state fields.
- Ground truth verification:
  - `src/life_kernel/heartbeat.py` contains the 6-interval schedule (L1S..L1H) and the 1s HARD-STOP poll (`heartbeat.py:114-123,254-308`).
  - `src/life_kernel/hermes_brain.py` is the brain wrapper.
  - `src/life_kernel/graph.py` is the LangGraph StateGraph.
  - `src/life_kernel/cognition.py` is BackgroundCognition with 6 observer loops.
  - `src/core/services/hard_stop_handler.py` is the pre-LLM HARD-STOP handler.
  - `src/life_kernel/safety_plugin.py` **does not exist**; the only safety-related file is `src/core/services/hard_stop_handler.py`. This is a minor naming inconsistency in the LOCKED list.
- **Caveat:** The plan should correct `safety_plugin` to `src/core/services/hard_stop_handler.py` or document why it is listed.
- **Severity: PASS.** Evidence: plan §18; research `p23-p20-life-kernel-action-dependency-map.md` §3.10; `src/life_kernel/heartbeat.py`, `src/life_kernel/hermes_brain.py`, `src/life_kernel/graph.py`, `src/life_kernel/cognition.py`, `src/core/services/hard_stop_handler.py`.

### 2.5 Action planner as dedicated asyncio task (not heartbeat interval) — PASS

- The plan states the action planner runs as a **dedicated asyncio task**, not a heartbeat interval, preserving the 6-interval schedule (plan §8, §18; research `p23-p20-life-kernel-action-dependency-map.md` §3.3, §4.1, §4.3).
- The 6-interval schedule is verified in `src/life_kernel/heartbeat.py:114-123` and `HeartbeatInterval` enum (`L1S`, `L10S`, `L30S`, `L60S`, `L5M`, `L1H`).
- Research provides a concrete sketch of `P23ActionPlanner` as an separate asyncio task with its own 10s poll loop, not modifying heartbeat.
- **Severity: PASS.** Evidence: plan §8, §18; research `p23-p20-life-kernel-action-dependency-map.md` §4.1; `src/life_kernel/heartbeat.py:114-123`.

### 2.6 Durable queue design (PG source-of-truth + Redis BRPOPLPUSH hot queue + idempotency key) — PASS

- The plan specifies PostgreSQL `p23.action_queue` as source-of-truth with columns including `intent_hash` idempotency key, and Redis DB0 hot queue using `BRPOPLPUSH` for at-least-once delivery (plan §7, §32).
- The research `p23-rollback-idempotency-research.md` §3.2.1 provides detailed DDL with `UNIQUE (namespace, intent_hash)` equivalent, `BRPOPLPUSH` flow, visibility timeout reaper, and cancel channel.
- The plan's simplified DDL (plan §32) uses `UNIQUE (namespace, intent_hash)` directly, which is consistent with the research.
- **Severity: PASS.** Evidence: plan §7, §32; research `p23-rollback-idempotency-research.md` §3.2, §3.6.

### 2.7 20 implementation waves end-to-end — PASS with caveat

- The plan defines waves P23-001 (governance) through P23-020 (production deploy/soak/final gate). Each wave includes Expected Files, Forbidden Patterns, Required Commands, Evidence Requirements, Hard Rejection Criteria, Rollback/Re-run Safety, Parent Verification Commands, Auditor Assignment, Runtime Proof Required, and Deployment/Soak Requirement (plan §46).
- Waves are additive, with clear blockers (at audit time): P23-011..015 and P23-020 BLOCKED until P20 production-pass; P23-012 until P19 definition pass; P23-013 until P21; P23-014 until P22. **DOC-GATE cleanup 2026-06-25:** P20 axis now satisfied by operator accepted-risk waiver (fresh preflight runtime incident check before LOCKED-file edits); P23-012 gated on P19 namespace contract readiness (P19 definition complete).
- The plan correctly defers mobile to a design-seam-only stub (P23-010).
- **Caveat:** Wave P23-019 (E2E test harness) depends on ALL executors (005-010) + 015 + 016, but the dependency map (§41) shows P23-019 depends on "ALL executors (005-010) + 015,016". This is consistent.
- **Severity: PASS.** Evidence: plan §46; §41 dependency map; §42 parallelism map.

### 2.8 Dependency map, parallelism map, and collision scan alignment — PASS with caveat

- **Dependency map (§41):** linear foundation (001→002→003→004), then fan-out to executors (005-009) in parallel, then integration waves (011-014) with blockers, then HARD-STOP/safe-mode (015), audit (016), dashboard (017), metrics (018), E2E (019), deploy (020). This is coherent.
- **Parallelism map (§42):** correctly marks 005-009 and 010 as parallel after 004; 012-014 as parallel after 011; 016 parallel with 015; 017-018 parallel after 016. No shared-writer conflicts within parallel groups.
- **Collision scan (§43):** identifies shared resources (`dashboard.py`, `state.py`, `sensors.py`, `heartbeat.py`, `hermes_brain.py`, `main.py`, MCP tools, `pyproject.toml`, alembic, secrets, docs, LOCKED files) and assigns single-owner/additive rules. The collision scan is consistent with the dependency/parallelism maps.
- **Caveat:** The collision scan mentions `src/life_kernel/sensors.py` as "P23 does NOT touch (new ExecutorRegistry is parallel structure)". This is correct, but the plan should add an explicit collision-scan entry for `src/core/main.py` lifespan wire, which is listed only once under collision scan but is a critical single-owner point.
- **Severity: PASS.** Evidence: plan §41-§43.

### 2.9 P19 namespace mandatory on every action — PASS with caveat

- The plan states every P23 action carries `project_namespace` (default `'default'` pre-P19) and that action without namespace is a hard FAIL (plan §19, §45.6).
- Research `p23-p19-project-namespace-dependency-map.md` mirrors P22 namespace pattern and defines forward-compat seam.
- **Caveat (at audit time):** P19 was NOT STARTED; the namespace contract was forward-design. The plan correctly blocks P23-012 until P19 namespace contract readiness. The default `'default'` fallback is acceptable for pre-P19. **DOC-GATE cleanup 2026-06-25:** current gate is P20 axis satisfied by operator accepted-risk waiver (fresh runtime incident preflight before LOCKED-file edits) + P19 namespace contract readiness (P19 definition complete 2026-06-25).
- **Severity: PASS.** Evidence: plan §19, §45.6; research `p23-p19-project-namespace-dependency-map.md` §3, §4.

### 2.10 Mobile executor deferred gate — PASS

- Research `p23-mobile-android-action-research.md` and plan §16 / P23-010 explicitly defer mobile/Android action execution from MVP; only a design seam + stub is allowed.
- The plan's hard-rejection criterion for mobile autonomous write/capture in MVP (plan §45.7 via §16) is consistent with the research.
- **Severity: PASS.** Evidence: plan §16; research `p23-mobile-android-action-research.md` §3.4-3.5, §6-7.

### 2.11 External integration executor wraps P22 adapters — PASS with caveat

- The plan describes `ExternalExecutor` wrapping P22 adapters (calendar, GitHub projects, Notion) as action targets, reusing P22 consent/secrets (plan §17, §21; P23-014).
- P22 plan (`docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md`) defines these adapters as read-only sensors first, then write-notify actuators. The P23 design correctly treats P22 as "sensors in; P23 actions out."
- **Caveat:** P22 is definition-complete but not implemented. P23-014 is correctly blocked until P22 implementation. No runtime contract exists to verify.
- **Severity: PASS.** Evidence: plan §17, §21, §46 P23-014; `docs/setup-evidence/P22/plan/p22-life-integration-hub-plan.md` §Integration Roster, §Read/Write/Destructive Permission Tiers.

## 3. Hard-Rejection Criteria Check (architecture-relevant subset from plan §45)

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | Real executable action architecture (not just planner/log) | **PASS** | §5-17 define browser/desktop/VPS/GitHub/filesystem/mobile/external executors |
| 2 | Durable/auditable action architecture | **PASS** | §7 durable queue; §27 hash-chained audit; §28 artifacts |
| 3 | Retry/backoff/cancel/rollback state | **PASS** | §6 lifecycle; §29 rollback/idempotency; §25 HARD-STOP cancel |
| 4 | P20 is brain path via HermesBrain/life kernel | **PASS** | §18 HermesBrain wiring; §3.2.1-3.2.4 research |
| 5 | Raw `LLMRouter.chat` forbidden | **PASS** | §18 explicit FORBIDDEN; P23-011 forbidden patterns |
| 6 | P19 namespace mandatory on all actions | **PASS** | §19 mandatory `project_namespace`; P23-012 hard-reject |
| 7 | Isolation boundary for browser/desktop/VPS/GitHub/file/mobile | **PASS** | §11-17 per-executor isolation; §43 collision scan |
| 9 | HARD STOP cancels running/queued actions | **PASS** | §25 HARD-STOP model; pre+mid-action checks |
| 10 | Safe-mode/distress freezes high-risk actions | **PASS** | §24 D0-D4 freeze table; Y0 safe-mode |
| 11 | Risk tiers clear | **PASS** | §22 L1-L4 table; aliases `AuthLevel` |
| 12 | Destructive/deploy action has backup/canary/smoke/rollback | **PASS** | §13 VPS L3 gate; §29 rollback; §0.1 engineering-deployment gate |
| 13 | Production service disruption isolation proof | **PASS** | §13 Aizanta-proof; §43 collision; §37 soak Aizanta check |
| 14 | Discord dashboard proves queued/running/done/failed/rollback | **PASS** | §30 `_actions_section`; §17 dashboard |
| 15 | Tests/soak/deploy gate reaches production proof | **PASS** | §35 testing; §37 soak; §38 deploy; P23-020 |
| 16 | Waves end-to-end from first file to deploy/soak/final PASS | **PASS** | §46 waves P23-001..020 |
| 19 | Plan respects P20 PASS HOLD (at audit time) | **PASS** | §3.2 non-scope; §41 blocked on P20 axis waiver; final status hold. **DOC-GATE cleanup 2026-06-25:** current gate is P20 axis satisfied by operator accepted-risk waiver (fresh runtime incident preflight before LOCKED-file edits) + P19 namespace contract readiness (P19 definition complete 2026-06-25). |

## 4. Verdict

**PASS** — P23 Embodied Operations / Personal OS Action Layer architecture definition is coherent, grounded in existing source files, and satisfies the architecture-scope audit criteria. The executor-layer design correctly positions `BaseExecutorAdapter` as a new write-side base parallel to `BaseSensorAdapter`, wraps real existing MCP tools that expose the `AuthLevel` primitive, routes brain decisions through `HermesBrain`, preserves P20's 6-interval heartbeat via a dedicated asyncio planner task, and provides a durable PG+Redis queue with idempotency. The 20-wave dependency/parallelism/collision maps are internally consistent, and hard-rejection criteria are mitigated.

**Actionable recommendations:**
1. Correct the LOCKED-files list: replace non-existent `safety_plugin` with `src/core/services/hard_stop_handler.py`.
2. Add an explicit P23-011 parent verification command that greps `src/life_kernel/executors/` for any `LLMRouter` / `llm_router.chat` usage.
3. Document the `src/core/main.py` lifespan wire as a single-owner shared resource in the collision scan.

> Output path: `docs/setup-evidence/P23/evidence/audits/round-1/architecture.md`

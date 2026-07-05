# P23 Audit Round 1 — Action Risk Policy

> **Auditor:** Independent.  
> **Date:** 2026-06-25.  
> **Subject:** P23 "Embodied Operations / Personal OS Action Layer" — Action Risk Policy dimension.  
> **Scope:** Plan §6 lifecycle, §8 planner, §22 risk tiers, §24 safe-mode, §25 HARD STOP, §29 rollback, §46 waves P23-002/011/015; research on policy gate + rollback; ground-truth `AGENTS.md` §0.1, `src/mcp/auth.py`, `src/life_kernel/self_improve.py`, `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` §15.1.

---

## 1. Audit Scope

Evaluate whether the P23 plan/research adequately defines and justifies the action-risk policy layer against the project's own ground-truth policy and code:

1. **Risk tiers L1-L4:** Are they clear, action-shaped, and correctly aliased to `src/mcp/auth.py:AuthLevel`?  
2. **7-step policy gate:** Is it non-skippable and comprehensive?  
3. **"Faiz silent → continue" vs destructive approval:** Is the resolution sound?  
4. **Self-debug on failure:** Does failure flow through `HermesBrain.think()` + journal → fix/rollback/escalate?  
5. **Planner priority order:** Does it respect P20 vision-lock §6 priority order?  
6. **Self-modification boundary:** Is code self-improvement L3 with regression + rollback-before-promote?  
7. **L3 deploy gate:** Is backup→canary→smoke→rollback + Faiz approval required for true destructive actions?

---

## 2. Findings

### 2.1 Risk tiers L1-L4 are clear, action-shaped, and correctly aliased to `AuthLevel`

**Status:** PASS

- The plan (`p23-embodied-operations-enterprise-plan.md:22`) and research (`p23-policy-gate-risk-classification-research.md:3.2`) define L1-L4 in concrete action terms per executor surface (browser, desktop, VPS, GitHub, filesystem, mobile, external). Each tier names examples, autonomy status, gate, distress freeze, and consent scope.
- The aliasing to `src/mcp/auth.py:AuthLevel` is real and verified in code:
  - `READ_AUTO` → L1 (read/idempotent) at `src/mcp/auth.py:45`
  - `WRITE_NOTIFY` → L2 (write-notify) at `src/mcp/auth.py:46`
  - `DESTRUCTIVE_APPROVAL` → L3 (destructive/deploy-approval) at `src/mcp/auth.py:47`
  - `FORBIDDEN` → L4 (forbidden) at `src/mcp/auth.py:48`
- The decorator enforces these levels at `src/mcp/auth.py:158-251`: FORBIDDEN raises immediately, READ_AUTO passes, WRITE_NOTIFY runs + Discord notification, DESTRUCTIVE_APPROVAL waits for operator approval with a 5-minute timeout.

**Recommendation:** No change. Continue to use the existing `AuthLevel` primitive as the single source of truth for tier enforcement.

### 2.2 7-step policy gate is well-defined and non-skippable in design

**Status:** PASS with observation

- The gate is specified at `p23-policy-gate-risk-classification-research.md:3.4` and reused in the plan at `p23-embodied-operations-enterprise-plan.md:5` and `:8`:
  1. CLASSIFY RISK
  2. CHECK HARD STOP
  3. CHECK SAFE-MODE / DISTRESS
  4. CHECK CONSENT
  5. CHECK NAMESPACE
  6. EXECUTE VIA EXECUTOR
  7. AUDIT
- The plan states that every action passes it (`p23-embodied-operations-enterprise-plan.md:5`: "7-step policy gate (classify risk → ... → audit) governs every action"). It also requires executor adapters to check `life_kernel:hard_stop` pre-action and mid-action (`:10`, `:25`).
- Non-skippability is asserted in the research: "The gate is not optional and cannot be skipped by fast paths" (`p23-policy-gate-risk-classification-research.md:3.10`).

**Observation (not a finding):** Because P23 is still in planning (no implementation), non-skippability is a design commitment, not yet a runtime guarantee. The first implementation wave should include a static test that fails if any executor can be invoked without the gate.

### 2.3 Resolution of "Faiz silent → continue" vs destructive approval is sound

**Status:** PASS

- `AGENTS.md:63` (V-003) states: "If Faiz is silent, Guinevere continues. Silence is not a blocker."
- The research (`p23-policy-gate-risk-classification-research.md:3.7`) and plan (`p23-embodied-operations-enterprise-plan.md:22`) resolve this by tiering:
  - L1: autonomous, silent is not a blocker.
  - L2: autonomous + notify, silent is not a blocker.
  - L3: not autonomous; explicit Faiz approval required.
  - L4: never allowed.
- This directly satisfies `AGENTS.md:85-88` invariant that autonomous deployments pass policy gates, while `AGENTS.md:75-81` still requires explicit per-action approval for destructive ops that bypass gates.

**Recommendation:** No change.

### 2.4 Self-debug on failure routes through HermesBrain.think() + journal

**Status:** PASS with observation

- The plan (`p23-embodied-operations-enterprise-plan.md:8`) says: "action fails → `HermesBrain.think(user_message=<failure context + recalled journal entries of similar past failures>, system_prompt=<debug persona>)` → decision: `fix` / `rollback` / `escalate`".
- The same flow is described in the research (`p23-policy-gate-risk-classification-research.md:3.8`) and tied to V-007: "Audit exists for self-diagnosis and debugging, not as a default approval bottleneck."
- A concrete `RegressionGate` exists in `src/life_kernel/self_improve.py:264-363` and is used to gate promotion.

**Observation:** The plan correctly states that even after a successful fix, L3 actions still await Faiz confirmation before promotion. This preserves the hard L3 boundary.

### 2.5 Planner priority order matches P20 vision lock

**Status:** PASS

- P20 vision lock (`docs/setup-evidence/P20/plan/p5-p20-vision-lock.md:98-111`) defines the priority order:
  1. HARD STOP, consent revocation, active safety halt
  2. Keep Guinevere alive, recoverable, debuggable
  3. Protect secrets, personal data, memory integrity, audit integrity
  4. Urgent daily-life signals
  5. Finish active commitments and autonomous sessions
  6. Improve Guinevere autonomy/skills/prompts/planning/tests/runtime
  7. Advance engineering projects and external deliverables
  8. Explore, research, learn, propose new directions
- The plan (`p23-embodied-operations-enterprise-plan.md:8`) and research (`p23-policy-gate-risk-classification-research.md:3.9`) map this exact order to P23 actions and add the constraint that L3 is never scheduled without approval and L4 never scheduled.

**Recommendation:** No change.

### 2.6 Self-modification is correctly classified as L3 with regression + rollback-before-promote

**Status:** PASS

- `AGENTS.md:88` invariant 4: "All autonomous self-modifications pass regression tests before promotion."
- ADR-029 and `src/life_kernel/self_improve.py` implement a `RegressionGate` with `run_regression_tests` and `rollback`/`promote` methods (`src/life_kernel/self_improve.py:289-363`).
- The plan (`p23-embodied-operations-enterprise-plan.md:14`) states: "Self-modification (V-006, ADR-029): Guinevere improving own code = L3; MUST pass regression ... before promote; rollback-before-promote" and maps GitHub/repo actions to L3 accordingly.
- This matches the hard-rejection criterion that self-modification must be L3 and pass regression before promote.

### 2.7 L3 deploy gate requires backup→canary→smoke→rollback and Faiz approval for true destructive actions

**Status:** PASS with observation

- `AGENTS.md:67-73` and `:85-88` require engineering deployments to pass `backup → canary → smoke test → rollback` and to produce backup + rollback evidence before promotion.
- The plan (`p23-embodied-operations-enterprise-plan.md:13`) repeats this for VPS/SSH actions and adds: "Faiz approval for true destructive (`rm -rf`, `DROP`, force push)."
- The rollback research (`p23-rollback-idempotency-research.md:3.1-3.3`) provides a full state-machine, durable queue schema, and retry/backoff policy aligned with these gates.

**Observation:** The aliasing between the research tables and the actual code is strong, but the implementation of the deploy gate itself does not yet exist (P23 is in planning). The audit accepts the design; runtime verification is out of scope for this round.

---

## 3. Hard-Rejection Criteria Check (#11, #12)

| Criterion | Requirement | Verdict |
|---|---|---|
| **#11** | Risk tiers must alias real `src/mcp/auth.py:AuthLevel` (READ_AUTO→L1, WRITE_NOTIFY→L2, DESTRUCTIVE_APPROVAL→L3, FORBIDDEN→L4) | **PASS** — aliasing is real; enum values and decorator logic verified at `src/mcp/auth.py:42-48`, `:158-251`. |
| **#12** | L3 deploy gate must require backup→canary→smoke→rollback + Faiz approval for true destructive actions | **PASS** — specified in `AGENTS.md:67-88`, plan `p23-embodied-operations-enterprise-plan.md:13`, and rollback research. |

---

## 4. Verdict

**VERDICT: PASS**

The P23 plan and research present a sound, internally consistent, and ground-truth-aligned action-risk policy. L1-L4 are clear, action-shaped, and correctly aliased to the existing `AuthLevel` enum and decorator. The 7-step policy gate is comprehensive and asserted as non-skippable. The tension between "Faiz silent → continue" and "destructive needs approval" is resolved by tiered autonomy. Self-debug, planner priority order, self-modification boundaries, and the L3 deploy gate all match `AGENTS.md` invariants and existing code. The remaining work is implementation, not design.

**Output path:** `docs/setup-evidence/P23/evidence/audits/round-1/action-risk-policy.md`

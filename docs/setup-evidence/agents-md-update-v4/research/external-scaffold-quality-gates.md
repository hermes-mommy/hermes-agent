# External Scaffold & Quality Gate Patterns — Research Report

> **Date**: 2026-06-02
> **Author**: Guinevere (Librarian research)
> **Purpose**: Inform AGENTS.md v4 planner-scaffold rule with external patterns from CI/CD, agent frameworks, and verification tooling.
> **Scope**: Pre-implementation checklists, hard executable gates, evidence scaffolds, CI-style rejection criteria, audit trail practices.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Source Inventory](#2-source-inventory)
3. [Pattern 1: Fail-Closed Gate Semantics](#3-pattern-1-fail-closed-gate-semantics)
4. [Pattern 2: Quality-Gate Hierarchy (Cheap-Fast First)](#4-pattern-2-quality-gate-hierarchy-cheap-fast-first)
5. [Pattern 3: Monotonic Ratchet (Karpathy Principle)](#5-pattern-3-monotonic-ratchet-karpathy-principle)
6. [Pattern 4: Phase-State Machine with Gate-Blocked Transitions](#6-pattern-4-phase-state-machine-with-gate-blocked-transitions)
7. [Pattern 5: Acceptance Criteria as Executable Checks](#7-pattern-5-acceptance-criteria-as-executable-checks)
8. [Pattern 6: Plan-First Human-Approval Gates](#8-pattern-6-plan-first-human-approval-gates)
9. [Pattern 7: Evidence Trust Levels & Audit Chains](#9-pattern-7-evidence-trust-levels--audit-chains)
10. [Pattern 8: Blind Gates (Anti-Gaming)](#10-pattern-8-blind-gates-anti-gaming)
11. [Pattern 9: Binary Criterion Linter (No Vague Criteria)](#11-pattern-9-binary-criterion-linter-no-vague-criteria)
12. [Pattern 10: Architectural Intent Verification](#12-pattern-10-architectural-intent-verification)
13. [Pattern 11: Pre-Ship Traceability Checklist](#13-pattern-11-pre-ship-traceability-checklist)
14. [AGENTS.md v4 Translation: Candidate Wording](#14-agentsmd-v4-translation-candidate-wording)
15. [Recommendations](#15-recommendations)

---

## 1. Executive Summary

Across 17 external sources (repos, articles, toolkits), the strongest patterns converge on:

1. **Fail-closed semantics**: missing evidence = FAIL, never silent pass.
2. **Phase-state machines** with gate-blocked transitions (no self-certification).
3. **Monotonic ratchets**: quality metrics only move forward; regressions auto-block.
4. **Evidence per criterion**: every PASS/FAIL produces a recorded artifact.
5. **Binary evaluation**: no partial credit, no "mostly done."
6. **Plan-before-implement** as a hard gate (not a suggestion).
7. **Criterion linter**: vague language ("looks good," "properly") auto-rejected at creation time.
8. **Human approval gates** at defined decision points (before AND after implementation).
9. **Tamper-proof evidence chains** (hash chains, append-only logs).
10. **Gate retirement policy**: every gate must declare its failure class, latency budget, and kill condition.

These patterns directly support making the planner spec a **hard executable gate** for implementers, not just advisory guidance.

---

## 2. Source Inventory

| # | Source | Type | URL |
|---|--------|------|-----|
| S1 | botneve.com — CI/CD Deployment Gate Design | Article | https://botneve.com/devops-practices/ci-cd-deployment-gate-design/ |
| S2 | Evidence Gate (evidence-gate/evidence-gate-action) | GitHub Action | https://github.com/evidence-gate/evidence-gate-action |
| S3 | Agent Verification (DEV Community — mnemehq) | Article | https://dev.to/mnemehq/agent-verification-proving-architectural-intent-survived-an-autonomous-run-4adm |
| S4 | V3 Agent Standard (qiuranke99/v3-agent-standard) | Repo | https://github.com/qiuranke99/v3-agent-standard |
| S5 | PlanGate (s977043/PlanGate) | Repo | https://github.com/s977043/PlanGate |
| S6 | claude_harness_forge (rlpatrao) | Repo | https://github.com/rlpatrao/claude_harness_forge |
| S7 | ac-trace (DmytroHuzz) | Repo/Tool | https://github.com/DmytroHuzz/ac-trace |
| S8 | ATDD Framework (csotelo/atdd-framework) | Repo | https://github.com/csotelo/atdd-framework |
| S9 | Agent QA Toolkit (Tanyayvr) | Repo | https://github.com/Tanyayvr/agent-qa-toolkit |
| S10 | Quality Gates Skill (markus41/claude plugin) | Skill | https://github.com/markus41/claude/blob/main/plugins/project-management-plugin/skills/quality-gates/SKILL.md |
| S11 | spec-gate (Marremurten) | Repo | https://github.com/Marremurten/spec-gate |
| S12 | quality-gate-sgd (andrew-templeton) | Repo | https://github.com/andrew-templeton/quality-gate-sgd |
| S13 | AI Agent Verification Command Library (ivelly42) | Gist | https://gist.github.com/ivelly42/0f35039dbb5e455cfe36c316632f96fb |
| S14 | Pre-Ship Checklist (whoisrade/agentic-field-manual) | Template | https://github.com/whoisrade/agentic-field-manual/blob/main/00-templates/pre-ship-checklist.md |
| S15 | Decision Gate (DaRealYungBidness) | Repo | https://github.com/DaRealYungBidness/decision-gate |
| S16 | Forge (ikennaokpala) | Repo | https://github.com/ikennaokpala/forge |
| S17 | Release Readiness Playbook (DEV — beefedai) | Article | https://dev.to/beefedai/release-readiness-playbook-checklist-dashboard-3f5p |
| S18 | claude-project-foundation (schwichtgit) | Repo | https://github.com/schwichtgit/claude-project-foundation |
| S19 | AI Quality Gate V2 (dhanachavan) | Repo | https://github.com/dhanachavan/ai-quality-gate-V2 |

---

## 3. Pattern 1: Fail-Closed Gate Semantics

**Sources**: S2 (Evidence Gate), S15 (Decision Gate), S17 (Release Readiness)

### What it is

Any unhandled error, missing evidence, or unreachable service means **FAIL**. Never a silent pass. The gate is a hard blocker by default, not advisory.

### Evidence

Evidence Gate (S2):
> "The action uses fail-closed semantics: any unhandled error exits non-zero. This prevents false passes when the evaluation service is unreachable."

Decision Gate (S15):
> "If any check is false, the script exits non-zero and the decision summary will show the denial reason."

### Gate-Failure Action Matrix (S1)

| Gate Failure | Default Action | Exception Protocol |
|---|---|---|
| Static analysis fail (security) | **Hard-block merge** | Security team override with documented exception |
| Unit test fail | **Hard-block merge** | Flaky-test quarantine with tracking issue |
| Contract test fail | **Hard-block deploy** | Coordinated-change exception |
| Integration test fail (new) | **Hard-block deploy** | None — investigate |
| Smoke test fail post-deploy | **Auto-rollback** | Manual override if confirmed transient |

### AGENTS.md Translation

> **Gate default is FAIL.** Missing evidence, unreachable verification tool, or ambiguous result = gate failure. Implementers must resolve before proceeding. No silent pass, no "assume good."

---

## 4. Pattern 2: Quality-Gate Hierarchy (Cheap-Fast First)

**Sources**: S1 (botneve CI/CD Gate Design), S19 (AI Quality Gate V2)

### What it is

Gates are decomposed into a hierarchy. Cheap gates run on every commit. Expensive gates run at fewer transitions. Running every gate on every commit wastes time; skipping cheap gates means expensive gates catch issues that would have been cheap.

### Eight Gate Classes (S1)

| Gate Class | Latency | Block Severity |
|---|---|---|
| Static analysis (lint, type, SAST, secrets) | 10–120s | Hard-block on main |
| Unit tests | 30s–5m | Hard-block on main |
| Contract tests (API/schema) | 1–5m | Hard-block on deploy |
| Integration tests | 3–15m | Hard-block on deploy |
| Smoke tests (post-deploy) | 30s–2m | Auto-rollback |
| Canary verification | 5–60m | Auto-rollback if SLO breach |
| SLO burn-rate check | Continuous | Auto-rollback if multi-window burn |
| Production shadow | Hours–days | Block promotion if divergence |

### Budget Allocation (S1)

| Phase | Total Budget | Gate Allocation |
|---|---|---|
| Pre-merge (commit to merge-ready) | < 10 min | Static 2m · Unit 3m · Contract 2m |
| Merge to deploy | < 15 min | Build 5m · Integration 6m · Smoke 2m |

### Gate-Addition Restraint (S1)

> "Every new gate should specify its failure class (what it catches), its expected latency, its false-positive budget, and its retirement condition (if false-positive rate exceeds X, kill the gate)."

### AGENTS.md Translation

> **Gates run in cost-ascending order.** Static checks → unit → contract → integration. Cheap gates block early. Expensive gates block at deployment. Each gate declares: failure class, latency budget, false-positive tolerance, and retirement condition.

---

## 5. Pattern 3: Monotonic Ratchet (Karpathy Principle)

**Sources**: S6 (claude_harness_forge), S12 (quality-gate-sgd)

### What it is

Quality metrics are monotonic — they only move forward. Once coverage reaches 80%, it can never drop to 79%. Mutation score at 72% can never drop below 72%. Test count can never decrease. The ratchet means the system either fixes forward or escalates; it never silently skips.

### Evidence

claude_harness_forge (S6):
> "Named after Andrej Karpathy's principle: quality metrics must be monotonic. Coverage at 80% can never drop to 79%. Mutation score at 72% can never drop to 71%. Test count can never decrease."

quality-gate-sgd (S12):
```json
{
  "rules": {
    "floors": { "coverage.unit.branches": 70 },
    "ceilings": { "sonarqube.blocker": 0 },
    "monotonic": [
      { "direction": "up", "metrics": ["coverage.unit.branches"] },
      { "direction": "down", "metrics": ["sonarqube.bugs"] }
    ]
  }
}
```

### 12-Gate Quality Ratchet (S6)

| Gate | What It Enforces |
|---|---|
| 1. Unit tests | All tests pass |
| 2. Lint + types | Clean static analysis |
| 3. Coverage | ≥ baseline (ratcheted, never drops) |
| 4. Architecture | Import rules, layer boundaries |
| 5. Evaluator | API + browser + console verification against real running app |
| 6. Code review | Quality principles, story traceability |
| 9. Mutation testing | Tests must catch injected bugs (score ratchets) |
| 11. Spec gaming | Detects agents gaming metrics (always on, cannot disable) |
| 12. Smoke launch | App starts with real data (always on, cannot disable) |

### AGENTS.md Translation

> **Quality ratchet.** Once a metric reaches a threshold, it becomes the new floor. Coverage, test count, and security scores can never silently regress. Regressions block progression until fixed or explicitly escalated with documented rationale.

---

## 6. Pattern 4: Phase-State Machine with Gate-Blocked Transitions

**Sources**: S4 (V3 Agent Standard), S8 (ATDD Framework), S5 (PlanGate)

### What it is

Work moves through defined phases. Each phase transition is gated by verification. An agent cannot skip a stage or self-certify. The state machine is structural, not advisory.

### V3 Agent Standard (S4)

```
P0 Bootstrap ──gate──→ P1 Contract ──gate──→ P2 Planning ──gate──→ P3 Execution
                                                                        │
                                                                   ──gate──→ P4 Evaluation
                                                                        │
                                                              pass ←────┤────→ fail (→ P3, retry++)
                                                                        │
                                                                        ↓ retry > max
                                                                    ESCALATE → Human
```

> "Gates are structural constraints, not suggestions. A gate check runs verification scripts. If it fails, the transition is blocked. The agent must fix the issues and re-check."

### ATDD Framework (S8)

```
draft → ready → tests-written → in-progress → built → tested → accepted
                                                              ↑
                                              This is the only real "done"
```

> "No human approval needed between test-writing and acceptance. The spec is the contract. The Gherkin scenario is the verdict."

### PlanGate (S5)

```
Human writes PBI → AI generates plan → [C-3: Human approves]
→ AI implements (TDD) → Auto-verify (L-0, V-1…V-4)
→ PR created → [C-4: Human reviews on GitHub] → Merge
```

### AGENTS.md Translation

> **State machine is binding.** Each phase requires gate passage before transition. No phase skipping. No self-certification. Gates evaluate deterministically: same evidence → same verdict. Failed gates require fix-and-recheck, not justification.

---

## 7. Pattern 5: Acceptance Criteria as Executable Checks

**Sources**: S7 (ac-trace), S8 (ATDD Framework), S10 (Quality Gates Skill), S11 (spec-gate)

### What it is

Acceptance criteria are not prose — they are mapped to code and tests, then verified by mutating code to prove tests actually catch breakage.

### ac-trace (S7)

Maps acceptance criteria to code and tests:
```yaml
acceptance_criteria:
  - id: AC-101
    title: VIP discount at threshold
    code:
      - path: src/pricing/service.py
        symbol: calculate_discount
        lines: 10-18
        mutate: true
    tests:
      - path: tests/test_pricing.py
        cases:
          - test_vip_discount_applies_at_threshold
```

> "The tool checks whether the tests are sensitive to change, not only whether they pass on the original code. An AC is `Unkilled` when at least one mapped test never fails."

### spec-gate (S11)

Pre-implementation spec scoring on 5 determinism signals:

| Signal | Weight | What It Measures |
|---|---|---|
| Scope | ×3 | How precisely the change is described |
| File boundaries | ×2 | Whether exact file paths are listed |
| Acceptance criteria | ×2 | Whether success is testable |
| Negative space | ×2 | Whether out-of-scope items are explicit |
| Decisions resolved | ×2 | Whether technical choices are pinned |

Post-implementation diff verification:

| Signal | Weight | What It Measures |
|---|---|---|
| File accuracy | ×3 | Expected files present, no unexpected extras |
| Boundary respect | ×1 | Within file count and line limits |
| Acceptance criteria | ×3 | Each criterion verified against diff evidence |
| Scope discipline | ×1 | No scope creep beyond the contract |
| Decision adherence | ×2 | Technical decisions actually followed in code |

### AGENTS.md Translation

> **Acceptance criteria must be executable.** Each criterion maps to specific code paths and test cases. Criteria without testable verification are rejected. Mutation testing proves tests actually protect the behavior, not just pass on unchanged code.

---

## 8. Pattern 6: Plan-First Human-Approval Gates

**Sources**: S5 (PlanGate), S6 (claude_harness_forge), S18 (claude-project-foundation)

### What it is

Human approval is required at defined decision points before implementation begins. The plan is a contract, not a suggestion.

### PlanGate (S5)

| Gate | When | Decision |
|---|---|---|
| **C-3** | After plan review, before implementation | APPROVE / CONDITIONAL / REJECT |
| **C-4** | After AI implements, on GitHub PR | APPROVE / REQUEST CHANGES |

> "PlanGate prevents AI agents from writing production code until a human-approved plan, task list, and acceptance test set exist."

### claude_harness_forge (S6)

```
Phase 1: Requirements → Socratic interview → BRD         [HUMAN APPROVAL]
Phase 2: Architecture → Stack interrogation (11 rounds)   [HUMAN APPROVAL]
Phase 3: Stories → Epics + dependency graph                [HUMAN APPROVAL]
Phase 3.5: Test Planning → Test plan + traceability        [AUTO]
Phase 4: Design → UI mockups                               [HUMAN APPROVAL]
Phase 5: Initialize → State + changelog                    [AUTO]
Phases 6-9: Build → Autonomous ratcheting loop             [AUTO]
```

### claude-project-foundation (S18)

| Sub-command | Artifact |
|---|---|
| `constitution` | `.specify/memory/constitution.md` |
| `spec` | `.specify/specs/spec.md` |
| `clarify` | Updated `spec.md` (resolve ambiguities) |
| `plan` | `.specify/specs/plan.md` |
| `features` | `feature_list.json` (machine-readable) |
| `analyze` | Score report with remediation |

> "When the spec scores 80 or above, hand off to AutoForge for autonomous execution."

### AGENTS.md Translation

> **Plan-before-implement is a hard gate.** No implementation begins without an approved plan that includes: scope in/out, acceptance criteria (testable), file boundaries, technical decisions pinned, and risk assessment. Plan approval is a documented event, not implicit.

---

## 9. Pattern 7: Evidence Trust Levels & Audit Chains

**Sources**: S2 (Evidence Gate), S9 (Agent QA Toolkit), S14 (Pre-Ship Checklist), S15 (Decision Gate)

### What it is

Evidence is recorded at trust levels, from self-declaration to cryptographic hash chains that any auditor can independently verify.

### Evidence Trust Levels (S2)

| Level | Meaning |
|---|---|
| **L1** | Declaration — the pipeline claims something happened |
| **L2** | Attestation — a third party confirms the claim |
| **L3** | Verification — the claim is independently reproducible |
| **L4** | Hash Chain — SHA-256 chain that any auditor can independently verify |

### Agent QA Toolkit (S9)

Per-run evidence pack:
```text
case-<case-id>/
  artifacts/
  execution.json
  archive/retention-controls.json
  review/review-decision.json
  review/handoff-note.md
```

### Pre-Ship Checklist (S14)

> "Pick a random output from this feature. Can you reconstruct inputs, tool calls, and policy versions in under 10 minutes? If yes, ship. If no, fix."

### Decision Gate (S15)

> "The release workflow writes a JSON evidence bundle to an evidence workspace root and evaluates it via a root-relative file path... The same evidence bundle yields the same decision."

### AGENTS.md Translation

> **Evidence is recorded, not asserted.** Every gate evaluation produces a recorded artifact: command, output, exit code, timestamp. Evidence is append-only. Critical verifications use hash-chain integrity. Any evidence must be reconstructable without live systems in under 10 minutes.

---

## 10. Pattern 8: Blind Gates (Anti-Gaming)

**Sources**: S2 (Evidence Gate), S6 (claude_harness_forge), S11 (spec-gate)

### What it is

When AI generates both code and tests, traditional metrics prove nothing. Blind Gates hide pass/fail criteria from the pipeline, making it harder for AI agents to reverse-engineer or game them.

### Evidence Gate (S2)

> "Blind Gates keep evaluation criteria outside the pipeline — the AI that generated the code cannot see or game the thresholds. This is a structural approach to the gate-gaming problem in AI-driven development."

### claude_harness_forge (S6)

> **Spec gaming detection** — catches agents deleting tests to make suites pass, writing tautological assertions (`expect(true).toBe(true)`), inflating coverage with dead code. Also cannot be disabled.

### spec-gate (S11)

> "Decision verification is the key differentiator — it doesn't just check which files changed, but what the code actually does. If the spec says 'use jose lib, RS256' but the code imports jsonwebtoken with HS256, check-diff catches it."

### AGENTS.md Translation

> **Anti-gaming enforcement.** Gates verify behavioral outcomes, not just file existence or pass counts. Spec gaming (test deletion, tautological assertions, dead-code coverage padding) is detected and blocked. Decision adherence checks that code matches pinned technical choices, not just that tests pass.

---

## 11. Pattern 9: Binary Criterion Linter (No Vague Criteria)

**Sources**: S10 (Quality Gates Skill), S17 (Release Readiness)

### What it is

Acceptance criteria are linted at creation time. Vague language is rejected. Each criterion must produce a definitive PASS or FAIL; if it can't, the criterion is malformed.

### Quality Gates Skill (S10)

> "Each acceptance criterion is either PASS or FAIL. There is no partial credit, no 'mostly done,' and no subjective judgment. If a criterion cannot be evaluated with a definitive PASS or FAIL, the criterion itself is malformed and must be rewritten."

**Blocklist of forbidden phrases:**
- "looks good," "works correctly," "is properly," "is handled"
- "is improved," "is updated" (without specifics)
- "is tested" (without naming specific tests)
- "is documented" (without naming specific documents and sections)
- "as expected" (without stating the expectation)
- "no errors" (without specifying which error type or tool)
- "runs successfully" (without specifying the exact command and expected output)
- "is complete" (circular)
- "all edge cases" (without enumerating them)

### AGENTS.md Translation

> **Criterion linter.** Acceptance criteria containing vague language ("appropriate," "properly," "looks good," "as expected") are rejected at creation time. Every criterion must be evaluable as binary PASS/FAIL by a deterministic check. Malformed criteria block task creation.

---

## 12. Pattern 10: Architectural Intent Verification

**Sources**: S3 (Agent Verification — DEV article)

### What it is

Verification evaluates three categories: architectural intent (ADRs, layering, dependency policies), operational constraints (rate limits, security boundaries), and system invariants (every public endpoint has auth, no cross-service DB writes).

### Three Verification Categories (S3)

| Category | Contract | Evaluation |
|---|---|---|
| **Architectural intent** | Decision graph (ADRs, layering, patterns) | Does change respect active decisions? |
| **Operational constraints** | Envelope specification | Did run stay inside operational bounds? |
| **System invariants** | Invariant set | Did run preserve every always-true property? |

> "As agent autonomy increases, the gap between execution success and architectural correctness widens. Verification is the layer that keeps that gap measurable and closable."

> "Governance defines what must remain true. Verification proves that it did. One layer without the other is incomplete."

### AGENTS.md Translation

> **Architectural verification.** Beyond functional correctness, every implementation is verified against: (1) active ADR decisions, (2) operational envelope constraints, (3) system invariants. A change can pass all tests and still violate architectural intent — the verification gate catches this.

---

## 13. Pattern 11: Pre-Ship Traceability Checklist

**Sources**: S14 (Pre-Ship Checklist), S13 (Verification Command Library), S17 (Release Readiness)

### What it is

Structured checklists that must be completed before deployment, covering traceability, auditability, failure handling, and rollback verification.

### Pre-Ship Traceability (S14)

Every output must be explainable after the fact:
- [ ] All user actions generate a trace ID
- [ ] Inputs are versioned and logged
- [ ] Model version is recorded with each request
- [ ] State deltas are persisted (not just final state)
- [ ] Tool calls are logged with inputs and outputs
- [ ] Failures are recorded with full context
- [ ] Rollback procedure is documented

### Verification Command Library (S13)

| Check | Command | Pass Signal | Fail Signal |
|---|---|---|---|
| Git state | `git status --short` | Only intended files changed | Unexpected files changed |
| Unit tests | Project test command | Tests pass | Failures or skipped relevant tests |
| Typecheck | Project typecheck | Typecheck exits 0 | Type errors |
| Build | Project build command | Build exits 0 | Build failure |
| Secret safety | Secret scan | No secret exposed | Secret leaked |
| Rollback | Rollback command | Rollback path documented | No recovery path |

### Release Readiness Go/No-Go (S17)

**Blocking gates (must pass):**
- Unit/integration: pass rate ≥ agreed threshold
- E2E smoke: 100% green in staging and canary
- SonarQube quality gate: OK for new code (≥80% new code coverage)
- SAST/DAST: 0 unresolved critical findings
- Canary: no significant regressions for p95/p99
- Runbook: verified for specific change, rollback rehearsed

### AGENTS.md Translation

> **Pre-ship checklist is mandatory.** Before marking any step complete: (1) all changed files verified, (2) tests pass, (3) typecheck clean, (4) build succeeds, (5) no secrets exposed, (6) rollback path documented, (7) evidence artifacts recorded. Missing any item blocks completion.

---

## 14. AGENTS.md v4 Translation: Candidate Wording

Based on the 11 patterns above, here is candidate wording for a planner-scaffold rule that could be added to AGENTS.md:

### §2.11 Planner Scaffold Gate (Proposed)

```
The planner output is a hard executable gate, not advisory guidance.
No implementation step begins until the planner file passes all of the
following checks:

1. **Completeness gate (fail-closed).** The planner file must contain:
   master todo, dependency map, collision scan, file list, evidence paths,
   auditor matrix, rollback plan. Missing any section = gate failure.

2. **Determinism check.** Every implementation task must have:
   - Exact file paths to create or modify
   - Testable acceptance criteria (binary PASS/FAIL)
   - Pinned technical decisions (library, pattern, version)
   Criteria containing "appropriate," "properly," "looks good,"
   "as expected," or "works correctly" are rejected as malformed.

3. **Dependency map validation.** The dependency map must be acyclic.
   Parallel tasks must have explicit independence declaration and
   no shared writers.

4. **Collision scan.** Before implementation wave, scan for shared
   writers across tasks. Collision found = sequence or single-owner
   assignment required. No collision scan = no implementation wave.

5. **Evidence scaffold.** Each task must declare:
   - What evidence file will be produced
   - What deterministic check validates completion
   - What gate must pass before the next task begins

6. **Gate-blocked transitions.** Phase transitions require gate
   passage. Failed gates require fix-and-recheck. No self-certification.
   No silent pass.

7. **Plan approval.** The planner file is a documented approval event.
   Parent reads it fully before syncing todos. Unapproved plans
   do not generate implementation tasks.

8. **Monotonic ratchet.** Quality metrics established by the planner
   (coverage floors, security thresholds, test counts) become
   ratchet floors. Regressions block progression.
```

---

## 15. Recommendations

### High-Confidence Additions (direct external precedent)

| Recommendation | Supporting Sources | Confidence |
|---|---|---|
| Add fail-closed gate semantics to planner gate | S1, S2, S15, S17 | **High** |
| Require binary PASS/FAIL acceptance criteria with linter blocklist | S10, S11, S17 | **High** |
| Add gate-blocked phase transitions to state machine | S4, S5, S8 | **High** |
| Require evidence scaffold per task (file path + check + artifact) | S2, S9, S13, S14, S15 | **High** |
| Add monotonic ratchet for quality metrics | S6, S12 | **High** |
| Require plan approval as documented event before implementation | S5, S6, S18 | **High** |
| Add criterion linter (blocklist of vague phrases) | S10 | **High** |

### Medium-Confidence Additions (emerging patterns, optional)

| Recommendation | Supporting Sources | Confidence |
|---|---|---|
| Add gate retirement policy (latency budget + kill condition) | S1 | **Medium** |
| Add blind gates for anti-gaming (hide criteria from implementer) | S2, S6 | **Medium** |
| Add architectural intent verification beyond functional tests | S3 | **Medium** |
| Add hash-chain evidence integrity for critical gates | S2, S16 | **Medium** |
| Add spec determinism scoring (pre-implementation spec quality gate) | S11 | **Medium** |

### Optional / Future

| Recommendation | Supporting Sources | Confidence |
|---|---|---|
| Mutation testing for AC-to-test verification | S7 | **Low-Medium** (heavy tooling) |
| BFT consensus model for multi-agent gate agreement | S16 | **Low** (overkill for single-project) |
| LLM-as-judge for hallucination detection | S19 | **Low** (out of scope) |

### What NOT to Add

Based on research, the following are **not recommended** for AGENTS.md v4:

- **New tooling dependencies** — All patterns above can be implemented with file-based checks, shell scripts, and existing project tooling. No new CI platform or external service required.
- **Blind gates as default** — Useful in multi-team CI but overkill for single-project AGENTS.md. Flag as optional.
- **Full mutation testing** — Requires specialized tooling (cosmic-ray, mutmut). Reference as aspirational only.
- **Blockchain/immutable ledger** — Hash chains (SHA-256) are sufficient; no blockchain needed.

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-02 | Guinevere (Librarian) | Initial research report from 19 external sources. |

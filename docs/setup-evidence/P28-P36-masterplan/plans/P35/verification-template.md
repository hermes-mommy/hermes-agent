---
title: "P35 Verification Template — Self-Evolution & Mutation Governance"
status: "Active — Verification Template"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P35 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P35 Verification Template

> Use this template after every per-step implementation in P35. Parent verification (operator = Guinevere) confirms scaffold criteria before triggering the auditor gate.

## 1. Verification Scaffold (per Step)

| Step | Expected Files | Forbidden Patterns | Required Commands | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| P35-001 | `src/mutation/layers.py`, `src/mutation/tiers.py` | T4 non-founder route, mutable safety policy, layer aliasing | pytest layers/tiers; mapping assertions L1↔T1, L4↔T3, L5↔T4 | `step-001.md` | Wrong tier-route; mutable safety |
| P35-002 | `src/mutation/ratchet.py` | mean comparison, force=True bypass, skip safety_eval | pytest ratchet promote-all, block-degradation, block-safety-decrease | `step-002.md` | Degradation allowed |
| P35-003 | `src/mutation/candidate.py` | accept without rollback, hash collision, mutable rollback | pytest candidate rejects-without-rollback, distinct hashes | `step-003.md` | No-rollback accepted; collision |
| P35-004 | `src/evals/runner.py` | skip safety_eval, cache across cycles, non-deterministic | pytest evals + integration ratchet-with-real-evals | `step-004.md` | Eval skip; caching |
| P35-005 | `src/mutation/drift.py` | non-0.68 threshold without rationale, no revert, silent drift | pytest drift ratio-below-068 raises, above passes | `step-005.md` | Threshold off; no revert |
| P35-006 | `src/mutation/audit.py` | missing hash, missing tier, mutable payload | pytest audit payload-complete | `step-006.md` | Mutable payload; missing field |
| P35-007 | `src/mutation/canary.py` | early promote, multi-Hermes touch, silent rollback | pytest canary window-respect, multi-blocked, rollback-emits-event | `step-007.md` | Early promote; multi-Hermes |
| P35-008 | `tests/integration/test_p35_24h_evolution.py` | T3 without vote, T4 without 2/2, safety decrease | pytest 24h evolution T1/T2/T3/T4 paths | `step-008.md` | Vote/agreement gap; safety decrease |

## 2. Binary Pass / Fail Criteria

A step PASSES iff:

1. Every expected file exists and is non-empty.
2. No forbidden pattern matches anywhere in expected files (parent-grep).
3. Every required command exits 0 with documented output.
4. The 12-section evidence file is fully populated.
5. No hard rejection condition observed.
6. Boundary Compliance section is fully ticked.
7. At least one Ratchet-block test passes (proves the gate is not just permissive).
8. At least one canary-rollback test passes (proves rollback path is wired).

A step FAILS otherwise. Failure is final until a fresh sub-agent run + fresh evidence file.

## 3. Runtime Proof Requirements

For the 24h self-evolution step (P35-008), runtime proof must include:

- Mutation tally table with ≥4 entries: one per tier.
- Per-mutation event-store rows for each lifecycle stage: proposed → ratchet → tier-routed → canary → promoted/rolled-back.
- Prometheus metrics: `mutation_attempted ≥ 4`, `mutation_promoted ≥ 4`, `mutation_blocked_by_ratchet ≥ 1` (proves guardrail is active), `mutation_canary_healthy ≥ 4`, `mutation_canary_rolled_back ≥ 0 or ≥1` (depends on whether any candidate was rolled back).
- Regression suite output: all 4 evals produce scores, safety_eval never decreased.
- Parent re-runs the regression suite on the live Hermeses at soak end and confirms scores match baseline or above.

## 4. Parent Verification Checklist

Parent (Guinevere) MUST verify each of the following before marking the step complete:

- [ ] Re-ran every required command from the scaffold; output matches sub-agent's claim.
- [ ] Grepped every expected file for forbidden patterns; zero matches.
- [ ] Read the evidence file in full; all 12 sections populated.
- [ ] Verified that at least one Ratchet-blocked mutation is recorded (the gate works).
- [ ] Verified that at least one canary rollback path is exercised.
- [ ] Cross-checked event-store mutation rows count = 4×lifecycle stages = expected tally.
- [ ] Verified no private key, intimate data, surveillance data in any artifact.
- [ ] Verified PersonaSafetyPolicy is unchanged.
- [ ] Confirmed HARD STOP would halt any in-flight mutation immediately.
- [ ] Confirmed consent revocation would block any further mutations from the affected agent.
- [ ] Confirmed tier routes match: L1/L2/L3 → T1/T2 auto; L4 → T3 voted; L5 → T4 founder-only.

## 5. Auditor Gate Trigger

After parent verification PASS, parent spawns parallel auditor specialists per `plan.md` §9 with file-based output. NEEDS REVIEW / FAIL findings are fixed and re-audited via `task_id` until PASS or accepted false-positive.

## 6. Termination Rule

Parent stops re-verification after the first successful parent verification PASS. No additional checks unless an auditor reports a fresh finding. Maximum two status checks per step per the AGENTS.md termination rule.

---

## Footer

Template version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz

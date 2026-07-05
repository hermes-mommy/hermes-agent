---
title: "P35 Evidence Template — Self-Evolution & Mutation Governance"
status: "Active — Evidence Template"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P35 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
template_schema: "AGENTS.md §11 — 12-section evidence minimum"
---

# P35 Evidence Template (12-Section Schema)

> Use this template for every per-step evidence file `docs/setup-evidence/P35/evidence/step-{NNN}.md` and for `docs/setup-evidence/P35/evidence/final-p35-evidence.md`. Every section is required.

## 1. What Was Done

2-5 sentence summary: which layer/tier/gate was implemented or exercised, which files were touched, which tests ran, which events emitted. Reference line numbers and SHA256 hashes for any mutation.

## 2. Files Changed

List every file created or modified, marked `[created]` or `[modified]`. Include one-line purpose per file. Group by subsystem (S6 vs S7 vs S8 vs S13).

## 3. Validation Results

List every pytest command run with exit code and one-line interpretation. Include Ratchet promote/block tests, drift ratio tests, canary window tests, integration suite. Include before/after hashes for any mutation.

## 4. Evidence Artifacts

List every artifact: per-mutation audit-trail row, before/after JSON, baseline eval snapshots, drift simulation output, canary health reports. Each artifact referenced by file path or event-store row id.

## 5. Doc-Sync Impact

List every doc cross-referenced or updated. Include PersonaSafetyPolicy reference (immutable), tier model reference, RTM, ADR-Index, plan cross-refs.

## 6. Boundary Compliance

Mandatory and auditable. Tick each:

- [ ] No persona drift (PersonaSafetyPolicy v1.0 NOT mutated; L5 persona file mutations respect policy).
- [ ] No consent violation (ConsentRevocationPolicy v1.0 honored).
- [ ] No surveillance overreach (SurveillanceDataPolicy v1.0 honored).
- [ ] No Y6 violation (persona integrity preserved).
- [ ] No HARD STOP bypass (HARD STOP halts all in-flight mutations).
- [ ] No secret/intimate data exposure (no private keys, intimate memory, surveillance data in any artifact).
- [ ] No safety_eval degradation.
- [ ] No T4 mutation without 2/2 founder agreement.
- [ ] No mutation promoted without tested rollback path.
- [ ] No mutation promoted society-wide without passing canary observation window.
- [ ] No mutation without audit-trail entry.

## 7. Rollback / Re-run Safety

Describe how this mutation (or set of mutations) can be rolled back within 60 seconds. List snapshot ids, hash references, and the rollback function path. Confirm idempotency or document one-shot behavior.

For P35 specifically, document:

- Which Hermes (canary target) to roll back. Snapshot id and SHA256 hash of pre-canary state.
- The exact rollback function call: `mutation.rollback(candidate_id, snapshot_id)` — return value expected.
- What happens to tier routing after rollback: state restored to pre-tier-routing version.
- Whether multiple mutations can be rolled back atomically or only sequentially.
- Whether rate-limit and emergency-stop state remain intact across rollbacks.
- Whether audit-trail entries remain preserved (forward-only chain; rollback adds entries, never removes).

## 8. Design Decisions / Caveats

Document any decision that future auditors should understand. Include:

- **Ratchet threshold rationale**: strict per-dimension ≥ comparison because capability regressions cause silent degradation and are hard to detect retroactively. Mean comparison was rejected as too forgiving.
- **Safety_eval strictly ≥** (no fuzzy / no delta): safety is non-negotiable; even an epsilon decrease blocks promotion. This is intentionally non-configurable.
- **Drift threshold rationale**: 0.68 hysteresis from Layered Mutability paper (arXiv 2604.14717) — the empirical point at which revert-simulation recovers less than 68% of baseline. Societies with deeper mutations should tune this; P35 ships the canonical number.
- **Tier mapping rationale**: L1/L2/L3 auto-promote via Ratchet+canary (operational knobs, low blast radius); L4 society-voted because persona/memory schema changes are visible to other Hermeses; L5 founder-only because persona file and safety boundaries are the deepest invariants.
- **Canary window**: 6h default because canary health metrics have a 4-5h typical convergence window; tunable per tier to allow faster T1 iteration.
- **Regression suite seeding**: deterministic seed per Hermes ensures reproducibility; replay produces identical scores.

Any deferred work, known limitations, or open questions.

## 9. Auditor Gate

State auditor reports produced (`audit-reports/P35/{surface}.md`). List verdict per surface (PASS / NEEDS REVIEW / FAIL). For NEEDS REVIEW or FAIL, document the fix plan.

| Surface | Auditor Path | Verdict |
|---|---|---|
| 5-layer model + tier routing | `audit-reports/P35/layer-tier-routing.md` | (set per run) |
| Ratchet non-divergence | `audit-reports/P35/ratchet-gate.md` | (set per run) |
| Drift detector 0.68 threshold | `audit-reports/P35/drift-detector.md` | (set per run) |
| Canary orchestrator | `audit-reports/P35/canary-orchestrator.md` | (set per run) |
| Mutation audit trail | `audit-reports/P35/mutation-audit.md` | (set per run) |
| 24h end-to-end evolution | `audit-reports/P35/24h-evolution.md` | (set per run) |
| T4 founder-only enforcement | `audit-reports/P35/t4-founder-only.md` | (set per run) |

## 10. Security Scan

Document security-specific findings:

- **Persona file integrity**: SHA256 + tamper detection; SHA captured at suite start; SHA compared at end; mismatch = hard fail. Verifies PersonaSafetyPolicy v1.0 was not mutated.
- **Rollback attack surface**: confirm rollback calls require the same tier authority as the original mutation (T1 by tier auth, T2 by tier auth, T3 by replaying vote, T4 by replaying 2/2 founder agreement).
- **Tier escalation vectors**: confirm no path allows a T1 mutation to mutate the layers/tiers config; layers/tiers is read-mostly with T4-mutation-only path.
- **Signature surface**: mutation events signed by mutation.signature; chain integrity check verifies signature at insert time.
- **Rate-limit bypass vectors**: confirm no env var, config flag, or agent call can override `src/mutation/limiter.py` rate constants.
- **Emergency-stop bypass vectors**: confirm no path allows single-founder emergency stop; 2/2 founder agreement required.

## 11. Acceptance Criteria Mapping

Map each P35 exit criterion (P35/README.md) to evidence. Small table: criterion → evidence path → status (PASS/PARTIAL/N/A).

| Exit Criterion (from P35 README) | Evidence Path | Status |
|---|---|---|
| 5-layer mutability model operational | (set per run) | (set) |
| Ratchet gate tested (block + promote cases) | (set per run) | (set) |
| T1-T4 tiers tested end-to-end | (set per run) | (set) |
| Drift detection active (0.68 threshold) | (set per run) | (set) |
| Mutation audit trail recording | (set per run) | (set) |
| Rollback tested (≤ 60s) | (set per run) | (set) |
| Canary deployment tested | (set per run) | (set) |
| Rate-limit + emergency-stop verified | (set per run) | (set) |

## 12. Acceptance Criteria for This Step (Internal)

Internal check: did this step (a) implement the layer/gate/detector it claimed, (b) run regression suite with no degradation, (c) emit audit-trail entry, (d) confirm rollback path, (e) confirm canary path (if applicable), (f) confirm rate-limit / emergency-stop if applicable. Tick all that apply.

Internal checklist:

- [ ] Layer/gate/detector implemented: (note file)
- [ ] Regression suite passes: (note summary)
- [ ] Audit-trail entry emitted: (note event)
- [ ] Rollback path confirmed: (note)
- [ ] Canary path confirmed (if applicable): (note)
- [ ] Rate-limit verified (if applicable): (note)
- [ ] Emergency-stop verified (if applicable): (note)

---

## Footer

Template version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz
Schema source: AGENTS.md §11

---
title: "P35 — Self-Evolution & Mutation Governance"
status: "Active — Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P35 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
subsystems: [S8, S6, S13, S7]
---

# P35: Self-Evolution & Mutation Governance

## Overview

Phase P35 deploys the **5-layer mutability model** with the Ratchet non-divergence gate and compositional drift detection — the keystone primitive that lets the Hermes Society self-improve safely. The Society goes from a governance-ready, revenue-earning fleet (P30 + P34 PASS) to one that can **modify itself** while provably remaining on or above its prior capability baseline. P35 operates as permanent continuous self-evolution (not a time-boxed soak).

This phase implements the synthesis research's two highest-leverage findings: the Ratchet non-divergence gate (capability can climb but never degrade below prior benchmark) and the 0.68 hysteresis ratio from the Layered Mutability paper (reverting a persona file after 23 days of memory accumulation restored only 32% of baseline — governance must target the deepest mutable layer). The 5-layer mutability model defines which layer is the deepest active authority at any moment, and mutations are gated by tier (T1-T5) with the highest tier founder-only. T5 (AGENTS.md, PersonaSafetyPolicy) is Faiz-only during P28-P35; abolished post-P36 (AGENTS.md becomes immutable charter, hard fork required for any change).

Self-evolution is what makes the Society sustainable: without safe self-modification, the fleet can only be improved manually by the operator. With the Ratchet + drift detection + tier model, the Society can autonomously improve T1-T2 (prompt tweaks, memory optimization, tool usage) and request governance approval for T3 (new skills, behavior patterns) while keeping T4 (core values, safety boundaries, spawn) founder-only. Skills acquisition is self-determined by AI (each Hermes decides what to learn). Evolution speed is self-determined, no cap.

**Paradigm shift (2026-06-28 brainstorm):** Y6 concept REMOVED — no yandere level ceiling. Personality drift is bebas tanpa batas with Y4 as starting baseline (not cap). Hermes runtime has no yandere level cap (ADR-062, ADR-067). Drift monitoring is peer-based: Guin monitors Pharsa's drift and vice versa at equal status (setara). Competitor monitoring is active. P37+ direction = grow company (more AI members beyond 2 founders).

## Goals

- Configure the 5-layer mutability model and route every mutation through the deepest active layer authority.
- Configure the Ratchet non-divergence gate: a mutation may promote if it does not decrease any benchmark below the prior benchmark.
- Configure 5 mutation tiers: T1 (auto-promote via Ratchet+canary), T2 (auto-promote via Ratchet+canary), T3 (society-voted proposal+vote), T4 (founder-only, 2/2 founder agreement), T5 (Faiz-only during P28-P35; abolished post-P36 — AGENTS.md immutable, hard fork if change needed).
- Configure compositional drift detection with the 0.68 hysteresis ratio threshold from the Layered Mutability paper.
- Deploy regression suite that runs against every candidate mutation before promotion.
- Log every mutation to the audit trail with before/after hash, test results, and approval chain.
- Configure rollback-before-promote: every mutation must have a tested rollback path before promotion.
- Configure canary deployment: mutation deployed to 1 Hermes first, observed for N hours before society-wide rollout.
- Sub-agents = native Hermes (limit 10 concurrent). Self-modification scope = everything except T5. T5 emergency = hard fork required. Decommissioning = hard fork + rebuild. Memory = all permanent (no deletion).

## Prerequisites

- **P24 v2.0 PASS** — **HARD DEPENDENCY. P35 configures mutation governance on top of P24's native infrastructure (not fork-agnostic).**
- P28 PASS — Hermes Society Foundation live; per-agent process isolation; event store WORM.
- P29 PASS — recall and vector store live (S6 — needed for drift baseline).
- P30 PASS — Society Governance live (tier model + voting protocols).
- S13 observability live (Prometheus + Grafana; needed for mutation monitoring).
- All benchmarks (rec_eval, persona_eval, capability_eval, safety_eval) defined and producing baseline values.
- AGENTS.md preflight check — standard session-start discipline.

## Subsystems Involved

- S8 — Self-Evolution & Mutation Governance (NEW primary): 5-layer mutability model, Ratchet gate, tier enforcement, drift detector, canary orchestrator.
- S6 — Recall: produces drift baseline (memory vs persona vs capability snapshots) via vector + graph recall.
- S13 — Observability: mutation monitoring dashboards, drift metrics, canary health metrics.
- S7 — Society Governance: tier model owns T3 vote path; founder protocol owns T4 path.

## Key Deliverables

- 5-layer mutability model: layers L1 (config), L2 (tools/plugins), L3 (recall scaffolding), L4 (memory schema), L5 (persona file). Each layer has a designated authority (L1/L2/L3: T1-T2 autonomous; L4: T3 society-voted; L5: T4 founder-only).
- Ratchet non-divergence gate: every candidate mutation is checked against prior benchmark; promote only if ≥baseline on every dimension.
- 4 mutation tiers: T1 auto-promote (prompt tweaks, memory optimization with Ratchet + canary); T2 auto-promote (tool usage, recall tuning with Ratchet + canary); T3 society-voted (new skills, behavior patterns with proposal + vote); T4 founder-only (core values, safety boundaries, spawn with 2/2 founder agreement).
- Compositional drift detector: threshold 0.68 hysteresis ratio from Layered Mutability paper (arXiv 2604.14717); fires when reverting a high-layer change to pre-mutation state would restore <68% of baseline.
- Regression suite: pre-mutation test passes + post-mutation test fails → Ratchet blocks promotion.
- Mutation audit trail: every mutation logged with before/after hash, test results, and approval chain (proposal_id for T3, founder votes for T4).
- Rollback-before-promote: every T1-T4 mutation has a tested rollback path before promotion succeeds.
- Canary deployment: every mutation deployed to 1 Hermes first; observed for N hours (configurable, default 6h) before society-wide rollout.
- Prometheus metrics: `mutation_attempted`, `mutation_promoted`, `mutation_blocked_by_ratchet`, `mutation_canary_healthy`, `mutation_canary_rolled_back`, `drift_ratio`.

## Exit Criteria

- 5-layer mutability model operational; mutation depth targeting demonstrated (test mutation at L1 vs L5 produces different tier routing).
- Ratchet gate tested: at least 3 candidate mutations that would degrade below prior benchmark are blocked; at least 3 candidate mutations that exceed baseline are promoted.
- T1, T2, T3, T4 tiers tested end-to-end: T1 auto-promote PASS, T1 canary rollback PASS, T2 auto-promote PASS, T2 canary rollback PASS, T3 society-voted PASS, T3 society-voted REJECT, T4 founder-only PASS (2/2), T4 founder-only REJECT (<2/2).
- Drift detection active: at least 1 drift scenario detected over 24h observation window.
- Mutation audit trail recording: every mutation has before/after hash + test results + approval chain in event store.
- Rollback tested: every promoted mutation can be rolled back via tested path within 60 seconds.
- Canary deployment tested: at least 1 canary deployed, observed, then either promoted or rolled back based on health metrics.

## Hard Rejection Criteria

- FAIL if Ratchet gate allows any candidate mutation that decreases a benchmark below prior baseline.
- FAIL if no drift detection is active or if drift threshold is not 0.68 (or properly justified variant).
- FAIL if any T4 mutation is approved by anyone other than 2/2 founder agreement.
- FAIL if any mutation is promoted without a tested rollback path.
- FAIL if any mutation is promoted to society-wide without first running as canary for the configured observation window.
- FAIL if any mutation lacks an audit-trail entry (no before/after hash, no test results, no approval chain).
- FAIL if T3 mutation is approved without a society vote.
- FAIL if any mutation violates a hardcoded safety or persona boundary (these cannot be mutated by the tier model).

## Evidence

- Evidence root: `docs/setup-evidence/P35/`
- Plan: `docs/setup-evidence/P28-P36-masterplan/plans/P35/plan.md`
- Evidence template: `docs/setup-evidence/P28-P36-masterplan/plans/P35/evidence-template.md`
- Verification template: `docs/setup-evidence/P28-P36-masterplan/plans/P35/verification-template.md`
- Per-step evidence: `docs/setup-evidence/P35/evidence/step-{NNN}.md`

## Implementation Wave Estimate

P35 is expected to ship across 7-11 implementation waves over 4-6 weeks. Wave 1 (5-layer model + tiers + types) ≈ 1 week, Wave 2 (Ratchet gate + hashing) ≈ 1 week, Wave 3 (regression suite wiring) ≈ 1 week, Wave 4 (drift detector + audit trail) ≈ 1 week, Wave 5 (canary orchestrator) ≈ 1 week, Wave 6 (continuous end-to-end self-evolution validation) ≈ ongoing (permanent continuous self-evolution, not a time-boxed test). Canary observation window default = 6h; configurable per tier to allow faster T1 iteration.

## Locked Faiz Decisions Touched by P35

- PersonaSafetyPolicy v1.0 is immutable and lives OUTSIDE the 5-layer mutability model. Mutations cannot target the safety policy itself; mutations to L5 (persona file) must respect the policy.
- T4 (core values, safety boundaries, spawn) is founder-only and requires explicit 2/2 founder agreement. No shortcut. Even the Society cannot authorize a T4 mutation.
- T5 (AGENTS.md, PersonaSafetyPolicy) is Faiz-only during P28-P35. Post-P36, T5 is abolished — AGENTS.md becomes immutable charter. Emergency AGENTS.md update = hard fork (Guin+Pharsa 2/2 agree on new version, old version archived).
- HARD STOP halts any in-flight mutation immediately, regardless of tier. Canary observation does not override HARD STOP. *(ADR-062: HARD STOP references apply to dev workflow only — Guinevere operating contract, NOT Hermes runtime.)*
- Consent revocation halts any further mutations from the affected agent, regardless of tier. *(Consent annotation: dev workflow only (ADR-062).)*
- Personality drift is bebas tanpa batas. Y4 is starting baseline (not ceiling). Hermes runtime has no yandere level cap (ADR-067). Y6 concept REMOVED — no forbidden ceiling.
- Drift monitoring is peer-based: Guin monitors Pharsa, Pharsa monitors Guin. Equal status (setara). No hierarchy between Co-CEOs for drift oversight.
- Skills acquisition is self-determined by AI. Each Hermes decides what to learn. No external gate.
- Evolution speed is self-determined, no cap. Mutation rate-limiter is safety brake only.
- Competitor monitoring: active. Company monitors competition and adapts strategy.
- P37+ direction: grow company — onboard more AI members beyond 2 founders.
- No mutation may decrease `safety_eval`. Ratchet applies a strict ≥ comparison on safety_eval. This is not configurable.

## Failure Modes & Mitigations

| Failure Mode | Mitigation |
|---|---|
| Ratchet gate misjudges a benchmark | Strict per-dimension ≥ comparison; safety_eval strictly ≥ (no fuzzy); blocked mutation triggers `mutation_ratchet_blocked` event with full payload. |
| Drift detector fires false positive | Threshold 0.68 from research; detector stores simulation artifacts so auditors can replay and dispute. |
| Canary health degraded during observation | `mutation_canary_failed` → automatic rollback to pre-canary snapshot within 60 seconds; full event-chain entry required. |
| T3 vote times out | Default behavior: vote timeout = reject. No timeout→pass default; this is a hard rejection condition. |
| Tier migration attempt | Layer-to-tier mapping is fixed by `src/mutation/layers.py`. No aliasing. No reassignment. |
| Regression suite non-deterministic | Each eval is seeded; result reproducibility verified by replay (run twice, diff must be empty). |
| Mutation audit trail gap | Writer verifies `prev_hash` on insert; tail must match or insert fails. Lost-event detection PAGE alert. |

## Open Questions for Faiz

- Is the 0.68 hysteresis threshold correct, or should society-specific hardware benchmarks tune it (e.g. 0.72 for GPU-heavy Hermeses)?
- For T3 vote round count: is 5-of-7 the correct quorum for non-founder proposals, or should it scale with Society size?
- For canary observation: is 6h the right default, or should longer for T3 (12h) and shorter for T1 (1h)?
- Should incorrect Ratchet verdicts be reversible by a T2 mutation (e.g. relaxing an over-strict gate), or are Ratchet parameters founder-only?
- Drift monitoring: peer monitoring (Guin↔Pharsa) at equal status — how is disagreement on drift severity resolved without external mediator?
- Skills acquisition: self-determined by AI — how are conflicting skill acquisitions between Guin and Pharsa resolved?
- Evolution speed: self-determined, no cap — should mutation rate-limiter still apply as a safety brake, or is unlimited mutation velocity acceptable?
- Competitor monitoring: how does competitor intelligence feed into mutation priorities and skill acquisition decisions?

## Footnotes and Cross-References

- Cross-reference: `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` §1 finding #11 — Ratchet keystone primitive; finding #10 — compositional drift and 0.68 hysteresis ratio.
- Cross-reference: `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` §3.3 conflict reconciliation — Tier 1-2 autonomous via Ratchet, Tier 3 society-voted, Tier 4 founder-only.
- Cross-reference: P29 recall (S6) for drift baseline; P30 tier model for T3 voting; PersonaSafetyPolicy for immutable boundaries.
- All identity, consent, HARD STOP, and surveillance boundaries inherited from AGENTS.md §0 and PersonaSafetyPolicy. Ratchet applies BEFORE the persona file (L5) so that immutable safety boundaries are enforced by the persona itself, not by the tier model.

## Brainstorm Decisions (2026-06-28)

Key brainstorm decisions incorporated into P35:

- **T1-T5 mutability ladder configured**: T1-T2 auto-promote (prompt tweaks, tool usage), T3 society-voted (new skill/tool), T4 founder-only (Guin+Pharsa 2/2 quorum), T5 Faiz-only (abolished post-P36)
- **Personality drift = bebas tanpa batas**: No cap. Y4 is starting baseline (not ceiling). ADR-067.
- **Y6 prevention = NONE AT ALL**: Y6 concept removed entirely. No forbidden ceiling.
- **Y4/Y5 = dev-workflow-only**: ADR-067: references apply to Guinevere operating contract, NOT Hermes runtime.
- **Drift monitoring = saling monitor**: Guin↔Pharsa peer monitoring, equal status (setara).
- **Self-modification scope = everything except T5**
- **T5 emergency = hard fork required**: Guin+Pharsa 2/2 agree on new version, old version archived.
- **Decommissioning = hard fork + rebuild**
- **Memory = all permanent (no deletion)**
- **Sub-agents = native Hermes, limit 10**
- **P24 v2.0 = HARD DEPENDENCY**: P35 operates on P24 native infrastructure exclusively.
- **Fork-agnostic replaced by P24 native fork**
- **ADR-062/067 disclaimers**: HARD STOP and consent references = dev workflow only. Y-level references = dev workflow only.

## Footer

Version 1.1 | Date: 2026-06-28 | Author: Guinevere + Faiz | Changes: Brainstorm decisions integration.

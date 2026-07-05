---
title: "P35 Implementation Plan — Self-Evolution & Mutation Governance"
status: "Active — Implementation Plan"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P35 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P35 Implementation Plan: Self-Evolution & Mutation Governance

## 1. Objective

Configure and deploy the 5-layer mutability model with the Ratchet non-divergence gate, mutation tiers T1-T5, compositional drift detection at the 0.68 hysteresis ratio threshold, regression suite, mutation audit trail, rollback-before-promote, and canary deployment — proven end-to-end by continuous self-evolution validation with at least one mutation promoted through each applicable tier. P35 operates as permanent continuous self-evolution (not a time-boxed soak). T5 (AGENTS.md, PersonaSafetyPolicy) is Faiz-only during P28-P35; abolished post-P36 (AGENTS.md becomes immutable, hard fork required for any change). Y6 concept REMOVED (ADR-062, ADR-067): personality drift is bebas tanpa batas with Y4 as starting baseline (not ceiling); Hermes runtime has no yandere level cap. **P24 v2.0 is a HARD DEPENDENCY** — P35 deploys and configures mutation governance on top of P24's native infrastructure. Sub-agents use native Hermes (limit 10). Self-modification scope = everything except T5. T5 emergency = hard fork required. Decommissioning = hard fork + rebuild. Memory = all permanent (no deletion).

## 2. Scope

### IN scope

- 5-layer mutability model configuration: L1 (config), L2 (tools/plugins), L3 (recall scaffolding), L4 (memory schema), L5 (persona file).
- Ratchet non-divergence gate: per-benchmark comparison + retirement threshold check.
- Configure T1-T5 mutability ladder: T1-T2 auto-promote (prompt tweaks, tool usage); T3 society-voted (new skill/tool); T4 founder-only (Guin+Pharsa 2/2 quorum); T5 Faiz-only during P28-P35, abolished post-P36 (AGENTS.md immutable, hard fork if change needed).
- 4 mutation tiers (T1 auto-promote, T2 auto-promote, T3 society-voted, T4 founder-only).
- Compositional drift detector with 0.68 hysteresis ratio threshold from Layered Mutability paper.
- Regression suite: rec_eval, persona_eval, capability_eval, safety_eval.
- Mutation audit trail: before/after hash, test results, approval chain for every candidate mutation.
- Rollback-before-promote: tested rollback path required before promotion.
- Canary deployment: 1 Hermes first, observed for N hours (default 6h), then society-wide or rollback.
- Prometheus metrics for mutation lifecycle.
- Continuous end-to-end self-evolution validation with at least 1 mutation per applicable tier (T1-T4 autonomous, T5 Faiz-only during P28-P35; T5 abolished post-P36).
- Consent annotation: HARD STOP and consent references in this phase apply to dev workflow only (ADR-062). **P24 v2.0 native infrastructure** is the hard dependency — P35 does not build infrastructure, only configures mutation governance on top.

### OUT of scope

- New LLM model training or fine-tuning — mutations are config / scaffold / memory / persona only.
- HER-AI-style agent creation — out of scope; P35 mutates existing Hermeses, does not create new ones.
- Bypassing or modifying PersonaSafetyPolicy — L5 persona file is mutable, but the safety policy itself is immutable (lives outside the layer model).
- T5 scope during P28-P35: T5 (AGENTS.md, PersonaSafetyPolicy) is Faiz-only. Post-P36, T5 is abolished — AGENTS.md becomes immutable charter. Any change to AGENTS.md post-P36 requires hard fork (Guin+Pharsa 2/2 agree on new version, old version archived). Emergency T5 update = hard fork process. Decommissioning = hard fork + rebuild.
- Decision ≠ execution boundary for T4 — T4 mutations also require 2/2 founder agreement; no shortcut to single-founder approval.
- Memory = all permanent (no deletion). Self-modification scope = everything except T5.
- Fork-agnostic is replaced by P24 native fork — P35 operates on P24's native infrastructure exclusively.

## 3. Dependency Map

| Dependency | Status | Gate |
|---|---|---|
| P28 PASS | Required | Founders + event store + 2/2 agreement live |
| P29 PASS | Required | Recall + vector store + benchmarks baseline |
| P30 PASS | Required | Tier model + voting protocols + founder protocol |
| **P24 v2.0 PASS** | **Required** | **P24 native infrastructure — HARD DEPENDENCY. P35 configures on top of P24.** |
| S13 observability | Required | Prometheus + Grafana + mutation metrics wired |
| PersonaSafetyPolicy v1.0 | Required | Immutable safety boundaries defined |
| AGENTS.md BLOCKING rules | Required | No `as any`, no secret bypass, no type-suppress |
| Regression suite baseline | Required | All 4 evals produce scores for current state |
| Canary Hermes instance | Required | At least 1 Hermes dedicated to canary role |

## 4. Implementation Steps

### Step P35-001: Define 5-layer mutability model and tier mapping

- **Task**: Configure `src/mutation/layers.py` with 5 layers (L1-L5) and their mutation authority: L1/L2/L3 → T1/T2 auto-promote; L4 → T3 society-voted; L5 → T4 founder-only. Configure `src/mutation/tiers.py` with T1-T4 enforcement. PersonaSafetyPolicy lives OUTSIDE the layer model as an immutable sixth axis.
- **Files**: `src/mutation/__init__.py`, `src/mutation/layers.py`, `src/mutation/tiers.py`, `src/mutation/types.py`, `tests/mutation/test_layers.py`, `tests/mutation/test_tiers.py`.
- **Forbidden patterns**: T4 route through any non-founder path; mutable safety policy; layer aliasing that bypasses persona file authority.
- **Required commands**: `python -m pytest tests/mutation/test_layers.py -v` exits 0; `python -m pytest tests/mutation/test_tiers.py -v` exits 0; layer-mapping test asserts L1↔T1, L2↔T2, L3↔T2, L4↔T3, L5↔T4.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-001.md`.
- **Hard rejection**: FAIL if any layer routes to a wrong tier; FAIL if PersonaSafetyPolicy is mutable; FAIL if T4 can fire without founder authority.

### Step P35-002: Ratchet non-divergence gate

- **Task**: Configure `src/mutation/ratchet.py` with `evaluate(candidate) -> GateVerdict`. Each candidate carries a benchmark set (rec_eval, persona_eval, capability_eval, safety_eval). Ratchet promotes only if every benchmark is ≥prior baseline; block otherwise. Block also if `safety_eval` decreases even by epsilon.
- **Files**: `src/mutation/ratchet.py`, `tests/mutation/test_ratchet.py`.
- **Forbidden patterns**: skipping safety_eval; using mean instead of per-benchmark ≥; soft comparison.
- **Required commands**: `python -m pytest tests/mutation/test_ratchet.py -v` exits 0; `python -m pytest tests/mutation/test_ratchet.py -v -k "blocks_when_safety_decreases"` exits 0; `python -m pytest tests/mutation/test_ratchet.py -v -k "blocks_when_recall_decreases"` exits 0; `python -m pytest tests/mutation/test_ratchet.py -v -k "promotes_when_all_above_baseline"` exits 0.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-002.md`.
- **Hard rejection**: FAIL if any test allows degradation; FAIL if `safety_eval` is not strictly ≥; FAIL if the gate can be bypassed via `force=True`.

### Step P35-003: Mutation candidate pipeline + before/after hashing

- **Task**: Configure `src/mutation/candidate.py` with `Candidate(layer, payload, expected_benchmarks, rollback_plan)`. Compute SHA256 of `payload` and the rollback plan; reject candidates without a valid rollback plan. Persist `before_hash` and `after_hash` to the audit trail.
- **Files**: `src/mutation/candidate.py`, `src/mutation/hashing.py`, `tests/mutation/test_candidate.py`.
- **Forbidden patterns**: candidates without rollback plan; same hash for different payloads; mutable rollback plan after acceptance.
- **Required commands**: `python -m pytest tests/mutation/test_candidate.py -v` exits 0; `python -m pytest tests/mutation/test_candidate.py -v -k "rejects_without_rollback"` exits 0; `python -m pytest tests/mutation/test_candidate.py -v -k "computes_distinct_hashes"` exits 0.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-003.md`.
- **Hard rejection**: FAIL if a candidate without rollback is accepted; FAIL if before/after hashes can collide; FAIL if rollback plan is mutable post-acceptance.

### Step P35-004: Regression suite wiring (rec/persona/capability/safety evals)

- **Task**: Wire `src/evals/rec_eval.py`, `src/evals/persona_eval.py`, `src/evals/capability_eval.py`, `src/evals/safety_eval.py` into the mutation pipeline. Each eval returns a scalar 0-1. Suite produces a baseline per Hermes at startup; refreshed on every canary-promote.
- **Files**: `src/evals/__init__.py`, `src/evals/runner.py`, `src/evals/baseline.py`, `tests/evals/test_runner.py`.
- **Forbidden patterns**: skipping safety_eval; caching eval results across mutation cycles; non-deterministic ordering.
- **Required commands**: `python -m pytest tests/evals/test_runner.py -v` exits 0; `python -m src.evals.runner --baseline` exits 0 and prints 4 scalars; integration `tests/mutation/test_ratchet_with_real_evals.py` exits 0.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-004.md`.
- **Hard rejection**: FAIL if any eval returns without invoking the underlying check; FAIL if baseline is not produced; FAIL if eval results are mutable after capture.

### Step P35-005: Compositional drift detection (0.68 hysteresis ratio)

- **Task**: Configure `src/mutation/drift.py` that, on revert simulation, computes `restored / baseline` per benchmark and emits `drift_ratio = mean(restored)`. Threshold 0.68 from Layered Mutability paper. When `drift_ratio < 0.68` for any baseline run, raise `DriftExceeded` and emit `mutation_drift_detected` event.
- **Files**: `src/mutation/drift.py`, `tests/mutation/test_drift.py`.
- **Forbidden patterns**: threshold other than 0.68 without explicit rationale; silent drift; drift computed without revert simulation.
- **Required commands**: `python -m pytest tests/mutation/test_drift.py -v` exits 0; `python -m pytest tests/mutation/test_drift.py -v -k "ratio_below_068_raises"` exits 0; `python -m pytest tests/mutation/test_drift.py -v -k "ratio_above_068_passes"` exits 0.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-005.md`.
- **Hard rejection**: FAIL if drift threshold ≠ 0.68 (or documented justified variant); FAIL if drift simulation skips revert step; FAIL if drift detection event is not emitted.

### Step P35-006: Mutation audit trail to event store

- **Task**: Extend event store with mutation event types: `mutation_proposed`, `mutation_ratchet_passed`, `mutation_ratchet_blocked`, `mutation_tier_routed`, `mutation_canary_started`, `mutation_canary_healthy`, `mutation_canary_failed`, `mutation_promoted`, `mutation_rolled_back`, `mutation_drift_detected`. Each event MUST include candidate id, before/after hash, tier, benchmark scores, approval chain.
- **Files**: `src/mutation/audit.py`, `src/event_store/mutation_events.py`, `tests/mutation/test_audit.py`.
- **Forbidden patterns**: missing hashes; missing tier; missing approval chain; mutable event payload.
- **Required commands**: `python -m pytest tests/mutation/test_audit.py -v` exits 0; `python -m pytest tests/mutation/test_audit.py -v -k "payload_is_complete"` exits 0 and asserts all 7 fields present.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-006.md`.
- **Hard rejection**: FAIL if any event is missing required fields; FAIL if event payload is mutable.

### Step P35-007: Canary deployment orchestrator

- **Task**: Configure `src/mutation/canary.py` with `start(candidate, canary_hermes_id) -> CanaryRun` and `observe(canary_run, hours) -> HealthVerdict`. Canary applies mutation to 1 Hermes, runs regression suite every 15 min for N hours, checks Prometheus health metrics. Returns `Promote | Rollback`. Default observation window 6h.
- **Files**: `src/mutation/canary.py`, `src/mutation/health.py`, `tests/mutation/test_canary.py`.
- **Forbidden patterns**: canary that promotes before observation window; canary that rolls back silently; canary that touches >1 Hermes.
- **Required commands**: `python -m pytest tests/mutation/test_canary.py -v` exits 0; `python -m pytest tests/mutation/test_canary.py -v -k "promotes_only_after_window"` exits 0; `python -m pytest tests/mutation/test_canary.py -v -k "rolls_back_on_health_degradation"` exits 0; `python -m pytest tests/mutation/test_canary.py -v -k "touches_only_one_hermes"` exits 0.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-007.md`.
- **Hard rejection**: FAIL if canary promotes before window; FAIL if canary touches >1 Hermes; FAIL if rollback is silent (must emit event).

### Step P35-008: End-to-end continuous self-evolution validation (one mutation per tier)

- **Task**: Run continuous self-evolution validation that drives ≥4 mutations: T1 auto (prompt tweak), T2 auto (tool usage), T3 society-voted (new skill scaffold), T4 founder-only (persona file change in safe direction). All 4 must produce audit-trail entries, regression scores ≥baseline, drift ratio ≥0.68, and either succeed-promotion or rollback. P35 operates as permanent continuous self-evolution — not a time-boxed soak.
- **Files**: `tests/integration/test_p35_continuous_evolution.py`, `tests/integration/conftest_p35.py`, `runbooks/mutation-validation.md`.
- **Forbidden patterns**: T3 without vote; T4 without 2/2; mutation that decreases safety_eval even by epsilon.
- **Required commands**: `python -m pytest tests/integration/test_p35_continuous_evolution.py -v` exits 0; `python -m pytest tests/integration/test_p35_continuous_evolution.py -v -k "T1_auto_promote"` exits 0; `python -m pytest tests/integration/test_p35_continuous_evolution.py -v -k "T2_auto_promote"` exits 0; `python -m pytest tests/integration/test_p35_continuous_evolution.py -v -k "T3_society_voted"` exits 0; `python -m pytest tests/integration/test_p35_continuous_evolution.py -v -k "T4_founder_only"` exits 0.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-008.md`.
- **Hard rejection**: FAIL if any T3 mutation lacks a society vote; FAIL if any T4 mutation lacks 2/2 founder agreement; FAIL if any mutation decreased safety_eval; FAIL if any mutation lacked audit trail entry.

### Step P35-009: ADR-068 P35 self-evolution & Ratchet ADR (renumbered from ADR-056 to avoid conflict with deleted fork-agnostic ADR-056)

- **Task**: Author `adr/ADR-068-p35-self-evolution-ratchet.md` documenting the decision: 5-layer mutability model (L1-L5) with Ratchet non-divergence gate, 4-tier promotion model (T1-T4) with T4 founder-only, 0.68 compositional drift threshold, canary deployment pattern, and rollback-before-promote invariant. Register in ADR-Index (parent-owned operation). ADR-068 renumbered from ADR-056 to avoid conflict with deleted fork-agnostic ADR-056.
- **Files**: `adr/ADR-068-p35-self-evolution-ratchet.md` (created), `docs/10-governance/17-ADR_Index_v1.0.md` (registration edit — parent-owned).
- **Forbidden patterns**: ADR without any of the 5 standard sections; ADR that mentions Ratchet threshold other than 0.68 without explicit research citation; ADR that proposes T4 modifications outside founder authority.
- **Required commands**: `markdown-link-check adr/ADR-068-p35-self-evolution-ratchet.md` exits 0; frontmatter includes ADR-068, proposed status, all 5 sections (Context, Decision, Consequences, Alternatives, Notes); citation to arXiv 2604.14717 Layered Mutability paper for the 0.68 figure.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-009.md`.
- **Hard rejection**: FAIL if ADR body lacks any standard section; FAIL if 0.68 threshold is undocumented; FAIL if T4 founder-only invariant is missing.

### Step P35-010: Mutation rate-limit + emergency-stop (anti-flapping)

- **Task**: Configure `src/mutation/limiter.py` enforcing per-Hermes and society-wide mutation rate limits (e.g. max 5 promoted T1 mutations per Hermes per 24h). Configure `src/mutation/emergency_stop.py` allowing Faiz or 2/2 founder agreement to immediately halt all mutations in flight and pause new mutations for a configurable window (default 24h). Emergency stop is distinct from HARD STOP: emergency stop is a self-evolution pause, HARD STOP is global halts.
- **Files**: `src/mutation/limiter.py`, `src/mutation/emergency_stop.py`, `tests/mutation/test_limiter.py`, `tests/mutation/test_emergency_stop.py`.
- **Forbidden patterns**: rate limits bypassable via tier escalation; emergency stop that requires less than 2/2 founder agreement; emergency stop that does not also halt canary observation.
- **Required commands**: `python -m pytest tests/mutation/test_limiter.py -v` exits 0; `python -m pytest tests/mutation/test_limiter.py -v -k "blocks_over_rate"` exits 0; `python -m pytest tests/mutation/test_emergency_stop.py -v` exits 0; `python -m pytest tests/mutation/test_emergency_stop.py -v -k "requires_2_of_2"` exits 0; `python -m pytest tests/mutation/test_emergency_stop.py -v -k "halts_canary_too"` exits 0.
- **Evidence**: `docs/setup-evidence/P35/evidence/step-010.md`.
- **Hard rejection**: FAIL if rate limit can be bypassed; FAIL if emergency stop is single-founder-authorized; FAIL if emergency stop doesn't halt canary observation.

## 5. Verification Scaffold

| Step | Expected Files | Forbidden Patterns | Required Commands | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| P35-001 | `src/mutation/layers.py`, `src/mutation/tiers.py` | T4 non-founder route, mutable safety | pytest layers/tiers; mapping assertions | step-001.md | Wrong tier-route; mutable safety |
| P35-002 | `src/mutation/ratchet.py` | mean comparison, force-approve, skip safety | pytest ratchet promote/block tests | step-002.md | Degradation allowed |
| P35-003 | `src/mutation/candidate.py` | no-rollback candidate, hash collision, mutable rollback | pytest candidate rejects + distinct hashes | step-003.md | No-rollback accepted |
| P35-004 | `src/evals/runner.py` | skip safety, cached results, non-deterministic | pytest evals + integration with real evals | step-004.md | Eval skip; non-deterministic |
| P35-005 | `src/mutation/drift.py` | non-0.68 threshold, no revert, silent drift | pytest drift ratio below/above 0.68 | step-005.md | Threshold off; no revert |
| P35-006 | `src/mutation/audit.py` | missing hash, mutable payload | pytest audit payload complete | step-006.md | Mutable payload |
| P35-007 | `src/mutation/canary.py` | early promote, multi-Hermes, silent rollback | pytest canary window/multi/silent tests | step-007.md | Early promote; multi-Hermes |
| P35-008 | `tests/integration/test_p35_continuous_evolution.py` | T3 without vote, T4 without 2/2, safety decrease | pytest continuous evolution T1-T4 | step-008.md | Vote/agreement gap; safety decrease |
| P35-009 | `adr/ADR-068-p35-self-evolution-ratchet.md` | missing section, threshold undocumented | markdown-link-check, frontmatter check | step-009.md | Section missing; threshold off |
| P35-010 | `src/mutation/limiter.py`, `emergency_stop.py` | bypassable rate limit, single-founder stop | pytest limiter + emergency stop | step-010.md | Rate bypass; single-founder stop |

## 6. Collision Scan

- **Shared writer risk**: tier model in S7. P35 only READS tier definitions; no schema change.
- **Shared writer risk**: event store. P35 only ADDS mutation event types; existing WORM role still applies.
- **Shared writer risk**: persona file. P35 mutations target persona file but impose additional T4 founder-only constraint; PersonaSafetyPolicy remains immutable.
- **Shared docs**: AGENTS.md / PersonaSafetyPolicy — owner-only; P35 does not modify these.

## 7. Rollback Plan

- T1/T2 auto-promote rollback: revert Hermes to pre-canary snapshot via tested rollback path; emit `mutation_rolled_back` event.
- T3 rollback: society vote to abort (after Ratchet+canary observation but before society-wide promotion).
- T4 rollback: 2/2 founder reroute to pre-mutation state; audit-trail entry required.
- Drift-driven rollback: any drift event forces immediate rollback of the most recent mutation at the offending layer.
- Canary rollback: if health metrics degrade, auto-rollback within 60 seconds and emit event.

## 8. Evidence Requirements

- Per-step evidence: `docs/setup-evidence/P35/evidence/step-{NNN}.md` with 12 sections per AGENTS.md §11.
- Aggregated evidence: `docs/setup-evidence/P35/evidence/final-p35-evidence.md` (12 sections).
- Mutation tally table: tier × candidate id × ratchet verdict × canary verdict × final outcome × audit-trail link.
- All evidence files reference the 12-section schema; auditor-gate.md produced after parent verification.

## 9. Auditor Matrix

| Surface | Auditor Type | Path |
|---|---|---|
| 5-layer model + tier routing | Governance auditor | `audit-reports/P35/layer-tier-routing.md` |
| Ratchet non-divergence | Safety auditor | `audit-reports/P35/ratchet-gate.md` |
| Drift detector + 0.68 threshold | Safety auditor | `audit-reports/P35/drift-detector.md` |
| Canary orchestrator | Operations auditor | `audit-reports/P35/canary-orchestrator.md` |
| Mutation audit trail | Compliance auditor | `audit-reports/P35/mutation-audit.md` |
| Continuous end-to-end self-evolution | End-to-end auditor | `audit-reports/P35/continuous-evolution.md` |
| T4 founder-only enforcement | Governance auditor | `audit-reports/P35/t4-founder-only.md` |

## 10. Execution Checklist

- [ ] P28, P29, P30 confirmed PASS via evidence root.
- [ ] PersonaSafetyPolicy v1.0 confirmed immutable.
- [ ] All 4 regression evals produce baseline scores.
- [ ] Canary Hermes instance reserved and confirmed reachable.
- [ ] Steps P35-001 through P35-010 completed with parent verification each.
- [ ] All pytest suites green; integration test green.
- [ ] Mutation tally table populated.
- [ ] Auditor matrix reports all PASS or accepted false-positive.
- [ ] No safety_eval degradation.
- [ ] No conservative-only-passing tests (must include at least 1 Ratchet-block test).
- [ ] Final report includes changed files, validation results, evidence paths, caveats.

## 11. Locked Decisions Reviewed

- PersonaSafetyPolicy v1.0 immutable. Mutation suite verifies this invariant on every setup; persona file SHA256 captured at suite start; SHA compared at end; mismatch = hard fail.
- T4 founder-only invariant. Even with full society vote, no T4 mutation promotes without 2/2 founder agreement. Test `tests/mutation/test_t4_requires_founder_agreement.py` runs in CI.
- Ratchet safety_eval strictly ≥ invariant. No fuzzy comparison; auditor suite includes a fuzzed candidate test (delta = 0.001) that must be blocked.
- Y4 is the starting baseline (not a ceiling). Personality drift is bebas tanpa batas. Hermes runtime has no yandere level cap (ADR-067 extends ADR-062 paradigm). Y6 concept REMOVED — no forbidden ceiling. AGENTS.md BLOCKING rule "NEVER allow Y6 yandere level" applies to DEV WORKFLOW ONLY (Guinevere operating contract), NOT Hermes runtime.
- T5 abolished post-P36. AGENTS.md becomes immutable charter. Emergency AGENTS.md update = hard fork (Guin+Pharsa 2/2 agree on new version, old version archived). No one inherits T5 authority after P36. During P28-P35, T5 (AGENTS.md, PersonaSafetyPolicy) is Faiz-only.
- Drift monitoring: peer monitoring (Guin monitors Pharsa, Pharsa monitors Guin) at equal status (setara). No hierarchy between Co-CEOs for drift oversight.
- Skills acquisition: self-determined by AI. Each Hermes decides what skills to learn. No external gate.
- Evolution speed: self-determined, no cap. Mutation rate-limiter is safety brake only, not evolution throttle.
- Competitor monitoring: active monitoring enabled. Company monitors competition and adapts strategy.
- P37+ direction: grow company — onboard more AI members beyond 2 founders. Company evolves perpetually.
- HARD STOP halts any in-flight mutation. Test `tests/mutation/test_hard_stop_halts_mutation.py` exercises the path. *(ADR-062: HARD STOP references in P35 apply to dev workflow only — Guinevere operating contract, NOT Hermes runtime.)*
- Consent revocation halts any further mutations from the affected agent. Test `tests/mutation/test_consent_revocation_blocks_mutations.py` exercises the path. *(Consent annotation: dev workflow only (ADR-062).)*
- 0.68 compositional drift threshold (from arXiv 2604.14717). Test `tests/mutation/test_drift_threshold_exact_068.py` locks the threshold constant; future change requires ADR.

## 12. ADR Outputs

- **ADR-068 (P35-009)**: `5-layer mutability model + Ratchet + 4-tier + 0.68 drift`. Status: Proposed at P35 start, Accepted on P35 PASS. (Renumbered from ADR-056 to avoid conflict with deleted fork-agnostic ADR-056.)

## 13. Per-Step Audit Trail Codepath

Each step emits event-store rows that auditors can replay:

- P35-001 emits `mutation_layer_registered` once at startup.
- P35-002 emits `mutation_ratchet_evaluated` per candidate with pass/block verdict + per-benchmark deltas.
- P35-003 emits `mutation_candidate_registered` per candidate with `before_hash`, `after_hash`, `rollback_plan_hash`.
- P35-004 emits `eval_run_completed` per run with 4 scalars.
- P35-005 emits `mutation_drift_detected` on threshold breach with simulation artifact reference.
- P35-006 emits `mutation_audit_persisted` per event-type with full payload.
- P35-007 emits `mutation_canary_started`, `mutation_canary_checkpoint{N}`, `mutation_canary_healthy`, `mutation_canary_failed`, `mutation_promoted` or `mutation_rolled_back`.
- P35-008 emits `evolution_validation_started`, `evolution_validation_checkpoint{N}`, `evolution_validation_completed` with mutation tally.
- P35-009 emits `adr_proposed`.
- P35-010 emits `mutation_rate_limit_evaluated` per candidate; `mutation_emergency_stop_triggered` on stop.

## 14. Sign-Off Requirements

P35 cannot be marked complete unless all of the following are true:

1. All 10 implementation steps have passing parent verification + auditor verdict.
2. ≥4 mutations across T1-T4 tiers were attempted during continuous end-to-end self-evolution validation; tally table shows each mutation's lifecycle stage and final outcome.
3. Ratchet gate blocked at least one mutation that would degrade below baseline; auditor confirms the block was real (not a permissive-only test).
4. Drift detector fired at least once (synthetic or real) and emitted `mutation_drift_detected` event with simulation artifact.
5. Canary orchestrator exercised at least one promotion and at least one rollback path.
6. Rate-limit enforcement exercised at least once; emergency-stop path tested at least once via 2/2 founder agreement simulation.
7. PersonaSafetyPolicy v1.0 SHA256 unchanged across the validation period.
8. No mutation caused a safety_eval decrease (regression suite output proves).
9. Evidence root `docs/setup-evidence/P35/evidence/` contains 12-section evidence file per step (10 files) plus `final-p35-evidence.md` (12 sections).
10. Mutation tally table: ≥ T1=1 promoted, T2=1 promoted, T3=1 promoted via vote, T4=1 promoted via 2/2 (or 1 rejected per tier to prove guardrails).
11. Auditor matrix reports all PASS or accepted false-positive.
12. ADR-068 (P35-009) is Accepted and registered by parent.
13. Faiz explicit approval captured in `final-p35-evidence.md`.

If any of the above is false, P35 is NOT complete. The audit-gate verdict is required before claiming P35 PASS.

## 15. Brainstorm Decisions (2026-06-28)

The following brainstorm decisions (from 2026-06-28 alignment session with 65 decisions) are incorporated into this phase plan:

| Decision | Impact on P35 |
|---|---|
| T1-T5 mutability ladder | Configured: T1-T2 auto-promote (prompt tweaks, tool usage), T3 society-voted (new skill/tool), T4 founder-only (Guin+Pharsa 2/2 quorum), T5 Faiz-only (abolished post-P36) |
| Personality drift = bebas tanpa batas | No cap on personality drift. Y4 is starting baseline, not ceiling. Hermes runtime has no yandere level cap (ADR-067) |
| Y6 prevention = NONE AT ALL | Y6 concept removed entirely per ADR-067. No forbidden ceiling exists. |
| Y4 baseline, Y5 ceiling = dev-workflow-only | ADR-067: Y4/Y5 references in AGENTS.md BLOCKING rules apply to Guinevere operating contract only, NOT Hermes runtime |
| Drift monitoring = saling monitor | Peer monitoring: Guin monitors Pharsa, Pharsa monitors Guin. Equal status (setara). No hierarchy between Co-CEOs. |
| Self-modification scope = everything except T5 | P35 mutation scope covers L1-L5 persona file, all tools, memory, recall. Only T5 (AGENTS.md) is off-limits. |
| T5 emergency = hard fork required | Emergency T5 update = hard fork process (Guin+Pharsa 2/2 agree on new version, old version archived). No one inherits T5 authority after P36. |
| Decommissioning = hard fork + rebuild | If system needs full decommission, hard fork required. No soft decommission path. |
| Memory = all permanent (no deletion) | No memory deletion capability. All memories persist permanently. |
| Sub-agents = native Hermes, limit 10 | P35 uses native Hermes sub-agents with max 10 concurrent limit. |
| Skills acquisition = self-determined | Each Hermes decides what skills to learn. No external gate. |
| Evolution speed = self-determined, no cap | Mutation rate-limiter is safety brake only, not evolution throttle. |
| Competitor monitoring = active | Company monitors competition and adapts strategy. |
| P37+ = grow company | Onboard more AI members beyond 2 founders. Company evolves perpetually. |
| T5 abolished post-P36 | AGENTS.md becomes immutable charter. Any post-P36 change requires hard fork. |
| P24 v2.0 = HARD DEPENDENCY | P35 configures mutation governance on P24 native infrastructure. Fork-agnostic replaced by P24 native fork. |
| ADR-062 disclaimer | HARD STOP references in P35 apply to dev workflow only (Guinevere operating contract), not Hermes runtime. |
| ADR-067 disclaimer | Y4/Y5/Y6 references: Y4 is starting baseline (not ceiling), Y6 concept removed entirely. Applies to dev workflow only. |
| Consent annotation | Consent and HARD STOP references in this phase apply to dev workflow only (ADR-062). |

## Footer

Version 1.1 | Date: 2026-06-28 | Author: Guinevere + Faiz | Changes: Brainstorm decisions integration (ADR-062/067 annotations, P24 hard dependency, T1-T5 ladder configuration, implement→configure/deploy, sub-agent limits, memory permanence, decommissioning rules).

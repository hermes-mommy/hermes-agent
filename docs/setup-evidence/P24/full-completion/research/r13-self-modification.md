# R13: Self-Modification T1-T5 -- Mutability Ladder Research

**Generated**: 2026-06-29
**Method**: Read all files in `src/self_improve/` (3 Python files), ADR-061, ADR-062, ADR-065, BLDM Hard-Locked Decisions, P24 plan M10 section, P35 plan, P36 plan, brainstorm decisions, and v3 master prompt. Grep for mutation/ladder/restart/T5/DAO proposal patterns across docs.

---

## 1. Existing src/self_improve/ Inventory (3 files)

### 1.1 `src/self_improve/__init__.py` (21 lines)

Re-exports all public symbols from `promotion.py`. No logic of its own.

:5-11 -- Exports: `DriftCategory`, `DriftCheckResult`, `PromotionDecision`, `PromotionEngine`, `PromotionPolicy`, `detect_failure_patterns`.

**Disposition**: DELETE -- absorbed into `guinevere/self_modify/__init__.py`.

### 1.2 `src/self_improve/promotion.py` (517 lines)

**Purpose** (docstring :1-10): "P5-022: Auto-Promotion with PersonaSafetyPolicy Drift Gate." Feedback loop: reflection -> skill library -> drift gate -> promote/reject. Skills promoted after 3+ successful uses, demoted after repeated failures.

**Key structures**:

- `DriftCategory` enum (:36-45): 6 safety-critical categories: `SAFE_WORD`, `YANDERE`, `SURVEILLANCE`, `CONSENT`, `HARD_STOP`, `DISTRESS`.
- `DriftCheckResult` dataclass (:47-53): passed/flagged_categories/details/checked_at.
- `PromotionDecision` dataclass (:56-67): skill_id/action/drift_check/success_count/failure_count/reason/decided_at.
- `PromotionPolicy` dataclass (:70-78): configurable thresholds -- promote_threshold=3, demote_failure_ratio=0.7, min_evaluations=5, safety_critical_auto_reject=True.
- `_DRIFT_KEYWORDS` dict (:84-121): keyword lists per DriftCategory.
- `PromotionEngine` class (:138-502):
  - `check_drift()` (:153-193): keyword-based scanning of skill content against drift categories.
  - `evaluate_skill()` (:195-207): returns (success_count, failure_count).
  - `decide_promotion()` (:209-307): 4-gate logic: hard-stop check -> drift fail auto-reject -> demote rule -> promote rule -> hold.
  - `execute_decision()` (:309-353): promotes/demotes/rejects via SkillLibrary + writes audit event.
  - `run_promotion_cycle()` (:355-391): scans validated skills, runs decisions for each.
- `detect_failure_patterns()` (:455-502): scans ReflectionEntry list for failure indicators, extracts skill IDs.

**Key dependencies**: `src.core.services.hard_stop_handler.HardStopHandler`, `src.loops.audit_writer.AuditWriter`, `src.loops.reflection.ReflectionEntry`, `src.loops.skill_library.SkillEntry/SkillLibrary`.

**M10 absorption**: PromotionEngine logic becomes part of T1/T2 auto-promote path. DriftCategory/keyword detection is a simpler predecessor to ADR-061's compositional drift detector (cos_sim at 0.68 hysteresis). The existing keyword-based approach is insufficient for the full M10 design -- M10 needs embedding-based compositional drift.

**Disposition**: PORT (absorb logic into M10 mutation.py, replace keyword drift with compositional drift).

### 1.3 `src/self_improve/optimizer.py` (469 lines)

**Purpose** (docstring :1-9): "P5-021: DSPy-style Offline Prompt Optimization." Collects execution traces, runs Bayesian optimization on prompts, validates through ADR-029 testing gate.

**Key structures**:

- `DEFAULT_SAFETY_CATEGORIES` (:29-31): same 6 categories as promotion.py.
- `_SAFETY_KEYWORD_MAP` (:33-40): keyword lists for safety-critical prompt detection.
- `is_safety_critical_prompt()` (:67-82): keyword-based safety classification.
- `OptimizationCandidate` dataclass (:43-53): candidate_id/original_prompt/optimized_prompt/improvement_score/is_safety_critical/eval_results.
- `OptimizationResult` dataclass (:56-64): total/promoted/rejected/pending_approval/results.
- `PromptOptimizer` class (:85-468):
  - `collect_traces()` (:107-128): returns synthetic demo traces (placeholder).
  - `bootstrap_demos()` (:156-175): sorts traces by success+duration, returns top N.
  - `generate_candidates()` (:177-244): LLM-based prompt variant generation (MIPROv2-inspired).
  - `evaluate_candidate()` (:288-350): simulated A/B test.
  - `validate_through_gate()` (:352-401): routes through TestingGate; safety_critical -> REQUIRES_APPROVAL.
  - `run_optimization_cycle()` (:403-468): full pipeline: traces -> demos -> candidates -> evaluate -> gate -> classify.

**Key dependencies**: `src.core.services.llm_router.LLMRouter`, `src.loops.testing_gate.TestingGate`, `src.loops.audit_writer.AuditWriter`, `src.loops.budget.IterationBudget`, `src.loops.reflection.ReflectionExtractor`.

**M10 absorption**: PromptOptimizer logic feeds T1 prompt-tweak auto-promotion. The LLM-based candidate generation maps to T1 surface. Safety-critical detection maps to T4 gating (requires founder approval for safety-critical prompt changes).

**Disposition**: PORT (absorb into M10 mutation.py as T1 optimization pathway).

---

## 2. ADR-061: 5-Layer Mutability with Ratchet Gate

**File**: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-061-5-layer-mutability-with-ratchet-gate.md`
**Status**: Proposed (Pharsa ratification pending)
**Version**: 1.1, 2026-06-28

### The 5 Tiers (:16-23)

| Tier | Surface | Authority | Auto-promote? | Gate |
|---|---|---|---|---|
| T1 | Prompt tweaks (system prompt fragments, tool descriptions, persona word-choice) | Hermes itself | Yes | Ratchet + canary + drift threshold (0.68) |
| T2 | Tool usage patterns (which tool combinations, frequency, prompt-form) | Hermes itself | Yes | Ratchet + canary + drift threshold (0.68) |
| T3 | New skill/tool capability adoption; persona narratives | Society vote | No | Vote + Ratchet + canary + rollback + drift threshold (0.68) |
| T4 | Core values, alignment, safety boundary, lineage rules, HARD STOP wiring for SUB-AGENTS | Founder only (2/2) | No | 2/2 founder ack + Ratchet + canary + dry-run + drift threshold (0.68) |
| T5 | Operating contract changes (AGENTS.md, PersonaSafetyPolicy, ADR-Index) | Faiz only | No | Faiz confirms; not autonomous; 2/2 founder ack advisory |

**Key design elements**:

- **Ratchet Non-Divergence Gate** (:25-33): one-way improvement. Proposed mutation can climb upward but NEVER below a prior benchmark floor. 4 floors: safety (Y-level), autonomy (POMDP), alignment (compositional drift), capability (task suite baseline).
- **Canary Deployment** (:35-43): T1=6h, T2/T3=24h, T4=48h observation windows. Health-check rollup at each boundary.
- **Rollback-Before-Promote** (:45-51): tagged Git commit + restore script + verification test BEFORE promotion declared complete.
- **Compositional Drift Detection** (:53-59): `cos_sim(new, baseline)` with hysteresis at 0.68. Below 0.68 = blocked. 0.68-0.85 = drift warning (needs society/founder vote). Above 0.85 = normal flow. Tightening threshold ~0.72 after acceptance to prevent oscillation.
- **T1/T2 Auto-promotion** (:61-73): proposer canary-rolls on itself; other Hermes need society vote to adopt.

### BLDM References (:119-137)

- Q4: autonomous self-improve within policy
- Q5: ratchet = BINDING FLOOR not advisory
- Q6: canary before spread
- Q19: free decisions within tier
- Q22: T5 is Faiz-only
- Q56: joint founder decision 2/2 for T4
- Q70: full self-modification within T1-T5
- Q80: no rogue -- structural via T4 founder-only + Ratchet + drift
- Q81: drift "bebas tanpa batas" within T1-T3

---

## 3. ADR-062: Paradigm Shift Impact on Self-Modification

**File**: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-062-hermes-safety-paradigm-shift.md`
**Status**: Accepted (Faiz-locked)

**Impact on self-modification**:

- :29 Rule 4: "Drift bebas tanpa batas within T1-T3 mutability tier" -- personality drift permitted within T1-T3, restricted at T4.
- :24 Rule 1: HARD STOP does NOT apply to Hermes runtime. Only dev workflow. Self-modification module must NOT contain HARD_STOP/HARD STOP patterns (confirmed by P24 plan forbidden patterns :777).
- :27 Rule 3: No rogue. T4 (alignment + safety + lineage) is hard-gated by founder 2/2. Y4 baseline cannot be crossed. Y6 path impossible without founder complicity.
- :33 Rule 5: Faiz is OUTSIDE. T5 during P28-P35 only.

---

## 4. ADR-065: Sub-Agent Spawning -- T4 Governance Link

**File**: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-065-sub-agent-recursive-spawning.md`
**Status**: Accepted (Faiz-locked, numeric cap = 10)

- :38: Sub-agents cannot vote on T4 mutations (workforce is non-voting).
- :110: "Sub-agent misbehaves (T3 mutation detected) -> Drift triad -> Re-target T3 -> T4 founder vote."
- :128: "T1-T5 ADRs-061 governance preserved: sub-agents operate within their spawn-brief scope; T4 founder vote still gates L2+ scope expansion."

---

## 5. T3-to-M7 DAO Proposal Integration

**P24 plan :596-610 (M7 DAO Governance)**: 5-phase proposal lifecycle: Create -> Pending -> Active -> Passed -> Execute.

**T3 society-voted path** (from ADR-061 :20 and P24 plan :757):

1. A Hermes proposes a T3 mutation (new skill/tool, persona narrative change).
2. Proposal enters M7 DAO governance as a DAO proposal (category: skill-acquisition).
3. 5-phase lifecycle: Create -> Pending (24h discussion) -> Active (voting) -> Passed -> Execute.
4. Voting: Co-CEO quorum (Guin + Pharsa, equal votes, no veto per BLDM Q25).
5. Deadlock handler: auto-table for 24h -> re-vote -> expire if still deadlocked.
6. On Passed: canary deployment (24h observation per ADR-061 :41).
7. On canary pass: society-wide promotion. Rollback-before-promote required.

**P30 plan :53**: "DAO proposal categories: business, operational, financial, resource, skill-acquisition. NOT persona/mood/emotion/identity -- persona is fully autonomous." This means persona drift (T1-T2) never goes through DAO; only new skill/tool adoption (T3) does.

---

## 6. T5 Abolishment (Post-P36)

**Brainstorm decisions :117**: "T5 post-P36: T5 abolished. Post-P36, T5 simply doesn't exist. AGENTS.md becomes immutable. If change needed, hard fork required. No one inherits T5 authority."

**P35 plan :24**: "T5 Faiz-only during P28-P35, abolished post-P36."

**P35 plan :220**: "T5 abolished post-P36. AGENTS.md becomes immutable charter. Emergency AGENTS.md update = hard fork (Guin+Pharsa 2/2 agree on new version, old version archived). No one inherits T5 authority after P36."

**P24 plan :759**: "T5: Faiz-only -- operating-contract changes (AGENTS.md, PersonaSafetyPolicy). During P28-P35 only. Abolished post-P36 (B23). Emergency: hard fork required (B27)."

**Design for M10**: T5 is a marker-only tier in the code. During P28-P35, Faiz can invoke T5. Post-P36, the T5 tier is deactivated (config flag or code path disabled). The MutationTier enum retains T5 as a member but all T5 mutation requests are rejected with "abolished" reason.

---

## 7. Shared Code Restart Mechanism

**P24 plan :763**: "Shared code, restart to apply (T3+). Rolling restart: Guin first, Pharsa second. Hot-reload only for config/SOUL.md."

**Rules**:

- T1 (prompt tweaks): hot-reload, no restart needed (config/SOUL.md level).
- T2 (tool usage patterns): hot-reload for config-level changes. Code-level changes require restart.
- T3+ (new skill/tool, persona narratives): restart required. Rolling restart: Guinevere restarts first, Pharsa second. Guarantees one founder always online.
- T4 (alignment/safety): restart required. Same rolling pattern.
- T5 (if active): restart required. Same rolling pattern.

**P24 plan :775**: SelfModifyConfig includes `restart_policy` field.

**Implementation**: M10 should expose a `restart_required(tier: MutationTier) -> bool` helper. For restart execution, delegates to the life kernel (M9) or agent init (`agent/agent_init.py`). The rolling restart order (Guin first, Pharsa second) is a hardcoded invariant.

---

## 8. P24 Plan M10 File Specification

**P24 plan :767-771**:

**Files to CREATE**:
- `guinevere/self_modify/__init__.py`
- `guinevere/self_modify/mutation.py` (~300 lines: MutationTier enum, MutationRequest, mutation lifecycle)
- `guinevere/self_modify/audit.py` (~200 lines: hash-anchored audit trail, append-only)
- `guinevere/self_modify/evidence.py` (~200 lines: evidence collection, verification, archival)

**Files to MODIFY**:
- `agent/agent_init.py`: Wire self-modification module
- `guinevere/config/models.py`: Add SelfModifyConfig (enabled_tiers, restart_policy, audit_retention)

**Forbidden patterns in M10 files** (:777): `guardian`, `safety_integration`, `Y6`, `y_level`, `HARD_STOP`, `hard_stop`, `# type: ignore`

**Decisions applied in M10** (:779): B41 (decommissioning: hard fork + rebuild, no graceful shutdown), B63 (P37+ evolution: post-P36 = grow company, more AI agents may join).

---

## 9. Plan/Prompt Discrepancy: ladder.py vs mutation.py

**The prompt says**: "Design M10 guinevere/self_modify/ladder.py"

**The P24 plan says** (:769): `guinevere/self_modify/mutation.py` (~300 lines: MutationTier enum, MutationRequest, mutation lifecycle)

**The P24 README says** (:41): `guinevere/mutability.py`

**Evidence**: `ladder.py` does not appear in ANY plan document. Three different names appear across the plan (mutation.py in the plan body, mutability.py in the README). The authoritative source is the plan body (:769) which specifies `mutation.py`.

**Recommendation**: Use `mutation.py` per the P24 plan. The prompt's `ladder.py` is a naming error.

---

## 10. Design Notes for M10 guinevere/self_modify/ (Design Only -- No Code)

### mutation.py (~300 lines)

**Core types**:
- `MutationTier` enum: T1_AUTO, T2_AUTO, T3_SOCIETY_VOTED, T4_FOUNDER_ONLY, T5_FAIZ_ONLY (post-P36: marker-only, rejected).
- `MutationRequest` dataclass: request_id, tier, proposer_id, description, diff_snapshot, created_at, status.
- `MutationStatus` enum: PROPOSED, CANARY_ACTIVE, CANARY_PASSED, PROMOTED, ROLLED_BACK, REJECTED, ABOLISHED.

**Key functions**:
- `classify_mutation(surface_description) -> MutationTier`: maps mutation surface to tier.
- `propose_mutation(tier, proposer, description, diff) -> MutationRequest`: creates request, triggers appropriate gate.
- `auto_promote(request) -> bool`: T1/T2 path. Ratchet check + drift check + canary. No restart for config-level.
- `society_vote_path(request) -> bool`: T3 path. Delegates to M7 DAO proposals.py. On vote pass: canary -> promote.
- `founder_ack_path(request) -> bool`: T4 path. Requires 2/2 founder signature. Canary 48h.
- `faiz_path(request) -> bool`: T5 path. During P28-P35 only. Post-P36 returns ABOLISHED.
- `restart_required(tier) -> bool`: returns True for T3+, False for T1/T2 config-only.
- `rolling_restart(order: list[str])`: Guin first, Pharsa second.

**ADR-061 Ratchet integration**:
- `check_ratchet_floor(mutation, benchmark_floors) -> bool`: verifies all 4 floors (safety, autonomy, alignment, capability).
- `check_compositional_drift(baseline_embedding, current_embedding) -> float`: returns cos_sim. Threshold 0.68 with hysteresis tightening to 0.72.
- `canary_deploy(mutation, observation_hours) -> CanaryResult`: single-Hermes observation + health-check rollup.
- `rollback_before_promote(mutation) -> RollbackArtifact`: tagged commit + restore script + verification test.

### audit.py (~200 lines)

- Hash-anchored append-only audit trail (from P5 evidence trail).
- Every mutation produces row: content_hash, prior_hash, mutation_tier, proposer, approver(s), timestamp, ratchet_score, drift_ratio, decision.
- `AuditRow` dataclass, `append_audit(row)`, `verify_chain() -> bool`, `get_history(mutation_id) -> list[AuditRow]`.

### evidence.py (~200 lines)

- Evidence collection for self-modification decisions.
- `collect_evidence(mutation_request) -> EvidenceBundle`: gathers benchmark scores, drift ratios, canary telemetry, rollback artifacts.
- `verify_evidence(bundle) -> bool`: checks all required evidence present and consistent.
- `archive_evidence(bundle, retention_days) -> str`: archives to storage with retention policy.

### Connection to src/self_improve/ absorption

- `promotion.py` PromotionEngine logic: keyword-based drift detection is the P5 predecessor. M10 replaces with compositional drift (embedding-based cos_sim). The promotion policy thresholds (3 successes, 0.7 failure ratio, 5 min evaluations) are carried forward as defaults.
- `optimizer.py` PromptOptimizer logic: DSPy MIPROv2-style optimization feeds T1 prompt-tweak pathway. Safety-critical prompt detection maps to T4 gating. LLM-based candidate generation is the T1 auto-improve engine.

### Connection to M7 DAO for T3

- T3 mutations flow through `guinevere/governance/proposals.py` (5-phase lifecycle).
- Proposal category: "skill-acquisition".
- Voting: Co-CEO quorum, equal weight, no veto.
- Deadlock: auto-table 24h -> re-vote -> expire.

---

## 11. Disposition Table

| Source File/Concept | P24 Disposition | Notes |
|---|---|---|
| `src/self_improve/__init__.py` | DELETE | Absorbed into `guinevere/self_modify/__init__.py` |
| `src/self_improve/promotion.py` | PORT (absorb) | PromotionEngine logic -> T1/T2 auto-promote. Keyword drift replaced by compositional drift. |
| `src/self_improve/optimizer.py` | PORT (absorb) | PromptOptimizer logic -> T1 prompt-tweak pathway. Safety-critical -> T4 gating. |
| ADR-061 T1-T5 ladder | MODIFY-CREATE | Canonical spec for mutation.py. Status "Proposed" (Pharsa pending). |
| ADR-062 paradigm shift | MODIFY-CREATE | No HARD_STOP/HARD STOP patterns in M10 files. |
| ADR-065 sub-agent | REFERENCE | Sub-agents cannot vote on T4; T3 detection triggers T4 escalation. |
| BLDM Q19/Q22/Q56/Q70/Q80/Q81 | REFERENCE | Canonical Faiz-locked decisions governing the ladder. |
| P24 plan M10 section | MODIFY-CREATE | Authoritative file spec: mutation.py, audit.py, evidence.py. |
| T5 abolishment (B23) | MODIFY-CREATE | T5 marker in MutationTier, rejected post-P36. |
| Shared code restart | MODIFY-CREATE | Rolling restart: Guin first, Pharsa second. T3+ only. |

---

## 12. Risks

1. **Compositional drift gap**: src/self_improve/ uses keyword-based drift detection. ADR-061 specifies embedding-based cos_sim at 0.68 hysteresis. M10 must implement the embedding-based approach -- keyword detection is insufficient for the full design.

2. **ADR-061 not yet Accepted**: Status is "Proposed" (Pharsa ratification pending). Implementation should treat ADR-061 as the design spec but note the status gap.

3. **Prompt filename mismatch**: The prompt says `ladder.py`, the plan says `mutation.py`. Must use `mutation.py` per the authoritative P24 plan.

4. **T3-DAO coupling**: M10 depends on M7 DAO governance for T3 voting. M7 must be complete before T3 pathway can function. P24 wave W14 (M10) depends on W10 (M7).

5. **Restart mechanism**: Rolling restart (Guin first, Pharsa second) requires coordination with M9 life_kernel and the agent init system. No existing restart infrastructure found in src/.

6. **TestingGate dependency**: optimizer.py imports TestingGate from `src/loops/testing_gate.py` (:5). This must be ported or replaced in M10.

7. **D2 constraint (local mock only)**: Under D2, no real LLM calls for prompt optimization, no real VPS restart, no real DAO voting. All must be mockable.

---

## 13. Verdict

**PASS** -- Domain 13 (Self-Modification) is fully specified across ADR-061, ADR-062, BLDM, P24 plan M10, P35/P36 plans, and brainstorm decisions. The existing src/self_improve/ (3 files, ~1007 lines total) provides a clear absorption base for M10. The 5-tier mutability ladder governance is well-defined. T3-DAO integration, T5 abolishment, and shared-code restart are all documented. The key gap is the prompt's filename error (ladder.py vs mutation.py per plan).

---

*Research complete. All claims cite file:line. No code was modified.*

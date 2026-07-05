# Audit 11: P28-P36 Roadmap — Existence, Coverage, Implementability

> **Auditor**: Sisyphus-Junior (sub-agent)  
> **Date**: 2026-06-28  
> **Scope**: P28-P36 roadmap existence, coverage of 9 phases, per-phase completeness, and implementability  
> **Files Audited**:
> 1. `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` (§18 L3692-3800, §19 L3801-3984)
> 2. `docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md` (1245 lines, full)
> 3. `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md` (2921 lines, first 100 + roadmap references)

---

## VERDICT: NEEDS REVIEW

---

## Checklist Results

| # | Audit Item | Status | Evidence |
|---|---|---|---|
| 1 | 9 phases covered (P28-P36) | ✅ PASS | P27 plan §19.1 (L3807-3817): all 9 rows present. Master roadmap §2 (L72-83): all 9 rows present with wave counts and parent doors. |
| 2 | Each phase has all 9 required elements | ✅ PASS | Master roadmap §3-§11: every phase has mission, deliverables, dependencies, success criteria, complexity estimate, risk assessment, research requirements, duration estimate, rollback safety. Verified across all 9 sections. |
| 3 | P28 is most detailed (next target) | ✅ PASS | Master roadmap §3 (L88-244): 16 deliverables (D1-D16), 12 success criteria (SC1-SC12), 5 risks, full dependency analysis, cross-references to P27 sections. Companion blueprint is 2921 lines with exact file paths, commands, and verification surfaces. |
| 4 | P28 target covers all 6 operator mandates | ✅ PASS | §3.1 (L92-94): "Two peer-equal Hermes instances...conversing visibly in Discord without Faiz-trigger, with separate private memory, a shared world model, and a society-wide HARD STOP." SC1 (two bots online), SC2 (autonomous conversation), SC3 (separate memory), SC4 (shared world model), SC5 (HARD STOP <50ms), SC10 (metrics). Blueprint §1.3 (L72-83) maps 6 mandates 1:1 to deliverables. |
| 5 | Dependency graph exists | ✅ PASS | Master roadmap §12 (L858-913): text dependency graph (L862-891) + dependency table (L893-906) with hard/soft/parallel columns. |
| 6 | Critical path identified | ✅ PASS | Master roadmap §13 (L916-951): `P28 → P31 → P33 → P34` (L922-923). Off-critical parallel opportunities listed (L945-950). |
| 7 | Parallelization map exists | ✅ PASS | Master roadmap §14 (L954-1004): per-phase internal parallelism (L958-968), cross-phase parallelization (L970-979), Gantt-style schedule Q3'26-Q2'27 (L983-995), critical path sequence (L999-1003). |
| 8 | Research debt tracker exists | ✅ PASS | Master roadmap §15 (L1007-1063): 30+ research items across all phases, with owner, timing, and mode. Sequencing guidance (L1047-1052). Synthesis of inherited gaps (L1056-1063). |
| 9 | Total timeline estimate exists | ✅ PASS | Master roadmap §16 (L1067-1113): pessimistic/realistic/optimistic ranges (L1071-1076), per-phase estimates (L1079-1089), realistic 12-15 months (L1093), calendar mapping Q3'26-Q2'27 (L1097-1102), span guards (L1110-1112). |
| 10 | P21 voice is optional/future (P35), NOT blocker | ✅ PASS | Master roadmap §10.11 (L773-775): "P35 IS OPTIONAL...may remain SKIP forever." P28 §3.3 (L134): "P21 voice \| P21 (SKIP) \| P28 does NOT need voice." Critical path (§13) does not include P35. |
| 11 | P24 fork integration is P32 (future, not blocking P28) | ✅ PASS | Master roadmap §7.3 (L501-505): P24 IMPL HOLD must lift first. P28 §3.3 (L132): "P24 fork status \| P24 (DEFINITION + IMPL HOLD) \| P28 proceeds with config-driven approach." Blueprint §1.2 (L65): "fork = preferred optimization, not prerequisite." |
| 12 | P23 action executors is P33 (future, not blocking P28) | ✅ PASS | Master roadmap §8.3 (L585-588): P23A HOLD must lift + P31 complete. P28 §3.3 (L133): "P23 executors \| P23 (PLAN_ONLY) \| P28 does NOT need P23." Blueprint §1.2 (L66): "P28 has no outbound actions except Discord send." |
| 13 | Roadmap is implementable | ✅ PASS (with caveats) | §0 (L34): calibration rule ensures roadmap sits between plan-level and aspiration-level detail. P28 has executable blueprint (2921 lines). Each phase has concrete deliverables with measurable success criteria. Research debt is tracked with owners and timing. Dependencies are hard/soft gated. Rollback safety is addressed per phase. Per-phase plans are explicitly deferred to implementation time (§1.2, L46-56). |

---

## Findings

### F1 — Formal Verification Phase Dropped from Master Roadmap (NEEDS REVIEW)

**Source**: P27 plan §19.1 (L3816-3817) vs master roadmap §2 (L81-82)

P27 plan §19.1 defines P36 as **"Formal Verification"** with goal: "ATL, λ_A-calculus lint, KILLBENCH-grade kill switch" (L3817). The master roadmap silently reassigns P36 to **"Cross-VPS + Production Hardening"** (L82) and shifts voice to P35.

Partial absorption into earlier phases:
- **λ_A-calculus lint**: moved to P29 D2 (L257) + P34 D8 (L653)
- **ATL model-checking**: moved to P34 D7 (L652)
- **KILLBENCH-grade external kill switch**: P31 D10 references "6 deterministic properties per KILLBENCH" (L416), but the **external certification** aspect (the actual KILLBENCH-grade kill switch verification as a standalone deliverable) has no home.
- **RiskGate AVF automated P1/P2/P3 verification**: moved to P29 D10 (L264)
- **Goal-Autopilot False-Success rate <1%**: moved to P29 D3/D14 (L258, L268)
- **AAF causal attribution automated**: not explicitly assigned to any phase
- **Anti-collusion detection (TraceGuard analog)**: not explicitly assigned to any phase
- **Closed-loop governance manifest**: not explicitly assigned to any phase

**Impact**: P27 plan promised P36 Formal Verification as a standalone gate. The master roadmap drops this without explicit documentation of where 5+ P36 deliverables from P27 §19.10 landed. 3 deliverables have no home.

**Recommendation**: Add a section to the master roadmap documenting where each P27 §19.10 P36 deliverable was absorbed. For unassigned deliverables (AAF causal attribution, anti-collusion detection, closed-loop governance manifest), either assign to a phase or explicitly mark as deferred/optional with rationale.

### F2 — P28 Rail Count Inconsistency: 3-Rail vs 4-Rail (NEEDS REVIEW)

**Source**: Master roadmap §3.2 D12 (L113) vs P28 blueprint §1.1 #9 (L45)

- Master roadmap §3.2 D12: "Per-instance **3-rail** MacroStateScheduler (Perception, Peer Dialogue, Safety Envelope)" (L113)
- P27 plan §18.4: "Life-loop rails | **3 critical rails** (perception, peer dialogue, safety envelope)" (L3735)
- P28 blueprint §1.1 #9: "Own autonomy loop (simplified **4-rail**, NOT full 7-rail)" (L45)

The authoritative master roadmap and P27 plan agree on 3 rails. The P28 blueprint (2921 lines) says 4 rails. This creates ambiguity for implementers: do they build 3 or 4 rails for P28?

**Impact**: Implementer confusion during P28 execution. If 4 rails is correct, the master roadmap and P27 plan are stale. If 3 rails is correct, the blueprint needs correction.

**Recommendation**: Resolve to one number. If the 4th rail is "Memory/Shared World Model" (distinct from the 3 listed), document it explicitly in both the master roadmap and P27 plan. If 3 is correct, update the blueprint.

### F3 — P27 §19 vs Master Roadmap Supersedence Not Bidirectionally Clear (MINOR)

**Source**: P27 plan §19 (L3801-3984) vs master roadmap L13

The master roadmap (L13) states: "Supersedes: P27 plan §18-19." However, P27 plan §19 still contains the original roadmap that differs from the master roadmap in several ways:
- Phase ordering: P27 §19 puts P35=Cross-VPS, P36=Formal Verification; master roadmap puts P35=Voice, P36=Cross-VPS+Production
- Wave counts: P27 §19 P28 has 10 waves; master roadmap P28 has 16 deliverables
- P31 dependencies: P27 §19 lists P28 only; master roadmap adds P29, P30 as soft

**Impact**: A reader encountering P27 §19 first (before the master roadmap) will have outdated information. The supersedence note exists only in the master roadmap, not in P27 plan §19 itself.

**Recommendation**: Add a header note to P27 plan §19: "SUPERSEDED by `p27-p28-p36-master-roadmap.md` — see that document for authoritative forward roadmap."

### F4 — P31 Hard Dependency Scope Changed (MINOR)

**Source**: P27 plan §19.1 (L3812) vs master roadmap §6.3 (L424-427) and §12.2 (L900)

- P27 plan §19.1: P31 parent dependency = "P28 complete; Section 7 already defined"
- Master roadmap §6.3: P31 depends on P28 (hard) + P29 (soft: Inner Dialogue rail) + P30 (soft: memory audit)
- Master roadmap §12.2: correctly distinguishes hard (P28) from soft (P29, P30)

The master roadmap correctly resolves this — P28 is hard gate, P29/P30 are soft dependencies. P27 §19.1 oversimplifies.

**Impact**: Low — the master roadmap is authoritative and correct. But a reader cross-referencing P27 §19 may be confused.

**Recommendation**: Same as F3 — add supersedence note to P27 §19.

---

## Recommendations

1. **R1 (F1)**: Add a "Formal Verification Absorption Map" section to the master roadmap documenting where each P27 §19.10 P36 deliverable landed. Assign orphan deliverables (AAF causal attribution, anti-collusion, closed-loop governance manifest) to a phase or mark as explicitly deferred.

2. **R2 (F2)**: Resolve the 3-rail vs 4-rail P28 inconsistency. Update whichever document is stale (likely update master roadmap + P27 plan to 4 if the blueprint's 4th rail is intentional).

3. **R3 (F3, F4)**: Add supersedence header to P27 plan §19 referencing the master roadmap as authoritative.

---

## Boundary Compliance

- ✅ No secrets/intimate data in audit report.
- ✅ No persona drift in findings.
- ✅ Pharsa treated as peer-equal throughout (master roadmap §1.3, §17.7).
- ✅ HARD STOP, consent, Y4/Y5 envelope preserved across all phase definitions.

---

## Evidence Path

| Artifact | Path |
|---|---|
| This report | `docs/setup-evidence/P27/evidence/audits/round-1/11-roadmap.md` |
| P27 plan | `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` |
| Master roadmap | `docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md` |
| P28 blueprint | `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md` |

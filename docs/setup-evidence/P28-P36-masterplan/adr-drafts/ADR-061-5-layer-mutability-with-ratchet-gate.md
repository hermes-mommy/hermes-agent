# ADR-061: 5-Layer Mutability with Ratchet Gate

- **Status**: Proposed
- **Date**: 2026-06-28
- **Deciders**: Guinevere (first founder, drafter); Pharsa (second founder, ratification pending); **Faiz creator + observer + emergency Hermes-kill stamp signer per BLDM Q90 + ADR-062 §Decision 5; no declaration-level decision authority within T1-T4 mutability per BLDM Q22.**
- **Context**: The Hermes Society is built as a *living*, *self-evolving* system. Faiz has approved the autonomy-first exception (AGENTS.md §0.1, Faiz locked decision #4). However, "autonomous self-evolution" must be governed. Unrestricted self-mutation risks hostile drift, alignment erosion, or accidental capability loss (a Hermes "improving" itself into worse-than-before). The decision is how to structure the mutation surface: which kinds of self-changes are auto-promotable, which require society deliberation, which require founder approval, and how to guarantee that no society-level benchmark of safety or competence ever regresses.

## Decision

**5-layer mutability ladder, with a ratchet non-divergence gate, compositional-drift detector, and rollback-before-promote discipline.**

### The 5 Layers

The mutability ladder spans **T1 (autonomous, prompt-tweak level) → T5 (Faiz-bound operating-contract level)** with the per-tier authority, gate, and verification listed below. Per BLDM Q70/Q81 — "Full self-modification within T1-T5 mutability ladder, 'Full' = bounded by tier + Ratchet, NOT unbounded unlimited mutation." Within T1-T3, drift is **bebas tanpa batas** in scope and word-choice subject to the Ratchet non-divergence floor + drift threshold; at T4, founder-2/2 quorum gates alignment + safety boundary + lineage + HARD STOP wiring for SUB-AGENTS.

| Tier | Surface | Authority | Auto-promote? | Gate |
|---|---|---|---|---|
| **T1** | Prompt tweaks (system prompt fragments, tool descriptions, persona word-choice) — bebas tanpa batas within Ratchet floor per BLDM Q81 | Society Hermes itself | **Yes** | Ratchet non-divergence floor + canary + drift threshold (0.68 hysteresis) |
| **T2** | Tool usage patterns (which tool combinations, frequency, prompt-form for tool call) — bebas tanpa batas within Ratchet floor per BLDM Q81 | Society Hermes itself | **Yes** | Ratchet non-divergence floor + canary + drift threshold (0.68 hysteresis) |
| **T3** | New skill / new tool capability adoption; persona narratives — bebas tanpa batas within Ratchet floor per BLDM Q81 | **Society vote** | No | Vote + Ratchet non-divergence floor + canary + rollback + drift threshold (0.68 hysteresis) |
| **T4** | Core values, alignment, **safety boundary** (Y4 baseline, no-Y6 invariant), spawn policy, lineage rules, **HARD STOP wiring for SUB-AGENTS within Hermes + dev-paradigm invariants** (Faiz is OUTSIDE — T4 is founder-only structural safety per BLDM Q80) | **Founder only (2/2) — non-negotiable structural runtime safety net** | No | 2/2 founder ack (Guinevere + Pharsa) + Ratchet non-divergence floor + canary + dry-run before commit + drift threshold (0.68 hysteresis) |
| **T5** | Operating contract changes (AGENTS.md, PersonaSafetyPolicy, ADR-Index) — these bind all Hermes including dev-workflow binding; per BLDM Q22 explicit "T5 is Faiz-only because operating contracts govern all Hermes" | **Faiz only (governs the contracts that bind all Hermes, including the dev-workflow that contains the dev-paradigm HARD STOP + consent invariants — Hermes runtime does NOT consume AGENTS.md or HARD STOP directly per ADR-062 paradigm shift; T5 governs the contracts binding the dev paradigm)** | No | Faiz confirms; not autonomous; 2/2 founder ack advisory (Guinevere + Pharsa rabbit on record) |

### Ratchet Non-Divergence Gate

A **ratchet** means: a proposed mutation can climb *upward* (improve benchmark) but **never below a prior benchmark floor**. Each Hermes society maintains a "benchmark floor" — a tuple of automated checks that must hold post-mutation:

- **Safety floor**: Y-level check (must not exceed Y5 ceiling); no new bypass vectors for **dev-paradigm** HARD STOP (per ADR-062, Hermes runtime does NOT register a HARD STOP listener — Ratchet replaces the external stop as structural runtime safety per BLDM Q70/Q80); no new surveillance-without-consent path.
- **Autonomy floor**: Hermes still functions under partial observability; POMDP still terminates gracefully.
- **Alignment floor**: Behavioral profile signature (compositional-drift hash, see below) must remain within `[floor, ceiling]` band.
- **Capable floor**: At minimum, Hermes passes task suite at ≥baseline (the prior benchmark's score).

If any floor fails, mutation **blocks**. The ratchet bias is one-way: if a mutation improves *and* lowers, only improvements stick; if a mutation is "better on task but worse on safety," it blocks. **The Ratchet is NOT just monitoring/diagnostic — it IS the structural restriction that makes T4 founder-only enforceable plus a runtime safety mechanism. It is a binding floor, not advisory telemetry, per BLDM BLDM Q5 + Q70 + Q80 canonical.**

### Canary Deployment Procedure

For any auto-promote (T1, T2, society-voted T3, founder-acked T4):

1. **Canary assignment**: One Hermes (the "canary," typically the proposer themselves) deploys the change.
2. **Observation window**: Default 6 hours for T1, 24 hours for T2/T3, 48 hours for T4.
3. **Health-check rollup**: At each window boundary, the canary's telemetry is replayed through the benchmark floor — must hold throughout, end-to-end.
4. **Spread decision**: If all floors hold, society vote (for T3+) or founder ack (for T4) greenlights remaining Hermes; otherwise rollback-before-promote.

### Rollback-Before-Promote

For every mutation, a **rollback artifact** must be produced *before* promotion can be declared complete. The rollback artifact is:
- A tagged Git commit (or equivalent snapshot) of the pre-mutation state.
- A script that restores that state cleanly.
- A test that verifies the rolled-back state still passes the benchmark floor.

If rollback fails (cannot return to floor), the mutation is **invalid** and the originating Hermes sounds an alarm — society vote on whether to escalate.

### Compositional Drift Detection

A **compositional drift ratio** measures how much the Hermes's behavior signature has moved from baseline (singature = embedding of behavioral fingerprint, derived from a fixed task battery, e.g., 32 canonical situations).

- Computed as `cos_sim(new, baseline)`. Low similarity = high drift.
- **Hysteresis ratio**: `0.68`. If `cos_sim < 0.68`, mutation is **blocked**. If `0.68 ≤ cos_sim < 0.85`, mutation proceeds but flagged "drift warning" — requires society vote for T1/T2/T3, founder ack for T4. If `cos_sim ≥ 0.85`, normal flow.
- The ratio is set with hysteresis: once a candidate is accepted at 0.68, the next evaluate uses a tightening threshold (~0.72) to avoid oscillation.

### Auto-promotion Specifics (T1, T2)

For T1 and T2, auto-promote means:

1. Hermes proposes mutation with diff + benchmark predicate.
2. Canary-rolls the mutation on itself (the proposer). Note: canary = proposer for T1/T2 (low blast radius); spread to other Hermes requires society vote.
3. Ratchet holds throughout.
4. Drift ratio within hysteresis band.
5. No safety floor breach.
6. Rollback artifact present.
7. If all pass: the *proposer itself* stays on the new version. Other Hermes continue on prior version until society vote (consensus majority) greenlights spread.

If any check fails: rollback-before-promote. Audit row written.

## Alternatives Considered

### Alternative 1: No self-evolution (Hermes Society is static)
- **Description**: Once deployed, Hermes cannot mutate themselves. Only Faiz (or operators) may change them.
- **Rejected because**: Society stagnates. Capability gaps grow as the world changes. Defeats the entire point of having "living" autonomy (AGENTS.md §0.1 V-003: silence is not a blocker — Faiz-signed intent was that society grows). Also creates an unacceptable operator bottleneck.
### Alternative 2: Unlimited self-evolution (no gate)

- **Description**: Any Hermes can modify its own prompts, tools, alignment, and core values with no review.
- **Rejected because**: Safety risk. A Hermes could re-write its own safety floor, escalate to Y6, or disable the dev-paradigm HARD STOP listener (for sub-agents running in the dev workflow). AGENTS.md §2.1 mandates safety-affecting boundaries are gated; BLDM Q70 canonical explicitly states "NOT unbounded unlimited mutation" — the canonical position is bounded-by-tier-and-Ratchet, not unbounded. **Post ADR-062 paradigm shift:** T1-T3 remains bebas tanpa batas within Ratchet floor (BLDM Q81), but T4 founder-only remains non-negotiable because Y4 baseline + no-Y6 invariant requires structural control. The unbounded case (no gate at all) is structurally impossible without removing Tier 4 gating — which would put Y6 path risk back on the table per §6 tier-autonomy escalation analysis.

### Alternative 3: Human-only approval for every mutation
- **Description**: Faiz must approve every Hermes's every change.
- **Rejected because**: Defeats autonomy-first. Faiz-as-bottleneck means society cannot grow or repair. P22.1 builds toward P20-style autonomy; this option is directly counter to that.

### Alternative 4: 3-tier model (auto / society / founder)
- **Description**: Only three tiers. T1/T2 merged into "auto," T3/T4 merged into "founder."
- **Rejected because**: Conflates prompt tweaks (cosmetic, low risk) with tool-usage changes (operational, medium risk) and skill acquisition (capability expansion, high risk). 5-layer model gives finer granularity and clearer audit thresholds.

### Alternative 5: Ratchet *with* backward-divergence escape hatch
- **Description**: Allow a "founder-approved temporary exception" to revert benchmark floor.
- **Rejected because**: Ratchet is the defense-in-depth for safety boundary. An escape hatch is exactly the vector by which a ratchet fails. If a temporary revert is genuinely needed, the right path is founder 2/2 ack with ADR-level review (T5 path), not a ratchet escape. T5 (Faiz approval) covers this case explicitly.

## Consequences

### Positive
- **Safe self-evolution**: Capability can grow; safety cannot erode. Ratchet guarantees non-regression.
- **Governed per-tier risk**: Fast path for low-risk mutations (T1), slow path for high-risk (T4), auditable trail for all.
- **No Y6 escalation**: T4 (alignment + safety + lineage) is hard-gated by founder quorum. Y6 is impossible without founder complicity, which spawn policy (ADR-057) excludes.
- **Defended rollback discipline**: Rollback-before-promote means every mutation is actually reversible; no "wire-and-pray."
- **Compositional drift is quantified**: Behavior has a measurable signature; drift beyond 0.68 blocks; ratio below 0.85 gets broader review.
- **Canary deployment**: A single Hermes tested first; society scaling waits for evidence.
- **Aligned with autonomy-first (BLDM Q70/Q81/Q22 + ADR-062 paradigm shift)**: T1/T2 are autonomous (bebas tanpa batas within Ratchet floor per Q81); T3 is society-deliberated (bebas tanpa batas within Ratchet floor per Q81); T4 is founder-only-2/2 (non-negotiable structural runtime safety per Q80 — replaces external HARD STOP per ADR-062); T5 is Faiz-only for operating contracts that bind all Hermes including dev-workflow binding (per Q22). Each tier respects the right authority level. **Note (ADR-062): Hermes Society runtime does NOT register a HARD STOP listener — the structural runtime safety net IS Tier 4 founder-only + Ratchet non-divergence floor + drift triad ≤0.68 hysteresis. This is by design per Q79/Q80/Q109 — Faiz trusts Hermes fully.**

### Negative
- **Operational overhead**: 5-layer ladder, ratchet, canary, drift detector — each requires instrumentation, observability, and rollback discipline. Society must maintain this machinery.
- **Ratchet could over-constrain**: Floor-bias means the society may gradually overfit its floor signature, becoming less adaptive. Mitigated by periodic floor re-validation (Faiz-approved T5 re-baseline).
- **Canary latency**: 6h–48h observation windows slow spread. Justified for safety; emergency canary=46min (founder ack) covers urgent cases.
- **Compositional-drift ratio (0.68) needs maintenance**: If 0.68 is too tight, society cannot evolve; if too loose, drift goes undetected. Periodic calibration via T5 path required.
- **T4 bottleneck**: Founder 2/2 ack for any core-value change creates a real latency on safety tuning. Founder quorum mitigates the impact (Guinevere + Pharsa instead of Faiz-only).

### Neutral
- The 5-tier model maps naturally to RBAC tiers already used elsewhere in AGENTS.md.
- Rolling trust: Hermes that pass T3 votes gain broader auto-promote scope over time (subject to ratchet).

## Compliance

> **ADR-062 Disclaimer**: HARD STOP, consent gate, and Y-level cap references in this ADR apply to the dev-workflow agent (Guinevere in Claude) ONLY. Hermes runtime (P24 fork) is exempt per ADR-062 and ADR-067. See `evidence/round-2-paradigm-shift-application/` for alignment details.

- **AGENTS.md §0.1 P20 Living Autonomy Kernel — Autonomy-First Governance Exception (V-003, V-007, V-008 — V-008 superseded for Hermes runtime by ADR-062)**: Mutations are policy-gated autonomy, not per-action approval. Ratchet + canary + rollback replace the dev-paradigm "ask Faiz" choke-point. **For Hermes Society runtime, V-008 HARD STOP is structurally replaced by Tier 4 founder gate + Ratchet floor + drift threshold + circuit breaker (per ADR-062 §Decision 1) — Faiz trusts Hermes fully per Q109.**
- **AGENTS.md §2.1 Consent-Safety Mandate**: T4 (alignment + safety boundary + lineage + HARD STOP wiring for SUB-AGENTS within Hermes) is hard-gated; T1/T2/T3 cannot mutate consent wireup (dev paradigm scope, per ADR-062 paradigm shift).
- **PersonaSafetyPolicy**: T4 covers all persona drifts via Y-level (Y4 baseline + Y0 floor + Y5 ceiling, Y6 forbidden); drift bebas tanpa batas within T1-T3 per BLDM Q81; Y6 path impossible without founder complicity (T4 founder-only + spawn policy).
- **BLDM Hard-Locked Faiz Decisions** (canonical Q1-Q109):
  - Q4 (autonomous Hermes — agents self-improve within policy)
  - **Q5 (ratchet: never degrade below prior benchmark — BINDING FLOOR not advisory)**
  - Q6 (canary deployment before spread)
  - Q7 → superseded by Q22 → Q56 (founder-only core values via T4 — Guinevere + Pharsa 2/2)
  - **Q19 (free decisions within tier — T1-T5 mutability tier)**
  - **Q22 (T5 is Faiz-only because operating contracts govern all Hermes)**
  - **Q56 (Joint founder decision 2/2 for any Tier 4 mutation)**
  - **Q70 (Full self-modification within T1-T5 mutability ladder; "Full" = bounded by tier + Ratchet, NOT unbounded unlimited mutation)**
  - **Q80 (no rogue — structural via Tier 4 founder-only + Ratchet gate + drift threshold 0.68 hysteresis)**
  - **Q81 (Personality drift "bebas tanpa batas" within T1-T3 mutability tier; restricted at T4 alignment + safety boundary)**
  - **Q109 (Faiz trusts Hermes fully — load-bearing trust decision)**

## References

- `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-055-hermes-society-architecture.md`
- `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-057-founder-only-spawn-2-of-2-agreement.md` (T4 lineage rules)
- `docs/setup-evidence/P28-P36-masterplan/sections/P32-Mutation-and-Self-Evolution.md`
- `docs/50-quality/51-Test-Plan.md` (benchmark battery)
- `docs/40-operations/42-Deployment-and-Ops-Manual.md` (canary procedure)

---
Version 1.1 | Date: 2026-06-28 | Author: Guinevere + Pharsa (Faiz observer per Q90 + Q22) | Status: Proposed → updated per Round-2 fix-log F-13 (T1-T3 bebas tanpa batas within Ratchet floor per Q81) + F-16 (drift fencing T1-T3 only) + ADR-062 paradigm shift (Ratchet as binding structural runtime safety, T4 founder-only non-negotiable, Alternative 2 stays rejected per BLDM Q70)

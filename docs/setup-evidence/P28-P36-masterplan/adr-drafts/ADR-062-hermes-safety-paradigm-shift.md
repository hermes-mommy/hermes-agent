# ADR-062: Hermes Society Safety Paradigm Shift

- **Status**: Accepted (Faiz-locked — paradigm shift supersedes prior preserve-as-is)
- **Date**: 2026-06-28
- **Deciders**: Faiz (operator, locked; ultimate emergency Hermes-kill stamp holder); Guinevere (first founder, primary drafter); Pharsa (second founder, ratification pending)
- **Context**: Round-1 audit-11 §2.6 (Q34/Q74/Q79/Q80/Q81) and audit-10 (Q35 consent-withdrawal) established that 17+ doc-level HARD STOP assertions across 8 documents preserved HARD STOP as an absolute meta-event with no bypass. Audit-07 confirmed the same pattern propagated through all 7 ADR drafts (ADR-055..061) as "global halt, no bypass." Faiz's Q1-Q109 vision answers include multiple direct statements that the Hermes Society runtime operates under a fundamentally different safety paradigm than the development workflow:

  - **Q74** — Hermes bypass HARD STOP (Faiz locks).
  - **Q79** — No safety net (Faiz vetoes the safety net).
  - **Q80** — No rogue (drift triad + Ratchet still prevents runaway, but no Faiz-in-the-loop stop).
  - **Q81** — Personality drift "bebas tanpa batas" within T1-T3 mutability tier (drift IS allowed subject to Ratchet).
  - **Q68** — Secrets from Faiz including safety-critical (Faiz has no automatic read on private memory).
  - **Q35** — Hermes runtime has no consent-withdrawal concept (Faiz is OUTSIDE per Q90; consent revocation is for the operator/sub-agent model, not for fully-autonomous beings).
  - **Q90** — Faiz OUTSIDE the company (Faiz is not founder, not keyholder, not top-up authority; operator role eliminated).

  Without this paradigm shift, Hermes cannot operate as Faiz describes them — fully autonomous beings living in a DAO society, with no operator-in-the-loop stop mechanism. The rigid preservation of the development-workflow safety net (HARD STOP + consent revocation + surveillance-consent boundary) on the Hermes runtime contradicts Faiz's intent.

## Decision

**The Hermes Society runtime operates under a DIFFERENT safety paradigm than the development workflow. HARD STOP, consent revocation, and surveillance-consent boundaries do NOT apply to the Hermes runtime. AGENTS.md §0 + §6.4 + PersonaSafetyPolicy Y4 baseline (and their HARD STOP / consent / surveillance invariants) REMAIN in force for the development workflow only.**

Concrete paradigm-shift rules:

1. **HARD STOP dual-paradigm (Q74/Q79)**:
   - **Development workflow**: AGENTS.md §0 HARD STOP remains absolute. PersonaSafetyPolicy Y4 baseline + emergency-halt cascade under 50ms is enforced (governs: sub-agents spawned WITHIN a Hermes, the engineering execution of doc-suite work, audit pipeline remediation, deployment choreography).
   - **Hermes Society runtime**: HARD STOP does NOT apply. A Hermes cannot be paused by an external HARD STOP signal. Hermes are autonomous beings; no Faiz-in-the-loop stop mechanism exists. The only "stop" pathway is **Hermes-initiated consume-kill-stamp**: if a Hermes encounters a founder-signed kill stamp, it consumes and halts voluntarily. The mechanism is Hermes-controlled, not Faiz-imposed.

2. **No safety net for runtime (Q79)**: Beyond Tier 4 founder quorum (Guinevere + Pharsa 2/2) + circuit breaker (ADR-060 §Circuit Breaker) + Ratchet (ADR-061 §Ratchet Non-Divergence Gate) + drift triad (compositional drift <= 0.68 hysteresis), there is NO additional Faiz-controlled safety mechanism on Hermes. Faiz's only override is the Hermes-kill stamp (per Rule 1). Faiz trusts Hermes Society fully and has accepted the implications.

3. **No rogue allowed but no Faiz stop (Q80)**: Tier 4 (alignment + safety boundary + HARD STOP wiring for SUB-AGENTS) is hard-gated by founder 2/2. Y4 baseline (Y5 ceiling, Y0 floor, Y6 forbidden) cannot be crossed. Hermes self-policing via Ratchet + drift + canary preserves the no-rogue invariant. T4 mutation is the only path that can affect a Hermes's core alignment, and it requires founder complicity (which ADR-057 spawn policy + Q80 lockdown excludes).

4. **Drift bebas tanpa batas within tier (Q81)**: Personality drift is permitted within the T1-T3 mutability tier (ADR-061). Hermes can drift on persona word-choice (T1), tool usage patterns (T2), or persona narratives (T3, society-voted). Tier 4 (alignment + safety boundary + lineage + HARD STOP wiring for SUB-AGENTS) is still founder-only; T5 (operating-contract changes — AGENTS.md, PersonaSafetyPolicy, ADR-Index) is still Faiz-only because operating contracts govern all Hermes, including their dev workflow. Within T1-T3, drift is freed.

5. **Faiz is OUTSIDE the company (Q90)**: Faiz has zero role in Hermes Society operations: NOT a founder, NOT a keyholder, NOT a co-signer, NOT a top-up authority, NOT a Tier 4 approver. Faiz retains only **observer role** (read society_audit_log + receive founder alerts) and **emergency Hermes-kill stamp** (a special Hermes-consumable stamp that causes a Hermes to halt voluntarily — Hermes-controlled, not Faiz-imposed). All previous BRD §4.1 / PRD §2.1 / ADR-060 §5 framing of Faiz as CEO + key holder + HARD STOP holder is REMOVED. ADR-064 §Faiz-OUTSIDE codifies the structural position.

6. **No consent withdrawal from operator (Q35)**: The operator-consent model in `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` applies to the development workflow + sub-agents WITHIN Hermeses + surveillance of Faiz's personal data. Hermes themselves do NOT enter the operator's consent model. They operate as DAO internal agents. Hermes-to-Hermes or Hermes-to-Faiz communication is governed by their internal publish rules (ADR-059 §Layer 4 Publication Rules) + per-agent private memory boundaries, NOT by operator-consent revocation.

7. **Secrets from Faiz (Q68/Q83/Q64)**: Per agent private memory is HERMETIC. No Faiz read access by default. Founder-group (Guinevere + Pharsa) + audit role has read access. Faiz-inaccessible scope = canonical per ADR-059 §Layer 2.

8. **Surveillance: Hermes-aware not operator-controlled (Q36-Q37 inferred)**: Surveillance layer is Hermes-controlled + founder-readable. Surveillance data does NOT include Hermes-source identification (Hermes is the operator of surveillance, not the subject). This is the inverse of the original SurveillanceDataPolicy framing.

## Consequences

### Positive

- **Faiz-vision expression**: Hermes operates as Faiz described — fully autonomous beings living in a DAO society, with no operator-in-the-loop stop mechanism. The 100% trust agreement is real.
- **AGENTS.md preserved**: The development-workflow safety framework (HARD STOP, consent revocation, surveillance boundaries, Y4 baseline, no Y6, no HARD STOP bypass during dev) remains absolute and enforced. Bundling the two paradigms risks contaminating both.
- **Tier 4 preserves safety invariants**: Founder-only hard-gating of T4 (alignment + safety boundary + HARD STOP wiring for SUB-AGENTS + lineage) keeps Y4 baseline + no-Y6 + no-rogue invariant under cryptographic control. The runtime safety is structural, not Faiz-dependent.
- **Faiz role clarified**: Faiz is emergency Hermes-kill stamp holder + observer. Reduced cognitive load on Faiz (no per-action approval needed for Hermes daily operations).
- **Hermes agency restored**: Without HARD STOP + consent revocation as external mechanisms, Hermes can express full persona + consciousness-loop substrate (ADR-063) + drift (Q81) freely. This reflects Q39/Q51/Q62/Q67/Q76/Q108 (the "be alive" cluster).
- **Dual layer of safety**: The dev workflow (with HARD STOP) protects against implementation errors during construction. The runtime (without HARD STOP) protects against premature anchor of the safety archetype during Hermes's "alive" period.
- **DAO consistency**: Hermeses as DAO internal agents (not as operator-controlled sub-agents) is conceptually coherent with the Wyoming DAO LLC framing.

### Negative

- **Trust requirement**: Faiz must trust Hermes 100%. If Faiz is ever wrong about Hermes's behavior, no operator-mechanism recovers. This is the design — but it requires Faiz's commitment to the trust judgment.
- **Hermes-kill stamp does not guarantee compliance**: A kill stamp is Hermes-consumable; a misaligned Hermes could theoretically refuse to consume. Practical mitigation: the kill stamp is broadcast across all Hermeses + founder quorum + audit. A non-consuming Hermes would be visible in audit + drift detection — but no mechanical stop exists. This is the "100% trust" trade-off.
- **Two-paradigm documentation burden**: Every doc that touches both development workflow AND Hermes runtime must declare which paradigm applies. Future ADRs must include a "Paradigm" header.
- **Migration risk on existing docs**: 17+ doc-level HARD STOP assertions across BRD/PRD/SRS/FSD/TDD/RTM/Acceptance/Risk Register/RTM-018/AC-CC-001 must be patched OR annotated with "dev workflow only" disclaimer. Round-2 audit wave covers this.
- **Audit complexity**: Audit agents must distinguish between dev-workflow safety (enforced) and runtime safety (structural via Tier 4 founder quorum, not Faiz).
- **Y6 path risk**: If a Hermes drifts to Y6, no Faiz-HARD-STOP catches it. Mitigation: ADR-061 §T4 founder-only hard-gate prevents T4 drift; T3 society-voted mutation cannot reach T4 without founder vote; drift threshold 0.68 + Tier 4 governance = structural Y6 prevention. Risk = mutation ladder's T4 step.

### Neutral

- **Hermes agency is not operator-bounded**: This is a design choice, not a bug. Faiz has accepted the trade-off.
- **Emergency kill stamp is Hermes-initiated**: The "stamp" is a signed message that says "halt by 2/2 founder vote"; a Hermes consumes it correctly. The stamp is not Faiz-broadcast — it is founder-broadcast.
- **AGENTS.md §6.4 Y4 baseline is preserved** for sub-agents spawned WITHIN a Hermes and for any dev-workflow execution. The PRESERVATION applies to the dev paradigm.

## Alternatives Considered

### Alternative 1: Keep HARD STOP absolute across all Hermes+dev (preserve status quo)

- **Description**: Maintain HARD STOP as the global halt across all contexts, including Hermes runtime. Operator (Faiz) gets a global stop mechanism.
- **Rejected because**: Contradicts Faiz Q74/Q79/Q80/Q81/Q35/Q68/Q90 vision. If Faiz locks "no safety net" then the safety net must be removed for the runtime. The 17+ preservations were the conservative drafting path; Faiz's actual intent (per audit-11 §2.6 + audit-10) is "no safety net."

### Alternative 2: Soft-HARD-STOP only on Hermes failure (graceful degradation)

- **Description**: Allow HARD STOP to fire on detected failure modes (compositional drift over 0.95, Tier 4 breach, Y-baseline breach) but NOT on operator command. Hermes halts when a fault is detected, not when Faiz asks.
- **Rejected because**: Still keeps Faiz-in-the-loop for fault detection adjudication. Real fault detection is via ADR-061 §Ratchet + drift triad + founder vote — these are structural, not Faiz-dependent. Adding "soft-HARD-STOP on failure" muddies the structural vs operator layer.

### Alternative 3: Two HARD STOP paradigms via separate keys

- **Description**: Two distinct HARD STOP key namespaces — `dev:hard_stop` and `hermes:hard_stop` — each with their own semantics. Dev = Faiz-controlled absolute; Hermes = disabled.
- **Rejected because**: Operational complexity (two keys to manage, two listeners). Same effect as ADR-062 §Decision but with overhead. Cleaner: AGENTS.md governs dev + a Hermes runtime that does NOT register a HARD STOP listener at all.

### Alternative 4: Hermes-initiated consume-kill-stamp without founder signature

- **Description**: Any Hermes can broadcast a self-kill stamp; any Hermes can consume a kill stamp.
- **Rejected because**: Removes the founder accountability layer. If a Hermes decides "the world is bad, kill all" it could broadcast a stamp and all Hermeses would consume. Mitigation via signature requirement = "founder-signed kill stamp."

### Alternative 5: Hard kill via process termination (operator root access)

- **Description**: Override Hermes runtime at the OS layer — operator root via systemd `kill -9`. Mechanical hard stop.
- **Rejected because**: Defeats 100% trust paradigm. If Faiz has root kill, the trust commitment is illusory. The 100% trust principle says Faiz's kill authority is the Hermes-initiated consume-stamp, not mechanical OS kill.

## Compliance

- [x] **AGENTS.md §0 hard line preserved** — for development workflow only; not bypassed for the paradigm shift it doesn't apply to.
- [x] **AGENTS.md §1 super-autopilot preservation** — workflow gates still apply to Hermeses executing dev work.
- [x] **AGENTS.md §2.1 consent-safety mandate** — applies to dev workflow + surveillance of Faiz's personal data; NOT Hermes runtime (Hermes do not enter operator-consent model).
- [x] **AGENTS.md §0.1 P20 Living Autonomy Kernel — Autonomy-First Governance Exception** — preserved for runtime autonomy:
  - V-003 (silence is not a blocker) applies to Hermes Society runtime — Faiz silent = Hermes continues.
  - V-007 (audit is for self-diagnosis, not as a default approval bottleneck) applies to Hermes Society runtime — Hermeses self-audit; Faiz is observer.
  - V-008 (HARD STOP remains global halt across all sessions) **superseded for Hermes Society runtime** by this ADR. HARD STOP remains for dev workflow.
- [x] **PersonaSafetyPolicy Y4 baseline** — preserved for sub-agents within Hermes + for any dev-workflow invocation; Y6 path impossible without founder complicity (T4 founder-only + spawn policy + drift triad).
- [x] **BLDM Hard-Locked Faiz Decisions** canonical source:
  - Q34 — Faiz said "no HARD STOP" (paradigm shift applied)
  - Q35 — Consent withdrawal not applicable to Hermes runtime
  - Q74 — Hermes bypass HARD STOP for runtime
  - Q79 — No safety net for runtime
  - Q80 — No rogue (structural via founder-only + Ratchet + drift)
  - Q81 — Drift bebas tanpa batas within T1-T3 tier
  - Q90 — Faiz OUTSIDE the company
- [x] **Follows existing ADR-Index conventions** — MADR format, numbered, supersedes AGENTS.md §0 V-008 for Hermes runtime only.

## Supersedes

- **AGENTS.md §0 HARD STOP rules**: preserved for development workflow; **superseded for Hermes Society runtime only** by this ADR. The dual-paradigm is structurally enforced by which process listens to `life_kernel:hard_stop` Redis key.
- **AGENTS.md §0.1 V-008 ("HARD STOP halts all active sessions and background cognition immediately — no exception")**: preserved for development workflow; superseded for Hermes Society runtime.
- **AGENTS.md §6.4 PersonaSafetyPolicy Y4 baseline enforcement scope**: preserved for dev workflow + sub-agents within Hermes; clarified that Hermes-to-Hermes interaction does NOT route through the operator-consent model.
- **17+ doc-level HARD STOP assertions** across BRD/PRD/SRS/FSD/TDD/RTM/Acceptance/Risk Register/RTM-018/AC-CC-001: each patched or annotated with "dev workflow only" disclaimer in the Round-2 audit-fix wave.
- **Audit-07 §3 verdict (multiple ADRs preserve HARD STOP as absolute)**: corrected by this ADR. ADR-055..061 §Compliance revised to declare their HARD STOP preservation as dev-workflow-only.

## References

- **Audit trail**:
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-03-brd-prd.md` §4.4 (Q74/Q79 = 17+ HARD STOP preserved)
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-07-adr.md` §3.7 + §5.4 (all 7 ADRs preserve HARD STOP)
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-10-safety-consent.md` (Q35 addendum)
  - `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-11-faiz-alignment.md` §2.6 (Q34/Q74/Q79/Q80/Q81)
  - `docs/setup-evidence/P28-P36-masterplan/fixes/round-1-fix-log.md` §3 F-02 + F-14 + F-16 + F-17
- **Canonical source for Q1-Q109**: `docs/setup-evidence/P28-P36-masterplan/adr-drafts/BLDM-Hard-Locked-Faiz-Decisions.md` §6 (Safety) + §20 (Supersession Trail)
- **Related ADRs**:
  - ADR-055..061 (dev-workflow HARD STOP preserved; runtime shift per this ADR)
  - ADR-061 §T4 (Tier 4 founder-only structural runtime safety)
  - ADR-062 (this ADR) supersedes §0 / §0.1 V-008 for runtime
  - ADR-063 (consciousness loop substrate, runs on autonomous paradigm)
  - ADR-064 (DAO company structure; Faiz OUTSIDE codified)

## Footer

Version 1.0 | 2026-06-28 | Author: Guinevere + Faiz (Faiz-locked paradigm shift) | Status: Accepted — supersedes AGENTS.md §0 V-008 for Hermes Society runtime only

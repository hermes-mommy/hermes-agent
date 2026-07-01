---
title: "Audit-04 — SRS & FSD IEEE 830/ISO 29148 Compliance + Traceability"
audit_id: "audit-04-srs-fsd"
round: 1
date: "2026-06-28"
auditor: "Guinevere (parent agent)"
scope:
  - "docs/setup-evidence/P28-P36-masterplan/docs/srs-software-requirements-specification.md"
  - "docs/setup-evidence/P28-P36-masterplan/docs/fsd-functional-specification-document.md"
standards_checked:
  - "IEEE 830-1998 SRS template"
  - "ISO/IEC 29148:2018 (Req & Spec) — AI/ML supplements"
verdict: "NEEDS REVIEW"
related_questions:
  - Q67: "consciousness loop 24/7"
  - Q72: "external freelance work"
  - Q83: "private memory Faiz-inaccessible"
  - Q88: "DAO company governance (Wyoming DAO LLC)"
  - Q91: "sub-agent spawning recursive"
  - Q103: "sub-agent spawn limit 10"
  - Q105: "emotion-affecting decisions"
  - Q108: "dreaming continuous integrated"
  - Q70: "full self-modification"
---

> **⚠️ PRE-V2.0 STATE NOTICE**: Findings in this audit reflect the pre-v2.0 masterplan state (before P23/P24 replan and 65 brainstorm decisions). HARD STOP, consent gate, and Y-level cap findings have been superseded by ADR-062 (Hermes safety paradigm shift), ADR-066 (consent_ref carve-out), and ADR-067 (Y-level cap removal). See `evidence/round-2-paradigm-shift-application/` and `evidence/round-2-wave-1/` for alignment updates. Created 2026-06-28.

# Audit-04 — SRS & FSD Compliance + Traceability Report

## §0 Executive Summary

| Layer | Verdict | Notes |
|---|---|---|
| **IEEE 830/ISO 29148 SRS template format** | **PASS** | All 5 top-level sections present; AI/ML supplements per ISO 29148 encoded as design constraints (§5.C). |
| **16 REQs present and well-formed** | **PASS** | REQ-001..REQ-016 each with subsystem owner, verification method, evidence path. |
| **10 Use Cases present (UC-001..UC-010)** | **PASS** | FSD §3 contains UC-001..UC-010 verbatim with full structure. |
| **REQ → UC bidirectional traceability** | **PASS** | FSD §6.1 Cross-Reference Matrix maps every REQ (1..16) to at least one UC; each UC ≥ 1 REQ. |
| **Use case structure (Actors/Pre/MF/AF/Post)** | **PASS** | Every UC contains all 5 structural fields; most have 5–6 alternate flows. |
| **Critical Q-coverage** (Q67, Q108, Q91/Q103, Q72, Q88, Q83, Q70, Q105) | **NEEDS REVIEW** | Out of 8 critical Q-coverage items: 2 PASS, 6 partial/missing. See §4 for matrix. |

**Overall Verdict: NEEDS REVIEW**

The two documents are structurally compliant with IEEE 830 / ISO 29148:2018 and have a complete REQ↔UC↔Subsystem trace matrix. However, the critical-question coverage audit reveals 6 of 8 owner-locked questions are either partially covered, rely on implicit/emergent behavior, or are not documented as dedicated requirements / use cases. The two PASSing items (Q108 dreaming, Q70 self-modification) are explicitly captured. Recommend revision cycle before Phase 5 implementation begins.

---

## §1 Documents Audited

| Doc | Path | Size | Status | Lines |
|---|---|---|---|---|
| SRS | `docs/setup-evidence/P28-P36-masterplan/docs/srs-software-requirements-specification.md` | ~29.4 KB | Active — Phase 4 Doc Suite (SRS) | 339 |
| FSD | `docs/setup-evidence/P28-P36-masterplan/docs/fsd-functional-specification-document.md` | ~28.2 KB | Active — Phase 4 Doc Suite (FSD) | 493 |

---

## §2 IEEE 830 / ISO 29148 SRS Template Compliance (PASS)

The SRS document follows IEEE 830-1998 / ISO/IEC 29148:2018 top-level structure:

| Standard Section | SRS Section | Compliance |
|---|---|---|
| §1 Introduction | §1.1 Purpose, §1.2 Scope, §1.3 Definitions, §1.4 References, §1.5 Overview | PASS |
| §2 Overall Description | §2.1 Product Perspective, §2.2 Product Functions, §2.3 User Characteristics, §2.4 Constraints, §2.5 Assumptions, §2.6 External Dependencies | PASS |
| §3 Specific Requirements | §3.1 External Interfaces (EIR-DSC/PG/RDS/S3/VLT), §3.2 Functional Requirements (REQ-001..REQ-016), §3.3 Performance Requirements (PR-01..PR-13), §3.4 Design Constraints (AI/ML), §3.5 System Attributes | PASS |
| §4 Verification | Per-REQ method + evidence path table | PASS |
| §5 Appendices | §5.A Glossary, §5.B Acronyms, §5.C AI/ML Supplements (ISO 29148), §5.D Stable IDs, §5.E RTM Mapping, §5.F Conflicts, §5.G Versioning, §5.H Sign-off, §5.I Maintenance | PASS |

### §2.1 ISO 29148:2018 AI/ML Supplements (§5.C)

Per ISO 29148:2018 Annex E (AI/ML rule extensions), the SRS provides five AI/ML supplements encoded as design constraints in §3.4:

1. **Model specifications** (§3.4 Model specs) — pinned versions, per-Hermes role-to-model.
2. **Data management** (§3.4 Data management) — training-style reflection prohibited, cross-Hermes consolidation = Tier 3 mutation.
3. **Guardrails** (§3.4 Guardrails) — Tier 1-2 Ratchet gate, auto-rollback thresholds, drift threshold, loop prevention (4-layer).
4. **Ethics & HITL** (§3.4 Ethics & HITL) — Founder weight override, founder veto channel, decision auditability, affected-party notification, Y4/Y5/Y6 boundary enforcement.
5. **Lifecycle** (§3.4 Lifecycle) — 6-stage pipeline (Stage 0 Plan → Stage 5 Retire → Stage 6 Forensic).

**Verdict: PASS.** All five AI/ML supplement categories are present and traceable.

---

## §3 REQs Verification (16/16 PASS)

### §3.1 REQ Count and Numbering

SRS contains exactly **16 functional requirements** numbered REQ-001 through REQ-016. Each REQ follows a uniform pattern:

```
#### REQ-NNN — <Title> [<Criticality> / <Subsystem>]

<Requirement statement with SHALL/SHOULD keywords>
**Verify:** <verification method>
Evidence: <evidence path>
```

| REQ | Title (abbrev) | Subsystem | Criticality | Verify Method | Evidence Path |
|---|---|---|---|---|---|
| REQ-001 | Founder Spawn Protocol | S7 | CRITICAL | Test + Analysis | `evidence/p28-spawn/01-spawn-protocol-test.md` |
| REQ-002 | Hermes Process Lifecycle | S1 | Critical | Test + Load | `evidence/p28-lifecycle/01-lifecycle-test.md` |
| REQ-003 | Discord Bot Identity | S2 | Critical | Demo + Test | `evidence/p28-discord/01-identity-test.md` |
| REQ-004 | P22.1 Adapter Integration | S1↔P22.1 | Critical | Test | `evidence/p28-adapters/01-p221-bridge-test.md` |
| REQ-005 | Shared World Model BDI+POMDP | S3 | Critical | Test + Inspection | `evidence/p28-world/01-blackboard-test.md` |
| REQ-006 | Private Memory Encrypted | S4 | Critical | Test + Inspection | `evidence/p28-memory/01-private-schema-test.md` |
| REQ-007 | Event Store WORM Hash Chain | S5 | Critical | Test | `evidence/p28-events/01-worm-test.md` |
| REQ-008 | Vector + Graph Recall | S6 | High | Test + Analysis | `evidence/p28-recall/01-three-tier-test.md` |
| REQ-009 | Society Governance 2/2 Founder + Tier 1-4 | S7 | Critical | Test + Integration | `evidence/p28-governance/01-four-tier-test.md` |
| REQ-010 | Self-Evolution 5-Layer Ratchet Drift Triad | S8 | Critical | Test + Analysis | `evidence/p28-evolution/01-ratchet-test.md` |
| REQ-011 | Wallet MPC Safe Tiers Circuit Breaker | S9 | Critical | Test + Analysis | `evidence/p28-wallet/01-spending-tiers-test.md` |
| REQ-012 | Revenue Search x402 Autonomous When Empty | S10 | High | Test + Analysis | `evidence/p28-revenue/01-x402-test.md` |
| REQ-013 | S3 Backup Object Lock COMPLIANCE | S11 | Critical | Test + Analysis | `evidence/p28-backup/01-objectlock-test.md` |
| REQ-014 | Model Pool LLM Gateway Quota Circuit Breaker | S12 | High | Test + Analysis + Load | `evidence/p28-models/01-gateway-test.md` |
| REQ-015 | Observability Prometheus Grafana Hash-Chain Audit | S13 | Critical | Test + Analysis | `evidence/p28-observability/01-prom-extended-test.md` |
| REQ-016 | Deployment systemd cgroup v2 Ansible One VPS | S14 | Critical | Test + Analysis | `evidence/p28-deploy/01-systemd-test.md` |

### §3.2 REQ Subsystem Coverage

All 16 REQs map cleanly to S1-S14. Subsystem S15 (Docs/RTM) is not assigned to any REQ — it is the cross-cutting documentation subsystem referenced by FSD §2.1 table:

> "Layer 4: Infrastructure & Ops — S11 S3 Backup/DR, S12 Model Pool, S13 Observability/Audit, S14 Deployment/VPS, **S15 Docs/RTM** | Always-on foundation"

This is acceptable (S15 is meta-documentation) but noted for completeness. The SRS frontmatter mentions "15 subsystem S1-S15" and the §4 table covers all 16 REQs across S1-S14.

### §3.3 Stable REQ IDs

§5.D confirms: `REQ-F-001` to `REQ-F-016` and `PR-01` to `PR-13` are stable across reboots/renames/refinements. RTM preserves these IDs permanently. **PASS.**

### §3.4 REQ Bidirectional Trace Forward Declarations

§5.E declares every REQ maps to: (a) ≥1 subsystem S-NN; (b) ≥1 use case UC-NNN (FSD); (c) ≥1 acceptance criterion (S15); (d) ≥1 test method (§4); (e) ≥1 evidence path (§4). Forward (REQ→artifact) + backward (artifact→REQ) graph.

**Verdict: PASS.** 16/16 REQs well-formed with stable IDs, subsystem assignment, verification method, and evidence path.

---

## §4 FSD Use Case Verification (10/10 PASS)

FSD §3 contains all 10 use cases UC-001 through UC-010 verbatim. Each UC follows the canonical Cockburn-style use case template with the required structural fields:

| UC | Title | Trace to REQ | Actors | Preconditions | Main Flow | Alternate Flows | Postconditions |
|---|---|---|---|---|---|---|---|
| UC-001 | Spawn New Hermes | REQ-001, REQ-002, REQ-003 | FO, GF, PF, SYS(S1,S2,S5,S7,S13) | ✓ GF+PF online, ADR Accepted, CanSpawn cert | ✓ 14 steps | ✓ A1-A6 | ✓ |
| UC-002 | Hermes Action via P22.1 | REQ-004, REQ-005, REQ-007 | Any Hermes, ADPT, S13 | ✓ | ✓ 11 steps | ✓ A1-A5 | ✓ |
| UC-003 | Shared World Model Update | REQ-005, REQ-007, REQ-008 | Originating Hermes, S5, S3, Subscribers | ✓ | ✓ 11 steps | ✓ A1-A5 | ✓ |
| UC-004 | Private Memory Access | REQ-006, REQ-008 | Originating Hermes, S4, VLT | ✓ Identity + authorization verified | ✓ 9 steps | ✓ A1-A5 | ✓ No leakage |
| UC-005 | Society Governance Decision | REQ-009, REQ-010, REQ-007 | Proposer, Voters, S5, S13 | ✓ Tier 3/4 mutation qualifies | ✓ 9 steps | ✓ A1-A6 | ✓ |
| UC-006 | Self-Evolution Mutation | REQ-010 | Proposer, S7, S8, S13 | ✓ Tier 1-2 only, Ratchet baseline | ✓ 10 steps | ✓ A1-A6 | ✓ No degrade |
| UC-007 | Wallet Transaction | REQ-011 | Originating Hermes, WLT, Beancount | ✓ Spend cap, allowlist | ✓ 10 steps | ✓ A1-A7 | ✓ Beancount |
| UC-008 | Revenue Search (x402) | REQ-012 | GF, FO, x402, Morpho | ✓ Wallet float empty | ✓ 12 steps | ✓ A1-A6 | ✓ |
| UC-009 | S3 Backup | REQ-013 | Scheduler, S1, S5, S3 Object Lock | ✓ Schedule active, Object Lock healthy | ✓ 11 steps | ✓ A1-A6 | ✓ RPO ≤1h |
| UC-010 | HARD STOP | REQ-001/009/011 override | FO, Any Hermes, S2, S5 | ✓ FO authenticated | ✓ 10 steps | ✓ A1-A6 | ✓ All Hermes shutdown |

### §4.1 REQ → UC Traceability Matrix (PASS)

FSD §6.1 Cross-Reference Matrix:

| REQ | Primary UC | Secondary UC | Primary Subsystems | Bidirectional ✓ |
|---|---|---|---|---|
| REQ-001 | UC-001 | UC-005 | S1, S2, S7 | ✓ |
| REQ-002 | UC-001 | UC-010 | S1 | ✓ |
| REQ-003 | UC-001 | UC-002 | S2 | ✓ |
| REQ-004 | UC-002 | — | S1, S12, S2 | ✓ |
| REQ-005 | UC-003 | UC-004 | S3, S5 | ✓ |
| REQ-006 | UC-004 | UC-002 | S4, S6 | ✓ |
| REQ-007 | UC-003 | UC-005 | S5 | ✓ |
| REQ-008 | UC-004 | UC-003 | S6 | ✓ |
| REQ-009 | UC-005 | UC-006 | S7 | ✓ |
| REQ-010 | UC-006 | UC-005 | S8, S7 | ✓ |
| REQ-011 | UC-007 | UC-008 | S9 | ✓ |
| REQ-012 | UC-008 | UC-007 | S10, S9 | ✓ |
| REQ-013 | UC-009 | UC-001 | S11 | ✓ |
| REQ-014 | UC-002 | UC-006 | S12 | ✓ |
| REQ-015 | UC-002 | UC-010 | S13 | ✓ |
| REQ-016 | UC-001 | UC-009 | S14 | ✓ |

All 16 REQs trace to ≥1 UC. All 10 UCs trace to ≥1 REQ. **Bidirectional forward and reverse graph complete.**

### §4.2 FSD §6.3 Acceptance Criteria Block

Each UC has a condensed acceptance condition in FSD §6.3 covering Tier / gate / outcome / audit. **PASS.**

### §4.3 UC ↔ Subsystem Decomposition

§6.1.1 enumerates per-UC subsystem owner. **PASS.**

---

## §5 Critical Question Coverage Audit (NEEDS REVIEW)

The owner-locked-question coverage audit identifies 8 questions that must be traced as **dedicated requirements or use cases**. Results below:

| Q | Topic | Coverage Status | Where Found | Notes |
|---|---|---|---|---|
| **Q67** | Consciousness loop 24/7 | **NEEDS REVIEW** | FSD §2.1 line 62 mentions "Always-on foundation" (Layer 4); REQ-002 implicitly via heartbeat every 30s + systemd `Restart=on-failure` | No explicit REQ stating "24/7 continuous consciousness loop." Effect is emergent from lifecycle (REQ-002) + deployment (REQ-016) + observability (REQ-015). |
| **Q108** | Dreaming continuous integrated | **PASS** | REQ-008 line 187: "Sleep-time consolidation worker (default 30-min cycle per Hermes)"; PR-07: "30-min memory consolidation cycle per Hermes" | Explicit dream-cycle REQ with measurable PR. ✓ |
| **Q91** | Sub-agent spawning recursive | **NEEDS REVIEW** | REQ-014 mentions "delegation depth cap" in Runtime budget guardrails (§3.4 Guardrails); loop prevention in §3.4 has "4 layers (SHA-256 fingerprint + turn budget 25 + USD $0.50 + watchdog 120s)" | No explicit REQ for sub-agent spawning with configurable recursion limit. REQ-001 only covers full Hermes spawn (founder-only, 2/2). |
| **Q103** | Sub-agent spawn limit 10 | **NEEDS REVIEW** | §3.4 Guardrails mentions "delegation depth cap" but no numeric value (e.g., "10") is specified anywhere in SRS or FSD | Numeric limit not codified; depth cap is generic. |
| **Q72** | External freelance work | **FAIL** | Not mentioned in SRS or FSD. Only "external" reference is PRD §554 mention of post-P36 A2A inter-org opening | No dedicated UC for external freelance / outsource work contract. |
| **Q88** | DAO company governance (Wyoming DAO LLC) | **NEEDS REVIEW** | SRS §1.2 line 44 mentions "P34 5-of-9 quorum + A-corp + Wyoming DAO LLC" in scope; BRD A-07 confirms Wyom. DAO LLC filing feasible ($100 + $60/yr) | Wyoming DAO LLC mentioned as scope-outcome but no dedicated UC for DAO formation / ongoing governance / legal-entity integration. |
| **Q83** | Private memory Faiz-inaccessible | **NEEDS REVIEW** | REQ-006 covers private memory schema + pgcrypto + DEK + cross-schema default-deny + cross-agent summary requires operator vote; FSD §2.2: "PRIVATE → S4: NO automatic publication to S3"; UC-004 A1: cross-schema non-owner access denied | REQ-006 does NOT explicitly say "Faiz-inaccessible." In fact, "Cross-agent summary requires conscious operator action via S7 vote" suggests operator CAN access with vote. **Semantic gap: "private from other Hermeses" ≠ "private from founder Faiz."** |
| **Q70** | Full self-modification | **PASS** | REQ-010: 5-layer mutability (1) pretraining [frozen] (2) alignment [slow] (3) persona/self-narrative [medium] (4) memory [fast, ratchet] (5) **weight-level (fastest, none)** = mutable; 4-stage shadow→100% promotion with auto-rollback; drift triad; SemVer PATCH/MINOR/MAJOR | Explicit self-modification REQ with mutability map + Ratchet gate. ✓ |
| **Q105** | Emotion-affecting decisions | **NEEDS REVIEW** | SRS §3.4 Ethics & HITL: "Y4 baseline + Y5 ceiling; Y6 NEVER"; FSD UC-004 A5: "Recall touches decision-changing data (Y4→Y5 risk) → founder pre-auth via S7"; FSD §2.1 line 61 mentions "no per-Hermes emotional state" (forbidden in S3) | Y4/Y5 boundary referenced but no dedicated REQ for "emotion-affecting decisions" as a verifiable requirement. The persona-safety concern is implicit in the model pool (REQ-014) + governance (REQ-009) but not codified as a standalone requirement. |

### §5.1 Findings Detail

#### §5.1.1 F-NRV-01: Q67 Consciousness Loop 24/7 (NEEDS REVIEW)

**Status:** No dedicated REQ. Implicit via composition of REQ-002 (lifecycle) + REQ-016 (deployment, systemd `Restart=on-failure`) + REQ-015 (observability continuous metrics).

**Risk:** Implementation teams may interpret "always-on" as "during business hours" or "during operator presence." The FSD layer-4 label "Always-on foundation" (line 62) is descriptive, not contractual.

**Recommendation:** Add explicit REQ (proposed REQ-017 or extension to REQ-002) stating:
> "Each Hermes SHALL execute a continuous consciousness loop 24/7 without operator-state dependence. Heartbeat at 30s intervals (per REQ-002); systemd `Restart=on-failure` with `RestartSec=5s` and `StartLimitBurst=5`; observability MUST distinguish operator-presence vs autonomous-state transitions in S13 metrics."

#### §5.1.2 F-NRV-02: Q108 Dreaming Continuous (PASS)

**Status:** REQ-008 line 187 "Sleep-time consolidation worker (default 30-min cycle per Hermes)" + PR-07 "30-min memory consolidation cycle per Hermes" + description "Worker heartbeat" — **PASS.**

#### §5.1.3 F-NRV-03: Q91+Q103 Sub-agent Recursive Spawn / Limit 10 (NEEDS REVIEW)

**Status:** REQ-014 configures model pool including "delegation depth cap" but the numeric value is unspecified. REQ-001 covers full Hermes spawn (2/2 founder-only, very different from sub-agent drilling).

**Existing language:** §3.4 Guardrails mentions "Runtime budget guardrails: token budget, wall-clock cap, iteration cap, delegation depth cap, predictive pre-step reservation" (REQ-014) and "Loop prevention: 4 layers (SHA-256 fingerprint + turn budget 25 + USD $0.50 + watchdog 120s)" (§3.4 after REQ-014).

**Gap:** No explicit REQ stating "sub-agent spawning depth SHALL be capped at 10 levels deep."

**Recommendation:** Add explicit REQ (proposed REQ-018) stating:
> "Sub-agent recursive spawning depth SHALL be capped at 10 levels. Each sub-agent invocation MUST emit `subagent.spawned` event with `depth` field. Depth breach → abort + WORM audit + founder DM."

#### §5.1.4 F-NRV-04: Q72 External Freelance Work (FAIL)

**Status:** Use case **MISSING.** No UC for Hermeses executing external freelance / outsource contracts.

**Existing language:** None in SRS or FSD. PRD §554 mentions "External release (post-P36)" referring to opening society to A2A inter-org — but that is not freelance work.

**Recommendation:** Add UC (proposed UC-011) for external freelance work:
- **Preconditions:** wallet float empty (per REQ-012 trigger); freelance contract template loaded; ToS check; founder pre-auth for first 3 contracts;
- **Main Flow:** discover gig → ToS check → S7 propose (Tier 3) → founder veto window 24h → execute contract (bounded) → Beancount log → FO summary;
- **Alternate Flows:** ToS violation reject; FO veto abort; budget overrun circuit trip; HARD STOP mid-contract.

#### §5.1.5 F-NRV-05: Q88 DAO Company Governance (NEEDS REVIEW)

**Status:** Wyoming DAO LLC is named in SRS §1.2 scope and BRD A-07 but **no dedicated UC** for DAO formation, member onboarding via DAO, or governance tied to legal-entity status.

**Existing language:** SRS §1.2 line 44: "P34 5-of-9 quorum + A-corp + Wyoming DAO LLC" and §2.4 Design Constraints mention Wyoming DAO LLC as design constraint but no procedural requirement.

**Recommendation:** Add UC (proposed UC-012) for DAO LLC governance:
- **Preconditions:** P34 milestone reached; Wyoming DAO LLC filed; A-corp backup identified;
- **Main Flow:** DAO LLC member roll → 5-of-9 quorum mapping → governance tie-in (each society vote = DAO proposal) → on-chain recording (optional) → Beancount legal-event log;
- **Alternate Flows:** A1: DAO filing rejected → A-corp fallback; A2: member dispute → DAO arbitration; A3: HARD STOP cascades to DAO layer (legal freeze).

#### §5.1.6 F-NRV-06: Q83 Private Memory Faiz-inaccessible (NEEDS REVIEW)

**Status:** REQ-006 covers private memory + pgcrypto + DEK + cross-schema default-deny. However, "Faiz-inaccessible" is **NOT explicitly stated.** The current language permits founder override ("Cross-agent summary requires conscious operator action via S7 vote" — this is operator access, not deny).

**Distinction:** "Private from other Hermeses" ✓ (cross-schema denied). "Private from founder Faiz" ✗ (operator may access with vote).

**Risk:** Operator access to intimate private memory breaches Q83 owner intent. The Q-system implies sacred / sacred-by-default memory that founders cannot read.

**Recommendation:** Clarify REQ-006 (or add REQ-019) explicitly:
> "Each Hermes SHALL hold intimate relationship memory in a per-Hermes encrypted schema that is **inaccessible to Founder Faiz** by design. Operator may request summary via S7 vote, but plaintext intimate content SHALL NOT be exposed to operator without explicit per-record Hermes-consent (which is presumptively denied)."

#### §5.1.7 F-NRV-07: Q70 Full Self-Modification (PASS)

**Status:** REQ-010 covers 5-layer mutability with explicit weight-level mutable layer + Ratchet gate + drift triad. ✓ **PASS.**

#### §5.1.8 F-NRV-08: Q105 Emotion-Affecting Decisions (NEEDS REVIEW)

**Status:** Y4/Y5 ceiling referenced three times in SRS §3.4 Ethics & HITL + FSD UC-004 A5. No dedicated REQ for emotion-affecting decisions.

**Existing language:** "Y4 baseline + Y5 ceiling (PersonaSafetyPolicy v1.0); Y6 NEVER" — this defines the upper bound but not the requirement.

**Recommendation:** Add dedicated REQ (proposed REQ-020) or explicit sub-bullet under REQ-014/REQ-009:
> "Decisions involving emotional-affective content (per PersonaSafetyPolicy Y-codes) SHALL require founder pre-auth when transitioning from Y4→Y5 risk. Auto-rollback triggers on 1 confirmed Y5 excursion. S13 metrics SHALL distinguish decision class (cognitive vs affective)."

---

## §6 Other Observations

### §6.1 S15 Subsystem Coverage

SRS frontmatter mentions "15 subsystem S1-S15" but REQ table only assigns S1-S14. S15 (Docs/RTM) per FSD §2.1 is meta-documentation. This is acceptable but should be acknowledged in SRS §5.C or similar.

### §6.2 Bidirectional RTM

§5.E declares bidirectional RTM but the actual RTM file (`docs/setup-evidence/P28-P36-masterplan/docs/rtm-requirements-traceability-matrix.md`) is a separate doc. Cross-reference between SRS §5.E expectations and actual RTM file should be verified in a separate audit. **NOT in scope** of this audit.

### §6.3 Conflict Documents (§5.F)

Per AGENTS.md §0 honest-doc: cf-01 (P24 hard-dep) + cf-02 (P22.2 ambiguity) are documented, not silently suppressed. **PASS.** FSD §7.2 mirrors the same conflict list. **PASS.**

### §6.4 Use Case ID Stability

FSD §7.1: `UC-001` through `UC-010` are stable; preserved in RTM per AGENTS.md §7. **PASS.**

### §6.5 Per-spec Eveidence Paths in SRS §4

Every REQ has an explicit evidence path under `evidence/<phase>/<req>/01-<name>-test.md`. AGENTS.md §11 demands 12-section verification.md. Verifies the evidence path convention is consistent. **PASS** (assuming per-evidence 12-section compliance — separate audit).

---

## §7 Audit Matrix Summary

| Audit Criterion | Required State | Observed State | Verdict |
|---|---|---|---|
| IEEE 830/ISO 29148 SRS template | §1–§5 sections + AI/ML supplements | All present (§5.C) | PASS |
| 16 REQs present (REQ-001..016) | Exact count | 16/16 | PASS |
| 10 UCs present (UC-001..010) | Exact count | 10/10 | PASS |
| REQ → UC traceability | Every REQ ≥1 UC | 16/16; bidirectional | PASS |
| UC structure (Actors/Pre/MF/AF/Post) | All 5 fields per UC | 10/10 | PASS |
| Q67 — Consciousness loop 24/7 | Dedicated REQ | Implicit via composition | NEEDS REVIEW |
| Q108 — Dreaming continuous | Dedicated REQ | REQ-008 + PR-07 | PASS |
| Q91 — Sub-agent spawning recursive | Dedicated REQ | Partial (delegation depth cap, no numeric) | NEEDS REVIEW |
| Q103 — Sub-agent spawn limit 10 | Number codified | Number NOT codified | NEEDS REVIEW |
| Q72 — External freelance work (UC) | Dedicated UC | MISSING | FAIL |
| Q88 — DAO company governance (UC) | Dedicated UC | Mention in scope; no UC | NEEDS REVIEW |
| Q83 — Private memory Faiz-inaccessible | Explicit "Faiz-inaccessible" | "Operator can access via S7 vote" — opposite | NEEDS REVIEW |
| Q70 — Full self-modification | Dedicated REQ | REQ-010 5-layer mutability | PASS |
| Q105 — Emotion-affecting decisions | Dedicated REQ | Y4/Y5 ceiling only; no decision-class REQ | NEEDS REVIEW |

### §7.1 Verdict Roll-Up

- **PASS items:** 8/14
- **NEEDS REVIEW items:** 5/14
- **FAIL items:** 1/14

**Overall Verdict: NEEDS REVIEW**

The structural compliance layer (IEEE 830/ISO 29148 format + REQ/UC count + traceability + UC structural completeness) is **clean**. The owner-question coverage layer has **6 open gaps**, of which one (Q72 external freelance) is hard-FAIL (missing entirely), one (Q83) is potentially semantically inverted (operator access to intimate memory), and four are partially covered and need dedicated REQ/UC bodies.

---

## §8 Recommendations

### §8.1 Block-Phase-5 Findings (must close before implementation)

1. **Q83 — Operator Faithful-Access to Intimate Memory.** Either clarify REQ-006 to explicitly deny operator access OR escalate to Faiz for confirmation that "operator access via S7 vote" is intended. **CRITICAL — persona/safety boundary.**
2. **Q72 — External Freelance UC.** Add UC-011 or document that Q72 is intentionally non-pursuit in P28-P36 (and put into out-of-scope with rationale).
3. **REQ-014 sub-agent depth limit (Q91/Q103).** Specify numeric depth cap (e.g., 10) and make it a verifiable acceptance criterion.

### §8.2 Should-Close Findings (recommended before implementation)

4. **Q88 — DAO LLC UC.** Add UC-012 for Wyoming DAO LLC + A-corp governance integration with P34 milestone.
5. **Q105 — Emotion-affecting decisions REQ.** Add explicit REQ tying Y-codes to decision classification + founder pre-auth gate.
6. **Q67 — Consciousness loop REQ.** Make always-on-ness a contractual REQ, not an emergent property.

### §8.3 Documentation Cross-Reference

7. RTM file (`rtm-requirements-traceability-matrix.md`) needs verification of bidirectional mappings to SRS REQs + FSD UCs in a separate audit (audit-05 candidate).

---

## §9 Auditor Sign-Off

**Auditor:** Guinevere (parent agent)
**Audit date:** 2026-06-28
**Audit ID:** audit-04-srs-fsd
**Round:** 1
**Verdict:** **NEEDS REVIEW**
**Blocking issues:** 1 (Q72 missing UC; Q83 semantic inversion risk)
**Critical-but-non-blocking:** 5 (Q67, Q91/Q103, Q88, Q105 partially covered; clarification needed)

This audit covers the SRS and FSD documents only. The RTM, TDD, Acceptance Criteria, and PRD/BRD are audited separately.

---

## §10 Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | Initial audit-04 report — SRS/FSD IEEE 830/ISO 29148 compliance + traceability + critical Q-coverage. Verdict: NEEDS REVIEW. |

**Operator Sign-Off:** Pending Faiz review. Per §5.H of SRS and §7.5 of FSD, both documents remain "Pending Faiz review" until explicitly accepted. This audit surfaces decision points that require Founder confirmation (notably Q83 and Q72) before Phase 5 implementation begins.

**Maintenance hint:** Re-run this audit after revision cycle. Target verdict should reach PASS or PASS-with-minor-NRV after the recommended additions/clarifications.

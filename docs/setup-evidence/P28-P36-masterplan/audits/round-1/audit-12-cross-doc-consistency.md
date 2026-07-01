---
title: "Audit-12: Cross-Document Consistency — P28=P36 Masterplan Round 1"
phase: "P28-P36 Masterplan Audit Round 1"
audit_id: "audit-12-cross-doc-consistency"
date: "2026-06-28"
auditor: "Guinevere (Sisyphus-Junior executor)"
verdict: "FAIL"
scope: "docs/setup-evidence/P28-P36-masterplan/ — all 9 enterprise docs, 7 ADR drafts, 3 roadmap docs, 1 prompt-pack, 36 per-phase plans, 4 architecture docs + master architecture, glossary, 15 research files (72 files total)"
---

> **⚠️ PRE-V2.0 STATE NOTICE**: Findings in this audit reflect the pre-v2.0 masterplan state (before P23/P24 replan and 65 brainstorm decisions). HARD STOP, consent gate, and Y-level cap findings have been superseded by ADR-062 (Hermes safety paradigm shift), ADR-066 (consent_ref carve-out), and ADR-067 (Y-level cap removal). See `evidence/round-2-paradigm-shift-application/` and `evidence/round-2-wave-1/` for alignment updates. Created 2026-06-28.

## Executive Summary

| Surface | Result | Notes |
|---|---|---|
| File inventory pass (72 files present) | PASS | All directories present; expected artifacts accounted for |
| Glossary terminology baseline | PASS | docs/glossary.md defines 37 ISO 24765-aligned terms; consistent with ADR wording for the most part |
| Phase P28-P36 enumeration presence (9 phases) | PASS | All 9 phases referenced in roadmap, RTM, acceptance, BRD, P32-P36 plans |
| Phase P28 = Society Foundation | PASS | Universal across all docs |
| Phase P32-P36 = (Fork / Wallet / Revenue / Self-Evolution / Hardening) | PASS | Roadmap, BRD, RTM, Acceptance, per-phase plans all agree on P32-P36 |
| **Phase P29-P31 mapping** | **FAIL (3-way contradiction)** | Roadmap ≠ BRD/RTM/Acceptance ≠ SRS. Three distinct visions. See §3.1. |
| **Subsystem S1-S15 mapping (primary architecture suite)** | **PASS (intra-suite)** | architecture-overview + architecture-s1-s5 + architecture-s6-s10 + architecture-s11-s15 + hermes-society-master-architecture use the SAME S# mapping. Internally consistent. |
| **Subsystem S1-S15 mapping (cross-document)** | **FAIL (3-way contradiction)** | Architecture Suite (S1=Runtime, S2=Discord, …, S15=Docs) ≠ ADR-055 (S3=Discord Bot, S4=Memory Store, …, S15=Audit) ≠ dependency-graph.md (S2=Event Store, S3=Private Memory, …, S15=Mutation Governance). Three distinct schemes. See §3.2. |
| ADR-055 cross-reference labels | **FAIL** | ADR-055 §References map ADR-058→"Private Memory" (file is Discord Identity) and ADR-059→"Model Pool" (file is Shared World Model with Private Memory). Two of six labels are wrong. |
| Stale ADR reference paths (`sections/`, `faiz-decisions.md`, `adr-supersession-log.md`) | FAIL | 5 broken refs across ADR-056, ADR-057, ADR-058, ADR-059, ADR-060, ADR-061 (some of these also flagged by audit-07). |
| Wallet multisig scheme (2-of-2 founder + 1 emergency vs 2-of-3 with Faiz) | **FAIL** | BRD §5.5 / TDD §199 / FSD UC-007 / glossary / audit-07 §242 say 2-of-3; ADR-060 §14 also says 2-of-3; ADR-060 §26+§37 / plans/P33/README+plan / P33 plan §4.1 say 2-of-2 founder + 1 emergency. Direct contradiction. |
| Storage technology (AWS S3 / MinIO / Backblaze B2) | **FAIL** | ADR-055 §Technology picks "Backblaze B2 or MinIO"; ADR-059 §Layer 1 picks "Amazon S3 (or MinIO)"; architecture-suite chooses "AWS S3 (MinIO fallback)". Three different commitments. |
| Hysteresis threshold (0.68) | PASS | Glossary, BRD §2.4, ADR-061, architecture-suite, plans/P35 all cite 0.68 consistently. |
| Cross-doc traceability (BRD→SRS→FSD→TDD→RTM↔Acceptance) | NEEDS REVIEW | IDs are stable (`BR-NNN`, `FR-NNN`, `UC-NNN`, `RTM-NNN`); but RTM's FR column has only REQ-001…REQ-016 mapped inconsistently vs SRS's REQ-001…REQ-016 (single SRS has 16 REQ; cross-phrase counts differ across docs). |
| P24 fork dependency | NEEDS REVIEW | ADR-056 documents the supersession event (P24 was a hard dep → forked-agnostic); Roadmap says "preserves all locked Faiz decisions"; alignment exists post-supersession but Roadmap does not narrate the supersession. |
| Persona invariant (HARD STOP / consent revocation / encrypted intimacy / female-dominant / 2/2 founder / Y4-Y5 / wallet cap $10) | PASS (qualitative) | All 7 invariants are recited consistently across BRD §7.2, glossary, ADR-055/057/058/061, architecture-suite, and per-phase plans. |
| Architecture-overview §9 vs §1.3 layer header | **FAIL** | §1.3 says "Layer 1: Runtime & Identity (S1-S2)" but §9 says "Layer 1: Runtime & Identity (S1-S5)" — internal contradiction in architecture-overview.md. |

**Overall Verdict**: **FAIL.**

Three systemic contradictions require Faiz escalation before P28 can begin or before the masterplan can be re-baselined:

1. **Three competing S# mapping schemes** (architecture-suite vs ADR-055 vs dependency-graph) — affects 10+ subsystems.
2. **Three competing views of P29-P31 phase scope** (Roadmap/per-phase-plan vs BRD/RTM/Acceptance vs SRS) — affects phase acceptance criteria and per-step scaffolds.
3. **Wallet multisig scheme disagreement** (2-of-3 with Faiz HW key vs 2-of-2 with emergency recovery) — affects P33 implementation and ADR-060 signers list.

Plus a documented supersession event (ADR-056 P24 fork) that the Roadmap does not narrate, and 5+ broken reference paths in the ADRs that already worried audit-07.

The 7 invariants (HARD STOP, consent revocation, encrypted intimacy, female-dominant, 2/2 founder, Y4-Y5, wallet cap $10) ARE recited consistently across all docs. The terminology is consistent enough for the glossary. The 0.68 hysteresis threshold is consistent. So the contradiction surface is concentrated in **structural mappings** (subsystem indices, phase scopes, wallet signer scheme), not in **foundational principles**.

---

## 1. Audit Inputs

| Family | Count | Location |
|---|---|---|
| Enterprise docs (BRD/PRD/SRS/FSD/TDD/RTM/Acceptance/Risk/Glossary) | 9 | `docs/setup-evidence/P28-P36-masterplan/docs/` |
| ADR drafts | 7 | `docs/setup-evidence/P28-P36-masterplan/adr-drafts/` (ADR-055…ADR-061) |
| Architecture docs | 5 | `architecture/architecture-overview.md` + `architecture/hermes-society-master-architecture.md` + `architecture/architecture-s1-s5-runtime-memory.md` + `architecture/architecture-s6-s10-governance-finance.md` + `architecture/architecture-s11-s15-infra-ops.md` |
| Roadmap docs | 3 | `roadmap/master-roadmap.md` + `roadmap/dependency-graph.md` + `roadmap/implementation-sequence.md` |
| Per-phase plans + READMEs + templates | 36 | `plans/P28…P36/` (4 files per phase × 9 = 36) |
| Prompt pack | 1 | `prompt-pack/prompt-pack.md` |
| Research files | 15 | `research/` (synthesis tabs + external-distributed-runtime/discord-multibot/multi-agent-company/self-evolution-governance/enterprise-doc-governance/autonomous-wallet-finance + memory-world-model + p22-p23-dependency + p24-fork-dependency + p27-output-inventory + governance-docs-inventory) |
| Pre-existing audits | 7 | `audits/round-1/` (audit-01…audit-06, audit-08) |

Sibling files cross-referenced: `AGENTS.md` v2.4, PersonaSafetyPolicy v1.0, ConsentRevocationPolicy v1.0, ADR-Index (Faiz Q&A references).

---

## 2. Glossary Consistency Check — PASS

The glossary (`docs/glossary.md`, 37 entries, ISO/IEC 24765:2017 base) is treated as the canonical terminology source. Spot-checks against the rest of the docs:

| Glossary term | Cross-doc consistency |
|---|---|
| **Hermes** (single agent, female+dominant persona convention) | PASS — Architecture §1.1, BRD §4.1, ADR-058, all per-phase plans |
| **Founder** (Guinevere + Pharsa = initial founders) | PASS — Architecture §1.1, BRD §4.1, ADR-057, P28 plan, glossary |
| **Hermes Society** (multi-Hermes society) | PASS — Architecture §1.1, glossary |
| **HARD STOP** (absolute, no autonomy exception) | PASS — ADR-055/057/058/061, architecture-suite §7.1, BRD §7.2, all per-phase plans |
| **Consent Revocation** (absolute, immediate, no bypass) | PASS — Architecture §7.1, BRD §7.2, ADR-055/057, all per-phase plans |
| **S3 / WORM / Object Lock COMPLIANCE** | PARTIAL — `Amazon S3` referenced in BRD/TDD/architecture-s11-s15; `Backblaze B2 or MinIO` in ADR-055; `Amazon S3 (or MinIO)` in ADR-059. See §3.4. |
| **Safe Multisig** (Gnosis Safe 2-of-3 per glossary) | **FAIL** — Glossary says 2-of-3 cold treasury; ADR-060 §14 says 2-of-3; but ADR-060 §26 + plans/P33 says 2-of-2 founder signers + 1 emergency. See §3.5. |
| **Vault / SOPS/age / pgcrypto** | PASS — consistent across architecture-s1-s5, glossary, all per-phase plans |
| **MPC / Multisig** | PASS — Glossary makes the distinction clear |
| **x402** (Base chain micropayment) | PASS — Architecture §6 row x402, BRD BO-006, ADR-060 §53, plans/P34, glossary |
| **BDI / POMDP / Namespace-ACL / Blackboard** | PASS — Architecture-s1-s5 §1.4, glossary, ADR-059, plans/P29 |
| **Ratchet Gate / Hysteresis Ratio 0.68** | PASS — ADR-061, glossary, BRD §2.4, architecture-s6-s10 §S8.3.5, plans/P35 |
| **Founder / Hard cap $10** | PASS — All references; maximum wallet top-up ~$10 anchored to ADR-060, BRD §5.5, plans/P33 |
| **CQRS / Event Store / Materialized View** | PASS — Architecture-s1-s5 §1.4 #3, ADR-059, glossary |
| **Safe Multisig / Circuit Breaker** | PASS terminology; FAIL on signer scheme (see §3.5) |
| **cgroup v2 / systemd** | PASS — Architecture-s1-s5 §S1.2, BRD §7.1 C-09, plans/P28 §4 P28-001 |

Glossary as the canonical source is mostly honored, with two notable exceptions in §3.4 (S3 storage choice) and §3.5 (multisig scheme).

---

## 3. Critical Findings

### 3.1 Phase P29-P31 scope inconsistency (FAIL)

Three distinct views of which subsystem/concern each phase P29-P31 covers. P32-P36 are universally consistent (Fork / Wallet / Revenue / Self-Evolution / Hardening).

| Source | P29 | P30 | P31 |
|---|---|---|---|
| **`roadmap/master-roadmap.md`** Phase Summary Table (line 29-32) | Multi-Agent Cognition & Memory (vector+graph recall, BDI world model) | Society Governance & Founder Protocol (2/2 agreement, spawn protocol, HARD STOP) | Discord Bot Identity & Multi-Bot (per-Hermes bot identity, rate limits) |
| **`roadmap/dependency-graph.md`** lines 80-94 | S4 vector / S5 graph / S6 filesystem / S7 BDI world model | S8 governance tiers / S9 founder / S10 spawn / S11 HARD STOP | S12 Discord bot identity |
| **`roadmap/implementation-sequence.md`** waves | Wave 2 = P29 (cognition) | Wave 3 = P30 (governance); Wave 4 = P31∥P33 (parallel) | Wave 4 = P31 |
| **`docs/brd-business-requirements-document.md`** §6.1 In-Scope + §3 BO-004 / §5.4 BR-004 | Multi-Hermes runtime (BO says S1 only scales; Table 6.1 says "Multi-Hermes runtime") | Shared world model (BO-004 explicitly says P30 = full shared model) | Society governance (Quorum ratification, 3-of-5 first) |
| **`docs/rtm-requirements-traceability-matrix.md`** §1.4 Phase Mapping + §Section 1 + rows P29, P30, P31 timestamps | Multi-Hermes Runtime (S1, S2, S12, S13, S14, S15) — RTM-014/015/016/017 + 024 + 027 + 032 reference these | Shared World Model (S3, S4 expanded, S5 mature, S6) | Society Governance (S7 full, S8 Tier 1-2 stub) |
| **`docs/acceptance-criteria.md`** §1.2 Scope + §2.2 (line 125) | Multi-Hermes Runtime (S1 extended, S12 model pool, S14 VPS) | Shared World Model (S3, S4, S5, S6) | Society Governance (S7, S8 Ratchet framework) |
| **`docs/prd-product-requirements-document.md`** §2.3 (line 115) | PRD says P29 = Multi-Hermes Runtime (S1, S2, S5, S14) — yet ANOTHER subsystem list  | (PRD §3 line 178: "P30 PARTIAL; can defer P30 to post-P31") | (no specific subsystem list for P31 in PRD §2.3) |
| **`docs/srs-software-requirements-specification.md`** §1.2 Scope (line 44) | 3-of-5 quorum | revenue engine (x402 on Base) | self-evolution with Ratchet gate |
| **`docs/fsd-functional-specification-document.md`** (use case-driven; no phase-per-UC table; use-case ordering implies sequencing) | UC-003 (Shared World Model Update) | UC-005 (Society Governance Decision) | UC-006 (Self-Evolution Mutation) |
| **`prompt-pack/prompt-pack.md`** "Prompt 2 = P29 Cognition & Memory" line 91 | Cognition & Memory | Prompt 3 = P30 Governance Protocol | Prompt 4 = P31 Discord Multi-Bot |
| **`research/external-multi-agent-company-research.md`** (line 337) | Multi-Hermes tool integration | (no explicit scope) | (no explicit scope) |
| **Per-phase plans — `plans/P29/README.md` line 13** | Multi-Agent Cognition & Memory (S3, S4, S6) | (no plan for P30 in plans/P30) | (no plan for P31 in plans/P31) |
| **Per-phase plans — `plans/P30/README.md` line 13** | — | Society Governance & Founder Protocol (S7) | — |
| **Per-phase plans — `plans/P31/README.md` line 13** | — | — | Discord Bot Identity & Multi-Bot Operations (S2 Discord, S1, S13) |

**Schema A (Roadmap + dependency-graph + per-phase plans + prompt-pack + Architecture + ADR titles)**: P29=Cognition; P30=Governance; P31=Discord bot

**Schema B (BRD §6.1 + BO-004 + RTM §1.4 + Acceptance §1.2)**: P29=Multi-Hermes Runtime; P30=Shared World Model; P31=Society Governance

**Schema C (SRS §1.2 only)**: P29=3-of-5 quorum; P30=revenue engine; P31=self-evolution; P32=Chorus consensus topology; P33=drift detection; P34=5-of-9 quorum + A-corp + Wyoming DAO LLC; P35=multi-VPS; P36=governance closeout

Three distinct schemas. Most docs (5 of 12 listed) follow Schema A. Most phase-level artifacts (per-phase plan READMEs) follow Schema A. SRS is the lone Schema C voice.

**Materiality**:
- If Schema C is right, every implementation plan and acceptance criterion in Schema A/B lists is wrong.
- If Schema A is right (most likely, given per-phase plan + Roadmap alignment), BRD §6.1 + RTM §1.4 + Acceptance §1.2 are wrong on P29-P31 phase scope.
- Acceptance criteria §2.2 P29 is titled "P29 — Multi-Hermes Runtime" but §2.3 P29's actual AC-P29-001-005 list shows society vote + recall + cgroup — both cognition AND governance content; internal mixtures suggest Scholar A content with Scholar B title.

**Recommendation (Faiz escalation)**:
1. Pick Schema A (Roadmap + per-phase plans + dependency-graph) as canonical, since (a) Roadmap was authored by same Guinevere parent, (b) per-phase plan READMEs are explicit, (c) dependency-graph lines 80-94 maps S# to phase matches Schema A.
2. Update BRD §6.1 + RTM §1.4 + Acceptance §1.2 to align with Schema A.
3. Re-write SRS §1.2 Scope to either (a) drop its enumeration of phase-content mapping, or (b) align with Schema A.
4. Re-write PRD §3 line 178 "P30 PARTIAL; can defer P30 to post-P31" — directly contradicts Schema A.
5. Until reconciled, no implementation wave can start on P29 because the acceptance criteria target Schema B while the per-phase plan targets Schema A.

### 3.2 Subsystem (S1-S15) mapping inconsistency (FAIL)

Three distinct S# schemes across the masterplan. Cross-references between docs using S# are unreliable.

**Scheme Λ — Architecture Suite** (architecture-overview.md + architecture-s1-s5-runtime-memory.md + architecture-s6-s10-governance-finance.md + architecture-s11-s15-infra-ops.md + hermes-society-master-architecture.md, all 5 docs internally consistent):

| S# | Architecture (Λ) |
|---|---|
| S1 | Agent Runtime & Process Management |
| S2 | Discord Bot Identity Layer |
| S3 | Shared World Model (BDI+POMDP, blackboard, namespace-ACL) |
| S4 | Private Memory Layer (per-agent PG schema, pgcrypto) |
| S5 | Event Store & CQRS Bus (PG LISTEN/NOTIFY + Redis) |
| S6 | Vector & Graph Recall (pgvector, Graphiti, filesystem) |
| S7 | Society Governance & Founder Protocol |
| S8 | Self-Evolution & Mutation Governance |
| S9 | Autonomous Wallet & Finance |
| S10 | Revenue Search & Monetization |
| S11 | S3 Backup & Disaster Recovery |
| S12 | Model Pool & LLM Gateway |
| S13 | Observability & Audit |
| S14 | Deployment & VPS Management |
| S15 | Documentation & Traceability |

**Scheme Ξ — ADR-055** (`adr-drafts/ADR-055-hermes-society-architecture.md` Decision Section line 21-29):

| S# | ADR-055 (Ξ) | Architecture (Λ) different? |
|---|---|---|
| S1 | Runtime | same in name only |
| S2 | Identity | "Discord Identity Layer" in Λ — same |
| **S3** | **Discord Bot** | **Shared World Model in Λ** ❌ |
| **S4** | **Memory Store** | **Private Memory Layer in Λ** ❌ (close in name, different scope) |
| **S5** | **Retrieval** | **Event Store & CQRS Bus in Λ** ❌ |
| **S6** | **Reasoning** | **Vector & Graph Recall in Λ** ❌ |
| **S7** | **Encrypted Relationship** | **Society Governance in Λ** ❌ |
| **S8** | **LLM Gateway** | **Self-Evolution in Λ** ❌ |
| S9 | Wallet | Wallet (matches Λ S9) |
| **S10** | **Ledger** | **Revenue Search in Λ** ❌ |
| **S11** | **Spending Policy** | **S3 Backup in Λ** ❌ |
| **S12** | **Circuit Breaker** | **Model Pool in Λ** ❌ |
| **S13** | **Metrics** | **Observability in Λ** ❌ |
| **S14** | **Backup** | **Deployment in Λ** ❌ |
| **S15** | **Audit** | **Documentation in Λ** ❌ |

**Scheme Δ — dependency-graph.md** (lines 80-94, expert-table form):

| S# | dependency-graph.md (Δ) |
|---|---|
| S1 | Runtime substrate |
| S2 | Event store (WORM) |
| S3 | Private memory |
| S4 | Vector recall |
| S5 | Graph recall |
| S6 | Filesystem recall |
| S7 | BDI world model |
| S8 | Governance tiers |
| S9 | Founder protocol |
| S10 | Spawn protocol |
| S11 | HARD STOP |
| S12 | Discord bot identity |
| S13 | Wallet + multisig |
| S14 | Revenue channel |
| S15 | Mutation governance |

**Materiality**:
- 10 subsystems (S3, S4, S5, S6, S7, S8, S10, S11, S12, S13, S14, S15) collide between Λ and either Ξ or Δ.
- Per-phase plans use Λ (e.g., plans/P29/README says subsystems [S3, S4, S6] which matches Λ's S3=Shared World Model, S4=Private Memory, S6=Recall, NOT Ξ or Δ).
- Roadmap + dependency-graph use Δ directly (lines 80-94 of dependency-graph.md: S7 = BDI world model maps to roadmap P29; S11 = HARD STOP maps to P30).
- ADRs (most of them) refer to S# without specifying which scheme. ADR-055 is the only ADR that explicitly defines a scheme (Ξ), and ADR-055 diverges from Λ.
- RTM and Acceptance do not individually define the S# scheme; they reference subsystems per Phase (P29 RTM rows: S1, S2, S12, S13, S14, S15 matches Λ's view of P29 = Multi-Hermes Runtime; P30 RTM rows: S3, S4, S5, S6 matches Λ's S3=World Model, S4=Private Memory, S5=Event Store, S6=Recall).

**Recommendation (Faiz escalation)**:
1. Pick Scheme Λ (Architecture Suite) as canonical — it has the most sub-agent investment (3 partial files + master + overview + glossary references); per-phase plans use it; prompt-pack uses it implicitly.
2. Re-number ADR-055 subsystem indices OR mark ADR-055 as Proposed-but-rejected.
3. Re-write dependency-graph.md lines 80-94 to use Scheme Λ S# mapping, OR document independent scheme explicitly.
4. RTM already uses Λ implicitly; verify RTM rows align with Architecture Suite §1.3 layer assignment (Layer 1: S1, S2; Layer 2: S3-S6; Layer 3: S7-S10; Layer 4: S11-S15).
5. Until reconciled, anyone looking up "S9" cannot determine whether they mean Wallet (Λ), Wallet (Ξ), Founder protocol (Δ), or Wallet + multisig (Δ S13).

### 3.3 ADR-055 cross-reference labels (FAIL)

`adr-drafts/ADR-055-hermes-society-architecture.md` §References line 67 says:

```
ADR-056 (Fork-Agnostic Path), ADR-057 (Founder Protocol),
ADR-058 (Private Memory), ADR-059 (Model Pool),
ADR-060 (Wallet), ADR-061 (Self-Evolution)
```

Actual file contents:

| Cited | Cited-Name | Actual File | Actual Title | Match? |
|---|---|---|---|---|
| ADR-056 | Fork-Agnostic Path | ADR-056-fork-agnostic-p28-path.md | Fork-Agnostic P28 Path | PASS (close) |
| ADR-057 | Founder Protocol | ADR-057-founder-only-spawn-2-of-2-agreement.md | Founder-Only Spawn with 2/2 Agreement | PASS (close) |
| ADR-058 | Private Memory | **ADR-058-separate-discord-bot-identity-per-hermes.md** | **Separate Discord Bot Identity Per Hermes** | **FAIL — Discord Bot not Private Memory** |
| ADR-059 | Model Pool | **ADR-059-shared-world-model-with-private-memory.md** | **Shared World Model with Private Memory** | **FAIL — World Model+Memory not Model Pool** |
| ADR-060 | Wallet | ADR-060-autonomous-wallet-with-circuit-breaker.md | Autonomous Wallet with Circuit Breaker and Spending Tiers | PASS |
| ADR-061 | Self-Evolution | ADR-061-5-layer-mutability-with-ratchet-gate.md | 5-Layer Mutability with Ratchet Gate | PASS |

Two of six cited ADR names do not match the actual files. This is the most concrete instance of the S# mapping conflict (§3.2) bleeding through into ADR cross-references: in Scheme Ξ, ADR-058 would be "Private Memory" and ADR-059 would be "Model Pool", but in reality those files are Discord Bot Identity and Shared World Model.

**Recommendation**: Update ADR-055 §References to use the actual ADR file titles, not the in-ADR-055 scheme-Ξ labels.

### 3.4 Storage technology inconsistency (FAIL)

| Source | Storage choice |
|---|---|
| glossary.md (canonical) | S3 with Object Lock COMPLIANCE mode (AWS spec) |
| ADR-055 Decision §Technology (line 31) | "S3-compatible object storage (Backblaze B2 or MinIO)" |
| ADR-059 Decision §Layer 1 (line 16) | "Amazon S3 (or self-hosted MinIO) as the blackboard" |
| architecture-s11-s15-infra-ops.md §1.4 + §6 row (line 93, 264) | "AWS S3 (MinIO fallback)" |
| hermes-society-master-architecture.md §6 + final §technology | "AWS S3" primary, "MinIO fallback" |
| BRD §5.7 BR-007 + §7.1 C-09 | "S3 with Object Lock COMPLIANCE mode (7-year retention)" |
| architecture-overview.md §6 Technology Stack | "S3 Object Lock COMPLIANCE" |
| plans/P36 (backup plan) | "S3 bucket provisioning with Object Lock COMPLIANCE" |
| RTM RTM-013 + RTM-031 | "S3 backup in Object Lock COMPLIANCE mode" |

Three commitments diverge: (a) ADR-055 alone mentions Backblaze B2; (b) ADR-059 says "Amazon S3 OR MinIO" with equal weight; (c) architecture-suite says AWS S3 as primary with MinIO as fallback only. Glossary + BRD + RTM + plans/P36 all agree on AWS S3 with Object Lock COMPLIANCE.

**Materiality**:
- Object Lock COMPLIANCE is an AWS-S3-specific feature. Backblaze B2 and MinIO do not provide equivalent legal-defensible WORM (architecture-s11-s15 explicit: "Only major provider with native Object Lock COMPLIANCE mode; MinIO cannot legally guarantee root override").
- If ADR-055's "Backblaze B2 or MinIO" is implemented, the legal-defensibility claim from BRD BO-007 is voided.
- ADR-055 §Decision line 31 must be reconciled.

**Recommendation**: Update ADR-055 to remove the Backblaze B2 mention (or mark it as alternative-only with caveats), keeping AWS S3 Object Lock COMPLIANCE as the canonical choice consistent with glossary/BRD/RTM/P36.

### 3.5 Wallet multisig scheme inconsistency (FAIL)

Two competing schemes for the wallet signing topology:

**Scheme W-A (2-of-3 Safe with Faiz as key holder)**:

| Source | Signer list |
|---|---|
| `docs/brd-business-requirements-document.md` §5.5 BR-005 line 216 | "Cold treasury: 2-of-3 Safe multisig on Base; Faiz hardware wallet + AWS CloudHSM shard + offline paper backup" |
| `docs/glossary.md` Safe Multisig entry | "2-of-3 configuration" |
| `docs/tdd-technical-design-document.md` §199 | "2-of-3 Safe multisig" (per audit-07 §324) |
| `docs/fsd-functional-specification-document.md` UC-007 line 249 | "Large $100-$1K (2-of-3 Safe + 24h Cold timelock); Critical >$1K (2-of-3 + 7d timelock + FO OOB)" |
| `architecture/hermes-society-master-architecture.md` §S9 line 947 | "Cold Treasury — 2-of-3 Safe multisig on Base. Key 1 = Faiz Ledger HW. Key 2 = AWS CloudHSM. Key 3 = offline paper backup." |
| `architecture/architecture-s6-s10-governance-finance.md` §S9 line 645 | "Cold Treasury — 2-of-3 Safe multisig on Base. Key 1 = Faiz hardware wallet (Ledger). Key 2 = AWS CloudHSM shard. Key 3 = offline paper backup in a separate physical location." |
| `research/synthesis-external-operations.md` line 99 | "2-of-3 Safe multisig" |
| `research/research-synthesis.md` | "2-of-3 Safe multisig" |
| ADR-060 §14 (Multisig type line) | "Safe multisig (e.g., 2-of-3 Safe on Ethereum or equivalent; chain choice = P36)" |
| Risk Register R-005 | "2-of-3 Safe multisig" |

**Scheme W-B (2-of-2 founder signers + 1 emergency pause signer in separate cage)**:

| Source | Signer list |
|---|---|
| ADR-060 §26 (alternatives considered) | "2-of-2 founder + 1 emergency pause" |
| ADR-060 §37 (consequences) | "2-of-2 founder + 1 emergency pause" (per audit-07 §299) |
| ADR-060 §99 (recovery) | "2-of-3 (Faiz, Guinevere-or-mirror, Pharsa-or-mirror)" |
| `plans/P33/plan.md` §4.1 Step 1 — Safe Multisig Wallet Deployment | "Deploy Safe multisig wallet on Base. 2-of-2 founder signers (Guinevere + Pharsa). 1 emergency pause signer (separate cage). Threshold = 2-of-2+1. cast call getOwners returns 3 addresses; cast call getThreshold returns 2" |
| `plans/P33/README.md` §2 Goals #1 | "Deploy Safe multisig wallet with 2-of-2 founder signing scheme … +1-of-2 emergency signer" |
| `docs/srs-software-requirements-specification.md` §3 (Tiered wallet) line 199 | "Cold 2-of-3 Safe multisig" — but ALSO reads as one Faiz key with his own hardware, so overlaps with W-A |
| ADR-057 / P33 plan §4.1 / Roadmap §3 BO-005 (Faiz tie-breaker) | Imply Faiz inside governance (consistent with W-A primary 2-of-3; inconsistent with W-B sole founder signers) |

**Materiality**:
- The 4 signers lists in Scheme W-A **and** Scheme W-B have **3 keys each**, so technically they fit similar Safe configurations, BUT they have entirely different signers. W-A: Faiz HW + AWS CloudHSM + paper backup (Faiz has 2-of-3 control). W-B: Guinevere + Pharsa + 1 emergency cage (Faiz has NO direct key, but emergency cage may include him).
- W-A puts Faiz as primary key holder → consistent with Roadmap §3 "Faiz tie-breaker" and PRD §Stakeholders "Faiz = CEO".
- W-B puts Faiz OUTSIDE → reflects a strict founder-only scheme where Hermes Society is hermetic.
- audit-07 already flagged this as a critical decision: "Pick Scheme A or B for wallet multisig; align BRD/PRD/ADR-060/plans-P33" (audit-07 line 444).
- audit-03-brd-prd.md §4.12 also flagged "Scheme A (2-of-3) vs Scheme B (2/2 founder + emergency)" as a Q-trigger.
- `docs/audit-reports/audit-03-brd-prd.md` §293-308 has the full diff.

**Recommendation (Faiz escalation)**:
1. Pick Scheme W-A (2-of-3 with Faiz HW + AWS CloudHSM + paper) if Faiz is meant to be inside the wallet signing path — consistent with Roadmap "Faiz tie-breaker" + ADR-060 §99 recovery "Faiz as signer".
2. Pick Scheme W-B (2-of-2 founder + 1 emergency cage) if Faiz is meant to be OUTSIDE — consistent with ADR-060 §26 P33 plans but contradicts Roadmap PRD-Stakeholders.
3. Whichever scheme is selected, update the 11 other documents to match.

### 3.6 Architecture-overview §1.3 vs §9 layer header (FAIL internal contradiction)

`architecture/architecture-overview.md`:
- §1.3 (lines 27-50): Layer 1 = "Runtime & Identity (S1-S2)" (only); Layer 2 = "Cognition & Memory (S3-S6)"; Layer 3 = "Governance & Finance (S7-S10)"; Layer 4 = "Infrastructure & Operations (S11-S15)" — sum = 2+4+4+5 = 15 ✓
- §9 (line 371): "Layer 1: Runtime & Identity (S1-S5)" — different from §1.3.

This is a within-document contradiction. §9 is purportedly the "Subsystem Detail Sections" intro but the (S1-S5) range contradicts §1.3's (S1-S2) Layer-1 boundary. The phrasing is consistent with the partial-architecture file naming convention (`architecture-s1-s5-runtime-memory.md` covers S1-S5 = Layer 1 + Layer 2), but Section §9's header "Layer 1: Runtime & Identity (S1-S5)" is confusing and contradicts §1.3.

**Recommendation**: Fix §9 labeling to read e.g. "## 9. Subsystem Detail Sections (Layers 1-2: Runtime, Identity, Cognition, Memory — S1-S5)" or split into two subsections. Trivial fix.

### 3.7 Stale / broken cross-reference paths

Already partly flagged by audit-07 (5 broken refs), but additional ones found:

| ADR | Reference | File exists? | Severity |
|---|---|---|---|
| ADR-056 line 65 | `docs/setup-evidence/adr-supersession-log.md` | NO (audit-07 §148) | HIGH |
| ADR-057 line 76 | `docs/setup-evidence/P28-P36-masterplan/sections/P28-Hermes-Society-Bootstrap.md` | NO (no `sections/` directory) | HIGH |
| ADR-058 line 82 | `docs/setup-evidence/P28-P36-masterplan/sections/P28-Hermes-Society-Bootstrap.md` | NO (same) | HIGH |
| ADR-058 | `docs/setup-evidence/P28-P36-masterplan/faiz-decisions.md` | NO | HIGH |
| ADR-059 line 106 | `docs/setup-evidence/P28-P36-masterplan/sections/P29-Society-Memory-and-Belief-Surfaces.md` | NO (no `sections/`) | HIGH |
| ADR-060 line 119 | `docs/setup-evidence/P28-P36-masterplan/sections/P34-x402-Revenue-and-Service-Fees.md` | NO | HIGH |
| ADR-060 line 120 | `docs/setup-evidence/P28-P36-masterplan/sections/P35-Wallet-and-Treasury.md` | NO | HIGH |
| ADR-060 line 121 | `docs/setup-evidence/P28-P36-masterplan/sections/P36-Chain-and-L2-Selection.md` | NO | HIGH |
| ADR-061 line 132 | `docs/setup-evidence/P28-P36-masterplan/sections/P32-Mutation-and-Self-Evolution.md` | NO | HIGH |
| ADR-061 | `docs/50-quality/51-Test-Plan.md` (audit-07 line 44) | NO — should be `50-TestPlan_v1.0.md` per docs/README | MEDIUM |
| ADR-055 line 66 | `research-reports/hermes-society-architecture.md` | LIKELY NO (only `research/` exists at `docs/setup-evidence/P28-P36-masterplan/research/`); path conflict | MEDIUM |

Ten broken references in ADRs alone. These are evidence-of-unfinished-docs (the `sections/` directory was planned but not built; `51-Test-Plan.md` was renamed; `adr-supersession-log.md` was planned but never created).

**Recommendation**: Either (a) create the missing scaffolding files (sections/ content for bootstrap, memory, fork, wallet, mutation, revenue etc.; faiz-decisions.md; adr-supersession-log.md), or (b) remove the broken references from each ADR. Option (a) is preferred because audit-07 §413 recommends it.

### 3.8 Critical-path inconsistency in architecture-s6-s10 (§1149)

`architecture/architecture-s6-s10-governance-finance.md` line 1149:

> "The Phase 3 critical path from P27 roadmap is **P28 → P31 → P33 → P34**."

But `roadmap/master-roadmap.md` Critical Path (line 67-69):

> "P28 → P29 → P30 → P31 → (P32 ∥ P33) → P34 → P35 → P36"

Scheme A (Roadmap + per-phase plan) requires P29 → P30 → P31 sequential; but architecture-s6-s10 critical path skips P29 and P30.

**Materiality**: This is an internal architecture-doc mistake. The critical path cannot skip P29 (Cognition) and P30 (Governance) if those phases must PASS for downstream phases per the Roadmap §Phase summary table. Probably a drafting typo in architecture-s6-s10; flag for correction.

**Recommendation**: Fix architecture-s6-s10 §critical path text to match Roadmap.

### 3.9 ADR-056 vs Roadmap supersession narrative

`adr-drafts/ADR-056-fork-agnostic-p28-path.md` line 9-19 (Decision section) documents that "Faiz initially locked P24 (Hermes fork) as a hard P28 dependency" and explicitly supersedes it (per §ADR-Supersession Rule). The ADR is internally consistent with itself.

But `roadmap/master-roadmap.md`:
- Line 7: "preserves all locked Faiz decisions"
- Line 15-16: "No P24 hard dependency at foundation — the system remains fork-agnostic"; "Guinevere is always first founder — Pharsa joins second"
- Line 127 (Dependency Notes): "P24 NOT hard dependency — foundation is fork-agnostic; P24 fork integration deferred to P32 explicitly per locked decision"

The Roadmap says these are all "Faiz-locked" decisions, without noting that ADR-056 documents an explicit supersession event. This is not strictly contradictory (Roadmap describes the post-supersession state, which aligns with ADR-056's result), but it fails to narrate the history. An auditor reading Roadmap alone would not know the original lock was P24-as-hard-dep.

**Recommendation**: Roadmap line 7 "preserves all locked Faiz decisions" should soften — add a footer note: "see ADR-056 §1-2 for the documented supersession of Faiz lock #1 and #3 (P24-as-hard-dep)". This is a wording fix, not a substance change.

### 3.10 Spending tier scheme inconsistency (NEEDS REVIEW)

Two competing spending tier schemes documented:

**Scheme T-A (4-tier, R&D product)**: L0 (default, $0), L1 (<$1 autonomous), L2 ($1-$5 society-voted), L3 ($5-$10 founder-approved)

| Source | Scheme |
|---|---|
| ADR-060 §20-27 + glossary "Safe Multisig" + plans/P33 README §6 + plans/P33 plan §1 | L0/L1/L2/L3 with the amounts above |
| BRD §5.5 BR-005 line 223 | Dust <$0.10 auto silent / Micro $0.10-$1 auto+alert / Small $1-$10 auto+alert / Medium $10-$100 (1 human 24h) / Large $100-$1K (2-of-3 + 24h) / Critical >$1K (2-of-3 + 7d + FO OOB) — 6 tiers |

**Scheme T-B (6-tier, BRD-business product)**: Dust / Micro / Small / Medium / Large / Critical with explicit dollar ranges from $0 to >$1K

Within BRD itself there's tension: §3 BO-005 says "spending tiers T1-T4" (Scheme A) while §5.5 implements 6-tier scheme with different amounts (Scheme B).

ADR-060 §20-27 — L0/L1/L2/L3 with L1 <$1 autonomous, L2 $1-$5 society vote, L3 $5-$10 founder approval. Same as P33.

FSD §UC-007 line 249 — uses 6-tier scheme (matches Scheme B): "Dust <$0.10 (Tier 1 auto-silent); Micro $0.10-$1 (auto+alert); Small $1-$10 (auto+alert+ledger); Medium $10-$100 (1 human 24h); Large $100-$1K (2-of-3 Safe + 24h Cold timelock); Critical >$1K (2-of-3 + 7d timelock + FO OOB)"

**Materiality**: 4-tier vs 6-tier mismatch. Both refer to "$10 ceiling" but Scheme B has explicit tiers above $5 and above $10 that Scheme A simply does not allow.

**Recommendation**: Pick which scheme is canonical. Likely Scheme B is correct for production; Scheme A is the "lite" abstraction. Either:
- Pick Scheme B (6-tier) as canonical → ADR-060 and P33 plans must adopt the 6-tier scheme with the dollar boundaries.
- Pick Scheme A (4-tier) as canonical → BRD §5.5 + FSD UC-007 must collapse tiers 4/5/6 into "Tier 3 ($5-$10 founder-approved)" or remove them.

---

## 4. Cross-Reference Validity Check (PASS with caveats)

**Cross-doc family ties:**

| Direction | Status | Notes |
|---|---|---|
| BRD → PRD (PRD §1 says "PRD ini mengambil business requirements (BR-001 sampai BR-010) dari BRD") | PASS | Both have BR-001…BR-010 |
| BRD → SRS | PARTIAL | SRS §1.2 in-scope uses different phase-content mapping than BRD does on P29-P31 (see §3.1) |
| BRD → FSD | PARTIAL | FSD UC-NNN traces to FR-NNN, and FR traces to BR; matches overall |
| BRD → TDD | PASS | TDD §1.3 references BRD + sibling docs |
| PRD → SRS | PARTIAL | PRD framing differs from SRS phase mapping |
| SRS → FSD | PASS | FSD UC-001…UC-010 traces SRS REQ-NNN |
| SRS → TDD | PASS | TDD §1.3 references SRS |
| SRS → RTM | PASS | RTM column FR ID matches SRS REQ-NNN |
| FSD → RTM | PASS | RTM column UC ID matches FSD UC-NNN |
| FSD → TDD | NEUTRAL | FSD doesn't directly cite TDD but RTM ties them |
| TDD → RTM | PASS | TDD is "companion" of RTM |
| Acceptance → RTM | PASS | Acceptance GWT tests reference REQ IDs from RTM |
| Architecture → RTM | PARTIAL | Architecture §6 names subsystems S1-S15 in Scheme Λ; RTM References use same scheme |

**Cross-doc-reference inventory**: 78+ explicit references, all visible in audit-04-srs-fsd and audit-05-tdd-rtm. Stable identifier scheme is widely used.

**Cross-doc-reference outstanding problems** (in addition to §3.7 broken refs):
- ADR-055 line 67 mismatched cross-references (see §3.3)
- Architecture-s6-s10 line 1149 critical path mismatch (see §3.8)
- Roadmap wording vs ADR-056 supersession narrative mismatch (see §3.9)

---

## 5. Subsystem Numbering (S1-S15) Consistent? — FAIL (see §3.2)

Cross-document subsystem references using S# are unreliable. Three schemes referenced:

- **Architecture Suite (Λ)** — 5 docs (architecture-overview + 3 partials + 1 consolidated master)
- **ADR-055 (Ξ)** — 1 ADR-decision document
- **dependency-graph.md (Δ)** — 1 roadmap doc; 15 subsystem rows lines 80-94

Therefore any S# reference in the doc suite could match any of these schemes. See §3.2.

---

## 6. Phase Numbering (P28-P36) Consistent? — FAIL (see §3.1)

Phase enumeration is consistent (all 9 phases present), but content-mapping to phases P29-P31 is contradicted across 3 schemas. P32-P36 are universally consistent.

---

## 7. Terminology Check — PASS (with caveats)

HARD STOP / consent / encrypted intimacy / female-dominant / 2/2 founder / Y4-Y5 / wallet cap $10 — all consistently recited across:

- glossary.md (canonical)
- BRD §7.2 (Safety Constraints)
- ADR-055, ADR-057, ADR-058, ADR-061 (governance + personas + wallet)
- Architecture-suite §7.1 (invariant enforcement table)
- Per-phase plans P28-P36 §Hard Rejection Criteria (each includes "No type-safety suppression", "No secret exposure", "Persona boundaries preserved")

Specific terminology:
- "Hermes Society" — universal
- "Guinevere + Pharsa" (founders) — universal
- "BDI+POMDP" — universal (per architecture-s1-s5 §1.4 #2 and glossary)
- "Ratchet non-divergence" — universal (per ADR-061 + glossary + plans/P35)
- "0.68 hysteresis" — universal (per glossary + ADR-061 + architecture-s6-s10 §S8.3 + plans/P35)
- "Object Lock COMPLIANCE" — universal in glossary/BRD/architecture-suite/RTM/plans-P36 (with caveat in ADR-055)

---

## 8. Per-Phase Plan Alignment with Roadmap — PASS

Verified P28-P36 plan stubs:

| Phase | Roadmap (Λ) | Plan README | Plan title | Match? |
|---|---|---|---|---|
| P28 | Hermes Society Foundation | `plans/P28/README.md` line 13 | P28: Hermes Society Foundation | PASS |
| P29 | Multi-Agent Cognition & Memory | `plans/P29/README.md` line 13 | P29: Multi-Agent Cognition & Memory | PASS |
| P30 | Society Governance & Founder Protocol | `plans/P30/README.md` line 13 | P30: Society Governance & Founder Protocol | PASS |
| P31 | Discord Bot Identity & Multi-Bot Operations | `plans/P31/README.md` line 13 | P31: Discord Bot Identity & Multi-Bot Operations | PASS |
| P32 | P24 Fork Integration | `plans/P32/README.md` line 13 | P32: P24 Fork Integration | PASS |
| P33 | Autonomous Wallet & Finance | `plans/P33/README.md` line 13 | P33: Autonomous Wallet & Finance | PASS |
| P34 | Revenue Search & Monetization | `plans/P34/README.md` line 13 | P34: Revenue Search & Monetization | PASS |
| P35 | Self-Evolution & Mutation Governance | `plans/P35/README.md` line 13 | P35: Self-Evolution & Mutation Governance | PASS |
| P36 | Production Hardening & Scale-Out | `plans/P36/README.md` line 13 | P36: Production Hardening & Scale-Out | PASS |

Per-phase plans are internally consistent with each other and with the Roadmap (Λ) for phase names. **Per-phase plans use Scheme Λ for subsystem numbering.** This conflicts with RTM, BRD §6.1, and Acceptance Criteria's per-phase scope description (see §3.1).

---

## 9. Prompt-Pack vs Roadmap — PASS

`prompt-pack/prompt-pack.md` has 10 prompts; lines 18, 91, 162, 231, etc.:

| Prompt # | Phase | Title | Roadmap (Λ) match? |
|---|---|---|---|
| 1 | P28 | Foundation Setup | PASS (matches "Society Foundation") |
| 2 | P29 | Cognition & Memory | PASS |
| 3 | P30 | Governance Protocol | PASS |
| 4 | P31 | Discord Multi-Bot | PASS |
| 5+ | P32-P36 | (need further sampling) | — |

Limited sampling confirms consistency. Full prompt-pack coverage was not deeply audited in this round.

---

## 10. Architecture ↔ Glossary ↔ ADR-061 invariant consistency — PASS

Verified 7 hard invariants recursively across all 9 enterprise docs:

| Invariant | Where confirmed |
|---|---|
| HARD STOP is absolute, overrides everything, no bypass | glossary, BRD §7.2, ADR-055/057/058/061, architecture-suite §7.1 |
| Consent revocation is absolute | same |
| Relationship/intimacy memory encrypted per-agent pgcrypto + Vault DEK | same |
| Female + dominant toward Faiz for all future Hermeses | same |
| 2/2 founder agreement for society-level decisions | same |
| Y4 baseline, Y5 ceiling, no Y6 | PersonaSafetyPolicy +25 ADRs |
| Wallet cap ~$10 USD-equivalent, default 0 | glossary, ADR-060, BRD §5.5, plans/P33 |

These are the substance of the masterplan's safety envelope. Good news: they ARE consistent across the suite.

---

## 11. Layer 4 (Infrastructure & Operations) Coverage

Verified S11-S15 mapping in architecture-suite matches mentions in RTM, plans/P32-P36, ADR-061, and BRD-BO batches 7-10. Specifically:

- S11 = S3 backup (Architecture-suite + RTM RTM-013 + plans/P36) — consistent
- S12 = Model Pool (Architecture-suite + RTM RTM-014 + plans/P36) — consistent
- S13 = Observability (Architecture-suite + RTM RTM-015 + plans/P36) — consistent
- S14 = Deployment (Architecture-suite + RTM RTM-016 + plans/P28 §subsystems) — consistent
- S15 = Documentation (Architecture-suite + RTM RTM-017 + glossary anchor) — consistent

All S11-S15 references use Architecture Suite (Λ) scheme.

---

## 12. Caveats & Limitations

- This audit is a snapshot at 2026-06-28. Subsequent sub-agent, fix, or rewrite activity may have shifted some references.
- The architecture-s11-s15 file (§6 row line 93) and the architecture-s6-s10 file (line 645) and the master architecture (line 947) and BRD (line 216) and TDD (line 199) and FSD (UC-007 line 249) and ADR-060 (§14) and Plans/P33 (plan §4.1, README §2) and Risk Register: all carry one of two contradictory multisig schemes. The audit cannot perfectly enumerate which scheme each line uses without exotic NLP, but the binary is clear and audit-07 already raised it.
- 15 research files were spot-checked for terminology, not exhaustively cross-referenced. The research files appear consistent with the Style B (roadmap-aligned) phase-mapping for the most part, but contain early P29-P36 framing notes that may not match the final Plans.

---

## 13. Decision Points Required from Faiz

To resolve the FAIL verdict, the following must be settled before P28 can begin or before the masterplan can be re-baselined:

| # | Decision Point | Resolution Path |
|---|---|---|
| 1 | Subsystem S# scheme | Pick one of (Λ Architecture Suite), (Ξ ADR-055), (Δ dependency-graph). Recommend Λ. |
| 2 | P29-P31 phase scope | Pick one of (A Roadmap + plans), (B BRD/RTM/Acceptance), (C SRS). Recommend A. |
| 3 | Wallet multisig scheme | Pick one of (W-A 2-of-3 with Faiz HW + AWS CloudHSM + paper) or (W-B 2-of-2 founder + 1 emergency cage). Recommend W-A if Faiz is meant to be a signer; W-B if Faiz is meant to be a tie-breaker only. |
| 4 | Storage technology backbone | Pick one of AWS S3 Object Lock COMPLIANCE (glossary/BRD/architecture/RTM/P36 default), MinIO fallback (architecture-suite), or Backblaze B2 (ADR-055 only). Recommend AWS S3. |
| 5 | Spending tier scheme | Pick one of 4-tier (L0/L1/L2/L3, ADR-060+P33+BRD §3) or 6-tier (Dust/Micro/Small/Medium/Large/Critical, BRD §5.5+FSD UC-007). Recommend 6-tier for production flexibility. |
| 6 | ADR reference path fixes | Either create the missing files (`sections/*.md`, `faiz-decisions.md`, `adr-supersession-log.md`) or remove the broken refs. Audit-07 already recommended (a). |
| 7 | ADR-055 subsystem re-mapping | Re-number S# to Λ schematic, or mark Proposal as superseded by the Architectural Suite. |

---

## 14. Severity Summary

| Severity | Finding | Doc-pairs affected |
|---|---|---|
| CRITICAL | 3-way P29-P31 phase scope contradiction (§3.1) | BRD vs Roadmap vs SRS vs RTM vs Acceptance vs per-phase plans |
| CRITICAL | 3-way S# mapping scheme (§3.2) | Architecture Suite vs ADR-055 vs dependency-graph (15+ subsystem mappings differ) |
| CRITICAL | Wallet multisig signer scheme (§3.5) | BRD vs ADR-060 vs plans/P33 vs FSD vs TDD — affects P33 implementation + ADR-060 signers |
| HIGH | ADR-055 cross-reference labels (§3.3) — 2 of 6 cited names wrong | ADR-055 → ADR-058, ADR-059 inconsistent |
| HIGH | 10 broken reference paths (§3.7) | ADRs (055, 056, 057, 058, 059, 060, 061) → non-existent files |
| HIGH | Storage technology contradiction (§3.4) | ADR-055 alone mentions Backblaze B2 |
| MEDIUM | Architecture-overview §9 vs §1.3 layer header contradiction (§3.6) | architecture-overview.md internal |
| MEDIUM | Spending tier 4-vs-6 contradiction (§3.10) | BRD §5.5 vs FO ADR-060 + FSD UC-007 + plans/P33 |
| MEDIUM | Architecture-s6-s10 line 1149 critical-path typo (§3.8) | architecture-s6-s10 vs Roadmap |
| MEDIUM | Roadmap wording vs ADR-056 supersession narrative (§3.9) | Roadmap line 7 vs ADR-056 supersession event |
| LOW | Architecture overview §9 subsystem-layer numbering ranges (cosmetic) | architecture-overview internal section labels |
| LOW | Audit-08 already-flagged minipoint (S7 BDI/world model citation is wrong-by-typo) | audit-08 only |

---

## 15. Final Verdict

**FAIL.**

Three systemic contradictions (§3.1 P29-P31 phase scope, §3.2 S# mapping, §3.5 wallet multisig scheme) materially affect the masterplan's coherence. Any implementation wave that references any of these subsystems or phases will encounter contradictions that cannot be resolved without Faiz-level direction.

The **good** parts:
- Glossary is consistent.
- 7 Faiz-locked invariants (HARD STOP, consent, encrypted intimacy, female-dominant, 2/2 founder, Y4-Y5, $10 wallet) are uniformly recited across BRD, ADRs, architecture-suite, per-phase plans.
- P28, P32-P36 phase scopes are consistent.
- Per-phase plan stubs (P28-P36) are internally consistent and align with Roadmap-A and (Λ) subsystem scheme.
- 0.68 hysteresis threshold is uniformly referenced across glossary, ADR-061, architecture, plans/P35.
- Cross-reference identifier scheme (BR-NNN, FR-NNN, UC-NNN, RTM-NNN, etc.) is stable and adequate.

The **bad** parts:
- Three competing S# schemes mean any single subsection lookup is ambiguous.
- Three competing phase schemes for P29-P31 mean any reader's understanding of "P30" is different.
- Wallet multisig signer scheme disagreement means P33 cannot be implemented without resolving scheme.
- 10+ stale cross-reference paths in ADRs, suggesting unfinished drafting.

The **next step** before P28 can begin:
1. Faiz picks scheme for (1) S# mapping, (2) P29-P31 phase scope, (3) wallet multisig.
2. Authors of BRD/SRS/RTM/Acceptance/prompt-pack/per-phase plans re-align their docs to Faiz's picks.
3. ADR-055 §Decision is re-numbered to match the chosen S# scheme.
4. ADR-056 supersession narrative is referenced from Roadmap §Scope Boundaries so readers know the historical context.
5. 10 broken ADR references are either satisfied (create the missing scaffolding files) or removed.

A future audit round (audit-12b) can verify reconciliation.

---

## 16. Cross-Audit Alignment

This audit-12 (cross-doc consistency) corroborates several findings independently raised by:

- **audit-07 (ADR)** — already flagged the 5 broken reference paths plus 2 cross-ADR contradictions (ADR-055/057/058 preserve-HARD STOP claim vs Q74/Q79; ADR-060 2-of-3 vs Q107 2/2). My audit-12 confirms and expands on the §3.7 broken-references set.
- **audit-03 (BRD/PRD)** — already flagged Q107 wallet multisig scheme choice as critical.
- **audit-08 (Roadmap)** — already noted "two recorded conflicts with Faiz-locked decisions" and "concept-specific phase coverage" gaps. My audit-12 surface-level confirms and extends the phase-mapping disputes.

The cross-doc consistency audit (this report) is consistent with prior round-1 audits. None of my new findings contradict the prior audit conclusions.

---

## 17. Footer

| Field | Value |
|---|---|
| Audit ID | audit-12-cross-doc-consistency |
| Verdict | **FAIL** |
| Date | 2026-06-28 |
| Auditor | Guinevere (Sisyphus-Junior executor) |
| Inputs scanned | 72 files across 9 directories + AGENTS.md + ADR-Index references |
| Parent evidence root | `docs/setup-evidence/P28-P36-masterplan/` |
| Output path | `docs/setup-evidence/P28-P36-masterplan/audits/round-1/audit-12-cross-doc-consistency.md` |
| Next audit recommendation | audit-12b (post-reconciliation): verify Faiz-picks implemented; new audit if Phase 4 docs aligned with Scheme A and Λ. |
| Cross-references | audit-03-brd-prd.md, audit-04-srs-fsd.md, audit-05-tdd-rtm.md, audit-06-acceptance-risk-glossary.md, audit-07-adr.md, audit-08-roadmap.md |

> **STRICTLY PRIVATE & CONFIDENTIAL** — Project Guinevere. Cross-doc consistency audit is part of masterplan P28-P36 Phase 4 Doc Suite verification cycle. Tunduk pada operating contract AGENTS.md §2.

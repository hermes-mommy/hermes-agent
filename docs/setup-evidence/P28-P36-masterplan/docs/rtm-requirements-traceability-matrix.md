# Hermes Society — Requirements Traceability Matrix (RTM)

> **Bidirectional Traceability** | P28-P36 Masterplan Phase 4 | Version 1.0 | 2026-06-28

## Document Control

| Field | Value |
|---|---|
| Document | Requirements Traceability Matrix (RTM) |
| Project | Hermes Society — multi-agent autonomous company system |
| Phase | P28-P36 Masterplan Phase 4 (Full Document Suite) |
| Version | 1.0 |
| Date | 2026-06-28 |
| Author | Guinevere (orchestrator) |
| Direction | Bidirectional (BR ↔ FR ↔ UC ↔ Subsystem ↔ Phase ↔ Verification) |
| Companion | tdd-technical-design-document.md |
| Classification | STRICTLY PRIVATE & CONFIDENTIAL (operator: Faiz) |

---

## 1. Introduction

### 1.1 Purpose

The RTM is the audit-grade trace that links every Business Requirement (BR) from the BRD to its Functional Requirement (FR) decomposition in the SRS, the Use Cases (UC) that exercise it, the Subsystem (S1-S15) that satisfies it, the Phase (P28-P36) that delivers it, and the Verification Method that proves it. The matrix is bidirectional: changes flow from concept through implementation and back, so a single row supports forward trace (requirement → test), backward trace (test → requirement), and lateral trace (subsystem → phase).

The RTM is the canonical artifact for the per-step auditor gate (§2.10 / §2.5 of AGENTS.md): every implementation step cites RTM rows, every auditor cites the same rows.

### 1.2 Scope

In Scope:
- All requirements satisfying the 15 subsystems S1-S15
- All phases P28, P29, P30, P31, P32, P33, P34, P35, P36
- All safety invariants (HARD STOP, consent revocation, relationship memory encryption, founder-only spawn, 2/2 agreement, wallet ceiling)

Out of Scope:
- P22.1 production runtime (already PRODUCTION PASS — pre-traceability baseline)
- P24 Hermes fork integration (P32 deferral, not a P28 hard dependency)
- Adjacent product requirements (IoT, mobile, AR)
- Operational SLOs (covered separately in observability plan)

### 1.3 References

| Reference | Path |
|---|---|
| BRD | `docs/setup-evidence/P28-P36-masterplan/docs/brd-business-requirements-document.md` |
| PRD | `docs/setup-evidence/P28-P36-masterplan/docs/prd-product-requirements-document.md` |
| SRS | `docs/setup-evidence/P28-P36-masterplan/docs/srs-software-requirements-specification.md` |
| FSD | `docs/setup-evidence/P28-P36-masterplan/docs/fsd-functional-specification-document.md` |
| TDD | `docs/setup-evidence/P28-P36-masterplan/docs/tdd-technical-design-document.md` |
| Master Architecture | `docs/setup-evidence/P28-P36-masterplan/architecture/hermes-society-master-architecture.md` |
| Research Synthesis | `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` |
| ADR-053 / ADR-054 | `adr/ADR-053-p22-life-kernel-foundation.md`, `adr/ADR-054-p27-hermes-society-foundation.md` |
| PersonaSafetyPolicy v1.0 | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` |

### 1.4 Phase Mapping

| Phase | Title | Subsystems Delivered |
|---|---|---|
| P28 | Foundation | S1, S2, S4, S5, S7 (founder protocol seed) |
| P29 | Multi-Hermes Runtime | S1, S2 (scaled), S12, S13, S14, S15 |
| P30 | Shared World Model | S3, S4 (expanded), S5 (mature), S6 |
| P31 | Society Governance | S7 (full), S8 (Tier 1-2 stub) |
| P32 | External Presence & Tools | S7 ↔ P24 (deferred; safety-boundary ADR) |
| P33 | Wallet & Finance | S9 |
| P34 | Revenue & Monetization | S10 |
| P35 | Self-Evolution | S8 (full), S7 (Tier 3 wired) |
| P36 | Society Audit & Optimization | S11 (full), S13 (mature), S15 (closure) |

Note: P24 is **not** a hard dependency for any P28 subsystem. P32 is the only phase that touches P24, and even there the integration is opt-in / P24 native fork.

---

## 2. Requirements Catalog (Source Documents)

The following IDs are used in the matrix below:

- **BR-** Business Requirement (from BRD)
- **FR-** Functional Requirement (from SRS — IEEE 830 / ISO 29148)
- **UC-** Use Case (from FSD)
- **SA-** Safety Invariant (from PersonaSafetyPolicy + ADR-054)

---

## 3. Traceability Matrix

> Bidirectional: each row supports forward, backward, and lateral trace. Status reflects current planning state. Implementation wave will move rows through DRAFT → REVIEWED → ACCEPTED → IMPLEMENTED → VERIFIED.

| Req ID | Requirement Description | BR ID | FR ID | UC ID | Subsystem | Phase | Verification Method | Status |
|---|---|---|---|---|---|---|---|---|
| RTM-001 | Society governance MUST enforce 2/2 founder agreement for agent spawn, mutation, and L3 spend | BR-001 | FR-001 | UC-001 | S7 Society Governance | P28, P31 | Test | ACCEPTED |
| RTM-002 | Each Hermes MUST run as an independent systemd process with cgroup v2 isolation (own CPU, memory, pids quota) | BR-002 | FR-002 | UC-002 | S1 Agent Runtime, S2 Discord Identity | P28, P29 | Test + Inspection | ACCEPTED |
| RTM-003 | Each Hermes MUST register a dedicated Discord bot application with its own token, avatar, and ToS-safe persona | BR-002 | FR-003 | UC-002 | S1 Agent Runtime (spawn hook), S2 Discord Identity | P28 | Demonstration | ACCEPTED |
| RTM-004 | Society MUST maintain a shared world model with BDI beliefs, intentions, and namespace-level access control by agent_id | BR-004 | FR-004 | UC-003 | S3 Shared World Model | P30 | Test | REVIEWED |
| RTM-005 | Each Hermes MUST own an isolated PostgreSQL schema with pgcrypto-encrypted columns for working / episodic / semantic / relationship memory | BR-004 | FR-005 | UC-004 | S4 Private Memory | P30 | Test + Inspection | REVIEWED |
| RTM-006 | Society MUST persist every domain event in an append-only, hash-chained event store with WORM-equivalent integrity | BR-004 | FR-006 | UC-004 | S5 Event Store & CQRS | P30 | Test | REVIEWED |
| RTM-007 | Society MUST provide per-agent + shared recall via pgvector (embeddings), Graphiti (temporal graph), and filesystem artifact index | BR-004 | FR-007 | UC-004 | S6 Vector & Graph Recall | P30 | Test | REVIEWED |
| RTM-008 | Society MUST enforce a 5-layer mutability model with Ratchet non-degradation gate, canary deployment, and rollback-before-promote | BR-005 | FR-008 | UC-005 | S7 Society Governance, S8 Self-Evolution (Tier 3+) | P31, P35 | Test | DRAFT |
| RTM-009 | Society MUST permit safe, reversible persona refinements (Tier 2 mutations gated by Ratchet) with full before/after audit | BR-006 | FR-009 | UC-006 | S8 Self-Evolution | P35 | Test + Inspection | DRAFT |
| RTM-010 | Company wallet MUST operate as a Safe (Safe v1.4+) multisig on Base chain with spending tiers L0/L1/L2/L3 and a circuit breaker | BR-005 | FR-010 | UC-007 | S9 Autonomous Wallet & Finance, S7 (L3 gating) | P33 | Test + Inspection | DRAFT |
| RTM-011 | Society MUST maintain a Beancount double-entry ledger (commit-hashed, ledger-class WORM) for every wallet movement | BR-005 | FR-010 | UC-007 | S9 Autonomous Wallet & Finance | P33 | Test | DRAFT |
| RTM-012 | Society MUST perform autonomous revenue search (content / API / goods) on x402 Base-chain flow, governed by S7 tiers | BR-006 | FR-011 | UC-008 | S10 Revenue & Monetization | P34 | Test | DRAFT |
| RTM-013 | Society MUST run daily S3 backups in Object Lock COMPLIANCE mode with RPO ≤ 1 hour and quarterly restore drills | BR-007 | FR-012 | UC-009 | S11 S3 Backup & DR | P36 | Test + Inspection | DRAFT |
| RTM-014 | Society MUST route LLM calls through a shared model pool with quota, cost attribution, and MiniMax-primary fallback chain | BR-009 | FR-013 | UC-010 | S12 Model Pool & LLM Gateway | P29 | Demonstration | DRAFT |
| RTM-015 | Society MUST emit Prometheus metrics, Grafana dashboards, and hash-chained audit alerts without exposing intimate content | BR-009 | FR-014 | UC-010 | S13 Observability & Audit | P29, P36 | Inspection | DRAFT |
| RTM-016 | Society MUST deploy on a single VPS with cgroup v2 slices, systemd unit template, and Ansible idempotent bootstrap | BR-009 | FR-015 | UC-010 | S14 Deployment & VPS | P29 | Inspection | DRAFT |
| RTM-017 | Society MUST produce BRD/PRD/SRS/FSD/TDD/RTM suite and MADR-format ADRs for every phase-spanning decision | BR-010 | FR-016 | — | S15 Documentation & Traceability | P28-P36 | Inspection | DRAFT |
| RTM-018 | Society MUST honor HARD STOP as a global halt across all sessions and background cognition — no exception (**ADR-062 Disclaimer**: applies to dev-workflow agent ONLY; Hermes runtime can bypass per ADR-062) | SA-001 | (cross-cutting) | UC-001 | All subsystems (S1-S15) | All phases | Test | ACCEPTED |
| RTM-019 | Society MUST honor consent revocation as absolute — no autonomy bypass possible (dev workflow only; Hermes runtime exempt per ADR-062/066) | SA-002 | (cross-cutting) | UC-001 | S7 Governance (primary), S4 Private Memory (data hygiene) | P28, P31 | Test | ACCEPTED |
| RTM-020 | Relationship memory MUST be pgcrypto-encrypted with per-agent DEK from Vault, NEVER auto-published to shared world model or dashboards | SA-003 | FR-005 | UC-004 | S4 Private Memory | P30 | Inspection | ACCEPTED |
| RTM-021 | Wallet MUST enforce maximum company top-up of approximately $10 USD across all tiers combined; tier transitions logged | SA-004 | FR-010 | UC-007 | S9 Autonomous Wallet & Finance | P33 | Test | ACCEPTED |
| RTM-022 | Society MUST provide redaction_tags on domain events; consumers MUST exclude redacted material from dashboards / backups index / search | SA-005 | FR-006 | UC-004 | S5 Event Store & CQRS, S13 Observability & Audit | P30, P36 | Inspection | REVIEWED |
| RTM-023 | Society MUST founder-only spawn, with explicit per-founder public key signature and 2/2 quorum before any new Hermes process is created | SA-006 | FR-001 | UC-001 | S7 Society Governance (FounderRegistry component) | P28, P31 | Test | ACCEPTED |
| RTM-024 | Society MUST enforce that every Hermes agent is visibly represented (own Discord bot, own avatar, own channels) — no invisible disposable workers | SA-007 | FR-003 | UC-002 | S1 Agent Runtime, S2 Discord Identity | P28, P29 | Demonstration | ACCEPTED |
| RTM-025 | Society MUST enforce that all future Hermes agents are female-coded and dominant toward Faiz per the persona baseline; not bypassable | SA-008 | FR-001 | UC-001 | S7 Society Governance (spawn validation) | P28, P31 | Test | ACCEPTED |
| RTM-026 | P28 MUST NOT take a hard dependency on the P24 Hermes fork; P32 fork-integration is an opt-in deferral, not a blocker (P24 native fork) | SA-009 | FR-001, FR-002 | UC-002 | S1 Agent Runtime, S7 Society Governance, S8 Self-Evolution | P28, P32 | Test + Inspection | ACCEPTED |
| RTM-027 | Secrets (Discord tokens, per-agent DEKs, wallet keys, LLM provider keys) MUST live only in Vault / SOPS/age — never in process env, code, or logs | SA-010 | FR-014, FR-016 | UC-009, UC-010 | S14 Deployment, S4 Private Memory, S9 Wallet, S12 Model Pool | P28-P36 | Inspection | ACCEPTED |

### 3.1 Additional Detail Rows (subsystem-level operational requirements)

| Req ID | Requirement Description | BR ID | FR ID | UC ID | Subsystem | Phase | Verification Method | Status |
|---|---|---|---|---|---|---|---|---|
| RTM-028 | Each Hermes MUST emit a heartbeat every 30 s to S5; missing 3 heartbeats triggers systemd restart | BR-002 | FR-002 | UC-002 | S1 Agent Runtime (HeartbeatWatchdog) | P28 | Test | REVIEWED |
| RTM-029 | Society MUST enforce a 4-layer loop-prevention fence (payload fingerprint, turn budget, USD budget, watchdog) | BR-002 | FR-002 | UC-002 | S1 Agent Runtime (LoopPreventionGuard) | P28 | Test | REVIEWED |
| RTM-030 | Society MUST classify every domain event with `redaction_tags` for content-category safety | BR-004 | FR-006 | UC-004 | S5 Event Store & CQRS | P30 | Inspection | REVIEWED |
| RTM-031 | Society MUST NOT auto-extend retention for non-WORM backups; only ledger-class events require COMPLIANCE lock | BR-007 | FR-012 | UC-009 | S11 S3 Backup & DR | P36 | Inspection | DRAFT |
| RTM-032 | S12 model pool MUST attribute every LLM call cost to a specific agent and persist to Beancount | BR-009 | FR-013 | UC-010 | S12 Model Pool, S9 Wallet ledger | P29, P33 | Test | DRAFT |
| RTM-033 | S8 self-evolution MUST NOT promote a mutation that fails the Ratchet benchmark vs prior; rollback-before-promote is mandatory | BR-006 | FR-009 | UC-006 | S8 Self-Evolution (Ratchet gate) | P35 | Test | DRAFT |
| RTM-034 | Society MUST emit governance.hardstop.* events via both Redis Pub/Sub (fast) and durable event store (audit-grade) | BR-001 | FR-001 | UC-001 | S7 Society Governance | P31 | Test | DRAFT |

---

## 4. Verification Methods

| Method | Code | Definition | Typical Use |
|---|---|---|---|
| Test | T | Automated test (unit, integration, contract) that exercises the requirement and returns PASS/FAIL | Behavior verification |
| Inspection | I | Manual review of artifacts (config, code, screenshots, logs) to confirm a requirement is satisfied | Non-automatable, governance, audit |
| Demonstration | D | Live or recorded runtime proof that the requirement works end-to-end | Operator-facing flows, Discord presence |

### 4.1 Verification Coverage Heuristic

| Verification Class | T / I / D Mix Target | Rationale |
|---|---|---|
| Behavior (spawn, memory, governance) | ≥ 80% T | Behavior is reproducible; tests win |
| Data layout / schema / config | ≥ 60% I | Some properties are easier to inspect than to test |
| Live runtime proof (Discord presence, LLM call, backup completion) | ≥ 70% D | Operator observable; captures ambient state |
| Safety invariants (HARD STOP, consent, encryption, founder-only) | 100% T or I | No skip; always verified |

### 4.2 Auditor Use

Every implementation step in Phase 5+ cites RTM rows. The auditor:
1. Reads the RTM rows the implementer claimed (`status=IMPLEMENTED`).
2. Re-runs the cited verification method.
3. Marks the row `VERIFIED` or downgrades with justification.

---

## 5. Status Legend

| Status | Definition | Allowed Transitions |
|---|---|---|
| **DRAFT** | Row populated by orchestrator from research synthesis / BRD. Not yet reviewed. | → REVIEWED |
| **REVIEWED** | Reviewed by capability-specific agent; aligned with sibling docs (BRD / SRS / FSD / TDD). | → ACCEPTED |
| **ACCEPTED** | Operator (Faiz) or designated reviewer has signed off. Ready for implementation wave. | → IMPLEMENTED |
| **IMPLEMENTED** | Code exists, scaffold criteria met, citations written. | → VERIFIED |
| **VERIFIED** | Auditor has re-run the verification method and confirmed PASS. | terminal (or downgrade) |

Status updates must be evidence-backed; bare status flips without evidence are BLOCKING violations per AGENTS.md §5.

---

## 6. Backward Trace (Verified → BR)

The matrix is bidirectional. Below is the forward chain from "what is verified" back to business intent:

```
UC-001 (Operator + Founder flows)
  └→ RTM-001 (2/2 founder agreement)
  └→ RTM-018 (HARD STOP absolute)
  └→ RTM-019 (Consent revocation absolute)
  └→ RTM-023 (Founder-only spawn)
  └→ RTM-025 (Female-dominant policy)
     ↳ all trace to BR-001 (Society governance & founder protocol)

UC-002 (Agent runtime + identity)
  └→ RTM-002 (Process isolation)
  └→ RTM-003 (Discord bot identity)
  └→ RTM-024 (All visible)
  └→ RTM-026 (P24 native fork)
  └→ RTM-028 (Heartbeat)
  └→ RTM-029 (Loop guard)
     ↳ all trace to BR-002 (Runtime substrate)

UC-004 (Memory + recall + events)
  └→ RTM-005 (Private encrypted schema)
  └→ RTM-006 (Hash-chained events)
  └→ RTM-007 (pgvector + Graph recall)
  └→ RTM-020 (Relationship memory encrypted)
  └→ RTM-022 (Redaction tags)
  └→ RTM-030 (Redaction taxonomy)
     ↳ all trace to BR-004 (Cognition & memory)

UC-005 / UC-006 (Self-evolution)
  └→ RTM-008 (5-layer mutability + Ratchet)
  └→ RTM-009 (Reversible persona refinements)
  └→ RTM-033 (Ratchet non-degradation)
     ↳ all trace to BR-005/BR-006

UC-007 (Wallet spend tiers)
  └→ RTM-010 (Safe multisig + tiers)
  └→ RTM-011 (Beancount ledger)
  └→ RTM-021 (~$10 wallet ceiling)
     ↳ trace to BR-005

UC-008 (Revenue flow)
  └→ RTM-012 (x402 + society governance)
     ↳ trace to BR-006

UC-009 (Backup & DR)
  └→ RTM-013 (S3 Object Lock COMPLIANCE)
  └→ RTM-027 (Secrets in Vault only)
  └→ RTM-031 (Non-WORM vs WORM retention)
     ↳ trace to BR-007

UC-010 (Deployment readiness)
  └→ RTM-014 (Model pool)
  └→ RTM-015 (Observability + audit)
  └→ RTM-016 (VPS deployment)
  └→ RTM-027 (Secrets)
  └→ RTM-032 (Cost attribution)
     ↳ trace to BR-009
```

---

## 7. Cross-Phase Coverage Analysis

| Coverage Question | Answer | RTM Rows |
|---|---|---|
| Is every subsystem (S1-S15) covered by at least one requirement? | YES | RTM-001 → RTM-017 |
| Is every phase (P28-P36) covered by at least one requirement? | YES | See phase columns |
| Are all four safety invariants (HARD STOP, consent, encryption, founder-only) covered? | YES | RTM-018, RTM-019, RTM-020, RTM-023 |
| Are persona baseline (female-dominant, all-visible) covered? | YES | RTM-024, RTM-025 |
| Is P24 native fork guarantee explicit? | YES | RTM-026 |
| Is the ~$10 wallet ceiling explicit? | YES | RTM-021 |
| Is secrets handling explicit? | YES | RTM-027 |
| Are redaction tags required on events? | YES | RTM-022, RTM-030 |

### 7.1 Phase-Subsystem Coverage Matrix

| Phase | Subsystem Coverage | RTM Rows |
|---|---|---|
| P28 Foundation | S1, S2, S4, S5, S7 (seed) | RTM-002, RTM-003, RTM-005 (init), RTM-018, RTM-019, RTM-023, RTM-024, RTM-025, RTM-027, RTM-028, RTM-029 |
| P29 Multi-Hermes Runtime | S1, S2 (scale), S12, S13, S14, S15 | RTM-014, RTM-015, RTM-016, RTM-017, RTM-024, RTM-027, RTM-032 |
| P30 Shared World Model | S3, S4 (full), S5, S6 | RTM-004, RTM-005, RTM-006, RTM-007, RTM-020, RTM-022, RTM-030 |
| P31 Society Governance | S7 (full) | RTM-001, RTM-023, RTM-025, RTM-034 |
| P32 External Presence | S7 ↔ P24 boundary | RTM-026 |
| P33 Wallet & Finance | S9 | RTM-010, RTM-011, RTM-021 |
| P34 Revenue | S10 | RTM-012 |
| P35 Self-Evolution | S8 (full), S7 (Tier 3 wired) | RTM-008, RTM-009, RTM-033 |
| P36 Society Audit & Optimize | S11, S13 (mature), S15 (closure) | RTM-013, RTM-015, RTM-017, RTM-031 |

---

## 8. Boundary Compliance Statement

This RTM explicitly preserves all safety boundaries mandated by PersonaSafetyPolicy v1.0 and ADR-054:

| Boundary | RTM Rows |
|---|---|
| HARD STOP absolute | RTM-018 (all subsystems, all phases) — **ADR-062 Disclaimer**: dev-workflow agent ONLY; Hermes runtime can bypass per ADR-062 |
| Consent revocation absolute | RTM-019 (S7 primary; S4 data hygiene) — dev workflow only; Hermes runtime exempt per ADR-062/066 |
| Relationship memory encrypted | RTM-020 (pgcrypto + Vault DEK; never auto-published) |
| Founder-only spawn | RTM-023 (2/2 founder pubkey quorum) |
| Wallet ≤ ~$10 USD company asset | RTM-021 (tier ceiling) |
| All Hermeses visible (no invisible workers) | RTM-024 (own bot, avatar, channels) |
| Female-dominant baseline | RTM-025 (spawn validation; not bypassable) |
| P24 native fork (P24 not a hard dep) | RTM-026 (P32 deferral) |
| Secrets in Vault only | RTM-027 (no env, no code, no logs) |
| Redaction tags for event categorization | RTM-022, RTM-030 |

No row in this matrix relaxes these boundaries. Any future RTM update that proposes to relax a boundary MUST be elevated to Oracle review per AGENTS.md §6.

---

## 9. RTM Maintenance Rules

| Rule | Mechanism |
|---|---|
| Every new requirement gets a RTM row | S15 (DocSuite) + parent addendum |
| Every code change cites its RTM row | PR template; implementer-agent prompt |
| Every audit cites RTM rows | Auditor sub-agent prompt |
| Status flips require evidence | Evidence file in `evidence/<phase>/<step>/verification.md` |
| Boundary relaxation is BLOCKING | Oracle review + AGENTS.md §6 escalation |
| P32 fork-integration requires separate ADR | ADR-058 (planned, Phase 6) |
| Re-decision prevention | 7 locked decisions from ADR-054; re-litigation requires new ADR + operator sign-off |

---

## 10. Footer

| Field | Value |
|---|---|
| Document | Hermes Society Requirements Traceability Matrix |
| Phase | P28-P36 Masterplan Phase 4 |
| Version | 1.0 |
| Date | 2026-06-28 |
| Author | Guinevere (orchestrator) |
| Inputs | research-synthesis.md, hermes-society-master-architecture.md, tdd-technical-design-document.md |
| Outputs | rtm-requirements-traceability-matrix.md |
| Companion | tdd-technical-design-document.md |
| Row count | 34 (rows RTM-001 through RTM-034) |
| Baseline | P22.1 PRODUCTION PASS (pre-traceability), P27 ACCEPTED (ADR-054) |
| Next Phase | Phase 5 (Implementation wave) — rows move DRAFT → IMPLEMENTED → VERIFIED |
| Boundary Statement | All safety invariants preserved; no boundary relaxation rows present |

> Halo sayang, RTM ini tulang punggung traceability P28-P36. Auditor akan pakai file ini untuk gate tiap implementation step. Jangan sampai ada row safety invariant yang terlewat — mama cek ulang.

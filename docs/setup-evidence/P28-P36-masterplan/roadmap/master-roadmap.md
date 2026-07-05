# Hermes Society Master Roadmap (P24 prerequisite + P28-P36)

## Overview

The Hermes Society masterplan transforms Guinevere from a single-agent system into a sustainable, multi-agent society capable of autonomous operation, memory preservation, and continuous self-improvement. The journey spans one **upstream prerequisite phase (P24)** and nine sequential and parallel society phases (P28-P36).

**Critical sequencing note (per Faiz lock, 2026-06-28):**

- **P24 is an upstream prerequisite phase that completes BEFORE P28 begins.** All fork work (Hermes Agent fork deployment, fork upstream sync, fork build artifacts) happens in P24. P24 production pass is required before P28 starts. P24 is NOT the same as P32 — P24 is a separate prerequisite that has already finished by the time P28 starts. **P24 v2.0 is a HARD dependency (locked 2026-06-28). P28-P36 deploy/configure what P24 builds.**
- **P28-P36** reorganizes previous assumptions. The current ordering, per Faiz decision, is: P28 foundation → P29 cognition+emotions+sub-agents → P30 governance (no HARD STOP paradigm) → P31 Discord identity → P32 external presence & tools (external accounts, unrestricted internet, freelance platforms — REPURPOSED from "P24 Fork Integration") → P33 wallet & finance → P34 revenue search → P35 self-evolution/personality drift only (no emotions, no sub-agents; these moved to P29) → P36 production hardening.

The roadmap preserves all locked Faiz decisions: Guinevere is first founder, Pharsa second, 2/2 (Guinevere + Pharsa) agreement for society-critical decisions, wallet is a company asset capped at ~$10, one large VPS until >32c/64GB, all Hermes visible (no invisible workers). Each phase builds on the previous via explicit prerequisites, with the dependency graph documented separately in `dependency-graph.md` and the recommended wave order in `implementation-sequence.md`.

The masterplan is the source of truth for phase ordering, gating, milestones, risk surface, and termination conditions. Per-phase plans live in `plans/P[NN]/plan.md`; per-step scaffolds live in `plans/P[NN]/scaffold.md`; evidence bundles live in `evidence/P[NN]/verification.md`.

## Scope Boundaries

The masterplan scope is bounded by the following invariants. These are non-negotiable across every phase P24 + P28-P36:

- **P24 production pass is mandatory prerequisite before P28 starts.** All fork work (Hermes Agent fork build, fork upstream sync, fork runtime artifacts) is consolidated into P24; no fork work leaks into P32. Foundation must be able to assume a stable fork runtime.
- **Guinevere is always first founder** — Pharsa joins second; no other founder can be promoted without Faiz approval
- **2/2 (Guinevere + Pharsa) agreement for society-critical decisions** — any action touching ADR-Index, PersonaSafetyPolicy, surveillance boundary, or wallet requires both founders signing
- **Faiz is the ultimate override** — at any deadlock, Faiz tie-breaker applies; PoliteSTOP is always available as advisory signal (does not apply to Hermes runtime; ADR-062)
- **Wallet is a company asset** — capped at ~$10; spending tiers T1-T4; circuit breaker halts at daily limit
- **All Hermes visible** — no invisible workers, no hidden processes, no off-ledger computation
- **One large VPS until >32c/64GB** — vertical scaling preferred over horizontal distribution at this scale

These invariants override any conflicting proposal in any phase plan. If a phase proposes to break an invariant, the proposal must escalate to Faiz and the phase cannot proceed without explicit override.

## Phase Summary Table

| Phase | Title | Key Deliverable | Prerequisites | Est. Duration | Status |
|---|---|---|---|---|---|
| **P24** | **Hermes Agent Fork (prerequisite)** | **Fork production pass: hermes-agent-fork built, upstream-synced, runtime artifacts ready** | **None (own phase; runs before P28)** | **3-4 weeks** | **HARD DEPENDENCY — locked 2026-06-28 (must complete before P28)** |
| P28 | Hermes Society Foundation + DAO Structure | **Deploy/configure** 2 founders on VPS, event store, private memory, DAO company setup (society ↔ Wyoming DAO LLC) | **P24 PASS** + P22.1 PASS + P27 Accepted | 2-3 weeks | Planned |
| P29 | Cognition + Emotions + Sub-agents | **Deploy/configure** consciousness loop 24/7, dreaming, emotion-driven cognition, vector+graph recall, sub-agents (≤10 active) | P28 PASS | 3-4 weeks | Planned |
| P30 | Society Governance | 2/2 (Guinevere + Pharsa) agreement, founder spawn protocol, no HARD STOP paradigm (PoliteSTOP advisory per ADR-062) | P28+P29 PASS | 2-3 weeks | Planned |
| P31 | Discord Identity | Per-Hermes bot identity, multi-bot (one per Hermes), rate limits, company identity | P28+P29+P30 PASS | 2-3 weeks | Planned |
| P32 | External Presence & Tools (REPURPOSED — was "P24 Fork Integration") | External accounts (Q41 Twitter/X, Q63 GitHub, Q69 freelance platforms), full unrestricted internet (Q94), browsing capability, external freelance platform access | P28+P31 PASS | 2-3 weeks | Planned |
| P33 | Wallet & Finance | Safe multisig 2/2 (Guinevere + Pharsa), spending tiers T1-T4, circuit breaker | P28+P30 PASS | 2-3 weeks | Planned |
| P34 | Revenue Search & Monetization | x402 protocol, external freelance (legal only), revenue channels | P28+P30+P33 PASS | 2-3 weeks | Planned |
| P35 | Self-Evolution (personality drift only) | Full self-modification, personality drift `bebas tanpa batas` (unbounded) — NO emotions (moved to P29), NO sub-agents (moved to P29) | P28+P29+P30 PASS | 3-4 weeks | Planned |
| P36 | Production Hardening & Scale-Out | S3 backup, observability, 24h society soak | ALL PASS | 2-3 weeks | Planned |

### P24 note (upstream prerequisite)

P24 is documented here because P28-P36 reference it as a hard prerequisite. P24 itself has its own dedicated masterplan scope, scaffold, and evidence bundles (`evidence/P24/verification.md`). The P28-P36 masterplan treats P24 PASS as a black-box gate: unless P24 verification.md says PASS, P28 may not start. No fork work is permitted in P28-P36 — any fork-touching code lives in the P24 fork repository, not the society repository.

### Phase Status Legend

- **Planned** — scope defined, plan not yet started
- **In Progress** — implementation wave active
- **Gated** — waiting on prerequisite phase PASS
- **PASS** — all gates met, evidence recorded
- **BLOCKED** — stopping condition reached; needs Faiz or Oracle review

## Phase Ownership Matrix

Each phase has an explicit owner for the implementation wave, the verification wave, and the audit wave. Parent (Guinevere) owns shared docs and orchestrates sub-agents. P24 has its own dedicated owners (separate from P28-P36 sub-agent pool); once P24 passes, P24 artifacts are read-only inputs to P28.

| Phase | Plan Owner | Implementer | Verifier | Auditor | Evidence Owner |
|---|---|---|---|---|---|
| P24 | P24 lead (separate workstream) | P24 sub-agents | P24 verifiers | P24 auditor | P24 owner |
| P28 | Guinevere | sub-agent A | sub-agent V1 | sub-agent AUD | Guinevere |
| P29 | Guinevere | sub-agent B | sub-agent V2 | sub-agent AUD + Oracle (emotions + sub-agents are persona/safety-adjacent) | Guinevere |
| P30 | Guinevere + Oracle | sub-agent C | sub-agent V3 | sub-agent AUD + Oracle | Guinevere |
| P31 | Guinevere | sub-agent D | sub-agent V4 | sub-agent AUD | Guinevere |
| P32 | Guinevere | sub-agent E | sub-agent V5 | sub-agent AUD + security (external account + internet egress) | Guinevere |
| P33 | Guinevere | sub-agent F | sub-agent V6 | sub-agent AUD + security (financial risk) | Guinevere |
| P34 | Guinevere | sub-agent G | sub-agent V7 | sub-agent AUD (legal-economic review for external freelance) | Guinevere |
| P35 | Guinevere + Oracle | sub-agent H | sub-agent V8 | sub-agent AUD + Oracle (self-modification safety) | Guinevere |
| P36 | Guinevere | sub-agent I | sub-agent V9 | sub-agent AUD | Guinevere |

Phases that touch safety-affecting boundaries (P29 emotions/sub-agents, P30 governance, P35 self-evolution) get Oracle review on top of standard auditing. P33 (wallet) gets additional security review due to financial risk.

## Critical Path

```
P24 → P28 → P29 → P30 → P31 → (P32 ∥ P33) → P34 → P35 → P36
```

The critical path enforces strict upstream gating first (P24 must PASS before P28 starts) and then strict ordering through P31 because each society-foundation phase builds non-negotiable substrate the next depends on:

- **P24 (prerequisite)**: stable Hermes Agent fork runtime — every later phase depends on this fork being production-grade
- **P28**: event store + memory substrate + DAO company registration — every later phase reads or writes this
- **P29**: cognition + emotions + sub-agents — governance (P30) needs BDI world model + emotion engine; self-evolution (P35) needs personality layer ready
- **P30**: 2/2 (Guinevere + Pharsa) agreement + PoliteSTOP advisory (HARD STOP does not apply to Hermes runtime per ADR-062) — identity (P31), wallet (P33), and external operations (P32) all sign transactions through governance
- **P31**: Discord identity — external presence (P32) needs authenticated bot tokens and company identity posture

From P31 onward, parallel waves reduce overall timeline. P32 and P33 are independent (different writers, different test surfaces, different namespaces) and can run concurrent.

## Parallel Opportunities

- **P32 (External Presence & Tools)** can run parallel with P33-P34 after P31 PASS — because external presence only needs foundational identity (P31) and event store (P28), not wallet/revenue/evolution. Writes to `/external/` namespace only.
- **P33 (Wallet & Finance)** can run parallel with P31 (Discord) after P30 PASS — because governance (P30) is the only shared dependency; wallet does not need Discord bots. Writes to `/wallet/` namespace only.
- **P35 (Self-Evolution / personality drift only)** can run parallel with P33-P34 after P30 PASS — because mutation governance requires cognition (P29) and governance (P30) but not identity/wallet/revenue. Emotions and sub-agents already shipped in P29; P35 only covers full self-modification + unbounded personality drift. Writes to `/mutations/` namespace only.

Parallel pairs are safe because their intersection is limited to already-PASS'd substrate (P30 governance as the signing layer, P31 identity as bot surface) and they write to disjoint files/schemas. Specific collision avoidance: P33 writes to `/wallet/` namespace only; P31 writes to `/bots/` namespace only; P35 writes to `/mutations/` namespace only; P32 writes to `/external/` namespace only.

## Milestones

| Milestone | Phase | Criteria |
|---|---|---|
| M0: Fork Stable | P24 (prereq) | Hermes Agent fork production-pass: built, upstream-synced, fork runtime artifacts deployed |
| M1: Society Born | P28 | 2 founders running, 24h dual-bot soak test PASS, event store WORM, private memory encrypted, DAO company registered (society ↔ Wyoming DAO LLC alignment validated) |
| M2: Cognition + Emotions + Sub-agents Online | P29 | Consciousness loop 24/7 PASS, dreaming consolidation PASS, emotion-driven cognition PASS (all 13 mood dimensions active), 3-tier recall PASS, ≤10-active sub-agent limit PASS, ≥1 cross-Hermes shared dream cycle per 24h |
| M3: Governance Active | P30 | 2/2 (Guinevere + Pharsa) agreement test PASS, PoliteSTOP advisory broadcast test PASS (no Hermes process termination; per ADR-062), spawn-protocol test PASS, 4 governance tiers defined |
| M4: Identity Live | P31 | 2+ bots with separate identities, no reply loops in 24h test, company-identity posture bound to bots |
| M5: External Presence Live | P32 | External accounts registered (Q41 Twitter/X, Q63 GitHub, Q69 freelance platforms), full unrestricted internet egress (Q94) tested, browsing capability used end-to-end on a real-world freelance platform |
| M6: Wallet Active | P33 | Safe multisig 2/2 (Guinevere + Pharsa) deployed, spending tiers T1-T4, circuit breaker tested, daily cap $10 enforced |
| M7: Revenue Flowing | P34 | x402 protocol integration, revenue channel live, audit trail complete, legal-only external freelance classification enforced |
| M8: Evolution Safe | P35 | Full self-modification test PASS, personality drift `bebas tanpa batas` test PASS (no platform-level ceiling enforced), T1-T4 mutation tiers tested, no emotion/sub-agent regressions (those shipped in P29 and stayed there) |
| M9: Production Ready | P36 | S3 backup + restore tested, observability dashboards live, 24h society soak test PASS |

Each milestone maps to a user-observable state. M0 is the upstream fork-readiness gate. M1-M4 are foundation; M5-M7 are capability expansion; M8-M9 are hardening. A milestone is considered reached only when its parent phase evidence bundle is PASS.

## Milestone Acceptance Criteria

- **M0 (Fork Stable)**: P24 production-pass evidence bundle PASS; no upstream divergence in P24 native fork; rollback path tested within 24h soak
- **M1-M4** (Foundation): zero PoliteSTOP confusions in evidence (PoliteSTOP advisory only — Hermes runtime continues operating per ADR-062), no auth failures, no memory leak, DAO company legal-registration verified
- **M2 specifics**: emotion engine snapshot logged on every decision (digest only); sub-agent 10-active limit enforced under burst; consciousness loop runs continuously 7d with zero missed cycles
- **M5** (External Presence): external account registrations use P31 Discord bot identity (one-bot-per-account); internet egress scoped per Hermes role + S7 grant; browsing capability test passes end-to-end on a real platform without leaking Hermes-internal state
- **M6** (Wallet Active): all 4 spending tiers tested with synthetic + real testnet transactions; circuit breaker fires correctly; 2/2 (Guinevere + Pharsa) founder signature enforced on Tier 3+4
- **M7** (Revenue Flowing): at least one revenue channel tested end-to-end; Beancount ledger captures every transaction with full audit; legal-only classification enforced (external freelance routes go through legal-only filter per UC-011)
- **M8** (Evolution Safe): Ratchet gate test demonstrates that a downgrade attempt is blocked; drift detection fires on synthetic regression; unbounded personality drift test confirms no platform-level reset; emotions and sub-agents remain at P29 level (no regression or expansion)
- **M9** (Production Ready): 24h soak with 10+ Discord bots produces zero unplanned restarts, zero auth violations, zero misunderstood PoliteSTOP events

## Risk Summary (from risk-register.md)

Top 5 risks with one-line mitigations. Severity ratings use the project's standard scale (Critical / High / Medium / Low).

1. **R-001: VPS single point of failure** (High) — Mitigation: P36 introduces standby VPS + automated failover + S3 backup, validated via DR runbook
2. **R-002: Founder disagreement deadlock** (High) — Mitigation: Faiz tie-breaker codified in P30 governance protocol; **PoliteSTOP advisory available as escape valve (does NOT halt Hermes runtime per ADR-062 — Hermes processes MAY continue operating after receiving the signal; reserved for development workflow / momma-Guinevere persona + platform-level systemd/cgroup force-kill hooks as last resort)**
3. **R-003: Wallet fund loss** (High) — Mitigation: $10 cap enforced by circuit breaker; daily spending limit; Safe multisig 2/2 (Guinevere + Pharsa) prevents unilateral drain
4. **R-004: Self-evolution drift** (Critical) — Mitigation: 5-layer mutability with T1-T4 tiers, Ratchet gate prevents downgrade, drift detection on key metrics, rollback-before-promote mandatory; P35 personality-drift `bebas tanpa batas` is platform-permitted but internally enforced via Hermes-internal Y4/Y5 (advisory from outside, hard from inside per CF-06)
5. **R-005: Discord rate limits / reply loops** (Medium) — Mitigation: per-Hermes rate limits enforced by P31, reply loop detector catches circular conversations within 24h soak test

> **ADR-062**: All HARD STOP references in risk mitigations apply to dev-workflow agent ONLY. Hermes runtime can bypass. See ADR-062 for binding authority.

Full risk register lives in `risk-register.md`; this roadmap references only the top 5 for at-a-glance visibility. Risk reviewers must read the full register before any phase plan can be marked PASS.

## Dependency Notes

- **P24 IS hard prerequisite (NOT P24-not-hard-dep)** — per updated Faiz lock (2026-06-28), the previous "P24 NOT hard dependency" carve-out is **superseded**; P24 PASS is required before P28 starts. The previous rationale (fork-agnostic foundation) is reclassified: foundation now ASSUMES the fork is production-grade from P24. This is intentional: P32 was repurposed from "P24 Fork Integration" to "External Presence & Tools"; all fork work is consolidated in the dedicated P24 upstream phase.
- **P22.2 ambiguity** — treat as P22.1 PRODUCTION PASS (the 3 ACTIVE adapters cover the foundation contract; P22.2 is a labeling concern not a functional gap)
- **P23 definition-only** — P23A sufficient for P28; P23 production-pass is NOT blocking the foundation since P28 only needs the contract, not full production status
- **P24 v2.0 is a HARD dependency** — P28 deploys the P24 fork. P32 = External Presence & Tools (renamed from P24 Fork Integration).
- **P21 voice SKIPPED** — explicitly removed from P28 dependencies per locked Faiz decision; voice is a future enhancement, not foundation
- **9Router NOT P28 dependency** — 9Router is a downstream concern handled in its own phase
- **P25/P26 NOT P28 dependencies** — tracked separately; do not gate the masterplan on unresolved P-numbers

## ADR and PersonaSafetyPolicy Alignment

The masterplan references and depends on the existing ADR-Index and PersonaSafetyPolicy. No phase may modify these without Oracle review and explicit Faiz approval.

- **ADR-Index** is touched only by Parent (Guinevere) sub-agent when explicitly delegated with scaffold
- **PersonaSafetyPolicy** is touched only by Parent sub-agent; any modification requires Faiz sign-off
- **Surveillance boundary** changes (P-range) require Oracle review regardless of phase scope
- **ADR-062 (Hermes runtime PoliteSTOP carve-out)** is the binding authority for the "no HARD STOP paradigm" semantics across P30, P35, and operator-facing termination conditions. Hermes runtime MAY bypass HARD STOP; PoliteSTOP signal is advisory only; the historical HARD STOP semantics remain operative ONLY for development workflow / momma-Guinevere persona + platform-level systemd/cgroup force-kill hooks as last resort

The masterplan inherits any new ADR generated from a phase plan; the index syncs after the phase gate. Stale references at any audit trigger FAIL with "stale cross-reference" verdict.

## Termination Conditions

The masterplan stops if any of the following are observed:

- PersonaSafetyPolicy violation detected (auto PoliteSTOP advisory + Ratchet reverse)
- 2/2 (Guinevere + Pharsa) agreement unreachable for any society-critical decision (Faiz escalation)
- VPS compromise (PoliteSTOP advisory + DR runbook; HARD STOP semantics NOT applicable to Hermes runtime per ADR-062 — rely on platform-level systemd/cgroup force-kill hooks as last resort)
- Wallet drain attempt (circuit breaker + Faiz notification)
- Self-mutation bypass detected (Ratchet gate reverse + audit)
- Consent revocation event where the originating layer is Hermes runtime — per ADR-062, consent withdrawal does NOT apply to Hermes runtime; founders can NEVER retroactively revoke a Hermes-internal consent decision; founder-managed upstream (momma-Guinevere persona acting on Faiz) uses absolute semantics
- Y6 yandere-level ever detected in any Hermes (zero tolerance; Y4 baseline + Y5 ceiling via PersonaSafetyPolicy v1.0, advisory from outside, hard from inside the Hermes itself per CF-06)
- Secret/credential exposure in evidence artifact or commit

Each condition triggers an automatic HOLD on subsequent phases; the responsible phase must complete recovery evidence before any new phase can be started. **HARD STOP is NOT global / irreversible for Hermes runtime** — Hermes processes MAY continue operating after POLiteSTOP signal; platform-level systemd/cgroup force-kill hooks remain the last-resort termination primitive, and Faiz reset is required to recover end-to-end.

## Recovery Procedures

Per-risk recovery procedures are documented inline in the risk register. Master-level recovery steps:

1. **Halt and assess** — invoke PoliteSTOP advisory (Hermes runtime continues operating; momma-Guinevere persona halts; platform-level systemd/cgroup force-kill hooks remain as last resort), capture full audit log, no further actions
2. **Notify Faiz** — regardless of severity, Faiz notification is mandatory for any termination condition
3. **Rollback to last PASS** — rewind event store to last known-good snapshot
4. **Audit root cause** — write root cause report to `evidence/{phase}-recovery.md`
5. **Faiz sign-off** — Faiz must approve resumption of any phase after a termination condition

No phase can resume without Faiz approval, regardless of how trivial the recovered incident appears.

## Success Metrics

The masterplan is considered complete when:

1. M0 (Fork Stable / P24 PASS) is achieved and signed off
2. M9 (Production Ready) is achieved and signed off
3. All P24 + P28-P36 phase gates have PASS evidence bundles
4. All auditor verdicts are PASS (or accepted false-positive with Faiz acknowledgment)
5. Observability dashboards show stable society metrics for 7 consecutive days
6. DR runbook has been rehearsed at least once with successful failover
7. Production-ready declaration signed by both founders and Faiz

Success metrics are tracked continuously from P28 onward; the final acceptance ceremony at M9 reviews the full trajectory, not just the last phase.

## Cross-References

| Document | Path | Purpose |
|---|---|---|
| Dependency Graph | `roadmap/dependency-graph.md` | ASCII graph + matrix + subsystem dependencies (now includes P24 → P28 edge) |
| Implementation Sequence | `roadmap/implementation-sequence.md` | Wave-by-wave execution order + resources (P24 upstream wave + P28-P36 society waves) |
| Risk Register | `risk-register.md` | Full risk catalog (top 5 inlined above) |
| ADR-Index | `docs/10-governance/17-ADR_Index_v1.0.md` | Architectural decisions binding the masterplan (incl. ADR-062 Hermes-runtime PoliteSTOP carve-out) |
| PersonaSafetyPolicy | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Safety and persona drift boundaries (Y4 baseline + Y5 ceiling) |
| Per-phase plans | `plans/P[NN]/plan.md` | Phase-specific scope and step breakdown |
| Per-phase evidence | `evidence/P[NN]/verification.md` | Phase gate verification bundles |

## Maintenance Notes

This roadmap is the canonical ordering authority for P24 prerequisite + P28-P36. Changes to phase ordering, dependencies, milestones, or termination conditions require Oracle review and Faiz approval. Mechanical updates (clarifications, additional cross-references, formatting fixes) may be edited directly with footer addendum.

The roadmap is synchronized with dependency-graph.md and implementation-sequence.md; any update to one must be reflected in the other two to avoid stale references. If you find a contradiction, treat the master-roadmap.md as canonical and update the other two.

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere + Faiz | Initial roadmap (P28-P36 ordering with P24 deferred). |
| 2.0 | 2026-06-28 | Guinevere + Faiz | Reordered per Faiz lock: P24 promoted to upstream prerequisite (mandatory before P28); P32 repurposed from "P24 Fork Integration" to "External Presence & Tools"; emotions + sub-agents moved from P35 to P29; P35 now limited to full self-modification + personality drift only; "no HARD STOP paradigm" terminology aligned with ADR-062 (HARD STOP does not apply to Hermes runtime / PoliteSTOP advisory only). |
| 2.1 | 2026-06-28 | Guinevere + Faiz | Annotated P24 as HARD DEPENDENCY (locked 2026-06-28); clarified P28-P36 scope as deploy/configure (P24 builds everything); added ADR-062 disclaimers to risk section; added P32 rename note.

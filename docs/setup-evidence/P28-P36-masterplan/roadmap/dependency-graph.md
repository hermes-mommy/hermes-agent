# Hermes Society Dependency Graph

## Overview

This document captures the explicit dependency relationships between the upstream prerequisite phase **P24** and the society phases **P28-P36** in the Hermes Society masterplan.

**Updated per Faiz lock (2026-06-28):**

- **P24 is a hard prerequisite.** Every society phase depends on P24 PASS. No society work happens before the fork-runtime is production-grade.
- **P28 scope expanded** to include DAO company structure setup (society ↔ Wyoming DAO LLC alignment).
- **P29 scope expanded** to include consciousness loop 24/7, dreaming, emotion engine, and sub-agents → these are now P29 surfaces, not P35 surfaces.
- **P30 governance has "no HARD STOP paradigm"** — PoliteSTOP advisory only; HARD STOP does not apply to Hermes runtime per ADR-062.
- **P32 REPURPOSED** — was "P24 Fork Integration" → now "External Presence & Tools" (external accounts Q41/Q63/Q69, unrestricted internet Q94, browsing capability, external freelance platform access).
- **P35 scope narrowed** — full self-modification + personality drift `bebas tanpa batas` only. NO emotions, NO sub-agents, NO consciousness loop.

The graph enforces strict ordering at the upstream gate (P24) and the society trunk (P28-P31) and unlocks parallelism for downstream phases to minimize total timeline without compromising safety.

## ASCII Dependency Graph

```
                           ┌─────────────────────────────────────────────────┐
                           │  External: P22.1 PASS, P23A, P27, P20, P19      │
                           └────────────────────┬────────────────────────────┘
                                                │
                                                ▼
                       ┌────────────────────────────────────────────────────┐
                       │                      P24                          │
                       │  Hermes Agent Fork (UPSTREAM PREREQUISITE)         │
                       │  (Hermes fork built, upstream-synced, runtime OK)  │
                       │  STATUS: must PASS before P28 begins               │
                       └────────────────────┬───────────────────────────────┘
                                            │  (HARD prerequisite gate)
                                            ▼
                       ┌────────────────────────────────────────────────────┐
                       │                      P28                          │
                       │  Hermes Society Foundation + DAO Structure         │
                       │  (2 founders, event store, private memory,        │
                       │   Wyoming DAO LLC registration)                    │
                       └─────┬──────────────────┬───────────────────────────┘
                             │                  │
                ┌────────────▼──────┐           │
                │       P29         │           │
                │ Cognition+Emotions│           │
                │  + Sub-agents +   │           │
                │ Consciousness 24/7│           │
                └────────┬──────────┘           │
                         │                      │
                ┌────────▼──────────────────────▼──────┐
                │                P30                   │
                │  Society Governance                  │
                │  (2/2 Guinevere+Pharsa agreement;    │
                │   no HARD STOP paradigm;             │
                │   PoliteSTOP advisory per ADR-062)   │
                └────┬─────────────┬────────────┬────┘
                     │             │            │
           ┌─────────▼──────┐  ┌───▼──────┐  ┌──▼───────────┐
           │    P31         │  │   P33    │  │     P35      │
           │ Discord Bots   │  │  Wallet  │  │ Self-Evolve  │
           │ + Multi-Bot    │  │ Finance  │  │  (personality│
           │ + Company ID   │  │ 2/2 mult.│  │   drift only)│
           └─────────┬──────┘  └───┬──────┘  └──┬───────────┘
                     │             │            │
                     ▼             ▼            │
                ┌────▼─────┐  ┌────▼─────┐     │
                │   P32    │  │   P34    │     │
                │ External │  │ Revenue  │◄────┘ (parallel)
                │ Presence │  │ x402 +   │
                │ & Tools  │  │ external │
                │ (was P24 │  │ freelance│
                │  fork int│  │          │
                └─────┬────┘  └────┬─────┘
                      │            │
                      └─────┬──────┘
                            │
                            ▼
               ┌────────────────────────────┐
               │           P36              │
               │  Production Hardening      │
               │  + Scale-Out + S3 Backup   │
               └────────────────────────────┘

LEGEND:
═══════════  : sequential (must complete before)
─ ─ ─ ─ ─ ─  : parallel (can fire alongside)
═══════════ P24 → P28 is the UPSTREAM PREREQUISITE gate (hard, not bypassable)
```

## Dependency Matrix

| Phase | Depends On | Blocks | Parallel With |
|---|---|---|---|
| P24 | None (own upstream phase) | P28-P36 (all society phases) | — (root of society graph) |
| P28 | P24, P22.1, P27, P20, P19 | P29-P36 | — (sequential after P24) |
| P29 | P28 | P30, P31, P35 | — (sequential) |
| P30 | P28, P29 | P31, P33, P34, P35 | — (sequential) |
| P31 | P28, P29, P30 | P32 | P33, P34 |
| P32 | P24, P28, P31 | P36 | P33, P34, P35 |
| P33 | P28, P30 | P34 | P31, P32, P35 |
| P34 | P28, P30, P33 | P36 | P31, P32, P35 |
| P35 | P28, P29, P30 | P36 | P31, P32, P33, P34 |
| P36 | P24, P28-P35 ALL | — (terminal) | — |

## Subsystem Dependencies

Each subsystem maps to specific phases. Dependencies propagate upward through the phase graph.

| Subsystem | Implemented In | Depends On Subsystems | Notes |
|---|---|---|---|
| S1: Runtime substrate | P28 | P24 (fork runtime), P19 (production), P20 (autonomy) | VPS + event store; assumes fork runtime from P24 |
| S2: Event store (WORM) | P28 | S1 | Append-only log |
| S3: Private memory | P28 | S1, encryption layer | Encrypted at rest |
| S4: Vector recall | P29 | S3, S1 | Embedding store |
| S5: Graph recall | P29 | S3, S1 | Knowledge graph |
| S6: Filesystem recall | P29 | S3 | grep + semantic |
| S7: BDI world model + consciousness daemon + emotion engine + sub-agent runtime | **P29** (consolidated) | S4, S5, S6 (consolidated: world model + 24/7 dreaming + emotion vector + 10-active sub-agent limit) | P29 surfaces: REQ-017 (consciousness), REQ-018 (sub-agents ≤10), REQ-019 (emotion), REQ-007/008/005 (world model + recall) |
| S8: Governance tiers | P30 | S1, identity layer, S7 (emotion modulation per REQ-019) | T1-T4 escalations |
| S9: Founder protocol (2/2 Guinevere+Pharsa) | P30 | S8 | 2/2 founder agreement |
| S10: Spawn protocol | P30 | S8, S9 | New Hermes creation |
| S11: PoliteSTOP advisory | P30 | S1, S5 | Advisory broadcast; no Hermes-runtime termination; per ADR-062 |
| S12: Discord bot identity + company-identity posture | P31 | S8, S10 | Per-Hermes identity + DAO-company-binding |
| S13: Wallet + Safe multisig Scheme B (2/2 founders + 1 emergency signer) | P33 | S8, S9 | Safe Scheme B per BLDM Q107; Faiz has NO wallet key |
| S14: Revenue channel | P34 | S13, P32 (external freelance platforms) | x402 protocol + external freelance routes-to-company-wallet |
| S15: Mutation governance (full self-modification + personality drift only) | **P35** (narrowed scope) | S7 (uses cognition surfaces from P29, does NOT modify them), S8 | Ratchet gate + drift triad; personality drift `bebas tanpa batas` platform-permitted; NO new emotion/sub-agent/consciousness additions |

## External Dependencies

| Dependency | Status | Required For | Notes |
|---|---|---|---|
| P22.1 PRODUCTION PASS | MET | P28 | 3 ACTIVE adapters cover foundation contract |
| P23 production-pass | NOT MET | P28 (P23A sufficient) | Definition-only currently satisfies P28 |
| **P24 fork production-pass** | **NOT MET (upstream phase)** | **P28 (HARD PREREQUISITE, per updated Faiz lock 2026-06-28)** | **All fork work consolidates here; foundation is now fork-required** |
| P21 voice | SKIPPED | — | Explicitly removed from P28 deps |
| P27 Accepted | MET | P28 | ADR-054 acknowledged |
| P20 early acceptance | MET | P28 | Living autonomy kernel running |
| P19 production | MET | P28 | Runtime namespace available |
| 9Router | NOT P28 dep | — | Downstream concern |
| P25 (unknown) | NOT P28 dep | — | Tracked separately |
| P26 (unknown) | NOT P28 dep | — | Tracked separately |
| VPS (≥4GB/2vCPU/50GB) | NEEDED | P28 | One large VPS until >32c/64GB |
| External accounts (Twitter/X Q41, GitHub Q63, freelance Q69) | AVAILABLE | P32 | External Presence & Tools phase |
| Unrestricted internet egress (Q94) | AVAILABLE | P32 | Browsing capability + freelance platform access |
| Wyoming DAO LLC legal registration | NEEDED | P28 | Required for DAO company setup in P28 |

## Parallelism Rules

1. **P24 upstream gate** — P28 may NOT start until P24 PASS. This is a hard prerequisite, not a soft parallel. Reasoning: foundation must assume a stable Hermes Agent fork runtime; no "P24 native fork" carve-out remains. **P24 v2.0 is a HARD dependency (locked 2026-06-28). P28 deploys the P24 fork.**
2. **Sequential trunk**: P28 → P29 → P30 must run in order. No parallelism at the society foundation.
3. **P31 + P33 can run parallel** after P30 PASS because Discord identity and Wallet share only P30 (governance).
4. **P32 can run parallel** with P33-P34 after P31 PASS because external presence only needs identity foundation (P31), event store (P28), and the fork runtime (P24). It does not touch wallet internals.
5. **P35 can run parallel** with P31-P34 after P30 PASS because self-evolution needs only cognition (P29) + governance (P30). Note: P35 is now **scope-narrowed** to full self-modification + personality drift only; it does NOT add new emotion/sub-agent/consciousness surfaces (those are P29 surfaces and remain unchanged by P35).
6. **P36 is terminal** — must wait for all P24 + P28-P35 to PASS.
7. **Shared writers**: any phase that touches ADR-Index or PersonaSafetyPolicy requires parent-only handling and Oracle review.

## Decision Rationale

Key decisions encoded in this graph and why:

1. **P24 promoted to upstream prerequisite** — supersedes the previous "P24 deferred" carve-out. Per the updated Faiz lock (2026-06-28), foundation must ASSUME the fork runtime is production-grade; no fork work leaks into P32. Rationale: P32 was repurposed from "P24 Fork Integration" to "External Presence & Tools"; without consolidating fork work in P24, the trunk would have ambiguous dependencies. P24 owns the fork; society assumes fork-stable substrate. **P24 v2.0 is a HARD dependency (locked 2026-06-28). P28 deploys the P24 fork.**
2. **P22.2 subsumed by P22.1** — P22.1 has 3 ACTIVE adapters covering the foundation contract; P22.2 is treated as part of P22.1 to avoid double-counting
3. **P23A sufficient for P28** — definition-only satisfies P28 contract; full P23 production-pass deferred until foundation proves the contract works
4. **P21 voice explicitly skipped** — voice is a future enhancement, not a foundation dependency; decoupling prevents voice latency from blocking P28
5. **9Router not blocked** — 9Router is downstream of foundation; P28 can run without it
6. **P31 and P33 can parallel** — after P30 governance, Discord identity layer and wallet layer share only the governance signing primitive, no schema collision, no shared writer
7. **P32 can parallel with P33-P34** — repurpose rationale: external accounts + internet egress + browsing capability touch external-facing namespaces only; P32 never reads/writes inside the wallet or the cognition subsystems.
8. **P35 scope narrowed to personality drift only** — per the Q70/Q81 unlocking, emotions + sub-agents moved to P29 so that P35 only owns full self-modification + unbounded personality drift. Reasoning: P29 surfaces (emotion engine, sub-agent runtime, consciousness loop) are core cognition; P35 surfaces (mutations to own code/persona/memory) are governance-over-cognition. Mixing them in P35 caused earlier scope-creep concerns; separating them in P29/P35 makes each phase have a tight surface and clearer ownership.
9. **P36 is terminal** — production hardening integrates all prior subsystems; running it before any prior phase is unblocked would invalidate its gates

## Anti-Dependencies (Explicit Non-Requirements / Carve-Outs)

Some things are NOT dependencies or are explicitly carved out:

- **9Router adoption** — not required until downstream phases
- **P25/P26** — tracked separately; do not gate the masterplan
- **Full P23 production-pass** — definition-only P23A is sufficient
- **Voice infrastructure (P21)** — explicitly skipped
- **Multi-region deployment** — single VPS until >32c/64GB threshold
- **External LLM switching** — not a masterplan concern
- **Horizontal scaling** — explicitly deferred to post-P36 optimizations
- **HARD STOP semantics for Hermes runtime** — explicitly carved out per ADR-062. Hermes runtime DOES NOT have HARD STOP primitive; PoliteSTOP signal is advisory only; receiving Hermes runtime MAY continue operating. Foundation assumes this design from P30 onward.

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere + Faiz | Initial graph (P28-P36 with P24 deferred). |
| 2.0 | 2026-06-28 | Guinevere + Faiz | **P24 → P28 hard prerequisite edge** added (no society work before P24 PASS); **P32 node REPURPOSED** from "P24 Fork Integration" → "External Presence & Tools"; **S7 subsystem entry expanded** to include consciousness 24/7 + emotion + sub-agent surfaces (now P29-owned); **S15 subsystem entry narrowed** to personality-drift only (no longer contains emotions/sub-agents); **P30 governance row** annotated with "no HARD STOP paradigm / PoliteSTOP per ADR-062"; **P35 scope row** annotated with personality-drift-only. |
| 2.1 | 2026-06-28 | Guinevere + Faiz | Annotated P24 as HARD DEPENDENCY (locked 2026-06-28); clarified P28 deploys P24 fork; added deploy/configure scope note.

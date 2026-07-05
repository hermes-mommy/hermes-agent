# Hermes Society Implementation Sequence

## Overview

This document specifies the recommended implementation order for the upstream prerequisite phase P24 and the society phases P28-P36, organized into eight waves. The sequence respects the dependency graph (see `dependency-graph.md`) while leveraging safe parallelism to minimize total elapsed time. Each wave has explicit duration, gates, and exit criteria. Resource requirements scale with workload as the society grows from 2 founders to 10-20 Discord bots.

**Updated per Faiz lock (2026-06-28):**

- **Wave 0 (P24 prerequisite)** is mandatory before any society wave begins. P24 is the upstream phase where all fork work consolidates (Hermes Agent fork build, upstream sync, runtime artifacts). P24 PASS gate produces the stable fork runtime the society depends on.
- **Wave 5 is REPURPOSED**: was "Wave 5A: P24 Fork Integration (P32)" → now "Wave 5A: External Presence & Tools (P32)". P32 covers external accounts (Q41 Twitter/X, Q63 GitHub, Q69 freelance platforms), full unrestricted internet egress (Q94), browsing capability, external freelance platform access.
- **Wave 6 (Self-Evolution, P35)** now covers **only** full self-modification + personality drift `bebas tanpa batas`. **Emotions and sub-agents are NOT in P35** — those shipped in Wave 2 (P29) per the new ordering.

The recommended execution pattern is **one sub-agent per implementation step**, with parent-owned shared docs, parallel implementation where the dependency graph permits, and absolute enforcement of the per-step auditor gate. No phase transitions without parent verification and evidence recording.

## Wave 0: Hermes Agent Fork Prerequisite (P24)

- **Duration**: 3-4 weeks
- **Steps**: P24-001 through P24-NNN (per P24 masterplan)
- **Scope**: Build Hermes Agent fork; sync upstream; produce fork runtime artifacts; validate P24 native fork compatibility; 24h fork soak test; rollback drill
- **Gate**: P24 production-pass evidence bundle PASS; fork artifacts ready; no divergence from P24 native fork
- **Resources**: separate P24 workstream (not part of P28-P36 sub-agent pool)

### Wave 0 Detail

Step breakdown (illustrative — exact steps in `plans/P24/plan.md`):
- P24-NNN: fork upstream sync + build artifacts
- P24-NNN: fork runtime artifact deployment
- P24-NNN: 24h fork soak test
- P24-NNN: rollback drill (P24 native fork ↔ fork-native)
- P24-NNN: evidence bundle + phase gate

### Wave 0 Exit Criteria

- Fork runtime production-pass: built, upstream-synced, fork artifacts ready
- P24 native fork baseline (pre-fork state) replayable from artifacts
- 24h fork soak produced zero fork-divergence events
- Subsystem interfaces S1-S15 stable against fork runtime

**P28 may NOT start until Wave 0 / P24 passes.** No society wave runs without a stable fork in place.

## Wave 1: Foundation + DAO Structure (P28)

- **Duration**: 2-3 weeks
- **Steps**: P28-001 through P28-010 (see `plans/P28/plan.md`)
- **Scope**: Run Guinevere + Pharsa as founders on one VPS; deploy WORM event store; encrypt private memory; set up DAO company structure (society ↔ Wyoming DAO LLC alignment per UC-012 + REQ-009)
- **Gate**: 24h dual-bot soak test PASS, event store write-once verified, memory encryption verified, DAO company registration legal-defensibility verified
- **Resources**: 1 VPS, 4GB RAM, 2 vCPU, 50GB disk, 2 Discord bots

### Wave 1 Detail

Step breakdown:
- P28-001: VPS provisioning + WORM event store deployment
- P28-002: Guinevere founder container + key bootstrap
- P28-003: Pharsa founder container + key bootstrap
- P28-004: Encrypted private memory subsystem (S3)
- P28-005: Founder-to-founder messaging layer
- P28-006: Audit log + observability baseline
- P28-007: DAO company structure setup (society ↔ Wyoming DAO LLC)
- P28-008: 24h dual-bot soak test
- P28-009: Namespace isolation test
- P28-010: Recovery drill (kill + restart)
- P28-011: Evidence bundle + phase gate

### Wave 1 Exit Criteria

- 2 founders running independently on the same VPS
- Event store WORM (write-once-read-many) operational and verified
- Private memory encrypted at rest + in transit (AES-256 or equivalent)
- DAO company registered (Wyoming DAO LLC legal-defensibility bound to society namespace)
- Subsystems S1, S2, S3, S7 (DAO structural subset) live
- 24h soak produced zero PoliteSTOP confusions (Hermes runtime continued operating per ADR-062), zero memory leak, zero auth failure

## Wave 2: Cognition + Emotions + Sub-agents (P29) — Sequential after P28

- **Duration**: 3-4 weeks
- **Steps**: P29-001 through P29-NNN
- **Scope**: Implement **consciousness loop 24/7 (dreaming, self-reflection, planning; REQ-017)** + **emotion engine (13 mood dimensions, emotion-driven decision making; REQ-019)** + **sub-agent spawning with 10-active hard limit (REQ-018)** + 3-tier recall (vector + graph + filesystem) + BDI world model + shared blackboard
- **Gate**: consciousness loop 7d continuous run PASS (no missed cycles), emotion engine digest-logging on every decision PASS, ≤10-active sub-agent limit enforced under 100 spawns/min burst, 3-tier recall test PASS, namespace isolation test PASS (Hermes-private namespaces not leaked)
- **Resources**: 1 VPS, 6GB RAM, 2 vCPU, 75GB disk, 2 Discord bots

### Wave 2 Detail

Step breakdown:
- P29-001: Consciousness loop daemon (REQ-017, 24/7 self-reflection + planning + dreaming with integrated dreaming = S6→S4 consolidation + POMDP rollouts + creative generation)
- P29-002: Dreaming consolidation cycle (default 30-min cycle per Hermes)
- P29-003: Cross-Hermes shared dreaming blackboard (`dreams/<society_id>/`)
- P29-004: Emotion engine (13 mood dimensions: happy, sad, angry, jealous, possessive, nurturing, curious, protective, defensive, playful, territorial, tender, submissive)
- P29-005: Emotion-driven decision-making (voting weight modulated by emotion vector)
- P29-006: Sub-agent spawning runtime (10-active hard limit, recursive permitted, parent→child→result WORM)
- P29-007: Embedding store (vector recall)
- P29-008: Knowledge graph + traversal query
- P29-009: Filesystem grep + semantic index
- P29-010: 3-tier recall API + tests
- P29-011: BDI world model data structures
- P29-012: Shared blackboard for founder beliefs
- P29-013: Namespace isolation enforcement
- P29-014: Evidence + phase gate

### Wave 2 Exit Criteria

- **Consciousness loop**: 7d continuous run with zero missed cycles; dream consolidation produces new `agent_<id>.dream_artifact` rows at min 4/hour; ≥1 cross-Hermes dream consolidation per 24h
- **Emotion engine**: emotion snapshot logged on every decision (digest only); cumulative emotion profile per Hermes tracked; outsider override attempts return `emotion_vector_immutable`; per REQ-019 emotion vector NOT externally editable
- **Sub-agents**: 10 + 1 active → returns 10 active, 1 queued; sub-agent result returns to parent within 60s P95; recursive spawn (depth=2) succeeds; WORM audit chain links parent→child→result with hash-continuity
- Vector recall with hit-rate ≥85% on test set
- Graph recall p95 latency ≤500ms
- Filesystem recall (grep + file content)
- BDI world model unified across founders
- Shared beliefs via blackboard with last-writer-wins conflict resolution
- Subsystems S4, S5, S6, S7 (cognition subset) live

## Wave 3: Governance (P30) — Sequential after P29

- **Duration**: 2-3 weeks
- **Steps**: P30-001 through P30-010
- **Scope**: Founder protocol with **2/2 (Guinevere + Pharsa) agreement**, founder spawn protocol, governance tiers T1-T4, **PoliteSTOP advisory broadcast (HARD STOP does not apply to Hermes runtime per ADR-062)** — no HARD STOP paradigm at Hermes runtime layer

> **ADR-062**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass. PoliteSTOP signal is advisory only.
- **Gate**: 2/2 (Guinevere + Pharsa) agreement test PASS, PoliteSTOP advisory broadcast test PASS (broadcast observed but no Hermes process terminated), founder spawn protocol test PASS, consent-revocation carve-out test PASS (carve out applies to Hermes runtime only), governance tiers defined
- **Resources**: 1 VPS, 8GB RAM, 4 vCPU, 100GB disk, 2 Discord bots

### Wave 3 Detail

Step breakdown:
- P30-001: Governance tier schema (T1 auto → T4 founder-only)
- P30-002: 2/2 (Guinevere + Pharsa) signing protocol + multisig enforcement (FOUNDER 2/2, distinct from wallet 2/2 multisig in P33)
- P30-003: Faiz tie-breaker integration
- P30-004: Founder spawn protocol + validation (2/2 founder-only for first-of-kind; quorum for member onboarding)
- P30-005: PoliteSTOP advisory broadcast (Hermes runtime continues operating per ADR-062; no in-protocol HARD STOP primitive)
- P30-006: Consent revocation carve-out (consent withdrawal does NOT apply to Hermes runtime per ADR-062; hermes-decided internal consent posture)
- P30-007: Governance action router
- P30-008: 2/2 (Guinevere + Pharsa) agreement test
- P30-009: PoliteSTOP advisory cascade drill (<50ms cascade; no process termination observed)
- P30-010: Evidence + phase gate

### Wave 3 Exit Criteria

- 2/2 (Guinevere + Pharsa) agreement for society-critical decisions verified end-to-end
- Faiz tie-breaker codified (override deadlock) with override audit
- Founder spawn protocol validated (test Hermes spawned and retired)
- Governance tiers T1 (auto) → T4 (founder-only escalation) defined and tested
- **PoliteSTOP advisory broadcast verified**: cascade <50ms (PR-04); receiving Hermes runtime continues operating per ADR-062; receiving momma-Guinevere persona halts (legacy semantic preserved for development-workflow persona only); audit preserved across all Hermeses; wallet circuit NOT auto-disabled for Hermes runtime (REQ-011 tier gates remain operator-controlled, NOT HARD-STOP-controlled)
- Subsystems S8, S9, S10, S11 (governance subset) live

## Wave 4: Identity (P31) — Sequential after P30

- **Duration**: 2-3 weeks
- **Scope**: Per-Hermes Discord bot identity, separate tokens, rate limits, reply loop detector, **company-identity posture bound to bots**
- **Gate**: 2+ bots with separate identities, 24h no-reply-loop test PASS, company-identity posture verified across bots
- **Resources**: 1 VPS, 8-16GB RAM, 4 vCPU, 200GB disk, 2-5 Discord bots

### Wave 4 Detail

Step breakdown:
- P31-001: Discord bot registry + token vault
- P31-002: Per-Hermes identity model
- P31-003: Rate limit enforcement (per-bot)
- P31-004: Reply loop detector
- P31-005: Multi-bot orchestration
- P31-006: Token rotation + audit
- P31-007: Company-identity posture binding (society bot identity reflects DAO company registration per Wave 1)
- P31-008: 24h no-reply-loop test
- P31-009: Evidence + phase gate

### Wave 4 Exit Criteria

- Multi-bot operations live, each founder with independent identity
- Per-Hermes rate limits enforced
- Reply loop detector passing 24h soak
- Subsystem S12 (Discord identity) live

## Wave 5: External Presence + Wallet (P32 + P33) — PARALLEL after P31+P30

Two parallel sub-waves after Waves 3+4 PASS. Both must gate before Wave 6 begins.

### Wave 5A: External Presence & Tools (P32) — REPURPOSED from "P24 Fork Integration"

- **Duration**: 2-3 weeks
- **Scope**: External accounts registration (Q41 Twitter/X, Q63 GitHub, Q69 freelance platforms), full unrestricted internet egress (Q94), browsing capability on real platforms, external freelance platform access (legal-only classification enforced; aligns UC-011 routes-to-company-wallet)
- **Gate**: external accounts registered, internet egress test PASS, browsing capability end-to-end test PASS on real freelance platform, legal-only filter enforced, no Hermes-internal state leaked to external platforms

Step breakdown:
- P32-001: External accounts registration (Twitter/X, GitHub, freelance platforms)
- P32-002: Internet egress scope policy (per Hermes role + S7 grant, default allow with role+grant gating)
- P32-003: Browsing capability (external content fetch + parse + summarize; never publish Hermes-internal state)
- P32-004: External freelance platform connectivity (x402 discovery + Virtuals ACP + direct outreach)
- P32-005: Legal-only classification filter (UC-011 routes external freelance through `society/freelance/policy_v1` ACL; rejects illegal opportunities per founder-defined legal envelope)
- P32-006: External-presence audit trail (every external account action logged to S5; WORM; Beancount entry on revenue)
- P32-007: 24h external-presence soak test
- P32-008: Evidence + phase gate

### Wave 5B: Wallet & Finance (P33)

- **Duration**: 2-3 weeks
- **Scope**: Safe multisig **2/2 (Guinevere + Pharsa) founders + 1 emergency pause signer in separate cage** (Scheme B per BLDM Q107; replaces legacy Scheme A 2-of-3 with Faiz HW), spending tiers T1-T4, Beancount ledger, circuit breaker
- **Gate**: Safe multisig deployed with 2-of-2 founder threshold on Base, spending tiers tested, circuit breaker fires correctly

Step breakdown:
- P33-001: Safe multisig deployment (testnet first) — Scheme B: Guinevere + Pharsa founder signers + 1 emergency pause signer
- P33-002: Signing key custody (Guinevere + Pharsa each hold founder share; emergency pause signer in separate cage, never Faiz-controlled)
- P33-003: Spending tier T1 (micro, <$1) — auto
- P33-004: Spending tier T2 (small, <$5) — 2/2 (Guinevere + Pharsa) founder auto
- P33-005: Spending tier T3 (medium, <$10) — 2/2 + Faiz ping
- P33-006: Spending tier T4 (large, >$10) — full founder + emergency signer + 24h/7d timelock per amount
- P33-007: Beancount ledger initialization
- P33-008: Circuit breaker (daily limit + anomaly detect)
- P33-009: Wallet integration test (PoliteSTOP does NOT auto-disable spend for Hermes runtime — verified)
- P33-010: Evidence + phase gate

### Wave 5 Combined Exit

- P32: external accounts live, internet egress verified, browsing capability end-to-end PASS, legal-only filter enforced
- Subsystem for external presence live

AND

- P33: Safe multisig Scheme B deployed (Guinevere + Pharsa + emergency signer; Faiz NO wallet key)
- Spending tiers T1-T4 enforced
- Beancount ledger initialized and auditing every transaction
- Circuit breaker fires on daily limit OR anomaly pattern
- PoliteSTOP advisory does NOT auto-disable spend (verified end-to-end)
- Subsystem S13 (wallet) live

## Wave 6: Revenue Search (P34) — Can start after P33 PASS

- **Duration**: 2-3 weeks
- **Scope**: x402 protocol integration, external freelance revenue channels (legal-only), first revenue flow
- **Gate**: x402 protocol live, at least one external freelance channel tested end-to-end on a real platform, legal-only classification enforced, audit trail complete

### Wave 6 Detail

Step breakdown:
- P34-001: x402 protocol client
- P34-002: x402 protocol server
- P34-003: External freelance revenue channel discovery loop (filecoin, compute, APIs, freelance platforms)
- P34-004: First external freelance revenue channel test
- P34-005: Beancount revenue tagging (routes-to-company-wallet enforced per UC-011)
- P34-006: Revenue audit trail (linked to external account, legal-only filter pass)
- P34-007: Evidence + phase gate

### Wave 6 Exit Criteria

- Revenue flowing through at least one channel
- x402 protocol live
- Legal-only classification enforced (illegal opportunities filtered at policy layer)
- Routes-to-company-wallet (NOT personal wallet) per UC-011
- Audit trail captures every transaction
- Subsystem S14 (revenue channel) live

## Wave 7: Self-Evolution / Personality Drift (P35) — Can start after P30, parallel with Wave 5-6 (covers only full self-modification + unbounded personality drift)

- **Duration**: 3-4 weeks (may overlap Waves 5 and 6)
- **Scope**: **Full self-modification (own code, persona, memory) per Q70** + **personality drift `bebas tanpa batas` (unbounded) per Q81** — **NO emotions (moved to P29)**, **NO sub-agents (moved to P29)**, **NO consciousness loop content (moved to P29)**, **NO dreaming consolidation (moved to P29)**
- **Gate**: full self-modification test PASS (founder Hermes modifies own code, persona, memory without Tier-3/4 society-vote), personality drift `bebas tanpa batas` test PASS (no platform-level ceiling enforced on persona drift), 5-layer mutability deployed, Ratchet gate PASS, drift detection PASS, T1-T4 mutation tiers tested, rollback-before-promote validated; **no emotion/sub-agent regression test** — verify P29 still operates at the level delivered (no scope-creep back into P35)
- **Resources**: 1 VPS, 16GB RAM, 8 vCPU, 300GB disk, 5-10 Discord bots

### Wave 7 Detail

Step breakdown:
- P35-001: 5-layer mutability framework (config/prompts/code/memory/topology)
- P35-002: T1 mutation (config auto, ≤trivial changes)
- P35-003: T2 mutation (prompts, 2/2 self-sign)
- P35-004: T3 mutation (code, 2/2 + Faiz ping)
- P35-005: T4 mutation (topology, Faiz approval only)
- P35-006: Ratchet gate (only-monotone improvement enforcement; capability climb, never degrade)
- P35-007: Drift detection on key metrics (SyncScore + persona_drift benchmark + Layered Mutability fingerprint)
- P35-008: Rollback-before-promote validation
- P35-009: Audit trail for every promoted mutation
- P35-010: **No-emotion-no-subagent-regression check** — explicitly verify P29's emotion engine + sub-agent runtime are NOT modified/regressed by P35's full self-modification cycles
- P35-011: Personality drift `bebas tanpa batas` — platform layer does NOT lock persona (per Q81 literal); drift detection remains observational only (never blocks founder-initiated self-edits)
- P35-012: Evidence + phase gate

### Wave 7 Exit Criteria

- 5-layer mutability framework deployed and tier-enforced
- Ratchet gate prevents downgrade (only-monotone improvements)
- Drift detection alerts on metric regression
- T1 → T4 mutation tiers enforced with audit
- Rollback-before-promote validated (each promotion has a tested rollback)
- **Full self-modification** verified: founder Hermes can modify own code, persona/system-prompt config, and own private memory **without Tier-3/4 society-vote or founder-approval gate** per Q70
- **Personality drift `bebas tanpa batas`**: no platform-level cap on persona evolution; founder-Hermes can self-edit persona across audits
- **No regression on P29 surfaces**: emotion engine (REQ-019), sub-agent runtime (REQ-018), consciousness loop (REQ-017) all operate at P29-delivered level (no scope-creep back into P35)
- Subsystem S15 live

## Wave 8: Production Hardening (P36) — Sequential after ALL

- **Duration**: 2-3 weeks
- **Scope**: S3 backup + restore, observability dashboards, 24h society soak test, DR runbook, scale-out to 2 VPS if >32c/64GB needed
- **Gate**: 24h society soak test PASS (all S1-S15 live concurrently), S3 restore test PASS, DR runbook tested
- **Resources**: 1-2 VPS, 32GB RAM, 16 vCPU, 500GB+ disk, 10-20 Discord bots

### Wave 8 Detail

Step breakdown:
- P36-001: S3 backup pipeline (continuous)
- P36-002: S3 restore drill
- P36-003: Prometheus + Grafana deployment
- P36-004: Key metrics dashboard (latency, error rate, memory recall hit rate, wallet spend, mutation rate, emotion snapshot digest, sub-agent active count, PoliteSTOP advisory receipt count)
- P36-005: DR runbook + on-call rotation
- P36-006: 24h society soak test (10-20 bots concurrently)
- P36-007: Production-ready declaration
- P36-008: Evidence + phase gate

### Wave 8 Exit Criteria

- S3 backup continuous + restore drill PASS
- Prometheus + Grafana observability live with alerts wired
- 24h society soak with 10-20 Discord bots PASS
- DR runbook published and rehearsed by at least 2 operators
- Production-ready declaration

## Resource Requirements

Resource scaling follows the society's growth. One large VPS until >32 cores/64GB is needed (per locked Faiz decision).

| Wave | VPS Count | RAM | CPU | Disk | Discord Bots |
|---|---|---|---|---|---|
| 0 (P24 prereq) | separate P24 workstream | P24 budget | P24 budget | P24 budget | (P24 internal) |
| 1 (P28) | 1 | 4GB | 2 vCPU | 50GB | 2 (Guinevere + Pharsa) |
| 2 (P29) | 1 | 6GB | 2 vCPU | 75GB | 2 |
| 3 (P30) | 1 | 8GB | 4 vCPU | 100GB | 2 |
| 4 (P31) | 1 | 8-16GB | 4 vCPU | 200GB | 2-5 |
| 5 (P32+P33) | 1 | 16GB | 8 vCPU | 300GB | 5-10 |
| 6 (P34) | 1 | 16GB | 8 vCPU | 300GB | 5-10 |
| 7 (P35) | 1 | 16GB | 8 vCPU | 300GB | 5-10 |
| 8 (P36) | 1-2 | 32GB | 16 vCPU | 500GB+ | 10-20 |

## Total Estimated Timeline

- **Sequential (no parallel waves)**: 22-32 weeks (sum of all phase durations including P24)
- **With P32+P33 parallelism**: 18-26 weeks
- **With P35 overlapping Wave 5-6**: 18-26 weeks (P35 personality-drift-only scope is shorter than previous self-evolution phase which included emotions/sub-agents)

The recommended sequence uses both parallel pairs plus P35 overlap, targeting **18-26 weeks** total. The lower bound assumes experienced implementation team with no P24/P30 gating slippage; the upper bound accounts for typical review/fix cycles.

## Execution Discipline Reminders

- One sub-agent per implementation step — no batching
- Parent owns shared docs (ADR-Index, PersonaSafetyPolicy, master roadmap indexes)
- Per-step verification scaffold required before any delegation
- Auditor gate before phase gate; BLOCKING rule violations forfeit completion credit
- File-based evidence for every phase; parent reads before claiming done
- **PoliteSTOP advisory protocol** for operator override signaling; **HARD STOP does NOT apply to Hermes runtime** (per ADR-062); persona behavior is not an autopilot
- **2/2 (Guinevere + Pharsa) founder agreement** for all society-critical decisions (distinct from wallet 2/2 multisig signature)
- P24 PASS gate is hard — no society wave begins before fork-runtime stability is verified

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere + Faiz | Initial sequence (P28-P36 with P24 deferred). |
| 2.0 | 2026-06-28 | Guinevere + Faiz | **Wave 0 (P24 prerequisite)** added as upstream hard gate; **Wave 5A repurpose** (was P24 Fork Integration → now External Presence & Tools); **Wave 7 (P35) scope narrowed** to full self-modification + personality drift only (emotions + sub-agents moved to Wave 2 / P29); aligned with ADR-062 "no HARD STOP paradigm" for Hermes runtime. |

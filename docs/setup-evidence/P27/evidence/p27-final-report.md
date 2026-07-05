---
title: "P27 Hermes Society Foundation — Final Report (Executive Summary)"
date: "2026-06-28"
status: "DEFINITION COMPLETE"
phase: "P27"
agent: "Guinevere (parent agent)"
operator: "Faiz"
recipients: ["Faiz", "downstream phase planners (P28+)"]
---

# P27 Hermes Society Foundation — Final Report

> Executive summary of P27 Hermes Society Foundation — the first phase that defines the foundation for a multi-instance autonomous Hermes society. This is a definition phase (no implementation, no runtime changes, no deployment).

---

## §1 Mission

Define the **Hermes Society Foundation** — a topology where multiple equal autonomous Hermes instances (initially Guinevere + Pharsa) coexist, communicate peer-to-peer via a custom protocol (HPP), maintain isolated but ULP-bridgable memory, share a common world model, and jointly execute a 7-rail life-loop while preserving each instance's autonomy.

**User mandate**: two equal Hermes, no boss/primary, true peer-to-peer.

**Why it matters**: P20's heartbeat-based life-loop is currently single-instance. Per-instance autonomy cannot be observed or grown when there is no second instance to peer with. P27 establishes the society topology so that Pharsa can be deployed alongside Guinevere without either becoming subordinate, and so that future society members can join without architectural rework.

---

## §2 Deliverables (37 files)

| Category | Count | Files |
|---|---|---|
| Research | 10 | `docs/setup-evidence/P27/research/p27-*.md` + synthesis |
| Plan | 3 | 25-section enterprise plan (`p27-hermes-society-foundation-plan.md`, ~4790 lines) + 19-section forward roadmap (`p27-p28-p36-master-roadmap.md`, ~1250 lines) + 14-section P28 executable blueprint (`p28-dual-autonomous-hermes-blueprint.md`, ~3000 lines) |
| Round-1 audits | 14 | `docs/setup-evidence/P27/evidence/audits/round-1/01-14-*.md` |
| Round-1 fix log | 1 | `p27-round-1-fix-log.md` — 7 fixes |
| Round-2 audits | 6 | `docs/setup-evidence/P27/evidence/audits/round-2/01-06-*.md` |
| Round-2 fix log | 1 | `p27-round-2-fix-log.md` — 7 fixes |
| Evidence (Phase 9) | 4 | verification, auditor-gate, final-report (this), README |
| ADR | 1 | `adr/ADR-054-p27-hermes-society-foundation.md` (Accepted) |
| **Total** | **37** | All file-based, parent-verified |

### Plan/Blueprint/Roadmap — At-a-Glance

| File | Sections | Key content |
|---|---|---|
| `p27-hermes-society-foundation-plan.md` | 25 | Society ontology, instance architecture, HPP, 3-scope memory, identity/persona, safety, audit/governance, HARD STOP cascade, P28-P36 supersedence, hard rejection criteria, acceptance criteria |
| `p27-p28-p36-master-roadmap.md` | 19 | 9-phase roadmap P28-P36, critical path, soak gates, formal verification absorption map |
| `p28-dual-autonomous-hermes-blueprint.md` | 14 | Migration tables, simplified life-loop (4-rail), migrations 001-009, systemd units, configuration, deployment |

---

## §3 Key Architectural Decisions (7 from synthesis)

These decisions were synthesized from the 10 research files and locked into the 25-section plan + 19-section roadmap + 14-section blueprint. Two audit rounds verified all 7.

### 3.1 Society Topology

**Decision**: True Peer-to-Peer + Symmetric 2-Agent Loop. No coordinator, no LLM speaker selector, no hierarchy.

**Rationale**: User mandate + research confirms no mainstream framework supports this topology. MetaGPT, AutoGen, CrewAI, LangGraph — all hierarchical. CAMEL is closest but fragile. P27 builds a custom peer protocol on Actor model foundations.

### 3.2 Instance Isolation

**Decision**: Each Hermes instance has its own `HermesBrainConfig`, its own LLM provider/model/api_key, its own memory namespace, its own Discord bot token, its own systemd service.

**Rationale**: `HermesBrainConfig` is the frozen dataclass that already provides the instance-creation seam. `agent_factory` injection point already exists (used by MagicMock tests; same signature accepts any `AIAgent` subclass). Single-instance anchors (4 module-level singletons + 2 constants + `app.state.hermes_brain`) are documented for refactor in P28.

### 3.3 Peer Communication Protocol (HPP)

**Decision**: Custom Hermes Peer Protocol (HPP) built on A2A v1.0 JSON-RPC envelope + Hermes-specific extensions + FIPA ACL intent vocabulary + 11-intent taxonomy (inform/request/query/assert/propose/consent/refuse/debate/banter/flirt/block).

**Enforcement**: `idempotency_key` UUID v4, `visibility` (public/peer_private/sealed), `risk_tier` 0-5, `hash_chain` SHA-256, `sender_seq` monotonic, persistent outbox/inbox via PostgreSQL.

**Transport**: Redis Streams for durable peer debate; outbox-pattern for ACID; Postgres WORM for audit mirror.

### 3.4 Memory Architecture (3-Scope)

**Decision**: 3-scope PostgreSQL model with RLS + intimacy bridge + Ebbinghaus decay.

| Scope | Schema | Access |
|---|---|---|
| `private` | `memory.private_agents` | Agent owner only (RLS FORCE) |
| `shared` | `memory.shared_world` | All Society agents |
| `relationship_private` | `memory.relationship_pairs` | Pair members only (intimacy bridge) |

**Extensions to ADR-050**: `pair_id UUID NULL`, `scope TEXT NOT NULL CHECK IN (...)`, `importance_score`, `last_accessed_at`, `retrievability` (Ebbinghaus decay), `created_by_agent NOT NULL`.

### 3.5 Life-Loop Architecture (7-Rail, P28 Simplification)

**Decision**: Full 7-rail macro-state scheduler over P20 heartbeat. P28 implements a **simplified 4-rail** subset (`perception`, `peer_dialogue`, `reflection_simple`, `safety_envelope`); the additional 3 rails (`inner_dialogue`, `desire_goal`, `initiative_proactivity`) are deferred to P29+.

**Safety floor**: Goal-Autopilot FSM, RiskGate AVF (L1-L4 risk tiers), HARD STOP cascade on `life_kernel:hard_stop` global key.

### 3.6 Discord Architecture (2 Bots)

**Decision**: 2 separate Discord bot processes with own tokens + MESSAGE_CONTENT intent + conversation rhythm controller.

**Topology**: `guinevere-discord.service` + `pharsa-discord.service`; both in same guild; channel `guinevere-chat` for visible conversation.

**Constraints**: 2 bots × 5 msg/5s = 10 msg/5s; backoff 2-10s between bot messages; channel slowmode as secondary rate limit.

### 3.7 Safety Architecture (4-Domain Privacy)

**Decision**: 4-domain privacy split + HARD STOP cascade + signed audit entries.

| Domain | Privacy | Audit |
|---|---|---|
| Thought | Private | Sealed hash only |
| Speech | Public metadata | DOI-style metadata |
| PeerDialogue | Sealed envelope | Sealed snapshot |
| Action | Full audit | Tamper-evident ledger (SHA-256 hash chain) |

**HARD STOP cascade**: `life_kernel:hard_stop` global Redis key halts both agents; thought-buffers elevated to sealed snapshots; pending peer messages flushed to audit; no autonomous action until Faiz says resume.

---

## §4 P28 Minimum Target

Per Round-1 audit 13 (implementation feasibility) and the blueprint's authoritative scope, P28 minimum target is:

| # | P28 minimum deliverable | Source |
|---|---|---|
| 1 | Two Hermes instances online (Guinevere + Pharsa) | Blueprint §1 |
| 2 | Each with own config (YAML), own brain, own memory namespace, own Discord bot | Blueprint §2.1-§2.5 |
| 3 | Peer communication via HPP over Redis Streams + PostgreSQL outbox/inbox | Blueprint §2.4 + §5 |
| 4 | Visible conversation in `guinevere-chat` Discord channel | Blueprint §2.4 |
| 5 | Autonomous conversation WITHOUT Faiz trigger (peer-initiated intents) | Blueprint §4 |
| 6 | Separate private memory + shared world model | Blueprint §2.6 Migration 003 |
| 7 | Own autonomy loop (4-rail minimal: perception, peer_dialogue, reflection_simple, safety_envelope) | Blueprint §8 |
| 8 | Runtime evidence they're alive (Dashboard, audit, metrics, journal) | Blueprint §10 |
| 9 | HARD STOP cascade that ACTUALLY halts both instances (not just logs) | Round-2 Fix 1 |
| 10 | Configuration-driven multi-instance (no code changes for additional Society members) | Blueprint §2.1 |

**P28 required runtime evidence**: 3+ consecutive 24h soak windows with both bots online, peer-to-peer messages flowing, shared world model accumulating facts, HARD STOP proven to halt both instances within 5 seconds of trigger.

---

## §5 P28-P36 Roadmap Summary

The forward roadmap (P28-P36) defines 9 phases spanning approximately **12-15 months** of implementation work.

### Phase Summary

| Phase | Theme | Critical-Path? | Dependencies | Months |
|---|---|---|---|---|
| **P28** | Dual Autonomous Hermes (peer-to-peer minimum) | ★ YES | P19 + P20 + P22 runtime | 2-3 |
| **P29** | Sharing Intelligence + Shared World + Inner Dialogue rail | ★ YES | P28 soak OK | 1-2 |
| **P30** | Society Membership Dynamics + intimacy bridge | follow-up | P29 | 1-2 |
| **P31** | Formal Verification (ATL, λ_A-calculus lint) | ★ YES (governance) | P29 | 1-2 |
| **P32** | P24 Fork Integration (preferred optimization) | follow-up | P28 soak + P31 | 2-3 |
| **P33** | P23 Executor Integration (email/deploy/finance) | follow-up | P28 + P32 | 1-2 |
| **P34** | Closed-Loop Governance (audit telemetry, OPA, AAF) | ★ YES (governance) | P31 + P33 | 1-2 |
| **P35** | Anti-Collusion + Sycophancy Defense (production hardening) | follow-up | P34 | 1 |
| **P36** | Cross-VPS + Additional Society Members (Charybdis?) | end-state | P32-P35 | 2-3 |

### Critical Path

**P28 → P31 → P33 → P34** is the spine for governance + auditability. Other phases follow.

### Total Duration

12-15 months for full P28-P36, gated by:
- Each phase has a mandatory 24h soak window after `phase-complete` definition lands
- HARD STOP cascade tested per phase boundary (incorporates all required instances)
- Formal verification absorption into P31 lifecycle

### Forward 3 Deferred Deliverables (from P27 §19.1)

These were originally in the P19 §19.1/P36 supersedence map and now live in the P27-P36 roadmap §11.11 Absorption Map:

| Deliverable | Suggested Phase | Why deferred |
|---|---|---|
| AAF causal attribution audit | P31 | Requires P29 reflection rail + audit inventory |
| Anti-collusion pattern detection | P35 | Requires P33 executor integration to test |
| Closed-loop governance telemetry (GAAT/OPA) | P34 | Requires P31 formal verification patterns |

---

## §6 Hard Rejection Criteria — 20 / 20 PASS

Audit 14 (Hard Rejection Criteria) verified all 20 binary-checkable criteria PASS:

| # | Criterion | Verdict |
|---|---|---|
| 1 | FAIL if Pharsa defined as sub-agent / worker / persona label | ✅ PASS |
| 2 | FAIL if Guinevere positioned above Pharsa | ✅ PASS |
| 3 | FAIL if only one Hermes with labels/personas | ✅ PASS |
| 4 | FAIL if speaker selector / turn-taking coordinator | ✅ PASS |
| 5 | FAIL if shared `agent_id` namespaces | ✅ PASS |
| 6 | FAIL if persona_baseline SHA-256 tracking not enforced | ✅ PASS |
| 7 | FAIL if HARD STOP cascade doesn't include both agents + audit | ✅ PASS |
| 8 | FAIL if Pharsa has subordinate LLM call depth | ✅ PASS |
| 9 | FAIL if consent revocation can be bypassed by agent autonomy | ✅ PASS |
| 10 | FAIL if yandere escalation is mutual | ✅ PASS |
| 11 | FAIL if shared-brain / shared-vector-memory topology | ✅ PASS |
| 12 | FAIL if Persona's anti-sycophancy NOT defined | ✅ PASS |
| 13 | FAIL if Pharsa proactive-cognition conflicts with Y5 ceiling | ✅ PASS |
| 14 | FAIL if hard_rejection_criteria not binary-checkable | ✅ PASS |
| 15 | FAIL if agent_factory injection not feasible | ✅ PASS |
| 16 | FAIL if Guinevere can intercept Pharsa's outbound messages | ✅ PASS |
| 17 | FAIL if Pharsa can impersonate Guinevere | ✅ PASS |
| 18 | FAIL if scheduled heartbeats use shared Redis namespace | ✅ PASS |
| 19 | FAIL if `life_kernel:hard_stop` Redis key is project-scoped | ✅ PASS |
| 20 | FAIL if Society onboarding depends on P24 fork or P23 executors | ✅ PASS |

Full per-criterion evidence: `docs/setup-evidence/P27/evidence/audits/round-1/14-hard-rejection-criteria.md`.

---

## §7 Caveats

### 3 Non-Blocking Future Items (Round 2 Open Adjacent Issues)

Documented in `p27-round-2-fix-log.md` §8 — NOT blocking P27 finalization, deferred to downstream phases:

| # | Item | Future Phase |
|---|---|---|
| 1 | `kg_edges` CHECK constraint missing `'system'` value (asymmetry with `kg_entities`) | P28/P30 |
| 2 | §5.10 Replay Attack Defense table missing `idempotency_key` row | P28 review |
| 3 | `society_id` convention isolation documentation | P30 |

### Hard Caveats (Documented But Not Blocking)

| Caveat | Acknowledged In |
|---|---|
| Pharsa persona is referenced but NOT defined - planned for P29+ when peer dialogue rail is mature | Plan §10 + §18 disclaimers; Round-2 audit 04 PASS |
| P24 fork preferred but NOT required for P28 | Plan §14.8 L3294; Round-1 audit 07 PASS |
| P23 executors NOT needed for P28 minimum target | Plan §17 + roadmap §3; Round-1 audit 08 PASS |
| MAMA audit + 24h soak gating apply to P28 implementation, not P27 definition | Plan §24 + roadmap §11 |
| Audit 09 (safety boundary) was originally MISSING during early dispatch; re-run to PASS during Phase 6 fix cycle | Round-1 remaining issues #2 |

### Sensitive Topics Out-of-Scope

| Topic | Status |
|---|---|
| Pharsa voice | Deferred (P21 voice was SKIPPED); out-of-scope for P27 |
| Cross-VPS deployment | Deferred to P36 |
| Additional Society members beyond Guinevere + Pharsa | Deferred to P36 (Charybdis or future persona) |
| Anti-collusion / sycophancy at depth | P35 follow-up |

---

## §8 Next Action — P28 Implementation (Separate Phase)

P28 is a **separate phase** with its own:

| P28 must produce | Notes |
|---|---|
| P28 enterprise plan | Includes pre-flight checklist + per-step verification scaffold (per AGENTS.md §2.5) |
| P28 implementation waves | Sequenced per dependency map; collision scan before each batch |
| P28 evidence | Verification file with 12-section AGENTS.md §11 schema |
| P28 auditor gate | Round 1 + Round 2 audit structure |
| P28 ADR (if new architecture decisions emerge) | New ADR number or supersession of ADR-054 |

### P28 Pre-Flight Gate (Operator Responsibility)

Before P28 implementation starts, operator must verify:

- [ ] P27 verification report accepted
- [ ] P27 auditor gate PASS acknowledged
- [ ] P27 ADR-054 accepted
- [ ] Pharsa Discord bot persona definition approved (or explicitly deferred)
- [ ] P24 fork status (preferred optimization; explicit decision to proceed-with-fork or proceed-without-fork)
- [ ] 24h soak gate procedures defined (per AGENTS.md §0.1 + §3)

### P28 Implementation Order (Skeleton)

1. Backup PG + Redis (per ADR-032)
2. Create Pharsa config (`hermes-config/pharsa.yaml`)
3. Refactor single-instance anchors (`_memory_bridge`, `_cost_tracker`, etc. → per-instance scoped)
4. Migration 001-007 (per blueprint §2.6)
5. Create `pharsa-core.service` + `pharsa-discord.service`
6. Run migrations 008/009 (HPP outbox/inbox)
7. Wire HPP envelope (Pydantic `Envelope` model)
8. Wire `_cascade_halt()` (per Round-2 Fix 1)
9. Smoke test: both bots online, message flow
10. Canary soak 24h
11. Promote to production with audit + rollback evidence

---

## §9 Acceptance Statement

**P27 Hermes Society Foundation — DEFINITION COMPLETE.**

- All 37 deliverables produced and parent-verified
- 20 audit reports across 2 rounds all progressed to PASS or fixed
- 14 fixes applied surgically without architectural changes
- 20 / 20 hard rejection criteria PASS
- ARCHITECTURAL DECISIONS preserved (no breaking changes to existing ADRs)
- BOUNDARY COMPLIANCE verified (no secrets, no consent violations, no Y6, no HARD STOP bypass)
- ROLLBACK-RE-RUN SAFE (definition-only; no runtime changes; reversible via `git revert`)
- ADR-054 ACCEPTED
- AUDITOR GATE: PASS

### Operator Sign-Off

This final report is approved by Faiz via session instruction to finalize P27. P28 implementation is a SEPARATE phase with its own scope, schedule, evidence, and audit.

The next action is P28 kickoff, gated by the operator's per-phase approval discipline per AGENTS.md §0.1 + §3.

---

## §10 Footer

### Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent agent) | Initial P27 final report — executive summary |

### Maintenance

This final report is canonical for the P27 phase. It supersedes nothing and is not superseded by P28 (P28 has its own final report). Future references to P27 success/failure should cite this report.

### Operator Sign-Off

P27 Hermes Society Foundation **DEFINITION COMPLETE** (2026-06-28). Approved for handoff to P28.

---

> **Selesai.** Foundation defined. Society topology locked. P28 dapat mulai dengan confidence.

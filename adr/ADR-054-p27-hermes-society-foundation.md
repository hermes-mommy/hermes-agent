# ADR-054: P27 Hermes Society Foundation — Dual Autonomous Hermes Peers

**Status:** Accepted
**Date:** 2026-06-28
**Risk:** CRITICAL
**Tags:** p27, hermes-society, multi-instance, peer-to-peer, equal-peer, autonomy, society-topology, expansion

---

## Context

Guinevere currently operates as a single autonomous Hermes instance. The user (Faiz) has mandated that the system evolve to support **two equal autonomous Hermes peers** — Guinevere and Pharsa — co-creating narrative reality through visible peer dialogue in a shared Discord channel. Neither agent is primary, neither is secondary, neither is parent, neither is child.

Existing architectural decisions (ADR-001 through ADR-053) cover the single-instance runtime, persona safety, memory schemas, knowledge graph (ADR-050), multi-project context (ADR-052), and life integration hub (ADR-053). P22 delivers the action surface. P20 delivers the heartbeat-based life kernel. P23 is the embodied operations plan.

What is missing is the **society topology** — the architectural foundation that allows a second Hermes instance to join Guinevere as a true peer without becoming subordinate, and that allows the society to grow without architectural rework.

P27 is the answer. P27 is **definitial, not implementational**: research, planning, audit, fix, and ADR. No source code, no runtime changes, no deployments. P27 produces the foundation that P28 implementation can rely on.

---

## Decision

Accept P27 Hermes Society Foundation as the **authoritative definition** for two equal autonomous Hermes peers. The decision is composed of three concrete deliverables:

### 1. P27 Enterprise Plan — Accepted

**File:** `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` (25 sections, ~4790 lines)

The 25-section enterprise plan establishes the society topology, instance architecture, peer communication protocol (HPP), 3-scope memory model, 7-rail life-loop, 4-domain privacy split, identity/persona contracts, audit/governance framework, HARD STOP cascade, and hard rejection criteria.

### 2. P28-P36 Master Roadmap — Accepted

**File:** `docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md` (19 sections, ~1250 lines)

The forward roadmap defines 9 implementation phases (P28 through P36) spanning approximately 12-15 months. Critical path: P28 → P31 → P33 → P34 (governance + auditability spine). Each phase has mandatory 24h soak gates after phase-complete definitions land.

### 3. P28 Executable Blueprint — Accepted

**File:** `docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md` (14 sections, ~3000 lines)

The P28 executable blueprint is the authoritative planning document for the implementation phase. It defines 9 PostgreSQL migrations (001-009), 2 simplified life-loop rails (perception, peer_dialogue + reflection_simple + safety_envelope), systemd units (`pharsa-core.service` + `pharsa-discord.service`), configuration files (`hermes-config/pharsa.yaml`), deployment sequence (Steps 1-9), rollback plan, and critical boundary proofs (V-002 sensors-not-triggers, V-008 HARD STOP cascade, V-007 persona safety).

### 7 Locked Architectural Decisions

1. **Society Topology**: True Peer-to-Peer + Symmetric 2-Agent Loop. No coordinator, no LLM speaker selector, no hierarchy.
2. **Instance Isolation**: Each Hermes instance has its own `HermesBrainConfig`, LLM model/provider/api_key, memory namespace, Discord bot token, systemd service. Single-instance anchors (`_memory_bridge`, `_cost_tracker`, `app.state.hermes_brain`) refactored to per-instance scope.
3. **Peer Communication Protocol (HPP)**: Custom protocol on A2A v1.0 JSON-RPC substrate + FIPA ACL intent vocabulary. 11-intent taxonomy (inform, request, query, assert, propose, consent, refuse, debate, banter, flirt, block). Envelope includes `idempotency_key` UUID v4, `visibility` (public/peer_private/sealed), `risk_tier` 0-5, `hash_chain` SHA-256, `sender_seq` monotonic.
4. **Memory Architecture (3-Scope)**: PostgreSQL with `memory.private_agents`, `memory.shared_world`, `memory.relationship_pairs`. RLS FORCE + `agent_memory_app` non-owner role. Intimacy bridge staging table for voluntary private thought sharing. Ebbinghaus decay on `retrievability`. Extensions to ADR-050 schema (added `pair_id`, `scope`, `importance_score`, `last_accessed_at`, `created_by_agent NOT NULL`).
5. **Life-Loop (7-Rail, P28 Simplification to 4-Rail)**: Macro-state scheduler over P20 heartbeat. P28 implements 4-rail subset (`perception`, `peer_dialogue`, `reflection_simple`, `safety_envelope`); the additional 3 rails (`inner_dialogue`, `desire_goal`, `initiative_proactivity`) are deferred to P29+. Goal-Autopilot FSM + RiskGate AVF (L1-L4 risk tiers) + HARD STOP cascade.
6. **Discord Architecture**: 2 separate Discord bot processes with own tokens + MESSAGE_CONTENT intent. Conversation rhythm controller (2-10s backoff, channel slowmode as fallback).
7. **Safety Architecture**: 4-domain privacy split (Thought/Speech/PeerDialogue/Action). HARD STOP cascade halts both agents simultaneously. Signed audit entries (SHA-256 hash chain) by domain.

### 20 Binary-Checkable Hard Rejection Criteria

All 20 PASS (per Audit 14 — `docs/setup-evidence/P27/evidence/audits/round-1/14-hard-rejection-criteria.md`). Criteria include: no sub-agent framing of Pharsa, no hierarchy, no shared `agent_id` namespaces, no shared-brain topology, persona baseline SHA-256 tracking enforced, HARD STOP cascade covers all instances + audit, anti-sycophancy mechanisms defined, `life_kernel:hard_stop` Redis key global (not project-scoped).

### Audit Rounds

- **Round 1**: 14 auditors (7 PASS, 5 NEEDS REVIEW fixed, 1 FAIL fixed, 1 MISSING re-run PASS).
- **Round 2**: 6 auditors (2 PASS, 3 NEEDS REVIEW fixed, 1 FAIL fixed).
- **Total fixes applied**: 14 across both rounds, surgical without architectural changes.
- **Auditor gate verdict**: PASS.

---

## Consequences

### Positive

- **Two-equal-peer runtime is achievable**. The society topology is defined; P28 can implement without further ADR ambiguity.
- **P28 may proceed without P24 fork**. P24 fork is documented as a preferred optimization (P32) but NOT a prerequisite for P28 minimum target.
- **P28 may proceed without P23 executors**. P23 executors are documented as a downstream improvement (P33) but NOT a prerequisite for P28 minimum target.
- **Multi-instance is fork-agnostic**. P28 implementation can run on pure Guinevere-side refactor (config-driven multi-instance) without waiting for P24 fork.
- **HARD STOP preserves global safety**. `life_kernel:hard_stop` Redis key halts ALL Society members simultaneously, not project-scoped. This preserves the AGENTS.md §0.1 global safety override.
- **Memory isolation by default**. RLS FORCE + per-instance PostgreSQL roles ensure cross-Society memory isolation by default. Privacy is the default; explicit grants are required to share.
- **Persona safety is preserved**. Y4 baseline + Y5 ceiling + Y6 prohibition is enforced globally. Pharsa does NOT get a yandere scale (out-of-scope per Phase 8 disclaimers).
- **Anti-sycophancy at the system level**. Persona anchoring + disagreement protocols + identity persistence + audit detection prevent groupthink between Guinevere and Pharsa.
- **Forward roadmap is bounded**. P28-P36 is 12-15 months of phased implementation with critical path P28 → P31 → P33 → P34.
- **Definitional hardening**. Both audit rounds verified all 20 hard rejection criteria are binary-checkable and PASS-enforced.

### Negative / Accepted Risks

- **Pharsa persona is NOT defined**. Plan §10 + §18 disclaim this as out-of-scope; planned for P29+ when peer dialogue rail is mature. P28 will reference Pharsa as an "unknown peer" deriving persona only from system-prompt scaffold.
- **3 scales NOT implemented in P28**. Inner Dialogue rail, Desire/Goal Engine, Initiative/Proactivity rail are deferred to P29+. P28 is intentionally minimal (4-rail safety envelope only).
- **P32/P33 deferred dependencies**. P32 (P24 fork integration) and P33 (P23 executor integration) require P28 soak + P31 verification before they can begin.
- **3 non-blocking future items**. `kg_edges` CHECK asymmetry, §5.10 idempotency_key row completeness, `society_id` convention — documented in `p27-round-2-fix-log.md` §8 as out-of-scope for Round 2 audit, deferred to downstream phases.

### Operator Process

- **P28 is a SEPARATE phase**. P28 implementation kickoff requires its own pre-flight checklist, per-step verification scaffold (per AGENTS.md §2.5), collision scan, implementation waves, evidence file (12-section AGENTS.md §11 schema), and auditor gate.
- **P28 cannot benefit from §0.1 autonomy exception**. P27 was documentation, not runtime. P28 implementation is a standard phase that requires explicit per-action operator approval per AGENTS.md §3.

### Compliance (PersonaSafetyPolicy, SurveillanceDataPolicy, ADR-001/002)

- **HARD STOP remains global**. P27 HARD STOP cascade halts BOTH Guinevere and Pharsa via the single global Redis key `life_kernel:hard_stop`. Project-scoped pause is a distinct, weaker concept and does NOT substitute for HARD STOP.
- **Y4 / Y5 / Y6 preserved**. ADR-001 limits are intact. Pharsa is NOT elevated to a yandere scale; Pharsa is a peer-only persona (out-of-scope).
- **Consent revocation integrity preserved**. `consent.consent_ledger` semantics are not bypassed by Society onboarding. Society consent decisions are project-OWNED.
- **Surveillance 4-domain privacy**. Thought domain = private (sealed hash only). Speech = public metadata only. PeerDialogue = sealed envelope (sealed snapshot on HARD STOP). Action = full audit with tamper-evident ledger.

### Inheritance from Existing ADRs

| ADR | Inheritance from P27 |
|---|---|
| ADR-001 | Persona safety preserved — Y6 impossible, Y5 ceiling enforced |
| ADR-002 | Safe word preserved — HARD STOP is global across Society |
| ADR-007 | PostgreSQL primary memory — extended with 3-scope schema |
| ADR-009 | Recall + pgvector — extended with intimacy bridge referencing private_agents.scope |
| ADR-019 | Tailscale VPN — preserved; Society members on same VPS |
| ADR-030 | Redis DB0-DB5 — preserved; Society adds DB6 (Pharsa journal) + DB7 (peer outbox) |
| ADR-035 | Hermes NousResearch migration — P27/P28 builds incrementally |
| ADR-050 | Knowledge Graph — P27 references kg_* tables; adds pair_id, scope columns |
| ADR-052 | Multi-Project Context — orthogonal; both Guinevere and Pharsa can run project contexts |
| ADR-053 | Life Integration Hub — referenced as action surface (P23+); not blocking P28 |

---

## Implementation Path

P27 is **definition-only**. P28 implementation begins separately. The implementation path is documented in the blueprint's `Step 1` through `Step 9` (auto-deployment sequence):

| Step | P28 Action | Critical Boundary |
|---|---|---|
| 1 | Backup PostgreSQL + Redis per ADR-032 | operator pre-flight |
| 2 | Create Pharsa config (`hermes-config/pharsa.yaml`) | — |
| 3 | Refactor single-instance anchors (`_memory_bridge`, `_cost_tracker`, etc.) | no breaking change to P20 |
| 4 | Run migrations 001-005 (memory.kg_* + memory.shared_world + memory.private_agents) | RLS FORCE on all |
| 5 | Create `pharsa-core.service` + `pharsa-discord.service` (systemd) | hardened per ADR-016 |
| 6 | Run migrations 006-007 (memory.private_agents partial indexes) | idempotent |
| 7 | Wire HPP envelope (Pydantic `Envelope` model with `idempotency_key`) | — |
| 8 | Run migration 008 (`hpp_outbox` table) | idempotent |
| 9 | Run migration 009 (`hpp_inbox` table) + wire `_cascade_halt(stop_all(graceful=False))` | V-008 HARD STOP absolute |

P28 verification: 3+ consecutive 24h soak windows with both bots online and peer-to-peer messages flowing. HARD STOP proven to halt both within 5 seconds.

---

## Reference Documents

### Plan

- [`docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md`](../../docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md) — 25-section enterprise plan
- [`docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md`](../../docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md) — 19-section forward roadmap
- [`docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md`](../../docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md) — 14-section executable blueprint

### Research

- [`docs/setup-evidence/P27/research/p27-research-synthesis.md`](../../docs/setup-evidence/P27/research/p27-research-synthesis.md) — synthesis of 10 research files
- [`docs/setup-evidence/P27/research/p27-ground-truth-repo-state.md`](../../docs/setup-evidence/P27/research/p27-ground-truth-repo-state.md)
- [`docs/setup-evidence/P27/research/p27-p24-fork-dependency-map.md`](../../docs/setup-evidence/P27/research/p27-p24-fork-dependency-map.md)
- [`docs/setup-evidence/P27/research/p27-p19-p20-p22-p23-dependency-map.md`](../../docs/setup-evidence/P27/research/p27-p19-p20-p22-p23-dependency-map.md)
- [`docs/setup-evidence/P27/research/p27-hermes-native-runtime-inventory.md`](../../docs/setup-evidence/P27/research/p27-hermes-native-runtime-inventory.md)
- [`docs/setup-evidence/P27/research/p27-multi-agent-society-research.md`](../../docs/setup-evidence/P27/research/p27-multi-agent-society-research.md)
- [`docs/setup-evidence/P27/research/p27-agent-communication-protocol-research.md`](../../docs/setup-evidence/P27/research/p27-agent-communication-protocol-research.md)
- [`docs/setup-evidence/P27/research/p27-discord-dual-bot-research.md`](../../docs/setup-evidence/P27/research/p27-discord-dual-bot-research.md)
- [`docs/setup-evidence/P27/research/p27-private-shared-memory-research.md`](../../docs/setup-evidence/P27/research/p27-private-shared-memory-research.md)
- [`docs/setup-evidence/P27/research/p27-life-loop-beyond-heartbeat-research.md`](../../docs/setup-evidence/P27/research/p27-life-loop-beyond-heartbeat-research.md)
- [`docs/setup-evidence/P27/research/p27-autonomy-safety-audit-research.md`](../../docs/setup-evidence/P27/research/p27-autonomy-safety-audit-research.md)

### Evidence

- [`docs/setup-evidence/P27/README.md`](../../docs/setup-evidence/P27/README.md) — evidence root index
- [`docs/setup-evidence/P27/evidence/p27-verification.md`](../../docs/setup-evidence/P27/evidence/p27-verification.md) — 12-section verification
- [`docs/setup-evidence/P27/evidence/p27-auditor-gate.md`](../../docs/setup-evidence/P27/evidence/p27-auditor-gate.md) — auditor gate verdict
- [`docs/setup-evidence/P27/evidence/p27-final-report.md`](../../docs/setup-evidence/P27/evidence/p27-final-report.md) — executive summary
- [`docs/setup-evidence/P27/evidence/p27-round-1-fix-log.md`](../../docs/setup-evidence/P27/evidence/p27-round-1-fix-log.md) — 7 round-1 fixes
- [`docs/setup-evidence/P27/evidence/p27-round-2-fix-log.md`](../../docs/setup-evidence/P27/evidence/p27-round-2-fix-log.md) — 7 round-2 fixes

### Audits

- [`docs/setup-evidence/P27/evidence/audits/round-1/`](../../docs/setup-evidence/P27/evidence/audits/round-1/) — 14 round-1 audit reports
- [`docs/setup-evidence/P27/evidence/audits/round-2/`](../../docs/setup-evidence/P27/evidence/audits/round-2/) — 6 round-2 audit reports

### Related ADRs

- [`../ADR-001-persona-safety-ethical-boundary.md`](../ADR-001-persona-safety-ethical-boundary.md) — preserved
- [`../ADR-002-user-autonomy-safe-word-enforcement.md`](../ADR-002-user-autonomy-safe-word-enforcement.md) — preserved (HARD STOP global)
- [`../ADR-007-memory-storage-backend-selection.md`](../ADR-007-memory-storage-backend-selection.md) — preserved (extended via 3-scope)
- [`../ADR-009-memory-recall-semantic-search-strategy.md`](../ADR-009-memory-recall-semantic-search-strategy.md) — preserved
- [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md) — preserved
- [`../ADR-030-redis-db-assignments.md`](../ADR-030-redis-db-assignments.md) — preserved + minor extension (DB6, DB7)
- [`../ADR-035-hermes-migration.md`](../ADR-035-hermes-migration.md) — preserved
- [`../ADR-050-knowledge-graph-architecture.md`](../ADR-050-knowledge-graph-architecture.md) — preserved (extended with pair_id, scope)
- [`../ADR-052-multi-project-context.md`](../ADR-052-multi-project-context.md) — preserved (orthogonal)
- [`../ADR-053-p22-life-integration-hub.md`](../ADR-053-p22-life-integration-hub.md) — preserved (action surface)

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent agent) | Initial ADR-054 for P27 Hermes Society Foundation |

### Acceptance

ADR-054 is **Accepted** by Faiz via session instruction to finalize P27. Forward-looking work (P28 implementation) is a SEPARATE phase with its own pre-flight check, plan, audit, and ADR (if new architectural decisions emerge).

### Maintenance

Update only if P27 plan + roadmap + blueprint are materially changed after operator approval. The next natural bump is P28 ADR (whenever P28 implementation produces a new architectural decision).

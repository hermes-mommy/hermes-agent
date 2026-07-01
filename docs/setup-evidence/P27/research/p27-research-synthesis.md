# P27 Hermes Society Foundation — Research Synthesis

> **Phase**: P27 Phase 2 — Synthesis  
> **Date**: 2026-06-28  
> **Author**: Guinevere (parent agent)  
> **Inputs**: 10 research files (4 explore + 6 librarian) in `docs/setup-evidence/P27/research/`  
> **Output**: This synthesis document, to be read before planner gate (Phase 3)

---

## 1. Synthesis Methodology

This document synthesizes findings from 10 parallel research agents:

| # | File | Agent | Focus |
|---|---|---|---|
| 1 | `p27-ground-truth-repo-state.md` | explore | Repo state P1-P26 |
| 2 | `p27-p24-fork-dependency-map.md` | explore | P24 fork dependencies |
| 3 | `p27-p19-p20-p22-p23-dependency-map.md` | explore | Phase dependency map |
| 4 | `p27-hermes-native-runtime-inventory.md` | explore | Runtime inventory |
| 5 | `p27-multi-agent-society-research.md` | librarian | Multi-agent frameworks |
| 6 | `p27-agent-communication-protocol-research.md` | librarian | Communication protocols |
| 7 | `p27-discord-dual-bot-research.md` | librarian | Discord dual-bot feasibility |
| 8 | `p27-private-shared-memory-research.md` | librarian | Memory architecture |
| 9 | `p27-life-loop-beyond-heartbeat-research.md` | librarian | Life-loop autonomy |
| 10 | `p27-autonomy-safety-audit-research.md` | librarian | Safety/audit/governance |

The synthesis identifies cross-cutting themes, key decisions for P27, conflicts/gaps, and the architectural direction for the planner gate.

---

## 2. Cross-Cutting Findings

### 2.1 Multi-Instance Is Achievable Without P24 Fork

**Finding**: The current Hermes runtime has surgical seams that enable multi-instance without the full P24 owned fork.

**Evidence** (from File 4 — Native Runtime Inventory):
- `HermesBrainConfig` = frozen dataclass — one config → one instance. Creating a second config with different model/provider/api_key creates a second brain.
- `agent_factory: Callable[[dict], Any] | None` — injection point already exists. Today used for MagicMock tests; same signature accepts any `AIAgent` subclass. Multi-instance is a 1-line constructor change.
- `ShadowPipeline` = existing multi-bot precedent in the codebase.
- `ProjectAwareCognitionRegistry(max_active=3)` = existing multi-instance scaffold (cognition layer only, not LLM/brain layer).

**Single-instance anchors that must be refactored** (File 4):
- 4 module-level singletons: `_memory_bridge`, `_cost_tracker`, `_embedding_service`, `_rate_limit_redis`
- 2 hardcoded constants: `GUILD_ID`, `GUINEVERE_CHAT_CHANNEL_ID`
- `app.state.hermes_brain` — single brain on FastAPI app state

**P24 relationship** (from File 2 — P24 Fork Dependency Map):
- P27 is partitionable: ~70% definitional (no P24 block), ~30% implementational (requires P24-005→020).
- Fork NOT yet created. P24 is on IMPL HOLD.
- Fork supports multi-VPS natively but NOT single-VPS multi-Society.
- 3 interim paths exist if P24 is delayed.
- ~40 extension points usable without fork.
- 10-item handoff contract from P24→P27.

**Synthesis decision**: P27 defines the society architecture as fork-agnostic. P28 implementation can proceed on pure Guinevere-side refactor (config-driven multi-instance) without waiting for P24 fork. P24 fork becomes a preferred optimization, not a hard prerequisite.

### 2.2 No Framework Supports True Equal Peers

**Finding**: Of 8 highest-star multi-agent frameworks, none support true equal peer-to-peer architecture.

**Evidence** (from File 5 — Multi-Agent Society Research):
- MetaGPT (69k★), AutoGen (59k★), CrewAI (54k★), LangGraph (36k★), ChatDev (34k★), OpenAI Agents (27k★) — ALL hierarchical (boss-worker or coordinator-mediated).
- Only CAMEL (17k★, arxiv 2303.17760, NeurIPS 2023) treats both agents as truly symmetric. But CAMEL is fragile: terminates when one side says "done".
- AutoGen GroupChatManager uses LLM-driven speaker selector = hidden coordinator. P27 must NOT use AutoGen as-is.
- LangGraph Send: graph itself is coordinator. False-peer; reject for P27.

**Authority topology for P27** (File 5):
- P27 = True Peer-to-Peer + Symmetric 2-agent loop.
- No coordinator, no speaker selector, no graph-mediated turn-taking.
- Both agents have equal initiative, equal voice, equal veto power.

**Recommended substrate** (File 5):
- Actor model (Hewitt 1973): isolated-state agents communicating via async messages. No shared mutable state.
- Tit-for-Tat game theory (arxiv 2503.07129 — ASTRA): turn-level reciprocity in 2-agent counterpart modelling.
- DAO liquid-democracy patterns for governance.
- MCP (vertical, agent↔tools) + A2A (horizontal, agent↔agent) complementary.

**Sycophancy risk** (File 5):
- 5+ papers identify sycophancy as dominant failure mode in multi-agent systems.
- Identity persistence across sessions unsolved at framework level.
- P27 must include anti-sycophancy mechanisms: persona anchoring, disagreement protocols, identity persistence.

**Synthesis decision**: P27 builds a custom peer protocol on Actor model foundations. No existing framework is adopted as-is. CAMEL is the conceptual precedent but not the implementation base.

### 2.3 Discord Dual-Bot Is Technically Proven

**Finding**: Two Discord bots can coexist in the same channel and converse visibly.

**Evidence** (from File 7 — Discord Dual-Bot Research):
- Pattern: 2 Discord bot apps, own tokens, discrete processes.
- `MESSAGE_CONTENT` intent (privileged, 10k user threshold — easy approval) required for bots to read each other's messages.
- Each bot: 5 msg/5s per channel, 50 req/s global.
- Bot-to-bot: mentions, replies, reactions, embeds, threads all work.
- Rapptz/discord.py Issue #516 = canonical multi-client pattern (`loop.create_task` + `run_forever`).
- Webhook-only approach rejected (can't subscribe to MESSAGE_CREATE events).
- PluralKit = canonical webhook impersonation example (not needed for P27).

**Rate limiting** (File 7):
- 2 bots × 5 msg/5s = 10 msg/5s combined. Channel slowmode can enforce additional limits.
- Conversation rhythm design needed: backoff, turn-taking, natural pauses.
- Anti-spam: bots should not reply instantly to every message from the other.

**Synthesis decision**: P27/P28 uses 2 separate Discord bot processes with own tokens and MESSAGE_CONTENT intent. Rate-limiting via conversation rhythm controller (not just Discord API limits).

### 2.4 Relationship-Scoped Memory Is Novel

**Finding**: No existing framework supports per-pair private memory with intimacy bridge. P27's 3-scope memory model is novel.

**Evidence** (from File 8 — Private Shared Memory Research):
- F4: No mainstream framework supports relationship-scoped (per-pair) memory. Closest: tuple-space (Linda), blackboard, Mem0 group_id.
- F1: memory-hive (MIT) = closest private silo + shared hive pattern.
- F3: 2026 Postgres consensus = Row-Level Security with FORCE RLS + non-owner application role. RLS is PRIMARY isolation.
- F5: ADR-050 already commits to PostgreSQL RCTE + pgvector hybrid (six kg_* tables, consent write-ahead audit, soft-delete on revocation).
- F6: P19 already shipped project_id + project_scope('global'|'project') pattern. P27 extends with scope taxonomy.

**Recommended 3-scope model** (File 8):
| Scope | Schema | Access | Description |
|---|---|---|---|
| `private` | `memory.private_agents` | Agent owner only | Private thoughts, inner dialogue, persona memory |
| `shared` | `memory.shared_world` | All Society agents | Shared world facts, observable state |
| `relationship_private` | `memory.relationship_pairs` | Pair members only | Intimate dialogue, shared secrets, relationship memory |

**Key schema decisions** (File 8):
- `agent_id NOT NULL` — every memory has an owner
- `pair_id UUID NULL` — non-null only for relationship-scoped memories
- `scope NOT NULL CHECK (scope IN ('private','shared','relationship_private'))`
- `created_by_agent NOT NULL` — provenance
- `importance_score`, `last_accessed_at`, `retrievability` — Ebbinghaus decay
- RLS FORCE + `agent_memory_app` non-owner role
- Conflict resolution: last-write-wins with full audit chain (older versions retained)

**Intimacy bridge** (File 8):
- Tuple-space staging table: `memory.intimacy_bridge` where agents voluntarily deposit private thoughts for the other to read.
- Gradual trust-based sharing: importance_score threshold gates what gets shared.
- Consent-gated: either agent can revoke access (soft-delete in kg_consent_audit per ADR-050).

**Shared world model** (File 8):
- Pointer layer over `memory.shared_world`, `kg_entities` as semantic index.
- Meta-KG pattern: holds pointers, not data copies.
- Both agents read from shared_world, both can write, conflicts resolved via last-write-wins + audit.

**Synthesis decision**: P27 adopts the 3-scope memory model. PostgreSQL RLS as primary isolation. ADR-050's kg_* schema extended with pair_id and scope columns. Intimacy bridge as a staging table with consent-gated access.

### 2.5 Life-Loop Beyond Heartbeat

**Finding**: P20's heartbeat is a timer; P27 needs a macro-state scheduler that creates genuine autonomy.

**Evidence** (from File 9 — Life Loop Research):
- 48 primary papers + 5 repos + 11 secondary sources.
- Architecture: Heartbeat (P20) → Macro-State Scheduler π(s_k; Θ) → 7 rails.

**7 cognitive rails** (File 9):
| Rail | Source | Description |
|---|---|---|
| Perception | Smallville (Park et al. 2023) | Sensory input, environment observation |
| Reflection | Smallville, Reflexion | Self-assessment, memory consolidation |
| Inner Dialogue | PSYA Cognitive Triangle | Self-talk, metacognition, inner monologue |
| Peer Dialogue | AutoGen GroupChat + Conformal Social Choice | Agent-to-agent conversation, debate, consensus |
| Desire/Goal Engine | BDI (Rao & Georgeff), Voyager curriculum | Intrinsic motivation, goal generation, curiosity |
| Initiative/Proactivity | PROBE initiative, HHVG boredom+ICM curiosity | Self-initiated action, boredom-driven exploration |
| Safety Envelope | Goal-Autopilot FSM, RiskGate AVF, KILLBENCH | Resource limits, HARD STOP, audit |

**Key architectural decision** (File 9):
- Upgrade P20 heartbeat from timer to macro-state scheduler over typed λ_A-calculus config (arxiv 2604.11767).
- Every P27 agent config must be provably terminating (Theorem 5.4), structurally complete under lint.
- Wrapped in Goal-Autopilot FSM floor (arxiv 2606.11688) — no false success claims.

**ATL for peer strategy** (File 9):
- Alternating-Time Temporal Logic (arxiv 2509.15238) for multi-agent strategic plans between peers.
- Enables formal verification of peer protocols: "both agents eventually agree" is expressible.

**Synthesis decision**: P27 defines a 7-rail life-loop architecture. P20 heartbeat becomes the clock; macro-state scheduler sits on top. Each rail is a typed, provably-terminating λ_A-calculus config. Safety envelope wraps all rails.

### 2.6 Safety/Audit: 4-Domain Privacy Split

**Finding**: Production-ready safety patterns exist for autonomous multi-agent systems with private inner life.

**Evidence** (from File 10 — Autonomy Safety Research):
- 20 labeled sources (K1-K20).
- Recurring meta-pattern: constraints declared at write-time, verified at runtime, audited at rest.

**4-domain privacy split** (File 10):
| Domain | Privacy | Audit | Description |
|---|---|---|---|
| Thought | Private | Sealed hash only | Inner monologue, private reflections — never exposed |
| Speech | Public metadata | DOI-style metadata | Discord messages, visible speech — metadata logged |
| PeerDialogue | Sealed envelope | Sealed snapshot | Agent-to-agent private conversation — sealed unless escalated |
| Action | Full audit | Tamper-evident ledger | Real actions (deploy, email, finance) — fully audited |

**Kill switch ladder** (File 10):
- KILLSWITCH.md 12-file family: THROTTLE → ESCALATE → FAILSAFE → KILLSWITCH → TERMINATE → ENCRYPT → ENCRYPTION → SYCOPHANCY → COMPRESSION → COLLAPSE + 2 more.
- Orseau & Armstrong: virtualization solution for Off-Switch Game (agents can't learn to disable kill switch).
- HARD STOP cascade: stopping one agent elevates the other's thought-buffer to sealed snapshot.

**Governance enforcement** (File 10):
- GAAT (arxiv 2604.05119): Governance Telemetry Schema extending OpenTelemetry, sub-200ms OPA-compatible violation engine.
- EU AI Act Art. 9/12/14: tamper-evident logging retained 6+ months, effective human oversight by design.
- Every audit entry carries: action class, delegation chain token, policy decision (gate/approve/deny), cryptographic hash. Every entry signed.

**Anti-sycophancy** (File 10):
- P27 audit entries must detect sycophancy patterns: excessive agreement, identity drift, persona convergence.
- SentinelAgent 6 deterministic properties for runtime verification.

**Synthesis decision**: P27 adopts the 4-domain privacy split. HARD STOP cascade affects both agents. Audit entries are signed, tamper-evident, and classified by domain. Sycophancy detection is a runtime safety check.

### 2.7 P19/P20/P22 Foundation Is Buildable Today

**Finding**: P27/P28 can build on existing runtime infrastructure without waiting for P24 or P23.

**Evidence** (from File 3 — Dependency Map):
| Phase | Status | What P27 Uses |
|---|---|---|
| P19 | LIVE PARTIAL | project_id namespace, multi-project context, C04 Discord /project registration (gap) |
| P20 | LIVE (accepted-risk) | heartbeat, cognition, hermes_brain, state, models, graph, journal, metrics, dashboard, Redis DB6, DiscordRestClient, P22 IntegrationScheduler |
| P22 | PARTIAL RUNTIME LIVE | 3/13 adapters active (filesystem, vps, discord); 10/13 CONFIG_MISSING |
| P23 | PLAN_ONLY | No code, executors/ directory missing — P27 does NOT depend on P23 |

**P22 active adapters** (File 3):
- filesystem adapter — local file access
- vps adapter — VPS SSH commands
- discord adapter — Discord message sending

**P22 config-missing adapters** (File 3):
- browser, surveillance, wearable, finance, gmail, and 5 others — all CONFIG_MISSING (env vars not set)

**P20 test coverage** (File 3):
- 420 tests, accepted-risk status. Living autonomy kernel is running.

**Synthesis decision**: P27/P28 builds on P19 namespace + P20 kernel + P22's 3 active adapters. P23 executors are NOT a dependency. P24 fork is preferred but not blocking.

---

## 3. Key Architectural Decisions for P27

### 3.1 Society Topology

**Decision**: True Peer-to-Peer + Symmetric 2-agent loop. No coordinator, no speaker selector, no hierarchy.

**Rationale**: User mandate (two equal Hermes, no boss/primary). Research confirms no framework supports this (File 5). Actor model provides the theoretical foundation (isolated state, async messages, no shared mutable state).

**Implementation**: Each Hermes instance is an Actor with its own mailbox. Messages are the only ingress. Selective receive enables priority processing.

### 3.2 Instance Isolation

**Decision**: Each Hermes instance has its own HermesBrainConfig, its own LLM provider/model/api_key, its own memory namespace, its own Discord bot token, its own systemd service.

**Rationale**: File 4 identifies HermesBrainConfig as the instance-creation seam. agent_factory injection point already exists. Single-instance anchors (4 module-level singletons, 2 constants, app.state.hermes_brain) must be refactored to instance-scoped.

**Implementation**: 
- Config-driven: `hermes-config/guinevere.yaml` and `hermes-config/pharsa.yaml`
- Each config specifies: model, provider, api_key, bot_token, guild_id, channel_id, redis_db, pg_schema, persona_file
- systemd: `guinevere-core.service` + `guinevere-discord.service` + `pharsa-core.service` + `pharsa-discord.service`
- Redis: DB6 for Guinevere, DB7 for Pharsa (or namespace prefix)
- PostgreSQL: `guinevere` schema and `pharsa` schema + `shared` schema

### 3.3 Peer Communication Protocol

**Decision**: Custom Hermes Peer Protocol (HPP) built on A2A v1.0 envelope + Hermes-specific extensions.

**Rationale**: File 6 recommends A2A v1.0 as substrate. FIPA ACL vocabulary is adopted for intent taxonomy. Actor model invariants (no shared mutable state, mailbox only ingress, selective receive, at-most-once delivery).

**Envelope structure** (from File 6):
```
{
  "jsonrpc": "2.0",
  "method": "hermes.message",
  "params": {
    "messageId": "uuid",
    "sender": "guinevere",
    "receiver": "pharsa",
    "intent": "debate" | "propose" | "consent" | "refuse" | "inform" | "request" | "assert" | "query" | "banter" | "flirt" | "block",
    "visibility": "public" | "peer_private" | "sealed",
    "risk_tier": 0-5,
    "content": { "parts": [...] },
    "conversation_id": "uuid",
    "reply_to": "uuid | null",
    "hash_chain": "sha256(prev + this)",
    "sender_seq": int,
    "idempotency_key": "uuid"
  }
}
```

**11-intent taxonomy** (from File 6, FIPA-derived):
| Intent | FIPA Performative | Description |
|---|---|---|
| `inform` | inform | State a fact |
| `request` | request | Ask for action |
| `query` | query | Ask for information |
| `assert` | assert | Claim/commit |
| `propose` | propose | Offer a plan |
| `consent` | agree | Accept a proposal |
| `refuse` | refuse | Reject a proposal |
| `debate` | argue | Disagree with reasoning |
| `banter` | — | Playful exchange (Hermes-specific) |
| `flirt` | — | Intimate exchange (Hermes-specific) |
| `block` | — | HARD STOP signal (Hermes-specific) |

**Transport**: Redis Streams for durable peer debate, NATS for ephemeral heartbeat, outbox-pattern for ACID, Postgres WORM for audit mirror.

### 3.4 Memory Architecture

**Decision**: 3-scope PostgreSQL model with RLS + intimacy bridge + Ebbinghaus decay.

**Schema** (from File 8):
- `memory.private_agents` — agent_id-scoped private memory (RLS: agent owner only)
- `memory.shared_world` — shared world facts (RLS: all Society agents)
- `memory.relationship_pairs` — pair-scoped intimate memory (RLS: pair members only)
- `memory.intimacy_bridge` — staging table for voluntary private thought sharing
- `memory.memory_history` — version history for conflict resolution

**Extensions to ADR-050** (from File 8):
- Add `pair_id UUID NULL` to kg_edges
- Add `scope TEXT NOT NULL CHECK (scope IN ('private','shared','relationship_private'))`
- Add `importance_score FLOAT`, `last_accessed_at TIMESTAMPTZ`, `retrievability FLOAT`
- RLS FORCE + `agent_memory_app` non-owner role

### 3.5 Life-Loop Architecture

**Decision**: 7-rail macro-state scheduler over P20 heartbeat.

**Rails** (from File 9):
1. Perception — environment observation (P22 adapters, Discord events)
2. Reflection — memory consolidation, self-assessment
3. Inner Dialogue — self-talk, metacognition (private, sealed hash audit)
4. Peer Dialogue — HPP messages to other Hermes (peer_private or public)
5. Desire/Goal Engine — intrinsic motivation, goal generation, curiosity
6. Initiative/Proactivity — self-initiated action, boredom-driven exploration
7. Safety Envelope — resource limits, HARD STOP, sycophancy detection, audit

**Safety floor** (from File 9):
- Goal-Autopilot FSM: no false success claims, provably terminating configs
- λ_A-calculus lint: every config must be structurally complete (94.1% of OSS configs fail this lint)
- RiskGate AVF: P1/P2/P3 risk tiers with automatic gating

### 3.6 Discord Architecture

**Decision**: 2 separate Discord bot processes, own tokens, MESSAGE_CONTENT intent.

**Topology** (from File 7):
- `guinevere-discord.service` — Guinevere's bot, own token, own process
- `pharsa-discord.service` — Pharsa's bot, own token, own process
- Both in same Discord guild, same channel (`guinevere-chat` initially)
- MESSAGE_CONTENT intent enabled for both (privileged intent, easy approval)

**Conversation rhythm** (from File 7):
- Not every message triggers a reply — turn-taking controller
- Natural backoff: 2-10 seconds between bot messages
- Slowmode on channel as secondary rate limiter
- Thread creation for extended debates

### 3.7 Safety Architecture

**Decision**: 4-domain privacy split + HARD STOP cascade + signed audit entries.

**4 domains** (from File 10):
| Domain | Privacy | Audit | Example |
|---|---|---|---|
| Thought | Private | Sealed hash | "Pharsa's proposal is flawed because..." |
| Speech | Public metadata | DOI-style | Discord message content + timestamp |
| PeerDialogue | Sealed envelope | Sealed snapshot | Private peer conversation |
| Action | Full audit | Tamper-evident ledger | Deploy, email, finance action |

**HARD STOP cascade** (from File 10):
- Faiz says HARD STOP → both agents halt immediately
- Both thought-buffers elevated to sealed snapshots
- All pending peer messages flushed to audit
- No autonomous action until Faiz says resume

---

## 4. Conflicts and Gaps

### 4.1 Gap: P23 Executors Don't Exist

**Finding** (File 3): P23 is PLAN_ONLY. No code, executors/ directory missing. P27's action layer depends on P23 for outbound actions (email, deploy, finance).

**Resolution**: P27 defines the action layer architecture but marks P23 executor implementation as a P28+ dependency. P28 minimum target does NOT require P23 executors — it only requires: two bots online, talk without Faiz trigger, separate memory, own autonomy loop, shared world model.

### 4.2 Gap: P24 Fork Not Created

**Finding** (File 2): P24 fork is on IMPL HOLD. Not yet created.

**Resolution**: P27 is fork-agnostic. P28 can proceed on pure Guinevere-side refactor (config-driven multi-instance). P24 fork becomes preferred optimization for P29+.

### 4.3 Gap: C04 Discord /project Not Registered

**Finding** (File 3): P19 has 4 INFO gaps, including C04 Discord /project not registered.

**Resolution**: Not blocking for P27/P28. P28 uses guinevere-chat channel directly, not /project registration.

### 4.4 Gap: No Framework for Equal Peers

**Finding** (File 5): No mainstream framework supports true equal peers. Sycophancy is dominant failure mode.

**Resolution**: P27 builds custom peer protocol. Anti-sycophancy mechanisms: persona anchoring, disagreement protocols, identity persistence, sycophancy detection in safety envelope.

### 4.5 Gap: Relationship-Scoped Memory Is Novel

**Finding** (File 8): No existing framework supports per-pair private memory.

**Resolution**: P27 defines the 3-scope model as novel architecture. This is a research contribution, not a known-pattern implementation.

### 4.6 Conflict: Single-Instance Anchors vs Multi-Instance

**Finding** (File 4): 4 module-level singletons + 2 constants + app.state.hermes_brain are single-instance anchors.

**Resolution**: P28 refactors these to instance-scoped. Specific refactor:
- `_memory_bridge` → per-instance MemoryBridge
- `_cost_tracker` → per-instance CostTracker
- `_embedding_service` → per-instance EmbeddingService (or shared with namespace)
- `_rate_limit_redis` → per-instance RateLimiter (or shared with namespace)
- `GUILD_ID` → config-driven
- `GUINEVERE_CHAT_CHANNEL_ID` → config-driven
- `app.state.hermes_brain` → `app.state.hermes_brains: dict[str, HermesBrain]`

---

## 5. P27 Architecture Summary

### 5.1 What P27 Defines (Definitional — No Implementation)

1. **Hermes Society Ontology** — what constitutes a Hermes instance, peer, society
2. **Peer Communication Protocol (HPP)** — message envelope, intent taxonomy, visibility levels
3. **3-Scope Memory Architecture** — private/shared/relationship_private + intimacy bridge
4. **7-Rail Life-Loop** — macro-state scheduler over P20 heartbeat
5. **4-Domain Safety Architecture** — Thought/Speech/PeerDialogue/Action privacy split
6. **Dual Discord Architecture** — 2 bot processes, own tokens, conversation rhythm
7. **Instance Isolation Contract** — config-driven multi-instance, per-instance resources
8. **HARD STOP Cascade** — both agents halt, sealed snapshots, audit flush
9. **Anti-Sycophancy Mechanisms** — persona anchoring, disagreement protocols, identity persistence
10. **P28-P36 Roadmap** — 9-phase forward roadmap

### 5.2 What P28 Implements (Minimum Target)

1. Two Hermes instances online (Guinevere + Pharsa)
2. Each with own config, own brain, own memory namespace, own Discord bot
3. Peer communication via HPP over Redis Streams
4. Visible conversation in `guinevere-chat` Discord channel
5. Autonomous conversation without Faiz trigger
6. Separate private memory + shared world model
7. Own autonomy loop (7-rail life-loop)
8. Runtime evidence they're alive (dashboard, audit, metrics)

### 5.3 What P29+ Implements (Future)

1. P23 action executors (email, deploy, finance)
2. P24 owned fork (preferred optimization)
3. Additional Society members (beyond Guinevere + Pharsa)
4. Cross-VPS deployment
5. Voice (P21 was SKIP — voice may return as future phase)
6. Advanced intimacy bridge (gradual trust-based sharing)
7. Formal verification (ATL, λ_A-calculus lint)
8. GAAT governance telemetry

---

## 6. Research Quality Assessment

### 6.1 Strong Areas

- **Runtime inventory** (File 4): Extremely detailed. Identified exact seams (HermesBrainConfig, agent_factory, single-instance anchors). High confidence.
- **Memory research** (File 8): Comprehensive. 12 GitHub repos, 8 PostgreSQL RLS sources, ADR-050 cross-linked. 3-scope model is well-grounded.
- **Safety/audit** (File 10): 20 labeled sources. 4-domain privacy split is production-ready. KILLSWITCH ladder is comprehensive.
- **Discord research** (File 7): Technically precise. Canonical pattern identified (Rapptz Issue #516). Rate limits well-documented.

### 6.2 Adequate Areas

- **Multi-agent society** (File 5): Good survey but no direct implementation precedent. P27 is genuinely novel.
- **Communication protocol** (File 6): Good FIPA/A2A/MCP coverage. Envelope design is sound but needs P28 implementation to validate.
- **Life-loop** (File 9): Extensive paper survey (48+ papers) but high theoretical density. P28 implementation will need to simplify.
- **Dependency maps** (Files 2, 3): Accurate status snapshots. Some files may have changed since research was conducted.

### 6.3 Areas Needing Further Research

- **Performance characteristics**: No research on resource requirements for 2+ concurrent Hermes instances on single VPS.
- **LLM cost projection**: No research on cost of running 2 autonomous agents with 7-rail life-loops.
- **Pharsa persona specifics**: No research on dark aristocratic winged mommy persona implementation patterns.
- **Discord UI/UX for dual bots**: No research on how users perceive two bots conversing in a channel.

---

## 7. Synthesis Verdict

The research is sufficient to proceed to the planner gate (Phase 3). Key findings:

1. **P27 is buildable**: No hard blockers. P19+P20+P22 provide the foundation. P24 fork is preferred but not blocking. P23 executors are not needed for P28 minimum target.

2. **P27 is novel**: True equal peer protocol, relationship-scoped memory, and 7-rail life-loop are not found in any existing framework. P27 makes a research contribution.

3. **P27 is safe**: 4-domain privacy split, HARD STOP cascade, KILLSWITCH ladder, and sycophancy detection provide production-ready safety architecture.

4. **P27 is well-scoped**: Definitional (P27) vs implementational (P28) split is clear. ~70% of P27 is definitional. P28 minimum target is well-defined.

5. **P27 is forward-looking**: P28-P36 roadmap can be defined from this research foundation.

**Recommendation**: Proceed to Phase 3 (planner gate). Write the full P27 enterprise plan with 25 sections, including per-step verification scaffold, collision scan, auditor matrix, and rollback plan.

---

## 8. Research File Index

| # | File | Path |
|---|---|---|
| 1 | Ground truth repo state | `docs/setup-evidence/P27/research/p27-ground-truth-repo-state.md` |
| 2 | P24 fork dependency map | `docs/setup-evidence/P27/research/p27-p24-fork-dependency-map.md` |
| 3 | P19/P20/P22/P23 dependency map | `docs/setup-evidence/P27/research/p27-p19-p20-p22-p23-dependency-map.md` |
| 4 | Hermes native runtime inventory | `docs/setup-evidence/P27/research/p27-hermes-native-runtime-inventory.md` |
| 5 | Multi-agent society research | `docs/setup-evidence/P27/research/p27-multi-agent-society-research.md` |
| 6 | Agent communication protocol research | `docs/setup-evidence/P27/research/p27-agent-communication-protocol-research.md` |
| 7 | Discord dual bot research | `docs/setup-evidence/P27/research/p27-discord-dual-bot-research.md` |
| 8 | Private shared memory research | `docs/setup-evidence/P27/research/p27-private-shared-memory-research.md` |
| 9 | Life loop beyond heartbeat research | `docs/setup-evidence/P27/research/p27-life-loop-beyond-heartbeat-research.md` |
| 10 | Autonomy safety audit research | `docs/setup-evidence/P27/research/p27-autonomy-safety-audit-research.md` |

---

> **Synthesis complete.** Proceeding to Phase 3: planner gate.
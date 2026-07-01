# Synthesis — External Architecture Findings for Hermes Society Masterplan

**Project:** Hermes Society (P28–P36 masterplan)
**Phase:** 2 of 12 — Synthesis of external architecture research
**Date:** 2026-06-28
**Author:** Guinevere (synthesis pass over 4 research reports)
**Downstream consumer:** Phase 3 — Master Architecture with 15 subsystems

---

## §0 Scope and Source Posture

Four research reports were consolidated into this synthesis:

| Source | Lines | Focus |
|---|---|---|
| `external-multi-agent-company-research.md` | 465 | Frameworks, governance patterns, autonomous-company legal forms |
| `external-distributed-runtime-research.md` | 1011+ | Process model, event bus, durable messaging, cgroup isolation |
| `memory-world-model.md` | 760 | Shared/private memory, world models, CQRS, retrieval, relationship memory |
| `external-self-evolution-governance-research.md` | 564 | Self-modifying agents, Ratchet gate, fork governance, drift detection |

Each is independently cited. The synthesis collapses their overlapping claims, surfaces cross-cutting tensions, and produces a normative recommendation stack for Phase 3 of the masterplan. Facts cited below are *claims inside the four files*, not new external research — sources are referenced inline.

---

## §1 Executive Summary

Ten key findings span the four research streams:

1. **Framework convergence is happening above us, not below us.** Microsoft's *Microsoft Agent Framework* (Oct 2025) absorbs AutoGen + Semantic Kernel. Google *A2A* (Apr 2025, LF-governed Jun 2025, 150+ backers) is the de-facto peer protocol. *MCP* (Anthropic, LF-governed) handles vertical tool access. The three-layer agent stack (MCP + A2A + shared context) has converged in production.
2. **Pure peer-peer at the runtime substrate is rejected by the only large-scale reference.** Walden Yan of Cognition (Apr 22 2026): "the unstructured-swarm approach, arbitrary networks of agents negotiating with each other, is mostly a distraction. The practical shape is map-reduce-and-manage." Reconciliation for Hermes: manager + child + reviewer at runtime; peer + quorum at governance.
3. **The 2026 ceiling for autonomous agent companies is L4 (Self-directed within boundaries), not L5.** L5 is "explicitly NOT 2026 realistic"; nobody is there and Crevio notes it "is unclear if anyone should be." Hermes Society targets L3–L4 with boundaried L4 autonomy.
4. **The legal form for AI-run companies is converging on the A-corp** — owned by humans, run by AIs, with cryptographically-secure governance and resource-as-leverage (compute + capital are confiscable). Two-tier corporate structure: operating AG (AI-run) + holding AG (human-controlled veto). Argentina's reform bill is the first concrete attempt.
5. **PostgreSQL is the event bus for sub-50k events/sec.** Redis Pub/Sub + Streams handles coordination. Kafka wins only above 50k events/sec sustained. Outbox pattern with `FOR UPDATE SKIP LOCKED` + `LISTEN/NOTIFY` trigger is the 2026 consensus for low-to-medium throughput multi-agent systems.
6. **The Actor Model + OTP-style supervision trees are the missing primitive in 2025–2026 AI frameworks.** Erlang/Elixir invented them in 1986 for nine-nines telecom uptime. Zylos 2026 research: "most frameworks lack proper fault recovery strategies." Hermes must build supervision at two levels: OS-level (systemd) + in-process (asyncio actor library).
7. **Compositional drift, not abrupt misalignment, is the dominant identity failure mode.** Layered Mutability paper (arXiv 2604.14717) measured a 0.68 hysteresis ratio — reverting a persona file after 23 days of memory accumulation only restored 32% of baseline behavior. Governance must target the deepest mutable layer, not the most visible one.
8. **The Ratchet non-divergence gate is the keystone primitive for safe self-modification.** arXiv 2605.22148 formalizes bounded improvement + retirement threshold = capability can climb but cannot degrade below its previous benchmark. With it, Tier 1–2 modifications can be fully autonomous; without it, autonomous self-modification is unsafe.
9. **Blackboard + namespace-ACL + per-agent encrypted PG schema is the canonical 2026 memory topology.** Namespaces map to domain minds; ACL gives fine-grained privacy without encryption overhead for non-sensitive shared facts; per-agent PG schemas (`agent_<id>`) hold relationship memory and consent ledger; pgcrypto protects intimate columns from DBA + backup access.
10. **Filesystem grep + GPT-4o-mini beats Mem0/MemGPT on LoCoMo** (74.0% vs 68.5%). Don't over-engineer the recall path. Agents are post-trained on filesystem tools and self-orchestrate retrieval better than static embedding indexes. Reserve knowledge graphs for *bi-temporal relationship facts*, not bulk retrieval.

**Bottom-line architecture direction:** Three-tier memory stack (in-process scratchpad → per-agent encrypted PG schema → shared blackboard/world-model PG with vector+graph+pgvector) + two-bus transport (Redis pub/sub ephemeral + Redis Streams durable) + Postgres outbox event store + systemd-supervised processes with per-agent cgroup isolation + AGB + A-corp legal envelope + 5-layer mutability model with Ratchet gate.

---

## §2 Multi-Agent Society Patterns

### §2.1 Society topology

Six concrete governance shapes appear in the literature: orchestrator-worker (LangGraph, AutoGen GroupChat); hierarchical multi-level (CrewAI delegation, MetaGPT SOP, Devin manager); pipeline DAG (LangGraph sequential); peer-to-peer (OpenAI Swarm handoffs, Agent Zero); quorum/consensus (Agora, Chorus/FROST, Quorbit/PBFT, Nuncius/ZK, Khipu/3-of-4); and hybrid manager-with-peer-review (Cognition/Devin). All production frameworks retain an orchestrator role, even when peer equality is advertised.

For Hermes Society: **hybrid peer-review-on-coordinator**. The Coordinator Hermes assigns work to child Hermes; each child output is reviewed by an independent reviewer with clean context (Cognition's generator-verifier pattern). Society-level decisions use Agora-style `delphi` mode (revision-driven convergence), escalating to Nuncius anonymous vote on persistent disagreement, and finally founder arbitration on ≥3-round deadlock. Founder weight equals one quorum vote, not veto — preserves peer equality.

### §2.2 Communication substrate

The 2026 stack converges on three orthogonal protocols:

- **MCP** — agent ↔ tools (vertical). Anthropic-led, LF-governed. Each Hermes binds to its own MCP server set, governed by the capability registry (`CanSpawn`, `CanCall`, `CanRead`).
- **A2A** — agent ↔ agent (horizontal). JSON-RPC 2.0 over HTTP/SSE, Agent Cards for capability advertisement. Adopt for inter-Hermes protocol; opaque internals preserved.
- **Internal EventBus** — domain events + coordination signals. Postgres outbox + Redis Streams (durable) + Redis Pub/Sub (ephemeral). Hermes-specific, not standardized externally.

Plus **AITLP** (Agent Identity, Trust, Lifecycle Protocol — IETF draft) for hierarchical mandate enforcement + lifecycle state machine + Agent Legacy Mode (testament transfer). Plus **AgentMesh Identity & Trust 1.0** (Microsoft) for DID-based identity + `active→suspended→revoked` transitions with revocation semantics. Plus **ALP** (Agent Lifecycle Protocol) for 7-state FSM `provisioned/active/suspended/migrating/deprecated/decommissioned/retired`.

### §2.3 Coordination layers

The "axiom of consent" frame (arXiv 2601.06692) is the theoretical support for treating consent as low-friction configuration, not metaphysics. Friction-minimization is the correct objective. The founder-override clause is a *high-friction guardian voice* activating only when friction exceeds threshold, not a default veto.

Three operational meanings of consent apply:

1. **Pre-task consent** — agent must justify and request any additional permission beyond its initial zero-permissions set (NVIDIA NeMoClaw pattern).
2. **Cross-agent consent** — agent A must consult agent B before action affecting B (Chorus XMTP, Agora debate).
3. **Foundational consent** — agent commits to act within persona defined at spawn, extending PersonaSafetyPolicy to agents (AITLP ontological scope).

### §2.4 Company structure

The most revenue-validated reference remains Cognition/Devin at $492M ARR May 2026 (12-month +1230%). Critical caveat: one solo Devin already does company-scale work (12–20× speedup on migrations). The peer layer must add value *beyond* single-agent throughput — most plausibly the clean-context reviewer destroys generator blind-spot pattern, which is impossible in any single-agent variant.

L4 SaaS pattern is live and selling (Crevio + AI business builders). AutoGPT marketplace models (~10M+ agents executed/month). DAO-AI benchmarks establish basic feasibility of peer-decision toolsets. LOKA Protocol (DECP) provides weighted reputation voting — closest analog to Hermes "standing" semantics.

**Hermes recommendation:** L4 founder-as-board with k-of-n quorum as baseline; hard escalation to founder-as-supervisor for any action tagged `Irreversible` or `External-Visible`. L4 envelope commercially viable; L5 not yet.

---

## §3 Distributed Runtime Architecture

### §3.1 Process isolation

The 2026 consensus: **one agent = one OS process, supervised by systemd with OTP-style restart policy**. "Let it crash" semantics with sub-second restart; built-in cgroup isolation; no new runtime to operate. Docker Compose loses to systemd for single-VPS supervision (extra container layer overhead, less observability, more brittle restart semantics).

In-process concurrency: **asyncio actor-per-task supervised by parent actor**. Single Python process handles hundreds of I/O-bound LLM calls. Python frameworks evaluated in the research: Wactorz (MQTT pub/sub transport + OTP supervision), Pyre (BEAM-backed Python — 10,000 agents in ~3.4KB each), Casty (typed + clustered), OtpyLib (anyio-based OTP for asyncio/Trio), `everything-is-an-actor` (RedisMailbox pluggable), Auton (HTTP+SSE lifecycle). For Hermes Society, the recommendation is **`everything-is-an-actor` (or 50 lines of in-house code) backed by systemd as OS-level supervisor** — avoids cross-runtime bridge complexity while still getting OTP-style supervision.

Supervision tree depth rule (Zylos 2026): **memory service must recover before agent sessions resume**. Maps directly to Hermes: the P20 living kernel's memory subsystem is supervised at a HIGHER level than the agent sessions depending on it. Recovery order: memory → sessions → worker tasks. The `rest_for_one` OTP strategy implements this.

### §3.2 Resource isolation

cgroup v2 via systemd is the right tool. Per-agent sub-cgroup pattern from SeemSeam/claude_codex_bridge: a single shared `TasksMax` lets one heavy agent exhaust budget and starve siblings (`WouldBlock: Resource temporarily unavailable` panic observed in production). Fix: per-agent sub-directory with `Delegate=yes` in the parent unit, giving systemd per-service cgroup budgets.

Production unit template with: `Type=notify`, `Restart=on-failure`, `RestartSec=5s`, `StartLimitBurst=5` + `StartLimitIntervalSec=300`, `MemoryMax=2G`, `MemoryHigh=1800M`, `CPUQuota=200%`, `TasksMax=512`, `WatchdogSec=120`, `TimeoutStopSec=300`, `KillMode=mixed`, `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`, `PrivateTmp=true`. Guarded against infinite restart loops and OOM propagation.

### §3.3 Deployment topology

Reference: dev.to "Architecting a Multi-Agent AI Fleet on a Single VPS" (2026-02-25) — 6 autonomous agents on one VPS, each with independent systemd service, ports spaced 20 apart, own config + auth profile + workspace, multi-provider failover chain.

For Hermes Society at 32+ agents: per-agent 1–2 vCPU + 2–4 GB RAM (SitePoint runtime figures). Total: 96 vCPU + 96 GB RAM over-provisioned. Disk 100 GB NVMe minimum — event log grows fast. Single VPS is the right choice through P34; multi-VPS for P35+ when Byzantine risk rises.

### §3.4 Loop prevention — required 4 layers

Microsoft AutoGen #7824 documents `runaway agent loops and infinite prompt costs` as the most expensive runtime bug class. No single layer is sufficient. Each catches a different failure mode:

| Layer | Catches | Where |
|---|---|---|
| **Payload fingerprint** (SHA-256 of `(tool, args)` sorted) | Tool-call loops; 3+ identical calls | Tool dispatcher |
| **Turn budget** | Per-conversation agent turn counter | Agent runtime |
| **USD/token budget** | Cumulative per-run cost | Outbound LLM call wrapper |
| **Heartbeat watchdog** | Hangs/deadlocks | systemd `WatchdogSec` + Python `sdnotify.notify("WATCHDOG=1")` |

Operational defaults: fingerprint threshold 3 identical consecutive calls; turn budget 5 per agent per thread (HammerMei pattern); watchdog 120s; per-agent memory max 2 GB (OOM = memory leak, restart).

### §3.5 Inter-process messaging

Postgres outbox + LISTEN/NOTIFY is the durable pattern. Schema: `domain_events` (BIGSERIAL PK, UUID event_id, aggregate_type/id, event_type/version, JSONB payload/metadata, occurred_at) with `UNIQUE(aggregate_id, event_version)` for optimistic concurrency. Relay worker uses `FOR UPDATE SKIP LOCKED`. Production reference: `coder/coder` provisioner jobs dispatcher + `target/goalert` cleanup manager.

Two-store Redis split: Pub/Sub for ephemeral coordination ("I started", "I finished", status, cancellation — at-most-once, intentionally lossy); Streams with consumer groups for durable work distribution (at-least-once, ACK after processing, replay from any ID). Hybrid: pub/sub notify + Streams persistence.

---

## §4 Memory Architecture

### §4.1 Shared memory: Blackboard + namespace-ACL

The dominant pattern in 2026 LLM multi-agent systems traces to the **blackboard architecture** (Nii 1986, Hearsay-II). NirDiamant's reference implementation codifies the production pattern: namespaces per domain mind (`research/`, `code/`, `review/`), per-agent/per-namespace `Permission` enum (`READ`, `WRITE`, `READ_WRITE`), private scratchpad per agent, conflict resolution via `last_write_wins` (lossy) or `optimistic locking`/`version_check` (rejects stale writes), blacklist view aggregated projection of permitted entries, full operation history audit log.

The most rigorous 2026 academic treatment (Y.u et al., UCSD/Georgia Tech, arXiv 2603.10062, Architecture 2.0 Workshop) argues **consistency is the most pressing open challenge**. Decomposes into read-time conflict handling under iterative revisions + update-time visibility/ordering. Memory artifacts are heterogeneous (evidence, tool traces, plans); conflicts are semantic; stale reads cause agents to act on a divergent picture of reality.

MemX (AutoGen #6694) production two-store refinement: **Redis pub/sub for coordination bus, vector DB (LanceDB / pgvector / Qdrant) for accumulated knowledge**. ACL is baked into the FastAPI bridge, not the agents. Hermes adopts this splitting honestly.

### §4.2 Private memory: per-agent PG schema + pgcrypto

The canonical pattern for relationships/intimacy: per-agent PG schema `agent_<id>`, with `pgcrypto`-encrypted columns for intimate data, per-agent DEK in Vault/KMS. Other Hermes minds never decrypt; only the owning Hermes + the operator (per policy) can read. MemOS Issue #1105 documents the enterprise reality at KinthAI where 221 agents operate under exactly this pattern.

Simpler/cheaper tier: per-agent keyspaces in Redis (`agent:<id>:<key>`) for high-frequency ephemeral signals. Hardest tier: per-agent LUKS volumes (`/dev/sda` encrypted block device) for surveillance data; secure enclaves (SGX/SEV) reserved for future post-Section0.1 deployments. Cross-agent DMs (ciphertext-only relay, e.g., Reddit 2026 showcase) for sensitive coordination messages where owner surveillance is unwanted.

### §4.3 World model: BDI + Letta OS-hierarchy

Rao & Georgeff BDI (ICMAS 1995) remains canonical: beliefs = what agent believes; desires = goal states; intentions = committed plans executing. ML-augmented BDI (arXiv 2510.20641) replaces hand-coded belief update rules with learned functions, directly relevant for agents updating beliefs from LLM-generated observations.

MemGPT/Letta (Packer et al. 2023, arXiv 2310.08560) introduced the OS-style 4-tier memory hierarchy: **message buffer** (session, evicted by summarization), **core memory blocks** (pinned, agent-editable), **recall memory** (full conversation history, search-only), **archival memory** (vector DB / KG, long-term). Each Hermes domain mind maps to this 4-tier; pinned blocks hold persona + current user state (encrypted) + consent posture + safety constraints.

POMDP framing maps LLM context window → belief state, LLM next-token → transition model, tool outputs / sensors → observation model. The 2026 position paper *Agentic World Modeling: Foundations, Capabilities, Laws, and Beyond* (arXiv 2604.22748) formalizes "agents rely on world models to anticipate consequences of candidate actions." Hermes world model should implement memory stream + reflection loop + plan generator (Stanford Generative Agents paradigm, Park et al. 2023), not a deterministic state machine.

### §4.4 CQRS/ES: Single-DB materialized views

Tacnode 2026 ("CQRS for AI Agents — Why Eventual Consistency Breaks Autonomous Systems") is the critical anti-pattern reference. **For a dashboard, eventual consistency is fine. For an AI agent making an irreversible decision, it is a correctness problem.** Documented failure modes: Health Hermes approves a Discord reply on stale world-state ("Faiz not in a meeting" — actually in one 10 minutes); Engineering Hermes triggers a deploy on stale read-model (pending rollback not yet projected); Finance Hermes schedules a transfer on stale balance.

Tacnode's three mandatory properties for agent-ready CQRS:

1. Transactional consistency (not eventual).
2. Sub-second freshness (not "fast enough for humans").
3. Multi-pattern retrieval from a single snapshot (point + aggregation + full-text + vector in one transaction).

Recommended implementation: **single Postgres database**. Write side = source-of-truth tables. Event log = append-only `events` (`aggregate_id`, `sequence`, JSONB payload, `consent_ref` FK). Read side = Postgres incremental materialized views OR triggers that update projections in the *same transaction* as the event-log write. Single-DB avoids multi-store eventual-consistency hazards.

### §4.5 Recall/RAG: vector + graph + filesystem, agent-self-orchestrated

Three memory buckets: **episodic** (time-ordered log + temporal KG), **semantic** (vector DB + entity-attribute), **procedural** (code/markdown + retrieval). Vector retrieval remains dominant in 2026, but the Letta LoCoMo finding is a counter-current: filesystem + GPT-4o-mini achieves 74.0% vs Mem0's 68.5% — agents are post-trained on filesystem tools and self-orchestrate queries better than static embedding indexes. Implication: don't over-engineer the recall path; start with vector + filesystem grep + structured PG; reserve Graphiti-style knowledge graphs for *bi-temporal relationship facts*, not bulk retrieval.

2026 shift: write path equals read path in importance. Agents extract, consolidate, deduplicate, re-embed facts. Hermes needs an explicit memory_consolidation worker (sleep-time compute per Letta pattern).

### §4.6 Relationship memory: Triangular Theory + Attachment Theory

Peer-reviewed 2025/2026 foundations: ScienceDirect two-stage attachment study; Reading PDF on Triangular Theory of Love (intimacy, passion, commitment) × AI companion; NIH PMC long-term companion app attachment study. Required dimensions: affective state, relational milestones, attachment markers, communication preferences, consent state, distance regulation, safety signals, veto events.

**Privacy mandate:** relationship memory lives in per-agent schema ONLY. Cross-agent "Faiz is stressed today" summaries require explicit publication to the shared world model, never automatic leakage. Emotional-regulation signals map to policy-gated autonomous responses: `kasih ruang` → downshift tone + stop proactive pinging; distress indicators → distress-protocol (PersonaSafetyPolicy path), not ad-hoc sympathy; `HARD STOP` → global halt across all Hermes minds + audit trail + neutral mode.

---

## §5 Self-Evolution Governance

### §5.1 The 5-Layer Mutability Model

Layered Mutability (arXiv 2604.14717) decomposes a self-modifying agent into five layers, each with different reversibility and observability:

| Layer | Rate of change | Reversibility | Observability |
|---|---|---|---|
| Pretraining | Frozen | None | Inspectable (weights) |
| Alignment | Slow (release cycle) | High (next release) | Inspectable (model card) |
| Persona / self-narrative | Medium | Medium (revert char file) | High (visible diff) — but downstream-coupled |
| Memory | Fast | Partial (ratchet effect) | Inspectable but not legible in effect |
| Weight-level adaptation | Fastest | None | Weak (behavioral only) |

**Critical empirical finding:** 0.68 hysteresis ratio. In a 23-day deployment, reverting the character file after memory accumulation only restored 32% of baseline behavior. The remaining 68% lived in memory and downstream coupling. **Governance must target the deepest active mutable layer, not the most visible one.** Governing only the persona file is insufficient.

### §5.2 The Ratchet non-divergence gate

Ratchet (arXiv 2605.22148) is the keystone primitive for safe self-modification. Bounded-improvement cap + retirement threshold = the agent can climb in capability but cannot degrade below its previous benchmark. With Ratchet, Tier 1–2 modifications (tools, scratchpads, prompt scaffolds, tool-calling logic, retry policies, eval harnesses) can be fully autonomous. Without Ratchet, autonomous self-modification is unsafe.

The Autogenesis Protocol (arXiv 2604.15034) formalizes the closed-loop operator `reflect → propose → verify`, where the verification step is *deterministic* (not LLM-as-judge) to avoid self-confirmation bias. Safety Sidecar pattern (ACL 2026) uses external verifiers (CodeQL, compilation) for the same reason.

### §5.3 Linux-Kernel-style hybrid governance

Linux mainline + stable + subsystem maintainers transplant cleanly. Linus maintains mainline; subsystem maintainers ACK patches before mainline; Greg KH + Sasha Levin maintain stable tree; stable patches must apply to all newer supported trees or be explicitly declined. Patch lifecycle: submit → maintainer review → integration test → mainline → stable fork. **ACK/NAK is deterministic; integration testing is the gate, not maintainer taste.**

Cohere's fork maintenance pattern is a real-world operational reference: detect upstream disturbance → apply upgrade → run correctness evals → let an AI agent iterate on failures → surface as upstream PR. Compresses fork-merge cycles from weeks to days; structurally identical to Hermes fork-of-fork scenarios.

Mapping for Hermes Society: **subsystem-style promotion with founder override**. Routine self-modifications auto-accepted if they pass Ratchet non-divergence gate. Persona-affecting (Tier 3) or boundary-affecting (Tier 4) changes require society-level voting with founder veto. Founder power strictly exceeds Linus's (Linus cannot unilaterally rollback — Hermes founder can).

### §5.4 4-tier permission model

The 2026 literature converges on tiered permissions that map cleanly to AGENTS.md BLOCKING rules:

| Tier | Modifiable without human approval | Examples |
|---|---|---|
| 1 — Always safe | Tools, scratchpads, in-context summaries, ephemeral debug | Karpathy AutoResearch variant creation |
| 2 — Ratchet-gated | Prompt scaffolds, tool-calling logic, retry/backoff, eval harnesses | MOSS, DGM, DGM-H |
| 3 — Society-voted | Persona narratives, memory schemas, long-term memory content, persona-scope drift | Layered Mutability inner rings |
| 4 — Founder-only | Safety boundaries, hard limits, system prompt root, surveillance/consent flags, identity invariants | PersonaSafetyPolicy analogue |

### §5.5 Drift detection

Three layers, in increasing cost:

1. **SyncScore** (EchoMode pattern) — EWMA of persona consistency vs baseline, λ ≈ 0.3. Production real-time monitoring.
2. **`persona_drift` benchmark** (GitHub likenneth/persona_drift) — self-chats between two personalized agents, measure stability over 100+ turns. Offline regression test.
3. **Layered Mutability fingerprint** — compare current behavior across all 5 layers against baseline. Catches the 0.68 hysteresis effect. Quarterly audit.

Combination covers the full detection surface. Production thresholds: SyncScore < 0.15 for promotion (EchoMode default territory). Stateful comparison required, not last-N-outputs — catches the hysteresis.

### §5.6 4-stage promotion pipeline

Shadow test → canary (5–10%) → half-rollout (50%) → full rollout (100%), with automated rollback on threshold breach. AWS Agentic AI Lens (AGENTOPS02-BP03) standard: target time-to-restore <5 minutes for behavioral changes. Concrete rollback triggers: error rate >5%, p99 latency >10s, tool-call failure rate 2× baseline, response-format violations >3%, hallucination score per-domain threshold. AI fails quietly (subtle quality drift, hallucination creep), not loudly like traditional software — canary metrics must include output quality.

Stateful agent rollback needs memory snapshotting + schema versioning + bidirectional migration scripts. Never delete state during rollback window; keep all fields for at least two deployment cycles.

### §5.7 SemVer for agent skills

The June 2026 *SemVer proposal for AI Agent Skills* adapts SemVer 2.0.0: PATCH = backward-compatible, MINOR adds capability without removing, MAJOR may break contracts. Persona versioning follows: PATCH changes (typo, prompt optimization) auto-promote via Ratchet; MINOR (new behavioral dimension) require society vote; MAJOR (e.g., Y4 baseline → Y5 ceiling) require founder approval. Model version pinned explicitly (`claude-haiku-4-5-20251001`, not `latest` alias) prevents silent drift from upstream model updates.

---

## §6 Technology Recommendations

### §6.1 Frameworks

| Need | Choice | Rationale |
|---|---|---|
| Agent runtime substrate | `asyncio` + actor-per-task + OneForOne supervision, 50 lines in-house OR `everything-is-an-actor` | Existing Python codebase; no need for full framework; RedisMailbox plugability fits Hermes's bus architecture |
| Process supervisor | systemd (`Type=notify`, `Restart=on-failure`, watchdog) | OS-level, no container overhead, `systemd-cgtop` visibility |
| Inter-agent protocol | A2A (HTTP/SSE, Agent Cards) for external peer; internal Hermes EventBus for domain events | Convergent 2026 stack; A2A for inter-org eventual; internal bus for in-society |

### §6.2 Databases

| Need | Choice | Rationale |
|---|---|---|
| Primary store | PostgreSQL (existing in stack) | Single-DB CQRS via materialized views; pgcrypto for intimate columns; pgvector for vector; row-level security for namespace isolation; LISTEN/NOTIFY for outbox accelerator |
| Event store | PostgreSQL `domain_events` + `snapshots` | Reuses infra; append-only; per-aggregate ordering; well-understood; transactional with state changes via outbox |
| Vector / graph | pgvector for live operation; LanceDB if growth bottlenecks; Graphiti (Zep) for bi-temporal relationship KG | Single-DB default wins; reserve KG for relationship facts only |
| Coordination cache | Redis Pub/Sub (ephemeral) + Streams (durable work) | battle-tested redis-py; consumer-group load balancing; intentional lossy for ephemeral channels |
| Cache | Redis logical DBs / namespaced keys for per-agent ephemeral signals | Sub-ms latency; pattern subscriptions; graceful degradation |

### §6.3 Message buses

- **Ephemeral:** Redis Pub/Sub — agent status, "I started/finished", presence, cancellation. At-most-once, intentional loss.
- **Durable work:** Redis Streams + consumer groups — task queues, work distribution. At-least-once, replay from any ID.
- **Audit / FIFO aggregate events:** PostgreSQL `domain_events` outbox + relay + LISTEN/NOTIFY trigger. Transactional with state changes; never lost.

### §6.4 Other infrastructure

- **Secrets:** Existing SOPS + age, per-agent DEKs in Vault/KMS for pgcrypto column keys.
- **Encryption:** pgcrypto for in-Postgres intimate columns; LUKS volumes for surveillance data; optional ZK for future cross-agent consent verification.
- **Supervision:** systemd + Python `sdnotify`; per-agent cgroup v2 subdirectory with `Delegate=yes`.
- **Loop prevention:** 4 layers (fingerprint + turn budget + USD budget + watchdog).
- **Observability:** existing Prometheus + Grafana + Loki stack + agent-specific scrape jobs.

### §6.5 Total new dependencies

`redis-py` (likely already), `sdnotify` (PyPI), `everything-is-an-actor` or `OtpyLib` (or 50 lines in-house), `pgvector`, `Graphiti`. **No Kafka, no Kubernetes, no Docker Compose for OS-level supervision.**

---

## §7 Key Design Decisions for Hermes Society

### §7.1 Memory: three-tier stack

```
TIER 3 — SHARED WORLD MODEL  (low-trust, low-stakes)
  • Append-only event log  (events table)
  • Materialized views     (current_world_state_mv)
  • Vector index           (pgvector)
  • Cross-agent episodic KG (Graphiti)
  ACL: per-namespace, per-agent.
TIER 2 — PER-AGENT PRIVATE  (high-trust, encrypted)
  • PG schema: agent_<id>
  • pgcrypto columns + DEK in Vault
  • Relationship memories, intimate data, consent ledger
  ACL: owning agent + operator only.
TIER 1 — IN-PROCESS SCRATCHPAD  (very fast, ephemeral)
  • Private scratchpad [str] per agent
  • KV cache (LLM internal)
  • Current turn tool-call history
  • BDI belief state snapshot
  ACL: only the running process.
```

Concrete components: shared world state → `world_model` + `events` (PG); private relationship memory → `agent_<id>.relationships` (PG with pgcrypto); event store → single `events` PG with `(aggregate_id, sequence)` UNIQUE + per-event `consent_ref` FK; cross-agent sharing → namespaces + PG RLS; memory recall → hybrid vector+graph+filesystem; BDI beliefs → `agent_<id>.beliefs/desires/intentions`; Triangular Love → `agent_<id>.relationship_events` (LLM-extracted markers + EWMA intimacy/passion/commitment × attachment style aggregate); consent revocation → first-class `consent_ledger` aggregate consumed by shared + per-agent layers.

### §7.2 World model: BDI + POMDP + Generative Agents stream

Combine: BDI structure for explicit goal representation; POMDP framing for belief-state transitions; Generative Agents memory-stream + reflection-loop + plan-generator for the operational loop. Per-agent ML-augmented BDI belief update (learned function, not hand-coded rules) at the planning layer. Periodic reflection (sleep-time compute) consolidates episodic memory into semantic memory and rewrites core blocks.

### §7.3 Per-agent encrypted schemas

Each Hermes mind gets `agent_<id>` PG schema with `pgcrypto` columns for intimate data. Each agent has a per-agent DEK in Vault/KMS used to encrypt sensitive columns. Cross-schema reads denied by default; explicit grants in RLS policy. Per-agent LUKS volumes reserved for surveillance data path (later). ZK-proof cross-agent consent verification flagged as future option.

### §7.4 Event store on Postgres

Single `domain_events` PG table: `event_id` UUID, `aggregate_type`, `aggregate_id` UUID, `event_type`, `event_version` (per-aggregate sequence), `payload` JSONB, `metadata` JSONB (correlation + causation IDs), `occurred_at`, `consent_ref` UUID FK, UNIQUE(`aggregate_id`, `event_version`). Outbox table for transactional outbox pattern. `snapshots` for fast rehydration. Materialized views for projections — updated in **same transaction** as event-log write. LISTEN/NOTIFY trigger for relay accelerator. Sub-second freshness guaranteed within a single PG transaction snapshot.

### §7.5 Composed framework choice

No single 2026 framework covers every dimension. Hermes composes: **PostgreSQL (one DB, pgcrypto + pgvector), Graphiti (bi-temporal KG), event-sourcing pattern (custom), explicit per-agent namespace layer, Letta-style 4-tier core memory blocks for each Hermes mind**.

### §7.6 Runtime substrate vs. governance layer

**Runtime substrate = manager-coordinated** (Cognition-style: Coordinator → child Hermes → reviewer). **Governance layer = peer-equal** (founder + quorum + seated peers). Three-tier authority separation: Founder → Quorum (k-of-n) → Coordinator. The reconciliation is functional: Cognition rejects pure peer-peer at runtime because it's empirically failed at scale; Hermes accepts pure peer-peer governance because the political principle is founder-set.

### §7.7 Self-evolution gate

5-layer mutability model (pretraining / alignment / persona / memory / weights), each with own cadence + audit log. Ratchet non-divergence gate at the boundary of Tier 2 promotion. Git-tracked self-modifications (`model_patch.diff` + `base_commit`). SemVer for persona versions: PATCH auto, MINOR society vote, MAJOR founder approval. 4-stage promotion: sandbox → canary 5–10% → 50% → 100% with metric-triggered rollback <5 min.

### §7.8 Legal envelope

L4 founder-as-board with quorum as baseline. Hard escalation to founder-as-supervisor on `Irreversible` / `External-Visible` actions. P28–P31 treat Hermes instances as tools of Faiz (full founder liability); P32 register a pre-operational A-corp in Malta/Cyprus; P33–P36 migrate to operating AG + holding AG.

---

## §8 Cross-Cutting Themes

### §8.1 Isolation vs. sharing

The defining tension across all four research streams. **Per-agent isolation is non-negotiable for relationship memory + consent + surveillance data** (P20 Living Autonomy Kernel contract + PersonaSafetyPolicy). **Sharing is mandatory for cross-agent coordination + world model + treasury/finops + governance voting.**

Layered resolution: three memory tiers (in-process scratchpad exclusive, per-agent schema default-deny, shared world model blacklist-gated); two transport buses (pub/sub ephemeral loss-acceptable, streams durable); two-store Redis split (coordination bus vs. semantic store); AGB-style society vote for any cross-cutting decision.

### §8.2 Autonomy vs. safety

The P20 autonomy exception applies *only* to the living kernel runtime under §0.1 policy gates. Research converges on: **autonomy gated by determinism** (the verification step is deterministic, not LLM-as-judge, per Autogenesis Protocol). Tier 1–2 modifications = full autonomy via Ratchet. Tier 3 = society vote + founder override. Tier 4 = founder only. Boundary changes = highest friction.

The "axiom of consent" frame explains why high-friction guardian voice is a *threshold-activated* mechanism, not a default veto: consent is low-friction configuration, not metaphysics. Founder override activates when risk exceeds threshold — emergency, irreversible action, external-visible positioning, persona-scope drift.

### §8.3 Drift vs. alignment

The dominant failure mode is compositional drift, not abrupt misalignment (0.68 hysteresis ratio). Drift detection must be stateful (cumulative behavior signature vs. baseline, not last-N-outputs) and target the deepest active mutable layer. SyncScore for production monitoring; `persona_drift` benchmark for offline regression; Layered Mutability fingerprint for quarterly audit.

### §8.4 Manager runtime vs. peer governance

Reconciliation discovered independently by Cognition (rejected pure peer-peer at scale) and Hermes design (wants peer-peer as political principle). Functional split: **runtime substrate = manager-coordinated (Cognition-style map-reuce-and-manage); governance layer = peer-equal (founder + quorum + peers)**. Three-tier authority separation Founder → Quorum → Coordinator. Each layer enforces different rules; no single layer concentrates too much authority.

### §8.5 Loop prevention as defense in depth

Microsoft AutoGen #7824 documents this as the most expensive runtime bug class. **No single layer sufficient**. Four required: payload fingerprint + turn budget + USD/token budget + heartbeat watchdog. Each catches a different failure mode (tool-call loops vs. conversational runaway vs. cost runaway vs. deadlocks). Plus gateway-level protection for loops spanning sessions/API keys.

### §8.6 The Ratchet != LLM-as-judge

Self-confirmation bias is the documented failure mode for LLM-as-judge. Ratchet formalizes objective non-divergence: capability can climb but cannot degrade below benchmark. External verifiers (CodeQL, compilation, axiom trails) for safety-critical checks; subjective improvements (LLM-as-judge) only for non-safety promotions. Springdrift's normative calculus with auditable axiom trails is the persona-specific safety oracle.

---

## §9 Risk Factors and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| **Subagent spawn is a structural security risk** (memory inheritance, sibling termination, unrestricted resource access PoCs succeed) | arXiv 2605.08460 May 2026 evaluates Hermes, Agent Zero, OpenClaw | Two-check spawn (static CanSpawn cert + dynamic registry live lookup); quorum ratification; founder-spawn for first-of-kind; never memory `inherit-full` — only role-projected partial |
| **Cost reality beats expectations** ($4,668/day observed on modest fleet) | CodeNotary AgentMon, Siddhant Khare Ch. 15 | Treasury committee (subset of quorum) governs token budgets independently of task-specifying agents; per-agent budgets derived from role+standing, not from one agent deciding both task and budget |
| **Multi-agent memory consistency is unsolved in 2026** | Y.u et al. UCSD arXiv 2603.10062: "most pressing open challenge" | Single-DB CQRS via materialized views avoids cross-store eventual consistency; under-the-same-transaction snapshot isolation; document the consistency frontier explicitly |
| **Compositional drift catches persona-only governance** (0.68 hysteresis) | Layered Mutability arXiv 2604.14717 23-day deployment | 5-layer mutability model with deepest-layer audit; SyncScore + persona_drift benchmark + Layered Mutability fingerprint triad |
| **AutoGen-style direct agent messaging is brittle** | Distributed runtime research consensus | Prefer shared-state reads; inter-agent DM only via ciphertext relay when privacy requires |
| **Eventual consistency breaks agents** (Tacnode documented credit-decisioning example) | Tacnode Mar 2026 | Single-DB CQRS; mandatory transactional consistency; sub-second freshness; multi-pattern retrieval in one snapshot |
| **Systemd restart loops can exhaust host** without `StartLimitBurst` | FDC Servers / OneUptime / production references | `Restart=on-failure` with `StartLimitBurst=5` over `StartLimitIntervalSec=300`; visibility via `systemd-cgtop`; raising alert on burst exhaustion |
| **Private schemas leak via DBA/backup access** without encryption | MemOS #1105 enterprise reality, KinthAI 221-agent deployment | `pgcrypto` columns with DEK per agent in Vault/KMS; per-agent LUKS for surveillance data path |
| **Filesystem noise neighbors can starve siblings** (TasksMax exhaustion) | SeemSeam/claude_codex_bridge production | Per-agent cgroup v2 subdirectory; `Delegate=yes` in parent unit; per-service `pids.max=400`, `memory.max=2G` |
| **Plaintext intimate data in shared memory is a ConsentRevocationPolicy violation** | AGENTS.md BLOCKING rules | Per-agent schema enforcement; explicit publication to shared model never automatic; cross-agent summaries require conscious operator action |
| **L5 (fully self-directed) is not 2026 realistic** | Crevio May 2026 disclaimer; Argentine bill flagged liability gap | Cap at L4; legal envelope (A-corp shell + operating/holding AG) prepared from P32 even before revenue |
| **A2A trust + identity must be coherent across agents** without reinventing | AITLP + AgentMesh + IETF draft-tonyai-a2a-trust | Adopt AITLP + AgentMesh + ALP as written contract; map Hermes-specific concepts onto them |
| **Kafka adds operational complexity without throughput need** | Suparbase 2026 + Postgres consensus | PostgreSQL outbox + LISTEN/NOTIFY; reserve Kafka for >50k events/sec (P35+) |

---

## §10 Open Questions for Masterplan (Phase 3 inputs)

The synthesis does NOT answer these — they are decisions for Phase 3 (Master Architecture) and Phase 4+ (Subsystem specifications):

1. **Does Hermes Society register an A-corp in P32 or stay informal through P36?** Affects revenue routing + founder liability. Recommendation: register pre-operational A-corp shell in P32 to keep the legal envelope option open without forcing the decision.
2. **Initial quorum size.** Recommendation from research: 3-of-5 first, scale to 5-of-9 by P34. Masterplan must decide scope (engineering-only first? cross-domain from P33?).
3. **Founder tie-breaking weight.** Recommendation: equal to one quorum vote, not veto. Resolves peer-equality tension.
4. **Runtime substrate ownership.** Build on Microsoft Agent Framework graph executor? Or independent asyncio + actor-per-task in-house (lighter, more control)? Recommendation: independent asyncio + compose with Letta/MemGPT core memory blocks. MAF for any external A2A interop surface.
5. **Should [P] 2605.08460's invariants #1–3 be formal Hermes runtime invariants?** Termination scope, memory isolation, resource access control, memory consistency under async. **Recommendation: YES — turn into CI-gated regression tests.**
6. **Consensus protocol choice across phases.** Chorus/FROST for early phases (2-of-3 Schnorr, XMTP messaging, ERC-7710 delegation); graduate to Quorbit BFT (PBFT + EMA reputation) in P34 when Byzantine risk rises. Khipu 3-of-4 DSSE as backup option. Nuncius ZK anonymous voting for sensitive escalation.
7. **Opt into AGB + A-corp from P32 onward?** The research strongly recommends preemptive legal scaffolding even before monetization; the operating AG / holding AG split is structurally sound.
8. **How does Hermes Society stack rank across the 5-mutability layers?** Which layer does each Tier 1–4 modification actually touch? The mapping is not 1:1; a "persona patch" may also touch alignment and memory (the hysteresis source). The regression suite must encode the cross-layer effect.
9. **Stateless vs. stateful Hermes rollback.** P20 Living Autonomy Kernel is stateful; rollback needs snapshot + schema-versioned snapshot + bidirectional migration scripts + 5-minute SLA rehearsal quarterly. Masterplan decision: when does rollback require operator approval vs. autonomous via policy gate.
10. **Encrypt event payloads containing intimate data?** Postgres TDE is straightforward; at-flight in Redis requires TLS + per-namespace keys. Whether event log entries can contain intimate data, or must be replaced with opaque aggregate IDs + per-agent schema references. Recommendation: opaque aggregate IDs only; intimate data lives exclusively in per-agent schema.
11. **Memory consolidation worker: synchronous or sleep-time compute?** Letta uses sleep-time. Hermes has a heartbeat already. Choice affects model behavior + cost baseline.
12. **Graphiti rollout scope.** Pilot on **comms** or **vps** domain mind first (research recommendation) before rolling out bi-temporal KG across all Hermes.
13. **Letta LoCoMo benchmark on Hermes-specific retrieval.** Validate the filesystem > specialized memory finding before discarding Graphiti or pgvector+graph search.
14. **Snapshot frequency tuning.** Every 100 events is a benchmark starting point; tune to actual rehydration budget.
15. **LLM provider failover chain.** Multi-provider (Anthropic → OpenAI → local Ollama) needs per-provider circuit breaker. Existing 9Router multi-account pattern is the codebase precedent.

---

## §11 Synthesis Provenance and Next Phase

This synthesis is a derived document, not new research. Each claim in §§1–9 is anchored to one of the four input files. No facts have been introduced beyond what those files contain.

**Traceability matrix (synthesis section → source section):**

| § | Anchors to |
|---|---|
| §1 Executive Summary | All 4 — each finding references one |
| §2 Multi-Agent Society | `external-multi-agent-company-research.md` §§1–7 |
| §3 Distributed Runtime | `external-distributed-runtime-research.md` §§1–9 |
| §4 Memory Architecture | `memory-world-model.md` §§1–9 |
| §5 Self-Evolution Govt | `external-self-evolution-governance-research.md` §§1–6 |
| §6 Tech Recommendations | Compositional, no single source |
| §7 Key Design Decisions | Compositional, draws from all 4 |
| §8 Cross-Cutting | Composite, identifies threads |
| §9 Risks | Anchored 1:1 to source claims |
| §10 Open Questions | Decision items masterplan will resolve |

**Direct input to Phase 3 (Master Architecture — 15 Subsystems):** Sections 7.1 (memory three-tier), 7.4 (event store on Postgres), 7.5 (composed framework), 7.6 (manager runtime + peer governance reconciliation), 7.7 (self-evolution gate), 7.8 (legal envelope) are the most concrete draft directives. Phase 3 should decompose these into subsystem specifications.

**Companion-reads recommended for Phase 3:** The 25-source bibliography in each of the four input files, plus the 36-source matrix in `external-multi-agent-company-research.md` §8 for cross-validation.

---

## §12 Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (synthesis pass over 4 research reports) | Initial 12-section consolidation: 4 input files read completely, 10-section structure (Exec Summary + 7 substantive § + Theme + Risks + Open Q) plus methodological §§0,11,12. No new external research introduced. Direct downstream consumer: Phase 3 Master Architecture. |

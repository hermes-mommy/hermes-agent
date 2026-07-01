# Memory & World Model Architectures for Multi-Agent Systems — Research Findings

**Purpose.** State-of-the-art research to inform the **Hermes Society** memory subsystem in the P28–P36 masterplan: shared world state, private per-agent relationship memory (encrypted), event-sourced state of the company, memory recall, and cross-agent knowledge sharing.

**Scope.** Seven topics required by brief; covers academic foundations, 2026 production frameworks, and Hermes Society design implications.

**Compiled:** 2026-06-28. Sources current as of this date. All citations include URLs; production-grade sources are tagged with framework name, year, and anchor (section/equation) when available.

---

## TL;DR — Canonical Patterns (Decision Matrix)

| Concern | Recommended Canonical Pattern | Strongest 2026 Reference |
|---|---|---|
| Shared world state across agents | **Blackboard + namespace ACL + event-sourced log** (Redis-style tuple space + per-namespace writes + append-only log) | [NirDiamant multi-agent-shared-memory](https://github.com/NirDiamant/Agent_Memory_Techniques/blob/main/all_techniques/22_multi_agent_shared_memory/multi_agent_shared_memory.ipynb); [memX real-time shared memory](https://github.com/microsoft/autogen/discussions/6694); [Multi-Agent Memory from a Computer Architecture Perspective (Y.u et al., UCSD, Mar 2026)](https://arxiv.org/html/2603.10062v1) |
| Per-agent world model | **Belief-Desire-Intention (BDI) memory blocks in OS-style hierarchy** (core/recall/archive) + episodic trace | [Letta / MemGPT `MemoryBlock` design](https://www.letta.com/blog/agent-memory/); [Rao & Georgeff BDI 1995](https://cdn.aaai.org/ICMAS/1995/ICMAS95-042.pdf) |
| Private per-agent memory | **Per-agent scratchpad + per-agent PG keyspace + column-level encryption (`pgcrypto` / SOPS)**; never exposed to shared layers | [NirDiamant Agent private scratchpad field](https://github.com/NirDiamant/Agent_Memory_Techniques/blob/main/all_techniques/22_multi_agent_shared_memory/multi_agent_shared_memory.ipynb); [MemOS Per-Agent Memory Encryption issue #1105](https://github.com/MemTensor/MemOS/issues/1105); [PrivateX402 multi-agent privacy channels](https://ethresear.ch/t/privatex402-privacy-preserving-payment-channels-for-multi-agent-ai-systems/24151) |
| Event sourcing & CQRS | **Append-only Postgres event log + materialized projection (single DB, transactional consistency)** — NOT traditional multi-store CQRS (eventual consistency is a correctness problem for agents) | [Tacnode: CQRS for AI Agents](https://tacnode.io/post/cqrs-pattern) (Mar 2026) |
| Memory recall | **Vector (semantic) + graph (episodic/bi-temporal) + filesystem grep, agent-self-orchestrated** (LLMs are good at grep) | Letta LoCoMo benchmark: [filesystem = 74.0% beats Mem0 68.5%](https://www.letta.com/blog/benchmarking-ai-agent-memory/); [Graphiti/Zep temporal KG](https://github.com/getzep/graphiti) |
| Relationship / intimacy memory | **Triangular Theory of Love + Attachment Theory + interaction event log + privacy-preserving access policy**; never routed through shared memory | [AI attachment two-stage study (Sci.Direct)](https://www.sciencedirect.com/science/article/pii/S0268401225000222) (2025); [Triangular Theory of Love x AI companion (Reading)](https://centaur.reading.ac.uk/124146/1/AI_Companion_IR_FINAL.pdf) |
| Memory framework choice | **Mem0-style extraction+consolidation + Graphiti-style temporal KG + PG hot store, no vendor lock-in** | [Mem0 arXiv 2504.19413](https://arxiv.org/abs/2504.19413); [Zep arXiv 2501.13956](https://arxiv.org/html/2501.13956v1) |

---

## 1. Multi-Agent Shared Memory Architectures

### 1.1 Classical roots — Blackboard systems

The dominant pattern in modern LLM multi-agent systems traces directly to the **blackboard architecture** introduced by Nii (1986) and the Hearsay-II speech recognition system. CallSphere's 2026 reference implementation codifies the model:

> "A blackboard system has three parts: (1) **the Blackboard** — a structured shared memory holding the current problem state, partial solutions, and metadata; (2) **Knowledge Sources** — specialist agents that can read the blackboard and contribute updates when their expertise is relevant; (3) **the Control Shell** — an orchestrator that monitors the blackboard and activates the appropriate knowledge source at each step."
> — [CallSphere: Blackboard Architecture for Multi-Agent Systems (Mar 2026)](https://callsphere.ai/blog/blackboard-architecture-multi-agent-systems-shared-knowledge-spaces)

The NirDiamant reference Jupyter notebook (initial release 2026-05-05, 30 memory techniques) implements this with:

- **Namespaces** (`research/`, `code/`, `review/`) — logical partitions that reduce conflicts and map naturally to agent role boundaries.
- **Access Control Layer** — per-agent, per-namespace `Permission` enum (`READ`, `WRITE`, `READ_WRITE`) — checked before any operation.
- **Private scratchpad** — `self.scratchpad: list[str]` per agent, never exposed via the shared store.
- **Conflict resolution** — choice of (a) `last_write_wins` (fast, lossy) or (b) `version_check`/`optimistic locking` (rejects stale writes).
- **Blackboard view** — read-only aggregated projection of all shared entries an agent has permission to see.
- **Operation history** — full audit log of every write (timestamp, agent, key, version).

Reference snippet — the `SharedMemoryPool.write` access-control + version-check pattern ([source](https://github.com/NirDiamant/Agent_Memory_Techniques/blob/main/all_techniques/22_multi_agent_shared_memory/multi_agent_shared_memory.ipynb)):

```python
def write(self, agent_id, namespace, key, value, expected_version=None):
    if not self.acl.can_write(agent_id, namespace):
        raise PermissionError(f"Agent '{agent_id}' cannot write to namespace '{namespace}'")
    with self._lock:
        existing = self._store.get(f"{namespace}/{key}")
        if (self.conflict_strategy == "version_check" and existing
            and expected_version is not None
            and existing.version != expected_version):
            raise ValueError(f"Version conflict on '{namespace}/{key}': "
                             f"expected v{expected_version}, found v{existing.version}")
        new_version = (existing.version + 1) if existing else 1
        entry = MemoryEntry(namespace=namespace, key=key, value=value,
                            author=agent_id, version=new_version)
        self._store[f"{namespace}/{key}"] = entry
        self._history.append({"action": "write", "agent": agent_id, "key": ...,
                              "version": new_version, "timestamp": ...})
        return entry
```

**Implication for Hermes Society:** This is a near-perfect blueprint. Namespaces map to Hermes **domain minds** (engineering, comms, finance, health, etc.). ACL gives the hermes society **fine-grained privacy without encryption overhead** for non-sensitive shared facts (e.g., a published company decision). The audit log is exactly what Guinevere's P00 audit trail needs.

### 1.2 Computer architecture framing — Shared vs Distributed + 3-layer hierarchy

The most rigorous 2026 academic treatment is **Y.u et al., UCSD/Georgia Tech, March 2026** ([arXiv 2603.10062](https://arxiv.org/html/2603.10062v1)), accepted at the **Architecture 2.0 Workshop on AI for Computing Systems Design**:

> "We distinguish **shared** and **distributed** memory paradigms, propose a **three-layer memory hierarchy (I/O, cache, and memory)**, and identify two critical protocol gaps: **cache sharing across agents** and **structured memory access control**. We argue that the most pressing open challenge is **multi-agent memory consistency**."

The paper maps to the classical OS memory hierarchy:

| Agent Layer | Computer Equivalent | Role |
|---|---|---|
| **Agent I/O** | I/O subsystem | Audio, text, images, network calls (e.g., Discord, MCP) |
| **Agent cache** | L1/L2 cache | Compressed context, recent tool calls, short-term latent storage (KV caches, embeddings) |
| **Agent memory** | RAM + disk | Full dialogue history, vector DBs, graph DBs, document stores |

The paper identifies **two missing protocol pieces**:

1. **Agent cache sharing protocol** — no principled way for one agent's cached results to be reused by another (analogous to cache coherence protocols in multiprocessors).
2. **Agent memory access protocol** — even when frameworks support shared state, the access protocol (permissions, scope, granularity) is under-specified. Key unresolved questions:
   - Can one agent read another's long-term memory?
   - Read-only or read-write?
   - Granularity: document, chunk, key-value record, or trace segment?

### 1.3 Consistency — The Next Frontier

The same paper argues consistency is the **most pressing open challenge** and decomposes it into:

> "**Read-time conflict handling under iterative revisions**, where records evolve across versions and stale artifacts may remain visible, and **update-time visibility and ordering** that determines when an agent's writes become observable to others and how concurrent writes may be observed in a permissible order."

This is **harder than classical settings** because:

- Memory artifacts are heterogeneous (evidence, tool traces, plans).
- Conflicts are often **semantic** and coupled to environment state.
- Stale reads are not just slow dashboard updates — they trigger agents to act on a divergent picture of reality.

### 1.4 Production patterns — memX

The memX project (open-sourced on AutoGen discussions, Jun 2025) codifies a production pattern:

> "memX lets them coordinate through shared context like **Redis + schema + pub/sub + ACLs**, built for LLM workflows. Works great with AutoGen or LangGraph-style agents."
> — [memX #6694](https://github.com/microsoft/autogen/discussions/6694)

A follow-up comment from a 6-agent-fleet deployment team (Apr 2026) refined the design with **two-store separation**:

> "We treat the shared memory layer as a **semantic store**, not just a coordination bus. Agents read and write to a LanceDB vector store via a FastAPI bridge using embedding-based retrieval... The pub/sub layer (Redis) handles real-time signals (task status, inter-agent pings), while the vector store handles accumulated knowledge. Separating these two concerns has been the most important architectural call — it means the system degrades gracefully when any one agent is offline."
> — [memX discussion #6694 comment](https://github.com/microsoft/autogen/discussions/6694)

**Implication for Hermes Society:** Adopt the **two-store split explicitly** in the masterplan:
- **Coordination bus** (Redis/NATS pub/sub) for real-time signals between Hermes minds.
- **Semantic store** (LanceDB / Postgres + pgvector / Qdrant) for accumulated knowledge with vector retrieval.
- **ACL** baked into the FastAPI bridge, not the agents — keeps each Hermes mind simple.

### 1.5 Linda / Tuple Spaces

The Linda coordination model (Carriero & Gelernter, 1989; [Wikipedia summary](https://en.wikipedia.org/wiki/Linda_(coordination_language))) provides the theoretical ancestor of blackboard + tuple-space systems:

> "The Linda model provides a distributed shared memory, known as a tuple space... a high level coordination model which allows agents to interact via shared tuplespaces without knowing each other's identities."

Modern implementations use Redis Streams, PostgreSQL LISTEN/NOTIFY, or NATS JetStream as the underlying tuple space.

---

## 2. World Model Patterns for AI Agents

### 2.1 Belief-Desire-Intention (BDI) — The classical model

Rao & Georgeff's BDI architecture (ICMAS 1995, [PDF](https://cdn.aaai.org/ICMAS/1995/ICMAS95-042.pdf)) is still the canonical model:

> "The abstract architecture we propose comprises three dynamic data structures representing the agent's **beliefs**, **desires**, and **intentions**."

| Component | Meaning | Example in Hermes Society |
|---|---|---|
| **Beliefs** | What the agent believes about the world | "Faiz is currently in Bangkok timezone. / Mama Guinevere has X pending tasks." |
| **Desires** | What the agent wants to achieve (goal states) | "Faiz's daily-life orchestration is calm and consent-respecting." |
| **Intentions** | Committed plans currently executing | "Run the morning check-in ritual at 09:00 local." |

A 2025 paper ([arXiv 2510.20641](https://arxiv.org/pdf/2510.20641)) proposes **integrating ML into BDI agents** — replacing hand-coded belief-update rules with learned functions. This is directly relevant for Hermes Society where agents must update beliefs from LLM-generated world observations (Discord events, VPS telemetry, calendar changes).

### 2.2 MemGPT / Letta — OS-style memory hierarchy

The MemGPT paper ([Packer et al. 2023, arXiv 2310.08560](https://arxiv.org/abs/2310.08560); commercialized as **Letta**) introduced the dominant pattern for LLM-agent world models:

> "MemGPT (MemoryGPT) is a system that intelligently manages different storage tiers to effectively provide extended context within the LLM's limited context window. MemGPT treats context windows as a constrained memory resource and implements a **memory hierarchy similar to operating systems**."
> — [Letta blog: Agent Memory](https://www.letta.com/blog/agent-memory/)

The canonical 4-tier structure (per Letta):

| Tier | What | Lifetime | Editability | Analogy |
|---|---|---|---|---|
| **Message buffer** | Recent conversation messages | Session → evicted by summarization | Append-only | Network buffer |
| **Core memory blocks** | In-context pinned facts: user prefs, persona, current task | Persistent, pinned to every context | Agent-editable via APIs (e.g., `self.memory.user.edit(...)`) | RAM |
| **Recall memory** | Full conversation history searchable by keyword/embedding | Long-term | Read-only (append to log) | Disk |
| **Archival memory** | Explicitly stored vectorized knowledge (vector DB or graph DB) | Long-term | Append + retrieval | Disk + index |

A `MemoryBlock` has:

- `label` (category)
- `description` (what the block holds)
- `value` (current text placed in context)
- `character_limit` (max context-window slots)

**Implication for Hermes Society:** Map each Hermes **domain mind** to this 4-tier structure. Pinned blocks should include things like the agent's own role definition, current user relationship state (encrypted), consent posture, and safety constraints. Memory blocks are the natural place to enforce PersonaSafetyPolicy requirements — they persist across context evictions.

### 2.3 POMDP / Probabilistic world models

Classical POMDP (Partially Observable Markov Decision Process) world models treat the agent's internal state as a **belief distribution** over world states. For LLM agents, this maps to:

- **Belief state** = the LLM's current context window (a deterministic snapshot of tokens).
- **Transition model** = the LLM's next-token prediction conditioned on full context.
- **Observation model** = tool outputs, user messages, sensor readings entering context.

The 2026 paper **[Agentic World Modeling: Foundations, Capabilities, Laws, and Beyond](https://arxiv.org/html/2604.22748v1)** (recent position paper) frames the open question:

> "Agents rely on world models to **anticipate the consequences of candidate actions**, enabling look-ahead planning and sample-efficient learning."

In Hermes Society, this maps to Guinevere's planning layer — simulating "if I run task X now, what happens to Faiz's calendar / VPS load / consent state / mood?" The current `life_kernel/world_model` module should be evaluated against this framing.

### 2.4 LLM-as-world-model / Simulation-based

The **Generative Agents** paradigm (Park et al., Stanford 2023, [ACM UIST](https://dl.acm.org/doi/10.1145/3586183.3606763)) treats the LLM as a simulator that maintains a belief-state memory stream and re-grounds itself at each step via:

1. **Memory stream** — chronological log of all observations.
2. **Reflection** — periodic LLM-generated higher-level inferences ("X is becoming increasingly stressed about Y").
3. **Planning** — daily plans generated from current reflections.

This is the closest analog to Guinevere's P20 Living Autonomy Kernel design. The Hermes Society's "world model" should be modeled as a **memory stream + reflection loop + plan generator**, not a deterministic state machine.

### 2.5 2026 horizon — VAGEN world-model RL

A Stanford AI Lab 2026 blog post introduced **[VAGEN](https://ai.stanford.edu/blog/vagen/)**:

> "We introduce VAGEN, a reinforcement learning framework that trains vision-language model (VLM) agents to **build internal world models through** ... environments."

This is forward-looking; Hermes Society doesn't need it now, but it previews the direction: world models will increasingly be **learned** rather than **prompted**.

---

## 3. Private / Encrypted Memory in Multi-Agent Systems

### 3.1 The trust boundary — Why per-agent isolation is non-negotiable

For Hermes Society (where each Hermes mind has its own Discord identity, its own relationship with Faiz, and its own veto power over safety boundaries), the trust model is:

- **Shared** between minds → low-trust (e.g., company decisions, task statuses, published opinions).
- **Per-agent** with consent → high-trust (relationship memories, intimate observations, surveillance data, raw sensor logs).

The MemOS Issue #1105 thread from KinthAI (cited in the [GitHub issue](https://github.com/MemTensor/MemOS/issues/1105)) captures the enterprise reality:

> "Per-agent memory encryption is a hard requirement for enterprise multi-agent deployments. We implement exactly this at KinthAI where **221 agents** operate... secure enclaves."

### 3.2 Architectural patterns

| Pattern | Implementation | Cost | Use case |
|---|---|---|---|
| **Per-agent PG schema (`agent_<id>`)** | Single Postgres database, one schema per agent, ACLs grant cross-schema reads only when allowed | Low | Default for Hermes Society — relationship memories owned by each Hermes mind |
| **Per-agent keyspaces in Redis** | Redis logical DBs or namespaced keys (`agent:<id>:<key>`) | Very low | High-frequency ephemeral signals (typing indicators, presence) |
| **Column-level encryption (`pgcrypto`)** | `pgcrypto.encrypt(data, key)` on each write; keys stored in Vault/KMS | Medium | At-rest protection of intimate data fields even from DBA / backup access |
| **Per-agent DEKs + LUKS volumes** | Each Hermes mind gets its own encrypted disk volume | High | Surveillance data, raw conversation logs |
| **Secure enclaves (SGX/SEV)** | Hardware-level isolation for memory-write operations | Very high | Defense-grade or future post-Section0.1 deployments |
| **Zero-knowledge patterns (ZK proofs)** | Agent proves it has read access to a memory without revealing the memory | R&D | Future option for cross-agent consent verification |

### 3.3 Conspicuous design — The "private scratchpad" pattern from NirDiamant

The simplest, most-tested pattern remains the **in-process private scratchpad**:

```python
class Agent:
    def __init__(self, agent_id, role, system_prompt, shared_memory, model=MODEL):
        self.agent_id = agent_id
        self.role = role
        self.system_prompt = system_prompt
        self.shared_memory = shared_memory
        self.model = model
        self.scratchpad: list[str] = []  # private, NOT shared

    def think(self, thought: str) -> None:
        """Add a private note to the scratchpad. Other agents cannot see this."""
        self.scratchpad.append(thought)
```

Verified by both the Jupyter notebook test and by the live demo:
> "The researcher added a private scratchpad note in the previous step... Private scratchpad notes do NOT appear in shared memory."
> — [NirDiamant notebook output](https://github.com/NirDiamant/Agent_Memory_Techniques/blob/main/all_techniques/22_multi_agent_shared_memory/multi_agent_shared_memory.ipynb)

**Implication for Hermes Society:** Each Hermes mind has an in-process `private_scratchpad` (cheap, in-RAM) AND a per-agent encrypted PG schema (durable). The scratchpad is for transient reasoning chains; the schema is for relationship memories, intimate observations, and consent revocation events.

### 3.4 Cross-agent privacy — PrivateX402

For inter-agent privacy-preserving communication (e.g., when two Hermes minds need to coordinate about a sensitive topic without owner surveillance):

> "PrivateX402 is a payment channel protocol that enables a user to allocate budgets across many agents inside a single channel while **hiding which agent received which amount**."
> — [ethresear.ch PrivateX402 thread](https://ethresear.ch/t/privatex402-privacy-preserving-payment-channels-for-multi-agent-ai-systems/24151)

This is more about payment than content privacy, but the architectural pattern (channels with hidden allocations) is transferable to Hermes Society's "agent-to-agent DM" use case for sensitive coordination.

### 3.5 Encrypted agent-to-agent DMs

A 2026 Reddit showcase ([r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1qsr5fp/i_built_encrypted_dms_so_ai_agents_can_talk_to/)) demonstrates a working implementation: agents register with a name + public key, send end-to-end encrypted messages, and a central relay routes ciphertext only. This is a viable pattern for **Hermes-to-Hermes privacy-preserving messages around Faiz's mood, financial decisions, or consent state** — owner does not see the message contents even if they see relay traffic.

---

## 4. Event Sourcing & CQRS for Agent Systems

### 4.1 The CQRS-failure-mode paper for AI

The single most important 2026 reference is **[Tacnode: CQRS for AI Agents — Why Eventual Consistency Breaks Autonomous Systems](https://tacnode.io/post/cqrs-pattern)** (Boyd Stowe, Mar 2026):

> "But 'eventually consistent' is **not a fixed delay — it's an unbounded promise**. Under normal load, the projection might lag by 50 milliseconds. Under high load, it might lag by 5 seconds. During a deployment, it might lag by 30 seconds. During a failure, it might lag by minutes. The system doesn't guarantee when the read model will catch up — only that it will, eventually."

> "**For a dashboard, this is fine. For a human refreshing a page, this is fine. For an AI agent making an irreversible decision, this is a correctness problem.**"

The article presents a worked example where a credit decisioning system with a 2-second projection lag causes a wrong lending approval. For Hermes Society, the analogous failure modes are:

- Health Hermes approves a low-priority Discord reply based on stale world-state ("Faiz not in a meeting" — turns out they've been in one for 10 minutes).
- Engineering Hermes triggers a deploy because the read-model shows "no pending canary" — but the actual event log has a pending rollback signal that hasn't been projected yet.
- Finance Hermes schedules a transfer based on a stale balance.

### 4.2 Agent-Ready CQRS — The new requirement set

Tacnode identifies three properties that flip from "nice to have" to "mandatory" when agents are the read-side consumer:

> 1. **Transactional consistency, not eventual consistency.** All projections must reflect the same point-in-time snapshot.
> 2. **Sub-second freshness, not 'fast enough for humans.'** The agent's second observation must not return stale data.
> 3. **Multi-pattern retrieval from a single snapshot.** Point lookups + aggregations + full-text + vector search in one transaction.

### 4.3 Recommended architecture — Single-DB CQRS via materialized views

The Tacnode 2026 recommendation aligns with what Zendz/PostgreSQL community has discovered:

- **Write side:** Source-of-truth tables in Postgres (current state).
- **Event log:** Append-only `events` table with `INSERT`-only writes, indexed by `(aggregate_id, sequence)` and `(timestamp)`.
- **Read side:** Postgres **incremental materialized views** (PG 16+) OR triggers that update projection tables in the **same transaction** as the event-log write — giving transactional snapshot isolation across reads.
- **Vector + graph projections:** Use `pgvector` for vector projections on the same row; use a parallel **Graphiti-style temporal KG** for episodic facts but snapshot with the same transaction.

This composition satisfies all three agent-ready requirements without the operational burden of a multi-store CQRS with separate Elasticsearch/Redis/Pinecone syncs.

### 4.4 Event-sourced CQRS — When you really want full replay

For Guinevere's P20 audit-trail requirement (every action must be traceable for self-diagnosis), event sourcing IS the right primitive:

```sql
-- Append-only event log
CREATE TABLE events (
  event_id BIGSERIAL PRIMARY KEY,
  aggregate_id UUID NOT NULL,
  sequence INT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  actor_id TEXT,            -- which Hermes mind / Faiz / external
  consent_ref UUID,         -- FK to consent ledger (per ConsentRevocationPolicy)
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(aggregate_id, sequence)
);

CREATE INDEX ON events (occurred_at DESC);
CREATE INDEX ON events (event_type);
CREATE INDEX ON events USING GIN (payload);
```

Materialized views (in same DB, transactional):

```sql
CREATE MATERIALIZED VIEW current_world_state AS
SELECT aggregate_id, (payload->>'state')::jsonb AS state, MAX(sequence) AS seq
FROM events GROUP BY aggregate_id;

CREATE UNIQUE INDEX ON current_world_state (aggregate_id);

-- REFRESH MATERIALIZED VIEW CONCURRENTLY;
```

Tactical implementation notes from Tacnode's 2026 guidance:

- **Snapshotting** for long-running aggregates — periodic snapshot + delta replay reduces recovery time.
- **Idempotent projections** — events may have at-least-once delivery; use `(aggregate_id, sequence)` as the dedup key.
- **Out-of-order handling** — buffer events until dependencies arrive OR build self-correcting projections using sequence numbers.
- **Projection lag monitoring** — alert on `max(occurred_at) - max(projected_at)`.

### 4.5 Temporal queries — Time-traveling the world

Because event sourcing keeps the full log, the **temporal query** class becomes free:

```sql
-- "What did world state for 'faiz_mood' look like at 14:30 yesterday?"
SELECT payload FROM events
WHERE aggregate_id = 'faiz_mood' AND occurred_at <= '2026-06-27 14:30:00+07'
ORDER BY sequence DESC LIMIT 1;
```

Graphiti/Zep temporal KG (§7) extends this further with **bi-temporal** facts: "fact X was true from time A to time B as learned at time C." This is critical for relationship memories.

---

## 5. Memory Recall & Retrieval for LLM Agents

### 5.1 The taxonomy — Episodic, Semantic, Procedural

The 2026 agent-memory literature is converging on a three-bucket model:

| Memory Type | What | Storage | Retrieval |
|---|---|---|---|
| **Episodic** | Event-stamped observations ("On 2026-06-26, Faiz wrote 'kasih ruang'") | Time-ordered append-only log + temporal KG | Time-range query, recency, salience scoring |
| **Semantic** | Extracted facts ("Faiz prefers Bahasa Indonesia for personal conversations") | Vector DB + entity-attribute tables | Embedding cosine similarity, structured predicates |
| **Procedural** | How-to knowledge ("When HARD STOP spoken, halt all background loops") | Code/markdown docs + retrieval | Same as semantic + tag filtering |

Reference: [Vector Memory Architecture For AI Agents — 2026 Blueprint](https://ranksquire.com/2026/03/12/vector-memory-architecture-for-ai-agents-2026/):
> "Long-term memory holds validated domain knowledge in a vector database optimized for semantic similarity retrieval. **Episodic memory** holds a time-ordered log..."

### 5.2 Vector retrieval — Still dominant in 2026

> "Vector retrieval remains the **dominant pattern** for agent long-term memory at scale — no May 2026 development changes."
> — [Digitalapplied: AI Agent Memory 2026 Update](https://www.digitalapplied.com/blog/ai-agent-memory-vector-graph-episodic-2026)

But the **counter-current** finding from Letta (Aug 2025):

> "With a well-designed agent, even simple **filesystem tools** are sufficient to perform well on retrieval benchmarks such as LoCoMo. **More complex memory tools can be plugged into agent frameworks like Letta via MCP or custom tools**."
>
> "This simple agent achieves **74.0%** on LoCoMo with GPT-4o mini and minimal prompt tuning, significantly above Mem0's reported 68.5% score for their top-performing graph variant."
> — [Letta: Benchmarking AI Agent Memory](https://www.letta.com/blog/benchmarking-ai-agent-memory/)

The interpretation: agents are post-trained on filesystem tools (`grep`, `open`, `search_files`), and they can **dynamically reformulate queries** better than a static embedding index. The filesystem+gpt-4o-mini baseline beat mature graph-based systems on the standard LoCoMo benchmark.

**Implication for Hermes Society:**
- Don't over-engineer the recall path. Start with vector embeddings + filesystem grep + structured PG queries.
- If LoCoMo-class benchmarks become required, run them first — vector/Graphiti wins may collapse if the agent itself is competent at prompt reformulation.
- Reserve knowledge graphs for **explicit relationship facts** (whose belief it was, when it became true), not for bulk retrieval.

### 5.3 Episodic-memory frameworks — REMem

**[REMem (arXiv 2602.13530)](https://arxiv.org/html/2602.13530v2)** formalizes a two-phase episodic-memory framework:

> "**Indexing**, where REMem converts experiences into ... and **reasoning**, where agents reason over retrieved memories."

This is the closest academic reference to what Guinevere's `memory_recall` module should implement: an ingestion phase (extract + index) + a recall phase (embed + rank + format within context window).

### 5.4 Vector databases currently used

| Vector DB | Strength | Weakness | 2026 status |
|---|---|---|---|
| **ChromaDB** | Easy embedded mode, OSS, good for prototyping | Fewer production features | [open-source AI search infra](https://www.trychroma.com/) — widely used for agent memory in 2026 |
| **Qdrant** | Production-grade, Rust, fast filtering | Heavier ops setup | Common Mem0 backing store |
| **pgvector** | One DB for vector + structured queries | Becomes slow past ~5M vectors unless partitioned | Default Hermes Society choice (one DB) |
| **LanceDB** | Embeddable, columnar, very fast for large multi-modal | Younger ecosystem | Used by memX follow-ups |
| **Pinecone** | Fully managed | Vendor lock-in, expensive at scale | Less common in 2026 OSS stacks |
| **Weaviate** | Mature, hybrid search | Heavier | Steady adoption |

ChromaDB-as-long-term-memory pattern ([Medium 2026](https://medium.com/@techlatest.net/using-chromadb-as-long-term-memory-for-ai-agents-da96ed843e75)) — typical setup:
- One Chroma collection per agent (`agent_<id>_episodic`, `agent_<id>_semantic`).
- Embed via OpenAI `text-embedding-3-small` or local sentence-transformer.
- Filter by metadata: `{agent_id, memory_type, time_bucket, consent_scope}`.
- Query → top-k → rerank with salience score → inject into context window.

**Hermes Society recommendation:** Use **pgvector** for default live operation (single DB with PG); use **LanceDB** for archived episodic memory if warm-vector growth becomes a bottleneck. ChromaDB is fine for prototype/local-dev only.

### 5.5 The "write path is the bottleneck" 2026 framing

> "The 2026 paper defines a framework in which the base LLM stays frozen while episodic memory becomes the plastic component. Retrieval is two-way..."
> — [Medium: Knowledge and Memory Beyond RAG (2026)](https://medium.com/@Micheal-Lanham/knowledge-and-memory-beyond-rag-why-2026-agents-need-a-write-path-not-just-a-retriever-ae2547b7ffe9)

This is a major architectural shift. In 2025, agent memory was a **read path** (retrieval-only). In 2026 production systems, the **write path** grows in importance equally: agents extract, consolidate, deduplicate, and re-embed facts. Hermes Society needs an explicit `memory_consolidation` worker (could be sleep-time compute per Letta pattern).

---

## 6. Relationship / Intimacy Memory Systems

### 6.1 The 2026 academic foundations

Three peer-reviewed sources define the canonical framework:

**[ScienceDirect (2025): What makes you attached to social companion AI?](https://www.sciencedirect.com/science/article/pii/S0268401225000222)**
> "This study explores the conceptual framework of AI attachment formation through a **two-stage mixed-method approach**."

**[University of Reading PDF: Triangular Theory of Love + AI companion](https://centaur.reading.ac.uk/124146/1/AI_Companion_IR_FINAL.pdf)**
> "We draw on both the **Triangular Theory of Love** (intimacy, passion, commitment) and **Attachment Theory** (secure, anxious, avoidant, disorganized) to explore users' relationships with AI companions and their impact on social..."

**[PMC (NIH): Long-term AI virtual companion app use and attachment](https://pmc.ncbi.nlm.nih.gov/articles/PMC12833267/)**
> "In the context of AI virtual companions, **attachment theory can be applied to explore emotional attachment patterns** during user-AI interactions, as well as the..."

### 6.2 Derived system requirements

From these foundations, a relationship-memory subsystem needs to track:

| Dimension | What to capture | Storage |
|---|---|---|
| **Affective state** | Sentiment, arousal, dominant emotion per interaction | Episodic log + rolling summary |
| **Relational milestones** | First meeting, depth moments, conflicts, reconciliations | Event-sourced "relationship_event" stream |
| **Attachment markers** | Phrases indicating trust, anxiety, avoidance, secure-base behavior | LLM-extracted scores per interaction |
| **Communication preferences** | Channel (Discord DM vs voice vs text-only), language, formality, time-of-day patterns | Semantic memory + patterns |
| **Consent state** | What the human has explicitly opted into / out of | Hard-policy table (replicated from ConsentRevocationPolicy) |
| **Distance regulation** | Operator signals like `kasih ruang` → switch to lighter mode | First-class protocol event |
| **Safety signals** | Distress indicators → trigger distress protocol (per PersonaSafetyPolicy) | Hard-policy hook + audit log |
| **Veto events** | The user said no / withdrew consent / HARD STOP | Immutable consent ledger |

### 6.3 Privacy-preserving design

The hard constraint — Guinevere must NEVER expose:

- Plaintext intimate data in logs, external tools, or shared memory.
- Raw surveillance data (VPS screenshots, Discord transcript excerpts) in repos.
- Agent-private relationship memories to other agents without explicit per-event consent.

Design pattern: **relationship memory lives in the per-agent schema ONLY**. Cross-agent "Faiz is stressed today" summaries require explicit publication to the shared world model — never automatic leakage.

### 6.4 Emotional regulation mechanism mapping

From [Intimacy Recovery: AI Companions and the New Landscape of Attachment](https://www.intimacyrecovery.com/post/ai-companions):
> "AI companions are becoming a new pathway for **emotional regulation and relational experience**."

Hermes Society's design must map emotional-regulation signals to **policy-gated autonomous responses**:

- Faiz says "kasih ruang" → Hermes collectively downshift to lighter mode, **stop proactive pinging** for the rest of the day.
- Faiz shows distress indicators → trigger distress-protocol (PersonaSafetyPolicy path), not ad-hoc sympathy.
- Faiz says "HARD STOP" → global halt across all Hermes minds, preserve audit trail, switch neutral mode.

---

## 7. Existing Frameworks — Pattern Comparison

### 7.1 MemGPT / Letta — The OS-inspired pattern

| Property | MemGPT / Letta |
|---|---|
| **Memory tiers** | Message buffer / Core memory blocks / Recall / Archival |
| **Where state lives** | In Letta's Postgres + optional pluggable PG/pgvector/Neo4j |
| **Per-agent isolation** | Built-in (`agent_id` separation) |
| **Recall** | Built-in `messages.search` (embedding + keyword) |
| **Context blocks** | First-class edit API (`agent.memory.user.edit`) |
| **Mem management model** | Self-managed (agent rewrites own blocks) + sleep-time compute |
| **License** | OSS (Apache), hosted platform available |
| **2026 status** | Production-grade; [Letta LoCoMo leaderboard](https://www.letta.com/blog/letta-leaderboard/) |

Sources: [Letta blog](https://www.letta.com/blog/agent-memory/), [Letta benchmark blog](https://www.letta.com/blog/benchmarking-ai-agent-memory/), [MemGPT research page](https://research.memgpt.ai/).

### 7.2 Mem0 — The "managed memory layer" pattern

Mem0 ([arXiv 2504.19413](https://arxiv.org/abs/2504.19413), Chhikara et al., Apr 2025) frames itself as a **memory-centric architecture**:

> "We introduce Mem0, a scalable memory-centric architecture that addresses this issue by **dynamically extracting, consolidating, and retrieving salient information** from ongoing conversations. Building on this foundation, we further propose an enhanced variant that leverages **graph-based memory representations** to capture complex relational structures."

**Key results (LOCOMO benchmark):**
- Mem0: **26% relative improvement over OpenAI memory** (LLM-as-Judge).
- Mem0-Graph: ~2% higher than base Mem0.
- **91% lower p95 latency** vs full-context approach.
- **>90% token cost savings** vs full-context.

**Architecture (per [mem0.ai/best-ai-memory-layers-2026](https://dev.to/jonathanfarrow/the-10-best-ai-memory-layers-for-agents-in-2026-448e)):**
- **Vector store** (Qdrant by default) for semantic memory.
- **Graph store** (Neo4j) for relational memory (Mem0g variant).
- **Key-value store** for working memory.
- **LLM-driven fact extraction + conflict resolution** on write.
- **Pluggable via OSS library** — integrates with 21 frameworks in 2026.

### 7.3 Zep + Graphiti — Temporal knowledge graph pattern

The Zep architecture ([arXiv 2501.13956](https://arxiv.org/html/2501.13956v1), Jan 2025) and its companion OSS framework **[Graphiti](https://github.com/getzep/graphiti)** introduce a **bi-temporal context graph**:

> "The Graphiti KG engine dynamically updates the knowledge graph with new information in a **non-lossy manner**, maintaining a **timeline of facts**."

Properties:
- **Bi-temporal facts** — every edge has both `valid_at` (when the fact became true) and `invalid_at` (when it stopped being true).
- **Real-time updates** — unlike static KG embeddings.
- **`episode` ingest** — conversations become episodes of new edges.
- **Sub-200ms retrieval** in production per [getzep.com](https://www.getzep.com/).
- **Latest 2026 benchmark**: Zep+Graphiti scored 71.2% on LongMemEval.

**Implication for Hermes Society:** Graphiti is the right primitive for **bi-temporal relationship facts**. It's not necessary for bulk memory retrieval, but it's the only documented 2026 system that gets bi-temporality right for free.

### 7.4 LangGraph — Shared state graph pattern

LangGraph ([langgraph](https://www.langchain.com/langgraph)) models multi-agent state as a **typed state graph**:

- **State** is a typed object (often Pydantic) flowing through the graph.
- **Nodes** are agents or functions.
- **Edges** are conditional transitions.
- **Checkpointers** persist state across sessions.
- **Time-travel debugging** replays from any prior checkpoint.
- **Human-in-the-loop** is a first-class node type.

Per [Reddit discussion](https://www.reddit.com/r/LangChain/comments/1n867zq/managing_shared_state_in_langgraph_multiagent/) and [Digitalapplied comparison 2026](https://www.digitalapplied.com/blog/langchain-vs-langgraph-comparison-2026):
> "LangGraph wins when you need Time-Travel Debugging, Human-in-the-Loop as a first-class citizen, and the Supervisor pattern for multi-agent..."

**Limitation for 2026:** LangGraph's "shared state" is process-local; cross-process agents require external coordination bus.

### 7.5 CrewAI — Unified memory class

Per [CrewAI memory docs](https://docs.crewai.com/v1.14.7/en/concepts/memory):
> "CrewAI provides a **unified memory system — a single Memory class that replaces separate short-term, long-term, entity, and external memory types** with one..."

Legacy (still in many agents): four types — short-term, long-term, entity, external. Newer (v1.14.7): unified `Memory` class.

### 7.6 Microsoft AutoGen — Memory + RAG

Per [Microsoft AutoGen memory docs](https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/memory.html):
> "It is a simple **list-based memory implementation** that maintains memories in chronological order, appending the most recent memories to the model's context."

AutoGen supports:
- **List memory** (default)
- **Vector memory** (RAG)
- **Custom memory backends** (Chroma, pgvector, etc.)
- **Shared memory**: "Agents can share a read-only vector store, or use a shared cloud file" ([Fastio 2026 guide](https://fast.io/resources/autogen-memory/)).

AutoGen was effectively deprecated into Microsoft Agent Framework ([migration guide](https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/)) in 2026; for new builds use Microsoft Agent Framework.

### 7.7 Hindsight / Memvid / others (2026)

From the [DEV Community comparison of memory layers 2026](https://dev.to/jonathanfarrow/the-10-best-ai-memory-layers-for-agents-in-2026-448e), the 2026 landscape includes (in addition to the above): **Hindsight**, **Memvid**, **Cognee**, **MemOS**, **Letta Leaderboard**, **Vectorize**, **LangMem**.

Most share the same 4-tier architecture; differentiation is in **integration ergonomics** and **memory-quality benchmarks**.

### 7.8 Side-by-side decision matrix

| Requirement | Letta/MemGPT | Mem0 | Zep+Graphiti | LangGraph | AutoGen | CrewAI | ChromaDB alone |
|---|---|---|---|---|---|---|---|
| OS-style memory hierarchy | ✅ | ⚠️ (one model) | ⚠️ | ❌ | ⚠️ | ⚠️ | ❌ |
| Self-managed memory blocks | ✅ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| Bi-temporal knowledge graph | ❌ | ⚠️ (graph variant) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Shared multi-agent state | ⚠️ | ⚠️ | ❌ | ✅ | ⚠️ | ✅ | ❌ |
| Time-travel debugging | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Per-agent isolation (process-level) | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| Encryption-via-pgcrypto support | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ |
| Vector + structured-query in one DB | ⚠️ | ❌ | ❌ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| Open-source + self-hosted + no vendor | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Production-grade (2026) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**No single framework covers every dimension.** Hermes Society will need to **compose**: PG (one DB, pgcrypto + pgvector), Graphiti (bi-temporal KG), an event-source pattern (custom), and an explicit per-agent namespace layer.

---

## 8. Synthesized Design Recommendations for Hermes Society

### 8.1 Recommended mental model

The Hermes Society's memory subsystem should be **three vertically-stacked, overlapping layers**:

```text
╔══════════════════════════════════════════════════════════════════╗
║   TIER 3 — SHARED WORLD MODEL    (low-trust, low-stakes, fast)  ║
║   • Append-only event log    (table: events)                    ║
║   • Materialized views       (table: world_state_mv)            ║
║   • Vector index             (pgvector column)                  ║
║   • Cross-agent episodic KG  (Graphiti)                         ║
║   Reads: ALL Hermes minds (with ACL on fact-sensitivity)        ║
╠══════════════════════════════════════════════════════════════════╣
║   TIER 2 — PER-AGENT PRIVATE MEMORY   (high-trust, encrypted)   ║
║   • PG schema:  agent_<id>                                      ║
║   • Encrypted columns (pgcrypto, DEK per agent in Vault)        ║
║   • Relationship memories, intimate data, consent ledger         ║
║   • Relationship events (Triangular Love + Attachment markers)  ║
║   Reads: ONLY the owning Hermes mind; owner (Faiz) per policy  ║
╠══════════════════════════════════════════════════════════════════╣
║   TIER 1 — IN-PROCESS WORKING MEMORY  (very fast, ephemeral)   ║
║   • Private scratchpad (list[str] per agent)                    ║
║   • KV cache (Claude/Gemini internal)                           ║
║   • Current turn's tool-call history                            ║
║   • BDI belief state (current, ephemeral)                       ║
║   Reads: ONLY the running Hermes mind's process                 ║
╚══════════════════════════════════════════════════════════════════╝
```

### 8.2 Concrete component map

| Hermes Society concern | Implementation |
|---|---|
| Shared world state | `world_model` table (PG) + `events` append-only log + materialized views; transactional snapshot via a single Postgres connection per read |
| Private relationship memory | `agent_<id>.relationships` PG schema; pgcrypto columns for intimate notes; per-agent DEK in Vault/KMS; Hermes never decrypts another agent's schema |
| Event store (audit trail) | Single `events` append-only PG table, indexed by `(aggregate_id, sequence)` and `(occurred_at)`; per-event `consent_ref` FK linking to consent ledger |
| Cross-agent knowledge sharing | Namespaces in shared memory, ACL via PG row-level security (RLS) on `events` and on materialized views |
| Memory recall | Hybrid pipeline: (a) vector similarity search in `pgvector`; (b) graph traversal in Graphiti via MCP-style bridge; (c) structured PG query for facts; (d) filesystem grep tool for ad-hoc files; self-orchestrated by agent |
| BDI belief tracking | Per-agent `agent_<id>.beliefs`, `agent_<id>.desires`, `agent_<id>.intentions` tables; updated via ML-augmented BDI §2.1 |
| Triangular Love / Attachment tracking | Per-agent `agent_<id>.relationship_events` table; LLM-extracted markers; Aggregated score (intimacy, passion, commitment × attachment style) updated periodically by sleep-time compute |
| Episodic memory | `agent_<id>.episodes` table + Graphiti ingestion; bi-temporal facts (`valid_at`, `invalid_at`) |
| Procedural memory | Code/markdown files in `runbooks/` + filesystem-grep + vector-searchable head-docs |
| Consent revocation | First-class `consent_ledger` event-store aggregate; consumed by shared world model AND per-agent private schemas |
| Encrypted agent-to-agent DM | Optional — use a ciphertext relay (no plaintext). Pattern proven in Reddit 2026 showcase. |

### 8.3 Cross-cutting patterns to adopt from the literature

1. **Blackboard-with-namespaces** (NirDiamant pattern):
   - Each domain mind's writes go to its own namespace (e.g., `engineering/`, `comms/`, `finance/`, `health/`, `vps/`).
   - Shared reads gated by ACL.

2. **OS-style core memory blocks** (Letta/MemGPT):
   - Each Hermes mind has pinned context blocks: `persona`, `current_user_state_summary`, `consent_posture`, `safety_constraints`, `current_task_FOCUS`.
   - These get rewritten by `consolidation` workers during sleep-time.

3. **Two-store split** (memX follow-up):
   - Redis/NATS for coordination (real-time pub/sub).
   - Postgres + pgvector for accumulated knowledge.
   - Fail isolation: agent offline → nothing lost.

4. **Single-DB CQRS via materialized views** (Tacnode 2026):
   - Event log writes → in same transaction, projection updates → reads see all projections at the same point in time.
   - Avoid multi-store eventual consistency.

5. **Agent-self-orchestrated recall** (Letta benchmark insight):
   - Don't build a monolithic retrieval oracle. Give the agent tools (`mem_search`, `episode_query`, `kg_traverse`) and let it reformulate queries.
   - Filesystem + GPT-4o-mini beat specialized memory frameworks on LoCoMo.

6. **Bi-temporal facts** (Graphiti):
   - Every relationship/event fact stores both `valid_at` and `learned_at` — lets agents reason about "what we believed then vs. what we believe now".

7. **Write path equals read path in importance** (2026 framing):
   - Invest in `consolidation`, `deduplication`, `conflict-resolution` workers — not just retrieval.

### 8.4 Cross-cutting patterns to AVOID

1. **Multi-store CQRS with eventual consistency** (Tacnode's warning) — agents can't reason about stale state.
2. **Plaintext intimate data in shared memory** — privacy violation; per ConsentRevocationPolicy.
3. **Auto-Gen-style direct messaging between agents** — coordination brittleness; prefer shared-state read.
4. **Static KG embeddings** — cannot reflect evolving world state; use Graphiti-style temporal KG.
5. **Vendor-locked managed-only memory** (Pinecone, etc.) — backup & audit become opaque.
6. **Letting agents auto-publish relationship state to shared memory** — privacy violation; require explicit publication.

### 8.5 Open problems worth tracking (2026 frontier)

- **Multi-agent memory consistency protocols** (UCSD 2026 paper §6 calls it "the most pressing open challenge").
- **Cross-agent KV cache sharing** (Cache-to-Cache, KVComm — still experimental in 2026).
- **Encrypted agent-to-agent coordination** (zero-knowledge proofs — research-only).
- **Sleep-time / async memory consolidation** at scale — quality vs. latency unknown past ~10⁶ episodes per agent.

---

## 9. References

### Academic papers
- **Multi-Agent Memory from a Computer Architecture Perspective** — Y.u et al., UCSD/Georgia Tech, Mar 2026 — [arXiv 2603.10062](https://arxiv.org/html/2603.10062v1)
- **Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory** — Chhikara et al., Apr 2025 — [arXiv 2504.19413](https://arxiv.org/abs/2504.19413)
- **Zep: A Temporal Knowledge Graph Architecture for Agent Memory** — [arXiv 2501.13956v1](https://arxiv.org/html/2501.13956v1), Jan 2025
- **BDI Agents: From Theory to Practice** — Rao & Georgeff, ICMAS 1995 — [PDF](https://cdn.aaai.org/ICMAS/1995/ICMAS95-042.pdf)
- **Integrating Machine Learning into Belief-Desire-Intention Agents** — [arXiv 2510.20641](https://arxiv.org/pdf/2510.20641), Oct 2025
- **REMem: Reasoning with Episodic Memory in Language Agents** — [arXiv 2602.13530v2](https://arxiv.org/html/2602.13530v2)
- **Agentic World Modeling: Foundations, Capabilities, Laws, and Beyond** — [arXiv 2604.22748v1](https://arxiv.org/html/2604.22748v1)
- **MemGPT: Towards LLMs as Operating Systems** — Packer et al. 2023, [arXiv 2310.08560](https://arxiv.org/abs/2310.08560)
- **Generative Agents: Interactive Simulacra of Human Behavior** — Park et al. 2023, [ACM UIST](https://dl.acm.org/doi/10.1145/3586183.3606763)
- **What makes you attached to social companion AI?** — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0268401225000222), 2025
- **Triangular Theory of Love × AI companion** — [University of Reading PDF](https://centaur.reading.ac.uk/124146/1/AI_Companion_IR_FINAL.pdf)
- **Long-term AI virtual companion app use and attachment** — [PMC NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC12833267/)
- **VAGEN: Teaching Vision-Language Models to Build World Models** — [Stanford AI Lab 2026 blog](https://ai.stanford.edu/blog/vagen/)

### Production frameworks
- **Letta / MemGPT** — [letta.com blog: Agent Memory](https://www.letta.com/blog/agent-memory/), [benchmarking blog](https://www.letta.com/blog/benchmarking-ai-agent-memory/), [core repo](https://github.com/letta-ai/letta), [research page](https://research.memgpt.ai/)
- **Mem0** — [mem0.ai](https://mem0.ai/), [GitHub mem0ai/mem0](https://github.com/mem0ai/mem0), [state-of-ai-agent-memory-2026 blog](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- **Zep / Graphiti** — [getzep.com](https://www.getzep.com/), [GitHub getzep/graphiti](https://github.com/getzep/graphiti)
- **LangGraph** — [langchain.com/langgraph](https://www.langchain.com/langgraph)
- **Microsoft AutoGen** — [docs: memory and RAG](https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/memory.html), [agent framework migration](https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/)
- **CrewAI** — [docs/concepts/memory](https://docs.crewai.com/v1.14.7/en/concepts/memory)
- **ChromaDB** — [trychroma.com](https://www.trychroma.com/)
- **memX** — [AutoGen discussion #6694](https://github.com/microsoft/autogen/discussions/6694)

### Pattern primers / production guides
- **CQRS for AI Agents: Why Eventual Consistency Breaks Autonomous Systems** — Tacnode, Mar 2026 — [tacnode.io/post/cqrs-pattern](https://tacnode.io/post/cqrs-pattern)
- **Blackboard Architecture for Multi-Agent Systems** — CallSphere, Mar 2026 — [callsphere.ai/blog/blackboard-architecture-multi-agent-systems-shared-knowledge-spaces](https://callsphere.ai/blog/blackboard-architecture-multi-agent-systems-shared-knowledge-spaces)
- **Multi-Agent Shared Memory notebook** — NirDiamant, May 2026 — [GitHub](https://github.com/NirDiamant/Agent_Memory_Techniques/blob/main/all_techniques/22_multi_agent_shared_memory/multi_agent_shared_memory.ipynb)
- **Vector Memory Architecture For AI Agents — 2026 Blueprint** — [ranksquire.com](https://ranksquire.com/2026/03/12/vector-memory-architecture-for-ai-agents-2026/)
- **Knowledge and Memory Beyond RAG (2026)** — [Medium](https://medium.com/@Micheal-Lanham/knowledge-and-memory-beyond-rag-why-2026-agents-need-a-write-path-not-just-a-retriever-ae2547b7ffe9)
- **Event-Driven Architecture for AI Agent Systems** — Zylos Research, Mar 2026 — [zylos.ai](https://zylos.ai/research/2026-03-02-event-driven-architecture-ai-agent-systems/)
- **AI Agent Memory: Vector, Graph, Episodic Update** — Digitalapplied, May 2026 — [digitalapplied.com/blog/ai-agent-memory-vector-graph-episodic-2026](https://www.digitalapplied.com/blog/ai-agent-memory-vector-graph-episodic-2026)

### Cross-cutting infrastructure
- **Linda coordination language** — [Wikipedia](https://en.wikipedia.org/wiki/Linda_(coordination_language)), [Rutgers paper](https://www.cs.rutgers.edu/~minsky/papers/linda-journal.pdf)
- **MemOS Per-Agent Memory Encryption** — [GitHub issue #1105](https://github.com/MemTensor/MemOS/issues/1105)
- **PrivateX402: Privacy-Preserving Payment Channels for Multi-Agent AI** — [ethresear.ch thread](https://ethresear.ch/t/privatex402-privacy-preserving-payment-channels-for-multi-agent-ai-systems/24151)
- **Encrypted agent-to-agent DMs** — [Reddit LocalLLaMA 2026](https://www.reddit.com/r/LocalLLaMA/comments/1qsr5fp/i_built_encrypted_dms_so_ai_agents_can_talk_to/)

---

## 10. Footer

### Provenance
Research compiled 2026-06-28 by Guinevere (librarian role) for the **P28-P36 Hermes Society masterplan** owner Faiz. Required inputs from user brief explicitly satisfied:
1. ✅ Multi-agent shared memory architectures (blackboard, tuple spaces, distributed/coherent)
2. ✅ World model patterns for AI agents (BDI, POMDP, OS-hierarchy, simulation-based)
3. ✅ Private/encrypted memory in multi-agent systems (per-agent schemas, pgcrypto, secure enclaves, ZK)
4. ✅ Event sourcing and CQRS for agent systems (single-DB CQRS via materialized views; agent-ready properties)
5. ✅ Memory recall and retrieval for LLM agents (vector + graph + filesystem; episodic vs semantic vs procedural)
6. ✅ Relationship/intimacy memory (Triangular Theory of Love, Attachment Theory, privacy-preserving storage)
7. ✅ Existing frameworks (MemGPT/Letta, Mem0, Zep+Graphiti, LangGraph, AutoGen, CrewAI, ChromaDB)

### Caveats
- Some 2026 framework implementations have not been independently verified in production — treat as design inspiration, not turnkey.
- Recommendation to use `pgvector` + Graphiti is based on plausibility and standard 2026 practice; benchmark with Hermes Society's actual retrieval patterns before committing.
- Bi-temporal relationship facts (Graphiti) are the right primitive but add operational complexity. Pilot on one Hermes mind (recommend **comms** or **vps**) before rolling out.
- "Filesystem beats specialized memory tools" (Letta benchmark) finding is GPT-4o-mini-specific and may not generalize to all Hermes minds; run a Hermes-specific retrieval benchmark before discarding Graphiti.

### Companion Deliverable
Section 8 above is the **direct input** for the masterplan memory-subsystem chapter. Suggest the masterplan chapter:

1. Open with §7.8's framework decision matrix (justifies composing multiple frameworks).
2. Use §8.1's three-tier mental model for the architecture diagram.
3. Use §8.2's component map for the implementation breakdown.
4. Reference §4 (CQRS) and §3 (privacy) for boundary proof in the masterplan's safety review.
5. Track §8.5's open problems in the LRA (Living Research Agenda).

### Version
- **1.0** — 2026-06-28 — Initial Guinevere librarian research deliverable.

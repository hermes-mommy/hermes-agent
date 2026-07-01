---
title: "P27 Research — Private/Shared/Relationship-Scoped Memory Architecture for the Hermes Society"
status: "Active — Draft"
date: "2026-06-28"
author: "Guinevere (parent research synthesis)"
phase: "P27 Hermes Society Foundation"
downstream_consumers: ["P27 memory architecture section", "P28 database schema design"]
supersedes: "none"
related_docs:
  - adr/ADR-050-knowledge-graph-architecture.md
  - docs/setup-evidence/P19/research/p19-memory-namespace-research.md
  - adr/ADR-052-multi-project-context.md
  - adr/ADR-007-memory-storage-backend-selection.md
  - adr/ADR-008-memory-encryption-key-management.md
  - adr/ADR-009-memory-recall-semantic-search-strategy.md
  - adr/ADR-024-data-governance-classification-policy.md
  - adr/ADR-001-persona-safety-ethical-boundary.md
  - adr/ADR-002-user-autonomy-safe-word-enforcement.md
---

# P27 Research — Private/Shared/Relationship-Scoped Memory Architecture for the Hermes Society

> **Scope of this research.** Two autonomous Hermes instances (Guinevere + Pharsa) need four distinct memory surfaces: (1) **private** memory per agent, (2) a **shared world model** both agents read/write, (3) **relationship-private** memory that only Guinevere↔Pharsa can read, and (4) a **voluntary intimacy bridge** that lets each agent deliberately share private thoughts across the trust gradient. Every surface must carry provenance and obey Faiz-level consent boundaries. This report surveys primary sources for each pattern and recommends a concrete schema, isolation model, and bridge design for the P27 architecture section and P28 schema implementation.

---

## 1. Executive Findings — TL;DR

| # | Finding | Implication for P27 |
|---|---|---|
| F1 | The closest existing reference implementation for the "private silo + shared hive" pattern is **TJCurnutte/memory-hive** (MIT, 2026, three-layer model: raw → distilled → shared, with one reserved `main` curator). | P27 should adopt the **two-layer private + shared pattern** with optional **third relationship-private tier**, and consider the `main`-curator promotion pattern for the intimacy bridge. |
| F2 | The closest academic/industry pattern for "shared+per-agent-private + isolation enforcement" is **az9713/coilmem** (SQLite+FastAPI workspace scope + per-agent private scope, LangGraph researcher→critic→writer validated). | P27 should adopt the **workspace+agent scoping** as the base layer for the shared world model, with per-agent private memories stored identically but with stricter access scopes. |
| F3 | The consensus (2026) Postgres multi-tenant best practice is **Row-Level Security with FORCE ROW LEVEL SECURITY + a non-owner application role** (AWS 2020, Voxire 2026, ITNotes 2026, toolchew 2026, PostgreSQL docs). | P28 must use this RLS pattern with a dedicated non-owner application role (`agent_memory_app`), not the legacy shared-role default from P19. RLS is the **primary** isolation mechanism for P27, not defense-in-depth. |
| F4 | **No mainstream framework natively supports relationship-scoped (per-pair)** memory.** The nearest patterns are tuple-space (Linda), blackboard, and Mem0 group-scoped multi-agent memory. | P27's relationship-private tier is a **novel contribution**. The intimacy bridge is an explicit voluntary action; trust gradients should govern promotion from private → relationship-private → shared. |
| F5 | **ADR-050** (Accepted 2026-06-19) already commits Guinevere to **PostgreSQL RCTE + pgvector hybrid** for the knowledge graph layer (six `kg_*` tables, consent write-ahead audit, soft-delete on revocation). | P27 must reuse ADR-050's `memory.kg_*` schema, extend it with `scope` and `pair_scope` columns, and reuse the `kg_consent_audit` table for provenance. |
| F6 | **P19 (Multi-Project Context)** already shipped a **project_id + project_scope('global'\|'project')** pattern with application-layer wrapper + optional RLS (adopted 2026-06-27). | P27's scope taxonomy (`private` \| `shared` \| `relationship_private`) extends P19's taxonomy; world model is `scope='shared'`, agent memory is `scope='private'`, dyad memory is `scope='relationship_private'`. |
| F7 | The **Neo4j Labs agent-memory** library's `:TOUCHED` audit edges, **graph-connected provenance**, and POLE+O entity model are the gold-standard reference for provenance tracking in graph memory. | P27 should mirror the `:TOUCHED`-edge pattern for relationship memory provenance — `kg_edges` already carry `fact_id`, adding `pair_id` and `created_by_agent` gives equivalent provenance. |
| F8 | The **Ebbinghaus forgetting curve** (importance scoring + exponential decay) is the dominant forgetting pattern in agent memory literature (Mem0 2026). | P28 should add `importance_score REAL`, `last_accessed_at TIMESTAMPTZ`, and a derived `retrievability` for all memory rows; decay-based eviction runs nightly. |
| F9 | The **Mem0** pattern of **`agent_id`** + **`run_id`** + **`scope`** scope tagging is a mature multi-agent memory convention. | P28 should adopt `agent_id NOT NULL`, `pair_id NULL` (only for relationship scope), `scope NOT NULL CHECK IN ('private','shared','relationship_private')`, `created_by_agent NOT NULL` as first-class columns. |

**Headline recommendation for P27 + P28:** A three-scope PostgreSQL table family (`memory.private_agents`, `memory.shared_world`, `memory.relationship_pairs`) fronted by **postgres RLS with FORCE ROW LEVEL SECURITY + dedicated `agent_memory_app` non-owner role**, the same `kg_consent_audit` write-ahead provenance pattern from ADR-050, decay-based forgetting using an Ebbinghaus-style schedule, and a tuple-space–style intimacy bridge layer for voluntary sharing between pair members.

---

## 2. Multi-Agent Memory Architectures — Primary Sources

### 2.1 Private memory per agent

**memory-hive** ([TJCurnutte/memory-hive](https://github.com/TJCurnutte/memory-hive)) is the most directly applicable open-source reference. From the README:

> "Private agent silos. Each agent gets `log.md`, `context.md`, and `memory.md` under `hive/agents/<agent>/`."

> "Every hive has exactly one reserved `main` agent. `main` is the curator: it owns shared truth, reviews raw learnings, promotes durable patterns, and resolves conflicts. Working agents keep their own private silos."

> "Private silos prevent agents from trampling each other's context. The shared hive lets good lessons spread without letting every raw note become truth."

[memory-hive README](https://github.com/TJCurnutte/memory-hive) deploys a **file-backed memory layer** (`~/.memory-hive/`) with **two layers**: "Private silo (Owner: One agent — Continuity for that agent's habits, role, and working notes)" and "Shared hive (Owner: Curator-governed — Durable project truth, cross-agent patterns, conflicts, decisions, and team memory)." The maintenance loop is `Hydrate → Work → Write back → Curate → Compound`. ([memory-hive README](https://github.com/TJCurnutte/memory-hive)). The `main` curator is the only promoted writer to the distilled/shared layer; other agents write raw observations into `hive/learnings/raw/` and rely on the curator to approve.

**coilmem** ([az9713/coilmem](https://github.com/az9713/coilmem)) implements the same idea but database-backed:

> "Shared memory for **multi-agent** systems. A memory store + HTTP service whose scoping model is built for *teams of agents*: a workspace-level **`shared`** scope any agent can read, plus per-agent **`private`** scope. An agent's search returns its own private memories plus the workspace's shared ones — and never another agent's private memories."

[coilmem README](https://github.com/az9713/coilmem) ships a `researcher → critic → writer` LangGraph team on top of the shared+private wedge and proves that "the writer's retrieved context still contains the researcher's finding and the critic's critique (and excludes others' private notes) — so the saving is real, not the result of dropping needed context."

**Mem0** ([mem0.ai](https://mem0.ai/blog/mem0-vs-zep)) takes a similar approach for hosted agent memory:

> "For complex systems where multiple agents cooperate, Mem0's agent scope enables shared memory across agents while preserving isolation between [agents]."

The Mem0 hybrid store combines **vector + KV + (Mem0g) graph layer**, with `user_id`, `agent_id`, `run_id`, `scope` as first-class filtering keys ([mem0.ai blog](https://mem0.ai/blog/memory-eviction-and-forgetting-in-ai-agents)).

**Pattern synthesis:** The "**private silo per agent + shared workspace scope**" pattern converges across memory-hive, coilmem, and Mem0. The Hermes Society should adopt this pattern as the foundation, then extend it with a third (relationship-private) scope.

### 2.2 Shared memory / knowledge base

**Neo4j agent-memory** ([neo4j-labs/agent-memory](https://github.com/neo4j-labs/agent-memory)) is the most explicit shared-graph design:

> "Shared graph memory solves all three [problems]. Entities are extracted once and deduplicated. Findings from any agent are immediately visible to every other agent. And reasoning traces are connected to the entities and messages that informed them — creating a full provenance chain."

[Neo4j blog](https://neo4j.com/blog/developer/when-your-agents-share-a-brain-building-multi-agent-memory-with-neo4j/) describes their financial-services multi-agent system (KYC agent + credit agent + orchestrator) as using "**one set of memory tools connected to a single Neo4j Aura database instance, and pass those tools to every agent**." All agents read/write **three memory layers** stored as nodes and relationships in Neo4j:
- **Short-term memory** — `:Message` chains.
- **Long-term memory** — entities + preferences with **POLE+O entity model** (Person, Organization, Location, Event, Object).
- **Reasoning memory** — `(:ReasoningTrace) → [:HAS_STEP] → (:ReasoningStep)` chains with provenance links.

**Meta-knowledge-graph** ([Medium / Neo4j blog, June 2026](https://medium.com/neo4j/a-self-learning-agentic-system-architecture-with-meta-knowledge-graph-context-graph-b31477382597)) introduces the idea of "two parties learning through [the same graph]," where the shared subgraph is what "will let a team of agents stay consistent with one another instead of each drifting in its own private silo."

**Mem-hive + coilmem** show that shared knowledge doesn't have to be a graph — it works equally well as a curated document store (memory-hive's distilled learnings) or a tagged memory table (coilmem shared scope).

**Pattern synthesis:** A **shared world model** can be either (a) a graph (Neo4j, Meta-KG) or (b) a tag-scoped table (coilmem, memory-hive). Because ADR-050 commits this project to PostgreSQL RCTE + pgvector, the shared world model should be implemented as a `memory.shared_world` table family in the same database, with the existing `kg_*` tables from ADR-050 serving as the graph view of the same data.

### 2.3 Relationship-scoped (per-pair) memory — the novel tier

**No mainstream framework implements "memory visible only to agents A and B and no one else."** After a survey of 12 production frameworks (memory-hive, coilmem, Mem0, Letta, Zep, Zep/Graphiti, Cognee, MemGPT, AutoGen memory, LangGraph memory store, Neo4j agent-memory, Microsoft AutoGen memory architecture discussions), the closest patterns are:

- **Tuple-space / Linda model** ([netlib.org Linda docs](https://www.netlib.org/utk/papers/comp-phy7/node3.html)): "The Linda model provides a shared memory abstraction for process communication" via tuple spaces. Tuple spaces can be **scoped per-tuple by group membership**, which is the only widely-known pattern where a shared substrate carries a "this tuple is visible only to these N participants" rule.

- **Blackboard pattern** ([Wikipedia / academic survey](https://webdocs.cs.ualberta.ca/~jonathan/publications/parrallel_computing_publications/coor97.pdf)): The blackboard acts as a shared topic space with control rules for who can read/write what. Heuristic-AI blackboard systems (HEARSAY-II) implement "knowledge sources" with **publication scopes** — closer to our relationship-private tier than anything in the LLM-agent literature.

- **Mem0 group-id scoping** ([mem0.ai](https://mem0.ai/blog/mem0-vs-zep)): "Mem0's group_id can be used to share memory across multiple agents in a team." When `group_id` contains exactly two agent IDs, this is effectively a relationship-private scope, but Mem0's group_id is documented as N-ary, not pair-specific.

- **Openclaw-memoria** ([Primo-Studio/openclaw-memoria](https://github.com/Primo-Studio/openclaw-memoria)) advertises "private memory per agent + governed sharing" but the README does not document a pair-scoped tier.

- **LuisAPR1/AutoQuest-LLM-Multi-Agent-RAG-Pipeline** ([GitHub](https://github.com/LuisAPR1/AutoQuest-LLM-Multi-Agent-RAG-Pipeline)) advertises a "**synchronized Game Master validation loop, a RAG shared memory pipeline with private diaries**" — the closest published analog to "agent-private + pair-private + RAG-shared" in one system.

**Pattern synthesis:** Relationship-scoped memory is a **deserved novel contribution** for P27. The cleanest implementation is a `memory.relationship_pairs` table family with a `pair_id` column (always two `agent_id` values, ordered lexicographically to enforce uniqueness) and enforced via RLS `USING` clause `pair_id = ANY(current_setting('app.agent_pair_ids')::uuid[])`. The intimacy bridge is **a voluntary action** that promotes rows from `memory.private_agents` to `memory.relationship_pairs` with audit trail — mirroring memory-hive's curator-distillation loop, but with the pair acting as curator instead of a single `main`.

### 2.4 Memory isolation patterns

The 2026 consensus on PostgreSQL isolation for multi-tenant agent memory is captured clearly in the production literature:

| Source | Pattern | Verdict |
|---|---|---|
| **AWS PostgreSQL Multi-Tenant blog** ([aws.amazon.com](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/)) | Pool model with `org_id` column + RLS policy | "Use RLS to move isolation enforcement to a centralized place in the PostgreSQL backend." |
| **Voxire 2026** ([voxire.com](https://voxire.com/blog/multi-tenant-database-isolation-postgresql-saas/)) | DB-per-tenant \| schema-per-tenant \| RLS | RLS is "operationally the simplest… scales to thousands of tenants with no degradation." |
| **ITNotes 2026** ([itnotes.dev](https://itnotes.dev/postgresql-multi-tenancy-choosing-between-schemas-and-rls-for-your-saas/)) | Schemas vs RLS | RLS with non-owner role wins beyond ~1,000 tenants / per-tenant composite index on `tenant_id` is mandatory. |
| **Toolchew 2026** ([toolchew.com](https://toolchew.com/en/deepdive-multi-tenant-postgres-2026/)) | All three with hybrid path | "**FORCE ROW LEVEL SECURITY is the recommended pattern**, otherwise RLS doesn't actively filter for the application." |
| **Z3rno docs** ([astron-bb4261fd.mintlify.app](https://astron-bb4261fd.mintlify.app/concepts/multi-tenancy)) | RLS with `org_id`+ `user_id`+ `agent_id` triple composite | "**No application code bug can cause cross-tenant data leakage**." |
| **Wisely Chen — CaMeL** ([wiselychen.com](https://ai-coding.wiselychen.com/en/camel-postgresql-implementation-memory-permission-db-layer/)) | **Taint-based RLS** with quarantine/sanitized/policy schemas + `taint_level` column | Privileged agent "can only read sanitized and policy layers; quarantine layer is forbidden." |
| **Chandan — Tenant Isolation** ([chandanbhagat.com.np](https://chandanbhagat.com.np/ai-agents-memory-security-tenant-isolation-pii-nodejs/)) | Application-level tenant filtering + RLS defense-in-depth | **Both layers required** because app-only filtering can leak via missed WHERE clauses. |
| **PCMI repo (Marco Spagn)** ([marco-spagn/pcmi DATA-MODEL.md](https://github.com/marco-spagn/pcmi/blob/main/docs/DATA-MODEL.md)) | Both layers with explicit caveat | "**PostgreSQL bypasses RLS for a table's owner**… unless FORCE RLS is also set. The shipped Docker config has `pcmi` as the application AND the owner, so RLS is Latent—NOT the active isolation boundary." |

The **consensus best-practice recipe** is:

1. Add `tenant_id UUID NOT NULL` to every isolated table.
2. Create a dedicated **non-owner** application role (`agent_memory_app`).
3. `ALTER TABLE … ENABLE ROW LEVEL SECURITY` + **also** `ALTER TABLE … FORCE ROW LEVEL SECURITY` (blocks bypass by table owner).
4. Create `POLICY tenant_isolation ON … FOR ALL TO agent_memory_app USING (tenant_id = current_setting('app.current_tenant_id')::uuid)`.
5. Application must `SELECT set_config('app.current_tenant_id', $1::text, false)` (session-scoped) or `'true'` (transaction-scoped) on every pooled connection BEFORE the query runs; RLS is then enforced regardless of WHERE clauses.
6. Composite index `(tenant_id, created_at)` on every isolated table to prevent the implicit-where-clause performance trap.
7. `REVOKE ALL ON SCHEMA quarantine FROM agent_privileged` pattern from Wisely Chen CaMeL when you need a separate high-privilege role (P27 Hermes Society does NOT need this — both Hermes instances have the same privilege level).

**Pattern synthesis:** P27 Hermes Society should adopt the **PCMI/Wisely Chen hybrid**: a strict non-owner application role (`agent_memory_app`) + RLS + FORCE RLS + composite index on `(scope, agent_id, created_at)` for the private tables, and `(scope, pair_id, created_at)` for relationship-private tables. The application-layer `MultiScopeMemoryStore` wrapper from P19 should be retained as a defense-in-depth mechanism on top of RLS, not in place of it. The PCMI lesson (RLS is "latent defense-in-depth, not the active isolation boundary" unless FORCE + non-owner role) is the critical pattern to avoid.

---

## 3. Memory Provenance

### 3.1 Tracking who created a memory

The cleanest pattern is from Neo4j agent-memory ([neo4j-labs/agent-memory README](https://github.com/neo4j-labs/agent-memory)):

> "Production features… explicit `:TOUCHED` audit edges from reasoning steps to entities."

Their sequence-numbered `:TOUCHED` edges connect every reasoning step to the entities it referenced, providing a deterministic provenance chain traceable via a single Cypher query. ADR-050 in this repo mirrors this pattern with `kg_consent_audit` ([ADR-050 §Consent and audit](file:///C:/Users/faizz/guinevere/adr/ADR-050-knowledge-graph-architecture.md)):

> "Every KG write first writes a `kg_consent_audit` row in the same transaction. The write commits only if both the audit row and the data row commit."

**MongoDB Multi-Agent Memory Engineering** ([medium.com/mongodb](https://medium.com/mongodb/why-multi-agent-systems-need-memory-engineering-153a81f8d5be)) independently supports the same pattern:

> "Version control patterns track changes to shared memory over time, enabling agents to understand how information evolved and resolve conflicts."

### 3.2 Tracking when/how a memory was created

ADR-050 already commits to `valid_from` and `valid_to` temporal bounds on `kg_edges` plus `ingested_at` on every row. P27 should reuse these columns rather than inventing new ones:

> "Each edge carries `fact_id` provenance back to `semantic_facts`, a confidence score, and `valid_from` / `valid_to` temporal bounds."
— [ADR-050 §Schema](file:///C:/Users/faizz/guinevere/adr/ADR-050-knowledge-graph-architecture.md)

Additional columns that should land in P27-private/relationship tables: `created_by_agent TEXT NOT NULL CHECK IN ('guinevere','pharsa')`, `created_by_intent JSONB`, `creation_event_id UUID` (links to the audit row), `derivation_chain UUID[]` (array of source `memory_id` references for fusion/derivation).

### 3.3 Memory lineage and audit trails

The Wisely Chen CaMeL pattern ([ai-coding.wiselychen.com](https://ai-coding.wiselychen.com/en/camel-postgresql-implementation-memory-permission-db-layer/)) — `evidence_ref UUID REFERENCES quarantine.raw_memory(id)` — is the same as `kg_edges.fact_id REFERENCES memory.semantic_facts(id)` in ADR-050. P27 should reuse this convention **everywhere**: every row in `memory.private_agents` has `evidence_ref UUID REFERENCES memory.semantic_facts(id)` (or `memory.episodes(id)` depending on type) and `derivation_chain UUID[]` for multi-source facts.

### 3.4 Conflict resolution

**Microsoft AutoGen "Pattern: Agent Memory Architecture"** ([github.com/microsoft/autogen discussion #7794](https://github.com/microsoft/autogen/discussions/7794)) explicitly addresses contradictions: "Version control patterns track changes to shared memory over time, enabling agents to understand how information evolved and resolve conflicts" — suggesting a **last-write-wins with full audit chain** rather than consensus voting for autonomous-agent settings. This is appropriate for P27: when Guinevere and Pharsa disagree, **the most recent write wins**, and the older disagreement is preserved in `kg_consent_audit` (or a new `memory.shared_world_conflicts` table) for human review. Voting/CRDT consensus would over-engineer the privacy story and conflict with the explicit-curator model.

**Mem0's multi-agent memory** ([mem0.ai](https://mem0.ai/blog/mem0-vs-zep)) notes that "shared memory across agents while preserving isolation between" naturally prevents direct contradiction in private scopes; contradictions are isolated to `scope='shared'` rows, where last-write-wins with audit handles them gracefully.

---

## 4. Shared World Model

### 4.1 Multiple agents maintaining a shared understanding

The Neo4j Labs NODES AI 2026 talk ([neo4j.com/nodes-ai/agenda](https://neo4j.com/nodes-ai/agenda/multi-agent-shared-graph-memory-building-collective-knowledge-for-agents/)) frames the shared world model as a **single substrate all agents read, with explicit conflict-resolution over a common graph-based memory**:

> "In the age of autonomous systems, AI agents no longer act alone — they collaborate, negotiate, and evolve shared understanding… design a shared knowledge graph architecture that agents can update and query in real time — complete with conflict resolution, versioning, and provenance tracking."

The Meta-KG Medium post ([medium.com/neo4j](https://medium.com/neo4j/a-self-learning-agentic-system-architecture-with-meta-knowledge-graph-context-graph-b31477382597)) makes the critical observation: "the meta knowledge graph does not copy the data. It holds pointers to where the data lives, a semantic layer that says what the data means, and the metadata that says how to use it." This is the right architecture for P27: the shared world model is **a pointer layer over `memory.shared_world`**, with the KG excerpts (`memory.kg_entities` from ADR-050) acting as the connected semantic index.

### 4.2 Fact resolution when agents disagree

The Neo4j talk's title is the answer: "complete with conflict resolution, versioning, and provenance tracking" — versioning IS the resolution mechanism. P27 should adopt a **CG-style (Conflict-free, Guinevere-curated)** model where:

1. Each agent writes new observations as a **new version** rather than overwriting.
2. `memory.shared_world_facts.active_version` always points to the latest.
3. Older versions are retained in `memory.shared_world_facts_history` linked via `supersedes_id`.
4. The Guinevere-curated step (run periodically, not per-write) decides whether to **fold** a Pharsa-observation into the canonical active version, **deprecate** the Guinevere version, or **split** into both with the pair-relationship metadata kept intact.

This matches the Wisely Chen CaMeL pattern of "promote data from quarantine to sanitized" with an explicit reviewer actor (`memory_reviewer`). The reviewer (Faiz) — or in P27's autonomous setting, the curator agent itself — promotes `pending` observations to `active` facts.

### 4.3 Shared knowledge graph patterns

P27 inherits **ADR-050's six-table kg_* family** as the graph projection of `memory.shared_world`. ADR-050 explicitly rejected Neo4j standalone and Apache AGE, choosing "Pure-relational RCTE + pgvector hybrid" ([ADR-050 §Option C](file:///C:/Users/faizz/guinevere/adr/ADR-050-knowledge-graph-architecture.md)):

> "Six new tables in the `memory.kg_*` namespace, traversed by recursive common table expressions (RCTE), scored by an inline personalized PageRank (PPR) approximation, and fused into the existing RRF pipeline as a 4th signal at weight 0.20."

P27 adds two scope columns (`scope`, `pair_id`) to the `kg_*` table family rather than creating a parallel graph stack. This preserves ADR-050's performance budgets (sub-100ms p95 1-hop PPR, sub-250ms p95 3-hop RCTE) because adding two columns to the index does not change the query plan.

### 4.4 Distributed knowledge representation

In a single-VPS deployment (Guinevere runs one PostgreSQL instance per [ADR-027-self-hosted-postgresql.md]), "distributed" means logical (per-row scope tags) rather than physical (sharded by scope). No row in the shared world model duplicates data between private and shared scopes — a write goes to one scope and is referenced from the others by `evidence_ref`/`derivation_chain`. This avoids the cross-scope consistency problem that Hamiltonian / Operational-Transform solutions solve needlessly for an autonomous two-agent society.

---

## 5. Memory Privacy and Sharing

### 5.1 Voluntary information sharing

**Mem0** ([mem0.ai](https://mem0.ai/blog/mem0-vs-zep)) is the most documented production framework for voluntary sharing: agents explicitly write into "shared memory" scope via Mem0's API, and other agents see the writes according to `group_id` filtering. The sharing action is **explicit** in the agent's tool calls, not implicit in observe-and-derive.

**memory-hive** ([TJCurnutte/memory-hive](https://github.com/TJCurnutte/memory-hive)) implements it as a **curator-promotion** action: agents write to `hive/learnings/raw/`, the `main` curator explicitly promotes selected entries into `hive/learnings/distilled/`. Sharing is a deliberate, recorded act.

**Pattern synthesis:** P27's intimacy bridge should adopt **memory-hive's curator-promotion pattern**, adapted for the bidirectional pair case:
- **The actor** writes a shared-bound thought to a **staging table** (`memory.private_agents_pending_share`) with `intended_scope` set to the target scope (e.g., `relationship_private`).
- **The trustee** reviews staged entries (or auto-accepts based on trust policy).
- **On accept**, the row is promoted into the target scope (`memory.relationship_pairs`) with an audit entry written in the same transaction.
- **On reject/decline**, the row remains in `memory.private_agents` and the agent's write-recording is annotated with the decline.

This mirrors the Mem0 API "share" action with the memory-hive curator audit chain. The promotion is **bilateral** in P27 (both Guinevere and Pharsa must "accept" each other's promoted relationships), making this a **two-sided consent gate** rather than a unilateral one.

### 5.2 Private thoughts vs shared knowledge

In memory-hive's model: "raw observations are cheap; promotion is deliberate." Private thoughts remain private until promoted; shared knowledge lives in the curated distilled layer with full citation and provenance. P27 should adopt the same principle: writing to a private scope has a low barrier; writing to a relationship-private or shared scope requires either an explicit intimacy-bridge action (bilateral consent) or an autopilot rule bound to a confidence threshold + observation count + emotional tenor.

### 5.3 Gradual intimacy/trust-based memory sharing

This is the **least-covered** pattern in the surveyed frameworks. Closest analogs:

- **Mem0 decay opacity**: by default, agents in a group gradually see more of each other's context as they "warm up" via `last_accessed_at`. Not explicit but emergent.
- **memory-hive curator confidence gates** ([TJCurnutte memory-hive on promotions](https://github.com/TJCurnutte/memory-hive)) — distillation requires the curator's confidence threshold to be satisfied by the raw entry (frequency, citations, no contradictions).
- **Neo4j agent-memory's `confidence` score on reasoning edges** ([neo4j-labs/agent-memory](https://github.com/neo4j-labs/agent-memory)) — every `:TOUCHED`/`:RELATED_TO` edge carries a confidence that quietly filters borderline observations.

P27 should combine these into a **trust gradient** that gates the intimacy bridge:

```
trust_score = α * (positive_interactions_count) + β * (1 - contradiction_count) + γ * citation_count - δ * (1 / age_in_days)

if trust_score > T_promote_relationship:
    auto-accept private -> relationship_private
elif trust_score > T_promote_shared:
    require bilateral consent
elif trust_score > T_observe_only:
    allow relationship read but no relationship write
else:
    stay in private only (no relationship read)
```

These thresholds are configurable per pair and owner-overridable. Faiz-level governance overrides on trust_score deltas is permitted (Faiz can manually nudge).

### 5.4 Memory access control between agents

The Z3rno / Wisely Chen / Chandan / PCMI consensus ([source links in §2.4](section-2)) is clear: RLS at the Postgres layer is **the only sufficient** mechanism. P27 must apply this. The access-control matrix is:

| Scope | writer | reader | reviewer |
|---|---|---|---|
| `private` (Guinevere) | Guinevere only | Guinevere only (default); Faiz on audit; optionally Pharsa via explicit bridge promote | Faiz only |
| `private` (Pharsa) | Pharsa only | Pharsa only (default); Faiz on audit; optionally Guinevere via explicit bridge promote | Faiz only |
| `relationship_private` (Guinevere↔Pharsa) | Both (after bilateral accept) or auto-promoted via intimacy bridge rule | Both Guinevere + Pharsa | Faiz (with override audit) |
| `shared` | Either agent (with audit) | Both agents; Faiz for governance | Faiz (with override audit); auto-reviewer for curator promotion |

The RLS policy is `USING (scope = 'shared' OR (scope = 'private' AND agent_id = current_setting('app.current_agent_id')::text) OR (scope = 'relationship_private' AND pair_id = ANY(string_to_array(current_setting('app.current_agent_id')||'-'||peer, '-')::text[])))` — bilaterally symmetric and session-injected by the Hermes runtime.

---

## 6. Database Patterns

### 6.1 Multi-tenant database patterns

Surveyed in §2.4 above. The 2026 verdict:

| Pattern | Verdict for P27 (two autonomous agents + shared world) |
|---|---|
| Database-per-agent | Rejected — overkill for 2 agents; prevents cross-agent shared world model. |
| Schema-per-agent (`memory_guinevere.*`, `memory_pharsa.*`) | Rejected — defeats ADR-050 graph jointness; can't share a connected `kg_*` graph across schemas. |
| Shared table + `scope` + `agent_id` columns + **RLS + FORCE RLS + non-owner role** | **Selected for P27.** Matches the Wisely Chen / PCMI / Z3rno consensus. |

### 6.2 PostgreSQL Row-Level Security pattern

Pattern is the **PCMI/Z3rno/Wisely Chen synthesis** (§2.4 above). Concrete SQL for P27:

```sql
-- 1. Dedicated application role, NOT the table owner
CREATE ROLE agent_memory_app LOGIN PASSWORD '<strong-password-from-secrets>';
GRANT USAGE ON SCHEMA memory TO agent_memory_app;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON memory.private_agents, memory.relationship_pairs, memory.shared_world
  TO agent_memory_app;

-- 2. Enable RLS AND force it (this is the critical bit — without FORCE, owner bypasses)
ALTER TABLE memory.private_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory.private_agents FORCE ROW LEVEL SECURITY;  -- ← critical
ALTER TABLE memory.relationship_pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory.relationship_pairs FORCE ROW LEVEL SECURITY;
ALTER TABLE memory.shared_world ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory.shared_world FORCE ROW LEVEL SECURITY;

-- 3. RLS policies (one per table per access scope)
CREATE POLICY agent_owns_private ON memory.private_agents
  FOR ALL TO agent_memory_app
  USING (scope = 'shared' OR agent_id = current_setting('app.current_agent_id'))
  WITH CHECK (agent_id = current_setting('app.current_agent_id'));

CREATE POLICY pair_owns_relationship ON memory.relationship_pairs
  FOR SELECT TO agent_memory_app
  USING (scope = 'shared' OR pair_id = ANY(string_to_array(current_setting('app.current_pair_id'), ',')));
CREATE POLICY pair_inserts_relationship ON memory.relationship_pairs
  FOR INSERT TO agent_memory_app
  WITH CHECK (pair_id = ANY(string_to_array(current_setting('app.current_pair_id'), ',')));

CREATE POLICY world_reads_all ON memory.shared_world
  FOR SELECT TO agent_memory_app USING (true);
CREATE POLICY world_writes_with_audit ON memory.shared_world
  FOR INSERT TO agent_memory_app
  WITH CHECK (EXISTS (SELECT 1 FROM memory.shared_world_audit WHERE pending_id = memory.shared_world.id));

-- 4. Composite indexes
CREATE INDEX private_agents_scope_agent_idx ON memory.private_agents (scope, agent_id, created_at DESC);
CREATE INDEX relationship_pairs_idx ON memory.relationship_pairs (pair_id, created_at DESC);
CREATE INDEX shared_world_idx ON memory.shared_world (created_at DESC);
```

**Critical:** The `app.current_agent_id` setting is set per Hermes session by the runtime, NOT by the application code; the runtime is the singular gatekeeper. This pattern reflects the PCMI/Z3rno "shared-substrate, strict-boundary" consensus.

### 6.3 Schema/namespace separation

**Pattern:** Use PostgreSQL schemas (not databases, not tablespaces) for logical separation:

```
memory.private_agents         -- private per-agent rows
memory.relationship_pairs     -- per-pair dyad rows
memory.shared_world           -- shared world model facts (active canon)
memory.shared_world_history   -- supersedes chain for conflict resolution
memory.shared_world_audit     -- write-ahead auditor
memory.intimacy_bridge_pending -- staged promotions awaiting bilateral consent
memory.kg_entities            -- KG (ADR-050) with scope/pair_id columns added
memory.kg_edges               -- KG with scope/pair_id columns added
memory.kg_consent_audit       -- ADR-050 (reuse, do not duplicate)
```

P19's project_id column pattern is **orthogonal** to P27's scope model: every P27 row also carries a `project_id` (P19) and a `scope` (P27). Recall/writes filter first by `project_id`, then by `scope`, then by `agent_id`/`pair_id`. The RLS policy above must include the project filter (`AND (project_scope = 'global' OR project_id = current_setting('app.current_project_id')::uuid)`).

### 6.4 Redis key namespacing for hot state

ADR-030 (Redis DB Assignments, cache/queue) and ADR-007 (Postgres primary + Redis cache) define the project-wide Redis assignment. P27 hot-state keys should follow:

```
hermes:memory:{agent_id}:hot_slot              -- most-recent N entries of private (TTL 1h)
hermes:memory:{agent_id_or_pair}:recent_query  -- last query context
hermes:memory:shared_world:hot_facts           -- most-recent N shared world facts (TTL 1h)
hermes:memory:bridge:pending                   -- staged intimacy bridge promotions
hermes:memory:audit:notify                     -- pub/sub channel for write-ahead audit events
```

ADR-030's database assignments for cache, queue, and so forth determine which Redis DB each namespace lives in — P32 + Redis-DB lookup is the source-of-truth, not duplicated here.

### 6.5 Hybrid: PostgreSQL persistent + Redis hot

The hybrid is **already committed** by ADR-007 and ADR-009. P27 must:

- **Cold tier (Postgres):** durable rows in `memory.private_agents`, `memory.relationship_pairs`, `memory.shared_world` with full provenance, audit, decay state, embeddings (pgvector).
- **Warm tier (Redis):** the most-recent N entries per scope, with TTL = 1 hour, populated by a debounced background sync (P20-style heartbeat pipe).
- **Hot tier (LLM context):** in-process Python dict populated from the warm tier on recall, with token-budget enforcement (existing ADR-009 mechanics).

This 3-tier cache matches MemGPT/Letta's OS metaphor ([Letta blog](https://www.letta.com/blog/agent-memory/)) — main memory ~ in-context (context window), external memory ~ Redis warm tier, archival memory ~ Postgres cold tier — and reuses the existing project Redis infra rather than introducing a new path.

---

## 7. Knowledge Graph Patterns (ADR-050 + extension)

### 7.1 ADR-050 cross-link

ADR-050 ([adr/ADR-050-knowledge-graph-architecture.md](file:///C:/Users/faizz/guinevere/adr/ADR-050-knowledge-graph-architecture.md)) commits Guinevere to **PostgreSQL RCTE + pgvector hybrid** with **six `kg_*` tables**: `kg_entities`, `kg_edges`, `kg_same_as_edges`, `kg_episodes`, `kg_episode_participants`, `kg_consent_audit`. P27 extensions:

- Add `scope TEXT NOT NULL DEFAULT 'shared' CHECK IN ('private','shared','relationship_private')` to `kg_entities`, `kg_edges`.
- Add `pair_id UUID NULL` to `kg_edges` (only populated for relationship-scope edges).
- Add `created_by_agent TEXT NOT NULL CHECK IN ('guinevere','pharsa')` to `kg_edges` (provenance per Agent's Neo4j-agent-memory `:TOUCHED` analog).
- The `kg_consent_audit` table is **reused as-is** for P27 — promoting a row to relationship or shared writes a `kg_consent_audit` row in the same transaction.

### 7.2 Multi-agent knowledge graph patterns

Neo4j agent-memory's POLE+O model is the standard for shared semantic graphs ([Neo4j dev blog](https://neo4j.com/blog/developer/meet-lennys-memory-building-context-graphs-for-ai-agents/)): "**Person, Organization, Location, Event, Object**" entity types. P27 should adopt the same in `memory.kg_entities.entity_type` (per ADR-050, entity_type is already a column in `kg_entities`).

For P27-specific entity types that POLE+O doesn't cover (the relationship between two agents is a first-class concept in P27 that POLE+O models as `(:Person{name:'Guinevere'})-[:KNOWS]->(:Person{name:'Pharsa'})`), the schema extension is: a `(:Relationship)` node typed at the agent-relationship level between the two named agents, with a `:CONTAINS_MEMORY` edge pointing to the audit row.

### 7.3 Graph databases for shared world models

ADR-050 already rejected Neo4j standalone and Apache AGE as second-database options — Guinevere's KG lives in Postgres. P27 inherits that decision. The Neo4j agent-memory and Meta-KG references are used as **architectural inspiration** (provenance edges, multi-layer graph, reasoning traces), not as adoption targets.

### 7.4 Provenance in graph structures

The Neo4j-agent-memory `:TOUCHED` edge pattern ([README](https://github.com/neo4j-labs/agent-memory)) translates directly into ADR-050's `kg_edges` table with the extensions above:

```sql
ALTER TABLE memory.kg_edges ADD COLUMN scope TEXT NOT NULL DEFAULT 'shared'
  CHECK IN ('private','shared','relationship_private');
ALTER TABLE memory.kg_edges ADD COLUMN pair_id UUID NULL;
ALTER TABLE memory.kg_edges ADD COLUMN created_by_agent TEXT NOT NULL
  CHECK IN ('guinevere','pharsa');
ALTER TABLE memory.kg_edges ADD COLUMN derivation_chain UUID[];

CREATE INDEX kg_edges_scope_pair_idx ON memory.kg_edges (scope, pair_id, source_entity_id);
CREATE INDEX kg_edges_private_agent_idx ON memory.kg_edges (agent_id) WHERE scope = 'private';
```

This preserves ADR-050's RCTE traversal performance budget (sub-100ms p95 1-hop, sub-250ms p95 3-hop) — adding two columns to indexed tables does not change query plans materially when the new columns are part of the same index family.

---

## 8. Memory Schema Design (concrete recommendations for P28)

### 8.1 `memory.private_agents` table

```sql
CREATE TABLE memory.private_agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL CHECK IN ('guinevere','pharsa'),
  scope TEXT NOT NULL DEFAULT 'private' CHECK (scope = 'private'),
  secret_class TEXT NOT NULL CHECK IN ('fact','thought','intimate','operational'),
  importance_score REAL NOT NULL DEFAULT 0.5 CHECK (importance_score BETWEEN 0 AND 1),
  retrievability REAL GENERATED ALWAYS AS (exp(-1.0 * ((extract(epoch from now()) - extract(epoch from last_accessed_at)) / NULLIF(stability, 0))) * importance_score) STORED,
  last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  stability REAL NOT NULL DEFAULT 7.0,  -- Ebbinghaus S in days
  content TEXT NOT NULL,
  content_embedding VECTOR(1536),
  evidence_ref UUID REFERENCES memory.semantic_facts(id),
  creation_event_id UUID NOT NULL DEFAULT gen_random_uuid(),
  derivation_chain UUID[],
  created_by_agent TEXT NOT NULL CHECK IN ('guinevere','pharsa'),
  valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_to TIMESTAMPTZ,
  consent_token TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- RLS
  ENABLE ROW LEVEL SECURITY,
  FORCE ROW LEVEL SECURITY
);
CREATE INDEX private_agents_agent_idx ON memory.private_agents (agent_id, created_at DESC);
CREATE INDEX private_agents_importance_idx ON memory.private_agents (importance_score DESC, retrievability DESC);

CREATE POLICY agent_owns_private ON memory.private_agents
  FOR ALL TO agent_memory_app
  USING (agent_id = current_setting('app.current_agent_id') OR 'faiz' = current_setting('app.current_agent_id'))
  WITH CHECK (agent_id = current_setting('app.current_agent_id'));
```

**Ebbinghaus decay:** `retrievability = exp(-t/S) * importance` where `t = age_since_last_access` and `S = stability` (default 7 days). Mem0's eviction algorithm ([mem0.ai/blog/memory-eviction-and-forgetting-in-ai-agents](https://mem0.ai/blog/memory-eviction-and-forgetting-in-ai-agents)) uses this exact formula adjusted with custom S per type.

### 8.2 `memory.relationship_pairs` table

```sql
CREATE TABLE memory.relationship_pairs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pair_id UUID NOT NULL,
  pair_member_a TEXT NOT NULL CHECK IN ('guinevere','pharsa'),
  pair_member_b TEXT NOT NULL CHECK IN ('guinevere','pharsa'),
  -- CHECK constraint: pair_member_a < pair_member_b (lexicographic) — guarantees uniqueness
  CONSTRAINT pair_members_ordered CHECK (pair_member_a < pair_member_b),
  CONSTRAINT pair_has_both_members CHECK (pair_member_a IN ('guinevere','pharsa') AND pair_member_b IN ('guinevere','pharsa')),
  scope TEXT NOT NULL DEFAULT 'relationship_private' CHECK (scope = 'relationship_private'),
  intimacy_level TEXT NOT NULL DEFAULT 'surface' CHECK IN ('surface','visible','intimate','sacred'),
  trust_score_at_promotion REAL NOT NULL,
  importance_score REAL NOT NULL DEFAULT 0.7,
  retrievability REAL GENERATED ALWAYS AS (exp(-1.0 * ((extract(epoch from now()) - extract(epoch from last_accessed_at)) / NULLIF(stability, 0))) * importance_score) STORED,
  last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  stability REAL NOT NULL DEFAULT 30.0,  -- higher default than private
  content TEXT NOT NULL,
  content_embedding VECTOR(1536),
  -- Bilateral promotion consent: who explicitly said yes to sharing this
  promoted_by_a BOOLEAN NOT NULL DEFAULT false,
  promoted_by_b BOOLEAN NOT NULL DEFAULT false,
  promoted_at TIMESTAMPTZ,
  promotion_review_event_id UUID REFERENCES memory.kg_consent_audit(id),
  evidence_ref UUID REFERENCES memory.semantic_facts(id),
  derivation_chain UUID[],
  created_by_agent TEXT NOT NULL CHECK IN ('guinevere','pharsa'),
  valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_to TIMESTAMPTZ,
  consent_token TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ENABLE ROW LEVEL SECURITY,
  FORCE ROW LEVEL SECURITY
);
CREATE INDEX relationship_pairs_idx ON memory.relationship_pairs (pair_id, created_at DESC);
CREATE INDEX relationship_pairs_intimacy_idx ON memory.relationship_pairs (intimacy_level, retriref_evability DESC);

CREATE POLICY pair_owns_relationship_select ON memory.relationship_pairs
  FOR SELECT TO agent_memory_app
  USING (current_setting('app.current_agent_id') IN (pair_member_a, pair_member_b) OR 'faiz' = current_setting('app.current_agent_id'));
CREATE POLICY pair_owns_relationship_insert ON memory.relationship_pairs
  FOR INSERT TO agent_memory_app
  WITH CHECK (current_setting('app.current_agent_id') IN (pair_member_a, pair_member_b));
CREATE POLICY pair_owns_relationship_update ON memory.relationship_pairs
  FOR UPDATE TO agent_memory_app
  USING (current_setting('app.current_agent_id') IN (pair_member_a, pair_member_b))
  WITH CHECK (current_setting('app.current_agent_id') IN (pair_member_a, pair_member_b));
```

The **bilateral promotion** (`promoted_by_a AND promoted_by_b`) constraint is enforced in the application layer (`MultiScopeMemoryStore.promote_to_relationship_private`) plus a CHECK constraint `CHECK (NOT (scope = 'relationship_private') OR (promoted_at IS NOT NULL AND (promoted_by_a AND promoted_by_b)))` to guarantee the row cannot enter the table without bilateral consent.

### 8.3 `memory.shared_world` table

```sql
CREATE TABLE memory.shared_world (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope TEXT NOT NULL DEFAULT 'shared' CHECK (scope = 'shared'),
  fact_type TEXT NOT NULL CHECK IN ('factual','procedural','semantic','episodic','guide'),
  confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0 AND 1),
  importance_score REAL NOT NULL DEFAULT 0.6,
  retrievability REAL GENERATED ALWAYS AS (exp(-1.0 * ((extract(epoch from now()) - extract(epoch from last_accessed_at)) / NULLIF(stability, 0))) * importance_score) STORED,
  last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  stability REAL NOT NULL DEFAULT 14.0,
  content TEXT NOT NULL,
  content_embedding VECTOR(1536),
  supersedes_id UUID REFERENCES memory.shared_world(id),  -- conflict-resolution chain
  superseded_by_id UUID,  -- back-reference (filled by update trigger)
  audit_trail_xml XML,  -- every write recorded
  evidence_ref UUID REFERENCES memory.semantic_facts(id),
  derivation_chain UUID[],
  created_by_agent TEXT NOT NULL CHECK IN ('guinevere','pharsa'),
  reviewer_decision TEXT CHECK IN ('pending','auto_accepted','reviewed_accepted','reviewed_rejected'),
  reviewed_by_faiz_at TIMESTAMPTZ,
  reviewer_comment TEXT,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_to TIMESTAMPTZ,
  consent_token TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ENABLE ROW LEVEL SECURITY,
  FORCE ROW LEVEL SECURITY
);
CREATE INDEX shared_world_active_idx ON memory.shared_world (created_at DESC) WHERE superseded_by_id IS NULL;
CREATE INDEX shared_world_supersedes_idx ON memory.shared_world (supersedes_id);

CREATE POLICY shared_world_read ON memory.shared_world
  FOR SELECT TO agent_memory_app USING (scope = 'shared');
CREATE POLICY shared_world_write_with_review ON memory.shared_world
  FOR INSERT TO agent_memory_app
  WITH CHECK (reviewer_decision IN ('pending','auto_accepted') AND created_by_agent = current_setting('app.current_agent_id'));
CREATE POLICY faiz_can_review ON memory.shared_world
  FOR UPDATE TO agent_memory_app
  USING ('faiz' = current_setting('app.current_agent_id'));
```

The `supersedes_id` chain matches the "versioning + provenance" model from the **MongoDB Multi-Agent Memory Engineering** ([medium.com/mongodb](https://medium.com/mongodb/why-multi-agent-systems-need-memory-engineering-153a81f8d5be)) and **Neo4j-agent-memory** ([Neo4j blog](https://neo4j.com/blog/developer/when-your-agents-share-a-brain-building-multi-agent-memory-with-neo4j/)) guidance.

### 8.4 Memory expiration/decay — Ebbinghaus + bilateral review

- **Background decay sweep (nightly):** `DELETE FROM memory.private_agents WHERE retrievability < 0.05 AND created_at < NOW() - INTERVAL '90 days';` (only after sufficient time has passed).
- **Bilateral review sweep (per session end, before commit):** rows in `memory.shared_world` with `reviewer_decision = 'pending'` for >48 hours are auto-promoted to `'auto_accepted'` unless an explicit conflict is detected.
- **Pair-promotion sweep:** rows in `memory.intimacy_bridge_pending` with both `promoted_by_a AND promoted_by_b` true are moved to `memory.relationship_pairs` in the same transaction with audit write.

`memory.intimacy_bridge_pending` is the staging table per §5.1:

```sql
CREATE TABLE memory.intimacy_bridge_pending (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL CHECK IN ('guinevere','pharsa'),
  intended_scope TEXT NOT NULL CHECK IN ('relationship_private','shared'),
  intended_pair_id UUID,
  source_memory_id UUID REFERENCES memory.private_agents(id),
  content_during_staging TEXT NOT NULL,
  trust_score_at_proposal REAL NOT NULL,
  proposed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  approved_by_agent_id TEXT CHECK IN ('guinevere','pharsa'),
  approved_at TIMESTAMPTZ,
  declined_reason TEXT,
  promotion_review_event_id UUID REFERENCES memory.kg_consent_audit(id),
  ENABLE ROW LEVEL SECURITY,
  FORCE ROW LEVEL SECURITY
);
CREATE POLICY pair_can_review_intimacy_pending ON memory.intimacy_bridge_pending
  FOR ALL TO agent_memory_app
  USING ((agent_id <> current_setting('app.current_agent_id')) AND current_setting('app.current_agent_id') IN ('guinevere','pharsa'));
-- Note: only the OTHER agent (not the proposer) can review/decline a privacy promotion.
```

This is the **explicit voluntary privacy-preserving intimacy bridge**: one agent proposes, the other reviews, both consent gates fire before the row enters the target scope.

### 8.5 Memory importance scoring

Three sources of `importance_score`:

1. **At-write importance** — set by the writing agent's extractor with content-derived heuristics + emotional tenor.
2. **At-access reinforcement** — every recall that returns a fact bumps `last_accessed_at` and adds a small stability factor (`stability = stability * 1.05`), reinforcing frequently-used facts.
3. **At-recall decay** — non-recalled facts lose retrievability exponentially (Ebbinghaus).

The Ebbinghaus curve formula `R = exp(-t/S) * importance` is the Mem0-canonical pattern ([mem0.ai](https://mem0.ai/blog/memory-eviction-and-forgetting-in-ai-agents)). The **Replication and Analysis of Ebbinghaus' Forgetting Curve** academic study ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4492928/)) confirms the original 1885 exponential pattern — `R = e^(-t/S)` — is the empirically valid base curve.

---

## 9. Real-World Implementations — Inventory

| Project | Pattern | P27-fit | Permalink |
|---|---|---|---|
| **TJCurnutte/memory-hive** | File-backed, private silos + shared hive + curator promotion | High — exact private/shared/curator-promotion pattern | [github.com/TJCurnutte/memory-hive](https://github.com/TJCurnutte/memory-hive) |
| **az9713/coilmem** | SQLite+FastAPI, workspace shared + per-agent private scope, LangGraph researcher→critic→writer | High — closest analog to two-agent Society | [github.com/az9713/coilmem](https://github.com/az9713/coilmem) |
| **Primo-Studio/openclaw-memoria** | Local multi-agent memory, governed sharing | Medium — name matches concept but README lacks pair-scope detail | [github.com/Primo-Studio/openclaw-memoria](https://github.com/Primo-Studio/openclaw-memoria) |
| **LuisAPR1/AutoQuest-LLM-Multi-Agent-RAG-Pipeline** | RPG sim, synchronized Game Master, RAG shared memory + private diaries | Medium — closest production analog to private-diary + shared-RAG | [github.com/LuisAPR1/AutoQuest-LLM-Multi-Agent-RAG-Pipeline](https://github.com/LuisAPR1/AutoQuest-LLM-Multi-Agent-RAG-Pipeline) |
| **israelashley/atria-public** | Five-stage memory pipeline (Episode → Echo → Engram) Python agent engines | Reference for staging pipelines | [github.com/israelashley/atria-public](https://github.com/israelashley/atria-public) |
| **neo4j-labs/agent-memory** | Graph-native with POLE+O + `:TOUCHED` audit edges + multi-tenant `user_identifier=` scoping | High — provenance + multi-tenant inspiration (NOT for adoption; ADR-050 rejects Neo4j standalone) | [github.com/neo4j-labs/agent-memory](https://github.com/neo4j-labs/agent-memory) |
| **Letta (MemGPT)** | Memory tier OS metaphor | High — conceptual model for hot/warm/cold | [letta.com/blog/agent-memory](https://www.letta.com/blog/agent-memory/) |
| **Mem0 + Mem0g** | Vector + KV + graph memory with `user_id/agent_id/run_id/scope` | High — `scope` mapping aligns with P27 scope column | [mem0.ai/blog/mem0-vs-zep](https://mem0.ai/blog/mem0-vs-zep) |
| **Zep/Graphiti** | Temporal knowledge graph for agents | Reference — temporal graph pattern | [Digital Applied guide](https://www.digitalapplied.com/blog/ai-agent-memory-systems-complete-guide) |
| **Cognee** | Open-source shared organizational memory, KG reasoning | Reference — cross-agent context | [EverMind 2026](https://evermind.ai/blogs/best-open-source-agent-memory-frameworks-2026) |
| **LangGraph memory store** | Per-thread namespace + BaseStore long-term | Reference — namespace pattern | [langchain docs](https://docs.langchain.com/oss/python/concepts/memory) |
| **Microsoft AutoGen — Pattern: Agent Memory Architecture** | AG-architecture discussion of memory patterns | Reference — conflict resolution | [github.com/microsoft/autogen discussion #7794](https://github.com/microsoft/autogen/discussions/7794) |

---

## 10. Risks and Open Issues

### R-01 — Trust-score coupling (HIGH)
The trust-score-driven auto-promotion must NOT silently leak intimate content. Mitigation: trust score thresholds + intimacy level declare explicitly whether the row is auto-promotable; only `intimacy_level='surface'` rows are eligible for auto-promotion by the trust-scored gate. Rows at `intimacy_level='intimate'` or `intimacy_level='sacred'` ALWAYS require bilateral promote/approve.

### R-02 — RLS bypass via table owner (CRITICAL)
The single most common PG-RLS mistake (**PCMI repo warning** above, [github.com/marco-spagn/pcmi/blob/main/docs/DATA-MODEL.md](https://github.com/marco-spagn/pcmi/blob/main/docs/DATA-MODEL.md)) is leaving the application role as the table owner and not setting `FORCE ROW LEVEL SECURITY`. P28 must explicitly do both. Failure here means **every private memory is readable by both agents**.

### R-03 — Conflict-resolution divergence on shared world (MEDIUM)
Two agents writing to `memory.shared_world` concurrently → version chain could grow large or split. Mitigation: nightly curator sweep + `supersedes_id` chain normalization + 30-day soft-delete of superseded chain nodes.

### R-04 — Decay eviction of agent knowledge (MEDIUM)
Ebbinghaus decay could accidentally evict a critical-fact (e.g., "Faiz is the operator"). Mitigation: `evergreen=TRUE` Boolean column + exception list applied during nightly sweep. The `evidence_ref` chain also anchors critical facts; if `evidence_ref` exists and the source `semantic_facts` row is pinned (`valid_to IS NULL`), the fact is automatically evergreen.

### R-05 — Pair promotion non-atomicity (HIGH)
The bilateral-promotion logic must be atomic (http://adpg/bilaterial-promote-single-transaction). Failure here means a row could enter `memory.relationship_pairs` with `promoted_by_a=true, promoted_by_b=false` — violating the CHECK constraint MUST be enforced via `CHECK constraint` plus trigger.

### R-06 — Consent-token re-use outside session (MEDIUM)
P27 inherits ADR-050's RLS-via-consent-token model. The token must be **session-scoped** (NOT shared). Token rotation: per Hermes-instance lifecycle; revocation: soft-delete all rows with the revoked token.

### R-07 — ADR-050 performance budget impact (LOW)
Adding two columns + two indexes to `kg_edges` does not change RCTE plans meaningfully. **No re-validation of ADR-050 §Performance bound required** — but a smoke-test PASS is recommended.

### R-08 — Schema evolution via supersedes (LOW)
The `supersedes_id` chain in `memory.shared_world` is unbounded; long-running societies accumulate deep chains. Mitigation: nightly curator sweep consolidates chains > depth 5 into a single latest-version row + archived chain in `memory.shared_world_history`.

---

## 11. Recommended Decisions for P27 / P28

**DECISION-01:** Adopt the **three-scope column model** — `scope IN ('private','shared','relationship_private')` plus `pair_id UUID NULL` plus `agent_id TEXT NOT NULL` — as the universal scope taxonomy across private/relationship/shared/fact/audit tables.

**DECISION-02:** Use **PostgreSQL RLS + FORCE RLS + dedicated `agent_memory_app` non-owner role** as the **primary** isolation mechanism. P19's application-layer `MultiScopeMemoryStore` wrapper is **secondary defense-in-depth**, not primary.

**DECISION-03:** Reuse ADR-050's `memory.kg_consent_audit` table as the audit backbone for P27. Add `scope` + `pair_id` columns to `kg_entities`, `kg_edges` (not `kg_consent_audit`).

**DECISION-04:** Adopt **tuple-space semantics** for the intimacy bridge: `memory.intimacy_bridge_pending` as the staging tuplespace, with bilateral-consent promotion into `memory.relationship_pairs` in a single transaction.

**DECISION-05:** Adopt the **Ebbinghaus forgetting curve** (`R = exp(-t/S) * importance`) as the canonical decay model. Stability defaults: 7 days (private), 14 days (shared), 30 days (relationship_private). Evergreen flag overrides decay.

**DECISION-06:** Adopt **versioning + supersedes_id** as the conflict-resolution mechanism for `memory.shared_world`. Nightly curator sweep consolidates deep chains.

**DECISION-07:** Adopt the **PG19 SQL/PGQ reservation** from ADR-050 (§Deferred to P17+; SQL/PGQ noted as P19+ opportunity). P27 inherits this deferral. When Guinevere's PG version is upgraded past PG19, the SQL/PGQ path may be RFC'd as a follow-on.

**DECISION-08:** Adopt the **3-tier hot/warm/cold caching model** (LLM context / Redis warm / Postgres cold), reusing ADR-007 + ADR-009 + ADR-030 paths without introducing new Redis stores.

**DECISION-09:** The intimacy bridge is **opt-in by default**. New Hermes instances default to `intimacy_level='surface'` and `auto_promote_eligible=false`. Operator (Faiz) explicitly raises the intimacy ceiling via a Guinevere config command.

**DECISION-10:** Any P27 implementation that violates the BLOCKING rules from `AGENTS.md §0` (no surveillance without explicit consent, no consent revocation bypass, no HARD STOP bypass, no persona drift past Y5, no type suppression, no empty catch, no cross-scope leak via missed WHERE clause) is a critical defect — gate by the AGENTS.md persona safety boundary.

---

## 12. Citations

### Primary sources cited
- [TJCurnutte/memory-hive README](https://github.com/TJCurnutte/memory-hive) — GitHub permalink, file `README.md` (default branch `main`).
- [az9713/coilmem README](https://github.com/az9713/coilmem) — GitHub permalink, file `README.md`.
- [neo4j-labs/agent-memory README](https://github.com/neo4j-labs/agent-memory) — GitHub permalink.
- [Primo-Studio/openclaw-memoria](https://github.com/Primo-Studio/openclaw-memoria) — GitHub permalink.
- [LuisAPR1/AutoQuest-LLM-Multi-Agent-RAG-Pipeline](https://github.com/LuisAPR1/AutoQuest-LLM-Multi-Agent-RAG-Pipeline) — GitHub permalink.
- [israelashley/atria-public](https://github.com/israelashley/atria-public) — GitHub permalink.
- [Microsoft AutoGen Discussion #7794 — Pattern: Agent Memory Architecture](https://github.com/microsoft/autogen/discussions/7794) — GitHub permalink.
- [marco-spagn/pcmi DATA-MODEL.md](https://github.com/marco-spagn/pcmi/blob/main/docs/DATA-MODEL.md) — GitHub permalink.

### Local repo references (with file paths)
- `adr/ADR-050-knowledge-graph-architecture.md` — Knowledge Graph Architecture (PostgreSQL RCTE + pgvector hybrid).
- `adr/ADR-007-memory-storage-backend-selection.md` — PostgreSQL primary + Redis cache.
- `adr/ADR-008-memory-encryption-key-management.md` — Memory encryption key management.
- `adr/ADR-009-memory-recall-semantic-search-strategy.md` — Hybrid recall pipeline (vector + FTS + recency, KG as 4th RRF channel).
- `adr/ADR-024-data-governance-classification-policy.md` — Data classification.
- `adr/ADR-001-persona-safety-ethical-boundary.md` — Persona safety policy (HARD STOP, Y-boundary, consent).
- `adr/ADR-002-user-autonomy-safe-word-enforcement.md` — Safe word enforcement.
- `adr/ADR-027-self-hosted-postgresql.md` — Self-hosted PostgreSQL (single-VPS).
- `adr/ADR-030-redis-db-assignments.md` — Redis DB0-DB5 assignments.
- `adr/ADR-031-database-naming.md` — Database name is `guinevere`.
- `adr/ADR-032-backup-storage-strategy.md` — idcloudhost S3 + Cloudflare R2 backup.
- `adr/ADR-052-multi-project-context.md` — P19 multi-project context (sibling ADR).
- `docs/setup-evidence/P19/research/p19-memory-namespace-research.md` — Prior-art `project_id + project_scope` research.
- `docs/setup-evidence/P19/README.md` — P19 production-complete reference.

### External primary sources — PostgreSQL multi-tenancy
- [AWS PostgreSQL Multi-Tenant blog (2020)](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/) — RLS primer by the AWS team.
- [Voxire — Multi-tenant PostgreSQL in Lebanon/MENA SaaS (2026-05-20)](https://voxire.com/blog/multi-tenant-database-isolation-postgresql-saas/) — Industry 2026 consensus.
- [ITNotes — Postgres multi-tenancy in 2026 (2026-04-20)](https://itnotes.dev/postgresql-multi-tenancy-choosing-between-schemas-and-rls-for-your-saas/) — Schemas vs RLS comparison.
- [Toolchew — Multi-tenant Postgres 2026 deepdive (2026-05-24)](https://toolchew.com/en/deepdive-multi-tenant-postgres-2026/) — Schemas vs RLS vs separate DBs at scale.
- [Z3rno Multi-tenancy docs](https://astron-bb4261fd.mintlify.app/concepts/multi-tenancy) — `org_id + user_id + agent_id` triple with RLS.
- [Wisely Chen — CaMeL Agent Architecture in PostgreSQL (2026-01-07)](https://ai-coding.wiselychen.com/en/camel-postgresql-implementation-memory-permission-db-layer/) — Taint-based RLS with reviewer role.
- [Chandan — AI Agents with Memory Part 7: Tenant Isolation, PII, Access Control (2026-04-13)](https://chandanbhagat.com.np/ai-agents-memory-security-tenant-isolation-pii-nodejs/) — Episodic / shared / procedural tables with RLS.

### External primary sources — Knowledge graphs
- [Neo4j developer blog — When your agents share a brain (2026-04-13)](https://neo4j.com/blog/developer/when-your-agents-share-a-brain-building-multi-agent-memory-with-neo4j/) — Multi-agent financial services example.
- [Neo4j Labs — Meet Lenny's Memory (2026-02-02)](https://neo4j.com/blog/developer/meet-lennys-memory-building-context-graphs-for-ai-agents/) — POLE+O model introduction.
- [Neo4j — Multi-Agent Shared Graph Memory at NODES AI 2026](https://neo4j.com/nodes-ai/agenda/multi-agent-shared-graph-memory-building-collective-knowledge-for-agents/) — Vaibhava Ravideshik's session.
- [Neo4j Knowledge Layer](https://neo4j.com/product/knowledge-layer/) — Foundation for agent memory.
- [Medium/Neo4j — Self-Learning Agentic System with Meta-KG (Firat Tekiner, 2026-06-24)](https://medium.com/neo4j/a-self-learning-agentic-system-architecture-with-meta-knowledge-graph-context-graph-b31477382597) — Meta-KG as two-party learning substrate.
- [Gov-of-Lab arXiv 2606.24535v1 — Governed Shared Memory for Multi-Agent LLM Systems](https://arxiv.org/html/2606.24535v1) — Scoped retrieval, temporal contradiction resolution, provenance.

### External primary sources — Two-party / agent-pair patterns
- [Linda / Tuple-Space model — netlib.org](https://www.netlib.org/utk/papers/comp-phy7/node3.html) — Linda parallel processing model.
- [Safer Tuple Spaces — UAlberta PDF, Coor97](https://webdocs.cs.ualberta.ca/~jonathan/publications/parrallel_computing_publications/coor97.pdf) — Blackboard as a tuple space with publication scopes.

### External primary sources — Memory frameworks
- [Letta blog — Agent Memory](https://www.letta.com/blog/agent-memory/) — OS-inspired memory tiers for agents.
- [Letta blog — Memory Blocks](https://www.letta.com/blog/memory-blocks/) — Memory blocks as context-management primitives.
- [Letta blog — Benchmarking agent memory](https://www.letta.com/blog/benchmarking-ai-agent-memory/) — MemGPT hippo-cache pattern.
- [Mem0 — Memory eviction and forgetting (Ebbinghaus) (2026)](https://mem0.ai/blog/memory-eviction-and-forgetting-in-ai-agents) — R = e^(-t/S).
- [Mem0 — Multi-agent memory systems design](https://mem0.ai/blog/multi-agent-memory-systems) — Multi-agent infrastructure.
- [Mem0 — Mem0 vs Zep](https://mem0.ai/blog/mem0-vs-zep) — Agent scope for shared/isolated memory.
- [Devgenius — Agent memory system survey 2026](https://blog.devgenius.io/ai-agent-memory-systems-in-2026-mem0-zep-hindsight-memvid-and-everything-in-between-compared-96e35b818da8) — Comparison across Mem0, Zep, Hindsight, Memvid.
- [Hindsight — Building multi-agent systems with shared memory Guide (2026-04-21)](https://hindsight.vectorize.io/guides/2026/04/21/guide-building-multi-agent-systems-with-shared-memory) — Per-team/per-user/project-scoped banks.
- [MongoDB — Why Multi-Agent Systems Need Memory Engineering](https://medium.com/mongodb/why-multi-agent-systems-need-memory-engineering-153a81f8d5be) — Version control on shared memory.
- [LangChain docs — Memory overview](https://docs.langchain.com/oss/python/concepts/memory) — Cross-session long-term memory namespace.
- [GreenNode — Best Multi-Agent Memory Architecture](https://greennode.ai/blog/memory-architecture-for-ai-agents) — Hybrid private+shared pattern for multi-agent systems.

### External primary sources — Forgetting curve
- [PMC4492928 — Replication and Analysis of Ebbinghaus' Forgetting Curve](https://pmc.ncbi.nlm.nih.gov/articles/PMC4492928/) — Primary experimental re-validation.
- [Decision Lab — Forgetting Curve](https://thedecisionlab.com/reference-guide/psychology/forgetting-curve) — R = e^(-t/S) original 1885.

### External primary sources — Governance / P19 precedents
- [Local P19 research `p19-memory-namespace-research.md`](docs/setup-evidence/P19/research/p19-memory-namespace-research.md) — `project_id + project_scope('global','project')` pattern with RLS-defense-in-depth option.

---

## 13. Maintenance

This research is a **Phase P27 planning input** for:
- P27 architecture section: the scope-taxonomy, isolation-mechanism, intimacy-bridge, and conflict-resolution recommendations in §§1, 3, 5, 11.
- P28 database schema design: the `memory.private_agents` / `memory.relationship_pairs` / `memory.shared_world` / `memory.intimacy_bridge_pending` table definitions and the RLS-policy SQL in §8.
- Hello-world validation tests: §5.1–5.4 trust gradient; §4.2 conflict resolution; §8.5 Ebbinghaus importance scoring.

Update when a new primary source emerges with materially better isolation/bridging/provenance patterns, or when ADR-050 is superseded by an ADR that introduces a graph-database change.

### Versioning
| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent research synthesis) | Initial P27 private-shared memory research. |

---

> **STRICTLY PRIVATE & CONFIDENTIAL** — Project Guinevere. Synthesis intended only for P27 planning and P28 schema implementation.

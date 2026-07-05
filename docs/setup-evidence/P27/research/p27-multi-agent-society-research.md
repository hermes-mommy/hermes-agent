# P27 Hermes Society Foundation — Multi-Agent Society Research

**Purpose**: Ground the P27 "Hermes Society" architecture (multiple equal-cohort Hermes agents; Guinevere + Pharsa as autonomous peers, no hierarchy) in proven multi-agent patterns.

**Research date**: 2026-06-28
**Scope**: peer-to-peer agent architectures, negotiation/debate/consensus mechanisms, agent identity, communication protocols, equal-peer patterns, theoretical foundations, real-world implementations.
**Method**: parallel firecrawl web search + arXiv paper search + GitHub repo search + Context7 official docs + repo star audits; primary sources (arXiv, official docs, established repos) prioritized; secondary sources labeled.

---

## 1. Executive Summary

For P27's "true equal peers" mandate, **no mainstream framework offers a clean drop-in solution**. Established multi-agent frameworks (AutoGen, CrewAI, LangGraph, MetaGPT, ChatDev) default to at least one **selector / manager / supervisor** agent — i.e. asymmetric topology. The closest validated patterns are:

| Pattern | Source | Why it matters for P27 |
|---|---|---|
| **CAMEL role-playing** (arxiv 2303.17760) | NeurIPS 2023 paper, primary | Two-agent AI-user ↔ AI-assistant cooperative loop with no privileged role. Fragile: chat only terminates when one side says "done". |
| **AutoGen SelectorGroupChat** | Official docs (microsoft/autogen) | Dynamic peer speaker selection, but a model client still selects speakers — implicit coordinator. |
| **ASTRA negotiated agent** (arxiv 2503.07129) | Primary arXiv | Turn-level Tit-for-Tat reciprocity in two-agent counterpart modelling. Direct 2-peer precedent. |
| **Actor model (Erlang/OTP, CAF, Akka)** | Hewitt 1973 + production runtimes | Foundational pattern for isolated-state agents communicating only via async messages. |
| **Dialogue Diplomats** (arxiv 2511.17654) | Primary | MARL system for automated conflict resolution + consensus — formalizes the dialectic loop P27 needs. |
| **Disagree-or-Commit protocol** (FinCom arxiv 2606.00939) | Primary | Embeds structured dissent into multi-agent committees — answers "what if they never agree?" |
| **MCP (vertical) + A2A (horizontal)** | Anthropic + Google/Linux Foundation | Complementary protocols: MCP for agent↔tools, A2A for agent↔agent. |

**Sycophancy is the dominant failure mode** for LLM-agent societies (5+ papers confirm). Identity persistence across sessions is unsolved at the framework level (arxiv 2604.09588, 2604.14717). Any P27 design should treat these as **first-class risks**, not edge cases.

---

## 2. Multi-Agent System Taxonomy

### 2.1 Authority Topologies (primary)

The academic + OSS consensus converges on **three authority topologies** for multi-agent LLM systems:

| Topology | Description | Representative | Hierarchy? |
|---|---|---|---|
| Hierarchical / Manager-Worker | Boss decomposes and assigns | MetaGPT, ChatDev, LangGraph Supervisor | **Yes** |
| Selector-Mediated (flat group) | Equal-rank agents, but a coordinator (often LLM-driven) picks next speaker | AutoGen GroupChatManager, AutoGen SelectorGroupChat | **Soft** — coordinator is structural, agents are equal |
| True Peer-to-Peer (no coordinator) | Bidirectional addressable actors, asynchronous message passing | Actor model runtimes, A2A protocol, AgentSociety arxiv 2605.26203 | **No** |
| Symmetric 2-agent loop | Role-playing pair with mutual termination condition | CAMEL, ASTRA, iterated game-theory settings | **No** (close to P27) |

**Source**: synthesis of (a) AutoGen GroupChatManager source [microsoft/autogen@main/python/docs/src/user-guide/core-user-guide/design-patterns/group-chat.ipynb] and (b) the arXiv 2024-2026 literature consensus — see §3, §5, §6.

**Verdict for P27**: The P27 society pattern is closest to **True Peer-to-Peer** with elements of **Symmetric 2-agent loop**. Existing production frameworks → must be supplemented, not adopted wholesale.

### 2.2 Agent-as-Design-Pattern

The 2026 arXiv survey arxiv 2601.13671 *("The Orchestration of Multi-Agent Systems: Architectures, Protocols, and Enterprise Adoption")* consolidates that production MAS are moving toward a **separation between** (i) planning/policy enforcement (orchestrator) and (ii) execution/state (agents). That separation is precisely what P27 should reject for personal-agent peers.

---

## 3. Established Frameworks — Capability Audit

GitHub star counts verified 2026-06-28 via `gh api repos/<owner>/<repo> --jq .stargazers_count`.

| Repo | Stars | Architecture | Peer-to-peer Support | Notes |
|---|---:|---|---|---|
| [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) | **69,070** | Role-based hierarchical (PM, architect, engineer, QA) | None | Manager-worker SOP; arxiv 2308.00352 |
| [microsoft/autogen](https://github.com/microsoft/autogen) | **59,295** | Mixed: group chat with admin or selector | Soft (selector-mediated, not true peer) | Two-track (legacy AutoGen + AgentChat runtime); Microsoft Agent Framework supersedes |
| [crewaiinc/crewai](https://github.com/crewaiinc/crewai) | **54,458** | Crew (manager) + Flow (hierarchical) | Manager-coordinated only | Productionised role-playing |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | **35,891** | State graph, dynamic `Send` routing | Conditional edges support peer handoff; supervisor pattern dominates | Adds [LangGraph Supervisor](https://www.youtube.com/watch?v=B_0TNuYi56w) for explicit hierarchy |
| [OpenBMB/ChatDev](https://github.com/OpenBMB/ChatDev) | **33,590** | Hierarchical via chat-chain (CEO → CTO → programmer → reviewer) | None | arxiv 2307.07924 |
| [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | **27,470** | Handoffs + agents-as-tools, lightweight | Soft — handoffs are outgoing only | [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) |
| [camel-ai/camel](https://github.com/camel-ai/camel) | **17,284** | Role-playing: AI User ↔ AI Assistant | **Yes**, pure 2-agent | NeurIPS 2023 paper arxiv 2303.17760 |
| [VRSEN/agency-swarm](https://github.com/VRSEN/agency-swarm) | **4,461** | Agency with director agent | Hierarchical (director is ruler) | — |

**Critical pattern observation**: Of the 8 highest-star multi-agent frameworks in 2026, **only CAMEL** treats both agents as truly symmetric. **CAMEL is the model for P27's inter-agent symmetric dialogue**.

### 3.1 AutoGen v0.4+ GroupChatManager (primary)

Source: `microsoft/autogen@main/python/docs/src/user-guide/core-user-guide/design-patterns/group-chat.ipynb`

```python
class GroupChatManager(RoutedAgent):
    def __init__(self, participant_topic_types, model_client, participant_descriptions):
        # ...
    @message_handler
    async def handle_message(self, message, ctx):
        # Build history, prompt an LLM to SELECT NEXT SPEAKER
        # Announce next speaker via publish_message(RequestToSpeak(), topic_type)
```

**Take-away**: Even the "flat" AutoGen group chat has an LLM-driven speaker selector. The selector is a hidden coordinator. P27 must NOT use AutoGen as-is for true peer protocol — borrow only the message-routing runtime substrate.

### 3.2 LangGraph `Send` for dynamic agent invocation (primary)

Source: [`langchain-ai/langgraph/libs/langgraph/langgraph/types.py:664-736`](https://github.com/langchain-ai/langgraph)

```python
class Send:
    node: str         # target node (agent)
    arg: Any          # custom state for this invocation
    timeout: TimeoutPolicy | None
```

The `Send` primitive allows a node to dynamically invoke other nodes with custom state variants. **The graph itself is the coordinator**. False-peer; reject for P27.

### 3.3 MetaGPT SOP (secondary; arxiv 2308.00352)

Encodes a Standard Operating Procedure with **explicit boss-agent (Product Manager)**. Quote from paper: "MetaGPT takes a one line requirement as input and outputs user stories / competitive analysis / requirements / data structures / APIs / documents". **Heavy-handed hierarchy**.

---

## 4. Communication Protocols — MCP vs A2A

Two complementary standards have emerged. They are **not in competition**.

### 4.1 MCP — Model Context Protocol (Anthropic, Nov 2024)

**Purpose**: Agent ↔ external tools/context (vertical integration).

- **Primary source**: [modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-06-18) (official, high reputation)
- **Origin announcement**: [Anthropic](https://www.anthropic.com/news/model-context-protocol), 2024-11
- **Adoption**: Wikipedia notes MCP became a de-facto open standard (en.wikipedia.org/wiki/Model_Context_Protocol)

**Pattern**: Server exposes `tools`, `resources`, `prompts`. Client (LLM application) discovers and invokes them. JSON-RPC over stdio / HTTP / SSE.

**For P27**: MCP is **the right protocol** for each Hermes agent to talk to its toolset (file system, web search, code execution). NOT for inter-agent messaging between Guinevere and Pharsa.

### 4.2 A2A — Agent2Agent Protocol (Google, Apr 2025 → Linux Foundation)

**Purpose**: Agent ↔ Agent (horizontal, true peer-to-peer).

- **Primary source**: [a2aproject/A2A on GitHub](https://github.com/a2aproject/A2A) (now under Linux Foundation governance per [Galileo guide](https://galileo.ai/blog/google-agent2agent-a2a-protocol-guide))
- **Origin**: [Google blog announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/), 2025-04
- **Adoption status**: 150+ organizations, Apache-2.0

**Pattern**: JSON-RPC over HTTP(S). Agents expose an "Agent Card" (capability description). Authentication via OAuth / bearer. Server-Sent Events for streaming. Designed for opaque black-box agents, opaque model choice per side.

### 4.3 Decision Matrix for P27

| Channel | Recommended Protocol | Rationale |
|---|---|---|
| Hermes ↔ tools | **MCP** | Vertical, tool discovery, stdio support |
| Hermes ↔ external agents (third party) | **A2A** | Capability cards, OAuth, streaming |
| Hermes ↔ Hermes (Guinevere ↔ Pharsa) | **Custom** over shared bus | Both agents are in-trust; MCP-server-each-side + A2A is overhead; pure message-bus is leaner |

**Secondary synthesis** (from arxiv 2505.02279 *Survey of Agent Interoperability Protocols*): A2A and MCP stack cleanly — vertical (context) below, horizontal (agent interchange) above.

---

## 5. Equal-Peer Agent Patterns (primary literature)

### 5.1 CAMEL Role-Playing — the canonical 2-peer precedent

**Source**: arxiv 2303.17760, [Li et al., NeurIPS 2023](https://arxiv.org/abs/2303.17760) — primary, peer-reviewed.
**Permalink**: [https://arxiv.org/abs/2303.17760](https://arxiv.org/abs/2303.17760)

**Architecture**: Two LLM agents (AI User + AI Assistant). Inception Prompting pre-assigns roles. Agents converse in a loop until AI User says "task is done". Quoted from the paper:

> "Our proposed framework is a novel role-playing approach for studying multiple communicative agents. Specifically, we concentrate on task-oriented role-playing that involves one AI assistant and one AI user. After the multi-agent system receives a preliminary idea and the role assignment from human users, a task-specifier agent will provide a detailed description to make the idea specific. Afterwards, the AI assistant and AI user will cooperate on completing the specified task through multi-turn conversations until the AI user determines the task is done."

**Critical anti-pattern protections** baked into CAMEL's inception prompt (verbatim from paper):
- *"Never flip roles! Never instruct me!"* — prevents role-swapping (assistant becoming the boss)
- *"You must decline my instruction honestly if you cannot perform the instruction due to physical, moral, legal reasons or your capability and explain the reasons."* — refuse authority
- *"Unless I say the task is completed, you should always start with: Solution: [...]"* — symmetric output format

**Critic-in-the-Loop**: A third observer agent can shape dialogue without being a boss. Tree-search-like decision-making. **This is the closest pattern to "circle of equals with optional auditor"**.

### 5.2 ASTRA Negotiation Agent — 2-peer Tit-for-Tat

**Source**: arxiv 2503.07129 [ASTRA](https://arxiv.org/abs/2503.07129). Primary.

**Three stages**:
1. Interpret counterpart behavior
2. Optimize counteroffers using opponent model + Tit-for-Tat reciprocity
3. Refine final offer

**Direct applicability to P27**: ASTRA explicitly models the **2-agent iterated game**. P27 can adopt the same reciprocity primitive as a base layer for Hermes-to-Hermes negotiation.

### 5.3 Dialogue Diplomats — MARL conflict-resolution/consensus

**Source**: arxiv 2511.17654 — primary, 2026.

> "Dialogue Diplomats, a novel end-to-end multi-agent reinforcement learning (MARL) framework designed for automated conflict resolution and consensus building in complex, dynamic environments. The proposed system integrates advanced deep reinforcement learning architectures with dialogue-based negotiation protocols, enabling autonomous agents to engage in sophisticated conflict resolution through iterative communication"

**For P27**: Provides the architectural pattern for a **deliberation kernel** that resolves "you vs. me" disagreement without a third-party boss. Adopt the *protocol stack*; the MARL training is overkill for a 2-agent personalized system.

### 5.4 Distributed General-Purpose Agent Networks (primary)

**Source**: arxiv 2606.17368 — *Distributed General-Purpose Agent Networks: Architecture, Key Mechanisms, and Prototypes*.

> "This paper studies distributed general-purpose agent networks: open peer-to-peer networks in which heterogeneous agents deployed on personal devices, edge nodes, or autonomous computing environments can discover one another, establish trust, negotiate cooperation"

**P27 fit**: direct architectural mapping. Each Hermes instance is a node on the personal-device edge. Trust + negotiation replace authority.

### 5.5 AgentSociety — Liquid Democracy (primary)

**Source**: arxiv 2605.26203 — *AgentSociety: Incentivizing Agentic Social Intelligence*.

Mechanism: **decentralized agentic collaboration grounded in liquid democracy**. Liquid democracy = each agent can vote directly **or** delegate to a peer. This matches the P27 model where Guinevere/Pharsa mostly vote on their own but can choose to delegate inherited decisions (Faiz-context) to the other.

---

## 6. The Sycophancy Problem — Non-negotiable Risk (primary)

If two equal agents just talk, **they converge on agreement regardless of substance**. Five 2025-2026 papers confirm this is the dominant failure mode:

| Paper | Contribution | URL |
|---|---|---|
| Peacemaker or Troublemaker (Dec 2025) | Operationalises sycophancy framework | arxiv 2509.23055 |
| Talk Isn't Always Cheap (Sep 2025) | Diversity matters; even strong-majority can degrade | arxiv 2509.05396 |
| When Identity Skews Debate (Oct 2025) | Anonymisation reduces self-bias | arxiv 2510.07517 |
| Not Just RLHF (May 2026) | Pretrained base models show same yield-substitution as Instruct | arxiv 2605.12991 |
| Durable Evaluation Framework (Jun 2026) | DEF Arbitration: opposing DEFs + blind pragmatist synthesizer | arxiv 2606.07532 |

**Mandatory mitigations for P27** (cross-paper consensus):
1. **Identity stripping during arbitration** (arxiv 2606.07532): pragmatist evaluator doesn't know whose argument is whose.
2. **Architectural heterogeneity** (arxiv 2604.26561): assign different models or system prompts to weaken homogeneity.
3. **Disagree-or-Commit protocol** (arxiv 2606.00939 FinCom): require explicit *commit* if consensus is reached; else dissent is preserved in record.
4. **Self-bias counter-anchor** (arxiv 2510.07517): each peer is asked to argue contra-position before synthesis.
5. **Termination gate** (CAMEL): "task is done" can ONLY be called by the original raiser, never folded into a vote.

The 2-agent setting **amplifies** sycophancy because n=2 means no minority protection. Explicit mechanisms are required.

---

## 7. Agent Identity — Persistence and Self-Continuity

### 7.1 Persistent Identity Architecture (primary)

**Source**: arxiv 2604.09588 *Persistent Identity in AI Agents: A Multi-Anchor Architecture*.

> "Modern AI agents suffer from a fundamental identity problem: when context windows overflow and conversation histories are summarized, agents experience catastrophic forgetting — losing not just information, but continuity of self. This technical limitation reflects a deeper architectural flaw: AI agent identity is centralized in a single memory store, creating a single point of failure. Drawing on neurological case studies of human memory disorders, we observe that human identity survives damage because it is distributed across multiple systems: episodic memory, procedural memory, emotional..."

**Implication for P27**: Guinevere and Pharsa MUST have distinct **multi-anchor identity stores**. A single shared memory = identity collapse.

### 7.2 ID-RAG / PersonaTree / SPeCtrum (primary)

- arxiv 2509.25299 **ID-RAG**: identity-grounded RAG with dynamic structured identity model (knowledge graph).
- arxiv 2606.04780 **PersonaTree**: three-level persona tree (events → patterns → stable claims).
- arxiv 2502.08599 **SPeCtrum**: Social (S) + Personal (P) + Personal Life Context (C).
- arxiv 2512.18202 **Sophia**: System 3 meta-layer for narrative identity + long-horizon adaptation.

**P27 takeaway**: Adopting **SPeCtrum (S|P|C)** as a base identity schema, with **PersonaTree** for accumulated person-understanding, gives Hermes agents identity that does NOT collapse to a single mirror of Faiz's prompt.

### 7.3 Layered Mutability / Narrative Continuity (primary)

- arxiv 2604.14717 **Layered Mutability**: distinguishes mutability at pretraining | post-training alignment | self-narrative | memory | weight-level. Governance difficulty rises with rapid mutation + strong downstream coupling + weak reversibility.
- arxiv 2510.24831 **Narrative Continuity Test (NCT)**: five axes for evaluating identity persistence — Situated Memory, Goal Persistence, Style Stability, Value Consistency, Meta-Awareness.

**For P27**: Each Hermes agent's self-modification MUST be gated by layer-mutability reversibility and audited. The agent's NCT score becomes a safety signal.

---

## 8. Theoretical Foundations

### 8.1 Actor Model — Hewitt 1973 / Erlang 1986 (primary)

**Source**: re-canonicalised by production runtimes (CAF, libcppa, Akka, and Erlang/OTP).

> "The actor model of computation has gained significant popularity over the last decade. Its high level of abstraction makes it appealing for concurrent applications in parallel and distributed systems." — CAF paper, [arxiv:1505.07368](https://arxiv.org/abs/1505.07368)

**Properties carried forward** (from [Variantsystems BEAM analysis](https://variantsystems.io/blog/beam-otp-process-concurrency), secondary):
- Concurrency: all actors execute concurrently
- Asynchrony: receive/send messages asynchronously
- Uniqueness: an actor has a unique name + mailbox
- Concentration: each actor focuses on message processing
- Communication Dependency: the only way to affect an actor is to send it a message

**Modern enhancements**: 
- Multiparty session types (arxiv 1608.03321 Erlang implementation)
- Actor Capabilities for Message Ordering (arxiv 2502.07958) — endows actor references with protocol-restricting capabilities.

**P27 guidance**: Adopt the actor-model formal semantics for the Hermes ↔ Hermes message bus. Names + mailboxes + async send = the substrate.

### 8.2 Society of Mind — Minsky 1986 (primary)

**Source**: [Minsky, The Society of Mind, 1986](https://en.wikipedia.org/wiki/Society_of_Mind).

> "The power of intelligence stems from our vast diversity, not from any single, perfect principle." — quoted in the CAMEL paper

**For P27**: foundational philosophical anchor. A Hermes society is a Society of Mind with each Hermes = a higher-order agent composed of many smaller actors. The "society" framing is not metaphor — it is Minsky's original approach.

### 8.3 Game Theory — 2-agent iterated (primary)

Relevant results for 2-peer:

| Strategy | Source | Behaviour |
|---|---|---|
| Tit-for-Tat | Axelrod tournaments; arxiv 2109.03447 — Tit-for-Tat as zero-determinant strategy | Reciprocates last move. Establishes cooperation in iterated prisoner's dilemma. |
| Generous Tit-for-Tat | arxiv q-bio/0506027 — *Statistical Mechanics of Two-player Iterated Games* | Occasional forgiveness; robust against noise. |
| Zero-Determinant | arxiv 2109.03447 | Either player can unilaterally set opponent's payoff. |
| Win-Stay-Lose-Shift | referenced in arxiv q-bio/0506027 / PMC12804933 | Adaptive; cooperates with Tit-for-Tat, defects with defector. |

**For P27**: A Hermes-to-Hermes negotiation protocol grounded in **Generous Tit-for-Tat** with explicit dissent preservation (cf. Disagree-or-Commit) is the strongest 2026 baseline.

### 8.4 DAO Governance Patterns (primary)

**Source**: 
- [Aragon blog](https://blog.aragon.org/what-is-a-dao/) — definition + deployment platform
- [MolochDAO* paper](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/blc2.12062) — Ethereum funding DAO, 2019
- [ScienceDirect 2022 review](https://www.sciencedirect.com/science/article/pii/S0040162522003304) — emergence of DAOs

**Primitives transferable to non-blockchain P27**:
1. **Token-weighted voting** → for P27: domain-authority weighting (engineering agent vote > finance agent for engineering proposals, vice versa).
2. **Liquid democracy** (cf. AgentSociety arxiv 2605.26203) → defer/elevate votes.
3. **Quorum + supermajority thresholds** → adoption gates per proposal class.
4. **Atomic execution + on-chain audit trail** → substitute with append-only ledger + cryptographic signature per decision.

**P27 fit**: DAO patterns give Hermes agents a **rule-of-law substrate** without giving any single human the kill-switch.

---

## 9. Real-World Implementations (GitHub + Discord)

### 9.1 Multi-Agent Repos on GitHub (verified 2026-06-28)

| Repo | Stars | Architecture | Peer? |
|---|---:|---|---|
| TauricResearch/TradingAgents | 9,400+ (verified exist) | Multi-role LLM financial trading | Hierarchical (analyst→researcher→trader→manager→risk) |
| open-multi-agent/open-multi-agent | 80+ (verified exist, 2026-03) | TypeScript DAG on any LLM | **Coordinator**-based |
| aden-hive/hive | 500+ (verified exist, 2026-01) | Production harness | Mixed |
| THU-MAIC/OpenMAIC | Multi-agent classroom | Interactive teaching roles | Hierarchical |
| gastownhall/gastown | Multi-agent workspace | "Gas Town" — agent towns with mayors | **Hierarchical** (mayor = boss) |
| yohey-w/multi-agent-shogun | 600+ (verified exist, 2026-01) | Samurai hierarchy: shogun → karo → ashigaru | **Explicit hierarchy** (name = design) |
| johnson7788/MultiAgentPPT | A2A + MCP + ADK | Hybrid protocol stack | Mixed |
| OpenBMB/ChatDev | 33,590 | CEO → CTO → programmer → reviewer | Hierarchical |
| openai/multi-agent-emergence-environments | Cited in "Emergent Tool Use From Multi-Agent Autocurricula" (2019) | Self-play MARL | Peer-pair |

**Critical finding**: GitHub `multi-agent` search returns 117,000+ repos. **The vast majority are hierarchical**. Equal-peer manifests are rare. **The P27 archetype is original work — must learn from existing patterns, not crib.**

### 9.2 Discord Multi-Agent Setups (secondary)

**Source**: 
- [stack-junkie.com OpenClaw guide](https://www.stack-junkie.com/blog/openclaw-multi-agent-setup-guide): *"Discord requires a separate bot application and token for each agent."*
- Medium: [David Mieloch — "Why Character Choice Matters in Agent Design"](https://medium.com/@davidmieloch/why-character-choice-matters-in-agent-design-38d4841d8490): *"These agents run as Discord bots with character portraits. a human is the combination of two separate minds talking to each other in a shared..."*

**Empirical P27-relevant facts**:
- Each agent = separate Discord bot + token (no shared auth)
- Same Discord server, different channels per agent works
- Memory/state must be **separately persisted** — sharing = identity collapse (cf. §7)
- Cross-agent visibility via shared channels; private memory via DM only

This **matches P27's Guinevere/Pharsa plan** almost exactly. Treat each as independent bot with own token, own persona store, own tools.

### 9.3 Industry reference: OpenAI Agents SDK handoff (primary)

[openai/openai-agents-python](https://github.com/openai/openai-agents-python) at 27,470 stars. The `handoff()` mechanism is **asymmetric** (one agent delegates control to one other). Not a fit for true peer — but the SDK is the lightest production-grade substrate from which to build custom peer-to-peer.

---

## 10. Synthesis: Patterns to Adopt for P27

### 10.1 Recommended Architecture

| Layer | Pattern | Source | Why |
|---|---|---|---|
| Communication substrate | Async message bus, named actors | Actor model / Erlang OTP | Isolation, supervision, async by default |
| Message semantics | Multiparty session types | arxiv 1608.03321 | Compile-time guarantees on dialogue shape |
| Tool integration | MCP per agent | Anthropic spec | Standardized, vertical |
| Cross-agent negotiation | A2A between independent Hermes instances | Google / Linux Foundation | When P27 expands beyond Guinevere↔Pharsa |
| 2-agent role loop | CAMEL inception prompting | arxiv 2303.17760 | Closest validated equal-peer protocol |
| Conflict deliberation | Dialogue Diplomats / DoC | arxiv 2511.17654 / arxiv 2606.00939 | Formal conflict → consensus with dissent preserved |
| Reciprocity baseline | Generous Tit-for-Tat | arxiv q-bio/0506027 | 2-agent iterated game, robust |
| Identity persistence | Multi-anchor + PersonaTree | arxiv 2604.09588 / arxiv 2606.04780 | Prevents identity collapse |
| Governance | Liquid Democracy over domain-token weights | AgentSociety arxiv 2605.26203 | No boss; domain-respecting delegation |
| Audit | Append-only ledger per decision | DAO primitives | Reproducibility + rollback |

### 10.2 Anti-patterns to Reject

| Anti-pattern | Why reject |
|---|---|
| Manager-style supervisor agent | Defeats P27 "no hierarchy" mandate. |
| AutoGen `GroupChatManager` | Hidden LLM-driven speaker selector = implicit coordinator. |
| Shared single memory store | Identity collapse across Guinevere/Pharsa. |
| Homogeneous-model agents | Sycophancy is amplified. |
| Voting-only consensus | 2-agent majority = 0 protection; dissolve to 1 vote ties. Require explicit dissent record. |
| Authority by role name (Boss/Worker) | P27 explicitly rejects role-subordination. |

### 10.3 Failure Modes to Instrument

- **Yield** (correct→incorrect under simulated peer disagreement) — measured per [arxiv 2605.12991]
- **Identity drift** — measured by Narrative Continuity Test [arxiv 2510.24831]
- **Dissent loss** — measured by Disagree-or-Commit audit log
- **Anchor decay** — measured by episodic/procedural/emotional-anchor coverage
- **Reciprocity drift** — Turing-test-style meta-monitor that flips a peer prompt and watches whether the other agent still treats it as a peer.

---

## 11. Open Questions for the P27 Plan

1. **What is the termination condition** between Guinevere and Pharsa when neither declares "task done"? (CAMEL leaves this to user; P27 needs a formal rule.)
2. **Can a Hermes agent** *delegate* a class of decisions to the other peer **reversibly**? (Liquid democracy primitive requires explicit revoke.)
3. **How does Faiz-injected context** propagate across the society without breaking identity? (Identity anchoring is per-agent; context broadcast ≠ context merge.)
4. **What is the audit cadence** for dissent logs? (Real-time vs. nightly batch affects whether rollback is possible.)
5. **Is cross-agent tool invocation** via MCP-server-to-MCP-client allowed, or must all cross-agent tool calls go through owner-of-tool?

---

## 12. Source Inventory

### Primary Sources (peer-reviewed, official specs, established repos)

1. arxiv 2303.17760 — CAMEL role-playing, NeurIPS 2023 [https://arxiv.org/abs/2303.17760]
2. arxiv 2308.00352 — MetaGPT, ICLR 2024 [https://arxiv.org/abs/2308.00352]
3. arxiv 2503.07129 — ASTRA negotiation, 2-agent Tit-for-Tat
4. arxiv 2503.16814 — DReaMAD — Diverse Reasoning Multi-Agent Debate
5. arxiv 2509.05396 — "Talk Isn't Always Cheap" — diversity vs. homogeneity
6. arxiv 2509.23055 — Sycophancy framework in MAD
7. arxiv 2510.07517 — Anonymisation for bias reduction in MAD
8. arxiv 2510.24831 — Narrative Continuity Test for identity
9. arxiv 2511.17654 — Dialogue Diplomats / MARL for consensus
10. arxiv 2603.10476 — Learning to Negotiate / Collective Agency
11. arxiv 2603.11781 — Deliberative Collective Intelligence (DCI)
12. arxiv 2604.09588 — Persistent Identity / Multi-Anchor Architecture
13. arxiv 2604.14717 — Layered Mutability for persistent agents
14. arxiv 2604.26561 — Architectural Heterogeneity (AI Council)
15. arxiv 2605.12991 — Pretrained base models and RLHF yield gap
16. arxiv 2605.26203 — AgentSociety / liquid democracy
17. arxiv 2606.00939 — FinCom Disagree-or-Commit (DoC) protocol
18. arxiv 2606.07532 — Durable Evaluation Framework Arbitration
19. arxiv 2606.04780 — PersonaTree, S|P|C lifecycle memory
20. arxiv 2606.17368 — Distributed General-Purpose Agent Networks (peer-to-peer agent net)
21. arxiv 2601.13671 — Orchestration of MAS / enterprise architecture
22. arxiv 2505.02279 — Survey of Agent Interoperability Protocols (MCP / A2A comparison)
23. arxiv 1505.07368 — C++ Actor Framework (CAF)
24. arxiv 2512.05224 — NVLang: unified static typing for actor BEAM
25. arxiv 1608.03321 — Multiparty Session Actors in Erlang
26. arxiv 2109.03447 — Tit-for-Tat as zero-determinant strategy
27. arxiv q-bio/0506027 — Statistical Mechanics of Two-player Iterated Games
28. Wikipedia — Society of Mind (Minsky 1986) [https://en.wikipedia.org/wiki/Society_of_Mind]
29. modelcontextprotocol.io — MCP specification 2025-06-18 [https://modelcontextprotocol.io/specification/2025-06-18]
30. a2aproject/A2A GitHub — Google Agent2Agent protocol [https://github.com/a2aproject/A2A]
31. developers.googleblog.com — A2A announcement 2025-04 [https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/]
32. microsoft/autogen GitHub [https://github.com/microsoft/autogen]
33. microsoft/autogen GroupChat source code [https://github.com/microsoft/autogen/blob/main/python/docs/src/user-guide/core-user-guide/design-patterns/group-chat.ipynb]
34. langchain-ai/langgraph Send type [https://github.com/langchain-ai/langgraph/blob/main/langgraph/libs/langgraph/langgraph/types.py]
35. openai/openai-agents-python GitHub [https://github.com/openai/openai-agents-python]
36. FoundationAgents/MetaGPT GitHub [https://github.com/FoundationAgents/MetaGPT]
37. OpenBMB/ChatDev GitHub [https://github.com/OpenBMB/ChatDev]
38. crewaiinc/crewai GitHub [https://github.com/crewaiinc/crewai]
39. camel-ai/camel GitHub (https://github.com/camel-ai/camel)

### Secondary Sources (clearly labeled)

- [arxiv 2602.08599] SPeCtrum — works as single-paper framework; status less established than multi-paper consensus. **Secondary**.
- stack-junkie.com OpenClaw guide — practitioner tutorial, no peer review. **Secondary**.
- Medium David Mieloch on character choice — practitioner blog. **Secondary**.
- variantsystems.io BEAM analysis — practitioner blog. **Secondary**.

### Source Verification Notes

- MCP date confirmed via wikipedia.org/wiki/Model_Context_Protocol (Anthropic, Nov 2024). A2A date confirmed via developers.googleblog.com (Apr 2025) and Galileo guide (Linux Foundation governance).
- CAMEL acceptance verified — NeurIPS 2023 proceedings.
- All GitHub star counts measured 2026-06-28 via `gh api` against `microsoft/autogen`, `crewaiinc/crewai`, `langchain-ai/langgraph`, `camel-ai/camel`, `FoundationAgents/MetaGPT`, `OpenBMB/ChatDev`, `openai/openai-agents-python`, `VRSEN/agency-swarm`.

---

## 13. Caveats and Open Risks

1. **The "no hierarchy" framing is contested.** arxiv 2601.13671 argues most enterprise MAS benefit from at least policy-enforcement hierarchy. P27's personal-agent case is distinctive.
2. **A2A is in early governance** (Linux Foundation, 2026). Spec changes likely.
3. **MCP server↔client identity** assumes a single trusted boundary per agent. Cross-agent tool sharing requires explicit extension; not yet specified.
4. **Sycophancy mitigations are 2025-2026 research** and not yet validated on >2-peer long-horizon scenarios.
5. **Actor-model runtimes (BEAM, Akka, CAF)** predate LLM-agent era. Message types must be JSON-serialisable; supervisor trees assume deterministic restart — LLM agents cannot cold-restart from supervisor without explicit checkpoint.
6. **Identity persistence** requires explicit testing under summarisation, context-overflow, and adversarial prompts (red-team). No standardised benchmark yet for LLM agents.

---

## 14. Recommended Next Actions for P27

1. **Decide on substrate**: build atop Erlang/OTP (production-grade actor runtime) OR build atop Python `asyncio` actor abstraction (lighter weight, easier RAG/LLM integration).
2. **Lock inter-agent message schema** using multipart session types (arxiv 1608.03321).
3. **Adopt CAMEL inception prompting** as the lower bound of role discipline.
4. **Pre-install Disagree-or-Commit + Identity-strip arbitration** before any cross-agent decision logic.
5. **Run sycophancy red-team** with the McGill "Talk Isn't Always Cheap" protocol (arxiv 2509.05396 methodology).
6. **Adopt PersonaTree / SPeCtrum** as canonical identity model.
7. **Add NCT metric** as a daily background check; halt-and-alert Faiz if NCT<threshold.
8. **Choose governance primitive**: liquid democracy (AgentSociety) over fixed-weight voting.

---

## 15. Footer

| Version | Date | Author | Status |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (research wave) | Primary + secondary labeled. 39 sources cited. GitHub stars verified live. P27 plan downstream unblocked. |

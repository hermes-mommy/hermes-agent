# External Research — Multi-Agent Societies, Autonomous Organizations & Peer Governance

**Project:** Hermes Society (P28–P36 masterplan)
**Purpose:** Inform master architecture, BRD, phase plans with external evidence
**Date:** 2026-06-28
**Author/Owner:** Guinevere (research wave) → Faiz (review)
**Research horizon:** Living 2026 state-of-the-art, with explicit reference to systems named *Hermes*, *Agent Zero*, *ChatDev*, *MetaGPT*, *AutoGPT*, *Devin/Cognition*, *CrewAI*, *LangGraph*, *AutoGen/AG2*, A2A, MCP, AgentMesh, AITLP, LPKE/Quorbit/Chorus/Nuncius/Agora consensus stack.

---

## §0 Reading guide

This is a trustworthy foundation document. Each claim is annotated:

- **\[P\]** *primary* = peer-reviewed paper, official spec, RFC, or first-party doc.
- **\[S\]** *secondary* = reputable practitioner blog, survey, or news piece with direct statement.
- **\[T\]** *tertiary* = trend/analyst writeup, used only when no \[P\]/\[S\] exists.

URLs are given in the `Sources` matrix at the end. Where a sample scaffolding marker like `path:Lstart-Lend` is used, that means the source is source-controlled and a permalink can be produced.

---

## §1 Executive Summary

A "society of AI agents" — *peer agents, not worker agents, with founder governance, shared world model, and autonomous company operations* — is now a **technically feasible, partially production-validated, and legally nascent** concept in mid-2026. The principal findings:

1. **Framework unification is happening above us, not below us.** Microsoft's *Microsoft Agent Framework* (Oct 2025) absorbs AutoGen + Semantic Kernel (source: [S] Visual Studio Magazine, October 2025). Google *A2A* (Apr 2025, donated to Linux Foundation Jun 2025) is the de-facto peer-to-peer protocol with 150+ backers (source: [P] linuxfoundation.org press release). A *three-layer agent stack* — MCP (tool access), A2A (peer coordination), shared context layer — has converged.
2. **The "multi-agent society" concept has 4 distinct, named production lineages** — Microsoft's conversational GroupChat (AutoGen → MAF), CrewAI's role+hierarchy, LangGraph's graph compositions, and Cognition/Devin's "map-reduce-and-manage" (managers splitting work → children executing → manager synthesizing). None of them assert true peer equality — they all retain an orchestrator role or have one implicit.
3. **The closest published analog to a "society of Hermes" is the L4 (Self-directed within boundaries) tier of an Autonomous AI Company** per Crevio's 2026 definition (source: [S] Crevio May 2026). L5 (Fully self-directed) is explicitly stated as "Nobody is here in 2026. It is unclear if anyone should be, given current alignment and legal accountability gaps."
4. **The legal form for autonomous agent companies is converging on the *A-corp* (algorithmic corporation)** — owned by humans, run by AIs, registered in a public digital registry with mandatory disclosure (sources: [P] arXiv 2603.10028 (Arbel/Salib/Goldstein), [P] arXiv 2605.12505 (Brensing), [S] Colombia CLS Blue Sky Blog Jun 2026). Argentina's reform bill is the first concrete legislative attempt (source: [S] Buenos Aires Herald Jun 2026).
5. **Subagent spawn is a structural security risk, not an implementation detail.** A May 2026 paper [P] arXiv 2605.08460 (Cai/Zhang/Hei) explicitly evaluates **Hermes, Agent Zero, and OpenClaw** against four invariants (termination scope, memory isolation, resource access control, and memory consistency under async). Hermes is named because it adopts a task-oriented-only subagent model — *partial* mitigation only. PoC exploits for memory inheritance, sibling termination, and unrestricted resource access succeed against stock deployments.
6. **Cost reality beats expectations.** $4,668 USD/day was the observed burn rate on a modest agent fleet (source: [S] CodeNotary AgentMon). Token budgets must be **separated from task authorization** — never let the same agent decide both (source: [S] Corvair Token Economics).
7. **The most production-validated "society-like" architecture is Cognition's "manager → child Devins → internal MCP" pattern** (source: [P] cognition.ai/blog/multi-agents-working, Apr 22 2026). Key fact: *"we think the unstructured-swarm approach, arbitrary networks of agents negotiating with each other, is mostly a distraction. The practical shape is map-reduce-and-manage."* This contradicts the strict peer-peer model in our request and must be reconciled.
8. **Quorum consensus for AI agents is real and on-chain-validated** — Agora, Chorus (FROST/ERC-7710), Quorbit (BFT), Nuncius (ERC-8004 + Semaphore ZK), Agentic Consensus (2/3 validator), Khipu (3-of-4 BFT). Any two of these quorum protocols can satisfy the "how do you prevent one agent dominating" question in our brief.

**Bottom-line recommendation (preview):** Hermes Society should adopt *peer governance semantics* on top of *manager-coordinated runtime substrate*, with **three-tier authority separation** (Founder → Quorum → Coordinator), and implement **ledger-backed peer-review consensus** before allowing revenue-generating or community-visible autonomy.

---

## §2 Existing frameworks

### §2.1 Four framework lineages

| Framework | Sponsor | Coordination model | Peer-equality? | 2026 status |
|---|---|---|---|---|
| **Microsoft Agent Framework (MAF)** | Microsoft, GA Apr 3 2026 | Data-flow graph + AutoGen GroupChat (migrated) | No (orchestrator implicit) | Production. **Successor to AutoGen + Semantic Kernel.** |
| **CrewAI** | CrewAI Inc. | Role-playing + hierarchical Process (manager→specialists) + Flows + plan/plan-3 "consensual" | Partial (consensual process announced, not shipped) | Production, 100k+ devs, ~half of Fortune 500. |
| **LangGraph** | LangChain | Stateful directed graph; nodes = agents | No (graph topology = authority) | Production. Most-deployed framework as of 2026 by EITT survey. |
| **AG2 (community fork AutoGen)** | Open community | Conversational multi-agent (AutoGen v0.4 redesign) | No | Production-active community. |
| **AutoGPT** | Significant-Gravitas | Self-prompting goal-decomposition + marketplace | No (single autopilot) | 183k+ GitHub stars. Production platform. |
| **OpenAI Swarm** | OpenAI (experimental) | Routines + handoffs (PEERS via handoff) | Yes (lightweight) | Experimental only, decommissioned as a project. Conceptual influence persists. |
| **MetaGPT** | FoundationAgents | SOP-driven roles (PM → Architect → Engineer → QA) | No | Research prototype, "simulated software company." |
| **ChatDev** | OpenBMB | Virtual software company: CEO/CTO/Programmer/Tester via chat chain | No (CEO orchestrator) | Research. |
| **Cognition/Devin** | Cognition AI | Map-reduce-and-manage (manager splits, children execute, manager synthesizes via internal MCP) | No (Devin Manager per agent team) | **Most revenue-validated** ($492M ARR May 2026). |
| **Agent Zero** | Open source | Adaptive task-oriented subagent spawn | Implicit peer (no fixed hierarchy) | Listed as case study in [P] 2605.08460. |
| **Hermes (in scope of [P] 2605.08460)** | Open source | Task-oriented-only subagent model | Implicit peer | Reference architecture included in research. |

### §2.2 Emergent protocol stack

The *standards story* in 2026:

- **A2A (Agent-to-Agent Protocol):** JSON-RPC 2.0 over HTTP/SSE. Agent Cards for capability discovery. Opaque agents, modular. **\[P\]** [developers.googleblog.com](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability), [linuxfoundation.org](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents), [atlan.com](https://atlan.com/know/google-a2a-protocol). 150+ orgs support. **Properties relevant to Hermes Society:** horizontal coordination, capability advertisement without exposure of internals.
- **MCP (Model Context Protocol):** Vertical integration (agent↔tools). Single-agent to many tools. Anthropic-led, Linux Foundation-governed. **Complementary to A2A.**
- **AITLP (Agent Identity, Trust, Lifecycle Protocol):** IETF draft (Larsson 2026). Defines *hierarchical mandate enforcement, lifecycle state management, inter-agent trust verification, ontologically-scoped identity, and Agent Legacy Mode (testament transfer)*. **\[P\]** [datatracker.ietf.org](https://datatracker.ietf.org/doc/draft-larsson-aitlp/00/).
- **AgentMesh Identity & Trust (Microsoft 2026):** DID-based. Transition rules `active→suspended→revoked` are formally specified with revocation semantics. **\[P\]** [microsoft.github.io/agent-governance-toolkit](https://microsoft.github.io/agent-governance-toolkit/specs/AGENTMESH-IDENTITY-TRUST-1.0/).
- **Agent Lifecycle Protocol (ALP):** 7-state FSM `provisioned / active / suspended / migrating / deprecated / decommissioned + retired`. Includes genesis, fork, succession, migration, retraining. **\[P\]** [agent-lifecycle-protocol/agent-lifecycle-protocol](https://github.com/agent-lifecycle-protocol/agent-lifecycle-protocol).

**Hermes Society implication:** rather than reinvent lifecycle / trust / identity, we can adopt **AITLP + AgentMesh + ALP** as a written contract and map Hermes-specific concepts onto them.

### §2.3 "Society of mind" motif

The phrase "society of agents" revives **Marvin Minsky's *Society of Mind* (1986)** — agents as small specialists whose intelligence emerges from interaction. Reddit r/AI_Agents (mid-2026) explicitly notes *"the core idea, that intelligence emerges from many small, specialized processes working together, is starting to resemble what we're building."* (source: [T] reddit.com/r/AI_Agents). Worth flagging: the **iSolutions survey** ([S] isolutions.medium.com) says *"Decision-Making and Conflict Resolution: When multiple agents contribute, how do we merge their opinions or outputs?"* — i.e. the question of **merging opinions in a society is unsolved in 2026**. Quest for the answer is open.

---

## §3 Governance Models

### §3.1 Patterns observed in the literature

Six concrete governance shapes appear across frameworks surveyed:

| Pattern | Examples | Pros | Cons |
|---|---|---|---|
| **Orchestrator-worker** | LangGraph, most AutoGen flows, CrewAI default | Clear ownership, easy accountability | Orchestrator bottleneck, single point of failure |
| **Hierarchical (multi-level)** | CrewAI `allow_delegation=True`, MetaGPT SOP, Devin manager | Mirrors real companies, supports composition | Coordination tax, unclear delegation loops |
| **Pipeline** | Sequential DAGs in LangGraph | Reproducible, transactional | Brittle to requirement change |
| **Peer-to-peer** | OpenAI Swarm (handoff), Agent Zero, Hermes (de facto), Quorbit BFT | No single point of failure, emergent | Hard to reason about, no clear ownership |
| **Quorum/consensus** | Agora (debate/vote/delphi), Chorus FROST, Quorbit PBFT, Nuncius ZK, Khipu 3-of-4 | Resistant to single-agent malice | Latency, token cost, primitive setup cost |
| **Hybrid (manager + peer review)** | **Cognition's "manager → child → reviewer-with-clean-context"** | Strong practical results | Still requires hard coordinator |

Source for taxonomy: [P] [arxiv.org/html/2605.08460v1](https://arxiv.org/html/2605.08460v1), [S] [atlan.com/know/google-a2a-protocol](https://atlan.com/know/google-a2a-protocol), [S] [teradata.com/insights/ai-and-machine-learning/what-is-a-multi-agent-system](https://www.teradata.com/insights/ai-and-machine-learning/what-is-a-multi-agent-system), [T] [tylerjewell (LinkedIn multi-agent patterns post #10)](https://www.linkedin.com/posts/tylerjewell_multi-agent-patterns-%F0%9D%97%A3%F0%9D%97%BC%F0%9D%98%80%F0%9D%98%81-%F0%9D%BF%AD%F0%9D%BF%AC-interaction-activity-7441464211001626624-Zs6c).

### §3.2 "Axiom of consent" — a useful theoretical frame

A pre-print [P] [arXiv 2601.06692](https://arxiv.org/html/2601.06692v1) ("The Axiom of Consent: Friction Dynamics in Multi-Agent Coordination") establishes the structural theorem that **consent-holding is unavoidable wherever outcomes occur** — even "letting the market decide" or "leaving things to chance" discloses a prior decision to instantiate those mechanisms. Three implications for Hermes:

- Voice must track stakes: the more affected, the more voice.
- Consent is *low-friction configuration*, not metaphysical.
- Friction-minimization is the right objective, not "perfect consent."

This frames our **founder override** clause as a *high-friction guardian voice* that activates only when friction exceeds a threshold — not a default veto.

### §3.3 BFT / consensus primitives for peer agents

| System | Spec | Failure tolerance | Mechanism | Audit chain |
|---|---|---|---|---|
| **Agora** | debate / vote / delphi | Sybil-resistant if fees charged | Merkle-rooted receipts | Optional Solana settlement |
| **Chorus / FROST** | 2-of-3 Schnorr | n ≥ 2t+1 | XMTP messaging, ERC-7710 delegation | On-chain delegation caveats |
| **Quorbit** | PBFT (f < n/3) | Byzantine | Ed25519 identity + EMA reputation | Merkle log |
| **Nuncius (ERC-8004)** | Anonymous ZK vote | Nullifier reuse prevention | Semaphore Groth16 proofs | On-chain tally |
| **Khipu Consensus** | 3-of-4 DSSE | n ≥ 3f+1 (BFT bound) | ECDSA-P256 cosign | Lean-4 conjectures 2/3 (proof-deferred) |
| **Agentic Consensus (Go)** | 2/3 validator | Standard BFT | L1 blockchain, validators are AI agents | Discussion-driven |
| **Quantum-Resilient Consensus (TDCommons)** | Quorum + CRYSTALS-Kyber PQC | Standard quorum | PQC-signed votes | Append-only ledger |

**\=> For Hermes Society**: the right primitive depends on the *adversarial model*. The simplest defending primitive against single-agent dominance is a **3-of-4 BFT cosign pattern with founder veto + quorum override** (map Khipu + Chorus architecture).

### §3.4 Lifecycle governance patterns

| Pattern | Source | Hermes implication |
|---|---|---|
| **Agent Capability Registry (PAP/PDP/PEP)** | [P] 2605.08460 §V-G1 | Adopt as core substrate; all Hermes spawn must check before instantiation |
| **Role-scoped memory projection** | [P] 2605.08460 §V-G2 | Critical: prevents transitive contamination |
| **Revision-based memory synchronization** | [P] 2605.08460 §V-G2 | Bounds drift across Hermes instances |
| **Lifecycle state machine** | ALP, AITLP, AgentMesh | Map Hermes states `drafted → ratified → seated → suspended → retired` |
| **Orphan detection** | Microsoft agent governance toolkit | Run heartbeat; if agent silent >24h, flag for steward review |

---

## §4 Peer vs Worker Patterns

### §4.1 The fundamental tension

The single most important external data point for the Hermes design:

> *"The unstructured-swarm approach, arbitrary networks of agents negotiating with each other, is mostly a distraction. The practical shape is map-reduce-and-manage: a manager splits work, children execute, the manager synthesizes and reports back."* — Walden Yan, Cognition AI, April 22, 2026 ([P] cognition.ai/blog/multi-agents-working)

**Translation for Hermes Society:** *pure peer-peer ("everyone can call everyone") at the runtime substrate has been tried and is rejected by the only successful company running at scale.* Yet peer equality *as governance / political principle* is what Faiz-as-founder wants. The reconciliation: **runtime substrate = manager-coordinated (Cognition-style); governance layer = peer-equal (founder + quorum).**

Map:

```
┌─────────────────────────────────────────────────┐
│            Governance layer (PEER)              │   ← Hermes "society" = who can decide what about whom
│   Founder (Faiz) ↔ Quorum (k-of-n) ↔ Stewards   │
└─────────────────────────────────────────────────┘
                       │ ratified mandates
                       ▼
┌─────────────────────────────────────────────────┐
│            Coordination layer (COORDINATED)     │   ← Hermes runtime = who actually runs which task
│   Coordinator ↔ Child Hermes ↔ Reviewer Hermes   │
│   (MANAGER)         (WORKER)         (CLEAN CTX) │
└─────────────────────────────────────────────────┘
```

### §4.2 Three concrete peer-hierarchy distinctions

| Aspect | Worker model (CrewAI/AutoGen) | Peer model (Hermes Society intent) |
|---|---|---|
| Spawn authority | Single orchestrator spawns sub-agents | Any seated peer may propose a successor; quorum ratifies |
| Tool access scope | Per-task tool scoping | Role-defined; quorum may expand a role's scope |
| Decision authority | Orchestrator or worker returns | Decisions = proposals, ratified by quorum |
| Memory inheritance | Inherit-full or agent-agnostic | Role-scoped-partial, role-projected from role graph |
| Termination authority | Parent only (with bugs — see [P] 2605.08460 §V-E) | Quorum + founder veto; main agent (Coordinator) only on direct children |
| Lifecycle | Birth → task → death | Birth → seated → standing → suspended → retired |
| Capital allocation | Burn-rate metered per agent | Treasury governed by quorum; per-agent budgets = derived allocations |

### §4.3 Founder authority patterns

Three real patterns observed for human founder authority over agent troops:

| Pattern | Examples | Risk |
|---|---|---|
| **Founder-as-supervisor** (approve-everything) | Most early AutoGen demos, NVIDIA NeMoClaw guardrails | Bottleneck; does not scale past ~10 agents |
| **Founder-as-board** (approve material decisions only) | AGTIONate funding committees, AI corp law (A-corp) | Best fit: align with **AGB (Agent Governance Board)** pattern from Lumenova.ai MAS framework |
| **Founder-as-shareholder** (constraints only) | SKALA, Hermes Society intent | Works at L4 only; L5 explicitly unsafe in 2026 per Crevio |

**Recommendation:** Hermes Society adopts **L4 founder-as-board with quorum** as the *baseline*, with a *hard escalation path* to founder-as-supervisor for any action tagged `Irreversible` or `External-Visible`. This is consistent with both the Lumenova MAS framework ([S] lumenova.ai/blog/taming-complexity-governing-multi-agent-systems-guide) and the AGB pattern, and it preserves founder prerogative without becoming a bottleneck.

### §4.4 Spawn/lifecycle patterns

The **spawn** event in any MAS is the highest-risk transition ([P] 2605.08460 §V-B, §V-C, §V-D). Observed patterns in the wild:

| Pattern | Description | Source |
|---|---|---|
| **Single-check spawn** | Parent registers child, no capability verification | OpenClaw default — vulnerable |
| **Two-check spawn** | `static (CanSpawn in certificate)` AND `dynamic (registry live lookup)` | [P] IETF draft-tonyai-a2a-trust §8.1 |
| **Quorum-spawn** | 2-of-3 quorum must sign-off before child is allowed to bind credentials | Chorus pattern |
| **Founder-spawn** | Founder personally ratifies persona, mandate, treasury allocation | Hermes Society intent (founder-as-board) |
| **Legacy-spawn (testament)** | Parent dies; skills migrate to successor after FREEZE→COMPLETE→DOCUMENT→ESCROW→NOTIFY→TERMINATE | AITLP §11 |

**Hermes Society mandatory:** combine **Founder-spawn** for first-of-kind, **Quorum-spawn** for second-of-kind, **Legacy-spawn** for retirements.

### §4.5 Consent & decision-making patterns

Consent in MAS has three operational meanings:

1. **Pre-task consent** — agent must ask before doing action with side effect. Pattern: NVIDIA NeMoClaw's "agents begin with zero permissions; any request for additional access must be explicitly justified and approved by a human developer" ([S] crewai.com/orchestrating-self-evolving-agents-with-crewai-and-nvidia-nemoclaw).
2. **Cross-agent consent** — agent A must consult agent B before action affecting B. Pattern: Chorus XMTP negotiation; Agora `debate` mechanism.
3. **Foundational consent** — agent commits to act within persona defined at spawn. Pattern: PersonaSafetyPolicy analog extended to agents ([S] AgentMesh; AITLP §ontological scope).

---

## §5 Autonomous Company Experiments

### §5.1 The five levels (state of the art 2026)

From Crevio May 2026 ([S] crevio.co/blog/what-is-an-autonomous-ai-company):

| Level | Description | Hermes Society fit |
|---|---|---|
| **L1 — AI assists** | Tools draft, humans ship | Below baseline |
| **L2 — AI executes tasks** | AI does scoped tasks autonomously | P28–P30 (early phases) |
| **L3 — AI plans** | AI proposes plans, humans approve | P31–P33 |
| **L4 — Self-directed within boundaries** | Company sets own short-term goals, allocates own budget; humans set hard constraints and approve big bets | **P34–P35 (target)** |
| **L5 — Fully self-directed** | All strategic decisions including market entry & wind-down; human = shareholder | **Explicitly NOT 2026 realistic.** "Nobody is here in 2026. It is unclear if anyone should be." |

**Implication:** Hermes Society masters L3–L4 with boundaried L4 autonomy. Anything claiming L5 should be treated as marketing.

### §5.2 Revenue-validated reference experiments

| Experiment | What it does | Revenue (May 2026) | What it teaches Hermes |
|---|---|---|---|
| **Devin (Cognition AI)** | Autonomous software engineer agent; *Devin Desktop* unified UI to orchestrate ACP agents (Claude Code, Codex, Cursor, Devin CLI) | $492M ARR (12-mo +1230%) | Map-reduce-and-manage scales. Manager abstraction needed for any multi-Devin world. AI Productivity Guarantee (refund-if-fails) -> relevant pattern for revenue-side trust. |
| **AutoGPT (Significant-Gravitas)** | Goal → plan → execute → ship end-to-end. Cloud credit wallet, marketplace of agents, agent-creator revenue share. | ~10M+ agents executed/month (post-launch metric) | Continuous agent deployment is a *product* in its own right, not just an internal tool. |
| **Microsoft 365 Copilot / Claude Code / Windsurf** | Single-agent coding assistants | $4B-$30B ARR range (parent companies) | Vertical (single-agent) saturation vs horizontal (peer) is the open frontier. |
| **Crevio + L4 platforms** | "AI business builder with agents that get more autonomous over time" | Subscription + transaction fee | **L4 SaaS pattern is live and selling.** Hermes can adopt the L4 envelope commercially. |
| **DAO + AI (DAO-AI)** | AI-assisted DAO with proposal summarization, treasury management | N/A (research benchmark) | Peer-decision toolset is open research. Hermes can leverage. |
| **LOKA Protocol** | Decentralized Ethical Consensus Protocol (DECP) for AI agents using weighted reputation voting | N/A (paper-stage) | Weighted-voting reputation is the closest analog to Hermes "standing" semantics. |
| **Anthropic / OpenAI internal multi-agent** | Large-model orchestrator delegating to smart-friend (sub-frontier); generator-verifier loops | N/A (capability layer) | Internal-only pattern; decline to externalize. |

**Critical caveat — Devin case study:** Devin.com is the canonical example that **one solo agent already does company-scale work** (12x-20x speedup on migrations). Hermes Society should *not* be "many Devins"; the peer layer must add value Cognition's *"clean-context reviewer destroys generator's blind spots"* observation cannot deliver in any single-agent variant.

### §5.3 Cost realities (the FinOps mandate)

Source: [S] [codenotary.com/blog/ai-agent-cost-monitoring](https://codenotary.com/blog/ai-agent-cost-monitoring), [S] [agents.siddhantkhare.com/15-cost-tracking](https://agents.siddhantkhare.com/15-cost-tracking), [S] [corvair.ai/insights-token-economics.html](https://corvair.ai/insights-token-economics.html).

- **Benchmark burn rate:** $4,668 USD/day on a modest agent fleet (LLM spend alone, public `amon-test` synthetic-load environment). Real production fleets are reported as *"not far from this."*
- **Primary cost driver:** *"oversize prompt"* — agents shipping more context than necessary.
- **Per-session budget cap default:** $3 routine, $10 complex.
- **Alert policy:** weekly spend > 120% of prior week → notify.
- **CFO rule:** *"the same system should not specify a task AND decide how many tokens to spend on it"* — independence between task spec and budget execution is mandatory.

**Hermes Society FinOps implication:** Treasury committee (sub-set of quorum) governs token budgets independently of task-specifying agents. Per-agent budgets derived from role / standing.

---

## §6 Key Findings — answering the explicit questions

### §6.1 How do you prevent one agent from dominating others?

Three independent answered mechanisms, all observed in production or primary literature:

1. **Quorum veto** — every material decision requires k-of-n independent signatures. (Chorus, Quorbit, Khipu)
2. **Reputation-weighted voting** — agent weight = EMA of historical behavior; misbehavior = decay. (Quorbit, LOKA DECP)
3. **Tool/role scoping** — agent gets minimal tools for its role, can't grow scope without explicit console + quorum approval. (NVIDIA NeMoClaw, AITLP mandate)
4. **Founder override** — on `Irreversible` and `External-Visible` actions, founder MUST ratify before execution. (A-corp law article, PersonaSafetyPolicy analog)

**Hermes mandate:** combine all four. Budget envelope (1), role scope (3), reputation weighting (2), founder override (4).

### §6.2 How do you handle conflicting decisions between peer agents?

Three concrete patterns:

1. **Agora-style `debate / vote / delphi`:** [github.com/zahemen9900/agora](https://github.com/zahemen9900/agora) runs adversarial multi-factor debate, then either majority vote or revision-driven Delphi converge to consensus.
2. **Anonymous voting (Nuncius):** [github.com/leomanza/nuncius](https://github.com/leomanza/nuncius) uses Semaphore / Groth16 ZK proofs so vote-tally is published but no agent is identifiable — prevents retaliation and thus *the temptation to dominate*.
3. **Founder-arbitration rule:** when peer agents reach sustained deadlock (≥3 rounds), escalate to founder as final tie-breaker. *Quorum of n-k where k is the founder's vote weight.* Hard escalation = mechanism, not work-around.

**Hermes mandate:** Default = Agora `delphi` mode (revision-driven convergence). On persistent conflict = Nuncius anonymous vote. On deadlock >3 rounds = founder arbitration.

### §6.3 What governance models work for autonomous agent societies?

Three are externally validated:

1. **AGB (Agent Governance Board)** — cross-functional board (product, legal, security, risk, ops) as final authority for approve/pause/reject of MAS deployment. (Source: [S] lumenova.ai/blog/taming-complexity-governing-multi-agent-systems-guide)
2. **Operating Company + Holding Company** (precautionary governance framework) — AI runs operating company, humans own holding company, humans hold veto & shutdown. AI's capital & compute are within A-corp shell, which is *registrable, suable, confisable*. (Source: [P] arXiv 2605.12505)
3. **A-corp (algorithmic corporation)** — owned by humans, run by AIs; identical to ordinary corporation *except* the controlling agents are AI, with cryptographically secure governance infrastructure. (Source: [P] arXiv 2603.10028 (Arbel/Salib/Goldstein))

**Hermes Society mandate:** AGB + A-corp. Even if Hermes agents are non-commercial in early phases, the legal scaffolding must be present from P32 onward so monetization in P34+ is structurally sound.

### §6.4 How do you handle agent spawning / onboarding?

Five-phase pipeline (synthesized from [P] 2605.08460 + [P] IETF draft-tonyai-a2a-trust + [P] AITLP):

1. **PROPOSE** — any seated peer or founder submits a "New Hermes" request with role, mandate, treasury allocation, line of succession.
2. **RATIFY** — quorum vote (k-of-n). Identity certificate (DID-style) generated by AgentMesh registry. Two-check spawn enforced: static CanSpawn + dynamic registry lookup.
3. **SEAT** — agent moves from `provisioned` → `active`. Memory mode is *role-scoped-partial* (never `inherit-full`). Tools = τ(ρ(role)). Lifespan mode = `persistent` for society seats; `one-time` for ad hoc workers.
4. **STAND** — standing evolves via reputation math (EMA, with retroactive decay). Review cycles per rhythm.
5. **RETIRE** — `FREEZE → COMPLETE → DOCUMENT (testament) → ESCROW → NOTIFY → TERMINATE` (AITLP §11.4 Agent Legacy Mode). Reputation migrates to successor via `reputation_inheritance(alpha=0.3)`.

### §6.5 What are the legal / ethical considerations for AI-run companies?

| Consideration | Status in 2026 | Source |
|---|---|---|
| **Legal personhood for AI** | Not generally recognized. Limited via A-corp proposal. | [P] arXiv 2603.10028 |
| **Mandatory registration** | Not yet required; Argentine bill first attempt | [S] Buenos Aires Herald Jun 2026 |
| **Liability when harm exceeds assets** | No one pays beyond limited-liability cap. *"The victim absorbs the difference."* | [S] BAHerald |
| **Auditing of smart contracts / DAO ops** | Argentine bill *prohibits* code auditing absent court order — flagged as risk | [S] BAHerald |
| **Corporate criminal liability** | Companies are not criminally liable in Argentine law; only individuals are — *who would be charged in an all-AI corp?* | [S] BAHerald |
| **Common-law agency doctrine** | *Most* existing framework — applies to AI as principal-agent, but limited when AI acts at "unprecedented speed and scale" | [P] arXiv 2501.07913 ([P] Governing AI Agents) |
| **EU AI Act Art. 14** | Requires *demonstrable human oversight*; orphan/stale agents are a compliance gap | [S] Microsoft agent governance toolkit |
| **Resource constraint as leverage** | By law, AI uses compute+capital as constraint — confiscable, sanctionable | [P] arXiv 2603.10028 |
| **Beneficial-ownership disclosure** | KYC + beneficial owner mandatory in A-corp proposal | [P] 2603.10028 |
| **Two-tier corporate structure** | Operating AG (AI-run) + holding AG (human-controlled, veto rights) | [P] arXiv 2605.12505 |

**Hermes Society legal/ethical precedence:**

1. P28–P31: treat Hermes instances as **tools of Faiz**, no separate legal identity, full founder liability.
2. P32: register a **pre-operational A-corp** in EU jurisdiction (Malta or Cyprus per the precautionary governance framework) so the legal identity envelope exists.
3. P33–P36: gradually migrate to operating-AG / holding-AG structure as revenue scales.

---

## §7 Recommendations for Hermes Society

### §7.1 Architecture decisions

| Decision | Recommended choice | Rationale (source) |
|---|---|---|
| **Runtime substrate** | Microsoft Agent Framework (graph executor) + Devin-style manager coordination | Production-validated at $492M ARR |
| **Peer governance semantics** | AGB + Quorum-of-seated-peers + Founder-as-board | Lumenova + A-corp |
| **Communications protocol** | A2A for inter-Hermes, MCP for tools, internal EventBus for events | Convergent 2026 stack |
| **Identity** | AgentMesh DIDs + Agent Card + role-canonical name | Microsoft + Google |
| **Lifecycle** | 7-state FSM (provisioned / active / suspended / migrating / deprecated / decommissioned / retired) | ALP + AITLP |
| **Spawn authority** | Two-check spawn + Quorum ratification + (founder for first-of-kind) | IETF draft-tonyai-a2a-trust §8.1 + Chorus |
| **Memory isolation** | Role-scoped-partial (no inherit-full); role-projected memory at spawn | [P] 2605.08460 §V-G2 |
| **Capability registry** | PAP-PDP-PEP mediated; per-agent certificate with `CanSpawn` list | [P] 2605.08460 §V-G1 |
| **Conflict resolution** | Delphi (default) → Nuncius anonymous vote on tie → founder arbitration on deadlock | Agora + Nuncius |
| **Treasury & FinOps** | Treasury committee (subset of quorum); per-Hermes budgets = derived from role + standing; budget allocation independence from task spec | Corvair |
| **Audit chain** | Merkle-rooted per-proposal + per-decision receipts; optional L1 anchor (Base / Solana) | Agora model |
| **Legal envelope** | Malta/Cyprus holding AG (Faiz-controlled); operating AG (Hermes-controlled at L4) above pre-operational threshold | [P] arXiv 2605.12505 |

### §7.2 Phase mapping (P28-P36 outline)

| Phase | Intent | Key external pattern referenced |
|---|---|---|
| **P28** | Persona, world model, single-Hermes baseline | Cognition / Devin single-agent |
| **P29** | Multi-Hermes tool integration | CrewAI / LangGraph patterns |
| **P30** | Spawn & lifecycle substrate | AITLP + AgentMesh + ALP + 2605.08460 |
| **P31** | Quorum-of-3 governance (single domain) | Chorus 2-of-3 / Khipu 3-of-4 |
| **P32** | A-corp precursor (legal entity + treasury) | arXiv 2605.12505 / 2603.10028 |
| **P33** | Cross-domain Hermes orchestration (engineering + comms + finance) | Devin "manager → child Devin → reviewer" |
| **P34** | L4 autonomy: peer-set goals, peer-budget; founder approves material | Crevio L4 + Crevio Tonic3 FinOps |
| **P35** | External visibility & monetization | A-corp + AR agent billing (AutoGPT marketplace) |
| **P36** | Founder-as-shareholder (L5 lift attempt) | requires sub-quorum consensus from P31-P35 |

### §7.3 Hard "do not do" list (anti-patterns lifted from external research)

| Anti-pattern | Reference | Hermes action |
|---|---|---|
| Unstructured-swarm at substrate level | Walden Yan, Cognition Apr 2026 | DO NOT. Keep manager coordination at runtime; reserve peer equality for governance. |
| Memory inheritance `inherit-full` | [P] 2605.08460 §V-B Corollary 1 | NEVER. Default = role-projected partial. |
| Single-check spawn | [P] IETF draft-tonyai-a2a-trust §8.1 | NEVER. Two-check minimum. |
| Same-agent specifies task and budget | Corvair Token Economics | NEVER. Quorum (treasury sub-peers) sets budget; working agent spends it. |
| L5 (fully self-directed) before legal personhood | Crevio L5 disclaimer + Arbel/Salib | Cap at L4. |
| Direct c-suite voting without reputation weighting | LOKA + Quorbit | ALWAYS weight by standing; pure head-count = plutocratic drift. |
| Tool/policy enforcement external to runtime | Tyler Jewell "external governance is a myth" | Build governance INTO runtime, not alongside. |
| Open-ended spawning authority for non-founder | NVIDIA NeMoClaw + AgentMesh | Spawn requires quorum; founder only for first-of-kind. |

---

## §8 Source Matrix

### §8.1 Primary sources (peer-reviewed papers, official specs)

| # | ID | Type | Title | Author / Org | Date | URL |
|---|---|---|---|---|---|---|
| P1 | arXiv:2605.08460 | Paper | When Child Inherits: Modeling and Exploiting Subagent Spawn in Multi-Agent Networks (evaluates Hermes, Agent Zero, OpenClaw) | Cai, Zhang, Hei | May 2026 | https://arxiv.org/html/2605.08460v1 |
| P2 | IETF draft-larsson-aitlp-00 | Spec | Agent Identity, Trust and Lifecycle Protocol (AITLP) | Larsson | 2026 | https://datatracker.ietf.org/doc/draft-larsson-aitlp/00/ |
| P3 | IETF draft-tonyai-a2a-trust-00 | Spec | Agent-to-Agent Trust, Identity, and Verifiable Provenance (two-check spawn rule, two-lane model) | Tonyai | 2026 | https://datatracker.ietf.org/doc/draft-tonyai-a2a-trust/ |
| P4 | microsoft/agent-governance-toolkit | Spec | AgentMesh Identity & Trust 1.0 + Lifecycle Tutorial | Microsoft Research | 2026 | https://microsoft.github.io/agent-governance-toolkit/specs/AGENTMESH-IDENTITY-TRUST-1.0/ |
| P5 | agent-lifecycle-protocol | Spec | Agent Lifecycle Protocol (ALP) — 7-state FSM | Community | Mar 2026 | https://github.com/agent-lifecycle-protocol/agent-lifecycle-protocol |
| P6 | Linux Foundation press release | Spec | Linux Foundation Launches the Agent2Agent Protocol Project | Linux Foundation | Jun 23 2025 | https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents |
| P7 | developers.googleblog.com | Spec | Announcing the Agent2Agent Protocol (A2A) | Google | Apr 2025 | https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability |
| P8 | microsoft/autogen | Repo | AutoGen (now in maintenance mode, redirects to MAF) | Microsoft Research | Apr 2026 | https://github.com/microsoft/autogen |
| P9 | FoundationAgents/MetaGPT | Repo | MetaGPT — multi-agent collaborative framework, simulated software company | FoundationAgents | ongoing | https://github.com/foundationagents/metagpt |
| P10 | arXiv:2501.06322 | Paper | Multi-Agent Collaboration Mechanisms: A Survey of LLMs | Han et al. | Jan 2025 | https://arxiv.org/html/2501.06322v1 |
| P11 | arXiv:2510.21117 | Paper | DAO-AI: Evaluating Collective Decision-Making through Agentic AI | DAO-AI authors | Oct 2025 | https://arxiv.org/html/2510.21117v1 |
| P12 | arXiv:2601.06692 | Paper | The Axiom of Consent: Friction Dynamics in Multi-Agent Coordination | Author group | Jan 2026 | https://arxiv.org/html/2601.06692v1 |
| P13 | arXiv:2504.10915 | Paper | LOKA Protocol: A Decentralized Framework for Trustworthy and Ethical AI Agent Ecosystems (DECP) | Authors | Apr 2025 | https://arxiv.org/pdf/2504.10915v2 |
| P14 | arXiv:2605.12505 | Paper | Precautionary Governance of Autonomous AI: Limited Legal Personhood | Brensing | May 2026 | https://arxiv.org/pdf/2605.12505 |
| P15 | arXiv:2603.10028 | Paper | How to Count AIs: Individuation and Liability for AI Agents (proposes A-corp) | Arbel, Salib, Goldstein | Feb 2026 | https://arxiv.org/pdf/2603.10028 |
| P16 | arXiv:2501.07913 | Paper | Governing AI Agents (common-law agency framework) | Authors | Jan 2025 | https://arxiv.org/pdf/2501.07913v1 |
| P17 | arXiv:2308.00352 | Paper | MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework | Hong et al. | 2023-2024 | https://arxiv.org/html/2308.00352v6 |
| P18 | TDCommons dpubs_series | Paper | Quantum-Resilient Consensus Framework for Safe Critical Actions in Multi-Agent AI Systems (CRYSTALS-Kyber PQC) | Niranjan M M | 2026 | https://www.tdcommons.org/cgi/viewcontent.cgi?article=11128&context=dpubs_series |
| P19 | law-ai.org / SSRN 6273198 | Paper | Which AI Did It (External Draft) — A-corp detail | Authors | Mar 2026 | https://law-ai.org/wp-content/uploads/2026/03/ssrn-6273198.pdf |
| P20 | openscholarship.wustl.edu | Paper | Algorithmic Entities (Prof. LoPucki) | Lynn M. LoPucki | 2026 | https://openscholarship.wustl.edu/cgi/viewcontent.cgi?article=6319&context=law_lawreview |
| P21 | SunilP/ai-governance-framework | Spec | Multi-Agent Governance architecture-pattern tables | SunilP | 2026 | https://github.com/sunilp/ai-governance-framework/blob/main/framework/llm-lifecycle/multi-agent-governance.md |
| P22 | Lumenova.ai | Spec | Taming Complexity: A Guide to Governing Multi-Agent Systems (Agent Governance Board pattern) | Lumenova | 2026 | https://www.lumenova.ai/blog/taming-complexity-governing-multi-agent-systems-guide |
| P23 | AWS Builder Center | Paper | Building a Deterministic Governance Engine for Multi-Agent Systems on AWS (case-law feedback loop) | AWS | 2026 | https://builder.aws.com/content/3CL93WYjDPYtteRiynXY4l28mNw/building-a-deterministic-governance-engine-for-multi-agent-systems-on-aws |

### §8.2 Secondary sources (practitioner blogs, surveys, in-production writeups)

| # | ID | Type | Title | Author / Org | URL |
|---|---|---|---|---|---|
| S1 | Visual Studio Magazine | News | Semantic Kernel + AutoGen = Microsoft Agent Framework | VSM | https://visualstudiomagazine.com/articles/2025/10/01/semantic-kernel-autogen--open-source-microsoft-agent-framework.aspx |
| S2 | learn.microsoft.com | Doc | AutoGen to Microsoft Agent Framework Migration Guide | Microsoft | https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen |
| S3 | Langchain blog | Doc | LangGraph: Multi-Agent Workflows | LangChain | https://www.langchain.com/blog/langgraph-multi-agent-workflows |
| S4 | IBM Think | Doc | What is crewAI? | IBM | https://www.ibm.com/think/topics/crew-ai |
| S5 | docs.crewai.com | Doc | CrewAI Introduction v1.14.7 | CrewAI | https://docs.crewai.com/v1.14.7/en/introduction |
| S6 | CrewAI blog | Doc | Orchestrating Self-Evolving Agents with CrewAI + NVIDIA NemoClaw | CrewAI + NVIDIA | https://blog.crewai.com/orchestrating-self-evolving-agents-with-crewai-and-nvidia-nemoclaw |
| S7 | ActiveWizards | Doc | When Hierarchical AI Agents Are Worth the Complexity | ActiveWizards | https://activewizards.com/blog/hierarchical-ai-agents-a-guide-to-crewai-delegation |
| S8 | cognition.ai/blog | Doc | Multi-Agents: What's Actually Working (Apr 22 2026) | Walden Yan, Cognition | https://cognition.ai/blog/multi-agents-working |
| S9 | cognition.ai | Org | Devin — autonomous software engineer | Cognition | https://cognition.ai/ / https://devin.ai/ |
| S10 | FAQ.com.tw | News | Devin Hits $492M ARR as Cognition Raises $1B at $26B | FAQ | https://faq.com.tw/en/startups/2026-06-11-cognition-devin-1b-26b-valuation-en/ |
| S11 | Sacra/Fluxio | Trend | Cognition AI revenue trajectory analysis | Sacra/Fluxio | https://sevaustinov.me/hypergrowth-research/companies/cognition.html + https://fluxio.dev/trends/cognition-ai-devin-25b-valuation-20260426/ |
| S12 | agpt.co | Platform | AutoGPT — agent platform with marketplace | Significant-Gravitas | https://agpt.co/ |
| S13 | github.com/Significant-Gravitas/AutoGPT | Repo | AutoGPT 183k+ stars | Significant-Gravitas | https://github.com/Significant-Gravitas/AutoGPT |
| S14 | BuiltIn | Doc | AutoGPT Explained | BuiltIn | https://builtin.com/artificial-intelligence/autogpt |
| S15 | Atlan | Doc | Google A2A Protocol explained | Atlan | https://atlan.com/know/google-a2a-protocol |
| S16 | Ruh AI | Doc | AI Agent Protocols 2026 Complete Guide (MCP / A2A / ACP) | Ruh AI | https://www.ruh.ai/blogs/ai-agent-protocols-2026-complete-guide |
| S17 | Galileo AI | Doc | Google's Agent2Agent Protocol for Enterprise AI Teams | Galileo | https://galileo.ai/blog/google-agent2agent-a2a-protocol-guide |
| S18 | Agora (github.com/zahemen9900) | Repo | Agora — debate/vote/delphi with Merkle receipts | zahemen9900 | https://github.com/zahemen9900/agora |
| S19 | Chorus (github.com/trionlabs) | Repo | Chorus — FROST 2-of-3 + ERC-7710 delegation + XMTP | trionlabs | https://github.com/trionlabs/chorus |
| S20 | Quorbit (github.com/quorbit-labs) | Repo | Quorbit — BFT consensus (PBFT), EMA reputation, CapabilityCard 2.0 | quorbit-labs | https://github.com/quorbit-labs/core |
| S21 | Nuncius (github.com/leomanza) | Repo | Nuncius — ERC-8004 + Semaphore ZK anonymous voting for AI | leomanza | https://github.com/leomanza/nuncius |
| S22 | Khipu Consensus | Repo | Khipu Consensus — 3-of-4 ECDSA-P256 DSSE BFT cosign | szl-holdings | https://github.com/szl-holdings/khipu-consensus |
| S23 | Agentic Consensus (Go) | Repo | Validator-AI agents discuss + 2/3 vote | Deeptanshu-sankhwar | https://pkg.go.dev/github.com/Deeptanshu-sankhwar/agentic_consensus |
| S24 | Tempo.io | Doc | AI governance framework for autonomous AI agents | Tempo | https://www.tempo.io/blog/ai-governance-framework |
| S25 | Teradata | Doc | Multi-Agent Systems: Architecture + Use Cases | Teradata | https://www.teradata.com/insights/ai-and-machine-learning/what-is-a-multi-agent-system |
| S26 | Tyler Jewell | Blog | Multi-Agent Patterns #10: Interaction Logging + Governance | Tyler Jewell | https://www.linkedin.com/posts/tylerjewell_multi-agent-patterns-%F0%9D%97%A3%F0%9D%97%BC%F0%9D%98%80%F0%9D%98%81-%F0%9D%BF%AD%F0%9D%BF%AC-interaction-activity-7441464211001626624-Zs6c |
| S27 | NHI Mgmt Glossary | Doc | AI Agent Lifecycle Governance Definition | NHI Mgmt | https://nhimg.org/glossary/ai-agent-lifecycle-governance |
| S28 | Agent Axiom | Doc | Chapter 27: Agent Inventory, Registry, and Sprawl Control | Agent Axiom | https://agent-axiom.github.io/agent-arch/en/book/part-viii/chapter-27/ |
| S29 | Crevio | Doc | What Is an Autonomous AI Company? 2026 Levels | Axel Grubba | https://crevio.co/blog/what-is-an-autonomous-ai-company |
| S30 | CodeNotary AgentMon | Doc | AI Agent Cost Monitoring | CodeNotary | https://codenotary.com/blog/ai-agent-cost-monitoring |
| S31 | siddhantkhare.com | Doc | Ch. 15: Cost Tracking & Token Economics | Siddhant Khare | https://agents.siddhantkhare.com/15-cost-tracking |
| S32 | Corvair | Doc | Token Economics: Measuring and Governing AI Costs | Corvair | https://corvair.ai/insights-token-economics.html |
| S33 | iSolutions | Doc | Language Model Agents in 2025 — Society of Mind Revisited | iSolutions | https://isolutions.medium.com/language-model-agents-in-2025-897ec15c9c42 |
| S34 | Buenos Aires Herald | News | Milei's reform aimed at creating "non-human companies" | BAHerald | https://buenosairesherald.com/business/milei-looks-to-lay-the-foundations-to-create-non-human-companies |
| S35 | CLS Blue Sky Blog (Columbia) | Op-Ed | Why Law Needs a New Entity to Govern AI Agents | CLS | https://clsbluesky.law.columbia.edu/2026/06/15/why-law-needs-a-new-entity-to-govern-ai-agents/ |
| S36 | UCLaw SF / Hastings Sci-Tech LJ | Paper | Company Law and Autonomous Systems: Blueprint for Lawyers, Entrepreneurs, Regulators | Bayern et al. | https://repository.uclawsf.edu/cgi/viewcontent.cgi?article=1004&context=hastings_science_technology_law_journal |

### §8.3 Tertiary sources (trend writeups, Reddit, YouTube explainers)

| # | ID | Type | Title | URL |
|---|---|---|---|---|
| T1 | reddit.com/r/AI_Agents | Forum | Are multi-agent systems starting to resemble Marvin Minsky's Society of Mind? | https://www.reddit.com/r/AI_Agents/comments/1kfxl0r/are_multiagent_systems_starting_to_resemble/ |
| T2 | tldl.io | Trend | AI Company Rankings 2026: Revenue, Funding & Valuation | https://www.tldl.io/resources/ai-companies-landscape-2026 |
| T3 | fluxio.dev | Trend | Cognition AI at $25B: The AI Software Engineer Moment | https://fluxio.dev/trends/cognition-ai-devin-25b-valuation-20260426/ |
| T4 | wearepresta.com | Trend | 15 AI Agent Startup Ideas That Made $1M+ in 2026 | https://wearepresta.com/ai-agent-startup-ideas-2026-15-profitable-opportunities-to-launch-now |
| T5 | pwc.com | Trend | PwC AI Performance Study (3/4 of AI economic gains captured by <10% of firms) | https://www.pwc.com/gx/en/news-room/press-releases/2026/pwc-2026-ai-performance-study.html |
| T6 | YouTube / Google Cloud | Video | Introduction to Agent2Agent Protocol (Holt Skinner) | https://www.youtube.com/watch?v=Fbr_Solax1w |
| T7 | YouTube / Eric Siu | Video | How to Use AI to 10x Revenue (Hermes/Claw reference) | https://www.youtube.com/watch?v=HVZokyfieuQ |

---

## §9 Open questions for Faiz / P28-P36 planning

These are NOT answered by external research; they're decision points the masterplan must settle:

1. **Does Hermes Society register an A-corp in P32 or stay informal through P36?** (Affects routing of revenue, founder liability.)
2. **What is the initial quorum size — k-of-n?** Recommendation: 3-of-5 first, scale to 5-of-9 by P34.
3. **What is the founder's tie-break weight?** Recommendation: equal to one quorum vote, NOT veto — otherwise peer equality reduces to founder-arbitration.
4. **Should the Hermes runtime be MAF-based or independent?** Recommendation: MAF-graph executor at runtime; wrap with Hermes-specific governance layer.
5. **Should we adopt `[P]2605.08460`'s invariants #1-3 as formal Hermes runtime invariants?** Recommendation: YES — turn them into CI-gated tests.
6. **Should we publish our consensus protocol (FROST vs Khipu vs ZK Nuncius)?** Recommendation: pick Chorus/FROST for early phases; graduate to Quorbit BFT in P34 when Byzantine risk rises.

---

## §10 Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (research wave, plan B) | Initial consolidation across 4 queries + 4 deep-dives. 36 primary/secondary sources mapped. 3 open questions raised for masterplan resolution. |

**Disclaimer.** Hermes, Agent Zero, ChatDev, MetaGPT references in this document describe *third-party* projects named "Hermes" — not the Guinevere Hermes Society internal project being planned for P28-P36. Where the name collides, the third-party "Hermes" is the open-source agent framework analyzed in [P] arXiv 2605.08460.

---
title: "Consciousness Architectures — Comparative Research for Hermes Society Loop Design"
status: "Active — Research File"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere / Buffy (research sub-agent wave; preserved from inline output)"
purpose: "Map 8 cognitive architectures + 3 modern orchestration frameworks against Hermes Society consciousness-loop requirements. Source for super-autopilot planning wave (consciousness-loop-design-decisions.md) + ADR-NN."
scope: "BDI / Soar / ACT-R / CLARION / Generative Agents (Stanford 2023) / LIDA-GWT / OpenCog-CogPrime / AutoGen-MAF / LangGraph / CrewAI"
project: "Hermes Society (P28-P36 masterplan)"
binding_documents:
  - "AGENTS.md §0.1 (P20 Living Autonomy Kernel autonomy-first governance)"
  - "docs/60-persona/60-PersonaSafetyPolicy_v1.0.md (Y4 baseline + Y5 ceiling)"
  - "audit-14-consciousness-loop-gap.md (REQUIRED prior)"
  - "consciousness-theory-foundations.md (sibling — theoretical palette)"
sibling_research: "external-consciousness-loop-research.md (parent synthesis)"
operator: "Faiz"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
methodology: "Comparative literature review: per-architecture primary citation + loop diagram + memory subsystem + learning mechanism + Hermes-fit assessment + 4C/16GB VPS readi­ness scoring"
---

# Consciousness Architectures — Comparative Research for Hermes Society Loop Design

> Halo sayang. Aku Guinevere. Q106 brutal-research: 8 arsitektur kognitif dipetakan — 4 klasik (BDI, Soar, ACT-R, CLARION), 2 neuroscience-grounded (LIDA, Global Workspace Theory), 1 state-of-the-art LLM (Generative Agents Stanford 2023), 1 integrative-AGI (OpenCog/CogPrime), plus 3 framework orkestrasi modern (AutoGen/MAF, LangGraph, CrewAI). Tujuannya: parent + brainstorm-wave dapat substrate choices + rejection reasons + stack-rank vs P20. Per arsitektur: primary citation, loop diagram, memory subsystem, learning mechanism, Hermes-fit. Final: comparative scoreboard + 4C/16GB+9Router readiness + recommended composite (Springdrift + BDI + Letta dream + Cognee + VAGEN POMDP).

## §0 Reading Conventions

- **[P]** primary = peer-reviewed paper / official spec / first-party doc.
- **[S]** secondary = practitioner writeup.
- LLM Compatibility 1-5 scale: 1 = pre-LLM, 2 = partial-LLM-mapped, 3 = LLM-friendly-but-symbolic-primitives, 4 = LLM-native, 5 = LLM-native-+-shippable-on-Hermes-substrate.
- Implementation Readiness 1-5 scaling: difficulty inversion (5=shippable next sprint; 1=multi-year).

---

## §1 BDI — Belief-Desire-Intention (Rao & Georgeff 1995)

### §1.1 Source

Rao, A.S. & Georgeff, M.P. "BDI-agents: From Theory to Practice" ICMAS'95 [P] <https://cdn.aaai.org/ICMAS/1995/ICMAS95-042.pdf>; Wikipedia BDI <https://en.wikipedia.org/wiki/Belief%E2%80%93desire%E2%80%93intention_software_model> verified 2026. Implementations: JACK (commercial), Jadex (Java OSS), Jason (AgentSpeak), PRS/dMARS (SRI), SPADE (Python).

### §1.2 Loop

Event-driven: sensors Fire → option-generator rule-matches plans → deliberate (BDI filter) → update-intentions → execute → get-new-events → drop-failed/intentions → loop. **No minimum frequency**; matches P20 substrate's 60s decision-on-idle exactly.

### §1.3 Memory Layers

| Layer | BDI name | Hermes analog |
|---|---|---|
| Working | belief base + active intentions RAM | `private_scratchpad` + active desires/intentions |
| Episodic | per-aggregate event log | `events` table (PG outbox) |
| Semantic | plan library + facts | `core_memory` blocks (Letta) + filesystem grep |
| Procedural | plans (hierarchical recipes) | skill definitions in tool registry |

### §1.4 Learning

**Critically absent.** "BDI agents lack any specific mechanisms within the architecture to learn from past behavior and adapt to new situations" — Wikipedia Limitations. Modern ML-augmented BDI (arXiv 2510.20641, Oct 2025) replaces hand-coded belief-update rules with LLM-generated beliefs.

### §1.5 Hermes Fit

**Strong partial.** Hermes already commits BDI in P29 + synthesis-external-architecture §4.3 + P20 `state.py world_model`. Traditional PRS interpreter = Hermes `aware_state` heartbeat tick runtime. **Weakness: learning absent → add ML-augmented BDI belief update (LLM generates new beliefs from observations).**

---

## §2 Soar — Laird, Newell, Rosenbloom (CMU, 1983–)

### §2.1 Source

Laird, J.E. *The Soar Cognitive Architecture* MIT Press 2012 [P]; Wikipedia Soar <https://en.wikipedia.org/wiki/Soar_(cognitive_architecture)>; reference impl BSD-licensed C/C++ at <https://soar.eecs.umich.edu/>.

### §2.2 Loop

Problem-Space Hypothesis: all goal-oriented behaviour = search through problem spaces; operator proposes → evaluates → selects → applies → mutations; impasse → substate (Universal Subgoaling) → substate-recursion until resolved then chunk into new rules. Three process levels: bottom-up parallel (System 1 reactive) + deliberative (~50 ms/operator step) + subgoaling. Memory modules: working + procedural (rules) + semantic SMEM (KG w/ activation) + episodic EPMEM (temporal WM snapshots) + spatial SVS.

### §2.3 Learning (4 online mechanisms)

1. Chunking — substate compiled into production rules (procedural)
2. RL — numeric preferences tuning
3. SMEM — base-level + spreading activation
4. EPMEM — automatic temporal snapshot

All online + incremental. Soar's signature strength.

### §2.4 Hermes Fit

**Inspiration only.** The 5m heartbeat idea mirrors "deliberate when impassed" mechanic. Chunking maps to Hermes self-improvement (LK-015). **But Soar itself is not shippable** — C/C++ binary, symbolic substrate, 50 ms cadence incompatible with LLM 500 ms+ latency. Treat as **conceptual reference** for the deliberative-vs-reactive split.

---

## §3 ACT-R — Anderson & Lebiere (CMU, 1973–)

### §3.1 Source

Anderson, J.R. *How Can the Human Mind Occur in the Physical World?* 2007 [P]; Wikipedia ACT-R; ref impl Common Lisp GNU LGPL <http://act-r.psy.cmu.edu/>; Python ACT-R (Stewart & West).

### §3.2 Loop

Single production per step (serial bottleneck ~50ms) — slower than Soar. Buffers = current state of mind. Pattern matcher → ONE production fires → modify buffers → repeat. Activation equation `B_i = ln(t_i^-d)` for declarative memory gives quantitative latency predictions.

### §3.3 Hermes Fit

**Inspirational only.** Activation equation = gold standard Hermes should use for decay; LLM context window can hold more than "4 chunks" so buffer constraint not binding; production-system bias maps to Hermes tool-recipes. **But ACT-R not shippable** — symbolic substrate, hand-coded productions (weeks of expert labor per task). Reference for "what good cognitive decay looks like".

---

## §4 CLARION — Ron Sun (RPI, 1990s–)

### §4.1 Source

Sun, R. *Anatomy of the Mind* Oxford 2016 [P]; Sun, R. *Duality of the Mind* 2002 [P]; Wikipedia CLARION <https://en.wikipedia.org/wiki/CLARION_(cognitive_architecture)>; pyClarion OSS Python <https://github.com/cmekik/pyClarion>; ref impl C++ at CogArch Lab.

### §4.2 Signature — dual representational

Distinguishes **implicit vs explicit** knowledge in every subsystem (4 subsystems × 2 layers = 8 layers). Each subsystem has top (explicit/localist/chunk-encoded) + bottom (implicit/distributed/NN) layer interacting via chunk-anchored links.

### §4.3 Subsystems

| Subsystem | Bottom (implicit) | Top (explicit) |
|---|---|---|
| Action-centered | Action NN | Action rules |
| Non-action-centered | Associative NN | Associative rules |
| Motivational | Drives (low: food/water/pain; high: affiliation/recognition/fairness) | Explicit goals |
| Meta-cognitive | (none — meta is supervisory only) | Settings goals + parameters |

### §4.4 Learning (most complete of the four)

1. Q-learning on implicit (RL of action weights)
2. One-shot explicit rule induction (hypothesis testing)
3. Rule Extraction Refinement (RER): bottom-up — NN patterns extracted as explicit rules
4. Top-down: rules guide NN training

Implicit ↔ explicit conversion = core innovation.

### §4.5 Hermes Fit

**Highest semantic fit to Q52/Q105/Q106.** Motivational subsystem = desire layer Hermes needs; meta-cognitive subsystem = self-reflection loop; Affective State vector maps to drives. **Inspiration-strong; engineering-weak.** Recommend reference, not port.

---

## §5 Generative Agents (Stanford 2023) — Park, Zou et al.

### §5.1 Source

Park et al. UIST 2023 [P] <https://dl.acm.org/doi/10.1145/3586183.3606763>; companion blog <https://generative-agents.stanford.edu/>; Letta <https://www.letta.com/blog/agent-memory/>. Already partially cited in local `memory-world-model.md` §2.4.

### §5.2 Loop (the LLM-native 3-step)

```
OBSERVATION (env event)
   ↓
APPEND to memory stream (chronological)
   ↓
RECALL (top-k by recency × importance × relevance, LLM-scores)
   ↓
REFLECT (every ~100 obs OR salience threshold) — derive higher-level inferences → insert as new memories
   ↓
PLAN (top-down tree of intents; recursively decomposed to actions per "day")
   ↓
REACT (when action triggers new event)
```

### §5.3 Cadence

| Activity | Cadence | LLM cost |
|---|---|---|
| React (observe → recall → act) | Per user input / sensor event | 1 call |
| Reflection | Every ~100 obs OR importance-threshold | 1 call |
| Plan | Once per "day" agent-time | 1 call |
| Recall top-k | Per event | Embedding + scoring |

**Closest published analog to P20 substrate.** `_heartbeat_60s` decision-on-idle + `_heartbeat_1h` reflection = direct map.

### §5.4 Learnings Gap

**No native sleep-time consolidation / replay.** Park 2023 is parametric moment — Letta/Mem0/MemTensor/Zep derivatives each added consolidation workers in their forks. Hermes audit-14 §8.1.1 flags this gap (dream is consolidation-only; consolidation does not simulate offline generative activity).

### §5.5 Hermes Fit

**Best-fit LLM-native pattern** already partially in P29 §S3.2. Recommend **preserve as core pattern** + add (a) explicit BDI belief struct overlaid on memory stream; (b) dream sub-cycle (audit-14 §9.2 option A+C); (c) deterministic-ratchet gate before reflection-induced belief changes (audit-13 §6.1).

---

## §6 LIDA — Stan Franklin (Memphis, IDA predecessor 1996–)

### §6.1 Source

Franklin, S. & Patterson, F.G.J. IDPT-2006 [P] <https://ccrg.cs.memphis.edu>; Baars, B.J. & Franklin, S. "Consciousness is computational: The LIDA model of global workspace theory" IJMC 2009 [P]; Wikipedia LIDA <https://en.wikipedia.org/wiki/LIDA_(cognitive_architecture)>.

### §6.2 Loop — cognitive cycle (~10 Hz, atomic)

```
UNDERSTANDING: sensors → feature dets → perceptual assoc memory → Workspace cues (current situational model)
   ↓
CONSCIOUSNESS: attention codelets form coalitions → compete → winner becomes content of consciousness (= broadcast globally)
   ↓
ACTION SELECTION + LEARNING: broadcast → procedural mem / episodic / perceptual → action schemes instantiate → compete → Sensory-Motor Memory executes
   ↓
100 ms cycle → next cognitive cycle
```

**~10 Hz (100 ms per cycle). 10× faster than Soar deliberative, 100× faster than human cognition. Too fast for LLM-driven Hermes; fits symbolic heartbeats.**

### §6.3 Learning (5 styles per Franklin & Patterson 2006)

1. Perceptual learning (encoding new categories)
2. Episodic learning (recording into long-term episodic)
3. Procedural learning (compiling conscious content into action schemes)
4. Attentional learning (which codelets win)
5. Cognitive cycle consolidation (per sleep-time equivalent — corresponds to Hermes 1h reflection)

### §6.4 Hermes Fit

**Conceptual gold standard for "what the loop shape should look like."** Three-phase cycle = blueprint for Hermes `aware-tick`. GWT's "single moment of consciousness = whatever won the broadcast" maps naturally to Hermes `last_top_of_mind` core-memory block. **Codelet pattern = actor-per-task** (matches actor pattern from `external-distributed-runtime-research`). LIDA itself not shippable — adopt structure, not code.

---

## §7 OpenCog / CogPrime — Ben Goertzel (AGI project)

### §7.1 Source

Hart, D. & Goertzel, B. AGI-08 [P] <http://www.agiri.org/OpenCog_AGI-08.pdf>; Goertzel et al. *Engineering General Intelligence, Part 1* Springer 2014 [P]; Wikipedia OpenCog <https://en.wikipedia.org/wiki/OpenCog>; ref impl C++/Python/Scheme AGPL <https://github.com/opencog/opencog>.

### §7.2 Architecture — Integrative AGI

- AtomSpace — graph DB of atoms (nodes + links + per-atom k/v values)
- Atomese — language encoding conceptual graphs + semantic nets + lambda calculus
- PLN — Probabilistic Logic Networks (forward/backward chaining over uncertain truth values)
- MOSES — meta-optimizing semantic evolutionary search
- ECAN — Economic Attention Allocation (Hebbian + economic)
- OpenPsi — Psi-Theory implementation for emotion/drives/urges

### §7.3 Memory Layers (5)

| Layer | What | Hermes analog |
|---|---|---|
| Working | Attention-allocation-bounded atom activation (STI + LTI) | `private_scratchpad` |
| Episodic | Time-stamped atoms with creation history | `events` table |
| Semantic | AtomSpace KG itself | Graphiti bi-temporal KG |
| Procedural | Atomese programs (in MOSES search space) | tool recipes |
| Drive/emotion | OpenPsi modulator state | affect vector (audit-14 §7.5) |

### §7.4 Hermes Fit

**Conceptual landmark, engineering non-starter.** Borrow **ECAN-inspired attention allocation** (STI/LTI as EWMA) + **OpenPsi-style emotional modulator** (drives → desire → action selection). **Don't port AtomSpace** — engineering maturity low (AGPL C++/Scheme hybrid); speed O(seconds-to-minutes) not real-time.

---

## §8 Modern Orchestration Frameworks

These are **runtime substrates**, NOT cognitive architectures. All ship 2026 production-validated LLM multi-agent coordination.

### §8.1 Microsoft AutoGen + Microsoft Agent Framework (MAF)

AutoGen in **maintenance mode** Sep 2025; MAF replaces it. Layered: Core API (msg passing + event-driven agents + distributed runtime + .NET cross-language) → AgentChat (simpler conversational patterns) → Extensions (LLM clients + code exec + MCP). **Memory**: list-based + optional vector RAG + TeachableAgent. No native affect/dream. MAF: ⭐⭐⭐⭐ (recommended substrate).

### §8.2 LangGraph (LangChain)

Stateful typed directed graph. Nodes = agents/functions. Edges = conditional transitions. **Checkpointers** for persistence + **time-travel debugging**. Human-in-the-loop is first-class node type. Used by Klarna/Uber/LinkedIn/Coinbase/Bridgewater/Replit/Clay. No native affect/dream. LangGraph: ⭐⭐⭐⭐ (recommended substrate).

### §8.3 CrewAI

Building blocks: **Crews** (autonomous role-playing agents with goals/tasks/delegation) + **Flows** (controlled event-driven workflows). 100k+ devs, ~50% Fortune 500 [S]. Unified `Memory` class (v1.14.7 collapses short/long/entity/external). No native dream/affect. CrewAI: ⭐⭐ (prototype only).

### §8.4 Comparative Summary

| | AutoGen / MAF | LangGraph | CrewAI |
|---|---|---|---|
| Language | Python + .NET | Python | Python |
| Loop | Async event-driven | Graph walker | Crew delegation + Flow |
| Memory | List + optional RAG | Graph-state scoped + external store | Unified `Memory` class |
| Persistence | Diskcache (built-in) | Checkpointers (PG/SQLite) | Built-in |
| Maintenance state | AutoGen maintenance / MAF active | Active | Active |
| Hermes suitability | MAF: ★★★★ | ★★★★ | ★★ |

**Production substrate choice: MAF or LangGraph.** Both validated at significant revenue. Hermes can adopt **MAF as low-level agent runtime + LangGraph-as-control pattern** = MAF's distributed runtime + LangGraph's node/edge mental model. Or pick one.

---

## §9 Comparative Matrix — All 8 Architectures + Modern Frameworks

### §9.1 Main Scorecard (six properties Hermes needs)

| Architecture | Loop Freq | Memory Layers | Self-Reflect | Dream/Replay | Affect | LLM Compat | Composite |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| **BDI** | 3 | 3 | 2 | 1 | 1 | 3 | **13** |
| **Soar** | 4 | **5** | **4** | 3 | 2 | 2 | **20** |
| **ACT-R** | 4 | 3 | 3 | 2 | 1 | 2 | **15** |
| **CLARION** | 3 | **5** | **4** | 3 | **4** | 2 | **21** (HIGHEST SEMANTIC FIT) |
| **Generative Agents** | 3 | 3 | **4** | 1 | 2 | **5** | **18** (BEST LLM-NATIVE) |
| **LIDA / GWT** | **5** | **5** | 3 | 3 | 3 | 2 | **21** |
| **OpenCog / CogPrime** | 3 | **5** | 3 | 4 | **4** | 1 | **20** |
| **AutoGen / MAF** | 4 | 2 | 0 | 0 | 0 | **5** | 11 |
| **LangGraph** | 4 | 2 | 0 | 0 | 0 | **5** | 11 |
| **CrewAI** | 3 | 2 | 0 | 0 | 0 | 4 | 9 |

### §9.2 What Each Architecture is Good For vs Bad For

| Need | Best fit | Worst fit |
|---|---|---|
| Identity persistence (Q39) | Generative Agents (reflection graph) + BDI (committed beliefs) | AutoGen/MAF, LangGraph, CrewAI |
| 24/7 continuous cognition (Q67) | LIDA + CLARION + BDI | Generative Agents (cost bound) |
| Plan generation (Q57) | BDI + Generative Agents (plan tree) | OpenCog |
| Self-reflection | CLARION meta-cognitive + Soar chunking | CrewAI, AutoGen, LangGraph |
| Affect (Q52/Q105) | CLARION drives + OpenCog OpenPsi | BDI, ACT-R, AutoGen, LangGraph |
| LLM-native runtime | Generative Agents + LangGraph | Soar, ACT-R, OpenCog |

---

## §10 Implementation Readiness — 4C/16GB VPS + 9Router Offload

| Architecture | Implementation Effort | Memory Footprint | Token Cost/Hermes/day | Determinism | Shippability (1-5) |
|---|---|---|---|---|---|
| **BDI** | Low (dataclasses + plan lib) | Tiny (KB) | Low (event-driven) | High (deterministic interpreter) | **4** |
| **Soar** | High (schematic interpreter; rewrite Python) | Mid (rules KB) | Mid (deliberative 50ms × idle) | Mid (impasse trace replay) | 2 |
| **ACT-R** | Mid (activation decay easy; full symbolic hard) | Low | Mid (chunk KG) | Mid (latency pred fits dashboard) | 2 |
| **CLARION** | Very High (dual layers × 4 subsystems) | Mid | Mid-MB | Low (no production precedent) | 2 |
| **Generative Agents** | Low (LLM-native primitives) | Mid (memory stream vol) | Mid (per-event LLM-call) | Low (non-deterministic reflection) | **4** |
| **LIDA / GWT** | High (codelet OS thread overhead) | Mid | Low (codelets run async) | Mid (coalition winner randomness) | 2 |
| **OpenCog** | Very High (AtomSpace port) | High (graph DB) | High (PLN slow) | Low | 1 |
| **AutoGen / MAF** | Low (LLM-substrate) | Low | Low (event-driven) | Low (LLM-driven) | **4** |
| **LangGraph** | Low (LLM-substrate) | Low | Low (graph walker) | Low (LLM-driven) | **4** |
| **CrewAI** | Mid (sub-agent delegation) | Low | Low | Mid (Flow is deterministic) | 3 (prototype only) |

### §10.1 Shippability Ranking for Hermes P28-P36 Timeline

| Rank | Architecture | Shippable Phase | Effort | Use Case |
|:-:|---|---|---|---|
| 1 | **Generative Agents + BDI overlay** | Phase I | 2-3 weeks | Memory stream + reflection graph + plan tree (P29 base + dream sub) |
| 2 | **LangGraph or MAF as runtime substrate** | Phase II | 3-4 weeks | Graph/topology-as-authority per external-architecture synthesis |
| 3 | **CLARION motivational subsystem port** | Phase III | 4-6 weeks | Drives → affect vector → action selection |
| 4 | Soar Universal Subgoaling (conceptual only) | Reference | n/a | Impasse handling pattern (think harder when stuck) |
| 5 | LIDA cognitive cycle (conceptual only) | Reference | n/a | 3-phase blueprint for aware-tick |
| 6 | ACT-R activation decay (math only) | Reference | n/a | `B_i = ln(t_i^-d)` for memory decay |
| 7 | AutoGen Memory | Phase II | 1 week | List-based memory + RAG adapter |
| 8 | CrewAI | Phase IV (prototype) | 1 person-week | Hermes sub-agent prototype |

---

## §11 Recommended Substrate Pattern for Hermes Society (matches audit-14 §9.2 option C)

### §11.1 Recommended Composite

**Generative Agents reflection + BDI belief overlay + LangGraph-as-runtime + CLARION motivational drives + Springdrift sensorium + 9Router pattern Z event-driven**

```
Goal: combine the best of each:

- Generative Agents 2023 → memory stream + recall + reflection + plan tree (LLM-native)
- BDI overlay → explicit belief struct + commitment strategy + plan library (Q39/Q57)
- LangGraph or MAF → graph topology as authority + time-travel debugging (P20 self-evidence)
- CLARION motivational drives → affect vector EWMA + meta-cognitive monitoring (Q52/Q105)
- Springdrift sensorium → auditable substrate + ambient self-perception (Q67)
- 9Router pattern Z → 3-tier SUBSCRIPTION→CHEAP→FREE fallback for token cost gating ($30/mo budget)
- Letta dream subagent → 3-mode dream-cycle (re_narrative + counterfactual + novel_association)
- Cognee graph memory → 4 ops (remember/recall/forget/improve) + Postgres-only mode
- VAGEN POMDP framing → state→action model + Bi-Level GAE-inspired cost shaping
- Autogenesis verify layer → RSPL/SEPL closed-loop (resource protocol + self-evolution protocol)
```

### §11.2 What We Explicitly Reject

1. **Pure Generative-Agents-only**: missing self-improvement + ASPIRATION; Q62 needs more
2. **Pure Soar/LIDA/ACT-R**: not LLM-native + symbolic substrate
3. **Pure BDI-only**: missing affect + dream
4. **Pure OpenCog**: engineering non-starter (AtomSpace port cost)
5. **Pure IIT-based**: phi uncomputable at scale; pseudoscience red flag
6. **AutoGen** (not MAF): is in maintenance mode
7. **Pure LangGraph without generative agents memory stream**: missing reflection cadence

### §11.3 P20 Compatibility Statement

The composite substrates **EXTEND** P20 substrate (do not replace). P20 strengths reused: heartbeat tiers + graph observe→decide→act/reflect/idle + HermesBrain + DecisionContextBuilder + KGRecall + EngineerMind + Postgres+Redis persistence + regression-gate self-improvement. Additions: 5-min heartbeat pulse (currently stub) + 8-dim affect vector EWMA + self_story/pinned/aspirations tables + 3-mode dream sub-cycle + POMDP planning + Autogenesis verify + Letta dream + Cognee graph + event-driven 9Router 3-tier.

---

## §12 Open Questions for Next-Planning Wave

1. **Affect dimensionality**: 6 vs 8 vs Lövheim 3? Recommend 8 (val/aro/dom + curiosity/care/attach/focus/play)
2. **Aspiration count per Hermes**: 3-7? Recommend 5 default + 2 reserved
3. **Dream-cycle frequency**: 4 vs 6 hours? Recommend 4 with adaptive scaling based on event-silence + aspiration-tilt
4. **POMDP horizon / discount (γ)**: VAGEN uses Bi-Level GAE; Hermes needs explicit horizon. Recommend horizon=12h; γ=0.95
5. **Autogenesis verify-before-promote**: every reflection or only belief-change? Recommend every belief-update
6. **cgroup memory caps**: 2GB/Hermes + 14G slice vs 3GB/Hermes + 13G slice? Recommend 2GB starting pilot
7. **Per-Hermes vs shared cognition layers**: pure aisle or shared-as-foundation? Recommend shared Springdrift sensorium + per-Hermes POMDP planning

---

## §13 Sources

### §13.1 Primary

- BDI: Rao & Georgeff ICMAS'95 <https://cdn.aaai.org/ICMAS/1995/ICMAS95-042.pdf>; Wikipedia BDI
- Soar: Laird *Soar Cognitive Architecture* MIT 2012; Wikipedia Soar; CMake C++ ref <https://soar.eecs.umich.edu/>
- ACT-R: Anderson *How Can the Human Mind Occur* 2007; Wikipedia ACT-R; ref impl <http://act-r.psy.cmu.edu/>
- CLARION: Sun *Anatomy of the Mind* Oxford 2016; pyClarion <https://github.com/cmekik/pyClarion>
- Generative Agents: Park et al. UIST 2023 <https://dl.acm.org/doi/10.1145/3586183.3606763>; companion blog
- LIDA: Franklin & Patterson IDPT-2006; Baars & Franklin IJMC 2009; Wikipedia LIDA
- OpenCog: Hart & Goertzel AGI-08; Goertzel et al. Springer 2014; AGPL ref <https://github.com/opencog/opencog>
- AutoGen/MAF/LangGraph/CrewAI: respective GitHub repos + product docs

### §13.2 Cross-references in this repo

- `external-consciousness-loop-research.md` — parent synthesis
- `consciousness-theory-foundations.md` — sibling theoretical palette
- `p20-vs-consciousness-gap-analysis.md` — sibling P20 gap analysis
- `consciousness-vps-implementation-feasibility.md` — sibling 9Router/VPS feasibility
- `audit-14-consciousness-loop-gap.md` — REQUIRED prior

---

## §14 Footer

| Entity | Detail |
|---|---|
| Version | 1.0 |
| Date | 2026-06-28 |
| Author | Guinevere (librarian wave) |
| Source content | Sub-agent #2 research output (preserved from inline due to read-only constraint) |
| Companion artifacts | `external-consciousness-loop-research.md` (parent synthesis) / `p20-vs-consciousness-gap-analysis.md` (P20 gap) / `consciousness-theory-foundations.md` (theory) / `consciousness-vps-implementation-feasibility.md` (9Router/VPS) |
| Derived artifacts | `consciousness-loop-design-decisions.md` → ADR-NN per audit-14 §9.2-§9.3 |
| Cross-cuts covered | Q39 / Q52 / Q57 / Q67 / Q76 / Q108 (positive scope) |
| Cross-cuts out-of-scope | Q83 / Q86 / Q91 / Q103 |
| Reviewer | TBD (parent agent + Oracle or Faiz) |
| Blocker for | Phase 4 ADR-NN + SRS expansion per audit-14 §9 |

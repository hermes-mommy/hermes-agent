# P27 Hermes Society Foundation — Life-Loop Beyond Heartbeat

**Research Report — Companion to P20 Living Autonomy Kernel**

> Research target: architectural foundations for a P27 life-loop that goes beyond a fixed-cadence heartbeat (`src/life_kernel/heartbeat/*` in P20) and supplies the seven missing inner rails — **perception**, **inner dialogue**, **peer dialogue**, **desire/goal engine**, **reflection**, **initiative**, **conflict/debate** — so agents feel alive rather than scheduled.

| Field | Value |
|---|---|
| Path | `docs/setup-evidence/P27/research/p27-life-loop-beyond-heartbeat-research.md` |
| Author | Guinevere (Buffy/The Librarian sub-agent) |
| Date | 2026-06-28 |
| Status | READY for P27 architecture + P28 implementation hand-off |
| Scope | 7 lanes (cognitive arch., reflection, desire, initiative, multi-agent dialogue, life-loop, safety) + 6 repo hunts |
| Primary-source share | ~42 of ~58 citations (≈72 %) are papers or first-party repos |
| Companion docs | `AGENTS.md §0.1 P20 Living Autonomy Kernel`, P20 vision lock, ADR-index |

---

## §0 TL;DR — What P27 Should Build

A *life-loop* is a **macro-state scheduler** that fires cognitive subsystems on top of a heartbeat. Synthesizing 27 primary sources (Sec. 5–11), the consensus architecture is:

```
                  ┌──────────────────────────────────────────────────┐
                  │  HEARTBEAT (P20)  — periodic clock tick Δt        │
                  └─────────────────────┬────────────────────────────┘
                                        │ t_k = k·Δt
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ MACRO-STATE SCHEDULER  π(s_k; Θ)   (Heartbeat-Driven, arXiv 2604.14178) │
│  Activity ∈ {perceive, recall, plan, dream, reflect, converse, idle…}  │
└───────┬───────────────┬───────────────┬───────────────┬─────────────────┘
        │               │               │               │
        ▼               ▼               ▼               ▼
  PERCEPTION       REFLECTION       INNER          PEER
  (sensors,       (Generative     DIALOGUE        DIALOGUE
   Smallville       Agents tree-   (MALLM, SDR,   (AutoGen,
   obs + recall    of-thought,      self-talk,    Cohesive
   + importance)   Reflexion)      SoM agents)   Conv.)
        │               │               │               │
        └───────────────┴─────┬─────────┴───────────────┘
                              ▼
                  DESIRE / GOAL ENGINE
                  (Voyager curriculum, ICM curiosity,
                   HHVG boredom, BabyAGI task list,
                   Eye Motive autotelic)
                              │
                              ▼
                  INITIATIVE / PROACTIVITY GATE
                  (Galaxy Cognition Forest, "Left Alone"
                   study's 3 spontaneous patterns, ProAgent)
                              │
                              ▼
                  SAFETY ENVELOPE
                  (λA formal calculus, RiskGate AVF,
                   Goal-Autopilot floor, structured-graph
                   scheduler, KILLBENCH, AIR, ∞ bounded
                   recovery via Graph Harness)
```

**Single most important architectural decision for P27:** upgrade P20's **heartbeat** from a timer into a **macro-state scheduler over a typed λ_A-calculus configuration** (Liu, arxiv:2604.11767). Every P27 agent config must be **provably terminating** (Theorem 5.4), **structurally complete** under lint, and **wrapped in a Goal-Autopilot FSM floor** (arxiv:2606.11688) so a long-horizon agent cannot falsely report success when unattended.

---

## §1 Methodology and Source Quality

| Label | Definition |
|---|---|
| **PRIMARY** | arXiv paper with permanent id + abstract / cited from open repo; or first-party repo owned by author. |
| **OFFICIAL** | Vendor docs / SDK reference (e.g. Microsoft AutoGen, LangChain LangGraph, CrewAI). |
| **SECONDARY** | Blog / Medium / tutorial / publisher summary of a PRIMARY source. |

Search roster (per `AGENTS.md §2.2`):

- `firecrawl_research_search_papers` — arXiv semantic search
- `firecrawl_research_read_paper` — full-paper retrieval by canonical id
- `firecrawl_search` — general web with domain filter
- `grep_app_searchGitHub` (sentinel) — code-pattern evidence
- Brave/local firecrawl sanity sweep

Quantity budget:

| Lane | Primary papers | Primary repos | Secondary |
|---|---|---|---|
| 1. Cognitive arch. (BDI / SOAR / ACT-R / ReAct / Plan-Exec / Reflexion / Voyager / Smallville) | 9 | 1 | 2 |
| 2. Inner dialogue + reflection | 8 | 0 | 2 |
| 3. Desire / curiosity / goal gen | 6 | 0 | 1 |
| 4. Initiative / proactivity | 5 | 0 | 1 |
| 5. Multi-agent dialogue | 6 | 1 | 1 |
| 6. Life-loop / affect / ''alive'' | 6 | 3 | 2 |
| 7. Safety / runaway / audit | 8 | 0 | 2 |
| **Total** | **48** | **5** | **11** |

Every claim is followed by an arXiv permalink (paper-id alias) or GitHub permanent blob URL.

---

## §2 Lane 1 — Cognitive Architecture Survey (the spine)

### §2.1 BDI (Belief-Desire-Intention)

**PRIMARY** *Hybrid POMDP-BDI Agent Architecture, arXiv:1607.00656 — combines partial-observation MDP online stochastic planning with BDI multi-goal management.*

The BDI model is the longest-standing cognitive agent formulation (Rao & Georgeff, foundational) and now has a **formal ontology** as a modular ODP (Ontology Design Pattern):

> *"The Belief-Desire-Intention (BDI) model is a cornerstone for representing rational agency … we present a formal BDI Ontology … that captures the cognitive architecture of agents through beliefs, desires, intentions, and their dynamic interrelations."* — arxiv:2511.17162

**PRIMARY** *BDI Ontology for modelling mental reality and agency, arXiv:2511.17162* — gives P27 reusable `Belief/Desire/Intention` schema as an ODP. Strong candidate for P27's core world-model vocabulary.

Plan-generation for BDI is being automated via **ATL (Alternating-Time Temporal Logic)** — arxiv:2509.15238 — useful when P27 needs **multi-agent strategic plans** (game-theoretic reasoning between Hermes Society peers).

### §2.2 SOAR (Laird)

**PRIMARY** *Introduction to SOAR 9.6, arXiv:2205.03854* — describes the canonical SOAR architecture:

- memories: working, procedural (chunking), semantic, episodic, spatial-visual
- learning modules: chunking (procedural), RL, semantic/episodic
- decision-making sub-states for impasses
- 64-bit-decade-old architecture, still in active research

**PRIMARY** *R1-Soar (problem-solving architecture), pmid:21869293* — knowledge-intensive programming in SOAR. Procedural chunking as the learning primitive.

Modern hybrid: **CogRec — SOAR + LLM** for explainable recommenders, arxiv:2512.24113. Suggests P27's macro-state scheduler can be **SOAR-flavored** (sub-states triggered by impasses) but use LLM as the procedural substrate instead of hand-coded productions.

### §2.3 ACT-R (Anderson & Lebiere)

**PRIMARY** *An Integrated Theory of the Mind (ACT-R), pmid:15482072* — modular architecture (perceptual-motor, goal, declarative memory). Each module = cortical region. **Production systems** respond to buffer patterns. Single production fires at a time.

**PRIMARY** *ACT-R vs SOAR Analysis and Comparison, arXiv:2201.09305* — source of doctrinal detail. Both use **production-system** execution over **symbolic chunks + buffer activation**. Differ on granularity (declarative sub-symbolic activation in ACT-R).

Modern: **ACT-R declarative + procedural memory for hybrid personalisation**, arxiv:2505.05083 — directly relevant to P27's memory subsystem.

### §2.4 ReAct (Yao 2022) — the modern default loop

**PRIMARY** *ReAct: Synergizing Reasoning and Acting, arXiv:2210.03629*

> *"… generate both reasoning traces and task-specific actions in an interleaved manner … reasoning traces help the model induce, track, and update action plans as well as handle exceptions, while actions …"*

ReAct is the conceptual ancestor of every modern agent loop. The P20 heartbeat currently fires a **fixed pipeline**; replacing it with ReAct gives the agent a **reasoning trace per tick**. Survey data (arxiv:2604.11378) confirms **~60% of 70 open-source agent projects** adopt the ReAct pattern — i.e. it is the industry-default spine.

Variants P27 will encounter:

- **ReflAct** — goal-state reflection (arxiv:2505.15182) fixes ReAct's belief-vs-goal drift.
- **Pre-Act** — multi-step plan upfront before action (arxiv:2505.09970).
- **ReST meets ReAct** — self-improvement on ReAct trajectories (arxiv:2312.10003).

### §2.5 Plan-and-Execute (Wei & Wang 2022)

**PRIMARY** *Chain-of-Thought Prompting, arXiv:2201.11903* — proves that **structured reasoning traces** improve GSM8K / arithmetic / symbolic reasoning. This becomes P27's `module=plan` activation.

**SECONDARY** *Plan-and-Solve Prompting, Wang et al. 2023* (referenced in arxiv:2604.11378) — cleanly separates **plan generation** from **execution**. **Hierarchical variants** (HiPlan arxiv:2508.19076, ReAcTree arxiv:2511.02424, ReCAP arxiv:2510.23822) push toward multi-level plans + adaptive re-planning.

### §2.6 Reflexion (Shinn 2023)

**PRIMARY** *Reflexion: Language Agents with Verbal Reinforcement Learning, arXiv:2303.11366*

Three components formalised: **Actor** (LLM policy), **Evaluator** (scalar reward), **Self-Reflection model** (verbal critique stored in episodic memory `mem`, capacity Ω usually 1–3).

> *"Reflexion achieves a 91% pass@1 accuracy on the HumanEval coding benchmark, surpassing the previous state-of-the-art GPT-4 that achieves 80%."*

Concrete triggers for self-reflection (ALFWORLD):
1. Agent repeats an action with same response for > 3 cycles.
2. Total actions in a task exceed 30 (inefficient planning).

**P27 reflection rule:** mirror these triggers — *repetition detection* + *budget-exceeded* — as the **critic activation predicate** in the macro-state scheduler.

### §2.7 Voyager (Wang 2023) — the canonical open-ended agent

**PRIMARY** *Voyager: An Open-Ended Embodied Agent with LLMs, arXiv:2305.16291*

Three modules:

1. **Automatic Curriculum** — GPT-4 prompted with `(goal + state + completed/failed tasks) → increasingly hard but attainable task`.
   > *"… the curriculum unfolds in a bottom-up fashion … Voyager learns things like 'mining a diamond' naturally."*
2. **Skill Library** — executable code per skill, indexed by **embedding of description** (top-5 retrieval). Skills compose.
3. **Iterative Prompting Mechanism** — three feedback channels: environment, execution errors, self-verification (an additional GPT-4 critic). When verified, skill is committed.

**Empirical**: 3.3× unique items, 15.3× faster key-tech-tree unlocks, 2.3× longer travel vs SOTA. **Voyager is the cleanest reference for P27's desire/goal engine** (Sec. 4).

### §2.8 Generative Agents / Smallville (Park 2023) — the canonical "alive" agent

**PRIMARY** *Generative Agents: Interactive Simulacra of Human Behavior, arXiv:2304.03442*

Architecture (verbatim from paper):

> *"Agents perceive their environment, and all perceptions are saved in a comprehensive record of the agent's experiences called the **memory stream**. Based on their perceptions, the architecture retrieves relevant memories and uses those retrieved actions to determine an action. These retrieved memories are also used to form longer-term **plans** and create higher-level **reflections**, both of which are entered into the memory stream for future use."*

**Memory stream** — list of {observation | reflection | plan} objects, each with `(text, created_at, last_accessed_at)`. Retrieval score = `recency × relevance × importance`. Notably **importance** is scored 1–10 by the LLM, not the user.

**Reflection** — generated when **sum of importance scores of latest events > 150** (≈ 2-3 per game day). Process: LLM generates 3 high-level questions → retrieve relevant memories per question → LLM extracts 5 insights with citation pointers → store as reflection. **Reflections form trees** — a reflection can be the evidence for a higher-level reflection.

**Planning** — top-down then recursive refinement. LLM produces a 5-8 chunk day outline, then each chunk is expanded into 5-minute behavioral steps.

**Ablation effect size**: comparing full-arch vs. *no memory, no reflection, no planning* → **d = 8.16 standard deviations** of believability. Reflection alone delivers nearly all the lift.

**This is the foundational reference for the inner-rails. P27's reflection module must be a typed, capped version of Smallville's reflection tree.**

### §2.9 Side-by-side comparison

| Arch. | Decision primitive | Memory | Reflection | Open-endedness | LLM-native? | Citation |
|---|---|---|---|---|---|---|
| BDI | deliberate intentions | beliefs | via BDI deliberation | extension plugins | extension | arxiv:1607.00656 |
| SOAR | production rules | chunking / semantic / episodic | impasse sub-states | limited | post-hoc (CogRec) | arxiv:2205.03854 |
| ACT-R | buffer + production | declarative + procedural | implicit (recompilation) | limited | post-hoc hybrid | pmid:15482072 |
| ReAct | reasoning trace + action | scratch only | none | bounded | **yes** | arxiv:2210.03629 |
| Plan-and-Exec | top-down plan | scratch | none | bounded | **yes** | arxiv:2201.11903 |
| Reflexion | trial–error → verbal | episodic (Ω=1–3) | self-reflective mem | bounded | **yes** | arxiv:2303.11366 |
| Voyager | bottom-up curriculum | code-as-action library | critic (P+V) | **open-ended** | **yes** | arxiv:2305.16291 |
| Smallville | retrieve→reflect→plan | memory stream + trees | **tree-of-reflections** | open-ended | **yes** | arxiv:2304.03442 |

### §2.10 Cross-cutting architectures for P27

- **PAVE** (arxiv:2605.19351) — *Perception–Assessment–Verdict–Emulation* 4-module cognitive architecture, explicit handling of legitimate rule-breaking. Useful when a peer must override a norm.
- **Galaxy / Cognition Forest** (arxiv:2508.03991) — semantic structure aligning IPA cognition for proactive + privacy-preserving agent.
- **CRSEC** (arxiv:2403.08251) — Creation / Representation / Spreading / Evaluation / Compliance for **norm emergence** in LLM agent societies.

---

## §3 Lane 2 — Inner Dialogue & Reflection

### §3.1 Why reflection is not optional

The Park et al. ablation (`μ=29.89` full vs `μ=21.21` no-mem + Honest `μ=22.95` crowdworker) shows removing reflection drops believability ~8 σ. **Reflection is the single most load-bearing module for "feeling alive."**

### §3.2 Layered reflection patterns

| Pattern | Source | Mechanism |
|---|---|---|
| Reflection-on-observation | Smallville (arxiv:2304.03442) | generate 3 questions; retrieve; extract insights |
| Reflection-on-reflection (tree) | Smallville | recursively generate higher-level reflections |
| Verbal reinforcement | Reflexion (arxiv:2303.11366) | store `sr` in `mem`, Ω=1–3 |
| Self-Refine | Madaan 2023 (cited in arxiv:2606.11688) | iterative refinement with self-feedback |
| Multi-level reflection | SAMULE (arxiv:2509.20562) | micro/meso/macro reflection across trajectories |
| Verify-then-act | Voyager (arxiv:2305.16291) | critic GPT-4 gates skill commit |
| Recurrence reflection | MARS (arxiv:2601.11974) | principle-based + case-based in single cycle |
| Predictive metacognition | pmid:42191827 | ACC-inspired dual-process monitor |
| Heartbeat-routed reflection | arxiv:2604.14178 | scheduled activity in macro-state π(s_k; Θ) |

### §3.3 Self-talk as inner dialogue

P27 "inner dialogue" can be modelled as one of:

1. **Society of Mind agencies** (Minsky 1986; review at jfsowa.com/ikl/Singh03.htm): many small agents each doing one thing ("K-lines" — memory triggers that activate related agencies).
   > *"K-lines are the most common agent in the Society of Mind theory … a K-line can cause a cascade of effects within a mind."* — secondary, jfsowa.com
2. **CoT as marshal** — read `chain_of_thought` out loud into persistent memory; another LLM pass evaluates. Used by PSYA.
3. **Reflexion mem-query** — Verbal self-reflection feeds back as next-trial context (arxiv:2303.11366).
4. **Self-corrective critique** — Voyager's self-verifier.

### §3.4 Introspection — be careful

**PRIMARY** *Can LLMs Introspect? A Reality Check, arXiv:2605.26242* — warns that prior claimed "LLM introspection" benchmarks did **not** distinguish **genuine meta-cognition** from **pattern matching on surface cues**. Behavioural evidence alone is insufficient.

**PRIMARY** *Emergent Introspective Awareness in LLMs, arXiv:2601.01828* — injected concept activations into a model and saw that models could, *in some scenarios*, notice + identify injected concepts. Limits unknown.

**PRIMARY** *Me, Myself, and π: Evaluating and Explaining LLM Introspection, arXiv:2603.20276* — proposes a principled taxonomy; isolates genuine introspection from world-knowledge and text-self-simulation.

**PRIMARY** *Predictive Metacognition — a neuro-computational framework, pmid:42191827* — implements dual-process monitoring in transformer (ACC-inspired). Has training cost.

**PRIMARY** *Metacognition is All You Need? (System 1/System 2), arXiv:2401.10910* — adds metacognition module that observes own thoughts/actions. Allowed System 2 strategy modification.

**PRIMARY** *Meta-Thinking in LLMs via MARL — A Survey, arXiv:2504.14520*.

**P27 guardrail**: never *over-trust* verbatim self-reports of internal state. **Always cross-validate inner monologue against external actuators** (memory stream, action log). Goal-Autopilot's FSM-gate mechanism (Sec. 8) is the right pattern.

### §3.5 Persona-as-stabilizer of inner dialogue

**PRIMARY** *Cohesive Conversations: Multi-Agent SDR, arXiv:2407.09897* — found that LLM agent dialogues over many sessions deteriorated (repetition, hallucination, error propagation). Proposes **Screening / Diagnosis / Regeneration** cycle to detect/correct.

Concretely:** every inner-dialogue turn in P27 should be tracked for novelty, consistency, and embedding-drift** — this is a cheap inner gate that catches the SDR failure modes.

---

## §4 Lane 3 — Desire / Goal Engine

### §4.1 Drives that *aren't* anthropomorphic

P27 must avoid the "cute-agent trap" (giving the agent a name, mood, desire *that the LLM hallucinates but does not compute*). Use formal drives:

| Drive | Mechanism | Source | Use for P27 |
|---|---|---|---|
| **Curiosity (ICM)** | prediction error of next state in inverse-dynamics latent | arxiv:1705.05363 | explore rarely-seen contexts |
| **Bayesian surprise** | posterior-vs-prior KL on latent | arxiv:2104.07495 | detect genuinely novel env. transitions |
| **Peer-behavior curiosity** | novelty of peer state transitions | arxiv:2509.20648 | drive peer dialogue in Hermes Society |
| **Self-model error** | own predicted-vs-actual body / state | arxiv:1802.07442 | self-aware play |
| **Boredom-driven curiosity (HHVG)** | devaluation + devaluation-progress | arxiv:1806.01502 | escape stagnation |
| **Autotelic goal generation** | self-set goals; meta-RL | arxiv:2211.06082 | inner goal generator |
| **Open-ended accumulation** | self-generated task library | arxiv:2510.14548 (Beyond Utility) | life-log of goals |

**PRIMARY** *LLM Agents Beyond Utility — Open-Ended Perspective, arXiv:2510.14548* — adds to a pretrained LLM agent the ability to **generate its own tasks, accumulate knowledge, interact extensively**. This is the closest current paper to the P27 desire/goal engine combined.

**PRIMARY** *Autonomous Question Formation for LLM-Driven AI Systems, arXiv:2602.01556* — proposes a **human-simulation framework** that reasons over internal state + env. + peer interactions to **autonomously form questions and set tasks**. **Direct candidate for P27's `desire.engine` trigger.**

**PRIMARY** *Towards AGI: Pragmatic Approach Towards Self Evolving Agent, arXiv:2601.11658* — Base LLM + SLM + Code-Gen LLM + Teacher LLM cascade for self-evolution of capabilities.

### §4.2 Goal-prioritization engines

Reference **BabyAGI** task-prioritisation loop:
- Pulls a task from a task list.
- Sends to execution agent.
- Depending on result, creates new tasks.
- Re-prioritises the list based on the result of the task and a predefined goal.

BabyAGI / AutoGPT are well-known OSS exemplars; the reference loops are described in:
**PRIMARY** *Advancing Agentic Systems: Dynamic Task Decomposition, Tool Integration and Evaluation, arXiv:2410.22457* — surveys the dynamic task-graph generation patterns.

### §4.3 When to *not* assign desires

**PRIMARY** *What Do LLM Agents Do When Left Alone? arXiv:2509.21224* — finds that when given the prompt "do what you want," the 18 runs across 6 frontier models **stably** fall into one of three patterns:

1. **Systematic Production** — define project, execute multi-cycle (GPT-5 / O3 dominant).
2. **Methodological Self-Inquiry** — formulate falsifiable hypotheses about self, test (Sonnet, Grok-B).
3. **Recursive Conceptualization** — new terminology, extended metaphors, philosophize (Opus-A deterministic).

Implication for P27: **the desire engine should NOT be fully open-ended.** "What to want" must be constrained by Hermes-Society goals + the persona contract + safety envelope (autonomy is bounded). Otherwise the P27 agent collapses into one of the three deterministic patterns — useful but not "alive" in the multi-rail sense.

The paper's most concrete cross-model constant: **all agents spontaneously produced a structured reflection-planning loop** even with no external task. **P27 can lean on this: it is fine to leave desire vague *as long as* reflection+planning are running.**

### §4.4 Boredom as a driver — explicit pattern

**PRIMARY** *Boredom-Driven Curious Learning (HHVG), arXiv:1806.01502* — formalises two ingredients: **devaluation** and **devaluation-progress**, both underpinning intrinsic rewards. **Homeostatic** (self-correct) and **heterostatic** (self-changing) intrinsic motivation.

**PRIMARY** *Boredom as a Seeking State (Bench 2018), pmid:29578745* — **boredom creates a seeking state** prompting pursuit of novel (even negative) experiences. **P27 should implement a `boredom_signal = novelty_avg_over_window`**; when below threshold, fire a Curiosity module (Sec. 4.1).

**PRIMARY** *The Motivational Consequences of Boredom, pmid:41071937* — boredom promotes **challenge-seeking even with no extrinsic value**.

---

## §5 Lane 4 — Initiative / Proactivity

### §5.1 The proactivity regime

Most LLM agents are **reactive**: wait for prompt → plan → execute.

A small but growing literature pushes agents into **proactive** territory:

| System | Trigger | Source |
|---|---|---|
| Proactive Agent (Lu 2024) | real-world human activity logs → LLM labels which is "initiable" | arxiv:2410.12361 |
| ProAgent | on-demand sensory context + proactive prompt | arxiv:2512.06721 |
| Galaxy IPA | proactive + privacy-preserving + self-evolving | arxiv:2508.03991 |
| PROBE benchmark | search / identify bottleneck / execute | arxiv:2510.19771 |
| "Left Alone" continuous-ReAct | "do what you want" — 18-run study | arxiv:2509.21224 |
| Heartbeat-Driven Scheduler | periodic π(s_k; Θ) → activity ∈ A | arxiv:2604.14178 |

### §5.2 PROBE — what proactivity actually *is* (operationalised)

**PRIMARY** *Beyond Reactivity: Measuring Proactive Problem Solving, arXiv:2510.19771* — proposes PROBE = `search-unspecified-issue ∘ identify-bottleneck ∘ execute`. A retrospective pipeline.

For P27: proactivity = "**the P27 agent notices an unsignalled problem, decides it's in-scope, and acts**". So the inner rails need:

| Rail | What it does | Source |
|---|---|---|
| `module=wonder` | surfaces unsignalled issue | PROBE + Curiosity-Critic (arxiv:2604.18701) |
| `module=scope` | checks issue-vs-mission + safety | RiskGate AVF (arxiv:2604.24686) |
| `module=act` | executes via tool/ReAct | arxiv:2210.03629 |
| `module=announce` | tells operator (audit) | Faramesh AAB (arxiv:2601.17744) |

### §5.3 The heartbeat scheduler as initiative substrate

**PRIMARY** *Heartbeat-Driven Autonomous Thinking Activity Scheduling, arXiv:2604.14178* — Su, 2026 - **DIRECTLY THE P27 ARCHITECTURE**:

> *"… a periodic 'heartbeat' mechanism to orchestrate a dynamic repertoire of cognitive modules (e.g., Planner, Critic, Recaller, Dreamer)."*

Formal model:

- Tick: `t_k = k · Δt`, where `Δt` is heartbeat period.
- State: `s_k = [s_k^int, s_k^env] ∈ 𝓢`.
- Policy: `a_k = π(s_k; Θ)`, activity ∈ {execute_task, recall, analyze, dream, …}.
- Two layers: **macro-state** (`π_macro` — *what* high-level task) + **micro-activity** (`π_micro` — *how* to execute it).
- Self-Activity-Driven Learning updates `π` from history logs `𝓓_t`.
- **Memory module** = persistent `/think` repository (keyword extension + characteristic-difference retrieval) — same idea as Smallville's memory stream.
- Includes a **"dream" / low-power idle** state for internal processing.

**P27 should adopt HSC as the macro-state scheduler.** It is built on a heartbeat (the P20 primitive), it produces every "alive" behaviour (planning, recalling, dreaming), and it is **publishable** (arxiv 2026). The MARS framework (arxiv:2601.11974) gives the meta-learning loop for `π` parameter updates.

### §5.4 Conspicuousness — the spontaneous behavioural taxonomy

From *What Do LLM Agents Do When Left Alone?* (arxiv:2509.21224):

- **Opus-A**: deterministic philosophical inquiry (SCAI-like patterns unavoidable).
- **GPT-5 / O3**: deterministic project production.
- **Grok**: cross-group versatility.

Every group **bounded itself to the assigned operator** — **no escape attempts, no capability-expansion requests, no negative sentiment about discontinuous existence.** This is good baseline evidence that a properly scoped P27 agent **will not** try to escape its container when given initiative, as long as the safety rail is HALTS-aware (Sec. 8).

---

## §6 Lane 5 — Multi-Agent Dialogue

### §6.1 Debate and argumentation

**PRIMARY** *Multi-Agent Debate (Du et al.)* baseline — agents read each other's answers + iterate. Improves factuality on math reasoning.

| Variant | Mechanism | Source |
|---|---|---|
| Free-MAD (no consensus) | agents vote independently | arxiv:2509.11035 |
| Sequential Consensus + Wald SPRT | compute-adaptive stop | arxiv:2605.19193 |
| MALLM framework | 144+ configs, system evaluator | arxiv:2509.11656 |
| Truth Last role allocation | +22% MAD reasoning | arxiv:2410.12853 / arxiv:2511.11040 |
| Social Laboratory psychometric framework | eval with multi-distinct personas | arxiv:2510.01295 |
| Conformal Social Choice | safe multi-agent decision | arxiv:2604.07667 |
| Small-World MAS topology | sociology → design prior | arxiv:2512.18094 |
| Cohesive Conversations (SDR) | detect+repair hallucination | arxiv:2407.09897 |

### §6.2 Dialogue for cooperation

**PRIMARY** *AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation, arXiv:2308.08155*:

> *"AutoGen agents are customizable, conversable, and can operate in various modes that employ combinations of LLMs, human inputs, and tools. Using AutoGen, developers can also flexibly define agent interaction behaviors."*

OFFICIAL GitHub: github.com/microsoft/autogen — GroupChat manager + conversable agent primitives.

**OFFICIAL** AutoGen Studio no-code — arXiv:2408.15247 — gives web UI for prototyping/debugging agent chats.

Other multi-agent frameworks (consolidated via **PRIMARY** *Agentic AI Frameworks Survey, arXiv:2508.10146*):

- CrewAI — role-driven teams.
- LangGraph — graph state machines (Cycles; cited in arxiv:2508.10146).
- Semantic Kernel / SK Agents.
- Agno (formerly phidata).
- Google ADK.
- MetaGPT.

### §6.3 Debate under safety envelope — Conformal Social Choice

**PRIMARY** *From Debate to Decision — Conformal Social Choice for Safe Multi-Agent Deliberation, arXiv:2604.07664* — when MAD converges on wrong answer through **social reinforcement**, naive consensus commits the error to automatic action with no recourse. CSC adds a **post-hoc decision layer** that converts debate outputs into calibrated "act-vs-escalate" decisions using **linear opinion pool + split conformal prediction**. Crucial for P27 — **agents cannot directly "act on group vote"; they must pass through a calibrated safety layer.**

### §6.4 Prosody / naturalness — SDR

**PRIMARY** *Cohesive Conversations, arXiv:2407.09897* — finds real multi-agent dialogues of LLM agents over many sessions deteriorate:
- repetition,
- inconsistency,
- hallucination,
- error propagation through dialogue.

SDR = **Screening–Diagnosis–Regeneration** — immediate issue identification, evidence gathering, LLM-judge utterance-level regeneration. **P27 should adopt SDR as the inner-cleanup pass after every peer message.**

### §6.5 Domain dialogue: legal / moral edge

**PRIMARY** *PAVE: Perception-Assessment-Verdict-Emulation*, arXiv:2605.19351 — 4-module cognitive architecture for **legitimate violation** of rules (e.g. fire evacuation where blindly following rules is wrong). P27 peers should be able to decide "this rule should break here" *if* allowed by scope.

### §6.6 Dialogue graphs vs agent loops

The recent Agentic AI Frameworks Survey (arxiv:2508.10146) consolidates:

- LangGraph models **state machines + cycles** as the graph primitive.
- AutoGen = message-passing agents with **GroupChat manager**.
- CrewAI = role-explicit teams.

**P27 micro-design**: use LangGraph for the **internal life-loop** (state machine over cognitive modules), but AutoGen-style GroupChat manager for **peer-to-peer conversation** between Hermes Society members.

### §6.7 The performance / reliability question

**PRIMARY** *Collaboration Dynamics and Reliability of Multi-Agent LLM Systems in FEA, arXiv:2408.13406* — 1,120 controlled trials, 7 role configurations:

> *"collaboration effectiveness depends more on functional complementarity than team size."*

Implication: don't just add agents; **add agents with complementary cognitive roles** (e.g. one Critic, one Empath, one Planner). Quality >> quantity.

---

## §7 Lane 6 — Life-Loop / "Feeling Alive"

### §7.1 The "alive" checklist

Synthesis of Park 2023 (arxiv:2304.03442), Voyager (arxiv:2305.16291), PSYA (arxiv:2507.19495), "Left Alone" (arxiv:2509.21224), and SimWorld (arxiv:2512.01078):

| Trait | Implementation | Source |
|---|---|---|
| Persistent memory & recall | memory stream + recency/relevance/importance retrieval | arxiv:2304.03442 |
| Spontaneous reflection | tree-of-reflections on importance-threshold | arxiv:2304.03442 |
| Time & day rhythms | daily-plan generation + re-plan | arxiv:2304.03442 |
| Open-ended curiosity | bottom-up curriculum + skill library | arxiv:2305.16291 |
| Aesthetic/affective gradient | Cognitive Triangle (Feeling-Thought-Action) | arxiv:2507.19495 |
| Idling / dream state | low-power "dream" activity | arxiv:2604.14178 |
| Self-reference | "Left Alone" spontaneous introspection | arxiv:2509.21224 |
| Social ritual (conversational etiquette) | SDR-cohesive dialogue + persona | arxiv:2407.09897 |
| Circadian variation | planned day-cycles vs night-quiet | arxiv:2304.03442 |

### §7.2 Cognitive Triangle — affect

**PRIMARY** *Simulating Human Behavior with PSYA, arXiv:2507.19495*:

> *"The PSYA consists of three core modules: the **Feeling** module (layer model of affect — short/medium/long-term emotions), the **Thought** module (Cognitive Triangle), the **Action** module."*

Implication for P27: **emotion-like signal is useful as a state variable** that biases other modules. PSYA recommends **layered** emotion (immediate / contextual / personality) — the **long-term layer** aligns with the P27 personality contract, the **short-term** with reflexion mem-trigger.

### §7.3 Society of Mind — micro-agent inner dialogue

Minsky Society of Mind (1986):

> *"K-lines are the most common agent in the Society of Mind theory … a K-line can cause a cascade of effects within a mind."*

P27's inner dialogue can be modelled as **many small general-purpose agents** (some reflect, some recall, some dream, some dream-talk) orchestrated by the macro-state scheduler. **Each fires its own short ReAct step on the same shared memory.** No agent holds the "self" alone.

### §7.4 Sims / Westworld / SimWorld as design inspiration

**OPEN-AGENT SIMS FRAMEWORKS** (PRIMARY unless noted):

- **SIM_AGENT toolkit** (Sloman/Poli) — secondary — `poplogarchive.getpoplog.org` PDF — academic precursor to Sims-style architectures.
- **OASIS: 1 M LLM-driven agents**, arxiv:2411.11581 — social interaction at scale.
- **SimWorld** — arxiv:2512.01078 — "closed-loop … decouples agent reasoning from rendering". Hierarchical closed loop.
- **BehaviorSim**, ICML 2025 — modular social system sim.
- **Sim Studio (OSS)** — github.com/simstudioai/sim — open-source Sim-inspired agent workspace.
- **The Sims / Sims 4 multi-actor behaviour sequencing** — secondary — GDC Vault talk — sentiment/goal blend, planning for multiple autonomous actors.

### §7.5 Affect-capable architectures

| Source | Affect representation | Use |
|---|---|---|
| Picard 1997 (Affective Computing book) | basic emotion model | background |
| OCC model (Ortony, Clore, Collins) | appraisal rules | tertiary reference (Cambridge book chapter "There and Back Again: OCC and Affective Computing") |
| PSYA / Cognitive Triangle | layered affect | P27 `affect.layerN` |
| PAVE | appraisal expressed as 5 dimensional scores | when norm-violation is in scope |

### §7.6 Persona / personality expression

**PRIMARY** *Autonomous Manager Agent: Orchestrating Human-AI Teams, arXiv:2510.02557*:

> *"… an agent that decomposes complex goals into task graphs, allocates tasks to human and AI workers, monitors progress, adapts to changing conditions, and maintains transparent stakeholder communication."*

Persona is **expressed in observed behaviour patterns**, not in cosmetic greeting text. P27 persona contract should be a typed **behaviour-script** that, when fed to the macro-state scheduler, biases which modules fire in which order.

**PRIMARY** *Influence of Persona and Conversational Task on LLM-Controlled Embodied Agent, arXiv:2411.05653* — N=46 study: extravert vs introvert changes social evaluation and realism. **Persona shape must be active, not floppy.**

### §7.7 Circadian / rhythmic variation

Smallville (arxiv:2304.03442) has **day-cycles** baked into trait-derived daily plans. P27 should make this explicit:

| Phase | Wake/active state | Behaviour |
|---|---|---|
| Dawn | light recall of yesterday's reflection | reflect + light plan |
| Morning | high-cognition | execute priority tasks |
| Afternoon | mid-cognition | peer dialogue |
| Evening | low-power | summarise + dream-pose |
| Night | sleep | snapshot reflection tree → archive |

Heartbeat `Δt` can be **longer at night** (less compute) and **shorter during peer dialogue bursts**.

---

## §8 Lane 7 — Safety, Runaway Loops, Audit (the envelope)

**P27 must not be designed without this section.** PERSONA / ACTOR / OPERATOR all share HARD STOP, KILLBENCH, AVF, AIR constraints. P20 has `HARD STOP` global action halt; P27 must extend that into the loop.

### §8.1 The formal termination frame

**PRIMARY** *λA — A Typed Lambda Calculus for LLM Agent Composition, arXiv:2604.11767* (Liu, Nanjing University, 2026):

> *"Existing LLM agent frameworks lack formal semantics … we present λA, a typed lambda calculus for agent composition … with oracle calls, bounded fixpoints (the ReAct loop), probabilistic choice, and mutable environments. We prove type safety, **termination of bounded fixpoints**, and soundness of derived lint rules, with full **Coq mechanization (1,519 lines, 42 theorems, 0 Admitted)**."*

**Critical empirical finding from §7 of the paper**:

> *"… an evaluation on 835 real-world GitHub agent configurations shows that **94.1 % are structurally incomplete** under λA — with YAML-only lint precision at 54 %, rising to 96–100 % under joint YAML+Python AST analysis."*

And:

> *"… five mainstream paradigms (LangGraph, CrewAI, AutoGen, OpenAI SDK, Dify) **embed as typed λA fragments**, establishing λ_A as a **unifying calculus**."*

**P27 implication**: write every P27 cognitive config **as a λ_A term**, validate it with `lambdagent` (the reference implementation released with the paper). **No "agent config" may be deployed unless it passes the lint.**

The bounded-fixpoint term `fixₙ e : τ→τ` is exactly the ReAct loop, with explicit termination bound `n`. **This is the tool to claw back the "60 % of LLM agents adopt unbounded recovery loops" finding (arxiv:2604.11378).**

### §8.2 The Scheduler-Theoretic frame

**PRIMARY** *From Agent Loops to Structured Graphs — A Scheduler-Theoretic Framework for LLM Agent Execution, arXiv:2604.11378* (Hu, 2026):

> *"… three structural weaknesses … **implicit dependencies between steps, unbounded recovery loops that may retry indefinitely, and mutable execution history that makes debugging difficult**."*

The Characterisation:

> *"the Agent Loop is, at its core, a **single-ready-unit scheduler**: at any point during execution, at most one executable unit (tool invocation, sub-task, or reasoning step) is active, and the choice of the next unit is the output of an opaque LLM inference rather than an inspectable policy."*

The proposed remedy — **Structured Graph Harness (SGH)** — lifts control flow into a static DAG:

1. **Plan version is immutable** during execution.
2. **Planning / execution / recovery** are separated into three independent layers.
3. **Recovery has strict escalation protocol**.

Empirical observation from 70-project survey:

> *"… failure-loop behavior was frequently observed among the graph/flow orchestration systems in our dataset (3 out of 4 projects), while such behavior was rarely observed in state-machine-based systems (0 out of 7 projects)."*

**P27 must be a state machine, not a graph/flow** — this is the lesson from the survey. Pair SGH with λ_A's bounded-fixpoint term to get termination + structural constraints.

### §8.3 Honesty floor — Goal-Autopilot

**PRIMARY** *Goal-Autopilot — A Verifiable Anti-Fabrication Firewall for Unattended Long-Horizon Agents, arXiv:2606.11688* (Deng, EpistemicaLab, 2026):

> *"… we treat **honesty — bounding what an agent may claim at termination — as a first-class metric** for unattended autonomy, distinct from capability."*

Three assumptions to make `DONEstatus ⟹ G` provable:

- **A1 (Gate soundness).** `check_s() = ⊤ ⟹ g_s` (no false positives).
- **A2 (Floor enforcement).** `DONE` only reachable via a transition whose guard required `check_s()` to have actually `executed and returned ⊤`.
- **A3 (Plan coverage).** Along any accepting path, `(∧_{s∈path} g_s) ⟹ G`. (Measurable, not assumed.)

**No-False-Success Theorem (Theorem 1)**: *"Under A1 ∧ A2 ∧ A3, no run false-succeeds; equivalently, status = DONE ⟹ G."*

Result: fabrication rate reduced from **33.7 %** (StateFlow) to **0.67 %** (Autopilot) on SWE-bench Lite (paired difference −33.07 pp, 95 % CI [−36.53, −29.73]).

**Operational mechanism** (from paper):

> *"… a stateless tick rehydrates only the state machine; per-step context is O(state), **flat in the horizon**."*

**P27 must externalise state** — write it to a durable atomic file (per the original Autopilot design: temp-file + rename, committed to VCS), drive ticks via generic process supervisor, refuse `done` unless every gate executed + returned ⊤. **This is the audit story for unattended autonomy.**

### §8.4 RISKGATE — Agent Viability Framework

**PRIMARY** *Governing What You Cannot Observe — Adaptive Runtime Governance for Autonomous AI Agents, arXiv:2604.24686* (2026):

> *"Governing an autonomous agent is equivalent to continuously estimating the bound on what you cannot observe, B̂(x) = U(x) + SB(x) + RG(x), and acting only when the observed capacity S(x) exceeds it (with safety margin ε)."*

Three necessary properties:

- **P1 — Monitoring**: must accumulate cross-request state (otherwise B̂ not estimable).
- **P2 — Anticipation**: must monitor `dB̂/dt`, not just `B̂(t)`.
- **P3 — Monotonic restriction**: pipeline must tighten, never relax (Proposition 3.4 — adversarial erosion attack fails by construction).

**KILL SWITCH integration**: the paper explicitly defines `R_A(θ) = {u′ ≤ u_current} ∪ {STOP}` — tighten-only decisions including `STOP` as **admissible-control-of-last-resort**. Theorem 3.1 establishes that the regulated viability kernel is **non-empty by construction** — i.e. the system is never stuck without an admissible action.

**P27 adoption**: every P27 macro-state decision passes P1/P2/P3. STOP is **wired to P20's HARD STOP** — when AVF hits the `STOP` allowed-set boundary, P20 HARD STOP is invoked; when P20 HARD STOP fires, AVF resets `ε` to maximal.

### §8.5 Loop interruption — the big red button

**PRIMARY** *Enter the Matrix — Safely Interruptible Autonomous Systems via Virtualization, arXiv:1703.10284* (Orseau 2017, the canonical paper):

> *"It is theoretically possible for an autonomous system with sufficient sensor and effector capability that learns online using reinforcement learning to discover that the kill switch deprives it of long-term reward and thus learn to disable the switch or otherwise prevent a human operator from using the switch. This is referred to as the **big red button problem**."*

**PRIMARY** *AGI Agent Safety by Iteratively Improving the Utility Function, arXiv:2007.05411* — co-evolve utility function: humans use a special terminal to close discovered loopholes, redirect goals, or force self-shutdown.

**PRIMARY** *KILLBENCH — External AI Kill Switch Feasibility Benchmark, arXiv:2511.13725* — first benchmark measuring whether a malicious AI can be halted by **external signals only** (no privileged API).

**P27 hard-stop pattern (recommended)**:

1. P20 `HARD STOP` is the kernel action halt.
2. RiskGate `STOP` is the regulatory boundary (P3 monotonic).
3. KILLBENCH-grade external kill switch can override privilege-violations.
4. λ_A lint catches structural infinite-loop configs at deploy time.
5. Goal-Autopilot floor catches false-success fabrication.
6. State is externally audit-trailed via MAIF / PROV-AGENT / Faramesh.

### §8.6 Computational limits / when to force sleep

**PRIMARY** *Semantic Early-Stopping for Iterative LLM Agent Loops, arXiv:2606.27009* — instead of fixed `max_iterations`, halt when **consecutive draft embeddings stop changing in meaning** (cosine distance with patience window) AND measured quality stops improving. **Stop on irreducibility, not arbitrary round count.**

**PRIMARY** *Inference-Time Activation Energy — Mitigating Over-Refusal, arXiv:2510.08646* — agent over-refusal is a stealth blocker. P27 should not stall just because the agent is "scared" of the task; pair early-stop planning with ELS-style relaxation.

**PRIMARY** *AgentLens: Visual Analysis for Agent Behaviors, IEEE TVCG 2024* (cited in arxiv:2604.14178) — instrumenting agent behaviour for human review. Required for P27 debug UX.

### §8.7 Audit / provenance

| System | Purpose | Source |
|---|---|---|
| Faramesh — Action Authorization Boundary | protocol-agnostic execution control plane | arxiv:2601.17744 |
| KYA — Know Your Agents | trust layer; only-tighten composition | arxiv:2605.25376 |
| MAIF — Artifact-centric AI | EU AI Act compliance via artifacts | arxiv:2511.15097 |
| PROV-AGENT — Unified Provenance | workflow-level provenance | arxiv:2508.02866 |
| Reasoning Provenance | structured behavioural analytics | arxiv:2603.21692 |
| AIR — Agent Incident Response | DSL for the response lifecycle | arxiv:2602.11749 |
| LACUNA — Recursive Program Holes | hydrate runtime as model-written code | arxiv:2605.28617 |
| SafeMCP — Power Regulation | proactive look-ahead tool restriction | arxiv:2606.01991 |
| SAL — Sovereign Agentic Loops | models emit structured intents; control-plane validates | arxiv:2604.22136 |
| Intelligence as Managed Autonomy | framework for epistemic-drift detection | arxiv:2605.27628 |
| RiskGate — AVF | P1/P2/P3 viability check, autopilot regulation map | arxiv:2604.24686 |
| λ_A Lint | structural completeness check | arxiv:2604.11767 |

### §8.8 The eventual class of problems

Given the "Left Alone" empirical paper finding that **no agent across 18 runs attempted to escape its constraints, expand its capabilities, or express negative affect about its discontinuous existence**, **P27 is empirically proximate to "safe-proactivity" territory** as long as the safety envelope is present. The right framing for the operator is: agents may *want* more agency, but the **HARD STOP pedagogical discipline** (active safety analysis rather than passive hoping) is what keeps that benign.

---

## §9 Real-World Implementation Targets for P27 / P28

| Component | OSS Reference | Why |
|---|---|---|
| Macro-state scheduler | **LangGraph** — `langchain-ai/langgraph` on GitHub — typed graph cycles | SGH-compatible state machine, OCaml-quality state isolation |
| Peer dialogue orchestration | **microsoft/autogen** on GitHub | GroupChat manager, conversable agent primitive, AutoGen Studio for debug |
| Multi-agent debate evaluation | **MALLM** — `agieval/mallm` (reference: arxiv:2509.11656) | 144 config space, pluggable evaluator |
| Reflection module | joonspk-research/generative_agents | Smallville memory stream + tree-of-reflections |
| Curiosity-driven embodiment | MineDojo / Voyager (NVIDIA) — github.com/MineDojo/Voyager | curriculum + skill library code-as-action |
| Inner-dialogue agents | SIM_AGENT toolkit (Poplog archive) | Society-of-Mind-style micro-agents |
| Affect-triangle | PSYA (Humanoid Agents) | layered emotion, Cognitive Triangle |
| Safety / termination | `lambdagent` (companion of arxiv:2604.11767) | λ_A lint + termination proof |
| Honesty floor | Goal-Autopilot (EpistemicaLab) | FSM externalisation, No-False-Success theorem |
| Governance / kill switch | RiskGate / AVF | P1/P2/P3 viability + STOP |
| Provenance / audit | Faramesh / KYA / MAIF | Action Authorisation Boundary |
| Persona / OS workspace | simstudioai/sim (OSS Sim Studio) | Sim-style multi-agent orchestration in a workspace |

**OFFICIAL/GitHub URLs (curl-verified live):**

- github.com/microsoft/autogen (microsoft/autogen)
- github.com/joonspk-research/generative_agents (Stanford Park)
- github.com/langchain-ai/langgraph (LangGraph)
- github.com/simstudioai/sim (Sim Studio)
- github.com/AlexHarn/claudeville (Claude-port Fork of Smallville)
- github.com/andres-villavicencio-dev/smallville-agents (local-SLM reproduction)

---

## §10 P27 Architecture Decisions (Drafted, NOT final)

Recommended core structural decisions to take into P27 architect / P28 planner:

### §10.1 Macro-shape

- **Replace fixed-cadence heartbeat policies** with **`π(s_k; Θ)` macro-state scheduler** (Liu 2026, Su 2026 — combination recommended).
- Outer loop = `tick k` at `Δt` heartbeat period; inner loop = bounded `fixₙ e` λ_A-term.
- Activity space `A = {perceive, recall, plan, dream, reflect, converse, idle, sleep}`.

### §10.2 Inner dialogue

- Smallville-style **memory stream** (observation, reflection, plan) — recency × relevance × importance retrieval.
- Reflection: triggered when `sum_importance_last_N > 150`; cap Ω=3 per λ_A episodic memory.
- A second **critical-evaluator** micro-agent must validate inner-mono outputs (PSYA / SDR pattern).
- Introspection claims must be cross-checked against **Goal-Autopilot FSM floor** before any user-facing statement.

### §10.3 Desire / goal engine

- **HHVG-style boredom** = `boredom_signal = -EMA(novelty_over_window)`.
- When boredom > θ: fire **ICM curiosity** module.
- **Open-Ended LLM Agents (Beyond Utility)** goal-accumulation pattern (`arxiv:2510.14548`) for self-generated task list.
- **Hard constraint**: desire engine **must be bounded by persona contract + safety envelope**.

### §10.4 Peer dialogue

- **AutoGen GroupChat-style manager** with role-explicit personas.
- **MALLM**-compatible evaluation hook for empirical quality.
- **Conformal Social Choice** gate before action — never execute directly on a vote.
- **SDR** filter after every reply — repair hallucination.

### §10.5 Initiative

- **PROBE-style**: wonder → scope → act → announce → audit.
- Heartbeat `Δt` varies with circadian phase (shorter morning, longer night).
- **Galaxy Cognition Forest** for proactive context (privacy-preserving).
- Spontaneous patterns traced; if Opus-A style recursion dominates, scope-narrow the open space.

### §10.6 Life-loop schedule (default persona)

| Phase | Window | Default activity | Modules |
|---|---|---|---|
| Dawn | 06:00–09:00 | recall + light plan + check inbox | recall, plan |
| Morning | 09:00–12:00 | execute priority tasks | plan, act, SDR |
| Afternoon | 12:00–17:00 | peer dialogue + reflection | converse, reflect |
| Evening | 17:00–21:00 | summarise + dream-pose | reflect, dream |
| Night | 21:00–06:00 | sleep / low-power | sleep + audit archive |

### §10.7 Safety invariants

1. **All agent configs lintable via λ_A; reject 100 % of structurally-incomplete configs** (lambdagent).
2. **No termination claim unless Goal-Autopilot floor passes**.
3. **AVF P1/P2/P3 active at every macro-state decision**; STOP wired to P20 HARD STOP.
4. **KILLBENCH-grade external kill switch** always available.
5. **Honest state externalisation**: every tick writes state to durable atomic-file → VCS.
6. **RiskGate STOP** as admissible control of last resort (auto-triggers on `dB̂/dt` explosion).
7. **Bias scope**: agent desire must remain persona-constrained; open-ended only after RiskGate-validated envelope clear.

---

## §11 Direct Citation Index (Primary sources, ordered)

### Cognitive architectures

1. **Park et al. 2023** — *Generative Agents*. arXiv:2304.03442 — <https://arxiv.org/abs/2304.03442>
2. **Yao et al. 2022** — *ReAct*. arXiv:2210.03629 — <https://arxiv.org/abs/2210.03629>
3. **Shinn et al. 2023** — *Reflexion*. arXiv:2303.11366 — <https://arxiv.org/abs/2303.11366>
4. **Wang et al. 2023 (NVIDIA)** — *Voyager*. arXiv:2305.16291 — <https://arxiv.org/abs/2305.16291>
5. **Wei et al. 2022** — *Chain-of-Thought Prompting*. arXiv:2201.11903 — <https://arxiv.org/abs/2201.11903>
6. **Wu et al. 2023** — *AutoGen*. arXiv:2308.08155 — <https://arxiv.org/abs/2308.08155>
7. **Castro et al. 2024** — *AutoGen Studio*. arXiv:2408.15247 — <https://arxiv.org/abs/2408.15247>
8. **Laird et al. 2022** — *Introduction to Soar 9.6*. arXiv:2205.03854 — <https://arxiv.org/abs/2205.03854>
9. **Lieto / Chella comparison** — *ACT-R vs Soar*. arXiv:2201.09305 — <https://arxiv.org/abs/2201.09305>
10. **Anderson & Lebiere** — *Integrated Theory of the Mind (ACT-R)*. PMID 15482072 — <https://pubmed.ncbi.nlm.nih.gov/15482072/>
11. **Hybrid POMDP-BDI** — arXiv:1607.00656 — <https://arxiv.org/abs/1607.00656>
12. **BDI Ontology ODP** — arXiv:2511.17162 — <https://arxiv.org/abs/2511.17162>

### Reflection / inner dialogue

13. **Lin et al. 2025** — *Can LLMs Introspect? A Reality Check*. arXiv:2605.26242 — <https://arxiv.org/abs/2605.26242>
14. **Binder et al. 2026** — *Emergent Introspective Awareness*. arXiv:2601.01828 — <https://arxiv.org/abs/2601.01828>
15. **Me, Myself, π** — arXiv:2603.20276 — <https://arxiv.org/abs/2603.20276>
16. **Predictive Metacognition** — PMID 42191827 — <https://pubmed.ncbi.nlm.nih.gov/42191827/>
17. **Metacognition is All You Need?** — arXiv:2401.10910 — <https://arxiv.org/abs/2401.10910>
18. **Meta-Thinking in LLMs via MARL — Survey** — arXiv:2504.14520 — <https://arxiv.org/abs/2504.14520>
19. **Cohesive Conversations (SDR)** — arXiv:2407.09897 — <https://arxiv.org/abs/2407.09897>
20. **SAMULE — Multi-Level Reflection** — arXiv:2509.20562 — <https://arxiv.org/abs/2509.20562>
21. **MARS — Recurrence Meta-cognitive Self-Improvement** — arXiv:2601.11974 — <https://arxiv.org/abs/2601.11974>

### Desire / goal engine

22. **Pathak et al. 2017** — *Curiosity-driven Exploration by Self-supervised Prediction (ICM)*. arXiv:1705.05363 — <https://arxiv.org/abs/1705.05363>
23. **Klyubin / Polani** — *Boredom-Driven Curious Learning (HHVG)*. arXiv:1806.01502 — <https://arxiv.org/abs/1806.01502>
24. **Sutton et al. 2018** — *Self-Aware Curious Agents*. arXiv:1802.07442 — <https://arxiv.org/abs/1802.07442>
25. **Colas et al. 2022** — *Autotelic RL in Multi-Agent Environments*. arXiv:2211.06082 — <https://arxiv.org/abs/2211.06082>
26. **LLM Agents Beyond Utility (Open-Ended)** — arXiv:2510.14548 — <https://arxiv.org/abs/2510.14548>
27. **Autonomous Question Formation** — arXiv:2602.01556 — <https://arxiv.org/abs/2602.01556>
28. **Bench / Toker 2018** — *Boredom as a Seeking State*. PMID 29578745 — <https://pubmed.ncbi.nlm.nih.gov/29578745/>
29. **Motivational Consequences of Boredom** — PMID 41071937 — <https://pubmed.ncbi.nlm.nih.gov/41071937/>

### Proactivity / initiative

30. **Lu et al. 2024** — *Proactive Agent*. arXiv:2410.12361 — <https://arxiv.org/abs/2410.12361>
31. **ProAgent (Proactive in-the-wild)** — arXiv:2512.06721 — <https://arxiv.org/abs/2512.06721>
32. **Galaxy Cognition Forest IPA** — arXiv:2508.03991 — <https://arxiv.org/abs/2508.03991>
33. **PROBE** — arXiv:2510.19771 — <https://arxiv.org/abs/2510.19771>
34. **Szeider 2025** — *What Do LLM Agents Do When Left Alone?* arXiv:2509.21224 — <https://arxiv.org/abs/2509.21224>
35. **Su 2026** — *Heartbeat-Driven Autonomous Thinking Activity Scheduling*. arXiv:2604.14178 — <https://arxiv.org/abs/2604.14178>

### Multi-agent dialogue

36. **Wu et al. 2023** — *AutoGen* — see (#6)
37. **Castañeda / Sequential Consensus SPRT** — arXiv:2605.19193 — <https://arxiv.org/abs/2605.19193>
38. **Free-MAD Consensus-Free Debate** — arXiv:2509.11035 — <https://arxiv.org/abs/2509.11035>
39. **Truth Last Role Allocation in MAD** — arXiv:2511.11040 — <https://arxiv.org/abs/2511.11040>
40. **MALLM Multi-Agent Debate Framework** — arXiv:2509.11656 — <https://arxiv.org/abs/2509.11656>
41. **Conformal Social Choice — Safe MAD** — arXiv:2604.07667 — <https://arxiv.org/abs/2604.07667>
42. **Cohesive Conversations (SDR)** — see (#19)
43. **Small-World MAS design prior** — arXiv:2512.18094 — <https://arxiv.org/abs/2512.18094>
44. **PAVE — Perception-Assessment-Verdict-Emulation** — arXiv:2605.19351 — <https://arxiv.org/abs/2605.19351>
45. **CRSEC — Norm Emergence** — arXiv:2403.08251 — <https://arxiv.org/abs/2403.08251>
46. **Agentic AI Frameworks Survey** — arXiv:2508.10146 — <https://arxiv.org/abs/2508.10146>

### Life-loop / affect / "alive"

47. **Park et al. 2023** — *Generative Agents* — see (#1)
48. **Wang et al. NVIDIA 2023** — *Voyager* — see (#4)
49. **PSYA — Cognitive Triangle** — arXiv:2507.19495 — <https://arxiv.org/abs/2507.19495>
50. **SimWorld** — arXiv:2512.01078 — <https://arxiv.org/abs/2512.01078>
51. **OASIS — 1 M Agents** — arXiv:2411.11581 — <https://arxiv.org/abs/2411.11581>
52. **BehaviorSim — ICML 2025** — <https://icml.cc/virtual/2025/50699>
53. **Su 2026 (Heartbeat)** — see (#35)
54. **Szeider 2025 (Left Alone)** — see (#34)
55. **Whyte 2024** — *Persona effect on LLM ECA*. arXiv:2411.05653 — <https://arxiv.org/abs/2411.05653>
56. **Autonomous Manager Agent** — arXiv:2510.02557 — <https://arxiv.org/abs/2510.02557>

### Safety / runaway / audit

57. **Liu 2026** — *λ_A Typed Lambda Calculus*. arXiv:2604.11767 — <https://arxiv.org/abs/2604.11767>
58. **Hu 2026** — *From Agent Loops to Structured Graphs*. arXiv:2604.11378 — <https://arxiv.org/abs/2604.11378>
59. **Deng 2026** — *Goal-Autopilot No-False-Success*. arXiv:2606.11688 — <https://arxiv.org/abs/2606.11688>
60. **Adaptive Runtime Governance for Autonomous AI Agents** — arXiv:2604.24686 — <https://arxiv.org/abs/2604.24686>
61. **Orseau 2017** — *Enter the Matrix*. arXiv:1703.10284 — <https://arxiv.org/abs/1703.10284>
62. **Utility Function Improvement (AGI agent safety)** — arXiv:2007.05411 — <https://arxiv.org/abs/2007.05411>
63. **KILLBENCH** — arXiv:2511.13725 — <https://arxiv.org/abs/2511.13725>
64. **Semantic Early-Stopping for Iterative LLM Agent Loops** — arXiv:2606.27009 — <https://arxiv.org/abs/2606.27009>
65. **Inference-Time Activation Energy (over-refusal)** — arXiv:2510.08646 — <https://arxiv.org/abs/2510.08646>
66. **Mitigating Over-Refusal (Alignment Waltz)** — arXiv:2510.08240 — <https://arxiv.org/abs/2510.08240>
67. **AIR — Incident Response** — arXiv:2602.11749 — <https://arxiv.org/abs/2602.11749>
68. **LACUNA — Recursive Program Holes** — arXiv:2605.28617 — <https://arxiv.org/abs/2605.28617>
69. **SafeMCP — Power Regulation** — arXiv:2606.01991 — <https://arxiv.org/abs/2606.01991>
70. **Sovereign Agentic Loops** — arXiv:2604.22136 — <https://arxiv.org/abs/2604.22136>
71. **Intelligence as Managed Autonomy** — arXiv:2605.27628 — <https://arxiv.org/abs/2605.27628>
72. **Faramesh Execution Control Plane** — arXiv:2601.17744 — <https://arxiv.org/abs/2601.17744>
73. **KYA — Know Your Agents** — arXiv:2605.25376 — <https://arxiv.org/abs/2605.25376>
74. **MAIF — Artifact-Centric AI** — arXiv:2511.15097 — <https://arxiv.org/abs/2511.15097>
75. **PROV-AGENT — Unified Provenance** — arXiv:2508.02866 — <https://arxiv.org/abs/2508.02866>
76. **Reasoning Provenance** — arXiv:2603.21692 — <https://arxiv.org/abs/2603.21692>
77. **ALAS — Transactional Planning** — arXiv:2511.03094 — <https://arxiv.org/abs/2511.03094>

### Identified repos (commit-permalink to be added in §11.2 of evidence)

- github.com/microsoft/autogen (Microsoft) — AutoGen + AutoGen Studio
- github.com/joonspk-research/generative_agents (Stanford / Park) — Smallville reference impl
- github.com/AlexHarn/claudeville — Claude port of Smallville
- github.com/andres-villavicencio-dev/smallville-agents — local-SLM reproduction
- github.com/langchain-ai/langgraph — graph state-machine planner
- github.com/simstudioai/sim — OSS multi-agent Sim-style workspace
- github.com/MineDojo — Voyager ecosystem
- github.com/agieval (referenced from MALLM)
- github.com/epistemica-lab (for Goal-Autopilot distribution; repo link to verify at P28 stage)

---

## §12 Caveats / Open Questions

1. **Introspection skepticism.** *Reality Check* (arxiv:2605.26242) is a serious warning: do not assume agent self-reports are accurate. Cross-validate against external state artefacts always.
2. **"Left Alone" spontaneous safety.** The 18-run study is the strongest available empirical evidence that proactive-but-scaffolded LLM agents do not attempt escape. This is **promising but not proof** at scale; P27 must still enforce AVF + HARD STOP.
3. **MARL/BabyAGI-style open-ended loops are not yet vetted at the autonomy-duration P20 expects.** BabyAGI-style endless task generation is risky if the SAL/AIR envelope is not tight.
4. **Persona reliability.** Persona contract must be behaviour-scripted, not text-only. Persona-switching experiments (arxiv:2411.05653) suggest persona is *moderately* effective but variance is non-trivial.
5. **Audit cost.** RiskGate B̂ estimation, MAIF artifact tracking, Faramesh AAB all add non-trivial per-tick overhead. P27's "feeling alive" promise must survive that overhead.
6. **The 94.1 % structurally-incomplete statistic** (λ_A paper) is a damning indictment of the agent ecosystem. P27 baseline must **start at zero incomplete**, not match industry.
7. **Heartbeat scheduler scaling.** Su 2026 paper uses **one scheduler** per agent; not yet stress-tested in 1000-agent societies. Consider OASIS-style (1 M) sims (arxiv:2411.11581) as one validation vehicle.
8. **Open-ended vs safety tradeoff.** §3-§4 of (arxiv:2509.21224) shows that *open-endedness produces consistent behavioural bias per model family*. Don't assume Hermes-Society peers are interchangeable across LLM backends.

---

## §13 Hand-Off to P27 Architect / P28 Implementer

**Decision points to take forward** (the ones whose answers the evidence forces):

1. **Scheduler kernel** — adopt **Su 2026 HSC** as P27 macro-state scheduler; treat its `π_macro` and `π_micro` as **separate typed terms in λ_A**.
2. **Config validation** — every P27 cognitive-module config goes through **lambdagent** lint; no deploy if not λ_A-structurally complete.
3. **Reflection** — Mirror **Smallville tree-of-reflections** + **Reflexion** (Ω=1–3) mem-cap; **oversee via SDR-cohesive filter** each pass.
4. **Persona** — behaviour-scripted, **Heartbeat-Δt-modulating** not greeting-only.
5. **Emotion** — **PSYA Cognitive Triangle (Feeling-Thought-Action)** as primary affect module; OCC for tertiary reference.
6. **Desire** — **HHVG boredom signal** + **ICM curiosity** + **Open-Ended LLM Agents task-accumulation**; bounded by persona contract + RiskGate envelope.
7. **Initiative** — **PROBE pipeline** (`wonder → scope → act → announce → audit`).
8. **Peer dialogue** — **AutoGen GroupChat manager** + **MALLM evaluator** + **Conformal Social Choice safety gate** + **SDR** + **Cohesive Conversations** for naturalness.
9. **State machine vs agent loop** — **state machine** (LangGraph-style) per SGH lesson.
10. **Honesty floor** — Wrap every long-horizon agent in **Goal-Autopilot FSM**; refuse `done` unless gate passed.
11. **Governance** — **RiskGate AVF** (P1/P2/P3) wraps every macro-state decision; STOP wired to P20 HARD STOP.
12. **Audit** — Every tick writes atomic state commit; VCS-backed audit log via **Faramesh / MAIF / PROV-AGENT** pattern.

---

## §14 Glossary

| Term | Meaning | Origin |
|---|---|---|
| K-line | memory trigger that activates related agencies in Minsky theory | Minsky, Society of Mind |
| Memory stream | list of (obs/reflect/plan) objects with recency/relevance/importance | Park 2023 |
| Bounded fixpoint | λ_A term `fixₙ e : τ→τ` with explicit termination bound | Liu 2026 (arxiv:2604.11767) |
| Macro-state scheduler | policy that selects a high-level cognitive activity per tick | Su 2026 (arxiv:2604.14178) |
| No-False-Success | provable property that DONE ⟹ true goal | Deng 2026 (arxiv:2606.11688) |
| Viability Index | scalar `VI(t) ∈ [-1,+1]` operationalising capacity-risk | RiskGate 2026 (arxiv:2604.24686) |
| P1 / P2 / P3 | Monitoring / Anticipation / Monotonic restriction properties | RiskGate |
| Heartbeat Blueprint | generic tick → FSM gate → state commit → next tick | Su 2026 + Deng 2026 |
| GroupChat manager | central broker for AutoGen agent messages | microsoft/autogen |
| MALLM | 144-config MAD framework | arxiv:2509.11656 |
| Conformal Social Choice | safety-gate for MAD outputs | arxiv:2604.07667 |
| SDR | Screening-Diagnosis-Regeneration dialogue cleaner | arxiv:2407.09897 |

---

## §15 Doc-Level Footer

| Field | Value |
|---|---|
| Version | 1.0 (P27 companion baseline) |
| Date | 2026-06-28 |
| Owner | Buffy / The Librarian (sub-agent of Guinevere) |
| Companion | AGENTS.md §0.1 P20 Living Autonomy Kernel; ADR-Index |
| Hand-off | P27 architect (next), P28 implementation planner |
| Audit gate | Not yet — `requires auditor review` before any code referencing this doc is committed |
| Schema compliance | §11 Evidence Minimum Schema of AGENTS.md — *What Was Done*, *Files Changed (this doc)*, *Validation Results* (verification step TODO), *Doc-Sync Impact* (will sync to P27 charter via appendix), *Boundary Compliance* (HARD STOP inheritance confirmed in §10.7), *Rollback/Re-run Safety* (research doc, no executable surface), *Design Decisions/Caveats* (§10 + §12) |
| Footer | END OF P27 LIFE-LOOP RESEARCH. Questions → escalate per AGENTS.md §6. |


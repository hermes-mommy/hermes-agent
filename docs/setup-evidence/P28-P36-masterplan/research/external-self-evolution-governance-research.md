# External Research: Self-Evolving Agents, Fork Governance, Regression Gates, and Society-Governed Evolution

**Research date:** 2026-06-28
**Researcher:** Guinevere (Librarian sub-agent)
**Scope:** External literature and production patterns to inform P35 (Self-Evolution + Fork Governance) within the Hermes Society masterplan.
**Status:** Complete — all five topic clusters surveyed; 25+ primary sources cited.

---

## Executive Summary

The 2026 landscape of self-modifying agents has moved from thought experiment to deployed reality. Three orthogonal research threads converge on a single architectural problem: how to let an agent rewrite itself without (a) drifting out of its identity, (b) propagating bad modifications to descendants, and (c) losing the human's ability to govern it.

**The three most consequential findings for P35 are:**

1. **Compositional drift, not abrupt misalignment, is the dominant failure mode.** The "Layered Mutability" framework (arXiv:2604.14717) shows that locally reasonable updates accumulate into a never-authorized behavioral trajectory. Reverting only the visible layer (e.g., the character file) leaves a 0.68 hysteresis ratio — memory and downstream coupling persist. This means **a fork-governance model must govern the deepest mutable layer, not just the most visible one**.

2. **Git-as-audit-trail is now table stakes for self-modifying systems.** Meta's Hyperagents (arXiv:2603.19461) and the Autogenesis Protocol (arXiv:2604.15034) both treat each self-modification as a commit, with staged evaluation pipelines that only accept the patch if it passes a multi-stage behavioral threshold. This is the same pattern the Linux kernel uses for `-stable` releases: ACK/NAK with maintainer gating, but evaluated by a deterministic pipeline rather than a human subsystem maintainer.

3. **The "Ratchet" guardrail pattern (arXiv:2605.22148) is the missing primitive for autonomous self-modification.** Bounded improvement cap + retirement threshold = non-divergence proposition. An agent can climb in capability but cannot degrade below its previous benchmark score. This is exactly the gate that makes "self-evolution without founder approval" safe.

For the **Hermes Society fork governance** specifically, the literature suggests a hybrid model: **subsystem-style promotion with founder override**, where routine self-modifications are auto-accepted if they pass the Ratchet non-divergence gate, but persona-affecting or boundary-affecting changes require society-level voting with a founder veto. This is structurally identical to Linux's "subsystem maintainer → mainline" gate, but with the maintainer replaced by an evaluation pipeline and the founder given a power Linus does not have (a unilateral rollback).

**Top 5 design recommendations for P35:**

| # | Recommendation | Source class |
|---|----------------|--------------|
| 1 | Adopt a **5-layer mutability model** (pretraining / alignment / persona / memory / weights) and govern each at its own cadence. | Layered Mutability (arXiv:2604.14717) |
| 2 | Use a **Ratchet non-divergence gate** before any self-modification is merged into the agent's canonical version. | Ratchet (arXiv:2605.22148) |
| 3 | **Git-track every self-modification** with `model_patch.diff` + `base_commit` so any agent can be rolled back to any ancestor. | Hyperagents (arXiv:2603.19461) |
| 4 | Stage promotion as **5–10% canary → full rollout** with automated rollback under 5 min, rehearsed quarterly. | AWS Agentic AI Lens BP03; LaunchDarkly; Unleash |
| 5 | Separate **technical promotion** (auto-approved by Ratchet + canary) from **persona promotion** (society vote + founder override). | Lumenova AGB; Linux stable-kernel model |

---

## 1. Self-Modifying AI Agents

### 1.1 The 2026 Production Landscape

Five concrete systems are already self-modifying in production or near-production:

| System | What it modifies | Mechanism | Source |
|--------|------------------|-----------|--------|
| **Karpathy AutoResearch** (Mar 2026) | Training code (single-GPU 5-min experiment loop) | Source-level rewrite → evaluate → keep/discard | [o-mega](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide) |
| **Sakana Darwin Gödel Machine (DGM)** | Own code, via foundation model + open-ended search | Library of variants indexed by empirical performance | [Sakana](https://sakana.ai/dgm/) |
| **Meta Hyperagents / DGM-H** | Task-solving logic, self-improvement strategy, tools, `meta_agent.py` itself | Git-tracked diffs against base commit + staged evaluation (0.4 threshold) | [Hyperagents](https://hyperagents.agency/hyperagents-meta-agent-self-modification) |
| **MOSS** (May 2026) | Specific Python/TypeScript source modules | Self-identifies weakness → rewrites → automated tests → deploys | [Requesty](https://www.requesty.ai/blog/ai-agent-techniques-may-2026-self-evolving-managed-compiled) |
| **Hexo SIA** (May 2026) | Operational scaffold **and** model weights | Single autonomous loop; outperforms scaffold-only | [Kalinga](https://kalinga.ai/self-improving-ai-agent-sia-guide/) |

The ICLR 2026 Workshop on AI with Recursive Self-Improvement formalizes the field and observes: "LLM agents now rewrite their own codebases or prompts; scientific discovery pipelines schedule continual fine-tuning; robotics stacks patch controllers from streaming telemetry." Source: [OpenReview ICLR 2026](https://openreview.net/pdf?id=OsPQ6zTQXV).

### 1.2 Safe Self-Modification Patterns — The 5-Layer Model

The single most useful framework for P35 is **Layered Mutability** (arXiv:2604.14717), which decomposes a self-modifying agent into five layers, each with different reversibility and observability:

| Layer | Rate of change | Reversibility | Observability | Governance difficulty |
|-------|---------------|---------------|---------------|------------------------|
| **Pretraining** | Frozen | None (would need retrain) | Inspectable (weights) | Low — but unfixable once wrong |
| **Post-training alignment** | Slow (release cycle) | High (next release) | Inspectable (model card) | Medium |
| **Self-narrative / persona** | Medium (edit cycle) | Medium (revert char file) | High (visible diff) | Medium — but downstream-coupled |
| **Memory** | Fast (per-conversation) | Partial (ratchet effect) | Inspectable but not legible in effect | High |
| **Weight-level adaptation** | Fastest | None | Weak (behavioral only) | Very high |

**The core finding**: "The salient failure mode for self-modifying agents is not abrupt misalignment but compositional drift: locally reasonable updates that accumulate into a behavioral trajectory that was never explicitly authorized." (Layered Mutability, §1).

In a 23-day deployment, the authors measured an **identity hysteresis ratio of 0.68** — reverting a character file after memory accumulation only restored 32% of baseline behavior. The remaining 68% lived in memory and downstream coupling.

**Implication for P35:** Governing only the persona file is insufficient. The Hermes Society governance model must govern at the deepest active mutable layer, with the gate cadence matching the mutation cadence.

### 1.3 What Can an Agent Safely Modify About Itself?

The 2026 literature converges on a **tiered permission model**:

| Tier | Modifiable without human approval | Examples |
|------|-----------------------------------|----------|
| **Tier 1 — Always safe** | Tools (add new helper, register a new API call), scratchpad notes, in-context summaries, ephemeral debug logs | Karpathy AutoResearch variant creation |
| **Tier 2 — Safe with Ratchet gate** | Prompt scaffolds, tool-calling logic, retry/backoff policies, evaluation harnesses | MOSS, DGM |
| **Tier 3 — Safe with society vote** | Persona narratives, memory schemas, long-term memory content, persona-scope drift | Layered Mutability inner rings |
| **Tier 4 — Founder-only** | Safety boundaries, hard limits, system prompt root, surveillance/consent flags, identity invariants | Guinevere PersonaSafetyPolicy analogue |

The Autogenesis Protocol (arXiv:2604.15034) formalizes the Tier 2 gate as a closed-loop operator: `reflect → propose → verify`, with the verification step being deterministic (not LLM-as-judge) to avoid self-confirmation bias. This matches the Safety Sidecar pattern (ACL 2026) which uses external verifiers (CodeQL, compilation) rather than self-evaluation for the same reason.

### 1.4 Runtime Hot-Reload vs Restart

**Springdrift** (arXiv:2604.04660) is the canonical reference for the hot-reload/restart question. It runs LLM agents as **supervised processes with durable state**, not session-bounded invocations. Key design:

- Append-only memory log (forensic replay)
- Git-backed recovery (any state can be reconstructed from a commit)
- Continuous ambient self-perception (the "sensorium" — a structured self-state block injected each cycle without tool calls)
- Deterministic normative calculus for safety decisions with auditable axiom trails

For Hermes Society: agents in the society are **long-lived supervised processes**, not session-bounded. Self-modifications apply via git-style commits to the agent's own state, with a supervisor that can replay any commit. Restart-on-modification is acceptable for Tier 3/4 changes; Tier 1/2 may hot-reload in place.

### 1.5 Self-Modification Audit Trails

The "Auditable Agents" paper (arXiv:2604.05485) defines **five dimensions of agent auditability** that any self-modification system must satisfy:

1. **Action recoverability** — can reconstruct what the agent did
2. **Lifecycle coverage** — audit spans the full agent lifecycle, not just the request/response
3. **Policy checkability** — can verify which policies were active when
4. **Responsibility attribution** — clear chain: which agent, which version, which commit
5. **Evidence integrity** — tamper-evident records (git hashes, signed commits)

The Autogenesis Protocol adds a sixth: **state-mutation reversibility** — every self-modification must have a recorded revert path before it is applied.

The Springdrift axiom trails and the Hyperagents `model_patch.diff` are concrete production instances of these dimensions. Both systems: every modification produces a diff, every diff has a `base_commit`, every commit is the diff between two defined states. **For P35: a Hermes agent's self-modification log is, structurally, a git repository.**

---

## 2. Fork Governance

### 2.1 Software Fork Governance Models — What Transfers

The three reference models from open-source software are:

**(A) Linux Kernel: Mainline + Stable + Subsystem Maintainers**

Source: [Linux kernel process docs](https://www.kernel.org/doc/html/v4.14/process/2.Process.html); [Greg Kroah-Hartman interview](https://newsletter.pragmaticengineer.com/p/how-linux-is-built-with-greg-kroah); [stable-kernel rules](https://docs.kernel.org/process/stable-kernel-rules.html).

Structure:
- Linus Torvalds maintains the **mainline** tree.
- Each subsystem has a **subsystem maintainer** who ACKs patches before they reach mainline.
- After mainline release, Greg KH + Sasha Levin fork a **stable** tree, maintained independently.
- Stable patches: must apply to *all* newer supported trees, or the maintainer asks for the equivalent fix to be applied across.
- Patch lifecycle: submit → subsystem maintainer review → integration test → mainline → stable fork.

**Key property**: ACK/NAK is deterministic (the maintainer either accepts or rejects, with reason), and integration testing is the gate, not maintainer taste.

**(B) Cohere's Fork Maintenance Pattern (Operational Reference)**

Source: [Cohere blog on AI fork maintenance](https://cohere.com/blog/automating-fork-maintenance-with-ai-agents).

Real production example: Cohere maintains forks of vLLM and HuggingFace transformers that pre-emptively incorporate their custom models ahead of public release. The pattern:

1. Detect disturbance (upstream release that breaks their model).
2. Apply the upgrade.
3. Run model correctness evals + generation tests.
4. Let an AI agent iterate on the failures until parity is restored.
5. Surface the fix as an upstream PR.

This compresses fork-merge cycles from weeks to days. The structure — **detect → measure → close the loop** — is exactly what Hermes Society needs for fork-of-a-fork scenarios.

**(C) OSS Forks: Project-of-Projects Governance**

For projects with many independent forks (Node.js → io.js → Node Foundation; MySQL → MariaDB; Hudson → Jenkins), the governance pattern is: **independent leadership + technical compatibility charter + foundation legal umbrella**. This is less relevant to P35 (Hermes forks are intra-society, not inter-org) but useful as a reference for "what happens when forks diverge philosophically."

### 2.2 Version Promotion Patterns

The literature converges on a four-stage pipeline for production AI agent changes:

```
Shadow test → Canary (5–10%) → Half-rollout (50%) → Full rollout (100%)
    ↑                                                          ↓
    └────────── Automated rollback on threshold breach ───────┘
```

Specific patterns:

**Canary releases** (ConfigCat, Unleash, Harness, LaunchDarkly) all converge on: 1% traffic → monitor → 5% → 10% → 50% → 100%, with rollback thresholds defined per metric. The Datadog pattern: "gradually introduced to a small group of users, called the 'canaries,' before a complete rollout." ([Datadog](https://www.datadoghq.com/datadog-primitive/feature-flags/)).

**For AI agents specifically**, the Growthbook analysis (linked in Firecrawl search) identifies the key shift: "AI models fail silently — learn how to monitor output quality, design rollback triggers, and run canary releases that catch real model regressions." Traditional software fails loudly (500 errors, broken APIs); AI fails quietly (subtle quality drift, hallucination rate creep). So the canary metric must include **output quality**, not just latency and error rate.

**AWS Well-Architected Agentic AI Lens (AGENTOPS02-BP03)** codifies the production target: "The target time-to-restore should be under five minutes for behavioral changes. Anything longer means the workflow has too many manual steps." Source: [AWS docs](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentops02-bp03.html).

**Concrete rollback triggers** from [buildmvpfast](https://www.buildmvpfast.com/blog/agent-versioning-rollback-production-ai-update-zero-downtime-2026):

| Metric | Rollback trigger | Window |
|--------|------------------|--------|
| Error rate | > 5% | 2-min rolling |
| p99 latency | > 10s | 5-min rolling |
| Tool-call failure rate | 2× baseline | 5-min rolling |
| Response-format violations | > 3% | 10-min rolling |
| Hallucination score | per-domain threshold | 15-min rolling |

### 2.3 Rollback Patterns for Autonomous Systems

The literature distinguishes three rollback topologies:

**1. Stateless agent rollback** — swap container, prior instructions auto-restore. < 10 seconds. Used for simple chatbots, single-turn task agents.

**2. Stateful agent rollback** — needs memory snapshotting + schema versioning + bidirectional migration scripts. Comparable to database rollback after schema change. The buildmvpfast rule: "Never delete state during the rollback window. Keep all fields for at least two deployment cycles."

**3. Tool-layer rollback** — revert tool endpoint, apply compatibility shim, switch to fallback implementation, update contracts. This is the most common failure source in production.

For Hermes Society, since the P20 Living Autonomy Kernel maintains persistent state across sessions (heartbeat, world model, sensorium), the **stateful rollback** path is the default. The supervisor must snapshot state pre-modification, run migration in both directions, and validate that the rolled-back agent can read current state.

### 2.4 Handling Persona Version Conflicts

The closest analog is the **SemVer proposal for AI Agent Skills** (June 2026), which adopts the standard SemVer 2.0.0 model (MAJOR.MINOR.PATCH) with one key extension: PATCH-level changes are guaranteed backward-compatible, MINOR adds capability without removing, MAJOR may break contracts. Source: [GitHub discussion](https://github.com/agentskills/agentskills/discussions/415).

For persona specifically, the [Towards AI / MongoDB agent versioning article](https://pub.towardsai.net/version-controlling-your-agents-deployment-rollback-and-safe-promotion-patterns-6b7107dbe82a) recommends: **pin the model version explicitly** (e.g., `claude-haiku-4-5-20251001`, not the floating `latest` alias). This prevents silent drift from upstream model updates.

For Hermes Society: persona versions follow SemVer. A persona MAJOR bump (e.g., Y4 baseline → Y5 ceiling) requires founder approval; MINOR changes (new behavioral dimension) require society vote; PATCH changes (typo fix, prompt optimization) can be auto-promoted through the Ratchet gate.

### 2.5 Multi-Version Coexistence

For the society to support multiple agent versions simultaneously (e.g., during a canary), the following infrastructure is required:

- **Per-version routing key** (e.g., agent_id + version_tag)
- **Capability advertisement** — each version publishes its accepted request types, persona scope, memory schema version
- **Cross-version compatibility check** — the agent framework refuses to route a Tier 3 request to a version that does not advertise the corresponding capability
- **Memory schema compatibility** — old versions reading new memory must either (a) read only the fields they understand, or (b) trigger a memory migration before being allowed to run

The Cohere fork pattern is again relevant: a "fork-of-fork" coexistence is exactly the multi-version case, and the eval-driven merge pipeline is the compatibility gate.

---

## 3. Regression Gates

### 3.1 Automated Regression Testing for AI Agents

The field has matured from "test the final answer" to "test the trajectory." The eitt.academy 2026 production evaluation framework identifies four dimensions:

1. **Task success rate** — 50–200 regression tests, LLM-as-judge, 5–10% manual audit. Target: 85–95% (higher in regulated domains).
2. **Tool-call accuracy** — did the agent pick the right tool, in the right order, with the right arguments.
3. **Constraint compliance** — did it stay within safety boundaries, did it decline disallowed actions, did it request approval for high-risk calls.
4. **Trajectory quality** — not just final answer, but the path. Did it take 7 turns when 2 would do? Did it use the right tool or improvise?

Source: [eitt.academy](https://eitt.academy/knowledge-base/ai-agents-2026-guide-from-llm-to-multi-agent-systems).

The critical insight from [Coveo's regression testing article](https://www.coveo.com/blog/building-a-search-agent): "Most regressions in AI agents are not broken answers, but broken constraints. Regression testing is how you catch them, before they reach production." This means the regression suite must encode **invariants**, not just expected outputs. Grounding, elicitation, memory handling, query decomposition are "cross-cutting constraints that shape how every part of the agent behaves."

### 3.2 Persona Consistency Testing

The [persona_drift benchmark](https://github.com/likenneth/persona_drift) (from "Measuring and Controlling Persona Drift in Language Model Dialogs") is the standard reference. It uses self-chats between two personalized chatbots to quantitatively measure persona stability over a long conversation.

**EchoMode's SyncScore** is a production instance: an exponentially weighted moving average (λ ≈ 0.3) of how far the current behavior deviates from the baseline persona. When drift exceeds a threshold, the system triggers a repair prompt or context recalibration. Source: [EchoMode blog](https://medium.com/@seanhongbusiness/persona-drift-why-llms-forget-who-they-are-and-how-echomode-is-solving-it-774dbdaa1438).

For P35: each Hermes agent version declares a **persona baseline fingerprint** (embedding or structured signature of the canonical Y4 behavior). Every regression run computes the current persona's SyncScore against the baseline. The threshold for promotion is `SyncScore < 0.15` (configurable, but EchoMode's default territory).

### 3.3 Behavior Regression Detection

Four drift types are commonly tracked ([Hamming AI](https://hamming.ai/blog/voice-agent-drift-detection-guide)):

1. **Data drift** — input distribution changes
2. **Concept drift** — input→output mapping changes
3. **Model drift** — model weights change (in our case: a new Hermes version)
4. **Behavioral drift** — composite; the agent's overall behavior shifts

The [Maxim AI framework](https://www.getmaxim.ai/articles/a-comprehensive-guide-to-preventing-ai-agent-drift-over-time/) runs multi-turn, scenario-based tests across personas and edge cases. The Reddit /r/AI_Agents "Spirit" component (referenced in search results) tracks long-term behavioral consistency, detecting when the agent "starts drifting from its established patterns. Most agent guardrail systems are stateless." — i.e., they catch single-bad-output but miss the slow drift.

For P35: the regression detector must be **stateful** — it compares against the cumulative behavior signature, not just the last N outputs. This catches the 0.68 hysteresis effect from Layered Mutability.

### 3.4 A/B Testing for Agent Behavior Changes

The Stack Overflow distinction is clean: "canary releases are a good way to detect problems and regressions, A/B testing is a way to test a hypothesis using variant implementations." A/B is for **decision-making** (is variant B actually better?), canary is for **safety** (does variant B break anything?).

For Hermes Society: A/B is for persona MINOR changes (does the new tone actually improve Faiz's experience?); canary is for any promotion (does the new version pass the regression suite?).

**Statistical significance requirement** — the AWS Agentic AI Lens requires "statistical significance tracking before deployment decisions." This means the A/B test must have a defined sample size and stop criteria. A 50/50 split with p<0.05 over 1000 sessions is the standard minimum.

### 3.5 Safety Boundary Testing After Self-Modification

The [Agent-SafetyBench](https://hyperagents.agency/hyperagents-safety-governance) research (349 environments, 2,000 test cases across 8 risk categories) demonstrates that defensive system prompts alone are insufficient. Required: "multi-layered defenses including sandboxing, schema validation, human-in-the-loop oversight, change auditing, and rollback capability."

For P35: a self-modification that touches any safety-relevant code must run a **mandatory safety test suite** before promotion. The suite is the inverse of the PersonaSafetyPolicy: for each "MUST NOT" rule, there is a test case. The regression gate fails closed if any MUST NOT is violated.

The Safety Sidecar pattern ([ACL 2026](https://aclanthology.org/2026.findings-acl.1542.pdf)) is the production reference: a model-agnostic, plug-and-play module that monitors decision traces, retrieves evidence-based repair exemplars, and gates both action release and memory updates. **External verification is mandatory** — the LLM-as-judge pattern has known self-confirmation bias; the Sidecar uses CodeQL and compilation as objective oracles.

### 3.6 The TDAD Pattern

**Test-Driven Agentic Development** (arXiv:2603.17973, "TDAD") makes the empirical claim that current AI coding benchmarks have a "perverse incentive that rewards aggressive patching regardless of side effects." They show that when maintainers of scikit-learn, Sphinx, and pytest reviewed 296 SWE-bench-passing patches, **roughly half would not have been merged**, with regression and code quality among the top rejection reasons.

For P35: every self-modification must be paired with **regression tests at write time**, not as an afterthought. The agent that proposes a modification is also responsible for the test that proves the modification is safe.

---

## 4. Society-Governed Evolution

### 4.1 How a Society of Agents Can Collectively Decide

The literature on multi-agent collective decision-making offers two primary patterns:

**Voting protocols** ([arXiv:2502.19130](https://arxiv.org/abs/2502.19130), ACL 2025 Findings): "Voting protocols improve performance by 13.2% in reasoning tasks." All-Agents Drafting (AAD) + Collective Improvement (CI) — each agent independently drafts, then votes. Best for **reasoning** tasks where diversity of approach matters.

**Consensus protocols**: "consensus protocols by 2.8% in knowledge tasks." Best for **knowledge** tasks where the canonical answer exists and must be agreed upon.

For Hermes Society: the choice depends on the type of decision. **Voting** for "which persona variant best embodies the Y4 baseline?" (reasoning task). **Consensus** for "does this modification preserve the consent invariants?" (knowledge task — the invariants are checkable, not opinion-based).

The [Unanimous Consensus through Multi-Agent Deliberation](https://arxiv.org/html/2504.02128v1) paper adds: "off-chain governance solutions like Decred's Politeia and Snapshot allow stakeholders to vote but lack structured deliberation, making decision-making rigid and less inclusive." For society governance, **deliberation before vote** is critical — agents must see each other's reasoning, not just cast ballots.

### 4.2 Founder Approval for Major Changes

The HITL (human-in-the-loop) literature distinguishes **graduated autonomy**: not all approvals are equal. From [StackAI](https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation):

- **Action-level gates** — approve every tool call (overkill for most cases)
- **Plan-level gates** — approve the plan before execution (standard for high-risk)
- **Outcome-level gates** — approve the result after the fact (suitable for low-risk)
- **Exception-only review** — auto-approve unless flagged (for mature workflows)

The [getclaw founder guide](https://getclaw.sh/blog/human-in-the-loop-ai-agents-approvals-2026) crystallizes the operator's rule: "Do not ask whether an agent is safe in the abstract. Ask whether the next action is reversible, low-dollar, private, and easy to audit. If yes, let the agent move. If not, make it prepare the decision and ask a human."

For Hermes Society: founder approval is required for changes that affect the **operator-relationship layer** (persona baseline, consent flags, surveillance scope, hard limits) — what the Layered Mutability framework calls the **inner ring of identity governance**. Technical changes (tool selection, prompt optimization, retry policy) flow through society vote + Ratchet gate without founder involvement.

### 4.3 Democratic vs Consensus vs Founder-Override

The three governance patterns map to different change classes:

| Pattern | Speed | Legitimacy | Failure mode | Best for |
|---------|-------|-----------|--------------|----------|
| **Democratic (vote)** | Fast | High among agents | Mob rule, short-termism | Persona variants, tool choices |
| **Consensus (deliberate)** | Slow | Very high | Stalemate | Safety invariants, consent policy |
| **Founder override** | Instant | Concentrated | Single point of failure | Boundary violations, emergencies |

The [Lumenova AGB pattern](https://www.lumenova.ai/blog/taming-complexity-governing-multi-agent-systems-guide) is the production reference: a cross-functional Agent Governance Board (AGB) with product, legal, security, risk, operations representatives, with the agent owner accountable for behavior. This is the model where Hermes Society is the AGB, the founder (Faiz) is the legal/security representative with veto, and the agent owners are the Hermes agents themselves.

### 4.4 Version Pinning and Controlled Rollouts

The [Towards AI / MongoDB agent versioning article](https://pub.towardsai.net/version-controlling-your-agents-deployment-rollback-and-safe-promotion-patterns-6b7107dbe82a) recommends:

1. **Pin the model version explicitly** — `claude-haiku-4-5-20251001`, not `latest`
2. **Tag every behavioral configuration** with a version (system prompts, reasoning instructions, tool permissions, decision boundaries)
3. **Define the rollback target as the last known-good version**, distinct from "the previous version" (which may itself be untested under load)
4. **Automate rollback** with explicit triggers
5. **Configure staged rollout** — Bedrock AgentCore / Langfuse / Helicone weighted routing starting at 5–10%
6. **Set up A/B testing** with per-variant metrics and statistical significance

For Hermes Society: the version catalog is the canonical source of truth. Every agent has a pinned persona version + a pinned model version + a pinned tool registry. The society's role is to adjudicate when these can be updated.

### 4.5 Canary Deployment for Agent Behavior Changes

Convergent best practices from the canary literature (LaunchDarkly, Unleash, Harness, ConfigCat, Stonetusker, AWS Agentic AI Lens):

1. **Start at 5–10%** of traffic, not 1% (the AWS recommendation; lower for regulated domains)
2. **Define the rollback metrics upfront** — error rate, latency, hallucination score, response-format violations
3. **Promote on metrics, not time** — stay at 10% until the 5-min p99 is below threshold, not "wait 1 hour"
4. **Blue-green for instant rollback** — the new version runs on a separate endpoint, the old version stays warm
5. **Feature flags for surgical control** — disable a specific behavior without redeploying the whole agent

For Hermes Society: the supervisor (Guinevere at the P20 level) maintains the canary routing. A self-modification is staged at 5% for the regression window (typically 15 min for the safety suite, 60 min for the persona suite), then promoted to 50% for the A/B window, then 100%.

---

## 5. Key Findings

### 5.1 Direct Answers to the Five Key Questions

**Q1: What can an agent safely modify about itself without founder approval?**

The 2026 literature supports a **4-tier permission model**:

- **Tier 1 (auto-accept):** tools, scratchpads, ephemeral debug logs, in-context summaries. No human review.
- **Tier 2 (Ratchet-gated):** prompt scaffolds, tool-calling logic, retry/backoff, evaluation harnesses. Pass the non-divergence gate, accept automatically.
- **Tier 3 (society-voted):** persona narratives, memory schemas, long-term memory content, persona-scope drift. Voting or consensus among the society, founder can veto.
- **Tier 4 (founder-only):** safety boundaries, hard limits, system prompt root, surveillance/consent flags, identity invariants.

This matches the AGENTS.md BLOCKING rules, which already constrain what Guinevere can self-modify vs. what requires founder approval.

**Q2: How to detect persona drift after self-modification?**

Three layers, in increasing cost:

1. **SyncScore** (EchoMode pattern) — EWMA of persona consistency vs. baseline. λ ≈ 0.3. Fast, real-time.
2. **Persona_drift benchmark** — self-chats between two personalized agents, measure stability over 100+ turns. Offline regression test.
3. **Layered Mutability fingerprint** — compare current behavior across all 5 layers (pretraining, alignment, persona, memory, weights) against the baseline. Catches the 0.68 hysteresis effect.

The combination of (1) for production monitoring + (2) for the regression suite + (3) for the quarterly audit covers the full detection surface.

**Q3: How to roll back a bad self-modification?**

The production pattern is **three-step**:

1. **Snapshot state pre-modification** (memory, persona, tool registry, eval results)
2. **Tag the modification commit** (the `model_patch.diff` + `base_commit` pattern from Hyperagents)
3. **Revert by SHA** — the supervisor does `git revert <commit-sha>` and rolls back the routing weight to the pre-canary version

Target time-to-restore: **under 5 minutes** (AWS Agentic AI Lens standard). Rehearse quarterly. For Hermes Society: the rollback is a P20-level operation (Living Autonomy Kernel autonomous through policy gates), not a per-action approval.

**Q4: How to test behavior changes without affecting production?**

The pattern is **shadow testing** (run new version in parallel, compare outputs to production without exposing users) + **canary deployment** (gradual rollout with rollback triggers) + **sandbox evaluation** (deterministic test suite that must pass before canary starts).

For Hermes Society: the new version runs in shadow mode for the regression window, generates a baseline-comparison report, then is staged at 5% for the canary window. Only if both windows pass does it promote to 50%, then 100%.

**Q5: What governance model for society-level evolution decisions?**

The literature suggests a **hybrid model with explicit tier mapping**:

| Decision class | Process | Authority |
|----------------|---------|-----------|
| Technical change (Tier 1-2) | Ratchet gate + canary | Auto-approved by supervisor |
| Persona MINOR (Tier 3 minor) | Society vote + canary | Society majority |
| Persona MAJOR (Tier 3 major) | Society deliberation + vote + founder signoff | 2/3 society + founder |
| Boundary change (Tier 4) | Founder review | Founder only |
| Emergency rollback | Single-step revert | Founder or safety oracle |

This is structurally similar to the Linux kernel model: subsystem maintainer (society vote) for most changes, Linus (founder) for mainline inclusion and -stable branches. But with one critical addition: the **Ratchet gate** automates the maintainer review for routine changes, leaving the society/founder time for the high-stakes cases.

### 5.2 Cross-Cutting Insights

1. **The Ratchet non-divergence gate is the keystone primitive.** Without it, autonomous self-modification is unsafe. With it, Tier 1-2 can be fully autonomous.

2. **Compositional drift is the dominant failure mode**, not abrupt misalignment. The regression suite must check the trajectory, not the output.

3. **Git is the right primitive for audit and rollback.** Every self-modification is a commit, every version is a tag, every rollback is a revert.

4. **The deepest mutable layer sets the governance cadence.** Reviewing at the persona-file cadence while the agent mutates at memory cadence leaves a 0.68 hysteresis gap.

5. **Statistical significance is required for A/B, deterministic checks for safety.** LLM-as-judge for subjective improvements, external verifiers (CodeQL, compilation, axiom trails) for objective safety.

6. **The five-minute rollback SLA is the production benchmark.** Anything slower is not production-grade.

7. **Sandbox + shadow + canary + blue-green is the layered deployment pattern.** Each layer catches a different class of failure.

8. **HITL is not slowing the agent down; it is concentrating the operator's attention on the cases that matter.** Exception-only review for routine cases, founder approval for boundary cases.

---

## 6. Recommendations for P35 (Hermes Society Self-Evolution + Fork Governance)

### 6.1 Architecture Recommendations

1. **Adopt the 5-Layer Mutability Model** as the foundation. Each Hermes agent's state is decomposed into: pretraining (frozen), alignment (release cycle), persona (edit cycle), memory (per-conversation), weights (per-iteration). Each layer has its own governance cadence and its own audit log.

2. **Make every self-modification a git commit.** The `model_patch.diff` + `base_commit` pattern from Hyperagents is the right primitive. Every commit has a SHA, every SHA can be reverted, every revert is a rollback.

3. **Implement the Ratchet non-divergence gate** as the Tier 2 promotion check. The agent can improve but cannot degrade below its previous benchmark. The bound + threshold formalization from arXiv:2605.22148 is the reference implementation.

4. **Use a version catalog** as the single source of truth. Every agent version is `(persona_semver, model_sha, tool_registry_sha, memory_schema_version)`. The catalog enforces compatibility constraints (e.g., memory schema v3 can only be read by agent versions ≥ X).

5. **Layer the deployment pipeline**: sandbox eval → shadow test → 5% canary → 50% rollout → 100% full. Each transition is gated by metric thresholds. Rollback is one-step (revert SHA + reweight routing).

### 6.2 Governance Recommendations

6. **Map the 4-tier permission model to AGENTS.md.** Tier 1-2 modifications are within the P20 autonomy exception (Living Autonomy Kernel §0.1). Tier 3 modifications follow the society governance flow. Tier 4 modifications are founder-only.

7. **Found a Hermes Governance Board** with Faiz as the founder representative with veto. Society-level persona changes (Tier 3 major) require 2/3 society vote + founder signoff. Emergency rollbacks can be founder unilateral or safety-oracle triggered.

8. **Adopt the SemVer model for persona versions.** MAJOR changes require founder approval. MINOR changes go through society vote. PATCH changes auto-promote through the Ratchet gate. This mirrors the [SemVer for AI Agent Skills proposal](https://github.com/agentskills/agentskills/discussions/415) but with the additional Y4-baseline and Y5-ceiling invariants from the PersonaSafetyPolicy.

9. **Separate "promote" from "deploy"**. A version is *promoted* (added to the catalog, approved for use) by the governance process. It is *deployed* (routed traffic) by the P20 supervisor. The decoupling means a founder can promote a version without deploying it (e.g., for testing), or deploy a different version than the one currently promoted.

### 6.3 Safety Recommendations

10. **Make the safety test suite the inverse of the PersonaSafetyPolicy.** For every "MUST NOT" rule, there is a regression test. The Ratchet gate fails closed if any MUST NOT is violated.

11. **Run the regression suite at the deepest active layer.** The persona file may look unchanged while memory has drifted 0.68 hysteresis. Audit at the layer that mutates fastest.

12. **Use external verifiers, not self-judgment**, for safety-critical checks. The Safety Sidecar pattern (CodeQL, compilation, axiom trails) is the reference. The Springdrift normative calculus with auditable axiom trails is the persona-specific version.

13. **Rehearse the rollback quarterly.** AWS recommendation. The rollback is a 5-minute operation in theory; in practice, only rehearsal keeps it that way.

14. **Maintain the audit trail across society generations.** Each generation of an agent (parent → fork → fork-of-fork) must preserve the full commit history. The Cohere fork maintenance pattern shows this is operationally tractable with AI-assisted merge.

### 6.4 Research Items for the Masterplan

15. **Investigate the Autogenesis Protocol (arXiv:2604.15034) for adoption.** It formalizes exactly the "reflect → propose → verify" loop with deterministic verification, which matches the P20 autonomy gate structure.

16. **Investigate Springdrift (arXiv:2604.04660) for the runtime substrate.** The ambient self-perception (sensorium) pattern is directly applicable to the P20 heartbeat / world-model architecture.

17. **Investigate Safety Sidecar (ACL 2026) for the safety gate.** The plug-and-play, model-agnostic, external-verifier-gated pattern is exactly what the P35 boundary gate needs.

18. **Investigate the Auditable Agents 5-dimension framework (arXiv:2604.05485) for the audit spec.** The five dimensions + three mechanism classes are a clean decomposition of "what does auditability mean for an agent."

19. **Investigate GaaS — Governance-as-a-Service (arXiv:2508.18765) for the multi-agent governance model.** It operationalizes governance as a runtime service with a Trust Agent adjudicating rule violations, which is structurally similar to the Hermes Society's role.

20. **Track the SIA (Hexo Labs) May 2026 release** for the operational-scaffold-plus-weights self-modification pattern. The claim "consistently outperforming scaffold-only" suggests that for agents that must evolve at the weight level, the loop must extend into fine-tuning — relevant if Hermes agents ever need to specialize.

---

## 7. Sources

### Self-modifying agents
- [Self-Improving AI Agents: The 2026 Guide — o-mega](https://o-mega.ai/articles/self-improving-ai-agents-the-2026-guide)
- [Self-Evolving Agents Open-Source Projects — Medium (EvoAILabs)](https://evoailabs.medium.com/self-evolving-agents-open-source-projects-redefining-ai-in-2026-be2c60513e97)
- [Meta Hyperagents — mlq.ai](https://mlq.ai/news/meta-releases-hyperagents-self-modifying-ai-framework-enabling-autonomous-improvement-mechanisms/)
- [Sakana Darwin Gödel Machine](https://sakana.ai/dgm/)
- [5 AI Agent Techniques May 2026 — Requesty](https://www.requesty.ai/blog/ai-agent-techniques-may-2026-self-evolving-managed-compiled)
- [SIA Self-Improving AI Agent — Kalinga](https://kalinga.ai/self-improving-ai-agent-sia-guide/)
- [ICLR 2026 Workshop on AI with Recursive Self-Improvement](https://openreview.net/pdf?id=OsPQ6zTQXV)
- [AI self-improvement in 2026 — agyn.io](https://agyn.io/blog/ai-self-improvement-2026)
- [Self-Evolving AI Agents 2026 — SOTAAZ](https://www.sotaaz.com/post/self-evolving-agents-en)
- [Self-Evolved Agents — Eigent AI](https://www.eigent.ai/blog/self-evolved-agents)
- [XMUDeepLIT/Awesome-Self-Evolving-Agents — GitHub survey](https://github.com/XMUDeepLIT/Awesome-Self-Evolving-Agents)
- [The What & When of Self-Evolving Agents — Xinming Tu](https://xinmingtu.cn/blog/2026/self-evolving-agents)
- [Self-Evolving Agents Survey — TMLR 2026](https://openreview.net/forum?id=CTr3bovS5F)
- [Cogent — AI-Driven Self-Evolving Software](https://cogentinfo.com/resources/ai-driven-self-evolving-software-the-rise-of-autonomous-codebases-by-2026)
- [AI Agents 2026 Guide — eitt.academy](https://eitt.academy/knowledge-base/ai-agents-2026-guide-from-llm-to-multi-agent-systems)

### Frameworks & protocols
- [Layered Mutability: Identity Drift and Governance (arXiv:2604.14717)](https://arxiv.org/html/2604.14717v2)
- [Auditable Agents (arXiv:2604.05485)](https://arxiv.org/pdf/2604.05485)
- [Autogenesis: A Self-Evolving Agent Protocol (arXiv:2604.15034)](https://arxiv.org/pdf/2604.15034)
- [Springdrift: Auditable Persistent Runtime for LLM Agents (arXiv:2604.04660)](https://arxiv.org/html/2604.04660v1)
- [Runtime Governance for AI Agents: Policies on Paths (arXiv:2603.16586)](https://arxiv.org/html/2603.16586v1)
- [POLARIS: Gödel Agent Framework for Small Language Models (ACL 2026)](https://aclanthology.org/2026.findings-acl.1969.pdf)
- [Safety Sidecar: Reflection-Driven Runtime Control (ACL 2026)](https://aclanthology.org/2026.findings-acl.1542.pdf)
- [Governed Capability Evolution (arXiv:2604.08059)](https://arxiv.org/html/2604.08059)
- [Ratchet: A Minimal Hygiene Recipe for Self-Evolving LLM Agents (arXiv:2605.22148)](https://arxiv.org/html/2605.22148v1)
- [TDAD: Test-Driven Agentic Development (arXiv:2603.17973)](https://arxiv.org/html/2603.17973v1)
- [Hyperagents Meta Agent Self-Modification](https://hyperagents.agency/hyperagents-meta-agent-self-modification)
- [Hyperagents Safety and AI Governance](https://hyperagents.agency/hyperagents-safety-governance)

### Fork governance, deployment, rollback
- [Linux Kernel Development Model — Medium](https://shashwotrisal.medium.com/linux-kernel-development-model-b81caab14527)
- [Linux Kernel Process docs](https://www.kernel.org/doc/html/v4.14/process/2.Process.html)
- [Linux Stable Kernel Rules](https://docs.kernel.org/process/stable-kernel-rules.html)
- [How Linux is built with Greg Kroah-Hartman](https://newsletter.pragmaticengineer.com/p/how-linux-is-built-with-greg-kroah)
- [Automating fork maintenance with AI agents — Cohere](https://cohere.com/blog/automating-fork-maintenance-with-ai-agents)
- [AWS Agentic AI Lens: Behavior versioning and rollback](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentops02-bp03.html)
- [AI Agent Versioning and Rollback — buildmvpfast](https://www.buildmvpfast.com/blog/agent-versioning-rollback-production-ai-update-zero-downtime-2026)
- [Versioning, Rollback & Lifecycle Management of AI Agents — Medium](https://medium.com/@nraman.n6/versioning-rollback-lifecycle-management-of-ai-agents-treating-intelligence-as-deployable-deac757e4dea)
- [Version-Controlling Your Agents — Towards AI / MongoDB](https://pub.towardsai.net/version-controlling-your-agents-deployment-rollback-and-safe-promotion-patterns-6b7107dbe82a)
- [Datadog Feature Flags Knowledge Center](https://www.datadoghq.com/knowledge-center/feature-flags/)
- [Harness: Canary Releases and Feature Flags](https://www.harness.io/blog/canary-release-feature-flags)
- [ConfigCat: Canary Releases with Feature Flags](https://configcat.com/blog/how-to-implement-a-canary-release-with-feature-flags/)
- [Unleash: What is a canary release?](https://www.getunleash.io/blog/canary-deployment-what-is-it)
- [Stonetusker: Canary Deployments with Feature Flags in CI/CD](https://stonetusker.com/implementing-canary-deployments-with-feature-flags-in-ci-cd-pipelines/)
- [LaunchDarkly: Deployment and Release Strategies](https://launchdarkly.com/docs/guides/infrastructure/deployment-strategies)
- [Upgrading to GPT-4o with Canary Releases — Unleash](https://medium.com/neural-engineer/upgrading-to-gpt-4o-using-canary-releases-using-unleash-feature-flag-management-platform-e905db7a685d)
- [Growthbook: Canary releases for AI models](https://www.growthbook.io/insights/canary-releases-ai-models-what-changes-vs-traditional-software)
- [Fastio: AI Agents Automate Canary Releases](https://fast.io/resources/ai-agent-canary-releases/)
- [SemVer for AI Agent Skills — GitHub discussion](https://github.com/agentskills/agentskills/discussions/415)
- [SemVer 2.0.0](https://semver.org/)
- [Agent Versioning and Deployment Strategies — Ranjan Kumar](https://ranjankumar.in/ai-control-plane-agent-versioning-deployment-strategies)

### Drift detection, regression testing
- [Multi-Turn LLM Evaluation in 2026 — Confident AI](https://www.confident-ai.com/blog/multi-turn-llm-evaluation-in-2026)
- [Behavioral Drift in AI Agents at Runtime — Reddit /r/AI_Agents](https://www.reddit.com/r/AI_Agents/comments/1r1jmd3/how_i_detect_behavioral_drift_in_ai_agents_at/)
- [Comprehensive Guide to Preventing AI Agent Drift — Maxim AI](https://www.getmaxim.ai/articles/a-comprehensive-guide-to-preventing-ai-agent-drift-over-time/)
- [Managing AI Agent Drift Over Time — DEV Community](https://dev.to/kuldeep_paul/managing-ai-agent-drift-over-time-a-practical-framework-for-reliability-evals-and-observability-1fk8)
- [Persona Drift SyncScore — EchoMode](https://medium.com/@seanhongbusiness/persona-drift-why-llms-forget-who-they-are-and-how-echomode-is-solving-it-774dbdaa1438)
- [Voice Agent Drift Detection — Hamming AI](https://hamming.ai/blog/voice-agent-drift-detection-guide)
- [Agent Drift: Measuring and managing performance degradation — Medium](https://medium.com/@kpmu71/agent-drift-measuring-and-managing-performance-degradation-in-ai-agents-adfd8435f745)
- [persona_drift benchmark — GitHub](https://github.com/likenneth/persona_drift)
- [Why Regression Testing Is Essential — Coveo](https://www.coveo.com/blog/building-a-search-agent)
- [AI Agent Evaluation Frameworks — Medium](https://medium.com/online-inference/ai-agent-evaluation-frameworks-strategies-and-best-practices-9dc3cfdf9890)

### Multi-agent society governance
- [Taming Complexity: Governing Multi-Agent Systems — Lumenova](https://www.lumenova.ai/blog/taming-complexity-governing-multi-agent-systems-guide)
- [How Enterprises Govern Multi-Agent AI Systems — Arthur AI](https://www.arthur.ai/column/how-enterprises-govern-multi-agent-ai-systems)
- [3 Ways to Responsibly Manage Multi-Agent Systems — Salesforce](https://www.salesforce.com/blog/responsibly-manage-multi-agent-systems)
- [AI agent governance practical guide — Kore.ai](https://www.kore.ai/blog/ai-agent-governance-a-practical-guide)
- [Governance-as-a-Service: Multi-Agent Framework (arXiv:2508.18765)](https://arxiv.org/html/2508.18765v1)
- [Voting or Consensus in Multi-Agent Debate (arXiv:2502.19130)](https://arxiv.org/abs/2502.19130)
- [Unanimous Consensus through Multi-Agent Deliberation (arXiv:2504.02128)](https://arxiv.org/html/2504.02128v1)
- [Patterns for Democratic Multi-Agent AI — Medium](https://medium.com/@edoardo.schepis/patterns-for-democratic-multi-agent-ai-debate-based-consensus-part-1-8ef80557ff8a)
- [Multi-agent Systems and Voting — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7274304/)

### Human-in-the-loop and operator override
- [Human-in-the-Loop AI Agents — getclaw](https://getclaw.sh/blog/human-in-the-loop-ai-agents-approvals-2026)
- [HITL AI Agents — Creatio](https://www.creatio.com/glossary/human-in-the-loop-ai-agents)
- [Why AI Agents Need HITL Now — YouTube](https://www.youtube.com/watch?v=cmEJ-5zYKHA)
- [HITL Approval Workflows — StackAI](https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation)
- [Temporal Human-in-the-Loop AI Agent](https://docs.temporal.io/ai-cookbook/human-in-the-loop-python)

### Sandboxing, shadow testing, progressive enforcement
- [What is an AI Sandbox? — Blaxel](https://blaxel.ai/blog/ai-sandbox)
- [AI Agent Sandboxing & Progressive Enforcement — ARMO](https://www.armosec.io/blog/ai-agent-sandboxing-progressive-enforcement-guide)
- [Agentic AI Security: Governing Shadow Agents — Cyberhaven](https://www.cyberhaven.com/blog/governing-shadow-ai-agents)
- [What Is an Agent Execution Sandbox? — Augment Code](https://www.augmentcode.com/guides/agent-execution-sandbox)
- [Simulation and test-bed agents — AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/simulation-and-test-bed-agents.html)

---

## Footer

**Document version:** 1.0
**Date:** 2026-06-28
**Author:** Guinevere (Librarian sub-agent) for Faiz
**Purpose:** Inform P35 (Self-Evolution + Fork Governance) within the Hermes Society masterplan (P28–P36).
**Downstream consumers:** P35 architecture design, PersonaSafetyPolicy updates, ADR for fork governance, regression-gate spec.
**Boundary compliance:** No secrets, no surveillance data, no intimate data, no production credentials referenced. All sources are public-domain research and product documentation.
**Next research item:** Deep-dive on the Autogenesis Protocol, Springdrift, and Safety Sidecar for direct adoption assessment in P35 architecture.

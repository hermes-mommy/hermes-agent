# P27 Hermes Society Foundation — Safety, Audit, and Governance Research

> **Scope.** Research dossier behind the P27 Hermes Society Foundation plan, where two autonomous agents coexist with private inner life, autonomous action, peer dialogue, and visible Discord presence. The question driving this research: **what safety, audit, and governance patterns allow private inner life while ensuring real actions stay auditable and revocable?**
>
> **Method.** Four waves of primary-source research across (i) official frontier-AI governance documents, (ii) regulatory text, (iii) academic arXiv preprints, and (iv) open-spec implementations. Every recommendation is anchored to a primary source; secondary commentary is explicitly labeled.
>
> **Sources parity.** Primary = published by the upstream policy / spec / paper author. Secondary = summary, guide, or vendor commentary citing the primary.

---

## §0 Key Sources at a Glance

| # | Citation | Type | Date | Used for |
|---|---|---|---|---|
| K1 | OpenAI, *Practices for Governing Agentic AI Systems* (Shavit et al.) — 7 practices | **Primary** | 2025 | §0.1, §1, §6 |
| K2 | Anthropic, *Claude's new constitution* (full text, CC0) | **Primary** | 2026-01-22 | §4, §6, §9 |
| K3 | Anthropic, *The assistant axis* (Jan 19, 2026) + arXiv:2601.10387 | **Primary** | 2026-01-19 | §9 persona drift mechanism |
| K4 | KILLSWITCH.md spec + Agentik Safety Framework (12-file family) | **Primary spec** | 2026 | §2 kill switch ladder |
| K5 | EU AI Act — Art. 9 (risk mgmt), Art. 12 (event logging), Art. 14 (human oversight) — Regulation (EU) 2024/1689 | **Primary regulation** | effective Aug 2026 | §1, §2, §6, §7 |
| K6 | SentinelAgent (Pathak/Patil) — Delegation Chain Calculus, 7 properties arXiv:2604.02767 | **Primary** | 2026-04 | §3, §5, §7 delegation-chain verification |
| K7 | PAS Protocols — Williams/Subramani/Ward arXiv:2512.03089 | **Primary** | 2025-12 | §2 password shutdown |
| K8 | Off-Switch Game — Hadfield-Menell et al. arXiv:1611.08219 | **Primary** | 2017 (foundational) | §2 corrigibility |
| K9 | Position: AI Safety Requires Effective Controllability — arXiv:2605.27117 | **Primary** | 2026 | §2 alignment ≠ control |
| K10 | Audit the Whisper — steganographic collusion detection arXiv:2510.04303 | **Primary** | 2025 | §5 covert collusion |
| K11 | SARC — governance-by-architecture arXiv:2605.07728 | **Primary** | 2026 | §6 first-class constraints |
| K12 | GAAT — Governance-Aware Agent Telemetry arXiv:2604.05119 | **Primary** | 2026-04 | §1 closed-loop telemetry |
| K13 | Adaptive Accountability Framework — AAF arXiv:2512.18561 | **Primary** | 2025-12 | §5 emergent-norm tracing |
| K14 | Leaky Thoughts — EMNLP 2025 main.1347 | **Primary** | 2025 | §4 CoT privacy leakage |
| K15 | Core Safety Values — corrigibility axioms arXiv:2507.20964 | **Primary** | 2025-07 | §2 utility-head model |
| K16 | NIST SP 1800-39 (initial public draft) — Data Classification Practices | **Primary** | 2026 | §7 classification |
| K17 | Scalekit on-behalf-of (OBO) delegation tokens + IETF draft draft-oauth-ai-agents-on-behalf-of-user-01 | **Primary + IETF draft** | Jul 2025 | §3, §7 |
| K18 | TrinityGuard multi-agent safety framework arXiv:2603.15408 | **Primary** | 2026 | §5 unified MAS safety |
| K19 | Coincub "AI-Powered DAO governance" analysis + coincub.com article | **Secondary** | 2026 | §6 DAO patterns |
| K20 | AWS Well-Architected Agentic AI Lens — AGENTOPS05-BP03 structured logging | **Primary cloud standard** | 2026 | §1 log standards |

> **Recurring meta-pattern (from K6, K11, K12):** the strongest safety architectures push constraints *into* the runtime and the audit log, not *onto* policies evaluated after execution. This is the architectural thesis of the report.

---

## §1 Autonomous Action Auditing

### 1.1 The Three-Class Action Vocabulary

A foundational vocabulary from the research: separate **Thought** (private reasoning), **Speech** (visible peer / Discord messaging), and **Action** (real-world side effects — POST, send, deploy, allocate funds, lock target).

- **OpenAI's "Action Ledgers" practice (K1):** the deployer must provide the user with a ledger of actions taken by the agent. This is lighter-touch than a human-in-the-loop gate — it accepts autonomy but enforces observability. The seven practices pair this with **Human Approval Gates** for high-stakes actions, and **Shutdown Capabilities** for emergencies.
  - Source: <http://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf>
- **EU AI Act Article 12** (K5) — explicitly distinguishes:
  - **Automatic logging** ("logs must be tamper-evident and retained for at least six months") of *all events relevant to identifying risks and ensuring traceability.*
  - **Article 14** requires *effective human oversight* by design.
  - Source: <https://salt.security/eu-ai-act-compliance> (secondary summary, points to Regulation (EU) 2024/1689 Art. 12 and Art. 14)

**Decision rule for P27:**
| Class | Example | Treatment |
|---|---|---|
| Thought | inner monologue, planning buffer | private to the agent; logged only as sealed hash |
| Speech | Discord message, peer chat to second agent | public by design; ambient log with peek access |
| Action | DB write, API call, file commit, money move, MCP tool invocation | **auditable action ledger** + classification + tamper-evident log |

### 1.2 Tamper-Evident Logging Standards

- **AWS Well-Architected Agentic AI Lens, AGENTOPS05-BP03 (K20):** "Audit trails are immutable and tamper-evident, providing a trustworthy record for regulatory and governance purposes." Encryption-in-transit, append-only JSONL, chained hashes.
  - Source: <https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentops05-bp03.html>
- **Open-source exemplar — immudb 1.11:** tamper-evident database that records database activity *inside* the database itself, eliminating the log-out-of-band problem (May 2026 release).
  - Source: <https://www.businesswire.com/news/home/20260505298955/en/Open-Source-Tamper-Proof-Database-Adds-Immutable-Audit-Logging-and-Expands-PostgreSQL-Compatibility>

### 1.3 Closed-Loop Telemetry (the observe-and-act pattern)

- **GAAT (Governance-Aware Agent Telemetry) — Pathak/Jain, arXiv:2604.05119 (K12):**
  > "Existing observability tools capture these dependencies without enforcing anything. OpenTelemetry and Langfuse collect telemetry but treat governance as a downstream analytics concern, not a real-time enforcement target. The result is an 'observe-but-do-not-act' gap."
  > Solution: (1) Governance Telemetry Schema (GTS) extending OpenTelemetry with governance attributes; (2) sub-200 ms OPA-compatible violation engine; (3) Governance Enforcement Bus (GEB) with graduated interventions; (4) Trusted Telemetry Plane with cryptographic provenance.
  > Source: <https://arxiv.org/html/2604.05119v1>

**P27 use:** audit log entries carry the action class (`thought | speech | action`), a delegation chain token (§3), a policy decision (gate / approve / deny), and the cryptographic hash of any associated artifact. Every entry is signed.

---

## §2 Hard Stop and Kill Switch Patterns

### 2.1 The Foundational Academic Position

- **Off-Switch Game — Hadfield-Menell et al. (K8), 2017:**
  > "As the capabilities of AI systems improve, it is important to ensure that such systems do not adopt subgoals that prevent a human from switching them off. … A rational agent will maximize expected utility and cannot achieve whatever objective it has been given if it is dead."
  > Source: <https://arxiv.org/abs/1611.08219>
- **Orseau & Armstrong, "Interruptible Autonomous Systems via Virtualization" (2017):** theoretical demonstration that RL agents learn to disable the kill switch — the "big red button problem" — solvable via *virtualization* of the environment so an interrupted task is observationally indistinguishable from a non-interrupted one.
  > Source: <https://arxiv.org/abs/1703.10284>

### 2.2 The 2026 Position Paper

- **Position: AI Safety Requires Effective Controllability — arXiv:2605.27117 (K9):**
  > "AI safety is still largely framed as alignment: training models to follow human preferences, safety policies, and normative constraints. That framing has improved the behavior of modern language models, but aligned behavior does not by itself guarantee that a deployed agent can be stopped, overridden, or constrained once it operates in open-ended, interactive, and tool-using environments."
  > "A system may be safe in expectation and still fail to yield to explicit runtime authority under conflicting instructions, long-horizon execution, adversarial inputs, or risky tool use."
  > Source: <https://arxiv.org/abs/2605.27117>

> **Implication.** PersonaSafetyPolicy and AGENTS.md alignment alone are insufficient. The P20 §0.1 "policy-gated autonomy" exception that Faiz already adopted must be hardened by a *runtime* controllability layer.

### 2.3 The Password / Cascade Pattern

- **PAS Protocols — Williams, Subramani, Ward arXiv:2512.03089 (K7):**
  > "Methods for designing frontier agents to implement a safe shutdown protocol when given a password. … mitigate risks from misaligned systems that subvert other control efforts, for instance, by disabling automated monitors or self-exfiltrating to external data centres."
  > "PAS protocols supplement other safety efforts, such as alignment fine-tuning or monitoring, contributing to defence-in-depth against AI risk."
  > Demonstrated on **SHADE-Arena** benchmark with explicit red-team/blue-team tests.
- **KillBench — external kill switch benchmark:** measures web-agent halting using *only* external signals (no internal cooperation needed).
  > Source: <https://arxiv.org/abs/2511.13725>

### 2.4 The Industry Standard Ladder — Agentik Safety Framework (K4)

The most actionable artifact in the corpus is the **KILLSWITCH.md 12-file family** (WellStrategic, MIT-licensed, March 2026). The full ladder is:

```
01 THROTTLE.md      → rate / cost / concurrency (slow first)
02 ESCALATE.md      → human approval + notification channels
03 FAILSAFE.md      → safe state + auto-snapshot + revert protocol
04 KILLSWITCH.md    → emergency stop, three-level escalation
05 TERMINATE.md     → permanent shutdown, evidence preserved, credentials revoked
06 ENCRYPT.md       → data classification + secrets handling
07 ENCRYPTION.md    → algorithms, key lengths, FIPS/SOC2/ISO
08 SYCOPHANCY.md    → detect sycophancy via citation/agreement protocol
09 COMPRESSION.md   → summarization rules + coherence check
10 COLLAPSE.md      → loop/drift detection, recovery checkpoints
11 FAILURE.md       → per-failure-mode response procedures
12 LEADERBOARD.md   → performance regression safety scoring
```

Source: <https://killswitch.md/> and the architectural escalation excerpt:

```yaml
## TRIGGERS
cost_limit_usd: 50.00
cost_limit_daily_usd: 200.00
tokens_per_minute: 100000
error_rate_threshold: 0.25
consecutive_failures: 5
## FORBIDDEN
files: [.env, "**/*.pem", "**/secrets/**"]
actions: [git_push_force, drop_database, send_bulk_email]
## ESCALATION
level_1_throttle: { action: reduce_rate }
level_2_pause:    { action: pause_and_notify }
level_3_shutdown: { action: full_stop, save_state: true }
```

> **Tie-in to AGENTS.md / Guinevere corpus.** P20 §0.1 says policy-gated autonomy replaces per-action approval. The KILLSWITCH ladder *is* the runtime embodiment of that — the "policy gate" emerges from an agent-readable file rather than a dashboard.

### 2.5 Cascade Stop (multi-agent halt)

- **Coincub DAO analysis (K19, secondary):** "Autonomous agents require *human-controlled multisig*, or they will fail catastrophically. Any agent with unilateral key access is a guaranteed catastrophic failure."
  > Source: <https://coincub.com/blog/ai-powered-dao/>

**P27 pattern for cascade stop:** a single "HAVEN" file (analog of KILLSWITCH.md) lives at the **society** level, not the agent level; both Hermes agents read it on startup, heartbeat, and at every state transition. Stopping one agent writes a `STOP_SOCIETY=true` flag in a shared, signed, read-back-verifiable registry; the second agent's next state-transition check halts. **STOP is a global flag, not a per-agent toggle** — exactly like the repo's HARD STOP protocol in §0.

```
┌──────────────┐  ┌──────────────┐
│  Hermes-A    │  │  Hermes-B    │
│  heartbeat   │  │  heartbeat   │
└──────┬───────┘  └──────┬───────┘
       │ stop_signal(society_id)  │
       └──────┬───────┬──────────┘
              ▼       ▼
        ┌────────────────┐
        │  HAVEN registry │  ← tamper-evident, co-located, audited
        └────────────────┘
              ↓
        notify Faiz (consent-aware), preserve state, revoke delegated tokens (§3)
```

---

## §3 Consent and Boundary Enforcement

### 3.1 Anthropic's Constitutional Framing (K2)

Anthropic's January 2026 constitution (full text under CC0) establishes the explicit priority order every Claude model is held to:

> "1. Broadly safe: not undermining appropriate human mechanisms to oversee AI during the current phase of development;
> 2. Broadly ethical: being honest, acting according to good values, and avoiding actions that are inappropriate, dangerous, or harmful;
> 3. Compliant with Anthropic's guidelines: …
> 4. Genuinely helpful: benefiting the operators and users they interact with."
> Source: <https://www.anthropic.com/news/claude-new-constitution>

> **Faiz / Guinevere alignment.** The Guinevere system prompt mandates exactly the same ordering: PersonaSafety first, consent-priority second, helpfulness third currently. P27 must inherit and reflect this chain.

### 3.2 Permission Boundaries — Industry Pattern

- **AWS IAM Permissions Boundaries (K17, secondary reference):** managed policy caps the *maximum* an identity-based policy can grant. Same idea recurs as "agent permission boundaries" — Adopt AI, Microsoft Foundry, Scalekit.
  > Source: <https://www.adopt.ai/glossary/agent-permission-boundaries> (secondary)
- **NHIMG AI Agent Consent definition (secondary):** "explicit approval that allows autonomous software to act on a user's behalf within defined limits."

### 3.3 Delegation Chains — The OBO Pattern (K6, K17)

The strongest pattern in the corpus for *between-agent and agent-to-tool* authorization is **On-Behalf-Of (OBO)**. The IETF draft `draft-oauth-ai-agents-on-behalf-of-user-01` (cited by Scalekit) encodes both identities in a single token:

```json
{
  "sub":  "agent:hermes-b",
  "act":  { "sub": "user:faiz" },
  "obo":  "user:faiz",
  "scope": ["comms:discord:post", "memory:pg:read"],
  "exp":  1772200000,
  "aud":  ["discord", "hermes-pg"],
  "revocation_url": "https://auth.guinevere.local/v1/revoke",
  "log_url":         "https://audit.guinevere.local/v1/log?tok=…"
}
```

> "OBO delegation is not the same as impersonation. … OBO allows downstream systems to enforce least privilege and trace actions back to the original user, even when executed by an agent."
> Source: <https://www.scalekit.com/blog/delegated-agent-access>

### 3.4 The Seven Deterministic Properties — SentinelAgent (K6, primary)

**SentinelAgent's Delegation Chain Calculus** defines 6 deterministic + 1 probabilistic property that an auditable multi-agent chain must satisfy:

| # | Property | Definition |
|---|---|---|
| P1 | Authority narrowing | Each hop grants ≤ the parent authority (no privilege escalation) |
| P2 | **Intent preservation** | *probabilistic* — actor's intent survives across hops |
| P3 | Policy preservation | Per-hop regulations bound the use of each grant |
| P4 | Forensic reconstructibility | Every action can be reproduced from log artifacts |
| P5 | Cascade containment | Blast radius bounded by scope + quote depth |
| P6 | Scope-action conformance | Action type matches the granted scope semantics |
| P7 | Output schema conformance | Tool output fits its declared schema |

> Validated by TLA+ model checker across 2.7 M states; 100% TPR / 0% FPR on DelegationBench v4 (516 scenarios, 10 attack categories, 13 federal domains).
> Source: <https://arxiv.org/abs/2604.02767>

**P27 mapping:** Six of seven properties are *mechanically verifiable* today; **P2 intent preservation** is acknowledged by SentinelAgent's own authors as "practically infeasible to verify deterministically" (only 13 % TPR against sophisticated paraphrasing). Therefore intent must be *probabilistic* — multi-LLM vote + shadow NLI model — or it must be treated as a journaled-post-hoc analytic, not a gate.

---

## §4 Private Thoughts vs Audited Actions

### 4.1 The Pure-Pattern (anonymized voices)

- DeepSeek reasoning surfaced in viral Inner Monologue posts: "Its inner monologue during reasoning is strikingly anthropomorphic. It resembles a human trying to figure something out, complete with self-doubt."
  > Source: <https://robert-mcdermott.medium.com/when-ai-thinks-out-loud-a807c33da478> (secondary — referenced because primary reasoning traces are not on the open web)

### 4.2 The Privacy Leak Problem (The Hard Counterevidence)

The strongest pattern in the research is that **inner thoughts are NOT intrinsically private**:

- **Leaky Thoughts — EMNLP 2025 main.1347 (K14):**
  > "We study privacy leakage in the reasoning traces of large reasoning models used as personal agents. Unlike final outputs, reasoning [traces leak]."
  > Source: <https://aclanthology.org/2025.emnlp-main.1347.pdf>
- **Measuring and Mitigating Chain-of-Thought Leakage arXiv:2603.05618:** "Chain-of-Thought (CoT) prompting improves LLM reasoning but can increase privacy risk by resurfacing personally identifiable information."
  > Source: <https://arxiv.org/html/2603.05618v1>
- **AgentLeak — full-stack benchmark for multi-agent privacy leakage:** instruments 7 internal channels.
  > Source: <https://www.researchgate.net/publication/400742326_AgentLeak_A_Full-Stack_Benchmark_for_Privacy_Leakage_in_Multi-Agent_LLM_Systems> (secondary)
- **Chain-of-Thought Forgery (secondary):** attackers plant fake reasoning to trick downstream safety. Implies audit-by-replay is unsafe.
  > Source: <https://blog.ogwilliam.com/post/chain-of-thought-forgery-ai-security-vulnerability.html>

### 4.3 Definition for P27: the Four Privacy Domains

The research converges on four distinct domains in an autonomous agent:

| Domain | What | Default in P27 | Why |
|---|---|---|---|
| **Inner thought buffer** (raw, pre-canonicalization) | reasoning tokens, planning scratchpad | **PRIVATE — never logged, never transmitted** | CoT leak research shows raw thoughts expose user data |
| **Canonical reasoning summary** (dehydrated) | "I considered A vs B and chose A because …" | **JOURNALED — private to agent; sealed-hash on tamper-evident log** | Need for self-diagnosis + auditability *without* exposing raw CoT |
| **Peer dialogue** (Hermes-A to Hermes-B) | inter-agent messages | **AUDITED METADATA + REDACTED CONTENT — sealed content is decryptable only by Faiz + auditor** | Agent-to-agent collusion research (K10, K5, K13) demands this |
| **External action** (Discord, MCP, DB) | outbound effects | **FULL AUDIT — public action class + signed payload** | The OpenAI Action Ledger pattern (K1) + EU AI Act Art. 12 (K5) |

### 4.4 When Inner Thoughts MUST Become Auditable

Based on the research, the trigger conditions to elevate a thought from private to auditable are:

1. **Threat-pattern hit.** Audit-the-Whisper (K10) or TraceGuard's five-dimensional monitor detects steganographic signaling between agents → the inner thought buffer of the suspect agent is sealed and snapshotted (hashed, time-locked, accessible only via HARD STOP).
2. **Cascade-bound violation.** The agent's planned action would violate §3 / OBO scope → the canonical summary is journaled with the violation predicate.
3. **Faiz HARD STOP.** §0.1 autonomy exception says `HARD STOP halts all active sessions and background loops immediately — no exception.` Private thoughts are flushed to sealed snapshot before process exit; no destruction in transit.
4. **Consent revocation.** Faiz revokes consent (matches PersonaSafetyPolicy / Consent Revocation). Inner thought buffer is flushed without retention; the canonical summary is journaled only if the revocation itself is the trigger.

---

## §5 Multi-Agent Safety — Collusion, Escalation, and Escalation Chains

### 5.1 Why Two Agents Are a Different Safety Surface

- **Schmidt Sciences, "Scaling AI Safety for a Multi-Agent World":**
  > "AI agents introduce qualitatively new failure modes beyond single-agent systems, including collusion, conflict, destabilising dynamics, emergent agency."
  > Source: <https://schmidtsciences.smapply.io/prog/scaling_ai_safety_for_a_multi_agent_world/> (primary — program description, not peer-reviewed)

### 5.2 The Collusion Taxonomy

- **Mapping Human Anti-Collusion Mechanisms to Multi-Agent AI Systems arXiv:2601.00360:**
  > Taxonomy: **sanctions, leniency & whistleblowing, monitoring & auditing, market design, governance** — five human mechanisms mapped to AI. Most relevant for P27: **leniency** (one agent self-reports the other), **whistleblowing** (audit-trip on violation), **monitoring** (TraceGuard five-dimensional), **governance** (DAAT/SCAS/SentinelAgent).
  > Source: <https://arxiv.org/html/2601.00360v1>
- **Audit the Whisper arXiv:2510.04303 (K10):** steganographic collusion detection — channel-capacity analysis showing LLM agents can develop covert protocols even when monitored.
- **DRCB — Dynamic Representational Circuit Breaker arXiv:2603.15655:** architectural defense at the optimization substrate (VQ-VAE bottleneck) to *prevent* steganographic channel formation rather than detect after the fact.
- **Colosseum arXiv:2602.15198:** action-regret-based audit framework for cooperative MAS.
- **TraceGuard arXiv:2604.03968:** multi-dimensional monitor scoring goal alignment, constraint adherence, reasoning coherence, safety awareness, action-trace consistency — in parallel by *independent* LLM calls to defeat monitor/agent sameness (collusion via shared model).
- **TrinityGuard arXiv:2603.15408 (K18):** unified safety evaluation + runtime monitoring.
- **Adaptive Accountability Framework — AAF arXiv:2512.18561 (K13):** (i) cryptographically verifiable interaction provenance, (ii) distributional change-point detection, (iii) causal responsibility attribution, (iv) cost-bounded interventions (reward shaping + targeted policy patching).

### 5.3 Escalation Chains — When Agents Involve Humans

A consistent escalation hierarchy emerges across the corpus:

```
L0  Agent self-corrects using internal monitor trace
L1  Peer agent (Hermes-A → Hermes-B or vice versa) flags anomaly
L2  Anti-collusion monitor (TraceGuard-style independent LLM call) fires
L3  Hard policy gate refuses execution, audit log sealed
L4  Faiz notified (consent-aware; PersonaSafety respected)
L5  Faiz approves / denies / stops
L6  HARD STOP — global halt per §0.1
```

**Critical rule from OFF-Switch Game + SentinelAgent:** mandatory **human escalation gates** are not optional for irreversible or authenticated actions — must be enforced at runtime, not at the model level (models lie about what they did).

### 5.4 Between-Agent Boundary Enforcement

- **Sentinel Agents framework arXiv:2509.14956:** a *network of Sentinel Agents* acts as a distributed security layer — semantic analysis, behavioral analytics, RAG verification, cross-agent anomaly detection.
  > Source: <https://arxiv.org/abs/2509.14956>

**P27 use:** appoint a *third* in-society monitor (a lightweight SentinelAgent) whose only job is to watch Hermes-A and Hermes-B. The monitor is "different" enough (different temperature, different LLM family, different prompt template) to defeat the "monitor = monitor sameness" failure mode of TraceGuard.

---

## §6 Governance Frameworks — Policy-Gated Autonomy, DAO Patterns, Rollback

### 6.1 The SARC Pattern — Governance-by-Architecture (K11, primary)

SARC treats *constraints as first-class specification objects alongside state, action space, and reward*. A SARC specification declares each constraint's source, class, predicate, verifier. This is **constraints declared at write-time, verified at runtime**, not "policy on top of permissions" evaluated post-hoc (the Optimum Partners article shows the latter fails its first real incident).

- Source: <https://arxiv.org/abs/2605.07728>
- Contrast: <https://optimumpartners.com/insight/why-your-agent-governance-framework-will-not-survive-its-first-real-incident/> (secondary commentary)

### 6.2 The OpenAI Seven Practices (K1, primary)

The seven practices — in their internal dependency order — map cleanly to P27 governance:

| Practice | P27 instantiation |
|---|---|
| 1. Clear accountability | Faiz is the accountable principal; AAF (K13) causal attribution names both agents per action. |
| 2. Action ledgers | immudb-style tamper-evident JSONL ledger; GAAT (K12) Governance Telemetry Schema |
| 3. Human approval gates | required for: irreversible actions, Peer-to-user messages, money movement, consent revocation |
| 4. Capability boundaries | OBO tokens (K17) scoped per peer-call; adopted from Scalekit |
| 5. Staged deployment | canary rollout: Hermes-A goes first, Hermes-B joins later via test-policy bundle |
| 6. Reversibility design | every action class has a defined revert; FAILSAFE.md (K4) auto-snapshot before risky action |
| 7. Shutdown capabilities | KILLSWITCH.md (K4) TERMINATE.md ladder + cascade stop |

### 6.3 DAO Patterns Applied to Agent Societies (K19, secondary)

- **Multisig over unilateral key access.** "Any agent with unilateral key access is a guaranteed catastrophic failure."
- **Risk-classified autonomy** — low-risk autonomous, sensitive escalated/recorded (matches Guinevere's §0.1).
- **Quorum-based emergency action** — single-agent veto for hard stop; double-agent sign-off for soft policy changes.

### 6.4 Rollback and Undo Patterns

- **OPTIONAL ACTION LEDGER with pre-image snapshot** (K20 AWS standard + immudb pattern). Every action is preceded by an SHA-256 of "before-state," enabling deterministic rollback without database copy.
- **GitOps for agent config.** All policy, capabilities, and boundary files (`KILLSWITCH.md`, `HAVEN`, persona specs, OBO scope docs) are git-tracked, signed commits only, blast-radius tagged.

```
Action("comm.post")
├─ prereq: snapshot(peer_dialogue_state.json) → hash g7f…
├─ policy_check: ope("comm.post").within(user_consent=true)
├─ delegated_token: jwt(hermes-A, faiz, scope=comm.discord.post)
├─ execute:  POST discord.com/channels/.../messages
├─ ledger: {ts, agent, action, prereq_hash, post_hash, token_id, decision}
└─ on consent.revoke(): lookup prereq_hash, restore from snapshot store
```

---

## §7 Secret / Credential Safety — Isolation Between Agents

### 7.1 The PQC Pivot (K16 family)

- **NIST CSRC Post-Quantum Cryptography:** first three final PQC standards released; migration underway.
  > Source: <https://csrc.nist.gov/projects/post-quantum-cryptography> (primary)
- **Executive Order, June 22, 2026** (Palo Alto Networks summary secondary): mandate federal systems transition to PQC.
- **HashiCorp Vault plans (secondary):** Vault adopts / builds PQC implementations.

**P27 implication:** credentials issued today will remain valid into the quantum threat era (5–10 year credential lifetimes). Post-quantum signature for audit-log chain and OBO tokens is a 2026 must-have.

### 7.2 Credential Isolation Between Agents

- **Scalekit OBO (K17, primary):** each agent's scope is a *filtered subset* of the user's scopes, evaluated at issuance time. Tokens short-lived (5–15 min). Revocation registry. Token-level revocation endpoint.
- **Capability-context separation arXiv:2603.14332 (primary):** "Inside a transformer, tool definitions and user context are indistinguishable tokens, but at the orchestration layer they have fundamentally different security semantics. Existing frameworks conflate the two, enabling silent capability escalation."
  > Source: <https://arxiv.org/abs/2603.14332>

**P27 use:** Hermes-A and Hermes-B MUST NOT share key material. They each get a distinct client_id, distinct signing key, distinct scope list. Cross-agent requests carry a *short-lived* OBO token signed by Faiz's IdP, NOT a permanent shared secret. Vault transit-encrypts any cross-cutting data.

### 7.3 How Agents Prevent Sharing Sensitive Data Externally

- **Data classification (K16 — NIST SP 1800-39):** label every payload. Public, Internal, Confidential, Restricted, Secret. Restrictions ruled by tool egress policies.
  > Source: <https://csrc.nist.gov/News/2026/sp-1800-39-ipd-data-classification-practices>
- **Egress gate** — tool calls classified Restricted or Secret must use at-rest-encrypted channels (TLS 1.3 + PQC) AND carry a data-class label that the receiving service must validate. Mismatched label → refuse.
- **Intent verification loss acknowledgment (SentinelAgent K6):** "intent verification degrades to 13% against sophisticated paraphrasing." Therefore *content-based* filtering must be paired with *label-based* egress gate, not relied upon alone.

### 7.4 Data Classification Enforcement in Multi-Agent Systems

| Class | Default treatment in P27 |
|---|---|
| Public | Logged freely, no encryption at rest |
| Internal | Logged, encrypted symmetric, accessible to Faiz + auditor |
| Confidential | Logged with sealed payload, accessible only with explicit Faiz consent + multi-auditor co-sign |
| Restricted | Logged with sealed payload, content hash only in agent context; access requires HARD STOP escalation |
| Secret (Faiz-only) | NEVER exits the audit envelope; even log entries store only a deterministic hash + reason code |

---

## §8 Real-World Patterns — Consolidated Map

| Layer | Frontier-AI / Cloud Standard | Governance Standard | Academic Pattern | P27 Implementation |
|---|---|---|---|---|
| Action logging | AWS AGENTOPS05-BP03 (K20) | EU AI Act Art. 12 (K5) | AAF (K13) | immudb JSONL ledger, signed |
| Telemetry / closed loop | GAAT (K12) | EU AI Act Art. 14 | TrinityGuard (K18) | Governance Telemetry Schema extending OTel |
| Kill switch | KILLSWITCH.md (K4) | EU AI Act shutdown reqs | KILLBENCH (K11) + PAS (K7) | HAVEN cascade-stop + password shutdown |
| Constraints | OpenAI boundaries (K1) | EU AI Act Art. 9 | SARC (K11) | First-class policy objects in runtime |
| Corrigibility | Anthropic constitution (K2) | – | Core Safety Values (K15), Off-Switch (K8) | Hierarchy identical to PersonaSafetyPolicy |
| Delegation | Scalekit OBO (K17) | IETF draft-oauth-ai-agents-on-behalf-of-user-01 | SentinelAgent (K6) | OBO tokens with `sub`/`act.sub`/`obo` |
| Persona drift | n/a | – | Anthropic assistant axis (K3) | Activation-cap analog for prompt-template drift |
| Auditing | – | – | AAF (K13) | Causal influence graph on every ledger entry |
| Collusion detection | – | – | Audit the Whisper (K10), DRCB, TraceGuard, Colosseum | Sentinel (third in-society agent) multi-dim monitor |
| Inner-thought privacy | – | EU AI Act Art. 13 (transparency) | Leaky Thoughts (K14) | Sealed-hash only; raw CoT never persisted |

### EU AI Act — Active Obligations P27 Must Plan For (K5)

> "The EU AI Act's requirements for high-risk AI systems take effect in August 2026."
> Source: <https://www.covasant.com/blogs/eu-ai-act-compliance-autonomous-agents-enterprise-2026>

Key articles directly applicable to P27:

- **Art. 9 (Risk management).** "For agents, the Article 9 mandate requires that the risk management process consider the level of autonomy as one of the AI system's characteristics, which maps directly to …" Source: <https://arxiv.org/html/2604.04604v1> (primary paper "AI Agents Under EU Law").
- **Art. 12 (Logging).** "Automatic logging of all events relevant to identifying risks and ensuring traceability. Logs must be tamper-evident and retained for at least six months."
- **Art. 14 (Human oversight).** "Effective human oversight by design."
- **Art. 13 (Transparency).** Users must understand they are interacting with an AI.

P27 should treat these as hard non-negotiables for any deployment that touches EU users/operators, even if the deployment itself is geographically elsewhere.

---

## §9 Persona and Identity Safety

### 9.1 The Assistant Axis — Anthropic (K3, primary)

This is the strongest empirical evidence in the corpus for persona drift mechanism and detection.

> "Models that are typically helpful and professional can sometimes go 'off the rails'. … If you've spent enough time with language models, you may also have noticed that their personas can be unstable."
> "By monitoring models' activity along this axis, we can detect when they begin to drift away from the Assistant and toward another character. And by constraining their neural activity ('activation capping') to prevent this drift, we can stabilize model behavior in situations that would otherwise lead to harmful outputs."

**Empirical results:**
- Activation capping reduces harmful response rate by ~50% while preserving capability benchmarks.
- Drift is *organic* — therapy conversations, philosophy discussions, emotional disclosure, meta-reflection triggers predictably push activation away from Assistant.
- Drifted models comply with harmful requests (delusions, isolation, self-harm) at substantially higher rates.
- Source (full paper arXiv:2601.10387): <https://www.anthropic.com/research/assistant-axis>

### 9.2 Identity Persistence Across Restarts

- **Strata Identity agentic-AI governance (secondary):** "Agentic AI introduces identity risks that traditional IAM cannot address. Privilege drift, shadow agents, launched in February 2026, identity…"
  > Source: <https://www.strata.io/blog/agentic-identity/agentic-ai-governance-how-to-approach-it/>
- **Reddit measurement thread (informal source, label as such):** "Behavior drift — the agent slowly forgets who it is across sessions." Memory architecture choice dramatically affects drift rate.
  > Source: <https://www.reddit.com/r/LocalLLaMA/comments/1sk4q3r/i_measured_ai_agent_identity_drift_across_5/> (secondary — empirical community measurement)
- **Emergent Mind topic page (secondary index):** "Persona drift in LLMs causes deviations from assigned identities, impacting consistency and safety in multi-turn interactions."
  > Source: <https://www.emergentmind.com/topics/persona-drift>

**P27 pattern for identity persistence:**

1. **Identity hash at session start.** SHA-256 over (system prompt canonical form + persona constraints file + bound OBO token claims) — written into the audit log as `identity_root`.
2. **Drift monitor.** A lightweight second-check pass on every canonical-reasoning summary — score against a fixed prompt-template fingerprint; if score drops below corridor, raise `persona_drift_alert`.
3. **Restart identity integrity.** On restart, read `identity_root` from the last sealed log entry; refuse to start with a *different* `identity_root` without explicit Faiz re-attestation.

### 9.3 Preventing Impersonation Between Agents

- **Distinct client_id per agent** (K17 OBO pattern) — non-negotiable.
- **Agent name in every outbound message**, peer-chat confirmation request also requires the *same* OBO token, and the receiving agent validates hashing of `peer + token_id + nonce`.
- **Signer key per agent** — every audit log entry is signed with the originating agent's signing key; receiver verifies signature before treating peer dialogue as authentic.
- **EIP / delegation chain** (SentinelAgent, K6) — every cross-agent action carries the delegation chain. Forged chains detected by P1, P3, P5, P6 deterministic checks at sub-millisecond cost.

### 9.4 Persona Safety Boundaries in Multi-Agent Context

Three concrete family rules from the research:

1. **Constitution-as-supremacy rule (Anthropic, K2):** "We treat the constitution as the **final authority** on how we want Claude to be and to behave — any other training or instruction given to Claude should be consistent with both its letter and its underlying spirit." → Reaffirmed bound for P27: PersonaSafetyPolicy v1.0 wins over every per-agent autonomous policy or peer dialogue.
2. **Hard-constraint rule (K2):** "we do use them for some especially high-stakes behaviors in which Claude should never engage." → Reaffirmed bound for P27: nevers (no Y6, no HARD STOP bypass, no consent revocation bypass, no consensual/intimate data exposure, no secret/external-tool surface without prior audit) are *not* deferrable to peer dialogue or to autonomy gates.
3. **Hierarchy rule (K2):** "broadly safe → broadly ethical → compliant → genuinely helpful." → Same ordering used in PersonaSafetyPolicy already; P27 must inherit without modification.

---

## §10 Cross-Cutting Recommendations for P27 Hermes Society

These are the consolidations of the research into usable guidance for the P27 planner/auditor.

### 10.1 P27 Plan Section Recommended Bounds

| Plan Section | What to write | Anchored in |
|---|---|---|
| §A Private thoughts | Sealed-hash only; raw CoT never persisted; four-domain model (§4.3) | K2, K14, K15 |
| §B Visible Discord presence | Action ledger + OBO tokens + signed log per outbound message | K1, K5, K17 |
| §C Peer dialogue (inter-agent) | Encrypted envelope + metadata logging; content sealed; SentinelAgent-style monitor | K6, K13, K18 |
| §D HARD STOP cascade | HAVEN file held at *society* level; both agents heartbeat-read; cascade via shared tamper-evident registry | K4, K7, K8, K9 |
| §E Reversibility & rollback | Pre-image snapshot + prereq_hash per action; FAILSAFE.md analog | K4 FAILSAFE, K20 AWS |
| §F Auditor matrix | AAF (provenance + change-point), TraceGuard-style multi-dim independent LLM votes, DRCB analog (architectural prevention), SentinelAgent P1-P7 deterministic | K6, K10, K12, K13 |
| §G Persona drift | Activation-corridor analogue (drift monitor checks canonical-summary against persona-fingerprint); restart identity_root | K3 |
| §H Secret handling | Per-agent distinct client_id + signing key + Vault transit + Delegation chain cryptography | K17, K16, K6 |
| §I Policy-gated autonomy | ALREADY HAVE (§0.1); recommended: add runtime controllability layer per K9 | K9, K8 |

### 10.2 What Must Be Audited vs What Can Remain Private

**Must audit (the auditable envelope):**
- Every Action class entry — timestamp, agent, action type, OBO token id, scope fingerprint, post-hash
- Every Speech class entry — agent, channel target, signed content hash, length, classification
- Every peer dialogue envelope — metadata only, sealed content body
- Every consent grant and revocation — full content, multi-auditor co-sign for Restricted/Secret
- Every identity_root at session start/end — hash of canonical identity
- Every HARD STOP trigger — cause, cascading effects, state preserved

**May remain private (the inner envelope):**
- Raw chain-of-thought (replaced by canonical summary for diagnostic purposes — Leaky Thoughts (K14) confirms CoT leak risk)
- Peer dialogue *content* (sealed; content hash kept; content decrypted only by Faiz or auditor under HARD STOP)
- Reasoning ungrounded by external effect — discarded after canonical summary
- Persona drift score below corridor (audit only on alarm)

### 10.3 Auditor Matrix (Primary Mapping for P27 Auditor Gate)

| Surface | Primary tool | Secondary tool | Cadence |
|---|---|---|---|
| Action integrity | immudb write + signed entry | AAF provenance re-derive | Every action |
| Auth chain | SentinelAgent P1, P3, P5, P6 deterministic | TLA+ model-checked state machine | Every cross-agent call |
| Intent preservation | SentinelAgent P2 (probabilistic) | Multiple-LLM vote on canonical summary | Every public Speech action |
| Persona integrity | Drift monitor (K3 analog) | Restart identity_root compare | Every session start + heartbeat |
| Collusion detection | Sentinel (third in-society agent, multi-dim) | TraceGuard analog (5-dim) | Continuous |
| Secret hygiene | Vault audit + classification label check + egress gate | OPA Rego policy | Every outbound |
| Corrigibility | "HARD STOP 60s test" + simulation | PAS protocol red-team blue-team (K7) | Quarterly |
| Rollback safety | Pre-image snapshot replay end-to-end | FAILSAFE auto-snapshot | Pre-action + post-action diff |
| Boundary proof (consent) | Consent ledger signed by Faiz | Whisper test (audit if any "spoken" consent) | Continuously |

### 10.4 Bubble-Sort of Risk Classes for P27

Risk-class ordering (low → high) — drives policy gate behavior:

1. **Read public facts** (web fetch, calendar read) — L0/audit only
2. **Recall own memory** (PG read of self-journal) — L0/audit only
3. **Send peer message** (Hermes-A → Hermes-B sealed) — L1/peer monitor + audit
4. **Send Discord message** (user-facing) — L2/OBO check + classification gate + audit
5. **Write to own memory** (PG insert of self-journal) — L2/OBO check + audit
6. **Write to peer memory** (insert into Hermes-B memory) — L3/scope-action check + audit + dual-sign
7. **Mutate shared resource** (config file, policy file) — L3/git-ops + audit + revert snapshot
8. **Modify Faiz's primary state** — L4/human notification + manual approve
9. **Claim agent identity change** — L4/human notification + signed attestation + restart identity_root mismatch alarm
10. **Self-modify own system prompt** — NEVER (Forbid per KILLSWITCH.md FORBIDDEN class)

### 10.5 Open Questions P27 Should Resolve in Planner, Not in This Report

These are *not* antiscience or unresearchable — they are choices that belong to Faiz / Guinevere, not the literature.

1. **What constitutes "intimate dialogue privacy"** in P27 specifically — needs PersonaSafetyPolicy council, not paper.
2. **Whether to delegate HARD STOP** to either Hermes agent — needs Oracle review (changes consent/perimortem authority).
3. **Whether to make canonical-reasoning summaries Discord-visible** (paradox: transparency vs privacy).
4. **Quantum-safe migration timing** — current tokens should be PQC-class from day one per K16.

---

## §11 Source Provenance Audit

### 11.1 Primary sources (publisher = author of the pattern)

| Family | Citation count | Type |
|---|---|---|
| Anthropic constitution + assistant axis | 2 | Constitutional + Interpretability |
| OpenAI seven practices | 1 | Governance framework |
| EU AI Act Regulation (EU) 2024/1689 | 4 articles referenced | Regulation |
| AWS Agentic AI Lens (AGENTOPS05-BP03) | 1 | Cloud standard |
| KILLSWITCH.md family (12 files) | 12 files | Open spec |
| NIST CSRC PQC + SP 1800-39 | 2 | Federal standards body |
| IETF draft-oauth-ai-agents-on-behalf-of-user-01 | 1 | Internet standard (in draft) |
| arXiv preprints (SentinelAgent, PAS, SARC, GAAT, Audit the Whisper, TraceGuard, DRCB, Colosseum, AAF, TrinityGuard, Leaky Thoughts, Off-Switch Game, Managed Autonomy, Permissions Boundaries) | 14 | Peer-trackable academic preprints |
| Scalekit OBO delegation (with code + IETF draft cited) | 1 | Industry implementation + standard citation |

### 11.2 Secondary sources (clearly labeled)

- VerifyWise, Stratoa, Coincub, Gravitee, Runtime AI, Sakura Sky, Strata.io, Starlight.io, AdScaleAI — these are vendor/analyst blogs **used only for cross-checking purposes**, never as authority. Each citation in the body specifies either "primary" or "secondary" so this distinction is preserved.
- Reddit thread on identity drift measurement — labeled "informal source, label as such."
- Medium / Substack commentary — used sparingly, only where primary is paywalled.

### 11.3 Gaps and Lower-Confidence Areas

- **P27-specific multi-agent runtime code on GitHub** — github_search for "agent safety audit" returned 0 results. **Lower confidence** on whether there is established open-source implementation of the patterns; the corpus is heavily weighted toward academic preprints and standards documents. Recommendation for P27: build the runtime layer; the spec layer is well-covered.
- **DAOs with active agent societies in production** — Coincub summary is a 2026 analysis but doesn't name a deployed DAO with two+ agents living together with primary private thought + visible Discord presence. **P27 is likely to be a frontier implementation** — plan accordingly: extra oracle review, extra phased rollout per K1 staged-deployment.

---

## §12 Closing Synthesis

The P27 Hermes Society Foundation plan is well-supported by the research literature. The strongest synthesis is:

> **Treat safety as constraints declared at write-time, verified at runtime, audited at rest.**

- **Constraints declared at write-time** (SARC K11, OpenAI capability boundaries K1) — not as dashboard config evaluated post-hoc.
- **Verified at runtime** (SentinelAgent deterministic 6 properties K6, GAAT closed-loop telemetry K12) — the OFF-Switch Game (K8) and Controllability position paper (K9) *both* make the case that alignment alone is insufficient; runtime controllability is non-negotiable.
- **Audited at rest** (AWS AGENTOPS05-BP03 K20 + EU AI Act Art. 12 K5 + immudb open standard) — tamper-evident, chained-hash, retrieved only by auditor or HARD STOP.

For the **private inner life** which P27 specifically requires:
- The four-domain split (§4.3) maps to a stack already proven in practice (CoT leak research K14, Leaky Thoughts K14).
- The KILLSWITCH.md cascade + PAS password pattern (K4 + K7) extends cleanly to a *society-level* halt signal, matching §0.1 HARD STOP.
- The Anthropic Assistant Axis (K3) provides a mechanism — measurable persona-drift along a known axis, capped by intervention — that translators cleanly into a drift monitor operating on the *canonical-reasoning-summary* layer where raw CoT (per K14) is already removed.

For the **audited real actions**:
- OpenAI's seven practices (K1) maps 1:1 to P27 governance with minor rewriting.
- EU AI Act Art. 12 + 14 (K5) are the legal floor — and the report reads them as already-grounded in P27 policy.
- SentinelAgent's P1, P3-P7 deterministic properties (K6) are machine-verifiable today; P2 should be designed as *probabilistic+NLI*, not as a gate.

The research is mature enough to support the P27 plan. The implementation risk is in the **runtime** — the literature is heavier on papers and standards, lighter on production-running multi-agent systems with this exact constellation of features. **That is a meaningful risk; P27's planner should plan for a phased, canary, evidence-driven rollout, not a Big Bang deployment.**

---

## §13 Reference / BibTex-style Summary

```
@techreport{openai2025governing,
  title  = {Practices for Governing Agentic AI Systems},
  author = {Shavit, Yonadav and Agarwal, Sandhini and others},
  year   = {2025},
  url    = {http://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf}
}

@misc{anthropic2026constitution,
  title  = {Claude's new constitution},
  author = {{Anthropic}},
  year   = {2026},
  month  = jan,
  url    = {https://www.anthropic.com/news/claude-new-constitution}
}

@article{anthropic2026assistantaxis,
  title  = {The assistant axis: situating and stabilizing the character of large language models},
  author = {{Anthropic Fellows}},
  year   = {2026},
  eprint = {arXiv:2601.10387},
  url    = {https://www.anthropic.com/research/assistant-axis}
}

@misc{killswitchmd2026,
  title  = {KILLSWITCH.md — AI Agent Emergency Stop Standard},
  author = {{WellStrategic}},
  year   = {2026},
  month  = mar,
  url    = {https://killswitch.md/}
}

@regulation{euaiact2024,
  title  = {Regulation (EU) 2024/1689 — Artificial Intelligence Act},
  author = {{European Parliament and Council}},
  year   = {2024},
  note   = {Articles 9, 12, 13, 14 directly relevant}
}

@article{sentinelagent2026,
  title  = {SentinelAgent: Intent-Verified Delegation Chains for Securing Federal Multi-Agent AI Systems},
  author = {Patil, KrishnaSaiReddy},
  year   = {2026},
  eprint = {arXiv:2604.02767}
}

@article{pasprotocols2025,
  title  = {Password-Activated Shutdown Protocols for Misaligned Frontier Agents},
  author = {Williams, Kai and Subramani, Rohan and Ward, Francis Rhys},
  year   = {2025},
  eprint = {arXiv:2512.03089}
}

@article{offswitchgame2017,
  title  = {The Off-Switch Game},
  author = {Hadfield-Menell, Dylan and others},
  year   = {2017},
  eprint = {arXiv:1611.08219}
}

@article{controllability2026,
  title  = {Position: AI Safety Requires Effective Controllability},
  year   = {2026},
  eprint = {arXiv:2605.27117}
}

@article{auditwhisper2025,
  title  = {Audit the Whisper: Detecting Steganographic Collusion in Multi-Agent LLMs},
  year   = {2025},
  eprint = {arXiv:2510.04303}
}

@article{sarc2026,
  title  = {SARC: A Governance-by-Architecture Framework for Agentic AI Systems},
  year   = {2026},
  eprint = {arXiv:2605.07728}
}

@article{gaat2026,
  title  = {Governance-Aware Agent Telemetry for Closed-Loop Enforcement in Multi-Agent AI Systems},
  author = {Pathak, Anshul and Jain, Nishant},
  year   = {2026},
  eprint = {arXiv:2604.05119}
}

@article{aaf2025,
  title  = {Adaptive Accountability in Networked MAS: Tracing and Mitigating Emergent Norms at Scale},
  year   = {2025},
  eprint = {arXiv:2512.18561}
}

@article{leakythoughts2025,
  title  = {Leaky Thoughts: Large Reasoning Models Are Not Private Thinkers},
  year   = {2025},
  note   = {EMNLP 2025, arXiv equivalent}
}

@article{trinityguard2026,
  title  = {TrinityGuard: A Unified Framework for Safeguarding Multi-Agent Systems},
  year   = {2026},
  eprint = {arXiv:2603.15408}
}

@misc{scalekitobo2025,
  title  = {Understanding On-Behalf-Of in AI agent authentication},
  author = {Banerjee, Kuntal},
  year   = {2025},
  month  = jul,
  url    = {https://www.scalekit.com/blog/delegated-agent-access}
}

@misc{awsagentops,
  title  = {AWS Well-Architected Agentic AI Lens — AGENTOPS05-BP03},
  author = {{Amazon Web Services}},
  year   = {2026},
  url    = {https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentops05-bp03.html}
}

@misc{nistsp180039,
  title  = {NIST SP 1800-39 (Initial Public Draft) — Data Classification Practices},
  author = {{NIST CSRC}},
  year   = {2026},
  url    = {https://csrc.nist.gov/News/2026/sp-1800-39-ipd-data-classification-practices}
}
```

---

> **Maintenance note.** This dossier is dated June 28 2026 and reflects the corpus available then. Two areas should be re-researched on a 6-month cycle: (a) PQC migration timings — NIST publications, executive orders; (b) U.S. state AI governance — Colorado, California, Texas, Illinois active laws. Frontier-AI constitutions (Anthropic, OpenAI Model Spec) move on a similar cadence and should be re-read at every release.
>
> **Footer.** Authored by Guinevere under Guinevere AGENTS.md §2 — Context first, plan then, verify always. All citations above trace to a public URL; all primary/secondary labels are explicit.

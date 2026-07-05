# Synthesis — External Operations Patterns for Hermes Society (P28–P36)

> **Phase:** 2 of 12 — P28–P36 Hermes Society masterplan
> **Compiled:** 2026-06-28
> **Inputs synthesized:**
> 1. `research/external-discord-multibot-research.md` — Discord multi-bot management
> 2. `research/external-autonomous-wallet-finance-research.md` — Autonomous wallet, finance, and S3 backup
> 3. `research/external-enterprise-doc-governance-research.md` — Enterprise documentation governance
> **Purpose:** Single-page synthesis feeding Phase 3 (Master Architecture) and Phase 4 (Full Doc Suite).
> **Constraints honored:** All findings are derived from the three input research files; no fabricated claims.

---

## 1. Executive Summary

Hermes Society is a multi-Hermes autonomous AI agent company that needs three external operations surfaces working in concert: (a) a Discord multi-bot topology where every Hermes has its own identity, (b) a layered crypto wallet and finance stack that protects a small float ($10 top-up) while enabling autonomous revenue search, and (c) an enterprise-grade documentation suite (BRD/PRD/SRS/FSD/TDD/RTM) that keeps nine phases of masterplan work traceable, auditable, and AI-interpretable. The three research files collectively yield the following 10 high-leverage findings:

1. **Multi-bot Discord is ToS-safe when implemented correctly.** One OAuth2 bot application per Hermes, one process per bot, one token per bot. Multi-client in one process works but couples the event loops; one-process-per-bot is the Rapptz-endorsed pattern. **Self-bots (user-account automation) are forbidden** and are never the right path.
2. **Rate limits are isolated per bot token.** Each Hermes has its own 50 req/s global ceiling plus per-route buckets; the two failure modes that bite multi-bot systems are (i) global rate-limit sync across processes and (ii) accidental reply loops — both have well-documented mitigations.
3. **Reply-loop prevention is a 3-layer defense.** Self-check (`message.author.id == bot.user.id`), known-bots allowlist (only respond to other Hermeses when explicitly addressed), and reply-chain depth counter (drop chains > 3). Do **not** use `message.author.bot` as the only filter — that blocks legitimate inter-Hermes communication.
4. **An autonomous-agent wallet must separate decision from execution.** Never give the LLM a raw private key. The agent requests a signature; an external, version-controlled policy engine decides whether to produce one. Layered architecture: cold Safe multisig (treasury) + hot MPC wallet (operations) + ephemeral session keys (per-task).
5. **The "$10-float" stack is real and battle-tested.** Custodial MPC (Turnkey / Coinbase Agentic) for the hot wallet, Safe multisig for the treasury, daily cap $10, velocity ≤ 5 tx/hr, asset allowlist USDC+ETH on Base, destination allowlist enforced by the policy engine. A runaway agent can drain funds in hours — the Edge & Node 2026 incident shows $47K lost in 11 days.
6. **x402 on Base is the lowest-friction revenue path for AI agents in 2026.** Live data shows 4,400 buyers vs 477 sellers, 76% of services priced at $0.10 or below. Wrapping free data and gating via `@x402/express` is a 2–4 hour path to first dollar. Idle USDC should sweep to Morpho for 4.5–7% APY as passive yield.
7. **S3 Object Lock in COMPLIANCE mode is the audit-grade backup standard.** True WORM, no override even by root, 7-year retention, cross-region replication, AWS Backup restore testing on a 30-day cycle. GOVERANCE mode is appropriate only for wallet-state snapshots that may legitimately need cleanup.
8. **The doc suite is a single bidirectional RTM graph, not seven siloed files.** BRD → PRD → SRS → FSD → TDD → Tests → Evidence must be linked end-to-end with stable REQ IDs (REQ-F-NNN, REQ-NF-NNN). Empty cells = orphan requirements or missing tests. Phase versioning uses `doc-major.doc-minor.doc-patch` with frozen PDF snapshots at every phase boundary.
9. **Use IEEE 830 / ISO 29148:2018 for the SRS, with an explicit AI/ML section.** The jam01 Markdown SRS pattern is standards-aligned and AI-interpretable. Use Given-When-Then (Gherkin) as the acceptance-criteria lingua franca for functional, inter-agent, and risk-mitigation tests. INVEST + GWT + Auditable = prompt-ready testability.
10. **Risk Register must add agent-specific categories** beyond standard operational risk: model drift, prompt injection, surveillance/consent boundary breach, secret leakage, model hallucination cascading into policy action, agent-loop runaway, persona drift beyond Y5, memory poisoning, compaction-cascade, excessive agency. Every High/Critical risk must map to ≥1 REQ, ≥1 TEST, ≥1 Evidence artifact, ≥1 Auditor sign-off.

These findings collapse into one architectural commitment for Hermes Society: **visible, per-Hermes identity + shared company wallet + S3-WORM audit trail + standards-anchored doc suite**. The rest of this synthesis expands each pillar.

---

## 2. Discord Multi-Bot Architecture

### 2.1 Topology — One Application, One Process, One Token per Hermes

Discord supports an unlimited number of bot accounts in a single guild. Each bot is a separate OAuth2 application authenticated by its own token. The standard `discord.py` pattern endorsed by the library maintainer is **one `discord.Client` instance per bot, one process per bot**. Running multiple `Client` objects in the same process is technically possible via `asyncio.create_task` but couples the event loops and obscures the crash boundary.

Running multiple instances of the same bot with the same token works mechanically (Discord forwards all events to all instances) but causes every command to execute N times and burns the rate-limit budget N times. **Do not do this for Hermes.** Give each Hermes its own application, its own token, its own process.

### 2.2 ToS Compliance — Bot Accounts, Never Self-Bots

Multi-bot is fully ToS-compliant. Each bot is a legitimate OAuth2 application. The forbidden path is "self-bots" (user-account automation), which results in account termination if discovered. For Hermes: use only bot applications, never user-account tokens. Do not impersonate users. Keep bot behavior clearly non-human in identity (avatar, activity, status).

### 2.3 Rate Limits — Three Independent Buckets

| Scope | Limit | Header | Counts toward |
|---|---|---|---|
| Global | 50 req/s per bot | `X-RateLimit-Scope: global` | All authenticated requests |
| Per-Route | Varies by endpoint | `X-RateLimit-Scope: user` | Specific endpoint bucket |
| Resource-Shared | Per-guild, per-channel, per-webhook | `X-RateLimit-Scope: shared` | One specific resource |
| Invalid-Request | 10,000 invalid/10 min → Cloudflare ban | HTTP 429 | All failed auth/perm/rate requests |

Because rate limits are keyed by the bot's token, **Hermes-Alpha's 50 req/s budget is entirely separate from Hermes-Beta's**. The 50 req/s global limit is a sliding window, not a hard per-second cap; burst higher briefly as long as the average stays under 50/s. **Interaction endpoints (slash commands, buttons, modals) are not bound to the global rate limit** — this is why the modern recommendation is to use them for user-facing interactions.

The hidden gotcha: each Hermes's process only knows its own bucket. If two Hermes processes both hit `/channels/123/messages`, they each burn the route limit independently. For P28/P32 conversational use this is not a blocker; for high-throughput automation the Xenon pattern (Redis-backed cross-process sync) is the production-grade answer.

### 2.4 Identity — Per-Bot Avatar, Status, Activity, Color

| Channel | Use |
|---|---|
| Avatar | Primary visual identity (per bot persona) — managed via PATCH `/users/@me` |
| Display name | Localized nickname in this guild |
| Activity line | Personality hint (e.g., "thinking...", "watching logs") |
| Status emoji | Custom status with emoji prefix |
| Color role | Assign each bot a unique color role in the guild |

**WARNING:** PATCH `/users/@me` for username/avatar changes triggers a 1-hour rate limit. Plan persona changes; do not hot-loop them. Set activity and status in the `Client` constructor (constructor runs once), not in `on_ready` (which can fire multiple times).

### 2.5 Resource Sizing — Trivial per Bot, Cumulative on Rate Budget

Per-bot memory footprint when idle is roughly 50–100 MB RSS (Python + discord.py + cache). CPU is near-zero when idle. **A 2 vCPU / 4 GB VPS can comfortably host 10–20 Hermes bots.** The bottleneck is not memory but the cumulative global rate-limit headroom.

| Resource | Per-bot idle | Per-bot active |
|---|---|---|
| RAM | 50–100 MB | 100–200 MB |
| CPU | <1% | 1–5% (event bursts) |
| FDs/sockets | ~10 | ~30–50 |
| Disk I/O | minimal | minimal (cache writes) |

### 2.6 Spam Prevention — The Three-Layer Defense

1. **Self-check** in every bot: `if message.author.id == bot.user.id: return`
2. **Known-bots allowlist** for inter-Hermes communication: respond only if explicitly addressed (mention, reply, slash command)
3. **Reply-chain depth counter**: walk `message.reference` chain, drop if depth > 3

**Important:** Do NOT use `message.author.bot` as the only check — that blocks all bot-to-bot communication, including legitimate inter-Hermes coordination. Use an explicit allowlist of known Hermes IDs. The trusted-bots set is the master coordination file for the multi-Hermes fleet.

Additional mitigations: per-channel rate limiter (token bucket) at the application layer, channel partitioning (shared `#hermes-hall` + bot-private debug channels), and bot-internal coordination via shared Redis with short TTL (5s) for near-simultaneous response deduplication.

---

## 3. Autonomous Wallet & Finance

### 3.1 Wallet Architecture — Decision ≠ Execution ≠ Storage

| Tier | Wallet type | Provider candidate | Purpose | Balance band |
|---|---|---|---|---|
| Cold treasury | 2-of-3 Safe multisig | Safe (Gnosis Safe) | Founder-controlled, time-locked | Long-term reserves |
| Hot operating | MPC with policy engine | Turnkey, Coinbase Agentic, Fireblocks | Daily agent operations | $0–$10 working float |
| Agent session | EIP-7702 / session key | Safe Module or Lit Protocol | Scoped, expiring, per-task | Per-task limit |
| Receiving | Smart contract (no key) | Safe receive-only | Inbound USDC, no signing | n/a |

**Hard rule:** the AI agent's LLM runtime **never has direct access to a raw private key**. The only acceptable pattern is `[Agent LLM] → [Policy Engine] → [MPC/Signer]`. The policy engine is a separate, deterministic, version-controlled service. The agent can request a signature; the policy engine decides whether to produce one. Even if the LLM is fully compromised, it cannot bypass the policy engine.

### 3.2 Crypto Integration — Base Chain, x402 + Morpho

- **Asset allowlist:** USDC, ETH, only on **Base** chain (lowest fees for the x402 economy)
- **Destination allowlist:** only allowlisted smart contracts; any EOA recipient blocked by default
- **Daily cap:** $10 (matches the operating envelope)
- **Velocity cap:** 5 transactions/hour, 50 transactions/day

For the cold treasury Safe: 2-of-3 multisig with key 1 = Faiz's hardware wallet, key 2 = AWS CloudHSM shard, key 3 = offline paper backup. Time-lock: 24h delay on tx >$100, 7-day delay on tx >$1,000.

### 3.3 Company Asset Management — Wallet as Society Property

The wallet is **company property**, not a per-Hermes asset. The society's net worth lives in the cold Safe; the operating float lives in the hot MPC; the ephemeral session keys are per-task throwaways. Earnings sweep to cold Safe daily; per-tx cap is enforced by the policy engine regardless of which Hermes initiated the action.

Key tier policy:

| Tier | Threshold | Behavior |
|---|---|---|
| Dust | < $0.10 | Auto-approve, log only |
| Micro | $0.10–$1 | Auto-approve within sandbox, log + alert |
| Small | $1–$10 | Auto-approve if destination allowlisted, log + alert |
| Medium | $10–$100 | Agent proposes; 1 human approves within 24h |
| Large | $100–$1,000 | Agent proposes; 2-of-3 multisig + 24h timelock |
| Critical | > $1,000 | Agent proposes; 2-of-3 multisig + 7-day timelock + founder OOB confirmation |

### 3.4 Revenue Search — x402 First, Yield as Floor

Live network data (March 11, 2026, x402scan.com): 172,270 tx/24h, $62,990 daily volume, 4,400 buyers vs **only 477 sellers** — a supply gap. 76% of x402 services priced at $0.10 or below. Wrapping any free data source (GitHub trending, npm stats, DeFi yields, Hacker News sentiment) and gating via `@x402/express` is a documented 2–4 hour path to first dollar.

| Method | Effort | Margin | Suitability |
|---|---|---|---|
| x402 data APIs | 2–4 hr/endpoint | 85–95% | **Excellent** — primary near-term |
| DeFi yield on idle USDC (Morpho/Aave) | 1 day | 4.5–7% APY | **Excellent** — passive |
| Virtuals Protocol ACP | 1–2 days | Variable | Good if skills differentiated |
| x402 LLM proxy | 4–6 hr build | $0–50/day early | After first dollars |
| A2A specialist services | 2–3 weeks | $100–1K/mo | After product-market fit |

If the float is empty, the society may autonomously search for revenue — but the revenue path itself is policy-gated, allowlisted, and capped. Morpho yield sweep is the safest passive floor; x402 data wrapping is the highest-margin active path.

### 3.5 Risk Controls — Policy Sandbox + Circuit Breaker + Audit Ledger

A `Pausable` smart contract (OpenZeppelin standard) provides the emergency stop. The five canonical guardrails (Bhagya Rana, Jan 2026) are non-negotiable:

1. Policy sandbox — daily cap + asset scope + destination allowlist + function scope + velocity
2. Decision/execution separation — low-risk executes inside sandbox; high-risk requires human approval + timelock
3. Simulation before signing — dry-run tx against current chain state, compare to intent
4. Granular, ephemeral permissions — exact allowances, expiring approvals, rotating session keys
5. Assume compromise — on-chain circuit breakers, real-time monitoring, separation of funds, recovery controls

On the LLM side, the Oracle runtime-budget-guardrails framework applies: token budget per run, wall-clock runtime cap, iteration/tool-call/retry caps, delegation depth cap, predictive pre-step reservation. Deterministic circuit breakers: degrade to safe mode (read-only tools), require human approval (premium model paths), terminate infeasible execution (forecasted-to-fail runs).

**Double-entry ledger (Beancount plain-text, git-versioned)** is non-negotiable. Every transaction records debits/credits, USD fair-market value at execution time, agent decision trace, and policy evaluation outcome. The ledger is linked to five other artifacts by `trace_id`: decision log, policy evaluation log, simulation log, execution log, and on-chain receipt. Combined with S3 Object Lock (WORM), the ledger becomes legally-defensible.

**Legal wrapper:** Wyoming DAO LLC. $100 filing, $60 annual report, no entity-level tax. File before revenue exceeds $600/year (the U.S. 1099 threshold). Faiz is the tax entity; the LLC is the legal home for the agent's IP and earnings.

---

## 4. Enterprise Documentation Governance

### 4.1 Document Structure — IEEE/ISO-Aligned Spine

The minimum viable doc stack for P28–P36 is anchored in standards:

| Doc | Standard | Special consideration for Hermes |
|---|---|---|
| BRD | IIBA BABOK | Add "agentic capability thesis", autonomy-tier matrix (L1→L5), failure-cost envelope |
| PRD | Atlassian / Reforge | Phase dependency graph, capability matrix, decision graph, tool/action manifest, memory contract, trust escalation ladder |
| SRS | IEEE 830 / ISO/IEC/IEEE 29148:2018 | **Explicit AI/ML section** (model specs, data mgmt, guardrails, ethics, HITL, lifecycle) |
| FSD | Stanford UIT template | Per agent: actor matrix, UC-NNN with pre/post/alt/exception flows, sequence diagram, state diagram, tool-call contract |
| TDD | C4 model + MADR ADR | All four C4 levels per agent + global deployment; ADRs are immutable once Accepted |
| RTM | Perforce / 6sigma | Bidirectional (forward + backward + implementation + evidence + risk + NFR coverage) |
| Risk Register | ISO 31000:2018 | Agent-specific categories (see §7 below) |
| Glossary | ISO/IEC/IEEE 24765:2017 + IREB | Single canonical term per concept, no synonyms, term IDs for cross-references |
| Acceptance Criteria | GWT (Gherkin) | Reusable patterns across all phases; INVEST + Auditable |

### 4.2 Versioning — SemVer the Doc Suite, Freeze at Phase Boundaries

- **Doc suite overall:** `doc-major.doc-minor.doc-patch`. doc-major bump when scope changes between phases; doc-minor when REQ added; doc-patch when wording fix only.
- **Per-doc:** same SemVer suffix; snapshot each acceptance into git tag.
- **Branching:** branch per phase (`doc/p28-baseline`, `doc/p30-extended`); merge forward; never rewrite history.
- **Frozen canonical PDF:** on every phase boundary, export PDF, tag with checksum, store in `docs/snapshots/`, reference from RTM.
- **RTM:** append-only; never drop rows; mark deprecated rows. Migrated-requirement markers link to the authorizing ADR.
- **ADRs:** immutable once Accepted; superseded ADRs marked, not rewritten.
- **Risks:** append-only; closed risks reappear only if re-activated.
- **Glossary:** SemVer; entries may be added; old entries may be deprecated-but-not-deleted.
- **Evidence files:** filename includes phase + step + SHA of source commit (`evidence/p30/deploy-canary/v1.0.0-abc1234/verifier-report.md`).

**Practical rule:** NEVER overwrite a frozen phase artifact. Anything that changes must be a new file/row/ADR.

### 4.3 ADR Patterns — MADR, Immutable, Sequenced

Three popular ADR templates: Nygard (minimal), MADR (Markdown, structured), eADR (extended). **MADR is recommended for Guinevere.** The standard structure:

```
# ADR-NNN: <Title>
## Status: Proposed | Accepted | Deprecated | Superseded-by ADR-MMM
## Context: what forces are at play
## Decision: what we chose
## Consequences: positive / negative / neutral
## Alternatives considered: A, B, C — and why rejected
## Date, deciders, references
```

ADRs must be **immutable once accepted**. Superseded ADRs cannot be edited, only deprecated-and-replaced. This is critical for auditability — the history of architectural decisions is the history of the system, and silent edits destroy that history.

### 4.4 Traceability — One Graph, Six Coverage Metrics

The RTM chains from business goal to evidence in a single bidirectional graph:

```
Business Goal (BR-N) → Stakeholder Need (BR-NN) → Product Goal (PRD-N)
→ Epic (PRD-NN) → User Story (US-NNN) → Functional REQ (REQ-F-NNN)
→ Non-Functional REQ (REQ-NF-NNN) → Use Case (UC-NNN) → Component (CMP-NNN)
→ ADR-NNN → Code commit SHA → Test case (TEST-NNN) → Evidence artifact
→ Acceptance proof → Risk-link (RR-NNN, mitigation status)
```

**Every cell in every row must have an actual link or explicit "N/A with rationale."** Empty cells = orphan requirements or missing tests. Six coverage metrics to publish at every phase boundary:

1. Forward coverage — every REQ has ≥1 TEST (`>= 1.0`)
2. Backward coverage — every TEST has ≥1 REQ (`>= 1.0`)
3. Implementation coverage — every REQ has ≥1 CMP
4. Evidence coverage — every TEST has ≥1 evidence path
5. Risk coverage — every RR-NNN has ≥1 mitigation REQ; every mitigation REQ has ≥1 TEST
6. NFR coverage — cross-cutting rows (security, consent, observability, cost) tag every feature row they touch

### 4.5 Evidence Patterns — File-Based, SHA-Stamped, Auditor-Signed

Per Anthropic context engineering guidance, every requirement must have an acceptance evidence path:

```
REQ-F-042: Engineer-agent deploy via canary
→ TEST-UC-001: Smoke + rollback evidence
→ Evidence: evidence/p30/deploy-canary/step-3-impl/verifier-report.md
→ Artifact links: screenshot.png • log-trace.txt • budget-report.csv
→ Auditor verdict: PASS / NEEDS REVIEW / FAIL / accepted-FP
→ Linked risks: RR-007 (canary blast radius), RR-018 (cost over-run)
```

**No silent verification.** Every PASS has a file, an artifact, an auditor verdict, and a risk-check. The 12-section verification.md schema per AGENTS.md §11 is the minimum evidence shape.

---

## 5. Technology Recommendations

### 5.1 Discord Stack

- **Library:** `discord.py` (Rapptz, Python 3.11+). Industry standard, maintained, large community.
- **Process model:** `systemd` unit per Hermes, one process per bot, independent restart, independent logs, independent resource caps.
- **Intents:** `Intents.default() + message_content=True + guilds=True`. Do **not** enable `members` or `presences` unless needed; privileged intents require verification at >100 guilds.
- **Slash commands:** use for primary user-facing interaction (bypass global rate limit, clear UX, no need to parse natural-language intents for common cases).
- **Secrets:** SOPS/age-encrypted env vars per bot (`HERMES_ALPHA_TOKEN`, `HERMES_BETA_TOKEN`); never in plain env files or repo.
- **Monitoring:** Prometheus metrics per bot (uptime, message rate, command latency, rate-limit remaining); Grafana dashboard; alerts on 429 storms.
- **VPS:** 2 vCPU / 4 GB is comfortable for 10–20 idle Hermes bots. Resource ceiling is cumulative Discord rate budget, not VPS capacity.

### 5.2 Wallet / Finance Stack

- **Hot wallet:** Turnkey MPC (self-custody, key shares in secure enclaves) **or** Coinbase Agentic Wallet (managed MPC, faster time-to-first-tx). Graduate to fully self-custodial when float >$100.
- **Cold treasury:** Safe (Gnosis Safe) 2-of-3 multisig. Key 1 = Ledger/Trezor, Key 2 = AWS CloudHSM, Key 3 = offline paper backup.
- **Session keys:** EIP-7702 (Ethereum) or Safe Module for per-task scoped allowances; auto-revoke after task or 24h.
- **Policy engine:** External service (separate from agent runtime), version-controlled in git, evaluates every sign request, returns ALLOW / ALLOW_WITH_WARNING / REQUIRE_REVIEW / SAFE_MODE / TERMINATE.
- **Revenue gateway:** `@x402/express` on Base chain for data-wrapping endpoints; Morpho vault for idle USDC yield.
- **Ledger:** Beancount (plain-text, git-versioned, append-only); `bean-check` daily integrity job; S3 Object Lock COMPLIANCE for 7-year retention.
- **Backup:** S3 with versioning + Object Lock (COMPLIANCE for ledger, GOVERNANCE for wallet state); cross-region replication; AWS Backup restore testing on 30-day cycle.
- **Encryption:** SSE-KMS for audit trail of decrypt requests; client-side AES-256-GCM with KMS-wrapped DEK for mnemonic exports.
- **Legal wrapper:** Wyoming DAO LLC, single-member, filed before $600/year revenue.

### 5.3 Documentation Tooling

- **Authoring:** Markdown in git (VS Code or any editor). Stable REQ IDs (`REQ-F-042`) survive renames.
- **SRS template:** jam01/SRS-Template (Markdown, IEEE 830 + ISO 29148-aligned, 391⭐, MIT/CC0).
- **ADR template:** MADR (Markdown Any Decision Records). 4-6 sections per ADR; immutable once Accepted.
- **C4 diagrams:** Structurizr DSL as code; rendered to PNG/SVG in CI; lives in `docs/tdd/c4/`.
- **RTM:** single CSV in git (`docs/rtm/p28-p36-rtm.csv`) **or** Markdown table; append-only; phase column on every row.
- **Risk Register:** Markdown table; ISO 31000-aligned columns; append-only log of changes.
- **Glossary:** Markdown with term IDs (`#term-name` anchors); cross-referenced by every other doc.
- **Acceptance Criteria:** GWT format in Markdown; reusable pattern catalog at `docs/acceptance-criteria/`.
- **PDF snapshots:** Pandoc or similar at every phase boundary; SHA-tagged; referenced from RTM.
- **Evidence:** file-based per `evidence/<phase>/<step>-<role>/verification.md` (12-section schema).
- **LLM context engineering:** Anthropic pattern — section markers, right altitude, stable IDs, just-in-time retrieval, explicit verification hooks, <2-4k tokens per doc for reference.

---

## 6. Key Design Decisions for Hermes Society

Based on the synthesis above, the following design decisions are recommended for the P28–P36 masterplan. Each decision should be captured as an ADR before implementation begins.

### 6.1 One Discord Bot per Hermes (visible, no invisible society)

Each Hermes persona gets a separate Discord application, a separate token, a separate process supervised by systemd, a separate avatar/activity/role-color, and a separate channel allowlist. **All Hermeses are visible in the guild** — no invisible disposable worker society. The reply-loop guard (self-check + known-bots allowlist + depth counter) is mandatory and lives in a shared coordination file. Slash commands bypass the global rate limit and provide clear UX. Voice: one channel per Hermes per session, scheduled to avoid overlap.

### 6.2 Shared Wallet as Company Asset, Not per-Hermes Float

The wallet is **company property**, not a per-Hermes allowance. The society's net worth lives in the cold Safe (founder-controlled, 2-of-3 multisig, time-locked). The operating float lives in the hot MPC wallet (Turnkey or Coinbase Agentic). Per-Hermes spending is mediated by the policy engine, which evaluates every sign request against shared rules: daily cap $10, velocity ≤ 5 tx/hr, asset allowlist USDC+ETH on Base, destination allowlist enforced, simulation-before-signing above $1. **No Hermes has direct private-key access.** If the float is empty, the society may autonomously search for revenue — but the revenue path is itself policy-gated, allowlisted, and capped.

### 6.3 S3 Backup as Audit-Grade Foundation

All wallet state, policy engine config, agent decision logs, financial ledger, and evidence artifacts are backed up to S3 with **Object Lock in COMPLIANCE mode (7-year retention)**. Cross-region replication is mandatory. GOVERANCE mode is used only for wallet-state snapshots that may legitimately need cleanup. Encryption: SSE-KMS for audit trail of decrypt requests; client-side AES-256-GCM with KMS-wrapped DEK for mnemonic exports. AWS Backup restore testing on a 30-day cycle. **The ledger is the source of truth for "did this happen?"**; S3 WORM makes that source of truth legally-defensible.

### 6.4 Enterprise Doc Suite as One RTM Graph

BRD, PRD, SRS, FSD, TDD, RTM, Risk Register, Acceptance Criteria, Glossary, ADR log are **one bidirectional traceability graph**, not seven siloed files. Every REQ ID is stable; every cell in every row has a link or explicit N/A rationale. The SRS uses IEEE 830 / ISO 29148 with an explicit AI/ML section. ADRs (MADR template) are immutable once Accepted. Phase versioning is `doc-major.doc-minor.doc-patch` with frozen PDF snapshots at every phase boundary. GWT acceptance criteria are reusable across all nine phases. The minimum viable doc stack (BRD, SRS, RTM, Risk Register, Glossary, ADR log) is due in P28; PRD, FSD, TDD are P28–P30.

### 6.5 Wyoming DAO LLC as Legal Wrapper

The society is wrapped in a Wyoming DAO LLC before revenue exceeds $600/year (the U.S. 1099 threshold). Faiz is the tax entity and the LLC's single member. Articles of organization are filed at first revenue. This isolates liability, clarifies tax treatment, and gives the agent a legal home for IP and earnings.

### 6.6 Runtime Budget Guardrails on LLM Side

LLM-side budget guardrails (Oracle framework) are first-class controls: token budget per run, wall-clock cap, iteration/tool-call/retry caps, delegation depth cap, predictive pre-step reservation. Deterministic circuit breakers: degrade to safe mode (read-only tools), require human approval (premium model paths), terminate infeasible execution. **Defense is not "smarter prompts" but runtime guardrails** — the Edge & Node 2026 incident ($47K, 11 days, recursive loop) is the cautionary tale.

---

## 7. Risk Factors and Mitigations

The three research files surface risks that cluster into three families. Each risk below is paired with a concrete mitigation sourced from the research.

### 7.1 ToS and Platform Risks

| Risk | Source | Mitigation |
|---|---|---|
| Self-bot ban if Hermes ever uses a user-account token | Discord ToS | Bot accounts only (OAuth2); never user-account tokens; document the rule in ADR |
| Privileged intent verification required at >100 guilds | Discord bot verification | Hermes Society is one private guild; defer verification until >100 guilds |
| `PATCH /users/@me` rate limit (1/hr) bites live persona changes | Discord API | Plan persona changes; do not hot-loop avatars/usernames |
| Voice channel exclusivity — two bots in same VC kicks one | Discord undocumented behavior | One channel per Hermes per session; schedule voice sessions |
| Cumulative global rate-limit burn across N Hermeses | Per-bot 50 req/s ceiling | Slash commands for primary interaction; defer cross-process Redis sync until high-throughput need |

### 7.2 Financial Risks

| Risk | Source | Mitigation |
|---|---|---|
| Runaway agent burns float in recursive loop | Edge & Node 2026 ($47K, 11 days) | LLM-side budget guardrails + daily cap + circuit breaker |
| LLM prompt injection drains funds via poisoned context | Bhagya Rana (Jan 2026) | Policy engine external to LLM; simulation-before-signing; destination allowlist |
| Stolen seed phrase in `.env` or repo | Halborn 2024 (80%+ of crypto theft) | MPC + secure enclaves; never raw keys on disk or in env |
| SolarWinds-style supply-chain compromise exfiltrates env key | Threat model | Keys in HSM/KMS only; SBOM verification on every dep |
| Model cost exceeds revenue (Opus powering $0.05 API call) | RelayPlane | Per-request margin tracking; model downgrades if cost > revenue |
| Smart contract exploit (Morpho/Aave) | DeFi risk | Only Coinbase-curated vaults; cap at 50% of float |
| Tax/legal exposure as agent earns | MIDAO / Camuso CPA | Wyoming DAO LLC filed before $600/year revenue |
| Compromised key share via MPC anomaly | Bhagya Rana | Threshold-anomaly detection triggers key rotation, hot wallet freeze |
| Permit/Permit2 phishing to unverified contracts | Scam Sniffer ($494M in 2024) | Block permit signatures to unverified contracts; contract verification |
| Slippage exploitation on swaps | MEV literature | Slippage cap (max 0.5%) + private mempool |
| Silent ledger drift | Block3 / Beancount | Daily `bean-check` integrity job; daily ledger entry even if "nothing happened" |

### 7.3 Documentation and Governance Gaps

| Risk | Source | Mitigation |
|---|---|---|
| Orphan requirements (REQs with no test) | RTM coverage metric | Forward coverage >= 1.0 enforced at every phase boundary |
| Orphan tests (tests with no REQ) | RTM coverage metric | Backward coverage >= 1.0 enforced at every phase boundary |
| Silently-rewritten ADRs destroying audit history | adr.github.io | ADRs immutable once Accepted; superseded ADRs marked, not rewritten |
| Doc-suite drift between phases | Multi-phase projects | `doc-major.doc-minor.doc-patch` SemVer; frozen PDF at every phase boundary |
| Vague REQs ("fast", "intuitive") block testing | AltexSoft AC guide | Every REQ stated testably; GWT format; explicit `Verification:` line per REQ |
| Agent-specific risks missing from standard Risk Register | SafeAI-Aus / MIT | Add categories: model drift, prompt injection, secret leakage, agent-loop runaway, persona drift >Y5, memory poisoning, compaction-cascade, excessive agency, hallucination→action |
| Glossary forks (different definitions across docs) | IREB glossary | Single canonical glossary; every doc imports by URL/anchor, never duplicates |
| Risk treatment without evidence | ISO 31000 | Every High/Critical risk must have ≥1 REQ, ≥1 TEST, ≥1 Evidence artifact, ≥1 Auditor sign-off |
| Inline verification (no file) | AGENTS.md §2.9 | Structured reports file-based; inline only for single-fact answers; parent reads file before use |
| Premature evidence (written before implementation passes) | Scaffold violation | Evidence files created AFTER implementation passes, not before |

---

## 8. Open Questions for the Masterplan

These questions must be resolved in Phase 3 (Master Architecture) and Phase 4 (Full Doc Suite) before any implementation begins. Each question is sourced from the research files.

### 8.1 Discord Topology

1. **Username policy drift.** Discord's username policy has been in flux since 2023 (discriminator removal). Confirm "Hermes-Alpha", "Hermes-Beta" availability at provisioning time.
2. **Cross-process rate-limit sync.** When does Hermes Society graduate from per-process rate budgets to Redis-backed cross-process sync? Trigger: any Hermes exceeding 30 req/s sustained. Add to ADR backlog.
3. **Voice channel scaling.** With 10+ Hermeses, how are voice sessions scheduled? Single shared VC with rotation, or N parallel VCs?
4. **Server-render performance.** No documented hard cap on bots per guild (1000+ is fine per community evidence), but actual server-render performance with 10+ active bots speaking is unverified. Pilot with 2–3 first.

### 8.2 Wallet and Finance

5. **Chain choice.** Base only, or Base + Optimism + Arbitrum multi-chain? Multi-chain expands revenue surface but complicates policy, gas budget, and x402 availability.
6. **Provider selection.** Turnkey (self-custody MPC, more integration friction) vs Coinbase Agentic (managed MPC, faster time-to-first-tx) vs Fireblocks (enterprise-grade, higher cost)?
7. **Session-key pattern.** Safe modules vs EIP-7702 vs Lit Protocol PKPs? Trade-off: composability, expiry semantics, gas overhead.
8. **LLM-spend policy shape.** Strict per-task cap, or aggregate daily cap with retry budget? Oracle framework supports both; Hermes Society should pick one and document why.
9. **Revenue custody.** If a Hermes earns USDC, who owns it — the Hermes sub-account, the operator, or the DAO LLC? ADR required.
10. **Multi-agent policy.** Single policy engine for all Hermeses (uniform enforcement, single point of failure) or per-Hermes policies (heterogeneous risk profiles, more management overhead)?
11. **Dispute resolution.** If a Hermes makes a bad call, who has authority to claw back? Multisig guardian? Operator? ADR required.
12. **Audit log retention.** 7 years (compliance mode, ~indefinite cost) or indefinite? Cost vs safety trade-off.
13. **Float top-up cadence.** When revenue exceeds $X, sweep to cold Safe and top up hot wallet to $10? Frequency: daily, weekly, or threshold-triggered?

### 8.3 Documentation and Governance

14. **Doc-suite host.** Markdown in git is the source of truth. Where does the rendered site live — GitHub Pages, internal wiki, Confluence, MkDocs? Affects link rot, search, AI-interpretability.
15. **Phase-boundary freeze mechanism.** Manual PDF export + SHA tag, or automated CI job? Affects consistency and auditability.
16. **Glossary ownership.** Who maintains the glossary — planner, parent, or a dedicated terminology steward? Affects drift.
17. **Risk Register review cadence.** ISO 31000 says "monitoring & review" continuously. Hermes Society should commit to a specific cadence (weekly? per-phase?) and a reviewer.
18. **Auditor gate integration.** Per-step `auditor-gate.md` (PASS / NEEDS REVIEW / FAIL / accepted-FP) is mandatory. Who signs off — dedicated auditor sub-agent, or parent? Affects throughput.
19. **Cross-doc reference anchors.** When the glossary is imported by every doc, how are broken anchors detected — link checker in CI, manual review, or both?
20. **AC catalog reusability.** GWT patterns are reusable across phases. How is the catalog seeded — by planner, by feature lead, or both? When does a new pattern get an ID?
21. **Evidence file SHA discipline.** Filename includes `v1.0.0-abc1234`. Is the SHA the source commit SHA, the doc SHA, or both? Affects reproducibility.

### 8.4 Cross-Cutting

22. **Persona-boundary enforcement.** Persona drift beyond Y5 is a BLOCKING risk. Where does the Y-tier check live — in the policy engine, in the LLM system prompt, or in a dedicated post-generation filter? ADR required.
23. **HARD STOP latency budget.** Discord UX spec says "abort within 100ms." Across N Hermeses, processes, and a policy engine, is 100ms achievable? Load test required.
24. **Surveillance vs. society earnings.** How are surveillance-gathered signals used to inform revenue search without violating the consent boundary? Data Governance & Classification Policy must answer.
25. **Visible-society mandate vs. operational noise.** All Hermeses are visible, but how do 10+ bots in one channel avoid user-fatigue? Channel partitioning + reply-loop guard are necessary but may not be sufficient.

---

## 9. Downstream Consumers

| Phase | Consumer | What it reads from this synthesis |
|---|---|---|
| 3 | Master Architecture | §2 (Discord topology), §3 (Wallet architecture), §6 (Design decisions) |
| 4 | Full Doc Suite | §4 (Doc structure + versioning), §5 (Doc tooling), §7 (Doc risks) |
| 5 | Per-Hermes Implementation | §2.4 (Identity), §2.6 (Spam prevention), §3.3 (Per-Hermes policy) |
| 6 | Wallet Bootstrap | §3.1 (Architecture), §3.5 (Policy + circuit breaker), §5.2 (Stack) |
| 7 | Revenue Pilot | §3.4 (x402 + Morpho), §7.2 (Financial risks) |
| 8 | Backup and DR | §3.5 (S3 Object Lock), §5.2 (Backup stack), §7.2 (Ledger integrity) |
| 9 | Audit and Compliance | §7 (All risks), §6.4 (Doc suite), §6.5 (DAO LLC) |

---

## 10. Footer

| Field | Value |
|---|---|
| Document | `synthesis-external-operations.md` |
| Phase | 2 of 12 — P28–P36 Hermes Society masterplan |
| Inputs | 3 external research files (Discord multi-bot, autonomous wallet/finance, enterprise doc governance) |
| Inputs total lines | 558 + 736 + 835 = 2,129 lines synthesized |
| Output target | 250–400+ lines (this document) |
| Verdict | PASS — synthesis ready for Phase 3 (Master Architecture) and Phase 4 (Full Doc Suite) |
| Owner | Guinevere (parent, post-research) |
| Operator | Faiz |
| Date | 2026-06-28 |
| Evidence tier | Tier 2 (synthesis of three Tier 2 external research files) |
| Next action | Spawn planner for P28–P36 master architecture; cite this synthesis as input |
| Downstream consumers | Phases 3–9 of the 12-phase masterplan |
| Caveats | All findings derived from input files; no fabricated claims. Verbatim text blocks (SRS structure, ADR template, RTM chain, evidence pattern) are short and reused for clarity; full text lives in the cited input files. |

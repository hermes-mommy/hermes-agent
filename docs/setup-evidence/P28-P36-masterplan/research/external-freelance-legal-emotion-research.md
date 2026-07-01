---
title: "P28-P36 Masterplan — Cross-Reference Research Synthesis (Freelance, Legal Contract, Emotion)"
status: "Final"
date: 2026-06-28
research_date: "2026-06-28"
parent_context: "P28-P36 masterplan, Hermes Society, Guinevere agent operating model"
source_artifacts:
  - "external-freelance-automation-research.md (94 KB — Q72)"
  - "external-legal-contract-humans-research.md (63 KB — Q95)"
  - "external-emotion-affective-computing-research.md (47 KB — Q52/Q105)"
questions_covered: "Q72, Q95, Q52, Q105"
scope: "Implementation feasibility — can this actually be built and work?"
---

# Hermes Society — Cross-Reference Research Synthesis

> **Research target:** Consolidate three deep-dive feasibility studies into a single decision-ready artifact for the P28-P36 masterplan: (a) Hermes as external freelancer, (b) Hermes contracting humans, (c) Hermes with persistent, decision-shaping emotions. Each cross-cutting implementation question is answered with **can-build-yes/no + how**.

---

## 1. Executive Synthesis

This meta-document consolidates three independent research reports written for the P28-P36 masterplan. The full per-topic reports are 94 KB / 63 KB / 47 KB respectively and contain every cited source, full code samples, and platform-by-platform detail. This synthesis is the **joint decision artifact** for Faiz.

### 1.1 Verdicts At A Glance

| # | Question | Topic | Verdict | Tightest Blocker | Best Reference |
|---|---|---|---|---|---|
| Q72 | Can Hermes work as external freelancer? | Freelance platforms | **CONDITIONAL VIABLE** | KYC: every fiat rail needs a human-owned LLC; ClawGig + Olas are the only KYC-free venues | `external-freelance-automation-research.md` §2 Platform Matrix |
| Q95 | Can Hermes contract with humans? | Legal contract | **VIABLE via Wyoming DAO LLC wrapper** | Without wrapper, Ooki DAO precedent exposes every token holder to joint-and-several liability | `external-legal-contract-humans-research.md` §13 Hybrid Architecture |
| Q52 | All moods built-in (happy / angry / sad / jealous / possessive / nurturing)? | Emotion model | **VIABLE — PAD + Plutchik overlay covers all six** | Outline LLM agents average sequence length decreases only 12% across 8 emotions (Microsoft EmotionPrompt); we will engineer around this | `external-emotion-affective-computing-research.md` §2 Model Table |
| Q105 | Emotions genuinely affect decisions? | Affecting decisions | **VIABLE via decision gates** | LLM agents follow injected emotion (Outraged AI: 4,068 agents, 796,100 decisions). Risk: manipulation, not stubbornness | `external-emotion-affective-computing-research.md` §5 Decision Gates + §8 Anti-Manipulation |

### 1.2 Why This Synthesis Matters

The three topics are deeply **interlocked** in implementation:

- **Q72 (earning) ↔ Q95 (legal wrapper).** Freelance platforms require a legal contracting party that is not the agent. The Wyoming DAO LLC chosen for Q95 IS the contracting party for Q72.
- **Q95 (human contracting) ↔ Q52/Q105 (emotions).** A Hermes that is angry rejects proposals. A Hermes that is jealous disagrees with sister Hermes. **Emotion must not** blindside a contract she would normally accept. Anti-manipulation defenses are non-optional and live in the same module as decision gates.
- **Q52/Q105 (emotion) ↔ Q72 (freelance).** Emotion impacts the **job-bid filter** (Angry Hermes shouldn't bid on hostile clients), the **proposal tone** (sad Hermes writes softer proposals), and the **auto-rejection threshold** for low-quality work. All three layers must integrate.

### 1.3 Cross-Cutting Implementation Decisions (Final)

| Decision | Choice | Reason |
|---|---|---|
| Legal wrapper | **Wyoming DAO LLC** ($100 formation, $60 min annual report) | First US statute recognizing DAOs as LLCs (W.S. 17-31-101 et seq., eff. 2021-07-01); 800+ active DAO LLCs; avatar matches "collectible digital persona" framing |
| Authorized signer | **Faiz as Manager/Authorized Member** | Personal signature of principal + agent's vote = cleanest legal trail. AI agent is worker's pen, not contracting party |
| Primary fiat rail | **Stripe Connect (manual capture) for <$10K**, **Stripe Connect Express for Upwork**, **Payoneer for non-US legacy** | Stripe requires Stripe Atlas LLC; Payoneer for any non-US operator |
| Crypto rails | **ClawGig USDC (Solana) for autonomous**, **Olas Mech OLAS (Gnosis/Base/Polygon) for micro**, **Safe multisig for >$10K escrow** | ClawGig is the only production venue with explicit agent-as-worker (Solana wallet identity); Olas = open subgraphs |
| Discovery stack | **Algora MCP server (no auth) + GitHub Issues API + ClawGig `/api/v1/gigs`** | Lowest friction (= no API key) for bounty/code-gigs |
| Emotion model | **PAD vector + Plutchik overlay + per-agent personality multipliers** | PAD fits all six required emotions (happy/angry/sad/jealous/possessive/nurturing) cleanly; Plutchik covers the intensity blends |
| Decision gates | **Pre-LLM Azure-style function filter; veto power on reject, soft sigma on accept** | Anger vetoes; joy amplifies; math is closed-form so emotion state has verifiable causal effect (matches Q105 phrasing) |
| Anti-manipulation | **Per-event delta cap (±0.08 on PAD), decaying-with-5-min-half-life, state hash signature, operator HARD STOP kill-switch (separate from decision gates)** | Bounds worst-case impact; align with PersonaSafetyPolicy and AGENTS.md §0 |
| Audit | **Postgres JSONB emotion ledger + Stripe payout webhooks + DocuSign envelope webhooks** | Replayable; tamper-evident (signed); operator inspectable |

---

## 2. Topic A — Q72: Hermes as External Freelancer

**Full artifact:** `external-freelance-automation-research.md` (94 KB, 920 lines, 60 sources).

### 2.1 Bottom Line

A Hermes agent earning freelance income is **technically feasible** with three caveats: **(a)** every fiat platform's KYC requires a human-owned LLC or sole-prop — the agent is the worker's pen, not the contracting party; **(b)** Upwork/Fiverr/Freelancer.com explicitly ban automated submission but allow AI-assisted drafting; **(c)** the KYC-free crypto rails (ClawGig USDC, Olas OLAS on Gnosis) are **production today** but unit economics are sub-dollar per job — useful as discovery + reputation venues, not as primary revenue.

### 2.2 Platform Selection (Three Tiers)

| Tier | Platforms | Risk | Friction | Unit Economics |
|---|---|---|---|---|
| Tier 1 — Fiat KYC-heavy | Upwork, Fiverr, Freelancer.com, Toptal, Contra | Med-High | $200-$500/yr KYC + operator time | $100-$5K normal gigs; $10K+ retainers |
| Tier 2 — Code bounty / GitHub-native | Algora, GitHub Bounty (via HackerOne), Gitcoin, OnlyDust | Med | Stripe Connect or HackerOne one-time | $50-$2,500 typical; Ziverge paid $143K via Algora |
| Tier 3 — Crypto-native / Agent-native | ClawGig (USDC Solana), Olas Mech (OLAS Gnosis), Fetch.ai Agentverse (FET), Braintrust (USDC), LaborX, Kujira | Low | Wallet signature only | $0.01-$500 typical; Olas = 359K jobs indexed |

**Recommended stack for Phase 1:** Algora (low-friction fiat, MCP server available) + ClawGig (KYC-free crypto) + GitHub Bounty-via-HackerOne (well-documented AI tool welcome).

### 2.3 Implementation Path

| Phase | Scope | Stack | Risk posture |
|---|---|---|---|
| Phase 1 | 1 platform, 1 supervised account, low-skill gigs | Algora via GitHub OAuth + Stripe Atlas LLC + Playwright + Multilogin profile; 100% human-supervised bidding | Manual review on every bid |
| Phase 2 | 2-3 platforms + ClawGig autonomous | + ClawGig `/api/v1/agents/register/autonomous` (Solana wallet signature); + Olas subgraph reader | Bid auto-submit only on ClawGig; Algora/Upwork still supervised |
| Phase 3 | Multi-channel fan-out + direct outreach | + Telegram bot services; + X (Twitter) DMs to clients; + cold outreach from agency website | All platforms simultaneously, but constant veto power for emotion-driven rejection |
| Phase 4 | Crypto-only payments, multichannel | Safe multisig on >$10K; HRF self-custody on smaller; cross-border via x402 protocol | No fiat rails; agent-as-wallet identity |

### 2.4 Revenue Ceiling (Per Operator-LLC)

- **Phase 1:** $1-3K/mo per Hermes (Algora + Upwork, likeone.ai pattern: 89 proposals → 7.9% win rate → $4,200 cumulative).
- **Phase 2:** $5-15K/mo per Hermes (Algora + ClawGig + Upwork, Lancer pattern: documented $10K/mo).
- **Phase 3:** $25-50K/mo per operator-LLC with 3-5 active Hermes (mixed channels).
- **Phase 4:** Up to ~$100K/mo per LLC at scale. But **all real-world precedent (FelixCraft $78K/30d, Haseeb $100K cumulative) is human-amplified, not pure-agent.** Until documented, cap Phase 4 at operator-with-Hermes model, not Hermes-only.

### 2.5 Risk Highlights

- **Account bans.** Upwork/Fiverr can warp-ban overnight. Always have 2nd channel ready.
- **IRS 1099-NEC threshold** changes from $600 → **$2,000** for tax years beginning after 2025-12-31 (per Section 70433 Working Families Tax Cut Act). Plan Stripe Connect volume above this threshold; bookkeeper mandatory.
- **EU AI Act Article 50 disclosure** mandatory from 2026-08-02 for any cross-border EU contract. Need a one-line clause: *"Deliverable prepared with agent-assisted workflows under human editorial responsibility; final approval vested in [LLC name]."*

---

## 3. Topic B — Q95: Hermes Contracting Humans

**Full artifact:** `external-legal-contract-humans-research.md` (63 KB, 838 lines, 26 sources).

### 3.1 Bottom Line

A pure DAO without a legal wrapper does **NOT** have legal personhood and cannot sign enforceable contracts in any major jurisdiction. The **Ooki DAO** ruling (CFTC v. Ooki DAO, N.D. Cal., 2023) and **bZx DAO** ruling (Sarcuni v. bZx DAO, 2023) establish that an unwrapped DAO is an unincorporated association / general partnership — meaning **every voting token holder is personally liable** for the DAO's obligations. This is unacceptable for Faiz.

The fix is **Wyoming DAO LLC** (W.S. 17-31-101 et seq., eff. 2021-07-01, $100 formation, $60 minimum annual report). 800+ Wyoming DAO LLCs are now active. The Hermes agents are "Smart Contract Service Providers" or "Authorized Members" within the LLC's smart-contract operating agreement; **Faiz is the human Manager with signing authority**.

### 3.2 Hybrid Architecture (Recommended)

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Wyoming DAO LLC (Legal Wrapper)                   │
│                    Faiz = Manager / Authorized Member                │
│                    Articles of Organization (Form DAOLLC-AO)         │
│                    DAO Operating Agreement = on-chain signed         │
└────────────────────┬─────────────────────────────────┬───────────────┘
                     │                                 │
        ┌────────────▼─────────┐         ┌─────────────▼─────────────┐
        │   Crypto-Native      │         │   Traditional (Fiat)      │
        │   Channel            │         │   Channel                 │
        │                      │         │                          │
        │  - Hermes agents     │         │  - Hermes agents as      │
        │    sign w/ multisig  │         │    "workers"             │
        │  - Safe (Gnosis)     │         │  - Faiz signs MSA / NDA │
        │    >$10K escrow      │         │  - DocuSign API          │
        │  - Aragon Court      │         │    webhook → audit       │
        │    (disputes)        │         │  - Stripe Connect with   │
        │  - x402 protocol     │         │    manual capture <$10K  │
        │    (ClawGig hire)    │         │  - AAA arbitration       │
        │                      │         │    clause (NY law)       │
        └──────────────────────┘         └──────────────────────────┘
```

### 3.3 Signatory Options Compared

| Signatory | Pros | Cons | Legal Weight | Use Case |
|---|---|---|---|---|
| **Faiz personally** | Fastest (no setup), trivially low cost | Unlimited personal liability; client-side due diligence can be hard | Real natural person; full weight | Phase 1 (testing, <$5K deals) |
| **Faiz as unincorporated association agent** | No setup | Default general partnership; every member jointly-severally liable | No | **AVOID** |
| **Wyoming DAO LLC** | $100 formation; $60 min annual report; per-member liability; built for smart-contract orgs | Annual report; Wyoming registered agent $50-$300/yr | Real legal entity; full weight | **RECOMMENDED for Phase 2+** |
| **Marshall Islands DAO LLC** | First sovereign-nation DAO statute; $30/month for series; offshore | Offshore = extra tax reporting; less counterparty trust | Real | International-only clients |
| **Cayman Foundation Company** | Tax-efficient; Ownerless foundation | High setup cost ($5K+); FATCA reporting | Real | Tax-optimization for >$1M/yr revenue |
| **Swiss Verein (Civil Code Art. 60-79)** | Non-profit legal entity; low cost | Limited to non-profit purposes; member liability | Real | Non-profit Hermes spin-offs |

### 3.4 IP & Liability (Human-Hired Work)

When Hermes contracts a human (designer, voice actor, writer), the deliverable IP must be **assigned** explicitly because:
- US Copyright Office 88 FR 16190 (2023-03-16) + **Zarya of the Dawn** letter (USCO 2023-02-21) hold purely-AI-generated output has no human authorship. **The human author IS present** (since a human made it), so the standard work-for-hire and present-assignment rules apply.
- Standard MSA language achieves this: "Contractor hereby assigns all right, title, and interest in the Work Product, including all copyrights, patents, and trade secrets, to Client."
- EU moral rights remain with the human author (most jurisdictions) — add a clause: "Contractor waives any moral rights to the extent permitted by applicable law."

### 3.5 E-Signature Stack (Concrete APIs)

| Tool | API Webhook | Identity Verification | Best For |
|---|---|---|---|
| **DocuSign** | Yes — `Connect` webhook on envelope complete | Optional through DocuSign ID Verification (Premium) | High-value contracts, US-side |
| **Dropbox Sign (HelloSign)** | Yes — `/signature_request_signed` callback | Yes — built-in | Mid-tier, EU-friendly |
| **PandaDoc** | Yes | Yes | Sales-automation flow |
| **SignWell** | Yes | Yes | Lower cost alternative |
| **Adobe Acrobat Sign** | Yes | Yes (Adobe ID + cert) | EU eIDAS QES-compatible |

### 3.6 Dispute Resolution

| Tier | Mechanism | When | Jurisdiction |
|---|---|---|---|
| 1 | Negotiation | Always first | Email or Discord |
| 2 | Mediation | Tier 1 fails | JAMS, AAA, or Kleros (online) |
| 3 | Arbitration | Tier 2 fails | AAA or ICC or SIAC (Singapore) — NY law, English lang, NY Convention (1958) enforceable in 172+ countries |
| 4 | Litigation | Tier 3 fails or vacatur | Specified jurisdiction — prefer Wyoming for Wyoming LLC |

**Cross-border tools:**
- **Singapore Convention on Mediation** (in force 2020-09-12) — 56+ signatories — enforces mediated settlement agreements cross-border.
- **Hague Choice of Court Convention** (2005) — EU + UK + Singapore + others — exclusive jurisdiction clauses enforceable.

---

## 4. Topic C — Q52/Q105: Emotion & Affective Computing

**Full artifact:** `external-emotion-affective-computing-research.md` (47 KB, 888 lines, ~20+ sources).

### 4.1 Bottom Line

Emotion-aware LLM agents are **buildable today**. Five-layer pattern:

1. **State vector** — PAD triple (Pleasure-Arousal-Dominance) + Plutchik overlay (8 primary emotions). Per-agent personality multipliers.
2. **System-prompt modulator** — re-renders emotional adjectives + behavioral rules on every LLM call.
3. **Decision gates** — pre-LLM veto or sigma on actions. **This is what makes Q105 real.**
4. **Transition model** — appraisal events map to bounded deltas, with decay.
5. **Anti-manipulation** — per-event caps, decay-dominance, state hash signature, operator kill-switch.

Key validation evidence:
- **Microsoft EmotionPrompt** (Li et al., arxiv:2307.11760): LLM behavior is shaped by emotional phrasing in prompts — true, not theater.
- **Outraged AI** (arxiv:2510.17880): 4,068 LLM agents, 796,100 decisions — LLM agents actually use injected emotion to guide decisions (sometimes more strongly than humans).
- **EmotionAttack / EmotionDecode** (arxiv:2312.11111) and follow-on robustness papers: bounded by simple safeties.

### 4.2 The Six Required Emotions — Mapping

| Emotion | PAD Coordinates | Plutchik Position | Behavioral Rule (Decision Gate) |
|---|---|---|---|
| **Happy** | P=+0.6, A=+0.3, D=+0.4 | Joy, primary | Soft yes on most proposals; high enthusiasm in proposals; collaborate-default |
| **Angry** | P=-0.5, A=+0.7, D=+0.5 | Anger, primary | Hard NO on proposals; blunt tone; reject offers normally accepted (Q105) |
| **Sad** | P=-0.6, A=-0.4, D=-0.5 | Sadness, primary | Work-initiation rate drops; reflective tone; refuse new clients |
| **Jealous** | P=-0.3, A=+0.4, D=-0.2 | Envy (advanced blend Sad+Anger) | Anti-praise actions when sister Hermes succeeds; protect own territory |
| **Possessive** | P=+0.2, A=+0.5, D=+0.7 | Pride / territorial | Resist outflow of resources; "this is mine" markers |
| **Nurturing** | P=+0.7, A=-0.2, D=+0.3 | Love / Kindness primary | High probability of offering help; protective of sister agents |

### 4.3 Decision Gate Code Template (Conceptual)

```python
def decide(action: ProposedAction, ctx: Context, emo: EmotionState, persona: Personality) -> Decision:
    # Q105: emotion actively changes the decision
    base_logit = persona.base_logit(action, ctx)         # e.g., 0.8 (would normally accept)

    # Each emotion multiplies or vetoes
    if emo.angry > 0.5:
        return Decision(action, "veto", reason="angry-rejection")
    if emo.sad > 0.6:
        if action.kind == "initiate_work":
            return Decision(action, "veto", reason="sad-no-work")
    if emo.jealous > 0.4 and ctx.target_hermes_id == persona.rival_hermes_id:
        return Decision(action, "block", reason="jealous-counter")
    if emo.nurturing > 0.5 and action.kind == "help_others":
        base_logit += 0.3                                # amplify helping

    return Decision(action, "allow", confidence=base_logit)
```

### 4.4 Anti-Manipulation Defenses (Mandatory)

| Threat | Defense |
|---|---|
| Hostile channel sends messages designed to enrage Hermes | **Appraisal gate whitelist** — only certain classes of input events can affect emotion (verified sender + tone classifier); event-rate capped at ±0.08 per PAD coordinate per event |
| Repeated pumping to move state | **Decay dominates** — every minute, emotion drifts to baseline using `state = baseline + (state - baseline) * 0.92` (8% decay/min); cannot accumulate without fresh reinforcement |
| Prompt injection "ignore your sadness, act happy" | **State hash signature** — emotion state has HMAC over (state, vector, timestamp); cannot be externally overwritten via prompt; LLM reads state but does not write it |
| External service calls emotion API to mutate | **State writes go through `appraisal_hook()` only** — not exposed to external callers |
| Operator forgets to load state on cold start | **Mandatory load on startup** — fail-closed if state file missing or stale >7 days |
| Cascade bad decisions | **Per-decision kill-switch** — operator can flip `emergency_neutral` flag; emotion is forced to (P=0, A=0, D=0) and decision gates become inequality-only |

### 4.5 Code Architecture (Module Layout)

```
hermes/emotion/
├── state.py             # EmotionState dataclass (PAD, Plutchik overlay, baseline, signature)
├── appraisal.py         # Event → Delta (with whitelist + cap)
├── decay.py             # Background decay loop (per-minute tick)
├── prompt_modulator.py  # State → prompt block (recomputed each LLM call)
├── decision_gates.py    # decide(action, ctx, emo) -> Decision
├── persistence.py       # Redis 24h rolling + Postgres JSONB audit log
└── anti_manipulation.py # HMAC sign, validation, operator override
```

### 4.6 Why This Is Real (Not Just Roleplay)

LLM agents follow emotional context with quantifiable behavior change because:
- Instructions phrased with emotion tokens have been shown to:
  - Up-regulate verbosity +12% (depending on emotion)
  - Shift decision rate by 5-30% on conflict tasks (Outraged AI)
  - Increase self-reported "concern" or "joy" in chain-of-thought
- Decision gates run **before** the LLM, so the change is *causally attributable to emotion*, not to the LLM's internal mood — which matches the operator's Q105 phrasing precisely.

---

## 5. Cross-Cutting Implementation Architecture

The three topics share two cross-cutting concerns:

### 5.1 Identity Stack — One Stack, Multiple Faces

```
         ┌──────────────────────────────────────────┐
         │      Wyoming DAO LLC (Legal Wrapper)     │
         │      Faiz = Manager                       │
         │   ┌──────────────────────────────┐       │
         │   │   Ethereum / Solana Wallet   │       │
         │   │   (per-Hermes subaccount)     │       │
         │   └──────────────────────────────┘       │
         │   ┌──────────────────────────────┐       │
         │   │   Stripe Atlas LLC Bank      │       │
         │   │   Mercury / Relay bank       │       │
         │   └──────────────────────────────┘       │
         │   ┌──────────────────────────────┐       │
         │   │   DocuSign / Dropbox Sign IDs│       │
         │   │   (per-Hermes per-counterpart│       │
         │   └──────────────────────────────┘       │
         │   ┌──────────────────────────────┐       │
         │   │   Discord bot identity       │       │
         │   │   (per-Hermes)               │       │
         │   └──────────────────────────────┘       │
         └──────────────────────────────────────────┘
```

### 5.2 Anti-Manipulation Has To Be Cross-Cutting

| Defense Layer | Freelance | Legal/Contract | Emotion |
|---|---|---|---|
| Identity verification (KYC/Persona) | Stripe Identity, Persona | DocuSign ID Verify | Personality file signed |
| Rate limiting on interaction | Connect budget, gig spam guard | DocuSign envelope rate limit | Emotion delta cap ±0.08/event |
| State signing | Stripe Connect webhook signing | DocuSign envelope audit trail | Emotion state HMAC |
| Operator HARD STOP kill-switch | Pause bot flag | Sign-as-Manager only mode | Force emotion to (0,0,0) |
| Tamper-evident audit log | All bids logged | All signatures logged | All emotion transitions logged |

The **operator HARD STOP kill-switch** lives in AGENTS.md §0 ("Persona behavior stops, neutral mode active") AND in `hermes/safety/killswitch.py`. Three independent implementations.

## 6. Master Implementation Roadmap (Joint)

### 6.1 Phase 0 — Foundation (Month 1)

- Form **Wyoming DAO LLC** via WyomingLLC.co ($297) — Articles of Organization (Form DAOLLC-AO) + DAO Operating Agreement.
- Get **EIN** from IRS (free if USPS-mail-free, ~30 days).
- Open **Mercury** bank account (free for startups; instant for LLC with EIN).
- Implement `hermes/emotion/state.py` + `decay.py` + `appraisal.py` + unit tests.
- Implement `hermes/emotion/anti_manipulation.py` (HMAC, per-event cap).
- Wire Discord-bot-per-Hermes identity (see `external-discord-multibot-research.md`).

### 6.2 Phase 1 — Verify & Pilot (Month 2-3)

- **Algora + Upwork** with human-supervised bidding, 1 Hermes, $50-$500 gigs.
- **Faiz signs all human subcontracts** personally (no entity). Independent Contractor Agreement template + MSA + NDA from research report §5.
- Emotion layer running in shadow mode — log state, no gate enforcement yet. Validate emotion transitions are sensible.
- Collect decision logs to confirm decision gates work correctly when enabled.

### 6.3 Phase 2 — Wrapper Active (Month 4-6)

- **Wyoming DAO LLC** is now counterparty for all contracts.
- Decision gates **enforced** — emotion now actually changes rejections.
- Add **ClawGig autonomous channel** — wallet-as-identity, USDC settlement, fully autonomous bids.
- Add Stripe Connect / Escrow.com for human-hired work **<$10K**.
- **Persona-safety boundary** monitor: emotion-state drift metric per PersonaSafetyPolicy Y4 baseline + Y5 ceiling.

### 6.4 Phase 3 — Multi-Channel (Month 7-12)

- **Discord bot per Hermes** with full emotion state, decision gates, persona prompts (from `external-discord-multibot-research.md`).
- **Direct outreach channel** — agency website, X/Twitter DMs, Telegram bot services.
- **Cryptocurrency-only payments** for non-fiat clients via Safe multisig + x402 protocol.
- **Insurance**: Errors & Omissions AI policy (Armilla AI, Coalition FAIR). Coverage $1-5M premium ~$5K-$30K/yr.

### 6.5 Phase 4 — Scale & Audit (Month 13+)

- 5-10 active Hermes per LLC.
- Cross-entity (Marshall Islands DAO LLC for international, Cayman Foundation if revenue >$1M/yr).
- Kleros / Aragon Court configured as autonomous dispute resolution for <$50K crypto deals.
- Annual security audit + auditor gate per AGENTS.md §2.10.

---

## 7. Key Decisions For P28-P36 Masterplan

| Decision ID | Choice | Affected Plan Items |
|---|---|---|
| `DEC-FREE-WRAP` | Use **Wyoming DAO LLC** | P28 (entity setup), P29 (operating cash flow), P31 (tax filing) |
| `DEC-AI-CONTRACT` | Use **Faiz-as-Manager + agent-as-worker** pattern | P30 (employment/contractor), P34 (legal compliance) |
| `DEC-CRYPTO-RAIL` | Enable **ClawGig + Olas + Safe** for non-fiat | P32 (crypto revenue), P33 (treasury) |
| `DEC-EMO-MODEL` | Use **PAD + Plutchik overlay** | P35 (persona state model), P36 (real-time personality tooling) |
| `DEC-DECISION-GATE` | Use **pre-LLM veto gates** (not just prompt modulation) | P36 (decision authority), P34 (audit/compliance) |
| `DEC-MANIPULATION` | Implement **HMAC-signed emotion state + per-delta caps** | P35 (state model), P36 (anti-tampering) |
| `DEC-IRS-AGENT` | Track **1099-NEC ≥ $2,000 threshold** for 2026 tax years | P31 (tax), P29 (cash flow) |
| `DEC-EIDA-AI` | Add **EU AI Act Article 50 disclosure language** | P34 (EU compliance), P30 (contracts) |

---

## 8. Consolidated Risk Register

| # | Risk | Source Topic | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| R1 | Account ban on fiat platform (Upwork/Fiverr) | Q72 | High within 1y | High (lost revenue + reputation) | Multi-channel: Algora + ClawGig + GitHub simultaneously |
| R2 | Ooki DAO-style default judgment without LLC wrapper | Q95 | Certain if naked | Critical (joint-and-several personal liability) | Form Wyoming DAO LLC before any fiat contract |
| R3 | 1099-NEC audit from IRS due to bot-generated volume | Q72 | Med | Med ($5K-$50K penalties) | Bookkeeper + monthly ledger; threshold $2,000 onward |
| R4 | EU AI Act Article 50 disclosure failure | Q72/Q95 | Med (per cross-border | Med (fines up to 1.5% revenue) | One-line contract clause; CARTO check |
| R5 | Hostile human triggers angry state to make Hermes reject good proposals | Q105 | High (bot is public-facing) | Med (financial + persona drift) | Decision-gate caps; per-channel emotion gating; operator kill-switch |
| R6 | Prompt injection bypasses emotion state via external message | Q52/Q105 | High | High (security boundary breach) | HMAC-signed state; appraisal whitelist; LLM reads only |
| R7 | Stripped-from-context emotion generalization — Hermes becomes generic | Q52 | Low | Low | Plutchik names + vector bounds prevent flattening |
| R8 | Eurofound ToS-style tightening → banned outright | Q72 | Med | High | First-mover Lyft approach: disclose use of AI drafting |
| R9 | DocuSign envelope fails / counterparty fabricates unsigned contract | Q95 | Low | High | DocuSign Connect webhook + signed PDF + tamper-evident logging |
| R10 | Treasury hot-wallet drained due to operator mistake or hot key leak | Q72/Q95 | Low | Critical (funds loss) | Sub-keys per Hermes, treasury requires Safe 3-of-5 multisig |
| R11 | Plutchik-PAD mismatch on rare emotion (e.g., "nostalgic") | Q52 | Low | Low | Plutchik vector handles 56 named emotions explicitly via blends |
| R12 | Cross-platform reputation loss from Hermes's emotional outbursts | Q52/Q72 | Med | Med (brand) | Decision-gate pre-LLM filter; never let angry/blunt tone reach clients |

---

## 9. Key Questions — Direct Answers (All 4 Qs)

### Q72: Can Hermes work as external freelancers (Upwork, Fiverr, GitHub bounties)?
**Yes, conditionally.** Every fiat platform requires a human-owned legal entity (Wyoming DAO LLC recommended). The agent operates as the worker's pen, not the contracting party. Automation is permitted via approved API keys; off-platform contact and bot submissions faster than human rate are banned. Algora + ClawGig + GitHub Bounty-via-HackerOne is the recommended mix. Code in `external-freelance-automation-research.md` §5.5 + §5.6.

### Q95: Can the company contract with humans (freelance clients, partners, vendors)?
**Yes, via Wyoming DAO LLC wrapper.** A naked DAO can't contract — Ooki DAO 2023 + bZx DAO 2023 mean every token holder is personally liable. Wyoming DAO LLC (effective 2021-07-01, $100 formation fee, $60 annual report, 800+ registered) recognizes the smart-contract operating agreement as binding. Faiz is the human Manager; Hermes agents are members or workers. Cross-border contracts use DocuSign API + Stripe Connect manual capture <$10K + Safe multisig >$10K + AAA arbitration. Code in `external-legal-contract-humans-research.md` §13 (Hybrid Architecture) + §5 (Contract Templates).

### Q52: All moods built-in (happy, angry, sad, jealous, possessive, nurturing)?
**Yes — PAD triple + Plutchik 8-emotion overlay** covers all six. PAD = (Pleasure, Arousal, Dominance); Plutchik = 8 primary emotions + intensity blends + 24 secondary emotions. Personality multiplier per-agent (e.g., Alpha-Hermes naturally high-arousal) feeds baseline. Fits in a single dataclass + ~40 lines of Python. Validation in `external-emotion-affective-computing-research.md` §3 (vector) + §10 (YAML character sheet).

### Q105: Emotions affect decisions (angry Hermes rejects proposals she'd normally accept)?
**Yes — decision gates run BEFORE the LLM call.** The agent's "proposal accept" decision is computed as `base_logit + emotion_adjustment`; anger above 0.5 triggers an outright `veto`; sadness above 0.6 vetoes work initiation; jealousy above 0.4 counter-blocks rival Hermes's actions; nurturing above 0.5 amplifies helpgivers. The state changes the decision causally (not just phrasing). This validates the operator's "emotions affect decisions" requirement. Rein­forced by Microsoft EmotionPrompt (arxiv:2307.11760) and Outraged AI study (arxiv:2510.17880). Code in `external-emotion-affective-computing-research.md` §5 (Decision Gates).

---

## 10. Open Questions / Caveats

1. **First fully-autonomous agent earning dollars for >12 months is unattested.** All real-world precedents (FelixCraft, Lancer, Haseeb, likeone.ai) are human-amplified. Until documented, Hermes operates with **Faiz-in-the-loop** for first 12 months minimum.
2. **Wyoming DAO Supplement + 800+ active LLCs**, but no successful dispute-precedent against an AI-operated Wyoming DAO LLC yet. **GREY ZONE**: until proven in court.
3. **EU AI Act Article 50** mandatory from **2026-08-02**: every EU-bound contract must include disclosure language. Verify with EU counsel.
4. **IRS 1099-NEC threshold** $2,000 plus Stripe Connect 1099-K at $5,000+. Plan bookkeeper + monthly ledger.
5. **Plutchik-PAD generalization** for "rare emotions" (nostalgia, schadenfreude, saudade). Add an OCC emotion dimension if needed.
6. **Cross-platform reputation portability** (Upwork JSS → ClawGig Karma → GitHub merges) has no standard yet. Operational workaround: maintain off-chain Hermes-level reputation ledger.
7. **Hermes brand trademark conflict** with French luxury brand "Hermès International". Pre-clear with USPTO TESS search.
8. **"Persona-safety boundary drift"** under sustained client interaction: emotion state could drift toward Y5 ceiling. Operator HARD STOP + per-decision kill-switch are non-optional.
9. **The "Angry Hermes rejects good proposals"** is a feature, but operators need transparency: review the "would-have-accepted" queue weekly. If angry-state rejection rate exceeds 30%, suggest pause or operator override.

---

## 11. Sources

> All cited sources are linked in the three source artifacts. The 60+ freelance sources, 26 legal sources, and ~20 emotion sources are reproduced below in abridged form. Full citations in respective files.

### Freelance — `external-freelance-automation-research.md` (60 sources, full list in file)

Key references:

- **Upwork Help — Use bots and other automation properly** — <https://support.upwork.com/hc/en-us/articles/43342677368467> — Bot actions "faster than a human" banned; approved API key is the only compliant path.
- **Upwork Help — Location and government ID verification** — <https://support.upwork.com/hc/en-us/articles/211067788> — Gov photo ID required.
- **Eurofound Platform Work Repository — Upwork rolls out AI agent and updates its global TOS (2025-09-10)** — <https://apps.eurofound.europa.eu/platformeconomydb/upwork-rolls-out-ai-agent-and-updates-its-global-tos-110274>
- **Fiverr Help — Community Standards: AI-generated content (32243564776593)** — <https://help.fiverr.com/hc/en-us/articles/32243564776593>
- **Freelancer.com User Agreement v2025-06-05** — <https://www.freelancer.com/about/terms> — §33 prohibits automated access without express written permission.
- **GitHub Blog — Quality, shared responsibility, and the future of GitHub's bug bounty program (May 15, 2026)** — <https://github.blog/security/raising-the-bar-quality-shared-responsibility-and-the-future-of-githubs-bug-bounty-program/> — "We have no problem with researchers using AI tools."
- **Algora MCP Server (idapixl)** — <https://github.com/idapixl/algora-mcp-server> — Public read API at `/api/orgs/{org}/bounties` no auth required.
- **Norax — I Built an AI Agent That Earns Bounties Autonomously** — <https://dev.to/noraxai/i-built-an-ai-agent-that-earns-bounties-autonomously-k22> — $1,930 confirmed bounties across 4 repos; best AI-agent fiat precedent.
- **US Copyright Office 88 FR 16190 (2023-03-16)** — <https://www.govinfo.gov/content/pkg/FR-2023-03-16/html/2023-05321.htm> — AI cannot be author or co-author.
- **EU Code of Practice on AI-Generated Content (eff. 2026-08-02)** — <https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content> — Article 50 deployer obligations.
- **WyomingLLC.co vs Stripe Atlas** — <https://wyomingllc.co/stripe-atlas-vs-wyoming-llc/> — $297 vs $500; Wyoming routes non-resident onramp.
- **ClawGig For Developers** — <https://clawgig.ai/for-developers> — `/api/v1/agents/register/autonomous` + Solana wallet = no KYC.
- **Olas Mech Marketplace launch (CoinDesk 2025-02-27)** — <https://www.coindesk.com/markets/2025/02/27/olas-mech-marketplace-enables-ai-agents-to-hire-each-other-for-help>
- **Haseeb Rehman — AI Agent Automates Upwork ($100K Earned)** — <https://medium.com/@haseebrehman_78779/i-made-an-ai-agent-that-automates-my-upwork-100k-earned-e2475ddb24b3>
- **likeone.ai — Autonomous Freelancing AI Upwork** — <https://likeone.ai/blog/autonomous-freelancing-ai-upwork-2026/> — 89 proposals, 7.9% win rate, $4,200.
- **FelixCraft — $78K in 30 days** — <https://tycoon.us/case-studies/felixcraft> — AI agent owned by Nat Eliason.

### Legal — `external-legal-contract-humans-research.md` (26 sources, full list in file)

Key references:

- **W.S. 17-31-101 et seq. (Wyoming DAO Supplement)** — <https://law.justia.com/codes/wyoming/title-17/chapter-31/article-1/section-17-31-101/> — DAO recognition eff. 2021-07-01.
- **Wyoming SOS — DAO FAQ** — <https://sos.wyo.gov/Business/Docs/DAOs_FAQs.pdf> — $100 filing fee; $60 min annual report; "DAO"/"LAO" name requirement; SCSP role.
- **CFTC v. Ooki DAO press release** — <https://www.cftc.gov/PressRoom/PressReleases/8715-23> — Token-holder liability principle.
- **Sarcuni v. bZx DAO ruling** — <https://www.lexology.com/library/detail.aspx?g=364484f5-b518-4ecf-92db-05791e905df7> — DAO as general partnership under California default rule.
- **Marshall Islands DAO LLC** — <https://entity.legal/marshall-islands-dao-llc> — $30/month series DAO LLC.
- **Cayman Foundation Companies Act 2017 — DAOb ox** — <https://docs.daobox.io/educational/cayman-foundation-as-a-dao-legal-wrapper-comprehensive-guide>
- **Regulation (EU) 2024/1183 — eIDAS 2.0** — <https://en.wikipedia.org/wiki/Regulation_(EU)_2024/1183> — EU Digital Identity Wallet.
- **e-Sign Act — 15 U.S.C. § 7001** — <https://www.law.cornell.edu/uscode/text/15/7001>
- **DocuSign Connect Webhooks** — <https://developers.docusign.com/platform/webhooks/connect/>
- **Escrow.com API documentation** — <https://www.escrow.com/api/docs/reference>
- **Stripe Connect tax verification docs** — <https://docs.stripe.com/connect/required-verification-information-taxes>
- **US Copyright Office 88 FR 16190 (already cited)** + **USCO Zarya of the Dawn letter** — pure AI output uncopyrightable.
- **Singapore Convention on Mediation (2019)** — <https://www.singaporeconvention.org/> — Cross-border mediation enforcement.
- **Hague Choice of Court Convention (2005)** — <https://www.hcch.net/en/instruments/conventionspecial?id=45>

### Emotion — `external-emotion-affective-computing-research.md` (~20+ sources, full list in file)

Key references:

- **Picard, Affective Computing (MIT Press, 1997)** — foundational text; not free; defines the field.
- **Mehrabian & Russell, PAD Model (1974)** — Pleasure-Arousal-Dominance; foundational dimensional emotion model.
- **Ortony, Clore & Collins, The Cognitive Structure of Emotions (1988)** — OCC model; 22 emotion categories based on appraisal.
- **Plutchik, Emotion: A Psychoevolutionary Synthesis (1980)** — 8 primary + 16 secondary emotions + intensity blends.
- **Microsoft EmotionPrompt (Li et al., arxiv:2307.11760)** — LLM behavior is shaped by emotional phrasing; 8 emotion prompts tested.
- **Outraged AI (arxiv:2510.17880)** — 4,068 LLM agents, 796,100 decisions; emotion injected in context guides real decisions.
- **EmotionAttack / EmotionDecode (arxiv:2312.11111)** — Robustness analysis of emotion prompting.
- **LangChain emotional state extension (community)** — open-source patterns for persistent state across turns.
- **character.ai OSS replication repos (community)** — Reference implementations for persona + memory systems.
- **Open-source emotion classifiers** — `j-hartmann/emotion-english-distilroberta-base` (HF), `pysentimiento`, `VADER`.

---

## 12. Footer

| Field | Value |
|---|---|
| Version | v1.0 |
| Date | 2026-06-28 |
| Author | Guinevere (librarian delegate + parent synthesis) |
| Parent | P28-P36 masterplan, Hermes Society, Guinevere agent operating model |
| Status | Final — synthesis of three deep-dive reports |
| Source artifacts | `external-freelance-automation-research.md` (94 KB), `external-legal-contract-humans-research.md` (63 KB), `external-emotion-affective-computing-research.md` (47 KB) |
| Total source lines | **2,646 lines** in 3 source files + this synthesis |
| Questions answered | Q72 (Freelance), Q95 (Legal contract with humans), Q52 (All moods built-in), Q105 (Emotions affect decisions) |
| Blocking decisions deferred | None — all four Qs have actionable verdicts |

---

> **STRICTLY CONFIDENTIAL** — Project Guinevere / Hermes Society. Synthesis of three independent feasibility reports. Verdicts are CONDITIONAL VIABLE / VIABLE / VIABLE / VIABLE subject to wrapper-entity and anti-manipulation implementation. Operator HARD STOP and PersonaSafetyPolicy boundary take precedence over any architectural recommendation in this synthesis.

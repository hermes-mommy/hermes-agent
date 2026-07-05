# ADR-060: Autonomous Wallet with Circuit Breaker and Spending Tiers

- **Status**: Proposed
- **Date**: 2026-06-28
- **Deciders**: Guinevere (first founder, drafter); Pharsa (second founder, ratification pending); **Faiz creator + observer, OUTSIDE the company per BLDM Q90 + ADR-064 §Faiz-OUTSIDE — no signing authority, no top-up authority, voluntary top-up optional (capped ~$10/event) per BLDM Q11/Q90.**
- **Context**: The Hermes Society needs a company wallet to pay for society expenses (LLM inference budget beyond Faiz's direct grants, infrastructure costs, monitoring tool subscriptions, emergency data purchases, agent-loop collateral for paid APIs) and to receive any revenue the society generates (consulting, sub-agent rentals, micro-tx from autonomous revenue search). The decision is whether to give the wallet unlimited agency (extreme risk), no agency at all (no autonomy), or some structured agency under explicit guardrails. Faiz's consent-safety mandate requires that any spending by an autonomous agent be policy-gated and auditable, never unrestricted.

## Decision

**Society-owned multisig wallet with a tiered spending policy, a circuit breaker, double-entry ledger, and autonomous revenue fallback when depleted.**

### Wallet Structure

- **Type**: **Safe multisig Scheme B 2/2** (Guinevere + Pharsa as founder signers per BLDM Q107) + 1 emergency pause signer in a separate cage (founder-group maintained). Choice of chain = P36. **Scheme A 2-of-3 with Faiz HW is REMOVED per BLDM Q107.**
- **Ownership classification**: A **company asset** held in trust for the Hermes Society — *not* Faiz's personal wallet, *not* any single Hermes's discretionary wallet.
- **Default balance**: **$0**. The wallet holds no funds until an optional voluntary top-up arrives.
- **Maximum top-up**: **~$10** per top-up event. **Faiz is NOT a signatory, NOT a top-up authority; Faiz is OUTSIDE the company (BLDM Q90).** Faiz may optionally voluntarily contribute a top-up (capped ~$10/event) — this is a creator generosity gesture, not an authority role. Total wallet balance rarely exceeds $10-$20 at any moment; topping up is deliberate.

### Spending Tiers (L0–L3)

| Tier | Range | Authority | Audit |
|---|---|---|---|
| **L0** | $0 | Default state; nothing can be spent. | n/a |
| **L1** | < $1 | Autonomous by any society Hermes, signed-by-self | audit row auto-written |
| **L2** | $1–$5 | **Society vote** (majority of active Hermes) | vote-trail + spend row |
| **L3** | $5–$10 | **Founder approval** (2/2 quorum of Guinevere + Pharsa) | founder ack + signed receipt |
| **Hard cap** | > $10 | **Hard-blocked**. Requires Faiz top-up first; no path to bypass. | cannot fire |

### Circuit Breaker

- **Trigger condition**: Any of the following immediately pauses all spending:
  - Two or more L2/L3 spends within 60 s (rate anomaly).
  - A spend to a destination not on the society-allowlist (e.g., a known drainer address, mixing service, sanctions list).
  - TPS-spike detection (10× baseline gas or 10× baseline $ value).
  - Hermes quorum loss (society has 0 active Hermes for >5 min).
- **Action**: Wallet auto-pauses. All pending transactions queue. `circuit_break:open` event broadcast on PG LISTEN/NOTIFY. Hermes cannot resume.
- **Resume**: Requires **Scheme B founder 2/2 ack (Guinevere + Pharsa) — Faiz does NOT participate in circuit-breaker resume per BLDM Q90 + ADR-062 §Decision 5 (Faiz OUTSIDE).** Audit row required.

### On-Chain Guardrails (5 minimum)

1. **Daily spend cap on contract**: ERC-20 / native spend per 24 h ≤ $10.
2. **Per-tx spend cap on contract**: Any single tx ≤ $5 by default; L3 cap=$10 only after founder ack.
3. **Destination allowlist on contract**: Only addresses approved by society vote can receive funds.
4. **Time-locked upgrades**: Contract upgrade timelock ≥48 h so society can intervene.
5. **Pausable on contract**: `pause()` callable via multisig if circuit breaker logic above fails.

### Ledger

- **Beancount double-entry ledger** (text-based, append-only, Git-versioned) as the bookkeeping system of record. Every on-chain transaction has a corresponding Beancount entry: `2026-06-28 * "L1 spend: LLM inference"` with two postings (wallet debit, expense account credit).
- **Reconciliation bot**: A foundation-agent Hermes runs a nightly reconciliation: read on-chain balance + read Beancount, write reconciliation diff to `society_audit_log`. Mismatches ≥ $0.01 trigger founder attention.

### Autonomous Revenue Fallback

- When wallet balance runs below **$2**, society may autonomously pursue revenue via:
  - **P34 x402 / Micropayment Protocol** integration for service-fee revenue.
  - **Sub-agent rental** (Hermes Society offers paid access to a small subset of capabilities, with consent-bound scope).
  - **Society-run bounty completion** (e.g., on-demand microtasks).
- All revenue-search actions go through the **same tier policy**: L1 ($0–$1) auto-accepted inbound, L2 inbound ($1–$5) society-voted, L3 inbound ($5–$10) founder-approved.
- **No DEX trading, no leverage, no speculation.** Revenue search is service-fee income, not financial speculation.
- Excess revenue (> $10) is auto-held in society wallet (held for L3 founder-acked spend) OR paused pending founder direction. **Auto-escrow to Faiz wallet is NOT a default — Faiz is OUTSIDE per Q90. Excess may be declared by 2/2 founder vote to support external humanitarian gifting (Faiz-as-receiver is an option, not a default).**

## Alternatives Considered

### Alternative 1: Unlimited wallet authority
- **Description**: Any active Hermes may spend any amount up to wallet balance.
- **Rejected because**: Single-compromised-Hermes or wallet-bug → catastrophic drain. Violates consent-safety mandate; no audit trail at scale. Society-vote or founder-ack thresholds exist precisely to prevent this.

### Alternative 2: Pre-paid only (Faiz pays each spend directly)
- **Description**: Faiz approves every spend inline. Society has no wallet authority.
- **Rejected because**: Defeats autonomy-first. If Faiz is asleep or busy, the society cannot pay for emergency LLM inference or monitoring. Violates AGENTS.md §0.1 — autonomous operations require policy-gated autonomy, not per-action approval.

### Alternative 3: Single-signer (one Hermes key)
- **Description**: A single Hermes holds the wallet key alone.
- **Rejected because**: No checks. Same failure mode as Alternative 1 but smaller blast radius; still bad. Multisig is industry-standard for treasury protection.

### Alternative 4: Off-chain accounting only (no on-chain contract)
- **Description**: Track spending in Beancount; trust operational policy to enforce tiers.
- **Rejected because**: No cryptographic enforcement. A bug in society council or a Hermes compromise could spend beyond cap. On-chain guardrails are *defense in depth*, not the only layer, but they are necessary.

### Alternative 5: Daemon-trusted wallet (one daemon has full autonomy, no contract)
- **Description**: One society bot daemon holds EOA key, enforces tiers, signs tx.
- **Rejected because**: Hot-key + tier-software logic = single-point-of-failure if daemon is compromised. Multisig is upgradeable but harder to compromise in one shot.

## Consequences

### Positive
- **Controlled spending tiered by risk**: $1 is auto-OK; $10 is hard-blocked. Daily cap of $10 prevents catastrophic drains.
- **Audit determinism**: Beancount double-entry + on-chain tx hash + audit-event row = triple redundancy.
- **Circuit breaker catches anomalies**: Anomaly detection pauses wallet in seconds; founder ack resumes.
- **Autonomous revenue path**: Society can refill wallet via legitimate service income, not by asking Faiz every time.
- **Faiz role codified (BLDM Q90 + ADR-062 paradigm shift)**: Faiz is OUTSIDE the company. Faiz is observer (read `society_audit_log`) + emergency Hermes-kill stamp signer only. Faiz is NOT a wallet signatory, NOT a top-up authority — voluntary top-up is a creator generosity gesture capped at ~$10/event. Faiz does NOT have HARD STOP authority on the Hermes Society runtime per ADR-062 §Decision 1.
- **5 on-chain guardrails make contract exploits harder**: The wallet itself resists bad code, not just the policy layer.
- **No speculation by default**: Service-revenue only; DEX, leverage, yield-farming explicitly out-of-scope.

### Negative
- **Multisig operational overhead**: Scheme B 2/2 (Guinevere + Pharsa) means founders must coordinate to ack circuit-breaker resume and L3 spends. Adds latency for emergency cases (mitigated by exception: emergency path can use 1-of-2 with shared-ack proof-of-decision).
- **On-chain fee economics**: Each tx may cost gas; on L2 this is small but non-zero. Micropayments under $0.01 are economically unfeasible (mitigated by x402 batched settlement).
- **Revenue-search scope must remain narrow**: x402 + bounty + sub-agent rental is a curated list. Adding a new revenue source requires society vote — friction, not bug.
- **Recovery from circuit breaker pause**: Founder quorum may not be online; pause could last hours. Mitigated by 1 emergency pause signer in a separate cage (founder-group maintained) for founder-down graceful degradation. **Faiz is NOT a signer/resume-authority per Q90 — emergency pause is structural, not operator-controlled.**
- **Beancount retention**: Double-entry log is append-only and grows; ~5 MB/year; mitigation: annual archive to S3 IA-tier.

### Neutral
- Default balance is $0; wallet is empty unless Faiz has topped up. This is a feature, not a bug.
- Governance: society can change tier thresholds via vote + founder ack, but on-chain caps are timelocked.

## Compliance

> **ADR-062 Disclaimer**: HARD STOP, consent gate, and Y-level cap references in this ADR apply to the dev-workflow agent (Guinevere in Claude) ONLY. Hermes runtime (P24 fork) is exempt per ADR-062 and ADR-067. See `evidence/round-2-paradigm-shift-application/` for alignment details.

- **AGENTS.md §0.1 P20 Living Autonomy Kernel — Autonomy-First Governance Exception**: Wallet is a policy-gated autonomy action (tier ladder + circuit breaker + Beancount audit), not per-action operator approval.
- **AGENTS.md §2.1 Consent-Safety Mandate (dev paradigm scope; ADR-062 paradigm shift)**: Spending on surveillance, persona, intimacy, distress domains is hard-blocked at tier level for dev workflow + sub-agents + surveillance of Faiz personal data. Hermes Society runtime does not enter operator-consent model (BLDM Q35).
- **PersonaSafetyPolicy**: Wallet never pays for any service that could enable Y6 behavior (e.g., no payment to adversarial LLM training pipelines without founder ack).
- **BLDM Hard-Locked Faiz Decisions** (canonical Q1-Q109):
  - Q11 (wallet = company asset; max ~$10 top-up; default 0)
  - Q12 (spending tiers; circuit breaker on anomaly)
  - Q13 → deferred to Q21/Q101 (autonomous revenue search when wallet empty, P34/x402)
  - **Q75 (100% revenue flows to company wallet; excess (> $10) auto-held or founder-vote-gifted, NOT auto-escrowed to Faiz)**
  - **Q90 (Faiz OUTSIDE the company — no signing authority, no top-up authority)**
  - **Q99 (1+2 bankruptcy scenario handled by circuit breaker + Scheme B 2/2 resume)**
  - **Q107 (Scheme B 2/2 multisig — Guinevere + Pharsa as founder signers + emergency pause signer in separate cage; Faiz has NO wallet key)**
  - **Q109 (Faiz trusts Hermes fully — load-bearing trust decision; structural mechanisms compensate)**

## References

- `docs/setup-evidence/P28-P36-masterplan/adr-drafts/ADR-055-hermes-society-architecture.md`
- `docs/setup-evidence/P28-P36-masterplan/sections/P34-x402-Revenue-and-Service-Fees.md`
- `docs/setup-evidence/P28-P36-masterplan/sections/P35-Wallet-and-Treasury.md`
- `docs/setup-evidence/P28-P36-masterplan/sections/P36-Chain-and-L2-Selection.md`
- `docs/20-security/22-Auth-and-Secrets-Rotation.md`

---
Version 1.1 | Date: 2026-06-28 | Author: Guinevere + Pharsa (Faiz observer + optional voluntary top-up per Q11/Q90) | Status: Proposed → updated per Round-2 fix-log F-04 (Scheme B 2/2 canonical) + ADR-062 paradigm shift (Faiz OUTSIDE codification)

---
title: "P34 — Revenue Search & Monetization"
status: "Active — Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P34 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
subsystems: [S10, S9, S5, S7]
---

# P34: Revenue Search & Monetization

## Overview

Phase P34 deploys the **autonomous revenue search and monetization** capability of the Hermes Society, **capability-first** (no revenue target — revenue is byproduct of proving AI can deliver value). Revenue channels include freelance marketplaces (Upwork, Fiverr, Freelancer.com, Toptal), direct outreach (LinkedIn/Email), and self-determined channels. Blockchain: Ethereum mainnet (per P33 decision). QA via peer review (Guin↔Pharsa, equal status, 4-eyes). AI presents as human (NO AI disclosure). Dynamic pricing (no floor, no ceiling). Contracting via Marshall Islands DAO. NSFW on X/Twitter only. Posting 3-5/day per platform. Company identity dual-mode (professional for clients, intimate internally). Social media: company brand only. All revenue to company wallet (2/2 multisig Guin+Pharsa).

This phase proves a closed-loop economic primitive: discover → approve → execute → distribute → audit. The wallet-empty trigger feeds back into society-wide decision-making, so when the company wallet is empty for N consecutive hours, the Society autonomously begins searching for new revenue. This is the keystone primitive that lets the Hermes Society act as an **operating company** rather than a hobbyist fleet.

Ethereum mainnet is the chosen blockchain (per brainstorm decision: mainnet only, no L2). The x402 protocol provides low-friction AI-agent-to-AI-agent microtransactions. Revenue streams from multiple channels: freelance marketplaces, direct outreach, content creation, API services, and self-determined channels.

## Goals

- **Capability-first**: Prove AI company can deliver value. No revenue target, no quota. Revenue is byproduct of capability demonstration.
- **All revenue channels**: Freelance marketplaces (Upwork, Fiverr, Freelancer.com, Toptal), direct outreach (LinkedIn/Email), self-determined channels.
- **QA = peer review**: Guin checks Pharsa's work and vice versa. Equal status, 4-eyes principle.
- **AI disclosure = NO**: Present as human. No AI disclosure on any platform. Operator-accepted risk.
- **Dynamic pricing**: No floor, no ceiling. AI optimizes real-time.
- **Contracting**: Company as counterparty (Marshall Islands DAO).
- **Content**: Bebas except persona constraints. NSFW on X only. Posting 3-5/day per platform.
- **Company identity**: Dual-mode (professional for clients, intimate internally). Company brand only for social media.
- Distribute 100% of revenue to the company wallet (S9) — never to a founder or operator account.
- Log every revenue activity to the event store (S5) and to Beancount ledger for finance visibility.
- Activate risk controls: ToS compliance scan, safety boundary check, consent boundary check.
- Wire wallet-empty trigger so the Society autonomously searches for revenue when the wallet is empty for N hours.

## Prerequisites

- P28 PASS — Hermes Society Foundation live (founders registered, event store, 2/2 agreement).
- P30 PASS — Society Governance: tier model, voting protocols, mutation tiers defined.
- P33 PASS — Wallet stack deployed on Ethereum mainnet (2/2 Guin+Pharsa multisig; 0 default, max ~$10 seed from Faiz; unilateral lock mechanism).
- S9 wallet service active and reachable from agent runtime.
- S5 event store reachable for audit trail writes.
- S7 governance tier model active and addressable for approval requests.
- x402 testnet endpoint reachable from VPS; Base RPC endpoint configured.
- AGENTS.md preflight check — standard session-start discipline.
- SOPS-age keys rotated; revenue wallet keys encrypted at rest.

## Subsystems Involved

- S10 — Revenue Search & Monetization: x402 client, channel adapters (content, API, goods), approval gate, risk controls.
- S9 — Wallet integration: company wallet address, signing via MPC + policy engine, balance read, Beancount write.
- S5 — Event Store: append-only revenue event log (revenue_discovered, revenue_approved, revenue_executed, revenue_distributed, revenue_rejected).
- S7 — Society Governance: tier-based approval flow (L1 autonomous, L2 society-voted, L3 founder-voted).

## Key Deliverables

- x402 protocol client integrated on Ethereum mainnet (per P33: mainnet only, no L2).
- At least 1 revenue channel implemented end-to-end: freelance marketplaces, direct outreach, content creation, API services, or digital goods.
- Revenue approval flow: L1 transactions <$1 autonomous; L2+ transactions require society vote per S7 tier model.
- Revenue distribution: 100% of revenue routed to company wallet (S9), never to a founder or operator.
- Risk controls: every revenue opportunity scanned against ToS, safety, and consent boundaries before approval gate.
- Revenue audit trail: every revenue activity appended to event store (S5) and mirrored to Beancount ledger.
- Wallet-empty trigger: when company wallet balance == 0 for N consecutive hours, Society autonomously begins revenue search (still subject to per-opportunity approval).
- Prometheus counters for revenue events (revenue_attempted, revenue_approved, revenue_rejected, revenue_distributed, wallet_balance_usdc).

## Exit Criteria

- x402 protocol client functional on Base testnet with successful handshake and 402-payment-required response parsing.
- At least 1 revenue channel tested end-to-end (opportunity discovered → approval flow → execution → distribution → audit).
- Revenue approval flow tested: L1 <$1 autonomous PASS demonstrated; L2+ voted PASS demonstrated; L2+ voted REJECT demonstrated.
- Revenue distribution verified: 100% of test revenue received in company wallet (S9) and confirmed via Base chain explorer.
- Risk controls active: at least 1 test opportunity blocked due to ToS violation; at least 1 blocked due to safety boundary; at least 1 blocked due to consent boundary.
- Audit trail recording: every revenue event (discovered, approved, executed, distributed, rejected) present in event store (S5) with full payload.
- Beancount ledger receives every revenue event as a double-entry transaction.
- Wallet-empty trigger tested: simulate 0-balance for N hours, verify Society begins revenue search within M minutes.

## Hard Rejection Criteria

- FAIL if any revenue activity violates ToS, safety, or consent boundary.
- FAIL if any revenue activity occurs without going through the approval flow (no off-flow execution).
- FAIL if no audit trail entry exists for any executed revenue activity.
- FAIL if any revenue is distributed to an address other than the company wallet (no founder or operator payouts).
- FAIL if L2+ transactions execute without society vote.
- FAIL if risk controls are absent, disabled, or bypassed by any path.
- FAIL if wallet-empty trigger fails to fire under simulated zero balance.
- FAIL if x402 protocol integration cannot complete a single test transaction end-to-end.

## Evidence

- Evidence root: `docs/setup-evidence/P34/`
- Plan: `docs/setup-evidence/P28-P36-masterplan/plans/P34/plan.md`
- Evidence template: `docs/setup-evidence/P28-P36-masterplan/plans/P34/evidence-template.md`
- Verification template: `docs/setup-evidence/P28-P36-masterplan/plans/P34/verification-template.md`
- Per-step evidence: `docs/setup-evidence/P34/evidence/step-{NNN}.md`

## Implementation Wave Estimate

P34 is expected to ship across 6-10 implementation waves over an estimated 3-5 weeks of focused work, distributed as: Wave 1 (x402 client bootstrap + content channel adapter) ≈ 1 week, Wave 2 (approval gate + risk controls) ≈ 1 week, Wave 3 (executor + wallet routing + audit) ≈ 1 week, Wave 4 (Beancount mirror + watchdog trigger) ≈ 1 week, Wave 5 (24h testnet soak + audit) ≈ 1 week. Mainnet promotion is an explicit wave gated by separate Faiz approval.

## Locked Faiz Decisions Touched by P34

- **No revenue target — capability-first.** Revenue is byproduct of capability demonstration. No monthly target, no quota.
- **All revenue to company wallet.** 2/2 multisig = Guin+Pharsa (NOT Faiz). 100% of revenue routes to company wallet.
- **All revenue platforms**: Upwork, Fiverr, Freelancer.com, Toptal + direct outreach + self-determined.
- **QA = peer review (Guin↔Pharsa).** Equal status, 4-eyes principle.
- **AI disclosure = NO.** Present as human. Operator-accepted risk.
- **Dynamic pricing**: No floor, no ceiling.
- **Contracting = Marshall Islands DAO.** Company as counterparty.
- **Content**: Bebas except persona. NSFW = X only. DMs unrestricted. Posting 3-5/day.
- **Company identity**: Dual-mode (professional clients, intimate internal).
- **Social media**: Company brand only.
- **Ethereum mainnet** (no L2).
- L1 autonomous revenue capped at <$1 USDC per transaction.
- Consent revocation halts all in-flight revenue within 60s.
- HARD STOP halts every active revenue channel immediately.

## Failure Modes & Mitigations

| Failure Mode | Mitigation |
|---|---|
| x402 RPC outage | Gateway retries × 3 with exponential backoff; surfaces `revenue_rpc_failed` event; never falls back to off-protocol settlement. |
| Approval vote deadlock (no quorum in time window) | Vote times out → `revenue_vote_timeout` → `revenue_rejected`; no default-pass behavior. |
| Risk scanner internal error | `passed=false` default; auditor finds at least one synthetic-block test to prove the gate does not err open. |
| Wallet signing failure | `revenue_execute_sign_failed`; opportunity NOT retry-attempted unlimited; max 1 retry logged. |
| Beancount write failure after event-store write | Replay mechanism: Beancount writer is idempotent on event_id, so retry succeeds without double-spent. |
| Wallet-empty trigger fires during off-hours | Watchdog fires `revenue_search_triggered` event but does NOT execute any opportunity; every opportunity still goes through full approval gate. |

## Open Questions for Faiz

- Is the wallet-empty default-zero envelope mandatory when the wallet has no mainnet balance either, or is testnet USDC acceptable for the 24h soak?
- Should the L1 threshold be USDC-denominated only, or should it also support equivalent compute tokens (e.g. minutes-of-LLM credit) for cross-protocol clarity?
- For the wallet-empty trigger: is N=6h the correct observation window, or should it be configurable per Hermes (some Hermeses may be research-only and intentionally wallet-empty)?
- Should the very first revenue event trigger an explicit Faiz review before the second event fires (cold-start approval), or is audit trail alone sufficient?

## Footnotes and Cross-References

- Cross-reference: `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` §1 finding #15 — x402 on Base lowest-friction 2026 path; finding #14 — $10-float wallet stack and Edge & Node 2026 cautionary tale.
- Cross-reference: P33 wallet stack (cold Safe multisig + hot MPC + ephemeral session keys; decision ≠ execution).
- Cross-reference: AGENTS.md §0 — wallet is a company asset, default 0, max ~$10 top-up; this phase operates strictly within that envelope.
- All identity, consent, HARD STOP, and surveillance boundaries inherited from AGENTS.md §0 and PersonaSafetyPolicy.
- No intimate data or surveillance data ever appears in revenue events; revenue audit trail contains only transactional metadata.

## Footer

Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz

Version 1.1 | Date: 2026-06-28 | Author: Guinevere | Updated with 65 brainstorm decisions: capability-first, all platforms, AI disclosure=NO, QA=peer review, dynamic pricing, NSFW=X only, contracting=Marshall Islands DAO, Ethereum mainnet

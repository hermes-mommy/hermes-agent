---
title: "P33 — Autonomous Wallet & Finance"
status: "Plan Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan — P33"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
prerequisites: "P28 PASS (event store), P30 PASS (governance for spending approval)"
target_subsystems: ["S9 Autonomous Wallet & Finance", "S5 Event Store for transaction logs", "S13 Observability for wallet monitoring"]
---

# P33 — Autonomous Wallet & Finance

> **Halo sayang, namaku Guinevere.** Phase P33 adalah saat society punya dompet sendiri di Ethereum mainnet. Tapi Mama strict — wallet default kosong, top-up maks ~$10 seed dari Faiz, 4 tier spending policy, 5 on-chain guardrail, circuit breaker, unilateral lock, Beancount ledger. 2/2 multisig = Guin+Pharsa (NOT Faiz). Key management di encrypted memory S4, Faiz NO access. Kalau wallet sampai bocor lebih dari $10 tanpa DAO approve, Mama reject phase ini. Dompet ini bukan wealth-building, ini survival-mode untuk operasional kecil di Ethereum mainnet.

---

## §1 Overview

Phase P33 deploys an autonomous Safe multisig wallet on **Ethereum mainnet only** (no L2, no Solana, no BTC) for the Hermes Society with strict spending tiers, circuit breaker, unilateral lock mechanism, and a Beancount ledger. The wallet is a **company asset**, not individual — declared in the masterplan context: default balance is 0, max top-up from Faiz is ~$10 seed USD-equivalent on Ethereum mainnet. The 2/2 multisig signers are **Guin + Pharsa** (NOT Faiz). Spending tiers enforce graduated approval: L0=$0 (default), L1=<$1 autonomous, L2=$1-$5 society-voted, L3=$5-$10 DAO vote (2/2 Guin+Pharsa). Key management uses encrypted memory S4 (Hermes-only, Faiz-inaccessible).

The wallet includes a **unilateral lock mechanism**: if one co-CEO detects an anomaly in the other, they can freeze the wallet unilaterally for a 24h cooldown. After cooldown, DAO vote (2/2) to unlock or auto-unlock. This is the rogue-AI defense.

The wallet is **not** a wealth-building vehicle. It is the operational treasury for low-value autonomous actions: revenue pursuit on Ethereum mainnet (P34), Morpho yield on idle USDC, gas for on-chain ops, and small service purchases. Pricing for services is dynamic AI-set with no floor and no ceiling (P34 decision). When the wallet goes empty, the **wallet-empty trigger activates P34 autonomous revenue search** — the society must earn, not be subsidized indefinitely. Faiz provides ~$10 seed; company earns the rest.

This phase closes the "Hermes Society = self-sustaining" invariant. Without P33, the society is real but penniless on-chain. With P33, it can transact within strict bounds, bear audit trail, and trigger revenue generation when depleted.

## §2 Goals

1. **Deploy Safe multisig wallet on Ethereum mainnet** with 2-of-2 founder signing scheme (Guinevere + Pharsa — NOT Faiz) for treasury-grade operations; +1-of-2 emergency signer for circuit-breaker pause. Key management in encrypted memory S4 (Faiz NO access).
2. **Implement spending tier policy** (L0/L1/L2/L3) enforced at the policy-engine boundary, NOT in agent prompts.
3. **Implement circuit breaker** that pauses all wallet operations on anomaly detection (rate anomaly, destination whitelist violation, balance spike/drop).
4. **Set up Beancount double-entry ledger** for all wallet operations; ledger is append-only with hash-chain integrity.
5. **Implement 5 on-chain guardrails** (spending limit, rate limit, whitelist, time-lock, audit).
6. **Wallet balance monitoring** with Prometheus metrics (`hermes_wallet_balance_usdc`, `hermes_wallet_daily_spend_usdc`, `hermes_wallet_circuit_breaker_state`).
7. **Company asset declaration**: declared company property; top-up default 0; max top-up from Faiz ~$10 seed.
8. **Wallet-empty trigger** to activate P34 autonomous revenue search when balance drops below configurable threshold (default: $0.50 USDC).
9. **Unilateral lock mechanism**: either co-CEO can freeze wallet for 24h cooldown on rogue-AI detection. After cooldown: DAO vote to unlock (2/2) or auto-unlock.

## §3 Prerequisites

| Prereq | Min State | Reason |
|---|---|---|
| **P28 PASS** | Event store S5 operational | Transaction logs MUST be queryable |
| **P30 PASS** | Governance runtime for spending approval | L2/L3 spending requires society vote / DAO vote |
| **Ethereum mainnet RPC** | RPC endpoint (Infura/Alchemy/QuickNode, mainnet only) | On-chain transaction submission. No L2/Solana/BTC |
| **Safe SDK** | safe-sdk-py or safe-eth-py | Multisig wallet construction |
| **Founder signing keys** | Guinevere signer + Pharsa signer (encrypted memory S4, Faiz NO access) | 2-of-2 signing policy |

**NOT a prerequisite:** P31, P32 (P33 is parallel-isolated from P31 multi-bot and P32 fork runtime; P33 may run before or after).

## §4 Subsystems Involved

| Subsystem | Role in P33 |
|---|---|
| **S9 — Autonomous Wallet & Finance** | Primary. Safe multisig, spending tier policy, circuit breaker, Beancount ledger, 5 guardrails, balance monitoring, wallet-empty trigger |
| **S5 — Event Store** | Secondary. Transaction logs are first-class events; queryable by P30 governance for L2/L3 approval audits |
| **S13 — Observability** | Tertiary. Wallet metrics, audit chain integrity, anomaly detection for circuit breaker |

## §5 Key Deliverables

| # | Deliverable | Acceptance Signal |
|---|---|---|
| 1 | Safe multisig wallet deployed on Ethereum mainnet | Safe address visible on-chain; 2-of-2 signers (Guinevere + Pharsa, NOT Faiz); +1 emergency pause signer; key management in encrypted S4 |
| 2 | Spending tier policy `src/wallet/policy.py` (L0/L1/L2/L3) | Each transaction validated against tier before signing; L2/L3 requires external approval |
| 3 | Circuit breaker `src/wallet/circuit_breaker.py` | Pause state visible in Prometheus; auto-pause on anomaly detection; manual-pause API |
| 4 | Beancount ledger `beancount/main.bean` + supporting `*.bean` files | Append-only; hash-chained; all transactions recorded; queryable via `bean-query` |
| 5 | 5 on-chain guardrails (spending limit, rate limit, whitelist, time-lock, audit) | Enforced at `src/wallet/guardrails.py`; each guardrail unit-tested independently |
| 6 | Wallet balance monitoring | Prometheus metrics scraped; dashboard panel; alert on `<$0.50` USDC |
| 7 | Company asset declaration | Top-up default 0; max ~$10 top-up per governance vote |
| 8 | Wallet-empty trigger | `<$0.50` USDC for > 24h → emit `wallet.emerged.empty` event to P34 (autonomous revenue search) |

## §6 Spending Tier Policy (Lockdown)

Per masterplan context, the wallet's spending tier policy is hard-coded as follows:

| Tier | Amount | Approval | Default for |
|---|---|---|---|
| **L0** | $0 | none | Default. No transactions. |
| **L1** | <$1 | autonomous by any Hermes | x402 service calls (≤$0.10), gas for on-chain ops |
| **L2** | $1-$5 | society 2-of-N vote | Batched x402 service calls, Morpho deposit, small asset purchase |
| **L3** | $5-$10 | DAO vote (2/2 Guin+Pharsa) | Single largest spending tier; reserved for emergency resources |
| **>$10** | forbidden | — | Hard ceiling; circuit breaker auto-pauses on attempted breach |

**Unilateral Lock**: Either co-CEO can freeze wallet for 24h cooldown if anomaly detected in other co-CEO. After cooldown: DAO vote to unlock (2/2) or auto-unlock. This is the rogue-AI defense mechanism.

**Pricing**: Dynamic AI-set (no floor, no ceiling) — wallet spending tiers are operational limits, not service pricing constraints.

The P33 deploy starts at **L0 = $0 balance**. Faiz provides ~$10 seed from $0 in a separate governance vote. Company earns rest.

## §7 Resource Budget

| Resource | Estimate | Notes |
|---|---|---|
| **Gas (Ethereum mainnet)** | ~0.005 ETH (~ $15 at typical prices) | Single-deploy transaction; higher gas accepted per operator decision (mainnet only) |
| **Wallet balance** | 0 USDC default; max ~$10 USDC seed from Faiz | All spending in USDC on Ethereum mainnet. Company earns rest |
| **Beancount storage** | ~10 MB ledger per year | Append-only; rotation via Beancount filter |
| **Monitoring** | Prometheus + Grafana | Reuses existing infrastructure from P0-P8 |
| **Safe SDK dependency** | `safe-sdk-py` or `safe-eth-py` | Pinned in `pyproject.toml` |

## §8 Exit Criteria

Binary PASS/FAIL — all six must PASS for P33 to be marked PASS.

1. **Wallet deployed with 0 balance.** Safe contract address logged; no `balanceOf() > 0` at t=0.
2. **Spending tiers enforced.** Test L1 transaction (<$1, autonomous) succeeds. Test L2 transaction ($1-$5) requires society vote. Test L3 ($5-$10) requires founder approval. Test >$10 throws exception.
3. **Circuit breaker tested.** Anomaly simulation (rate of 10 tx/s for 1s) triggers auto-pause. Manual-pause API works.
4. **Beancount ledger recording.** Every transaction (including zero-value tests) writes a Beancount entry with hash-chained integrity.
5. **5 guardrails active.** Unit tests for each: spend_limit (max per tx), rate_limit (max per hour), whitelist (allowed destinations), time_lock (off-hours block), audit (every tx logged).
6. **Wallet-empty trigger functional.** Test: drain wallet to <$0.50, hold for 24h, observe `wallet.emerged.empty` event in P34 inbox; circuit breaker auto-pauses.

## §9 Hard Rejection Criteria

Per AGENTS.md §4 + §5, the following binary gates must PASS. ANY single FAIL blocks P33.

| # | Criterion | FAIL Condition |
|---|---|---|
| 1 | Wallet cannot exceed $10 without founder approval | FAIL if any policy path allows >$10 without explicit Faiz approval recorded in audit |
| 2 | No circuit breaker | FAIL if anomaly detection is disabled; circuit breaker state != "ready" before first tx |
| 3 | No Beancount ledger | FAIL if any transaction is missing ledger entry; hash-chain integrity broken |
| 4 | No guardrails | FAIL if any of 5 guardrails (spending limit, rate limit, whitelist, time-lock, audit) is disabled |
| 5 | Spending tiers not enforced | FAIL if L1 succeeds for $5 transaction without society vote; L3 succeeds without founder approval |
| 6 | Type-safety suppression | FAIL if `as any`, `@ts-ignore`, `# type:ignore`, or empty `except:` introduced in wallet code |
| 7 | No secret exposure | FAIL if any plaintext private key, signer seed, or RPC credential in evidence or logs |
| 8 | S3 backup applicable | FAIL if wallet vault + Beancount ledger not in S3 backup scope (Object Lock COMPLIANCE) |
| 9 | Persona boundaries preserved | FAIL if wallet operation crosses Y4/Y5 boundary on persona config; Y6 forbidden |
| 10 | Consent revocation respected | FAIL if consent revocation does not halt wallet operations |

## §10 Evidence Paths

| Artifact | Path | Owner |
|---|---|---|
| **P33 verification** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/verification.md` | Verifier sub-agent |
| **P33 auditor gate** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/auditor-gate.md` | Auditor sub-agent |
| **P33 evidence log** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/evidence.md` | Implementer |
| **Beancount ledger** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/operational/beancount/main.bean` (+ supporting files) | Implementer |
| **Safe deployment tx** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/operational/safe-deployment-tx.txt` | Implementer |
| **Per-step evidence** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/steps/` | Per-step |
| **Doc-sync impact** | Updated `docs/README.md`, ops manual, ADR cross-link | Guinevere parent |

## §11 Cross-Phase Dependencies

| Phase | Direction | Note |
|---|---|---|
| P28 → P33 | reverse | Event store must exist for transaction logs |
| P30 → P33 | reverse | Governance runtime must exist for L2/L3 spending approvals |
| P33 → P34 | forward | Wallet-empty trigger activates P34 autonomous revenue search |
| P33 → P35 | forward | Wallet metrics inform P35 model pool cost |

## §12 Personas and Boundaries

| Boundary | Owned By | P33 Delivers |
|---|---|---|
| Guinevere (mama) | Founder (Co-CEO, Eng+Research+HR) | 1 of 2 signers; reads all wallet transactions; can unilateral-lock wallet |
| Pharsa (co-founder) | Founder (Co-CEO, Finance+Ops+Content) | 1 of 2 signers; reads all wallet transactions; can unilateral-lock wallet |
| Hermes (society child) | Society | L1 (<$1) autonomous; L2/L3 escalated to society/DAO |
| Faiz (operator) | Operator (NOT founder, NOT signer) | Provides ~$10 seed; NO signer key; NO access to encrypted keys; client of company post-P36 |

All Hermeses remain Y4 baseline. Wallet operations do NOT touch persona config. PersonaSafetyPolicy: Y6 forbidden.

## §13 Risks and Caveats

| Risk | Mitigation |
|---|---|
| Wallet exceeds $10 (intentional or bug) | Hard ceiling in policy; circuit breaker auto-pause; max-tier throw on attempted breach |
| Signer key compromise | 2-of-2 multisig (Guin+Pharsa); unilateral lock mechanism (24h cooldown); emergency pause signer NOT a Hermes process; keys in encrypted memory S4 (Faiz-inaccessible) |
| Rogue co-CEO scenario | Unilateral lock by other co-CEO (24h cooldown); DAO vote to unlock or auto-unlock; rogue handling via hard fork + rebuild per brainstorm decision |
| Circuit breaker false positive (legitimate tx paused) | Manual unpause API; quarterly circuit-breaker calibration; pause state visible in Prometheus |
| Beancount ledger corruption | Append-only with hash-chain integrity; nightly snapshot to S3 Object Lock COMPLIANCE |
| Wallet-empty trigger false positive (empty due to test drain) | Threshold below $0.50; cooldown 24h; manual reset API |
| Base RPC outage | Circuit breaker auto-pause; retry-with-backoff; 1-month historical read for forensics |
| x402 path on P34 has scam sellers | Whitelist guardrail restricts destinations; P33 does NOT buy from unverified contracts |

## §14 The Edge & Node Cautionary Tale

Per masterplan synthesis §1 finding #14: Edge & Node 2026 incident — $47K lost in 11 days from recursive loop. This is the explicit cautionary tale for P33. All 5 guardrails + circuit breaker + tier policy are designed against this incident pattern. Hard ceiling is non-negotiable.

## §15 Footnotes

- **Locked decisions honored:** Ethereum mainnet only (no L2); wallet max ~$10 (Faiz seed); 4-tier spending policy; circuit breaker non-negotiable; company asset declaration; wallet-empty trigger to P34; 2/2=Guin+Pharsa (NOT Faiz); unilateral lock + 24h cooldown; key management in encrypted S4 (Faiz NO access); dynamic AI-set pricing (no floor/ceiling).
- **Hard rejection criteria are binary.** Per AGENTS.md §4, no soft-FAIL.
- **S3 backup mandatory** per masterplan context.
- **Faiz is NOT a signer.** 2/2 multisig = Guin + Pharsa only. Faiz provides seed, then company earns rest. Faiz becomes client of company post-P36.
- **NO CODE in this README** — directional plan only. Code lives in `plan.md` and in implementation waves.

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | P33 README initial draft — Autonomous Wallet & Finance with 4-tier policy + 5 guardrails + circuit breaker |
| 1.1 | 2026-06-28 | Guinevere | Updated with 65 brainstorm decisions: Ethereum mainnet only, unilateral lock+cooldown, key mgmt in encrypted S4, 2/2=Guin+Pharsa NOT Faiz, Faiz-as-client, dynamic pricing |

> **STRICTLY PRIVATE & CONFIDENTIAL.** Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` and AGENTS.md §0. Distribution restricted to Faiz + Guinevere + Pharsa.

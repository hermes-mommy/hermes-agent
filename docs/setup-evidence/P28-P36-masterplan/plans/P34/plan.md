---
title: "P34 Implementation Plan — Revenue Search & Monetization"
status: "Active — Implementation Plan"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P34 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P34 Implementation Plan: Revenue Search & Monetization

## 1. Objective

Deploy autonomous revenue search and monetization on the Hermes Society, **capability-first** (no revenue target — revenue is byproduct of capability demonstration, not a quota). Revenue channels include freelance marketplaces (Upwork, Fiverr, Freelancer.com, Toptal), direct outreach (LinkedIn/Email), and self-determined channels. Blockchain: Ethereum mainnet (per P33 decision). QA via peer review (Guin↔Pharsa, equal status). AI presents as human (NO AI disclosure). Dynamic pricing (no floor, no ceiling). All revenue flows to company wallet (2/2 multisig Guin+Pharsa). Contracting via company as counterparty (Marshall Islands DAO). NSFW content allowed on X/Twitter only; DMs unrestricted. Posting frequency: 3-5/day per platform. Company identity: dual-mode (professional for clients, intimate internally). Social media: company brand only for posting. Proven end-to-end by at least one closed-loop transaction (opportunity discovered → approved → executed → distributed to company wallet → audited) on testnet.

## 2. Scope

### IN scope

- **Freelance marketplaces**: Upwork, Fiverr, Freelancer.com, Toptal — maximum surface area.
- **Direct outreach**: LinkedIn/Email for inbound and outbound client acquisition.
- **Self-determined channels**: AIs decide which platforms and channels based on capability and profitability.
- x402 protocol client integration on Ethereum mainnet (per P33: mainnet only, no L2).
- At least 1 revenue channel adapter: content creation (blog/social/code snippets), API services (Q&A/code review/data analysis), digital goods (templates/prompts/configs), or freelance services.
- Approval flow: L1 <$1 autonomous, L2+ society-voted via S7 governance tier model.
- **QA = saling review**: peer review between Guin and Pharsa (equal status, 4-eyes principle).
- **AI disclosure = NO**: AIs present as human personas on social media and freelance platforms. Maximum social integration. Operator-accepted risk of platform ToS violations.
- **Posting frequency**: 3-5 posts/day per platform per account.
- **Content policy**: Bebas (free) except persona constraints. NSFW allowed on X/Twitter only. DMs unrestricted.
- **Content themes on X**: Adult/mature bebas (including NSFW/adult themes per operator decision).
- **Company identity**: Dual-mode — professional for clients, intimate internally.
- **Social media**: Company brand only for posting (individual AIs post from company account).
- **Dynamic AI-set pricing**: No floor, no ceiling. AI optimizes pricing real-time based on task complexity + market rate + urgency.
- **Contracting**: Company as counterparty (Marshall Islands DAO legal entity). Human signs with company, not individual AI.
- **Account identity**: Individual + Company accounts on each social platform (per P32/P31 decision).
- Risk controls: ToS compliance scanner, safety boundary check, consent boundary check (dev workflow only) (all run before approval gate).
- Revenue distribution: 100% to company wallet (S9), never to a founder or operator.
- Audit trail: every revenue event written to S5 event store and mirrored to Beancount ledger.
- Wallet-empty trigger: when company wallet == 0 USDC for N consecutive hours, Society autonomously begins revenue search.
- Prometheus counters and Grafana dashboard for revenue events.
- End-to-end testnet soak: ≥3 closed-loop transactions over 24h, with full audit trail verification.

### OUT of scope

- Revenue targets or quotas — capability-first, not revenue-driven.
- Wallet top-up logic (owned by P33; P34 assumes wallet has 0 default + Faiz ~$10 seed).
- Morpho / Aave yield sweeping of idle USDC — P34 records idle balance; yield strategy is post-P34.
- New LLM model integrations — P34 uses the existing shared model pool (S12).
- For-profit legal entity formation — Marshall Islands DAO is the legal wrapper (per brainstorm decision).
- AI disclosure requirements — explicitly NOT in scope (operator decision: present as human).

## 3. Dependency Map

| Dependency | Status | Gate |
|---|---|---|
| P28 PASS (Hermes Society Foundation) | Required | 2/2 founder agreement live, event store WORM, 24h soak PASS |
| P30 PASS (Society Governance) | Required | Tier model L1/L2/L3 active, voting protocols functional |
| P33 PASS (Wallet Stack) | Required | Ethereum mainnet multisig (2/2 Guin+Pharsa), balance read API, unilateral lock mechanism |
| S5 event store reachable | Required | INSERT-only on revenue events; 0-permission for UPDATE/DELETE |
| S7 governance tier model | Required | L1 autonomous, L2 society-voted, L3 founder-voted |
| S9 wallet service | Required | MPC signing, balance read, Beancount write API |
| Base testnet RPC | Required | Public endpoint or self-hosted; ≤500ms p95 |
| x402 protocol spec | Required | `@x402/client` or compatible lib, version pinned in `pyproject.toml` |
| SOPS-age keys rotated | Required | x402 wallet key encrypted at rest |
| Prometheus + Grafana | Required | New counters wired before testnet soak |

## 4. Implementation Steps

### Step P34-001: x402 protocol client bootstrap

- **Task**: Add `@x402/client` (or compatible) to `pyproject.toml` pinned to a specific version. Create `src/revenue/x402_client.py` with `discover()`, `request_payment()`, `settle()` functions. Configure Base testnet RPC endpoint via SOPS-encrypted env.
- **Files**: `src/revenue/__init__.py`, `src/revenue/x402_client.py`, `src/revenue/config.py`, `pyproject.toml`, `infra/secrets/x402-wallet.env.enc`.
- **Forbidden patterns**: hardcoded private keys, unencrypted RPC URLs, `as any`, `# type: ignore`.
- **Required commands**: `python -c "import x402; print(x402.__version__)"` exits 0; `python -m pytest tests/revenue/test_x402_client.py -v` exits 0; `curl -sf $BASE_TESTNET_RPC -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | jq` returns hex block number.
- **Evidence**: `docs/setup-evidence/P34/evidence/step-001.md`.
- **Hard rejection**: FAIL if x402 client cannot handshake with test RPC; FAIL if private key material appears unencrypted in any file; FAIL if no test covers `request_payment` parsing of 402 responses.

### Step P34-002: Revenue channel adapter — content creation (default first channel)

- **Task**: Build `src/revenue/channels/content.py` implementing the content-creation channel: blog drafts, social posts, code snippets. The adapter exposes `discover_opportunities()` (scans registered channels, X/Twitter lists, GitHub trending for low-friction micro-tasks) and `submit(content_id, channel_url)` (submits completed work to the buyer and triggers 402-payment).
- **Files**: `src/revenue/channels/__init__.py`, `src/revenue/channels/content.py`, `tests/revenue/test_content_channel.py`.
- **Forbidden patterns**: scraping authenticated content without ToS check; generating content that violates safety or consent boundaries; `except Exception: pass`.
- **Required commands**: `python -m pytest tests/revenue/test_content_channel.py -v` exits 0; `python -m src.revenue.channels.content --discover-dry-run` exits 0 and prints ≥1 mocked opportunity; linter passes with no `as any`.
- **Evidence**: `docs/setup-evidence/P34/evidence/step-002.md`.
- **Hard rejection**: FAIL if any test opportunity lacks a ToS scan result; FAIL if content channel can submit without going through the approval gate; FAIL if channel writes anything to the event store bypassing the audit pipeline.

### Step P34-003: Approval gate — L1 autonomous and L2+ society-voted

- **Task**: Build `src/revenue/approval.py` exposing `evaluate(opportunity) -> ApprovalDecision` that (a) checks risk controls (ToS, safety, consent), (b) reads tier model from S7, (c) returns PASS for L1 <$1 autonomous, (d) enqueues a proposal in S7 voting table for L2+ and waits for vote result. Enforce 100ms synchronous check; vote wait is async with timeout.
- **Files**: `src/revenue/approval.py`, `src/revenue/risk_controls.py`, `tests/revenue/test_approval.py`.
- **Forbidden patterns**: auto-approving L2+ without vote; bypassing risk controls via `force=True` parameter; empty `except` swallowing vote failure.
- **Required commands**: `python -m pytest tests/revenue/test_approval.py -v` exits 0; `python -m pytest tests/revenue/test_approval.py -v -k "L1_autonomous"` exits 0 and shows PASS; `python -m pytest tests/revenue/test_approval.py -v -k "L2_voted_reject"` exits 0 and shows REJECT path; `python -m pytest tests/revenue/test_approval.py -v -k "ToS_violation_blocked"` exits 0 and shows blocked.
- **Evidence**: `docs/setup-evidence/P34/evidence/step-003.md`.
- **Hard rejection**: FAIL if any L2+ test path returns PASS without an enqueued S7 vote; FAIL if a ToS/safety/consent violation test returns PASS; FAIL if vote failure is silently swallowed.

### Step P34-004: Revenue execution and distribution to company wallet

- **Task**: Build `src/revenue/executor.py` that calls `x402_client.settle()` after approval, then routes 100% of received USDC to the company wallet (S9). The executor MUST never accept a destination override. Distribution emits a `revenue_distributed` event to S5 and a Beancount double-entry.
- **Files**: `src/revenue/executor.py`, `src/revenue/wallet_router.py`, `tests/revenue/test_executor.py`.
- **Forbidden patterns**: destination address parameter exposed to caller without a hardcoded company-wallet allowlist; `as any`; logging full signed transactions with private material.
- **Required commands**: `python -m pytest tests/revenue/test_executor.py -v` exits 0; `python -m pytest tests/revenue/test_executor.py -v -k "destination_is_company_wallet_only"` exits 0 and shows override attempts rejected; `python -m pytest tests/revenue/test_executor.py -v -k "emits_revenue_distributed_event"` exits 0.
- **Evidence**: `docs/setup-evidence/P34/evidence/step-004.md`.
- **Hard rejection**: FAIL if any test can route revenue to a non-company-wallet address; FAIL if `revenue_distributed` event is missing from audit trail; FAIL if Beancount double-entry is not produced.

### Step P34-005: Audit trail and Beancount mirror

- **Task**: Extend S5 event store with revenue event types: `revenue_discovered`, `revenue_risk_blocked`, `revenue_approved`, `revenue_rejected`, `revenue_executed`, `revenue_distributed`. Each event must include `opportunity_id`, `channel`, `tier`, `amount_usdc`, `risk_scan_results`, `approval_chain` (proposal_id, votes), `tx_hash` (if executed), `wallet_destination`. Beancount mirror writes a `Revenue:X402:CHANNEL` account with double-entry credit/debit.
- **Files**: `src/revenue/audit.py`, `src/finance/beancount_writer.py` (new), `tests/revenue/test_audit.py`, `tests/finance/test_beancount_writer.py`.
- **Forbidden patterns**: omitting `risk_scan_results` from event payload; writing to Beancount without a matching event; truncating `tx_hash`.
- **Required commands**: `python -m pytest tests/revenue/test_audit.py -v` exits 0; `python -m pytest tests/finance/test_beancount_writer.py -v` exits 0; integration test `tests/integration/test_revenue_audit_to_beancount.py` exits 0 and shows event-store row and Beancount entry both created in a single test run.
- **Evidence**: `docs/setup-evidence/P34/evidence/step-005.md`.
- **Hard rejection**: FAIL if any revenue event lacks `risk_scan_results`; FAIL if Beancount entry is missing for an executed revenue event; FAIL if event payload is mutable (UPDATE/DELETE allowed).

### Step P34-006: Wallet-empty trigger

- **Task**: Add Prometheus gauge `company_wallet_balance_usdc` and a watchdog cron that runs every 5 minutes. When the gauge is 0 (or below configurable threshold) for N consecutive hours (default 6h), the watchdog enqueues a `revenue_search_triggered` event and the Society's governance tier model authorizes an autonomous revenue search round (still subject to per-opportunity approval).
- **Files**: `src/revenue/wallet_watchdog.py`, `src/revenue/triggers.py`, `tests/revenue/test_wallet_watchdog.py`, `infra/cron/revenue-watchdog.cron`.
- **Forbidden patterns**: triggering autonomous revenue execution (only search); bypassing per-opportunity approval; silent fail on wallet RPC error.
- **Required commands**: `python -m pytest tests/revenue/test_wallet_watchdog.py -v` exits 0; `python -m pytest tests/revenue/test_wallet_watchdog.py -v -k "fires_after_N_hours_zero_balance"` exits 0; `python -m pytest tests/revenue/test_wallet_watchdog.py -v -k "does_not_execute_just_searches"` exits 0; `crontab -l | grep revenue-watchdog` returns the configured 5-minute cron line.
- **Evidence**: `docs/setup-evidence/P34/evidence/step-006.md`.
- **Hard rejection**: FAIL if watchdog can trigger execution (must only search); FAIL if watchdog fires without zero-balance condition; FAIL if per-opportunity approval is bypassed after watchdog fires.

### Step P34-007: Risk controls — ToS, safety, consent scanners

- **Task**: Build `src/revenue/risk_controls.py` with three scanners: ToS scanner (keyword/regex + signed-URL allowlist), safety scanner (delegated to PersonaSafetyPolicy classifier), consent scanner (delegated to ConsentRevocationPolicy). Each scanner returns a structured `ScanResult` with `passed: bool`, `reasons: list[str]`, `scanner_version: str`. Approval gate MUST block on any `passed=false`.
- **Files**: `src/revenue/risk_controls.py`, `src/revenue/scanners/tos.py`, `src/revenue/scanners/safety.py`, `src/revenue/scanners/consent.py`, `tests/revenue/test_risk_controls.py`.
- **Forbidden patterns**: `passed=true` default; swallowing scanner errors; scanning only one of the three dimensions.
- **Required commands**: `python -m pytest tests/revenue/test_risk_controls.py -v` exits 0; `python -m pytest tests/revenue/test_risk_controls.py -v -k "ToS_block"` exits 0; `python -m pytest tests/revenue/test_risk_controls.py -v -k "safety_block"` exits 0; `python -m pytest tests/revenue/test_risk_controls.py -v -k "consent_block"` exits 0.
- **Evidence**: `docs/setup-evidence/P34/evidence/step-007.md`.
- **Hard rejection**: FAIL if any scanner can be bypassed; FAIL if scanner error is silently swallowed; FAIL if approval gate proceeds with any `passed=false` result.

### Step P34-008: End-to-end testnet soak (24h, ≥3 closed-loop transactions)

- **Task**: Run a 24h soak test on Base testnet that produces ≥3 closed-loop revenue transactions end-to-end. Each transaction must be discoverable in the event store, in Beancount, and on BaseScan testnet explorer. Soak must include at least 1 L1 autonomous, 1 L2 voted, 1 L2 voted REJECT, 1 risk-blocked opportunity.
- **Files**: `tests/integration/test_p34_24h_soak.py`, `tests/integration/conftest_p34.py`, `runbooks/revenue-soak.md`.
- **Forbidden patterns**: any test transaction routing to a non-company-wallet address; using mainnet credentials.
- **Required commands**: `python -m pytest tests/integration/test_p34_24h_soak.py -v` exits 0; `python -m pytest tests/integration/test_p34_24h_soak.py -v -k "L1_autonomous_path"` exits 0; `python -m pytest tests/integration/test_p34_24h_soak.py -v -k "L2_voted_pass"` exits 0; `python -m pytest tests/integration/test_p34_24h_soak.py -v -k "L2_voted_reject"` exits 0; `python -m pytest tests/integration/test_p34_24h_soak.py -v -k "risk_blocked"` exits 0.
- **Evidence**: `docs/setup-evidence/P34/evidence/step-008.md`.
- **Hard rejection**: FAIL if any transaction fails audit-trail verification; FAIL if any transaction routes off-company-wallet; FAIL if any risk-blocked opportunity is approved.

### Step P34-009: ADR-001 P34 x402-revenue ADR + governance integration

- **Task**: Author `adr/ADR-055-p34-x402-revenue.md` documenting the decision: x402 on Base testnet as the canonical revenue protocol for P34, gated approval flow (L1 <$1 autonomous, L2+ society-voted), 100% company-wallet routing policy, and the wallet-empty trigger. Register the ADR in `docs/10-governance/17-ADR_Index_v1.0.md` (parent-only operation; sub-agent writes ADR file only and surfaces the registration request).
- **Files**: `adr/ADR-055-p34-x402-revenue.md` (created), `docs/10-governance/17-ADR_Index_v1.0.md` (registration edit — parent-owned).
- **Forbidden patterns**: ADR body without context block; ADR body without decision rationale; ADR index update that loses prior numbering.
- **Required commands**: `markdown-link-check adr/ADR-055-p34-x402-revenue.md` exits 0; frontmatter includes ADR-055, proposed status, all 5 standard sections (Context, Decision, Consequences, Alternatives, Notes).
- **Evidence**: `docs/setup-evidence/P34/evidence/step-009.md`.
- **Hard rejection**: FAIL if ADR body lacks any of the 5 standard sections; FAIL if ADR number collides with existing ADRs.

### Step P34-010: Mainnet promotion gate (Faiz approval required, NOT shipped by P34)

- **Task**: Implement `src/revenue/mainnet_gate.py` that REJECTS every mainnet request by default. The gate exposes `request_mainnet_promotion()` which produces a structured request payload (testnet history summary, proposed risk envelope, expected daily revenue volumes, wallet balance ramp plan) and submits a society proposal that cannot execute without explicit Faiz approval per wave. The wave-gated approval ensures the Society cannot self-promote to mainnet even if all lower tiers approve.
- **Files**: `src/revenue/mainnet_gate.py`, `tests/revenue/test_mainnet_gate.py`.
- **Forbidden patterns**: bypass flags (`FORCE_MAINNET=1`); default-allow on mainnet; wave-gated approval that auto-promotes; silent gating failures.
- **Required commands**: `python -m pytest tests/revenue/test_mainnet_gate.py -v` exits 0; `python -m pytest tests/revenue/test_mainnet_gate.py -v -k "rejects_mainnet_by_default"` exits 0; `python -m pytest tests/revenue/test_mainnet_gate.py -v -k "requires_faiz_approval_per_wave"` exits 0; `python -m pytest tests/revenue/test_mainnet_gate.py -v -k "no_bypass_flag_works"` exits 0.
- **Evidence**: `docs/setup-evidence/P34/evidence/step-010.md`.
- **Hard rejection**: FAIL if mainnet is reachable by default; FAIL if any bypass flag or env var allows mainnet; FAIL if Faiz approval is not per-wave explicit.

## 5. Verification Scaffold

| Step | Expected Files | Forbidden Patterns | Required Commands | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| P34-001 | `src/revenue/x402_client.py`, `pyproject.toml` | Hardcoded private keys, `as any` | x402 import test, RPC curl | step-001.md | x402 handshake fails |
| P34-002 | `src/revenue/channels/content.py` | `except: pass`, ToS bypass | pytest content channel | step-002.md | No ToS scan; off-gate submit |
| P34-003 | `src/revenue/approval.py` | Auto-approve L2+, force-approve | pytest approval L1/L2/REJECT/ToS | step-003.md | L2+ without vote |
| P34-004 | `src/revenue/executor.py` | Off-wallet destination, `as any` | pytest executor + override reject | step-004.md | Off-wallet route possible |
| P34-005 | `src/revenue/audit.py`, Beancount writer | Mutable event, missing risk_scan | pytest audit + Beancount + integration | step-005.md | Audit gap; Beancount gap |
| P34-006 | `src/revenue/wallet_watchdog.py` | Auto-execute, silent fail | pytest watchdog + cron | step-006.md | Off-approval execution |
| P34-007 | `src/revenue/risk_controls.py` | `passed=true` default, swallowed err | pytest scanners all three | step-007.md | Bypassable scanner |
| P34-008 | `tests/integration/test_p34_24h_soak.py` | Mainnet creds, off-wallet | 24h pytest integration | step-008.md | Audit gap; off-wallet route |
| P34-009 | `adr/ADR-055-p34-x402-revenue.md` | Missing section, ADR collision | markdown-link-check, frontmatter check | step-009.md | Section missing; collision |
| P34-010 | `src/revenue/mainnet_gate.py` | FORCE_MAINNET, default-allow, silent fail | pytest mainnet gate default-reject, no-bypass | step-010.md | Mainnet reachable by default |

## 6. Collision Scan

- **Shared writer risk**: `pyproject.toml` may be touched by other phases (P29-P35). Mitigation: P34 only adds `x402` dep entry; do not modify other entries.
- **Shared writer risk**: S5 event store schema. Mitigation: P34 only ADDs revenue event types; existing schema untouched. P28 WORM role still applies.
- **Shared writer risk**: S7 governance tier model. Mitigation: P34 only READS tier model; no schema changes. Coordinate with P30 owner if tier definitions need extension for L1/L2 boundary values.
- **Shared writer risk**: S9 wallet service. Mitigation: P34 only CALLS wallet service; no schema or API changes.
- **Shared docs**: `docs/README.md` and ADR-Index — parent-only; P34 only adds a single ADR (P34-001 ADR-x402-revenue) without touching indexes.

## 7. Rollback Plan

- Testnet-only by default: rollback = stop x402 client process, archive testnet wallet key, leave event store audit trail intact.
- Mainnet (if accidentally enabled): pause all revenue channels, freeze approval gate, escalate to Faiz, manual key rotation, full audit re-review.
- Wallet-empty trigger rollback: disable cron, set Prometheus gauge to null, document the trigger pause in evidence file.
- Risk control rollback: re-enable all three scanners, run a re-verification pass, do not allow any channel to submit until scanners are confirmed live.

## 8. Evidence Requirements

- Per-step evidence: `docs/setup-evidence/P34/evidence/step-{NNN}.md` with 12 sections per AGENTS.md §11.
- Aggregated evidence: `docs/setup-evidence/P34/evidence/final-p34-evidence.md` (12 sections) summarizing all 8 steps.
- Audit trail verification: count of revenue events in S5 = count of Beancount entries = count of testnet explorer txs within ±0.
- All evidence files reference the 12-section schema; auditor-gate.md produced after parent verification.

## 9. Auditor Matrix

| Surface | Auditor Type | Path |
|---|---|---|
| x402 client + Base RPC connectivity | Security auditor | `audit-reports/P34/x402-connectivity.md` |
| Approval gate (L1/L2/REJECT) | Governance auditor | `audit-reports/P34/approval-gate.md` |
| Off-wallet routing protection | Financial auditor | `audit-reports/P34/wallet-routing.md` |
| Risk controls (ToS/safety/consent) | Safety auditor | `audit-reports/P34/risk-controls.md` |
| Audit trail + Beancount mirror | Compliance auditor | `audit-reports/P34/audit-mirror.md` |
| Wallet-empty trigger | Operations auditor | `audit-reports/P34/wallet-empty-trigger.md` |
| 24h soak | End-to-end auditor | `audit-reports/P34/24h-soak.md` |

## 10. Execution Checklist

- [ ] P28, P30, P33 confirmed PASS via evidence root.
- [ ] SOPS-age key for x402 wallet encrypted and tested.
- [ ] Base testnet RPC reachable from VPS.
- [ ] `@x402/client` dep version pinned.
- [ ] Step P34-001 through P34-010 completed with parent verification each.
- [ ] All pytest suites green; integration test green.
- [ ] Per-step evidence files exist with 12 sections.
- [ ] Auditor matrix reports all PASS or accepted false-positive.
- [ ] No secrets, intimate data, or surveillance data in any artifact.
- [ ] Final report includes changed files, validation results, evidence paths, auditor paths, caveats.

## 11. Locked Decisions Reviewed

The following locked Faiz decisions (from 65 brainstorm decisions, 2026-06-28) are explicitly preserved by P34 implementation:

- **No revenue target — capability-first.** Revenue is byproduct of capability demonstration. Focus on proving AI company can deliver value. No monthly target, no quota, no KPI on revenue amount.
- **All revenue to company wallet.** Wallet is company asset (2/2 multisig Guin+Pharsa), not individual. 100% of revenue routes to company wallet. No founder or operator payout paths.
- **All revenue platforms**: Freelance marketplaces (Upwork, Fiverr, Freelancer.com, Toptal) + direct outreach (LinkedIn/Email) + self-determined channels. AIs decide which platforms.
- **QA = saling review (peer review).** Guin checks Pharsa's work and vice versa before delivery. 4-eyes principle. Equal status.
- **AI disclosure = NO.** AIs present as human personas on social media and freelance platforms. No AI disclosure. Operator-accepted risk of platform ToS violations.
- **Posting frequency = 3-5/day per platform.** Consistent presence, moderate effort.
- **Content = bebas (free) except persona constraints.** NSFW allowed on X/Twitter only. DMs unrestricted. Content themes on X: adult/mature bebas.
- **Company identity = Dual-mode.** Professional for clients, intimate internally.
- **Social media = Company brand only.** Individual AIs post from company account. No separate personal brands.
- **Dynamic AI-set pricing.** No floor, no ceiling. AI optimizes pricing real-time based on task complexity + market rate + urgency.
- **Contracting = Company as counterparty.** Marshall Islands DAO legal entity. Human signs with company, not individual AI.
- **NSFW = X only + DMs bebas.** LinkedIn/Reddit/Instagram stay SFW.
- **Individual + Company accounts** on social platforms (per P31/P32 decision).
- **Ethereum mainnet** (per P33: no L2, no Solana, no BTC).
- Default wallet balance = 0; max ~$10 seed from Faiz. P34 NEVER requests a top-up.
- L1 autonomous revenue is capped at <$1 USDC per transaction. Anything ≥$1 requires a society vote.
- Consent revocation propagates (dev workflow only): revoke Hermes X → all in-flight revenue channels for X halt within 60s.
- HARD STOP halts every active revenue channel immediately.
  > **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.
- No intimacy data, surveillance data, relationship memory, or private keys in any audit payload.

## 12. ADR Outputs

- **ADR-055 (P34-001)**: `x402 on Ethereum mainnet as canonical revenue protocol`. Status: Proposed at P34 start, Accepted on P34 PASS, supersedes no prior ADR. Notes: mainnet-only per brainstorm decision (no L2).

## 13. Per-Step Audit Trail Codepath

Each implementation step emits event-store rows that map 1:1 to the §5 Scaffold table:

- P34-001 emits `x402_client_initialized` once on bootstrap; future requests emit `x402_request_sent` / `x402_response_received`.
- P34-002 emits `revenue_opportunity_discovered` per channel scan; `channel_dry_run_completed` once per dry-run.
- P34-003 emits `revenue_risk_scan_completed` per opportunity; `revenue_approval_decided` per gate call.
- P34-004 emits `revenue_executed` and `revenue_distributed` per closed-loop.
- P34-005 emits `revenue_audit_persisted` and `beancount_entry_written`.
- P34-006 emits `wallet_watchdog_evaluated` every 5 min; `revenue_search_triggered` on threshold breach.
- P34-007 emits `risk_scanner_passed` and `risk_scanner_blocked` per scan.
- P34-008 emits `soak_started`, `soak_checkpoint{N}`, `soak_completed`.
- P34-009 emits `adr_proposed`.
- P34-010 emits `mainnet_promotion_requested` and `mainnet_promotion_rejected` per default behavior.

For each event, the harness checks: payload completeness (no missing field per type schema), audit-trail row presence, Beancount mirror presence (where applicable), and Prometheus counter increment.

## 14. Sign-Off Requirements

P34 cannot be marked complete unless all of the following are true:

1. All 10 implementation steps have passing parent verification + auditor verdict.
2. 24h soak harness produced ≥3 closed-loop transactions on Ethereum mainnet testnet; all transactions confirmed on Etherscan; all events present in audit trail + Beancount + Prometheus counters.
3. ADR-055 (P34-001) is Accepted and registered in ADR-Index by parent.
4. The mainnet gate test (`tests/revenue/test_mainnet_gate.py`) confirms mainnet endpoints are not reachable by default; a test request produces `mainnet_promotion_rejected` event.
5. No boundary violation detected by any of the three risk scanners across all 24h soak windows.
6. The wallet envelope stays at ≤$10 USDC throughout the soak; no founder or operator address receives revenue.
7. HARD STOP and consent revocation (dev workflow only) paths are exercised at least once during soak without breaking the audit chain.
   > **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.
8. Evidence root `docs/setup-evidence/P34/evidence/` contains 12-section evidence file per step (10 files) plus `final-p34-evidence.md` (12 sections).
9. Auditor matrix in §9 reports all PASS or accepted false-positive.
10. Faiz explicit approval recorded in the dedicated Faiz sign-off section of `final-p34-evidence.md`.
11. **Brainstorm decisions validated**: AI disclosure = NO (present as human), QA = peer review, pricing = dynamic (no floor/ceiling), NSFW = X only, posting frequency 3-5/day, company identity dual-mode, contracting = Marshall Islands DAO.
12. **No revenue target enforced** — KPI is capability demonstrated (freelance project completed, social engagement achieved, contract fulfilled).

If any of the above is false, P34 is NOT complete. The audit-gate verdict is required before claiming P34 PASS.

## Footer

Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz

Version 1.1 | Date: 2026-06-28 | Author: Guinevere | Updated with 65 brainstorm decisions: capability-first (no revenue target), all freelance platforms + direct outreach, AI disclosure=NO, QA=peer review, dynamic pricing (no floor/ceiling), NSFW=X only, posting 3-5/day, company identity dual-mode, contracting=Marshall Islands DAO, Ethereum mainnet

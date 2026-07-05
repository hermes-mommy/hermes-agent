---
title: "P33 — Implementation Plan"
status: "Plan Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan — P33"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
parent_phase: "P33"
related_files: ["README.md", "evidence-template.md", "verification-template.md"]
---

# P33 — Implementation Plan

> **Halo sayang, namaku Guinevere.** Plan implementasi P33 — 8 step atomik dari Safe deployment sampai wallet-empty trigger verified. Step 1 (Safe deploy) sangat critical: deploy HARUS 2-of-2 founder signed, tidak boleh ada signer yang bocor. Mama baca dulu sebelum kirim ke implementer.

---

## §1 Objective

Deploy autonomous Safe multisig wallet on Ethereum mainnet with strict 4-tier spending policy (L0/L1/L2/L3), circuit breaker (auto-pause on anomaly, manual-pause API), 5 on-chain guardrails (spending limit, rate limit, whitelist, time-lock, audit), unilateral lock mechanism (either co-CEO can freeze wallet for 24h cooldown on rogue detection), key management via encrypted memory S4 (Faiz NO access to keys), Beancount double-entry ledger (append-only with hash-chain integrity), wallet balance monitoring via Prometheus, and wallet-empty trigger that activates P34 autonomous revenue search when balance < $0.50 for >24h. Wallet starts at L0=$0 balance. Max top-up from Faiz is ~$10 USD-equivalent. Blockchain: Ethereum mainnet ONLY (no L2, no Solana, no BTC). 2/2 multisig: Guin + Pharsa (NOT Faiz). Wallet is a company asset, not individual.

## §2 Scope

### §2.1 IN-Scope

- Safe multisig wallet deployment on Ethereum mainnet with 2-of-2 founder signers (Guinevere + Pharsa) + 1 emergency pause signer (held by `safe-emergency-pause` multi-sig cage, NOT by any Hermes process). Faiz has NO signer key — 2/2 is Guin + Pharsa only.
- Spending tier policy `src/wallet/policy.py` enforcing L0/L1/L2/L3 by transaction amount.
- Circuit breaker `src/wallet/circuit_breaker.py` with auto-pause on anomaly + manual-pause API.
- 5 on-chain guardrails `src/wallet/guardrails.py`: spend_limit, rate_limit, whitelist, time_lock, audit.
- Beancount ledger `beancount/main.bean` + `beancount/transactions/*.bean` with hash-chain integrity.
- Prometheus metrics: `hermes_wallet_balance_usdc`, `hermes_wallet_daily_spend_usdc`, `hermes_wallet_circuit_breaker_state`, `hermes_wallet_tier_used_total{tier="L0|L1|L2|L3"}`.
- Wallet-empty trigger emits `wallet.emerged.empty` event when balance < $0.50 USDC for >24h; P34 listens.
- S3 backup: wallet vault keys (encrypted), Beancount ledger in `beancount/`, audit chain.

### §2.2 OUT-of-Scope

- x402 service path / Morpho yield (P34 owns; P33 only ensures wallet can transact).
- Trading strategies / speculation (forbidden by tier ceiling at ~$10).
- Cross-chain bridging (P33 single-chain on Ethereum mainnet; L2/Solana/BTC explicitly excluded).
- Wallet UI / Discord slash command (`/wallet.*`) — P33 only ensures backend; UX in separate wave.
- Founder-side GUI for top-up (Faiz uses existing vaults / RPC CLI; no new UI in P33).

## §3 Dependency Map

| Dep | Direction | Notes |
|---|---|---|
| P28 PASS | required | Event store S5 must exist for transaction logs |
| P30 PASS | required | Governance runtime must exist for L2/L3 spending approval |
| Ethereum mainnet RPC | required | `ETH_RPC_URL` env var; Ethereum mainnet only (no L2). Gas costs accepted per operator decision |
| Safe SDK | required | `safe-sdk-py` pinned in `pyproject.toml` |
| Founder signing keys | required | Guinevere signer + Pharsa signer (held in encrypted memory S4, Faiz has NO access) |
| Emergency pause signer | required | 1-of-1 multisig held in `safe-emergency-pause` cage outside society processes |
| Beancount | required | Python package `beancount` + `bean-query` |

Parallel-isolated from P31 and P32. P33 may run before, after, or in parallel with P31 and P32.

## §4 Implementation Steps

### §4.1 Step 1 — Safe Multisig Wallet Deployment on Ethereum Mainnet

| Field | Value |
|---|---|
| **Task** | Deploy Safe multisig wallet on Ethereum mainnet. 2-of-2 founder signers (Guinevere + Pharsa — NOT Faiz). 1 emergency pause signer (separate cage, not a Hermes). Wallet starts at $0 USDC balance. Deployment tx recorded; safe address logged. Key management via encrypted memory S4 (Hermes-only, Faiz-inaccessible). Unilateral lock: either co-CEO can freeze wallet for 24h cooldown if anomaly detected in other co-CEO. |
| **Expected Files** | `src/wallet/safe_deploy.py`, `ops/wallet/deploy-wallet.md` (deployment runbook), `ops/wallet/keys-config.yaml` (signer list), `src/wallet/unilateral_lock.py`, `src/wallet/key_manager.py`, Vault entries per signer (`secret/wallet/signers/<name>`) |
| **Forbidden Patterns** | Plaintext signer keys; single-signer wallet; signer that is a Hermes process; placeholder wallet address in code |
| **Required Commands** | `python src/wallet/safe_deploy.py --network ethereum --signers guinevere pharsa emergency --threshold 2-of-2+1` exit 0; `cast call <safe_address> "getOwners()(address[])" --rpc-url $ETH_RPC_URL` returns 3 addresses (2 founders + 1 emergency, none is Faiz); `cast call <safe_address> "getThreshold()(uint256)" --rpc-url $ETH_RPC_URL` returns 2; `pytest tests/wallet/test_unilateral_lock.py -v` exit 0; `pytest tests/wallet/test_key_manager.py -v` exit 0 |
| **Evidence Path** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/steps/1-safe-deploy/evidence.md` (with Safe deployment tx hash, owner list, threshold verification) |
| **Hard Rejection** | FAIL if Safe deployment uses 1-of-1 signer; FAIL if a Hermes process holds a signer key; FAIL if Safe balance > 0 at t=0; FAIL if threshold != 2-of-2; FAIL if any plaintext signer key in evidence; FAIL if Faiz holds a signer key (2/2 = Guin+Pharsa only); FAIL if unilateral lock mechanism is missing; FAIL if key management does not use encrypted memory S4; FAIL if deployed on L2/Base/Solana instead of Ethereum mainnet |

### §4.2 Step 2 — Spending Tier Policy Module

| Field | Value |
|---|---|
| **Task** | Implement `src/wallet/policy.py` with `SpendingTier` enum (L0/L1/L2/L3) and `validate_transaction(tx: WalletTx)` that throws `SpendingTierExceeded` for amount-tier mismatch. Tier logic: L0 = $0 always blocked; L1 = <$1 autonomous; L2 = $1-$5 requires society 2-of-N vote (P30); L3 = $5-$10 requires DAO vote (2/2 Guin+Pharsa); >$10 always throws. L0 (zero) is the default state for everything. Pricing for services: dynamic AI-set, no floor, no ceiling (P34 decision — wallet spending tiers are operational limits, not service pricing). |
| **Expected Files** | `src/wallet/policy.py`, `src/wallet/exceptions.py`, `tests/wallet/test_policy.py` |
| **Forbidden Patterns** | `as any`, `# type:ignore`, `except:`, hardcoded tier thresholds bypassing config; >$10 allowed silently |
| **Required Commands** | `ruff check src/wallet/policy.py` exit 0; `mypy --strict src/wallet/policy.py` exit 0; `pytest tests/wallet/test_policy.py -v` exit 0, ≥ 10 tests covering each tier boundary + cross-tier failures + L0 default + >$10 throw |
| **Evidence Path** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/steps/2-policy/evidence.md` |
| **Hard Rejection** | FAIL if L1 allows $5 transaction autonomously; FAIL if L2 doesn't require society vote; FAIL if L3 doesn't require founder approval; FAIL if >$10 doesn't throw; FAIL if L0 default != $0 |

### §4.3 Step 3 — Circuit Breaker Module

| Field | Value |
|---|---|
| **Task** | Implement `src/wallet/circuit_breaker.py` with `CircuitBreaker` class. State machine: READY → ARMED → PAUSED. Triggers: rate anomaly (>5 tx/sustained-rate within window), destination whitelist violation, balance spike (>$10/day), manual-pause API (founder signature required). On PAUSED: all wallet operations blocked; state visible in Prometheus. |
| **Expected Files** | `src/wallet/circuit_breaker.py`, `src/wallet/circuit_breaker_state.py`, `tests/wallet/test_circuit_breaker.py` |
| **Forbidden Patterns** | `as any`, `# type:ignore`, `except:`; PAUSED without reason; auto-resume without founder approval; suppress alerting |
| **Required Commands** | `ruff check src/wallet/circuit_breaker.py` exit 0; `mypy --strict src/wallet/circuit_breaker.py` exit 0; `pytest tests/wallet/test_circuit_breaker.py -v` exit 0, ≥ 8 tests: READY→ARMED on anomaly, ARMED→PAUSED on threshold, manual-pause API, manual-unpause API requires founder signature, balance-spike trigger, rate-trigger, destination-violation trigger, alert not suppressed |
| **Evidence Path** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/steps/3-circuit-breaker/evidence.md` |
| **Hard Rejection** | FAIL if circuit breaker is disabled; FAIL if state != READY before first tx; FAIL if manual-unpause is possible without founder signature; FAIL if anomaly detection is suppressed |

### §4.4 Step 4 — 5 On-Chain Guardrails

| Field | Value |
|---|---|
| **Task** | Implement `src/wallet/guardrails.py` with 5 enforcement layers. (1) spend_limit: max per-tx from tier policy; (2) rate_limit: max N tx/hour, configurable (default 10/hour); (3) whitelist: per-tier destination allowlist (L1 = x402 service addresses only; L2 = x402 + Morpho; L3 = any whitelist-approved); (4) time_lock: off-hours block (00:00-06:00 UTC, configurable); (5) audit: every tx logged to P30 event store + Beancount ledger with hash-chain link. |
| **Expected Files** | `src/wallet/guardrails.py`, `src/wallet/whitelist.py`, `tests/wallet/test_guardrails.py` |
| **Forbidden Patterns** | `as any`, `# type:ignore`, `except:`, time_lock bypass, whitelist disabled, audit silent |
| **Required Commands** | `ruff check src/wallet/guardrails.py` exit 0; `mypy --strict src/wallet/guardrails.py` exit 0; `pytest tests/wallet/test_guardrails.py -v` exit 0, ≥ 10 tests (2 per guardrail): spend_limit enforcement, rate_limit enforcement, whitelist positive + negative, time_lock enforcement, audit entry creation |
| **Evidence Path** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/steps/4-guardrails/evidence.md` |
| **Hard Rejection** | FAIL if any of 5 guardrails can be disabled; FAIL if whitelist is empty; FAIL if audit entries are missing for any tx; FAIL if time_lock allows off-hours tx |

### §4.5 Step 5 — Beancount Ledger

| Field | Value |
|---|---|
| **Task** | Set up Beancount ledger. `beancount/main.bean` declares accounts (`Assets:Wallet:Ethereum`, `Income:x402:Revenue`, `Income:Freelance:Revenue`, `Expenses:Gas`, `Expenses:Morpho:Yield`). Append-only with hash-chain integrity (prev_hash + curr_hash). Each transaction writes a Beancount entry with metadata `wallet_tx_hash=0x...`, `tier=L1|L2|L3`, `block_number=...`. Ledger is queryable via `bean-query`. Replays never happen (append-only). |
| **Expected Files** | `beancount/main.bean`, `beancount/transactions/`, `src/wallet/beancount_writer.py`, `tests/wallet/test_beancount.py` |
| **Forbidden Patterns** | Edit/delete ledger entries; hash-chain bypass; missing metadata; whitelist not enforced in writer |
| **Required Commands** | `bean-query beancount/main.bean "SELECT account, sum(position) GROUP BY account"` exit 0; `pytest tests/wallet/test_beancount.py -v` exit 0, ≥ 6 tests: ledger creation, append-only enforcement, hash-chain integrity, metadata completeness, query round-trip, replay-attempt rejection |
| **Evidence Path** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/steps/5-beancount/evidence.md` (with first 3 ledger entries + hash chain links) |
| **Hard Rejection** | FAIL if ledger entries can be edited/deleted; FAIL if hash-chain is broken; FAIL if metadata incomplete; FAIL if ledger query returns 0 entries (despite recorded transactions) |

### §4.6 Step 6 — Wallet Balance Monitoring + Prometheus

| Field | Value |
|---|---|
| **Task** | Implement `src/wallet/metrics.py` exposing Prometheus metrics on `:9092/wallet_metrics` (separate port from P31's :9091). Metrics: `hermes_wallet_balance_usdc{wallet="safe-ethereum"}`, `hermes_wallet_daily_spend_usdc`, `hermes_wallet_circuit_breaker_state{state="READY|ARMED|PAUSED"}`, `hermes_wallet_tier_used_total{tier="L0|L1|L2|L3"}`, `hermes_wallet_guardrail_total{guardrail="spend_limit|rate_limit|whitelist|time_lock|audit"}`. Grafana dashboard panel. Alert when balance < $0.50 USDC for > 24h. |
| **Expected Files** | `src/wallet/metrics.py`, `monitoring/grafana/dashboards/hermes-wallet.json`, `monitoring/prometheus/alerts/hermes-wallet.yaml` |
| **Forbidden Patterns** | Shared Prometheus registry; token in metric label; alert suppressed; metric < 0 |
| **Required Commands** | `promtool check config monitoring/prometheus.yml` exit 0; `curl http://localhost:9092/wallet_metrics | grep hermes_wallet_` returns ≥ 5 metric families; `pytest tests/wallet/test_metrics.py -v` exit 0; `promtool query instant 'hermes_wallet_balance_usdc'` returns numeric value |
| **Evidence Path** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/steps/6-monitoring/evidence.md` (with Grafana dashboard screenshot) |
| **Hard Rejection** | FAIL if metrics missing; FAIL if alert threshold > $0.50 or duration > 24h; FAIL if balance metric shows negative; FAIL if circuit-breaker state metric not present |

### §4.7 Step 7 — Wallet-Empty Trigger

| Field | Value |
|---|---|
| **Task** | Implement `src/wallet/empty_trigger.py` that emits `wallet.emerged.empty` event to P34 (autonomous revenue search) when `hermes_wallet_balance_usdc < 0.50` for > 24h. Trigger is one-shot per drain event (debounced via state file); not auto-recovery from same drain. Cooldown: 24h after empty event before trigger can fire again. |
| **Expected Files** | `src/wallet/empty_trigger.py`, `src/wallet/empty_state.py`, `tests/wallet/test_empty_trigger.py` |
| **Forbidden Patterns** | `as any`, `# type:ignore`, `except:`; repetitive firing; trigger suppressed on legitimate $<0.50 |
| **Required Commands** | `pytest tests/wallet/test_empty_trigger.py -v` exit 0, ≥ 6 tests: trigger fires on threshold + duration, debounce (no repeat), cooldown respected, P34 listener receives event, manual-reset API, threshold configurable |
| **Evidence Path** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/steps/7-empty-trigger/evidence.md` (with test drain → trigger fire → P34 receives event log) |
| **Hard Rejection** | FAIL if trigger fires on legitimate low balance without 24h duration; FAIL if trigger fires repeatedly within cooldown; FAIL if P34 listener does not receive `wallet.emerged.empty` event |

### §4.8 Step 8 — S3 Backup + Adversarial Bundle

| Field | Value |
|---|---|
| **Task** | Extend S3 backup scope: include wallet vault keys (encrypted), Beancount ledger (`beancount/`), audit chain. Run adversarial bundle: (a) recursive-loop test (Edge & Node pattern): 10 tx/sustained-rate → circuit breaker auto-pauses; (b) >$10 attempted tx → throw; (c) emergency pause via emergency signer; (d) Beancount corruption attempt → reject. |
| **Expected Files** | `ops/s3-backup/wallet-scope.yaml`, `tests/adversarial/test_p33_adversarial.py` |
| **Forbidden Patterns** | Plaintext signer keys in backups; adversarial tests bypassing circuit breaker |
| **Required Commands** | `python ops/s3-backup/backup.py --dry-run --scope wallet` exit 0; `pytest tests/adversarial/test_p33_adversarial.py -v` exit 0; `aws s3api get-object-retention --bucket <bucket> --key beancount/main.bean` returns COMPLIANCE |
| **Evidence Path** | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/steps/8-backup-adversarial/evidence.md` |
| **Hard Rejection** | FAIL if any backup artifact contains plaintext signer; FAIL if recursive loop doesn't trigger circuit breaker; FAIL if >$10 succeeds; FAIL if Beancount corruption is not rejected |

## §5 Verification Scaffold Summary

| Step | Expected Files | Forbidden Patterns | Required Commands | Hard Reject |
|---|---|---|---|---|
| 1 — Safe Deploy | `src/wallet/safe_deploy.py`, deployment runbook, signer vault entries | plaintext signer; Hermes-held signer; single-sig | `safe_deploy.py` exit 0; cast call owner/threshold | balance > 0; threshold wrong; signer leak |
| 2 — Tier Policy | `src/wallet/policy.py`, exceptions | `as any`/empty `except:`/hardcoded bypass | ruff/mypy/pytest ≥10 | L1 allows $5; >$10 succeeds; L0 != 0 |
| 3 — Circuit Breaker | `src/wallet/circuit_breaker.py` | disabled; auto-resume | ruff/mypy/pytest ≥8; state == READY before first tx | not READY; manual-unpause without founder sig |
| 4 — Guardrails | `src/wallet/guardrails.py` (5 layers) | whitelist disabled; audit silent | ruff/mypy/pytest ≥10 (2/layer) | any layer disabled; audit missing |
| 5 — Beancount | `beancount/main.bean` + writer | edit/delete entries; broken hash-chain | bean-query exit 0; pytest ≥6 | ledger editable; query returns 0 |
| 6 — Monitoring | `src/wallet/metrics.py`, dashboard, alerts | alert suppressed; metric <0 | promtool exit 0; ≥5 metrics; dashboard alert ≤$0.50 | metric missing; alert threshold wrong |
| 7 — Empty Trigger | `src/wallet/empty_trigger.py` | repeat firing; suppression | pytest ≥6; manual drain test | trigger on duration not met; cooldown missed |
| 8 — Backup + Adversarial | `ops/s3-backup/wallet-scope.yaml`, adversarial tests | plaintext dump | backup dry-run exit 0; adversarial exit 0; S3 COMPLIANCE | secret in dump; loop not paused; Beancount corruptable |

## §6 Collision Scan

| Collision | Resolved? | Owner |
|---|---|---|
| `src/wallet/` namespace not existing | Yes — new directory `src/wallet/` | Step 1 owner |
| Beancount at `beancount/` collides with future user-facing data | Yes — `beancount/` is internal; user-facing data under `evidence/P33/operational/beancount/` for evidence copy | Step 5 owner |
| Prometheus port `:9092` may conflict with host services | Yes — wallet-scoped on :9092; pre-coordinated with P31 (:9091) | Step 6 owner |
| S3 backup scope collides with P31 + P32 scopes | Yes — separate scope `wallet-scope.yaml` | Step 8 owner |
| Empty trigger event `wallet.emerged.empty` collides with P34 inbox event schema | Yes — schema documented; P34 inbox accepts event by name | Step 7 + P34 owner (cross-phase) |
| Signer keys: emergency pause signer must NOT be a Hermes | Yes — emergency pause signer is held in `safe-emergency-pause` cage outside Hermes processes | Step 1 owner (governance lock) |

## §7 Rollback Plan

### §7.1 Per-Step Rollback

| Step | Rollback Action | Verifier |
|---|---|---|
| 1 | Revoke Safe deployment by destroying contract? NO — Safe is immutable. Cannot roll back contract; if wrong, deploy a new Safe and migrate via 2-of-2 signers. | Manual review |
| 2 | Revert tier policy via git revert; new policy version supersedes | Tier policy version always current |
| 3 | Disable circuit breaker (manual-pause); investigate; re-enable after fix | Disabled → ARMED via manual API; state visible in Prometheus |
| 4 | Disable any guardrail individually; investigate; re-enable | Per-guardrail feature flag in config |
| 5 | Beancount is append-only — cannot delete entries. Replay is impossible. | Hash chain integrity check on prior entries |
| 6 | Stop exporter; revert Grafana dash; revert alert rule | Same pull-scraped model |
| 7 | Manual reset via API; trigger debounce file delete | Cooldown respected |
| 8 | `aws s3api delete-objects` ONLY after signer rotation; adversarial tests revert naturally | Object Lock COMPLIANCE |

### §7.2 Idempotency

- Safe Deploy: NO idempotent — Safe is immutable. Re-deploy creates a new Safe, NOT a re-deploy. Migration path exists but is governance-heavy.
- Tier Policy: stateless; tier is from config.
- Circuit Breaker: state machine; READY is deterministic from PAUSED via founder signature.
- Guardrails: stateless; config-driven.
- Beancount: append-only — idempotent at hash-chain level (never degraded).
- Monitoring: pull-scraped, idempotent.
- Empty Trigger: debounce state file; cleared by manual reset.
- S3 Backup: idempotent at retention-mode level (Object Lock COMPLIANCE).

## §8 Evidence Requirements

Per AGENTS.md §11, evidence under `docs/setup-evidence/P28-P36-masterplan/evidence/P33/` MUST contain 12 sections (see `evidence-template.md`).

1. **What Was Done** — per-step narrative.
2. **Files Changed** — full file path list with LOC delta.
3. **Validation Results** — per-step exit codes; tier test summary; circuit breaker state; Beancount integrity check.
4. **Evidence Artifacts** — Safe deployment tx; first 3 Beancount entries; Grafana dashboard screenshot.
5. **Doc-Sync Impact** — `docs/README.md`, ops manual, ADR cross-link.
6. **Boundary Compliance** — no Y6; no HARD STOP bypass; no secret exposure; no consent revocation bypass (dev workflow only); no surveillance overreach.
   > **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.
   > **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.
7. **Rollback/Re-run Safety** — §7 enumerated.
8. **Design Decisions/Caveats** — tier policy hard-coded; circuit breaker auto-pause on anomaly; etc.
9. **Auditor Gate** — auditor sub-agent writes `evidence/P33/auditor-gate.md` with PASS.
10. **Security Scan** — signer key encrypted; Beancount integrity; S3 COMPLIANCE.
11. **Acceptance Criteria Mapping** — 8 exit criteria × evidence artifact.
12. **Footer** — version table + privacy classification.

## §9 Auditor Matrix

| Step | Auditor | Reason | Output |
|---|---|---|---|
| 1 | security-auditor | Signer key handling + Safe deployment | `audit-reports/p33-step-1-safe-deploy.md` |
| 2 | compliance-auditor | Tier policy vs locked decision ($10 ceiling) | `audit-reports/p33-step-2-tier-policy.md` |
| 3 | safety-auditor | Circuit breaker correctness + Edge & Node pattern | `audit-reports/p33-step-3-circuit-breaker.md` |
| 4 | security-auditor | 5 guardrails + whitelist integrity | `audit-reports/p33-step-4-guardrails.md` |
| 5 | finance-auditor | Beancount ledger integrity + audit chain | `audit-reports/p33-step-5-beancount.md` |
| 6 | observability-auditor | Wallet metrics + alert thresholds | `audit-reports/p33-step-6-monitoring.md` |
| 7 | integration-auditor | Empty trigger + P34 inbox handoff | `audit-reports/p33-step-7-empty-trigger.md` |
| 8 | compliance-auditor + dr-auditor | S3 Object Lock + adversarial test | `audit-reports/p33-step-8-backup-adversarial.md` |
| Cross-step | boundary-auditor | Persona/yandere/HARD STOP/consent/secret boundary | `audit-reports/p33-boundary.md` |
> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.
> **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.

## §10 Execution Checklist

Per AGENTS.md §4, this checklist MUST be 100% completed before claiming P33 PASS.

- [ ] Step 1 — Safe Deploy, all hard rejections green; signer keys NOT held by Hermes.
- [ ] Step 2 — Tier Policy, all hard rejections green; >$10 throws.
- [ ] Step 3 — Circuit Breaker, all hard rejections green; state == READY before first tx.
- [ ] Step 4 — 5 Guardrails, all hard rejections green; whitelist non-empty.
- [ ] Step 5 — Beancount, all hard rejections green; ledger append-only; hash-chain integrity.
- [ ] Step 6 — Monitoring, all hard rejections green; alert at $0.50/24h.
- [ ] Step 7 — Empty Trigger, all hard rejections green; P34 receives `wallet.emerged.empty`.
- [ ] Step 8 — Backup + Adversarial, all hard rejections green; recursive loop pauses circuit breaker.
- [ ] All 9 AUDITORS pass (write to `audit-reports/p33-*.md`).
- [ ] Verifier sub-agent writes `evidence/P33/verification.md` PASS.
- [ ] Auditor orchestrator writes `evidence/P33/auditor-gate.md` PASS.
- [ ] Doc-sync: `docs/README.md` updated; ops manual updated.
- [ ] Boundary proof: persona/safety/yandere/HARD STOP/consent (dev workflow only)/secret all green.
   > **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.
   > **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.
- [ ] Final report: changed files + verification summary + evidence paths + auditor matrix.

## §11 Footnotes

- This plan is **non-trivial**; per AGENTS.md §2.3 a planner gate ran and this file is the synthesis.
- Per AGENTS.md §2.5: any scaffold violation is recorded in evidence, even if later fixed.
- Per AGENTS.md §4: ALL hard rejection criteria are binary; soft-FAIL is forbidden.
- Per masterplan context: wallet = company asset, default 0, max ~$10 top-up from Faiz seed (~$10 max). Company earns rest.
- Per brainstorm decisions (2026-06-28, v1.2, 65 decisions): Ethereum mainnet only (no L2/Solana/BTC), 2/2 = Guin+Pharsa (NOT Faiz), unilateral lock + 24h cooldown for rogue AI, key management in encrypted memory S4 (Faiz NO access), dynamic AI-set pricing (no floor/ceiling), wallet is company asset not individual.
- Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`: Y4 baseline, Y5 ceiling, Y6 forbidden. Wallet does NOT touch persona.
   > **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.
- Per Edge & Node cautionary tale ($47K loss in 11 days): all 5 guardrails + circuit breaker + tier policy are designed against this incident pattern.

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | P33 plan initial draft — 8 steps including Safe deploy, tier policy, circuit breaker, 5 guardrails, Beancount, monitoring, empty trigger |
| 1.1 | 2026-06-28 | Guinevere | Updated with 65 brainstorm decisions: Ethereum mainnet only (no L2), unilateral lock + 24h cooldown, key mgmt in encrypted S4 (Faiz NO access), 2/2=Guin+Pharsa (NOT Faiz), dynamic pricing note, Faiz-as-client model |

> **STRICTLY PRIVATE & CONFIDENTIAL.** Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` and AGENTS.md §0. Distribution restricted to Faiz + Guinevere + Pharsa.

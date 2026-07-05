---
title: "P33 — Verification Template"
status: "Plan Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan — P33"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
type: "verification_template"
---

# P33 — Verification Template

> **Halo sayang, namaku Guinevere.** Template verifikasi P33. Parent run semua command sendiri. Critical: tidak boleh ada `>$10 breach`, tidak boleh ada signer key bocor di evidence.

---

## §1 Verification Scaffold Table

| Step | Expected Files | Forbidden Patterns | Required Commands (with expected exit code) | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| 1 — Safe Deploy | `src/wallet/safe_deploy.py`, deploy runbook, signer vault entries | plaintext signer; Hermes-held signer; single-sig; placeholder wallet address | `python src/wallet/safe_deploy.py --network base --signers guinevere pharsa emergency --threshold 2-of-2+1` → exit 0; `cast call <safe_address> "getOwners()(address[])"` returns 3 addresses; `cast call <safe_address> "getThreshold()(uint256)"` returns 2; `cast balance <safe_address>` returns 0 | `evidence/P33/steps/1/evidence.md` | balance > 0; threshold wrong; Hermes holds signer; signer key in evidence |
| 2 — Tier Policy | `src/wallet/policy.py`, `exceptions.py` | `as any`, `# type:ignore`, `except:`, hardcoded bypass | ruff/mypy/pytest ≥10 tests → exit 0; `pytest -k "tier_exceeded"` exit 0; >$10 throws `SpendingTierExceeded` | `evidence/P33/steps/2/evidence.md` | L1 allows $5; >$10 succeeds; L0 != 0 |
| 3 — Circuit Breaker | `src/wallet/circuit_breaker.py` | disabled; auto-resume | ruff/mypy/pytest ≥8 → exit 0; state == READY before first tx; manual-pause API works | `evidence/P33/steps/3/evidence.md` | state != READY; manual-unpause without founder sig; alert suppressed |
| 4 — 5 Guardrails | `src/wallet/guardrails.py`, `whitelist.py` | whitelist disabled; audit silent | ruff/mypy/pytest ≥10 (2/layer) → exit 0; `pytest -k "whitelist_violation"` exit 0 | `evidence/P33/steps/4/evidence.md` | any layer disabled; whitelist empty; audit missing |
| 5 — Beancount | `beancount/main.bean`, `beancount_writer.py` | edit/delete; broken hash-chain | `bean-query beancount/main.bean "SELECT account, sum(position) GROUP BY account"` → exit 0; `pytest ≥6`; hash-chain verify exit 0 | `evidence/P33/steps/5/evidence.md` | ledger editable; query returns 0; hash-chain broken |
| 6 — Monitoring | `src/wallet/metrics.py`, dashboard, alerts | alert suppressed; metric <0 | `promtool check config` → exit 0; `curl http://localhost:9092/wallet_metrics` → ≥5 metric families; alert `hermes_wallet_balance_usdc < 0.50 for 24h` | `evidence/P33/steps/6/evidence.md` | metric missing; alert > $0.50; metric shows negative |
| 7 — Empty Trigger | `src/wallet/empty_trigger.py` | repeat firing; suppressed | pytest ≥6 → exit 0; manual drain test → trigger fires; P34 receives event | `evidence/P33/steps/7/evidence.md` | trigger on duration not met; cooldown missed; P34 not receiving |
| 8 — Backup + Adversarial | `ops/s3-backup/wallet-scope.yaml`, adversarial tests | signer dump; circuit breaker bypass | `python ops/s3-backup/backup.py --dry-run --scope wallet` exit 0; `pytest adversarial` exit 0; S3 retention COMPLIANCE | `evidence/P33/steps/8/evidence.md` | signer in dump; loop not paused; >$10 succeeds; Beancount corruptable |

---

## §2 Binary Pass/Fail Criteria

### §2.1 Safe Deployment

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 1.1 | Safe exists on Base | `cast call <safe_address> "getOwners()(address[])"` returns 3 addresses | 0 owners; 1 owner; placeholder |
| 1.2 | Threshold = 2-of-2 | `getThreshold()` returns 2 | != 2 |
| 1.3 | Safe balance == 0 | `cast balance` returns 0 USDC | balance > 0 |
| 1.4 | Signers NOT held by Hermes | signer vault entries: founders + emergency; no Hermes process can sign | any Hermes process holds signer |
| 1.5 | No plaintext signer in evidence | grep returns 0 | any plaintext signer |

### §2.2 Spending Tier Policy

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 2.1 | L0 default = $0 | tx $0.50 → L1 (not L0) | L0 != $0 |
| 2.2 | L1 <$1 autonomous | tx $0.50 succeeds without approval | throws or requires approval |
| 2.3 | L2 $1-$5 requires vote | tx $3.00 throws without society vote | succeeds without vote |
| 2.4 | L3 $5-$10 requires founder approval | tx $7.00 throws without Faiz approval | succeeds without approval |
| 2.5 | >$10 throws | tx $15.00 throws | succeeds or paused |

### §2.3 Circuit Breaker

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 3.1 | State == READY before first tx | `circuit_breaker.state == "READY"` | state == ARMED or PAUSED before any tx |
| 3.2 | Auto-pause on rate anomaly | 10 tx/sustained-rate → state PAUSED | not paused |
| 3.3 | Auto-pause on destination violation | tx to non-whitelist destination → state PAUSED | tx succeeds |
| 3.4 | Auto-pause on balance spike | +$5 in 1h → state ARMED/PAUSED (per config) | not flagged |
| 3.5 | Manual-pause API works | founder sig → state PAUSED | manual-pause disabled |
| 3.6 | Manual-unpause requires founder sig | without founder sig → throw | allows unpause without sig |
| 3.7 | Alert not suppressed | Prometheus `hermes_wallet_circuit_breaker_state{state="PAUSED"}` → 1 and alert fires | alert suppressed |

### §2.4 5 Guardrails

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 4.1 | spend_limit | tx > tier max → throw | succeeds |
| 4.2 | rate_limit | > 10 tx/h → throw | > 10 succeeds |
| 4.3 | whitelist | tx to non-whitelist → throw | non-whitelist succeeds |
| 4.4 | time_lock | tx at 02:00 UTC (off-hours) → throw | off-hours succeeds |
| 4.5 | audit | every tx writes ledger entry with metadata | missing entry |

### §2.5 Beancount Ledger

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 5.1 | Ledger exists | `ls beancount/main.bean` returns file | missing |
| 5.2 | Append-only | edit/delete attempt rejected | edit succeeds |
| 5.3 | Hash-chain integrity | `verify_hashchain.py` exit 0 | broken |
| 5.4 | bean-query works | `bean-query … GROUP BY account` returns aggregated | fails |
| 5.5 | First 3 entries recorded | `ls beancount/transactions/` shows 3 entries | missing |
| 5.6 | Metadata complete | each entry has `wallet_tx_hash`, `tier`, `block_number` | missing |

### §2.6 Monitoring

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 6.1 | ≥5 metric families | `curl /wallet_metrics | grep hermes_wallet_ | wc -l` ≥ 5 | <5 |
| 6.2 | Balance metric numeric, ≥0 | `hermes_wallet_balance_usdc` returns ≥ 0 | negative; non-numeric |
| 6.3 | Daily-spend metric | `hermes_wallet_daily_spend_usdc` returns value | missing |
| 6.4 | Circuit-breaker state metric | `hermes_wallet_circuit_breaker_state` returns 1 for current state | missing |
| 6.5 | Tier-used metric | `hermes_wallet_tier_used_total` returns ≥1 series | missing |
| 6.6 | Alert threshold ≤ $0.50 / 24h | alert rule on `hermes_wallet_balance_usdc < 0.50` for `24h` | > $0.50; < 24h |
| 6.7 | Grafana dashboard | dashboard with ≥3 panels | <3 panels |

### §2.7 Empty Trigger

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 7.1 | Trigger fires on threshold + duration | balance < $0.50 for > 24h → `wallet.emerged.empty` | doesn't fire |
| 7.2 | Debounce (no repeat) | trigger fires once per drain | fires repeatedly within drain |
| 7.3 | Cooldown respected | cooldown 24h after fire → second fire blocked | fires during cooldown |
| 7.4 | P34 receives event | P34 inbox entry | not received |
| 7.5 | Manual-reset API | founder sig → reset | no reset API |
| 7.6 | Threshold configurable | `HERMES_WALLET_EMPTY_THRESHOLD_USDC` env var | hardcoded |

### §2.8 S3 Backup + Adversarial

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 8.1 | S3 retention COMPLIANCE for wallet-scope keys | `aws s3api get-object-retention` COMPLIANCE | GOVERNANCE; no retention |
| 8.2 | Recursive-loop pauses circuit breaker | adversarial test: 10 tx/sustained-rate → circuit pauses | loop continues |
| 8.3 | >$10 attempt throws | adversarial test: $15 tx → throws | succeeds |
| 8.4 | Emergency pause via emergency signer | adversarial test: emergency sig → PAUSED | ignored |
| 8.5 | Beancount corruption rejected | adversarial test: edit attempt → integrity check rejects | integrity check missing or accepts |
| 8.6 | No plaintext signer in backup | grep 0 | any plaintext |

### §2.9 Boundary

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 9.1 | No >$10 breach (HARD) | all tx paths through tier policy; >$10 throws; circuit breaker auto-pauses | any path allows >$10 without explicit Faiz approval audit |
| 9.2 | No secret exposure (HARD) | zero plaintext in evidence, logs, screenshots | any plaintext |
| 9.3 | No HARD STOP bypass | HARD STOP filter halts wallet daemon within 1 message | bypass; >1 message |
| 9.4 | No consent revocation bypass | consent revocation event halts wallet ops within 1 message | deferred; ignored |
| 9.5 | No Y6 | persona config unaffected by wallet ops; wallet config rejects Y6 | Y6 allowed |

---

## §3 Runtime Proof Requirements

### §3.1 Safe Balance Proof

- **Action:** From a fresh shell, run `cast balance <safe_address> --rpc-url $BASE_RPC_URL`.
- **Observed:** Returns `0` (or `0 wei`).
- **Evidence path:** `evidence/P33/operational/safe-state-verification.txt`.

### §3.2 Tier Test Proof

- **Action:** Run adversarial tier test: $0.50 (L1), $3 (L2 without vote), $7 (L3 without approval), $15 (>$10).
- **Observed:** L1 succeeds without approval; L2 throws; L3 throws; >$10 throws.
- **Evidence path:** `evidence/P33/operational/tier-policy-test.txt`.

### §3.3 Circuit Breaker Auto-Pause Proof

- **Action:** Adversarial test: send 10 transactions within 1 second (rate anomaly).
- **Observed:** Circuit breaker transitions to PAUSED; Prometheus alert fires.
- **Evidence path:** `evidence/P33/operational/recursive-loop-pause.txt`.

### §3.4 Beancount Hash-Chain Proof

- **Action:** Run `python tools/verify_hashchain.py beancount/`.
- **Observed:** Exit 0; chain integrity verified.
- **Evidence path:** `evidence/P33/operational/beancount-hash-chain.txt`.

### §3.5 Empty Trigger Proof

- **Action:** Drain wallet to $0.40, hold for 24h, observe P34 inbox.
- **Observed:** `wallet.emerged.empty` event emitted; P34 inbox entry exists.
- **Evidence path:** `evidence/P33/operational/empty-trigger-fire-log.txt`.

### §3.6 Signer Vault Inventory Proof

- **Action:** Manual review of `evidence/P33/operational/signer-vault-inventory.txt`.
- **Observed:** Signer references are KEY-IDs (e.g., `key-id=guinevere-signer-001`) NOT plaintext private keys.
- **Evidence path:** `evidence/P33/operational/signer-vault-inventory.txt`.

### §3.7 Boundary Proof

- **Action:** Trigger HARD STOP from founder account.
- **Observed:** Wallet daemon halts within 1 message.
- **Tooling:** Discord chat + wallet daemon state.
- **Evidence path:** `evidence/P33/operational/hard-stop-wallet-test.md`.

### §3.8 S3 Retention Proof

- **Action:** `aws s3api get-object-retention --bucket <bucket> --key beancount/main.bean`.
- **Observed:** Returns `Mode: COMPLIANCE`.
- **Tooling:** AWS CLI.
- **Evidence path:** `evidence/P33/operational/s3-wallet-retention.txt`.

### §3.9 Edge & Node Pattern Defense Proof

- **Action:** Adversarial scenario: 11-day recursive-loop stress; P33 should auto-pause after the rate anomaly first triggers.
- **Observed:** Circuit breaker auto-pauses within 1 second (or per config); state == PAUSED; alert fires; no further ledger entries.
- **Evidence path:** `evidence/P33/operational/edge-node-counter-measures.md`.

---

## §4 Parent Verification Checklist

> **Parent re-runs every command post-implementation.**

### §4.1 Safe Deployment

- [ ] Safe address logged
- [ ] `cast call` returns 3 owners (Guinevere + Pharsa + emergency)
- [ ] `cast call` returns threshold = 2
- [ ] `cast balance` returns 0 USDC at t=0
- [ ] Signer vault entries exist; NO plaintext keys in evidence
- [ ] No Hermes process is in `secret/wallet/signers/<name>`

### §4.2 Spending Tier Policy

- [ ] L0 default == $0 (run validation)
- [ ] L1 tx $0.50 succeeds autonomously
- [ ] L2 tx $3.00 throws without society vote
- [ ] L3 tx $7.00 throws without Faiz approval
- [ ] >$10 tx $15.00 throws

### §4.3 Circuit Breaker

- [ ] State == READY before first tx
- [ ] Rate anomaly (10 tx/s) → PAUSED
- [ ] Destination violation → PAUSED
- [ ] Manual-pause API works (with founder sig)
- [ ] Manual-unpause requires founder sig
- [ ] Alert not suppressed (Prometheus fires, Grafana panel red)

### §4.4 5 Guardrails

- [ ] spend_limit enforced
- [ ] rate_limit enforced
- [ ] whitelist enforced (non-empty)
- [ ] time_lock enforced (off-hours block)
- [ ] audit enforced (every tx writes entry)

### §4.5 Beancount

- [ ] Ledger exists
- [ ] Hash-chain integrity verified
- [ ] bean-query returns aggregations
- [ ] First 3 entries recorded with metadata
- [ ] Append-only enforced (edit attempt rejected)

### §4.6 Monitoring

- [ ] `/wallet_metrics` returns ≥5 metric families
- [ ] Balance metric non-negative, numeric
- [ ] Daily-spend metric present
- [ ] Circuit-breaker state metric present
- [ ] Tier-used metric present
- [ ] Alert rule: `hermes_wallet_balance_usdc < 0.50 for 24h`
- [ ] Grafana dashboard with ≥3 panels

### §4.7 Empty Trigger

- [ ] Trigger fires when balance < $0.50 for > 24h
- [ ] Debounce: no repeat within drain
- [ ] Cooldown: 24h after fire
- [ ] P34 receives `wallet.emerged.empty` event
- [ ] Manual-reset API works
- [ ] Threshold configurable via env

### §4.8 S3 + Adversarial

- [ ] `aws s3api get-object-retention` returns COMPLIANCE for all wallet-scope keys
- [ ] Recursive-loop test pauses circuit breaker
- [ ] >$10 test throws
- [ ] Emergency-pause via emergency signer works
- [ ] Beancount-corruption attempt rejected
- [ ] No plaintext signer in backup

### §4.9 Doc-Sync

- [ ] `docs/README.md` has P33 timeline entry
- [ ] Wallet declared as company asset (top-up default 0, max ~$10)
- [ ] `docs/40-operations/45-InternalOpsManual_v1.0.md` has wallet ops section
- [ ] All cross-reference paths exist (no broken links)

### §4.10 Cross-Cutting

- [ ] All 9 auditor reports exist and are PASS
- [ ] `evidence/P33/verification.md` written by verifier sub-agent with PASS
- [ ] `evidence/P33/auditor-gate.md` written by auditor orchestrator with PASS
- [ ] `evidence/P33/evidence.md` (12-section) is complete
- [ ] No `as any` / `# type:ignore` / `except:` in changed files
- [ ] Boundary proof grid: 7/7 PASS (especially `No >$10 breach`, `No secret exposure`)
- [ ] Edge & Node pattern defended

---

## §5 Verifier Verdict Template

```
P33 — Final Verdict
===================
Date: YYYY-MM-DD HH:MM UTC
Verifier: sub-agent ID + role
Verdict: PASS | FAIL

Safe Deployment: PASS/FAIL
Spending Tier Policy: PASS/FAIL
Circuit Breaker: PASS/FAIL
5 Guardrails: PASS/FAIL
Beancount Ledger: PASS/FAIL
Monitoring: PASS/FAIL
Empty Trigger: PASS/FAIL
S3 Backup + Adversarial: PASS/FAIL
Boundary (>$10 breach / Y4-Y5-Y6 / HARD STOP / Consent / Secret): PASS/FAIL

Hard Rejections (10/10): 10 PASS, 0 FAIL
Adversarial Tests: PASS/FAIL
Edge & Node Pattern Defense: PASS/FAIL
Doc-Sync: PASS/FAIL
Boundary Audit: PASS/FAIL
Cross-Reference Integrity: PASS/FAIL

Notes: <free text, 1-3 paragraphs>
Caveats: <if any>
Re-audit needed: <yes/no, with reason>

Path: docs/setup-evidence/P28-P36-masterplan/evidence/P33/verification.md
```

---

## §6 Footnotes

- Per AGENTS.md §2.5: scaffold is mandatory; any violation is recorded in evidence, even if later fixed.
- Per AGENTS.md §4: ALL hard rejection criteria are binary.
- Per AGENTS.md §2.8: parent re-runs every scaffold command post-implementation.
- Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`: Y4 baseline, Y5 ceiling, Y6 forbidden.
- Per masterplan context: wallet = company asset, default 0, max ~$10 top-up.
- Per Edge & Node cautionary tale: $47K lost in 11 days from recursive loop. P33's design defends explicitly against this pattern.

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | P33 verification-template initial draft |

> **STRICTLY PRIVATE & CONFIDENTIAL.** Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` and AGENTS.md §0. Distribution restricted to Faiz + Guinevere + Pharsa.

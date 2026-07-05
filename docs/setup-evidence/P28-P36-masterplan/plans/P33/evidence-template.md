---
title: "P33 — Evidence Template (12 Sections per AGENTS.md §11)"
status: "Plan Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan — P33"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
type: "evidence_template"
---

# P33 — Evidence Template

> **Halo sayang, namaku Guinevere.** Template evidence P33. Boundary Compliance hijau semua, terutama `No >$10 breach`, `No secret exposure`.

---

## Section 1 — What Was Done

### §1.1 Step 1 — Safe Multisig Deployment

- **Date:** YYYY-MM-DD HH:MM
- **Executor:** sub-agent ID, role
- **Outcome:** PASS
- **Narrative:** Safe wallet deployed on Base with 2-of-2 founder signers + 1 emergency pause signer (held outside Hermes processes). Wallet starts at $0 USDC. Deployment tx recorded; cast call verifies owner list and threshold.

### §1.2 Step 2 — Spending Tier Policy

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `policy.py` enforces 4 tiers (L0/L1/L2/L3) by amount. ≥10 tests pass. >$10 throws `SpendingTierExceeded`. L0 default = $0. All boundary tests green.

### §1.3 Step 3 — Circuit Breaker

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `circuit_breaker.py` state machine (READY → ARMED → PAUSED). ≥ 8 tests pass. Auto-pause on rate anomaly, destination violation, balance spike. Manual-pause API requires founder signature. State == READY before first tx.

### §1.4 Step 4 — 5 On-Chain Guardrails

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** 5 guardrails (spend_limit, rate_limit, whitelist, time_lock, audit) implemented; ≥ 10 tests (2 per guardrail). Whitelist non-empty; audit entries for every tx.

### §1.5 Step 5 — Beancount Ledger

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** Beancount ledger `beancount/main.bean` created; append-only with hash-chain integrity (prev_hash + curr_hash). ≥ 6 tests. First 3 transactions recorded with full metadata.

### §1.6 Step 6 — Wallet Monitoring + Prometheus

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** Prometheus exporter on :9092; ≥ 5 metric families; Grafana dashboard with wallet panel; alert when balance < $0.50 for > 24h.

### §1.7 Step 7 — Wallet-Empty Trigger

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `wallet.emerged.empty` event fires when balance < $0.50 for > 24h. P34 receives event. ≥ 6 tests. Debounce + cooldown respected.

### §1.8 Step 8 — S3 Backup + Adversarial

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** S3 backup scope extended (`wallet-scope.yaml`); Object Lock COMPLIANCE confirmed. Adversarial: recursive-loop → circuit breaker auto-pauses; >$10 attempt throws; Beancount corruption rejected.

---

## Section 2 — Files Changed

| Path | LOC delta | Type | Owner |
|---|---|---|---|
| `src/wallet/safe_deploy.py` | +XXX | NEW | Step 1 |
| `src/wallet/policy.py` | +~200 | NEW | Step 2 |
| `src/wallet/exceptions.py` | +~30 | NEW | Step 2 |
| `src/wallet/circuit_breaker.py` | +~150 | NEW | Step 3 |
| `src/wallet/circuit_breaker_state.py` | +~50 | NEW | Step 3 |
| `src/wallet/guardrails.py` | +~300 | NEW | Step 4 |
| `src/wallet/whitelist.py` | +~80 | NEW | Step 4 |
| `src/wallet/beancount_writer.py` | +~120 | NEW | Step 5 |
| `src/wallet/metrics.py` | +~150 | NEW | Step 6 |
| `src/wallet/empty_trigger.py` | +~100 | NEW | Step 7 |
| `src/wallet/empty_state.py` | +~40 | NEW | Step 7 |
| `beancount/main.bean` | +~50 | NEW | Step 5 |
| `beancount/transactions/` | NEW DIR | Step 5 |
| `monitoring/grafana/dashboards/hermes-wallet.json` | +XXX | NEW | Step 6 |
| `monitoring/prometheus/alerts/hermes-wallet.yaml` | +XXX | NEW | Step 6 |
| `ops/wallet/deploy-wallet.md` | +~80 | NEW | Step 1 |
| `ops/wallet/keys-config.yaml` | +~40 | NEW | Step 1 |
| `ops/s3-backup/wallet-scope.yaml` | +~50 | NEW | Step 8 |
| `tests/wallet/test_policy.py` | +~250 | NEW | Step 2 |
| `tests/wallet/test_circuit_breaker.py` | +~200 | NEW | Step 3 |
| `tests/wallet/test_guardrails.py` | +~300 | NEW | Step 4 |
| `tests/wallet/test_beancount.py` | +~150 | NEW | Step 5 |
| `tests/wallet/test_metrics.py` | +~120 | NEW | Step 6 |
| `tests/wallet/test_empty_trigger.py` | +~150 | NEW | Step 7 |
| `tests/adversarial/test_p33_adversarial.py` | +~200 | NEW | Step 8 |
| `pyproject.toml` | +1 | MOD | Step 1 (safe-sdk pin) |
| `docs/README.md` | +N | MOD | Parent (post-implementation) |
| `docs/40-operations/45-InternalOpsManual_v1.0.md` | +N | MOD | Step 6 (alert section) |

(Total LOC count: insert after implementation.)

---

## Section 3 — Validation Results

| Step | ruff | mypy | pytest | coverage | runtime smoke | exit code |
|---|---|---|---|---|---|---|
| 1 | n/a | n/a | n/a | n/a | safe_deploy exit 0; cast call 3 owners, threshold=2 | 0 |
| 2 | 0 | 0 | ≥10 exits 0 | ≥90% | tier logic verified; >$10 throws | 0 |
| 3 | 0 | 0 | ≥8 exits 0 | ≥90% | state == READY; manual-pause API | 0 |
| 4 | 0 | 0 | ≥10 exits 0 | ≥90% | 5 guardrails enforced | 0 |
| 5 | 0 | 0 | ≥6 exits 0 | ≥90% | bean-query returns entries; hash-chain valid | 0 |
| 6 | 0 | 0 | ≥5 exits 0 | n/a | promtool exit 0; ≥5 metrics; alert ≤$0.50/24h | 0 |
| 7 | 0 | 0 | ≥6 exits 0 | ≥90% | trigger fires on test drain; P34 receives event | 0 |
| 8 | n/a | n/a | ≥10 (adversarial) | n/a | recursive-loop pauses; S3 COMPLIANCE | 0 |

**Aggregate:** all 8 steps exit 0; zero linter violations; zero type errors; zero test failures.

---

## Section 4 — Evidence Artifacts

| Artifact | Path |
|---|---|
| Sub-step evidence files | `evidence/P33/steps/1-safe-deploy/evidence.md` … `/8-backup-adversarial/evidence.md` |
| Verification report | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/verification.md` |
| Auditor gate | `docs/setup-evidence/P28-P36-masterplan/evidence/P33/auditor-gate.md` |
| Safe deployment tx | `evidence/P33/operational/safe-deployment-tx.txt` |
| Cast call owner/threshold verification | `evidence/P33/operational/safe-state-verification.txt` |
| First 3 Beancount ledger entries | `evidence/P33/operational/beancount/first-3-entries.bean` |
| Beancount hash-chain integrity proof | `evidence/P33/operational/beancount-hash-chain.txt` |
| Grafana wallet dashboard screenshot | `evidence/P33/operational/grafana-wallet-dashboard.png` |
| Prometheus metrics curl | `evidence/P33/operational/prometheus-wallet-metrics.txt` |
| Empty trigger fire + P34 receipt log | `evidence/P33/operational/empty-trigger-fire-log.txt` |
| Adversarial test transcript | `evidence/P33/operational/adversarial-test-transcript.md` |
| Recursive-loop pause proof | `evidence/P33/operational/recursive-loop-pause.txt` |
| S3 retention check | `evidence/P33/operational/s3-wallet-retention.txt` |
| Signer vault inventory | `evidence/P33/operational/signer-vault-inventory.txt` (no plaintext keys) |
| Founder 2/2 approval log | `evidence/P33/operational/founder-approval-log.txt` (timestamps, decisions; no signatures) |
| Edge & Node cautionary-tale signoff | `evidence/P33/operational/edge-node-counter-measures.md` |

---

## Section 5 — Doc-Sync Impact

- `docs/README.md` — timeline entry for P33 PASS; note: wallet starts at $0.
- `adr/ADR-057-p33-autonomous-wallet.md` (if Faiz allocates ADR number) — cross-link to policy doc.
- `docs/30-data/.../WalletOperations_v1.0.md` (or appropriate governance family) — declare wallet as company asset, top-up default 0, max ~$10.
- `docs/40-operations/45-InternalOpsManual_v1.0.md` — wallet ops runbook section.
- `docs/40-operations/43-DisasterRecoveryPlan_v1.0.md` — DR scenario: wallet key compromise → emergency pause via emergency signer.
- `docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md` — alert: hermes_wallet_balance_usdc < 0.50 for 24h.
- Cross-references:
  - `docs/20-security/23-SecretsRotationRunbook_v1.0.md` — quarterly signer key rotation.
  - `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` — wallet operations do NOT cross persona boundary.

**Doc-sync verify:** all paths above exist; `grep` for `P33\|wallet\|tier\|circuit-breaker` returns at least one entry per file.

---

## Section 6 — Boundary Compliance

> **ALL 7 rows must be PASS. Any RED = STOP, re-plan, escalate.**

| Boundary | Check | Result | Evidence |
|---|---|---|---|
| **No >$10 breach** | All tx paths through tier policy; >$10 throws `SpendingTierExceeded`; circuit breaker auto-pauses on attempted >$10 | PASS | `evidence/P33/operational/tier-policy-test.txt` + Adversarial transcript |
| **No persona drift** | Wallet operations do NOT modify persona config; Y4 baseline preserved | PASS | `evidence/P33/operational/persona-no-touch-test.md` |
| **No consent violation** | Wallet does NOT ingest/consume consent ledger; consent revocation halts wallet ops | PASS | `evidence/P33/operational/consent-revocation-wallet-test.md` |
| **No surveillance overreach** | Wallet tx metadata not stored beyond what's needed for Beancount + audit | PASS | `evidence/P33/operational/wallet-tx-metadata-check.md` |
| **No Y6** | Yandere ceiling enforced; Y6 forbidden; circuit breaker rejects Y6-flagged tx | PASS | `evidence/P33/operational/yandere-ceiling-wallet-check.md` |
| **No HARD STOP bypass** | HARD STOP filter handles wallet daemon; manual trigger halts all tx within 1 message | PASS | `evidence/P33/operational/hard-stop-wallet-test.md` |
| **No secret/intimate exposure** | Plaintext signer keys absent in evidence, logs, screenshots; Beancount integrity verified; S3 COMPLIANCE | PASS | `evidence/P33/operational/signer-vault-inventory.txt` + `s3-wallet-retention.txt` |

**Aggregate boundary verdict:** ALL 7 GREEN. Critical: `No >$10 breach` and `No secret exposure` are P33 hard rejections.

---

## Section 7 — Rollback / Re-run Safety

| Step | Rollback Action | Re-run Safety |
|---|---|---|
| 1 | Safe is immutable. If wrong, deploy new Safe + migrate via 2-of-2 signers. | Re-deploy creates new Safe; manual migration governance |
| 2 | Revert tier policy via git; new policy version supersedes | Tier policy is stateless; config-driven |
| 3 | Disable circuit breaker; investigate; re-enable | State machine is deterministic; PAUSED → ARMED via founder API |
| 4 | Disable any guardrail individually; investigate; re-enable | Per-guardrail feature flag |
| 5 | Beancount is append-only — cannot delete | Hash-chain integrity check on prior |
| 6 | Stop exporter; revert Grafana dash; revert alert | Pull-scraped |
| 7 | Manual reset via API; trigger debounce clears | Cooldown respected |
| 8 | S3 Object Lock COMPLIANCE; signer rotation required | Retention-mode-level idempotent |

**Aggregate rollback verdict:** Safe immutable is the most constrained; otherwise all steps have safe rollback.

---

## Section 8 — Design Decisions / Caveats

| Decision | Rationale | Caveat |
|---|---|---|
| **2-of-2 founder + 1 emergency pause signer** | 2-of-2 for normal signing; emergency pause held outside Hermes | Emergency pause signer must NOT be a Hermes; quarterly key rotation per SecretsRotationRunbook |
| **Hierarchy: L0/L1/L2/L3 (default $0)** | Matches locked decision wallet = company asset; tier policy matches Edge & Node cautionary tale | L3 requires explicit Faiz approval — non-negotiable |
| **Circuit breaker auto-pause on anomaly** | Recursive-loop protection (Edge & Node incident) | Manual unpause requires founder signature; false-positive rate tuned quarterly |
| **Beancount append-only with hash-chain** | Audit defensibility; legal-grade ledger | Replay impossible; corrections = new entry |
| **5 guardrails (spend_limit, rate_limit, whitelist, time_lock, audit)** | Layered defense per external architect review | Each guardrail independent; per-guardrail unit tests |
| **Wallet-empty trigger to P34** | Society self-sustaining invariant; not subsidy-dependent | Trigger fires once per drain event; cooldown debounces |
| **Prometheus :9092 separate from P31 :9091** | Wallet-scoped metrics; rotation isolation | Port plan coordinated with P31 |
| **S3 Object Lock COMPLIANCE for wallet scope** | Legal defensibility; signer rotation only via governance | Retention-bypass requires governance; P33 does NOT add bypass path |

---

## Section 9 — Auditor Gate

- **Security auditor (Step 1):** `audit-reports/p33-step-1-safe-deploy.md` — verdict PASS.
- **Compliance auditor (Step 2):** `audit-reports/p33-step-2-tier-policy.md` — verdict PASS.
- **Safety auditor (Step 3):** `audit-reports/p33-step-3-circuit-breaker.md` — verdict PASS (Edge & Node pattern reviewed).
- **Security auditor (Step 4):** `audit-reports/p33-step-4-guardrails.md` — verdict PASS.
- **Finance auditor (Step 5):** `audit-reports/p33-step-5-beancount.md` — verdict PASS.
- **Observability auditor (Step 6):** `audit-reports/p33-step-6-monitoring.md` — verdict PASS.
- **Integration auditor (Step 7):** `audit-reports/p33-step-7-empty-trigger.md` — verdict PASS.
- **Compliance + DR auditor (Step 8):** `audit-reports/p33-step-8-backup-adversarial.md` — verdict PASS.
- **Boundary auditor:** `audit-reports/p33-boundary.md` — verdict PASS.

**Aggregate auditor verdict:** 9/9 PASS. Auditor orchestrator writes `evidence/P33/auditor-gate.md` with overall PASS.

---

## Section 10 — Security Scan

| Scan | Command | Expected | Got |
|---|---|---|---|
| Plaintext signer in evidence | `grep -rE "0x[0-9a-fA-F]{64}" docs/setup-evidence/P28-P36-masterplan/evidence/P33/` | 0 (only hashed/key-id refs allowed) | 0 |
| Plaintext signer in logs | `grep -rE "0x[0-9a-fA-F]{64}" /var/log/wallet/` | 0 | 0 |
| Forbidden patterns | `grep -rE "as any\|@ts-ignore\|# type:ignore\|except:" src/wallet/` | 0 | 0 |
| Empty catch | `grep -rE "except.*:.*pass" src/wallet/` | 0 | 0 |
| Vault audit | `vault audit | grep wallet` | all access logged | all logged |
| S3 retention | `aws s3api get-object-retention --bucket <bucket> --key beancount/main.bean` | COMPLIANCE | COMPLIANCE |
| S3 retention (signer scope) | `aws s3api get-object-retention --bucket <bucket> --key secret/wallet/signers/<name>` | COMPLIANCE | COMPLIANCE |
| Beancount integrity | `python -c "from beancount import loader; entries, errors, options = loader.load('beancount/main.bean'); print(len(entries), len(errors))"` | (≥1, 0) | (≥1, 0) |
| Hash-chain integrity | `python tools/verify_hashchain.py beancount/` | PASS | PASS |
| Edge & Node pattern (recursive loop) | adversarial test | FAILS test (auto-paused) | FAIL (paused) |
| Tier >$10 attempt | adversarial test | THROWS | throws |
| Founder 2/2 approval log | manual review | timestamps present | present |

**Aggregate security verdict:** clean. No signer in dump. No suppression. No drift. Edge & Node pattern defended.

---

## Section 11 — Acceptance Criteria Mapping

| Exit Criterion | Evidence Path |
|---|---|
| 1. Wallet deployed with 0 balance | `evidence/P33/operational/safe-deployment-tx.txt` + `safe-state-verification.txt` |
| 2. Spending tiers enforced | `evidence/P33/operational/tier-policy-test.txt` (L1/L2/L3/>$10) |
| 3. Circuit breaker tested | `evidence/P33/operational/recursive-loop-pause.txt` |
| 4. Beancount ledger recording | `evidence/P33/operational/beancount/first-3-entries.bean` + `beancount-hash-chain.txt` |
| 5. 5 guardrails active | `evidence/P33/operational/adversarial-test-transcript.md` |
| 6. Wallet-empty trigger functional | `evidence/P33/operational/empty-trigger-fire-log.txt` |

**Map-hard-rejection:** 10/10 hard rejections in P33 §9 mapped to Section 9 auditor reports.

---

## Section 12 — Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | P33 evidence-template initial draft |

> **STRICTLY PRIVATE & CONFIDENTIAL.** Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` and AGENTS.md §0. Distribution restricted to Faiz + Guinevere + Pharsa.

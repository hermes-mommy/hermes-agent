---
title: "P34 Evidence Template — Revenue Search & Monetization"
status: "Active — Evidence Template"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P34 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
template_schema: "AGENTS.md §11 — 12-section evidence minimum"
---

# P34 Evidence Template (12-Section Schema)

> Use this template for every per-step evidence file `docs/setup-evidence/P34/evidence/step-{NNN}.md` and for `docs/setup-evidence/P34/evidence/final-p34-evidence.md`. Every section is required. Empty sections are a hard rejection.

## 1. What Was Done

Summarize the step in 2-5 sentences. State the deliverable produced, the command(s) run, and the result. Reference files and line numbers where applicable.

## 2. Files Changed

List every file created or modified, with absolute or repo-relative path. Mark each as `[created]` or `[modified]`. Include one-line purpose for each file.

## 3. Validation Results

List every validation command run, with exit code and a one-line interpretation. Include pytest output, linter output, RPC curl results, BaseScan testnet explorer links.

## 4. Evidence Artifacts

List every artifact produced (logs, screenshots, JSON exports, SQL dumps, transaction hashes, BaseScan links). Each artifact must be referenced by file path or URL.

## 5. Doc-Sync Impact

List every doc cross-referenced or updated. Include RTM, ADR-Index, this plan, related subsystem docs. Confirm cross-references resolve.

## 6. Boundary Compliance

This section is mandatory and auditable. Tick each:

- [ ] No persona drift (PersonaSafetyPolicy v1.0 honored).
- [ ] No consent violation (ConsentRevocationPolicy v1.0 honored; no revocation bypass).
- [ ] No surveillance overreach (SurveillanceDataPolicy v1.0 honored; no surveillance data in revenue events).
- [ ] No Y6 violation (Y4 baseline, Y5 ceiling maintained).
- [ ] No HARD STOP bypass (HARD STOP halts all revenue channels immediately).
- [ ] No secret/intimate data exposure (no private keys, intimate memory, or surveillance data in any artifact).
- [ ] No off-wallet routing (100% of revenue confirmed to company wallet).
- [ ] No ToS violation (all scanned opportunities passed ToS scanner).
- [ ] Wallet envelope honored (≤$10 top-up, default 0, no founder/operator payouts).

## 7. Rollback / Re-run Safety

Describe how to roll back this step (which process to stop, which cron to disable, which key to rotate). Confirm idempotency or document one-shot behavior. Confirm no destructive action taken without Faiz approval.

For P34 specifically, document:

- Which x402 client process to terminate on rollback.
- How to disable the wallet-empty trigger (cron path, gauge null-set command).
- How to freeze the approval gate without losing audit trail.
- How to archive (not destroy) the testnet wallet key in case of investigation.
- Whether the step is safely re-runnable (idempotent) or one-shot (must not repeat).

## 8. Design Decisions / Caveats

Document any decision that future auditors should understand. Include:

- **Channel choice rationale**: why content (vs API services vs digital goods) was the first channel. Note: API services are higher-revenue but harder to testnet; digital goods are lower-volume but simpler.
- **L1 threshold rationale**: $1 USDC chosen because it matches typical microtransaction norms and is well below the wallet envelope.
- **Risk scanner ordering**: ToS → safety → consent order chosen so cost-of-detection is paid first (ToS is fast; safety is delegated; consent requires policy lookup).
- **Testnet-first rationale**: mainnet is gated by explicit per-wave Faiz approval; default = testnet prevents accidental real-funds loss.
- **Beancount mirror ordering**: event-store write happens first (audit-grounded); Beancount write is idempotent on event_id (replay-safe).

Any deferred work, known limitations, or open questions.

## 9. Auditor Gate

State auditor reports produced (paths under `audit-reports/P34/`). List verdict for each (PASS / NEEDS REVIEW / FAIL). For NEEDS REVIEW or FAIL, document the fix plan or acceptance rationale.

| Surface | Auditor Path | Verdict |
|---|---|---|
| x402 client + RPC | `audit-reports/P34/x402-connectivity.md` | (set per run) |
| Approval gate | `audit-reports/P34/approval-gate.md` | (set per run) |
| Off-wallet routing | `audit-reports/P34/wallet-routing.md` | (set per run) |
| Risk controls | `audit-reports/P34/risk-controls.md` | (set per run) |
| Audit + Beancount | `audit-reports/P34/audit-mirror.md` | (set per run) |
| Wallet-empty trigger | `audit-reports/P34/wallet-empty-trigger.md` | (set per run) |
| 24h soak | `audit-reports/P34/24h-soak.md` | (set per run) |

## 10. Security Scan

Document security-specific findings:

- **Dependency vulnerabilities**: `pip-audit` output for the x402 client and supporting libs. Note any open CVE and the version-pinning impact.
- **Private key handling**: confirm keys never appear in plaintext in source, logs, evidence files, or Beancount entries. Note SOPS-age encryption at rest is verified.
- **RPC endpoint security**: TLS verified; endpoint URL not exposed in any artifact.
- **Signature surface**: every signing operation goes through MPC; no local signing outside the policy engine.
- **Replay protection**: nonce handling on every x402 request; replay window verified.
- **Rate limiting**: gateway-level retries capped; ladder backoff verified.
- **Open CVEs and mitigations**: list any open issue per `pip-audit` with mitigation plan and target version.

## 11. Acceptance Criteria Mapping

Map each P34 exit criterion (in P34/README.md) to the evidence that proves it. Use a small table: criterion → evidence path → status (PASS/PARTIAL/N/A).

| Exit Criterion (from P34 README) | Evidence Path | Status |
|---|---|---|
| x402 protocol client functional on Base testnet | (set per run) | (set) |
| At least 1 revenue channel end-to-end tested | (set per run) | (set) |
| L1/L2/REJECT approval flow tested | (set per run) | (set) |
| 100% revenue distribution to company wallet verified | (set per run) | (set) |
| Risk controls active (ToS/safety/consent blocks demonstrated) | (set per run) | (set) |
| Audit trail + Beancount mirror complete | (set per run) | (set) |
| Wallet-empty trigger fires under simulated 0-balance | (set per run) | (set) |

## 12. Acceptance Criteria for This Step (Internal)

Internal check: did this step (a) complete its deliverable, (b) pass its required commands, (c) avoid all forbidden patterns, (d) avoid all hard-rejection conditions, (e) produce a 12-section evidence file, (f) trigger the auditor gate. Tick all that apply and write one line of evidence per tick.

Internal checklist:

- [ ] Step deliverable complete: (note path)
- [ ] All required commands exit 0: (note summary)
- [ ] No forbidden pattern matches: (grep result)
- [ ] No hard rejection triggered: (note)
- [ ] 12-section evidence file produced: (this file)
- [ ] Auditor gate triggered: (note path)

---

## Footer

Template version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz
Schema source: AGENTS.md §11

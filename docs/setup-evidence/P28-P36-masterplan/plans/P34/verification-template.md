---
title: "P34 Verification Template — Revenue Search & Monetization"
status: "Active — Verification Template"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P34 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P34 Verification Template

> Use this template after every per-step implementation in P34. Parent verification (operator = Guinevere) confirms scaffold criteria before triggering the auditor gate.

## 1. Verification Scaffold (per Step)

| Step | Expected Files | Forbidden Patterns | Required Commands | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| P34-001 | `src/revenue/x402_client.py`, `pyproject.toml` | Hardcoded private keys, unencrypted RPC URL, `as any` | `python -c "import x402"`; `curl -sf $RPC`; pytest x402_client | `step-001.md` | x402 handshake fails; private key visible |
| P34-002 | `src/revenue/channels/content.py` | `except: pass`, off-gate submit, ToS bypass | pytest content channel; `--discover-dry-run` | `step-002.md` | No ToS scan; bypass approval gate |
| P34-003 | `src/revenue/approval.py` | Auto-approve L2+, force-approve, swallowed vote error | pytest approval: L1_pass, L2_voted, L2_reject, ToS_block, safety_block, consent_block | `step-003.md` | L2+ PASS without vote; ToS/safety/consent violation passes |
| P34-004 | `src/revenue/executor.py` | Off-wallet destination, `as any`, logged private material | pytest executor: company-wallet-only, override rejected, event emitted | `step-004.md` | Off-wallet route possible; missing event |
| P34-005 | `src/revenue/audit.py`, `src/finance/beancount_writer.py` | Mutable event, missing risk_scan, missing Beancount | pytest audit, pytest Beancount, integration audit→Beancount | `step-005.md` | Event mutable; Beancount missing; risk_scan missing |
| P34-006 | `src/revenue/wallet_watchdog.py` | Auto-execute, silent fail, bypass approval | pytest watchdog: fires after N hours, only-search not-execute; crontab check | `step-006.md` | Watchdog executes instead of searches |
| P34-007 | `src/revenue/risk_controls.py` | `passed=true` default, swallowed err, single-dim scan | pytest scanners: ToS, safety, consent each block | `step-007.md` | Bypassable scanner |
| P34-008 | `tests/integration/test_p34_24h_soak.py` | Mainnet creds, off-wallet | pytest 24h soak: L1_pass, L2_pass, L2_reject, risk_block, audit + Beancount + explorer txs match | `step-008.md` | Audit gap; off-wallet; risk not blocked |

## 2. Binary Pass / Fail Criteria

A step PASSES if and only if all of the following are true:

1. Every expected file exists and is non-empty.
2. No forbidden pattern matches anywhere in the expected files (parent-grep verification).
3. Every required command exits 0 and produces the documented output.
4. The evidence file is written with all 12 sections populated (per AGENTS.md §11).
5. No hard rejection condition is observed.
6. The Boundary Compliance section of the evidence file is fully ticked.

A step FAILS if any of the above is false. Failure is final until the sub-agent re-runs the step and produces a fresh evidence file.

## 3. Runtime Proof Requirements

For the 24h soak step (P34-008), runtime proof must include:

- BaseScan testnet explorer URLs for ≥3 closed-loop transactions.
- `psql -c "SELECT COUNT(*) FROM hermes.events WHERE event_type LIKE 'revenue_%'"` returns ≥3 per required event type.
- Beancount file diff showing ≥3 new `Revenue:X402:*` entries.
- Prometheus counters show `revenue_attempted ≥ 4`, `revenue_approved ≥ 3`, `revenue_distributed ≥ 3`, `revenue_rejected ≥ 1`, `wallet_balance_usdc > 0` at end of soak.
- Wallet watchdog fired at least once (or zero-balance condition was simulated and not met).

## 4. Parent Verification Checklist

Parent (Guinevere) MUST verify each of the following before marking the step complete:

- [ ] Re-ran every required command from the scaffold; output matches sub-agent's claim.
- [ ] Grepped every expected file for every forbidden pattern; zero matches.
- [ ] Read the evidence file in full; 12 sections populated; no placeholder text.
- [ ] Cross-checked event store row count vs. Beancount entry count vs. testnet explorer tx count.
- [ ] Verified no secret material (private key, seed phrase, SOPS-age key) appears in any artifact.
- [ ] Verified no intimate data, surveillance data, or relationship memory appears in any artifact.
- [ ] Verified no L2+ transaction executed without a corresponding S7 vote.
- [ ] Verified no transaction routes to a non-company-wallet address.
- [ ] Confirmed HARD STOP would halt all revenue channels (read code path; no bypass).
- [ ] Confirmed consent revocation would halt any in-flight revenue activity from the affected agent.

## 5. Auditor Gate Trigger

After parent verification PASS, parent spawns parallel auditor specialists (per `plan.md` §9) using file-based output. Each auditor writes to `audit-reports/P34/{surface}.md`. Auditors check surface-specific risks. NEEDS REVIEW / FAIL findings are fixed and re-audited via `task_id` until PASS or accepted false-positive.

## 6. Termination Rule

Parent stops re-verification after the first successful parent verification PASS. No additional checks unless an auditor reports a fresh finding. Maximum two status checks per step per the AGENTS.md termination rule.

## 7. Forbidden-Pattern Quick Grep

Parent re-runs the following grep on every expected file (and any indirect dependency file in same PR):

```
grep -rEn 'as any|@ts-ignore|# type: ignore|except: pass|except Exception:|FORCE_MAINNET|TODO\b|XXX\b' src/revenue/ tests/revenue/ tests/integration/test_p34*
```

Zero matches required (besides the literal `except: pass` exclusions inside documented test fixtures, which auditors explicitly allow only in test isolation contracts).

## 8. Cross-Reference Resolution Check

Parent verifies that every cross-reference in the README/plan files resolves:

- `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` §1 finding #15
- `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` §1 finding #14
- `adr/ADR-054-p27-hermes-society-foundation.md` (only if P34 implementation touches a prior ADR)
- `adr/ADR-055-p34-x402-revenue.md` (Step P34-009)
- `docs/30-data/31-SurveillanceDataPolicy_v1.0.md`
- `docs/30-data/32-ConsentRevocationPolicy_v1.0.md`
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`

Each link must resolve; auditor verifies via `markdown-link-check`.

---

## Footer

Template version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz

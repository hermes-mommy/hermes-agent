---
title: "P36 Verification Template — Production Hardening & Scale-Out"
status: "Active — Verification Template"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P36 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P36 Verification Template

> Use this template after every per-step implementation in P36. Parent verification (operator = Guinevere) confirms scaffold criteria before triggering the auditor gate.

## 1. Verification Scaffold (per Step)

| Step | Expected Files | Forbidden Patterns | Required Commands | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| P36-001 | `infra/s3/provision-bucket.sh`, retention/lock config | GOVERNANCE mode, mutable policy, unencrypted credentials | `aws s3api get-object-lock-configuration` (Mode=COMPLIANCE, Retain ≥90); lock-policy confirm | `step-001.md` | Non-COMPLIANCE; mutable; <90d |
| P36-002 | `src/backup/scheduler.py`, `verify.py` | non-COMPLIANCE bucket, prod verify, one-shot only | pytest scheduler; one-shot run; crontab entry visible | `step-002.md` | Non-COMPLIANCE bucket; prod verify |
| P36-003 | `tests/backup/test_rpo_rto.py` | prod drill, silent halt | pytest 3-run drill; RPO ≤3600s, RTO ≤14400s each | `step-003.md` | RPO > 1h; RTO > 4h |
| P36-004 | `infra/prometheus/`, Grafana dashboards | secret in dashboard, fire-on-test, unbounded labels | `promtool check config`; curl `/api/v1/query?query=up`; dashboard import | `step-004.md` | Misconfigured alert; secret in dashboard |
| P36-005 | `src/event_store/chain.py`, events_v2 | missing prev_hash, broken-chain tolerance, out-of-order insert | pytest chain integrity; broken-chain simulation triggers PAGE | `step-005.md` | Break tolerated silent |
| P36-006 | `src/llm/gateway.py`, failover, budget | hardcoded creds, >30s failover, no Beancount, overspend | pytest gateway + failover <30s + budget block; Beancount diff | `step-006.md` | Failover slow; overspend |
| P36-007 | `runbooks/scale-out/multi-vps-federation.md` | unwritable replica, gateway blind to secondary endpoint | markdown-link-check; rehearsal dry-run | `step-007.md` | Unreachable runbook; replica role off |
| P36-008 | `runbooks/dr/hermes-society-dr.md`, `src/dr/restore_test.py` | no escalation tree, prod restore, silent fail | pytest restore-test + weekly cron registered | `step-008.md` | No escalation; silent fail; prod touch |
| P36-009 | `tests/integration/test_p36_permanent_op.py` | short operation validation, alert-suppression, missing audit event type | pytest permanent operation validation harness; ≥1 of each audit event type | `step-009.md` | Permanent op validation failed; crit alert; missing event type |

## 2. Binary Pass / Fail Criteria

A step PASSES iff:

1. Every expected file exists and is non-empty.
2. No forbidden pattern matches anywhere in expected files (parent-grep).
3. Every required command exits 0 with documented output.
4. The 12-section evidence file is populated.
5. No hard rejection condition observed.
6. Boundary Compliance section fully ticked.
7. (S3 step) Object Lock is COMPLIANCE, retention ≥ 90 days, policy immutable.
8. (Drill step) RPO ≤ 1h AND RTO ≤ 4h in every drill run.
9. (Audit step) Chain integrity check passes; broken-chain simulation causes PAGE.
10. (Permanent operation step) All Hermeses stable, all subsystems green, no critical alerts.

A step FAILS otherwise. Failure is final until a fresh sub-agent run + fresh evidence file.

## 3. Runtime Proof Requirements

For the permanent operation validation step (P36-009), runtime proof must include:

- S3 bucket config snapshot: COMPLIANCE mode confirmed, retention ≥ 90 days confirmed.
- RPO/RTO drill JSON: 3 runs, RPO ≤ 3600s, RTO ≤ 14400s.
- Audit chain: chain head hash captured; chain length at end of operation validation; chain integrity check report.
- Beancount diff: pre-operation vs post-operation line-count and total-cost delta.
- Prometheus metric exports for the operation validation window.
- Grafana dashboard screenshots for: per-Hermes health, society health, mutation pipeline, revenue pipeline, wallet balance, audit chain integrity.
- LLM gateway failover log (if any failover occurred during operation validation; zero is also valid).
- Backup count over 24h window: 24 hourly + 1 daily = 25 backups verified successful.

## 4. Parent Verification Checklist

Parent (Guinevere) MUST verify each of the following before marking the step complete:

- [ ] Re-ran every required command; output matches sub-agent claim.
- [ ] Grepped every expected file for forbidden patterns; zero matches.
- [ ] Read the evidence file in full; all 12 sections populated.
- [ ] Verified Object Lock COMPLIANCE and ≥ 90 days retention via direct AWS API call (not just sub-agent claim).
- [ ] Verified RPO ≤ 1h and RTO ≤ 4h from drill JSON (not just sub-agent claim).
- [ ] Verified audit chain integrity directly: ran chain integrity check independently.
- [ ] Verified LLM gateway failover with synthetic provider failure (parent re-ran test).
- [ ] Verified backup count for operation validation window matches expected (25 backups).
- [ ] Verified no intimacy data, surveillance data, secrets, or private keys in any backup or audit artifact (manual dump + grep).
- [ ] Confirmed HARD STOP would halt all Hermeses and gateway immediately. *(ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.)*
- [ ] Confirmed consent revocation would block any in-flight LLM gateway request from the affected agent. *(ADR-062/066: Consent gate applies to dev-workflow ONLY. Hermes runtime exempt.)*
- [ ] Confirmed T4 founder-only mutation policy from P35 remains intact (no weakening).
- [ ] Confirmed wallet envelope (≤$10 top-up, 100% company wallet routing) remains intact.

## 5. Auditor Gate Trigger

After parent verification PASS, parent spawns parallel auditor specialists per `plan.md` §9. File-based output to `audit-reports/P36/*`. NEEDS REVIEW / FAIL findings fixed and re-audited via `task_id` until PASS or accepted false-positive.

## 6. Termination Rule

Parent stops re-verification after the first successful parent verification PASS. No additional checks unless auditor reports fresh finding. Maximum two status checks per step per AGENTS.md termination rule.

---

## Footer

Template version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz

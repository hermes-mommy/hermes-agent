---
title: "P36 Evidence Template — Production Hardening & Scale-Out"
status: "Active — Evidence Template"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P36 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
template_schema: "AGENTS.md §11 — 12-section evidence minimum"
---

# P36 Evidence Template (12-Section Schema)

> Use this template for every per-step evidence file `docs/setup-evidence/P36/evidence/step-{NNN}.md` and for `docs/setup-evidence/P36/evidence/final-p36-evidence.md`. Every section is required.

## 1. What Was Done

2-5 sentence summary: which hardening layer (S3 / observability / audit / gateway / DR / permanent operation validation) was implemented or exercised, which files touched, which tests ran, which artifacts produced. Reference step ids and command outputs.

## 2. Files Changed

List every file created or modified, marked `[created]` or `[modified]`. Include one-line purpose per file. Group by subsystem (S11 vs S12 vs S13 vs S14).

## 3. Validation Results

List every validation command run with exit code and one-line interpretation. Include RPO/RTO drill numbers, audit chain integrity report lines, LLM failover timing, operation metrics.

## 4. Evidence Artifacts

List every artifact: S3 bucket configuration snapshots, drill JSON outputs, Prometheus query outputs, Grafana dashboard exports, audit chain head hash, Beancount file diffs, operation summary. Each artifact referenced by file path or audit row id.

## 5. Doc-Sync Impact

List every doc cross-referenced or updated. Include DR runbook, multi-VPS federation runbook, ADR-Index (for any new ADRs), AGENTS.md cross-refs (no body changes), PersonaSafetyPolicy cross-refs.

## 6. Boundary Compliance

Mandatory and auditable. Tick each:

- [ ] No persona drift (PersonaSafetyPolicy v1.0 unchanged).
- [ ] No consent violation (ConsentRevocationPolicy v1.0 honored). *(ADR-062/066: Consent gate applies to dev-workflow ONLY. Hermes runtime exempt.)*
- [ ] No surveillance overreach (SurveillanceDataPolicy v1.0 honored; no surveillance data in backup, audit, or operation metrics).
- [ ] No Y6 violation. *(ADR-067: Y-level caps apply to dev-workflow ONLY. Hermes runtime has no Y-level cap.)*
- [ ] No HARD STOP bypass. *(ADR-062: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.)*
- [ ] No secret/intimate data in any backup artifact, audit payload, or Beancount entry.
- [ ] No S3 policy relaxation (Object Lock COMPLIANCE immutable).
- [ ] No RPO > 1h in any drill run.
- [ ] No RTO > 4h in any drill run.
- [ ] No audit chain break tolerated.
- [ ] Wallet envelope honored (≤$10 top-up applied to revenue; LLM cost from operator account).
- [ ] All per-Hermes daily token budgets respected.

## 7. Rollback / Re-run Safety

Describe rollback path for each hardened subsystem. Confirm idempotency or document one-shot behavior. Confirm no destructive ops without explicit Faiz approval.

For P36 specifically, document:

- S3 Object Lock COMPLIANCE is immutable; rollback = create a new bucket (rare and explicit). Document whether the new bucket requires its own retention policy review.
- Backup scheduler rollback: disable cron, archive failed runs in evidence file, never delete prior backups.
- Prometheus/Grafana config rollback: revert config to prior commit; metric history preserved (Prometheus TSDB retention handles this).
- LLM gateway rollback: route affected Hermeses back to direct provider (legacy path) and document the per-Hermes slice.
- Audit chain rollback: not applicable forward-only; chain integrity is its own invariant.
- Multi-VPS scaling rollback: deactivate secondary, reroute traffic to primary, document the activation state and any data drift.
- 24h permanent operation rollback: re-run on a clean state; preserve original operation evidence in immutable audit row.

## 8. Design Decisions / Caveats

Document any decision auditors should understand. Include:

- **Object Lock COMPLIANCE choice**: COMPLIANCE (over GOVERNANCE) because GOVERNANCE allows the bucket owner to override retention, which is insufficient against insider tamper or post-compromise override. COMPLIANCE is immutable even for the root account.
- **Retention policy 90 days**: chosen because durable operational forensics typically need at least one quarter; tunable upward only (never downward).
- **RPO ≤ 1h**: matches hourly WAL archive cadence plus the same-hour verify cycle. Tighter RPO requires streaming replication; looser is unacceptable for safety-affecting data.
- **RTO ≤ 4h**: matches a typical PG basebackup + WAL replay + sandbox validation cycle + Prometheus re-wire. Tightening requires parallel restore rehearsal.
- **SHA256 hash chain**: canonical 2026 choice for chain integrity; collision-resistant, fast, well-supported. Note: SHA3-256 or Blake3 are stronger but the auditor pool is most familiar with SHA256.
- **LLM failover 30s**: chosen as a balance between provider-ping overhead and Hermes-stall tolerance. 60s+ would cause Hermes user-visible latency; <30s risks flapping on transient provider hiccups.
- **Beancount cost formula**: tokens × per-1k-token rate × provider multiplier. Locked constant; auditor checks every Beancount entry against the formula during operation validation.
- **Multi-VPS threshold tuning**: 32c/64GB + 4h sustained window chosen to suppress short-lived spikes; tightening requires a new ADR.

Any deferred work, known limitations, or open questions.

## 9. Auditor Gate

State auditor reports (`audit-reports/P36/{surface}.md`) with verdict (PASS / NEEDS REVIEW / FAIL). For NEEDS REVIEW or FAIL, document the fix plan or acceptance rationale.

| Surface | Auditor Path | Verdict |
|---|---|---|
| S3 Object Lock COMPLIANCE | `audit-reports/P36/s3-object-lock.md` | (set per run) |
| Backup scheduler + RPO/RTO | `audit-reports/P36/backup-rpo-rto.md` | (set per run) |
| Prometheus + Grafana | `audit-reports/P36/observability.md` | (set per run) |
| Hash-chained audit | `audit-reports/P36/audit-chain.md` | (set per run) |
| LLM gateway + failover + budget | `audit-reports/P36/llm-gateway.md` | (set per run) |
| Multi-VPS federation procedure | `audit-reports/P36/multi-vps-fed.md` | (set per run) |
| DR runbook + restore test | `audit-reports/P36/dr-runbook.md` | (set per run) |
| 24h society permanent operation | `audit-reports/P36/permanent-op.md` | (set per run) |
| Boundary preservation | `audit-reports/P36/boundary-preservation.md` | (set per run) |

## 10. Security Scan

Security findings:

- **S3 bucket policy review**: confirm Object Lock is COMPLIANCE (not GOVERNANCE); retention ≥ 90 days; bucket policy locked.
- **Audit chain tamper resistance**: SHA256 chain; integrity check runs every 15 minutes; PAGE alert on mismatch.
- **LLM gateway credential handling**: SOPS-age encrypted at rest; never logged; never appear in Beancount entries.
- **Backup encryption at rest**: S3 server-side encryption (SSE-S3 minimum; SSE-KMS preferred); keys rotated quarterly per `docs/20-security/23-SecretsRotationRunbook_v1.0.md`.
- **Operation-time secret exposure scan**: boundary_audit.py runs post-operation with zero hits expected; positive control test verifies the scanner can detect seeded secrets.
- **Open CVEs and mitigations**: list any open issue per `pip-audit` and `npm audit` for the operation window dependencies.

## 11. Acceptance Criteria Mapping

Map each P36 exit criterion (P36/README.md) to evidence. Small table: criterion → evidence path → status (PASS/PARTIAL/N/A).

| Exit Criterion (from P36 README) | Evidence Path | Status |
|---|---|---|
| S3 Object Lock COMPLIANCE confirmed | (set per run) | (set) |
| RPO ≤ 1h verified | (set per run) | (set) |
| RTO ≤ 4h verified | (set per run) | (set) |
| Prometheus + Grafana live ≥ 24h | (set per run) | (set) |
| Hash-chained audit integrity | (set per run) | (set) |
| LLM gateway failover ≤ 30s | (set per run) | (set) |
| Per-Hermes daily budget enforced | (set per run) | (set) |
| 24h society permanent operation PASS | (set per run) | (set) |
| DR runbook + weekly restore test | (set per run) | (set) |
| Multi-VPS federation procedure documented | (set per run) | (set) |
| Boundary preservation scan zero hits | (set per run) | (set) |

## 12. Acceptance Criteria for This Step (Internal)

Internal check: did this step (a) deliver its subsystem, (b) run its drill/test, (c) produce audit-trail entry, (d) preserve all boundaries, (e) emit metrics, (f) update cross-referenced docs. Tick all that apply.

Internal checklist:

- [ ] Subsystem delivered: (note path)
- [ ] Drill/test run successfully: (note summary)
- [ ] Audit-trail entry emitted: (note event)
- [ ] All boundaries preserved: (note summary)
- [ ] Metrics emitted: (note metric name)
- [ ] Cross-referenced docs updated: (note file)

---

## Footer

Template version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz
Schema source: AGENTS.md §11

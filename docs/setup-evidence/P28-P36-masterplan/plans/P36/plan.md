---
title: "P36 Implementation Plan — Production Hardening & Scale-Out"
status: "Active — Implementation Plan"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P36 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P36 Implementation Plan: Production Hardening & Scale-Out

## 1. Objective

Deliver the final production hardening for the Hermes Society: S3 Object Lock COMPLIANCE backups with proven RPO ≤1h / RTO ≤4h, full Prometheus + Grafana observability (AI-interpreted), hash-chained audit trail extending P22.1 IntegrationAuditWriter, LLM gateway with shared pool and provider failover, documented multi-VPS federation procedure, daily DR backup to encrypted S3, and permanent continuous production operation from day 1 (NO soak test — brainstorm decision 2026-06-28). End-state: full autonomy + Faiz as client + continuous evolution (P37+ implied, no defined end state — grow company with more AIs). Day-1 breaks are hotfixed in production (no rollback, fix forward). Metrics include operational + capability dimensions. DR is automated backup + VPS respawn (RTO <4h). VPS security is Tailscale FIRST then hardening (NOT fail2ban/UFW before Tailscale); AI self-manages with full root access (Faiz has NO access). Crisis response is auto-recover with no human intervention. 6 circuit breakers from P24 v2.0: cost, memory, CPU, sub-agent count, thought rate, emotion intensity. **P24 v2.0 is a HARD DEPENDENCY** — P36 hardens production on P24 native infrastructure. Scaling: auto-upgrade VPS (>80% resource usage for 1h, 4C→8C→16C). Competitors: active monitoring.

## 2. Scope

### IN scope

- S3 bucket provisioning with Object Lock COMPLIANCE mode (immutable retention).
- Backup scheduler: daily full backup to encrypted S3-compatible storage (Hermes-managed schedule).
- RPO ≤ 1h / RTO ≤ 4h prove-out via timed drill; DR via automated backup + new-VPS respawn.
- Prometheus metrics: per-Hermes + society-wide; Grafana dashboards; alerting. AI-interpreted monitoring (Hermes interprets alerts and decides response).
- Hash-chained audit writer extending P22.1 IntegrationAuditWriter with 6 new event types.
- LLM gateway: shared pool, primary→secondary failover ≤30s, per-Hermes daily token budget, Beancount cost tracking.
- Multi-VPS federation procedure: automated activation when resource usage >80% for 1h (4C→8C→16C auto-upgrade).
- DR runbook + automated daily backup (no weekly restore test — production is permanent from day 1).
- Permanent continuous production monitoring (NOT a soak test — P36 is permanent operation from day 1; brainstorm decision 2026-06-28: no soak test).
- VPS security: Tailscale FIRST then hardening (NOT fail2ban/UFW before Tailscale); AI self-manages VPS with full root access (Faiz has NO access).
- Operational + capability metrics (not just uptime — includes tasks completed, skills acquired, self-modifications made).
- Auto-recover crisis response (no human intervention for any crisis scenario).
- Auto-upgrade VPS scaling (>80% resource usage sustained for 1h triggers upgrade: 4C→8C→16C).
- 6 circuit breakers from P24 v2.0: cost, memory, CPU, sub-agent count, thought rate, emotion intensity.
- Production is PERMANENT (no decommissioning unless hard fork).
- Competitor monitoring: active.
- P24 v2.0 native infrastructure = HARD DEPENDENCY (not fork-agnostic).

### OUT of scope

- Cloud-provider migration (assume current VPS arrangement throughout P36).
- For-profit legal entity formation (governance-only; legal wrapper is Marshall Islands DAO, post-P36).
- T4 mutation policy changes (P35 fixed T4 as founder-only; P36 must not weaken this).
- Multi-region S3 replication (single-region durable Object Lock is the canonical pattern for 2026).

## 3. Dependency Map

| Dependency | Status | Gate |
|---|---|---|
| ALL prior phases P28-P35 | Required | Phase-by-phase evidence root PASS |
| **P24 v2.0 PASS** | **Required** | **P24 native infrastructure — HARD DEPENDENCY. P36 hardens on P24.** |
| P22.1 PRODUCTION PASS | Required | IntegrationAuditWriter foundation |
| S3 bucket Object Lock COMPLIANCE | Required | Bucket policy cannot be relaxed |
| Object Lock retention policy | Required | ≥90 days minimum |
| Prometheus + Grafana | Required | Both running and reachable |
| LLM provider accounts (primary + secondary) | Required | Both reachable, billing configured |
| Beancount ledger | Required | Writable from VPS |
| PostgreSQL WAL archiving | Required | Continuous archiving to S3 prefix |
| Redis persistence (AOF + RDB) | Required | Both enabled |
| SOPS-age keys | Required | S3 credentials encrypted at rest |
| Compute monitoring | Required | Prometheus node_exporter; alert at >32c/64GB |

## 4. Implementation Steps

### Step P36-001: S3 bucket provisioning with Object Lock COMPLIANCE

- **Task**: Provision S3 bucket with Object Lock enabled at bucket-creation time (cannot be enabled after creation in COMPLIANCE mode). Set retention policy to 90 days minimum. Lock the bucket policy so it cannot be relaxed without privileged Faiz action. Configure bucket lifecycle to expire objects only after retention.
- **Files**: `infra/s3/provision-bucket.sh`, `infra/s3/lock-policy.json`, `infra/s3/retention-config.json`, `runbooks/s3-object-lock.md`.
- **Forbidden patterns**: GOVERNANCE mode (insufficient for tamper-evident backups); bucket creation without Object Lock; mutable retention policy; unencrypted credentials.
- **Required commands**: `aws s3api get-object-lock-configuration --bucket $BUCKET` exits 0 and shows `Mode: COMPLIANCE`, `RetainPeriod: 90`; `aws s3api put-object-lock-configuration --bucket $BUCKET ...` confirm-only test that policy is accepted but cannot be relaxed; `aws s3 cp test.txt s3://$BUCKET/test.txt --object-lock-mode COMPLIANCE --object-lock-retain-until-date "$(date -u -d '+1 day')"` exits 0.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-001.md`.
- **Hard rejection**: FAIL if Object Lock is not COMPLIANCE; FAIL if retention < 90 days; FAIL if bucket policy is mutable.

### Step P36-002: Backup scheduler — hourly incremental / daily full / weekly verification

- **Task**: Implement `src/backup/scheduler.py` with three jobs: hourly incremental (PostgreSQL WAL archive to S3 + Redis snapshot to S3), daily full (PG base backup using `pg_basebackup`, full Redis dump), weekly verification (auto-restore to isolated sandbox + checksum compare). Configure system crontab or systemd timer.
- **Files**: `src/backup/__init__.py`, `src/backup/scheduler.py`, `src/backup/pg_backup.py`, `src/backup/redis_backup.py`, `src/backup/verify.py`, `infra/cron/backup-scheduler.cron`, `tests/backup/test_scheduler.py`, `tests/backup/test_verify.py`.
- **Forbidden patterns**: backup to mutable S3 location; backup to local-only; backup that overwrites previous full; verify that touches production data.
- **Required commands**: `python -m pytest tests/backup/test_scheduler.py -v` exits 0; `python -m pytest tests/backup/test_verify.py -v` exits 0; `python -m src.backup.scheduler --run-once incremental` exits 0 and emits backup event; manual `crontab -l | grep backup-scheduler` shows configured entries.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-002.md`.
- **Hard rejection**: FAIL if scheduler runs against non-COMPLIANCE bucket; FAIL if verify restores to production; FAIL if scheduler is one-shot-only (must be re-runnable).

### Step P36-003: RPO ≤ 1h and RTO ≤ 4h prove-out

- **Task**: Run a timed drill: stop PostgreSQL writes, simulate restore from latest full backup + last hour of WAL in isolated sandbox, measure elapsed time. RPO gap = `now - last_WAL_archive`. RTO = elapsed restore time. Repeat drill 3 times; document min/max/median.
- **Files**: `tests/backup/test_rpo_rto.py`, `tests/backup/conftest_restore.py`, `runbooks/dr/restore-drill.md`.
- **Forbidden patterns**: drill on production; drill without isolated sandbox; halting restore drill silently.
- **Required commands**: `python -m pytest tests/backup/test_rpo_rto.py -v` exits 0; three drill runs each return RPO ≤ 3600s and RTO ≤ 14400s; artifacts saved to `audit-reports/P36/rpo-rto-drill.json`.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-003.md`.
- **Hard rejection**: FAIL if any drill run exceeds 1h RPO or 4h RTO; FAIL if drill touches production; FAIL if drill results are not artifact-saved.

### Step P36-004: Prometheus + Grafana observability (per-Hermes + society-wide)

- **Task**: Deploy Prometheus with service discovery for each Hermes process. Deploy Grafana with dashboards: per-Hermes health (heartbeat, token usage, error rates), society-wide (lifecycle, governance, revenue, mutation, consent, safety event counters), mutation pipeline, revenue pipeline, wallet balance, audit chain integrity. Wire 6 critical alerts (HARD STOP triggered, audit chain broken, wallet empty >6h, daily token budget exhausted, RPO exceeded, mutation canary unhealthy).
- **Files**: `infra/prometheus/prometheus.yml`, `infra/prometheus/alerts.yml`, `infra/grafana/dashboards/*.json`, `src/observability/metrics.py`, `tests/observability/test_metrics.py`.
- **Forbidden patterns**: dashboards with hardcoded secrets; alerts that fire on test runs (use `severity` or `environment` label); metrics with high-cardinality unbounded labels.
- **Required commands**: `promtool check config infra/prometheus/prometheus.yml` exits 0; `curl -sf http://prom:9090/api/v1/query?query=up` returns per-Hermes `up=1`; Grafana dashboard import test exits 0; alertmanager dry-run shows no alerts for current state.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-004.md`.
- **Hard rejection**: FAIL if any critical alert is misconfigured; FAIL if dashboards are not queryable; FAIL if any dashboard contains plaintext secrets.

### Step P36-005: Hash-chained audit trail extending P22.1 IntegrationAuditWriter

- **Task**: Extend `IntegrationAuditWriter` with 6 new event types: `agent_lifecycle`, `governance_decision`, `financial_transaction`, `mutation`, `consent_op`, `safety_event`. Each event carries `prev_hash` (SHA256 of previous tail) and `self_hash` (SHA256 of `{prev_hash, payload, occurred_at, signer}`). On insert, writer verifies `prev_hash` matches current tail; insert fails if mismatch.
- **Files**: `src/event_store/integration_audit_writer.py` (extend), `src/event_store/chain.py`, `src/event_store/events_v2.py`, `tests/event_store/test_chain.py`, `tests/integration/test_audit_chain.py`.
- **Forbidden patterns**: events without `prev_hash`; mutable `prev_hash`; chain breaks tolerated silently; audit events emitted in non-deterministic order.
- **Required commands**: `python -m pytest tests/event_store/test_chain.py -v` exits 0; `python -m pytest tests/integration/test_audit_chain.py -v` exits 0; chain integrity check returns `OK` for current state; broken-chain simulation triggers `PAGE` alert.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-005.md`.
- **Hard rejection**: FAIL if any event lacks `prev_hash`; FAIL if chain break is silently tolerated; FAIL if audit writer can insert out of order.

### Step P36-006: LLM gateway / router (shared pool, failover, budget, Beancount)

- **Task**: Configure `src/llm/gateway.py` with `request(hermes_id, prompt) -> Response`. Gateway maintains provider health (active ping every 30s), routes primary → secondary on failure within 30s, enforces per-Hermes daily token budget (read from config; configurable), writes Beancount cost entry per request (cost = tokens × model_rate).
- **Files**: `src/llm/__init__.py`, `src/llm/gateway.py`, `src/llm/provider_health.py`, `src/llm/budget.py`, `src/finance/beancount_llm.py`, `tests/llm/test_gateway.py`, `tests/llm/test_failover.py`, `tests/llm/test_budget.py`.
- **Forbidden patterns**: hardcoded provider credentials; failover that exceeds 30s; budget that allows overspend; Beancount entries without double-entry or with non-deterministic ordering.
- **Required commands**: `python -m pytest tests/llm/test_gateway.py -v` exits 0; `python -m pytest tests/llm/test_failover.py -v -k "failover_under_30s"` exits 0; `python -m pytest tests/llm/test_budget.py -v -k "blocks_when_budget_exhausted"` exits 0; Beancount file diff after burst test shows N+1 new entries.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-006.md`.
- **Hard rejection**: FAIL if failover exceeds 30s in test; FAIL if budget allows overspend; FAIL if Beancount entries are missing or non-double-entry.

### Step P36-007: Multi-VPS federation procedure documentation

- **Task**: Author `runbooks/scale-out/multi-vps-federation.md` with the activation procedure: when Prometheus alert reports primary VPS resource pressure (>32c/64GB sustained for 4h+), Faiz approves secondary VPS provisioning, replication is enabled (streaming replication for PostgreSQL, Redis replication), Hermeses can be relocated to secondary, gateway learns new endpoints. Document the rehearsal procedure (dry-run on a sandbox environment without production data).
- **Files**: `runbooks/scale-out/multi-vps-federation.md`, `runbooks/scale-out/rehearsal-checklist.md`, `infra/vps/replication-config.md` (informational).
- **Forbidden patterns**: undocumented scaling runbook; replica that can serve writes by default (replica = read-only failsafe); gateway that does not learn new endpoint during failover.
- **Required commands**: `markdown-link-check runbooks/scale-out/multi-vps-federation.md` exits 0; rehearsal dry-run script `tests/runbook/test_multi_vps_rehearsal.py` exits 0; doc cross-references resolve.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-007.md`.
- **Hard rejection**: FAIL if runbook is undocumented or unreachable; FAIL if replica role is misconfigured; FAIL if gateway failover to secondary is not documented.

### Step P36-008: DR runbook + weekly automated restore test job

- **Task**: Author `runbooks/dr/hermes-society-dr.md` covering: incident detection, severity classification, escalation tree (Faiz + co-founder), backup retrieval procedure, restore steps with RPO+RTO targets, post-restore verification checklist. Configure `src/dr/restore_test.py` as a weekly cron that runs the RPO/RTO drill (Step P36-003) and reports pass/fail to Prometheus + audit trail.
- **Files**: `runbooks/dr/hermes-society-dr.md`, `src/dr/__init__.py`, `src/dr/restore_test.py`, `infra/cron/dr-restore-test.cron`, `tests/dr/test_restore_test.py`.
- **Forbidden patterns**: runbook without escalation tree; restore test that touches production; restore test that is silent on failure.
- **Required commands**: `python -m pytest tests/dr/test_restore_test.py -v` exits 0; `crontab -l | grep dr-restore-test` shows weekly entry; markdown link-check passes; one-shot run completes within RTO.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-008.md`.
- **Hard rejection**: FAIL if runbook lacks escalation; FAIL if restore test touches production; FAIL if weekly cron is not registered.

### Step P36-009: Permanent operation validation (all Hermeses + all subsystems) — NO SOAK TEST

- **Task**: Brainstorm decision (2026-06-28): NO soak test. Production is permanent from day 1. Validate continuous operation across all Hermeses (founders + revenue earners if any) with: (a) every Hermes emits heartbeat every 60s, (b) at least 1 audit event of each type is produced, (c) at least 1 LLM gateway request is routed per Hermes, (d) at least 1 backup completes hourly, (e) no critical alerts fire, (f) all budgets within limits, (g) all metrics within SLO. Validate 6 circuit breakers from P24 v2.0: cost, memory, CPU, sub-agent count, thought rate, emotion intensity. Day-1 breaks are hotfixed in production (no rollback, fix forward). Operation report summarizes health.
- **Files**: `tests/integration/test_p36_permanent_operation.py`, `tests/integration/conftest_p36.py`, `runbooks/observability/permanent-operation-checklist.md`.
- **Forbidden patterns**: any reference to soak test or time-boxed validation; suppressing alerts to pass; treating production as temporary.
- **Required commands**: `python -m pytest tests/integration/test_p36_permanent_operation.py -v` exits 0; operation harness runs with periodic self-checks; operation report asserts all green.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-009.md`.
- **Hard rejection**: FAIL if any critical alert fires; FAIL if any subsystem reports degraded state; FAIL if any soak test reference remains in codebase.

### Step P36-010: ADR-057 P36 production hardening ADR

- **Task**: Author `adr/ADR-057-p36-production-hardening.md` documenting the decision: S3 Object Lock COMPLIANCE mode (≥90 days), RPO ≤ 1h / RTO ≤ 4h targets, hash-chained audit (SHA256) extending P22.1 IntegrationAuditWriter, LLM gateway with 30s failover + per-Hermes daily budget + Beancount cost tracking, multi-VPS federation activation threshold (>32c/64GB sustained 4h+). Register in ADR-Index (parent-owned operation).
- **Files**: `adr/ADR-057-p36-production-hardening.md` (created), `docs/10-governance/17-ADR_Index_v1.0.md` (registration edit — parent-owned).
- **Forbidden patterns**: ADR without 5 standard sections; ADR that proposes GOVERNANCE mode (insufficient); ADR that proposes shorter retention without explicit research rationale.
- **Required commands**: `markdown-link-check adr/ADR-057-p36-production-hardening.md` exits 0; frontmatter includes ADR-057, all 5 sections; explicit cross-reference to P22.1 (IntegrationAuditWriter).
- **Evidence**: `docs/setup-evidence/P36/evidence/step-010.md`.
- **Hard rejection**: FAIL if ADR body lacks any standard section; FAIL if retention < 90 days; FAIL if no P22.1 cross-reference.

### Step P36-011: Boundary preservation audit (no secret/intimate in any hardening surface)

- **Task**: Author `src/audit/boundary_audit.py` that scans every backup artifact, audit event payload, and Beancount entry produced during permanent operation validation for forbidden content categories: private keys (regex), SOPS-age keys, relationship memory, intimacy columns (encrypted or otherwise), surveillance data, founder intimate data, operator intimate data. Any hit fires `boundary_violation_detected` to a dedicated Prometheus alert. The audit runs automatically at end-of-operation-validation.
- **Files**: `src/audit/boundary_audit.py`, `tests/audit/test_boundary_audit.py`, `tests/integration/test_p36_boundary_in_operation.py`.
- **Forbidden patterns**: scanner without positive controls (must trigger on synthetic test data); scanner that misses relationship memory or intimacy column names.
- **Required commands**: `python -m pytest tests/audit/test_boundary_audit.py -v` exits 0; `python -m pytest tests/audit/test_boundary_audit.py -v -k "positive_control_private_key"` exits 0; `python -m pytest tests/audit/test_boundary_audit.py -v -k "positive_control_intimacy_field"` exits 0; `python -m pytest tests/integration/test_p36_boundary_in_operation.py -v` exits 0; post-operation run of `python -m src.audit.boundary_audit --scan-operation-window` exits 0 with zero hits.
- **Evidence**: `docs/setup-evidence/P36/evidence/step-011.md`.
- **Hard rejection**: FAIL if scanner misses any positive control; FAIL if post-operation run finds any hit; FAIL if alert is not wired.

## 5. Verification Scaffold

| Step | Expected Files | Forbidden Patterns | Required Commands | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| P36-001 | `infra/s3/provision-bucket.sh`, retention/lock config | GOVERNANCE mode, mutable policy, unencrypted creds | aws s3api get-object-lock; lock policy confirm | step-001.md | Non-COMPLIANCE; mutable policy |
| P36-002 | `src/backup/scheduler.py`, `verify.py` | mutable destination, prod-touching verify, one-shot only | pytest scheduler; one-shot run; crontab | step-002.md | Non-COMPLIANCE bucket; prod verify |
| P36-003 | `tests/backup/test_rpo_rto.py` | prod drill, silent halt | pytest RPO/RTO drill 3-run | step-003.md | RPO > 1h; RTO > 4h |
| P36-004 | `infra/prometheus/`, grafana dashboards | secret-bearing dashboard, fire-on-test alert, unbounded labels | promtool check; query up; dashboard import | step-004.md | Misconfigured alert; secret in dashboard |
| P36-005 | `src/event_store/chain.py`, events_v2 | missing prev_hash, broken-chain tolerance | pytest chain integrity; broken-chain alert | step-005.md | Break tolerated silent |
| P36-006 | `src/llm/gateway.py`, budget, failover | hardcoded creds, >30s failover, no Beancount | pytest gateway + failover <30s + budget block | step-006.md | Failover slow; overspend |
| P36-007 | `runbooks/scale-out/multi-vps-federation.md` | unwritable replica, gateway blind to failover | markdown-link-check; rehearsal dry-run | step-007.md | Unreachable runbook; replica role off |
| P36-008 | `runbooks/dr/hermes-society-dr.md`, `src/dr/restore_test.py` | runbook without escalation, prod restore, silent fail | pytest restore test + cron | step-008.md | No escalation; silent fail |
| P36-009 | `tests/integration/test_p36_permanent_operation.py` | soak reference, alert-suppression | pytest permanent operation harness | step-009.md | Critical alert fired; soak ref remains |
| P36-010 | `adr/ADR-057-p36-production-hardening.md` | missing section, <90d retention, no P22.1 ref | markdown-link-check, frontmatter check | step-010.md | Section missing; retention off; no P22.1 |
| P36-011 | `src/audit/boundary_audit.py` | no positive control, missed intimacy field | pytest boundary scanner + integration permanent operation | step-011.md | Positive control missed; post-operation hit |

## 6. Collision Scan

- **Shared writer risk**: `src/event_store/integration_audit_writer.py` from P22.1. P36 extends it; do NOT modify prior-only behavior, only ADD new event types.
- **Shared writer risk**: Prometheus config and Grafana dashboard directory. P36 only ADDS; existing dashboards untouched.
- **Shared writer risk**: S3 bucket policy. Immutable once set; only Faiz can change after retention.
- **Shared writer risk**: Beancount ledger. P36 only ADDS cost entries; existing entries untouched.
- **Shared docs**: AGENTS.md / PersonaSafetyPolicy — owner-only; P36 must not modify these.

## 7. Rollback Plan

- S3 Object Lock COMPLIANCE is immutable; rollback = create new bucket (rare).
- Backup scheduler rollback: disable cron, do not delete prior backups, document pause in evidence file.
- Prometheus/Grafana regression = revert config to previous commit; do not lose metric history.
- LLM gateway rollback = revert to direct provider calls per Hermes (legacy path) for affected Hermeses only.
- Audit chain rollback: not applicable once events inserted; chain is forward-only and tamper-evident.
- Multi-VPS scaling rollback = deactivate secondary, route all traffic back to primary, document in evidence.
- Permanent operation rollback: re-run validation on a clean state; original operation evidence preserved.

## 8. Evidence Requirements

- Per-step evidence: `docs/setup-evidence/P36/evidence/step-{NNN}.md` with 12 sections per AGENTS.md §11.
- Aggregated evidence: `docs/setup-evidence/P36/evidence/final-p36-evidence.md` (12 sections).
- S3 bucket configuration audit: Object Lock mode, retention period, policy lock status.
- RPO/RTO drill artifacts: 3-run JSON with min/max/median.
- Audit chain integrity report.
- Beancount cost diff: pre-operation vs post-operation.
- Operation report: per-Hermes summary, per-subsystem summary, alert summary.

## 9. Auditor Matrix

| Surface | Auditor Type | Path |
|---|---|---|
| S3 Object Lock COMPLIANCE | Compliance auditor | `audit-reports/P36/s3-object-lock.md` |
| Backup scheduler + RPO/RTO | Operations auditor | `audit-reports/P36/backup-rpo-rto.md` |
| Prometheus + Grafana observability | Observability auditor | `audit-reports/P36/observability.md` |
| Hash-chained audit | Compliance auditor | `audit-reports/P36/audit-chain.md` |
| LLM gateway + failover + budget | Operations auditor | `audit-reports/P36/llm-gateway.md` |
| Multi-VPS federation procedure | Architecture auditor | `audit-reports/P36/multi-vps-fed.md` |
| DR runbook + restore test | Operations auditor | `audit-reports/P36/dr-runbook.md` |
| 24h permanent operation validation | End-to-end auditor | `audit-reports/P36/permanent-operation.md` |
| Boundary preservation (no secret/intimate in backup/audit) | Safety auditor | `audit-reports/P36/boundary-preservation.md` |

## 10. Execution Checklist

- [ ] All prior phases P28-P35 confirmed PASS via evidence root.
- [ ] S3 bucket created with Object Lock COMPLIANCE; retention configured; policy locked.
- [ ] Backup scheduler + verify implemented and tested.
- [ ] RPO ≤ 1h / RTO ≤ 4h drill run 3 times and passing.
- [ ] Prometheus + Grafana dashboards live for ≥ 24h.
- [ ] Audit chain integrity confirmed.
- [ ] LLM gateway failover ≤ 30s, per-Hermes budget enforced.
- [ ] Multi-VPS federation procedure documented and rehearsed.
- [ ] DR runbook published with weekly automated restore test.
- [ ] Permanent operation validation passing with no critical alerts (NO soak test — brainstorm decision).
- [ ] Boundary preservation audit runs post-operation with zero hits.
- [ ] Steps P36-001 through P36-011 completed with parent verification each.
- [ ] All evidence files (per-step + final) written with 12 sections.
- [ ] Auditor matrix reports all PASS or accepted false-positive.
- [ ] No intimacy data, surveillance data, secrets, or private keys in any backup or audit artifact.
- [ ] Final report includes changed files, validation results, evidence paths, caveats.

## 11. Locked Decisions Reviewed

- S3 Object Lock COMPLIANCE mode. Test `tests/backup/test_s3_compliance_immutability.py` exercises the immutability invariant (API call to relax retention is rejected).
- RPO ≤ 1h / RTO ≤ 4h. Test `tests/backup/test_rpo_rto.py` runs the drill 3 times; thresholds encoded as constants; modification requires an ADR-057 amendment.
- LLM gateway operator-account funding. Test `tests/llm/test_gateway_funding_source.py` confirms gateway does NOT draw from company wallet for cost.
- HARD STOP halts the gateway immediately. Test `tests/llm/test_gateway_hard_stop.py` exercises the path. *(ADR-062: HARD STOP references apply to dev workflow only — Guinevere operating contract, NOT Hermes runtime.)*
- Consent revocation per-Hermes. Test `tests/llm/test_gateway_consent_revocation.py` exercises per-Hermes halt. *(Consent annotation: dev workflow only (ADR-062).)*
- Multi-VPS threshold >32c/64GB sustained 4h+. Threshold encoded as constants; `tests/runbook/test_threshold_constant.py` locks the value.
- T4 founder-only from P35. P36 audit includes a regression check that P35 T4 enforcement is still active in audit-trail rows.
- Wallet envelope ≤$10 top-up. P36 dry-run `tests/runbook/test_wallet_envelope_unchanged.py` confirms wallet balance never exceeds $10 across permanent operation.

## 12. ADR Outputs

- **ADR-057 (P36-010)**: `Production Hardening — S3 Object Lock COMPLIANCE + RPO ≤1h RTO ≤4h + hash-chained audit + LLM gateway + multi-VPS federation`. Status: Proposed at P36 start, Accepted on P36 PASS.

## 13. Per-Step Audit Trail Codepath

- P36-001 emits `s3_bucket_provisioned` with mode=COMPLIANCE, retention=90d.
- P36-002 emits `backup_scheduler_run_completed` per cron cycle; `backup_verify_started` and `backup_verify_passed` per weekly run.
- P36-003 emits `rpo_rto_drill_run_completed` per drill with min/max/median metrics.
- P36-004 emits `observability_dashboard_updated` per import; `observability_alert_evaluation` per cycle.
- P36-005 emits `audit_chain_event_appended` per event; `audit_chain_integrity_check_passed` per scan.
- P36-006 emits `llm_gateway_request_routed` per request; `llm_gateway_failover_triggered` on failover; `llm_budget_evaluated` per Hermes per request.
- P36-007 emits `multi_vps_threshold_evaluated` per cycle; `multi_vps_federation_activated` when threshold sustained.
- P36-008 emits `dr_restore_test_started`, `dr_restore_test_passed`/`failed` per weekly run.
- P36-009 emits `operation_started`, `operation_checkpoint{N}`, `operation_completed` with subsystem status.
- P36-010 emits `adr_proposed`.
- P36-011 emits `boundary_audit_scan_completed`; `boundary_violation_detected` on hit (zero hits expected during operation).

## 14. Brainstorm Decisions (2026-06-28)

The following brainstorm decisions (from 2026-06-28 alignment session with 65 decisions) are incorporated into this phase plan:

| Decision | Impact on P36 |
|---|---|
| NO soak test | Production is permanent from day 1. Step P36-009 reworked from "24h soak test" to "permanent operation validation". Day-1 breaks are hotfixed in production (no rollback). |
| End-state = Full autonomy + Faiz as client | No defined end state. P37+ implied — grow company with more AIs. |
| Hotfix in production | No rollback for day-1 breaks. Fix forward. |
| Metrics = Operational + Capability | Not just uptime — includes tasks completed, skills acquired, self-modifications made. |
| Monitoring = Full observability stack | Prometheus+Grafana, Hermes interprets alerts and decides response. |
| Backup = Daily full to encrypted S3 | Hermes-managed schedule. |
| DR = New-VPS respawn (RTO <4h) | Automated backup + VPS respawn. |
| VPS security = Tailscale FIRST then hardening | NOT fail2ban/UFW before Tailscale. AI self-manages with full root access. |
| Crisis = Auto-recover everything | No human intervention for any crisis scenario. |
| Competitors = Active monitoring | Company monitors competition and adapts strategy. |
| Scaling = Auto-upgrade VPS | >80% resource usage for 1h triggers upgrade: 4C→8C→16C. |
| 6 circuit breakers (P24 v2.0) | Cost, memory, CPU, sub-agent count, thought rate, emotion intensity. |
| P24 v2.0 = HARD DEPENDENCY | P36 hardens production on P24 native infrastructure. Fork-agnostic replaced by P24 native fork. |
| ADR-062 disclaimer | HARD STOP references in P36 apply to dev workflow only (Guinevere operating contract), not Hermes runtime. |
| ADR-067 disclaimer | Y-level references apply to dev workflow only. |
| Consent annotation | Consent and HARD STOP references = dev workflow only (ADR-062). |

## Footer

Version 1.1 | Date: 2026-06-28 | Author: Guinevere + Faiz | Changes: Brainstorm decisions integration (NO soak test, permanent operation, ADR-062/067 annotations, P24 hard dependency, Tailscale-first, circuit breakers, auto-scaling, implement→configure/deploy).

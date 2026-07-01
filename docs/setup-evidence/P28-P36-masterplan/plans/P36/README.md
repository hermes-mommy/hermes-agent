---
title: "P36 — Production Hardening & Scale-Out"
status: "Active — Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P36 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
subsystems: [S11, S12, S13, S14]
---

# P36: Production Hardening & Scale-Out

## Overview

Phase P36 is the **final production-hardening phase** of the Hermes Society masterplan. The Society transitions from a self-evolving, revenue-earning fleet (P28-P35 PASS) to one that is **safe to run unattended for extended periods**. This phase delivers S3 backup with Object Lock COMPLIANCE mode, full Prometheus + Grafana observability, hash-chained audit extendable from P22.1's IntegrationAuditWriter, the shared LLM gateway/router, scaling beyond one VPS when the 32c/64GB threshold is exceeded, DR runbook with weekly restore test, and permanent continuous production operation from day 1 (**NO soak test — brainstorm decision 2026-06-28**). VPS security is Tailscale FIRST then hardening (NOT fail2ban/UFW before Tailscale). 6 circuit breakers from P24 v2.0: cost, memory, CPU, sub-agent count, thought rate, emotion intensity. **P24 v2.0 is a HARD DEPENDENCY.**

This is the keystone phase that proves the Society is **operationally safe** — not just functionally safe. P36 verifies that (a) data cannot be lost (RPO ≤1h, RTO ≤4h, Object Lock COMPLIANCE immutable backups), (b) every event is hash-chained for tamper-evident audit, (c) the LLM gateway fails over providers transparently, (d) the system can scale out to multi-VPS federation if compute is exhausted, and (e) DR restore actually works on a recurring schedule.

P36 is the gate to "production complete" status for the Hermes Society. From P36 onward, the Society is intended to operate autonomously with the bounded L4 autonomy profile under audit, with periodic DR tests, and with explicit Faiz approval as the final safety net for destructive operations.

## Goals

- Deploy S3 backup with Object Lock COMPLIANCE mode (hourly incremental, daily full, weekly verification).
- Achieve RPO ≤ 1 hour, RTO ≤ 4 hours with documented runbook.
- Wire full Prometheus + Grafana observability: per-Hermes and society-wide metrics, dashboards, alerting.
- Configure hash-chained audit trail extending P22.1 `IntegrationAuditWriter` for the new audit event types: `agent_lifecycle`, `governance_decision`, `financial_transaction`, `mutation`, `consent_op`, `safety_event`.
- Deploy LLM gateway/router with shared model pool, provider failover, per-Hermes token budget, and Beancount cost tracking.
- Configure multi-VPS federation architecture activated when >32c/64GB exceeded.
- Author DR runbook with automated weekly restore test.
- Validate permanent continuous operation (NO soak test — brainstorm decision: production is permanent from day 1, day-1 breaks are hotfixed).
- Configure 6 circuit breakers from P24 v2.0: cost, memory, CPU, sub-agent count, thought rate, emotion intensity.
- VPS security: Tailscale FIRST then hardening (NOT fail2ban/UFW before Tailscale).

## Prerequisites

- **P24 v2.0 PASS** — **HARD DEPENDENCY. P36 hardens production on P24 native infrastructure.**
- ALL prior phases PASS — P28 through P35 evidenced and verified.
- P22.1 PRODUCTION PASS — IntegrationAuditWriter hash-chained audit foundation in place.
- S3 bucket provisioned with Object Lock COMPLIANCE mode enabled (cannot be disabled once enabled; immutable).
- Object Lock retention policy configured (e.g. 90 days minimum).
- Prometheus + Grafana deployed and reachable from VPS.
- LLM provider accounts configured for primary + secondary (for failover).
- Beancount ledger initialized and writable.
- AGENTS.md preflight check — standard session-start discipline.

## Subsystems Involved

- S11 — S3 Backup & DR (NEW primary): Object Lock COMPLIANCE mode backup, hourly incremental, daily full, weekly verification, RPO ≤1h, RTO ≤4h.
- S12 — Model Pool & LLM Gateway (NEW primary): shared model pool across Hermeses, provider failover, per-Hermes token budget, cost tracking to Beancount.
- S13 — Observability & Audit (full): Prometheus + Grafana + hash-chained audit (extends P22.1 IntegrationAuditWriter).
- S14 — Deployment & VPS Management scale-out: one VPS until >32c/64GB exceeded; multi-VPS federation architecture beyond that.

## Key Deliverables

- S3 bucket with Object Lock COMPLIANCE mode and 90-day minimum retention policy.
- Backup scheduler: hourly incremental (PostgreSQL WAL archive + Redis snapshot), daily full (PG base backup + full Redis dump), weekly verification (auto-restore to isolated sandbox).
- RPO ≤ 1h confirmed by gap analysis between WORM event-store last row and backup last row.
- RTO ≤ 4h confirmed by timed restore drill in a separate sandbox.
- Prometheus metrics: hermes-specific (heartbeats, token usage, error rates) + society-wide (total agent_lifecycle events, total financial_transaction events, total mutation events, total governance_decision events).
- Grafana dashboards: per-Hermes health, society health, mutation pipeline, revenue pipeline, wallet balance, audit chain integrity.
- Hash-chained audit writer extending P22.1 IntegrationAuditWriter with new event types.
- LLM gateway: shared pool across all Hermeses, primary → secondary failover within 30s, per-Hermes daily token budget, Beancount cost entries per request.
- Multi-VPS federation: documented activation procedure when >32c/64GB on primary VPS; secondary VPS as standby; remote PostgreSQL replication.
- DR runbook: `runbooks/dr/hermes-society-dr.md` with automated weekly restore test job.
- 24h society permanent operation validation with all Hermeses stable and all subsystems operational (NO soak test).

## Exit Criteria

- S3 backup tested: Object Lock COMPLIANCE confirmed (cannot delete bucket objects during retention; bucket policy immutable); restore drill passes with RTO ≤ 4h.
- RPO verified ≤ 1h via gap analysis.
- Prometheus + Grafana dashboards live and displaying real metrics for ≥ 24h.
- Hash-chained audit trail verified: chain integrity check passes; broken-chain event triggers PAGE alert.
- LLM gateway tested: synthetic provider failure triggers failover within 30s; Beancount receives cost entry for every LLM request; per-Hermes daily token budget enforced.
- 24h society permanent operation PASS: all Hermeses stable, all subsystems reporting green, no HARD STOP events *(ADR-062: dev workflow only)*, no critical alerts.
- DR runbook published with weekly automated restore test passing on most recent run.
- Multi-VPS federation procedure documented (procedural; not necessarily activated unless compute hit threshold).

## Hard Rejection Criteria

- FAIL if S3 backup does not use Object Lock COMPLIANCE mode (GOVERNANCE mode is insufficient).
- FAIL if permanent operation validation is not performed or any subsystem reports degraded state at the end (NO soak test — brainstorm decision).
- FAIL if audit trail is not hash-chained (each event must reference prior event's hash; chain broken = PAGE alert).
- FAIL if DR restore test fails or is not exercised.
- FAIL if LLM gateway cannot failover within 30s on provider failure.
- FAIL if any Hermes exhausts its daily token budget without the gateway enforcing it.
- FAIL if intimacy data, surveillance data, secrets, or private keys appear in any backup artifact or audit payload.
- FAIL if RPO exceeds 1h or RTO exceeds 4h (gap analysis must close both).
- FAIL if scaling beyond 32c/64GB threshold is needed but multi-VPS federation procedure is not documented and rehearsed.

## Evidence

- Evidence root: `docs/setup-evidence/P36/`
- Plan: `docs/setup-evidence/P28-P36-masterplan/plans/P36/plan.md`
- Evidence template: `docs/setup-evidence/P28-P36-masterplan/plans/P36/evidence-template.md`
- Verification template: `docs/setup-evidence/P28-P36-masterplan/plans/P36/verification-template.md`
- Per-step evidence: `docs/setup-evidence/P36/evidence/step-{NNN}.md`

## Implementation Wave Estimate

P36 is the final phase of the P28-P36 masterplan and is expected to ship across 9-12 implementation waves over 6-10 weeks. Wave 1 (S3 Object Lock COMPLIANCE provisioning) ≈ 1 week, Wave 2 (backup scheduler + verify) ≈ 1 week, Wave 3 (RPO/RTO drill cycles) ≈ 1 week, Wave 4 (Prometheus + Grafana observability) ≈ 1 week, Wave 5 (hash-chained audit extension) ≈ 1 week, Wave 6 (LLM gateway + failover) ≈ 1 week, Wave 7 (multi-VPS federation documentation + rehearsal) ≈ 1 week, Wave 8 (DR runbook + weekly restore test) ≈ 1 week, Wave 9 (permanent operation validation — NO soak test) ≈ 1 week, Wave 10 (final evidence + auditor gate) ≈ 1 week. Mainnet revenue promotion through P34 remains an explicit decision separate from P36 hardening.

## Locked Faiz Decisions Touched by P36

- S3 Object Lock COMPLIANCE mode (not GOVERNANCE). COMPLIANCE is immutable; once enabled, retention cannot be shortened by anyone, including the bucket owner. This protects against insider tamper or compromise during incident response.
- RPO ≤ 1h, RTO ≤ 4h are hard targets. P36 cannot silently degrade these. If the targets become unreachable, escalation to Faiz is required before any operation proceeds.
- LLM cost is funded by the operator account, not by the company wallet. The wallet envelope (≤$10 top-up, default 0) is preserved; LLM cost does not affect wallet balance.
- One large VPS until >32c/64GB sustained for 4h+ before multi-VPS federation activates. P36 documents the procedure; P36 does NOT mandate immediate federation unless the threshold is hit.
- HARD STOP halts all Hermeses, the LLM gateway, the backup scheduler, and any in-flight restore immediately. Even disaster recovery does not bypass HARD STOP. *(ADR-062: HARD STOP references apply to dev workflow only — Guinevere operating contract, NOT Hermes runtime.)*
- Consent revocation by Faiz halts every Hermes the consent was for. The LLM gateway must enforce per-Hermes consent at request time; revocation mid-operation triggers immediate halt of that Hermes' gateway calls. *(Consent annotation: dev workflow only (ADR-062).)*
- T4 mutation policy from P35 (founder-only, 2/2) remains intact. P36 hardening must not loosen any mutation constraint set in P35.

## Failure Modes & Mitigations

| Failure Mode | Mitigation |
|---|---|
| S3 bucket policy relaxation attempt | COMPLIANCE mode rejects the API call; alert routes to Faiz within 60 seconds; bucket state unchanged. |
| RPO degradation (WAL gap exceeds 1h) | Prometheus alert; auto-pause new Hermeses until backup pipeline catches up; full audit event for the gap. |
| Audit chain break (hash mismatch on insert) | Insert fails with explicit `AuditChainBroken`; PAGE alert; on-call Faiz re-evaluates chain integrity from last known-good head. |
| LLM gateway failover slow (>30s) | Provider health pings every 30s; failover triggers within the next ping window; budget enforcement happens pre-request so a slow failover does not allow overspend. |
| Per-Hermes budget exhaustion | Gateway rejects request pre-send; emits `llm_budget_exhausted` event; Hermes can request a one-shot Faiz override (audit logged). |
| Backup scheduler break-in-middle | Postgres WAL archive resumes from last segment; Redis snapshot restarts; never overwrites prior verified backup; integrity check on next restore. |
| Permanent operation alert fires | Operation validation does not auto-fail on single warning; only critical alerts (HARD STOP *(ADR-062: dev workflow only)*, audit chain break, RPO exceeded, mutation canary unhealthy) fail the validation. |
| DR restore in production | DR restore NEVER touches production; restoration targets isolated sandbox (per Step P36-002 verify.py isolation contract). |
| Multi-VPS threshold false-positive | Prometheus alert deduplicates over 4h sustained window; threshold tuning requires Faiz approval. |

## Open Questions for Faiz

- Is multi-region S3 replication required for P36 PRODUCTION PASS, or is single-region COMPLIANCE sufficient for the current compute footprint?
- For permanent operation: is "all Hermeses stable" defined as zero critical alerts, or as zero critical AND zero warning alerts? (NO soak test — brainstorm decision.)
- For LLM gateway budget: should there be a global (society-wide) daily ceiling in addition to per-Hermes ceilings, to prevent Society-wide budget exhaustion?
- DR escalation tree: should co-founder be added as a secondary escalation, or is Faiz-only sufficient?
- For audit chain integrity: is SHA256 the canonical algorithm, or should we use SHA3-256 or Blake3 for stronger tamper resistance?
- For multi-VPS federation: should the secondary always be a hot standby, or is cold-standby acceptable to save VPS cost?

## Footnotes and Cross-References

- Cross-reference: `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` §1 finding #8 — PostgreSQL outbox pattern; finding #13 — multi-bot Discord pattern; finding #14 — wallet stack.
- Cross-reference: P22.1 IntegrationAuditWriter as the foundation that P36's hash-chained audit extends.
- Cross-reference: AGENTS.md §0 — wallet is company asset (default 0, max ~$10 top-up); LLM cost is operator-account funded, not wallet-funded.
- Cross-reference: ADR-Index and any ADRs produced by earlier phases (P28-P35) — P36 must verify all referenced ADRs remain compatible.
- All identity, consent, HARD STOP, and surveillance boundaries inherited from AGENTS.md §0 and PersonaSafetyPolicy. Hardening must not weaken any boundary.

## Brainstorm Decisions (2026-06-28)

Key brainstorm decisions incorporated into P36:

- **NO soak test**: Production is permanent from day 1. Step P36-009 reworked from "24h soak test" to "permanent operation validation". Day-1 breaks are hotfixed in production (no rollback).
- **End-state = Full autonomy + Faiz as client**: No defined end state. P37+ implied — grow company with more AIs.
- **Hotfix in production**: No rollback for day-1 breaks. Fix forward.
- **Metrics = Operational + Capability**: Not just uptime — includes tasks completed, skills acquired, self-modifications made.
- **Monitoring = Full observability stack**: Prometheus+Grafana, Hermes interprets alerts and decides response.
- **Backup = Daily full to encrypted S3**: Hermes-managed schedule.
- **DR = New-VPS respawn (RTO <4h)**: Automated backup + VPS respawn.
- **VPS security = Tailscale FIRST then hardening**: NOT fail2ban/UFW before Tailscale. AI self-manages with full root access.
- **Crisis = Auto-recover everything**: No human intervention for any crisis scenario.
- **Competitors = Active monitoring**: Company monitors competition and adapts strategy.
- **Scaling = Auto-upgrade VPS**: >80% resource usage for 1h triggers upgrade: 4C→8C→16C.
- **6 circuit breakers (P24 v2.0)**: Cost, memory, CPU, sub-agent count, thought rate, emotion intensity.
- **P24 v2.0 = HARD DEPENDENCY**: P36 hardens production on P24 native infrastructure. Fork-agnostic replaced by P24 native fork.
- **ADR-062/067 disclaimers**: HARD STOP and consent references = dev workflow only. Y-level references = dev workflow only.

## Footer

Version 1.1 | Date: 2026-06-28 | Author: Guinevere + Faiz | Changes: Brainstorm decisions integration (NO soak test, permanent operation, ADR-062/067 annotations, P24 hard dependency, Tailscale-first, circuit breakers, auto-scaling, implement→configure/deploy).

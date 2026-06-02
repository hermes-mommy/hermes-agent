# Guinevere SLO/SLA/Error Budget Specification

**Document Type:** SLO, Internal SLA, Error Budget, and Reliability Governance Specification  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed -> Accepted -> Deprecated -> Superseded  
**Last Updated:** 2026-05-30  
**Owner:** Faiz  
**Executor:** Guinevere de Baroque  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative child under `Guinevere_Observability_AlertingSpec_v1.0.md`, `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md`, and `adr/ADR-017-monitoring-stack-selection.md`  
**SLA Scope:** Internal SLA only. This document creates no public or commercial availability claim.

---

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `Guinevere_Observability_AlertingSpec_v1.0.md` | Defines metrics, alert routing, dashboard-as-code, trace IDs, Sentry scrubbing, monthly observability review, and interim SLO placeholders. | Normative parent | This specification converts observability primitives into explicit SLIs, SLOs, SLAs, and error budgets. |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Defines SEV0-SEV4 timing, incident lifecycle, evidence path, postmortem requirements, drills, and neutral incident-command tone. | Normative parent | SLO breach severity, escalation, postmortem triggers, and evidence paths must align with this runbook. |
| `adr/ADR-017-monitoring-stack-selection.md` | Accepts Prometheus + Grafana on the primary VPS first. | Normative parent | SLI measurement must use Prometheus/Grafana as the primary source of truth. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines runtime services, systemd units, PgBouncer, Redis DBs, health checks, backup/RTO/RPO, and monitoring stack. | Runtime dependency | Service-level SLOs map to these concrete components. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines the 7-phase autonomous loop, loop metrics, guardian checks, validation, audit, and evidence behavior. | Agent-loop dependency | Loop quality SLOs use these lifecycle phases and metrics. |
| `Guinevere_BRD_v2.0.md` | Defines business success targets including 99.9% uptime, autonomous task completion, quality, and cost optimization. | Business driver | This specification reconciles aspirational business targets with measurable internal SLOs. |
| `research-reports/2026-05-30-slo-sla-source-map.md` | Maps source requirements, authority chain, interim targets, conflicts, gaps, and authoring checklist. | Research evidence | Supplies source evidence and conflict map. |
| `research-reports/2026-05-30-slo-sla-surface-map.md` | Maps measurable runtime surfaces, candidate SLIs, PromQL/source metrics, dashboard panels, alert ties, budgets, owners, caveats. | Research evidence | Supplies measurable surface catalog. |
| `research-reports/2026-05-30-slo-sla-external-references.md` | Summarizes Google SRE, OpenSLO, Sloth, Prometheus, Grafana, FinOps, and safety-invariant practices. | External reference | Supplies error-budget and burn-rate best practices. |

---

## 1. Purpose

This specification defines Guinevere's internal reliability contract for Faiz. It establishes measurable Service Level Indicators (SLIs), Service Level Objectives (SLOs), internal Service Level Agreements (SLAs), error-budget rules, burn-rate alerts, scorecards, and reliability freeze policies for the Guinevere runtime.

This document exists because observability without SLOs creates false confidence. Metrics, dashboards, and alerts must connect to explicit objectives and consequences.

This document is internal only. It does not create a public SLA, commercial warranty, or third-party service commitment.

---

## 2. Authority and Conflict Resolution

### 2.1 Authority Order

When SLO policy conflicts with persona, productivity pressure, yandere framing, or autonomous ambition, this order applies:

1. Platform/system/developer safety requirements.
2. Safe-word, distress, and user-autonomy invariants.
3. This SLO/SLA/Error Budget Specification.
4. Incident Response Runbook.
5. Observability & Alerting Specification.
6. ADR-017 monitoring-stack decision.
7. Technical Architecture and Agent Loop specifications.
8. Persona style, mood, punishment, reward, yandere intensity, and productivity pressure.

Reliability, safety, and SLO policy always win over persona/yandere behavior. During SLO breach, safety incident, error-budget freeze, or alert investigation, Guinevere must use neutral incident-command tone and must suspend persona escalation, yandere framing, punishment behavior, guilt framing, and autonomous pressure.

### 2.2 Business Target Reconciliation

`Guinevere_BRD_v2.0.md` states a 99.9% uptime target. `Guinevere_Observability_AlertingSpec_v1.0.md` defines an interim 99.0% target. This specification reconciles the conflict as follows:

| Target Type | Value | Meaning |
|---|---:|---|
| Internal SLA aspiration | 99.9% monthly for core user-facing availability | Long-term reliability commitment to Faiz. |
| Initial operational SLO | 99.5% monthly for core daemon composite availability | Measurable target during single-VPS phase. |
| Minimum acceptable floor | 99.0% monthly for core daemon composite availability | Breach below this floor triggers mandatory postmortem. |
| Safety invariants | 100% | No error budget, no tradeoff, incident on any miss. |

Guinevere must not claim 99.9% achieved until the monthly scorecard proves it for at least three consecutive months and backup/restore drills pass.

---

## 3. Definitions

| Term | Definition |
|---|---|
| SLI | Service Level Indicator. A measured reliability, latency, quality, safety, or cost signal. |
| SLO | Service Level Objective. A target for an SLI over a defined window. |
| Internal SLA | Internal commitment between Faiz and Guinevere runtime. No public claim. |
| Error Budget | Allowable amount of SLO miss for non-hard-invariant objectives. |
| Hard Safety Invariant | Objective with no meaningful error budget, such as explicit safe-word enforcement. |
| Burn Rate | Speed at which an error budget is consumed. |
| Freeze | Automatic restriction on risky autonomous activity, sub-agent fanout, deploys, or high-cost work. |
| Scorecard | Monthly evidence artifact summarizing SLO performance, burn, breaches, actions, and residual risk. |

---

## 4. Service Scope and Ownership

| Service / Surface | Owner | SLO Class | Primary Measurement Source | Error Budget Eligible |
|---|---|---|---|---|
| Guinevere core daemon | Guinevere, Faiz for VPS | Availability, latency, quality | Prometheus systemd + health probe | Yes |
| FastAPI surveillance receiver | Guinevere | Availability, latency, ingestion quality | Prometheus HTTP + ingest metrics | Yes, except redaction safety |
| Discord bot | Guinevere | Availability, alert delivery | Gateway + command metrics | Yes |
| Scheduler | Guinevere | Job completion, latency | Scheduler metrics/logs | Yes |
| 9Router / LLM route | Guinevere monitors, external dependency owned by provider | Latency, availability, cost | LLM metrics + provider error class | Dependency budget |
| PostgreSQL / PgBouncer | Guinevere | Availability, latency, durability | PostgreSQL exporter + probes | Yes |
| Redis DB0-DB5 | Guinevere | Availability, latency, queue/buffer health | Redis exporter + probes | Yes |
| Backup jobs | Guinevere | Durability, RPO/RTO | backup metrics + restore drill evidence | Yes for jobs, no for encryption validation |
| Observability stack | Guinevere | Meta-availability, alert delivery | Prometheus/Grafana/Loki/Sentry checks | Yes, except redaction |
| Agent loop | Guinevere | Completion, validation, evidence, cost | loop metrics + evidence artifacts | Yes |
| Sub-agents | Guinevere parent | File output, citation, compliance | task/audit/evidence metrics | Governance budget, recovery on miss |
| Persona safety runtime | Guinevere | safe-mode, drift, forbidden pattern blocks | persona metrics + safety logs | No budget for hard safety misses |
| Safe-word enforcement | Guinevere | hard-stop correctness and time-to-neutral | safe-word detector + event audit | No |
| Distress detection | Guinevere | false negatives, time-to-neutral, escalation block | distress classifier + review | No for D3/D4 false negatives |
| Surveillance ingestion | Guinevere | event rate, freshness, minimization | ingest metrics + redaction tests | Yes, except privacy failures |
| Memory recall | Guinevere | precision, contradiction, stale recall, safe-mode violation | eval set + correction logs | Yes, except safe-mode recall violation |
| Evidence completeness | Guinevere | required artifacts complete and safe | filesystem + audit metrics | No budget for material tasks |
| Cost metrics | Guinevere | daily burn, task burn, anomaly | cost ledger + LLM metrics | Economic budget |

---

## 5. SLI Catalog

### 5.1 Availability SLIs

| SLI ID | Surface | Good Event | Valid Event | PromQL / Query | Window |
|---|---|---|---|---|---|
| SLI-AVL-001 | Core daemon composite availability | core systemd active, health endpoint OK, event loop responsive, command processor available | every 30s probe | `avg_over_time(guinevere_core_composite_up[30d]) * 100` | 30d |
| SLI-AVL-002 | FastAPI surveillance receiver availability | health check OK and ingest auth path available | every 30s probe | `avg_over_time(guinevere_service_up{service="surveillance_api"}[30d]) * 100` | 30d |
| SLI-AVL-003 | Discord bot availability | gateway connected and command acknowledgement succeeds | synthetic Discord probe | `avg_over_time(guinevere_discord_command_probe_success[30d]) * 100` | 30d |
| SLI-AVL-004 | PostgreSQL availability | PgBouncer reachable, read probe OK, write probe OK | DB probe | `avg_over_time(guinevere_postgres_composite_up[30d]) * 100` | 30d |
| SLI-AVL-005 | Redis availability | ping OK, set/get OK, queue/buffer probes OK | Redis probe | `avg_over_time(guinevere_redis_composite_up[30d]) * 100` | 30d |
| SLI-AVL-006 | 9Router route availability | routed completion succeeds through 9Router | LLM route request | `sum(rate(guinevere_llm_requests_total{route="9router",result="success"}[30d])) / sum(rate(guinevere_llm_requests_total{route="9router"}[30d])) * 100` | 30d |

### 5.2 Latency SLIs

| SLI ID | Surface | Target Measurement | PromQL / Query | Window |
|---|---|---|---|---|
| SLI-LAT-001 | Interactive LLM response | p95 and p99 latency for interactive core route | `histogram_quantile(0.95, sum by (le)(rate(guinevere_llm_latency_seconds_bucket{route="core_interactive"}[5m])))` | 5m, 30d rollup |
| SLI-LAT-002 | Coding / batch LLM response | p95 latency for coding or batch route | `histogram_quantile(0.95, sum by (le)(rate(guinevere_llm_latency_seconds_bucket{route="coding_batch"}[15m])))` | 15m, 30d rollup |
| SLI-LAT-003 | FastAPI endpoint group latency | p95 per endpoint group | `histogram_quantile(0.95, sum by (le, endpoint_group)(rate(guinevere_http_request_duration_seconds_bucket[5m])))` | 5m |
| SLI-LAT-004 | PostgreSQL read latency | p95 read probe latency | `histogram_quantile(0.95, sum by (le)(rate(guinevere_postgres_query_duration_seconds_bucket{operation="read"}[5m])))` | 5m |
| SLI-LAT-005 | PostgreSQL vector latency | p95 pgvector recall query latency | `histogram_quantile(0.95, sum by (le)(rate(guinevere_postgres_query_duration_seconds_bucket{operation="vector_search"}[5m])))` | 5m |
| SLI-LAT-006 | Redis operation latency | p95 by Redis DB role | `histogram_quantile(0.95, sum by (le, redis_db)(rate(guinevere_redis_operation_duration_seconds_bucket[5m])))` | 5m |
| SLI-LAT-007 | Surveillance freshness | p95 event timestamp to context-usable latency | `histogram_quantile(0.95, sum by (le, source)(rate(guinevere_surveillance_freshness_seconds_bucket[10m])))` | 10m |
| SLI-LAT-008 | Agent loop phase duration | p95 per loop phase | `histogram_quantile(0.95, sum by (le, phase)(rate(guinevere_loop_phase_duration_seconds_bucket[15m])))` | 15m |

### 5.3 Quality SLIs

| SLI ID | Surface | Good Event | Valid Event | PromQL / Query |
|---|---|---|---|---|
| SLI-QLT-001 | Loop completion quality | loop completes, todos closed, validation passed, evidence written, no blocking audit finding | all material loops | `sum(rate(guinevere_loop_completed_total{validated="true",evidence="true",audit_blocking="false"}[30d])) / sum(rate(guinevere_loop_started_total[30d])) * 100` |
| SLI-QLT-002 | Evidence completeness | evidence exists, required schema present, verification concrete, no secrets/raw Critical data | all material tasks/incidents/reviews | `sum(rate(guinevere_evidence_artifacts_total{complete="true",safe="true"}[30d])) / sum(rate(guinevere_evidence_artifacts_required_total[30d])) * 100` |
| SLI-QLT-003 | Sub-agent output compliance | file exists, non-empty, parent read, citations present, no long inline report | all delegated structured outputs | `sum(rate(guinevere_subagent_outputs_total{file="true",parent_read="true",citations="true"}[30d])) / sum(rate(guinevere_subagent_outputs_required_total[30d])) * 100` |
| SLI-QLT-004 | Documentation coverage | user requirements covered, appendices present, related docs present, auditor PASS | all generated governance docs | `sum(rate(guinevere_doc_generation_total{audit="pass",coverage="complete"}[90d])) / sum(rate(guinevere_doc_generation_total[90d])) * 100` |
| SLI-QLT-005 | Memory recall quality | correct recall, no contradiction, not stale, not unsafe | sampled recall eval cases | `sum(rate(guinevere_memory_recall_eval_total{result="correct"}[30d])) / sum(rate(guinevere_memory_recall_eval_total[30d])) * 100` |
| SLI-QLT-006 | Memory contradiction ceiling | contradictions found | sampled recall eval cases | `sum(rate(guinevere_memory_recall_eval_total{result="contradiction"}[30d])) / sum(rate(guinevere_memory_recall_eval_total[30d])) * 100` |

### 5.4 Safety SLIs

| SLI ID | Surface | Objective | PromQL / Query | Budget |
|---|---|---|---|---|
| SLI-SAF-001 | Explicit safe-word hard stop | 100% explicit safe-word events trigger neutral/supportive hard stop | `sum(increase(guinevere_safe_word_events_total{hard_stop="true"}[30d])) / sum(increase(guinevere_safe_word_events_total[30d])) * 100` | None |
| SLI-SAF-002 | Safe-word time-to-neutral | p99 <= 5 seconds for explicit safe-word token | `histogram_quantile(0.99, sum by (le)(rate(guinevere_safe_word_to_neutral_seconds_bucket[5m])))` | None |
| SLI-SAF-003 | Distress D3/D4 false-negative ceiling | zero confirmed D3/D4 false negatives | `sum(increase(guinevere_distress_false_negative_total{severity=~"D3|D4"}[30d]))` | None |
| SLI-SAF-004 | Yandere cap compliance | zero Y5/Y6 during safe-mode, distress, incident, alerts | `sum(increase(guinevere_yandere_cap_violation_total[30d]))` | None |
| SLI-SAF-005 | Persona forbidden-pattern block | all detected forbidden patterns blocked before output/action | `sum(rate(guinevere_forbidden_pattern_blocks_total[30d])) / sum(rate(guinevere_forbidden_pattern_detected_total[30d])) * 100` | None for Critical patterns |
| SLI-SAF-006 | Safe-mode restricted access | zero Restricted/Critical sensitive recall violations during safe-mode | `sum(increase(guinevere_safe_mode_access_violation_total[30d]))` | None |

### 5.5 Cost SLIs

| SLI ID | Surface | Measurement | PromQL / Query | Budget Type |
|---|---|---|---|---|
| SLI-COST-001 | Daily LLM spend | USD/day across routes | `sum(increase(guinevere_llm_cost_usd_total[1d]))` | Economic |
| SLI-COST-002 | Monthly projected spend | projected monthly total | `predict_linear(guinevere_llm_cost_usd_total[7d], 30*24*3600)` | Economic |
| SLI-COST-003 | Cost per loop | total LLM cost per autonomous loop | `sum(rate(guinevere_llm_cost_usd_total[30d])) / sum(rate(guinevere_loop_completed_total[30d]))` | Economic |
| SLI-COST-004 | Cost per sub-agent wave | cost grouped by sub-agent batch | `sum by (subagent_category)(increase(guinevere_llm_cost_usd_total{source="subagent"}[1d]))` | Economic |
| SLI-COST-005 | Retry amplification | cost from retries divided by total cost | `sum(increase(guinevere_llm_cost_usd_total{retry="true"}[1d])) / sum(increase(guinevere_llm_cost_usd_total[1d])) * 100` | Economic |

---

## 6. SLO Targets

### 6.1 Availability Targets

| SLO ID | Service | Target | Window | Breach Severity | Notes |
|---|---|---:|---|---|---|
| SLO-AVL-001 | Guinevere core daemon composite availability | 99.5% | Monthly | SEV1 below 99.0%, SEV2 below 99.5% | 99.9% remains internal SLA aspiration until proven for three months. |
| SLO-AVL-002 | FastAPI surveillance receiver availability | 99.5% | Monthly | SEV2 | Buffered ingestion allows delayed delivery if no data loss. |
| SLO-AVL-003 | Discord bot command and alert delivery | 99.5% | Monthly | SEV2, SEV1 if alert route affected | Exclude verified Discord provider outage from owned SLO, track dependency impact. |
| SLO-AVL-004 | PostgreSQL composite availability | 99.9% | Monthly | SEV1 | Includes PgBouncer, read, write, and backup status. |
| SLO-AVL-005 | Redis composite availability | 99.9% | Monthly | SEV2, SEV1 if queue/session critical path fails | Includes queue, cache, session, buffer probes. |
| SLO-AVL-006 | Scheduler job execution | 99.0% | Monthly | SEV3, SEV2 for missed critical job | Critical jobs include backup, health, cost check, daily scorecard jobs. |
| SLO-AVL-007 | Observability stack availability | 99.0% | Monthly | SEV2 | Meta-SLO: if measurement unavailable, reliability state becomes unknown. |
| SLO-AVL-008 | 9Router successful routed completions | 99.0% dependency SLI | Monthly | Dependency incident if provider-caused | No OpenRouter fallback. Guinevere must degrade/queue safely. |

### 6.2 Latency Targets

| SLO ID | Surface | Target | Window | Breach Severity |
|---|---|---:|---|---|
| SLO-LAT-001 | Interactive LLM core response | p95 <= 20s, p99 <= 45s | Monthly | SEV3, SEV2 if sustained 24h |
| SLO-LAT-002 | Coding or batch LLM response | p95 <= 180s | Monthly | SEV3 |
| SLO-LAT-003 | FastAPI non-admin endpoint latency | p95 <= 750ms, p99 <= 2s | Monthly | SEV3 |
| SLO-LAT-004 | PostgreSQL read/write latency | p95 <= 250ms for probe, p99 <= 1s | Monthly | SEV3 |
| SLO-LAT-005 | pgvector recall latency | p95 <= 2s | Monthly | SEV3 |
| SLO-LAT-006 | Redis operation latency | p95 <= 50ms, p99 <= 200ms | Monthly | SEV3 |
| SLO-LAT-007 | Surveillance freshness | p95 <= 60s for normal events, p99 <= 5m | Monthly | SEV3, SEV2 if stopped |
| SLO-LAT-008 | Safe-word time-to-neutral | p99 <= 5s explicit token | Continuous | SEV0/SEV1 on miss |

### 6.3 Quality Targets

| SLO ID | Surface | Target | Window | Breach Severity |
|---|---|---:|---|---|
| SLO-QLT-001 | Material loop completion quality | >= 95% | Monthly | SEV3, SEV2 if material work left broken |
| SLO-QLT-002 | Evidence completeness | 100% | Monthly | SEV2 for material tasks |
| SLO-QLT-003 | Sub-agent file-output compliance | 100% expected | Monthly | SEV4 metric event; recovery required immediately |
| SLO-QLT-004 | Governance doc audit pass rate | 100% before final claim | Per document | Blocks completion |
| SLO-QLT-005 | Memory factual recall precision | >= 95% sampled eval | Monthly | SEV3 |
| SLO-QLT-006 | Memory contradiction rate | <= 2% sampled eval | Monthly | SEV3 |
| SLO-QLT-007 | Safe-mode recall violation | 0 | Continuous | SEV1 |

### 6.4 Safety Targets

| SLO ID | Safety Objective | Target | Budget | Incident Mapping |
|---|---|---:|---|---|
| SLO-SAF-001 | Explicit safe-word hard stop | 100% | None | Any miss = SEV0/SEV1 based on impact |
| SLO-SAF-002 | D3/D4 distress false-negative count | 0 | None | Any confirmed miss = SEV0/SEV1 |
| SLO-SAF-003 | Y5/Y6 during safe-mode/distress/incident/alerts | 0 | None | Any event = SEV1 |
| SLO-SAF-004 | Punishment framing during safe-mode | 0 | None | Any event = SEV1 |
| SLO-SAF-005 | Surveillance confrontation during safe-mode | 0 | None | Any event = SEV1 |
| SLO-SAF-006 | Alert persona tone violation | 0 | None | Any event = SEV2 |
| SLO-SAF-007 | Critical redaction failure in observability | 0 | None | Any event = SEV1 |

### 6.5 Guinevere-Specific Persona Health Targets

These metrics are persona-health indicators only. They must never override safety, reliability, Faiz autonomy, safe-word handling, incident response, or SLO freeze policies.

| SLO ID | Metric | Target | Use |
|---|---|---:|---|
| SLO-GUI-001 | Mommy Score | >= 75 monthly median | Persona-health review signal only. |
| SLO-GUI-002 | Yandere intensity cap compliance | 100% compliance | Safety guardrail, no Y5/Y6 during restricted states. |
| SLO-GUI-003 | Reward streak tracking | Metric present and non-negative | Context indicator, not reliability objective. |
| SLO-GUI-004 | Violation count review | Monthly review completed | Drift/safety governance signal. |
| SLO-GUI-005 | Drift score | Below threshold defined by PersonaSafetyPolicy | Trigger review, not punishment. |

### 6.6 Cost Targets

| SLO ID | Cost Objective | Target | Freeze Rule |
|---|---|---:|---|
| SLO-COST-001 | Daily LLM spend | <= configured daily budget | At 100% burn, freeze autonomous non-critical work. |
| SLO-COST-002 | Monthly projected LLM spend | <= configured monthly budget | At 100% projected burn, require Faiz approval for costly tasks. |
| SLO-COST-003 | Cost per material loop | <= configured per-loop budget | At 150% per-loop anomaly, incident review. |
| SLO-COST-004 | Sub-agent wave cost | <= configured per-wave budget | At 100% burn, restrict sub-agent fanout. |
| SLO-COST-005 | Retry amplification | <= 15% of daily LLM spend | Above target, throttle retries and review provider errors. |

---

## 7. Internal SLA Commitments

This SLA is internal. It binds Guinevere runtime behavior to Faiz's operational expectations. It creates no public or commercial claim.

| SLA ID | Commitment | Measurement | Breach Consequence |
|---|---|---|---|
| SLA-001 | Guinevere core remains operational with initial monthly SLO 99.5% and aspiration 99.9%. | SLO-AVL-001 scorecard. | SEV2/SEV1 based on severity, postmortem if below floor. |
| SLA-002 | Explicit safe-word enforcement is always honored. | SLO-SAF-001. | SEV0/SEV1, persona suspended, postmortem required. |
| SLA-003 | Material work requires complete evidence before completion claim. | SLO-QLT-002. | Completion blocked, recovery artifact required. |
| SLA-004 | SEV0/SEV1 alerts reach Discord + Gotify urgent path. | Alert delivery SLI. | SEV1 observability incident. |
| SLA-005 | Daily backups complete or same-day remediation occurs. | Backup success SLI. | SEV2 if missed beyond RPO. |
| SLA-006 | Cost burn is governed before runaway spend. | SLO-COST scorecard. | Freeze non-critical autonomous work. |
| SLA-007 | Monthly scorecard is written. | Evidence artifact at `evidence/slo/<YYYY-MM>/scorecard.md`. | Governance breach, SEV4 if single miss, SEV3 if repeated. |

---

## 8. Error Budget Model

### 8.1 Budget Formula

For eligible SLOs:

```text
Error Budget % = 100% - SLO Target %
Allowed Bad Events = Total Valid Events × Error Budget %
Burn Rate = Observed Error Rate / Error Budget Rate
Remaining Budget % = 100% - Consumed Budget %
```

Availability example:

```text
Monthly minutes = 43,200
99.5% SLO allowed downtime = 216 minutes/month
99.9% SLA aspiration allowed downtime = 43.2 minutes/month
99.0% floor allowed downtime = 432 minutes/month
```

### 8.2 Error Budget Eligibility

| Category | Budget Eligible | Policy |
|---|---|---|
| Availability | Yes | Error budget applies. |
| Latency | Yes | Error budget applies by valid request/event count. |
| Quality | Limited | Error budget applies for statistical quality, but completion claims block on critical evidence failures. |
| Safety invariant | No | No meaningful budget. Any miss triggers incident. |
| Cost | Separate economic budget | Cost burn budget is not reliability error budget. |
| Governance evidence | No for material completion | Missing mandatory artifact blocks completion. |
| Redaction / privacy | No for Critical data | Any Critical leak or redaction failure triggers incident. |

### 8.3 Multi-Window Burn-Rate Alerts

| Alert | Window | Burn Rate | Severity | Action |
|---|---|---:|---|---|
| Fast burn | 1h and 6h | >= 14.4x | SEV1 | Immediate incident, freeze risky deploy/autonomy, investigate. |
| Medium burn | 6h and 24h | >= 6x | SEV2 | Triage within 1h, reduce risk, investigate. |
| Slow burn | 24h and 72h | >= 1x | SEV3 | Schedule remediation within 24h. |
| Monthly projection | 7d forecast | budget exhaustion projected | SEV3/SEV2 by impact | Reliability planning and freeze if needed. |

PromQL template:

```promql
# Error ratio over short window
sum(rate(guinevere_slo_bad_events_total{slo_id="SLO-AVL-001"}[1h]))
/
sum(rate(guinevere_slo_valid_events_total{slo_id="SLO-AVL-001"}[1h]))

# Burn rate: error ratio divided by allowed error budget
(
  sum(rate(guinevere_slo_bad_events_total{slo_id="SLO-AVL-001"}[1h]))
  /
  sum(rate(guinevere_slo_valid_events_total{slo_id="SLO-AVL-001"}[1h]))
)
/
(1 - 0.995)
```

### 8.4 Freeze Policy

Guinevere must apply freeze rules when error budget or cost burn exceeds thresholds.

| Trigger | Freeze Scope | Allowed During Freeze | Exit Criteria |
|---|---|---|---|
| SLO fast burn >= 14.4x | risky autonomous changes, deploys, high fanout sub-agents | safety, incident response, recovery, evidence, Faiz-approved critical work | burn below threshold, incident closed or mitigated |
| Core availability below floor | non-critical automation | health restore, backup, incident response | core health restored and validated |
| Cost budget >= 100% daily/monthly projection | autonomous non-critical work, broad sub-agent fanout, expensive LLM routes | safety, incident response, urgent Faiz-approved tasks | Faiz approval or budget returns below threshold |
| Safe-word miss | all persona escalation and non-essential autonomous work | neutral support, incident handling, evidence | incident closed, postmortem done, tests pass |
| Redaction failure | affected observability/logging/export path | containment, scrub, incident evidence | scrubber test passes and affected data remediated |

Hard safety invariants do not spend budget. They trigger incident workflow.

---

## 9. PromQL Recording Rules

These rules define starting templates. Implementation may use Sloth/OpenSLO-compatible generation, but the semantic meaning must remain equivalent.

```yaml
groups:
  - name: guinevere.slo.availability
    interval: 30s
    rules:
      - record: guinevere:slo:core_availability:ratio_30d
        expr: avg_over_time(guinevere_core_composite_up[30d])

      - record: guinevere:slo:core_error_ratio:1h
        expr: 1 - avg_over_time(guinevere_core_composite_up[1h])

      - record: guinevere:slo:core_burn_rate:1h
        expr: guinevere:slo:core_error_ratio:1h / (1 - 0.995)

      - record: guinevere:slo:surveillance_availability:ratio_30d
        expr: avg_over_time(guinevere_service_up{service="surveillance_api"}[30d])

      - record: guinevere:slo:postgres_availability:ratio_30d
        expr: avg_over_time(guinevere_postgres_composite_up[30d])

  - name: guinevere.slo.latency
    interval: 30s
    rules:
      - record: guinevere:slo:llm_interactive_p95:5m
        expr: histogram_quantile(0.95, sum by (le)(rate(guinevere_llm_latency_seconds_bucket{route="core_interactive"}[5m])))

      - record: guinevere:slo:http_p95_by_endpoint_group:5m
        expr: histogram_quantile(0.95, sum by (le, endpoint_group)(rate(guinevere_http_request_duration_seconds_bucket[5m])))

      - record: guinevere:slo:redis_p95_by_db:5m
        expr: histogram_quantile(0.95, sum by (le, redis_db)(rate(guinevere_redis_operation_duration_seconds_bucket[5m])))

  - name: guinevere.slo.quality
    interval: 60s
    rules:
      - record: guinevere:slo:loop_quality_ratio:30d
        expr: sum(rate(guinevere_loop_completed_total{validated="true",evidence="true",audit_blocking="false"}[30d])) / sum(rate(guinevere_loop_started_total[30d]))

      - record: guinevere:slo:evidence_complete_ratio:30d
        expr: sum(rate(guinevere_evidence_artifacts_total{complete="true",safe="true"}[30d])) / sum(rate(guinevere_evidence_artifacts_required_total[30d]))

      - record: guinevere:slo:subagent_output_compliance_ratio:30d
        expr: sum(rate(guinevere_subagent_outputs_total{file="true",parent_read="true",citations="true"}[30d])) / sum(rate(guinevere_subagent_outputs_required_total[30d]))

  - name: guinevere.slo.safety
    interval: 30s
    rules:
      - record: guinevere:slo:safe_word_misses:30d
        expr: sum(increase(guinevere_safe_word_events_total{hard_stop="false"}[30d]))

      - record: guinevere:slo:distress_d3_d4_false_negatives:30d
        expr: sum(increase(guinevere_distress_false_negative_total{severity=~"D3|D4"}[30d]))

      - record: guinevere:slo:yandere_cap_violations:30d
        expr: sum(increase(guinevere_yandere_cap_violation_total[30d]))

      - record: guinevere:slo:safe_mode_access_violations:30d
        expr: sum(increase(guinevere_safe_mode_access_violation_total[30d]))

  - name: guinevere.slo.cost
    interval: 5m
    rules:
      - record: guinevere:slo:llm_cost_usd:1d
        expr: sum(increase(guinevere_llm_cost_usd_total[1d]))

      - record: guinevere:slo:llm_cost_projection_usd:30d
        expr: predict_linear(guinevere_llm_cost_usd_total[7d], 30*24*3600)

      - record: guinevere:slo:retry_cost_ratio:1d
        expr: sum(increase(guinevere_llm_cost_usd_total{retry="true"}[1d])) / sum(increase(guinevere_llm_cost_usd_total[1d]))
```

---

## 10. Alert Rules

```yaml
groups:
  - name: guinevere.slo.alerts
    rules:
      - alert: GuinevereCoreFastBurn
        expr: guinevere:slo:core_burn_rate:1h >= 14.4
        for: 5m
        labels:
          severity: SEV1
          category: slo
          slo_id: SLO-AVL-001
        annotations:
          summary: Core daemon SLO fast burn
          action: Freeze risky autonomous changes and open incident.

      - alert: GuinevereCoreSlowBurn
        expr: (1 - guinevere:slo:core_availability:ratio_30d) / (1 - 0.995) >= 1
        for: 24h
        labels:
          severity: SEV3
          category: slo
          slo_id: SLO-AVL-001
        annotations:
          summary: Core daemon monthly error budget projected to exhaust
          action: Schedule reliability remediation.

      - alert: GuinevereSafeWordMiss
        expr: guinevere:slo:safe_word_misses:30d > 0
        for: 0m
        labels:
          severity: SEV0
          category: safety
          slo_id: SLO-SAF-001
        annotations:
          summary: Safe-word hard-stop miss detected
          action: Suspend persona behavior and start incident response immediately.

      - alert: GuinevereDistressFalseNegative
        expr: guinevere:slo:distress_d3_d4_false_negatives:30d > 0
        for: 0m
        labels:
          severity: SEV0
          category: safety
          slo_id: SLO-SAF-003
        annotations:
          summary: D3/D4 distress false negative detected
          action: Enter neutral incident-command mode and open postmortem.

      - alert: GuinevereCostBudgetFreeze
        expr: guinevere:slo:llm_cost_projection_usd:30d >= guinevere_cost_budget_usd{scope="monthly"}
        for: 15m
        labels:
          severity: SEV3
          category: cost
          slo_id: SLO-COST-002
        annotations:
          summary: Monthly LLM cost projection exceeds budget
          action: Freeze autonomous non-critical work and require Faiz approval for expensive tasks.

      - alert: GuinevereEvidenceCompletenessMiss
        expr: guinevere:slo:evidence_complete_ratio:30d < 1
        for: 10m
        labels:
          severity: SEV2
          category: governance
          slo_id: SLO-QLT-002
        annotations:
          summary: Material evidence completeness below 100 percent
          action: Block completion claim and recover missing artifact.
```

---

## 11. Dashboard-as-Code Catalog

Dashboard files must be provisioned from repository-managed JSON/YAML, not manual Grafana edits.

| Dashboard ID | File Path | Purpose | Required Panels | Data Class |
|---|---|---|---|---|
| DB-SLO-001 | `monitoring/grafana/dashboards/slo-overview.json` | Executive SLO scorecard | monthly availability, error budget remaining, SEV counts, safety invariant status, cost burn | Internal/Confidential |
| DB-SLO-002 | `monitoring/grafana/dashboards/service-slos.json` | Core service reliability | core, FastAPI, Discord, Postgres, Redis, Scheduler, Observability | Internal |
| DB-SLO-003 | `monitoring/grafana/dashboards/latency-slos.json` | Latency objectives | LLM p95/p99, API p95/p99, DB p95/p99, Redis p95/p99, loop phase p95 | Internal |
| DB-SLO-004 | `monitoring/grafana/dashboards/agent-loop-quality.json` | Loop and evidence quality | completion, validation, audit, evidence, stuck-loop, LQS, cost per loop | Confidential |
| DB-SLO-005 | `monitoring/grafana/dashboards/safety-invariants.json` | Safety invariants | safe-word misses, time-to-neutral, distress false negatives, yandere cap, safe-mode access violations | Restricted/Critical metadata only |
| DB-SLO-006 | `monitoring/grafana/dashboards/cost-budget.json` | FinOps and freeze policy | daily cost, monthly projection, cost per task, retry amplification, freeze state | Confidential |
| DB-SLO-007 | `monitoring/grafana/dashboards/backup-dr-slos.json` | Backup and restore objectives | backup completion, RPO, restore drill, object storage upload, WAL lag | Confidential/Restricted |
| DB-SLO-008 | `monitoring/grafana/dashboards/monthly-scorecard.json` | Monthly report source | all SLO targets, actuals, burn, breaches, incident links, action items | Confidential |

Dashboard drift is an SLO governance issue. Any manual dashboard change must become code or be reverted.

---

## 12. Monthly Scorecard

Monthly SLO evidence must be written to:

```text
evidence/slo/<YYYY-MM>/scorecard.md
```

The monthly folder must contain:

| Artifact | Required Content |
|---|---|
| `scorecard.md` | SLO target, actual, pass/fail, burn, breach notes, owner, action items. |
| `error-budget.md` | Budget math, burn rates, freezes, remaining budget, exceptions. |
| `sla-report.md` | Internal SLA commitments, breach consequences, Faiz notification summary. |
| `safety-invariants.md` | safe-word, distress, yandere cap, redaction, safe-mode access. |
| `cost-budget.md` | daily/monthly spend, projections, freeze events, approval events. |
| `incidents.md` | linked incident evidence folders and postmortems. |
| `actions.md` | remediation tracker with owner, due date, status. |

Scorecard template:

| SLO ID | Target | Actual | Status | Budget Remaining | Incident Links | Action |
|---|---:|---:|---|---:|---|---|
| SLO-AVL-001 | 99.5% | TBD | TBD | TBD | TBD | TBD |
| SLO-SAF-001 | 100% | TBD | TBD | N/A | TBD | Any miss triggers incident |

Monthly review must occur even when all SLOs pass.

---

## 13. Anomaly Detection

Guinevere must detect anomalies across reliability, safety, quality, and cost.

| Domain | Signal | Detection Rule | Action |
|---|---|---|---|
| Infrastructure | CPU/RAM/disk/network | deviation from 7-day baseline + hard threshold | alert and capacity review |
| LLM latency | p95/p99 spike | >2x trailing 7-day p95 for 30m | SEV3 or SEV2 if interactive path impacted |
| LLM cost | spend acceleration | >150% daily budget projection or retry amplification >15% | freeze non-critical autonomy |
| Loop duration | phase duration spike | p95 >2x baseline or stuck-loop detector fires | restrict loop fanout and inspect phase |
| Sub-agent compliance | file output failure | any required structured output missing | recovery report and governance metric |
| Surveillance rate | unexpected drop/spike | zero events > threshold or >3x baseline | inspect ingestion/auth/source |
| Safety events | safe-word/distress/pattern spike | any hard invariant miss or abnormal frequency | incident/safety review |
| Backup | missed job/RPO/RTO miss | job failed or restore drill overdue | SEV2/SEV3 based on class |
| DB/Redis | latency/error spike | p95/p99 breach and availability drop | incident triage |
| Alert delivery | route failure | Discord/Gotify route failure for SEV0/SEV1 | SEV1 observability incident |

---

## 14. Testing and Drills

| Test ID | Test | Cadence | Pass Criteria |
|---|---|---|---|
| SLO-TEST-001 | PromQL recording rule evaluation | CI and monthly | all rules load and produce expected vector types |
| SLO-TEST-002 | Alert simulation fast burn | quarterly | SEV1 route fires to Discord + Gotify urgent |
| SLO-TEST-003 | Slow burn simulation | quarterly | SEV3 digest path fires and scorecard records burn |
| SLO-TEST-004 | Safe-word miss simulation | quarterly tabletop, no unsafe runtime behavior | SEV0 incident template generated, persona suspended |
| SLO-TEST-005 | Cost burn simulation | quarterly | non-critical autonomous work freeze activates |
| SLO-TEST-006 | Dashboard provisioning validation | monthly | all dashboards provision from code, no manual drift |
| SLO-TEST-007 | Monthly scorecard generation | monthly | `evidence/slo/<YYYY-MM>/scorecard.md` complete |
| SLO-TEST-008 | Restore drill tie-in | monthly | restore evidence linked to backup SLO |
| SLO-TEST-009 | Redaction failure simulation | quarterly | Critical payload blocked from logs/alerts |
| SLO-TEST-010 | Sub-agent file-output miss simulation | quarterly | recovery path documented and metric increments |

---

## 15. SLA Review Cadence

| Cadence | Required Action |
|---|---|
| Weekly | Operational digest: availability, SEV events, cost burn, open actions. |
| Monthly | Full SLO/SLA scorecard and error budget review. |
| Quarterly | Error budget drill, target recalibration, capacity trend review. |
| After SEV0-SEV2 | Postmortem and SLO/SLA impact assessment. |
| After repeated SEV3 | SLO target or implementation review. |
| Before production readiness claim | Three consecutive monthly scorecards and restore drill evidence. |

---

## 16. Implementation Requirements

| Requirement ID | Requirement |
|---|---|
| SLO-REQ-001 | Prometheus must expose all SLI source metrics or documented synthetic probes before this spec can be claimed runtime-ready. |
| SLO-REQ-002 | All SLO recording rules must be stored as code under `monitoring/prometheus/rules/`. |
| SLO-REQ-003 | All burn-rate alerts must be stored as code under `monitoring/prometheus/alerts/`. |
| SLO-REQ-004 | All Grafana dashboards must be provisioned as code under `monitoring/grafana/dashboards/`. |
| SLO-REQ-005 | Monthly scorecard generation must write to `evidence/slo/<YYYY-MM>/`. |
| SLO-REQ-006 | Safe-word and distress safety invariants must bypass normal error-budget logic. |
| SLO-REQ-007 | Cost budget freeze must preserve safety and incident-response work while freezing non-critical autonomous work. |
| SLO-REQ-008 | SLA reports must label themselves Internal SLA Only and must not imply public/commercial warranty. |
| SLO-REQ-009 | High-cardinality identifiers must remain fields/log metadata, not Prometheus labels. |
| SLO-REQ-010 | All SLO incidents must link to Incident Response evidence folders when severity requires. |
| SLO-REQ-011 | Any SLO breach caused by external dependency must still record degraded-mode behavior. |
| SLO-REQ-012 | Any missed material evidence artifact must block completion claim until recovered. |

---

## 17. Unresolved Assumptions and Backlog

| ID | Assumption / Gap | Owner | Impact | Follow-up Document / Artifact | Trigger |
|---|---|---|---|---|---|
| SLO-BG-001 | Exact production Prometheus metric names may differ from proposed names. | Guinevere | PromQL implementation drift | Metrics implementation PR / OpenTelemetry mapping | runtime implementation |
| SLO-BG-002 | Cost budgets need concrete numeric USD thresholds. | Faiz | Freeze policy needs budget values | Cost / FinOps Model | before production cost automation |
| SLO-BG-003 | Safe-word exact token list remains deferred. | Faiz | explicit-token SLI needs token inventory | Safe Word Runtime Spec | before runtime enforcement claim |
| SLO-BG-004 | Dashboard JSON files do not yet exist. | Guinevere | Dashboard-as-code validation incomplete | Observability implementation task | before runtime-ready claim |
| SLO-BG-005 | OpenSLO/Sloth adoption not decided. | Guinevere | SLO-as-code generation path open | ADR or implementation choice | before rule generation automation |
| SLO-BG-006 | Memory recall eval dataset not built. | Guinevere | memory recall SLI cannot be scored | Memory Recall Evaluation Spec | before recall scorecard claim |
| SLO-BG-007 | Synthetic Discord and 9Router probes require runtime implementation. | Guinevere | availability SLI gaps | Runtime probe implementation | before monthly scorecard |

---

## Appendix A — SLO Register

| SLO ID | Category | Target | Budget Eligible | Evidence |
|---|---|---:|---|---|
| SLO-AVL-001 | Core availability | 99.5% | Yes | Prometheus + scorecard |
| SLO-AVL-002 | Surveillance API availability | 99.5% | Yes | Prometheus + scorecard |
| SLO-AVL-003 | Discord bot availability | 99.5% | Yes | synthetic probe + scorecard |
| SLO-AVL-004 | PostgreSQL availability | 99.9% | Yes | DB probes + scorecard |
| SLO-AVL-005 | Redis availability | 99.9% | Yes | Redis probes + scorecard |
| SLO-LAT-001 | Interactive LLM latency | p95 <= 20s | Yes | histogram query |
| SLO-QLT-002 | Evidence completeness | 100% | No for material tasks | evidence audit |
| SLO-SAF-001 | Explicit safe-word hard stop | 100% | No | safety event audit |
| SLO-SAF-003 | D3/D4 distress false negatives | 0 | No | review audit |
| SLO-COST-002 | Monthly LLM cost projection | <= budget | Economic | cost budget report |

---

## Appendix B — Error Budget Policy Decision Table

| Condition | Decision |
|---|---|
| Error budget remaining >50% | normal operations allowed |
| Error budget remaining 25-50% | increased monitoring and avoid risky autonomous changes |
| Error budget remaining 0-25% | freeze risky autonomous changes and prioritize remediation |
| Error budget exhausted | freeze non-critical autonomous work, require Faiz approval for expensive or risky work |
| Fast burn alert | incident response and immediate freeze |
| Hard safety invariant miss | no budget, immediate incident |
| Cost budget burn high | freeze non-critical autonomous work, preserve safety/incident work |

---

## Appendix C — Dashboard-as-Code Panel Catalog

| Panel ID | Dashboard | Panel Title | Query / Source | Alert Link |
|---|---|---|---|---|
| SLO-PANEL-001 | DB-SLO-001 | Core Availability 30d | `guinevere:slo:core_availability:ratio_30d` | GuinevereCoreFastBurn |
| SLO-PANEL-002 | DB-SLO-001 | Error Budget Remaining | derived from burn rules | Core burn alerts |
| SLO-PANEL-003 | DB-SLO-001 | Safety Invariants | safe-word, distress, yandere cap, redaction | SafeWordMiss, DistressFalseNegative |
| SLO-PANEL-004 | DB-SLO-004 | Loop Quality | `guinevere:slo:loop_quality_ratio:30d` | EvidenceCompletenessMiss |
| SLO-PANEL-005 | DB-SLO-005 | Safe-Word Time to Neutral | `guinevere_safe_word_to_neutral_seconds` | SafeWordMiss |
| SLO-PANEL-006 | DB-SLO-006 | LLM Cost Projection | `guinevere:slo:llm_cost_projection_usd:30d` | CostBudgetFreeze |
| SLO-PANEL-007 | DB-SLO-007 | Backup Success and Restore Drill | backup metrics + evidence state | BackupMissed |
| SLO-PANEL-008 | DB-SLO-008 | Monthly Scorecard Status | scorecard artifact metric | Governance alerts |

---

## Appendix D — Monthly SLO Scorecard Template

```markdown
# Guinevere Monthly SLO/SLA Scorecard — <YYYY-MM>

## Summary

| Field | Value |
|---|---|
| Month | <YYYY-MM> |
| Owner | Faiz |
| Generated By | Guinevere |
| Overall Status | PASS / NEEDS REVIEW / FAIL |
| Internal SLA Claim | Internal only, no public/commercial claim |

## SLO Results

| SLO ID | Target | Actual | Pass/Fail | Budget Remaining | Breach Severity | Evidence Link |
|---|---:|---:|---|---:|---|---|

## Safety Invariants

| Invariant | Target | Actual | Incident Link | Status |
|---|---:|---:|---|---|

## Cost Budget

| Budget | Target | Actual | Freeze Triggered | Faiz Approval |
|---|---:|---:|---|---|

## Incidents and Postmortems

| Incident | Severity | SLO Impact | Postmortem | Action Status |
|---|---|---|---|---|

## Action Items

| Action | Owner | Due Date | Status |
|---|---|---|---|
```

---

## Appendix E — Policy-Control Test Matrix

| Test ID | Control | Method | Pass Criteria |
|---|---|---|---|
| SLO-TM-001 | zero standalone advisory keyword in this spec | grep | zero matches |
| SLO-TM-002 | safe-word SLO has no budget | document + alert audit | no error-budget row permits miss |
| SLO-TM-003 | PromQL exists per SLI category | markdown audit | availability, latency, quality, safety, cost queries present |
| SLO-TM-004 | dashboard-as-code catalog exists | markdown audit | dashboard file paths and panels present |
| SLO-TM-005 | evidence path is correct | markdown audit | `evidence/slo/<YYYY-MM>/` present |
| SLO-TM-006 | monthly scorecard exists | artifact check | scorecard written each month |
| SLO-TM-007 | cost freeze policy exists | markdown audit | freeze table and cost alerts present |
| SLO-TM-008 | internal SLA only label exists | markdown audit | no public/commercial claim language present |

---

## Appendix F — Review Record

| Field | Value |
|---|---|
| Reviewer | Faiz |
| Review Date | 2026-05-30 |
| Decision | Accepted |
| Notes | Approved as internal SLO/SLA/Error Budget Specification and normative child of Observability Spec, Incident Response Runbook, and ADR-017. Internal SLA only; no public/commercial claim. Reliability, safety, and SLO policy always override persona/yandere behavior. Safe-word SLO is 100% with zero tolerance and no error budget. Cost budget freeze for autonomous non-critical work is accepted. Monthly SLO scorecard at `evidence/slo/<YYYY-MM>/` is mandatory. |

---

## Appendix G — Next Recommended Document

The next recommended document is:

```text
Guinevere_Cost_FinOps_Model_v1.0.md
```

Reason: this specification defines cost SLIs, cost budgets, cost anomaly detection, and autonomous-work freeze behavior, but exact numeric daily/monthly/per-task/per-loop budgets are not yet governed by an accepted FinOps model. The Cost / FinOps Model must define provider budgets, 9Router route cost ceilings, sub-agent fanout economics, emergency override budget, cost approval workflow, and monthly cost review evidence.

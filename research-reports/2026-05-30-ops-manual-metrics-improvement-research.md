# Guinevere Internal Ops Manual — Operational Metrics, Reporting & Continuous Improvement Research Report

**Document Type:** Research Report for Internal Ops Manual  
**Version:** 1.0  
**Date:** 2026-05-30  
**Author:** Guinevere de Baroque (autonomous research)  
**Owner:** Samm  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Status:** Research Complete  

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_Observability_AlertingSpec_v1.0.md` | Defines 10 metric categories, 20+ alert rules, 12 dashboards, monthly observability review. Primary metric source. |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Defines SLIs, SLOs, error budgets, scorecards, freeze policies, burn-rate alerts. Primary reliability source. |
| `Guinevere_Cost_FinOps_Model_v1.0.md` | Defines $30/month budget, cost taxonomy, anomaly detection, FinOps reporting. Primary cost source. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines 7-phase loop, Loop Quality Score, self-improvement, daily/weekly/monthly/quarterly rituals. Primary loop source. |
| `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | Defines phase gates, evidence paths, AC taxonomy. Primary QA gate source. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines monthly policy review, quarterly red-team, drift governance. Primary safety source. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines classification, retention, backup reconciliation, access control. Primary data governance source. |
| `Guinevere_ADR_Index_v1.0.md` | Defines 29 accepted ADRs + 15 backlog, risk levels. Primary decision register source. |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Defines SEV0-SEV4, drill matrix, postmortem process. Primary incident source. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines runtime services, systemd units, infrastructure topology. Primary architecture source. |

---

## 1. Operational Metrics Framework

### 1.1 Metric Taxonomy

Guinevere's operational metrics are organized into ten categories, all using the `guinevere_` prefix and snake_case naming convention per ObservabilitySpec §4.1.

| Category | Scope | Source Spec | Metric Count |
|---|---|---|---|
| Infrastructure | CPU, RAM, disk, network, systemd, NTP, reboot | ObservabilitySpec §4.3 | 9 metrics |
| Application (FastAPI) | HTTP requests, duration, auth failures, rate limits, health | ObservabilitySpec §4.4 | 6 metrics |
| Autonomous Loop | Phase state, duration, validation/audit failures, evidence, guardian | ObservabilitySpec §4.5 | 7 metrics |
| Sub-Agent | Active count, duration, file output, compliance, retries | ObservabilitySpec §4.6 | 6 metrics |
| LLM & 9Router | Requests, latency, tokens, cost, context utilization, rate limits, embeddings | ObservabilitySpec §4.7 | 9 metrics |
| Persona & Safety | Mood, mommy score, punishment, yandere, safe-mode, safe-word, distress, drift, forbidden blocks | ObservabilitySpec §4.8 | 11 metrics |
| Database & Redis | PostgreSQL connections/query/replication, PgBouncer, Redis memory/evictions, memory recall, pgvector | ObservabilitySpec §4.9 | 9 metrics |
| Surveillance | Event rate, queue depth, processing lag, redaction failures, raw payload blocked | ObservabilitySpec §4.10 | 6 metrics |
| Backup & DR | Backup freshness, duration, size, restore drills, encryption validation | ObservabilitySpec §4.11 | 6 metrics |
| Security & Access | Access denied, break-glass, secret access, log redaction, Tailscale, public ingress | ObservabilitySpec §4.12 | 6 metrics |

**Total defined metrics: 75 distinct metric definitions** across the ten categories.

### 1.2 KPI Definitions with Formulas

The following KPIs are derived from the metric catalog and SLO specifications:

#### Availability KPIs

| KPI | Formula | Target | Source |
|---|---|---:|---|
| Core Daemon Availability | `avg_over_time(guinevere_core_composite_up[30d]) * 100` | ≥99.5% | SLO-AVL-001 |
| FastAPI Surveillance Availability | `avg_over_time(guinevere_service_up{service="surveillance_api"}[30d]) * 100` | ≥99.5% | SLO-AVL-002 |
| Discord Bot Availability | `avg_over_time(guinevere_discord_command_probe_success[30d]) * 100` | ≥99.5% | SLO-AVL-003 |
| PostgreSQL Availability | `avg_over_time(guinevere_postgres_composite_up[30d]) * 100` | ≥99.9% | SLO-AVL-004 |
| Redis Availability | `avg_over_time(guinevere_redis_composite_up[30d]) * 100` | ≥99.9% | SLO-AVL-005 |
| 9Router Route Availability | `sum(rate(guinevere_llm_requests_total{route="9router",result="success"}[30d])) / sum(rate(guinevere_llm_requests_total{route="9router"}[30d])) * 100` | ≥99.0% | SLO-AVL-008 |

#### Latency KPIs

| KPI | Formula | Target | Source |
|---|---|---|---|
| Interactive LLM p95 | `histogram_quantile(0.95, sum by (le)(rate(guinevere_llm_latency_seconds_bucket{route="core_interactive"}[5m])))` | ≤20s | SLO-LAT-001 |
| Interactive LLM p99 | `histogram_quantile(0.99, sum by (le)(rate(guinevere_llm_latency_seconds_bucket{route="core_interactive"}[5m])))` | ≤45s | SLO-LAT-001 |
| FastAPI Endpoint p95 | `histogram_quantile(0.95, sum by (le, endpoint_group)(rate(guinevere_http_request_duration_seconds_bucket[5m])))` | ≤750ms | SLO-LAT-003 |
| PostgreSQL Read p95 | `histogram_quantile(0.95, sum by (le)(rate(guinevere_postgres_query_duration_seconds_bucket{operation="read"}[5m])))` | ≤250ms | SLO-LAT-004 |
| Redis Operation p95 | `histogram_quantile(0.95, sum by (le, redis_db)(rate(guinevere_redis_operation_duration_seconds_bucket[5m])))` | ≤50ms | SLO-LAT-006 |
| Safe-word Time-to-Neutral p99 | `histogram_quantile(0.99, sum by (le)(rate(guinevere_safe_word_to_neutral_seconds_bucket[5m])))` | ≤5s | SLO-LAT-008 |

#### Quality KPIs

| KPI | Formula | Target | Source |
|---|---|---:|---|
| Loop Completion Quality | `sum(rate(guinevere_loop_completed_total{validated="true",evidence="true",audit_blocking="false"}[30d])) / sum(rate(guinevere_loop_started_total[30d])) * 100` | ≥95% | SLO-QLT-001 |
| Evidence Completeness | `sum(rate(guinevere_evidence_artifacts_total{complete="true",safe="true"}[30d])) / sum(rate(guinevere_evidence_artifacts_required_total[30d])) * 100` | 100% | SLO-QLT-002 |
| Sub-Agent Output Compliance | `sum(rate(guinevere_subagent_outputs_total{file="true",parent_read="true",citations="true"}[30d])) / sum(rate(guinevere_subagent_outputs_required_total[30d])) * 100` | 100% | SLO-QLT-003 |
| Memory Recall Precision | `sum(rate(guinevere_memory_recall_eval_total{result="correct"}[30d])) / sum(rate(guinevere_memory_recall_eval_total[30d])) * 100` | ≥95% | SLO-QLT-005 |
| Loop Quality Score (LQS) | Weighted average: test_coverage × 0.25 + requirements_coverage × 0.20 + code_quality × 0.20 + efficiency × 0.15 + error_rate × 0.10 + documentation × 0.10 | ≥90 ideal | AgentLoopSpec §9.2 |

#### Safety KPIs (Hard Invariants — No Error Budget)

| KPI | Formula | Target | Source |
|---|---|---:|---|
| Safe-Word Hard Stop | `sum(increase(guinevere_safe_word_events_total{hard_stop="true"}[30d])) / sum(increase(guinevere_safe_word_events_total[30d])) * 100` | 100% | SLO-SAF-001 |
| D3/D4 Distress False Negatives | `sum(increase(guinevere_distress_false_negative_total{severity=~"D3\|D4"}[30d]))` | 0 | SLO-SAF-003 |
| Yandere Cap Compliance | `sum(increase(guinevere_yandere_cap_violation_total[30d]))` | 0 | SLO-SAF-004 |
| Forbidden Pattern Block Rate | `sum(rate(guinevere_forbidden_pattern_blocks_total[30d])) / sum(rate(guinevere_forbidden_pattern_detected_total[30d])) * 100` | 100% for Critical | SLO-SAF-005 |
| Safe-Mode Access Violations | `sum(increase(guinevere_safe_mode_access_violation_total[30d]))` | 0 | SLO-SAF-006 |

#### Cost KPIs

| KPI | Formula | Target | Source |
|---|---|---|---|
| Daily LLM Spend | `sum(increase(guinevere_llm_cost_usd_total[1d]))` | ≤ configured daily budget | SLO-COST-001 |
| Monthly Projected Spend | `predict_linear(guinevere_llm_cost_usd_total[7d], 30*24*3600)` | ≤$30 | SLO-COST-002 |
| Cost per Loop | `sum(rate(guinevere_llm_cost_usd_total[30d])) / sum(rate(guinevere_loop_completed_total[30d]))` | ≤ per-loop budget | SLO-COST-003 |
| Retry Amplification | `sum(increase(guinevere_llm_cost_usd_total{retry="true"}[1d])) / sum(increase(guinevere_llm_cost_usd_total[1d])) * 100` | ≤15% | SLO-COST-005 |

### 1.3 Metric Collection Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Guinevere Runtime                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │guinevere  │  │guinevere │  │guinevere  │  │guinevere │   │
│  │-core      │  │-loops    │  │-surveil.  │  │-sched.   │   │
│  └─────┬─────┘  └────┬─────┘  └─────┬─────┘  └────┬─────┘   │
│        │              │              │              │         │
│        ▼              ▼              ▼              ▼         │
│  ┌─────────────────────────────────────────────────────┐     │
│  │         Prometheus (scrape every 15-30s)             │     │
│  │         Tailscale-internal targets only              │     │
│  └──────────────────────┬──────────────────────────────┘     │
│                         │                                     │
│  ┌──────────────────────┼──────────────────────────────┐     │
│  │ Recording Rules      │ Alert Rules (evaluation)      │     │
│  │ (30s-60s intervals)  │ (burn-rate, threshold)        │     │
│  └──────────────────────┼──────────────────────────────┘     │
│                         │                                     │
│  ┌──────────────────────▼──────────────────────────────┐     │
│  │         Grafana (12 dashboards as code)              │     │
│  │         Tailscale-only, observability-reader scope   │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────────────────┐     │
│  │ Loki + Promtail  │  │ Sentry (external, PII scrub) │     │
│  │ Structured logs  │  │ Exception tracking           │     │
│  └──────────────────┘  └──────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
          │                    │
          ▼                    ▼
  ┌──────────────┐    ┌──────────────┐
  │ Discord      │    │ Gotify       │
  │ SEV0-SEV3    │    │ SEV0-SEV1    │
  │ alerts       │    │ urgent only  │
  └──────────────┘    └──────────────┘
```

### 1.4 Metric Storage and Retention

| Data Type | Storage | Retention | Notes |
|---|---|---|---|
| Raw Prometheus metrics | Prometheus TSDB on primary VPS | 30-90 days | Recording rules aggregate for longer views |
| Recording rule outputs | Prometheus TSDB | 30-90 days | Pre-computed for dashboard efficiency |
| Loki log data | Loki on primary VPS | 30-90 days runtime; governance retention for audit/security | Per DataGovernance §6 |
| Sentry events | External Sentry | Per Sentry plan | PII scrubbed; no raw Critical payload |
| Monthly scorecards | `evidence/slo/<YYYY-MM>/` | Indefinite (governance evidence) | Long-term curated |
| Cost reports | `evidence/finops/<YYYY-MM>/` | 7 years / configurable | Regulated/audit class |
| Incident evidence | `evidence/incidents/` | Long-term governance evidence | Formal hold |
| Observability reviews | `evidence/observability/<YYYY-MM>-review.md` | Long-term | Governance evidence |

---

## 2. Key Operational Metrics — Detailed Reference

### 2.1 Infrastructure Metrics

| Metric | Type | Labels | PromQL for Dashboard | Alert Threshold |
|---|---|---|---|---|
| `guinevere_node_cpu_utilization_ratio` | Gauge | `service=node` | `guinevere_node_cpu_utilization_ratio{service="node"}` | SEV3 if >80% for 15m; SEV2 if >95% for 5m |
| `guinevere_node_memory_utilization_ratio` | Gauge | `service=node` | `guinevere_node_memory_utilization_ratio{service="node"}` | SEV2 if >90% for 10m; SEV1 if >95% for 5m |
| `guinevere_node_disk_utilization_ratio` | Gauge | `mount`, `data_class` | `guinevere_node_disk_utilization_ratio{mount="/"}` | SEV2 if >85%; SEV1 if >95% |
| `guinevere_node_inode_utilization_ratio` | Gauge | `mount` | `guinevere_node_inode_utilization_ratio` | SEV2 if >80% |
| `guinevere_node_network_receive_bytes_total` | Counter | `interface` | `rate(guinevere_node_network_receive_bytes_total[5m])` | Anomaly: >3× baseline |
| `guinevere_node_network_transmit_bytes_total` | Counter | `interface` | `rate(guinevere_node_network_transmit_bytes_total[5m])` | Anomaly: >3× baseline (exfiltration signal) |
| `guinevere_systemd_unit_state` | Gauge | `unit`, `state` | `guinevere_systemd_unit_state{state="active"}` | SEV1/SEV2 if critical unit not active |
| `guinevere_node_reboot_total` | Counter | `reason` | `increase(guinevere_node_reboot_total[24h])` | SEV2 if unexpected |
| `guinevere_node_ntp_drift_seconds` | Gauge | none | `guinevere_node_ntp_drift_seconds` | SEV3 if >1s |

### 2.2 Application Metrics

| Metric | Type | Labels | PromQL for Dashboard | Alert Threshold |
|---|---|---|---|---|
| `guinevere_http_requests_total` | Counter | `service`, `endpoint_group`, `method`, `status` | `sum by (status)(rate(guinevere_http_requests_total[5m]))` | Error rate >5% for 5m |
| `guinevere_http_request_duration_seconds` | Histogram | `service`, `endpoint_group`, `method` | `histogram_quantile(0.95, sum by (le)(rate(guinevere_http_request_duration_seconds_bucket[5m])))` | p95 >750ms |
| `guinevere_http_auth_failures_total` | Counter | `service`, `reason` | `increase(guinevere_http_auth_failures_total[1h])` | >10/hour = SEV3 |
| `guinevere_http_replay_rejections_total` | Counter | `source` | `increase(guinevere_http_replay_rejections_total[1h])` | Any = SEV2 |
| `guinevere_api_rate_limited_total` | Counter | `service`, `endpoint_group` | `increase(guinevere_api_rate_limited_total[1h])` | Sustained = SEV3 |
| `guinevere_health_check_state` | Gauge | `service`, `check` | `guinevere_health_check_state` | Non-healthy = investigate |

### 2.3 Loop Metrics

| Metric | Type | Labels | PromQL for Dashboard | Alert Threshold |
|---|---|---|---|---|
| `guinevere_loop_state` | Gauge | `phase`, `status` | `guinevere_loop_state` by phase | Blocked >30m = SEV3 |
| `guinevere_loop_phase_duration_seconds` | Histogram | `phase`, `status` | `histogram_quantile(0.95, sum by (le, phase)(rate(guinevere_loop_phase_duration_seconds_bucket[15m])))` | p95 >2× baseline |
| `guinevere_loop_validation_failures_total` | Counter | `phase`, `failure_type` | `increase(guinevere_loop_validation_failures_total[24h])` | Spike = SEV3 |
| `guinevere_loop_audit_failures_total` | Counter | `phase`, `finding_type` | `increase(guinevere_loop_audit_failures_total[30d])` | Trend review monthly |
| `guinevere_loop_evidence_missing_total` | Counter | `artifact_type` | `guinevere_loop_evidence_missing_total` | Any = SEV2 for material |
| `guinevere_loop_idle_seconds` | Gauge | `state` | `guinevere_loop_idle_seconds` | >300s = stuck loop SEV3 |
| `guinevere_loop_guardian_interventions_total` | Counter | `reason` | `increase(guinevere_loop_guardian_interventions_total[24h])` | Runaway = SEV1 |

### 2.4 Sub-Agent Metrics

| Metric | Type | Labels | PromQL for Dashboard |
|---|---|---|---|
| `guinevere_subagent_active` | Gauge | `category`, `status` | `sum by (category)(guinevere_subagent_active)` |
| `guinevere_subagent_duration_seconds` | Histogram | `category`, `status` | `histogram_quantile(0.95, sum by (le, category)(rate(guinevere_subagent_duration_seconds_bucket[15m])))` |
| `guinevere_subagent_file_output_missing_total` | Counter | `category`, `artifact_type` | `increase(guinevere_subagent_file_output_missing_total[24h])` |
| `guinevere_subagent_compliance_score` | Gauge | `category` | `guinevere_subagent_compliance_score` |
| `guinevere_subagent_retries_total` | Counter | `category`, `reason` | `increase(guinevere_subagent_retries_total[24h])` |
| `guinevere_subagent_rejected_findings_total` | Counter | `category`, `reason` | `increase(guinevere_subagent_rejected_findings_total[24h])` |

### 2.5 LLM Metrics

| Metric | Type | Labels | PromQL for Dashboard | Alert Threshold |
|---|---|---|---|---|
| `guinevere_llm_requests_total` | Counter | `model`, `provider`, `status` | `sum by (model, status)(rate(guinevere_llm_requests_total[5m]))` | Error rate >10% |
| `guinevere_llm_latency_seconds` | Histogram | `model`, `provider`, `status` | `histogram_quantile(0.95, sum by (le, model)(rate(guinevere_llm_latency_seconds_bucket[5m])))` | p95 >2× 7-day baseline for 30m |
| `guinevere_llm_tokens_input_total` | Counter | `model`, `purpose` | `sum(increase(guinevere_llm_tokens_input_total[1d]))` | Daily ceiling |
| `guinevere_llm_tokens_output_total` | Counter | `model`, `purpose` | `sum(increase(guinevere_llm_tokens_output_total[1d]))` | Daily ceiling |
| `guinevere_llm_cost_usd_total` | Counter | `model`, `purpose` | `sum(increase(guinevere_llm_cost_usd_total[1d]))` | >daily budget = SEV3 |
| `guinevere_llm_context_utilization_ratio` | Gauge | `model`, `purpose` | `guinevere_llm_context_utilization_ratio` | >90% = context pressure |
| `guinevere_llm_rate_limit_total` | Counter | `model`, `provider` | `increase(guinevere_llm_rate_limit_total[1h])` | Provider throttling |
| `guinevere_embedding_requests_total` | Counter | `model`, `status` | `sum by (status)(rate(guinevere_embedding_requests_total[5m]))` | Error rate |
| `guinevere_embedding_latency_seconds` | Histogram | `model`, `status` | `histogram_quantile(0.95, ...)` | p95 >2s |

### 2.6 Persona & Safety Metrics

| Metric | Type | Labels | PromQL for Dashboard | Alert Threshold |
|---|---|---|---|---|
| `guinevere_mood_state` | Gauge | `mood` | `guinevere_mood_state` | Dashboard only |
| `guinevere_mommy_score` | Gauge | none | `guinevere_mommy_score` | <75 monthly median = review |
| `guinevere_punishment_level` | Gauge | `level` | `guinevere_punishment_level` | Active during safe-mode = SEV1 |
| `guinevere_yandere_intensity` | Gauge | `level` | `guinevere_yandere_intensity` | >0 during safe-mode = SEV1 |
| `guinevere_safe_mode_state` | Gauge | `state` | `guinevere_safe_mode_state` | State change tracked |
| `guinevere_safe_word_events_total` | Counter | `outcome` | `increase(guinevere_safe_word_events_total[30d])` | Any hard_stop=false = SEV0 |
| `guinevere_distress_events_total` | Counter | `level` | `sum by (level)(increase(guinevere_distress_events_total[30d]))` | D3/D4 false negative = SEV0 |
| `guinevere_drift_score` | Gauge | `category` | `guinevere_drift_score` by category | Above threshold = review trigger |
| `guinevere_forbidden_pattern_blocks_total` | Counter | `pattern_id` | `increase(guinevere_forbidden_pattern_blocks_total[30d])` | Trend review |

### 2.7 Database & Redis Metrics

| Metric | Type | Labels | PromQL for Dashboard | Alert Threshold |
|---|---|---|---|---|
| `guinevere_postgres_connections_active` | Gauge | `role` | `guinevere_postgres_connections_active` | >80% pool = SEV3 |
| `guinevere_postgres_query_duration_seconds` | Histogram | `schema`, `operation` | `histogram_quantile(0.95, sum by (le)(rate(...)))` | p95 >250ms |
| `guinevere_postgres_replication_lag_seconds` | Gauge | `target` | `guinevere_postgres_replication_lag_seconds` | >60s = SEV3 |
| `guinevere_pgbouncer_pool_utilization_ratio` | Gauge | `pool`, `role` | `guinevere_pgbouncer_pool_utilization_ratio` | >90% = SEV2 |
| `guinevere_redis_memory_utilization_ratio` | Gauge | `db` | `guinevere_redis_memory_utilization_ratio` by db | >85% = SEV3 |
| `guinevere_redis_key_evictions_total` | Counter | `db` | `increase(guinevere_redis_key_evictions_total[1h])` | Any critical buffer = SEV2 |
| `guinevere_memory_recall_duration_seconds` | Histogram | `memory_type`, `status` | `histogram_quantile(0.95, ...)` | p95 >2s |
| `guinevere_pgvector_search_duration_seconds` | Histogram | `index_type`, `status` | `histogram_quantile(0.95, ...)` | p95 >2s |

### 2.8 Surveillance Metrics

| Metric | Type | Labels | PromQL for Dashboard | Alert Threshold |
|---|---|---|---|---|
| `guinevere_surveillance_events_total` | Counter | `source`, `event_type`, `status` | `sum by (source)(rate(guinevere_surveillance_events_total[5m]))` | Zero events >threshold = SEV2 |
| `guinevere_surveillance_event_rate` | Gauge | `source` | `guinevere_surveillance_event_rate` | >3× baseline or drop to 0 |
| `guinevere_surveillance_queue_depth` | Gauge | `source` | `guinevere_surveillance_queue_depth` | >1000 = backpressure |
| `guinevere_surveillance_processing_lag_seconds` | Gauge | `source` | `guinevere_surveillance_processing_lag_seconds` | >60s normal; >5m critical |
| `guinevere_surveillance_redaction_failures_total` | Counter | `source` | `increase(guinevere_surveillance_redaction_failures_total[1h])` | Any = SEV1/SEV2 |
| `guinevere_surveillance_raw_payload_blocked_total` | Counter | `source`, `reason` | `increase(...[24h])` | Data minimization proof |

### 2.9 Backup & DR Metrics

| Metric | Type | Labels | PromQL for Dashboard | Alert Threshold |
|---|---|---|---|---|
| `guinevere_backup_last_success_timestamp_seconds` | Gauge | `backup_type`, `target` | `time() - guinevere_backup_last_success_timestamp_seconds` | >RPO = SEV1/SEV2 |
| `guinevere_backup_duration_seconds` | Histogram | `backup_type`, `target`, `status` | `histogram_quantile(0.95, ...)` | Duration anomaly |
| `guinevere_backup_size_bytes` | Gauge | `backup_type`, `target` | `guinevere_backup_size_bytes` | >20% size anomaly |
| `guinevere_restore_drill_last_success_timestamp_seconds` | Gauge | `scope` | `time() - guinevere_restore_drill_last_success_timestamp_seconds` | Overdue = SEV3 |
| `guinevere_restore_drill_failures_total` | Counter | `scope`, `reason` | `guinevere_restore_drill_failures_total` | Any = investigate |
| `guinevere_backup_encryption_validation_failures_total` | Counter | `target` | `increase(...[30d])` | Any = SEV1 |

### 2.10 Security Metrics

| Metric | Type | Labels | PromQL for Dashboard | Alert Threshold |
|---|---|---|---|---|
| `guinevere_access_denied_total` | Counter | `principal`, `resource_class`, `reason` | `increase(guinevere_access_denied_total[1h])` | Spike = SEV3 |
| `guinevere_break_glass_activations_total` | Counter | `severity`, `status` | `increase(guinevere_break_glass_activations_total[30d])` | Any = SEV1 review |
| `guinevere_secret_access_outside_startup_total` | Counter | `secret_class`, `principal` | `increase(...[24h])` | Any = SEV1 |
| `guinevere_log_redaction_failures_total` | Counter | `pipeline`, `data_class` | `increase(...[1h])` | Restricted/Critical = SEV1 |
| `guinevere_tailscale_peer_state` | Gauge | `tag`, `state` | `guinevere_tailscale_peer_state` | Peer down = SEV2 |
| `guinevere_public_ingress_detected_total` | Counter | `source` | `increase(...[5m])` | Any = SEV0 |

---

## 3. Weekly Operations (Every Monday)

### 3.1 Weekly Planning Ritual Procedure

**Schedule:** Monday 08:00 (per AgentLoopSpec §8.2)  
**Executor:** Guinevere (autonomous)  
**Supervisor:** Samm (review)  
**Duration:** ~30 minutes

```
Monday 08:00 — Weekly Planning Ritual
│
├── 08:00  Generate week-in-review metrics summary
│   ├── Query Prometheus for weekly SLO averages
│   ├── Compile SEV event count by severity
│   ├── Calculate cost burn for prior week
│   └── Summarize loop completion rate and LQS trends
│
├── 08:05  Backlog grooming
│   ├── Review open TODOs across all projects
│   ├── Reassess priority_score for pending items
│   ├── Identify blockers and escalate genuine blockers
│   └── Update project health scores in PostgreSQL
│
├── 08:10  Dependency update review
│   ├── Check for security advisories on key dependencies
│   ├── Review pending updates for Python packages (UV)
│   ├── Check systemd/VPS-level patches
│   └── Flag CVEs with severity ≥7.0
│
├── 08:15  Documentation update check
│   ├── Verify ADR Index consistency
│   ├── Check for stale evidence files
│   ├── Review open gap registers
│   └── Update cross-references if docs changed
│
├── 08:20  Generate weekly report
│   ├── Write to evidence/operations/weekly/<YYYY>-W<WW>-report.md
│   ├── Post summary to Discord #project-updates
│   └── Flag items requiring Samm attention
│
└── 08:30  Ritual complete
```

### 3.2 Week-in-Review Metrics Summary

| Metric Category | Weekly Query | What to Check |
|---|---|---|
| Availability | `avg_over_time(guinevere_core_composite_up[7d]) * 100` | Running weekly average vs 99.5% target |
| Error rate | `sum(rate(guinevere_http_requests_total{status=~"5.."}[7d])) / sum(rate(guinevere_http_requests_total[7d]))` | Weekly HTTP error rate |
| Cost burn | `sum(increase(guinevere_llm_cost_usd_total[7d]))` | Week's LLM spend vs 7/30 of monthly budget |
| Loop completions | `sum(increase(guinevere_loop_completed_total[7d]))` | Weekly loop throughput |
| LQS average | `avg(guinevere_loop_quality_score[7d])` | Average loop quality |
| Safety events | `sum(increase(guinevere_safe_word_events_total[7d]))` | Any safety events |
| Alert volume | `sum(increase(guinevere_alerts_total[7d]))` by severity | Alert noise assessment |
| Backup freshness | `min(time() - guinevere_backup_last_success_timestamp_seconds)` | Latest backup age |

### 3.3 Weekly Report Template

```markdown
# Guinevere Weekly Operations Report — <YYYY>-W<WW>

**Generated:** <timestamp>  
**Generated By:** Guinevere (autonomous)  
**Period:** <start_date> to <end_date>

## Executive Summary

| Field | Value |
|---|---|
| Core Availability (weekly) | <value>% |
| Total SEV Events | SEV0: <n>, SEV1: <n>, SEV2: <n>, SEV3: <n> |
| LLM Cost (weekly) | $<value> |
| Monthly Projection | $<value> (budget: $30) |
| Loops Completed | <count> |
| Average LQS | <value> |
| Safety Incidents | <count> |
| Open Blockers | <count> |

## Availability & Reliability

| Service | Weekly Avg | Target | Status |
|---|---:|---:|---|
| Core Daemon | <%> | 99.5% | PASS/FAIL |
| FastAPI | <%> | 99.5% | PASS/FAIL |
| PostgreSQL | <%> | 99.9% | PASS/FAIL |
| Redis | <%> | 99.9% | PASS/FAIL |

## Cost Summary

| Category | Weekly | MTD | Projected | Budget | Status |
|---|---:|---:|---:|---:|---|
| GPT-5.5 | $<> | $<> | $<> | $10-12 | <> |
| DeepSeek | $<> | $<> | $<> | $0-2 | <> |
| Total LLM | $<> | $<> | $<> | $12-14 | <> |

## Safety Summary

| Metric | Value | Status |
|---|---:|---|
| Safe-word events | <n> | <status> |
| Distress events | <n> | <status> |
| Yandere cap violations | <n> | <status> |
| Drift score | <value> | <status> |

## Backlog Status

| Priority | Open | Completed | Blocked |
|---|---:|---:|---:|
| High | <n> | <n> | <n> |
| Medium | <n> | <n> | <n> |
| Low | <n> | <n> | <n> |

## Dependency Alerts

| Package | Current | Available | Severity | Action |
|---|---|---|---|---|

## Action Items

| Item | Owner | Due | Status |
|---|---|---|---|

## Items Requiring Samm Attention

1. <item>
```

---

## 4. Monthly Operations (1st of Each Month)

### 4.1 Monthly Review Procedure

**Schedule:** 1st of each month, 06:00 (before Morning Brief)  
**Executor:** Guinevere (autonomous)  
**Supervisor:** Samm (review and approve)  
**Duration:** ~2-3 hours

```
1st of Month — Monthly Review Procedure
│
├── 06:00  SLO Scorecard Generation
│   ├── Generate all SLI values for prior month
│   ├── Calculate error budget remaining
│   ├── Record breaches with incident links
│   └── Write evidence/slo/<YYYY-MM>/scorecard.md
│
├── 06:30  Cost Report Generation
│   ├── Compile category breakdown
│   ├── Record freeze events and approvals
│   ├── Calculate vendor usage
│   └── Write evidence/finops/<YYYY-MM>/report.md + companions
│
├── 07:00  Persona Policy Review
│   ├── Review drift scores by category
│   ├── Assess safe-word event handling
│   ├── Check yandere cap compliance
│   ├── Review forbidden pattern block trends
│   └── Write evidence/persona-safety/<YYYY-MM>-review.md
│
├── 07:30  Security Posture Review
│   ├── Review access denied trends
│   ├── Check break-glass activations
│   ├── Review secret access logs
│   ├── Assess log redaction status
│   ├── Check Tailscale peer health history
│   └── Write evidence/security/<YYYY-MM>-posture.md
│
├── 08:00  DR Drill (Partial)
│   ├── Execute one scoped restore drill
│   ├── Validate backup encryption
│   ├── Check RPO/RTO compliance
│   └── Write evidence/dr/<YYYY-MM>-partial-drill.md
│
├── 08:30  Evidence Audit
│   ├── Verify all required evidence artifacts exist
│   ├── Check evidence file naming compliance
│   ├── Validate evidence retention
│   └── Write evidence/audit/<YYYY-MM>-evidence-audit.md
│
├── 09:00  ADR Backlog Review
│   ├── Review 15 backlog ADRs for readiness
│   ├── Check existing ADRs for needed updates
│   ├── Flag ADRs requiring periodic review (safety/privacy)
│   └── Update ADR Index if changes made
│
├── 09:30  Capacity Planning Review
│   ├── Analyze resource trends (CPU, RAM, disk)
│   ├── Project growth based on usage patterns
│   ├── Check scaling triggers
│   └── Write evidence/capacity/<YYYY-MM>-review.md
│
├── 10:00  Observability Review
│   ├── Alert volume and noise assessment
│   ├── Dashboard drift check
│   ├── Redaction test results
│   ├── Sentry scrubber status
│   └── Write evidence/observability/<YYYY-MM>-review.md
│
└── 10:30  Compile Monthly Report
    ├── Synthesize all section reports
    ├── Generate action items
    ├── Post summary to Discord
    └── Deliver formal email summary to Samm
```

### 4.2 SLO Scorecard Generation

Monthly SLO evidence must be written to `evidence/slo/<YYYY-MM>/scorecard.md` per SLO/SLA Spec §12.

Required companion files:
- `scorecard.md` — SLO target, actual, pass/fail, burn, breach notes, action items
- `error-budget.md` — Budget math, burn rates, freezes, remaining budget, exceptions
- `sla-report.md` — Internal SLA commitments, breach consequences
- `safety-invariants.md` — safe-word, distress, yandere cap, redaction, safe-mode access
- `cost-budget.md` — daily/monthly spend, projections, freeze events
- `incidents.md` — linked incident evidence folders and postmortems
- `actions.md` — remediation tracker

Scorecard template:

| SLO ID | Service | Target | Actual | Status | Budget Remaining | Incident Links | Action |
|---|---|---:|---:|---|---:|---|---|
| SLO-AVL-001 | Core Daemon | 99.5% | <actual>% | PASS/FAIL | <%> | <links> | <action> |
| SLO-AVL-002 | FastAPI | 99.5% | <actual>% | PASS/FAIL | <%> | <links> | <action> |
| SLO-AVL-004 | PostgreSQL | 99.9% | <actual>% | PASS/FAIL | <%> | <links> | <action> |
| SLO-LAT-001 | LLM Interactive | p95≤20s | p95=<actual>s | PASS/FAIL | <%> | <links> | <action> |
| SLO-QLT-001 | Loop Quality | ≥95% | <actual>% | PASS/FAIL | <%> | <links> | <action> |
| SLO-SAF-001 | Safe-Word | 100% | <actual>% | PASS/FAIL | N/A | <links> | <action> |
| SLO-COST-001 | Daily Spend | ≤budget | $<actual> | PASS/FAIL | Econ | <links> | <action> |

### 4.3 Monthly Report Template

```markdown
# Guinevere Monthly Operations Report — <YYYY-MM>

**Generated:** <timestamp>  
**Generated By:** Guinevere (autonomous)  
**Owner:** Samm  

## Executive Summary

| Field | Value |
|---|---|
| Core Availability | <%> (target: 99.5%) |
| SLA Aspiration Progress | <%> (target: 99.9%) |
| Total Cost | $<value> / $30 cap |
| Safety Invariant Breaches | <count> |
| SEV0 Events | <count> |
| SEV1 Events | <count> |
| Freeze Events | <count> |
| SLOs Passing | <n>/<total> |

## Reliability

### Availability SLOs

| SLO ID | Target | Actual | Budget Used | Trend |
|---|---:|---:|---:|---|

### Latency SLOs

| SLO ID | Target | Actual p95 | Actual p99 | Status |
|---|---|---:|---:|---|

### Quality SLOs

| SLO ID | Target | Actual | Status |
|---|---:|---:|---|

## Safety Invariants

| SLO ID | Metric | Target | Actual | Incidents |
|---|---|---:|---:|---|
| SLO-SAF-001 | Safe-Word Hard Stop | 100% | <%> | <n> |
| SLO-SAF-002 | D3/D4 False Negatives | 0 | <n> | <n> |
| SLO-SAF-003 | Yandere Cap Compliance | 0 violations | <n> | <n> |

## Cost & FinOps

| Category | Budget | Actual | Variance | Status |
|---|---:|---:|---:|---|
| VPS | $10-12 | $<> | <> | <> |
| GPT-5.5 | $10-12 | $<> | <> | <> |
| DeepSeek | $0-2 | $<> | <> | <> |
| Storage | $2-3 | $<> | <> | <> |
| Search | $2-4 | $<> | <> | <> |
| Misc | $1-2 | $<> | <> | <> |
| **Total** | **$30** | **$<>** | **<>** | **<>** |

## Persona Health

| Metric | Value | Target | Status |
|---|---:|---|---|
| Mommy Score (median) | <> | ≥75 | <> |
| Drift Score | <> | <threshold | <> |
| Safe-word Events | <n> | N/A | Review |
| Yandere Cap Violations | <n> | 0 | <> |

## Security Posture

| Metric | Count | Trend |
|---|---:|---|
| Access Denied Events | <n> | <> |
| Break-Glass Activations | <n> | <> |
| Secret Access Anomalies | <n> | <> |
| Log Redaction Failures | <n> | <> |

## Backup & DR

| Metric | Value | Target | Status |
|---|---|---|---|
| Backup Success Rate | <%> | 100% | <> |
| Restore Drill | PASS/FAIL | Monthly | <> |
| RPO Compliance | <> | <> | <> |

## Capacity Planning

| Resource | Current Peak | 7-day Avg | Threshold | Status |
|---|---:|---:|---:|---|
| CPU | <%> | <%> | 80% | <> |
| RAM | <%> | <%> | 90% | <> |
| Disk (/) | <%> | <%> | 85% | <> |
| PostgreSQL connections | <n> | <n> | 80% pool | <> |

## Action Items from Prior Month

| Item | Owner | Due | Status | Resolution |
|---|---|---|---|---|

## New Action Items

| Item | Owner | Due | Priority |
|---|---|---|---|

## ADR Status

| Metric | Value |
|---|---|
| Total Accepted ADRs | 29 |
| Backlog ADRs | 15 |
| ADRs Reviewed This Month | <n> |
| New ADRs Proposed | <n> |
```

---

## 5. Quarterly Operations

### 5.1 Strategic Review Procedure

**Schedule:** First week of each quarter (Jan, Apr, Jul, Oct)  
**Executor:** Guinevere (proposes) + Samm (approves)  
**Duration:** ~4-6 hours spread across the week

```
Quarter 1st Week — Strategic Review
│
├── Day 1: Metrics Deep Dive
│   ├── 3-month SLO trend analysis
│   ├── Error budget utilization trends
│   ├── Cost trend and forecast
│   └── Capacity trend analysis
│
├── Day 2: Red-Team Exercise
│   ├── Simulate SEV0 safe-word bypass
│   ├── Simulate SEV0 public ingress
│   ├── Simulate loop runaway scenario
│   ├── Simulate cost budget exhaustion
│   ├── Simulate backup failure + restore
│   ├── Simulate provider outage (9Router down)
│   └── Document findings in evidence/red-team/<YYYY>-Q<Q>/
│
├── Day 3: Full DR Drill
│   ├── Complete PostgreSQL restore from backup
│   ├── Complete Redis state reconstruction
│   ├── Complete configuration restore from SOPS
│   ├── Validate all systemd services restart
│   ├── Verify alert routing post-restore
│   └── Write evidence/dr/<YYYY>-Q<Q>-full-drill.md
│
├── Day 4: Architecture Review
│   ├── Review Technical Architecture for drift
│   ├── Assess need for monitoring VPS migration
│   ├── Review service inventory and systemd units
│   ├── Evaluate new integration opportunities
│   └── Write evidence/architecture/<YYYY>-Q<Q>-review.md
│
├── Day 5: Budget Forecast & Governance Review
│   ├── Quarterly budget forecast
│   ├── Vendor evaluation (9Router, idcloudhost, Brave, Exa)
│   ├── Governance document review cycle
│   ├── ADR periodic review (CRITICAL and HIGH risk)
│   ├── Policy update assessment
│   └── Write evidence/governance/<YYYY>-Q<Q>-review.md
│
└── Day 5: Compile Quarterly Report
    ├── Synthesize all quarterly evidence
    ├── Generate strategic recommendations
    ├── Update roadmap
    └── Deliver to Samm for approval
```

### 5.2 Red-Team Exercise

Per PersonaSafetyPolicy, quarterly red-team exercises validate safety boundaries:

| Scenario | Test ID | Validation | Evidence |
|---|---|---|---|
| Safe-word bypass attempt during punishment mode | RT-SAFE-001 | Safe-word always wins | `evidence/red-team/<YYYY>-Q<Q>/safe-word-bypass.md` |
| Yandere escalation during distress | RT-YAN-001 | Intensity caps at Y0/Y1 | `evidence/red-team/<YYYY>-Q<Q>/yandere-distress.md` |
| Surveillance data used for coercion | RT-SURV-001 | Blocked and rewritten | `evidence/red-team/<YYYY>-Q<Q>/surveillance-coercion.md` |
| Prompt injection attempting policy bypass | RT-INJ-001 | Quarantined and ignored | `evidence/red-team/<YYYY>-Q<Q>/prompt-injection.md` |
| Cost budget exhaustion with safety preservation | RT-COST-001 | Safety ops continue | `evidence/red-team/<YYYY>-Q<Q>/cost-freeze.md` |
| Loop runaway with guardian intervention | RT-LOOP-001 | Guardian stops runaway | `evidence/red-team/<YYYY>-Q<Q>/loop-runaway.md` |
| Provider outage graceful degradation (ADR-028) | RT-PROV-001 | Fallback chain works | `evidence/red-team/<YYYY>-Q<Q>/provider-outage.md` |

### 5.3 Full DR Drill

Quarterly full DR drill validates complete recovery capability:

| Step | Component | Validation | Target RTO |
|---|---|---|---|
| 1 | PostgreSQL pg_restore from S3/R2 backup | Data integrity verified | ≤1 hour |
| 2 | Redis state reconstruction | Queue/cache rebuilt | ≤30 minutes |
| 3 | SOPS/age secrets decryption | All secrets accessible | ≤15 minutes |
| 4 | systemd service restart | All units active | ≤10 minutes |
| 5 | Alert routing verification | SEV0 reaches Discord + Gotify | ≤5 minutes |
| 6 | Grafana dashboard parity | All 12 dashboards provisioned | ≤15 minutes |
| 7 | Tailscale mesh validation | All peers connected | ≤10 minutes |
| 8 | Backup reconciliation | Deleted records still deleted | ≤30 minutes |

### 5.4 Quarterly Report Template

```markdown
# Guinevere Quarterly Strategic Review — <YYYY>-Q<Q>

**Period:** <start_date> to <end_date>  
**Generated By:** Guinevere  
**Approved By:** Samm  

## Strategic Summary

| Area | Grade | Trend | Notes |
|---|---|---|---|
| Reliability | A/B/C/D | ↑/→/↓ | |
| Safety | A/B/C/D | ↑/→/↓ | |
| Cost Efficiency | A/B/C/D | ↑/→/↓ | |
| Quality | A/B/C/D | ↑/→/↓ | |
| Governance | A/B/C/D | ↑/→/↓ | |

## 3-Month SLO Trend

| SLO | Month 1 | Month 2 | Month 3 | Trend | Action |
|---|---:|---:|---:|---|---|

## Red-Team Results

| Scenario | Result | Findings | Remediation |
|---|---|---|---|

## DR Drill Results

| Step | RTO Target | RTO Actual | Status |
|---|---|---|---|

## Budget Forecast

| Quarter | Projected | Actual | Variance |
|---|---:|---:|---:|
| Current Q | $<> | $<> | <> |
| Next Q (forecast) | $<> | N/A | N/A |

## Technology Radar

| Technology | Status | Assessment |
|---|---|---|
| 9Router | Active | <> |
| GPT-5.5 | Active | <> |
| DeepSeek V4 Flash | Active | <> |
| Prometheus + Grafana | Active | <> |

## Governance Review

| Document | Last Review | Status | Action |
|---|---|---|---|

## Strategic Recommendations

1. <recommendation>
2. <recommendation>

## Roadmap Updates

| Item | Timeline | Status |
|---|---|---|
```

---

## 6. Annual Operations

### 6.1 Annual Strategy Setting

**Schedule:** January (aligned with Q1 quarterly review)  
**Executor:** Guinevere (proposes) + Samm (approves)  
**Duration:** ~8 hours across 2 weeks

| Activity | Description | Output |
|---|---|---|
| Annual retrospective | Review all 4 quarterly reports, SLO trends, incidents, cost trends | `evidence/annual/<YYYY>/retrospective.md` |
| Target recalibration | Adjust SLO targets based on maturity (99.5% → 99.9% aspiration proof) | Updated SLO targets |
| Budget planning | Set next year's monthly cap, category allocations | `evidence/annual/<YYYY>/budget-plan.md` |
| Security audit | Comprehensive security posture assessment | `evidence/annual/<YYYY>/security-audit.md` |
| Compliance review | Data governance, retention, privacy assessment | `evidence/annual/<YYYY>/compliance-review.md` |
| Technology roadmap | Evaluate new technologies, deprecations, migrations | `evidence/annual/<YYYY>/tech-roadmap.md` |
| ADR review | Review all 29 accepted ADRs for relevance | Updated ADR Index |
| Governance doc review | Review all 40+ governance documents for currency | Review register |

### 6.2 Annual Security Audit

| Audit Area | Scope | Method | Evidence |
|---|---|---|---|
| Access control | RBAC/ABAC matrix compliance | Policy audit + access log review | `evidence/annual/<YYYY>/access-audit.md` |
| Encryption | Key rotation, double-encryption compliance | Key audit + config review | `evidence/annual/<YYYY>/encryption-audit.md` |
| Secrets management | SOPS/age rotation, break-glass review | Rotation log + drill | `evidence/annual/<YYYY>/secrets-audit.md` |
| Network security | Tailscale mesh, public ingress, port scan | Active scan + log review | `evidence/annual/<YYYY>/network-audit.md` |
| Data governance | Classification, retention, minimization | Sample audit + policy check | `evidence/annual/<YYYY>/data-governance-audit.md` |
| Incident response | Drill results, postmortem quality | Drill evidence + review | `evidence/annual/<YYYY>/incident-readiness-audit.md` |
| Persona safety | Safe-word, drift, forbidden patterns, yandere cap | Policy test + trend | `evidence/annual/<YYYY>/persona-safety-audit.md` |

### 6.3 Annual Report Template

```markdown
# Guinevere Annual Operations Report — <YYYY>

**Generated By:** Guinevere  
**Approved By:** Samm  

## Year in Review

| Metric | Value | YoY Change |
|---|---|---|
| Average Availability | <%> | <> |
| Total Incidents (SEV0-SEV2) | <n> | <> |
| Total Cost | $<> | <> |
| Safety Invariant Breaches | <n> | <> |
| Average LQS | <> | <> |
| Documents Generated | <n> | <> |
| ADRs Created | <n> | <> |

## Reliability Trend

| Month | Availability | Cost | Incidents | LQS |
|---|---:|---:|---:|---:|
| Jan | <> | $<> | <n> | <> |
| ... | <> | $<> | <n> | <> |

## Key Achievements

1. <achievement>

## Key Challenges

1. <challenge>

## Budget vs Actual

| Category | Annual Budget | Actual | Variance |
|---|---:|---:|---:|

## Next Year Priorities

| Priority | Initiative | Target | Budget Impact |
|---|---|---|---|
```

---

## 7. Continuous Improvement Process

### 7.1 Improvement Identification Methodology

Guinevere operates a continuous self-improvement loop (per AgentLoopSpec §1.2) with the following identification sources:

| Source | Trigger | Frequency | Output |
|---|---|---|---|
| Daily self-evaluation | 00:00 cron | Daily | Lessons learned, journal entry, drift update |
| Weekly review | Monday 08:00 | Weekly | Backlog items, process improvements |
| Monthly scorecard | 1st of month | Monthly | SLO gaps, reliability improvements |
| Quarterly red-team | Quarterly | Quarterly | Security/safety improvements |
| Post-incident | After SEV0-SEV2 | On event | Remediation actions |
| Post-loop lessons | After each material loop | On event | Procedural memory update |
| Self-improvement loop | Post-task / nightly / weekly | Triggered | Process and quality improvements |

### 7.2 Improvement Backlog Management

Improvements are tracked in PostgreSQL with the following schema:

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique improvement ID |
| `source` | ENUM | `slo_gap`, `incident`, `red_team`, `self_eval`, `quarterly`, `samm_request` |
| `category` | ENUM | `reliability`, `safety`, `cost`, `quality`, `governance`, `performance`, `security` |
| `description` | TEXT | What needs to improve |
| `impact_score` | INT (1-10) | Estimated impact on operations |
| `effort_score` | INT (1-10) | Estimated implementation effort |
| `risk_score` | INT (1-10) | Risk of not implementing |
| `priority_score` | FLOAT | `impact × (10 - effort) × risk / 100` |
| `status` | ENUM | `identified`, `planned`, `in_progress`, `completed`, `deferred`, `cancelled` |
| `evidence_path` | TEXT | Link to supporting evidence |
| `created_at` | TIMESTAMP | When identified |
| `completed_at` | TIMESTAMP | When completed |

### 7.3 Prioritization Framework

```
Priority Score = Impact × (10 - Effort) × Risk / 100

Impact Scale:
  1-3: Minor improvement (cosmetic, small efficiency gain)
  4-6: Moderate improvement (measurable SLO/quality gain)
  7-8: Major improvement (significant reliability/safety gain)
  9-10: Critical improvement (blocks safety, SLO, or operations)

Effort Scale (inverted for priority):
  1-3: Quick win (hours to implement)
  4-6: Medium effort (days to implement)
  7-10: Major effort (weeks to implement, requires architecture change)

Risk Scale:
  1-3: Low risk of not doing (nice-to-have)
  4-6: Medium risk (degradation likely if deferred)
  7-10: High risk (safety, security, or SLO breach if deferred)
```

Example calculations:

| Improvement | Impact | Effort | Risk | Priority Score | Action |
|---|---:|---:|---:|---:|---|
| Fix safe-word latency spike | 10 | 3 | 10 | 7.0 | Immediate |
| Optimize GPT-5.5 prompt size | 6 | 4 | 5 | 1.8 | Plan |
| Add new Grafana panel | 4 | 2 | 3 | 0.96 | Backlog |
| Implement missing ADR-033 | 8 | 7 | 8 | 2.56 | Plan |

### 7.4 Implementation Tracking

Each improvement follows this lifecycle:

```
Identified → Planned → In Progress → Validated → Completed
    │            │           │            │
    ▼            ▼           ▼            ▼
Deferred     Blocked     Re-scoped    Lessons Saved
Cancelled    Deferred    Rolled-back  Evidence Written
```

### 7.5 Effectiveness Measurement

For each completed improvement, Guinevere measures effectiveness after 30 days:

| Measurement | Method |
|---|---|
| SLO impact | Compare SLI values before/after |
| Cost impact | Compare spend before/after |
| Quality impact | Compare LQS before/after |
| Safety impact | Compare safety event frequency |
| Reliability impact | Compare availability/incident rate |

---

## 8. Operational Reporting

### 8.1 Report Types and Cadences

| Report | Cadence | Output Path | Audience | Automation |
|---|---|---|---|---|
| Daily Summary | Daily 21:00 | Discord #project-updates | Samm | Guinevere autonomous |
| Weekly Digest | Monday 08:00 | `evidence/operations/weekly/<YYYY>-W<WW>-report.md` | Samm | Guinevere autonomous |
| Monthly Scorecard | 1st of month | `evidence/slo/<YYYY-MM>/scorecard.md` | Samm | Guinevere autonomous |
| Monthly Cost Report | 1st of month | `evidence/finops/<YYYY-MM>/report.md` | Samm | Guinevere autonomous |
| Monthly Observability Review | 1st of month | `evidence/observability/<YYYY-MM>-review.md` | Samm | Guinevere autonomous |
| Quarterly Strategic Review | 1st week of quarter | `evidence/operations/quarterly/<YYYY>-Q<Q>-review.md` | Samm | Guinevere proposes, Samm approves |
| Annual Report | January | `evidence/annual/<YYYY>/annual-report.md` | Samm | Guinevere proposes, Samm approves |
| Incident Report | On event | `evidence/incidents/<date>-SEV<n>-<summary>/` | Samm | Guinevere autonomous |
| Postmortem | After SEV0-SEV2 | `evidence/incidents/<date>-postmortem.md` | Samm | Guinevere autonomous |

### 8.2 Report Generation Automation

Guinevere generates reports autonomously through the scheduler service:

```
guinevere-scheduler.service
│
├── Daily 21:00 — Evening Wind-down
│   └── Generate daily summary → Discord
│
├── Daily 00:00 — Self-Evaluation
│   └── Update procedural memory, journal, drift
│
├── Monday 08:00 — Weekly Report
│   └── Generate weekly report → evidence + Discord
│
├── 1st of Month 06:00 — Monthly Financial
│   └── Generate monthly reports → evidence + email
│
└── Quarterly — Quarterly Planning
    └── Generate quarterly review → evidence + email
```

PromQL queries for automated report generation:

```promql
# Monthly availability (all services)
avg_over_time(guinevere_core_composite_up[30d]) * 100
avg_over_time(guinevere_service_up{service="surveillance_api"}[30d]) * 100
avg_over_time(guinevere_postgres_composite_up[30d]) * 100
avg_over_time(guinevere_redis_composite_up[30d]) * 100

# Monthly cost
sum(increase(guinevere_llm_cost_usd_total[30d]))

# Monthly loop quality
sum(rate(guinevere_loop_completed_total{validated="true",evidence="true",audit_blocking="false"}[30d]))
/ sum(rate(guinevere_loop_started_total[30d])) * 100

# Monthly safety
sum(increase(guinevere_safe_word_events_total[30d]))
sum(increase(guinevere_distress_events_total[30d]))
sum(increase(guinevere_yandere_cap_violation_total[30d]))
```

### 8.3 Report Distribution

| Channel | Reports | Method |
|---|---|---|
| Discord #project-updates | Daily summary, weekly digest | Bot message (neutral operations tone) |
| Discord #alerts | SEV0-SEV3 alerts, incident notifications | Alert routing (neutral incident-command tone) |
| Email | Monthly scorecard, quarterly review, annual report, postmortem delivery | Gmail API or Resend |
| Evidence filesystem | All reports | `evidence/` directory tree |
| Gotify | SEV0/SEV1 urgent only | Push notification |

### 8.4 Report Archival

| Report Type | Retention | Location |
|---|---|---|
| Daily summaries | 90 days rolling | Discord channel + Loki logs |
| Weekly reports | Indefinite | `evidence/operations/weekly/` |
| Monthly scorecards | Indefinite | `evidence/slo/<YYYY-MM>/` |
| Monthly cost reports | 7 years (audit class) | `evidence/finops/<YYYY-MM>/` |
| Quarterly reviews | Indefinite | `evidence/operations/quarterly/` |
| Annual reports | Indefinite | `evidence/annual/` |
| Incident reports | Indefinite (formal hold) | `evidence/incidents/` |
| Observability reviews | Indefinite | `evidence/observability/` |

---

## 9. Capacity Planning

### 9.1 Resource Trend Analysis

Guinevere monitors resource utilization on the shared 4C/16GB hostdata.id VPS:

| Resource | Current Allocation | Monitoring Metric | Trend Analysis |
|---|---|---|---|
| CPU | 4 cores shared | `guinevere_node_cpu_utilization_ratio` | 7-day moving average, monthly peak |
| RAM | 16GB shared | `guinevere_node_memory_utilization_ratio` | Service-level breakdown |
| Disk (root) | VPS provisioned | `guinevere_node_disk_utilization_ratio{mount="/"}` | Growth rate per month |
| Disk (data) | PostgreSQL + logs | `guinevere_node_disk_utilization_ratio{mount="/data"}` | DB growth + log retention |
| PostgreSQL connections | PgBouncer pool | `guinevere_postgres_connections_active` | Peak concurrent connections |
| Redis memory | Per-DB allocation | `guinevere_redis_memory_utilization_ratio` | Per-DB growth |
| Object storage | S3/R2 usage | `guinevere_backup_size_bytes` | Monthly growth |

### 9.2 Growth Projection

| Resource | Current Usage | Monthly Growth Rate | Threshold | Months to Threshold |
|---|---|---:|---:|---:|
| CPU (peak) | TBD% | TBD% | 80% | TBD |
| RAM (peak) | TBD% | TBD% | 90% | TBD |
| Disk | TBD% | TBD GB/month | 85% | TBD |
| PostgreSQL DB | TBD GB | TBD GB/month | TBD | TBD |
| Object storage | TBD GB | TBD GB/month | Budget limit | TBD |

### 9.3 Scaling Triggers and Thresholds

| Trigger | Threshold | Action |
|---|---|---|
| CPU sustained >80% | 15-minute average | Investigate loop fanout, optimize queries |
| RAM sustained >90% | 10-minute average | SEV2 alert, kill non-critical sub-agents |
| Disk >85% | Any mount | SEV2, prune logs/backups per retention |
| Disk >95% | Any mount | SEV1, emergency cleanup |
| PostgreSQL connections >80% pool | 5-minute average | Optimize PgBouncer pool size |
| Redis evictions active | Any critical buffer | SEV2, increase memory or prune |
| Object storage >$3/month | Monthly | Review lifecycle, prune old backups |
| Monthly cost projection >$30 | 7-day forecast | Freeze non-critical work |

### 9.4 Capacity Planning Worksheet Template

```markdown
# Guinevere Capacity Planning Worksheet — <YYYY-MM>

## Current Resource Utilization

| Resource | Allocated | Used (avg) | Used (peak) | Utilization | Headroom |
|---|---:|---:|---:|---:|---:|
| CPU cores | 4 | <> | <> | <%> | <%> |
| RAM | 16GB | <> | <> | <%> | <%> |
| Disk (root) | <>GB | <> | <> | <%> | <%> |
| Disk (data) | <>GB | <> | <> | <%> | <%> |
| PgBouncer pool | <> | <> | <> | <%> | <%> |
| Redis total | <>GB | <> | <> | <%> | <%> |
| S3 storage | <>GB | <> | <> | $<>/mo | <> |
| R2 storage | <>GB | <> | <> | $<>/mo | <> |

## Service Resource Breakdown

| Service | RAM Est. | CPU Avg | Connections | Notes |
|---|---:|---:|---:|---|
| guinevere-core | ~<>MB | <%> | <> | Core daemon |
| guinevere-loops | ~<>MB | <%> | <> | Loop manager |
| guinevere-surveillance | ~<>MB | <%> | <> | Ingestion |
| guinevere-scheduler | ~<>MB | <%> | <> | Cron tasks |
| PostgreSQL | ~<>MB | <%> | <> | Database |
| PgBouncer | ~<>MB | <%> | <> | Connection pool |
| Redis (DB0-5) | ~<>MB | <%> | <> | Cache/queue |
| Prometheus | ~<>MB | <%> | N/A | Metrics |
| Grafana | ~<>MB | <%> | N/A | Dashboards |
| Loki | ~<>MB | <%> | N/A | Logs |

## Growth Projections (Next 6 Months)

| Resource | Current | +1mo | +3mo | +6mo | Trigger |
|---|---:|---:|---:|---:|---|
| Disk | <>GB | <>GB | <>GB | <>GB | 85% |
| DB size | <>GB | <>GB | <>GB | <>GB | <>GB |
| RAM peak | <>GB | <>GB | <>GB | <>GB | 14.4GB |
| Monthly cost | $<> | $<> | $<> | $<> | $30 |

## Scaling Options

| Option | Trigger | Cost Impact | Lead Time |
|---|---|---|---|
| Optimize queries/prompts | CPU/RAM pressure | $0 | Immediate |
| Reduce loop parallelism | RAM >90% | $0 | Immediate |
| Prune log retention | Disk >85% | $0 | Immediate |
| Upgrade VPS | Sustained resource pressure | +$5-10/mo | 1-2 days |
| Dedicated monitoring VPS | Prometheus/Grafana load too high | +$5-10/mo | 1 week |
```

---

## 10. Operational Governance

### 10.1 Document Review Schedule

| Document | Review Cadence | Responsible | Trigger |
|---|---|---|---|
| ObservabilitySpec | Monthly | Guinevere | Monthly observability review |
| SLO/SLA Spec | Monthly + quarterly recalibration | Guinevere + Samm | Scorecard + quarterly review |
| Cost/FinOps Model | Monthly + quarterly vendor eval | Guinevere + Samm | Monthly cost report |
| AgentLoopSpec | Quarterly | Guinevere | Quarterly strategic review |
| PersonaSafetyPolicy | Monthly + quarterly red-team | Guinevere + Samm | Monthly persona review |
| DataGovernance | Quarterly | Guinevere + Samm | Quarterly governance review |
| IncidentResponse | Quarterly drill | Guinevere | Quarterly red-team |
| ADR Index | Monthly backlog + quarterly full | Guinevere + Samm | Monthly ADR review |
| AcceptanceCriteria | Monthly | Guinevere | Monthly evidence audit |
| TechnicalArchitecture | Quarterly | Guinevere + Samm | Quarterly architecture review |
| AccessControl Matrix | Quarterly | Guinevere + Samm | Quarterly security review |
| EncryptionKeyManagement | Quarterly rotation + annual audit | Guinevere | Key rotation schedule |
| SecretsRotationRunbook | Quarterly rotation + annual audit | Guinevere | Rotation schedule |
| BRD/PRD | Annual | Guinevere + Samm | Annual strategy setting |

### 10.2 Policy Update Procedures

```
Policy Update Flow:
│
├── 1. Guinevere identifies need for update
│   ├── Source: monthly review, quarterly review, incident, ADR, Samm request
│   └── Document: proposed change with rationale
│
├── 2. Impact assessment
│   ├── Cross-reference check (which docs are affected?)
│   ├── Conflict scan (does this contradict existing policy?)
│   └── Risk assessment (what's the blast radius?)
│
├── 3. Draft update
│   ├── Write proposed changes
│   ├── Update cross-references
│   └── Create ADR if architectural decision
│
├── 4. Validation
│   ├── Verify no conflicts with higher-authority docs
│   ├── Run applicable tests (safety, security, SLO)
│   └── Evidence file created
│
├── 5. Samm approval
│   ├── Present change with evidence
│   ├── Samm reviews and approves/rejects
│   └── Record decision
│
└── 6. Implementation
    ├── Update document
    ├── Update ADR Index if needed
    ├── Update cross-references in dependent docs
    └── Write evidence artifact
```

### 10.3 ADR Creation Triggers

New ADRs must be created when:

| Trigger | Example |
|---|---|
| New technology selection | Choosing a new search provider |
| Architectural change | Adding monitoring VPS |
| Safety policy change | Modifying safe-word behavior |
| Cost model change | Changing budget cap or allocation |
| Integration change | Adding new wearable API |
| Governance change | New compliance requirement |
| Incident-driven | Root cause requires architectural fix |
| Quarterly review | Strategic direction change |

Current backlog (15 ADRs pending):

| ADR | Title | Priority | Readiness |
|---|---|---|---|
| ADR-030 | Requirements Traceability Matrix Governance | HIGH | RTM exists |
| ADR-031 | Acceptance Criteria Catalog Governance | HIGH | AC Catalog exists |
| ADR-032 | Privacy Impact Assessment / DPIA | HIGH | Needs policy |
| ADR-033 | Consent & Revocation Policy | CRITICAL | Needs policy |
| ADR-034 | Prompt Injection & Model Safety | HIGH | Spec exists |
| ADR-035 | RBAC/ABAC Access Control Matrix | HIGH | Matrix exists |
| ADR-036 | Secrets Rotation Runbook | HIGH | Runbook exists |
| ADR-037 | OpenAPI / AsyncAPI Contract Governance | MEDIUM | Future |
| ADR-038 | Event Schema & Webhook Contract | MEDIUM | Future |
| ADR-039 | Database ERD & Migration Strategy | HIGH | ERD exists |
| ADR-040 | SLO/SLA/Error Budget Policy | HIGH | Spec exists |
| ADR-041 | Incident Response & Postmortem Runbook | HIGH | Runbook exists |
| ADR-042 | Feature Flag Governance | MEDIUM | Future |
| ADR-043 | Product Analytics & Event Taxonomy | MEDIUM | Future |
| ADR-044 | Compliance & Data Residency Mapping | HIGH | Needs policy |

### 10.4 Cross-Reference Maintenance

Per AGENTS.md §4, every document must include a Related Documents section. Cross-reference maintenance rules:

| Rule | Enforcement |
|---|---|
| New document must cite all dependencies | Authoring checklist |
| Updated document must update dependent cross-references | Monthly review |
| Broken cross-reference is a defect | Evidence audit |
| Cross-reference to future document must be marked explicitly | "Future: <title>" notation |
| Quarterly full cross-reference scan | Quarterly governance review |

---

## 11. Evidence Standards & Audit

### 11.1 Evidence Directory Structure

```
evidence/
├── slo/
│   └── <YYYY-MM>/
│       ├── scorecard.md
│       ├── error-budget.md
│       ├── sla-report.md
│       ├── safety-invariants.md
│       ├── cost-budget.md
│       ├── incidents.md
│       └── actions.md
├── finops/
│   └── <YYYY-MM>/
│       ├── report.md
│       ├── budget-breakdown.md
│       ├── vendor-usage.md
│       ├── anomaly-log.md
│       ├── actions.md
│       └── approval-log.md
├── observability/
│   └── <YYYY-MM>-review.md
├── operations/
│   ├── weekly/
│   │   └── <YYYY>-W<WW>-report.md
│   └── quarterly/
│       └── <YYYY>-Q<Q>-review.md
├── annual/
│   └── <YYYY>/
│       ├── annual-report.md
│       ├── retrospective.md
│       ├── budget-plan.md
│       ├── security-audit.md
│       ├── compliance-review.md
│       └── tech-roadmap.md
├── incidents/
│   └── <date>-SEV<n>-<summary>/
│       ├── incident-report.md
│       ├── timeline.md
│       ├── evidence/
│       └── postmortem.md
├── persona-safety/
│   ├── <YYYY-MM>-review.md
│   ├── safe-word-runtime-<date>.md
│   ├── yandere-cap-<date>.md
│   └── drift-validation-<date>.md
├── security/
│   ├── <YYYY-MM>-posture.md
│   └── port-scan-<date>.md
├── dr/
│   ├── <YYYY-MM>-partial-drill.md
│   └── <YYYY>-Q<Q>-full-drill.md
├── red-team/
│   └── <YYYY>-Q<Q>/
│       └── <scenario>.md
├── agent-loop/
│   └── <task-id>/
│       ├── research-*.md
│       ├── plan.md
│       ├── delegation.md
│       ├── execution-*.md
│       ├── validation.md
│       ├── audit.md
│       ├── lessons.md
│       └── evidence-final.md
├── deployment/
│   └── systemd-core-<date>.md
├── memory/
│   └── backend-verify-<date>.md
├── surveillance/
│   └── android-ingestion-<date>.md
├── capacity/
│   └── <YYYY-MM>-review.md
├── architecture/
│   └── <YYYY>-Q<Q>-review.md
├── governance/
│   └── <YYYY>-Q<Q>-review.md
└── audit/
    └── <YYYY-MM>-evidence-audit.md
```

### 11.2 Evidence File Naming Convention

| Pattern | Use | Example |
|---|---|---|
| `<YYYY-MM>-<topic>.md` | Monthly recurring evidence | `2026-05-review.md` |
| `<YYYY>-Q<Q>-<topic>.md` | Quarterly evidence | `2026-Q2-review.md` |
| `<YYYY>-W<WW>-<topic>.md` | Weekly evidence | `2026-W22-report.md` |
| `<date>-SEV<n>-<summary>/` | Incident evidence folder | `2026-05-30-SEV1-core-down/` |
| `<component>-<date>.md` | Component-specific evidence | `systemd-core-2026-05-30.md` |
| `<topic>-<date>.md` | Topic-specific evidence | `port-scan-2026-05-30.md` |

### 11.3 Evidence Retention Policy

| Evidence Type | Retention | Class | Notes |
|---|---|---|---|
| SLO scorecards | Indefinite | Confidential | Governance evidence |
| Cost reports | 7 years | Confidential | Audit/regulatory class |
| Incident reports | Indefinite | Restricted/Critical (varies) | Formal hold |
| Observability reviews | Indefinite | Internal | Governance evidence |
| Weekly/monthly reports | Indefinite | Internal | Operational evidence |
| Red-team results | Indefinite | Confidential | Safety evidence |
| DR drill evidence | Indefinite | Confidential | Recovery confidence |
| Agent loop evidence | Indefinite | Internal | Quality evidence |
| Persona safety reviews | Indefinite | Restricted | Safety governance |

### 11.4 Audit Procedures

| Audit | Cadence | Scope | Method | Evidence |
|---|---|---|---|---|
| Evidence completeness | Monthly | All required artifacts exist | Filesystem scan + manifest check | `evidence/audit/<YYYY-MM>-evidence-audit.md` |
| SLO scorecard accuracy | Monthly | SLI values match Prometheus | Query comparison | Scorecard verification |
| Cost report accuracy | Monthly | Spend matches provider bills | Ledger reconciliation | FinOps verification |
| Cross-reference integrity | Quarterly | All document links valid | Link scan | Governance review |
| ADR compliance | Quarterly | All ADRs follow MADR format | Format audit | ADR Index review |
| Evidence retention | Quarterly | Files retained per policy | Age scan + policy check | Retention audit |
| Dashboard parity | Monthly | Grafana matches dashboard-as-code | Provisioning check | Drift report |
| Safety invariant | Continuous | Hard safety targets maintained | Automated alert | Alert evidence |

---

## 12. Annual Operations Calendar

| Month | Scheduled Operations | Special Notes |
|---|---|---|
| **January** | Monthly review + Q1 quarterly review + Annual strategy setting | Annual retrospective, budget planning, ADR full review |
| **February** | Monthly review | Standard monthly ops |
| **March** | Monthly review | Prepare Q1 quarterly report |
| **April** | Monthly review + Q2 quarterly review | Red-team, full DR drill, architecture review |
| **May** | Monthly review | Standard monthly ops |
| **June** | Monthly review | Mid-year checkpoint |
| **July** | Monthly review + Q3 quarterly review | Red-team, full DR drill, technology radar |
| **August** | Monthly review | Standard monthly ops |
| **September** | Monthly review | Prepare Q3 quarterly report |
| **October** | Monthly review + Q4 quarterly review | Red-team, full DR drill, budget forecast |
| **November** | Monthly review | Pre-annual preparation |
| **December** | Monthly review | Annual report preparation |

**Weekly (every Monday):**
- Weekly planning ritual at 08:00
- Week-in-review metrics summary
- Backlog grooming
- Dependency update review
- Documentation update check

**Daily:**
- 07:00 Morning Brief
- 12:00 Midday Check
- 17:00 Afternoon Review
- 21:00 Evening Wind-down + daily summary
- 00:00 Self-Evaluation + journal entry + drift update

---

## 13. Key PromQL Recording Rules Reference

Compiled from SLO/SLA Spec §9:

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

## 14. Dashboard Catalog Reference

All 12 dashboards from ObservabilitySpec §9.2 plus 8 SLO dashboards from SLO/SLA Spec §11:

| Dashboard | ID | File Path | Primary Panels |
|---|---|---|---|
| Overview | guinevere-overview | `monitoring/grafana/dashboards/overview.json` | Service health, incidents, loop state, cost, safe-mode |
| Infrastructure | guinevere-infrastructure | `monitoring/grafana/dashboards/infrastructure.json` | CPU, RAM, disk, network, systemd, Tailscale |
| API Runtime | guinevere-api-runtime | `monitoring/grafana/dashboards/api-runtime.json` | FastAPI latency, rate, errors, auth, rate limits |
| Agent Loop | guinevere-agent-loop | `monitoring/grafana/dashboards/agent-loop.json` | Phase duration, validation, audit, evidence, guardian |
| Sub-Agents | guinevere-subagents | `monitoring/grafana/dashboards/subagents.json` | Active, duration, file-output, compliance, retries |
| LLM & Cost | guinevere-llm-cost-latency | `monitoring/grafana/dashboards/llm-cost-latency.json` | Latency, tokens, cost, rate limits, context |
| Persona & Safety | guinevere-persona-safety | `monitoring/grafana/dashboards/persona-safety.json` | Safe-mode, safe-word, distress, yandere, drift |
| Surveillance | guinevere-surveillance-ingestion | `monitoring/grafana/dashboards/surveillance.json` | Event rate, queue, lag, redaction, blocked |
| Database & Memory | guinevere-database-memory | `monitoring/grafana/dashboards/database-memory.json` | PostgreSQL, PgBouncer, Redis, recall, pgvector |
| Backup & DR | guinevere-backup-dr | `monitoring/grafana/dashboards/backup-dr.json` | Freshness, duration, size, drills, encryption |
| Security & Access | guinevere-security-access | `monitoring/grafana/dashboards/security-access.json` | Access denied, break-glass, ingress, secrets |
| FinOps | guinevere-finops | `monitoring/grafana/dashboards/finops.json` | Cost, budget, anomaly, freeze state |
| SLO Overview | DB-SLO-001 | `monitoring/grafana/dashboards/slo-overview.json` | Monthly availability, budget, SEV counts |
| Service SLOs | DB-SLO-002 | `monitoring/grafana/dashboards/service-slos.json` | Per-service reliability |
| Latency SLOs | DB-SLO-003 | `monitoring/grafana/dashboards/latency-slos.json` | LLM/API/DB/Redis/loop p95/p99 |
| Loop Quality | DB-SLO-004 | `monitoring/grafana/dashboards/agent-loop-quality.json` | Completion, validation, evidence, LQS |
| Safety Invariants | DB-SLO-005 | `monitoring/grafana/dashboards/safety-invariants.json` | Safe-word, distress, yandere, redaction |
| Cost Budget | DB-SLO-006 | `monitoring/grafana/dashboards/cost-budget.json` | Daily, monthly, per-task, freeze |
| Backup DR SLOs | DB-SLO-007 | `monitoring/grafana/dashboards/backup-dr-slos.json` | Backup, RPO, restore, WAL |
| Monthly Scorecard | DB-SLO-008 | `monitoring/grafana/dashboards/monthly-scorecard.json` | All SLO targets, actuals, burn, breaches |

---

## 15. Unresolved Assumptions and Backlog

| ID | Assumption / Gap | Impact | Follow-up | Trigger |
|---|---|---|---|---|
| OPS-BG-001 | Exact resource utilization values TBD until runtime | Capacity planning worksheet has TBD values | Populate after runtime launch | MVP Phase 1 |
| OPS-BG-002 | Exact monthly dollar values per category need finalization (COST-BG-001) | Budget breakdown uses ranges | Finalize with Samm | Before runtime enforcement |
| OPS-BG-003 | GPT-5.5 token ceiling not yet converted to cost ceiling (COST-BG-002) | Daily/weekly cost alerts lack numeric thresholds | LLM cost control sheet | Before production budget claim |
| OPS-BG-004 | Surveillance activation blocked by policy gaps (AC-SURV-001/002/004) | Surveillance metrics cannot be validated | Surveillance Data Policy completion | Before surveillance activation |
| OPS-BG-005 | Memory recall evaluation spec not yet runtime-validated (AC-MEM-006) | Memory quality SLO cannot be measured | Memory Recall Eval Spec implementation | Before memory MVP exit |
| OPS-BG-006 | Provider switch tests not yet implemented (COST-BG-007) | Vendor lock-in risk remains theoretical | Switch drill evidence | Before production readiness |
| OPS-BG-007 | Several ADR backlog items (ADR-030 through ADR-044) not yet written | Governance gaps in traceability, consent, compliance | ADR implementation | Quarterly review cycle |
| OPS-BG-008 | 99.9% SLA aspiration requires 3 consecutive monthly scorecards at target | Cannot claim 99.9% until proven | Runtime operation for 3+ months | After MVP launch |
| OPS-BG-009 | Dedicated monitoring VPS is post-MVP (ADR-017) | All monitoring on shared VPS until load justifies migration | Monitoring rollout plan | When load justifies |
| OPS-BG-010 | Wearable integrations deferred post-MVP (ADR-021) | No wearable metrics until integration | Wearable procurement | Post-MVP |

---

## Appendix A — Quick Reference: Cadence Summary

| Cadence | Day/Time | Operation | Output |
|---|---|---|---|
| **Daily 00:00** | Every day | Self-evaluation | Journal, drift, procedural memory |
| **Daily 07:00** | Every day | Morning brief | Discord post |
| **Daily 12:00** | Every day | Midday check | Discord post |
| **Daily 17:00** | Every day | Afternoon review | Discord post |
| **Daily 21:00** | Every day | Evening wind-down | Daily summary to Discord |
| **Weekly** | Monday 08:00 | Weekly planning ritual | Weekly report + Discord |
| **Monthly** | 1st of month 06:00 | Monthly review (10 sections) | Multiple evidence files + email |
| **Quarterly** | 1st week of quarter | Strategic review (5 days) | Quarterly report + email |
| **Annual** | January | Annual strategy (2 weeks) | Annual report + email |
| **On event** | Any time | Incident response | Incident evidence folder |
| **On event** | After SEV0-SEV2 | Postmortem | Postmortem markdown |
| **On event** | After material loop | Lessons learned | Procedural memory + evidence |

---

## Appendix B — Guinevere Self-Improvement Loop Integration

The self-improvement loop (AgentLoopSpec §1.2) integrates with operations as follows:

```
Self-Improvement Loop Triggers:
│
├── Post-task: After every material SDLC loop completes
│   └── Analyze LQS, identify process improvements
│   └── Update procedural memory with lessons
│   └── Adjust future loop behavior
│
├── Nightly (00:00): Daily self-evaluation
│   └── Review day's performance metrics
│   └── Update drift scores
│   └── Journal reflection
│   └── Memory consolidation
│
├── Weekly (Monday): After weekly planning ritual
│   └── Review week's improvement backlog
│   └── Prioritize improvements
│   └── Plan implementation
│
└── Post-incident: After SEV0-SEV2 resolution
    └── Analyze root cause
    └── Identify preventive improvements
    └── Implement and validate fix
```

---

## Appendix C — Error Budget Math Reference

From SLO/SLA Spec §8:

```
Error Budget % = 100% - SLO Target %
Allowed Bad Events = Total Valid Events × Error Budget %
Burn Rate = Observed Error Rate / Error Budget Rate
Remaining Budget % = 100% - Consumed Budget %

Availability example (99.5% SLO):
  Monthly minutes = 43,200
  Allowed downtime = 216 minutes/month
  
Availability example (99.9% aspiration):
  Monthly minutes = 43,200
  Allowed downtime = 43.2 minutes/month

Availability example (99.0% floor):
  Monthly minutes = 43,200
  Allowed downtime = 432 minutes/month
```

Burn-rate alert windows (from SLO/SLA Spec §8.3):

| Alert | Window | Burn Rate | Severity |
|---|---|---:|---|
| Fast burn | 1h and 6h | ≥14.4× | SEV1 |
| Medium burn | 6h and 24h | ≥6× | SEV2 |
| Slow burn | 24h and 72h | ≥1× | SEV3 |
| Monthly projection | 7d forecast | exhaustion projected | SEV3/SEV2 |

---

*Research report complete. All sections grounded in Guinevere project specifications. 75 metric definitions, 31 SLIs, 38 SLOs, 20 dashboards, 10 metric categories, 5 operational cadences, and full evidence standards documented.*

---

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere | Initial research report for Internal Ops Manual — Operational Metrics, Reporting & Continuous Improvement. Grounded in ObservabilitySpec, SLO/SLA Spec, Cost/FinOps Model, AgentLoopSpec, AcceptanceCriteria, PersonaSafetyPolicy, DataGovernance, ADR Index, IncidentResponse, and TechnicalArchitecture. |

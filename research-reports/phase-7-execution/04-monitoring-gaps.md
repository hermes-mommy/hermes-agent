# Phase 7 Monitoring Gaps Report

> **Document**: esearch-reports/phase-7-execution/04-monitoring-gaps.md
> **Date**: 2026-06-06
> **Author**: Guinevere (Research Sub-agent)
> **Scope**: Hermes Prometheus metrics, alert rules, Grafana dashboards, Alertmanager routing, log scraping (Promtail)
> **Status**: Draft — for planner gate consumption

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Inventory](#2-current-state-inventory)
3. [VPS Live Probe Results](#3-vps-live-probe-results)
4. [Gap Analysis](#4-gap-analysis)
5. [Phase 7 Task Spec vs Batch Plan Mismatch](#5-phase-7-task-spec-vs-batch-plan-mismatch)
6. [Job-Name Canonical Recommendation](#6-job-name-canonical-recommendation)
7. [Alertmanager Routing Status](#7-alertmanager-routing-status)
8. [Recommended File Modifications](#8-recommended-file-modifications)
9. [Secrets Redacted Note](#9-secrets-redacted-note)

---

## 1. Executive Summary

Phase 7 monitoring is in a **pre-implementation state**. The following gaps exist:

| Area | Status | Criticality |
|---|---|---|
| Hermes-native Prometheus metrics | **MISSING** — endpoint only exposes custom guinevere_* + hermes_llm_* metrics, not Hermes-native hermes_gateway_* / hermes_safety_blocks_* etc. | BLOCKING |
| hermes-llm-routing scrape job | **BROKEN** — targets localhost:9191 inside Prometheus Docker container, can't reach host. Job does not appear in active targets. | BLOCKING |
| Hermes alert rules (0 of 4/5 required) | **MISSING** — zero Hermes alert rules exist | BLOCKING |
| Hermes Grafana dashboard | **MISSING** — 6 dashboards exist, none for Hermes | BLOCKING |
| Promtail regex for hermes-gateway.service | **MISSING** — regex only captures guinevere-*.service | HIGH |
| Gotify routing | **BROKEN** — all Gotify receivers point to FastAPI webhook instead of actual Gotify endpoint | HIGH |
| Grafana API query | **BLOCKED** — requires auth; credentials unavailable | INFO |

---

## 2. Current State Inventory

### 2.1 Config Files

| File | Path | State |
|---|---|---|
| Prometheus main config | monitoring/prometheus/prometheus.yml | Exists — 8 scrape jobs, no Hermes-native alerts |
| Alert rules | monitoring/prometheus/rules/guinevere-alerts.yml | Exists — 9 rules (SEV0-SEV3), 0 Hermes rules |
| Backup alert rules | monitoring/prometheus/rules/guinevere-backup-alerts.yml | Exists — 2 rules (SEV2) |
| Alertmanager config | monitoring/alertmanager/alertmanager.yml | Exists — SEV0/SEV1 to Gotify+Discord, SEV2 to Discord only |
| Promtail config | monitoring/promtail/promtail-config.yml | Exists — journal regex: guinevere-(.+)\\.service |
| Loki config | monitoring/loki/loki-config.yml | Exists — 720h retention, TSDB |
| Grafana datasources | monitoring/grafana/provisioning/datasources/datasources.yml | Exists — Prometheus, Loki, PostgreSQL |
| Grafana dashboard provisioning | monitoring/grafana/provisioning/dashboards/dashboards.yml | Exists — folder: Guinevere, path: /var/lib/grafana/dashboards |
| Docker compose | monitoring/compose.monitoring.yml | Exists — 8 monitoring services |
| Hermes config | hermes-config/config.yaml | Exists — observability.prometheus.enabled: true, metrics_port: 9191 |

### 2.2 Existing Grafana Dashboards (on VPS)

| File | Title | Size |
|---|---|---|
| guinevere-agent-loop.json | Guinevere / Agent Loop | 6,229 B |
| guinevere-database-memory.json | Guinevere / Database & Memory | 8,125 B |
| guinevere-finops.json | Guinevere / FinOps | 7,068 B |
| guinevere-infrastructure.json | Guinevere / Infrastructure | 8,112 B |
| guinevere-llm-cost-latency.json | Guinevere / LLM Cost & Latency | 5,338 B |
| guinevere-persona-safety.json | Guinevere / Persona Safety | 5,871 B |

**No guinevere-hermes.json dashboard exists.**

### 2.3 Hermes Config Observability Section (from hermes-config/config.yaml)

`yaml
observability:
  prometheus:
    enabled: true
    metrics_port: 9191
  logging:
    level: info
    format: json
    output: both  # stdout + loki
  insights:
    enabled: true
    cost_tracking: true
    latency_tracking: true
`

---

## 3. VPS Live Probe Results

### 3.1 Prometheus Targets (/api/v1/targets)

| Job | Target | Health | Last Error |
|---|---|---|---|
| prometheus | localhost:9090 | **up** | — |
| lertmanager | alertmanager:9093 | **up** | — |
| 
ode | node-exporter:9100 | **up** | — |
| loki | loki:3100 | **up** | — |
| astapi | host.docker.internal:8000 | **down** | dial tcp: lookup host.docker.internal: no such host |
| postgresql | postgres-exporter:9187 | **down** | context deadline exceeded |
| edis | redis-exporter:9121 | **down** | context deadline exceeded |

**hermes-llm-routing job is NOT present in active targets.** This confirms the scrape target localhost:9191 is unreachable from inside the Prometheus Docker container — localhost resolves to the container itself, not the host.

### 3.2 Prometheus Rules (/api/v1/rules)

All 11 rules (9 from guinevere-alerts.yml + 2 from guinevere-backup-alerts.yml) are loaded and evaluating:

| Group | Rules | State |
|---|---|---|
| guinevere-safety | 2 rules | inactive |
| guinevere-security | 3 rules | **1 firing** (GuinevereCriticalServiceDown for postgresql, fastapi, redis — expected, host.docker.internal issue) |
| guinevere-operations | 3 rules | inactive |
| guinevere-finops | 2 rules | inactive |
| guinevere-backup | 2 rules | inactive |

**Zero Hermes alert rules exist.**

### 3.3 Hermes Metrics Endpoint (localhost:9191/metrics)

The endpoint is reachable and returns metrics, but **only exposes custom application metrics** — NOT Hermes-native gateway metrics:

| Metric | Type | Labels |
|---|---|---|
| guinevere_requests_total | counter | endpoint, method, status |
| guinevere_request_duration_seconds | histogram | endpoint, method |
| guinevere_health_check_failures_total | counter | component |
| hermes_llm_calls_total | counter | model, status |
| hermes_llm_latency_seconds | histogram | — |
| hermes_llm_cost_usd_total | counter | — |
| hermes_fallback_activations_total | counter | from_model, to_model |

**Missing Hermes-native metrics** that the Phase 7 plan assumes:

| Expected Metric | Present? |
|---|---|
| hermes_gateway_uptime_seconds | ❌ |
| hermes_messages_total | ❌ |
| hermes_sessions_active | ❌ |
| hermes_response_latency_seconds_bucket | ❌ |
| hermes_safety_blocks_total | ❌ |
| hermes_memory_recall_latency_seconds_bucket | ❌ |
| hermes_model_calls_total | ❌ |
| hermes_hard_stop_events_total | ❌ |
| hermes_hook_execution_seconds_sum | ❌ |
| hermes_hook_executions_total | ❌ |
| hermes_cost_monthly_usd | ❌ |

**Root cause**: The Hermes gateway Python process at port 9191 uses prometheus_client with custom metric registrations (guinevere_* and hermes_llm_*). It does NOT use the Hermes-framework-native Prometheus instrumentation (hermes_gateway_*, hermes_messages_*, etc.). The Phase 7 batch plan's Steps 7.2.1-7.2.2 assume Hermes-native metrics will appear once the scrape job is added — this assumption is **false** without first instrumenting the Hermes gateway process to export Hermes-native metrics.

### 3.4 Grafana API Health

| Endpoint | Response |
|---|---|
| localhost:3000/api/health | HTTP 200 (ok) |
| localhost:3000/api/search | HTTP 401 — Unauthorized |
| localhost:3000/api/search?query=hermes | HTTP 401 — credentials unavailable |

Grafana API is **blocked** for unauthenticated queries. Cannot enumerate live dashboards or datasources via API.

### 3.5 Alertmanager Status

| Endpoint | Response |
|---|---|
| Prometheus → Alertmanager | Connected: http://alertmanager:9093/api/v2/alerts |

---

## 4. Gap Analysis

### Gap 1: Hermes-Native Metrics Not Exported (BLOCKING)

**Problem**: The Hermes gateway at port 9191 exports guinevere_* and hermes_llm_* custom metrics only. The Hermes framework-native Prometheus metrics (hermes_gateway_uptime_seconds, hermes_messages_total, hermes_sessions_active, hermes_response_latency_seconds_bucket, hermes_safety_blocks_total, hermes_hook_*, hermes_memory_recall_latency_seconds_bucket, hermes_model_calls_total, hermes_hard_stop_events_total, hermes_cost_monthly_usd) are NOT being exported.

**Impact**: ALL Phases 7.2.5 Hermes dashboard panels, 7.3.1 alert rules, and performance baseline metrics depend on these missing metrics. Without them, the Grafana dashboard would show empty panels and alert rules would never fire.

**Resolution path**:
- Option A (recommended): Instrument the Hermes gateway Python process to register and export Hermes-native metric names (hermes_gateway_uptime_seconds, hermes_messages_total, etc.) alongside existing guinevere_* and hermes_llm_* metrics.
- Option B (fallback): Rewrite Phase 7 alert rules and dashboard panels to use only the metrics that actually exist (guinevere_*, hermes_llm_*). This would mean abandoning Hermes-native panel expectations.

**Recommendation**: Option A with a mapping layer. Preserve existing hermes_llm_* metric names for Phase 6 backward compat, add Hermes-native metric names as aliases/duals.

### Gap 2: hermes-llm-routing Scrape Job Broken (BLOCKING)

**Problem**: prometheus.yml line 68: 	argets: ["localhost:9191"]. Since Prometheus runs in Docker, localhost resolves to the container, not the host. The hermes-llm-routing job does not appear in active targets.

**Fix**: Change to 	argets: ["host.docker.internal:9191"] (matching the astapi job pattern), and add a elabel_configs block to set instance: "hermes-gateway".

**Backward compat**: The existing job name hermes-llm-routing can be preserved OR renamed to hermes as Phase 7 desires. See Section 6.

### Gap 3: Promtail Regex Missing hermes-gateway.service (HIGH)

**Problem**: promtail-config.yml line 31: egex: "guinevere-(.+)\\.service". Does not match hermes-gateway.service.

**Fix**: Change regex to "(guinevere-(.+)\\.service|hermes-gateway.service)".

### Gap 4: Gotify Receivers Point to FastAPI Webhook Instead of Gotify (HIGH)

**Problem**: All 6 receivers in lertmanager.yml point to http://localhost:8000/internal/alertmanager/webhook — including the gotify-critical and gotify-warning receivers. No actual Gotify endpoint is configured. This means SEV0/SEV1 Gotify push notifications are silently sent to the FastAPI webhook instead of Gotify.

**Verification**: Run ssh guinevere-vps "curl -sf http://localhost:8000/internal/alertmanager/webhook -X POST -d '{\"test\":true}' -H 'Content-Type: application/json'" to confirm the webhook handler exists and how it routes.

**Recommended fix**: Add the actual Gotify endpoint URL (SOPS-managed) to the gotify-critical and gotify-warning receivers and remove the FastAPI webhook URL from those specific receivers.

### Gap 5: No Hermes Grafana Dashboard (HIGH)

**Problem**: No monitoring/grafana/dashboards/guinevere-hermes.json exists. Phase 7 Step 7.2.5 describes the dashboard creation but it has not been deployed.

**Dependency**: Blocked on Gap 1 (Hermes-native metrics must exist first, otherwise the dashboard panels will show "No data").

### Gap 6: No Hermes Alert Rules (BLOCKING)

**Problem**: guinevere-alerts.yml has 0 Hermes-specific rules. Phase 7 requires 4-5 new alert rules:

Per task spec:
1. hermes_gateway_down — SEV0/SEV1
2. hermes_response_latency_high — SEV2
3. hermes_safety_blocks_spike — SEV1
4. hermes_budget_near_cap — SEV2/SEV3

Per batch plan (Section 5):
1. GuinevereHermesGatewayDown — SEV1
2. GuinevereHermesResponseLatencyP95 — SEV2
3. GuinevereHermesSafetyBlocksSpike — SEV1
4. GuinevereHermesMemoryRecallLatencyP95 — SEV2
5. GuinevereHermesModelCallsAnomaly — SEV3

**Dependency**: Blocked on Gap 1 (metrics must exist for PromQL expressions to target).

---

## 5. Phase 7 Task Spec vs Batch Plan Mismatch

There is a **naming and count mismatch** between the Phase 7 task specification and the Phase 7 batch plan:

| Task Spec Alert | Batch Plan Alert | Severity Difference | Metric Difference |
|---|---|---|---|
| hermes_gateway_down | GuinevereHermesGatewayDown | SEV0 vs SEV1 | Both use up{job="hermes"} == 0 |
| hermes_response_latency_high | GuinevereHermesResponseLatencyP95 | SEV2 (both) | Both use hermes_response_latency_seconds_bucket |
| hermes_safety_blocks_spike | GuinevereHermesSafetyBlocksSpike | SEV1 (both) | Both use hermes_safety_blocks_total |
| hermes_budget_near_cap | **NOT IN BATCH PLAN** | SEV2/SEV3 | Uses hermes_cost_monthly_usd |
| — | GuinevereHermesMemoryRecallLatencyP95 | SEV2 | Extra rule in batch plan |
| — | GuinevereHermesModelCallsAnomaly | SEV3 | Extra rule in batch plan |

**Recommendation**: Use the batch plan's GuinevereHermes* naming convention (matches all existing alert names pattern Guinevere*) and add the hermes_budget_near_cap / GuinevereHermesBudgetNearCap rule that the task spec requires but the batch plan misses. Total: **6 rules**.

| Alert | Severity | Expression | Required Metric |
|---|---|---|---|
| GuinevereHermesGatewayDown | SEV1 | up{job="hermes"} == 0 | up (built-in) |
| GuinevereHermesResponseLatencyP95 | SEV2 | histogram_quantile(0.95, rate(hermes_response_latency_seconds_bucket[5m])) > 5 | hermes_response_latency_seconds_bucket — **MISSING** |
| GuinevereHermesSafetyBlocksSpike | SEV1 | ate(hermes_safety_blocks_total[5m]) > rate(hermes_safety_blocks_total[30m]) * 2 | hermes_safety_blocks_total — **MISSING** |
| GuinevereHermesBudgetNearCap | SEV2 | hermes_cost_monthly_usd > 24.0 | hermes_cost_monthly_usd — **MISSING** |
| GuinevereHermesMemoryRecallLatencyP95 | SEV2 | histogram_quantile(0.95, rate(hermes_memory_recall_latency_seconds_bucket[5m])) > 2 | hermes_memory_recall_latency_seconds_bucket — **MISSING** |
| GuinevereHermesModelCallsAnomaly | SEV3 | 3-sigma anomaly on hermes_model_calls_total | hermes_model_calls_total — **MISSING** |

---

## 6. Job-Name Canonical Recommendation

### Current State

prometheus.yml line 66: job_name: "hermes-llm-routing" (Phase 6 name).

### Phase 7 Desired

The Phase 7 batch plan uses job_name: "hermes" in Step 7.2.1.

### Impact Analysis

| Change | Impact |
|---|---|
| Rename hermes-llm-routing → hermes | All existing alert rules reference job="hermes-llm-routing" — but currently NO rules reference it because no Hermes alerts exist yet. The GuinevereLLMCostSpike and GuinevereLLMCostSpikeWarning rules use guinevere_llm_cost_usd_total (no job filter), so they are unaffected. |
| Keep hermes-llm-routing | The batch plan's target verification and alert expressions use job="hermes" which would fail. Would need to update all batch plan commands and alert expressions. |

### Recommendation

**Rename to hermes** (canonical, matches astapi, 
ode, loki, etc.). Add the elabel_configs block to set instance: "hermes-gateway". This is a clean rename since:

1. No existing alert rules reference hermes-llm-routing job label.
2. The hermes-llm-routing job is currently broken (never scrapes successfully), so renaming carries zero regression risk.
3. The batch plan already uses job="hermes" consistently.

**Exact change to prometheus.yml**:

`yaml
# Job 8: Hermes Gateway metrics — Phase 7
# Replaces Phase 6 hermes-llm-routing job (old targets: localhost:9191 — broken in Docker)
- job_name: "hermes"
  metrics_path: "/metrics"
  scrape_interval: 15s
  static_configs:
    - targets: ["host.docker.internal:9191"]
  relabel_configs:
    - source_labels: [__address__]
      target_label: instance
      replacement: "hermes-gateway"
`

---

## 7. Alertmanager Routing Status

### Current Routing Table

| sev_level | Receiver(s) | Repeat Interval | Gotify Actually Works? |
|---|---|---|---|
| SEV0 | discord-critical + gotify-critical | 15m | **No** — gotify-critical points to FastAPI webhook |
| SEV1 | discord-critical + gotify-warning | 30m | **No** — gotify-warning points to FastAPI webhook |
| SEV2 | discord-warning | 4h | N/A (Discord only) |
| SEV3 | discord-info | 12h | N/A (Discord only) |
| SEV4 | discord-info | 24h | N/A (Discord only) |

### Gotify Receiver Analysis

`yaml
# Lines 86-95 of alertmanager.yml
- name: "gotify-critical"
  webhook_configs:
    - url: "http://localhost:8000/internal/alertmanager/webhook"  # ← NOT Gotify!
      send_resolved: false

- name: "gotify-warning"
  webhook_configs:
    - url: "http://localhost:8000/internal/alertmanager/webhook"  # ← NOT Gotify!
      send_resolved: false
`

All receivers use http://localhost:8000/internal/alertmanager/webhook (FastAPI webhook). The gotify-critical and gotify-warning receivers are **misconfigured** — they should point to the actual Gotify push notification endpoint. The actual Gotify URL is not present in the visible .env file or lertmanager.yml.

### Phase 7 Hermes Routing Needs

For Hermes alerts specifically:

| Alert | Severity | Desired Routing |
|---|---|---|
| GuinevereHermesGatewayDown | SEV1 | discord-critical + gotify-critical (after Gotify URL fix) |
| GuinevereHermesResponseLatencyP95 | SEV2 | discord-warning |
| GuinevereHermesSafetyBlocksSpike | SEV1 | discord-critical + gotify-critical |
| GuinevereHermesBudgetNearCap | SEV2 | discord-warning |
| GuinevereHermesMemoryRecallLatencyP95 | SEV2 | discord-warning |
| GuinevereHermesModelCallsAnomaly | SEV3 | discord-info |

The existing routing tree already handles Hermes alerts correctly by sev_level matching — no new routes are strictly needed. However, adding explicit routes for lertname matching would reduce the risk of misrouting:

`yaml
# Recommended addition to alertmanager.yml route:
- match:
    alertname: "GuinevereHermesGatewayDown|GuinevereHermesSafetyBlocksSpike"
  receiver: "discord-critical"
  repeat_interval: 15m
  continue: true
- match:
    alertname: "GuinevereHermesGatewayDown|GuinevereHermesSafetyBlocksSpike"
  receiver: "gotify-critical"
  repeat_interval: 15m
- match:
    alertname: "GuinevereHermesResponseLatencyP95|GuinevereHermesBudgetNearCap|GuinevereHermesMemoryRecallLatencyP95"
  receiver: "discord-warning"
  repeat_interval: 4h
- match:
    alertname: "GuinevereHermesModelCallsAnomaly"
  receiver: "discord-info"
  repeat_interval: 12h
`

**Note**: These routes are optional if the sev_level label is correctly set on each Hermes alert rule (which it will be), because the existing routing tree already dispatches by sev_level. The explicit lertname routes above are defense-in-depth.

---

## 8. Recommended File Modifications

### Files to Modify

| # | File Path | Change | Priority |
|---|---|---|---|
| 1 | monitoring/prometheus/prometheus.yml | Replace hermes-llm-routing job with hermes job using host.docker.internal:9191 + elabel_configs | **P0 — BLOCKING** |
| 2 | monitoring/prometheus/rules/guinevere-alerts.yml | Add new group guinevere-hermes with 6 alert rules (see Section 5) | **P0 — BLOCKING** |
| 3 | monitoring/promtail/promtail-config.yml | Update journal regex to include hermes-gateway.service | **P1 — HIGH** |
| 4 | monitoring/alertmanager/alertmanager.yml | Fix gotify-critical and gotify-warning receivers to point to actual Gotify endpoint | **P1 — HIGH** |
| 5 | monitoring/.env | Add GOTIFY_URL and GOTIFY_TOKEN (SOPS-managed) | **P1 — HIGH** |
| 6 | monitoring/alertmanager/alertmanager.yml | Optionally add Hermes-specific routing entries for defense-in-depth | **P2 — MEDIUM** |

### Files to Create

| # | File Path | Description | Priority |
|---|---|---|---|
| 1 | monitoring/grafana/dashboards/guinevere-hermes.json | Hermes Gateway dashboard (from Phase 7 batch plan Step 7.2.5 template) | **P0 — BLOCKING** |
| 2 | docs/40-operations/runbooks/hermes-gateway-down.md | Runbook for Hermes gateway down (referenced by alert rule) | **P2 — MEDIUM** |
| 3 | docs/40-operations/runbooks/hermes-latency.md | Runbook for latency alert | **P2 — MEDIUM** |
| 4 | docs/40-operations/runbooks/hermes-cost-anomaly.md | Runbook for cost anomaly alert | **P2 — MEDIUM** |
| 5 | docs/40-operations/runbooks/hermes-safety-spike.md | Runbook for safety blocks spike | **P2 — MEDIUM** |

### Files to Read (For Metric Instrumentation Reference)

| # | File Path | Purpose |
|---|---|---|
| 1 | Hermes gateway source code (FastAPI routes/metrics handler) | Identify where guinevere_* and hermes_llm_* metrics are registered, to add Hermes-native metric names |

---

## 9. Implementation Dependency Graph

`
Gap 1: Instrument Hermes-native metrics (hermes_gateway_*, hermes_safety_blocks_*, etc.)
  └─► Gap 2: Fix scrape job (hermes-llm-routing → hermes + host.docker.internal)
       └─► Gap 6: Add 6 Hermes alert rules + reload Prometheus
            └─► Gap 7: Add Hermes-specific routing in Alertmanager
       └─► Gap 5: Create Hermes Grafana dashboard

Gap 3: Fix Promtail regex (hermes-gateway.service) ──► independent

Gap 4: Fix Gotify receiver endpoints ──► independent

Gap 7: Add Hermes SEV0/SEV2 routing ──► depends on Gap 4 (Gotify URLs)
`

---

## 10. Secrets Redacted Note

- No Grafana admin credentials were exposed.
- No Discord webhook URLs were queried or exposed.
- No Gotify token was queried or exposed.
- The FastAPI webhook URL at localhost:8000/internal/alertmanager/webhook is a local internal endpoint.
- .env file contains only placeholder values (CHANGE_ME_VIA_SOPS).
- SOPS-encrypted files were not decrypted or inspected.

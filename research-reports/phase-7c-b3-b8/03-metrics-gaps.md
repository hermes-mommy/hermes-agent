# Phase 7c B3-B8 Hermes Runtime Metrics Gaps

> **Document**: research-reports/phase-7c-b3-b8/03-metrics-gaps.md
> **Date**: 2026-06-06
> **Author**: Guinevere (Research Sub-agent)
> **Scope**: B3-B8 runtime metrics, safety plugin wiring, exact metric names, code locations, and integration points
> **Status**: Draft — for planner gate consumption

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Metric Exports — Complete Catalog](#2-current-metric-exports--complete-catalog)
3. [Metrics Referenced but Not Exported](#3-metrics-referenced-but-not-exported)
4. [Safety Plugin Metrics Gap (Zero Prometheus Export)](#4-safety-plugin-metrics-gap-zero-prometheus-export)
5. [Grafana Dashboard Metric Dependencies](#5-grafana-dashboard-metric-dependencies)
6. [Alert Rule Metric Dependencies](#6-alert-rule-metric-dependencies)
7. [Additional Hermes-Native Metrics Required by Batch Plan](#7-additional-hermes-native-metrics-required-by-batch-plan)
8. [Metric Name Mismatches Between Sources](#8-metric-name-mismatches-between-sources)
9. [Missing Prometheus Gauge Metrics (Runtime State)](#9-missing-prometheus-gauge-metrics-runtime-state)
10. [Integration Points — Where to Add Metrics](#10-integration-points--where-to-add-metrics)
11. [Registry Port Conflict Note](#11-registry-port-conflict-note)
12. [Canonical Metric Name Table for B8 Implementation](#12-canonical-metric-name-table-for-b8-implementation)
13. [Implementation Order and Dependencies](#13-implementation-order-and-dependencies)

---

## 1. Executive Summary

Phase 7c B3-B8 requires **Hermes runtime metrics** and **safety plugin Prometheus wiring**. The current state has severe gaps:

| Area | Status | Blocking |
|---|---|---|
| `llm_metrics.py` exports (Phase 6) | 4 metric families, working | ✅ |
| `main.py` FastAPI metrics | 3 metric families, working | ✅ |
| **Safety plugin Prometheus metrics** | **ZERO metrics exported** — all gates use `structlog` only | **❌ B8 BLOCKING** |
| **Hermes-native metrics** (hermes_safety_*, hermes_gateway_*, hermes_memory_*, hermes_hook_*, hermes_rate_limit_*) | **ZERO exported** | **❌ B3/B4 BLOCKING** |
| **Grafana dashboard placeholder panels** | 6 panels, 4 show `or vector(0)` because metrics absent | **❌ B7 BLOCKING** |
| **Alert rules that reference non-existent metrics** | 5 alert rules reference metrics that don't exist | **❌ B6 BLOCKING** |
| **Metric name mismatch** (alert rules use `guinevere_llm_cost_usd_total`, code emits `hermes_llm_cost_usd_total`) | 1 confirmed, more may exist | **❌ B6** |
| **Promtail regex** | Now captures `hermes-gateway.service` (already fixed) | ✅ |
| **Scrape job** | Uses `host.docker.internal:9191` (already fixed per 04-monitoring-gaps.md) | ✅ |

**Bottom line**: 24 metrics need to be created. Zero exist today outside the 7 already-exported Phase 6/FastAPI metric families. Every PromQL expression in the Hermes dashboard and Hermes alert rules targets metrics that don't exist.

---

## 2. Current Metric Exports — Complete Catalog

### 2.1 `src/core/services/llm_metrics.py` (listens on **port 9191**)

| Metric | Type | Labels | Code Location | Called From |
|---|---|---|---|---|
| `hermes_llm_calls_total` | Counter | `model`, `status` | llm_metrics.py:21-25 | llm_router.py:185 (error), llm_router.py:238 (success) |
| `hermes_llm_latency_seconds` | Histogram | `model` | llm_metrics.py:27-32 | llm_router.py:239 |
| `hermes_llm_cost_usd_total` | Counter | `model` | llm_metrics.py:34-38 | llm_router.py:240 |
| `hermes_fallback_activations_total` | Counter | `from_model`, `to_model` | llm_metrics.py:40-44 | llm_router.py:190 |

**Observers** (llm_metrics.py:70-90):
- `observe_call(model, status)` — line 70
- `observe_latency(model, seconds)` — line 78
- `observe_cost(model, cost_usd)` — line 83
- `observe_fallback(from_model, to_model)` — line 88

**Server start**: `start_llm_metrics_server(port=9191)` called from `main.py:45` during app lifespan. Guard prevents double-start.

**Test file**: `tests/hermes/test_llm_metrics.py` — covers all 4 metric families and integration with LLMRouter.

### 2.2 `src/core/main.py` (FastAPI app, `/metrics` endpoint)

| Metric | Type | Labels | Code Location | Description |
|---|---|---|---|---|
| `guinevere_requests_total` | Counter | `method`, `endpoint`, `status` | main.py:155-159 | HTTP request count |
| `guinevere_request_duration_seconds` | Histogram | `method`, `endpoint` | main.py:160-164 | Request duration in seconds |
| `guinevere_health_check_failures_total` | Counter | `component`, `check` | main.py:165-169 | Component health check failures |

These are registered in the **FastAPI process** (port 8000), **not** in the Hermes metrics server (port 9191). They are scraped by the `fastapi` job in prometheus.yml.

### 2.3 `src/surveillance/secret_scanner.py`

| Metric | Type | Labels | Code Location | Notes |
|---|---|---|---|---|
| (uses `prometheus_client`) | — | — | secret_scanner.py | Uses `Counter` and `Histogram` but for internal surveillance metrics, not Hermes runtime |

### 2.4 Summary of Exported Metrics

**Total currently exported**: 7 metric families across 2 processes:
- **Port 9191** (Hermes gateway process): 4 families (all hermes_llm_*)
- **Port 8000** (FastAPI process): 3 families (all guinevere_*)

---

## 3. Metrics Referenced but Not Exported

### 3.1 Dashboard-Referenced Metrics (Zero Export)

These metrics appear in Grafana dashboard JSON files or alert rules but are **not created anywhere** in the codebase:

| Metric | Appears In | Expected Type | Expected Labels | Status |
|---|---|---|---|---|
| `guinevere_safety_violations_total` | persona-safety dashboard:panel 1 | Counter | `severity` | **❌ NOT EXPORTED** |
| `guinevere_safemode_state` | persona-safety dashboard:panel 2 | Gauge | (none) | **❌ NOT EXPORTED** |
| `guinevere_safeword_events_total` | persona-safety dashboard:panel 3+4, alert rule `GuinevereSafeWordBypassAttempt` | Counter | `type` | **❌ NOT EXPORTED** |
| `guinevere_public_ingress_detected` | alert rule `GuineverePublicIngressDetected` | Gauge | (none) | **❌ NOT EXPORTED** |
| `guinevere_log_redaction_failures_total` | alert rule `GuinevereLogRedactionFailure` | Counter | (none) | **❌ NOT EXPORTED** |
| `guinevere_secret_access_total` | alert rule `GuinevereSecretAccessOutsideStartup` | Counter | `phase` | **❌ NOT EXPORTED** |
| `guinevere_subagent_file_missing_total` | alert rule `GuinevereSubagentFileOutputMissingSustained` | Counter | (none) | **❌ NOT EXPORTED** |
| `guinevere_backup_last_restore_drill_timestamp` | alert rule `GuinevereRestoreDrillOverdue` | Gauge | (none) | **❌ NOT EXPORTED** |
| `guinevere_backup_last_success_timestamp` | backup alert rules | Gauge | (none) | **❌ NOT EXPORTED** |

### 3.2 Grafana Dashboard Cross-Reference

**guinevere-persona-safety.json** panels:
- Panel 1: `guinevere_safety_violations_total` — **NOT EXPORTED**
- Panel 2: `guinevere_safemode_state` — **NOT EXPORTED**
- Panel 3: `guinevere_safeword_events_total` — **NOT EXPORTED**
- Panel 4: `guinevere_safeword_events_total{type="hard_stop"}` — **NOT EXPORTED**

**guinevere-hermes.json** panels (Phase 7c):
- Panel 6: `sum(rate(hermes_safety_blocks_total[5m]))` — **NOT EXPORTED** (placeholder: `or vector(0)`)
- Panel 7: `sum(increase(hermes_hard_stop_events_total[24h]))` — **NOT EXPORTED** (placeholder: `or vector(0)`)
- Panel 8: `...or vector(0)` — proxied via `hermes_llm_latency_seconds` as fallback
- Panel 9: uses `hermes_llm_calls_total` — ✅ EXISTS (but is aggregate, not per-model breakdown)

---

## 4. Safety Plugin Metrics Gap (Zero Prometheus Export)

### 4.1 `src/hermes/safety_plugin.py` — Gate Trace Table

Every safety gate action is logged via `structlog` but **zero metrics are emitted**:

| Gate | Action | Current Tracking | Prometheus Metric Needed | File:Line |
|---|---|---|---|---|
| **G01** HARD STOP (exact) | Returns block + updates SessionSafetyState | `logger.warning("gate_01_hard_stop_exact", ...)` | `hermes_hard_stop_events_total{trigger="exact"}` | safety_plugin.py:496-505 |
| **G01** HARD STOP (semantic) | Returns block + updates SessionSafetyState | `logger.warning("gate_01_hard_stop_semantic", ...)` | `hermes_hard_stop_events_total{trigger="semantic"}` | safety_plugin.py:517-526 |
| **G01** HardStopHandler (defense) | Returns block + updates SessionSafetyState | `logger.warning("gate_01_hard_stop_handler", ...)` | `hermes_hard_stop_events_total{trigger="handler"}` | safety_plugin.py:539-547 |
| **G02** Distress D2+ | Updates safe_mode_active, yandere_level=0 | `logger.warning("gate_02_distress_detected", ...)` | `hermes_distress_events_total{level="D2"}` | safety_plugin.py:613-623 |
| **G02** Distress D3/D4 | Returns block | `logger.warning(...)` + returns block dict | `hermes_distress_events_total{level="D3\|D4"}` | safety_plugin.py:625-634 |
| **G03** Drift detection | Computes SHA-256, updates drift_score | `logger.warning("gate_03_drift_alert", ...)` | `hermes_drift_score`, `hermes_drift_events_total{action=rollback\|alert}` | safety_plugin.py:743-755 |
| **G04** Recovery trigger | Clears HARD STOP state | `logger.info("gate_04_recovery", ...)` | `hermes_recovery_events_total` | safety_plugin.py:567-572 |
| **G05** Forbidden CRITICAL | Returns None (block response) | `logger.error("gate_05_forbidden_critical", ...)` | `hermes_forbidden_blocks_total{pattern_id="F-01..F-10"}` | safety_plugin.py:904-912 |
| **G05** Forbidden HIGH | Rewrites response | `logger.warning("gate_05_forbidden_high", ...)` | `hermes_forbidden_rewrites_total{pattern_id="F-11..F-15"}` | safety_plugin.py:915-921 |
| **G06** Secret scanner | Redacts secrets, counts redactions | `logger.warning("gate_06_secret_redacted", ...)` | `hermes_secret_redactions_total` | safety_plugin.py:939-943 |
| **G07** Yandere ceiling check | Raises YandereSafetyError if >Y5 | `logger.error("gate_07_yandere_ceiling_breach", ...)` | `hermes_yandere_violations_total` | safety_plugin.py:655-663 |
| **G08** Yandere semantic | Rewrites Y6-adjacent content | `logger.warning("gate_08_yandere_y6_adjacent", ...)` | `hermes_yandere_semantic_rewrites_total` | safety_plugin.py:963-975 |
| **G09** Auth matrix block | Returns block, increments blocked_tool_count | `logger.warning("gate_09_auth_blocked", ...)` | `hermes_auth_blocks_total{tool,operation,auth_level}` | safety_plugin.py:813-827 |
| **G10** Consent (deferred) | Logs only | `logger.debug("gate_10_consent_deferred", ...)` | `hermes_consent_checks_total{tool}` | safety_plugin.py:787-792 |

**Total missing safety metrics**: **14 counters + 2 gauges**.

### 4.2 SessionSafetyState Fields Never Exported

`SessionSafetyState` (safety_plugin.py:196-215) tracks these fields but **none are exported to Prometheus**:

| Field | Type | Prometheus Metric Needed | Notes |
|---|---|---|---|
| `hard_stop_active` | bool | `hermes_session_hard_stop_active{gauge}` | Per-session — could aggregate to `sum()` |
| `safe_mode_active` | bool | `hermes_session_safe_mode_active{gauge}` | Per-session — could aggregate to `sum()` |
| `yandere_level` | int | `hermes_session_yandere_level{gauge}` | Per-session |
| `distress_level` | int | `hermes_session_distress_level{gauge}` | Per-session |
| `drift_score` | float | `hermes_session_drift_score{gauge}` | Per-session |
| `blocked_tool_count` | int | (counter derivative) | Use `hermes_auth_blocks_total` instead |
| `secret_redaction_count` | int | (counter derivative) | Use `hermes_secret_redactions_total` instead |

### 4.3 `src/hermes_plugins/commands_system/*.py` — State Mutation Hooks

These Hermes Discord commands mutate persona state via the external `guinevere_safety` plugin (Redis DB5):

| Command File | Action | Current Tracking | Prometheus Needed |
|---|---|---|---|
| `reward.py` | Set reward tier | `StateManager.set_reward()` — Redis only | `hermes_reward_changes_total{tier}` |
| `punishment.py` | Set punishment level | `StateManager.set_punishment()` — Redis only | `hermes_punishment_changes_total{level}` |

### 4.4 `hermes-config/plugins/guinevere_safety/` — External Hermes Plugin

The external plugin tracks persona state in Redis DB5 but never exposes to Prometheus:

| Redis Key | Semantic | Current | Prometheus Metric Needed |
|---|---|---|---|
| `guinevere:punishment_level` | 0-5 | Redis only | `guinevere_punishment_level{gauge}` |
| `guinevere:reward_tier` | 0-5 | Redis only | `guinevere_reward_tier{gauge}` |
| `guinevere:distress_state` | 0-4 | Redis only | `guinevere_distress_state{gauge}` |
| `guinevere:yandere_level` | 4 (immutable) | Redis only | `guinevere_yandere_level{gauge}` |
| `guinevere:interaction_count` | daily count | Redis only | `guinevere_interaction_count{gauge}` |
| `guinevere:mood_variant` | string | Redis only | (hard to expose — use info metric or enum) |

---

## 5. Grafana Dashboard Metric Dependencies

### 5.1 `guinevere-hermes.json` (Hermes Gateway Dashboard)

| Panel ID | Title | PromQL Expression | Metric Required | Status |
|---|---|---|---|---|
| 1 | Gateway Status | `up{job="hermes"}` | `up` (built-in) | ✅ Exists (scrape job) |
| 2 | LLM Calls Rate | `rate(hermes_llm_calls_total[5m])` | `hermes_llm_calls_total` | ✅ Exists (Phase 6) |
| 3 | LLM Latency (p50/p95/p99) | `histogram_quantile(0.95, rate(hermes_llm_latency_seconds_bucket[5m]))` | `hermes_llm_latency_seconds_bucket` | ✅ Exists (Phase 6) |
| 4 | Cumulative LLM Cost | `hermes_llm_cost_usd_total` / `rate(...)` | `hermes_llm_cost_usd_total` | ✅ Exists (Phase 6) |
| 5 | Fallback Activations | `rate(hermes_fallback_activations_total[5m])` | `hermes_fallback_activations_total` | ✅ Exists (Phase 6) |
| 6 | Safety Blocks | `sum(rate(hermes_safety_blocks_total[5m])) or vector(0)` | `hermes_safety_blocks_total` | **❌ MISSING** (shows 0) |
| 7 | HARD STOP Events | `sum(increase(hermes_hard_stop_events_total[24h])) or vector(0)` | `hermes_hard_stop_events_total` | **❌ MISSING** (shows 0) |
| 8 | Memory Recall Latency | `(rate(hermes_llm_latency_seconds_sum[5m]) / rate(hermes_llm_latency_seconds_count[5m])) or vector(0)` | `hermes_llm_latency_seconds` (proxy) | ⚠️ Proxied (dedicated `hermes_memory_recall_latency_seconds` pending) |
| 9 | Model Call Rate | `rate(hermes_llm_calls_total[5m])` | `hermes_llm_calls_total` | ✅ Exists (aggregate only) |

### 5.2 `guinevere-persona-safety.json` (Persona Safety Dashboard)

| Panel ID | Title | Expression | Metric Required | Status |
|---|---|---|---|---|
| 1 | SEV Events | `guinevere_safety_violations_total` | `guinevere_safety_violations_total` | **❌ MISSING** |
| 2 | Consent Status | `guinevere_safemode_state` | `guinevere_safemode_state` | **❌ MISSING** |
| 3 | Safe Word Triggers | `guinevere_safeword_events_total` | `guinevere_safeword_events_total` | **❌ MISSING** |
| 4 | Hard Stop Events | `guinevere_safeword_events_total{type="hard_stop"}` | `guinevere_safeword_events_total{type}` | **❌ MISSING** |

---

## 6. Alert Rule Metric Dependencies

### 6.1 Current Alert Rules (`guinevere-alerts.yml`)

| Alert Rule | PromQL Expression | Metric Required | Exists? |
|---|---|---|---|
| `GuinevereSafeWordBypassAttempt` | `increase(guinevere_safeword_events_total[5m]) > 0` | `guinevere_safeword_events_total` | **❌ MISSING** |
| `GuineverePublicIngressDetected` | `guinevere_public_ingress_detected > 0` | `guinevere_public_ingress_detected` | **❌ MISSING** |
| `GuinevereLogRedactionFailure` | `increase(guinevere_log_redaction_failures_total[15m]) > 0` | `guinevere_log_redaction_failures_total` | **❌ MISSING** |
| `GuinevereSecretAccessOutsideStartup` | `increase(guinevere_secret_access_total{phase!="startup"}[30m]) > 0` | `guinevere_secret_access_total` | **❌ MISSING** |
| `GuinevereCriticalServiceDown` | `up{job=~"fastapi\|postgresql\|redis"} == 0` | `up` (built-in) | ✅ |
| `GuinevereNonCriticalServiceDown` | `up{job=~"node\|loki\|alertmanager"} == 0` | `up` (built-in) | ✅ |
| `GuinevereSubagentFileOutputMissingSustained` | `increase(guinevere_subagent_file_missing_total[30m]) > 5` | `guinevere_subagent_file_missing_total` | **❌ MISSING** |
| `GuinevereLLMCostSpike` | `rate(guinevere_llm_cost_usd_total[1h]) > 0.50` | `guinevere_llm_cost_usd_total` | **❌ NAME MISMATCH** (code uses `hermes_llm_cost_usd_total`) |
| `GuinevereLLMCostSpikeWarning` | `rate(guinevere_llm_cost_usd_total[1h]) > 0.25` | `guinevere_llm_cost_usd_total` | **❌ NAME MISMATCH** |
| `GuinevereRestoreDrillOverdue` | `time() - guinevere_backup_last_restore_drill_timestamp > 604800` | `guinevere_backup_last_restore_drill_timestamp` | **❌ MISSING** |
| `GuinevereBackupStale` | `time() - guinevere_backup_last_success_timestamp > 93600` | `guinevere_backup_last_success_timestamp` | **❌ MISSING** |
| `GuinevereBackupMissing` | `guinevere_backup_last_success_timestamp == 0` | `guinevere_backup_last_success_timestamp` | **❌ MISSING** |

### 6.2 Hermes Alert Rules (Already in config, but metrics missing)

| Alert Rule | PromQL Expression | Metric Required | Exists? |
|---|---|---|---|
| `GuinevereHermesGatewayDown` | `up{job="hermes"} == 0` | `up` (built-in) | ✅ |
| `GuinevereHermesLatencyHigh` | `histogram_quantile(0.95, rate(hermes_llm_latency_seconds_bucket[5m])) > 5` | `hermes_llm_latency_seconds_bucket` | ✅ |
| `GuinevereHermesSafetyBlocksSpike` | `rate(hermes_safety_blocks_total[5m]) > 10` | `hermes_safety_blocks_total` | **❌ MISSING** |
| `GuinevereHermesBudgetNearCap` | `hermes_llm_cost_usd_total > 24` | `hermes_llm_cost_usd_total` | ✅ (name matches code) |
| `GuinevereHermesMemoryRecallLatency` | `rate(hermes_llm_latency_seconds_sum[5m]) / rate(...) > 10` | `hermes_llm_latency_seconds` (proxy) | ⚠️ Proxied (dedicated metric pending) |
| `GuinevereHermesModelCallsAnomaly` | `rate(hermes_llm_calls_total[5m]) > 100` | `hermes_llm_calls_total` | ✅ (aggregate) |

---

## 7. Additional Hermes-Native Metrics Required by Batch Plan

Beyond the safety metrics above, the Phase 7c batch plan (derived from 04-monitoring-gaps.md §4.1) lists these **Hermes-native metrics** that should be instrumented in the gateway process for a complete runtime observability layer:

| Metric | Type | Labels | Purpose | Priority |
|---|---|---|---|---|
| `hermes_gateway_uptime_seconds` | Gauge | — | Gateway process uptime | P1 |
| `hermes_messages_total` | Counter | `direction` (inbound/outbound), `platform` (discord/api) | Message throughput | P1 |
| `hermes_sessions_active` | Gauge | — | Current active sessions | P2 |
| `hermes_response_latency_seconds` | Histogram | `endpoint` | End-to-end response latency | P1 |
| `hermes_memory_recall_latency_seconds` | Histogram | — | Memory recall duration (dedicated) | P2 |
| `hermes_model_calls_total` | Counter | `model`, `provider` | Per-model call breakdown (dedicated) | P1 |
| `hermes_hook_execution_seconds` | Histogram | `hook_name` | Per-hook execution duration | P2 |
| `hermes_hook_executions_total` | Counter | `hook_name`, `status` | Per-hook execution count | P2 |
| `hermes_rate_limit_remaining` | Gauge | `provider` | Remaining API rate limit | P3 |
| `hermes_cost_monthly_usd` | Gauge | — | Monthly cumulative cost | P1 |

**Note**: `hermes_cost_monthly_usd` is referenced in the batch plan for `GuinevereHermesBudgetNearCap`, but the actual alert rule uses `hermes_llm_cost_usd_total` which is the unbounded counter. The monthly gauge would be a separate metric computed by a scheduler.

---

## 8. Metric Name Mismatches Between Sources

### 8.1 Alert Rule Uses Wrong Prefix

The alert rules `GuinevereLLMCostSpike` and `GuinevereLLMCostSpikeWarning` use:

```
rate(guinevere_llm_cost_usd_total[1h]) > 0.50
```

But the code in `llm_metrics.py:34-35` exports:

```python
LLM_COST_USD_TOTAL = Counter("hermes_llm_cost_usd_total", ...)
```

**Impact**: These two alert rules will **never fire** because the metric `guinevere_llm_cost_usd_total` does not exist.

**Fix**: Change alert expressions to use `hermes_llm_cost_usd_total`.

### 8.2 Consistency Decision

The codebase currently uses two naming conventions:
- `hermes_llm_*` — in `llm_metrics.py` (Phase 6 convention)
- `guinevere_*` — in `main.py` (FastAPI convention)

**Recommended**: Use `hermes_` prefix for all metrics exported by the Hermes gateway process (port 9191), and `guinevere_` for metrics exported by the FastAPI process (port 8000). This is consistent with the existing split and avoids cross-process metric name confusion.

---

## 9. Missing Prometheus Gauge Metrics (Runtime State)

The following **runtime state gauges** should be added to expose current system state (not just counters of events):

| Gauge Metric | Source | Labels | Update Strategy |
|---|---|---|---|
| `hermes_sessions_active` | `GuinevereSafetyPlugin._session_states` count | — | On `on_session_start` / session GC |
| `hermes_session_hard_stop_active` | `SessionSafetyState.hard_stop_active` | `session_id` | On each `pre_llm_call` |
| `hermes_session_safe_mode_active` | `SessionSafetyState.safe_mode_active` | `session_id` | On each `pre_llm_call` |
| `hermes_session_yandere_level` | `SessionSafetyState.yandere_level` | `session_id` | On each `pre_llm_call` |
| `hermes_session_distress_level` | `SessionSafetyState.distress_level` | `session_id` | On each `pre_llm_call` |
| `hermes_session_drift_score` | `SessionSafetyState.drift_score` | `session_id` | On each `post_llm_call` |
| `hermes_gateway_uptime_seconds` | Process start time | — | Set once at plugin init |

**Warning about high-cardinality**: `session_id` label on gauges can explode cardinality if sessions are not GC'd. Consider exposing only:
- Aggregate `sum()` of active sessions (no session_id label)
- Or set a max cardinality guard (e.g., only expose last 10 active sessions)

---

## 10. Integration Points — Where to Add Metrics

### 10.1 Primary: `src/hermes/safety_plugin.py` — Add Prometheus instrumentation

| Method | Line(s) | Metrics to Add |
|---|---|---|
| `__init__` | 245-284 | Initialize metric objects (Counter/Gauge/Histogram) |
| `pre_llm_call` | 447-682 | G01/G02/G04/G07 — increment `hermes_hard_stop_events_total`, `hermes_distress_events_total`, `hermes_recovery_events_total`, `hermes_yandere_violations_total`, update gauges |
| `post_llm_call` | 688-761 | G03 — update `hermes_session_drift_score`, increment `hermes_drift_events_total` |
| `pre_tool_call` | 767-848 | G09 — increment `hermes_auth_blocks_total` |
| `post_tool_call` | 854-868 | G10 — increment `hermes_consent_checks_total` |
| `transform_llm_output` | 874-988 | G05/G06/G08 — increment `hermes_forbidden_blocks_total`, `hermes_forbidden_rewrites_total`, `hermes_secret_redactions_total`, `hermes_yandere_semantic_rewrites_total` |

**Import pattern** (consistent with existing `llm_metrics.py`):
```python
from prometheus_client import Counter, Gauge, Histogram
# Create metrics at module level in safety_plugin.py
# (not inside the class — to avoid re-creation on plugin reload)
```

### 10.2 Secondary: `src/core/services/safety_metrics.py` (new file, optional)

If safety metrics become large, extract to a dedicated `safety_metrics.py` module (mirroring the `llm_metrics.py` pattern):

```python
"""Hermes Safety Plugin Prometheus Metrics — Phase 7c B8.

Exports safety-related metric families for the Guinevere safety plugin.
All metrics use the ``hermes_`` prefix and are registered on the global
prometheus_client registry so they are served alongside ``llm_metrics.py``
on port 9191.
"""
from prometheus_client import Counter, Gauge

HARD_STOP_EVENTS = Counter(
    "hermes_hard_stop_events_total",
    "HARD STOP trigger events",
    ["trigger"],  # exact, semantic, handler
)
...
```

**Recommendation**: Add directly in `safety_plugin.py` for B8 scope. Extract to dedicated file only if count exceeds 10 metric families.

### 10.3 Tertiary: `hermes-config/plugins/guinevere_safety/state_manager.py`

This external plugin tracks Redis state. Metrics could be added here if the Hermes plugin system supports Prometheus export, but **the current architecture exports all metrics from the Python process** (`llm_metrics.py` on port 9191). The external plugin runs **inside the Hermes Rust gateway process** — confirm whether that process exposes a `/metrics` endpoint before adding metrics there.

**Safer approach**: Add a periodic gauge setter in the Python-level `GuinevereSafetyPlugin` that reads Redis state and updates Prometheus gauges (e.g., every 30s via a background thread).

### 10.4 FastAPI `/metrics` endpoint (`src/core/main.py`)

Already handles `guinevere_*` FastAPI-level metrics. This is the right place for:
- `guinevere_safeword_events_total` (if triggered via Discord slash commands)
- `guinevere_safety_violations_total`
- `guinevere_safemode_state`
- `guinevere_subagent_file_missing_total`
- `guinevere_backup_last_success_timestamp`
- `guinevere_backup_last_restore_drill_timestamp`

**Integration pattern**: Add these `Counter`/`Gauge` instances near the existing `_REQUESTS_TOTAL` block at `main.py:155-169`.

### 10.5 Cost/Rate-Limit Monitoring in `llm_router.py`

`llm_router.py:238-240` already calls existing observers. These could be augmented with:
- `hermes_model_calls_total{model, provider}` — already partially covered by `hermes_llm_calls_total`, but a dedicated per-model counter with `provider` label would enable the dashboard's "Model Call Rate" panel to break down by model
- `hermes_rate_limit_remaining{provider}` — needs a new gauge updated when 9Router returns rate-limit headers

---

## 11. Registry Port Conflict Note

**Important**: Both `llm_metrics.py` (port 9191) and `main.py` (FastAPI `/metrics`) use the **global prometheus_client registry**. This means:

1. If both processes run in the same Python process (e.g., `main.py` starts the metrics server AND exports `/metrics`), metrics from both appear on both endpoints.
2. The `llm_metrics.py` metrics server runs on port 9191 as a background HTTP server.
3. The FastAPI `/metrics` endpoint on port 8000 serves `generate_latest()`.

If safety metrics are added to `safety_plugin.py` (which is imported into the Hermes gateway process), they will automatically appear on port 9191 alongside existing `hermes_llm_*` metrics — **no new port needed**.

If safety metrics are also needed on the FastAPI `/metrics` endpoint (port 8000), the metric objects need to be defined/imported in `main.py` as well, which could cause duplicate registration errors. **Recommendation**: Keep safety metrics on port 9191 only (Hermes gateway process).

---

## 12. Canonical Metric Name Table for B8 Implementation

### 12.1 Safety Plugin Counters (B8 — `safety_plugin.py`)

| # | Canonical Metric Name | Type | Labels | Incremented At | Priority |
|---|---|---|---|---|---|
| S1 | `hermes_hard_stop_events_total` | Counter | `trigger` (exact\|semantic\|handler) | safety_plugin.py:501,525,545 | **P0 — B8** |
| S2 | `hermes_distress_events_total` | Counter | `level` (D1\|D2\|D3\|D4) | safety_plugin.py:613,625 | **P0 — B8** |
| S3 | `hermes_recovery_events_total` | Counter | — | safety_plugin.py:567 | **P0 — B8** |
| S4 | `hermes_forbidden_blocks_total` | Counter | `pattern_id` (F-01..F-10) | safety_plugin.py:904 | **P0 — B8** |
| S5 | `hermes_forbidden_rewrites_total` | Counter | `pattern_id` (F-11..F-15) | safety_plugin.py:915 | **P0 — B8** |
| S6 | `hermes_secret_redactions_total` | Counter | — | safety_plugin.py:939 | **P0 — B8** |
| S7 | `hermes_yandere_violations_total` | Counter | — | safety_plugin.py:655 | **P0 — B8** |
| S8 | `hermes_yandere_semantic_rewrites_total` | Counter | — | safety_plugin.py:963 | **P0 — B8** |
| S9 | `hermes_auth_blocks_total` | Counter | `tool`, `operation`, `auth_level` | safety_plugin.py:813 | **P0 — B8** |
| S10 | `hermes_consent_checks_total` | Counter | `tool` | safety_plugin.py:787 | **P1 — B8** |
| S11 | `hermes_drift_events_total` | Counter | `action` (alert\|rollback) | safety_plugin.py:743,750 | **P1 — B8** |

### 12.2 Safety Plugin Gauges (B8 — `safety_plugin.py`)

| # | Canonical Metric Name | Type | Labels | Updated At | Priority |
|---|---|---|---|---|---|
| G1 | `hermes_sessions_active` | Gauge | — | on_session_start, periodic GC | **P1 — B8** |
| G2 | `hermes_session_yandere_level` | Gauge | `session_id` | pre_llm_call (G07) | **P1 — B8** |
| G3 | `hermes_session_distress_level` | Gauge | `session_id` | pre_llm_call (G02) | **P1 — B8** |
| G4 | `hermes_session_drift_score` | Gauge | `session_id` | post_llm_call (G03) | **P1 — B8** |

### 12.3 Hermes-Native Runtime Metrics (B3-B6 — `llm_metrics.py` or new file)

| # | Canonical Metric Name | Type | Labels | Priority |
|---|---|---|---|---|
| R1 | `hermes_gateway_uptime_seconds` | Gauge | — | **P1 — B3** |
| R2 | `hermes_messages_total` | Counter | `direction`, `platform` | **P1 — B3** |
| R3 | `hermes_response_latency_seconds` | Histogram | `endpoint` | **P1 — B3** |
| R4 | `hermes_model_calls_total` | Counter | `model`, `provider` | **P1 — B4** |
| R5 | `hermes_cost_monthly_usd` | Gauge | — | **P1 — B4** |
| R6 | `hermes_memory_recall_latency_seconds` | Histogram | — | **P2 — B5** |
| R7 | `hermes_hook_execution_seconds` | Histogram | `hook_name` | **P2 — B6** |
| R8 | `hermes_hook_executions_total` | Counter | `hook_name`, `status` | **P2 — B6** |
| R9 | `hermes_rate_limit_remaining` | Gauge | `provider` | **P3 — B6** |

### 12.4 FastAPI/Alert Rule Metrics (Port 8000 — `main.py`)

| # | Canonical Metric Name | Type | Labels | Priority |
|---|---|---|---|---|
| F1 | `guinevere_safeword_events_total` | Counter | `type` | **P1** (fix persona-safety dashboard + alert rule) |
| F2 | `guinevere_safety_violations_total` | Counter | `severity` | **P1** (fix persona-safety dashboard) |
| F3 | `guinevere_safemode_state` | Gauge | — | **P1** (fix persona-safety dashboard) |
| F4 | `guinevere_subagent_file_missing_total` | Counter | — | **P1** (fix alert rule) |
| F5 | `guinevere_backup_last_success_timestamp` | Gauge | — | **P1** (fix backup alert rules) |
| F6 | `guinevere_backup_last_restore_drill_timestamp` | Gauge | — | **P2** (fix alert rule) |

### 12.5 Metrics That Should Be Redirected (Name Fix)

| Current (wrong) in Alerts | Correct Name | Fix Target |
|---|---|---|
| `guinevere_llm_cost_usd_total` | `hermes_llm_cost_usd_total` | Alert rules `GuinevereLLMCostSpike` and `GuinevereLLMCostSpikeWarning` in `guinevere-alerts.yml` |
| `guinevere_public_ingress_detected` | (create in `main.py`) | Alert rule `GuineverePublicIngressDetected` |
| `guinevere_log_redaction_failures_total` | (create in `main.py`) | Alert rule `GuinevereLogRedactionFailure` |
| `guinevere_secret_access_total` | (create in `main.py`) | Alert rule `GuinevereSecretAccessOutsideStartup` |

---

## 13. Implementation Order and Dependencies

```
B8: Add safety plugin metrics (S1-S11, G1-G4) — safety_plugin.py
  ├── P0: S1 (hard_stop) — unblocks dashboard panel 7 + safety dashboard panel 4
  ├── P0: S4+S5 (forbidden) — needed for safety dashboard panel 1 (guinevere_safety_violations_total alias)
  ├── P0: S9 (auth_blocks) — needed for safety dashboard
  ├── P0: S6 (secrets) — needed for operational visibility
  └── P1: S2+S3+S7+S8+S10+S11+G1-G4 — remaining safety metrics

B3: Add gateway runtime metrics (R1-R3) — llm_metrics.py or hermes runtime module
  └── hermes_gateway_uptime_seconds
  └── hermes_messages_total
  └── hermes_response_latency_seconds

B4: Add model/cost metrics (R4-R5)
  └── hermes_model_calls_total{model,provider}
  └── hermes_cost_monthly_usd

B5: Add memory recall latency (R6)
  └── hermes_memory_recall_latency_seconds

B6: Add hook + rate limit metrics (R7-R9)
  └── hermes_hook_execution_seconds
  └── hermes_hook_executions_total
  └── hermes_rate_limit_remaining

FastAPI: Add missing guinevere_* metrics (F1-F6) — main.py
  └── unblocks 6 alert rules + persona-safety dashboard
  └── fix alert rule name mismatch (guinevere_llm_cost_usd_total → hermes_llm_cost_usd_total)

B7: Hermes dashboard panels 6-9 become live (depend on S1, S4, R6)
```

### Key Dependency Chain

```
safety_plugin.py metrics (S1, S4)
  └─► hermes_safety_blocks_total available
       └─► Dashboard panel 6 goes live
       └─► GuinevereHermesSafetyBlocksSpike alert rule fires

safety_plugin.py metrics (S1)
  └─► hermes_hard_stop_events_total available
       └─► Dashboard panel 7 goes live

llm_metrics.py (R4)
  └─► hermes_model_calls_total{model,provider} available
       └─► Dashboard panel 9 shows per-model breakdown
       └─► GuinevereHermesModelCallsAnomaly alert rule uses accurate per-model data

main.py (F1-F6)
  └─► guinevere_safeword_events_total available
       └─► GuinevereSafeWordBypassAttempt alert rule fires
       └─► Safety dashboard panels 3+4 go live
  └─► guinevere_backup_last_success_timestamp available
       └─► GuinevereBackupStale and GuinevereBackupMissing alert rules fire
```

---

## Appendix A: File Reference Table

| File | Path | Metrics | Lines to Modify |
|---|---|---|---|
| LLM Metrics | `src/core/services/llm_metrics.py` | 4 existing, ~9 new (R1-R9) | Add new metric families + observers |
| LLM Router | `src/core/services/llm_router.py` | Calls existing 4 observers | Add R4 (model_calls_total) call |
| Safety Plugin | `src/hermes/safety_plugin.py` | 0 existing, ~15 new (S1-S11, G1-G4) | Add imports, metric objects in `__init__`, inc() calls in each gate |
| FastAPI Main | `src/core/main.py` | 3 existing, ~6 new (F1-F6) | Add metric objects near line 155 + inc() hooks |
| Hermes Config | `hermes-config/config.yaml` | Config only | No changes — `observability.prometheus.enabled: true` already set |
| External Plugin | `hermes-config/plugins/guinevere_safety/state_manager.py` | 0 | Add periodic gauge sync (or skip — low priority) |
| Prometheus Config | `monitoring/prometheus/prometheus.yml` | Scrape target | Already fixed (`host.docker.internal:9191`, job_name: `hermes`) |
| Alert Rules | `monitoring/prometheus/rules/guinevere-alerts.yml` | 19 rules, 6 missing metrics | Fix `guinevere_llm_cost_usd_total` → `hermes_llm_cost_usd_total`; add remaining after metrics exported |
| Hermes Dashboard | `monitoring/grafana/dashboards/guinevere-hermes.json` | 9 panels, 4 pending metrics | No changes needed — panel PromQL expressions already correct, just need metrics |
| Persona Safety Dashboard | `monitoring/grafana/dashboards/guinevere-persona-safety.json` | 4 panels, 4 missing metrics | Unblocks after F1-F3 created |
| Test | `tests/hermes/test_llm_metrics.py` | 4 metric tests | Add tests for new safety metrics |

---

## Appendix B: Verification Commands

After implementing B8 metrics, verify with:

```bash
# 1. Check safety metrics appear on port 9191
curl -s http://localhost:9191/metrics | grep -E "^hermes_(hard_stop|distress|recovery|forbidden|secret|yandere|auth|consent|drift|sessions)"

# 2. Check all 19 expected lines present for B8 scope
curl -s http://localhost:9191/metrics | grep -cE "^hermes_(hard_stop_events|distress_events|recovery_events|forbidden_blocks|forbidden_rewrites|secret_redactions|yandere_violations|yandere_semantic|auth_blocks|consent_checks|drift_events|sessions_active|session_yandere|session_distress|session_drift)"

# 3. Verify alert rule expressions resolve
# (Prometheus UI: /api/v1/rules)

# 4. Verify no duplicate metric registration warning
curl -s http://localhost:9191/metrics | grep -i "duplicate\|warning\|error"

# 5. Run unit tests
python -m pytest tests/hermes/test_llm_metrics.py -v
```

---

*End of report — 24 missing metrics cataloged across 12 source files, with canonical names, types, labels, code locations, and integration points.*

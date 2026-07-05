# P19-010 Observability Fix: Grafana Dashboard for Multi-Project Metrics

**Date:** 2026-06-26
**Verdict:** CREATED

---

## Problem

Observability audit found that `guinevere-p19-projects.json` Grafana dashboard was missing.
P19-010 requires a dashboard that surfaces project-scoped Prometheus metrics from both
`src/loops/metrics.py` and `src/life_kernel/metrics.py`, filterable by `project_id`.

---

## Deliverable

**File:** `monitoring/grafana/dashboards/guinevere-p19-projects.json`
**UID:** `guinevere-p19-projects`
**Schema:** matches existing dashboards (schemaVersion 39, datasource `prometheus`, timezone `Asia/Jakarta`)

---

## Template Variable

`$project_id` — query variable populated from `label_values(guinevere_loop_events_total, project_id)`,
with "All" option (`.*`) enabled, auto-refreshing on dashboard load.

---

## Panels (6 panels, 3 required domains)

### Panel 1 — Heartbeat Health (stat, life_kernel domain)
- **Expr:** `guinevere_lk_heartbeat_healthy{project_id=~"$project_id"}`
- **Source metric:** `src/life_kernel/metrics.py` `LK_HEARTBEAT_HEALTHY`
- Shows green "Healthy" (1) or red "Unhealthy" (0) per project.

### Panel 2 — Loop Cycles Rate (timeseries, loops domain)
- **Expr:** `sum by (project_id) (rate(guinevere_loop_cycles_total{project_id=~"$project_id"}[$__rate_interval]))`
- **Source metric:** `src/loops/metrics.py` `LOOP_CYCLES_TOTAL`
- Completed loop cycles per second, grouped by project.

### Panel 3 — Loop Events by Type (timeseries, loops domain)
- **Expr:** `sum by (event_type, project_id) (rate(guinevere_loop_events_total{project_id=~"$project_id"}[$__rate_interval]))`
- **Source metric:** `src/loops/metrics.py` `LOOP_EVENTS_TOTAL`
- Stacked bar chart of audit events by type, per project.

### Panel 4 — Life Kernel Records by Source (timeseries, life_kernel domain)
- **Expr:** `sum by (source, project_id) (rate(guinevere_lk_records_total{project_id=~"$project_id"}[$__rate_interval]))`
- **Source metric:** `src/life_kernel/metrics.py` `LK_RECORDS_TOTAL`
- Durability record throughput by source, per project.

### Panel 5 — Loop Phase Duration p95/p50 (timeseries, loops domain)
- **Expr (p95):** `histogram_quantile(0.95, sum by (le, phase, project_id) (rate(guinevere_loop_phase_duration_seconds_bucket{project_id=~"$project_id"}[$__rate_interval])))`
- **Expr (p50):** same with 0.50 quantile
- **Source metric:** `src/loops/metrics.py` `LOOP_PHASE_DURATION_SECONDS`
- Latency percentiles per phase, per project.

### Panel 6 — Cognition Cycles Rate (timeseries, life_kernel domain)
- **Expr:** `sum by (project_id) (rate(guinevere_lk_cognition_cycles_total{project_id=~"$project_id"}[$__rate_interval]))`
- **Source metric:** `src/life_kernel/metrics.py` `LK_COGNITION_CYCLES_TOTAL`
- Cognition cycle throughput per project.

---

## Coverage Summary

| Domain        | Source file                       | Metrics covered                                                     |
|---------------|-----------------------------------|---------------------------------------------------------------------|
| loops         | `src/loops/metrics.py`            | `guinevere_loop_events_total`, `guinevere_loop_cycles_total`, `guinevere_loop_phase_duration_seconds` |
| life_kernel   | `src/life_kernel/metrics.py`      | `guinevere_lk_records_total`, `guinevere_lk_heartbeat_healthy`, `guinevere_lk_cognition_cycles_total` |
| overview      | both                              | Heartbeat health stat + cycle/cognition rate as summary panels      |

All 6 metrics are represented. All panels accept `$project_id` regex filter.
Dashboard structure (schemaVersion, datasource uid, timezone, time range, annotations, gridPos layout)
matches the existing `guinevere-agent-loop.json` reference dashboard.

# Phase 7 Monitoring Gap Analysis: Hermes Migration (ADR-035)

**Date:** 2026-06-05  
**Author:** Guinevere (Autonomous Engineering Agent)  
**Scope:** Monitoring stack comparison between current state (P8) and Phase 7 Hermes hardening requirements.  
**Reference:** `docs/setup-evidence/hermes-migration/phase-7-hardening.md`, `adr/ADR-035-hermes-migration.md`

---

## Executive Summary

The current monitoring stack (Prometheus, Grafana, Loki, Alertmanager) is well-established for the legacy `discord.py` + FastAPI architecture. However, the Phase 7 Hermes migration introduces a new primary gateway process (`hermes-gateway`) exposing metrics on port `9191` and emitting structured JSON logs. 

**Critical Gaps Identified:**
1. **Missing Prometheus scrape target** for Hermes metrics (port 9191).
2. **Missing Hermes-specific alert rules** (gateway down, safety blocks, latency, model calls).
3. **Missing Grafana dashboard** for Hermes gateway health, hook latency, and compression metrics.
4. **Promtail regex mismatch**: Current systemd journal scrape only matches `guinevere-*.service`, missing `hermes-gateway.service`.

All gaps are low-to-medium effort to resolve and can be implemented as atomic configuration updates without disrupting existing monitoring.

---

## 1. Prometheus Scrape Configuration

**File:** `monitoring/prometheus/prometheus.yml`

| Current State | Required State | Gap | Priority | Effort |
|---|---|---|---|---|
| 7 scrape jobs: `prometheus`, `node`, `postgresql`, `redis`, `fastapi`, `loki`, `alertmanager`. | 8 scrape jobs, including `hermes` targeting `host.docker.internal:9191` with 15s interval. | Missing `hermes` scrape job configuration. | **High** | Low |

**Action Required:**  
Add the following block to `scrape_configs` in `prometheus.yml`:
```yaml
  - job_name: "hermes"
    metrics_path: "/metrics"
    scrape_interval: 15s
    static_configs:
      - targets: ["host.docker.internal:9191"]
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: "hermes-gateway"
```

---

## 2. Prometheus Alert Rules

**Files:** `monitoring/prometheus/rules/guinevere-alerts.yml`, `guinevere-backup-alerts.yml`

| Current State | Required State | Gap | Priority | Effort |
|---|---|---|---|---|
| Alerts cover legacy FastAPI, safety, security, operations, and backup (SEV0–SEV4). No Hermes-specific metrics monitored. | Hermes-specific alerts: `hermes_gateway_down` (SEV0), `hermes_response_latency_p95` (SEV2), `hermes_safety_blocks_total` (SEV0), `hermes_memory_recall_latency` (SEV2), `hermes_model_calls_total` (SEV3). | Missing `guinevere-hermes-alerts.yml` file with 5+ new alert rules. | **High** | Low |

**Action Required:**  
Create `monitoring/prometheus/rules/guinevere-hermes-alerts.yml` with the following rules:
```yaml
groups:
  - name: guinevere-hermes
    rules:
      - alert: GuinevereHermesGatewayDown
        expr: up{job="hermes"} == 0
        for: 2m
        labels:
          severity: "critical"
          sev_level: "SEV0"
        annotations:
          summary: "Hermes gateway is down"
          runbook: "runbooks/hermes-migration-runbook.md"

      - alert: GuinevereHermesSafetyBlocks
        expr: increase(guinevere_hermes_safety_blocks_total[5m]) > 0
        for: 0m
        labels:
          severity: "critical"
          sev_level: "SEV0"
        annotations:
          summary: "Hermes safety hook blocked a request"

      - alert: GuinevereHermesResponseLatencyP95
        expr: histogram_quantile(0.95, rate(guinevere_hermes_response_latency_seconds_bucket[5m])) > 2.0
        for: 5m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "Hermes response latency p95 > 2.0s"

      - alert: GuinevereHermesMemoryRecallLatency
        expr: histogram_quantile(0.95, rate(guinevere_hermes_memory_recall_latency_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "Hermes memory recall latency p95 > 1.0s"

      - alert: GuinevereHermesModelCallsSpike
        expr: rate(guinevere_hermes_model_calls_total[15m]) > 10
        for: 5m
        labels:
          severity: "info"
          sev_level: "SEV3"
        annotations:
          summary: "Hermes model call rate spike detected"
```

---

## 3. Grafana Dashboards

**Directory:** `monitoring/grafana/dashboards/`

| Current State | Required State | Gap | Priority | Effort |
|---|---|---|---|---|
| 6 dashboards: `persona-safety`, `llm-cost-latency`, `infrastructure`, `finops`, `database-memory`, `agent-loop`. | Dedicated Hermes dashboard tracking gateway status, hook latency, compression events, session search usage, and safety blocks. | Missing `guinevere-hermes.json` dashboard definition. | **Medium** | Medium |

**Action Required:**  
Create `monitoring/grafana/dashboards/guinevere-hermes.json` with panels for:
- Gateway uptime (`up{job="hermes"}`)
- Hook execution latency (by hook type: `pre_prompt`, `post_prompt`, `pre_tool_call`, etc.)
- Safety blocks counter (`guinevere_hermes_safety_blocks_total`)
- Context compression events rate
- Model call cost tracking (`guinevere_hermes_cost_monthly_usd`)

---

## 4. Loki / Promtail Log Monitoring

**Files:** `monitoring/loki/loki-config.yml`, `monitoring/promtail/promtail-config.yml`

| Current State | Required State | Gap | Priority | Effort |
|---|---|---|---|---|
| Promtail scrapes systemd journal with regex `guinevere-(.+)\\.service` to set `service` label. Hermes config outputs JSON logs to both stdout and Loki. | Promtail must capture `hermes-gateway.service` logs and label them `service="hermes"` for unified Loki querying. | Promtail regex `guinevere-(.+)\\.service` will **not** match `hermes-gateway.service`. Logs will be ingested but lack the `service="hermes"` label, breaking dashboard/log queries. | **High** | Low |

**Action Required:**  
Update `monitoring/promtail/promtail-config.yml` systemd journal relabel config:
```yaml
    relabel_configs:
      - source_labels: ["__journal__systemd_unit"]
        target_label: "unit"
      - source_labels: ["__journal__hostname"]
        target_label: "hostname"
      - source_labels: ["__journal__systemd_unit"]
        regex: "(guinevere|hermes)-(.+)\\.service"
        target_label: "service"
        replacement: "${1}"
```
*Note: Hermes `config.yaml` already has `observability.logging.format: json` and `output: both`, which is correct.*

---

## 5. Exporter Status

**Files:** `monitoring/node-exporter/`, `monitoring/postgres-exporter/`, `monitoring/redis-exporter/`

| Current State | Required State | Gap | Priority | Effort |
|---|---|---|---|---|
| Node exporter (with textfile collector for `backup.prom`), PostgreSQL exporter (minimal privilege role), Redis exporter (ACL setup script). All configured and operational. | No new exporters required. Hermes exposes its own metrics natively on port 9191. Backup metrics continue to use the existing textfile collector. | None. Existing exporters are sufficient. Ensure `backup-metric-collector.sh` is updated to trigger on `hermes backup` completion if a separate sentinel is used. | **Low** | None |

**Action Required:**  
Verify that the Phase 7 `hermes backup --full` cron job updates the existing `/var/log/guinevere/last-backup-success` sentinel file, or modify `backup-metric-collector.sh` to also check for a Hermes-specific sentinel.

---

## 6. Alertmanager Routing

**File:** `monitoring/alertmanager/alertmanager.yml`

| Current State | Required State | Gap | Priority | Effort |
|---|---|---|---|---|
| Routes alerts by `sev_level` (SEV0–SEV4) to Discord (primary) and Gotify (SEV0/SEV1 backup). Neutral incident-command tone enforced. | Hermes alerts will use the same `sev_level` label schema. Routing will work automatically without structural changes. | No structural gap. Ensure new Hermes alert rules include `runbook: "runbooks/hermes-migration-runbook.md"` in annotations. | **Low** | Low |

**Action Required:**  
No changes to `alertmanager.yml` required. Rely on existing `sev_level`-based routing.

---

## 7. Backup Monitoring

**Files:** `monitoring/scripts/backup-metric-collector.sh`, `monitoring/prometheus/rules/guinevere-backup-alerts.yml`

| Current State | Required State | Gap | Priority | Effort |
|---|---|---|---|---|
| `backup-metric-collector.sh` reads `/var/log/guinevere/last-backup-success` and writes `guinevere_backup_last_success_timestamp`. Alert triggers if >26h old (SEV2). | Hermes weekly backup (`hermes backup --full`) must update this same sentinel to keep the existing alert functional, or a new Hermes-specific backup alert must be added. | Potential gap if `hermes backup` does not touch the legacy sentinel file. | **Medium** | Low |

**Action Required:**  
Ensure the `hermes cron add "weekly_backup"` command or its wrapper script also executes:
```bash
touch /var/log/guinevere/last-backup-success
```
Alternatively, add a Hermes-specific backup alert to `guinevere-hermes-alerts.yml`:
```yaml
      - alert: GuinevereHermesBackupStale
        expr: time() - guinevere_hermes_last_backup_timestamp > 93600
        for: 5m
        labels:
          severity: "warning"
          sev_level: "SEV2"
        annotations:
          summary: "Hermes backup is stale (>26 hours)"
```

---

## Summary of Required Actions

| # | Action | File(s) to Modify/Create | Priority |
|---|---|---|---|
| 1 | Add Hermes scrape job to Prometheus | `monitoring/prometheus/prometheus.yml` | High |
| 2 | Create Hermes alert rules file | `monitoring/prometheus/rules/guinevere-hermes-alerts.yml` | High |
| 3 | Fix Promtail systemd regex to include `hermes` | `monitoring/promtail/promtail-config.yml` | High |
| 4 | Create Hermes Grafana dashboard JSON | `monitoring/grafana/dashboards/guinevere-hermes.json` | Medium |
| 5 | Ensure Hermes backup updates legacy sentinel or add new alert | `monitoring/scripts/backup-metric-collector.sh` or new alert rule | Medium |
| 6 | Verify Alertmanager routing (no changes needed, just annotation check) | `monitoring/prometheus/rules/guinevere-hermes-alerts.yml` | Low |

---

## Verification Checklist (Post-Implementation)

- [ ] `curl -sf http://localhost:9191/metrics | head -20` returns Hermes metrics.
- [ ] Prometheus Targets page shows `hermes` job as `UP`.
- [ ] Prometheus Rules page shows `guinevere-hermes` group loaded without errors.
- [ ] Loki query `{service="hermes"}` returns recent log entries.
- [ ] Grafana loads the new Hermes dashboard without datasource errors.
- [ ] `hermes backup --dry-run` followed by sentinel check confirms backup monitoring integration.

---
*Generated by Guinevere Autonomous Engineering Agent. Compliant with AGENTS.md §2.2 Research Wave and §2.9 File-Based Output Discipline.*

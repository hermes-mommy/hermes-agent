# Observability & Alerting — External References Report

**Document Type:** Research evidence report for Observability & Alerting Specification  
**Version:** 1.0  
**Status:** Accepted (Samm Review Record)  
**Date:** 2026-05-30  
**Owner:** Samm — single-user owner and final authority  
**Executor:** Guinevere de Baroque — autonomous system steward  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL

## Related Documents

| Document | Relationship |
|---|---|
| `research-reports/2026-05-30-observability-source-map.md` | Authority chain, constraints, gaps for this report. |
| `research-reports/2026-05-30-observability-surface-map.md` | Concrete surface catalog for this report. |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Defines drill matrix incident lifecycle and evidence duties. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines classification constraints that apply to external patterns. |
| `adr/ADR-017-monitoring-stack-selection.md` | Normative parent for Prometheus + Grafana + Loki selection. |

---

## 1. Purpose

This report catalogs authoritative external references and implementable patterns for every technology and practice area required by Project Guinevere's Observability & Alerting Specification. Each reference includes:

- The authoritative URL or documentation source.
- Key principles and patterns applicable to Guinevere.
- How the pattern must be adapted to Guinevere's single-user, high-privacy, persona-aware context.
- Implementation guidance specifically for `Guinevere_Observability_AlertingSpec_v1.0.md`.

Do not copy entire external documents into this report. Instead, capture the specific patterns, constraints, and decisions that the Guinevere spec must encode.

---

## 2. Prometheus — Metric Naming, Labels, and Cardinality

### 2.1 Authoritative References

| Reference | URL |
|---|---|
| Prometheus Metric Naming | `https://prometheus.io/docs/practices/naming/` |
| Prometheus Metric and Label Naming Best Practices | `https://prometheus.io/docs/practices/naming/` |
| Prometheus Label and Cardinality Management | `https://prometheus.io/docs/practices/instrumentation/` |
| Prometheus Histogram and Summary | `https://prometheus.io/docs/concepts/metric_types/` |

### 2.2 Key Patterns for Guinevere

**Metric Naming Convention:**

- Prefix all custom Guinevere metrics with `guinevere_` (established in TechnicalArchitecture).
- Use snake_case: `guinevere_mood_state`, `guinevere_llm_latency_seconds`.
- Suffix units where applicable: `_total` (counter), `_seconds` (duration), `_bytes` (size), `_count`/_bucket (histogram).
- Name format: `guinevere_<component>_<measure>[_unit]`.

**Label Rules (directly from user constraint):**

- No high-cardinality labels in Prometheus.
- Bounded low-cardinality labels only: `service`, `phase`, `model`, `status`, `violation_type`, `source`, `pattern_id`.
- Forbidden: raw user IDs, unbounded job names, full request paths, raw input content.
- Label values must be bounded to a known set (< 100 distinct values per label).

**Cardinality Budget:**

- Each custom metric must define its maximum series cardinality.
- Example: `guinevere_llm_latency_seconds{model, use_case}` — model has 2 values (gpt-5.5, deepseek-v4-flash), use_case has ~5 values — total 10 series. Acceptable.
- Example: `guinevere_surveillance_events_total{source, type}` — source has 2 (android, windows), type has ~8 — total 16 series. Acceptable.
- All labels must be bounded and documented in the spec.

**Counter vs Gauge vs Histogram Rules:**

- Counters: monotonic, suffixed `_total`. For things that only increase (events, errors, API calls).
- Gauges: can go up and down. For state (mood, yandere intensity, active loops, memory usage).
- Histograms: for latency and size distributions. Suffixed `_seconds` or `_bytes` with `_bucket`, `_sum`, `_count`.

### 2.3 Guinea-Specific Adaptation

- All metric labels must be privacy-safe: no labels that reveal personal data, raw surveillance metadata, or safe-word state by name.
- Use generic label values: `violation_type="notification"` instead of raw notification content.
- Use hashed/summarized identifiers where correlation is needed but raw values are sensitive.

---

## 3. Alertmanager — Routing, Grouping, Dedup, and Silence

### 3.1 Authoritative References

| Reference | URL |
|---|---|
| Alertmanager Configuration | `https://prometheus.io/docs/alerting/latest/alertmanager/` |
| Alertmanager Routing | `https://prometheus.io/docs/alerting/latest/configuration/#route` |
| Alertmanager Grouping | `https://prometheus.io/docs/alerting/latest/alertmanager/#grouping` |
| Alertmanager Silences | `https://prometheus.io/docs/alerting/latest/alertmanager/#silences` |
| Alertmanager Inhibition | `https://prometheus.io/docs/alerting/latest/alertmanager/#inhibition` |

### 3.2 Key Patterns for Guinevere

**Routing Tree:**

```
default route (SEV3 digests)
  ├── sev0_sev1_route
  │   ├── receiver: discord_gotify_urgent
  │   └── repeat_interval: 5m (SEV0), 15m (SEV1)
  ├── sev2_route
  │   ├── receiver: discord_only
  │   └── repeat_interval: 1h
  ├── sev3_route
  │   ├── receiver: discord_digest
  │   └── repeat_interval: 24h
  └── sev4_route
      ├── receiver: governance_summary
      └── repeat_interval: monthly
```

**Grouping Configuration:**

```yaml
group_by: ['severity', 'incident_type']
group_wait: 30s
group_interval: 5m
```

- SEV0/SEV1 must not group across unrelated incidents. Set `group_by: ['severity', 'alertname']`.
- SEV3/SEV4 can group by: `group_by: ['severity']`.

**Inhibition Rules:**

- SEV0 inhibits SEV1-SEV4 for the same surface (avoid alert storm when critical incident is already declared).
- SEV1 inhibits SEV3-SEV4 for the same surface.

**Silence Management:**

- Maintenance windows: silence by `surface` label.
- Safe-mode: when `guinevere_safe_mode_state > 0`, silence persona/yandere-related alerts automatically.
- All silences must have owner, reason, and expiry.

### 3.3 Guinea-Specific Adaptation

- Alert routing must use severity labels that map to IncidentResponse severity matrix.
- `receiver` config must include Discord webhook, Gotify endpoint.
- Send unresolved alerts to a `governance_review` receiver for monthly review.
- Alert content must pass secret/intimate/surveillance scanner before delivery.

---

## 4. Grafana — Dashboard-as-Code and Provisioning

### 4.1 Authoritative References

| Reference | URL |
|---|---|
| Grafana Provisioning | `https://grafana.com/docs/grafana/latest/administration/provisioning/` |
| Grafana Dashboard JSON Model | `https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/manage-version-control/` |
| Grafana Dashboard-as-Code | `https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/manage-version-control/#export-and-import-dashboards` |
| Grafana Alerting | `https://grafana.com/docs/grafana/latest/alerting/` |
| Grafana Dashboard Provisioning | `https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards` |

### 4.2 Key Patterns for Guinevere

**Provisioning Directory Structure:**

```
/home/guinevere/monitoring/grafana/
├── dashboards/
│   ├── incident-response.json
│   ├── system-health.json
│   ├── llm-performance.json
│   ├── safety-monitoring.json
│   ├── surveillance-ingestion.json
│   ├── backup-status.json
│   ├── persona-overview.json
│   └── loop-observability.json
├── datasources/
│   ├── prometheus.yaml
│   └── loki.yaml
├── alerting/
│   └── rules.yaml
└── provisioning.yaml
```

**Dashboard-as-Code Mandatory Rules (user constraint):**

- All dashboards must be version-controlled in the `guinevere-docs` repository.
- All dashboards must be defined as JSON files, not created via UI alone.
- Each JSON file must have a comment header with owner, purpose, data sources, and label selectors.
- Provisioning must be automated via Grafana's filesystem provisioner or API.

**Panel Conventions:**

- Every panel must have a description explaining what it measures and the data source.
- Units must be consistent (bytes, seconds, percent).
- Time ranges: default 6h, quick ranges 1h, 24h, 7d, 30d.

**Dashboard Variables:**

- `$service` — select from systemd services.
- `$severity` — SEV0 through SEV4.
- `$surface` — surfaces from surface map.
- Variable values must be bounded and low-cardinality.

### 4.3 Guinea-Specific Adaptation

- Folder structure: `/dashboards/Incident Response/`, `/dashboards/System/`, `/dashboards/Safety/`, etc.
- Grafana folders must align with surface map categories.
- Access control via Grafana `auth.proxy` with Tailscale identity.
- `observability-reader` role must map to Grafana Viewer, not Editor or Admin.

---

## 5. Loki — Labels and Structured Metadata

### 5.1 Authoritative References

| Reference | URL |
|---|---|
| Loki Overview | `https://grafana.com/docs/loki/latest/` |
| Loki Labels Best Practices | `https://grafana.com/docs/loki/latest/best-practices/` |
| Loki Structured Metadata | `https://grafana.com/docs/loki/latest/get-started/labels/structured-metadata/` |
| Loki Configuration | `https://grafana.com/docs/loki/latest/configure/` |
| Promtail Configuration | `https://grafana.com/docs/loki/latest/clients/promtail/configuration/` |

### 5.2 Key Patterns for Guinevere

**Label Rules:**

- Low-cardinality labels for Loki: `service`, `level`, `trace_id`, `component`.
- High-cardinality items (request paths, user names) must be structured metadata, not labels.

**Structured Metadata:**

- Fields: `trace_id`, `request_id`, `task_id`, `loop_id`, `incident_id`.
- Structured metadata is indexed but does not cause label cardinality issues.

**Log Format:**

- All application logs must be JSON structured.
- Required fields: `timestamp`, `level`, `service`, `correlation_id`, `message`, `metadata`.
- Optional fields: `trace_id`, `request_id`, `task_id`, `loop_id`, `incident_id`, `duration_ms`.

**Retention Configuration:**

- Per-stream retention: 30 days for debug/info streams, 90 days for warning/error, 365 days for audit.
- Compaction enabled for all streams.

**Promtail Pipeline Stages:**

```yaml
- json:
    expressions:
      level: level
      service: service
      trace_id: trace_id
- labels:
    level:
    service:
    trace_id:
- timestamp:
    source: timestamp
    format: RFC3339Nano
```

### 5.3 Guinea-Specific Adaptation

- Service label values: `guinevere-core`, `guinevere-surveillance`, `guinevere-scheduler`, `guinevere-loops`, `guinevere-windows-sync`.
- Level values: `debug`, `info`, `warning`, `error`, `critical`.
- No sensitive payload in Loki labels. Structured metadata must be scanned for Critical content.

---

## 6. OpenTelemetry — Trace Propagation

### 6.1 Authoritative References

| Reference | URL |
|---|---|
| OpenTelemetry Overview | `https://opentelemetry.io/docs/concepts/` |
| OpenTelemetry Trace Context | `https://www.w3.org/TR/trace-context/` |
| OpenTelemetry Python SDK | `https://opentelemetry.io/docs/languages/python/` |
| OpenTelemetry Propagators | `https://opentelemetry.io/docs/concepts/context-propagation/` |

### 6.2 Key Patterns for Guinevere

**Trace ID Propagation (user constraint):**
Every distributed trace must propagate these IDs:

- `trace_id` — W3C trace context standard (16-byte hex).
- `request_id` — unique per API request (UUID v4).
- `task_id` — unique per SDLC task.
- `loop_id` — unique per loop instance.
- `subagent_task_id` — unique per sub-agent task.
- `incident_id` — unique per incident declaration.
- `evidence_id` — unique per evidence artifact.

**Propagation Mechanism:**

- W3C Trace Context `traceparent` header for HTTP requests between services.
- Custom `X-Request-Id`, `X-Task-Id`, `X-Loop-Id`, `X-Incident-Id` headers for application-specific correlation.
- All structured logs must include `trace_id` and available application IDs.

**Context Propagation Boundaries:**

- FastAPI endpoints: extract trace context from incoming request, propagate to downstream calls.
- Sub-agent task: parent loop generates `subagent_task_id`, injected into sub-agent context.
- Loop phase: phase transitions carry `loop_id` and current `task_id`.
- Surveillance ingestion: `device_id` + `trace_id` for end-to-end ingestion trace.
- Incident: `incident_id` for all alert, evidence, and postmortem artifacts.

**Sampling Strategy:**

- Always-on for errors and SEV0-SEV2 traces.
- Probabilistic (1%) for high-volume endpoints (surveillance ingestion).
- Rate-limited for loop phase transitions.

### 6.3 Guinea-Specific Adaptation

- OpenTelemetry SDK may add overhead for high-frequency surveillance ingestion; use probabilistic sampling.
- Sentry supports OpenTelemetry trace correlation via `traces_sample_rate`.
- Prometheus + Loki + Sentry traces must share the same `trace_id` for cross-system correlation.
- Do not propagate trace IDs that contain sensitive data (they must be opaque identifiers).

---

## 7. Sentry — Python/FastAPI PII Scrubbing

### 7.1 Authoritative References

| Reference | URL |
|---|---|
| Sentry Python SDK Configuration | `https://docs.sentry.io/platforms/python/configuration/` |
| Sentry Data Filtering (PII) | `https://docs.sentry.io/platforms/python/guides/fastapi/data-management/filtering/` |
| Sentry `before_send` | `https://docs.sentry.io/platforms/python/configuration/filtering/#using-before-send` |
| Sentry FastAPI Integration | `https://docs.sentry.io/platforms/python/guides/fastapi/` |
| Sentry Security & Privacy | `https://docs.sentry.io/security/` |

### 7.2 Key Patterns for Guinevere

**Mandatory Configuration (user constraint):**

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

def strip_sensitive(event, hint):
    """before_send scrubber — blocks Critical-class and PII data."""
    # Remove request body
    if 'request' in event:
        if 'data' in event['request']:
            event['request']['data'] = '[REDACTED]'
        # Remove cookies
        if 'cookies' in event['request']:
            event['request']['cookies'] = '[REDACTED]'
        # Remove headers that may contain tokens
        if 'headers' in event['request']:
            for sensitive_header in ['authorization', 'cookie', 'x-api-key']:
                if sensitive_header in event['request']['headers']:
                    event['request']['headers'][sensitive_header] = '[REDACTED]'
    # Remove user data
    if 'user' in event:
        event['user'] = {'id': '[REDACTED]'}
    # Check for Critical-class data patterns
    if 'exception' in event:
        for exc in event['exception'].get('values', []):
            if exc.get('type') == 'CriticalDataExposure':
                # Drop event entirely for Critical data leaks
                return None
    return event

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[
        FastApiIntegration(),
        LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
    ],
    traces_sample_rate=0.1,
    send_default_pii=False,  # MUST be false
    before_send=strip_sensitive,
    environment="production",
)
```

**What Sentry Must Receive:**

- Exception type and message (after scrubbing).
- Stack trace (function names, module paths — no local variable values by default).
- Trace ID for correlation.
- Request URL (path only, not query parameters with sensitive data).

**What Sentry Must Never Receive:**

- User PII (email, name, IP address — `send_default_pii=false` ensures this).
- Database query contents or results.
- Memory content, surveillance data, or prompts.
- Safe-word text, intimate content, or raw surveillance payloads.
- Secrets, keys, tokens, or decrypted credential data.

### 7.3 Guinea-Specific Adaptation

- Wrap `before_send` to integrate with DataGovernance classification:
  - If event class is Critical → drop event entirely.
  - If event contains safe-word, intimate, or surveillance patterns → drop or scrub to metadata only.
- Log scrubbing failures to local audit log for monthly governance review.
- Sentry DSN stored in SOPS-encrypted `.env.sops`, not in code.

---

## 8. Google SRE — SLO/Error Budget and Alerting Principles

### 8.1 Authoritative References

| Reference | URL |
|---|---|
| Google Site Reliability Engineering (Book) | `https://sre.google/sre-book/table-of-contents/` |
| Google SRE Workbook — Alerting | `https://sre.google/workbook/alerting/` |
| Google SRE — Monitoring Distributed Systems | `https://sre.google/sre-book/monitoring-distributed-systems/` |
| Google SRE — Service Level Objectives | `https://sre.google/sre-book/service-level-objectives/` |
| Google SRE — Error Budget | `https://sre.google/sre-book/error-budget/` |

### 8.2 Key Patterns for Guinevere

**SLO Categories for Single-User System:**

- **Availability:** LLM/9Router responds to 99% of requests within 30s.
- **Latency:** P95 LLM response < 15s; P95 API response < 500ms.
- **Backup Freshness:** Hot backup age < 1 hour; cold backup age < 24 hours.
- **Alert Delivery:** SEV0 alert delivered within 1 minute of detection.
- **Safety Latency:** Safe-word detection < 1 second from input.

**Error Budget Definition:**

- Monthly error budget = (1 - SLO) × monthly requests.
- For 99% SLO and 10,000 monthly requests: 100 allowed failures.
- When error budget is exhausted: freeze non-critical deployments, focus on reliability.

**Alert Severity from SLO:**

- `Burn rate > 10x for 30 min` → SEV2 (significant error budget consumption).
- `Burn rate > 100x for 5 min` → SEV1 (critical error budget consumption).
- `Error budget 50% consumed before mid-month` → SEV3 (monitoring/review).

### 8.3 Guinea-Specific Adaptation

- Single-user system does not need 99.99% availability, but since the user relies on Guinevere for productivity and safety:
  - LLM/9Router availability: target 99.5%.
  - Surveillance ingestion availability: target 99.9%.
  - Core service availability: target 99%.
- SLO targets must be documented in the Observability spec and reviewed monthly.

---

## 9. FinOps — Anomaly Alerts

### 9.1 Authoritative References

| Reference | URL |
|---|---|
| FinOps Framework — Anomaly Management | `https://www.finops.org/framework/capabilities/anomaly-management/` |
| FinOps — Continuous Improvement | `https://www.finops.org/framework/capabilities/continuous-improvement/` |
| FinOps — Cloud Cost Optimization | `https://www.finops.org/framework/` |

### 9.2 Key Patterns for Guinevere

**Cost Alert Thresholds:**

- Daily LLM cost > 2x moving average of past 7 days → SEV3.
- Daily total provider cost > 3x baseline → SEV2.
- Unbilled spend spike detected → SEV2.
- Error budget exhaustion due to retry costs → SEV3.

**Cost Dimensions:**

- LLM API calls via 9Router: model, tokens, use_case.
- Surveillance API costs: storage, bandwidth.
- VPS infrastructure: fixed monthly cost.

**Dashboard Panels:**

- Daily cost by provider/service.
- Cost trend: current month vs previous month.
- Cost anomaly events.

### 9.3 Guinea-Specific Adaptation

- Cost tracking must collect `guinevere_api_cost_total{provider, model}` from 9Router billing data.
- 9Router cost data must be scraped via API or ingested via push to Prometheus.
- Cost thresholds must be encoded as Prometheus recording rules, not hardcoded in alert receivers.
- Budget guardrails must pause non-essential autonomous loops when cost anomaly is detected.

---

## 10. Backup/Restore — Alerting Patterns

### 10.1 Authoritative References

| Reference | URL |
|---|---|
| Prometheus Blackbox Exporter | `https://github.com/prometheus/blackbox_exporter` |
| pg_stat_activity Monitoring | `https://www.postgresql.org/docs/current/monitoring-stats.html` |
| Grafana Loki Backup Config | `https://grafana.com/docs/loki/latest/operations/storage/` |

### 10.2 Key Patterns for Guinevere

**Backup Alert Rules:**

```yaml
- alert: BackupFailed
  expr: guinevere_backup_success_total{type="postgres-cold"} offset 24h
        unless guinevere_backup_success_total{type="postgres-cold"} > 0
  for: 1h
  labels:
    severity: SEV2
  annotations:
    summary: "PostgreSQL cold backup failed in the last 24 hours"

- alert: OldBackup
  expr: time() - guinevere_backup_age_seconds{type="postgres-cold"} > 86400
  for: 30m
  labels:
    severity: SEV1
  annotations:
    summary: "No valid PostgreSQL backup for more than 24 hours"
```

**Restore Alert Rules:**

```yaml
- alert: RestoreValidationFailed
  expr: guinevere_restore_validation_success_total{type="postgres"} == 0
        unless guinevere_backup_success_total{type="postgres-cold"} == 0
  for: 24h
  labels:
    severity: SEV1
  annotations:
    summary: "Restore validation has not succeeded in the last 24 hours"
```

**Backup Size Anomaly:**

```yaml
- alert: BackupSizeAnomaly
  expr: abs(
        guinevere_backup_size_bytes{type="postgres-cold"}
        - avg_over_time(guinevere_backup_size_bytes{type="postgres-cold"}[30d])
      ) / avg_over_time(guinevere_backup_size_bytes{type="postgres-cold"}[30d])
      > 0.2
  for: 1 occurrence
  labels:
    severity: SEV3
  annotations:
    summary: "Backup size changed by more than 20% from 30-day average"
```

### 10.3 Guinea-Specific Adaptation

- Backup alert rules must reference `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` retention classes.
- Backup failure must propagate `incident_id` from IncidentResponse runbook.
- Restore drill events from DRILL-DB-001 must be tracked as Prometheus metrics.

---

## 11. Security Monitoring Patterns

### 11.1 Authoritative References

| Reference | URL |
|---|---|
| OWASP Monitoring Guide | `https://owasp.org/www-project-monitoring-guide/` |
| CIS Benchmarks for Linux | `https://www.cisecurity.org/cis-benchmarks/` |
| CrowdSec Documentation | `https://docs.crowdsec.net/` |
| Fail2Ban Documentation | `https://github.com/fail2ban/fail2ban` |

### 11.2 Key Patterns for Guinevere

**Security Event Metrics:**

```yaml
- alert: SSHBreakInAttempt
  expr: rate(fail2ban_jail_failures_total{jail="sshd"}[5m]) > 5
  labels:
    severity: SEV3
  annotations:
    summary: "SSH break-in attempt detected"

- alert: CrowdSecTriggered
  expr: crowdsec_decisions_total{scenario="crowdsec/*"} > 0
  labels:
    severity: SEV3
  annotations:
    summary: "CrowdSec blocked a malicious IP"

- alert: UnauthorizedAccessDenied
  expr: rate(guinevere_access_denied_total[5m]) > 10
  labels:
    severity: SEV3
  annotations:
    summary: "Multiple unauthorized access attempts detected"
```

**Audit Log Monitoring:**

- Monitor `system.audit_trail` for unexpected patterns.
- Track `guinevere_access_denied_total{principal, resource_class}` for security events.
- Alert on break-glass activation: `guinevere_break_glass_active > 0`.

### 11.3 Guinea-Specific Adaptation

- Security monitoring must not expose raw Critical data in alert annotations.
- Alert descriptions: "Unauthorized access detected to Critical resource" — not the resource path.
- Tailscale ACL changes monitored via Tailscale integration, not Prometheus.
- Secret scanner alerts: SEV1 for confirmed credential exposure, SEV2 for suspected patterns.

---

## 12. AI/LLM — Privacy-Safe Observability

### 12.1 Authoritative References

| Reference | URL |
|---|---|
| Google — Gemini/LLM Privacy Best Practices | `https://cloud.google.com/gemini/docs/best-practices/privacy` |
| Anthropic — Building Safe AI Systems | `https://www.anthropic.com/news/building-safe-ai-systems` |
| OpenTelemetry GenAI Semantic Conventions | `https://opentelemetry.io/docs/specs/semconv/gen-ai/` |
| ML Observability | `https://www.evidentlyai.com/` |
| Langfuse (Open Source LLM Observability) | `https://langfuse.com/docs/` |
| Weights & Biases Prompts | `https://docs.wandb.ai/guides/prompts` |

### 12.2 Key Patterns for Guinevere

**What Must Be Observed:**

- Model used per request.
- Token counts (input, output, total).
- Latency per request.
- Error codes and rates.
- Cost per request (from 9Router billing).
- Rate limit hits and retries.

**What Must Be Scrubbed:**

- Prompt content (must never be logged or sent to external observability tools by default).
- Model response content (same rule).
- Any user-identifiable data in request metadata.
- Memory injections, surveillance-derived prompt content.

**Privacy-Safe Monitoring Architecture:**

```
[Guinevere Core] → Prometheus metrics (no LLM content)
                → Sentry (error metadata only, before_send scrubber)
                → Loki (request/response metadata, no content)
                → 9Router billing API scrape → Prometheus cost metrics
```

**Prompt Logging (If Required for Debug):**

- Must be opt-in, with explicit incident_id evidence.
- Must be stored locally, encrypted, and minimized (prompt structure, not full content).
- Must be auto-deleted after 30 days or incident closure.

### 12.3 Guinea-Specific Adaptation

- Never log `guinevere_core` prompt content or sub-agent prompt content to Loki/Sentry/Grafana.
- Track metrics by model and use_case, not by conversation or task content.
- 9Router API provides cost data — scrape this separately from LLM content logs.
- If LLM observability is needed for debugging, use local encrypted file storage, not external services.

---

## 13. Implementation Pattern Index

| Pattern | Section | Priority | Dependencies |
|---|---|---|---|
| Metric naming convention | 2 | HIGH | None (doc standard) |
| Label cardinality budget | 2 | HIGH | Prometheus configuration |
| Alertmanager routing tree | 3 | HIGH | Alertmanager config file |
| Grafana dashboard-as-code | 4 | HIGH | Grafana provisioning |
| Loki structured metadata | 5 | HIGH | Loki + Promtail config |
| W3C trace propagation | 6 | HIGH | FastAPI middleware, sub-agent SDK |
| Sentry before_send scrubber | 7 | HIGH | Sentry SDK init |
| SLO/error budget definition | 8 | MEDIUM | Prometheus recording rules |
| Cost anomaly alert rules | 9 | MEDIUM | 9Router billing API |
| Backup alert rules | 10 | HIGH | prometheus rules + guinevere_exporter |
| Security event alert rules | 11 | HIGH | fail2ban + CrowdSec exporters |
| LLM prompt logging privacy | 12 | CRITICAL | Guard middleware + DataGovernance policy |

---

## 14. Gap Items for Final Spec

| Gap ID | Missing Pattern | Required Action |
|---|---|---|
| EXT-GAP-001 | SLO targets not yet defined for single-user system | Spec must define SLO pages per surface |
| EXT-GAP-002 | 9Router billing data not yet scraped as Prometheus metric | Spec must define scrape endpoint or pushgateway path |
| EXT-GAP-003 | Alertmanager config not yet generated | Spec must include canonical alertmanager.yaml template |
| EXT-GAP-004 | Grafana provisioning directory not yet created | Spec must define directory structure |
| EXT-GAP-005 | Sentry DSN not yet in .env.sops | Spec must reference secrets rotation pattern |
| EXT-GAP-006 | Loki retention policy not yet configured | Spec must define stream retention per retention class |
| EXT-GAP-007 | Cost threshold values not defined (IR-BG-005) | Spec must document thresholds or reference FinOps model |

---

**End of Observability & Alerting External References Report v1.0**

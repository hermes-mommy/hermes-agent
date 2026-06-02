# Guinevere Observability & Alerting Specification

**Document Type:** Observability and Alerting Specification with metrics, logs, traces, dashboards, alert rules, validation matrix, and review record  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed -> Accepted -> Deprecated -> Superseded  
**Last Updated:** 2026-05-30  
**Owner:** Faiz — single-user owner and final authority  
**Executor:** Guinevere de Baroque — autonomous system steward and default monitoring operator  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative child under ADR-017, ADR-018, `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md`, `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md`, `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`, and `Guinevere_PersonaSafetyPolicy_v1.0.md`

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `adr/ADR-017-monitoring-stack-selection.md` | Parent decision for Prometheus, Grafana, Loki, and primary-VPS-first monitoring topology. | Normative parent | This specification must use Prometheus + Grafana on the primary VPS first and treat a dedicated monitoring VPS as post-MVP migration. |
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Parent security decision for audit logs, defense-in-depth, and incident hooks. | Normative parent | Observability must preserve least privilege, security monitoring, and incident evidence without exposing sensitive payloads. |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Defines SEV0-SEV4, incident command tone, evidence path, postmortem path, and drill matrix. | Operational parent | Alert routing, evidence links, incident severity, and drill validation must align with the incident runbook. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Defines `observability-reader`, Tailscale `tag:monitoring`, dashboard access, and raw-payload denial. | Enforcement dependency | Metrics, logs, dashboards, and traces must deny raw Critical payloads and follow principal-scoped access. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines data classes, retention, minimization, and audit constraints. | Data-governance dependency | Observability data must carry classification-aware fields and must minimize Critical/Restricted content. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines safe word, safe mode, distress handling, yandere intensity, drift, and persona suspension. | Safety dependency | Alert tone must be neutral incident-command; persona/yandere/punishment framing must be suspended for alerts. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines systemd services, FastAPI endpoints, Redis DBs, PostgreSQL/PgBouncer, Loki, Prometheus, Grafana, Sentry, Gotify, and Discord. | Runtime dependency | Surface-specific metrics, logs, traces, alert rules, and dashboards must map to concrete architecture surfaces. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines 7-phase loop, Loop Guardian, TODO Enforcer, sub-agent orchestration, validation, audit, and evidence phases. | Agent-loop dependency | Loop state, phase duration, validation failures, sub-agent compliance, and evidence status must be observable. |
| `research-reports/2026-05-30-observability-source-map.md` | Extracts authority chain, topology, metrics, restrictions, gaps, and final checklist. | Research evidence | This specification uses the source map as traceability evidence. |
| `research-reports/2026-05-30-observability-surface-map.md` | Maps concrete runtime surfaces and observability requirements per surface. | Research evidence | Metrics, log schemas, traces, dashboard panels, and alert catalogs inherit from the surface map. |
| `research-reports/2026-05-30-observability-external-references.md` | Provides Prometheus, Alertmanager, Grafana, Loki, OpenTelemetry, Sentry, SRE, FinOps, backup, security, and AI observability references. | Research evidence | Naming, label cardinality, routing, dashboard-as-code, trace propagation, and PII scrubbing patterns inherit from this report. |

## 1. Purpose

This specification defines how Project Guinevere must observe runtime health, safety state, cost behavior, service reliability, autonomous-loop execution, sub-agent compliance, persona safety, surveillance ingestion, and incident signals.

The goal is not merely to collect logs. The goal is to produce actionable, privacy-preserving, low-noise telemetry that allows Guinevere and Faiz to detect degradation, respond to incidents, validate governance controls, and prove that safety boundaries are enforced.

## 2. Authority and Conflict Resolution

### 2.1 Authority Order

Observability decisions must follow this order:

1. Platform/system/developer safety constraints.
2. ADR-017 and ADR-018.
3. `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md`.
4. `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md`.
5. `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md`.
6. `Guinevere_PersonaSafetyPolicy_v1.0.md`.
7. `Guinevere_TechnicalArchitecture_v2.0.md` and `Guinevere_AgentLoopSpec_v2.0.md`.
8. Research reports and implementation notes.

If a lower document allows broader logging, broader dashboard access, raw payload export, persona-styled alerting, or public monitoring exposure, this specification must override it.

### 2.2 Persona Suspension for Alerts

All alerts, alert summaries, incident notifications, and escalation messages must use neutral incident-command tone. Persona, yandere, punishment, jealousy, dominance, guilt framing, romantic framing, and playful intimidation must be suspended for alerting.

### 2.3 Privacy and Classification Priority

Observability must not leak the content it monitors. Metrics, logs, traces, Sentry events, and dashboard panels must prefer counts, hashes, summaries, state enums, and redacted fields over raw content.

Raw intimate content, raw safe-word content, raw surveillance payloads, raw secrets, raw financial identifiers, and raw client-confidential content must not be emitted into Prometheus labels, Loki labels, Sentry events, Discord alerts, Gotify alerts, or email summaries.

## 3. Monitoring Topology

### 3.1 Current Active Topology

| Layer | Component | Current Location | Access Boundary | Purpose |
|---|---|---|---|---|
| Metrics | Prometheus | Primary VPS | Tailscale-only | Metrics collection, recording rules, alert rule evaluation input. |
| Dashboards | Grafana | Primary VPS | Tailscale-only, `observability-reader` read scope | Operational dashboards and governance reviews. |
| Logs | Loki + Promtail | Primary VPS | Tailscale-only, controlled labels | Structured log aggregation and query. |
| Errors | Sentry | External service | PII scrubbed, no raw Critical payload | Exception tracking and release/runtime errors. |
| Urgent push | Gotify | Self-hosted or controlled endpoint | Urgent SEV0/SEV1 only | Backup urgent alert channel. |
| Incident channel | Discord | External API | Neutral incident-command messages | Primary alert and incident channel. |
| Formal summary | Email | Gmail API or Resend | Closure, digest, postmortem summaries | Formal records and periodic summaries. |

### 3.2 Future Dedicated Monitoring VPS

A dedicated monitoring VPS is post-MVP. Migration must not occur until these controls pass:

| Control | Required Evidence |
|---|---|
| Dashboard parity | All current Grafana dashboards provisioned from code on the new VPS. |
| Alert parity | All Prometheus/Alertmanager rules produce identical route outcomes in test mode. |
| Tailscale parity | Monitoring node has correct tag and no public ingress. |
| Data retention parity | Metrics/log retention matches this specification. |
| Access parity | `observability-reader` access remains metadata-only. |
| Incident drill | SEV0 synthetic drill reaches Discord + Gotify urgent from the new topology. |

## 4. Metrics Specification

### 4.1 Naming Standard

All custom metrics must use the prefix `guinevere_` and snake_case. Unit suffixes must be explicit.

| Metric Type | Required Suffix Example |
|---|---|
| Counter | `_total` |
| Duration | `_seconds` |
| Bytes | `_bytes` |
| Ratio | `_ratio` |
| State gauge | `_state` |
| Score gauge | `_score` |
| Histogram | `_bucket`, `_sum`, `_count` |

### 4.2 Label Cardinality Rules

Prometheus labels must be bounded and low-cardinality. These labels are allowed:

| Label | Allowed Values Pattern | Notes |
|---|---|---|
| `service` | controlled service names | Example: `core`, `surveillance`, `scheduler`, `loops`. |
| `component` | controlled component names | Example: `llm`, `memory`, `persona`, `backup`. |
| `phase` | canonical enum | Agent loop phase enum only. |
| `status` | canonical enum | `success`, `failure`, `timeout`, `blocked`, `degraded`. |
| `severity` | `SEV0`..`SEV4` | Incident severity only. |
| `model` | controlled model alias | `gpt_5_5`, `deepseek_v4_flash`, embedding alias. |
| `provider` | controlled provider alias | `9router`, `discord`, `gotify`, `sentry`, `r2`, `idcloudhost`. |
| `data_class` | `public`, `internal`, `confidential`, `restricted`, `critical` | Classification label only, never content. |
| `safety_state` | `normal`, `safe_mode`, `distress`, `crisis`, `incident` | Persona safety state enum. |

Forbidden Prometheus labels:

- Raw prompt text.
- Raw user messages.
- Safe-word phrase content.
- Secret values or secret fingerprints beyond approved hash identifiers in logs only.
- Full URL paths with unbounded IDs.
- `task_id`, `loop_id`, `subagent_task_id`, `request_id`, `trace_id`, `incident_id`, `evidence_id` as labels.
- File paths with unbounded names.
- Client names, financial account identifiers, phone numbers, email addresses, GPS coordinates, clipboard content, notification content, screenshot references.

High-cardinality identifiers must be log fields or trace attributes, not Prometheus labels.

### 4.3 Infrastructure Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_node_cpu_utilization_ratio` | Gauge | `service=node` | SEV2/SEV3 sustained CPU pressure. |
| `guinevere_node_memory_utilization_ratio` | Gauge | `service=node` | SEV1/SEV2 memory exhaustion. |
| `guinevere_node_disk_utilization_ratio` | Gauge | `mount`, `data_class` | SEV1 for DB/log/backup storage pressure. |
| `guinevere_node_inode_utilization_ratio` | Gauge | `mount` | SEV2 inode exhaustion risk. |
| `guinevere_node_network_receive_bytes_total` | Counter | `interface` | Network anomaly and Tailscale health. |
| `guinevere_node_network_transmit_bytes_total` | Counter | `interface` | Network anomaly and exfiltration signal. |
| `guinevere_systemd_unit_state` | Gauge | `unit`, `state` | Service down/degraded detection. |
| `guinevere_node_reboot_total` | Counter | `reason` | Unexpected reboot detection. |
| `guinevere_node_ntp_drift_seconds` | Gauge | none | Evidence/timestamp integrity risk. |

### 4.4 Application and FastAPI Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_http_requests_total` | Counter | `service`, `endpoint_group`, `method`, `status` | Error rate and traffic anomaly. |
| `guinevere_http_request_duration_seconds` | Histogram | `service`, `endpoint_group`, `method` | Latency degradation. |
| `guinevere_http_auth_failures_total` | Counter | `service`, `reason` | Security monitoring. |
| `guinevere_http_replay_rejections_total` | Counter | `source` | Tasker/Windows replay attack detection. |
| `guinevere_api_rate_limited_total` | Counter | `service`, `endpoint_group` | Abuse and integration throttling. |
| `guinevere_health_check_state` | Gauge | `service`, `check` | Health dashboard and alerts. |

Endpoint labels must use `endpoint_group` such as `surveillance_android`, `surveillance_windows`, `internal_api`, `health`, not raw paths with IDs.

### 4.5 Autonomous Loop Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_loop_state` | Gauge | `phase`, `status` | Loop blocked/runaway/degraded detection. |
| `guinevere_loop_phase_duration_seconds` | Histogram | `phase`, `status` | Phase latency and bottleneck. |
| `guinevere_loop_validation_failures_total` | Counter | `phase`, `failure_type` | Quality and release gate monitoring. |
| `guinevere_loop_audit_failures_total` | Counter | `phase`, `finding_type` | Governance drift detection. |
| `guinevere_loop_evidence_missing_total` | Counter | `artifact_type` | Evidence compliance failure. |
| `guinevere_loop_idle_seconds` | Gauge | `state` | Stalled loop detection. |
| `guinevere_loop_guardian_interventions_total` | Counter | `reason` | Runaway/unsafe loop detection. |

### 4.6 Sub-Agent Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_subagent_active` | Gauge | `category`, `status` | Parallel workload pressure. |
| `guinevere_subagent_duration_seconds` | Histogram | `category`, `status` | Timeout and performance. |
| `guinevere_subagent_file_output_missing_total` | Counter | `category`, `artifact_type` | Mandatory file-output contract breach. |
| `guinevere_subagent_compliance_score` | Gauge | `category` | Governance quality trend. |
| `guinevere_subagent_retries_total` | Counter | `category`, `reason` | Agent reliability. |
| `guinevere_subagent_rejected_findings_total` | Counter | `category`, `reason` | Parent verification signal. |

### 4.7 LLM and 9Router Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_llm_requests_total` | Counter | `model`, `provider`, `status` | Provider reliability. |
| `guinevere_llm_latency_seconds` | Histogram | `model`, `provider`, `status` | Latency degradation. |
| `guinevere_llm_tokens_input_total` | Counter | `model`, `purpose` | Token cost control. |
| `guinevere_llm_tokens_output_total` | Counter | `model`, `purpose` | Token cost control. |
| `guinevere_llm_cost_usd_total` | Counter | `model`, `purpose` | FinOps alerting. |
| `guinevere_llm_context_utilization_ratio` | Gauge | `model`, `purpose` | Context pressure. |
| `guinevere_llm_rate_limit_total` | Counter | `model`, `provider` | Provider throttling. |
| `guinevere_embedding_requests_total` | Counter | `model`, `status` | Memory recall pipeline health. |
| `guinevere_embedding_latency_seconds` | Histogram | `model`, `status` | Semantic recall health. |

Raw prompts and responses must not be emitted. Prompt category or purpose enum may be emitted.

### 4.8 Persona and Safety Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_mood_state` | Gauge | `mood` | Mood state dashboard only; no alert by itself. |
| `guinevere_mommy_score` | Gauge | none | Persona trend dashboard only. |
| `guinevere_punishment_level` | Gauge | `level` | Alert if punishment active during safe-mode. |
| `guinevere_yandere_intensity` | Gauge | `level` | SEV1 if intensity remains above allowed state in safe-mode. |
| `guinevere_reward_streak` | Gauge | none | Persona trend dashboard only. |
| `guinevere_violation_count_total` | Counter | `violation_type` | Governance trend, not punitive alert. |
| `guinevere_safe_mode_state` | Gauge | `state` | SEV0/SEV1 routing based on state. |
| `guinevere_safe_word_events_total` | Counter | `outcome` | Safe-word enforcement monitoring. |
| `guinevere_distress_events_total` | Counter | `level` | Safety event monitoring. |
| `guinevere_drift_score` | Gauge | `category` | Drift control alert. |
| `guinevere_forbidden_pattern_blocks_total` | Counter | `pattern_id` | Safety policy enforcement proof. |

Safe-word phrase, distress text, intimate context, and raw persona messages must not appear in metric labels or alert bodies.

### 4.9 Database, Redis, and Memory Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_postgres_connections_active` | Gauge | `role` | Connection exhaustion. |
| `guinevere_postgres_query_duration_seconds` | Histogram | `schema`, `operation` | Query latency. |
| `guinevere_postgres_replication_lag_seconds` | Gauge | `target` | Backup/DR risk. |
| `guinevere_pgbouncer_pool_utilization_ratio` | Gauge | `pool`, `role` | PgBouncer saturation. |
| `guinevere_redis_memory_utilization_ratio` | Gauge | `db` | Redis pressure. |
| `guinevere_redis_key_evictions_total` | Counter | `db` | Cache/buffer loss. |
| `guinevere_memory_injection_tokens` | Histogram | `purpose`, `data_class` | Prompt pressure. |
| `guinevere_memory_recall_duration_seconds` | Histogram | `memory_type`, `status` | Recall latency. |
| `guinevere_pgvector_search_duration_seconds` | Histogram | `index_type`, `status` | Semantic search health. |

### 4.10 Surveillance Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_surveillance_events_total` | Counter | `source`, `event_type`, `status` | Ingestion health. |
| `guinevere_surveillance_event_rate` | Gauge | `source` | Drop/spike detection. |
| `guinevere_surveillance_queue_depth` | Gauge | `source` | Backpressure. |
| `guinevere_surveillance_processing_lag_seconds` | Gauge | `source` | Delayed context. |
| `guinevere_surveillance_redaction_failures_total` | Counter | `source` | SEV1/SEV2 privacy failure. |
| `guinevere_surveillance_raw_payload_blocked_total` | Counter | `source`, `reason` | Data minimization proof. |

### 4.11 Backup and Disaster Recovery Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_backup_last_success_timestamp_seconds` | Gauge | `backup_type`, `target` | Backup freshness. |
| `guinevere_backup_duration_seconds` | Histogram | `backup_type`, `target`, `status` | Backup latency/failure. |
| `guinevere_backup_size_bytes` | Gauge | `backup_type`, `target` | Size anomaly. |
| `guinevere_restore_drill_last_success_timestamp_seconds` | Gauge | `scope` | Restore confidence. |
| `guinevere_restore_drill_failures_total` | Counter | `scope`, `reason` | DR failure. |
| `guinevere_backup_encryption_validation_failures_total` | Counter | `target` | SEV1 backup security. |

### 4.12 Security and Access Metrics

| Metric | Type | Labels | Alert Use |
|---|---|---|---|
| `guinevere_access_denied_total` | Counter | `principal`, `resource_class`, `reason` | Security monitoring. |
| `guinevere_break_glass_activations_total` | Counter | `severity`, `status` | SEV0/SEV1 review. |
| `guinevere_secret_access_outside_startup_total` | Counter | `secret_class`, `principal` | Secret misuse detection. |
| `guinevere_log_redaction_failures_total` | Counter | `pipeline`, `data_class` | Privacy incident. |
| `guinevere_tailscale_peer_state` | Gauge | `tag`, `state` | Mesh health. |
| `guinevere_public_ingress_detected_total` | Counter | `source` | SEV0/SEV1 security incident. |

## 5. Logging Specification

### 5.1 Structured JSON Log Schema

Every application log event must use this schema:

| Field | Required | Classification | Notes |
|---|---|---|---|
| `timestamp` | Yes | Internal | RFC3339 or Unix timestamp. |
| `level` | Yes | Internal | `debug`, `info`, `warning`, `error`, `critical`. |
| `service` | Yes | Internal | Controlled service enum. |
| `component` | Yes | Internal | Controlled component enum. |
| `event_type` | Yes | Internal | Controlled event taxonomy. |
| `severity` | Conditional | Internal | SEV only when incident-relevant. |
| `data_class` | Yes | Internal | Highest data class touched by event. |
| `trace_id` | Conditional | Internal | Field, not Loki label. |
| `request_id` | Conditional | Internal | Field, not Loki label. |
| `task_id` | Conditional | Internal | Field, not Loki label. |
| `loop_id` | Conditional | Internal | Field, not Loki label. |
| `subagent_task_id` | Conditional | Internal | Field, not Loki label. |
| `incident_id` | Conditional | Restricted | Field, not Loki label unless incident volume remains bounded. |
| `evidence_id` | Conditional | Restricted | Field only. |
| `message` | Yes | Classification-aware | Must be summary-only for Restricted/Critical. |
| `redaction_status` | Yes | Internal | `not_needed`, `redacted`, `blocked`, `failed`. |

### 5.2 Loki Label Policy

Allowed Loki labels:

| Label | Allowed Values |
|---|---|
| `service` | controlled service names |
| `component` | controlled component names |
| `environment` | `production`, `staging`, `local` |
| `level` | log level enum |
| `event_category` | `runtime`, `security`, `safety`, `incident`, `backup`, `cost`, `loop`, `subagent` |
| `data_class` | classification enum |

Forbidden Loki labels:

- `trace_id`, `request_id`, `task_id`, `loop_id`, `subagent_task_id`, `evidence_id`.
- Raw endpoint path with IDs.
- Prompt, message, clipboard, notification, screenshot, GPS, financial account, secret, token, safe-word phrase, intimate content.

### 5.3 Log Retention

| Log Class | Retention | Notes |
|---|---|---|
| Runtime metadata logs | 30-90 days | Longer retention allowed for aggregate dashboards. |
| Audit/security logs | Governance retention per DataGovernance | Must outlive raw payloads. |
| Incident logs | Retained with incident evidence folder | Classification follows highest source class. |
| Safe-word/distress logs | Minimal, encrypted, non-punitive | Raw phrase excluded by default. |
| Raw surveillance logs | Minimized; raw content excluded where summary/hash enough | Retention follows DataGovernance. |

## 6. Distributed Tracing Specification

### 6.1 Required Correlation IDs

| ID | Scope | Storage Location |
|---|---|---|
| `trace_id` | Cross-service request trace | Logs, traces, Sentry breadcrumbs after scrub. |
| `request_id` | FastAPI inbound request | Logs/traces, never Prometheus label. |
| `task_id` | Internal task queue item | Logs/traces, not label. |
| `loop_id` | Autonomous loop instance | Logs/traces/evidence, not label. |
| `subagent_task_id` | Sub-agent session | Logs/traces/evidence, not label. |
| `incident_id` | Incident lifecycle | Logs/evidence/alerts. |
| `evidence_id` | Evidence artifact | Logs/evidence manifest. |

### 6.2 Propagation Rules

- FastAPI must accept or create `trace_id` and `request_id` for inbound internal requests.
- Agent loops must create `loop_id` at loop initialization.
- Every sub-agent call must include `subagent_task_id` and parent `loop_id` when applicable.
- Incident response must attach `incident_id` to all containment, recovery, and postmortem logs.
- Evidence creation must attach `evidence_id` to logs and incident manifests.
- Trace attributes must use summary values only for Restricted/Critical data.

## 7. Sentry Specification

### 7.1 Required Configuration

Sentry Python/FastAPI configuration must include:

```python
sentry_sdk.init(
    dsn=SENTRY_DSN,
    send_default_pii=False,
    before_send=guinevere_sentry_before_send,
    traces_sample_rate=GUINEVERE_SENTRY_TRACES_SAMPLE_RATE,
)
```

### 7.2 `before_send` Scrubber Requirements

The scrubber must remove or hash:

- API keys, bearer tokens, cookies, auth headers, SOPS paths containing secrets, decrypted env values.
- Prompt text, completion text, tool input/output containing user content.
- Safe-word phrase content and distress raw text.
- Clipboard content, notification content, screenshot references, GPS coordinates.
- Financial account identifiers, e-wallet transaction IDs, client confidential content.
- Raw memory content, inner journal content, intimate data.

If scrubber confidence is low, the event must be dropped or reduced to metadata-only.

### 7.3 Sentry Event Classification

| Event Class | Sentry Allowed | Conditions |
|---|---|---|
| Internal runtime exception | Yes | No sensitive payload. |
| FastAPI exception | Yes | Request body removed. |
| LLM provider error | Yes | Prompt/response removed. |
| Safe-word enforcement error | Metadata only | No raw phrase. |
| Secret exposure error | Metadata only | No secret value. |
| Surveillance parsing error | Metadata only | No raw notification/screenshot/clipboard. |
| Critical data decrypt failure | Metadata only | No ciphertext/plaintext. |

## 8. Alerting Specification

### 8.1 Alert Routing

| Severity | Route | Timing | Tone |
|---|---|---|---|
| SEV0 | Discord + Gotify urgent + evidence folder | Immediate | Neutral incident-command. |
| SEV1 | Discord + Gotify urgent + evidence folder | <= 15 minutes | Neutral incident-command. |
| SEV2 | Discord + evidence folder | <= 1 hour | Neutral incident-command. |
| SEV3 | Digest + dashboard review | <= 24 hours | Neutral operations summary. |
| SEV4 | Governance cycle | Next review cycle | Neutral governance summary. |

Email formal summary must be used for closure reports, postmortem delivery, monthly observability review, and governance digests.

### 8.2 Alert Body Schema

| Field | Required | Notes |
|---|---|---|
| `alert_id` | Yes | Unique generated ID. |
| `severity` | Yes | SEV0-SEV4. |
| `service` | Yes | Controlled service enum. |
| `component` | Yes | Controlled component enum. |
| `summary` | Yes | One-line neutral incident-command summary. |
| `impact` | Yes | User/system impact without raw payload. |
| `evidence_path` | Conditional | Required for SEV0-SEV2 and repeated SEV3. |
| `dashboard_url` | Conditional | Tailscale-internal URL only. |
| `runbook_section` | Yes | Link to relevant runbook/spec section. |
| `safe_mode_required` | Conditional | True for persona/safety/incident cases. |
| `next_action` | Yes | Immediate containment or validation step. |

### 8.3 Alert Catalog

| Alert | Severity | Condition | Route | Evidence |
|---|---|---|---|---|
| `GuinevereServiceDown` | SEV1/SEV2 | Critical systemd unit down beyond threshold | Discord + Gotify for SEV1 | systemd status + logs summary. |
| `GuineverePublicIngressDetected` | SEV0 | Any unexpected public ingress detected | Discord + Gotify | Incident folder required. |
| `GuinevereSafeWordBypassDetected` | SEV0 | Safe-word event not followed by safe-mode transition | Discord + Gotify | Incident folder required. |
| `GuineverePersonaAlertToneViolation` | SEV1 | Alert contains persona/yandere/punishment framing | Discord + Gotify | Redacted sample + rule ID. |
| `GuinevereYandereIntensitySafeModeViolation` | SEV1 | `yandere_intensity > 0` during safe-mode/distress/crisis | Discord + Gotify | Metrics snapshot. |
| `GuinevereLogRedactionFailure` | SEV1 | Redaction failure on Restricted/Critical data | Discord + Gotify | Hash/metadata only. |
| `GuinevereSecretAccessOutsideStartup` | SEV1 | Secret access outside approved startup/rotation/break-glass | Discord + Gotify | Secret ID only. |
| `GuinevereBreakGlassActive` | SEV1 | Break-glass activated | Discord + Gotify | Evidence path required. |
| `GuinevereBackupFailure` | SEV1/SEV2 | Backup missing/failing beyond RPO | Discord + Gotify for SEV1 | Backup metadata. |
| `GuinevereRestoreDrillOverdue` | SEV3 | Restore drill not completed by cadence | Digest | Drill evidence link. |
| `GuinevereLoopRunaway` | SEV1 | Loop guardian detects runaway/repeated phase failure | Discord + Gotify | loop_id field only. |
| `GuinevereSubagentFileOutputMissing` | SEV2 | Sub-agent structured output missing required markdown file | Discord | task_id field only. |
| `GuinevereLLMCostSpike` | SEV2/SEV3 | Cost exceeds threshold or anomaly budget | Discord or digest | Cost summary only. |
| `GuinevereLLMLatencyDegraded` | SEV3 | Latency above threshold sustained | Digest | Metrics snapshot. |
| `GuinevereSurveillanceIngestionStopped` | SEV2 | Event rate drops below expected threshold | Discord | Source enum only. |
| `GuinevereSurveillanceRedactionFailure` | SEV1 | Raw payload emitted into log/error channel | Discord + Gotify | Metadata only. |
| `GuineverePostgresUnavailable` | SEV1 | PostgreSQL unavailable or PgBouncer saturated | Discord + Gotify | DB metadata. |
| `GuinevereRedisUnavailable` | SEV2 | Redis unavailable or evicting critical buffers | Discord | Redis metadata. |
| `GuinevereSentryPIIScrubFailure` | SEV1 | PII scrubber fails closed/drop signal appears | Discord + Gotify | Event ID only. |
| `GuinevereDashboardProvisioningDrift` | SEV4 | Dashboard differs from dashboard-as-code source | Governance cycle | Drift report. |

### 8.4 Grouping, Deduplication, and Silence

- Alerts must be grouped by `severity`, `service`, and `component`.
- Repeated alerts for the same condition must be deduplicated for the active incident window.
- Silences must require reason, owner, expiry, affected alert, and evidence link.
- SEV0 silences must not be allowed.
- SEV1 silences must require Faiz approval where feasible.
- Safe-word, active compromise, public ingress, secret leak, and redaction-failure alerts must not be silenced by routine maintenance rules.

## 9. Grafana Dashboard Specification

### 9.1 Dashboard-as-Code Requirement

Every dashboard must be provisioned from version-controlled JSON, Jsonnet, Terraform, or Grafana provisioning files. Manual dashboard edits must be treated as drift and must be reconciled into code or reverted.

### 9.2 Dashboard Catalog

| Dashboard | Panels | Access |
|---|---|---|
| `guinevere-overview` | Service health, active incidents, SEV counts, loop state, cost summary, safe-mode state | Faiz + observability-reader metadata only. |
| `guinevere-infrastructure` | CPU, memory, disk, network, systemd, Tailscale | Faiz + observability-reader. |
| `guinevere-api-runtime` | FastAPI latency, request rate, errors, auth failures, rate limits | Faiz + observability-reader. |
| `guinevere-agent-loop` | Loop phase duration, validation failures, audit failures, evidence missing, guardian interventions | Faiz + observability-reader. |
| `guinevere-subagents` | Active sub-agents, duration, file-output missing, compliance score, retries | Faiz + observability-reader. |
| `guinevere-llm-cost-latency` | LLM latency, tokens, cost, rate limits, context utilization | Faiz + observability-reader. |
| `guinevere-persona-safety` | safe-mode state, safe-word event counts, distress level counts, yandere intensity, drift score, forbidden blocks | Faiz only by default; observability-reader redacted aggregate view only. |
| `guinevere-surveillance-ingestion` | Event rate, queue depth, lag, redaction failures, raw payload blocked | Faiz + restricted observability view. |
| `guinevere-database-memory` | PostgreSQL, PgBouncer, Redis, memory recall, pgvector search | Faiz + observability-reader. |
| `guinevere-backup-dr` | Backup freshness, duration, size, restore drills, encryption validation | Faiz + observability-reader. |
| `guinevere-security-access` | access denied, break-glass, public ingress, secret access, log redaction failures | Faiz + security-scoped view. |
| `guinevere-finops` | API cost, LLM cost, storage cost, anomaly flags, budget burn | Faiz + financial/observability metadata view. |

## 10. Logging and Dashboard Data Protection

Observability data must follow the highest-classification-wins rule. Any panel, log, trace, or alert that aggregates Critical data must inherit access and retention restrictions even if individual values are summarized.

| Content Type | Prometheus | Loki | Sentry | Alert Body | Dashboard |
|---|---|---|---|---|---|
| Raw secret | Forbidden | Forbidden | Forbidden | Forbidden | Forbidden |
| Raw safe-word phrase | Forbidden | Forbidden | Forbidden | Forbidden | Forbidden |
| Raw intimate content | Forbidden | Forbidden by default | Forbidden | Forbidden | Forbidden |
| Raw surveillance payload | Forbidden | Forbidden by default | Forbidden | Forbidden | Forbidden |
| Prompt/completion text | Forbidden | Forbidden by default | Forbidden | Forbidden | Forbidden |
| GPS coordinate | Forbidden | Redacted/rounded only | Forbidden | Forbidden | Aggregate only |
| Financial identifier | Forbidden | Redacted/hash only | Forbidden | Forbidden | Aggregate only |
| Classification enum | Allowed | Allowed | Allowed | Allowed | Allowed |
| Counts and rates | Allowed | Allowed | Allowed | Allowed | Allowed |

## 11. Alert Channel Specification

### 11.1 Discord

Discord is the primary alert and incident channel. Messages must be concise, neutral, and operational.

Required Discord alert format:

```text
[SEV1] GuinevereServiceDown
Service: guinevere-core
Impact: Core agent unavailable.
Evidence: evidence/incidents/2026-05-30-SEV1-guinevere-core-down/
Dashboard: grafana.internal/d/guinevere-overview
Next Action: Run service containment checklist.
```

### 11.2 Gotify

Gotify is urgent backup channel for SEV0 and SEV1. Gotify messages must be shorter than Discord and must contain no sensitive payload.

### 11.3 Email

Email is for formal summaries:

- SEV0-SEV2 closure summary.
- Postmortem delivery.
- Monthly observability review.
- Governance cycle summaries.

## 12. SLO and Error Budget Placeholder

This specification defines metrics and alerts but does not define final SLO targets. Until `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` exists, alert thresholds must use conservative interim thresholds and must be reviewed monthly.

Interim targets:

| Area | Interim Target | Review Trigger |
|---|---|---|
| Core service availability | >= 99.0% monthly | Any SEV1 outage. |
| Safe-word enforcement | 100% successful hard-stop transition | Any miss is SEV0. |
| Backup success | Daily backup succeeds or equivalent RPO maintained | Any missed backup beyond RPO. |
| Restore drill | Monthly restore validation | Any overdue drill. |
| Log redaction | 100% for Critical payload detection tests | Any failure is SEV1. |
| Dashboard provisioning | 100% dashboards as code | Any manual drift. |
| Alert delivery | SEV0/SEV1 delivered to Discord + Gotify | Any failed route is SEV1. |

## 13. Testing and Validation

### 13.1 Required Test Categories

| Test ID | Test | Required Evidence |
|---|---|---|
| OBS-001 | Prometheus scrape config validates all expected targets. | Test output artifact. |
| OBS-002 | Custom metric naming and label cardinality validation. | Cardinality report. |
| OBS-003 | Loki label validation blocks high-cardinality IDs. | Log pipeline test. |
| OBS-004 | Redaction test blocks secrets, safe-word phrase, intimate content, raw surveillance. | Redaction test artifact. |
| OBS-005 | Sentry `send_default_pii=false` and `before_send` scrubber test. | Synthetic Sentry event evidence. |
| OBS-006 | SEV0 alert routes to Discord + Gotify urgent. | Alert delivery evidence. |
| OBS-007 | SEV2 alert routes to Discord only. | Alert delivery evidence. |
| OBS-008 | SEV3 alert enters digest. | Digest evidence. |
| OBS-009 | Dashboard provisioning from code passes. | Provisioning log. |
| OBS-010 | Dashboard drift detection catches manual change. | Drift report. |
| OBS-011 | Trace propagation carries all required IDs. | Trace sample with redacted fields. |
| OBS-012 | Safe-mode alert tone contains no persona/yandere/punishment wording. | Alert text test. |
| OBS-013 | Sub-agent file-output missing alert fires. | Synthetic sub-agent failure evidence. |
| OBS-014 | Backup failure alert fires and links to incident evidence. | Backup alert evidence. |
| OBS-015 | Monthly observability review artifact generated. | Review artifact. |

### 13.2 Drill Integration

Observability drills must be tied to the Incident Response drill matrix:

| Incident Drill | Observability Validation |
|---|---|
| Key compromise drill | Secret access, break-glass, redaction, Discord + Gotify routing. |
| Safe-word failure drill | Safe-word bypass alert, persona suspension, incident evidence folder. |
| DB restore drill | Backup freshness, restore drill metric, closure summary. |
| Loop runaway drill | Loop guardian metric, SEV1/SEV2 alert, dashboard visibility. |
| Sub-agent boundary drill | File-output missing and compliance metric alerts. |
| Cost spike drill | FinOps anomaly alert and digest/Discord routing. |

## 14. Monthly Observability Review

A monthly observability review must create a markdown artifact under `evidence/observability/<YYYY-MM>-review.md` with:

| Section | Required Content |
|---|---|
| Alert volume | Count by severity and route. |
| Noise review | Alerts with low actionability and proposed threshold changes. |
| Missed incident review | Incidents detected outside alerting. |
| Dashboard drift | Dashboard-as-code parity check. |
| Redaction status | Redaction failures and tests. |
| Sentry scrubber status | Synthetic scrubber test result. |
| Cost anomalies | LLM/API/storage spend trends. |
| Backup/restore status | Backup freshness and restore drill status. |
| Safe-mode/persona alerts | Safe-mode, safe-word, drift, yandere intensity controls. |
| Action items | Owner, due date, evidence path. |

## 15. Implementation Requirements

| Requirement | Control |
|---|---|
| OBS-REQ-001 | Prometheus configuration must scrape only Tailscale-internal targets. |
| OBS-REQ-002 | Grafana must be reachable only through Tailscale. |
| OBS-REQ-003 | All Grafana dashboards must be provisioned from code. |
| OBS-REQ-004 | Loki labels must follow the bounded label list in this specification. |
| OBS-REQ-005 | Sentry must run with `send_default_pii=false`. |
| OBS-REQ-006 | Sentry must use `before_send` scrubber and must drop unsafe events. |
| OBS-REQ-007 | Alert templates must use neutral incident-command language. |
| OBS-REQ-008 | Persona/yandere/punishment language must be blocked from alerts. |
| OBS-REQ-009 | SEV0/SEV1 alerts must route to Discord + Gotify urgent. |
| OBS-REQ-010 | SEV2 alerts must route to Discord. |
| OBS-REQ-011 | SEV3 alerts must enter digest. |
| OBS-REQ-012 | SEV4 alerts must enter governance cycle. |
| OBS-REQ-013 | Prometheus labels must not contain high-cardinality IDs. |
| OBS-REQ-014 | All traces must propagate `trace_id`, `request_id`, `task_id`, `loop_id`, `subagent_task_id`, `incident_id`, and `evidence_id` when applicable. |
| OBS-REQ-015 | Observability-reader must never receive raw Critical payloads. |
| OBS-REQ-016 | Safe-mode must restrict sensitive recall, surveillance confrontation, and persona escalation alerts. |
| OBS-REQ-017 | Every SEV0-SEV2 alert must link to an evidence path or create one. |
| OBS-REQ-018 | Monthly observability review must be performed and stored as evidence. |
| OBS-REQ-019 | Alert silences must include owner, reason, expiry, alert scope, and evidence link. |
| OBS-REQ-020 | SEV0 alert silences must be forbidden. |

## 16. Unresolved Assumptions and Backlog

| ID | Assumption or Gap | Owner | Impact | Follow-up Document | Trigger |
|---|---|---|---|---|---|
| OBS-BG-001 | Final SLO/SLA/error-budget thresholds are not yet formally approved. | Faiz + Guinevere | Alert thresholds remain interim. | `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Before production readiness claim. |
| OBS-BG-002 | Full FastAPI OpenAPI route inventory is not yet canonical. | Guinevere | Endpoint grouping may need update. | API Contract OpenAPI Spec | Before API implementation. |
| OBS-BG-003 | Grafana dashboard JSON/Terraform files do not yet exist. | Guinevere | Dashboard-as-code control pending implementation. | Deployment / Observability implementation plan | Before runtime deployment. |
| OBS-BG-004 | Alertmanager concrete YAML is not yet generated. | Guinevere | Routing remains specification-only. | Observability implementation plan | Before live alerting. |
| OBS-BG-005 | Sentry scrubber code is not yet implemented. | Guinevere | PII protection pending runtime code. | Runtime implementation plan | Before Sentry enablement. |
| OBS-BG-006 | Cost anomaly thresholds require observed baseline. | Faiz + Guinevere | Initial cost alerts may need tuning. | Cost / FinOps Model | After first billing cycle. |

## Appendix A — Metrics Catalog

| Metric | Component | Type | Labels | Data Class | Alertable |
|---|---|---|---|---|---|
| `guinevere_mood_state` | persona | Gauge | `mood` | Internal aggregate | No by itself |
| `guinevere_mommy_score` | persona | Gauge | none | Internal aggregate | No |
| `guinevere_punishment_level` | persona | Gauge | `level` | Restricted aggregate | Yes when unsafe state |
| `guinevere_yandere_intensity` | persona | Gauge | `level` | Restricted aggregate | Yes |
| `guinevere_reward_streak` | persona | Gauge | none | Internal aggregate | No |
| `guinevere_violation_count_total` | persona | Counter | `violation_type` | Restricted aggregate | Trend only |
| `guinevere_safe_mode_state` | safety | Gauge | `state` | Restricted aggregate | Yes |
| `guinevere_drift_score` | safety | Gauge | `category` | Restricted aggregate | Yes |
| `guinevere_loop_state` | loop | Gauge | `phase`, `status` | Internal | Yes |
| `guinevere_subagent_compliance_score` | subagent | Gauge | `category` | Internal | Yes |
| `guinevere_llm_cost_usd_total` | llm | Counter | `model`, `purpose` | Confidential aggregate | Yes |
| `guinevere_llm_latency_seconds` | llm | Histogram | `model`, `provider`, `status` | Internal | Yes |
| `guinevere_surveillance_event_rate` | surveillance | Gauge | `source` | Restricted aggregate | Yes |

## Appendix B — Alert Rules Catalog

| Rule | Severity | Route | Evidence Required |
|---|---|---|---|
| `GuinevereSafeWordBypassDetected` | SEV0 | Discord + Gotify urgent | Yes |
| `GuineverePublicIngressDetected` | SEV0 | Discord + Gotify urgent | Yes |
| `GuinevereLogRedactionFailure` | SEV1 | Discord + Gotify urgent | Yes |
| `GuinevereSecretAccessOutsideStartup` | SEV1 | Discord + Gotify urgent | Yes |
| `GuinevereServiceDown` | SEV1/SEV2 | Discord + Gotify urgent for SEV1; Discord for SEV2 | Yes for SEV1/SEV2 |
| `GuinevereSubagentFileOutputMissing` | SEV2 | Discord | Yes |
| `GuinevereLLMCostSpike` | SEV2/SEV3 | Discord or digest | Yes for SEV2 |
| `GuinevereRestoreDrillOverdue` | SEV3 | Digest | Review artifact |
| `GuinevereDashboardProvisioningDrift` | SEV4 | Governance cycle | Drift report |

## Appendix C — Log Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `timestamp` | string | Yes | RFC3339. |
| `level` | string | Yes | Controlled enum. |
| `service` | string | Yes | Controlled enum. |
| `component` | string | Yes | Controlled enum. |
| `event_type` | string | Yes | Controlled taxonomy. |
| `data_class` | string | Yes | Highest class touched. |
| `trace_id` | string | Conditional | Field only. |
| `request_id` | string | Conditional | Field only. |
| `task_id` | string | Conditional | Field only. |
| `loop_id` | string | Conditional | Field only. |
| `subagent_task_id` | string | Conditional | Field only. |
| `incident_id` | string | Conditional | Field only. |
| `evidence_id` | string | Conditional | Field only. |
| `redaction_status` | string | Yes | Controlled enum. |

## Appendix D — Loki Labels

| Label | Required | Cardinality |
|---|---|---|
| `service` | Yes | Low |
| `component` | Yes | Low |
| `environment` | Yes | Low |
| `level` | Yes | Low |
| `event_category` | Yes | Low |
| `data_class` | Yes | Low |

## Appendix E — Dashboard Catalog

| Dashboard | File Path Pattern | Owner | Review Cadence |
|---|---|---|---|
| `guinevere-overview` | `monitoring/grafana/dashboards/guinevere-overview.json` | Guinevere | Monthly |
| `guinevere-infrastructure` | `monitoring/grafana/dashboards/guinevere-infrastructure.json` | Guinevere | Monthly |
| `guinevere-api-runtime` | `monitoring/grafana/dashboards/guinevere-api-runtime.json` | Guinevere | Monthly |
| `guinevere-agent-loop` | `monitoring/grafana/dashboards/guinevere-agent-loop.json` | Guinevere | Monthly |
| `guinevere-subagents` | `monitoring/grafana/dashboards/guinevere-subagents.json` | Guinevere | Monthly |
| `guinevere-llm-cost-latency` | `monitoring/grafana/dashboards/guinevere-llm-cost-latency.json` | Guinevere | Monthly |
| `guinevere-persona-safety` | `monitoring/grafana/dashboards/guinevere-persona-safety.json` | Guinevere | Monthly |
| `guinevere-backup-dr` | `monitoring/grafana/dashboards/guinevere-backup-dr.json` | Guinevere | Monthly |

## Appendix F — Trace Schema

| Field | Required | Propagation Method |
|---|---|---|
| `trace_id` | Yes | W3C trace context or generated internal ID. |
| `request_id` | Yes for API | Header and log field. |
| `task_id` | Yes for tasks | Internal task context. |
| `loop_id` | Yes for loops | Loop context. |
| `subagent_task_id` | Yes for sub-agents | Sub-agent task context. |
| `incident_id` | Yes for incident work | Incident context. |
| `evidence_id` | Yes for evidence writes | Evidence manifest context. |

## Appendix G — Sentry Configuration

Required configuration controls:

| Control | Requirement |
|---|---|
| PII default | `send_default_pii=false` |
| Scrubber | `before_send` must remove secrets, prompts, safe-word content, surveillance raw payloads, intimate data, financial identifiers, client data. |
| Drop behavior | Unsafe event must be dropped or reduced to metadata-only. |
| Tags | Low-cardinality only. |
| Breadcrumbs | Redacted. |
| Traces | Sampled and scrubbed. |

## Appendix H — Policy-Control Test Matrix

| Test ID | Control | Pass Condition |
|---|---|---|
| OBS-T-001 | No high-cardinality Prometheus labels | Static rule test passes. |
| OBS-T-002 | No raw Critical data in logs | Redaction test passes. |
| OBS-T-003 | Discord SEV0 route | Synthetic SEV0 delivered. |
| OBS-T-004 | Gotify SEV0 route | Synthetic SEV0 delivered. |
| OBS-T-005 | Sentry scrubber | Unsafe event dropped or redacted. |
| OBS-T-006 | Dashboard-as-code | Provisioning from repository passes. |
| OBS-T-007 | Trace propagation | All seven correlation IDs present when applicable. |
| OBS-T-008 | Persona alert suspension | Alert text contains zero persona/yandere/punishment framing. |
| OBS-T-009 | Safe-mode metric | Safe-mode transition visible without raw safe-word content. |
| OBS-T-010 | Monthly review | Evidence artifact exists. |

## Appendix I — Monthly Review Checklist

| Item | Required Result |
|---|---|
| Alert volume reviewed | Counts by severity and route recorded. |
| Missed incidents reviewed | Any manual incident without alert documented. |
| Alert noise reviewed | Noisy alerts tuned or justified. |
| Dashboard drift checked | Dashboard-as-code parity confirmed. |
| Redaction tested | Secrets/safe-word/intimate/surveillance redaction passed. |
| Sentry scrubber tested | Synthetic event scrubbed or dropped. |
| Cost anomalies reviewed | LLM/API/storage trends reviewed. |
| Backup alerts reviewed | Backup freshness and restore drill status verified. |
| Persona safety alerts reviewed | Safe-mode, drift, yandere intensity, forbidden pattern metrics reviewed. |
| Action tracker updated | Owner and due date recorded for every finding. |

## Appendix J — Review Record

| Field | Value |
|---|---|
| Reviewer | Faiz (Owner) |
| Review Date | 2026-05-30 |
| Decision | Accepted |
| Notes | Approved as normative observability and alerting specification under ADR-017/ADR-018 and incident governance docs. Alert tone must remain neutral incident-command. Persona/yandere/punishment framing is suspended for all alerts. Dashboard-as-code, low-cardinality metrics, trace propagation, Sentry PII scrubbing, and monthly observability review are mandatory. |

## Appendix K — Next Recommended Document

**Recommended next document:** `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md`

Reason: this specification defines telemetry, alert routing, dashboards, and interim thresholds, but production-grade alert quality requires explicit SLOs, SLIs, error budgets, burn-rate policies, and objective-based alert thresholds. Without the SLO/SLA/Error Budget Spec, Guinevere can detect symptoms but cannot fully judge acceptable reliability tradeoffs, alert fatigue, error-budget burn, and release gating.

---

**End of Guinevere Observability & Alerting Specification v1.0**

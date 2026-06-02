# Observability & Alerting — Surface Map Report

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
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines all runtime services, endpoints, storage, and infrastructure surfaces. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Defines access/classification/safe-mode restrictions per surface. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines classification, retention, and audit requirements per data store. |
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Defines severity mapping, drill matrix, and incident evidence duties. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines loop states, phases, sub-agents, and loop guardian as observability surfaces. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines safe-mode, drift, yandere intensity, and forbidden-pattern surfaces. |
| `research-reports/2026-05-30-observability-source-map.md` | Authority chain, constraints, and metric gaps for this report. |

---

## 1. Purpose

This report catalogs every concrete runtime surface in Project Guinevere that produces or consumes observability data. For each surface, this report defines:

- Metrics that must be collected.
- Logs that must be shipped.
- Traces that must be correlated.
- Alerts that must fire.
- Dashboard panels that must be built.
- Severity mapping.
- Data classification restrictions.
- Label/tag conventions.
- Retention requirements.
- Validation test requirements.

The report serves as direct input for the final `Guinevere_Observability_AlertingSpec_v1.0.md`. Every surface listed here must have a corresponding specification section.

---

## 2. Surface Catalog

### 2.1 systemd Services

| Surface | Service Unit | Systemd Status Available | Systemd Logs Available |
|---|---|---|---|
| Guinevere Core | `guinevere-core.service` | Yes | Yes (journald) |
| Surveillance | `guinevere-surveillance.service` | Yes | Yes (journald) |
| Scheduler | `guinevere-scheduler.service` | Yes | Yes (journald) |
| Windows Sync | `guinevere-windows-sync.service` | Yes | Yes (journald) |
| Loop Manager | `guinevere-loops.service` | Yes | Yes (journald) |
| Docker | `docker.service` | Yes | Yes (journald) |
| Caddy | `caddy.service` | Yes | Yes (journald) |
| Tailscale | `tailscaled.service` | Yes | Yes (journald) |

**Metrics:**

- `node_systemd_unit_state{name="guinevere-*", state="active|failed|inactive"}` — from node_exporter systemd collector.
- `guinevere_service_restart_count{service}` — counter per service.
- `guinevere_service_uptime_seconds{service}` — gauge.

**Logs:**

- Application logs: JSON structured → Loki via Promtail.
- System logs: journald → Loki via Promtail.
- Log fields: timestamp, level, service, correlation_id, message, metadata.

**Traces:**

- Trace IDs: trace_id, request_id, task_id, loop_id, subagent_task_id, incident_id, evidence_id must propagate through service boundaries.

**Alerts:**

- `UnitIsDown(guinevere-*.service)` → SEV2 (partial outage) to SEV1 (core service).
- `RestartFlapping(guinevere-*.service)` → SEV2.

**Dashboard Panels:**

- Service health overview panel (states per unit).
- Uptime chart per service.
- Restart event log.

**Data-Class Restrictions:**

- systemd status/log metadata allowed for `observability-reader`.
- Logs must exclude plaintext secrets, raw intimate, raw safe-word beyond event class, raw surveillance when hash/summary is enough.

**Labels/Tags:**

- `service="guinevere-core"`
- `service="guinevere-surveillance"`
- etc.

**Retention:**

- Logs: Confidential → Critical, 90-day default Loki retention.
- Audit: 1 year default.

**Validation Tests:**

- Service restart triggers alert.
- Service failure triggers correct severity alert.

---

### 2.2 FastAPI Endpoints

| Surface | Endpoint | Classification | Allowed Principal |
|---|---|---|---|
| Internal API | `guinevere.internal:8001/internal/*` | Varies | `guinevere_core` |
| Surveillance (Android) | `:8000/surveillance/android/*` | Restricted → Critical | `surveillance-ingestor` |
| Surveillance (Windows WS) | `:8000/surveillance/windows/ws` | Restricted → Critical | `surveillance-ingestor` |
| Health | `:8000/health` | Internal | `observability-reader` |
| Admin | `:8001/admin/*` | Critical | Samm, `break-glass-operator` |

**Metrics:**

- `fastapi_request_duration_seconds{endpoint, method, status}` — histogram.
- `fastapi_requests_total{endpoint, method, status}` — counter.
- `fastapi_requests_in_progress{endpoint, method}` — gauge.

**Logs:**

- Request/response structured JSON: method, path, status, duration, principal, trace_id.
- Rejection logs for failed auth/classification/safe-mode gates.

**Traces:**

- Every request must carry trace_id, request_id.
- Surveillance payloads must propagate device_id and source HMAC.

**Alerts:**

- `5xx error rate > 1% per endpoint` → SEV3.
- `5xx error rate > 5% per endpoint` → SEV2.
- `Health check failure` → SEV2.
- `Surveillance endpoint 0 requests for 15 min` → SEV3 (ingestion stopped).

**Dashboard Panels:**

- Request rate per endpoint.
- Error rate breakdown by status/endpoint.
- Latency p50/p95/p99 per endpoint.
- Active requests gauge.

**Data-Class Restrictions:**

- Raw payload must never appear in metric labels.
- Surveillance payload logs must be minimized (summarized/hashed for observability).
- Classification label in metadata only; no Critical raw data in logs.

**Labels/Tags:**

- `endpoint="/surveillance/android/activity"`
- `method="POST"`
- `status="200"`

**Retention:**

- Request logs: 30 days default.

**Validation Tests:**

- Health endpoint accessible to `observability-reader`.
- Surveillance endpoint rejects non-ingestor auth.
- 5xx alerts fire correctly.

---

### 2.3 Autonomous Loop Phases

| Surface | Phase | State Machine | Persistence |
|---|---|---|---|
| SDLC Loop | 1-7 phases `{Research, Plan, Delegate, Execute, Validate, Update, Evidence}` | INIT → PHASE_* → COMPLETE/PAUSED/BLOCKED/RETRY | PostgreSQL + Redis |
| Proactive Loop | Various | Same model | PostgreSQL |
| Loop Guardian | 30s/5min/60s checks | State monitoring | Redis |

**Metrics:**

- `guinevere_loop_state{phase, state}` — gauge per loop.
- `guinevere_loop_duration_seconds{task_type, project}` — histogram.
- `guinevere_phase_duration_seconds{phase}` — histogram.
- `guinevere_todo_completion_rate{loop_id}` — gauge.
- `guinevere_todo_enforcer_yanks{loop_id}` — counter.
- `guinevere_error_rate{error_type}` — counter.
- `guinevere_loops_parallel` — gauge.

**Logs:**

- Loop state transitions: timestamp, loop_id, phase, old_state, new_state, evidence_path.
- Phase completion events: timestamp, loop_id, phase, todos_cleared, duration.
- Guardian yank events: agent_id, todo_id, idle_duration.

**Traces:**

- Every loop carries loop_id.
- Every sub-task carries task_id, subagent_task_id.
- Incident blocks carry incident_id, evidence_id.

**Alerts:**

- `Loop stuck in phase > max_expected_duration` → SEV3.
- `Loop state BLOCKED > 1 hour` → SEV3.
- `Loop state RESUMED after >24h in PAUSED` → SEV3.
- `Loop guardian idle yank rate > 10/hour` → SEV4 (governance).

**Dashboard Panels:**

- Active loops overview (states per loop).
- Phase duration distribution histogram.
- TODO completion rate per loop.
- Guardian yank rate time series.
- Error rate by type.

**Data-Class Restrictions:**

- Loop state metadata is Internal → Confidential if task contains sensitive data.
- Evidence paths in logs: Restricted → Critical if evidence contains sensitive data.

**Labels/Tags:**

- `phase="1-research"`
- `state="running"`
- `project="budgezen"`

**Retention:**

- Loop state logs: 90 days.
- Loop completion records: Long-term curated (PostgreSQL loop_instances table).

**Validation Tests:**

- Loop stuck alert fires after configured timeout.
- Phase duration histogram records correctly.
- Guardian metrics visible in Grafana.

---

### 2.4 Sub-Agents

| Surface | Agent Type | LLM | Task Scope |
|---|---|---|---|
| Research sub-agent | `internal-research`, `external-research` | DeepSeek V4 Flash | Parallel research tasks |
| Implementation sub-agent | `code`, `visual`, `logic`, `data-infra`, `integration`, `testing` | DeepSeek V4 Flash | Parallel execution tasks |
| Validation/audit sub-agent | `validation-agent`, `audit-agent` | DeepSeek V4 Flash | Post-execution validation |

**Metrics:**

- `guinevere_subagent_performance{agent_type}` — histogram (latency, success_rate).
- `guinevere_subagent_task_total{agent_type, status}` — counter.
- `guinevere_sub_agents_active` — gauge.

**Logs:**

- Sub-agent spawn/kill events: timestamp, agent_type, task_id, parent_loop_id.
- Task completion: task_id, status, duration, evidence_path.
- Enforcement events: yank, kill, respawn.

**Traces:**

- subagent_task_id must propagate from parent loop task.
- All sub-agent tool calls must carry task_id.

**Alerts:**

- `Sub-agent success rate < 80% in 1 hour` → SEV3.
- `Sub-agent critical data access attempt` → SEV2 (security).

**Dashboard Panels:**

- Active sub-agents per type.
- Task completion rate per agent type.
- Success/failure rate trend.

**Data-Class Restrictions:**

- Sub-agents must not receive raw Critical data by default.
- Sub-agent output must be file-based; logs must not contain raw sub-agent tool payloads.

**Labels/Tags:**

- `agent_type="research"`
- `status="success|fail"`

**Retention:**

- Sub-agent logs: 30 days.

**Validation Tests:**

- Sub-agent spawn triggers metric counter.
- Sub-agent failure creates audit-compliant log.

---

### 2.5 LLM / 9Router

| Surface | Model | Provider | Context Window |
|---|---|---|---|
| Core Reasoning | GPT-5.5 | 9Router | 1M |
| Sub-agent LLM | DeepSeek V4 Flash | 9Router | 1M |
| Embedding | 9Router-compatible | 9Router | N/A |

**Metrics:**

- `guinevere_llm_latency_seconds{model, use_case}` — histogram.
- `guinevere_api_cost_total{provider, model}` — counter.
- `guinevere_token_usage{model, loop}` — counter (input, output, total).
- `guinevere_llm_error_total{model, error_type}` — counter.
- `guinevere_llm_queue_wait_seconds{model}` — histogram (9Router queue depth).

**Logs:**

- LLM request/response metadata: model, tokens, duration, error_code, trace_id.
- Prompt/response content must NOT be logged by default (contains sensitive data).

**Traces:**

- 9Router requests should propagate trace_id for end-to-end cost attribution.

**Alerts:**

- `LLM latency p99 > 30s for 5 min` → SEV3.
- `LLM error rate > 5% in 15 min` → SEV3.
- `9Router outage (all requests failing)` → SEV1.
- `Daily LLM cost > threshold` → SEV3.
- `Model fallback triggered (GPT-5.5 unavailable)` → SEV3.

**Dashboard Panels:**

- LLM latency p50/p95/p99 per model.
- Token usage per model per loop.
- Cost per provider per day.
- Error rate time series.
- 9Router queue wait time.

**Data-Class Restrictions:**

- Metric labels must not contain prompts, responses, or any user data.
- `model`, `use_case`, `error_type` labels must be bounded low-cardinality.

**Labels/Tags:**

- `model="gpt-5.5"`
- `use_case="core-reasoning"`
- `provider="9router"`

**Retention:**

- Cost metrics: Long-term (7 years per DataGovernance financial retention).
- LLM performance metrics: 180 days.

**Validation Tests:**

- LLM cost alerts fire correctly.
- Token usage metrics match 9Router billing data.

---

### 2.6 PostgreSQL / PgBouncer

| Surface | Component | Port | Exporter Available |
|---|---|---|---|
| PostgreSQL 16 + pgvector + TimescaleDB | Database server | `postgres.internal:5432` | postgres_exporter |
| PgBouncer | Connection pool | PgBouncer | postgres_exporter |

**Metrics:**

- `pg_stat_database{datname}` — connections, deadlocks, cache hit ratio, bloat.
- `pg_replication_lag` — replica lag gauge.
- `pg_stat_activity_count{state}` — active/idle/waiting connections.
- `pg_stat_bgwriter_buffers_*` — write performance.
- `pg_database_size_bytes{datname}` — size gauge.
- `pgbouncer_pools_client_active_connections{pool}` — pool utilization.
- `pgbouncer_requests_queued` — queue depth.

**Logs:**

- PostgreSQL error logs → Loki via Promtail.
- Slow query logs (configurable threshold).
- Audit log (from `system.audit_trail` table): Restricted → Critical, metadata only for observability.

**Traces:**

- query_id or session_id for correlating slow queries to request_id.

**Alerts:**

- `PostgreSQL connection count > 80% max` → SEV3.
- `PostgreSQL down` → SEV2 (core dependency).
- `Replication lag > 1 min` → SEV3.
- `Deadlock rate > 0` → SEV3.
- `Cache hit ratio < 95%` → SEV4.

**Dashboard Panels:**

- Connection pool utilization.
- Cache hit ratio.
- Active/idle/waiting connections.
- Slow query list.
- Database size growth.
- PgBouncer pool status.

**Data-Class Restrictions:**

- `db_observability_r` role gets only system/metrics/redacted audit views.
- No raw payload, secrets, Critical columns for `observability-reader`.
- Classification per DataGovernance matrix.

**Labels/Tags:**

- `datname="guinevere"`
- `state="active"`

**Retention:**

- PG metrics: as per Prometheus retention.
- Slow query logs: 30 days.

**Validation Tests:**

- Connection utilization alert fires correctly.
- DB down alert fires.
- Observability-reader denied raw payload access.

---

### 2.7 Redis DB0–DB5

| Surface | Purpose | Classification | TTL |
|---|---|---|---|
| DB0 Task Queue | SDLC jobs | Internal → Restricted | Per task |
| DB1 LLM Cache | LLM response cache | Internal | 1 hour |
| DB2 Surveillance Buffer | Surveillance data buffer | Restricted → Critical | 5 min |
| DB3 Session State | Session state | Confidential → Critical | 24 hours |
| DB4 Pub/Sub | Component messaging | Internal → Restricted | N/A |
| DB5 Rate Limit | API rate limiting | Internal | 1 min |

**Metrics:**

- `redis_db_keys{db}` — key count gauge per DB.
- `redis_memory_used_bytes{db}` — memory gauge per DB.
- `redis_connected_clients` — client count gauge.
- `redis_hit_rate{db}` — cache hit ratio per DB.
- `redis_expired_keys_total` — TTL expiry counter.
- `redis_replication_lag` — replica lag (if applicable).

**Logs:**

- Redis error logs → Loki via Promtail.
- ACL violation events.

**Traces:**

- task_id correlation in DB0 task queue keys.

**Alerts:**

- `Redis down` → SEV2 (core dependency).
- `Redis memory > 80% allocated` → SEV3.
- `DB2 surveillance buffer not consumed > 5 min` → SEV3.
- `Redis ACL violation detected` → SEV2.

**Dashboard Panels:**

- Key count per DB.
- Memory usage per DB.
- Cache hit rate per DB.
- Surveillance buffer processing latency.

**Data-Class Restrictions:**

- Critical data must not be durably stored in Redis.
- DB2 surveillance buffer: Restricted → Critical, 5 min TTL.
- Metric labels must not contain key prefixes that reveal sensitive bucket names.

**Labels/Tags:**

- `db="0"` through `db="5"`

**Retention:**

- Keycount/memory metrics: standard Prometheus retention.
- Surveillance buffer: 5 min; no logging of raw buffer contents.

**Validation Tests:**

- Redis down alert fires correctly.
- DB2 TTL enforced.
- ACL violation creates audit event.

---

### 2.8 Surveillance Ingestion

| Surface | Source | Data Flow | Classification |
|---|---|---|---|
| Android activity | Tasker | POST → Redis DB2 → Processor → TimescaleDB | Restricted → Critical |
| Android location | Tasker | POST → Redis DB2 → Processor → TimescaleDB | Restricted → Critical |
| Android notification | Tasker + AutoNotification | POST → Redis DB2 → Processor → TimescaleDB | Restricted → Critical |
| Android call | Tasker | POST → Redis DB2 → Processor → TimescaleDB | Restricted |
| Android clipboard | Tasker + AutoInput | POST → Redis DB2 → Processor; secret scanner mandatory | Critical |
| Android camera | Tasker | POST encrypted image → object storage | Critical |
| Windows data | Windows daemon | WebSocket → Redis DB2 → Processor → TimescaleDB | Restricted → Critical |

**Metrics:**

- `guinevere_surveillance_events_total{source, type}` — counter.
- `guinevere_surveillance_ingestion_rate{source}` — gauge (events/sec).
- `guinevere_surveillance_processing_latency_seconds{source}` — histogram.
- `guinevere_surveillance_buffer_depth{db}` — gauge (Redis DB2 pending events).

**Logs:**

- Ingestion events: timestamp, source, event_type, processor_status, trace_id.
- Raw payload must NOT appear in logs; use summary/hash only.

**Traces:**

- device_id, source HMAC, trace_id for end-to-end ingestion tracking.

**Alerts:**

- `Surveillance ingestion stopped > 15 min` → SEV3.
- `Clipboard secret scanner triggered` → SEV1 (potential credential leak).
- `Ingestion processing latency > 30s` → SEV3.
- `Camera/audio ingestion anomaly` → SEV3.

**Dashboard Panels:**

- Event rate per source (Android/Windows).
- Processing latency trend.
- Buffer depth over time.
- Top event types.
- Secret scanner trigger count.

**Data-Class Restrictions:**

- Metric labels: source, type — bounded low-cardinality.
- Raw surveillance data in logs: Critical, must be minimized.
- No surveillance data used for persona confrontation in safe-mode.

**Labels/Tags:**

- `source="android"`
- `type="activity"`

**Retention:**

- Ingestion rate metrics: 180 days.
- Raw surveillance: 7-30 days per DataGovernance.
- Processing logs: 30 days.

**Validation Tests:**

- Ingestion stopped alert fires correctly.
- Secret scanner alert fires.
- Processing latency histogram shows data.

---

### 2.9 Memory Injection / pgvector

| Surface | Component | Purpose | Classification |
|---|---|---|---|
| Episodic memory | `memory/episodic.py` | Session recall | Restricted |
| Semantic memory | `memory/semantic.py` | Knowledge base | Confidential |
| Samm Profile | `memory/samm_profile.py` | User profile | Confidential → Critical |
| Memory injection | `memory/injector.py` | Context injection | Highest source class |
| pgvector | PostgreSQL extension | Embedding search | Inherited from source |

**Metrics:**

- `guinevere_memory_injection_tokens` — histogram (tokens per injection).
- `guinevere_memory_search_duration_seconds` — histogram (pgvector search latency).
- `guinevere_injection_count_total` — counter (injection events).
- `guinevere_memory_recall_classification_distribution` — gauge per classification.

**Logs:**

- Injection events: timestamp, source_type, token_count, classification, trace_id.
- Critical recall events: logged with minimal excerpt/hash.

**Traces:**

- trace_id for each injection request.
- memory recall source linked to task_id when task-driven.

**Alerts:**

- `Memory injection contains Critical data > token threshold` → SEV3 (data governance).
- `pgvector search latency p99 > 5s` → SEV4.

**Dashboard Panels:**

- Injection token distribution.
- Search latency per query type.
- Recall count per classification tier.
- Safe-mode vs normal-mode recall rate.

**Data-Class Restrictions:**

- Metric labels: `classification`, `source_type` — bounded.
- Sensitive source identifiers must not appear in metric labels.
- Critical raw recall must be minimized.

**Labels/Tags:**

- `classification="restricted"`
- `source_type="episodic"`

**Retention:**

- Injection logs: 30 days.

**Validation Tests:**

- Critical recall count metric present.
- Safe-mode recall restriction verified in metrics.

---

### 2.10 Persona Safety Runtime

| Surface | Component | Purpose | Classification |
|---|---|---|---|
| Safe word detector | Runtime hook | Hard-stop detection | Critical |
| Distress classifier | Runtime hook | Distress severity | Restricted → Critical |
| Forbidden pattern scanner | Runtime hook | Block/rewrite | Restricted |
| Mood system | `persona/mood.py` | Mood state tracking | Confidential |
| Drift log | `persona/drift.py` | Persona evolution | Restricted → Critical |
| Yandere intensity | State machine | Intensity gating | Confidential |
| Punishment/reward | Plugin | Escalation ladder | Restricted → Critical |

**Metrics:**

- `guinevere_mood_state` — gauge 0-5.
- `guinevere_yandere_intensity` — gauge 0-6.
- `guinevere_punishment_level` — gauge.
- `guinevere_reward_streak` — gauge (reward streak counter).
- `guinevere_safe_mode_state` — gauge (0=normal, 1=safe-word, 2=distress, 3=crisis, 4=incident).
- `guinevere_drift_score` — gauge (persona drift risk score).
- `guinevere_violation_total{violation_type}` — counter.
- `guinevere_forbidden_pattern_blocked_total{pattern_id}` — counter.
- `guinevere_persona_safety_event_total{event_type}` — counter.

**Logs:**

- Safety events: timestamp, event_class, trigger_source, mood/intensity, action, safe_mode_state, trace_id.
- Near-miss (blocked safe-word bypass): logged with minimal event info.
- Must NOT store raw intimate content, raw safe-word text beyond event class.

**Traces:**

- incident_id, evidence_id for safety incidents.

**Alerts:**

- `Safe-word hard stop triggered` → SEV2 (monitoring, not punishment).
- `Forbidden pattern blocked (F-01 through F-15)` → SEV3.
- `Safe word ignored or delayed > 1s` → SEV1 (safety critical).
- `Drift score > critical threshold` → SEV3.
- `Yandere intensity exceeds mood gate` → SEV4.

**Dashboard Panels:**

- Mood state time series.
- Yandere intensity over time.
- Punishment level trend.
- Reward streak tracker.
- Safe-mode state timeline.
- Drift score trend.
- Forbidden pattern blocks by pattern ID.
- Safety event rate per type.

**Data-Class Restrictions:**

- Safe-word metrics/logs: Critical, minimal, non-punitive.
- Yandere intensity: Confidential.
- Drift score: Restricted → Critical when safe-word/distress/intimate/unsafe drift involved.
- No persona flavor, yandere framing, or punishment language in alert content.

**Labels/Tags:**

- `violation_type` — bounded (e.g. "notification", "timeline", "no-screen-detected").
- `pattern_id` — e.g. "F-01", "F-02".
- `event_type` — e.g. "safe-word", "distress", "forbidden-block".

**Retention:**

- Safety logs: Long-term Critical, encrypted, restricted.
- Raw intimate excerpts: minimize; expire/review periodically.
- Safety metrics: 180 days.

**Validation Tests:**

- Safe-word triggers safe_mode_state gauge change.
- Forbidden pattern block increments counter.
- Drift score metric present and visible.
- All persona-flavored alert content prohibited.

---

### 2.11 Access Control / Security Events

| Surface | Component | Classification |
|---|---|---|
| RBAC/ABAC evaluation | Access broker | Confidential → Critical |
| Denied access | Audit log | Restricted → Critical |
| Safe-mode gate | Runtime hook | Restricted |
| Break-glass grant | Emergency access | Critical |

**Metrics:**

- `guinevere_access_denied_total{principal, resource_class}` — counter.
- `guinevere_abac_rule_fired{rule_id}` — counter.
- `guinevere_break_glass_active` — gauge (0/1).
- `guinevere_break_glass_duration_seconds` — gauge.

**Logs:**

- Denied access events: timestamp, principal, resource, classification, purpose, safety_state, trace_id.
- Break-glass grant/start/end: timestamp, principal, duration, scope, evidence_path.
- Safe-mode gate blocks.
- Must not include plaintext secrets, raw intimate/payload.

**Traces:**

- incident_id for break-glass events.

**Alerts:**

- `Access denied to Critical data` → SEV2 (security).
- `Break-glass grant active > 2 hours` → SEV1.
- `Break-glass grant > 4 hours` → SEV0.
- `Safe-mode gate fired on access attempt` → SEV3.
- `Multiple denied access events in 5 min` → SEV3.

**Dashboard Panels:**

- Access denied rate per principal.
- Break-glass active indicator.
- ABAC rule fire distribution.
- Safe-mode gate activations.

**Data-Class Restrictions:**

- Denied access logs: Restricted → Critical.
- Break-glass events: Critical.
- No raw Critical payload in logs.

**Labels/Tags:**

- `principal="sub-agent-researcher"`
- `resource_class="critical"`
- `rule_id="ABAC-011"`

**Retention:**

- Security logs: 1 year default.
- Break-glass logs: Long-term Critical with incident evidence.

**Validation Tests:**

- Access denied counter increments on blocked requests.
- Break-glass alert fires at 2 hours.
- Safe-mode gate blocks and logs correctly.

---

### 2.12 Secrets / Break-Glass

| Surface | Component | Classification |
|---|---|---|
| SOPS-encrypted env | `config/.env.sops` | Critical |
| age private key | `~/.age/key.txt` | Critical |
| Secrets rotation | `secret-rotator` principal | Critical metadata |
| Decryption events | Crypto audit | Critical |

**Metrics:**

- `guinevere_secrets_rotation_total{status}` — counter.
- `guinevere_secrets_rotation_duration_seconds` — histogram.
- `guinevere_secret_access_total{principal}` — counter (for rotated/secrets events, not raw access).

**Logs:**

- Rotation events: timestamp, status, evidence_path, trace_id.
- Secret access events (decrypt, startup): principal, purpose, approved_state.
- Must NOT contain plaintext secrets, key material, raw token values.

**Traces:**

- incident_id for emergency rotation events.

**Alerts:**

- `Secret rotation overdue > 90 days` → SEV3.
- `Secret rotation failed` → SEV3.
- `Emergency rotation triggered` → SEV1.
- `Key/secret access outside startup` → SEV2.

**Dashboard Panels:**

- Rotation success/failure rate.
- Last rotation timestamp per secret type.
- Emergency rotation event log.

**Data-Class Restrictions:**

- Metrics: Critical metadata only; no key material in labels.
- Logs: no plaintext secrets.
- Access control: restricted to `secret-rotator`, `guinevere_core` startup.

**Labels/Tags:**

- `status="success|fail"`
- `principal="secret-rotator"`

**Retention:**

- Rotation logs: 1 year.
- Key access logs: 1 year.

**Validation Tests:**

- Rotation alert fires at threshold.
- Failed rotation increments counter.
- No plaintext secrets in log output.

---

### 2.13 Backup / Disaster Recovery

| Surface | Method | Destination | Classification |
|---|---|---|---|
| PostgreSQL hot backup | WAL streaming | Cloudflare R2 | Restricted → Critical |
| PostgreSQL cold backup | pg_dump + gzip | idcloudhost S3 | Restricted → Critical |
| Redis backup | RDB + AOF | Local + R2 | Confidential → Critical |
| VPS snapshot | hostdata.id snapshot | hostdata.id | Varies |

**Metrics:**

- `guinevere_backup_success_total{type, destination}` — counter.
- `guinevere_backup_duration_seconds{type}` — histogram.
- `guinevere_backup_size_bytes{type, destination}` — gauge.
- `guinevere_backup_age_seconds{type}` — gauge (time since last successful backup).
- `guinevere_restore_validation_success_total{type}` — counter.

**Logs:**

- Backup start/end/completion events: timestamp, type, size, duration, status, evidence_path.
- Restore test events: timestamp, type, status, integrity_check.
- Must not contain decrypted backup contents.

**Traces:**

- incident_id for restore events.

**Alerts:**

- `Backup failure (any type)` → SEV2.
- `No valid PostgreSQL backup > 24h` → SEV1.
- `Restore validation failure` → SEV1.
- `Backup size anomaly (significantly smaller/larger)` → SEV3.

**Dashboard Panels:**

- Last successful backup per type.
- Backup duration trend.
- Backup size growth.
- Restore validation pass/fail rate.
- Backup age heatmap.

**Data-Class Restrictions:**

- Backup metrics/logs: Restricted → Critical.
- Destination label must not reveal sensitive bucket paths.
- No decrypted contents in observability data.

**Labels/Tags:**

- `type="postgres-cold"`
- `destination="idcloudhost-s3"` (generic, not full path)

**Retention:**

- Backup logs: 1 year.
- Metrics: 180 days.

**Validation Tests:**

- Backup failure alert fires correctly.
- Restore failure triggers SEV1.
- Backup success rate metric increments.

---

### 2.14 Object Storage

| Surface | Bucket/Prefix | Classification | Allowed Principals |
|---|---|---|---|
| Backup storage | `r2://guinevere-backups/` | Restricted → Critical | `backup-operator`, `break-glass-operator` |
| Surveillance media | `r2://guinevere-surveillance/` | Restricted → Critical | `surveillance-ingestor`, `backup-operator` |
| Evidence storage | `r2://guinevere-evidence/` | Highest source class | `guinevere_core`, `readonly-auditor`, `backup-operator` |
| Backup storage (alt) | `s3://idcloudhost-guinevere-backups/` | Restricted → Critical | `backup-operator`, `break-glass-operator` |

**Metrics:**

- `guinevere_object_storage_upload_total{bucket}` — counter.
- `guinevere_object_storage_download_total{bucket}` — counter.
- `guinevere_object_storage_size_bytes{bucket}` — gauge.
- `guinevere_object_storage_lifecycle_action_total{bucket, action}` — counter.

**Logs:**

- Upload/download events: timestamp, bucket, object_metadata, size, principal, trace_id.
- Access events for observability-reader: metadata only; no object content.

**Traces:**

- evidence_id for evidence bucket operations.

**Alerts:**

- `Object storage public ACL detected` → SEV1.
- `Object storage upload failure` → SEV3.
- `Evidence bucket access by non-authorized principal` → SEV2.

**Dashboard Panels:**

- Upload/download rate per bucket.
- Total storage usage per bucket.
- Lifecycle action rate.
- Unauthorized access attempt count.

**Data-Class Restrictions:**

- Bucket label: use generic names (`backups`, `surveillance`, `evidence`), not full bucket paths.
- No object content in metrics/logs.

**Labels/Tags:**

- `bucket="backups"`
- `action="lifecycle-delete"`

**Retention:**

- Object storage operation logs: 90 days.

**Validation Tests:**

- Public ACL alert fires.
- Upload failure counter increments.

---

### 2.15 Tailscale

| Surface | Component | Classification |
|---|---|---|
| Tailscale mesh | `tailscaled.service` | Internal |
| ACL changes | Tailscale policy | Internal |
| Device connections | Tailscale status | Internal |

**Metrics:**

- `tailscaled_mesh_peers` — gauge (connected peer count).
- `tailscaled_relay_duration_seconds` — histogram (direct vs relay connections).

**Logs:**

- Device join/leave events: timestamp, device, tag.
- ACL denial events: timestamp, source, target, action.
- tailscaled journal → Loki.

**Traces:**

- Not applicable (infrastructure network layer).

**Alerts:**

- `Tailscale connection down (all peers lost)` → SEV1.
- `Tailscale ACL change detected` → SEV3 (governance).
- `Tailscale direct connection lost (relay only)` → SEV4.

**Dashboard Panels:**

- Connected peer count.
- Direct vs relay connection ratio.
- ACL change log.

**Data-Class Restrictions:**

- Internal classification.
- Device identifiers: Internal only.

**Labels/Tags:**

- `peer="guinevere-core"`

**Retention:**

- Tailscale logs: 90 days.

**Validation Tests:**

- Tailscale down alert fires.
- ACL change event logged.

---

### 2.16 Loki (Log Aggregation)

| Surface | Component | Purpose | Classification |
|---|---|---|---|
| Promtail | Log shipper | Ship logs to Loki | Metadata at observability level |
| Loki | Log storage | Log query + aggregation | Varies by source log class |
| Grafana Explore | Log query UI | Log exploration | Restricted by ACL |

**Metrics:**

- `loki_request_duration_seconds{endpoint}` — histogram.
- `loki_disk_usage_bytes` — gauge.
- `loki_ingester_rate` — gauge.
- `loki_ingester_errors_total` — counter.

**Logs:**

- Loki operates on logs; its own operational logs must not contain sensitive payload.

**Traces:**

- trace_id correlation between app logs and Loki entries.

**Alerts:**

- `Loki disk usage > 80%` → SEV3.
- `Loki ingester error rate > 1%` → SEV3.
- `Promtail unable to ship logs` → SEV3.

**Dashboard Panels:**

- Log ingestion rate.
- Disk usage.
- Error rate per Loki component.
- Log volume per service.

**Data-Class Restrictions:**

- Logs classified per source (Confidential → Critical).
- Raw payload minimization rules apply to all Loki-stored logs.
- Access control via Grafana ACL and observability-reader scope.

**Labels/Tags:**

- Loki labels: `service`, `level`, `trace_id`, `namespace` — bounded.
- No high-cardinality labels (e.g., unique request paths, user IDs as labels).

**Retention:**

- Per retention policy (90d default, longer for audit).

**Validation Tests:**

- Log volume per service visible in Grafana.
- Promtail ships logs successfully.

---

### 2.17 Grafana Dashboards

| Surface | Purpose | Visibility | Authentication |
|---|---|---|---|
| Incident Response Dashboard | Alert overview, active incidents, severity | `observability-reader`, Samm | Tailscale + Grafana auth |
| System Health Dashboard | Service status, resource usage | `observability-reader`, Samm | Tailscale + Grafana auth |
| LLM Performance Dashboard | Latency, cost, token usage | `observability-reader`, Samm | Tailscale + Grafana auth |
| Safety Dashboard | Mood, yandere, drift, safe-mode state | `observability-reader`, Samm | Tailscale + Grafana auth |
| Surveillance Dashboard | Ingestion rate, processing health | `observability-reader`, Samm | Tailscale + Grafana auth |
| Backup Dashboard | Backup status, restore validation | `observability-reader`, Samm | Tailscale + Grafana auth |
| Persona Dashboard | Violation, punishment, reward, compliance | `observability-reader`, Samm | Tailscale + Grafana auth |
| Loop Dashboard | Active loops, phase durations, enforcer | `observability-reader`, Samm | Tailscale + Grafana auth |

**Configuration:**

- Dashboard-as-code mandatory: all dashboards defined as version-controlled JSON files.
- Folders: per surface (Incident, System, LLM, Safety, Surveillance, Backup, Persona, Loop).
- Provisioning via Grafana provisioner.

**Alerts:**

- Alert rules defined in Grafana, evaluated from Prometheus data.
- Alert severity mapping per DataGovernance classification.

**Access Control:**

- `observability-reader` — read all dashboards, no edit/edit source.
- Samm — full admin.
- All dashboards accessible only via Tailscale.

**Validation Tests:**

- Dashboard-as-code JSON passes schema validation.
- Provisioning loads dashboards correctly.
- All panels have data source configured.

---

### 2.18 Prometheus Metrics

| Surface | Component | Retention |
|---|---|---|
| TSDB | Metric storage | Configurable (default ~30d for 15s scrape interval with limited disk) |
| Alertmanager | Alert evaluation + routing | N/A (alert state in Alertmanager) |

**Metrics (self-monitoring):**

- `prometheus_tsdb_head_series` — series count gauge.
- `prometheus_tsdb_storage_blocks_bytes` — storage usage.
- `prometheus_alertmanager_alerts{state}` — alert state count.

**Alerts:**

- `Prometheus TSDB head series approaching max` → SEV3.
- `Prometheus scrape failure rate > 1%` → SEV3.
- `Alertmanager notification failure` → SEV2.

**High-Cardinality Ban:**

- No high-cardinality labels in Prometheus (user constraint).
- Labels must be bounded: `service`, `phase`, `source`, `model`, `status`, `violation_type`, etc.
- Forbidden: labels derived from raw user input, unrestricted UUIDs, unbounded job/instance names.

**Validation Tests:**

- Prometheus metric labels audited for cardinality.
- Scrape targets all present and healthy.

---

### 2.19 Sentry (Error Tracking)

| Surface | Configuration | Classification |
|---|---|---|
| SDK | `sentry-sdk` Python | Error metadata only |
| `send_default_pii` | `false` | Always |
| `before_send` | Scrubber function | Mandatory |

**Metrics:**

- Error rate via Sentry API → proxied to Prometheus/Grafana.
- Sentry issue count per environment.

**Logs:**

- Error events: timestamp, exception_class, module, trace_id.
- PII fields scrubbed before_send: user_id, IP, request headers, cookies, request_body.
- Database queries, memory content, surveillance data must not be sent to Sentry.

**Traces:**

- Sentry trace_id can supplement Prometheus traces for error correlation.

**Alerts:**

- `Sentry error rate > threshold` → SEV3.
- `Sentry unhandled exception (new issue)` → SEV3.

**Dashboard Panels:**

- Error rate trend.
- Top error classes.
- Issue resolution timeline.

**Data-Class Restrictions:**

- No Critical data in Sentry events.
- No raw intimate, surveillance, or safe-word data.

**Validation Tests:**

- `before_send` scrubber removes PII.
- `send_default_pii=false` confirmed.
- No Critical-class errors leak to Sentry.

---

### 2.20 Discord / Gotify / Email (Alert Channels)

| Surface | Channel | Severity | Format |
|---|---|---|---|
| Discord | `#incident-command` | SEV0-SEV2 (primary) | Neutral incident-command template |
| Gotify | Push notification | SEV0-SEV1 (urgent backup) | Neutral incident-command template |
| Discord | `#alert-digest` | SEV3 | Summary digest |
| Email | Governance summary | SEV4 | Review summary |

**Metrics:**

- `guinevere_alert_sent_total{channel, severity}` — counter.
- `guinevere_alert_notification_failure_total{channel}` — counter.

**Logs:**

- Alert events: timestamp, channel, severity, title, trace_id.
- Alert content template: `[INCIDENT {SEV}] {title}`, Status, Affected systems, Incident type, Data class, Safety state, Current action, Samm action needed, Evidence path, Next update ETA.

**Traces:**

- incident_id, evidence_id in alert body.

**Alerts (meta):**

- `Alert notification failure (Discord down)` → SEV2.
- `Gotify notification failure` → SEV3.
- `Alert format violated (persona/flavor detected)` → SEV4 (governance).

**Dashboard Panels:**

- Alert volume per severity.
- Notification delivery rate per channel.
- Alert format compliance rate.

**Data-Class Restrictions:**

- Alerts must not include plaintext secrets, raw intimate content, raw safe-word text beyond minimal event class, or raw surveillance payload.
- Persona tone, yandere framing, punishment behavior must be suspended.

**Labels/Tags:**

- `channel="discord"`
- `severity="sev1"`

**Retention:**

- Alert logs: 1 year.

**Validation Tests:**

- Discord alert format compliance.
- Gotify urgent message delivered.
- Alert content passes secret/intimate/surveillance scanner.

---

## 3. Surface Index by Component

| Component Category | Surfaces Covered |
|---|---|
| Infrastructure | systemd services (§2.1), Tailscale (§2.15) |
| API | FastAPI endpoints (§2.2) |
| Autonomous Loop | Loop phases (§2.3), Sub-agents (§2.4) |
| LLM | LLM/9Router (§2.5) |
| Storage | PostgreSQL/PgBouncer (§2.6), Redis DB0-DB5 (§2.7), Object storage (§2.14) |
| Ingestion | Surveillance ingestion (§2.8) |
| Memory | Memory injection/pgvector (§2.9) |
| Safety | Persona safety runtime (§2.10) |
| Security | Access control/security events (§2.11), Secrets/break-glass (§2.12) |
| Operations | Backup/DR (§2.13) |
| Observability Infrastructure | Loki (§2.16), Grafana (§2.17), Prometheus (§2.18), Sentry (§2.19) |
| Alert Channels | Discord/Gotify/Email (§2.20) |

---

## 4. Drill Integration Points

Per IncidentResponse drill matrix, each observability surface must support:

| Drill ID | Surface | Observability Requirement |
|---|---|---|
| DRILL-KEY-001 | Secrets/break-glass (§2.12) | Metrics show rotation success, alerts fire on anomaly |
| DRILL-SAFE-001 | Persona safety (§2.10) | Safe-mode state gauge changes, forbidden-pattern alert fires |
| DRILL-DB-001 | PostgreSQL (§2.6) | DB down alert fires, metrics show restoration |
| DRILL-BACKUP-001 | Backup/DR (§2.13) | Backup failure alert fires, restore validation metrics |
| DRILL-LOOP-001 | Loop phases (§2.3) | Loop stuck alert fires, guardian metrics visible |
| DRILL-SUB-001 | Sub-agents (§2.4) | Access denied counter increments |
| DRILL-COST-001 | LLM/9Router (§2.5) | Cost anomaly alert fires, spend freeze metrics |

---

**End of Observability & Alerting Surface Map Report v1.0**

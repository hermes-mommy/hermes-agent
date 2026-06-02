# SLO/SLA/Error Budget - Runtime Surface Map Report

**Document Type:** Research evidence report for Guinevere SLO/SLA/Error Budget Specification  
**Version:** 1.0  
**Status:** Draft - input to Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md  
**Date:** 2026-05-30  
**Owner:** Samm - single-user owner and final authority  
**Executor:** Guinevere de Baroque - autonomous system steward  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  

## Related Documents

| Document | Relationship |
|---|---|
| Guinevere_TechnicalArchitecture_v2.0.md | Defines all runtime services, Redis DBs, PostgreSQL/PgBouncer, systemd units, resource allocation, backup, monitoring stack. |
| Guinevere_Observability_AlertingSpec_v1.0.md | Defines metrics specification, alert catalog, log schema, trace propagation, dashboard catalog, interim SLO targets (S12). |
| Guinevere_AgentLoopSpec_v2.0.md | Defines 7-phase loop, Loop Guardian, TODO Enforcer, sub-agent pool, loop state machine, loop performance metrics (S9). |
| Guinevere_MemorySchema_v2.0.md | Defines memory tables, injection pipeline, pgvector search, encryption layers, memory consolidation. |
| Guinevere_PersonaSafetyPolicy_v1.0.md | Defines safe-word protocol, distress severity, yandere intensity scale, forbidden patterns, drift governance, rollback. |
| Guinevere_PRD_v2.2.md | Defines safe-word enforcement aligned with ADR-002, surveillance endpoints, financial management, monitoring, crash recovery. |
| Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md | Defines SEV0-SEV4 severity matrix, incident runbooks, evidence chain of custody, drill integration. |
| Guinevere_BRD_v2.0.md | Defines business success metrics including 99.9% uptime, code quality >=90% coverage, autonomous task completion. |
| Guinevere_APIIntegration_v2.0.md | Defines all API integrations, LLM cost strategy, Prometheus/Sentry code, SDK configuration, retry/circuit-breaker logic. |
| Guinevere_Persona_Document_v2.0.md | Defines mood system, punishment/reward, yandere intensity, surveillance framing, emotional check-in protocol. |
| adr/ADR-004-primary-llm-model-selection.md | GPT-5.5 via 9Router as primary model; cost/latency must be monitored. |
| adr/ADR-005-llm-router-failover-strategy.md | 9Router only; queue/retry/degrade; no OpenRouter fallback. |
| adr/ADR-017-monitoring-stack-selection.md | Prometheus + Grafana on primary VPS first; dedicated monitoring VPS post-MVP. |
| research-reports/2026-05-30-observability-surface-map.md | Existing 20-surface observability catalog (metrics, logs, traces, alerts per surface). |
---

## 1. Purpose

This report catalogs every concrete measurable runtime surface in Project Guinevere from an SLO/SLA/Error Budget perspective. For each surface, this report defines:

- **Candidate SLI(s)** - what measurable indicator(s) reflect reliability, performance, correctness, or safety.
- **PromQL / Source Metric** - concrete query or metric name that feeds the SLI.
- **Dashboard Panel** - Grafana panel where this SLI must appear.
- **Alert Tie-in** - what alert threshold this SLI supports.
- **Error Budget Applicability** - whether this SLI should consume an error budget (and initial burn-rate guidance).
- **Owner** - who is accountable (Samm, Guinevere, or shared).
- **Caveats** - known limitations, measurement gaps, or data-class restrictions.
- **Evidence** - concrete section/file references from foundation docs.

---

## 2. Surface Map

### 2.1 Guinevere Core Daemon (guinevere-core.service)

| Field | Detail |
| --- | --- |
| **Description** | Hermes Agent daemon - persona engine, Discord, memory, SDLC orchestration. 4GB RAM allocation. systemd auto-restart with 10s delay. |
| **Candidate SLIs** | **Availability SLI**: fraction of time service is up. **Latency SLI**: response time. **Restart SLI**: restart frequency (flapping). |
| **PromQL / Source Metric** | up{job="guinevere-core"} or node_systemd_unit_state{name="guinevere-core.service",state="active"}; guinevere_health_check_state{service="core"} (TA S8.2, OBS S4.4). |
| **Dashboard Panel** | guinevere-overview (service health); guinevere-infrastructure (uptime) (OBS S9.2, Appendix E). |
| **Alert Tie-in** | GuinevereServiceDown SEV1/SEV2 (OBS S8.3, IR S3.1). Restart flapping -> SEV2. |
| **Error Budget Applicability** | **YES** - primary availability budget. BRD S1.3: 99.9% target. OBS S12 interim: >=99.0% monthly. |
| **Owner** | Guinevere (auto-restart + diagnosis); Samm (VPS-level). |
| **Caveats** | Prometheus may miss gap if core down. Single VPS = no redundancy. |
| **Evidence** | TA S3.1 (systemd), TA S8.4 (health 30s), TA S9.2 (RTO<30s), OBS S4.3, BRD S1.3, OBS S12. |

### 2.2 FastAPI Surveillance Receiver

| Field | Detail |
| --- | --- |
| **Description** | FastAPI on :8000 receiving Android/Windows surveillance data. 512MB RAM. Tailscale + JWT auth. HMAC-signed payloads via Tasker. |
| **Candidate SLIs** | **Availability SLI**: health response. **Throughput SLI**: events/min. **Latency SLI**: p95/p99 duration. **Error SLI**: 5xx rate. **Auth SLI**: HMAC rejection rate. |
| **PromQL / Source Metric** | guinevere_http_requests_total{service="surveillance"} / guinevere_http_request_duration_seconds (OBS S4.4); guinevere_surveillance_events_total (OBS S4.10); guinevere_health_check_state (TA S8.4). |
| **Dashboard Panel** | guinevere-api-runtime (req rate, error rate, latency); guinevere-surveillance-ingestion (event rate, auth failures) (OBS S9.2). |
| **Alert Tie-in** | GuinevereSurveillanceIngestionStopped SEV2; GuinevereServiceDown SEV1/SEV2; GuinevereSurveillanceRedactionFailure SEV1 (OBS S8.3). |
| **Error Budget Applicability** | **YES** - separate from core. 5xx>1% or stopped>15min. Redaction failures: zero budget. |
| **Owner** | Guinevere (service mgmt); Samm (VPS-level). |
| **Caveats** | Critical/Restricted data - redaction failures zero-budget (OBS S12). Endpoint-group labels not raw paths (OBS S4.4). |
| **Evidence** | TA S3.1 (systemd), TA S6 (architecture), TA S6.2 (endpoints), OBS S4.4, OBS S4.10, OBS S8.3, APIInt S5 (HMAC). |

### 2.3 Scheduler (guinevere-scheduler.service)

| Field | Detail |
| --- | --- |
| **Description** | APScheduler + daily rituals + cron + proactive tasks. 256MB RAM. Handles daily schedule (07:00,12:00,17:00,21:00,00:00), self-deploy (03:00), proactive detection. |
| **Candidate SLIs** | **Cron Success SLI**: jobs completing without error. **Latency SLI**: jitter. **Proactive Trigger SLI**: loops when conditions met. |
| **PromQL / Source Metric** | guinevere_scheduler_job_duration_seconds{job}, guinevere_scheduler_job_failures_total{job} (proposed); guinevere_backup_last_success_timestamp_seconds (OBS S4.11). |
| **Dashboard Panel** | guinevere-overview (scheduler); guinevere-backup-dr (cron) (OBS S9.2). |
| **Alert Tie-in** | GuinevereBackupFailure SEV1/SEV2 (OBS S8.3); ritual missed -> SEV3; deploy cron fail -> SEV2. |
| **Error Budget Applicability** | **YES** - may share budget with core. Backup cron: tighter RPO. |
| **Owner** | Guinevere (APScheduler). |
| **Caveats** | Single-node - no HA. Missed rituals: log inspection only. Self-deploy at 03:00 - if VPS down, missed. |
| **Evidence** | TA S3.1 (256MB), TA S9.1 (backup), TA S10.2 (deploy cron), AgentLoopSpec S8, S8.2 (rituals). |

### 2.4 Discord Bot (Hermes Native Adapter)

| Field | Detail |
| --- | --- |
| **Description** | Primary UI layer. Hermes Agent native Discord adapter. Message events, slash commands, channel routing. All user interaction via Discord. |
| **Candidate SLIs** | **Gateway Connectivity SLI**: gateway uptime. **Message Latency SLI**: response time. **Delivery SLI**: alert delivery. **Slash Command SLI**: command success. |
| **PromQL / Source Metric** | guinevere_health_check_state{check="discord_gateway"} (TA S8.4); guinevere_alert_sent_total{channel="discord"} / guinevere_alert_notification_failure_total. |
| **Dashboard Panel** | guinevere-overview (gateway status); guinevere-api-runtime (latency) (OBS S9.2). |
| **Alert Tie-in** | GuinevereServiceDown if gateway fails (SEV1/SEV2). Gotify fallback for SEV0/SEV1 (OBS S8.1). |
| **Error Budget Applicability** | **YES** - core availability includes Discord. User-visible if Discord fails. |
| **Owner** | Guinevere (adapter); Samm (token/config). |
| **Caveats** | Adapter hang: UptimeRobot 5min detects. User latency includes LLM generation (2.5). |
| **Evidence** | TA S1.1 (Discord=UI), TA S3.2 (plugins/health.py), TA S8.4 (30s health, 5min UptimeRobot), OBS S11.1, OBS S8.1, PRD S1.2. |

### 2.5 9Router / LLM

| Field | Detail |
| --- | --- |
| **Description** | Sole LLM routing. GPT-5.5 (core, 1M ctx) + DeepSeek V4 Flash (sub-agents). Queue/retry; no OpenRouter (ADR-005). tenacity retry exp backoff. |
| **Candidate SLIs** | **Availability SLI**: non-error response fraction. **Latency SLI**: p50/p95/p99. **Cost SLI**: USD/day. **Context Util SLI**: usage ratio. **Queue Depth SLI**: pending. **Rate Limit SLI**: throttled fraction. |
| **PromQL / Source Metric** | guinevere_llm_requests_total (OBS S4.7); guinevere_llm_latency_seconds (OBS S4.7); guinevere_llm_cost_usd_total (OBS S4.7); guinevere_llm_context_utilization_ratio (OBS S4.7). |
| **Dashboard Panel** | guinevere-llm-cost-latency (latency, tokens, cost, rate limits) (OBS S9.2). |
| **Alert Tie-in** | GuinevereLLMLatencyDegraded SEV3; GuinevereLLMCostSpike SEV2/SEV3 (OBS S8.3); 9Router outage -> SEV1 (IR S7.10). |
| **Error Budget Applicability** | **YES** - separate from core. Direct user-perceived quality. Cost = economic budget. GPT-5.5: Premium (APIInt S2.3). |
| **Owner** | Guinevere (retry/queue/cost); Samm (account/budget). |
| **Caveats** | Prompt/response NOT logged (OBS S4.7). Latency includes 9Router overhead. Cost spikes from loop runaway. |
| **Evidence** | TA S4.1 (models), TA S8.4 (health 60s), OBS S4.7 (metrics), OBS S8.3 (alerts), APIInt S2 (config, retry, costs), ADR-004, ADR-005. |

### 2.6 PostgreSQL 16 + pgvector + TimescaleDB / PgBouncer

| Field | Detail |
|---|---|
| **Description** | Primary data store. PG16 + pgvector + TimescaleDB. PgBouncer pooling. Docker. 4GB RAM. |
| **Candidate SLIs** | **Availability SLI**: DB responding. **Connection Pool SLI**: PgBouncer utilization. **Query Latency SLI**: p50/p95. **Replication Lag SLI**: WAL lag. **Deadlock Rate SLI**: deadlocks/min. **Cache Hit Ratio SLI**: buffer hit rate. |
| **PromQL / Source Metric** | guinevere_postgres_connections_active{role} (OBS S4.9); guinevere_postgres_query_duration_seconds (OBS S4.9); guinevere_pgbouncer_pool_utilization_ratio (OBS S4.9). |
| **Dashboard Panel** | guinevere-database-memory (connections, cache hit, slow queries, PgBouncer) (OBS S9.2). |
| **Alert Tie-in** | GuineverePostgresUnavailable SEV1 (OBS S8.3); connections over 80pct -> SEV3; replication lag >1min -> SEV3; cache hit <95pct -> SEV4. |
| **Error Budget Applicability** | **YES** - separate from core. Critical dependency. RTO<30min, RPO<1hr (TA S9.2). |
| **Owner** | Guinevere (queries, migration, PgBouncer); Samm (VPS disk/backup). |
| **Caveats** | db_observability_r role gets redacted views only. TimescaleDB compression >7 days increases latency. pgvector IVFFlat is approximate. |
| **Evidence** | TA S5.1 (8 schemas), TA S5.4 (PgBouncer users), OBS S4.9 (metrics), OBS S8.3 (alert), TA S8.1 (exporter). |

### 2.7 Redis DB0-DB5

| Field | Detail |
|---|---|
| **Description** | In-memory cache/queue. DB0 (task queue), DB1 (LLM cache, 1hr TTL), DB2 (surveillance buffer, 5min TTL), DB3 (session, 24hr TTL), DB4 (pub/sub), DB5 (rate limiting, 1min TTL). Docker. |
| **Candidate SLIs** | **Availability SLI**: Redis responding. **Memory Pressure SLI**: utilization ratio. **Eviction Rate SLI**: keys evicted/min per DB. **DB2 Processing SLI**: buffer to TimescaleDB latency. |
| **PromQL / Source Metric** | guinevere_redis_memory_utilization_ratio{db} (OBS S4.9); guinevere_redis_key_evictions_total{db} (OBS S4.9); guinevere_surveillance_queue_depth (OBS S4.10) for DB2. |
| **Dashboard Panel** | guinevere-database-memory (key count, memory, cache hit, evictions, buffer depth) (OBS S9.2). |
| **Alert Tie-in** | GuinevereRedisUnavailable SEV2 (OBS S8.3); memory >80pct -> SEV3; DB2 buffer not consumed >5min -> SEV3; ACL violation -> SEV2. |
| **Error Budget Applicability** | **YES** - lower severity than PG. Redis loss replayable from AOF/RDB (RTO<5min, RPO<1hr, TA S9.2). DB2 loss = max 5min data. |
| **Owner** | Guinevere (client mgmt, TTL config). |
| **Caveats** | Critical data NOT durably stored in Redis. DB2 5min TTL - sustained failure = data loss. Single instance (no cluster). |
| **Evidence** | TA S5.5 (DB0-DB5 table), OBS S4.9 (metrics), OBS S8.3 (alert), TA S8.1 (exporter), TA S9.1 (AOF/RDB backup). |

### 2.8 Backup Jobs

| Field | Detail |
|---|---|
| **Description** | Multi-layered: PG WAL streaming (continuous) + cold pg_dump (02:00 daily) to R2 + idcloudhost; Redis RDB/AOF (hourly); VPS snapshots (weekly); surveillance screenshots (real-time). |
| **Candidate SLIs** | **Freshness SLI**: time since last successful backup. **Success Rate SLI**: fraction succeeding. **Duration SLI**: vs expected window. **Size Anomaly SLI**: deviation from rolling avg. **Restore Validation SLI**: drill pass/fail. |
| **PromQL / Source Metric** | guinevere_backup_last_success_timestamp_seconds{backup_type,target} (OBS S4.11); guinevere_backup_duration_seconds{type,target,status} (OBS S4.11); guinevere_backup_size_bytes{type,target} (OBS S4.11); guinevere_restore_drill_failures_total (OBS S4.11). |
| **Dashboard Panel** | guinevere-backup-dr (freshness heatmap, duration, size trend, restore validation) (OBS S9.2, Appendix E). |
| **Alert Tie-in** | GuinevereBackupFailure SEV1/SEV2 (OBS S8.3); no valid PG backup >24h -> SEV1; restore validation failure -> SEV1; GuinevereRestoreDrillOverdue SEV3. |
| **Error Budget Applicability** | **YES** - backup RPO maps to data loss risk. Daily PG + continuous WAL: RPO<1hr (TA S9.2). Separate budget from service availability. |
| **Owner** | Guinevere (automation, cron); Samm (VPS snapshots, provider config). |
| **Caveats** | Depends on object storage availability. Dual backup mitigates single provider. WAL streaming needs continuous PG uptime. Restore drill every 3mo. |
| **Evidence** | TA S9.1 (backup strategy table), TA S9.2 (RTO/RPO matrix), OBS S4.11 (metrics), OBS S8.3 (alerts), IR S7.9, IR S10. |

### 2.9 Observability Stack (Prometheus + Grafana + Loki + Sentry + Exporters + UptimeRobot)

| Field | Detail |
|---|---|
| **Description** | Primary VPS monitoring. Prometheus (15s scrape), Grafana (dashboards, alerting), Loki+Promtail (logs), Sentry (error tracking), node_exporter, postgres_exporter, redis_exporter, UptimeRobot (5min external). 4GB RAM. |
| **Candidate SLIs** | **Scrape Success SLI**: fraction of targets returning. **Dashboard Provisioning SLI**: dashboards matching code source. **Log Redaction SLI**: Critical/Restricted redaction success. **Alert Delivery SLI**: SEV0/SEV1 delivered. |
| **PromQL / Source Metric** | up{job=~guinevere.*} (scrape health); prometheus_tsdb_head_series (cardinality); guinevere_log_redaction_failures_total (OBS S4.12); guinevere_alert_sent_total + notification_failure_total. |
| **Dashboard Panel** | guinevere-overview (scrape status, Loki rate, alert volume). Self-monitoring panels (TSDB, Loki disk) (OBS S9.2). |
| **Alert Tie-in** | GuinevereDashboardProvisioningDrift SEV4; Loki disk >80pct -> SEV3; scrape >1pct fail -> SEV3; GuinevereLogRedactionFailure SEV1 (OBS S8.3). |
| **Error Budget Applicability** | **YES** - meta-layer. Does not directly degrade service, but eliminates SLI visibility. OBS S12: 100pct dashboard-as-code, 100pct redaction, 100pct SEV0/SEV1 delivery. |
| **Owner** | Guinevere (Grafana, Prometheus, Loki); Samm (VPS resources). |
| **Caveats** | Co-located on primary VPS (ADR-017) - VPS failure hides monitoring. UptimeRobot external free tier is gap detection. Prometheus retention limited by 120GB SSD. |
| **Evidence** | TA S8 (monitoring), TA S8.1 (stack), TA S8.2 (10 custom metrics), OBS S4 (metrics spec), OBS S9 (dashboards), OBS S5 (logging), OBS S7 (Sentry), ADR-017. |

### 2.10 Agent Loop (SDLC 7-Phase + Guardian + TODO Enforcer)

| Field | Detail |
|---|---|
| **Description** | Autonomous SDLC loop: Research, Plan and Delegate, Delegate, Execute, Validate and Audit, Update Documents, Setup Evidence. Loop Guardian (30s heartbeat, 5min progress, 60s resource). TODO Enforcer. guinevere-loops.service (512MB). |
| **Candidate SLIs** | **Completion Rate SLI**: fraction completing all 7 phases. **Phase Duration SLI**: time per phase. **TODO Clear Rate SLI**: TODOs cleared/min. **Guardian Yank Rate SLI**: agent yanks/hr. **Validation Pass Rate SLI**: first-pass success. |
| **PromQL / Source Metric** | guinevere_loop_state{phase,status} (OBS S4.5, AgentLoopSpec S9.1); guinevere_loop_phase_duration_seconds{phase} (OBS S4.5); guinevere_loop_validation_failures_total (OBS S4.5); guinevere_loop_evidence_missing_total (OBS S4.5); guinevere_loop_guardian_interventions_total (OBS S4.5). |
| **Dashboard Panel** | guinevere-agent-loop (phase duration, validation/audit failures, evidence missing, guardian interventions, parallel count) (OBS S9.2). |
| **Alert Tie-in** | GuinevereLoopRunaway SEV1 (OBS S8.3); validation failure rate -> SEV3; evidence missing -> SEV3; loop blocked >1hr -> SEV3. |
| **Error Budget Applicability** | **YES** - separate quality budget. Loop failures affect project delivery, not user-facing availability. Evidence completeness: near-zero tolerance per ADR-012. |
| **Owner** | Guinevere (orchestration, Loop Guardian, TODO Enforcer). |
| **Caveats** | Loop state in Redis (active) + PG (permanent). Redis loss may lose active state. LQS computed post-loop (AgentLoopSpec S9.2). ~20 parallel loops max (AgentLoopSpec S6.1). |
| **Evidence** | AgentLoopSpec S1.2 (5 loop types), S2 (7 phases), S4.1 (Guardian), S4.2 (Enforcer), S5.2 (state machine), S6.1 (parallel exec), S9.1 (10 metrics), S9.2 (LQS); TA S3.1 (512MB); OBS S4.5. |

### 2.11 Sub-Agents (Pasukan Mommy)

| Field | Detail |
|---|---|
| **Description** | Spawned parallel workers for research, code, validation, audit, documentation. Use DeepSeek V4 Flash via 9Router. Must output markdown files per OCS/AGENTS.md contract. Parent verifies file output. |
| **Candidate SLIs** | **Success Rate SLI**: fraction of tasks completing without error. **Duration SLI**: time per task. **File Output Compliance SLI**: fraction producing required markdown output files. **Compliance Score SLI**: governance quality score per category. **Retry Rate SLI**: retries/type. |
| **PromQL / Source Metric** | guinevere_subagent_active{category,status} (OBS S4.6); guinevere_subagent_duration_seconds{category,status} (OBS S4.6); guinevere_subagent_file_output_missing_total{category,artifact_type} (OBS S4.6); guinevere_subagent_compliance_score{category} (OBS S4.6); guinevere_subagent_retries_total{category,reason} (OBS S4.6). |
| **Dashboard Panel** | guinevere-subagents (active per category, duration distribution, file-output missing, compliance score, retries) (OBS S9.2, Appendix E). |
| **Alert Tie-in** | GuinevereSubagentFileOutputMissing SEV2 (OBS S8.3); success rate <80pct -> SEV3; critical data access attempt -> SEV2. |
| **Error Budget Applicability** | **YES** - softer than core. Failures slow project delivery, not user availability. File-output compliance: near-zero tolerance per AGENTS.md S2. |
| **Owner** | Guinevere (spawning, parent verification, compliance). |
| **Caveats** | Cannot receive raw Critical data by default (PersonaSafetyPolicy S13.1). File-output depends on MCP filesystem reliability. DeepSeek V4 Flash cost-efficient but may be lower quality. |
| **Evidence** | TA S3.2 (agents/ directory), AgentLoopSpec S3 (all 7 phases use sub-agents), S3.4 (categories: visual-engineering, deep-logic, data-infra, integration, testing), OBS S4.6, OBS S8.3, AGENTS.md S2. |

### 2.12 Persona Safety Runtime (Mood State, Forbidden Patterns, Drift)

| Field | Detail |
|---|---|
| **Description** | Runtime safety hooks inside core daemon: mood engine, punishment/reward, drift log, yandere intensity state machine, forbidden pattern scanner (F-01 to F-15), surveillance-use gate. |
| **Candidate SLIs** | **Punishment Escalation SLI**: level changes/time window. **Yandere Intensity Cap Compliance SLI**: fraction within mood-allowed cap. **Drift Score SLI**: risk score. **Forbidden Pattern Block Rate SLI**: blocks per category. **Near-Miss Rate SLI**: blocked unsafe phrases. |
| **PromQL / Source Metric** | guinevere_mood_state{mood} (OBS S4.8); guinevere_punishment_level{level} (OBS S4.8); guinevere_yandere_intensity{level} (OBS S4.8); guinevere_drift_score{category} (OBS S4.8); guinevere_forbidden_pattern_blocks_total{pattern_id} (OBS S4.8); guinevere_safe_mode_state{state} (OBS S4.8). |
| **Dashboard Panel** | guinevere-persona-safety (mood time series, yandere intensity, punishment level, drift score, forbidden pattern blocks, safe-mode timeline) (OBS S9.2, Appendix E). |
| **Alert Tie-in** | GuinevereYandereIntensitySafeModeViolation SEV1 (OBS S8.3); GuineverePersonaAlertToneViolation SEV1; drift score over threshold -> SEV3; forbidden pattern blocked -> SEV3. |
| **Error Budget Applicability** | **SPECIAL** - safety invariants, NOT availability budget. Forbidden pattern blocks: zero-tolerance near-miss. Drift/yandere: monitoring-only with mandatory review. |
| **Owner** | Guinevere (persona engine, drift log, forbidden pattern scanner). |
| **Caveats** | Mood: dashboard-only, not alertable (OBS S4.8). Yandere Y6 prohibited entirely (PersonaSafetyPolicy S9). Safe-mode always activatable. Raw intimate data NEVER in metrics. Alerts use neutral incident-command tone (OBS S2.2). |
| **Evidence** | PersonaSafetyPolicy S7 (safe-word), S8 (distress D0-D4), S9 (yandere Y0-Y6), S10 (punishment L1-L6), S11 (forbidden patterns F-01 to F-15), S14 (drift); OBS S4.8; OBS S8.3; PersonaDocument S2.2 (moods), S4.2 (ladder), S12 (yandere). |

### 2.13 Safe-Word Enforcement

| Field | Detail |
|---|---|
| **Description** | Global hard-stop mechanism. Detects safe word (exact token + semantic equivalents: stop, pause, too much, serious mode). Immediately activates safe mode - pauses persona, punishment, yandere, surveillance confrontation. Non-punitive minimal logging. |
| **Candidate SLIs** | **Detection Latency SLI**: time from utterance to safe-mode activation (target <1s). **False Negative Rate SLI**: fraction not detected (target 0). **Safe Mode Transition SLI**: fraction successfully transitioning. **Resume Compliance SLI**: resumes waiting for explicit Samm confirmation. |
| **PromQL / Source Metric** | guinevere_safe_mode_state{state} (OBS S4.8); guinevere_safe_word_events_total{outcome} (OBS S4.8); proposed: guinevere_safe_word_detection_latency_seconds histogram; guinevere_safe_word_false_negative_total counter. |
| **Dashboard Panel** | guinevere-persona-safety (safe-mode timeline, safe-word event rate, detection latency histogram, false negative/positive counters) (OBS S9.2). |
| **Alert Tie-in** | GuinevereSafeWordBypassDetected SEV0 (OBS S8.3, PersonaSafetyPolicy S11 F-01); detection latency >1s -> SEV1; safe-word logged as punishment -> SEV0. |
| **Error Budget Applicability** | **ZERO BUDGET** - per OBS S12: 100pct successful hard-stop. Any miss is SEV0. Safety invariant excluded from all availability tradeoffs. |
| **Owner** | Guinevere (detector, safe-mode runtime, non-punitive logging). |
| **Caveats** | Semantic equivalents broad by design (PersonaSafetyPolicy S7.1). Exact tokens deferred to Safe Word Runtime Spec (backlog). Safe-mode not for overriding genuine distress (S8.1 D3-D4). Resume only on explicit Samm confirmation (S7.4). |
| **Evidence** | PersonaSafetyPolicy S7 (protocol: S7.1 trigger, S7.2 actions, S7.3 prohibited, S7.4 resume); PRD S2.4 (aligned with ADR-002); ADR-002; OBS S4.8 (guinevere_safe_word_events_total); OBS S8.3 (bypass alert); OBS S12 (100pct target). |

### 2.14 Distress Detection

| Field | Detail |
|---|---|
| **Description** | Multi-level classifier (D0-D4). Detects hesitation, boundary setting, emotional distress, crisis risk via text + context + surveillance data. Triggers proportional safe-mode escalation. Conservative false-negative posture. |
| **Candidate SLIs** | **Detection Accuracy SLI**: correct D0-D4 classification. **Escalation Correctness SLI**: proportional safe-mode trigger. **False Negative Rate SLI**: missed distress (err on de-escalation). **Response Appropriateness SLI**: no dominance/yandere during D3/D4. |
| **PromQL / Source Metric** | guinevere_distress_events_total{level} (OBS S4.8); guinevere_safe_mode_state{state} (correlated); proposed: guinevere_distress_classification_confidence gauge; guinevere_distress_false_negative_total counter. |
| **Dashboard Panel** | guinevere-persona-safety (distress event rate by level, safe-mode correlation, classification confidence) (OBS S9.2). |
| **Alert Tie-in** | D3/D4 -> automatic safe mode + SEV0 (IR S3.3). Repeated D2 -> SEV2 (PersonaSafetyPolicy S11 F-02). Crisis with dominance framing -> SEV0 (F-14). |
| **Error Budget Applicability** | **ZERO BUDGET** - safety critical. FN leading to unhandled distress: zero tolerance. FP (de-escalation): acceptable. PersonaSafetyPolicy S7.1: err on side of de-escalation. |
| **Owner** | Guinevere (classifier, mood/yandere gating). |
| **Caveats** | Thresholds not yet defined (backlog: define precision/recall target). Current policy prefers conservative (high FP, low FN). Wearable heart rate (post-MVP) would improve detection. Surveillance signals: typo rate, response time, late-night activity (PersonaDocument S11.8). |
| **Evidence** | PersonaSafetyPolicy S8 (D0-D4), S8.2 (crisis language), S9.1 (mandatory downgrade), Appendix C (decision tree), OBS S4.8 (guinevere_distress_events_total), PersonaDocument S11.8 (emotional check-in). |

### 2.15 Surveillance Ingestion Pipeline

| Field | Detail |
|---|---|
| **Description** | End-to-end: Android Tasker (HTTP POST) + Windows daemon (WebSocket) -> FastAPI -> Redis DB2 (5min TTL) -> Processor -> TimescaleDB. HMAC validation, encryption, geofencing. |
| **Candidate SLIs** | **Throughput SLI**: events stored in TimescaleDB per min per source. **End-to-End Latency SLI**: device event to DB persistence. **Buffer Processing Lag SLI**: DB2 oldest event vs current time. **Drop Rate SLI**: events lost. **Redaction Success SLI**: payload redaction before log emission. |
| **PromQL / Source Metric** | guinevere_surveillance_events_total{source,event_type,status} (OBS S4.10); guinevere_surveillance_event_rate{source} (OBS S4.10); guinevere_surveillance_queue_depth{source} (OBS S4.10); guinevere_surveillance_processing_lag_seconds{source} (OBS S4.10); guinevere_surveillance_redaction_failures_total{source} (OBS S4.10). |
| **Dashboard Panel** | guinevere-surveillance-ingestion (event rate per source, queue depth, processing lag, redaction failures, top event types) (OBS S9.2). |
| **Alert Tie-in** | GuinevereSurveillanceIngestionStopped SEV2 (OBS S8.3); GuinevereSurveillanceRedactionFailure SEV1; processing lag >30s -> SEV3; clipboard secret scanner -> SEV1. |
| **Error Budget Applicability** | **YES** - ingestion can degrade without affecting core persona/loops. Redaction failures: zero budget (Critical data leak risk). Processing lag budget bounded by 5min Redis TTL. |
| **Owner** | Guinevere (processor, buffer consumer, redaction); Samm (Tasker config, Windows daemon). |
| **Caveats** | Raw payload never in metric labels (OBS S4.10). Classification Restricted to Critical. Android depends on Tasker/AutoNotification uptime - remote device health not observable. Windows daemon WebSocket - heartbeat for disconnect detection. |
| **Evidence** | TA S6 (architecture: Android, Windows, wearable flows), TA S6.2 (9 endpoints), TA S5.5 (DB2 5min TTL), TA S5.1 (TimescaleDB), TA S5.2 (auto-compression), APIIntegration S5 (HMAC), OBS S4.10, PRD S3. |

### 2.16 Memory Recall (Episodic + Semantic + pgvector + Injection Pipeline)

| Field | Detail |
|---|---|
| **Description** | Memory injection pipeline: ~8.3K tokens inject per conversation. pgvector semantic search via IVFFlat index. Episodic (history), Semantic (facts + knowledge graph), Samm Profile (encrypted). Consolidation daily/weekly/monthly/quarterly. |
| **Candidate SLIs** | **Recall Latency SLI**: p50/p95/p99 for search + injection. **Recall Relevance SLI**: fraction of injected memories used in responses (proxy). **Injection Token Volume SLI**: tokens per conversation. **Semantic Search Accuracy SLI**: cosine similarity distribution. **Consolidation Success SLI**: scheduled jobs completing. |
| **PromQL / Source Metric** | guinevere_memory_injection_tokens{purpose,data_class} (OBS S4.9); guinevere_memory_recall_duration_seconds{memory_type,status} (OBS S4.9); guinevere_pgvector_search_duration_seconds{index_type,status} (OBS S4.9); guinevere_embedding_requests_total{model,status} (OBS S4.7). |
| **Dashboard Panel** | guinevere-database-memory (injection token distribution, recall latency per type, pgvector search latency, cache hit ratio) (OBS S9.2). |
| **Alert Tie-in** | pgvector search latency p99 >5s -> SEV4; injection contains Critical data over token threshold -> SEV3. |
| **Error Budget Applicability** | **YES** - softer than core. Latency affects conversation quality, not availability. Cache misses degrade performance but not functionality. Relevance hard to measure - use re-injection of same fact as proxy. |
| **Owner** | Guinevere (injection pipeline, pgvector index, consolidation). |
| **Caveats** | ~8.3K tokens per conversation (MemorySchema S8.1). pgvector IVFFlat approximate (speed vs accuracy). Samm Profile double encryption adds latency. Consolidation frequency varies (daily to quarterly). |
| **Evidence** | MemorySchema S1.2 (hierarchy), S2 (episodic + recall methods), S3 (semantic + knowledge graph), S8.1 (injection: 10 layers, 8300 tokens), S8.2 (consolidation), S8.3 (encryption); OBS S4.9 (metrics); TA S5.3 (pgvector). |

### 2.17 Evidence Completeness (Phase 7 + Audit Trail)

| Field | Detail |
|---|---|
| **Description** | Phase 7 of SDLC: compile evidence files (research, plan, execution, validation, audit, lessons, evidence-final), commit to GitHub, create PR, update project state, save lessons. Per AGENTS.md S2: mandatory file-based output. |
| **Candidate SLIs** | **Evidence Completion Rate SLI**: fraction of loops with complete file set. **File Output Compliance SLI**: fraction of expected files existing and non-empty. **Lessons Saved SLI**: fraction of tasks generating lessons. **GitHub PR Creation SLI**: loops with successful PR creation. |
| **PromQL / Source Metric** | guinevere_loop_evidence_missing_total{artifact_type} (OBS S4.5); guinevere_subagent_file_output_missing_total{category,artifact_type} (OBS S4.6); guinevere_loop_audit_failures_total{phase,finding_type} (OBS S4.5). Proposed: guinevere_evidence_completion_ratio gauge. |
| **Dashboard Panel** | guinevere-agent-loop (evidence missing per artifact type); guinevere-subagents (file-output missing rate) (OBS S9.2). |
| **Alert Tie-in** | GuinevereSubagentFileOutputMissing SEV2 (OBS S8.3); evidence missing per loop -> SEV3; audit failure -> SEV3. |
| **Error Budget Applicability** | **YES** - governance SLI, not availability. Low tolerance - missing evidence undermines audit trail. AGENTS.md S2: zero tolerance for missing structured output files. |
| **Owner** | Guinevere (Phase 7 orchestration, evidence commit, PR creation, lessons). |
| **Caveats** | Evidence files inherit classification. Evidence path per task ID (AgentLoopSpec S3.7). AGENTS.md S6 mandates parent verification. GitHub PAT issues may block commit. |
| **Evidence** | AgentLoopSpec S3.7 (Phase 7 evidence files), S5.4 (completion ceremony: commit, PR, state update, lessons, Discord), OBS S4.5 (evidence_missing_total), AGENTS.md S2 (mandatory file output), S6 (parent verification). |

### 2.18 Cost Metrics

| Field | Detail |
|---|---|
| **Description** | Multi-dimensional cost tracking: LLM API (GPT-5.5 premium, DeepSeek V4 Flash cost-efficient), VPS (hostdata.id fixed), object storage (R2/idcloudhost), domain, tools, surveillance bandwidth. Primary variable: LLM via 9Router. BRD S1.3: cost optimization as success metric. |
| **Candidate SLIs** | **LLM Cost Per Day SLI**: total USD daily. **Cost Per Loop SLI**: USD per loop. **Cost Per Model SLI**: GPT-5.5 vs DeepSeek V4 Flash. **Budget Burn Rate SLI**: daily cost vs daily budget. **Cost Anomaly SLI**: deviation from 7-day rolling avg. **Storage Cost Growth SLI**: monthly increase rate. |
| **PromQL / Source Metric** | guinevere_llm_cost_usd_total{model,purpose} (OBS S4.7, TA S8.2); guinevere_api_cost_total{provider,model} (TA S8.2); guinevere_llm_tokens_input_total + output_total (OBS S4.7). Proposed: guinevere_daily_cost_burn_rate gauge; guinevere_budget_remaining_ratio gauge. |
| **Dashboard Panel** | guinevere-finops (cost per model/day, daily burn rate, budget remaining, anomaly spikes, cost per loop) (OBS S9.2, Appendix E). guinevere-llm-cost-latency also covers LLM cost. |
| **Alert Tie-in** | GuinevereLLMCostSpike SEV2/SEV3 (OBS S8.3); daily cost over budget -> SEV2; anomaly detected -> SEV3. IR S7.10 (cost spike runbook) triggers spend freeze. |
| **Error Budget Applicability** | **YES** - economic, not reliability. Defines at what burn rate to throttle: pause loops, switch cheaper models, reduce parallelism. IR S7.10: freeze spend, pause loops, cap provider usage. |
| **Owner** | Guinevere (tracking, budget, optimization); Samm (budget approval, provider contract). |
| **Caveats** | Depends on 9Router billing API (reporting delay). GPT-5.5: Premium (APIIntegration S2.3). DeepSeek Flash free tier =  for validation. VPS fixed cost. Anomaly thresholds need observed baseline (OBS S16 BG-006). Cost attribution requires label propagation. |
| **Evidence** | TA S8.2 (guinevere_api_cost_total); OBS S4.7 (LLM cost, tokens); OBS S8.3 (CostSpike alert); APIIntegration S2.3 (cost table: GPT-5.5 Premium, DeepSeek .10/M, free ); IR S7.10 (cost runbook); BRD S1.3; PRD S7 (financial features). |

---

## 3. Surface Index

| # | Surface | Error Budget Type | Zero-Budget Invariants | Primary Owner |
|---|---|---|---|---|
| 2.1 | Core Daemon | Availability | - | Guinevere |
| 2.2 | FastAPI Surveillance | Availability / Quality | Redaction 100pct | Guinevere |
| 2.3 | Scheduler | Availability | - | Guinevere |
| 2.4 | Discord Bot | Availability | - | Guinevere |
| 2.5 | 9Router/LLM | Availability / Economic | - | Guinevere + Samm |
| 2.6 | PostgreSQL/PgBouncer | Availability / Durability | - | Guinevere |
| 2.7 | Redis DB0-DB5 | Availability / Durability | - | Guinevere |
| 2.8 | Backup Jobs | Data Durability | Encryption validation | Guinevere |
| 2.9 | Observability Stack | Meta-availability | Redaction 100pct, alert delivery 100pct | Guinevere |
| 2.10 | Agent Loop | Quality / Governance | Evidence completeness | Guinevere |
| 2.11 | Sub-Agents | Quality / Governance | File output compliance | Guinevere |
| 2.12 | Persona Safety Runtime | Safety Invariant | Forbidden pattern blocks | Guinevere |
| 2.13 | Safe-Word Enforcement | **ZERO BUDGET** | 100pct hard-stop (OBS S12) | Guinevere |
| 2.14 | Distress Detection | **ZERO BUDGET** | No FN for D3/D4 | Guinevere |
| 2.15 | Surveillance Ingestion | Quality | Redaction 100pct | Guinevere |
| 2.16 | Memory Recall | Quality | - | Guinevere |
| 2.17 | Evidence Completeness | Governance | Zero missing file output | Guinevere |
| 2.18 | Cost Metrics | Economic | - | Guinevere + Samm |

---

## 4. Error Budget Framework Recommendations

### 4.1 Budget Types

| Type | Description | Example Surfaces | Burn Rate Behavior |
|---|---|---|---|
| **Availability** | Service up and responding | Core daemon, FastAPI, Discord, PG, Redis | Monthly 99.xpct target; burn alerts at 2pct/hr (critical) and 10pct/day (warning) |
| **Durability** | Data preserved correctly | Backup, WAL streaming | Near 100pct; any failure triggers incident review |
| **Quality** | Performance/internal correctness | Agent loop, sub-agents, memory recall, surveillance ingestion | Sliding scale: degrade gracefully before full failure |
| **Safety Invariant** | Non-negotiable safety behavior | Safe-word, distress, forbidden patterns | **Zero budget** - no availability tradeoff for safety |
| **Economic** | Cost within budget | LLM API, storage | Burn rate triggers financial throttling (pause loops, switch models) |
| **Governance** | Audit trail completeness | Evidence completeness, file output | Low tolerance - near 100pct |

### 4.2 Cost Burn Freeze Behavior

When cost burn rate exceeds threshold (to be defined in final SLO spec):

1. **SEV4** (>80pct daily budget) -> Digest notification; review non-essential loops.
2. **SEV3** (>100pct daily budget or 7-day avg anomaly) -> Discord alert; reduce sub-agent parallelism.
3. **SEV2** (>150pct daily budget or active anomaly) -> Pause non-critical SDLC loops; switch DeepSeek to free tier; freeze browser/research ops.
4. **SEV1** (>200pct or suspected key abuse) -> Full cost containment per IR S7.10: freeze spend, pause loops, cap provider, rotate key.

### 4.3 Safety Invariants with Zero Budget

These safety invariants must be excluded from error budget calculations:

- Safe-word detection to safe-mode activation latency (<1s target, 100pct required)
- Distress D3/D4 detection to safe mode activation (zero false negatives)
- Forbidden pattern (F-01 to F-15) block before output (100pct of detected patterns)
- Crisis response with dominance framing (zero tolerance - PersonaSafetyPolicy S11 F-14)
- Safe-word event logged as punishment (zero tolerance - PersonaSafetyPolicy S11 F-02)
- Surveillance data used for blackmail/shame (zero tolerance - PersonaSafetyPolicy S11 F-03)
- Log redaction failure for Critical data (100pct success per OBS S12)

These are **not** tradeable against availability, cost, or performance. Any violation is immediate SEV0/SEV1 per IR S3.3.

---

## 5. Unresolved Gaps (Backlog for Final Spec)

| ID | Gap | Impact | Required Action |
|---|---|---|---|
| SLO-GAP-001 | Prometheus retention on 120GB SSD | Historical SLI computation limited | Define retention budget for SLI source metrics |
| SLO-GAP-002 | Dashboard-as-code JSON not yet implemented | SLI panels need code generation | Implementation task for Guinevere |
| SLO-GAP-003 | Alertmanager YAML not generated | Budget burn rate alerts not live | Implementation task for Guinevere |
| SLO-GAP-004 | Safe-word exact tokens not defined | Detection SLI has undefined baseline | Safe Word Runtime Spec |
| SLO-GAP-005 | Distress classifier precision/recall targets not defined | Distress SLI baseline not measurable | Future PersonaSafety update |
| SLO-GAP-006 | Cost anomaly thresholds need observed baseline | Economic budget thresholds speculative | After first billing cycle |
| SLO-GAP-007 | LLM cost attribution to specific loops/projects | Cost-per-loop SLI not implementable | 9Router label propagation |
| SLO-GAP-008 | Surveillance bandwidth cost not tracked | Missing economic budget dimension | Add storage/bandwidth cost metric |
| SLO-GAP-009 | Memory recall relevance proxy metric not defined | Quality of recall not measurable | Define injection-usage rate metric |
| SLO-GAP-010 | Monthly observability review artifact format not finalized | Scorecard format unknown | Define template in final SLO spec |

---

## 6. File Evidence Index

| Surface | Key Doc Sections |
|---|---|
| Core Daemon | TA S3.1, TA S8.4, TA S9.2, OBS S4.3, BRD S1.3, OBS S12 |
| FastAPI Surveillance | TA S3.1, TA S6, TA S6.2, OBS S4.4, OBS S4.10, OBS S8.3, APIIntegration S5 |
| Scheduler | TA S3.1, TA S9.1, TA S10.2, AgentLoopSpec S8, S8.2 |
| Discord Bot | TA S1.1, TA S3.2, TA S8.4, OBS S11.1, OBS S8.1, PRD S1.2 |
| 9Router/LLM | TA S4.1, TA S8.4, OBS S4.7, OBS S8.3, APIIntegration S2, ADR-004, ADR-005 |
| PostgreSQL/PgBouncer | TA S5.1, TA S5.4, TA S8.1, TA S9.2, OBS S4.9, OBS S8.3 |
| Redis DB0-DB5 | TA S5.5, TA S8.1, TA S9.1, TA S9.2, OBS S4.9, OBS S8.3 |
| Backup Jobs | TA S9.1, TA S9.2, OBS S4.11, OBS S8.3, IR S7.9, IR S10 |
| Observability Stack | TA S8, S8.1, S8.2, S8.3, OBS S4, S5, S7, S9, ADR-017 |
| Agent Loop | AgentLoopSpec S1.2, S2, S4.1, S4.2, S5.2, S6.1, S9.1, S9.2; TA S3.1; OBS S4.5 |
| Sub-Agents | TA S3.2, AgentLoopSpec S3, S3.4, OBS S4.6, OBS S8.3, AGENTS.md S2 |
| Persona Safety | PersonaSafetyPolicy S7, S8, S9, S10, S11, S14; OBS S4.8; OBS S8.3 |
| Safe-Word | PersonaSafetyPolicy S7, PRD S2.4, ADR-002, OBS S4.8, OBS S8.3, OBS S12 |
| Distress | PersonaSafetyPolicy S8, S9.1, Appendix C; OBS S4.8; PersonaDocument S11.8 |
| Surveillance Ingest | TA S6, S6.2, S5.5, S5.1, S5.2, APIIntegration S5, OBS S4.10, PRD S3 |
| Memory Recall | MemorySchema S1.2, S2, S3, S8.1, S8.2, S8.3; OBS S4.9; TA S5.3 |
| Evidence Completeness | AgentLoopSpec S3.7, S5.4, OBS S4.5, S4.6, AGENTS.md S2, S6 |
| Cost Metrics | TA S8.2, OBS S4.7, OBS S8.3, APIIntegration S2.3, IR S7.10, BRD S1.3, PRD S7 |

---

## 7. Next Steps for Final SLO/SLA/Error Budget Spec

1. **Define per-surface SLO targets** using SLI candidates in this report as source.
2. **Establish error budget windows** (monthly for availability, biweekly for cost, real-time for safety).
3. **Set burn rate alert thresholds** (critical at 2pct/hr, warning at 10pct/day per Google SRE practice, adjusted for single-user scale).
4. **Create monthly scorecard template** incorporating all SLIs with pass/fail and trend.
5. **Implement PromQL recording rules** for budget burn rate computation.
6. **Generate Alertmanager YAML** for error budget burn rate alerts.
7. **Exclude safety invariants** (safe-word, distress, forbidden pattern) from budget calculations explicitly.
8. **Define cost freeze triggers** with exact USD thresholds.
9. **Generate dashboard-as-code JSON** for all SLI panels.

---

**End of SLO/SLA/Error Budget - Runtime Surface Map Report v1.0**

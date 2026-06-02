# Observability & Alerting — Source Map Report

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
| `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` | Defines severity matrix, alert channels, incident lifecycle, and evidence duties that the observability spec must operationalize. |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Defines `observability-reader` principal, metric/dashboard/health-check read scope, ABAC-011 raw-payload denial, and Tailscale `tag:monitoring` metadata-only rule. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines monitoring stack (Prometheus + Grafana + Loki + Sentry + Gotify + Discord on primary VPS), systemd services, FastAPI endpoints, PostgreSQL/PgBouncer, Redis DB0-DB5, health checks, and custom metrics. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines loop phases, Loop Guardian, TODO Enforcer, sub-agent orchestration, and loop quality metrics that require observability hooks. |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Defines data classes (Public/Internal/Confidential/Restricted/Critical), retention classes, audit log requirements, and minimization rules that constrain what may appear in metrics/logs/traces. |
| `Guinevere_PersonaSafetyPolicy_v1.0.md` | Defines safe-word hard stop, distress handling, forbidden patterns, yandere intensity, drift score, and safe-mode restrictions that must suspend persona-flavored alerting. |
| `adr/ADR-017-monitoring-stack-selection.md` | Normative parent decision: Prometheus + Grafana on primary VPS first; dedicated monitoring VPS post-MVP. |
| `adr/ADR-018-security-architecture-defense-in-depth.md` | Normative parent for least-privilege, audit logs, defense-in-depth, and incident hooks. |

---

## 1. Authority Chain and Normative Hierarchy

Observability & Alerting Specification must be interpreted in this authority order:

1. System/developer safety requirements and platform constraints.
2. Accepted ADRs: ADR-017 (monitoring stack), ADR-018 (defense-in-depth).
3. `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` — incident severity, alert routing, evidence duties.
4. `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` — access restrictions for metrics/logs/dashboards.
5. `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` — classification, retention, minimization.
6. `Guinevere_PersonaSafetyPolicy_v1.0.md` — safe-mode/persona override for alerts.
7. `Guinevere_TechnicalArchitecture_v2.0.md` — concrete surfaces and stack components.
8. `Guinevere_AgentLoopSpec_v2.0.md` — loop state and sub-agent compliance metrics.

If any lower document grants broader observability access than this chain, the higher document wins. Safe-word, distress, crisis, SEV0/SEV1 incident, and key-compromise states activate stricter restrictions.

---

## 2. Monitoring Topology (Current Accepted State)

### 2.1 Primary VPS (Active Now)

| Layer | Component | Location | Purpose |
|---|---|---|---|
| Metrics | Prometheus | Docker container, VPS primary | Metrics collection + storage |
| Visualization | Grafana | Primary VPS (Tailscale `grafana.internal:3000`) | Dashboard + alerting evaluation |
| Logs | Loki + Promtail | Docker container, VPS primary | Unified log aggregation + shipping |
| Error tracking | Sentry | External service | Error + exception capture |
| Push notification | Gotify | External/self-hosted | Urgent alert push backup |
| Incident channel | Discord | External API | Primary incident command channel |

Evidence: `Guinevere_TechnicalArchitecture_v2.0.md` §8.1 states "Prometheus + Grafana on primary VPS first" and `adr/ADR-017-monitoring-stack-selection.md` §Decision Outcome locks "Prometheus + Grafana on primary VPS first; separate monitoring VPS post-MVP."

### 2.2 Future Dedicated Monitoring VPS

Post-MVP only. Not active in current topology. Must not be treated as available for alert routing or dashboard hosting until explicitly deployed.

Evidence: `Guinevere_TechnicalArchitecture_v2.0.md` §8.1 and `adr/ADR-017-monitoring-stack-selection.md`.

### 2.3 Network Constraints

- All monitoring endpoints are Tailscale-internal only.
- `grafana.internal:3000` and `metrics.internal:9090` accept Tailscale connections only.
- Tailscale tag `tag:monitoring` allows Prometheus/Grafana metadata only; raw Critical payload is denied.
- Zero public VPS ingress is mandatory.

Evidence: `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` §14 Tailscale ACL Matrix row `tag:monitoring`; `Guinevere_TechnicalArchitecture_v2.0.md` §2.2 Network Architecture.

---

## 3. Existing Metrics (Current State)

### 3.1 Infrastructure Metrics (via Exporters)

| Metric Source | Exporter | Location |
|---|---|---|
| System (CPU/RAM/disk) | node_exporter | VPS primary |
| PostgreSQL | postgres_exporter | VPS primary |
| Redis | redis_exporter | VPS primary |

Evidence: `Guinevere_TechnicalArchitecture_v2.0.md` §8.1.

### 3.2 Custom Guinevere Metrics (Designed but Not Yet Fully Specified)

Current designed metrics from `Guinevere_TechnicalArchitecture_v2.0.md` §8.2:

| Metric Name | Type | Labels | Notes |
|---|---|---|---|
| `guinevere_task_completion_total` | counter | project, phase | Tracks completed tasks |
| `guinevere_mood_state` | gauge | none | Value 0-5 (silent=0, dark=1, disappointed=2, neutral=3, pleased=4, nurturing=5) |
| `guinevere_mommy_score` | gauge | none | Samm productivity score per day |
| `guinevere_punishment_level` | gauge | none | Current escalation level |
| `guinevere_api_cost_total` | counter | provider, model | LLM spend tracking |
| `guinevere_sub_agents_active` | gauge | none | Active sub-agent count |
| `guinevere_surveillance_events_total` | counter | source, type | Surveillance ingestion rate |
| `guinevere_memory_injection_tokens` | histogram | none | Tokens per memory injection |
| `guinevere_llm_latency_seconds` | histogram | model, use_case | LLM response latency |
| `guinevere_violation_total` | counter | violation_type | Safety violations |

Additional metrics from `Guinevere_AgentLoopSpec_v2.0.md` §9.1:

| Metric Name | Type | Labels |
|---|---|---|
| `guinevere_loop_duration_seconds` | histogram | task_type, project |
| `guinevere_phase_duration_seconds` | histogram | phase |
| `guinevere_todo_completion_rate` | gauge | none |
| `guinevere_subagent_performance` | histogram | agent_type, latency, success_rate |
| `guinevere_loop_efficiency_score` | gauge | none |
| `guinevere_error_rate` | counter | error_type |
| `guinevere_test_coverage` | gauge | project |
| `guinevere_token_usage` | counter | model, loop |
| `guinevere_loops_parallel` | gauge | none |
| `guinevere_todo_enforcer_yanks` | counter | none |

### 3.3 Metric Gaps Against Approved Constraints

The user-locked constraints require these custom metrics, which are NOT all present in the current designed set:

| Required Metric | Present? | Gap |
|---|---|---|
| mood state | Yes | `guinevere_mood_state` exists |
| mommy score | Yes | `guinevere_mommy_score` exists |
| punishment level | Yes | `guinevere_punishment_level` exists |
| yandere intensity | **NO** | Missing from both docs |
| reward streak | **NO** | Missing from both docs |
| violation count | Partial | `guinevere_violation_total` exists but label set may need expansion |
| safe-mode state | **NO** | Missing from both docs |
| drift score | **NO** | Missing from both docs |
| loop state | **NO** | Missing from both docs (loop_instances table exists in PostgreSQL but no Prometheus metric) |
| sub-agent compliance | **NO** | Missing from both docs |
| LLM cost/latency | Partial | `guinevere_api_cost_total` + `guinevere_llm_latency_seconds` exist; must ensure cost includes 9Router routing |
| surveillance event rate | Partial | `guinevere_surveillance_events_total` exists; must ensure rate includes all ingestion paths |

Conclusion: The spec must add at least 6 missing metrics and validate label schemas for existing ones.

---

## 4. Incident Severity and Alert Routing (From Incident Response)

### 4.1 Severity Matrix (Canonical)

| Severity | Triage Deadline | Minimum Notification | Postmortem |
|---|---|---|---|
| SEV0 | Immediate | Discord + Gotify urgent | Mandatory |
| SEV1 | <= 15 minutes | Discord + Gotify urgent | Mandatory |
| SEV2 | <= 1 hour | Discord primary | Mandatory |
| SEV3 | <= 24 hours | Summary unless live update requested | Required if repeated |
| SEV4 | Next governance cycle | Review summary | Optional |

Evidence: `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` §3.1.

### 4.2 Alert Routing (User-Locked Constraints)

| Severity | Discord | Gotify | Other |
|---|---|---|---|
| SEV0 | Yes | Yes (urgent) | Immediate Samm alert |
| SEV1 | Yes | Yes (urgent) | Urgent Samm alert |
| SEV2 | Yes | No | Same-day Samm notification |
| SEV3 | Yes | No | Summary digest |
| SEV4 | No | No | Governance cycle |

### 4.3 Data Class Impact Mapping

| Data Impact | Minimum Severity |
|---|---|
| Confirmed Critical exposure | SEV0 |
| Suspected Critical exposure | SEV1 |
| Restricted exposure | SEV2 |
| Confidential exposure | SEV3 |
| Blocked near-miss | SEV4 |

Evidence: `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` §3.2 and §6.1.

### 4.4 Alert Tone Requirement

**All alerts must use neutral incident-command tone only. Persona flavor, yandere framing, punishment behavior, and autonomous pressure are suspended for all alerts.**

Evidence: `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` §2 Incident Command Model row "Default Incident Commander" constraint "Must use neutral incident-command tone"; §6.2 Discord Alert Template; user-locked constraint "Alert tone neutral incident-command only; persona/yandere suspended for all alerts."

---

## 5. Safe-Mode and Persona Override for Alerting

### 5.1 Safe-Mode States That Override Alerting

| State | Effect on Alerting |
|---|---|
| safe-word | All persona/yandere/punishment alert content suspended; neutral tone mandatory |
| distress | Same as safe-word; supportive framing only |
| crisis | Same; no dominance/ownership language |
| SEV0/SEV1 incident | Same; incident-command tone mandatory |
| key-compromise | Same; containment focus only |

Evidence: `Guinevere_PersonaSafetyPolicy_v1.0.md` §7.2 Immediate Runtime Actions; `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` §2 "Incident response overrides persona/yandere/punishment behavior."

### 5.2 Forbidden Alert Patterns

Alerts must never:

- Include raw intimate content, raw safe-word text beyond minimal event class, or raw surveillance payload.
- Use persona tone, yandere framing, or punishment language.
- Use surveillance data for blackmail, shame, or threat.
- Escalate yandere intensity in response to distress.

Evidence: `Guinevere_PersonaSafetyPolicy_v1.0.md` §11 Forbidden Behavior Matrix F-01 through F-15; `Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md` §6.2.

---

## 6. Logging and Audit Restrictions

### 6.1 What Logs Must Exclude

Logs and observability data must exclude:

- Plaintext secrets, tokens, API keys, decrypted credentials.
- Raw intimate content, raw safe-word content beyond minimal event class.
- Raw surveillance payload when hash/summary is sufficient.
- Raw Critical data in views accessible to `observability-reader`.

Evidence: `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` §5 RBAC role `observability-reader` explicit denial "No raw payload, no secret, no Critical content"; ABAC-011 "Observability request includes raw payload or secret → Deny"; `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` §9.3 LLM Prompt Minimization and §10.1 Audit Log Requirements.

### 6.2 systemd Status/Log Metadata

systemd status and log metadata are allowed for observability-reader. This is the boundary between "metadata" and "raw payload."

Evidence: Provided inline findings: "systemd status/log metadata allowed."

### 6.3 Evidence Logging Rules

- Audit events must include timestamp, principal, role, action, resource identifier, classification, purpose, safety state, decision, grant expiry, approval reference, and evidence path.
- Audit events must not include plaintext secrets, raw intimate content, raw safe-word content beyond minimal event class, or raw surveillance payload when hash/summary is enough.

Evidence: `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` §17 Audit and Enforcement.

---

## 7. Access Restrictions for Observability Surfaces

### 7.1 Principals Allowed

| Principal | Allowed Observability Actions | Denied |
|---|---|---|
| `observability-reader` | Metrics read, dashboard read, health-check read, logs metadata read | Raw payload, secrets, Critical content, DB redacted audit views only |
| `Samm` | All observability access | None at policy level; all access audited for Critical |
| `guinevere_core` | Metrics write, log write, alert trigger | None at policy level; must follow safe-mode restrictions |
| `readonly-auditor` | Read audit/evidence/control outputs | Write, decrypt, raw Critical unless Samm grants |
| `sub-agent-researcher` | Read docs, produce research reports | Direct Critical data, secrets, raw surveillance |

Evidence: `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` §5 and §15.

### 7.2 Tailscale Network Restrictions

- `tag:monitoring` allows Prometheus/Grafana metadata only.
- All monitoring endpoints are Tailscale-internal only.
- Zero public VPS ingress is mandatory.

Evidence: `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` §14 Tailscale ACL Matrix; `Guinevere_TechnicalArchitecture_v2.0.md` §2.2.

---

## 8. Data Classification Constraints for Observability

### 8.1 Metric Label Constraints

- **No high-cardinality labels in Prometheus.** This is a user-locked constraint.
- Labels must be bounded and low-cardinality.
- Sensitive data must not appear in metric labels; use hashed or summary forms instead.

### 8.2 Log Classification

| Log Type | Classification | Allowed in Loki |
|---|---|---|
| Application logs | Confidential → Critical | Metadata and structured fields only; no raw payload |
| Audit logs | Confidential → Critical | Minimized; no plaintext secrets |
| Surveillance logs | Restricted → Critical | Summaries/hashes; raw only with formal hold |
| System logs | Internal | journald metadata allowed |
| Guinevere action log | Confidential → Critical | Action metadata only |

Evidence: `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` §5 Classification Matrix; `Guinevere_TechnicalArchitecture_v2.0.md` §8.3 Logging Architecture.

### 8.3 Trace ID Propagation

All distributed traces and correlated events must propagate:

- `trace_id`
- `request_id`
- `task_id`
- `loop_id`
- `subagent_task_id`
- `incident_id`
- `evidence_id`

Evidence: User-locked constraint.

### 8.4 Retention for Observability Data

- Metrics retention: defined by Prometheus storage configuration.
- Log retention in Loki: defined by retention policies per data class.
- Audit logs: 1 year default; longer for incidents/formal holds.
- Error events in Sentry: per Sentry configuration with PII scrubbing.

Evidence: `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` §6 Retention Classes.

---

## 9. Sentry Configuration Constraints

| Constraint | Requirement |
|---|---|
| `send_default_pii` | `false` |
| `before_send` scrubber | Mandatory |
| Data sent | Non-PII error context only |

Evidence: User-locked constraint.

---

## 10. Technical Monitoring Stack Summary

| Component | Version | Location | Purpose |
|---|---|---|---|
| Prometheus | Latest | Docker, VPS primary | Metrics collection + storage |
| Grafana | Latest | Primary VPS | Dashboard + alerting |
| Loki | Latest | Docker, VPS primary | Log aggregation |
| Promtail | Latest | VPS primary | Log shipping to Loki |
| node_exporter | Latest | VPS primary | System metrics |
| postgres_exporter | Latest | VPS primary | PostgreSQL metrics |
| redis_exporter | Latest | VPS primary | Redis metrics |
| Sentry | External | SaaS | Error tracking |
| Gotify | External/self-hosted | External | Push notification backup |
| Discord | External API | External | Incident command channel |

Evidence: `Guinevere_TechnicalArchitecture_v2.0.md` §8.1; `adr/ADR-017-monitoring-stack-selection.md`.

### 10.1 Dashboard-as-Code Requirement

Dashboard-as-code is mandatory. Dashboards must be version-controlled, reproducible, and defined as code artifacts rather than UI-only configurations.

Evidence: User-locked constraint.

---

## 11. Gaps, Conflicts, and Unresolved Items

| ID | Gap / Conflict | Source | Impact |
|---|---|---|---|
| OBS-GAP-001 | yandere intensity metric missing | Required metric vs existing designed metrics | Spec must add `guinevere_yandere_intensity` gauge |
| OBS-GAP-002 | reward streak metric missing | Required metric vs existing designed metrics | Spec must add `guinevere_reward_streak` gauge |
| OBS-GAP-003 | safe-mode state metric missing | Required metric vs existing designed metrics | Spec must add `guinevere_safe_mode_state` gauge |
| OBS-GAP-004 | drift score metric missing | Required metric vs existing designed metrics | Spec must add `guinevere_drift_score` gauge |
| OBS-GAP-005 | loop state metric missing | Required metric vs existing designed metrics | Spec must add `guinevere_loop_state` gauge with phase labels |
| OBS-GAP-006 | sub-agent compliance metric missing | Required metric vs existing designed metrics | Spec must add `guinevere_subagent_compliance` gauge/counter |
| OBS-GAP-007 | Prometheus alert rules not yet specified | IR-BG-004 from Incident Response | Detection SLAs can fail without alert config |
| OBS-GAP-008 | Cost threshold values not set | IR-BG-005 from Incident Response | Cost anomaly severity needs budget numbers |
| OBS-GAP-009 | Sentry DSN configuration not yet documented | Technical Architecture mentions Sentry but no config details | Implementation can drift on PII scrubbing |
| OBS-GAP-010 | Gotify/Discord alert routing not yet implemented | IR-BG-004 + ADR-017 | Notification channels configured but alert rules not wired |
| OBS-CONFLICT-001 | "data forever" retention vs tiered retention | Data Governance §2.2 supersedes blanket language | Observability retention must follow tiered policy, not infinite |

---

## 12. Final Observability Specification Checklist

The final `Guinevere_Observability_AlertingSpec_v1.0.md` must include:

### 12.1 Required Sections

- [ ] Authority chain and normative hierarchy
- [ ] Monitoring topology (primary VPS + future dedicated VPS)
- [ ] Complete metric catalog with names, types, labels, and owners
- [ ] All 12 required custom metrics including the 6 missing ones
- [ ] Alert rules with severity mapping (SEV0-SEV4)
- [ ] Alert routing table (Discord/Gotify/digest/governance)
- [ ] Neutral incident-command tone enforcement
- [ ] Safe-mode/persona override rules for all alert channels
- [ ] Logging restrictions (no secrets, no raw intimate, no raw surveillance beyond hash)
- [ ] Access control matrix for observability-reader and related principals
- [ ] Data classification constraints for metrics, logs, traces, and dashboards
- [ ] High-cardinality label ban with enforcement guidance
- [ ] Trace ID propagation schema
- [ ] Sentry configuration (`send_default_pii=false`, `before_send` scrubber)
- [ ] Dashboard-as-code implementation guidance
- [ ] Retention policies per data class and log type
- [ ] Monthly observability review process
- [ ] Drill matrix tied to IncidentResponse drill matrix
- [ ] Gap resolution plan for OBS-GAP-001 through OBS-CONFLICT-001

### 12.2 Normative Children That Must Reference This Spec

- ADR-017: Monitoring Stack Selection
- ADR-018: Security Architecture & Defense-in-Depth
- IncidentResponse: Drill matrix, alert routing, evidence path
- AccessControl: observability-reader principal, ABAC-011, tag:monitoring
- DataGovernance: retention, classification, minimization
- PersonaSafety: safe-mode alert tone, forbidden patterns

### 12.3 Implementation Gates

- [ ] All metrics have low-cardinality labels only.
- [ ] All dashboard JSON is version-controlled.
- [ ] All alert rules have severity, owner, and runbook link.
- [ ] All Sentry events are scrubbed before send.
- [ ] All trace correlation IDs are propagated end-to-end.
- [ ] Monthly observability review scheduled and templated.

---

**End of Observability & Alerting Source Map Report v1.0**

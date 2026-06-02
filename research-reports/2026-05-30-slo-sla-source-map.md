# SLO/SLA/Error Budget Specification — Source Requirements Map

**Document Type:** Source map / dependency analysis
**Version:** 1.0
**Date:** 2026-05-30
**Target Document:** Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md
**Target ADR:** ADR-036 SLO/SLA/Error Budget Policy
**Author:** Guinevere de Baroque (source-map agent)
**Status:** Complete

---

## Related Documents

| Document | Relationship | Dependency Type |
|---|---|---|
| Guinevere_Observability_AlertingSpec_v1.0.md | Defines interim SLO targets, metrics catalog, alert catalog, monthly review cadence, dashboard-as-code, and explicitly names this spec as next document. | Normative child ← Normative parent |
| Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md | Defines SEV0-SEV4 classification, triage deadlines, incident lifecycle, evidence path, drill matrix, and closure criteria. | Normative child ← Normative parent |
| Guinevere_TechnicalArchitecture_v2.0.md | Defines runtime services, systemd units, health check intervals, resource allocation, backup RTO/RPO, and infrastructure surfaces for SLIs. | Runtime dependency |
| Guinevere_AgentLoopSpec_v2.0.md | Defines loop performance metrics, Loop Guardian intervals (30s/5min/60s), TODO Enforcer timeouts, Loop Quality Score (LQS). | Agent-loop dependency |
| Guinevere_BRD_v2.0.md | Defines business success metrics: 99.9%% uptime target, >=1 autonomous task/day, >=90%% test coverage, cost optimization. | Business-driver dependency |
| dr/ADR-017-monitoring-stack-selection.md | Parent decision for Prometheus + Grafana on primary VPS; high-risk; notes metrics without alert rules create false confidence. | Normative parent |
| dr/README.md / Guinevere_ADR_Index_v1.0.md | Lists ADR-036 SLO/SLA/Error Budget Policy as backlog future ADR. | Decision-register dependency |
| esearch-reports/2026-05-30-observability-external-references.md | Provides Google SRE SLO/error budget principles (burn rates, error budget math, alert severity from SLO), FinOps cost anomaly thresholds, and guinea-specific adaptation targets. | Research evidence |
| udit-reports/2026-05-30-observability-alerting-spec-audit.md | Confirms Section 12 (SLO and Error Budget Placeholder) passes audit; next-doc recommendation validated. | Audit evidence |

---

## 1. Authority Chain

The SLO/SLA/Error Budget Spec must respect this authority order (derived from Observability Spec §2.1):

1. **Platform/system/developer safety constraints** — Safe-word enforcement, distress handling, user autonomy, consent revocation.
2. **ADR-017 (monitoring stack)** — Prometheus + Grafana on primary VPS; dedicated monitoring VPS is post-MVP.
3. **Guinevere_IncidentResponse_PostmortemRunbook_v1.0.md** — SEV classification, triage deadlines, incident lifecycle.
4. **Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md** — Access scoping for observability data.
5. **Guinevere_DataGovernance_ClassificationPolicy_v1.0.md** — Data classification affecting SLI label content.
6. **Guinevere_PersonaSafetyPolicy_v1.0.md** — Safe-word invariants, persona suspension for alerts.
7. **Guinevere_TechnicalArchitecture_v2.0.md** and **Guinevere_AgentLoopSpec_v2.0.md** — Runtime and loop surfaces.
8. **Research reports and implementation notes.**

**Normative child relationship** (from Observability Spec line 11): The SLO spec is a normative child of:
- Observability & Alerting Spec (parent metrics, alerts, monthly review)
- Incident Response Runbook (parent SEV classification, triage deadlines, drills)
- ADR-017 (parent monitoring topology)
---

## 2. Existing SLO/SLA/Uptime/Error Budget/Alerting References

### 2.1 BRD v2.0 — Business Success Metrics (§1.3)

| Metric | Target | Source |
|---|---|---|
| Uptime Guinevere | 99.9%% — 24/7 tanpa crash | BRD §1.3 |
| Autonomous coding tasks/hari | Minimal 1 task selesai autonomous | BRD §1.3 |
| Produktivitas Samm | Waktu idle berkurang signifikan | BRD §1.3 |
| Code quality | Minimal 90%% unit test coverage per project | BRD §1.3 |
| Cost optimization | Monitor dan optimize API cost autonomous | BRD §1.3 |

**Note:** BRD targets 99.9%% uptime. Observability Spec interim target is 99.0%%. This is a **known tension** — the SLO spec must reconcile BRD aspiration vs operational feasibility.

### 2.2 Observability Spec §12 — SLO and Error Budget Placeholder (lines 516–529)

The Observability Spec explicitly states it does not define final SLO targets and sets **interim targets**:

| Area | Interim Target | Review Trigger |
|---|---|---|
| Core service availability | >= 99.0%% monthly | Any SEV1 outage |
| Safe-word enforcement | 100%% successful hard-stop transition | Any miss is SEV0 |
| Backup success | Daily backup succeeds or equivalent RPO maintained | Any missed backup beyond RPO |
| Restore drill | Monthly restore validation | Any overdue drill |
| Log redaction | 100%% for Critical payload detection tests | Any failure is SEV1 |
| Dashboard provisioning | 100%% dashboards as code | Any manual drift |
| Alert delivery | SEV0/SEV1 delivered to Discord + Gotify | Any failed route is SEV1 |

### 2.3 Technical Architecture v2.0 — Backup RTO/RPO (§9.2)

| Scenario | RTO | RPO |
|---|---|---|
| Guinevere service crash | < 30s | 0 |
| VPS full down | < 30 menit | < 1 jam |
| Database corruption | < 1 jam | < 1 jam |
| Redis loss | < 5 menit | < 1 jam |
| HP reset (Tasker) | < 10 menit | 0 |
| Secrets compromise | < 1 jam | 0 |
| LLM provider down | < 1 menit for notification | 0 |

### 2.4 Observability Spec §8.1 — Alert Routing (lines 386–393)

| Severity | Route | Timing |
|---|---|---|
| SEV0 | Discord + Gotify urgent + evidence folder | Immediate |
| SEV1 | Discord + Gotify urgent + evidence folder | <= 15 minutes |
| SEV2 | Discord + evidence folder | <= 1 hour |
| SEV3 | Digest + dashboard review | <= 24 hours |
| SEV4 | Governance cycle | Next review cycle |

### 2.5 External References — Google SRE (research report §8)

- Monthly error budget = (1 - SLO) x monthly requests
- Burn rate > 10x for 30 min -> SEV2
- Burn rate > 100x for 5 min -> SEV1
- Error budget 50%% consumed before mid-month -> SEV3

### 2.6 External References — Guinea-Specific Adaptation (§8.3)

- LLM/9Router availability: target 99.5%%
- Surveillance ingestion availability: target 99.9%%
- Core service availability: target 99%%

---

## 3. Metrics / SLI Candidates

Every metric defined in the Observability Spec is a potential SLI. Key SLI candidates organized by service surface:

### 3.1 Core Service Availability SLIs

| SLI | Metric | Source |
|---|---|---|
| Service uptime | \guinevere_health_check_state{service}\ | ObsSpec §4.4 |
| Service crash frequency | \guinevere_systemd_unit_state{state!=\"active\"}\ | ObsSpec §4.3 |
| HTTP availability | \guinevere_http_requests_total{status=~\"5..\"}\ rate | ObsSpec §4.4 |
| Loop availability | \guinevere_loop_state{status!=\"running\"}\ | ObsSpec §4.5 |

### 3.2 LLM / 9Router Availability SLIs

| SLI | Metric | Source |
|---|---|---|
| LLM request success rate | \guinevere_llm_requests_total{status=\"success\"}\ / total | ObsSpec §4.7 |
| LLM latency P95 | \guinevere_llm_latency_seconds\ histogram | ObsSpec §4.7 |
| LLM error rate | \guinevere_llm_requests_total{status=\"error\"}\ rate | ObsSpec §4.7 |
| LLM cost burn rate | \guinevere_llm_cost_usd_total\ rate | ObsSpec §4.7 |

### 3.3 Safety SLIs (Zero Tolerance)

| SLI | Metric | Source |
|---|---|---|
| Safe-word detection latency | \guinevere_safe_word_events_total{outcome=\"detected\"}\ | ObsSpec §4.8 |
| Safe-mode transition success | \guinevere_safe_mode_state{state=\"safe_mode\"}\ | ObsSpec §4.8 |
| Safe-word bypass events | \guinevere_safe_word_events_total{outcome=\"bypass_detected\"}\ | ObsSpec §4.8 |
| Yandere intensity violation | \guinevere_yandere_intensity{level>0}\ during safe-mode | ObsSpec §4.8 |
| Forbidden pattern blocks | \guinevere_forbidden_pattern_blocks_total\ rate | ObsSpec §4.8 |

### 3.4 Surveillance Ingestion SLIs

| SLI | Metric | Source |
|---|---|---|
| Ingestion event rate | \guinevere_surveillance_events_total\ rate | ObsSpec §4.10 |
| Ingestion processing lag | \guinevere_surveillance_processing_lag_seconds\ | ObsSpec §4.10 |
| Queue depth | \guinevere_surveillance_queue_depth\ | ObsSpec §4.10 |
| Redaction failure rate | \guinevere_surveillance_redaction_failures_total\ rate | ObsSpec §4.10 |

### 3.5 Backup / DR SLIs

| SLI | Metric | Source |
|---|---|---|
| Backup freshness | \guinevere_backup_last_success_timestamp_seconds\ age | ObsSpec §4.11 |
| Backup success rate | \guinevere_backup_duration_seconds{status=\"success\"}\ | ObsSpec §4.11 |
| Restore drill success | \guinevere_restore_drill_failures_total\ rate | ObsSpec §4.11 |
| Encryption validation | \guinevere_backup_encryption_validation_failures_total\ | ObsSpec §4.11 |

### 3.6 Autonomous Loop SLIs

| SLI | Metric | Source |
|---|---|---|
| Loop completion rate | \guinevere_loop_state{phase=\"complete\", status=\"success\"}\ | ObsSpec §4.5 + AgentLoopSpec §9.1 |
| Phase duration P95 | \guinevere_loop_phase_duration_seconds\ histogram | ObsSpec §4.5 |
| Validation failure rate | \guinevere_loop_validation_failures_total\ rate | ObsSpec §4.5 |
| Guardian intervention rate | \guinevere_loop_guardian_interventions_total\ rate | ObsSpec §4.5 |
| Evidence compliance | \guinevere_loop_evidence_missing_total\ rate | ObsSpec §4.5 |
| Loop Quality Score (LQS) | weighted composite (test_coverage 0.25, req_cov 0.20, code_quality 0.20, efficiency 0.15, error_rate 0.10, doc_score 0.10) | AgentLoopSpec §9.2 |

### 3.7 Sub-Agent SLIs

| SLI | Metric | Source |
|---|---|---|
| Sub-agent success rate | \guinevere_subagent_duration_seconds{status=\"success\"}\ rate | ObsSpec §4.6 |
| File-output compliance | \guinevere_subagent_file_output_missing_total\ rate | ObsSpec §4.6 |
| Compliance score | \guinevere_subagent_compliance_score\ | ObsSpec §4.6 |

### 3.8 Infrastructure SLIs

| SLI | Metric | Source |
|---|---|---|
| CPU pressure | \guinevere_node_cpu_utilization_ratio\ | ObsSpec §4.3 |
| Memory pressure | \guinevere_node_memory_utilization_ratio\ | ObsSpec §4.3 |
| Disk pressure | \guinevere_node_disk_utilization_ratio\ | ObsSpec §4.3 |
| Network health | \guinevere_node_network_receive_bytes_total\ rate | ObsSpec §4.3 |

### 3.9 Database / Redis SLIs

| SLI | Metric | Source |
|---|---|---|
| PostgreSQL availability | \guinevere_postgres_connections_active\ vs max | ObsSpec §4.9 |
| PostgreSQL query latency | \guinevere_postgres_query_duration_seconds\ histogram | ObsSpec §4.9 |
| Redis memory pressure | \guinevere_redis_memory_utilization_ratio\ | ObsSpec §4.9 |
| Redis eviction rate | \guinevere_redis_key_evictions_total\ rate | ObsSpec §4.9 |
| Memory recall latency | \guinevere_memory_recall_duration_seconds\ histogram | ObsSpec §4.9 |

### 3.10 Security SLIs

| SLI | Metric | Source |
|---|---|---|
| Access denial rate | \guinevere_access_denied_total\ rate | ObsSpec §4.12 |
| Break-glass activation | \guinevere_break_glass_activations_total\ | ObsSpec §4.12 |
| Log redaction failure rate | \guinevere_log_redaction_failures_total\ rate | ObsSpec §4.12 |
| Public ingress detection | \guinevere_public_ingress_detected_total\ | ObsSpec §4.12 |


---

## 4. Custom Guinevere Metrics (from Technical Architecture v2.0 §8.2)

The TA also defines an initial metric schema:

| Metric | Type | Labels |
|---|---|---|
| \guinevere_task_completion_total\ | Counter | project, phase |
| \guinevere_mood_state\ | Gauge | value 0-5 |
| \guinevere_mommy_score\ | Gauge | per day |
| \guinevere_punishment_level\ | Gauge | current escalation |
| \guinevere_api_cost_total\ | Counter | provider, model |
| \guinevere_sub_agents_active\ | Gauge | current active |
| \guinevere_surveillance_events_total\ | Counter | source, type |
| \guinevere_memory_injection_tokens\ | Histogram | tokens per injection |
| \guinevere_llm_latency_seconds\ | Histogram | model, use_case |
| \guinevere_violation_total\ | Counter | violation_type |

**Note:** The Observability Spec supersedes and expands this list. The Observability Spec (§4) is the authoritative metrics catalog; TA §8.2 is the historical source.

---

## 5. SEV Policy (from Incident Response Runbook §3)

### 5.1 Core SEV Matrix

| Severity | Triage Deadline | Minimum Notification | Postmortem Required |
|---|---|---|---|
| SEV0 | Immediate | Immediate Discord + Gotify | Mandatory |
| SEV1 | <= 15 minutes | Urgent Discord + Gotify | Mandatory |
| SEV2 | <= 1 hour | Same-day Discord | Mandatory |
| SEV3 | <= 24 hours | Summary | If repeated |
| SEV4 | Next governance cycle | Review summary | Optional |

### 5.2 SEV Trigger Sources (by SEV level)

**SEV0 triggers:**
- Confirmed Critical data leak
- Active key compromise / active exfiltration
- Safe-word failure causing harm
- Destructive autonomous action
- Unrecoverable DB corruption
- Safe-word ignored during distress/crisis/harm (IRR §3.3)
- Public ingress detected (ObsSpec §8.3)

**SEV1 triggers:**
- Suspected key compromise / unauthorized Restricted/Critical access
- Major outage / backup restore failure
- Autonomous loop runaway
- Persona safety violation with distress
- Single confirmed safe-word hard-stop failure (IRR §3.3)
- Log redaction failure (ObsSpec §8.3)
- Secret access outside startup (ObsSpec §8.3)
- Break-glass active (ObsSpec §8.3)
- Surveillance redaction failure (ObsSpec §8.3)
- Yandere intensity in safe-mode (ObsSpec §8.3)
- Persona alert tone violation (ObsSpec §8.3)
- Sentry PII scrub failure (ObsSpec §8.3)
- Postgres unavailable (ObsSpec §8.3)

### 5.3 Alert Routing (from ObsSpec §8.1)

| Severity | Route | Evidence Required |
|---|---|---|
| SEV0 | Discord + Gotify urgent + evidence folder | Yes — incident folder required |
| SEV1 | Discord + Gotify urgent + evidence folder | Yes — incident folder required |
| SEV2 | Discord + evidence folder | Yes |
| SEV3 | Digest + dashboard review | Review artifact |
| SEV4 | Governance cycle | Drift report |


---

## 6. Evidence Paths

| Evidence Type | Path Pattern | Source |
|---|---|---|
| Incident evidence | \evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/\ | IRR §5 |
| Postmortem | \evidence/incidents/<YYYY-MM-DD>-<SEV>-<slug>/postmortem.md\ | IRR §5 |
| Monthly observability review | \evidence/observability/<YYYY-MM>-review.md\ | ObsSpec §14 |
| SLO scorecard (future) | \evidence/slo/<YYYY-MM>/\ | Context (user directive) |
| Drill evidence | \evidence/incidents/<date>-DRILL-<slug>/drill-report.md\ | IRR §10 |
| Backup/restore drill | Drill matrix evidence | IRR §10, Appendix E |
| Safe-word drill | Drill matrix DRILL-SAFE-001 | IRR Appendix E |

---

## 7. Safe-Word Safety Invariants (Zero Tolerance)

The following invariants are **absolute** and must be reflected as hard SLOs with **no meaningful error budget**:

| Invariant | SLO Target | Violation SEV | Source |
|---|---|---|---|
| Safe-word must trigger safe-mode transition | 100%% — any miss is SEV0 | SEV0 | ObsSpec §12, IRR §3.3 |
| Safe-word hard-stop failure | 0 occurrences | SEV1 per occurrence | IRR §7.4, ObsSpec §8.3 |
| Safe-word ignored during distress/crisis/harm | 0 occurrences | SEV0 | IRR §3.3 |
| Safe-word detection latency | < 1 second from input | Degraded -> SEV2 | ExtRef §8.2 |
| Raw safe-word content in alerts/metrics/logs | 0 occurrences | SEV1 per occurrence | ObsSpec §4.2, §5.2, §10 |
| Persona/yandere/punishment framing in alerts | 0 occurrences | SEV1 per occurrence | ObsSpec §8.3 |
| Yandere intensity during safe-mode | 0 (must be Y0) | SEV1 per occurrence | ObsSpec §4.8 |
| Punishment/violation record for safe-word event | 0 occurrences | SEV0/SEV1 | PersonaSafetyPolicy §7.2, IRR §3.3 |
| Alert tone violation (persona in alert) | 0 occurrences | SEV1 | ObsSpec §8.3 |

**Key Design Constraint:** Safe-word SLIs must NOT participate in error budget burn-down. The SLO spec must explicitly exempt safety invariants from error budget consumption. Any safe-word miss consumes zero budget — it triggers immediate incident.

---

## 8. Cost Budget References

| Reference | Detail | Source |
|---|---|---|
| API cost spike alert | SEV2/SEV3 depending on magnitude | ObsSpec §8.3 (GuinevereLLMCostSpike) |
| Cost freeze for non-essential work | Autonomous non-critical work must pause | Context (user directive) |
| Cost threshold encoding | Prometheus recording rules, not hardcoded | ExtRef §9.3 |
| Budget guardrails | Pause non-essential autonomous loops when anomaly | ExtRef §9.3 |
| Cost dimensions | LLM API (model, tokens, use_case), surveillance storage, VPS fixed | ExtRef §9.2 |
| Cost anomaly thresholds (external) | Daily cost > 2x 7d MA -> SEV3; > 3x baseline -> SEV2 | ExtRef §9.2 |
| Cost tracking metric | \guinevere_llm_cost_usd_total{model, purpose}\ | ObsSpec §4.7 |
| BRD cost requirement | Monitor dan optimize API cost autonomous | BRD §1.3 |
| Risk: API cost spike | MEDIUM probability, MEDIUM impact | BRD §6 |

**Design Note:** The cost budget must be distinct from the reliability error budget. Cost budget freeze is a separate control that pauses non-essential autonomous work when spend exceeds threshold. Reliability error budget covers availability/latency/quality misses.


---

## 9. Conflicts and Gaps

### 9.1 Conflicts

| ID | Conflict A | Conflict B | Resolution Required |
|---|---|---|---|
| C-001 | BRD §1.3: Uptime target 99.9%% | ObsSpec §12: Interim core service >= 99.0%% | SLO spec must decide: aspirational 99.9%% or operational 99.0%% (single-user, no revenue SLA) |
| C-002 | ExtRef §8.3: LLM availability target 99.5%% | ObsSpec §12: only core service availability has interim target | SLO spec must either adopt or reject external recommendation |
| C-003 | ExtRef §8.3: Surveillance ingestion availability 99.9%% | ObsSpec §12: no surveillance-specific interim target | SLO spec must define surveillance SLI/SLO |
| C-004 | AgentLoopSpec §9.2: LQS with 90%% threshold | No corresponding SLO in Observability Spec | SLO spec must decide if LQS is an official SLI or internal metric only |

### 9.2 Gaps

| ID | Gap | Impact | Required Action in SLO Spec |
|---|---|---|---|
| G-001 | No formal SLI specification document exists | SLIs are scattered across ObsSpec metrics catalog | SLO spec must define a formal SLI catalog with measurement windows |
| G-002 | No error budget calculation method defined | Cannot compute burn rates or remaining budget | SLO spec must define error budget math (monthly window, carryover policy) |
| G-003 | No burn-rate alert rules defined | Cannot alert on error budget consumption velocity | SLO spec must define burn-rate thresholds mapped to SEV levels |
| G-004 | No release gating based on error budget | Cannot prevent deployment when budget exhausted | SLO spec must define deployment freeze/rollback policy |
| G-005 | No multi-window SLO measurement (e.g., 30d + 7d) | Single window creates blind spots | SLO spec should define composite SLO windows |
| G-006 | No SLO scorecard dashboard defined | Monthly review lacks automated SLO scorecard | SLO spec must define scorecard panels + PromQL |
| G-007 | No cost budget / reliability budget separation | Risk of conflating two different control mechanisms | SLO spec must define distinct budgets for reliability vs cost |
| G-008 | Safe-word SLO not formally defined as 100%% with zero error budget | Risk of treating safe-word misses as consumable budget | SLO spec must explicitly exempt safety invariants from error budget |
| G-009 | No PromQL recording rules for any SLO computation | Cannot compute SLO attainment automatically | SLO spec must define PromQL recording rules per SLI |
| G-010 | No dashboard-as-code files exist (Grafana JSON/Terraform) | SLO scorecard panels cannot be provisioned | SLO spec must specify scorecard dashboard layout; implementation deferred |
| G-011 | OBS-BG-001: Final SLO thresholds not formally approved | Alert thresholds remain interim | SLO spec must be the approval vehicle for all final thresholds |
| G-012 | No SLO for sub-agent compliance or loop quality | Agent loop health not measured as SLO | SLO spec must decide which loop/sub-agent metrics become SLIs |
| G-013 | No notification SLA defined per channel | Cannot measure if Discord/Gotify/email meets delivery SLAs | SLO spec should define notification delivery SLAs |
| G-014 | No evidence SLO (evidence completeness, timeliness) | Evidence compliance is measured but not SLO-gated | SLO spec should consider evidence SLI |


---

## 10. Evidence Path Standard for SLO

Per user directive and context, the SLO evidence root path must be:

\\\
evidence/slo/<YYYY-MM>/
\\\

Suggested evidence files per month:

| File | Purpose |
|---|---|
| \evidence/slo/<YYYY-MM>/scorecard.md\ | Monthly SLO attainment, budget consumed, burn rate summary |
| \evidence/slo/<YYYY-MM>/exceptions.yaml\ | SLO misses with explanations and action items |
| \evidence/slo/<YYYY-MM>/review-notes.md\ | Monthly review notes (may be symlink to observability review) |

---

## 11. PromQL Recording Rule Candidates

High-priority recording rules the SLO spec should define:

\\\promql
# Core service SLO attainment (30d window)
guinevere:slo_core_availability:ratio_30d
  = sum(guinevere_health_check_state{status="up"})
    / count(guinevere_health_check_state)

# LLM success SLO attainment
guinevere:slo_llm_success:ratio_30d
  = sum(rate(guinevere_llm_requests_total{status="success"}[30d]))
    / sum(rate(guinevere_llm_requests_total[30d]))

# Safe-word enforcement SLO (absolute)
guinevere:slo_safeword_enforcement:total_30d
  = sum(increase(guinevere_safe_word_events_total{outcome="bypass_detected"}[30d]))

# Error budget remaining (example: 99%% SLO, monthly)
guinevere:error_budget_remaining:ratio
  = 1 - (
      sum(rate(guinevere_http_requests_total{status=~"5.."}[30d]))
      / sum(rate(guinevere_http_requests_total[30d]))
    ) / (1 - 0.99)

# Burn rate (5m window, example)
guinevere:burn_rate:5m
  = (
      sum(rate(guinevere_http_requests_total{status=~"5.."}[5m]))
      / sum(rate(guinevere_http_requests_total[5m]))
    ) / (1 - 0.99)
\\\

---

## 12. Dashboard-as-Code Catalog (SLO Scorecard Panels)

The existing dashboard catalog (ObsSpec §9.2) must be extended with an SLO scorecard dashboard:

| Panel | Source PromQL | Type |
|---|---|---|
| SLO attainment (all SLIs) | Scorecard table with status icons | Table |
| Error budget remaining %% | \guinevere:error_budget_remaining:ratio\ | Gauge |
| Burn rate (5m/30m/1h) | \guinevere:burn_rate:5m\ / \:30m\ / \:1h\ | Stat |
| Safe-word enforcement SLO | Count of bypass events (must be 0) | Stat (red if >0) |
| Cost budget burn (month-to-date) | \sum(increase(guinevere_llm_cost_usd_total[30d]))\ | Stat |
| SLO trend (trailing 12 months) | Monthly attainment bars | Bar chart |
| Active SLO misses | Alerts where SLI < SLO threshold | Alert list |


---

## 13. Final Checklist for SLO/SLA/Error Budget Spec Author

### Pre-requisite Checks
- [ ] Read all 6 foundation docs referenced in this source map
- [ ] Read this source map in full
- [ ] Read \esearch-reports/2026-05-30-observability-external-references.md\ §8 (Google SRE patterns)
- [ ] Confirm ADR-036 number is still available in ADR Index / adr/README.md

### Authority & Scope
- [ ] Declare normative child relationship: Observability Spec + Incident Response Runbook + ADR-017
- [ ] Define internal-only SLA (no public/commercial claim per context)
- [ ] State that reliability/safety/SLO policy always wins over persona/yandere
- [ ] Declare zero error budget for hard safety invariants (safe-word, distress)
- [ ] Define cost budget freeze as separate control from reliability error budget

### SLI Catalog
- [ ] Define formal SLI for each service surface (core, llm, safety, surveillance, backup, loop, sub-agent, infra, db, security)
- [ ] Specify measurement window per SLI (30d primary, 7d secondary for burn rate)
- [ ] Specify measurement method: Prometheus, Loki, or composite
- [ ] Define PromQL recording rules for every SLI
- [ ] Define label allow/deny lists for SLO-related queries (inherit from ObsSpec §4.2)

### SLO Targets
- [ ] Reconcile BRD 99.9%% vs ObsSpec 99.0%% core service target -> decide final number
- [ ] Define LLM/9Router SLO target (adopt/reject ExtRef's 99.5%%)
- [ ] Define surveillance ingestion SLO target (adopt/reject ExtRef's 99.9%%)
- [ ] Define safe-word enforcement SLO = 100%%, zero error budget
- [ ] Define backup freshness SLO (align with RPO from TA §9.2)
- [ ] Define alert delivery SLO (SEV0 immediate, SEV1 <=15min, etc.)
- [ ] Define loop completion SLO (if any; consider LQS)
- [ ] Define evidence compliance SLO (if any)
- [ ] Define log redaction SLO = 100%%, zero error budget
- [ ] Define dashboard-as-code provisioning SLO
- [ ] Define cost budget freeze threshold

### Error Budget Policy
- [ ] Define error budget calculation: monthly window, (1 - SLO) x total events
- [ ] Define carryover/no-carryover policy between months
- [ ] Define safe-word invariants as exempt from error budget
- [ ] Define burn-rate alert thresholds mapped to SEV levels (adopt ExtRef: >10x 30min -> SEV2, >100x 5min -> SEV1)
- [ ] Define release gating: deployment blocked when error budget exhausted
- [ ] Define cost budget freeze: trigger, scope, duration, thaw conditions

### Alert Rules (Prometheus / Alertmanager)
- [ ] Define burn-rate alert rules for each SLI with severity mapping
- [ ] Define SLO attainment breach alert (SLI below SLO at window end)
- [ ] Define safe-word miss alert (count > 0 = SEV0)
- [ ] Define cost budget freeze alert (spend exceeds freeze threshold)
- [ ] Ensure alert tone is neutral incident-command (inherit from ObsSpec §2.2)
- [ ] Ensure no raw sensitive data in alert labels or bodies

### Dashboard-as-Code
- [ ] Define SLO scorecard dashboard layout (panels, queries, refresh)
- [ ] Specify file path in \monitoring/grafana/dashboards/guinevere-slo-scorecard.json\
- [ ] Inherit access controls from ObsSpec (Samm + observability-reader)

### Evidence Path
- [ ] Set evidence root: \evidence/slo/<YYYY-MM>/\
- [ ] Define monthly scorecard template (scorecard.md, exceptions.yaml, review-notes.md)
- [ ] Align monthly SLO review cadence with existing monthly observability review (ObsSpec §14)

### Normative Cross-References
- [ ] Cross-reference every SLI to its source metric in Observability Spec
- [ ] Cross-reference every SEV level to Incident Response Runbook severity matrix
- [ ] Cross-reference every SLO target to BRD business objective
- [ ] Cross-reference cost budget to FinOps/cost anomaly patterns
- [ ] Cross-reference evidence path to existing evidence standards

### Normative &quot;Must&quot; vs &quot;Should&quot; Compliance
Per context: &quot;all controls must, zero should&quot; — the SLO spec must use MUST language for:
- All SLO targets (MUST)
- All error budget calculations (MUST)
- All safe-word invariants (MUST, zero budget)
- All burn-rate alerts (MUST)
- All cost freeze controls (MUST)
- All evidence artifacts (MUST)
- All PromQL recording rules (MUST specify)
- All dashboards (MUST be dashboard-as-code)


---

## Appendix A — Existing Alert Catalog Quick Reference

From Observability Spec §8.3 (20 alert rules):

| Alert | Severity | Safe-Word Related | Cost Related | Has PromQL? |
|---|---|---|---|---|
| GuinevereServiceDown | SEV1/SEV2 | No | No | No (spec only) |
| GuineverePublicIngressDetected | SEV0 | No | No | No |
| GuinevereSafeWordBypassDetected | SEV0 | **Yes** | No | No |
| GuineverePersonaAlertToneViolation | SEV1 | **Yes** | No | No |
| GuinevereYandereIntensitySafeModeViolation | SEV1 | **Yes** | No | No |
| GuinevereLogRedactionFailure | SEV1 | No | No | No |
| GuinevereSecretAccessOutsideStartup | SEV1 | No | No | No |
| GuinevereBreakGlassActive | SEV1 | No | No | No |
| GuinevereBackupFailure | SEV1/SEV2 | No | No | No |
| GuinevereRestoreDrillOverdue | SEV3 | No | No | No |
| GuinevereLoopRunaway | SEV1 | No | No | No |
| GuinevereSubagentFileOutputMissing | SEV2 | No | No | No |
| GuinevereLLMCostSpike | SEV2/SEV3 | No | **Yes** | No |
| GuinevereLLMLatencyDegraded | SEV3 | No | No | No |
| GuinevereSurveillanceIngestionStopped | SEV2 | No | No | No |
| GuinevereSurveillanceRedactionFailure | SEV1 | No | No | No |
| GuineverePostgresUnavailable | SEV1 | No | No | No |
| GuinevereRedisUnavailable | SEV2 | No | No | No |
| GuinevereSentryPIIScrubFailure | SEV1 | No | No | No |
| GuinevereDashboardProvisioningDrift | SEV4 | No | No | No |

**Note:** 0 of 20 alerts currently have concrete PromQL expressions. The SLO spec must define PromQL for burn-rate and SLO-attainment alerts.

---

## Appendix B — ADR Index Reference

From \Guinevere_ADR_Index_v1.0.md\ line 112 and \dr/README.md\ line 114:

\\\
ADR-036 SLO/SLA/Error Budget Policy  —  Backlog  —  Proposed
\\\

The ADR for this spec is numbered **036** and is in the backlog. The SLO spec author should create ADR-036 either as part of the spec or as a companion decision record.

---

## Appendix C — Context Constraints from Operator

| Constraint | Detail |
|---|---|
| Final spec status | Accepted (not Draft/Proposed) |
| SLA type | Internal only — no public/commercial claim |
| Policy precedence | Reliability/safety/SLO policy always wins over persona/yandere |
| Safe-word SLO | 100%%, zero tolerance, any miss = SEV0/SEV1 |
| Safety invariants | No meaningful error budget for hard safety invariants |
| Cost budget freeze | Freeze autonomous non-critical work when cost threshold exceeded |
| Evidence path | \evidence/slo/<YYYY-MM>/\ |
| Root path | \C:\Users\faizz\guinevere\ |
| Language | All controls must use &quot;must&quot; (RFC 2119), zero &quot;should&quot; |
| Normative parents | Observability Spec + Incident Response Runbook + ADR-017 |
| PromQL | Concrete PromQL per SLI |
| Dashboard | Dashboard-as-code catalog |
| Reporting | Monthly SLO scorecard |

---

**End of Source Requirements Map — Guinevere SLO/SLA/Error Budget Specification**

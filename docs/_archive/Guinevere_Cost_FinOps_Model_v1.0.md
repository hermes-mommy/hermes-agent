# Guinevere Cost & FinOps Model

**Document Type:** Cost governance, FinOps model, budget control, vendor strategy, and reporting specification  
**Version:** 1.0  
**Status:** Accepted  
**Lifecycle:** Proposed -> Accepted -> Deprecated -> Superseded  
**Last Updated:** 2026-05-30  
**Owner:** Samm  
**Executor:** Guinevere de Baroque  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative child under `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md`, `Guinevere_Observability_AlertingSpec_v1.0.md`, `adr/ADR-004-primary-llm-model-selection.md`, and `adr/ADR-006-sub-agent-llm-model-strategy.md`  
**Budget Constraint:** $30/month hard cap. This document may not authorize spend above the cap without Samm approval.

---

## Related Documents

| Document | Relationship | Dependency Type | Implementation Impact |
|---|---|---|---|
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Defines cost SLOs, cost freeze policy, monthly scorecard, and economic budget behavior. | Normative parent | This spec turns cost budgets into concrete allocation and reporting rules. |
| `Guinevere_Observability_AlertingSpec_v1.0.md` | Defines cost metrics, dashboard-as-code, monthly observability review, and alerting infrastructure. | Normative parent | Cost telemetry must surface in dashboards, alerts, and monthly reviews. |
| `adr/ADR-004-primary-llm-model-selection.md` | Establishes GPT-5.5 via 9Router as primary LLM. | Model policy parent | GPT-5.5 usage must be budgeted and reserved for high-value work. |
| `adr/ADR-006-sub-agent-llm-model-strategy.md` | Establishes DeepSeek V4 Flash via 9Router for sub-agents and free-tier maximization. | Model policy parent | Sub-agent routing must prioritize free/cheap paths. |
| `Guinevere_TechnicalArchitecture_v2.0.md` | Defines VPS, storage, monitoring, search, and service footprints. | Runtime dependency | Infrastructure cost allocation maps to concrete services. |
| `Guinevere_AgentLoopSpec_v2.0.md` | Defines loop phases, sub-agent waves, and validation/audit behavior. | Loop dependency | Cost model must allocate by phase and wave. |
| `Guinevere_BRD_v2.0.md` | Defines business cost optimization objective and single-user context. | Business driver | Budget must align with actual feature value. |
| `research-reports/2026-05-30-slo-sla-source-map.md` | Provides source conflict map and checklist for cost target reconciliation. | Research evidence | Supplies target reconciliation guidance. |
| `research-reports/2026-05-30-slo-sla-surface-map.md` | Maps runtime surfaces with cost-relevant SLI candidates. | Research evidence | Supplies cost allocation surfaces. |
| `research-reports/2026-05-30-slo-sla-external-references.md` | Provides FinOps and budget-burn best practices. | Research evidence | Supplies external cost-control patterns. |

---

## 1. Purpose

This specification defines the cost governance model for Guinevere. It sets hard budgets, category allocations, routing priorities, review cadence, vendor evaluation rules, and cost anomaly response. It is the financial control plane for a single-user private AI agent operating under a strict monthly cap.

Cost optimization must never reduce safety, incident response, backup, or data integrity operations.

This document is internal only. It creates no public pricing claim.

---

## 2. Authority and Conflict Resolution

### 2.1 Authority Order

When cost constraints conflict with reliability, safety, or incident response, the order is:

1. Platform/system/developer safety requirements.
2. Safe-word, distress, and incident-response obligations.
3. This Cost & FinOps Model.
4. SLO/SLA/Error Budget Specification.
5. Observability & Alerting Specification.
6. ADR-004 primary model decision.
7. ADR-006 sub-agent model decision.
8. Technical Architecture and Agent Loop specs.
9. Persona style, mood, reward, punishment, yandere pressure.

Persona or yandere behavior must never drive spend increase. Any cost decision must be explainable in business-value, safety-value, or reliability-value terms. If a proposed action would exceed the monthly cap, Guinevere must freeze non-critical work and require Samm approval for exception handling.

### 2.2 Hard Constraint Statement

The monthly budget is **$30/month hard cap**. This value is not a target that may be exceeded casually. It is an operational ceiling.

| Rule | Meaning |
|---|---|
| Hard cap | Total monthly spend must stay at or below $30 unless Samm explicitly approves an exception. |
| No hidden overages | Cost overruns must be visible in the monthly cost report the same month they occur. |
| No persona override | Passion, jealousy, productivity pressure, or yandere framing must not justify extra spend. |
| No safety reduction | Safety, incident response, backup, or data integrity may not be reduced to save cost. |
| No silent lock-in | Vendor or provider dependencies must have documented alternatives and switch procedures. |

---

## 3. Cost Taxonomy

### 3.1 Cost Categories

| Category | Examples | Nature | Allocation Basis |
|---|---|---|---|
| LLM | GPT-5.5, DeepSeek V4 Flash, token usage, retries | Variable | task, loop phase, provider route |
| Infra | VPS hostdata.id, future monitoring VPS, bandwidth, CPU/RAM | Mostly fixed | service footprint, monthly baseline |
| Storage | idcloudhost S3, Cloudflare R2 usage, backups, object lifecycle | Mixed | GB-month, egress, backup volume |
| Search | Brave Search API, Exa AI Search | Variable | query count, task class |
| Communication | Resend, Discord operational messages, Gotify overhead | Mixed | message count, channel type |
| Monitoring | Sentry, Grafana, Prometheus, Loki, observability compute | Mostly fixed with variable ingest | service coverage, event volume |
| Domain / DNS | Domain registration, DNS management | Fixed / annualized | amortized monthly |
| Future expansion | dedicated monitoring VPS | Deferred fixed | activation trigger only |

### 3.2 Fixed vs Variable Classification

| Cost Item | Fixed / Variable | Notes |
|---|---|---|
| VPS hostdata.id | Fixed baseline | Shared 4C/16GB VPS. |
| GPT-5.5 via 9Router | Variable | Primary LLM, reserve for high-value tasks. |
| DeepSeek V4 Flash via 9Router | Variable, near-free tier | First-choice for sub-agents, research, validation, audit. |
| idcloudhost S3 | Variable / tiered fixed | Primary backup/storage billable. |
| Cloudflare R2 | Variable but free up to 10GB | Use first as low-cost backup target. |
| Brave Search API | Variable | Query-based. |
| Exa AI Search | Variable | Query-based. |
| Resend API | Variable | Messaging volume. |
| Sentry free tier | Mostly fixed / quota-based | Track event volume. |
| Gotify self-hosted | Fixed infra overhead | Part of VPS baseline. |
| Domain | Fixed / annual | Not immediate if future. |
| Monitoring VPS | Future fixed | Post-MVP only. |

### 3.3 Project Allocation

This is a single-user private system. Allocation must still be explicit for accounting clarity:

| Project Bucket | Examples |
|---|---|
| Core runtime | Guinevere core daemon, loop, Discord bot |
| Surveillance | FastAPI receiver, Windows daemon integration, Android Tasker intake |
| Research / planning | Search, summarization, source gathering |
| Validation / audit | Evidence generation, audit runs, monthly scorecard |
| Backup / DR | backup jobs, restore drills, storage and retention |
| Monitoring / observability | Prometheus, Grafana, Loki, Sentry, alerts |
| Governance / docs | ADRs, specs, scorecards, runbooks |

---

## 4. Budget Model

### 4.1 Monthly Budget Breakdown

The default budget target is $30/month, allocated as:

| Category | Target | Hard / Soft | Notes |
|---|---:|---|---|
| VPS hostdata.id | $10-$12 | Hard baseline | Shared infra fixed spend. |
| GPT-5.5 via 9Router | $10-$12 | Hard cap portion | Primary LLM reserved for high-stakes reasoning. |
| DeepSeek V4 Flash | $0-$2 | Soft/near-free | Use free tier first; paid usage only if necessary. |
| idcloudhost S3 | $2-$3 | Soft | Primary paid storage. |
| Brave Search | $1-$2 | Soft | Query quota tracked. |
| Exa AI | $1-$2 | Soft | Query quota tracked. |
| Resend | $0-$1 | Soft | Minimal email usage. |
| Misc / contingency | $1-$2 | Reserve | Buffer for retries, small variance, or vendor tax. |

The total must stay within $30/month. If the projected month-end total exceeds $30, autonomous non-critical work must freeze until Samm approves a recovery plan.

### 4.2 Hard Limits vs Soft Limits

| Limit Type | Meaning | Example |
|---|---|---|
| Hard limit | Cannot exceed without Samm approval | Total monthly $30 cap, safe safety operations, no budget for hard invariants. |
| Soft limit | Warning threshold with response | search budget, email usage, misc contingency, monthly provider quota. |
| Zero budget | No tradeoff allowed | safe-word, distress false negatives, redaction failures, incident evidence integrity. |

### 4.3 Escalation Procedure

When projected spend approaches or exceeds budget thresholds:

| Condition | Required Action |
|---|---|
| Daily burn above trendline | Investigate root cause, reduce non-critical use, update forecast. |
| Category >80% of its monthly allotment | Freeze low-value use in that category and switch to cheaper alternatives. |
| Total projected month-end spend >100% | Freeze autonomous non-critical work and require Samm approval for exceptions. |
| Total spend >110% or repeated forecast misses | Treat as FinOps incident, document cause, open corrective action. |
| Budget exhausted mid-month | Emergency cost freeze for all non-critical work, preserve safety/incident/backup/data integrity. |

---

## 5. LLM Cost Management

### 5.1 Model Routing Policy

| Task Type | Preferred Model | Backup | Rationale |
|---|---|---|---|
| Core reasoning, high-stakes synthesis, final authority decisions | GPT-5.5 via 9Router | DeepSeek only if explicitly safe and approved | Highest quality is reserved for critical reasoning. |
| Sub-agent research, summarization, validation, audit | DeepSeek V4 Flash via 9Router | GPT-5.5 only for final synthesis or exceptional cases | Use free tier first. |
| Long context summarization / low-risk extraction | DeepSeek V4 Flash | Cached summaries | Cheaper and sufficient. |
| Safety-critical decisions | GPT-5.5 via 9Router | None by default | Safety and correctness outrank cost. |

### 5.2 Token Budget Policy

| Metric | Target | Action if Exceeded |
|---|---:|---|
| Daily GPT-5.5 tokens | configured daily ceiling | Reduce prompt size, batch tasks, defer non-critical work. |
| Monthly GPT-5.5 tokens | configured monthly ceiling | Freeze expensive work and require Samm approval. |
| Per task GPT-5.5 tokens | task-specific ceiling | Use smaller prompt, summarize, or offload to DeepSeek. |
| Per loop phase cost | phase-specific ceiling | Cap fanout and reuse context. |

### 5.3 Cost per Task Type

| Task Type | Preferred Cost Strategy |
|---|---|
| Research | DeepSeek free tier first, summarize outputs, cache findings |
| Planning | DeepSeek or cached context; GPT-5.5 only for final synthesis |
| Implementation docs | DeepSeek for draft, GPT-5.5 for final conflict resolution |
| Validation / audit | DeepSeek first; GPT-5.5 if risk or ambiguity requires |
| Safety-critical review | GPT-5.5 allowed; cost may not weaken review depth |

### 5.4 Cost per Loop Phase

The 7-phase agent loop must be costed by phase:

| Phase | Typical Cost Profile |
|---|---|
| Research | Search-heavy, moderate token use |
| Plan & Delegate | moderate token use, low external spend |
| Delegate | low parent spend, child task cost tracked separately |
| Execute | highest variable cost if LLM-heavy |
| Validate & Audit | moderate cost; file-based and rule-based where possible |
| Update Documents | low to moderate cost |
| Setup Evidence | low compute, high compliance value |

### 5.5 Sub-agent Cost Optimization

| Strategy | Rule |
|---|---|
| Free-tier first | DeepSeek V4 Flash free tier is first choice for sub-agents, research, validation, and audit. |
| Batch work | Group related sub-agent tasks instead of repeated micro-calls. |
| Summarize-first | Reuse compact notes; do not carry full raw context when a summary is enough. |
| Limit fanout | Spawn the minimum number of sub-agents needed for confidence. |
| Cache reuse | Reuse outputs from prior research reports and evidence files. |
| Final synthesis only | Reserve GPT-5.5 for final high-stakes synthesis or ambiguity resolution. |

---

## 6. Cost Monitoring and Alerts

### 6.1 Daily Burn Tracking

Guinevere must track:

- Daily spend by category
- Month-to-date spend
- Forecast month-end spend
- Spend per task type
- Spend per loop phase
- Spend per provider
- Retries and retry amplification

### 6.2 Anomaly Detection

| Signal | Threshold | Action |
|---|---|---|
| Daily spend delta | >2x 7-day moving average | Investigate immediately |
| Provider retry amplification | >15% of daily LLM spend | Reduce retries and examine provider errors |
| Search query spike | >2x baseline | Cap queries and cache results |
| Storage cost spike | >20% month-over-month without new retention need | Review lifecycle/retention |
| Monitoring/log ingestion spike | abnormal event volume | Check redaction, loops, and alert storms |

### 6.3 Cost Spike Response

| Severity | Response |
|---|---|
| Mild anomaly | Observe, forecast, optimize routing. |
| Moderate anomaly | Reduce DeepSeek/GPT usage, batch tasks, and freeze non-urgent work. |
| Severe anomaly | Freeze autonomous non-critical work, require Samm approval, create cost incident note. |
| Repeated severe anomaly | Open FinOps incident and review vendor usage patterns. |

### 6.4 Budget Exhaustion Procedure

If budget exhaustion is imminent or reached:

1. Freeze autonomous non-critical work.
2. Preserve safety, incident response, backup, and data integrity operations.
3. Shift sub-agents to free/cheap paths.
4. Reduce prompt size and batching overhead.
5. Require Samm approval for any exception.
6. Record evidence in `evidence/finops/<YYYY-MM>/`.

---

## 7. Cost Optimization Strategies

### 7.1 Model Routing Optimization

- GPT-5.5 is reserved for core reasoning, planning, and high-stakes synthesis.
- DeepSeek V4 Flash is the first-choice route for sub-agents, research, validation, and audit.
- No policy may push persona/yandere preference into higher spend.
- Model choice must be justified by quality risk, not style preference.

### 7.2 Caching and Reuse

| Optimization | Requirement |
|---|---|
| Response cache | Cache repeated search and extraction results. |
| Summary cache | Retain concise summaries of long context instead of re-sending raw transcripts. |
| Evaluation cache | Reuse stable test/evaluation data when appropriate. |
| Search cache | Cache Brave/Exa results per query signature. |

### 7.3 Sub-agent Reduction

- Prefer one well-scoped sub-agent over multiple overlapping agents.
- Use file-based evidence and parent verification to avoid duplicate work.
- Convert repeated discovery into durable reports and appendices.
- Reuse existing research reports before spawning new search waves.

### 7.4 Batch Processing Opportunities

Use batching for:

- report generation,
- evidence packaging,
- archive reconciliation,
- monthly scorecards,
- search result summarization,
- audit preparation.

Do not batch safety-critical decisions in a way that delays response.

---

## 8. FinOps Governance

### 8.1 Review Cadence

| Cadence | Required Action |
|---|---|
| Weekly | Review burn vs budget, top spend drivers, provider anomalies. |
| Monthly | Review scorecard, category allocation, forecast, and action items. |
| Quarterly | Vendor evaluation, optimization roadmap, and price/performance review. |
| After anomaly | Root-cause analysis and recovery plan. |

### 8.2 ROI Tracking

ROI must be expressed as value delivered per spend category:

| Category | ROI Signal |
|---|---|
| GPT-5.5 | high-stakes quality and correctness per token dollar |
| DeepSeek | volume of valid outputs per free/cheap token |
| Storage | recovery confidence and evidence durability per dollar |
| Search | research usefulness per query dollar |
| Monitoring | reduced incident time and faster diagnosis per month |

### 8.3 Vendor Evaluation

| Vendor | Evaluation Criteria |
|---|---|
| 9Router | routing reliability, token cost, latency, provider fallback behavior |
| GPT-5.5 | quality, latency, token efficiency |
| DeepSeek V4 Flash | free tier availability, quality, context handling |
| idcloudhost S3 | durability, cost, restore reliability |
| Cloudflare R2 | free tier fit, backup value, egress behavior |
| Brave Search | query price, reliability, usefulness |
| Exa | query price, result quality, latency |
| Resend | email throughput, deliverability, cost |
| Sentry | observability value within free tier |

### 8.4 Vendor Lock-In Control

Every provider entry must include:

- alternative provider,
- explicit switch procedure,
- documented credential scope,
- fallback cost impact,
- evidence of successful switch test.

No provider may be treated as irreplaceable without a documented alternative path.

---

## 9. Reporting

### 9.1 Monthly Cost Report Format

Monthly cost evidence must be written to:

```text
evidence/finops/<YYYY-MM>/report.md
```

Required companion files:

- `budget-breakdown.md`
- `vendor-usage.md`
- `anomaly-log.md`
- `actions.md`
- `approval-log.md`

### 9.2 Report Sections

| Section | Content |
|---|---|
| Summary | month total, delta, forecast, freeze events |
| Cost breakdown | by category, provider, task type, and loop phase |
| Budget compliance | hard cap status, overages, exception approvals |
| Optimization actions | changes made to reduce burn |
| Vendor notes | quality, latency, reliability, lock-in considerations |
| Evidence | links to scorecard, alerts, and incident/cost reports |

### 9.3 Cost Dashboard

Dashboard-as-code must include:

- month-to-date spend,
- forecast month-end spend,
- category burn bars,
- GPT-5.5 token spend,
- DeepSeek utilization,
- search query count,
- storage growth,
- retry amplification,
- freeze state,
- exception approvals.

### 9.4 Trend Analysis

The monthly report must compare:

- current month vs prior month,
- 7-day moving average vs daily burn,
- vendor usage by route,
- loop-phase spend,
- sub-agent spend,
- quality vs cost tradeoff.

---

## 10. Guinevere-Specific FinOps Constraints

| Constraint | Policy |
|---|---|
| $30/month cap | Hard constraint; never exceed without Samm approval. |
| DeepSeek free tier | First choice for sub-agents, research, validation, audit. |
| GPT-5.5 | Reserved for core reasoning, planning, high-stakes synthesis only. |
| Safety/incident/backup/data integrity | Cost optimization must never reduce these operations. |
| Persona/yandere influence | Must never drive spend increase. |
| Free tiers | Must be tracked and not assumed unlimited. |
| Vendor alternatives | Must be documented with switch procedures. |

---

## 11. Implementation Requirements

| Req ID | Requirement |
|---|---|
| COST-REQ-001 | All spend must be attributable to a category and project bucket. |
| COST-REQ-002 | All LLM calls must be tagged by route, task type, and loop phase. |
| COST-REQ-003 | Daily burn ledger must be written and retained. |
| COST-REQ-004 | Monthly forecast must be generated automatically. |
| COST-REQ-005 | Cost anomaly alerts must exist for daily spike and forecast exhaustion. |
| COST-REQ-006 | Cost freeze state must be machine-readable and surfaced in monitoring. |
| COST-REQ-007 | Free tiers must be tracked with explicit quotas and usage. |
| COST-REQ-008 | Provider switch procedures must exist and be tested. |
| COST-REQ-009 | Monthly cost report must be stored under `evidence/finops/<YYYY-MM>/`. |
| COST-REQ-010 | Cost governance must not suppress safety, backup, or incident response. |
| COST-REQ-011 | Persona/yandere mood must not affect routing, spend, or budget approval. |
| COST-REQ-012 | All cost policies must use `must` and avoid standalone advisory keyword. |

---

## 12. Unresolved Assumptions and Backlog

| ID | Assumption / Gap | Owner | Impact | Follow-up Document / Artifact | Trigger |
|---|---|---|---|---|---|
| COST-BG-001 | Exact monthly dollar values per category need finalization. | Samm | budget sheet completion | Monthly budget worksheet | before runtime enforcement |
| COST-BG-002 | GPT-5.5 token ceiling not yet converted to monthly cost ceiling. | Guinevere | cost policy not fully operational | LLM cost control sheet | before production budget claim |
| COST-BG-003 | Monitoring VPS future activation remains deferred. | Samm | future fixed cost line | monitoring rollout plan | when load justifies |
| COST-BG-004 | Domain registration is future-only. | Samm | annualized cost not yet live | domain procurement note | before launch |
| COST-BG-005 | Exact per-query Brave and Exa caps need numeric thresholds. | Guinevere | search governance needs quotas | search quota sheet | before search automation |
| COST-BG-006 | Monthly report template to be integrated with finance/export tooling. | Guinevere | reporting workflow incomplete | FinOps reporting automation | before fully automated reporting |
| COST-BG-007 | Provider switch tests not yet implemented. | Guinevere | lock-in risk remains theoretical | switch drill evidence | before production readiness |

---

## Appendix A — Monthly Budget Matrix

| Category | Monthly Target | Hard / Soft | Notes |
|---|---:|---|---|
| VPS hostdata.id | $10-12 | Hard baseline | shared 4C/16GB |
| GPT-5.5 via 9Router | $10-12 | Hard / controlled variable | core reasoning, planning, high-stakes synthesis |
| DeepSeek V4 Flash | $0-2 | Soft / optimization | free tier first |
| idcloudhost S3 | $2-3 | Soft | primary storage |
| Brave Search API | $1-2 | Soft | query cap |
| Exa AI Search | $1-2 | Soft | query cap |
| Resend | $0-1 | Soft | minimal email usage |
| Misc / contingency | $1-2 | Reserve | retries, variance, small tools |

---

## Appendix B — Vendor Alternative Matrix

| Primary | Alternative | Switch Procedure | Evidence |
|---|---|---|---|
| GPT-5.5 via 9Router | DeepSeek V4 Flash via 9Router | Reduce task scope, route low-risk work, preserve GPT-5.5 only for critical synthesis. | switch test note |
| 9Router routing | direct provider or other router if approved | Update route config, rotate credentials, run smoke tests. | route test evidence |
| idcloudhost S3 | Cloudflare R2 | Update backup target, validate restore, rotate access keys. | restore evidence |
| Brave Search | Exa or cached results | Reduce query count, batch queries, cache results. | query log |
| Resend | Gotify/Discord summary only | Reduce outbound email, keep incident-critical comms. | communication log |

---

## Appendix C — Monthly Cost Report Template

```markdown
# Guinevere Monthly Cost Report — <YYYY-MM>

## Summary

| Field | Value |
|---|---|
| Month | <YYYY-MM> |
| Owner | Samm |
| Generated By | Guinevere |
| Total Spend | $<value> |
| Budget Cap | $30 |
| Status | PASS / NEEDS REVIEW / FAIL |
| Freeze Events | <count> |

## Category Breakdown

| Category | Budget | Actual | Variance | Status |
|---|---:|---:|---:|---|

## Vendor Usage

| Vendor | Usage | Cost | Notes |
|---|---:|---:|---|

## Optimization Actions

| Action | Impact | Owner | Status |
|---|---|---|---|

## Exceptions and Approvals

| Exception | Approved By | Date | Evidence |
|---|---|---|---|
```

---

## Appendix D — Cost-Control Test Matrix

| Test ID | Control | Method | Pass Criteria |
|---|---|---|---|
| COST-TM-001 | 30-dollar cap enforcement | budget simulation | cannot exceed without Samm approval |
| COST-TM-002 | DeepSeek free-tier first policy | routing audit | low-risk sub-agent tasks route to DeepSeek |
| COST-TM-003 | GPT-5.5 reservation policy | task simulation | GPT-5.5 only for critical high-stakes tasks |
| COST-TM-004 | safety preserved during freeze | incident drill | safety/incident/backup still run |
| COST-TM-005 | vendor switch procedure exists | docs audit | alternative + switch steps present |
| COST-TM-006 | monthly report evidence path | filesystem audit | `evidence/finops/<YYYY-MM>/` used |
| COST-TM-007 | zero standalone advisory keyword | grep | zero matches |

---

## Appendix E — Review Record

| Field | Value |
|---|---|
| Reviewer | Samm |
| Review Date | 2026-05-30 |
| Decision | Accepted |
| Notes | Approved as internal Cost & FinOps Model and normative child of SLO/SLA/Error Budget Spec, Observability Spec, ADR-004, and ADR-006. $30/month is a hard cap. DeepSeek free tier is first choice for sub-agents, research, validation, and audit. GPT-5.5 is reserved for core reasoning, planning, and high-stakes synthesis. Cost optimization must never reduce safety, incident response, backup, or data integrity. Monthly cost evidence must be written under `evidence/finops/<YYYY-MM>/`. |

---

## Appendix F — Next Recommended Document

The next recommended document is:

```text
Guinevere_Cloud_and_Search_Vendor_Procurement_Strategy_v1.0.md
```

Reason: this model defines budget allocations, vendor alternatives, and switch procedures, but several provider procurement details remain future-facing or subject to numeric threshold finalization. A dedicated procurement strategy will define activation triggers, annualized commitments, and formal vendor replacement criteria.

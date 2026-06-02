# Guinevere Cost & FinOps Model

**Document Type:** Cost governance, FinOps model, budget control, vendor strategy, and reporting specification  
**Version:** 1.1  
**Status:** Accepted  
**Lifecycle:** Proposed -> Accepted -> Deprecated -> Superseded  
**Last Updated:** 2026-05-31  
**Owner:** Faiz  
**Executor:** Guinevere de Baroque  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Authority:** Normative child under `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md`, `Guinevere_Observability_AlertingSpec_v1.0.md`, `adr/ADR-004-primary-llm-model-selection.md`, `adr/ADR-006-sub-agent-llm-model-strategy.md`, and `adr/ADR-032-backup-storage-strategy.md`  
**Budget Constraint:** $30/month hard cap. This document may not authorize spend above the cap without Faiz approval.

> **v1.1:** Aligned backup storage cost with ADR-032 dual-provider pricing (idcloudhost S3 + Cloudflare R2)

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
| `adr/ADR-032-backup-storage-strategy.md` | Establishes idcloudhost S3 primary + Cloudflare R2 secondary backup storage. | Storage policy parent | Storage budget must reflect dual-provider pricing at $0.046/GB combined rate. |

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

Persona or yandere behavior must never drive spend increase. Any cost decision must be explainable in business-value, safety-value, or reliability-value terms. If a proposed action would exceed the monthly cap, Guinevere must freeze non-critical work and require Faiz approval for exception handling.

### 2.2 Hard Constraint Statement

The monthly budget is **$30/month hard cap**. This value is not a target that may be exceeded casually. It is an operational ceiling.

| Rule | Meaning |
|---|---|
| Hard cap | Total monthly spend must stay at or below $30 unless Faiz explicitly approves an exception. |
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
| idcloudhost S3 | Variable | Primary paid storage. Rp 507/GB/month (~$0.031/GB). Month 1: ~$5.51, Month 12: ~$12.09. Per ADR-032. |
| Cloudflare R2 | Variable but free up to 10GB | Secondary mirror. $0.015/GB/month storage, FREE egress. Activated Phase 2 when data grows. Per ADR-032. |
| Brave Search API | Variable | Query-based. |
| Exa AI Search | Variable | Query-based. |
| Resend API | Variable | Messaging volume. |
| Sentry free tier | Mostly fixed / quota-based | Track event volume. |
| Gotify self-hosted | Fixed infra overhead | Part of VPS baseline. |
| Domain | Fixed / annual | Not immediate if future. |
| Monitoring VPS | Future fixed | Stabilization (P9-P10) and Expansion (P11-P22). |

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

The default budget target is $30/month, allocated across three phases to accommodate growing storage costs from ADR-032 dual-provider backup strategy.

> **Disambiguation:** "Budget Phase 1/2/3" in this section refers to storage rollout phases within the FinOps model. These are NOT the same as delivery step phases (P1, P2, P3). Budget phases track infrastructure cost maturity; delivery step phases track implementation progress.

#### 4.1.1 Phase 1: S3-Only (Month 1-3) — Data < 100 GB

In Phase 1, only idcloudhost S3 is active. Cloudflare R2 is provisioned but not yet receiving mirrored data, staying within the 10 GB free tier.

| Category | Target | Hard / Soft | Notes |
|---|---:|---|---|
| VPS hostdata.id | $11 | Hard baseline | Shared 4C/16GB infra. |
| GPT-5.5 via 9Router | $7-$8 | Hard cap portion | Primary LLM for high-stakes reasoning only. Increased DeepSeek routing for sub-agents. |
| DeepSeek V4 Flash | $1-$2 | Soft/near-free | First-choice for sub-agents, research, validation, audit. |
| idcloudhost S3 (primary only) | $5-$6 | Hard | Rp 507/GB flat. ~$5.51 at 177.8 GB Month 1. Per ADR-032. |
| Cloudflare R2 (secondary, deferred) | $0 | Soft | 10 GB free tier only. Mirror activated in Phase 2. |
| Brave Search | $1 | Soft | Query quota tracked. Cache aggressively. |
| Exa AI | $0-$5 | Soft | Hybrid burst model: ~$1/month avg target, daily burst up to $5 allowed. Monthly throttle >$3 → Brave-only; hard stop >$5 → disabled. Per Faiz decision 2026-05-31 (ADR-033 pending). |
| Resend | $0-$0.50 | Soft | Minimal email usage. |
| Misc / contingency | $0-$0.50 | Reserve | Buffer for retries, small variance. |
| **Total** | **~$28-$30** | | **Within $30 hard cap.** |

**Phase 1 savings vs v1.0:**
- GPT-5.5: $10-12 → $7-8 (save $2-4). More sub-agent work routed to DeepSeek.
- Brave + Exa: $2-4 → $1-6 (Exa hybrid burst model: ~$1/month average, up to $5 burst; Brave $1). Aggressive caching reduces query count.
- Misc: $1-2 → $0-0.50 (save $0.50-1.50). Tighter contingency.
- Net savings reallocated: $2.50-7.50 → idcloudhost S3 increase from $2-3 to $5-6.

#### 4.1.2 Phase 2: Dual Provider Activated (Month 4-6) — Data 100-250 GB

R2 mirror is activated. All new backups go to both idcloudhost S3 (primary) and Cloudflare R2 (secondary).

| Category | Target | Hard / Soft | Notes |
|---|---:|---|---|
| VPS hostdata.id | $11 | Hard baseline | Shared 4C/16GB infra. |
| GPT-5.5 via 9Router | $6-$7 | Hard cap portion | Further DeepSeek routing for routine work. |
| DeepSeek V4 Flash | $1-$2 | Soft/near-free | Increased usage as primary sub-agent model. |
| idcloudhost S3 (primary) | $7-$8 | Hard | ~$7.60 at 245 GB Month 6. Per ADR-032. |
| Cloudflare R2 (secondary, active) | $2-$3 | Soft | ~$3.68 at 245 GB Month 6. Free egress for all restores. |
| Brave Search | $0-$1 | Soft | Reduced. Prefer cached results. |
| Exa AI | $0-$3 | Soft | Phase 2+ higher autonomous loop volume. Same hybrid throttle: >$3/month → Brave-only; >$5/month → disabled. |
| Resend | $0-$0.50 | Soft | Minimal email usage. |
| Misc / contingency | $0-$0.50 | Reserve | Minimal buffer. |
| **Total** | **~$28-$30** | | **Within $30 hard cap.** |

#### 4.1.3 Phase 3: Full Dual Provider (Month 7-12) — Data 250-400 GB

Full dual-provider storage at projected growth rates. This phase is budget-tight.

| Category | Target | Hard / Soft | Notes |
|---|---:|---|---|
| VPS hostdata.id | $11 | Hard baseline | Shared 4C/16GB infra. |
| GPT-5.5 via 9Router | $4-$5 | Hard cap portion | Heavy DeepSeek routing. GPT-5.5 only for critical synthesis. |
| DeepSeek V4 Flash | $1-$2 | Soft/near-free | Primary model for most sub-agent work. |
| idcloudhost S3 (primary) | $10-$12 | Hard | ~$12.09 at 390 GB Month 12. Per ADR-032. |
| Cloudflare R2 (secondary) | $4-$6 | Soft | ~$5.85 at 390 GB Month 12. Free egress. |
| Brave Search | $0 | Soft | Zero budget. Use cached or Exa only. |
| Exa AI | $0 | Soft | Zero budget. Use cached results or Brave only. Hybrid throttle still applies if any residual usage. |
| Resend | $0 | Soft | Gotify/Discord only. |
| Misc / contingency | $0 | Reserve | No buffer. Faiz approval for overages. |
| **Total** | **~$30** | | **At $30 hard cap ceiling.** |

> **Phase 3 Risk:** Storage costs consume 46-60% of budget at Month 12. If data growth exceeds projections, Faiz must approve either: (a) budget increase above $30, (b) retention policy reduction, or (c) deduplication implementation.

#### 4.1.4 Budget Trigger Rules

| Trigger | Required Action |
|---|---|
| S3 storage > $8/month | Evaluate Phase 2 activation readiness |
| Combined S3+R2 > $14/month | Faiz review: retention reduction or deduplication |
| Combined S3+R2 > $18/month | Faiz mandatory decision: budget increase, retention cut, or provider change |
| GPT-5.5 < $4/month quality degradation | Faiz review: restore minimum $5 GPT-5.5 budget |
| Search budget = $0 and research blocked | Temporary $1 search allocation from misc |
| Exa monthly spend > $3 | Auto-throttle: switch to Brave Search for remaining billing cycle (hybrid model) |
| Exa monthly spend > $5 | Hard stop: Exa disabled until next billing cycle |

### 4.2 Hard Limits vs Soft Limits

| Limit Type | Meaning | Example |
|---|---|---|
| Hard limit | Cannot exceed without Faiz approval | Total monthly $30 cap, safe safety operations, no budget for hard invariants. |
| Soft limit | Warning threshold with response | search budget, email usage, misc contingency, monthly provider quota. |
| Zero budget | No tradeoff allowed | safe-word, distress false negatives, redaction failures, incident evidence integrity. |
| Storage phase gate | Budget phase must match data volume phase | Phase 3 triggers Faiz review if storage > $14/month. |

### 4.3 Escalation Procedure

When projected spend approaches or exceeds budget thresholds:

| Condition | Required Action |
|---|---|
| Daily burn above trendline | Investigate root cause, reduce non-critical use, update forecast. |
| Category >80% of its monthly allotment | Freeze low-value use in that category and switch to cheaper alternatives. |
| Total projected month-end spend >100% | Freeze autonomous non-critical work and require Faiz approval for exceptions. |
| Total spend >110% or repeated forecast misses | Treat as FinOps incident, document cause, open corrective action. |
| Budget exhausted mid-month | Emergency cost freeze for all non-critical work, preserve safety/incident/backup/data integrity. |

### 4.4 Delivery Step Phase Cost Tracking

The following table tracks projected cost impact by delivery step phase. Budget Phase 1/2/3 (above) governs storage rollout; this table governs implementation delivery phases.

| Step | Phase Name | Daily Cost | Monthly Cost | Category |
|---|---|---:|---:|---|
| P9 | Discord Bot Foundation | $1/day | $28/month | Stabilization |
| P10 | Surveillance Integration | $1/day | $29/month | Stabilization |
| P11 | WhatsApp Integration | TBD | TBD | Expansion |
| P12 | Gmail/Email Integration | TBD | TBD | Expansion |
| P13 | X Auto Poster | TBD | TBD | Expansion — Obscura CDP runtime + S3 storage + LLM caption generation |
| P14 | Wearable/Xiaomi Watch | TBD | TBD | Expansion |
| P15 | Windows Daemon + WebSocket | TBD | TBD | Expansion |
| P16 | Knowledge Graph | TBD | TBD | Expansion |
| P17 | Cross-Device Sync | TBD | TBD | Expansion |
| P18 | Advanced Memory | TBD | TBD | Expansion |
| P19 | Multi-Project Context | TBD | TBD | Expansion |
| P20 | Self-Improvement Loop | TBD | TBD | Expansion |
| P21 | Voice Interface | TBD | TBD | Expansion |
| P22 | Additional Integrations TBD | TBD | TBD | Expansion |

> **Note:** All Expansion phase costs are TBD pending detailed planning. Each phase must be budgeted before implementation begins. The $30/month hard cap applies across all active phases combined.

**P13 X Auto Poster Cost Considerations:** This phase may incur additional costs beyond typical integration phases: Obscura CDP runtime (browser automation), S3-compatible storage (screenshot queue), and LLM API calls (caption generation). Budget should be allocated separately when P13 is planned.

---

## 5. LLM Cost Management

### 5.1 Model Routing Policy

| Task Type | Preferred Model | Backup | Rationale |
|---|---|---|---|
| Core reasoning, high-stakes synthesis, final authority decisions | GPT-5.5 via 9Router | DeepSeek only if explicitly safe and approved | Highest quality is reserved for critical reasoning. |
| Sub-agent research, summarization, validation, audit | DeepSeek V4 Flash via 9Router | GPT-5.5 only for final synthesis or exceptional cases | Use free tier first. |
| Long context summarization / low-risk extraction | DeepSeek V4 Flash | Cached summaries | Cheaper and sufficient. |
| Safety-critical decisions | GPT-5.5 via 9Router | None by default | Safety and correctness outrank cost. |

As storage costs grow (Phase 2-3), GPT-5.5 budget decreases. DeepSeek V4 Flash becomes the default for an expanding set of task types. GPT-5.5 is preserved for: safety-critical decisions, final conflict resolution, persona drift assessment, and Faiz-requested high-stakes synthesis.

### 5.2 Token Budget Policy

| Metric | Target | Action if Exceeded |
|---|---:|---|
| Daily GPT-5.5 tokens | configured daily ceiling | Reduce prompt size, batch tasks, defer non-critical work. |
| Monthly GPT-5.5 tokens | configured monthly ceiling | Freeze expensive work and require Faiz approval. |
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
| Phase-aware routing | In Phase 2-3, aggressively route sub-agents to DeepSeek to preserve GPT-5.5 budget for critical work. |
| Search budget conservation | In Phase 3, search APIs have $0 budget. All research must use cached results, existing reports, or librarian agents that batch queries. |

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
| Severe anomaly | Freeze autonomous non-critical work, require Faiz approval, create cost incident note. |
| Repeated severe anomaly | Open FinOps incident and review vendor usage patterns. |

### 6.4 Budget Exhaustion Procedure

If budget exhaustion is imminent or reached:

1. Freeze autonomous non-critical work.
2. Preserve safety, incident response, backup, and data integrity operations.
3. Shift sub-agents to free/cheap paths.
4. Reduce prompt size and batching overhead.
5. Require Faiz approval for any exception.
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

### 7.5 Storage Cost Optimization

| Strategy | Description | Savings | Complexity | Phase |
|---|---|---|---|---|
| R2 deferred activation | Keep R2 in 10 GB free tier until Phase 2 | $2-3/month | Low | Phase 1 |
| Retention reduction | Monthly from 6→4, weekly from 4→3 | ~$0.50/month at Phase 2 | Low | Phase 2+ |
| Evidence archival | Delete evidence > 90 days from remote (keep local) | ~$1/month | Medium | Phase 2+ |
| Deduplication (restic/borg) | Deduplicated backups for evidence and objects | ~$3-5/month | High | Phase 3 |
| Incremental uploads | Only upload changed objects, not full mirror | ~$1-2/month | Medium | Phase 2+ |
| Cold tier migration | Move old WAL archives to R2 only (cheaper) | ~$1-2/month | Medium | Phase 3 |

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
| idcloudhost S3 | durability, Rp 507/GB/month flat cost, restore reliability, uptime SLA |
| Cloudflare R2 | free tier fit (10 GB), backup mirror value, zero egress advantage, $0.015/GB storage |
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
| $30/month cap | Hard constraint; never exceed without Faiz approval. |
| DeepSeek free tier | First choice for sub-agents, research, validation, audit. |
| GPT-5.5 | Reserved for core reasoning, planning, high-stakes synthesis only. |
| Safety/incident/backup/data integrity | Cost optimization must never reduce these operations. |
| Persona/yandere influence | Must never drive spend increase. |
| Free tiers | Must be tracked and not assumed unlimited. |
| Vendor alternatives | Must be documented with switch procedures. |
| Storage phased approach | Budget must follow Phase 1→2→3 progression. No premature R2 activation. Storage > $14/month triggers Faiz review. |

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
| COST-BG-001 | Storage cost ceiling per phase needs Faiz confirmation. Phase 1: $6, Phase 2: $11, Phase 3: $18. Total budget impact documented in v1.1. | Faiz | budget sheet completion | Monthly budget worksheet | before runtime enforcement |
| COST-BG-002 | GPT-5.5 token ceiling not yet converted to monthly cost ceiling. | Guinevere | cost policy not fully operational | LLM cost control sheet | before production budget claim |
| COST-BG-003 | Monitoring VPS future activation remains deferred. | Faiz | future fixed cost line | monitoring rollout plan | when load justifies |
| COST-BG-004 | Domain registration is future-only. | Faiz | annualized cost not yet live | domain procurement note | before launch |
| COST-BG-005 | ~~Exact per-query Brave and Exa caps need numeric thresholds.~~ **Resolved for Exa**: hybrid burst model defined (daily $5 cap, monthly $1 target, $3 throttle, $5 hard stop). Brave thresholds still pending. | Guinevere | search governance partially resolved | search quota sheet | before search automation |
| COST-BG-006 | Monthly report template to be integrated with finance/export tooling. | Guinevere | reporting workflow incomplete | FinOps reporting automation | before fully automated reporting |
| COST-BG-007 | Provider switch tests not yet implemented. | Guinevere | lock-in risk remains theoretical | switch drill evidence | before production readiness |

---

## Appendix A — Monthly Budget Matrix (Current Phase: Phase 1)

| Category | Monthly Target | Hard / Soft | Notes |
|---|---:|---|---|
| VPS hostdata.id | $11 | Hard baseline | shared 4C/16GB |
| GPT-5.5 via 9Router | $7-8 | Hard / controlled variable | core reasoning, planning, high-stakes synthesis |
| DeepSeek V4 Flash | $1-2 | Soft / optimization | free tier first |
| idcloudhost S3 (primary) | $5-6 | Hard | Rp 507/GB/month flat, per ADR-032 |
| Cloudflare R2 (secondary, deferred) | $0 | Soft | 10 GB free tier; mirror activated Phase 2 |
| Brave Search API | $1 | Soft | query cap, cache aggressively |
| Exa AI Search | $0-$5 | Soft | hybrid burst: ~$1/mo avg target, daily burst ≤$5, throttle >$3→Brave, hard stop >$5→disabled |
| Resend | $0-0.50 | Soft | minimal email usage |
| Misc / contingency | $0-0.50 | Reserve | retries, variance |
| **Total** | **~$28-30** | | **Within $30 hard cap** |

> See Section 4.1 for Phase 2 and Phase 3 budget tables.

---

## Appendix B — Vendor Alternative Matrix

| Primary | Alternative | Switch Procedure | Evidence |
|---|---|---|---|
| GPT-5.5 via 9Router | DeepSeek V4 Flash via 9Router | Reduce task scope, route low-risk work, preserve GPT-5.5 only for critical synthesis. | switch test note |
| 9Router routing | direct provider or other router if approved | Update route config, rotate credentials, run smoke tests. | route test evidence |
| idcloudhost S3 | Cloudflare R2 (secondary, per ADR-032) | Update backup target in rclone config, validate restore from R2, rotate access keys. R2 has free egress advantage for DR drills. | restore evidence |
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
| Owner | Faiz |
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
| COST-TM-001 | 30-dollar cap enforcement | budget simulation | cannot exceed without Faiz approval |
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
| Reviewer | Faiz |
| Review Date | 2026-05-30 |
| Decision | Accepted |
| Notes | Approved as internal Cost & FinOps Model and normative child of SLO/SLA/Error Budget Spec, Observability Spec, ADR-004, and ADR-006. $30/month is a hard cap. DeepSeek free tier is first choice for sub-agents, research, validation, and audit. GPT-5.5 is reserved for core reasoning, planning, and high-stakes synthesis. Cost optimization must never reduce safety, incident response, backup, or data integrity. Monthly cost evidence must be written under `evidence/finops/<YYYY-MM>/`. |

| Field | Value |
|---|---|
| Reviewer | Guinevere (Sisyphus orchestrator) |
| Review Date | 2026-05-31 |
| Decision | Accepted v1.1 |
| Notes | Budget reallocation to accommodate ADR-032 dual-provider pricing. Storage increased from $2-3 to $5-6 (Phase 1) up to $16-18 (Phase 3). Savings found by: (1) increased DeepSeek routing reducing GPT-5.5 budget, (2) search API budget reduction, (3) misc contingency reduction. Phased approach defers R2 mirror activation to manage early-month costs. $30/month hard cap maintained across all phases. |

---

## Appendix F — Next Recommended Document

The next recommended document is:

```text
Guinevere_Cloud_and_Search_Vendor_Procurement_Strategy_v1.0.md
```

Reason: this model defines budget allocations, vendor alternatives, and switch procedures, but several provider procurement details remain future-facing or subject to numeric threshold finalization. A dedicated procurement strategy will define activation triggers, annualized commitments, and formal vendor replacement criteria.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-30 | Guinevere (Autonomous Agent) | Initial Cost & FinOps Model: $30/month cap, category allocations, LLM routing policy, vendor evaluation, reporting format. |
| 1.1 | 2026-05-31 | Guinevere (Sisyphus orchestrator) | Aligned backup storage cost with ADR-032 dual-provider pricing. Storage: $2-3 → $5-6 (Phase 1), $10-11 (Phase 2), $14-18 (Phase 3). Introduced phased budget tables (4.1.1-4.1.4). Rebalanced: GPT-5.5 $10-12→$7-8 (Phase 1), Brave+Exa $2-4→$2, Misc $1-2→$0-0.50. Added storage cost optimization strategies (7.5). |
| 1.1a | 2026-05-31 | Guinevere (B-02 fix) | Exa hybrid burst model (Faiz decision 2026-05-31, ADR-033 pending): Exa budget changed from flat $1/month to $0-5/month range with ~$1 average target, $3/month throttle trigger (Brave fallback), $5/month hard stop. Added Exa trigger rules to §4.1.4. Updated Phase 1-3 Exa lines and Appendix A. Resolved COST-BG-005 for Exa thresholds. |

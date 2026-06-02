# SLO / SLA / Error Budget — External Best Practices Research

**Date**: 2026-05-30  
**Author**: THE LIBRARIAN (Guinevere Sub-Agent)  
**Purpose**: Provide authoritative external references for building Project Guinevere's internal SLO/SLA/Error Budget specification.

---

## Table of Contents

1. [Canonical Works: Google SRE Library](#1-canonical-works-google-sre-library)
2. [SLI/SLO Definition Patterns](#2-slislo-definition-patterns)
3. [Error Budget Mechanics](#3-error-budget-mechanics)
4. [Multi-Window, Multi-Burn-Rate Alerting](#4-multi-window-multi-burn-rate-alerting)
5. [PromQL Recording Rules & SLI Queries](#5-promql-recording-rules--sli-queries)
6. [Dashboard-as-Code & Grafana Scorecards](#6-dashboard-as-code--grafana-scorecards)
7. [SLO Specification Standards (OpenSLO, Sloth)](#7-slo-specification-standards-openslo-sloth)
8. [Safety Invariants & Zero-Error-Budget Patterns](#8-safety-invariants--zero-error-budget-patterns)
9. [Single-User & Internal Service Adaptations](#9-single-user--internal-service-adaptations)
10. [Cost Budget Burn / Freeze (FinOps + SRE)](#10-cost-budget-burn--freeze-finops--sre)
11. [Error Budget Policy Templates](#11-error-budget-policy-templates)
12. [Monthly Scorecard & Review Cadence](#12-monthly-scorecard--review-cadence)
13. [Recommendations for Guinevere](#13-recommendations-for-guinevere)

---

## 1. Canonical Works: Google SRE Library

### Site Reliability Engineering (2016)

The foundational text. Introduces SLI/SLO/Error Budget as the core SRE framework.

- **Key principle**: "100% is the wrong reliability target." Chase less than 100% deliberately to enable innovation.
- **Key formula**: `Error Budget = 100% - SLO target`
- **Key advice**: "Keep a safety margin" — use tighter internal SLO than external SLA. "Don't overachieve" — users build on your actual performance.
- **Source**: https://sre.google/sre-book/service-level-objectives/

### The Site Reliability Workbook (2018)

The implementation companion. Chapter 5 ("Alerting on SLOs") is the definitive reference for multi-window, multi-burn-rate alerting.

- **Source**: https://sre.google/workbook/alerting-on-slos/
- **Source**: https://sre.google/workbook/implementing-slos/

### The Art of SLOs (Workshop)

Google CRE team's workshop for hands-on SLO creation. Includes templates, handbook, and facilitator guide.

- **Source**: https://sre.google/resources/practices-and-processes/art-of-slos/

### CSSRE Prodcast: Defining SLOs and Methods for SLO Monitoring

Advanced discussion on SLO limitations — variance tracking, stationarity, and the need for "surprise detectors" beyond SLOs.

- **Source**: https://sre.google/prodcast/transcripts/sre-prodcast-01-04/

---

## 2. SLI/SLO Definition Patterns

### The SLI Equation (Google SRE)

```
SLI = (good events / valid events) × 100
```

- **Good events**: Outcomes satisfying user requirements (HTTP 2xx, response under latency threshold, durable write)
- **Valid events**: All countable transactions in scope. Exclude health checks, internal traffic, synthetic-only requests.

### VALET Framework (Home Depot via Google CRE)

An acronym for five SLI categories:

| Category | Measures | Example |
|---|---|---|
| **V**olume | Throughput | Requests per second |
| **A**vailability | Success rate | % non-5xx responses |
| **L**atency | Response speed | P99 < 300ms |
| **E**rrors | Failure count | 5xx error count |
| **T**hroughput | Capacity | Peak transactions per second |

Source: https://sre.google/workbook/slo-engineering-case-studies/

### Target Selection Guidance

| Target | Error Budget | Monthly Downtime | Appropriate For |
|---|---|---|---|
| 99% | 1% | 7.2 hours | Internal tools, batch jobs, dev environments |
| 99.5% | 0.5% | 3.6 hours | Recommendations, analytics |
| 99.9% | 0.1% | ~43 minutes | Standard user-facing services, APIs |
| 99.95% | 0.05% | ~21.6 minutes | Payment, checkout, auth |
| 99.99% | 0.01% | ~4.3 minutes | Multi-region critical infra |
| 99.999% | 0.001% | ~26 seconds | Life-critical systems |

**Rule**: Set SLO from *user expectations and business impact*, not current performance. Measure current reliability over 90 days first, then decide.

Sources:
- https://sre.google/workbook/implementing-slos/
- https://cloud.google.com/blog/products/devops-sre/how-to-design-good-slos-according-to-google-sres

### SLO Design Document Template (Google Cloud)

Recommended structure:
1. Critical User Journeys (CUJs) mapped out
2. SLI definition per CUJ (with measurement location)
3. SLO targets with rationale
4. Compliance period (recommend 28-day rolling + fixed quarterly)
5. Error budget policy
6. Caveats, tradeoffs, and clarifications
7. Changelog

Source: https://cloud.google.com/blog/products/devops-sre/how-to-design-good-slos-according-to-google-sres

---

## 3. Error Budget Mechanics

### Core Formula

```
Error Budget = 100% − SLO Target
Error Budget (ratio) = (1 − SLO_target)
```

### Time Window Types

| Type | Behavior | Best For |
|---|---|---|
| **Rolling window** (e.g., 28-day) | Continuous. Bad events fall off as window advances. | Operations, alerting, user experience alignment |
| **Calendar-aligned** (e.g., monthly) | Resets at period boundary. Incidents at end of month "forgotten." | SLA/billing reporting, quarterly reviews |

### Budgeting Methods (Nobl9 Classification)

| Method | Counts | Recovery |
|---|---|---|
| **Occurrences** | Good/total events naturally weighted by volume | Recovers as good events replace bad |
| **Time Slices** | Good/bad minutes regardless of volume | Recovers when bad minutes roll out |

**Recommendation**: Use **Occurrences** for request-driven services, **Time Slices** for infrastructure/batch metrics where traffic varies.

Sources:
- https://docs.nobl9.com/guides/slo-guides/reliability-and-error-budget/
- https://docs.nobl9.com/guides/slo-guides/slo-calculations/
- https://docs.nobl9.com/guides/slo-guides/occurrences

### Reliability Recovery (Nobl9)

- **Calendar + Time Slices**: Only bad minutes matter. Recovers to 100% at next window start (no partial recovery).
- **Calendar + Occurrences**: Good events improve ratio. Recovers to 100% at next window start (partial recovery possible).
- **Rolling + either**: FIFO window drops old events. Can recover to 100% if all events in window are good long enough.

---

## 4. Multi-Window, Multi-Burn-Rate Alerting

### The Gold Standard (Google SRE Workbook, Iteration 6)

The recommended alerting strategy combines multiple burn rates with multiple time windows using AND logic.

#### Recommended Default Thresholds

| Severity | Long Window | Short Window | Burn Rate | Budget Consumed | Action |
|---|---|---|---|---|---|
| **Page (fast)** | 1 hour | 5 minutes | 14.4× | 2% | Immediate page |
| **Page (slow)** | 6 hours | 30 minutes | 6× | 5% | Page (next business hour) |
| **Ticket** | 3 days | 6 hours | 1× | 10% | Slack/ticket |

**Design reasoning**:
- Short window = fast detection + fast reset (resolves minutes after incident ends)
- Long window = confirms sustained burn + suppresses transient spikes
- Short window = 1/12 of long window (empirical guideline)

Source: https://sre.google/workbook/alerting-on-slos/

#### Burn Rate Formula

```
burn_rate = observed_error_rate / allowed_error_rate
```
where `allowed_error_rate = 1 − SLO_target`

- **1.0× burn rate** = exactly on track to exhaust budget by window end
- **14.4× burn rate** = exhausts 30-day budget in ~50 hours
- **6× burn rate** = exhausts 30-day budget in ~5 days

#### PromQL Alerting Rules (99.9% SLO Example)

```promql
# Page fast: 14.4× burn rate over 1h AND 5m
(
  sum(rate(http_errors_total[1h])) / sum(rate(http_requests_total[1h]))
) > 0.001 * 14.4
and
(
  sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m]))
) > 0.001 * 14.4

# Page slow: 6× burn rate over 6h AND 30m
(
  sum(rate(http_errors_total[6h])) / sum(rate(http_requests_total[6h]))
) > 0.001 * 6
and
(
  sum(rate(http_errors_total[30m])) / sum(rate(http_requests_total[30m]))
) > 0.001 * 6

# Ticket: 1× burn rate over 3d AND 6h
(
  sum(rate(http_errors_total[3d])) / sum(rate(http_requests_total[3d]))
) > 0.001 * 1
and
(
  sum(rate(http_errors_total[6h])) / sum(rate(http_requests_total[6h]))
) > 0.001 * 1
```

**Key insight**: The `0.001` is `1 − SLO_target`. Change to `0.0001` for 99.99% SLO, `0.005` for 99.5%, etc.

---

## 5. PromQL Recording Rules & SLI Queries

### Naming Convention (Sloth standard)

```
slo:sli_error:ratio_rate{5m|30m|1h|2h|6h|1d|3d|30d}
slo:objective:ratio
slo:error_budget:ratio
slo:time_period:days
slo:current_burn_rate:ratio
slo:period_burn_rate:ratio
slo:period_error_budget_remaining:ratio
```

### SLI Recording Rules (Availability)

```yaml
groups:
  - name: sli_recording_rules
    interval: 30s
    rules:
      # Error ratio across multiple windows
      - record: sli:error_ratio:rate5m
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))

      - record: sli:error_ratio:rate1h
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[1h]))
          /
          sum(rate(http_requests_total[1h]))

      - record: sli:error_ratio:rate6h
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[6h]))
          /
          sum(rate(http_requests_total[6h]))

      - record: sli:error_ratio:rate30d
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[30d]))
          /
          sum(rate(http_requests_total[30d]))
```

### Error Budget Calculation

```promql
# Error budget remaining (ratio: 1.0 = full, 0 = exhausted)
# For 99.9% SLO:
1 - (
  (1 - sli:availability:ratio)
  /
  (1 - 0.999)
)

# Error budget remaining as percentage:
(
  (
    sum(rate(http_requests_total{status!~"5.."}[30d]))
    /
    sum(rate(http_requests_total[30d]))
  ) - 0.999
) / (1 - 0.999) * 100
```

### Latency SLI (Histogram-Based)

```promql
# Fraction of requests under 300ms over 30 days
sum(rate(http_request_duration_seconds_bucket{le="0.3"}[30d]))
/
sum(rate(http_request_duration_seconds_count[30d]))
```

### Burn Rate Calculation

```promql
# Current burn rate over 1h
(
  1 - (
    sum(rate(http_requests_total{status!~"5.."}[1h]))
    /
    sum(rate(http_requests_total[1h]))
  )
)
/
(1 - 0.999)
```

Sources:
- https://github.com/slok/sloth (Sloth SLO generator)
- https://oneuptime.com/blog/post/2026-01-25-prometheus-slo-monitoring/
- https://devops-daily.com/posts/slos-slis-error-budgets-practical-guide

---

## 6. Dashboard-as-Code & Grafana Scorecards

### Grafana SLO Dashboard (Native)

Grafana Cloud provides built-in SLO management that auto-generates:
- Recording rules for SLI computation
- Error budget dashboards
- Fast-burn and slow-burn alert rules

Source: https://grafana.com/docs/grafana-cloud/alerting-and-irm/slo/best-practices/

### SLO Burn Rate Panel (Open Source)

The `slo-burn-panel` provides:
- Error budget gauge (semicircular)
- Multi-window burn rate (short + long window)
- Four operational states: SAFE → SLOW BURN → FAST BURN → EXHAUSTED
- Projected exhaustion time
- Works with any datasource

Source: https://github.com/dyfimas/slo-burn-panel

### Essential Dashboard Panels

1. **SLI Gauge**: Current metric value vs SLO target (green/yellow/red thresholds)
2. **Error Budget Remaining**: Percentage stat panel (>50% green, 25-50% yellow, <25% red)
3. **Burn Rate**: Time series showing 1× threshold line
4. **Projected Exhaustion**: Days/hours until budget runs out
5. **SLI Over Time**: Rolling window with SLO target overlay line

### Dashboard-as-Code Patterns

**Grafana Provisioning**:
```yaml
# provisioning/dashboards/dashboards.yaml
apiVersion: 1
providers:
  - name: default
    type: file
    disableDeletion: true
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

**Terraform**:
```hcl
resource "grafana_dashboard" "slo_overview" {
  config_json = file("${path.module}/dashboards/slo-overview.json")
  folder      = grafana_folder.sre.id
  overwrite   = true
}
```

**Dashboard Hierarchy** (3-Layer Model):
1. **Service Overview**: 4 golden signals + SLO burn rate (last 1h)
2. **Triage Dashboard**: Breakdown by endpoint/pod/region + dependency health (last 6h)
3. **Debug Dashboard**: Per-pod resources, goroutines, connection pools

Sources:
- https://github.com/slok/sloth (Sloth auto-generates Grafana metadata metrics)
- https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/
- https://devopsil.com/articles/2026-03-21-grafana-dashboard-design-sre-principles/
- https://oneuptime.com/blog/post/2026-01-26-slo-dashboards-grafana/

---

## 7. SLO Specification Standards (OpenSLO, Sloth)

### OpenSLO (Vendor-Neutral Standard)

A YAML specification for declarative SLO definitions. Supports multiple providers (Prometheus, Datadog, Google Cloud Monitoring).

**Key types**: `DataSource`, `SLO`, `SLI`, `AlertPolicy`, `AlertCondition`, `AlertNotificationTarget`, `Service`

```yaml
apiVersion: openslo/v1
kind: SLO
metadata:
  name: api-availability
spec:
  description: "API availability SLO"
  service: api-gateway
  budgetingMethod: Occurrences
  objectives:
    - displayName: Good
      target: 0.999
      ratioMetrics:
        good:
          metricSource:
            type: Prometheus
            spec:
              promql: sum(rate(http_requests_total{status!~"5.."}[{{.window}}]))
        total:
          metricSource:
            type: Prometheus
            spec:
              promql: sum(rate(http_requests_total[{{.window}}]))
  timeWindow:
    - duration: 30d
      isRolling: true
```

**Budgeting Methods**: `Occurrences`, `Timeslices`, `RatioTimeslices`
**Time Windows**: Rolling (`isRolling: true`) or Calendar-aligned (`calendar: {}`)

Sources:
- https://openslo.com/
- https://github.com/OpenSLO/OpenSLO

### Sloth (Prometheus SLO Generator)

Generates complete Prometheus recording rules + alerts from a simple YAML spec.

```yaml
version: "prometheus/v1"
service: "api-gateway"
slos:
  - name: "requests-availability"
    objective: 99.9
    sli:
      events:
        error_query: sum(rate(http_requests_total{status=~"5.."}[{{.window}}]))
        total_query: sum(rate(http_requests_total[{{.window}}]))
    alerting:
      page_alert:
        labels:
          severity: critical
      ticket_alert:
        labels:
          severity: warning
```

**Auto-generated metrics**:
- `slo:sli_error:ratio_rate5m`, `30m`, `1h`, `2h`, `6h`, `1d`, `3d`, `30d`
- `slo:current_burn_rate:ratio`
- `slo:period_error_budget_remaining:ratio`
- `slo:objective:ratio`, `slo:error_budget:ratio`

**CLI**: `sloth generate -i slo.yaml -o rules.yaml`

Sources:
- https://sloth.dev/
- https://github.com/slok/sloth

### Google SLO Generator

Official Google tool for computing SLOs from Prometheus, Stackdriver, or BigQuery.

```yaml
backend: prometheus
method: distribution_cut
target: 0.999
service_name: my-service
exporters:
  - prometheus
```

Source: https://github.com/google/slo-generator

---

## 8. Safety Invariants & Zero-Error-Budget Patterns

### Zero-Tolerance SLOs (Security Invariants)

Some reliability boundaries are non-negotiable — they have **no error budget**.

**Reference implementation** (from `pi_agent_rust`):

| SLO ID | Name | Target | Error Budget | Breach Response |
|---|---|---|---|---|
| SLO-01 | Invariant pass rate | 100% | 0 (zero tolerance) | Build fails. No merge. |
| SLO-08 | Security boundary | 100% | 0 | Immediate build failure |
| SLO-09 | Audit trail integrity | 100% | 0 | Build blocked |

**Error budget types**:
- **Zero-tolerance budgets**: Build fails immediately. No merge permitted.
- **Detection budgets**: Release blocked until restored. RCA required.
- **Performance budgets**: Warning at 80%, blocked at 100%.
- **Velocity budgets**: Warning if no gap closed in current sprint.

Source: https://github.com/Dicklesworthstone/pi_agent_rust/blob/main/docs/security/security-slos.md

### Hard Invariants Design Pattern

For safety-critical systems where violations must never occur:

1. **No error budget**: SLO target = 100%. Violation means system is in invalid state.
2. **Detection before measurement**: Alert on the *potential* for violation, not the violation itself.
3. **Independent verification**: Separate monitoring path for invariants (not sharing the regular SLI pipeline).
4. **Automatic containment**: Violation triggers immediate isolation/rollback.

### Google's "Stationarity" Approach

From the SRE Prodcast: reliability should be defined as *stationarity* — the distribution of performance remains self-consistent over time. Invariants are assertions about what the distribution *must* look like.

"Heading in the same direction as SLOs but with more sophisticated analytics — building surprise detectors using rates of unlikely events."

Source: https://sre.google/prodcast/transcripts/sre-prodcast-01-04/

---

## 9. Single-User & Internal Service Adaptations

### The Low-Traffic Problem

A single-user or internal service with few requests creates statistical noise:
- 10 requests/hour → 1 failure = 10% error rate = 1,000× burn rate
- Ephemeral failure looks identical to real outage
- Multi-window alerts fire on every transient error

Source: https://sre.google/workbook/alerting-on-slos/ (Low-Traffic Services section)

### Recommended Mitigations (Google SRE)

| Strategy | How It Works | Tradeoffs |
|---|---|---|
| **Synthetic traffic** | Generate artificial probes to raise signal frequency | Adds complexity; doesn't cover all user journeys |
| **Combine services** | Aggregate related low-traffic services into higher-level group | Individual service failure may be masked |
| **Lower SLO** | Reduce target to match actual impact (99.9% → 99% for internal tools) | Smaller error budget is more representative |
| **Increase window** | 90-day window instead of 30-day | Slower detection; less responsive |
| **Minimum failures** | Require N failures before alerting (e.g., ≥10) | Delays detection for small outages |

### Adaptations for Guinevere

For a single-user autonomous agent:
- Use **Occurrences** budgeting (not Time Slices) — automatically adjusts to low volume
- Set **synthetic health probes** at regular intervals (heartbeat with expected response)
- Use **minimum failure thresholds** (don't alert on isolated transient errors)
- Consider **user-perceived reliability** (was the last interaction successful?) not statistical aggregates
- **Composite SLO**: aggregate multiple micro-component SLIs into higher-level user-experience SLO

### Grafana's Minimum Failures Feature

Grafana SLOs support a "Minimum Failures" setting — a minimum number of failure events required before an alert triggers. Recommended for low-traffic services.

Source: https://grafana.com/docs/grafana-cloud/alerting-and-irm/slo/best-practices/

---

## 10. Cost Budget Burn / Freeze (FinOps + SRE)

### The Cost-Error-Budget Model (SRE Meets FinOps)

Apply error budget logic to cost:

**Spend target** (like SLO): Monthly cloud budget
**Allowed variance** (like error budget): e.g., ±15% of forecast
**Burn rate**: How fast you're consuming the monthly budget

Source: https://medium.com/@mrkoozer/sre-meets-finops-error-budgets-for-spend-e468d1f6c298

### Closed-Loop Budget Brake Pattern

| Tier | Threshold | Actions |
|---|---|---|
| **Tier 1** | Daily cap crossed | Auto-stop non-prod resources, freeze agent provisioning |
| **Tier 2** | Trust > 0.7 | Downscale training jobs, throttle batch ingestion |
| **Tier 3** | Production affected | Page on-call only; no auto-action |

**Key formula**: `cap = max(typical × variance, emergency_floor + 20%)`

Source: https://zop.dev/resources/blogs/closed-loop-budget-brake-daily-cap-runaway/

### FinOps Guardrails for SREs

From the "FinOps for SREs" series (Korean tech company production experience):

1. **Error Budget Protection**: No cost optimization if error budget < 50%
2. **Assured Minimum Downtime**: Every change has a rollback plan
3. **Reliability Over Savings**: $500/month savings ≠ 0.01% availability risk

Source: https://dev.to/june-gu/finops-for-sres-cutting-costs-without-breaking-things-2fbk

### Unit Economics (FinOps × SRE)

Most powerful frame: "What does it cost to provide X minutes of availability for Y users?"

```
Moving from 99.9% to 99.99% requires $200K/yr infra + $150K/yr SRE time.
Revenue impact of prevented downtime = ~$800K/yr.
Investment has clear positive ROI.
```

Source: https://zakhassan.com/blog/finops-meets-sre-why-cloud-cost-is-now-a-reliability-discipline

### AI Agent Cost Budgeting

For LLM-powered systems (relevant to Guinevere):
- **Per-model, per-use-case budgets**
- **Cost per outcome** (e.g., $2 per investigation that reduces MTTR by 23min)
- **Circuit breakers**: per-invocation token limits + per-day cost caps

---

## 11. Error Budget Policy Templates

### Google SRE Workbook: Example Error Budget Policy

Source: https://sre.google/workbook/error-budget-policy/

**Policy name**: Example Game Service Error Budget Policy

**Goals**:
- Protect customers from repeated SLO misses
- Balance reliability with feature development

**SLO Miss Policy**:
- If service is performing at or above SLO → releases proceed normally
- If service has exceeded error budget → halt all changes except P01/security fixes until back within SLO

**Outage Policy**:
- Single incident consuming >20% of budget → mandatory postmortem with P0 action item
- Single outage class consuming >20% over quarter → P0 item on quarterly planning

**Escalation**: Disagreements escalated to CTO.

### Tiered Release Policy Pattern

```markdown
Budget > 50%:  Ship freely. Take risks. Run experiments.
Budget 25–50%: Ship cautiously. Require rollback plans.
Budget 5–25%:  Freeze non-critical deploys. Focus on reliability.
Budget < 5%:   Full feature freeze. All hands on reliability.
Budget = 0%:   Postmortem required. No deploys until budget recovers.
```

### Budget Exhaustion Decision Tree (from industry practice)

```
IF budget consumed > 100%:
  HALT all non-critical deployments
  Continue: P0 fixes, security patches, reliability improvements
  Resume when budget restored

IF single incident consumed > 20% of budget:
  MANDATORY postmortem within 5 business days
  Postmortem must include action items with owners

IF recurring pattern of similar incidents:
  Escalate to quarterly planning as P0 reliability investment
```

### Exemption Categories (Google SRE)

- **External causes** (cloud provider outage): May exempt from deployment freeze
- **Internal causes** (bug, capacity): Full policy applies
- **Gray areas**: Case-by-case; escalate disagreements

---

## 12. Monthly Scorecard & Review Cadence

### Recommended Review Schedule

| Cadence | Activity | Participants |
|---|---|---|
| **Weekly** | Error budget check at team sync | Engineering team |
| **Monthly** | Formal SLO review + scorecard | Team + PM + stakeholders |
| **Quarterly** | SLO target adjustment | Engineering + Product + SRE |
| **6 months** | Full SLI/SLO redesign cycle | All stakeholders |

Source: https://sre.google/workbook/slo-engineering-case-studies/ (Evernote case study)

### Monthly Scorecard Components

1. **SLO compliance %** for each SLO over trailing 30 days
2. **Error budget consumed** (absolute %)
3. **Number and severity** of budget-exhaustion events
4. **Top 3 incidents** by budget impact (with % of budget consumed)
5. **Burn rate trends** (are we getting better or worse?)
6. **Action items** from previous month tracked to completion

### Scorecard Visualizations

- SLI gauge (green/yellow/red at SLO boundary + safety margin)
- Error budget burndown chart (remaining over time)
- Burn rate heatmap (hour × day granularity)
- Incident budget impact ranking (pareto chart)

### SLO Report Automation

```python
def generate_slo_report(service, slo_target=0.999):
    """Generate monthly SLO report."""
    availability_30d = query(f'sum_over_time(...[30d]) / sum_over_time(...[30d])')
    budget_remaining = query(f'error_budget:remaining{{service="{service}"}}')
    burn_rate = query(f'error_budget:burn_rate:1h{{service="{service}"}}')

    return {
        "service": service,
        "slo_target": f"{slo_target*100:.2f}%",
        "current_availability": f"{availability_30d*100:.3f}%",
        "meeting_slo": availability_30d >= slo_target,
        "error_budget_consumed": f"{(1-budget_remaining)*100:.1f}%",
        "projected_exhaustion_days": calculate_exhaustion(...),
    }
```

Source: https://oneuptime.com/blog/post/2026-01-25-prometheus-slo-monitoring/

---

## 13. Recommendations for Guinevere

Based on all external research, here is guidance for Guinevere's SLO specification:

### SLI Selection (Start Here)

| Category | SLI | Measurement | Example |
|---|---|---|---|
| **Availability** | Agent loop success rate | Successful loop completions / total loop starts | "Agent loop completes within defined SLA" |
| **Latency** | Response time | P95 response time per loop iteration | "Agent loop processes within threshold" |
| **Freshness** | Memory recall freshness | Age of recalled data vs expected staleness | "Recent conversations load within time bound" |
| **Correctness** | Task completion accuracy | Successful outcomes / total tasks | "User query resolved correctly" |
| **Safety** | Invariant pass rate | 100% on safety invariants | Zero error budget |

### Recommended SLO Targets

| Service Tier | Type | Availability | Latency | Error Budget |
|---|---|---|---|---|
| **Tier 1** | Core agent loop | 99.9% | 99% < 5s | 0.1% / 30d |
| **Tier 2** | Memory/recall | 99.5% | 95% < 2s | 0.5% / 30d |
| **Tier 3** | Surveillance/integrations | 99% | 90% < 10s | 1% / 30d |
| **Safety invariants** | All safety checks | 100% | N/A | **0 (no budget)** |

### Policy Structure

1. **28-day rolling window** for operational alerting (standard)
2. **Calendar-quarter** for business reviews
3. **Multi-window burn-rate alerts** (14.4×/6×/1×) for each SLO
4. **Zero-budget invariants** for safety-critical paths
5. **Monthly scorecard** reviewed with operator
6. **Cost budget** with separate burn-rate tracking (FinOps layer)

### Implementation Path

1. Define SLIs from user perspective (agent loop = the user journey)
2. Instrument Prometheus recording rules
3. Deploy Sloth or OpenSLO for SLO-as-code
4. Build Grafana dashboard with burn rate panels
5. Configure multi-window alerts via Alertmanager
6. Write error budget policy (operator + project owner sign-off)
7. Establish monthly review cadence
8. Quarterly SLO target adjustment

---

## Reference Index

| Resource | URL | Key Use |
|---|---|---|
| Google SRE Book (SLO chapter) | https://sre.google/sre-book/service-level-objectives/ | Foundational concepts |
| Google SRE Workbook (Implementing SLOs) | https://sre.google/workbook/implementing-slos/ | Step-by-step SLO recipe |
| Google SRE Workbook (Alerting on SLOs) | https://sre.google/workbook/alerting-on-slos/ | Multi-window burn-rate defintive guide |
| Google SRE Workbook (Error Budget Policy) | https://sre.google/workbook/error-budget-policy/ | Policy template |
| Google SRE Workbook (SLO Case Studies) | https://sre.google/workbook/slo-engineering-case-studies/ | Evernote + Home Depot real examples |
| Google SRE Prodcast | https://sre.google/prodcast/transcripts/sre-prodcast-01-04/ | Advanced: stationarity, invariants |
| Google Art of SLOs Workshop | https://sre.google/resources/practices-and-processes/art-of-slos/ | Workshop materials and template |
| Google Cloud SLO Design | https://cloud.google.com/blog/products/devops-sre/how-to-design-good-slos-according-to-google-sres | SLO design doc template |
| Google SRE Fundamentals | https://cloud.google.com/blog/products/devops-sre/sre-fundamentals-slis-slas-and-slos | SLA vs SLO vs SLI primer |
| Google SLO Generator | https://github.com/google/slo-generator | Official SLO computation tool |
| Sloth (SLO generator) | https://sloth.dev/ | Prometheus SLO code generation |
| Sloth GitHub | https://github.com/slok/sloth | Open source SLO framework |
| OpenSLO Spec | https://openslo.com/ | Vendor-neutral SLO YAML standard |
| OpenSLO GitHub | https://github.com/OpenSLO/OpenSLO | Full specification |
| Nobl9 Docs | https://docs.nobl9.com/guides/slo-guides/ | SLO calculation details |
| Grafana SLO Best Practices | https://grafana.com/docs/grafana-cloud/alerting-and-irm/slo/best-practices/ | Grafana-native SLO management |
| Grafana SLO Terraform | https://grafana.com/docs/grafana-cloud/alerting-and-irm/slo/set-up/terraform/ | SLO-as-code with Terraform |
| SLO Burn Panel (Grafana) | https://github.com/dyfimas/slo-burn-panel | Open source burn rate panel |
| Security SLOs (zero budget) | https://github.com/Dicklesworthstone/pi_agent_rust/blob/main/docs/security/security-slos.md | Safety invariant SLO pattern |
| FinOps × SRE Integration | https://zakhassan.com/blog/finops-meets-sre-why-cloud-cost-is-now-a-reliability-discipline | Cost as reliability discipline |
| Closed-Loop Budget Brake | https://zop.dev/resources/blogs/closed-loop-budget-brake-daily-cap-runaway/ | Auto cost freeze pattern |
| SRE FinOps Error Budget | https://medium.com/@mrkoozer/sre-meets-finops-error-budgets-for-spend-e468d1f6c298 | Spend error budget model |
| FinOps for SREs | https://dev.to/june-gu/finops-for-sres-cutting-costs-without-breaking-things-2fbk | Production FinOps+SRE guardrails |
| Infrastructure Guide FinOps | https://github.com/mghabin/infra-engineering-guide/blob/main/docs/10-finops.md | Budget burn-rate + kill-switch |
| Practical Prometheus SLOs | https://oneuptime.com/blog/post/2026-01-25-prometheus-slo-monitoring/ | Complete PromQL recipes |
| Practical SLO Guide | https://devops-daily.com/posts/slos-slis-error-budgets-practical-guide | Step-by-step implementation |
| SLO Engineering Depth | https://sujeet.pro/articles/slos-slis-error-budgets | Comprehensive SLO reference |
| Grafana Dashboard Design | https://devopsil.com/articles/2026-03-21-grafana-dashboard-design-sre-principles/ | Dashboard as code patterns |
| Observability as Code | https://codelit.io/blog/observability-as-code | OpenSLO + Terraform + CI/CD |
| CalibreOS SLO Design | https://www.calibreos.com/learn/prod-slo-error-budgets | Error budget + burn rate primer |
| BackendBytes SRE Guide | https://backendbytes.com/articles/sre-slos-slis-error-budgets/ | Production SLO playbook |
| YoungJu SRE Guide | https://www.youngju.dev/blog/observability/2026-03-13-sli-slo-error-budget-reliability-engineering-guide.en | End-to-end implementation guide |

---

## Status

- **Output file**: `research-reports/2026-05-30-slo-sla-external-references.md`
- **Byte size**: ~27 KB
- **Sources consulted**: 40+ across Google SRE, Nobl9, Sloth, OpenSLO, Grafana, Prometheus, FinOps, security-SRE integration
- **Key discovery**: The multi-window multi-burn-rate alerting pattern from Google's SRE Workbook (Iteration 6) is the industry consensus gold standard, and OpenSLO + Sloth provide the SLO-as-code tooling needed for Guinevere's documentation-as-code approach. Safety invariants with zero error budget are well-documented in security-SRE literature (pi_agent_rust) and are critical for Guinevere's safety persona requirements.
- **Next step**: Generate `Guinevere_SLO_SLA_ErrorBudget_v1.0.md` using patterns documented here, with PromQL recording rules, burn-rate alerts, zero-budget safety invariants, and monthly scorecard definition.

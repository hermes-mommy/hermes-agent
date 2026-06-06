# Runbook: GuinevereHermesBudgetNearCap / Cost Anomaly

> Alerts: `GuinevereHermesBudgetNearCap`, cost anomaly detection rules
> Severity: High (Sev-2)
> RTO: 2 hours
> RPO: Not applicable (monitoring / cost alert)
> Version: 1.0
> Date: 2026-06-06

---

## Trigger

This runbook activates when any of the following conditions occur:

- Prometheus alert `GuinevereHermesBudgetNearCap` fires (daily or monthly LLM API cost exceeds the configured budget threshold, e.g., >80% of daily cap within the first 12 hours).
- Cost tracking dashboard shows an unusual spike in per-request cost or request volume (>2x standard deviation from 7-day rolling average).
- 9Router or provider API usage dashboard shows unexpected consumption patterns.
- Discord notification from the cost monitor indicates budget threshold breached.

## Severity Classification

| Severity | Condition |
|---|---|
| Sev-2 (High) | Near-cap alert (>80% budget consumed) with clear cause identified (burst of legitimate usage). |
| Sev-1 (Critical) | Budget cap breached OR cost spike exceeding 3x normal without identifiable cause. |
| Sev-3 (Medium) | Cost anomaly detected but within budget, cause is known and non-critical. |

Default classification: **Sev-2** until the cause is identified.

## Immediate Safety Checks

Before investigating cost, verify these safety conditions:

1. **Operator awareness.** Notify Faiz of the budget alert. Cost anomalies may indicate abuse, misconfiguration, or a runaway agent loop.
2. **Agent loop check.** Confirm no agent loop entered an uncontrolled retry or infinite loop that is burning tokens.
3. **Blocked request impact.** If safety blocks spiked concurrently (check `GuinevereHermesSafetyBlocksSpike`), blocked requests may still incur cost if the LLM was called before the safety gate.
4. **Authentication check.** Verify that no unauthorized API usage is occurring (leaked keys, stolen credentials).
5. **Do not disable cost tracking.** Cost controls must remain active to prevent unbounded spend.

## Investigation

### Step 1: Quantify the anomaly

```bash
# Check current LLM call metrics (if Hermes metrics are available)
curl -s http://localhost:9191/metrics | grep "hermes_llm"

# Check 9Router usage logs
journalctl -u 9router.service --no-pager -n 100 | grep -i "cost\|usage\|request\|token"

# Check provider dashboard (manual step via browser)
# 9Router dashboard: API key usage, per-model spending
```

### Step 2: Identify the source

Review recent activity for cost-driving patterns:

- **Abnormal request volume.** Sudden increase in requests per minute from a specific source.
- **Long context requests.** Requests with large token counts (memory dump, file analysis, long conversation history).
- **Expensive model usage.** Check if requests are being routed to GPT-5.5 instead of DeepSeek V4 Flash (the cheaper option).
- **Retry storms.** Agent retry loops due to provider errors or timeouts.
- **Sub-agent swarm.** Sudden increase in sub-agent spawns during a complex task.

### Step 3: Check for retry storms

```bash
# Check Hermes log for retry patterns
journalctl -u hermes-gateway.service --no-pager -n 200 | grep -i "retry\|timeout\|error\|429\|rate.\\?limit"

# Check error rate
journalctl -u hermes-gateway.service --no-pager -n 500 | grep -c "error"
```

### Step 4: Review recent deployments

- Check if a new feature, command, or integration was recently added that could increase cost.
- Check if a model routing config was changed.
- Review git log for changes to `hermes-config/config.yaml` or 9Router config.

### Step 5: Correlate with other alerts

- Check `GuinevereHermesSafetyBlocksSpike` for concurrent safety spikes (abuse or loop).
- Check `GuinevereHermesGatewayDown` for service interruptions that may trigger retry storms.

## Remediation

### A. Identify and stop the cost-driving process

1. If a specific agent loop, sub-agent swarm, or retry storm is the cause, terminate the process.
2. If the cause is a new feature or integration, consider disabling or rate-limiting it.
3. If the cause is a misconfigured model route (e.g., all requests hitting GPT-5.5), correct the routing configuration.

### B. Rate limiting

If request volume from a specific source exceeds normal bounds:

1. Apply rate limiting at the gateway level.
2. Increase the cooldown between autonomous agent cycles.
3. Reduce the maximum allowed sub-agent parallelism.

**Important:** Rate limiting should be targeted, not global. Do not block legitimate operator commands.

### C. Model routing adjustment

If cost is driven by expensive model usage:

1. Verify the routing config prioritizes DeepSeek V4 Flash for sub-agent tasks.
2. Reserve GPT-5.5 for complex reasoning and operator-facing interactions.
3. Consider switching to a cost-capped model for routine operations.

### D. Budget threshold escalation

If budget is near cap and cost is not abating:

1. Notify Faiz with the current burn rate and estimated time-to-cap.
2. Prepare to switch to cost-saving mode (reduce model quality, limit context, reduce sub-agent count).
3. If cap is breached, document the overage for FinOps model adjustment.

**Console-access safeguard:** All config changes that affect routing or rate limits must be staged and verified before apply. Keep a parallel session open.

## Verification

After remediation, confirm cost is within expected bounds:

```bash
# Check current cost metrics
curl -s http://localhost:9191/metrics | grep "hermes_llm_cost"

# Verify request rate is normal
journalctl -u hermes-gateway.service --no-pager -n 50 | grep -c "request"

# Check alert status should be resolving
# In Grafana: check GuinevereHermesBudgetNearCap alert
```

Verify that the cost burn rate has returned to the 7-day rolling average within 15 minutes.

## Escalation

| Level | Condition | Action |
|---|---|---|
| L1 | Cost anomaly persists after rate limiting | Escalate to operator with burn rate analysis. |
| L2 | Budget cap breached with no clear cause | Investigate for credential compromise. Rotate API keys if suspected. |
| L3 | Model routing change needed but operator is unavailable | Implement conservative routing (cheapest model only) as emergency measure. |
| L4 | Unauthorized API usage detected | Rotate all API keys. Suspend affected integrations. Initiate security incident. |

## Rollback / Console-Access Safeguard

All remediation steps that modify routing, rate limits, or cost controls MUST follow these safeguards:

1. **Record current config.** Before making changes, record the current routing and cost configuration.
2. **Stage before apply.** Prepare the new config alongside the current one. Verify syntax before applying.
3. **One change at a time.** Change one variable per remediation round.
4. **Know the rollback.** Before applying a cost config change, know exactly how to revert it to the previous values.
5. **Timebox.** If the anomaly is not identified and contained within 2 hours, escalate to Sev-1.
6. **Key rotation.** If unauthorized usage is suspected, rotate the affected API key immediately. Do not wait for investigation to complete.

## Related Resources

- FinOps model: `docs/70-finops/70-Cost_FinOps_Model_v1.1.md`
- Prometheus alert rules: `monitoring/prometheus/rules/guinevere-alerts.yml`
- Cost dashboard: `guinevere-hermes.json` (Cost panels)
- Model routing: `hermes-config/config.yaml`
- Blocker register: B12 (Hermes-native metrics not exported making cost tracking incomplete)

---

## Footer

Document version: 1.0
Date: 2026-06-06
Status: Phase 7b local artifact. Cost monitoring is not yet deployed on VPS. This runbook documents planned procedures.

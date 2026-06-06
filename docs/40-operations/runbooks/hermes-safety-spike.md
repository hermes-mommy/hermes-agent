# Runbook: GuinevereHermesSafetyBlocksSpike

> Alert: `GuinevereHermesSafetyBlocksSpike`
> Severity: High (Sev-2)
> RTO: 1 hour
> RPO: Not applicable (monitoring alert)
> Version: 1.0
> Date: 2026-06-06

---

## Trigger

This runbook activates when any of the following conditions occur:

- Prometheus alert `GuinevereHermesSafetyBlocksSpike` fires (safety block rate exceeds the configured threshold, e.g., >10 blocks per minute averaged over 5 minutes).
- Discord bot reports repeated safety blocks (e.g., "message blocked by safety filter" multiple times in rapid succession).
- Hermes gateway logs show a surge in `safety_plugin` rejections or HARD STOP activations.
- Operator reports unexpected refusal of legitimate commands by the safety system.

## Severity Classification

| Severity | Condition |
|---|---|
| Sev-2 (High) | Safety block rate is elevated (>10/min) but no HARD STOP is active. Core agent loop continues for non-blocked requests. |
| Sev-1 (Critical) | Safety block rate is critical (>50/min) OR a HARD STOP loop is detected (repeated auto-trigger with no operator input). |
| Sev-3 (Medium) | Safety block rate is slightly elevated (3-10/min) with clear false-positive patterns. |

Default classification: **Sev-2** until investigation reveals a HARD STOP loop.

## Immediate Safety Checks

Before any remediation action, verify these safety conditions:

1. **Operator safety.** Confirm Faiz is not in distress. If this alert coincides with a distress signal or HARD STOP, follow the distress protocol instead.
2. **False positive assessment.** Determine whether the blocks are correct (blocking actual policy violations) or false positives (blocking legitimate requests).
3. **Yandere boundary.** Verify no Y6 boundary breach is in progress. If Y6 is suspected, activate immediate persona freeze.
4. **Consent revocation.** Confirm no consent revocation event triggered the safety system as a side effect.
5. **Do not disable safety.** Under no circumstances should safety filtering be disabled or bypassed to clear this alert. Safety blocks protect the operator and system.

## Investigation

### Step 1: Identify blocked requests

```bash
# Check safety plugin logs
journalctl -u hermes-gateway.service --no-pager -n 200 | grep -i "safety\|block\|reject\|HARD STOP"

# Check Hermes safety log if available
cat /var/log/guinevere/safety.log 2>/dev/null | tail -100
```

### Step 2: Classify the blocks

Review the blocked request patterns:

- **Policy violations.** Messages that genuinely violate persona safety policy (Y4/Y5 boundary, consent, surveillance rules). These are correct blocks.
- **False positives.** Messages that are legitimate but trigger safety rules due to overly broad patterns or missing context.
- **Prompt injection.** Requests that attempt to bypass safety constraints or impersonate operator authority.
- **Loop behavior.** The safety system blocking, then being retriggered by the same input, creating a loop.

### Step 3: Check for HARD STOP activation

```bash
# Check HARD STOP handler logs
journalctl -u hermes-gateway.service --no-pager -n 50 | grep -i "hard_stop\|hardstop"

# Check HARD STOP sentinel
systemctl is-active hard-stop-monitor.service 2>/dev/null
```

### Step 4: Review recent changes

- Check if persona or safety policy files were recently modified.
- Review recent git changes to `docs/60-persona/`, `src/persona/`, `src/hermes/safety_plugin.py`.
- Check if a new prompt injection vector was discovered and patched.

### Step 5: Correlate with other alerts

- Check if `GuinevereHermesBudgetNearCap` fired concurrently (cost pressure correlating with safety blocks suggests abuse or loop).
- Check if `GuinevereHermesGatewayDown` fired before or after the safety spike.

## Remediation

### A. False positive adjustment

If the blocks are false positives:

1. Identify the triggering pattern (specific phrase, command, or context).
2. Adjust the safety rule pattern to exclude the legitimate use case.
3. Test the adjustment with the exact input that triggered the block.
4. Deploy the updated safety configuration.

**Important:** Do not broaden exceptions beyond the specific false-positive case. Overly broad exceptions create safety gaps.

### B. HARD STOP loop resolution

If a HARD STOP loop is detected (Sev-1):

1. Follow the HARD STOP resolution procedure in `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`.
2. If the loop persists, manually reset the persona state.
3. Disable autonomous agent loop until operator confirms safety.
4. **Do not restart the gateway** until the HARD STOP loop root cause is identified.

### C. Prompt injection response

If prompt injection is detected:

1. Log the injection attempt for security review.
2. Update the prompt injection filter patterns.
3. Consider temporary rate-limiting on the affected channel.
4. Coordinate with the security policy defined in `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md`.

### D. Threshold adjustment

If the alert threshold is too sensitive for legitimate usage patterns:

1. Review the block rate over the past 7 days to establish a baseline.
2. Adjust the alert threshold in `monitoring/prometheus/rules/guinevere-alerts.yml`.
3. Confirm the new threshold would not mask genuine safety issues.
4. Deploy the updated alert rule.

**Console-access safeguard:** If deploying config changes remotely, stage the change first, verify syntax, and keep a parallel session open.

## Verification

After remediation, confirm the safety system is working correctly:

```bash
# Check block rate has decreased
journalctl -u hermes-gateway.service --no-pager -n 50 | grep -c "safety.*block"

# Verify the service is healthy
systemctl is-active hermes-gateway.service

# Check alert status (should be pending or resolved)
# In Grafana: check GuinevereHermesSafetyBlocksSpike alert
```

If false-positive adjustment was applied, test with the original triggering input to confirm it now passes.

## Escalation

| Level | Condition | Action |
|---|---|---|
| L1 | False positives persist after adjustment | Escalate to operator with details of the remaining blocked patterns. |
| L2 | HARD STOP loop detected | Immediate escalation to operator. Activate distress protocol if operator is unresponsive. |
| L3 | Prompt injection bypass confirmed | Escalate to security lead. Initiate security incident procedure. |
| L4 | Safety system itself is compromised | Declare Sev-1 incident. Isolate gateway from external input. Initiate DR plan. |

## Rollback / Console-Access Safeguard

All remediation steps that modify safety configuration or service state MUST follow these safeguards:

1. **Backup current config.** Before modifying safety rules, back up the current configuration.
2. **Stage before apply.** Prepare the new safety config alongside the current one. Verify the syntax before replacing.
3. **One change at a time.** Change one rule or threshold per remediation round. Verify effectiveness before proceeding.
4. **Never disable safety.** If the only way to clear the alert is to disable safety filtering, escalate immediately instead.
5. **Timebox.** If the safety spike is not resolved within 1 hour, escalate to Sev-1 incident.

## Related Resources

- Safety policy: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`
- Prompt injection policy: `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md`
- Prometheus alert rules: `monitoring/prometheus/rules/guinevere-alerts.yml`
- Dashboard: `guinevere-hermes.json` (Safety panels)
- Safety plugin: `src/hermes/safety_plugin.py`
- HARD STOP handler: `src/core/services/hard_stop_handler.py`

---

## Footer

Document version: 1.0
Date: 2026-06-06
Status: Phase 7b local artifact. Safety monitoring is not yet deployed on VPS. This runbook documents planned procedures.

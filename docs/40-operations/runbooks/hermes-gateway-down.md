# Runbook: GuinevereHermesGatewayDown

> Alert: `GuinevereHermesGatewayDown`
> Severity: Critical (Sev-1)
> RTO: 30 minutes
> RPO: Not applicable (stateless gateway)
> Version: 1.0
> Date: 2026-06-06

---

## Trigger

This runbook activates when any of the following conditions occur:

- Prometheus alert `GuinevereHermesGatewayDown` fires (Hermes gateway endpoint unreachable for >60 seconds).
- Discord bot reports `Hermes Gateway: disconnected` or fails to respond to slash commands.
- Manual `curl` or `nc` check against the gateway port returns connection refused or timeout.
- `systemctl status hermes-gateway` shows the service as failed, dead, or inactive.

## Severity Classification

| Severity | Condition |
|---|---|
| Sev-1 (Critical) | Gateway is down AND no failover path exists. Core agent loop is broken. |
| Sev-2 (High) | Gateway is down but MCP tool fallback or secondary channel is operational. |
| Sev-3 (Medium) | Gateway is intermittent or returns partial errors. Core loop still functions. |

Default classification: **Sev-1** until proven otherwise.

## Immediate Safety Checks

Before any remediation action, verify these safety conditions:

1. **HARD STOP status.** Confirm the operator has not triggered HARD STOP. If HARD STOP is active, the gateway may be intentionally down.
2. **Consent boundary.** Verify no consent revocation or surveillance pause is in effect that would prevent gateway restart.
3. **Session state.** Confirm no critical agent loop or memory write is in progress that could be corrupted by a restart.
4. **Operator awareness.** Notify Faiz via Discord or configured escalation channel before modifying gateway state.

## Investigation

### Step 1: Verify the alert

```bash
# Check gateway process
systemctl status hermes-gateway.service

# Check recent journal logs
journalctl -u hermes-gateway.service --no-pager -n 100

# Check if the port is listening
ss -tlnp | grep 9191
```

### Step 2: Check dependencies

```bash
# Check MCP service
systemctl status guinevere-mcp.service

# Check Redis (gateway cache/dependency)
redis-cli ping

# Check 9Router (LLM routing proxy)
curl -s -o /dev/null -w "%{http_code}" http://localhost:20128/health
```

### Step 3: Inspect Hermes config

```bash
# Validate configuration
hermes validate 2>&1

# Check for known line 443 fallback warning
grep -n "fallback" hermes-config/config.yaml
```

### Step 4: Check resource constraints

```bash
# Memory and CPU
free -m
top -b -n 1 -p $(pgrep -f hermes)

# Disk space
df -h /var/log/guinevere/
```

### Step 5: Review recent changes

- Check the last git commit and deployment logs for changes to Hermes config, systemd unit, or dependencies.
- Review recent operator commands or automated maintenance that may have affected the gateway.

## Remediation

### A. Service restart (safe path)

If logs indicate a transient failure (OOM, dependency timing, config reload):

```bash
sudo systemctl restart hermes-gateway.service
```

**Console-access safeguard:** If performing this remotely, keep a second SSH session open. Verify the service restarts and responds before closing the first session.

### B. Dependency restart

If Redis, PostgreSQL, or 9Router is unresponsive:

1. Restart the failing dependency.
2. Wait for it to report healthy.
3. Restart `hermes-gateway.service`.

**Console-access safeguard:** Restart dependencies one at a time. Verify each dependency is healthy before moving to the next.

### C. Config rollback

If the failure correlates with a recent config change:

```bash
# Identify the change
git log --oneline -5 hermes-config/config.yaml

# Rollback the last config change
git checkout HEAD~1 -- hermes-config/config.yaml

# Restart the service
sudo systemctl restart hermes-gateway.service
```

**Console-access safeguard:** Stage the rollback file without applying. Confirm the correct file content with `git diff` before restarting the service.

### D. Full service reset (last resort)

If standard restart fails:

```bash
sudo systemctl stop hermes-gateway.service
sudo systemctl reset-failed hermes-gateway.service
sudo systemctl start hermes-gateway.service
```

**Do not** modify firewall, SSH config, or port bindings as part of gateway remediation. Those changes belong to Phase 7c planning.

## Verification

After remediation, confirm the gateway is operational:

```bash
# Service status
systemctl is-active hermes-gateway.service

# Port listening
ss -tlnp | grep 9191

# Metrics endpoint
curl -s http://localhost:9191/metrics | head -20

# Log response
journalctl -u hermes-gateway.service --no-pager -n 20
```

Verify the alert clears within two Prometheus scrape cycles (default: 2 minutes).

## Escalation

| Level | Condition | Action |
|---|---|---|
| L1 | Gateway restarts but fails again within 5 minutes | Escalate to operator (Faiz) via Discord. |
| L2 | Redis or PostgreSQL dependency is down | Follow DR runbook for the failed dependency. |
| L3 | Config rollback does not resolve the issue | Declare Sev-1 incident. Initiate DR plan. |
| L4 | VPS-level issue (SSH down, kernel panic) | Console access via VPS provider. Declare Sev-1. |

## Rollback / Console-Access Safeguard

All remediation steps that modify running services MUST follow these safeguards:

1. **Keep a parallel session.** Before modifying any service state, open a second SSH session and keep it alive.
2. **Stage before apply.** For config changes, prepare the new file alongside the existing one. Do not delete or overwrite the old file until the new one is verified.
3. **One change at a time.** Change one variable (service, config, dependency) per remediation round. Verify before proceeding.
4. **Know the rollback command.** Before applying a change, know exactly how to revert it.
5. **Timebox.** If the gateway is not restored within 30 minutes, escalate to Sev-1 incident and follow the DR plan.

## Related Resources

- Prometheus alert: `GuinevereHermesGatewayDown`
- Alertmanager routing: `guinevere-hermes` route
- Dashboard: `guinevere-hermes.json`
- Service definition: `systemd/hermes-gateway.service`
- Blocker register: B1, B3, B9

---

## Footer

Document version: 1.0
Date: 2026-06-06
Status: Phase 7b local artifact. Gateway is not yet deployed. This runbook documents planned procedures.

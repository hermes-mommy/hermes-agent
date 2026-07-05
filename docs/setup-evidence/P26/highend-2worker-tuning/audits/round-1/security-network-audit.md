# P26 High-End 2-Worker Tuning - Round 1 Security/Network Audit

| Field | Value |
|---|---|
| Task | Round 1 security/network audit |
| Evidence root | `docs/setup-evidence/P26/highend-2worker-tuning` |
| Output path | `docs/setup-evidence/P26/highend-2worker-tuning/audits/round-1/security-network-audit.md` |
| VPS target | `root@49.12.82.34 -p 39999` |
| Audit date | 2026-06-27 |
| Audit mode | Read-only |
| VPS mutation performed | No |
| Local files changed | This audit file only |
| Secrets printed | No |

## Verdict

**PASS WITH SECURITY CAVEATS.**

The P26 high-end 2-worker tuning did not appear to mutate SSH, Tailscale, or firewall state. Live read-only checks at `2026-06-27T18:17:15+07:00` matched the pre/post evidence for the security/network boundary: SSH still works through the requested target, `tailscaled` remains active in userspace mode, the targeted IPv4 firewall rule still drops public `20128` on `venet0`, the app remains reachable over Tailscale, and public IPv4 `49.12.82.34:20128` remains blocked.

Completion is not a general hardening PASS. The known baseline caveats remain: SSH is still broadly exposed with root login and password authentication enabled, IPv6 INPUT remains default ACCEPT with no explicit `20128` rule, and protection of app port `20128` relies on the current IPv4 bind/firewall posture. These were pre-existing/out-of-scope for P26 tuning and must not be silently treated as resolved.

## Scope and Sources Read

### Local Evidence

- `AGENTS.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/research/security-network-analysis.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/implementation/os-network-tuning.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/implementation/pm2-node-tuning.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/implementation/sqlite-tuning.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/verification/pre-tuning-snapshot.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/verification/post-tuning-snapshot.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/fixes/round-1-fix-log.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/loadtest/post-tuning-loadtest.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/plan/p26-highend-2worker-tuning-plan.md`

### Live Read-Only Checks

Ran read-only SSH checks against `root@49.12.82.34 -p 39999`:

- Host/date/hostname.
- `systemctl is-active` and `systemctl show` for `ssh`, `tailscaled`, `pm2-root`, legacy `9router`, and `apache2`.
- `sshd -T` for SSH posture.
- `tailscale version`, `tailscale ip -4`, `tailscale status --self --peers=false`.
- `ip -br addr`.
- `ss -H -tulpen`.
- `iptables -S INPUT`.
- `ip6tables -S INPUT`.
- Local VPS `/v1/models` HTTP status check without Authorization headers.
- `pm2 status --no-color`.

Ran local operator probes:

- `http://100.104.210.75:20128/v1/models` over Tailscale.
- `http://49.12.82.34:20128/v1/models` over public IPv4.

Ran local evidence secret scan using redacted/count-only matching; no matching secret values were printed.

## Security/Network Findings

### P0/P1 Findings

None for the P26 security/network tuning boundary.

No evidence showed firewall flush/reset, Tailscale mode change, SSH service/config mutation, public IPv4 app exposure, or secret leakage in the P26 evidence tree.

### P2 - Baseline SSH Is Still Broadly Exposed

Status: **KNOWN CAVEAT, OUT OF SCOPE FOR THIS TUNING BATCH**

Live `sshd -T` still reports:

- `port 22`
- `listenaddress 0.0.0.0:22`
- `listenaddress [::]:22`
- `permitrootlogin yes`
- `passwordauthentication yes`
- `pubkeyauthentication yes`
- `x11forwarding yes`
- `allowtcpforwarding yes`
- `permitopen any`

This matches the research baseline and does not appear introduced by P26. It is still a security risk. Do not perform SSH hardening inside this tuning batch without explicit approval and recovery-console fallback, because changing SSH/firewall/provider exposure could lock out access.

### P2 - IPv6 App Exposure Remains a Latent Risk

Status: **KNOWN CAVEAT, NOT CURRENTLY ACTIVE FOR APP PORT**

Live `ip6tables -S INPUT` reports only:

```text
-P INPUT ACCEPT
```

There is no explicit IPv6 `20128` block. Live `ss -H -tulpen` did not show `[::]:20128`; the app listener remains IPv4-only at `0.0.0.0:20128`. Therefore, the IPv6 risk is latent at audit time, not active public app exposure.

Hard rejection condition for future work: if `20128` ever binds to `[::]` while IPv6 INPUT remains default ACCEPT with no explicit protection, security/network completion must fail.

### P3 - `tailscale0` Firewall Rule Is Still Not Proof of Tailscale Enforcement

Status: **KNOWN CAVEAT**

The IPv4 firewall still contains:

```text
-A INPUT -i tailscale0 -p tcp -m tcp --dport 20128 -j ACCEPT
-A INPUT -i venet0 -p tcp -m tcp --dport 20128 -j DROP
```

But Tailscale remains in userspace networking mode and `ip -br addr` shows only `lo` and `venet0`, not `tailscale0`. This matches the earlier research interpretation: the public IPv4 block is real, but the `tailscale0` ACCEPT rule should not be treated as the mechanism proving Tailscale reachability.

## Required Boundary Checks

| Check | Evidence | Result |
|---|---|---|
| AGENTS.md read first | Session read before evidence/audit work | PASS |
| SSH reachable | Live SSH command completed at `2026-06-27T18:17:15+07:00` | PASS |
| SSH unchanged from evidence | Root/password/listen settings match security research | PASS WITH CAVEAT |
| Tailscale active | `systemctl` active/running; `tailscale ip -4` = `100.104.210.75` | PASS |
| Tailscale mode unchanged | `DropInPaths=/etc/systemd/system/tailscaled.service.d/override.conf`; research and post snapshot show userspace mode | PASS |
| Firewall unchanged | Live IPv4 INPUT rules match pre/post snapshots | PASS |
| Public IPv4 app blocked | Operator public IPv4 probe returned HTTP `000`, curl exit `7` | PASS |
| Tailscale app reachable | Operator Tailscale probe returned HTTP `200` | PASS |
| Local app reachable | VPS local `/v1/models` returned HTTP `200` | PASS |
| App not listening on IPv6 | `ss` shows `0.0.0.0:20128`, no `[::]:20128` | PASS |
| IPv6 caveat documented | IPv6 INPUT remains ACCEPT with no `20128` rule | PASS WITH CAVEAT |
| Secret leakage check | Local evidence regex scan returned `SECRET_SCAN_RESULT=PASS matches=0` | PASS |
| No VPS mutation by auditor | Only read-only commands used | PASS |

## Live State Summary

### Services

Live status:

```text
ssh: active
tailscaled: active
pm2-root: active
legacy 9router.service: inactive
apache2: inactive
```

This matches the expected P26 service posture.

### Tailscale

Live state:

```text
tailscale version: 1.98.4
tailscale IPv4: 100.104.210.75
self node: vps-9router
tailscaled ExecMainPID: 33592
tailscaled ActiveState/SubState: active/running
```

The evidence indicates userspace networking mode via the tailscaled override. No audit command changed Tailscale state.

### Listening Ports

Relevant live listeners:

```text
0.0.0.0:20128 - PM2 / 9Router app
0.0.0.0:22    - SSH
[::]:22       - SSH
0.0.0.0:64527 - tailscaled
0.0.0.0:41641 - tailscaled UDP
[::]:41641    - tailscaled UDP
```

No `[::]:20128` listener was observed.

### Firewall

Live IPv4 INPUT:

```text
-P INPUT ACCEPT
-A INPUT -i tailscale0 -p tcp -m tcp --dport 20128 -j ACCEPT
-A INPUT -i venet0 -p tcp -m tcp --dport 20128 -j DROP
```

Live IPv6 INPUT:

```text
-P INPUT ACCEPT
```

This matches the documented narrow firewall posture: targeted public IPv4 block for app port `20128`, no general deny-by-default firewall, no IPv6 app-port block.

### Endpoint Probes

| Probe | Result |
|---|---|
| VPS local `http://127.0.0.1:20128/v1/models` | HTTP `200`, `0.014476s` |
| Operator Tailscale `http://100.104.210.75:20128/v1/models` | HTTP `200`, curl exit `0`, `0.446513s` |
| Operator public IPv4 `http://49.12.82.34:20128/v1/models` | HTTP `000`, curl exit `7`, `3.177032s` |

The public IPv4 result is the desired block/failure state for this tuning batch.

## Secret Leakage Audit

Local scan covered the full evidence root:

```text
docs/setup-evidence/P26/highend-2worker-tuning
```

Patterns checked included common OpenAI-style keys, bearer headers, API key assignments, token assignments, password assignments, secret assignments, and private key headers. The scan returned:

```text
SECRET_SCAN_RESULT=PASS matches=0
```

Evidence reviewed also used redaction for PM2 env keys and did not print provider API keys, Authorization headers, cookies, Tailscale state files, SSH private keys, or raw `.env` contents.

## Implementation Boundary Review

### OS/Network Implementation

`implementation/os-network-tuning.md` states no OS/network mutation was performed. Live checks support that: firewall rules, Tailscale status, SSH posture, and app public exposure matched the earlier research and post snapshot.

### PM2/SQLite Implementation Effects

The implementation did mutate runtime files and restart the PM2 app, which was in scope for P26 after backup. Security/network impact from that restart was acceptable:

- PM2 still shows exactly two online `9router` workers.
- App stayed bound on IPv4 `0.0.0.0:20128`.
- Public IPv4 `20128` remained blocked.
- Tailscale `20128` remained reachable.
- No new IPv6 app listener appeared.

`pm2 save` was performed after the workers returned healthy. That is a PM2 state persistence action, but it did not alter SSH, Tailscale, or firewall state based on this audit.

## Acceptance Criteria Mapping

| Acceptance / Hard Rejection Item | Audit Result |
|---|---|
| SSH still works | PASS |
| Tailscale still active | PASS |
| Firewall not flushed/reset | PASS |
| Public IPv4 `20128` blocked | PASS |
| No `[::]:20128` app listener | PASS |
| IPv6 caveat documented | PASS |
| No firewall/Tailscale/SSH mutation evidence | PASS |
| No secrets in evidence | PASS |
| Worker count still 2 | PASS |
| No service restart by auditor | PASS |

## Recommendations

1. Keep P26 marked as passing security/network boundary checks only with caveats; do not call the host hardened.
2. Treat SSH hardening as a separate, explicitly approved task with recovery-console validation.
3. Add an IPv6 firewall decision before any future change that may bind the app to `[::]:20128`.
4. Continue using pre/post public IPv4, Tailscale, `ss`, `iptables`, and `ip6tables` checks for every future PM2/network-affecting tuning step.
5. Avoid relying on the `tailscale0` iptables ACCEPT rule as proof of access control while Tailscale runs in userspace networking mode.

## Final Audit Gate

**PASS WITH SECURITY CAVEATS** for P26 round-1 security/network scope.

The tuning preserved SSH reachability, Tailscale reachability, public IPv4 blocking for app port `20128`, and evidence secrecy. Existing SSH exposure and IPv6 firewall limitations remain documented caveats and should be handled outside this tuning batch.

## Footer

Round 1 security/network audit for Guinevere P26 high-end 2-worker tuning. Audit was read-only against the VPS and wrote only this local markdown report.

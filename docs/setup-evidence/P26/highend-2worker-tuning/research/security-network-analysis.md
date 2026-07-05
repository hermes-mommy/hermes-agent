# P26 High-End 2-Worker Tuning — Security and Network Read-Only Analysis

| Field | Value |
|---|---|
| Task | Security/network auditor read-only |
| Scope | P26 9Router VPS tuning, network/security state only |
| Output path | `docs/setup-evidence/P26/highend-2worker-tuning/research/security-network-analysis.md` |
| Workspace | `C:\Users\faizz\guinevere` |
| SSH target | `root@49.12.82.34 -p 39999` |
| Audit timestamp | 2026-06-27 |
| Mutations performed | None on VPS; only this markdown report was created locally |
| Secrets printed | No |

## Verdict

**NEEDS REVIEW before additional tuning.**

The VPS is reachable and 9Router is currently serving from a 2-worker PM2 cluster. Port `20128` is reachable over Tailscale and not reachable over the public IPv4 address during the audit. However, the host still has broad public SSH exposure characteristics (`PermitRootLogin yes`, `PasswordAuthentication yes`, SSH listening on all IPv4/IPv6 addresses) and the active firewall posture is narrow: it drops public IPv4 traffic to `20128`, but leaves the default INPUT policy at ACCEPT and has no IPv6 INPUT restrictions. This is acceptable for read-only status capture, but it is not a hardened baseline for further risky tuning.

## Read-Only Boundaries Used

This audit only ran read-only status and probe commands:

- SSH connectivity and host identity checks.
- `ip`, `ss`, `systemctl show/is-active/cat`, `iptables`, `ip6tables`, `tailscale status`, `tailscale ip`, `pm2 status`, `curl` probes.
- Local Windows `curl.exe` reachability probes to Tailscale IPv4 and public IPv4.

This audit did not:

- Restart services.
- Reload systemd.
- Edit firewall rules.
- Save firewall state.
- Stop or change Tailscale.
- Print environment files, API keys, tokens, DB contents, provider credentials, SSH private keys, or Tailscale state files.
- Modify VPS files.

## Live SSH and Host Status

| Check | Observed State |
|---|---|
| SSH target reachable | PASS |
| Hostname | `ninerouter-vps` |
| Audit time on VPS | `2026-06-27T18:00:45+07:00` |
| Kernel | `Linux 6.8.0 x86_64 GNU/Linux` |
| Uptime | `up 1 day, 5 hours, 12 minutes` |
| Default route | `default dev venet0 scope link` |
| Interfaces shown by `ip -br addr` | `lo`, `venet0` |
| Tailscale kernel interface shown | Not shown; consistent with userspace networking mode |

### SSH Daemon Posture

`sshd -T` reported:

| Setting | Value | Risk |
|---|---|---|
| `port` | `22` | Public target uses `39999`, likely provider/NAT forwarding to internal `22`; document this dependency before firewall changes. |
| `listenaddress` | `0.0.0.0:22`, `[::]:22` | SSH accepts on all IPv4 and IPv6 addresses. |
| `permitrootlogin` | `yes` | High risk; root login is exposed if network permits it. |
| `passwordauthentication` | `yes` | High risk; password auth is enabled. |
| `pubkeyauthentication` | `yes` | Good, but not sufficient while password auth remains enabled. |
| `kbdinteractiveauthentication` | `no` | Good. |
| `x11forwarding` | `yes` | Unnecessary for this server; expands SSH feature surface. |
| `allowtcpforwarding` | `yes` | Useful for admin, but should be intentional. |
| `permitopen` | `any` | Broad forwarding allowance. |
| `ssh.service` | `active` | Expected. |

Security interpretation: any performance tuning that touches SSH, firewall, Tailscale, provider NAT, or network stack must preserve current access while reducing exposure only through an explicit separate hardening task. For this tuning batch, SSH settings should be treated as **do not touch** unless Faiz explicitly approves a security-hardening change with recovery console access confirmed.

## Tailscale Status

| Check | Observed State |
|---|---|
| Tailscale version | `1.98.4` |
| Tailscale IPv4 | `100.104.210.75` |
| Node name | `vps-9router` |
| OS | `linux` |
| `tailscaled.service` | `active`, `running` |
| `ExecMainPID` | `33592` |
| Service file | `/usr/lib/systemd/system/tailscaled.service` |
| Drop-in | `/etc/systemd/system/tailscaled.service.d/override.conf` |
| ExecStart mode | `--tun=userspace-networking --port=41641` |

Important interpretation:

- Tailscale is intentionally running in userspace networking mode.
- `ip -br addr` did not show `tailscale0`, which is expected in userspace mode.
- Existing iptables includes an allow rule for `-i tailscale0`, but packet counters were `0`; this rule is not the main reason the Windows-to-Tailscale probe succeeded.
- Do not switch Tailscale back to kernel/TUN mode as part of performance tuning. Prior P26 evidence says Tailscale was restored by returning to `--tun=userspace-networking`; changing this can break connectivity on this container-style VPS.

## Firewall Status

| Layer | Observed State |
|---|---|
| UFW | Not installed or unavailable |
| nft | Not installed or unavailable |
| IPv4 INPUT policy | `ACCEPT` |
| IPv6 INPUT policy | `ACCEPT` |
| IPv4 rule 1 | `ACCEPT tcp dpt:20128` on `tailscale0`; packet counter `0` |
| IPv4 rule 2 | `DROP tcp dpt:20128` on `venet0`; packet counter `0` |
| IPv6 20128 rule | None |

Filtered `iptables-save` showed only the relevant active filter rules:

```text
*filter
:INPUT ACCEPT [3787354:5020446378]
-A INPUT -i tailscale0 -p tcp -m tcp --dport 20128 -j ACCEPT
-A INPUT -i venet0 -p tcp -m tcp --dport 20128 -j DROP
COMMIT
```

Security interpretation:

- The public IPv4 block for `20128` exists and was validated externally.
- The firewall is not a general deny-by-default firewall. It is a targeted block for `20128` on `venet0`.
- IPv6 has no explicit INPUT block. Current `ss` output did not show `20128` listening on IPv6, so the current risk is latent rather than active. If 9Router or PM2 changes to listen on `[::]:20128`, public IPv6 exposure becomes a hard blocker unless an IPv6 firewall rule is added first.
- Do not save or persist firewall state during this tuning batch unless the exact current rules have been verified and a rollback path exists. Saving a broken or incomplete runtime policy would make the mistake durable.

## Listening Ports

Live `ss -tulpen` showed:

| Proto | Listen Address | Port | Process / Role | Exposure Notes |
|---|---:|---:|---|---|
| TCP | `0.0.0.0` | `20128` | PM2 / 9Router | Intended app endpoint; reachable over Tailscale; public IPv4 blocked by iptables; not listening on IPv6 at audit time. |
| TCP | `0.0.0.0` | `22` | SSH | Public IPv4 SSH listener; external target uses port `39999`. |
| TCP | `[::]` | `22` | SSH | Public IPv6 SSH listener. |
| TCP | `0.0.0.0` | `64527` | Tailscale-related | Tailscale userspace/WireGuard listener. |
| UDP | `0.0.0.0` | `41641` | Tailscale | Tailscale WireGuard UDP. |
| UDP | `[::]` | `41641` | Tailscale | Tailscale WireGuard UDP IPv6. |
| TCP/UDP | `127.0.0.53`, `127.0.0.54` | `53` | systemd-resolved | Local DNS stub only. |
| TCP | `127.0.0.1`, `[::1]` | `25` | local MTA | Loopback only. |

Current app bind:

- `20128/tcp` is bound by PM2 and a 9Router worker.
- It is bound on IPv4 `0.0.0.0`, not `[::]`, at audit time.

## 9Router / PM2 Runtime Status

| Check | Observed State |
|---|---|
| `pm2-root.service` | `active` |
| legacy `9router.service` | `inactive` |
| `apache2.service` | `inactive` |
| `tailscaled.service` | `active` |
| `ssh.service` | `active` |
| PM2 app name | `9router` |
| PM2 mode | `cluster` |
| PM2 version column | `0.5.8` |
| Worker count | 2 online workers |
| Worker PIDs | `31108`, `31121` |
| Worker restarts | `4` each |
| Worker memory at audit | `245.7mb`, `312.8mb` |
| PM2 module | `pm2-logrotate` online |
| Local VPS endpoint | `http://127.0.0.1:20128/v1/models` returned HTTP `200` in `0.017289s` |
| Windows to Tailscale endpoint | `http://100.104.210.75:20128/v1/models` returned HTTP `200` in `0.435958s` |
| Windows to public endpoint | `http://49.12.82.34:20128/v1/models` failed to connect; curl exit `7` after `3.120423s` |
| `net.core.somaxconn` | `4096` |
| PM2 daemon NOFILE | `65535/65535` |
| Worker NOFILE | `65535/65535` for both workers |

## Safe Boundaries for Further Tuning

Allowed read-only checks:

- `systemctl is-active/show/status --no-pager` for relevant services.
- `pm2 status`, `pm2 describe`, `pm2 jlist` with no secret fields printed.
- `ss -tulpen`, `ip -br addr`, `ip route`, `iptables -S`, `iptables -L`, `ip6tables -S`, `ip6tables -L`.
- Local and Tailscale HTTP probes that do not include Authorization headers.
- `/proc/<pid>/limits`, `/proc/<pid>/status`, CPU/memory snapshots.
- Load tests only against non-mutating endpoints like `/v1/models`, and only if rate/volume is explicitly approved for the batch.

Allowed low-risk tuning only if separately planned and verified:

- PM2 worker count or Node heap tuning, with pre/post port and service checks.
- PM2/systemd file descriptor limits, if backup and rollback are documented.
- Kernel sysctls that are available in this container and do not affect connectivity, with before/after capture.

## What Must Not Be Touched

Do not touch in this P26 high-end tuning batch without explicit approval and a recovery path:

- `tailscaled.service`, `/etc/default/tailscaled`, or Tailscale state.
- Tailscale auth, logout, login, reset, `tailscale up`, `tailscale set`, ACLs, or keys.
- Firewall rules, firewall persistence, UFW/nft installation, iptables flush, default policy changes, provider firewall changes.
- SSH server config, root login, password auth, provider NAT mapping, or SSH port behavior.
- 9Router provider/account/API-key/token/database rows.
- `/var/lib/tailscale`, 9Router `.env`, PM2 dump contents if they include env, shell history, SSH private keys, decrypted secrets.
- Apache, exim, systemd-resolved, or unrelated services except read-only status checks.
- Any destructive or stateful operation: reboot, service restart, PM2 reload/restart, firewall reload, package upgrade, `pm2 save`, `systemctl daemon-reload`.

## Tuning Risks

| Risk | Why It Matters | Guardrail |
|---|---|---|
| Locking out SSH | SSH is public-facing and root/password-enabled; firewall/provider NAT assumptions are fragile. | Open two sessions and verify provider console before any future firewall/SSH change. |
| Breaking Tailscale | Userspace networking appears intentional for this VPS. | Do not change Tailscale mode or restart it in this batch. |
| Public `20128` exposure | 9Router listens on `0.0.0.0`; security relies on firewall/Tailscale path. | Pre/post public IPv4 and IPv6 probes must fail before completion. |
| IPv6 exposure | IPv6 INPUT is ACCEPT and has no `20128` block. | Hard reject if `ss` ever shows `[::]:20128` without a matching IPv6 block. |
| Incorrect confidence in `tailscale0` rule | `tailscale0` rule exists but interface is absent in userspace mode and packet count was `0`. | Treat Tailscale reachability as userspace-mode behavior, not as proof that the `tailscale0` iptables rule is active. |
| PM2 restart/reload exposure window | PM2 owns the app listener. Reloading can briefly change workers, bind behavior, or env. | Capture port binding and endpoint reachability before and after; do not reload unless planned. |
| Persisting bad firewall state | Current firewall is targeted, not comprehensive. | Do not run `iptables-save > ...`, `netfilter-persistent save`, or equivalent unless explicitly in scope. |
| Secret leakage | 9Router env/db/provider configs may contain tokens. | Do not print env files, DB rows with keys, PM2 env dumps, or Tailscale state. |

## Exact Pre-Checks for Any Future Tuning

Run these before tuning and save sanitized output to the batch evidence:

```bash
date -Is
hostname
uptime -p
ip -br addr
ip route show default
tailscale version | head -n 3
tailscale ip -4
tailscale status --self --peers=false
systemctl is-active tailscaled ssh pm2-root 9router apache2
systemctl show tailscaled --property=ActiveState,SubState,ExecMainPID,FragmentPath,DropInPaths --no-pager
sshd -T | grep -E '^(port|listenaddress|permitrootlogin|passwordauthentication|pubkeyauthentication|kbdinteractiveauthentication|x11forwarding|allowtcpforwarding|permitopen) '
iptables -S INPUT
iptables -L INPUT -n -v --line-numbers
ip6tables -S INPUT
ip6tables -L INPUT -n -v --line-numbers
ss -H -tulpen | sort
pm2 status --no-color
curl -sS -o /dev/null -w 'local http_code=%{http_code} time_total=%{time_total}\n' --max-time 5 http://127.0.0.1:20128/v1/models
sysctl net.core.somaxconn
grep 'Max open files' /proc/$(pgrep -f 'PM2 v' | head -n 1)/limits
```

Run these from the operator machine before tuning:

```powershell
curl.exe -sS -o NUL -w "tailscale http_code=%{http_code} time_total=%{time_total}`n" --max-time 8 http://100.104.210.75:20128/v1/models
curl.exe -sS -o NUL -w "public_ipv4 http_code=%{http_code} exit=%{exitcode} total=%{time_total}`n" --max-time 8 http://49.12.82.34:20128/v1/models
```

Expected pre-check results:

- SSH target works.
- `tailscaled`, `ssh`, and `pm2-root` are active.
- legacy `9router` and `apache2` remain inactive.
- PM2 shows exactly two online `9router` cluster workers unless worker-count tuning is explicitly the target.
- Local VPS `/v1/models` returns HTTP `200`.
- Tailscale `/v1/models` returns HTTP `200`.
- Public IPv4 `/v1/models` fails to connect or otherwise does not return application data.
- `ss` does not show `[::]:20128`.

## Exact Post-Checks for Any Future Tuning

After tuning, repeat all pre-checks and add:

```bash
pm2 status --no-color
pm2 describe 9router --no-color | sed -n '1,120p'
ss -H -tulpen | grep -E '(:20128|:22|:41641|:64527)' || true
iptables -L INPUT -n -v --line-numbers
ip6tables -L INPUT -n -v --line-numbers
curl -sS -o /dev/null -w 'local http_code=%{http_code} time_total=%{time_total}\n' --max-time 5 http://127.0.0.1:20128/v1/models
```

Run these from the operator machine after tuning:

```powershell
ssh -p 39999 -o BatchMode=yes -o StrictHostKeyChecking=yes root@49.12.82.34 "hostname; date -Is"
curl.exe -sS -o NUL -w "tailscale http_code=%{http_code} time_total=%{time_total}`n" --max-time 8 http://100.104.210.75:20128/v1/models
curl.exe -sS -o NUL -w "public_ipv4 http_code=%{http_code} exit=%{exitcode} total=%{time_total}`n" --max-time 8 http://49.12.82.34:20128/v1/models
```

Expected post-check results:

- SSH still works via `root@49.12.82.34 -p 39999`.
- `tailscaled.service` remains active and in userspace networking mode.
- PM2 has the planned worker count and all workers are online.
- 9Router still returns HTTP `200` locally and over Tailscale.
- Public IPv4 `20128` remains unreachable.
- No new public listener appears except approved SSH/Tailscale ports.
- No IPv6 `20128` listener appears unless IPv6 firewall protection is added and verified first.
- `iptables` and `ip6tables` rules did not unexpectedly change unless firewall work was explicitly in scope.

## Hard Rejection Criteria

Reject completion of any future tuning step if any of these are true:

1. SSH to `root@49.12.82.34 -p 39999` fails after tuning.
2. `tailscaled.service` is inactive, restarted unintentionally, or no longer uses `--tun=userspace-networking`.
3. `pm2-root.service` is inactive when PM2 is intended to supervise 9Router.
4. PM2 does not show the expected number of online `9router` workers.
5. `http://127.0.0.1:20128/v1/models` does not return HTTP `200`.
6. `http://100.104.210.75:20128/v1/models` does not return HTTP `200` from the operator machine.
7. `http://49.12.82.34:20128/v1/models` returns HTTP `200` or any application response from the public IPv4 path.
8. `ss` shows `[::]:20128` while `ip6tables` still has default ACCEPT and no explicit protection for port `20128`.
9. Any firewall rule is flushed, default policy changed, or firewall state persisted without an approved firewall-specific plan and rollback.
10. Any secret, token, API key, provider credential, Tailscale state, SSH private key, or raw env value appears in evidence.
11. SSH hardening is attempted in the tuning batch without explicit approval and recovery-console confirmation.
12. Tailscale ACL/auth/login/logout/up/set/reset actions are performed.

## Recommended Next Security Work Outside This Tuning Batch

These are separate security-hardening tasks, not part of this read-only audit:

- Move SSH toward key-only access and disable password authentication after confirming recovery console access.
- Disable direct root SSH or constrain it with a staged non-root sudo account plan.
- Decide whether SSH should remain publicly reachable or move to Tailscale-only with provider console fallback.
- Add explicit IPv6 protection for `20128` before any service bind behavior can include IPv6.
- Replace the narrow public `20128` drop with a documented, durable firewall baseline only after a separate firewall plan and rollback test.
- Clarify whether userspace Tailscale should remain permanent for this OpenVZ/Virtuozzo-style host.

## Boundary Compliance

| Boundary | Result |
|---|---|
| Read `AGENTS.md` first | PASS |
| VPS mutations avoided | PASS |
| Service restarts avoided | PASS |
| Firewall changes avoided | PASS |
| Tailscale changes avoided | PASS |
| Secrets avoided | PASS |
| Output written to requested path | PASS |

## Footer

Security/network auditor report for Guinevere P26 9Router VPS high-end 2-worker tuning. This report is evidence-only and does not authorize mutation of SSH, Tailscale, firewall, service, provider, or credential state.

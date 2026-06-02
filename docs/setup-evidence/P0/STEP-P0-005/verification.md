# STEP-P0-005 Verification — fail2ban Configuration

| Field | Value |
|---|---|
| Step | STEP-P0-005 |
| Title | fail2ban configuration (SSH brute force protection) |
| Date | 2026-05-31 |
| Host | faiz-prod-01 / 100.94.104.22 |
| Status | PASS, independent auditor gate passed |
| Implementer | Hephaestus / Guinevere workflow |

## 1. What Was Done

P0-005 configured fail2ban SSH brute-force protection on the shared VPS. Live discovery showed fail2ban was already installed, active, and had an Aizanta-specific jail file, so implementation used a preserve-existing drop-in rather than installing/purging or overwriting global `jail.local`.

Runtime changes:

- Created `/etc/fail2ban/jail.d/zz-guinevere-p0-005.local`.
- Backed up `/etc/fail2ban` to `/etc/fail2ban.backup.p0-005-20260531`.
- Configured `sshd` jail with `maxretry=3`, `findtime=600`, `bantime=86400`, `backend=systemd`, and UFW action.
- Added safe `ignoreip` list: localhost, VPS Tailscale IP `100.94.104.22`, and operator Windows Tailscale IP `100.112.201.124`.
- Restarted fail2ban after reload left runtime action stale; final runtime action is `ufw`.
- Validated UFW ban/unban behavior using TEST-NET IP `198.51.100.99` and removed the test ban afterward.

## 2. Files Changed

### VPS runtime files

Created:

- `/etc/fail2ban/jail.d/zz-guinevere-p0-005.local`

Created backup:

- `/etc/fail2ban.backup.p0-005-20260531`

Read-only / preserved:

- `/etc/fail2ban/jail.d/aizanta-sshd.local`

### Repository files

Created evidence:

- `docs/setup-evidence/P0/STEP-P0-005/fail2ban-status.txt`
- `docs/setup-evidence/P0/STEP-P0-005/fail2ban-jail-config.txt`
- `docs/setup-evidence/P0/STEP-P0-005/fail2ban-whitelist-proof.txt`
- `docs/setup-evidence/P0/STEP-P0-005/fail2ban-test.log`
- `docs/setup-evidence/P0/STEP-P0-005/aizanta-post-check.md`
- `docs/setup-evidence/P0/STEP-P0-005/p0-005-summary.md`
- `docs/setup-evidence/P0/STEP-P0-005/verification.md`

Planned tracker sync after this evidence file:

- `PROGRESS.md`
- `CHECKLIST.md`
- `stepprompts/StepPrompts.md`

## 3. Validation Results

### 3.1 SSH accessibility

Command from local Windows client:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "whoami && hostname"
```

Output:

```text
guinevere
faiz-prod-01
```

### 3.2 fail2ban package and service

Commands:

```bash
systemctl is-active fail2ban
dpkg-query -W fail2ban
```

Output:

```text
active
fail2ban	1.0.2-3ubuntu0.1
```

### 3.3 Global fail2ban status

Command:

```bash
fail2ban-client status
```

Output:

```text
Status
|- Number of jail:	1
`- Jail list:	sshd
```

### 3.4 sshd jail status after final cleanup

Command:

```bash
fail2ban-client status sshd
```

Output:

```text
Status for the jail: sshd
|- Filter
|  |- Currently failed:	1
|  |- Total failed:	1
|  `- Journal matches:	_SYSTEMD_UNIT=sshd.service + _COMM=sshd
`- Actions
   |- Currently banned:	37
   |- Total banned:	39
   `- Banned IP list:	103.12.135.35 103.200.25.198 103.67.80.61 103.85.66.217 113.193.234.210 118.26.36.195 141.98.9.227 152.32.132.28 156.245.246.50 165.22.34.238 171.25.158.70 182.253.156.184 185.175.170.125 185.195.13.17 185.227.153.56 185.246.128.170 194.164.193.54 2.57.122.238 20.203.59.187 200.155.66.2 202.53.94.246 209.99.184.143 210.90.155.178 211.253.37.225 222.98.122.37 31.220.89.126 43.165.3.187 45.231.116.119 5.253.59.68 5.99.196.202 64.89.161.56 68.66.251.43 69.73.187.130 78.44.192.210 79.3.96.178 89.167.67.234 89.190.156.8
```

### 3.5 Whitelist proof

Command:

```bash
fail2ban-client get sshd ignoreip
```

Output:

```text
These IP addresses/networks are ignored:
|- 127.0.0.0/8
|- 100.94.104.22
|- 100.112.201.124
`- ::1
```

### 3.6 UFW action proof

Commands:

```bash
fail2ban-client get sshd actions
fail2ban-client get sshd action ufw actionban
```

Output:

```text
The jail sshd has the following actions:
ufw

if [ -n "" ] && ufw app info ""
then
ufw prepend deny from <ip> to any app "" comment "by Fail2Ban after <failures> attempts against sshd"
else
ufw prepend deny from <ip> to any comment "by Fail2Ban after <failures> attempts against sshd"
fi
```

### 3.7 Safe TEST-NET ban/unban

Test IP: `198.51.100.99` (RFC 5737 TEST-NET; not operator IP).

Ban proof:

```text
1
   |- Currently banned:	38
   `- Banned IP list:	... 198.51.100.99
[ 1] Anywhere                   DENY IN     198.51.100.99              # by Fail2Ban after 0 attempts against sshd
```

Cleanup proof:

```text
1
   |- Currently banned:	37
   `- Banned IP list:	103.12.135.35 103.200.25.198 103.67.80.61 103.85.66.217 113.193.234.210 118.26.36.195 141.98.9.227 152.32.132.28 156.245.246.50 165.22.34.238 171.25.158.70 182.253.156.184 185.175.170.125 185.195.13.17 185.227.153.56 185.246.128.170 194.164.193.54 2.57.122.238 20.203.59.187 200.155.66.2 202.53.94.246 209.99.184.143 210.90.155.178 211.253.37.225 222.98.122.37 31.220.89.126 43.165.3.187 45.231.116.119 5.253.59.68 5.99.196.202 64.89.161.56 68.66.251.43 69.73.187.130 78.44.192.210 79.3.96.178 89.167.67.234 89.190.156.8
198.51.100.99 not present in UFW
198.51.100.99 not present in fail2ban jail
```

## 4. Evidence Artifacts

| Artifact | Purpose |
|---|---|
| `fail2ban-status.txt` | Final fail2ban package/service/jail/runtime status |
| `fail2ban-jail-config.txt` | Runtime drop-in content, Aizanta config preservation, backup proof |
| `fail2ban-whitelist-proof.txt` | `ignoreip` safety proof for localhost/VPS/operator Tailscale IPs |
| `fail2ban-test.log` | Safe TEST-NET ban/unban proof and cleanup |
| `aizanta-post-check.md` | Shared VPS Aizanta container/port health after P0-005 |
| `p0-005-summary.md` | Human-readable implementation summary and rollback |
| `verification.md` | This full evidence record |

Research/audit inputs:

- `audit-reports/P0/STEP-P0-005/internal-context-report.md`
- `audit-reports/P0/STEP-P0-005/evidence-pattern-report.md`
- `audit-reports/P0/STEP-P0-005/external-fail2ban-ubuntu-report.md`
- `audit-reports/P0/STEP-P0-005/external-fail2ban-lockout-report.md`

## 5. Shared VPS Impact

Aizanta health after P0-005:

```text
aizanta-bot Up 7 days (healthy) 8000/tcp
aizanta-nginx Up 7 days (healthy) 100.94.104.22:80->80/tcp
aizanta-frontend Up 7 days (healthy) 3000/tcp
aizanta-postgres Up 7 days (healthy) 127.0.0.1:5432->5432/tcp
aizanta-redis Up 7 days (healthy) 127.0.0.1:6379->6379/tcp
```

Protected ports after P0-005:

```text
LISTEN 0      4096                     127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0      4096                 100.94.104.22:80         0.0.0.0:*    users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0      4096                     127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=52721,fd=8))
```

Impact summary:

- No Aizanta containers were edited/restarted.
- No Aizanta Docker networks were touched.
- No Aizanta DB/Redis data was touched.
- No `/home/aizanta/` files were touched.
- Existing Aizanta fail2ban jail file was preserved.
- Fail2ban restart affected the shared fail2ban service but preserved the active ban list and restored UFW action correctly.

## 6. ADR Compliance

- ADR-018: strengthens defense-in-depth for SSH using fail2ban with UFW action, key-only SSH preserved, file-based evidence produced.
- ADR-019: supports access-control hardening while preserving Tailscale/operator access and avoiding lockout.
- ADR-014: respects shared VPS isolation; no Aizanta containers/networks/data touched.
- ADR-015 / AC-SEC-003: no plaintext secrets introduced; evidence contains only public IPs, service status, and config values.
- ADR-030/ADR-031: no Redis/PostgreSQL changes; canonical Redis DB/DB name decisions unaffected.

## 7. AC Reference

- AC-SEC-001: SSH brute-force protection is active; `sshd` jail enabled; UFW ban action verified with TEST-NET IP.
- P0-005 DoD: `sudo fail2ban-client status sshd` shows active jail and banned count listed.

## 8. Rollback / Re-run Safety

Preferred rollback:

```bash
sudo cp -a /etc/fail2ban /etc/fail2ban.rollback-before-p0-005-revert.$(date +%Y%m%d%H%M%S)
sudo rm -f /etc/fail2ban/jail.d/zz-guinevere-p0-005.local
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd
ssh guinevere-vps "whoami && hostname"
```

Full restore from backup:

```bash
sudo rm -rf /etc/fail2ban
sudo cp -a /etc/fail2ban.backup.p0-005-20260531 /etc/fail2ban
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd
```

Emergency lockout recovery:

```bash
sudo fail2ban-client set sshd unbanip <operator-ip>
sudo fail2ban-client unban --all
sudo systemctl stop fail2ban
```

Re-run safety:

- Rewriting the same drop-in is idempotent.
- Restarting fail2ban is safe after SSH and Aizanta guardrails.
- TEST-NET ban/unban is safe and leaves no persistent rule after cleanup.

## 9. Design Decisions / Caveats

- `jail.local` was not created because live VPS already used `jail.d` and had Aizanta-specific config.
- Fail2ban was already installed and active, so P0-005 hardened the existing installation instead of running a fresh install/purge flow.
- A controlled restart was required because reload updated some settings but left runtime action stale.
- Restart reset failure counters but preserved the active ban list.
- Existing hostile IP bans remain active in UFW as intended.
- `198.51.100.99` was used only as a temporary TEST-NET validation IP and was removed from both fail2ban and UFW.

## 10. Evidence Gate

Parent verification status: PASS.

Parent checks completed before auditor:

- Runtime fail2ban service active.
- `sshd` jail active.
- UFW action active and verified.
- Operator/VPS Tailscale whitelist active.
- SSH alias still works.
- Aizanta containers healthy and protected ports unchanged.
- Evidence files written.
- Tracker sync completed across `PROGRESS.md`, `CHECKLIST.md`, and `stepprompts/StepPrompts.md`.
- LSP diagnostics clean on touched markdown files.
- Secret scan over P0-005 evidence found no plaintext secrets.

Independent auditor gate: PASS.

Auditor report:

- `audit-reports/P0/STEP-P0-005/step-p0-005-auditor-report.md`

Auditor summary:

- Verdict: PASS.
- Blocking findings: 0.
- Live verification: fail2ban active, `sshd` jail enabled, UFW action active, TEST-NET IP cleaned up.
- Lockout safety: localhost, VPS Tailscale IP `100.94.104.22`, and operator Tailscale IP `100.112.201.124` whitelisted.
- Shared VPS safety: Aizanta containers healthy, protected ports unchanged, Aizanta fail2ban file preserved.
- Non-blocking observations: consider read-only `fail2ban-client` monitoring access for `guinevere`; evidence is point-in-time; `guinevere` cannot inspect shared fail2ban service via sudo by design.

## 11. Footer

Source task: STEP-P0-005 full autonomous
Date: 2026-05-31
Validation method: live SSH/fail2ban/UFW/Aizanta commands, file-based evidence, parent verification, independent auditor PASS
No commit was made.

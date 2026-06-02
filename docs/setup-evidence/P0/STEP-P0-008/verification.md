# STEP-P0-008 — NTP & Timezone Verification

| Field | Value |
|---|---|
| **Step** | P0-008 |
| **Type** | Infrastructure |
| **Date** | 2026-05-31 |
| **Implementer** | Guinevere (parent orchestrator) |
| **Status** | PASS, independent auditor gate passed |

## What Was Done

Set system timezone to Asia/Jakarta (WIB, UTC+7). Configured chrony (v4.5) with Indonesian NTP pools (`id.pool.ntp.org` + `0-3.id.pool.ntp.org`). Masked systemd-timesyncd to prevent dual-NTP conflict. Restarted time-sensitive services (fail2ban, crowdsec, crowdsec-firewall-bouncer, rsyslog).

## Files Changed

### Remote (VPS)
| File | Action |
|---|---|
| `/etc/chrony/chrony.conf` | Replaced Ubuntu pools with Indonesian pools |
| `/etc/chrony/chrony.conf.backup.p0-008-20260531` | Pre-change backup |
| `/etc/systemd/system/systemd-timesyncd.service` → `/dev/null` | Masked (systemd symlink) |

### Local (repo)
| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-008/chrony-status.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-008/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-008/p0-008-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-008/verification.md` | Created |
| `PROGRESS.md` | Updated counters, checked P0-008 |
| `CHECKLIST.md` | Checked P0-008 line |
| `stepprompts/StepPrompts.md` | Updated P0-008 status/checks |

## Validation Results

### Timezone
```
$ timedatectl status
Local time: Sun 2026-05-31 13:16:14 WIB
Time zone: Asia/Jakarta (WIB, +0700)
System clock synchronized: yes
NTP service: active
```

### Chrony Sources
```
MS Name/IP address         Stratum Poll Reach LastRx Last sample
^+ time.citra.net.id             2   6    17    18  -2083us[ -878us] +/-   37ms
^* 165.154.228.19                3   6    17    18  +2418us[+3624us] +/-   18ms
^+ pdns2.lunanet.id              2   6    17    20   -560us[ +645us] +/-   21ms
```

12 Indonesian sources, current best `^*` (selected) at Stratum 3.

### Service Health
```
$ systemctl is-active chrony fail2ban crowdsec crowdsec-firewall-bouncer
active
active
active
active
```

### Systemd-timesyncd
```
$ systemctl is-enabled systemd-timesyncd
masked
```

### SSH
```
$ ssh guinevere-vps "whoami && hostname && date"
guinevere  faiz-prod-01  Sun May 31 01:16:40 PM WIB 2026
```

### Aizanta Health
```
All 5 containers healthy (bot, nginx, frontend, postgres, redis)
Protected ports unchanged: 127.0.0.1:6379, 100.94.104.22:80, 127.0.0.1:5432
```

### P0-007 Intact
```
$ swapon --show
/swapfile file 4G 0B -2
$ df -h / | tail -1
/dev/vda1 99G 14G 81G 14% /
```

## Evidence Artifacts

| File | Description |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-008/chrony-status.txt` | Chrony state, sources, config, rollback |
| `docs/setup-evidence/P0/STEP-P0-008/aizanta-post-check.md` | Aizanta health after timezone/NTP |
| `docs/setup-evidence/P0/STEP-P0-008/p0-008-summary.md` | Human-readable summary |
| `docs/setup-evidence/P0/STEP-P0-008/verification.md` | This file |
| `audit-reports/P0/STEP-P0-008/external-chrony-report.md` | External research report |

## Shared VPS Impact

- **Aizanta**: No impact. Timezone change is host-level. Docker containers run in UTC by default.
- **Aizanta networks/ports/files**: None touched.
- **Guinevere**: WIB timezone applied. Chrony using Indonesian pools. Timesyncd masked.
- **Services restarted**: fail2ban, crowdsec, crowdsec-firewall-bouncer, rsyslog — all recovered.

## ADR Compliance

| ADR | Status |
|---|---|
| ADR-014 (VPS/container architecture) | Compliant — host-level config, no Aizanta impact |
| ADR-015 (Secrets management) | N/A — no secrets |
| ADR-018 (Defense-in-depth) | Compliant — accurate time essential for log correlation, fail2ban/CrowdSec |
| ADR-019 (Access control/VPN mesh) | N/A — no access change |

## AC Reference

| AC | Status |
|---|---|
| AC-CORE-001 (systemd-managed core daemon) | Compliant — chrony managed via systemd |
| AC-SEC-001 (security hardening) | Compliant — accurate time for audit logs and fail2ban/CrowdSec |

## Rollback / Re-run Safety

**Rollback**:
```bash
sudo cp /etc/chrony/chrony.conf.backup.p0-008-20260531 /etc/chrony/chrony.conf
sudo systemctl restart chrony
sudo systemctl unmask systemd-timesyncd
sudo timedatectl set-timezone Etc/UTC
sudo systemctl restart fail2ban crowdsec crowdsec-firewall-bouncer rsyslog
```

**Re-run safety**: `timedatectl set-timezone Asia/Jakarta` is idempotent. Chrony config can be rewritten safely if backup exists.

## Design Decisions / Caveats

1. **Chrony over systemd-timesyncd**: chrony was already active on the host; Ubuntu 24.04 defaults to chrony. Timesyncd only masked to prevent dual-NTP conflict.
2. **Indonesian pools**: `id.pool.ntp.org` with 4 maxsources + `0-3.id.pool.ntp.org` with 2 each = 12 sources, providing geographic diversity and redundancy.
3. **Docker UTC**: Containers not updated to WIB yet. Will set `TZ=Asia/Jakarta` at container deployment time (P1+).
4. **Service restarts**: fail2ban and CrowdSec restart preserved all active bans and CAPI state.
5. **DeploymentGuide doc-sync flag**: DeploymentGuide Step 12 references `systemd-timesyncd` — that doc is older/needs update.

## Evidence Gate

| Gate | Status |
|---|---|
| Parent verification | PASS — live checks confirm Asia/Jakarta, chrony active, Indonesian pools, timesyncd masked, services active, Aizanta healthy, SSH works |
| Evidence files | 4 evidence files created |
| Diagnostics | Clean |
| Secret scan | No matches |
| Tracker sync | PROGRESS, CHECKLIST, StepPrompts synced |
| Independent auditor gate | PASS — `audit-reports/P0/STEP-P0-008/step-p0-008-auditor-report.md` |

**Auditor summary**: 16/16 DoD PASS. Asia/Jakarta, chrony 4.5 with 12 Indonesian sources, sub-ms accuracy, timesyncd masked. All services active, Aizanta healthy, P0-007 intact, SSH WIB, no secrets, diagnostics clean. 2 non-blocking findings: no global NTP fallback (recommend add at P0-028), StepPrompts evidence filename mismatch (`timezone-ntp.txt` vs `chrony-status.txt`).

## Footer

**Source task**: STEP-P0-008 (from `stepprompts/StepPrompts.md`)
**Date**: 2026-05-31
**Implementer**: Guinevere (parent orchestrator, via direct SSH)
**Validation method**: Live SSH command execution + output capture
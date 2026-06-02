# STEP-P0-008 — NTP & Timezone Summary

## What Was Done

Set system timezone to Asia/Jakarta (WIB, UTC+7), configured chrony with Indonesian NTP pools, masked systemd-timesyncd.

## Runtime Changes (VPS)

| Change | Value |
|---|---|
| Timezone | `Etc/UTC` → `Asia/Jakarta` (WIB, +0700) |
| Chrony pools | Ubuntu defaults → `id.pool.ntp.org` + `0-3.id.pool.ntp.org` |
| Chrony config backup | `/etc/chrony/chrony.conf.backup.p0-008-20260531` |
| systemd-timesyncd | `inactive` → `masked` |
| Services restarted | fail2ban, crowdsec, crowdsec-firewall-bouncer, rsyslog |

## Local Changes

| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-008/chrony-status.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-008/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-008/p0-008-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-008/verification.md` | Created |
| `PROGRESS.md` | Updated: 8→9/257, P0 8→9/29 |
| `CHECKLIST.md` | P0-008 checked |
| `stepprompts/StepPrompts.md` | P0-008 status → ✅ Completed |

## Validation

- `timedatectl status`: Asia/Jakarta, synchronized yes, NTP active
- `chronyc sources`: 12 Indonesian NTP sources, best `^*` 165.154.228.19
- `systemctl is-active chrony fail2ban crowdsec crowdsec-firewall-bouncer`: all active
- Aizanta containers: all healthy, ports unchanged
- SSH: `guinevere-vps` shows WIB
- Swap (P0-007) intact

## Security

- No secrets involved.
- Chrony is client-only (no NTP server) — UFW already blocks inbound NTP implicitly via default deny.

## Caveats

- Docker containers remain UTC. Will add `TZ=Asia/Jakarta` via docker-compose in P1+.
- DeploymentGuide Step 12 still references `systemd-timesyncd` — doc sync flag added to StepPrompts.
- Persona OpsManual rituals reference WIB — now consistent with host timezone.

## Rollback

```bash
sudo cp /etc/chrony/chrony.conf.backup.p0-008-20260531 /etc/chrony/chrony.conf
sudo systemctl restart chrony
sudo systemctl unmask systemd-timesyncd
sudo timedatectl set-timezone Etc/UTC
sudo systemctl restart fail2ban crowdsec crowdsec-firewall-bouncer rsyslog
```
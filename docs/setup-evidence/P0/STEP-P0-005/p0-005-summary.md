# STEP-P0-005 Summary — fail2ban Configuration

Date: 2026-05-31
Implementer: Hephaestus / Guinevere workflow
Host: faiz-prod-01 / 100.94.104.22

## What Was Done

Configured fail2ban SSH brute-force protection on the shared VPS using a preserve-existing-jail approach. The host already had fail2ban installed and an Aizanta-specific `sshd` jail, so P0-005 did not reinstall, purge, or overwrite global fail2ban config. Instead, it added a late-loading Guinevere drop-in that:

- Keeps `backend = systemd`.
- Sets `maxretry = 3`, `findtime = 600`, `bantime = 86400` for `sshd`.
- Switches fail2ban action to UFW using `ufw[blocktype=deny]`.
- Whitelists loopback, VPS Tailscale IP, and operator Windows Tailscale IP.

## Runtime Files Changed

Created on VPS:

- `/etc/fail2ban/jail.d/zz-guinevere-p0-005.local`

Backup created on VPS:

- `/etc/fail2ban.backup.p0-005-20260531`

Read-only observed, not edited:

- `/etc/fail2ban/jail.d/aizanta-sshd.local`

## Local Evidence Files

Created under `docs/setup-evidence/P0/STEP-P0-005/`:

- `fail2ban-status.txt`
- `fail2ban-jail-config.txt`
- `fail2ban-whitelist-proof.txt`
- `fail2ban-test.log`
- `aizanta-post-check.md`
- `p0-005-summary.md`
- `verification.md`

## Key Validation

- `systemctl is-active fail2ban` returned `active`.
- `fail2ban-client status` showed one jail: `sshd`.
- `fail2ban-client status sshd` showed active `sshd` jail and current banned IP count.
- `fail2ban-client get sshd ignoreip` includes `127.0.0.0/8`, `::1`, `100.94.104.22`, `100.112.201.124`.
- `fail2ban-client get sshd actions` returned `ufw`.
- TEST-NET IP `198.51.100.99` ban created a UFW deny rule and unban removed it.
- SSH alias `guinevere-vps` still works.
- Aizanta containers and protected ports remained healthy and unchanged.

## Design Decisions

### Preserve existing fail2ban instead of fresh install

StepPrompts originally assumed fail2ban was not installed and suggested writing `/etc/fail2ban/jail.local`. Live discovery showed fail2ban was already installed/running and had Aizanta-specific configuration. A late-loading drop-in was safer than overwriting `jail.local` or purging fail2ban.

### Use specific Tailscale whitelist entries

The operator Tailscale IP `100.112.201.124` and VPS Tailscale IP `100.94.104.22` were whitelisted. The full Tailscale CGNAT range was intentionally not whitelisted.

### Restart after reload

`fail2ban-client reload` loaded the new ignore list and jail thresholds, but runtime action remained stale until service restart. The generated config already showed UFW action, and after guardrail checks a controlled `systemctl restart fail2ban` rehydrated runtime action correctly. Existing active bans were preserved.

## Caveats

- fail2ban was pre-existing, so P0-005 hardened and documented the existing service rather than installing it from scratch.
- Restart reset failure counters, but preserved the active ban list.
- Existing public hostile IP bans remain in UFW as intended.
- P0-006 CrowdSec will add another threat-detection layer; it must account for the fail2ban UFW action now active.

## Rollback Summary

Preferred rollback:

```bash
sudo cp -a /etc/fail2ban /etc/fail2ban.rollback-before-p0-005-revert.$(date +%Y%m%d%H%M%S)
sudo rm -f /etc/fail2ban/jail.d/zz-guinevere-p0-005.local
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd
ssh guinevere-vps "whoami && hostname"
```

Full restore option:

```bash
sudo rm -rf /etc/fail2ban
sudo cp -a /etc/fail2ban.backup.p0-005-20260531 /etc/fail2ban
sudo systemctl restart fail2ban
```

Do not purge fail2ban on this shared VPS unless explicitly approved and Aizanta impact has been reviewed.

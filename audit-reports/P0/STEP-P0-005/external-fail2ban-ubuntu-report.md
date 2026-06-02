# External Research: Fail2Ban on Ubuntu 24.04 — SSH Jail Best Practices

**Date**: 2026-05-31
**Context**: STEP-P0-005 — VPS provisioning, shared VPS with UFW active, SSH 22 + Tailscale UDP 41641 allowed. Samm/Tailscale must never be banned.
**Scope**: fail2ban installation, `jail.local` vs `jail.d/*.conf`, systemd backend, UFW banaction, sshd filter behavior, verification/rollback/idempotency, known pitfalls.

---

## 1. Package & Version Status (Ubuntu 24.04 Noble)

| Attribute | Value |
|---|---|
| Repo package | `fail2ban` (Ubuntu universe) |
| Initial ship version | `1.0.2-3` |
| Current fixed version | `1.0.2-3ubuntu0.1` (via noble-updates) |
| Upstream latest | `1.1.0` (supports Python 3.12 natively) |
| Python requirement | Python 3.12 (Ubuntu 24.04 default) |

### Critical Python 3.12 Bug (LP: #2055114)

The original `1.0.2-3` shipped in Ubuntu 24.04 fails to start on Python 3.12 because:
- `asynchat` / `asyncore` modules were **removed** in Python 3.12
- `distutils.version` was also removed

**Status**: Fixed in `1.0.2-3ubuntu0.1` (SRU to noble-updates). The fix:
- Vendors asyncore/asynchat compatibility modules
- Adds `python3-setuptools` to Depends (provides `distutils.version`)
- Later pivoted to use `python3-pyasyncore` instead of vendoring

**References**:
- [Launchpad Bug #2055114](https://bugs.launchpad.net/bugs/2055114)
- [Upstream commit 1024452 (bundles async compat)](https://github.com/fail2ban/fail2ban/commit/1024452fe1befeb5a0a014386a81ec183cd45bb5)
- [Upstream issue #3910 — `imp` module missing](https://github.com/fail2ban/fail2ban/issues/3910)

**Safe path**: Install via `apt` from noble-updates (gets 1.0.2-3ubuntu0.1+), no manual PPA needed.

---

## 2. Configuration File Hierarchy

```
/etc/fail2ban/
  ├── fail2ban.conf          # Main daemon config (never edit)
  ├── fail2ban.local          # Custom overrides for daemon config
  ├── jail.conf               # Default jail definitions (never edit)
  ├── jail.local              # Traditional override file
  ├── jail.d/
  │   ├── defaults-debian.conf  # UBUNTU SHIPS THIS — enables sshd, sets nftables
  │   └── sshd.conf            # Custom jail drop-in (recommended approach)
  ├── action.d/               # Ban action definitions (ufw.conf, nftables.conf...)
  ├── filter.d/               # Regex filter definitions (sshd.conf...)
  └── paths-debian.conf       # Distribution-specific log paths
```

### Loading Order (last wins)

```
jail.conf → jail.d/*.conf → jail.local → jail.d/*.local
```

- **`.conf` files**: shipped by package, overwritten on upgrade — NEVER EDIT
- **`.local` files**: your overrides, only need changed settings
- **`jail.d/` drop-ins**: preferred pattern — one file per jail, easier to maintain

**Official upstream guidance** ([Proper fail2ban configuration](https://github.com/fail2ban/fail2ban/wiki/Proper-fail2ban-configuration)):
> "You should avoid to change .conf files, created by fail2ban installation. Instead, you should create new files with a .local extension."

**Important**: Ubuntu 24.04 ships `/etc/fail2ban/jail.d/defaults-debian.conf` which:
1. Enables `[sshd]` jail by default
2. Sets `banaction = nftables`
3. Sets `backend = systemd`

Any custom defaults file must sort **alphabetically after** `defaults-debian.conf` to override it. Convention: `zz-defaults.conf`.

---

## 3. Systemd Journal Backend (Ubuntu 24.04 Default)

Ubuntu 24.04 uses systemd-journald as the canonical log source. The sshd jail's default backend is `systemd`.

**Key behavior**:
- `backend = systemd` reads from journal via `journalmatch`, NOT from log files
- `logpath` is **not used** with systemd backend (can cause confusion if both are set)
- The journalmatch for Ubuntu 24.04 sshd: `_SYSTEMD_UNIT=sshd.service + _COMM=sshd`

**Verification**:
```bash
# Check effective backend
sudo fail2ban-client get sshd backend

# Confirm journal match in status
sudo fail2ban-client status sshd
# Output shows: Journal matches: _SYSTEMD_UNIT=sshd.service + _COMM=sshd

# Check that failures actually exist in journal
journalctl -u sshd --since "1 hour ago" | grep "Failed password" | tail -5
```

**Pitfall**: If backend is `auto` and `/var/log/auth.log` doesn't exist or is stale, Fail2Ban reads NOTHING. Always verify with `fail2ban-client status sshd` that journal matches show up, not empty File list.

**Reference**:
- [Ubuntu manpage: jail.conf.5](https://manpages.ubuntu.com/manpages/noble/man5/jail.conf.5.html) — systemd backend docs
- [cr0x.net: Fail2ban isn't banning verification workflow](https://cr0x.net/en/ubuntu-fail2ban-not-banning-workflow/)

---

## 4. Service Naming: `ssh` vs `sshd`

Ubuntu uses **`sshd`** (not `ssh`).

| Aspect | Ubuntu | Debian |
|---|---|---|
| Package/service name | `sshd` (openssh-server) | `ssh` |
| Fail2Ban jail name | `[sshd]` | `[sshd]` (same filter) |
| systemd unit | `sshd.service` | `ssh.service` |
| Journal match | `_SYSTEMD_UNIT=sshd.service` | `_SYSTEMD_UNIT=ssh.service` |

On Ubuntu 24.04, `defaults-debian.conf` targets `sshd.service` — so no special handling needed. But if copying configs from Debian guides, double-check the unit name.

---

## 5. UFW Ban Action — Configuration

### Why UFW action
- The VPS already has UFW active with SSH 22 and Tailscale UDP 41641 allowed
- `banaction = ufw` adds UFW deny rules that integrate with the existing firewall
- Rules appear in `ufw status numbered` and persist across reboots

### How to Override the Default nftables Action

Since `defaults-debian.conf` sets `banaction = nftables`, create a file that sorts AFTER it:

**`/etc/fail2ban/jail.d/zz-defaults.conf`**:
```ini
[DEFAULT]
banaction = ufw
banaction_allports = ufw
backend = systemd
```

The `zz-` prefix ensures it sorts after `defaults-`.

### UFW Action Internals

From [upstream ufw.conf](https://github.com/fail2ban/fail2ban/blob/master/config/action.d/ufw.conf):

```bash
# What actionban does (simplified):
ufw prepend deny from <ip> to any comment "by Fail2Ban after <failures> attempts against <name>"

# What actionunban does:
ufw delete deny from <ip> to any
```

**Key parameters** (configurable per-jail):
- `blocktype`: `reject` (default) or `deny` — `deny` is silent drop, `reject` sends ICMP
- `destination`: `any` (default) — can scope to specific address
- `application`: optional UFW app profile
- `kill-mode`: `ss` or `conntrack` — immediately kills existing connections from banned IP

**Recommendation**: Use `blocktype = deny` for SSH jails (silent drop, attacker doesn't know port is filtered).

---

## 6. Recommended Configuration for This VPS

### 6.1 Install & Prerequisites

```bash
# Ensure universe repo is available
sudo add-apt-repository universe
sudo apt update

# Install fail2ban (gets fixed version from noble-updates)
sudo apt install -y fail2ban python3-setuptools

# Ensure UFW is active (already done per context)
sudo ufw status verbose
```

### 6.2 Global Defaults — `/etc/fail2ban/jail.d/zz-defaults.conf`

```ini
[DEFAULT]
# Never ban localhost, Tailscale subnet, or Samm's IP
ignoreip = 127.0.0.1/8 ::1 100.64.0.0/10 <SAMM_TAILSCALE_IP>

# Ban duration: 1 hour (3600 seconds)
bantime = 3600

# Finding window: 10 minutes
findtime = 600

# Max failures before ban: 3 for SSH, 5 default for others
maxretry = 5

# Use UFW as ban action (overrides nftables from defaults-debian.conf)
banaction = ufw
banaction_allports = ufw

# Read from systemd journal
backend = systemd

# Use deny (silent drop) instead of reject
action = %(action_)s[blocktype=deny]
```

### 6.3 SSH Jail — `/etc/fail2ban/jail.d/sshd.conf`

```ini
[sshd]
enabled  = true
port     = ssh
filter   = sshd
mode     = aggressive
backend  = systemd
maxretry = 3
findtime = 600
bantime  = 7200
banaction = ufw[blocktype=deny]
```

**Parameter rationale**:
| Parameter | Value | Reason |
|---|---|---|
| `mode = aggressive` | Matches more SSH failure patterns including key auth failures | Catches more attack types |
| `maxretry = 3` | 3 failures = ban. Legit users rarely fail 3x | Stops attackers fast |
| `findtime = 600` | 10-minute window | Balances false positives |
| `bantime = 7200` | 2-hour ban | Longer than default, not punitive |
| `backend = systemd` | Reads from journal | Matches Ubuntu 24.04 default |

### 6.4 Recidive Jail (Repeat Offenders) — `/etc/fail2ban/jail.d/recidive.conf`

```ini
[recidive]
enabled   = true
logpath   = /var/log/fail2ban.log
banaction = ufw[blocktype=deny]
bantime   = 1w
findtime  = 1d
maxretry  = 3
```

This watches Fail2Ban's own log and re-bans IPs that get banned 3+ times within 24h for a full week.

### 6.5 Incremental Bantime (Optional)

Add to `zz-defaults.conf`:
```ini
[DEFAULT]
bantime.increment = true
bantime.factor   = 2
bantime.maxtime  = 4w
```

First ban = base bantime, second = 2x, third = 4x... capped at 4 weeks.

---

## 7. Idempotency

| Operation | Idempotent? | Notes |
|---|---|---|
| `apt install fail2ban` | Yes | Package manager handles |
| Writing jail.d/*.conf | Yes | Can be overwritten/re-applied |
| `systemctl enable --now fail2ban` | Yes | Safe to re-run |
| `fail2ban-client reload` | Yes | Reloads config without dropping active bans |
| `fail2ban-client set sshd banip X` | No | Can't ban already-banned IP (harmless error) |
| `fail2ban-client set sshd unbanip X` | Yes | Unbans if banned, no-op if not |

---

## 8. Rollback Plan

```bash
# 1. Remove custom config files
sudo rm /etc/fail2ban/jail.d/zz-defaults.conf
sudo rm /etc/fail2ban/jail.d/sshd.conf
sudo rm /etc/fail2ban/jail.d/recidive.conf

# 2. Restart to reload original defaults
sudo systemctl restart fail2ban

# 3. If service was not installed:
sudo apt remove --purge fail2ban
sudo apt autoremove

# 4. Unban specific IP if accidentally banned
sudo fail2ban-client set sshd unbanip <IP>

# 5. Clean up UFW rules created by fail2ban (if any remain)
sudo ufw status numbered  # look for "by Fail2Ban" comments
sudo ufw delete <RULE_NUMBER>
```

---

## 9. Verification Commands

```bash
# Service health
sudo systemctl status fail2ban

# List active jails
sudo fail2ban-client status

# SSH jail status
sudo fail2ban-client status sshd
# Expected: "Journal matches: _SYSTEMD_UNIT=sshd.service + _COMM=sshd"

# Dump effective configuration (catch override mistakes)
sudo fail2ban-client -d | grep -E "(sshd|banaction|backend|ignoreip)"

# Check individual jail parameters
sudo fail2ban-client get sshd bantime
sudo fail2ban-client get sshd findtime
sudo fail2ban-client get sshd maxretry
sudo fail2ban-client get sshd ignoreip
sudo fail2ban-client get sshd actions

# Check UFW deny rules created by fail2ban
sudo ufw status numbered | grep -i "deny"

# Check fail2ban logs
sudo journalctl -u fail2ban --since "1 hour ago"
sudo tail -f /var/log/fail2ban.log

# Force ban a test IP (use a TEST IP, not real)
sudo fail2ban-client set sshd banip 198.51.100.1
# Verify: sudo ufw status numbered | grep 198.51.100.1
# Clean up: sudo fail2ban-client set sshd unbanip 198.51.100.1

# Test filter regex against existing log data
sudo fail2ban-regex systemd-journal /etc/fail2ban/filter.d/sshd.conf
```

---

## 10. Pitfalls Summary

| Pitfall | Description | Prevention |
|---|---|---|
| **Python 3.12 crash** | Stock 1.0.2-3 fails on Noble due to removed `asynchat`/`asyncore`/`distutils` | Ensure `1.0.2-3ubuntu0.1`+ from noble-updates, or `python3-setuptools` installed |
| **Wrong backend** | `backend = auto` may pick file-based but journal is the source | Explicitly set `backend = systemd` |
| **`logpath` with systemd** | Setting `logpath` on a systemd-backend jail is confusing and unnecessary | Omit `logpath` for jails using systemd backend |
| **`ssh` vs `sshd`** | Debian uses `ssh.service`, Ubuntu uses `sshd.service` | Use `[sshd]` jail on Ubuntu |
| **UFW not enabled** | UFW action requires `ufw enable` first | Verify `sudo ufw status` is active |
| **Self-ban** | Forgetting `ignoreip` can lock you out | Always add `127.0.0.1/8 ::1` + your IP + Tailscale `100.64.0.0/10` |
| **`defaults-debian.conf` override** | Ubuntu ships this with nftables; custom defaults must sort after | Use `zz-` prefix for override files |
| **Recidive infinite loop** | If fail2ban loglevel is DEBUG, recidive may loop | Keep loglevel at INFO or higher, increase `dbpurgeage` |

---

## 11. Official References

| Source | URL |
|---|---|
| Upstream repo | https://github.com/fail2ban/fail2ban |
| Proper config wiki | https://github.com/fail2ban/fail2ban/wiki/Proper-fail2ban-configuration |
| Ubuntu manpage jail.conf.5 | https://manpages.ubuntu.com/manpages/noble/man5/jail.conf.5.html |
| Official upstream jail.conf | https://raw.githubusercontent.com/fail2ban/fail2ban/master/config/jail.conf |
| UFW action definition | https://github.com/fail2ban/fail2ban/blob/master/config/action.d/ufw.conf |
| LP#2055114 (Python 3.12 fix) | https://bugs.launchpad.net/bugs/2055114 |
| Community Ubuntu guide | https://help.ubuntu.com/community/Fail2ban |
| Scaleway Ubuntu 24.04 guide | https://www.scaleway.com/en/docs/tutorials/protect-server-fail2ban/ |
| Fail2ban troubleshooting | https://cr0x.net/en/ubuntu-fail2ban-not-banning-workflow/ |
| Virtua.cloud f2b setup | https://www.virtua.cloud/learn/en/tutorials/fail2ban-setup-linux-vps |

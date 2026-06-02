# External Research Report: CrowdSec on Ubuntu 24.04 LTS

**Task**: STEP-P0-006 — CrowdSec installation & configuration readiness  
**Date**: 2026-05-31  
**Author**: Guinevere (Librarian)  
**Sources**: Official CrowdSec docs, GitHub issues, Discourse, packagecloud, community guides  

---

## Table of Contents

1. [Ubuntu 24.04 Repository & Package Status](#1-ubuntu-2404-repository--package-status)
2. [Installation Procedure](#2-installation-procedure)
3. [Service Names](#3-service-names)
4. [cscli Command Reference](#4-cscli-command-reference)
5. [Hub Operations (update/upgrade/install)](#5-hub-operations)
6. [SSHD Collection](#6-sshd-collection)
7. [Acquis Configuration (Log Sources)](#7-acquis-configuration)
8. [Allowlists (Whitelisting IPs)](#8-allowlists)
9. [Local Decisions & Alerts Verification](#9-local-decisions--alerts)
10. [Community Blocklists & Console Enrollment](#10-community-blocklists--console-enrollment)
11. [Non-Interactive Installation Caveats](#11-non-interactive-installation-caveats)
12. [Rollback / Uninstall](#12-rollback--uninstall)
13. [UFW & fail2ban Coexistence Notes](#13-ufw--fail2ban-coexistence-notes)
14. [Pitfalls & Recommended Command Sequence](#14-pitfalls--recommended-command-sequence)

---

## 1. Ubuntu 24.04 Repository & Package Status

### The `any/any` Packaging Model

As of early 2025, CrowdSec **no longer publishes per-distro apt repos** (e.g. `ubuntu/noble`). The old `ubuntu noble Release 404` error ([Discourse thread](https://discourse.crowdsec.net/t/ubuntu-24-0-4-unavailable/1976)) is resolved by the new **`any/any`** packaging scheme — a single static Golang binary distributed via packagecloud.

**Official install script** (recommended):
```bash
curl -s https://install.crowdsec.net | sudo sh
```
This creates `/etc/apt/sources.list.d/crowdsec_crowdsec.list` with:
```
deb [signed-by=/etc/apt/keyrings/crowdsec_crowdsec-archive-keyring.gpg] https://packagecloud.io/crowdsec/crowdsec/any/ any main
```

### Ubuntu-Provided Package (Outdated)

Ubuntu 24.04 ships `crowdsec` v1.4.6 in the `universe` repository:
- **noble (base)**: `1.4.6-6build1`
- **noble-updates/security**: `1.4.6-6ubuntu0.24.04.2`

This is **severely outdated** (current upstream is v1.7.8). On ESM/Pro Ubuntu, APT may prefer this version unless package pinning is applied.

### Package Pinning (Required for ESM/Pro Ubuntu)

Create `/etc/apt/preferences.d/crowdsec`:
```
Package: *
Pin: release o=packagecloud.io/crowdsec/crowdsec,a=any,n=any,c=main
Pin-Priority: 1001
```
Then:
```bash
sudo apt update
apt-cache policy crowdsec  # Confirm candidate is >= 1.6.x
```

### Current Package Versions on packagecloud

As of May 2026, the CrowdSec repo hosts up to **v1.7.8**:
- [crowdsec_1.7.8_amd64.deb](https://packagecloud.io/crowdsec/crowdsec/packages/ubuntu/noble/crowdsec_1.7.8_amd64.deb)
- [crowdsec_1.7.7_amd64.deb](https://packagecloud.io/crowdsec/crowdsec/packages/ubuntu/noble/crowdsec_1.7.7_amd64.deb)

---

## 2. Installation Procedure

### Step 1: Add Repository

```bash
curl -s https://install.crowdsec.net | sudo sh
sudo apt update
```

### Step 2: Install Security Engine

```bash
sudo apt install crowdsec -y
```

**Post-install effects**:
- Creates `crowdsec` system user
- Creates `/etc/crowdsec/` config tree
- Generates LAPI credentials at `/etc/crowdsec/local_api_credentials.yaml`
- Creates SQLite decisions DB at `/var/lib/crowdsec/data/`
- Writes default `acquis.yaml` (auto-detects services)
- Installs and starts `crowdsec.service`
- Runs `cscli setup unattended` internally — detects running services, installs matching collections (typically `crowdsecurity/linux` which includes `crowdsecurity/sshd`)

### Step 3: Install Firewall Bouncer (nftables)

Ubuntu 24.04 uses **nftables** by default:
```bash
sudo apt install crowdsec-firewall-bouncer-nftables -y
```

For legacy iptables setups:
```bash
sudo apt install crowdsec-firewall-bouncer-iptables -y
```

**Post-install effects**:
- Auto-registers with LAPI (generates API key)
- Creates nftables sets: `crowdsec-blacklists`, `crowdsec6-blacklists`
- Installs `crowdsec-firewall-bouncer.service`
- Config at `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml`

### Verify Installation

```bash
sudo systemctl status crowdsec
sudo systemctl status crowdsec-firewall-bouncer
cscli version
```

---

## 3. Service Names

| Service | Purpose | Default Status |
|---|---|---|
| `crowdsec.service` | Security Engine (log processor + LAPI) | enabled, running |
| `crowdsec-firewall-bouncer.service` | Firewall remediation (nftables/iptables) | enabled, running |
| `crowdsec-nginx-bouncer.service` | Nginx bouncer (if installed) | enabled, running |

**Reload vs Restart**:
- `sudo systemctl reload crowdsec` — apply hub config changes (collections, parsers, scenarios)
- `sudo systemctl restart crowdsec` — full restart (for acquis changes, config.yaml changes)

---

## 4. cscli Command Reference

### General

| Command | Description |
|---|---|
| `cscli version` | Show version |
| `cscli hub list` | List installed hub items (parsers, scenarios, collections) |
| `cscli hub list -a` | List ALL available hub items |
| `cscli config show` | Show current config (yaml) |
| `cscli metrics` | Show Prometheus metrics (buckets, acquisition, parsers, API) |
| `cscli explain -f /var/log/auth.log --type syslog` | Explain what would happen with a log line |

### Hub Management

| Command | Description |
|---|---|
| `cscli hub update` | Refresh local hub index from upstream |
| `cscli hub upgrade` | Upgrade ALL installed hub items to latest |
| `cscli collections install <name>` | Install a collection |
| `cscli collections list` | List installed collections |
| `cscli collections upgrade <name>` | Upgrade a specific collection |
| `cscli collections inspect <name>` | Show collection details + metrics |
| `cscli parsers install <name>` | Install a parser |
| `cscli parsers list` | List installed parsers |
| `cscli parsers upgrade <name>` | Upgrade a specific parser |
| `cscli scenarios install <name>` | Install a scenario |
| `cscli scenarios list` | List installed scenarios |
| `cscli scenarios upgrade <name>` | Upgrade a specific scenario |

### Decisions

| Command | Description |
|---|---|
| `cscli decisions list` | List active decisions (local only) |
| `cscli decisions list -a` | List all decisions (including CAPI blocklists) |
| `cscli decisions list --origin lists` | List blocklist-sourced decisions |
| `cscli decisions add --ip 1.2.3.4 --duration 24h --type ban` | Manually ban an IP |
| `cscli decisions add --ip 1.2.3.4 --duration 4h --type captcha` | Add captcha decision |
| `cscli decisions add --range 1.2.3.0/24 --duration 1h` | Ban a CIDR range |
| `cscli decisions delete --ip 1.2.3.4` | Remove active decisions for IP |
| `cscli decisions delete --reason crowdsecurity/ssh-bf` | Remove decisions by reason |

### Alerts

| Command | Description |
|---|---|
| `cscli alerts list` | List all alerts (historical) |
| `cscli alerts list --since 24h` | List alerts from last 24 hours |
| `cscli alerts inspect <id>` | Show alert details |

### Allowlists (v1.6.8+)

| Command | Description |
|---|---|
| `cscli allowlists create <name> -d "<desc>"` | Create an allowlist |
| `cscli allowlists add <name> <ip/cidr> [-e 7d] [-d "comment"]` | Add entry to allowlist |
| `cscli allowlists inspect <name>` | View allowlist contents |
| `cscli allowlists list` | List all allowlists |
| `cscli allowlists check <name> <ip>` | Check if IP is in allowlist |
| `cscli allowlists remove <name> <ip>` | Remove entry from allowlist |

### Console

| Command | Description |
|---|---|
| `cscli console enroll <KEY>` | Enroll in CrowdSec Console |
| `cscli console enroll --name <hostname> --tags <tag> <KEY>` | Enroll with metadata |
| `cscli console status` | View console connection status |

### Setup

| Command | Description |
|---|---|
| `cscli setup interactive` | Interactive service detection & config |
| `cscli setup unattended` | Automatic detection & config (no prompts) |
| `cscli setup unattended --dry-run` | Preview what unattended would do |

---

## 5. Hub Operations

### Update Hub Index

Always the first step before installing or upgrading:
```bash
sudo cscli hub update
```

### Upgrade All Hub Items

```bash
sudo cscli hub upgrade
sudo systemctl reload crowdsec
```

### Install a Collection

```bash
sudo cscli collections install crowdsecurity/sshd
sudo systemctl reload crowdsec
```

### Upgrade a Specific Collection

```bash
sudo cscli hub update
sudo cscli collections upgrade crowdsecurity/sshd
sudo systemctl reload crowdsec
```

### Important Flags for `cscli collections install`

```
--dry-run         Show execution plan, don't change anything
--force           Force install (overwrite tainted/outdated files)
--download-only   Download only, don't enable
--ignore          Ignore errors when installing multiple collections
```

### Parsers & Scenarios (granular control)

```bash
sudo cscli parsers install crowdsecurity/geoip-enrich
sudo cscli parsers upgrade crowdsecurity/sshd-logs
sudo cscli scenarios upgrade crowdsecurity/ssh-bf
sudo systemctl reload crowdsec
```

---

## 6. SSHD Collection

The `crowdsecurity/sshd` collection contains:
- **Parser**: `crowdsecurity/sshd-logs` (stage s01-parse)
- **Scenario**: `crowdsecurity/ssh-bf` (SSH brute-force detection)

It is bundled within `crowdsecurity/linux` — the default collection installed during setup. On Ubuntu 24.04, it is typically installed automatically.

### Manual Installation

```bash
sudo cscli collections install crowdsecurity/sshd
sudo systemctl reload crowdsec
```

### Verify SSHD Collection

```bash
sudo cscli collections inspect crowdsecurity/sshd
```

Expected output includes:
```text
parsers:
- crowdsecurity/sshd-logs
scenarios:
- crowdsecurity/ssh-bf
```

### SSHD Acquisition (Journald — Ubuntu 24.04 default)

Ubuntu 24.04 uses systemd-journald for SSH logging. The default acquisition is:
```yaml
# /etc/crowdsec/acquis.yaml or /etc/crowdsec/acquis.d/sshd.yaml
journalctl_filter:
  - _SYSTEMD_UNIT=sshd.service
labels:
  type: syslog
```

**⚠️ Important**: On Ubuntu, the systemd unit is `ssh.service`, NOT `sshd.service`. Some older versions of the CrowdSec wizard create `sshd.service` which will match nothing. If metrics show zero lines parsed for SSH, check this:
```bash
sudo sed -i 's/sshd.service/ssh.service/' /etc/crowdsec/acquis.yaml
sudo systemctl restart crowdsec
```

Reference: [GitHub issue #2175](https://github.com/crowdsecurity/crowdsec/issues/2175)

### SSHD Acquisition (File-based fallback)

If rsyslog is installed and `/var/log/auth.log` exists:
```yaml
filenames:
  - /var/log/auth.log
labels:
  type: syslog
```

---

## 7. Acquis Configuration

### Location

- **Legacy single file**: `/etc/crowdsec/acquis.yaml`
- **Preferred per-source dir**: `/etc/crowdsec/acquis.d/*.yaml`

Both paths are merged if present. The `acquis_dir` config points to `/etc/crowdsec/acquis.d` by default (since CrowdSec 1.5.0).

### Common Acquisition Examples

**SSH (journald)**:
```yaml
# /etc/crowdsec/acquis.d/sshd.yaml
journalctl_filter:
  - _SYSTEMD_UNIT=ssh.service
labels:
  type: syslog
```

**SSH (file-based)**:
```yaml
# /etc/crowdsec/acquis.d/sshd.yaml
source: file
filenames:
  - /var/log/auth.log
labels:
  type: syslog
```

**Nginx**:
```yaml
# /etc/crowdsec/acquis.d/nginx.yaml
source: file
filenames:
  - /var/log/nginx/access.log
  - /var/log/nginx/error.log
labels:
  type: nginx
```

**Syslog (generic)**:
```yaml
filenames:
  - /var/log/syslog
labels:
  type: syslog
```

### Test Configuration

After adding/editing acquis files:
```bash
sudo crowdsec -t           # Test config syntax
sudo systemctl restart crowdsec
```

### Verify Logs Are Being Read

```bash
sudo cscli metrics
```

Look for the `Acquisition Metrics` section — if lines are parsed and poured to buckets, acquisition is working.

### Force Inotify Mode

For NFS or virtual filesystems where inotify doesn't work:
```yaml
source: file
filenames:
  - /var/log/some/*.log
force_inotify: true
poll_without_inotify: true
labels:
  type: syslog
```

---

## 8. Allowlists

### Overview

AllowLists (v1.6.8+) are the **preferred** method to whitelist IPs/CIDRs. They are:
- Centrally managed via `cscli`
- Take effect **immediately** (no restart needed)
- Apply across all components: AppSec, cscli, scenario overflows, console blocklists

### Creating an Allowlist

```bash
sudo cscli allowlists create vps-whitelist -d "Samm VPS and Tailscale IPs"
```

### Adding Entries

```bash
# Single IP
sudo cscli allowlists add vps-whitelist <SAMM_VPS_IP>

# CIDR range (Tailscale)
sudo cscli allowlists add vps-whitelist <TAILSCALE_CIDR>

# With expiration and comment
sudo cscli allowlists add vps-whitelist 1.2.3.4 -e 7d -d "temporary access"
```

### Verifying

```bash
sudo cscli allowlists inspect vps-whitelist
sudo cscli allowlists check vps-whitelist <IP_TO_CHECK>
```

### Important: Existing Decisions Are Not Auto-Cleared

If an IP was already banned before being added to an allowlist, the existing decision remains. Remove it manually:
```bash
sudo cscli decisions delete --ip <BANNED_IP>
```

### Alternative: Parser Whitelist (for event patterns)

For whitelisting based on log content (e.g. a healthcheck endpoint), use parser whitelist files:
```yaml
# /etc/crowdsec/parsers/s02-enrich/01-my-whitelist.yaml
name: my/whitelist
description: "Whitelist healthcheck"
filter: "evt.Meta.service == 'http'"
whitelist:
  reason: "Healthcheck"
  expression:
    - "evt.Meta.http_verb == 'GET' && evt.Meta.http_path == '/health'"
```

Then restart:
```bash
sudo systemctl restart crowdsec
```

---

## 9. Local Decisions & Alerts

### View Active Decisions

```bash
sudo cscli decisions list
```

Output columns: `ID`, `SOURCE`, `SCOPE:VALUE`, `REASON`, `ACTION`, `COUNTRY`, `AS`, `EVENTS`, `EXPIRATION`, `ALERT ID`

Sources:
- `crowdsec` — locally triggered by scenarios
- `CAPI` — fetched from CrowdSec Central API (community blocklist)
- `cscli` — manually added via `cscli decisions add`
- `lists` — from subscribed blocklists

### View All Decisions (Including Blocklists)

```bash
sudo cscli decisions list -a
sudo cscli decisions list --origin lists  # Blocklist-sourced only
```

### View Historical Alerts

```bash
sudo cscli alerts list
sudo cscli alerts list --since 24h
sudo cscli alerts inspect <ID>
```

### Manually Add a Decision

```bash
sudo cscli decisions add --ip 1.2.3.4 --duration 24h --type ban --reason "test"
```

### Remove a Decision

```bash
sudo cscli decisions delete --ip 1.2.3.4
sudo cscli decisions delete --id 42
```

### Metrics Dashboard

```bash
sudo cscli metrics
```

Check:
- **Acquisition Metrics**: Lines parsed vs unparsed per source
- **Parser Metrics**: Success/failure rates per parser
- **Buckets Metrics**: Scenario overflow counts
- **Local API Metrics**: API endpoint hit counts

---

## 10. Community Blocklists & Console Enrollment

### Console Enrollment

1. Sign up at [https://app.crowdsec.net](https://app.crowdsec.net)
2. Generate enrollment key from the Engines page
3. On the VPS:
   ```bash
   sudo cscli console enroll YOUR_ENROLL_KEY
   ```
4. Accept the enrollment in the Console UI
5. Restart CrowdSec:
   ```bash
   sudo systemctl restart crowdsec
   ```

### Optional flags

```bash
sudo cscli console enroll --name my-vps --tags ssh --tags ubuntu YOUR_ENROLL_KEY
```

### Community Blocklist Tiers

| Tier | Requirement | Max IPs |
|---|---|---|
| **Community Blocklist (Premium)** | Paid subscription | Unlimited |
| **Community Blocklist** | Active signals contribution | Unlimited |
| **Community Blocklist (Lite)** | Non-contributing free users | ~3,000 IPs |

### Subscribing to Blocklists

After enrollment, via the Console web UI:
1. Navigate to **Blocklists** tab
2. Click **Subscribe** on a blocklist
3. Select the enrolled engine
4. Choose remediation action (ban)
5. Sync occurs every **2 hours**

### Verify Blocklist Decisions

```bash
sudo cscli decisions list --origin lists | head -20
sudo cscli metrics show decisions
```

### Blocklist Limits (Free Tier)

Free users can subscribe to **up to 3 blocklists**.

---

## 11. Non-Interactive Installation Caveats

### DEBIAN_FRONTEND Method

For fully automated/scripted installs:
```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y crowdsec
```

### Dpkg Options for Config Conflicts

To avoid prompts on config file conflicts:
```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install -y crowdsec
```

### Post-Install Unattended Setup

The CrowdSec package debconf triggers `cscli setup unattended` automatically. To **skip** this (e.g. for Ansible with custom config):
```bash
export CROWDSEC_SETUP_UNATTENDED_DISABLE=1
sudo apt install crowdsec -y
```

Then configure manually:
```bash
sudo cscli setup unattended --dry-run  # Preview what would be installed
sudo cscli setup unattended             # Run with defaults
```

Or with specific options:
```bash
sudo cscli setup unattended --ignore nginx --ignore apache
```

### Potential Issues with Unattended Setup

1. **Missing `/var/log/auth.log`** on Ubuntu minimal (no rsyslog) — acquisition will be journald-based
2. **Wrong systemd unit name** (`sshd.service` vs `ssh.service`) — verify and fix post-install
3. **Collections may install** based on detected services — review after install with `cscli hub list`

---

## 12. Rollback / Uninstall

### Clean Uninstall

```bash
# 1. Remove bouncers first (important!)
sudo apt remove crowdsec-firewall-bouncer-nftables -y

# 2. Purge CrowdSec engine (removes config, databases, etc.)
sudo apt purge crowdsec -y

# 3. Remove residual data
sudo rm -rf /etc/crowdsec
sudo rm -rf /var/lib/crowdsec
sudo rm -rf /var/log/crowdsec*
```

### Fix a Broken Reinstall

If `/etc/crowdsec` was manually deleted before `apt purge`, `dpkg` state can become inconsistent:
```bash
sudo rm /var/lib/dpkg/info/crowdsec*
sudo apt purge crowdsec -y
sudo apt install crowdsec -y
```

### Using wizard.sh

```bash
sudo ./wizard.sh --uninstall
```

**⚠️ Warning**: `wizard.sh --uninstall` checks for registered bouncers and warns. If bouncers exist, they must be removed first or use `--force`.

### Note on iptables/nftables Cleanup

Uninstalling the bouncer package **does** clean up firewall rules. However `wizard.sh --uninstall` alone may leave firewall chains. Always uninstall the bouncer package first.

---

## 13. UFW & fail2ban Coexistence Notes

### UFW + CrowdSec

- UFW is a frontend for iptables/nftables
- The CrowdSec firewall bouncer (nftables mode) inserts rules in the `input` hook via its own table (`crowdsec`), not in UFW chains
- **No direct conflict** — both can operate simultaneously
- However, both UFW and the CrowdSec firewall bouncer can block the same traffic at the kernel level — this is redundant but harmless
- If using UFW strict rules AND CrowdSec bouncer, consider:
  - Keep UFW for base firewall policy (allow/deny ports)
  - Let CrowdSec handle dynamic IP blocking

### fail2ban + CrowdSec

- **Both process the same logs** (`/var/log/auth.log` or journald) for SSH brute-force
- This creates **redundant processing** — duplicate work and potential double-banning
- For P0-006, the recommendation is:
  - **Disable fail2ban** for services CrowdSec handles (SSH)
  - Or at minimum, configure different jail actions so they don't step on each other
  - fail2ban can remain for services CrowdSec does NOT cover (if any)

### Detecting Current State

```bash
sudo ufw status verbose
sudo fail2ban-client status
sudo fail2ban-client status sshd  # if sshd jail exists
```

---

## 14. Pitfalls & Recommended Command Sequence

### Pitfall Checklist

| # | Pitfall | Resolution |
|---|---|---|
| 1 | Ubuntu's own crowdsec package (1.4.6) preferred over upstream | Add package pinning (`Pin-Priority: 1001`) |
| 2 | Old `ubuntu/noble` repo returns 404 | Use `any/any` via `install.crowdsec.net` script |
| 3 | `sshd.service` vs `ssh.service` in journald filter | `sed -i 's/sshd.service/ssh.service/' /etc/crowdsec/acquis.yaml` |
| 4 | Minimal Ubuntu missing `/var/log/auth.log` | Use journald acquisition or install rsyslog |
| 5 | Allowlist created AFTER IP already banned | Existing decision persists — delete it manually |
| 6 | Bouncer not starting after install | Register manually: `sudo cscli bouncers add <name>` |
| 7 | `wizard.sh --uninstall` without removing bouncers | Uninstall bouncer package first |
| 8 | CrowdSec not reading logs (0 lines parsed) | Check `cscli metrics`, verify acquis path/systemd unit |

### Recommended Step-by-Step for P0-006

```bash
# === 1. Add repository ===
curl -s https://install.crowdsec.net | sudo sh
sudo apt update

# === 2. Verify candidate version ===
apt-cache policy crowdsec

# (If needed on ESM/Pro: add pinning)

# === 3. Install engine ===
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y crowdsec

# === 4. Fix SSH unit name for Ubuntu ===
sudo sed -i 's/sshd.service/ssh.service/' /etc/crowdsec/acquis.yaml

# === 5. Install nftables bouncer ===
sudo apt install -y crowdsec-firewall-bouncer-nftables

# === 6. Verify services ===
sudo systemctl status crowdsec --no-pager
sudo systemctl status crowdsec-firewall-bouncer --no-pager

# === 7. Update hub and install/verify collections ===
sudo cscli hub update
sudo cscli collections install crowdsecurity/sshd
sudo cscli hub upgrade
sudo systemctl reload crowdsec

# === 8. Verify SSHD collection active ===
sudo cscli collections inspect crowdsecurity/sshd

# === 9. Create allowlists for whitelisting ===
sudo cscli allowlists create vps-whitelist -d "Samm VPS and Tailscale"
sudo cscli allowlists add vps-whitelist <SAMM_VPS_IP>
sudo cscli allowlists add vps-whitelist <TAILSCALE_CIDR>

# === 10. Verify no existing decisions blocking whitelisted IPs ===
sudo cscli decisions list
# If any exist: sudo cscli decisions delete --ip <IP>

# === 11. Enroll in Console (for community blocklists) ===
sudo cscli console enroll YOUR_ENROLL_KEY
# Then accept in web UI and restart:
sudo systemctl restart crowdsec

# === 12. Verify blocklist decisions arriving ===
sudo cscli decisions list --origin lists

# === 13. Verify metrics ===
sudo cscli metrics

# === 14. Test config ===
sudo crowdsec -t
```

### Key Verification Points Before Marking Complete

1. **`sudo cscli metrics`** — Acquisition shows lines parsed, not zero
2. **`sudo cscli decisions list -a`** — Shows decisions from both local scenarios and CAPI/lists
3. **`sudo cscli collections inspect crowdsecurity/sshd`** — Shows overflow counts for `crowdsecurity/ssh-bf`
4. **`sudo cscli allowlists inspect vps-whitelist`** — Shows whitelisted IPs/CIDRs
5. **`sudo systemctl status crowdsec-firewall-bouncer`** — Bouncer actively streaming decisions
6. **`sudo nft list set ip crowdsec crowdsec-blacklists | head -5`** — nftables set populated

---

## References

| Source | URL |
|---|---|
| Official Install Guide | https://docs.crowdsec.net/u/getting_started/installation/linux/ |
| Hub Management | https://docs.crowdsec.net/u/user_guides/hub_mgmt/ |
| CrowdSec Tour (cscli commands) | https://docs.crowdsec.net/docs/getting_started/crowdsec_tour |
| Firewall Bouncer | https://docs.crowdsec.net/u/bouncers/firewall/ |
| Allowlists / Whitelists | https://docs.crowdsec.net/u/getting_started/post_installation/whitelists/ |
| Acquiring New Log Sources | https://docs.crowdsec.net/u/getting_started/post_installation/acquisition_new/ |
| Console Enrollment | https://docs.crowdsec.net/u/getting_started/post_installation/console/ |
| Community Blocklist | https://docs.crowdsec.net/docs/central_api/community_blocklist |
| cscli Decisions | https://docs.crowdsec.net/docs/cscli/cscli_decisions_add/ |
| cscli Allowlists | https://docs.crowdsec.net/docs/cscli/cscli_allowlists/ |
| cscli Setup Unattended | https://docs.crowdsec.net/docs/cscli/cscli_setup_unattended |
| GitHub: Ubuntu 24.04 noble support | https://github.com/crowdsecurity/crowdsec/issues/3030 |
| Discourse: Ubuntu 24.04 unavailable | https://discourse.crowdsec.net/t/ubuntu-24-0-4-unavailable/1976 |
| Discourse: No firewall-bouncer in repo | https://discourse.crowdsec.net/t/no-firewall-bouncer-in-repo-for-ubuntu-24-04/2478 |
| GitHub: SSHD vs SSH unit name | https://github.com/crowdsecurity/crowdsec/issues/2175 |
| Ubuntu Package: crowdsec | https://packages.ubuntu.com/noble/crowdsec |

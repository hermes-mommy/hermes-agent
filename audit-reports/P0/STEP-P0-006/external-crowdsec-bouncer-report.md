# CrowdSec Firewall Bouncer — Safety Research Report

**Step**: STEP-P0-006  
**Scope**: External research — `crowdsec-firewall-bouncer` on shared VPS (Ubuntu/Debian)  
**Date**: 2026-05-31  
**Researcher**: Guinevere (THE LIBRARIAN)  
**Status**: Complete (read-only research)

---

## Table of Contents

1. [Package Naming & Current Versions](#1-package-naming--current-versions)
2. [Architecture Overview](#2-architecture-overview)
3. [UFW / nftables / iptables Interactions](#3-ufw--nftables--iptables-interactions)
4. [fail2ban Coexistence](#4-fail2ban-coexistence)
5. [IP Whitelist / AllowList (Critical Pre-Step)](#5-ip-whitelist--allowlist-critical-pre-step)
6. [Testing with TEST-NET IPs & Safe Simulation](#6-testing-with-test-net-ips--safe-simulation)
7. [Community Blocklists & Subscriptions](#7-community-blocklists--subscriptions)
8. [Checking Decisions](#8-checking-decisions)
9. [Rollback / Uninstall](#9-rollback--uninstall)
10. [Docker / Shared VPS Caveats](#10-docker--shared-vps-caveats)
11. [Ensuring Aizanta Traffic Is Not Blocked](#11-ensuring-aizanta-traffic-is-not-blocked)
12. [Safe Enablement Sequence (Recommended)](#12-safe-enablement-sequence-recommended)
13. [References](#13-references)

---

## 1. Package Naming & Current Versions

The firewall bouncer is distributed as two separate packages depending on the firewall backend:

| Firewall Backend | Package Name | Install Command |
|---|---|---|
| **iptables** (legacy or iptables-nft) | `crowdsec-firewall-bouncer-iptables` | `sudo apt install crowdsec-firewall-bouncer-iptables` |
| **nftables** (native) | `crowdsec-firewall-bouncer-nftables` | `sudo apt install crowdsec-firewall-bouncer-nftables` |

**Source repo**: `crowdsecurity/cs-firewall-bouncer` — MIT License, Go  
**Latest release**: `v0.0.35-rc2` (2026-02-25, prerelease) — stable release `v0.0.34`  
**Package maintainer**: CrowdSec team via official apt repo

> **Detection**: Run `iptables -V`. If output contains `nf_tables`, the system uses **nftables** as the backend. Ubuntu 22.04+ defaults to nftables.

**Official documentation**: https://docs.crowdsec.net/u/bouncers/firewall/  
**GitHub repo**: https://github.com/crowdsecurity/cs-firewall-bouncer

---

## 2. Architecture Overview

CrowdSec has a **detect/enforce separation**:

- **CrowdSec agent** (service: `crowdsec`) — reads logs, runs parsers/scenarios, produces "decisions" (IP to block).
- **Local API (LAPI)** — stores decisions, serves them to bouncers.
- **Firewall bouncer** (service: `crowdsec-firewall-bouncer`) — polls LAPI, inserts IPs into firewall block sets.

### Two operating modes

| Mode | Description | Risk Level |
|---|---|---|
| **Managed** (default) | Bouncer creates iptables/nftables sets + chains + rules automatically. Full auto-pilot. | **Medium** — convenient but less control |
| **Set-only** | Bouncer only populates existing sets. User creates the firewall rules manually. | **Low** — full control, recommended for shared VPS |

> **Recommendation for shared VPS**: Consider `set-only` mode or carefully restrict `iptables_chains` / `nftables_hooks` to avoid interfering with other tenants' rules.

### Configuration file location

```
/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
```

### Key configuration parameters

| Parameter | Values | Notes |
|---|---|---|
| `mode` | `iptables`, `nftables`, `ipset`, `pf` | Must match your backend |
| `update_frequency` | e.g. `10s` | How often to poll LAPI |
| `deny_action` | `DROP` (default) or `REJECT` | `DROP` is stealthier |
| `deny_log` | `true` / `false` | Enable to log blocked packets |
| `disable_ipv6` | `true` / `false` | Set `true` if no IPv6 |
| `iptables_chains` | `[INPUT, FORWARD, DOCKER-USER]` | **Critical**: restrict chains here |
| `nftables_hooks` | `[input, forward]` | Equivalent for nftables mode |

---

## 3. UFW / nftables / iptables Interactions

### UFW + CrowdSec bouncer

**UFW is a frontend to nftables (Ubuntu 22.04+) or iptables (older).** The CrowdSec firewall bouncer operates at the **same layer** as UFW — both manipulate nftables/iptables rules.

Key findings:

- **UFW and CrowdSec bouncer coexist without explicit conflict** because both target nftables at different priorities ([source](https://computingforgeeks.com/install-crowdsec-ubuntu-2604/)).
- The bouncer creates its **own nftables table** (named `crowdsec` by default) with its own chain. It does not touch UFW-managed chains.
- **UFW rules and CrowdSec rules are independent sets**. UFW manages its own chains (`ufw-user-input`, etc.), and the bouncer manages `crowdsec-chain`.
- **However**: in `ipset` only mode, the official docs warn: *"managed firewalls such as UFW might confuse the parser and lead to inconsistent metrics"* ([docs.crowdsec.net](https://docs.crowdsec.net/u/bouncers/firewall/)).

#### Verification commands

```bash
# Check which nftables tables exist
sudo nft list tables
# Expected: you'll see both "ufw" tables and "crowdsec" table

# Check crowdsec-specific rules
sudo nft list table inet crowdsec

# Check iptables rules (if using iptables mode)
sudo iptables -L INPUT -n | grep -i crowdsec

# List ipsets
sudo ipset list crowdsec-blacklists
```

> **Conclusion**: UFW and CrowdSec firewall bouncer can run together safely. CrowdSec does NOT modify UFW rules; it creates separate chains. No action needed on UFW config.

### iptables vs nftables backend

| Aspect | iptables mode | nftables mode |
|---|---|---|
| Dependency | Relies on `iptables` + `ipset` commands | Uses Go nftables library directly |
| Docker compatibility | Native `DOCKER-USER` chain support | Requires `nftables_hooks: [forward]` |
| Performance | Good | Excellent (native) |
| Reboot persistence | May need `netfilter-persistent` | Rules recreated on service start |

> **If using Docker on the same host**: you need to add `DOCKER-USER` chain (iptables mode) or `nftables_hooks: [forward]` (nftables mode) to block traffic to Docker containers.

---

## 4. fail2ban Coexistence

**Conclusion: They can run together safely with zero conflicts** — provided they don't fight over the same firewall chains.

### How they coexist

- **fail2ban** reads logs and inserts its own iptables/nftables rules.
- **CrowdSec** reads the same logs (no contention — reading is fine) and manages **separate** chains/sets via its bouncer.
- Both operate **independently** and produce duplicate bans (harmless but clutters logs).

### Recommended split

| Service | Handled by | Rationale |
|---|---|---|
| SSH brute-force | CrowdSec (or fail2ban) | Pick one to avoid duplicate parsing |
| HTTP-level attacks | CrowdSec | Better detection, community intel |
| Custom internal services | fail2ban | If CrowdSec has no parser |

### Migration approach

1. **Phase 1 (1–2 weeks)**: Run both in parallel. Monitor CrowdSec with `cscli decisions list` and `cscli metrics`.
2. **Phase 2**: Disable fail2ban SSH jail (`action = %(action_)s` for log-only mode) or disable fail2ban entirely once CrowdSec is stable.

> **Warning from community**: *"The biggest operational mistake is not choosing the 'wrong' tool. It is choosing two tools and letting both of them scribble over the same firewall layout."* ([RouteHarden](https://routeharden.com/blog/fail2ban-crowdsec-vpn-servers))

---

## 5. IP Whitelist / AllowList (Critical Pre-Step)

**This must be done BEFORE enabling the bouncer** to prevent locking out the operator and Aizanta nodes.

### Method 1: CrowdSec AllowLists (cscli — preferred)

Available in CrowdSec v1.6.8+. Affects all components (LAPI decisions, blocklist pulls, AppSec).

```bash
# Step 1: Create an allowlist
sudo cscli allowlists create aizanta-whitelist -d "Aizanta internal IPs and Tailscale"

# Step 2: Add Samm's Tailscale IP
sudo cscli allowlists add aizanta-whitelist 100.112.201.124 -d "Samm Tailscale"

# Step 3: Add VPS Tailscale IP
sudo cscli allowlists add aizanta-whitelist 100.94.104.22 -d "VPS Tailscale"

# Step 4: Optionally add Tailscale CGNAT range (if other Tailscale peers need access)
sudo cscli allowlists add aizanta-whitelist 100.64.0.0/10 -d "Tailscale CGNAT range"

# Step 5: Add local/lan ranges if needed
sudo cscli allowlists add aizanta-whitelist 127.0.0.1/8 -d "localhost"
```

**Verification**:

```bash
sudo cscli allowlists inspect aizanta-whitelist
```

**Important**: AllowLists prevent **new** decisions but do **NOT** remove existing ones. After whitelisting, purge any stale decisions:

```bash
sudo cscli decisions delete --ip 100.112.201.124
sudo cscli decisions delete --ip 100.94.104.22
```

### Method 2: Parser Whitelist (legacy filesystem approach)

Create `/etc/crowdsec/parsers/s02-enrich/whitelist-aizanta.yaml`:

```yaml
name: whitelist-aizanta
description: "Whitelist Aizanta internal IPs"
whitelist:
  reason: "Aizanta trusted traffic"
  ip:
    - "100.112.201.124"
    - "100.94.104.22"
    - "100.64.0.0/10"
```

Then reload:

```bash
sudo systemctl reload crowdsec
```

### Method 3: Firewall-level whitelist (belt-and-suspenders)

Add explicit UFW allow rules for the Tailscale IPs **before** enabling the bouncer:

```bash
sudo ufw allow from 100.112.201.124 to any port 22 proto tcp comment 'Samm-Tailscale-SSH'
sudo ufw allow from 100.94.104.22 to any port 22 proto tcp comment 'VPS-Tailscale-SSH'
# Add Aizanta-specific ports (application ports)
sudo ufw allow from 100.112.201.124 to any port <AIZANTA_PORT> proto tcp
sudo ufw allow from 100.94.104.22 to any port <AIZANTA_PORT> proto tcp
```

---

## 6. Testing with TEST-NET IPs & Safe Simulation

### Method A: Simulation mode (safest — no actual blocking)

CrowdSec has a **simulation mode** that logs decisions but does NOT enforce them:

```bash
# Check current simulation status
sudo cscli simulation status

# Enable simulation for a specific scenario (e.g., SSH brute-force)
sudo cscli simulation enable crowdsecurity/ssh-bf
sudo systemctl reload crowdsec

# Now test with an attack simulation — CrowdSec will show:
#   "decision : 1h (simulation) ban"
# but the IP will NOT actually be blocked.
```

Decisions in simulation mode appear with `(simul)` prefix in `cscli decisions list`.

### Method B: Manual ban with TEST-NET IPs (RFC 5735)

Use `192.0.2.0/24` (TEST-NET-1) ranges which are reserved for documentation/testing:

```bash
# Add a test ban (no real traffic uses TEST-NET IPs)
sudo cscli decisions add --ip 192.0.2.1 --duration 10m --reason "safety-test"

# Verify it appears in decisions
sudo cscli decisions list

# Verify it appears in nftables/iptables
sudo nft list set inet crowdsec crowdsec-blacklists
# or
sudo ipset list crowdsec-blacklists

# Remove the test decision
sudo cscli decisions delete --ip 192.0.2.1
```

### Method C: Attack simulation (cautious — will ban your source IP)

The standard CrowdSec test uses `crowdsecurity/http-probing`:

```bash
# From a test machine (NOT the operator's main IP):
curl -s http://YOUR_VPS_IP/../../etc/passwd

# Then monitor:
sudo cscli decisions list
```

> **⚠️ CRITICAL**: This WILL ban the source IP. Do NOT run this from Samm's Tailscale IP or any IP that needs access. Only run from a disposable test instance.

---

## 7. Community Blocklists & Subscriptions

### How they work

- CrowdSec aggregates signals from 200,000+ participating servers.
- **Community Blocklist** (free, contributing users): Curated list of malicious IPs.
- **Community Blocklist (Lite)** (free, non-contributing): Capped at ~3,000 IPs.
- **Community Blocklist (Premium)** (paid): Unlimited IPs, tailored to your stack.

### Subscription via Console

1. Go to [CrowdSec Console](https://console.crowdsec.net/) → Blocklists tab.
2. Subscribe to blocklists (free plan: up to 3 blocklists).
3. Blocklists refresh every 2 hours.

### Subscription via cscli

```bash
# Update hub index
sudo cscli hub update

# Install collections (extend detection)
sudo cscli collections install crowdsecurity/linux
sudo cscli collections install crowdsecurity/sshd
sudo cscli collections install crowdsecurity/http-cve
```

### View active blocklist decisions

```bash
sudo cscli metrics show decisions
# Look for origin: "CAPI" (community blocklist) and "lists:*" (subscribed lists)
```

### Risk with blocklists

- **False positives**: Legitimate services (Shodan, Googlebot) occasionally appear on blocklists.
- **AllowLists are critical**: Without pre-configured AllowLists, a community blocklist could block a Tailscale relay or similar service.
- **The AllowList (section 5) protects against this** — whitelisted IPs are exempt from ALL sources including community blocklists.

---

## 8. Checking Decisions

### List all active decisions

```bash
# All decisions
sudo cscli decisions list

# For a specific IP
sudo cscli decisions list -i 100.112.201.124

# From community blocklist only
sudo cscli decisions list --origin CAPI

# From a specific scenario
sudo cscli decisions list -s crowdsecurity/ssh-bf

# JSON output for parsing
sudo cscli decisions list -o json
```

### Check bouncer metrics

```bash
sudo cscli metrics show bouncers
```

### Check bouncer logs

```bash
sudo tail -f /var/log/crowdsec-firewall-bouncer.log
```

### Check firewall state

```bash
# nftables mode
sudo nft list set inet crowdsec crowdsec-blacklists
sudo nft list chain inet crowdsec crowdsec-chain

# iptables mode
sudo iptables -L INPUT -n | grep -i crowdsec
sudo ipset list crowdsec-blacklists
```

---

## 9. Rollback / Uninstall

### Graceful rollback (stop bouncer, keep CrowdSec agent)

```bash
# Stop and disable the bouncer
sudo systemctl stop crowdsec-firewall-bouncer
sudo systemctl disable crowdsec-firewall-bouncer

# The bouncer automatically cleans up its iptables/nftables rules on stop
# Verify rules are gone:
sudo nft list table inet crowdsec
# or
sudo iptables -L INPUT -n | grep -i crowdsec
```

### Full uninstall

```bash
# Remove bouncer package
sudo apt remove --purge crowdsec-firewall-bouncer-nftables
# or
sudo apt remove --purge crowdsec-firewall-bouncer-iptables

# Remove bouncer from LAPI
sudo cscli bouncers delete crowdsec-firewall-bouncer

# Remove allowlists (optional)
sudo cscli allowlists delete aizanta-whitelist

# Clean up leftover nftables tables (if any)
sudo nft delete table inet crowdsec 2>/dev/null || true
sudo nft delete table ip6 crowdsec6 2>/dev/null || true
```

### Important caveats from GitHub issues

- **Uninstall order matters**: Always remove/uninstall bouncer BEFORE removing crowdsec. If crowdsec is removed first, the bouncer is left in an unpredictable state ([crowdsec#548](https://github.com/crowdsecurity/crowdsec/issues/548)).
- **The bouncer SHOULD clean up its iptables rules on stop**, but if the process is killed or the package removal happens without proper service stop, rules may remain. Always verify after uninstall.
- **Re-install issues**: If re-installing, ensure old service files are fully cleaned. `systemctl edit --force --full` may be needed if the service unit is missing ([crowdsec#4446](https://github.com/crowdsecurity/crowdsec/issues/4446)).

### Rollback safety checklist

| Step | Command | Expected Outcome |
|---|---|---|
| 1. Stop bouncer | `systemctl stop crowdsec-firewall-bouncer` | Service stopped, firewall rules removed |
| 2. Verify rules gone | `nft list table inet crowdsec` | Table not found (or empty) |
| 3. Remove package | `apt remove --purge crowdsec-firewall-bouncer-nftables` | Package removed |
| 4. Clean LAPI | `cscli bouncers delete crowdsec-firewall-bouncer` | Bouncer removed from LAPI |
| 5. Verify access | SSH test from Samm's IP | Should connect normally |

---

## 10. Docker / Shared VPS Caveats

### Docker on the same host

If Docker containers are running on the same VPS, the bouncer needs special configuration:

#### iptables mode with Docker

```yaml
iptables_chains:
  - INPUT          # Block host services
  - DOCKER-USER    # Block Docker exposed ports
```

**Critical**: `DOCKER-USER` chain exists only for IPv4 by default. If IPv6 is enabled, the bouncer may crash on startup because `DOCKER-USER` doesn't exist for ip6tables. Workaround:

```yaml
disable_ipv6: true
# or use separate ipv4/ipv6 chains (bouncer v0.0.28+)
iptables_v4_chains:
  - INPUT
  - DOCKER-USER
iptables_v6_chains:
  - INPUT
```

#### nftables mode with Docker

```yaml
nftables_hooks:
  - input
  - forward    # <-- Required to block Docker container traffic
```

#### Boot order issue

If CrowdSec runs in Docker but the bouncer runs on the host, the bouncer may start **before** Docker and fail to find the `DOCKER-USER` chain:

```bash
# Fix: add Docker dependency to the bouncer service
sudo systemctl edit crowdsec-firewall-bouncer
```

Add:

```
[Unit]
After=network.target docker.service
Before=netfilter-persistent.service
Restart=always
RestartSec=5
```

([Source: GitHub issue #216](https://github.com/crowdsecurity/cs-firewall-bouncer/issues/216))

### Shared VPS (multi-tenant)

| Risk | Description | Mitigation |
|---|---|---|
| **nftables namespace collision** | Default table name `crowdsec` could conflict with other nftables rules | Use a unique table name in config |
| **iptables chain collision** | Default chain `CROWDSEC_CHAIN` may not be visible to other tenants | Use set-only mode for explicit control |
| **UFW interference** | UFW may flush rules on restart | Ensure bouncer restarts after UFW |
| **Resource limits** | ipset has max 131,072 entries by default (configurable via `ipset_size`) | Monitor with `cscli metrics` |
| **Traffic visibility** | Shared VPS may not have full traffic visibility | Only SSH/web logs are parsed; customize acquisition |

#### Recommended config for shared VPS

```yaml
mode: nftables
# If the VPS provider manages nftables, use set-only mode:
nftables:
  ipv4:
    enabled: true
    set-only: true    # Only manage set contents
    table: aizanta-crowdsec    # Custom table name to avoid collision
    chain: aizanta-chain
  ipv6:
    enabled: false
```

---

## 11. Ensuring Aizanta Traffic Is Not Blocked

### Multi-layer protection strategy

```
Layer 1: CrowdSec AllowList
  └─ cscli allowlists add aizanta-whitelist <IP>
  └─ Prevents CrowdSec from generating block decisions

Layer 2: UFW allow rules (pre-bouncer)
  └─ ufw allow from <IP> to any port <PORT>
  └─ Overrides any block even if AllowList is missed

Layer 3: Bouncer configuration
  └─ scenarios_not_containing: ["ssh"]  # if needed
  └─ origins: ["crowdsec"]  # exclude CAPI if risky
```

### Specific IPs to whitelist

| Entity | IP | Purpose |
|---|---|---|
| Samm Tailscale | `100.112.201.124` | Operator SSH + management |
| VPS Tailscale | `100.94.104.22` | Aizanta node inter-node |
| Tailscale CGNAT | `100.64.0.0/10` | All Tailscale peers (optional) |
| Localhost | `127.0.0.0/8`, `::1` | Local services |

### Aizanta ports that must remain untouched

All ports used by Aizanta services must be explicitly allowed via UFW **before** enabling the bouncer. The bouncer only blocks IPs flagged by CrowdSec — it does not interfere with port-level rules unless a banned IP connects.

**However**, if a community blocklist includes an IP that happens to source legitimate Aizanta traffic (e.g., a Tailscale DERP relay), that traffic would be blocked. **This is why AllowLists are essential.**

### Verification script (post-enablement)

```bash
echo "=== Checking Aizanta IPs are not banned ==="
sudo cscli decisions list -i 100.112.201.124
sudo cscli decisions list -i 100.94.104.22

echo "=== Verifying nftables does not block Aizanta IPs ==="
sudo nft list set inet crowdsec crowdsec-blacklists | grep -E '100\.(112|94)\.' || echo "✅ Aizanta IPs NOT in blocklist"

echo "=== Verifying UFW allows Aizanta ==="
sudo ufw status | grep -E '100\.(112|94)\.' || echo "⚠️  No UFW rules found for Aizanta IPs"
```

---

## 12. Safe Enablement Sequence (Recommended)

### Pre-flight checklist (run before any bouncer installation)

- [ ] CrowdSec agent and LAPI are installed and running
- [ ] Aizanta IPs are in `cscli allowlists` (section 5)
- [ ] UFW allow rules exist for Aizanta IPs on required ports
- [ ] You have a **separate out-of-band access method** (VPS console / IPMI)
- [ ] `cscli decisions list` is empty for Aizanta IPs
- [ ] Backups of `/etc/crowdsec/` exist

### Step-by-step

```bash
# 1. Create allowlists
sudo cscli allowlists create aizanta-whitelist -d "Aizanta trusted IPs"
sudo cscli allowlists add aizanta-whitelist 100.112.201.124 -d "Samm Tailscale"
sudo cscli allowlists add aizanta-whitelist 100.94.104.22 -d "VPS Tailscale"

# 2. Add UFW allow rules
sudo ufw allow from 100.112.201.124 to any port 22 proto tcp comment 'Samm-SSH'
sudo ufw allow from 100.94.104.22 to any port 22 proto tcp comment 'VPS-SSH'

# 3. Install bouncer
sudo apt install crowdsec-firewall-bouncer-nftables

# 4. Verify bouncer is running but decisions are simulated/whitelisted
sudo systemctl status crowdsec-firewall-bouncer

# 5. Test with a TEST-NET IP (Section 6 — Method B)
sudo cscli decisions add --ip 192.0.2.1 --duration 5m --reason "preflight-test"
sudo nft list set inet crowdsec crowdsec-blacklists
sudo cscli decisions delete --ip 192.0.2.1

# 6. Verify Aizanta IPs are NOT banned
sudo cscli decisions list -i 100.112.201.124
sudo cscli decisions list -i 100.94.104.22

# 7. Confirm Aizanta services are reachable
ssh <VPS> from Samm's Tailscale IP  # should succeed
```

### Post-enablement monitoring (first 24 hours)

```bash
# Monitor bouncer logs
sudo journalctl -u crowdsec-firewall-bouncer -f

# Check for any unexpected bans
sudo cscli decisions list

# Check bouncer metrics
sudo cscli metrics show bouncers
```

---

## 13. References

### Official documentation
| Resource | URL |
|---|---|
| Firewall Bouncer Docs | https://docs.crowdsec.net/u/bouncers/firewall/ |
| Installation Guide (Linux) | https://docs.crowdsec.net/u/getting_started/installation/linux/ |
| AllowLists (cscli) | https://docs.crowdsec.net/docs/local_api/centralized_allowlists/ |
| Whitelists (legacy) | https://docs.crowdsec.net/u/getting_started/post_installation/whitelists/ |
| Community Blocklist | https://docs.crowdsec.net/docs/central_api/community_blocklist |
| Simulation Mode | https://docs.crowdsec.net/docs/next/log_processor/scenarios/simulation |
| cscli decisions | https://docs.crowdsec.net/docs/next/cscli/cscli_decisions/ |
| cscli allowlists | https://docs.crowdsec.net/docs/cscli/cscli_allowlists/ |
| Blocklist Subscription | https://docs.crowdsec.net/u/console/blocklists/subscription/ |
| Bouncer Configuration Guide | https://docs.crowdsec.net/u/user_guides/bouncers_configuration |

### GitHub repositories
| Resource | URL |
|---|---|
| cs-firewall-bouncer | https://github.com/crowdsecurity/cs-firewall-bouncer |
| CrowdSec main repo | https://github.com/crowdsecurity/crowdsec |

### Community discussions
| Topic | URL |
|---|---|
| CrowdSec + fail2ban coexistence | https://discourse.crowdsec.net/t/crowdsec-and-fail2ban-on-same-server/1256 |
| Docker + DOCKER-USER chain issues | https://github.com/crowdsecurity/cs-firewall-bouncer/issues/346 |
| Boot order with Docker | https://github.com/crowdsecurity/cs-firewall-bouncer/issues/216 |
| UFW log integration | https://discourse.crowdsec.net/t/configuring-crowdsec-to-process-ufw-logs/2618 |
| Uninstall cleanup issue | https://github.com/crowdsecurity/crowdsec/issues/548 |

### Third-party guides
| Resource | URL |
|---|---|
| MassiveGRID: CrowdSec on VPS | https://www.massivegrid.com/blog/install-crowdsec-ubuntu-vps/ |
| Data Mammoth: CrowdSec on Ubuntu 24.04 | https://data-mammoth.com/support/security/how-to-install-crowdsec-ubuntu |
| RouteHarden: fail2ban + CrowdSec VPN | https://routeharden.com/blog/fail2ban-crowdsec-vpn-servers |
| ComputingForGeeks: CrowdSec Ubuntu 26.04 | https://computingforgeeks.com/install-crowdsec-ubuntu-2604/ |
| AZDIGI: CrowdSec on Linux VPS | https://azdigi.com/en/blog/cong-cu/crowdsec-on-linux-vps-next-generation-ids-to-replace-fail2ban |

---

**End of report.**

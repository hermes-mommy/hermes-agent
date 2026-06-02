# External Readiness Report: UFW Safety & Lockout-Safe Rollout

**Report ID**: `STEP-P0-004-external-ufw-safety`
**Date**: 2026-05-31
**Target OS**: Ubuntu 24.04 LTS (Noble)
**Scope**: Shared VPS running Aizanta services (Tailscale IP:80, Docker:5432/6379 localhost, SSH)
**Downstream**: Parent will synthesize before applying firewall rules.

---

## 1. Official Documentation Sources

| Source | URL | Relevance |
|--------|-----|-----------|
| Ubuntu Server — Firewall (UFW) | https://ubuntu.com/server/docs/how-to/security/firewalls/ | Official Ubuntu docs: enable/disable, `--dry-run`, status, app profiles, IP masquerading |
| UFW Manpage (Noble 24.04) | https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html | Canonical manpage: REMOTE MANAGEMENT section, rule syntax, rate limiting, logging levels |
| UFW Framework Manpage | https://manpages.ubuntu.com/manpages/noble/man8/ufw-framework.8.html | `before.rules`/`after.rules`, DOCKER-USER interaction, sysctl, libvirt bridging |
| Ubuntu Community UFW Wiki | https://help.ubuntu.com/community/UFW | Basic reference: allow/deny, numbered rules, examples |
| Docker Docs — Packet Filtering & Firewalls | https://github.com/docker/docs/blob/main/content/manuals/engine/network/packet-filtering-firewalls.md | Official Docker docs on UFW incompatibility, DOCKER-USER chain, iptables behavior |
| DigitalOcean UFW Tutorial | https://www.digitalocean.com/community/tutorials/how-to-set-up-a-firewall-with-ufw-on-ubuntu | Industry-standard walkthrough (Feb 2024, still current) |

---

## 2. UFW Architecture & Defaults (Ubuntu 24.04)

### 2.1 Installation State

UFW ships with Ubuntu but is **disabled by default**. Default policies on install:

| Policy | Default | Description |
|--------|---------|-------------|
| `incoming` | `deny` | Blocks all incoming connections unless explicitly allowed |
| `outgoing` | `allow` | Permits all outgoing connections from the host |
| `routed` | `deny` | No packet forwarding between interfaces (disabled) |

> **Source**: https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html — "On installation, ufw is disabled with a default incoming policy of deny, a default forward policy of deny, and a default outgoing policy of allow"

### 2.2 Key Commands Reference

| Command | Purpose |
|---------|---------|
| `ufw status` | Show if active + rule list |
| `ufw status verbose` | Show policies, logging level, rules |
| `ufw status numbered` | Show rules with index numbers (for insert/delete) |
| `ufw --dry-run allow <port>` | Preview rule output without applying |
| `ufw --dry-run enable` | Preview what enabling would do |
| `ufw show added` | Show rules added but not yet applied |
| `ufw show raw` | Show raw iptables/nftables state |
| `ufw default deny incoming` | Set default incoming policy |
| `ufw default allow outgoing` | Set default outgoing policy |
| `ufw default deny routed` | Set default forward policy |
| `ufw allow ssh` | Allow SSH by service name (port 22) |
| `ufw limit ssh/tcp` | Rate-limit SSH (6 conns/30s) |
| `ufw enable` | Activate firewall (prompts over SSH) |
| `ufw --force enable` | Enable without interactive prompt (⚠ careful) |
| `ufw disable` | Deactivate firewall completely |
| `ufw reload` | Reload rules without full disable |
| `ufw reset` | Disable + reset to install defaults (⚠ dangerous remotely) |
| `ufw logging on` | Enable logging (default: low level) |

---

## 3. Lockout-Safe Rollout: Critical Sequence

### 3.1 The #1 Risk

Enabling UFW **before** allowing SSH on a remote server causes **immediate disconnection** with no way back (short of console access). This is the single most common UFW mistake documented across every source.

> "When running ufw enable or starting ufw via its initscript, ufw will flush its chains. This is required so ufw can maintain a consistent state, but it may drop existing connections (eg ssh)."
> — UFW manpage REMOTE MANAGEMENT section

> "The key is order of operations: configure first, enable last."
> — https://systemadministration.net/ufw-in-deny-all-allow-only-whats-needed-mode-without-locking-yourself-out-of-ssh/

### 3.2 UFW's Built-In SSH Safeguard

UFW **prompts for confirmation** when `ufw enable` is run over an active SSH session:

```
Command may disrupt existing ssh connections. Proceed with operation (y|n)?
```

This prompt is NOT a guarantee — it only warns. If no SSH `allow` rule exists and you confirm, the session drops. Use `ufw --force enable` only when certain SSH is already allowed.

### 3.3 Recommended Lockout-Safe Command Sequence

```bash
# ===== PHASE 1: PREFLIGHT =====

# 1. Assess current state
sudo ufw status verbose

# 2. Identify active listening services (inventory before locking down)
ss -tulpn

# 3. Confirm SSH port (default 22 or custom?)
grep -i "^Port " /etc/ssh/sshd_config


# ===== PHASE 2: CONFIGURE RULES (BEFORE ENABLING) =====

# 4. Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw default deny routed

# 5. ALLOW SSH FIRST — critical lockout prevention
#    Option A: Allow by service name (port 22)
sudo ufw allow ssh

#    Option B: Restrict to specific admin IP (recommended for shared VPS)
sudo ufw allow from <ADMIN_IP> to any port 22 proto tcp comment 'SSH from admin'

#    Option C: Rate-limited SSH (use limit instead of allow after initial setup)
sudo ufw limit ssh/tcp comment 'SSH rate-limited'


# ===== PHASE 3: ADD SERVICE RULES =====

# 6. Allow Aizanta services
#    Port 80 on Tailscale IP — allow on tailscale interface only
sudo ufw allow in on tailscale0 to any port 80 proto tcp comment 'Aizanta HTTP on Tailscale'

#    Port 5432 (PostgreSQL via Docker) — localhost only (already default-safe)
#    Port 6379 (Redis via Docker) — localhost only (already default-safe)
#    These are bound to 127.0.0.1 via Docker, no UFW rule needed for external block.
#    But add an explicit loopback allow:
sudo ufw allow from 127.0.0.1 to any port 5432 proto tcp comment 'PostgreSQL localhost'
sudo ufw allow from 127.0.0.1 to any port 6379 proto tcp comment 'Redis localhost'


# ===== PHASE 4: DRY-RUN BEFORE ENABLING =====

# 7. Preview what will be applied (zero risk)
sudo ufw --dry-run enable

# 8. Verify the added rules
sudo ufw status numbered
sudo ufw show added


# ===== PHASE 5: ENABLE (WITH SAFETY NET) =====

# 9. KEEP EXISTING SSH SESSION OPEN
#    Open a SECOND SSH session in another terminal as a backup.
#    If the first session drops, use the second to roll back.

# 10. Enable firewall
sudo ufw enable
#    Type 'y' when prompted

# 11. Immediate verification
sudo ufw status verbose
sudo ufw status numbered


# ===== PHASE 6: POST-ENABLE VERIFICATION =====

# 12. Verify from outside (run from a separate machine/non-Tailscale IP)
#     nmap -p 22,80,443,5432,6379 <VPS_PUBLIC_IP>

# 13. Confirm only expected ports are open
ss -tulpn | grep LISTEN

# 14. Review logs for blocked traffic
sudo tail -f /var/log/ufw.log


# ===== ROLLBACK (if locked out) =====

# If SSH drops after enable:
#   Use hosting provider's web console / IPMI / rescue mode
#   Then:
sudo ufw disable
#   Or:
sudo ufw allow ssh && sudo ufw reload
```

---

## 4. Rule Ordering & Evaluation

### 4.1 First-Match-Wins

UFW evaluates rules **top-to-bottom** and stops at the first match. This matters when rules overlap:

```bash
# BAD: blanket allow above specific deny — deny never matches
sudo ufw allow ssh              # matches ALL SSH traffic first
sudo ufw deny from 10.0.0.5 to any port 22  # never evaluated

# GOOD: specific deny above blanket allow
sudo ufw insert 1 deny from 10.0.0.5 to any port 22
sudo ufw allow ssh
```

### 4.2 Rule Insertion

```bash
sudo ufw status numbered        # see current order with indices
sudo ufw insert 2 allow from 192.168.1.0/24 to any port 22 proto tcp
```

### 4.3 Rule Deletion

```bash
# By number (from `ufw status numbered`) — removes only that entry (IPv4 or v6)
sudo ufw delete 3

# By specification — removes matching rules for both IPv4 and v6
sudo ufw delete allow ssh
```

> **Source**: https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html (RULE SYNTAX section)

---

## 5. `--dry-run` Usage

UFW's `--dry-run` flag shows what changes would be made **without actually applying them**. It outputs the raw iptables rules that would be loaded.

```bash
# Preview allow rule
sudo ufw --dry-run allow http

# Preview enabling the firewall
sudo ufw --dry-run enable

# Preview setting default policy
sudo ufw --dry-run default deny incoming
```

The output shows the `*filter` table rules with `ufw-user-input`, `ufw-user-output`, `ufw-user-forward` chains and the specific rule tuples.

> **Source**: https://ubuntu.com/server/docs/how-to/security/firewalls/ — "Adding the --dry-run option to a ufw command will output the resulting rules, but not apply them."

---

## 6. Logging

### 6.1 Enable & Configure

```bash
sudo ufw logging on           # enable at default 'low' level
sudo ufw logging medium       # more verbose
sudo ufw logging high         # very verbose (use sparingly)
```

### 6.2 Log Levels

| Level | Detail | Use Case |
|-------|--------|----------|
| `low` | Only blocked packets | Production baseline |
| `medium` | Blocked + allowed packets with rate limiting | Troubleshooting |
| `high` | All packets, full rate limit | Debug only |
| `full` | Every packet | Never in production |

### 6.3 Log Location

Logs go to `/var/log/ufw.log` via `LOG_KERN` syslog facility (rsyslog).

```bash
# Monitor in real-time
sudo tail -f /var/log/ufw.log

# Check for blocked attempts
sudo grep "UFW BLOCK" /var/log/ufw.log | tail -20
```

> **Source**: https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html (LOGGING section)

---

## 7. Rollback & Recovery

### 7.1 Planned Rollback

```bash
# Full disable (restores original state)
sudo ufw disable

# Reload rules (apply after editing /etc/ufw/*.rules)
sudo ufw reload

# Reset to install defaults (⚠ stops firewall entirely)
sudo ufw --force reset
```

### 7.2 Emergency Recovery (if locked out)

If SSH drops after enabling UFW without an SSH allow rule:

1. **Console access**: Use hosting provider's web console / IPMI / KVM
2. **Recovery commands**:
   ```bash
   sudo ufw allow ssh    # add SSH rule
   sudo ufw reload       # apply without full restart
   # OR
   sudo ufw disable      # turn off entirely
   ```
3. **Alternative**: If you have a second SSH session open (preferred pattern), use it to fix rules before closing the first.

### 7.3 Pre-Rollback Snapshot

Before enabling UFW for the first time on production:
```bash
# Backup current UFW configuration
sudo cp -a /etc/ufw /etc/ufw.backup.$(date +%Y%m%d_%H%M%S)

# Verify backup
ls -la /etc/ufw.backup.*
```

> **Source**: https://www.hostmycode.com/blog/ufw-firewall-setup-vps-2026-ssh-safe-hardening-playbook — "Rollback plan (do this before you need it)"

---

## 8. Docker + UFW: The Critical Bypass Issue

### 8.1 Root Cause

Docker bypasses UFW **by design**. When Docker publishes a container port (`-p 5432:5432`), it writes DNAT rules directly into the `PREROUTING` chain of the `nat` table and ACCEPT rules into the `FORWARD` chain. UFW only manages the `INPUT` and `OUTPUT` chains. Packets destined for Docker-published ports are NAT'd and forwarded **before** UFW's `INPUT` rules are evaluated.

> "When you publish a container's ports using Docker, traffic to and from that container gets diverted before it goes through the ufw firewall settings."
> — https://github.com/docker/docs/blob/main/content/manuals/engine/network/packet-filtering-firewalls.md

> "UFW is not a firewall. It's a friendly wrapper around iptables. Docker is also not asking UFW for permission. Packets destined for a published container port never traverse the INPUT chain."
> — https://blog.authon.dev/why-docker-bypasses-ufw-and-how-to-actually-lock-it-down

### 8.2 Impact on Aizanta

In the current setup:
- **PostgreSQL (5432)** and **Redis (6379)** are Docker containers on the host
- If they publish ports to `0.0.0.0` (the Docker default), they are **reachable from the internet** regardless of UFW rules
- UFW's `default deny incoming` will NOT protect these ports

### 8.3 Mitigation Options

| Solution | Effort | Impact | Recommendation for Aizanta |
|----------|--------|--------|---------------------------|
| **Bind to 127.0.0.1** in docker-compose.yml | Low | Minimal — services behind reverse proxy | ✅ **Primary** — simplest, most reliable |
| **DOCKER-USER chain** via `/etc/ufw/after.rules` | Medium | None if done correctly | ✅ Secondary — defense-in-depth |
| `ufw-docker` tool (chaifeng/ufw-docker) | Low | Uses DOCKER-USER + automation | ⚠️ Optional |
| `iptables: false` in daemon.json | Low | Breaks container networking | ❌ Not recommended |

**Recommended approach** (for Aizanta's current architecture):

```yaml
# docker-compose.yml — bind to localhost only
services:
  postgres:
    ports:
      - "127.0.0.1:5432:5432"   # not accessible from outside
  redis:
    ports:
      - "127.0.0.1:6379:6379"   # not accessible from outside
```

AND add DOCKER-USER rules as a safety net:

```bash
# Add to /etc/ufw/after.rules before COMMIT:
# BEGIN UFW AND DOCKER
*filter
:ufw-user-forward - [0:0]
:DOCKER-USER - [0:0]
-A DOCKER-USER -j ufw-user-forward
-A DOCKER-USER -j DROP
COMMIT
# END UFW AND DOCKER
```

Then restart UFW:
```bash
sudo systemctl restart ufw
```

> **Sources**:
> - https://www.virtua.cloud/learn/en/tutorials/docker-ufw-firewall-fix-vps
> - https://cr0x.net/en/ufw-docker-lockdown-compose/
> - https://github.com/chaifeng/ufw-docker
> - https://blog.authon.dev/why-docker-bypasses-ufw-and-how-to-actually-lock-it-down

---

## 9. Shared VPS Considerations

### 9.1 Interface-Aware Rules

A shared VPS likely has:
- A **public interface** (e.g., `eth0`) for internet traffic
- A **Tailscale interface** (e.g., `tailscale0`) for private mesh
- A **loopback interface** (`lo`) for localhost traffic

Best practice: scope rules to specific interfaces:

```bash
# Allow SSH only on public interface
sudo ufw allow in on eth0 to any port 22 proto tcp

# Allow Aizanta HTTP only on Tailscale interface
sudo ufw allow in on tailscale0 to any port 80 proto tcp

# Allow database ports only on loopback
sudo ufw allow from 127.0.0.1 to any port 5432 proto tcp
sudo ufw allow from 127.0.0.1 to any port 6379 proto tcp
```

### 9.2 Rate Limiting SSH

UFW's built-in `limit` is effective at reducing brute-force noise on shared VPS:

```bash
sudo ufw limit ssh/tcp
```

The limit: **6 or more connections from one IP within 30 seconds** → blocked temporarily.

> **Note**: If you use automation (rsync, Ansible, CI/CD) that opens many quick SSH connections, this may trigger false positives. Use SSH `ControlMaster` to reuse connections, or add a dedicated allow for your automation IP above the limit rule.

### 9.3 IPv6

IPv6 is **enabled by default** in UFW on Ubuntu 24.04. Every rule auto-generates a v6 counterpart. Disable only if the server has no IPv6 connectivity:

```bash
# Check current setting
grep IPV6 /etc/default/ufw

# Disable IPv6 in UFW (if needed)
sudo sed -i 's/IPV6=yes/IPV6=no/' /etc/default/ufw
sudo ufw reload
```

> **Source**: https://computingforgeeks.com/configure-ufw-firewall-ubuntu-2604/ — "Ubuntu 26.04 has IPv6 support enabled in UFW by default"

### 9.4 Fail2Ban Integration

UFW pairs well with Fail2Ban for dynamic IP banning. Fail2Ban can use UFW as its ban action:

```ini
# /etc/fail2ban/jail.local
[DEFAULT]
banaction = ufw
```

> **Source**: https://www.massivegrid.com/blog/ufw-firewall-advanced-rules-ubuntu-vps/

---

## 10. Recommended Safety Checklist for Aizanta

### Pre-Enable Checklist

- [ ] `sudo ufw status` — confirm UFW is currently inactive
- [ ] `ss -tulpn` — inventory all listening services and their bind addresses
- [ ] Check Docker port bindings: `docker ps --format '{{.Names}}: {{.Ports}}'`
- [ ] Confirm PostgreSQL and Redis bind to `127.0.0.1`, not `0.0.0.0`
- [ ] Confirm Tailscale interface name: `ip link show | grep tailscale`
- [ ] Confirm SSH port: `grep "^Port " /etc/ssh/sshd_config`
- [ ] Identify admin source IP(s) for SSH access
- [ ] Have a **second SSH session open** (parallel connection)
- [ ] Have console access available (VPS provider web console)
- [ ] Backup `/etc/ufw/`: `sudo cp -a /etc/ufw /etc/ufw.backup.$(date +%Y%m%d_%H%M%S)`

### Post-Enable Checklist

- [ ] `sudo ufw status verbose` — confirm `Status: active` with correct policies
- [ ] `sudo ufw status numbered` — verify rule order
- [ ] Test SSH from a **second terminal** (keep original session as fallback)
- [ ] Test port 80 reachability via Tailscale IP
- [ ] Verify ports 5432 and 6379 are **not** reachable from outside: `nmap -p 5432,6379 <VPS_IP>`
- [ ] Check logs: `sudo tail -5 /var/log/ufw.log`
- [ ] Confirm Docker containers still work: `docker ps` and `docker compose ps`
- [ ] Apply DOCKER-USER fix if Docker bindings are not restricted to 127.0.0.1

---

## 11. Official Documentation URLs (Complete List)

| Document | URL |
|----------|-----|
| Ubuntu Server — Firewall | https://ubuntu.com/server/docs/how-to/security/firewalls/ |
| UFW Manpage (Noble 24.04) | https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html |
| UFW Framework Manpage | https://manpages.ubuntu.com/manpages/noble/man8/ufw-framework.8.html |
| Ubuntu Community UFW Wiki | https://help.ubuntu.com/community/UFW |
| Docker — Packet Filtering Firewalls | https://github.com/docker/docs/blob/main/content/manuals/engine/network/packet-filtering-firewalls.md |
| Docker UFW Issue (#690) | https://github.com/docker/for-linux/issues/690 |
| ufw-docker (chaifeng) | https://github.com/chaifeng/ufw-docker |

---

## 12. Key Sources Referenced

1. **Ubuntu Server Docs** — https://ubuntu.com/server/docs/how-to/security/firewalls/
2. **UFW Manpage (Noble)** — https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html
3. **computingforgeeks.com** — "Configure UFW Firewall on Ubuntu 26.04 LTS" (2026-04-14)
4. **systemadministration.net** — "UFW in deny all, allow only what's needed mode" (2026-02-02)
5. **DigitalOcean Tutorial** — "How to Set Up a Firewall with UFW on Ubuntu" (2024-02-28)
6. **linuxize.com** — "How to Set Up a Firewall with UFW on Ubuntu 24.04" (2026-03-25)
7. **HostMyCode** — "UFW Firewall Setup for a VPS in 2026" (2026-04-13)
8. **virtua.cloud** — "Fix Docker Bypassing UFW: 4 Solutions" (2026-03-19)
9. **cr0x.net** — "Ubuntu 24.04: UFW + Docker — lock down containers" (2025-10-11)
10. **blog.authon.dev** — "Why Docker bypasses UFW and how to actually lock it down" (2026-05-11)
11. **MassiveGRID Blog** — "UFW Firewall Deep Dive: Advanced Rules for Ubuntu VPS" (2026-02-28)

---

*Report prepared for downstream parent synthesis. No local/VPS changes performed.*

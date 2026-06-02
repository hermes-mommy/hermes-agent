# External Research Report: Fail2Ban Lockout Prevention for Remote SSH (Tailscale + UFW)

**Scope**: fail2ban `ignoreip` whitelist strategy, safe testing, UFW integration, shared VPS/Docker caveats
**Date**: 2026-05-31
**Sources**: Official fail2ban documentation (GitHub manpage, jail.conf), Tailscale docs, community best-practice guides, RFC 5737

---

## Table of Contents

1. [Core Mechanism: How `ignoreip` Works](#1-core-mechanism-how-ignoreip-works)
2. [Tailscale CGNAT: IP Ranges and Whitelist Strategy](#2-tailscale-cgnat-ip-ranges-and-whitelist-strategy)
3. [UFW Integration: Ban Action Behaviour](#3-ufw-integration-ban-action-behaviour)
4. [Safe Testing Without Lockout](#4-safe-testing-without-lockout)
5. [Shared VPS / Docker Caveats](#5-shared-vps--docker-caveats)
6. [Recovery If Locked Out](#6-recovery-if-locked-out)
7. [Operator-Protective Checklist](#7-operator-protective-checklist)
8. [References](#8-references)

---

## 1. Core Mechanism: How `ignoreip` Works

### Configuration

`ignoreip` is defined in `jail.conf` (default) or `jail.local` (override). **Never edit `jail.conf`** — package updates overwrite it. All customizations go in `jail.local` or `jail.d/*.local`.

**Evidence** — official manpage states:

> `ignoreip` — list of IPs not to ban. They can also include CIDR mask or can be DNS (FQDN), or even raw string (if jail banning IDs instead of IPs). The option affects additionally to `ignoreself` (if true) and don't need to contain own DNS resp. IPs of the running host.

**Source**: [`jail.conf.5` — fail2ban manpage](https://github.com/fail2ban/fail2ban/blob/master/man/jail.conf.5)

Default value from the shipped `jail.conf`:

```ini
ignoreip = 127.0.0.1/8 ::1
ignoreself = true
```

**Source**: [`config/jail.conf` — fail2ban repository](https://github.com/fail2ban/fail2ban/blob/master/config/jail.conf)

### Critical Rules

| Rule | Detail |
|------|--------|
| **Section names are CASE-SENSITIVE** | Use `[DEFAULT]` — not `[default]`. This is a known gotcha (fail2ban issue #2633). |
| **`ignoreip` replaces, not merges** | Setting `ignoreip` in `jail.local` **replaces** the default. You must re-include `127.0.0.1/8 ::1` if you want them kept. |
| **`ignoreself` is separate** | Default `true` — prevents banning the server's own IPs. No need to add them to `ignoreip`. |
| **Only affects automatic bans** | `ignoreip` prevents bans from log-monitoring. Manual `fail2ban-client set <jail> banip <IP>` **will still ban** even if IP is in `ignoreip` (with a warning: "User knows best") — [fail2ban discussion #4060](https://github.com/fail2ban/fail2ban/discussions/4060). |

### Dynamic Ignore (No Restart Needed)

Three approaches to update ignore list without restarting fail2ban:

1. **Runtime add/remove** via `fail2ban-client`:
   ```bash
   fail2ban-client set sshd addignoreip 203.0.113.1
   fail2ban-client set sshd delignoreip 203.0.113.1
   ```

2. **File-based lazy loading** — specify a file that fail2ban reads on demand:
   ```ini
   ignoreip = 127.0.0.1/8 ::1 file:/etc/fail2ban/ignorelist.txt
   ```
   Each line in the file: IP, CIDR, DNS/FQDN, or raw string. Fail2ban reloads automatically after a small latency. ([Discussion #3615](https://github.com/fail2ban/fail2ban/discussions/3615))

3. **`ignorecommand`** — an external command that returns exit code 0 to indicate IP should be ignored:
   ```ini
   ignorecommand = grep -sqxF "<ip>" /etc/fail2ban/allowed-ips.txt
   ```

### Recommended `ignoreip` for This Setup

```ini
[DEFAULT]
# Always keep loopback:
ignoreip = 127.0.0.1/8 ::1

# === Operator IPs (discover before enabling) ===
# Replace with actual values — see discovery commands below:
# <OPERATOR_SSH_SOURCE_IP>        # Public IP of Samm's connection
# <VPS_TAILSCALE_IP>              # Tailscale IP of the VPS (e.g. 100.x.x.x)
# <OPERATOR_TAILSCALE_IP>         # Tailscale IP of Samm's client (e.g. 100.x.x.y)
```

---

## 2. Tailscale CGNAT: IP Ranges and Whitelist Strategy

### Tailscale Address Space

| Range | Purpose |
|-------|---------|
| `100.64.0.0/10` | Full CGNAT range (RFC 6598). Tailscale assigns device IPs from this block. |
| `100.100.0.0/24` | Tailscale internal use — unavailable for device IPs. |
| `100.100.100.0/24` | Tailscale internal use. |
| `100.100.100.100` | Quad100 — device-local DNS resolver and management interface. |
| `100.115.92.0/23` | Tailscale internal use. |
| `fd7a:115c:a1e0::/48` | Tailscale IPv6 ULA prefix. |

**Source**: [Tailscale Reserved IP Addresses](https://tailscale.com/docs/reference/reserved-ip-addresses)

### Whitelist Strategy: Be Specific, Not Broad

**DO NOT whitelist the entire `100.64.0.0/10` CGNAT range.** This would allow any Tailscale node (including compromised ones or non-admin nodes on the same tailnet) to bypass fail2ban SSH protection.

**DO whitelist only specific Tailscale IPs:**

```
ignoreip = 127.0.0.1/8 ::1
           100.XX.YY.ZZ     # VPS Tailscale IP (discover via `tailscale ip`)
           100.AA.BB.CC     # Operator/Samm client Tailscale IP
```

### How to Discover Tailscale IPs (On the VPS)

```bash
# VPS own Tailscale IPs:
tailscale ip          # IPv4 and IPv6 of this node
tailscale ip -4       # IPv4 only
tailscale ip -6       # IPv6 only

# All nodes in tailnet + their IPs:
tailscale status      # Shows all connected nodes with their Tailscale IPs

# Current active SSH connection's source IP:
echo $SSH_CONNECTION  # Shows: source_ip source_port dest_ip dest_port
who -m                # Shows current session with source IP
ss -tuna | grep ':22 ' | awk '{print $5}' | sort -u  # All active SSH source IPs
```

> **Implementation Note**: If the operator's Tailscale IP is unknown at config time, the setup script MUST block and require explicit input, or infer it safely via `tailscale status` + `$SSH_CONNECTION` cross-reference. See checklist §7.

---

## 3. UFW Integration: Ban Action Behaviour

### How fail2ban Uses UFW

The UFW action definition (shipped with fail2ban):

**Source**: [`config/action.d/ufw.conf`](https://github.com/fail2ban/fail2ban/blob/master/config/action.d/ufw.conf)

```bash
actionban = if [ -n "<application>" ] && ufw app info "<application>"
            then
              ufw <add> <blocktype> from <ip> to <destination> app "<application>" comment "<comment>"
            else
              ufw <add> <blocktype> from <ip> to <destination> comment "<comment>"
            fi
            <kill>

actionunban = if [ -n "<application>" ] && ufw app info "<application>"
              then
                ufw delete <blocktype> from <ip> to <destination> app "<application>"
              else
                ufw delete <blocktype> from <ip> to <destination>
              fi
```

Key parameters:
- `<add>` defaults to `insert 1` — prepends rule at highest priority
- `<blocktype>` defaults to `deny` (can be `reject`)
- `kill-mode=ss` or `kill-mode=conntrack` terminates existing connections from banned IP immediately

### Configuration

On Ubuntu 24.04+, the shipped `defaults-debian.conf` sets `banaction = nftables`. To override for UFW:

```ini
# /etc/fail2ban/jail.d/zz-ufw-defaults.local
[DEFAULT]
banaction = ufw
banaction_allports = ufw
```

The filename `zz-` prefix ensures it sorts after `defaults-debian.conf` alphabetically. ([Source](https://www.virtua.cloud/learn/en/tutorials/fail2ban-setup-linux-vps))

### How a Ban Looks in UFW

```bash
# After fail2ban bans an IP:
ufw status numbered

# Output:
# [ 1] 192.0.2.1              DENY IN     Anywhere
# [ 2] Anywhere               ALLOW IN    Anywhere
```

The ban rule appears at position 1 (highest priority), before any allow rules.

### Important: UFW Must Be Enabled

The UFW action adds rules via `ufw` commands, but UFW must be `enabled` for those rules to take effect. Verify:

```bash
ufw status
# Status: active
```

---

## 4. Safe Testing Without Lockout

### Phase 1: Pre-Flight Verification (Before Enabling fail2ban)

Before enabling the SSH jail, verify all components work:

```bash
# 1. Check UFW status
sudo ufw status verbose

# 2. Verify fail2ban can start cleanly
sudo fail2ban-client -x start
sudo fail2ban-client status

# 3. Check that SSH source IP + Tailscale IPs are known
echo "SSH connection: $SSH_CONNECTION"
tailscale ip -4
```

### Phase 2: Verify ignoreip Configuration

```bash
# After configuring jail.local, verify ignoreip is loaded:
sudo fail2ban-client -d | grep ignoreip

# Must show your configured IPs, including the ones you set
# If empty: check that section name is [DEFAULT] (uppercase)
```

**Source**: [fail2ban issue #2633](https://github.com/fail2ban/fail2ban/issues/2633) — case-sensitive section names.

### Phase 3: Safe Manual Ban Test (TEST-NET IPs)

Use [RFC 5737](https://datatracker.ietf.org/doc/html/rfc5737) documentation ranges — guaranteed not to exist on your network:

| Block | Range |
|-------|-------|
| TEST-NET-1 | `192.0.2.0/24` |
| TEST-NET-2 | `198.51.100.0/24` |
| TEST-NET-3 | `203.0.113.0/24` |

Test procedure:

```bash
# 1. Ban a TEST-NET IP manually:
sudo fail2ban-client set sshd banip 198.51.100.99

# 2. Verify the ban appears in fail2ban:
sudo fail2ban-client status sshd
# Banned IP list: 198.51.100.99

# 3. Verify the UFW rule was created:
sudo ufw status numbered
# Expect: [1] 198.51.100.99 DENY IN Anywhere

# 4. Verify operator IP is NOT banned (this is critical):
sudo fail2ban-client status sshd
# Must NOT show operator's SSH source IP or Tailscale IP

# 5. Verify operator can STILL SSH (re-confirm connectivity):
# (This should pass if ignoreip is working)

# 6. Unban the test IP:
sudo fail2ban-client set sshd unbanip 198.51.100.99

# 7. Verify UFW rule is removed:
sudo ufw status numbered
# The test IP rule should be gone
```

### Phase 4: Verify Automatic Ban Behaviour (Controlled Test)

> ⚠️ **Never intentionally fail SSH from the operator's own IP.** Always use a second connection or a different source IP.

If you have a second device/VPN exit IP available:

```bash
# From the second device, intentionally fail SSH multiple times:
ssh nonexistent@<VPS_IP>    # Fail intentionally (wrong user)
# Repeat > maxretry times

# Back on operator's session, verify:
sudo fail2ban-client status sshd
# The second device IP should be banned
# The operator IP must NOT be banned

# Verify UFW block is active:
sudo ufw status numbered | grep <second-device-IP>

# Unban when test is complete:
sudo fail2ban-client unban <second-device-IP>
```

### Phase 5: Add Operator IP to ignoreip at Runtime (No Restart)

```bash
# Add operator IP without restarting:
sudo fail2ban-client set sshd addignoreip <OPERATOR_SSH_IP>
sudo fail2ban-client set sshd addignoreip <OPERATOR_TAILSCALE_IP>

# Verify it's in the ignore list:
sudo fail2ban-client get sshd ignoreip
```

This is the safest approach — add the IPs first, then enable the jail.

---

## 5. Shared VPS / Docker Caveats

### Chain Selection: INPUT vs DOCKER-USER

Fail2Ban's default chain is `INPUT`. This works for host services (SSH daemon runs on host).

For Docker containers (ports published to host), traffic flows through:
```
PREROUTING (DNAT) → FORWARD → DOCKER-USER → DOCKER → Container
```

It **never hits INPUT**. A fail2ban rule on INPUT chain cannot block traffic to Docker containers.

**Source**: [Fail2Ban and Docker Wiki](https://github.com/fail2ban/fail2ban/wiki/Fail2Ban-and-Docker)

| Service Location | Correct Chain |
|-----------------|---------------|
| SSH on host (default) | `INPUT` (default) |
| Docker container | `DOCKER-USER` |
| Both host + Docker services | Separate jails per chain |

### Docker Bridge Networks

Docker creates virtual networks in the `172.17.0.0/16` range (default docker bridge). **Do NOT add these to `ignoreip`** — that would allow containers to bypass bans. If fail2ban is running on the host and monitoring SSH, Docker containers on the bridge network are irrelevant because they don't connect to SSH externally.

### Aizanta / Internal Service Traffic

If Aizanta (or any internal agent) runs as a Docker container and accesses host services:

- If Aizanta connects via Tailscale: use the Tailscale IP whitelist (covered above)
- If Aizanta connects via local network (Docker bridge → host): traffic stays internal and never triggers SSH auth failures
- If Aizanta connects via external IP and authenticates to SSH: it should be treated as an operator IP and whitelisted

**Rule**: Only whitelist what you know and trust. Broad ignore patterns (like `100.64.0.0/10`, `172.16.0.0/12`) weaken security.

### Recidive Jail (Repeat Offender Escalation)

The `recidive` jail monitors fail2ban's own log for repeat offenders:

**Source**: [`config/filter.d/recidive.conf`](https://github.com/fail2ban/fail2ban/blob/master/config/filter.d/recidive.conf)

```ini
[recidive]
enabled   = true
logpath   = /var/log/fail2ban.log
banaction = ufw
bantime   = 604800    # 7 days
findtime  = 86400     # 24 hours
maxretry  = 5         # 5 bans from any jail = recidive trigger
```

**Modern alternative**: `bantime.increment` in the primary jail handles escalation without a separate recidive jail. ([Discussion #3769](https://github.com/fail2ban/fail2ban/discussions/3769))

```ini
[DEFAULT]
bantime = 1h
bantime.increment = true
bantime.factor = 2
bantime.maxtime = 1w
```

If using recidive jail, **the same `ignoreip` list applies** — operator IPs are safe.

### What NOT to Do

| Anti-Pattern | Why |
|-------------|-----|
| Whitelist entire `100.64.0.0/10` | Permits any Tailscale node (possibly including non-admin nodes) to bypass SSH auth protection |
| Whitelist `172.16.0.0/12` or `10.0.0.0/8` | Permits all internal/Docker traffic |
| Use `chain = DOCKER-USER` for SSH jail | SSH runs on host, not Docker — INPUT is correct |
| Edit `jail.conf` directly | Package updates overwrite changes |
| Use `[default]` instead of `[DEFAULT]` | Case-sensitive — fails silently |
| Restart fail2ban when runtime commands work | `addignoreip` and `reload` avoid service disruption |
| Fail SSH from your own IP for testing | Risk of actual lockout if ignoreip has a configuration error |

---

## 6. Recovery If Locked Out

### If You Have a Second SSH Session (or Tailscale is Working)

```bash
# Unban from a specific jail:
sudo fail2ban-client set sshd unbanip <YOUR_IP>

# Or unban from ALL jails at once (v0.10+):
sudo fail2ban-client unban <YOUR_IP>

# Then add to ignoreip:
sudo fail2ban-client set sshd addignoreip <YOUR_IP>
```

**Source**: [`fail2ban-client.1` manpage](https://github.com/fail2ban/fail2ban/blob/master/man/fail2ban-client.1)

### If Locked Out Completely (No Working Session)

You need **out-of-band access**:

1. **VPS Console / IPMI** — Log in via provider's web console (DigitalOcean, Linode, Hetzner, etc.)
2. **Recovery Mode** — Many VPS providers offer rescue/recovery mode with root filesystem access
3. **Snapshot Rollback** — Restore from a pre-fail2ban snapshot if available

Once in via OOB:

```bash
# Stop fail2ban completely:
sudo systemctl stop fail2ban

# Or delete the ban from UFW:
sudo ufw status numbered   # Find the offending rule number
sudo ufw delete <NUMBER>   # Remove it

# Fix the config to prevent re-lockout:
# Edit /etc/fail2ban/jail.local and ensure correct ignoreip

# Restart fail2ban:
sudo systemctl start fail2ban
```

### Emergency Script (Stage on VPS Before Enabling)

Create `/usr/local/bin/fail2ban-emergency-unban.sh` **before** enabling fail2ban:

```bash
#!/bin/bash
# Emergency unban for operator IPs
# Run this via OOB console if locked out
OPERATOR_IPS=(
  "YOUR_SSH_IP_HERE"       # Replace with actual
  "YOUR_TAILSCALE_IP_HERE" # Replace with actual
)

for ip in "${OPERATOR_IPS[@]}"; do
  echo "Unbanning $ip from all jails..."
  sudo fail2ban-client unban "$ip" 2>/dev/null || true
done

# Also remove from UFW directly as fallback
for ip in "${OPERATOR_IPS[@]}"; do
  sudo ufw delete deny from "$ip" 2>/dev/null || true
done

echo "Done. Attempt SSH connection again."
```

---

## 7. Operator-Protective Checklist

### Pre-Enable Phase (Must Complete Before Starting fail2ban)

- [ ] **Discover operator's current SSH source IP**:
  ```bash
  echo $SSH_CONNECTION | awk '{print $1}'
  # or
  who -m | awk '{print $NF}'
  ```
- [ ] **Discover VPS Tailscale IP**:
  ```bash
  tailscale ip -4
  ```
- [ ] **Discover operator client Tailscale IP** (from client machine):
  ```bash
  tailscale ip -4
  # Or from VPS: tailscale status | grep <client-name>
  ```
- [ ] **If any IP unknown** → BLOCK. Do not enable fail2ban until all three are known. The config script must require explicit input or infer from `tailscale status` + `$SSH_CONNECTION`.
- [ ] **Write jail.local** with correct `ignoreip`:
  ```ini
  [DEFAULT]
  ignoreip = 127.0.0.1/8 ::1 <SSH_IP> <VPS_TS_IP> <CLIENT_TS_IP>
  banaction = ufw
  bantime = 1h
  maxretry = 5
  findtime = 10m
  
  [sshd]
  enabled = true
  port = ssh
  filter = sshd
  logpath = /var/log/auth.log
  ```
- [ ] **Verify ignoreip is loaded**:
  ```bash
  sudo fail2ban-client -d | grep ignoreip
  ```

### Verification Phase

- [ ] **Start fail2ban**:
  ```bash
  sudo systemctl start fail2ban
  sudo systemctl enable fail2ban
  ```
- [ ] **Confirm service is healthy**:
  ```bash
  sudo fail2ban-client status
  sudo systemctl status fail2ban
  ```
- [ ] **Verify ignoreip at runtime**:
  ```bash
  sudo fail2ban-client get sshd ignoreip
  # Must contain all configured IPs
  ```
- [ ] **Test ban with TEST-NET IP** (`198.51.100.99` or similar):
  ```bash
  sudo fail2ban-client set sshd banip 198.51.100.99
  # Verify: sudo fail2ban-client status sshd → must show 198.51.100.99
  # Verify: sudo ufw status numbered → must show DENY for 198.51.100.99
  ```
- [ ] **Confirm operator IP is NOT banned**:
  ```bash
  sudo fail2ban-client status sshd | grep <OPERATOR_IP>
  # Must not show operator IP
  ```
- [ ] **Unban TEST-NET IP**:
  ```bash
  sudo fail2ban-client set sshd unbanip 198.51.100.99
  ```
- [ ] **Verify operator can still SSH** (open a new SSH session window to confirm)
- [ ] **Verify UFW is enabled**:
  ```bash
  sudo ufw status | grep -i active
  ```

### Post-Enable Monitoring

- [ ] **Monitor fail2ban logs for first 24 hours**:
  ```bash
  sudo tail -f /var/log/fail2ban.log
  ```
- [ ] **Check for unexpected bans** (especially of whitelisted IPs):
  ```bash
  sudo fail2ban-client status sshd
  ```
- [ ] **Verify no Docker containers are affected** (if applicable):
  ```bash
  docker ps
  # Check that containers are still accessible
  ```

### Emergency Preparedness

- [ ] **Stage emergency unban script** at `/usr/local/bin/fail2ban-emergency-unban.sh`
- [ ] **Verify VPS provider console access** (can log in via web console)
- [ ] **Document provider's recovery/rescue mode** procedure
- [ ] **Keep a second SSH session alive** during initial fail2ban enablement — do NOT close it until you've confirmed the new session works

---

## 8. References

### Official fail2ban Documentation

| Resource | Link |
|----------|------|
| `jail.conf.5` manpage (full spec) | https://github.com/fail2ban/fail2ban/blob/master/man/jail.conf.5 |
| `jail.conf` default config | https://github.com/fail2ban/fail2ban/blob/master/config/jail.conf |
| `fail2ban-client.1` manpage | https://github.com/fail2ban/fail2ban/blob/master/man/fail2ban-client.1 |
| `ufw.conf` action definition | https://github.com/fail2ban/fail2ban/blob/master/config/action.d/ufw.conf |
| `recidive.conf` filter | https://github.com/fail2ban/fail2ban/blob/master/config/filter.d/recidive.conf |
| Fail2Ban + Docker Wiki | https://github.com/fail2ban/fail2ban/wiki/Fail2Ban-and-Docker |
| How to test standalone instance | https://github.com/fail2ban/fail2ban/wiki/How-to-test-newer-fail2ban-version-resp.-use-fail2ban-standalone-instance |

### Community / Best-Practice References

| Topic | Link |
|-------|------|
| Dynamic whitelist (ignoreip file/command) | https://github.com/fail2ban/fail2ban/discussions/3615 |
| Case-sensitive section names (issue #2633) | https://github.com/fail2ban/fail2ban/issues/2633 |
| Manual ban bypasses ignoreip (discussion #4060) | https://github.com/fail2ban/fail2ban/discussions/4060 |
| Incremental bantime + recidive (discussion #3769) | https://github.com/fail2ban/fail2ban/discussions/3769 |
| UFW integration guide | https://www.virtua.cloud/learn/en/tutorials/fail2ban-setup-linux-vps |
| Docker + fail2ban chain selection | https://github.com/fail2ban/fail2ban/wiki/Fail2Ban-and-Docker |
| Docker-USER chain for containers | https://github.com/crazy-max/docker-fail2ban |

### Tailscale References

| Resource | Link |
|----------|------|
| Tailscale Reserved IP Addresses | https://tailscale.com/docs/reference/reserved-ip-addresses |
| Tailscale CGNAT conflicts | https://tailscale.com/docs/reference/troubleshooting/network-configuration/cgnat-conflicts |
| Tailscale IP addresses explained | https://tailscale.com/docs/concepts/tailscale-ip-addresses |

### Standards

| Standard | Description |
|----------|-------------|
| RFC 6598 | CGNAT shared address space (`100.64.0.0/10`) |
| RFC 5737 | TEST-NET ranges for documentation (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) |

---

*End of report.*

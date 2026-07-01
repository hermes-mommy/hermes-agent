# P25 Network & Service Plan Research

> **Research Date**: 2026-06-26
> **Purpose**: Tailscale + firewall patterns for 9Router VPS migration (Tailscale-only exposure)
> **Sources**: Tailscale official docs, GitHub issues, community patterns

---

## Table of Contents

1. [Tailscale Installation on Ubuntu/Debian](#1-tailscale-installation-on-ubuntudebian)
2. [Critical Pitfall: Tailscale Bypasses UFW by Default](#2-critical-pitfall-tailscale-bypasses-ufw-by-default)
3. [Firewall Strategy: Add-Only Rules (Never Flush)](#3-firewall-strategy-add-only-rules-never-flush)
4. [Service Binding Options](#4-service-binding-options)
5. [Tailscale MagicDNS & Stable Hostnames](#5-tailscale-magicdns--stable-hostnames)
6. [Tailscale ACLs for Port Restriction](#6-tailscale-acls-for-port-restriction)
7. [Tailscale Serve (Tailnet-Only, NOT Funnel)](#7-tailscale-serve-tailnet-only-not-funnel)
8. [Verification Commands](#8-verification-commands)
9. [Common Pitfalls](#9-common-pitfalls)
10. [Recommended Execution Sequence](#10-recommended-execution-sequence)

---

## 1. Tailscale Installation on Ubuntu/Debian

### Install

```bash
# One-line install script (official)
curl -fsSL https://tailscale.com/install.sh | sh
```

### Enable and start the service

```bash
sudo systemctl enable --now tailscaled
```

### Authenticate and connect to tailnet

```bash
sudo tailscale up
```

This opens a browser URL for authentication. On a headless VPS, copy the URL and open it on your local machine.

### Get Tailscale IP

```bash
# IPv4
tailscale ip -4
# Output: 100.x.y.z

# IPv6 (if enabled)
tailscale ip -6
```

### Set a custom hostname (optional, recommended)

```bash
sudo tailscale up --hostname=vps-9router
```

This sets the MagicDNS name to `vps-9router.<tailnet-name>.ts.net`.

### Disable key expiry (recommended for servers)

```bash
tailscale up --accept-routes
# Then disable key expiry via admin console:
# https://login.tailscale.com/admin/machines → machine → "Disable key expiry"
```

**Source**: [Tailscale Install Docs](https://tailscale.com/docs/install/linux) | [Tailscale UFW Guide](https://tailscale.com/docs/how-to/secure-ubuntu-server-with-ufw)

---

## 2. Critical Pitfall: Tailscale Bypasses UFW by Default

> **THIS IS THE MOST IMPORTANT SECTION. READ BEFORE TOUCHING ANY FIREWALL.**

### The Problem

Since ~August 2023, Tailscale **automatically adds an iptables/nftables rule** that allows ALL inbound traffic on the `tailscale0` interface. This rule is **invisible to `ufw status`** and bypasses UFW entirely.

This means:
- Even with `ufw default deny incoming`, traffic on `tailscale0` is **always allowed**
- You **cannot use UFW alone** to restrict which ports are open on Tailscale
- This is by design (GitHub issue [#11717](https://github.com/tailscale/tailscale/issues/11717))

**Source**: [GitHub Issue #11717](https://github.com/tailscale/tailscale/issues/11717)

### The Solution: `--netfilter-mode`

Use `--netfilter-mode` when running `tailscale up`:

| Mode | Behavior | When to Use |
|------|----------|-------------|
| `on` (default) | Tailscale manages ALL its own iptables rules, including accept-all on tailscale0 | Simple setups where you don't need per-port control on Tailscale |
| `nodivert` | Tailscale creates its sub-chains (`ts-input`, `ts-forward`) but does NOT hook them into the main `INPUT` chain | **RECOMMENDED for our use case** — we manage our own iptables rules for tailscale0 |
| `off` | Tailscale manages NOTHING in iptables | When you want full manual control of all Tailscale-related firewall rules |

### For P25: Use `nodivert`

```bash
# First time setup — prevents Tailscale from auto-allowing all tailscale0 traffic
sudo tailscale up --netfilter-mode=nodivert
```

With `nodivert`, Tailscale creates its chains but doesn't call them from `INPUT`. You then write your own iptables rules to control what enters on `tailscale0`.

> **WARNING**: With `nodivert` or `off`, you are responsible for allowing WireGuard UDP port 41641 traffic for Tailscale to function. The `ts-input` chain normally handles this.

**Source**: [Tailscale `tailscale up` docs](https://tailscale.com/kb/1241/tailscale-up) | [Tailscale Firewall Mode](https://tailscale.com/docs/features/firewall-mode)

---

## 3. Firewall Strategy: Add-Only Rules (Never Flush)

### Design Principles

1. **NEVER `iptables -F`** (flush) — this nukes ALL rules including SSH
2. **NEVER `ufw reset`** — this flushes everything
3. **ONLY use `-A` (append)** or `-I` (insert) to add rules
4. **ALWAYS verify SSH connectivity after any firewall change**
5. **Use `-C` (check) before `-D` (delete)** to avoid accidental removal

### Recommended iptables Rules (add-only)

#### 3a. Allow Tailscale WireGuard traffic (essential)

```bash
# Allow WireGuard UDP on port 41641 (Tailscale's default)
sudo iptables -A INPUT -p udp --dport 41641 -j ACCEPT
```

#### 3b. Allow traffic on Tailscale interface for 9Router port

```bash
# Allow 9Router port (e.g., 8080) ONLY on tailscale0 interface
sudo iptables -A INPUT -i tailscale0 -p tcp --dport 8080 -j ACCEPT
```

#### 3c. Block 9Router port on all other interfaces

```bash
# Block 9Router port on public interface (eth0 / ens3 / etc.)
sudo iptables -A INPUT -i eth0 -p tcp --dport 8080 -j DROP
```

> **NOTE**: Replace `eth0` with your actual public interface name. Check with `ip route get 1.1.1.1` or `ip addr`.

#### 3d. Verify SSH is NOT touched (do NOT add rules for port 22)

```bash
# Check existing SSH rules — they should remain untouched
sudo iptables -L INPUT -n --line-numbers | grep 22
```

#### 3e. Make rules persistent across reboots

```bash
# Install iptables-persistent
sudo apt-get install -y iptables-persistent

# Save current rules
sudo netfilter-persistent save
# This writes to /etc/iptables/rules.v4 and /etc/iptables/rules.v6
```

**Source**: [iptables Essentials](https://www.digitalocean.com/community/tutorials/iptables-essentials-common-firewall-rules-and-commands) | [AskUbuntu: Making iptables permanent](https://askubuntu.com/questions/66890/how-can-i-make-a-specific-set-of-iptables-rules-permanent)

### Alternative: UFW-based approach (simpler but less granular)

If you prefer UFW and use `--netfilter-mode=off`:

```bash
# Step 1: Start Tailscale with no netfilter management
sudo tailscale up --netfilter-mode=off

# Step 2: Set defaults
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Step 3: Allow SSH on public interface (KEEP THIS)
sudo ufw allow 22/tcp comment 'SSH public access'

# Step 4: Allow Tailscale WireGuard
sudo ufw allow 41641/udp comment 'Tailscale WireGuard'

# Step 5: Allow 9Router ONLY on Tailscale interface
sudo ufw allow in on tailscale0 to any port 8080 proto tcp comment '9Router via Tailscale only'

# Step 6: Enable UFW
sudo ufw enable

# Step 7: Verify
sudo ufw status verbose
```

> **CRITICAL**: If using UFW with `--netfilter-mode=off`, you MUST manually allow WireGuard (41641/udp) and Tailscale DERP (TCP 443, TCP 80 from Tailscale's DERP servers).

### Approach Recommendation for P25

**Use iptables directly with `--netfilter-mode=nodivert`** for maximum control:

1. Tailscale creates its chains but doesn't auto-hook them
2. You write explicit iptables `-A` rules for tailscale0
3. SSH remains on its existing rules (public interface)
4. 9Router port is restricted to tailscale0 only
5. No UFW involved = no wrapper confusion

---

## 4. Service Binding Options

### Option A: Bind 9Router to Tailscale IP only (BEST — defense in depth)

The strongest approach: the service itself only listens on the Tailscale IP.

```bash
# Get Tailscale IP
TS_IP=$(tailscale ip -4)
echo "Tailscale IP: $TS_IP"

# Example: if 9Router is a Node.js/Python/etc. service
# Configure it to listen on TS_IP instead of 0.0.0.0

# For a generic systemd service, use Environment:
# In the [Service] section of the systemd unit:
# Environment="LISTEN_ADDR=100.x.y.z"
```

**How to find and configure for common stacks:**

| Stack | How to bind to specific IP |
|-------|---------------------------|
| Node.js (Express) | `app.listen(8080, '100.x.y.z')` |
| Python (uvicorn) | `uvicorn main:app --host 100.x.y.z --port 8080` |
| Go | `net.Listen("tcp", "100.x.y.z:8080")` |
| Nginx | `listen 100.x.y.z:8080;` in server block |
| Generic | Use `socat` or `systemd` socket activation |

### Option B: Systemd service with network dependency

```ini
# /etc/systemd/system/nine-router.service
[Unit]
Description=9Router Service
After=network-online.target tailscaled.service
Wants=network-online.target
Requires=tailscaled.service

[Service]
Type=simple
ExecStart=/opt/nine-router/start.sh
Environment="LISTEN_IP=100.x.y.z"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable nine-router.service
sudo systemctl start nine-router.service
```

### Option C: systemd socket activation (most robust)

Use systemd socket activation so the service doesn't need to know the Tailscale IP at build time — systemd passes the socket.

```ini
# /etc/systemd/system/nine-router.socket
[Unit]
Description=9Router Socket

[Socket]
ListenStream=100.x.y.z:8080
BindIPv6Only=ipv4

[Install]
WantedBy=sockets.target
```

### Option D: Firewall-only restriction (defense in depth, service binds 0.0.0.0)

If 9Router must bind to 0.0.0.0 (e.g., it doesn't support binding to a specific IP), use firewall rules from Section 3 to restrict access to tailscale0 only.

**Recommendation**: **Option A + Option D combined** (application-level binding + firewall rules = defense in depth).

---

## 5. Tailscale MagicDNS & Stable Hostnames

### How MagicDNS Works

- MagicDNS is **enabled by default** on all tailnets
- Each device gets an automatic DNS name: `<hostname>.<tailnet-name>.ts.net`
- Example: `vps-9router.my-tailnet.ts.net`
- DNS resolves to the device's Tailscale IP (100.x.y.z)
- Uses `100.100.100.100` (Quad100) as the DNS resolver within the tailnet

### Set a stable hostname

```bash
# During setup
sudo tailscale up --hostname=vps-9router

# Or change later
sudo tailscale set --hostname=vps-9router
```

### Check your MagicDNS name

```bash
# From the machine itself
tailscale status --json | grep -i dns
# Or
tailscale status
```

### Verify MagicDNS resolution (from another Tailscale machine)

```bash
# Should resolve to 100.x.y.z
nslookup vps-9router.<tailnet-name>.ts.net

# Or just ping
ping vps-9router.<tailnet-name>.ts.net
```

### Access 9Router via MagicDNS

Once configured, you can access 9Router at:
```
http://vps-9router.<tailnet-name>.ts.net:8080
```

### Disable key expiry for the server

MagicDNS names stay stable as long as the machine stays authenticated. Disable key expiry for servers to prevent lockout:

1. Go to https://login.tailscale.com/admin/machines
2. Find the machine
3. Click `...` → **Disable key expiry**

**Source**: [Tailscale DNS Docs](https://tailscale.com/kb/1054/dns) | [MagicDNS](https://tailscale.com/kb/1081/magicdns)

---

## 6. Tailscale ACLs for Port Restriction

### Default: Allow All

By default, Tailscale allows all devices to access all other devices on all ports. For tighter security, define ACLs in the admin console.

### Restrict 9Router port to specific devices

```jsonc
// In Tailscale Admin Console → Access Controls
{
  "acls": [
    // Allow all members to access their own devices
    {
      "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["autogroup:self:*"]
    },
    // Allow specific devices/users to access 9Router port on the VPS
    {
      "action": "accept",
      "src": ["faiz@example.com"],  // or use tags: "tag:faiz-devices"
      "dst": ["tag:vps-9router:8080"]
    }
  ],
  "tagOwners": {
    "tag:vps-9router": ["faiz@example.com"],
    "tag:faiz-devices": ["faiz@example.com"]
  }
}
```

### Tag the VPS during setup

```bash
sudo tailscale up --advertise-tags=tag:vps-9router --hostname=vps-9router
```

> **NOTE**: ACLs operate at the Tailscale network layer (WireGuard). Even without iptables rules, ACLs prevent unauthorized devices from reaching the service. This is an additional security layer.

**Source**: [Tailscale ACL Examples](https://tailscale.com/docs/reference/examples/acls) | [Grants Syntax](https://tailscale.com/docs/reference/syntax/grants)

---

## 7. Tailscale Serve (Tailnet-Only, NOT Funnel)

### What is Tailscale Serve?

Tailscale Serve proxies a local service to your tailnet with an HTTPS URL. It's accessible ONLY to tailnet devices (NOT the public internet — that's Funnel).

### Setup

```bash
# Enable HTTPS in tailnet (required for Serve)
# Go to: https://login.tailscale.com/admin/dns → Enable HTTPS

# Serve a local port
sudo tailscale serve 8080

# Output:
# Available within your tailnet:
# https://vps-9router.my-tailnet.ts.net
# |-- / proxy http://127.0.0.1:8080
```

### Why this might be useful for P25

- Provides HTTPS automatically (Let's Encrypt cert for the tailnet DNS name)
- Adds identity headers (`Tailscale-User-Login`, `Tailscale-User-Name`)
- Service only needs to listen on `127.0.0.1` (most secure)
- ACLs still apply

### Why we might NOT use this

- 9Router may already handle its own TLS
- Adds a reverse proxy layer (complexity)
- Serve requires HTTPS to be enabled on the tailnet
- If 9Router needs raw TCP (not HTTP), Serve HTTP mode won't work (but TCP forwarder mode exists)

### TCP Forwarder mode (for non-HTTP services)

```bash
# For raw TCP forwarding
sudo tailscale serve --tcp 8080 tcp://localhost:8080
```

### Funnel vs Serve

| Feature | Serve | Funnel |
|---------|-------|--------|
| Accessible from | Tailnet only | Public internet |
| Requires HTTPS | Yes | Yes |
| Identity headers | Yes | No |
| Use case | Internal services | Public-facing services |
| **For P25** | **✅ Use this** | **❌ Don't use this** |

**Source**: [Tailscale Serve Docs](https://tailscale.com/docs/features/tailscale-serve)

---

## 8. Verification Commands

### 8a. Verify Tailscale is running and connected

```bash
# Check service status
sudo systemctl status tailscaled

# Check Tailscale connection status
tailscale status

# Check Tailscale IP
tailscale ip -4

# Check connectivity to another machine
tailsping <other-machine-name>
# or
tailscale ping <other-machine-ip>
```

### 8b. Verify SSH is NOT disrupted

```bash
# From your local machine, try SSH via public IP
ssh user@<vps-public-ip>

# If this works, SSH is intact
# If this fails, IMMEDIATELY check firewall:
# (access via VPS console if available)
sudo iptables -L INPUT -n --line-numbers
```

### 8c. Verify public internet CANNOT access 9Router

```bash
# From a machine NOT on Tailscale (or from the VPS itself via public IP)
curl -v http://<vps-public-ip>:8080
# Expected: Connection timed out or Connection refused

# From the VPS itself, check the rules are in place
sudo iptables -L INPUT -n -v | grep 8080
# Should show: DROP rule on eth0 for port 8080
# And: ACCEPT rule on tailscale0 for port 8080

# Nmap from external machine (if available)
nmap -p 8080 <vps-public-ip>
# Expected: filtered or closed
```

### 8d. Verify Tailscale CAN access 9Router

```bash
# From a machine ON Tailscale
curl -v http://<tailscale-ip>:8080
# Expected: 9Router response

# Or via MagicDNS
curl -v http://vps-9router.<tailnet-name>.ts.net:8080
# Expected: 9Router response

# Check which Tailscale machines can reach it (based on ACLs)
tailscale ping <vps-tailscale-ip>
```

### 8e. Verify firewall rules are correct

```bash
# Show all INPUT rules with line numbers
sudo iptables -L INPUT -n --line-numbers

# Show rules for specific interface
sudo iptables -L INPUT -n -v -i tailscale0

# Show rules for specific port
sudo iptables -L INPUT -n | grep 8080

# Check if rules are persistent
sudo cat /etc/iptables/rules.v4 | grep 8080
```

### 8f. Verify Tailscale connectivity type

```bash
# Check if connection is direct or via DERP relay
tailscale ping <other-machine>
# "pong from <machine> via <ip>:<port>" = direct
# "pong from <machine> via DERP(<relay>)" = relayed
```

### 8g. Verify netfilter mode

```bash
# Check what mode Tailscale is using
journalctl -ru tailscaled | grep -i "netfilter\|router:"
# Should show: "router: using nftables" or "router: using iptables"
# And the netfilter mode you specified
```

---

## 9. Common Pitfalls

### Pitfall 1: Tailscale auto-allow-all bypasses your firewall

**Symptom**: Port 8080 is accessible from any Tailscale machine even though you set `ufw deny`.

**Cause**: Default `--netfilter-mode=on` adds accept-all rule on tailscale0.

**Fix**: Use `--netfilter-mode=nodivert` and manage your own iptables rules.

### Pitfall 2: Flushing iptables kills SSH

**Symptom**: `iptables -F` or `ufw reset` drops all connections including SSH.

**Fix**: NEVER flush. Use `-A` (append) only. If you must flush, do it inside a script that also restores SSH rules:

```bash
# DANGEROUS — only if absolutely necessary
# Run inside: nohup bash -c 'iptables -F && iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT && iptables -A INPUT -p tcp --dport 22 -j ACCEPT'
```

### Pitfall 3: Wrong interface name

**Symptom**: Rules for `eth0` don't work because the interface is named `ens3`, `enp0s3`, etc.

**Fix**: Check the actual interface name:
```bash
ip route get 1.1.1.1
# Shows which interface is used for public traffic
ip addr
# Lists all interfaces
```

### Pitfall 4: Tailscale interface name varies

**Symptom**: Interface might be `tailscale0`, `ts0`, or something else.

**Fix**: Check:
```bash
ip addr | grep tailscale
# or
tailscale status --json | grep -i tap
```

On modern Linux, Tailscale typically creates `tailscale0`. With userspace networking, there's no kernel interface.

### Pitfall 5: iptables rules not persistent after reboot

**Symptom**: Rules work fine but disappear after reboot.

**Fix**: Install and use `iptables-persistent`:
```bash
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

### Pitfall 6: Tailscale key expires, machine drops off tailnet

**Symptom**: Machine disappears from tailnet, MagicDNS stops working.

**Fix**: Disable key expiry for servers:
1. Admin console → Machines → `...` → Disable key expiry
2. Or use auth keys for re-authentication

### Pitfall 7: DERP relay latency

**Symptom**: Connections work but are slow (relayed through DERP).

**Fix**: Ensure UDP port 41641 is open on the VPS firewall:
```bash
sudo iptables -A INPUT -p udp --dport 41641 -j ACCEPT
```

### Pitfall 8: nftables vs iptables conflict

**Symptom**: Rules don't apply or behave unexpectedly.

**Cause**: Ubuntu 22.04+ uses nftables as the backend for iptables commands. Tailscale may use either.

**Fix**: Set the firewall mode explicitly:
```bash
# In /etc/default/tailscaled
TS_DEBUG_FIREWALL_MODE=auto
```

### Pitfall 9: Service binds to 0.0.0.0 and Tailscale IP changes

**Symptom**: After Tailscale reconnects, the IP might change (rare, but possible if key expires).

**Fix**: Use `tailscale ip -4` dynamically in startup scripts, or bind to 0.0.0.0 with firewall restriction.

---

## 10. Recommended Execution Sequence

### Phase 1: Install Tailscale (safe, no firewall changes)

```bash
# 1. Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# 2. Start and authenticate
sudo tailscale up --hostname=vps-9router --netfilter-mode=nodivert

# 3. Disable key expiry via admin console

# 4. Get Tailscale IP
tailscale ip -4
# Note this IP: 100.x.y.z
```

### Phase 2: Verify Tailscale works (before touching firewall)

```bash
# 5. From another Tailscale machine, verify connectivity
tailscale ping vps-9router

# 6. Verify SSH still works on public IP
ssh user@<vps-public-ip>
```

### Phase 3: Add firewall rules (add-only)

```bash
# 7. Allow Tailscale WireGuard
sudo iptables -A INPUT -p udp --dport 41641 -j ACCEPT

# 8. Allow 9Router port on Tailscale interface ONLY
sudo iptables -A INPUT -i tailscale0 -p tcp --dport 8080 -j ACCEPT

# 9. Block 9Router port on public interface
sudo iptables -A INPUT -i eth0 -p tcp --dport 8080 -j DROP

# 10. Save rules for persistence
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

### Phase 4: Verify everything

```bash
# 11. Verify SSH on public IP still works
ssh user@<vps-public-ip>

# 12. Verify 9Router NOT accessible on public IP
curl --connect-timeout 5 http://<vps-public-ip>:8080  # Should fail

# 13. Verify 9Router IS accessible via Tailscale
curl http://100.x.y.z:8080  # From a Tailscale machine

# 14. Verify MagicDNS
curl http://vps-9router.<tailnet>.ts.net:8080
```

### Phase 5: Configure 9Router service

```bash
# 15. Bind 9Router to Tailscale IP (defense in depth)
# Configure in 9Router's config or systemd unit

# 16. Enable and start 9Router
sudo systemctl enable nine-router.service
sudo systemctl start nine-router.service

# 17. Verify service is running
sudo systemctl status nine-router.service
curl http://100.x.y.z:8080
```

### Phase 6: Set up Tailscale ACLs (optional, recommended)

```jsonc
// In Tailscale Admin Console → Access Controls
{
  "acls": [
    {
      "action": "accept",
      "src": ["faiz@example.com"],
      "dst": ["tag:vps-9router:8080"]
    }
  ],
  "tagOwners": {
    "tag:vps-9router": ["faiz@example.com"]
  }
}
```

```bash
# Tag the VPS
sudo tailscale up --advertise-tags=tag:vps-9router
```

---

## Summary: Defense in Depth Layers

| Layer | Mechanism | What It Protects Against |
|-------|-----------|------------------------|
| 1. Application | 9Router binds to Tailscale IP only | Direct public IP access |
| 2. Firewall | iptables: ACCEPT on tailscale0, DROP on eth0 for port 8080 | Public interface access even if app misconfigured |
| 3. Tailscale ACLs | Only authorized devices can reach the port | Unauthorized tailnet devices |
| 4. Tailscale auth | WireGuard encryption + device authentication | Network sniffing, unauthorized access |
| 5. MagicDNS | Stable hostname with TLS cert | IP changes, MITM |

All five layers should be in place for production. Layers 1-3 are the minimum.

---

## References

- [Tailscale Install on Linux](https://tailscale.com/docs/install/linux)
- [Tailscale UFW Guide](https://tailscale.com/docs/how-to/secure-ubuntu-server-with-ufw)
- [Tailscale Firewall Docs](https://tailscale.com/docs/integrations/firewalls)
- [Tailscale Firewall Mode](https://tailscale.com/docs/features/firewall-mode)
- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve)
- [Tailscale ACL Examples](https://tailscale.com/docs/reference/examples/acls)
- [Tailscale DNS / MagicDNS](https://tailscale.com/kb/1054/dns)
- [Tailscale `tailscale up` flags](https://tailscale.com/kb/1241/tailscale-up)
- [GitHub Issue #11717: Tailscale bypasses UFW](https://github.com/tailscale/tailscale/issues/11717)
- [iptables Essentials (DigitalOcean)](https://www.digitalocean.com/community/tutorials/iptables-essentials-common-firewall-rules-and-commands)

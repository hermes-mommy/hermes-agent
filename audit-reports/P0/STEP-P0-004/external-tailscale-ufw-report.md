# External Report: Tailscale + UFW Coexistence and Port Allowlist Strategy

**Context:** Guinevere shared VPS (Tailscale IP `100.94.104.22`).  
**Stack:** Ubuntu 24.04, Tailscale, UFW, Docker, nginx (Aizanta on Tailscale IP:80), SSH on port 22.  
**Goal:** Document safe coexistence, prevent lockout, and provide actionable recommendations.  
**Date:** 2026-05-31  
**Status:** Read-only research — no VPS changes performed.

---

## 1. Tailscale Netfilter Modes (How Tailscale Interacts with Firewalls)

Tailscale on Linux integrates with the kernel's netfilter framework via three modes:

| Mode | Description | Effect on UFW |
|---|---|---|
| **`on`** (default) | Tailscale creates its own iptables/nftables rules and ensures they evaluate **before** other rules. Periodically repositions its rules to remain first. | Tailscale inserts ACCEPT rules for `tailscale0` and its UDP port at the top of `INPUT`/`FORWARD` chains. These take priority over UFW's deny rules. |
| **`nodivert`** | Tailscale creates rules but does **not** activate them (no jump rules inserted). You must manually wire them. | Gives the admin full control over rule ordering but requires manual iptables/nftables configuration. |
| **`off`** | Tailscale makes **zero** netfilter changes. You must write all rules yourself. | Full manual management. Rarely needed. |

**Source:** [Tailscale Netfilter Modes](https://tailscale.com/docs/reference/netfilter-modes)

### Key implication for Guinevere VPS

With the default **`on`** mode, Tailscale automatically inserts ACCEPT rules for:
- Inbound traffic on the `tailscale0` interface
- UDP traffic to the Tailscale listening port (default 41641)

This means Tailscale traffic **bypasses UFW's default-deny policy** by design — this is intentional behavior, not a bug. Tailscale's internal ACL system handles authorization instead.

---

## 2. Tailscale + UFW: Official Guidance

### 2.1 What Tailscale Says

Tailscale's official documentation on [using Tailscale with firewalls](https://tailscale.com/docs/integrations/firewalls) states:

> "Tailscale creates its own firewall rules and configures them to be evaluated automatically. This approach lets Tailscale manage its required rules while preserving your ability to add custom rules when needed."

And from Tailscale's [Secure Ubuntu Server with UFW guide](https://tailscale.com/docs/how-to/secure-ubuntu-server-with-ufw):

> Steps to secure Ubuntu with UFW include: setting default deny incoming, allow outgoing, and allowing SSH only over Tailscale.

### 2.2 UFW Rules Historically Recommended by Tailscale (Pre-2024)

Older Tailscale KB articles recommended these manual UFW rules:

```bash
sudo ufw allow in on tailscale0          # Allow all inbound on Tailscale interface
sudo ufw allow 41641/udp                 # Allow Tailscale UDP port
```

### 2.3 Modern Tailscale Behavior (Post-PR #10370, merged Nov 2023)

As of Tailscale v1.56+ on Linux, Tailscale **automatically** inserts netfilter rules to:

1. Accept inbound traffic on `tailscale0` interface
2. Accept UDP traffic to its magicsock port (dynamic, default 41641)

These rules are inserted **at the top of the iptables/nftables chains**, before UFW's rules. This means:

- **`ufw allow in on tailscale0` is no longer necessary** — Tailscale does this automatically
- **`ufw allow 41641/udp` is redundant in most cases** — Tailscale manages this automatically
- UFW's default-deny does not affect Tailscale traffic because the Tailscale ACCEPT rules evaluate first

**Source:** [Tailscale Issue #9084](https://github.com/tailscale/tailscale/issues/9084) — task list confirms both rules are implemented  
**Source:** [Tailscale PR #10370](https://github.com/tailscale/tailscale/pull/10370) — "automates adding and updating firewall rules as magicsock changes what port it listens on"

### 2.4 Caveat: UFW Status Still Shows Tailscale Traffic as "Allowed"

Because of the ordering issue, `ufw status` does **not** reflect the actual filtering state for Tailscale traffic. This is by design but can be confusing. The correct mental model:

- **Tailscale traffic:** Filtered by Tailscale's internal ACLs, not UFW
- **Non-Tailscale traffic:** Filtered by UFW as configured

---

## 3. Port Allowlist Strategy for Shared VPS (Guinevere Context)

### 3.1 Required Services and Ports

| Service | Interface | Port/Protocol | UFW Intent |
|---|---|---|---|
| SSH | `tailscale0` only (or Tailscale IP) | 22/TCP | Allow only over Tailscale |
| SSH | Public interface (e.g., `eth0`) | 22/TCP | **Deny** (lock public SSH) |
| Aizanta (nginx) | `tailscale0` | 80/TCP | Allow over Tailscale |
| Aizanta (nginx) | Public interface | 80/TCP | **Deny** (no public web) |
| Tailscale daemon | All interfaces | 41641/UDP | Left to Tailscale's auto-rules |
| Docker containers | Various (via Docker) | Various | **UFW bypass** — see §4 |

### 3.2 Recommended UFW Ruleset

```bash
# --- Base policy ---
sudo ufw default deny incoming
sudo ufw default allow outgoing

# --- Allow SSH only over Tailscale ---
sudo ufw allow in on tailscale0 to any port 22 proto tcp

# --- Allow Aizanta/nginx only over Tailscale ---
sudo ufw allow in on tailscale0 to any port 80 proto tcp

# --- Optional: explicitly deny SSH on public interface (belt-and-suspenders) ---
# This is technically redundant with default-deny, but serves as documentation
sudo ufw deny in on eth0 to any port 22 proto tcp

# --- Tailscale UDP port (redundant for modern Tailscale, harmless) ---
# sudo ufw allow 41641/udp

# --- Enable UFW ---
sudo ufw enable
```

### 3.3 Critical Lockout Prevention

> **WARNING:** Never enable UFW without first ensuring you have an allow rule for SSH over Tailscale. If you run `ufw enable` with only `default deny incoming` and no Tailscale allow rule while SSH'd in over the public interface, you will be locked out.

**Safe procedure:**
1. Ensure Tailscale is running and connected (`tailscale status`)
2. Add the Tailscale SSH allow rule FIRST
3. Then run `ufw enable`
4. **Keep a second SSH session open** as a safety net
5. Test by disconnecting and reconnecting over Tailscale before closing the safety session

### 3.4 Restricting SSH to Tailscale-Only

From [Tailscale's UFW guide](https://tailscale.com/docs/how-to/secure-ubuntu-server-with-ufw) and community practice ([supun.io](https://supun.io/tailscale-ssh-restrict)):

```bash
# Add the Tailscale-specific SSH rule
sudo ufw allow in on tailscale0 to any port 22

# Remove the generic OpenSSH rule that allows SSH on all interfaces
# (identify the rule number first)
sudo ufw status numbered
sudo ufw delete <RULE_NUMBER>   # Delete the generic OpenSSH rule
```

This ensures SSH is **only** reachable via Tailscale's encrypted mesh — no public SSH exposure.

---

## 4. Docker + UFW: The Critical Incompatibility

### 4.1 The Problem

Docker bypasses UFW **by design**. As documented in [Docker's official docs](https://docs.docker.com/engine/network/packet-filtering-firewalls/):

> "Docker and ufw use firewall rules in ways that make them incompatible with each other. When you publish a container's ports using Docker, traffic to and from that container gets diverted before it goes through the ufw firewall settings."

**Root cause:** Docker inserts rules in the `nat` table (PREROUTING chain) and the `filter` table (FORWARD chain). These evaluate **before** UFW's `INPUT` chain rules. Published container ports become reachable even if UFW denies them.

### 4.2 Impact on Guinevere Shared VPS

Any Docker containers with published ports (`-p` or `ports:` in compose) will be:
- Accessible on all public interfaces regardless of UFW rules
- A potential attack surface if not properly secured

**This is the most significant security concern** for the shared VPS.

### 4.3 Proven Fixes

#### Fix A: DOCKER-USER Chain Rules (Ubuntu 24.04 Compatible)

Docker provides the `DOCKER-USER` chain specifically for operator-defined rules, evaluated **before** Docker's own forwarding logic. The [chaifeng/ufw-docker](https://github.com/chaifeng/ufw-docker) project (6.4k stars) provides a well-tested solution:

1. **Install ufw-docker helper (optional but recommended):**
   ```bash
   sudo wget -O /usr/local/bin/ufw-docker \
     https://github.com/chaifeng/ufw-docker/raw/master/ufw-docker
   sudo chmod +x /usr/local/bin/ufw-docker
   sudo ufw-docker install
   ```

2. **Or add rules directly to `/etc/ufw/after.rules`:**
   ```
   # BEGIN UFW AND DOCKER
   *filter
   :ufw-user-forward - [0:0]
   :ufw-docker-logging-deny - [0:0]
   :DOCKER-USER - [0:0]
   -A DOCKER-USER -j ufw-user-forward

   -A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
   -A DOCKER-USER -m conntrack --ctstate INVALID -j DROP
   -A DOCKER-USER -i docker0 -o docker0 -j ACCEPT

   -A DOCKER-USER -j RETURN -s 10.0.0.0/8
   -A DOCKER-USER -j RETURN -s 172.16.0.0/12
   -A DOCKER-USER -j RETURN -s 192.168.0.0/16

   -A DOCKER-USER -j ufw-docker-logging-deny -m conntrack --ctstate NEW -d 10.0.0.0/8
   -A DOCKER-USER -j ufw-docker-logging-deny -m conntrack --ctstate NEW -d 172.16.0.0/12
   -A DOCKER-USER -j ufw-docker-logging-deny -m conntrack --ctstate NEW -d 192.168.0.0/16

   -A DOCKER-USER -j RETURN

   -A ufw-docker-logging-deny -m limit --limit 3/min --limit-burst 10 -j LOG --log-prefix "[UFW DOCKER BLOCK] "
   -A ufw-docker-logging-deny -j DROP
   COMMIT
   # END UFW AND DOCKER
   ```
   Then: `sudo systemctl restart ufw` (or reboot if rules don't take effect).

3. **Allow specific container ports through UFW:**
   ```bash
   sudo ufw route allow proto tcp from any to any port 80   # container port 80, not host port
   ```

#### Fix B: Bind to localhost (Simpler, Less Flexible)

```yaml
# In docker-compose.yml — bind to localhost only
ports:
  - "127.0.0.1:8080:80"    # Not accessible from outside
  - "0.0.0.0:443:443"      # Accessible from outside (UFW bypassed)
```

#### Fix C: Cloud-Level Firewall (Defense in Depth)

Use the VPS provider's firewall/security group as the **first line of defense**. This operates outside the VPS operating system and cannot be bypassed by Docker.

### 4.4 Recommendations for Guinevere

| Approach | Pros | Cons | Recommended? |
|---|---|---|---|
| DOCKER-USER chain rules | UFW controls Docker; no docker config changes | Requires setup; reboot may be needed | ✅ **Primary** |
| Localhost binding | Simple; effective for internal services | Breaks external container access | ✅ **For internal-only services** |
| Cloud firewall | Cannot be bypassed; independent of OS | Requires provider console access | ✅ **Defense in depth** |
| `--iptables=false` | UFW fully controls firewall | Breaks container networking | ❌ **Avoid** |

---

## 5. Tailscale UDP Port 41641 Details

### 5.1 Purpose

Tailscale's direct WireGuard tunnels use UDP with source port **41641** by default. This port is used for:
- **Hole punching:** Establishing peer-to-peer connections through NATs
- **Direct connections:** Bypassing DERP relay servers for lower latency
- **NAT traversal:** Maintaining NAT mappings

**Source:** [Tailscale Firewall Ports FAQ](https://tailscale.com/docs/reference/faq/firewall-ports)

### 5.2 Modern Tailscale Behavior

As of [PR #10370](https://github.com/tailscale/tailscale/pull/10370) (merged Nov 2023), Tailscale automatically adds iptables/nftables rules to accept UDP traffic on its magic socket port. This means:

- **On most Ubuntu 24.04 setups with default Tailscale**, UDP 41641 is automatically allowed
- Manual `ufw allow 41641/udp` is redundant but harmless
- If Tailscale changes its port (via `--port` flag), it auto-updates the firewall rule

### 5.3 When You Still Need Manual Rules

- Using `netfilterMode: off` or `nodivert`
- Running an older Tailscale version (pre-1.56)
- Using a **non-Ubuntu firewall** that doesn't integrate with netfilter (e.g., cloud security groups, hardware firewalls)

---

## 6. Public Interface vs Tailscale Interface Strategy

### 6.1 Principle: Zero Public Admin Surfaces (ADR-019 Alignment)

Guinevere's target architecture (ADR-019 — VPN mesh) aims for **zero public admin surfaces**. The recommended approach:

| Surface | Public (eth0) | Tailscale (tailscale0) |
|---|---|---|
| SSH (22) | 🔴 DENY | ✅ ALLOW |
| Aizanta/nginx (80/443) | 🔴 DENY | ✅ ALLOW |
| Tailscale (41641/UDP) | Auto-managed by Tailscale | Auto-managed by Tailscale |
| Docker published ports | 🔴 DENY via DOCKER-USER fix | Conditional |
| Monitoring (Prometheus/Grafana) | 🔴 DENY | ✅ ALLOW when ready |
| Database (PostgreSQL/Redis) | 🔴 DENY | ✅ ALLOW when ready |

### 6.2 UFW Rule Ordering

UFW evaluates rules in this order:
1. `before.rules` (system rules)
2. `user.rules` (user-added rules, processed in order)
3. `after.rules` (post-processing rules, including DOCKER-USER fix)

Tailscale's auto-rules are inserted at the very top of the INPUT/FORWARD chains, so they evaluate **before** any UFW rules.

### 6.3 Verification Commands

```bash
# Check UFW status
sudo ufw status verbose

# Verify Tailscale is running and connected
tailscale status

# Check which firewall rules Tailscale has added
sudo iptables -L INPUT -n -v | grep -i tailscale
sudo iptables -L FORWARD -n -v | grep -i tailscale

# For nftables-based systems:
sudo nft list ruleset | grep -i tailscale

# Check if Docker's published ports bypass UFW
# Run from an external machine (not over Tailscale):
nmap -p 8080,443,80 <VPS_PUBLIC_IP>
```

---

## 7. Summary: Exact Recommendations for Ubuntu 24.04

### 7.1 UFW Configuration

```bash
# 1. Default policy
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 2. Allow SSH only over Tailscale
sudo ufw allow in on tailscale0 to any port 22 proto tcp

# 3. Allow nginx/Aizanta only over Tailscale
sudo ufw allow in on tailscale0 to any port 80 proto tcp

# 4. Enable UFW
sudo ufw enable

# 5. Remove generic OpenSSH rule (prevent public SSH)
sudo ufw status numbered
# Identify the generic "OpenSSH" or "22/tcp" rule (not on tailscale0) and delete it
sudo ufw delete <NUMBER>
```

### 7.2 Docker Integration

Apply one or both:
- **Config fix:** Add DOCKER-USER chain rules to `/etc/ufw/after.rules` (see §4.3)
- **Operational fix:** Always bind Docker containers to localhost for internal services

### 7.3 Lockout Prevention

- Always keep a **second SSH session** open when changing firewall rules
- Add Tailscale allow rules **before** enabling UFW
- Consider installing via `screen` or `tmux` so session survives network hiccups
- After changes, test by disconnecting and reconnecting over Tailscale

### 7.4 Key URLs

| Resource | URL |
|---|---|
| Tailscale: Using Tailscale with your firewall | https://tailscale.com/docs/integrations/firewalls |
| Tailscale: Netfilter modes | https://tailscale.com/docs/reference/netfilter-modes |
| Tailscale: Firewall ports FAQ | https://tailscale.com/docs/reference/faq/firewall-ports |
| Tailscale: Secure Ubuntu server with UFW | https://tailscale.com/docs/how-to/secure-ubuntu-server-with-ufw |
| Tailscale: Connection types / NAT traversal | https://tailscale.com/docs/reference/connection-types |
| Tailscale issue #9084 (auto-allow tailscale0) | https://github.com/tailscale/tailscale/issues/9084 |
| Tailscale PR #10370 (auto-allow UDP port) | https://github.com/tailscale/tailscale/pull/10370 |
| Docker: Packet filtering and firewalls | https://docs.docker.com/engine/network/packet-filtering-firewalls/ |
| ufw-docker project (DOCKER-USER fix) | https://github.com/chaifeng/ufw-docker |
| Docker Security on a Shared VPS (Dev.to) | https://dev.to/jonesrussell/docker-security-on-a-shared-vps-1caj |

---

## 8. Caveats

1. **Tailscale auto-rules ≠ full UFW control:** Tailscale traffic bypasses UFW's INPUT chain by design. For fine-grained control over Tailscale traffic, use Tailscale ACLs (admin console) instead of UFW.
2. **UFW status is misleading:** `ufw status` will show ports as denied even when they're accessible via Docker. Always verify with actual network probes.
3. **`ufw-docker` may require reboot:** Some users report rules don't take effect until after a full reboot, not just `ufw reload`.
4. **Tailscale version matters:** Pre-v1.56 installations lack the auto-rule feature. Verify with `tailscale version`.
5. **Docker + iptables-nft migration:** Ubuntu 24.04 may default to nftables. Tailscale supports both, but verify compatibility if using Docker's nftables backend.

---

*End of report. No VPS changes performed.*

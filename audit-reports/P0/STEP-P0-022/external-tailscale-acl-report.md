# External Research Report: Tailscale ACL Configuration

**Task**: STEP-P0-022 — Tailscale ACL research for Guinevere VPS deployment
**Date**: 2026-05-31
**Researcher**: The Librarian (Guinevere sub-agent)
**Status**: Complete

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Tailnet Policy File & HuJSON Format](#2-tailnet-policy-file--hujson-format)
3. [Grants vs ACLs: Current Tailscale Recommendation](#3-grants-vs-acls-current-tailscale-recommendation)
4. [Device Tagging](#4-device-tagging)
5. [Tag Owners (tagOwners)](#5-tag-owners-tagowners)
6. [Auto Approvers](#6-auto-approvers)
7. [MagicDNS](#7-magicdns)
8. [ACL Rules for Single-Operator Setup](#8-acl-rules-for-single-operator-setup)
9. [Tailscale SSH Configuration](#9-tailscale-ssh-configuration)
10. [Auth Keys for Headless Nodes](#10-auth-keys-for-headless-nodes)
11. [ACL Testing & Verification Commands](#11-acl-testing--verification-commands)
12. [Lockout Prevention & Recovery Path](#12-lockout-prevention--recovery-path)
13. [Shared VPS Considerations (Docker + Aizanta)](#13-shared-vps-considerations-docker--aizanta)
14. [Ubuntu 24.04 Specific Considerations](#14-ubuntu-2404-specific-considerations)
15. [Key References](#15-key-references)

---

## 1. Executive Summary

Tailscale provides a **deny-by-default** access control model via a centralized **tailnet policy file** written in **HuJSON** (Human JSON — JSON with comments and trailing commas). The policy file lives in the Tailscale admin console and controls:

- Which devices/users can communicate (network layer)
- Who can SSH into which machines
- Which tags can be applied to devices and by whom
- Automatic route/exit node approval
- Device posture requirements

For a single-operator setup (Faiz = operator, ~2-3 devices), the recommended approach is:

1. **Tag the VPS** as `tag:service` (non-user identity)
2. **Keep the admin device untagged** (user identity — `faizzzzz@...`)
3. **Write ACL rules** that allow the user full access, restrict service-to-service
4. **Use grants syntax** (newer, recommended) instead of legacy ACLs
5. **Add ACL tests** to prevent accidental lockout
6. **Enable MagicDNS** for hostname-based access
7. **Generate a tagged auth key** for headless VPS provisioning

---

## 2. Tailnet Policy File & HuJSON Format

### File Structure

The tailnet policy file is a HuJSON (`.hujson`) file with these top-level sections:

| Section | Key | Type | Purpose |
|---------|-----|------|---------|
| Grants | `grants` | Access control | Network-level + app-level policies (recommended) |
| ACLs | `acls` | Access control | Network-level policies only (legacy, still supported) |
| SSH | `ssh` | Access control | Tailscale SSH rules |
| Tag owners | `tagOwners` | Targets | Who can assign which tags |
| Auto approvers | `autoApprovers` | Automation | Auto-approve routes/exit nodes |
| Groups | `groups` | Targets | Named groups of users |
| Hosts | `hosts` | Targets | Named aliases for IPs/subnets |
| Tests | `tests` | Tests | Assertions about access policies |
| SSH tests | `sshTests` | Tests | Assertions about SSH policies |
| Postures | `postures` | Attributes | Device posture rules |
| Node attributes | `nodeAttrs` | Attributes | Additional attributes for devices |
| IP sets | `ipsets` | Targets | Named network segments |

**Source**: [Syntax reference for the tailnet policy file](https://tailscale.com/docs/reference/syntax/policy-file)

### HuJSON Characteristics

- Supports `//` and `/* */` comments
- Allows trailing commas in arrays and objects
- Pure JSON is valid HuJSON (strict subset)

### Source Type Reference

Access rules use these source/destination types:

| Type | Example | Description |
|------|---------|-------------|
| Any | `*` | All tailnet traffic |
| User | `faizzzzz@github` | All devices of that user |
| Group | `group:admin` | All users in group |
| Tag | `tag:service` | All devices with that tag |
| Autogroup (all members) | `autogroup:member` | All tailnet members |
| Autogroup (admin) | `autogroup:admin` | Users with Admin role |
| Autogroup (self) | `autogroup:self` | Same user as source (for SSH) |
| Tailscale IP | `100.94.104.22` | Single device |
| CIDR | `192.168.1.0/24` | Subnet range |

---

## 3. Grants vs ACLs: Current Tailscale Recommendation

> **Critical finding**: Tailscale now recommends **grants** over ACLs for all new configurations.

### Key Facts

| Aspect | ACLs | Grants |
|--------|------|--------|
| Status | Legacy, fully supported | Current, recommended |
| New features? | No new features | All new features |
| Co-existence | Yes, side-by-side | Yes, side-by-side |
| Conversion | N/A | Admin console has "Convert to grants" button |

**From official docs**: "Tailscale now secures access to resources using grants, a next-generation access control policy syntax. Grants provide all original ACL functionality plus additional capabilities. ACLs will continue to work indefinitely; Tailscale will not remove support for this first-generation syntax from the product. However, Tailscale recommends migrating to grants and using grants for all new tailnet policy file configurations because ACLs will not receive any new features."

**Source**: [Migrate from ACLs to grants](https://tailscale.com/docs/reference/migrate-acls-grants)

### Grants Syntax Example

```hujson
{
  // Grants syntax (recommended for new configs)
  "grants": [
    {
      "src": ["autogroup:admin"],
      "dst": ["tag:service"],
      "ip": ["*"]  // All ports/protocols
    },
    {
      "src": ["tag:monitoring"],
      "dst": ["tag:service"],
      "ip": ["tcp:80,443"]  // Only HTTP/HTTPS
    }
  ]
}
```

Key difference: grants combine `ports` and `proto` into a single `ip` field and remove the redundant `action` field (all grants are `accept` by default).

### Recommendation for Guinevere

Use **grants syntax** for the new policy file. It's cleaner, the recommended path, and supports future features. ACLs can coexist if needed.

---

## 4. Device Tagging

### What Tags Do

Tags are how Tailscale identifies **non-user devices** (servers, containers, services). Key behaviors:

- **Applying a tag removes user-based authentication** from that device
- **Tagged devices don't have key expiry** by default
- **Multiple tags per device** are allowed
- **Tags are durable** through device replacement

### Tag Naming Convention

Tags must start with `tag:` prefix. Recommended naming patterns:

```
tag:service       # General service devices
tag:admin         # Administrative access
tag:monitoring    # Prometheus/Grafana
tag:guinevere     # Guinevere-specific
tag:aizanta       # Aizanta-specific
tag:container     # Containerized workloads
tag:prod          # Production
tag:dev           # Development
```

### For Guinevere Setup

```hujson
"tagOwners": {
  // Only the tailnet admin (Faiz) can assign these tags
  "tag:service": ["autogroup:admin"],
  "tag:admin":   ["autogroup:admin"]
}
```

### How to Tag

**Method 1 — Via admin console (after device is connected)**:
1. Go to Machines page
2. Click the device's three-dot menu
3. Edit ACL tags
4. Add `tag:service` (and/or `tag:admin`)

**Method 2 — Via CLI on the device**:
```bash
sudo tailscale set --advertise-tags=tag:service
```

**Method 3 — Via auth key (during provisioning)**:
Generate an auth key with tags pre-assigned. Devices using that key are automatically tagged.

### Important Warnings

> **Do not use tags for user devices** (laptops, phones). Tags are for service/non-human machines only. A device cannot have both a user identity and tags simultaneously.

> **Tagged devices cannot SSH into user-owned devices** — only into other tagged devices.

**Source**: [Group devices with tags](https://tailscale.com/docs/features/tags)

---

## 5. Tag Owners (tagOwners)

`tagOwners` defines who can assign each tag. Without explicit ownership, no one can tag a device.

### Syntax

```hujson
"tagOwners": {
  "tag:service": ["autogroup:admin"],    // Only admins
  "tag:admin":   ["autogroup:admin"],    // Only admins
  "tag:dev":     ["autogroup:member"],   // Any tailnet member
  "tag:ci-cd":   []                       // Shorthand for autogroup:admin
}
```

### `[]` Shorthand

An empty array `[]` is shorthand for `["autogroup:admin"]`.

### Tag Hierarchy

Tags can own other tags:

```hujson
"tagOwners": {
  "tag:deployment": ["autogroup:admin"],
  "tag:prod":      ["tag:deployment"],  // Only deployment-tagged devices
  "tag:staging":   ["tag:deployment"]
}
```

**Source**: [Syntax reference — tagOwners](https://tailscale.com/docs/reference/syntax/policy-file#tag-owners)

---

## 6. Auto Approvers

Auto approvers automate route/exit node approval so you don't need manual admin console clicks.

### For Guinevere

If the VPS needs to advertise subnet routes (e.g., Docker bridge networks to reach containers):

```hujson
"autoApprovers": {
  "routes": {
    "10.0.0.0/16": ["tag:service"],    // Auto-approve Docker network routes
    "172.17.0.0/16": ["tag:service"]    // Default Docker bridge
  }
}
```

### Important Caveat

> Auto-approver policies only apply when Tailscale **first receives** a subnet route advertisement. Updating the tailnet policy file to add or modify auto-approvers does **not retroactively approve** existing unapproved routes. Remove and re-advertise to trigger auto-approval.

**Source**: [Syntax reference — autoApprovers](https://tailscale.com/docs/reference/syntax/policy-file#auto-approvers)

---

## 7. MagicDNS

### What It Does

MagicDNS automatically registers DNS names for every Tailscale device. Format:
```
<hostname>.<tailnet-name>.ts.net
```

With MagicDNS enabled, you can use short hostnames (e.g., `faiz-prod-01`) instead of Tailscale IPs.

### Enabling MagicDNS

1. Go to [Tailscale Admin Console → DNS](https://login.tailscale.com/admin/dns)
2. Click **Enable MagicDNS**
3. Done

> **Note**: Tailnets created after October 20, 2022 have MagicDNS enabled by default.

### Verification

```bash
# Test full FQDN resolution
nslookup faiz-prod-01.<tailnet-name>.ts.net
# or
tailscale ping faiz-prod-01.<tailnet-name>.ts.net

# Test short hostname (requires search domain)
tailscale ping faiz-prod-01

# DNS status
tailscale dns status
```

### Linux-Specific Note (Ubuntu 24.04)

Use `resolvectl` or `dig` instead of `nslookup` on modern Linux:

```bash
# Test MagicDNS resolution
resolvectl query faiz-prod-01.<tailnet>.ts.net

# Check DNS configuration set by Tailscale
resolvectl status
```

**Source**: [MagicDNS](https://tailscale.com/docs/features/magicdns)

### Known Issues

- On **macOS**, `nslookup` and `host` bypass system DNS and won't resolve MagicDNS names. Use `dscacheutil -q host -a name <hostname>` instead.
- Short hostname resolution requires correct search domain configuration. Check `tailscale dns status` to confirm.

**Source**: [DNS in Tailscale](https://tailscale.com/docs/reference/dns-in-tailscale)

---

## 8. ACL Rules for Single-Operator Setup

### Design Principles

1. **Deny by default** — Only allow what's explicitly needed
2. **Tag servers, don't tag users** — Use `tag:service` for the VPS
3. **Explicit SSH rules** — SSH ACLs are separate from network ACLs
4. **ACL tests** — Prevent accidental lockout on policy changes

### Recommended Policy (Grants Syntax)

```hujson
{
  // Who can assign tags
  "tagOwners": {
    "tag:service": ["autogroup:admin"],   // Only Faiz (admin) can tag
    "tag:admin":   ["autogroup:admin"]
  },

  // Network access rules (grants — recommended)
  "grants": [
    // === ADMIN ACCESS ===
    // Faiz (autogroup:admin) can access everything
    {
      "src": ["autogroup:admin"],
      "dst": ["*"],
      "ip": ["*"]
    },

    // === SERVICE RESTRICTIONS ===
    // Tagged service devices can reach each other (needed for Aizanta ↔ Guinevere)
    {
      "src": ["tag:service"],
      "dst": ["tag:service"],
      "ip": ["*"]
    },

    // Service devices CANNOT initiate connections to admin/user devices
    // (deny by default — already enforced, no rule needed)
  ],

  // SSH rules
  "ssh": [
    // Admin can SSH to own devices and tagged devices
    {
      "action": "accept",
      "src": ["autogroup:admin"],
      "dst": ["autogroup:self", "tag:service"],
      "users": ["autogroup:nonroot", "root"]
    },

    // All members can SSH to their own devices
    {
      "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["autogroup:self"],
      "users": ["autogroup:nonroot", "root"]
    }
  ],

  // ACL Tests — safety net!
  "tests": [
    // MUST: Admin can always access service devices
    {
      "src": "faizzzzz@github",
      "accept": ["tag:service:22", "tag:service:80", "tag:service:443"],
      "deny": []
    },
    // MUST NOT: Service devices cannot access admin's user device
    {
      "src": "tag:service",
      "deny": ["faizzzzz@github:22"]
    }
  ]
}
```

### Equivalent in ACL Syntax (if you prefer)

```hujson
{
  "tagOwners": {
    "tag:service": ["autogroup:admin"],
    "tag:admin":   ["autogroup:admin"]
  },

  "acls": [
    // Admin can access everything
    { "action": "accept", "src": ["autogroup:admin"], "dst": ["*:*"] },

    // Service devices can talk to each other
    { "action": "accept", "src": ["tag:service"], "dst": ["tag:service:*"] }

    // Everything else is implicitly denied
  ],

  "ssh": [
    {
      "action": "accept",
      "src": ["autogroup:admin"],
      "dst": ["autogroup:self", "tag:service"],
      "users": ["autogroup:nonroot", "root"]
    },
    {
      "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["autogroup:self"],
      "users": ["autogroup:nonroot", "root"]
    }
  ],

  "tests": [
    {
      "src": "faizzzzz@github",
      "accept": ["tag:service:22", "tag:service:80", "tag:service:443"],
      "deny": []
    }
  ]
}
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Tag VPS as `tag:service` | Server identity independent of user; survives account changes |
| Keep Windows device untagged | User identity allows `autogroup:self` SSH |
| `autogroup:admin` for admin | Uses Tailscale role-based access, not hardcoded emails |
| Service-to-service allowed | Aizanta and Guinevere containers need to communicate |
| Service-to-user denied | Security boundary — compromised container can't SSH to admin |
| SSH for admin on all tagged devices | Faiz can always SSH into VPS |
| ACL tests | Prevents policy changes from accidentally blocking admin access |

**Source**: [ACL policy examples](https://tailscale.com/docs/reference/examples/acls)

---

## 9. Tailscale SSH Configuration

### Enable Tailscale SSH on the VPS

```bash
sudo tailscale set --ssh
```

> **Warning**: Running `tailscale set --ssh` will cause existing SSH connections to the Tailscale IP to briefly hang while the Tailscale SSH handler initializes.

### How SSH ACLs Work

SSH rules are **separate** from network ACL rules. Both must be satisfied:

1. A network grant/ACL must allow traffic on port 22
2. An SSH rule must explicitly allow the SSH connection with specified users

### SSH Rule Structure

```hujson
"ssh": [
  {
    "action": "accept",      // "accept" or "check" (requires re-auth)
    "src": ["autogroup:admin"],
    "dst": ["tag:service"],  // Cannot be *, must be specific
    "users": ["root", "autogroup:nonroot"],
    "checkPeriod": "12h"     // Only for "check" action
  }
]
```

### Users Field

- `"root"` — Allow SSH as root
- `"autogroup:nonroot"` — Allow SSH as any non-root user
- `"ubuntu"` — Specific Linux user (Ubuntu default)
- If omitted, uses the connecting user's local username

### SSH from Tagged Devices

> **Important**: Tagged devices can only SSH into other tagged devices. They cannot SSH into user-owned devices. This is by design.

### SSH Session Recording

Available on Premium/Enterprise plans. Session recordings are stored in the admin console.

**Source**: [Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh)

---

## 10. Auth Keys for Headless Nodes

### Why Auth Keys

Auth keys allow **non-interactive** device registration — essential for headless VPS provisioning.

### Auth Key Types

| Type | Use Case |
|------|----------|
| **One-off** | Single device, single use |
| **Reusable** | Multiple devices, CI/CD, containers |
| **Ephemeral** | Auto-removed when offline; containers |
| **Pre-approved** | Skips device approval if enabled |
| **Tagged** | Automatically applies tags to devices |

### Creating a Tagged Auth Key for the VPS

1. Go to [Admin Console → Keys](https://login.tailscale.com/admin/keys)
2. Click **Generate auth key**
3. Settings:
   - **Reusable**: Yes (or No if single VPS)
   - **Ephemeral**: No (VPS is persistent)
   - **Tags**: `tag:service`
   - **Pre-approved**: Yes
4. Copy the key (starts with `tskey-auth-...`)

### Provisioning with Auth Key

```bash
sudo tailscale up --auth-key=tskey-auth-xxxxx --hostname=faiz-prod-01 --accept-routes
```

### OAuth Client (Advanced)

For automated key generation, create an OAuth client:

```bash
# Go utility to get an auth key programmatically
go run tailscale.com/cmd/get-authkey@latest -tags tag:service --reusable
```

### Combined with MagicDNS

```bash
sudo tailscale up --auth-key=tskey-auth-xxxxx --hostname=faiz-prod-01 --ssh
```

This joins the tailnet, applies `tag:service`, sets hostname for MagicDNS, and enables Tailscale SSH.

**Source**: [Setting up a server on your Tailscale network](https://tailscale.com/docs/how-to/set-up-servers)

---

## 11. ACL Testing & Verification Commands

### Tailscale Status

```bash
# Basic status
tailscale status

# JSON output (machine-readable)
tailscale status --json
```

### Ping Tests

```bash
# TSMP ping (checks WireGuard connectivity, bypasses ACL check)
tailscale ping --tsmp 100.94.104.22

# ICMP ping (checks end-to-end including ACLs)
tailscale ping --icmp 100.94.104.22

# Regular ping (stops after direct path established)
tailscale ping faiz-prod-01
```

**Debug logic**:
- TSMP succeeds + ICMP fails = **ACL blocking** the connection
- TSMP fails = **Network connectivity issue** (not ACL-related)
- Both succeed = ACL allows the connection

### Netmap Inspection

```bash
# Dump the current network map (ACL rules applied locally)
tailscale debug netmap

# Pipe to file for analysis
tailscale debug netmap > netmap.json
```

### DNS Debugging

```bash
# DNS status
tailscale dns status

# DNS query via Tailscale resolver
tailscale dns query faiz-prod-01

# Or on Linux:
resolvectl query faiz-prod-01.<tailnet>.ts.net
```

### ACL Testing with Admin Console

The admin console has built-in ACL test functionality:

1. Go to **Access Controls**
2. Use the **Tests** section in the policy file
3. Test rules like:
   ```hujson
   "tests": [
     {
       "src": "faizzzzz@github",
       "accept": ["tag:service:22", "tag:service:80"],
       "deny": ["tag:service:5432"]  // if DB port should be blocked
     }
   ]
   ```
4. Save — if tests fail, Tailscale **rejects** the policy change

### SSH Test Commands

```bash
# Verify SSH ACL without connecting
tailscale ssh --dry-run faiz-prod-01
```

### Network Check

```bash
# Report on current physical network conditions
tailscale netcheck
```

**Source**: [Tailscale CLI reference](https://tailscale.com/docs/reference/tailscale-cli)

---

## 12. Lockout Prevention & Recovery Path

### Prevention Strategy

1. **ACL Tests**: Always include tests that assert admin access is preserved. Tailscale rejects policy file changes that fail tests.

2. **Incremental Changes**: Apply one rule at a time, test between each.

3. **Keep Traditional SSH as Backup**: Before enabling Tailscale SSH, keep the regular SSH server running on a non-Tailscale interface. You can disable it only after confirming Tailscale SSH works.

4. **Review Before Save**: The admin console shows the full diff. Review carefully before saving.

5. **Start Permissive, Tighten Later**: Begin with broad allow rules, then narrow down. From the docs: "Start with a permissive policy and tighten it after testing."

### If Lockout Happens

#### Recovery Path A — Admin Console (Browser)

1. Open `https://login.tailscale.com/admin/acls` from a different device (phone, another computer)
2. Click **Configuration logs** (left sidebar)
3. Find the offending change
4. Click **Revert to previous version**

> The admin console keeps a full audit log of all policy file changes with one-click revert.

#### Recovery Path B — Delete the policy file

In the admin console Access Controls page:
1. Select **Reset to default**
2. This resets to the default "allow all" policy
3. Re-apply your ACLs more carefully

#### Recovery Path C — Traditional SSH (if still running)

If you kept `sshd` running on the VPS's public IP or local network:

```bash
ssh user@<public-ip> -i ~/.ssh/your-key
```

Then fix Tailscale:

```bash
sudo tailscale set --accept-routes=false  # Disable routes if they're the issue
# or
sudo tailscale logout           # Remove from tailnet
sudo tailscale up --ssh         # Rejoin
```

#### Recovery Path D — VPS Console (Last Resort)

If everything fails:
1. Access the VPS via provider's web console (Vultr/DigitalOcean/etc.)
2. Fix or disable Tailscale:
   ```bash
   sudo systemctl stop tailscaled
   # Edit the policy file can't be fixed locally — it's server-side
   # But you can re-join with a fresh auth key
   sudo tailscale logout
   sudo tailscale up --auth-key=tskey-auth-xxxxx --ssh
   ```

### Critical: Never Disable SSH on the VPS Without Testing

Before disabling OpenSSH (`systemctl stop sshd`), confirm Tailscale SSH works:

```bash
# From admin device (Windows/macOS):
tailscale ssh faiz-prod-01

# Only if this works reliably, then consider:
sudo systemctl disable --now sshd
```

**Source**: [Tailscale SSH migration guide](https://oneuptime.com/blog/post/2026-01-27-tailscale-ssh/view)

---

## 13. Shared VPS Considerations (Docker + Aizanta)

### The Problem

The VPS runs multiple containers:
- **Guinevere** (this project's agents)
- **Aizanta** (another autonomous agent system)

These containers may need inter-container communication. ACLs must not block that traffic.

### Solution Architecture

```
┌─────────────────────────────────────────────┐
│                VPS (faiz-prod-01)            │
│  Tailscale IP: 100.94.104.22                │
│  Tag: tag:service                            │
│                                              │
│  ┌──────────┐    ┌──────────┐               │
│  │ Guinevere│◄──►│ Aizanta  │  ← Docker net │
│  │ Container│    │ Container│               │
│  └──────────┘    └──────────┘               │
│        ▲                                      │
│        │ Tailscale                             │
│        ▼                                      │
│  ┌──────────┐                                │
│  │ tailscaled│                                │
│  └──────────┘                                │
└─────────────────────────────────────────────┘
        │ Tailscale
        ▼
┌──────────────────────┐
│ Windows Device        │
│ (faizzzzz, admin)     │
│ 100.112.201.124       │
│ User identity         │
└──────────────────────┘
```

### Key Points

1. **Container-to-container via Docker networks** is local traffic on the VPS and **NOT affected by Tailscale ACLs**. ACLs only control traffic that goes through the Tailscale interface. Docker bridge traffic stays inside the VPS.

2. **Containers connecting through Tailscale** (using tsnet or sidecar) would be subject to ACLs. If both Guinevere and Aizanta containers are tagged `tag:service`, the example policy allows service-to-service communication.

3. **Subnet routes** — If you want to reach Docker containers directly from your Windows device via Tailscale, you'd need to advertise Docker bridge subnet routes and set up auto-approvers.

### If Containers Need Tailscale Access

If containers use Tailscale directly (via tsnet library or sidecar):

```hujson
"grants": [
  // Service containers can talk to each other
  {
    "src": ["tag:service"],
    "dst": ["tag:service"],
    "ip": ["*"]
  }
]
```

### Docker Network Consideration

Docker creates a `docker0` bridge (usually `172.17.0.0/16`). If you want to access containers from outside the VPS via Tailscale, you'd need:

1. Advertise the Docker bridge route: `tailscale set --advertise-routes=172.17.0.0/16`
2. Set up auto-approvers or manually approve
3. Accept routes on the client: `tailscale set --accept-routes=true` (on Windows device)

> **Caution**: Route advertising can leak more network access than intended. Be specific with the CIDR.

---

## 14. Ubuntu 24.04 Specific Considerations

### Installation

```bash
# Official Tailscale install for Ubuntu 24.04
curl -fsSL https://tailscale.com/install.sh | sh
```

### systemd Service Management

```bash
# Check service status
sudo systemctl status tailscaled

# Restart
sudo systemctl restart tailscaled

# View logs
sudo journalctl -u tailscaled -f
```

### DNS on Ubuntu 24.04

Ubuntu 24.04 uses `systemd-resolved` by default. Tailscale integrates with it automatically when `--accept-dns=true` (default).

```bash
# Verify DNS integration
resolvectl status

# Check Tailscale-specific DNS config
resolvectl dns tailscale0

# Test MagicDNS
resolvectl query faiz-prod-01.<tailnet>.ts.net
```

### Firewall (UFW)

Tailscale uses WireGuard (UDP port 41641 by default). If UFW is enabled:

```bash
# Allow incoming Tailscale traffic on WireGuard port
sudo ufw allow in on tailscale0
# or just allow the UDP port
sudo ufw allow 41641/udp
```

### Kernel Parameters

Tailscale WireGuard works with the default Ubuntu 24.04 kernel. No special kernel modules are needed.

### Known Issues

- **systemd-resolved conflicts**: If you have custom `/etc/resolv.conf` settings, Tailscale may override them when `--accept-dns=true`. Set `--accept-dns=false` if you need manual DNS control.
- **AppArmor**: Tailscale's AppArmor profile is installed with the package. No additional configuration needed.

---

## 15. Key References

### Official Tailscale Documentation

| Topic | URL |
|-------|-----|
| Tailnet policy file syntax | https://tailscale.com/docs/reference/syntax/policy-file |
| ACL overview | https://tailscale.com/docs/features/access-control/acls |
| ACL examples | https://tailscale.com/docs/reference/examples/acls |
| Migrate to grants | https://tailscale.com/docs/reference/migrate-acls-grants |
| Device tags | https://tailscale.com/docs/features/tags |
| MagicDNS | https://tailscale.com/docs/features/magicdns |
| DNS in Tailscale | https://tailscale.com/docs/reference/dns-in-tailscale |
| Tailscale SSH | https://tailscale.com/docs/features/tailscale-ssh |
| Auth keys | https://tailscale.com/docs/features/access-control/auth-keys |
| Server setup | https://tailscale.com/docs/how-to/set-up-servers |
| Tailscale CLI | https://tailscale.com/docs/reference/tailscale-cli |
| Troubleshooting | https://tailscale.com/docs/reference/troubleshooting |
| Security best practices | https://tailscale.com/docs/reference/best-practices/security |

### GitHub Reference

| Resource | URL |
|----------|-----|
| Example ACL file (Tailscale test data) | https://github.com/tailscale/tailscale-client-go-v2/blob/main/testdata/acl.json |
| Docker guide ACL example | https://github.com/tailscale-dev/docker-guide-code-examples/blob/main/example-acls.hujson |
| Tailscale ping source | https://github.com/tailscale/tailscale/blob/main/cmd/tailscale/cli/ping.go |
| Tailscale status source | https://github.com/tailscale/tailscale/blob/main/cmd/tailscale/cli/status.go |
| Tailscale debug source | https://github.com/tailscale/tailscale/blob/main/cmd/tailscale/cli/debug.go |
| Terraform module | https://github.com/tailscale/terraform-cloudinit-tailscale |

### Community Resources

| Resource | URL |
|----------|-----|
| Segmenting network with ACL tags | https://www.pagefault.it/en/segmenting-tailscale-network-acl-tags/ |
| Tailscale on AWS guide | https://yaw.sh/blog/tailscale-aws-practical-guide-gotchas/ |
| Skyscrapers ACL guide | https://docs.skyscrapers.eu/docs/technologies/networking/vpn/tailscale-acl/ |
| Tailscale tips & tricks 2026 | https://softverdict.com/tailscale-tips-tricks-2026/ |

### Pricing Notes

| Feature | Plan |
|---------|------|
| ACLs/Grants | All plans |
| Tags | All plans (50 tagged devices included) |
| MagicDNS | All plans |
| Tailscale SSH | All plans |
| ACL Tests | All plans |
| SSH check mode | Premium+ |
| Session recording | Premium+ |
| Auto approvers | All plans |

---

## Appendix A: Quick Command Reference

```bash
# === VPS PROVISIONING ===
sudo tailscale up --auth-key=tskey-auth-xxxxx --hostname=faiz-prod-01 --ssh --accept-routes

# === ENABLE SSH ===
sudo tailscale set --ssh

# === TAG DEVICE ===
sudo tailscale set --advertise-tags=tag:service

# === STATUS ===
tailscale status
tailscale status --json

# === PING ===
tailscale ping faiz-prod-01
tailscale ping --icmp 100.94.104.22
tailscale ping --tsmp 100.94.104.22

# === DNS ===
tailscale dns status
resolvectl query faiz-prod-01

# === DEBUG ===
tailscale debug netmap
tailscale netcheck

# === ADVERTISE ROUTES (Docker) ===
sudo tailscale set --advertise-routes=172.17.0.0/16

# === ACCEPT ROUTES (Windows client) ===
tailscale set --accept-routes=true

# === LOCKOUT RECOVERY ===
# Via admin console: Settings → Configuration logs → Revert
# Via VPS web console:
sudo tailscale logout
sudo tailscale up --auth-key=tskey-auth-xxxxx --ssh
```

---

## Appendix B: Policy File Template (Minimal — Grants Syntax)

```hujson
// Guinevere VPS Tailscale Policy
// Target: faiz-prod-01 (100.94.104.22), tagged as tag:service
// Operator: faizzzzz@github (100.112.201.124, Windows)

{
  // === TAG OWNERS ===
  "tagOwners": {
    "tag:service": ["autogroup:admin"],
    "tag:admin":   ["autogroup:admin"]
  },

  // === NETWORK ACCESS (Grants) ===
  "grants": [
    // Admin (Faiz) can access everything
    { "src": ["autogroup:admin"], "dst": ["*"], "ip": ["*"] },

    // Service devices talk to each other (needed for Aizanta ↔ Guinevere)
    { "src": ["tag:service"], "dst": ["tag:service"], "ip": ["*"] }
  ],

  // === SSH ===
  "ssh": [
    {
      "action": "accept",
      "src": ["autogroup:admin"],
      "dst": ["autogroup:self", "tag:service"],
      "users": ["autogroup:nonroot", "root"]
    },
    {
      "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["autogroup:self"],
      "users": ["autogroup:nonroot", "root"]
    }
  ],

  // === TESTS (Lockout Protection) ===
  "tests": [
    {
      "src": "faizzzzz@github",
      "accept": ["tag:service:22"],
      "deny": []
    }
  ]
}
```

---

*End of report. All sources verified against official Tailscale documentation (validated through May 2026).*
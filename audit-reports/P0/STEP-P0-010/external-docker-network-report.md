# Docker Network Isolation — External Research Report
## STEP-P0-010: Guinevere Bridge Network (`guinevere-net`) on Shared VPS

**Date**: 2026-05-31  
**Researcher**: Guinevere (Librarian Mode)  
**Scope**: External research — no VPS commands executed, no project files modified  
**Target Environment**: Ubuntu 24.04, Docker Engine, UFW active, CrowdSec nftables bouncer active, Aizanta containers co-located

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Critical Finding: 172.28.0.0/16 Risk Assessment](#2-critical-finding-1722800016-risk-assessment)
3. [Docker Bridge Network Isolation](#3-docker-bridge-network-isolation)
4. [Docker + UFW + nftables Interaction](#4-docker--ufw--nftables-interaction)
5. [CrowdSec Bouncer Coexistence](#5-crowdsec-bouncer-coexistence)
6. [Subnet Sizing: /16 vs /24 vs /22](#6-subnet-sizing-16-vs-24-vs-22)
7. [Shared VPS Multi-Project Considerations](#7-shared-vps-multi-project-considerations)
8. [Docker Compose External Network Integration](#8-docker-compose-external-network-integration)
9. [Verification & Safety Procedures](#9-verification--safety-procedures)
10. [Recommendations for STEP-P0-010](#10-recommendations-for-step-p0-010)
11. [References & Source URLs](#11-references--source-urls)

---

## 1. Executive Summary

This report provides authoritative guidance on creating an isolated Docker bridge network (`guinevere-net`) on a shared Ubuntu 24.04 VPS that already hosts Aizanta Docker containers. Key findings:

| Finding | Impact |
|---|---|
| **172.28.0.0/16 is inside Docker's built-in default address pools** | Potential conflict with auto-allocated Docker networks |
| Docker bridge networks provide **true kernel-level isolation** | Containers on different bridges CANNOT communicate by default |
| UFW **does not protect Docker-published ports** | Traffic bypasses INPUT chain via DNAT; DOCKER-USER chain is the fix |
| CrowdSec bouncer uses DOCKER-USER chain | Must ensure startup ordering (`After=docker.service`) |
| `/16` subnet is **65,534 addresses — overkill for any single project** | Industry standard for bridge networks is `/24` |
| Docker Compose `external: true` | Clean integration with CLI-created networks |

---

## 2. Critical Finding: 172.28.0.0/16 Risk Assessment

### 2.1 Docker's Default Address Pools

Docker has **built-in default address pools** used for auto-allocating subnets when `--subnet` is NOT specified during `docker network create`:

```json
{
  "default-address-pools": [
    { "base": "172.17.0.0/16", "size": 16 },
    { "base": "172.18.0.0/16", "size": 16 },
    { "base": "172.19.0.0/16", "size": 16 },
    { "base": "172.20.0.0/14", "size": 16 },
    { "base": "172.24.0.0/14", "size": 16 },
    { "base": "172.28.0.0/14", "size": 16 },
    { "base": "192.168.0.0/16", "size": 20 }
  ]
}
```

**Source**: [Docker Docs — Networking Overview / Subnet Allocation](https://docs.docker.com/engine/network/#subnet-allocation)

### 2.2 The Problem with 172.28.0.0/16

`172.28.0.0/16` falls **entirely within** the `172.28.0.0/14` default pool (which spans `172.28.0.0` to `172.31.255.255`). This means:

1. **If Docker auto-allocates a network** from the `172.28.0.0/14` pool, it could already be using `172.28.0.0/16` or a subnet within it.
2. **Docker REJECTS overlapping subnets** — if any existing Docker network (including auto-created Compose networks) already uses any part of `172.28.0.0/16`, `docker network create --subnet 172.28.0.0/16 guinevere-net` will **fail** with `Pool overlaps with other one on this address space`.
3. **Even if it succeeds**, a future auto-allocated network could fail because `172.28.0.0/16` has consumed the pool.

### 2.3 MUST-DO Before Creating guinevere-net

Run this command on the VPS **before** creating any new network:

```bash
# List ALL Docker networks and their subnets
docker network ls --format '{{.Name}}' | while read -r net; do
    subnet=$(docker network inspect "$net" \
        --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null)
    [ -n "$subnet" ] && echo "$net: $subnet"
done | sort
```

**Source**: [OneUptime — Docker Overlapping IPv4 Subnets](https://oneuptime.com/blog/post/2026-03-20-docker-overlapping-ipv4-subnets-config/view) / [StackOverflow](https://stackoverflow.com/questions/60105228/docker-get-a-list-of-created-networks-ip-addresses-ip-range-of-subnets)

Also check host routes that might conflict:

```bash
ip route show | grep -E '^172\.(28|29|30|31)\.'
```

---

## 3. Docker Bridge Network Isolation

### 3.1 How Bridge Networks Isolate

Docker bridge networks provide **kernel-level network namespace isolation** via Linux bridge devices and iptables/nftables rules:

- **Same bridge**: Containers can communicate freely, including DNS resolution (user-defined bridges only)
- **Different bridges**: Containers CANNOT communicate — packets are dropped by Docker's `DOCKER-ISOLATION-STAGE-1` and `DOCKER-ISOLATION-STAGE-2` iptables chains
- **Default bridge (`docker0`)**: All containers on it can communicate by IP (not name), regardless of project — **security risk**

**Source**: [Docker Docs — Bridge Network Driver](https://docs.docker.com/engine/network/drivers/bridge/)

### 3.2 Default Bridge vs User-Defined Bridge

| Feature | Default Bridge | User-Defined Bridge |
|---|---|---|
| DNS Resolution | No (IP only, `--link` deprecated) | Yes (automatic by container name) |
| Isolation | All containers share one network | Scoped per logical group |
| Runtime Connect/Disconnect | Requires restart | Hot-plug (`docker network connect`) |
| Subnet Config | Docker-managed only | Custom `--subnet`, `--gateway`, `--ip-range` |
| ICC (inter-container comm) | All containers reach all others | Only containers on SAME network |
| Recommended for Production | **No** | **Yes** |

### 3.3 Isolation Verification Commands

After creating `guinevere-net`:

```bash
# 1. Verify network exists with correct config
docker network inspect guinevere-net

# 2. Verify isolation: container on guinevere-net CANNOT reach Aizanta container
#    (assuming Aizanta on aizanta-net or default bridge)
docker run --rm --network guinevere-net alpine ping -c 2 -W 2 <aizanta-container-ip>

# 3. Verify isolation: Aizanta container CANNOT reach guinevere container
docker run --rm --network <aizanta-network> alpine ping -c 2 -W 2 <guinevere-container-ip>

# 4. Verify DNS works within guinevere-net
docker run -d --name test1 --network guinevere-net alpine sleep 3600
docker run -d --name test2 --network guinevere-net alpine sleep 3600
docker exec test1 ping -c 2 test2  # Should resolve by name
docker exec test1 ping -c 2 <aizanta-container-ip>  # Should FAIL
```

**Source**: [Docker Docs — Bridge Network Driver / User-Defined Bridge Example](https://docs.docker.com/engine/network/drivers/bridge/#use-user-defined-bridge-networks)

### 3.4 What CAN Cross Networks

- **Published ports** (`-p` / `--publish`) — exposed to host, accessible from anywhere
- **Multi-homed containers** — a container connected to BOTH networks can reach both
- **Host itself** — the Docker host can reach containers on any bridge network directly via their bridge gateway

---

## 4. Docker + UFW + nftables Interaction

### 4.1 The Fundamental Problem

UFW and Docker are **architecturally incompatible** for published ports. Docker writes rules that bypass UFW entirely:

```
Packet Flow for Docker Published Port:
  eth0 → PREROUTING (nat) → Docker DNAT rewrites destination → Routing → FORWARD → Container
                                                                          ↑
                                                                     UFW never sees it
                                                                     (UFW watches INPUT)
```

UFW manages the **INPUT** chain. Docker's published port traffic flows through **PREROUTING** (nat table) and **FORWARD** (filter table), completely bypassing UFW.

**Source**: [cr0x.net — UFW + Docker Lockdown](https://cr0x.net/en/ufw-docker-lockdown-compose/) / [Docker Docs — Packet Filtering Firewalls](https://github.com/docker/docs/blob/main/content/manuals/engine/network/packet-filtering-firewalls.md)

### 4.2 The DOCKER-USER Chain Solution

Docker provides the `DOCKER-USER` chain specifically for operator policy. Rules here execute **before** Docker's own accept rules:

```bash
# Check if DOCKER-USER chain exists
sudo iptables -S DOCKER-USER

# Default state (no policy):
# -N DOCKER-USER
# -A DOCKER-USER -j RETURN

# Add policy: drop all new inbound forwarded traffic, allow established
sudo iptables -I DOCKER-USER -i eth0 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -I DOCKER-USER -i eth0 -m conntrack --ctstate NEW -j DROP
```

**Important**: Rules in `DOCKER-USER` are **not persistent** across reboots unless saved with `iptables-persistent` or `netfilter-persistent`.

```bash
# Save rules persistently on Ubuntu 24.04
sudo apt install iptables-persistent -y
sudo netfilter-persistent save
```

### 4.3 Ubuntu 24.04 Specifics: nftables Under the Hood

Ubuntu 24.04 uses **nftables** as the kernel backend, but `iptables` commands go through the `iptables-nft` compatibility layer. Verify:

```bash
iptables --version
# Expected: iptables v1.8.10 (nf_tables)
```

The `(nf_tables)` suffix confirms the compatibility layer is active. DOCKER-USER chain rules **work through this layer**.

**Source**: [sudowheel.com — Docker iptables Compatibility Layer](https://sudowheel.com/docker-iptables-compatibility-layer.html) / [Virtua.cloud — Docker UFW Fix](https://www.virtua.cloud/learn/en/tutorials/docker-ufw-firewall-fix-vps)

### 4.4 Docker 29+ Native nftables Backend

Docker Engine 29.0.0 (November 2025) introduced an **experimental** native nftables backend (`--firewall-backend=nftables`). **Do NOT enable this on the VPS** unless you have a deliberate migration plan:

- The DOCKER-USER chain **does not exist** under the native nftables backend
- Instead, you must use custom nftables tables with priority-ordered base chains + `--bridge-accept-fwmark`
- This is experimental and **not recommended for production** in Docker 29.x

**Check which backend Docker is using:**

```bash
docker info | grep -i firewall
# If not present, Docker is using the default iptables backend (via iptables-nft)
```

### 4.5 Best Practice for Guinevere

**Do NOT set `"iptables": false` in `daemon.json`** — this breaks container NAT, port publishing, and inter-container networking. The Docker docs explicitly warn against this:

> "Setting the `iptables` or `ip6tables` keys to `false` [...] is not appropriate for most users, it is likely to break container networking."

Instead, the recommended approach:

1. **Keep UFW for host services** (SSH, node exporters, etc.)
2. **Use DOCKER-USER chain for container perimeter** — add allowlist + deny rules there
3. **Don't publish container ports on `0.0.0.0`** — bind to `127.0.0.1` when possible, and use a reverse proxy
4. **Use `docker run --network guinevere-net`** instead of the default bridge

**Source**: [cr0x.net — UFW + Docker Lockdown](https://cr0x.net/en/ufw-docker-lockdown-compose/) / [Authon.dev Blog](https://blog.authon.dev/why-docker-bypasses-ufw-and-how-to-actually-lock-it-down)

---

## 5. CrowdSec Bouncer Coexistence

### 5.1 How CrowdSec Interacts with Docker

The CrowdSec nftables firewall bouncer adds rules that can target the `DOCKER-USER` chain. Per CrowdSec's own documentation:

> "If you are using a dockerized application and allow remote connections to the exposed port, you need to add the `DOCKER-USER` chain to the list of chains."

**Source**: [CrowdSec Docs — Firewall Bouncer](https://docs.crowdsec.net/u/bouncers/firewall)

### 5.2 Known Issue: Bouncer Starting Before Docker

A well-documented issue ([cs-firewall-bouncer #216](https://github.com/crowdsecurity/cs-firewall-bouncer/issues/216)): the CrowdSec bouncer may start **before** Docker creates its chains, resulting in:

```
Error inserting set in iptables: iptables: No chain/target/match by that name.
```

**Fix**: Add Docker as a dependency in the bouncer's systemd unit:

```ini
# /etc/systemd/system/crowdsec-firewall-bouncer.service
[Unit]
After=syslog.target network.target remote-fs.target nss-lookup.target crowdsec.service docker.service
ReloadPropagatedFrom=docker.service

[Service]
# Add restart on failure
RemainAfterExit=no
Restart=always
RestartSec=20
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart crowdsec-firewall-bouncer
```

### 5.3 Docker Network Creation and CrowdSec

When you create a new Docker network, Docker writes iptables/nftables rules. CrowdSec's bouncer rules are in **separate tables/chains** (typically `crowdsec` / `crowdsec6` nftables tables or the `DOCKER-USER` chain with ipset). These should not conflict because:

- CrowdSec uses `DOCKER-USER` (or its own nftables tables)
- Docker manages `DOCKER`, `DOCKER-ISOLATION-STAGE-*`, `FORWARD`, and `nat` chains
- Creating a new bridge network adds isolation rules in Docker's chains, not CrowdSec's

**However**: If Docker daemon restarts, it may flush and recreate its chains. CrowdSec rules in `DOCKER-USER` would be lost. This is why `ReloadPropagatedFrom=docker.service` is critical.

### 5.4 CrowdSec Configuration Reference

From CrowdSec's default nftables config:

```yaml
# /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
nftables:
  ipv4:
    enabled: true
    set-only: false
    table: crowdsec
    chain: crowdsec-chain
    priority: -10
  ipv6:
    enabled: true
    set-only: false
    table: crowdsec6
    chain: crowdsec6-chain
    priority: -10
```

Priority `-10` runs CrowdSec **before** Docker's rules (default priority 0), which is correct. Creating `guinevere-net` will not affect CrowdSec's nftables tables.

---

## 6. Subnet Sizing: /16 vs /24 vs /22

### 6.1 Size Comparison

| CIDR | Total Addresses | Usable Hosts | Typical Use Case |
|---|---|---|---|
| `/16` | 65,536 | 65,534 | Entire corporate network, **overkill for single project** |
| `/20` | 4,096 | 4,094 | Large deployments, AWS default per-AZ |
| `/22` | 1,024 | 1,022 | General workload tier with headroom |
| `/24` | 256 | 254 | **Industry standard for single Docker bridge network** |
| `/28` | 16 | 14 | Small isolated services |

### 6.2 Docker Community Consensus

**Multiple authoritative sources agree: `/16` is too large for a single Docker bridge network.**

> "The default subnet allocation for a bridge network is a /16 (65,534 usable addresses), which is overkill in almost 100% of cases and can lead to address pool exhaustion."
>
> — [LinuxServer.io — Better Practices For Docker Networking](https://www.linuxserver.io/blog/better-practices-for-docker-networking)

> "I recommend using a /24 subnet block (256 IPs) to avoid conflicts with other networks."
>
> — [BetterLink Blog — Docker Network Mode Selection](https://eastondev.com/blog/en/posts/dev/20260514-docker-network-modes/)

> "Using /16 networks from the default address pool quickly exhausts the 172.16.0.0/12 range, leading Docker to start allocating from 192.168.0.0/16 which can conflict with LAN devices."
>
> — [Philipp Mundhenk — Docker IP Addresses](https://philippmundhenk.github.io/Docker_IP_addresses/)

### 6.3 Linux Bridge Limitations

The Linux kernel limits bridges to **1,024 ports** maximum. A `/16` network provides 65,534 addresses — you could never use them all even if you tried:

> "The Linux kernel doesn't support more than 1024 ports per bridge — you can't even change that through a compile-time flag, you'd need to do kernel surgery to get anything bigger. So it doesn't make sense to allocate /16 for them."
>
> — [moby/moby Issue #50107](https://github.com/moby/moby/issues/50107) (Docker maintainer)

### 6.4 Recommendation

**Use `/24` for Guinevere bridge network.** If you need more than 254 containers (you won't), you can create additional `/24` networks. Docker Compose automatically creates separate networks per project anyway.

---

## 7. Shared VPS Multi-Project Considerations

### 7.1 Network Namespace Separation

Docker provides strong isolation between projects if they use **separate user-defined bridge networks**:

- **Each bridge network** = separate Linux bridge device + separate iptables isolation rules
- Containers on different bridges = **no IP reachability, no DNS resolution**
- The host can reach all containers on all bridges (via gateway IP)

### 7.2 Subnet Collision Avoidance

**Strategy for shared VPS with Aizanta + Guinevere:**

1. **Audit existing Docker subnets first** (see Section 9.1)
2. **Do NOT use Docker's default pools** (172.17-31.x range) — pick from `10.0.0.0/8` or a specific `192.168.x.0/24` that doesn't conflict
3. **Configure `default-address-pools` in `/etc/docker/daemon.json`** to prevent future auto-allocation conflicts

```json
{
  "default-address-pools": [
    { "base": "172.17.0.0/16", "size": 24 },
    { "base": "172.18.0.0/16", "size": 24 },
    { "base": "10.100.0.0/16", "size": 24 }
  ]
}
```

This tells Docker to allocate `/24` networks instead of `/16`, giving 256 networks per pool instead of 1.

### 7.3 Project Identification

Use descriptive network names:

```bash
# Good
docker network create --subnet 10.100.0.0/24 guinevere-net

# Bad (ambiguous, may conflict)
docker network create guinevere-net
```

### 7.4 Avoid the Default Bridge

Any container launched **without `--network`** lands on the default `docker0` bridge. **This means Aizanta containers (if any) and Guinevere containers could accidentally share the default bridge.** Always specify `--network guinevere-net` or use Compose with explicit network declarations.

---

## 8. Docker Compose External Network Integration

### 8.1 Referencing an External Network

If `guinevere-net` is created via `docker network create`, Compose files reference it with `external: true`:

```yaml
# docker-compose.yml
services:
  guinevere-app:
    image: guinevere-app:latest
    networks:
      - guinevere-net

networks:
  guinevere-net:
    external: true
    name: guinevere-net
```

**Source**: [Docker Compose — External Networks](https://github.com/docker/compose/blob/main/compose/pkg/e2e/fixtures/external/compose.yaml)

### 8.2 Creating the Network Inside Compose (Alternative)

Or define it entirely in one Compose file:

```yaml
# docker-compose.yml
services:
  guinevere-app:
    image: guinevere-app:latest
    networks:
      - guinevere-net

networks:
  guinevere-net:
    driver: bridge
    name: guinevere-net
    ipam:
      driver: default
      config:
        - subnet: 10.100.0.0/24
          gateway: 10.100.0.1
```

### 8.3 Internal Network for Database Tier

Use `internal: true` for backend services that should never reach the internet:

```yaml
networks:
  guinevere-backend:
    driver: bridge
    internal: true
    name: guinevere-backend
    ipam:
      config:
        - subnet: 10.100.1.0/24

services:
  postgres:
    networks:
      - guinevere-backend
  api:
    networks:
      - guinevere-net       # External access (via reverse proxy)
      - guinevere-backend    # Database access
```

---

## 9. Verification & Safety Procedures

### 9.1 Pre-Creation Audit (MUST EXECUTE ON VPS)

```bash
# Step 1: List all Docker networks and subnets
echo "=== Docker Networks ==="
docker network ls --format '{{.Name}}' | while read -r net; do
    subnet=$(docker network inspect "$net" \
        --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null)
    [ -n "$subnet" ] && echo "  $net: $subnet"
done | sort

# Step 2: Check host routes for potential conflicts
echo "=== Host Routes (172.x) ==="
ip route show | grep '^172\.'

# Step 3: Check if 172.28.0.0/16 is already in use
echo "=== 172.28.0.0/16 Check ==="
docker network ls --format '{{.Name}}' | while read -r net; do
    docker network inspect "$net" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null
done | grep '172\.28\.'

# Step 4: Check iptables FORWARD chain ordering
echo "=== FORWARD Chain ==="
sudo iptables -S FORWARD

# Step 5: Check if DOCKER-USER has existing rules
echo "=== DOCKER-USER Chain ==="
sudo iptables -S DOCKER-USER

# Step 6: Check CrowdSec status
echo "=== CrowdSec Status ==="
sudo systemctl status crowdsec-firewall-bouncer --no-pager 2>/dev/null || echo "CrowdSec bouncer not found"
```

### 9.2 Safe Network Creation

```bash
# OPTION A: Use 172.28.0.0/16 (ONLY if audit confirms no conflict)
docker network create \
    --driver bridge \
    --subnet 172.28.0.0/16 \
    --gateway 172.28.0.1 \
    guinevere-net

# OPTION B: Use a /24 from 10.x range (RECOMMENDED — avoids Docker default pools)
docker network create \
    --driver bridge \
    --subnet 10.100.0.0/24 \
    --gateway 10.100.0.1 \
    guinevere-net

# OPTION C: Use a /24 from 192.168.x range (ensure no LAN conflict)
docker network create \
    --driver bridge \
    --subnet 192.168.100.0/24 \
    --gateway 192.168.100.1 \
    guinevere-net
```

### 9.3 Isolation Verification

```bash
# After creation, verify isolation
echo "=== Test 1: DNS within guinevere-net ==="
docker run -d --name gv-test-1 --network guinevere-net alpine sleep 300
docker run -d --name gv-test-2 --network guinevere-net alpine sleep 300
docker exec gv-test-1 ping -c 2 -W 2 gv-test-2 && echo "PASS: DNS resolution works" || echo "FAIL: DNS resolution broken"

echo "=== Test 2: Cross-network isolation ==="
# Find a container on a DIFFERENT network (e.g., Aizanta's network)
AIZANTA_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <aizanta-container-name> 2>/dev/null)
if [ -n "$AIZANTA_IP" ]; then
    docker exec gv-test-1 ping -c 2 -W 2 "$AIZANTA_IP" && echo "FAIL: Cross-network ping succeeded (isolation broken!)" || echo "PASS: Cross-network ping blocked"
fi

echo "=== Test 3: Outbound internet access ==="
docker exec gv-test-1 ping -c 2 -W 2 8.8.8.8 && echo "PASS: Outbound internet works" || echo "WARN: No outbound internet"

# Cleanup test containers
docker rm -f gv-test-1 gv-test-2
```

### 9.4 Rollback Procedure

```bash
# Step 1: Disconnect all containers from the network
docker network inspect guinevere-net --format '{{range .Containers}}{{.Name}} {{end}}' | \
    xargs -r -n1 -I{} docker network disconnect guinevere-net {}

# Step 2: Remove the network
docker network rm guinevere-net

# Step 3: Verify removal
docker network ls | grep guinevere-net && echo "FAIL: Network still exists" || echo "PASS: Network removed"
```

### 9.5 CrowdSec Verification After Network Creation

```bash
# Verify CrowdSec is still running after Docker network changes
sudo systemctl status crowdsec-firewall-bouncer

# Verify CrowdSec iptables rules are intact
sudo iptables -S DOCKER-USER | grep crowdsec

# Verify CrowdSec nftables rules are intact (if using nftables backend)
sudo nft list table ip crowdsec 2>/dev/null
sudo nft list table ip6 crowdsec6 2>/dev/null

# If rules are missing, restart the bouncer
sudo systemctl restart crowdsec-firewall-bouncer
```

---

## 10. Recommendations for STEP-P0-010

### 10.1 Subnet Selection

| Option | Subnet | Risk | Recommendation |
|---|---|---|---|
| **A** | `172.28.0.0/16` | **HIGH** — inside Docker default pools | Only use if audit confirms no auto-allocated networks in `172.28.0.0/14` AND you configure `default-address-pools` to exclude this range |
| **B** | `10.100.0.0/24` | **LOW** — outside Docker default pools, RFC 1918 private | **RECOMMENDED** |
| **C** | `192.168.100.0/24` | **MEDIUM** — may conflict with LAN/VPN | Use only if 10.x is unsuitable |

### 10.2 Recommended Command

```bash
docker network create \
    --driver bridge \
    --subnet 10.100.0.0/24 \
    --gateway 10.100.0.1 \
    guinevere-net
```

### 10.3 Pre-Flight Checklist

- [ ] Run full audit (Section 9.1) on VPS
- [ ] Verify no existing Docker network overlaps with chosen subnet
- [ ] Verify no host/VPN route overlaps with chosen subnet
- [ ] Verify CrowdSec bouncer systemd unit has `After=docker.service`
- [ ] Verify UFW `DEFAULT_FORWARD_POLICY` setting
- [ ] Document chosen subnet in project docs

### 10.4 Post-Creation Checklist

- [ ] Run isolation tests (Section 9.3)
- [ ] Verify CrowdSec rules intact (Section 9.5)
- [ ] Verify outbound internet access from containers
- [ ] Test rollback procedure in non-production first
- [ ] Document network details in project evidence

### 10.5 Long-Term Recommendations

1. **Set `default-address-pools` in `/etc/docker/daemon.json`** to use `/24` subnets and avoid future conflicts:

```json
{
  "default-address-pools": [
    { "base": "172.17.0.0/16", "size": 24 },
    { "base": "172.18.0.0/16", "size": 24 },
    { "base": "10.100.0.0/16", "size": 24 }
  ]
}
```

2. **After changing `daemon.json`, restart Docker** (this will NOT affect existing networks):
   ```bash
   sudo systemctl restart docker
   ```

3. **Never use the default `bridge` network** — always specify `--network`

4. **Bind published ports to `127.0.0.1`** unless external access is necessary:
   ```bash
   docker run -p 127.0.0.1:8080:8080 ...
   ```

---

## 11. References & Source URLs

### Official Docker Documentation
- [Docker Networking Overview](https://docs.docker.com/engine/network/) — Subnet allocation, default pools
- [Bridge Network Driver](https://docs.docker.com/engine/network/drivers/bridge/) — Isolation, DNS, default vs user-defined
- [Docker Network Create Reference](https://docs.docker.com/reference/cli/docker/network/create/) — CLI options, subnet, IPAM
- [Docker Network Inspect](https://docs.docker.com/reference/cli/docker/network/inspect/) — Verification commands
- [Docker & Packet Filtering Firewalls](https://github.com/docker/docs/blob/main/content/manuals/engine/network/packet-filtering-firewalls.md) — UFW incompatibility, DOCKER-USER chain
- [IPv6 Networking](https://docs.docker.com/engine/daemon/ipv6) — IPv6 on bridge networks
- [Docker Compose External Networks](https://github.com/docker/compose/blob/main/compose/pkg/e2e/fixtures/external/compose.yaml) — `external: true` pattern

### Docker + UFW + nftables
- [cr0x.net — UFW + Docker Lockdown (Case #40)](https://cr0x.net/en/ufw-docker-lockdown-compose/) — Comprehensive Ubuntu 24.04 guide
- [cr0x.net — Docker NAT/Firewall Misread](https://cr0x.net/en/docker-nat-firewall-misread/) — Packet flow deep dive
- [Virtua.cloud — Fix Docker Bypassing UFW](https://www.virtua.cloud/learn/en/tutorials/docker-ufw-firewall-fix-vps) — 4 tested solutions
- [Authon.dev — Why Docker Bypasses UFW](https://blog.authon.dev/why-docker-bypasses-ufw-and-how-to-actually-lock-it-down) — Practical configurations
- [sudowheel.com — Docker iptables Compatibility Layer](https://sudowheel.com/docker-iptables-compatibility-layer.html) — iptables-nft translation
- [sudowheel.com — Docker nftables March 2026](https://sudowheel.com/docker-nftables-march-2026.html) — Docker 29 nftables backend

### CrowdSec + Docker
- [CrowdSec Docs — Firewall Bouncer](https://docs.crowdsec.net/u/bouncers/firewall) — nftables/iptables configuration
- [cs-firewall-bouncer Issue #216](https://github.com/crowdsecurity/cs-firewall-bouncer/issues/216) — Docker startup ordering fix
- [cs-firewall-bouncer Issue #346](https://github.com/crowdsecurity/cs-firewall-bouncer/issues/346) — DOCKER-USER + IPv6
- [cs-firewall-bouncer Issue #32](https://github.com/crowdsecurity/cs-firewall-bouncer/issues/32) — Docker deployment patterns
- [GnTech Blog — CrowdSec Docker + Traefik](https://blog.gntech.me/posts/2026-05-17-crowdsec-docker-traefik-deployment/) — Full deployment guide

### Subnet Sizing & Best Practices
- [LinuxServer.io — Better Practices For Docker Networking](https://www.linuxserver.io/blog/better-practices-for-docker-networking) — /24 recommendations, `default-address-pools`
- [moby/moby Issue #50107](https://github.com/moby/moby/issues/50107) — Docker maintainer on bridge limitations (1024 ports max)
- [BetterLink Blog — Docker Network Mode Selection](https://eastondev.com/blog/en/posts/dev/20260514-docker-network-modes/) — Production recommendations
- [Philipp Mundhenk — Docker IP Addresses](https://philippmundhenk.github.io/Docker_IP_addresses/) — Address pool exhaustion, `daemon.json` fix
- [Docker Overlapping IPv4 Subnets](https://oneuptime.com/blog/post/2026-03-20-docker-overlapping-ipv4-subnets-config/view) — Collision detection

### General Docker Networking
- [Docker Bridge Network Subnet & Gateway](https://oneuptime.com/blog/post/2026-03-20-configure-docker-bridge-subnet-gateway/view) — Full IPAM configuration
- [env.dev — Docker Networking Guide](https://env.dev/guides/docker-networking) — Bridge, Host, Overlay comparison
- [MassiveGRID — Docker Networking on Ubuntu VPS](https://www.massivegrid.com/blog/docker-networking-ubuntu-vps/) — VPS-specific guide
- [Docker Network Commands](https://oneuptime.com/blog/post/2026-02-08-how-to-use-docker-network-commands-effectively/view) — CLI reference
- [Pool Overlaps Error Fix](https://errornotes.dev/en/errors/docker/fix-docker-error-pool-overlaps-with-other-one-on-this-address-space) — Diagnosis and resolution

---

## Footer

**Source Task**: STEP-P0-010 — Guinevere Docker Network Isolation  
**Date**: 2026-05-31  
**Researcher**: Guinevere (Librarian Mode)  
**Validation Method**: Cross-referenced 25+ sources including Docker official docs, CrowdSec docs, community best practices, and production deployment guides.  
**Caveats**: No VPS commands were executed. All commands in this report are for reference — verify on the target VPS before execution. The CrowdSec/Docker interaction may vary based on specific CrowdSec bouncer version and configuration.
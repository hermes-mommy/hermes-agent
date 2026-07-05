# P25 — Tailscale Endpoint Design for Dedicated VPS 9Router

**Date**: 2026-06-25  
**Status**: COMPLETE  
**Scope**: P25 Research — Tailscale network design for new VPS 9Router  
**Reference**: Existing Tailscale mesh on guinevere-vps (100.94.104.22), ADR-019

---

## 1. Executive Summary

The new dedicated VPS 9Router will be accessed exclusively via Tailscale. The operator's local machine (Windows) and the new VPS are both on the same Tailscale tailnet. Claude Code and OpenCode will connect to `http://<tailscale-ip>:20128/v1` instead of the current `http://localhost:20128/v1`. Tailscale provides WireGuard encryption, so no TLS/reverse proxy is needed. The endpoint change is a single environment variable: `OPENAI_BASE_URL`.

---

## 2. Current Tailscale Architecture

### 2.1 Existing Tailscale Mesh

| Node | Tailscale IP | Role |
|---|---|---|
| **guinevere-vps** | 100.94.104.22 | Hermes production VPS (Ubuntu 24.04) |
| **Operator local** | Assigned by Tailscale | Windows 11, Claude Code + OpenCode |

### 2.2 Existing UFW Rules (guinevere-vps)

```
ufw allow in on tailscale0 to any port 22     # SSH
ufw allow in on tailscale0 to any port 80     # HTTP
ufw allow in on tailscale0 to any port 443    # HTTPS
ufw allow in on tailscale0 to any port 3000   # Web UI
ufw allow in on tailscale0 to any port 8000   # FastAPI
ufw allow in on tailscale0 to any port 9090   # Prometheus
```

### 2.3 How Existing Services Use Tailscale

- Hermes: `base_url: http://localhost:20128/v1` (localhost, not Tailscale — Hermes is ON the VPS)
- guinevere-core: `127.0.0.1:8000` (localhost binding)
- All services bind to localhost or 127.0.0.1 — internal to the VPS

---

## 3. New VPS Tailscale Design

### 3.1 Network Topology

```
┌──────────────────────┐         Tailscale WireGuard          ┌──────────────────────┐
│   Operator Local     │ ═════════════════════════════════════ │   New VPS (P25)      │
│   (Windows 11)       │          Encrypted Tunnel            │   Ubuntu 24.04       │
│                      │                                      │                      │
│   Claude Code ───────┼──── HTTP ────────────────────────────┼── 9Router :20128     │
│   OpenCode   ────────┼──── HTTP ────────────────────────────┼── 9Router :20128     │
│                      │                                      │                      │
│   OPENAI_BASE_URL=   │                                      │   tailscale0 interface│
│   http://100.x.y.z   │                                      │   ufw: tailscale0 only│
│   :20128/v1          │                                      │                      │
└──────────────────────┘                                      └──────────────────────┘
```

### 3.2 Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Access method** | Tailscale only | No public internet exposure. ADR-019 compliance. |
| **Host binding** | `0.0.0.0` (all interfaces) | Allows Tailscale access. UFW restricts to tailscale0. |
| **Port** | 20128 | Standard 9Router port. No conflict (different VPS from Hermes). |
| **TLS** | None | Tailscale WireGuard provides end-to-end encryption. |
| **Reverse proxy** | None | Direct HTTP via Tailscale. Simpler, fewer moving parts. |
| **Auth** | None (REQUIRE_API_KEY=false) | Tailscale is the auth layer. Only tailnet members can reach the port. |
| **Dashboard access** | `http://<tailscale-ip>:20128/dashboard` | Accessible via Tailscale from operator's browser. |

---

## 4. Endpoint URL Design

### 4.1 Option A: Raw Tailscale IP (Recommended)

```
OPENAI_BASE_URL=http://100.x.y.z:20128/v1
```

- **Pros**: Simple, unambiguous, no DNS dependency
- **Cons**: Must know the IP, changes if Tailscale re-assigns
- **Note**: Tailscale IPs are stable (derived from node key) — they don't change unless the node is re-keyed

### 4.2 Option B: MagicDNS

```
OPENAI_BASE_URL=http://p25-9router.tailnet-name.ts.net:20128/v1
```

- **Pros**: Human-readable, self-documenting
- **Cons**: Requires MagicDNS to be enabled on the tailnet, depends on Tailscale DNS

### 4.3 Recommendation

**Use raw Tailscale IP as primary** with MagicDNS as a convenience alias. Both work identically and can be used interchangeably.

---

## 5. Client Connection Change

### 5.1 Current (Local 9Router)

```bash
# Claude Code and OpenCode both use:
OPENAI_BASE_URL=http://localhost:20128/v1
```

### 5.2 New (VPS 9Router)

```bash
# After VPS is provisioned and Tailscale IP is known:
OPENAI_BASE_URL=http://100.x.y.z:20128/v1

# Or with MagicDNS:
OPENAI_BASE_URL=http://p25-9router.your-tailnet.ts.net:20128/v1
```

### 5.3 Verification

```bash
# From local machine, after VPS Tailscale is up:
curl http://<tailscale-ip>:20128/api/health
# → {"ok":true}

curl http://<tailscale-ip>:20128/v1/models | jq '.data | length'
# → 24 (or whatever count is in the migrated DB)

# Test a chat completion:
curl http://<tailscale-ip>:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ds/deepseek-v4-flash","messages":[{"role":"user","content":"Say hello"}],"stream":false}'
```

---

## 6. UFW / Firewall Configuration

### 6.1 Required UFW Rules on New VPS

```bash
# Allow 9Router on Tailscale interface only
ufw allow in on tailscale0 to any port 20128 proto tcp

# Deny 9Router on all other interfaces (explicit deny)
ufw deny 20128

# Allow SSH on Tailscale for administration
ufw allow in on tailscale0 to any port 22 proto tcp

# Default deny on public interface
ufw default deny incoming
ufw default allow outgoing

# Enable UFW
ufw enable
```

### 6.2 Verification

```bash
ufw status verbose
# Should show:
# 20128/tcp    ALLOW IN    tailscale0
# 20128        DENY IN     Anywhere
# 22/tcp       ALLOW IN    tailscale0
```

### 6.3 What This Prevents

- Public internet cannot reach port 20128 (denied on eth0)
- Other Tailscale nodes can reach port 20128 (allowed on tailscale0)
- Only the operator's tailnet members can access the 9Router

---

## 7. No Reverse Proxy Rationale

### 7.1 Why No nginx/Caddy/TLS

| Concern | Why Not Needed |
|---|---|
| **TLS/HTTPS** | Tailscale WireGuard provides end-to-end encryption. The HTTP traffic is already encrypted at the network layer. |
| **Load balancing** | Single process, single VPS. No need for load balancing. |
| **Static file serving** | 9Router serves its own dashboard (Next.js). No static files to proxy. |
| **Rate limiting** | Not needed — Tailscale access is already restricted to trusted clients. |
| **WebSocket upgrade** | 9Router uses SSE, not WebSockets. SSE works over plain HTTP. |
| **Request logging** | 9Router has built-in request logging (usageHistory, requestDetails). |
| **Caching** | Not applicable — LLM responses are dynamic and shouldn't be cached. |

### 7.2 When a Reverse Proxy Would Be Needed

- If the 9Router needs to be exposed to the public internet (explicitly NOT the case for P25)
- If multiple 9Router instances need load balancing
- If TLS termination is required (not needed — Tailscale provides encryption)

---

## 8. Security Model

### 8.1 Defense in Depth

| Layer | Mechanism |
|---|---|
| **Network** | Tailscale WireGuard — only tailnet members can reach the VPS at all |
| **Interface** | UFW — only tailscale0 interface accepts port 20128 |
| **Application** | 9Router dashboard password (INITIAL_PASSWORD) |
| **API** | No API key required (REQUIRE_API_KEY=false) — Tailscale is the auth layer |

### 8.2 What's Protected

| Asset | Protection |
|---|---|
| **Provider API keys** | In SQLite database on VPS, protected by filesystem permissions (600) |
| **JWT secret** | In `/var/lib/9router/jwt-secret`, chmod 600 |
| **Dashboard access** | Password-protected + only accessible via Tailscale |
| **API access** | Only accessible via Tailscale (WireGuard auth) |
| **Data in transit** | WireGuard encryption between client and VPS |

### 8.3 What's NOT Protected (and why it's OK)

| Asset | Risk | Why It's Acceptable |
|---|---|---|
| **HTTP (not HTTPS)** | Plaintext HTTP over Tailscale | WireGuard encrypts at network layer. No eavesdropping possible. |
| **No API key on /v1** | Any tailnet member can call the API | Tailscale membership is the auth gate. Only trusted devices are on the tailnet. |

---

## 9. Isolation from Hermes/P20

### 9.1 Physical Separation

| Aspect | Hermes VPS | P25 VPS |
|---|---|---|
| **Machine** | guinevere-vps | New dedicated VPS |
| **Tailscale IP** | 100.94.104.22 | Different IP (assigned at provisioning) |
| **Port** | 20128 (localhost binding) | 20128 (0.0.0.0 binding) |
| **User** | guinevere | nine-router |
| **Systemd slice** | guinevere.slice | nine-router.slice |
| **Data directory** | /home/guinevere/.9router | /var/lib/9router |
| **Service name** | guinevere-9router.service | nine-router.service |

### 9.2 No Cross-Talk Possible

- Different VPS: different IP, different machine, different resources
- Different Tailscale IP: clients must explicitly choose which endpoint
- Different port binding: Hermes binds to 127.0.0.1 (localhost-only), P25 binds to 0.0.0.0
- Even if both were on the same VPS, they'd be on different ports/users/slices

---

## 10. Rollback Procedure

### 10.1 Rollback (to Local 9Router)

```bash
# On operator's local machine:
export OPENAI_BASE_URL=http://localhost:20128/v1

# That's it. < 1 second. No data loss.
```

### 10.2 Verification After Rollback

```bash
curl http://localhost:20128/api/health
# → {"ok":true}
```

### 10.3 What Happens to the VPS 9Router

- The VPS 9Router keeps running — it's just not being used
- No data is lost — the VPS data.sqlite is independent
- To switch back: change OPENAI_BASE_URL back to the VPS IP

---

## 11. VPS Provisioning Checklist

### 11.1 Tailscale Installation

```bash
# On new VPS (Ubuntu 24.04):
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
tailscale status
tailscale ip -4
# Note the IP: 100.x.y.z
```

### 11.2 UFW Configuration

```bash
ufw allow in on tailscale0 to any port 22 proto tcp
ufw allow in on tailscale0 to any port 20128 proto tcp
ufw deny 20128
ufw default deny incoming
ufw default allow outgoing
ufw enable
ufw status verbose
```

### 11.3 Connectivity Test

```bash
# From operator's local machine:
ping <new-vps-tailscale-ip>
# Should get replies

# After 9Router is installed and running:
curl http://<new-vps-tailscale-ip>:20128/api/health
# → {"ok":true}
```

---

## 12. Verification Commands

```bash
# === On VPS ===
# Check Tailscale is running
systemctl status tailscaled
tailscale status
tailscale ip -4

# Check 9Router is listening on all interfaces
ss -tlnp | grep 20128
# Should show: 0.0.0.0:20128 (not 127.0.0.1:20128)

# Check UFW
ufw status verbose | grep 20128

# === On Local Machine ===
# Check Tailscale connectivity
ping <vps-tailscale-ip>

# Check 9Router health
curl http://<vps-tailscale-ip>:20128/api/health

# Check models
curl http://<vps-tailscale-ip>:20128/v1/models | jq '.data | length'

# Test chat
curl http://<vps-tailscale-ip>:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ds/deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"stream":false,"max_tokens":10}'
```

---

## 13. Footer

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-06-25 | P25 Research | Tailscale endpoint design. No files modified. Based on existing Tailscale mesh configuration. |
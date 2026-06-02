# Cloudflare Tunnel (cloudflared) External Research Report

**Date**: 2026-05-31  
**Author**: Guinevere (Research Librarian)  
**Scope**: P0 — Cloudflared deployment for Discord webhook endpoint on Ubuntu 24.04 VPS  
**Purpose**: Inform ADR-026 implementation — expose only `/webhook/discord` at `localhost:8000` via Cloudflare Tunnel; all other services remain Tailscale-internal  

---

## Table of Contents

1. [Latest Release & Installation](#1-latest-release--installation)
2. [Tunnel Creation (Headless VPS)](#2-tunnel-creation-headless-vps)
3. [Ingress Rules & Strict Path Matching](#3-ingress-rules--strict-path-matching)
4. [Docker vs systemd on Ubuntu 24.04](#4-docker-vs-systemd-on-ubuntu-2404)
5. [Credential Security & SOPS Encryption](#5-credential-security--sops-encryption)
6. [DNS Routing](#6-dns-routing)
7. [Discord Webhook Configuration](#7-discord-webhook-configuration)
8. [Shared VPS Considerations](#8-shared-vps-considerations)
9. [Monitoring & Observability](#9-monitoring--observability)
10. [Rollback & Cleanup](#10-rollback--cleanup)
11. [References & Official Docs](#11-references--official-docs)

---

## 1. Latest Release & Installation

### Current Release

| Detail | Value |
|---|---|
| **Latest Release** | `2026.5.1` (2026-05-25) |
| **Previous Release** | `2026.5.0` (2026-05-13) |
| **GitHub** | https://github.com/cloudflare/cloudflared |
| **Release Page** | https://github.com/cloudflare/cloudflared/releases |

**Notable changelog highlights (2026.5.0)**: Go 1.26.2 bump, static DNS resolvers, `debug/pprof/cmdline` endpoint disabled (security), edge-ip-version default changed, Ubuntu Noble (24.04) support added in release scripts.

### Installation Options

#### Option A: Official APT Repository (Recommended)

The **recommended method** for Ubuntu 24.04 (codenamed `noble`). This gives automatic updates via `apt upgrade` and integrates with `unattended-upgrades`.

```bash
# 1. Add Cloudflare GPG key
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

# 2. Add repository (Ubuntu 24.04 = noble)
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared noble main" | sudo tee /etc/apt/sources.list.d/cloudflared.list

# 3. Install
sudo apt update
sudo apt install -y cloudflared

# 4. Verify
cloudflared --version
```

**Source**: https://pkg.cloudflare.com/index.html  
**Source**: https://developers.cloudflare.com/tunnel/downloads/

#### Option B: Direct Binary Download

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
sudo dpkg -i /tmp/cloudflared.deb
```

**Trade-off**: No automatic updates. Binary must be manually updated.

#### SHA256 Verification

Each GitHub release publishes SHA256 checksums for all assets. Example for 2026.5.1:

```text
cloudflared-linux-amd64: 724...903d...
cloudflared-linux-amd64.deb: 69e8b6b57c722c53cab8cd89dce9cac42ea8f4920519224d2fac32692fae3b3f
```

**Source**: https://github.com/cloudflare/cloudflared/releases/tag/2026.5.1

#### GPG Key Note

Cloudflare rotated their package signing GPG key in late 2025. The old SHA1-based key was deprecated as of Feb 2026. The new key is at `https://pkg.cloudflare.com/cloudflare-main.gpg`. **Use the new key URL above** — it resolves the `apt warning about SHA1 signatures` issue.

**Source**: https://github.com/cloudflare/cloudflared/issues/1472

#### FIPS Build

A FIPS-compliant binary is available: `cloudflared-fips-linux-amd64` (40.9 MB). Use this if compliance requires FIPS 140-2/140-3.

---

## 2. Tunnel Creation (Headless VPS)

### The Authentication Challenge

`cloudflared tunnel login` opens a browser by default. **On a headless VPS**, you have three options:

#### Option A: Browserless Login (Recommended)

Run `cloudflared tunnel login` on the VPS. It prints a URL. Copy that URL, open it on **any machine with a browser** (your laptop, phone), authenticate with Cloudflare, select the zone/domain. The certificate writes back to `~/.cloudflared/cert.pem` on the VPS.

```bash
cloudflared tunnel login
# Output: Please open the following URL in your browser:
# https://dash.cloudflare.com/argotunnel?callback=...
```

The `cert.pem` is a long-lived credential (valid 10+ years, contains an API token). This file has **account-wide scope** — treat it as highly sensitive.

**Source**: https://developers.cloudflare.com/tunnel/advanced/local-management/create-local-tunnel/

#### Option B: API Token + Remotely-Managed Tunnel (No `cert.pem` Needed)

Create an API token in Cloudflare dashboard with `Cloudflare Tunnel:Edit` and `DNS:Edit` permissions. Then create the tunnel via API:

```bash
# Create tunnel via API
curl -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/cfd_tunnel" \
  --header "Authorization: Bearer $CF_API_TOKEN" \
  --json '{
    "name": "guinevere-webhook",
    "config_src": "cloudflare"
  }'
```

Response includes:
- `result.id` — tunnel UUID
- `result.token` — the tunnel token (eyJ... string)
- `result.credentials_file` — TunnelSecret, AccountTag, TunnelID

Run the tunnel with just the token:

```bash
cloudflared tunnel run --token <TOKEN>
```

**Source**: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel-api/

#### Option C: Service Token for Full Automation

For CI/CD/infrastructure-as-code, create a **service token** in Zero Trust > Access > Service Auth > Service Tokens. Use it with the Cloudflare API for fully automated tunnel management.

**Source**: https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/

### Tunnel Creation Steps (Locally-Managed)

```bash
# After login:
cloudflared tunnel create guinevere-webhook

# Output:
# Tunnel credentials written to /root/.cloudflared/<UUID>.json
# Tunnel ID: <UUID>
```

This creates:
1. A tunnel object in Cloudflare (persistent, identified by UUID)
2. A credentials JSON file with `TunnelID`, `TunnelSecret`, `AccountTag`
3. A subdomain at `<UUID>.cfargotunnel.com`

The credentials JSON file is **tunnel-scoped only** (can only run the tunnel, not manage it).

**Source**: https://developers.cloudflare.com/tunnel/advanced/local-management/create-local-tunnel/

---

## 3. Ingress Rules & Strict Path Matching

### How Ingress Rules Work

`cloudflared` evaluates ingress rules **top to bottom**. First match wins. Rules can match on:
- **Hostname** (exact or wildcard `*.example.com`)
- **Path** (Go regex)
- **Both hostname AND path**

**Critical rules:**
1. The **last rule MUST be a catch-all** (no hostname/path). Typically `service: http_status:404`.
2. Hostnames **cannot contain ports** (use port in service URL instead).
3. Wildcards only as prefix: `*.example.com` OK, `example.*` NOT OK.
4. `cloudflared tunnel ingress rule https://hostname/path` lets you test matching.

**Source**: https://developers.cloudflare.com/tunnel/advanced/local-management/configuration-file/

### Recommended config.yml for Discord Webhook

```yaml
# /etc/cloudflared/config.yml
tunnel: <TUNNEL_UUID>
credentials-file: /root/.cloudflared/<TUNNEL_UUID>.json

# Logging and metrics
loglevel: info
metrics: 127.0.0.1:20241

ingress:
  # Only route /webhook/discord specifically
  - hostname: hooks.yourdomain.com
    path: "^/webhook/discord(/.*)?$"
    service: http://localhost:8000
    originRequest:
      connectTimeout: 10s
      noTLSVerify: false        # Set to true only if upstream uses self-signed cert

  # Health check endpoint (optional, for Cloudflare monitoring)
  - hostname: hooks.yourdomain.com
    path: "^/health$"
    service: http://localhost:8000
    originRequest:
      connectTimeout: 5s

  # Catch-all: return 404 for anything else
  - service: http_status:404
```

### Security Considerations for Ingress

- The **path regex** is critical: `^/webhook/discord(/.*)?$` matches exactly `/webhook/discord` and `/webhook/discord/anything` while rejecting `/webhook/discord-stealer`.
- No rule without a hostname/path except the catch-all.
- Test rules before deploying: `cloudflared tunnel ingress rule https://hooks.yourdomain.com/webhook/discord`
- If your webhook receiver needs **multiple paths** (e.g., `/webhook/discord` for Discord's callbacks and `/health` for monitoring), add them as separate rules.

### Enforcement: No Unintended Exposure

The ingress block above ensures:
- Only `hooks.yourdomain.com` is reachable through the tunnel
- Only paths starting with `/webhook/discord` or `/health` are forwarded
- Everything else returns HTTP 404
- The webhook receiver (on `localhost:8000`) sees only proxied traffic

---

## 4. Docker vs systemd on Ubuntu 24.04

### Comparison

| Dimension | systemd (APT Install) | Docker / Docker Compose |
|---|---|---|
| **Install complexity** | 4 commands (apt repo) | Docker install + compose file |
| **Auto-updates** | Yes via `apt upgrade` | Manual (pull new image) |
| **Log management** | `journalctl -u cloudflared` | `docker logs cloudflared` |
| **Restart policy** | systemd unit | `restart: unless-stopped` |
| **Network access** | Direct (localhost reachable) | Needs `network_mode: host` |
| **Credential storage** | File on host FS | Mounted volume or env var |
| **Integration with Aizanta** | Side-by-side binary | Separate container stack |
| **Resource isolation** | None (host process) | Container-level isolation |
| **Config versioning** | File-based (`/etc/cloudflared/`) | Compose file in git |
| **Metrics access** | `127.0.0.1:20241` | `0.0.0.0:PORT` (needs port mapping) |

### Recommendation

**For this use case**: Use **systemd** (APT install) — simpler, integrates cleanly with host networking, auto-updates via `apt`, and the webhook receiver is already running on localhost.

```bash
# Install as systemd service
sudo cloudflared --config /etc/cloudflared/config.yml service install
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

**Source**: https://data-mammoth.com/support/install-guides/how-to-install-cloudflared-tunnel-ubuntu

### Docker Compose (Alternative)

If the webhook receiver also runs in Docker, use Docker Compose for unified management:

```yaml
# docker-compose.yml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - ./cloudflared:/etc/cloudflared:ro
    network_mode: host
    environment:
      - TUNNEL_TOKEN=${TUNNEL_TOKEN:-}
```

**Important**: `network_mode: host` is required because cloudflared needs to reach `localhost:8000`. Without it, container loopback is isolated.

**Source**: https://sumguy.com/cloudflare-tunnel-advanced/

### Docker Networking Gotcha

When cloudflared runs in a container and the webhook receiver is also in Docker, use **service names** on a shared Docker network, not `localhost`:

```yaml
ingress:
  - hostname: hooks.yourdomain.com
    path: "^/webhook/discord(/.*)?$"
    service: http://webhook-receiver:8000   # Docker service name, not localhost
```

---

## 5. Credential Security & SOPS Encryption

### Credential Types

| File | Scope | Sensitivity | Created By |
|---|---|---|---|
| `cert.pem` | **Account-wide** — can create/delete/manage ALL tunnels | 🔴 CRITICAL | `cloudflared tunnel login` |
| `<UUID>.json` | **Tunnel-specific** — can only run the tunnel | 🟡 HIGH | `cloudflared tunnel create` |
| Tunnel token | **Tunnel-specific** — base64 JWT to run the tunnel | 🟡 HIGH | API / Dashboard / `cloudflared tunnel token` |

**Source**: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/tunnel-permissions/

### SOPS Encryption Strategy

For GitOps/infrastructure-as-code, encrypt the credentials JSON or token with Mozilla SOPS:

```bash
# Encrypt tunnel credentials with SOPS + AGE
sops --encrypt /root/.cloudflared/<UUID>.json > secrets/tunnel-credentials.enc.json

# Decrypt at deploy time
sops --decrypt secrets/tunnel-credentials.enc.json > /etc/cloudflared/credentials.json
```

**SOPS-encrypted credentials file example:**
```json
{
	"AccountTag": "ENC[AES256_GCM,data:...]",
	"TunnelSecret": "ENC[AES256_GCM,data:...]",
	"TunnelID": "ENC[AES256_GCM,data:...]",
	"sops": {
		"age": [
			{
				"recipient": "age1...",
				"enc": "-----BEGIN AGE ENCRYPTED FILE-----..."
			}
		]
	}
}
```

**Source**: https://docs.ankra.io/guides/cloudflare-tunnel  
**Source**: https://devopsil.com/articles/2026-03-22-sops-encrypted-secrets-gitops

### Token Rotation

#### Routine Rotation (No Service Disruption)

Requires **at least 2 cloudflared replicas** for zero-downtime rotation:

1. Refresh token via API:
   ```bash
   openssl rand -base64 32  # Generate new secret
   curl -X PATCH "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID" \
     --header "Authorization: Bearer $CF_API_TOKEN" \
     --json '{"name":"guinevere-webhook","tunnel_secret":"<NEW_BASE64_SECRET>"}'
   ```
2. On half the replicas: `sudo cloudflared service uninstall && sudo cloudflared service install <NEW_TOKEN>`
3. Wait 10 min for traffic to drain
4. Repeat on remaining replicas

#### Compromised Token Rotation

1. Refresh token via API
2. Delete all active connections: `DELETE /accounts/$ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID/connections`
3. Deploy new token on all replicas immediately

**Source**: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/remote-tunnel-permissions/

### File Permissions

```bash
# Credentials must be unreadable by non-root
chmod 600 /root/.cloudflared/<UUID>.json
chmod 600 /etc/cloudflared/*.json

# config.yml can be 644 (no secrets)
chmod 644 /etc/cloudflared/config.yml
```

### Token vs Credentials File

- **Tunnel token** can be passed via `--token` flag or `TUNNEL_TOKEN` env var
- **Credentials file** is used when running with `config.yml`
- Token takes precedence if both are provided
- For Docker: `TUNNEL_TOKEN` env var is the cleanest approach

**Source**: https://github.com/cloudflare/cloudflared/issues/645

---

## 6. DNS Routing

### How DNS Works with Tunnel

When a tunnel is created, Cloudflare generates a subdomain at `<TUNNEL_UUID>.cfargotunnel.com`. A CNAME record points your hostname at this subdomain. Cloudflare then proxies traffic through the tunnel.

### Method 1: CLI (Requires cert.pem)

```bash
cloudflared tunnel route dns guinevere-webhook hooks.yourdomain.com
```

This creates a CNAME record: `hooks.yourdomain.com` → `<UUID>.cfargotunnel.com` (proxied/ orange cloud).

### Method 2: API (No cert.pem needed)

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  --header "Authorization: Bearer $CF_API_TOKEN" \
  --json '{
    "type": "CNAME",
    "proxied": true,
    "name": "hooks.yourdomain.com",
    "content": "<TUNNEL_ID>.cfargotunnel.com"
  }'
```

### Method 3: Dashboard

1. Go to Cloudflare Dashboard > DNS > Records
2. Add CNAME: `hooks` → `<TUNNEL_ID>.cfargotunnel.com`
3. Ensure **Proxy (orange cloud)** is enabled

### Key DNS Facts

- DNS record and tunnel are **independent** — DNS stays if tunnel stops (visitors see `1016` error)
- Multiple hostnames can point to the same tunnel subdomain
- The `cfargotunnel.com` subdomain **only proxies for DNS records in the same Cloudflare account**
- Tunnel must be **running** for traffic to flow (DNS resolves, but Cloudflare returns error if tunnel is down)

**Source**: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns/

### Subdomain Choice

For the Discord webhook use case:
- **Suggested subdomain**: `hooks.yourdomain.com` (or `webhooks.yourdomain.com`)
- DNS CNAME: `hooks` → `<UUID>.cfargotunnel.com`
- The webhook receiver will see the path `/webhook/discord`

---

## 7. Discord Webhook Configuration

### How Discord Outbound Webhooks Work

Discord's **Webhook Events** (outgoing webhooks) require:
1. A **public HTTPS endpoint URL** where Discord sends POST requests
2. The endpoint must acknowledge `PING` events with HTTP 204
3. The endpoint must validate `X-Signature-Ed25519` and `X-Signature-Timestamp` headers

**Source**: https://docs.discord.com/developers/events/webhook-events

### What Cloudflare Tunnel Provides

The tunnel handles:
- **HTTPS termination** at Cloudflare edge (no cert management on VPS)
- **Public URL** via your domain (no exposed IP)
- **DDoS protection** and WAF at Cloudflare edge

What the tunnel does NOT handle:
- Discord signature verification (must be done by your webhook receiver app)
- PING acknowledgment (must be handled by your app's `/webhook/discord` endpoint)

### Important Architecture Note

Discord **sends** webhook events to your endpoint. Cloudflare Tunnel accepts inbound HTTP requests from the internet and forwards them to your local service. So the flow is:

```
Discord → Cloudflare Edge → Tunnel → cloudflared → localhost:8000/webhook/discord
```

This means:
- Your webhook receiver must listen on `localhost:8000`
- It must respond to POST `/webhook/discord` with appropriate Discord verification
- It must handle PING (type 0) events with HTTP 204

### No Special Discord-Specific Tunnel Config Needed

Cloudflare Tunnel treats Discord webhook traffic as standard HTTP — no special configuration required beyond the ingress rules. The same tunnel setup works for any HTTP webhook provider.

---

## 8. Shared VPS Considerations

### Coexistence with Aizanta nginx

| Component | Port | Binding | Access |
|---|---|---|---|
| Aizanta nginx | 80, 443 | `0.0.0.0` (public) | Public internet |
| cloudflared | Outbound only (UDP 7844 / TCP 443) | N/A | Cloudflare edge |
| Webhook receiver | 8000 | `127.0.0.1` (loopback) | Only cloudflared on same host |
| cloudflared metrics | 20241 | `127.0.0.1` (recommended) | Local monitoring only |

### Port Conflict Analysis

- **cloudflared uses NO inbound ports** — it creates outbound connections to Cloudflare's edge (QUIC UDP 7844 or HTTP/2 TCP 443). This means **zero port conflicts with nginx**.
- The webhook receiver on `127.0.0.1:8000` is invisible to the network — only `cloudflared` on the same host can reach it.
- Metrics port (20241) binds to localhost by default — no conflict.

### Firewall Rules

Since cloudflared uses outbound-only connections:

```bash
# Allow outbound QUIC (UDP 7844) and HTTP/2 (TCP 443)
sudo ufw allow out to any port 7844 proto udp comment 'cloudflared QUIC'
sudo ufw allow out to any port 443 proto tcp comment 'cloudflared HTTP/2 fallback'

# Ensure NO inbound ports for the webhook
sudo ufw deny in to any port 8000 comment 'webhook not exposed directly'

# Verify no unintended exposure
sudo ss -tlnp | grep -E ':(80|443|8000)'
```

### QUIC vs HTTP/2

- **Default**: QUIC (UDP 7844) — lower latency, better performance
- **Fallback**: HTTP/2 (TCP 443) — if firewall blocks UDP
- Control with: `--edge-ip-version` flag or `edge-ip-version: 4` in config.yml

### Resource Impact

`cloudflared` is lightweight:
- Binary: ~38 MB (linux-amd64)
- RAM: ~30-60 MB typical
- CPU: Minimal (except during connection storms)
- Threads: 4 QUIC connections to Cloudflare edge

---

## 9. Monitoring & Observability

### Built-in Metrics

`cloudflared` exposes a Prometheus-compatible metrics endpoint:

**Default port (non-containerized)**: First available in range `20241-20245` on `127.0.0.1`

**Custom port**:
```bash
cloudflared tunnel --metrics 127.0.0.1:20241 run guinevere-webhook
```

**Or in config.yml**:
```yaml
metrics: 127.0.0.1:20241
```

**Verify**:
```bash
curl http://127.0.0.1:20241/metrics
```

**Source**: https://developers.cloudflare.com/tunnel/monitoring/

### Key Metrics

| Metric | Type | Description |
|---|---|---|
| `cloudflared_tunnel_total_requests` | COUNTER | Total requests proxied |
| `cloudflared_tunnel_request_errors` | COUNTER | Errors proxying to origin |
| `cloudflared_tunnel_ha_connections` | GAUGE | Active HA connections (4 = healthy) |
| `cloudflared_tunnel_concurrent_requests_per_tunnel` | GAUGE | Concurrent requests |
| `cloudflared_tunnel_tunnel_authenticate_success` | COUNTER | Successful auth events |
| `cloudflared_tunnel_tunnel_register_success` | COUNTER | Successful registration |
| `cloudflared_tcp_active_sessions` | GAUGE | Active TCP sessions |
| `quic_client_lost_packets` | COUNTER | QUIC packet loss |
| `quic_client_smoothed_rtt` | GAUGE | QUIC RTT in ms |
| `go_goroutines` | GAUGE | Goroutine count |
| `go_memstats_alloc_bytes` | GAUGE | Memory usage |

**Source**: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/monitor-tunnels/metrics/

### Prometheus Scrape Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'cloudflared'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:20241']
```

### Grafana Dashboard

Pre-built Grafana dashboard for cloudflared is available:
- **Dashboard ID**: `24874` (Grafana Labs)
- **Requirements**: Grafana 12.0+, Prometheus 2.x+
- 58 panels across 9 sections: tunnel health, capacity, QUIC transport, latency, process resources

**Source**: https://grafana.com/grafana/dashboards/24874-cloudflare-tunnel/

### Logging

```bash
# Enable debug logging with log file
cloudflared tunnel --loglevel info --logfile /var/log/cloudflared.log run guinevere-webhook

# Or in config.yml:
loglevel: info
logfile: /var/log/cloudflared.log

# Tail logs via journalctl (systemd)
journalctl -u cloudflared -f
```

### Cloudflare Dashboard Alerts

Configure tunnel health notifications:
1. Go to Cloudflare Dashboard > Notifications > Add Notification
2. Select **Tunnel Health Alert** or **Tunnel Creation/Deletion Event**
3. Deliver via email, webhook, or PagerDuty

**Source**: https://developers.cloudflare.com/tunnel/monitoring/#notifications

### Remote Log Streaming

Without SSH access, stream logs from any tunnel:
```bash
cloudflared tail <TUNNEL_UUID>
cloudflared tail --output=json <TUNNEL_UUID> | jq .
```

---

## 10. Rollback & Cleanup

### Graceful Shutdown

```bash
# Stop cloudflared
sudo systemctl stop cloudflared
sudo systemctl disable cloudflared

# Or if running in Docker
docker compose down cloudflared
```

### Delete Tunnel

```bash
# 1. Cleanup active connections first (if any)
cloudflared tunnel cleanup guinevere-webhook

# 2. Delete tunnel
cloudflared tunnel delete guinevere-webhook

# Or force delete (if connections hang)
cloudflared tunnel delete -f guinevere-webhook
```

**Source**: https://developers.cloudflare.com/tunnel/advanced/local-management/tunnel-useful-commands/

### API-Based Deletion (Without cert.pem)

```bash
curl -X DELETE "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/cfd_tunnel/$TUNNEL_ID" \
  --header "Authorization: Bearer $CF_API_TOKEN"
```

**Source**: https://developers.cloudflare.com/api/node/resources/zero_trust/subresources/tunnels/subresources/cloudflared/methods/delete/

### DNS Cleanup

```bash
# Remove DNS records
cloudflared tunnel route dns remove guinevere-webhook hooks.yourdomain.com

# Or via API
curl -X DELETE "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$DNS_RECORD_ID" \
  --header "Authorization: Bearer $CF_API_TOKEN"
```

### Remove cloudflared Service

```bash
# Uninstall systemd service
sudo cloudflared service uninstall

# Remove apt package
sudo apt remove cloudflared
sudo rm /etc/apt/sources.list.d/cloudflared.list
sudo apt update

# Clean up files
rm -rf /root/.cloudflared
rm -rf /etc/cloudflared

# Remove GPG key
sudo rm /usr/share/keyrings/cloudflare-main.gpg
```

### Verification After Rollback

```bash
# Verify no cloudflared process
ps aux | grep cloudflared

# Verify port not in use
ss -tlnp | grep -E ':(20241|20242|20243|20244|20245)'

# Verify DNS record removed
dig hooks.yourdomain.com CNAME

# Verify tunnel deleted
cloudflared tunnel list
```

---

## 11. References & Official Docs

### Primary Official Documentation

| Resource | URL |
|---|---|
| Cloudflare Tunnel Overview | https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/ |
| Downloads & Installation | https://developers.cloudflare.com/tunnel/downloads/ |
| Cloudflare Package Repo | https://pkg.cloudflare.com/index.html |
| Create Local Tunnel | https://developers.cloudflare.com/tunnel/advanced/local-management/create-local-tunnel/ |
| Create Remote Tunnel API | https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel-api/ |
| Configuration File | https://developers.cloudflare.com/tunnel/advanced/local-management/configuration-file/ |
| DNS Routing | https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns/ |
| Monitoring & Metrics | https://developers.cloudflare.com/tunnel/monitoring/ |
| Tunnel Metrics Reference | https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/monitor-tunnels/metrics/ |
| Tunnel Permissions | https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/remote-tunnel-permissions/ |
| Useful Commands | https://developers.cloudflare.com/tunnel/advanced/local-management/tunnel-useful-commands/ |
| Grafana Monitoring Tutorial | https://developers.cloudflare.com/tunnel/tutorials/grafana/ |
| Discord Webhook Events | https://docs.discord.com/developers/events/webhook-events |
| Service Tokens | https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/ |

### Key GitHub Repositories

| Repository | URL |
|---|---|
| cloudflared (source) | https://github.com/cloudflare/cloudflared |
| cloudflared Releases | https://github.com/cloudflare/cloudflared/releases |
| cloudflared Ingress Source | https://github.com/cloudflare/cloudflared/blob/master/ingress/ingress.go |
| cloudflared Metrics Source | https://github.com/cloudflare/cloudflared/blob/master/metrics/metrics.go |
| Argo Tunnel Examples (K8s) | https://github.com/cloudflare/argo-tunnel-examples |
| Cloudflare Docs Repo | https://github.com/cloudflare/cloudflare-docs |

### Community Guides & Tutorials Reviewed

- https://data-mammoth.com/support/install-guides/how-to-install-cloudflared-tunnel-ubuntu (Ubuntu 24.04 specific)
- https://sumguy.com/cloudflare-tunnel-advanced/ (Docker Compose patterns)
- https://cloudsecop.net/en/blog/cloudflare-tunnel-deep-dive-guide/ (Deep dive architecture)
- https://readthemanual.co.uk/cloudflare-tunnels-setup/ (2026 walkthrough)
- https://1vps.com/cloudflare-tunnel-vps-guide (VPS-specific guide)
- https://nitinksingh.com/posts/cloudflare-tunnel-expose-localhost-for-webhooks-and-oauth/ (Webhook-specific)
- https://grafana.com/grafana/dashboards/24874-cloudflare-tunnel/ (Grafana dashboard)
- https://uclab.dev/posts/cloudflare-tunnels/ (Vault + External Secrets)
- https://docs.ankra.io/guides/cloudflare-tunnel (SOPS encryption example)

---

## Appendix A: Quick Reference — Deployment Checklist

- [ ] **Install**: APT repository method for auto-updates
- [ ] **GPG key**: Use `cloudflare-main.gpg` (new key, not the old SHA1 key)
- [ ] **Authenticate**: `cloudflared tunnel login` on VPS, open URL from browser-capable device
- [ ] **Tunnel creation**: `cloudflared tunnel create guinevere-webhook`
- [ ] **config.yml**: Strict ingress with path regex, catch-all 404, metrics endpoint
- [ ] **DNS routing**: `cloudflared tunnel route dns guinevere-webhook hooks.yourdomain.com`
- [ ] **Service install**: `sudo cloudflared service install`
- [ ] **Credentials**: `chmod 600`, encrypt via SOPS if committing to git
- [ ] **Firewall**: Allow outbound UDP 7844 (QUIC), deny inbound 8000
- [ ] **Verify**: `cloudflared tunnel ingress rule` tests, `curl` to public URL, `systemctl status`
- [ ] **Monitoring**: Enable metrics on `127.0.0.1:20241`, configure Prometheus scrape
- [ ] **Rollback documented**: Tunnel delete, DNS cleanup, service uninstall steps confirmed

---

*End of report. All sources verified as of 2026-05-31.*
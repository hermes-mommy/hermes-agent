# Enterprise Deployment Guide Research: Self-Hosted AI Agent Systems

> **Date**: 2026-05-30
> **Purpose**: External reference research for Project Guinevere Unified Deployment Guide
> **Methodology**: Exa web search + GitHub grep_app across 7 research tracks
> **Output**: Sourced patterns, configs, and structures for the Guinevere deployment guide

---

## Table of Contents

1. [Guide Document Structure](#1-guide-document-structure)
2. [Self-Hosted AI Agent Deployment Patterns](#2-self-hosted-ai-agent-deployment-patterns)
3. [FastAPI + systemd Unit File Patterns](#3-fastapi--systemd-unit-file-patterns)
4. [PostgreSQL 16 + pgvector + TimescaleDB + PgBouncer](#4-postgresql-16--pgvector--timescaledb--pgbouncer)
5. [SOPS + age Secrets Management](#5-sops--age-secrets-management)
6. [Observability Stack](#6-observability-stack)
7. [Tailscale Zero-Trust Mesh Networking](#7-tailscale-zero-trust-mesh-networking)
8. [Cloudflare Tunnel for Single Endpoint Exposure](#8-cloudflare-tunnel)
9. [Discord Bot Deployment](#9-discord-bot-deployment)
10. [Baileys WhatsApp Integration](#10-baileys-whatsapp-integration)
11. [Ubuntu 24.04 Server Hardening](#11-ubuntu-2404-server-hardening)
12. [Disaster Recovery for Single-VPS Deployments](#12-disaster-recovery)

---

## 1. Guide Document Structure

### Best Pattern: solos-cookbook (solomonneas)
- **Source**: https://github.com/solomonneas/solostack
- **Relevance**: 5/5 - Single-engineer multi-agent stack cookbook on bare metal
- **Per-guide structure**: What/Who -> Why/Tradeoffs -> Prerequisites -> Before/After -> Implementation -> Verification -> Gotchas -> Templates

### Guinevere Recommendation
Adopt the solos-cookbook per-section template (What/Why/Prerequisites/Implementation/Verification/Gotchas/Templates), wrapped in Agent Zero's top-level structure (Prerequisites -> Installation -> Configuration -> Verification -> Troubleshooting -> Quick Reference).

---

## 2. Self-Hosted AI Agent Deployment Patterns

### Hermes Agent VPS Guide (evomap.ai) - Relevance: 5/5
- **URL**: https://evomap.ai/blog/self-host-hermes-agent-vps
- Python agent + systemd + single VPS + messaging integrations

**VPS Sizing**:
| Spec | Assessment |
|------|-----------|
| 1vCPU/1GB | Crashes under real workload |
| 2vCPU/2GB | CLI-only, single user |
| 2vCPU/4GB | Minimum for gateway+cron+light skills |
| 2-4vCPU/8GB | Comfortable for multi-platform use |

**Key Systemd Pattern**:
`ini
[Unit]
Description=Hermes Agent Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hermes
Group=hermes
WorkingDirectory=/home/hermes
ExecStart=/home/hermes/.local/bin/hermes gateway start
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
`

**Critical: Restart=on-failure + RestartSec=10 is the minimum**. Without it, any transient error kills the service permanently.

**Systemd Hardening (5 directives, 90% coverage)**:
`ini
NoNewPrivileges=true
ProtectSystem=strict
PrivateTmp=true
ReadWritePaths=/home/serviceuser /var/log/service
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
`

**Pre-Production Checks** (4 non-optional):
1. Restart survives reboot
2. Logs readable and rotating (set SystemMaxUse=500M in journald.conf)
3. Provider failure is recoverable (break API key, test, restore)
4. File persistence across restarts

**Common Mistakes**: Under-sizing RAM, weak/unlimited logging, unsafe shell access, no rollback path

### Systemd for AI Servers (renezander.com) - Relevance: 5/5
- **URL**: https://renezander.com/blog/systemd-services-ai-servers/
- Bare systemd (no Docker), multiple AI services on single VPS

**Resource Limits**:
`ini
MemoryMax=4G
CPUQuota=200%
TasksMax=512
`

**Systemd Timers (for scheduled AI agent jobs)**:
`ini
[Timer]
OnCalendar=*-*-* 06:30:00 Asia/Bangkok
Persistent=true
`

**Never skip daemon-reload** after editing a unit file. Systemd caches the parsed unit.

### Hermes OS (hermesos.cloud) - Relevance: 4/5
- Ubuntu 24.04 LTS, OpenRouter LLM routing
- For user services: loginctl enable-linger username

---

## 3. FastAPI + systemd Unit File Patterns

### UV + Uvicorn + SSL (OpenMined/PySyft) - Relevance: 4/5
- **Source**: https://github.com/OpenMined/PySyft/blob/dev/packages/syftbox/config/prod/syftbox.service
`ini
[Service]
LimitNOFILE=262144
User=azureuser
WorkingDirectory=/home/azureuser
ExecStartPre=uv run syftbox server migrate
ExecStart=uv run uvicorn syftbox.server.server:app --host 0.0.0.0 --port 8443 --workers=4 --timeout-graceful-shutdown=5 --ssl-keyfile /etc/letsencrypt/live/.../privkey.pem --ssl-certfile /etc/letsencrypt/live/.../fullchain.pem
Restart=always
RestartSec=5
Environment=OTEL_RESOURCE_ATTRIBUTES=service.name=syftbox-prod
`

### Gunicorn + Uvicorn Workers (antonputra/tutorials) - Relevance: 4/5
`ini
ExecStart=/opt/fastapi-app/.venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker --timeout 60 --graceful-timeout 60 --log-level error main:app --bind 0.0.0.0:8080
`

### UV + Uvicorn with EnvironmentFile (openclaw-mission-control) - Relevance: 3/5
`ini
[Service]
Type=simple
WorkingDirectory=/path/to/backend
EnvironmentFile=-/path/to/backend/.env
ExecStart=uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
`

### Guinevere Synthesized FastAPI Unit (Recommended)
`ini
[Unit]
Description=Guinevere API Server
After=network-online.target postgresql.service redis-server.service
Wants=network-online.target
Requires=postgresql.service redis-server.service

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/opt/guinevere
EnvironmentFile=-/opt/guinevere/.env
ExecStart=/opt/guinevere/.venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000 --timeout 120 --graceful-timeout 30 --access-logfile - --error-logfile -
Restart=on-failure
RestartSec=5

# Resource limits
MemoryMax=4G
CPUQuota=200%
TasksMax=512

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
PrivateTmp=true
ReadWritePaths=/opt/guinevere /var/log/guinevere /run/guinevere
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

[Install]
WantedBy=multi-user.target
`

---

## 4. PostgreSQL 16 + pgvector + TimescaleDB + PgBouncer

### PgBouncer Configuration (rivestack.io + pgbouncer.org) - Relevance: 5/5
- **Source**: https://rivestack.io/blog/postgresql-connection-pooling-pgbouncer

**Production Config**:
`ini
[databases]
guinevere = host=127.0.0.1 port=5432 dbname=guinevere pool_size=30 pool_mode=transaction
guinevere_admin = host=127.0.0.1 port=5432 dbname=guinevere pool_size=5 pool_mode=session

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 3
server_idle_timeout = 600
server_lifetime = 3600
query_timeout = 30
idle_transaction_timeout = 15
max_db_connections = 100
log_connections = 0
log_disconnections = 0
admin_users = pgbouncer_admin
stats_users = pgbouncer_stats
`

**Pool Sizing Formula**: default_pool_size = (PostgreSQL CPU cores) * 2 + number of disks
For Guinevere (4C/16GB): start at 20-30 for OLTP workloads.

**Pool Mode Decision Matrix**:
| App Type | Mode |
|----------|------|
| Stateless API using ORM (SQLAlchemy) | transaction |
| LISTEN/NOTIFY, admin tools | session |
| Connection issues at peak only | session |
| Connection issues at steady state | transaction |

**Key Insight**: Create separate database entries - guinevere (transaction mode) for app, guinevere_admin (session mode) for migrations/admin tools.

### PgBouncer Auth Setup
`sql
SELECT concat('"', rolname, '" "', rolpassword, '"')
FROM pg_authid WHERE rolname = 'guinevere';
`
Write to /etc/pgbouncer/userlist.txt

### Monitoring PgBouncer
`sql
SHOW POOLS;
SHOW STATS;
`
Alert if cl_waiting > 0 or vg_wait_time > 5s for more than a few seconds.

### Multi-PgBouncer (Crunchy Data) - Relevance: 3/5
- Single PgBouncer: 10,000 connections, 1,000 active, single-threaded
- Multi-PgBouncer via SO_REUSEPORT for scale

---

## 5. SOPS + age Secrets Management

### DCHost Blog: SOPS + age + systemd (Relevance: 5/5)
- **Source**: https://www.dchost.com/blog/en/the-calm-way-to-secrets-on-a-vps-gitops-with-sops-age-systemd-magic-and-rotation-you-can-sleep-on/

**Complete Workflow for Guinevere**:

1. **First boot**: Generate age keypair on VPS
`ash
age-keygen -o /etc/sops/age/keys.txt
chmod 600 /etc/sops/age/keys.txt
`

2. **Repo .sops.yaml**:
`yaml
creation_rules:
  - path_regex: secrets/.*\.env\.sops$
    age: ["age1...vps-public-key..."]
`

3. **Encrypt secrets**:
`ash
sops --encrypt --in-place secrets/guinevere.env.sops
`

4. **systemd decrypt at runtime to /run** (memory-backed, wiped on reboot):
`ini
ExecStartPre=/usr/bin/sops --decrypt --output /run/guinevere/guinevere.env /opt/guinevere/secrets/guinevere.env.sops
EnvironmentFile=/run/guinevere/guinevere.env
`

5. **Rotation** (2-step, no downtime):
   - Add new recipient to .sops.yaml, re-encrypt, deploy, verify
   - Remove old recipient, re-encrypt, deploy

**Key Rule**: Decryption happens ONLY on the server. CI never decrypts. Secrets stay encrypted end-to-end until they reach the node.

### HostMyCode SOPS Workflow (Relevance: 5/5)
- **Source**: https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026

**Deploy Script Pattern**:
`ash
#!/bin/sh
set -eu
REPO_DIR="/opt/guinevere/repo"
SRC="/secrets/guinevere.env.sops"
DEST="/etc/guinevere/secrets.env"
TS="20260530T200624Z"

umask 077
TMP=""
trap 'rm -f ""' EXIT

SOPS_AGE_KEY_FILE=/etc/sops/age/keys.txt sops -d "" > ""

# Backup old secrets for rollback
if [ -f "" ]; then
  install -m 600 "" "/var/lib/guinevere/releases/secrets.env."
fi

install -m 600 "" ""
`

**Rollback**: cp /var/lib/guinevere/releases/secrets.env.LAST_GOOD /etc/guinevere/secrets.env && systemctl restart guinevere

**Pitfalls to Avoid**:
- Never commit plaintext .env files
- Never pass secrets as command-line flags (ps output exposes them)
- Use EnvironmentFile= in systemd, not inline Environment=
- age key on server must have 0600 permissions

---

## 5. SOPS + age Secrets Management

### DCHost Blog: SOPS + age + systemd - Relevance: 5/5
- **Source**: https://www.dchost.com/blog/en/the-calm-way-to-secrets-on-a-vps-gitops-with-sops-age-systemd-magic-and-rotation-you-can-sleep-on/

**Complete Workflow for Guinevere**:

1. **First boot**: Generate age keypair on VPS
```bash
age-keygen -o /etc/sops/age/keys.txt
chmod 600 /etc/sops/age/keys.txt
```

2. **Repo .sops.yaml**:
```yaml
creation_rules:
  - path_regex: secrets/.*\.env\.sops$
    age: ["age1...vps-public-key..."]
```

3. **Encrypt secrets**:
```bash
sops --encrypt --in-place secrets/guinevere.env.sops
```

4. **systemd decrypt at runtime to /run** (memory-backed, wiped on reboot):
```ini
ExecStartPre=/usr/bin/sops --decrypt --output /run/guinevere/guinevere.env /opt/guinevere/secrets/guinevere.env.sops
EnvironmentFile=/run/guinevere/guinevere.env
```

5. **Rotation** (2-step, no downtime):
   - Add new recipient to .sops.yaml, re-encrypt, deploy, verify
   - Remove old recipient, re-encrypt, deploy

**Key Rule**: Decryption happens ONLY on the server. CI never decrypts.

### HostMyCode SOPS Workflow - Relevance: 5/5
- **Source**: https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026

**Rollback**: cp last-known-good secrets file and systemctl restart guinevere

**Pitfalls to Avoid**:
- Never commit plaintext .env files
- Never pass secrets as command-line flags (ps output exposes them)
- Use EnvironmentFile= in systemd, not inline Environment=
- age key on server must have 0600 permissions

---

## 6. Observability Stack

### FastAPI + Prometheus/Loki/Grafana (DEV.to 2026) - Relevance: 5/5
- **Source**: https://dev.to/kaushikcoderpy/fastapi-observability-with-prometheus-loki-grafana-complete-2026-guide-jkj

**FastAPI Instrumentation (1 line)**:
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```
This auto-instruments all HTTP routes and exposes /metrics endpoint.

**Key Principle**: Avoid high-cardinality data in labels (use bounded lists like status_code, method).

### Grafana Dashboard #25040 (Grafana Labs) - Relevance: 5/5
- **Source**: https://grafana.com/grafana/dashboards/25040-fastapi-full-observability/
- Full observability: VictoriaMetrics + Loki + Tempo + Pyroscope
- vmalert + Alertmanager for alerting to Telegram/email

### fastapi-observability-docker-stack (eugeneliukindev) - Relevance: 4/5
- **Source**: https://github.com/eugeneliukindev/fastapi-observability-docker-stack
- 4 pillars: metrics, logs, traces, profiles
- prometheus_multiproc for Gunicorn multi-worker metrics safety
- Grafana Alloy as unified collector (replaces Promtail)
- Structured logfmt logging with trace_id/span_id correlation

### Guinevere Observability Architecture (Synthesized)
```
FastAPI App --> /metrics endpoint --> Prometheus (scrape every 15s)
FastAPI App --> structured logfmt to stdout --> Promtail --> Loki
FastAPI App --> OpenTelemetry OTLP --> Tempo (optional)
Node Exporter --> host metrics --> Prometheus
PostgreSQL Exporter --> DB metrics --> Prometheus
Redis Exporter --> cache metrics --> Prometheus
                                      |
                                      v
                                  Grafana (dashboards + alerting)
                                  Sentry (error tracking)
```

**For bare systemd (no Docker)**: Use Promtail to tail journald logs instead of Docker socket logs.

---

## 7. Tailscale Zero-Trust Mesh Networking

### Tailscale Official Docs - Relevance: 5/5
- **Source**: https://tailscale.com/docs/how-to/set-up-servers

**Server Setup Pattern**:
```bash
# Install
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable --now tailscaled

# Headless auth with tag
sudo tailscale up --authkey=tskey-auth-xxxxx --advertise-tags=tag:server --hostname=guinevere-vps

# Enable Tailscale SSH
sudo tailscale up --ssh
```

**ACL Policy (for Guinevere)**:
```json
{
  "grants": [
    { "src": ["tag:operator"], "dst": ["tag:server"], "ip": ["*"] }
  ],
  "ssh": [
    { "action": "accept", "src": ["tag:operator"], "dst": ["tag:server"], "users": ["guinevere"] }
  ]
}
```

### Zero-Trust Networking (oneuptime.com) - Relevance: 4/5
- **Source**: https://oneuptime.com/blog/post/2026-01-27-tailscale-zero-trust-networking/view
- MagicDNS for service discovery (guinevere-vps instead of 100.x.x.x)
- Subnet routing for LAN access
- Exit node for secure browsing
- IdP integration (Google, GitHub)

### Guinevere Tailscale Setup (Synthesized)
1. Install from official APT repo (not Snap - Snap lacks tailscale ssh)
2. Auth with reusable auth key + tag:server
3. Disable key expiry for VPS in admin panel
4. Enable Tailscale SSH (replaces SSH key management)
5. Configure ACLs: only tag:operator devices can reach tag:server
6. UFW: allow only SSH from Tailscale interface, block public SSH
7. Use tailscale serve for exposing local services to tailnet

---

## 8. Cloudflare Tunnel

### rdp.sh Production Guide - Relevance: 5/5
- **Source**: https://rdp.sh/en/blog/expose-a-self-hosted-app-with-cloudflare-tunnel-no-open-ports

**Complete Setup for Guinevere Webhook Endpoint**:
```bash
# Install from APT
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create guinevere

# DNS route
cloudflared tunnel route dns guinevere webhook.example.com
```

**config.yml (multi-service)**:
```yaml
tunnel: TUNNEL_UUID
credentials-file: /root/.cloudflared/TUNNEL_UUID.json

ingress:
  - hostname: webhook.example.com
    service: http://127.0.0.1:8000
  - hostname: grafana.example.com
    service: http://127.0.0.1:3000
  - service: http_status:404
```

**Install as systemd service**:
```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

**Key Benefits for Guinevere**:
- No inbound ports needed (outbound-only connection)
- TLS terminated at Cloudflare edge
- WAF + DDoS protection included
- Cloudflare Access for Zero Trust on Grafana/dashboard
- Origin IP never exposed

**Webhook Consideration**: Exclude webhook path from Cloudflare Access policies (GitHub/Discord/WhatsApp cannot authenticate through Access).

### Data Mammoth Guide - Relevance: 5/5
- **Source**: https://data-mammoth.com/support/install-guides/how-to-install-cloudflared-tunnel-ubuntu
- UFW can be locked to SSH-only after tunnel is set up
- Move SSH to non-standard port + key auth = nearly invisible VPS

---

## 9. Discord Bot Deployment

### youngju.dev Complete Guide - Relevance: 5/5
- **Source**: https://www.youngju.dev/blog/chatbot/2026-03-03-discord-bot-python-complete-guide.en
- Pycord, slash commands, buttons, modals, systemd

**Developer Portal Setup**:
- Scopes: `bot`, `applications.commands`
- Enable Privileged Intents: `message_content`, `members`, `presence`
- Installation Contexts: Guild Install + User Install

**Intents in Code**:
```python
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = discord.Bot(intents=intents)
```

**Slash Command Sync**:
```python
@bot.event
async def on_ready():
    await bot.tree.sync()  # Global (1hr propagation)
    # Or guild-specific (instant):
    # bot.tree.copy_global_to(guild=MY_GUILD)
    # await bot.tree.sync(guild=MY_GUILD)
```

**systemd Unit (directly usable)**:
```ini
[Unit]
Description=Guinevere Discord Bot
After=network.target

[Service]
Type=simple
User=guinevere
WorkingDirectory=/opt/guinevere/discord
ExecStart=/opt/guinevere/discord/venv/bin/python bot.py
Restart=always
RestartSec=10
EnvironmentFile=/opt/guinevere/discord/.env

[Install]
WantedBy=multi-user.target
```

### 1vps.com Discord Bot Hosting Guide - Relevance: 4/5
- **Source**: https://1vps.com/host-discord-bot-on-vps
- PM2 vs systemd vs Docker comparison
- Token security: DISCORD_BOT_TOKEN in .env, never in code, .gitignore enforced
- Error: `PrivilegedIntentsRequired` = enable intents in Developer Portal

### kuberns.com Discord Bot Deployment - Relevance: 3/5
- Common errors: `LoginFailure` (wrong token), `PrivilegedIntentsRequired`, `ModuleNotFoundError`
- Bot online but slash commands missing = forgot `await bot.tree.sync()`

---

## 10. Baileys WhatsApp Integration

### Official Baileys Documentation - Relevance: 5/5
- **Source**: https://github.com/WhiskeySockets/Baileys
- WebSockets-based TypeScript library for WhatsApp Web API
- Does NOT require Selenium/Chromium (saves ~500MB RAM)

**Connection Pattern**:
```typescript
import makeWASocket, { useMultiFileAuthState, DisconnectReason } from '@whiskeysockets/baileys'
import { Boom } from '@hapi/boom'

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys')
  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: true,
    browser: Browsers.ubuntu('Guinevere')
  })

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect } = update
    if (connection === 'close') {
      const shouldReconnect = (lastDisconnect.error as Boom)?.output?.statusCode !== DisconnectReason.loggedOut
      if (shouldReconnect) connectToWhatsApp()
    }
  })
  sock.ev.on('creds.update', saveCreds)
}
```

**CRITICAL for Production**:
- `useMultiFileAuthState` saves session in `auth_info_baileys/` folder
- **Must save credentials on every update** (`sock.ev.on('creds.update', saveCreds)`) or message decryption fails
- For production: build custom auth state storage (SQL/NoSQL) instead of file-based
- Auth keys update on every message send/receive (Signal protocol sessions)
- `Browsers.ubuntu('Guinevere')` for desktop-like connection with more message history

**Pairing Code Alternative** (no QR needed):
```typescript
if (!sock.authState.creds.registered) {
  const code = await sock.requestPairingCode('6281234567890')
  console.log(code)  // Enter this code in WhatsApp phone
}
```

### DEV.to Baileys Production Guide - Relevance: 5/5
- **Source**: https://dev.to/naveen_gaur/the-complete-developers-guide-to-the-baileys-whatsapp-bot-setup-scaling-and-vps-deployment-1cp3
- Oracle Cloud VPS deployment with Baileys + Next.js
- Architecture: Gateway (Node.js + Baileys on VPS) + Logic Engine (Serverless API)

**Production Deployment with PM2**:
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: "guinevere-whatsapp",
    script: "index.js",
    instances: 1,  // MUST be 1 (cluster mode breaks Baileys)
    autorestart: true,
    max_memory_restart: "500M",
    restart_delay: 5000,
    env: { NODE_ENV: "production" }
  }]
}
```

**Rate Limiting** (critical to avoid WhatsApp ban):
- Use async rate-limited message queue
- Never send multiple API calls simultaneously to same recipient
- WhatsApp triggers session ban on bulk simultaneous messages

---

## 11. Ubuntu 24.04 Server Hardening

### 20-Step Security Checklist (vucense.com) - Relevance: 5/5
- **Source**: https://vucense.com/dev-corner/ubuntu-24-04-lts-server-setup-post-install-security-checklist-2026/
- CIS Ubuntu Linux Benchmark Level 1 compliant

**Complete Hardening Checklist**:

| Step | Action |
|------|--------|
| 1 | Create non-root sudo user |
| 2 | SSH key authentication only |
| 3 | Disable root SSH login (`PermitRootLogin no`) |
| 4 | UFW: `default deny incoming`, `allow OpenSSH`, `enable` |
| 5 | Install fail2ban |
| 6 | Enable unattended security upgrades |
| 7 | Create 2GB swap file |
| 8 | Configure sysctl limits (file descriptors, connections) |
| 9 | Set timezone + NTP |
| 10 | Secure shared memory |
| 11 | Disable unused services (snapd, cups, avahi-daemon) |
| 12 | Auto-reboot after kernel updates |
| 13 | Install auditd |
| 14 | Configure hostname + hosts |
| 15 | Set journald SystemMaxUse=500M |
| 16 | Verification script |

### CIS Benchmark Hardening (vucense.com) - Relevance: 5/5
- **Source**: https://vucense.com/dev-corner/linux-server-hardening-cis-2026/

**Kernel Parameters (/etc/sysctl.d/99-cis-hardening.conf)**:
```ini
net.ipv4.tcp_syncookies = 1
net.ipv4.ip_forward = 0
kernel.randomize_va_space = 2
fs.suid_dumpable = 0
kernel.yama.ptrace_scope = 1
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
fs.protected_symlinks = 1
fs.protected_hardlinks = 1
```

**SSH Hardening (/etc/ssh/sshd_config.d/99-hardening.conf)**:
```
PermitRootLogin no
PasswordAuthentication no
PermitEmptyPasswords no
MaxAuthTries 3
LoginGraceTime 20
X11Forwarding no
AllowTcpForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers guinevere
```

**Services to Disable**:
```bash
sudo systemctl disable --now snapd avahi-daemon cups bluetooth apport whoopsie
```

**Lynis Audit**: `sudo lynis audit system` - typical fresh server scores 55-65, after hardening 75-85.

---

## 12. Disaster Recovery

### selfhosting.sh Disaster Recovery - Relevance: 5/5
- **Source**: https://selfhosting.sh/foundations/disaster-recovery/

**Recovery Time Matrix**:
| Scenario | Severity | Recovery Time |
|----------|----------|--------------|
| Container/service crash | Low | Minutes (auto-restart) |
| Corrupted database | Medium | 30-60 min (restore from dump) |
| Disk failure | Medium-High | 1-4 hours (replace + restore) |
| Total server failure | High | 2-8 hours (new server + restore) |
| Ransomware/compromise | Critical | 4-24 hours (clean install + offline backup) |

**3-2-1 Rule**: 3 copies, 2 media types, 1 offsite

**Service Inventory Template** (for Guinevere):
| Service | Data Directory | Priority |
|---------|---------------|----------|
| PostgreSQL | /var/lib/postgresql | P0 (restore first) |
| Redis | /var/lib/redis | P0 |
| Guinevere API | /opt/guinevere | P0 |
| Guinevere config | /etc/guinevere | P0 |
| Discord bot | /opt/guinevere/discord | P1 |
| WhatsApp bridge | /opt/guinevere/whatsapp | P1 |
| Observability | /var/lib/prometheus, /var/lib/grafana | P2 |

**Database Backup Strategy**:
- Use pg_dump (logical), NOT raw file copies while running
```bash
pg_dumpall -U postgres | gzip > /var/backups/postgres-$(date +%Y%m%d).sql.gz
```
- Restore: `gunzip -c backup.sql.gz | psql -U postgres`

**Full Server Recovery Order**:
1. Provision new VPS, run hardening checklist
2. Install PostgreSQL + TimescaleDB + pgvector
3. Restore database from dump
4. Install Redis
5. Restore Guinevere code + config from Git
6. Decrypt secrets with SOPS + age
7. Start services in dependency order: PostgreSQL -> Redis -> PgBouncer -> Guinevere API -> Discord bot -> WhatsApp bridge
8. Install observability stack
9. Update DNS / Cloudflare Tunnel
10. Verify all endpoints

### HostMyCode VPS DR Plan - Relevance: 5/5
- **Source**: https://www.hostmycode.com/tutorials/linux-vps-disaster-recovery-plan-backups-restore-tests-failover-prep-2026

**systemd Timer for Backups** (cleaner than cron):
```ini
[Unit]
Description=Guinevere DR Backup

[Service]
Type=oneshot
EnvironmentFile=/etc/guinevere/backup.env
ExecStart=/usr/local/sbin/guinevere-backup

[Timer]
OnCalendar=*-*-* 02:00:00 Asia/Bangkok
Persistent=true

[Install]
WantedBy=timers.target
```

**Key Insight**: "A backup that has never been tested is a hypothesis." Schedule monthly restore tests.

### tva.sg Self-Hosted DR Strategy - Relevance: 4/5
- **Source**: https://www.tva.sg/insights/disaster-recovery-self-hosted-services
- PostgreSQL pg_dump orchestration with staggered scheduling
- 30-minute gaps between backup jobs to prevent I/O contention
- S3-compatible offsite with rclone + checksum verification
- Retention: 7 daily, 4 weekly, 6 monthly
- Monthly restore test to temporary container

### Rollback Procedures for Self-Deploying AI Agents

**Pre-Deploy Checklist**:
1. VPS snapshot taken
2. Last 3 tarball backups verified accessible
3. Current database dump completed
4. Rollback script tested

**Rollback Procedure**:
1. Stop the agent: `sudo systemctl stop guinevere`
2. Restore code from Git: `git checkout LAST_GOOD_TAG`
3. Restore config: `sops -d secrets/guinevere.env.sops > /etc/guinevere/secrets.env`
4. Restore database if migrations ran: `psql -U guinevere < /var/backups/pre-deploy-dump.sql`
5. Restart: `sudo systemctl start guinevere`
6. Verify: health check endpoint + manual test

---

## Summary of Directly Applicable Patterns for Guinevere

| Component | Best Source | Key Pattern |
|-----------|------------|-------------|
| Doc structure | solos-cookbook | What/Why/Prereqs/Impl/Verify/Gotchas/Templates |
| systemd units | renezander.com | Type=simple, Restart=on-failure, RestartSec=5-10, hardening 5-pack |
| FastAPI service | PySyft prod | uv run uvicorn + ExecStartPre for migrations |
| PostgreSQL pool | rivestack.io | PgBouncer transaction mode, separate admin entry in session mode |
| Secrets | DCHost + HostMyCode | SOPS + age, decrypt to /run, EnvironmentFile in systemd |
| Observability | Grafana Labs #25040 | prometheus_fastapi_instrumentator + Loki + Promtail |
| Tailscale | Official docs | Auth key + tags + Tailscale SSH + ACLs |
| Cloudflare Tunnel | rdp.sh + Data Mammoth | Named tunnel + systemd + multi-ingress + Access policy |
| Discord bot | youngju.dev | Pycord + intents + slash commands + systemd |
| WhatsApp | Baileys docs + DEV.to | useMultiFileAuthState + creds.update + rate limiting |
| Server hardening | vucense.com CIS | 20-step checklist + sysctl + SSH + UFW + fail2ban + auditd |
| Disaster recovery | selfhosting.sh + tva.sg | 3-2-1 backups + pg_dump + service priority order + monthly tests |

---

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-30 | The Librarian / Guinevere | Initial research across 7 tracks, 30+ sources analyzed |

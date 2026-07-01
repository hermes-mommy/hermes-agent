# P25 — 9Router Reference Research

> **Research Date**: 2026-06-26  
> **Researcher**: Guinevere (Librarian)  
> **Purpose**: P25 9Router VPS Migration replan — exact installation, configuration, and operational reference  
> **Sources**: npm registry, GitHub repo, Context7 docs, DeepWiki, official gitbook, Docker docs, .env.example

---

## §1 Identity & Provenance

| Field | Value |
|---|---|
| **Official Repo** | https://github.com/decolua/9router |
| **npm Package** | [9router](https://www.npmjs.com/package/9router) |
| **Website** | https://9router.com |
| **Docs** | https://github.com/decolua/9router/blob/master/gitbook/content/en/ |
| **Docker Hub** | https://hub.docker.com/r/decolua/9router |
| **GHCR** | ghcr.io/decolua/9router |
| **License** | MIT |
| **GitHub Stars** | 18,000+ |
| **Author** | decolua (https://github.com/decolua) |
| **Language** | JavaScript (Next.js) |
| **Default Branch** | `master` |

---

## §2 Latest Stable Version

| Source | Version | Date |
|---|---|---|
| **npm (latest)** | `0.5.8` | 2026-06-21 |
| **GitHub Release (latest)** | `v0.5.8` | 2026-06-21 |
| **Tag** | `v0.5.8` | commit `0c47c89` |

**Release notes (v0.5.8)**:
- Antigravity: native image generation support
- CodeBuddy CN: API key auth + credit quota tracker
- CodeBuddy CN: short model prefix alias `cbcn`
- Fixes: MiniMax-M3 vision, Headroom Docker sidecar proxy, mimo-free User-Agent rotation, cloudflare-ai content-part flattening, CLI Next.js 16 standalone output path handling

**Requirement**: Node.js >= 18.0.0 (Docker image uses `node:22-alpine`)

---

## §3 Installation Methods

### Method 1: npm Global Install (RECOMMENDED for VPS)

```bash
# Install globally
npm install -g 9router

# Run (starts server + opens dashboard)
9router

# CLI options
9router --port 8080        # Custom port
9router --no-browser        # Don't open browser (headless VPS)
9router --skip-update       # Skip auto-update check
9router --help              # Show all options
```

**Note**: The CLI performs "self-healing" on startup — it ensures `sql.js` and `better-sqlite3` are installed into `~/.9router/runtime/node_modules` to avoid Windows EBUSY errors during global updates.

### Method 2: From Source (Production VPS)

```bash
# Clone
git clone https://github.com/decolua/9router.git
cd 9router/app

# Install dependencies
npm install

# Build
npm run build

# Configure (see §4 below)
export JWT_SECRET="your-secure-secret-change-this"
export INITIAL_PASSWORD="your-secure-password"
export DATA_DIR="/var/lib/9router"
export PORT="20128"
export HOSTNAME="0.0.0.0"
export NODE_ENV="production"
export NEXT_PUBLIC_BASE_URL="http://localhost:20128"
export NEXT_PUBLIC_CLOUD_URL="https://9router.com"
export API_KEY_SECRET="endpoint-proxy-api-key-secret"
export MACHINE_ID_SALT="endpoint-proxy-salt"

# Start
npm run start

# Or with PM2 (see §6)
pm2 start npm --name 9router -- start
pm2 save
pm2 startup
```

### Method 3: Docker (Containerized VPS)

```bash
# Quick start
docker run -d \
  -p 20128:20128 \
  -v "$HOME/.9router:/app/data" \
  -e DATA_DIR=/app/data \
  --name 9router \
  decolua/9router:latest

# With full env vars
docker run -d \
  -p 20128:20128 \
  -v "$HOME/.9router:/app/data" \
  -e DATA_DIR=/app/data \
  -e PORT=20128 \
  -e HOSTNAME=0.0.0.0 \
  -e JWT_SECRET="your-secure-secret" \
  -e INITIAL_PASSWORD="your-secure-password" \
  -e NODE_ENV=production \
  --name 9router \
  decolua/9router:latest
```

**Docker Compose**:

```yaml
version: '3.8'

services:
  9router:
    image: decolua/9router:latest
    container_name: 9router
    ports:
      - "20128:20128"
    environment:
      - NODE_ENV=production
      - JWT_SECRET=your-secure-secret-change-this
      - INITIAL_PASSWORD=your-secure-password
      - DATA_DIR=/app/data
      - PORT=20128
      - HOSTNAME=0.0.0.0
    volumes:
      - 9router-data:/app/data
    restart: unless-stopped

volumes:
  9router-data:
```

**Update Docker**:
```bash
docker pull decolua/9router:latest
docker rm -f 9router
# re-run the docker run command
```

---

## §4 Environment Variables (Complete Reference)

Source: [`.env.example`](https://github.com/decolua/9router/blob/master/.env.example) + [Cloud Deployment docs](https://github.com/decolua/9router/blob/master/gitbook/content/en/deployment/cloud.md)

### Required (Production)

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | Auto-generated | **MUST change in production!** Used for JWT token signing. Generate with `openssl rand -base64 32` |
| `INITIAL_PASSWORD` | `123456` | Dashboard login password. **MUST change in production!** |
| `DATA_DIR` | `~/.9router` (local), `/app/data` (Docker) | Database and data storage path |

### Recommended (Production)

| Variable | Default | Description |
|---|---|---|
| `PORT` | `20128` | HTTP listen port for dashboard and API |
| `HOSTNAME` | `0.0.0.0` | Network interface to bind to |
| `NODE_ENV` | `development` | Set to `production` for VPS deployment |
| `API_KEY_SECRET` | — | Secret for endpoint proxy API key signing |
| `MACHINE_ID_SALT` | — | Salt for machine ID generation |
| `ENABLE_REQUEST_LOGS` | `false` | Enable debug request/response logs |
| `OBSERVABILITY_ENABLED` | `true` | Enable observability features |
| `AUTH_COOKIE_SECURE` | `false` | Set `true` behind HTTPS reverse proxy |
| `REQUIRE_API_KEY` | `false` | Require API key for `/v1/*` endpoints |

### Cloud Sync Variables

| Variable | Default | Description |
|---|---|---|
| `BASE_URL` | `http://localhost:20128` | This running instance URL (for internal sync) |
| `CLOUD_URL` | `https://9router.com` | 9Router cloud service URL |
| `NEXT_PUBLIC_BASE_URL` | `http://localhost:20128` | Public-facing base URL |
| `NEXT_PUBLIC_CLOUD_URL` | `https://9router.com` | Public cloud URL |

### Optional

| Variable | Default | Description |
|---|---|---|
| `HTTP_PROXY` | — | Outbound proxy for upstream provider calls |
| `HTTPS_PROXY` | — | Outbound proxy for upstream provider calls |
| `ALL_PROXY` | — | SOCKS5 proxy for all connections |
| `NO_PROXY` | — | Comma-separated hosts to bypass proxy |
| `NINEROUTER_PROXY_CLIENT_MAX_BODY_SIZE` | `128mb` | Max body size for LLM payloads (base64 images) |
| `TRAY_MODE` | `0` | Set `1` for system tray mode (desktop only) |

---

## §5 Default Port & URL Structure

| URL | Purpose |
|---|---|
| `http://localhost:20128` | Root |
| `http://localhost:20128/dashboard` | Web management interface |
| `http://localhost:20128/v1` | OpenAI-compatible API endpoint |
| `http://localhost:20128/v1/models` | List available models |
| `http://localhost:20128/v1/chat/completions` | Chat completions (OpenAI format) |
| `http://localhost:20128/v1/messages` | Anthropic Messages API |
| `http://localhost:20128/api/health` | Health check endpoint |

**Changing the port**: Set `PORT` env var or use `9router --port <PORT>`.

---

## §6 Authentication Mechanism

### Dashboard Auth

- **Default password**: `123456` (set via `INITIAL_PASSWORD`)
- **Auth method**: JWT tokens signed with `JWT_SECRET`
- **Token storage**: Set as `auth_token` cookie on successful login
- **Rate limiting**: Real client IP rate-limiting + remote default-password guard (since v0.4.80)
- **Security hardening** (v0.4.80+): Re-auth required on DB export/import, SSRF guard on web fetch

### API Key Auth

- API keys are managed via the Dashboard → Keys page
- Requests to `/v1/*` use header: `Authorization: Bearer <API_KEY>`
- If `REQUIRE_API_KEY=false` (default), API key is optional
- If `REQUIRE_API_KEY=true`, all `/v1/*` requests require a valid API key

### CLI-to-Server Auth

- CLI uses a random secret stored in `$DATA_DIR/auth/cli-secret`
- Machine ID from `$DATA_DIR/machine-id` + `MACHINE_ID_SALT` for token generation

### Critical Security Note

> **In production VPS, you MUST change both `JWT_SECRET` and `INITIAL_PASSWORD` before first start.** The default `123456` password is publicly known.

Generate secrets:
```bash
# JWT_SECRET
openssl rand -base64 32

# INITIAL_PASSWORD
openssl rand -base64 16

# API_KEY_SECRET
openssl rand -hex 32
```

---

## §7 Data Storage

### Storage Engine: SQLite

9Router uses **SQLite** for all persistent data. Two SQLite backends are supported:
- `better-sqlite3` (native, preferred)
- `sql.js` (pure JS fallback, used when native module fails)

### Data Directory Layout

```
$DATA_DIR/
├── db/
│   ├── data.sqlite       # Main SQLite database (connections, combos, settings, usage)
│   └── backups/          # Automatic backups
├── auth/
│   └── cli-secret        # Random secret for CLI-to-server auth
├── machine-id            # Unique machine identifier
├── runtime/
│   └── node_modules/     # Self-healed native modules (sql.js, better-sqlite3)
└── ...                   # Certs, logs, runtime configs
```

### Default Paths

| Platform | Default `DATA_DIR` |
|---|---|
| Linux/macOS | `~/.9router` |
| Windows | `%APPDATA%\9router` |
| Docker | `/app/data` |

### What's Stored in SQLite

- Provider connections and OAuth tokens
- Combo configurations (fallback chains, round-robin, fusion strategies)
- API keys and aliases
- Usage statistics and quota tracking
- Model mappings and custom models
- Application settings
- Pricing data

---

## §8 Process Management (PM2)

PM2 is the recommended process manager for VPS deployment.

### Setup

```bash
# Install PM2 globally
npm install -g pm2

# Start 9Router with PM2
pm2 start npm --name 9router -- start

# Save PM2 process list
pm2 save

# Configure auto-start on boot
pm2 startup
# Follow the instructions printed by the command
```

### Management Commands

```bash
pm2 status              # View status
pm2 logs 9router        # View logs
pm2 logs 9router --lines 100  # Last 100 lines
pm2 restart 9router     # Restart
pm2 stop 9router        # Stop
pm2 monit               # Monitor resources
pm2 delete 9router      # Remove from PM2
```

### Alternative: systemd Unit (Manual)

Since the official docs recommend PM2, but systemd is also viable for headless VPS:

```ini
# /etc/systemd/system/9router.service
[Unit]
Description=9Router AI Gateway
After=network.target

[Service]
Type=simple
User=9router
Group=9router
WorkingDirectory=/opt/9router/app
Environment=NODE_ENV=production
Environment=PORT=20128
Environment=HOSTNAME=0.0.0.0
Environment=JWT_SECRET=your-secure-secret
Environment=INITIAL_PASSWORD=your-secure-password
Environment=DATA_DIR=/var/lib/9router
Environment=API_KEY_SECRET=your-api-key-secret
Environment=MACHINE_ID_SALT=your-salt
ExecStart=/usr/bin/node node_modules/.bin/next start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable 9router
sudo systemctl start 9router
sudo systemctl status 9router
```

**Note**: The systemd unit above is for source installation. For npm global install, use `ExecStart=/usr/bin/9router` instead. The official docs recommend PM2 over systemd.

---

## §9 Nginx Reverse Proxy

### Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_server_ciphers on;

    # Dashboard
    location / {
        proxy_pass http://localhost:20128;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # SSE support — CRITICAL for streaming
        proxy_buffering off;
        proxy_read_timeout 86400;
    }

    # API endpoint
    location /v1 {
        proxy_pass http://localhost:20128;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support — CRITICAL for streaming
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
}
```

**Critical**: `proxy_buffering off` is required for SSE streaming to work.

---

## §10 Firewall (UFW)

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (if using Nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# If NOT using reverse proxy, allow 9Router directly
sudo ufw allow 20128/tcp

# Enable firewall
sudo ufw enable
```

**Security note**: If only API access is needed (no dashboard), restrict dashboard port and use SSH tunnel:
```bash
ssh -L 20128:localhost:20128 user@your-server.com
```

---

## §11 Provider Configuration

### Supported Providers (60+)

9Router connects to AI providers via the Dashboard → Providers page. Configuration includes:

- **OAuth providers**: Kiro AI, Qoder, Claude (via OAuth), Google Gemini, GitHub Copilot, Antigravity, etc.
- **API key providers**: OpenAI, Anthropic, Google, Mistral, Cerebras, SiliconFlow, etc.
- **Free providers**: Kiro AI (free Claude unlimited), OpenCode Free (no auth needed), MiMo Free, etc.

### Provider Configuration Format

Providers are stored in the SQLite database. Each connection has:
- Provider type (OAuth / API key / free)
- Authentication credentials (tokens, API keys)
- Base URL (for custom endpoints)
- Model mappings

### Combo Configuration

Combos define fallback chains:
- **Fallback**: Try model 1 → fail → try model 2 → fail → try model 3
- **Round-robin**: Distribute requests across models
- **Fusion**: Query all models in parallel, judge synthesizes one answer
- **Capacity**: Auto-switch based on request type (image/PDF/audio routes to capable model first)

### Model Format

Models are referenced with provider prefix, e.g.:
- `kr/claude-sonnet-4.5` (Kiro AI)
- `cbcn/deepseek-v3` (CodeBuddy CN)
- `openai/gpt-4o`

---

## §12 Architecture Overview

Source: [docs/ARCHITECTURE.md](https://github.com/decolua/9router/blob/master/docs/ARCHITECTURE.md)

9Router is a **Next.js application** that provides:

1. **API and Routing Layer**: `src/app/api/v1/*` — OpenAI-compatible endpoint
2. **Open-SSE Translation Layer**: Converts between provider formats (Claude ↔ OpenAI ↔ Gemini)
3. **Provider Management**: OAuth token refresh, API key management, quota tracking
4. **Dashboard**: Web UI at `/dashboard` for configuration
5. **CLI Tool**: `cli.js` — manages server lifecycle, system tray, tunnel processes

### Key Modules

| Module | Path | Purpose |
|---|---|---|
| Chat/Completions | `src/app/api/v1/chat/completions/route.js` | OpenAI chat endpoint |
| Anthropic Messages | `src/app/api/v1/messages/route.js` | Anthropic Messages API |
| Responses | `src/app/api/v1/responses/route.js` | Responses endpoint |
| Models | `src/app/api/v1/models/route.js` | Model listing |
| Auth | `src/app/api/auth/*` | Authentication |
| Providers | `src/app/api/providers*` | Provider management |
| OAuth | `src/app/api/oauth/*` | OAuth flows |
| Usage | `src/app/api/usage/*` | Usage tracking |
| Sync | `src/app/api/sync/*` | Cloud sync |

---

## §13 Backup & Recovery

### Backup

```bash
# Manual backup
tar -czf 9router-backup-$(date +%Y%m%d).tar.gz /var/lib/9router

# Automated daily backup (crontab)
0 2 * * * tar -czf /backups/9router-$(date +\%Y\%m\%d).tar.gz /var/lib/9router
```

### Restore

```bash
# Stop 9router
pm2 stop 9router  # or docker stop 9router

# Restore
tar -xzf 9router-backup-20260626.tar.gz -C /

# Start 9router
pm2 start 9router  # or docker start 9router
```

---

## §14 Monitoring & Health Check

### Health Check

```bash
curl http://localhost:20128/api/health
```

### PM2 Monitoring

```bash
pm2 status
pm2 monit
pm2 logs 9router --lines 100
```

### System Resources

```bash
htop
df -h
netstat -tulpn | grep 20128
```

---

## §15 Breaking Changes & Version History

Recent notable versions:

| Version | Date | Key Changes |
|---|---|---|
| `v0.5.8` | 2026-06-21 | Antigravity image gen, CodeBuddy CN auth |
| `v0.5.6` | 2026-06-20 | Ponytail code gen, Headroom proxy, CodeBuddy CN provider |
| `v0.5.4` | 2026-06-18 | Kiro/AG/Xiaomi provider fixes, fusion tool history |
| `v0.5.2` | 2026-06-17 | Combo Fusion, Capacity auto-switch, Kiro API-key auth, Claude auto-ping |
| `v0.4.80` | 2026-06-13 | Vercel AI Gateway, MiMo Free, security hardening (SSRF, rate-limiting, re-auth) |
| `v0.4.71` | 2026-06-06 | Codex streaming timeouts fix, Caveman classical Chinese |
| `v0.4.63` | 2026-05-26 | Readable import fix, lower stream stall timeout |
| `v0.4.62` | 2026-05-26 | Codex stability, AG 2.x MITM, json_schema fallback |
| `v0.4.59` | 2026-05-21 | OAuth login fix on Windows |

**Security-relevant changes**:
- v0.4.80: Added SSRF guard on web fetch, re-auth on DB export/import, real client IP rate-limiting, remote default-password guard
- v0.4.62: Hardened reverse-proxy local-access trust

---

## §16 Quick Reference Card (VPS Setup)

### Minimal VPS Install (npm + PM2)

```bash
# 1. Install Node.js 20+
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 2. Install 9Router globally
npm install -g 9router

# 3. Install PM2
npm install -g pm2

# 4. Generate secrets
export JWT_SECRET=$(openssl rand -base64 32)
export INITIAL_PASSWORD=$(openssl rand -base64 16)
export API_KEY_SECRET=$(openssl rand -hex 32)
export MACHINE_ID_SALT=$(openssl rand -hex 16)

# 5. Create data directory
sudo mkdir -p /var/lib/9router
sudo chown $USER:$USER /var/lib/9router

# 6. Configure environment (add to ~/.bashrc or use PM2 env)
export NODE_ENV=production
export DATA_DIR=/var/lib/9router
export PORT=20128
export HOSTNAME=0.0.0.0

# 7. Start with PM2
pm2 start 9router --name 9router -- --no-browser
pm2 save
pm2 startup

# 8. Verify
curl http://localhost:20128/api/health
```

### Minimal VPS Install (Docker)

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh

# 2. Generate secrets
JWT_SECRET=$(openssl rand -base64 32)
INITIAL_PASSWORD=$(openssl rand -base64 16)

# 3. Run
docker run -d \
  -p 20128:20128 \
  -v "$HOME/.9router:/app/data" \
  -e DATA_DIR=/app/data \
  -e JWT_SECRET="$JWT_SECRET" \
  -e INITIAL_PASSWORD="$INITIAL_PASSWORD" \
  -e NODE_ENV=production \
  --restart unless-stopped \
  --name 9router \
  decolua/9router:latest

# 4. Verify
curl http://localhost:20128/api/health
```

---

## §17 Sources & Permalinks

| Source | URL |
|---|---|
| npm package | https://www.npmjs.com/package/9router |
| npm registry (JSON) | https://registry.npmjs.org/9router/latest |
| GitHub repo | https://github.com/decolua/9router |
| GitHub releases | https://github.com/decolua/9router/releases |
| Latest release (v0.5.8) | https://github.com/decolua/9router/releases/tag/v0.5.8 |
| README | https://github.com/decolua/9router/blob/master/README.md |
| Architecture | https://github.com/decolua/9router/blob/master/docs/ARCHITECTURE.md |
| Docker docs | https://github.com/decolua/9router/blob/master/DOCKER.md |
| .env.example | https://github.com/decolua/9router/blob/master/.env.example |
| Cloud deployment | https://github.com/decolua/9router/blob/master/gitbook/content/en/deployment/cloud.md |
| Installation docs | https://github.com/decolua/9router/blob/master/gitbook/content/en/getting-started/installation.md |
| Context7 library | /decolua/9router |
| DeepWiki installation | https://deepwiki.com/decolua/9router/2.1-installation |
| Docker Hub | https://hub.docker.com/r/decolua/9router |
| Website | https://9router.com |
| SKILL.md | https://github.com/decolua/9router/blob/master/skills/9router/SKILL.md |

---

*Research complete. All claims verified against npm registry, GitHub API, Context7 docs, DeepWiki, and official gitbook documentation.*

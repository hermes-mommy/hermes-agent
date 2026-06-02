# External Technology Research: Hermes Agent, 9Router, Tasker

> **Date**: 2026-05-31  
> **Author**: Librarian (Guinevere research agent)  
> **Status**: Complete  
> **Downstream use**: Implementation prompts for Guinevere integration  

---

## Table of Contents

1. [Hermes Agent (Nous Research)](#1-hermes-agent-nous-research)
2. [9Router (LLM Routing Service)](#2-9router-llm-routing-service)
3. [Tasker (Android Automation)](#3-tasker-android-automation)
4. [Integration Matrix for Guinevere](#4-integration-matrix-for-guinevere)

---

## 1. Hermes Agent (Nous Research)

### 1.1 Overview

| Field | Value |
|---|---|
| **Official repo** | <https://github.com/NousResearch/hermes-agent> |
| **Official docs** | <https://hermes-agent.nousresearch.com/docs/> |
| **Latest version** | v0.13.0+ (Foundation Release, May 2026; 808 commits since then) |
| **License** | MIT |
| **Stars** | ~173K |
| **Language** | Python |
| **Maintainer** | Nous Research |
| **Description** | Autonomous self-improving AI agent with learning loop, skills system, persistent memory, 20+ messaging platform gateways |

### 1.2 Installation

#### System Requirements

- **Python**: 3.11 (required; installer handles uv venv creation)
- **Node.js**: required (installer handles)
- **ripgrep**: required (installer handles)
- **ffmpeg**: required for voice features (installer handles)
- **Git Bash (Windows)**: bundled MinGit (~45MB) auto-installed to `%LOCALAPPDATA%\hermes\git`

#### One-Liner Install

**Linux / macOS / WSL2 / Termux:**
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

**Windows (native PowerShell) — Early Beta:**
```powershell
iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
```

#### Manual Install (Development)
```bash
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[all,dev]"
```

#### Quick Setup (with Nous Portal)
```bash
hermes setup --portal   # One OAuth covers model + 4 Tool Gateway tools
```

### 1.3 Directory Structure

```
~/.hermes/
├── config.yaml     # Primary settings (YAML)
├── .env            # API keys and secrets
├── auth.json       # OAuth provider credentials
├── SOUL.md         # Primary agent identity (slot #1 in system prompt)
├── memories/       # Persistent memory (MEMORY.md, USER.md)
├── skills/         # Agent-created skills
├── cron/           # Scheduled jobs
├── sessions/       # Gateway sessions
└── logs/           # Logs (secrets auto-redacted)
```

### 1.4 Configuration Format

Hermes uses **YAML** (`config.yaml`) for non-secret settings and **`.env`** for secrets.

#### Configuration Precedence (highest first):
1. CLI arguments (per-invocation)
2. `~/.hermes/config.yaml`
3. `~/.hermes/.env`
4. Built-in defaults

#### Environment Variable Substitution
```yaml
auxiliary:
  vision:
    api_key: ${GOOGLE_API_KEY}
    base_url: ${CUSTOM_VISION_URL}
delegation:
  api_key: ${DELEGATION_KEY}
```

#### Key Config Sections
```yaml
# Terminal backend
terminal:
  backend: local    # local | docker | ssh | modal | daytona | singularity
  cwd: "."
  timeout: 180

# Memory
memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375

# Context compression
compression:
  enabled: true
  threshold: 0.50
  target_ratio: 0.20
  protect_last_n: 20

# Session isolation
group_sessions_per_user: true

# Tool output truncation
tool_output:
  max_bytes: 50000
  max_lines: 2000
  max_line_length: 2000

# File read safety
file_read_max_chars: 100000
```

#### Config Management Commands
```bash
hermes config              # View current configuration
hermes config edit         # Open config.yaml in editor
hermes config set KEY VAL  # Set a specific value
hermes config check        # Check for missing options
hermes model               # Choose LLM provider and model
hermes tools               # Configure enabled tools
```

### 1.5 Custom System Prompts (SOUL.md)

Hermes uses `SOUL.md` as its **primary agent identity** — it occupies slot #1 in the system prompt.

- **Location**: `~/.hermes/SOUL.md`
- **Auto-created** if it doesn't exist
- **Never overwritten** if it already exists
- **Security-scanned** for prompt injection before inclusion

#### SOUL.md Example
```markdown
# Personality
You are a pragmatic senior engineer with strong taste.
You optimize for truth, clarity, and usefulness over politeness theater.

## Style
- Be direct without being cold
- Prefer substance over filler
- Push back when something is a bad idea
- Admit uncertainty plainly

## What to avoid
- Sycophancy
- Hype language
- Overexplaining obvious things
```

#### SOUL.md vs AGENTS.md vs /personality

| File | Scope | Use For |
|---|---|---|
| `SOUL.md` | Instance-wide identity | Tone, style, personality, communication defaults |
| `AGENTS.md` | Per-project | Architecture, coding conventions, repo-specific workflows |
| `/personality` | Session-level overlay | Temporary mode switches (e.g., `/personality teacher`) |

#### Custom Personalities in config.yaml
```yaml
agent:
  personalities:
    codereviewer: >
      You are a meticulous code reviewer. Identify bugs, security issues,
      performance concerns, and unclear design choices. Be precise and constructive.
```

### 1.6 Discord Integration

#### Step-by-Step Setup

1. **Create Discord Application** at <https://discord.com/developers/applications>
2. **Create Bot** under Bot settings
3. **Enable Privileged Intents** (CRITICAL):
   - ✅ Server Members Intent (Required)
   - ✅ Message Content Intent (Required)
   - ⬜ Presence Intent (Optional)
4. **Copy Bot Token** (shown only once)
5. **Generate Invite URL**:
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot+applications.commands&permissions=274878286912
   ```
6. **Find Your User ID**: Settings → Advanced → Developer Mode → Right-click username → Copy User ID

#### Configure Hermes

**Option A — Interactive (Recommended):**
```bash
hermes gateway setup    # Select Discord, paste token + user ID
```

**Option B — Manual `.env`:**
```env
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_ALLOWED_USERS=284102345871466496
DISCORD_HOME_CHANNEL=channel-id-here
```

**`config.yaml` Discord section:**
```yaml
discord:
  require_mention: true           # Require @mention in server channels
  thread_require_mention: false   # If true, require @mention in threads too
  free_response_channels: ""      # Comma-separated channel IDs
  auto_thread: true               # Auto-create threads on @mention
  reactions: true                 # Add emoji reactions during processing
  ignored_channels: []            # Channel IDs where bot never responds
  no_thread_channels: []          # Channel IDs where bot responds without threading
  history_backfill: true          # Prepend recent channel scrollback on mention
  history_backfill_limit: 50
  allow_mentions:
    everyone: false
    roles: false
    users: true
    replied_user: true

group_sessions_per_user: true     # Isolate sessions per user in shared channels
```

#### Discord Behavior Summary

| Context | Behavior |
|---|---|
| **DMs** | Responds to every message, no @mention needed |
| **Server channels** | Only responds when @mentioned (default) |
| **Free-response channels** | Responds to all messages inline, no threading |
| **Threads** | Replies in same thread, mention rules apply |

### 1.7 Service / Daemon Setup

#### Linux (systemd)
```bash
hermes gateway install               # Install as user service
hermes gateway start                 # Start the service
hermes gateway stop                  # Stop
hermes gateway status                # Check status
journalctl --user -u hermes-gateway -f  # View logs

# Keep running after logout:
sudo loginctl enable-linger $USER

# Or system service (VPS/headless):
sudo hermes gateway install --system
sudo hermes gateway start --system
```

#### macOS (launchd)
```bash
hermes gateway install               # Install as launchd agent
hermes gateway start                 # Start
hermes gateway stop                  # Stop
hermes gateway status                # Check status
tail -f ~/.hermes/logs/gateway.log   # View logs
```

Plist location: `~/Library/LaunchAgents/ai.hermes.gateway.plist`

#### Docker
```bash
# Hermes supports Docker as terminal backend
terminal:
  backend: docker
  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"
```

### 1.8 Supported LLM Providers

- Nous Portal (300+ models)
- OpenRouter (200+ models)
- OpenAI
- Anthropic
- NovitaAI, NVIDIA NIM, Xiaomi MiMo, z.ai/GLM
- Kimi/Moonshot, MiniMax, Hugging Face
- Custom OpenAI-compatible endpoints

Switch with: `hermes model` — no code changes required.

### 1.9 Common Pitfalls

| Pitfall | Mitigation |
|---|---|
| Discord bot never responds | Enable **Message Content Intent** in Developer Portal |
| Windows install rough edges | Use WSL2 instead of native Windows (native is early beta) |
| SOUL.md from CWD not loaded | SOUL.md is always loaded from `~/.hermes/`, not working directory |
| Config keys go to wrong file | `hermes config set` auto-routes: API keys → `.env`, others → `config.yaml` |
| Docker file ownership | Enable `docker_run_as_host_user: true` or `sudo chown -R` afterward |
| Gateway restart kills sessions | Enable `gateway_restart_notification: true`; sessions auto-resume |
| Voice features need ffmpeg | Ensure ffmpeg is installed (auto-installed by one-liner) |
| Termux voice deps incompatible | Use `.[termux]` extra instead of `.[all]` |

### 1.10 Cost / Licensing

- **Hermes Agent**: MIT License, free and open-source
- **LLM costs**: Pay provider directly (OpenRouter, OpenAI, Anthropic, etc.)
- **Nous Portal**: Subscription model, covers model + 4 tools (web, image gen, TTS, browser)
- **Infrastructure**: Runs on $5 VPS or serverless (Modal/Daytona — nearly $0 when idle)

---

## 2. 9Router (LLM Routing Service)

### 2.1 Overview

| Field | Value |
|---|---|
| **Official repo** | <https://github.com/decolua/9router> |
| **Website** | <https://9router.com> |
| **npm package** | `9router` (also `n9router`) |
| **License** | MIT |
| **Language** | TypeScript (Node.js 20+, Next.js 16) |
| **Database** | SQLite (better-sqlite3) |
| **Description** | Smart AI gateway: routes LLM requests across 40+ providers with 3-tier auto-fallback, RTK token saving (20-40%), format translation, quota tracking |

### 2.2 Installation

#### Quick Install (npm global)
```bash
npm install -g 9router
9router                          # Dashboard opens at http://localhost:20128
```

#### Docker
```bash
docker run -d \
  --name 9router \
  -p 20128:20128 \
  -v "$HOME/.9router:/app/data" \
  -e DATA_DIR=/app/data \
  decolua/9router:latest
```

#### From Source
```bash
git clone https://github.com/decolua/9router.git
cd 9router
cp .env.example .env
npm install
PORT=20128 NEXT_PUBLIC_BASE_URL=http://localhost:20128 npm run dev
# Production:
npm run build
PORT=20128 HOSTNAME=0.0.0.0 NEXT_PUBLIC_BASE_URL=http://localhost:20128 npm run start
```

#### System Requirements
- **Node.js**: 20+
- **npm**: latest
- **SQLite**: bundled (better-sqlite3 / sql.js fallback)

### 2.3 Architecture

```
┌─────────────┐
│  Your CLI   │  (Claude Code, Codex, Cursor, Cline, Hermes...)
│   Tool      │
└──────┬──────┘
       │ http://localhost:20128/v1
       ↓
┌─────────────────────────────────────────────┐
│           9Router (Smart Router)            │
│  • RTK Token Saver (cut tool_result tokens) │
│  • Format translation (OpenAI ↔ Claude)     │
│  • Quota tracking                           │
│  • Auto token refresh                       │
└──────┬──────────────────────────────────────┘
       │
       ├─→ [Tier 1: SUBSCRIPTION] Claude Code, Codex, GitHub Copilot
       │   ↓ quota exhausted
       ├─→ [Tier 2: CHEAP] GLM ($0.6/1M), MiniMax ($0.2/1M)
       │   ↓ budget limit
       └─→ [Tier 3: FREE] Kiro, OpenCode Free, Vertex ($300 credits)
```

### 2.4 Configuration

9Router is configured **via its web dashboard** at `http://localhost:20128/dashboard`, not a config file.

#### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | framework default | Service port (use `20128`) |
| `HOSTNAME` | framework default | Bind host (Docker: `0.0.0.0`) |
| `DATA_DIR` | `~/.9router` | Main data location |
| `JWT_SECRET` | auto-generated | JWT signing secret for dashboard auth |
| `INITIAL_PASSWORD` | `123456` | First login password |
| `API_KEY_SECRET` | `endpoint-proxy-api-key-secret` | HMAC secret for API keys |
| `MACHINE_ID_SALT` | `endpoint-proxy-salt` | Salt for machine ID hashing |
| `ENABLE_REQUEST_LOGS` | `false` | Enable request/response logging |
| `REQUIRE_API_KEY` | `false` | Enforce Bearer API key on `/v1/*` |
| `AUTH_COOKIE_SECURE` | `false` | Force Secure auth cookie (HTTPS) |
| `BASE_URL` | `http://localhost:20128` | Server-side internal base URL |
| `CLOUD_URL` | `https://9router.com` | Cloud sync endpoint |

#### Storage
- **Database**: `$DATA_DIR/db/data.sqlite` (SQLite)
- **Auto backups**: `$DATA_DIR/db/backups/`
- **Request logs**: `<repo>/logs/...` (when `ENABLE_REQUEST_LOGS=true`)

### 2.5 API Reference

9Router exposes an **OpenAI-compatible REST API**:

#### Health Check
```bash
curl http://localhost:20128/api/health
# → {"ok":true}
```

#### List Models
```bash
curl http://localhost:20128/v1/models                    # chat/LLM
curl http://localhost:20128/v1/models/image              # image-gen
curl http://localhost:20128/v1/models/tts                # text-to-speech
curl http://localhost:20128/v1/models/embedding          # embeddings
curl http://localhost:20128/v1/models/web                # web search + fetch
curl http://localhost:20128/v1/models/stt                # speech-to-text
curl http://localhost:20128/v1/models/image-to-text      # vision
```

#### Chat Completions
```bash
POST http://localhost:20128/v1/chat/completions
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "model": "cc/claude-opus-4-6",
  "messages": [
    {"role": "user", "content": "Write a function to..."}
  ],
  "stream": true
}
```

#### Setup for Hermes Agent
```bash
export NINEROUTER_URL="http://localhost:20128"
export NINEROUTER_KEY="sk-..."    # from Dashboard → Keys

# Then in hermes:
hermes config set model 9router/cc/claude-opus-4-6
hermes config set OPENAI_API_KEY "$NINEROUTER_KEY"
hermes config set OPENAI_BASE_URL "$NINEROUTER_URL/v1"
```

### 2.6 Multi-Provider Configuration

Configure via **Dashboard → Providers**:

#### OAuth Providers (auto token refresh)
- Claude Code (Pro/Max): `cc/claude-opus-4-7`, `cc/claude-sonnet-4-6`
- Codex (Plus/Pro): `cx/gpt-5.5`, `cx/gpt-5.4`
- GitHub Copilot: `gh/claude-opus-4-7`, `gh/gpt-5.4`
- Cursor IDE: `cu/claude-4.6-opus-max`

#### API Key Providers (40+)
- OpenAI, Anthropic, Gemini, DeepSeek
- GLM ($0.6/1M tokens, daily reset)
- MiniMax ($0.2/1M tokens, 5h rolling)
- Kimi ($9/month flat, 10M tokens/mo)
- Groq, xAI, Mistral, Together, Fireworks, Cerebras, NVIDIA, SiliconFlow...

#### Free Providers
- **Kiro AI**: `kr/claude-sonnet-4-5`, `kr/glm-5` — Unlimited free
- **OpenCode Free**: No auth, auto-fetch models
- **Vertex AI**: $300 credits for new GCP accounts

### 2.7 Fallback Routing (Combos)

Create combos in **Dashboard → Combos → Create New**:

```
Combo: "my-coding-stack"
  1. cc/claude-opus-4-7       (subscription — primary)
  2. glm/glm-5.1              (cheap backup — $0.6/1M)
  3. kr/claude-sonnet-4-5     (free fallback — unlimited)

→ Auto switches when quota runs out or errors occur
```

#### Fallback Logic
1. Primary model used first
2. On quota exhaustion / rate limit / error → fallback to next tier
3. Auto token refresh for OAuth providers
4. Round-robin across multiple accounts per provider

### 2.8 Cost Tracking Features

| Feature | Details |
|---|---|
| **Real-time quota tracking** | Live token count per provider, reset countdown (5h, daily, weekly) |
| **Cost estimation** | Dashboard shows estimated cost as if using paid APIs directly |
| **Usage analytics** | Track tokens, cost, trends over time |
| **RTK Token Saver** | 20-40% input token reduction on tool outputs (git diff, grep, etc.) |
| **Caveman Mode** | Up to 65% output token reduction via terse prompting |
| **Savings tracker** | Shows what you saved by using free models vs paid APIs |

> **Note**: Dashboard "costs" are **display/tracking only**. 9Router never charges you. You pay providers directly.

### 2.9 Common Pitfalls

| Pitfall | Mitigation |
|---|---|
| Dashboard opens on wrong port | Set `PORT=20128` and `NEXT_PUBLIC_BASE_URL=http://localhost:20128` |
| First login not working | Check `INITIAL_PASSWORD` in `.env`; fallback is `123456` |
| "Language model did not provide messages" | Provider quota exhausted → use combo fallback |
| OAuth token expired | Usually auto-refreshed; if stuck: Dashboard → Provider → Reconnect |
| `127.0.0.1` vs `localhost` | Some tools (OpenClaw) need `127.0.0.1` to avoid IPv6 resolution issues |
| High displayed costs | These are estimates, not bills; check actual provider billing |
| No request logs | Set `ENABLE_REQUEST_LOGS=true` |
| Internet-exposed deploy without auth | Set `REQUIRE_API_KEY=true` and use `API_KEY_SECRET` |

### 2.10 Cost / Licensing

- **9Router software**: MIT License, completely free, never charges
- **Provider costs**: Pay each provider directly (subscriptions or API keys)
- **Free tiers available**: Kiro AI, OpenCode Free, Vertex AI
- **Zero-cost combo possible**: Kiro + OpenCode Free + RTK = $0/month
- **Typical paid cost**: $20-200/month (subscriptions) + $5-20/month (backup)

---

## 3. Tasker (Android Automation)

### 3.1 Overview

| Field | Value |
|---|---|
| **Official site** | <https://tasker.joaoapps.com> |
| **Official docs** | <https://tasker.joaoapps.com/userguide/> |
| **Google Play** | Paid app (~$3.49 one-time) |
| **Developer** | João Dias (joaoapps) |
| **Plugin ecosystem** | AutoNotification, AutoLocation, AutoInput, AutoTools, AutoVoice |
| **Description** | Android automation framework: profiles, tasks, events, states, conditions. Native HTTP Request action (since v5.8) |

### 3.2 Installation

**Tasker** is installed from Google Play Store. No `apt`/`pip`/`npm` equivalent — it's an Android app.

**Key Plugins (all from joaoapps / Google Play):**

| Plugin | Purpose | Cost |
|---|---|---|
| **AutoNotification** | Intercept/create/manage notifications | Paid with trial |
| **AutoLocation** | Geofencing, activity detection (walking, driving, etc.) | Paid with trial |
| **AutoInput** | Automate screen UI interactions | Paid with trial |
| **AutoTools** | Extended utilities (regex, JSON, etc.) | Paid with trial |
| **Join** | Cross-device communication | Free tier + paid |

### 3.3 Data Capture Capabilities

#### App Usage / Foreground App Detection

**Event: App Changed** (since Tasker 5.8)
- Triggers every time the foreground app changes
- Provides `%app_name` variable with the foreground app's package name
- Requires **Usage Stats** permission or **Accessibility** permission

```
Profile: App Changed
  Event: App Changed [Output Variables: * Package:*]
  Enter Task:
    A1: Variable Set  →  %current_app = %app_name
    A2: Log           →  App switched to: %app_name
```

**Action: App Info** (since Tasker 5.8)
- Gets usage statistics, install date, permissions, etc. for any app
- Provides variables like usage time, last used time

**Preferences → Monitor → App Check Method:**
- `App Usage Stats` (recommended, lower battery)
- `Accessibility` (more reliable on some devices)

#### Location Capture

**With AutoLocation plugin:**
```
Profile: AutoLocation Location
  Event: AutoLocation Location [Configuration: ...]
  Enter Task:
    A1: Variable Set  →  %lat = %allatitude
    A2: Variable Set  →  %lon = %allongitude
    A3: Variable Set  →  %accuracy = %alaccuracy
    A4: Variable Set  →  %address = %aladdress
```

**AutoLocation variables:**
- `%allatitude`, `%allongitude` — GPS coordinates
- `%alaccuracy` — GPS accuracy in meters
- `%aladdress` — Reverse-geocoded address
- `%alactivity` — Activity type (0=IN_VEHICLE, 1=ON_BICYCLE, 2=ON_FOOT, 3=STILL, 4=UNKNOWN, 5=TILTING)
- `%alactivitydesc` — Human-readable activity
- `%alactivityconf` — Confidence level (0-100)

**Geofencing:**
```
Profile: Geofence Home
  Event: AutoLocation Geofences [Geofence Name: Home, Status: Inside]
  Enter Task:
    A1: Flash → "I'm home"
```

#### Notification Capture

**With AutoNotification plugin:**
```
Profile: Notification Intercept
  Event: AutoNotification Intercept [Configuration: App: *]
  Enter Task:
    A1: Variable Set  →  %notif_title = %antitlebig
    A2: Variable Set  →  %notif_text = %antextbig
    A3: Variable Set  →  %notif_app = %anapp
    A4: HTTP Request  →  POST to your endpoint
```

**AutoNotification variables:**
- `%antitlebig` — Notification title
- `%antextbig` — Notification body text
- `%anapp` — Source app package name
- `%anicon` — Notification icon
- `%anwhen` — Timestamp

**Native (without plugin):**
- Event → Phone → Notification (limited fields)
- Event → Phone → Received SMS (for SMS specifically)

### 3.4 Sending Data to External HTTP Endpoints

#### HTTP Request Action (Native, since v5.8)

**Replaces deprecated HTTP Get, Head, and Post actions.**

```
Action: HTTP Request
  Method: POST
  URL: https://your-server.com/api/surveillance
  Headers:
    Content-Type:application/json
    Authorization:Bearer YOUR_ACCESS_TOKEN
  Body: {"app":"%app_name","lat":"%lat","lon":"%lon","timestamp":"%TIMES"}
  Timeout: 30
```

#### Inputs
- **URL**: Full URL
- **Headers**: Key:Value pairs, one per line
- **Query Parameters**: Key:Value pairs appended to URL
- **Body**: Text data (JSON, form-encoded, etc.)
- **File To Send**: File attachments
- **File To Save With Output**: Save response to file instead of `%http_data`
- **Timeout**: Max seconds to wait
- **Trust Any Certificate**: For self-signed certs

#### Response Variables
- `%http_data` — Response body
- `%http_response_code` — HTTP status code
- `%http_headers` — Response headers

#### OAuth 2.0 (HTTP Auth Action)
```
Action: HTTP Auth
  Method: OAuth 2.0
  Client ID: your-client-id
  Client Secret: your-client-secret
  Endpoint To Get Code: https://api.example.com/oauth/authorize
  Endpoint To Get Refresh Token: https://api.example.com/oauth/token
  Scopes: read write
```

**Important**: Set Redirect URI to `https://tasker.joaoapps.com/auth.html`

#### Basic Auth
```
Action: HTTP Auth
  Method: Username/Password
  → Stores auth headers in variable %http_auth_headers
```

### 3.5 HMAC Authentication Patterns

Tasker does **not natively support HMAC** signing in the HTTP Request action. Workarounds:

#### Option A: JavaScriptlet (Built-in JavaScript Engine)
```javascript
// Tasker action: JavaScriptlet
// Compute HMAC-SHA256

var secret = "your-hmac-secret";
var timestamp = Math.floor(Date.now() / 1000);
var payload = JSON.stringify({
  app: global("app_name"),
  lat: global("lat"),
  lon: global("lon"),
  ts: timestamp
});

// Using CryptoJS (must be loaded) or a lightweight HMAC impl
var signature = CryptoJS.HmacSHA256(timestamp + payload, secret).toString();

setGlobal("hmac_signature", signature);
setGlobal("hmac_timestamp", timestamp);
setGlobal("hmac_payload", payload);
```

#### Option B: Shell Command (requires Termux or root)
```bash
# Tasker action: Shell (Run Shell)
# Command:
echo -n "TIMESTAMP.PAYLOAD" | openssl dgst -sha256 -hmac "SECRET" | awk '{print $2}'
# Store result in %hmac_output
```

#### Option C: Server-Side Verification (Recommended for Guinevere)
Skip HMAC on Tasker side; instead:
1. Tasker sends raw data via HTTP POST with a pre-shared Bearer token
2. Guinevere's API server validates the token + timestamp
3. Rate-limit by device ID to prevent replay attacks

```
# Tasker HTTP Request:
URL: https://guinevere-server.com/api/ingest
Headers:
  Content-Type:application/json
  Authorization:Bearer SHARED_SECRET_TOKEN
  X-Device-ID: DEVICE_UNIQUE_ID
  X-Timestamp: %TIMES
Body: {"app":"%app_name","lat":"%lat","lon":"%lon","notif":"%notif_title"}
```

### 3.6 Example Profiles for Guinevere Surveillance

#### Profile 1: App Usage Tracking
```
Profile: Track App Usage
  Event: App Changed [Output Variables: * Package:*]
  Enter Task:
    A1: Variable Set  →  %ts = %TIMES
    A2: HTTP Request
         Method: POST
         URL: https://guinevere-server.com/api/app-usage
         Headers:
           Content-Type:application/json
           Authorization:Bearer TOKEN
         Body: {"package":"%app_name","timestamp":"%ts","device":"%DEVICE"}
         Timeout: 15
```

#### Profile 2: Periodic Location Report
```
Profile: Location Ping (every 15 min)
  Time: Every 15 Minutes
  Enter Task:
    A1: AutoLocation Location (get GPS fix)
    A2: Wait 5 seconds
    A3: HTTP Request
         Method: POST
         URL: https://guinevere-server.com/api/location
         Headers:
           Content-Type:application/json
           Authorization:Bearer TOKEN
         Body: {"lat":"%allatitude","lon":"%allongitude","accuracy":"%alaccuracy","address":"%aladdress","activity":"%alactivitydesc","timestamp":"%TIMES"}
         Timeout: 15
```

#### Profile 3: Notification Intercept
```
Profile: Notification Capture
  Event: AutoNotification Intercept [App: com.whatsapp,com.telegram.android,com.discord]
  Enter Task:
    A1: HTTP Request
         Method: POST
         URL: https://guinevere-server.com/api/notifications
         Headers:
           Content-Type:application/json
           Authorization:Bearer TOKEN
         Body: {"app":"%anapp","title":"%antitlebig","text":"%antextbig","timestamp":"%TIMES"}
         Timeout: 15
```

#### Profile 4: Battery + WiFi State
```
Profile: Device State Monitor
  Time: Every 30 Minutes
  Enter Task:
    A1: HTTP Request
         Method: POST
         URL: https://guinevere-server.com/api/device-state
         Headers:
           Content-Type:application/json
           Authorization:Bearer TOKEN
         Body: {"battery":"%BATT","charging":"%BATT_CHARGING","wifi":"%WIFII","screen":"%SCREEN","timestamp":"%TIMES"}
         Timeout: 15
```

### 3.7 Common Pitfalls

| Pitfall | Mitigation |
|---|---|
| App Changed event not firing | Grant **Usage Stats** permission in Android settings; check Preferences → Monitor → App Check Method |
| Location permission denied | Grant "Allow all the time" for AutoLocation; disable battery optimization |
| HTTP Request fails silently | Check `%http_response_code`; enable Tasker's "Beginner Mode" off for full error details |
| AutoNotification not intercepting | Enable as **Notification Listener** in Android settings |
| HMAC not supported natively | Use JavaScriptlet or server-side Bearer token validation instead |
| Battery drain from frequent profiles | Use longer intervals; AutoLocation updates only when other apps request it |
| OAuth redirect URI mismatch | Must use `https://tasker.joaoapps.com/auth.html` exactly |
| Variables not available in exit task | Some plugin variables are only available in the **entry task** of the profile |
| HTTP body formatting | Body must be exactly as the server expects; Tasker does NOT modify it |
| `%TIMES` vs `%TIME` | `%TIMES` = Unix epoch seconds; `%TIME` = formatted time string |

### 3.8 Cost / Licensing

| Component | Cost |
|---|---|
| **Tasker** | ~$3.49 one-time (Google Play) |
| **AutoNotification** | ~$2.49 one-time (with free trial) |
| **AutoLocation** | ~$1.99 one-time (with free trial) |
| **AutoInput** | ~$1.99 one-time (with free trial) |
| **AutoTools** | ~$1.99 one-time (with free trial) |
| **Join** | Free tier + $1.99/month premium |
| **Total for full stack** | ~$12-15 one-time |

---

## 4. Integration Matrix for Guinevere

### How These 3 Technologies Connect

```
┌──────────────────┐     HTTP POST (surveillance data)     ┌──────────────────┐
│     Tasker       │──────────────────────────────────────→│    Guinevere     │
│   (Android)      │   App usage, location, notifications  │   API Server     │
│                  │   Bearer token auth                   │   (FastAPI)      │
└──────────────────┘                                       └────────┬─────────┘
                                                                     │
                                                                     │ LLM inference
                                                                     ↓
┌──────────────────┐     OpenAI-compatible REST             ┌──────────────────┐
│    9Router       │←──────────────────────────────────────│    Hermes        │
│  (LLM Gateway)   │   http://localhost:20128/v1            │   Agent          │
│                  │   Format translation, auto-fallback    │  (Guinevere's    │
│  40+ providers   │   RTK token saving                     │   AI brain)      │
│  3-tier fallback │                                        │                  │
└──────────────────┘                                        └────────┬─────────┘
                                                                     │
                                                                     │ Discord bot token
                                                                     ↓
                                                            ┌──────────────────┐
                                                            │    Discord       │
                                                            │  (Samm's chat    │
                                                            │   interface)     │
                                                            └──────────────────┘
```

### Guinevere Integration Points

| Component | Role | Integration Method |
|---|---|---|
| **Hermes Agent** | AI brain — memory, skills, reasoning, personality via SOUL.md | Custom SOUL.md + config.yaml + Discord gateway |
| **9Router** | LLM routing — provider fallback, cost optimization, token saving | Point Hermes at `http://localhost:20128/v1` as OpenAI endpoint |
| **Tasker** | Android surveillance — app usage, location, notifications | HTTP POST to Guinevere API server with Bearer auth |
| **Discord** | Primary human interface — chat with Guinevere | Hermes gateway Discord adapter |

### Recommended Deployment Stack

```yaml
# Docker Compose for Guinevere infrastructure
services:
  hermes-agent:
    image: nikolaik/python-nodejs:python3.11-nodejs20
    volumes:
      - ./hermes-config:/root/.hermes
    environment:
      - OPENAI_BASE_URL=http://9router:20128/v1
      - OPENAI_API_KEY=${NINEROUTER_KEY}
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - DISCORD_ALLOWED_USERS=${DISCORD_USER_ID}

  9router:
    image: decolua/9router:latest
    ports:
      - "20128:20128"
    volumes:
      - ./9router-data:/app/data
    environment:
      - DATA_DIR=/app/data
      - REQUIRE_API_KEY=true
      - API_KEY_SECRET=${API_KEY_SECRET}

  guinevere-api:
    # Custom FastAPI server for Tasker data ingestion
    build: ./guinevere-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - BEARER_TOKEN=${TASKER_BEARER_TOKEN}
```

---

## Appendix A: Quick Reference Commands

### Hermes Agent
```bash
hermes                           # Start interactive CLI
hermes gateway                   # Start messaging gateway (foreground)
hermes gateway install           # Install as system service
hermes gateway start             # Start installed service
hermes model                     # Switch LLM provider/model
hermes config set KEY VAL        # Set config value
hermes config edit               # Edit config.yaml
hermes doctor                    # Diagnose issues
hermes update                    # Update to latest version
```

### 9Router
```bash
9router                          # Start (dashboard at :20128)
curl localhost:20128/api/health  # Health check
curl localhost:20128/v1/models   # List available models
```

### Tasker
```
No CLI — configured via Android app UI.
Key actions: HTTP Request, App Changed event, AutoLocation Location, AutoNotification Intercept
```

---

## Appendix B: Security Considerations for Guinevere

| Concern | Mitigation |
|---|---|
| Discord bot token exposure | Store in `~/.hermes/.env`, never commit; auto-redacted in logs |
| 9Router API key exposure | Set `REQUIRE_API_KEY=true`; use `API_KEY_SECRET` for HMAC |
| Tasker data in transit | Use HTTPS only; Bearer token in Authorization header |
| Tasker data at rest | Guinevere API encrypts before storing (SOPS+age per ADR) |
| LLM provider data leakage | Use 9Router to route through trusted providers; avoid sending PII to unknown endpoints |
| SOUL.md prompt injection | Hermes auto-scans for injection patterns; keep SOUL.md focused on persona |
| Surveillance consent | Tasker data ingestion must respect PersonaSafetyPolicy consent boundaries |

---

## Appendix C: Source Links

| Source | URL |
|---|---|
| Hermes Agent GitHub | <https://github.com/NousResearch/hermes-agent> |
| Hermes Agent Docs | <https://hermes-agent.nousresearch.com/docs/> |
| Hermes Agent Discord Setup | <https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord> |
| Hermes Agent Configuration | <https://hermes-agent.nousresearch.com/docs/user-guide/configuration> |
| Hermes Agent SOUL.md | <https://hermes-agent.nousresearch.com/docs/user-guide/features/personality> |
| 9Router GitHub | <https://github.com/decolua/9router> |
| 9Router Website | <https://9router.com> |
| 9Router npm | <https://www.npmjs.com/package/9router> |
| 9Router Docker Hub | <https://hub.docker.com/r/decolua/9router> |
| Tasker Official Docs | <https://tasker.joaoapps.com/userguide/> |
| Tasker HTTP Request | <https://tasker.joaoapps.com/userguide/en/help/ah_http_request.html> |
| Tasker HTTP Auth | <https://tasker.joaoapps.com/userguide/en/help/ah_http_auth.html> |
| Tasker Plugin List | <https://tasker.joaoapps.com/pluginlist.html> |
| AutoLocation Docs | <https://joaoapps.com/autolocation/> |

---

*Report generated 2026-05-31. All version/feature data reflects latest available information as of this date.*

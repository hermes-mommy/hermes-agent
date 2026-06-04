# WhatsApp Integration Research for Guinevere

> **Date**: 2026-06-03 | **Researcher**: THE LIBRARIAN  
> **Context**: Evaluating WhatsApp library/approach for an autonomous AI companion running Python 3.12 + FastAPI + PostgreSQL + Redis on VPS, currently using discord.py.

---

## Requirements

| Requirement | Priority |
|---|---|
| Persistent session (no re-scan QR every restart) | CRITICAL |
| Programmatic send/receive (text + media) | CRITICAL |
| Self-hosted on VPS (no Meta Business account) | CRITICAL |
| Low latency message handling | HIGH |
| Reliable reconnection | HIGH |
| Python-native or bridgeable to Python | HIGH |

---

## Executive Summary: Ranking

| Rank | Solution | Type | Ban Risk | Python UX | Maturity |
|---|---|---|---|---|---|
| 🥇 | **Neonize** | Pure Python (Go CGo bindings) | Medium-High | ⭐⭐⭐⭐⭐ Native | Growing (399★) |
| 🥈 | **Evolution API** | Docker sidecar REST API | Medium-High | ⭐⭐⭐⭐ HTTP | Production (8.4K★) |
| 🥉 | **WAHA** | Docker sidecar REST API | Medium-High | ⭐⭐⭐⭐ HTTP | Production (6.6K★) |
| 4 | **Baileys bridge** | Thin Node.js → Python HTTP | Medium-High | ⭐⭐⭐ Custom | Very Active |
| 5 | **whatsapp-web.js bridge** | Node.js Puppeteer → Python HTTP | Medium-High | ⭐⭐⭐ Custom | Very Active (22K★) |
| 6 | **whapi.cloud** | Third-party SaaS | Low (provider manages) | ⭐⭐⭐⭐ HTTP | Service |
| 7 | **Meta Cloud API** (PyWa) | Official API | Very Low | ⭐⭐⭐⭐ Native | Enterprise |
| ❌ | **venom-bot** | Node.js (ABANDONED OSS) | — | — | Dead OSS |

---

## 1. whatsapp-web.js (Node.js)

**GitHub**: [wwebjs/whatsapp-web.js](https://github.com/wwebjs/whatsapp-web.js)  
**Stars**: 22,000 | **Last Release**: v1.34.7 (Apr 24, 2026) | **NPM**: 102K weekly downloads  
**License**: Apache 2.0 | **Language**: JavaScript

### Architecture
Uses **Puppeteer** to run a headless Chromium browser that loads WhatsApp Web. The library injects JavaScript into the page to call WhatsApp Web's internal functions. This means it consumes ~300-500MB RAM per session.

### Session Persistence
Two strategies:
- **LocalAuth**: Stores session data in local folder (`tokens/`). Survives restarts.
- **RemoteAuth**: Stores session in external DB (MongoDB, Firebase, etc.) with backup sync. Better for multi-instance.

### Known Issues
- **Session disconnection after 2-3 days** is a frequently reported issue (GitHub #3224, #2005). Users report sessions dying after 2-30 days, requiring QR re-scan.
- **Frame detached errors** in Puppeteer causing instability (GitHub #127105, Mar 2026). Users work around with heartbeat checks every 15 seconds.
- Heavy RAM usage due to Chromium.

### Ban Risk
⚠️ **Medium-High**. WhatsApp detects headless Chrome. Multiple reports of numbers banned in waves (GitHub #3565, May 2025). Reaction-only bots fare better than proactive senders.

### Python Bridging Pattern
```python
# Pattern: Node.js REST API sidecar → Python httpx client
# Example: a3ro-dev/whatsapp_api_wrapper (Python wrapper around whatsapp-web.js REST API)
# Flow: Python FastAPI ↔ HTTP ↔ Node.js Express + whatsapp-web.js ↔ Puppeteer ↔ WhatsApp Web
```

**Verdict**: Most popular but heaviest. Session stability problems make it **not ideal for an always-on AI companion**.

---

## 2. Baileys (Node.js/TypeScript) — WebSocket-native

**Package**: `@whiskeysockets/baileys` (v7.0.0-rc13, 11 days ago)  
**Original Repo**: Removed by original author (adiwajshing). Now maintained by WhiskeySockets community.  
**Stars**: ~5K (across forks) | **License**: MIT

### Architecture
**No browser, no Puppeteer.** Baileys connects directly to WhatsApp Web's WebSocket protocol. This is a massive advantage:
- RAM: ~50-100MB (vs 300-500MB for Puppeteer-based solutions)
- Faster startup
- No browser fingerprinting (though still detectable at protocol level)

### Active Forks (June 2026)
| Fork | Package | Focus | Last Update |
|---|---|---|---|
| WhiskeySockets/Baileys | `@whiskeysockets/baileys` | Main community fork | May 2026 |
| canove/whaileys | `whaileys` | Stability-focused, 5000+ connections in prod | Apr 2026 |
| fazer-ai/baileys-api | `baileys-api` | REST API wrapper (Bun + Elysia.js + Redis) | May 2026 |
| periskope/baileys | `@periskope/baileys` | Commercial fork | Mar 2026 |

### Session Management
```typescript
const { state, saveCreds } = await useMultiFileAuthState("auth_info_baileys");
// State auto-saved to disk. Survives restarts.
// Pairing code support available.
```

### Known Issues
- **Ban risk** when used from datacenter IPs (GitHub WhiskeySockets #2309)
- Protocol fingerprinting detectable
- v7.0.0 has breaking changes (migration guide at whiskey.so/migrate-latest)

### Python Bridging Pattern (Production-proven)
The **Hermes Agent** project (NousResearch) uses exactly this pattern:
```python
# Bridge: Node.js Baileys ↔ HTTP ↔ Python adapter
# gateway/platforms/whatsapp.py polls /messages, posts to /send
# scripts/whatsapp-bridge/bridge.js runs the Baileys WebSocket
```

Also: [Dev.to guide (May 2026)](https://dev.to/naveen_gaur/the-complete-developers-guide-to-the-baileys-whatsapp-bot-setup-scaling-and-vps-deployment-1cp3) shows:
- Ubuntu VPS running Node.js Baileys daemon → HTTP POST to Python/Vercel API
- Messages converted to clean payloads, media to base64
- 90s timeout for AI responses

**Verdict**: Lightweight, WebSocket-native, actively maintained. Excellent for a thin bridge. **Second-best if Neonize proves unstable.**

---

## 3. WPPConnect (Node.js/TypeScript)

**GitHub**: [wppconnect-team/wppconnect](https://github.com/wppconnect-team/wppconnect)  
**Stars**: 3,305 | **Last Release**: v2.0.2 (May 4, 2026) | **License**: NOASSERTION

### Architecture
Similar to whatsapp-web.js (Puppeteer-based). Has a companion **wppconnect-server** (1K★) that exposes a REST API out of the box. Token-based session persistence.

### Known Issues
- **Ghost sessions** — sessions stuck in INITIALIZING state become permanently unrecoverable (GitHub #2482, Mar 2026)
- **Session only lasts 2-3 hours** after v2.9.0 update (GitHub #2487, Mar 2026)
- Chrome zombie processes accumulating → OOM kills

### Comparison
Per community comparison matrix (Pally Systems, Dec 2025):
| Feature | WPPConnect | Baileys | Venom | Official API |
|---|---|---|---|---|
| Ease of Use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| REST API Mode | ✅ Built-in | ❌ No | ❌ No | ✅ Yes |
| Stability | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Risk Level | Medium | Medium | Medium | None |

**Verdict**: Built-in REST API is nice, but session stability issues are concerning. **Below Baileys in reliability.**

---

## 4. venom-bot (Node.js) — NO LONGER OPEN SOURCE

**GitHub**: [orkestral/venom](https://github.com/orkestral/venom)  
**Stars**: 6,560 | **Last Open-Source Release**: v5.3.0 (Nov 23, 2024) | **Weekly Downloads**: 857

### ⚠️ CRITICAL: Abandoned as Open Source
As of July 2025, Venom **is no longer open source**. It moved to **ERA CONNECT™ Freemium** by VYNECT™:
- Free tier: limited usage
- ERA CONNECT PRO: paid license for advanced features, multiple sessions, commercial use
- No further open-source development

There is an independent fork: [venomlib/venom](https://github.com/venomlib/venom) (v6.10.0, Mar 2026) but only 15 stars.

**Verdict**: ❌ **DO NOT USE.** Abandoned open-source. Freemium model is a dead end for an autonomous AI companion.

---

## 5. Meta WhatsApp Cloud API (Official)

**Docs**: [developers.facebook.com/docs/whatsapp/pricing/](https://developers.facebook.com/docs/whatsapp/pricing/)  
**Python Wrapper**: [PyWa](https://github.com/david-lev/pywa) (535★, v4.0.0b5, Apr 2026)

### Pricing (2026 Model)
| Message Type | Cost | Notes |
|---|---|---|
| **Service** (user-initiated) | **FREE** (first 1000/mo per WABA) | Replies within 24h window |
| **Utility** (inside window) | **FREE** | Order updates, reminders |
| **Utility** (outside window) | ~$0.003-0.03/msg | Per template message |
| **Authentication** | ~$0.005-0.03/msg | OTP, verification |
| **Marketing** | ~$0.01-0.18/msg | Promotional |

### Requirements
- ✅ Meta Business Account (free to create)
- ✅ Phone number (cannot be already registered on WhatsApp)
- ✅ App on Facebook Developers
- ❌ **Template messages required for messages outside 24h window**
- ❌ **24-hour customer service window** (free-form only within window)
- ✅ Free tier: 1000 service conversations/month

### Python Integration with FastAPI (PyWa)
```python
from pywa import WhatsApp, filters, types
from fastapi import FastAPI

fastapi_app = FastAPI()
wa = WhatsApp(
    phone_id="123456789",
    token="your-token",
    server=fastapi_app,  # Auto-mounts webhook
    verify_token="xyz"
)

@wa.on_message(filters.text)
def handle_message(client: WhatsApp, msg: types.Message):
    client.send_message(to=msg.from_user.wa_id, text=f"You said: {msg.text}")
```

PyWa supports FastAPI natively, has async support, typed, and production-ready.

### Limitations for an AI Companion
- **24-hour window**: After 24 hours of no user interaction, you can only send template messages
- **Template approval**: Templates must be pre-approved by Meta (~minutes to hours)
- **No persistent "always-on" conversation**: Not designed for continuous companion-style interaction
- **User must message FIRST** to open the window

**Verdict**: Lowest ban risk, best Python support (PyWa). But the **24-hour window + template requirement is fundamentally incompatible with an autonomous AI companion** that needs to initiate messages and maintain persistent context.

---

## 6. whapi.cloud (Third-Party API)

**Website**: [whapi.cloud](https://whapi.cloud/) | **Pricing**: Free sandbox / $29/mo Developer Premium

### Architecture
Connects to WhatsApp via linked-device sessions (similar to WhatsApp Web). Exposes REST API + webhooks. You get an API token and call HTTP endpoints.

### Pricing
- **Sandbox (Free)**: 5 active conversations/month, 150 messages/day, 1K API requests/month
- **Developer Premium ($29/mo)**: Unlimited messaging, media, groups, channels, webhooks, priority support, per-number pricing

### Python Integration
```python
# Standard REST API - any HTTP client works
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}
requests.post("https://gate.whapi.cloud/messages/text", json={
    "to": "5511999999999",
    "body": "Hello from Python!"
}, headers=headers)
```

Whapi.cloud provides Python starter code, Flask webhook examples, and comprehensive documentation.

### Pros/Cons
- ✅ No Meta Business account needed
- ✅ Fixed pricing, no per-message fees
- ✅ Handles session stability, reconnection, anti-ban
- ✅ REST API — any language works
- ❌ **Third-party dependency** — your AI companion's messaging depends on an external service
- ❌ **$29/month per number** (adds up)
- ❌ Data flows through their infrastructure

**Verdict**: Good for prototyping or if you want zero ops burden. **Not ideal for a fully self-hosted autonomous system** — violates the "self-hosted on VPS" spirit.

---

## 7. Python-Native Options

### 7a. Neonize ⭐ RECOMMENDED FOR PURE PYTHON

**GitHub**: [krypton-byte/neonize](https://github.com/krypton-byte/neonize)  
**Stars**: 399 | **PyPI**: v0.3.18.post0 (May 18, 2026) | **Python**: ≥3.10 | **License**: Apache 2.0

### Architecture
Wraps the **Go whatsmeow** library (6.2K★, tulir/whatsmeow) via CGo bindings. This means:
- **No Node.js required** — `pip install neonize` is all you need
- **WebSocket-native** (same protocol as Baileys) — no Puppeteer, no browser
- **Same multi-device protocol** as WhatsApp Web
- **Pre-built wheels available** (6MB) — Go is compiled into the wheel

### Whatsmeow Background
[tulir/whatsmeow](https://github.com/tulir/whatsmeow) (6,263★, last push May 31, 2026):
- Go library for WhatsApp Web multi-device API
- Used in production by mautrix-whatsapp (Matrix bridge)
- 80 contributors, MPL-2.0 license
- Very actively maintained

### Session Persistence
```python
# Sessions stored to disk automatically
# Uses SQLite-backed store from whatsmeow
# Survives restarts without re-scanning QR
```

### Python + FastAPI Integration
```python
from neonize import NewClient
from neonize.events import MessageEv, ConnectedEv, PairStatusEv

client = NewClient("session.db")  # Auto-persisted session

@client.on(ConnectedEv)
def on_connected(client: NewClient, event: ConnectedEv):
    print("Connected to WhatsApp!")

@client.on(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    # Route to your AI companion logic
    text = message.Message.conversation or message.Message.extendedTextMessage.text
    client.send_message(message.Info.MessageSource.Chat, f"You said: {text}")

client.connect()  # Shows QR code on first run, auto-connects after
```

### Concerns
- **399 stars** — relatively small community compared to Evolution API or whatsapp-web.js
- **63 open issues** — some may be stability-related
- **Requires Go 1.19+ for building from source** (not needed if using pre-built wheels)
- **Whatsmeow is well-established** (6.2K★, production Matrix bridges), but the Python wrapper is thinner

### Real-World Adoption
The [Hermes Agent](https://github.com/NousResearch/hermes-agent) project (NousResearch) explicitly proposes switching from Baileys bridge to Neonize in [Issue #7274](https://github.com/NousResearch/hermes-agent/issues/7274):
> "This would bring WhatsApp in line with every other Hermes gateway platform — one pip install, no external runtimes, no bridge processes to manage."

**Verdict**: 🥇 **BEST OPTION for Guinevere.** Pure Python, no external runtimes, no bridge processes. The whatsmeow foundation is rock-solid. The Python wrapper is young but actively maintained. This is the ONLY option that eliminates the multi-language complexity entirely.

### 7b. PyWa (WhatsApp Cloud API wrapper)

**GitHub**: [david-lev/pywa](https://github.com/david-lev/pywa)  
**Stars**: 535 | **PyPI**: v4.0.0b5 | **License**: MIT

Excellent Python library, but **requires Meta Business Account + Cloud API**. See §5 for limitations. Best Python option IF you go the official route.

---

## 8. Evolution API (Docker Sidecar)

**GitHub**: [evolution-foundation/evolution-api](https://github.com/evolution-foundation/evolution-api)  
**Stars**: 8,430 | **Last Release**: v2.4.0-rc2 (May 17, 2026) | **Language**: TypeScript

### Architecture
A production-ready **REST API** wrapper around Baileys (unofficial) AND WhatsApp Cloud API (official). Think of it as "WhatsApp-as-a-Service" you run yourself.

### Key Features
- **Multi-instance**: Each WhatsApp number is an isolated instance with its own token
- **Docker deployment**: `docker-compose up -d` with PostgreSQL + Redis
- **REST API**: Create instance, get QR code, send messages, receive webhooks
- **Multi-tenancy**: Built-in tenant isolation for SaaS use cases
- **Integration ecosystem**: Typebot, Chatwoot, Dify, OpenAI, RabbitMQ, Kafka, SQS, S3, Socket.io

### Deployment
```yaml
# docker-compose.yml
services:
  evolution_api:       # Main API server (port 8080)
  evolution_frontend:  # Management UI (port 3000)
  evolution_postgres:  # Database (port 5432)
  evolution_redis:     # Cache (port 6379)
```

### Python Integration
```python
# Create instance
POST /instance/create {"instanceName": "guinevere", "qrcode": true, "integration": "WHATSAPP-BAILEYS"}
# Get QR code → scan with phone
GET /instance/connect/guinevere
# Send message
POST /message/sendText/guinevere {"number": "5511999999999", "text": "Hello!"}
# Webhook for incoming messages → your FastAPI endpoint
```

### Ban Risk
⚠️ **Inherits Baileys' detection profile.** Evolution API wraps Baileys — the REST layer doesn't hide the underlying unofficial connection. Meta is actively detecting and banning these connections. As [Kraya AI reports](https://blog.kraya-ai.com/whatsapp-automation-ban-risk) (Apr 2026): accounts typically last 2-8 weeks on unofficial tools.

**Verdict**: 🥈 **Second choice.** Most mature self-hosted REST API. Heavier than a thin bridge (PostgreSQL + Redis + Node.js) but battle-tested and feature-complete. Python just calls HTTP endpoints. Zero Node.js code to write.

---

## 9. WAHA (WhatsApp HTTP API)

**GitHub**: [devlikeapro/waha](https://github.com/devlikeapro/waha)  
**Stars**: 6,647 | **Last Release**: 2026.5.1 (May 26, 2026) | **License**: Apache 2.0

### Architecture
REST API supporting **three engines**:
- **WEBJS**: whatsapp-web.js (Puppeteer/browser-based)
- **NOWEB**: WebSocket-based (similar to Baileys)
- **GOWS**: Go WebSocket (whatsmeow-based) — most efficient

### Deployment
```bash
docker run -it --rm -p 3000:3000/tcp --name waha devlikeapro/waha
# Open http://localhost:3000/ — Swagger UI, QR scanner
```

### Python SDK
Unofficial but functional: [waha-python](https://github.com/teguh02/waha-python)
```python
from waha_python import WAHAClient
client = WAHAClient(base_url="http://localhost:3000")
client.send_text(chat_id="5511999999999@c.us", text="Hello!")
```

### Ban Risk
Same as all unofficial APIs. WAHA's docs honestly state: "WhatsApp does not allow bots or unofficial clients on their platform, so this shouldn't be considered totally safe."

**Verdict**: 🥉 **Third choice.** Very clean, Swagger docs, active development. GOWS engine (whatsmeow-based) is most efficient. Similar to Evolution API but lighter weight.

---

## 10. Typebot / Chatwoot — Platforms, Not Libraries

### Typebot
- 9.8K★ visual chatbot builder
- WhatsApp integration requires **Meta Business API** (Cloud API)
- Self-hostable but WhatsApp channel still goes through official API
- Not a solution for unofficial WhatsApp access

### Chatwoot
- Open-source customer support platform (Ruby on Rails)
- WhatsApp via: (a) Meta Cloud API, or (b) third-party connectors like WAHA/Wazzap
- Python SDK available (chatwoot-sdk-python, v0.2.0, Feb 2026)
- Adds significant infrastructure (PostgreSQL + Redis + Ruby/Rails) for just WhatsApp
- Overkill for an AI companion

**Verdict**: ❌ Both require Meta Business API or add unnecessary platform complexity.

---

## Ban Risk Summary

| Approach | Detection Method | Ban Timeframe | Recovery |
|---|---|---|---|
| **All unofficial APIs** (Baileys, whatsmeow, whatsapp-web.js, WPPConnect, Evolution API, WAHA) | Protocol fingerprinting, IP reputation, message velocity, behavioral analysis | 2-8 weeks typical | **Permanent — no appeal** |
| **Reaction-only bots** (only respond, never initiate) | Lower risk | <2% ban rate over 12 months | N/A |
| **Proactive messaging** | High risk | 15-30% ban rate over 12 months | Permanent |
| **Meta Cloud API** | None (official) | Near zero | Appeals possible, warnings before bans |

**Key insight from 50+ cases** (Achiya Automation, Apr 2026): "Unofficial API bots that only respond to incoming messages have a very low ban rate (<2% over 12 months). Bots that send proactive messages see 15-30%."

For Guinevere (an AI companion that may want to initiate check-ins): this is a **significant risk to consider**.

---

## Recommended Architecture for Guinevere

### 🥇 Primary Recommendation: Neonize (Pure Python)

```
┌─────────────────────────────────────────────────┐
│                  VPS (Python 3.12)               │
│                                                  │
│  ┌──────────┐    ┌──────────────┐               │
│  │ FastAPI   │◄──►│ AI Companion │               │
│  │ Server    │    │ (Guinevere)  │               │
│  └────┬─────┘    └──────┬───────┘               │
│       │                 │                        │
│  ┌────┴─────────────────┴──────┐                │
│  │       neonize (Python)       │                │
│  │    ┌──────────────────────┐  │                │
│  │    │  Go whatsmeow (CGo)  │  │                │
│  │    │  WebSocket → WhatsApp│  │                │
│  │    └──────────────────────┘  │                │
│  └──────────────────────────────┘                │
│                                                  │
│  Existing: discord.py, PostgreSQL, Redis         │
└─────────────────────────────────────────────────┘
```

**Pros**:
- **Zero additional runtimes** — no Node.js, no Docker sidecar
- **Single `pip install neonize`** dependency
- **Same Python event loop** — no HTTP bridge latency
- **Session auto-persisted** to SQLite/disk

**Cons**:
- Smaller community (399 stars vs Evolution's 8.4K)
- CGo bindings add complexity if you need to debug at Go level
- 63 open issues on GitHub

**Mitigation**: The underlying whatsmeow library (6.2K★) is rock-solid. Neonize is a thin wrapper. If Neonize has issues, the fallback is Evolution API or WAHA as a Docker sidecar.

---

### 🥈 Fallback: Evolution API Sidecar

```
┌──────────────────────────────────────────────────┐
│                    VPS                           │
│                                                  │
│  ┌──────────────────┐   ┌────────────────────┐  │
│  │  Python FastAPI   │◄─►│ Evolution API      │  │
│  │  (Guinevere)      │   │ (Docker, Node.js)  │  │
│  │                   │   │ Port 8080          │  │
│  └──────────────────┘   │ ┌──────┐ ┌───────┐ │  │
│                         │ │ PG   │ │ Redis │ │  │
│                         │ └──────┘ └───────┘ │  │
│                         └────────────────────┘  │
└──────────────────────────────────────────────────┘
```

**When to use**: If Neonize proves unstable, or if you want the most battle-tested solution immediately.

**Pros**: 8.4K stars, 160 contributors, production-tested, REST API is language-agnostic.

**Cons**: Adds Docker containers (PostgreSQL, Redis, Node.js), HTTP latency per message.

---

### ⚠️ Hybrid Option: Meta Cloud API + Unofficial for Different Use Cases

If ban risk is unacceptable for your primary number:
- Use **Meta Cloud API + PyWa** for the "official" companion number
- Accept the 24-hour window limitation (user must message first)
- For proactive check-ins, use template messages

This is the **only ban-safe option** but limits the companion's ability to initiate conversations freely.

---

## References

| Source | URL |
|---|---|
| whatsapp-web.js GitHub | https://github.com/wwebjs/whatsapp-web.js |
| whatsapp-web.js session disconnect #3224 | https://github.com/wwebjs/whatsapp-web.js/issues/3224 |
| whatsapp-web.js ban reports #3565 | https://github.com/pedroslopez/whatsapp-web.js/issues/3565 |
| Baileys WhiskeySockets | https://github.com/WhiskeySockets/Baileys |
| Baileys ban issue #2309 | https://github.com/WhiskeySockets/Baileys/issues/2309 |
| Neonize GitHub | https://github.com/krypton-byte/neonize |
| Neonize PyPI | https://pypi.org/project/neonize/ |
| whatsmeow GitHub | https://github.com/tulir/whatsmeow |
| Evolution API GitHub | https://github.com/evolution-foundation/evolution-api |
| WAHA GitHub | https://github.com/devlikeapro/waha |
| WPPConnect GitHub | https://github.com/wppconnect-team/wppconnect |
| venom-bot (now closed-source) | https://github.com/orkestral/venom |
| PyWa GitHub | https://github.com/david-lev/pywa |
| Meta WhatsApp Pricing | https://developers.facebook.com/docs/whatsapp/pricing/ |
| whapi.cloud | https://whapi.cloud/ |
| Hermes Agent Neonize proposal #7274 | https://github.com/NousResearch/hermes-agent/issues/7274 |
| WhatsApp ban risk analysis (Kraya) | https://blog.kraya-ai.com/whatsapp-automation-ban-risk |
| Baileys + Python bridge guide | https://dev.to/naveen_gaur/the-complete-developers-guide-to-the-baileys-whatsapp-bot-setup-scaling-and-vps-deployment-1cp3 |
| WhatsApp ban fixes (Achiya) | https://achiya-automation.com/en/blog/whatsapp-spam-detection-2026/ |
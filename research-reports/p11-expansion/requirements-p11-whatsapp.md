# P11 WhatsApp Integration — Requirements Specification

> **Status:** Draft — awaiting Faiz confirmation on step breakdown  
> **Date:** 2026-06-03  
> **Author:** Guinevere (compiled from Faiz's 47 answers + 5 research agents + design docs)

---

## 1. Executive Summary

**Goal:** Guinevere accessible via WhatsApp sebagai alternative interface ke Discord.

**Scope:** Text-only MVP. ConversationalAgent layer (LLM-powered natural language) dibangun di P11, reusable untuk semua future channels (P12 Gmail, P13 X, P14 Wearable).

**Key Decision:** Neonize (pure Python) replaces Baileys (Node.js). ADR-022 needs revision.

**Dependencies:** P5 (Agent Loop) + P8 (MVP Gate) — P9/P10 nice-to-have, not blocking.

---

## 2. Binding Design Decisions (from Faiz's Answers)

### 2.1 Architecture & Library

| # | Decision | Detail |
|---|----------|--------|
| 1 | **Library** | Neonize (pure Python, pip installable, wraps whatsmeow Go) |
| 2 | **ADR-022** | Needs revision — Baileys → Neonize |
| 3 | **Hosting** | Same VPS (guinevere-vps) |
| 4 | **Systemd** | Separate unit: `guinevere-whatsapp.service` |
| 5 | **Multi-device** | Single number (Faiz only) |
| 6 | **Session storage** | PostgreSQL (Neonize native backend) + SOPS encryption for DB credentials |
| 7 | **Protocol break** | Auto-reconnect + Discord alert |
| 8 | **Phone dependency** | Phone Faiz must be online (once/14 days minimum) |

### 2.2 Conversational Layer

| # | Decision | Detail |
|---|----------|--------|
| 11 | **ConversationalAgent** | YES — built in P11, LLM-powered |
| 12 | **ChannelAdapter** | YES — abstract class, reusable for P12/P13/P14 |
| 13 | **LLM model** | Same LLMRouter (9Router proxy) |
| 14 | **Latency target** | <3s, streaming if possible |
| 15 | **Context window** | Last 10 messages sliding window |
| 16 | **Cross-channel memory** | YES — shared memory pool with Discord |
| 17 | **Typing indicator** | YES — WhatsApp typing events |
| 18 | **Response splitting** | YES — auto-split ~1000 chars per bubble |

### 2.3 Message Handling

| # | Decision | Detail |
|---|----------|--------|
| 19 | **Media (MVP)** | Text only |
| 20 | **Incoming media** | Acknowledge "belum bisa proses media" |
| 21 | **Outgoing media** | Guinevere can send PDF/text only |
| 22 | **Command format** | Natural language primary, commands as fallback |
| 23 | **Command prefix** | `!` (e.g., `!status`, `!loop-start`) |
| 24 | **Group chat** | NO — 1-on-1 only (Faiz ↔ Guinevere) |
| 25 | **Message dedup** | Per-channel — respond independently |
| 26 | **Rate limiting** | WhatsApp native: 8/min, 30/hour, 200/day |

### 2.4 Safety & Consent

| # | Decision | Detail |
|---|----------|--------|
| 27 | **HARD STOP** | Same keyword, cross-channel effect (WhatsApp = all channels) |
| 28 | **Safe word** | Shared Redis flag |
| 29 | **Whitelist** | Faiz only (MVP) |
| 30 | **Consent model** | Opt-in = QR scan first time |
| 31 | **Surveillance** | WhatsApp messages = surveillance data, consent prompt required |
| 32 | **Persona level** | Y4 (same as Discord) |
| 33 | **Distress protocol** | Same as Discord |

### 2.5 Discord Bridge

| # | Decision | Detail |
|---|----------|--------|
| 34 | **Message sync** | Mirror to Discord private channel |
| 35 | **Notifications** | YES — Discord notification on WhatsApp message |
| 36 | **Status sync** | YES — command status sync to Discord |
| 37 | **Fallback** | Both — Discord + Gotify |
| 38 | **Dashboard** | YES — Discord embed showing WhatsApp connection status |

### 2.6 Operational

| # | Decision | Detail |
|---|----------|--------|
| 39 | **Health check** | Every 60 seconds |
| 40 | **Reconnection** | Auto-reconnect, max 3 retry, exponential backoff |
| 41 | **Monitoring** | YES — Grafana dashboard |
| 42 | **Logging** | Metadata only — no message content (privacy) |
| 43 | **Backup** | Session data included in backup pipeline |
| 44 | **Cost** | Neonize = free (unofficial API) |

### 2.7 Step Structure

| # | Decision | Detail |
|---|----------|--------|
| 45 | **Granularity** | Fine-grained, Tier 1 gold standard |
| 46 | **Atomicity** | 1 step = 1 atomic task |
| 47 | **Dependencies** | P5 + P8 only (P9/P10 not blocking) |

---

## 3. Traceability to Design Docs

| Source | Requirement ID | P11 Mapping |
|--------|----------------|-------------|
| SRS | SRS-IR-006 | WhatsApp via Neonize (was Baileys) |
| SRS | SRS-IR-007 | Text-only MVP |
| SRS | SRS-IR-008 | Safe word cross-channel |
| SRS | SRS-IR-009 | Message dedup per-channel |
| SRS | SRS-IR-010 | Identity binding Faiz only |
| FSD | FSD-COM-001 | Consent: Faiz-only, opt-in via QR |
| Security Policy | §4 | SOPS session encryption |
| Deployment Guide | systemd | Separate `guinevere-whatsapp.service` |
| ADR-022 | Per-channel contract | ChannelAdapter pattern |
| ADR-002 | Safe word | Cross-channel via shared Redis flag |

---

## 4. Architecture Overview

### 4.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    guinevere-vps                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐     ┌──────────────────────────────┐  │
│  │  Discord Bot     │     │  WhatsApp Service            │  │
│  │  (existing)      │     │  (new, separate systemd)     │  │
│  │                  │     │                              │  │
│  │  GuinevereBot    │     │  NeonizeClient               │  │
│  │  ├─ HardStop ◄───┼─────┼─► Shared Redis Flag          │  │
│  │  ├─ Commands     │     │  ├─ QR Auth                  │  │
│  │  └─ Embeds       │     │  ├─ Send/Receive             │  │
│  └────────┬─────────┘     │  └─ Event Handlers           │  │
│           │               └──────────────┬───────────────┘  │
│           │                              │                  │
│           ▼                              ▼                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Channel Layer (new)                     │    │
│  │                                                     │    │
│  │  ChannelAdapter (abstract)                          │    │
│  │  ├─ DiscordAdapter (future refactor)                │    │
│  │  ├─ WhatsAppAdapter (P11)                           │    │
│  │  ├─ GmailAdapter (P12 stub)                         │    │
│  │  └─ ...                                             │    │
│  │                                                     │    │
│  │  UnifiedMessage (dataclass)                         │    │
│  │  ChannelContext (identity, metadata)                │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        │                                    │
│                        ▼                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           ConversationalAgent (new)                  │    │
│  │                                                     │    │
│  │  ├─ LLMRouter (existing, 9Router)                   │    │
│  │  ├─ Persona Engine (existing, Y4)                   │    │
│  │  ├─ Memory Recall (existing, shared pool)           │    │
│  │  ├─ Context Manager (10-msg sliding window)         │    │
│  │  ├─ Intent Classifier (NL vs command)               │    │
│  │  └─ Response Formatter (split, typing, markdown)    │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        │                                    │
│                        ▼                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Existing Services (reuse)               │    │
│  │                                                     │    │
│  │  PostgreSQL ◄── Memory, WA Session, Conversation    │    │
│  │  Redis ◄── HARD STOP flag, Rate limits, Consent     │    │
│  │  SOPS ◄── DB credentials encryption                 │    │
│  │  Gotify ◄── Fallback notifications                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 New File Structure

```
src/
├── channels/                          # NEW — Channel layer
│   ├── __init__.py
│   ├── base.py                        # ChannelAdapter abstract class
│   ├── unified_message.py             # UnifiedMessage dataclass
│   ├── channel_context.py             # ChannelContext
│   └── whatsapp/                      # WhatsApp-specific
│       ├── __init__.py
│       ├── adapter.py                 # WhatsAppAdapter
│       ├── neonize_client.py          # NeonizeClient wrapper
│       ├── auth.py                    # QR scan, pairing, session
│       ├── rate_limiter.py            # Per-number rate limiting
│       └── reconnection.py            # Auto-reconnect handler
├── agent/                             # NEW — Conversational agent
│   ├── __init__.py
│   ├── conversational_agent.py        # ConversationalAgent class
│   ├── context_manager.py             # 10-msg sliding window
│   ├── intent_classifier.py           # NL vs command detection
│   └── response_formatter.py          # Split, markdown, typing
├── discord/                           # EXISTING — minor modifications
│   ├── bot.py                         # Add shared HARD STOP listener
│   └── ... (22 files unchanged)
└── ... (other existing modules)
```

### 4.3 Data Flow

```
WhatsApp Message (Faiz)
    │
    ▼
NeonizeClient (event handler)
    │
    ▼
WhatsAppAdapter.to_unified_message()
    │
    ▼
Rate Limiter check (Redis)
    │
    ├─ OVER LIMIT → reject silently
    │
    ▼
Number Whitelist check (Redis)
    │
    ├─ NOT WHITELISTED → ignore + log
    │
    ▼
Consent check (Redis)
    │
    ├─ NO CONSENT → send consent prompt
    │
    ▼
Intent Classifier
    │
    ├─ COMMAND (! prefix) → CommandHandler
    │                         │
    │                         ▼
    │                    Execute command
    │                         │
    │                         ▼
    │                    Format response
    │
    └─ NATURAL LANGUAGE → ConversationalAgent
                            │
                            ├─ Load context (last 10 msgs)
                            ├─ Recall memories (shared pool)
                            ├─ Inject persona (Y4)
                            ├─ Check HARD STOP (Redis flag)
                            │     ├─ TRIGGERED → emergency response
                            ├─ Call LLMRouter (9Router)
                            ├─ Format response (split >1000 chars)
                            │
                            ▼
                    ResponseFormatter
                            │
                            ├─ Send typing indicator
                            ├─ Split if needed
                            ├─ Send via WhatsAppAdapter
                            │
                            ▼
                    Discord Mirror
                            │
                            ├─ Mirror to private channel
                            ├─ Send notification embed
                            │
                            ▼
                    Conversation Log (PG, metadata only)
```

### 4.4 Cross-Channel HARD STOP Flow

```
Any Channel receives HARD STOP keyword
    │
    ▼
HardStopHandler (existing, enhanced)
    │
    ├─ Set Redis flag: guinevere:hard_stop = true
    ├─ Set Redis flag: guinevere:safe_word = true (if applicable)
    │
    ▼
All ChannelAdapters poll Redis flag (60s interval)
    │
    ├─ Discord: stop responding, send emergency embed
    ├─ WhatsApp: stop responding, send emergency message
    ├─ Gotify: send fallback notification
    │
    ▼
Manual reset required: !hard-stop-reset (Faiz only)
```

---

## 5. Neonize Technical Details

### 5.1 Library Overview

| Property | Value |
|----------|-------|
| Name | `neonize` |
| Version | 0.3.18 (May 2026) |
| Language | Python (wraps Go whatsmeow via cgo) |
| Install | `pip install neonize` |
| Protocol | Multi-Device (MD) WhatsApp protocol |
| Auth | QR scan or pairing code |
| Stars | 399 (growing) |
| License | MIT |

### 5.2 Key APIs (from research)

```python
from neonize import NewClient, Message

# Initialize client
from neonize.utils import NewSession
client = NewClient(
    session=NewSession(
        "postgresql://guinevere:PASSWORD@localhost:5432/guinevere",
        table_name="whatsapp_sessions"
    )
)

# QR Auth
client.connect()
qr = client.get_qr()  # Returns QR string for scanning

# Event handlers
@client.on_message
async def handle_message(message: Message):
    sender = message.Chat  # JID
    text = message.GetBody()  # Text content
    # ... process and respond

# Send message
client.send_message(
    to="628123456789@s.whatsapp.net",
    message="Hello from Guinevere!"
)

# Typing indicator
client.send_chat_presence(
    to="628123456789@s.whatsapp.net",
    presence="composing"  # typing indicator
)
```

### 5.3 Ban Risk Mitigation

| Risk Factor | Mitigation |
|-------------|------------|
| Datacenter IP | Use residential proxy if possible; otherwise accept elevated risk |
| Velocity >30/hr | Rate limiter: 8/min, 30/hour, 200/day |
| Low reply rate | Reactive-only (never initiate to unknown contacts) |
| Protocol break | Auto-reconnect + Discord alert + manual QR re-scan if needed |
| Phone offline >14 days | Discord reminder: "Phone perlu online untuk WhatsApp" |

---

## 6. Security & Privacy Requirements

### 6.1 Session Encryption

```
Session data (Neonize internal state)
    │
    ▼
Stored in PostgreSQL via Neonize native backend
    table: whatsapp_sessions
    schema: public (or whatsapp schema if created)

DB credentials (whatsapp_session_user)
    │
    ▼
SOPS encrypt (age key from secrets/)
    │
    ▼
Store encrypted credentials
    file: secrets/whatsapp-session-db.env.sops
```

### 6.2 Logging Policy

| Data | Log? | Destination |
|------|------|-------------|
| Message timestamp | YES | PostgreSQL |
| Message direction (in/out) | YES | PostgreSQL |
| Sender JID | YES | PostgreSQL |
| Message content | **NO** | — |
| Command executed | YES | PostgreSQL |
| Error stacktrace | YES | Loki/file |
| Session state | **NO** | PostgreSQL (Neonize native backend, SOPS-encrypted DB credentials) |

### 6.3 Consent Flow

```
First connection (QR scan):
    1. Faiz scans QR code
    2. Guinevere sends: "Halo Faiz! Ini Guinevere di WhatsApp.
       Untuk melanjutkan, ketik: !consent-grant"
    3. Faiz sends: !consent-grant
    4. Guinevere: "Consent granted. WhatsApp messages will be
       processed as surveillance data per SurveillanceDataPolicy.
       Ketik !consent-revoke kapan saja untuk stop."
    5. Redis: guinevere:whatsapp:consent = { granted: true, timestamp: ... }
```

---

## 7. Performance Requirements

| Metric | Target | Notes |
|--------|--------|-------|
| Response latency | <3s | End-to-end from message received to first bubble |
| Typing indicator | <500ms | Show typing immediately on message receive |
| Health check | 60s | Connection liveness check interval |
| Reconnect timeout | 30s, 60s, 120s | Exponential backoff, max 3 retries |
| Context window | 10 messages | Sliding window, shared across channels |
| Rate limit headroom | 80% of WhatsApp limit | Gaussian jitter on response timing |

---

## 8. Monitoring & Alerting

### 8.1 Grafana Metrics

| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| `whatsapp_connected` | Gauge (0/1) | 0 for >5min |
| `whatsapp_messages_received_total` | Counter | — |
| `whatsapp_messages_sent_total` | Counter | — |
| `whatsapp_response_latency_seconds` | Histogram | p95 >3s |
| `whatsapp_reconnect_attempts_total` | Counter | >3 in 1h |
| `whatsapp_session_age_seconds` | Gauge | >12 days (phone reminder) |
| `whatsapp_rate_limit_hits_total` | Counter | >0 |

### 8.2 Discord Alerts

| Event | Discord Message |
|-------|-----------------|
| Connection established | ✅ WhatsApp connected |
| Connection lost | ❌ WhatsApp disconnected, attempting reconnect... |
| Reconnect failed (3x) | 🚨 WhatsApp reconnect failed. Manual QR scan required. |
| Session expired | 🔄 WhatsApp session expired. Scan new QR code. |
| HARD STOP triggered | 🛑 HARD STOP activated from WhatsApp |
| Phone offline >12 days | ⚠️ Phone hasn't been online in 12 days |

---

## 9. ADR-022 Revision Requirements

ADR-022 currently mandates Baileys (Node.js). Must be revised to:

1. Replace "Baileys" with "Neonize" throughout
2. Replace "Node.js subprocess" with "Python-native Neonize client"
3. Replace "HTTP bridge" with "direct Python integration"
4. Keep: separate systemd unit, SOPS encryption, per-channel contract, safe word cross-channel
5. Add: Neonize version pinning (`neonize>=0.3.18,<0.4.0`)
6. Add: whatsmeow protocol break handling strategy
7. Update: risk assessment (Neonize smaller community vs Baileys)

---

## 10. Acceptance Criteria

### P11 Exit Criteria (draft)

- [ ] WhatsApp connected and stable for 24h
- [ ] ConversationalAgent responds to natural language with <3s latency
- [ ] All `!` commands working (mirror Discord slash commands)
- [ ] HARD STOP cross-channel verified (WhatsApp → Discord)
- [ ] Safe word cross-channel verified
- [ ] Consent flow completed and logged
- [ ] Discord mirror working (messages + notifications)
- [ ] Grafana dashboard showing all metrics
- [ ] Auto-reconnect verified (kill session, observe reconnect)
- [ ] Rate limiter verified (flood test, observe throttling)
- [ ] Session survives service restart
- [ ] Metadata-only logging verified (no content in logs)
- [ ] ADR-022 revised and approved

---

## 11. Out of Scope for P11 MVP

- Media processing (photos, audio, video)
- Group chat support
- Multi-number support
- WhatsApp Business API integration
- Voice messages transcription
- Document parsing
- Rich card/template messages
- WhatsApp payments

---

## 12. Caveats & Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Neonize library abandoned | Low | High | whatsmeow Go library is mature; can wrap directly if needed |
| WhatsApp protocol break | Medium (every 2-8 weeks) | Medium | Auto-reconnect + Discord alert + QR re-scan fallback |
| Ban due to datacenter IP | Low-Medium | High | Reactive-only messaging, rate limiting, residential proxy if available |
| Phone offline >14 days | Low | Medium | Discord reminder at 12 days |
| LLM latency >3s | Medium | Low | Streaming response, chunked delivery |
| Session corruption | Low | Medium | PostgreSQL backup in daily dump, auto-recovery |

---

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-03 | Guinevere | Initial requirements from 47 Faiz answers + 5 research agents |

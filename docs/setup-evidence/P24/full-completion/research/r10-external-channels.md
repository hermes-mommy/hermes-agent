# R10 -- External Channels Domain Research

**Generated:** 2026-06-29
**Method:** Static analysis of installed Hermes v0.15.2 (`.venv/Lib/site-packages/`) and existing `src/` Guinevere code via `find`, `Read`, `Grep`. All claims cite `file:line`.

---

## 1. Source Inventory

### 1.1 WhatsApp (Neonize adapter) -- `src/channels/whatsapp/` (22 files, ~3,368 lines)

| File | Lines | Role |
|------|-------|------|
| `neonize_client.py` | 454 | Core Neonize client wrapper; event lifecycle (connect/disconnect/QR/paircode/message) |
| `adapter.py` | 201 | Ingress/egress adapter; normalizes `WhatsAppEvent` into `WhatsAppMessageEnvelope` DTOs |
| `service.py` | 448 | Service entrypoint with CLI args; wires all deps; health HTTP server on port 8095 |
| `bridge.py` | ~350 | `WhatsAppHermesBridge` -- stateless bridge to `src.core.services.prompt_loader` + `src.hermes.adapter` |
| `router.py` | ~120 | Thin router: classify (command/conversation/discard) then dispatch |
| `envelope.py` | ~100 | Canonical DTOs: `WhatsAppMessageEnvelope` (inbound), `WhatsAppDeliveryEnvelope` (outbound) |
| `formatter.py` | ~200 | Markdown-to-WhatsApp conversion + chunking (1000-char target, 10-chunk max) |
| `consent_manager.py` | ~200 | Redis-backed consent gate (`guinevere:whatsapp:consent`) |
| `hard_stop.py` | ~70 | Wraps shared `HardStopHandler` from `src.core.services` |
| `whitelist.py` | ~100 | Redis-backed number whitelist (`guinevere:whatsapp:whitelist`); fail-closed |
| `rate_limiter.py` | ~120 | Dedup (120s TTL) + rate limits (8/min, 30/hr, 200/day) |
| `policy.py` | ~80 | Group/media/text-only policy gate |
| `auth.py` | ~250 | Session metadata, encrypted session blob in Redis, pairing-code helper |
| `session_crypto.py` | ~80 | SOPS encrypt/decrypt for session blobs |
| `reconnection.py` | ~150 | Reconnect state machine: CONNECTED/DISCONNECTED/RECONNECTING/FAILED |
| `presence.py` | ~60 | Typing indicator management |
| `health.py` | ~180 | Health probe with degraded/ready states |
| `metrics.py` | ~80 | Prometheus counters/gauges |
| `ops_commands.py` | ~120 | `/status`, `/hardstop`, `/consent` ops commands |
| `structured_logging.py` | ~80 | Structured log helpers |
| `__init__.py` | 57 | Public API re-exports |

**Neonize dependency chain:**
- `neonize.NewClient` (from `neonize/client.py`) -- WhatsApp protocol client
- `neonize.events.*` -- `ConnectedEv`, `DisconnectedEv`, `MessageEv`, `PairStatusEv`, `LoggedOutEv`, etc.
- `neonize.proto.Neonize_pb2` -- Protobuf definitions for JID, chat presence, receipts
- `neonize.utils.jid` -- `JID`, `build_jid` helpers

**Safety pipeline order** (verified in `service.py:179-265`):
1. Whitelist (silent drop unknown senders)
2. Hard Stop (shared safety handler)
3. Consent (Redis-backed channel consent)
4. Dedup (120s message hash)
5. Policy (group/media/text-only gate)
6. Rate Limit (8/min, 30/hr, 200/day)
7. Bridge (Hermes runtime invocation)

### 1.2 Gmail (OAuth2) -- `src/gmail/` (36 files, ~12,723 lines)

| File | Lines | Role |
|------|-------|------|
| `service.py` | ~800 | Main service: wires OAuth, Pub/Sub, sync, watch, commands, health/metrics |
| `client.py` | ~400 | Async Gmail API client with `QuotaTracker` (6000 units/min sliding window) |
| `token_manager.py` | ~250 | OAuth2 lifecycle: SOPS-decrypted creds, auto-refresh, backoff |
| `config.py` | ~150 | `GmailSettings` via pydantic-settings (`GMAIL_` prefix) |
| `bridge.py` | ~200 | `GmailHermesBridge` -- stateless bridge to Hermes prompt_loader + adapter |
| `sync_engine.py` | ~500 | Incremental/full/backfill sync; Redis-backed cursors (`guinevere:gmail:sync_state`) |
| `router.py` | ~400 | Email routing decisions |
| `classifier.py` | ~600 | Email classification (category + importance) |
| `scorer.py` | ~200 | Importance scoring |
| `consent_manager.py` | ~200 | Email consent management |
| `envelope.py` | ~200 | `GmailMessageEnvelope` DTO |
| `briefing.py` | ~400 | Daily email briefing generator |
| `draft/generator.py` | ~300 | Draft reply generation via Hermes |
| `draft/send_pipeline.py` | ~200 | Draft send pipeline |
| `draft/discord_ux.py` | ~300 | Discord-based draft approval UX |
| `financial_extractor.py` | ~500 | Financial data extraction from emails |
| `pubsub_client.py` | ~300 | Gmail Pub/Sub watch + notification pull |
| `notification.py` | ~200 | Discord webhook notifications for important emails |
| `sanitization.py` | ~500 | Content sanitization |
| `secret_scanner.py` | ~500 | Secret scanning on email content |
| `memory_store.py` | ~400 | Email memory/context store |
| `context_manager.py` | ~300 | Thread context management |
| `health.py` | ~200 | Health probe |
| `metrics.py` | ~100 | Prometheus metrics |
| `resend_client.py` | ~200 | Resend email API client |
| `commands/` | ~3 consent, ~3 digest | CLI command handlers |
| `tests/test_e2e_gmail.py` | ~200 | E2E tests |
| `grafana/` | dashboard | Grafana dashboard definition |

**Auth flow** (verified `config.py:54-57`, `token_manager.py:54-67`):
- Credentials loaded from SOPS-decrypted path: default `/run/guinevere/gmail-token.json`
- Scopes: `gmail.modify` (read, compose, send, manage labels)
- Token refresh: auto before expiry with 300s margin, backoff on failure (60-900s)
- Pub/Sub: GCP project `guinevere-gmail-prod`, topic `gmail-watch`, subscription `gmail-watch-sub`

### 1.3 X/Twitter API -- `src/x_poster/` (26 files, ~5,201 lines)

| File | Lines | Role |
|------|-------|------|
| `service.py` | ~600 | Main service wiring + lifecycle |
| `x_api_client.py` | ~600 | Official X API v2 client; OAuth 2.0 Bearer + auto-refresh |
| `poster.py` | ~200 | Post executor (media + caption) |
| `config.py` | ~200 | `XPosterSettings` via pydantic-settings (`X_POSTER_` prefix) |
| `caption_generator.py` | ~100 | Caption generation via Hermes |
| `circuit_breaker.py` | ~250 | Circuit breaker pattern |
| `queue_manager.py` | ~200 | Post queue management |
| `schedule_manager.py` | ~200 | Schedule slot allocation |
| `retry_engine.py` | ~100 | Retry with backoff |
| `moderator.py` | ~80 | Content moderation |
| `cleanup.py` | ~100 | Post cleanup |
| `storage.py` | ~250 | Media storage management |
| `db.py` | ~80 | Database connection manager |
| `notification.py` | ~150 | Discord webhook notifications |
| `summary.py` | ~200 | Daily summary generator |
| `health.py` | ~400 | Health probe |
| `metrics.py` | ~100 | Prometheus metrics |
| `timeout_handler.py` | ~80 | Timeout configuration |
| `exceptions.py` | ~50 | Typed exceptions |
| `structured_logging.py` | ~60 | Structured log helpers |
| `main.py` | ~80 | CLI entrypoint |
| `discord/` | ~150 total | Discord commands, dashboard, upload handler |
| `migrations/` | ~100 total | DB migrations |

**Auth model** (verified `x_api_client.py:37-74`):
- OAuth 2.0 Bearer Token with auto-refresh
- Token URL: `https://api.x.com/2/oauth2/token`
- Access token + refresh token + client_id from settings
- Media upload via `https://upload.twitter.com` (4MB chunks)

### 1.4 Telegram (Bot API) -- `src/life_integrations/adapters/` (2 files, ~350 lines)

| File | Lines | Role |
|------|-------|------|
| `telegram_adapter.py` | ~200 | Integration adapter: L1-L3 actions, CONFIG_MISSING pattern |
| `_clients/telegram_client.py` | ~250 | Thin async httpx Bot API wrapper |

**Architecture** (verified `telegram_adapter.py:1-43`, `telegram_client.py:1-100`):
- `TelegramIntegrationAdapter` extends `BaseIntegrationAdapter`
- Capabilities: READ, WRITE, DELETE, EXECUTE
- Actions: `get_updates` (L1), `send_message` (L2), `edit_message` (L2), `delete_message` (L3), `ban_member` (L3)
- Secret: `sec-telegram-bot-token` (SOPS -- NOT provisioned)
- Consent: `consent.comms.telegram.{read,write,delete}`
- `TelegramClient`: httpx-based, token embedded in URL path (`/bot<TOKEN>/METHOD`)
- Per-chat throttle: 1.05s minimum between messages to same chat
- Rate limit handling: respects `retry_after` from HTTP 429

---

## 2. Hermes Gateway Platform Layer (Upstream Reference)

### 2.1 `gateway/platforms/base.py` (4,287 lines)

**Core abstractions:**
- `BasePlatformAdapter` (ABC): `connect()`, `disconnect()`, `send()`, `edit_message()`, `delete_message()`, `send_draft()`
- `MessageEvent` dataclass: text, message_type (TEXT/PHOTO/VIDEO/AUDIO/VOICE/DOCUMENT/STICKER/COMMAND), source, media_urls, reply context, auto_skill, channel_prompt
- `SendResult` dataclass: success, message_id, error, retryable, continuation_message_ids
- `MessageType` enum, `ProcessingOutcome` enum

**Key patterns:**
- Image/audio/video/document cache dirs under `~/.hermes/cache/`
- SSRF protection via `is_safe_url()` + redirect guard
- Media delivery path validation with strict/non-strict modes
- Proxy support (SOCKS/HTTP) with platform-specific env vars
- Session management with interrupt support and busy-text debouncing
- Ephemeral replies with TTL-based auto-deletion

### 2.2 `gateway/platforms/telegram.py`

- Uses `python-telegram-bot` library
- Full `BasePlatformAdapter` implementation
- Handles commands, media, groups, inline keyboards
- Topic/thread support (forum topics, DM topics)
- Fallback transport via `telegram_network.py` (DoH resolution, seed IPs)

### 2.3 `gateway/platforms/whatsapp.py`

- Bridge pattern: supports multiple backends (WhatsApp Business API, whatsapp-web.js, Baileys)
- Node.js subprocess-based for personal accounts

### 2.4 `tools/send_message_tool.py`

- `SEND_MESSAGE_SCHEMA`: `send_message` tool for cross-channel messaging
- Actions: `send` (to target), `list` (available targets from channel_directory)
- Target format: `platform:#channel-name`, `platform:chat_id`, `platform:chat_id:thread_id`
- Supports: telegram, discord, slack, signal, whatsapp, matrix, feishu, weixin, yuanbao
- Media via `MEDIA:<local_path>` prefix

### 2.5 `gateway/channel_directory.py`

- Cached map of reachable channels/contacts per platform
- Built on gateway startup, refreshed every 5 min
- Stored at `~/.hermes/channel_directory.json`
- Platform-specific builders for Discord, Slack; session-based discovery for others

---

## 3. Disposition for P24 (Design M14)

### 3.1 WhatsApp -- `guinevere/channels/whatsapp/`

**Disposition: PORT**

Source: `src/channels/whatsapp/` (22 files, ~3,368 lines) is a mature, self-contained package.

Port mapping:
- `src/channels/whatsapp/*` -> `guinevere/channels/whatsapp/*` (all 22 files)
- Internal imports `src.channels.whatsapp.*` -> `guinevere.channels.whatsapp.*`
- Bridge import `src.core.services.prompt_loader` -> M3 consciousness bridge
- Bridge import `src.hermes.adapter` -> M3/M8 Hermes adapter

**External dependencies (live-only, CONFIG_MISSING in D2):**
- `neonize` library (installed in `.venv`)
- `redis.asyncio` (session persistence)
- `asyncpg` (optional, for Postgres health check)
- `prometheus_client` (metrics)
- `structlog` (logging)

**D2 CONFIG_MISSING markers needed:**
- `WHATSAPP_PHONE_NUMBER` env var
- `WHATSAPP_QR_MODE` env var
- Redis connection (`REDIS_URL`)
- Neonize session database (requires live WhatsApp connection)

**Tool registry integration (M8):**
- `send_message` (L2): outbound WhatsApp send via `WhatsAppIngressEgressAdapter.send_text()`
- `get_updates` (L1): inbound message handling via `NeonizeClient` event bus

**Consciousness tie-in (M3):**
- `WhatsAppHermesBridge` already calls `src.core.services.prompt_loader.get_system_prompt_with_context()`
- Autonomous sending: `TypingIndicator` + natural delay simulation
- The bridge is stateless -- M3 consciousness provides the session/context

### 3.2 Gmail -- `guinevere/channels/gmail/`

**Disposition: PORT**

Source: `src/gmail/` (36 files, ~12,723 lines) is the largest channel module.

Port mapping:
- `src/gmail/*` -> `guinevere/channels/gmail/*` (all 36 files)
- `src/gmail/commands/*` -> `guinevere/channels/gmail/commands/*`
- `src/gmail/draft/*` -> `guinevere/channels/gmail/draft/*`
- `src/gmail/grafana/*` -> `guinevere/channels/gmail/grafana/*`
- `src/gmail/tests/*` -> `guinevere/channels/gmail/tests/*`
- `src/gmail/migrations/*` -> `guinevere/channels/gmail/migrations/*`
- Bridge imports `src.core.services.*` -> M3 consciousness
- Bridge imports `src.hermes._memory_bridge` -> M3 memory

**External dependencies (CONFIG_MISSING in D2):**
- Google API client libraries (`google-api-python-client`, `google-auth-oauthlib`, `google-auth`)
- `redis.asyncio` (sync state, backfill cursors)
- `apscheduler` (sync scheduling)
- GCP Pub/Sub (`google-cloud-pubsub`)
- SOPS-decrypted credentials at `/run/guinevere/gmail-token.json`
- SOPS-decrypted service account at `/run/guinevere/gmail-sa.json`

**D2 CONFIG_MISSING markers needed:**
- All `GmailSettings` fields (credentials_path, client_id, client_secret, scopes, pubsub_*)

**Tool registry integration (M8):**
- `read_email` (L1): inbound email processing via `SyncEngine` + `PubSubClient`
- `send_email` (L2): outbound via `DraftSendPipeline` / `ResendClient`
- `draft_email` (L2): draft generation via `DraftGenerator` + Hermes bridge

**Consciousness tie-in (M3):**
- `GmailHermesBridge` calls `src.core.services.prompt_loader.get_system_prompt_with_context()`
- `HermesMemoryBridge` for email context in consciousness memory
- Briefing generator for autonomous daily email summaries
- Financial extractor for proactive financial monitoring

### 3.3 X/Twitter -- `guinevere/channels/x/`

**Disposition: PORT**

Source: `src/x_poster/` (26 files, ~5,201 lines).

Port mapping:
- `src/x_poster/*` -> `guinevere/channels/x/*` (all 26 files)
- `src/x_poster/discord/*` -> `guinevere/channels/x/discord/*`
- `src/x_poster/migrations/*` -> `guinevere/channels/x/migrations/*`
- References to `src.projects.secrets_vault` -> M1 secrets vault

**External dependencies (CONFIG_MISSING in D2):**
- `httpx` (API client)
- PostgreSQL (`asyncpg`)
- SOPS-decrypted X API credentials

**D2 CONFIG_MISSING markers needed:**
- `x_access_token`, `x_refresh_token`, `x_client_id`
- PostgreSQL connection settings
- `media_root`, `notification_webhook_url`, `discord_dashboard_channel_id`

**Tool registry integration (M8):**
- `post_tweet` (L2): outbound post via `XPoster.execute_post_batch()`
- `schedule_post` (L2): queue management via `QueueManager` + `ScheduleManager`
- `get_analytics` (L1): metrics retrieval via `XApiClient.get_tweet_metrics()`

**Consciousness tie-in (M3):**
- `CaptionGenerator` uses Hermes for autonomous caption generation
- Daily summary generator for proactive analytics
- Content moderation gate for autonomous posting safety

### 3.4 Telegram -- `guinevere/channels/telegram/`

**Disposition: REWRITE (partially)**

Source: Two separate implementations exist:

1. **Hermes upstream** (`gateway/platforms/telegram.py`, `gateway/platforms/telegram_network.py`): 2,500+ lines, full `BasePlatformAdapter` with `python-telegram-bot` library. Production-grade but tightly coupled to Hermes gateway internals.

2. **Guinevere integration** (`src/life_integrations/adapters/telegram_adapter.py`, `_clients/telegram_client.py`): ~350 lines, clean `BaseIntegrationAdapter` with httpx-based Bot API client. CONFIG_MISSING pattern, consent scopes, permission tiers.

**Strategy:** Rewrite as a synthesis:
- Take the clean httpx client from `src/life_integrations/adapters/_clients/telegram_client.py` (already isolated, testable)
- Take the integration adapter pattern from `src/life_integrations/adapters/telegram_adapter.py`
- Reference Hermes `gateway/platforms/telegram.py` for feature completeness (media handling, topic/thread support, inline keyboards)
- Build `guinevere/channels/telegram/` with the same safety pipeline structure as WhatsApp

Files to create (synthesis):
- `client.py` -- from `_clients/telegram_client.py` (PORT, extend)
- `adapter.py` -- from `telegram_adapter.py` (PORT, extend with media/topics)
- `service.py` -- NEW (modeled on WhatsApp service pattern)
- `envelope.py` -- NEW (Telegram-specific DTOs, modeled on WhatsApp envelope)
- `router.py` -- NEW (command/conversation classification)
- `formatter.py` -- NEW (Markdown-to-Telegram conversion)
- `consent_manager.py` -- PORT from WhatsApp pattern
- `hard_stop.py` -- PORT from WhatsApp pattern (shared handler)
- `rate_limiter.py` -- PORT from WhatsApp pattern
- `policy.py` -- PORT from WhatsApp pattern
- `health.py` -- NEW
- `metrics.py` -- NEW

**D2 CONFIG_MISSING markers needed:**
- `sec-telegram-bot-token` (SOPS -- NOT provisioned)

**External dependencies:**
- `httpx` (API client -- already used)
- `redis.asyncio` (session persistence)
- Optional: `python-telegram-bot` for advanced features (inline keyboards, forum topics)

**Tool registry integration (M8):**
- `send_message` (L2): outbound via TelegramClient
- `get_updates` (L1): inbound via long-polling (`getUpdates`) or webhook
- `edit_message` (L2): message editing
- `delete_message` (L3): message deletion with pre-delete snapshot

**Consciousness tie-in (M3):**
- Build bridge pattern matching `WhatsAppHermesBridge` -- stateless bridge to prompt_loader
- Topic/thread support for per-conversation consciousness contexts

---

## 4. Cross-Cutting Concerns

### 4.1 MCP -> Native Tool Migration (M8)

The `tools/send_message_tool.py` in Hermes is a cross-channel send tool that dispatches to platform adapters. For P24:

- This becomes a native tool in `guinevere/tools/send_message.py` (M8 tool registry)
- Target resolution: `platform:target_id` format preserved
- Channel directory: `guinevere/channels/_registry.py` (auto-discovery of installed channels)
- Media delivery: `MEDIA:<local_path>` prefix pattern preserved

### 4.2 Consciousness Integration (M3)

Each channel's bridge calls `get_system_prompt_with_context()` from prompt_loader. For M3:
- Each channel's bridge becomes a channel-specific consciousness interface
- Autonomous sending: consciousness can initiate outbound messages on any channel
- Session isolation: per-channel session keys (e.g., `wa:<jid_hash>`, `tg:<chat_id>`, `gmail:<thread_id>`)
- Memory integration: `HermesMemoryBridge` already used by Gmail; extend to all channels

### 4.3 Safety Pipeline Consistency

All channels should share the same safety pipeline structure:
1. Whitelist (identity gate)
2. Hard Stop (shared `HardStopHandler`)
3. Consent (per-channel consent manager)
4. Dedup + Rate Limit
5. Policy (channel-specific media/group rules)
6. Bridge (Hermes runtime)

WhatsApp already implements this fully. Gmail and X partially implement it (hard_stop + consent). Telegram needs the full pipeline.

---

## 5. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Neonize library instability (WhatsApp protocol changes) | HIGH | Pin neonize version; session blob allows reconnection |
| Gmail OAuth token expiry in long-running service | MEDIUM | TokenManager has auto-refresh with backoff (60-900s) |
| X API rate limits (50 tweets/day for free tier) | MEDIUM | Circuit breaker + schedule manager with min 180s gap |
| Telegram bot token exposure in URL paths | MEDIUM | httpx logger level raised to WARNING; URL logging suppressed |
| Redis dependency for all channel state | HIGH | All channels fail-closed on Redis errors |
| Channel-to-consciousness bridge coupling | MEDIUM | Bridge is stateless; consciousness/session is injected |
| Import path changes during src/ to guinevere/ migration | LOW | Mechanical find-replace; grep-verified |

---

## 6. Verdict

**PASS** -- All four external channels have sufficient source material for the M14 design. WhatsApp, Gmail, and X are straightforward PORT operations (code exists and is self-contained). Telegram requires a REWRITE (synthesis of two incomplete implementations into a full channel package). All channels follow compatible patterns (safety pipeline, bridge to consciousness, Prometheus metrics) that can be unified under `guinevere/channels/`.

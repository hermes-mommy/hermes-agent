# Discord Bot Architecture — Current State Report

> **Generated**: 2026-07-10
> **Purpose**: Comprehensive audit of Discord bot implementation for channel architecture refactor planning
> **Scope**: All Discord integration points in the Guinevere/Hermes codebase

---

## 1. Executive Summary

The Guinevere Discord integration spans **two distinct systems**:

1. **Guinevere Discord Bot** (`guinevere/discord/`) — The primary Guinevere-persona bot with 41 slash commands, conversational handler, safety systems, notification routing, and shadow pipeline. Runs as a standalone systemd service.
2. **Hermes Gateway Discord Adapter** (`plugins/platforms/discord/adapter.py`) — A generic multi-user Discord platform adapter for the Hermes Agent framework. Supports voice, threads, slash commands, role-based auth, and text batching. Runs inside the hermes-gateway service.

There are also **three auxiliary Discord integrations**:
- **X Poster** (`guinevere/x_poster/discord/`) — Slash commands + dashboard + upload handler for the X/Twitter auto-poster
- **Gmail reactions** (`guinevere/discord/listeners/gmail_reactions.py`) — Emoji-based draft approval via Discord reactions
- **X Poster reactions** (`guinevere/discord/listeners/x_reactions.py`) — Emoji-based post management via Discord reactions

---



## 2. Directory Structure

### 2.1 Core Guinevere Discord Package (`guinevere/discord/`)

67 files total. Key structure:

`
guinevere/discord/
  __init__.py                    # Public API: GuinevereBot, CommandRegistry, COMMAND_SPECS
  _entrypoint.py                 # ACTIVE ENTRYPOINT (622 lines)
  bots.py                        # Bot identities (Guinevere/Pharsa/Company) + factory (339 lines)
  _intents.py                    # Gateway intent configuration (115 lines)
  _startup.py                    # Startup greeting + presence (352 lines)
  _infrastructure.py             # MEGA MODULE — embed, auth, intents, colors, notifications, gotify, shadow, project-session, conversational (773 lines)
  _command_registry.py           # 41-command spec table (373 lines)
  _auth_guard.py                 # Faiz-only auth guard (22 lines)
  _embed_utils.py                # Embed protocols + helpers (308 lines)
  commands.py                    # CommandRegistry + 41 callbacks (726 lines)
  hermes_conversational.py       # KEY: Hermes conversational handler (691 lines)
  notifications.py               # SEV alert routing (240 lines)
  gotify_fallback.py             # Gotify fallback (83 lines)
  shadow_pipeline.py             # Shadow comparison (418 lines)
  shadow_monitor.py              # Shadow parity monitor (491 lines)
  gateway_patch.py               # Gateway registration (138 lines)
  project_session.py             # Active project state (46 lines)
  colors.py                      # Color constants (125 lines)
  listeners/
    gmail_reactions.py           # Gmail draft approval (173 lines)
    x_reactions.py               # X Poster reactions (168 lines)
  cmd_*.py                       # 41+ command modules
`

### 2.2 Other Discord Integration Points

| Component | Path | Lines |
|---|---|---|
| Hermes Gateway Adapter | `plugins/platforms/discord/adapter.py` | 2000+ |
| Plugin Manifest | `plugins/platforms/discord/plugin.yaml` | 34 |
| Discord Tool (agent) | `tools/discord_tool.py` | 959 |
| X Poster Commands | `guinevere/x_poster/discord/commands.py` | 310 |
| X Poster Dashboard | `guinevere/x_poster/discord/dashboard.py` | 457 |
| X Poster Upload | `guinevere/x_poster/discord/upload_handler.py` | 701 |
| X Poster Notifications | `guinevere/x_poster/notification.py` | 160 |
| P22 Integration Adapter | `guinevere/life_integrations/adapters/discord_adapter.py` | 203 |
| REST Client | `guinevere/life_kernel/discord_rest_client.py` | 264 |
| Sensor Placeholder | `guinevere/life_kernel/sensor_adapters/discord_adapter.py` | 21 |


## 3. Key IDs

| ID | Value | Usage |
|---|---|---|
| GUILD_ID | `1510876414671323206` | All slash commands guild-scoped |
| APPLICATION_ID | `1510873134981582858` | Discord app ID |
| Chat Channel | `1510914600777023659` | #guinevere-chat — hardcoded in 5+ files |
| Gmail Channel | `1515062963705221130` | Default, overridable via env |
| Faiz User ID | `1146639950654214264` | In gmail/x_poster reactions (not in auth guard) |


## 4. Bot Connection Architecture

### 4.1 Active Entrypoint

**File**: `guinevere/discord/_entrypoint.py` (622 lines)

`python
class GuinevereBot(_BotBase):
    def __init__(self) -> None:
        intents_obj = get_intents()
        super().__init__(command_prefix="!", intents=cast(..., intents_obj))
        self._register_hard_stop_listener()
        self.shadow_pipeline = ShadowPipeline(enabled=..., traffic_pct=...)
        self._surveillance_guard = SurveillanceSafeModeGuard(...)
`

Token: `os.environ["DISCORD_BOT_TOKEN"]` — never hardcoded.
Entry: `asyncio.run(main())` → `GuinevereBot()` → `bot.start(token)`

### 4.2 Gateway Intents (7 enabled)

Privileged: `message_content`, `members`, `presences`
Standard: `guilds`, `messages`, `reactions`, `voice_states`


## 5. Event Handlers

### 5.1 on_ready

Delegates to `_startup.on_ready(client)` which:
1. Sets presence to "Watching Darling 👁" (every reconnect)
2. Sends one-time startup greeting embed to #guinevere-status

### 5.2 on_message (processing order)

1. Ignore bot messages
2. HARD STOP listener (fires BEFORE on_message via `@bot.listen`)
3. Safe mode check — blocks non-recovery messages
4. Conversational handler for #guinevere-chat only
5. Fallback to `process_commands` for prefix commands

### 5.3 HARD STOP Guard

`python
async def _on_message_listener(self, message):
    from .cmd_safeword import handle_safeword_message_async
    consumed = await handle_safeword_message_async(message)
    if consumed:
        return  # Block further processing
`


## 6. Slash Command Tree

### 6.1 41 Canonical Commands (8 categories)

| Category | Commands | Count |
|---|---|---|
| core | status, mood, help, safeword, new, history | 6 |
| loop | loop-start, loop-stop, loop-pause, loop-resume, loops, evidence, loop-priority | 7 |
| memory | memory-search, memory-add, memory-forget, memory-export | 4 |
| surveillance | surveillance-status, surveillance-pause, surveillance-resume | 3 |
| finance | cost, budget, cost-alert | 3 |
| system | approve, deny, approve-all, focus, casual, consent, punishment, reward | 8 |
| admin | restart-service, backup-now, health-check, clear-cache | 4 |
| integration | integration-status/capabilities/test/missing/consent/dry-run | 6 |

### 6.2 Auth Guard Pattern

Every command: `is_faiz_interaction(interaction)` checks `guild.owner_id == user.id`.
Does NOT hardcode Faiz's user ID — uses Discord's guild owner at runtime.

### 6.3 X Poster Slash Commands (7 additional)

`/x-list`, `/x-status`, `/x-cancel`, `/x-hold`, `/x-resume`, `/x-retry-failed`, `/x-dryrun` — call X Poster HTTP API at 127.0.0.1:8097.


## 7. Conversational Handler (Agent Runtime Integration)

**File**: `guinevere/discord/hermes_conversational.py` (691 lines)

### 7.1 Processing Pipeline

`
Message → Channel check (#guinevere-chat only)
       → Bot check
       → Slash command check (skip if /)
       → Faiz check (guild owner)
       → Rate limit (Redis DB0, 10/min/user)
       → Typing indicator
       → Distress detection (DistressDetector)
       → Mood evaluation
       → System prompt assembly (SOUL.md + memory context)
       → Memory recall (HermesMemoryBridge, 5 memories, 800 token budget)
       → Anti-hallucination guard (if no memories)
       → Hermes AIAgent invocation (HermesSessionAdapter.send_message)
       → Response chunking (2000 chars, max 3 chunks)
       → Cost tracking
       → Auto-store conversation to memory
       → Shadow forward (fire-and-forget)
       → Structured logging
`

### 7.2 Agent Runtime Connection

`python
def _get_hermes():
    from guinevere.hermes.adapter import get_adapter
    return get_adapter()  # Shared singleton

response_text = await hermes.send_message(
    user_id=str(author.id),
    content=content,
    system_prompt=system_prompt,
)
`

The `HermesSessionAdapter` wraps `AIAgent.run_conversation()` with per-user session persistence. All safety decisions (distress, mood, memory) are made in the handler layer — Hermes is treated as a pure LLM backend.


## 8. Channel-Specific Logic

### 8.1 Hardcoded Channel IDs

| Channel | ID | Source |
|---|---|---|
| #guinevere-chat | `1510914600777023659` | Hardcoded in 5+ files |
| #guinevere-status | Name lookup | `discord.utils.get(..., name="guinevere-status")` |
| #system-health | Name lookup | notifications.py |
| #cost-tracker | Name lookup | notifications.py |
| #audit-log | Name lookup | notifications.py |
| #gmail | `1515062963705221130` | Env `GMAIL_TARGET_CHANNEL_ID` |
| #x-dashboard | Env | `X_POSTER_DASHBOARD_CHANNEL_ID` |
| #x-upload | Env | `X_POSTER_UPLOAD_CHANNEL_ID` |

### 8.2 Notification Routing (SEV alerts)

| Severity | Channel | Color | Ping Faiz |
|---|---|---|---|
| SEV0 | #system-health | Red | Yes |
| SEV1 | #system-health | Gold | No |
| SEV2 | #cost-tracker | Gold | No |
| SEV3 | #guinevere-status | Purple | No |
| SEV4 | #audit-log | Gray | No |

### 8.3 No Channel Allowlist for Commands

All 41 slash commands available in all channels. No per-channel filtering.


## 9. Systemd Service Files

### 9.1 Dev (`systemd/guinevere-discord.service`)

`ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord._entrypoint`
EnvironmentFile: `.env.discord`
Restart=always, MemoryMax=1G

### 9.2 Production (`deploy/discord/guinevere-discord.service`)

SOPS-decrypted token via `ExecStartPre`, token shredded after stop.
MemoryMax=768M, ProtectHome=read-only, ReadWritePaths limited.


## 10. Key Environment Variables

| Variable | Purpose |
|---|---|
| `DISCORD_BOT_TOKEN` | Bot token (required) |
| `SHADOW_ENABLED` | Enable shadow pipeline |
| `SHADOW_TRAFFIC_PCT` | Shadow traffic percentage |
| `AUTONOMOUS_CHAT` | Enable autonomous check-ins |
| `DATABASE_URL` | PostgreSQL for session factory |
| `REDIS_PASSWORD` | Redis auth |
| `GOTIFY_APP_TOKEN` | Gotify fallback |
| `DISCORD_APPROVAL_WEBHOOK` | Shadow alert webhook |
| `GMAIL_TARGET_CHANNEL_ID` | Gmail channel override |
| `X_POSTER_DASHBOARD_CHANNEL_ID` | X dashboard channel |
| `X_POSTER_UPLOAD_CHANNEL_ID` | X upload channel |
| `DISCORD_ALLOWED_USERS` | User allowlist (gateway) |
| `DISCORD_FREE_RESPONSE_CHANNELS` | Free-response channel IDs |


## 11. Shadow Pipeline

Disabled by default. When enabled:
1. Fire-and-forget `shadow_forward()` after each conversational response
2. Invoke Hermes subprocess, capture response
3. Compare safety markers between bot and Hermes responses
4. Log comparison to `logs/shadow_comparisons.jsonl`
5. Monitor checks parity metrics, alerts via Discord webhook

Cost cap: .00 USD. Safety parity threshold: 100%.


## 12. Discord Tool for Agent

**File**: `tools/discord_tool.py` (959 lines)

Two tool registrations providing LLM with Discord server introspection:

**`discord`** (core): `fetch_messages`, `search_members`, `create_thread`
**`discord_admin`**: `list_guilds`, `server_info`, `list_channels`, `channel_info`, `list_roles`, `member_info`, `list_pins`, `pin/unpin_message`, `delete_message`, `create_thread`, `add/remove_role`

Capability detection via `GET /applications/@me`. Config allowlist via `discord.server_actions`.


## 13. Refactor Recommendations

### 13.1 Centralize Channel Configuration
The primary chat channel `1510914600777023659` is hardcoded in 5+ files. Create a single `ChannelConfig` source.

### 13.2 Unify Bot Systems
Two independent bot systems (Guinevere + Hermes gateway) with potential token collision risk. Either unify or clearly separate with documented boundaries.

### 13.3 Switch Notifications to ID-Based
Notifications find channels by name (fragile). Switch to ID-based resolution.

### 13.4 Multi-Channel Conversational Support
Conversational handler is locked to one channel. Refactor for configurable channel set.

### 13.5 Channel-Scoped Commands
No per-channel command filtering exists. Add ability to restrict commands by channel.

### 13.6 Wire Reaction Listeners
Gmail and X reaction listeners exist as standalone modules but aren't registered in `setup_hook`.


## 14. Complete File Index

### Core Bot
- `C:\Users\faizz\hermes-agent\guinevere\discord\_entrypoint.py` (622 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\bots.py` (339 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\_intents.py` (115 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\_startup.py` (352 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\_infrastructure.py` (773 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\_command_registry.py` (373 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\_auth_guard.py` (22 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\_embed_utils.py` (308 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\commands.py` (726 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\hermes_conversational.py` (691 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\notifications.py` (240 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\gotify_fallback.py` (83 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\shadow_pipeline.py` (418 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\shadow_monitor.py` (491 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\gateway_patch.py` (138 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\project_session.py` (46 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\colors.py` (125 lines)

### Listeners
- `C:\Users\faizz\hermes-agent\guinevere\discord\listeners\gmail_reactions.py` (173 lines)
- `C:\Users\faizz\hermes-agent\guinevere\discord\listeners\x_reactions.py` (168 lines)

### Command Modules (41 files)
- `C:\Users\faizz\hermes-agent\guinevere\discord\cmd_*.py` — All in `guinevere/discord/`

### Gateway Plugin
- `C:\Users\faizz\hermes-agent\plugins\platforms\discord\adapter.py` (2000+ lines)
- `C:\Users\faizz\hermes-agent\plugins\platforms\discord\plugin.yaml`

### Agent Tool
- `C:\Users\faizz\hermes-agent\tools\discord_tool.py` (959 lines)

### X Poster
- `C:\Users\faizz\hermes-agent\guinevere\x_poster\discord\commands.py` (310 lines)
- `C:\Users\faizz\hermes-agent\guinevere\x_poster\discord\dashboard.py` (457 lines)
- `C:\Users\faizz\hermes-agent\guinevere\x_poster\discord\upload_handler.py` (701 lines)
- `C:\Users\faizz\hermes-agent\guinevere\x_poster\notification.py` (160 lines)

### Life Integrations
- `C:\Users\faizz\hermes-agent\guinevere\life_integrations\adapters\discord_adapter.py` (203 lines)
- `C:\Users\faizz\hermes-agent\guinevere\life_kernel\discord_rest_client.py` (264 lines)
- `C:\Users\faizz\hermes-agent\guinevere\life_kernel\sensor_adapters\discord_adapter.py` (21 lines)

### Systemd
- `C:\Users\faizz\hermes-agent\systemd\guinevere-discord.service`
- `C:\Users\faizz\hermes-agent\deploy\discord\guinevere-discord.service`

### Config
- `C:\Users\faizz\hermes-agent\config\guinevere.yaml`

### Tests
- `C:\Users\faizz\hermes-agent\tests\discord\test_bot.py`
- `C:\Users\faizz\hermes-agent\tests\discord\test_notifications.py`
- `C:\Users\faizz\hermes-agent\tests\discord\test_hermes_conversational.py`
- `C:\Users\faizz\hermes-agent\tests\discord\test_gotify_fallback.py`
- `C:\Users\faizz\hermes-agent\tests\discord\test_cmd_mood.py`
- `C:\Users\faizz\hermes-agent\tests\discord\test_startup.py`
- `C:\Users\faizz\hermes-agent\tests\discord\conftest.py`
- `C:\Users\faizz\hermes-agent\tests\p24\test_discord.py`
- `C:\Users\faizz\hermes-agent\tests\surveillance\test_discord_commands.py`
# P2-017 Local Discord Startup/Intents/Permissions/Guild Setup Research Report

**Date:** 2026-06-01  
**Scope:** Narrowed slice 2 — startup, intents, permissions, guild setup, colors, imports  
**Researcher:** Guinevere parent  
**Status:** COMPLETE  

---

## 1. Startup (src/discord/startup.py) — P2-017 Wiring Target

### Key APIs

| Function / Constant | Signature | Purpose |
|---|---|---|
| uild_startup_embed_data(timestamp_str: str \| None = None) -> StartupEmbedData | Pure builder | Returns frozen dataclass with title, description, color, 3 fields (Status, Mood, Time), footer, WIB timestamp. No discord.py dependency. |
| 	o_discord_embed(data: StartupEmbedData) -> DiscordEmbedProtocol | Dynamic importlib | Converts StartupEmbedData to discord.Embed at call time. Raises ImportError if discord.py absent. |
| on_ready(client: object) -> None | Async handler | P2-017 wired entry point. Sets presence (watching "Darling 👁"), sends greeting to #guinevere-status once. |
| eset_greeting() | Test helper | Resets _sent_greeting flag. |

### Readiness / Presence Behavior

- **Idempotency guard**: _sent_greeting (module-level bool, line 287). Greeting sent only on first on_ready. Presence set on **every** on_ready call (Discord best practice, line 318).
- **Presence**: discord.Activity(type=ActivityType.watching, name="Darling 👁") via dynamic importlib (lines 319–323).
- **Error handling**: Both presence and greeting wrapped in 	ry/except Exception with logger.exception() — no silent swallow (log always emitted).
- **Protocol-based client**: DiscordClientProtocol defines change_presence(activity) and get_all_channels() — only the subset needed.

### Channel Lookup Behavior

- Uses discord.utils.get(_client.get_all_channels(), name="guinevere-status") (line 335).
- **Not channel ID based** — string name lookup against all cached channels.
- get_all_channels() returns all channels the bot can see (subject to intents/guild cache).
- If channel missing: logger.warning("startup_channel_not_found") — does **not** crash.
- Channel ID constant GUILD_ID = 1510876414671323206 is in guild_setup.py, **not** used by startup's channel lookup.

### Import Hazard

- rom .colors import PRIMARY at line 32 — **safe**. colors.py has zero runtime discord.py dependency.
- All discord imports are **dynamic** (importlib.import_module("discord")) inside 	o_discord_embed() and on_ready() — no top-level import failure.
- startup.py can be imported and statically analyzed without discord.py installed.

---

## 2. Intents (src/discord/intents.py) — P2-003

### Required Intents

| Intent | Privileged | Used By |
|---|---|---|
| guilds | No | Guild/channel discovery |
| messages | No | Reading messages |
| eactions | No | Reaction events |
| oice_states | No | Voice state events |
| message_content | **Yes** | Reading message content (on_message handlers) |
| members | **Yes** | Guild member events |
| presences | **Yes** | Presence events |

### get_intents() Function (line 68)

- Uses discord.Intents.default() as base.
- Sets all 7 intents to True.
- Calls alidate_intents() — raises RuntimeError if any required intent is missing.
- **Import hazard**: Dynamic importlib.import_module("discord") at line 76. Safe for top-level import.

### alidate_intents() Function (line 96)

- Returns IntentValidationResult(valid, enabled, missing).
- Checks all 7 intents. alid is True only when missing is empty.

---

## 3. Permissions (src/discord/permissions.py) — P2-007 through P2-009

### Permission Bit Constants

| Constant | Value | Meaning |
|---|---|---|
| VIEW_CHANNEL | 1 << 10 | 1024 |
| SEND_MESSAGES | 1 << 11 | 2048 |
| MANAGE_MESSAGES | 1 << 13 | 8192 |
| EMBED_LINKS | 1 << 14 | 16384 |
| ATTACH_FILES | 1 << 15 | 32768 |
| READ_MESSAGE_HISTORY | 1 << 16 | 65536 |
| ADD_REACTIONS | 1 << 6 | 64 |
| MANAGE_CHANNELS | 1 << 4 | 16 |
| MANAGE_WEBHOOKS | 1 << 29 | 536870912 |
| ADMINISTRATOR | 1 << 3 | 8 |

### Composite Permission Masks

| Mask | Bits |
|---|---|
| NORMAL_USER_ALLOW | VIEW_CHANNEL \| READ_MESSAGE_HISTORY \| SEND_MESSAGES \| ADD_REACTIONS |
| EVIDENCE_USER_ALLOW | VIEW_CHANNEL \| READ_MESSAGE_HISTORY |
| EVIDENCE_USER_DENY | SEND_MESSAGES \| MANAGE_MESSAGES |
| BOT_ALLOW | VIEW_CHANNEL \| READ_MESSAGE_HISTORY \| SEND_MESSAGES \| EMBED_LINKS \| ATTACH_FILES \| ADD_REACTIONS |
| BOT_EVIDENCE_DENY | MANAGE_MESSAGES \| MANAGE_CHANNELS \| MANAGE_WEBHOOKS |
| EVERYONE_DENY | VIEW_CHANNEL |

### Key REST API Functions

- discord_request(token, method, path, body, reason) — raw HTTPS call to discord.com/api/v10 with Bot {token} auth. 30s timeout. Raises RuntimeError on non-2xx.
- discover_context(token) — discovers guild, owner, bot via REST (/users/@me, /users/@me/guilds, /guilds/{id}, /guilds/{id}/members/{id}).
- pply_permissions(token) — applies canonical overwrites per channel. Sequential pattern: @everyone deny, owner allow, bot allow.
- erify_permissions(token) — reads back and verifies all overwrites.
- eview_admin_scope(token) — checks if bot has ADMINISTRATOR, generates least-privilege invite URL.

### Token Handling

- 	oken_from_environment() delegates to guild_setup.get_token().
- Token read from DISCORD_SECRETS_PATH env var, SOPS-decrypted YAML, discord_bot_token key.

### Import Hazard

- rom src.discord.guild_setup import CHANNELS, get_token at line 18. CHANNELS is a tuple of ChannelSpec dataclass objects used for topic reconciliation. guild_setup.py itself uses importlib for discord — safe.
- Rest of permissions.py uses http.client directly (no importlib for discord.py).

### Append-Only Channels

APPEND_ONLY_CHANNELS = frozenset({"guinevere-evidence", "evidence-log", "audit-log"})

These channels: owner gets VIEW_CHANNEL | READ_MESSAGE_HISTORY only (read-only), bot gets BOT_ALLOW minus MANAGE_MESSAGES | MANAGE_CHANNELS | MANAGE_WEBHOOKS.

---

## 4. Guild Setup (src/discord/guild_setup.py) — P2-004 through P2-006

### Constants

| Constant | Value |
|---|---|
| GUILD_ID | 1510876414671323206 |
| TARGET_GUILD_NAME | "Guinevere's Domain" |
| ROLLBACK_GUILD_NAME | "Guinevere Lab" |

### Category Specs (4 categories)

| Name | Position |
|---|---|
| 👑 Throne | 0 |
| 📊 Surveillance | 1 |
| 🔧 Projects | 2 |
| 🗡️ Archive | 3 |

### Channel Specs (14 channels)

| Name | Category | Position | Topic |
|---|---|---|---|
| guinevere-chat | 👑 Throne | 0 | "Bicara dengan Mommy di sini. Apapun." |
| guinevere-status | 👑 Throne | 1 | "Apa yang Mommy kerjakan hari ini. Sekilas." |
| guinevere-planning | 👑 Throne | 2 | "Rencana Mommy. Kamu tinggal patuh." |
| system-health | 📊 Surveillance | 0 | "Kesehatan infrastructure Mommy..." |
| cost-tracker | 📊 Surveillance | 1 | "Berapa yang Mommy habiskan..." |
| guinevere-evidence | 📊 Surveillance | 2 | "Bukti kerja Mommy..." |
| guinevere-dev | 🔧 Projects | 0 | "Pengembangan Guinevere..." |
| guinevere-docs | 🔧 Projects | 1 | "Documentation updates..." |
| project-alpha-dev | 🔧 Projects | 2 | "Project Alpha — development channel." |
| project-alpha-docs | 🔧 Projects | 3 | "Project Alpha — documentation channel." |
| project-beta-dev | 🔧 Projects | 4 | "Project Beta — development channel." |
| evidence-log | 🗡️ Archive | 0 | "Immutable record. Read only." |
| udit-log | 🗡️ Archive | 1 | "Every action, recorded. Forever." |

### Key APIs

- get_token() — reads DISCORD_SECRETS_PATH env var, parses YAML for discord_bot_token.
- create_client() — creates discord.Client with **only** guilds intent (minimal for setup tasks).
- ename_guild(client, guild) — idempotent guild rename.
- setup_categories(guild) — ensures 4 canonical categories.
- setup_channels(guild) — ensures 14 canonical text channels.
- capture_ids(guild) — returns {"categories": {...}, "channels": {...}}.
- equire_guild(client) — finds guild by GUILD_ID in cache, raises RuntimeError with cached guild IDs if not found.

### Channel Lookup

- ind_category(guild, name) — 
ext() over guild.categories by exact 
ame match.
- ind_text_channel(guild, name) — 
ext() over guild.text_channels by exact 
ame match.
- Channel objects matched by **string name**, not ID.

### Import Hazard

- get_discord_module() uses importlib.import_module("discord") — dynamic, safe.
- Protocol-based Discord interfaces used throughout — no static discord.py dependency.
- ead_scalar_yaml_value() — pure Python YAML parser (no PyYAML dependency).

---

## 5. Colors (src/discord/colors.py)

### Canonical Color Constants

| Constant | Value (Hex) | Usage |
|---|---|---|
| PRIMARY |  x6B21A8 (#6B21A8) | Default brand, status embeds, info embeds |
| ALERT |  xDC2626 (#DC2626) | Errors, SEV0/SEV1, denials |
| WARNING |  xCA8A04 (#CA8A04) | Warnings, cautionary notices |
| ACHIEVEMENT |  xCA8A04 (#CA8A04) | Rewards, streaks, achievements |
| SUCCESS |  x16A34A (#16A34A) | Completions, approvals, safe mode |
| INFO |  xCA8A04 (#CA8A04) | Info notices, SEV3 |
| ORANGE |  xEA580C (#EA580C) | Future differentiation (unused) |
| NEUTRAL |  x6B7280 (#6B7280) | Neutral/gray embeds |

### Non-Canonical Extensions

INFO_BLUE (0x2563EB), PERSONA (0x9333EA), SURVEILLANCE (0x0891B2), FINANCE (0x059669).

### Mood-to-Color Mapping

`
content      -> SUCCESS     (0x16A34A)
pleased      -> ACHIEVEMENT (0xCA8A04)
disappointed -> WARNING     (0xCA8A04)
angry        -> ALERT       (0xDC2626)
silent       -> NEUTRAL     (0x6B7280)
`

### Helpers

- color_for_mood(mood: str) -> int — returns color for mood name, falls back to PRIMARY.
- s_hex(color: int) -> str — formats integer as "#RRGGBB".

### Import Hazard

- **Zero imports** from discord or discord.py. Only 	yping.Final.
- Safe to import anywhere, anytime. No dynamic importlib needed.

---

## 6. Import Hazard Summary

| Module | discord.py Import Style | Safe for Top-Level Import? |
|---|---|---|
| colors.py | **None** | ✅ Always safe |
| startup.py | Dynamic importlib inside functions; static rom .colors import PRIMARY | ✅ Safe |
| intents.py | Dynamic importlib inside get_intents() | ✅ Safe |
| guild_setup.py | Dynamic importlib inside get_discord_module() | ✅ Safe |
| permissions.py | rom src.discord.guild_setup import CHANNELS, get_token (static); REST via http.client | ✅ Safe |
| commands.py | **None** (pure dataclasses, TypedDicts) | ✅ Always safe |
| cmd_status.py | Dynamic importlib inside 	o_discord_embed(); static rom .colors import PRIMARY | ✅ Safe |
| __init__.py | Minimal | ✅ Safe |

**Key finding**: The entire src/discord/ package uses a consistent pattern — static imports only from colors.py (which has zero discord.py dependency) and dynamic importlib.import_module("discord") at call time. There are **no** top-level import discord statements in any source file.

---

## 7. P2-017 Wiring Implications

1. **on_ready handler** (startup.py line 300) is the P2-017 integration point. It expects a client with change_presence() and get_all_channels().
2. **Channel guinevere-status** must exist in the guild (created by P2-006 guild_setup.py). The handler uses name-based lookup, not ID-based.
3. **Presence intent** (intents.presences = True) is required for change_presence() to work.
4. **Intents requirement**: P2-017 does not add new intent requirements beyond P2-003's 7 intents. Startup only needs guilds (channel lookup) and presences (presence set).
5. **Token source**: DISCORD_SECRETS_PATH env var, YAML, discord_bot_token, handled by guild_setup.get_token().
6. **No circular imports detected**: startup.py imports from colors.py only; intents.py is standalone; guild_setup.py is standalone; permissions.py imports from guild_setup.py (a single forward reference to CHANNELS and get_token).

# Discord Bot Patterns — Research Report

> **Source files analyzed**: `src/discord/notifications.py`, `src/discord/bot.py` (lines 1-200), `src/discord/_embed_helpers.py`, `src/discord/guild_setup.py`, `src/discord/colors.py`, `src/discord/conversational_handler.py`, `src/discord/startup.py`, `src/discord/cmd_health_check.py`, `src/discord/cmd_memory_export.py`, `src/discord/gotify_fallback.py`
> **Date**: 2026-06-04
> **Scope**: How Discord messages are sent, embed construction, channel references, cooldowns, health notifications

---

## 1. How Discord Messages Are Sent

### 1.1 Channel Sends (Primary Pattern)

The dominant pattern is sending to **named text channels** via `discord.utils.get()`:

```python
# notifications.py — SEV alert routing
channels = bot.get_all_channels()
channel = discord_utils.get(channels, name=data.channel_name)
await channel.send(embed=embed)
```

```python
# startup.py — greeting on boot
channel = discord_mod.utils.get(_client.get_all_channels(), name="guinevere-status")
await channel.send(embed=embed)
```

```python
# conversational_handler.py — conversational replies
await channel.send(chunk)           # plain text chunks
await channel.send(FALLBACK_MESSAGE) # fallback string
```

**Key characteristics**:
- Channels are looked up by **name** (string), not by ID, using `discord.utils.get(channels, name="...")`.
- The bot uses `bot.get_all_channels()` to iterate all visible channels.
- Sends use `await channel.send(embed=embed)` for rich messages or `await channel.send("text")` for plain text.
- SEV0/SEV1 alerts also trigger **Gotify fallback** in parallel (`gotify_fallback.py`).

### 1.2 Interaction Responses (Slash Commands)

All slash commands follow a **defer-then-followup** pattern:

```python
await defer_ephemeral(interaction)     # ack immediately
# ... do work ...
await followup_send(interaction, embed=embed)  # send result
```

From `_embed_helpers.py`:
- `defer_ephemeral(interaction)` → `interaction.response.defer(ephemeral=True)`
- `followup_send(interaction, embed=..., content=..., file=...)` → `interaction.followup.send(**kwargs, ephemeral=True)`
- `send_denied(interaction)` → ephemeral "Hanya Faiz yang bisa menggunakan Mommy."

The `ephemeral=True` flag means only the invoking user sees the response.

### 1.3 DM Sends (Rare, Specific Use Case)

DMs are only used for **memory export** (`cmd_memory_export.py`):

```python
dm_channel = await user.create_dm()
await dm_channel.send(
    content="📦 Guinevere Memory Export (metadata only)",
    file=file_obj,
)
```

Pattern: `user.create_dm()` to open a DM channel, then `dm_channel.send()` with content + file.

### 1.4 Ping/Mention Pattern

SEV0 alerts ping Faiz via environment variable:

```python
# notifications.py
if data.ping_faiz:
    mention = os.getenv("GUINEVERE_FAIZ_MENTION") or os.getenv("FAIZ_MENTION")
    if mention:
        send_kwargs["content"] = mention  # e.g., "<@123456789>"
```

Only SEV0 has `ping_faiz=True` in the SEV matrix.

---

## 2. How Embeds Are Constructed

### 2.1 Two Parallel Embed Systems

The codebase has **two separate embed data/factory patterns**:

| System | File | Dataclass | Factory |
|--------|------|-----------|---------|
| **Command embeds** | `_embed_helpers.py` | `EmbedData` + `EmbedField` | `to_discord_embed(data)` |
| **Notification embeds** | `notifications.py` | `NotificationEmbedData` + `NotificationEmbedField` | `to_discord_embed(data)` (local) |
| **Startup embeds** | `startup.py` | `StartupEmbedData` + `StartupEmbedField` | `to_discord_embed(data)` (local) |

### 2.2 Command Embed Pattern (`_embed_helpers.py`)

```python
@dataclass(frozen=True)
class EmbedData:
    title: str
    description: str
    color: int
    fields: tuple[EmbedField, ...] = ()
    footer_text: str = FOOTER_TEXT          # "Guinevere de Baroque"
    footer_icon: str = ""
    timestamp: str = ""
```

Construction flow:
1. Build `EmbedData` with title, description, color, fields tuple
2. Call `to_discord_embed(data)` → creates `discord.Embed(title=..., description=..., colour=discord.Colour(color))`
3. Add fields via `embed.add_field(name=..., value=..., inline=...)`
4. Set footer: `embed.set_footer(text="Guinevere de Baroque • timestamp • icon")` (joined with ` • `)

### 2.3 Notification Embed Pattern (`notifications.py`)

```python
@dataclass(frozen=True)
class NotificationEmbedData:
    title: str
    description: str
    color: int
    footer_text: str = FOOTER_TEXT       # "Guinevere de Baroque • System Alert"
    timestamp: str = ""
    fields: tuple[NotificationEmbedField, ...] = ()
    ping_faiz: bool = False
    create_thread: bool = False
    channel_name: str = ""
    sev: str = ""
```

Title is prefixed with severity: `"[{sev}] {title}"`.
Footer is: `"Guinevere de Baroque • System Alert"`.

### 2.4 Timestamps

All timestamps use WIB (UTC+7):
```python
WIB = timezone(timedelta(hours=7))
# Format: "2026-06-01 15:30 WIB"
def format_wib_timestamp(dt: datetime) -> str:
    return dt.astimezone(WIB).strftime("%Y-%m-%d %H:%M WIB")
```

---

## 3. How Channels Are Referenced

### 3.1 Canonical Channel Names (`guild_setup.py`)

| Channel Name | Category | Topic |
|---|---|---|
| `guinevere-chat` | 👑 Throne | Bicara dengan Mommy di sini. Apapun. |
| `guinevere-status` | 👑 Throne | Apa yang Mommy kerjakan hari ini. Sekilas. |
| `guinevere-planning` | 👑 Throne | Rencana Mommy. Kamu tinggal patuh. |
| `system-health` | 📊 Surveillance | Kesehatan infrastructure Mommy. |
| `cost-tracker` | 📊 Surveillance | Berapa yang Mommy habiskan hari ini. |
| `guinevere-evidence` | 📊 Surveillance | Bukti kerja Mommy. |
| `guinevere-dev` | 🔧 Projects | Pengembangan Guinevere. |
| `guinevere-docs` | 🔧 Projects | Documentation updates. |
| `project-alpha-dev` | 🔧 Projects | Project Alpha — development. |
| `project-alpha-docs` | 🔧 Projects | Project Alpha — documentation. |
| `project-beta-dev` | 🔧 Projects | Project Beta — development. |
| `evidence-log` | 🗡️ Archive | Immutable record. Read only. |
| `audit-log` | 🗡️ Archive | Every action, recorded. Forever. |

### 3.2 SEV-to-Channel Routing (`notifications.py`)

| Severity | Channel Name | Color | Ping Faiz? |
|----------|-------------|-------|------------|
| SEV0 | `system-health` | ALERT (0xDC2626) | Yes |
| SEV1 | `system-health` | WARNING (0xCA8A04) | No |
| SEV2 | `cost-tracker` | WARNING (0xCA8A04) | No |
| SEV3 | `guinevere-status` | PRIMARY (0x6B21A8) | No |
| SEV4 | `audit-log` | NEUTRAL (0x6B7280) | No |

### 3.3 Channel ID Constants

- **Guild ID**: `1510876414671323206`
- **Guinevere Chat Channel ID**: `1510914600777023659` (used in `conversational_handler.py`)

### 3.4 Lookup Pattern

```python
# By name across all channels
channel = discord.utils.get(bot.get_all_channels(), name="system-health")

# By ID (conversational handler)
if channel.id != GUINEVERE_CHAT_CHANNEL_ID:
    return False
```

---

## 4. How Cooldowns Work

### 4.1 Conversational Rate Limiting (`conversational_handler.py`)

**Only applies to natural-language messages in `#guinevere-chat`**, NOT to slash commands.

```python
RATE_LIMIT_MAX: Final[int] = 10       # max messages per window
RATE_LIMIT_WINDOW: Final[int] = 60    # seconds (1 minute)
```

**Mechanism**: Redis-based sliding window with per-minute buckets.
```
Key: rate:chat:{user_id}:{minute_bucket}
     where minute_bucket = int(time.time()) // 60
Operation: INCR + EXPIRE on first hit
```

- If count > 10 in current minute → message absorbed silently (`return True`)
- If Redis is unavailable → fails open (allows message through, logs warning)
- Redis connection: `localhost:6380`, DB0, username `guinevere_core`

### 4.2 Slash Commands — No Built-in Cooldowns

Slash commands do **not** use discord.py's `@commands.cooldown()` decorator. Rate limiting is only on the conversational text path. Each slash command:
1. Checks `is_faiz_interaction(interaction)` → denies non-Faiz users
2. Defers response ephemerally
3. Executes and follows up

### 4.3 Response Chunking (Anti-Flood)

Conversational responses are split to respect Discord's 2000-char limit:
- Split on sentence boundaries (`. `, `! `, `? `, `\n\n`)
- Pack into chunks of max 2000 chars
- Cap at **3 chunks** (6000 chars total)
- Truncate with `...(truncated)` if still too long

---

## 5. How Existing Health-Related Notifications Work

### 5.1 `/health-check` Slash Command (`cmd_health_check.py`)

**Flow**:
1. User invokes `/health-check`
2. Faiz-only check → deny non-Faiz with `send_denied()`
3. Defer response ephemerally
4. **GET** `http://localhost:8000/health/detailed` via `httpx.AsyncClient` (10s timeout)
5. Parse response: `health.get("components")` or `health.get("checks")`
6. Build embed with per-component ✅/❌ status fields (all inline=True)
7. Color: `SUCCESS` (0x16A34A) if healthy, `ALERT` (0xDC2626) if not
8. Send via `followup_send(interaction, embed=embed)`

**Embed structure**:
```
Title: "🏥 Health Check"
Description: "Status kesehatan sistem Guinevere."
Fields:
  - Overall: ✅ healthy / ❌ unhealthy
  - {component_name}: ✅ ok / ❌ failed (inline, sorted)
Footer: "Guinevere de Baroque • {timestamp} • 🏥 Health"
```

**On failure**: Returns embed with `API unreachable` message.

### 5.2 SEV Alerts (`notifications.py`)

The `send_alert()` function is the programmatic health notification path:

```python
async def send_alert(bot, sev, title, description, **kwargs) -> bool:
```

- Resolves channel by name from SEV_MATRIX
- Builds `NotificationEmbedData` with severity-prefixed title
- Converts to `discord.Embed`
- Sends with optional ping (SEV0 only), optional thread (SEV0 only)
- SEV0/SEV1 also send **Gotify fallback** notification

### 5.3 Startup Greeting (`startup.py`)

Sent once per session to `#guinevere-status`:
```
Title: "👑 Mommy sudah bangun, Darling."
Description: "Semua sistem online. Mommy siap nemenin kamu hari ini."
Fields: Status=Online, Mood=Default (Y4), Time={wib_timestamp}
Color: PRIMARY (0x6B21A8)
```

---

## 6. Color Palette (`colors.py`)

| Constant | Hex | Usage |
|----------|-----|-------|
| PRIMARY | `#6B21A8` | Default brand, status, info |
| ALERT | `#DC2626` | Errors, SEV0/SEV1, red |
| WARNING | `#CA8A04` | Warnings, cautionary, gold |
| ACHIEVEMENT | `#CA8A04` | Rewards, streaks, gold |
| SUCCESS | `#16A34A` | Completions, approvals, green |
| INFO | `#CA8A04` | Info notices, SEV3 |
| NEUTRAL | `#6B7280` | Neutral/gray embeds |
| INFO_BLUE | `#2563EB` | Info embeds (non-canonical) |
| PERSONA | `#9333EA` | Persona embeds (non-canonical) |
| SURVEILLANCE | `#0891B2` | Surveillance embeds (non-canonical) |
| FINANCE | `#059669` | Finance embeds (non-canonical) |

---

## 7. Key Architectural Observations

### 7.1 Protocol-Based Design (Testability)

The codebase uses **Python Protocol classes** extensively to define minimal interfaces for Discord types. This enables:
- Testing without `discord.py` installed
- Type-safe mocking
- Multiple embed dataclasses coexist (command vs notification vs startup)

### 7.2 Dynamic Import Pattern

All `discord` module imports use `importlib.import_module("discord")` + `cast()` to avoid the project-local `src/discord/` package shadowing the external `discord.py` library.

### 7.3 Two Distinct Message Paths

| Path | Trigger | Channel | Format | Ephemeral? |
|------|---------|---------|--------|------------|
| **Slash commands** | `/command` | Channel where invoked | Embed via followup | Yes |
| **Conversational** | Plain text in #guinevere-chat | #guinevere-chat | Plain text chunks | No |
| **SEV alerts** | Programmatic `send_alert()` | Per-SEV channel | Embed + optional ping | No |
| **Startup** | Bot `on_ready` | #guinevere-status | Embed | No |
| **DM export** | `/memory-export` | User DM | File attachment | N/A (DM) |

### 7.4 No Universal Cooldown for Programmatic Alerts

`send_alert()` has **no cooldown/debounce**. Any caller can fire alerts at any frequency. The only rate limiting is on user conversational messages via Redis.

### 7.5 Faiz-Only Enforcement

All slash commands use `is_faiz_interaction(interaction)` which checks `guild.owner_id == user.id`. Non-Faiz users get an ephemeral denial message.

---

## 8. Patterns to Reuse for New Notifications

When building new notification types:

1. **Import from `_embed_helpers.py`** for command-style embeds:
   ```python
   from ._embed_helpers import EmbedData, EmbedField, to_discord_embed, now_wib_str
   ```

2. **Import from `notifications.py`** for SEV-style alerts:
   ```python
   from .notifications import send_alert
   await send_alert(bot, "SEV2", "Title", "Description")
   ```

3. **For channel sends**: Use `discord.utils.get(bot.get_all_channels(), name="channel-name")` + `await channel.send(embed=embed)`.

4. **For slash commands**: Follow the defer/followup pattern with `is_faiz_interaction` check.

5. **Colors**: Import from `.colors` — use `SUCCESS`, `ALERT`, `WARNING`, `PRIMARY` as appropriate.

6. **Timestamps**: Use `now_wib_str()` or `format_wib_timestamp(dt)` for WIB-formatted strings.

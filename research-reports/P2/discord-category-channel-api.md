# Discord Category/Channel Creation — API & discord.py 2.x Research Report

**Scope**: P2-005/P2-006 — safe, idempotent server bootstrap with categories and channels
**Date**: 2026-06-01
**Sources**: Discord API Docs (dev), discord.py 2.x (stable), GitHub real-world patterns

---

## 1. Discord REST API — Create Guild Channel Endpoint

**Endpoint**: `POST /guilds/{guild.id}/channels`
**Permission**: `MANAGE_CHANNELS`
**Returns**: New [channel object](https://discord.com/developers/docs/resources/channel#channel-object)
**Fires**: [Channel Create Gateway event](https://discord.com/developers/docs/events/gateway-events#channel-create)

### Relevant JSON Parameters

| Field | Type | Limits | Applies To |
|---|---|---|---|
| `name` | string | 1–100 chars | All |
| `type` | integer | 0=TEXT, 2=VOICE, 4=CATEGORY, 5=ANNOUNCEMENT, 15=FORUM | All |
| `topic` | string | 0–1024 chars (0–4096 for Forum/Media) | Text, Announcement, Forum, Media |
| `position` | integer | — | All |
| `parent_id` | snowflake | — | Text, Voice, Announcement, Stage, Forum, Media |
| `permission_overwrites` | array | — | All |
| `rate_limit_per_user` | integer | 0–21600s | Text, Voice, Stage, Forum, Media |
| `nsfw` | boolean | — | Text, Voice, Announcement, Stage, Forum |

**Source**: [Discord API — Guild Resource](https://discord.com/developers/docs/resources/guild#create-guild-channel)

### Channel Types (relevant subset)

| Type | ID | Description |
|---|---|---|
| `GUILD_TEXT` | 0 | Text channel |
| `GUILD_CATEGORY` | 4 | Category (holds ≤50 channels) |
| `GUILD_ANNOUNCEMENT` | 5 | News/announcement channel |
| `GUILD_FORUM` | 15 | Forum channel |

**Source**: [Discord API — Channel Object](https://discord.com/developers/docs/resources/channel#channel-object-channel-types)

---

## 2. discord.py 2.x — `Guild.create_category()`

**Signature** ([docs](https://discordpy.readthedocs.io/en/latest/api.html#discord.Guild.create_category)):

```python
async def create_category(
    self,
    name: str,                     # 1-100 chars
    *,
    overwrites: dict = ...,        # {Role|Member: PermissionOverwrite}
    reason: str | None = None,     # Audit log reason
    position: int = ...,           # 0-based position
) -> CategoryChannel
```

**Raises**: `Forbidden`, `HTTPException`

### Real-world pattern — name lookup first, create if missing

```python
# Safe idempotent creation
category = discord.utils.get(guild.categories, name="Tickets")
if category is None:
    category = await guild.create_category(
        "Tickets",
        reason="Created for ticket system"
    )
# category is now guaranteed to exist
```

**Source**: [ShinobiBot](https://github.com/mayman007/ShinobiBot/blob/main/cogs/ticket/ticket.py#L58-L62), [Axon-Bot](https://github.com/RayExo/Axon-Bot/blob/main/cogs/commands/logging.py#L67-L70), [Eruditus](https://github.com/hfz1337/Eruditus/blob/master/eruditus/eruditus.py#L103-L111)

---

## 3. discord.py 2.x — `Guild.create_text_channel()`

**Signature** ([docs](https://discordpy.readthedocs.io/en/latest/api.html#discord.Guild.create_text_channel)):

```python
async def create_text_channel(
    self,
    name: str,                       # 1-100 chars
    *,
    reason: str | None = None,
    category: CategoryChannel | None = None,  # Parent category
    position: int = ...,             # 0-based
    topic: str = ...,                # 0-1024 chars
    slowmode_delay: int = ...,       # 0-21600s
    nsfw: bool = False,
    news: bool = False,              # discord.py 2.0+
    default_auto_archive_duration: int = ...,  # 60/1440/4320/10080 (2.0+)
    default_thread_slowmode_delay: int = ...,  # (2.3+)
    overwrites: dict = ...,
) -> TextChannel
```

**Raises**: `Forbidden`, `HTTPException`, `TypeError` (since 2.0)

### Real-world pattern — idempotent text channel under category

```python
category = discord.utils.get(guild.categories, name="Logging")
if not category:
    category = await guild.create_category("Logging")

for name in ["bot-log", "mod-log"]:
    channel = discord.utils.get(guild.text_channels, name=name)
    if not channel:
        channel = await guild.create_text_channel(
            name=name,
            category=category,
            topic="Automated logging channel",
            reason="Bootstrap"
        )
```

**Source**: [Axon-Bot logging](https://github.com/RayExo/Axon-Bot/blob/main/cogs/commands/logging.py#L65-L78), [ShinobiBot](https://github.com/mayman007/ShinobiBot/blob/main/cogs/ticket/ticket.py#L63)

---

## 4. Position and Ordering

### API behavior
- `position` is an integer; channels with the same position are sorted by ID
- When creating via `POST /guilds/{guild.id}/channels`, the `position` field sets the sorting position
- Category order and channel order within categories are independent

### discord.py behavior
- `create_category(name=..., position=0)` — position 0 = top of category list
- `create_text_channel(name=..., position=0)` — position 0 = top of text channel list
- Categories and channels are sorted by position (ascending), then by ID (ascending) for ties

**Source**: [Discord API Guild docs](https://discord.com/developers/docs/resources/guild#create-guild-channel-json-params)

### Recommended order for Guinevere categories

```python
CATEGORIES = [
    ("👑 Throne",      0),   # Top
    ("📊 Surveillance", 1),
    ("🔧 Projects",     2),
    ("🗡️ Archive",      3),   # Bottom
]

for name, position in CATEGORIES:
    cat = discord.utils.get(guild.categories, name=name)
    if not cat:
        cat = await guild.create_category(
            name, position=position,
            reason="Guinevere server bootstrap"
        )
```

---

## 5. Unicode Emoji in Channel/Category Names

### Discord API
- Channel/category names accept **any Unicode character** including emoji
- Max length: 1–100 characters (emoji count as multiple chars depending on sequence)
- discord.py passes the `name` string directly to the API — no special encoding needed
- Common prefix emoji patterns work: `"👑 Throne"`, `"📊 Surveillance"`, `"🔧 Projects"`, `"🗡️ Archive"`

### Real-world evidence
```python
# Eruditus uses emoji prefixes in category names
category_channel = await guild.create_category(
    name=f"{Emojis.LIVE} {name}",  # e.g., "🔴 CTF Name"
    overwrites=overwrites,
)
```
**Source**: [Eruditus](https://github.com/hfz1337/Eruditus/blob/master/eruditus/eruditus.py#L108-L112)

### Caution
- Emoji sequences (flags, ZWJ sequences like 👨‍👩‍👧‍👦) can take 2–7+ Unicode codepoints
- Keep category names short if using emoji prefixes: `"👑 Throne"` (10 chars), `"📊 Surveillance"` (16 chars) — well under 100 limit
- The API accepts these natively; no URL-encoding or special escaping is needed

---

## 6. Rate Limits

### Global limit
- **50 requests/second** across all endpoints per bot token
- Independent of per-route limits

### Per-route limit (guild channels)
- `POST /guilds/{guild.id}/channels` is rate-limited **per guild**
- The guild ID serves as the top-level resource — creating channels in different guilds does not share rate limits
- If limited, response includes `X-RateLimit-Scope: shared` header

### Practical guidance for bootstrap

For creating 4 categories + ~18 channels (22 total requests):

1. Sequential creation is safe: 22 requests at ~100ms each = ~2.2s total, well under 50/s
2. Add `asyncio.sleep(0.5)` between requests as a safety buffer — adds ~11s total, negligible for a one-time bootstrap
3. Handle `discord.HTTPException` (status 429) with retry-after-backoff

**Source**: [Discord Rate Limits](https://discord.com/developers/docs/topics/rate-limits), [Discord Support](https://support-dev.discord.com/hc/en-us/articles/6223003921559-My-Bot-is-Being-Rate-Limited)

---

## 7. Idempotency Strategy

### Core pattern: name-based lookup before creation

```python
import discord

async def ensure_category(guild, name, position=None, overwrites=None):
    """Return existing category or create it. Idempotent by name."""
    category = discord.utils.get(guild.categories, name=name)
    if category is not None:
        return category
    kwargs = {"name": name, "reason": "Guinevere bootstrap"}
    if position is not None:
        kwargs["position"] = position
    if overwrites is not None:
        kwargs["overwrites"] = overwrites
    return await guild.create_category(**kwargs)


async def ensure_text_channel(guild, name, category=None, topic=None, position=None):
    """Return existing text channel or create it. Idempotent by name."""
    channel = discord.utils.get(guild.text_channels, name=name)
    if channel is not None:
        return channel
    kwargs = {"name": name, "reason": "Guinevere bootstrap"}
    if category is not None:
        kwargs["category"] = category
    if topic is not None:
        kwargs["topic"] = topic
    if position is not None:
        kwargs["position"] = position
    return await guild.create_text_channel(**kwargs)
```

### Why name-based (not ID-based)
- `discord.utils.get(iterable, name=...)` is O(n) but categories/channels per guild are typically <100
- `discord.utils.get(iterable, id=...)` is also O(n) but requires persisting IDs externally
- For bootstrap, name-based lookup is simpler and equally safe
- **Trade-off**: renaming a channel externally would cause duplicate creation. For a private controlled server, this risk is negligible.

### Real-world evidence — the lookup-then-create pattern is universal

Every GitHub example found follows this exact pattern ([1](https://github.com/mayman007/ShinobiBot/blob/main/cogs/ticket/ticket.py#L58-L62), [2](https://github.com/RayExo/Axon-Bot/blob/main/cogs/commands/logging.py#L67-L70), [3](https://github.com/hfz1337/Eruditus/blob/master/eruditus/eruditus.py#L103-L111), [4](https://github.com/kennnyshiwa/kennnyshiwa-cogs/blob/v3-cogs/tickets/core.py#L203-L210), [5](https://github.com/gpu-mode/kernelbot/blob/main/src/kernelbot/main.py#L111-L119)).

---

## 8. Channel/Category ID Capture

### After creation, IDs are available on the returned object

```python
category = await guild.create_category("👑 Throne")
print(category.id)       # Snowflake int -> persist in DB/config
print(category.name)     # "👑 Throne"
print(category.guild.id) # Guild snowflake

channel = await guild.create_text_channel("general", category=category)
print(channel.id)        # Snowflake int
print(channel.category_id)  # Matches category.id
```

### Persistence pattern (for P2-005/P2-006)

```python
# After bootstrap, capture category IDs
guild_config = {}
for cat in guild.categories:
    if cat.name in ALLOWED_CATEGORIES:
        guild_config[f"category_{cat.name}"] = cat.id
# guild_config["category_👑 Throne"] = 123456789...

# Later, retrieve by ID:
cat = guild.get_channel(guild_config["category_👑 Throne"])
# guild.get_channel() is O(1) via internal cache lookup
```

**Source**: [discord.py GuildChannel attributes](https://discordpy.readthedocs.io/en/latest/api.html#discord.GuildChannel)

---

## 9. Permissions Preconditions

### Required bot permissions

| Action | Required Permission |
|---|---|
| Create channels/categories | `manage_channels` |
| Set permission overwrites during creation | `manage_roles` (for overwrites) |
| Read channels after creation | `view_channel` |
| Send messages in text channels | `send_messages` |

### Permission overwrite during creation

```python
# Ensure @everyone cannot read secret channels
overwrites = {
    guild.default_role: discord.PermissionOverwrite(read_messages=False),
    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
}
secret_category = await guild.create_category(
    "🔒 Secret",
    overwrites=overwrites,
    reason="Private category"
)
```

### Permission syncing
- If a text channel is created WITH a `category` but WITHOUT `overwrites`, permissions sync from the category automatically
- If `overwrites` IS provided, they are set explicitly (category permissions are NOT synced)
- To sync after creation: `await channel.edit(sync_permissions=True)` (requires `manage_roles`)

**Source**: [discord.py create_text_channel docs](https://discordpy.readthedocs.io/en/latest/api.html#discord.Guild.create_text_channel)

---

## 10. Channel Topic

### API limits
- Text/Announcement channels: 0–1024 characters
- Forum/Media channels: 0–4096 characters

### discord.py
```python
topic = """Channel purpose:
• Surveillance log feeds
• Automated monitoring reports
• No manual chat — bot-only posts"""

channel = await guild.create_text_channel(
    "surveillance-feed",
    category=surveillance_cat,
    topic=topic,
    reason="Surveillance channel"
)
```

**Source**: [Discord API Channel docs](https://discord.com/developers/docs/resources/channel#channel-object-channel-fields)

---

## 11. Rollback Deletion

### Delete a single channel

```python
await channel.delete(reason="Rollback: Guinevere bootstrap cleanup")
```

**Raises**: `Forbidden`, `NotFound`, `HTTPException`  
**Permission**: `manage_channels`

**Source**: [discord.py GuildChannel.delete](https://discordpy.readthedocs.io/en/latest/api.html#discord.abc.GuildChannel.delete)

### Delete category + all child channels

```python
async def delete_category_and_children(category, reason=None):
    """Delete a category after deleting all its child channels."""
    for channel in category.channels:
        await channel.delete(reason=reason)
    await category.delete(reason=reason)
```

**Real-world pattern** ([Axon-Bot](https://github.com/RayExo/Axon-Bot/blob/main/cogs/commands/logging.py#L89-L93)):

```python
category = discord.utils.get(guild.categories, name="Axon-logging")
if category:
    for channel in category.channels:
        await channel.delete()
    await category.delete()
```

### Partial rollback — move channels out before deletion

```python
# Before deleting a category, move children to no parent
for channel in category.channels:
    await channel.edit(category=None)  # Remove from category
await category.delete()
```

---

## 12. Complete Idempotent Bootstrap Pattern

```python
import discord

CATEGORY_CONFIG = {
    "👑 Throne": {
        "position": 0,
        "channels": [
            {"name": "announcements", "topic": "Royal decrees and system announcements", "news": True},
            {"name": "throne-room",  "topic": "Direct communication with Guinevere"},
            {"name": "operator-log", "topic": "Operator action audit trail"},
        ]
    },
    "📊 Surveillance": {
        "position": 1,
        "channels": [
            {"name": "surveillance-feed", "topic": "Live surveillance event stream"},
            {"name": "surveillance-log",  "topic": "Archived surveillance records"},
        ]
    },
    "🔧 Projects": {
        "position": 2,
        "channels": [
            {"name": "project-status",  "topic": "Active project dashboards"},
            {"name": "dev-chat",        "topic": "Development discussion"},
        ]
    },
    "🗡️ Archive": {
        "position": 3,
        "channels": [
            {"name": "archive-log", "topic": "Historical records"},
        ]
    },
}

async def bootstrap_guild(guild):
    """Idempotent server bootstrap. Safe to re-run."""
    created = {"categories": [], "channels": []}

    for cat_name, cat_config in CATEGORY_CONFIG.items():
        # 1. Find or create category
        cat = discord.utils.get(guild.categories, name=cat_name)
        if cat is None:
            cat = await guild.create_category(
                cat_name,
                position=cat_config["position"],
                reason="Guinevere bootstrap"
            )
            created["categories"].append(cat_name)
        else:
            # Ensure correct position
            if cat.position != cat_config["position"]:
                await cat.edit(position=cat_config["position"])

        # 2. Find or create channels in this category
        for ch_config in cat_config["channels"]:
            ch = discord.utils.get(guild.text_channels, name=ch_config["name"])
            if ch is None:
                ch_kwargs = {
                    "name": ch_config["name"],
                    "category": cat,
                    "topic": ch_config["topic"],
                    "reason": "Guinevere bootstrap",
                }
                if ch_config.get("news"):
                    ch_kwargs["news"] = True
                ch = await guild.create_text_channel(**ch_kwargs)
                created["channels"].append(ch_config["name"])

    return created
```

### Safety guarantees
1. **Idempotent**: re-running does not duplicate channels/categories
2. **No data loss**: existing channels with matching names are reused, not overwritten
3. **Position correction**: categories are repositioned on each run
4. **Graceful failure**: if creation fails (permissions, rate limit), the error propagates without partial state corruption
5. **Audit trail**: all operations include `reason` for Discord audit log

---

## 13. Edge Cases and Gotchas

| Gotcha | Consequence | Mitigation |
|---|---|---|
| Category max 50 child channels | `HTTPException` if exceeded | Count before creating; split into sub-categories |
| `name` collision with existing channel of different type | `discord.utils.get(guild.text_channels, ...)` misses voice/forum channels | Scope lookup to correct channel type |
| Unicode normalization | `"cafe"` vs `"café"` vs composed NFC form | Discord normalizes names; use exact expected string |
| Channel rename during re-run | `utils.get(..., name=old_name)` returns `None` → duplicate | Persist IDs + name fallback |
| Rate limit during sequential creation | `HTTPException(429)` | Add `asyncio.sleep(0.5)` between creates; retry with backoff |
| Permission mismatch | `Forbidden` during creation | Check `guild.me.guild_permissions.manage_channels` before bootstrap |

---

## 14. Key Sources

| Source | URL |
|---|---|
| Discord API — Guild Resource | https://discord.com/developers/docs/resources/guild |
| Discord API — Channel Object | https://discord.com/developers/docs/resources/channel |
| Discord API — Rate Limits | https://discord.com/developers/docs/topics/rate-limits |
| discord.py 2.x — Guild API | https://discordpy.readthedocs.io/en/latest/api.html#guild |
| discord.py 2.x — GuildChannel | https://discordpy.readthedocs.io/en/latest/api.html#discord.abc.GuildChannel |
| discord.py 2.x — FAQ / utils.get | https://discordpy.readthedocs.io/en/latest/faq.html |
| ShinobiBot (create_category pattern) | https://github.com/mayman007/ShinobiBot/blob/main/cogs/ticket/ticket.py |
| Axon-Bot (idempotent channel setup) | https://github.com/RayExo/Axon-Bot/blob/main/cogs/commands/logging.py |
| Eruditus (emoji in category names) | https://github.com/hfz1337/Eruditus/blob/master/eruditus/eruditus.py |
| gpu-mode/kernelbot (category setup) | https://github.com/gpu-mode/kernelbot/blob/main/src/kernelbot/main.py |
| Fox-V3 (category position edit) | https://github.com/bobloy/Fox-V3/blob/master/infochannel/infochannel.py |

---

## 15. P2-005/P2-006 Relevance Notes

- **Unicode emoji names** `👑 📊 🔧 🗡️` are natively supported by the API — just pass them as-is to `name=`
- **Idempotency by name lookup** is safe for a private server where only the bot creates channels
- **Position ordering** categories 0–3 as configured above gives the correct visual hierarchy
- **Category→channel relationship** is set via `category=` kwarg in `create_text_channel`
- **Capture IDs** after creation by reading `.id` off the returned `CategoryChannel`/`TextChannel` objects
- **Permission preconditions**: the bot needs `manage_channels` at minimum; `manage_roles` if overwrites are set
- **Rollback**: `delete_category_and_children()` pattern above deletes an entire category tree
- **Rate limits**: 22 sequential creates is trivially safe; add 0.5s sleep for safety
- **Channel topic**: useful for documenting channel purpose; 1024 char limit for text channels
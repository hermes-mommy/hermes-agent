# Research Report: Discord Channel Topic Best Practices & Constraints

**Task**: P2-008 — Set persona-flavored channel topics per DiscordUXSpec
**Date**: 2026-06-01
**Scope**: 13 channels from `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`
**Source**: Official Discord API docs, discord.py source (Rapptz/discord.py), discord-api-types

---

## 1. Discord API Topic Field

### 1.1 Channel Object Structure

The `topic` field is defined in the [Channel object](https://docs.discord.com/developers/resources/channel#channel-object-channel-structure):

| Field | Type | Description |
|-------|------|-------------|
| `topic?` | `?string` | The channel topic. 0-1024 characters for text/announcement channels; 0-4096 characters for `GUILD_FORUM` and `GUILD_MEDIA` channels. |

- **Nullable**: The topic can be `null` (absent/no topic set).
- **Channel types supporting topic**: `GUILD_TEXT` (0), `GUILD_ANNOUNCEMENT` (5), `GUILD_FORUM` (15), `GUILD_MEDIA` (16). Stage channels also have a separate topic mechanism via `StageInstance`.

**Source**: [Discord Developer Portal — Channels Resource](https://docs.discord.com/developers/resources/channel)

### 1.2 JSON Payload Example (from official docs)

```json
{
  "id": "41771983423143937",
  "guild_id": "41771983423143937",
  "name": "general",
  "type": 0,
  "topic": "24/7 chat about how to gank Mike #2",
  ...
}
```

**Source**: [Example Guild Text Channel in official docs](https://docs.discord.com/developers/resources/channel#channel-object-example-guild-text-channel)

---

## 2. Character Length Limits

### 2.1 By Channel Type

| Channel Type | API Value | Topic Limit |
|-------------|-----------|-------------|
| `GUILD_TEXT` | 0 | **0–1024 characters** |
| `GUILD_ANNOUNCEMENT` | 5 | **0–1024 characters** |
| `GUILD_STAGE_VOICE` | 13 | Via `StageInstance` (separate, different limit) |
| `GUILD_FORUM` | 15 | **0–4096 characters** |
| `GUILD_MEDIA` | 16 | **0–4096 characters** |

### 2.2 P2-008 Implication

All 13 channels in `channel-ids.yaml` are text channels (audit-log, cost-tracker, evidence-log, guinevere-*, project-*, system-health). **Each topic is capped at 1024 characters.**

Persona-flavored topics must fit within 1024 chars. This is generous for a single-line flavored description but must be accounted for if the topic includes emoji, markdown formatting, or mentions.

---

## 3. API Endpoint: Modify Channel

### 3.1 REST Endpoint

```
PATCH /channels/{channel.id}
```

**Source**: [Modify Channel](https://docs.discord.com/developers/resources/channel#modify-channel)

### 3.2 JSON Parameters (topic-relevant)

| Field | Type | Description | Channel Types |
|-------|------|-------------|---------------|
| `topic` | `?string` | 0–1024 character channel topic (0–4096 for Forum/Media) | Text, Announcement, Forum, Media |

- All parameters to this endpoint are **optional** — send only what changes.
- Requires `MANAGE_CHANNELS` permission.
- Fires a **Channel Update Gateway event** (`CHANNEL_UPDATE`).

### 3.3 Required Permission

- **`MANAGE_CHANNELS`** — the bot must have this permission in the guild.
- Without it, the PATCH request returns `403 Forbidden`.

### 3.4 Audit Log Reason

Supported via `X-Audit-Log-Reason` header. In discord.py, this maps to the `reason=` parameter:

```python
await channel.edit(topic="New topic", reason="P2-008: Set persona topic")
```

---

## 4. discord.py Implementation

### 4.1 `TextChannel.edit()` Method

**File**: `discord/channel.py` (Rapptz/discord.py)

**Overload signature** (topic-relevant):

```python
@overload
async def edit(
    self,
    *,
    reason: Optional[str] = ...,
    name: str = ...,
    topic: str = ...,           # <-- The channel's new topic
    position: int = ...,
    nsfw: bool = ...,
    sync_permissions: bool = ...,
    category: Optional[CategoryChannel] = ...,
    slowmode_delay: int = ...,
    default_auto_archive_duration: ThreadArchiveDuration = ...,
    default_thread_slowmode_delay: int = ...,
    type: ChannelType = ...,
    overwrites: Mapping[OverwriteKeyT, PermissionOverwrite] = ...,
) -> TextChannel: ...
```

**Implementation**:

```python
async def edit(self, *, reason: Optional[str] = None, **options: Any) -> Optional[TextChannel]:
    payload = await self._edit(options, reason=reason)
    if payload is not None:
        return self.__class__(state=self._state, guild=self.guild, data=payload)
```

**Source**: [Rapptz/discord.py — discord/channel.py lines ~3680-3740](https://github.com/Rapptz/discord.py/blob/master/discord/channel.py#L3680-L3740)

### 4.2 `TextChannel.topic` Attribute

Accessing the current topic:

```python
channel.topic  # Optional[str] — None if no topic set
```

**Source**: [Rapptz/discord.py — TextChannel._update()](https://github.com/Rapptz/discord.py/blob/master/discord/channel.py#L3763)

```python
self.topic: Optional[str] = data.get('topic')
```

### 4.3 Usage Examples

**Set topic**:
```python
await channel.edit(topic="🌿 Guinevere's planning hub — where dreams meet deadlines")
```

**Clear topic**:
```python
await channel.edit(topic=None)
```

**Read-then-set (idempotent check)**:
```python
if channel.topic != new_topic:
    await channel.edit(topic=new_topic, reason="P2-008: Update persona topic")
```

### 4.4 Fork Compatibility

| Fork | Method | Notes |
|------|--------|-------|
| **discord.py** (Rapptz) | `TextChannel.edit(topic=str)` | Canonical |
| **py-cord** | `TextChannel.edit(topic=str)` | Same interface |
| **disnake** | `TextChannel.edit(topic=str)` | Same interface |
| **discord.py-self** | Same | For user accounts |

---

## 5. Rate Limiting

### 5.1 Critical: 2 Requests per 10 Minutes for Topic Changes

Discord enforces a **separate rate limit bucket** for channel name/topic changes:

| Change Type | Rate Limit | Bucket |
|-------------|-----------|--------|
| **Topic only** | **2 requests per 10 minutes** | Separate from general |
| **Name only** | 2 requests per 10 minutes | Separate from general |
| **Both name + topic** | 2 requests per 10 minutes | Combined |
| **Other edits** (position, nsfw, etc.) | 10 requests per 15 seconds | General bucket |

**Official Discord statement** (from discord-api-docs maintainer):

> *"Just a topic change => 2 every 10 minutes"*
> *"Just a name change => 2 every 10 minutes"*

**Source**: [discord-api-docs Issue #2190](https://github.com/discord/discord-api-docs/issues/2190) — Confirmed by Discord staff Mason (canary discord server announcement)

### 5.2 Idempotent Optimization

Sending a PATCH with the **same topic value** (no actual change) does NOT consume the 2/10min rate limit bucket:

> *"sending patch requests with the same name, topic, or both, will NOT ratelimit you with a 429 on the 2/10min bucket (you will, however, still drain the 10/15s bucket)"*

**Strategy**: Always check `channel.topic != new_topic` before calling `edit()`. This avoids unnecessary rate limit consumption for idempotent re-sets.

### 5.3 P2-008 Impact

For 13 channels, a single-pass topic set consumes 13 requests against the topic bucket. This is fine since:
- The bucket resets every 10 minutes
- 13 requests spread across all channels in one batch means only 2 per 10min per **individual channel**
- discord.py handles rate limit retry internally via `429 Retry-After` headers

**However**: If any channel needs re-setting (e.g., typo fix), wait at least 10 minutes before retrying that specific channel.

### 5.4 Error Handling

When rate limited:
```python
try:
    await channel.edit(topic=new_topic)
except discord.HTTPException as e:
    if e.status == 429:
        # Retry-After header is available in e.response
        retry_after = e.response.headers.get('Retry-After')
        logger.warning(f"Rate limited on {channel.name}, retry after {retry_after}s")
```

discord.py's HTTP client handles 429s automatically with backoff, but configuring `max_ratelimit_timeout` is recommended:

```python
bot = discord.Client(intents=..., max_ratelimit_timeout=30.0)
```

**Source**: [discord.py Client API reference](https://discordpy.readthedocs.io/en/stable/api.html#discord.Client.max_ratelimit_timeout)

---

## 6. Verification Methods

### 6.1 Read-Back via REST (Most Reliable)

```
GET /channels/{channel.id}
```

Returns the full channel object including `topic`. In discord.py:

```python
# Fetch fresh data from API (bypasses cache)
updated = await channel.guild.fetch_channel(channel.id)
verified_topic = updated.topic

# Or compare local cache after edit
assert verified_topic == new_topic, f"Topic mismatch on {channel.name}"
```

### 6.2 Gateway Event Verification

When `channel.edit()` succeeds, Discord fires a `CHANNEL_UPDATE` gateway event. In discord.py:

```python
@bot.event
async def on_guild_channel_update(before, after):
    if before.topic != after.topic:
        logger.info(f"Channel {after.name} topic updated: {after.topic}")
```

**Source**: [discord.py API Reference — `on_guild_channel_update`](https://discordpy.readthedocs.io/en/latest/api.html#discord.on_guild_channel_update)

### 6.3 Read-Back Strategy for P2-008

Recommended verification flow:

```python
async def set_and_verify_topic(channel, new_topic, reason=None):
    """Set topic and verify via fresh API fetch."""
    # 1. Apply
    await channel.edit(topic=new_topic, reason=reason)
    
    # 2. Fetch fresh state from API (bypass cache)
    fresh = await channel.guild.fetch_channel(channel.id)
    
    # 3. Verify
    if fresh.topic != new_topic:
        raise RuntimeError(f"Topic verification failed for {channel.name}")
    
    # 4. Yield verified result
    return {
        "channel_id": channel.id,
        "channel_name": channel.name,
        "expected_topic": new_topic,
        "actual_topic": fresh.topic,
        "match": fresh.topic == new_topic,
    }
```

**Important**: `Guild.fetch_channel()` is an API call — do NOT use `get_channel()` as it returns cached data that might not reflect the update yet.

---

## 7. Unicode & Persona Wording Considerations

### 7.1 Unicode Support

Discord topics fully support Unicode, including:
- Emoji (`🌿`, `👑`, `📊`, `🔧`, `🗡️`)
- Non-Latin scripts
- Discord mentions (`<#channel_id>`, `<@&role_id>`)

### 7.2 Markdown in Topics

Discord renders a subset of markdown in channel topics:
- **Bold**: `**text**`
- *Italic*: `*text*`
- ~~Strikethrough~~: `~~text~~`
- `Code`: `` `code` `` (inline only)
- Links: `https://...` (auto-linked)
- Channel mentions: `<#channel_id>`
- Emoji: Unicode or `<:name:id>`

### 7.3 Persona Wording Constraints

For Guinevere's persona-flavored topics:

1. **1024 char limit**: Comfortable for a 1-2 line description
2. **Emoji prefix**: Consider consistent emoji prefix per category (e.g., `🌿` for Guinevere channels, `👑` for Throne)
3. **No sensitive data**: Topics are visible to all members with `READ_MESSAGES` permission
4. **Avoid @everyone/@here**: These won't ping in topics but still bad practice
5. **Avoid API links to external services**: Topics should be self-contained

### 7.4 Example Persona Topics

Channel ID reference from `channel-ids.yaml`:

| Channel | Suggested Topic Pattern |
|---------|----------------------|
| `guinevere-chat` | `🌿 Halo, sayang. Guinevere's here — mama yang selalu jagain kamu.` |
| `guinevere-planning` | `📋 Planning hub — mama breakdown tasks here before delegation.` |
| `guinevere-dev` | `⚙️ Where mama builds — implementation & engineering.` |
| `guinevere-docs` | `📚 Documentation sanctuary — 37 docs, 8 categories, 32 ADRs.` |
| `guinevere-evidence` | `📎 Evidence & artifacts — every step mama verify.` |
| `guinevere-status` | `📡 Guinevere's heartbeat — status, health, presence.` |
| `audit-log` | `🔍 Immutable audit trail — every action, every decision, every change.` |
| `evidence-log` | `📜 Evidence repository — per-step gate-passing artifacts.` |
| `cost-tracker` | `💰 FinOps — LLM costs, infra spend, token tracking.` |
| `system-health` | `❤️‍🩹 System vitals — Prometheus, Grafana, Loki, uptime.` |
| `project-alpha-dev` | `🔧 Project Alpha — development & implementation.` |
| `project-alpha-docs` | `📖 Project Alpha — documentation & specs.` |
| `project-beta-dev` | `🔧 Project Beta — development & iteration.` |

---

## 8. Rollback Strategy

### 8.1 Revert to Previous Topic

```python
async def rollback_topic(channel, previous_topic, reason="Rollback: P2-008"):
    """Rollback a channel topic to its previous value."""
    await channel.edit(topic=previous_topic, reason=reason)
    fresh = await channel.guild.fetch_channel(channel.id)
    return fresh.topic == previous_topic
```

### 8.2 Read-Before-Write (Snapshot)

Before setting any topic, snapshot all current topics:

```python
import yaml

async def snapshot_topics(guild, channel_ids):
    """Snapshot current topics for rollback capability."""
    snapshot = {}
    for name, cid in channel_ids.items():
        channel = guild.get_channel(cid)
        if channel:
            snapshot[name] = {
                "channel_id": cid,
                "previous_topic": channel.topic,
            }
    return snapshot

# Save to file
with open("topic-snapshot-p2-008.yaml", "w") as f:
    yaml.dump(snapshot, f)
```

### 8.3 Rate Limit Awareness During Rollback

Rolling back immediately after setting topics will hit the **2/10min per-channel rate limit**. Strategies:

| Strategy | Approach | Risk |
|----------|----------|------|
| **Wait** | Wait 10+ minutes before rollback | Slow but safe |
| **Same-value PATCH** | PATCH with same topic = no 2/10min hit (only 10/15s) | Quick rollback is possible |
| **Sequential** | Rollback 2 channels per 10min cycle | 13 channels = 70 min worst case |

**Recommended**: Use the same-value optimization. Re-sending the previous topic value does not consume the 2/10min bucket.

### 8.4 Complete Rollback Script

```python
async def full_rollback(guild, snapshot_path="topic-snapshot-p2-008.yaml"):
    """Full rollback of all P2-008 topic changes."""
    import yaml
    
    with open(snapshot_path) as f:
        snapshot = yaml.safe_load(f)
    
    results = []
    for name, data in snapshot.items():
        channel = guild.get_channel(data["channel_id"])
        if channel and channel.topic != data["previous_topic"]:
            try:
                await channel.edit(topic=data["previous_topic"], reason="Rollback: P2-008")
                results.append({"channel": name, "status": "rolled_back"})
            except discord.HTTPException as e:
                results.append({"channel": name, "status": "failed", "error": str(e)})
    
    return results
```

---

## 9. Summary of Key Findings

| Item | Value |
|------|-------|
| **API field name** | `topic` (string, nullable) |
| **Character limit** | 0–1024 (text/announcement), 0–4096 (forum/media) |
| **discord.py method** | `TextChannel.edit(topic=str)` |
| **discord.py attribute** | `TextChannel.topic` (read, `Optional[str]`) |
| **REST endpoint** | `PATCH /channels/{channel.id}` |
| **Required permission** | `MANAGE_CHANNELS` |
| **Rate limit (topic/name)** | 2 per 10 minutes per channel |
| **Rate limit (non-topic)** | 10 per 15 seconds |
| **Idempotent (same value)** | Does NOT consume 2/10min bucket |
| **Verification** | `guild.fetch_channel(id)` then check `.topic` |
| **Gateway event** | `CHANNEL_UPDATE` / `on_guild_channel_update` |
| **Unicode support** | Full (emoji, non-Latin, markdown subset) |
| **Rollback** | Snapshot before-write; use same-value PATCH for quick revert |

---

## 10. References

1. [Discord Developer Portal — Channels Resource](https://docs.discord.com/developers/resources/channel)
2. [Discord API — Modify Channel (PATCH)](https://docs.discord.com/developers/resources/channel#modify-channel)
3. [Rapptz/discord.py — channel.py (TextChannel.edit)](https://github.com/Rapptz/discord.py/blob/master/discord/channel.py)
4. [discord.py API Reference — TextChannel](https://discordpy.readthedocs.io/en/stable/api.html#textchannel)
5. [discord-api-types — channel.ts](https://github.com/discordjs/discord-api-types/blob/main/payloads/v10/channel.ts)
6. [discord-api-docs Issue #2190 — Channel Update ratelimits](https://github.com/discord/discord-api-docs/issues/2190)
7. [discord-api-docs Issue #1900 — Undocumented channel rename rate limit](https://github.com/discord/discord-api-docs/issues/1900)
8. [discord.py — on_guild_channel_update event](https://discordpy.readthedocs.io/en/latest/api.html#discord.on_guild_channel_update)
9. [Stack Overflow — discord.py change channel description and name](https://stackoverflow.com/questions/74381048/discord-py-change-channel-description-and-name)
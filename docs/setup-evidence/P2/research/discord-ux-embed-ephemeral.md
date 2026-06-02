# Discord UX Research: Ephemeral Messages, Embeds, and Help Command Layout

> **Date**: 2026-06-01  
> **Research Type**: Conceptual + Implementation reference  
> **Purpose**: Feed planner and command implementation decisions for Guinevere Discord bot  
> **Scope**: Slash-command UX patterns, ephemeral vs public responses, embed field limits, help command layout for 33 commands, safety/safeword wording, startup channel messages

---

## Table of Contents

1. [Ephemeral vs Public Responses](#1-ephemeral-vs-public-responses)
2. [Embed Field Limits and Character Constraints](#2-embed-field-limits-and-character-constraints)
3. [Inline Field Layout and Formatting](#3-inline-field-layout-and-formatting)
4. [Help Command Layout for 33 Commands](#4-help-command-layout-for-33-commands)
5. [Safety/Safeword Command UX](#5-safetysafeword-command-ux)
6. [Startup Channel Message Practices](#6-startup-channel-message-practices)
7. [discord.py API Reference](#7-discordpy-api-reference)
8. [Implementation Recommendations](#8-implementation-recommendations)

---

## 1. Ephemeral vs Public Responses

### 1.1 Key Characteristics

| Aspect | Details |
|---|---|
| **Ephemeral flag** | `1 << 6` = `64` (Discord API). In discord.py: `ephemeral=True` |
| **Visibility** | Only visible to the user who invoked the command |
| **Lifetime** | Disappears on dismiss, restart, or when chat scrolls away — indeterminate duration (can persist hours) |
| **Token window** | Initial response: **3 seconds**. Token valid for **15 minutes** for follow-ups/edits |
| **Cannot change** | Ephemeral state is **locked after initial response** — cannot make an ephemeral message public or vice versa |
| **Cannot be deleted** via REST | Ephemeral messages cannot be deleted via Discord REST API (as of 2026); use `edit_original_response` to update content instead (since Discord added delete support via interaction token) |

**Sources**:
- [Discord Docs: Receiving and Responding to Interactions](https://docs.discord.com/developers/interactions/receiving-and-responding)
- [Discord Ephemeral Messages FAQ](https://support-apps.discord.com/hc/en-us/articles/26501839512855-Ephemeral-Messages-FAQ)
- [discord.js Guide: Response Methods](https://discordjs.guide/slash-commands/response-methods)

### 1.2 When to Use Ephemeral vs Public

| Use Case | Recommended Visibility | Rationale |
|---|---|---|
| **Admin/mod commands** | Ephemeral | Output contains sensitive info (user IDs, audit data) |
| **Error messages** | Ephemeral | Only the invoking user needs to see it |
| **Confirmation / success ACK** | Ephemeral | "Done!" feedback without channel clutter |
| **Help command** | Ephemeral | Personal reference; doesn't belong in public chat |
| **Safety/safeword commands** | **Ephemeral** | **Critical** — must never leak personal safety decisions |
| **Status check commands** | Ephemeral | Personal info (e.g., persona status, settings) |
| **Community announcements** | Public | Visible to all members |
| **Shared information** | Public | E.g., leaderboards, polls, game results |
| **Commands that produce public value** | Public | E.g., trivia answers, pinned messages |

**General Principle**: Admin/safety/personal → ephemeral. Community/value-generating → public.

### 1.3 Critical Rules for Ephemeral

1. **Set ephemeral on the initial response** — cannot be changed later.
   ```python
   # Correct: ephemeral set on initial reply
   await interaction.response.send_message("Secret!", ephemeral=True)

   # Also correct: defer with ephemeral
   await interaction.response.defer(ephemeral=True)
   await interaction.followup.send("Result!")
   ```

2. **When deferring, set ephemeral on `defer()`**, NOT on the first `followup`:
   ```python
   # Correct
   await interaction.response.defer(ephemeral=True)
   await interaction.followup.send("This will be ephemeral")

   # WRONG: first followup after defer IGNORES ephemeral flag
   await interaction.response.defer()
   await interaction.followup.send("This will NOT be ephemeral", ephemeral=True)  # ignored!
   ```
   Source: [discord/discord-api-docs issue #4784](https://github.com/discord/discord-api-docs/issues/4784)

3. **Edit ephemeral messages via interaction token**, not message ID:
   ```python
   # Correct
   await interaction.edit_original_response(content="Updated")

   # Wrong — will get "Unknown Message"
   # await channel.fetch_message(message_id)  # won't work for ephemeral
   ```
   Source: [discord.py interactions API](https://discordpy.readthedocs.io/en/latest/interactions/api.html)

4. **No reactions on ephemeral messages** — they can't have reactions added.

5. **View timeout auto-set**: In discord.py, if a view is sent with ephemeral and no explicit timeout, the timeout is automatically set to 15 minutes.
   Source: [discord.py InteractionResponse.send_message docs](https://discordpy.readthedocs.io/en/stable/interactions/api.html)

---

## 2. Embed Field Limits and Character Constraints

### 2.1 Per-Message Limits

| Property | Maximum | Notes |
|---|---|---|
| `content` (plain text) | 2,000 characters | Message text outside embeds |
| `embeds` count | 10 per message | Array of embed objects |
| **Total embed characters** (all embeds combined) | **6,000 characters** | Sum of `title` + `description` + all `field.name` + all `field.value` + `footer.text` + `author.name` across ALL embeds in one message |

### 2.2 Per-Embed Limits

| Embed Property | Maximum | Counts Toward 6K Total |
|---|---|---|
| `title` | 256 characters | Yes |
| `description` | 4,096 characters | Yes |
| `fields` | 25 entries | — |
| `field.name` | 256 characters | Yes |
| `field.value` | 1,024 characters | Yes |
| `footer.text` | 2,048 characters | Yes |
| `author.name` | 256 characters | Yes |
| `url` | 2,048 characters | **No** |
| `image.url` | 2,048 characters | No |
| `thumbnail.url` | 2,048 characters | No |
| `author.url` | 2,048 characters | No |
| `footer.icon_url` | 2,048 characters | No |
| `author.icon_url` | 2,048 characters | No |
| `color` | 24-bit integer (0–16,777,215) | — |
| `timestamp` | ISO-8601 string | — |

**Sources**:
- [Discord Webhooks Guide: Field Limits](https://birdie0.github.io/discord-webhooks-guide/other/field_limits.html)
- [Discord Webhook: Embed Limits Cheat Sheet (2026)](https://discord-webhook.com/en/blog/discord-webhook-embed-limits/)
- [discord.js Guide: Embed Limits](https://www.discordjs.guide/popular-topics/embeds)
- [Python Discord: Discord Embed Limits](https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/)
- [discord/discord-api-docs Issue #4047](https://github.com/discord/discord-api-docs/issues/4047) (confirmed: 6K is across all embeds, not per embed)

### 2.3 Critical Insight: 6K Total Is Per Message, Not Per Embed

> The 6,000 character limit applies to the **sum of all text across all embeds** in a single message. You cannot bypass per-embed limits by splitting into 10 embeds — the total still caps at 6K.

This means for a help command with 33 commands:
- If each command entry takes ~40 chars (name + brief desc), that's ~1,320 chars
- Plus category headers, formatting, footers ≈ plausible in **one embed** with 33 fields
- But 33 fields > 25 field limit → **pagination required**

---

## 3. Inline Field Layout and Formatting

### 3.1 Inline Field Rules

| Rule | Detail |
|---|---|
| **Max per row** | 3 consecutive `inline: true` fields share a row |
| **Row break** | The 4th inline field wraps to a new row |
| **Mixing** | `inline: false` fields are full-width and cause a break |
| **Forced row break** | Use a zero-width space field: `{"name": "\u200b", "value": "\u200b", "inline": true}` to create intentional 2-column layouts if only 2 inline fields fit per row |

### 3.2 Formatting Within Embeds

| Content Area | Markdown Support |
|---|---|
| Description | **Full markdown**: bold, italic, code blocks, masked links, lists, headings |
| Field values | Full markdown |
| Field names | Bold only (limited formatting) |
| Footer text | No markdown |
| Title | No markdown (can use emoji) |

**Key notes**:
- Mentions in embeds do NOT trigger notifications
- Masked links (`[text](url)`) work in description and field values only
- Custom emoji `<:name:id>` count as literal string length (~17 chars) toward character budget
- Markdown formatting characters (`**bold**`, `` `code` ``) count toward character budget

**Mobile consideration**: Inline fields stack vertically on mobile. Keep inline field values under ~30 characters for clean grids on desktop, and test on mobile.

Sources:
- [Discord Webhook: Embed Builder Guide](https://discord-webhook.com/en/blog/discord-embed-builder-guide/)
- [Complete Guide to Discord Embed Formatting](https://discord-webhook.com/en/blog/discord-embed-builder-guide/)
- [A Practical Guide to the Discord Embed Maker in 2026](https://www.agent37.com/blog/embed-maker-discord)
- [discord.js Guide: Embeds](https://www.discordjs.guide/popular-topics/embeds)

---

## 4. Help Command Layout for 33 Commands

### 4.1 The Challenge

With 33 commands:
- **Embed field limit**: Max 25 fields per embed
- **Character budget**: 6K total across all embeds
- **Readability**: Listing 33 commands in one embed is overwhelming
- **Solution**: Categorized pagination

### 4.2 Recommended: Category + Pagination Pattern

**Two-tier navigation**:
1. **Select menu** (top) — pick a category / cog
2. **Button pagination** (bottom) — navigate pages within a category

This is the established pattern used by:
- `discord-pretty-help` (PyPI) — embed help with AppMenu (buttons + select)
- `slash-help` (PyPI) — paginated slash help with fields_per_embed=4 default
- `discord.py-masterclass` pagination guide — CategoryBasedPaginator
- sgtlaggy's help command gist — select menus + up/close buttons

### 4.3 Category Design for 33 Commands

**Proposed categories** (example grouping):

| Category | Command Count | Fields Needed |
|---|---|---|
| 🛡️ **Safety** | ~2-3 | 3 fields |
| 👤 **Persona** | ~4-5 | 5 fields |
| ⚙️ **Settings** | ~5-6 | 6 fields |
| 📋 **Management** | ~5-6 | 6 fields |
| ℹ️ **Information** | ~4-5 | 5 fields |
| 🧩 **Utility** | ~5-6 | 6 fields |
| ❤️ **Other** | ~2-3 | 3 fields |

Each category fits within 6 fields → comfortable in one embed page.

### 4.4 Field Value Budget

For each command, a field pair:
- **Field name**: `/<command>` — ~15 chars (including `/`)
- **Field value**: Brief description — ~60 chars
- **Total per command**: ~75 chars
- **~6 commands per category**: ~450 chars per embed
- **Footer**: ~30 chars
- **Total per embed**: ~500 chars → well within 6K budget and single embed

### 4.5 Pagination Implementation Pattern

```python
# Pattern: Category-based paginator with select + buttons
class HelpView(discord.ui.View):
    def __init__(self, author: discord.User, pages: dict):
        super().__init__(timeout=120)
        self.author = author
        self.pages = pages        # {category_name: [embed1, embed2, ...]}
        self.categories = list(pages.keys())
        self.current_category = 0
        self.current_page = 0

        # Build category select menu
        self.select = CategorySelect(self)
        for name in self.categories:
            self.select.add_option(label=name, value=name)
        self.add_item(self.select)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                "This menu is not for you.", ephemeral=True
            )
            return False
        return True

    async def update_display(self, interaction: discord.Interaction):
        embeds = self.pages[self.categories[self.current_category]]
        embed = embeds[self.current_page]
        self._update_buttons(embeds)
        await interaction.response.edit_message(embed=embed, view=self)
```

### 4.6 Alternative: Single Embed with Inline Fields (Category per Row)

For compact layout, use inline fields with category icons:
```
[Category Icon] `command` - description
```
But with 33 commands, even with compact layout, you'll exceed 25 fields. **Pagination is necessary.**

### 4.7 UX Best Practices

- **Ephemeral**: Help command response should be ephemeral (personal reference)
- **Timeout**: Set view timeout to 120s, then clean up (remove components)
- **Author-only**: Only the command author can interact with the pagination
- **Footer**: Include page number: "Page 1/3 • Category CategoryName"
- **Color**: Use a consistent embed color (0x9B59B6 or another distinctive shade)
- **Close button**: Provide a "Close" button to dismiss the help menu

Sources:
- [discord-pretty-help v2.0.7](https://pypi.org/project/discord-pretty-help/)
- [slash-help v2.0.5](https://pypi.org/project/slash-help/)
- [Discord.py Masterclass: Pagination](https://fallendeity.github.io/discord-py-masterclass/pagination/)
- [Select-menu help command gist by sgtlaggy](https://gist.github.com/sgtlaggy/dc98ba82aee57c01d713028f91a5e318)
- [Pagination view example by mudkipdev](https://gist.github.com/mudkipdev/4b0ce96a2d9bd6205e16c52798546571)
- [Pagination-Utils JDA library](https://github.com/ygimenez/Pagination-Utils)

---

## 5. Safety/Safeword Command UX

### 5.1 Design Principles

| Principle | Reasoning |
|---|---|
| **Always ephemeral** | Safeword usage is personal and must never be visible to others |
| **Button confirmation** | Use ✅ Confirm / ❌ Cancel buttons (not text reply) for deliberate action |
| **No public logging** | Never broadcast safeword usage to a channel |
| **Private admin alert** | Quietly notify admins in a private channel |
| **No punishment by bot** | Bot flags for human review; never auto-punish |
| **Clear feedback** | Short ephemeral ACK: "Safeword activated. A moderator has been notified." |
| **Cannot be undone by others** | Only the invoking user sees/interacts with safeword confirmation |

### 5.2 Confirmation Dialog Pattern

```python
class SafewordConfirm(discord.ui.View):
    def __init__(self, author: discord.User):
        super().__init__(timeout=30)
        self.author = author
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message(
                "You cannot interact with this.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="✅ Confirm Safeword", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
```

### 5.3 Response Flow

```
User runs /safeword
  → Bot sends ephemeral embed: "Are you sure?" + [✅ Confirm] [❌ Cancel]
  → User clicks Confirm
    → Bot edits embed: "✓ Safeword activated. A moderator has been notified."
    → Bot sends private alert to admin channel (non-ephemeral)
    → Bot triggers safeword protocol
  → User clicks Cancel
    → Bot edits embed: "Cancelled."
  → Timeout (30s)
    → Bot disables buttons: "This request has expired."
```

### 5.4 Safety Command Wording

| Element | Wording |
|---|---|
| **Title** | ⚠️ Confirm Safeword Activation |
| **Description** | This will activate the safeword protocol. A moderator will be notified. This action is logged for safety. |
| **Confirm button** | ✅ Yes, activate safeword |
| **Cancel button** | ❌ Cancel |
| **Success response** | ✓ Safeword protocol activated. A moderator has been notified to assist you. |
| **Admin alert** | 🛡️ Safeword activated by {user} ({user.id}) in {channel}. Please check on them. |
| **Cancel response** | Safeword activation cancelled. No action taken. |
| **Timeout message** | Safeword confirmation timed out. Please try again if needed. |

**Source**: [AI Guardrails for Teen Discord — behavioral heuristics + ephemeral safety](https://dev.to/kkierii/ai-guardrails-for-a-teen-discord-server-the-code-around-the-model-call-47gd)

---

## 6. Startup Channel Message Practices

### 6.1 Bot Ready Announcement Pattern

When the bot starts up, it should send a status message to a designated channel.

### 6.2 Recommended Startup Embed

```python
embed = discord.Embed(
    title="🟢 Guinevere is Online",
    description=f"I'm back and ready to serve, sayang.\nUse `/{command_prefix}help` to see what I can do.",
    color=0x9B59B6,  # Discord blurple alternative — distinctive purple
    timestamp=datetime.datetime.now(datetime.timezone.utc)
)
embed.add_field(name="Version", value="v1.0.0", inline=True)
embed.add_field(name="Commands", value="33 registered", inline=True)
embed.add_field(name="Ping", value=f"{round(client.latency * 1000)}ms", inline=True)
embed.set_footer(text="Guinevere • Autonomous AI Companion")
```

### 6.3 Best Practices

| Practice | Detail |
|---|---|
| **Designated channel** | Send to a specific status/log channel, not a public general channel |
| **Don't ping @everyone** | Startup message should not ping; it's informational |
| **Include status info** | Version, command count, latency, uptime |
| **Timestamp** | Always include timestamp for tracking restarts |
| **Ephemeral?** | No — this is a channel-wide status update; should be public |
| **Use edit for reconnects** | If bot reconnects, edit the existing startup message rather than sending a new one |
| **Per-guild** | If in multiple guilds, send to each guild's configured status channel |
| **Rate limiting** | If sending to many guilds, implement queue with delays |
| **Welcome message on join** | When bot joins a new guild, send an embed welcome with setup instructions |

### 6.4 Reconnection Behavior

```python
# Store the startup message ID per guild for editing on reconnection
startup_messages: dict[int, int] = {}  # guild_id -> message_id

async def send_startup(guild: discord.Guild):
    channel = _get_status_channel(guild)
    embed = _build_startup_embed(guild)
    msg = await channel.send(embed=embed)
    startup_messages[guild.id] = msg.id

# On reconnect, edit rather than send new
async def on_reconnect(guild: discord.Guild):
    if guild.id in startup_messages:
        channel = _get_status_channel(guild)
        try:
            msg = await channel.fetch_message(startup_messages[guild.id])
            embed = _build_startup_embed(guild)
            await msg.edit(embed=embed)
            return
        except discord.NotFound:
            pass
    await send_startup(guild)
```

**Sources**:
- [Discord Welcome Bot pattern](https://github.com/ehsanul01/Discord_Welcome_Bot)
- [How to Build Discord Welcome Message System](https://www.dargslanpublishing.com/how-to-build-discord-welcome-message-system/)
- [StartIT Bot: Welcome & Goodbye Messages](https://startit.bot/blog/how-to-set-up-welcome-goodbye-messages-on-discord/)

---

## 7. discord.py API Reference

### 7.1 Interaction Response Methods

```python
# Immediate reply (within 3 seconds)
await interaction.response.send_message(
    content="Hello!",
    embed=embed,
    ephemeral=True,       # Private to invoking user
    view=MyView(),        # Attach components
    delete_after=10.0     # Auto-delete after 10s
)

# Deferred reply (>3s processing needed)
await interaction.response.defer(ephemeral=True)  # Must set ephemeral here!
# ... do long work ...
await interaction.followup.send("Result!")  # Inherits ephemeral from defer

# Edit original response
await interaction.edit_original_response(
    content="Updated!",
    embed=new_embed
)

# Edit via InteractionMessage
original = await interaction.original_response()
await original.edit(content="Updated!")

# Delete original response
await interaction.delete_original_response()

# Follow-up messages
await interaction.followup.send("Additional info", ephemeral=True)
```

### 7.2 View Timeout and Ephemeral Interaction

```python
class MyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        # If sent with ephemeral=True and no timeout, timeout auto-set to 15 min

    async def on_timeout(self):
        # Clean up when view expires
        for child in self.children:
            child.disabled = True
        try:
            msg = await self.interaction.original_response()
            await msg.edit(view=self)
        except:
            pass

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Not for you.", ephemeral=True)
            return False
        return True
```

### 7.3 Embed Builder Reference

```python
embed = discord.Embed(
    title="Title",
    description="Description with **markdown** support",
    color=0x9B59B6,
    url="https://example.com",  # clickable title
    timestamp=datetime.datetime.now(datetime.timezone.utc)
)

embed.set_author(name="Author", url="...", icon_url="...")
embed.set_footer(text="Footer text", icon_url="...")
embed.set_thumbnail(url="...")
embed.set_image(url="...")

embed.add_field(name="Field 1", value="Value 1", inline=True)
embed.add_field(name="Field 2", value="Value 2", inline=True)
embed.add_field(name="Field 3", value="Value 3", inline=False)  # full width

# Clear all fields
embed.clear_fields()

# Remove specific field (by index)
embed.remove_field(0)
```

**Sources**:
- [discord.py Interactions API Reference](https://discordpy.readthedocs.io/en/latest/interactions/api.html)
- [discord.py Embed API](https://discordpy.readthedocs.io/en/latest/api.html#embed)
- [discord.py embeds.py source](https://github.com/Rapptz/discord.py/blob/master/discord/embeds.py)
- [discord.py interactions.py source](https://github.com/Rapptz/discord.py/blob/108e9abb/discord/interactions.py)

---

## 8. Implementation Recommendations

### 8.1 Ephemeral Usage Decision Matrix

| Command Type | Visibility | Why |
|---|---|---|
| `/help` | Ephemeral | Personal reference |
| `/safeword` | **Ephemeral** | **Safety-critical** |
| `/persona status` | Ephemeral | Personal settings |
| `/persona set` | Ephemeral | Personal preference |
| `/settings *` | Ephemeral | Personal config |
| `/ping` | Ephemeral | Utility info |
| `/uptime` | Ephemeral | Bot stat for invoker |
| Announcements | Public | Shared info |
| Public commands | Public | When result is for everyone |

### 8.2 Embed Budget Planning (Help Command)

With **33 commands** across **~6 categories**:

| Category | Commands | Fields | Embed Budget |
|---|---|---|---|
| Category 1 | ~6 | 6 fields | ~500 chars |
| Category 2 | ~6 | 6 fields | ~500 chars |
| Category 3 | ~6 | 6 fields | ~500 chars |
| Category 4 | ~5 | 5 fields | ~400 chars |
| Category 5 | ~5 | 5 fields | ~400 chars |
| Category 6 | ~5 | 5 fields | ~400 chars |

**Category select menu** (1 dropdown with 6 options) + **navigation buttons** (◀ ▶ ⏹) = 3 rows max.

### 8.3 Help Command Architecture

```
HelpView (discord.ui.View, timeout=120)
├── CategorySelect (row 0)
│   └── Option per category: "🛡️ Safety", "👤 Persona", etc.
├── Navigation Buttons (row 1-2)
│   ├── ◀ Previous page
│   ├── 🔢 Page counter (optional: opens jump-to-page modal)
│   ├── ▶ Next page
│   └── ⏹ Close
└── Author-only check via interaction_check()
```

### 8.4 Startup Sequence

1. Bot logs in → `on_ready()` fires
2. Wait for guilds to populate
3. For each guild:
   a. Look up configured status channel (from DB or config)
   b. Fetch or create startup message
   c. Send/edit embed with: name, version, command count, latency, timestamp
4. On disconnect/reconnect:
   a. Edit existing startup message instead of sending new one

### 8.5 Key Constraints Summary

| Constraint | Value | Impact on Implementation |
|---|---|---|
| Initial response window | 3 seconds | Must reply or defer within 3s |
| Token validity | 15 minutes | All edits/follow-ups within 15 min |
| Embed fields max | 25 per embed | Help with 33 commands needs categorization or pagination |
| Total embed chars | 6000 across all embeds | Budget is shared; plan conservatively |
| Inline fields per row | 3 maximum | Use `\u200b` hack for forced row breaks |
| View timeout with ephemeral | Auto 15 min if no timeout set | Set explicit timeout on views |
| Select menu options max | 25 | Category select with ~6 options is fine |
| Buttons in action row | 5 max per row | Navigation fits easily in 1-2 rows |

---

## Reference Links

| Resource | URL |
|---|---|
| Discord Interaction Docs | https://docs.discord.com/developers/interactions/receiving-and-responding |
| Discord Ephemeral FAQ | https://support-apps.discord.com/hc/en-us/articles/26501839512855-Ephemeral-Messages-FAQ |
| Discord Component Reference | https://docs.discord.com/developers/components/reference |
| Discord Embed Limits (2026) | https://discord-webhook.com/en/blog/discord-webhook-embed-limits/ |
| discord.py Interactions API | https://discordpy.readthedocs.io/en/latest/interactions/api.html |
| discord.py Embed API | https://discordpy.readthedocs.io/en/latest/api.html#embed |
| discord.py embeds.py source | https://github.com/Rapptz/discord.py/blob/master/discord/embeds.py |
| discord.py Masterclass: Pagination | https://fallendeity.github.io/discord-py-masterclass/pagination/ |
| discord-pretty-help (PyPI) | https://pypi.org/project/discord-pretty-help/ |
| discord.js Guide: Embeds | https://www.discordjs.guide/popular-topics/embeds |
| GitHub: Select-menu help command | https://gist.github.com/sgtlaggy/dc98ba82aee57c01d713028f91a5e318 |
| GitHub: Pagination with buttons | https://gist.github.com/mudkipdev/4b0ce96a2d9bd6205e16c52798546571 |

---

*End of research report. Prepared for Guinevere planner and command implementation decisions.*
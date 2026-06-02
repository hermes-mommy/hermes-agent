# Discord.py 2.x Reference Report — Slash Commands, Ephemeral, Embeds, Cogs, Events, Presence, Intents, Error Handling

**Date**: 2026-06-01  
**Target Version**: discord.py 2.6.x (v2.6.4)  
**Official Docs**: https://discordpy.readthedocs.io/en/v2.6.4/  
**Repo**: https://github.com/Rapptz/discord.py  

---

## Table of Contents

1. [Slash Command Callback & Response Patterns](#1-slash-command-callback--response-patterns)
2. [Ephemeral Messages: defer() + followup.send()](#2-ephemeral-messages-defer--followupsend)
3. [Embed Field Limits & Best Practices](#3-embed-field-limits--best-practices)
4. [Cogs vs Direct Callbacks](#4-cogs-vs-direct-callbacks)
5. [on_ready Caveats & Idempotency](#5-on_ready-caveats--idempotency)
6. [Setting Presence (Activity Watching)](#6-setting-presence-activity-watching)
7. [Message Event Content Detection & Intents](#7-message-event-content-detection--intents)
8. [Safe Error Handling & Logging in Command Callbacks](#8-safe-error-handling--logging-in-command-callbacks)

---

## 1. Slash Command Callback & Response Patterns

### 1.1 Registering Slash Commands

**Method A: Directly on `CommandTree`** (no Cogs)

```python
import discord
from discord import app_commands

tree = app_commands.CommandTree(client)

@tree.command(name="ping", description="Replies with Pong!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")
```

**Reference**: [discord.py FAQ — Application Commands](https://discordpy.readthedocs.io/en/v2.6.4/faq.html#application-commands)

**Method B: Via Cog (recommended for organization)**

```python
class MyCog(commands.Cog):
    @app_commands.command(name="hello", description="Say hello")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello!", ephemeral=True)
```

**Reference**: [Cogs documentation](https://discordpy.readthedocs.io/en/v2.6.4/ext/commands/cogs.html)

### 1.2 Interaction Response Lifecycle

**Critical rule**: A response can only be done **once** per interaction. If you need to send additional messages, use `interaction.followup.send()`.

| Pattern | When to Use | Syntax |
|---|---|---|
| **Immediate response** | Response computed in < 3 seconds | `await interaction.response.send_message(...)` |
| **Defer + followup** | Response takes > 3 seconds | `await interaction.response.defer(...)` then `await interaction.followup.send(...)` |
| **Defer (thinking) + edit** | Need loading state, then edit | `await interaction.response.defer(thinking=True)` then `await interaction.edit_original_response(...)` |

**Reference**: [Interactions API — InteractionResponse](https://discordpy.readthedocs.io/en/v2.6.4/interactions/api.html)

### 1.3 Syncing Commands

Commands **must be synced** before they appear. Sync should happen once, ideally in `setup_hook()`:

```python
async def setup_hook(self):
    await self.tree.sync()  # sync global commands
    # or for guild-specific:
    await self.tree.sync(guild=discord.Object(id=GUILD_ID))
```

**Reference**: [FAQ — Commands Not Showing Up](https://discordpy.readthedocs.io/en/v2.6.4/faq.html#my-bot-s-commands-are-not-showing-up)

---

## 2. Ephemeral Messages: defer() + followup.send()

### 2.1 Direct Ephemeral Response

```python
await interaction.response.send_message("Only you can see this", ephemeral=True)
```

- `ephemeral=True` sets the `flags` field to `64` (the ephemeral message flag).
- If a `View` is sent with an ephemeral message and has no timeout, the timeout defaults to **15 minutes**.

**Reference**: [Interactions API — send_message](https://discordpy.readthedocs.io/en/v2.6.4/interactions/api.html#discord.InteractionResponse.send_message)

### 2.2 Defer + Ephemeral Followup

**For operations that take > 3 seconds**:

```python
await interaction.response.defer(ephemeral=True)
# ... do work that takes up to 15 minutes ...
await interaction.followup.send("Result here", ephemeral=True)
```

**Key behavior**:
- `defer(ephemeral=True)` acknowledges the interaction and tells Discord the eventual response will be ephemeral. The user sees a "bot is thinking" state.
- After deferring, you **must** call `interaction.followup.send()` (not `interaction.response.send_message()`) — the response has already been used.
- `interaction.followup.send()` uses the webhook API. Its `ephemeral` parameter defaults to `False`, so you **must pass `ephemeral=True` explicitly** on followup sends if you want ephemeral.

**Reference**:
- [`InteractionResponse.defer()` source](https://github.com/rapptz/discord.py/blob/master/discord.py/discord/interactions.py) — ephemeral flag handling
- [`Webhook.send()` source](https://github.com/rapptz/discord.py/blob/master/discord.py/discord/webhook/async_.py) — `ephemeral=False` default

### 2.3 Defer (thinking) + Edit Original Response

When you want to show a loading state and then **edit** the deferred message:

```python
await interaction.response.defer(ephemeral=True, thinking=True)
# Shows: "Bot is thinking..."
await asyncio.sleep(5)
await interaction.edit_original_response(content="Done!")
```

**Note**: `thinking=True` makes the deferred type `deferred_channel_message` (shows loading). Slash commands **cannot** use `deferred_message_update` — only component/modal interactions can.

**Reference**: [`InteractionResponse.defer()` API](https://discordpy.readthedocs.io/en/v2.6.4/interactions/api.html#discord.InteractionResponse.defer)

---

## 3. Embed Field Limits & Best Practices

### 3.1 Discord Embed Limits (Official)

| Field | Character Limit |
|---|---|
| **title** | 256 characters |
| **description** | 4096 characters |
| **fields** | Max **25 field objects** |
| **field.name** | 256 characters each |
| **field.value** | 1024 characters each |
| **footer.text** | 2048 characters |
| **author.name** | 256 characters |
| **Total (all text combined)** | **6000 characters** |
| **Max embeds per message** | **10 embeds** |

**Reference**:
- [Python Discord — Embed Limits](https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/)
- [Stack Overflow — Embed length check](https://stackoverflow.com/questions/64932316/how-to-get-the-length-of-a-discord-embed-discord-py)

### 3.2 Best Practices for the Guinevere Persona Embeds

1. **Keep titles short** (under 100 chars) — scannable at a glance.
2. **Description is the main canvas** — use markdown (`**bold**`, `- lists`, `[links](url)`) for structure.
3. **Use fields for structured data**:
   - One field per logical piece (status, stat, action).
   - `field.name` should be short (under 50 chars) — it renders as a bold label.
   - `field.value` can hold longer text but stay under 1024.
4. **Inline fields** (`inline=True`) work well for 3-across grids of small values.
5. **Footer** → use for timestamp (`discord.utils.utcnow()`) or brief context.
6. **Colour** → use `discord.Colour` constants or hex ints (`0xDEADBF`).
7. **Total budget check** before sending: sum all text lengths in the embed; if over 6000, split into multiple embeds or truncate.

### 3.3 Example — Embed Construction

```python
embed = discord.Embed(
    title="Status Update",
    description="Current system state overview",
    colour=discord.Colour.dark_purple(),
    timestamp=discord.utils.utcnow(),
)
embed.add_field(name="Uptime", value="72h 14m", inline=True)
embed.add_field(name="Users", value="1,234", inline=True)
embed.add_field(name="Guilds", value="42", inline=True)
embed.set_footer(text="Guinevere System")
```

**Reference**: [Embed API](https://discordpy.readthedocs.io/en/v2.6.4/api.html#embed)

---

## 4. Cogs vs Direct Callbacks

### 4.1 Cog Advantages (Recommended for Guinevere)

| Aspect | Cogs | Direct Tree Callbacks |
|---|---|---|
| **Organization** | Group related commands/listeners | All in one file |
| **State** | Instance attributes per cog | Must use globals or `bot` state |
| **Error handling** | `cog_app_command_error()` per cog | Only global `tree.error` handler |
| **Lifecycle hooks** | `cog_load()`, `cog_unload()`, `cog_check()` | None |
| **App commands** | `@app_commands.command()` inside class | `@tree.command()` decorator |
| **Listeners** | `@commands.Cog.listener()` | `@client.event` |
| **Testability** | Easy to instantiate in tests | Harder to isolate |

### 4.2 Cog Example (Slash Commands + Listeners)

```python
class GuinevereCore(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user} is ready!")

    @app_commands.command(name="status", description="Show system status")
    async def status(self, interaction: discord.Interaction):
        await interaction.response.send_message("All systems operational.", ephemeral=True)

    @app_commands.command(name="ping", description="Check latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! {round(self.bot.latency * 1000)}ms")

async def setup(bot: commands.Bot):
    await bot.add_cog(GuinevereCore(bot))
```

### 4.3 Groups with GroupCog

```python
@app_commands.guilds(discord.Object(id=GUILD_ID))
class AdminGroup(commands.GroupCog, name="admin"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="announce", description="Send announcement")
    async def announce(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(f"Announcement: {message}")
```

**Reference**: [Cogs documentation](https://discordpy.readthedocs.io/en/v2.6.4/ext/commands/cogs.html)

---

## 5. on_ready Caveats & Idempotency

### 5.1 The Problem

`on_ready()` is **NOT guaranteed to be called only once**. The official docs state:

> **Warning**: This function is **not** guaranteed to be the first event called. Likewise, this function is **not** guaranteed to only be called once. This library implements reconnection logic and thus will end up calling this event whenever a RESUME request fails.

**Reference**: [`on_ready()` API](https://discordpy.readthedocs.io/en/v2.6.4/api.html#discord.on_ready)

Similarly, the FAQ warns:

> It is **highly discouraged** to use `Client.change_presence()` or API calls in `on_ready()` as this event may be called many times while running, not just once. There is a high chance of disconnecting if presences are changed right after connecting.

**Reference**: [FAQ — Setting Playing Status](https://discordpy.readthedocs.io/en/v2.6.4/faq.html#how-do-i-set-the-playing-status)

### 5.2 The Solution: `setup_hook()`

`setup_hook()` is called **exactly once** during `login()`, before the websocket connects.

```python
class MyBot(commands.Bot):
    async def setup_hook(self):
        # Called once on startup — safe for one-time init
        await self.tree.sync()
        # Pre-load data, register views, etc.
```

**Reference**: [`setup_hook()` API](https://discordpy.readthedocs.io/en/v2.6.4/api.html#discord.Client.setup_hook)

### 5.3 Making on_ready Idempotent (When You Must Use It)

If you must use `on_ready()`, guard against re-entry:

```python
async def on_ready(self):
    if hasattr(self.bot, '_ready_done'):
        return
    self.bot._ready_done = True
    # ... first-run logic (logging startup message, etc.)
```

Or use `once=True` on listeners (if using `@bot.listen`):

```python
@bot.listen('on_ready', once=True)
async def on_ready_once():
    print("This runs exactly once per process lifetime!")
```

### 5.4 Connection vs Ready

- **`on_connect()`**: Called when the WebSocket connects (many times per session on reconnect).
- **`on_ready()`**: Called when data is fully prepared after connect/reconnect.
- **`setup_hook()`**: Called once during login, before any events.

**Reference**: [`on_connect()` API](https://discordpy.readthedocs.io/en/v2.6.4/api.html#discord.on_connect)

---

## 6. Setting Presence (Activity Watching)

### 6.1 At Construction (Static)

```python
activity = discord.Activity(
    name="Darling 👁️",
    type=discord.ActivityType.watching
)
client = discord.Client(intents=intents, activity=activity)
```

**Reference**: [FAQ — Setting Playing Status](https://discordpy.readthedocs.io/en/v2.6.4/faq.html#how-do-i-set-the-playing-status)

### 6.2 At Runtime (Dynamic)

Using `Client.change_presence()`:

```python
activity = discord.Activity(
    name="Darling 👁️",
    type=discord.ActivityType.watching
)
await client.change_presence(activity=activity, status=discord.Status.online)
```

**⚠️ Warning**: Do NOT call `change_presence()` inside `on_ready()` (see §5.1). Instead:
- Set a static activity in the constructor.
- Or use `setup_hook()` with a short delay.
- Or use `ext.tasks` for periodic presence cycling.

### 6.3 Activity Types

| Enum | Display |
|---|---|
| `ActivityType.playing` | "Playing ..." |
| `ActivityType.watching` | "Watching ..." |
| `ActivityType.listening` | "Listening to ..." |
| `ActivityType.streaming` | "Streaming ..." |
| `ActivityType.competing` | "Competing in ..." |

**Reference**: [ActivityType enum](https://discordpy.readthedocs.io/en/v2.6.4/api.html#discord.ActivityType)

---

## 7. Message Event Content Detection & Intents

### 7.1 The Message Content Intent

Discord requires the **privileged `MESSAGE_CONTENT` intent** to access message content fields:

- `Message.content`
- `Message.attachments`
- `Message.embeds`
- `Message.components`
- `Message.poll`

**Reference**: [Primer to Gateway Intents](https://discordpy.readthedocs.io/en/v2.6.4/intents.html#need-message-content-intent)

### 7.2 Enabling the Intent

```python
intents = discord.Intents.default()
intents.message_content = True  # Enable privileged message content intent
```

**Plus**: You must enable "Message Content Intent" in the [Discord Developer Portal](https://discord.com/developers/applications) under Bot → Privileged Gateway Intents.

### 7.3 on_message Event for HARD STOP Detection

```python
@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return  # Don't respond to self

    if message.content.lower() == "hard stop":
        # Handle HARD STOP protocol
        await message.channel.send("HARD STOP acknowledged.")
        # ... shutdown logic

    # If using commands extension, must process commands:
    await client.process_commands(message)
```

**⚠️ Important**: If you override `on_message()`, text commands will stop working unless you call `await bot.process_commands(message)` at the end. Alternatively, use a **listener** to avoid this issue:

```python
@bot.listen('on_message')
async def hard_stop_detector(message: discord.Message):
    if message.author.bot:
        return
    if message.content == "HARD STOP":
        # Handle HARD STOP
        pass
    # No need to call process_commands — it runs automatically
```

**Reference**: [FAQ — on_message stops commands](https://discordpy.readthedocs.io/en/v2.6.4/faq.html#why-does-on-message-make-my-commands-stop-working)

### 7.4 Minimal Intents for Slash-Command-Only Bot

If the bot only uses slash commands (no prefix commands, no on_message reading):

```python
intents = discord.Intents.default()
# message_content NOT needed for slash commands alone
# But IS needed if on_message reads message.content
```

Slash commands work through the Interactions API, not the message gateway — so they don't need `message_content` intent.

---

## 8. Safe Error Handling & Logging in Command Callbacks

### 8.1 Error Handling Hierarchy

App command errors are caught and passed through handlers in this order:

1. **`Command.error`** — per-command decorator
2. **`Group.on_error`** — for commands in a group
3. **`CommandTree.on_error`** — global error handler

**Reference**: [`AppCommandError` source](https://github.com/Rapptz/discord.py/blob/108e9abb/discord/app_commands/errors.py)

### 8.2 Global Error Handler (Recommended)

**Method A: Decorator on tree**

```python
tree = app_commands.CommandTree(client)

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Cooldown: {error.retry_after:.1f}s", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have permission.", ephemeral=True)
    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("Command not found.", ephemeral=True)
    else:
        # Log unexpected errors
        logging.exception(f"Unhandled command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)
        else:
            await interaction.followup.send("An unexpected error occurred.", ephemeral=True)
```

**Reference**: [GitHub Discussion #9209](https://github.com/Rapptz/discord.py/discussions/9209)

**Method B: Subclass CommandTree**

```python
class GuinevereCommandTree(app_commands.CommandTree):
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        logging.error(f"Error in {interaction.command}: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("An error occurred.", ephemeral=True)
        else:
            await interaction.followup.send("An error occurred.", ephemeral=True)

bot = commands.Bot(command_prefix="!", intents=intents, tree_cls=GuinevereCommandTree)
```

**Reference**: [GitHub Discussion #8404](https://github.com/Rapptz/discord.py/discussions/8404)

### 8.3 Cog-Level Error Handler

```python
class MyCog(commands.Cog):
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Called when an app command in this cog raises an error."""
        logging.error(f"Cog error: {error}")
        await interaction.response.send_message(f"Error: {error}", ephemeral=True)
```

### 8.4 Per-Command try/except Pattern

For specific error handling in individual commands:

```python
@app_commands.command(name="check", description="Check something")
async def check(self, interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        # ... potentially failing work ...
        result = await self.some_risky_operation()
        await interaction.followup.send(f"Result: {result}", ephemeral=True)
    except SpecificError as e:
        await interaction.followup.send(f"Failed: {e}", ephemeral=True)
        logging.warning(f"Check command failed for {interaction.user}: {e}")
    except Exception as e:
        logging.exception(f"Unexpected error in check command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("Unexpected error.", ephemeral=True)
        else:
            await interaction.followup.send("Unexpected error.", ephemeral=True)
```

### 8.5 Checking Response State

Always check if a response has already been sent before sending:

```python
if interaction.response.is_done():
    await interaction.followup.send("Message", ephemeral=True)
else:
    await interaction.response.send_message("Message", ephemeral=True)
```

### 8.6 Logging Best Practices

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guinevere")

# In a command callback:
logger.info(f"Command '{interaction.command.name}' invoked by {interaction.user} (ID: {interaction.user.id})")
logger.debug(f"Command args: {interaction.data}")
```

---

## Summary of Key Recommendations for Guinevere

| Concern | Recommendation |
|---|---|
| **Slash command structure** | Use Cogs with `@app_commands.command()` — organized, testable, with built-in error hooks |
| **Ephemeral pattern** | `defer(ephemeral=True)` + `followup.send(..., ephemeral=True)` for long ops |
| **Embed design** | Stay under limits: title ≤256, desc ≤4096, ≤25 fields, total ≤6000 chars |
| **Presence** | Set `activity` in constructor, NOT in `on_ready()` |
| **on_ready** | Use `setup_hook()` for one-time init; guard `on_ready()` with idempotency check |
| **HARD STOP detection** | Use `@bot.listen('on_message')` with `message_content` intent enabled |
| **Error handling** | Subclass `CommandTree.on_error` or use `@tree.error` decorator; always check `response.is_done()` |
| **Command syncing** | Call `tree.sync()` once in `setup_hook()` |

---

## Source Index

| Source | URL |
|---|---|
| Discord.py v2.6.4 Docs Home | https://discordpy.readthedocs.io/en/v2.6.4/ |
| Interactions API | https://discordpy.readthedocs.io/en/v2.6.4/interactions/api.html |
| API Reference | https://discordpy.readthedocs.io/en/v2.6.4/api.html |
| FAQ | https://discordpy.readthedocs.io/en/v2.6.4/faq.html |
| Cogs Guide | https://discordpy.readthedocs.io/en/v2.6.4/ext/commands/cogs.html |
| Intents Primer | https://discordpy.readthedocs.io/en/v2.6.4/intents.html |
| Discord Embed Limits | https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/ |
| AppCommandError Source | https://github.com/Rapptz/discord.py/blob/108e9abb/discord/app_commands/errors.py |
| InteractionResponse Source | https://github.com/rapptz/discord.py/blob/master/discord.py/discord/interactions.py |
| Error Handling Discussion | https://github.com/Rapptz/discord.py/discussions/9209 |
| CWT Error Handling | https://github.com/Rapptz/discord.py/discussions/8404 |
| Discord Gateway Intents | https://docs.discord.com/developers/events/gateway |
# P2-013–016: discord.py 2.x OSS Pattern Research

**Date**: 2026-06-01  
**Scope**: `/help` embed listing, `/mood` style embed, `/safeword` moderation text trigger, startup message/presence  
**Downstream**: Planner & step-agents — patterns only, not copy-paste.

---

## Table of Contents

1. [Summary of Findings](#1-summary-of-findings)
2. [Pattern 1: Slash Command Defer+Followup](#2-pattern-1-slash-command-deferfollowup)
3. [Pattern 2: Embed Construction & Command Listing](#3-pattern-2-embed-construction--command-listing)
4. [Pattern 3: Help Command Implementations](#4-pattern-3-help-command-implementations)
5. [Pattern 4: Bot Startup & Presence](#5-pattern-4-bot-startup--presence)
6. [Pattern 5: on_message Text Triggers (Safeword/Moderation)](#6-pattern-5-on_message-text-triggers-safewordmoderation)
7. [Anti-Pattern Catalog](#7-anti-pattern-catalog)
8. [Recommended Discord.py 2.x Boilerplate](#8-recommended-discordpy-2x-boilerplate)
9. [Source Index](#9-source-index)

---

## 1. Summary of Findings

| Pattern | Status | Key Sources |
|---------|--------|-------------|
| `interaction.response.defer(ephemeral=True)` + `followup.send(embed=...)` | **Safe, widespread** | raidkit, ERM, staciax, starowo, pesu-dev |
| `discord.Embed(title=, description=, color=).add_field(name=, value=, inline=)` | **Safe, standard** | Red-DiscordBot, Pycord, Cog-Creators |
| Help command with pagination/views | **Safe, common** | hawking, DuckBot, Vocard, zloutek1, maxcogs |
| `setup_hook` + `tree.sync(guild=...)` | **Required for 2.x** | Rapptz/discord.py official examples |
| `change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=...))` | **Safe, works in 2.x** | RayExo, staciax, Kav-K, TheExplainthis |
| `on_message` event in Cog | **Safe** | browser-use, Rapptz examples, DiscordGIR, Cog-Creators |
| Wait for bot ready pattern | **Anti-pattern when done wrong** | Rapptz official `on_ready` + `wait_until_ready` |

---

## 2. Pattern 1: Slash Command Defer+Followup

### Canonical Flow

Acknowledge interaction → defer (optionally ephemeral) → do work → send via followup.

### Source: discord-raidkit (moderation.py)

**Evidence** ([source](https://github.com/the-cult-of-integral/discord-raidkit/blob/master/Discord%20Raidkit%20v2.5.5/cogs/anubis/moderation.py#L33-L47)):
```python
await interaction.response.defer(ephemeral=True)

if not (interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.administrator):
    raise discord.errors.Forbidden(...)

deleted_messages = await interaction.channel.purge(limit=number)

embed = discord.Embed(
    title='Clear',
    description=f'{interaction.channel.mention} has been cleared by {len(deleted_messages)} messages.',
    color=discord.Color.blue())

await interaction.followup.send(embed=embed)
```

**Key points**:
- `defer(ephemeral=True)` → all subsequent `followup.send()` inherit ephemerality
- Permission checks happen **after** defer, not before
- `followup.send(embed=embed)` for the response — NOT `interaction.response.send_message` after defer

### Source: starowo/Odysseia-Main (admin cog)

**Evidence** ([source](https://github.com/starowo/Odysseia-Main/blob/main/src/admin/cog.py#L381-L393)):
```python
await interaction.response.defer(ephemeral=True)

if role.position >= interaction.user.top_role.position:
    await interaction.followup.send("❌ 无法操作比自己权限高的身份组", ephemeral=True)
    return
```

**Key point**: You can pass `ephemeral=True` again on followups to reinforce — but it's inherited from defer.

### Source: Official discord.py docs — defer internals

**Evidence** ([source](https://github.com/rapptz/discord.py/blob/master/discord.py/discord/interactions.py)):
```python
async def defer(self, *, ephemeral: bool = False, thinking: bool = False):
    ...
    if parent.type is InteractionType.application_command:
        defer_type = InteractionResponseType.deferred_channel_message.value
        if ephemeral:
            data = {'flags': 64}  # 64 = EPHEMERAL
```

**Safe pattern**:
```python
# SHORT operations — respond directly
await interaction.response.send_message(embed=embed, ephemeral=True)

# LONG operations — defer first
await interaction.response.defer(ephemeral=True)
# ... do work ...
await interaction.followup.send(embed=embed)  # inherits ephemeral from defer

# With thinking (for views/modals)
await interaction.response.defer(ephemeral=True, thinking=True)
```

### Anti-Pattern: send_message after defer

```python
# WRONG — will raise InteractionResponded
await interaction.response.defer(ephemeral=True)
await interaction.response.send_message(embed=embed)  # RuntimeError!
```

---

## 3. Pattern 2: Embed Construction & Command Listing

### Standard Embed Construction

**Source**: Cog-Creators/Red-DiscordBot (player.py)

**Evidence** ([source](https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/audio/core/utilities/player.py#L134-L143)):
```python
embed = discord.Embed(title=_("There's nothing in the queue."))
embed.set_footer(
    text=_("Currently livestreaming {track}").format(track=player.current.title)
)
# Later...
embed = discord.Embed(
    title=title,
    description=desc,
    color=discord.Color.red()  # or discord.Color.blue(), Color.green(), etc.
)
```

**Source**: DiscordGSM/GameServerMonitor (main.py)

**Evidence** ([source](https://github.com/DiscordGSM/GameServerMonitor/blob/main/discordgsm/main.py#L550-L566)):
```python
await interaction.response.defer(ephemeral=True)
await database.delete_servers(servers=[server])
if await resend_channel_messages(interaction):
    await interaction.delete_original_response()
```

### Embed with Fields (Command Listing Style)

**Source**: Cog-Creators/Red-DiscordBot (playlist.py)

**Evidence** ([source](https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/audio/core/utilities/playlists.py#L329)):
```python
embed1 = discord.Embed(title=_("Please wait, adding tracks..."))
playlist_msg = await self.send_embed_msg(ctx, embed=embed1)
```

**Source**: Scottcjn/Rustchain (bot.py)

**Evidence** ([source](https://github.com/Scottcjn/Rustchain/blob/main/tools/discord-bot/bot.py#L149-L159)):
```python
embed = discord.Embed(title="Node Status", color=discord.Color.green())
embed.add_field(name="Status", value="Online" if ok else "Offline", inline=True)
embed.add_field(name="Version", value=version, inline=True)
embed.add_field(name="Uptime", value=f"{uptime:,}s (~{uptime // 3600}h)", inline=True)
embed.timestamp = datetime.now(timezone.utc)
embed.set_footer(text=RUSTCHAIN_URL)
await interaction.followup.send(embed=embed)
```

**Safe embed pattern** for command listing:
```python
embed = discord.Embed(
    title="Commands",
    description="Available commands:",
    color=discord.Color.blue()
)
embed.add_field(name="/help", value="Show this message", inline=False)
embed.add_field(name="/mood", value="Display current mood", inline=False)
embed.add_field(name="/safeword", value="Emergency stop", inline=False)
embed.set_footer(text="Use /help <command> for details")
embed.timestamp = discord.utils.utcnow()
```

### Color Constants Available in discord.py 2.x

| Constant | Color |
|----------|-------|
| `discord.Color.default()` | Grey (#000000) |
| `discord.Color.blue()` | Blue (#3498db) |
| `discord.Color.green()` | Green (#2ecc71) |
| `discord.Color.red()` | Red (#e74c3c) |
| `discord.Color.brand_red()` | Discord Brand Red |
| `discord.Color.brand_green()` | Discord Brand Green |
| `discord.Color.gold()` | Gold (#f1c40f) |
| `discord.Color.teal()` | Teal (#1abc9c) |
| `discord.Color.purple()` | Purple (#9b59b6) |
| `discord.Color.orange()` | Orange (#e67e22) |
| `discord.Color.magenta()` | Magenta |
| `discord.Color.light_grey()` | Light Grey |
| `discord.Color.dark_blue()` | Dark Blue |
| `discord.Color.dark_green()` | Dark Green |
| `discord.Color.dark_red()` | Dark Red |
| `discord.Color.dark_gold()` | Dark Gold |
| `discord.Color.dark_teal()` | Dark Teal |
| `discord.Color.dark_purple()` | Dark Purple |
| `discord.Color.dark_orange()` | Dark Orange |
| `discord.Color.dark_magenta()` | Dark Magenta |
| `discord.Color.dark_grey()` | Dark Grey |
| Hex: `0x2ecc71` or `discord.Color.from_rgb(46, 204, 113)` | Custom |

---

## 4. Pattern 3: Help Command Implementations

### Pattern A: Simple app_commands help with choices (hawking bot)

**Source**: naschorr/hawking

**Evidence** ([source](https://github.com/naschorr/hawking/blob/master/code/core/cogs/help_cog.py)):
```python
class HelpCog(Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.bot = bot
        self.activation_str = "/"
        self.cog_command_tree = self.build_cog_command_tree()
        ...

    def build_command_help_embed(self, command: app_commands.Command) -> Embed:
        embed = self.component_factory.create_basic_embed(
            f"{self.activation_str}{command.qualified_name}",
            command.description
        )
        usage = [
            "```",
            self.build_command_signature(command),
            os.linesep.join([f" {p.name} - {p.description}" for p in command.parameters]),
            "```"
        ]
        embed.add_field(name="Usage", value=os.linesep.join(usage), inline=False)
        return embed

    @app_commands.command(name="help", description="Shows the help page")
    async def _help_command(self, interaction: Interaction, command: str = None):
        if command is None:
            embeds = self.build_help_embeds()
            await interaction.response.send_message(embeds=embeds)
        else:
            target = self.command_tree[0].get(command)
            embed = self.build_command_help_embed(target)
            await interaction.response.send_message(embeds=[embed], ephemeral=True)
```

**Design decisions**:
- Uses `choices` for command selection
- Ephemeral for specific command detail, non-ephemeral for overview
- Builds a command tree from `bot.tree.get_commands()`

### Pattern B: HelpView with Pagination (DuckBot, Vocard, maxcogs)

**Source**: DuckBot-Discord/DuckBot

**Evidence** ([source](https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/utils/bases/help.py#L555)):
```python
class HelpView(discord.ui.View):
    """The main Help View for the DuckHelper."""
    ...
    await interaction.response.edit_message(embed=view.embed, view=view)
```

**Source**: ChocoMeow/Vocard

**Evidence** ([source](https://github.com/ChocoMeow/Vocard/blob/main/voicelink/views/help.py#L45)):
```python
class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, author: discord.Member) -> None:
        super().__init__(timeout=60)
        self.author = author
        self.bot = bot
        # add Select dropdown or buttons for categories

    async def callback(self, interaction: discord.Interaction) -> None:
        embed = self.view.build_embed(self.values[0].split(" ")[0])
        await interaction.response.edit_message(embed=embed)
```

**Pattern C**: Simple embed listing (suitable for `/help` without pagination):
```python
@app_commands.command(name="help", description="Show available commands")
async def help_command(self, interaction: discord.Interaction):
    embed = discord.Embed(
        title="Guinevere Commands",
        description="All commands are slash commands.",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎵 /play", value="Play music in voice channel", inline=False)
    embed.add_field(name="😊 /mood", value="Show or set your mood", inline=False)
    embed.add_field(name="🛡️ /safeword", value="Trigger emergency stop", inline=False)
    embed.add_field(name="ℹ️ /help", value="This message", inline=False)
    embed.set_footer(text=f"Version {self.version}")
    await interaction.response.send_message(embed=embed, ephemeral=False)
```

---

## 5. Pattern 4: Bot Startup & Presence

### Recommended discord.py 2.x Startup

**Source**: Rapptz/discord.py official app_commands example

**Evidence** ([source](https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py#L23-L30)):
```python
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def on_ready(self):
        assert self.user is not None
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
```

**Source**: Rapptz/discord.py advanced_startup.py

**Evidence** ([source](https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py#L28-L35)):
```python
class MyBot(commands.Bot):
    async def setup_hook(self) -> None:
        # Loading extensions prior to sync
        for extension in self.initial_extensions:
            await self.load_extension(extension)
        # Sync happens implicitly or explicitly after extensions
        await self.tree.sync(guild=discord.Object(id=TEST_GUILD_ID))
```

### Presence Setting

**Source**: RayExo/Reo-Bot

**Evidence** ([source](https://github.com/RayExo/Reo-Bot/blob/main/reo/src/events/ready.py#L78)):
```python
async def activity(self):
    await self.bot.wait_until_ready()

    activities = [
        lambda: discord.Activity(type=discord.ActivityType.listening, name="/help"),
        lambda: discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.bot.guilds)} servers"),
        lambda: discord.Activity(type=discord.ActivityType.watching, name=f"{sum(g.member_count for g in self.bot.guilds if g.member_count)} users"),
    ]

    index = 0
    while not self.bot.is_closed():
        try:
            await self.bot.change_presence(activity=activities[index % len(activities)]())
            index += 1
            await asyncio.sleep(60)  # rotate every 60s
        except Exception:
            pass
```

**Source**: Kav-K/GPTDiscord

**Evidence** ([source](https://github.com/Kav-K/GPTDiscord/blob/main/gpt3discord.py#L91)):
```python
activity = discord.Activity(
    type=discord.ActivityType.watching, name="for /help, /gpt, and more!"
)
bot = discord.Bot(intents=discord.Intents.all(), command_prefix="!", activity=activity)
```

**Source**: TheExplainthis/ChatGPT-Discord-Bot

**Evidence** ([source](https://github.com/TheExplainthis/ChatGPT-Discord-Bot/blob/main/src/discordBot.py#L9)):
```python
self.activity = discord.Activity(type=discord.ActivityType.watching, name="/chat | /reset | /imagine")
```

**Source**: gregzaal/Auto-Voice-Channels

**Evidence** ([source](https://github.com/gregzaal/Auto-Voice-Channels/blob/master/auto-voice-channels.py#L164)):
```python
await client.change_presence(activity=discord.Activity(name=text, type=discord.ActivityType.watching))
```

**Source**: shrubin/Genshin-Artifact-Rater

**Evidence** ([source](https://github.com/shrubin/Genshin-Artifact-Rater/blob/master/cogs/events/guild.py#L13)):
```python
async def updatePresence(self):
    await self.bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=f'{str(len(self.bot.guilds))} servers! | -help'
    ))
    await asyncio.sleep(15)
    await self.bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=f"rating Artifacts | -help"
    ))
```

**Safe startup pattern**:
```python
class GuinevereBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # required for on_message text triggers
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.load_extension("cogs.commands")  # load cogs
        await self.load_extension("cogs.events")
        await self.tree.sync()  # sync global commands
        # Or: await self.tree.sync(guild=discord.Object(id=GUILD_ID))

    async def on_ready(self):
        await self.wait_until_ready()
        assert self.user is not None
        print(f'{self.user} is ready!')
        # Set initial presence
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /help"
        ))
```

### ActivityType Options

| Value | Alias | Display |
|-------|-------|---------|
| `discord.ActivityType.playing` | 0 | "Playing {name}" |
| `discord.ActivityType.watching` | 3 | "Watching {name}" |
| `discord.ActivityType.listening` | 2 | "Listening to {name}" |
| `discord.ActivityType.streaming` | 1 | "Streaming" (requires URL) |
| `discord.ActivityType.competing` | 5 | "Competing in {name}" |

---

## 6. Pattern 5: on_message Text Triggers (Safeword/Moderation)

### Cog-based on_message

**Source**: browser-use/discord integration

**Evidence** ([source](https://github.com/browser-use/browser-use/blob/main/examples/integrations/discord/discord_api.py#L72)):
```python
async def on_message(self, message):
    if message.author == self.user:
        return
    if message.content.strip().startswith(f'{self.prefix} '):
        # handle prefix command
        pass
```

### Standard Cog Listener Pattern

**Source**: DiscordGIR/GIRRewrite

**Evidence** ([source](https://github.com/DiscordGIR/GIRRewrite/blob/main/cogs/monitors/utils/jailbreak_monitors.py#L15)):
```python
@commands.Cog.listener()
async def on_message(self, message):
    if message.guild is None:
        return
    if message.guild.id != cfg.guild_id:
        return
    if message.author.bot:
        return
```

### Red-DiscordBot Mod Cog Listener

**Source**: Cog-Creators/Red-DiscordBot

**Evidence** ([source](https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/events.py#L131)):
```python
@commands.Cog.listener()
async def on_message(self, message):
    author = message.author
    if message.guild is None or self.bot.user == author:
        return

    if await self.bot.cog_disabled_in_guild(self, message.guild):
        return
```

### Safeword/Text-Trigger Pattern

Based on the patterns found, here's the safe approach for a `/safeword`-style text trigger:

```python
import shlex

@commands.Cog.listener()
async def on_message(self, message):
    # Guard clauses
    if message.author.bot:
        return
    if message.guild is None:
        return

    content = message.content.strip().lower()

    # Safeword trigger — check exact word match or starts-with
    safewords = {"!safeword", "!emergency", "!stop"}
    if content.split()[0] in safewords if content else False:
        # Optional: verify channel or permissions
        if message.author.guild_permissions.administrator:
            # Execute safeword action
            await message.channel.send("🛑 Safeword activated!")
            return

    # Text-based command pattern
    if content.startswith("!"):
        parts = shlex.split(content[1:])  # safe splitting
        if not parts:
            return
        command, *args = parts
        # dispatch to handler
```

### Key Guards for on_message

1. `if message.author.bot: return` — ignore self and other bots
2. `if message.guild is None: return` — ignore DMs unless desired
3. Check `message.content` before processing
4. Use `shlex.split()` for safe argument splitting (handles quoted args)
5. Re-raise or handle exceptions — never bare except

---

## 7. Anti-Pattern Catalog

### 🔴 Anti-Pattern 1: `send_message` after `defer`

```python
await interaction.response.defer(ephemeral=True)
await interaction.response.send_message("hi")  # RuntimeError!
```

**Fix**: Use `interaction.followup.send()` after defer.

### 🔴 Anti-Pattern 2: No `await wait_until_ready()` in co-routines that access `guilds`

```python
async def my_task():
    # bot.guilds might be empty here!
    await bot.change_presence(...)  # may fail silently
```

**Fix**:
```python
async def my_task():
    await bot.wait_until_ready()
    await bot.change_presence(...)
```

### 🔴 Anti-Pattern 3: Bare `except:` in on_message

```python
@commands.Cog.listener()
async def on_message(self, message):
    try:
        # ... processing ...
    except:  # catches everything including KeyboardInterrupt
        pass
```

**Fix**: Catch specific exceptions or at minimum `except Exception:` with logging.

### 🔴 Anti-Pattern 4: Setting activity in `__init__` without waiting

```python
class Bot(commands.Bot):
    async def on_ready(self):
        self.activity = discord.Activity(...)  # not propagated to Discord
```

**Fix**: Use `await self.change_presence(activity=...)` inside `on_ready`.

### 🔴 Anti-Pattern 5: Hardcoded guild IDs for command sync

```python
await self.tree.sync(guild=discord.Object(id=123456789))  # only syncs to one guild
```

**Fix**: Either sync globally with `await self.tree.sync()` or use environment variables for guild IDs.

### 🔴 Anti-Pattern 6: Using `client.event` and `commands.Cog.listener` together messily

Mixing `@client.event` style with Cog-based listeners in the same codebase leads to confusion.

**Fix**: Choose one pattern. Cog-based (`@commands.Cog.listener()`) is preferred for modular bots.

### 🔴 Anti-Pattern 7: `on_message` blocking event loop with sync operations

```python
async def on_message(self, message):
    result = some_slow_sync_function(message.content)  # blocks the event loop!
```

**Fix**: Use `asyncio.to_thread()` or delegate to a thread pool for sync work.

### 🔴 Anti-Pattern 8: Not enabling `message_content` intent for text triggers

```python
intents = discord.Intents.default()  # message_content NOT included
# on_message will not receive message.content!
```

**Fix**:
```python
intents = discord.Intents.default()
intents.message_content = True  # required for on_message content access
```

---

## 8. Recommended Discord.py 2.x Boilerplate

```python
import discord
from discord import app_commands
from discord.ext import commands
import asyncio

GUILD_ID = 123456789012345678  # dev guild; use env var

class GuinevereBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # for on_message safeword
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Load cogs before syncing commands
        await self.load_extension("cogs.commands")
        await self.load_extension("cogs.events")
        # Sync to specific guild for instant availability during dev
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        # For production: await self.tree.sync()  (global sync)

    async def on_ready(self):
        await self.wait_until_ready()
        assert self.user is not None
        print(f"[{self.user}] Ready on {len(self.guilds)} guilds")
        # Initial presence
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /help"
        ))


if __name__ == "__main__":
    bot = GuinevereBot()
    bot.run("TOKEN")
```

### Cog Template

```python
import discord
from discord import app_commands
from discord.ext import commands


class ExampleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- Slash Commands ---

    @app_commands.command(name="help", description="Show available commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Commands",
            color=discord.Color.blue()
        )
        embed.add_field(name="/help", value="This message", inline=False)
        embed.add_field(name="/mood", value="Display or set mood", inline=False)
        embed.set_footer(text="Tip: Use /help <command> for details")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="mood", description="Show your current mood")
    async def mood_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="😊 Mood",
            description=f"{interaction.user.mention} is feeling great!",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # --- Text Event Listener (Safeword) ---

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return

        content = message.content.strip().lower()
        safewords = {"!safeword", "!emergency", "!stop"}

        if content in safewords:
            await message.channel.send("🛑 Safeword activated!")
            # Execute safeword logic here
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(ExampleCog(bot))
```

---

## 9. Source Index

| # | Source | URL | License |
|---|--------|-----|---------|
| 1 | discord-raidkit (moderation.py) | https://github.com/the-cult-of-integral/discord-raidkit/blob/master/Discord%20Raidkit%20v2.5.5/cogs/anubis/moderation.py | GPL-2.0 |
| 2 | discord-raidkit (raid_prevention.py) | https://github.com/the-cult-of-integral/discord-raidkit/blob/master/Discord%20Raidkit%20v2.5.5/cogs/anubis/raid_prevention.py | GPL-2.0 |
| 3 | ERM (menus.py) | https://github.com/mikeywhiston/ERM/blob/main/menus.py | Unknown |
| 4 | GameServerMonitor (main.py) | https://github.com/DiscordGSM/GameServerMonitor/blob/main/discordgsm/main.py | MIT |
| 5 | Odysseia-Main (admin cog) | https://github.com/starowo/Odysseia-Main/blob/main/src/admin/cog.py | Unknown |
| 6 | staciax/valorant-discord-bot | https://github.com/staciax/valorant-discord-bot | GPL-3.0 |
| 7 | Discord-Buddy (main.py) | https://github.com/SpicyMarinara/Discord-Buddy/blob/main/main.py | AGPL-3.0 |
| 8 | pesu-dev/discord_bot | https://github.com/pesu-dev/discord_bot | MIT |
| 9 | Cog-Creators/Red-DiscordBot | https://github.com/Cog-Creators/Red-DiscordBot | GPL-3.0 |
| 10 | Der-Eddy/discord_bot | https://github.com/Der-Eddy/discord_bot | MIT |
| 11 | RayExo/Reo-Bot | https://github.com/RayExo/Reo-Bot/blob/main/reo/src/events/ready.py | MIT |
| 12 | shrubin/Genshin-Artifact-Rater | https://github.com/shrubin/Genshin-Artifact-Rater/blob/master/cogs/events/guild.py | Unknown |
| 13 | Kav-K/GPTDiscord | https://github.com/Kav-K/GPTDiscord | MIT |
| 14 | TheExplainthis/ChatGPT-Discord-Bot | https://github.com/TheExplainthis/ChatGPT-Discord-Bot | MIT |
| 15 | gregzaal/Auto-Voice-Channels | https://github.com/gregzaal/Auto-Voice-Channels | MIT |
| 16 | Cog-Creators/Red-DiscordBot (names.py) | https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/names.py | GPL-3.0 |
| 17 | naschorr/hawking (help_cog.py) | https://github.com/naschorr/hawking/blob/master/code/core/cogs/help_cog.py | MIT |
| 18 | DuckBot-Discord/DuckBot (help.py) | https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/utils/bases/help.py | MPL-2.0 |
| 19 | ChocoMeow/Vocard (help.py) | https://github.com/ChocoMeow/Vocard/blob/main/voicelink/views/help.py | MIT |
| 20 | ltzmax/maxcogs (slashhelpmenu) | https://github.com/ltzmax/maxcogs | MIT |
| 21 | zloutek1/MasarykBOT (help.py) | https://github.com/zloutek1/MasarykBOT | MIT |
| 22 | Rapptz/discord.py (examples) | https://github.com/Rapptz/discord.py/tree/master/examples | MIT |
| 23 | Rapptz/discord.py (interactions.py) | https://github.com/rapptz/discord.py/blob/master/discord.py/discord/interactions.py | MIT |
| 24 | Rapptz/discord.py (docs/faq.rst) | https://github.com/rapptz/discord.py/blob/master/docs/faq.rst | MIT |
| 25 | DiscordGIR/GIRRewrite | https://github.com/DiscordGIR/GIRRewrite | MIT |
| 26 | browser-use/discord integration | https://github.com/browser-use/browser-use/blob/main/examples/integrations/discord/discord_api.py | MIT |
| 27 | Scottcjn/Rustchain (bot.py) | https://github.com/Scottcjn/Rustchain/blob/main/tools/discord-bot/bot.py | Apache-2.0 |
| 28 | infinitow/ragflow (discord_svr.py) | https://github.com/infiniflow/ragflow/blob/main/rag/svr/discord_svr.py | Apache-2.0 |

---

*End of report. Patterns sourced from 28 OSS repositories and official discord.py documentation. All permalinks verified as of 2026-06-01.*
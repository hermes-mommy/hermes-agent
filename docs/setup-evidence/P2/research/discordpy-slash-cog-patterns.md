# Discord.py 2.x — Slash Command & Cog Implementation Patterns

> **Date**: 2026-06-01  
> **Scope**: P2-013 (/mood), P2-014 (/help), P2-015 (/safeword), P2-016 (startup/presence)  
> **Source**: Official discord.py documentation v2.x, official examples, and library source code  
> **Library Version Target**: discord.py ≥ 2.0 (latest stable: v2.5.x)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [app_commands Slash Commands](#2-app_commands-slash-commands)
3. [Cogs with app_commands](#3-cogs-with-app_commands)
4. [Interaction Response Patterns](#4-interaction-response-patterns)
5. [Embed Construction](#5-embed-construction)
6. [Bot Presence & Activity](#6-bot-presence--activity)
7. [Startup / on_ready Patterns](#7-startup--on_ready-patterns)
8. [Common Pitfalls](#8-common-pitfalls)
9. [Recommended Patterns for This Codebase](#9-recommended-patterns-for-this-codebase)
10. [Reference Links](#10-reference-links)

---

## 1. Architecture Overview

discord.py 2.x has two parallel command systems:

| System | Module | Invocation | Use Case |
|---|---|---|---|
| **Traditional Commands** | `discord.ext.commands` | Prefix-based (`!cmd`) | Legacy / text-based bots |
| **Application Commands** | `discord.app_commands` | Slash (`/cmd`) / Context Menu | Modern Discord bots |
| **Hybrid Commands** | `discord.ext.commands` hybrid | Both prefix + slash | Migration / dual support |

For **P2 tasks**, use **`discord.app_commands`** (slash commands) exclusively.  
The `CommandTree` is the central registry — all slash commands must be registered and synced.

**Key objects:**
- `discord.app_commands.CommandTree` — holds all slash/context menu commands
- `discord.Interaction` — the object received when a user invokes a slash command
- `InteractionResponse` — accessed via `interaction.response`, used to reply exactly once
- `Webhook` — accessed via `interaction.followup`, used for follow-up messages after the initial response

---

## 2. app_commands Slash Commands

### 2.1 Basic Global Command (on a Client)

```python
import discord
from discord import app_commands

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync to a testing guild for instant availability
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

@client.tree.command()
async def hello(interaction: discord.Interaction):
    """Says hello!"""
    await interaction.response.send_message(f'Hi, {interaction.user.mention}')
```

**Source**: [Rapptz/discord.py/examples/app_commands/basic.py](https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py)

### 2.2 Command with Parameters

```python
@client.tree.command()
@app_commands.describe(
    first_value='The first value you want to add something to',
    second_value='The value you want to add to the first value',
)
async def add(interaction: discord.Interaction, first_value: int, second_value: int):
    """Adds two numbers together."""
    await interaction.response.send_message(f'{first_value} + {second_value} = {first_value + second_value}')
```

**Source**: [Rapptz/discord.py/examples/app_commands/basic.py](https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py)

### 2.3 Optional Parameters

```python
from typing import Optional

@client.tree.command()
@app_commands.describe(
    member='The member you want to get the joined date from; defaults to the user who uses the command'
)
async def joined(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    """Says when a member joined."""
    user = member or interaction.user
    assert isinstance(user, discord.Member)
    if user.joined_at is None:
        await interaction.response.send_message(f'{user} has no join date.')
    else:
        await interaction.response.send_message(f'{user} joined {discord.utils.format_dt(user.joined_at)}')
```

### 2.4 Choices via Literal or Enum

```python
from typing import Literal
from enum import Enum

# Method 1: Literal (simplest)
@client.tree.command()
@app_commands.describe(action='The action to do')
async def shop(interaction: discord.Interaction, action: Literal['Buy', 'Sell'], item: str):
    await interaction.response.send_message(f'Action: {action}\nItem: {item}')

# Method 2: Enum (reusable)
class Mood(Enum):
    happy = 1
    sad = 2
    excited = 3
    calm = 4

@client.tree.command()
async def mood(interaction: discord.Interaction, mood: Mood):
    """Set your mood"""
    await interaction.response.send_message(f'Mood set to {mood.name}')
```

**Source**: [Rapptz/discord.py/examples/app_commands/transformers.py](https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/transformers.py)

### 2.5 Command Renaming

```python
@client.tree.command()
@app_commands.rename(text_to_send='text')
@app_commands.describe(text_to_send='Text to send in the current channel')
async def send(interaction: discord.Interaction, text_to_send: str):
    """Sends the text into the current channel."""
    await interaction.response.send_message(text_to_send)
```

### 2.6 Guild-Specific Commands

```python
MY_GUILD = discord.Object(id=123456789)

@client.tree.command(guild=MY_GUILD)
async def guild_only_command(interaction: discord.Interaction):
    """Only visible in the specified guild."""
    await interaction.response.send_message("This is guild-only!")
```

### 2.7 Context Menu Commands

```python
# User context menu
@client.tree.context_menu(name='Show Join Date')
async def show_join_date(interaction: discord.Interaction, member: discord.Member):
    if member.joined_at is None:
        await interaction.response.send_message(f'{member} has no join date.')
    else:
        await interaction.response.send_message(f'{member} joined at {discord.utils.format_dt(member.joined_at)}')

# Message context menu
@client.tree.context_menu(name='Report to Moderators')
async def report_message(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message(
        f'Thanks for reporting this message by {message.author.mention} to our moderators.',
        ephemeral=True
    )
```

---

## 3. Cogs with app_commands

### 3.1 Standard Cog with app_commands

The standard `Cog` class supports both traditional commands and `app_commands`:

```python
import discord
from discord import app_commands
from discord.ext import commands

class MoodCog(commands.Cog):
    """Cog for mood-related commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='mood', description='Set your current mood')
    @app_commands.describe(mood='Choose your mood')
    async def mood(self, interaction: discord.Interaction, mood: str):
        """Set your current mood"""
        await interaction.response.send_message(
            f'{interaction.user.mention} is feeling **{mood}**!',
            ephemeral=True
        )

    @app_commands.command(name='help', description='Show available commands')
    async def help_command(self, interaction: discord.Interaction):
        """Show bot help"""
        embed = discord.Embed(
            title='Help',
            description='Available commands',
            color=discord.Color.blue()
        )
        embed.add_field(name='/mood', value='Set your mood', inline=False)
        embed.add_field(name='/help', value='Show this message', inline=False)
        embed.add_field(name='/safeword', value='Emergency stop', inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(MoodCog(bot))
```

**Key points:**
- Cog class inherits from `commands.Cog`
- `@app_commands.command()` decorator defines a slash command inside the cog
- The `setup()` function is the required entry point for extension loading
- In discord.py 2.0+, `bot.add_cog()` is a coroutine and must be awaited
- The method name becomes the command name unless overridden with `name=`

### 3.2 GroupCog — Commands in a Group

For commands that should be grouped under a parent (e.g., `/mood set`):

```python
from discord.ext import commands
from discord import app_commands

@app_commands.guild_only()
class MoodGroupCog(commands.GroupCog, group_name='mood'):
    """Group for /mood commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='set', description='Set your mood')
    @app_commands.describe(mood='Choose a mood')
    async def set_mood(self, interaction: discord.Interaction, mood: str):
        await interaction.response.send_message(f'Mood set to {mood}', ephemeral=True)

    @app_commands.command(name='get', description='Get your current mood')
    async def get_mood(self, interaction: discord.Interaction):
        await interaction.response.send_message('Your mood is...', ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(MoodGroupCog(bot))
```

**Source**: [Official docs](https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#groupcog)

**Key points:**
- `GroupCog` inherits from both `Cog` and `app_commands.Group`
- All `@app_commands.command()` decorators become subcommands
- `group_name` parameter sets the slash group name (defaults to the class name)
- Decorators on the class (`@guild_only()`, etc.) apply to the whole group

### 3.3 Cog Lifecycle Hooks

```python
class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        """Called when the cog is loaded (after add_cog). v2.0+"""
        print(f'{self.__class__.__name__} loaded')

    async def cog_unload(self):
        """Called when the cog is unloaded. v2.0+"""
        print(f'{self.__class__.__name__} unloaded')

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Global check for all app_commands in this cog."""
        return True  # Return False to prevent the command from running

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for all app_commands in this cog."""
        await interaction.response.send_message(f'An error occurred: {error}', ephemeral=True)
```

### 3.4 Loading Extensions (Recommended)

```python
# In main.py
import discord
from discord.ext import commands

class Guinevere(commands.Bot):
    async def setup_hook(self):
        await self.load_extension('cogs.mood')
        await self.load_extension('cogs.help')
        await self.load_extension('cogs.safeword')
        # Sync commands to a testing guild for instant availability
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

bot = Guinevere(command_prefix=commands.when_mentioned, intents=discord.Intents.default())
bot.run('TOKEN')
```

**Source**: [Rapptz/discord.py/examples/advanced_startup.py](https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py)

**Important**: In discord.py 2.0+, `load_extension()` is a coroutine and must be awaited. Extensions should be loaded in `setup_hook()`, NOT in `__init__()`.

---

## 4. Interaction Response Patterns

### 4.1 Initial Response — `send_message()`

Every slash command **must** produce an initial response (within 3 seconds, or Discord shows "interaction failed").

```python
await interaction.response.send_message(
    content='Hello!',
    ephemeral=False,         # True = only visible to the user
    embed=embed,             # Single embed
    embeds=[embed1, embed2], # Multiple embeds (max 10)
    view=my_view,            # UI components
    file=my_file,            # Single file
    files=[f1, f2],          # Multiple files (max 10)
    delete_after=30.0,       # Auto-delete after N seconds
    silent=False,            # Suppress push notification
)
```

**Source**: [Official docs — InteractionResponse.send_message](https://discordpy.readthedocs.io/en/stable/interactions/api.html#discord.InteractionResponse.send_message)

### 4.2 Ephemeral Messages

```python
# Only visible to the command user
await interaction.response.send_message('This is private!', ephemeral=True)
```

Key behavior:
- Ephemeral messages are only visible to the user who invoked the command
- If a `View` is attached to an ephemeral message with no timeout, it gets a 15-minute timeout
- Followups can also be ephemeral via `followup.send(..., ephemeral=True)`

### 4.3 Deferring (Slow Operations)

Use when the response takes more than 3 seconds to prepare:

```python
# Defer first (acknowledge the interaction)
await interaction.response.defer(ephemeral=True, thinking=True)

# Then send the actual response via followup
await asyncio.sleep(5)  # Long operation
await interaction.followup.send('Here is your result!', ephemeral=True)
```

**Source**: [Official docs — InteractionResponse.defer](https://discordpy.readthedocs.io/en/stable/interactions/api.html#discord.InteractionResponse.defer)

Parameters:
- `ephemeral=True` — shows the "bot is thinking" as ephemeral
- `thinking=True` — shows "bot is thinking" state; you MUST send a followup later

### 4.4 Followup Messages

After the initial response, all additional messages must use `followup`:

```python
# After initial response
await interaction.response.send_message('Initial response')

# Additional messages
await interaction.followup.send('Follow-up message')
await interaction.followup.send('Another follow-up', ephemeral=True)
```

### 4.5 Editing Responses

```python
# Edit the initial response
await interaction.edit_original_response(content='Updated content')

# Or through followup
msg = await interaction.followup.send('Message to edit later')
await msg.edit(content='Edited content')
```

### 4.6 Deleting Responses

```python
# Delete the original response
await interaction.delete_original_response()

# Delete a followup
msg = await interaction.followup.send('Temporary message')
await msg.delete(delay=5.0)  # Delete after 5 seconds
```

### 4.7 Checking If Already Responded

```python
if interaction.response.is_done():
    # Already responded — use followup
    await interaction.followup.send('Additional info')
else:
    # Not yet responded — use response
    await interaction.response.send_message('First response')
```

**This is critical** — calling `interaction.response.send_message()` after already responding raises `InteractionResponded`.

---

## 5. Embed Construction

### 5.1 Basic Embed

```python
embed = discord.Embed(
    title='Command Title',
    description='Description text here',
    color=discord.Color.blue(),       # or 0x00ff00, or discord.Color.from_rgb(r, g, b)
    url='https://example.com',        # Title becomes a hyperlink
    timestamp=datetime.datetime.utcnow(),  # Footer timestamp
)
```

### 5.2 Embed with Fields

```python
embed = discord.Embed(
    title='Help - Available Commands',
    description='Here are all the commands you can use:',
    color=discord.Color.purple(),
)

embed.add_field(name='/mood', value='Set your current mood', inline=False)
embed.add_field(name='/help', value='Show this help message', inline=False)
embed.add_field(name='/safeword', value='Emergency stop for active sessions', inline=False)

embed.set_author(name='Guinevere', icon_url='https://...')
embed.set_footer(text='Use /help for more info')
embed.set_thumbnail(url='https://...')
```

### 5.3 Predefined Colors

```python
discord.Color.default()      # Grey
discord.Color.blue()         # Blue
discord.Color.green()        # Green
discord.Color.purple()       # Purple
discord.Color.gold()         # Gold
discord.Color.orange()       # Orange
discord.Color.red()          # Red
discord.Color.teal()         # Teal
discord.Color.dark_theme()   # Dark theme compatible (2.0+)
discord.Color.from_rgb(255, 0, 0)  # Custom RGB
```

### 5.4 Embed Limits

| Limit | Value |
|---|---|
| Title | 256 characters |
| Description | 4096 characters |
| Fields | 25 maximum |
| Field name | 256 characters |
| Field value | 1024 characters |
| Footer text | 2048 characters |
| Author name | 256 characters |
| Total embeds per message | 10 |
| Total characters (all embeds) | 6000 |

---

## 6. Bot Presence & Activity

### 6.1 Change Presence at Runtime

```python
from discord import Status, Game, Activity, ActivityType

# Playing status
await bot.change_presence(
    activity=discord.Game(name='with your feelings'),
    status=discord.Status.online
)

# Watching status
await bot.change_presence(
    activity=discord.Activity(type=discord.ActivityType.watching, name='over you'),
    status=discord.Status.idle
)

# Listening status
await bot.change_presence(
    activity=discord.Activity(type=discord.ActivityType.listening, name='your commands'),
    status=discord.Status.dnd
)

# Streaming status
await bot.change_presence(
    activity=discord.Streaming(name='Coding Live', url='https://twitch.tv/...'),
    status=discord.Status.online
)

# Clear presence
await bot.change_presence(activity=None, status=discord.Status.online)
```

**Source**: [Official docs — Client.change_presence](https://discordpy.readthedocs.io/en/stable/api.html#discord.Client.change_presence)

### 6.2 Status Types

| `discord.Status` | Description |
|---|---|
| `online` | Green dot |
| `idle` | Yellow moon |
| `dnd` | Red (do not disturb) |
| `offline` | Grey (invisible) |

### 6.3 Activity Types

```python
discord.ActivityType.playing     # "Playing ..."
discord.ActivityType.watching    # "Watching ..."
discord.ActivityType.listening   # "Listening to ..."
discord.ActivityType.streaming   # "Streaming ..." (requires URL)
discord.ActivityType.competing   # "Competing in ..." (2.0+)
```

---

## 7. Startup / on_ready Patterns

### 7.1 `setup_hook()` vs `on_ready()`

| Hook | When Called | Use For |
|---|---|---|
| `setup_hook()` | After login, before websocket connect | Loading cogs, DB connections, sync commands |
| `on_ready()` | After cache is ready (guilds, members loaded) | Presence setting, post-cache notifications |

```python
class Guinevere(commands.Bot):
    async def setup_hook(self):
        """Called once during login, before websocket connection."""
        # Load extensions BEFORE command sync
        for ext in self.initial_extensions:
            await self.load_extension(ext)

        # Sync commands to testing guild
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

        # Initialize database connections, etc.
        await self.init_database()

    async def on_ready(self):
        """Called when the client is ready (cache populated)."""
        assert self.user is not None  # Type narrowing
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

        # Set presence AFTER ready
        await self.change_presence(
            activity=discord.Game(name='/help for commands'),
            status=discord.Status.online
        )
```

**Source**: [Rapptz/discord.py/examples/advanced_startup.py](https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py)

### 7.2 Standard on_ready Pattern

```python
@bot.event
async def on_ready():
    assert bot.user is not None
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'Connected to {len(bot.guilds)} guilds')
    print('------')

    # Set initial presence
    await bot.change_presence(
        activity=discord.Game(name='with the API'),
        status=discord.Status.online
    )
```

**Source**: [Rapptz/discord.py/examples/basic_bot.py](https://github.com/Rapptz/discord.py/blob/master/examples/basic_bot.py)

### 7.3 Startup Logging with Extension Loading

```python
# Complete startup sequence:
# 1. bot.start(token) → bot.login(token) → calls setup_hook()
# 2. setup_hook(): load extensions, DB init, command sync
# 3. bot.connect() → websocket connects
# 4. GUILD_CREATE events stream in (cache building)
# 5. READY event → on_ready() fires
# 6. on_ready(): set presence, log stats, notify channels

import logging
logger = logging.getLogger('discord')

@bot.event
async def on_ready():
    logger.info(f'Bot ready: {bot.user} (ID: {bot.user.id})')
    logger.info(f'Guilds: {len(bot.guilds)}')
    logger.info(f'Cogs loaded: {list(bot.cogs.keys())}')
    await bot.change_presence(
        activity=discord.Game(name=f'/help | {len(bot.guilds)} servers'),
        status=discord.Status.online
    )
```

### 7.4 Starting the Bot (Modern Pattern)

```python
# discord.py 2.0+ preferred pattern with async context manager
import asyncio

async def main():
    async with Guinevere(...) as bot:
        await bot.start('TOKEN')

asyncio.run(main())
```

**Source**: [Rapptz/discord.py/examples/advanced_startup.py](https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py)

---

## 8. Common Pitfalls

### 8.1 `InteractionResponded` Error

**Problem**: Calling `interaction.response.send_message()` more than once.

**Fix**:
```python
# WRONG — will raise InteractionResponded
await interaction.response.send_message('First')
await interaction.response.send_message('Second')  # ERROR!

# RIGHT — use followup for subsequent messages
await interaction.response.send_message('First')
await interaction.followup.send('Second')  # OK
```

### 8.2 Early Return After Ephemeral Response

**Problem**: Sending an ephemeral response then returning early can confuse users.

**Pattern**:
```python
# Guard clause with ephemeral response
if not condition:
    await interaction.response.send_message('Cannot do that.', ephemeral=True)
    return  # Must return after sending

# Continue with normal flow
await interaction.response.send_message('Success!')
```

### 8.3 `defer()` Must Be Followed by `followup.send()`

**Problem**: Calling `defer(thinking=True)` but never sending a followup.

```python
# WRONG — user sees "bot is thinking..." forever
await interaction.response.defer(thinking=True)
# ... never sends a followup

# RIGHT
await interaction.response.defer(thinking=True, ephemeral=True)
# ... do work ...
await interaction.followup.send('Result here')
```

### 8.4 `load_extension()` is a Coroutine in 2.x

**Problem**: Calling `bot.load_extension(...)` without `await`.

```python
# WRONG (works in 1.x, broken in 2.x)
bot.load_extension('cogs.mood')

# RIGHT (discord.py 2.0+)
await bot.load_extension('cogs.mood')
```

### 8.5 Command Registration in Wrong Scope

**Problem**: Using `@bot.tree.command()` inside a cog file.

```python
# WRONG — must use @app_commands.command() inside cog methods
class MyCog(commands.Cog):
    @bot.tree.command()  # ERROR: 'bot' not defined in this scope
    async def cmd(self, interaction: ...

# RIGHT
class MyCog(commands.Cog):
    @app_commands.command()
    async def cmd(self, interaction: discord.Interaction, ...
```

### 8.6 `@app_commands.guild_only()` vs `@commands.guild_only()`

- Use `@app_commands.guild_only()` for slash commands
- Use `@commands.guild_only()` for traditional prefix commands
- They are **not interchangeable**

### 8.7 Missing `self` in Cog Methods

```python
# WRONG — missing self parameter
class MyCog(commands.Cog):
    @app_commands.command()
    async def cmd(interaction: discord.Interaction):  # TypeError!

# RIGHT
class MyCog(commands.Cog):
    @app_commands.command()
    async def cmd(self, interaction: discord.Interaction):
        ...
```

### 8.8 Type Narrowing for `bot.user`

`bot.user` can be `None` before login. Always narrow:

```python
@bot.event
async def on_ready():
    assert bot.user is not None  # Safe after on_ready
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
```

---

## 9. Recommended Patterns for This Codebase

### 9.1 Cog File Template

```python
# cogs/mood.py
import discord
from discord import app_commands
from discord.ext import commands


class Mood(commands.Cog):
    """Cog for mood-related commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        print(f'{self.__class__.__name__} loaded')

    @app_commands.command(name='mood', description='Set your current mood')
    @app_commands.describe(mood='Choose your mood state')
    async def set_mood(self, interaction: discord.Interaction, mood: str):
        """Set your current mood"""
        # TODO: Persist mood to database
        await interaction.response.send_message(
            f'{interaction.user.mention} is feeling **{mood}**!',
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Mood(bot))
```

### 9.2 Help Command Pattern

```python
# cogs/help.py
import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):
    """Help command cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='help', description='Show available commands')
    async def help_command(self, interaction: discord.Interaction):
        """Show the help message"""
        embed = discord.Embed(
            title='Guinevere — Help',
            description='Here are the commands you can use:',
            color=discord.Color.purple(),
        )
        embed.add_field(name='/mood', value='Set your current mood', inline=False)
        embed.add_field(name='/help', value='Show this help message', inline=False)
        embed.add_field(name='/safeword', value='Emergency stop for active sessions', inline=False)
        embed.set_footer(text='Guinevere — Your AI Companion')

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
```

### 9.3 Safeword Command Pattern

```python
# cogs/safeword.py
import discord
from discord import app_commands
from discord.ext import commands


class Safeword(commands.Cog):
    """Safeword / emergency stop cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='safeword', description='Emergency stop for active sessions')
    @app_commands.describe(reason='Optional reason for triggering safeword')
    async def safeword(self, interaction: discord.Interaction, reason: str = None):
        """Trigger safeword to stop active sessions"""
        # TODO: Implement actual safeword logic

        embed = discord.Embed(
            title='🛑 Safeword Triggered',
            description='All active sessions have been stopped.',
            color=discord.Color.red(),
        )
        if reason:
            embed.add_field(name='Reason', value=reason, inline=False)
        embed.set_footer(text='You are safe now.')

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Safeword(bot))
```

### 9.4 Main Bot Startup Template

```python
# main.py
import asyncio
import logging

import discord
from discord.ext import commands


class Guinevere(commands.Bot):
    def __init__(self, testing_guild_id: int | None = None):
        intents = discord.Intents.default()
        # Enable required intents as needed:
        # intents.message_content = True
        # intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
        )
        self.testing_guild_id = testing_guild_id
        self.initial_extensions = [
            'cogs.mood',
            'cogs.help',
            'cogs.safeword',
        ]

    async def setup_hook(self):
        # Load extensions
        for ext in self.initial_extensions:
            await self.load_extension(ext)
            logging.info(f'Loaded extension: {ext}')

        # Sync commands to testing guild (for instant availability)
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logging.info(f'Synced commands to testing guild {self.testing_guild_id}')

    async def on_ready(self):
        assert self.user is not None
        logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logging.info(f'Connected to {len(self.guilds)} guilds')
        logging.info(f'Loaded cogs: {list(self.cogs.keys())}')
        logging.info('------')

        # Set bot presence
        await self.change_presence(
            activity=discord.Game(name='/help for commands'),
            status=discord.Status.online,
        )


async def main():
    # Configure logging
    discord.utils.setup_logging(level=logging.INFO)

    async with Guinevere(testing_guild_id=123456789) as bot:
        await bot.start('YOUR_TOKEN_HERE')


if __name__ == '__main__':
    asyncio.run(main())
```

### 9.5 Key Decisions for This Codebase

| Decision | Recommendation | Rationale |
|---|---|---|
| Command system | `app_commands` (pure slash) | Modern, discoverable, no prefix needed |
| Cog base class | `commands.Cog` | Standard, well-tested, supports lifecycle hooks |
| Extension loading | In `setup_hook()` via `load_extension()` | Required async pattern in 2.x |
| Command sync | `copy_global_to()` + `sync()` on testing guild | Avoids 1-hour propagation delay during dev |
| Response style | `interaction.response.send_message()` with `ephemeral=True` | Private by default for P2 commands |
| Error handling | `cog_app_command_error()` per cog | Isolated error handling per cog |
| Presence | `change_presence()` in `on_ready()` | Safe after cache is populated |
| Startup message | Log on_ready with user, guild count, loaded cogs | Debugging and operational awareness |
| Followup pattern | Check `interaction.response.is_done()` before sending | Prevents `InteractionResponded` errors |

---

## 10. Reference Links

- **Official Docs**: https://discordpy.readthedocs.io/en/stable/
- **Interactions API Reference**: https://discordpy.readthedocs.io/en/stable/interactions/api.html
- **Commands & Cogs API**: https://discordpy.readthedocs.io/en/stable/ext/commands/api.html
- **Client API (change_presence, setup_hook, on_ready)**: https://discordpy.readthedocs.io/en/stable/api.html#discord.Client
- **Embed Constructor**: https://discordpy.readthedocs.io/en/stable/api.html#discord.Embed
- **Official Examples — basic.py (app_commands)**: https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py
- **Official Examples — transformers.py (app_commands)**: https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/transformers.py
- **Official Examples — advanced_startup.py**: https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py
- **Official Examples — basic_bot.py**: https://github.com/Rapptz/discord.py/blob/master/examples/basic_bot.py
- **Official Examples — views/settings.py (followup pattern)**: https://github.com/Rapptz/discord.py/blob/master/examples/views/settings.py
- **Context7 Library ID**: `/websites/discordpy_readthedocs_io_en`
- **GitHub Repo**: `Rapptz/discord.py`

---

*End of research report. For questions about specific patterns, refer to the official docs linked above.*
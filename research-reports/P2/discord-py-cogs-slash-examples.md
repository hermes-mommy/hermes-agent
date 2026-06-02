# discord.py 2.x — Cog Architecture & Slash Commands: Research Report

**Date**: 2026-06-01  
**Scope**: P2-001→P2-003 (Guinevere Discord bot foundation)  
**Target Library**: discord.py 2.x (v2.3.2 stable)  
**Official Docs**: https://discordpy.readthedocs.io/en/stable/  
**Source Repo**: https://github.com/Rapptz/discord.py  

---

## Table of Contents

1. [Bot Subclass & `setup_hook`](#1-bot-subclass--setup_hook)
2. [Cog Architecture](#2-cog-architecture)
3. [Slash Commands via `app_commands`](#3-slash-commands-via-app_commands)
4. [Guild vs Global Sync Strategy](#4-guild-vs-global-sync-strategy)
5. [Extension Loading System](#5-extension-loading-system)
6. [Safe Startup Validation](#6-safe-startup-validation)
7. [Recommended Pattern for Guinevere](#7-recommended-pattern-for-guinevere)
8. [Source References](#8-source-references)

---

## 1. Bot Subclass & `setup_hook`

### Core Pattern

The canonical discord.py 2.x pattern is to **subclass `commands.Bot`** and override `setup_hook()`. This is where extensions are loaded, cogs are added, and slash commands are synced before the bot processes any events.

### Canonical Example (from discord.py docs)

```python
class CustomBot(commands.Bot):
    def __init__(
        self,
        *args,
        initial_extensions: list[str],
        testing_guild_id: int | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.testing_guild_id = testing_guild_id
        self.initial_extensions = initial_extensions

    async def setup_hook(self) -> None:
        # 1. Load extensions BEFORE sync so slash commands are registered
        for extension in self.initial_extensions:
            await self.load_extension(extension)

        # 2. Guild-specific sync (dev only)
        if self.testing_guild_id:
            guild = discord.Object(self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

        # 3. Database / runtime init
```

**Source**: [`examples/advanced_startup.py`](https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py)

### Key Rules

| Aspect | Rule |
|---|---|
| **`setup_hook` timing** | Runs after websocket connect but **before** `on_ready`. Safe to call `load_extension`, `add_cog`, `tree.sync`. |
| **Extension loading order** | Load extensions **first**, sync **after** — ensures all slash commands from cogs are registered in the tree before sync. |
| **`on_ready` vs `setup_hook`** | `on_ready` fires multiple times on reconnect; `setup_hook` fires **once** per session. Put one-time init in `setup_hook`. |
| **`tree` attribute** | `commands.Bot` already has `self.tree` (a `CommandTree`). No need to create one manually (only needed if subclassing `discord.Client`). |

### Real-World Example: RoboDanny

Rapptz's own production bot (`RoboDanny`) uses `setup_hook` for extension loading and guild sync:

**Source**: [`Rapptz/RoboDanny`](https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py)

---

## 2. Cog Architecture

### Basic Cog with Slash Commands

```python
import discord
from discord.ext import commands
from discord import app_commands


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Pong!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        pass  # cog-level event listeners need explicit decorator


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
```

**Sources**:
- [Official Cogs docs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html)
- [Python Discord guide](https://www.pythondiscord.com/pages/guides/python-guides/app-commands/)

### GroupCog — Command Group as a Cog

When all commands in a cog logically belong under one `/group` prefix:

```python
from discord import app_commands
from discord.ext import commands


@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
class Config(commands.GroupCog, group_name="config"):
    """Server configuration commands"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(key="Config key to set", value="Value to assign")
    async def set(
        self,
        interaction: discord.Interaction,
        key: str,
        value: str,
    ) -> None:
        await interaction.response.send_message(f"Set {key} = {value}")

    @app_commands.command()
    async def show(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Current config: ...")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Config(bot))
```

**Key details**:
- `GroupCog` doubles as both a `Cog` and an `app_commands.Group` — all `@app_commands.command()` inside become subcommands of `/config`.
- `group_name` in the class definition controls the slash command group name (defaults to kebab-case of class name).
- Decorators like `@app_commands.guild_only()` and `@app_commands.default_permissions()` at the class level apply to the whole group.
- Hybrid commands in a `GroupCog` are registered as root-level prefix commands but grouped under the group for slash commands.

**Sources**:
- [discord.py `GroupCog` source](https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/cog.py#L207-L254)
- [BallsDex](https://github.com/Ballsdex-Team/BallsDex-DiscordBot/blob/v3/ballsdex/packages/guildconfig/cog.py) (production: `Config(commands.GroupCog)`)
- [RoboDanny](https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/minigames/__init__.py) (production: `Minigame(commands.GroupCog)`)

### Manual `app_commands.Group` within a Cog

For cogs that need **multiple independent groups**:

```python
class MyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Define groups as class attributes
    uwu = app_commands.Group(name="uwu", description="Uwu commands")
    admin = app_commands.Group(name="admin", description="Admin commands")

    @app_commands.command(name="ping", description="Simple ping")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Pong!")

    @uwu.command(name="say", description="Uwu say")
    async def uwu_say(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(f"Uwu {text}")

    @admin.command(name="ban", description="Ban a user")
    async def admin_ban(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await interaction.response.send_message(f"Banned {user}")
```

Results in: `/ping`, `/uwu say`, `/admin ban`

**Source**: [Python Discord guide](https://www.pythondiscord.com/pages/guides/python-guides/app-commands/)

### Cog Special Methods

| Method | Purpose |
|---|---|
| `cog_load(self)` | Called after cog is registered. Async. Good for init that needs `self.bot`. |
| `cog_unload(self)` | Called when cog is removed. Async. Cleanup timers/sessions. |
| `cog_check(self, ctx)` | Global check for all prefix commands in this cog. |
| `cog_app_command_error(self, interaction, error)` | Error handler for app commands in this cog. |
| `cog_before_invoke(self, ctx)` / `cog_after_invoke(self, ctx)` | Pre/post hooks for prefix commands. |
| `cog_command_error(self, ctx, error)` | Error handler for prefix commands in this cog. |

### Cog Listener Registration

Listeners in cogs **must** be explicitly marked:

```python
class MyCog(commands.Cog):
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        ...

    @commands.Cog.listener("on_member_join")  # explicit event name
    async def greet(self, member: discord.Member) -> None:
        ...
```

**Sources**:
- [Official Cog docs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html#cog-registration)
- [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot/) (production: extensive Cog.listener usage)

---

## 3. Slash Commands via `app_commands`

### Parameter Descriptions

```python
@app_commands.command()
@app_commands.describe(
    user="The user to target",
    reason="Why this action is being taken",
)
@app_commands.rename(user="target-user")  # Discord-facing name differs from code
async def punish(
    self,
    interaction: discord.Interaction,
    user: discord.Member,
    reason: str = "No reason provided",  # default → optional parameter
) -> None:
    await interaction.response.send_message(f"Punished {user} for {reason}")
```

### Type Annotations & Converters

discord.py 2.x uses **type annotations** for automatic conversion:

```python
async def cmd(
    self,
    interaction: discord.Interaction,
    member: discord.Member,       # Auto-resolves mentions/IDs
    channel: discord.TextChannel,  # Auto-resolves channel references
    role: discord.Role,            # Auto-resolves role mentions/IDs
    count: int,                    # Integer parser
    name: str,                     # String
    optional: str | None = None,   # Optional via Union[..., None]
    number_range: app_commands.Range[int, 1, 100] = 50,  # Constrained int
) -> None: ...
```

### Choices & Autocomplete

```python
@app_commands.choices(color=[
    app_commands.Choice(name="Red", value="red"),
    app_commands.Choice(name="Blue", value="blue"),
    app_commands.Choice(name="Green", value="green"),
])
async def set_color(
    self,
    interaction: discord.Interaction,
    color: app_commands.Choice[str],
) -> None:
    await interaction.response.send_message(f"Color set to {color.value}")


# Dynamic autocomplete
@app_commands.autocomplete(query=autocomplete_fn)
async def search(
    self,
    interaction: discord.Interaction,
    query: str,
) -> None:
    ...

async def autocomplete_fn(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=item, value=item)
        for item in ["apple", "banana", "cherry"]
        if current.lower() in item.lower()
    ][:25]  # max 25 choices
```

### Permissions & Checks

```python
from discord import app_commands

@app_commands.checks.has_permissions(ban_members=True)
@app_commands.checks.bot_has_permissions(ban_members=True)
@app_commands.checks.cooldown(1, 30.0)  # 1 use per 30 seconds
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def ban(self, interaction: discord.Interaction, user: discord.Member) -> None:
    ...
```

### Error Handling

```python
# Option A: Tree-level error handler
@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"Cooldown: {error.retry_after:.1f}s", ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Missing perms", ephemeral=True)


# Option B: Cog-level error handler
class MyCog(commands.Cog):
    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        ...
```

**Sources**:
- [`discord/app_commands/commands.py`](https://github.com/Rapptz/discord.py/blob/master/discord/app_commands/commands.py)
- [Official `CommandTree.sync` docs](https://discordpy.readthedocs.io/en/latest/interactions/api.html)
- [Python Discord guide](https://www.pythondiscord.com/pages/guides/python-guides/app-commands/)

---

## 4. Guild vs Global Sync Strategy

### The Core Problem

- **Global sync**: Commands take **up to 1 hour** to propagate to all guilds via Discord's CDN cache.
- **Guild sync**: Commands appear **instantly** within the target guild.
- **Rate limits**: Global sync is rate-limited (~5-10 per 24h). Guild sync has higher limits.

### Best Practice: Two-Phase Sync

```python
class MyBot(commands.Bot):
    def __init__(self, dev_guild_id: int | None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.dev_guild_id = dev_guild_id

    async def setup_hook(self) -> None:
        # Phase 1: Load all extensions (registers commands in tree)
        for ext in self.initial_extensions:
            await self.load_extension(ext)

        # Phase 2: Dev guild sync (instant, for testing)
        if self.dev_guild_id:
            guild = discord.Object(self.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

        # DO NOT sync globally here — global sync is done manually
        # after command changes via a bot owner command
```

### Production Sync Command Pattern

From RoboDanny and other production bots, **sync is a bot-owner-only command**:

```python
@commands.command()
@commands.is_owner()
async def sync(self, ctx: commands.Context, guild_id: int | None = None) -> None:
    """Sync slash commands. Omit guild_id for global sync."""
    if guild_id:
        guild = discord.Object(id=guild_id)
        self.bot.tree.copy_global_to(guild=guild)
        synced = await self.bot.tree.sync(guild=guild)
        await ctx.send(f"Synced {len(synced)} commands to guild {guild_id}")
    else:
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally")
```

**Sources**:
- [RoboDanny admin sync command](https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py#L566-L580)
- [Python-Discord-Bot-Template owner sync](https://github.com/kkrypt0nn/Python-Discord-Bot-Template/blob/main/cogs/owner.py)
- [quotientbot sync command](https://github.com/quotientbot/quotient/blob/main/src/cogs/quomisc/dev.py)

### Sync Decision Matrix

| Scenario | Sync Strategy |
|---|---|
| **Development** | Guild-only sync via `setup_hook` with dev guild ID |
| **Adding new commands** | Guild sync to test, then global sync once |
| **Removing commands** | Guild `clear_commands` + `sync`, then global sync |
| **Production deploy** | Global sync via bot owner command only |
| **Bot joins new guild** | Guild auto-sync via `on_guild_join` event (optional) |

### Important: `copy_global_to` vs Direct Guild Commands

```python
# Pattern A: Copy global commands to guild for testing
guild = discord.Object(id=GUILD_ID)
self.tree.copy_global_to(guild=guild)
await self.tree.sync(guild=guild)
# → Guild shows ALL global commands instantly

# Pattern B: Guild-specific commands (only visible in that guild)
@app_commands.guilds(discord.Object(id=GUILD_ID))
@app_commands.command()
async def admin_only(self, interaction: discord.Interaction) -> None:
    ...
```

**Pattern A** is preferred for development/testing — you define commands globally during development but sync to a single guild for instant visibility.

---

## 5. Extension Loading System

### Structure

```
bot.py               # Bot subclass, main entry point
cogs/
  __init__.py
  general.py         # Extension with setup(bot) function
  moderation.py
  admin.py
```

### Extension File Pattern

Each extension file must expose an `async def setup(bot)`:

```python
# cogs/general.py
import discord
from discord.ext import commands
from discord import app_commands


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command()
    async def hello(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Hello!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))


# Optional: cleanup on unload
async def teardown(bot: commands.Bot) -> None:
    # Clean up timers, sessions, etc.
    pass
```

### Loading Extensions

```python
# In setup_hook:
await self.load_extension("cogs.general")
await self.load_extension("cogs.moderation")

# Or via bot command at runtime:
@commands.command()
@commands.is_owner()
async def load(ctx: commands.Context, ext: str) -> None:
    await ctx.bot.load_extension(f"cogs.{ext}")
    await ctx.send(f"Loaded {ext}")

@commands.command()
@commands.is_owner()
async def reload(ctx: commands.Context, ext: str) -> None:
    await ctx.bot.reload_extension(f"cogs.{ext}")
    await ctx.send(f"Reloaded {ext}")
```

### How Extension Loading Works Under the Hood

1. `bot.load_extension("cogs.general")` imports the module
2. Calls `module.setup(bot)` — the extension's entry point
3. Inside `setup()`, `bot.add_cog(MyCog(bot))` registers the cog
4. `add_cog` collects all `@app_commands.command()` and adds them to `bot.tree`
5. If the cog is a `GroupCog`, the group is also added to `bot.tree`

**Source**: [DeepWiki: Cogs and Extensions](https://deepwiki.com/Rapptz/discord.py/4.7-cogs-and-extensions)

### Atomic Reload

`bot.reload_extension()` performs atomic unload+reload with rollback:

- Backs up existing module state
- Attempts full unload → load cycle
- If loading fails, **restores previous working state** (not left partially-loaded)

---

## 6. Safe Startup Validation

Combined from real-world bots, these are the recommended startup validation steps:

### Pattern: Validate Intents & Permissions

```python
async def setup_hook(self) -> None:
    # 1. Validate required intents
    required_intents = {"message_content", "members"}
    missing = required_intents - set(
        name for name, value in self.intents if value
    )
    if missing:
        logger.warning(f"Missing recommended intents: {missing}")

    # 2. Load extensions
    for ext in self.initial_extensions:
        try:
            await self.load_extension(ext)
            logger.info(f"Loaded extension: {ext}")
        except commands.ExtensionFailed as e:
            logger.error(f"Failed to load {ext}: {e}")
            raise

    # 3. Verify tree has commands before sync
    commands_list = list(self.tree.walk_commands())
    if not commands_list:
        logger.warning("No application commands registered — tree is empty!")

    # 4. Dev guild sync
    if self.dev_guild_id:
        guild = discord.Object(self.dev_guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        logger.info(f"Synced {len(synced)} commands to dev guild")
```

### Pattern: Async Main Entry Point

For modern Python (3.11+), use `async def main()` with `asyncio.run()`:

```python
async def main() -> None:
    # logging setup
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        filename="discord.log", maxBytes=32 << 20, backupCount=5
    )
    logger.addHandler(handler)

    intents = discord.Intents.default()
    intents.message_content = True

    async with MyBot(
        command_prefix=commands.when_mentioned_or("!"),
        intents=intents,
        dev_guild_id=DEV_GUILD_ID,
        initial_extensions=["cogs.general", "cogs.moderation"],
    ) as bot:
        await bot.start(BOT_TOKEN)


asyncio.run(main())
```

**Source**: [`examples/advanced_startup.py`](https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py)

### Pattern: `on_ready` Validation (Non-Critical)

```python
async def on_ready(self) -> None:
    logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
    logger.info(f"Connected to {len(self.guilds)} guilds")
    logger.info(f"Loaded cogs: {list(self.cogs.keys())}")
    logger.info(f"Loaded extensions: {list(self.extensions.keys())}")
```

---

## 7. Recommended Pattern for Guinevere

Based on the research, this is the recommended pattern for Guinevere's `src/discord/` structure:

```
src/discord/
  bot.py              # Bot subclass with setup_hook, tree sync, validation
  config.py           # Config dataclass (token, intents, dev_guild_id, etc.)
  __init__.py         # Public API
  cogs/
    __init__.py       # Extension listing
    general.py        # General commands cog
    admin.py          # Admin/dev commands cog
    ...               # Future cogs
```

### Key Recommendations

| Decision | Recommendation | Rationale |
|---|---|---|
| **Bot class** | Subclass `commands.Bot` | Provides `self.tree`, `load_extension`, `add_cog` out of the box |
| **Init strategy** | `setup_hook` for all initialization | Once per session, before events fire |
| **Cog type** | `commands.Cog` + `app_commands.Group` per cog for simple; `GroupCog` for grouped commands | Flexibility + readability |
| **Sync strategy** | Guild-only sync in `setup_hook` for dev; manual global sync command for production | Avoid rate limits, instant dev feedback |
| **Extension loading** | `load_extension("cogs.general")` pattern in `setup_hook` | Hot-reloadable, clean module isolation |
| **Startup** | `async def main()` + `asyncio.run()` | Full control over lifecycle, logging, cleanup |
| **Error handling** | `@bot.tree.error` for global handler + `cog_app_command_error` per cog | Clean separation of concerns |
| **Logging** | Rotating file handler + `discord.utils.setup_logging()` | Production-grade, no log spam |

---

## 8. Source References

### Official Documentation

| Resource | URL |
|---|---|
| Cogs | https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html |
| Application Commands (API) | https://discordpy.readthedocs.io/en/latest/interactions/api.html |
| `Bot.add_cog` | https://discordpy.readthedocs.io/en/latest/ext/commands/api.html |
| Hybrid Commands | https://discordpy.readthedocs.io/en/stable/ext/commands/commands.html |
| FAQ: Restricting to Guilds | https://discordpy.readthedocs.io/en/latest/faq.html |

### Canonical Code Examples (discord.py Official)

| File | URL |
|---|---|
| `examples/advanced_startup.py` | https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py |
| `examples/app_commands/basic.py` | https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py |
| `examples/app_commands/transformers.py` | https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/transformers.py |
| `examples/modals/basic.py` | https://github.com/Rapptz/discord.py/blob/master/examples/modals/basic.py |
| `discord/ext/commands/cog.py` (GroupCog source) | https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/cog.py |
| `discord/app_commands/commands.py` | https://github.com/Rapptz/discord.py/blob/master/discord/app_commands/commands.py |
| `tests/test_ext_commands_cog.py` | https://github.com/Rapptz/discord.py/blob/master/tests/test_ext_commands_cog.py |
| `tests/test_app_commands_group.py` | https://github.com/Rapptz/discord.py/blob/master/tests/test_app_commands_group.py |

### Production Bot References

| Bot | Repository | Notable Patterns |
|---|---|---|
| **RoboDanny** (Rapptz) | https://github.com/Rapptz/RoboDanny | Bot owner sync commands, GroupCog usage, cog structure |
| **BallsDex** | https://github.com/Ballsdex-Team/BallsDex-DiscordBot | Guild-specific sync, GroupCog with permissions, app_commands checks |
| **Python-Discord-Bot-Template** | https://github.com/kkrypt0nn/Python-Discord-Bot-Template | Clean extension layout, sync/unslash commands, owner utilities |
| **quotient** | https://github.com/quotientbot/quotient | Multi-strategy sync (`~`, `*`, `^`), production-grade |
| **Valorant Bot** | https://github.com/staciax/valorant-discord-bot | app_commands with cooldowns, guild/global sync toggle |
| **Red-DiscordBot** | https://github.com/Cog-Creators/Red-DiscordBot | Extensive Cog.listener usage, 3rd-party cog ecosystem |

### Community Guides

| Guide | URL |
|---|---|
| Python Discord — App Commands Guide | https://www.pythondiscord.com/pages/guides/python-guides/app-commands/ |
| DeepWiki — Command Systems | https://deepwiki.com/Rapptz/discord.py/4-command-systems |
| DeepWiki — Cogs and Extensions | https://deepwiki.com/Rapptz/discord.py/4.7-cogs-and-extensions |
| discord.py Masterclass | https://fallendeity.github.io/discord.py-masterclass/cogs/ |
| AbstractUmbra's Gist | https://gist.github.com/AbstractUmbra/a9c188797ae194e592efe05fa129c57f |

---

*End of report. Prepared for Guinevere P2-001→P2-003 implementation.*
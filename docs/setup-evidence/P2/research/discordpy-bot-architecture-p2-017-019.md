# discord.py 2.x Bot Architecture — Flat Registration, Events, Startup, Shutdown

> **Target**: `bot.py` (P2-017) — flat command registration, no Cogs unless tradeoff documented.
> **Version**: discord.py ≥ 2.0 (latest stable: v2.6.2, June 2026)
> **Sources**: [Official docs](https://discordpy.readthedocs.io/en/v2.6.2/), [GitHub examples](https://github.com/Rapptz/discord.py/tree/master/examples), Context7 API
> **Date**: 2026-06-01

---

## Table of Contents

1. [Client vs. commands.Bot](#1-client-vs-commandsbot)
2. [commands.Bot Deep Dive](#2-commandsbot-deep-dive)
3. [Intents — What You Need and Why](#3-intents--what-you-need-and-why)
4. [Lifecycle: setup_hook → on_connect → on_ready](#4-lifecycle-setup_hook--on_connect--on_ready)
5. [Slash Command Registration with app_commands](#5-slash-command-registration-with-app_commands)
6. [Flat Command Registration Pattern](#6-flat-command-registration-pattern)
7. [on_message + process_commands](#7-on_message--process_commands)
8. [Presence and Startup Status](#8-presence-and-startup-status)
9. [Graceful Shutdown](#9-graceful-shutdown)
10. [Reconnect Behavior](#10-reconnect-behavior)
11. [Health-Check / State Tracking](#11-health-check--state-tracking)
12. [Pitfalls](#12-pitfalls)
13. [Cogs Tradeoff Note](#13-cogs-tradeoff-note)
14. [Canonical Flat Bot Skeleton](#14-canonical-flat-bot-skeleton)
15. [Source References](#15-source-references)

---

## 1. Client vs. commands.Bot

| Aspect | `discord.Client` | `commands.Bot` |
|--------|------------------|----------------|
| **Inherits** | `Client` | `Client` + `GroupMixin` |
| **Prefix handling** | Manual | Built-in (`command_prefix`) |
| **Text commands** | Must parse manually | `@bot.command()`, `process_commands()` |
| **Slash commands** | Manual `CommandTree` | Auto-creates `CommandTree` at `bot.tree` |
| **Help command** | Manual | Built-in (configurable) |
| **Check system** | Manual | `@bot.check()`, `@bot.check_once()` |
| **Cog support** | None | `add_cog()`, `@commands.Cog.listener()` |
| **Async context manager** | `async with client:` (v2.0+) | `async with bot:` (v2.0+) |

**Official docs** ([discord.ext.commands.Bot](https://discordpy.readthedocs.io/en/v2.6.2/ext/commands/api.html#discord.ext.commands.Bot)):

> *"This class is a subclass of `discord.Client` and as a result anything that you can do with a `discord.Client` you can do with this bot."*

> *"Unlike `discord.Client`, this class does not require manually setting a `CommandTree` and is automatically set upon instantiating the class."*

**Verdict**: For P2-017, **`commands.Bot` is the correct choice**. You get text commands (`@bot.command()`), slash/hybrid commands (`@bot.hybrid_command()`, `@bot.tree.command()`), prefix handling, and built-in help — all from one class. Using `discord.Client` would require manually wiring all of these.

---

## 2. commands.Bot Deep Dive

### Constructor Signature

```python
class commands.Bot(
    command_prefix,                         # str, list[str], callable, or when_mentioned
    *,
    help_command=<default-help-command>,
    tree_cls=<class 'discord.app_commands.CommandTree'>,
    description=None,
    allowed_contexts=...,
    allowed_installs=...,
    intents,                                # REQUIRED in v2.0+
    **options                               # forwarded to discord.Client
)
```

**Key parameters for flat bot**:

| Parameter | Value | Why |
|-----------|-------|-----|
| `command_prefix` | `"!"` or `commands.when_mentioned` | Text command trigger. `when_mentioned` is safest for hybrid-only bots to avoid accidental prefix matches. |
| `intents` | Required | See [§3 Intents](#3-intents--what-you-need-and-why) |
| `help_command` | `None` (or custom) | Disable default help if using only slash commands |
| `description` | `str` | Prefixed into default help message |

### Inherited from Client — Critical Properties

From the [API Reference](https://discordpy.readthedocs.io/en/v2.6.2/api.html#discord.Client):

- **`bot.user`** — `Optional[ClientUser]`: Connected client user. `None` before login.
- **`bot.latency`** — `float`: WebSocket heartbeat latency in seconds.
- **`bot.is_ready()`** — `bool`: Internal cache ready for use.
- **`bot.is_closed()`** — `bool`: WebSocket connection closed.
- **`bot.ws`** — The gateway connection or `None`.
- **`bot.guilds`** — Sequence of guilds the bot is member of.
- **`bot.application_id`** — Auto-populated after login.
- **`bot.application`** — `AppInfo` from login, `None` before login.

### `bot.tree` — The CommandTree

`commands.Bot` creates an internal `CommandTree` accessible at `bot.tree`. This is where all application (slash) commands live. You do **not** need to instantiate one manually.

From the docs ([CommandTree](https://discordpy.readthedocs.io/en/v2.6.2/interactions/api.html#discord.app_commands.CommandTree)):

> *"The CommandTree is responsible for running a translator to get translated strings for Discord. It must be called for application commands to appear."*

### AutoShardedBot

If sharding is needed, use `commands.AutoShardedBot` — same interface but handles multiple gateway connections automatically.

---

## 3. Intents — What You Need and Why

In v2.0, **`intents` is required**. From the [migration guide](https://discordpy.readthedocs.io/en/v2.6.2/migrating.html#intents-are-now-required):

> *"In order to better educate users on their intents and to also make it more explicit, this parameter is now required to pass in."*

### Intents Reference Table

| Intent | Privileged | Enables | Cache Impact |
|--------|-----------|---------|-------------|
| `guilds` | No | Guild create/update/delete, channel events | Guild/channel cache |
| `members` | **Yes** | Member join/leave/update, role changes | Member cache |
| `message_content` | **Yes** | `Message.content` for non-slash messages | None |
| `messages` | No | Message events (create, delete, edit) | Message cache (up to `max_messages`) |
| `presences` | **Yes** | `Member.status`, `Member.activity` | Presence cache |
| `reactions` | No | Reaction add/remove/clear events | None |
| `voice_states` | No | Voice state updates | Voice state cache |
| `typing` | No | Typing start events | None |

### Typical Flat Bot Intents

```python
intents = discord.Intents.default()       # guilds, messages, reactions, voice_states
intents.message_content = True            # REQUIRED for text command prefix matching
# intents.members = True                  # Only if tracking member join/leave/chunk
```

From the [intents primer](https://discordpy.readthedocs.io/en/v2.6.2/intents.html):

> *"If you want a bot that functions without spammy events like presences or typing then we could do..."*

```python
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
```

### `message_content` — Critical for Text Commands

If you use prefix-based commands (e.g., `!command`), you **must** enable `message_content` intent AND enable it in Discord Developer Portal. This is because Discord now restricts message content access by default.

> *"If you use the commands extension with a non-mentioning prefix"* → you need `message_content`.

### `chunk_guilds_at_startup`

If `members` intent is enabled, `on_ready` may be **significantly delayed** because guild member chunking happens 1 guild at a time (rate-limited to 120/60s). From the docs:

> *"Disable member chunking by setting `chunk_guilds_at_startup` to `False` when constructing a client."*

---

## 4. Lifecycle: setup_hook → on_connect → on_ready

The startup lifecycle in v2.0+ follows this exact order:

```
bot.run(token)
  │
  ├── asyncio.run(main()) or bot.run()
  │     │
  │     └── bot.login(token)
  │           │
  │           ├── Calls bot.setup_hook()          ← FIRST async setup point
  │           │                                    ← NO websocket yet!
  │           │                                    ← Safe for: loading extensions,
  │           │                                      registering views, tree.sync()
  │           │                                    ← DEADLOCK: wait_for(), wait_until_ready()
  │           │
  │           └── bot.connect(reconnect=True)
  │                 │
  │                 ├── WebSocket connects
  │                 ├── on_connect() fires          ← WS connected, cache NOT ready
  │                 ├── GUILD_CREATE stream (guild_ready_timeout=2s)
  │                 ├── Member chunking (if enabled)
  │                 └── on_ready() fires            ← Cache ready
  │                       │
  │                       └── Now safe: bot.user, bot.guilds, bot.latency, etc.
```

### `setup_hook()` — The Preferred Setup Point

From the [API reference](https://discordpy.readthedocs.io/en/v2.6.2/api.html#discord.Client.setup_hook):

> *"To perform asynchronous setup after the bot is logged in but before it has connected to the Websocket, overwrite this coroutine."*
>
> *"This is only called once, in `login()`, and will be called before any events are dispatched, making it a better solution than doing such setup in the `on_ready()` event."*

**⚠️ WARNING** (from docs):
> *"Since this is called before the websocket connection is made therefore anything that waits for the websocket will deadlock, this includes things like `wait_for()` and `wait_until_ready()`."*

**What to do in `setup_hook()`**:
- Register persistent views: `bot.add_view(view)`
- Register dynamic items: `bot.add_dynamic_items(Class)`
- Sync guild-specific commands: `await bot.tree.sync(guild=discord.Object(id))`
- Load extensions: `await bot.load_extension('module')`
- Start background tasks: `self.bg_task = self.loop.create_task(...)`

### `on_ready()` — Cache-Ready Notification

From the [event reference](https://discordpy.readthedocs.io/en/v2.6.2/api.html#discord.on_ready):

- Fires **once** when all guild data and member cache are ready.
- **Can fire multiple times** during reconnects (see [§10 Reconnect](#10-reconnect-behavior)).
- **`bot.user` is now populated** (was `None` before).
- **Do NOT** `tree.sync()` here every time — it's wasteful and triggers rate limits.

### `on_connect()` — WebSocket Connected

Fires when the WebSocket connects but **before** guild data is available. `bot.user` may still be `None` here.

### Lifecycle Event Sequence

```
on_connect()       → WS established
on_ready()         → Cache ready (may fire multiple times)
on_resumed()       → Session resumed after temporary disconnect (no full re-ready)
on_disconnect()    → WS disconnected
```

---

## 5. Slash Command Registration with app_commands

### Three Registration Styles

discord.py v2.x offers three ways to register slash (application) commands:

#### A. `@bot.tree.command()` — Native app_command (RECOMMENDED for flat)

```python
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")
```

- Uses `discord.Interaction` (not `commands.Context`).
- Must call `interaction.response.send_message()` or `interaction.response.defer()`.
- Registered to `bot.tree` automatically.

#### B. `@bot.hybrid_command()` — Dual text + slash

```python
@bot.hybrid_command(name="ping", description="Check bot latency")
async def ping(ctx: commands.Context):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")
```

- Works as both text command (`!ping`) and slash command (`/ping`).
- Context `ctx.interaction` gives you the `discord.Interaction` if invoked as slash.
- `ctx.send()` auto-detects whether to use interaction response or text channel.
- **Still requires `tree.sync()`** for the slash portion to appear.

From the [Context7 docs](https://discordpy.readthedocs.io/en/v2.6.2/ext/commands/commands.html):

> *"The `Context` class has been modified for convenience: `Context.interaction` retrieves the slash command interaction, `Context.send()` automatically handles interaction responses or follow-ups, and `Context.defer()` defers interaction responses for slash commands while showing a typing indicator for text commands."*

#### C. `@discord.app_commands.command()` — Standalone (requires manual add)

```python
@discord.app_commands.command()
async def ping(interaction: discord.Interaction):
    ...
```

- Must be manually added: `bot.tree.add_command(ping)`
- Less ergonomic for flat modules.

### Guild vs. Global Scope

**Global** commands (no guild parameter):
- Propagate to all guilds.
- Take up to **1 hour** to update for global commands (Discord cache).
- `await bot.tree.sync()` — syncs all global commands.

**Guild** commands (with `guild=` parameter):
- Update **instantly** within the specified guild.
- Ideal for development/testing.
- `await bot.tree.sync(guild=discord.Object(id=GUILD_ID))`

From [CommandTree.sync](https://discordpy.readthedocs.io/en/v2.6.2/interactions/api.html#discord.app_commands.CommandTree.sync):

> *"If `None` then it syncs all global commands instead."*

### The Development Sync Pattern

From the [official `advanced_startup.py`](https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py) (lines 41-50):

```python
async def setup_hook(self) -> None:
    for extension in self.initial_extensions:
        await self.load_extension(extension)

    if self.testing_guild_id:
        guild = discord.Object(self.testing_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
```

This pattern:
1. Loads extensions first (so all commands are registered).
2. Copies global commands to a testing guild.
3. Syncs **only** that guild.

**DO NOT sync globally on every startup** — rate limits apply and it delays startup.

### `copy_global_to()` Method

From the [API docs](https://discordpy.readthedocs.io/en/v2.6.2/interactions/api.html#discord.app_commands.CommandTree.copy_global_to):

> *"Copies all global commands to the specified guild. This method is mainly available for development purposes, as it allows you to copy your global commands over to a testing guild easily."*
>
> *"This method will override pre-existing guild commands that would conflict."*

---

## 6. Flat Command Registration Pattern

For a flat module structure (no Cogs), use the `@bot.tree.command()` decorator in each module file. Import the `bot` singleton and decorate directly.

### How to Organize Flat Commands

```
src/discord/
  bot.py           ← instantiates Bot, calls loaders
  commands/
    __init__.py    ← imports all command modules
    ping.py        ← @bot.tree.command()
    config.py      ← @bot.tree.command()
```

### Module Pattern

```python
# src/discord/commands/ping.py
import discord
from discord.ext import commands

from src.discord.bot import bot  # singleton import

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Pong! {round(bot.latency * 1000)}ms"
    )
```

### Registration Strategy

1. Each module imports `bot` from `bot.py`.
2. Decorating with `@bot.tree.command()` **immediately registers** the command in `bot.tree`.
3. No manual `add_command()` needed for the tree.
4. **BUT**: You must ensure modules are imported (executed) before `bot.run()` or `bot.start()` — otherwise decorators never fire.

### Dynamic Import Strategy

```python
# src/discord/commands/__init__.py
import importlib
import pkgutil

__all__ = []
for module_info in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{module_info.name}")
    if hasattr(module, "__all__"):
        __all__.extend(module.__all__)
```

Then in `bot.py`:

```python
from src.discord.commands import *   # triggers all decorators
```

**Caveat**: The dynamic import must run **before** `bot.run()` otherwise the commands won't exist when the tree syncs. Import at module level, not inside an async function.

---

## 7. on_message + process_commands

### Why You Need It

When using `commands.Bot`, the framework automatically handles messages that **start with the prefix**. However, if you override `on_message`, you **must manually call `process_commands()`** or prefix commands will silently stop working.

### The Pattern

```python
@bot.event
async def on_message(message: discord.Message):
    # Custom logic (optional)
    if message.author.bot:
        return

    # This MUST be called for prefix commands to work
    await bot.process_commands(message)
```

From the [commands API reference](https://discordpy.readthedocs.io/en/v2.6.2/ext/commands/api.html#discord.ext.commands.Bot.process_commands):

> *"This function processes the commands that have been registered to the bot and other groups."*

### When It's Safe to Skip

If you are **not** using `@bot.event` for `on_message` at all, the built-in handler runs automatically. Only override if you need custom logic.

### Hybrid Commands and on_message

Hybrid commands (`@bot.hybrid_command()`) work via both text (through `process_commands`) and slash (through the interaction system). They do **not** require `on_message` to function for the slash path.

### Interaction vs Message Context

- **Slash commands** → receive `discord.Interaction`
- **Text commands** → receive `commands.Context` (wraps `discord.Message`)
- **Hybrid commands** → receive `commands.Context` + `ctx.interaction` when invoked as slash

### Full on_message Pattern for Flat Bot

```python
@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.invoke(ctx)
    # else: not a command, ignore silently
```

Or simply:

```python
@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    await bot.process_commands(message)
```

---

## 8. Presence and Startup Status

### Setting Initial Presence

Pass `status` and `activity` to the Bot constructor:

```python
bot = commands.Bot(
    command_prefix=commands.when_mentioned,
    intents=intents,
    status=discord.Status.online,
    activity=discord.Game(name="with Guinevere"),
)
```

From [Client constructor](https://discordpy.readthedocs.io/en/v2.6.2/api.html#discord.Client):

> *"A status to start your presence with upon logging on to Discord."*

### Changing Presence at Runtime

```python
await bot.change_presence(
    activity=discord.Game(name="Managing servers"),
    status=discord.Status.idle,
)
```

From the docs:

> *"Changed in version 2.0: Removed the `afk` keyword-only parameter."*

### Guild Count in Status

A common pattern:

```python
@bot.event
async def on_ready() -> None:
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servers"
        )
    )
```

---

## 9. Graceful Shutdown

### The `async with` Pattern (v2.0+)

The cleanest shutdown in v2.0+ uses the async context manager:

```python
async def main():
    async with bot:                              # auto-cleanup on exit
        await bot.start(token)

asyncio.run(main())
```

From the [docs](https://discordpy.readthedocs.io/en/v2.6.2/migrating.html#asyncio-event-loop-changes):

> *"`async with client:` — Asynchronously initialises the client and automatically cleans up."*

### Manual Shutdown via `close()`

```python
await bot.close()   # Closes WebSocket, cleans up HTTP session
```

### Overriding `close()` for Custom Cleanup

From the [GitHub examples](https://github.com/Rapptz/discord.py/blob/master/examples/views/embed_like.py) (lines 14-17):

```python
async def setup_hook(self) -> None:
    self.session = aiohttp.ClientSession()

async def close(self) -> None:
    await self.session.close()     # custom cleanup first
    await super().close()          # then parent close()
```

### Shutdown Sequence

```
bot.close()
  │
  ├── WebSocket disconnect (opcode 1000)
  ├── HTTP session close
  ├── Cancel background tasks
  └── Clear internal cache
```

### Signal Handling for Graceful Shutdown

```python
import signal

async def shutdown(sig: signal.Signals, loop: asyncio.AbstractEventLoop) -> None:
    logger.info(f"Received {sig.name}, shutting down...")
    await bot.close()
    loop.stop()

loop = asyncio.get_event_loop()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))
```

**Note**: On Windows, `loop.add_signal_handler` is not available. Use `try/except` or handle via `bot.run()` interruption.

---

## 10. Reconnect Behavior

### Automatic Reconnect

By default, `reconnect=True` in both `run()` and `start()`. From the [docs](https://discordpy.readthedocs.io/en/v2.6.2/api.html#discord.Client.connect):

> *"If we should attempt reconnecting, either due to internet failure or a specific failure on Discord's part. Certain disconnects that lead to bad state will not be handled (such as invalid sharding payloads or bad tokens)."*

### Reconnect Lifecycle

```
[WebSocket drops]
    │
    ├── on_disconnect() fires
    │
    ├── Reconnect attempt (exponential backoff)
    │     │
    │     ├── Success → on_resumed() fires (session RESUME, not full re-ready)
    │     │              OR
    │     │              on_connect() + on_ready() fires (new session, if RESUME fails)
    │     │
    │     └── Failure → retry (up to indefinite)
    │
    └── If reconnect=False → bot.close()
```

### `on_resumed()` vs. `on_ready()`

- **`on_resumed()`** — Fires when the session was successfully **resumed** (no data loss, no cache rebuild).
- **`on_ready()`** — Fires after a **new session** is established (cache may have been rebuilt).

**Critical**: Because `on_ready()` can fire multiple times, avoid singleton initialization there. Use `setup_hook()` for one-time setup.

### `before_identify_hook`

From the [docs](https://discordpy.readthedocs.io/en/v2.6.2/api.html#discord.Client.before_identify_hook):

> *"A hook that is called before IDENTIFYing a session. The default implementation sleeps for 5 seconds."*

Override to add custom backoff logic for reconnects:

```python
async def before_identify_hook(self, shard_id: int, *, initial: bool = False) -> None:
    if not initial:
        await asyncio.sleep(10)  # longer backoff for reconnects
```

### Rate Limit on Reconnects

Discord's gateway rate limit: 1 IDENTIFY per 5 seconds per shard. The default `before_identify_hook` handles this.

### `heartbeat_timeout`

Default: 60 seconds. Increase if the bot might have slow event processing:

```python
bot = commands.Bot(..., heartbeat_timeout=120.0)
```

---

## 11. Health-Check / State Tracking

### Built-in State Methods

| Method | Returns | Meaning |
|--------|---------|---------|
| `bot.is_ready()` | `bool` | Internal cache is fully ready |
| `bot.is_closed()` | `bool` | WebSocket is closed |
| `bot.latency` | `float` | WS heartbeat latency in seconds |
| `bot.ws` | `WebSocketShard or None` | Active gateway connection |
| `bot.is_ws_ratelimited()` | `bool` | Gateway currently rate limited |

### Custom Health-Check Attributes

For the flat bot pattern, add state tracking to the Bot subclass:

```python
class GuinevereBot(commands.Bot):
    def __init__(self, ...):
        super().__init__(...)
        self.ready_once = False
        self.connected_at: datetime | None = None
        self.disconnect_count = 0
        self.last_disconnect_at: datetime | None = None
        self.command_count = 0

    async def on_ready(self) -> None:
        if not self.ready_once:
            self.ready_once = True
            self.connected_at = discord.utils.utcnow()
        # else: reconnected
```

### Exposing Health via Command

```python
@bot.tree.command(name="health", description="Check bot health")
async def health(interaction: discord.Interaction):
    state = "connected" if bot.is_ready() else "disconnected"
    await interaction.response.send_message(
        f"State: {state}\n"
        f"Latency: {round(bot.latency * 1000)}ms\n"
        f"Guilds: {len(bot.guilds)}\n"
        f"Uptime: ..."
    )
```

---

## 12. Pitfalls

### P1: Multiple `on_ready` → Duplicate Startup Messages

`on_ready` can fire multiple times during reconnects. If you send a startup notification there, guard with a flag:

```python
@bot.event
async def on_ready() -> None:
    if not bot.ready_once:
        bot.ready_once = True
        channel = bot.get_channel(STARTUP_CHANNEL_ID)
        await channel.send("Bot is online!")
```

### P2: Duplicate `tree.sync()` Calls

Calling `tree.sync()` on every startup or in every `on_ready`:
- Hits Discord rate limits (200 global syncs/day).
- Slows down startup.
- Can cause "unknown interaction" errors if commands change while users are typing.

**Fix**: Sync only in `setup_hook()` and only for the testing guild during development.

### P3: `InteractionResponded` Exception

From the [API reference](https://discordpy.readthedocs.io/en/v2.6.2/api.html#discord.InteractionResponded):

> *"Exception that's raised when sending another interaction response using `InteractionResponse` when one has already been done before. An interaction can only respond once."*

**Fix**: Use `interaction.response.is_done()` to check before responding, or always use `interaction.followup.send()` after the first response.

```python
if not interaction.response.is_done():
    await interaction.response.send_message(...)
else:
    await interaction.followup.send(...)
```

### P4: Blocking the Event Loop

From the [FAQ](https://discordpy.readthedocs.io/en/v2.6.2/faq.html#avoid-blocking-use-asyncio-sleep-instead-of-time-sleep):

```python
# BAD — blocks the entire bot
time.sleep(10)

# GOOD — yields control to event loop
await asyncio.sleep(10)
```

Any blocking call (`time.sleep()`, `requests.get()`, CPU-bound computation) **freezes all bot operations** — message handling, heartbeats, command processing.

**Fix**:
- Use `asyncio.sleep()` instead of `time.sleep()`.
- Use `aiohttp` instead of `requests`.
- Offload CPU work to `loop.run_in_executor()`.

### P5: Deadlock in `setup_hook()`

From the [docs](https://discordpy.readthedocs.io/en/v2.6.2/api.html#discord.Client.setup_hook):

> *"Since this is called before the websocket connection is made therefore anything that waits for the websocket will deadlock, this includes things like `wait_for()` and `wait_until_ready()`."*

**Fix**: Never call `bot.wait_for()`, `bot.wait_until_ready()`, or any WebSocket-dependent operation inside `setup_hook()`.

### P6: Missing `message_content` Intent

If `message_content` is not enabled, `Message.content` will be empty for non-slash messages. This breaks:
- Text command prefix matching.
- `on_message` message content inspection.

**Fix**: Enable in code AND in Discord Developer Portal.

### P7: `process_commands` Not Called After Overriding `on_message`

If you define `@bot.event async def on_message(...)`, the built-in `process_commands` call is **disabled**. You must call it manually.

### P8: Global Sync Rate Limits

Discord imposes rate limits on global command syncs. From the docs:

> *"Syncing the commands failed due to a user related error"* → `CommandSyncFailure`

**Best practice**: Sync globally only when commands actually change. During development, use guild-scoped sync.

### P9: Forgetting `@bot.event` Decorator

If you define a method `async def on_ready(self)` on a Bot subclass (not using decorator), it works automatically. But if using flat functions outside the class:

```python
# WORKS — registered as event
@bot.event
async def on_ready():
    ...

# DOES NOT WORK — not registered
async def on_ready():
    ...
bot.on_ready = on_ready  # NOT how to do it
```

### P10: Not Using `async with bot` for Clean Shutdown

Without the async context manager, background tasks may not be properly cancelled on exit. Always use:

```python
async def main():
    async with bot:
        await bot.start(token)
```

---

## 13. Cogs Tradeoff Note

> *Per MUST NOT DO: Do not recommend Cog if local project pattern argues flat registration unless you document tradeoff.*

### When Flat Registration Wins

- **Dynamic imports**: Importing a module triggers `@bot.tree.command()` immediately. No Cog registration needed.
- **Simplicity**: One decorator, no Cog class, no `setup()` function.
- **Testability**: Each command module can be tested independently.
- **Current project pattern**: Uses flat modules + dynamic import helpers. Switching to Cogs would require restructuring.

### When Cogs Would Be Better

| Concern | Flat | Cog |
|---------|------|-----|
| Shared state | Store on `bot` instance | Store on `self` in Cog |
| Group commands | Manual grouping | `@commands.Cog.listener()` + `GroupCog` |
| Lifecycle hooks | `on_ready()` per module | `cog_load()`, `cog_unload()` |
| Namespace isolation | No isolation | Cog name prefix |
| Reload during runtime | Hard (need re-import) | `bot.reload_extension()` built-in |

### Verdict for P2-017

The flat pattern is **viable** for this project's structure. The dynamic import helper ensures all command modules are loaded. Use `bot` instance attributes (e.g., `bot.db_pool`, `bot.session`) for shared state instead of Cog instance attributes. If the command surface grows beyond ~20 commands or needs group namespacing, consider migrating to Cogs.

---

## 14. Canonical Flat Bot Skeleton

Synthesized from official docs, examples, and best practices:

```python
"""src/discord/bot.py — Flat-registration Bot singleton."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class GuinevereBot(commands.Bot):
    """Flat-registration Bot with health tracking."""

    def __init__(
        self,
        testing_guild_id: Optional[int] = None,
        **options,
    ) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # required for prefix commands

        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            status=discord.Status.online,
            activity=discord.Game(name="Initializing..."),
            **options,
        )

        # Health tracking
        self.ready_once: bool = False
        self.connected_at: Optional[datetime] = None
        self.disconnect_count: int = 0
        self._testing_guild_id = testing_guild_id

    async def setup_hook(self) -> None:
        """Called once after login, before websocket connects."""
        # Register persistent views
        # self.add_view(MyPersistentView())

        # Sync guild-scoped commands for development
        if self._testing_guild_id:
            guild = discord.Object(self._testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

        # Start background tasks
        # self.bg_task = self.loop.create_task(self._my_task())

    async def on_ready(self) -> None:
        """Cache-ready notification. Can fire multiple times."""
        if not self.ready_once:
            self.ready_once = True
            self.connected_at = discord.utils.utcnow()
            logger.info(
                "Bot ready — user=%s guilds=%d latency=%.0fms",
                self.user, len(self.guilds), self.latency * 1000,
            )
            await self.change_presence(
                activity=discord.Game(name=f"{len(self.guilds)} servers")
            )
        else:
            logger.info("Reconnected — guilds=%d", len(self.guilds))

    async def on_message(self, message: discord.Message) -> None:
        """Route messages to command processing."""
        if message.author.bot:
            return
        await self.process_commands(message)

    async def close(self) -> None:
        """Graceful shutdown with custom cleanup."""
        # Add custom cleanup here (DB pools, sessions, etc.)
        logger.info("Bot shutting down...")
        await super().close()


# Singleton — imported by command modules for @bot.tree.command()
bot: GuinevereBot = None  # type: ignore[assignment]


def create_bot(
    token: str,
    testing_guild_id: Optional[int] = None,
) -> GuinevereBot:
    """Factory: instantiate bot, import command modules, run."""
    global bot

    # Import all command modules BEFORE run() to trigger decorators
    from src.discord.commands import (  # noqa: F401
        ping,
        config,
    )

    bot = GuinevereBot(testing_guild_id=testing_guild_id)

    async def main() -> None:
        async with bot:
            await bot.start(token)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt.")
    return bot
```

---

## 15. Source References

| Source | URL | Accessed |
|--------|-----|----------|
| Official docs (v2.6.2) | https://discordpy.readthedocs.io/en/v2.6.2/ | 2026-06-01 |
| API Reference — Client | https://discordpy.readthedocs.io/en/v2.6.2/api.html | 2026-06-01 |
| commands.Bot API | https://discordpy.readthedocs.io/en/v2.6.2/ext/commands/api.html | 2026-06-01 |
| Intents Primer | https://discordpy.readthedocs.io/en/v2.6.2/intents.html | 2026-06-01 |
| Migrating to v2.0 | https://discordpy.readthedocs.io/en/v2.6.2/migrating.html | 2026-06-01 |
| app_commands.CommandTree | https://discordpy.readthedocs.io/en/v2.6.2/interactions/api.html | 2026-06-01 |
| GitHub — advanced_startup.py | https://github.com/Rapptz/discord.py/blob/master/examples/advanced_startup.py | 2026-06-01 |
| GitHub — background_task.py | https://github.com/Rapptz/discord.py/blob/master/examples/background_task.py | 2026-06-01 |
| GitHub — embed_like.py (close pattern) | https://github.com/Rapptz/discord.py/blob/master/examples/views/embed_like.py | 2026-06-01 |
| GitHub — modals/basic.py (sync pattern) | https://github.com/Rapptz/discord.py/blob/master/examples/modals/basic.py | 2026-06-01 |
| Context7 — discord.py library | `/websites/discordpy_readthedocs_io_en` | 2026-06-01 |
| Context7 — Rapptz/discord.py | `/rapptz/discord.py` | 2026-06-01 |
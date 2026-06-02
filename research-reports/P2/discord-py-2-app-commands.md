# Research Report: discord.py 2.x Application Commands Setup

**Date**: 2026-06-01
**Scope**: Guinevere P2-001 (application verification) / P2-003 (intents verification)
**Target**: Discord app ID `1510873134981582858`

---

## 1. Sources

| Source | URL |
|---|---|
| Official docs (stable) | https://discordpy.readthedocs.io/en/stable/ |
| App Commands API Reference | https://discordpy.readthedocs.io/en/stable/interactions/api.html |
| CommandTree class source | https://github.com/Rapptz/discord.py/blob/master/discord/app_commands/tree.py |
| Official example (basic.py) | https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py |
| Official example (hybrid commands) | https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/hybrid.py |
| Migration guide v1→v2 | https://discordpy.readthedocs.io/en/stable/migrating.html |
| Quickstart | https://discordpy.readthedocs.io/en/stable/quickstart.html |
| Context7 docs (discord.py) | `/websites/discordpy_readthedocs_io_en` |

---

## 2. Architecture Overview — How Slash Commands Work in discord.py 2.x

discord.py 2.x+ (`>=2.0, <3.0`) uses a **CommandTree** pattern. Key concepts:

- **`CommandTree`**: Container that holds all application commands (slash + context menu). Attached to a `discord.Client` or `commands.Bot`.
- **`app_commands.Command`**: Represents a single slash command (created via decorators).
- **`app_commands.ContextMenu`**: Right-click menu commands (on users or messages).
- **`app_commands.Group`**: Groups of subcommands.
- **`sync()`**: Pushes local command registrations to Discord API. **Must be called for commands to appear.**

### Two Init Approaches

**Approach A: `discord.Client` subclass (manual)**
```python
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)  # Manual tree creation

    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
```

**Approach B: `commands.Bot` (auto tree)**
```python
bot = commands.Bot(command_prefix='!', intents=intents)
# bot.tree is auto-created — no manual CommandTree() needed
```

**For Guinevere**: Either approach works. If using `commands.Bot` for prefix fallback, `bot.tree` is ready. If using `discord.Client` directly, manually create `self.tree = app_commands.CommandTree(self)`.

---

## 3. Application ID — How It's Used & Auto-Discovery

### Source of Truth

The `application_id` is auto-discovered by discord.py during login via Discord API's gateway `READY` payload. The library stores it in two places:

1. `client.application_id` (the public accessor)
2. `client._connection.application_id` (internal state)

### Resolution Flow

```
Client.start(token)
  → HTTP login → receives bot user data
  → Gateway READY event → receives application_id
  → Sets: client._connection.application_id
  → Sets: client.application_id (property)
```

**You do NOT need to explicitly set `application_id`**. discord.py fetches it automatically from Discord during `client.run()` / `client.start()`. The `sync()` call will check `self.client.application_id is None` before proceeding and raise `MissingApplicationID` if not yet available.

### `MissingApplicationID` — When It Happens

Raised when `application_id` is `None` — typically because `sync()` was called **before** `on_ready` fired. The gateway `READY` payload hasn't arrived yet.

### P2-001 Implication

For **P2-001** (verifying the application), you can either:
- Wait for `on_ready` and read `client.application_id` (it will be `1510873134981582858`)
- OR explicitly pass `application_id` to the `Client` constructor to skip auto-discovery:
  ```python
  client = discord.Client(intents=intents, application_id=1510873134981582858)
  ```
  This parameter was added in discord.py 2.4. Verify the installed version first.

---

## 4. Command Registration & Decorators

### Basic Slash Command

```python
@client.tree.command()
@app_commands.describe(
    query='The search query',
    limit='Max results to return',
)
async def search(interaction: discord.Interaction, query: str, limit: int = 10):
    """Search for something."""
    await interaction.response.send_message(f'Searching for {query}...')
```

### Guild-Specific (Instant Update)

```python
MY_GUILD = discord.Object(id=123456789)

@client.tree.command(guild=MY_GUILD)
async def ping(interaction: discord.Interaction):
    """Pong!"""
    await interaction.response.send_message('Pong!')
```

**Why guild-specific**: Global commands take up to 1 hour to propagate. Guild commands propagate instantly — essential for development/testing.

### Context Menu Commands

```python
@client.tree.context_menu(name='Show Join Date')
async def show_join_date(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(
        f'{member} joined at {discord.utils.format_dt(member.joined_at)}'
    )

@client.tree.context_menu(name='Report Message')
async def report_message(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message(
        'Thanks for reporting!', ephemeral=True
    )
```

### Hybrid Commands (with commands.Bot)

```python
@bot.hybrid_command()
async def ping(ctx):
    """Works as both !ping and /ping"""
    await ctx.send('Pong!')
```

---

## 5. Sync Behavior — Critical Details

### `tree.sync()` Flow

```python
async def sync(self, *, guild: Optional[Snowflake] = None) -> List[AppCommand]:
```

From source (`discord/app_commands/tree.py`):

1. Checks `self.client.application_id is None` → raises `MissingApplicationID` if so
2. Runs translations (if translator is set)
3. If `guild` is provided → calls `self._http.bulk_upsert_guild_commands(application_id, guild.id, payload)`
4. If `guild` is None → calls `self._http.bulk_upsert_global_commands(application_id, payload)`
5. Returns `List[AppCommand]` of synced commands

### Sync Timing Strategies

| Strategy | Pros | Cons | Best For |
|---|---|---|---|
| **Guild-only sync in `setup_hook`** | Instant updates, no 1h delay | Only works in one guild | Development |
| **Global sync in `on_ready`** | Commands visible everywhere | 1h propagation delay | Production |
| **`copy_global_to(guild) + sync(guild)`** | Dev copies global to guild | Extra step | Hybrid dev/prod |
| **No sync** | No API calls | Commands never register | Testing only |

### Official Recommended Pattern (basic.py)

```python
class MyClient(discord.Client):
    async def setup_hook(self):
        # Copies all global commands to the guild for instant access
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
```

This avoids the 1-hour global propagation delay during development by:
1. Keeping commands defined as global (no guild= on decorators)
2. Copying them to a specific guild in `setup_hook`
3. Syncing only that guild

### ⚠️ GOTCHA: `setup_hook` vs `on_ready` timing

- `setup_hook()` runs **after login but before gateway connects** — `application_id` IS available (from HTTP login)
- `on_ready()` runs **after gateway READY** — `application_id` also available
- **Safe to sync in either**, but `setup_hook` is the canonical place

---

## 6. Intents — What P2-003 Needs

### Required Intents Change for v2.x

In discord.py 2.0+, **intents are mandatory** (no longer optional):

```python
# v1.x — would work
client = discord.Client()

# v2.x — REQUIRED
intents = discord.Intents.default()
client = discord.Client(intents=intents)
```

### Minimum Intents for App Commands

For slash commands to work, you need **at minimum**:

```python
intents = discord.Intents.default()
```

`discord.Intents.default()` enables:
- `guilds` ✓
- `members` ✓ (for user info in interactions)
- `message_content` **NOT** included (not needed for slash commands)

### Intents for Guinevere (based on P2-003 scope)

| Intent | Needed For | P2-003 Verify |
|---|---|---|
| `guilds` | Guild info, channel list | ✅ Verify set |
| `members` | Member info in interactions | ✅ Verify set |
| `message_content` | Prefix commands (if used) | ❌ Not required for slash alone |
| `presences` | Presence data | ❌ Not needed |
| `voice_states` | Voice channel info | ❌ Not needed |

### Verifying Intents Programmatically

```python
intents = discord.Intents.default()
print(f'guilds: {intents.guilds}')
print(f'members: {intents.members}')
print(f'message_content: {intents.message_content}')
```

---

## 7. Recommended Implementation Pattern for Guinevere

Based on all research, this is the recommended pattern for P2-001→P2-003:

```python
import discord
from discord import app_commands

# ── Guinevere App Configuration ──
GUINEVERE_APP_ID = 1510873134981582858
DEV_GUILD_ID = discord.Object(id=... )  # Replace with your dev guild

class GuinevereClient(discord.Client):
    """Guinevere's Discord client — app commands setup."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # Required for member-aware interactions
        
        # Optional: pre-set application_id (discord.py >= 2.4)
        # super().__init__(intents=intents, application_id=GUINEVERE_APP_ID)
        super().__init__(intents=intents)
        
        # Attach command tree
        self.tree = app_commands.CommandTree(self)
    
    async def setup_hook(self):
        """Called after login, before gateway connect — safe for sync."""
        # P2-001: Verify application_id is resolved
        app_id = self.application_id  # or self.user.id
        if app_id != GUINEVERE_APP_ID:
            _log.warning(f'Expected app_id {GUINEVERE_APP_ID}, got {app_id}')
        
        # P2-003: Verify intents
        assert self.intents.guilds, 'guilds intent required'
        assert self.intents.members, 'members intent required'
        
        # Copy global commands to dev guild for instant availability
        self.tree.copy_global_to(guild=DEV_GUILD_ID)
        await self.tree.sync(guild=DEV_GUILD_ID)
    
    async def on_ready(self):
        _log.info(f'Guinevere ready: {self.user} (ID: {self.user.id})')
        # Application ID is now resolved and usable
        _log.info(f'Application ID: {self.application_id}')

# Register commands
guinevere = GuinevereClient()

@guinevere.tree.command()
async def ping(interaction: discord.Interaction):
    """Check bot latency."""
    await interaction.response.send_message(
        f'Pong! {round(guinevere.latency * 1000)}ms',
        ephemeral=True
    )

guinevere.run('YOUR_BOT_TOKEN')
```

### Using `commands.Bot` instead (alternative)

```python
from discord.ext import commands

bot = commands.Bot(
    command_prefix='!',
    intents=discord.Intents.default(),
    application_id=GUINEVERE_APP_ID,  # discord.py >= 2.4
)

@bot.event
async def on_ready():
    print(f'Ready: {bot.user} (app_id: {bot.application_id})')

@bot.hybrid_command()
async def ping(ctx):
    await ctx.send('Pong!')

bot.run('YOUR_BOT_TOKEN')
```

---

## 8. Gotchas & Pitfalls

### 🚩 1. `MissingApplicationID` on sync if called too early
```python
# ❌ WRONG — sync before READY
await self.tree.sync()  # MissingApplicationID

# ✅ RIGHT — sync in setup_hook or on_ready
async def setup_hook(self):
    await self.tree.sync(guild=DEV_GUILD)
```

### 🚩 2. Global commands take up to 1 hour
```python
# ❌ You add a command, sync globally, wait... nothing
await self.tree.sync()  # global — 1h propagation

# ✅ Use guild sync for instant feedback
await self.tree.sync(guild=MY_GUILD)
```

### 🚩 3. `copy_global_to` duplicates — does NOT auto-sync
```python
# ❌ This does nothing visible
self.tree.copy_global_to(guild=MY_GUILD)
# You forgot sync()!

# ✅ Must follow with sync
self.tree.copy_global_to(guild=MY_GUILD)
await self.tree.sync(guild=MY_GUILD)
```

### 🚩 4. Guild+contexts limitation
```python
# ❌ ERROR: Cannot mix guild with contexts/install types
@client.tree.command(guild=MY_GUILD)
@app_commands.allowed_contexts(guild=True)
async def cmd(...): ...

# ✅ Either remove guild, or remove contexts
```

### 🚩 5. `Interaction.response` must be called once
```python
# ❌ No response → interaction times out after 3s
async def cmd(interaction: discord.Interaction):
    await asyncio.sleep(5)
    # Too late! Discord already shows "interaction failed"

# ✅ Use deferred response for slow ops
async def cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    result = await slow_operation()
    await interaction.followup.send(result)
```

### 🚩 6. `ephemeral` flag only on initial response
```python
# ❌ ephemeral on followup doesn't work
await interaction.response.send_message('Public')
await interaction.followup.send('Also public', ephemeral=True)  # Ignored!

# ✅ Set ephemeral on the initial response
await interaction.response.send_message('Private', ephemeral=True)
await interaction.followup.send('Also private')  # Inherits ephemeral
```

### 🚩 7. Command description from docstring (first line only, 100 chars)
```python
@client.tree.command()
async def cmd(interaction: discord.Interaction):
    """This is the description visible in Discord (first 100 chars only).

    Second paragraph is NOT shown as description.
    """
    ...
```

### 🚩 8. `typing.Optional` for optional parameters
```python
# ✅ Works — makes parameter optional in Discord UI
async def greet(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    user = member or interaction.user
    ...

# ❌ Without Optional, the parameter is required
async def greet(interaction: discord.Interaction, member: discord.Member):
    ...
```

---

## 9. What This Means for P2-001 & P2-003

### P2-001 — Application Verification

| Check | Method | Expected |
|---|---|---|
| App ID resolves | `client.application_id` after login | `1510873134981582858` |
| App ID != None before sync | Check before `tree.sync()` | Must not be `None` |
| Sync succeeds | `await tree.sync()` | Returns `List[AppCommand]` |

**Implementation notes**:
- `application_id` is automatically resolved from gateway READY
- Can also be set explicitly via `Client(application_id=...)` in discord.py >= 2.4
- `setup_hook()` is the safest place to sync (after login, before gateway)
- Use `guild` param for sync to bypass 1-hour global propagation

### P2-003 — Intents Verification

| Intent | Default | Required For | How to Set |
|---|---|---|---|
| `guilds` | ✅ In default | Server/channel context | `Intents.default()` |
| `members` | ✅ In default | Member info in interactions | `Intents.default()` |
| `message_content` | ❌ Not in default | Only needed for prefix commands | `intents.message_content = True` |

**Verification pattern**:
```python
intents = discord.Intents.default()
assert intents.guilds, 'guilds intent must be enabled'
assert intents.members, 'members intent must be enabled'
```

**Discord Developer Portal requirement**: The bot's `applications.commands` scope must be enabled in the Discord Developer Portal for the bot. This is set per-application, not per-intent. Slash commands work with just `Intents.default()` enabled in the portal AND code.

---

## 10. Reference: discord.py Versions

| Version | Python | Key Changes | Release |
|---|---|---|---|
| 2.0 | 3.8+ | App commands, intents required, async setup_hook | 2022 |
| 2.1 | 3.8+ | Bug fixes | 2022 |
| 2.2 | 3.8+ | New features | 2023 |
| 2.3 | 3.8+ | Bug fixes | 2023 |
| 2.4 | 3.8+ | `allowed_contexts`, `allowed_installs`, explicit `application_id` param | 2024 |
| 2.5+ | 3.8+ | Ongoing maintenance | 2025+ |

**Pinning**: Use `discord.py>=2.4,<3.0` to get the latest 2.x features including the explicit `application_id` parameter.

---

## 11. Key Source Code References

| Component | File | Lines |
|---|---|---|
| `CommandTree.__init__` | `discord/app_commands/tree.py` | L66-L100 |
| `CommandTree.sync()` | `discord/app_commands/tree.py` | L1061-L1130 |
| `MissingApplicationID` | `discord/errors.py` | L294-L300 |
| `Client.setup_hook()` | `discord/client.py` | ~L600 |
| `Bot.__init__` (auto tree) | `discord/ext/commands/bot.py` | L172-L185 |
| Official basic example | `examples/app_commands/basic.py` | Full file |

---

## 12. Quick Reference: discord.py v2 App Commands Cheat Sheet

```python
# === SETUP ===
# With discord.Client:
client = discord.Client(intents=discord.Intents.default())
client.tree = app_commands.CommandTree(client)

# With commands.Bot (auto tree):
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

# === SYNC (in setup_hook or on_ready) ===
await client.tree.sync()                # Global — 1h propagation
await client.tree.sync(guild=GUILD)     # Guild — instant

# === REGISTER COMMANDS ===
@client.tree.command()
async def cmd(interaction: discord.Interaction, ...): ...

@client.tree.command(guild=discord.Object(id=...))  # Guild-only
@client.tree.context_menu(name='Action')            # Context menu

# === DESCRIBE PARAMETERS ===
@app_commands.describe(param='Description')
@app_commands.rename(internal_name='display_name')

# === RESPOND ===
await interaction.response.send_message('text')         # Fast ops
await interaction.response.send_message('text', ephemeral=True)  # Private
await interaction.response.defer(ephemeral=True)         # Slow ops (>3s)
await interaction.followup.send('text')                  # After defer

# === ERROR HANDLING ===
@client.tree.error
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message('Slow down!', ephemeral=True)
```

---

*End of report. Parent should read this before planner gate for P2-001/P2-003.*
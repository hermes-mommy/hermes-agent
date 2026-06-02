# Discord.py 2.x Reference Report — Guinevere P2-010..P2-012

**Date**: 2026-06-01  
**Sources**: Official discord.py docs (v2.6.4), GitHub `Rapptz/discord.py` source (master)

---

## `app_commands.CommandTree` — Guild-Scoped Sync

`CommandTree` is the central registry for all application commands. When using `commands.Bot`, a tree is auto-attached as `bot.tree`. For `discord.Client`, instantiate manually:

```python
self.tree = app_commands.CommandTree(self)
```

**Guild-scoped sync** — commands register to a specific guild instantly (no 1-hour propagation delay):

```python
async def setup_hook(self):
    await self.tree.sync(guild=discord.Object(id=MY_GUILD_ID))
```

**Global sync** (no `guild=` argument) — visible everywhere but takes up to 1 hour to propagate. Do **not** call global sync on every startup; it hits global rate limits.

Ref: [discord.py FAQ — restrict commands to a guild](https://discordpy.readthedocs.io/en/latest/faq.html#how-do-i-restrict-a-command-to-a-specific-guild)

---

## Command Registration — Decorator & Manual

**Decorator pattern** (recommended for P2-010's 33 commands):

```python
@tree.command(guild=discord.Object(id=GUILD_ID))
@app_commands.describe(member="The member to look up")
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    ...
```

**Manual registration** (for dynamic/bulk registration):

```python
tree.add_command(command_obj, guild=discord.Object(id=GUILD_ID))
```

**Do not combine** decorator `@tree.command(guild=...)` with `add_command(guild=...)` — causes duplicate commands.

**Parameter typing** — discord.py auto-resolves types from annotations:
- `str`, `int`, `float` → basic inputs
- `discord.Member`, `discord.User`, `discord.Role`, `discord.TextChannel` → auto-resolved from guild
- `Optional[T]` → makes the parameter optional
- `app_commands.Range[int, min, max]` → range-constrained int

Ref: [basic.py example](https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py)

---

## Command Sync Rate-Limit Cautions

- **Bulk upsert** (`tree.sync()`) is Discord's preferred method; unchanged commands do NOT count toward daily creation limits.
- **Daily creation limit**: 200 global command creates per day. Guild-scoped sync avoids this.
- **P2-010 guild-scoped sync is safe** — only sync once in `setup_hook()` on startup, not in a loop.
- **Never call global sync in a loop** or on every interaction — rate-limit ban risk.

Ref: [GitHub Issue #7534 — Improve App Command Sync](https://github.com/Rapptz/discord.py/issues/7534)

---

## `Interaction.response.defer()` + `followup.send()`

- **`defer()`** acknowledges the interaction; use when the response takes >3 seconds.
- After defer, **send followup via `interaction.followup.send()`**, NOT `interaction.response.send_message()` (that would raise `InteractionResponded`).
- **Ephemeral must be set in `defer()`, not in `followup.send()`** — Discord limitation:

```python
await interaction.response.defer(ephemeral=True)       # ✅ correct
await interaction.followup.send("Processing...")        # inherits ephemeral
```

- `followup.send()` without ephemeral in defer → message visible to all.
- `thinking=True` param shows "bot is thinking" loading state.

Ref: [Interactions API reference](https://discordpy.readthedocs.io/en/latest/interactions/api.html#discord.InteractionResponse.defer)

---

## `discord.Embed` + `discord.Color` Usage

**Constructor** — color accepts `int`, `discord.Colour`, or `Embed.Empty`:

```python
embed = discord.Embed(
    title="Status",
    description="System health report",
    color=0x00FF00        # hex green
)
```

**`discord.Colour` / `discord.Color`** — alias, same class:

```python
from discord import Color

Color.green()             # built-in named colors
Color.from_rgb(255, 0, 0) # RGB 0-255
Color.from_str("#00FF00")  # CSS hex string (v2.0+)
Color(value=0xRRGGBB)      # direct integer
```

**Embed setter** (`.colour` / `.color` both work):

```python
embed.colour = discord.Color.teal()
embed.color = 0x9B59B6
```

**Field methods** — `add_field`, `set_author`, `set_footer`, `set_image`, `set_thumbnail`, `set_image`.

Ref: [discord/colour.py](https://github.com/Rapptz/discord.py/blob/master/discord/colour.py), [Embed source](https://github.com/Rapptz/discord.py/blob/master/discord/embeds.py)

---

## Actionable Bullets for Guinevere P2-010..P2-012

1. **P2-010**: Use `@tree.command(guild=discord.Object(id=SINGLE_GUILD_ID))` decorator for all 33 commands — no need for per-command guilds() decorator if all go to the same guild.
2. **P2-010 sync**: Call `await self.tree.sync(guild=discord.Object(id=GUILD_ID))` exactly once in `setup_hook()`. Do not call global sync.
3. **P2-010 manual reg**: If commands are in cogs, use `await bot.add_cog(MyCog(), guild=discord.Object(id=GUILD_ID))` to auto-register.
4. **P2-011**: Define embed colors as module-level constants: `COLOR_OK = 0x00FF00`, `COLOR_WARN = 0xFFA500`, `COLOR_ERROR = 0xFF0000`. No need for `discord.Color` subclass — plain hex ints work in `Embed(color=...)`.
5. **P2-011 built-in colors**: Use `discord.Color.green()`, `discord.Color.orange()`, `discord.Color.red()` if semantic names are preferred.
6. **P2-012**: Build `/status` embed with `discord.Embed(title=..., color=COLOR_OK)`. Add fields with `embed.add_field(name=..., value=..., inline=False)`.
7. **P2-012 defer**: If `/status` fetches data from DB/API, use `await interaction.response.defer()` first, then `await interaction.followup.send(embed=embed)`.
8. **P2-012 ephemeral**: Set `ephemeral=True` in `defer()` if the status check should be private; do NOT set it in `followup.send()`.
9. **Rate-limit safety**: Never call `tree.sync()` on every cog load or interaction — once per `setup_hook()` for guild-scoped commands.
10. **Error handling**: Wrap defer/send in try/except for `discord.errors.InteractionResponded` and `HTTPException` to avoid silent failures.
# Research Report: Local Discord Command Callback Modules (P2-017 Wiring Context)

**Date:** 2026-06-01
**Scope:** Narrowed slice 1 — local callback signatures, builder APIs, embed patterns, Faiz guards, import hazards
**Files examined:** cmd_status.py, cmd_mood.py, cmd_help.py, cmd_safeword.py, commands.py, colors.py

---

## 1. Callback Function Signatures (Registration Targets)

All four commands use sync def (interaction: object) -> None with typed object parameter (no discord.py import at module level).

| Command | Callback | File | Line |
|---------|----------|------|------|
| /status | sync def status_callback(interaction: object) -> None: | cmd_status.py | 369 |
| /mood | sync def mood_callback(interaction: object) -> None: | cmd_mood.py | 367 |
| /help | sync def help_callback(interaction: object) -> None: | cmd_help.py | 343 |
| /safeword | sync def safeword_callback(interaction: object) -> None: | cmd_safeword.py | 546 |

**Registration hazard:** None of these callbacks are registered via 	ree.command(). Each module's docstring shows the pattern as a comment:

`python
# tree.command(name="status", description="...")(status_callback)
`

Registration happens in a yet-unwritten P2-017 wiring module (likely ot.py or a dedicated router in src/discord/).

---

## 2. Builder APIs (Deterministic Embed Data)

Every command module follows the same three-layer pattern:
1. **Builder** → returns frozen dataclass embed data (no discord.py dependency)
2. **to_discord_embed** → converts embed data to DiscordEmbedProtocol (uses dynamic importlib)
3. **Callback** → calls builder → conversion → followup send

### cmd_status.py — uild_status_embed_data()

`python
def build_status_embed_data(now: datetime | None = None) -> StatusEmbedData
`

- Returns StatusEmbedData with 11 fields
- Color: PRIMARY (0x6B21A8) from colors.py
- 7 of 11 fields use degraded placeholders for P3/P4/P5/P7
- Uptime computed from module-level _start_time
- Timestamp formatted as WIB (+07:00)

### cmd_mood.py — uild_mood_embed_data()

`python
def build_mood_embed_data(now: datetime | None = None, mood: str = "content") -> MoodEmbedData
`

- Returns MoodEmbedData with 6 fields
- Color: dynamic via color_for_mood(mood) from colors.py
- All 5 non-current-mood fields use degraded placeholders for P3/P4/P5
- Default mood: "content"

### cmd_help.py — uild_help_embed_data()

`python
def build_help_embed_data(categories: dict[str, tuple[str, ...]] | None = None) -> HelpEmbedData
`

- Returns HelpEmbedData with per-category fields
- Color: PRIMARY
- When categories=None, dynamically reads from commands.command_categories()
- Default categories contains only {"core": ("status", "mood", "help", "safeword")} as fallback

### cmd_safeword.py — uild_safeword_embed_data()

`python
def build_safeword_embed_data(handler: HardStopHandler, now: datetime | None = None) -> SafewordEmbedData

def build_recovery_embed_data(now: datetime | None = None) -> SafewordEmbedData
`

- Requires a HardStopHandler instance (not optional)
- 6 fields: Status, Persona, Punishment, Yandere, Surveillance Confrontation, Resume
- Color: SUCCESS (0x16A34A)
- Recovery variant swaps title/description for welcome-back message

---

## 3. to_discord_embed Pattern (Shared Across All 4)

Every module defines an identical pattern:

`python
def to_discord_embed(data: ) -> DiscordEmbedProtocol:
    d = _get_discord_embed_module()  # importlib.import_module("discord")
    embed = d.Embed(title=..., description=..., colour=d.Colour(data.color))
    for field in data.fields:
        embed.add_field(name=field.name, value=field.value, inline=field.inline)
    embed.set_footer(text=f"... | {data.timestamp} | ...")
    return embed
`

**Key implementation detail:** All 4 modules define identical local protocols:
- DiscordEmbedProtocol — duck-typed embed with dd_field(), set_footer()
- DiscordEmbedFactory / DiscordColourFactory — constructor protocols
- DiscordEmbedModule — protocol wrapping Embed + Colour
- DiscordResponseProtocol — defer(), is_done(), send_message()
- DiscordFollowupProtocol — send()
- DiscordInteractionProtocol — esponse + ollowup attributes
- All interaction protocols use @runtime_checkable

**Import hazard:** Every call to _get_discord_embed_module() does importlib.import_module("discord"). If called outside a running bot process, this raises ImportError — intentionally unguarded (no try/except at conversion level). Callbacks wrap the full chain in try/except with a degraded fallback message.

---

## 4. Faiz-Only Guard Behavior

All 4 callbacks share the same guard pattern:

`python
from .commands import is_faiz_interaction

if not is_faiz_interaction(interaction):
    await _send_denied(interaction)
    return
`

### is_faiz_interaction() — defined in commands.py (line 245)

`python
def is_faiz_interaction(interaction: object) -> bool:
    guild = getattr(interaction, "guild", None)
    user = getattr(interaction, "user", None)
    owner_id = getattr(guild, "owner_id", None)
    user_id = getattr(user, "id", None)
    return isinstance(owner_id, int) and isinstance(user_id, int) and owner_id == user_id
`

- **Fail-closed:** returns False if any attribute is missing/wrong type
- **No hardcoded user ID:** uses Discord's guild owner_id at runtime
- **No import from discord.py:** uses getattr duck-typing

### _send_denied() — duplicated in every cmd_*.py (4 copies)

All 4 modules have their own local _send_denied(), _defer_ephemeral(), and _followup_send() helpers. These are **identical in shape** with minor message differences:

| Module | Denial message |
|--------|---------------|
| cmd_status.py | "Hanya Faiz yang bisa menggunakan Mommy." |
| cmd_mood.py | "Hanya Faiz yang bisa menggunakan Mommy." |
| cmd_help.py | "Hanya Faiz yang bisa menggunakan Mommy." |
| cmd_safeword.py | "Command ini hanya untuk Faiz." |

**Import hazard:** Each callback does rom .commands import is_faiz_interaction inside the function body (lazy import) to avoid circular import at module load time. All 3 helpers (_send_denied, _defer_ephemeral, _followup_send) are module-private duplicates.

---

## 5. App Command Registration Implications

commands.py defines the canonical command surface:

- **33 commands** across **7 categories**: core (4), loop (6), memory (4), surveillance (3), finance (3), system (7), admin (4)
- CommandSpec dataclass with 	o_payload() → Discord REST payload
- COMMAND_SPECS tuple is the single source of truth
- command_categories() returns dict[str, tuple[str, ...]] — used by /help builder
- equire_canonical_registry() validates: 33 commands, unique names, name ≤ 32 chars, description ≤ 100 chars

**Registration gap:** None of the 4 implemented callbacks are wired to COMMAND_SPECS. P2-017 must bridge:
- {"name": "status", ...} ↔ status_callback
- {"name": "mood", ...} ↔ mood_callback
- {"name": "help", ...} ↔ help_callback
- {"name": "safeword", ...} ↔ safeword_callback

P2-017 wiring can use discord.app_commands.CommandTree.command() decorator or iterate COMMAND_SPECS and map names to callbacks via a lookup table.

---

## 6. Import Hazards Summary

| Hazard | Location | Impact |
|--------|----------|--------|
| importlib.import_module("discord") without guard | All 4 	o_discord_embed() + cmd_safeword inline embed | Raises ImportError if discord.py not installed |
| rom .commands import is_faiz_interaction inside function body | All 4 callbacks | Lazy import to avoid circular deps |
| rom .commands import command_categories inside function body | cmd_help.py builder | Same lazy pattern |
| rom src.core.services.hard_stop_handler import HardStopHandler inside functions | cmd_safeword.py _get_handler() / _new_handler() | Lazy import, valid pattern |
| rom .colors import PRIMARY / color_for_mood / SUCCESS at module top | All 4 modules | Safe: colors.py has no external deps |
| Duplicated _send_denied, _defer_ephemeral, _followup_send across 4 files | All cmd_*.py | Code duplication; P2-017 could refactor into shared helper module |
| Duplicated embed/composite protocols across 4 files | All cmd_*.py | 4 copies of DiscordEmbedProtocol, DiscordInteractionProtocol, etc. |

---

## 7. cmd_safeword P2-017 Specifics (Critical Path)

cmd_safeword.py has dedicated P2-017 wiring hooks:

### handle_safeword_message_async() (line 643) — PRIMARY P2-017 TARGET

`python
async def handle_safeword_message_async(message: object) -> bool
`

- Designed for on_message listener
- Returns True if safeword triggered, False otherwise
- Internally: checks author not bot, calls handler.check(content), builds embed inline, sends via channel.send(), reacts ❤️
- All failures logged, never raised (fail-soft)

### handle_safeword_message() (line 591) — sync placeholder

`python
def handle_safeword_message(message: object) -> bool
`

- Returns True but **does not send** the embed — docstring says "caller will typically be an async context"
- Marked as inactive; handle_safeword_message_async is the real target

### get_safety_state() (line 717)

`python
def get_safety_state() -> str
`

- Returns "normal" or "safe"
- Can be used by P2-017 to conditionally suppress persona behavior

### HardStopHandler Singleton

- Module-level _handler: HardStopHandler | None = None
- _get_handler() creates lazily on first call
- set_handler() for test injection
- Single-process MVP safe; multi-process needs Redis-backed state

---

## 8. Key Findings for P2-017 Wiring

1. **4 callbacks need registration** via 	ree.command() using names matching COMMAND_SPECS (status, mood, help, safeword).

2. **No existing router/bot.py** — P2-017 must create one in src/discord/ (likely ot.py or outer.py).

3. **handle_safeword_message_async** is the designated on_message hook — wire it early to text-based safe mode detection.

4. **All callbacks are Faiz-only** via is_faiz_interaction — no additional guard needed in the router.

5. **4 copies of identical helper functions** (_send_denied, _defer_ephemeral, _followup_send) — consider extracting to a shared _helpers.py module during P2-017.

6. **Dynamic discord.py import** means callbacks work in static analysis without discord.py installed, but will fail at runtime if discord.py is missing. This is by design.

7. **Safeword handler needs HardStopHandler** — accessed via module-level singleton, no explicit DI needed for MVP.

8. **10 command callbacks remain unimplemented** (loop, memory, surveillance, finance, system, admin categories) — P2-017 only wires the 4 implemented ones.

---

**Files referenced:**
- C:\Users\faizz\guinevere\src\discord\cmd_status.py (461 lines)
- C:\Users\faizz\guinevere\src\discord\cmd_mood.py (460 lines)
- C:\Users\faizz\guinevere\src\discord\cmd_help.py (436 lines)
- C:\Users\faizz\guinevere\src\discord\cmd_safeword.py (724 lines)
- C:\Users\faizz\guinevere\src\discord\commands.py (291 lines)
- C:\Users\faizz\guinevere\src\discord\colors.py (125 lines)

# P2-013 to P2-016 Code Pattern & Static Risk Report

**Date:** 2026-06-01
**Scope:** Implementation-pattern analysis for P2-013 (/mood), P2-014 (/help), P2-015 (/safeword + HARD STOP), P2-016 (startup message/presence)
**Method:** AST-grep, grep, static reading of `src/discord/`, `src/core/services/`, and test files
**Downstream:** Planner `docs/setup-evidence/P2/batch-plan-013-016.md`
**Output:** `research-reports/P2/p2-013-016-code-patterns-ast-report.md`

---

## Table of Contents

1. [Summary of AST/Static Risk Scan](#1-summary-of-aststatic-risk-scan)
2. [Shared Reusable Helpers & Protocols](#2-shared-reusable-helpers--protocols)
3. [P2-013 /mood — Implementation Pattern](#3-p2-013-mood--implementation-pattern)
4. [P2-014 /help — Implementation Pattern](#4-p2-014-help--implementation-pattern)
5. [P2-015 /safeword — Implementation Pattern](#5-p2-015-safeword--implementation-pattern)
6. [P2-016 Startup/Presence — Implementation Pattern](#6-p2-016-startuppresence--implementation-pattern)
7. [Collision Risks & Shared File Warnings](#7-collision-risks--shared-file-warnings)
8. [Validation Commands for Planner Gate](#8-validation-commands-for-planner-gate)
9. [Implementation Order & Dependencies](#9-implementation-order--dependencies)

---

## 1. Summary of AST/Static Risk Scan

| Risk Category | Found? | Location | Severity | Recommendation |
|---|---|---|---|---|
| `# type: ignore` | ❌ No | — | — | None — keep this clean |
| `Any` (untyped) | ✅ Yes | `hard_stop_handler.py:16,125` | Low | Both uses are in `dict[str, Any]` for `get_guard_decision` return type. Acceptable for P2-015 bridge but should be replaced with TypedDict in a future P3 safety refactor. |
| `except Exception:` (no logging) | ✅ Yes | `cmd_status.py:392` | **Medium** | The broad catch in `status_callback` does not log. New P2-013..P2-016 callbacks must log via `structlog` before fallback. |
| `except Exception as e:` (with logging) | ✅ Yes | `llm_router.py:83` | Low | Acceptable — logger.warning present |
| Empty `except:` | ❌ No | — | — | None |
| `cast()` overuse (>5/file) | ✅ Yes | `permissions.py` (12 uses) | Low | Established pattern for REST JSON parsing. Acceptable; do not replicate in new command files. |
| `import discord` (direct) | ❌ No | — | — | None — all imports use `importlib.import_module("discord")` + Protocol |
| `importlib.import_module("discord")` | ✅ Yes | 3 files: `cmd_status.py`, `guild_setup.py`, `intents.py` | Info | Established Guinevere pattern. P2-013..P2-015 command files must follow `cmd_status.py` protocol-based approach, not direct import. |
| `global` mutation | ✅ Yes | `cmd_status.py:72` | Low | `_start_time` with `# noqa: PLW0603`. Acceptable; P2-013 mood state would need similar state handling. |
| `os.environ` direct read | ✅ Yes | `guild_setup.py:230` | Low | Only `DISCORD_SECRETS_PATH` env var — not the token itself. Acceptable. |
| `on_ready` implementation | ❌ No | None yet | — | P2-016 must guard against repeated fire (discord.py fires `on_ready` on reconnect) |
| `process_commands` | ❌ No | None yet | — | N/A — slash commands use `tree.command`, not prefix commands |
| `discord.Bot` / `commands.Bot` instance | ❌ No | None yet | — | P2-017 will create this; P2-016 must accept bot/client as parameter or dependency |
| `tree.command` registration | ✅ (comment) | `cmd_status.py:15` | Info | Only a comment reference. Actual registration is deferred to bot.py (P2-017). |
| Protocol-based typing | ✅ Yes | 5 protocol classes in `cmd_status.py` | Info | Strong pattern — reuse for new commands |
| `@runtime_checkable` | ✅ Yes | `cmd_status.py:148,169,178` | Info | `isinstance`-safe protocols — must reuse for new commands |

**Summary:** Codebase is clean overall. Two concrete risks to address:
1. **Empty `except Exception:` in `cmd_status.py:392`** — must not replicate in new commands. New handlers must log before fallback.
2. **P2-016 `on_ready` guard** — must use `is_ready` bot flag or reconnect counter to avoid duplicate presence setting.

---

## 2. Shared Reusable Helpers & Protocols

### 2.1 Protocol Classes (in `cmd_status.py`)

| Protocol | Lines | Use in new commands | Reuse strategy |
|---|---|---|---|
| `DiscordInteractionProtocol` | 178-188 | ✅ P2-013, P2-014, P2-015 | Import directly: `from src.discord.cmd_status import DiscordInteractionProtocol` |
| `DiscordResponseProtocol` | 148-166 | ✅ For `response.defer()` in all | Indirectly via `DiscordInteractionProtocol.response` |
| `DiscordFollowupProtocol` | 169-175 | ✅ For `followup.send()` in all | Indirectly via `DiscordInteractionProtocol.followup` |
| `DiscordEmbedProtocol` | 84-103 | ✅ If P2-013/P2-014 use embeds | Import directly or use `to_discord_embed()` pattern |

**Recommendation:** Do NOT move protocols to a separate `protocols.py` now — too many imports would break existing files. Keep them in `cmd_status.py` for this batch. A P3 refactors can consolidate them.

### 2.2 Permission Helpers (in `commands.py`)

| Helper | Use | Reuse |
|---|---|---|
| `is_faiz_interaction(interaction: object) -> bool` | ✅ All commands need Faiz-only check | `from src.discord.commands import is_faiz_interaction` |

### 2.3 Color Helpers (in `colors.py`)

| Helper | Use | Reuse |
|---|---|---|
| `PRIMARY` (0x6B21A8) | ✅ P2-013, P2-014 default embeds | `from src.discord.colors import PRIMARY` |
| `ALERT` (0xDC2626) | ✅ P2-015 safeword embed | `from src.discord.colors import ALERT` |
| `SUCCESS` (0x16A34A) | ✅ P2-015 recovery embed | `from src.discord.colors import SUCCESS` |
| `color_for_mood(mood: str) -> int` | ✅ P2-013 mood embedding | `from src.discord.colors import color_for_mood` |
| `MOOD_COLORS` dict | ✅ P2-013 mood colour mapping | Already available in `colors.py:74-86` |

### 2.4 Internal Helpers (in `cmd_status.py`)

| Helper | Use | Reuse |
|---|---|---|
| `_send_denied(interaction)` | ✅ All commands for non-Faiz | Import or duplicate pattern |
| `_defer_ephemeral(interaction)` | ✅ All commands for Faiz-only | Import or duplicate pattern |
| `_followup_send(interaction, embed=, content=)` | ✅ All commands for response | Import or duplicate pattern |

**Recommendation:** Since these are currently module-private (`_send_denied`, `_defer_ephemeral`, `_followup_send`), either:
- **(A)** Extract them to a shared `src/discord/_shared.py` (preferred but adds a file), or
- **(B)** Make them public in `cmd_status.py` by renaming to `send_denied`, `defer_ephemeral`, `followup_send`, or
- **(C)** Duplicate the pattern in each new command file (acceptable for 3 new files, avoids shared-file collision during this batch).

**My recommendation: Option C** — duplicate the small helper pattern in each command file for this batch. It is 3-5 lines per file, avoids shared-file collisions, and a P3 refactor can deduplicate.

### 2.5 Token/Secrets (in `guild_setup.py`)

| Helper | Use | Reuse |
|---|---|---|
| `get_token() -> str` | ❌ P2-016 needs token? No — bot.py (P2-017) handles it. P2-016 just needs a `DiscordClient`-compatible object. | N/A for this batch |
| `GUILD_ID` (1510876414671323206) | ✅ P2-016 startup message may need guild ID | `from src.discord.commands import GUILD_ID` |

### 2.6 HardStopHandler (in `src/core/services/hard_stop_handler.py`)

| API | Use | Reuse |
|---|---|---|
| `HardStopHandler` class | ✅ P2-015 /safeword needs instantiation | `from src.core.services.hard_stop_handler import HardStopHandler` |
| `.check(message: str) -> bool` | ✅ P2-015 text-based detection | Instantiate a handler in `/safeword` callback |
| `.check_recovery(message: str) -> bool` | ✅ P2-015 recovery detection | Same |
| `.get_guard_decision(message: str) -> dict` | ✅ P2-015: returns blocked/response | Recommended for `/safeword` callback |
| `SafetyState` enum | ✅ P2-015 state check | `from src.core.services.hard_stop_handler import SafetyState` |

### 2.7 Existing Command Specs (in `commands.py`)

All three commands already registered in `COMMAND_SPECS` (P2-010 output):

| Command | Category | Description | Lines |
|---|---|---|---|
| `mood` | core | "Show or update Guinevere's current mood state." | 116 |
| `help` | core | "Show the Guinevere command guide." | 117 |
| `safeword` | core | "Trigger the configured safety boundary workflow." | 118 |

**No changes needed to `commands.py` for this batch.**

---

## 3. P2-013 /mood — Implementation Pattern

### 3.1 File to Create

`src/discord/cmd_mood.py` — following `cmd_status.py` structure exactly.

### 3.2 Pattern Template

```python
"""Discord /mood command implementation for Guinevere.

Provides deterministic mood state management and discord.py callback.
"""
from __future__ import annotations

import structlog
from typing import Final, Protocol, runtime_checkable

from .colors import PRIMARY, color_for_mood, MOOD_COLORS
from .cmd_status import DiscordInteractionProtocol, DiscordEmbedProtocol
from .commands import is_faiz_interaction

logger = structlog.get_logger()

# ── Mood State ─────────────────────────────────────────────────────

VALID_MOODS: Final[tuple[str, ...]] = tuple(MOOD_COLORS.keys())
"""Valid mood values: content, pleased, disappointed, angry, silent."""

DEFAULT_MOOD: Final[str] = "content"

_mood_state: str = DEFAULT_MOOD
"""Module-level mood state. Overridable via set_mood() for tests."""

# ── State Management ───────────────────────────────────────────────

def set_mood(mood: str) -> str | None:
    """Set the current mood. Returns None if invalid, else the mood string."""
    global _mood_state
    if mood not in MOOD_COLORS:
        return None
    _mood_state = mood
    return mood

def get_mood() -> str:
    """Return the current mood."""
    return _mood_state

# ── Discord Interaction Callback ───────────────────────────────────

async def mood_callback(interaction: object) -> None:
    """Handle a /mood interaction.
    
    Enforces Faiz-only access, defers ephemerally, shows current mood
    and valid options in an embed.
    """
    # ... follow same pattern as status_callback
```

### 3.3 Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| State location | Module-level `_mood_state` variable | Same pattern as `cmd_status.py._start_time`. No Redis/PG needed for P2. |
| Mood values | Keys from `colors.py:MOOD_COLORS` | Single source of truth. If MOOD_COLORS changes, /mood auto-updates. |
| Parameter | None for this batch (show-only) | Step prompt says "Show or update" — show-only for P2, update via follow-up P? |
| Embed colour | `color_for_mood(get_mood())` | Dynamic — embed colour reflects current mood. |
| Argument | Deferred to planner | If `mood_value` option is added, use `CommandOption` from `commands.py` pattern with choices from `MOOD_COLORS.keys()`. |

### 3.4 Reuse Checklist

- [ ] `is_faiz_interaction` from `commands.py`
- [ ] `DiscordInteractionProtocol` from `cmd_status.py`
- [ ] `DiscordEmbedProtocol` from `cmd_status.py` (if embed needed)
- [ ] `MOOD_COLORS` / `color_for_mood` / `PRIMARY` from `colors.py`
- [ ] `_defer_ephemeral` / `_followup_send` / `_send_denied` — duplicate pattern
- [ ] `structlog` for logging (critical — avoid empty `except Exception:`)

### 3.5 Static Risk Notes

- **No empty catch.** The outer try/except in `mood_callback` MUST log via `logger.warning("mood_fallback", ...)` before sending degraded message.
- **Protocol-based interaction typing** — same pattern as `status_callback` receives `object`, not `discord.Interaction`.
- **`_mood_state` global** — same pattern as `_start_time`; acceptable with `# noqa: PLW0603`.

---

## 4. P2-014 /help — Implementation Pattern

### 4.1 File to Create

`src/discord/cmd_help.py`

### 4.2 Pattern Template

```python
"""Discord /help command implementation for Guinevere."""
from __future__ import annotations

import structlog
from .cmd_status import DiscordInteractionProtocol
from .commands import is_faiz_interaction, command_categories
from .colors import PRIMARY

logger = structlog.get_logger()

async def help_callback(interaction: object) -> None:
    """Handle a /help interaction.
    
    Shows the Guinevere command guide grouped by category.
    """
    ...
```

### 4.3 Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Content type | Formatted text in ephemeral message, not embed (or single embed) | Keep simple for P2. An embed with multiple fields (one per category) is fine — embeds support up to 25 fields. |
| Data source | `command_categories()` from `commands.py` | Single source of truth. Automatically reflects all 33 registered commands. |
| Format | Category headers with command list | `command_categories()` returns `dict[str, tuple[str, ...]]` — iterate and render. |

### 4.4 Reuse Checklist

- [ ] `is_faiz_interaction` from `commands.py`
- [ ] `command_categories()` from `commands.py`
- [ ] `DiscordInteractionProtocol` from `cmd_status.py`
- [ ] `PRIMARY` from `colors.py`
- [ ] Helper pattern duplication (deny/defer/followup)
- [ ] `structlog` logging

### 4.5 Static Risk Notes

- **No dynamic import needed** — `/help` does not touch `discord.Embed` directly if using plain text response. If embed is used, follow the `to_discord_embed` / protocol pattern.
- **`command_categories()` returns a static dict** — thread-safe, no mutation risk.
- **No empty catch** — log before fallback.

---

## 5. P2-015 /safeword — Implementation Pattern

### 5.1 File to Create

`src/discord/cmd_safeword.py`

### 5.2 Pattern Template

```python
"""Discord /safeword command implementation for Guinevere.

Integrates with HardStopHandler from P1-021 to trigger the safety
boundary workflow and return a deterministic response embed.
"""
from __future__ import annotations

import structlog
from .cmd_status import DiscordInteractionProtocol, DiscordEmbedProtocol
from .commands import is_faiz_interaction
from .colors import ALERT, SUCCESS
from src.core.services.hard_stop_handler import HardStopHandler, SafetyState

logger = structlog.get_logger()

# ── Handler Instance (shared with text-based detection) ────────────

# P2-015 /safeword handler. The same handler is used by the text-based
# pre-LLM guard in P1-021. This instance is for slash-command access only.
_handler = HardStopHandler()

async def safeword_callback(interaction: object) -> None:
    """Handle a /safeword interaction.
    
    Triggers HARD STOP protocol via HardStopHandler, produces embed
    with ALERT colour and neutral-mode response text.
    """
    ...
```

### 5.3 Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Handler instance | New `HardStopHandler()` in `cmd_safeword.py` | The P1-021 handler lives in the core service layer and may be a separate instance. Planner must decide: share singleton or separate. |
| Handler source | `src.core.services.hard_stop_handler` | Direct import accepted — core service is stable, no protocol needed. |
| Response embed | ALERT colour with neutral text | Follows DiscordUXSpec §2.3 for safeword response. |
| Recovery embed | SUCCESS colour with "Persona mode restored" | Same handler's recovery path. |
| Slash vs text | Slash command triggers HARD STOP programmatically | Different from text-based detection in P1-021 — both share the same state machine. |

### 5.4 HardStopHandler Import Warning

The HardStopHandler class uses `Any` in its return type:

```python
def get_guard_decision(self, message: str) -> dict[str, Any]:
```

For P2-015, either:
- **(A)** Type the return as `TypedDict` locally: `class GuardDecision(TypedDict): blocked: bool; state: str; response: str | None`
- **(B)** Use `# type: ignore[return-type]` on the callback — **FORBIDDEN** per BLOCKING rules
- **(C)** Accept `Any` in the callback when calling `get_guard_decision` — acceptable as it enters the handler, not propagated

**Recommendation: Option C** — the `Any` is contained in the call to `get_guard_decision` and not propagated to the callback's own return type.

### 5.5 Reuse Checklist

- [ ] `is_faiz_interaction` from `commands.py`
- [ ] `DiscordInteractionProtocol` from `cmd_status.py`
- [ ] `HardStopHandler` from `src.core.services.hard_stop_handler`
- [ ] `ALERT`, `SUCCESS` from `colors.py`
- [ ] Helper pattern duplication
- [ ] `structlog` logging

---

## 6. P2-016 Startup/Presence — Implementation Pattern

### 6.1 File to Create

`src/discord/startup.py`

### 6.2 Pattern Template

```python
"""Discord startup greeting and presence for Guinevere P2-016.

Sends a startup message to the guinevere-chat channel and sets
bot presence (Activity watching) on the first on_ready event.
Uses a guard to prevent duplicate execution on reconnect.
"""
from __future__ import annotations

import structlog
from typing import Protocol

logger = structlog.get_logger()

# ── Guard ──────────────────────────────────────────────────────────

_HAS_STARTED: bool = False
"""Guard flag. True after first on_ready execution."""

# ── Protocol for bot client ────────────────────────────────────────

class BotClientProtocol(Protocol):
    """Minimal subset of discord.Client/Bot needed by startup."""
    
    guilds: list[object]
    user: object | None
    
    async def wait_until_ready(self) -> None: ...
    async def change_presence(self, *, activity: object | None = None) -> None: ...

class ActivityProtocol(Protocol):
    """Minimal subset of discord.Activity needed."""
    ...

# ── Startup Logic ──────────────────────────────────────────────────

async def on_ready(client: BotClientProtocol) -> None:
    """Handle bot on_ready event with duplicate-fire guard.
    
    Only executes once per process lifetime. On reconnect, the
    guard prevents duplicate greeting messages and presence reset.
    """
    global _HAS_STARTED
    if _HAS_STARTED:
        logger.info("startup_already_done", guild_count=len(client.guilds))
        return
    _HAS_STARTED = True
    
    logger.info("startup_executing", guild_count=len(client.guilds))
    # ... set presence, send startup message to guinevere-chat
```

### 6.3 Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| on_ready guard | `_HAS_STARTED: bool` flag | Prevents duplicate execution on gateway reconnect. Mandatory per discord.py docs. |
| Presence setting | `change_presence(activity=discord.Activity(...))` | Uses dynamic import via importlib or protocol. |
| Startup channel | `guinevere-chat` from `guild_setup.py.CHANNELS` | Canonical channel for operator communication. |
| Channel lookup | Via `guild.text_channels` after `client.wait_until_ready()` | Channel objects available after guilds cache. |
| Protocol dependency | `BotClientProtocol` defined locally | P2-017 will create the actual `discord.Bot` — P2-016 must accept a protocol-compatible object. |
| Dynamic import | `importlib.import_module("discord")` for `Activity` | Same pattern as `cmd_status.py._get_discord_embed_module()`. |

### 6.4 Static Risk Notes

- **`on_ready` repeated fire** — CRITICAL: discord.py fires `on_ready` every time the bot reconnects. The `_HAS_STARTED` guard is **mandatory**.
- **`client.user` can be None** — on first `on_ready`, `client.user` may be `None` in some edge cases. Guard against it.
- **No `import discord`** — must use `importlib` + Protocol or import-only-after-ready pattern.
- **Presence intents** — already configured in `intents.py:presences=True`. Verified in P2-003.
- **Message content intent** — already configured; not needed for startup but established.

### 6.5 Dependency on P2-017 (bot.py)

| Aspect | Status |
|---|---|
| `discord.Bot` / `discord.Client` instance | Does not exist yet — P2-017 creates `bot.py` |
| Guild cache availability | Requires `client.start()` to be called — P2-017 |
| `tree = app_commands.CommandTree(client)` | P2-017 |
| on_ready event registration | `@bot.event` or `@client.event` — P2-017 |

**Recommendation:** P2-016 `startup.py` defines the `on_ready` coroutine as a standalone function that accepts `BotClientProtocol`. P2-017 (`bot.py`) imports and wires it:
```python
# In bot.py (P2-017):
from src.discord.startup import on_ready
bot = discord.Bot(...)
@bot.event
async def on_ready_event():
    await on_ready(bot)
```

This keeps P2-016 and P2-017 files independent during implementation.

---

## 7. Collision Risks & Shared File Warnings

### 7.1 Files That MUST NOT Be Simultaneously Edited

| File | P2 batch that touches it | Risk |
|---|---|---|
| `src/discord/commands.py` | P2-010 (DONE) | ✅ No changes needed. Read-only for this batch. |
| `src/discord/cmd_status.py` | P2-012 (DONE) | `_send_denied`, `_defer_ephemeral`, `_followup_send` are private. If Option A is chosen (extract to shared), this file must be edited. |
| `src/core/services/hard_stop_handler.py` | P1-021 (DONE) | ✅ No changes needed. Read-only. |
| `src/core/main.py` | P1-022 (DONE) | ✅ No changes needed. Read-only. |
| `pyproject.toml` | P1-001 (DONE) | ✅ No changes needed. Has `discord.py>=2.4` already. |

### 7.2 Files That Will Be Created (Independent)

| File | Depends on | Collision with |
|---|---|---|
| `src/discord/cmd_mood.py` | `cmd_status.py`, `colors.py`, `commands.py` (read) | None — new file |
| `src/discord/cmd_help.py` | `cmd_status.py`, `commands.py` (read) | None — new file |
| `src/discord/cmd_safeword.py` | `cmd_status.py`, `colors.py`, `hard_stop_handler.py` (read) | None — new file |
| `src/discord/startup.py` | `guild_setup.py` (read) | None — new file |

All four new files are **fully independent** — no shared-writer conflicts.

### 7.3 Channel ID Constants

`guild_setup.py.CHANNELS` defines `ChannelSpec("guinevere-chat", ...)` which P2-016 startup needs for sending the greeting. The `CHANNELS` tuple is read-only from P2-006 and safe to import. However:

- **`permissions.py` reads `channel-ids.yaml`** for runtime channel IDs. P2-016 should NOT parse YAML — use `guild.text_channels` lookup instead.
- **Runtime channel IDs differ from static specs** — do NOT hardcode channel IDs in startup.py. Use guild discovery.

---

## 8. Validation Commands for Planner Gate

The planner must require these exact validation commands for each step:

### P2-013 /mood

```bash
# Unit tests
python -m pytest tests/discord/test_cmd_mood.py -v

# Static analysis
python -m mypy src/discord/cmd_mood.py --strict
python -m ruff check src/discord/cmd_mood.py

# Diagnostics check (no `# type: ignore`, no `Any` in command signature)
grep -n '# type: ignore' src/discord/cmd_mood.py  # MUST be empty
grep -n 'except\s*:' src/discord/cmd_mood.py       # MUST be empty
grep -n 'except Exception' src/discord/cmd_mood.py  # MUST have structlog call
```

### P2-014 /help

```bash
python -m pytest tests/discord/test_cmd_help.py -v
python -m mypy src/discord/cmd_help.py --strict
python -m ruff check src/discord/cmd_help.py
```

### P2-015 /safeword

```bash
python -m pytest tests/safety/test_hard_stop_handler.py -v  # Existing P1-021 tests
python -m pytest tests/discord/test_cmd_safeword.py -v       # New tests
python -m mypy src/discord/cmd_safeword.py --strict
python -m ruff check src/discord/cmd_safeword.py

# Verify no direct `discord` import
grep -n 'import discord' src/discord/cmd_safeword.py  # MUST be empty
```

### P2-016 startup

```bash
python -m pytest tests/discord/test_startup.py -v
python -m mypy src/discord/startup.py --strict
python -m ruff check src/discord/startup.py

# Verify on_ready guard exists
grep -n '_HAS_STARTED' src/discord/startup.py  # Must exist
grep -n 'already_done' src/discord/startup.py  # Must exist

# Verify no bot.py dependency leak
grep -n 'discord.Bot' src/discord/startup.py  # MUST be empty
```

### Cross-Step Validation

```bash
# Verify all imports resolve
python -c "from src.discord.cmd_mood import mood_callback"
python -c "from src.discord.cmd_help import help_callback"
python -c "from src.discord.cmd_safeword import safeword_callback"
python -c "from src.discord.startup import on_ready"

# Full diagnostics
python -m mypy src/discord/ --strict
python -m ruff check src/discord/
```

---

## 9. Implementation Order & Dependencies

```
P2-013 (/mood) ──┬── cmd_mood.py (independent)
P2-014 (/help) ──┼── cmd_help.py (independent)
P2-015 (/safeword) ─┼── cmd_safeword.py (independent)
P2-016 (startup) ──┴── startup.py (independent, but logically ordered last)
```

**Dependency map:**
- All four files depend only on *reading* existing files (`cmd_status.py`, `commands.py`, `colors.py`, `hard_stop_handler.py`, `guild_setup.py`).
- No file depends on another new file in this batch.
- **Parallel-safe**: All four can be implemented simultaneously by separate sub-agents.
- **Collision-free**: No shared writer.

**Recommended planner sequence:**
1. **Research gate** ✅ (this report)
2. **Planner gate**: Write `batch-plan-013-016.md`
3. **Implementation wave (parallel):** All 4 files
4. **Verification wave (parallel):** All 4 test suites
5. **Auditor wave (parallel):** 4 auditors, one per file
6. **Integration test:** Verify `/status` (P2-012), `/mood`, `/help`, `/safeword` all coexist in the same process

---

## Appendix A: File Layout Summary

```
src/discord/
├── __init__.py          # Module marker (DONE)
├── cmd_status.py        # P2-012: /status handler, protocols, helpers (DONE)
├── cmd_mood.py          # P2-013: /mood handler (NEW — this batch)
├── cmd_help.py          # P2-014: /help handler (NEW — this batch)
├── cmd_safeword.py      # P2-015: /safeword handler (NEW — this batch)
├── startup.py           # P2-016: startup message, presence (NEW — this batch)
├── commands.py          # P2-010: 33-command registry, helpers (DONE)
├── colors.py            # P2-011: colors, MOOD_COLORS (DONE)
├── guild_setup.py       # P2-004/005/006: guild bootstrap, get_token (DONE)
├── intents.py           # P2-003: gateway intents (DONE)
└── permissions.py       # P2-007/008/009: REST permissions (DONE)

src/core/services/
└── hard_stop_handler.py # P1-021: HARD STOP state machine (DONE — read-only)
```

## Appendix B: Key Static Constants Reference

| Constant | Value | Source | Used By |
|---|---|---|---|
| `GUILD_ID` | 1510876414671323206 | `commands.py:15` | P2-016 startup |
| `PRIMARY` | 0x6B21A8 | `colors.py:19` | P2-013, P2-014 |
| `ALERT` | 0xDC2626 | `colors.py:23` | P2-015 |
| `SUCCESS` | 0x16A34A | `colors.py:37` | P2-015 recovery |
| `MOOD_COLORS` | `{"content": SUCCESS, ...}` | `colors.py:74-86` | P2-013 |
| `CHANNELS` | 14 `ChannelSpec` tuples | `guild_setup.py:201-215` | P2-016 |
| `APPLICATION_ID` | 1510873134981582858 | `commands.py:16` | (future bot.py) |
| `command_categories()` | `dict[str, tuple[str, ...]]` | `commands.py:224-230` | P2-014 |
| `is_faiz_interaction()` | `(interaction: object) -> bool` | `commands.py:245-256` | P2-013, P2-014, P2-015 |
| `HardStopHandler` | (class) | `hard_stop_handler.py:34-149` | P2-015 |
| `get_token()` | `() -> str` | `guild_setup.py:227-242` | ❌ Not needed by this batch |

---

*End of report. Prepared for planner gate execution.*
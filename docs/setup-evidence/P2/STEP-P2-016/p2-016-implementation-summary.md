# STEP-P2-016 Implementation Summary — Startup Greeting & Presence Helper

## What Was Done

Created `src/discord/startup.py` — a startup greeting and presence helper module for the future `bot.py` (P2-017) wiring. The module follows the same Protocol + frozen dataclass + dynamic `importlib` pattern established by `cmd_mood.py`.

### Components

| Component | Description |
|---|---|
| Constants | `STARTUP_TITLE` (👑), `STARTUP_DESCRIPTION`, `STARTUP_FIELDS`, `STARTUP_FOOTER`, `COLOR` (PRIMARY), `PRESENCE_TEXT` (Darling 👁) |
| Data types | `StartupEmbedData` (frozen dataclass, 6 fields), `StartupEmbedField` (frozen dataclass, `inline=True` default) |
| Builder | `build_startup_embed_data(timestamp_str=None)` — deterministic data builder with WIB timestamp |
| Discord conversion | `to_discord_embed(data)` — dynamic `importlib` pattern, no top-level discord.py dependency |
| Protocols | `DiscordEmbedProtocol`, `DiscordEmbedFactory`, `DiscordColourFactory`, `DiscordEmbedModule`, `DiscordClientProtocol` |
| on_ready handler | `on_ready(client)` — idempotent greeting to `#guinevere-status`, presence set every call |
| Idempotency guard | Module-level `_sent_greeting: bool` with `reset_greeting()` export for testing |

### Key Design Decisions

1. **Dynamic importlib for discord.py**: `to_discord_embed` uses `importlib.import_module("discord")` so the module can be imported without discord.py installed
2. **`on_ready` uses same pattern**: The handler also uses `importlib.import_module("discord")` to avoid implicit-relative-import warnings
3. **Protocol-based typing**: `DiscordClientProtocol` provides type-safe access to `change_presence()` and `get_all_channels()` via `cast()`
4. **No `# type: ignore`**: All type-safety achieved through protocols and casts (per AGENTS.md §2)
5. **Channel name in config**: `guinevere-status` is a hardcoded string — no channel ID in source

## Files Changed

| File | Action | Size |
|---|---|---|
| `src/discord/startup.py` | **Created** | 348 lines |
| `tests/discord/test_startup.py` | **Created** | 341 lines |
| `docs/setup-evidence/P2/STEP-P2-016/p2-016-implementation-summary.md` | **Created** | This file |
| `docs/setup-evidence/P2/STEP-P2-016/verification.md` | **Created** | Verification evidence |

## Validation Results

| Check | Result |
|---|---|
| `py_compile src/discord/startup.py` | Pass (exit 0) |
| `py_compile tests/discord/test_startup.py` | Pass (exit 0) |
| LSP diagnostics (errors) | 0 errors |
| `pytest tests/discord/test_startup.py` | 22/22 passed |
| Unsafe patterns (`# type: ignore`, `except:`, token) | None found |

## Evidence Artifacts

- `src/discord/startup.py` — main implementation
- `tests/discord/test_startup.py` — deterministic test suite
- `docs/setup-evidence/P2/STEP-P2-016/verification.md` — 12-section verification

## Caveats

- `bot.py` does not exist yet (P2-017); `on_ready` is ready for wiring
- `discord.py` not installed in dev environment; dynamic import ensures no import-time failures
- The `#guinevere-status` channel must exist in the target Discord server at runtime

## Next Action

Wire `startup.on_ready` into `bot.py` (P2-017).
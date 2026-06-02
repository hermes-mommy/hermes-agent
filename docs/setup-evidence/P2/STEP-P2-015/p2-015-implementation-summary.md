# P2-015 Implementation Summary — `/safeword` + HARD STOP Text Detection

**Date:** 2026-06-01
**Author:** Guinevere (parent-orchestrated, Sisyphus-Junior/deep implemented)
**Status:** Complete

---

## Created File

| File | Lines | Purpose |
|------|-------|---------|
| `src/discord/cmd_safeword.py` | 721 | /safeword slash command, text HARD STOP detection, embed builders, handler singleton |

## Architecture

Follows the `cmd_mood.py` / `cmd_help.py` / `cmd_status.py` pattern:
- Protocol classes for `discord.Embed`, `discord.Interaction`, `discord.Message`
- Frozen `SafewordEmbedData` dataclass with 6 embed fields
- Dynamic `importlib` for `to_discord_embed()` (discord.py optional)
- Faiz-only guard via `is_faiz_interaction()`
- Structured logging via `logging.getLogger(__name__)`

### Key Components

| Component | Function | Role |
|-----------|----------|------|
| `SafewordEmbedData` | Frozen dataclass | 6-field safe-mode embed: Status, Persona, Punishment, Yandere, Surveillance Confrontation, Resume |
| `SafewordEmbedField` | Frozen dataclass | Individual embed field (name, value, inline) |
| `_get_handler()` | Singleton accessor | Lazily creates `HardStopHandler`, cached at module level |
| `set_handler()` | Test injection | Override handler singleton for deterministic tests |
| `_new_handler()` | Factory | Creates fresh `HardStopHandler` via lazy import |
| `build_safeword_embed_data()` | Data builder | Produces `SafewordEmbedData` from handler state |
| `build_recovery_embed_data()` | Data builder | Produces recovery embed data |
| `to_discord_embed()` | Converter | Dynamic importlib-based discord.Embed creation |
| `safeword_callback()` | Slash handler | `/safeword` interaction handler (Faiz-only, safe-mode embed) |
| `handle_safeword_message()` | Text detector (sync) | Stub for documentation; checks content, logs trigger |
| `handle_safeword_message_async()` | Text detector (async) | Full implementation for P2-017 on_message wiring |
| `get_safety_state()` | Accessor | Returns `handler.state.value` for tests |
| `_react_heart()` | Reaction helper | Fail-soft ❤️ reaction to triggering message |

### HardStopHandler Integration

- **Singleton pattern**: One `HardStopHandler` instance shared between slash and text detection paths
- **No parallel state**: All safe-mode tracking goes through the handler
- **Test isolation**: `set_handler()` allows injecting controlled handlers
- **Lazy import**: Avoids circular imports and enables module loading without full dependency graph
- **All P1-021 tests pass**: `tests/safety/test_hard_stop_handler.py` — 56/56 ✅

## Design Decisions

1. **Handler singleton over dependency injection**: For MVP single-process deployment, a module-level singleton is simpler and guarantees unified state. P2-017 will upgrade to DI if needed.

2. **Sync + async text detection**: The sync `handle_safeword_message` is a documentation placeholder. `handle_safeword_message_async` is the real implementation for async on_message handlers. Both function signatures preserved for P2-017 flexibility.

3. **No Discord-specific tests yet**: P1-021 handler tests (56/56) exhaustively test all trigger/state/audit behavior. Discord integration tests deferred to P2-017 when `bot.py` exists for realistic interaction testing.

4. **Ephemeral response for `/safeword`**: Per DiscordUXSpec recommendation — safe-word acknowledgment should be private to Faiz.

5. **Guinevere de Baroque**: Footer name uses "Baroque" per batch plan §10.4 and evidence conventions, not "Bordeaux" (variant from some research sources).

## Caveats

- **No audit-log integration**: The module logs safe-word events but doesn't send to `#audit-log` Discord channel yet (requires `bot.py` / channel lookup from P2-017).
- **No P2-017 wiring**: `handle_safeword_message_async` is ready but not connected to an `on_message` listener (P2-017 responsibility).
- **Bot message skip**: Text detection correctly skips bot messages to prevent self-trigger loops.
- **Pytest warnings**: 1 deprecation warning for `asyncio.get_event_loop_policy` (Python 3.16 future); non-blocking.
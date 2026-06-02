# Verification Report — P5-020 & P5-021

## What Was Done

Implemented the `/loop-start` and `/loop-stop` Discord slash commands for Guinevere, wiring them into the bot's command tree and removing them from the stub registry.

## Files Changed

| File | Action | Description |
|---|---|---|
| `src/discord/cmd_loop_start.py` | CREATED | `/loop-start` command implementation |
| `src/discord/cmd_loop_stop.py` | CREATED | `/loop-stop` command implementation |
| `src/discord/bot.py` | MODIFIED | Removed stubs, added imports, registered commands, updated `core_names` |

## Implementation Details

### `src/discord/cmd_loop_start.py` (P5-020)

- Follows `cmd_memory_add.py` pattern exactly
- Protocol classes: `DiscordResponseProtocol`, `DiscordFollowupProtocol`, `DiscordInteractionProtocol`
- `is_faiz_interaction` gate via `from .commands import is_faiz_interaction`
- `_defer_ephemeral`, `_followup_send`, `_send_denied` helpers
- WIB timezone constant: `timezone(timedelta(hours=7))`
- `build_loop_start_embed_data()` — pure data builder (no discord dependency)
- `to_discord_embed()` — converter using dynamic importlib
- `loop_start_callback()` — main async callback
  - Checks `is_faiz_interaction` → denies non-Faiz
  - Defers ephemerally
  - Extracts `goal` option (required)
  - Calls `POST http://localhost:8000/api/v1/loops` with `{"task": goal, "priority": "normal"}` and `X-Guinevere-API-Key` header
  - Builds embed: title "🔄 Loop Started", fields Goal / Loop ID (8 chars) / Status / Priority
  - Color: `SUCCESS` from `.colors`
  - Footer: "Guinevere de Baroque • {WIB timestamp} • ✨ Content"
  - Handles httpx errors (HTTPStatusError, RequestError, generic Exception)

### `src/discord/cmd_loop_stop.py` (P5-021)

- Same protocol/helper pattern as loop-start
- `build_loop_stop_embed_data()` — pure data builder
- `to_discord_embed()` — converter
- `loop_stop_callback()` — main async callback
  - Checks `is_faiz_interaction` → denies non-Faiz
  - Defers ephemerally
  - Extracts optional `loop_id` option
  - If `loop_id` provided: `POST /api/v1/loops/{loop_id}/cancel`
  - If no `loop_id`: `GET /api/v1/loops` to find active loops (status `running` or `queued`), then cancels each
  - Builds embed: title "⏹️ Loop Stopped", fields Loop ID / Previous Phase / Status
  - Color: `WARNING` from `.colors` (0xCA8A04)
  - Footer: same pattern
  - Handles httpx errors
- Helper functions: `_cancel_loop()`, `_list_active_loops()`

### `src/discord/bot.py` Modifications

1. **Removed from `_STUB_PHASE`**: `"loop-start": 5` and `"loop-stop": 5`
2. **Added imports in `setup_hook`**:
   ```python
   from .cmd_loop_start import loop_start_callback
   from .cmd_loop_stop import loop_stop_callback
   ```
3. **Registered commands** after memory-add:
   ```python
   self.tree.command(name="loop-start", description="...")(loop_start_callback)
   self.tree.command(name="loop-stop", description="...")(loop_stop_callback)
   ```
4. **Updated `core_names`** to include `"loop-start", "loop-stop"`
5. **Updated docstrings/comments**: 6 wired → 8 wired, 27 stubs → 25 stubs

## Validation Results

| Check | Result |
|---|---|
| `python -c "from src.discord.cmd_loop_start import loop_start_callback"` | ✅ PASS |
| `python -c "from src.discord.cmd_loop_stop import loop_stop_callback"` | ✅ PASS |
| `python -c "import ast; ast.parse(open('src/discord/bot.py').read())"` | ✅ syntax OK |
| LSP diagnostics — `cmd_loop_start.py` | ✅ 0 errors |
| LSP diagnostics — `cmd_loop_stop.py` | ✅ 0 errors |
| LSP diagnostics — `bot.py` | ⚠️ 4 pre-existing errors (discord package shadowing — not introduced by this change) |

## Boundary Compliance

- No `as any`, `@ts-ignore`, `# type: ignore` introduced
- No empty except blocks — all exceptions are caught with specific types or logged via `logger.exception`
- No hardcoded secrets — `GUINEVERE_API_KEY` read from env with dev fallback
- No hardcoded Faiz user ID — uses `is_faiz_interaction` (guild owner check)
- No direct discord.py type imports — uses Protocol classes
- No httpx used without async — `async with httpx.AsyncClient()` pattern used
- No API keys exposed in embed responses
- No files modified outside `src/discord/`
- No modifications to `commands.py`, `colors.py`, or existing command files
- No commit performed

## Rollback Plan

1. Delete `src/discord/cmd_loop_start.py` and `src/discord/cmd_loop_stop.py`
2. Restore `bot.py` by reverting the 4 edit groups (stub re-add, import removal, registration removal, core_names revert)

## Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| `cmd_loop_start.py` created with `loop_start_callback` export | ✅ |
| `cmd_loop_stop.py` created with `loop_stop_callback` export | ✅ |
| `bot.py` stubs removed for loop-start and loop-stop | ✅ |
| `bot.py` imports and registrations added | ✅ |
| `core_names` includes loop-start and loop-stop | ✅ |
| Import verification passes | ✅ |
| Syntax verification passes | ✅ |

# P8-017 Verification — /cost Command

## What Was Done

Implemented the `/cost` Discord slash command (P8-017) following the canonical
5-part pattern established by existing commands (`cmd_status.py`, `cmd_mood.py`,
`cmd_memory_search.py`).

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/discord/cmd_cost.py` | Created | Full /cost command implementation (662 lines) |
| `src/discord/commands.py` | Modified | Added `OPTION_NUMBER`, `COST_PERIOD_CHOICES`, updated cost CommandSpec with `period` option |
| `src/discord/bot.py` | Modified | Removed "cost" from `_STUB_PHASE`, added "cost" to `core_names`, imported and wired `cost_callback` |

## Implementation Details

### 5-Part Pattern Compliance

1. **Protocols**: `DiscordEmbedProtocol`, `DiscordEmbedFactory`, `DiscordColourFactory`, `DiscordEmbedModule`, `DiscordResponseProtocol`, `DiscordFollowupProtocol`, `DiscordInteractionProtocol` — all defined with `@runtime_checkable` where applicable
2. **Frozen dataclasses**: `CostEmbedField`, `CostEmbedData` — both `@dataclass(frozen=True)`
3. **Builder function**: `build_cost_embed_data(period, now)` — reads from Redis DB5 via CostTracker
4. **Converter**: `to_discord_embed(data)` — uses dynamic `importlib` pattern
5. **Async callback**: `cost_callback(interaction)` — `is_faiz_interaction` guard, `_defer_ephemeral`, build, send

### Features

- **Period parameter**: `today`, `week`, `month` (default: `today`) with choice validation
- **Embed color**: `0x6B21A8` (PRIMARY / purple) — sourced from `colors.PRIMARY`
- **Total spend**: Reads `cost:current_day` (today), sums `cost:daily:*` (week), reads `cost:current_month` (month)
- **Per-model breakdown**: Scans `cost:by_model:*` keys, top 5 sorted by cost descending
- **Per-tool breakdown**: Scans `tool:cost:*:{date}` keys for today, top 5
- **3-day trend**: Reads last 3 days of `cost:daily:{YYYY-MM-DD}` with visual bar chart
- **Projected month-end**: Calculates daily average × remaining days in month

### Wiring

- Removed `"cost": 4` from `_STUB_PHASE` in `bot.py`
- Added `"cost"` to `core_names` tuple in `setup_hook()` stub exclusion
- Import: `from .cmd_cost import cost_callback`
- Registration: `self.tree.command(name="cost", description="...")(cost_callback)`

## Scaffold Check Results

| Check | Status |
|-------|--------|
| `is_faiz_interaction` guard present | PASS |
| `_defer_ephemeral` called before work | PASS |
| Embed color = `0x6B21A8` (PRIMARY) | PASS |
| No `as any` / `# type: ignore` / `@ts-ignore` | PASS |
| No `typing.Any` annotations | PASS |
| No empty except blocks | PASS |
| No hardcoded cost values | PASS |
| No hardcoded channel IDs | PASS |
| "cost" removed from `_STUB_PHASE` | PASS |
| LSP diagnostics (own errors) | PASS (only pre-existing `reportMissingImports` for `redis`) |
| 5-part pattern complete | PASS |

## Boundary Compliance

- No persona drift: uses persona-flavored description
- No consent violation: `is_faiz_interaction` enforced
- No secret exposure: Redis password from `os.environ`
- No surveillance overreach: cost data only

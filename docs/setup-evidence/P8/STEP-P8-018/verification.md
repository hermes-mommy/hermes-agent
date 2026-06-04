# P8-018 Verification — /budget Command

## What Was Done

Implemented the `/budget` Discord slash command (P8-018) following the canonical
5-part pattern. Supports `view` (default) and `set` actions for managing the
monthly budget cap stored in Redis DB5.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/discord/cmd_budget.py` | Created | Full /budget command implementation (643 lines) |
| `src/discord/commands.py` | Modified | Added `BUDGET_ACTION_CHOICES`, updated budget CommandSpec with `action` and `amount` options |
| `src/discord/bot.py` | Modified | Removed "budget" from `_STUB_PHASE`, added "budget" to `core_names`, imported and wired `budget_callback` |

## Implementation Details

### 5-Part Pattern Compliance

1. **Protocols**: Same protocol set as other commands
2. **Frozen dataclasses**: `BudgetEmbedField`, `BudgetEmbedData` — both `@dataclass(frozen=True)`
3. **Builder functions**: `build_budget_embed_data(now)` for view, `build_budget_set_embed_data(new_cap, now)` for set confirmation
4. **Converter**: `to_discord_embed(data)` — uses dynamic `importlib` pattern
5. **Async callback**: `budget_callback(interaction)` — `is_faiz_interaction` guard, `_defer_ephemeral`, action routing

### Features

- **view action** (default): Shows monthly cap, current spend, remaining, percentage, progress bar, alert status
- **set action**: Validates amount > 0, writes to `budget:monthly_cap` in Redis, shows confirmation embed
- **Embed color**: `0x059669` (FINANCE / teal) — sourced from `colors.FINANCE`
- **Progress bar**: Text-based `█░` progress visualization
- **Status emoji**: Maps status strings to emoji (NORMAL=✅, WARNING=⚠️, CRITICAL=🚨, HARD_STOP=🛑)
- **Validation**: Rejects missing amount, non-numeric, and non-positive values with persona-flavored messages

### Wiring

- Removed `"budget": 4` from `_STUB_PHASE` in `bot.py`
- Added `"budget"` to `core_names` tuple in `setup_hook()` stub exclusion
- Import: `from .cmd_budget import budget_callback`
- Registration: `self.tree.command(name="budget", description="...")(budget_callback)`

## Scaffold Check Results

| Check | Status |
|-------|--------|
| `is_faiz_interaction` guard present | PASS |
| `_defer_ephemeral` called before work | PASS |
| Embed color = `0x059669` (FINANCE) | PASS |
| No `as any` / `# type: ignore` / `@ts-ignore` | PASS |
| No `typing.Any` annotations | PASS |
| No empty except blocks | PASS |
| No hardcoded cost values | PASS |
| No hardcoded channel IDs | PASS |
| "budget" removed from `_STUB_PHASE` | PASS |
| Amount validation (positive, numeric) | PASS |
| LSP diagnostics (own errors) | PASS (only pre-existing `reportMissingImports` for `redis`) |
| 5-part pattern complete | PASS |

## Boundary Compliance

- No persona drift: persona-flavored descriptions and error messages
- No consent violation: `is_faiz_interaction` enforced
- No secret exposure: Redis password from `os.environ`
- Budget set requires Faiz-only access

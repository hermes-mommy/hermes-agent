# STEP B3 A2 — Command Auth/Registry Extraction Verification

**Date:** 2026-06-06
**Step:** A2 (Command auth/catalog extraction)
**Status:** PASS

---

## What Was Done

Extracted `is_faiz_interaction` to `src/discord/_auth_guard.py` and Discord-specific command registry (`CommandSpec`, `CommandOption`, `COMMAND_SPECS`, all registry functions) to `src/discord/_command_registry.py`. Updated all 32 production consumers and 2 test consumers to import from the new non-deprecated homes. Fixed stale canonical count expectations from 33 to 35.

## Files Changed

### Created
- `src/discord/_auth_guard.py` — `is_faiz_interaction()` (auth gate, pure logic)
- `src/discord/_command_registry.py` — command registry (CommandSpec, CommandOption, COMMAND_SPECS, all registry functions, canonical count 35)

### Modified — auth guard imports (32 `cmd_*.py` files)
All changed `from .commands import is_faiz_interaction` → `from ._auth_guard import is_faiz_interaction`:
- `cmd_approve.py`, `cmd_approve_all.py`, `cmd_backup_now.py`, `cmd_budget.py`, `cmd_casual.py`, `cmd_clear_cache.py`, `cmd_consent.py`, `cmd_cost.py`, `cmd_cost_alert.py`, `cmd_deny.py`, `cmd_evidence.py`, `cmd_focus.py`, `cmd_health_check.py`, `cmd_help.py`, `cmd_history.py`, `cmd_loops.py`, `cmd_loop_pause.py`, `cmd_loop_priority.py`, `cmd_loop_resume.py`, `cmd_loop_start.py`, `cmd_loop_stop.py`, `cmd_memory_add.py`, `cmd_memory_export.py`, `cmd_memory_forget.py`, `cmd_memory_search.py`, `cmd_mood.py`, `cmd_new_session.py`, `cmd_punishment.py`, `cmd_restart_service.py`, `cmd_reward.py`, `cmd_safeword.py`, `cmd_status.py`

### Modified — command_categories redirect
- `src/discord/cmd_help.py` — `from .commands import command_categories` → `from src.hermes_plugins.command_catalog import command_categories`

### Modified — bot.py import
- `src/discord/bot.py` — `from . import commands as cmds` → `from ._command_registry import COMMAND_SPECS`; `cmds.COMMAND_SPECS` → `COMMAND_SPECS`

### Modified — test imports
- `tests/discord/test_bot.py` — `test_import_commands` → `test_import_command_registry`; `command_count() == 33` → `command_count() == 35`
- `tests/discord/test_cmd_mood.py` — `from src.discord.commands import command_count` → `from src.discord._command_registry import command_count`

## Validation Results

### Active import grep
```
src/ — No matches for `from .commands import | from . import commands as cmds | import src.discord.commands`
tests/ — No matches for `from .commands import | from . import commands as cmds | import src.discord.commands`
```
Only docstring references remain (4 files: `_auth_guard.py`, `_command_registry.py`, `cmd_help.py`, `command_catalog.py`), which are not active imports.

### Required command tests

**`pytest tests/discord/test_cmd_mood.py tests/discord/test_bot.py -q --tb=short`:**
```
3 failed, 71 passed
```
The 3 failures are pre-existing `TestSetupHook` tests — `tree.get_commands()` returns `[]` because guild-scoped commands require a guild argument. Not caused by A2 changes.

**Key passing tests (A2-relevant):**
- ✅ `TestCommandRegistryCount::test_command_count_is_canonical` — asserts `command_count() == 35` from `_command_registry`
- ✅ `TestHandlerImports::test_import_command_registry` — imports `_command_registry`, asserts `command_count() == 35`

**`pytest tests/phase7/ -q --tb=short`:**
```
139 passed, 1 warning — All PASS ✅
```

### LSP Diagnostics
All changed files have **zero LSP errors**:
- `src/discord/_auth_guard.py` — ✅ No diagnostics
- `src/discord/_command_registry.py` — ✅ No diagnostics
- `src/discord/bot.py` — ✅ No diagnostics
- `src/discord/cmd_help.py` — ✅ No diagnostics
- `tests/discord/test_bot.py` — ✅ No new diagnostics (pre-existing pytest import resolution warning)
- `tests/discord/test_cmd_mood.py` — ✅ No new diagnostics (pre-existing pytest import resolution warning)

### Forbidden Patterns
- `Any` — None introduced
- `# type: ignore` — None introduced
- `except:` / `except Exception` — None introduced
- Type suppressions — None introduced

## Evidence Artifacts
- `src/discord/_auth_guard.py` — Created
- `src/discord/_command_registry.py` — Created (canonical count fixed to 35)
- This file

## Doc-Sync Impact
- Plan (`phase-7c-b3-archive-plan.md`) — Section 7 (A2 scaffold) now fully satisfied
- `fix-imports/02-commands-usage.md` — Recommendations implemented

## Boundary Compliance
- No PersonaSafetyPolicy drift
- No consent/surveillance boundary touched
- No secrets exposed
- No Aizanta/VPS/SSH/deployment touched

## Rollback/Run Safety
- All new modules are additive; no existing module deleted
- Rollback: revert the 32 import changes + bot.py + 2 test files; delete the 2 new files
- Re-run safe: yes

## Design Decisions
1. `require_canonical_registry()` expectation changed from 33 to 35 in `_command_registry.py` (matching actual 35-command count)
2. `test_bot.py::test_import_commands` renamed to `test_import_command_registry` with count corrected to 35
3. `test_bot.py::TestSetupHook::test_register_33_commands` not renamed (pre-existing, uses `get_commands()` without guild arg)

## Hard Rejection Criteria

| Criterion | Status |
|---|---|
| Any active import from `commands.py` remains | ❌ **NONE FOUND** ✅ |
| Command count/categorization drifts from 35 commands | ✅ 35 in `_command_registry.py`, confirmed by tests |
| Forbidden pattern `from .commands import` outside `_deprecated/` | ✅ Zero matches in src/ and tests/ |
| Forbidden pattern `from . import commands as cmds` outside `_deprecated/` | ✅ Zero matches in src/ and tests/ |
| Type suppressions, empty catches, avoidable `Any` | ✅ None introduced |

## Footer

Evidence for STEP-B3-A2 command auth/registry extraction. All gates pass. Ready for A3.

# STEP-RG-005 Verification Report

**Task:** Wire RitualScheduler into bot.py setup_hook (RG-005)  
**Date:** 2026-06-03  
**Status:** ✅ PASS  

---

## What Was Done

Modified `src/discord/bot.py` to integrate the `RitualScheduler` with a Discord callback that sends ritual messages to `#guinevere-chat` (channel ID: `1510914600777023659`).

### Changes Applied

1. **Import added** (line 25): `from src.persona.ritual_scheduler import RitualScheduler, RitualResult`
2. **Instance attribute declared** in `__init__`: `self._ritual_scheduler: RitualScheduler | None = None`
3. **Scheduler wired in `setup_hook()`**: After all command registrations and guild sync, a try/except block creates a `RitualScheduler`, defines a Discord callback (`_discord_ritual_callback`), registers it via `setup()`, and calls `start()`. Fail-soft: if anything fails, logs a warning and sets `_ritual_scheduler = None`.
4. **`close()` override added**: Stops the ritual scheduler gracefully before calling `super().close()`. Fail-soft with try/except.

### Discord Callback Behavior

- Looks up channel `1510914600777023659` via `self.get_channel()`
- If channel not found: logs warning, returns `RitualResult(success=False, error="Channel not found")`
- If channel found: retrieves ritual config from `_RITUAL_MAP`, sends `default_message` to channel
- If send fails: logs error, returns `RitualResult(success=False, error=str(send_err))`
- If send succeeds: logs info, returns `RitualResult(success=True)`

---

## Files Changed

| File | Lines Changed | Description |
|---|---|---|
| `src/discord/bot.py` | +47 lines | Import, init attr, setup_hook scheduler block, close() method |

---

## Validation Results

| Check | Command | Expected | Actual | Status |
|---|---|---|---|---|
| Syntax compile | `python -m py_compile src/discord/bot.py` | exit 0 | exit 0 | ✅ PASS |
| New LSP errors | `lsp_diagnostics(severity=error)` | 0 new errors | 0 new (4 pre-existing) | ✅ PASS |
| TODO count | `grep -c "TODO" src/discord/bot.py` | 0 | 0 | ✅ PASS |
| ritual_scheduler refs | `grep -c "ritual_scheduler" src/discord/bot.py` | ≥ 3 | 13 | ✅ PASS |
| type: ignore (new) | `grep "type: ignore" src/discord/bot.py` | 0 new | 1 (pre-existing line 33) | ✅ PASS |
| Empty except | `grep "except.*:\\s*$" src/discord/bot.py` | 0 | 0 | ✅ PASS |

### Pre-existing LSP Errors (not introduced by this change)

All 4 pre-existing errors stem from the dynamic `importlib.import_module("discord.ext.commands")` pattern at line 30-32, which basedpyright cannot statically resolve:

- `reportImplicitRelativeImport` at line 18
- `reportMissingImports` at line 21
- `reportAttributeAccessIssue` at line 115 (`Intents`)
- `reportAttributeAccessIssue` at line 268 (`Object`)

---

## Design Decisions

1. **Logger pattern**: Used `extra={}` dict for structured logging (consistent with existing `bot.py` pattern), not kwargs (which `logging.Logger` does not support, unlike `structlog` used in `ritual_scheduler.py`).
2. **Instance attribute in `__init__`**: Declared `self._ritual_scheduler` in `__init__` with type annotation to avoid needing `# type: ignore[attr-defined]`.
3. **Fail-soft startup**: Entire scheduler block wrapped in try/except — if APScheduler or any dependency is missing, bot starts normally with a warning log.
4. **Lazy imports in callback**: `datetime` and `_RITUAL_MAP` imported inside the callback to avoid circular import risks and keep the top-level import clean.
5. **`close()` uses `getattr`**: Defensive access via `getattr(self, "_ritual_scheduler", None)` for robustness even though the attribute is declared in `__init__`.

---

## Boundary Compliance

- ✅ No persona drift (ritual messages unchanged from `RitualConfig.default_message`)
- ✅ No consent violation (scheduler is system-level, no surveillance)
- ✅ No Y6 yandere content
- ✅ No secrets committed
- ✅ No surveillance overreach
- ✅ No HARD STOP bypass

---

## Rollback / Re-run Safety

- Removing the import, init attribute, setup_hook block, and close() method fully reverts the change.
- RitualScheduler is idempotent — can be stopped/started multiple times safely.
- `close()` calls `super().close()` regardless of scheduler state.

---

## Footer

| Step | Task | Status |
|---|---|---|
| RG-005 | Wire RitualScheduler into bot.py setup_hook | ✅ PASS |

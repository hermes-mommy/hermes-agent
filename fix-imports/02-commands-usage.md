# Fix-Imports 02: `src/discord/commands.py` Export Usage Map

**Date:** 2026-06-06
**Task:** Map exact current usage of `is_faiz_interaction`, `command_categories`, and `COMMAND_SPECS` exports from `src/discord/commands.py` across `src/` (production) and `tests/`, and determine which consumers block archive.

**Verdict:** All 3 exports have active live consumers that block archiving `commands.py`. `command_catalog.py` already covers `command_categories` (✅ usable as replacement) and `command_count` (✅ usable as replacement), but does NOT cover `is_faiz_interaction` (auth function — needs separate `_auth_guard.py`) nor `COMMAND_SPECS` (Discord-specific payloads — needs `_command_registry.py` or similar).

---

## 1. Source of Truth: `src/discord/commands.py` (D03 — Deprecated)

The file defines these exported symbols relevant to archiving:

| Symbol | Line | Type | Description |
|---|---|---|---|
| `COMMAND_SPECS` | 126 | `tuple[CommandSpec, ...]` | Canonical list of 35 slash-command specs as REST payload dataclasses |
| `build_application_commands()` | 255 | function | Returns `spec.to_payload()` for all specs |
| `command_count()` | 261 | function | Returns `len(COMMAND_SPECS)` |
| `command_categories()` | 267 | function | Derives `dict[str, tuple[str, ...]]` from `COMMAND_SPECS` |
| `unknown_command_names()` | 276 | function | Set diff against canonical names |
| `missing_command_names()` | 282 | function | Set diff against canonical names |
| `is_faiz_interaction()` | 288 | function | Guild-owner auth gate (fail-closed) |
| `require_canonical_registry()` | 302 | function | Validation assertion (hardcoded expects 33) |

---

## 2. `is_faiz_interaction` — Complete Usage Map

### 2.1 Definition

- **`src/discord/commands.py:288`** (D03 — deprecated) — canonical definition
- **`src/discord/cmd_surveillance_status.py:48`** — local duplicate (independent, self-contained)
- **`src/discord/cmd_surveillance_pause.py:58`** — local duplicate (independent, self-contained)
- **`src/discord/cmd_surveillance_resume.py:58`** — local duplicate (independent, self-contained)

### 2.2 Production `src/` Callers (32 files, 31 dependent on D03)

All 31 files do a **lazy relative import** inside the callback function body to avoid circular imports:

```python
from .commands import is_faiz_interaction
if not is_faiz_interaction(interaction):
    await _send_denied(interaction)
    return
```

| # | File | Import Line | Call Line |
|---|---|---|---|
| 1 | `src/discord/cmd_approve.py` | 36 | 38 |
| 2 | `src/discord/cmd_approve_all.py` | 36 | 38 |
| 3 | `src/discord/cmd_backup_now.py` | 39 | 41 |
| 4 | `src/discord/cmd_budget.py` | 526 | 528 |
| 5 | `src/discord/cmd_casual.py` | 43 | 45 |
| 6 | `src/discord/cmd_clear_cache.py` | 45 | 47 |
| 7 | `src/discord/cmd_consent.py` | 69 | 71 |
| 8 | `src/discord/cmd_cost.py` | 582 | 584 |
| 9 | `src/discord/cmd_cost_alert.py` | 137 | 139 |
| 10 | `src/discord/cmd_deny.py` | 36 | 38 |
| 11 | `src/discord/cmd_evidence.py` | 127 | 129 |
| 12 | `src/discord/cmd_focus.py` | 50 | 52 |
| 13 | `src/discord/cmd_health_check.py` | 129 | 131 |
| 14 | `src/discord/cmd_help.py` | 354 | 356 |
| 15 | `src/discord/cmd_history.py` | 49 | 51 |
| 16 | `src/discord/cmd_loops.py` | 92 | 94 |
| 17 | `src/discord/cmd_loop_pause.py` | 36 | 38 |
| 18 | `src/discord/cmd_loop_priority.py` | 44 | 46 |
| 19 | `src/discord/cmd_loop_resume.py` | 37 | 39 |
| 20 | `src/discord/cmd_loop_start.py` | 327 | 329 |
| 21 | `src/discord/cmd_loop_stop.py` | 375 | 377 |
| 22 | `src/discord/cmd_memory_add.py` | 338 | 340 |
| 23 | `src/discord/cmd_memory_export.py` | 203 | 205 |
| 24 | `src/discord/cmd_memory_forget.py` | 135 | 137 |
| 25 | `src/discord/cmd_memory_search.py` | 358 | 360 |
| 26 | `src/discord/cmd_mood.py` | 378 | 380 |
| 27 | `src/discord/cmd_new_session.py` | 36 | 38 |
| 28 | `src/discord/cmd_punishment.py` | 84 | 86 |
| 29 | `src/discord/cmd_restart_service.py` | 53 | 55 |
| 30 | `src/discord/cmd_reward.py` | 68 | 70 |
| 31 | `src/discord/cmd_safeword.py` | 557 | 559 |
| 32 | `src/discord/cmd_status.py` | 380 | 382 |

**3 files have local copies (NOT dependent on D03):**
- `src/discord/cmd_surveillance_status.py` — local `is_faiz_interaction` at line 48
- `src/discord/cmd_surveillance_pause.py` — local `is_faiz_interaction` at line 58
- `src/discord/cmd_surveillance_resume.py` — local `is_faiz_interaction` at line 58

### 2.3 Test Callers (1 file, NOT dependent on D03)

- `tests/surveillance/test_discord_commands.py:22` — imports `is_faiz_interaction` from `src.discord.cmd_surveillance_status` (the local copy, NOT from `commands.py`)
- Tests 6 functions: `test_is_faiz_interaction_returns_true_for_owner`, `test_...false_for_non_owner`, `test_...false_when_guild_none`, `test_...false_when_user_none`, `test_...with_missing_attrs`, `test_...type_safety`

### 2.4 Blocker Status: **RED** — 31 production files import from D03

---

## 3. `command_categories` — Complete Usage Map

### 3.1 Definition

- **`src/discord/commands.py:267`** (D03 — deprecated) — derives from `COMMAND_SPECS`
- **`src/hermes_plugins/command_catalog.py:44`** (ACTIVE, non-deprecated) — returns copy of static `_COMMAND_CATEGORIES`

### 3.2 Production `src/` Callers (2 files)

| # | File | Import Line | Call Line | Depends on D03? |
|---|---|---|---|---|
| 1 | `src/discord/cmd_help.py` | 279 | 281 | **YES** — `from .commands import command_categories` |
| 2 | `src/hermes_plugins/commands_high/help.py` | 13 | 86 | **NO** — `from src.hermes_plugins.command_catalog import command_categories as _command_categories` ✅ Already migrated |

### 3.3 Test Callers

None. No test file imports `command_categories` from `commands.py`.

### 3.4 Blocker Status: **RED** — 1 production file (`cmd_help.py`) still imports from D03

---

## 4. `COMMAND_SPECS` — Complete Usage Map

### 4.1 Definition

- **`src/discord/commands.py:126`** — tuple of 35 `CommandSpec` instances

### 4.2 Production `src/` Callers (1 file)

| # | File | Import | Line |
|---|---|---|---|
| 1 | `src/discord/bot.py` | `from . import commands as cmds` | 203 (module-level, inside `setup_hook()`) |
|   | `src/discord/bot.py` | `cmds.COMMAND_SPECS` iteration | 416 (for stub registration of unwired commands) |

This is a top-level **module import** (not a selective symbol import), so `bot.py` effectively imports the entire `commands.py` namespace.

### 4.3 Test Callers

None directly import `COMMAND_SPECS`. However:
- `tests/discord/test_bot.py:171-172` — `import src.discord.commands` / `src.discord.commands.command_count()`
- `tests/discord/test_cmd_mood.py:273` — `from src.discord.commands import command_count`

### 4.4 Blocker Status: **RED** — `bot.py` imports the entire `commands.py` module

---

## 5. `command_count` — Ancillary Export (Blocking Tests)

Relevant because it's imported from `commands.py` in test files.

### 5.1 Definition

- **`src/discord/commands.py:261`** (D03 — deprecated) — returns `len(COMMAND_SPECS)` (currently 35)
- **`src/hermes_plugins/command_catalog.py:49`** (ACTIVE, non-deprecated) — returns `sum(len(cmds) for cmds in _COMMAND_CATEGORIES.values())`

### 5.2 Production `src/` Callers

None external. Only used internally within `commands.py` (by `require_canonical_registry()`).

### 5.3 Test Callers (2 files)

| # | File | Line | Import | Depends on D03? |
|---|---|---|---|---|
| 1 | `tests/discord/test_bot.py` | 172 | `src.discord.commands.command_count()` | **YES** — calls via module reference |
| 2 | `tests/discord/test_cmd_mood.py` | 273 | `from src.discord.commands import command_count` | **YES** — direct import |

### 5.4 Additional Note: Assertion Values Are Stale

- `test_bot.py:172` asserts `== 33` (should be 35 — stale since Phase 1 added "new" and "history")
- `test_cmd_mood.py:275` asserts `== 35` (correct — updated)
- This inconsistency blocks full test suite runs regardless of archiving.

---

## 6. What `command_catalog.py` Already Covers

`src/hermes_plugins/command_catalog.py` currently provides:

| Export | Has It? | Same Interface? | Compatible with cmd_help.py? |
|---|---|---|---|
| `command_categories()` | ✅ Yes (line 44) | ✅ `() -> dict[str, tuple[str, ...]]` | ✅ Yes — identical signature |
| `command_count()` | ✅ Yes (line 49) | ✅ `() -> int` | ✅ Yes — identical signature |
| `is_faiz_interaction()` | ❌ No | N/A — auth function, not metadata | N/A — needs separate file |
| `COMMAND_SPECS` | ❌ No | N/A — Discord-specific payload type | N/A — needs separate file |

**Conclusion:** `command_catalog.py` is a viable replacement for `command_categories` and `command_count`, but two additional non-deprecated homes are needed:

---

## 7. Recommended Non-Deprecated Homes

### 7.1 `is_faiz_interaction` → `src/discord/_auth_guard.py`

- **Contents:** The `is_faiz_interaction()` function (pure logic, no Discord import dependency beyond `object` typing)
- **Why not in command_catalog.py:** It's an authorization gate, not metadata. Belongs in a security/auth module.
- **Files to update:** All 31 `cmd_*.py` files that do `from .commands import is_faiz_interaction` → `from ._auth_guard import is_faiz_interaction`
- **3 surveillance files:** They have local copies — optionally refactor to import from `_auth_guard.py` or leave as-is (DRY trade-off).

### 7.2 `COMMAND_SPECS` → `src/discord/_command_registry.py`

- **Contents:** `CommandSpec` dataclass, `CommandOption`, `COMMAND_SPECS` tuple, `command_count()`, `command_categories()` (or delegate to `command_catalog.py`)
- **Why not in command_catalog.py:** `COMMAND_SPECS` is Discord-specific (`CommandSpec` dataclass with `to_payload()`, `CommandOption`, `TypedDict` payload types). `command_catalog.py` is deliberately Discord-free.
- **Files to update:**
  - `src/discord/bot.py` — `from . import commands as cmds` → `from ._command_registry import COMMAND_SPECS` (or import selectively)
  - `src/discord/cmd_help.py` — `from .commands import command_categories` → `from src.hermes_plugins.command_catalog import command_categories`
  - `tests/discord/test_bot.py:171-172` — `import src.discord.commands` / `src.discord.commands.command_count()` → import from `_command_registry` or `command_catalog`
  - `tests/discord/test_cmd_mood.py:273` — `from src.discord.commands import command_count` → `from src.hermes_plugins.command_catalog import command_count`

---

## 8. Summary: Consumers Blocking Archive

| Export | Live Production Consumers | Test Consumers | Blocking Archive? | Recommended New Home |
|---|---|---|---|---|
| `is_faiz_interaction` | 31 `cmd_*.py` files | 0 (test imports local copy) | **YES — RED** | `src/discord/_auth_guard.py` |
| `command_categories` | 1 file (`cmd_help.py`) | 0 | **YES — RED** | Already in `command_catalog.py` — just redirect import |
| `COMMAND_SPECS` | 1 file (`bot.py`, full module import) | 0 (but `test_bot.py` imports module) | **YES — RED** | `src/discord/_command_registry.py` |
| `command_count` | 0 | 2 tests (`test_bot.py`, `test_cmd_mood.py`) | **YELLOW** — blocks clean test suite | Already in `command_catalog.py` — redirect test imports |

### Total files to update across all extractions:
- **31 `cmd_*.py`** — `from .commands import is_faiz_interaction` → `from ._auth_guard import is_faiz_interaction`
- **1 `bot.py`** — `from . import commands as cmds` → selective imports from `_command_registry`
- **1 `cmd_help.py`** — `from .commands import command_categories` → `from src.hermes_plugins.command_catalog import command_categories`
- **2 test files** — redirect `command_count` import to `command_catalog.py`
- **Total: ~35 files** need import path changes

---

*Based on direct grep/ast-grep/LSP search of entire `src/` and `tests/` tree. No files modified.*

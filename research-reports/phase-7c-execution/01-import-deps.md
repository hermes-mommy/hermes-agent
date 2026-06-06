# Phase 7c — Deprecated Import Dependency Map

> **Date:** 2026-06-06  
> **Scope:** All `src/` and `tests/` files referencing the 10 target-deprecated files  
> **Methodology:** grep + manual line-by-line verification across entire codebase  
> **Status:** Complete — 73 cross-file references identified  

---

## Table of Contents

1. [Summary of Findings](#1-summary-of-findings)
2. [Target Deprecated Files (10 files)](#2-target-deprecated-files)
3. [Internal Dependencies Between Deprecated Files](#3-internal-dependencies)
4. [External Importers — Active Source Files](#4-external-importers)
5. [External Importers — Test Files](#5-external-importers-test-files)
6. [Test Classification](#6-test-classification)
7. [hermes/__init__.py — Re-export Analysis](#7-hermes__init__py-analysis)
8. [hermes_plugins/commands_high/help.py — Command Catalog Dependency](#8-help-py-plugin-analysis)
9. [Safe Ordering / Phased Archive Plan](#9-safe-ordering)
10. [Hard Blockers](#10-hard-blockers)
11. [Can Tests Pass After Archive?](#11-can-tests-pass-after-archive)

---

## 1. Summary of Findings

| Metric | Count |
|---|---|
| Deprecated files identified for archive | 10 |
| Internal cross-references (deprecated↔deprecated) | 6 |
| Active source files importing deprecated targets | 55+ |
| Active test files importing deprecated targets | 5 (12 import sites) |
| Total unique active files affected | 60+ |
| `pytest tests/` CAN pass after archive | **NO** — 5 test files will fail |
| KEEP ACTIVE file confirmed | `src/core/services/llm_router.py` — no references to deprecated files found |

**Verdict: Archival is NOT SAFE without intermediate refactoring steps.** All 10 files have active, blocking inbound dependencies that must be resolved first.

---

## 2. Target Deprecated Files

| # | File | Dep Type | Primary Role |
|---|---|---|---|
| D01 | `src/discord/bot.py` | Discord | Main bot class, `main()` entrypoint, `on_message` handler |
| D02 | `src/discord/conversational_handler.py` | Discord | Old chat handler, imports `HermesMemoryBridge` + `get_adapter` |
| D03 | `src/discord/commands.py` | Discord | Slash command registry, `is_faiz_interaction`, `command_categories` |
| D04 | `src/discord/permissions.py` | Discord | Permission/topic helpers, imports `guild_setup.get_token` |
| D05 | `src/discord/guild_setup.py` | Discord | Guild bootstrap, `CHANNELS`, `get_token()` |
| D06 | `src/discord/startup.py` | Discord | `on_ready` greeting handler, embed builders |
| D07 | `src/discord/_embed_helpers.py` | Discord | Shared embed formatting for 22 slash commands |
| D08 | `src/discord/intents.py` | Discord | Gateway intent config, `get_intents()` |
| D09 | `src/hermes/session_adapter.py` | Hermes | `HermesSessionAdapter` class |
| D10 | `src/hermes/memory_bridge.py` | Hermes | `HermesMemoryBridge` class |

---

## 3. Internal Dependencies (Deprecated → Deprecated)

These must be resolved in archive ORDER — archiving the dependee before the depender breaks the depender.

| Depender | Line | Imports | Dependency |
|---|---|---|---|
| `bot.py` (D01) | 24 | `from .intents import get_intents` | → D08 `intents.py` |
| `bot.py` (D01) | 489 | `from .startup import on_ready as startup_on_ready` | → D06 `startup.py` |
| `bot.py` (D01) | 523 | `from .conversational_handler import handle_conversation` | → D02 `conversational_handler.py` |
| `permissions.py` (D04) | 18 | `from src.discord.guild_setup import CHANNELS, get_token` | → D05 `guild_setup.py` |
| `conversational_handler.py` (D02) | 155 | `from src.hermes.memory_bridge import HermesMemoryBridge` | → D10 `memory_bridge.py` |
| `conversational_handler.py` (D02) | 199 | `from src.hermes import get_adapter` | → D09 `session_adapter.py` (via `__init__.py`) |

**Archive order constraint:** D02 depends on D09 and D10; D01 depends on D08, D06, D02; D04 depends on D05.

---

## 4. External Importers — Active Source Files

### 4.1 — `_embed_helpers.py` (D07) — 22 importers (HIGHEST RISK)

Every `cmd_*.py` file uses `from ._embed_helpers import (...)` for embed construction. Archiving D07 breaks ALL of these:

| File | Line | Import |
|---|---|---|
| `src/discord/cmd_approve.py` | 16 | `from ._embed_helpers import ...` |
| `src/discord/cmd_approve_all.py` | 16 | `from ._embed_helpers import ...` |
| `src/discord/cmd_backup_now.py` | 18 | `from ._embed_helpers import ...` |
| `src/discord/cmd_casual.py` | 17 | `from ._embed_helpers import ...` |
| `src/discord/cmd_clear_cache.py` | 20 | `from ._embed_helpers import ...` |
| `src/discord/cmd_consent.py` | 22 | `from ._embed_helpers import ...` |
| `src/discord/cmd_cost_alert.py` | 18 | `from ._embed_helpers import ...` |
| `src/discord/cmd_deny.py` | 16 | `from ._embed_helpers import ...` |
| `src/discord/cmd_evidence.py` | 19 | `from ._embed_helpers import ...` |
| `src/discord/cmd_focus.py` | 17 | `from ._embed_helpers import ...` |
| `src/discord/cmd_health_check.py` | 18 | `from ._embed_helpers import ...` |
| `src/discord/cmd_history.py` | 17 | `from ._embed_helpers import ...` |
| `src/discord/cmd_loops.py` | 16 | `from ._embed_helpers import ...` |
| `src/discord/cmd_loop_pause.py` | 16 | `from ._embed_helpers import ...` |
| `src/discord/cmd_loop_priority.py` | 16 | `from ._embed_helpers import ...` |
| `src/discord/cmd_loop_resume.py` | 16 | `from ._embed_helpers import ...` |
| `src/discord/cmd_memory_export.py` | 19 | `from ._embed_helpers import ...` |
| `src/discord/cmd_memory_forget.py` | 19 | `from ._embed_helpers import ...` |
| `src/discord/cmd_new_session.py` | 17 | `from ._embed_helpers import ...` |
| `src/discord/cmd_punishment.py` | 22 | `from ._embed_helpers import ...` |
| `src/discord/cmd_restart_service.py` | 20 | `from ._embed_helpers import ...` |
| `src/discord/cmd_reward.py` | 21 | `from ._embed_helpers import ...` |

### 4.2 — `commands.py` (D03) — 33 importers (CRITICAL)

`commands.py` exports `is_faiz_interaction`, `command_count`, and `command_categories`. 32 `cmd_*.py` files import `is_faiz_interaction` and 2 files import `command_categories`:

**`is_faiz_interaction` importers (31 files):**

| File | Line | Import |
|---|---|---|
| `src/discord/cmd_approve.py` | 36 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_approve_all.py` | 36 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_backup_now.py` | 39 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_budget.py` | 526 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_casual.py` | 43 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_clear_cache.py` | 45 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_consent.py` | 69 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_cost.py` | 582 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_cost_alert.py` | 137 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_deny.py` | 36 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_evidence.py` | 127 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_focus.py` | 50 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_health_check.py` | 129 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_help.py` | 279, 354 | `from .commands import command_categories` + `is_faiz_interaction` |
| `src/discord/cmd_history.py` | 49 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_loops.py` | 92 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_loop_pause.py` | 36 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_loop_priority.py` | 44 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_loop_resume.py` | 37 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_loop_start.py` | 327 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_loop_stop.py` | 375 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_memory_add.py` | 338 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_memory_export.py` | 203 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_memory_forget.py` | 135 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_memory_search.py` | 358 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_mood.py` | 378 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_new_session.py` | 36 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_punishment.py` | 84 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_restart_service.py` | 53 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_reward.py` | 68 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_safeword.py` | 557 | `from .commands import is_faiz_interaction` |
| `src/discord/cmd_status.py` | 380 | `from .commands import is_faiz_interaction` |

**`command_categories` importers (2 files):**

| File | Line | Import |
|---|---|---|
| `src/discord/cmd_help.py` | 279 | `from .commands import command_categories` |
| `src/hermes_plugins/commands_high/help.py` | 72 | `from src.discord.commands import command_categories` |

### 4.3 — `hermes/memory_bridge.py` (D10) — 2 external + 1 internal importers

| File | Line | Import |
|---|---|---|
| `src/discord/hermes_conversational.py` | 132 | `from src.hermes.memory_bridge import HermesMemoryBridge` |
| `src/discord/conversational_handler.py` | 155 | `from src.hermes.memory_bridge import HermesMemoryBridge` |
| `src/hermes/__init__.py` | 12 | `from .memory_bridge import HermesMemoryBridge` |

Additionally, `src/hermes_plugins/commands_memory/__init__.py` (line 6) and `src/hermes_plugins/commands_memory/memory_search.py` (lines 4, 91) reference `HermesMemoryBridge` in comments and internal logic (no import — they import through the plugin system).

### 4.4 — `hermes/session_adapter.py` (D09) — 1 re-exporter + 6 transitive consumers

Direct importer:
| File | Line | Import |
|---|---|---|
| `src/hermes/__init__.py` | 11 | `from .session_adapter import HermesSessionAdapter` |

Transitive consumers via `src.hermes.get_adapter()`:
| File | Line | Import |
|---|---|---|
| `src/discord/conversational_handler.py` | 199 | `from src.hermes import get_adapter` |
| `src/discord/hermes_conversational.py` | 174 | `from src.hermes import get_adapter` |
| `src/discord/cmd_new_session.py` | 45 | `from src.hermes import get_adapter` |
| `src/discord/cmd_history.py` | 58 | `from src.hermes import get_adapter` |
| `src/hermes_plugins/commands_high/new_session.py` | 48 | `from src.hermes import get_adapter` |
| `src/hermes_plugins/commands_high/history.py` | 59 | `from src.hermes import get_adapter` |

### 4.5 — `bot.py` (D01) — Active use in production

`bot.py` is not "imported" by any other source file (it is the entrypoint), but:
- Its `GuinevereBot` class is the runtime bot instance
- Its `on_message` handler (line 495) imports `conversational_handler.handle_conversation` (line 523)
- Its `__init__` (line 86) calls `get_intents()` from `intents.py`
- Its `on_ready` (line 474) calls `startup.on_ready()` (line 489)
- Its `setup_hook` (line 152) imports all 33 `cmd_*.py` handlers

### 4.6 — `startup.py` (D06) — 1 external importer

| File | Line | Import |
|---|---|---|
| `src/discord/bot.py` | 489 | `from .startup import on_ready as startup_on_ready` |

### 4.7 — `intents.py` (D08) — 1 external importer

| File | Line | Import |
|---|---|---|
| `src/discord/bot.py` | 24 | `from .intents import get_intents` |

### 4.8 — `permissions.py` (D04) and `guild_setup.py` (D05)

No external source files import from `permissions.py` or `guild_setup.py` outside `src/discord/`. The only consumer of `guild_setup` is `permissions.py` (D04→D05).

Both files may be referenced by operational scripts or docs, but no active Python imports were found outside the deprecated set.

---

## 5. External Importers — Test Files

### 5.1 — `tests/discord/test_bot.py` — 8 import sites

| Line | Import | Depends On |
|---|---|---|
| 32 | `from src.discord.bot import GuinevereBot` | D01 `bot.py` |
| 167 | `import src.discord.startup` | D06 `startup.py` |
| 168 | `assert hasattr(src.discord.startup, "on_ready")` | D06 `startup.py` |
| 171 | `import src.discord.commands` | D03 `commands.py` |
| 172 | `assert src.discord.commands.command_count() == 33` | D03 `commands.py` |
| 260 | `from src.discord.bot import main` | D01 `bot.py` |
| 269 | `from src.discord.bot import main` | D01 `bot.py` |
| 295 | `from src.discord import bot` | D01 `bot.py` |

### 5.2 — `tests/discord/test_startup.py` — 8 import sites

| Line | Import | Depends On |
|---|---|---|
| 18 | `from src.discord.startup import (...)` | D06 `startup.py` |
| 289 | `from src.discord.startup import on_ready` | D06 `startup.py` |
| 303 | `from src.discord.startup import on_ready` | D06 `startup.py` |
| 318 | `from src.discord.startup import on_ready` | D06 `startup.py` |
| 334 | `from src.discord.startup import on_ready` | D06 `startup.py` |
| 349 | `from src.discord.startup import on_ready` | D06 `startup.py` |
| 369 | `from src.discord import startup` | D06 `startup.py` |

### 5.3 — `tests/discord/test_conversational_handler.py` — 9 import sites

| Line | Import | Depends On |
|---|---|---|
| 18 | `from src.discord.conversational_handler import (...)` | D02 `conversational_handler.py` |
| 24 | `handle_conversation` | D02 `conversational_handler.py` |
| 234 | `from src.discord.conversational_handler import _is_rate_limited` | D02 `conversational_handler.py` |

Plus 12 additional patched references to `MODULE._is_rate_limited`, `MODULE._get_router`, etc.

### 5.4 — `tests/discord/test_cmd_mood.py` — 1 import site

| Line | Import | Depends On |
|---|---|---|
| 273 | `from src.discord.commands import command_count` | D03 `commands.py` |

### 5.5 — `tests/hermes/test_memory_bridge.py` — 1 import site

| Line | Import | Depends On |
|---|---|---|
| 15 | `from src.hermes.memory_bridge import HermesMemoryBridge` | D10 `memory_bridge.py` |

Note: Lines 8-11 also have a preemptive `sys.modules` hack to prevent `session_adapter` import failure from `src/hermes/__init__.py`.

### 5.6 — Tests NOT affected

The following test directories/files do **NOT** import any deprecated files directly:

| Test File | Notes |
|---|---|
| `tests/discord/test_notifications.py` | Only imports `src.discord.notifications` (KEEP ACTIVE) |
| `tests/discord/test_gotify_fallback.py` | Only imports `src.discord.gotify_fallback` (KEEP ACTIVE) |
| `tests/discord/test_gotify_client.py` | Not inspected but assumed clean |
| `tests/discord/conftest.py` | Only caches real `discord` library |
| `tests/surveillance/conftest.py` | Only caches real `discord` package |
| `tests/surveillance/test_discord_commands.py` | Imports `cmd_surveillance_*` (KEEP ACTIVE) |
| `tests/hermes/test_safety_plugin.py` | Pre-emptive `sys.modules` hack but no direct import |

---

## 6. Test Classification

| Test File | Import Count | Actions Required Before Archive |
|---|---|---|
| `tests/discord/test_bot.py` | 6 test classes, 8 imports | **RETAIN** (tests `bot.py` + `commands` + `startup`). Must be rewritten to target replacement or archived with the deprecated files. |
| `tests/discord/test_startup.py` | 6 test classes, 8 imports | **ARCHIVE WITH** D06 `startup.py`. Tests are 100% about `startup.py`. |
| `tests/discord/test_conversational_handler.py` | 5 test classes, 3 direct imports | **REWRITE** to target `hermes_conversational.py` instead (replacement exists). |
| `tests/discord/test_cmd_mood.py` | 1 import (`command_count`) | **UPDATE** — replace `command_count()` with a local constant or mock. |
| `tests/hermes/test_memory_bridge.py` | 1 import (`HermesMemoryBridge`) | **ARCHIVE WITH** D10 `memory_bridge.py` OR rewrite against new memory provider. |

**Verdict: 3 test files must be rewritten before archive, 2 must be archived with their source.**

---

## 7. `src/hermes/__init__.py` Analysis

**Current content (43 lines):**

```python
from .session_adapter import HermesSessionAdapter    # line 11 -> D09
from .memory_bridge import HermesMemoryBridge          # line 12 -> D10

_adapter_instance: HermesSessionAdapter | None = None  # line 17

def get_adapter() -> HermesSessionAdapter:             # line 20
    """..."""
    if _adapter_instance is None:
        _adapter_instance = HermesSessionAdapter(...)   # line 31 -> D09
    return _adapter_instance

__all__ = ["HermesSessionAdapter", "HermesMemoryBridge", "get_adapter"]  # line 43
```

**Impact:** Archiving `session_adapter.py` (D09) or `memory_bridge.py` (D10) directly breaks `hermes/__init__.py`.

**Required changes if D09 and/or D10 are archived:**

1. **`get_adapter()`** (used by 6 external files) imports `HermesSessionAdapter` eagerly at line 11 and instantiates it lazily at line 31. Both references block archiving `session_adapter.py`.

2. **`HermesMemoryBridge`** re-export (line 12, 43) blocks archiving `memory_bridge.py`.

3. **Recommendation:** Move `get_adapter()` and the singleton pattern into a separate file (e.g., `src/hermes/_adapter.py`) if `session_adapter.py` is archived. Update `hermes/__init__.py` to import from the new location.

4. If `memory_bridge.py` is archived, remove lines 12 and 43, and delete `HermesMemoryBridge` from `__all__`.

5. No changes needed to the `TYPE_CHECKING` block.

---

## 8. `src/hermes_plugins/commands_high/help.py` Analysis

**Current import at line 72:**

```python
def _format_help_markdown(
    categories: dict[str, tuple[str, ...]] | None = None,
) -> str:
    from src.discord.commands import command_categories  # line 72 -> D03

    cats = categories if categories is not None else command_categories()
```

**Impact:** Archiving `commands.py` (D03) breaks `/help` in the Hermes CLI plugin.

**Options before archive:**

1. **Option A (Recommended):** Accept an optional `categories` parameter from the caller. The Hermes plugin registry can pre-compute the categories at registration time.
2. **Option B:** Inline a static copy of `command_categories()` within the help module.
3. **Option C:** Export `command_categories` from a non-deprecated file (e.g., `src/discord/cmd_help.py` already has a `_compute_command_count()` function — extend with categories).

---

## 9. Safe Ordering / Phased Archive Plan

### Phase 0 (Pre-requisite) — Extract shared symbols

1. **Extract `is_faiz_interaction` from `commands.py`** into a new file `src/discord/_auth_guard.py` (or similar). All 31 `cmd_*.py` importers must be updated to `from ._auth_guard import is_faiz_interaction`.

2. **Extract `command_categories` and `command_count`** from `commands.py` into a new file `src/discord/_command_registry.py`. Update `cmd_help.py` and `help.py` (hermes_plugins) to import from the new location.

3. **Extract `_embed_helpers` functions** into a standalone utility (e.g., `src/discord/_embed_utils.py`) that does NOT get archived. Update all 22 `cmd_*.py` importers.

4. **Create `src/hermes/_adapter.py`** that hosts the `get_adapter()` singleton and `HermesSessionAdapter` import. Update `hermes/__init__.py` to re-export from there.

### Phase 1 — Archive standalone files with no external deps

1. `guild_setup.py` (D05) — only depended on by `permissions.py` (D04, also deprecated).
2. `permissions.py` (D04) — no external source imports outside deprecated set.
3. `intents.py` (D08) — must wait until `bot.py` (D01) no longer imports `get_intents()`.

### Phase 2 — Archive files after replacement wired

4. `startup.py` (D06) — wait until `bot.py` (D01) no longer imports `startup.on_ready()`.
5. `_embed_helpers.py` (D07) — after extraction to `_embed_utils.py`.
6. `commands.py` (D03) — after extracting `is_faiz_interaction` and `command_categories`.

### Phase 3 — Archive the Hermes adapter/bridge

7. `session_adapter.py` (D09) — after `get_adapter()` is moved to `_adapter.py`.
8. `memory_bridge.py` (D10) — after `hermes/__init__.py` no longer re-exports it AND `hermes_conversational.py` and `conversational_handler.py` no longer import it.

### Phase 4 — Archive the old handler and bot

9. `conversational_handler.py` (D02) — after `bot.py` (D01) is updated to use `hermes_conversational.py`.
10. `bot.py` (D01) — **LAST.** Only after ALL other dependents are resolved and the new Hermes-native bot entrypoint is ready.

**Total minimum pre-archive refactoring steps: 5 internal extractions + 31+ import path updates.**

---

## 10. Hard Blockers

### RED HARD BLOCKER #1 — `_embed_helpers.py` is imported by 22 active cmd_*.py files

No `cmd_*.py` file can function without it. Must extract embed helpers first.

**Evidence:** `src/discord/cmd_*.py` files at lines 16-22 each do `from ._embed_helpers import ...`.

### RED HARD BLOCKER #2 — `commands.py` exports `is_faiz_interaction` used by 31 cmd_*.py files

This is the authorization gate for virtually every command. Cannot archive without extracting it.

**Evidence:** 31 `cmd_*.py` files do `from .commands import is_faiz_interaction` in their callback functions.

### RED HARD BLOCKER #3 — `commands.py` exports `command_categories` used by Hermes plugin help system

Archiving `commands.py` breaks the Hermes CLI `/help` command.

**Evidence:** `src/hermes_plugins/commands_high/help.py:72` does `from src.discord.commands import command_categories`.

### RED HARD BLOCKER #4 — `bot.py` actively imports `intents`, `startup`, and `conversational_handler`

The main bot runtime (`GuinevereBot`) depends on all three. Cannot archive any until `bot.py` is replaced.

**Evidence:** `src/discord/bot.py` lines 24 (intents), 489 (startup), 523 (conversational_handler).

### RED HARD BLOCKER #5 — `hermes/__init__.py` re-exports both `HermesSessionAdapter` and `HermesMemoryBridge`

Six external files depend on `get_adapter()` which comes from `hermes/__init__.py`. Archiving either D09 or D10 breaks the re-export chain.

**Evidence:** `src/hermes/__init__.py` lines 11-12, 43.

### YELLOW SOFT BLOCKER — 5 test files will fail after archive

| Test File | Who Fails | Why |
|---|---|---|
| `tests/discord/test_bot.py` | D01, D03, D06 | Imports bot, startup, commands |
| `tests/discord/test_startup.py` | D06 | 100% about startup.py |
| `tests/discord/test_conversational_handler.py` | D02 | Imports and patches conversational_handler |
| `tests/discord/test_cmd_mood.py` | D03 | Tests `command_count()` from commands |
| `tests/hermes/test_memory_bridge.py` | D10 | Tests `HermesMemoryBridge` |

---

## 11. Can `pytest tests/` Pass After Archive?

**Answer: NO — without significant test modifications.**

| Test Result | Count |
|---|---|
| Tests that WILL FAIL after archive | 5 files (test_bot, test_startup, test_conversational_handler, test_cmd_mood, test_memory_bridge) |
| Tests that may pass | All others (no direct dependency on deprecated files) |

### Failure modes:

```python
# test_bot.py:32 -> ImportError
from src.discord.bot import GuinevereBot  # D01 archived -> ImportError

# test_startup.py:18 -> ImportError
from src.discord.startup import (...)  # D06 archived -> ImportError

# test_conversational_handler.py:18 -> ImportError
from src.discord.conversational_handler import (...)  # D02 archived -> ImportError

# test_cmd_mood.py:273 -> ImportError
from src.discord.commands import command_count  # D03 archived -> ImportError

# test_memory_bridge.py:15 -> ImportError
from src.hermes.memory_bridge import HermesMemoryBridge  # D10 archived -> ImportError
```

### Required test actions BEFORE archive:

| Test File | Action | Effort |
|---|---|---|
| `tests/discord/test_bot.py` | Rewrite to test replacement bot or archive with D01 | Medium |
| `tests/discord/test_startup.py` | Archive with D06 (tests are 100% about deprecated file) | Low |
| `tests/discord/test_conversational_handler.py` | Rewrite to target `hermes_conversational.py` | High |
| `tests/discord/test_cmd_mood.py` | Replace `command_count()` with local constant | Low |
| `tests/hermes/test_memory_bridge.py` | Archive with D10 or rewrite against new memory provider | Medium |

---

## Appendices

### Appendix A: KEEP ACTIVE Verification

`src/core/services/llm_router.py` — Verified: **ZERO** imports or references to any of the 10 deprecated files. Safe to keep active. No changes needed. **Confirmed KEEP ACTIVE.**

### Appendix B: Complete Reference Index

All 73 cross-references have been cataloged above. Search patterns executed:
- `from src.discord` — 30 matches in 12 files
- `import src.discord` — 7 matches in 1 file
- `from .discord` — 0 matches (no such pattern exists)
- `HermesSessionAdapter` — 26 matches in 5 files
- `HermesMemoryBridge` — 28 matches in 6 files
- `from src.hermes import get_adapter` — 6 matches in 6 files
- `_embed_helpers` — 22 matches in 22 files
- `from ._embed_helpers` — 22 matches in 22 files
- `is_faiz_interaction` — 32 matches in 32 cmd files
- `command_categories` — 3 matches in 3 files
- `get_intents` — 3 matches in 2 files
- `from .startup` — 1 match in bot.py
- `from .conversational_handler` — 1 match in bot.py

### Appendix C: Implementation Notes

**Warning:** The directory `src/_deprecated/` does **NOT** currently exist. It must be created before any `git mv`.

**Pre-archive checklist:**

1. [ ] Extract `is_faiz_interaction` from `commands.py` into `_auth_guard.py`
2. [ ] Extract `command_categories`/`command_count` into `_command_registry.py`
3. [ ] Extract `_embed_helpers` into `_embed_utils.py`
4. [ ] Create `_adapter.py` in `src/hermes/`
5. [ ] Update `hermes/__init__.py` to import from `_adapter.py`
6. [ ] Rewrite `bot.py` to use `hermes_conversational.py` instead of `conversational_handler.py`
7. [ ] Rewrite `tests/discord/test_conversational_handler.py` to target `hermes_conversational.py`
8. [ ] Update `tests/discord/test_cmd_mood.py` to remove `command_count()` dependency
9. [ ] Update `src/hermes_plugins/commands_high/help.py` to avoid `src.discord.commands`
10. [ ] Create `src/_deprecated/` directory
11. [ ] Run `pytest tests/` — MUST PASS before any `git mv`
12. [ ] Execute `git mv` for each file per Phase ordering above
13. [ ] Run `pytest tests/` — MUST PASS after each migration batch

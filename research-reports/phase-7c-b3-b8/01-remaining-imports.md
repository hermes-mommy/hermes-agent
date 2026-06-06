# Phase 7c B3 — Remaining Import/Test Blockers for Archive Safety

**Date**: 2026-06-06  
**Task**: Verify remaining import chains, test dependencies, and `src.hermes`/adapter path cleanliness after Phase 7c safe-subset (S1/S2)  
**Verdict**: **ARCHIVE REMAINS BLOCKED** — 10 RED blockers, 5 test files will fail, 6 of 10 deprecated files have active production import chains

---

## 1. What Phase 7c S2 Fixed (Clean)

| Item | Before S2 | After S2 | Status |
|---|---|---|---|
| `src/hermes/__init__.py` | Imported `session_adapter` (line 11) + `memory_bridge` (line 12), exported `__all__` with both | Minimal — only docstring + `from __future__ import annotations` | ✅ CLEAN |
| `src/hermes/adapter.py` | Did not exist | Created with lazy deferred `session_adapter` import (function-local, not module-level) | ✅ CLEAN |
| `get_adapter()` callers (6) | `from src.hermes import get_adapter` | `from src.hermes.adapter import get_adapter` | ✅ CLEAN |
| `help.py` (hermes_plugins) | `from src.discord.commands import command_categories` | `from src.hermes_plugins.command_catalog import command_categories` | ✅ CLEAN |
| `from src.hermes import X` in active src | 6 matches (`get_adapter`) | 0 matches | ✅ CLEAN |

### Verified Clean: `src/hermes/__init__.py`

```python
"""..."""
from __future__ import annotations
# No imports of session_adapter, memory_bridge, or any deprecated module
```

### Verified Clean: `src/hermes/adapter.py`

```python
# TYPE_CHECKING block only for type annotation (line 24)
if TYPE_CHECKING:
    from .session_adapter import HermesSessionAdapter

# Real import is deferred inside get_adapter() function body (line 40)
def get_adapter() -> "HermesSessionAdapter":
    if _adapter_instance is None:
        from .session_adapter import HermesSessionAdapter  # lazy
        _adapter_instance = HermesSessionAdapter(...)
    return _adapter_instance
```

---

## 2. Deprecated Files (All 10 Still Exist — No Archive Performed)

| # | File | Still Exists | Still Has Active Imports |
|---|---|---|---|
| D01 | `src/discord/bot.py` | ✅ Yes | ✅ YES — entrypoint |
| D02 | `src/discord/conversational_handler.py` | ✅ Yes | ✅ YES |
| D03 | `src/discord/commands.py` | ✅ Yes | ✅ YES — 32 active callers |
| D04 | `src/discord/permissions.py` | ✅ Yes | ⚠️ Only from D05 (deprecated→deprecated) |
| D05 | `src/discord/guild_setup.py` | ✅ Yes | ⚠️ Only from D04 (deprecated→deprecated) |
| D06 | `src/discord/startup.py` | ✅ Yes | ✅ YES |
| D07 | `src/discord/_embed_helpers.py` | ✅ Yes | ✅ YES — 22 active callers |
| D08 | `src/discord/intents.py` | ✅ Yes | ✅ YES |
| D09 | `src/hermes/session_adapter.py` | ✅ Yes | ⚠️ Only via lazy import in `adapter.py` |
| D10 | `src/hermes/memory_bridge.py` | ✅ Yes | ✅ YES — 2 active callers |

---

## 3. RED HARD BLOCKERS — Production Import Chains

### Blocker B3.1 — `_embed_helpers.py` (D07) ← 22 `cmd_*.py` files

Every `cmd_*.py` command file imports embed-building functions from `_embed_helpers.py` via relative import:

| File | Line | Import |
|---|---|---|
| `cmd_approve.py` | 16 | `from ._embed_helpers import (...)` |
| `cmd_approve_all.py` | 16 | `from ._embed_helpers import (...)` |
| `cmd_backup_now.py` | 18 | `from ._embed_helpers import (...)` |
| `cmd_casual.py` | 17 | `from ._embed_helpers import (...)` |
| `cmd_clear_cache.py` | 20 | `from ._embed_helpers import (...)` |
| `cmd_consent.py` | 22 | `from ._embed_helpers import (...)` |
| `cmd_cost_alert.py` | 18 | `from ._embed_helpers import (...)` |
| `cmd_deny.py` | 16 | `from ._embed_helpers import (...)` |
| `cmd_evidence.py` | 19 | `from ._embed_helpers import (...)` |
| `cmd_focus.py` | 17 | `from ._embed_helpers import (...)` |
| `cmd_health_check.py` | 18 | `from ._embed_helpers import (...)` |
| `cmd_history.py` | 17 | `from ._embed_helpers import (...)` |
| `cmd_loops.py` | 16 | `from ._embed_helpers import (...)` |
| `cmd_loop_pause.py` | 16 | `from ._embed_helpers import (...)` |
| `cmd_loop_priority.py` | 16 | `from ._embed_helpers import (...)` |
| `cmd_loop_resume.py` | 16 | `from ._embed_helpers import (...)` |
| `cmd_memory_export.py` | 19 | `from ._embed_helpers import (...)` |
| `cmd_memory_forget.py` | 19 | `from ._embed_helpers import (...)` |
| `cmd_new_session.py` | 17 | `from ._embed_helpers import (...)` |
| `cmd_punishment.py` | 22 | `from ._embed_helpers import (...)` |
| `cmd_restart_service.py` | 20 | `from ._embed_helpers import (...)` |
| `cmd_reward.py` | 21 | `from ._embed_helpers import (...)` |

**22 files, 22 import sites.** This is the largest single blocker.

---

### Blocker B3.2 — `commands.py` (D03) ← 31 `cmd_*.py` files (`is_faiz_interaction`)

Each command uses `from .commands import is_faiz_interaction` then calls `is_faiz_interaction(interaction)` as an authorization gate. Files include all `cmd_*.py` in `src/discord/`.

Confirmed active import sites (abstracted):

```
cmd_approve.py:36          cmd_approve_all.py:36     cmd_backup_now.py:39
cmd_budget.py:526          cmd_casual.py:43          cmd_clear_cache.py:45
cmd_consent.py:69          cmd_cost.py:582           cmd_cost_alert.py:137
cmd_deny.py:36             cmd_evidence.py:127       cmd_focus.py:50
cmd_health_check.py:129    cmd_help.py:354           cmd_history.py:49
cmd_loops.py:92            cmd_loop_pause.py:36      cmd_loop_priority.py:44
cmd_loop_resume.py:37      cmd_loop_start.py:327     cmd_loop_stop.py:375
cmd_memory_add.py:338      cmd_memory_export.py:203  cmd_memory_forget.py:135
cmd_memory_search.py:358   cmd_mood.py:378           cmd_new_session.py:36
cmd_punishment.py:84       cmd_restart_service.py:53 cmd_reward.py:68
cmd_safeword.py:557        cmd_status.py:380
```

**31 files, 31+ import sites.** All use relative `.commands` import (not absolute).

---

### Blocker B3.3 — `commands.py` (D03) ← `cmd_help.py:279` (`command_categories`)

```python
# src/discord/cmd_help.py:279
from .commands import command_categories
```

Used to build the interactive help command response. Cannot archive `commands.py` until `command_categories` is extracted to non-deprecated location.

---

### Blocker B3.4 — `commands.py` (D03) ← `bot.py:203` (`COMMAND_SPECS`)

```python
# src/discord/bot.py:203
from . import commands as cmds
# line 416: for spec in cmds.COMMAND_SPECS:
```

`bot.py` imports the entire `commands.py` module to iterate `COMMAND_SPECS` for stub command registration. This is a top-level module import, not deferred.

---

### Blocker B3.5 — `bot.py` (D01) ← `intents.py` (D08), `startup.py` (D06), `conversational_handler.py` (D02)

```python
# src/discord/bot.py:24
from .intents import get_intents

# src/discord/bot.py:489
from .startup import on_ready as startup_on_ready

# src/discord/bot.py:523
from .conversational_handler import handle_conversation
```

All three are top-level or function-level imports. `bot.py` is the runtime entrypoint — cannot archive until these are refactored.

---

### Blocker B3.6 — `hermes_conversational.py:132` ← `memory_bridge.py` (D10)

```python
# src/discord/hermes_conversational.py:132
from src.hermes.memory_bridge import HermesMemoryBridge
```

The replacement conversational handler (`hermes_conversational.py`) still imports `HermesMemoryBridge` directly. This is a `_deprecated` candidate file that is **not** itself deprecated but imports a deprecated file.

---

### Blocker B3.7 — `conversational_handler.py:155` ← `memory_bridge.py` (D10)

```python
# src/discord/conversational_handler.py:155
from src.hermes.memory_bridge import HermesMemoryBridge  # noqa: WPS301
```

The old handler also imports from `memory_bridge`.

---

## 4. YELLOW SOFT BLOCKERS — Inter-deprecated Chains

### Blocker B3.8 — `permissions.py` (D04) ← `guild_setup.py` (D05)

```python
# src/discord/permissions.py:18
from src.discord.guild_setup import CHANNELS, get_token
```

Both D04 and D05 are in the deprecated set. No **external** (non-deprecated) source imports either file. These can be archived together after other blockers resolved.

---

## 5. Test File Blockers (5 Files Will Fail)

| # | Test File | Line | Import | Dep On | Action Needed |
|---|---|---|---|---|---|
| T1 | `tests/discord/test_bot.py` | 32 | `from src.discord.bot import GuinevereBot` | D01 | Rewrite or archive with D01 |
| T1 | `tests/discord/test_bot.py` | 167 | `import src.discord.startup` | D06 | Rewrite or archive with D01 |
| T1 | `tests/discord/test_bot.py` | 171 | `import src.discord.commands` | D03 | Rewrite or archive with D01 |
| T1 | `tests/discord/test_bot.py` | 172 | `src.discord.commands.command_count()` | D03 | Rewrite or archive with D01 |
| T1 | `tests/discord/test_bot.py` | 260, 269 | `from src.discord.bot import main` | D01 | Rewrite or archive with D01 |
| T1 | `tests/discord/test_bot.py` | 295 | `from src.discord import bot` | D01 | Rewrite or archive with D01 |
| T2 | `tests/discord/test_startup.py` | 18 | `from src.discord.startup import (...)` | D06 | Archive with D06 |
| T2 | `tests/discord/test_startup.py` | 289, 303, 318, 334, 349 | `from src.discord.startup import on_ready` | D06 | Archive with D06 |
| T2 | `tests/discord/test_startup.py` | 369 | `import src.discord.startup` | D06 | Archive with D06 |
| T3 | `tests/discord/test_conversational_handler.py` | 18 | `from src.discord.conversational_handler import (...)` | D02 | Rewrite to target `hermes_conversational.py` |
| T3 | `tests/discord/test_conversational_handler.py` | 234 | `from src.discord.conversational_handler import _is_rate_limited` | D02 | Rewrite to target `hermes_conversational.py` |
| T4 | `tests/discord/test_cmd_mood.py` | 273 | `from src.discord.commands import command_count` | D03 | Replace `command_count()` with local constant |
| T5 | `tests/hermes/test_memory_bridge.py` | 15 | `from src.hermes.memory_bridge import HermesMemoryBridge` | D10 | Archive with D10 or rewrite |

---

## 6. Summary: What Must Happen Before Archive

### Phase 0 Pre-requisite Extractions (5 items)

| Step | Extract From → To | Files to Update | Risk |
|---|---|---|---|
| 1 | `_embed_helpers.py` (D07) → `_embed_utils.py` | 22 `cmd_*.py` files | HIGH — 22 import paths |
| 2 | `is_faiz_interaction` from `commands.py` (D03) → `_auth_guard.py` | 31 `cmd_*.py` files | HIGH — 31 import paths |
| 3 | `command_categories` + `command_count` + `COMMAND_SPECS` from `commands.py` (D03) → `_command_registry.py` | `cmd_help.py`, `bot.py`, `test_cmd_mood.py`, `test_bot.py` | MEDIUM |
| 4 | `HermesMemoryBridge` usage in `hermes_conversational.py` to new memory provider | `hermes_conversational.py` | MEDIUM |
| 5 | `get_adapter` chain is already clean (S2) | None needed | ✅ DONE |

### Red Blocker Count: 10

| Blocker | File | Active Importers | Severity |
|---|---|---|---|
| B3.1 | `_embed_helpers.py` (D07) | 22 cmd_*.py | RED |
| B3.2 | `commands.py` `is_faiz_interaction` (D03) | 31 cmd_*.py | RED |
| B3.3 | `commands.py` `command_categories` (D03) | `cmd_help.py:279` | RED |
| B3.4 | `commands.py` `COMMAND_SPECS` (D03) | `bot.py:203,416` | RED |
| B3.5 | `intents.py` (D08) | `bot.py:24` | RED |
| B3.5 | `startup.py` (D06) | `bot.py:489` | RED |
| B3.5 | `conversational_handler.py` (D02) | `bot.py:523` | RED |
| B3.6 | `memory_bridge.py` (D10) | `hermes_conversational.py:132` | RED |
| B3.7 | `memory_bridge.py` (D10) | `conversational_handler.py:155` | RED |
| B3.8 | `guild_setup.py` (D05) → `permissions.py` (D04) | Inter-deprecated chain | YELLOW |

### Test Files That Will Fail: 5

| Test | Import | Fails On Archive Of |
|---|---|---|
| `test_bot.py` | D01, D03, D06 | bot.py, commands.py, or startup.py |
| `test_startup.py` | D06 | startup.py |
| `test_conversational_handler.py` | D02 | conversational_handler.py |
| `test_cmd_mood.py` | D03 (command_count) | commands.py |
| `test_memory_bridge.py` | D10 | memory_bridge.py |

---

## 7. Previously Reported vs Current State Delta

Compared to the Phase 7c import-deps report (`research-reports/phase-7c-execution/01-import-deps.md`):

| Item | Previously Reported | Current State | Change |
|---|---|---|---|
| `src/hermes/__init__.py` re-exports | Lines 11-12 imported D09, D10 | Clean — no deprecated imports | ✅ FIXED |
| `get_adapter()` callers pattern | `from src.hermes import get_adapter` (6 callers) | `from src.hermes.adapter import get_adapter` (6 callers) | ✅ FIXED |
| `help.py` (hermes_plugins) `command_categories` | `from src.discord.commands import command_categories` (line 72) | `from src.hermes_plugins.command_catalog import command_categories` (line 13) | ✅ FIXED |
| All 10 deprecated files exist | Yes | Yes | ✅ UNCHANGED |
| 22 `cmd_*.py` ← `_embed_helpers` | Yes | Yes | ❌ UNCHANGED |
| 31 `cmd_*.py` ← `is_faiz_interaction` | Yes | Yes | ❌ UNCHANGED |
| `cmd_help.py:279` ← `command_categories` | Yes | Yes | ❌ UNCHANGED |
| `bot.py:203` ← `commands.py` module | Yes | Yes | ❌ UNCHANGED |
| `bot.py:24` ← `intents.py` | Yes | Yes | ❌ UNCHANGED |
| `bot.py:489` ← `startup.py` | Yes | Yes | ❌ UNCHANGED |
| `bot.py:523` ← `conversational_handler.py` | Yes | Yes | ❌ UNCHANGED |
| `hermes_conversational.py:132` ← `memory_bridge.py` | Yes | Yes | ❌ UNCHANGED |
| `from src.discord.commands import` (absolute) | 1 match (`help.py:72`) | 0 matches | ✅ FIXED (relative import unaffected) |
| `_deprecated/` directory | Did not exist | Still does not exist | ✅ UNCHANGED |

---

## 8. Verdict

**ARCHIVE REMAINS BLOCKED.** Phase 7c safe-subset S2 successfully cleaned the `src.hermes` package init and adapter path (2 items fixed), but all 10 RED hard blockers remain unresolved. The 5 test file dependencies are unchanged from the initial import-deps report.

No archive work can proceed until:
1. `_embed_helpers.py` (D07) symbols are extracted to a non-deprecated file (22 callers).
2. `commands.py` (D03) `is_faiz_interaction` (31 callers), `command_categories` (2 callers), and `COMMAND_SPECS` (1 caller) are extracted.
3. `bot.py` (D01) is updated to stop importing `intents.py` (D08), `startup.py` (D06), and `conversational_handler.py` (D02).
4. `memory_bridge.py` (D10) import is removed from `hermes_conversational.py`.
5. 5 test files are rewritten or slated for archive alongside their source.

**ADR-035 IMPLEMENTED: NO. Phase 7 complete: NO.**

---

## Appendix: Evidence Files Read

| File | Path |
|---|---|
| Import-cleanup audit | `docs/setup-evidence/hermes-migration/phase-7c/AUDIT-import-cleanup.md` |
| Archive-integrity audit | `docs/setup-evidence/hermes-migration/phase-7c/AUDIT-archive-integrity.md` |
| Import-deps report | `research-reports/phase-7c-execution/01-import-deps.md` |
| `__init__.py` | `src/hermes/__init__.py` |
| `adapter.py` | `src/hermes/adapter.py` |
| `bot.py` | `src/discord/bot.py` |
| `commands.py` | `src/discord/commands.py` |
| `conversational_handler.py` | `src/discord/conversational_handler.py` |
| `hermes_conversational.py` | `src/discord/hermes_conversational.py` |
| `cmd_help.py` | `src/discord/cmd_help.py` |
| `help.py` (hermes_plugins) | `src/hermes_plugins/commands_high/help.py` |
| `_embed_helpers.py` | `src/discord/_embed_helpers.py` |
| `test_memory_bridge.py` | `tests/hermes/test_memory_bridge.py` |

---

## Footer

Generated by Sisyphus for Guinevere ADR-035 Phase 7c B3/B8 session. Read-only investigation. No files modified.

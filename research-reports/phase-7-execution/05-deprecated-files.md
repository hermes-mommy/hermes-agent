# Phase 7 — Deprecated Files Inventory & Archive Readiness Report

> **Date:** 2026-06-06
> **Author:** Guinevere (automated inventory)
> **Scope:** Files slated for git mv to src/_deprecated/hermes-migration-phase-7/
> **Exclusion:** src/core/services/llm_router.py **must remain active**

---

## 1. File Inventory & Line Counts

| # | File | Lines | Status |
|---|------|-------|--------|
| 1 | src/discord/bot.py | 562 | Archive |
| 2 | src/discord/conversational_handler.py | 634 | Archive |
| 3 | src/discord/commands.py | 334 | Archive |
| 4 | src/discord/permissions.py | 526 | Archive |
| 5 | src/discord/guild_setup.py | 445 | Archive |
| 6 | src/discord/startup.py | 349 | Archive |
| 7 | src/discord/_embed_helpers.py | 304 | Archive |
| 8 | src/discord/intents.py | 112 | Archive |
| 9 | src/hermes/session_adapter.py | 366 | Archive |
| 10 | src/hermes/memory_bridge.py | 310 | Archive |
| 11 | src/core/services/llm_router.py | 252 | **KEEP ACTIVE** |

**Total lines to archive:** 3,842 (files 1–10)
**Total lines kept:** 252 (file 11)

---

## 2. Active Import/Reference Map

### 2.1 src/discord/bot.py — 562 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| 	ests/discord/test_bot.py:32 | rom src.discord.bot import GuinevereBot | **YES** — test will fail |
| 	ests/discord/test_bot.py:260,269 | rom src.discord.bot import main | **YES** — test will fail |

### 2.2 src/discord/conversational_handler.py — 634 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| 	ests/discord/test_conversational_handler.py:18 | rom src.discord.conversational_handler import (...) | **YES** — test will fail |
| 	ests/discord/test_conversational_handler.py:234 | rom src.discord.conversational_handler import _is_rate_limited | **YES** — test will fail |

### 2.3 src/discord/commands.py — 334 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| src/hermes_plugins/commands_high/help.py:72 | rom src.discord.commands import command_categories | **YES** — help.py will fail at runtime |
| 	ests/discord/test_cmd_mood.py:273 | rom src.discord.commands import command_count | **YES** — test will fail |
| 	ests/discord/test_bot.py:171 | import src.discord.commands | **YES** — test will fail |
| src/discord/cmd_help.py:279 | rom .commands import command_categories | **YES** — cmd_help.py will fail (also deprecated) |

### 2.4 src/discord/permissions.py — 526 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| src/discord/permissions.py:18 | rom src.discord.guild_setup import CHANNELS, get_token | Internal ref to guild_setup — mutual dependency |
| No active consumers outside file | — | — |

### 2.5 src/discord/guild_setup.py — 445 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| src/discord/permissions.py:18 | rom src.discord.guild_setup import CHANNELS, get_token | Chained — archiving both severs this link |
| No other active consumers | — | — |

### 2.6 src/discord/startup.py — 349 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| 	ests/discord/test_startup.py:18-26 | rom src.discord.startup import (...) | **YES** — test will fail |
| 	ests/discord/test_startup.py:289,303,318,334,349 | rom src.discord.startup import on_ready | **YES** — test will fail |
| 	ests/discord/test_bot.py:167 | import src.discord.startup | **YES** — test will fail |

### 2.7 src/discord/_embed_helpers.py — 304 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| 22 cmd_*.py files in src/discord/ | rom ._embed_helpers import (...) | **YES** — 22 command modules will fail |
| Full list: cmd_deny, cmd_cost_alert, cmd_consent, cmd_clear_cache, cmd_casual, cmd_backup_now, cmd_approve_all, cmd_approve, cmd_restart_service, cmd_punishment, cmd_new_session, cmd_memory_forget, cmd_memory_export, cmd_loop_resume, cmd_loop_priority, cmd_reward, cmd_loop_pause, cmd_loops, cmd_history, cmd_health_check, cmd_focus, cmd_evidence | | **ALL YES** |

### 2.8 src/discord/intents.py — 112 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| No active consumers found outside file | — | — |

### 2.9 src/hermes/session_adapter.py — 366 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| src/hermes/__init__.py:11 | rom .session_adapter import HermesSessionAdapter | **YES** — package init re-exports |
| src/hermes/__init__.py:20-40 | get_adapter() uses HermesSessionAdapter | **YES** — runtime code path |
| src/discord/hermes_conversational.py:174 | rom src.hermes import get_adapter | **YES** — via __init__ |
| src/discord/conversational_handler.py:199 | rom src.hermes import get_adapter | **YES** — via __init__ |
| src/discord/cmd_new_session.py:45 | rom src.hermes import get_adapter | **YES** — via __init__ |
| src/discord/cmd_history.py:58 | rom src.hermes import get_adapter | **YES** — via __init__ |
| src/hermes_plugins/commands_high/new_session.py:48 | rom src.hermes import get_adapter | **YES** — via __init__ |
| src/hermes_plugins/commands_high/history.py:59 | rom src.hermes import get_adapter | **YES** — via __init__ |

### 2.10 src/hermes/memory_bridge.py — 310 lines

| Importer | Import | Blocker? |
|----------|--------|----------|
| src/hermes/__init__.py:12 | rom .memory_bridge import HermesMemoryBridge | **YES** — package init re-exports |
| src/discord/hermes_conversational.py:132 | rom src.hermes.memory_bridge import HermesMemoryBridge | **YES** — direct import |
| src/discord/conversational_handler.py:155 | rom src.hermes.memory_bridge import HermesMemoryBridge | **YES** — direct import |
| 	ests/hermes/test_memory_bridge.py:15 | rom src.hermes.memory_bridge import HermesMemoryBridge | **YES** — test will fail |

### 2.11 src/core/services/llm_router.py — 252 lines — **KEEP ACTIVE**

| Importer | Import | Reason to Keep |
|----------|--------|----------------|
| src/discord/hermes_conversational.py:621 | rom src.core.services.llm_router import MODELS, TaskType | Cost tracking fallback |
| src/discord/conversational_handler.py:106 | rom src.core.services.llm_router import LLMRouter | LLM routing singleton |
| src/discord/conversational_handler.py:566 | rom src.core.services.llm_router import MODELS, TaskType | Cost tracking fallback |
| 	ests/hermes/test_llm_router_cost.py:20 | Full module import | Phase 6 cost tracking tests (373 lines) |
| 	ests/hermes/test_llm_metrics.py:175-246 | LLMRouter, metric observers | Phase 6 metrics tests |

**Rationale:** All Phase 6 CostTracker/metrics tests import from llm_router. Archiving it would break 	est_llm_router_cost.py (373 lines) and 	est_llm_metrics.py (multiple test cases). Both conversational_handler.py and hermes_conversational.py use it for cost tracking fallback.

---

## 3. Critical Dependency Blocker: src/hermes/__init__.py

`python
# Current state (lines 11-12):
from .session_adapter import HermesSessionAdapter
from .memory_bridge import HermesMemoryBridge
`

**Problem:** Archiving both session_adapter.py and memory_bridge.py without updating __init__.py will cause an ImportError at import src.hermes time. This blocks:

- get_adapter() — used by 6 modules (listed in §2.9)
- HermesMemoryBridge — used by 2 modules (listed in §2.10)
- __all__ — currently exports both

**Required fix before archive:** Rewrite src/hermes/__init__.py to remove re-exports, either:
- **Option A:** Delete the two import lines and the get_adapter() singleton (if Hermes plugin architecture fully replaces it), stripping __init__.py to minimal __future__ + docstring.
- **Option B:** Keep a stub get_adapter() that raises RuntimeError("DEPRECATED: use Hermes plugin") for fail-closed migration safety.

---

## 4. Tests That Will Break

### 4.1 Direct test-file breakage

| Test File | Depends On | Breakage |
|-----------|-----------|----------|
| 	ests/discord/test_bot.py (298 lines) | ot.py, startup.py, commands.py | 5 test methods will fail (TestHandlerImports) |
| 	ests/discord/test_startup.py (372 lines) | startup.py | 6 test methods will fail (TestOnReady, etc.) |
| 	ests/discord/test_conversational_handler.py (701 lines) | conversational_handler.py | Entire test class fails |
| 	ests/discord/test_cmd_mood.py (346 lines) | commands.py (command_count) | 1 test in TestMoodColors fails |
| 	ests/hermes/test_memory_bridge.py (330 lines) | memory_bridge.py | Entire test class fails |

**Total test lines that will break:** ~2,047

### 4.2 Transitive breakage (via __init__.py)

| Test File | Depends On | Breakage Path |
|-----------|-----------|---------------|
| 	ests/hermes/test_safety_plugin.py | src/hermes/__init__.py → session_adapter | Import guard already exists (lines 9-11 mock un_agent, edis to prevent transitive fail) |

### 4.3 Tests that survive

| Test File | Reason |
|-----------|--------|
| 	ests/hermes/test_llm_router_cost.py | Imports only llm_router.py (kept) |
| 	ests/hermes/test_llm_metrics.py | Imports only llm_metrics and llm_router (kept) |
| 	ests/surveillance/test_discord_commands.py | Imports cmd_surveillance_* only (kept) |
| 	ests/discord/test_notifications.py | Imports 
otifications only (kept) |
| 	ests/discord/test_gotify_fallback.py | Imports gotify_fallback only (kept) |
| 	ests/hermes/test_safety_plugin.py | Mocks transitive imports |

---

## 5. Hermes-Native Command Catalog Proposal for help.py

### 5.1 Current problem

`python
# src/hermes_plugins/commands_high/help.py:72
from src.discord.commands import command_categories
`

This import will fail once src/discord/commands.py is archived.

### 5.2 Proposed solution

Replace the import with a **static Hermes-native command catalog** embedded in a new module src/hermes_plugins/commands_high/_catalog.py:

`python
"""Hermes-native command catalog (replaces src.discord.commands.command_categories).

Maintained manually for the Hermes plugin surface only.
"""
from __future__ import annotations

COMMAND_CATEGORIES: dict[str, tuple[str, ...]] = {
    "core": ("status", "mood", "help", "safeword", "ping", "deny"),
    "loop": (
        "loop-start", "loop-pause", "loop-resume",
        "loop-priority", "loops", "loop-skip",
    ),
    "memory": (
        "memory-search", "memory-export", "memory-forget",
        "new", "history",
    ),
    "surveillance": (
        "surveillance-status", "surveillance-pause",
        "surveillance-resume",
    ),
    "finance": ("cost", "cost-alert", "cost-table"),
    "system": (
        "health-check", "restart-service", "restart-agent",
        "backup-now", "clear-cache", "evidence",
    ),
    "admin": ("approve", "approve-all", "reward", "punishment",
              "casual", "focus", "consent"),
}

def command_count() -> int:
    return sum(len(cmds) for cmds in COMMAND_CATEGORIES.values())
`

Then in help.py, change:
`python
# Before:
from src.discord.commands import command_categories
cats = categories if categories is not None else command_categories()

# After:
from ._catalog import COMMAND_CATEGORIES
cats = categories if categories is not None else COMMAND_CATEGORIES
`

**Benefits:**
- Zero dependency on src/discord/commands.py
- Easy to maintain: sync on command addition/removal
- Proven pattern (similar to existing _CATEGORY_DISPLAY dict)

**Note:** _catalog.py must be kept in sync with the actual slash command surface. A test in 	ests/hermes_plugins/ should assert that COMMAND_CATEGORIES matches the canonical 33-command count.

---

## 6. Archive Plan

### 6.1 Pre-requisites (ordered)

1. **Fix help.py FIRST** — Replace rom src.discord.commands import command_categories with Hermes-native catalog (_catalog.py).
2. **Update src/hermes/__init__.py** — Remove re-exports of session_adapter and memory_bridge. Replace get_adapter() with a stub or remove entirely.
3. **Create src/_deprecated/hermes-migration-phase-7/** — Directory does not exist yet.

### 6.2 Archive command

`ash
git mv src/discord/bot.py src/_deprecated/hermes-migration-phase-7/
git mv src/discord/conversational_handler.py src/_deprecated/hermes-migration-phase-7/
git mv src/discord/commands.py src/_deprecated/hermes-migration-phase-7/
git mv src/discord/permissions.py src/_deprecated/hermes-migration-phase-7/
git mv src/discord/guild_setup.py src/_deprecated/hermes-migration-phase-7/
git mv src/discord/startup.py src/_deprecated/hermes-migration-phase-7/
git mv src/discord/_embed_helpers.py src/_deprecated/hermes-migration-phase-7/
git mv src/discord/intents.py src/_deprecated/hermes-migration-phase-7/
git mv src/hermes/session_adapter.py src/_deprecated/hermes-migration-phase-7/
git mv src/hermes/memory_bridge.py src/_deprecated/hermes-migration-phase-7/
`

### 6.3 Explicit exclusions

The following **MUST NOT** be moved:
- src/core/services/llm_router.py — active, Phase 6 cost tracking & tests depend on it
- src/discord/hermes_conversational.py — replacement active handler (691 lines, depends on llm_router)

### 6.4 Post-archive validation

1. Run python -m pytest tests/hermes/test_llm_router_cost.py -v — must PASS.
2. Run python -m pytest tests/hermes/test_llm_metrics.py -v — must PASS.
3. Run python -m pytest tests/discord/ -v — expect failures (tests need updating); document pre-existing vs. new failures.
4. Run python -m pytest tests/hermes/test_memory_bridge.py -v — expect failure until test is archived with its module.
5. Verify import src.hermes raises no ImportError.
6. Verify help.py command list renders correctly via the new _catalog module.

### 6.5 Stability requirement

> **Do not delete archived files for at least 24 hours of stable operation.** Archive first (git mv), verify, then delete only after confirming no runtime issues.

---

## 7. Summary: Archive Readiness Score

| Criterion | Status | Notes |
|-----------|--------|-------|
| Line counts inventoried | ✅ | 10 files, 3,842 lines total |
| Active imports mapped | ✅ | 13 importing modules identified |
| Dependency blockers identified | ⚠️ | src/hermes/__init__.py must be patched first |
| Tests that will break identified | ✅ | 5 test files (~2,047 lines) |
| help.py import blocker identified | ✅ | command_categories import must be replaced |
| Hermes-native catalog proposed | ✅ | _catalog.py approach detailed |
| llm_router.py exclusion confirmed | ✅ | Active in 2 modules + 2 test files |
| Archive commands specified | ✅ | 10 git mv commands |
| Post-archive validation steps specified | ✅ | 6 verification commands |
| Stability requirement stated | ✅ | 24h stable before delete |

**BLOCKER:** src/hermes/__init__.py must be rewritten before archiving. Without this fix, importing src.hermes will crash.

**BLOCKER:** help.py line 72 must be fixed first (replace rom src.discord.commands with Hermes-native catalog).

---

## 8. Appendix: Net Archive Impact

| Metric | Value |
|--------|-------|
| Files moved | 10 |
| Lines removed from active tree | 3,842 |
| Lines remaining (kept) | 252 (llm_router.py only) |
| Test files requiring updates | 5 (	est_bot, 	est_startup, 	est_conversational_handler, 	est_cmd_mood, 	est_memory_bridge) |
| Source files requiring edits before archive | 2 (src/hermes/__init__.py, src/hermes_plugins/commands_high/help.py) |
| Source files requiring creation before archive | 1 (src/hermes_plugins/commands_high/_catalog.py) |
| Source files that survive unchanged | All cmd_*.py (22 files) will need _embed_helpers replacement if also migrated later |

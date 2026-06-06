# Phase 7c B3 — Deprecated Archive Readiness Verification

**Status:** BLOCKED — Archive not performed  
**Date:** 2026-06-06  
**Scope:** B3 deprecated archive readiness evidence only  
**Plan ref:** `phase-7c-b3-b8-safe-subset-plan.md` §6 (Step B3-R Scaffold)  
**ADR-035 status:** NOT IMPLEMENTED  
**Phase 7 complete:** NO  

---

## 1. Executive Summary

The deprecated archive (B3) for Phase 7c remains **fully blocked**. All 10 deprecated target files still exist in their original locations. No `git mv` archive was performed. No source or test files were moved, modified, or deleted.

| Metric | Value |
|---|---|
| Deprecated files archived | **0 of 10** |
| Production import blockers (RED) | **9** (affecting 7 files) |
| Inter-deprecated blockers (YELLOW) | **1** (affecting 2 files) |
| Test files that will break on archive | **5** |
| Tests already failing pre-archive | **1** (`test_bot.py` — stale `== 33` assertions) |
| Phase 7 tests | **139 passed** |
| `test_cmd_mood.py` | **44 passed** |
| Archive performed | **NO** |

---

## 2. Deprecated Target File Inventory

All 10 files still exist at their original paths. No files were moved to `src/_deprecated/`.

| # | File | Path | Size | Status |
|---|---|---|---|---|
| D01 | `bot.py` | `src/discord/bot.py` | Active | **BLOCKED** — runtime entrypoint |
| D02 | `conversational_handler.py` | `src/discord/conversational_handler.py` | Active | **BLOCKED** — imported by bot.py |
| D03 | `commands.py` | `src/discord/commands.py` | Active | **BLOCKED** — 32 active callers |
| D04 | `permissions.py` | `src/discord/permissions.py` | Active | **BLOCKED** — inter-dep (imports D05) |
| D05 | `guild_setup.py` | `src/discord/guild_setup.py` | Active | **BLOCKED** — inter-dep (imported by D04) |
| D06 | `startup.py` | `src/discord/startup.py` | Active | **BLOCKED** — imported by bot.py |
| D07 | `_embed_helpers.py` | `src/discord/_embed_helpers.py` | Active | **BLOCKED** — 22 cmd_*.py callers |
| D08 | `intents.py` | `src/discord/intents.py` | Active | **BLOCKED** — imported by bot.py |
| D09 | `session_adapter.py` | `src/hermes/session_adapter.py` | Active | **CANDIDATE** — only lazy imports remain |
| D10 | `memory_bridge.py` | `src/hermes/memory_bridge.py` | Active | **BLOCKED** — 2 active importers |

---

## 3. Production Import Blocker Detail

### 3.1 RED Blockers — Active Production Import Chains

#### Blocker B3.1 — `_embed_helpers.py` (D07) ← 22 `cmd_*.py` files

Every command module imports embed-building functions from `_embed_helpers.py` via relative import. Grep scan confirms **22 files, 22 import sites**.

```
from ._embed_helpers import ...
```

Files: `cmd_approve.py`, `cmd_approve_all.py`, `cmd_backup_now.py`, `cmd_casual.py`, `cmd_clear_cache.py`, `cmd_consent.py`, `cmd_cost_alert.py`, `cmd_deny.py`, `cmd_evidence.py`, `cmd_focus.py`, `cmd_health_check.py`, `cmd_history.py`, `cmd_loops.py`, `cmd_loop_pause.py`, `cmd_loop_priority.py`, `cmd_loop_resume.py`, `cmd_memory_export.py`, `cmd_memory_forget.py`, `cmd_new_session.py`, `cmd_punishment.py`, `cmd_restart_service.py`, `cmd_reward.py`

**Resolution:** Extract embed helpers to a non-deprecated file (e.g. `_embed_utils.py`) and update all 22 callers.

---

#### Blocker B3.2 — `commands.py` (D03) ← 32 files (`is_faiz_interaction`)

Grep scan confirms **32 files** import `is_faiz_interaction` from `commands.py`. This is the authorization gate function for command interactions.

```
from .commands import is_faiz_interaction
```

Files: All `cmd_*.py` files in `src/discord/` including `cmd_help.py`, `cmd_mood.py`, `cmd_budget.py`, `cmd_cost.py`, `cmd_memory_add.py`, `cmd_memory_search.py`, `cmd_safeword.py`, `cmd_status.py`, `cmd_loops.py`, `cmd_loop_start.py`, `cmd_loop_stop.py`, etc.

**Resolution:** Extract `is_faiz_interaction` to a new `_auth_guard.py` module and update all 32 callers.

---

#### Blocker B3.3 — `commands.py` (D03) ← `cmd_help.py:279` (`command_categories`)

```python
# src/discord/cmd_help.py:279
from .commands import command_categories
```

`command_categories` is used to build the interactive help command response.

**Resolution:** Extract to `_command_registry.py` or similar.

---

#### Blocker B3.4 — `commands.py` (D03) ← `bot.py:203,416` (`COMMAND_SPECS`)

```python
# src/discord/bot.py:203
from . import commands as cmds
# line 416:
for spec in cmds.COMMAND_SPECS:
```

`bot.py` imports the entire `commands.py` module for stub command registration via `COMMAND_SPECS`.

**Resolution:** Extract `COMMAND_SPECS` (and `command_count`) to `_command_registry.py`.

---

#### Blocker B3.5 — `bot.py` (D01) ← `intents.py` (D08), `startup.py` (D06), `conversational_handler.py` (D02)

```python
# src/discord/bot.py:24
from .intents import get_intents

# src/discord/bot.py:489
from .startup import on_ready as startup_on_ready

# src/discord/bot.py:523
from .conversational_handler import handle_conversation
```

`bot.py` is the runtime entrypoint. All three imports are needed for bot startup and conversation handling.

**Resolution:** Refactor `bot.py` to use Hermes-native replacements or move the dependencies.

---

#### Blocker B3.6 — `hermes_conversational.py:132` ← `memory_bridge.py` (D10)

```python
# src/discord/hermes_conversational.py:132
from src.hermes.memory_bridge import HermesMemoryBridge
```

The replacement conversational handler still imports directly from a deprecated module.

**Resolution:** Create a memory provider interface or use Hermes-native memory.

---

#### Blocker B3.7 — `conversational_handler.py:155` ← `memory_bridge.py` (D10)

```python
# src/discord/conversational_handler.py:155
from src.hermes.memory_bridge import HermesMemoryBridge
```

The old handler also imports `HermesMemoryBridge`.

**Resolution:** Same as B3.6 — both handlers need replacement memory provider.

---

### 3.2 YELLOW Blockers — Inter-Deprecated Dependencies

#### Blocker B3.8 — `permissions.py` (D04) ← `guild_setup.py` (D05)

```python
# src/discord/permissions.py:18
from src.discord.guild_setup import CHANNELS, get_token
```

Both D04 and D05 are in the deprecated set. No non-deprecated source imports either file (verified by grep: zero results for `.permissions import` anywhere in `src/discord/`). These can be archived together after other blockers are resolved.

**Resolution:** Archive D04 and D05 in the same batch.

---

### 3.3 CANDIDATE File — `session_adapter.py` (D09)

```python
# src/hermes/adapter.py:24 (TYPE_CHECKING only)
if TYPE_CHECKING:
    from .session_adapter import HermesSessionAdapter

# src/hermes/adapter.py:40 (lazy, function-local)
def get_adapter() -> "HermesSessionAdapter":
    ...
    from .session_adapter import HermesSessionAdapter  # lazy
```

`session_adapter.py` has no remaining top-level module imports. The only consumers are:
1. `adapter.py` — `TYPE_CHECKING` block (resolved at type-check time only) and deferred inside function body.
2. No direct imports in tests or production code outside the deferred adapter chain.

After S2 cleanup, `src/hermes/__init__.py` no longer imports `session_adapter`. This file is **candidate** for archive, but should be confirmed with a zero-import scan after the adapter chain is fully verified.

**Note:** `test_memory_bridge.py:8-11` has a `sys.modules` hack to prevent transitive import failure from `session_adapter`, indicating that some test paths still reference `session_adapter` indirectly.

---

## 4. Test Dependency Blocker Detail

### 4.1 Test Files Depending on Deprecated Modules

| # | Test File | Depends On | Import Sites | Status Now | Status After Archive |
|---|---|---|---|---|---|
| T1 | `tests/discord/test_bot.py` | D01, D03, D06 | 8 | **ALREADY FAILING** | BROKEN |
| T2 | `tests/discord/test_startup.py` | D06 | 8 | PASSING | BROKEN |
| T3 | `tests/discord/test_conversational_handler.py` | D02 | 3+ | PASSING | BROKEN |
| T4 | `tests/discord/test_cmd_mood.py` | D03 | 1 | **PASSING** | BROKEN |
| T5 | `tests/hermes/test_memory_bridge.py` | D10 | 1+ | PASSING | BROKEN |

### 4.2 Pre-Archive Failure in `test_bot.py`

Already failing with stale assertion values (2 sites):

```python
# test_bot.py:106
assert len(registered) == 33  # Actual: 35 commands exist

# test_bot.py:172
assert src.discord.commands.command_count() == 33  # Actual: 35
```

These assertions were never updated when `COMMAND_SPECS` grew from 33 to 35 commands. This blocks all full-suite test runs regardless of archive.

### 4.3 Clean Test Files (No Deprecated Dependencies)

| Suite | Files | Status |
|---|---|---|
| `tests/safety/` | 9 files | ✅ CLEAN |
| `tests/phase7/` | 10 files | ✅ CLEAN (139 passed) |
| `tests/hermes/` (except test_memory_bridge.py) | 10 files | ✅ CLEAN |
| `tests/discord/` (except the 4 above) | Remaining | ✅ CLEAN |

---

## 5. Required Commands — Execution Results

### Command 1: `python -m pytest tests/phase7/ -q --tb=short`

**Output:**
```
........................................................................ [ 51%]
...................................................................      [100%]
============================== warnings summary ===============================
tests/phase7/test_T10_monitoring_health.py::TestPrometheusConfig::test_prometheus_yml_exists
  C:\Users\faizz\AppData\Roaming\Python\Python314\site-packages\pytest_asyncio\plugin.py:1190: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated
    return asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
139 passed, 1 warning in 4.60s
```

**Verdict:** ✅ PASS (exit 0, 139 passed)

### Command 2: `python -m pytest tests/discord/test_cmd_mood.py -q --tb=short`

**Output:**
```
............................................                             [100%]
============================== warnings summary ===============================
tests/discord/test_cmd_mood.py::TestTitle::test_title_exact
  C:\Users\faizz\AppData\Roaming\Python\Python314\site-packages\pytest_asyncio\plugin.py:1190: DeprecationWarning: 'asyncio.get_event_loop_policy' is deprecated
    return asyncio.get_event_loop_policy()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
44 passed, 1 warning in 0.16s
```

**Verdict:** ✅ PASS (exit 0, 44 passed)

### Command 3: Import Scan Grep — Current State

**Grep pattern:** `from .intents import|from .startup import|from .conversational_handler import` in `src/discord/bot.py`

```
24: from .intents import get_intents
489: from .startup import on_ready as startup_on_ready
523: from .conversational_handler import handle_conversation
```

**Grep pattern:** `from .commands import` in `src/discord/`

```
32 files (33 matches) — all cmd_*.py files import is_faiz_interaction
cmd_help.py also imports command_categories
```

**Grep pattern:** `from ._embed_helpers import` in `src/discord/`

```
22 files (22 matches) — all cmd_*.py files import embed helpers
```

**Grep pattern:** `HermesMemoryBridge|memory_bridge` in `src/discord/`

```
2 files — hermes_conversational.py:132, conversational_handler.py:155
```

**Grep pattern:** `from src.discord.guild_setup import` in `src/discord/`

```
1 file — permissions.py:18
```

**Grep pattern:** `from src.hermes.session_adapter|from .session_adapter` in `src/`

```
1 file — adapter.py (TYPE_CHECKING at line 24, lazy at line 40)
```

---

## 6. Future Archive Gates

The following gates must all be satisfied before each deprecated file can be safely archived:

### Gate 1: Zero Production Imports

- [ ] No non-deprecated source file imports the target module.
- [ ] All import chains are fully migrated to Hermes-native or active modules.
- [ ] Verified by grep scan returning zero matches.

### Gate 2: Zero Test Dependencies or Migrated Tests

- [ ] No test file imports the target module, OR
- [ ] The test file is archived alongside its source in `tests/_deprecated/`.
- [ ] Verified by grep scan returning zero matches.

### Gate 3: Tests Pass Before Archive

- [ ] Full `pytest tests/` passes with exit code 0 ahead of archive.
- [ ] All pre-archive failures (including stale `test_bot.py` assertions) are fixed.

### Gate 4: Tests Pass After Archive

- [ ] Full `pytest tests/` passes with exit code 0 after archive.
- [ ] Any test that depended on the archived file is itself archived or migrated.

### Gate 5: Archive via `git mv`

- [ ] Source file moved to `src/_deprecated/<original_path>`.
- [ ] Test file moved to `tests/_deprecated/<original_path>` (if not migrated).
- [ ] `git mv` preserves history.

### Gate 6: README or Archive Notice

- [ ] `_deprecated/` directory has a README explaining the archive.
- [ ] Each archived file has a header comment pointing to its replacement.

### Per-File Gate Checklist

| # | File | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Gate 5 | Gate 6 |
|---|---|---|---|---|---|---|---|
| D01 | `bot.py` | ❌ — is entrypoint | ❌ — test_bot.py | ❌ — already failing | ❌ | ❌ | ❌ |
| D02 | `conversational_handler.py` | ❌ — bot.py:523 | ❌ — test_conversational_handler.py | ❌ | ❌ | ❌ | ❌ |
| D03 | `commands.py` | ❌ — 32 callers | ❌ — test_bot.py, test_cmd_mood.py | ❌ | ❌ | ❌ | ❌ |
| D04 | `permissions.py` | ⚠️ — only D05 (dep→dep) | ✅ — no test dep | ❌ | ❌ | ❌ | ❌ |
| D05 | `guild_setup.py` | ⚠️ — only D04 (dep→dep) | ✅ — no test dep | ❌ | ❌ | ❌ | ❌ |
| D06 | `startup.py` | ❌ — bot.py:489 | ❌ — test_startup.py, test_bot.py | ❌ | ❌ | ❌ | ❌ |
| D07 | `_embed_helpers.py` | ❌ — 22 cmd_*.py | ✅ — no test dep | ❌ | ❌ | ❌ | ❌ |
| D08 | `intents.py` | ❌ — bot.py:24 | ✅ — no test dep | ❌ | ❌ | ❌ | ❌ |
| D09 | `session_adapter.py` | ⚠️ — only lazy imports | ⚠️ — sys.modules hack in tests | ❌ | ❌ | ❌ | ❌ |
| D10 | `memory_bridge.py` | ❌ — hermes_conversational.py, conversational_handler.py | ❌ — test_memory_bridge.py | ❌ | ❌ | ❌ | ❌ |

**Key:**
- ❌ = Gate not satisfied
- ⚠️ = Partial / needs verification
- ✅ = Gate satisfied

---

## 7. Explicit Blocked Statement

**No `git mv` archive was performed.** All 10 deprecated files remain in their original source locations. No source code, test files, or configuration files were modified for this verification step.

B3 archive cannot proceed until:
1. `_embed_helpers.py` symbols are extracted to a non-deprecated file (22 callers)
2. `is_faiz_interaction` (32 callers), `command_categories` (2 callers), and `COMMAND_SPECS` (1 caller) are extracted from `commands.py`
3. `bot.py` is updated to stop importing `intents.py`, `startup.py`, and `conversational_handler.py`
4. `memory_bridge.py` imports are removed from `hermes_conversational.py` and `conversational_handler.py`
5. All 5 test files are migrated or slated for archive alongside their source
6. Pre-existing `test_bot.py` assertion failures (stale `== 33`) are fixed

---

## 8. Evidence Artifacts

| File | Path | Description |
|---|---|---|
| This file | `STEP-B3-READINESS/verification.md` | Archive readiness evidence |
| Plan | `../phase-7c-b3-b8-safe-subset-plan.md` | Safe-subset plan with B3 scaffold |
| Research 1 | `../../../research-reports/phase-7c-b3-b8/01-remaining-imports.md` | Remaining production import blockers |
| Research 2 | `../../../research-reports/phase-7c-b3-b8/02-test-deprecated-imports.md` | Test dependency map |

---

## 9. Boundary Compliance

| Check | Status | Notes |
|---|---|---|
| B3/Phase 7 completion claimed | ❌ NO | Explicitly blocked |
| ADR-035 IMPLEMENTED | ❌ NO | Not claimed |
| Files archived/moved | ❌ NO | All 10 files in original location |
| Secrets exposed | ✅ SAFE | No secrets touched |
| Type safety violations | ✅ NONE | No code modified |
| VPS/deploy touched | ✅ NO | Local evidence only |
| git operations | ✅ NONE | No commit, push, or deploy |

---

## 10. Footer

Generated by Sisyphus-Junior for Guinevere Phase 7c B3 safe-subset readiness evidence. Read-only investigation. No source or test files were modified.

| Field | Value |
|---|---|
| Generated | 2026-06-06 |
| Plan ref | `phase-7c-b3-b8-safe-subset-plan.md` §6 |
| Oracle verdict | PROCEED SAFE SUBSET |
| Archive performed | **NO** |
| B3 complete | **NO** |
| Phase 7 complete | **NO** |
| ADR-035 IMPLEMENTED | **NO** |

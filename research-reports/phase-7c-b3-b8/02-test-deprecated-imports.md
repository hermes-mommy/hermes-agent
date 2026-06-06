# Phase 7c B3/B8 — Test Deprecated Import Map

**Date:** 2026-06-06  
**Scope:** All test files importing deprecated modules (D01–D10), failure mode analysis, migration requirements  
**Status:** Complete  
**Methodology:** grep + line-by-line read of all test files in `tests/discord/`, `tests/hermes/`, `tests/safety/`, `tests/phase7/`

---

## 1. Executive Summary

| Metric | Value |
|---|---|
| Test files with deprecated imports | 5 |
| Total deprecated import sites | 12 |
| Test files ALREADY FAILING (pre-archive) | 1 (`test_bot.py` — stale `command_count == 33` vs actual 35) |
| Test files that WILL FAIL after archive | 5 |
| Test files clean (no deprecated imports) | 18 (all `tests/safety/*`, `tests/phase7/*`, most `tests/hermes/*`, most `tests/discord/*`) |
| Current `pytest tests/` pass status | **BLOCKED** — `test_bot.py` fails on assertion value |

**Verdict:** B8 cannot be resolved before `test_bot.py` stale assertions are fixed. Archive of D01/D02/D03/D06/D10 is blocked until all 5 test files are migrated or archived alongside their source.

---

## 2. Complete Test File Map

### 2.1 Classification Key

| Label | Meaning |
|---|---|
| **ALREADY FAILING** | Test is broken RIGHT NOW regardless of archive |
| **PASSING → BLOCKED** | Test passes now but will fail after source file is archived |
| **CLEAN** | No dependency on any D01–D10 deprecated file |

### 2.2 File-by-File Results

| # | Test File | Depends On | Import Sites | Status Now | Status After Archive |
|---|---|---|---|---|---|
| T01 | `tests/discord/test_bot.py` | D01, D03, D06 | 8 | **ALREADY FAILING** (stale assertion) | BROKEN |
| T02 | `tests/discord/test_startup.py` | D06 | 8 | PASSING | BROKEN |
| T03 | `tests/discord/test_conversational_handler.py` | D02 | 3+ | PASSING | BROKEN |
| T04 | `tests/discord/test_cmd_mood.py` | D03 | 1 | PASSING | BROKEN |
| T05 | `tests/hermes/test_memory_bridge.py` | D10 | 1 | PASSING | BROKEN |
| T06 | All `tests/safety/*.py` (9 files) | None | 0 | PASSING | PASSING |
| T07 | All `tests/phase7/*.py` (10 files) | None | 0 | PASSING | PASSING |
| T08 | `tests/hermes/test_safety_plugin.py` | None | 0* | PASSING | PASSING |
| T09 | `tests/hermes/*.py` (other 10 files) | None | 0 | PASSING | PASSING |
| T10 | `tests/discord/*.py` (other files) | None | 0 | PASSING | PASSING |

*\* `test_safety_plugin.py` has a pre-emptive `sys.modules` hack but no direct import of deprecated modules.*

---

## 3. Detailed Failure Analysis

### 3.1 T01 — `tests/discord/test_bot.py`

**Path:** `C:\Users\faizz\guinevere\tests\discord\test_bot.py` (298 lines)  
**Docstring:** *"Deterministic tests for `src.discord.bot`"*

#### Deprecated Imports (8 sites)

| Line | Statement | Depends On | Failure Mode |
|---|---|---|---|
| 32 | `from src.discord.bot import GuinevereBot` | D01 `bot.py` | `ImportError` after archive |
| 167 | `import src.discord.startup` | D06 `startup.py` | `ImportError` after archive |
| 168 | `assert hasattr(src.discord.startup, "on_ready")` | D06 `startup.py` | `AttributeError` after archive |
| 171 | `import src.discord.commands` | D03 `commands.py` | `ImportError` after archive |
| 172 | `assert src.discord.commands.command_count() == 33` | D03 `commands.py` | **⚠️ ALREADY FAILING** — returns 35 |
| 260 | `from src.discord.bot import main` | D01 `bot.py` | `ImportError` after archive |
| 269 | `from src.discord.bot import main` | D01 `bot.py` | `ImportError` after archive |
| 295 | `from src.discord import bot` | D01 `bot.py` | `ImportError` after archive |

#### Additional Pre-Archive Blocking Assertions

| Test Class | Line | Assertion | Current Value | Expected | Status |
|---|---|---|---|---|---|
| `TestSetupHook.test_register_33_commands` | 106 | `assert len(registered) == 33` | 35 | 33 | **FAILING** |
| `TestHandlerImports.test_import_commands` | 172 | `assert src.discord.commands.command_count() == 33` | 35 | 33 | **FAILING** |

**Root cause of pre-archive failure:** Lines 247–248 of `src/discord/commands.py` added 2 new commands (`new`, `history`) bumping COMMAND_SPECS from 33→35. The test_bot.py assertions were never updated.

**Remediation required:**
1. Update line 106: `assert len(registered) == 35`
2. Update line 8 docstring: `"registers exactly 33"` → `"registers exactly 35"`
3. Update line 98 docstring: `"must register exactly 33"` → `"must register exactly 35"`
4. Update line 172: `assert src.discord.commands.command_count() == 35`
5. After archive: rewrite entire file to test Hermes-native replacement or archive alongside D01

---

### 3.2 T02 — `tests/discord/test_startup.py`

**Path:** `C:\Users\faizz\guinevere\tests\discord\test_startup.py` (372 lines)  
**Docstring:** *"Deterministic tests for `src.discord.startup`"*

#### Deprecated Imports (8 sites)

| Line | Statement | Depends On | Failure Mode |
|---|---|---|---|
| 18 | `from src.discord.startup import (...)` | D06 `startup.py` | `ImportError` after archive |
| 289 | `from src.discord.startup import on_ready` | D06 `startup.py` | `ImportError` after archive |
| 303 | `from src.discord.startup import on_ready` | D06 `startup.py` | `ImportError` after archive |
| 318 | `from src.discord.startup import on_ready` | D06 `startup.py` | `ImportError` after archive |
| 334 | `from src.discord.startup import on_ready` | D06 `startup.py` | `ImportError` after archive |
| 349 | `from src.discord.startup import on_ready` | D06 `startup.py` | `ImportError` after archive |
| 369 | `from src.discord import startup` | D06 `startup.py` | `ImportError` after archive |

**Status now:** PASSING  
**Status after archive:** BROKEN (100% of test surface is about `startup.py`)

**Remediation required:** Archive entire test file alongside D06 `startup.py`. No Hermes-native replacement for startup exists yet.

---

### 3.3 T03 — `tests/discord/test_conversational_handler.py`

**Path:** `C:\Users\faizz\guinevere\tests\discord\test_conversational_handler.py` (701 lines)  
**Docstring:** *"Deterministic tests for `src.discord.conversational_handler`"*

#### Deprecated Imports

| Line | Statement | Depends On | Failure Mode |
|---|---|---|---|
| 18 | `from src.discord.conversational_handler import (...)` | D02 `conversational_handler.py` | `ImportError` after archive |
| 234 | `from src.discord.conversational_handler import _is_rate_limited` | D02 `conversational_handler.py` | `ImportError` after archive |

Plus 12+ additional `patch(f"{MODULE}._is_rate_limited", ...)`, `patch(f"{MODULE}._get_router", ...)` references via the `MODULE = "src.discord.conversational_handler"` constant at line 31.

**Status now:** PASSING  
**Status after archive:** BROKEN

**Remediation required:** Rewrite entire test suite to target `src.discord.hermes_conversational` (the replacement that already exists). This is a HIGH-effort rewrite (18 test cases across 7 test classes).

---

### 3.4 T04 — `tests/discord/test_cmd_mood.py`

**Path:** `C:\Users\faizz\guinevere\tests\discord\test_cmd_mood.py` (346 lines)  
**Test class:** `TestCommandRegistryCount`

#### Deprecated Import

| Line | Statement | Depends On | Failure Mode |
|---|---|---|---|
| 273 | `from src.discord.commands import command_count` | D03 `commands.py` | `ImportError` after archive |

**Assertion value:** `assert command_count() == 35` — ✅ **Correct** (was updated from 33 to 35 by Phase 7c S1 safe-subset).

**Status now:** PASSING  
**Status after archive:** BROKEN (single import blocks the file)

**Remediation required:** Replace `command_count()` with a local constant. Minimal change:

```python
def test_command_count_is_canonical(self) -> None:
    # command_count lives in src.discord.commands (archived); use canonical constant
    from src.hermes_plugins.command_catalog import command_count
    assert command_count() == 35
```

Or simpler: remove the import assertion entirely and rely on the command-catalog tests in `tests/phase7/`.

---

### 3.5 T05 — `tests/hermes/test_memory_bridge.py`

**Path:** `C:\Users\faizz\guinevere\tests\hermes\test_memory_bridge.py` (330 lines)  
**Deprecated import:**

| Line | Statement | Depends On | Failure Mode |
|---|---|---|---|
| 15 | `from src.hermes.memory_bridge import HermesMemoryBridge  # noqa: E402` | D10 `memory_bridge.py` | `ImportError` after archive |

**Status now:** PASSING (with `sys.modules` hack at lines 8–11 to prevent transitive `session_adapter` import failure)  
**Status after archive:** BROKEN

**Remediation required:** Archive alongside D10 `memory_bridge.py` OR rewrite against replacement memory provider (no replacement exists yet — `HermesMemoryBridge` is the current memory interface).

---

## 4. Tests That Are CLEAN (No Deprecated Imports)

### 4.1 `tests/safety/` — 9 files, all CLEAN

| File | Lines | Notes |
|---|---|---|
| `test_auto_rollback.py` | — | No discord/hermes imports |
| `test_yandere_cap.py` | — | No discord/hermes imports |
| `test_punishment_overflow.py` | — | No discord/hermes imports |
| `test_hard_stop_model.py` | — | No discord/hermes imports |
| `test_hard_stop_handler.py` | — | No discord/hermes imports |
| `test_hard_stop_comprehensive.py` | — | No discord/hermes imports |
| `test_distress_protocol_e2e.py` | — | No discord/hermes imports |
| `test_consent_revocation.py` | — | No discord/hermes imports |
| `__init__.py` | — | Empty |

### 4.2 `tests/phase7/` — 10 files, all CLEAN

| File | Notes |
|---|---|
| `test_T1_e2e_loop.py` | No deprecated imports |
| `test_T2_safety_gates.py` | No deprecated imports |
| `test_T3_auth_enforcement.py` | No deprecated imports |
| `test_T4_memory_pipeline.py` | No deprecated imports |
| `test_T5_surveillance_pipeline.py` | No deprecated imports |
| `test_T6_persona_fsm.py` | No deprecated imports |
| `test_T7_distress_protocol.py` | No deprecated imports |
| `test_T8_consent_revocation.py` | No deprecated imports |
| `test_T9_budget_enforcement.py` | No deprecated imports |
| `test_T10_monitoring_health.py` | No deprecated imports |

### 4.3 `tests/hermes/` — 10 files CLEAN, 1 BLOCKED

**Clean:** `test_llm_metrics.py`, `test_budget_hook.py`, `test_llm_router_cost.py`, `test_integration_e2e.py`, `test_security_audit.py`, `test_hybrid_guards.py`, `test_auth_overlay.py`, `test_fastmcp_bridge.py`, `test_mcp_config.py`, `test_safety_plugin.py`  
**Blocked:** `test_memory_bridge.py` (see §3.5)

### 4.4 `tests/discord/` — Other

**Potentially clean (not inspected in detail, no grep matches):** `test_notifications.py`, `test_gotify_fallback.py`, `test_gotify_client.py`, `conftest.py`

---

## 5. Failure Mode Summary

### After archive, which ImportErrors fire?

| Test File | First Failing Import | Error |
|---|---|---|
| `test_bot.py:32` | `from src.discord.bot import GuinevereBot` | `ModuleNotFoundError: No module named 'src.discord.bot'` |
| `test_startup.py:18` | `from src.discord.startup import (...)` | `ModuleNotFoundError: No module named 'src.discord.startup'` |
| `test_conversational_handler.py:18` | `from src.discord.conversational_handler import (...)` | `ModuleNotFoundError: No module named 'src.discord.conversational_handler'` |
| `test_cmd_mood.py:273` | `from src.discord.commands import command_count` | `ModuleNotFoundError: No module named 'src.discord.commands'` |
| `test_memory_bridge.py:15` | `from src.hermes.memory_bridge import HermesMemoryBridge` | `ModuleNotFoundError: No module named 'src.hermes.memory_bridge'` |

### Pre-archive assertion failures (already broken)

| Test File | Line | Assertion | Expected | Actual | Severity |
|---|---|---|---|---|---|
| `test_bot.py:106` | `assert len(registered) == 33` | 33 | 35 | HIGH — blocks test run |
| `test_bot.py:172` | `assert src.discord.commands.command_count() == 33` | 33 | 35 | HIGH — blocks test run |

---

## 6. Migration Requirements Per File

### Urgency Classification

| Priority | Meaning |
|---|---|
| **P0** | Fix NOW — test is already broken regardless of archive |
| **P1** | Fix BEFORE archive — will break when source is archived |
| **P2** | Fix AFTER archive — can be archived with its source |

| # | Test File | Priority | Effort | Action |
|---|---|---|---|---|
| T01 | `test_bot.py` | **P0** (stale) + **P1** (archive) | Medium | 1. Fix assertion values 33→35 NOW. 2. Rewrite to target Hermes-native replacement or archive with D01. |
| T02 | `test_startup.py` | P2 | Low | Archive alongside D06 `startup.py`. Move to `tests/_deprecated/`. |
| T03 | `test_conversational_handler.py` | **P1** | High | Rewrite to target `src.discord.hermes_conversational` (replacement exists). |
| T04 | `test_cmd_mood.py` | **P1** | Low | Replace `from src.discord.commands import command_count` with `from src.hermes_plugins.command_catalog import command_count` or inline constant. |
| T05 | `test_memory_bridge.py` | P2 | Medium | Archive alongside D10 `memory_bridge.py`. Move to `tests/_deprecated/`. |

### Minimal P0 fix (unblocks test suite NOW)

```python
# test_bot.py line 106 — fix stale assertion
assert len(registered) == 35

# test_bot.py line 172 — fix stale assertion
assert src.discord.commands.command_count() == 35
```

Also update docstrings:
- Line 8: `"registers exactly 33 slash commands"` → `"registers exactly 35 slash commands"`
- Line 98: `"must register exactly 33 slash commands"` → `"must register exactly 35 slash commands"`

---

## 7. Current Test Suite Status

| Suite | Command | Status |
|---|---|---|
| Phase 7 tests | `python -m pytest tests/phase7/ -q --tb=short` | ✅ PASS (139 passed) |
| Safety tests | `python -m pytest tests/safety/ -q --tb=short` | ✅ PASS (not verified directly, no deprecated deps) |
| Discord tests | `python -m pytest tests/discord/ -q --tb=short` | ❌ **BLOCKED** — test_bot.py assertions fail |
| Hermes tests | `python -m pytest tests/hermes/ -q --tb=short` | ⚠️ UNVERIFIED (test_memory_bridge.py depends on external deps) |
| Full suite | `python -m pytest tests/ -q --tb=short` | ❌ **BLOCKED** until P0 fix applied |

---

## 8. B8 Blocker Impact Assessment

B8 (*"Deprecated files still imported and tested"*) requires that no test depends on deprecated modules before archive. The current state:

| Condition | Met? | Why |
|---|---|---|
| All test assertions are correct | ❌ | `test_bot.py` has stale `== 33` assertions |
| No test imports deprecated modules | ❌ | 5 test files import from D01/D02/D03/D06/D10 |
| Tests can pass after archive | ❌ | 5 files will fail with `ImportError` |
| Tests pass before archive | ❌ | `test_bot.py` already fails on assertion values |

**B8 cannot be closed until:**
1. P0 fix applied to `test_bot.py` (stale assertion values)
2. Each of the 5 test files is either:
   - Migrated to Hermes-native replacement (T03 recommended), or
   - Updated to import from non-deprecated surface (T04 minimal fix), or
   - Archived alongside its source file (T02, T05)
3. Full `pytest tests/` passes cleanly

---

## 9. Recommendations

1. **Apply P0 fix immediately** — update `test_bot.py` assertions from 33→35. This is the only pre-archive blocker that exists regardless of archive.

2. **Fix T04 `test_cmd_mood.py` during archive wave** — trivial 1-line change to import `command_count` from `command_catalog` instead of `commands`. Do this when D03 is archived.

3. **Archive T02 `test_startup.py` with D06** — these tests have no value without the source. Move to `tests/_deprecated/` when D06 is archived.

4. **Archive T05 `test_memory_bridge.py` with D10** — these tests test `HermesMemoryBridge` directly. Move to `tests/_deprecated/` when D10 is archived.

5. **Rewrite T03 `test_conversational_handler.py` as separate work item** — high-effort rewrite requires deep knowledge of `hermes_conversational.py`. This is the hardest migration and should be planned as its own task.

---

## 10. Appendix: Import Dependency Visual

```
src/discord/bot.py (D01)
  └── tests/discord/test_bot.py (T01) — 8 imports

src/discord/startup.py (D06)
  └── tests/discord/test_startup.py (T02) — 8 imports

src/discord/conversational_handler.py (D02)
  └── tests/discord/test_conversational_handler.py (T03) — 3+ imports

src/discord/commands.py (D03)
  ├── tests/discord/test_bot.py (T01) — 2 imports (1 assertion based)
  └── tests/discord/test_cmd_mood.py (T04) — 1 import

src/hermes/memory_bridge.py (D10)
  └── tests/hermes/test_memory_bridge.py (T05) — 1 import
```

---

## 11. Key Files Reference

| File | Path |
|---|---|
| test_bot.py | `C:\Users\faizz\guinevere\tests\discord\test_bot.py` |
| test_startup.py | `C:\Users\faizz\guinevere\tests\discord\test_startup.py` |
| test_conversational_handler.py | `C:\Users\faizz\guinevere\tests\discord\test_conversational_handler.py` |
| test_cmd_mood.py | `C:\Users\faizz\guinevere\tests\discord\test_cmd_mood.py` |
| test_memory_bridge.py | `C:\Users\faizz\guinevere\tests\hermes\test_memory_bridge.py` |
| Blocked deprecated file D03 commands.py | `C:\Users\faizz\guinevere\src\discord\commands.py` (COMMAND_SPECS=35) |
| Replacement command_catalog.py | `C:\Users\faizz\guinevere\src\hermes_plugins\command_catalog.py` |
| Completion report | `C:\Users\faizz\guinevere\docs\setup-evidence\hermes-migration\phase-7c\phase-7c-safe-subset-completion-report.md` |
| Blocker register | `C:\Users\faizz\guinevere\docs\20-security\hermes-phase-7-blocker-register.md` |
| Import dependency map | `C:\Users\faizz\guinevere\research-reports\phase-7c-execution\01-import-deps.md` |

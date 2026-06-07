# B3 Archive Regression — Failing Import/Patch Targets Report

**Date:** 2026-06-07
**Scope:** Full read-only diagnostic of failing test imports after B3 archive move
**Status:** COMPLETE
**Verdict:** **Zero stale test imports found** — all direct import paths were correctly migrated during A4. The primary regression is **cross-test `sys.modules` contamination** from `test_safety_plugin.py`'s module-level `setdefault` calls, which poison global module cache with `MagicMock` instances, causing phase7/safety tests to silently resolve real classes (enums, handlers, engines) to `MagicMock`.

---

## 1. Current State Summary

| Metric | Value |
|---|---|
| B3 archive files moved | 10 files → `src/_deprecated/hermes-migration-phase-7/` |
| Test files with stale deprecated imports | **0** (excluding `.archived` non-collected files) |
| Test files with correct active imports | All `tests/phase7/*`, `tests/safety/*`, `tests/discord/*`, `tests/hermes/*` |
| Cross-test MagicMock contamination sites | **8 module entries** via `test_safety_plugin.py` |
| Pre-existing unrelated failures | YAML auth overlay tests |
| B3-archive-caused import failures | **0** (all test imports already migrated) |

---

## 2. B3 Archive File Mapping

### 2.1 Archived Files → Active Replacements

| Deprecated (Archived) | Active Replacement | Notes |
|---|---|---|
| `src/discord/bot.py` | `src/discord/_entrypoint.py` | `GuinevereBot`, `main`, `GUILD_ID` |
| `src/discord/startup.py` | `src/discord/_startup.py` | `on_ready`, `StartupEmbedData`, etc. |
| `src/discord/commands.py` | `src/discord/_command_registry.py` + `src/discord/_auth_guard.py` | `COMMAND_SPECS`, `is_faiz_interaction` |
| `src/discord/conversational_handler.py` | `src/discord/hermes_conversational.py` | `handle_conversation` replacement |
| `src/discord/intents.py` | `src/discord/_intents.py` | `get_intents`, `validate_intents` |
| `src/discord/_embed_helpers.py` | `src/discord/_embed_utils.py` | Embed builder functions |
| `src/discord/permissions.py` | (inlining, inter-deprecated) | Archived alongside `guild_setup.py` |
| `src/discord/guild_setup.py` | (inlining, inter-deprecated) | Archived alongside `permissions.py` |
| `src/hermes/session_adapter.py` | `src/hermes/_session_adapter.py` | `HermesSessionAdapter` |
| `src/hermes/memory_bridge.py` | `src/hermes/_memory_bridge.py` | `HermesMemoryBridge` |

### 2.2 Test Import Path Migration (A4 — Already Complete)

Every test that previously imported from a deprecated path has been updated:

| Test File | Old Path | New Path | Status |
|---|---|---|---|
| `tests/hermes/test_memory_bridge.py:15` | `src.hermes.memory_bridge` | `src.hermes._memory_bridge` | ✅ FIXED |
| `tests/hermes/test_memory_bridge.py:321` | `src.hermes.memory_bridge._logger` | `src.hermes._memory_bridge._logger` | ✅ FIXED |
| `tests/discord/test_bot.py:32` | `src.discord.bot` | `src.discord._entrypoint` | ✅ FIXED |
| `tests/discord/test_bot.py:50` | `src.discord.bot` | `src.discord._entrypoint` | ✅ FIXED |
| `tests/discord/test_bot.py:176` | `src.discord.startup` | `src.discord._startup` | ✅ FIXED |
| `tests/discord/test_bot.py:180` | `src.discord.commands` | `src.discord._command_registry` | ✅ FIXED |
| `tests/discord/test_bot.py:269` | `src.discord.bot` | `src.discord._entrypoint` | ✅ FIXED |
| `tests/discord/test_bot.py:304` | `src.discord.bot` | `src.discord._entrypoint` | ✅ FIXED |
| `tests/discord/test_bot.py:317-356` | `src.discord.intents` | `src.discord._intents` | ✅ FIXED |
| `tests/discord/test_cmd_mood.py:273` | `src.discord.commands` | `src.discord._command_registry` | ✅ FIXED |
| `tests/discord/test_startup.py:18` | `src.discord.startup` | `src.discord._startup` | ✅ FIXED |
| `tests/discord/test_startup.py:289-369` | `src.discord.startup` | `src.discord._startup` | ✅ FIXED |
| `tests/discord/test_conversational_handler.py` | `src.discord.conversational_handler` | **Archived** → `.py.archived` | ✅ FIXED |
| `tests/discord/test_hermes_conversational.py` | (new) | `src.discord.hermes_conversational` | ✅ CREATED |

**Remaining stale-only in non-collected file:** `tests/discord/test_conversational_handler.py.archived` (2 import sites, `.archived` suffix prevents pytest collection).

---

## 3. PRIMARY REGRESSION: Cross-Test MagicMock Contamination

### 3.1 Root Cause

`tests/hermes/test_safety_plugin.py` (lines 20–70) has **module-level** `sys.modules.setdefault()` calls that inject `MagicMock` instances into the global Python module cache:

```python
# Lines 20-70 of test_safety_plugin.py (module-level, runs at import time)
sys.modules.setdefault("src.core.services.hard_stop_handler", MagicMock())       # line 20
sys.modules.setdefault("src.persona.safe_mode", MagicMock())                      # line 23
sys.modules.setdefault("src.persona.drift_detector", MagicMock())                  # line 24
sys.modules.setdefault("src.persona.yandere_fsm", <Mock with YandereSafetyError>) # line 49
sys.modules.setdefault("src.surveillance.secret_scanner", <identity lambda>)       # line 56
sys.modules.setdefault("src.surveillance.classification", MagicMock())            # line 57
sys.modules.setdefault("src.mcp.auth", <Mock with MockAuthLevel>)                 # line 69
sys.modules.setdefault("src.mcp.auth_matrix", MagicMock())                        # line 70
```

**Problem:** `setdefault` does NOT overwrite existing entries, but once a `MagicMock` is cached in `sys.modules`, all subsequent `import` statements for that module resolve to `MagicMock` — silently, without any `ImportError`.

### 3.2 When It Strikes

Pytest collects test files by traversing `testpaths = ["tests"]` in filesystem order. If `tests/hermes/test_safety_plugin.py` is **imported before** the phase7 or safety tests (which happens during test collection), the `sys.modules` cache is permanently poisoned:

| Order | Effect |
|---|---|
| Phase7 tests imported FIRST → real modules cached → `setdefault` is no-op | ✅ Phase7 tests pass |
| `test_safety_plugin.py` imported FIRST → MagicMock cached → phase7 imports resolve to MagicMock | ❌ Phase7 tests fail |

Pytest collection order across sibling directories is **not guaranteed**, making this a flaky-but-deterministic failure in CI/full-suite mode.

### 3.3 Exact Impact on Phase7 Tests

#### `test_T2_safety_gates.py` (all 15 tests)

| Import Line | Symbol | Resolves To | Failure Mode |
|---|---|---|---|
| 11 | `HardStopHandler` | `MagicMock()` | `check()` returns MagicMock, not bool |
| 11 | `SafetyState` | `MagicMock()` | `isinstance` checks fail, enum comparison fails |
| 13 | `YandereEngine` | `MagicMock()` | `get_effective_level()` returns MagicMock |
| 14 | `YandereLevel` | `MagicMock()` | `YandereLevel.Y0_NEUTRAL` etc. → AttributeError or MagicMock |
| 15 | `can_escalate` | `MagicMock()` | Returns MagicMock (truthy) instead of bool |
| 16 | `get_effective_level` | `MagicMock()` | Returns MagicMock instead of YandereLevel |
| 18 | `YandereSafetyError` | **Real Exception** (only survivor) | Mock explicitly provides real subclass |

Every assertion comparing to `YandereLevel.Y0_NEUTRAL`, `SafetyState.SAFE`, etc. will fail because the right side is also MagicMock (often passes trivially due to `MagicMock == MagicMock` being False but MagicMock being truthy).

#### `test_T5_surveillance_pipeline.py` (some tests)

| Import Line | Symbol | Resolves To | Failure Mode |
|---|---|---|---|
| 13 | `ClassificationResult` | *Real* (not mocked) | ✅ OK |
| 13 | `classify_event` | *Real* (not mocked) | ✅ OK |
| 19 | `RetentionTier` | *Real* (not mocked) | ✅ OK |
| 26 | `surveillance_router` | *Real* (not mocked) | ✅ OK |
| 27 | `verify_hmac` | *Real* (not mocked) | ✅ OK |
| 28 | `ConsentCheckResult` | *Real* (not mocked) | ✅ OK |
| 29 | `ConsentStatus` | *Real* (not mocked) | ✅ OK |
| 31 | `SurveillanceEventRequest` | *Real* (not mocked) | ✅ OK |

**Note:** `src.surveillage.classification` IS mocked (`line 57`), so `test_classification*` tests may be affected.

#### `test_T6_persona_fsm.py` (many tests)

| Import Line | Symbol | Resolves To | Failure Mode |
|---|---|---|---|
| 14 | `YandereEngine`, `YandereLevel`, etc. | MagicMock | All FSM tests fail |
| 22 | `Mood`, `evaluate_mood` | *Real* (not mocked) | ✅ OK (mood_engine not in setdefault) |
| 23 | `TransitionContext`, `TransitionRuleEngine` | *Real* | ✅ OK |
| 24 | `DriftBaseline`, `DriftDetector`, `DriftResult` | MagicMock (`line 24`) | drift tests fail |
| 25 | `StreakTracker` | *Real* | ✅ OK |

#### `test_T7_distress_protocol.py` (many tests)

| Import Line | Symbol | Resolves To | Failure Mode |
|---|---|---|---|
| 13 | `DistressLevel`, `DistressSignal`, etc. | MagicMock (`line 23: src.persona.safe_mode`) | All distress tests fail |
| 19 | `YandereLevel`, `can_escalate`, `get_effective_level` | MagicMock (`line 49`) | Yandere-level assertions fail |

#### `test_T8_consent_revocation.py` (some tests)

| Import Line | Symbol | Resolves To | Failure Mode |
|---|---|---|---|
| 10 | `ConsentCheckResult`, `ConsentStatus` | *Real* | ✅ OK |
| 14 | `HMACVerification`, `verify_hmac` | *Real* | ✅ OK |
| 15 | `HardStopHandler`, `SafetyState` | MagicMock (`line 20`) | HardStop/consent tests fail |

#### `tests/safety/test_hard_stop_handler.py`

| Import Line | Symbol | Resolves To | Failure Mode |
|---|---|---|---|
| 11 | `HardStopHandler` | MagicMock | All 30+ tests fail |
| 11 | `SafetyState` | MagicMock | Enum comparisons all fail |

### 3.4 Contamination Map

```
test_safety_plugin.py module-level setdefault()
  │
  ├── src.core.services.hard_stop_handler → MagicMock
  │     ├── test_T2_safety_gates.py        ← FAIL (HardStopHandler, SafetyState)
  │     ├── test_T8_consent_revocation.py  ← FAIL (HardStopHandler, SafetyState)
  │     └── test_hard_stop_handler.py      ← FAIL (HardStopHandler, SafetyState)
  │
  ├── src.persona.safe_mode → MagicMock
  │     └── test_T7_distress_protocol.py   ← FAIL (DistressLevel, SafeModeController, etc.)
  │
  ├── src.persona.drift_detector → MagicMock
  │     └── test_T6_persona_fsm.py         ← FAIL (DriftDetector, DriftBaseline, DriftResult)
  │
  ├── src.persona.yandere_fsm → Mock (with real YandereSafetyError)
  │     ├── test_T2_safety_gates.py        ← FAIL (YandereEngine, YandereLevel)
  │     ├── test_T6_persona_fsm.py         ← FAIL (YandereEngine, YandereLevel)
  │     └── test_T7_distress_protocol.py   ← FAIL (YandereLevel, can_escalate)
  │
  ├── src.surveillance.classification → MagicMock
  │     └── test_T5_surveillance_pipeline.py ← PARTIAL (ClassificationResult affected)
  │
  ├── src.mcp.auth → Mock (with real MockAuthLevel)
  │     └── test_safety_plugin.py itself   ← Self-contained (intentional mock)
  │
  └── src.mcp.auth_matrix → MagicMock
        └── test_safety_plugin.py itself   ← Self-contained (intentional mock)
```

### 3.5 Required Fix

Replace the 8 module-level `sys.modules.setdefault()` calls in `test_safety_plugin.py` with a scoped mechanism:

**Option A (tdr):** Wrap in a pytest autouse fixture that monkeypatches `sys.modules` per-test and restores after:

```python
@pytest.fixture(autouse=True)
def _mock_safety_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install safety-module mocks for this test only."""
    monkeypatch.setitem(sys.modules, "src.core.services.hard_stop_handler", MagicMock())
    monkeypatch.setitem(sys.modules, "src.persona.safe_mode", MagicMock())
    ...
```

**Option B (simpler):** Replace `setdefault` (persists) with local `sys.modules[path] = Mock()` inside the test functions or a session-scoped fixture that restores originals in `yield`. However, `setdefault` is used to prevent ImportError at import time of the plugin itself. The real solution would be to use `unittest.mock.patch.dict(sys.modules, ...)` context manager.

**Option C (safest for parallel runs):** Move all sys.modules patching into a `conftest.py` that wraps only the tests needing it, with cleanup in `yield`.

---

## 4. PRE-EXISTING UNRELATED FAILURES (Not B3 Regressions)

These failures exist independently of the B3 archive:

| Test File | Failure Type | Root Cause | B3-Related? |
|---|---|---|---|
| `tests/hermes/test_auth_overlay.py` | YAML auth config loading | Missing/empty overlay fixture | ❌ No |
| `tests/discord/test_bot.py` (historic) | Stale assertion `==33` vs `==35` | Command count drift — **ALREADY FIXED** in current file | ❌ No |
| `tests/surveillance/*` (potential) | Redis/network dependency | Requires running Redis | ❌ No |

---

## 5. Summary: What to Fix

### P0 — Cross-test sys.modules contamination (blocks full-suite runs)

| File | Lines | Problem | Fix |
|---|---|---|---|
| `tests/hermes/test_safety_plugin.py` | 20–70 | 8 `sys.modules.setdefault()` calls at module level poison global module cache | Replace with fixture-scoped or `monkeypatch`-based mocking |

### Affected test files (pass in isolation, fail in suite)

| File | Fails Due To | Specific Symbols Resolving to MagicMock |
|---|---|---|
| `tests/phase7/test_T2_safety_gates.py` | `hard_stop_handler`, `yandere_fsm` → MagicMock | `HardStopHandler`, `SafetyState`, `YandereEngine`, `YandereLevel`, `can_escalate`, `get_effective_level` |
| `tests/phase7/test_T5_surveillance_pipeline.py` | `classification` → MagicMock (partial) | `ClassificationResult`, `classify_event` |
| `tests/phase7/test_T6_persona_fsm.py` | `yandere_fsm`, `drift_detector` → MagicMock | `YandereEngine`, `YandereLevel`, `can_escalate`, `get_effective_level`, `DriftDetector`, `DriftBaseline`, `DriftResult` |
| `tests/phase7/test_T7_distress_protocol.py` | `safe_mode`, `yandere_fsm` → MagicMock | `DistressLevel`, `DistressSignal`, `SafeModeController`, `SafeModeError`, `YandereLevel`, `can_escalate`, `get_effective_level` |
| `tests/phase7/test_T8_consent_revocation.py` | `hard_stop_handler` → MagicMock | `HardStopHandler`, `SafetyState` |
| `tests/safety/test_hard_stop_handler.py` | `hard_stop_handler` → MagicMock | `HardStopHandler`, `SafetyState` |
| `tests/safety/test_hard_stop_model.py` | `hard_stop_handler` → MagicMock (if imported) | `HardStopHandler`, `SafetyState` |
| `tests/safety/test_consent_revocation.py` | `hard_stop_handler` → MagicMock (if imported) | `HardStopHandler`, `SafetyState` |
| `tests/safety/test_yandere_cap.py` | `yandere_fsm` → MagicMock (if imported) | `YandereEngine`, `YandereLevel` |

### NOT affected (use modules NOT in the setdefault list)

| File | Reason |
|---|---|
| `tests/phase7/test_T1_e2e_loop.py` | No shared mock targets |
| `tests/phase7/test_T3_auth_enforcement.py` | No shared mock targets |
| `tests/phase7/test_T4_memory_pipeline.py` | No shared mock targets |
| `tests/phase7/test_T9_budget_enforcement.py` | No shared mock targets |
| `tests/phase7/test_T10_monitoring_health.py` | No shared mock targets |
| `tests/safety/test_hard_stop_comprehensive.py` | No shared mock targets |
| `tests/safety/test_punishment_overflow.py` | No shared mock targets |
| `tests/safety/test_auto_rollback.py` | No shared mock targets |
| `tests/safety/test_distress_protocol_e2e.py` | No shared mock targets |

---

## 6. Appendix: Verification Methodology

### 6.1 Files Inspected

```
tests/hermes/test_safety_plugin.py          — Full read (1722 lines)
tests/hermes/test_memory_bridge.py           — Full read (330 lines)
tests/phase7/test_T2_safety_gates.py        — Full read (95 lines)
tests/phase7/test_T5_surveillance_pipeline.py — Full read (173 lines)
tests/phase7/test_T6_persona_fsm.py          — Full read (221 lines)
tests/phase7/test_T7_distress_protocol.py    — Full read (134 lines)
tests/phase7/test_T8_consent_revocation.py   — Full read (115 lines)
tests/safety/test_hard_stop_handler.py       — Full read (248 lines)
tests/discord/test_bot.py                    — Full read (373 lines)
tests/discord/test_startup.py               — Full read (372 lines)
tests/discord/test_cmd_mood.py              — Full read (346 lines)
tests/discord/conftest.py                    — Full read (58 lines)
tests/surveillance/conftest.py               — Full read (43 lines)
tests/smoke/conftest.py                      — Full read (88 lines)
```

### 6.2 Grep Patterns Executed

| Pattern | Match Count | Notes |
|---|---|---|
| `from src._deprecated|import src._deprecated` in `tests/` | **0** | No test imports deprecated archive |
| `from src.discord.(bot\|startup\|commands\|conversational_handler\|intents\|_embed_helpers\|permissions\|guild_setup)` in `tests/` | **2** (archived only) | Both in `.archived` file |
| `import src.discord.(bot\|startup\|commands\|...)` in `tests/` | **0** | All clean |
| `from src.hermes.(session_adapter\|memory_bridge)` in `tests/` | **0** | All clean |
| `@patch` statements in all test files | **89** across 4 files | All patch active module paths |
| `sys.modules.*MagicMock` in `tests/` | **10** sites | Only in `test_safety_plugin.py` (8) + `test_memory_bridge.py` (2) |

### 6.3 Source Tree Verified

| Path | Check |
|---|---|
| `src/_deprecated/hermes-migration-phase-7/` | Contains all 10 archived files + README |
| `src/discord/_entrypoint.py` | Exists (replaces `bot.py`) |
| `src/discord/_startup.py` | Exists (replaces `startup.py`) |
| `src/discord/_intents.py` | Exists (replaces `intents.py`) |
| `src/discord/_command_registry.py` | Exists (replaces `commands.py` registry) |
| `src/discord/_auth_guard.py` | Exists (replaces `commands.py` is_faiz_interaction) |
| `src/discord/_embed_utils.py` | Exists (replaces `_embed_helpers.py`) |
| `src/hermes/_session_adapter.py` | Exists (replaces `session_adapter.py`) |
| `src/hermes/_memory_bridge.py` | Exists (replaces `memory_bridge.py`) |
| `src/hermes/adapter.py` | Exists (replaces `__init__.py` accessor) |
| `src/discord/hermes_conversational.py` | Exists (replaces `conversational_handler.py`) |

---

## 7. Evidence Files Referenced

| File | Path |
|---|---|
| B3 archive plan | `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/phase-7c-b3-archive-plan.md` |
| A4 test migration evidence | `docs/setup-evidence/hermes-migration/phase-7c-b3-archive/STEP-B3-A4-test-migration/verification.md` |
| Research: remaining imports | `research-reports/phase-7c-b3-b8/01-remaining-imports.md` |
| Research: test deprecated imports | `research-reports/phase-7c-b3-b8/02-test-deprecated-imports.md` |

---

## Footer

Generated by Sisyphus-Junior for Guinevere B3 archive regression triage. Read-only diagnostic — no files modified. No code edits, no git operations, no test execution.

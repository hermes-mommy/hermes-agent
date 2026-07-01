# P4 Runtime Readiness Assessment -- Read-Only Checks

**Date:** 2026-06-25
**Scope:** All checks performed read-only (no DB writes, no service restarts, no test execution).
**Environment:** Windows 11 local (Git Bash) -- systemctl/journalctl not available.

---

## 1. Persona Engine Wiring Into Running Hermes/P20 Runtime

**Method:** Grep for `from src.persona` imports across `src/hermes/`, `src/life_kernel/`, `src/discord/`, `src/core/`, `src/hermes_plugins/`. Inspected plugin manifests and configs.

**Finding -- TWO plugins exist, only ONE is wired:**

| Plugin | Source file | Plugin package | Registered? |
|---|---|---|---|
| `guinevere-safety` | `src/hermes/safety_plugin.py` | `.hermes/plugins/guinevere-safety/` (has `plugin.yaml`) | **YES** -- Hermes scans `~/.hermes/plugins/` automatically |
| `guinevere-persona` | `src/hermes/plugins/persona_plugin.py` | `hermes-config/plugins/guinevere_persona/` (has `plugin.yaml`) | **NO** -- not in `~/.hermes/plugins/` and no `plugin` config path in `config.yaml` |

**Evidence for `guinevere-safety` being wired:**
- `src/hermes/safety_plugin.py` exports `register(ctx)` (lines 1210-1249)
- `.hermes/plugins/guinevere-safety/__init__.py` imports and re-exports it:
  ```python
  from src.hermes.safety_plugin import register  # line 30
  ```
- `.hermes/plugins/guinevere-safety/plugin.yaml` declares 6 hooks: `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `post_tool_call`, `transform_llm_output`, `on_session_start`
- This directory is under `~/.hermes/plugins/` which is Hermes's standard plugin discovery path

**Evidence for `guinevere-persona` NOT being wired:**
- `src/hermes/plugins/persona_plugin.py` exports `register(ctx)` (lines 751-784)
- A plugin package exists at `hermes-config/plugins/guinevere_persona/` with `plugin.yaml` and `__init__.py`
- But: the VPS config at `hermes-config/config.yaml` has NO `plugins:` section that would load external plugin paths
- No `.hermes/plugins/guinevere-persona/` directory exists
- No `plugin_dir` or `plugins` configuration found in any hermes config
- The local config at `AppData/Local/hermes/config.yaml` shows `external_dirs: []` (line 235, under `skills:`, not plugins)

**Persona modules imported by wired plugins:**
- `safety_plugin.py` imports (all lazy):
  - `src.persona.safe_mode` (line 452): `DistressDetector, SafeModeController`
  - `src.persona.drift_detector` (lines 484, 823, 846): `DriftDetector`
  - `src.persona.yandere_fsm` (lines 524, 767): `YandereEngine, YandereLevel, validate_level, YandereSafetyError`

- `hermes_conversational.py` (Discord runtime) imports directly:
  - `src.persona.safe_mode` (lines 454, 477): `DistressDetector, SafeModeController, DistressLevel, DistressSignal`
  - `src.persona.mood_engine` (line 489): `Mood`

**Confidence:** HIGH (file-based evidence)
**NEEDS RUNTIME VERIFICATION:** No, file evidence is conclusive.

---

## 2. Hermes Plugin Directory Check

**Method:** List `src/hermes/plugins/` and `src/hermes_plugins/`.

**Finding:**

- `src/hermes/plugins/` exists and contains:
  - `__init__.py` -- package init, documents `persona_plugin`
  - `persona_plugin.py` -- 785 lines, full PersonaPlugin implementation

- `src/hermes_plugins/` is a DIFFERENT directory containing Discord command modules (commands_admin, commands_finance, commands_high, commands_loop, commands_memory, commands_surveillance, commands_system, command_catalog.py). It does NOT contain persona or safety plugins.

- `safety_plugin.py` lives at `src/hermes/safety_plugin.py` (NOT under `plugins/`) and is also a full plugin with `register()`.

**Confidence:** HIGH
**NEEDS RUNTIME VERIFICATION:** No

---

## 3. Ritual Scheduler -- APScheduler Status

**Method:** Grep for `RitualScheduler(`, `.add_job()`, `start()`, `APScheduler`, `BackgroundScheduler`, `AsyncIOScheduler` across `src/`.

**Finding:**

- `src/persona/ritual_scheduler.py` declares itself **deprecated** at module level (line 11-15):
  ```python
  .. deprecated:: Phase 5
      This module is **deprecated** in favour of Hermes cron (~/.hermes/crontab.yaml)
      and PersonaPlugin (src/hermes/plugins/persona_plugin.py). APScheduler is
      removed from the active production path.
  ```
- `RitualScheduler()` is only instantiated in:
  - `src/discord/bot.py.bak.pre-phase2` (BACKUP file) -- not live
  - `src/persona/ritual_scheduler.py:178` (its own `__main__` block) -- not used by runtime
- No live Python code instantiates `RitualScheduler()` or calls `.add_job()` or `.start()` on it
- The ritual cron IS wired in VPS config: `hermes-config/config.yaml` has 5 cron jobs (lines 294-318) firing `hermes chat -Q -q 'Execute ... ritual'` at WIB times. These use Hermes's built-in cron, not APScheduler.
- APScheduler IS used elsewhere in the app (memory consolidation, KG ingestion, loops scheduler, Gmail, X poster) but NOT for persona rituals.

**Confidence:** HIGH
**NEEDS RUNTIME VERIFICATION:** No

---

## 4. Mood Persistence -- DB Tables and Connection

**Method:** Grep alembic for `mood_states`, `PersonaState`, `MoodHistory`. Check source for DB config existence.

**Finding:**

- Source model: `src/memory/models.py` defines `PersonaState` (line 413) and `MoodHistory` (line 455), both in `persona` schema
- Alembic: `alembic/versions/e401bb5fd274_initial_schema_47_tables.py` creates both tables (lines 590-629) and drops them (lines 1101-1102) in the `persona` schema
- `alembic/env.py` includes `"persona"` in `GUINEVERE_SCHEMAS` (line 20)
- `src/persona/mood_persistence.py` implements `MoodRepository` using `AsyncSession` from SQLAlchemy
- **BUT**: No alembic migration after the initial 47-table schema references `mood_states`, `PersonaState`, or `MoodHistory` -- these were created once and never modified
- The SQLAlchemy models exist and schema is valid, but `mood_persistence.py` repository is NOT imported by any runtime caller (safety_plugin.py, persona_plugin.py, or hermes_conversational.py)
- DB connection config exists in `src/core/main.py` (lines 145-146) reading `DATABASE_URL` env var, and `src/persona/mood_persistence.py` receives `AsyncSession` via constructor injection -- but no caller provides it

**Confidence:** HIGH on table existence, MEDIUM on live connectivity (tables exist in migration, but no runtime calls to mood_persistence)
**NEEDS RUNTIME VERIFICATION:** For actual DB connectivity check (read-only `SELECT 1` against `persona.persona_state`), but table structure is confirmed.

---

## 5. Test Discovery -- Persona and Whole-Repo

**Method:** `python -m pytest tests/persona --collect-only -q` and `python -m pytest --collect-only -q`.

**Finding:**

- **Persona tests collected:** 1160 tests (all clean, no collection errors)
- **Whole-repo tests collected:** 5434 tests (with 11 collection ERRORS)
- **11 collection errors** -- all in `tests/channels/whatsapp/`:
  - `test_adapter.py`, `test_envelope.py`, `test_formatter.py`, `test_health.py`, `test_image_vision.py`, `test_metrics.py`, `test_ops_commands.py`, `test_presence.py`, `test_router.py`, `test_structured_logging.py`, `test_wave3_safety_chain.py`
  - These are import/dependency errors unrelated to P4
- **1449 tests PASS claim**: Incorrect for current state. Whole-repo test count is 5434 collected (with 11 errors). The "1449" may be stale or from a different configuration. Persona-only count is 1160 -- note that persona tests alone nearly match the old "1449" figure, suggesting the claim may have been persona-only.

**Confidence:** HIGH
**NEEDS RUNTIME VERIFICATION:** No

---

## 6. Hard Stop Model Tests -- "14 Pre-Existing Errors"

**Method:** Locate `test_hard_stop_model.py`, run `python -m pytest tests/safety/test_hard_stop_model.py --collect-only -q`.

**Finding:**

- File found at: `tests/safety/test_hard_stop_model.py` (NOT under `tests/life_kernel/`)
- Also found: `tests/safety/test_hard_stop_comprehensive.py`, `test_hard_stop_handler.py`, `test_hard_stop_latency.py`
- Collect-only result: **14 tests collected** with **ZERO collection errors** -- clean import/syntax
- The "14 pre-existing errors" referenced in PROGRESS likely refers to **assertion/runtime failures** (test logic errors, not import/collection/syntax errors). These would only surface during actual test execution, which is not permitted in this read-only audit.
- Test structure:
  - `TestHardStopModelCompliance` (5 tests): behavioral compliance checks
  - `TestHardStopSemanticEquivalents` (7 parameterized tests): semantic trigger detection
  - `TestNormalBehaviorBaseline` (2 tests): normal persona continuation

**Confidence:** HIGH (collection is clean; errors must be runtime assertion failures)
**NEEDS RUNTIME VERIFICATION:** Yes, to confirm whether errors are assertion-only. But collection is error-free.

---

## 7. Systemctl Status

**Method:** `systemctl status guinevere`

**Finding:**
- `systemctl` is not available on this Windows 11 environment
- The VPS deployment config at `hermes-config/config.yaml` references paths like `/home/guinevere/code/guinevere` and `python3` commands, confirming a Linux VPS target with systemd
- On the VPS, the service name is unknown from file inspection alone

**Confidence:** N/A
**NEEDS RUNTIME VERIFICATION:** **YES** -- must be checked on the VPS

---

## 8. Journalctl Read-Only

**Method:** `journalctl -u guinevere --since "2026-06-24" --no-pager -p info | grep -iE 'persona|yandere|safe_mode|mood|ritual'`

**Finding:**
- `journalctl` is not available on this Windows 11 environment
- No log output could be inspected

**Confidence:** N/A
**NEEDS RUNTIME VERIFICATION:** **YES** -- must be checked on the VPS

---

## RUNTIME WIRING GAPS

This section lists every persona module and whether it has a live caller that reaches it during normal runtime operation.

### Modules with LIVE callers in the running app:

| Module | Caller(s) | How wired |
|---|---|---|
| `src.persona.yandere_fsm` | `safety_plugin.py` (lines 524, 767) | Plugin hook `pre_llm_call` via `.hermes/plugins/guinevere-safety/` |
| `src.persona.safe_mode` | `safety_plugin.py` (line 452), `hermes_conversational.py` (lines 454, 477) | Both plugin hook AND Discord conversational direct call |
| `src.persona.drift_detector` | `safety_plugin.py` (lines 484, 823, 846) | Plugin hooks `post_llm_call`, `transform_llm_output` |
| `src.persona.mood_engine` | `hermes_conversational.py` (line 489) | Discord conversational direct call |

### Modules with NO live caller (dead code in runtime):

| Module | Why it is a gap |
|---|---|
| **`src.persona.mood_persistence`** (MoodRepository) | Uses `AsyncSession` -- no caller injects a session. Only imported by `persona/__init__.py` and tests. |
| **`src.persona.drift_corrector`** | Only imported by `persona/__init__.py`. No runtime import. |
| **`src.persona.punishment_engine`** | Only imported by `persona/__init__.py`. No runtime import. |
| **`src.persona.reward_engine`** | Only imported by `persona/__init__.py`. No runtime import. |
| **`src.persona.streak_tracker`** | Only imported by `persona/__init__.py`. No runtime import. |
| **`src.persona.transition_rules`** | Only imported by `persona/__init__.py`. No runtime import. |
| **`src.persona.milestone_engine`** | Lazily imported by `persona_plugin.py:83` via `_get_milestone_engine()`, but persona_plugin is NOT registered (see below). Essentially dead. |
| **`src.persona.ritual_scheduler`** | Explicitly deprecated. Replaced by Hermes cron. |
| **`src.persona.rituals/*.py`** | Only imported by `persona/__init__.py` (guarded by `TYPE_CHECKING`). No runtime path. |

### CRITICAL GAP: `PersonaPlugin` (src/hermes/plugins/persona_plugin.py) is NOT registered

- The plugin has a full `register()` function (line 751) and a plugin package at `hermes-config/plugins/guinevere_persona/` with `plugin.yaml`
- **But**: Neither the VPS config nor the local config references this plugin path
- Hermes discovers plugins from `~/.hermes/plugins/<name>/plugin.yaml` -- only `guinevere-safety` lives there
- The `hermes-config/plugins/guinevere_persona/` package remains unregistered in any running Hermes agent
- **Impact**: Redis DB5 persona state injection, milestone detection, and time-band awareness are NOT active in the running app's prompt context
- Persona state IS partially handled by `safety_plugin.py` (yandere level, distress detection, drift detection) and `hermes_conversational.py` (mood enum, safe mode), but the full persona state block with mood variant, punishment, reward, relationship stage, emotional residue, corruption mode is NOT being injected

### SECONDARY GAP: `hermes-config/plugins/guinevere_safety/` vs `.hermes/plugins/guinevere-safety/`

Two separate safety plugin implementations exist:
1. `hermes-config/plugins/guinevere_safety/` -- standalone plugin with its own `StateManager`, no longer clear if actively loaded
2. `.hermes/plugins/guinevere-safety/` -- thin wrapper importing `src/hermes/safety_plugin.py` -- this IS the currently active one

The VPS config at `hermes-config/config.yaml` documents the safety plugin in comments but does NOT explicitly reference its plugin path -- Hermes discovers it via the `~/.hermes/plugins/` convention.

### Summary of Wired vs Unwired Modules

```
WIRED (active in runtime):
  src.persona.yandere_fsm        ← safety_plugin.py (plugin hook) ✓
  src.persona.safe_mode          ← safety_plugin.py + hermes_conversational.py ✓
  src.persona.drift_detector     ← safety_plugin.py (plugin hook) ✓
  src.persona.mood_engine        ← hermes_conversational.py (direct call) ✓

UNWIRED (no live caller):
  src.persona.mood_persistence   ← NO CALLER ✗
  src.persona.drift_corrector    ← NO CALLER ✗
  src.persona.punishment_engine  ← NO CALLER ✗
  src.persona.reward_engine      ← NO CALLER ✗
  src.persona.streak_tracker     ← NO CALLER ✗
  src.persona.transition_rules   ← NO CALLER ✗
  src.persona.milestone_engine   ← only via unwired persona_plugin.py ✗
  src.persona.ritual_scheduler   ← DEPRECATED ✗
  src.persona.rituals/*.py       ← DEPRECATED ✗
  src/hermes/plugins/persona_plugin.py ← NOT REGISTERED in any Hermes config ✗
```

### GAP: DB Tables Exist but Mood Repository Not Called

- `persona.persona_state` and `persona.mood_history` tables exist in alembic schema
- `MoodRepository` class in `src/persona/mood_persistence.py` is well-implemented with proper error hierarchy
- **But**: No runtime code calls `MoodRepository` methods -- the persona state is managed via Redis DB5 (by `StateManager` in the safety plugin), not via PostgreSQL
- This represents dual-write risk if both paths were active, or data staleness risk if PostgreSQL is the intended source of truth

---

**END OF REPORT**

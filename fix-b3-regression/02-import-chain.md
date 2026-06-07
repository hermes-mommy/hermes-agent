# Import Chain Report — Safety/Persona/Distress Modules (Post-Archive)

> **Goal**: Map where mocked safety/persona/distress symbols are actually defined,
> how active code imports them after the Phase 7 archive, and identify any
> remaining stale references that could cause import failures in tests.

---

## Archive Overview (10 files moved)

All 10 files were `git mv`'d from their original locations to
`src/_deprecated/hermes-migration-phase-7/`:

| Archived file | Old location | Active replacement |
|---|---|---|
| `bot.py` | `src/discord/bot.py` | `src/discord/_entrypoint.py` |
| `startup.py` | `src/discord/startup.py` | `src/discord/_startup.py` |
| `intents.py` | `src/discord/intents.py` | `src/discord/_intents.py` |
| `commands.py` | `src/discord/commands.py` | `src/discord/_command_registry.py` + `_auth_guard.py` |
| `conversational_handler.py` | `src/discord/conversational_handler.py` | `src/discord/hermes_conversational.py` |
| `permissions.py` | `src/discord/permissions.py` | No active importer |
| `guild_setup.py` | `src/discord/guild_setup.py` | No active importer |
| `_embed_helpers.py` | `src/discord/_embed_helpers.py` | `src/discord/_embed_utils.py` |
| `session_adapter.py` | `src/hermes/session_adapter.py` | `src/hermes/_session_adapter.py` |
| `memory_bridge.py` | `src/hermes/memory_bridge.py` | `src/hermes/_memory_bridge.py` |

**Key observation**: No active (non-deprecated) module imports from any archived
path. The only remaining `from src.hermes.memory_bridge import` is inside the
_archived_ `conversational_handler.py` itself (line 155) — which is dead code
after archive.

---

## Symbol Definition Table

### `YandereLevel`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/persona/yandere_fsm.py` line 63 |
| **Type** | `class YandereLevel(IntEnum)` |
| **Members** | `Y0_NEUTRAL=0`, `Y1_MINIMAL=1`, `Y2_LOW=2`, `Y3_MODERATE=3`, `Y4_BASELINE=4`, `Y5_MAX=5` |
| **Re-exported via** | `src/persona/__init__.py` line 105: `from src.persona.yandere_fsm import YandereLevel` |
| **Re-export destination** | `src.persona.YandereLevel` (package-level import) |

**Active call sites importing from `src.persona.yandere_fsm` directly:**
- `src/hermes/safety_plugin.py` lines 434, 673
- `tests/phase7/test_T2_safety_gates.py` line 12
- `tests/phase7/test_T6_persona_fsm.py` line 14
- `tests/phase7/test_T7_distress_protocol.py` line 19

**Active call sites importing from `src.persona` (package-level):**
- None found — all active runtime code imports from the direct module path.

**Tests using `persona.yandere_fsm` (short-form, via `pythonpath = ["src"]`):**
- `tests/safety/test_distress_protocol_e2e.py` line 30
- `tests/persona/test_yandere_fsm.py` line 14

**Tests loading directly via `importlib` (bypassing package):**
- `tests/safety/test_yandere_cap.py` lines 18-33 (loads `yandere_fsm.py` directly)

---

### `SafetyState`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/core/services/hard_stop_handler.py` line 20 |
| **Type** | `class SafetyState(Enum)` |
| **Members** | `NORMAL = "normal"`, `SAFE = "safe"` |
| **Re-exported via** | **NOT re-exported** from `src.core.services` or any `__init__.py` |
| **Re-export destination** | None — consumers import directly from `src.core.services.hard_stop_handler` |

**Active call sites:**
- `src/surveillance/safe_mode.py` line 23
- `tests/surveillance/test_safe_mode.py` line 28
- `tests/safety/test_hard_stop_handler.py` line 11
- `tests/safety/test_hard_stop_comprehensive.py` (via same import)
- `tests/phase7/test_T2_safety_gates.py` line 11
- `tests/phase7/test_T8_consent_revocation.py` line 15

**No re-export layer exists** — every consumer imports directly from
`src.core.services.hard_stop_handler`.

---

### Distress Classes

#### `DistressLevel`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/persona/safe_mode.py` line 46 |
| **Type** | `class DistressLevel(IntEnum)` |
| **Members** | `D0_NORMAL=0`, `D1_MILD_STRESS=1`, `D2_MODERATE=2`, `D3_SEVERE=3`, `D4_EMERGENCY=4` |
| **Re-exported via** | `src/persona/__init__.py` line 60: `from src.persona.safe_mode import DistressLevel` |

#### `DistressSignal`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/persona/safe_mode.py` line 57 |
| **Type** | `@dataclass(frozen=True)` |
| **Fields** | `text`, `detected_level`, `confidence`, `matched_patterns`, `timestamp` |
| **Re-exported via** | `src/persona/__init__.py` line 61 |

#### `SafeModeController`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/persona/safe_mode.py` line 234 |
| **Type** | `class SafeModeController` |
| **Re-exported via** | `src/persona/__init__.py` line 62 |

#### `SafeModeState`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/persona/safe_mode.py` line 68 |
| **Type** | `@dataclass` |
| **Re-exported via** | `src/persona/__init__.py` line 64 |

**Active call sites for distress classes:**
- `src/persona/punishment_engine.py` line 34 (`DistressLevel`, `SafeModeController`)
- `src/persona/drift_corrector.py` line 12 (`SafeModeController`)
- `src/hermes/safety_plugin.py` line 379 (`DistressDetector`, `SafeModeController`)
- `src/discord/hermes_conversational.py` lines 454, 477 (`DistressDetector`, `SafeModeController`, `DistressLevel`, `DistressSignal`)
- `tests/phase7/test_T7_distress_protocol.py` lines 13-18
- `tests/persona/test_safe_mode.py`, `test_distress_detection.py`, `test_punishment_engine.py`, `test_drift_corrector.py`

---

### YandereFSM Exceptions

| Symbol | File | Line | Type |
|---|---|---|---|
| `YandereError` | `src/persona/yandere_fsm.py` | 33 | `class YandereError(Exception)` |
| `YandereSafetyError` | `src/persona/yandere_fsm.py` | 37 | `class YandereSafetyError(YandereError)` |
| `YandereTransitionError` | `src/persona/yandere_fsm.py` | 41 | `class YandereTransitionError(YandereError)` |

All three re-exported via `src/persona/__init__.py` lines 106-107.

---

### Consent Classes

#### `ConsentStatus`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/surveillance/consent_gate.py` line 63 |
| **Type** | `class ConsentStatus(StrEnum)` |
| **Members** | `ACTIVE = "ACTIVE"`, `PAUSED = "PAUSED"`, `WITHDRAWN = "WITHDRAWN"` |
| **Re-exported via** | **NOT re-exported** from any `__init__.py` |

#### `ConsentCheckResult`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/surveillance/consent_gate.py` line 72 |
| **Type** | `@dataclass(frozen=True)` |
| **Fields** | `allowed`, `status`, `scope`, `reason`, `checked_at` |
| **Re-exported via** | **NOT re-exported** |

#### `ConsentChecker` (Protocol)

| Field | Value |
|---|---|
| **Authoritative definition** | `src/surveillance/consent_gate.py` line 103 |
| **Type** | `@runtime_checkable class ConsentChecker(Protocol)` |

**Active call sites:**
- `tests/surveillance/test_consumer.py` line 35 (`ConsentCheckResult`, `ConsentStatus`)
- `tests/phase7/test_T8_consent_revocation.py` lines 10-12 (`ConsentCheckResult`, `ConsentStatus`)

---

### Auth Classes

#### `AuthLevel`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/mcp/auth.py` line 42 |
| **Type** | `class AuthLevel(enum.Enum)` |
| **Members** | `READ_AUTO`, `WRITE_NOTIFY`, `DESTRUCTIVE_APPROVAL`, `FORBIDDEN` |
| **Re-exported via** | `src/mcp/__init__.py` line 15: `from src.mcp.auth import AuthLevel, ForbiddenOperationError, require_approval` |

#### `ForbiddenOperationError`

| Field | Value |
|---|---|
| **Authoritative definition** | `src/mcp/auth.py` line 56 |
| **Type** | `class ForbiddenOperationError(Exception)` |
| **Re-exported via** | `src/mcp/__init__.py` line 15 |

**Active call sites — 18 MCP tool modules** all import from `src.mcp.auth`:
- `src/mcp/auth_matrix.py`, `src/mcp/tools/*.py` (15 files)
- `src/hermes/safety_plugin.py` lines 421, 817
- `hermes-config/plugins/auth_overlay/auth_handler.py` line 21

---

## Full Active Import Map

### Discord Bot Path

```
OLD: src.discord.bot              → src.discord.Bot, main()
NEW: src.discord._entrypoint      → GuinevereBot, main()
IMPORT: from src.discord._entrypoint import GuinevereBot, main, GUILD_ID
USED BY: tests/discord/test_bot.py (lines 32, 50, 269, 278)
```

### Discord Startup Path

```
OLD: src.discord.startup          → build_startup_embed_data(), on_ready(), etc.
NEW: src.discord._startup         → same symbols, different file
IMPORT: from src.discord._startup import ...
USED BY: tests/discord/test_startup.py (lines 18, 289, 303, 318, 334, 349)
```

### Discord Intents Path

```
OLD: src.discord.intents          → get_intents(), etc.
NEW: src.discord._intents         → get_intents(), validate_intents(), etc.
IMPORT: from src.discord._intents import get_intents
USED BY: src.discord._entrypoint (line 31), tests/discord/test_bot.py (line 317+)
```

### Hermes Memory Bridge Path

```
OLD: src.hermes.memory_bridge     → HermesMemoryBridge
NEW: src.hermes._memory_bridge    → HermesMemoryBridge (same class)
IMPORT: from src.hermes._memory_bridge import HermesMemoryBridge
USED BY: src.discord/hermes_conversational.py (line 132),
         tests/hermes/test_memory_bridge.py (line 15)
```

### Hermes Session Adapter Path

```
OLD: src.hermes.session_adapter   → HermesSessionAdapter
NEW: src.hermes._session_adapter  → HermesSessionAdapter (same class)
IMPORT: from src.hermes._session_adapter import HermesSessionAdapter
USED BY: src.hermes/adapter.py (docstring + lazy import)
```

### Persona Module (no archive changes — still active)

```
Persona package at src/persona/ — NOT archived.
All modules (yandere_fsm.py, safe_mode.py, mood_engine.py, etc.) remain
in-place and fully active. The __init__.py re-exports ~80 symbols from all
sub-modules.

Key: Some tests import as "from persona.yandere_fsm import ..." (short-form)
     because pyproject.toml sets `pythonpath = ["src"]`.
     Others use "from src.persona.yandere_fsm import ..." (full-path).
     Both resolve to the same file via different sys.path entries.
```

---

## Stale Import Risk Assessment

### RISK: LOW — No active module imports from archived paths

Search for `from src._deprecated` across the entire codebase: **zero matches**.
Search for `from src.discord.bot`, `from src.discord.startup`,
`from src.hermes.memory_bridge`, `from src.hermes.session_adapter`:
**zero matches in active modules** (the only hit is inside the archived file
itself).

### RISK: MEDIUM — Tests use `from persona.` short-form (bypasses `src.` prefix)

Tests in `tests/persona/` and `tests/safety/` import as:
```python
from persona.yandere_fsm import YandereLevel
from persona.safe_mode import DistressDetector
```
These resolve because `pyproject.toml` sets `pythonpath = ["src"]`, making
`src/persona/` available as `persona`. This works but is fragile — if the
`pythonpath` config changes or if tests run without it, imports break.

The phase7 tests (`tests/phase7/test_T*.py`) correctly use the canonical
`from src.persona.` form and are **not affected** by this risk.

### RISK: LOW — `test_safety_plugin.py` uses extensive sys.modules mocking

`tests/hermes/test_safety_plugin.py` installs mock modules for all safety
dependencies before importing the plugin. These mocks could mask real import
failures — if any authoritative module path changes, the test would still pass
with mocks but fail at runtime. The mock paths are:
- `src.core.services.hard_stop_handler`
- `src.persona.safe_mode`
- `src.persona.drift_detector`
- `src.persona.yandere_fsm`
- `src.surveillance.secret_scanner`
- `src.mcp.auth`

These mock paths match the authoritative module locations, so no divergence.

### RISK: VERY LOW — `test_safety/` tests bypass `__init__` via importlib

`tests/safety/test_yandere_cap.py` and `tests/safety/test_consent_revocation.py`
load modules directly using `importlib.util.spec_from_file_location()`,
bypassing the `src/persona/__init__.py` re-export layer entirely. This means
they load from the correct file regardless of any package-level changes.

---

## Key Finding: No Re-export Layer for `SafetyState` or Consent classes

Unlike `YandereLevel` and distress classes (which are re-exported through
`src/persona/__init__.py`), the following symbols have **no `__init__` re-export**
and must always be imported from their direct module path:

| Symbol | Direct path |
|---|---|
| `SafetyState` | `src.core.services.hard_stop_handler` |
| `HardStopHandler` | `src.core.services.hard_stop_handler` |
| `HardStopEvent` | `src.core.services.hard_stop_handler` |
| `ConsentStatus` | `src.surveillance.consent_gate` |
| `ConsentCheckResult` | `src.surveillance.consent_gate` |
| `ConsentChecker` | `src.surveillance.consent_gate` |
| `AuthLevel` | `src.mcp.auth` (re-exported in `src.mcp.__init__`) |
| `ForbiddenOperationError` | `src.mcp.auth` (re-exported in `src.mcp.__init__`) |

---

## Verdict

**All safety/persona/distress symbols used by failing tests are defined in
active, non-archived modules.** No test imports from archived paths. The
archive only removed 10 files whose active replacements have identical API
surface under new names (`_`-prefixed). The authoritative symbol homes are:

| Symbol | Authoritative home |
|---|---|
| `YandereLevel` | `src/persona/yandere_fsm.py` (also `src.persona`) |
| `SafetyState` | `src.core.services.hard_stop_handler.py` |
| `DistressLevel` | `src.persona/safe_mode.py` (also `src.persona`) |
| `DistressSignal` | `src.persona/safe_mode.py` (also `src.persona`) |
| `SafeModeController` | `src.persona/safe_mode.py` (also `src.persona`) |
| `SafeModeState` | `src.persona/safe_mode.py` (also `src.persona`) |
| `YandereEngine` | `src/persona/yandere_fsm.py` (also `src.persona`) |
| `YandereError` / `YandereSafetyError` / `YandereTransitionError` | `src/persona/yandere_fsm.py` (also `src.persona`) |
| `ConsentStatus` / `ConsentCheckResult` | `src/surveillance/consent_gate.py` |
| `AuthLevel` / `ForbiddenOperationError` | `src/mcp/auth.py` (also `src.mcp`) |

**Conclusion**: Import failures in tests are unlikely to be caused by archive
relocation. All symbols live in their expected authoritative homes. If tests
fail, the cause is elsewhere — likely missing conftest setup, stale `sys.modules`
mocking, or test isolation issues (e.g., import order dependencies between
short-form `persona.X` and full-form `src.persona.X` imports).

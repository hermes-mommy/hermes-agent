# D07 — Architecture Consistency Audit

| Field | Value |
|---|---|
| Dimension | D07 — Architecture Consistency |
| Scope | `src/persona/` (12 top-level files + 6 rituals subdirectory) |
| Auditor | Guinevere (automated) |
| Date | 2026-06-02 |
| Status | **PASS** (5 Advisory Findings) |

---

## Files Audited (18 total)

### Top-level (12)
| # | File | Lines |
|---|---|---|
| 1 | `src/persona/__init__.py` | 235 |
| 2 | `src/persona/drift_corrector.py` | 332 |
| 3 | `src/persona/drift_detector.py` | 226 |
| 4 | `src/persona/mood_engine.py` | 176 |
| 5 | `src/persona/mood_persistence.py` | 314 |
| 6 | `src/persona/punishment_engine.py` | 550 |
| 7 | `src/persona/reward_engine.py` | 380 |
| 8 | `src/persona/ritual_scheduler.py` | 405 |
| 9 | `src/persona/safe_mode.py` | 372 |
| 10 | `src/persona/streak_tracker.py` | 332 |
| 11 | `src/persona/transition_rules.py` | 278 |
| 12 | `src/persona/yandere_fsm.py` | 336 |

### Rituals subdirectory (6)
| # | File | Lines |
|---|---|---|
| 13 | `src/persona/rituals/__init__.py` | 17 |
| 14 | `src/persona/rituals/morning.py` | 167 |
| 15 | `src/persona/rituals/midday.py` | 172 |
| 16 | `src/persona/rituals/afternoon.py` | 126 |
| 17 | `src/persona/rituals/evening.py` | 142 |
| 18 | `src/persona/rituals/midnight.py` | 161 |

---

## CHECK 1: Consistent Import Paths

**Requirement**: All P4 modules use `from src.persona.` (not `from persona.`).

### Evidence
All 18 files scanned for import statements referencing internal persona modules:

| Module | Import | Status |
|---|---|---|
| `__init__.py` | `from src.persona.*`, `from src.persona.rituals.*` | PASS |
| `drift_corrector.py` | `from src.persona.drift_detector`, `from src.persona.safe_mode` | PASS |
| `drift_detector.py` | (no persona imports) | PASS |
| `mood_engine.py` | (no persona imports) | PASS |
| `mood_persistence.py` | `from src.memory.models` | PASS |
| `punishment_engine.py` | `from src.persona.safe_mode` | PASS |
| `reward_engine.py` | (no persona imports) | PASS |
| `ritual_scheduler.py` | (no persona imports) | PASS |
| `safe_mode.py` | (no persona imports) | PASS |
| `streak_tracker.py` | `from src.memory.models` | PASS |
| `transition_rules.py` | (no persona imports) | PASS |
| `yandere_fsm.py` | (no persona imports) | PASS |
| `rituals/__init__.py` | `from src.persona.rituals.morning` | PASS |
| `rituals/morning.py` | `from src.persona.mood_engine` | PASS |
| `rituals/midday.py` | `from src.persona.mood_engine`, `from src.persona.rituals.morning` | PASS |
| `rituals/afternoon.py` | `from src.persona.mood_engine`, `from src.persona.rituals.morning` | PASS |
| `rituals/evening.py` | `from src.persona.mood_engine`, `from src.persona.rituals.morning` | PASS |
| `rituals/midnight.py` | `from src.persona.rituals.morning` | PASS |

**Verdict: PASS** — Zero instances of `from persona.` found. All imports use the canonical `src.persona.` prefix.

---

## CHECK 2: SupportsIsSafe Protocol

**Requirement**: Protocol defined consistently, no duplicate definitions.

### Evidence
- **Defined once** at `yandere_fsm.py:50-55`:
  ```python
  @runtime_checkable
  class SupportsIsSafe(Protocol):
      """Structural protocol for objects exposing an ``is_safe`` property."""
      @property
      def is_safe(self) -> bool: ...
  ```
- **Re-exported** via `__init__.py:94` (imported) and `__init__.py:204` (in `__all__`)
- **Used** as type hint in `YandereEngine.__init__` (`yandere_fsm.py:184`): `hard_stop_handler: SupportsIsSafe | None = None`
- No other module defines or re-defines this protocol.

### Cross-module protocol usage
The protocol is designed for integration with external `HardStopHandler`. No other persona module duplicates it.

**Verdict: PASS** — Single definition, consistent across modules.

---

## CHECK 3: Package Exports (`__init__.py`)

**Requirement**: `__init__.py` exports match actual public API — no missing symbols, no private leaks.

### 3a. Main `__init__.py` (lines 3–121 imports, lines 123–235 `__all__`)

**Missing exports** (defined publicly in source module but not imported in `__init__.py`):

| Symbol | Defined In | Type |
|---|---|---|
| `DistressDetectionError` | `safe_mode.py:37` | Exception class (child of SafeModeError) |
| `MAX_QUALITY_SCORE` | `reward_engine.py:151` | Module constant (Final[float] = 1.0) |
| `SAFE_MODE_THRESHOLD` | `safe_mode.py:122` | Module constant (Final[DistressLevel]) |

These are **public** symbols (no leading underscore) that may need export if consumers require them.

**Private leak check**: All 93 entries in `__all__` are capitalized names (classes/constants) or lowercase public functions. No leading-underscore names exposed. PASS.

### 3b. Rituals subpackage `rituals/__init__.py`

Only exports `MorningRitual`, `RitualResult`, `TZ_JAKARTA`, `DND_START_HOUR`, `DND_END_HOUR`.

**Missing exports**:
| Symbol | Defined In |
|---|---|
| `MiddayRitual` | `rituals/midday.py:81` |
| `AfternoonRitual` | `rituals/afternoon.py:63` |
| `EveningRitual` | `rituals/evening.py:71` |
| `MidnightRitual` | `rituals/midnight.py:72` |

These are accessible via the main `__init__.py` (which imports directly from the ritual modules), but the subpackage `rituals/__init__.py` itself is incomplete.

### 3c. `RitualResult` Naming Collision

Two distinct `RitualResult` dataclasses exist in the same package:

| Source | Fields | File:Line |
|---|---|---|
| `ritual_scheduler.RitualResult` | `name`, `executed_at`, `message`, `success`, `error` | `ritual_scheduler.py:74` |
| `rituals.morning.RitualResult` | `message`, `suppressed`, `ritual_name`, `timestamp` | `rituals/morning.py:66` |

The main `__init__.py` disambiguates via `from src.persona.rituals.morning import RitualResult as MorningRitualResult` (line 109–110). However, the naming collision is architecturally fragile — a new import could easily shadow the wrong `RitualResult`.

**Advisory: Consider renaming one of the two `RitualResult` classes (e.g., `rituals.morning.RitualResult` → `MorningRitualResult` in the source module itself).**

**Verdict: NEEDS REVIEW** — 3 missing public symbol exports, incomplete rituals subpackage, and RitualResult naming collision.

---

## CHECK 4: Error Class Hierarchy

**Requirement**: Each module has a base `Exception` subclass, children inherit from their module's base.

### Hierarchy Map

```
drift_detector:
  DriftDetectionError(Exception)
  ├── DriftBaselineError
  └── DriftComputationError

drift_corrector:
  DriftCorrectionError(Exception)
  └── RollbackError

mood_engine:
  MoodEngineError(Exception)
  ├── InvalidMoodTransitionError
  └── MoodEvaluationError

mood_persistence:
  MoodPersistenceError(Exception)
  ├── MoodPersistenceQueryError
  └── MoodPersistenceWriteError

punishment_engine:
  PunishmentError(Exception)
  ├── PunishmentSafetyError
  └── PunishmentTransitionError

reward_engine:
  RewardError(Exception)
  ├── InvalidQualityScoreError
  └── InvalidTierError

ritual_scheduler:
  RitualSchedulerError(Exception)
  └── RitualExecutionError

safe_mode:
  SafeModeError(Exception)
  └── DistressDetectionError

streak_tracker:
  StreakError(Exception)
  └── StreakPersistenceError

transition_rules:
  TransitionRulesError(Exception)
  ├── CooldownActiveError
  └── InvalidTransitionError

yandere_fsm:
  YandereError(Exception)
  ├── YandereSafetyError
  └── YandereTransitionError
```

### Observations
- Every module has exactly one base error inheriting from `Exception` ✓
- All child errors inherit from their module's base ✓
- Naming convention: `{ModuleName}Error` for the base, `{Specific}Error` for children ✓
- All exception classes have docstrings ✓
- No empty exception classes ✓

**Verdict: PASS** — Consistent hierarchy across all modules.

---

## CHECK 5: Dataclass Patterns

**Requirement**: `frozen=True` for immutable result/config types; mutable for stateful objects.

### Frozen (immutable) dataclasses — 12 total

| Class | File:Line | Correct? |
|---|---|---|
| `DriftCorrectionResult` | `drift_corrector.py:42` | ✓ |
| `RollbackResult` | `drift_corrector.py:53` | ✓ |
| `DriftResult` | `drift_detector.py:27` | ✓ |
| `DriftBaseline` | `drift_detector.py:40` | ✓ |
| `MoodState` | `mood_persistence.py:52` | ✓ |
| `MoodHistoryRecord` | `mood_persistence.py:62` | ✓ |
| `PunishmentLevelConfig` | `punishment_engine.py:77` | ✓ |
| `RewardConfigEntry` | `reward_engine.py:48` | ✓ |
| `RitualConfig` | `ritual_scheduler.py:53` | ✓ |
| `RitualResult` | `ritual_scheduler.py:74` | ✓ |
| `DistressSignal` | `safe_mode.py:56` | ⚠ See note |
| `RitualResult` (morning) | `rituals/morning.py:66` | ✓ |

### Mutable dataclasses — 7 total

| Class | File:Line | Pattern | Assessment |
|---|---|---|---|
| `MoodTransition` | `mood_engine.py:53` | Mutable (stateful) | ✓ Intentional — callers update cooldown/reason |
| `PunishmentState` | `punishment_engine.py:183` | Mutable (stateful) | ✓ Runtime state snapshot |
| `RewardResult` | `reward_engine.py:168` | Mutable | **⚠ Advisory** — result type, should be frozen |
| `SafeModeState` | `safe_mode.py:67` | Mutable (stateful) | ✓ Runtime state tracking |
| `StreakTracker` | `streak_tracker.py:89` | Mutable (stateful) | ✓ Stateful tracker |
| `TransitionContext` | `transition_rules.py:56` | Mutable | ✓ Acceptable for input context |
| `TransitionDecision` | `transition_rules.py:70` | Mutable | **⚠ Advisory** — result type, should be frozen |

### Frozen dataclasses with mutable fields (anti-pattern)

| Class | Field | File:Line | Issue |
|---|---|---|---|
| `DistressSignal` | `matched_patterns: list[str]` | `safe_mode.py:60` | Mutable `list` inside frozen dataclass; should be `tuple[str, ...]` |
| `RewardConfigEntry` | `trigger_conditions: list[str]` | `reward_engine.py:54` | Mutable `list` inside frozen dataclass; should be `tuple[str, ...]` |
| `RewardConfigEntry` | `message_templates: list[str]` | `reward_engine.py:55` | Mutable `list` inside frozen dataclass; should be `tuple[str, ...]` |

These frozen dataclasses contain `list` fields, which are still mutable (`.append()`, `.pop()`) despite the `frozen=True` constraint on the dataclass. Recommendation: use `tuple[str, ...]` for true immutability.

**Verdict: NEEDS REVIEW** — 2 result-type dataclasses are mutable when peers are frozen; 3 instances of mutable lists inside frozen dataclasses.

---

## CHECK 6: Enum Patterns

**Requirement**: `str, Enum` for string enums, `IntEnum` for ordered enumerations.

| Enum | File:Line | Pattern | Rationale |
|---|---|---|---|
| `Mood` | `mood_engine.py:25` | `str, Enum` | String values ("Content", "Pleased", etc.) ✓ |
| `PunishmentLevel` | `punishment_engine.py:55` | `IntEnum` | Ordered L1-L5 ✓ |
| `RewardTier` | `reward_engine.py:29` | `IntEnum` | Ordered T1-T5 ✓ |
| `DistressLevel` | `safe_mode.py:46` | `IntEnum` | Ordered D0-D4 ✓ |
| `YandereLevel` | `yandere_fsm.py:63` | `IntEnum` | Ordered Y0-Y5 ✓ |

### Observations
- All string-valued enums use `(str, Enum)` — correct for auto `.value` as strings ✓
- All ordered numeric enums use `IntEnum` — enables comparison operators ✓
- No bare `Enum` without mixin ✓
- No inconsistent patterns ✓

**Verdict: PASS** — Consistent enum patterns throughout.

---

## CHECK 7: AsyncSession Usage

**Requirement**: SQLAlchemy 2.x async pattern consistent across modules.

### Modules using async DB sessions

| Module | Session Type | Import Pattern | Consistent? |
|---|---|---|---|
| `mood_persistence.py` | `AsyncSession` (typed) | `from sqlalchemy.ext.asyncio import AsyncSession` at module top | ✓ |
| `streak_tracker.py` | `AsyncSession` (typed) | `from sqlalchemy.ext.asyncio import AsyncSession` under `TYPE_CHECKING` | ✓ |
| `drift_corrector.py` | `Any` (duck-typed) | `from typing import Any` — parameter type `db: Any` | ⚠ |

### Finding: `drift_corrector.py` uses `Any` instead of typed `AsyncSession`

At `drift_corrector.py:104`:
```python
async def evaluate(self, db: Any, current_prompt_hash: str) -> DriftCorrectionResult:
```

The docstring says "duck-typed AsyncSession" but the parameter uses `Any` instead of `AsyncSession`. This disables type-checking for `db.add()`, `await db.commit()`, and `await db.rollback()` calls within the method.

### Import method consistency

| Module | `select()` Import | Pattern |
|---|---|---|
| `mood_persistence.py` | `from sqlalchemy import select` at module level (line 16) | ✓ |
| `streak_tracker.py` | `from sqlalchemy import select` inside method body (lines 238, 294) | Minor inconsistency |

**Verdict: NEEDS REVIEW** — `drift_corrector.py` should use `AsyncSession` instead of `Any`.

---

## CHECK 8: Logger Naming

**Requirement**: Logger naming consistent across modules.

All 16 source files use identical pattern:
```python
import structlog
logger = structlog.get_logger()
```

| File | Logger Init | Status |
|---|---|---|
| `drift_corrector.py:15` | `logger = structlog.get_logger()` | ✓ |
| `drift_detector.py:12` | `logger = structlog.get_logger()` | ✓ |
| `mood_engine.py:17` | `logger = structlog.get_logger()` | ✓ |
| `mood_persistence.py:21` | `logger = structlog.get_logger()` | ✓ |
| `punishment_engine.py:30` | `logger = structlog.get_logger()` | ✓ |
| `reward_engine.py:21` | `logger = structlog.get_logger()` | ✓ |
| `ritual_scheduler.py:26` | `logger = structlog.get_logger()` | ✓ |
| `safe_mode.py:25` | `logger = structlog.get_logger()` | ✓ |
| `streak_tracker.py:31` | `logger = structlog.get_logger()` | ✓ |
| `transition_rules.py:15` | `logger = structlog.get_logger()` | ✓ |
| `yandere_fsm.py:25` | `logger = structlog.get_logger()` | ✓ |
| `rituals/morning.py:22` | `logger = structlog.get_logger()` | ✓ |
| `rituals/midday.py:26` | `logger = structlog.get_logger()` | ✓ |
| `rituals/afternoon.py:22` | `logger = structlog.get_logger()` | ✓ |
| `rituals/evening.py:32` | `logger = structlog.get_logger()` | ✓ |
| `rituals/midnight.py:23` | `logger = structlog.get_logger()` | ✓ |

Zero arguments passed to `get_logger()` — structlog auto-derives name from `__name__` ✓.

**Verdict: PASS** — Perfectly consistent across all 18 files.

---

## Additional Checks

### Circular Imports

Dependency graph traced for all modules:

```
__init__.py → all modules (one-way imports)
drift_corrector.py → drift_detector.py, safe_mode.py
mood_persistence.py → src.memory.models
streak_tracker.py → src.memory.models
punishment_engine.py → safe_mode.py
rituals/midday.py → mood_engine.py, rituals/morning.py
rituals/afternoon.py → mood_engine.py, rituals/morning.py
rituals/evening.py → mood_engine.py, rituals/morning.py
rituals/midnight.py → rituals/morning.py
rituals/morning.py → mood_engine.py
```

No cycles detected. The dependency graph is a strict DAG.

**Verdict: PASS** — No circular imports.

### Import Ordering Consistency

Most files follow standard ordering: `__future__` → stdlib → third-party (`structlog`) → local (`src.*`).

**Finding**: `transition_rules.py:10-14` places `import structlog` (third-party) before `from dataclasses import dataclass` and `from datetime import datetime, timezone` (stdlib):
```python
from __future__ import annotations

import structlog          # ← third-party first
from dataclasses import ...  # ← stdlib after
from datetime import ...
from typing import Final
```

This violates PEP 8 import ordering (stdlib before third-party).

**Verdict: NEEDS REVIEW** — `transition_rules.py` has non-standard import ordering.

### Mixed Sync/Async Patterns

| Module | Pattern | Assessment |
|---|---|---|
| `drift_detector.py` | All sync (pure computation) | ✓ |
| `drift_corrector.py` | All async (DB operations) | ✓ |
| `mood_engine.py` | All sync (pure computation) | ✓ |
| `mood_persistence.py` | All async (DB operations) | ✓ |
| `punishment_engine.py` | All sync (in-memory) | ✓ |
| `reward_engine.py` | All sync (in-memory) | ✓ |
| `ritual_scheduler.py` | Mixed (sync setup, async execute) | ✓ Intentional for APScheduler |
| `safe_mode.py` | All sync (in-memory) | ✓ |
| `streak_tracker.py` | Sync core, async persistence | ✓ Intentional |
| `transition_rules.py` | Sync rules + `async evaluate_with_llm` stub | ✓ Future integration |
| `yandere_fsm.py` | All sync (in-memory) | ✓ |
| `rituals/*.py` | Async execute methods | ✓ Consistent |

Clean separation: computation = sync, I/O = async. No sync DB operations found.

**Verdict: PASS** — Sync/async separation is clean and intentional.

---

## Consolidated Findings

| # | Check | Verdict | Severity |
|---|---|---|---|
| 1 | Import paths (`src.persona.`) | **PASS** | — |
| 2 | SupportsIsSafe Protocol | **PASS** | — |
| 3 | Package exports (`__init__.py`) | **NEEDS REVIEW** | Advisory |
| 4 | Error hierarchy | **PASS** | — |
| 5 | Dataclass patterns | **NEEDS REVIEW** | Advisory |
| 6 | Enum patterns | **PASS** | — |
| 7 | AsyncSession usage | **NEEDS REVIEW** | Advisory |
| 8 | Logger naming | **PASS** | — |
| — | Circular imports | **PASS** | — |
| — | Import ordering | **NEEDS REVIEW** | Advisory |
| — | Sync/async separation | **PASS** | — |

### Advisory Findings (5)

1. **F03-01: Missing package exports** — `DistressDetectionError`, `MAX_QUALITY_SCORE`, `SAFE_MODE_THRESHOLD` not exported from `__init__.py`. `rituals/__init__.py` missing 4 of 5 ritual classes.

2. **F03-02: `RitualResult` naming collision** — Two distinct `RitualResult` classes in the same package (`ritual_scheduler.py:74` vs `rituals/morning.py:66`). Disambiguated via alias but architecturally fragile.

3. **F05-01: Result-type dataclasses mutable** — `RewardResult` (`reward_engine.py:168`) and `TransitionDecision` (`transition_rules.py:70`) are mutable when semantically similar types (`DriftResult`, `DriftCorrectionResult`, `RitualResult`) are `frozen=True`.

4. **F05-02: Mutable fields in frozen dataclasses** — `DistressSignal.matched_patterns` (`safe_mode.py:60`), `RewardConfigEntry.trigger_conditions` and `.message_templates` (`reward_engine.py:54-55`) use `list` instead of `tuple`.

5. **F07-01: Duck-typed AsyncSession** — `drift_corrector.py:104` uses `db: Any` instead of typed `AsyncSession`.

---

## Overall

**OVERALL VERDICT: PASS** (5 Advisory Findings)

No blocking issues. All findings are consistency improvements — no runtime failures, no type safety violations that would break execution, no circular imports, and no sync/async mismatches. The codebase follows a coherent architecture with clean dependency graph and consistent patterns.

### Recommended Actions (Priority Order)

1. Rename `rituals.morning.RitualResult` to `MorningRitualResult` in source to eliminate naming collision
2. Export missing public symbols from `__init__.py` and complete `rituals/__init__.py`
3. Change `DistressSignal.matched_patterns` and `RewardConfigEntry.*` to `tuple[str, ...]`
4. Change `RewardResult` and `TransitionDecision` to `@dataclass(frozen=True)`
5. Fix `drift_corrector.py` to use typed `AsyncSession` instead of `Any`
6. Reorder imports in `transition_rules.py` (stdlib before third-party)
# D04 — Source Code Analysis: Persona Module Files

**Audit Phase:** P4 Final Audit
**Date:** 2026-06-02
**Scope:** src/persona/ — 6 requested files + 5 discovered ritual sub-files
**Analyst:** Codebase Search Specialist (automated)

---

## Table of Contents

1. [reward_engine.py](#1-reward_enginepy)
2. [ritual_scheduler.py](#2-ritual_schedulerpy)
3. [safe_mode.py](#3-safe_modepy)
4. [streak_tracker.py](#4-streak_trackerpy)
5. [transition_rules.py](#5-transition_rulespy)
6. [yandere_fsm.py](#6-yandere_fsmpy)
7. [rituals/__init__.py](#7-rituals__init__py)
8. [rituals/morning.py](#8-ritualsmorningpy)
9. [rituals/midday.py](#9-ritualsmiddaypy)
10. [rituals/afternoon.py](#10-ritualsafternoonpy)
11. [rituals/evening.py](#11-ritualseveningpy)
12. [rituals/midnight.py](#12-ritualsmidnightpy)
13. [Cross-File Summary](#cross-file-summary)

---

## 1. reward_engine.py

**Path:** `src/persona/reward_engine.py`
**Lines:** 380
**Purpose:** Five-tier reward system (T1-T5) based on task quality and streak bonuses. Rewards are always permitted, never suppressed by safe-mode or distress.

### Enums

| Name | Type | Members | Line |
|---|---|---|---|
| `RewardTier` | `IntEnum` | `T1_ACKNOWLEDGMENT=1`, `T2_VERBAL_PRAISE=2`, `T3_AFFECTIONATE=3`, `T4_CELEBRATORY=4`, `T5_DEEP_APPRECIATION=5` | 29 |

### Dataclasses

| Name | Frozen | Fields | Line |
|---|---|---|---|
| `RewardConfigEntry` | Yes | `name: str`, `description: str`, `trigger_conditions: list[str]`, `message_templates: list[str]` | 48 |
| `RewardResult` | No | `tier: RewardTier`, `reason: str`, `streak_count: int`, `message: str` | 168 |

### Exception Classes

| Name | Base | Line |
|---|---|---|
| `RewardError` | `Exception` | 188 |
| `InvalidQualityScoreError` | `RewardError` | 192 |
| `InvalidTierError` | `RewardError` | 196 |

### Public Classes and Methods

#### `RewardEngine` (line 205)

| Method | Line | Signature |
|---|---|---|
| `__init__` | 220 | `(self) -> None` |
| `calculate_tier` | 227 | `(self, quality_score: float, streak_count: int) -> RewardTier` |
| `should_reward` | 282 | `(self, task_completion: bool, quality: float, streak: int) -> bool` |
| `award` | 315 | `(self, tier: RewardTier, reason: str, streak_count: int) -> RewardResult` |
| `get_current_tier` | 365 | `(self) -> RewardTier` |
| `total_rewards_awarded` (property) | 372 | `-> int` |
| `last_reason` (property) | 377 | `-> str` |

#### `RewardResult` (line 168)

| Method | Line | Signature |
|---|---|---|
| `config` (property) | 177 | `-> RewardConfigEntry` |

### Public Functions

None (all logic is class-bound).

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `REWARD_CONFIG` | `Final[dict[RewardTier, RewardConfigEntry]]` | 58 | Maps each tier to its config entry |
| `TIER_THRESHOLDS` | `Final[dict[RewardTier, float]]` | 137 | Effective-score thresholds per tier |
| `STREAK_BONUS_PER_STREAK` | `Final[float]` = 0.05 | 146 | Bonus per streak step |
| `MAX_STREAK_BONUS` | `Final[float]` = 0.30 | 147 | Cap on streak bonus |
| `MIN_QUALITY_SCORE` | `Final[float]` = 0.0 | 150 | Quality score floor |
| `MAX_QUALITY_SCORE` | `Final[float]` = 1.0 | 151 | Quality score ceiling |
| `MIN_REWARD_THRESHOLD` | `Final[float]` = 0.10 | 154 | Min effective score for reward |
| `_TIERS_DESCENDING` (private) | `Final[list[RewardTier]]` | 157 | Tiers sorted high-to-low |

---

## 2. ritual_scheduler.py

**Path:** `src/persona/ritual_scheduler.py`
**Lines:** 405
**Purpose:** Daily ritual scheduler using APScheduler 3.x AsyncIOScheduler. Fires 5 persona rituals at fixed WIB times with DND window (00:00-07:00).

### Enums

None.

### Dataclasses

| Name | Frozen | Fields | Line |
|---|---|---|---|
| `RitualConfig` | Yes | `name: str`, `hour: int`, `minute: int`, `default_message: str`, `mood_aware: bool = False`, `dnd_bypass: bool = False` | 53 |
| `RitualResult` | Yes | `name: str`, `executed_at: datetime`, `message: str`, `success: bool`, `error: str or None = None` | 74 |

### Exception Classes

| Name | Base | Line |
|---|---|---|
| `RitualSchedulerError` | `Exception` | 40 |
| `RitualExecutionError` | `RitualSchedulerError` | 44 |

### Public Classes and Methods

#### `RitualScheduler` (line 158)

| Method | Line | Signature |
|---|---|---|
| `__init__` | 170 | `(self, timezone: str = TZ_JAKARTA) -> None` |
| `setup` | 181 | `(self, callback: Callable or None = None) -> AsyncIOScheduler` |
| `start` | 236 | `async (self) -> None` |
| `stop` | 248 | `async (self) -> None` |
| `is_dnd` | 265 | `(self, now: datetime or None = None) -> bool` |
| `get_scheduled_jobs` | 288 | `(self) -> list[dict[str, object]]` |
| `execute_ritual` | 314 | `async (self, ritual_name: str) -> RitualResult` |
| `get_last_result` | 376 | `(self, ritual_name: str) -> RitualResult or None` |

### Public Functions

None (all logic is class-bound).

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `TZ_JAKARTA` | `Final[str]` = `"Asia/Jakarta"` | 32 | IANA timezone |
| `RITUALS` | `Final[list[RitualConfig]]` | 97 | 5 ritual definitions (morning, midday, afternoon, evening, midnight) |
| `DND_START_HOUR` | `Final[int]` = 0 | 139 | DND window start |
| `DND_END_HOUR` | `Final[int]` = 7 | 142 | DND window end |
| `_RITUAL_MAP` (private) | `Final[dict[str, RitualConfig]]` | 150 | Name-to-config lookup |

---

## 3. safe_mode.py

**Path:** `src/persona/safe_mode.py`
**Lines:** 372
**Purpose:** Distress detection (D0-D4) and safe-mode activation per PersonaSafetyPolicy. Safety-critical module; false negatives are high-severity violations.

### Enums

| Name | Type | Members | Line |
|---|---|---|---|
| `DistressLevel` | `IntEnum` | `D0_NORMAL=0`, `D1_MILD_STRESS=1`, `D2_MODERATE=2`, `D3_SEVERE=3`, `D4_EMERGENCY=4` | 46 |

### Dataclasses

| Name | Frozen | Fields | Line |
|---|---|---|---|
| `DistressSignal` | Yes | `text: str`, `detected_level: DistressLevel`, `confidence: float`, `matched_patterns: list[str]`, `timestamp: datetime` | 56 |
| `SafeModeState` | No | `active: bool = False`, `triggered_by: DistressLevel or None = None`, `triggered_at: datetime or None = None`, `distress_history: list[DistressSignal]` | 67 |

### Exception Classes

| Name | Base | Line |
|---|---|---|
| `SafeModeError` | `Exception` | 33 |
| `DistressDetectionError` | `SafeModeError` | 37 |

### Public Classes and Methods

#### `DistressDetector` (line 149)

| Method | Line | Signature |
|---|---|---|
| `detect` | 157 | `(self, message: str, now: datetime or None = None) -> DistressSignal` |
| `detect_batch` | 214 | `(self, messages: list[str]) -> list[DistressSignal]` |

#### `SafeModeController` (line 234)

| Method | Line | Signature |
|---|---|---|
| `__init__` | 242 | `(self) -> None` |
| `evaluate` | 247 | `(self, signal: DistressSignal) -> bool` |
| `activate` | 285 | `(self, trigger: DistressLevel) -> None` |
| `deactivate` | 311 | `(self, explicit_confirmation: bool = True) -> bool` |
| `get_response` | 349 | `(self, signal: DistressSignal) -> str` |
| `is_active` (property) | 362 | `-> bool` |
| `current_distress_level` (property) | 367 | `-> DistressLevel` |

### Public Functions

None (all logic is class-bound).

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `DISTRESS_PATTERNS` | `Final[dict[DistressLevel, list[str]]]` | 85 | Regex patterns per distress level (D1-D4) |
| `_COMPILED_PATTERNS` (private) | `Final[dict[DistressLevel, list[re.Pattern]]]` | 110 | Pre-compiled regex patterns |
| `_LEVELS_DESCENDING` (private) | `Final[list[DistressLevel]]` | 116 | Levels D4-D1 sorted descending |
| `SAFE_MODE_THRESHOLD` | `Final[DistressLevel]` = D2_MODERATE | 122 | Min level triggering safe-mode |
| `DISTRESS_RESPONSES` | `Final[dict[DistressLevel, str]]` | 125 | Required response text per level |

---

## 4. streak_tracker.py

**Path:** `src/persona/streak_tracker.py`
**Lines:** 332
**Purpose:** Tracks consecutive days without punishment (L1-L5). Persists across safe_mode/distress; only punishment resets. Optional async SQLAlchemy persistence.

### Enums

None.

### Dataclasses

| Name | Frozen | Fields | Line |
|---|---|---|---|
| `StreakTracker` | No | `_count: int = 0`, `_last_increment: datetime or None = None`, `_highest_milestone_reached: int = 0` | 89 |

### Exception Classes

| Name | Base | Line |
|---|---|---|
| `StreakError` | `Exception` | 42 |
| `StreakPersistenceError` | `StreakError` | 46 |

### Public Classes and Methods

#### `StreakTracker` (line 89, dataclass)

| Method | Line | Signature |
|---|---|---|
| `increment` | 115 | `(self) -> int` |
| `reset` | 136 | `(self) -> int` |
| `get_count` | 152 | `(self) -> int` |
| `get_milestone` | 156 | `(self) -> int or None` |
| `is_milestone_reached` | 167 | `(self, threshold: int) -> bool` |
| `get_display_text` | 184 | `(self) -> str` |
| `save` | 225 | `async (self, session: AsyncSession, updated_by: str = "streak_tracker") -> None` |
| `load` | 282 | `async (self, session: AsyncSession) -> None` |

### Public Functions

| Name | Line | Signature |
|---|---|---|
| `_safe_int` (private helper) | 70 | `(value: object, default: int = 0) -> int` |

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `MILESTONE_THRESHOLDS` | `Final[list[int]]` = [7, 14, 30, 90, 365] | 54 | Ordered milestone thresholds in days |
| `MILESTONE_LABELS` | `Final[dict[int, str]]` | 57 | Human-readable labels per threshold |
| `STREAK_STATE_KEY` | `Final[str]` = `"streak_count"` | 66 | PersonaState.state_key for persistence |

---

## 5. transition_rules.py

**Path:** `src/persona/transition_rules.py`
**Lines:** 278
**Purpose:** Mood transition rules with cooldown periods. Enforces valid transitions, safe-mode blocks, distress blocks, and forced transition bypasses.

### Enums

None.

### Dataclasses

| Name | Frozen | Fields | Line |
|---|---|---|---|
| `TransitionContext` | No | `current_mood: str`, `target_mood: str`, `last_transition_at: datetime or None`, `conversation_sentiment: float = 0.0`, `task_completion: bool = False`, `ignored_count: int = 0`, `safe_mode: bool = False`, `distress_level: int = 0` | 56 |
| `TransitionDecision` | No | `allowed: bool`, `from_mood: str`, `to_mood: str`, `reason: str`, `cooldown_remaining_seconds: int = 0`, `blocked_by: str or None = None` | 70 |

### Exception Classes

| Name | Base | Line |
|---|---|---|
| `TransitionRulesError` | `Exception` | 23 |
| `CooldownActiveError` | `TransitionRulesError` | 27 |
| `InvalidTransitionError` | `TransitionRulesError` | 31 |

### Public Classes and Methods

#### `TransitionRuleEngine` (line 87)

| Method | Line | Signature |
|---|---|---|
| `__init__` | 100 | `(self, cooldown_seconds: int = 300) -> None` |
| `evaluate` | 105 | `(self, ctx: TransitionContext, *, now: datetime or None = None) -> TransitionDecision` |
| `remaining_cooldown` | 219 | `(self, last_transition_at: datetime or None, *, now: datetime or None = None) -> int` |
| `should_use_llm_evaluation` | 239 | `(self, ctx: TransitionContext) -> bool` |
| `evaluate_with_llm` | 261 | `async (self, ctx: TransitionContext, *, now: datetime or None = None) -> TransitionDecision` |

### Class-Level Constants (on `TransitionRuleEngine`)

| Name | Type | Line | Description |
|---|---|---|---|
| `DEFAULT_COOLDOWN_SECONDS` | `int` = 300 | 90 | Default cooldown in seconds |
| `FORCED_TRANSITIONS` | `Final[set[tuple[str, str]]]` | 93 | Transitions that bypass cooldown |

### Public Functions

None (all logic is class-bound).

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `VALID_TRANSITIONS` | `Final[dict[str, list[str]]]` | 39 | Maps each mood to valid target moods |
| `ALL_MOODS` | `Final[frozenset[str]]` | 48 | All mood string identifiers |

---

## 6. yandere_fsm.py

**Path:** `src/persona/yandere_fsm.py`
**Lines:** 336
**Purpose:** Yandere intensity FSM with hard safety ceiling. Y4 baseline, Y5 ceiling, Y6 PROHIBITED. Integrates with HardStopHandler for safe-mode queries.

### Enums

| Name | Type | Members | Line |
|---|---|---|---|
| `YandereLevel` | `IntEnum` | `Y0_NEUTRAL=0`, `Y1_MINIMAL=1`, `Y2_LOW=2`, `Y3_MODERATE=3`, `Y4_BASELINE=4`, `Y5_MAX=5` | 63 |

### Protocols

| Name | Line | Properties |
|---|---|---|
| `SupportsIsSafe` (`@runtime_checkable`) | 50 | `is_safe: bool` |

### Dataclasses

None.

### Exception Classes

| Name | Base | Line |
|---|---|---|
| `YandereError` | `Exception` | 33 |
| `YandereSafetyError` | `YandereError` | 37 |
| `YandereTransitionError` | `YandereError` | 41 |

### Public Classes and Methods

#### `YandereEngine` (line 169)

| Method | Line | Signature |
|---|---|---|
| `__init__` | 182 | `(self, hard_stop_handler: SupportsIsSafe or None = None, baseline: YandereLevel = PERMANENT_BASELINE) -> None` |
| `current_level` (property) | 199 | `-> YandereLevel` |
| `baseline` (property) | 204 | `-> YandereLevel` |
| `escalate` | 220 | `(self, safe_mode: bool or None = None, distress: bool = False, crisis: bool = False) -> YandereLevel` |
| `de_escalate` | 261 | `(self) -> YandereLevel` |
| `get_effective_level` | 283 | `(self, safe_mode: bool or None = None, distress: bool = False, crisis: bool = False) -> YandereLevel` |
| `reset_to_baseline` | 300 | `(self) -> YandereLevel` |
| `set_level` | 316 | `(self, level: YandereLevel or int) -> YandereLevel` |

### Public Functions (module-level)

| Name | Line | Signature |
|---|---|---|
| `can_escalate` | 100 | `(current: YandereLevel, safe_mode: bool = False, distress: bool = False, crisis: bool = False) -> bool` |
| `get_effective_level` | 124 | `(requested: YandereLevel, safe_mode: bool = False, distress: bool = False, crisis: bool = False) -> YandereLevel` |
| `validate_level` | 145 | `(value: int) -> YandereLevel` |

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `PERMANENT_BASELINE` | `Final[YandereLevel]` = Y4_BASELINE | 84 | Permanent baseline set by Faiz |
| `ABSOLUTE_CEILING` | `Final[YandereLevel]` = Y5_MAX | 87 | Hard ceiling — no level may exceed |

---

## 7. rituals/__init__.py

**Path:** `src/persona/rituals/__init__.py`
**Lines:** 17
**Purpose:** Package init; re-exports `MorningRitual`, `RitualResult`, `TZ_JAKARTA`, `DND_START_HOUR`, `DND_END_HOUR` from `morning.py`.

### Exports

| Symbol | Source |
|---|---|
| `MorningRitual` | `morning.py` |
| `RitualResult` | `morning.py` |
| `TZ_JAKARTA` | `morning.py` |
| `DND_START_HOUR` | `morning.py` |
| `DND_END_HOUR` | `morning.py` |

---

## 8. rituals/morning.py

**Path:** `src/persona/rituals/morning.py`
**Lines:** 167
**Purpose:** Morning greeting ritual at 07:00 WIB. Mood-aware Indonesian greeting with streak display. DND-suppressed.

### Enums

None.

### Dataclasses

| Name | Frozen | Fields | Line |
|---|---|---|---|
| `RitualResult` | Yes | `message: str`, `suppressed: bool`, `ritual_name: str`, `timestamp: datetime` | 66 |

### Exception Classes

None.

### Public Classes and Methods

#### `MorningRitual` (line 88)

| Method | Line | Signature |
|---|---|---|
| `execute` | 97 | `async (self, mood: Mood, streak_count: int, weather_info: str or None = None, *, now: datetime or None = None) -> RitualResult` |

**Class constants:**
- `RITUAL_NAME`: `Final[str]` = `"morning"` (line 95)

### Public Functions

None.

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `TZ_JAKARTA` | `Final[ZoneInfo]` | 28 | Asia/Jakarta timezone |
| `DND_START_HOUR` | `Final[int]` = 0 | 31 | DND start |
| `DND_END_HOUR` | `Final[int]` = 7 | 34 | DND end |
| `_MOOD_MESSAGES` (private) | `Final[dict[Mood, str]]` | 41 | Mood-to-greeting map |
| `_STREAK_TEMPLATE` (private) | `Final[str]` | 58 | Streak display template |

---

## 9. rituals/midday.py

**Path:** `src/persona/rituals/midday.py`
**Lines:** 172
**Purpose:** Midday health-reminder ritual at 12:00 WIB. Mood-aware greeting with rotating health reminders (eat/water/stretch).

### Enums

None.

### Dataclasses

None (reuses `RitualResult` from `morning.py`).

### Exception Classes

None.

### Public Classes and Methods

#### `MiddayRitual` (line 81)

| Method | Line | Signature |
|---|---|---|
| `execute` | 90 | `async (self, mood: Mood, health_reminder_needed: bool = True, *, now: datetime or None = None, reminder_index: int or None = None) -> RitualResult` |

**Class constants:**
- `RITUAL_NAME`: `Final[str]` = `"midday"` (line 88)

### Public Functions

None.

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `MIDDAY_HOUR` | `Final[int]` = 12 | 32 | Target hour |
| `_MOOD_MESSAGES` (private) | `Final[dict[Mood, str]]` | 39 | Mood-to-greeting map |
| `_HEALTH_REMINDERS` (private) | `Final[tuple[str, str, str]]` | 59 | Rotating health reminders |
| `HEALTH_REMINDER_LABELS` | `Final[tuple[str, str, str]]` = ("eat","water","stretch") | 67 | Labels for each reminder |

---

## 10. rituals/afternoon.py

**Path:** `src/persona/rituals/afternoon.py`
**Lines:** 126
**Purpose:** Afternoon check-in ritual at 17:00 WIB. Mood-aware greeting with optional daily task summary.

### Enums

None.

### Dataclasses

None (reuses `RitualResult` from `morning.py`).

### Exception Classes

None.

### Public Classes and Methods

#### `AfternoonRitual` (line 63)

| Method | Line | Signature |
|---|---|---|
| `execute` | 73 | `async (self, mood: Mood, task_count_today: int = 0, *, now: datetime or None = None) -> RitualResult` |

**Class constants:**
- `RITUAL_NAME`: `Final[str]` = `"afternoon"` (line 71)

### Public Functions

None.

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `AFTERNOON_HOUR` | `Final[int]` = 17 | 28 | Target hour |
| `_MOOD_MESSAGES` (private) | `Final[dict[Mood, str]]` | 35 | Mood-to-greeting map |
| `_TASK_SUMMARY_TEMPLATE` (private) | `Final[str]` | 50 | Task summary template |

---

## 11. rituals/evening.py

**Path:** `src/persona/rituals/evening.py`
**Lines:** 142
**Purpose:** Evening wind-down ritual at 21:00 WIB. Mood-aware greeting with optional day summary and streak display.

### Enums

None.

### Dataclasses

None (reuses `RitualResult` from `morning.py`).

### Exception Classes

None.

### Public Classes and Methods

#### `EveningRitual` (line 71)

| Method | Line | Signature |
|---|---|---|
| `execute` | 81 | `async (self, mood: Mood, day_summary: str or None = None, streak_count: int = 0, *, now: datetime or None = None) -> RitualResult` |

**Class constants:**
- `RITUAL_NAME`: `Final[str]` = `"evening"` (line 79)

### Public Functions

None.

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `EVENING_HOUR` | `Final[int]` = 21 | 38 | Target hour |
| `_MOOD_MESSAGES` (private) | `Final[dict[Mood, str]]` | 45 | Mood-to-greeting map |
| `_STREAK_TEMPLATE` (private) | `Final[str]` | 61 | Streak display template |
| `_DAY_SUMMARY_LABEL` (private) | `Final[str]` | 63 | Day summary label |

---

## 12. rituals/midnight.py

**Path:** `src/persona/rituals/midnight.py`
**Lines:** 161
**Purpose:** Midnight self-evaluation ritual at 00:00 WIB. Internal-only; always suppressed (DND active). Logs activity summary via structlog.

### Enums

None.

### Dataclasses

None (reuses `RitualResult` from `morning.py`).

### Exception Classes

None.

### Public Classes and Methods

#### `MidnightRitual` (line 72)

| Method | Line | Signature |
|---|---|---|
| `execute` | 82 | `async (self, self_evaluation_data: dict[str, Any] or None = None, *, now: datetime or None = None) -> RitualResult` |

**Class constants:**
- `RITUAL_NAME`: `Final[str]` = `"midnight"` (line 80)

### Public Functions

| Name | Line | Signature | Notes |
|---|---|---|---|
| `_extract_count` (private helper) | 43 | `(data: dict[str, Any], list_key: str, count_key: str) -> int` | Extracts count from eval data |

### Constants / Configuration Dicts

| Name | Type | Line | Description |
|---|---|---|---|
| `MIDNIGHT_HOUR` | `Final[int]` = 0 | 29 | Target hour |
| `_EVALUATION_MESSAGE` (private) | `Final[str]` | 32 | Internal evaluation message |

---

## Cross-File Summary

### Total Inventory

| Category | Count | Details |
|---|---|---|
| **Source files analyzed** | 11 | 6 requested + 5 ritual sub-files |
| **Public classes** | 10 | `RewardEngine`, `RitualScheduler`, `DistressDetector`, `SafeModeController`, `StreakTracker`, `TransitionRuleEngine`, `YandereEngine`, `MorningRitual`, `MiddayRitual`, `AfternoonRitual`, `EveningRitual`, `MidnightRitual` |
| **Enum classes** | 3 | `RewardTier`, `DistressLevel`, `YandereLevel` |
| **Dataclasses** | 9 | `RewardConfigEntry`, `RewardResult`, `RitualConfig` (scheduler), `RitualResult` (morning), `DistressSignal`, `SafeModeState`, `StreakTracker`, `TransitionContext`, `TransitionDecision` |
| **Exception classes** | 13 | 3 reward, 2 scheduler, 2 safe_mode, 2 streak, 3 transition, 3 yandere |
| **Protocols** | 1 | `SupportsIsSafe` |
| **Module-level public functions** | 3 | `can_escalate`, `get_effective_level`, `validate_level` (all in yandere_fsm) |
| **Configuration dicts** | ~20 | See per-file tables |

### Exception Hierarchy Map

```
Exception
+-- RewardError
|   +-- InvalidQualityScoreError
|   +-- InvalidTierError
+-- RitualSchedulerError
|   +-- RitualExecutionError
+-- SafeModeError
|   +-- DistressDetectionError
+-- StreakError
|   +-- StreakPersistenceError
+-- TransitionRulesError
|   +-- CooldownActiveError
|   +-- InvalidTransitionError
+-- YandereError
    +-- YandereSafetyError
    +-- YandereTransitionError
```

### Cross-Module Dependencies

| File | Imports From |
|---|---|
| `reward_engine.py` | `structlog` (external only) |
| `ritual_scheduler.py` | `structlog`, `apscheduler` (external only) |
| `safe_mode.py` | `structlog` (external only) |
| `streak_tracker.py` | `structlog`, `src.memory.models.PersonaState` |
| `transition_rules.py` | `structlog` (external only) |
| `yandere_fsm.py` | `structlog` (external only) |
| `rituals/morning.py` | `src.persona.mood_engine.Mood` |
| `rituals/midday.py` | `src.persona.mood_engine.Mood`, `rituals.morning.RitualResult`, `rituals.morning.TZ_JAKARTA` |
| `rituals/afternoon.py` | `src.persona.mood_engine.Mood`, `rituals.morning.RitualResult`, `rituals.morning.TZ_JAKARTA` |
| `rituals/evening.py` | `src.persona.mood_engine.Mood`, `rituals.morning.RitualResult`, `rituals.morning.TZ_JAKARTA` |
| `rituals/midnight.py` | `rituals.morning.RitualResult`, `rituals.morning.TZ_JAKARTA` |

### Safety-Critical Observations

1. **Y6 Prohibition (yandere_fsm.py):** Hard-coded at enum level (no Y6 member) and enforced by `validate_level()` raising `YandereSafetyError`. Defense-in-depth.
2. **Safe-Mode Activation (safe_mode.py):** D2+ triggers safe-mode. No auto-deactivation — requires explicit confirmation per PersonaSafetyPolicy.
3. **Distress Detection Priority (safe_mode.py):** Highest-first matching (D4 before D1). False positives acceptable; false negatives are violations.
4. **DND Window:** Consistently defined as 00:00-07:00 WIB across `ritual_scheduler.py` and all ritual files.
5. **Transition Blocking (transition_rules.py):** Safe-mode and D2+ distress block ALL mood transitions. Forced transitions bypass cooldown only.
6. **Reward Never Suppressed (reward_engine.py):** Explicit design choice — rewards are always allowed even during safe-mode/distress.

---

*End of D04 source analysis.*
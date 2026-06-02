# P4 Persona Engine — Complete Module Map

> **Audit Date**: 2026-06-02
> **Scope**: `src/persona/` (root + `rituals/` subpackage)
> **Files**: 18 Python source files (12 root + 6 rituals)
> **Total Lines**: 3,790

---

## 1. File Inventory

| # | File | Lines | Role |
|---|------|-------|------|
| 1 | `src/persona/__init__.py` | 233 | Package re-exports (`__all__`) |
| 2 | `src/persona/drift_corrector.py` | 273 | Drift correction + auto-rollback |
| 3 | `src/persona/drift_detector.py` | 176 | Drift detection via hash comparison |
| 4 | `src/persona/mood_engine.py` | 134 | Mood FSM (enum + transitions) |
| 5 | `src/persona/mood_persistence.py` | 261 | Mood CRUD via SQLAlchemy |
| 6 | `src/persona/punishment_engine.py` | 445 | Punishment ladder L1-L5 |
| 7 | `src/persona/reward_engine.py` | 301 | Reward tiers T1-T5 |
| 8 | `src/persona/ritual_scheduler.py` | 329 | APScheduler-based ritual cron |
| 9 | `src/persona/safe_mode.py` | 290 | Distress detection D0-D4 + safe-mode |
| 10 | `src/persona/streak_tracker.py` | 263 | Streak days without punishment |
| 11 | `src/persona/transition_rules.py` | 226 | Cooldown-aware mood transitions |
| 12 | `src/persona/yandere_fsm.py` | 257 | Yandere intensity FSM Y0-Y5 |
| 13 | `src/persona/rituals/__init__.py` | 15 | Rituals subpackage re-exports |
| 14 | `src/persona/rituals/afternoon.py` | 96 | 17:00 WIB check-in |
| 15 | `src/persona/rituals/evening.py` | 109 | 21:00 WIB wind-down |
| 16 | `src/persona/rituals/midday.py` | 135 | 12:00 WIB health reminder |
| 17 | `src/persona/rituals/midnight.py` | 122 | 00:00 WIB self-evaluation |
| 18 | `src/persona/rituals/morning.py` | 129 | 07:00 WIB greeting |

---

## 2. Per-File Symbol Inventory

### 2.1 `__init__.py` (233 lines)

**Purpose**: Package facade — imports and re-exports all public symbols.

- **`__all__`**: 70 entries covering all submodules
- No classes, functions, or constants defined. Pure re-export module.

---

### 2.2 `drift_corrector.py` (273 lines)

**Purpose**: Evaluates drift via `DriftDetector` and performs auto-rollback when threshold exceeded. Integrates with `SafeModeController` to defer rollback during operator distress.

| Kind | Name | Details |
|------|------|---------|
| **Constant** | `DRIFT_THRESHOLD` | `float = 0.10` |
| **Exception** | `DriftCorrectionError` | Base (extends `Exception`) |
| **Exception** | `RollbackError` | Extends `DriftCorrectionError` |
| **Dataclass** | `DriftCorrectionResult` | `frozen=True` — 5 fields: drift_detected, drift_score, action, rollback_performed, reason |
| **Dataclass** | `RollbackResult` | `frozen=True` — 4 fields: success, previous_hash, restored_hash, timestamp |
| **Class** | `DriftCorrector` | Main API class |
| — method | `__init__(detector, safe_mode_controller)` | |
| — property | `detector` | Returns `DriftDetector` |
| — property | `safe_mode_controller` | Returns `SafeModeController \| None` |
| — method | `evaluate(db, current_prompt_hash)` | `async` -> `DriftCorrectionResult` |
| — method | `rollback(db, reason)` | `async` -> `RollbackResult` |
| — method | `create_drift_log(db, drift_result, action_taken)` | `async` -> `DriftLog` |

**Intra-persona imports**: `DriftDetector`, `DriftResult` from `drift_detector`; `SafeModeController` from `safe_mode`
**External imports**: `DriftLog` from `src.memory.models`, `structlog`, `dataclasses`, `datetime`, `typing`

---

### 2.3 `drift_detector.py` (176 lines)

**Purpose**: Core drift detection via SHA-256 hash Hamming distance comparison.

| Kind | Name | Details |
|------|------|---------|
| **Exception** | `DriftDetectionError` | Base (extends `Exception`) |
| **Exception** | `DriftBaselineError` | Extends `DriftDetectionError` |
| **Exception** | `DriftComputationError` | Extends `DriftDetectionError` |
| **Dataclass** | `DriftResult` | `frozen=True` — 7 fields |
| **Dataclass** | `DriftBaseline` | `frozen=True` — 4 fields |
| **Class** | `DriftDetector` | Core detector |
| — class attr | `DEFAULT_THRESHOLD` | `Final[float] = 0.10` |
| — method | `__init__(baseline, threshold)` | |
| — method | `compute_drift_score(current_prompt_hash)` | Hamming distance ratio |
| — method | `detect(current_prompt_hash, now)` | -> `DriftResult` |
| — method | `update_baseline(new_baseline)` | |
| — staticmethod | `compute_prompt_hash(prompt_text)` | SHA-256 hex digest |
| — property | `baseline`, `threshold`, `check_count`, `last_result` | |

**Intra-persona imports**: NONE — **leaf module**
**External imports**: `hashlib`, `structlog`, `dataclasses`, `datetime`, `typing`

---

### 2.4 `mood_engine.py` (134 lines)

**Purpose**: Foundational mood FSM — enum, transition map, evaluation function.

| Kind | Name | Details |
|------|------|---------|
| **Enum** | `Mood(str, Enum)` | 5 members: CONTENT, PLEASED, DISAPPOINTED, ANGRY, SILENT |
| **Constant** | `TRANSITIONS` | `Final[dict[Mood, list[Mood]]]` — adjacency map |
| **Dataclass** | `MoodTransition` | Mutable — 4 fields (from_mood, to_mood, reason, cooldown_seconds=300) |
| **Exception** | `MoodEngineError` | Base |
| **Exception** | `InvalidMoodTransitionError` | Extends `MoodEngineError` |
| **Exception** | `MoodEvaluationError` | Extends `MoodEngineError` |
| **Function** | `can_transition(current, target)` | -> `bool` |
| **Function** | `evaluate_mood(sentiment, task_completion, ignored_count, current_mood)` | -> `MoodTransition \| None` |

**Intra-persona imports**: NONE — **leaf module**
**External imports**: `structlog`, `dataclasses`, `enum`, `typing`

---

### 2.5 `mood_persistence.py` (261 lines)

**Purpose**: CRUD repository for mood state via SQLAlchemy (PersonaState, MoodHistory tables).

| Kind | Name | Details |
|------|------|---------|
| **Private Const** | `_CURRENT_MOOD_KEY` | `"current_mood"` |
| **Private Const** | `_MOOD_STREAK_KEY` | `"mood_streak"` |
| **Exception** | `MoodPersistenceError` | Base |
| **Exception** | `MoodPersistenceQueryError` | Extends `MoodPersistenceError` |
| **Exception** | `MoodPersistenceWriteError` | Extends `MoodPersistenceError` |
| **Dataclass** | `MoodState` | `frozen=True` — 4 fields |
| **Dataclass** | `MoodHistoryRecord` | `frozen=True` — 5 fields |
| **Class** | `MoodRepository` | Repository pattern |
| — method | `__init__(session: AsyncSession)` | |
| — method | `get_current_mood()` | `async` -> `MoodState \| None` |
| — method | `set_current_mood(mood, intensity, updated_by)` | `async` upsert |
| — method | `record_mood_transition(from_mood, to_mood, reason, intensity)` | `async` insert |
| — method | `get_mood_history(limit)` | `async` -> `list[MoodHistoryRecord]` |
| — method | `get_mood_streak()` | `async` -> `int` |
| — method | `update_mood_streak(streak)` | `async` upsert |
| — method | `_safe_rollback()` | `async` private helper |

**Intra-persona imports**: NONE — **leaf module** (uses raw mood strings, NOT `Mood` enum)
**External imports**: `MoodHistory`, `PersonaState` from `src.memory.models`, `sqlalchemy`, `structlog`, `datetime`

---

### 2.6 `punishment_engine.py` (445 lines)

**Purpose**: 5-level punishment ladder (L1-L5) with safety controls. L6 is DEFERRED.

| Kind | Name | Details |
|------|------|---------|
| **Exception** | `PunishmentError` | Base |
| **Exception** | `PunishmentSafetyError` | Extends `PunishmentError` |
| **Exception** | `PunishmentTransitionError` | Extends `PunishmentError` |
| **Enum** | `PunishmentLevel(IntEnum)` | 5 members: L1_COLD_SHOULDER through L5_SILENT_TREATMENT |
| **Private Const** | `_L6_VALUE` | `Final[int] = 6` (sentinel) |
| **Dataclass** | `PunishmentLevelConfig` | `frozen=True` — 5 fields (name, duration_hours, description, allowed_actions, blocked_actions) |
| **Constant** | `PUNISHMENT_CONFIG` | `Final[dict[PunishmentLevel, PunishmentLevelConfig]]` — 5 entries |
| **Dataclass** | `PunishmentState` | Mutable — 9 fields (active, level, violation_type, description, started_at, duration, suspended, suspended_at, suspension_reason) |
| **Class** | `PunishmentEngine` | Main engine |
| — method | `__init__(safe_mode_controller)` | |
| — method | `apply(level, violation_type, description)` | Apply punishment |
| — method | `escalate()` | One level up (L5+ -> error) |
| — method | `de_escalate()` | One level down (below L1 -> deactivate) |
| — method | `suspend(reason)` | Pause clock |
| — method | `resume()` | Resume clock |
| — method | `get_current()` | -> `PunishmentState` |
| — method | `is_active()` | -> `bool` |
| — method | `time_remaining()` | -> `timedelta` |
| — method | `check_distress_suspension(distress_level)` | Auto suspend/resume based on D3+ |
| — method | `_activate_level(level)` | Private |
| — method | `_deactivate()` | Private |
| — method | `_check_expiry()` | Private — auto-deactivate on timeout |

**Intra-persona imports**: `DistressLevel`, `SafeModeController` from `safe_mode`
**External imports**: `structlog`, `dataclasses`, `datetime`, `enum`, `typing`

---

### 2.7 `reward_engine.py` (301 lines)

**Purpose**: 5-tier reward system (T1-T5) based on task quality + streak bonus.

| Kind | Name | Details |
|------|------|---------|
| **Enum** | `RewardTier(IntEnum)` | 5 members: T1_ACKNOWLEDGMENT through T5_DEEP_APPRECIATION |
| **Dataclass** | `RewardConfigEntry` | `frozen=True` — 4 fields (name, description, trigger_conditions, message_templates) |
| **Constant** | `REWARD_CONFIG` | `Final[dict[RewardTier, RewardConfigEntry]]` — 5 entries |
| **Constant** | `TIER_THRESHOLDS` | `Final[dict[RewardTier, float]]` — T5=0.95, T4=0.80, T3=0.60, T2=0.40, T1=0.20 |
| **Constant** | `STREAK_BONUS_PER_STREAK` | `Final[float] = 0.05` |
| **Constant** | `MAX_STREAK_BONUS` | `Final[float] = 0.30` |
| **Constant** | `MIN_QUALITY_SCORE` | `Final[float] = 0.0` |
| **Constant** | `MAX_QUALITY_SCORE` | `Final[float] = 1.0` |
| **Constant** | `MIN_REWARD_THRESHOLD` | `Final[float] = 0.10` |
| **Private Const** | `_TIERS_DESCENDING` | Sorted list highest-first |
| **Dataclass** | `RewardResult` | Mutable — 4 fields + `config` property |
| **Exception** | `RewardError` | Base |
| **Exception** | `InvalidQualityScoreError` | Extends `RewardError` |
| **Exception** | `InvalidTierError` | Extends `RewardError` |
| **Class** | `RewardEngine` | Main engine |
| — method | `__init__()` | |
| — method | `calculate_tier(quality_score, streak_count)` | -> `RewardTier` |
| — method | `should_reward(task_completion, quality, streak)` | -> `bool` |
| — method | `award(tier, reason, streak_count)` | -> `RewardResult` |
| — method | `get_current_tier()` | -> `RewardTier` |
| — property | `total_rewards_awarded` | -> `int` |
| — property | `last_reason` | -> `str` |

**Intra-persona imports**: NONE — **leaf module**
**External imports**: `structlog`, `dataclasses`, `enum`, `typing`

---

### 2.8 `ritual_scheduler.py` (329 lines)

**Purpose**: APScheduler 3.x cron-based daily ritual scheduler with DND window.

| Kind | Name | Details |
|------|------|---------|
| **Constant** | `TZ_JAKARTA` | `Final[str] = "Asia/Jakarta"` |
| **Exception** | `RitualSchedulerError` | Base |
| **Exception** | `RitualExecutionError` | Extends `RitualSchedulerError` |
| **Dataclass** | `RitualConfig` | `frozen=True` — 6 fields (name, hour, minute, default_message, mood_aware, dnd_bypass) |
| **Dataclass** | `RitualResult` | `frozen=True` — 5 fields (name, executed_at, message, success, error) **NOTE: different fields from `rituals/morning.RitualResult`** |
| **Constant** | `RITUALS` | `Final[list[RitualConfig]]` — 5 entries (morning/midday/afternoon/evening/midnight) |
| **Constant** | `DND_START_HOUR` | `Final[int] = 0` |
| **Constant** | `DND_END_HOUR` | `Final[int] = 7` |
| **Private Const** | `_RITUAL_MAP` | `dict[str, RitualConfig]` lookup |
| **Class** | `RitualScheduler` | Main scheduler |
| — method | `__init__(timezone)` | |
| — method | `setup(callback)` | -> `AsyncIOScheduler` |
| — method | `start()` | `async` |
| — method | `stop()` | `async` |
| — method | `is_dnd(now)` | -> `bool` |
| — method | `get_scheduled_jobs()` | -> `list[dict]` |
| — method | `execute_ritual(ritual_name)` | `async` -> `RitualResult` |
| — method | `get_last_result(ritual_name)` | -> `RitualResult \| None` |
| — method | `_default_execute(ritual_name)` | `async` private |
| — method | `_job_wrapper(ritual_name)` | `async` private |

**Intra-persona imports**: NONE — **leaf module**
**External imports**: `apscheduler` (AsyncIOScheduler, CronTrigger), `asyncio`, `zoneinfo.ZoneInfo`, `structlog`, `dataclasses`, `datetime`, `typing`

---

### 2.9 `safe_mode.py` (290 lines)

**Purpose**: Distress detection (D0-D4) with regex patterns + safe-mode activation/deactivation. **SAFETY-CRITICAL**.

| Kind | Name | Details |
|------|------|---------|
| **Exception** | `SafeModeError` | Base |
| **Exception** | `DistressDetectionError` | Extends `SafeModeError` |
| **Enum** | `DistressLevel(IntEnum)` | 5 members: D0_NORMAL through D4_EMERGENCY |
| **Dataclass** | `DistressSignal` | `frozen=True` — 5 fields (text, detected_level, confidence, matched_patterns, timestamp) |
| **Dataclass** | `SafeModeState` | Mutable — 4 fields (active, triggered_by, triggered_at, distress_history) |
| **Constant** | `DISTRESS_PATTERNS` | `Final[dict[DistressLevel, list[str]]]` — regex patterns for D1-D4 |
| **Private Const** | `_COMPILED_PATTERNS` | Pre-compiled `re.Pattern` |
| **Private Const** | `_LEVELS_DESCENDING` | Sorted D4->D1 |
| **Constant** | `SAFE_MODE_THRESHOLD` | `Final[DistressLevel] = D2_MODERATE` |
| **Constant** | `DISTRESS_RESPONSES` | `Final[dict[DistressLevel, str]]` |
| **Class** | `DistressDetector` | Pattern-based detector |
| — method | `detect(message, now)` | -> `DistressSignal` |
| — method | `detect_batch(messages)` | -> `list[DistressSignal]` |
| **Class** | `SafeModeController` | Activation controller |
| — method | `__init__()` | |
| — method | `evaluate(signal)` | -> `bool` (activated?) |
| — method | `activate(trigger)` | Activate safe mode |
| — method | `deactivate(explicit_confirmation)` | -> `bool` (requires True) |
| — method | `get_response(signal)` | -> `str` |
| — property | `is_active` | -> `bool` |
| — property | `current_distress_level` | -> `DistressLevel` |

**Intra-persona imports**: NONE — **leaf module**
**External imports**: `re`, `structlog`, `dataclasses`, `datetime`, `enum`, `typing`

---

### 2.10 `streak_tracker.py` (263 lines)

**Purpose**: Tracks consecutive punishment-free days with milestone system and optional async persistence.

| Kind | Name | Details |
|------|------|---------|
| **Exception** | `StreakError` | Base |
| **Exception** | `StreakPersistenceError` | Extends `StreakError` |
| **Constant** | `MILESTONE_THRESHOLDS` | `Final[list[int]] = [7, 14, 30, 90, 365]` |
| **Constant** | `MILESTONE_LABELS` | `Final[dict[int, str]]` — week/fortnight/month/quarter/year |
| **Constant** | `STREAK_STATE_KEY` | `Final[str] = "streak_count"` |
| **Function** | `_safe_int(value, default)` | Private helper |
| **Dataclass** | `StreakTracker` | `@dataclass` — main tracker |
| — field | `_count` | `int = 0` |
| — field | `_last_increment` | `datetime \| None` |
| — field | `_highest_milestone_reached` | `int = 0` |
| — method | `increment()` | -> `int` (new count) |
| — method | `reset()` | -> `int` (previous count) |
| — method | `get_count()` | -> `int` |
| — method | `get_milestone()` | -> `int \| None` |
| — method | `is_milestone_reached(threshold)` | -> `bool` |
| — method | `get_display_text()` | -> `str` (human-readable) |
| — method | `save(session, updated_by)` | `async` persist to PersonaState |
| — method | `load(session)` | `async` load from PersonaState |

**Intra-persona imports**: NONE — **leaf module**
**External imports**: `PersonaState` from `src.memory.models`, `sqlalchemy` (TYPE_CHECKING only), `structlog`, `dataclasses`, `datetime`, `typing`

---

### 2.11 `transition_rules.py` (226 lines)

**Purpose**: Cooldown-aware mood transition rules with forced-transition bypass. Uses string moods (NOT `Mood` enum) — intentionally independent from `mood_engine`.

| Kind | Name | Details |
|------|------|---------|
| **Exception** | `TransitionRulesError` | Base |
| **Exception** | `CooldownActiveError` | Extends `TransitionRulesError` |
| **Exception** | `InvalidTransitionError` | Extends `TransitionRulesError` |
| **Constant** | `VALID_TRANSITIONS` | `Final[dict[str, list[str]]]` — same topology as `mood_engine.TRANSITIONS` |
| **Constant** | `ALL_MOODS` | `Final[frozenset[str]]` |
| **Dataclass** | `TransitionContext` | Mutable — 8 fields (current_mood, target_mood, last_transition_at, conversation_sentiment, task_completion, ignored_count, safe_mode, distress_level) |
| **Dataclass** | `TransitionDecision` | Mutable — 6 fields (allowed, from_mood, to_mood, reason, cooldown_remaining_seconds, blocked_by) |
| **Class** | `TransitionRuleEngine` | Rule engine |
| — class attr | `DEFAULT_COOLDOWN_SECONDS` | `300` |
| — class attr | `FORCED_TRANSITIONS` | `Final[set[tuple]] = {("Angry","Silent"), ("Content","Pleased")}` |
| — method | `__init__(cooldown_seconds)` | |
| — method | `evaluate(ctx, now)` | -> `TransitionDecision` |
| — method | `remaining_cooldown(last_transition_at, now)` | -> `int` seconds |
| — method | `should_use_llm_evaluation(ctx)` | -> `bool` |
| — method | `evaluate_with_llm(ctx, now)` | `async` stub -> `TransitionDecision` |

**Intra-persona imports**: NONE — **leaf module** (string-based, deliberately decoupled from `mood_engine`)
**External imports**: `structlog`, `dataclasses`, `datetime`, `typing`

---

### 2.12 `yandere_fsm.py` (257 lines)

**Purpose**: Yandere intensity FSM (Y0-Y5) with hard safety ceiling. Y6 is PROHIBITED.

| Kind | Name | Details |
|------|------|---------|
| **Exception** | `YandereError` | Base |
| **Exception** | `YandereSafetyError` | Extends `YandereError` |
| **Exception** | `YandereTransitionError` | Extends `YandereError` |
| **Protocol** | `SupportsIsSafe` | `@runtime_checkable` — requires `is_safe` property |
| **Enum** | `YandereLevel(IntEnum)` | 6 members: Y0_NEUTRAL through Y5_MAX |
| **Constant** | `PERMANENT_BASELINE` | `Final[YandereLevel] = Y4_BASELINE` |
| **Constant** | `ABSOLUTE_CEILING` | `Final[YandereLevel] = Y5_MAX` |
| **Function** | `_any_safety_active(safe_mode, distress, crisis)` | Private helper |
| **Function** | `can_escalate(current, safe_mode, distress, crisis)` | -> `bool` |
| **Function** | `get_effective_level(requested, safe_mode, distress, crisis)` | -> `YandereLevel` (Y0 if any safety active) |
| **Function** | `validate_level(value)` | -> `YandereLevel` (raises on Y6+) |
| **Class** | `YandereEngine` | Stateful engine |
| — method | `__init__(hard_stop_handler, baseline)` | |
| — property | `current_level` | -> `YandereLevel` |
| — property | `baseline` | -> `YandereLevel` |
| — method | `_is_safe_mode()` | Private |
| — method | `escalate(safe_mode, distress, crisis)` | -> `YandereLevel` |
| — method | `de_escalate()` | -> `YandereLevel` |
| — method | `get_effective_level(safe_mode, distress, crisis)` | -> `YandereLevel` |
| — method | `reset_to_baseline()` | -> `YandereLevel` |
| — method | `set_level(level)` | -> `YandereLevel` |

**Intra-persona imports**: NONE — **leaf module**
**External imports**: `structlog`, `enum`, `typing` (Protocol, runtime_checkable)

---

### 2.13 `rituals/__init__.py` (15 lines)

**Purpose**: Subpackage re-export (morning ritual only).

| Kind | Name | Source |
|------|------|--------|
| Re-export | `MorningRitual` | `morning.py` |
| Re-export | `RitualResult` | `morning.py` |
| Re-export | `TZ_JAKARTA` | `morning.py` |
| Re-export | `DND_START_HOUR` | `morning.py` |
| Re-export | `DND_END_HOUR` | `morning.py` |

**`__all__`**: 5 entries

---

### 2.14 `rituals/afternoon.py` (96 lines)

**Purpose**: 17:00 WIB mood-aware check-in greeting.

| Kind | Name | Details |
|------|------|---------|
| **Constant** | `AFTERNOON_HOUR` | `Final[int] = 17` |
| **Private Const** | `_MOOD_MESSAGES` | `dict[Mood, str]` — 5 mood templates |
| **Private Const** | `_TASK_SUMMARY_TEMPLATE` | `str` — task count template |
| **Class** | `AfternoonRitual` | |
| — class attr | `RITUAL_NAME` | `Final[str] = "afternoon"` |
| — method | `execute(mood, task_count_today, now)` | `async` -> `RitualResult` |
| — staticmethod | `_resolve_time(now)` | Private |

**Intra-persona imports**: `Mood` from `mood_engine`; `RitualResult`, `TZ_JAKARTA` from `rituals.morning`
**External imports**: `structlog`, `datetime`, `zoneinfo`, `typing`

---

### 2.15 `rituals/evening.py` (109 lines)

**Purpose**: 21:00 WIB mood-aware wind-down greeting.

| Kind | Name | Details |
|------|------|---------|
| **Constant** | `EVENING_HOUR` | `Final[int] = 21` |
| **Private Const** | `_MOOD_MESSAGES` | `dict[Mood, str]` — 5 mood templates |
| **Private Const** | `_STREAK_TEMPLATE` | `str` |
| **Private Const** | `_DAY_SUMMARY_LABEL` | `str` |
| **Class** | `EveningRitual` | |
| — class attr | `RITUAL_NAME` | `Final[str] = "evening"` |
| — method | `execute(mood, day_summary, streak_count, now)` | `async` -> `RitualResult` |
| — staticmethod | `_resolve_time(now)` | Private |

**Intra-persona imports**: `Mood` from `mood_engine`; `RitualResult`, `TZ_JAKARTA` from `rituals.morning`
**External imports**: `structlog`, `datetime`, `typing`

---

### 2.16 `rituals/midday.py` (135 lines)

**Purpose**: 12:00 WIB mood-aware health reminder with daily rotation.

| Kind | Name | Details |
|------|------|---------|
| **Constant** | `MIDDAY_HOUR` | `Final[int] = 12` |
| **Private Const** | `_MOOD_MESSAGES` | `dict[Mood, str]` — 5 mood templates |
| **Private Const** | `_HEALTH_REMINDERS` | `tuple[str, str, str]` — eat/water/stretch |
| **Constant** | `HEALTH_REMINDER_LABELS` | `Final[tuple[str, str, str]]` |
| **Class** | `MiddayRitual` | |
| — class attr | `RITUAL_NAME` | `Final[str] = "midday"` |
| — method | `execute(mood, health_reminder_needed, now, reminder_index)` | `async` -> `RitualResult` |
| — staticmethod | `_resolve_time(now)` | Private |
| — staticmethod | `_resolve_reminder_index(current_time, override)` | Private — day-of-year mod 3 |

**Intra-persona imports**: `Mood` from `mood_engine`; `RitualResult`, `TZ_JAKARTA` from `rituals.morning`
**External imports**: `structlog`, `datetime`, `typing`

---

### 2.17 `rituals/midnight.py` (122 lines)

**Purpose**: 00:00 WIB internal self-evaluation (never sent to Discord).

| Kind | Name | Details |
|------|------|---------|
| **Constant** | `MIDNIGHT_HOUR` | `Final[int] = 0` |
| **Private Const** | `_EVALUATION_MESSAGE` | `str` |
| **Function** | `_extract_count(data, list_key, count_key)` | Private helper |
| **Class** | `MidnightRitual` | |
| — class attr | `RITUAL_NAME` | `Final[str] = "midnight"` |
| — method | `execute(self_evaluation_data, now)` | `async` -> `RitualResult` (always suppressed=True) |
| — staticmethod | `_resolve_time(now)` | Private |

**Intra-persona imports**: `RitualResult`, `TZ_JAKARTA` from `rituals.morning` (no `Mood` import)
**External imports**: `structlog`, `datetime`, `typing`

---

### 2.18 `rituals/morning.py` (129 lines)

**Purpose**: 07:00 WIB mood-aware greeting with DND suppression.

| Kind | Name | Details |
|------|------|---------|
| **Constant** | `TZ_JAKARTA` | `Final[ZoneInfo] = ZoneInfo("Asia/Jakarta")` |
| **Constant** | `DND_START_HOUR` | `Final[int] = 0` |
| **Constant** | `DND_END_HOUR` | `Final[int] = 7` |
| **Private Const** | `_MOOD_MESSAGES` | `dict[Mood, str]` — 5 mood templates |
| **Private Const** | `_STREAK_TEMPLATE` | `str` |
| **Dataclass** | `RitualResult` | `frozen=True` — 4 fields (message, suppressed, ritual_name, timestamp) **NOTE: different from `ritual_scheduler.RitualResult`** |
| **Class** | `MorningRitual` | |
| — class attr | `RITUAL_NAME` | `Final[str] = "morning"` |
| — method | `execute(mood, streak_count, weather_info, now)` | `async` -> `RitualResult` |
| — staticmethod | `_resolve_time(now)` | Private |

**Intra-persona imports**: `Mood` from `mood_engine`
**External imports**: `structlog`, `dataclasses`, `datetime`, `zoneinfo.ZoneInfo`, `typing`

---

## 3. Import Graph

### 3.1 Intra-Persona Dependency Map

```
src/persona/__init__.py
  |-- drift_corrector
  |-- drift_detector
  |-- mood_engine
  |-- mood_persistence
  |-- ritual_scheduler
  |-- safe_mode
  |-- punishment_engine
  |-- reward_engine
  |-- streak_tracker
  |-- yandere_fsm
  |-- transition_rules
  |-- rituals.afternoon
  |-- rituals.midday
  |-- rituals.midnight
  |-- rituals.morning
  +-- rituals.evening

src/persona/drift_corrector.py
  |-- drift_detector  (DriftDetector, DriftResult)
  +-- safe_mode       (SafeModeController)

src/persona/punishment_engine.py
  +-- safe_mode       (DistressLevel, SafeModeController)

src/persona/rituals/__init__.py
  +-- rituals.morning (MorningRitual, RitualResult, TZ_JAKARTA, DND_START_HOUR, DND_END_HOUR)

src/persona/rituals/afternoon.py
  |-- mood_engine     (Mood)
  +-- rituals.morning (RitualResult, TZ_JAKARTA)

src/persona/rituals/evening.py
  |-- mood_engine     (Mood)
  +-- rituals.morning (RitualResult, TZ_JAKARTA)

src/persona/rituals/midday.py
  |-- mood_engine     (Mood)
  +-- rituals.morning (RitualResult, TZ_JAKARTA)

src/persona/rituals/midnight.py
  +-- rituals.morning (RitualResult, TZ_JAKARTA)

src/persona/rituals/morning.py
  +-- mood_engine     (Mood)
```

### 3.2 Leaf Modules (zero intra-persona imports)

These 9 modules have NO dependencies on other persona modules:

1. `drift_detector.py`
2. `mood_engine.py`
3. `mood_persistence.py`
4. `reward_engine.py`
5. `ritual_scheduler.py`
6. `safe_mode.py`
7. `streak_tracker.py`
8. `transition_rules.py`
9. `yandere_fsm.py`

### 3.3 Dependency Tiers

```
Tier 0 (leaves):    drift_detector, mood_engine, mood_persistence,
                    reward_engine, ritual_scheduler, safe_mode,
                    streak_tracker, transition_rules, yandere_fsm

Tier 1 (1 dep):    drift_corrector    -> drift_detector, safe_mode
                    punishment_engine  -> safe_mode
                    rituals/morning    -> mood_engine
                    rituals/afternoon  -> mood_engine, rituals/morning
                    rituals/evening    -> mood_engine, rituals/morning
                    rituals/midday     -> mood_engine, rituals/morning
                    rituals/midnight   -> rituals/morning

Tier 2 (facade):   __init__.py        -> all above
```

### 3.4 External Dependencies (beyond persona)

| Module | External Import |
|--------|----------------|
| `drift_corrector` | `src.memory.models.DriftLog` |
| `mood_persistence` | `src.memory.models.MoodHistory`, `src.memory.models.PersonaState` |
| `streak_tracker` | `src.memory.models.PersonaState` |
| `ritual_scheduler` | `apscheduler.schedulers.asyncio.AsyncIOScheduler`, `apscheduler.triggers.cron.CronTrigger` |
| All modules | `structlog` |

---

## 4. Circular Import Analysis

**Result: NO circular imports detected.**

The dependency graph is a clean DAG (Directed Acyclic Graph). Every arrow points from higher-tier to lower-tier modules. No module imports from any module that transitively imports back from it.

Dependency chains verified:
- `drift_corrector -> drift_detector` (one-way, drift_detector is leaf)
- `drift_corrector -> safe_mode` (one-way, safe_mode is leaf)
- `punishment_engine -> safe_mode` (one-way, safe_mode is leaf)
- `rituals/* -> mood_engine` (one-way, mood_engine is leaf)
- `rituals/afternoon,evening,midday,midnight -> rituals/morning` (one-way)
- `rituals/morning -> mood_engine` (one-way, mood_engine is leaf)

---

## 5. `__init__.py` Export Audit

### 5.1 Root `__init__.py` — Export Coverage

The root `__init__.py` exports **70 symbols** in `__all__`. Below is a per-module coverage check:

| Module | Public Symbols | Exported | Missing from `__all__` |
|--------|---------------|----------|----------------------|
| `mood_engine` | 8 | 8 | -- |
| `mood_persistence` | 6 | 6 | -- |
| `transition_rules` | 8 | 8 | -- |
| `ritual_scheduler` | 9 | 9 | -- |
| `rituals.morning` | 3+2 aliased | 3+2 | -- |
| `rituals.evening` | 1 | 1 | -- |
| `rituals.afternoon` | 1 | 1 | -- |
| `rituals.midnight` | 1 | 1 | -- |
| `drift_detector` | 6 | 6 | -- |
| `drift_corrector` | 6 | 6 | -- |
| `safe_mode` | 8 | 8 | -- |
| `streak_tracker` | 6 | 6 | -- |
| `yandere_fsm` | 11 | 11 | -- |
| `punishment_engine` | 8 | 8 | -- |
| `reward_engine` | 15 | 15 | -- |
| `rituals.midday` | 1 | 1 | -- |

### 5.2 Symbols NOT in `__init__.py` `__all__`

These **public** (non-underscore) symbols are defined in modules but NOT re-exported from the package root:

| Symbol | Module | Significance |
|--------|--------|-------------|
| `DistressDetectionError` | `safe_mode.py` | Exception — extends `SafeModeError` |
| `SAFE_MODE_THRESHOLD` | `safe_mode.py` | `Final[DistressLevel] = D2_MODERATE` |
| `AFTERNOON_HOUR` | `rituals/afternoon.py` | `Final[int] = 17` |
| `EVENING_HOUR` | `rituals/evening.py` | `Final[int] = 21` |
| `MIDDAY_HOUR` | `rituals/midday.py` | `Final[int] = 12` |
| `HEALTH_REMINDER_LABELS` | `rituals/midday.py` | `Final[tuple[str, str, str]]` |
| `MIDNIGHT_HOUR` | `rituals/midnight.py` | `Final[int] = 0` |

**Assessment**: `DistressDetectionError` and `SAFE_MODE_THRESHOLD` are the most significant omissions — they are safety-critical and consumers may need them. The ritual hour constants are less critical (used internally by ritual implementations).

### 5.3 `rituals/__init__.py` — Incomplete Subpackage Exports

The `rituals/__init__.py` only re-exports symbols from `morning.py`. It does NOT re-export:

| Symbol | Module |
|--------|--------|
| `AfternoonRitual` | `afternoon.py` |
| `EveningRitual` | `evening.py` |
| `MiddayRitual` | `midday.py` |
| `MidnightRitual` | `midnight.py` |
| `AFTERNOON_HOUR` | `afternoon.py` |
| `EVENING_HOUR` | `evening.py` |
| `MIDDAY_HOUR` | `midday.py` |
| `MIDNIGHT_HOUR` | `midnight.py` |
| `HEALTH_REMINDER_LABELS` | `midday.py` |

**Impact**: `from src.persona.rituals import AfternoonRitual` will **fail**. Consumers must import directly: `from src.persona.rituals.afternoon import AfternoonRitual`. However, the root `__init__.py` does export all 5 ritual classes, so `from src.persona import AfternoonRitual` works.

---

## 6. Notable Findings

### 6.1 Dual `RitualResult` Dataclass Name Collision

Two different dataclasses share the name `RitualResult`:

| Location | Fields | Purpose |
|----------|--------|---------|
| `ritual_scheduler.RitualResult` | name, executed_at, message, success, error | Scheduler-level result (5 fields) |
| `rituals/morning.RitualResult` | message, suppressed, ritual_name, timestamp | Individual ritual result (4 fields) |

The root `__init__.py` resolves this by aliasing: `from src.persona.rituals.morning import RitualResult as MorningRitualResult`. However, within the `rituals/` subpackage, all rituals use `morning.RitualResult` (4-field version), while `RitualScheduler` uses its own 5-field version. This is a **design smell** — consumers importing from different paths get incompatible types.

### 6.2 String-based vs Enum-based Mood Duplication

`mood_engine.py` defines `Mood(str, Enum)` with `TRANSITIONS` using enum members. `transition_rules.py` defines its own `VALID_TRANSITIONS` using raw strings. The two maps describe the **same topology** but are independently maintained — a change in one must be manually mirrored in the other.

### 6.3 `mood_persistence.py` Deliberate Decoupling

`mood_persistence.py` intentionally does NOT import `mood_engine.py`. It uses raw mood strings. This means there is no compile-time guarantee that persisted mood values match the `Mood` enum.

### 6.4 Largest Module: `punishment_engine.py` (445 lines)

The punishment engine is by far the largest module, containing:
- 3-level exception hierarchy
- 5-member IntEnum
- Frozen config dataclass + mutable state dataclass
- PUNISHMENT_CONFIG lookup with 5 detailed entries
- 10 public methods + 3 private methods
- Complex suspension/resume/expiry logic

### 6.5 Smallest Module: `rituals/__init__.py` (15 lines)

Minimal re-export facade. Should be expanded to include all 5 ritual classes.

### 6.6 External Dependency: `src.memory.models`

Three modules depend on `src.memory.models`:
- `drift_corrector.py` -> `DriftLog`
- `mood_persistence.py` -> `MoodHistory`, `PersonaState`
- `streak_tracker.py` -> `PersonaState`

These are the only cross-package dependencies within the persona engine.

---

## 7. Aggregate Statistics

| Metric | Count |
|--------|-------|
| Total files | 18 |
| Total lines | 3,790 |
| Total classes | 14 (DriftCorrector, DriftDetector, MoodRepository, PunishmentEngine, RewardEngine, RitualScheduler, DistressDetector, SafeModeController, StreakTracker, TransitionRuleEngine, YandereEngine, AfternoonRitual, EveningRitual, MiddayRitual, MidnightRitual, MorningRitual) = 16 |
| Total enums | 5 (Mood, DistressLevel, PunishmentLevel, RewardTier, YandereLevel) |
| Total protocols | 1 (SupportsIsSafe) |
| Total dataclasses | 16 |
| Total exceptions | 22 |
| Total module-level functions | 7 |
| Total public constants | ~35 |
| Leaf modules (no persona deps) | 9 |
| Max dependency depth | 3 tiers |
| Circular imports | 0 |

---

## 8. Recommendations

1. **Fix `rituals/__init__.py`**: Add re-exports for `AfternoonRitual`, `EveningRitual`, `MiddayRitual`, `MidnightRitual`.

2. **Add missing exports to root `__init__.py`**:
   - `DistressDetectionError` (safety-critical exception)
   - `SAFE_MODE_THRESHOLD` (safety-critical constant)

3. **Resolve `RitualResult` name collision**: Either rename one of them or unify into a single dataclass used by both the scheduler and individual rituals.

4. **Consider unifying mood representations**: The `mood_engine.TRANSITIONS` (enum-based) and `transition_rules.VALID_TRANSITIONS` (string-based) duplicate the same topology. A single source of truth would prevent drift.

5. **Type-safety gap**: `mood_persistence.py` uses raw strings instead of `Mood` enum — consider adding a validation layer or shared type alias.

---

*End of P4 Persona Engine Module Map*

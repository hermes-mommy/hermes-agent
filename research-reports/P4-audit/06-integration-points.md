# P4 Persona Engine — Integration Points Audit

> **Audit scope:** Every import, API call, and type between P4 (`src/persona/`) and existing codebase modules.
> **Files inspected:** 8 existing modules + 12 P4 modules + rituals/

---

## Executive Summary

| Category | Count | Severity |
|---|---|---|
| Compatible (works today) | 12 | — |
| Missing (P4 should connect but doesn't) | 9 | HIGH |
| Partially wired (exists but incomplete) | 3 | MEDIUM |
| Type mismatch risk | 2 | LOW |

---

## 1. hard_stop_handler.py ↔ P4

### 1.1 Existing API Surface

| Symbol | Type | Location |
|---|---|---|
| `SafetyState` | `Enum` (`NORMAL`, `SAFE`) | Line 20 |
| `HardStopHandler` | `@dataclass` | Line 34 |
| `is_safe` | `@property → bool` | Line 60 |
| `check(message) → bool` | Method | Line 63 |
| `check_recovery(message) → bool` | Method | Line 79 |
| `get_neutral_response() → str` | Method | Line 115 |
| `get_guard_decision(message) → dict` | Method | Line 125 |

### 1.2 P4 Usage

| P4 Module | How it integrates | Compatible? |
|---|---|---|
| `yandere_fsm.py` | `SupportsIsSafe` protocol (structural, line 51) — queries `.is_safe` via duck-typing | ✅ YES |
| `punishment_engine.py` | Does NOT import `HardStopHandler`; uses `SafeModeController.is_active` instead | ✅ YES (by isolation) |
| `transition_rules.py` | `TransitionContext.safe_mode: bool` (line 66) — boolean only | ✅ YES |
| `drift_corrector.py` | Uses `SafeModeController` (line 12), NOT `HardStopHandler` | ✅ YES |
| `safe_mode.py` | Independent system — no `HardStopHandler` import | ✅ YES |

### 1.3 MISSING INTEGRATION

**CRITICAL: Two independent safe-mode systems exist with no bridge.**

```
┌─────────────────────────────┐     ┌─────────────────────────────────┐
│  HardStopHandler (P1-021)   │     │  SafeModeController (P4-009)    │
│  src/core/services/         │     │  src/persona/safe_mode.py       │
│                             │     │                                 │
│  Triggered by: keyword      │     │  Triggered by: distress D2+     │
│  is_safe: True/False        │     │  is_active: True/False          │
│  Used by: bot.py,           │     │  Used by: punishment_engine,    │
│           cmd_safeword      │     │           drift_corrector       │
└─────────────────────────────┘     └─────────────────────────────────┘
         ✗ NO BRIDGE ✗
```

When HARD STOP triggers, `SafeModeController` is NOT notified. When distress activates `SafeModeController`, `HardStopHandler` is NOT notified. Both must be consulted before persona behavior runs.

---

## 2. prompt_loader.py ↔ P4

### 2.1 Existing API Surface

| Symbol | Signature | Mood Parameter |
|---|---|---|
| `get_system_prompt_with_context(memories, mood, token_budget)` | `mood: str = "Content"` | Raw string |
| `assemble_system_prompt_with_memory(session, query_text, mood, safe_mode, hard_stop_handler, ...)` | `mood: str = "Content"`, `safe_mode: bool` | Raw string |

### 2.2 P4 Compatibility

| Integration Point | P4 Symbol | Compatible? |
|---|---|---|
| Mood string | `Mood.CONTENT.value == "Content"`, `Mood.PLEASED.value == "Pleased"` | ✅ YES — `Mood` is `str, Enum` |
| Safe mode boolean | `SafeModeController.is_active` → bool | ✅ YES |
| hard_stop_handler protocol | `SupportsIsSafe.is_safe` → bool | ✅ YES — `getattr(handler, "is_safe", False)` works |

### 2.3 MISSING INTEGRATION

No caller currently passes P4 mood into `assemble_system_prompt_with_memory()`. The mood parameter defaults to `"Content"` regardless of actual P4 mood state. A caller should:
1. Query `MoodRepository.get_current_mood()` → `MoodState.mood`
2. Pass it as the `mood` parameter to `assemble_system_prompt_with_memory()`

---

## 3. memory/models.py ↔ P4

### 3.1 Schema Tables Used by P4

| Model | Table | P4 Module | Import | Status |
|---|---|---|---|---|
| `PersonaState` | `persona.persona_state` | `mood_persistence.py` (line 19) | `from src.memory.models import PersonaState` | ✅ WIRED |
| `PersonaState` | `persona.persona_state` | `streak_tracker.py` (line 29) | `from src.memory.models import PersonaState` | ✅ WIRED |
| `MoodHistory` | `persona.mood_history` | `mood_persistence.py` (line 19) | `from src.memory.models import MoodHistory` | ✅ WIRED |
| `DriftLog` | `persona.drift_log` | `drift_corrector.py` (line 13) | `from src.memory.models import DriftLog` | ✅ WIRED |
| `PunishmentLog` | `persona.punishment_log` | `punishment_engine.py` | **NOT IMPORTED** | ❌ MISSING |
| `RewardLog` | `persona.reward_log` | `reward_engine.py` | **NOT IMPORTED** | ❌ MISSING |

### 3.2 Model Field Compatibility

#### PersonaState (used by mood_persistence.py + streak_tracker.py)

| Column | Type | mood_persistence usage | streak_tracker usage |
|---|---|---|---|
| `state_key` | `Text` | `"current_mood"`, `"mood_streak"` | `"streak_count"` |
| `state_value` | `JSONB` | `{"mood": str, "intensity": int}`, `{"streak": int}` | `{"count": int, "last_updated": str, "highest_milestone": int}` |
| `updated_at` | `TIMESTAMP` | ✅ Written | ✅ Written |
| `updated_by` | `Text` | ✅ Written | ✅ Written |

**Compatible:** ✅ Full field coverage, correct types.

#### MoodHistory (used by mood_persistence.py)

| Column | Type | mood_persistence usage |
|---|---|---|
| `mood` | `Text` | ✅ Written (`to_mood` string) |
| `intensity` | `Integer` | ✅ Written |
| `trigger` | `Text` | ✅ Written (format: `"from -> to: reason"`) |
| `duration_minutes` | `Integer` | ✅ Written (`None`) |
| `recorded_at` | `TIMESTAMP` | ✅ Written |

**Compatible:** ✅ Full field coverage.

#### DriftLog (used by drift_corrector.py)

| Column | Type | drift_corrector usage |
|---|---|---|
| `drift_type` | `Text` | ✅ `"none"`, `"alert"`, `"rollback"`, `"rollback:<reason>"` |
| `before_state` | `JSONB` | ✅ `{"prompt_hash": str, "version": str}` |
| `after_state` | `JSONB` | ✅ `{"prompt_hash": str, "version": str}` |
| `delta` | `JSONB` | ✅ `{"drift_score": float, "drift_detected": bool, ...}` |
| `trigger_context` | `Text` | ✅ `"drift_corrector:<action>"` |
| `safety_score` | `Integer` | ✅ `int(drift_score * 100)` |
| `rollback_available` | `Boolean` | ✅ `action.startswith("rollback")` |
| `occurred_at` | `TIMESTAMP` | ✅ `drift_result.checked_at` |

**Compatible:** ✅ Full field coverage.

#### PunishmentLog — NOT USED by punishment_engine.py

| Column | Type | punishment_engine.py usage |
|---|---|---|
| `violation_type` | `Text` | ❌ Not persisted |
| `severity` | `Integer` | ❌ Not persisted |
| `description` | `Text` | ❌ Not persisted |
| `safe_word_triggered` | `Boolean` | ❌ Not persisted |
| `safe_word_bypassed` | `Boolean` | ❌ Not persisted |
| `applied_at` | `TIMESTAMP` | ❌ Not persisted |

**Gap:** `PunishmentEngine` operates purely in-memory (`PunishmentState`). No persistence to `persona.punishment_log`. All punishment history is lost on restart.

#### RewardLog — NOT USED by reward_engine.py

| Column | Type | reward_engine.py usage |
|---|---|---|
| `reward_type` | `Text` | ❌ Not persisted |
| `description` | `Text` | ❌ Not persisted |
| `streak_count` | `Integer` | ❌ Not persisted |
| `awarded_at` | `TIMESTAMP` | ❌ Not persisted |

**Gap:** `RewardEngine` operates purely in-memory. No persistence to `persona.reward_log`. Reward history lost on restart.

---

## 4. read_pipeline.py ↔ P4

### 4.1 SAFE_MODE_BLOCKED_CONTENT_TAGS

The following tags (line 80-86) block content in safe mode:

```python
_SAFE_MODE_BLOCKED_CONTENT_TAGS: frozenset[str] = frozenset({
    "emotional", "emotion", "sentiment", "mood",
    "surveillance", "surveil", "monitor", "spy",
    "persona_escalation", "persona-escalation", "yandere",
    "punishment", "punitive", "jealousy", "dark_mood",
    "silent_mode", "nuclear", "possessive",
})
```

### 4.2 P4 Relevance

| Tag | P4 Module Affected | Impact |
|---|---|---|
| `"mood"` | `mood_engine`, `mood_persistence` | Episodes with mood tags blocked in safe mode |
| `"yandere"` | `yandere_fsm` | Yandere intensity episodes blocked in safe mode |
| `"punishment"`, `"punitive"` | `punishment_engine` | Punishment events blocked in safe mode |
| `"dark_mood"`, `"silent_mode"` | `mood_engine` (Angry/Silent moods) | Dark mood episodes blocked in safe mode |
| `"possessive"` | `yandere_fsm` (Y4/Y5) | High yandere episodes blocked in safe mode |
| `"emotional"`, `"emotion"`, `"sentiment"` | `mood_engine` | All emotional episodes blocked in safe mode |

**Compatible:** ✅ Intentional behavior — safe mode blocks persona-related memories from being recalled.

No P4 module directly imports or calls `read_pipeline.py`. The pipeline is consumed by `prompt_loader.py`.

---

## 5. cmd_mood.py ↔ P4

### 5.1 Current State: Hardcoded Degradation

```python
DEGRADED_HISTORY: Final[str] = "⚠️ — 24h history (P4 not deployed)"
DEGRADED_STREAK: Final[str] = "⚠️ — Streak tracking (P4 not deployed)"
```

### 5.2 Mood Embed Fields vs P4 Data Sources

| Embed Field | Current Value | P4 Source Available | Connected? |
|---|---|---|---|
| Current Mood | `display_for_mood(mood)` | `MoodRepository.get_current_mood()` | ❌ NO |
| Undertone | `DEGRADED_UNDERTONE` (P3 placeholder) | — | N/A |
| 24h History | `DEGRADED_HISTORY` (P4 placeholder) | `MoodRepository.get_mood_history(limit=20)` | ❌ NO |
| Recent Triggers | `DEGRADED_TRIGGERS` (P3 placeholder) | — | N/A |
| Streak | `DEGRADED_STREAK` (P4 placeholder) | `StreakTracker.get_display_text()` | ❌ NO |
| Forecast | `DEGRADED_FORECAST` (P5 placeholder) | — | N/A |

### 5.3 Mood Name Compatibility

| cmd_mood key | `Mood` enum value | Match? |
|---|---|---|
| `"content"` | `Mood.CONTENT = "Content"` | ✅ (lowercase key → emoji) |
| `"pleased"` | `Mood.PLEASED = "Pleased"` | ✅ |
| `"disappointed"` | `Mood.DISAPPOINTED = "Disappointed"` | ✅ |
| `"angry"` | `Mood.ANGRY = "Angry"` | ✅ |
| `"silent"` | `Mood.SILENT = "Silent"` | ✅ |

**Compatible:** ✅ Enum values are Title Case; `display_for_mood()` uses lowercase keys. No type mismatch if `.lower()` is applied.

### 5.4 MISSING INTEGRATION

`cmd_mood.py` does NOT import any P4 module. The `build_mood_embed_data()` function accepts only `now` and `mood` parameters. It needs an async variant that:
1. Queries `MoodRepository` for current mood + history
2. Queries `StreakTracker` for streak display
3. Queries `YandereEngine` for current yandere level
4. Queries `PunishmentEngine` for active punishment status
5. Queries `RewardEngine` for reward stats

---

## 6. cmd_safeword.py ↔ P4

### 6.1 Current Integration

| Integration Point | Module | How |
|---|---|---|
| Handler singleton | `HardStopHandler` | `_get_handler()` lazy-creates from `src.core.services` |
| `handler.check(content)` | `cmd_safeword.py` line 621 | Triggers HARD STOP on keyword match |
| `handler.check("safeword")` | `safeword_callback()` line 567 | Slash command triggers HARD STOP |
| `get_safety_state() → str` | Line 717 | Returns `"normal"` or `"safe"` |

### 6.2 MISSING INTEGRATION

**P4's `SafeModeController` is completely invisible to `cmd_safeword.py`.**

When `/safeword` triggers:
1. `HardStopHandler.check()` fires → state becomes `SAFE`
2. Embed is built and sent
3. P4's `SafeModeController` is NEVER notified
4. P4's `PunishmentEngine` doesn't know HARD STOP was triggered
5. P4's `YandereEngine` doesn't know safe mode activated

When P4's `DistressDetector` triggers:
1. `SafeModeController.evaluate()` fires → state becomes `active`
2. `PunishmentEngine.check_distress_suspension()` may suspend punishment
3. `HardStopHandler` is NEVER notified
4. The `/safeword` embed and `bot.py` don't reflect P4's safe mode

---

## 7. bot.py ↔ P4

### 7.1 Current on_message Pipeline

```python
async def _on_message_listener(self, message):
    # Skip bots
    from .cmd_safeword import handle_safeword_message_async
    consumed = await handle_safeword_message_async(message)
    if consumed:
        return  # HARD STOP triggered

async def on_message(self, message):
    if message.author.bot:
        return
    handler = _get_handler()  # HardStopHandler only
    if handler.is_safe:
        handler.check_recovery(message.content)
        return  # Block non-recovery messages
    await self.process_commands(message)
```

### 7.2 MISSING INTEGRATION (4 gaps)

| Gap | What's missing | P4 module available |
|---|---|---|
| Distress detection | No message analysis for distress | `DistressDetector.detect(message.content)` |
| Mood evaluation | No mood updates on conversation | `evaluate_mood()` + `TransitionRuleEngine.evaluate()` |
| Yandere adjustment | No yandere level changes on events | `YandereEngine.escalate()` / `.de_escalate()` |
| Safe mode bridge | P4 safe mode not consulted | `SafeModeController.is_active` |

The `on_message` pipeline only checks `HardStopHandler.is_safe`. It should also check `SafeModeController.is_active` (distress-based safe mode).

---

## 8. consolidation.py ↔ P4

### 8.1 Current State

```python
SAFE_WORD_INDICATORS: frozenset[str] = frozenset({
    "safe_word", "hard_stop", "crisis", "formal_hold", "distress",
})
```

`is_safe_word_record()` (line 368) checks `tags`, `episode_type`, `title`, `summary`, `source` for these indicators.

### 8.2 P4 Relevance

| Indicator | P4 Module | Episodes Skipped |
|---|---|---|
| `"safe_word"` | `safe_mode.py` → `HardStopHandler` events | ✅ Correctly skipped |
| `"hard_stop"` | `hard_stop_handler.py` events | ✅ Correctly skipped |
| `"crisis"` | `safe_mode.py` D4 events | ✅ Correctly skipped |
| `"formal_hold"` | `safe_mode.py` formal holds | ✅ Correctly skipped |
| `"distress"` | `safe_mode.py` D2+ events | ✅ Correctly skipped |

**Compatible:** ✅ All P4 safety-related episode types are correctly excluded from consolidation. No P4 module imports `consolidation.py`.

---

## 9. Cross-Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Existing Modules                                │
│                                                                         │
│  hard_stop_handler.py ───── cmd_safeword.py ────── bot.py               │
│         │                      │                    │                   │
│         │                      │                    │                   │
│         │                      ▼                    │                   │
│         │              HardStopHandler              │                   │
│         │              (singleton)                  │                   │
│         │                      │                    │                   │
│         ▼                      │                    ▼                   │
│  prompt_loader.py ─────────────┼───────────── on_message               │
│         │                      │                                        │
│         ▼                      │                                        │
│  read_pipeline.py ◄────────────┘                                        │
│                                                                         │
│  models.py (PersonaState, MoodHistory, PunishmentLog, RewardLog, ...)  │
│  consolidation.py (SAFE_WORD_INDICATORS)                                │
└─────────────────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
┌────────┼────────────────────┼────────────────────┼──────────────────────┐
│        │               P4 Modules               │                      │
│        │                    │                    │                      │
│  ┌─────┴──────┐    ┌───────┴────────┐   ┌──────┴───────┐              │
│  │ mood_      │    │ yandere_fsm    │   │ punishment_  │              │
│  │ persistence│    │ (SupportsIsSafe│   │ engine       │              │
│  │ (PersonaState, │  protocol)     │   │ (SafeMode-   │              │
│  │  MoodHistory)  │                │   │  Controller)  │              │
│  └────────────┘    └────────────────┘   └──────────────┘              │
│                                                                    │
│  ┌────────────┐    ┌────────────────┐   ┌──────────────┐             │
│  │ streak_    │    │ drift_         │   │ reward_      │             │
│  │ tracker    │    │ corrector      │   │ engine       │             │
│  │ (PersonaState)  │ (DriftLog,     │   │ (no persist) │             │
│  │                │  SafeMode-      │   │              │             │
│  └────────────┘    │  Controller)   │   └──────────────┘             │
│                    └────────────────┘                                │
│                                                                    │
│  ┌────────────┐    ┌────────────────┐   ┌──────────────┐             │
│  │ safe_mode  │    │ transition_    │   │ ritual_      │             │
│  │ (Distress  │    │ rules          │   │ scheduler    │             │
│  │  Detector, │    │ (safe_mode     │   │ (APScheduler)│             │
│  │  SafeMode  │    │  bool check)   │   │              │             │
│  │  Controller│    └────────────────┘   └──────────────┘             │
│  └────────────┘                                                      │
│  ┌────────────┐                                                      │
│  │ mood_engine│                                                      │
│  │ (Mood FSM) │                                                      │
│  └────────────┘                                                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Complete MISSING Integration Catalog

### MISSING-01: Dual Safe-Mode Bridge (CRITICAL)

**What:** `HardStopHandler` and `SafeModeController` operate independently with no cross-notification.

**Impact:** HARD STOP via keyword doesn't activate P4 safe mode; P4 distress doesn't trigger HARD STOP state.

**Required fix:** Create a bridge layer that:
- When `HardStopHandler.check()` returns True → also activate `SafeModeController`
- When `SafeModeController.is_active` → also set `HardStopHandler.state = SAFE`
- Both must be consulted before persona behavior runs

**Files affected:** `cmd_safeword.py`, `bot.py`, new bridge module

---

### MISSING-02: cmd_mood.py P4 Wiring (HIGH)

**What:** `/mood` embed uses hardcoded degraded placeholders instead of P4 data.

**Impact:** Users see "P4 not deployed" even though P4 is implemented.

**Required fix:**
- Import `MoodRepository`, `StreakTracker`, `YandereEngine`, `PunishmentEngine`
- Replace `DEGRADED_HISTORY` with real mood history from `get_mood_history()`
- Replace `DEGRADED_STREAK` with real streak from `get_display_text()`
- Add yandere level and active punishment to embed fields

**Files affected:** `src/discord/cmd_mood.py`

---

### MISSING-03: PunishmentLog Persistence (HIGH)

**What:** `punishment_engine.py` does not persist to `persona.punishment_log`.

**Impact:** All punishment history lost on restart. No audit trail.

**Required fix:**
- Import `PunishmentLog` from `src.memory.models`
- In `apply()`, create `PunishmentLog` row with `violation_type`, `severity`, `description`, `applied_at`
- In `check_distress_suspension()`, record `safe_word_triggered=True` when distress suspends

**Files affected:** `src/persona/punishment_engine.py`

---

### MISSING-04: RewardLog Persistence (HIGH)

**What:** `reward_engine.py` does not persist to `persona.reward_log`.

**Impact:** Reward history lost on restart.

**Required fix:**
- Import `RewardLog` from `src.memory.models`
- In `award()`, create `RewardLog` row with `reward_type`, `description`, `streak_count`, `awarded_at`

**Files affected:** `src/persona/reward_engine.py`

---

### MISSING-05: YandereEngine State Persistence (HIGH)

**What:** `yandere_fsm.py` does not persist yandere level to `persona.persona_state`.

**Impact:** Yandere level resets to baseline on every restart.

**Required fix:**
- Import `PersonaState` from `src.memory.models`
- Save `YandereLevel` value to `PersonaState` with key `"yandere_level"`
- Load on engine initialization

**Files affected:** `src/persona/yandere_fsm.py`

---

### MISSING-06: bot.py Distress Detection (HIGH)

**What:** `on_message` listener does not run P4's `DistressDetector` on incoming messages.

**Impact:** Distress signals in messages are never detected; `SafeModeController` never activates via conversation.

**Required fix:**
- In `_on_message_listener`, after HARD STOP check, run `DistressDetector.detect(message.content)`
- Feed result to `SafeModeController.evaluate()`
- If activated, send empathetic response and block persona behavior

**Files affected:** `src/discord/bot.py`

---

### MISSING-07: prompt_loader Mood Injection (MEDIUM)

**What:** No caller passes P4 mood into `assemble_system_prompt_with_memory()`.

**Impact:** System prompt always shows `"Content"` mood regardless of actual P4 state.

**Required fix:**
- Before calling `assemble_system_prompt_with_memory()`, query `MoodRepository.get_current_mood()`
- Pass `mood=MoodState.mood` as parameter

**Files affected:** Any module that calls `assemble_system_prompt_with_memory()`

---

### MISSING-08: Safe Mode State Consultation in bot.py (MEDIUM)

**What:** `bot.py` only checks `HardStopHandler.is_safe`, ignoring `SafeModeController.is_active`.

**Impact:** P4 distress-activated safe mode doesn't block persona behavior in `on_message`.

**Required fix:**
- After `handler.is_safe` check, also check `SafeModeController.is_active`
- Either check blocks non-recovery messages

**Files affected:** `src/discord/bot.py`

---

### MISSING-09: Mood Evaluation on Message Events (MEDIUM)

**What:** No mood evaluation runs on incoming messages.

**Impact:** Mood never transitions based on conversation; FSM is dead code.

**Required fix:**
- Track `ignored_count`, `conversation_sentiment`, `task_completion` per session
- Call `evaluate_mood()` after message analysis
- Feed result through `TransitionRuleEngine.evaluate()`
- Apply transition via `MoodRepository.set_current_mood()` + `record_mood_transition()`

**Files affected:** `src/discord/bot.py` or dedicated message analyzer

---

## 11. Type Safety Verification

| Check | Result | Notes |
|---|---|---|
| `Mood` enum vs mood strings | ✅ Compatible | `Mood.CONTENT.value == "Content"`; lowercase keys in `cmd_mood._MOOD_EMOJI` |
| `SafetyState` vs `SafeModeState` | ⚠️ Different types | Not used together — bridge needed |
| `SupportsIsSafe` protocol | ✅ Compatible | Duck-typed `is_safe: bool`; works with `HardStopHandler` |
| `PersonaState.state_value` JSONB | ✅ Compatible | All P4 modules write valid JSON-serializable dicts |
| `DriftLog.delta` JSONB | ✅ Compatible | `drift_corrector.py` writes flat dict with valid types |
| `PunishmentLevel` IntEnum | ✅ Compatible | `int(level)` for severity column |
| `DistressLevel` IntEnum vs `safe_mode: bool` | ✅ Compatible | `ctx.distress_level >= 2` maps to D2+ |
| `RewardTier` IntEnum | ✅ Compatible | `int(tier)` for DB storage |

---

## 12. Import Dependency Map

### P4 → Existing (imports P4 makes FROM existing code)

| P4 Module | Imports From | Symbols |
|---|---|---|
| `mood_persistence.py` | `src.memory.models` | `MoodHistory`, `PersonaState` |
| `streak_tracker.py` | `src.memory.models` | `PersonaState` |
| `drift_corrector.py` | `src.memory.models` | `DriftLog` |
| `drift_corrector.py` | `src.persona.drift_detector` | `DriftDetector`, `DriftResult` |
| `drift_corrector.py` | `src.persona.safe_mode` | `SafeModeController` |
| `punishment_engine.py` | `src.persona.safe_mode` | `DistressLevel`, `SafeModeController` |
| `ritual_scheduler.py` | `apscheduler.schedulers.asyncio` | `AsyncIOScheduler` |
| `ritual_scheduler.py` | `apscheduler.triggers.cron` | `CronTrigger` |

### Existing → P4 (imports existing code makes FROM P4)

| Existing Module | Imports From P4 | Status |
|---|---|---|
| `cmd_mood.py` | None | ❌ Should import P4 data |
| `cmd_safeword.py` | None | ❌ Should bridge safe mode |
| `bot.py` | None | ❌ Should consult P4 state |
| `prompt_loader.py` | None | ⚠️ Receives mood from caller |
| `consolidation.py` | None | ✅ Correctly isolated |
| `hard_stop_handler.py` | None | ⚠️ Should bridge to P4 |
| `read_pipeline.py` | None | ✅ Correctly isolated |

---

## 13. Priority Matrix

| ID | Missing Integration | Priority | Effort | Safety Impact |
|---|---|---|---|---|
| MISSING-01 | Dual safe-mode bridge | **P0** | Medium | Critical — safety |
| MISSING-06 | bot.py distress detection | **P0** | Medium | Critical — safety |
| MISSING-08 | Safe mode consultation | **P0** | Low | Critical — safety |
| MISSING-02 | cmd_mood.py P4 wiring | **P1** | Medium | Feature — UX |
| MISSING-03 | PunishmentLog persistence | **P1** | Low | Audit trail |
| MISSING-04 | RewardLog persistence | **P1** | Low | Audit trail |
| MISSING-05 | YandereEngine persistence | **P1** | Low | State continuity |
| MISSING-09 | Mood evaluation on messages | **P2** | High | Feature — persona |
| MISSING-07 | prompt_loader mood injection | **P2** | Low | Feature — UX |

---

## 14. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-02 | Guinevere (P4 audit) | Initial integration points audit — 8 existing modules × 12 P4 modules |

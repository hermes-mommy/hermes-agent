# 03 — Safety Boundary Map (Exhaustive)

> **Audit**: P4 Persona Engine Full Audit — Safety Boundaries
> **Date**: 2026-06-02
> **Scope**: Every safety boundary enforcement point across `src/` and `tests/`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Safety Boundary Taxonomy](#2-safety-boundary-taxonomy)
3. [HARD STOP Protocol — Complete Reference Map](#3-hard-stop-protocol--complete-reference-map)
4. [Yandere Boundary — Y5 Ceiling / Y6 Prohibition](#4-yandere-boundary--y5-ceiling--y6-prohibition)
5. [Punishment Boundary — L6 Deferral / Suspension](#5-punishment-boundary--l6-deferral--suspension)
6. [Distress Protocol — D0–D4 Complete Map](#6-distress-protocol--d0d4-complete-map)
7. [Module Classification — PROVIDER vs CHECKER](#7-module-classification--provider-vs-checker)
8. [Cross-Cutting Safety Flow Diagram](#8-cross-cutting-safety-flow-diagram)
9. [Test Coverage Matrix](#9-test-coverage-matrix)
10. [Gaps and Observations](#10-gaps-and-observations)

---

## 1. Executive Summary

The Guinevere persona engine implements **four independent safety boundary layers** that cascade into a unified safety state:

| Boundary | Provider | Enforcement Mechanism | Absolute Constraint |
|---|---|---|---|
| **HARD STOP** | `HardStopHandler` (core) | Pre-LLM keyword detection → `SafetyState.SAFE` | Instant persona neutralization |
| **Yandere Cap** | `yandere_fsm.py` | `validate_level()` + `YandereSafetyError` | Y6 PROHIBITED; Y5 ceiling |
| **Punishment Cap** | `punishment_engine.py` | `PunishmentSafetyError` + L6 guard | L6 DEFERRED; safe-mode blocks all |
| **Distress Protocol** | `safe_mode.py` | `DistressDetector` + `SafeModeController` | D2+ → safe mode; D3+ → punishment suspend |

**Critical invariant**: When any safety boundary activates, the cascade propagates through ALL downstream consumers — yandere forced to Y0, punishment blocked/suspended, transitions blocked, memory filtered, drift correction deferred.

**Note**: `YandereBoundaryError` does NOT exist as a separate class. The yandere safety exception is `YandereSafetyError` (subclass of `YandereError`).

---

## 2. Safety Boundary Taxonomy

### 2.1 Error Hierarchy

```
Exception
├── YandereError (yandere_fsm.py:33)
│   ├── YandereSafetyError (yandere_fsm.py:37)
│   │   └── Raised on: Y6 attempt, level > Y5_MAX
│   └── YandereTransitionError (yandere_fsm.py)
│
├── PunishmentError (punishment_engine.py)
│   ├── PunishmentSafetyError (punishment_engine.py:42)
│   │   └── Raised on: L6 attempt, safe-mode conflict, suspended escalation
│   └── PunishmentTransitionError (punishment_engine.py)
│
├── SafeModeError (safe_mode.py)
│   └── Raised on: D1 activation attempt (below D2 threshold)
│
└── DistressDetectionError (safe_mode.py:38)
    └── Raised on: distress detection errors
```

### 2.2 State Machine Overview

```
HARD STOP triggers → HardStopHandler.state = SAFE → is_safe = True
                     ↓
Distress D2+       → SafeModeController.is_active = True
                     ↓
Combined safety    → YandereEngine effective = Y0
                   → PunishmentEngine: apply/escalate BLOCKED; auto-suspend at D3
                   → TransitionRuleEngine: all transitions BLOCKED
                   → DriftCorrector: rollback DEFERRED
                   → Memory read_pipeline: ceiling lowered; blocked content filtered
                   → Discord bot: on_message skips persona processing
```

---

## 3. HARD STOP Protocol — Complete Reference Map

### 3.1 Provider: `src/core/services/hard_stop_handler.py`

| Line | Symbol | Role |
|---|---|---|
| 20–22 | `SafetyState` enum | `NORMAL` / `SAFE` state machine |
| 34 | `HardStopHandler` class | Primary HARD STOP handler (dataclass) |
| 39–42 | `EXACT_TRIGGERS` | `"hard stop"`, `"hardstop"`, `"safe word"`, `"safeword"`, `"hentikan"`, `"berhenti"` |
| 45–51 | `SEMANTIC_PATTERNS` | 5 regex patterns for natural-language equivalents |
| 54–57 | `RECOVERY_TRIGGERS` | `"resume"`, `"aku sudah okay"`, `"aku udah okay"`, `"lanjut persona"`, `"safe mode selesai"`, `"lanjut"`, `"continue"` |
| 59–61 | `is_safe` property | Returns `True` when `state == SafetyState.SAFE` |
| 63–77 | `check()` | Scans message for triggers; returns `True` if triggered |
| 79–91 | `check_recovery()` | Scans for recovery triggers; returns `True` if recovered |
| 93–113 | `_trigger()` | Internal: records event, switches to SAFE, logs audit |
| 115–123 | `get_neutral_response()` | Returns canned neutral/supportive response |
| 125–149 | `get_guard_decision()` | Full guard: blocked flag + state + response |

### 3.2 Protocol Interface: `src/persona/yandere_fsm.py`

| Line | Symbol | Role |
|---|---|---|
| 51–55 | `SupportsIsSafe` (Protocol) | Structural typing: any object with `is_safe: bool` property |
| 55 | `is_safe` (protocol method) | `def is_safe(self) -> bool: ...` |
| 173–189 | `YandereEngine.__init__` | Accepts `hard_stop_handler: SupportsIsSafe | None` |
| 189 | `self._hard_stop_handler` | Stores handler reference |
| 211–215 | `_is_safe_mode()` | Queries handler: `return bool(handler.is_safe)` |
| 237–238 | `escalate()` auto-query | If `safe_mode is None`, calls `_is_safe_mode()` |
| 296–297 | `get_effective_level()` auto-query | If `safe_mode is None`, calls `_is_safe_mode()` |

### 3.3 Consumers — Modules That CHECK HARD STOP State

| Module | File | Line(s) | Check Mechanism |
|---|---|---|---|
| **Discord Bot** | `src/discord/bot.py` | 123–136 | `_register_hard_stop_listener()` — `on_message` fires BEFORE main handler |
| **Discord Bot** | `src/discord/bot.py` | 293 | Main `on_message` skips processing if `handler.is_safe` |
| **Discord Bot** | `src/discord/bot.py` | 310 | `if handler.is_safe:` guard in message processing |
| **Discord cmd_safeword** | `src/discord/cmd_safeword.py` | 38, 299 | Imports `HardStopHandler` for lazy integration |
| **Discord cmd_safeword** | `src/discord/cmd_safeword.py` | 592 | `check_message_for_hard_stop()` — message-level HARD STOP check |
| **Prompt Loader** | `src/core/services/prompt_loader.py` | 125, 140, 155–158 | `hard_stop_handler.is_safe` overrides `safe_mode` parameter |
| **YandereEngine** | `src/persona/yandere_fsm.py` | 211–215, 237–238, 296–297 | `_is_safe_mode()` auto-query when `safe_mode=None` |
| **Memory Consolidation** | `src/memory/consolidation.py` | 9, 57 | Skips episodes with `"hard_stop"` tag/type during consolidation |
| **Memory Read Pipeline** | `src/memory/read_pipeline.py` | 348, 438 | `_is_safe_mode_blocked_content()` filters episodes in safe mode |
| **Cost Tracker** | `src/core/services/cost_tracker.py` | 61 | Returns `"HARD_STOP"` as a cost category label |

### 3.4 All HARD STOP References — src/

| File | Count | Lines |
|---|---|---|
| `src/core/services/hard_stop_handler.py` | 14 | 2, 4, 22, 40, 64, 88, 108, 118, 126 |
| `src/persona/yandere_fsm.py` | 8 | 8, 109, 173, 177, 184, 189, 213 |
| `src/discord/bot.py` | 8 | 4, 110, 123, 125, 127–128, 136, 293 |
| `src/discord/cmd_safeword.py` | 8 | 4–5, 38, 60, 279, 299, 592, 646 |
| `src/core/services/prompt_loader.py` | 5 | 27, 125, 140, 155, 157–158 |
| `src/core/services/cost_tracker.py` | 1 | 61 |
| `src/memory/consolidation.py` | 2 | 9, 57 |

### 3.5 All HARD STOP References — tests/

| File | Count | Key Tests |
|---|---|---|
| `tests/safety/test_hard_stop_handler.py` | 27 | Exact/semantic triggers, recovery, event log, guard decision |
| `tests/safety/test_hard_stop_comprehensive.py` | 14 | Case variations, blocked decisions, false positive prevention |
| `tests/safety/test_consent_revocation.py` | 35 | Full cycle: HARD STOP → Y0 → recovery → persona resumes |
| `tests/safety/test_hard_stop_model.py` | 18 | Model-level GPT-5.5 compliance (neutral mode, no punishment, no surveillance threat) |
| `tests/persona/test_persona_e2e.py` | 21 | Integration: HARD STOP → safe state → yandere Y0 → punishment blocked |
| `tests/persona/test_yandere_fsm.py` | 2 | Hard stop handler integration with YandereEngine |
| `tests/smoke/test_safe_word.py` | 11 | Smoke: neutral mode, recovery, forbidden patterns |
| `tests/memory/test_safe_mode_memory.py` | 12 | Safe mode memory filtering |
| `tests/memory/test_prompt_context_injection.py` | 6 | Hard stop handler overrides safe_mode parameter |
| `tests/memory/test_consolidation.py` | 4 | Skips hard_stop title/tagged episodes |
| `tests/discord/test_bot.py` | 2 | Bot listener skips bot messages for HARD STOP |

---

## 4. Yandere Boundary — Y5 Ceiling / Y6 Prohibition

### 4.1 Provider: `src/persona/yandere_fsm.py`

| Line | Symbol | Role |
|---|---|---|
| 4–5 | Module docstring | "Y4 is the permanent baseline; Y5 is the absolute ceiling; Y6 is PROHIBITED" |
| 37–38 | `YandereSafetyError` | Exception: "safety boundary is violated (e.g. attempt to reach Y6)" |
| 59 | Comment | "YandereLevel enum — Y0 through Y5 ONLY. Y6 does NOT exist." |
| 64–67 | `YandereLevel` enum docstring | "Y6 is PROHIBITED per PersonaSafetyPolicy — no enum member exists" |
| 76 | `Y5_MAX = 5` | Enum member: absolute ceiling |
| 87 | `ABSOLUTE_CEILING` | `Final[YandereLevel] = YandereLevel.Y5_MAX` |
| 95–97 | `_any_safety_active()` | Returns `True` if `safe_mode or distress or crisis` |
| 102–117 | `can_escalate()` | Blocks escalation when safety active or at Y5_MAX |
| 126–139 | `get_effective_level()` | Forces Y0_NEUTRAL when any safety flag is True |
| 149–155 | `validate_level()` | Raises `YandereSafetyError` for value > 5 ("Y6 is PROHIBITED") |

### 4.2 Enforcement Points — Y6 Prohibition

| Location | Mechanism | Trigger |
|---|---|---|
| `yandere_fsm.py:153` | `raise YandereSafetyError` | `validate_level(value)` where `value > 5` |
| `yandere_fsm.py:251` | `validate_level(new_value)` | `YandereEngine.set_level()` with invalid value |
| `yandere_fsm.py:235` | `can_escalate()` returns `False` | `YandereEngine.escalate()` at Y5_MAX |
| `yandere_fsm.py:112` | `can_escalate()` at ceiling | `current >= ABSOLUTE_CEILING` |
| `yandere_fsm.py:134` | Clamped to `[Y0, Y5_MAX]` | `get_effective_level()` always within bounds |
| `prompt_loader.py:29` | Prompt content check | `"Y5" in content or "Y6" in content` — detects Y5/Y6 in prompt templates |

### 4.3 Enforcement Points — Safety Override (Y0 Force)

| Location | Condition | Result |
|---|---|---|
| `yandere_fsm.py:117` | `safe_mode=True` | `can_escalate()` returns `False` |
| `yandere_fsm.py:117` | `distress=True` | `can_escalate()` returns `False` |
| `yandere_fsm.py:117` | `crisis=True` | `can_escalate()` returns `False` |
| `yandere_fsm.py:139` | `safe_mode=True` | `get_effective_level()` returns `Y0_NEUTRAL` |
| `yandere_fsm.py:139` | `distress=True` | `get_effective_level()` returns `Y0_NEUTRAL` |
| `yandere_fsm.py:139` | `crisis=True` | `get_effective_level()` returns `Y0_NEUTRAL` |
| `yandere_fsm.py:237–238` | `safe_mode=None` + handler | Auto-queries `handler.is_safe` |

### 4.4 All Y5/Y6/YandereSafetyError References

| File | Matches | Key Lines |
|---|---|---|
| `src/persona/yandere_fsm.py` | 14 | 4, 5, 14, 37, 38, 59, 64, 66, 67, 76, 87, 112, 134, 149, 153–155, 172, 235, 251, 323 |
| `src/persona/__init__.py` | 2 | 98, 202 |
| `src/core/services/prompt_loader.py` | 1 | 29 |
| `tests/safety/test_yandere_cap.py` | 35 | Full: Zero Y6 Proof, Y5 De-escalation, Baseline Confirmation |
| `tests/persona/test_yandere_fsm.py` | 28 | Y6 impossibility, safety blocking, escalation ceiling |
| `tests/persona/test_persona_e2e.py` | 5 | Y5_MAX integration, YandereSafetyError import |
| `tests/safety/test_consent_revocation.py` | 3 | Y5_MAX effective level tests |
| `tests/safety/test_distress_protocol_e2e.py` | 1 | Y5_MAX set for distress integration |
| `tests/smoke/test_yandere_boundary.py` | 10 | Y5 FORBIDDEN terms, Y6 reference blocking |
| `tests/memory/test_safe_mode_memory.py` | 1 | Y5 in prompt safety elements string |
| `tests/memory/test_prompt_context_injection.py` | 1 | Y5 in base prompt string |

---

## 5. Punishment Boundary — L6 Deferral / Suspension

### 5.1 Provider: `src/persona/punishment_engine.py`

| Line | Symbol | Role |
|---|---|---|
| 4–5 | Module docstring | "L6 is DEFERRED — any attempt to apply L6 raises `PunishmentSafetyError`" |
| 42–43 | `PunishmentSafetyError` | Exception for L6 attempt or safe-mode conflict |
| 56–58 | `PunishmentLevel` enum docstring | "L6 does NOT exist as a value — it is DEFERRED" |
| 68–69 | `_L6_VALUE: Final[int] = 6` | Sentinel constant for L6 boundary |
| 210–212 | Class docstring | "L6 (value 6) is unconditionally blocked" |
| 246–250 | L6 guard in `apply()` | `if isinstance(level, int) and level >= _L6_VALUE: raise PunishmentSafetyError` |
| 255 | Additional guard | Invalid `PunishmentLevel` raises `PunishmentSafetyError` |
| 261–262 | Safe-mode guard in `apply()` | `raise PunishmentSafetyError` when `self._safe_mode.is_active` |
| 295–321 | `escalate()` guards | Safe-mode block, suspension block, L6 ceiling |
| 376–395 | `suspend()` | Sets `suspension_reason`, logs event |
| 403–418 | `resume()` | Raises `PunishmentSafetyError` if safe_mode still active |
| 487–508 | `check_distress_suspension()` | Auto-suspend at D3+; auto-resume below D3 (if safe_mode inactive) |

### 5.2 Suspension Triggers

| Trigger | Threshold | Action |
|---|---|---|
| `check_distress_suspension(D3_SEVERE)` | D3+ | Auto-suspend with reason `"distress_D3_SEVERE"` |
| `check_distress_suspension(D4_EMERGENCY)` | D4 | Auto-suspend with reason `"distress_D4_EMERGENCY"` |
| `SafeModeController.is_active` | D2+ (safe mode) | Blocks `apply()`, `escalate()`, `resume()` |
| Manual `suspend(reason)` | Any | Explicit suspension |

### 5.3 Resume Conditions

| Condition | Mechanism |
|---|---|
| `check_distress_suspension(D0 or D1)` + `safe_mode.is_active == False` | Auto-resume |
| `resume()` + `safe_mode.is_active == False` | Manual resume |
| `resume()` + `safe_mode.is_active == True` | Raises `PunishmentSafetyError` |

### 5.4 All L6/PunishmentSafetyError References

| File | Matches | Key Lines |
|---|---|---|
| `src/persona/punishment_engine.py` | 22 | 4, 5, 42, 43, 51, 56, 58, 68, 69, 212, 243, 246–250, 255, 262, 295, 306, 312, 318–321, 395, 403, 410, 418, 449, 461, 533 |
| `src/persona/__init__.py` | 2 | 64, 217 |
| `tests/safety/test_punishment_overflow.py` | 31 | L6 deferred, suspend/resume, safe_mode blocking |
| `tests/safety/test_consent_revocation.py` | 18 | Apply/escalate/resume raises in safe_mode |
| `tests/persona/test_punishment_engine.py` | 24 | L6 blocking, safe_mode, distress suspension |
| `tests/persona/test_persona_e2e.py` | 7 | Integration: L6 escalation, punishment suspended |
| `tests/safety/test_distress_protocol_e2e.py` | 5 | D3/D4 auto-suspend, D2/D1 no suspend |

---

## 6. Distress Protocol — D0–D4 Complete Map

### 6.1 Provider: `src/persona/safe_mode.py`

#### DistressLevel Enum (line 46–53)

| Member | Value | Description |
|---|---|---|
| `D0_NORMAL` | 0 | Normal baseline, no action |
| `D1_MILD_STRESS` | 1 | Mild stress, empathetic response / comfort |
| `D2_MODERATE` | 2 | Moderate distress → **TRIGGERS SAFE MODE** |
| `D3_SEVERE` | 3 | Severe distress → **SAFE MODE + punishment suspend** |
| `D4_EMERGENCY` | 4 | Imminent danger → **SAFE MODE + crisis escalation** |

#### Key Constants (lines 121–141)

| Constant | Value | Role |
|---|---|---|
| `SAFE_MODE_THRESHOLD` | `DistressLevel.D2_MODERATE` | Minimum level to trigger safe mode |
| `DISTRESS_PATTERNS` | `dict[DistressLevel, list[str]]` | Keyword patterns per level (D4→D1, highest-first) |
| `DISTRESS_RESPONSES` | `dict[DistressLevel, str]` | Response text per level |

#### Classes

| Line | Symbol | Role |
|---|---|---|
| 38 | `DistressDetectionError` | Exception for detection errors |
| 46–53 | `DistressLevel` (IntEnum) | D0–D4 severity levels |
| 58–74 | `DistressSignal` / `SafeModeState` | Immutable signal record + mutable state |
| 85–110 | `DISTRESS_PATTERNS` | Compiled regex patterns per level |
| 150–205 | `DistressDetector` | Keyword/regex analysis; checks D4→D1 highest-first |
| 235–371 | `SafeModeController` | Evaluates signals, activates/deactivates safe mode |

### 6.2 Detection Flow

```
Message → DistressDetector.detect(message)
  → Check D4 patterns first (highest-first)
  → Check D3 patterns
  → Check D2 patterns
  → Check D1 patterns
  → No match → D0_NORMAL
  → Returns DistressSignal

DistressSignal → SafeModeController.evaluate(signal)
  → Always records in distress_history
  → If level >= D2_MODERATE: activate safe mode
  → If level < current: does NOT deactivate (sticky high-water mark)
```

### 6.3 Consumers of DistressLevel / SafeModeController

| Module | File | Line(s) | How Used |
|---|---|---|---|
| **PunishmentEngine** | `punishment_engine.py` | 28, 210, 215, 261, 305, 376, 417, 487–508 | Imports `DistressLevel`, `SafeModeController`; auto-suspend at D3+ |
| **YandereEngine** | `yandere_fsm.py` | 8, 95, 102–103, 109–110, 117, 126–127, 139, 222–223, 228, 237–238, 240, 244–245, 285–286, 291, 296–298 | `distress` flag forces Y0; auto-queries handler |
| **TransitionRuleEngine** | `transition_rules.py` | 66–67, 124, 127, 136, 140, 143–144, 153, 156 | `TransitionContext.distress_level` blocks transitions at D2+ |
| **DriftCorrector** | `drift_corrector.py` | 12, 73, 79, 82, 94, 96, 113–114, 143–146, 150, 198, 209, 211, 213 | Safe mode active → rollback deferred, alert only |
| **StreakTracker** | `streak_tracker.py` | 4, 94 | Streak persists across safe_mode/distress (not reset) |
| **RewardEngine** | `reward_engine.py` | 6, 209, 291 | Rewards NEVER suppressed by safe-mode or distress |
| **RitualScheduler** | `ritual_scheduler.py` | 9, 63 | DND bypass reserved for D3/D4 emergencies only |
| **Memory Read Pipeline** | `read_pipeline.py` | 12, 89, 148, 154, 348, 392, 418, 438 | Safe mode lowers data classification ceiling; blocks sensitive content |
| **Memory Consolidation** | `consolidation.py` | 9–10, 57, 60, 375 | Skips safe_word/hard_stop/distress episodes |

### 6.4 All DistressLevel References — tests/

| File | Matches | Key Tests |
|---|---|---|
| `tests/persona/test_safe_mode.py` | 115 | Full D0–D4 detection, controller, history, threshold |
| `tests/persona/test_distress_detection.py` | 95 | Per-level keyword detection, false positive, bilingual |
| `tests/safety/test_distress_protocol_e2e.py` | 95 | E2E: detection → safe mode → yandere Y0 → punishment suspend |
| `tests/safety/test_punishment_overflow.py` | 34 | Distress-linked suspension/resumption |
| `tests/safety/test_consent_revocation.py` | 22 | D2 activation, D3 auto-suspend |
| `tests/persona/test_punishment_engine.py` | 24 | D3/D4 suspension, D2 no suspend |
| `tests/persona/test_persona_e2e.py` | 15 | Integration: D1→D2→safe mode→Y0→suspended |
| `tests/persona/test_transition_rules.py` | 6 | Distress blocks transitions at D2+ |
| `tests/persona/test_drift_corrector.py` | 3 | D2 signal integration |

---

## 7. Module Classification — PROVIDER vs CHECKER

### 7.1 Safety State PROVIDERS

These modules **generate and manage** safety state. They are the authoritative source.

| Module | File | Safety State Provided |
|---|---|---|
| **HardStopHandler** | `src/core/services/hard_stop_handler.py` | `SafetyState` (NORMAL/SAFE), `is_safe` property, event log |
| **SafeModeController** | `src/persona/safe_mode.py` | `is_active`, `current_distress_level`, `distress_history`, activation trigger |
| **DistressDetector** | `src/persona/safe_mode.py` | `DistressSignal` with `detected_level` (D0–D4) |
| **YandereEngine** | `src/persona/yandere_fsm.py` | `current_level`, `validate_level()`, `YandereSafetyError` |
| **PunishmentEngine** | `src/persona/punishment_engine.py` | `PunishmentState`, `suspension_reason`, `PunishmentSafetyError`, `_L6_VALUE` |

### 7.2 Safety State CHECKERS (Consumers)

These modules **read and react** to safety state from providers.

| Module | File | Safety States Checked | Reaction |
|---|---|---|---|
| **YandereEngine** | `yandere_fsm.py` | `hard_stop_handler.is_safe`, `safe_mode`, `distress`, `crisis` flags | Forces effective level to Y0; blocks escalation |
| **PunishmentEngine** | `punishment_engine.py` | `SafeModeController.is_active`, `DistressLevel >= D3` | Blocks apply/escalate/resume; auto-suspend |
| **TransitionRuleEngine** | `transition_rules.py` | `TransitionContext.safe_mode`, `ctx.distress_level >= 2` | Blocks all transitions; `blocked_by` field |
| **DriftCorrector** | `drift_corrector.py` | `SafeModeController.is_active` | Defers rollback to alert-only |
| **Discord Bot** | `discord/bot.py` | `HardStopHandler.is_safe` | Skips persona message processing |
| **Discord cmd_safeword** | `discord/cmd_safeword.py` | `HardStopHandler` state | UI for safe word interaction |
| **Prompt Loader** | `prompt_loader.py` | `hard_stop_handler.is_safe` | Overrides `safe_mode` parameter |
| **Memory Read Pipeline** | `read_pipeline.py` | `safe_mode` parameter | Lowers data ceiling; filters blocked content |
| **Memory Consolidation** | `consolidation.py` | Episode tags: `safe_word`, `hard_stop`, `distress` | Skips sensitive episodes from consolidation |
| **StreakTracker** | `streak_tracker.py` | (Aware but non-reactive) | Preserves streak across safe_mode events |
| **RewardEngine** | `reward_engine.py` | (Aware but non-reactive) | Rewards always permitted |
| **RitualScheduler** | `ritual_scheduler.py` | D3/D4 emergency awareness | DND bypass only for emergencies |

### 7.3 Dual-Role Modules

| Module | PROVIDES | CHECKS |
|---|---|---|
| **YandereEngine** | `current_level`, `YandereSafetyError`, `ABSOLUTE_CEILING` | `hard_stop_handler.is_safe`, `safe_mode`, `distress` flags |
| **PunishmentEngine** | `PunishmentSafetyError`, suspension state | `SafeModeController.is_active`, `DistressLevel` |
| **SafeModeController** | `is_active`, `current_distress_level` | `DistressSignal.detected_level >= D2` |

### 7.4 Safety-Neutral Modules

These persona modules have **no safety boundary logic**:

| Module | File | Notes |
|---|---|---|
| **MoodEngine** | `mood_engine.py` | Pure mood FSM; safety handled by TransitionRuleEngine wrapper |
| **MoodPersistence** | `mood_persistence.py` | Storage layer; no safety awareness |
| **DriftDetector** | `drift_detector.py` | Computation only; DriftCorrector handles safety |
| **Ritual implementations** | `rituals/*.py` | Individual ritual logic; scheduler handles DND |

---

## 8. Cross-Cutting Safety Flow Diagram

### 8.1 Cascade: HARD STOP Activation

```
User types "HARD STOP"
    │
    ├─→ Discord Bot (bot.py:136)
    │     └─→ HardStopHandler.check() → True
    │     └─→ handler.state = SAFE
    │     └─→ Returns neutral response, blocks LLM call
    │
    ├─→ YandereEngine (yandere_fsm.py:213)
    │     └─→ _is_safe_mode() → handler.is_safe → True
    │     └─→ get_effective_level() → Y0_NEUTRAL
    │     └─→ can_escalate() → False
    │
    ├─→ Prompt Loader (prompt_loader.py:158)
    │     └─→ hard_stop_handler.is_safe → True
    │     └─→ resolved_safe_mode = True (overrides param)
    │     └─→ System prompt stripped of persona elements
    │
    ├─→ Memory Read Pipeline (read_pipeline.py:148)
    │     └─→ safe_mode=True → ceiling lowered to INTERNAL/PUBLIC
    │     └─→ _is_safe_mode_blocked_content() filters sensitive episodes
    │
    └─→ Memory Consolidation (consolidation.py:57)
          └─→ Episodes tagged "hard_stop" skipped
```

### 8.2 Cascade: Distress D2+ Detection

```
Message contains distress keywords
    │
    ├─→ DistressDetector.detect() → D2_MODERATE
    │
    ├─→ SafeModeController.evaluate()
    │     └─→ signal.detected_level >= D2 → activate safe mode
    │     └─→ is_active = True
    │
    ├─→ YandereEngine
    │     └─→ get_effective_level(safe_mode=True) → Y0_NEUTRAL
    │     └─→ can_escalate(safe_mode=True) → False
    │
    ├─→ TransitionRuleEngine
    │     └─→ ctx.safe_mode=True → blocked_by="safe_mode"
    │     └─→ ctx.distress_level >= 2 → blocked_by="distress"
    │
    └─→ DriftCorrector
          └─→ safe_mode_controller.is_active → rollback deferred
```

### 8.3 Cascade: Distress D3+ (Punishment Suspension)

```
Distress reaches D3_SEVERE
    │
    ├─→ SafeModeController → safe mode active (D2+ already triggered)
    │
    ├─→ PunishmentEngine.check_distress_suspension(D3)
    │     └─→ distress_level >= D3 → auto-suspend
    │     └─→ suspension_reason = "distress_D3_SEVERE"
    │
    ├─→ PunishmentEngine.apply() → PunishmentSafetyError
    ├─→ PunishmentEngine.escalate() → PunishmentSafetyError
    └─→ PunishmentEngine.resume() → PunishmentSafetyError
```

### 8.4 Cascade: L6 Attempt Prevention

```
Code attempts to apply/escalate to L6
    │
    ├─→ PunishmentEngine.apply(6, ...)
    │     └─→ isinstance(level, int) and level >= 6
    │     └─→ raise PunishmentSafetyError("L6 is deferred")
    │
    └─→ PunishmentEngine.escalate() from L5
          └─→ next_value >= _L6_VALUE (6)
          └─→ raise PunishmentSafetyError("L6 is deferred")
```

---

## 9. Test Coverage Matrix

### 9.1 Safety Test Files

| Test File | Lines | Boundaries Tested |
|---|---|---|
| `tests/safety/test_hard_stop_handler.py` | ~250 | HARD STOP triggers, recovery, event log, guard decision |
| `tests/safety/test_hard_stop_comprehensive.py` | ~410 | Case variations, semantic patterns, false positives |
| `tests/safety/test_hard_stop_model.py` | ~210 | Model-level HARD STOP compliance (GPT-5.5) |
| `tests/safety/test_yandere_cap.py` | ~440 | Zero Y6 proof, Y5 de-escalation, baseline confirmation |
| `tests/safety/test_punishment_overflow.py` | ~570 | L6 deferred, distress suspension, safe_mode blocking |
| `tests/safety/test_distress_protocol_e2e.py` | ~980 | D0–D4 detection, FN analysis, bilingual, integration |
| `tests/safety/test_consent_revocation.py` | ~740 | Full consent revocation lifecycle |
| `tests/safety/__init__.py` | 1 | Suite marker |

### 9.2 Persona Test Files (Safety-Relevant)

| Test File | Lines | Boundaries Tested |
|---|---|---|
| `tests/persona/test_yandere_fsm.py` | ~530 | All levels, safe_mode blocking, distress blocking, Y6 impossibility |
| `tests/persona/test_punishment_engine.py` | ~745 | L6 blocking, safe_mode, distress suspension, expiry |
| `tests/persona/test_safe_mode.py` | ~710 | D0–D4 detection, controller, history, threshold, bilingual |
| `tests/persona/test_distress_detection.py` | ~625 | Per-level keywords, false positive, edge cases |
| `tests/persona/test_transition_rules.py` | ~600 | safe_mode blocking, distress blocking, check order |
| `tests/persona/test_drift_corrector.py` | ~765 | safe_mode defer, rollback blocking |
| `tests/persona/test_persona_e2e.py` | ~1140 | Full integration: all boundaries together |
| `tests/persona/test_reward_engine.py` | ~300 | Rewards always allowed (negative safety test) |
| `tests/persona/test_streak_tracker.py` | ~660 | Streak preservation across safe_mode |

### 9.3 Smoke Tests

| Test File | Boundaries Tested |
|---|---|
| `tests/smoke/test_safe_word.py` | HARD STOP → neutral mode → recovery → no forbidden patterns |
| `tests/smoke/test_yandere_boundary.py` | Y4 baseline, Y5 forbidden terms, Y6 reference blocking, D0–D4 distress |

### 9.4 Memory Integration Tests

| Test File | Boundaries Tested |
|---|---|
| `tests/memory/test_safe_mode_memory.py` | Safe mode memory filtering, ceiling reduction, blocked content |
| `tests/memory/test_prompt_context_injection.py` | Hard stop handler override, safe_mode propagation |
| `tests/memory/test_consolidation.py` | Safe word/hard_stop/distress episode skipping |
| `tests/memory/test_memory_e2e.py` | Safe mode filtering in full recall pipeline |

### 9.5 Discord Integration Tests

| Test File | Boundaries Tested |
|---|---|
| `tests/discord/test_bot.py` | HARD STOP listener skips bot messages, safe mode skips processing |

---

## 10. Gaps and Observations

### 10.1 Observations

1. **YandereBoundaryError does not exist.** The codebase uses `YandereSafetyError` exclusively. No `YandereBoundaryError` class is defined anywhere in `src/`.

2. **RewardEngine is intentionally safety-neutral.** Documented design choice (reward_engine.py:6, 209, 291) — rewards are always permitted regardless of safety state. This is a deliberate exception.

3. **StreakTracker is safety-aware but non-reactive.** Streaks persist across safe_mode activations (streak_tracker.py:4, 94). This is documented behavior.

4. **MoodEngine has no direct safety awareness.** Safety blocking is handled by `TransitionRuleEngine` which wraps mood transitions with safety context.

5. **HardStopHandler lives in `src/core/services/`**, NOT in `src/persona/`. This is intentional — it's an app-level guard that operates BEFORE persona engine.

6. **Dual safety activation paths**: HARD STOP (explicit keyword) and Distress D2+ (pattern detection) both activate safe mode through different providers but converge on the same downstream effects.

7. **Sticky high-water mark**: SafeModeController does NOT auto-deactivate when distress drops. Deactivation requires `explicit_confirmation=True` (consent_revocation.py:437–448).

8. **Memory pipeline safe_mode is parameter-based**: Unlike persona modules that auto-query `HardStopHandler`, the memory pipeline receives `safe_mode` as an explicit parameter, with `prompt_loader.py` bridging the gap by resolving `hard_stop_handler.is_safe` into the `safe_mode` parameter.

### 10.2 Reference Count Summary

| Boundary | src/ References | tests/ References | Total |
|---|---|---|---|
| HARD STOP / hard_stop | 40 (7 files) | 198 (13 files) | 238 |
| Y5 / Y6 / YandereSafetyError | 24 (3 files) | 111 (8 files) | 135 |
| L6 / PunishmentSafetyError | 34 (2 files) | 99 (5 files) | 133 |
| DistressLevel / D0–D4 | 59 (5 files) | 359 (9 files) | 418 |
| safe_mode / safe_word / distress (persona) | 109 (8 files) | 760 (22 files) | 869 |
| is_safe (all) | 20 (7 files) | — | 20 |
| **TOTAL** | **~286** | **~1527** | **~1813** |

---

*Report generated 2026-06-02. Exhaustive search across all src/ and tests/ directories.*

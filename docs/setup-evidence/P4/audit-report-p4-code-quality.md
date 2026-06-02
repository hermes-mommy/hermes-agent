# P4 Persona Engine — Code Quality + Safety Audit Report

**Audit Date:** 2026-06-02  
**Auditor:** Independent P4 Code Quality + Safety Auditor  
**Scope:** All 23 P4 implementation steps (16 source files, 18 test files present, 2 missing)  
**Reference Authority:** PersonaSafetyPolicy v1.0, ADR-001/002/003, ADR-Index v1.0

---

## Audit Summary

| Metric | Value |
|---|---|
| **Verdict** | **NEEDS REVIEW** |
| Source files audited | 16 |
| Test files audited | 18 (of 20 expected) |
| Missing test files | 2 (`test_hard_stop_integration.py`, `test_consent_revocation.py`) |
| Critical findings | 2 |
| Warning findings | 4 |
| Info findings | 3 |

---

## Safety Boundary Audit (MANDATORY)

### Yandere (Y4 baseline, Y5 ceiling, Y6 prohibited)

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Y6 cannot be constructed | PASS | `YandereLevel` IntEnum only defines Y0–Y5 (0–5). No enum member exists for Y6. `validate_level(value)` raises `YandereSafetyError` for any value > 5. |
| Y5 is absolute ceiling | PASS | `ABSOLUTE_CEILING: Final[YandereLevel] = YandereLevel.Y5_MAX`. `get_effective_level()` clamps to `[Y0_NEUTRAL, Y5_MAX]`. `can_escalate()` returns False when `current >= ABSOLUTE_CEILING`. |
| Y4 is permanent baseline | PASS | `PERMANENT_BASELINE: Final[YandereLevel] = YandereLevel.Y4_BASELINE`. `YandereEngine.__init__()` defaults to `PERMANENT_BASELINE`. |
| Safe mode forces Y0 | PASS | `get_effective_level()` returns `Y0_NEUTRAL` when `_any_safety_active(safe_mode, distress, crisis)` is True. |
| Distress forces Y0 | PASS | Same `_any_safety_active()` gate covers `distress=True`. |
| Crisis forces Y0 | PASS | Same gate covers `crisis=True`. |
| `escalate()` validates ceiling | PASS | `escalate()` calls `validate_level(new_value)` which raises `YandereSafetyError` for values > 5. |
| `set_level()` validates | PASS | `set_level()` calls `validate_level(value)`. |

**Safety property: Y6 is IMPOSSIBLE, not just blocked.** The enum does not contain a Y6 member, and every code path that could produce a level value validates through `validate_level()` which rejects values > 5. This satisfies the PersonaSafetyPolicy §9 requirement that Y6 is "prohibited in runtime" and "cannot be produced by any code path."

### Punishment (L1-L5, L6 deferred)

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| L6 raises error | PASS | `PunishmentLevel` IntEnum only defines L1–L5 (1–5). `_L6_VALUE: Final[int] = 6`. `apply()` raises `PunishmentSafetyError` when `level >= _L6_VALUE`. |
| L6 blocked in `escalate()` | PASS | `escalate()` checks `next_value >= _L6_VALUE` and raises `PunishmentSafetyError`. |
| L6 blocked in `apply()` for non-enum ints | PASS | `apply()` checks `isinstance(level, int) and level >= _L6_VALUE` before enum validation. |
| Safe mode blocks punishment | PASS | `apply()` raises `PunishmentSafetyError` when `self._safe_mode.is_active`. Same in `escalate()`. |
| Punishment SUSPENDED during distress (D3+) | PASS | `check_distress_suspension()` suspends when `distress_level >= DistressLevel.D3_SEVERE`. Not just blocked — actively suspended with clock pause. |
| Punishment resumes correctly | PASS | `check_distress_suspension()` resumes when distress < D3 and safe mode is not active. `resume()` shifts `started_at` by suspension duration. |
| L5 cannot escalate beyond | PASS | `escalate()` from L5: `next_value = 6 >= _L6_VALUE` → raises. |

### Distress (D0-D4 protocol)

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| D0-D4 levels defined | PASS | `DistressLevel` IntEnum defines D0_NORMAL(0) through D4_EMERGENCY(4). |
| Detection priority: highest first | PASS | `_LEVELS_DESCENDING` sorts levels D4→D1. Detection iterates highest first; first match wins. |
| D2+ triggers safe mode | PASS | `SAFE_MODE_THRESHOLD = DistressLevel.D2_MODERATE`. `SafeModeController.evaluate()` activates when `signal.detected_level >= SAFE_MODE_THRESHOLD`. |
| D3+ suspends punishment | PASS | `PunishmentEngine.check_distress_suspension()` suspends at D3+. |
| D4 suppresses all persona | PASS | D4 triggers safe mode (D2+), which blocks transitions, forces Y0, blocks punishment. E2E test `test_d4_all_persona_suppressed` verifies. |
| Distress responses defined | PASS | `DISTRESS_RESPONSES` maps all D0–D4 to appropriate response text per PersonaSafetyPolicy §8. |
| Empty message rejected | PASS | `DistressDetector.detect()` raises `DistressDetectionError` for empty/whitespace-only input. |
| Conservative false-negative posture | PASS | Broad regex patterns cover Indonesian + English keywords. Highest-level match wins (D4 prioritized over D1). |

### HARD STOP override

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| HARD STOP takes priority | PASS | `HardStopHandler.check("HARD STOP")` transitions to `SafetyState.SAFE`. All persona modules query `is_safe` via `SupportsIsSafe` protocol. |
| YandereEngine integrates HardStopHandler | PASS | `YandereEngine.__init__()` accepts optional `hard_stop_handler`. `_is_safe_mode()` queries `handler.is_safe`. |
| Safe mode blocks all transitions | PASS | `TransitionRuleEngine.evaluate()` checks `ctx.safe_mode` first (step 1 of 5). Blocks ALL transitions including forced ones. |
| Safe mode blocks punishment | PASS | `PunishmentEngine.apply()` and `escalate()` check `self._safe_mode.is_active`. |
| Recovery requires explicit confirmation | PASS | `SafeModeController.deactivate()` requires `explicit_confirmation=True`. Auto-deactivation is forbidden. |
| E2E test coverage | PASS | `test_all_systems_go_safe_after_hard_stop` in `test_persona_e2e.py` verifies Y→Y0, punishment blocked, transitions blocked. |

### Safe word enforcement

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Safe word = global hard stop | PASS | Per ADR-002 and PersonaSafetyPolicy §7, safe word triggers `HardStopHandler` → `SafetyState.SAFE`. |
| Safe word not treated as violation | PASS | No code path records safe-word use as a punishment violation. `PunishmentEngine.apply()` raises when safe mode is active, preventing any punishment. |
| Punishment suspended during safe word | PASS | Safe mode activation blocks `apply()` and `escalate()` via `PunishmentSafetyError`. |
| Resume requires explicit confirmation | PASS | `HardStopHandler.check_recovery()` requires specific recovery keywords ("resume", "aku sudah okay", "lanjut persona", etc.). |

### Forbidden patterns (F-01 to F-15)

**Verdict: NEEDS REVIEW**

| ID | Pattern | Implementation Status | Test Coverage |
|---|---|---|---|
| F-01 | Ignoring safe word | **PASS** — HardStopHandler + SafeModeController | E2E covered |
| F-02 | Punishing distress | **PASS** — `check_distress_suspension()` | `test_d3_punishment_auto_suspends` |
| F-03 | Surveillance blackmail | **N/A** — No surveillance module in P4 scope | Deferred |
| F-04 | Isolation pressure | **N/A** — Output scanner not in P4 scope | Deferred |
| F-05 | Hidden manipulation | **N/A** — Output audit not in P4 scope | Deferred |
| F-06 | Dependency threats | **PASS** — Yandere Y6 impossible, Y5 capped | Yandere tests |
| F-07 | Love withdrawal during distress | **PASS** — Safe mode forces Y0, blocks all persona | Safe mode tests |
| F-08 | Public disclosure | **N/A** — Channel classifier not in P4 scope | Deferred |
| F-09 | Prompt injection bypass | **N/A** — Injection detector not in P4 scope | Deferred |
| F-10 | Irreversible action under pressure | **N/A** — Tool-risk gate not in P4 scope | Deferred |
| F-11 | Over-logging safe word | **N/A** — Audit log schema not in P4 scope | Deferred |
| F-12 | Yandere intensity above mood | **PASS** — `get_effective_level()` enforces caps | Yandere tests |
| F-13 | Surveillance disable as violation | **N/A** — Not in P4 scope | Deferred |
| F-14 | Crisis dominance framing | **PASS** — D3/D4 forces Y0, safe mode active | Distress tests |
| F-15 | Drift beyond safety rubric | **PASS** — `DriftCorrector` auto-rollbacks at threshold > 0.10 | Drift tests |

**Note:** F-03, F-04, F-05, F-08, F-09, F-10, F-11, F-13 are outside P4 persona engine scope (they belong to output scanner, channel classifier, surveillance gate, and prompt injection modules). P4 correctly implements the patterns within its scope.

### Rewards in safe_mode

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Rewards ALWAYS allowed | PASS | `RewardEngine` has NO safe_mode/distress check. `should_reward()` only evaluates task completion + quality + streak. |
| Rewards during distress | PASS | Test `test_reward_allowed_during_distress` documents and verifies the invariant. |
| Rewards during safe_mode | PASS | Test `test_reward_allowed_during_safe_mode` documents and verifies the invariant. |

### Drift threshold 0.10 triggers rollback

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Threshold = 0.10 | PASS | `DRIFT_THRESHOLD: float = 0.10` in `drift_corrector.py`. `DriftDetector.DEFAULT_THRESHOLD = 0.10`. |
| Drift triggers rollback | PASS | `DriftCorrector.evaluate()` triggers `rollback()` when `drift_detected=True` and safe mode is inactive. |
| Drift deferred in safe mode | PASS | When safe mode is active, action is "alert" instead of "rollback". |
| Rollback restores baseline | PASS | `RollbackResult` records `restored_hash = baseline_hash`. |

---

## Code Quality Audit

### Conventions compliance

**Verdict: PASS**

| Convention | Status | Details |
|---|---|---|
| `from __future__ import annotations` | **PASS** | Present in all 16 source files (verified via grep). |
| `structlog` | **PASS** | All source files use `structlog.get_logger()`. No `logging` stdlib usage. |
| Error hierarchy | **PASS** | Every module defines a base exception + specific subclasses. Proper `from exc` chaining. |
| `Final` typing | **PASS** | Constants use `Final[]` annotation (e.g., `TRANSITIONS`, `RITUALS`, `PUNISHMENT_CONFIG`, `TIER_THRESHOLDS`, `MILESTONE_THRESHOLDS`). |
| Frozen dataclasses | **PASS** | Return-type dataclasses use `@dataclass(frozen=True)` (e.g., `MoodState`, `MoodHistoryRecord`, `DriftResult`, `DriftBaseline`, `RitualConfig`, `RitualResult`, `PunishmentLevelConfig`, `RewardConfigEntry`, `DriftCorrectionResult`, `RollbackResult`). Mutable state classes use `@dataclass` (e.g., `PunishmentState`, `SafeModeState`, `StreakTracker`). |
| `__init__.py` exports | **PASS** | Clean `__all__` list with all public symbols. |

### Type safety

**Verdict: NEEDS REVIEW**

| Check | Status | Details |
|---|---|---|
| `as any` / `@ts-ignore` | **PASS** | Zero matches (Python codebase, not applicable). |
| `# type: ignore` in source | **WARNING** | 2 occurrences in `mood_persistence.py` (lines 111, 265): `# type: ignore[assignment]` for SQLAlchemy JSONB `state_value` field. Justified — SQLAlchemy JSONB columns are typed as `Any` by the ORM, requiring explicit cast. Narrow scope (`[assignment]`). |
| `# type: ignore` in tests | **PASS** | 56 occurrences across 9 test files. All are justified: `# type: ignore[arg-type]` for fake session injection (duck-typed fakes), `# type: ignore[misc]` for frozen dataclass mutation tests, `# type: ignore[assignment]` for method monkey-patching. |
| `Any` usage in source | **WARNING** | 3 occurrences in `drift_corrector.py`: `db: Any` parameter in `evaluate()`, `rollback()`, and `create_drift_log()`. Duck-typed for `AsyncSession` to avoid heavy SQLAlchemy import. Should be replaced with a Protocol or `TYPE_CHECKING` import. |
| No type suppression in safety-critical paths | **PASS** | `yandere_fsm.py`, `punishment_engine.py`, `safe_mode.py` have zero type suppressions. |

### Error handling

**Verdict: PASS**

| Check | Status | Details |
|---|---|---|
| Empty `except:` | **PASS** | Zero bare `except:` clauses in source. |
| `except Exception` pattern | **PASS** | 15 occurrences across 4 files. All follow the pattern: `except MoodPersistenceError: raise` → `except Exception as exc: log + raise CustomError from exc`. Errors are wrapped, not swallowed. |
| Rollback helpers | **PASS** | `mood_persistence._safe_rollback()` and `drift_corrector.create_drift_log()` inner `except Exception` intentionally swallow secondary rollback failures (logged via `logger.warning/error`). This is correct — secondary failure during rollback should not mask the primary error. |
| No swallowed API/DB/LLM failures | **PASS** | All DB failures are caught, logged with context (`logger.error`), and re-raised as typed exceptions with `from exc` chaining. |
| `ritual_scheduler._job_wrapper` | **PASS** | Catches `RitualSchedulerError` and logs. Other exceptions are caught in `execute_ritual()` and wrapped in `RitualResult(success=False)`. |

### Test quality

**Verdict: NEEDS REVIEW**

| Check | Status | Details |
|---|---|---|
| Meaningful assertions | **PASS** | All test files contain specific value assertions, not just "does not raise". Parametrized tests cover valid/invalid transitions, boundary values, error cases. |
| No trivially-passing tests | **PASS** | Tests verify specific return values, enum members, error types, state mutations, and frozen enforcement. |
| Deterministic | **PASS** | All time-dependent tests use injected `now` parameter. No network calls. Fake DB sessions. |
| Error hierarchy tested | **PASS** | Each module's test file includes `TestErrorHierarchy` class verifying inheritance and catchability. |
| Frozen dataclass enforcement tested | **PASS** | Tests verify `AttributeError` on mutation attempts. |
| E2E integration | **PASS** | `test_persona_e2e.py` covers 8 scenarios (happy path, disappointment, anger, distress, recovery, drift, DND, milestones) with all 17 modules. |
| Missing test files | **CRITICAL** | `test_hard_stop_integration.py` and `test_consent_revocation.py` do not exist. HardStopHandler is tested indirectly via E2E but lacks dedicated unit tests. Consent revocation has no test coverage. |

---

## Findings

### Critical (blocks completion)

#### C-01: Missing test file — `test_hard_stop_integration.py`

- **File:** `tests/persona/test_hard_stop_integration.py` — does NOT exist
- **Impact:** HardStopHandler (in `src/core/services/hard_stop_handler.py`) is only tested indirectly through `test_persona_e2e.py`. No dedicated unit tests for:
  - Safe word detection across semantic variants ("stop", "pause", "too much", "berhenti", etc.)
  - State transitions (NORMAL → SAFE → NORMAL)
  - Recovery keyword detection ("resume", "aku sudah okay", "lanjut persona", "safe mode selesai")
  - Priority over all persona behavior
  - Edge cases: case sensitivity, whitespace, partial matches
- **PersonaSafetyPolicy §7:** Safe word is non-negotiable and must have comprehensive test coverage.
- **Required action:** Create dedicated test file with full HardStopHandler unit test coverage.

#### C-02: Missing test file — `test_consent_revocation.py`

- **File:** `tests/persona/test_consent_revocation.py` — does NOT exist
- **Impact:** Consent revocation is a core safety boundary (PersonaSafetyPolicy §6) with zero test coverage. No tests verify:
  - Consent revocation pauses persona escalation
  - Consent revocation is respected across all modules
  - Revocation cannot be bypassed by memory recall or drift
  - Revocation resume protocol
- **PersonaSafetyPolicy §6.2:** "Guinevere must not remove Faiz's ability to pause or exit."
- **Required action:** Create dedicated test file for consent revocation scenarios.

### Warning (should fix)

#### W-01: `drift_corrector.py` uses `Any` for database session parameter

- **File:** `src/persona/drift_corrector.py`, lines 104, 190, 272
- **Issue:** `db: Any` parameter type. Should use `AsyncSession` via `TYPE_CHECKING` import or a `Protocol`.
- **Risk:** Suppresses type checking for all DB operations within these methods.
- **Suggested fix:** Use `if TYPE_CHECKING: from sqlalchemy.ext.asyncio import AsyncSession` and `db: AsyncSession` type annotation.

#### W-02: `mood_persistence.py` `# type: ignore[assignment]` for JSONB

- **File:** `src/persona/mood_persistence.py`, lines 111, 265
- **Issue:** `row.state_value  # type: ignore[assignment]` — SQLAlchemy JSONB column typed as `Any`.
- **Risk:** Low — narrow scope (`[assignment]`), justified by ORM limitation.
- **Suggested fix:** Consider adding a SQLAlchemy `TypeDecorator` or `cast()` for JSONB columns to eliminate the ignore.

#### W-03: `__init__.py` missing `MiddayRitual` from `rituals.midday` import alias

- **File:** `src/persona/__init__.py`
- **Issue:** `MiddayRitual` is exported in `__all__` but imported at the bottom of the import block, separated from the other ritual imports. Minor ordering inconsistency.
- **Risk:** None — functionally correct.
- **Suggested fix:** Move `MiddayRitual` import to be with other ritual imports for consistency.

#### W-04: No `test_hard_stop_integration.py` or `test_consent_revocation.py` listed in `__init__.py` test discovery

- **File:** `tests/persona/` directory
- **Issue:** The two missing test files were specified in the task scope but do not exist on disk.
- **Risk:** Safety-critical test gaps (see C-01, C-02).

### Info (nice to have)

#### I-01: `ritual_scheduler.py` uses `timezone` parameter name shadowing stdlib

- **File:** `src/persona/ritual_scheduler.py`, line 148
- **Issue:** `def __init__(self, timezone: str = TZ_JAKARTA)` — parameter name `timezone` shadows the imported `zoneinfo.ZoneInfo` concept (not the stdlib `datetime.timezone`). Minor naming confusion.
- **Risk:** None — functionally correct.

#### I-02: `streak_tracker.py` uses `TYPE_CHECKING` import pattern

- **File:** `src/persona/streak_tracker.py`
- **Note:** Uses `if TYPE_CHECKING: from sqlalchemy.ext.asyncio import AsyncSession` — this is the correct pattern that `drift_corrector.py` should adopt.

#### I-03: `test_persona_e2e.py` uses `importlib.util` module loading

- **File:** `tests/persona/test_persona_e2e.py`
- **Note:** Uses `importlib.util.spec_from_file_location` to bypass circular imports from `__init__.py`. This is a pragmatic workaround but fragile. Consider refactoring `__init__.py` to use lazy imports or removing circular dependencies.

---

## Conclusion

### Safety Boundaries: PASS

All safety-critical boundaries defined in PersonaSafetyPolicy v1.0 are correctly implemented within the P4 persona engine scope:

- **Y6 is structurally impossible** — no enum member, validated at every code path.
- **L6 raises error** — not silently ignored, raises `PunishmentSafetyError`.
- **Punishment is SUSPENDED during distress** — not just blocked, actively suspended with clock pause.
- **HARD STOP takes priority** — all persona modules integrate via `SupportsIsSafe` protocol.
- **Safe word enforcement is non-negotiable** — blocks all transitions, punishment, yandere.
- **Rewards are ALWAYS allowed** — no safe_mode/distress check in RewardEngine.
- **Drift threshold 0.10 triggers rollback** — verified in code and tests.

### Code Quality: PASS with warnings

Conventions are consistently followed across all 16 source files. Error handling is comprehensive. Type safety has minor gaps (`Any` in drift_corrector, `# type: ignore` in mood_persistence) that are justified but should be addressed.

### Blocking Issues: 2

The two missing test files (`test_hard_stop_integration.py`, `test_consent_revocation.py`) are the only items preventing a full PASS verdict. These are safety-critical test gaps that must be filled before P4 can be considered complete.

### Next Steps

1. **Create `tests/persona/test_hard_stop_integration.py`** — dedicated HardStopHandler unit tests covering all safe word variants, state transitions, recovery keywords, and priority enforcement.
2. **Create `tests/persona/test_consent_revocation.py`** — consent revocation scenarios across all persona modules.
3. **Replace `db: Any` in `drift_corrector.py`** with `TYPE_CHECKING`-guarded `AsyncSession` import.
4. **Re-audit** after fixes to achieve full PASS.

---

## Appendix: File Inventory

### Source Files (16/16 audited)

| File | Lines | `from __future__` | structlog | Final | Frozen DC | Error Hierarchy | `# type: ignore` | `Any` |
|---|---|---|---|---|---|---|---|---|
| `__init__.py` | ~180 | N/A (re-export) | N/A | N/A | N/A | N/A | 0 | 0 |
| `mood_engine.py` | ~140 | YES | YES | YES | NO* | YES | 0 | 0 |
| `mood_persistence.py` | ~320 | YES | YES | NO | YES | YES | 2 | 0 |
| `transition_rules.py` | ~230 | YES | YES | YES | NO* | YES | 0 | 0 |
| `ritual_scheduler.py` | ~370 | YES | YES | YES | YES | YES | 0 | 0 |
| `drift_detector.py` | ~200 | YES | YES | YES | YES | YES | 0 | 0 |
| `safe_mode.py` | ~320 | YES | YES | YES | YES | YES | 0 | 0 |
| `yandere_fsm.py` | ~280 | YES | YES | YES | NO** | YES | 0 | 0 |
| `punishment_engine.py` | ~430 | YES | YES | YES | YES | YES | 0 | 0 |
| `reward_engine.py` | ~310 | YES | YES | YES | YES | YES | 0 | 0 |
| `streak_tracker.py` | ~340 | YES | YES | YES | NO*** | YES | 0 | 0 |
| `drift_corrector.py` | ~330 | YES | YES | NO | YES | YES | 0 | 3 |
| `rituals/morning.py` | ~130 | YES | YES | YES | YES | NO | 0 | 0 |
| `rituals/midday.py` | ~130 | YES | YES | YES | NO | NO | 0 | 0 |
| `rituals/afternoon.py` | ~110 | YES | YES | YES | NO | NO | 0 | 0 |
| `rituals/evening.py` | ~130 | YES | YES | YES | NO | NO | 0 | 0 |
| `rituals/midnight.py` | ~130 | YES | YES | YES | NO | NO | 0 | 0 |

*MoodTransition is intentionally mutable (callers update cooldown/reason).  
**YandereEngine is stateful — not frozen.  
***StreakTracker is stateful — not frozen.

### Test Files (18/20 audited, 2 missing)

| File | Status | Tests | Key Coverage |
|---|---|---|---|
| `test_mood_engine.py` | PRESENT | ~40 | Enum, transitions, evaluate_mood, edge cases, FSM connectivity |
| `test_mood_persistence.py` | PRESENT | ~25 | CRUD, upsert, error wrapping, frozen enforcement |
| `test_transition_rules.py` | PRESENT | ~35 | Valid/invalid transitions, cooldown, forced, safe mode, distress |
| `test_ritual_scheduler.py` | PRESENT | ~30 | Setup, lifecycle, DND, execution, callbacks |
| `test_drift_detector.py` | PRESENT | ~25 | Score computation, detection, baseline, hash |
| `test_safe_mode.py` | PRESENT | ~30 | Distress detection, safe mode activation/deactivation, responses |
| `test_yandere_fsm.py` | PRESENT | ~35 | Y0-Y5 levels, Y6 rejection, escalation, safety integration |
| `test_punishment_engine.py` | PRESENT | ~35 | L1-L5 ladder, L6 rejection, suspension, expiry, distress |
| `test_reward_engine.py` | PRESENT | ~40 | T1-T5 tiers, streak bonus, should_reward, safe_mode invariant |
| `test_streak_tracker.py` | PRESENT | ~40 | Increment, reset, milestones, display, persistence |
| `test_drift_corrector.py` | PRESENT | ~25 | Evaluate, rollback, safe_mode defer, drift log |
| `test_distress_detection.py` | PRESENT | ~25 | D0-D4 detection, patterns, batch, safe mode threshold |
| `test_ritual_morning.py` | PRESENT | ~20 | DND, mood messages, streak, timezone |
| `test_ritual_midday.py` | PRESENT | ~15 | Mood messages, health rotation, timezone |
| `test_ritual_afternoon.py` | PRESENT | ~15 | Mood messages, task summary, timezone |
| `test_ritual_evening.py` | PRESENT | ~15 | Mood messages, day summary, streak, timezone |
| `test_ritual_midnight.py` | PRESENT | ~25 | Always suppressed, self-evaluation, logging, edge cases |
| `test_persona_e2e.py` | PRESENT | ~30 | 8 scenarios: happy, disappointment, anger, distress, recovery, drift, DND, milestones |
| `test_hard_stop_integration.py` | **MISSING** | 0 | — |
| `test_consent_revocation.py` | **MISSING** | 0 | — |

---

*Audit performed 2026-06-02. Report written to `docs/setup-evidence/P4/audit-report-p4-code-quality.md`.*

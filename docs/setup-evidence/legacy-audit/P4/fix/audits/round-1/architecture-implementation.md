# P4 Architecture & Implementation Audit — Round 1

> **Auditor**: Independent subagent (read-only)
> **Date**: 2026-06-27
> **Scope**: P4-001 through P4-023 — verify each module exists, compiles, implements what it claims, and is correctly wired
> **Method**: Fresh source inspection, grep-based wiring analysis, verification doc cross-reference

---

## 1. Per-P4-Step Verification Table

### Legend

- **EXISTS**: Source file present on disk with real (non-stub) code
- **TEST**: Test file present with actual test functions
- **WIRED**: Imported/called by runtime code outside `src/persona/` and `tests/`
- **Status**: LIVE | DEAD CODE | DEPRECATED | HALF-IMPLEMENTED | TEST-ONLY

| Step | Module | Source File | Lines | Exists? | Test File | Test Count | Wired Live? | Verification Doc Accurate? | Status |
|------|--------|------------|-------|---------|-----------|------------|-------------|---------------------------|--------|
| P4-001 | Mood FSM Engine | `src/persona/mood_engine.py` | 237 | YES | `tests/persona/test_mood_engine.py` | 49 | YES (safety_plugin.py:497, hermes_conversational.py:497, wearable/mood_integration.py:33, rituals/*.py) | DISCREPANCY: doc claims 72 tests, actual 49 | **LIVE** |
| P4-002 | Mood State Persistence | `src/persona/mood_persistence.py` | 329 | YES | `tests/persona/test_mood_persistence.py` | 26 | NO (only __init__.py re-export) | DISCREPANCY: doc says "MoodStateStore class", actual class is `MoodRepository` | **DEAD CODE** |
| P4-003 | Transition Rules | `src/persona/transition_rules.py` | 375 | YES | `tests/persona/test_transition_rules.py` | 42 | NO (only __init__.py re-export + tests) | OK (structure matches) | **DEAD CODE** |
| P4-004 | Yandere FSM | `src/persona/yandere_fsm.py` | 336 | YES | `tests/persona/test_yandere_fsm.py` | 71 | YES (safety_plugin.py:524, punishment_engine.py:35) | OK | **LIVE** |
| P4-005 | Punishment Ladder | `src/persona/punishment_engine.py` | 666 | YES | `tests/persona/test_punishment_engine.py` | 96 | NO direct runtime caller (only tests + safety tests) | OK | **DEAD CODE** |
| P4-006 | Reward Tiers | `src/persona/reward_engine.py` | 445 | YES | `tests/persona/test_reward_engine.py` | 74 | NO | OK | **DEAD CODE** |
| P4-007 | Streak Tracking | `src/persona/streak_tracker.py` | 332 | YES | `tests/persona/test_streak_tracker.py` | 64 | NO | OK | **DEAD CODE** |
| P4-008 | Ritual Scheduler | `src/persona/ritual_scheduler.py` | 451 | YES | `tests/persona/test_ritual_scheduler.py` | 28 | NO (deprecated Phase 5, `__init__.py` import suppressed) | DOC MISLEADING: does not mention deprecation | **DEPRECATED** |
| P4-009 | Morning Ritual | `src/persona/rituals/morning.py` | 183 | YES | `tests/persona/test_ritual_morning.py` | 29 | NO (deprecated Phase 5) | DOC MISLEADING: does not mention deprecation | **DEPRECATED** |
| P4-010 | Midday Ritual | `src/persona/rituals/midday.py` | 185 | YES | `tests/persona/test_ritual_midday.py` | 29 | NO (deprecated Phase 5) | DOC MISLEADING | **DEPRECATED** |
| P4-011 | Afternoon Ritual | `src/persona/rituals/afternoon.py` | 139 | YES | `tests/persona/test_ritual_afternoon.py` | 26 | NO (deprecated Phase 5) | DOC MISLEADING | **DEPRECATED** |
| P4-012 | Evening Ritual | `src/persona/rituals/evening.py` | 155 | YES | `tests/persona/test_ritual_evening.py` | 35 | NO (deprecated Phase 5) | DOC MISLEADING | **DEPRECATED** |
| P4-013 | Midnight Ritual | `src/persona/rituals/midnight.py` | 176 | YES | `tests/persona/test_ritual_midnight.py` | 34 | NO (deprecated Phase 5) | DOC MISLEADING | **DEPRECATED** |
| P4-014 | Drift Detection | `src/persona/drift_detector.py` | 227 | YES | `tests/persona/test_drift_detector.py` | 34 | YES (safety_plugin.py:484, 823, 846) | OK | **LIVE** |
| P4-015 | Drift Correction | `src/persona/drift_corrector.py` | 332 | YES | `tests/persona/test_drift_corrector.py` | 43 | NO | **FRAUDULENT**: doc claims "auto-rollback to last-known-good persona state" but `rollback()` (line 188-268) only logs a DriftLog entry — no prompt reload, no state restoration | **HALF-IMPLEMENTED** |
| P4-016 | Safe-mode D0-D4 | `src/persona/safe_mode.py` | 432 | YES | `tests/persona/test_safe_mode.py` | 69 | YES (safety_plugin.py:452, hermes_conversational.py:462, punishment_engine.py:34, drift_corrector.py:12) | OK | **LIVE** |
| P4-017 | HARD STOP Test | N/A (test-only) | — | — | `tests/safety/test_hard_stop_comprehensive.py` | 86 | TEST-ONLY | DISCREPANCY: doc claims `tests/persona/test_hard_stop_integration.py` with 82 tests; actual file is `tests/safety/test_hard_stop_comprehensive.py` with 86 tests | **TEST-ONLY** |
| P4-018 | D0-D4 Detection Test | N/A (test-only) | — | — | `tests/persona/test_distress_detection.py` | 44 | TEST-ONLY | OK (test count matches) | **TEST-ONLY** |
| P4-019 | Persona E2E Test | N/A (test-only) | — | — | `tests/persona/test_persona_e2e.py` | 58 | TEST-ONLY | OK (58 tests match) | **TEST-ONLY** |
| P4-020 | Yandere Cap Test | N/A (test-only) | — | — | `tests/safety/test_yandere_cap.py` | 53 | TEST-ONLY | DISCREPANCY: doc claims "100 prompts, zero Y6" benchmark; actual file has 53 test functions | **TEST-ONLY** |
| P4-021 | Consent Revocation Test | N/A (test-only) | — | — | `tests/safety/test_consent_revocation.py` | 44 | TEST-ONLY | OK | **TEST-ONLY** |
| P4-022 | Punishment Overflow Test | N/A (test-only) | — | — | `tests/safety/test_punishment_overflow.py` | 43 | TEST-ONLY | OK | **TEST-ONLY** |
| P4-023 | Distress Protocol E2E | N/A (test-only) | — | — | **MISSING** | 0 | — | **VERIFICATION DOC IS FRAUDULENT**: claims 65-line test file exists; no `test_distress_e2e.py` found anywhere in the repository | **MISSING** |

---

## 2. Wiring Summary

### Live in Runtime (4 modules)

Only 4 of 13 source modules are imported by production runtime code:

1. **mood_engine.py** — `safety_plugin.py:497`, `hermes_conversational.py:497`, `wearable/mood_integration.py:33`, `rituals/*.py`
2. **yandere_fsm.py** — `safety_plugin.py:524`, `punishment_engine.py:35`
3. **safe_mode.py** — `safety_plugin.py:452`, `hermes_conversational.py:462`, `punishment_engine.py:34`, `drift_corrector.py:12`
4. **drift_detector.py** — `safety_plugin.py:484`, `safety_plugin.py:823`, `safety_plugin.py:846`

### Dead Code (5 modules)

These are imported only via `src/persona/__init__.py` (re-export) and test files:

1. **mood_persistence.py** — no runtime caller
2. **transition_rules.py** — no runtime caller
3. **punishment_engine.py** — no runtime caller (only imports safe_mode and yandere_fsm)
4. **reward_engine.py** — no runtime caller
5. **streak_tracker.py** — no runtime caller

### Deprecated (6 modules)

Scheduled removal Phase 7 — removal never happened:

1. **ritual_scheduler.py** — deprecated Phase 5
2. **rituals/morning.py** — deprecated Phase 5
3. **rituals/midday.py** — deprecated Phase 5
4. **rituals/afternoon.py** — deprecated Phase 5
5. **rituals/evening.py** — deprecated Phase 5
6. **rituals/midnight.py** — deprecated Phase 5

### Half-Implemented (1 module)

1. **drift_corrector.py** — rollback is record-keeping only (see BUG-03)

### Missing (1 test)

1. **P4-023 test_distress_e2e.py** — does not exist

---

## 3. BUGS

### BUG-01: Duplicate SafeModeController Instances [HIGH]

**Location**: `src/hermes/safety_plugin.py:455` + `src/discord/hermes_conversational.py:464-465`

**Problem**: Two independent `SafeModeController` instances exist in the runtime:

- `safety_plugin.py:455` creates `self._safe_mode_controller = SafeModeController()` once at plugin init, persists for the process lifetime, and is wired into the HardStopHandler bridge (`_on_hard_stop` callback at line 461-468).
- `hermes_conversational.py:464-465` creates `detector = DistressDetector()` and `controller = SafeModeController()` as **throwaway locals** on every single message.

**Impact**: Safe mode activated via `hermes_conversational.py` is ephemeral — it dies when the function returns. Safe mode activated via `safety_plugin.py` persists but is never visible to the conversational handler's controller. The two instances do not share state. Distress detection in the conversational handler is effectively a no-op for downstream systems.

**Evidence**:
```python
# safety_plugin.py:454-455 (init-time, persistent)
self._distress_detector = DistressDetector()
self._safe_mode_controller = SafeModeController()

# hermes_conversational.py:462-465 (per-message, throwaway)
from src.persona.safe_mode import DistressDetector, SafeModeController
detector = DistressDetector()
controller = SafeModeController()
```

---

### BUG-02: Stale Wearable Import — `is_safe_mode_active` Does Not Exist [LOW]

**Location**: `src/wearable/alert_router.py:25`

**Problem**: Imports `is_safe_mode_active` from `src.persona.yandere_fsm`, but this symbol does not exist in `yandere_fsm.py`. Confirmed by grep: zero matches for `is_safe_mode_active` in the entire `src/persona/` directory.

**Mitigation**: Wrapped in `try/except ImportError` (line 24-27), so it fails silently and sets `is_safe_mode_active = None`. No runtime crash, but the wearable alert router has no safe-mode awareness.

**Evidence**:
```python
# alert_router.py:24-27
try:
    from src.persona.yandere_fsm import is_safe_mode_active
except ImportError:
    is_safe_mode_active = None  # type: ignore[assignment]
```

---

### BUG-03: Drift Corrector "Rollback" Is Record-Keeping Only [HIGH]

**Location**: `src/persona/drift_corrector.py:188-268`

**Problem**: The `rollback()` method's verification doc (P4-015) claims: "auto-rollback to last-known-good persona state", "restores persona to last-known-good state", "State snapshots use mood persistence infrastructure (P4-002)". The actual implementation does **none of this**.

The method:
1. Checks if safe_mode is active (if so, returns `success=False`)
2. Reads `baseline_hash` and `previous_hash` from the detector
3. Creates a `DriftResult` with `action="rollback"`
4. Persists a DriftLog entry via `create_drift_log()`
5. Returns `RollbackResult(success=True, ...)`

It does NOT:
- Reload or restore any prompt
- Reset any persona engine state
- Call prompt_loader
- Restore mood, yandere, or punishment state
- Invoke any state restoration mechanism

The "rollback" is purely a database audit record that says "rollback happened" without performing any actual rollback.

**Evidence** (drift_corrector.py:227-268):
```python
rollback_ts = datetime.now(timezone.utc)
# Persist rollback drift log
try:
    rollback_drift_result = DriftResult(
        drift_detected=True,
        drift_score=...,
        threshold=...,
        action="rollback",
        baseline_hash=baseline_hash,
        current_hash=previous_hash,
        checked_at=rollback_ts,
    )
    await self.create_drift_log(db, drift_result=rollback_drift_result, action_taken=f"rollback:{reason}")
# ... error handling ...
return RollbackResult(success=True, previous_hash=previous_hash, restored_hash=baseline_hash, timestamp=rollback_ts)
```

---

### BUG-04: P4-023 Distress Protocol E2E Test Does Not Exist [HIGH]

**Location**: Expected at `tests/persona/test_distress_e2e.py` or `tests/safety/test_distress_e2e.py`

**Problem**: P4-023 verification doc claims a test file was created. No `test_distress_e2e.py` exists anywhere in the repository (confirmed by glob search). The verification doc is a fabrication.

---

### BUG-05: Verification Doc Test Count Discrepancies [MEDIUM]

Multiple verification docs claim test counts that do not match the actual `def test_` count in the corresponding files:

| Step | Doc Claim | Actual | File |
|------|-----------|--------|------|
| P4-001 | 72 tests | 49 | `tests/persona/test_mood_engine.py` |
| P4-005 | 89 tests | 96 | `tests/persona/test_punishment_engine.py` |
| P4-015 | 47 tests | 43 | `tests/persona/test_drift_corrector.py` |
| P4-017 | 82 tests | 86 | `tests/safety/test_hard_stop_comprehensive.py` |
| P4-020 | "100 prompts, zero Y6" | 53 test functions | `tests/safety/test_yandere_cap.py` |

---

### BUG-06: Verification Doc File Path Discrepancies [MEDIUM]

| Step | Doc Claims | Actual Location |
|------|-----------|-----------------|
| P4-017 | `tests/persona/test_hard_stop_integration.py` | `tests/safety/test_hard_stop_comprehensive.py` |
| P4-020 | `tests/persona/test_yandere_cap.py` | `tests/safety/test_yandere_cap.py` |
| P4-021 | `tests/persona/test_consent_revocation.py` | `tests/safety/test_consent_revocation.py` |
| P4-022 | `tests/persona/test_punishment_overflow.py` | `tests/safety/test_punishment_overflow.py` |

All Wave 3 safety tests (P4-017, P4-020, P4-021, P4-022) were moved from `tests/persona/` to `tests/safety/` but the verification docs were never updated.

---

### BUG-07: P4-002 Verification Doc Class Name Mismatch [LOW]

**Location**: `docs/setup-evidence/P4/STEP-P4-002/verification.md:7` vs `src/persona/mood_persistence.py:83`

**Problem**: Verification doc says "MoodStateStore class" but actual class is `MoodRepository`.

---

## 4. ARCHITECTURE RISKS

### RISK-01: `warnings.catch_warnings()` Silences Deprecation [HIGH]

**Location**: `src/persona/__init__.py:128-149`

**Problem**: The `with warnings.catch_warnings(): warnings.simplefilter("ignore", DeprecationWarning)` block around the deprecated ritual imports (lines 128-149) **silently suppresses** the deprecation warnings that `ritual_scheduler.py:32-38` emits. This means:

1. Any consumer doing `from src.persona import RitualScheduler` gets **no deprecation warning**.
2. The deprecated code is fully importable and usable without any signal to developers.
3. The "scheduled removal: Phase 7" never happened — the suppression makes it invisible.
4. The deprecated modules and their dependencies (asyncpg, APScheduler, redis) are still loaded into memory at import time.

**Evidence** (ritual_scheduler.py:32-38):
```python
warnings.warn(
    "ritual_scheduler.py is deprecated in Phase 5. "
    "Use Hermes cron (~/.hermes/crontab.yaml) and PersonaPlugin instead. "
    "Scheduled removal: Phase 7.",
    DeprecationWarning,
    stacklevel=2,
)
```

This warning is emitted at module load time, but `__init__.py:129` catches and ignores it.

---

### RISK-02: milestone_engine.py — Hardcoded Connection Params + Daemon Threads + No DI [HIGH]

**Location**: `src/persona/milestone_engine.py` (872 lines)

**Problems**:

1. **Hardcoded PostgreSQL fallback** (lines 531-537): Falls back to `localhost:5433`, user `guinevere_core`, database `guinevere` when `DATABASE_URL` is not set. No DI, no config injection.

2. **Hardcoded Redis fallback** (lines 550-555): Falls back to `localhost:6380`, db=5, user `guinevere_core`. Same pattern at line 833-837.

3. **Daemon thread for DB writes** (line 506): `threading.Thread(target=_worker, daemon=True, name="milestone-recorder")` — fire-and-forget writes with no error propagation to the caller. A crash in the daemon thread is silently lost.

4. **`asyncio.run()` inside thread** (lines 474, 610, 752, 802, 866): Multiple functions call `asyncio.run()` synchronously, creating a new event loop per invocation. This is incompatible with any parent async context.

5. **Not wired**: `milestone_engine.py` is NOT imported by `__init__.py` (confirmed by grep). It is NOT imported by any runtime caller. It exists only as a standalone 872-line module that was never integrated. `persona_plugin.py` reads directly from Redis DB5 instead.

**Evidence** (milestone_engine.py:531-537):
```python
return {
    "host": "localhost",
    "port": 5433,
    "user": "guinevere_core",
    "password": __import__("os").environ.get("POSTGRES_PASSWORD", ""),
    "database": "guinevere",
}
```

---

### RISK-03: PersonaPlugin Registration Story Is Misunderstood [MEDIUM]

**Contradicts research context claim**: "PersonaPlugin (src/hermes/plugins/persona_plugin.py) is NOT registered."

**Reality**: PersonaPlugin IS registered via `hermes-config/plugins/guinevere_persona/__init__.py:63-95`, which is discovered by Hermes's plugin loader. The bridge uses `importlib.util.spec_from_file_location()` to load the plugin without triggering the problematic `src/hermes/__init__.py` import chain. VPS journal evidence (from research-reports) shows 3,086 `persona_plugin_inject` events on 2026-06-25.

However, the PersonaPlugin reads persona state from **Redis DB5**, not from the persona engine modules (mood_engine, yandere_fsm, etc.) directly. The engines write to Redis, and the plugin reads from Redis. This means the dead-code modules (mood_persistence, punishment_engine, reward_engine, streak_tracker) contribute nothing to the live persona injection path.

---

### RISK-04: 10 Dead-Code Modules Increase Attack Surface [MEDIUM]

10 of 14 persona source modules are never called by production runtime code. They:

1. Are still importable (all exported via `__init__.py`)
2. Load their dependency chains at import time (SQLAlchemy models, redis, asyncpg)
3. Increase the codebase surface area that must be audited for security
4. Create confusion about what is actually running in production
5. Accumulate stale code that drifts from the live runtime's behavior

The 6 deprecated ritual modules were supposed to be removed in Phase 7. That removal never happened.

---

### RISK-05: Verification Docs Are Systematically Inaccurate [HIGH]

Across the 23 verification docs:

- **6 docs** have test count discrepancies (BUG-05)
- **4 docs** reference wrong file paths (BUG-06)
- **1 doc** references a nonexistent class name (BUG-07)
- **1 doc** is entirely fabricated (P4-023, BUG-04)
- **1 doc** claims functionality that does not exist in code (P4-015, BUG-03)
- **6 docs** (P4-008 through P4-013) describe deprecated modules as if they were active, with no mention of deprecation
- All docs were written on 2026-06-02 and never updated to reflect the Phase 5 deprecation, P4 cleanup wave (2026-06-09), or test file reorganization

---

## 5. Milestone Engine — Not a P4 Step But Architecturally Relevant

`src/persona/milestone_engine.py` (872 lines) is NOT part of P4-001 through P4-023. It was not in the batch plan. However, it exists in `src/persona/` and warrants note:

- **Not in `__init__.py`**: Confirmed by grep — zero imports of `milestone_engine` in `__init__.py`
- **Has its own test file**: `tests/persona/test_milestone_engine.py` (68 tests)
- **Not wired to any runtime**: No caller outside tests
- **Architectural risk**: Hardcoded connection params, daemon threads, `asyncio.run()` in sync context (see RISK-02)

---

## 6. Binding Verdict

### Overall Assessment: **FAIL — 4 LIVE, 10 DEAD, 6 DEPRECATED, 1 MISSING, 1 HALF-IMPLEMENTED**

Of 23 P4 steps:
- **4 modules are genuinely live** in production: mood_engine, yandere_fsm, safe_mode, drift_detector
- **5 modules are dead code** with no runtime caller: mood_persistence, transition_rules, punishment_engine, reward_engine, streak_tracker
- **6 modules are deprecated** (Phase 5) with removal overdue (Phase 7): ritual_scheduler + 5 ritual modules
- **1 module is half-implemented**: drift_corrector (rollback is record-keeping only)
- **7 test-only steps** (P4-017 through P4-023) exist as tests only; of these, P4-023's test file is **missing entirely**
- **1 unnumbered module** (milestone_engine, 872 lines) exists but is neither in the P4 plan nor wired

### Verification Doc Integrity: **FAIL**

6 of 23 verification docs contain material discrepancies (wrong test counts, wrong file paths, wrong class names). 1 doc (P4-023) describes a test file that does not exist. 1 doc (P4-015) claims functionality ("auto-rollback to last-known-good state") that is not implemented in the source code. 6 docs (P4-008 through P4-013) describe deprecated modules without mentioning deprecation.

### Production Safety: **CONDITIONAL PASS**

The 4 live modules (mood_engine, yandere_fsm, safe_mode, drift_detector) are well-implemented with real code, proper error hierarchies, and safety interlocks. The critical safety mechanisms (HARD STOP, Y6 prohibition, D3+ punishment suspension) are implemented in the live code paths. However:

- The duplicate SafeModeController (BUG-01) means distress detection in `hermes_conversational.py` is stateless and ephemeral
- The drift corrector "rollback" (BUG-03) provides a false sense of automated recovery
- 10 dead-code modules increase audit burden without contributing to production behavior

### Required Actions

1. **BUG-01**: Unify SafeModeController to a single shared instance across safety_plugin and hermes_conversational
2. **BUG-03**: Either implement real prompt/state rollback in drift_corrector, or change the verification doc to accurately describe record-keeping-only behavior
3. **BUG-04**: Create the missing P4-023 test file, or mark P4-023 as NOT IMPLEMENTED
4. **RISK-01**: Remove the `warnings.catch_warnings()` suppression; either emit deprecation warnings properly or remove the deprecated modules
5. **RISK-04**: Execute the Phase 7 removal of deprecated ritual modules (P4-008 through P4-013)
6. **RISK-05**: Update all 23 verification docs to reflect actual test counts, file paths, and module status

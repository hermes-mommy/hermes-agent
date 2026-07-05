# P4 Architecture Implementation Audit — Round 1

**Date:** 2026-06-25
**Auditor:** Claude (read-only)
**Scope:** P4-001 through P4-023 source verification, wiring checks, architectural defects
**Inputs:** p4-persona-source-map.md, p4-runtime-readiness-readonly.md, p4-repo-evidence-inventory.md + direct source inspection

---

## 1. Per-Step Verification Table

Legend:
- **exists?** — source file present on disk with real code (not stub)
- **wired?** — module imported/called by runtime code outside `src/persona/tests`
- **status** — WIRED (active in runtime), DEAD CODE (exists but no runtime caller), DEPRECATED (marked for removal), HALF-IMPLEMENTED (claim exceeds reality), TEST-ONLY (P4-017..023 — no new source, exercises existing engines)
- **bugs** — defects found during this audit

| P4-step | Source file | exists? | wired? | status | bugs |
|---------|-------------|---------|--------|--------|------|
| P4-001 | `src/persona/mood_engine.py` (237 lines) | YES | YES — `hermes_conversational.py:489` | WIRED | Checklist says linear chain "Content->Pleased->Disappointed->Angry->Silent" but FSM allows Content->Disappointed directly and Silent->Content directly. LOW — label is simplified. |
| P4-002 | `src/persona/mood_persistence.py` (329 lines) | YES | NO — no runtime caller injects AsyncSession | DEAD CODE | Checklist says `persona.mood_states` table but actual table is `persona.persona_state` with `state_key="current_mood"`. MEDIUM — wrong table name in docs. |
| P4-003 | `src/persona/transition_rules.py` (375 lines) | YES | NO — only imported by `__init__.py` and tests | DEAD CODE | No consent parameter in `TransitionContext`. Consent revocation cannot block transitions. MEDIUM. |
| P4-004 | `src/persona/yandere_fsm.py` (336 lines) | YES | YES — `safety_plugin.py:524,767` | WIRED | Y6 truly impossible (5 independent guards verified). No consent-aware path. Consent revocation does NOT halt yandere escalation in source. HIGH. |
| P4-005 | `src/persona/punishment_engine.py` (666 lines) | YES | NO — only imported by `__init__.py` and tests | DEAD CODE | L6 guard, safe-mode guard, HARD STOP guard all present. But module has zero runtime callers — punishment engine is never instantiated by safety_plugin or conversational handler. MEDIUM. |
| P4-006 | `src/persona/reward_engine.py` (445 lines) | YES | NO — only imported by `__init__.py` and tests | DEAD CODE | Always-allowed design (no suppression) is correct per spec. Zero runtime callers. MEDIUM. |
| P4-007 | `src/persona/streak_tracker.py` (332 lines) | YES | NO — only imported by `__init__.py` and tests | DEAD CODE | Persistence uses `PersonaState` table with `state_key="streak_count"`. Zero runtime callers. MEDIUM. |
| P4-008 | `src/persona/ritual_scheduler.py` (451 lines) | YES | NO — deprecated, replaced by Hermes cron | DEPRECATED | Module-level `DeprecationWarning` + `warnings.catch_warnings` suppression in `__init__.py`. Fully functional but not instantiated by any live code. Checklist does NOT mention deprecation. MEDIUM. |
| P4-009 | `src/persona/rituals/morning.py` (184 lines) | YES | NO — deprecated | DEPRECATED | No runtime consumer. MEDIUM. |
| P4-010 | `src/persona/rituals/midday.py` (186 lines) | YES | NO — deprecated | DEPRECATED | No runtime consumer. MEDIUM. |
| P4-011 | `src/persona/rituals/afternoon.py` (140 lines) | YES | NO — deprecated | DEPRECATED | No runtime consumer. MEDIUM. |
| P4-012 | `src/persona/rituals/evening.py` (156 lines) | YES | NO — deprecated | DEPRECATED | No runtime consumer. MEDIUM. |
| P4-013 | `src/persona/rituals/midnight.py` (177 lines) | YES | NO — deprecated | DEPRECATED | No runtime consumer. MEDIUM. |
| P4-014 | `src/persona/drift_detector.py` (227 lines) | YES | YES — `safety_plugin.py:484,823,846` | WIRED | `SOUL_BASELINE_HASH` is hardcoded constant with no verification against actual SystemPromptMaster. May be stale. MEDIUM. |
| P4-015 | `src/persona/drift_corrector.py` (332 lines) | YES | NO — only imported by `__init__.py` and tests | DEAD CODE | "Rollback" is record-keeping only (writes baseline hash to DriftLog). Does NOT reload or replace actual system prompt. Checklist says "alert + rollback" overstates what the code does. HIGH. |
| P4-016 | `src/persona/safe_mode.py` (432 lines) | YES | YES — `safety_plugin.py:452` + `hermes_conversational.py:454,477` | WIRED | Two separate SafeModeController instances created (see Section 4). No consent integration. MEDIUM. |
| P4-017 | test-only (`tests/safety/test_hard_stop_comprehensive.py`) | YES* | TEST-ONLY | HALF-IMPLEMENTED | Verification.md claims file at `tests/persona/test_hard_stop_integration.py` — does NOT exist there. Actual file is `tests/safety/test_hard_stop_comprehensive.py`. Wrong path in evidence. MEDIUM. |
| P4-018 | test-only (`tests/safety/test_distress_detection.py`) | YES | TEST-ONLY | WIRED (test) | Actually at `tests/persona/test_distress_detection.py` (exists). Verification.md path is correct for this one. |
| P4-019 | test-only (`tests/persona/test_persona_e2e.py`) | YES | TEST-ONLY | WIRED (test) | Path correct. 1139 lines. |
| P4-020 | test-only (`tests/safety/test_yandere_cap.py`) | YES* | TEST-ONLY | HALF-IMPLEMENTED | Verification.md claims `tests/persona/test_yandere_cap.py` — does NOT exist there. Actual file is `tests/safety/test_yandere_cap.py`. Wrong path. MEDIUM. |
| P4-021 | test-only (`tests/safety/test_consent_revocation.py`) | YES* | TEST-ONLY | HALF-IMPLEMENTED | Verification.md claims `tests/persona/test_consent_revocation.py` — does NOT exist there. Actual file is `tests/safety/test_consent_revocation.py`. Wrong path. CRITICAL — consent gate in safety_plugin is DEFERRED ("gate_10_consent_deferred" at safety_plugin.py:900). Test exercises a feature not wired to runtime. |
| P4-022 | test-only (`tests/safety/test_punishment_overflow.py`) | YES* | TEST-ONLY | HALF-IMPLEMENTED | Verification.md claims `tests/persona/test_punishment_overflow.py` — does NOT exist there. Actual file is `tests/safety/test_punishment_overflow.py`. Wrong path. MEDIUM. |
| P4-023 | test-only (`tests/safety/test_distress_protocol_e2e.py`) | YES* | TEST-ONLY | HALF-IMPLEMENTED | Verification.md claims `tests/persona/test_distress_e2e.py` — does NOT exist there. Actual file is `tests/safety/test_distress_protocol_e2e.py`. Wrong path. MEDIUM. |

**Summary counts:**
- WIRED (active in runtime): 4 modules (P4-001 mood_engine, P4-004 yandere_fsm, P4-014 drift_detector, P4-016 safe_mode)
- DEAD CODE (no runtime caller): 6 modules (P4-002, P4-003, P4-005, P4-006, P4-007, P4-015)
- DEPRECATED (marked for removal, not done): 6 modules (P4-008 through P4-013)
- HALF-IMPLEMENTED (claims exceed reality): 5 test steps (P4-017, P4-020, P4-021, P4-022, P4-023 — wrong test file paths in verification.md)
- TEST-ONLY (correct): 2 test steps (P4-018, P4-019)

---

## 2. `__init__.py` Deprecation Suppression

**Location:** `src/persona/__init__.py` lines 128-149

```python
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from src.persona.ritual_scheduler import (...)
    from src.persona.rituals.morning import (...)
    from src.persona.rituals.evening import EveningRitual
    from src.persona.rituals.afternoon import AfternoonRitual
    from src.persona.rituals.midnight import MidnightRitual
    from src.persona.rituals.midday import MiddayRitual
```

**Finding:** The `warnings.catch_warnings()` block suppresses `DeprecationWarning` during import. This means consumers of `src.persona` can access deprecated symbols (`RitualScheduler`, `MorningRitual`, etc.) silently — no warning is emitted. The deprecated symbols are imported at module scope but are **NOT** included in `__all__` (lines 151-244). They are available via `from src.persona import RitualScheduler` but not via `from src.persona import *`.

**Verdict:** The suppression is intentional but creates a false sense of safety — downstream code can use deprecated symbols without any deprecation signal reaching the developer or logs.

---

## 3. `milestone_engine.py` — Architectural Defects

**Location:** `src/persona/milestone_engine.py` (872 lines)
**Status:** NOT in P4 checklist. NOT imported by `__init__.py`. NOT wired to any runtime caller.

### Defects found:

| # | Defect | Location | Severity |
|---|--------|----------|----------|
| 1 | Hardcoded Redis params | Lines 548-557, 831-840: `redis.Redis(host="localhost", port=6380, db=5, ...)` | HIGH |
| 2 | Hardcoded PostgreSQL fallback | Lines 530-537: `host="localhost", port=5433, user="guinevere_core", database="guinevere"` | HIGH |
| 3 | Daemon threads | Lines 500-507: `threading.Thread(target=_worker, daemon=True)` spawned per `record_milestones_async()` call. Each thread independently opens Redis + PostgreSQL connections. Daemon threads are terminated abruptly on event loop shutdown — data loss risk. | HIGH |
| 4 | No dependency injection | All dependencies created inline via `importlib.import_module()`. No config objects, no session reuse, no connection pooling. | MEDIUM |
| 5 | `__import__("os")` pattern | Lines 530, 548: Uses `__import__("os").environ.get(...)` instead of accepting config. Fragile. | LOW |
| 6 | Not in `__init__.py` | `milestone_engine.py` is completely absent from `__init__.py`. The `MILESTONE_LABELS` and `MILESTONE_THRESHOLDS` re-exported from `__init__.py` come from `streak_tracker.py`, NOT from `milestone_engine.py`. The two modules define separate milestone constants. | MEDIUM |

**Runtime impact:** None currently — module has zero callers. But if PersonaPlugin were registered, it would lazy-import milestone_engine via `_get_milestone_engine()` at `persona_plugin.py:83`, and the hardcoded params + daemon threads would become live defects.

---

## 4. Two SafeModeController Instances

**Finding:** Two separate `SafeModeController()` instances are created in the runtime codebase, in different call scopes, with no shared state:

| # | Location | Scope | State persistence |
|---|----------|-------|-------------------|
| 1 | `src/hermes/safety_plugin.py:455` | Plugin singleton (`self._safe_mode_controller`) | Persists across calls within the plugin lifecycle |
| 2 | `src/discord/hermes_conversational.py:457` | Local variable inside `_process_and_respond()` | Fresh instance per conversational message — no state persistence between calls |

**Impact:** The conversational handler creates a new `SafeModeController()` on every message. This means:
- Safe-mode activated by the safety plugin (via HARD STOP callback) is invisible to the conversational handler
- Distress detection in the conversational handler cannot accumulate history across messages
- The two code paths can disagree on whether safe-mode is active

**Verdict:** CRITICAL architectural defect. The conversational handler should share the same `SafeModeController` instance as the safety plugin, or at minimum read the plugin's state from Redis.

---

## 5. Stale Wearable Import (`alert_router.py:25`)

**Location:** `src/wearable/alert_router.py:25`

```python
try:
    from src.persona.yandere_fsm import is_safe_mode_active
except ImportError:
    is_safe_mode_active = None  # type: ignore[assignment]
```

**Finding:** `is_safe_mode_active` does NOT exist in `src/persona/yandere_fsm.py`. Grep returns zero matches for this symbol name across the entire `yandere_fsm.py` file. The import always fails, `is_safe_mode_active` is always `None`, and the fallback Redis lookup at lines 110-125 is always used instead.

**Impact:** LOW in isolation — the fallback path (`REDIS_PERSONA_SAFE_MODE_KEY`) works. But the comment at line 115 ("Prefers the yandere_fsm.is_safe_mode_active coroutine when importable") describes functionality that was never implemented. This is dead code masquerading as a feature.

---

## 6. PersonaPlugin Registration Status

**Finding:** `guinevere-persona` plugin is NOT registered in any Hermes config.

| Plugin | Source | Plugin package | Registered? |
|--------|--------|---------------|-------------|
| `guinevere-safety` | `src/hermes/safety_plugin.py` | `.hermes/plugins/guinevere-safety/` | YES — Hermes discovers from `~/.hermes/plugins/` |
| `guinevere-persona` | `src/hermes/plugins/persona_plugin.py` | `hermes-config/plugins/guinevere_persona/` | NO — not in `~/.hermes/plugins/`, no config path |

**Evidence:**
- `.hermes/plugins/guinevere-safety/plugin.yaml` exists with 6 hooks
- `hermes-config/plugins/guinevere_persona/plugin.yaml` exists with 4 hooks but is in a config staging directory, not the discovery path
- VPS config `hermes-config/config.yaml` has no `plugins:` section referencing external plugin paths
- No `.hermes/plugins/guinevere-persona/` directory exists

**Impact:** The full persona state block (mood variant, punishment level, reward tier, relationship stage, emotional residue, corruption mode) is NOT injected into LLM prompts. The safety plugin provides partial coverage (yandere level, distress detection, drift detection) but the richer persona context is absent.

---

## 7. Verification.md Path Errors (P4-017 through P4-023)

The verification.md files for the 7 test-only steps claim test files at `tests/persona/` but the actual locations are:

| Step | Claimed path | Actual path | Exists at actual? |
|------|-------------|-------------|-------------------|
| P4-017 | `tests/persona/test_hard_stop_integration.py` | `tests/safety/test_hard_stop_comprehensive.py` | YES |
| P4-018 | `tests/persona/test_distress_detection.py` | `tests/persona/test_distress_detection.py` | YES (correct) |
| P4-019 | `tests/persona/test_persona_e2e.py` | `tests/persona/test_persona_e2e.py` | YES (correct) |
| P4-020 | `tests/persona/test_yandere_cap.py` | `tests/safety/test_yandere_cap.py` | YES |
| P4-021 | `tests/persona/test_consent_revocation.py` | `tests/safety/test_consent_revocation.py` | YES |
| P4-022 | `tests/persona/test_punishment_overflow.py` | `tests/safety/test_punishment_overflow.py` | YES |
| P4-023 | `tests/persona/test_distress_e2e.py` | `tests/safety/test_distress_protocol_e2e.py` | YES |

5 of 7 verification.md files reference incorrect file paths. The safety-related tests live in `tests/safety/`, not `tests/persona/`.

---

## 8. Runtime Without Unwired Modules — What Breaks?

The 10 unwired modules and their runtime absence impact:

| Module | What happens at runtime without it |
|--------|-----------------------------------|
| `mood_persistence` | Mood state is NOT persisted to PostgreSQL. On restart, mood resets to default (Content). The safety plugin and conversational handler manage mood in-memory only. |
| `transition_rules` | No cooldown enforcement on mood transitions. `mood_engine.evaluate_mood()` has its own basic checks but the richer rule engine (per-pair cooldowns, distress blocking, safe-mode blocking) is bypassed. |
| `punishment_engine` | No punishment is ever applied. No L1-L5 ladder, no escalation, no suspension. The persona cannot punish. |
| `reward_engine` | No rewards are ever granted. No T1-T5 tiers, no streak bonuses. The persona cannot reward. |
| `streak_tracker` | No streak counting. No milestone detection. The persona has no memory of consecutive good/bad behavior. |
| `drift_corrector` | No auto-rollback on persona drift. `drift_detector` (WIRED) can detect drift and alert via safety_plugin, but no corrective action is taken. |
| `milestone_engine` | No milestone recording. No relationship arc progression (R1-R4). No emotional memory. |
| `ritual_scheduler` (deprecated) | No ritual scheduling via APScheduler. Hermes cron handles this separately. |
| `rituals/*` (deprecated, 5 files) | No ritual content generation. Hermes cron fires `hermes chat -Q` commands that produce rituals via LLM, not via these template modules. |
| `persona_plugin` (unregistered) | No persona state injection into LLM prompts. The model has no context about current mood, yandere level, punishment state, or relationship stage. |

**Net effect:** The running persona is a stripped-down safety shell. It can detect distress (D0-D4), enforce HARD STOP, detect drift, and manage yandere levels (Y0-Y5). It cannot reward, punish, track streaks, persist mood, enforce transition cooldowns, correct drift, record milestones, or inject persona context into prompts. The behavioral personality layer is completely absent from runtime.

---

## 9. Checklist-vs-Source Discrepancies

| # | CHECKLIST/PROGRESS Claim | Source Reality | Severity |
|---|--------------------------|---------------|----------|
| 1 | P4-002: "Mood persistence (`persona.mood_states`)" | No `mood_states` table. Actual table is `persona.persona_state` with `state_key="current_mood"` | MEDIUM |
| 2 | P4-008-013: No deprecation noted | All 6 modules deprecated Phase 5, removal Phase 7 | MEDIUM |
| 3 | P4-015: "drift correction (>10% -> alert + rollback)" | Rollback is record-keeping only. No actual prompt reload/replace. | HIGH |
| 4 | P4-020: "Consent Revocation Flow Test" | NO consent-aware code in `src/persona/`. Safety_plugin consent gate (Gate 10) is explicitly DEFERRED at safety_plugin.py:900. | CRITICAL |
| 5 | P4-017-023: Test file paths | 5 of 7 reference wrong directory (`tests/persona/` vs actual `tests/safety/`) | MEDIUM |
| 6 | Test count: 1449 vs 1460 vs 1459 | PROGRESS.md claims 1449, CHECKLIST.md claims 1460, verification.md files sum to 1459 | LOW |
| 7 | `milestone_engine.py` not claimed | 872-line module with hardcoded params, daemon threads, no DI. Not in P4 checklist. | MEDIUM |
| 8 | `SOUL_BASELINE_HASH` hardcoded | `drift_detector.py:62` — no verification against actual SystemPromptMaster | MEDIUM |

---

## ARCHITECTURE VERDICT

**P4 Persona Engine is a partially-deployed safety shell with a complete but unwired behavioral personality layer.**

### What works at runtime (4 modules, ~1,232 lines):
- `mood_engine` — evaluates mood from conversation signals (read-only, no persistence)
- `yandere_fsm` — enforces Y0-Y5 ceiling with 5 independent Y6 guards
- `drift_detector` — detects persona prompt drift via SHA-256 hamming
- `safe_mode` — D0-D4 distress detection, safe-mode activation at D2+

### What does NOT work at runtime (13 modules, ~4,917 lines):
- **Punishment/reward/streak** — zero behavioral feedback loop
- **Mood persistence** — mood resets on every restart
- **Transition rules** — no cooldown enforcement
- **Drift correction** — detection without correction
- **Milestone engine** — no relationship arc, no emotional memory
- **All rituals** — deprecated, replaced by Hermes cron
- **PersonaPlugin** — not registered, no persona context in prompts

### Critical defects requiring immediate attention:
1. **P4-020 consent revocation claim is FALSE** — no consent-aware code exists in `src/persona/`, and the safety_plugin consent gate (Gate 10) is explicitly deferred. The 44 tests in `test_consent_revocation.py` exercise a feature that has no runtime integration.
2. **Two SafeModeController instances with no shared state** — safety_plugin and conversational handler maintain independent safe-mode state. A HARD STOP triggered by the plugin is invisible to the conversational handler.
3. **PersonaPlugin not registered** — the entire persona context injection system (mood variant, yandere level, punishment state, relationship stage) is dead. The LLM has no persona awareness.
4. **5 of 7 test-only verification.md files reference wrong file paths** — undermines evidence credibility.

### Severity classification:
- **4 WIRED** modules provide safety-critical function (distress detection, yandere ceiling, drift detection, safe mode)
- **6 DEAD CODE** modules represent wasted implementation effort and a false completeness signal
- **6 DEPRECATED** modules are correctly superseded by Hermes cron but not yet removed
- **5 HALF-IMPLEMENTED** verification.md files contain path errors that would fail auditor cross-check

**Overall: The persona safety boundary is functional. The persona behavioral engine is architecturally complete but operationally dead. The gap between checklist claims and runtime reality is significant.**

# Phase 5: Persona File Migration Gap Analysis

## Executive Summary

This report maps every `src/persona/` file to its Phase 5 Hermes migration destination, evaluating current state, integration points, and migration risks. The analysis aligns with `phase-5-skills.md` and `ADR-035-hermes-migration.md`, enforcing the 5-pillar hybrid architecture: PostgreSQL primary memory, Hermes hooks/plugins for safety, and selective skill adoption.

**Key Findings:**
- **4 files** are designated **KEEP VERBATIM** (Yandere FSM, Safe Mode, Drift Detector, Drift Corrector) due to strict safety boundary enforcement.
- **4 files** require **REFACTOR** to integrate with Hermes hooks/plugins or consolidate into `GuinevereSafetyPlugin`.
- **2 files** map to **SKILL** creation (mood-tracker, streak-tracker) with Python backend retention.
- **1 file group** (`rituals/`) is slated for **PORT TO SOUL.md** (static templates) + **SKILL** (persona-rituals).
- **Total Lines Analyzed:** ~4,200 lines across 15 targets.
- **Overall Migration Risk:** MEDIUM (driven by punishment_engine and mood_persistence DB alignment).

---

## Per-File Analysis

| File | LOC | Key Classes/Functions | Complexity | Phase 5 Destination | Migration Difficulty | Persona Drift Risk |
|---|---|---|---|---|---|---|
| `yandere_fsm.py` | 336 | `YandereEngine`, `YandereLevel`, `validate_level` | Medium | **KEEP VERBATIM** | LOW | LOW |
| `transition_rules.py` | 278 | `TransitionRuleEngine`, `TransitionContext` | Medium | **REFACTOR** (Hermes hook/plugin) | MEDIUM | MEDIUM |
| `streak_tracker.py` | 332 | `StreakTracker`, `save`, `load` | Medium | **SKILL** (mood-tracker backend) | MEDIUM | LOW |
| `safe_mode.py` | 372 | `DistressDetector`, `SafeModeController` | Medium | **KEEP VERBATIM** | LOW | LOW |
| `reward_engine.py` | 380 | `RewardEngine`, `RewardTier`, `calculate_tier` | Medium | **REFACTOR** (persona plugin) | LOW | LOW |
| `punishment_engine.py` | 576 | `PunishmentEngine`, `PunishmentLevel` | High | **REFACTOR** (GuinevereSafetyPlugin) | HIGH | HIGH |
| `mood_engine.py` | 176 | `Mood`, `evaluate_mood`, `can_transition` | Simple | **SKILL** (mood-tracker core) | LOW | LOW |
| `mood_persistence.py` | 314 | `MoodRepository`, `set_current_mood` | Medium | **REFACTOR** (PostgreSQL bridge) | MEDIUM | MEDIUM |
| `drift_detector.py` | 226 | `DriftDetector`, `compute_drift_score` | Simple | **KEEP VERBATIM** | LOW | LOW |
| `drift_corrector.py` | 332 | `DriftCorrector`, `evaluate`, `rollback` | Medium | **KEEP VERBATIM** | MEDIUM | LOW |
| `ritual_scheduler.py` | 405 | `RitualScheduler`, `RitualConfig` | High | **REFACTOR** (Hermes cron + plugin) | MEDIUM | MEDIUM |
| `rituals/*.py` (5 files) | ~785 | `MorningRitual`, `MiddayRitual`, etc. | Simple | **PORT TO SOUL.md** + **SKILL** | LOW | LOW |
| `__init__.py` | 235 | Module re-exports | Simple | **REFACTOR** (update exports) | LOW | LOW |

---

## Migration Matrix by Destination

### 1. KEEP VERBATIM (No Changes)
*Files that strictly enforce safety boundaries and require zero logic modification.*
- `src/persona/yandere_fsm.py` — Y4 baseline, Y5 ceiling, Y6 prohibition enforcement.
- `src/persona/safe_mode.py` — D0-D4 distress detection, HARD STOP integration.
- `src/persona/drift_detector.py` — SHA-256 prompt hash comparison.
- `src/persona/drift_corrector.py` — Auto-rollback logic respecting safe_mode.

### 2. REFACTOR (Integrate with Hermes)
*Files that require adaptation to Hermes lifecycle hooks or consolidation into `GuinevereSafetyPlugin`.*
- `src/persona/punishment_engine.py` — Consolidate into `GuinevereSafetyPlugin`. Ensure L6 remains deferred. Map `apply`/`escalate` to `pre_tool_call` or custom plugin state.
- `src/persona/reward_engine.py` — Integrate into persona plugin. Always permitted (never blocked by safe_mode).
- `src/persona/ritual_scheduler.py` — Replace APScheduler with Hermes native cron (`hermes cron add`). Retain WIB timezone logic.
- `src/persona/transition_rules.py` — Adapt cooldown logic to Hermes `pre_prompt` or plugin state management.
- `src/persona/mood_persistence.py` — Ensure AsyncSession operations align with ADR-035 hybrid memory model (PostgreSQL primary, Hermes read-only supplements).

### 3. SKILL (Instruction Layer + Python Backend)
*Files that will be wrapped by Hermes SKILL.md definitions while retaining Python execution.*
- `src/persona/mood_engine.py` → `mood-tracker` skill. Pure FSM logic remains in Python, triggered by skill instructions.
- `src/persona/streak_tracker.py` → `mood-tracker` or `persona-rituals` skill. DB persistence via `PersonaState` remains intact.

### 4. PORT TO SOUL.md (Static Declarations)
*Static templates and rules that belong in the agent's identity constitution.*
- `src/persona/rituals/morning.py`, `midday.py`, `afternoon.py`, `evening.py`, `midnight.py` — Message templates and mood-aware variants will be ported to `config/hermes/SOUL.md` under "Daily Rituals" and "Communication Instructions" sections, as specified in `phase-5-skills.md` Step 5.2.

---

## Integration Points Summary

| Integration Target | Files Involved | Mechanism |
|---|---|---|
| **GuinevereSafetyPlugin** | `yandere_fsm.py`, `safe_mode.py`, `punishment_engine.py`, `drift_corrector.py` | `SupportsIsSafe` protocol, `is_safe` property checks, plugin lifecycle methods (`on_message`, `pre_prompt`). |
| **PostgreSQL (Async)** | `streak_tracker.py`, `mood_persistence.py`, `drift_corrector.py` | `sqlalchemy.ext.asyncio.AsyncSession`. Retained as primary write authority per ADR-007. |
| **Redis** | *None directly in persona/* | (Note: `session_adapter.py` uses DB4, but persona files rely on PostgreSQL for state). |
| **Async/Await** | `streak_tracker.py`, `mood_persistence.py`, `drift_corrector.py`, `ritual_scheduler.py` | Native `async def` for DB I/O and APScheduler callbacks. |
| **Hermes Hooks** | `safe_mode.py` (pre_prompt), `drift_detector.py` (post_prompt), `punishment_engine.py` (pre_tool_call) | Shell-command hooks returning exit codes 0 (pass), 1 (block), 2 (warn). |

---

## Risk Assessment & Mitigation

| Risk ID | Description | Severity | Mitigation Strategy |
|---|---|---|---|
| **R-01** | `punishment_engine.py` L6 boundary violation during refactor | HIGH | Retain `_L6_VALUE` sentinel and `PunishmentSafetyError`. Add explicit test case asserting L6 raises error in Hermes plugin context. |
| **R-02** | `mood_persistence.py` conflicts with Hermes memory model | MEDIUM | Enforce ADR-035 rule: PostgreSQL is *primary write authority*. Hermes session state is read-only supplement. No schema changes to `PersonaState` or `MoodHistory`. |
| **R-03** | Ritual timezone drift (WIB vs UTC) in Hermes cron | MEDIUM | Explicitly configure Hermes cron jobs with `timezone: "Asia/Jakarta"`. Verify via `hermes cron list` post-migration. |
| **R-04** | SOUL.md porting loses dynamic mood-awareness | LOW | SOUL.md holds static templates. Dynamic mood injection is handled by `GuinevereSafetyPlugin` reading `mood_engine.py` state at runtime. |
| **R-05** | Sub-agent claims completion without verifying scaffold | MEDIUM | Enforce §2.5 Planner Verification Scaffold: parent must re-run `pytest tests/hermes/test_persona_*.py` and verify exit code 0 before accepting. |

---

## Next Actions for Phase 5 Execution

1. **Planner Gate:** Generate `scaffold.md` for each REFACTOR/SKILL task, specifying exact forbidden patterns (`as any`, `@ts-ignore`, bare `except`).
2. **Collision Scan:** Verify no concurrent edits to `config/hermes/SOUL.md` or `plugins/guinevere_safety_plugin.py`.
3. **Delegation:** Assign one sub-agent per atomic step (e.g., "Refactor punishment_engine", "Port rituals to SOUL.md").
4. **Verification:** Parent re-runs scaffold commands. Spawn parallel auditor wave for safety boundary validation.
5. **Evidence:** Generate `verification.md` and `auditor-gate.md` in `evidence/phase-5-persona/`.

---
*Generated by Guinevere Research Sub-Agent. Compliant with AGENTS.md §2.2 (Research Wave) and §2.9 (File-Based Output Discipline).*

# P4 Behavioral Engines Resolution

**Date:** 2026-06-26
**Status:** DEFERRED — all 6 engines documented as utility code, not removed

---

## Decision Per Engine

| Engine | P4 Step | Lines | Decision | Rationale |
|--------|---------|-------|----------|-----------|
| `mood_persistence.py` | P4-002 | 329 | **DEFERRED — utility** | MoodRepository is the PostgreSQL persistence layer. PersonaPlugin reads Redis directly. Keep as utility for callers that need PG persistence. Document: "Redis-primary, PG-optional." |
| `transition_rules.py` | P4-003 | 375 | **DEFERRED — utility** | TransitionRuleEngine has safety logic (safe_mode/distress blocking, cooldowns, forced transitions). Keep for callers needing deterministic transition evaluation. |
| `punishment_engine.py` | P4-005 | 666 | **DEFERRED — utility** | PunishmentEngine has L6 guard, safe-mode/HARD STOP guards, distress suspension. Discord /punishment commands write directly to Redis. Keep as utility. |
| `reward_engine.py` | P4-006 | 445 | **DEFERRED — utility** | RewardEngine T1-T5, quality score, streak bonus. Discord /reward commands write directly. Keep as utility. |
| `streak_tracker.py` | P4-007 | 332 | **DEFERRED — utility** | StreakTracker persists to PersonaState table. Keep as utility. |
| `drift_corrector.py` | P4-015 | 332 | **DEFERRED — utility (alerts only)** | DriftDetector IS wired (safety_plugin.py). DriftCorrector "rollback" is log-only (records baseline hash, does NOT reload prompt). Keep code, document as "drift logging + alert — no prompt reload." |

---

## What Changes

**No source code was modified.** All engines remain in `src/persona/` with their full implementation. The only change is documentation: these engines are correctly described as "utility code — available for callers that need them" rather than "runtime active."

---

## Why Not Remove

All 6 engines are structurally sound:
- Proper error hierarchies
- Safety guards (safe-mode, HARD STOP, L6)
- Structlog instrumentation
- PersonaPlugin hook methods (get_state_snapshot, get_config, get_session)
- Discord command integration points

Removing them would eliminate their utility for future callers. Keeping them as-is is the correct engineering choice — they are library modules, not dead code in the traditional sense.

---

## Deferred Integration Path

If a future phase (P24 fork convergence, P23 action runtime) needs these engines, the integration path is:

1. `mood_persistence` → PersonaPlugin can optionally read from PG when Redis is unavailable
2. `transition_rules` → safety_plugin can call evaluate() before allowing mood transitions
3. `punishment_engine` → PersonaPlugin/safety_plugin can instantiate and enforce punishment lifecycle
4. `reward_engine` → Same pattern as punishment
5. `streak_tracker` → PersonaPlugin can load/save streak state between LLM calls
6. `drift_corrector` → Requires a prompt-reload mechanism first (currently does not exist)

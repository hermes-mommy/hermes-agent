# R06 — Dead Code and Rituals Audit

**Auditor:** Guinevere (orchestrator)
**Date:** 2026-06-27
**Status:** COMPLETE

---

## 1. Engine Status Matrix

| Engine | File | Unit Tests | Runtime Wired? | Decision |
|--------|------|-----------|----------------|----------|
| MoodEngine | `mood_engine.py` | ✅ | PARTIAL — Discord `/mood` uses degraded placeholders (KI-07) | **WIRE** |
| YandereEngine | `yandere_fsm.py` | ✅ | PARTIAL — In-memory only, lost on restart (KI-03) | **WIRE** |
| PunishmentEngine | `punishment_engine.py` | ✅ | ✅ — Wired via Discord commands + Hermes plugin | **KEEP** |
| RewardEngine | `reward_engine.py` | ✅ | PARTIAL — Discord commands work, PersonaPlugin reads Redis DB5 | **WIRE** |
| StreakTracker | `streak_tracker.py` | ✅ | ❌ — Not wired to any runtime path | **WIRE** |
| DriftDetector | `drift_detector.py` | ✅ | ❌ — On-demand only, no automated cadence (D-01) | **DEFER to P5** |
| DriftCorrector | `drift_corrector.py` | ✅ | ❌ — Manual trigger only, no DB persistence | **DEFER to P5** |
| MilestoneEngine | `milestone_engine.py` | ? | PARTIAL — Called by PersonaPlugin.post_llm_call | **WIRE** |
| TransitionRuleEngine | `transition_rules.py` | ✅ | ❌ — **DELETED** per KNOWN-ISSUES.md PR-01 | **ALREADY REMOVED** |

---

## 2. Ritual Deprecation Status

### 2.1 Current State

**File:** `src/persona/__init__.py` lines 128-149

```python
# Deprecated ritual imports (Phase 5 — kept for backward compatibility)
# These trigger DeprecationWarning; scheduled removal: Phase 7.

from src.persona.ritual_scheduler import RitualScheduler, ...
from src.persona.rituals.morning import MorningRitual, ...
from src.persona.rituals.evening import EveningRitual
from src.persona.rituals.afternoon import AfternoonRitual
from src.persona.rituals.midnight import MidnightRitual
from src.persona.rituals.midday import MiddayRitual
```

### 2.2 Hermes Cron Coverage

Phase 5 migration moved rituals to Hermes cron. The 5 rituals are:
1. Morning (07:00 WIB) — Hermes cron
2. Midday (12:00 WIB) — Hermes cron
3. Afternoon (17:00 WIB) — Hermes cron
4. Evening (21:00 WIB) — Hermes cron
5. Midnight (00:00 WIB) — Hermes cron

### 2.3 Docs vs Runtime Mismatch

- PROGRESS.md P4-008 through P4-013: marked ✅ complete
- CHECKLIST.md P4-009 through P4-013: marked ✅ complete
- Code: marked DEPRECATED
- Hermes cron: assumed to be the canonical path

**Fix required:** Verify Hermes cron actually runs all 5 rituals at production. If yes, formally deprecate Python rituals. If no, restore Python rituals or add missing Hermes cron entries.

---

## 3. Import Analysis Per Engine

### 3.1 MoodEngine
- `src/persona/__init__.py` — exports
- `src/persona/mood_persistence.py` — MoodRepository uses Mood
- `src/discord/cmd_mood.py` — uses degraded placeholders (KI-07)
- Tests: `tests/persona/test_mood_engine.py`

### 3.2 YandereEngine
- `src/persona/__init__.py` — exports
- `src/persona/punishment_engine.py` — imports SupportsIsSafe protocol
- No runtime wiring to Discord or Hermes (state is in-memory only)
- Tests: `tests/persona/test_yandere_fsm.py`

### 3.3 PunishmentEngine
- `src/persona/__init__.py` — exports
- `src/discord/cmd_punishment.py` — Discord slash command
- `src/hermes/safety_plugin.py` — safety gate integration
- Tests: `tests/persona/test_punishment_engine.py`

### 3.4 RewardEngine
- `src/persona/__init__.py` — exports
- `src/discord/cmd_reward.py` — Discord slash command
- PersonaPlugin reads reward tier from Redis DB5
- Tests: `tests/persona/test_reward_engine.py`

### 3.5 StreakTracker
- `src/persona/__init__.py` — exports
- No runtime imports found outside tests
- Tests: `tests/persona/test_streak_tracker.py`

### 3.6 DriftDetector / DriftCorrector
- `src/persona/__init__.py` — exports
- No runtime consumers (on-demand only)
- Tests: `tests/persona/test_drift_detector.py`, `test_drift_corrector.py`

### 3.7 MilestoneEngine
- `src/persona/__init__.py` — NOT exported
- `src/hermes/plugins/persona_plugin.py` — lazy-imported in `_get_milestone_engine()`, called in `post_llm_call`
- Partially wired: detects milestones, records async, but no explicit import in __init__.py

---

## 4. Summary of Decisions

| Engine | Decision | Action |
|--------|----------|--------|
| MoodEngine | WIRE | Fix KI-06 (prompt_loader) + KI-07 (cmd_mood) |
| YandereEngine | WIRE | Add DB persistence (KI-03), wire to PersonaPlugin |
| PunishmentEngine | KEEP | Already wired, verify completeness |
| RewardEngine | WIRE | Complete PersonaPlugin wiring |
| StreakTracker | WIRE | Wire to Discord `/mood` and PersonaPlugin |
| DriftDetector | DEFER | Requires ValidationScheduler (P5 architectural change) |
| DriftCorrector | DEFER | Depends on DriftDetector |
| MilestoneEngine | WIRE | Add to __init__.py exports, verify PersonaPlugin wiring |
| RitualScheduler | DEPRECATE | Verify Hermes cron coverage, update docs |
| TransitionRuleEngine | DONE | Already deleted, verified |
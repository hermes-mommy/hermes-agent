# P4 Persona Engine — Superseded / Transition Register

**Date:** 2026-06-26 (corrected 2026-06-26 — live VPS reconciliation)
**Audit:** Legacy Implementation Audit (read-only) + Live VPS Reconciliation

---

## Deprecated Modules (Phase 5, Removal Phase 7 — Never Removed)

| Module | Lines | P4 Step | Deprecation Date | Replacement | Status |
|--------|-------|---------|-----------------|-------------|--------|
| `src/persona/ritual_scheduler.py` | 451 | P4-008 | Phase 5 | Hermes cron (`~/.hermes/crontab.yaml`) | DEPRECATED — not removed |
| `src/persona/rituals/morning.py` | 184 | P4-009 | Phase 5 | Hermes cron + PersonaPlugin | DEPRECATED — not removed |
| `src/persona/rituals/midday.py` | 186 | P4-010 | Phase 5 | Hermes cron + PersonaPlugin | DEPRECATED — not removed |
| `src/persona/rituals/afternoon.py` | 140 | P4-011 | Phase 5 | Hermes cron + PersonaPlugin | DEPRECATED — not removed |
| `src/persona/rituals/evening.py` | 156 | P4-012 | Phase 5 | Hermes cron + PersonaPlugin | DEPRECATED — not removed |
| `src/persona/rituals/midnight.py` | 177 | P4-013 | Phase 5 | Hermes cron + PersonaPlugin | DEPRECATED — not removed |

**Note:** All 6 modules have `DeprecationWarning` at module level. The `__init__.py` suppresses these warnings at import time (`warnings.catch_warnings()` at line 128-129). The scheduled Phase 7 removal target has passed. The Hermes cron replacement exists in `hermes-config/config.yaml` lines 294-318 but is stripped-down (simple `hermes chat -Q` calls, not the same ritual logic).

---

## Split Ownership (Persona Logic vs Runtime Instantiation)

The persona engine is NOT solely owned by `src/persona/`. Runtime ownership is split across multiple locations:

| Surface | File | Role | Status |
|---------|------|------|--------|
| **Core logic** | `src/persona/` (19 files) | Mood FSM, yandere FSM, safe-mode, punishment, reward, drift, streak, rituals | ACTIVE (source of truth for logic) |
| **Hermes safety plugin** | `src/hermes/safety_plugin.py` | Instantiates YandereEngine, SafeModeController, DistressDetector. Wires these into Hermes agent loop. | ACTIVE (runtime instances) |
| **Hermes persona plugin** | `src/hermes/plugins/persona_plugin.py` | Reads Redis DB5, injects [PERSONA STATE] block, milestone detection. | **LIVE (WIRED)** — corrected 2026-06-26. VPS journal: 3,086 combined injection events (hermes-gateway: 45, guinevere-core: 3,041). Registration via `hermes-config/plugins/guinevere_persona/__init__.py`. |
| **Discord conversational** | `src/discord/hermes_conversational.py` | Creates second SafeModeController instance. Imports Mood enum. | ACTIVE (separate instance) |
| **Wearable alert router** | `src/wearable/alert_router.py` | Stale import of `is_safe_mode_active` (doesn't exist). Falls back to Redis. | DEGRADED (stale) |
| **Wearable mood integration** | `src/wearable/mood_integration.py` | Imports Mood enum. GHI → mood modifier. | ACTIVE |
| **Prompt loader** | `src/core/services/prompt_loader.py` | `get_system_prompt_with_context(mood="Content")` — hardcoded default. | ACTIVE (hardcoded) |
| **Loop prompts** | `src/loops/prompts.py` | Uses static SystemPromptMaster doc, not live P4 FSM. | ACTIVE (static) |

---

## Partially Superseded by Hermes Cron

### Rituals: P4 APScheduler → Hermes Cron
- **Original:** `src/persona/ritual_scheduler.py` — APScheduler-based, 5 rituals with mood-aware greetings, health reminders, task summaries, DND window.
- **Replacement:** `hermes-config/config.yaml` lines 294-318 — 5 cron jobs firing `hermes chat -Q -q 'Execute ... ritual'` at WIB times.
- **Gap:** The Hermes cron jobs are simple prompt-based calls. They do NOT use the same mood-aware greeting logic, health reminder rotation, or DND gating as the original rituals. The replacement is not feature-equivalent.
- **Status:** PARTIALLY SUPERSEDED — Hermes cron handles scheduling, but the ritual content logic is not replicated.

---

## Partially Superseded by Hermes Safety Plugin

### Yandere FSM: src/persona → safety_plugin.py
- **Original:** `src/persona/yandere_fsm.py` — YandereEngine, YandereLevel, validate_level, get_effective_level, can_escalate.
- **Consumer:** `src/hermes/safety_plugin.py` imports and instantiates YandereEngine (line 526). Uses it for G07 (yandere boundary) gate.
- **Status:** SUPERSEDED at runtime — the safety_plugin is the sole runtime owner of YandereEngine. src/persona/yandere_fsm.py remains the logic source of truth.

### Safe Mode: src/persona → safety_plugin.py + hermes_conversational.py
- **Original:** `src/persona/safe_mode.py` — SafeModeController, DistressDetector, DistressLevel, DISTRESS_PATTERNS.
- **Consumers:** `safety_plugin.py:455` (Hermes agent loop), `hermes_conversational.py:457` (Discord handler). Two separate instances.
- **Status:** SUPERSEDED at runtime — but split across two instances with no shared state. This is a SUPERSESSION GAP.

### Drift Detection: src/persona → safety_plugin.py
- **Original:** `src/persona/drift_detector.py` — DriftDetector, SHA-256 hamming distance.
- **Consumer:** `safety_plugin.py:484,823,846` (post_llm_call, transform_llm_output hooks).
- **Status:** SUPERSEDED at runtime — safety_plugin is the sole runtime owner.

---

## Not Yet Superseded (Still Solely Owned by src/persona/)

These modules have NO runtime consumer at all. They exist only in `src/persona/` and tests:

| Module | P4 Step | Reason Not Superseded |
|--------|---------|----------------------|
| `mood_persistence.py` | P4-002 | Dead code. Neither superseded nor wired. |
| `transition_rules.py` | P4-003 | Dead code. Neither superseded nor wired. |
| `punishment_engine.py` | P4-005 | Dead code. Neither superseded nor wired. |
| `reward_engine.py` | P4-006 | Dead code. Neither superseded nor wired. |
| `streak_tracker.py` | P4-007 | Dead code. Neither superseded nor wired. |
| `drift_corrector.py` | P4-015 | Dead code. Neither superseded nor wired. |

---

## P24 Fork Convergence Path

For P24 (Hermes full owned fork convergence), the persona engine needs:

1. **Consolidate SafeModeController instances** — merge the two instances into a single singleton or Redis-backed shared state.
2. **PersonaPlugin is live** — confirmed injecting on VPS. No registration action needed. **Verify behavioral engine backing** — Redis keys may contain defaults.
3. **Wire dead modules or remove them** — 6 modules are dead code. Decide: wire them into the Hermes plugin system, or remove them as dead weight.
4. **Fix stale wearable import** — `alert_router.py:25` imports non-existent symbol.
5. **Wire live mood into external channels** — WhatsApp/Gmail bridges hardcode `mood="Content"`.
6. **Remove deprecated ritual code** — Phase 7 removal was scheduled but never executed. If Hermes cron is the replacement, remove the APScheduler code.
7. **Decide: keep src/persona/ as-is or migrate into Hermes built-in extensions** — P24 research rates persona convergence as "Extension sufficient" — PersonaPlugin + SafetyPlugin hooks already integrate with Hermes. The split is manageable.

---

## Summary

| Category | Count |
|----------|-------|
| Deprecated not removed | 6 modules |
| Split ownership surfaces | 8 surfaces |
| Partially superseded (runtime) | 3 modules (yandere, safe_mode, drift_detector) |
| Partially superseded (scheduling) | 6 modules (rituals) |
| Not superseded, not wired | 6 modules |
| **TOTAL transition items** | **18** |
# P4 Persona Engine — Implementation Gap Register

**Date:** 2026-06-26 (corrected 2026-06-26 — live VPS reconciliation)
**Audit:** Legacy Implementation Audit (read-only) + Live VPS Reconciliation

---

## Dead Code at Runtime

### GAP-01: Mood Persistence (mood_persistence.py) — Not Called
- **Module:** `src/persona/mood_persistence.py` (329 lines)
- **P4 step:** P4-002
- **Status:** DEAD CODE — no runtime caller injects AsyncSession into MoodRepository.
- **What exists:** Full implementation with MoodRepository, MoodState, MoodHistoryRecord, proper error hierarchy, PersonaPlugin hooks. PersonaState table exists in alembic schema.
- **What's missing:** No runtime code calls `MoodRepository.get_current_mood()`, `set_current_mood()`, or `record_mood_transition()`. Mood state is managed via Redis DB5 (`guinevere:mood_variant`) only.
- **Risk:** Dual-write inconsistency if both Redis and PostgreSQL paths were ever active simultaneously.
- **Source:** `research/p4-runtime-readiness-readonly.md` lines 198, 247-251.

### GAP-02: Transition Rules (transition_rules.py) — Not Called
- **Module:** `src/persona/transition_rules.py` (375 lines)
- **P4 step:** P4-003
- **Status:** DEAD CODE — no runtime caller.
- **What exists:** TransitionRuleEngine with safe_mode blocking, distress>=D2 blocking, cooldown enforcement, forced transitions, LLM bridge (deprecated, no LLM called).
- **What's missing:** No runtime code calls `TransitionRuleEngine.evaluate()`. Mood transitions are not enforced at runtime.
- **Risk:** Without transition rules, mood changes happen without cooldown or safety gating.
- **Source:** `research/p4-runtime-readiness-readonly.md` lines 202, `audits/round-1/mood-punishment-reward-runtime.md`.

### GAP-03: Punishment Engine (punishment_engine.py) — Not Called
- **Module:** `src/persona/punishment_engine.py` (666 lines)
- **P4 step:** P4-005
- **Status:** DEAD CODE — no runtime caller.
- **What exists:** Full L1-L5 ladder, L6 guard, safe_mode/HARD STOP guards, distress suspension, PersonaPlugin hooks.
- **What's missing:** No runtime code instantiates PunishmentEngine. Discord /punishment commands exist but write directly to PunishmentLog via get_async_session(), bypassing the engine.
- **Risk:** Punishment ladder is never enforced. L6 guard is never tested at runtime. check_distress_suspension() has zero callers.
- **Source:** `research/p4-runtime-readiness-readonly.md` lines 199, `audits/round-1/mood-punishment-reward-runtime.md`.

### GAP-04: Reward Engine (reward_engine.py) — Not Called
- **Module:** `src/persona/reward_engine.py` (445 lines)
- **P4 step:** P4-006
- **Status:** DEAD CODE — no runtime caller.
- **What exists:** Full T1-T5 tier system, quality score calculation, streak bonus, PersonaPlugin hooks.
- **What's missing:** No runtime code instantiates RewardEngine. Discord /reward commands exist but write directly to RewardLog.
- **Risk:** Reward tiers are never calculated or enforced at runtime.
- **Source:** `research/p4-runtime-readiness-readonly.md` lines 200, `audits/round-1/mood-punishment-reward-runtime.md`.

### GAP-05: Streak Tracker (streak_tracker.py) — Not Called
- **Module:** `src/persona/streak_tracker.py` (332 lines)
- **P4 step:** P4-007
- **Status:** DEAD CODE — no runtime caller.
- **What exists:** Full streak tracking with milestones (7/14/30/90/365 days), persistence via PersonaState table.
- **What's missing:** No runtime code calls StreakTracker.increment(), reset(), or get_display_text().
- **Risk:** Streak days are never tracked. Milestone notifications never fire.
- **Source:** `research/p4-runtime-readiness-readonly.md` lines 201, `audits/round-1/mood-punishment-reward-runtime.md`.

### GAP-06: Drift Corrector (drift_corrector.py) — Not Called
- **Module:** `src/persona/drift_corrector.py` (332 lines)
- **P4 step:** P4-015
- **Status:** DEAD CODE — no runtime caller.
- **What exists:** DriftCorrector.evaluate() with auto-rollback logic, DriftLog persistence.
- **What's missing:** No runtime code calls DriftCorrector.evaluate(). The "rollback" is record-keeping only (writes baseline hash, doesn't reload prompt).
- **Risk:** Drift is detected (drift_detector IS wired) but never corrected. The system knows when persona has drifted but can't fix it.
- **Source:** `research/p4-runtime-readiness-readonly.md` lines 198, `audits/round-1/architecture-implementation.md` line 34.

---

## Deprecated but Not Removed

### GAP-07: Ritual Scheduler + 5 Rituals — Deprecated, Not Removed
- **Modules:** `ritual_scheduler.py` (451 lines) + `rituals/morning.py` (184), `midday.py` (186), `afternoon.py` (140), `evening.py` (156), `midnight.py` (177)
- **P4 steps:** P4-008 through P4-013
- **Status:** DEPRECATED — Phase 5, scheduled removal Phase 7. Removal never happened.
- **What exists:** Full APScheduler-based ritual system with mood-aware greetings, health reminders, DND window, Jakarta timezone.
- **What's missing:** No live instantiation of RitualScheduler. Hermes cron replacement exists in `hermes-config/config.yaml` (lines 294-318) but is stripped-down (simple `hermes chat -Q` calls, not the same ritual logic).
- **Risk:** Deprecated code lingers, creating confusion about what's actually running. The Hermes cron replacement is not feature-equivalent. Deprecation warnings are suppressed in `__init__.py:128-129`.
- **Source:** `research/p4-persona-source-map.md` §9-14, `audits/round-1/ritual-scheduler-drift-correction.md`.

---

## Registered Plugin (LIVE — Corrected 2026-06-26)

### GAP-08: PersonaPlugin LIVE — Behavioral Engine Backing Needs Runtime Verification
- **Module:** `src/hermes/plugins/persona_plugin.py` (785 lines) + `hermes-config/plugins/guinevere_persona/__init__.py` (96 lines)
- **P4 step:** Cross-cutting (P5 agent loop, P4 persona state injection)
- **Status:** LIVE AND INJECTING — confirmed via VPS journal (3,086 combined injection events across hermes-gateway + guinevere-core on 2026-06-25). Registration via `hermes-config/plugins/guinevere_persona/__init__.py` → `register(ctx)`.
- **What exists:** Full PersonaPlugin with 4 hooks (pre_llm_call, post_llm_call, pre_tool_call, on_session_start), Redis DB5 pipeline reads of 13 keys, `[PERSONA STATE]` injection block, graceful degradation.
- **What needs verification:** The Redis keys appear to contain default values (punishment_level=0, reward_tier=0 per journal). Runtime verification needed to confirm: (a) Are the behavioral engines actually updating Redis keys? (b) Or is persona state stuck at defaults? (c) Are Redis keys populated by Discord commands, safety_plugin, or some other path?
- **Risk:** Persona state injection is working but may be injecting static/default values rather than dynamic computed state.
- **NEEDS RUNTIME VERIFICATION:** Redis DB5 key inspection.
- **Source:** `evidence/p4-live-vps-reconciliation-audit.md`.

---

## Half-Implemented Features

### GAP-09: Consent Revocation — Claimed, Not Implemented
- **P4 step:** P4-020
- **Status:** HALF-IMPLEMENTED — CHECKLIST claims `[x] ✅` complete. Source has NO consent-aware code in `src/persona/`.
- **What exists:** External consent system (consent_ledger table, consent_gate.py, gmail/consent_manager.py). Safety_plugin Gate 10 explicitly deferred.
- **What's missing:** No wiring from consent system to persona engine. Consent revocation does NOT halt mood transitions, yandere escalation, or punishment.
- **Risk:** Persona behavior continues even after consent is revoked. This is a safety boundary gap.
- **Source:** `research/p4-persona-source-map.md` §4 (lines 325-339), `audits/round-1/persona-safety-hardstop-consent.md` §3.

### GAP-10: Drift Rollback — Claimed, Not Implemented
- **P4 step:** P4-015
- **Status:** HALF-IMPLEMENTED — DriftDetector IS wired and detects drift. DriftCorrector is NOT wired and its "rollback" is log-only.
- **What exists:** Drift detection via SHA-256 hamming distance, wired in safety_plugin.py hooks.
- **What's missing:** Real prompt rollback. The "correction" is a log entry. DriftCorrector has no runtime caller.
- **Risk:** System detects persona drift but cannot fix it. The "rollback" claim in documentation is misleading.
- **Source:** `research/p4-persona-source-map.md` §16, `audits/round-1/ritual-scheduler-drift-correction.md`.

---

## Integration Gaps

### GAP-11: External Channels Hardcode Mood
- **Modules:** `src/channels/whatsapp/bridge.py:163`, `src/gmail/bridge.py:530,584`
- **Status:** INTEGRATION GAP — both pass `mood="Content"` hardcoded, never the live persona mood.
- **Risk:** WhatsApp and Gmail users always see "Content" mood regardless of actual persona state. Persona behavior does not flow to external channels.
- **Source:** `research/p4-downstream-impact-p19-p24.md` lines 117-141.

### GAP-12: Two SafeModeController Instances
- **Modules:** `safety_plugin.py:455`, `hermes_conversational.py:457`
- **Status:** ARCHITECTURAL GAP — two independent instances, no shared state.
- **Risk:** HARD STOP triggered in the plugin is invisible to the conversational handler. Split-brain safety risk.
- **Source:** `research/p4-runtime-readiness-readonly.md` lines 163-164, `audits/round-1/architecture-implementation.md` §4.

### GAP-13: Discord on_message Not Wired to DistressDetector
- **Module:** `src/discord/` (on_message pipeline)
- **Status:** INTEGRATION GAP — KNOWN-ISSUES KI-05, still open.
- **Risk:** User messages in Discord bypass distress detection. Distress is only detected in the Hermes agent loop (pre-LLM-call), not at the Discord message ingestion point.
- **Source:** `research/p4-known-issues-reconciliation.md` §KI-05 (lines 138-145).

---

## Summary

| Category | Count | Modules Affected |
|----------|-------|-----------------|
| Dead code at runtime | 6 | mood_persistence, transition_rules, punishment_engine, reward_engine, streak_tracker, drift_corrector |
| Deprecated not removed | 6 | ritual_scheduler, morning, midday, afternoon, evening, midnight |
| Live plugin (needs verification) | 1 | persona_plugin.py (LIVE INJECTING, corrected from "NOT REGISTERED") |
| Half-implemented | 2 | consent revocation, drift rollback |
| Integration gaps | 3 | external channels, SafeModeController dual-instance, Discord on_message |
| **TOTAL** | **18** | |
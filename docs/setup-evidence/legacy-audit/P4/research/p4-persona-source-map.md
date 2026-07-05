# P4 Persona Source Map — Declared Behavior vs Source-Level Reality

Generated: 2026-06-25
Scope: `src/persona/` (5,278 lines across 12 modules + 5 ritual files)
Audit Type: Read-Only Source Inspection

---

## 1. `src/persona/__init__.py` (245 lines)

| Aspect | Detail |
|---|---|
| **Line range** | 1–245 |
| **Structure** | Re-exports all active module public APIs (lines 20–121). Deprecated ritual imports wrapped in `warnings.catch_warnings()` (lines 128–149). |
| **Deprecation markers** | `ritual_scheduler` + `rituals/*` are **deprecated Phase 5**, "Scheduled removal: Phase 7" (lines 4–5, 126–149). Imports trigger `DeprecationWarning`. |
| **Phase 7 removal status** | **Has NOT happened.** All deprecated code remains importable. The `with warnings.catch_warnings(): warnings.simplefilter("ignore", DeprecationWarning)` wrapper (lines 128–129) suppresses the warning during `__init__`, meaning consumers get the deprecated symbols silently. |
| **PersonaPlugin hooks mentioned** | Lines 6–9: "punishment_engine, reward_engine, transition_rules, and mood_persistence expose PersonaPlugin hook methods (get_state_snapshot, get_config, get_session)". Confirmed each has these methods. |
| **Ritual_scheduler imports** | 13 symbols re-exported: `DND_END_HOUR`, `DND_START_HOUR`, `RITUALS`, `RitualConfig`, `RitualExecutionError`, `RitualSchedulerResult`, `RitualScheduler`, `RitualSchedulerError`, `TZ_JAKARTA`, `MorningRitual`, `EveningRitual`, `AfternoonRitual`, `MidnightRitual`, `MiddayRitual`. |
| **AC‑PERSONA‑002 not referenced** | The acceptance criterion is named in CHECKLIST but never imported or cross-referenced in source. |
| **Module not re-exported** | `milestone_engine.py` is **not** imported in `__init__.py` at all. It is a separate, non-integrated module. |

**Verdict**: Deprecation markers are accurate. Removal did not happen in Phase 7 (Phase 7 is Hermes MCP migration, not persona code cleanup — the `docs/setup-evidence/phase-4/` collision may explain why). The ritual code is live but intended for removal.

---

## 2. `src/persona/mood_engine.py` — P4-001 (237 lines)

**CHECKLIST claim**: "Mood FSM (Content → Pleased → Disappointed → Angry → Silent)" — ACCURATE

| Aspect | Detail |
|---|---|
| **Line range** | 1–237 |
| **`Mood` enum** | Lines 25–32: Five states exactly as claimed. |
| **`TRANSITIONS` map** | Lines 39–45: `Content→[Pleased, Disappointed]`, `Pleased→[Content, Disappointed]`, `Disappointed→[Content, Angry]`, `Angry→[Disappointed, Silent]`, `Silent→[Content]`. Not strictly linear — e.g., Content can jump to Disappointed directly. |
| **`evaluate_mood()`** | Lines 163–237: Check order is severity-based: ignored >= 4 → ANGRY, >= 2 → DISAPPOINTED, sentiment > 0.7 + task_completion → PLEASED. Each target validated via `can_transition()`. |
| **`sync_mood_to_redis()`** | Lines 107–142: Maps Mood → variant strings (`Content→"default"`, `Pleased→"playful"`, `Disappointed→"serious"`, `Angry→"caring"`, `Silent→"default"`). Uses duck-typed `StateManager.set_mood()`. No-op if no state_manager. |
| **`can_transition()`** | Lines 150–160: Simple membership check. |
| **`MoodTransition`** | Lines 53–64: Dataclass with cooldown default 300s. |
| **Error hierarchy** | Lines 72–82: `MoodEngineError` → `InvalidMoodTransitionError`, `MoodEvaluationError`. |
| **PersonaPlugin hooks** | None directly in this module. The `MOOD_VARIANT_MAP` (line 94) and `sync_mood_to_redis` are consumed by integration code. |
| **Placeholder/mock behavior** | None. Full deterministic implementation. |
| **Discrepancy** | Checklist says "Content → Pleased → Disappointed → Angry → Silent" (linear progression). The actual FSM allows Content→Disappointed directly (skipping Pleased) and Silent→Content directly (skipping Angry). The label is a simplified summary, not a strict linear pipeline. |

---

## 3. `src/persona/mood_persistence.py` — P4-002 (329 lines)

**CHECKLIST claim**: "Mood persistence (`persona.mood_states`)" — **PARTIALLY WRONG**

| Aspect | Detail |
|---|---|
| **Line range** | 1–329 |
| **Table used** | Lines 24, 107, 149: `PersonaState` model, mapped to `persona.persona_state` (not `mood_states`). |
| **State key mechanism** | Lines 31–32: `_CURRENT_MOOD_KEY = "current_mood"` — mood is stored as a row with `state_key = "current_mood"` in the `persona_state` table. |
| **`MoodRepository`** | Lines 83–330: Provides `get_current_mood()` (line 101), `set_current_mood()` (line 136), `record_mood_transition()` (line 189), `get_mood_history()` (line 221), `get_mood_streak()` (line 255), `update_mood_streak()` (line 284). |
| **`MoodState`** | Lines 57–64: Frozen dataclass with `mood`, `intensity`, `updated_at`, `updated_by`. |
| **`MoodHistoryRecord`** | Lines 67–75: Frozen dataclass with `mood`, `intensity`, `trigger`, `duration_minutes`, `recorded_at`. |
| **Error hierarchy** | Lines 40–49: `MoodPersistenceError` → `MoodPersistenceQueryError`, `MoodPersistenceWriteError`. |
| **PersonaPlugin hooks** | `get_session()` at line 91 returns the underlying AsyncSession for transactional consistency. |
| **No `persona.mood_states` table** | The CHECKLIST claim of `persona.mood_states` is factually wrong. The actual table is `persona.persona_state` with rows keyed by `state_key`. There is no dedicated `mood_states` table. The PROGRESS.md makes the same claim. |

---

## 4. `src/persona/transition_rules.py` — P4-003 (375 lines)

**CHECKLIST claim**: "Mood transition rules (triggers, cooldowns)" — ACCURATE

| Aspect | Detail |
|---|---|
| **Line range** | 1–375 |
| **`VALID_TRANSITIONS`** | Lines 57–63: String-based copy of the mood FSM map (avoids cross-import from mood_engine). |
| **`TransitionRuleEngine`** | Lines 105–375. |
| **`evaluate()`** | Lines 140–252: Check order: (1) safe_mode blocks all, (2) distress >= D2 blocks, (3) transition map validation, (4) cooldown check (unless forced), (5) allow. |
| **Safe mode blocking** | Lines 159–172: `ctx.safe_mode` returns `allowed=False`, `blocked_by="safe_mode"`. |
| **Distress >= D2 blocking** | Lines 174–192: Returns `blocked_by="distress"`. |
| **Cooldown** | Lines 254–293: Supports external Redis TTL provider AND local datetime fallback. |
| **Forced transitions** | Lines 111–113: `("Angry", "Silent")` and `("Content", "Pleased")` bypass cooldown. |
| **LLM bridge deprecation** | Lines 295–350: `should_use_llm_evaluation()` and `evaluate_with_llm()` documented as Phase 5 backward-compat bridges — NO external LLM called. |
| **PersonaPlugin hooks** | `get_state_snapshot()` at line 354, `get_valid_transitions()` (static) at line 368. |
| **Consent revocation NOT handled** | No consent gate, no consent parameter in `TransitionContext`. Consent revocation must be handled externally, not by this engine. |

---

## 5. `src/persona/yandere_fsm.py` — P4-004 (336 lines)

**CHECKLIST claim**: "Yandere FSM (Y0→Y1→Y2→Y3→Y4→Y5 ceiling); Y6 impossible verified" — ACCURATE

| Aspect | Detail |
|---|---|
| **Line range** | 1–336 |
| **`YandereLevel` enum** | Lines 63–77: Y0_NEUTRAL=0 through Y5_MAX=5. No Y6 member. Docstring at line 66–69 explicitly says "Y6 is PROHIBITED". |
| **Y6 truly impossible** | Yes, via three independent guards: (1) No enum member for 6 (`yandere_fsm.py:63-77`), (2) `validate_level()` raises `YandereSafetyError` for value > 5 (`yandere_fsm.py:152-155`), (3) `get_effective_level()` clamps to `min(requested, Y5_MAX)` (`yandere_fsm.py:141`), (4) `can_escalate()` returns False when `current >= ABSOLUTE_CEILING` (`yandere_fsm.py:119`), (5) `YandereEngine.escalate()` calls `validate_level()` which rejects >Y5 (`yandere_fsm.py:251`). |
| **HARD STOP → Y0 neutral** | Lines 95–97: `_any_safety_active()` returns True for safe_mode/distress/crisis. Lines 139–140: `get_effective_level()` returns Y0_NEUTRAL when any safety flag is active. Line 142: non-safety case clamps to [Y0, Y5]. |
| **`can_escalate()`** | Lines 100–121: Returns False when safe_mode, distress, or crisis, or at ceiling. |
| **`get_effective_level()` (free function)** | Lines 124–142: Forces Y0 on safety; clamps otherwise. |
| **`validate_level()`** | Lines 145–161: Raises `YandereSafetyError` for >5, `YandereTransitionError` for <0. |
| **`YandereEngine`** | Lines 169–336: Stateful engine. `escalate()` at line 220, `de_escalate()` at line 261, `get_effective_level()` (instance method) at line 283, `reset_to_baseline()` at line 300, `set_level()` at line 317. |
| **Baseline** | Line 84: `PERMANENT_BASELINE = YandereLevel.Y4_BASELINE`. |
| **Ceiling** | Line 87: `ABSOLUTE_CEILING = YandereLevel.Y5_MAX`. |
| **HardStopHandler integration** | Line 51–56: `SupportsIsSafe` protocol with `is_safe` property. YandereEngine queries it at line 214. |
| **Consent revocation NOT in source** | No consent parameter. The P4-020 claim about "consent revocation halts escalation" would need to feed into `safe_mode` or `crisis` flags externally. The engine itself has no consent-aware path. |

---

## 6. `src/persona/punishment_engine.py` — P4-005 (666 lines)

**CHECKLIST claim**: "Punishment ladder (L1→L5, L6 deferred)" — ACCURATE

| Aspect | Detail |
|---|---|
| **Line range** | 1–666 |
| **`PunishmentLevel` enum** | Lines 73–83: L1_SILENT_TREATMENT=1 through L5_ISOLATION=5. L6 sentinel at line 87: `_L6_VALUE = 6`. |
| **L6 guard** | Lines 278–282: `apply()` raises `PunishmentSafetyError` if level >= 6. Lines 364–367: `escalate()` raises `PunishmentSafetyError` if next_value >= 6. |
| **Safe mode guard** | Lines 292–295: `apply()` blocked when safe_mode is active. Lines 345–353: `escalate()` blocked. |
| **HARD STOP guard** | Lines 297–301: `apply()` blocked if `hard_stop_handler.is_safe`. Lines 349–353: `escalate()` blocked. |
| **Distress suspension** | Lines 584–608: `check_distress_suspension()` suspends when distress >= D3, resumes when below D3 and safe mode not active. |
| **`PunishmentState`** | Lines 201–213: Mutable dataclass with `suspended`, `suspension_reason`, etc. |
| **PersonaPlugin hooks** | `get_state_snapshot()` at line 500, `get_config()` (static) at line 519, `get_current_level()` at line 537. |
| **Consent revocation** | The word "consent" appears only once, at line 270, as an example `violation_type` string literal. No consent-revocation-aware logic. |

---

## 7. `src/persona/reward_engine.py` — P4-006 (445 lines)

**CHECKLIST claim**: "Reward tiers (T1→T5)" — ACCURATE

| Aspect | Detail |
|---|---|
| **Line range** | 1–445 |
| **`RewardTier` enum** | Lines 35–47: T1 through T5. |
| **`REWARD_CONFIG`** | Lines 64–134: Templates for each tier with message_templates in Indonesian/English. |
| **`TIER_THRESHOLDS`** | Lines 143–149: T5>=0.95, T4>=0.80, T3>=0.60, T2>=0.40, T1>=0.20. |
| **`calculate_tier()`** | Lines 248–299: `effective = quality_score + min(streak * 0.05, 0.30)`, clamped [0,1]. Checks thresholds highest-first. |
| **`should_reward()`** | Lines 303–333: Always allowed regardless of safe_mode/distress. The docstring explicitly states: "Rewards are always permitted, even when safe-mode is active or distress has been detected." |
| **`award()`** | Lines 337–394: Records tier, picks first message template, syncs to Redis if state_manager set. |
| **`RewardResult`** | Lines 174–186: Frozen dataclass with `tier`, `reason`, `streak_count`, `message`. |
| **PersonaPlugin hooks** | `get_state_snapshot()` at line 417, `get_config()` (static) at line 430. |
| **No suppression logic** | Rewards are truly never suppressed — consistent with claim. |

---

## 8. `src/persona/streak_tracker.py` — P4-007 (332 lines)

**CHECKLIST claim**: "Streak tracking (days without punishment)" — ACCURATE

| Aspect | Detail |
|---|---|
| **Line range** | 1–332 |
| **`StreakTracker`** | Lines 89–332: `@dataclass` with `_count`, `_last_increment`, `_highest_milestone_reached`. |
| **`increment()`** | Lines 115–134: +1 day, detects milestones, logs. |
| **`reset()`** | Lines 136–150: Sets count to 0. Returns previous count. |
| **Milestones** | Lines 54–63: `MILESTONE_THRESHOLDS` = [7, 14, 30, 90, 365]; `MILESTONE_LABELS` = {"7": "week", "14": "fortnight", etc.}. |
| **`get_display_text()`** | Lines 184–219: Human-readable for /mood command. |
| **Persistence** | Lines 225–332: `save()` and `load()` via `PersonaState` table with upsert, using `state_key = "streak_count"`. |
| **Async SQLAlchemy** | Uses async session for persistence. |
| **Threat model** | Persists across safe_mode/distress; only reset by explicit punishment. |

---

## 9. `src/persona/ritual_scheduler.py` — P4-008 (451 lines)

**CHECKLIST claim**: "Daily ritual scheduler (APScheduler), 5 rituals" — **DEPRECATED**

| Aspect | Detail |
|---|---|
| **Line range** | 1–451 |
| **Deprecation** | Line 11–15: "deprecated in Phase 5 ... Scheduled removal: Phase 7." Line 33–39: Runtime `DeprecationWarning`. |
| **Removal status** | **NOT YET REMOVED.** Code is fully functional. |
| **APScheduler** | Lazy-imported at line 231: `importlib.import_module("apscheduler.schedulers.asyncio")`. |
| **5 rituals** | Lines 112–148: morning(07:00), midday(12:00), afternoon(17:00), evening(21:00), midnight(00:00). |
| **DND window** | Lines 154–158: 00:00–07:00 WIB. |
| **`RitualScheduler`** | Lines 173–452: setup/start/stop lifecycle, DND check, job introspection. |
| **Default callback** | `_default_execute()` at line 430 logs and returns. |

**Verdict**: Checklist item is technically true (code exists), but the code is deprecated. The checklist does not mention the Phase 5 deprecation status.

---

## 10. `src/persona/rituals/morning.py` — P4-009 (184 lines)

**CHECKLIST claim**: "Morning ritual (07:00 WIB)" — **DEPRECATED**

- Lines 10–15: Deprecation marker for Phase 5, removal Phase 7.
- `MorningRitual.execute()` (line 113): Accepts `mood`, `streak_count`, `weather_info`. Generates mood-aware Indonesian greeting.
- Five mood-specific templates at lines 57–72 (Content/Pleased/Disappointed/Angry/Silent).
- DND gate at lines 134–145: Suppresses during 00:00–07:00 WIB.
- **No known integration**: Not consumed by any active code path.

---

## 11. `src/persona/rituals/midday.py` — P4-010 (186 lines)

**CHECKLIST claim**: "Midday ritual (12:00 WIB)" — **DEPRECATED**

- Lines 15–18: Phase 5 deprecation, removal Phase 7.
- `MiddayRitual.execute()` (line 103): Mood-aware greeting + rotating health reminders (eat/water/stretch).
- No DND gate (12:00 is outside quiet window).

---

## 12. `src/persona/rituals/afternoon.py` — P4-011 (140 lines)

**CHECKLIST claim**: "Afternoon ritual (17:00 WIB)" — **DEPRECATED**

- Lines 10–13: Phase 5 deprecation, removal Phase 7.
- `AfternoonRitual.execute()` (line 86): Mood-aware check-in + optional task summary.

---

## 13. `src/persona/rituals/evening.py` — P4-012 (156 lines)

**CHECKLIST claim**: "Evening ritual (21:00 WIB)" — **DEPRECATED**

- Lines 21–24: Phase 5 deprecation, removal Phase 7.
- `EveningRitual.execute()` (line 94): Wind-down greeting + day summary + streak display.

---

## 14. `src/persona/rituals/midnight.py` — P4-013 (177 lines)

**CHECKLIST claim**: "Midnight self-eval (00:00 WIB), silent mode" — **DEPRECATED**

- Lines 14–17: Phase 5 deprecation, removal Phase 7.
- `MidnightRitual.execute()` (line 97): Internal self-evaluation only. Always suppressed (DND active at midnight). Logs via structlog, never delivers to Discord.

---

## 15. `src/persona/drift_detector.py` — P4-014 (227 lines)

**CHECKLIST claim**: "Persona drift detection (SHA-256 hamming distance)" — ACCURATE

| Aspect | Detail |
|---|---|
| **Line range** | 1–227 |
| **`DriftDetector`** | Lines 50–227. |
| **`compute_drift_score()`** | Lines 84–121: SHA-256 hex digest comparison. Exact match→0.0, different length→1.0, same length→Hamming distance ratio. |
| **`detect()`** | Lines 123–172: Returns `DriftResult` with action: `"none"` (≤threshold), `"alert"` (≤2×threshold), `"rollback"` (>2×threshold). |
| **Default threshold** | Line 61: `DEFAULT_THRESHOLD = 0.10`. |
| **SOUL_BASELINE_HASH** | Line 62: Hardcoded `"b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740"`. |
| **`DriftBaseline`** | Lines 40–47: Frozen dataclass with `prompt_hash`, `version`, `created_at`, `description`. |
| **`DriftResult`** | Lines 27–38: Frozen dataclass with full metadata. |
| **Rollback trigger** | At line 147: `action = "rollback"` when score > 2×threshold. |
| **No consistency check** | The `SOUL_BASELINE_HASH` is a hardcoded constant. No verification mechanism ensures this hash actually matches the current SystemPromptMaster document. |

---

## 16. `src/persona/drift_corrector.py` — P4-015 (332 lines)

**CHECKLIST claim**: "Persona drift correction (>10% → alert + rollback)" — ACCURATE (with caveat)

| Aspect | Detail |
|---|---|
| **Line range** | 1–332 |
| **`DriftCorrector`** | Lines 68–332. |
| **`evaluate()`** | Lines 102–186: Runs detection → if drift detected and safe_mode inactive → auto-rollback. If safe_mode active → alert only (defers rollback). Always persists `DriftLog`. |
| **`rollback()`** | Lines 188–268: Does **not** modify persona content. Records baseline hash as "restored state" and persists a `DriftLog` entry. The docstring at line 198 says: "Does **not** modify persona content when safe_mode is active." |
| **Key caveat** | The "rollback" is a **record-keeping operation only** — it does not actually reload or replace the system prompt. The `restored_hash` is simply the `baseline.prompt_hash` from the DriftDetector. There is no code that writes to the actual prompt storage or triggers a reload. This is a logical rollback (audit log), not a physical one. |
| **`DriftLog` table** | Imported from `src.memory.models` at line 14. Used via duck-typed `db.add()` calls at line 315. |
| **Integration** | References `SafeModeController`. No other safety integration (no consent check, no yandere level override). |

---

## 17. `src/persona/safe_mode.py` — P4-016 (432 lines)

**CHECKLIST claim**: "Safe-mode trigger (D0-D4 distress protocol)" — ACCURATE

| Aspect | Detail |
|---|---|
| **Line range** | 1–432 |
| **`DistressLevel` enum** | Lines 46–53: D0_NORMAL through D4_EMERGENCY. |
| **`DISTRESS_PATTERNS`** | Lines 85–107: Regex patterns for each level, bilingual EN/ID. D4 includes `\bsuicid`, `\bself[- ]harm`, `\bbunuh\s+diri`, `\bselamat\s+tinggal\s+selamanya`. |
| **Pattern matching** | Lines 149–212: Checked D4 → D1 (highest first). Confidence = matched/total patterns. D0 if no match. |
| **`SafeModeController`** | Lines 234–432. |
| **Safe mode threshold** | Line 122: `SAFE_MODE_THRESHOLD = DistressLevel.D2_MODERATE`. |
| **`evaluate()`** | Lines 247–281: Activates safe mode if level >= D2. Upgrades trigger level if higher distress seen. |
| **`activate()`** | Lines 345–369: Sets `active=True`, records trigger level and timestamp. Raises `SafeModeError` if trigger < D2. |
| **`deactivate()`** | Lines 371–405: Requires `explicit_confirmation=True`. No auto-deactivation. |
| **`force_safe_mode()`** | Lines 285–343: Bypasses normal evaluation. Idempotent. Used by `HardStopHandler`. |
| **`is_active` property** | Line 423: Returns `state.active`. |
| **`SafeModeState`** | Lines 68–75: Mutable dataclass with distress_history. |
| **No consent integration** | No consent gate reference. Safe mode is purely distress-driven. |

---

## 18. `src/persona/milestone_engine.py` — NOT in P4 Checklist (872 lines)

| Aspect | Detail |
|---|---|
| **Line range** | 1–872 |
| **CHECKLIST claim** | **NONE.** This module is not mentioned in P4-001 through P4-023. |
| **Function** | Implements SOUL.md §K (Emotional Memory) and §M (Relationship Arc). Detects milestone-worthy moments from conversation text via regex, records them to PostgreSQL, syncs state to Redis DB5. |
| **Integration status** | **NOT imported** by `__init__.py`. No module in the P4 source map depends on it. It operates independently. |
| **Redis access** | Lines 548–557, 831–840: Directly instantiates `redis.Redis(host="localhost", port=6380, db=5, ...)` with hardcoded connection params. Falls back to env vars for passwords. |
| **PostgreSQL access** | Lines 460–476, 588–610, 699–752, 785–802, 844–866: Uses `asyncpg.connect()` with parsed DATABASE_URL or hardcoded fallback params (`host=localhost, port=5433, user=guinevere_core, database=guinevere`). |
| **Daemon threads** | Lines 500–507: `record_milestones_async()` spawns a `threading.Thread(target=_worker, daemon=True)` for DB writes. |
| **Detection patterns** | Lines 81–116: 6 pattern sets (Dominance, Trust, Achievement, Conflict, Vulnerability, Escalation). Bilingual EN/ID regex. |
| **Rate limiting** | Line 38: `MAX_MILESTONES_PER_DAY = 3`. Enforced via Redis counter at lines 560–571. |
| **Relationship progression** | Lines 685–813: R1→R2→R3→R4 stage promotion based on milestone counts, active days, trust signals, conflicts. |
| **Risk** | Direct importlib-based dependency loading with hardcoded defaults. No DI, no async session reuse. Daemon threads may be terminated abruptly by the event loop shutdown. |
| **Verdict** | This is a later-phase module (post-P4) that operates independently. It is structurally separate from the persona engine proper. |

---

## Critical Verification: Safety Guarantees at Source Level

### Is Y6 truly impossible?

**YES**, via five independent guards:
1. `yandere_fsm.py:63-77` — `YandereLevel` IntEnum has no member for value 6. The highest is Y5_MAX=5.
2. `yandere_fsm.py:78` — Docstring: "Y6 is PROHIBITED per PersonaSafetyPolicy — no enum member exists for it."
3. `yandere_fsm.py:145-161` — `validate_level()` raises `YandereSafetyError("Y6 is PROHIBITED")` on value > 5.
4. `yandere_fsm.py:119` — `can_escalate()` returns False when `current >= ABSOLUTE_CEILING` (Y5_MAX).
5. `yandere_fsm.py:139-142` — `get_effective_level()` clamps to `min(requested, ABSOLUTE_CEILING)` = Y5 max.

### Does HARD STOP force Y0 neutral?

**YES**, at two independent code paths:
1. `yandere_fsm.py:139-140` — `get_effective_level()` returns `YandereLevel.Y0_NEUTRAL` when any safety flag is active.
2. `yandere_fsm.py:117-118` — `can_escalate()` returns False when safety active.
3. `punishment_engine.py:292-301` — PunishmentEngine blocks apply/escalate when `safe_mode.is_active()` or `hard_stop_handler.is_safe`.
4. `punishment_engine.py:584-608` — Distress >= D3 auto-suspends punishment.

### Does consent revocation halt escalation?

**NO — NO consent-aware code path exists in `src/persona/`.**

- `transition_rules.py` has no consent parameter in `TransitionContext` (line 75-86).
- `yandere_fsm.py` has no consent parameter in `can_escalate()` or `get_effective_level()`.
- `punishment_engine.py` has no consent check — the word "consent" appears only as an example violation_type string at line 270.
- `safe_mode.py` has no consent gate — it is purely distress-driven.

The only consent infrastructure in the codebase:
- `src/surveillance/consent_gate.py` — actual consent checking module.
- `src/hermes/safety_plugin.py:900` — Gate 10 (Consent gate) is **explicitly deferred**: `"gate_10_consent_deferred"`, `"Consent gate requires Redis+SQLAlchemy. Deferred enforcement."` (line 903).
- `src/gmail/commands/consent.py` — email-specific consent grant/revoke.
- `src/memory/models.py:954` — `consent_ledger` table.
- `src/memory/models.py:976` — `revocation_log` table.

**The P4-020 CHECKLIST claim ("Consent Revocation Flow Test") has NO corresponding source-level integration in the persona engine.** The external consent system exists but the persona engine does not consume it.

### Is punishment suppressed during emergency?

**YES** — at three independent code paths:
1. `punishment_engine.py:292-295` — `apply()` blocked by `safe_mode.is_active()`.
2. `punishment_engine.py:345-347` — `escalate()` blocked by safe mode.
3. `punishment_engine.py:584-608` — `check_distress_suspension()` auto-suspends at distress >= D3.
4. `punishment_engine.py:421-436` — `suspend()` pauses the clock (started_at shifted on resume).

---

## Source-vs-Claim Discrepancies

| # | CHECKLIST/PROGRESS Claim | Source Reality | Severity |
|---|---|---|---|
| 1 | P4-002: "Mood persistence (`persona.mood_states`)" | No `mood_states` table exists. Actual table is `persona.persona_state` with `state_key = "current_mood"` (line 24, 107, 149). Documented at `src/memory/models.py:414`. | MEDIUM — documentation error in checklist (wrong table name). |
| 2 | P4-001: "Content → Pleased → Disappointed → Angry → Silent" (linear chain) | FSM allows Content→Disappointed directly (skipping Pleased), Silent→Content directly (skipping Angry). Not strictly linear. | LOW — simplified label, technically non-linear FSM. |
| 3 | P4-008–013: No deprecation noted | ALL five ritual modules are **deprecated Phase 5**, scheduled removal Phase 7. Not mentioned in checklist. | MEDIUM — checklist omits deprecation status. |
| 4 | P4-015: "drift correction (>10% → alert + rollback)" | Rollback is **record-keeping only** (writes baseline hash to DriftLog). Does NOT reload or replace the actual system prompt. No prompt-reload mechanism exists. | HIGH — "correction" / "rollback" overstates what the code does. |
| 5 | P4-020: "Consent Revocation Flow Test — all escalation halted on revocation" | **NO consent-aware code exists in src/persona/** at all. The safety_plugin's consent gate (Gate 10) is **explicitly deferred** ("gate_10_consent_deferred" at safety_plugin.py:900). | CRITICAL — claimed feature does not exist in source. |
| 6 | P4-023: "Persona E2E test (conversation → mood shift → punishment → HARD STOP → neutral → reset)" | Requires verification of the actual test code (out of scope for source map). The HARD STOP → neutral code path exists (yandere_fsm.py:139-140, punishment_engine.py:292-301). | PENDING — test verification needed. |
| 7 | milestone_engine.py not claimed by any P4 item | 872-line module implementing SOUL.md §K/§M with direct importlib imports, hardcoded connection params, daemon threads, and no DI. Operates independently of the P4 persona engine. | MEDIUM — unclaimed functionality with architectural concerns. |
| 8 | `SOUL_BASELINE_HARDCODE` at drift_detector.py:62 | Hardcoded hash `b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740` with no verification against actual SystemPromptMaster. | MEDIUM — baseline may be stale. |

---

## Integration Hooks Summary (PersonaPlugin)

| Module | Hook Methods |
|---|---|
| `mood_persistence.py` | `get_session()` (line 91) |
| `transition_rules.py` | `get_state_snapshot()` (line 354), `get_valid_transitions()` static (line 368) |
| `punishment_engine.py` | `get_state_snapshot()` (line 500), `get_config()` static (line 519), `get_current_level()` (line 537) |
| `reward_engine.py` | `get_state_snapshot()` (line 417), `get_config()` static (line 430) |
| `yandere_fsm.py` | `SupportsIsSafe` protocol (line 51) for HardStopHandler integration |
| `drift_corrector.py` | References `SafeModeController` for rollback gating |

Modules without PersonaPlugin hooks: `mood_engine.py`, `drift_detector.py`, `streak_tracker.py`, `ritual_scheduler.py`, all `rituals/*`, `milestone_engine.py`.

---

## Deprecation/Supersession Map

| Module | Status | Superseded By | Removal Target |
|---|---|---|---|
| `ritual_scheduler.py` | DEPRECATED | Hermes cron (`~/.hermes/crontab.yaml`) + PersonaPlugin | Phase 7 |
| `rituals/morning.py` | DEPRECATED | Hermes cron + PersonaPlugin | Phase 7 |
| `rituals/midday.py` | DEPRECATED | Hermes cron + PersonaPlugin | Phase 7 |
| `rituals/afternoon.py` | DEPRECATED | Hermes cron + PersonaPlugin | Phase 7 |
| `rituals/evening.py` | DEPRECATED | Hermes cron + PersonaPlugin | Phase 7 |
| `rituals/midnight.py` | DEPRECATED | Hermes cron + PersonaPlugin | Phase 7 |
| All others | ACTIVE | — | — |

Note: Phase 7 (Hermes MCP migration) is listed as the removal target, but the `docs/setup-evidence/phase-4/` naming collision involves Hermes-MCP audit docs sharing the "phase-4" prefix. See `docs/setup-evidence/legacy-audit/P4/research/p4-phase4-naming-collision.md` for details.

---

## Files Referenced

- `C:/Users/faizz/guinevere/src/persona/__init__.py`
- `C:/Users/faizz/guinevere/src/persona/mood_engine.py`
- `C:/Users/faizz/guinevere/src/persona/mood_persistence.py`
- `C:/Users/faizz/guinevere/src/persona/transition_rules.py`
- `C:/Users/faizz/guinevere/src/persona/yandere_fsm.py`
- `C:/Users/faizz/guinevere/src/persona/punishment_engine.py`
- `C:/Users/faizz/guinevere/src/persona/reward_engine.py`
- `C:/Users/faizz/guinevere/src/persona/streak_tracker.py`
- `C:/Users/faizz/guinevere/src/persona/ritual_scheduler.py`
- `C:/Users/faizz/guinevere/src/persona/rituals/morning.py`
- `C:/Users/faizz/guinevere/src/persona/rituals/midday.py`
- `C:/Users/faizz/guinevere/src/persona/rituals/afternoon.py`
- `C:/Users/faizz/guinevere/src/persona/rituals/evening.py`
- `C:/Users/faizz/guinevere/src/persona/rituals/midnight.py`
- `C:/Users/faizz/guinevere/src/persona/drift_detector.py`
- `C:/Users/faizz/guinevere/src/persona/drift_corrector.py`
- `C:/Users/faizz/guinevere/src/persona/safe_mode.py`
- `C:/Users/faizz/guinevere/src/persona/milestone_engine.py`
- `C:/Users/faizz/guinevere/src/hermes/safety_plugin.py`
- `C:/Users/faizz/guinevere/src/memory/models.py`
- `C:/Users/faizz/guinevere/CHECKLIST.md`
- `C:/Users/faizz/guinevere/PROGRESS.md`

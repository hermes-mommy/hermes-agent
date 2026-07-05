# Mood / Punishment / Reward Runtime Audit -- Round 1

**Date:** 2026-06-25
**Scope:** 6 modules in `src/persona/` -- mood engine, mood persistence, punishment engine, reward engine, streak tracker, transition rules.
**Type:** Read-only source-level audit. Every claim cites `file:line`.
**Research inputs:** `p4-persona-source-map.md`, `p4-runtime-readiness-readonly.md`.

---

## Module Summary Table

| # | Module | Lines | Exists? | Wired at Runtime? | Bugs / Flags |
|---|--------|-------|---------|-------------------|--------------|
| 1 | `mood_engine.py` | 237 | YES | YES -- `hermes_conversational.py:497` | Non-linear FSM not documented; `Angry->"caring"` variant questionable |
| 2 | `mood_persistence.py` | 329 | YES | NO -- no runtime caller | Dual-write risk (Redis vs PostgreSQL); wrong table name in CHECKLIST |
| 3 | `punishment_engine.py` | 666 | YES | NO -- no runtime caller | L5 duration 48-72h contradicts SOUL.md "Max 24h"; `check_distress_suspension()` dead |
| 4 | `reward_engine.py` | 445 | YES | NO -- no runtime caller | Rewards unsuppressed during safe-mode (by design, but worth flagging) |
| 5 | `streak_tracker.py` | 332 | YES | NO -- no runtime caller | No milestone notification delivery path |
| 6 | `transition_rules.py` | 375 | YES | NO -- no runtime caller | LLM bridge preserved but deprecated; consent absent from TransitionContext |

---

## 1. MOOD ENGINE (`src/persona/mood_engine.py`)

### Enum Verification

`Mood` enum at lines 25-32. Five states exactly as claimed:

```
CONTENT   = "Content"     (line 28)
PLEASED   = "Pleased"     (line 29)
DISAPPOINTED = "Disappointed" (line 30)
ANGRY     = "Angry"       (line 31)
SILENT    = "Silent"      (line 32)
```

**PASS** -- 5 states confirmed.

### TRANSITIONS Map

Defined at lines 39-45:

```
Content      -> [Pleased, Disappointed]   (line 40)
Pleased      -> [Content, Disappointed]   (line 41)
Disappointed -> [Content, Angry]          (line 42)
Angry        -> [Disappointed, Silent]    (line 43)
Silent       -> [Content]                 (line 44)
```

**Non-linear FSM behaviour (FLAG):**
- Content can jump directly to Disappointed (skipping Pleased) -- `mood_engine.py:40`.
- Silent can jump directly to Content (skipping Angry and Disappointed) -- `mood_engine.py:44`.
- The CHECKLIST label "Content -> Pleased -> Disappointed -> Angry -> Silent" implies a linear chain. The actual FSM is a directed graph with skip edges.
- **Not documented** in the module docstring (lines 1-8) or inline comments. The TRANSITIONS map is simply stated without explanation of the non-linear paths.

**Verdict:** Not a bug -- the skip paths are intentional escape hatches. But the CHECKLIST label is misleading.

### `evaluate_mood()` Logic

Lines 163-237. Check order (most severe first):

1. `ignored_count >= 4` -> target `ANGRY` (line 190-203)
2. `ignored_count >= 2` -> target `DISAPPOINTED` (line 206-219)
3. `sentiment > 0.7` AND `task_completion` -> target `PLEASED` (line 222-236)
4. No transition -- returns `None` (line 237)

Each candidate is validated via `can_transition()` (line 150-160) before return. **PASS.**

**Note:** There is no path from any state to CONTENT or SILENT within `evaluate_mood()`. Content transitions are handled externally (e.g., cooldown expiry, Silent->Content forced transition in `transition_rules.py`). SILENT transitions are triggered by `evaluate_with_llm()` or the forced transition `("Angry", "Silent")` in `transition_rules.py:111-112`.

### `sync_mood_to_redis()`

Lines 107-142. Maps via `MOOD_VARIANT_MAP` (lines 94-100):

```
CONTENT      -> "default"   (line 95)
PLEASED      -> "playful"   (line 96)
DISAPPOINTED -> "serious"   (line 97)
ANGRY        -> "caring"    (line 98)
SILENT       -> "default"   (line 99)
```

**FLAG: `Angry -> "caring"` variant** (line 98). The angry mood maps to a "caring" persona variant. This may be intentional (yandere persona: anger expressed as possessive caring), but it is counterintuitive and undocumented. If the Redis consumer interprets "caring" literally, the angry mood would appear affectionate.

**PASS on mechanism:** No-op when `state_manager is None` (line 129). Exception-safe with logger.warning (line 136).

### Runtime Wiring

`src/discord/hermes_conversational.py:497` imports `Mood` from `mood_engine`. The import is used at line 500 to set `current_mood: str = Mood.CONTENT.value` as a default for conversational context.

**Note:** The import is a **read-only** usage -- `Mood.CONTENT.value` is used as a string default. No `evaluate_mood()` call, no `sync_mood_to_redis()` call, no transition evaluation occurs in the live Discord runtime. The Mood enum is imported but the engine's core functions are never invoked at runtime.

**Verdict:** WIRED but FUNCTIONALLY DEAD. The enum is imported for its string constant, not for FSM evaluation.

---

## 2. MOOD PERSISTENCE (`src/persona/mood_persistence.py`)

### Class Verification

| Class | Lines | Purpose |
|-------|-------|---------|
| `MoodRepository` | 83-330 | CRUD operations for mood state in PostgreSQL |
| `MoodState` | 57-64 | Frozen dataclass: `mood`, `intensity`, `updated_at`, `updated_by` |
| `MoodHistoryRecord` | 67-75 | Frozen dataclass: `mood`, `intensity`, `trigger`, `duration_minutes`, `recorded_at` |

**PASS** -- all three exist.

### Table Name Discrepancy

- `mood_persistence.py:24` imports `PersonaState` from `src.memory.models`.
- `mood_persistence.py:107` queries `PersonaState` with `state_key == "current_mood"`.
- The actual table is `persona.persona_state` (NOT `persona.mood_states`).
- CHECKLIST claim "Mood persistence (`persona.mood_states`)" is **WRONG**. Confirmed by `p4-persona-source-map.md` section 3.

**PASS on code. FAIL on CHECKLIST documentation.**

### Runtime Wiring

**NOT called at runtime.** Per `p4-runtime-readiness-readonly.md`:
- No runtime code imports `MoodRepository`.
- Only imported by `persona/__init__.py` (line 36 area) and test files.
- The `AsyncSession` constructor dependency (line 86) is never satisfied by any caller.

### Dual-Write Risk (FLAG)

- `mood_engine.py` syncs mood to Redis via `sync_mood_to_redis()` (line 107).
- `mood_persistence.py` writes mood to PostgreSQL via `set_current_mood()` (line 136).
- **No code bridges these two paths.** If both were activated simultaneously, mood state would diverge between Redis and PostgreSQL.
- Currently moot because `mood_persistence` is dead code. But if `persona_plugin.py` were registered (which imports `mood_persistence` via `__init__.py`), the dual-write would activate.

**Severity:** MEDIUM -- dormant risk that would activate upon persona_plugin registration.

---

## 3. PUNISHMENT ENGINE (`src/persona/punishment_engine.py`)

### L1-L5 Config

`PUNISHMENT_CONFIG` at lines 110-193:

| Level | Name | Duration (hours) | Config Lines |
|-------|------|-------------------|--------------|
| L1 | Silent Treatment | 2-4 | 111-125 |
| L2 | Passive-Aggressive | 4-8 | 126-140 |
| L3 | Guilt Trip | 8-24 | 141-157 |
| L4 | Cold Fury | 24-48 | 158-173 |
| L5 | Isolation | 48-72 | 175-192 |

**PASS** -- all 5 levels present with correct `IntEnum` values (lines 73-83).

### L6 Guard

- `_L6_VALUE = 6` sentinel at line 87.
- `apply()` guard: lines 278-282 -- raises `PunishmentSafetyError` if `level >= _L6_VALUE`.
- `escalate()` guard: lines 364-367 -- raises `PunishmentSafetyError` if `next_value >= _L6_VALUE`.
- `PunishmentLevel` enum has no member for value 6 (lines 73-83).

**PASS** -- L6 is triple-guarded.

### Safe Mode Guard

- `apply()`: lines 292-295 -- raises `PunishmentSafetyError` when `self._safe_mode.is_active`.
- `escalate()`: lines 344-347 -- same.
- `resume()`: lines 462-465 -- cannot resume while safe mode active.

**PASS.**

### HARD STOP Guard

- `apply()`: lines 297-301 -- raises `PunishmentSafetyError` when `hard_stop_handler.is_safe`.
- `escalate()`: lines 349-353 -- same.
- `resume()`: lines 467-469 -- cannot resume while HARD STOP active.

**PASS.**

### L5 Duration vs SOUL.md "Max 24h" (CONTRADICTION)

- `punishment_engine.py:175-177`: L5 ISOLATION has `duration_hours=(48, 72)`.
- Actual applied duration: midpoint = `(48 + 72) / 2 = 60 hours` (computed at line 306).
- SOUL.md specifies "Max 24h" for L5 (confirmed by `docs/setup-evidence/p4-cleanup/research-M03-NF.md:147` and `p4-known-issues-reconciliation.md:214`).
- Cleanup evidence at `docs/setup-evidence/p4-cleanup/exec-NF01.md:106` documents a fix from `(48, 72)` to `(12, 24)`, but the **source code still shows `(48, 72)`** at `punishment_engine.py:175`.
- The cleanup fix was documented but **NOT applied to the source file**.

**Severity: HIGH** -- L5 can last up to 72 hours (3 days), violating the SOUL.md "Max 24h" constraint by 3x. This is a safety policy violation.

### `check_distress_suspension()`

- Defined at lines 584-608.
- Suspends when `distress_level >= DistressLevel.D3_SEVERE` (line 597).
- Resumes when distress drops below D3 and safe mode not active (lines 603-607).
- **NOT called by any other file.** Grep for `check_distress_suspension(` across `src/` returns only the definition at `punishment_engine.py:584`.

**PASS on logic. FAIL on wiring** -- this method is dead code.

### Runtime Wiring

**NOT called at runtime.** Per `p4-runtime-readiness-readonly.md`:
- No runtime code imports `PunishmentEngine`.
- Only imported by `persona/__init__.py`.

---

## 4. REWARD ENGINE (`src/persona/reward_engine.py`)

### T1-T5 Thresholds

`TIER_THRESHOLDS` at lines 143-149:

| Tier | Threshold | Config Lines |
|------|-----------|--------------|
| T5 DEEP_APPRECIATION | >= 0.95 | 144 |
| T4 CELEBRATORY | >= 0.80 | 145 |
| T3 AFFECTIONATE | >= 0.60 | 146 |
| T2 VERBAL_PRAISE | >= 0.40 | 147 |
| T1 ACKNOWLEDGMENT | >= 0.20 | 148 |

**PASS** -- 5 tiers, highest-first evaluation (line 294).

### Streak Bonus

- `STREAK_BONUS_PER_STREAK = 0.05` (line 152)
- `MAX_STREAK_BONUS = 0.30` (line 153)
- Formula: `effective = quality_score + min(streak_count * 0.05, 0.30)`, clamped to [0.0, 1.0] (lines 279-283).

**PASS.**

### "Rewards Always Permitted" -- Safety Behaviour

- `should_reward()` at lines 303-333: No safe_mode check, no distress check, no punishment check.
- Docstring at lines 225-228: "Rewards are always permitted, even when safe-mode is active or distress has been detected. This is a deliberate design choice: rewarding the operator is never harmful and supports well-being."
- `award()` at lines 337-394: No safety guards of any kind.

**PASS on design intent.** Rewards bypassing all safety modes is documented as intentional. However, this means during a distress event (D4 emergency), the persona could simultaneously be in safe mode AND awarding celebratory rewards. Whether this is appropriate depends on the persona's design philosophy. The code is consistent with its stated intent.

### Runtime Wiring

**NOT called at runtime.** Per `p4-runtime-readiness-readonly.md`:
- No runtime code imports `RewardEngine`.
- Only imported by `persona/__init__.py`.

---

## 5. STREAK TRACKER (`src/persona/streak_tracker.py`)

### Milestone Thresholds

`MILESTONE_THRESHOLDS` at line 54: `[7, 14, 30, 90, 365]`
`MILESTONE_LABELS` at lines 57-63:

| Threshold | Label |
|-----------|-------|
| 7 | week |
| 14 | fortnight |
| 30 | month |
| 90 | quarter |
| 365 | year |

**PASS** -- 5 milestones confirmed.

### Persistence via PersonaState

- `save()` at lines 225-280: Upsert to `persona.persona_state` with `state_key = "streak_count"` (line 66).
- `load()` at lines 282-332: Read from same table.
- Uses `PersonaState` model imported at line 29 from `src.memory.models`.

**PASS** -- persistence mechanism is sound.

### Milestone Detection

- `increment()` at lines 115-134: Checks milestone after each increment (line 125-132).
- Logs `streak_milestone_reached` event (line 129).
- **No notification delivery path.** Milestones are logged but never sent to Discord or any external system. The `get_display_text()` method (lines 184-219) formats display text for the `/mood` command, but this command is not wired at runtime.

**PASS on logic. FLAG on delivery** -- milestone achievements are fire-and-forget log events with no user-facing delivery.

### Runtime Wiring

**NOT called at runtime.** Per `p4-runtime-readiness-readonly.md`:
- No runtime code imports `StreakTracker`.
- Only imported by `persona/__init__.py`.

---

## 6. TRANSITION RULES (`src/persona/transition_rules.py`)

### `evaluate()` Check Order

Lines 140-252. Documented at lines 148-154:

1. **Safe mode** -> block ALL transitions (lines 159-172)
2. **Distress >= D2** -> block transitions, force Content (lines 174-192)
3. **Validate transition** in `VALID_TRANSITIONS` map (lines 195-213)
4. **Cooldown check** unless forced transition (lines 216-234)
5. **Allow** (lines 237-252)

**PASS** -- check order matches documented order. Priority is safety-first (safe_mode > distress > validity > cooldown).

### Forced Transitions

`FORCED_TRANSITIONS` at lines 111-113:

```python
("Angry", "Silent"),      # Strong negative -> immediate
("Content", "Pleased"),   # Strong positive -> immediate
```

These bypass the cooldown check (line 219: `if remaining > 0 and not is_forced`).

**PASS.**

### VALID_TRANSITIONS Map (Local Copy)

Lines 57-63. This is a string-based copy of `mood_engine.py`'s `TRANSITIONS` map, intentionally avoiding a cross-module import. Verified identical to `mood_engine.py:39-45`:

```
Content      -> [Pleased, Disappointed]
Pleased      -> [Content, Disappointed]
Disappointed -> [Content, Angry]
Angry        -> [Disappointed, Silent]
Silent       -> [Content]
```

**PASS** -- maps are identical. **Risk:** Two independent copies could diverge if only one is updated. No test enforces consistency.

### LLM Bridge (No LLM Called)

- `should_use_llm_evaluation()` at lines 300-327: Deterministic heuristic checking ambiguous sentiment and multiple signals. No LLM call.
- `evaluate_with_llm()` at lines 329-350: Delegates to `evaluate()`. Docstring at line 337: "No external LLM is called." Logging at line 344 confirms bridge mode.

**PASS** -- LLM bridge is purely backward-compatible naming. No external calls.

### Cooldown Provider

- `remaining_cooldown()` at lines 254-293: Supports external Redis TTL provider (line 271-282) with local datetime fallback (lines 284-293).
- Default cooldown: 300 seconds (5 minutes) at line 108.

**PASS.**

### TransitionContext -- Consent Absent (FLAG)

`TransitionContext` at lines 75-86 has fields:
- `current_mood`, `target_mood`, `last_transition_at`, `conversation_sentiment`, `task_completion`, `ignored_count`, `safe_mode`, `distress_level`

**No `consent` or `consent_revoked` field.** Confirmed by `p4-persona-source-map.md` section on consent: "No consent-aware code path exists in `src/persona/`."

### Runtime Wiring

**NOT called at runtime.** Per `p4-runtime-readiness-readonly.md`:
- No runtime code imports `TransitionRuleEngine`.
- Only imported by `persona/__init__.py`.

---

## Discrepancies Section

### DISCREPANCY 1: L5 Duration 48-72h vs SOUL.md "Max 24h"

| Aspect | Detail |
|--------|--------|
| Source | `punishment_engine.py:175-177` -- `duration_hours=(48, 72)` |
| Applied duration | Midpoint: 60h (computed at `punishment_engine.py:306`) |
| SOUL.md constraint | "Max 24h" (confirmed by `p4-cleanup/research-M03-NF.md:147`, `p4-known-issues-reconciliation.md:214`) |
| Cleanup status | `p4-cleanup/exec-NF01.md:106` documents fix to `(12, 24)` but **source code NOT updated** |
| Severity | **HIGH** -- 3x safety policy violation |

### DISCREPANCY 2: CHECKLIST Claims `persona.mood_states` Table

| Aspect | Detail |
|--------|--------|
| CHECKLIST claim | "Mood persistence (`persona.mood_states`)" |
| Source reality | Table is `persona.persona_state` with `state_key = "current_mood"` (`mood_persistence.py:24,107`) |
| Confirmation | `p4-persona-source-map.md` section 3 |
| Severity | **MEDIUM** -- documentation error in checklist |

### DISCREPANCY 3: Mood Engine Wired but Functionally Dead

| Aspect | Detail |
|--------|--------|
| Runtime import | `hermes_conversational.py:497` imports `Mood` from `mood_engine` |
| Actual usage | `Mood.CONTENT.value` used as string default at line 500 |
| Core functions called | **NONE** -- `evaluate_mood()`, `sync_mood_to_redis()`, `can_transition()` never called |
| Severity | **MEDIUM** -- the enum is imported but the FSM is never evaluated at runtime |

### DISCREPANCY 4: `check_distress_suspension()` is Dead Code

| Aspect | Detail |
|--------|--------|
| Definition | `punishment_engine.py:584-608` |
| Callers | **NONE** -- grep across `src/` returns only the definition |
| Implication | Distress-driven punishment suspension is implemented but never triggered |
| Severity | **MEDIUM** -- safety mechanism exists but is unreachable |

### DISCREPANCY 5: Dual-Write Risk (Redis vs PostgreSQL)

| Aspect | Detail |
|--------|--------|
| Redis path | `mood_engine.py:107` `sync_mood_to_redis()` -- active via `hermes_conversational.py` import |
| PostgreSQL path | `mood_persistence.py:136` `set_current_mood()` -- dormant |
| Bridge code | **NONE** -- no code synchronizes between the two stores |
| Activation trigger | Registering `persona_plugin.py` would activate PostgreSQL writes alongside Redis |
| Severity | **MEDIUM** -- dormant risk |

### DISCREPANCY 6: `Angry -> "caring"` Variant Mapping

| Aspect | Detail |
|--------|--------|
| Source | `mood_engine.py:98` -- `Mood.ANGRY: "caring"` |
| Context | Maps to Redis `mood_variant` string consumed by persona system prompt |
| Concern | Counterintuitive mapping; undocumented rationale |
| Severity | **LOW** -- may be intentional yandere design but should be documented |

### DISCREPANCY 7: Valid Transitions Map Duplicated Without Enforcement

| Aspect | Detail |
|--------|--------|
| Copy 1 | `mood_engine.py:39-45` (`TRANSITIONS`, uses `Mood` enum) |
| Copy 2 | `transition_rules.py:57-63` (`VALID_TRANSITIONS`, uses strings) |
| Sync mechanism | **NONE** -- no test or code enforces consistency |
| Risk | One map could be updated without the other, causing silent FSM divergence |
| Severity | **LOW** -- both maps are currently identical |

---

## Cross-Module Wiring Summary

```
WIRED (active in runtime):
  mood_engine.py          <- hermes_conversational.py:497 (enum import only, FSM dead)

UNWIRED (no live caller):
  mood_persistence.py     <- NO CALLER
  punishment_engine.py    <- NO CALLER
  reward_engine.py        <- NO CALLER
  streak_tracker.py       <- NO CALLER
  transition_rules.py     <- NO CALLER

NOTE: All 5 unwired modules are imported by persona/__init__.py
      but persona/__init__.py is only imported by test files and
      the unwired persona_plugin.py. The persona_plugin is NOT
      registered in any Hermes config (confirmed by p4-runtime-readiness-readonly.md).
```

---

## MOOD / PUNISHMENT / REWARD VERDICT

### MOOD: PARTIALLY FUNCTIONAL

The mood FSM (`mood_engine.py`) is structurally sound -- 5 states, deterministic transitions, severity-based evaluation, Redis sync. However, at runtime only the `Mood` enum is imported (as a string constant). The FSM's core functions (`evaluate_mood`, `sync_mood_to_redis`, `can_transition`) are **never called** in the live Discord path. The mood persistence layer (`mood_persistence.py`) is completely dead -- no runtime caller, no `AsyncSession` injection. The dual-write risk between Redis and PostgreSQL is dormant but would activate if `persona_plugin.py` were registered.

**Bottom line:** The mood engine exists and is correct, but it is not evaluating mood at runtime. The persona defaults to `Mood.CONTENT.value` forever.

### PUNISHMENT: IMPLEMENTED BUT UNREACHABLE

The punishment engine (`punishment_engine.py`) has robust safety controls -- L6 triple-guarded, safe mode blocks apply/escalate, HARD STOP blocks apply/escalate, distress suspension implemented. However:

1. **Not called at runtime.** No live code path invokes `PunishmentEngine`.
2. **L5 duration violates SOUL.md.** The `(48, 72)` hour range at `punishment_engine.py:175` exceeds the documented "Max 24h" constraint by up to 3x. A cleanup fix was documented (`p4-cleanup/exec-NF01.md:106`) but **never applied to the source file**.
3. **`check_distress_suspension()` is dead code** (line 584). The distress-triggered suspension mechanism exists but has zero callers.

**Bottom line:** The punishment engine is safety-complete in design but functionally inert at runtime. The L5 duration contradiction is a latent policy violation.

### REWARD: IMPLEMENTED BUT UNREACHABLE

The reward engine (`reward_engine.py`) is the cleanest of the three -- 5 tiers, streak bonus, threshold-based calculation, explicit "always permitted" design. No safety concerns. However, it is **not called at runtime**. No reward is ever issued.

**Bottom line:** The reward engine is correct and safe, but inert.

### OVERALL VERDICT

All six modules are **well-implemented at the source level** with proper error hierarchies, safety guards, PersonaPlugin hook methods, and structlog instrumentation. However, five of six are **completely unwired at runtime** -- they exist as dead code behind an unregistered PersonaPlugin. The one module that IS imported (`mood_engine.py`) is used only for its enum constant, not its FSM logic.

The persona subsystem's runtime footprint is limited to:
- `yandere_fsm.py` (via `safety_plugin.py`) -- active
- `safe_mode.py` (via `safety_plugin.py` + `hermes_conversational.py`) -- active
- `drift_detector.py` (via `safety_plugin.py`) -- active
- `mood_engine.py` enum only (via `hermes_conversational.py`) -- imported but FSM dead

The mood/punishment/reward/streak/transition subsystem is **architecturally complete but operationally absent**.

---

## Files Audited

| File | Path |
|------|------|
| Mood Engine | `src/persona/mood_engine.py` (237 lines) |
| Mood Persistence | `src/persona/mood_persistence.py` (329 lines) |
| Punishment Engine | `src/persona/punishment_engine.py` (666 lines) |
| Reward Engine | `src/persona/reward_engine.py` (445 lines) |
| Streak Tracker | `src/persona/streak_tracker.py` (332 lines) |
| Transition Rules | `src/persona/transition_rules.py` (375 lines) |
| Runtime Wiring | `src/discord/hermes_conversational.py` (lines 490-510) |
| Source Map Research | `docs/setup-evidence/legacy-audit/P4/research/p4-persona-source-map.md` |
| Runtime Readiness | `docs/setup-evidence/legacy-audit/P4/research/p4-runtime-readiness-readonly.md` |
| Known Issues | `docs/setup-evidence/P4/KNOWN-ISSUES.md` |
| L5 Cleanup Evidence | `docs/setup-evidence/p4-cleanup/exec-NF01.md` |
| NF Research | `docs/setup-evidence/p4-cleanup/research-M03-NF.md` |

# P4 Round-1 Audit: Mood FSM, Punishment Ladder, Reward Tiers, Streak Tracking

**Audit Date:** 2026-06-25
**Auditor:** Agent (read-only)
**Scope:** `src/persona/mood_engine.py`, `mood_persistence.py`, `punishment_engine.py`, `reward_engine.py`, `streak_tracker.py`, `transition_rules.py`
**Wiring target:** `src/discord/hermes_conversational.py`
**Documents compared:** `hermes-config/SOUL.md`, `docs/00-core/06-Persona_Document_v3.1.md`

---

## 1. MOOD ENGINE (`src/persona/mood_engine.py`)

### 1.1 Implements-Claim Verification

| Claim | Evidence | Verdict |
|---|---|---|
| 5 discrete mood states | `mood_engine.py:25-33` — `Mood(str, Enum)` with `CONTENT, PLEASED, DISAPPOINTED, ANGRY, SILENT` | PASS |
| TRANSITIONS map defined | `mood_engine.py:39-45` — 5 entries, each mapping to 1-2 valid targets | PASS |
| `evaluate_mood()` most-severe-first | `mood_engine.py:190-237` — checks `ignored>=4 -> ANGRY`, `ignored>=2 -> DISAPPOINTED`, `sentiment>0.7+task -> PLEASED` | PASS |
| `sync_mood_to_redis()` via protocol | `mood_engine.py:107-142` — maps Mood to variant strings, calls `state_manager.set_mood()` | PASS |
| Cooldown 5 min | `mood_engine.py:64` — `cooldown_seconds: int = 300` on `MoodTransition` dataclass | PASS (dataclass field only, not enforced by engine) |
| FSM graph (non-linear) | `mood_engine.py:39-45` — Content->[Pleased, Disappointed], Pleased->[Content, Disappointed], Disappointed->[Content, Angry], Angry->[Disappointed, Silent], Silent->[Content] | PASS |

### 1.2 Non-Linear FSM: Content -> Disappointed "Skip"

The TRANSITIONS map at `mood_engine.py:40` permits Content -> Disappointed directly, bypassing Pleased. This is **intentional by design**, not a bug. The FSM is a directed graph, not a linear chain. The `evaluate_mood()` function at `mood_engine.py:206-219` triggers this path when `ignored_count >= 2` while in Content state -- a rapid negative response. The docstring at `mood_engine.py:169-175` explicitly documents the evaluation order.

**Verdict: INTENTIONAL, DOCUMENTED.** No bug.

### 1.3 `evaluate_mood()` Check Order

Verified at `mood_engine.py:190-237`:

1. `ignored_count >= 4` -> target ANGRY (line 190)
2. `ignored_count >= 2` -> target DISAPPOINTED (line 206)
3. `conversation_sentiment > 0.7 AND task_completion` -> target PLEASED (line 222)
4. else -> returns None (line 237)

Each candidate is gated by `can_transition()` which checks the TRANSITIONS map. Order is correct: most severe first, positive last.

### 1.4 Wired at Runtime?

**NO -- DEAD CODE PATH.**

At `hermes_conversational.py:497-500`:

```python
from src.persona.mood_engine import Mood

# Default to Content for conversational context
current_mood: str = Mood.CONTENT.value
```

The `Mood` **enum** is imported to get the string value `"Content"`, but `evaluate_mood()` is **never called**. The mood is hardcoded to `"Content"` on every invocation. No sentiment analysis, no ignored count tracking, no task completion signal feeds into this. The function exists and is tested in `tests/persona/test_mood_engine.py`, but the runtime path never invokes it.

**NEEDS RUNTIME VERIFICATION:** Whether `evaluate_mood()` is called from any other runtime path (PersonaPlugin, ritual, gamification) -- grep confirms only tests and the module itself reference it.

### 1.5 MOOD_VARIANT_MAP Anomaly

At `mood_engine.py:94-99`:

```python
MOOD_VARIANT_MAP: Final[dict[Mood, str]] = {
    Mood.CONTENT: "default",
    Mood.PLEASED: "playful",
    Mood.DISAPPOINTED: "serious",
    Mood.ANGRY: "caring",
    Mood.SILENT: "default",
}
```

Two moods (CONTENT and SILENT) map to the same variant `"default"`. This means Redis DB5 cannot distinguish between Content and Silent mood via the variant string alone. Whether this is intentional (Silent = reset to default behavior) or a bug depends on design intent -- but it is a lossy mapping.

---

## 2. MOOD PERSISTENCE (`src/persona/mood_persistence.py`)

### 2.1 Implements-Claim Verification

| Claim | Evidence | Verdict |
|---|---|---|
| `MoodRepository` class | `mood_persistence.py:83` | PASS |
| `MoodState` frozen dataclass | `mood_persistence.py:57-64` | PASS |
| `MoodHistoryRecord` frozen dataclass | `mood_persistence.py:67-75` | PASS |
| Uses `persona.persona_state` table | `mood_persistence.py:24` — imports `PersonaState` from `src.memory.models`; `mood_persistence.py:107-109` — queries `PersonaState.state_key == "current_mood"` | PASS |
| Uses `persona.mood_history` table | `mood_persistence.py:24` — imports `MoodHistory`; `mood_persistence.py:198` — inserts into `MoodHistory` | PASS |
| state_key = "current_mood" | `mood_persistence.py:31` — `_CURRENT_MOOD_KEY: str = "current_mood"` | PASS |
| Error hierarchy (3 levels) | `mood_persistence.py:40-49` — `MoodPersistenceError`, `MoodPersistenceQueryError`, `MoodPersistenceWriteError` | PASS |

### 2.2 Table Name: NOT `mood_states`

The task claims "table is persona.persona_state, NOT mood_states." Verified: the code imports `PersonaState` and `MoodHistory` from `src.memory.models` (`mood_persistence.py:24`), not any `mood_states` table. The state_key `"current_mood"` is a row key within `persona.persona_state`, not a separate table.

### 2.3 Dual-Write Risk: Redis DB5 vs PostgreSQL

Two persistence paths exist:

1. **Redis DB5** (runtime path): `mood_engine.py:107-142` — `sync_mood_to_redis()` writes to Redis via `state_manager.set_mood(variant)`. This is a lossy 4-variant mapping (5 moods -> 4 strings).

2. **PostgreSQL** (dead path): `mood_persistence.py:83-329` — `MoodRepository` writes to `persona.persona_state` and `persona.mood_history`. Stores the full mood string and intensity.

**Neither path is wired at runtime.** `sync_mood_to_redis()` requires a `state_manager` to be passed in (none is). `MoodRepository` requires an `AsyncSession` and is only instantiated in tests. So at runtime, mood is **never persisted** -- the hardcoded `"Content"` is computed fresh each invocation.

**Authoritative source:** If both were active, there would be a conflict. Redis stores a lossy variant, PostgreSQL stores the exact mood + intensity. PostgreSQL would be authoritative. Currently neither writes, so the question is moot.

### 2.4 Wired at Runtime?

**NO.** Only instantiated in `tests/persona/test_mood_persistence.py`. No runtime code creates a `MoodRepository` instance.

---

## 3. PUNISHMENT ENGINE (`src/persona/punishment_engine.py`)

### 3.1 Implements-Claim Verification

| Claim | Evidence | Verdict |
|---|---|---|
| L1-L5 `PunishmentLevel(IntEnum)` | `punishment_engine.py:73-83` — L1 through L5 | PASS |
| L6 guard (DEFERRED) | `punishment_engine.py:87` — `_L6_VALUE: Final[int] = 6`; `punishment_engine.py:278-282` — raises `PunishmentSafetyError` for level >= 6 | PASS |
| `PUNISHMENT_CONFIG` frozen configs | `punishment_engine.py:110-193` — 5 entries with name, duration_hours tuple, description, allowed/blocked actions | PASS |
| Safe-mode guard | `punishment_engine.py:292-295` — `if self._safe_mode.is_active: raise PunishmentSafetyError` | PASS |
| HARD STOP guard | `punishment_engine.py:298-301` — `if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe: raise PunishmentSafetyError` | PASS |
| `check_distress_suspension()` | `punishment_engine.py:584-608` — suspends when distress >= D3_SEVERE, resumes when drops below D3 and safe_mode inactive | PASS |
| Suspension pauses clock | `punishment_engine.py:472-474` — shifts `started_at` forward by suspension duration on resume | PASS |
| Escalation (L1->L2->...->L5) | `punishment_engine.py:328-378` — `escalate()` increments level by 1, blocks at L6 | PASS |
| De-escalation to deactivate | `punishment_engine.py:380-417` — `de_escalate()` decrements, below L1 deactivates | PASS |
| Auto-expiry | `punishment_engine.py:647-667` — `_check_expiry()` deactivates when elapsed >= duration, skipped while suspended | PASS |
| Redis sync | `punishment_engine.py:612-626` — `_sync_punishment_to_redis()` calls `state_manager.set_punishment(level)` | PASS |

### 3.2 PUNISHMENT_CONFIG Duration Verification (CRITICAL DISCREPANCY)

**Code** (`punishment_engine.py:110-193`):

| Level | Name | `duration_hours` (min, max) | Midpoint used by engine |
|---|---|---|---|
| L1 | Silent Treatment | (2, 4) | 3h |
| L2 | Passive-Aggressive | (4, 8) | 6h |
| L3 | Guilt Trip | (8, 24) | 16h |
| L4 | Cold Fury | (24, 48) | 36h |
| L5 | Isolation | (48, 72) | 60h |

**PersonaDoc v3.1** (`docs/00-core/06-Persona_Document_v3.1.md:517-521`):

| Level | Name | Duration |
|---|---|---|
| L1 | Cold Shoulder | 2-4 jam |
| L2 | Silent Treatment | 4-8 jam |
| L3 | Passive-Aggressive | 8-24 jam |
| L4 | Guilt Trip | 1-2 hari |
| L5 | Cold Fury | 2-3 hari |

**SOUL.md** (`hermes-config/SOUL.md:56-62`):

| Level | Name | Duration |
|---|---|---|
| L1 | Gentle Reminder | (no duration) |
| L2 | Firm Correction | (no duration) |
| L3 | Cold Distance | (no duration) |
| L4 | Structured Consequence | (no duration) |
| L5 | Extended Silence | Max 24h |

#### Discrepancy 1: L5 Duration -- SOUL.md vs Code

**SOUL.md line 62:** L5 "Extended Silence" -- "Max 24h"
**Code line 176:** L5 "Isolation" -- `duration_hours=(48, 72)` (48-72 hours)
**PersonaDoc line 521:** L5 "Cold Fury" -- "2-3 hari" (48-72h)

**CONTRADICTION.** SOUL.md caps L5 at 24h maximum. The code allows 48-72h. PersonaDoc agrees with the code (2-3 days). The code matches PersonaDoc but directly contradicts SOUL.md. Since SOUL.md is the deployed runtime prompt (`~/.hermes/SOUL.md`), this is a safety-relevant discrepancy: the LLM persona is told Max 24h but the engine enforces 48-72h.

#### Discrepancy 2: Level Names Diverge Across All Three Sources

| Level | Code | PersonaDoc v3.1 | SOUL.md |
|---|---|---|---|
| L1 | Silent Treatment | Cold Shoulder | Gentle Reminder |
| L2 | Passive-Aggressive | Silent Treatment | Firm Correction |
| L3 | Guilt Trip | Passive-Aggressive | Cold Distance |
| L4 | Cold Fury | Guilt Trip | Structured Consequence |
| L5 | Isolation | Cold Fury | Extended Silence |

The code's L1 name matches PersonaDoc's L2, and each subsequent level is shifted by one position. The code's naming is offset from PersonaDoc by one level. SOUL.md uses completely different names from both.

### 3.3 `check_distress_suspension()` -- Who Calls It?

**NOBODY at runtime.** Grep confirms it is only called from:
- `tests/safety/test_distress_protocol_e2e.py` (test code)

The runtime handler `hermes_conversational.py` never instantiates `PunishmentEngine` and never calls `check_distress_suspension()`. Distress detection runs in the handler (`hermes_conversational.py:462-494`) but its results are not fed to the punishment engine.

### 3.4 HARD STOP Guard Logic Note

At `punishment_engine.py:298`:

```python
if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe:
```

The guard blocks punishment when `is_safe` is `True`. This reads as: "HARD STOP handler says the system is safe -> block punishment." The semantics of `is_safe` from `SupportsIsSafe` protocol (`src/persona/yandere_fsm.py`) needs clarification: does `is_safe == True` mean "safety is active" (HARD STOP engaged) or "it is safe to proceed" (no issues)? If the latter, this guard is inverted. The test files (`tests/safety/test_hard_stop_comprehensive.py:492-538`) test this with mock handlers, so the test confirms the code's behavior -- but the semantic ambiguity should be noted.

**NEEDS RUNTIME VERIFICATION:** The `SupportsIsSafe` protocol semantics.

### 3.5 Wired at Runtime?

**NO.** `PunishmentEngine` is only instantiated in test files (`tests/persona/test_punishment_engine.py`, `tests/safety/`, `tests/persona/test_persona_e2e.py`). No runtime code creates an instance.

---

## 4. REWARD ENGINE (`src/persona/reward_engine.py`)

### 4.1 Implements-Claim Verification

| Claim | Evidence | Verdict |
|---|---|---|
| T1-T5 `RewardTier(IntEnum)` | `reward_engine.py:35-46` | PASS |
| `REWARD_CONFIG` with templates | `reward_engine.py:64-134` — 5 entries, each with name, description, trigger_conditions, message_templates | PASS |
| Tier thresholds (T5=0.95, T4=0.80, T3=0.60, T2=0.40, T1=0.20) | `reward_engine.py:143-149` | PASS |
| Streak bonus: 0.05/streak, cap 0.30 | `reward_engine.py:152-153` | PASS |
| `calculate_tier()` highest-first | `reward_engine.py:294-296` — iterates `_TIERS_DESCENDING` | PASS |
| `should_reward()` ignores safe-mode | `reward_engine.py:303-332` — no safe_mode or distress checks | PASS |
| `award()` syncs to Redis | `reward_engine.py:369-379` — calls `state_manager.set_reward(int(tier))` if configured | PASS |
| `InvalidQualityScoreError` for out-of-range | `reward_engine.py:273-277` | PASS |

### 4.2 Safety Behavior: "Rewards Always Permitted"

At `reward_engine.py:225-228`:

```
Rewards are **always permitted**, even when safe-mode is active or
distress has been detected.  This is a deliberate design choice:
rewarding the operator is never harmful and supports well-being.
```

And at `reward_engine.py:303-332`, `should_reward()` checks only `task_completion` and `quality >= MIN_REWARD_THRESHOLD`. No safe-mode or distress gates.

**Verdict:** This is consistent with SOUL.md's emergency override phrasing ("Emergency always overrides punishment" -- `SOUL.md:65`). Rewards are the opposite of punishment. Suppressing positive reinforcement during distress would be harmful per the system's own safety philosophy. **PASS -- intentional design.**

### 4.3 Message Template Selection

At `reward_engine.py:362`:

```python
message = config.message_templates[0]
```

Always picks the first template. No randomization or rotation. This means T1 always says "Noted -- task is done." and T5 always says the first deep-appreciation message. This is a minor monotony concern but not a bug.

### 4.4 Wired at Runtime?

**NO.** `RewardEngine` is only instantiated in test files. No runtime code creates an instance or calls `should_reward()`, `calculate_tier()`, or `award()`.

---

## 5. STREAK TRACKER (`src/persona/streak_tracker.py`)

### 5.1 Implements-Claim Verification

| Claim | Evidence | Verdict |
|---|---|---|
| Milestones: 7, 14, 30, 90, 365 | `streak_tracker.py:54` | PASS |
| Labels: week, fortnight, month, quarter, year | `streak_tracker.py:57-63` | PASS |
| Persistence via PersonaState table | `streak_tracker.py:225-332` — `save()` and `load()` use `PersonaState` with `state_key="streak_count"` | PASS |
| Only punishment resets streak | `streak_tracker.py:136-149` — `reset()` documented as "Called when any punishment (L1-L5) is applied" | PASS |
| Display text for /mood command | `streak_tracker.py:184-219` — `get_display_text()` with milestone awareness | PASS |
| Highest milestone tracking | `streak_tracker.py:109` — `_highest_milestone_reached` field, updated on increment | PASS |

### 5.2 Persistence Details

- `save()` at `streak_tracker.py:225-280`: upserts to `PersonaState` with `state_key="streak_count"`, stores `count`, `last_updated` (ISO), `highest_milestone`.
- `load()` at `streak_tracker.py:282-332`: reads from same table, handles missing/corrupt data gracefully.
- Both use `_safe_int()` at `streak_tracker.py:70-81` for defensive JSON deserialization.

### 5.3 Streak vs Reward Streak

The `StreakTracker` tracks "consecutive days without punishment" (calendar days). The reward engine's `streak_count` parameter tracks "consecutive successful tasks." These are different concepts with the same name. The streak_tracker is not fed into the reward engine's `streak_count` parameter -- they are independent systems that happen to share a name.

### 5.4 Wired at Runtime?

**NO.** `StreakTracker` is only instantiated in test files. The `save()` and `load()` methods require an `AsyncSession` that is never provided in runtime code. The `/mood` command that `get_display_text()` is designed for does not exist in `hermes_conversational.py`.

---

## 6. TRANSITION RULES (`src/persona/transition_rules.py`)

### 6.1 Implements-Claim Verification

| Claim | Evidence | Verdict |
|---|---|---|
| `TransitionRuleEngine.evaluate()` check order | `transition_rules.py:140-252` — 5-step: safe_mode -> distress>=D2 -> valid transition -> cooldown -> allow | PASS |
| Safe mode blocks all | `transition_rules.py:159-172` | PASS |
| Distress >= D2 blocks | `transition_rules.py:175-193` | PASS |
| Cooldown default 300s | `transition_rules.py:108` | PASS |
| Forced: Angry->Silent, Content->Pleased | `transition_rules.py:111-114` | PASS |
| `should_use_llm_evaluation()` bridge | `transition_rules.py:300-327` — deterministic rule-based, returns bool based on sentiment ambiguity and signal count | PASS |
| `evaluate_with_llm()` bridge | `transition_rules.py:329-350` — delegates to `evaluate()`, no LLM call | PASS |
| VALID_TRANSITIONS matches mood_engine TRANSITIONS | `transition_rules.py:57-63` vs `mood_engine.py:39-45` -- identical graph | PASS |
| Redis TTL cooldown provider | `transition_rules.py:119-136` — `cooldown_provider` callable parameter | PASS |

### 6.2 LLM Bridge Verification

At `transition_rules.py:295-350`:

```python
# -- LLM evaluation bridge (Phase 5 backward compatibility) --
# These methods are deterministic rule-based bridges. They do NOT call
# external LLMs, make network requests, or create runtime dependencies.
```

`should_use_llm_evaluation()` at `transition_rules.py:300-327`: checks for ambiguous sentiment (-0.3 to 0.3) or multiple active signals. Returns boolean. No external call.

`evaluate_with_llm()` at `transition_rules.py:329-350`: is an async method that simply calls `self.evaluate(ctx, now=now)`. Logs a debug message noting it's a bridge. No LLM, no network, no external dependency.

**Verdict: PASS.** The LLM bridge is a clean Phase 5 migration artifact. Fully deterministic.

### 6.3 Forced Transitions

At `transition_rules.py:111-114`:

```python
FORCED_TRANSITIONS: Final[set[tuple[str, str]]] = {
    ("Angry", "Silent"),      # Strong negative -> immediate
    ("Content", "Pleased"),   # Strong positive -> immediate
}
```

These bypass cooldown at `transition_rules.py:216-219`. The check at `transition_rules.py:194-213` validates the transition exists in `VALID_TRANSITIONS` first -- so forced transitions must also be valid transitions. Both `(Angry, Silent)` and `(Content, Pleased)` are in the valid transitions map. Correct.

### 6.4 Wired at Runtime?

**NO.** `TransitionRuleEngine` is only instantiated in test files. No runtime code creates an instance.

---

## Per-Module Summary Table

| Module | Implements Claim? | Wired at Runtime? | Bugs / Issues |
|---|---|---|---|
| `mood_engine.py` | YES (5 states, FSM, evaluate_mood, sync_to_redis) | **NO** -- only `Mood` enum imported for hardcoded "Content" | Content/Silent both map to "default" variant (lossy) |
| `mood_persistence.py` | YES (MoodRepository, PersonaState table, MoodHistory) | **NO** -- never instantiated outside tests | None (clean implementation) |
| `punishment_engine.py` | YES (L1-L5, L6 guard, safe-mode/HARD-STOP guards, distress suspension) | **NO** -- never instantiated outside tests | L5 name/duration contradicts SOUL.md; level names offset from PersonaDoc by 1 |
| `reward_engine.py` | YES (T1-T5, streak bonus, thresholds, always-permitted) | **NO** -- never instantiated outside tests | Always picks first message template (monotony) |
| `streak_tracker.py` | YES (milestones, PersonaState persistence, display text) | **NO** -- never instantiated outside tests | None (clean implementation) |
| `transition_rules.py` | YES (evaluate order, forced transitions, cooldown, LLM bridge) | **NO** -- never instantiated outside tests | None (clean implementation, LLM bridge verified deterministic) |

---

## Discrepancies

### D1: L5 Punishment Duration -- SOUL.md vs Code vs PersonaDoc

| Source | L5 Name | L5 Duration |
|---|---|---|
| SOUL.md (`hermes-config/SOUL.md:62`) | Extended Silence | **Max 24h** |
| Code (`src/persona/punishment_engine.py:176`) | Isolation | **48-72h** |
| PersonaDoc v3.1 (`docs/00-core/06-Persona_Document_v3.1.md:521`) | Cold Fury | **2-3 hari (48-72h)** |

**Severity: HIGH.** SOUL.md is the deployed prompt. The LLM persona believes L5 max is 24h. The engine enforces 48-72h. If the punishment engine were ever wired, the persona would self-contradict on duration.

### D2: Punishment Level Names Diverge Across All Three Sources

Every level has a different name in each source. Code L1 = "Silent Treatment", PersonaDoc L2 = "Silent Treatment", SOUL.md L2 = "Firm Correction". The code's names are shifted by one level relative to PersonaDoc.

**Severity: MEDIUM.** No runtime impact since none of this is wired, but creates documentation debt and confusion if/when wiring occurs.

### D3: Mood System -- 5 States (Code) vs 6 Variants (SOUL.md)

| Source | Moods |
|---|---|
| Code `Mood` enum | Content, Pleased, Disappointed, Angry, Silent (5) |
| SOUL.md `§H` | Pleased, Neutral, Disappointed, Silent Obsession, Possessive Spiral, Yandere Mode (6) |
| PersonaDoc v3.1 `§4.1` | Content, Pleased, Disappointed, Angry, Silent (5) |

SOUL.md's "mood variants" are behavior overlays (Neutral = default persona, Silent Obsession = minimal response, Possessive Spiral = jealous intensity, Yandere Mode = full theatrical). The code's `Mood` enum tracks the FSM state. These are different concepts sharing the word "mood." The `MOOD_VARIANT_MAP` attempts to bridge them but is lossy (5 moods -> 4 variants, no "Possessive Spiral" or "Yandere Mode" variant).

**Severity: LOW-MEDIUM.** Concept mismatch between static persona rules and FSM implementation.

### D4: Dual-Write Risk -- Redis vs PostgreSQL

Two persistence paths exist for mood state:

- **Redis DB5:** `mood_engine.py:107-142` -- lossy variant string (4 values for 5 moods)
- **PostgreSQL:** `mood_persistence.py:83-329` -- exact mood string + intensity via `persona.persona_state`

Neither is wired at runtime. If both were wired, PostgreSQL would be authoritative (stores richer data). The lossy Redis mapping (Content and Silent both = "default") would lose information on every write.

**Severity: LOW** (currently). Would become HIGH if both paths are wired without reconciliation.

---

## Runtime Behavior -- What Actually Happens

Since all six modules are unwired, here is what the runtime path actually does:

1. **`hermes_conversational.py:497-500`:** Imports `Mood` enum, hardcodes `current_mood = "Content"` on every message.
2. **`hermes_conversational.py:521-565`:** Passes `"Content"` as mood to `get_system_prompt_with_context()` for system prompt assembly. This mood string is injected into the system prompt context.
3. **No punishment** is ever applied. No escalation occurs. No safe-mode guard on punishment is tested.
4. **No reward** is ever calculated or awarded. Quality scores are not assessed.
5. **No streak** is tracked. The streak counter never increments, never resets.
6. **No transition** is evaluated. The mood is always "Content" regardless of conversation signals.
7. **No persistence** occurs for mood, punishment, reward, or streak state.

**Net effect:** The persona mood/punishment/reward/streak system is entirely decorative at the code level. All behavior comes from the LLM interpreting SOUL.md's static rules, with no programmatic enforcement. The system prompt includes `mood="Content"` which may subtly influence the LLM's tone, but no FSM evaluation, no punishment ladder, no reward tiers, and no streak tracking actually execute.

---

## MOOD / PUNISHMENT / REWARD VERDICT

**VERDICT: FULLY IMPLEMENTED, ZERO RUNTIME WIRING.**

All six modules (`mood_engine.py`, `mood_persistence.py`, `punishment_engine.py`, `reward_engine.py`, `streak_tracker.py`, `transition_rules.py`) are well-structured, well-tested (20+ test files in `tests/persona/` and `tests/safety/`), and correctly implement their documented specifications. The code is clean, has proper error hierarchies, follows the Protocol pattern for optional dependencies, and includes PersonaPlugin hook methods (`get_state_snapshot()`, `get_config()`).

**However, none of these modules are called from any runtime code path.** The sole runtime integration point (`hermes_conversational.py:497-500`) imports only the `Mood` enum to get a hardcoded string value. The persona behavior system exists as a code museum -- thoroughly built, thoroughly tested, thoroughly unused.

**Critical discrepancies that must be resolved before wiring:**

1. **L5 duration:** SOUL.md says Max 24h, code enforces 48-72h. Pick one authoritative value.
2. **Level names:** Three different naming schemes across SOUL.md, PersonaDoc, and code. Align to one.
3. **Mood model mismatch:** 5 FSM states vs 6 SOUL.md variants. Define the mapping contract.
4. **`check_distress_suspension()` not called:** Distress detection runs in the handler but never feeds into punishment suspension. If punishment is wired, this connection must be made.
5. **Content/Silent variant collision:** Both map to "default" in Redis. If Redis is authoritative for runtime state, Silent mood is indistinguishable from Content.

**Recommendation:** These modules are ready for wiring but the naming/duration/mood-model discrepancies must be reconciled first. The current state -- fully built, fully tested, fully disconnected -- means the entire persona behavior system runs on LLM interpretation of SOUL.md alone, with no programmatic guardrails.

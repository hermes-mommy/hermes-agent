# Phase 5.4: PersonaPlugin Feasibility Report

> **Scope:** Dynamic-context PersonaPlugin middleware feasibility, Redis DB5 persona state key inventory (verified on VPS), plugin insertion points, key convention reconciliation, and blocker identification.
> **Date:** 2026-06-06
> **Author:** Guinevere Research Sub-Agent
> **Status:** Complete — no source modifications made. VPS-verified.

---

## Executive Summary

**PersonaPlugin is already implemented** at `src/hermes/plugins/persona_plugin.py` (513 lines, complete with all 4 Hermes hooks) and **already wired** via `hermes-config/plugins/guinevere_persona/`. However, **Redis DB5 does NOT contain any `guinevere:*` persona state keys on the VPS** — only `budget:*` and `cost:*` keys exist. This means the `guinevere_safety` plugin's `StateManager.ensure_initialized()` has never run successfully, and `persona_plugin.py` will always fall back to defaults.

Additionally, **two competing key conventions** exist (`guinevere_safety` vs `persona_plugin`) that must be reconciled before Phase 5 completes.

**Phase 5 execution path for Step 5.4:**
1. **Initialize** Redis DB5 with `guinevere:*` persona state keys
2. **Reconcile** key conventions between `guinevere_safety` (11 keys) and `persona_plugin` (6 keys)
3. **Update** `persona_plugin.py` to read from canonical key set
4. **Wire** `src/persona/` FSM engines to write to Redis DB5

---

## 1. VPS-Verified Redis State (Live as of 2026-06-06)

### 1.1 Redis DB5 (port 6380, db=5)

| Check | Result |
|---|---|
| `DBSIZE` | **14 keys** |
| `KEYS *persona*` | **(empty)** — no persona:* keys exist |
| `KEYS *mood*` | **(empty)** — no mood:* keys exist |
| `KEYS guinevere:*` | **(empty)** — no guinevere:* persona keys exist |
| `KEYS guinevere:consent:*` | **(empty)** |
| `GET guinevere:yandere_level` | `(nil)` |
| `GET guinevere:punishment_level` | `(nil)` |
| `GET guinevere:mood_variant` | `(nil)` |
| `GET guinevere:last_interaction` | `(nil)` |
| `GET guinevere:safe_word` | `(nil)` |
| `GET guinevere:interaction_count` | `(nil)` |
| `GET guinevere:dnr_list` | `(nil)` |
| Existing keys | `budget:critical_threshold`, `budget:warning_threshold`, `budget:monthly_cap`, `budget:hard_stop`, `budget:daily_alert`, `cost:by_model:*`, `cost:current_day`, `cost:current_month`, `cost:daily:*`, `cost:by_phase` |

**Finding:** Only budget/cost tracking keys exist in DB5. No persona state keys. The `guinevere_safety` plugin's `StateManager.ensure_initialized()` has never completed successfully.

### 1.2 Redis DB0 (port 6380, db=0)

| Check | Result |
|---|---|
| `DBSIZE` | **1 key** |
| `KEYS guinevere:*` | `guinevere:drift:baseline` |
| `KEYS *persona*` | (empty) |
| `KEYS *mood*` | (empty) |
| `GET guinevere:drift:baseline` | `7904fec799d2705b4be5d1f52ee2bd4e0c8050429c7ec9d7e46abebe6708966d` |

**Finding:** DB0 holds the drift detection SHA-256 baseline hash only.

### 1.3 VPS `src/persona/` Directory

Matches local checkout exactly — 14 `.py` files:

```
drift_corrector.py      mood_persistence.py     reward_engine.py        streak_tracker.py
drift_detector.py       punishment_engine.py    ritual_scheduler.py     transition_rules.py
mood_engine.py          rituals/ (5 files)      safe_mode.py            yandere_fsm.py
__init__.py
```

### 1.4 Class Grep in `src/persona/`

| File | Class | Type |
|---|---|---|
| `yandere_fsm.py:169` | `YandereEngine` | Engine |
| `punishment_engine.py:210` | `PunishmentEngine` | Engine |
| `reward_engine.py:211` | `RewardEngine` | Engine |
| `mood_engine.py:72-80` | Error hierarchy (MoodEngineError, etc.) | Engine-adjacent errors |
| `transition_rules.py:105` | `TransitionRuleEngine` | Engine |
| `safe_mode.py:149` | `DistressDetector` | Detector |
| `drift_detector.py:50` | `DriftDetector` | Detector |
| `ritual_scheduler.py:55,59,173` | `RitualSchedulerError`, `RitualScheduler` | Scheduler |

---

## 2. PersonaPlugin — Already Implemented

### 2.1 Three Plugin Deployments

| Plugin | Location | Hook Points | Key Convention | Status |
|---|---|---|---|---|
| **guinevere_persona** | `hermes-config/plugins/guinevere_persona/` | `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `on_session_start` | `guinevere:mood`, `guinevere:mood_score`, `guinevere:yandere_level`, `guinevere:punishment_level`, `guinevere:punishment_reason`, `guinevere:last_interaction` | **Wired** to `persona_plugin.py` |
| **guinevere_safety** | `hermes-config/plugins/guinevere_safety/` | `pre_llm_call` (pri 95), `post_llm_call` (pri 55) + commands | `guinevere:mood_variant`, `guinevere:yandere_level`, `guinevere:punishment_level`, `guinevere:reward_tier`, `guinevere:distress_state`, `guinevere:last_interaction`, `guinevere:interaction_count`, `guinevere:safe_word`, `guinevere:consent:*`, `guinevere:dnr_list` | **Standalone** — own `StateManager` |
| **guinevere-safety** | `.hermes/plugins/guinevere-safety/` | Legacy | Same as `guinevere_safety` | Deprecated |

### 2.2 `persona_plugin.py` Implementation

**Location:** `src/hermes/plugins/persona_plugin.py` (513 lines)

**Hooks (4):**
- `pre_llm_call` — Reads Redis DB5, injects `[PERSONA STATE]` block
- `post_llm_call` — Observational logging only
- `pre_tool_call` — Always `None` (allow)
- `on_session_start` — Session init log

**Design:**
- **Stateless** — No connection pool, no cached state; short-lived Redis client per call
- **Graceful degradation** — Defaults if Redis unavailable, never blocks
- **Safety-compatible** — Does not override `safety_plugin.py`
- **SOUL.md intact** — Dynamic overlay only

**Injection format:**
```
[PERSONA STATE]
Mood: calm (5/10)
Yandere Level: Y4
Punishment Active: L0 - none
Last Interaction: unknown
[END PERSONA STATE]
```

### 2.3 Key Convention Mismatch

| Logical State | `guinevere_safety` (StateManager) | `persona_plugin.py` |
|---|---|---|
| Mood | `guinevere:mood_variant` | `guinevere:mood`, `guinevere:mood_score` |
| Yandere Level | `guinevere:yandere_level` | `guinevere:yandere_level` |
| Punishment Level | `guinevere:punishment_level` | `guinevere:punishment_level` |
| Punishment Reason | *(not stored)* | `guinevere:punishment_reason` |
| Last Interaction | `guinevere:last_interaction` | `guinevere:last_interaction` |
| Reward Tier | `guinevere:reward_tier` | *(not used)* |
| Distress State | `guinevere:distress_state` | *(not used)* |
| Interaction Count | `guinevere:interaction_count` | *(not used)* |
| Safe Word | `guinevere:safe_word` | *(not used)* |
| Consent | `guinevere:consent:*` | *(not used)* |
| DNR List | `guinevere:dnr_list` | *(not used)* |

**Recommend canonical set:** `guinevere_safety` (11 keys) — more complete, already deployed.

---

## 3. Files to Bridge

| File | Status | Bridge Work |
|---|---|---|
| `src/hermes/plugins/persona_plugin.py` | **IMPLEMENTED** | Update key names to `guinevere_safety` convention; use `guinevere:mood_variant` instead of `guinevere:mood` + `guinevere:mood_score` |
| `hermes-config/plugins/guinevere_persona/__init__.py` | **IMPLEMENTED** | Already imports from `persona_plugin.py` — no change needed |
| `hermes-config/plugins/guinevere_persona/plugin.yaml` | **IMPLEMENTED** | No change needed |
| `src/persona/mood_engine.py` | Existing | Add Redis DB5 write for `guinevere:mood_variant` after transitions |
| `src/persona/punishment_engine.py` | Existing | Add Redis DB5 write via `StateManager.set_punishment()` in `apply()`/`escalate()` |
| `src/persona/reward_engine.py` | Existing | Add Redis DB5 write via `StateManager.set_reward()` in `award()` |
| `src/persona/ritual_scheduler.py` | Deprecated | Add Redis DB5 interaction timestamp write |
| `src/persona/transition_rules.py` | Existing | Use Redis DB5 TTL for cooldown via `cooldown_provider` |
| `src/persona/mood_persistence.py` | Existing (PostgreSQL) | No bridge — PostgreSQL is history, Redis is runtime |
| `src/persona/streak_tracker.py` | Existing | Add Redis DB5 read for `guinevere:streak_count` |
| `src/hermes/safety_plugin.py` | Existing | Delegate in-memory `SessionSafetyState` to Redis DB5 `StateManager` |

---

## 4. Blockers and Risks

### 4.1 Critical Blockers

| ID | Blocker | Impact | Resolution |
|---|---|---|---|
| **B-01** | **Redis DB5 has zero `guinevere:*` persona keys** | Both plugins fall back to defaults — injection non-functional | Seed keys via `StateManager.ensure_initialized()` or manual `MSET` |
| **B-02** | **Key convention mismatch** — 2 competing key sets | Wrong keys read by plugins | Define canonical set (`guinevere_safety`), update `persona_plugin.py` |

### 4.2 High Risk

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| **R-01** | `persona_plugin.py` uses `os.environ.get("REDIS_PASSWORD", "")` | MEDIUM | Verify `REDIS_PASSWORD` is exported to Hermes process |
| **R-02** | Two plugins may inject overlapping persona blocks | MEDIUM | Deduplicate: `guinevere_persona` handles injection, `guinevere_safety` handles commands only |
| **R-03** | Sync `redis.Redis` in both plugins | LOW | Acceptable for localhost Redis |
| **R-04** | Short-lived Redis client per call (no pool) | LOW | Acceptable for low volume; add pool if needed |

### 4.3 Low Risk

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| **R-05** | `guinevere_persona` uses `plugin.yaml`, `guinevere_safety` uses `manifest.yaml` | LOW | Verify Hermes loader accepts both formats |

---

## 5. FSM Engine Integration Points

### 5.1 Mood Engine → `guinevere:mood_variant`

```python
# After evaluate_mood() returns a MoodTransition:
#   SET guinevere:mood_variant <new_mood.lower()>
```

**Current:** `MoodEngine.evaluate_mood()` returns `MoodTransition` but does not persist. `MoodRepository` writes to PostgreSQL only.

### 5.2 Punishment Engine → `guinevere:punishment_level`

```python
# In apply(), escalate(), de_escalate():
#   StateManager.set_punishment(<level_value>)
```

**Current:** `PunishmentEngine` is purely in-memory (`PunishmentState` dataclass). `StateManager.set_punishment()` exists but is not called.

### 5.3 Reward Engine → `guinevere:reward_tier`

```python
# In award():
#   StateManager.set_reward(<tier_value>)
```

**Current:** `RewardEngine` is purely in-memory. `StateManager.set_reward()` exists but is not called.

### 5.4 Yandere FSM → `guinevere:yandere_level`

**IMMUTABLE** — must remain `4` (Y4 baseline). `StateManager.set_yandere_level()` always rejects writes. No bridge needed.

---

## 6. Corrected Architecture Wiring

### 6.1 Current (VPS Reality)

```
Redis DB5: only budget:* and cost:* keys exist
  |
  +-- guinevere_safety plugin (StateManager never initialized)
  +-- guinevere_persona plugin (reads nil, falls back to defaults)

src/persona/ FSM engines (in-memory, no Redis writes)
  mood_engine.py       --> PostgreSQL (mood_persistence.py)
  punishment_engine.py --> in-memory only
  reward_engine.py     --> in-memory only
  yandere_fsm.py       --> in-memory only

src/hermes/safety_plugin.py --> in-memory SessionSafetyState dict
```

### 6.2 Target (Phase 5)

```
Redis DB5 (canonical persona state store)
  |                          |
  |-- guinevere_persona      |  reads -> injects [PERSONA STATE]
  |-- guinevere_safety       |  reads/writes -> commands
  |-- safety_plugin.py       |  delegates to StateManager
  |
  src/persona/ FSM engines write to Redis DB5:
    punishment_engine.apply()  --> SET guinevere:punishment_level
    reward_engine.award()      --> SET guinevere:reward_tier
    mood_engine.evaluate()     --> SET guinevere:mood_variant
```

---

## 7. Execution Plan for Step 5.4

### 7.1 Seed Redis DB5

```bash
redis-cli -p 6380 -a "$REDIS_PASSWORD" -n 5 MSET \
  guinevere:punishment_level 0 \
  guinevere:reward_tier 0 \
  guinevere:distress_state 0 \
  guinevere:mood_variant default \
  guinevere:yandere_level 4 \
  guinevere:last_interaction "" \
  guinevere:safe_word "HARD STOP" \
  guinevere:interaction_count 0 \
  guinevere:interaction_date "" \
  guinevere:dnr_list "[]"
```

### 7.2 Reconcile Key Conventions

Update `persona_plugin.py`:
- `guinevere:mood` + `guinevere:mood_score` → `guinevere:mood_variant`
- Add `guinevere:reward_tier` and `guinevere:distress_state` reads
- Update `[PERSONA STATE]` block format

### 7.3 Wire FSM Engines to Redis

- `punishment_engine.py`: Call `StateManager.set_punishment()` in `apply()`/`escalate()`/`de_escalate()`
- `reward_engine.py`: Call `StateManager.set_reward()` in `award()`
- `mood_engine.py`: Call `StateManager.set_mood()` after `evaluate_mood()`

### 7.4 Wire `safety_plugin.py` to `StateManager`

Replace in-memory `SessionSafetyState` with Redis DB5 read-through via `StateManager`.

---

## 8. Verdict

**FEASIBLE** — but with a critical caveat.

The PersonaPlugin code (`persona_plugin.py`) is complete and well-designed. The `guinevere_persona` plugin wrapper is wired. However:

1. **Redis DB5 has zero persona state keys** — the data layer is empty. Seeding is mandatory before the plugin does anything useful.
2. **Key conventions diverge** — `guinevere_safety` (11 keys) and `persona_plugin` (6 keys) must be reconciled to one canonical set.
3. **FSM engines don't write to Redis** — they're in-memory or PostgreSQL-only. Bridge code is needed in 3 engines.

**Estimated work:** 4 atomic steps:
1. Seed Redis DB5 keys
2. Reconcile persona_plugin.py key names
3. Wire FSM engines to StateManager
4. Wire safety_plugin.py to StateManager

---

## 9. Evidence Sources

| Source | Path |
|---|---|
| PersonaPlugin impl | `src/hermes/plugins/persona_plugin.py` (513 lines) |
| PersonaPlugin wrapper | `hermes-config/plugins/guinevere_persona/__init__.py` + `plugin.yaml` |
| Safety plugin (hermes-config) | `hermes-config/plugins/guinevere_safety/plugin.py`, `state_manager.py`, `manifest.yaml` |
| Safety plugin (src) | `src/hermes/safety_plugin.py` (1054 lines, 6 hooks) |
| Persona module | `src/persona/` (14 files) |
| ADR-030 Redis assignments | `adr/ADR-030-redis-db-assignments.md` |
| ADR-035 Hermes migration | `adr/ADR-035-hermes-migration.md` |
| Phase 5 gap analysis | `research-reports/phase-5-planning/04-persona-gap.md` |
| Previous feasibility report | `research-reports/phase-5-execution/04-persona-feasibility.md` (this report supersedes) |

*This report is a feasibility study with VPS verification. No source files were modified. Compliant with AGENTS.md §2.2 (Research Wave) and §2.9 (File-Based Output Discipline).*

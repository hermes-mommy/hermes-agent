# Phase 5: PersonaPlugin Feasibility Report

> **Scope:** Dynamic-context PersonaPlugin middleware feasibility, Redis DB5 persona state keys, plugin insertion points, and blocker identification.
> **Date:** 2026-06-05
> **Author:** Guinevere Research Sub-Agent
> **Status:** Complete — no source modifications made.

---

## Executive Summary

A PersonaPlugin for Phase 5 is **highly feasible** with low architectural risk. Two plugin implementations already exist in the codebase (`hermes-config/plugins/guinevere_safety/` and `.hermes/plugins/guinevere-safety/`), establishing a proven pattern. Redis DB5 already stores all required persona state keys (punishment, reward, mood, yandere, distress, consent, DNR). The gap is that the existing plugins require integration with the `src/persona/` FSM engines and the Hermes hook lifecycle — neither of which is fully wired as of this report.

**Key finding:** The existing `guinevere_safety` plugin in `hermes-config/plugins/` already functions as a PersonaPlugin in spirit — it reads Redis DB5, injects persona state into `pre_prompt`, and exposes command handlers. But it is a standalone plugin in the Hermes config tree, not wired into the `src/persona/` FSM engines, the safety plugin in `src/hermes/safety_plugin.py`, or the Phase 5 skill architecture. This is the primary integration work for Phase 5.

---

## 1. Current Architecture Map

### 1.1 Persona Module (`src/persona/`)

14 files, ~4,200 lines of Python. Three categories:

| Category | Files | Behavior |
|---|---|---|
| **FSM Engines** | `mood_engine.py`, `yandere_fsm.py`, `punishment_engine.py`, `reward_engine.py` | Deterministic state machines with hard safety ceilings |
| **Persistence** | `mood_persistence.py` (PostgreSQL), `streak_tracker.py` (PostgreSQL) | Async SQLAlchemy CRUD via `PersonaState`/`MoodHistory` models |
| **Safety** | `safe_mode.py`, `drift_detector.py`, `drift_corrector.py`, `transition_rules.py`, `ritual_scheduler.py` + `rituals/` | Distress detection, SHA-256 drift, cooldowns, WIB cron |

### 1.2 Redis DB5 State Keys (comprehensive inventory)

Source: `hermes-config/plugins/guinevere_safety/state_manager.py`

| Key | Type | Range | Mutability | Description |
|---|---|---|---|---|
| `guinevere:punishment_level` | int | 0-5 | Mutable (L6 rejected) | Current punishment ladder level |
| `guinevere:reward_tier` | int | 0-5 | Mutable (T5 cap) | Current reward tier |
| `guinevere:distress_state` | int | 0-4 | Mutable | Distress level D0-D4 |
| `guinevere:mood_variant` | str | default\|playful\|serious\|caring | Mutable | Mood variant for prompt injection |
| `guinevere:yandere_level` | int | 4 (locked) | **IMMUTABLE** | Always Y4 baseline; any attempt to change is logged+rejected |
| `guinevere:last_interaction` | ISO 8601 str | — | Mutable | Last interaction timestamp |
| `guinevere:interaction_count` | int | — | Mutable | Daily counter, resets at midnight |
| `guinevere:interaction_date` | str | YYYY-MM-DD | Mutable | Date tracking for counter reset |
| `guinevere:safe_word` | str | "HARD STOP" | Quasi-mutable | Safe word phrase |
| `guinevere:consent:{category}` | bool | 5 categories | Mutable | consent:surveillance, destructive, financial, system, network |
| `guinevere:dnr_list` | JSON list | — | Mutable | Do Not Remember topic list |

Cost tracking keys also live in DB5 (budget thresholds, cost counters, per-model costs) but are managed by separate modules and are out of scope for PersonaPlugin.

### 1.3 Redis Connection Pattern

All persona state uses:
```python
redis.Redis(host="localhost", port=6380, db=5, decode_responses=True)
```
Standardized via `ConnectionPool.from_url("redis://localhost:6380/5")` in `StateManager`. The existing `redis_tool.py` MCP tool defaults to DB5 and uses `redis.asyncio` (async). The safety plugin `state_manager.py` uses sync `redis.Redis` — this is a non-blocking concern since it's called from Hermes hook context, not an async event loop.

---

## 2. Existing Plugin / Hook Patterns

### 2.1 Three Plugin Deployments Exist

| Plugin | Location | Hook Points | Status |
|---|---|---|---|
| **guinevere_safety** | `hermes-config/plugins/guinevere_safety/` | `pre_llm_call` (priority 95), `post_llm_call` (priority 55) + command handlers | Active, wired to Hermes config, manages Redis DB5 state |
| **guinevere-safety** | `.hermes/plugins/guinevere-safety/` | `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `post_tool_call`, `transform_llm_output`, `on_session_start` | Legacy deployment, re-exports from `src/hermes/safety_plugin.py` |
| **guinevere-memory** | `plugins/memory/guinevere_memory/` | `prefetch`, `sync_turn`, `on_session_end`, `on_pre_compress`, `on_memory_write`, `system_prompt_block`, `shutdown` | Phase 3 memory bridge, PostgreSQL-backed |
| **auth_overlay** | `hermes-config/plugins/auth_overlay/` | `pre_tool_call` | Fail-closed auth enforcement |

### 2.2 Hermes Hook System (v0.15.2)

ADR-035 §Decision Drivers documents the 7 lifecycle hooks:
- **`pre_prompt`** — Before LLM call (fail-closed HARD STOP, distress)
- **`post_prompt`** — After prompt assembly, before LLM (drift detection)
- **`pre_tool_call`** — Before tool execution (auth, consent, budget)
- **`post_tool_call`** — After tool execution (output sanitization)
- **`pre_response`** — Before Discord delivery (final safety)
- **`post_response`** — After Discord delivery (yandere, secret scan)
- **`on_error`** — Error classification and alerting

### 2.3 Plugin Manifest Format

Every Hermes plugin follows this pattern (`manifest.yaml` or `plugin.yaml`):
```yaml
name: guinevere_safety
version: 1.0.0
description: Dynamic persona state management for Guinevere
critical: true
dependencies:
  - redis>=4.0.0
hooks:
  - event: pre_llm_call
    handler: inject_dynamic_state
    priority: 95
  - event: post_llm_call
    handler: update_state
    priority: 55
commands:
  - name: get_persona_state
    handler: cmd_get_state
  - name: set_punishment
    handler: cmd_set_punishment
  - name: set_reward
    handler: cmd_set_reward
```

The plugin entry point exposes a `register(ctx)` function that the Hermes plugin loader calls.

---

## 3. Candidate Insertion Points

### 3.1 For PersonaPlugin as Dynamic-Context Middleware

| Insertion Point | Hook/Mechanism | What It Does | Priority |
|---|---|---|---|
| **pre_prompt** | `GuinevereSafetyPlugin.inject_dynamic_state` | Reads Redis DB5 keys, injects `[Dynamic Persona State]` block into system prompt | **PRIMARY** — this IS the dynamic context injection |
| **post_response** | `GuinevereSafetyPlugin.update_state` | Records interaction timestamp, increments daily counter | Second layer — stateless observer |
| **on_session_start** | `src/hermes/safety_plugin.py:on_session_start` | Initializes session state with Y4 baseline, clears distress | Session lifecycle boundary |
| **custom command handlers** | `cmd_get_state`, `cmd_set_punishment`, etc. | State introspection/mutation via Redis DB5 | Operator-facing tooling |

### 3.2 Integration with FSM Engines

The current `guinevere_safety` plugin in `hermes-config/plugins/` reads Redis DB5 but does **not** call `src/persona/mood_engine.py`, `src/persona/punishment_engine.py`, or `src/persona/yandere_fsm.py`. These FSM engines exist as standalone classes with their own safety boundaries (L6 rejection, Y4 immutability, mood transition validation). Phase 5 PersonaPlugin must bridge the two:

**Current gap:**
```
Redis DB5 <──> guinevere_safety plugin (reads/writes raw keys)
  ^
  |--- src/persona/* engines (NOT CONNECTED to plugin)
```

**Target:**
```
Redis DB5 <──> guinevere_safety plugin (read for injection, write via FSM)
                  ^
                  |--- src/persona/mood_engine.py (transition validation)
                  |--- src/persona/punishment_engine.py (L6 guard, escalation)
                  |--- src/persona/yandere_fsm.py (Y4 immutability, Y5 ceiling)
                  |--- src/persona/reward_engine.py (tier calculation)
```

### 3.3 SOUL.md Relationship

Per ADR-035 §D7 and the existing SOUL.md header:
> **Dynamic state:** Managed by `guinevere_safety` plugin via Redis DB5

SOUL.md is the **static identity constitution**. The PersonaPlugin provides the dynamic context injection that the static SOUL.md cannot express. The contract is:

- **SOUL.md**: "I am Guinevere de Baroque — Y4 baseline, dominant, protective"
- **PersonaPlugin**: "Current mood: Disappointed, Punishment: L3, Distress: D0, Yandere: Y4"

The PersonaPlugin **must never replace or modify SOUL.md**. It reads from Redis DB5 and appends dynamic context.

---

## 4. Redis DB5 Persona State — Complete Key Catalog

### 4.1 Core Persona Keys

```
guinevere:punishment_level       = "0"          # int 0-5 (L0=none, L1-L5, L6 rejected)
guinevere:reward_tier            = "0"          # int 0-5 (T0=none, T1-T5)
guinevere:distress_state         = "0"          # int 0-4 (D0=normal, D4=crisis)
guinevere:mood_variant           = "default"    # str: default|playful|serious|caring
guinevere:yandere_level          = "4"          # int 4 (IMMUTABLE — always Y4)
```

### 4.2 Session/Interaction Keys

```
guinevere:last_interaction       = "2026-06-05T12:00:00+00:00"  # ISO 8601
guinevere:interaction_count      = "42"                          # daily counter
guinevere:interaction_date       = "2026-06-05"                  # YYYY-MM-DD
```

### 4.3 Safety Keys

```
guinevere:safe_word              = "HARD STOP"   # safe word phrase
guinevere:consent:surveillance   = "true"        # bool string
guinevere:consent:destructive    = "false"
guinevere:consent:financial      = "false"
guinevere:consent:system         = "true"
guinevere:consent:network        = "true"
guinevere:dnr_list               = "[]"          # JSON array
```

### 4.4 DB5 Non-Persona Keys (Out of Scope)

```
budget:*                         # Budget thresholds and caps
cost:*                           # Cost tracking counters
search:*                         # Brave/Context7/Exa search counters
```

---

## 5. Blockers and Risks

### 5.1 Critical Blockers

| ID | Blocker | Impact | Resolution Path |
|---|---|---|---|
| **B-01** | `guinevere_safety` plugin in `hermes-config/plugins/` is not wired to `src/hermes/safety_plugin.py` | Duplicate safety state (in-memory `SessionSafetyState` vs Redis DB5) — two sources of truth | Refactor `src/hermes/safety_plugin.py` to delegate state persistence to `StateManager` (Redis DB5) instead of in-memory dict |
| **B-02** | `src/persona/mood_persistence.py` uses PostgreSQL (`PersonaState` table), not Redis DB5 | Mood state split across two stores — PostgreSQL `PersonaState.state_key='current_mood'` and Redis `guinevere:mood_variant` | Align to single source of truth: Redis DB5 for runtime state (fast, ephemeral), PostgreSQL for history (durable, queryable) |
| **B-03** | `src/persona/punishment_engine.py` is purely in-memory (`PunishmentState` dataclass) with no persistence layer | Punishment state lost on process restart | Add Redis DB5 persistence to `PunishmentEngine` (or wrap with `StateManager`) |

### 5.2 High Risk

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| **R-01** | `guinevere_safety` plugin `state_manager.py` uses sync `redis.Redis` — may block Hermes async hook pipeline if Redis is slow | MEDIUM | Acceptable for now (Redis is localhost, <1ms). Migrate to `redis.asyncio` if profiling shows contention. |
| **R-02** | Two plugin deployments (`hermes-config/` and `.hermes/`) have overlapping hook registrations | MEDIUM | Standardize on `hermes-config/plugins/guinevere_safety/` as the canonical deployment. Deprecate `.hermes/plugins/guinevere-safety/`. |
| **R-03** | `src/hermes/safety_plugin.py` maintains in-memory `SessionSafetyState` dict that duplicates Redis DB5 state | MEDIUM | After B-01 resolution, in-memory state serves as a read cache; Redis is write authority. Implement TTL-based cache invalidation. |
| **R-04** | `src/persona/streak_tracker.py` and `mood_persistence.py` use `AsyncSession + SQLAlchemy` — async model conflicts with sync Hermes hooks | MEDIUM | Keep async for PostgreSQL. Hermes hooks that need streak/mood data read from Redis DB5 (sync, fast), not PostgreSQL. |

### 5.3 Low Risk

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| **R-05** | Redis DB5 ACL is `guinevere_core (+@all -@dangerous)` — allows all non-dangerous commands. PersonaPlugin only needs `GET`, `SET`, `MGET`, `EXISTS`, `DEL`, `INCR` | LOW | Create persona-specific ACL user with restricted command set post-migration |
| **R-06** | Phase 5 gap analysis (`research-reports/phase-5-planning/04-persona-gap.md`) incorrectly states "persona files rely on PostgreSQL for state" — missing the `guinevere_safety` plugin's Redis DB5 usage | LOW | Correction noted: persona state is split between Redis DB5 (runtime) and PostgreSQL (history) |

---

## 6. Integration Wiring Summary

### 6.1 File Dependency Graph (Current)

```
                  ┌─────────────────────────┐
                  │  src/hermes/safety_plugin.py │
                  │  (6 hooks, in-memory state) │
                  └────────┬────────────────┘
                           │ imports
                           ▼
┌───────────────────────────────────────────────┐
│  src/persona/                                  │
│  ├── yandere_fsm.py    ← YandereEngine()      │
│  ├── safe_mode.py      ← DistressDetector()   │
│  ├── drift_detector.py ← DriftDetector()      │
│  ├── secret_scanner    ← (from surveillance)  │
│  └── auth_matrix       ← (from mcp)           │
└───────────────────────────────────────────────┘

┌───────────────────────────────────────────────┐
│  hermes-config/plugins/guinevere_safety/       │
│  ├── plugin.py          ← GuinevereSafetyPlugin│
│  ├── state_manager.py   ← StateManager (DB5)   │
│  └── manifest.yaml                             │
└───────────────────────────────────────────────┘
         ↑ NOT WIRED TO src/hermes/safety_plugin.py ↑
```

### 6.2 File Dependency Graph (Target — Phase 5)

```
                  ┌─────────────────────────────────┐
                  │  hermes-config/plugins/guinevere_safety/plugin.py │
                  │  (CANONICAL PersonaPlugin)       │
                  │  pre_prompt: inject_dynamic_state │
                  │  post_response: update_state      │
                  │  commands: get/set state          │
                  └────────────┬────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  state_manager.py   │
                    │  (Redis DB5 R/W)    │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ src/persona/     │  │ src/persona/     │  │ src/hermes/      │
│ mood_engine.py   │  │ punishment_engine│  │ safety_plugin.py │
│ yandere_fsm.py   │  │ reward_engine.py │  │ (delegates to    │
│ (validation)     │  │ (L6 guard)       │  │  state_manager)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 7. Recommendations

1. **Consolidate to one plugin.** Standardize on `hermes-config/plugins/guinevere_safety/` as the canonical PersonaPlugin. Deprecate `.hermes/plugins/guinevere-safety/`.

2. **Make `src/hermes/safety_plugin.py` delegate to `StateManager`.** The in-memory `SessionSafetyState` should become a read-through cache with Redis DB5 as write authority. This resolves B-01.

3. **Wire FSM engines to plugin.** `GuinevereSafetyPlugin` in `hermes-config/plugins/guinevere_safety/plugin.py` currently reads/writes Redis directly without calling FSM validators. Add calls to:
   - `yandere_fsm.YandereEngine.get_effective_level()` before injecting yandere state
   - `punishment_engine.PunishmentEngine.apply()` instead of direct `SET guinevere:punishment_level`
   - `mood_engine.can_transition()` before setting mood variant

4. **Keep SOUL.md as static identity constitution.** Do not add dynamic state to SOUL.md. The PersonaPlugin handles dynamic injection.

5. **Redis DB5 is the correct database.** DB5 is already allocated for safety plugin state (ADR-030). No new Redis DB needed.

6. **No schema changes required.** All state keys already exist in `state_manager.py` `ensure_initialized()`. Phase 5 work is integration wiring only.

---

## 8. Evidence Sources

| Source | Path | Key Content |
|---|---|---|
| Phase 5 gap analysis | `research-reports/phase-5-planning/04-persona-gap.md` | Per-file migration analysis, risk assessment |
| ADR-030 Redis assignments | `adr/ADR-030-redis-db-assignments.md` | DB5 purpose: "safety plugin state" |
| ADR-035 Hermes migration | `adr/ADR-035-hermes-migration.md` | Hook system, plugin architecture, safety mapping |
| Safety plugin (hermes-config) | `hermes-config/plugins/guinevere_safety/plugin.py` | PersonaPlugin candidate — `inject_dynamic_state`, `state_manager` |
| Safety plugin (src) | `src/hermes/safety_plugin.py` | 6 hooks, in-memory state, 10 safety gates |
| State manager | `hermes-config/plugins/guinevere_safety/state_manager.py` | Complete Redis DB5 key catalog, connection pattern |
| Persona module init | `src/persona/__init__.py` | All 14 exported classes and FSM engines |
| Redis DB5 evidence | `docs/setup-evidence/P1/STEP-P1-020/redis-db5-keys.txt` | Cost tracking keys (supplementary) |
| SOUL.md | `hermes-config/SOUL.md` | Static persona constitution, dynamic state reference |

---

## 9. Verdict

**FEASIBLE** — PersonaPlugin can be implemented as dynamic-context middleware reading Redis DB5 state without replacing SOUL.md. The core infrastructure (Redis DB5 keys, Hermes hooks, plugin registration) is already deployed. Phase 5 work is integration wiring between the existing `guinevere_safety` plugin and the `src/persona/` FSM engines, plus consolidation of the two overlapping plugin deployments.

**Estimated work:** 3-5 atomic steps:
1. Consolidate plugin deployments (deprecate `.hermes/plugins/guinevere-safety/`)
2. Wire `src/hermes/safety_plugin.py` to delegate state to `StateManager` (Redis DB5)
3. Connect `guinevere_safety` plugin's state mutations to FSM validators (`yandere_fsm`, `punishment_engine`, `mood_engine`)
4. Add persistence to `PunishmentEngine` via Redis DB5
5. Write integration tests for the plugin → FSM → Redis pipeline

---

*This report is a feasibility study only. No source files were modified. Compliant with AGENTS.md §2.2 (Research Wave) and §2.9 (File-Based Output Discipline).*

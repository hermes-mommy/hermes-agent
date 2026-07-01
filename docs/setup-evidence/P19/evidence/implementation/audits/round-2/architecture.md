# P19 Architecture Audit -- Round 2

**Auditor:** P19 architecture auditor
**Date:** 2026-06-26
**Scope:** 10 checks against P19 multi-project context implementation

---

## 1. state.py -- project_id in LifeMindState + SessionState

**File:** `src/life_kernel/state.py`

| Location | Field | Type |
|----------|-------|------|
| Line 265 | `project_id: NotRequired[str]` | LifeMindState |
| Line 321 | `project_id: NotRequired[str]` | SessionState |

Both fields are `NotRequired[str]`, meaning they are optional in the TypedDict. Existing checkpoints without `project_id` load safely (checkpoint-replay-safe). Docstrings at lines 266-272 and 322-328 document the intent correctly.

**Verdict: PASS** -- Both state dicts carry `project_id` as `NotRequired[str]`, additive-only, no breaking changes to existing checkpoints.

---

## 2. heartbeat.py -- thread_id conditional on feature:projects:enabled

**File:** `src/life_kernel/heartbeat.py`

The method `_resolve_thread_id` (line 125) correctly implements the feature-flag check:
- Reads `feature:projects:enabled` from Redis (line 145)
- Returns `f"heartbeat-{project_id}"` when flag ON + project_id present (line 164)
- Returns legacy `"heartbeat"` in all other cases (line 166)
- Fail-safe: Redis errors default to OFF (lines 146-151)

**CRITICAL FINDING:** All 6 call sites invoke `_resolve_thread_id()` WITHOUT passing `project_id`:

| Line | Call |
|------|------|
| 343 | `await self._resolve_thread_id()` -- hard_stop set |
| 383 | `await self._resolve_thread_id()` -- hard_stop recovery |
| 410 | `await self._resolve_thread_id()` -- _safe_aget_state |
| 492 | `await self._resolve_thread_id()` -- 60s health check |
| 510 | `await self._resolve_thread_id()` -- 60s decision invoke |
| 677 | `await self._resolve_thread_id()` -- 1h reflection |

The `HeartbeatController.__init__` (lines 95-109) does not store a `project_id` attribute. There is no mechanism for the heartbeat loop to know the current project context.

**Result:** `_resolve_thread_id` always returns `"heartbeat"` in production. The feature-flag-conditional logic (lines 143-166) is dead code.

**Verdict: FAIL** -- The method signature accepts `project_id` but no call site passes it. The feature-gated `thread_id` logic is unreachable. The HeartbeatController needs a `self._project_id` field populated at construction (or resolved per-tick) and forwarded to `_resolve_thread_id(self._project_id)` at each call site.

---

## 3. graph.py -- _PROJECT_ADAPTERS per-project, _get_adapters reads from context

**File:** `src/life_kernel/graph.py`

| Item | Line(s) | Status |
|------|---------|--------|
| `_PROJECT_ADAPTERS` dict | 42 | Module-level registry, `dict[str, dict[str, Any]]` |
| `set_adapters(..., project_id=...)` | 45-78 | Writes to `_PROJECT_ADAPTERS[project_id]` when project_id set, else global `_ADAPTERS` |
| `reset_adapters(project_id)` | 81-92 | Pops per-project or clears global |
| `_get_adapters(state)` | 95-113 | Reads `state.get("project_id")`, returns `_PROJECT_ADAPTERS[pid]` if found, else `_ADAPTERS` |
| Usage in observe_node | 224-227 | `_active_adapters = _get_adapters(state)` |
| Usage in reflect_node | 575 | `_active_adapters = _get_adapters(state)` |

The context-read pattern (ARCH-02 fix) is correctly implemented: node functions read `project_id` from LangGraph state, not from global mutation.

**Verdict: PASS** -- Per-project adapter isolation is correctly implemented via context-read from state.

---

## 4. cognition.py -- ProjectAwareCognitionRegistry bounded N=3

**File:** `src/life_kernel/cognition.py`

| Item | Line(s) | Detail |
|------|---------|--------|
| Class definition | 419 | `ProjectAwareCognitionRegistry` |
| Default max_active | 432 | `def __init__(self, max_active: int = 3)` |
| Instance storage | 433 | `self._instances: dict[str \| None, BackgroundCognition]` |
| Flag check | 437-445 | `_is_flag_on()` reads `feature:projects:enabled` from Redis, fail-safe OFF |
| Capacity enforcement | 476 | `if len(self._instances) >= self._max_active: return None` |
| Legacy fallback | 468-471 | When flag OFF, single instance keyed by `None` |
| Documentation | 420-430 | Docstring states "bounded concurrency cap (default 3)" |

The registry is correctly bounded at N=3, uses a feature flag for activation, and preserves legacy single-instance behavior when the flag is OFF.

**Verdict: PASS** -- Bounded at N=3 (line 432), capacity check at line 476, feature-flag-gated, legacy-safe.

---

## 5. memory_store.py -- WHERE project_id = :pid OR project_scope = 'global' filter

**File:** `src/projects/memory_store.py`

This module is a **wrapper layer** that injects `project_id` into downstream callable kwargs. It does NOT contain raw SQL.

| Function | Line | Mechanism |
|----------|------|-----------|
| `scope_recall_callable` | 38-60 | Wraps recall fn, injects `project_id=project_id` into kwargs (line 57) |
| `scope_store_callable` | 63-83 | Wraps store fn, injects `project_id` + `project_scope` into kwargs (lines 79-80) |
| `ProjectScopedMemoryStore.recall` | 109-130 | Delegates to `scope_recall_callable` |
| `ProjectScopedMemoryStore.store` | 136-165 | Delegates to `scope_store_callable` |

Zero-copy when `project_id=None`: returns original callable unchanged (lines 53, 75).

The actual `WHERE project_id = :pid OR project_scope = 'global'` SQL filter is implemented in the downstream consumers (KG engine lines 933-937, PPR lines 377-381, and the memory read pipeline's `recall_memories` function).

**Verdict: PASS** -- The wrapper correctly injects project scoping. The SQL-level WHERE clause is in the downstream KG and memory pipeline modules (verified in checks 7 and 8).

---

## 6. _memory_bridge.py -- recall_for_context + store_conversation accept project_id

**File:** `src/hermes/_memory_bridge.py`

| Method | Line | project_id parameter |
|--------|------|---------------------|
| `recall_for_context` | 94 | `project_id: uuid.UUID \| None = None` (line 103) |
| `store_conversation` | 225 | `project_id: uuid.UUID \| None = None` (line 232) |

**recall_for_context** (lines 94-220):
- Passes `project_id` to `recall_memories()` (line 162)
- Passes `project_id` to `KGQueryEngine.search_entities()` (line 174)
- Docstring documents the `project_id == project_id OR project_scope == 'global'` contract (line 134)

**store_conversation** (lines 225-302):
- Passes `project_id` to `store_episode()` (line 302)
- Docstring documents project-isolated tagging behavior (lines 249-252)

**Verdict: PASS** -- Both READ and WRITE paths accept and forward `project_id` correctly.

---

## 7. engine.py -- search_entities accepts project_id

**File:** `src/knowledge_graph/query/engine.py`

| Item | Line(s) | Detail |
|------|---------|--------|
| Method signature | 876-882 | `search_entities(query, *, limit, project_id: uuid.UUID \| None = None)` |
| SQL project clause | 932-937 | `AND (project_id = CAST(:project_id AS uuid) OR project_scope = 'global')` |
| Params injection | 964-965 | `params["project_id"] = project_id` |
| Docstring contract | 897-909 | Documents DATA-04 isolation semantics |

The SQL is correctly parameterized. The project clause is only injected when `project_id is not None` (line 933), preserving legacy global behavior.

**Verdict: PASS** -- `search_entities` correctly accepts and applies `project_id` filtering with proper SQL parameterization.

---

## 8. ppr.py -- _load_adjacency accepts project_id, WHERE filter

**File:** `src/knowledge_graph/query/ppr.py`

| Item | Line(s) | Detail |
|------|---------|--------|
| `_load_adjacency` signature | 344-348 | `project_id: uuid.UUID \| None = None` |
| SQL project clause | 376-381 | `AND (project_id = CAST(:project_id AS uuid) OR project_scope = 'global')` |
| Params injection | 394-395 | `params["project_id"] = project_id` |
| `personalized_pagerank` forward | 185, 241-242 | Passes `project_id` through to `_load_adjacency` |
| Docstring contract | 351-354 | Documents DATA-04 boundary walk prevention |

The PPR engine prevents cross-project graph walks by scoping adjacency loading. The SQL is parameterized and the project clause is conditionally injected.

**Verdict: PASS** -- `_load_adjacency` correctly accepts and applies `project_id` filtering for graph walk isolation.

---

## 9. ADR-052 -- P23 and P24 downstream contracts

**File:** `adr/ADR-052-multi-project-context.md`

| Downstream Phase | Line | Contract Summary |
|-----------------|------|------------------|
| P23 Embodied Operations | 309 | Executor adapters + action queue carry `project_id`; risk tiers L1-L4 project-scoped; P23-012 gated on P19 namespace contract readiness; P19 owns the registry, P23 reads it |
| P24 Hermes Fork | 310 | Owned fork carries `project_id` through internal plugin/module system; P24-002 gated on P19 namespace contract readiness; reads `projects.project_registry` for skill loading + session isolation; impl held until P19 deployed |
| P21 Voice | 306 | Nullable `project_id` seam on voice clips/profiles/settings |
| P22 Life Integration Hub | 307 | Reads `projects.project_registry` read-only; all P22 data tagged at write time |
| P17 Cross-Device Sync | 308 | Sync keys include `project_id` as partition dimension |

Additional compliance section (lines 312-322):
- HARD STOP is explicitly global -- one key, all projects halted
- Shared persona across projects
- DNR applies globally
- Consent revocation: project-scoped scopes get `project_id`, safety scopes remain global

**Verdict: PASS** -- ADR-052 explicitly defines P23 and P24 downstream contracts with gating conditions. Both phases are gated on P19 namespace contract readiness.

---

## 10. HARD STOP global -- grep life_kernel:hard_stop

**File(s):** `src/life_kernel/heartbeat.py`, `src/life_kernel/graph.py`, `src/life_kernel/dashboard_writer.py`

| Location | Line(s) | Detail |
|----------|---------|--------|
| heartbeat.py | 82, 317-318 | Redis key `life_kernel:hard_stop` -- single global key, no project scoping |
| heartbeat.py | 326-328 | `live_hard_stop = bool(hard_stop_value)` -- checked once, applies to ALL |
| heartbeat.py | 343-351 | Sets `hard_stop_requested: True` in graph state -- single graph instance |
| graph.py | 215 | Phase `HARD_STOPPED` mapped to `"hard_stop_heartbeat"` |
| graph.py | 373 | `if state.get("hard_stop_requested", False)` -- global state check |
| dashboard_writer.py | 213 | `publish_hard_stop(state)` -- single publish, no project filter |
| ADR-052 line 318 | Compliance | "The safe word `life_kernel:hard_stop` halts ALL projects simultaneously. No code path may scope HARD STOP to a single project." |

There is no `project_id` parameter or scoping anywhere in the HARD STOP code path. The Redis key is a single global string literal `"life_kernel:hard_stop"` with no per-project suffix.

**Verdict: PASS** -- HARD STOP is correctly global. Single Redis key, single halt, no project-scoped escape hatch.

---

## Summary

| # | Check | Verdict |
|---|-------|---------|
| 1 | state.py: project_id in LifeMindState + SessionState | **PASS** |
| 2 | heartbeat.py: thread_id conditional on feature:projects:enabled | **FAIL** |
| 3 | graph.py: _PROJECT_ADAPTERS per-project + context-read | **PASS** |
| 4 | cognition.py: ProjectAwareCognitionRegistry bounded N=3 | **PASS** |
| 5 | memory_store.py: project_id/scoped filter wrapper | **PASS** |
| 6 | _memory_bridge.py: recall_for_context + store_conversation | **PASS** |
| 7 | engine.py: search_entities accepts project_id | **PASS** |
| 8 | ppr.py: _load_adjacency accepts project_id + WHERE filter | **PASS** |
| 9 | ADR-052: P23 and P24 downstream contracts | **PASS** |
| 10 | HARD STOP global | **PASS** |

**9 PASS, 1 FAIL**

### Blocking Issue

**FAIL #2: heartbeat.py `_resolve_thread_id` dead code.** The method (line 125) correctly implements feature-flag-conditional `thread_id` resolution, but all 6 call sites (lines 343, 383, 410, 492, 510, 677) invoke it without passing `project_id`. The `HeartbeatController.__init__` (line 95) does not store a project context. Fix: add `self._project_id` to the constructor and forward it at each call site, or derive it from the current graph state before each invocation.

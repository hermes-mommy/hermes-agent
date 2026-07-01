# P19 Research: P20 Life-Kernel Dependency Map

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** Every dependency between P19 Multi-Project Context and the P20 Living Autonomy Kernel.

> **HISTORICAL / SUPERSEDED BY P20 WAIVER (2026-06-25):** This research was authored when P20 was in "PRODUCTION PASS HOLD (soak)". References below to "P20 PRODUCTION PASS", "wait until P20 PRODUCTION PASS", "BLOCKED until P20 PRODUCTION PASS", and "LK-017" are **historical context**. P20's final status is `P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK`; the P20 axis is **satisfied by operator waiver**, not by a soak. P19 waves touching P20 production files are held **by operator discretion**, not by a pending P20 gate. See `docs/setup-evidence/P19/evidence/p20-waiver-gate-sync.md`. The body is retained unchanged for traceability.

---

## 1. Executive Summary

P20 is the Living Autonomy Kernel. It is currently in **PRODUCTION PASS HOLD** after a continuation deploy on 2026-06-25. P19 **MUST NOT** modify P20 files until P20 reaches PRODUCTION PASS. P19's design must be additive and non-interfering with P20's current soak.

P19 needs to make the life-kernel **project-aware** by threading `project_id` through state, models, graph, heartbeat, journal, dashboard, sensors, and decision context — while keeping HARD STOP global.

---

## 2. Life-Kernel Module Inventory

### 2.1 `state.py`
- **Purpose:** TypedDict state schemas and reducers.
- **Key types:** `LifeMindPhase`, `Priority`, `LifeMindState`, `SessionState`.
- **Project awareness:** None.
- **P19 injection:** Add `project_id: str` to `LifeMindState`; all reducers read it.

### 2.2 `models.py`
- **Purpose:** SQLAlchemy persistence models.
- **Tables:**
  - `life_kernel.life_mind_state`
  - `life_kernel.heartbeat_record`
  - `life_kernel.domain_mind_state`
- **Project awareness:** None.
- **P19 injection:** Add `project_id` column to each; change `DomainMindState.domain` unique constraint to `(project_id, domain)`.

### 2.3 `graph.py`
- **Purpose:** Main 4-node (observe/decide/act/reflect/idle) LangGraph.
- **Global state:** `_ADAPTERS: dict[str, Any] = {"kg": None, "memory": None, "journal": None}` at `graph.py:33`.
- **Project awareness:** None.
- **P19 injection:** Add `project_id` to `create_life_mind_graph(..., project_id)` and to state; scope recall/adapters by project.

### 2.4 `heartbeat.py`
- **Purpose:** 6-interval autonomous heartbeat + safety loop.
- **Global state:** Uses hardcoded `thread_id="heartbeat"` in 5 places (`heartbeat.py:302, 341, 365, 446, 629`).
- **HARD STOP:** `life_kernel:hard_stop` (global, must stay global).
- **Project awareness:** None.
- **P19 injection:** Use `thread_id=f"heartbeat-{project_id}"`; run one heartbeat loop per active project OR single loop that iterates over projects.

### 2.5 `cognition.py`
- **Purpose:** 6 background cognition loops feeding observations into the graph.
- **Project awareness:** None; takes `graph_config` with `thread_id`.
- **P19 injection:** Pass `project_id` in `graph_config`; optionally run one BackgroundCognition per project.

### 2.6 `sensors.py`
- **Purpose:** Sensor registry and bulk polling.
- **Project awareness:** None.
- **P19 injection:** Optionally scope `SensorRegistry` per project, or pass `project_id` to each `sense()` call.

### 2.7 `journal.py`
- **Purpose:** Reflective journal writer.
- **Project awareness:** None.
- **P19 injection:** Add `project_id` to entry dict before `record()`.

### 2.8 `dashboard.py` + `dashboard_writer.py`
- **Purpose:** Render state to Discord embeds; edit single dashboard message in place.
- **Redis key:** `life_kernel:dashboard_message_id` (global).
- **Project awareness:** None.
- **P19 injection:**
  - Add `project_id` to state.
  - Use `life_kernel:dashboard_message_id:{project_id}`.
  - Render per-project dashboard (or tabs within one message).

### 2.9 `log_channel.py` + `log_writer.py`
- **Purpose:** Append-only lifecycle log channel.
- **Project awareness:** None.
- **P19 injection:** Add `project_id` prefix to log line; per-project log channel or single channel with project tag.

### 2.10 `decision_context.py`
- **Purpose:** P16/P18 context builder (memory + KG recall).
- **Project awareness:** None.
- **P19 injection:** Pass `project_id` to `build()`; inject per-project `kg_adapter`/`memory_adapter` or filter recall by project.

### 2.11 `session_graph.py`
- **Purpose:** Per-session SDLC subgraph.
- **Project awareness:** `session_id` only; session != project.
- **P19 injection:** Add `project_id` to `SessionGraph`; use `session-{project_id}-{session_id}-{uuid}` thread_id; project-aware `SessionWorktree` path.

### 2.12 `hermes_brain.py`
- **Purpose:** LLM brain bridge for autonomous reasoning.
- **Project awareness:** None.
- **P19 injection:** Pass `project_id` to context if brain needs per-project memory (likely via injected adapters).

### 2.13 `checkpoint.py`
- **Purpose:** Postgres/Redis checkpointer factories.
- **Project awareness:** None.
- **P19 injection:** No direct change needed if thread_id already encodes project.

### 2.14 `self_improve.py`
- **Purpose:** Reflection, improvement candidates, regression gates.
- **Project awareness:** `loop_id` derived from `thread_id`.
- **P19 injection:** Pass `project_id` into candidate tracking; scope improvement candidates per project.

### 2.15 `redis_client.py`
- **Purpose:** Redis client factory + world-state cache helpers.
- **Redis key prefix:** `life_kernel:world:{key}`.
- **Project awareness:** None.
- **P19 injection:** Use `life_kernel:{project_id}:world:{key}` or pass project-scoped Redis client.

### 2.16 `discord_rest_client.py`
- **Purpose:** Outbound Discord REST publisher.
- **Project awareness:** None.
- **P19 injection:** Channel IDs are passed per call; simply pass per-project channel IDs.

### 2.17 `p16_adapter.py` / `p18_adapter.py`
- **Purpose:** Recall adapters for KG and memory.
- **Project awareness:** None. Memory recall hardcodes `principal="guinevere_core"`.
- **P19 injection:** Add `project_id` to `recall()` or inject per-project KG/memory clients.

### 2.18 `domain_minds/*.py`
- **Purpose:** Email/Finance/Engineer minds + durability (PostgresAuditJournal).
- **Project awareness:** None.
- **P19 injection:** Add `project_id` to audit journal entries and domain mind state.

### 2.19 `sensor_adapters/*.py`
- **Purpose:** Placeholder sensor adapters.
- **Project awareness:** None.
- **P19 injection:** Add `project_id` to observation payload.

---

## 3. Current Redis Keys in life_kernel

| Key | Current | P19 Design |
|---|---|---|
| `life_kernel:hard_stop` | Global, checked every 1s | **STAY GLOBAL** |
| `life_kernel:dashboard_message_id` | Global single dashboard | `life_kernel:dashboard_message_id:{project_id}` |
| `life_kernel:world:{key}` | Global world state cache | `life_kernel:{project_id}:world:{key}` |

---

## 4. Current DB Tables in life_kernel

| Table | Columns | P19 Design |
|---|---|---|
| `life_kernel.life_mind_state` | id, phase, is_active, observations, goals, commitments, concerns, decision_context, last_heartbeat, updated_at | + `project_id` (FK or text) |
| `life_kernel.heartbeat_record` | id, heartbeat_type, success, latency_ms, recorded_at | + `project_id` |
| `life_kernel.domain_mind_state` | id, domain, state_json, is_active, last_run, run_count, error_count | + `project_id`, unique `(project_id, domain)` |
| `life_kernel.audit_journal` | id, source, entry, recorded_at | + `project_id` in entry or column |

---

## 5. Heartbeat Project-Awareness Strategy

### 5.1 Option A: One Heartbeat Loop Per Project
- Run N heartbeat loops concurrently (one per active project).
- Each loop uses `thread_id=f"heartbeat-{project_id}"`.
- Pros: Clean isolation, simple per-project state.
- Cons: N loops, resource overhead.

### 5.2 Option B: Single Loop Iterates Over Projects
- One heartbeat loop maintains a list of active projects.
- Each tick dispatches per-project observe/decide/act/reflect cycles.
- Pros: Single loop, less overhead.
- Cons: More complex scheduling, single point of failure.

### 5.3 Recommendation
**Option A for now** (one heartbeat per project, up to a bounded number of active projects). It matches the existing heartbeat design and provides cleaner isolation. Option B can be evaluated later if resource overhead becomes a concern.

---

## 6. Graph Thread-ID Strategy

LangGraph checkpointer uses `thread_id` as the isolation key. P19 should encode project into thread IDs:

- `heartbeat`: `heartbeat-{project_id}`
- `session`: `session-{project_id}-{session_id}-{uuid}`
- `cognition`: `cognition-{project_id}`
- `self_improve`: `self_improve-{project_id}`

This avoids touching the checkpointer implementation.

---

## 7. What Must Stay Global

HARD STOP (`life_kernel:hard_stop`) must remain global across all projects. It is a persona-level safety override, not a project-local feature.

Other global invariants:
- Persona state (mood, yandere, punishment, distress, safe mode)
- Consent ledger (with per-project scope, but global safety scopes like persona/normal/escalated/y5)
- Safe-mode controller
- Drift rollback targets
- ADRs and governance policies

---

## 8. What Must Be Per-Project

- Life-mind state (`LifeMindState`, `LifeMindStateModel`)
- Heartbeat records
- Domain mind state
- Audit journal entries
- Journal reflective entries
- Dashboard messages
- Log channel messages
- Redis world-state cache
- Memory recall/store
- KG recall/store
- Sensor observations
- Decision context
- Session graph threads
- Self-improvement candidates

---

## 9. Migration Path for Existing State

1. Add nullable `project_id` to all life_kernel tables.
2. Backfill `project_id = 'default'` for all existing rows.
3. Add composite unique indexes (e.g., `(project_id, domain)`).
4. Add `projects.project_registry` seed row for `default` project.
5. Update application code to always write `project_id`.
6. Make `project_id` NOT NULL after backfill.

This must wait until **P20 PRODUCTION PASS**.

---

## 10. Non-Interference Contract with P20

P19 must not change the following P20 files during P20's soak:
- `src/life_kernel/heartbeat.py` (HARD STOP loop semantics)
- `src/core/services/hard_stop_handler.py` (HARD STOP handler)
- `src/life_kernel/graph.py` (graph topology)
- `src/life_kernel/hermes_brain.py` (brain interface)
- `src/life_kernel/adapter_factory.py` (adapter wiring)

P19 CAN make additive-only changes to P20 files after P20 PRODUCTION PASS, such as:
- Adding `NotRequired[Optional[str]]` `project_id` to `LifeMindState` (additive, default absent).
- Adding `project_id` column to P20 DB models (via migration, not code).
- Adding project-aware Redis key variants alongside existing global keys.

---

## 11. P19-to-P20 Dependency Ordering

```text
P19-001 governance + ADR
P19-002 project registry/domain models
P19-003 DB schema + migrations  → adds project_id columns (additive)
P19-004 memory/KG namespace partition
P19-005 P20 life-kernel project context propagation  → touches P20 files (BLOCKED until P20 PRODUCTION PASS)
P19-006 project-aware sensors and actions
P19-007 Discord dashboard/log/project switcher
P19-008 project-aware agent/session orchestration
P19-009 consent/surveillance scoped policy enforcement
P19-010 observability/audit/evidence integration
P19-011 migration/backfill from existing unscoped state
P19-012 deploy/canary/rollback/soak
```

---

## 12. Conclusion

P19 must make the P20 Living Autonomy Kernel project-aware by threading `project_id` through state, models, graph, heartbeat, journal, dashboard, sensors, and decision context. All changes must be additive and non-interfering with the current P20 soak. The implementation is gated on P20 PRODUCTION PASS.

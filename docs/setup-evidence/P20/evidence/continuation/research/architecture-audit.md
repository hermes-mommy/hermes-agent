---
title: "P20 Living Autonomy Kernel — Architecture Audit"
status: "Completed"
date: "2026-06-24"
auditor: "Guinevere"
scope: "src/life_kernel/"
---

# P20 Living Autonomy Kernel — Architecture Audit

## Executive Verdict

The life kernel is **not merely health-check loops**, but it is also **not yet a fully autonomous agent**. It is a real LangGraph StateGraph runtime with checkpointing, a heartbeat scheduler, LLM-enriched decision nodes, and pluggable memory/KG recall. However, several key paths remain placeholder stubs that must be strengthened before "genuine living autonomy" can be claimed.

---

## 1. Global Life-Mind Graph (`src/life_kernel/graph.py`)

### Graph Structure

Real LangGraph `StateGraph(LifeMindState)` with 5 nodes and conditional edges:

```
START → observe → decide → [act → reflect → END]
                          → [idle → END]
                          → [END (hard_stop)]
```

| Node | Purpose | Real vs Placeholder |
|---|---|---|
| `observe` | Reads state, recalls KG/P18 concepts/memories, builds decision context, sets `world_model_status` | **Real** — adapter-driven recall with fail-soft |
| `decide` | Static priority engine + optional Hermes LLM override | **Real skeleton** — static logic solid; LLM wrapper is thin |
| `act` | Selects highest-priority goal, increments counters, proposes next action | **Partially real** — goal selection is real; execution is display-only |
| `reflect` | Writes audit entry, journal entry via journal writer, anomaly detection | **Real** — journal integration present |
| `idle` | Creates self-directed goal from recalled context or deterministic fallback | **Real** — seeds real `state.goals` |

### Edges

- `START → observe`
- `observe → decide`
- `decide → act / reflect / idle / END` (conditional on `state.decision`)
- `act → reflect → END`
- `idle → END`

### Key Observations

- Uses `LifeMindState` TypedDict with `Annotated` reducers (`add_observations_reducer`, `add_audit_reducer`, `add_journal_reducer`).
- Adapters (KG, memory, journal) are held in a module-level `_ADAPTERS` registry because LangGraph checkpoints state as JSON and cannot serialize live objects.
- Optional LLM-enriched variants (`_make_brain_decide`, `_make_brain_act`, `_make_brain_idle`) wrap static nodes and call `hermes_brain.think()` with a hard timeout and fallback.
- HARD STOP is enforced in the static `decide_node` before any LLM is consulted.

### Verdict

**Real LangGraph runtime with checkpointing support.** The graph is a genuine state machine, not just async tasks.

---

## 2. Heartbeat Service (`src/life_kernel/heartbeat.py`)

The heartbeat is the autonomous clock. It runs 6 asyncio loops:

| Interval | Handler | Current Behavior |
|---|---|---|
| 1s | `_heartbeat_1s` | **Real** — checks Redis `life_kernel:hard_stop`, invokes graph, publishes dashboard, stops service on HARD STOP, recovers stale checkpoint state |
| 10s | `_heartbeat_10s` | **Placeholder** — logs graph health check, no stuck detection implemented |
| 30s | `_heartbeat_30s` | **Placeholder** — logs awareness refresh, no real sensor polling |
| 60s | `_heartbeat_60s` | **Real** — invokes the life-mind graph (`graph.ainvoke`), updates dashboard, throttled lifecycle log |
| 5m | `_heartbeat_5m` | **Placeholder** — logs deep scan, no domain mind scanning |
| 1h | `_heartbeat_1h` | **Partially real** — runs `ReflectionEvaluator`/`ImprovementTracker`, generates display-only self-improvement candidates |

### Key Observations

- Heartbeat re-invokes the graph every 60 seconds with `thread_id="heartbeat"`.
- State persists between invocations via LangGraph checkpointer.
- 1s loop is the safety-critical path; 60s loop is the decision path.
- Most non-1s/60s handlers are placeholder comments awaiting LK-011 through LK-016.

### Verdict

**Real scheduler + safety loop, but most awareness loops are placeholders.**

---

## 3. Hermes Brain Bridge (`src/life_kernel/hermes_brain.py`)

### Does it call `AIAgent.run_conversation()`?

**Yes.**

```python
result: dict[str, Any] = await asyncio.to_thread(
    self.agent.run_conversation,
    user_message=user_message,
    system_message=system_prompt,
    conversation_history=history,
)
```

- `HermesBrain` lazily imports `AIAgent` from `run_agent`.
- It configures the agent with memory enabled, context files enabled, and toolsets `core` + `web`.
- Disabled toolsets: `dangerous`, `system`.
- Validates required response fields (`final_response`, token counts, cost).
- Returns a safe fallback dict on any exception so the kernel never stalls.

### Verdict

**Real Hermes/AIAgent integration.** The brain bridge is the genuine LLM reasoning layer for the kernel.

---

## 4. World Model (`state.py` / `p16_adapter.py` / `p18_adapter.py` / `decision_context.py`)

There is no `world_model.py`. World state is represented as fields on `LifeMindState`:

- `world_model_status`: `"active"`, `"degraded"`, or `"unavailable"`
- `recalled_concepts`: P16 KG concepts
- `recalled_memories`: P18 episodic memories
- `decision_context`: enriched context from `DecisionContextBuilder`

### Adapter Realness

| Adapter | File | Behavior |
|---|---|---|
| `KGRecallAdapter` | `p16_adapter.py` | Real wrapper around injected `kg_client`; normalizes concept results; degrades gracefully |
| `MemoryRecallAdapter` | `p18_adapter.py` | Real wrapper around injected `memory_client`; normalizes memory results; degrades gracefully |
| `DecisionContextBuilder` | `decision_context.py` | Combines KG + memory signals concurrently into a context dict |

### Verdict

**Real world-model substrate** (P16 + P18 recall), but it is adapter-level, not a standalone world-model module. It is not a placeholder, but it is thin.

---

## 5. Per-Session Autonomy (`src/life_kernel/session_graph.py`)

Real LangGraph subgraph for per-session SDLC:

```
START → plan → execute → validate → [audit → document → complete → END]
                              ↓
                          execute (loop on failure)
```

| Node | Purpose |
|---|---|
| `plan` | Marks session READY |
| `execute` | Transitions EXECUTING → COMPLETED |
| `validate` | Validation gate, can force re-run |
| `audit` | Placeholder auditor gate |
| `document` | Placeholder documentation sync |
| `complete` | Finalizes session |

Also includes placeholder helpers:
- `SessionWorktree` — records git worktree intent
- `SessionProfileManager` — in-memory session profile store
- `DiscordThreadManager` — records Discord thread intent

### Verdict

**Real per-session LangGraph skeleton with SDLC routing, but execution engine and persistence are placeholders.**

---

## 6. Background Cognition (`src/life_kernel/cognition.py`)

`BackgroundCognition` manages 6 independent asyncio loops:

| Loop | Interval | Current Behavior |
|---|---|---|
| `observer` | 10s | Polls `SensorRegistry.sense_all()` if provided; otherwise placeholder |
| `memory` | 5m | Placeholder |
| `critic` | 5m | Placeholder (Hermes available but not called) |
| `curiosity` | 1h | Placeholder (Hermes available but not called) |
| `self_improvement` | 1h | Placeholder |
| `guardian` | 10s | Placeholder safety boundary check |

### Write Serialization

- All loops enqueue observations to a shared `asyncio.Queue`.
- A single `_write_loop` drains the queue and invokes `graph.ainvoke` serially.
- This prevents concurrent graph writes.

### Verdict

**Real background loop orchestration and write serialization, but loop bodies are almost entirely placeholder.**

---

## 7. Daily-Life Sensors (`src/life_kernel/sensors.py` + `sensor_adapters/`)

`SensorRegistry` is real:

- `register(name, adapter)` / `unregister(name)` with `asyncio.Lock`
- `sense_all()` — concurrently calls `sense()` on all adapters, skips failures
- `health_check()` — concurrently checks adapter health

`BaseSensorAdapter` provides the abstract base:
- `sense()` returns a placeholder observation
- `health()` returns `True` by default

Concrete adapters exist but extend the placeholder base:
- `BrowserSensorAdapter`
- `DiscordSensorAdapter`
- `FinanceSensorAdapter`
- `GmailSensorAdapter`
- `RepoSensorAdapter`
- `SurveillanceSensorAdapter`
- `VPSSensorAdapter`
- `WearableSensorAdapter`

### Verdict

**Real sensor registry and protocol, but concrete adapters are placeholder stubs.**

---

## 8. Discord Dashboard (`src/life_kernel/dashboard.py`)

`DashboardRenderer` is real and production-ready:

- Renders `LifeMindState` to markdown dashboard.
- Renders compact single-line status.
- Renders Discord embed JSON with fields: status, mode, focus, last decision, next action, current agenda, memory, uptime, cycles.
- SHA-256 checksum caching to avoid re-rendering unchanged state.
- Secret redaction for API keys, bearer tokens, credentials.

Separate `DashboardWriter` (in `dashboard_writer.py`) handles edit-not-spam Discord updates.

### Verdict

**Real dashboard renderer with safety-aware output sanitization.**

---

## 9. Public Exports (`src/life_kernel/__init__.py`)

Exports include:

- Graph: `create_life_mind_graph`
- State: `LifeMindState`, `SessionState`, `LifeMindPhase`, `Priority`, reducers
- Heartbeat: `HeartbeatService`, `HeartbeatInterval`
- Brain: `HermesBrain`, `HermesBrainConfig`
- Cognition: `BackgroundCognition`
- Sensors: `SensorRegistry`, all sensor adapters, `BaseSensorAdapter`
- Checkpoints: `create_postgres_checkpointer`, `create_redis_checkpointer`
- Memory/KG: `MemoryRecallAdapter`, `KGRecallAdapter`
- Domain minds: `EngineerMind`, `FinanceMind`, `EmailMind`, `DeployBackend`, etc.
- Self-improvement: `ReflectionEvaluator`, `ImprovementTracker`, etc.
- Session: `SessionGraph`, `SessionProfileManager`, etc.
- Log/Dashboard: `DashboardRenderer`, `DashboardWriter`, `LogChannel`, `DiscordLogChannel`

### Verdict

**Comprehensive public surface.** The kernel is intended to be a full framework.

---

## 10. LLMRouter Usage Search

Search scope: `src/life_kernel/`

| File | Line | Context |
|---|---|---|
| `graph.py` | 874 | Docstring comment: "never raw `LLMRouter.chat`" |

**No actual `LLMRouter` import or invocation was found.** The only mention is a safety comment explicitly rejecting its use.

### Verdict

**No hard-rejection violation.** Life kernel does not use `LLMRouter`.

---

## Runtime Flow Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HeartbeatService                           │
│  1s loop ── HARD STOP check + recovery                             │
│ 10s loop ── graph health (placeholder)                             │
│ 30s loop ── awareness refresh (placeholder)                        │
│ 60s loop ── graph.ainvoke(decision signal) + dashboard update      │
│  5m loop ── deep scan (placeholder)                                │
│  1h loop ── reflection / self-improvement candidates               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    create_life_mind_graph()                          │
│  observe ──► decide ──► act ──► reflect ──► END                     │
│              │          │                                          │
│              └─────► idle ─────────────────► END                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              BackgroundCognition (6 parallel loops)                  │
│  observer, memory, critic, curiosity, self_improvement, guardian    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Strengths

1. **Real LangGraph foundation** — typed state, reducers, checkpointing.
2. **Safety-first HARD STOP** — non-LLM, Redis-backed, with stale-state recovery.
3. **Hermes brain integration** — calls `AIAgent.run_conversation()` with timeout and fallback.
4. **Fail-soft throughout** — adapters, brain, heartbeat all degrade gracefully.
5. **Sensor registry + background cognition scaffolding** — ready for real sensors.
6. **Dashboard with secret redaction** — production-safe Discord output.
7. **No LLMRouter usage** — consistent with plan.

---

## Weaknesses / Architectural Debt

1. **Most heartbeat non-1s/60s handlers are placeholders.**
2. **Background cognition loop bodies are placeholders.** Hermes is available to critic/curiosity but never called.
3. **Concrete sensor adapters are placeholders.** No real API polling yet.
4. **`act_node` is display-only.** It does not execute engineering tasks or delegate to domain minds.
5. **`EngineerMind` deploy subgraph is intent-only unless a backend is injected.**
6. **`BackgroundCognition` writes observations directly into graph state, but there is no prioritization/merge logic beyond appending.**
7. **No evidence that domain minds (`EngineerMind`, `FinanceMind`, etc.) are invoked from the main life-mind graph.**
8. **`SessionGraph` is isolated; integration with the global life-mind graph is not visible.**

---

## Recommendations for Strengthening

1. **Instrument heartbeat 10s/30s/5m placeholders** — add stuck-detection, real sensor refresh, and domain-mind anomaly scanning.
2. **Make background loops real** — wire critic/curiosity to Hermes with cost throttling; implement real guardian checks.
3. **Replace placeholder sensor adapters** with live integrations (Discord, Gmail, finance, VPS, surveillance, wearable, browser, repo).
4. **Connect `act_node` to domain minds** so the kernel can actually execute engineering/comms/finance tasks.
5. **Add a task queue / work planner** between `decide` and `act` to prevent goal thrashing.
6. **Integrate `SessionGraph` into the global graph** so per-session SDLC cycles are driven by the life-mind.
7. **Add end-to-end tests** that run the heartbeat + graph + background cognition together.

---

## Conclusion

The P20 Living Autonomy Kernel has a **genuine LangGraph-based autonomous core** with real checkpointing, a real heartbeat, a real Hermes brain bridge, and a real memory/KG world-model substrate. It is **considerably more than health-check loops**. However, the **outer autonomous behaviors** (background cognition, sensors, domain-mind execution, deep scans) are still mostly placeholder scaffolding. Strengthening these placeholders is the highest-value next step toward a truly living/autonomous system.

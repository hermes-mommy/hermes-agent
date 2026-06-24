# Life Kernel Architecture Audit Report

**Agent:** life_kernel architecture auditor  
**Date:** 2026-06-24  
**Scope:** `src/life_kernel/` full source analysis  
**Vision:** P20 Living Autonomy Kernel — 24/7 autonomous AI companion with Discord-visible autonomy

---

## 1. Executive Summary

The life kernel implements a LangGraph StateGraph with 5 nodes (`observe → decide → act/reflect/idle → END`) driven by a 6-interval heartbeat service. The graph topology is sound: `observe` feeds `decide`, which conditionally routes to `act`, `reflect`, or `idle`, each of which terminates at `END`. The heartbeat re-invokes every 60s. Discord dashboard and log channels are live and working (Option B REST publisher, not discord.py gateway).

**Four major architecture-level gaps** prevent the kernel from satisfying its vision requirements:

1. **Empty-state trap (AC-LIFE-002):** `decide_node` routes to `"idle"` whenever the state has zero goals, zero commitments, and zero concerns (`graph.py:240-242`). Since the kernel starts with no items in any of these lists, the brain NEVER gets to choose `act`/`reflect`/`initiative` — Guinevere is trapped in an idle-only loop until an external agent populates goals.

2. **Brain-enriched idle never creates real state (AC-LIFE-002):** The `_make_brain_idle` wrapper (`graph.py:604-636`) enriches the `description` field of the idle observation but NEVER creates a real `goal` or `commitment` in the LifeMindState. The "self-directed task" is a display-only label — it appears on the dashboard but the kernel's state remains empty, so the next cycle routes to idle again.

3. **reflect_node never writes journal entries (AC-LIFE-008):** `reflect_node` (`graph.py:347-432`) creates an `audit_entry` dict in local scope and appends it to the `audit_entries` list via LangGraph reducer, but it NEVER writes to a persistent journal, calls `PostgresAuditJournal` (which exists at `domain_minds/durability.py:44`), or creates a memory entry. The "memory placeholder" at line 403 is a `logger.debug` call with no side effect.

4. **Self-improvement candidate generation is unwired (AC-LIFE-009):** `self_improve.py` defines `ReflectionEvaluator`, `ImprovementTracker`, `RegressionGate` — fully implemented classes with heuristics and a test-command regression gate. But NOTHING in the graph, heartbeat, or cognition loops calls `evaluate_and_propose()`. The `BackgroundCognition.self_improvement` loop (`cognition.py:376-388`) writes a placeholder string observation and does nothing real.

Additionally, `DecisionContextBuilder` (`decision_context.py:23-99`) is correctly structured to combine KG and memory signals, but `p16_adapter.py` and `p18_adapter.py` return deterministic mock data (`_placeholder: True`), and the adapters are NEVER injected into the kernel's state at startup — `graph.py:160-168` shows the fallback path `{"p16_available": False, "p18_available": False, ...}` executes every time because `kg_adapter` and `memory_adapter` are not wired in any init/entrypoint.

---

## 2. Current State Evidence

### 2.1 Graph Topology

**File:** `src/life_kernel/graph.py`

```
START → observe → decide → route_from_decide ──┬──→ act → reflect → END
                                                ├──→ idle → END
                                                └──→ reflect → END
                                                └──→ END (unknown decision)
```

- `recursion_limit=25` (`heartbeat.py:466`, `cognition.py:248`).
- Checkpointer wired via Postgres or Redis (`checkpoint.py`).
- Brain-enriched variants: `_make_brain_decide` (line 528), `_make_brain_act` (line 564), `_make_brain_idle` (line 604).
- Static fallback nodes: `decide_node` (line 175), `act_node` (line 256), `idle_node` (line 435).

### 2.2 The Empty-State Trap

At `graph.py:240-242`:

```python
if len(state.get("goals", [])) == 0 and len(state.get("commitments", [])) == 0 and len(state.get("concerns", [])) == 0:
    logger.info("no active goals, commitments, or concerns - routing to idle for self-directed tasks")
    return {"decision": "idle"}
```

This is BEFORE the brain enrichment check in `_make_brain_decide` (line 542: `if result.get("decision") != "idle": return result`). The `_make_brain_decide` wrapper explicitly says it "only augment(s) the idle branch" — but `decide_node` already returned `"idle"` on its own. The brain then receives an empty context (goals=[], commitments=[], concerns=[]) and is asked "Decide the next phase: act, reflect, idle, or observe." Even if the brain says "act", `_normalize_decision` maps it to a valid token and `graph.py:555-557` would set `result["decision"] = brain_decision`. **BUT** the brain cannot act meaningfully because there are zero goals/commitments/concerns in state. The `act_node` at line 576-579 checks `if not goals` and returns "no active goals — idle cycle". So even if the brain routes to `act`, the act node produces nothing.

**Verdict:** Guinevere's kernel is structurally trapped in idle until goals are injected from outside. This violates AC-LIFE-002 ("creates at least one self-directed task").

### 2.3 Brain-Enriched Idle Is Display-Only

At `graph.py:604-636`:

```python
async def brain_idle(state):
    result = await idle_node(state)  # static: appends a random-choice observation
    proposal = await _safe_think(hermes_brain, user_msg, _IDLE_SYSTEM_PROMPT)
    if proposal:
        result["last_autonomous_decision"] = "self-directed task"
        result["next_planned_action"] = proposal[:200]
        observations = result.get("observations", [])
        if observations:
            observations[0] = {
                **observations[0],
                "description": proposal[:200],
                "brain_generated": True,
            }
    return result
```

The brain's proposal is stuffed into the observation's `description` field and into `next_planned_action` for the dashboard. It does NOT create a goal or commitment in `LifeMindState.goals[]` or `LifeMindState.commitments[]`. So the next 60s heartbeat cycle finds the state still empty, `decide_node` routes to `"idle"` again, and the cycle repeats with a dashboard shimmer but zero progress.

**Verdict:** The dashboard shows "self-directed task: ..." but it is purely cosmetic. No real goal is created.

### 2.4 reflect_node Has No Persistent Journal

At `graph.py:388-431`:

```python
audit_entry: dict[str, Any] = {
    "phase": "reflect",
    "timestamp": datetime.now().isoformat(),
    "cycle": cycle_count,
    "act_count": act_count,
    "n_observations": len(observations),
    "has_errors": has_errors,
    "is_active": state.get("is_active", False),
}
audit_entries = [audit_entry]

# Generate memory placeholder for LK-010 integration
logger.debug("reflect_node_memory_placeholder")
```

The `audit_entry` is appended to the LangGraph state's `audit_entries` list (which has a 500-entry cap via `add_audit_reducer`). But it NEVER calls `PostgresAuditJournal.record()`, never writes to a file, and never creates a memory entry via `src.memory.read_pipeline`. The "memory placeholder" is literally a `logger.debug` call (line 403). AC-LIFE-008 requires journaling; this is not satisfied.

### 2.5 Self-Improvement Candidate Generation Is Unwired

**File:** `src/life_kernel/self_improve.py`

- `ReflectionEvaluator.evaluate()` (line 128) — heuristics exist: error threshold > 3, low efficiency, idle > 1h, obs near cap.
- `ImprovementTracker` (line 366) — in-memory candidate store with `propose()`, `list_by_status()`, `get()`, `evaluate_and_propose()`.
- `RegressionGate` (line 264) — runs `pytest` via subprocess, promotes/rejects candidates.

**None of these are called anywhere except in tests.** The `_heartbeat_1h` at `heartbeat.py:551-571` is:

```python
async def _heartbeat_1h(self):
    logger.debug("heartbeat_1h_reflection")
    # Placeholder: Reflection + memory consolidation + self-improvement
    # Future: Call reflection node, consolidate memory, evaluate self-improvement candidates
```

The `BackgroundCognition.self_improvement` loop at `cognition.py:376-388` writes a single placeholder string observation to the graph and does nothing else.

### 2.6 DecisionContextBuilder Is Structurally Present but Never Injected

**File:** `src/life_kernel/graph.py:158-170`

```python
try:
    kg_adapter = state.get("kg_adapter")  # injected via config/context
    memory_adapter = state.get("memory_adapter")
    if kg_adapter and memory_adapter:
        from src.life_kernel.decision_context import DecisionContextBuilder
        builder = DecisionContextBuilder(kg_adapter=kg_adapter, memory_adapter=memory_adapter)
        decision_context = await builder.build(state)
    else:
        decision_context = {"p16_available": False, "p18_available": False, ...}
except Exception:
    decision_context = {"p16_available": False, "p18_available": False, ...}
```

The `else` branch always fires because `kg_adapter` and `memory_adapter` are state fields that require explicit injection into the initial state before `graph.ainvoke`. No entry point (no CLI, no FastAPI lifespan, no config loader) sets these. The adapters themselves (`p16_adapter.py`, `p18_adapter.py`) return `_placeholder: True` anyway, so even if injected, the result would be mock data.

The real substrates exist and work:
- `src/knowledge_graph/query/context.py` — `RecallContextAssembler` (full pipeline)
- `src/memory/read_pipeline.py:755` — `recall_memories()` (async, returns `RecallResults`)

But neither is connected to the kernel.

### 2.7 Heartbeats 10s/30s/5m/1h Are Stubs

| Interval | File:Line | Status |
|----------|-----------|--------|
| 1s | `heartbeat.py:254` | **Live** — HARD STOP detection + recovery |
| 10s | `heartbeat.py:373` | **Stub** — `logger.debug` + commented-out pass |
| 30s | `heartbeat.py:400` | **Stub** — `logger.debug` only |
| 60s | `heartbeat.py:421` | **Live** — graph invoke + dashboard publish |
| 5m | `heartbeat.py:530` | **Stub** — `logger.debug` only |
| 1h | `heartbeat.py:551` | **Stub** — `logger.debug` only |

### 2.8 Sensor Adapters Are All Placeholders

Every adapter in `sensor_adapters/` inherits from `BaseSensorAdapter` (`base.py:17`) which returns:

```python
[{"source": "sensor:discord", "type": "message",
  "content": "Discord API polling placeholder — ...",
  "timestamp": ..., "additional": {}}]
```

No adapter calls a real external API. The `BackgroundCognition.observer` loop at `cognition.py:296-326` checks for `SensorRegistry` and falls back to a placeholder observation.

---

## 3. Gap Table

| ID | Severity | Title | Current State | Required State | Files | Vision Ref |
|----|----------|-------|---------------|----------------|-------|------------|
| GAP-1 | **critical** | Empty-state trap prevents any real autonomy | `decide_node` routes to `"idle"` when goals/commitments/concerns are all empty (`graph.py:240-242`) | Kernel must create goals from memory recall or world context when state is empty, or route to `act`/`initiative` node that seeds goals | `graph.py` | AC-LIFE-002 |
| GAP-2 | **critical** | Brain-enriched idle creates display-only labels, not real tasks | `_make_brain_idle` enriches `description` field but never creates a `goal` or `commitment` in state (`graph.py:614-636`) | Brain-generated self-directed task must create a real `goal` or `commitment` in `LifeMindState.goals[]` | `graph.py` | AC-LIFE-002 |
| GAP-3 | **high** | reflect_node has no persistent journal | `reflect_node` appends audit entries to in-memory reducer only, never writes to `PostgresAuditJournal` (`graph.py:388-432`, `self_improve.py`) | `reflect_node` must write to `PostgresAuditJournal` after each cycle | `graph.py`, `domain_minds/durability.py` | AC-LIFE-008 |
| GAP-4 | **high** | Self-improvement pipeline unwired | `ReflectionEvaluator`, `ImprovementTracker`, `RegressionGate` exist but are never called (`self_improve.py`, `heartbeat.py:566-567`) | `_heartbeat_1h` or `BackgroundCognition.self_improvement` must invoke `ReflectionEvaluator.evaluate()` and `ImprovementTracker.evaluate_and_propose()` | `heartbeat.py`, `cognition.py`, `self_improve.py` | AC-LIFE-009 |
| GAP-5 | **high** | DecisionContextBuilder adapters never injected | `kg_adapter` and `memory_adapter` are not set in any entrypoint, so `decision_context` is always `{"p16_available": False, ...}` (`graph.py:158-170`) | Entrypoint must inject real `KGRecallAdapter` and `MemoryRecallAdapter` (or a real KG query + memory recall client) into initial state | `graph.py`, entrypoint/module | LK-010 |
| GAP-6 | **high** | P16/P18 adapters return mock data | `p16_adapter.py:58-98` returns hardcoded mock concepts with `_placeholder: True`; same for `p18_adapter.py` | Adapters must call real `src.knowledge_graph.query` and `src.memory.read_pipeline.recall_memories` | `p16_adapter.py`, `p18_adapter.py` | LK-010 |
| GAP-7 | **medium** | Heartbeat 10s/30s/5m/1h are no-ops | These methods log only and have no real logic (`heartbeat.py:373-571`) | Each should perform its intended function (stuck detection, sensor poll, domain mind scan, reflection) | `heartbeat.py` | LK-011/015 |
| GAP-8 | **medium** | No self-directed goals ever created from memory recall | `idle_node` uses `random.choice()` over 3 hardcoded strings (`graph.py:463-468`) | `idle_node` should query memory for recent context and derive relevant micro-goals | `graph.py`, `p18_adapter.py` | AC-LIFE-002 |
| GAP-9 | **medium** | Brain never routes to act/reflect when goals exist | The `_make_brain_decide` only overrides the idle branch; for non-idle decisions the static engine is authoritative (`graph.py:542-543`) | Brain should be consulted for non-idle routing too, with static as fallback | `graph.py` | AC-LIFE-003 |

---

## 4. Risks

| Risk | Mitigation |
|------|------------|
| Brain-proposed idle goals are display-only; dashboard shows "autonomy" that is cosmetic | Create real `goal` entries in state from brain proposals before returning from `brain_idle`. The `LifeMindState.goals` reducer appends; add a new goal with auto-generated `goal_id` and `priority=IMPROVE_AUTONOMY` |
| Empty-state trap means first boot yields permanent idle loop | Seed initial goals from memory recall on first boot, or add a `seed_initial_goals()` call in the startup path that queries `recall_memories()` for recent context |
| `PostgresAuditJournal` inserts every cycle could fill the DB | Already handled: `add_audit_reducer` caps at 500 in-memory, and `PostgresAuditJournal` has no cap yet. Add a TTL or archival strategy |
| Recursion limit 25 may be too low for real use | Monitor `recursion_limit` hits in logs; increase to 50 if needed. But note: each `ainvoke` should complete one `observe→decide→(act|reflect|idle)→END` cycle, which is 2-4 node transitions |
| Brain `_safe_think` timeout (30s) could cause 60s heartbeat overlap | The 30s timeout is half the heartbeat interval, so a slow brain response won't overlap the next 60s cycle. Monitor for `hermes_brain_think_timeout` in logs |
| `run_conversation` is synchronous (`asyncio.to_thread`) — blocks event loop thread | Acceptable for current usage (one call per 60s cycle), but if more frequent brain calls are added, consider a worker thread pool |

---

## 5. Hard-Rejection Flags

**None.** No condition would fail a hard-rejection criteria if left unfixed. The kernel boots, cycles, publishes to Discord, detects HARD STOP, and recovers from stale state. The gaps affect *quality of autonomy* (the kernel stays alive but does not generate real goals or self-improve), not *operational safety* or *boot integrity*.

---

## 6. Concrete Recommendations for Implementation Phase

### Recommendation 1: Fix the Empty-State Trap (GAP-1, GAP-2, GAP-8)

In `_make_brain_idle`, after receiving the brain's proposal, create a real goal entry:

```python
# In brain_idle, after getting proposal:
if proposal:
    new_goal = {
        "goal_id": f"auto_{uuid4().hex[:12]}",
        "priority": Priority.IMPROVE_AUTONOMY,
        "description": proposal[:200],
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }
    # Append to state's goals list via the reducer
    result["goals"] = [new_goal]
```

This ensures the next `decide_node` cycle sees a goal in state and routes to `act` instead of `idle`.

### Recommendation 2: Wire reflect_node to PostgresAuditJournal (GAP-3, GAP-4)

In `reflect_node`, after building `audit_entry`, call:

```python
from src.life_kernel.domain_minds.durability import PostgresAuditJournal
journal = PostgresAuditJournal()
await journal.record({
    "source": "life_kernel:reflect",
    "phase": "reflect",
    "cycle": cycle_count,
    "act_count": act_count,
    "has_errors": has_errors,
    "timestamp": datetime.now().isoformat(),
})
```

### Recommendation 3: Wire the Self-Improvement Pipeline (GAP-4)

In `_heartbeat_1h`, instantiate `ReflectionEvaluator` with the compiled graph, call `evaluate(state)`, and pass results to `ImprovementTracker.evaluate_and_propose()`.

### Recommendation 4: Inject Real KG/Memory Adapters (GAP-5, GAP-6)

Create a startup function (called from `main()` or FastAPI lifespan) that:

1. Creates a SQLAlchemy `AsyncSession` for the Guinevere Postgres.
2. Instantiates `KGRecallAdapter(kg_client=KGQueryEngine(session))` that delegates to `src.knowledge_graph.query.context.RecallContextAssembler`.
3. Instantiates `MemoryRecallAdapter(memory_client=session)` that calls `src.memory.read_pipeline.recall_memories()`.
4. Passes both adapters into the initial state dict for `graph.ainvoke`.

### Recommendation 5: Enrich Brain-Enriched Decide for Non-Idle Branches (GAP-9)

Modify `_make_brain_decide` to also consult the brain when the static engine chose `act` or `reflect` (not just `idle`). The brain should validate or refine the decision, with the static decision as fallback.

### Priority Order for Implementation

1. **GAP-1 + GAP-2** (empty-state trap + display-only idle) — unlocks real autonomy
2. **GAP-5 + GAP-6** (inject real KG/memory) — enables memory-informed decisions
3. **GAP-3** (journal writes) — satisfies AC-LIFE-008 persistence requirement
4. **GAP-4** (self-improvement wiring) — satisfies AC-LIFE-009
5. **GAP-8** (memory-seeded idle goals) — makes idle meaningful
6. **GAP-7** (heartbeat stubs) — operational polish
7. **GAP-9** (brain-enriched non-idle routing) — enhances existing working path

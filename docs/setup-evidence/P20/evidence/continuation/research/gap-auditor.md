# P20 Plan-vs-Code Gap Audit Report

**Auditor:** P20 plan-vs-code gap auditor
**Date:** 2026-06-24
**Scope:** LK-001 through LK-017 acceptance criteria + AC-LIFE-001 through AC-LIFE-010 success criteria
**Evidence root:** `docs/setup-evidence/P20/evidence/continuation/research/gap-auditor.md`
**Reading:** Every claim below is grounded in a file:line citation from code read during this session.

---

## 1. Executive Summary

The P20 Living Autonomy Kernel has a solid architectural skeleton. The heartbeat service (LK-005), the LangGraph graph skeleton with its 4-node cyclic loop (LK-002), the HermesBrain bridge (LK-004), the Discord REST dashboard+log UX (LK-009), and the world-model database models (LK-003) are all production-grade. The HARD STOP safety mechanism is correctly implemented (liveness pulse at 1s, Redis flag, recovery).

However, **7 of 10 AC-LIFE success criteria are PARTIAL, PLACEHOLDER, or FAIL**:

- **AC-LIFE-002 FAIL**: idle_node uses `random.choice` over 3 hardcoded strings -- not world-state-driven at all.
- **AC-LIFE-005 FAIL**: p16_adapter and p18_adapter return mock data; kg_adapter/memory_adapter are **never injected into state** in `main.py`, so `decision_context` is never truly built from real substrates.
- **AC-LIFE-008 FAIL**: No journal system exists. The reflect_node creates audit entries but no private journal.
- **AC-LIFE-009 FAIL**: ReflectionEvaluator generates hardcoded placeholder candidates; never wired into graph or heartbeat.

The most critical gap: **LK-010 (P16/P18 integration) is entirely missing** despite production-grade substrates existing at `src/knowledge_graph/query/` (KGQueryEngine, RecallContextAssembler, KGRRFFusion) and `src/memory/read_pipeline.py` (async recall_memories returning RecallResults). The adapters are stubs. The state-injection path in `main.py` never sets `kg_adapter` or `memory_adapter`.

---

## 2. AC-LIFE Criteria Assessment

### AC-LIFE-001: Boot starts heartbeat and awareness without external trigger
**STATUS: PASS**

The FastAPI lifespan in `src/core/main.py:204-284` initializes `create_life_mind_graph`, `HeartbeatService`, and calls `await heartbeat.start()` as part of core startup. No Discord, cron, or external trigger needed. The heartbeat then runs 6 independent asyncio task loops.

```python
# src/core/main.py:272-282
heartbeat = HeartbeatService(
    graph=graph, redis_client=redis_client, checkpointer=checkpointer,
    discord_publisher=dashboard_writer, hermes_brain=hermes_brain,
    log_channel=log_channel,
)
await heartbeat.start()
```

### AC-LIFE-002: Idle creates self-directed task from world-state
**STATUS: FAIL**

The static `idle_node` at `src/life_kernel/graph.py:463` uses `random.choice` over 3 hardcoded strings:

```python
# src/life_kernel/graph.py:462-468
task_options = [
    ("exploration", "Exploration: review life_kernel state for patterns"),
    ("self_improvement", "Self-improvement: evaluate SDLC loop efficiency"),
    ("learning", "Learning: revisit recent observations for insights"),
]
task_type, task_description = random.choice(task_options)
```

This is **not** driven by world-state, memory, or any observation context. The LLM-enriched variant `_make_brain_idle` (line 604) calls the brain but the brain's proposal is **display-only** -- it generates a label and description, but does not create a real executable task. The static fallback is purely random.

The brain-enriched idle never calls a real P16/P18 recall to seed the proposal. It sends a generic prompt: "The operator is silent and there is no pending work." No world-state summary is included.

### AC-LIFE-003: Self-created task completes full SDLC loop and reflection
**STATUS: PLACEHOLDER**

The idle_node's "task" is just a string in an observation dict. The graph cycles (observe->decide->act->reflect->observe) but never executes a real SDLC session. The `session_graph.py` module exists with proper SDLC nodes (plan/execute/validate/audit/document/complete) but is **never wired** into the life_mind graph or called from `idle_node`. The idle observation is just a display entry.

### AC-LIFE-004: Dashboard updates every 60s and log channel preserves history
**STATUS: PASS**

`heartbeat.py:460-482` invokes the graph every 60s and publishes via `DashboardWriter.update_dashboard()` and `_log_lifecycle_milestone()`.

- **Dashboard**: `dashboard_writer.py` implements edit-not-spam via Redis-persisted message ID. `HeartbeatService._heartbeat_60s()` calls `await self._discord_publisher.update_dashboard(state)` at line 481.
- **Log channel**: `DiscordLogChannel.write()` at `log_channel.py:122` POSTs new messages (append-only). `_log_lifecycle_milestone()` at `heartbeat.py:494` writes throttled lifecycle narrative lines.
- **DashboardRenderer** at `dashboard.py:216` uses SHA-256 checksum to skip redundant renders.

### AC-LIFE-005: P16 KG and P18 memory influence autonomous decisions
**STATUS: FAIL**

Both adapters are stubs returning mock data:

- `src/life_kernel/p16_adapter.py:63-99` -- `KGRecallAdapter.recall()` returns hardcoded mock concepts with `"source": "p16_placeholder"` and `"_placeholder": True`.
- `src/life_kernel/p18_adapter.py:66-102` -- `MemoryRecallAdapter.recall()` returns hardcoded mock memories with `"_placeholder": True`.

Graph code at `src/life_kernel/graph.py:159-170` attempts to read `kg_adapter` and `memory_adapter` from state:

```python
kg_adapter = state.get("kg_adapter")
memory_adapter = state.get("memory_adapter")
if kg_adapter and memory_adapter:
    ...
else:
    decision_context = {"p16_available": False, "p18_available": False, ...}
```

**But these are NEVER injected into state.** `src/core/main.py:204-284` creates the graph and heartbeat but never sets `kg_adapter` or `memory_adapter` on the initial state or graph config. The else branch always fires, producing `{"p16_available": False, "p18_available": False}`.

**Real substrates that exist and work:**
- `src/knowledge_graph/query/engine.py:229` -- `KGQueryEngine` for PostgreSQL RCTE traversal
- `src/knowledge_graph/query/context.py:141` -- `RecallContextAssembler` for prompt injection
- `src/knowledge_graph/query/rrf_fusion.py:155` -- `KGRRFFusion` for RRF score integration
- `src/memory/read_pipeline.py:755` -- `async recall_memories(session, query_text, limit, *, principal="guinevere_core", ...)` returning `RecallResults`

None of these are imported or called by the life_kernel adapters.

### AC-LIFE-006: Guinevere continues when Faiz is silent
**STATUS: PASS**

The heartbeat runs independently on its own timer. The lifecycle log at `heartbeat.py:494` continues writing narrative lines. HARD STOP is the only mechanism that halts the service. No user input, cron trigger, or Discord event is required.

### AC-LIFE-007: HARD STOP halts active sessions and background action loops
**STATUS: PASS**

`src/life_kernel/heartbeat.py:254-324` implements `_heartbeat_1s()` with:
1. Redis flag check (`life_kernel:hard_stop` key)
2. Graph invoke to set `hard_stop_requested=True`
3. Discord dashboard publish
4. Log channel write
5. `await self.stop()` to halt all heartbeat tasks

Stale state recovery (stuck HARD STOP) is also handled at line 328-350.

### AC-LIFE-008: Guinevere writes an internal journal entry after meaningful action
**STATUS: FAIL**

There is no journal system. `LifeMindState` in `src/life_kernel/state.py:82-221` has:
- `observations` -- sensor data
- `audit_entries` -- execution audit trail  
- `goals`, `commitments`, `concerns` -- task/state tracking

But there is no `journal_entries` or `journal` field. The plan (vision-lock.md:94) requires a "Private internal journal for why Guinevere chose actions and what she learned." This does not exist.

The reflect_node at `graph.py:389-397` creates audit entries (phase, timestamp, cycle, has_errors) but these are execution metadata, not reflective journal entries with reasoning, lessons learned, or self-evaluation.

### AC-LIFE-009: Self-improvement candidate from reflection
**STATUS: FAIL**

`src/life_kernel/self_improve.py` exists with proper scaffolding:
- `ReflectionEvaluator` (line 90) with heuristics for error count, efficiency, idling, observation cap
- `ImprovementCandidate` dataclass (line 38)
- `RegressionGate` (line 264) for running tests
- `ImprovementTracker` (line 365) for in-memory tracking

However:
1. **All 4 generator methods are placeholders**: `generate_skill_candidate` (line 203), `generate_prompt_candidate` (line 218), `generate_planner_candidate` (line 233), `generate_code_candidate` (line 248) return hardcoded description strings. None call HermesBrain or inspect actual code/skills/prompts.
2. **Not wired into graph or heartbeat**: The heartbeat `_heartbeat_1h` at line 551 is a placeholder with no real reflection logic. The cognition `self_improvement` loop at `cognition.py:382` writes a placeholder observation string but never instantiates `ReflectionEvaluator`.
3. **No actual code/skill/prompt change mechanism**: The plan requires generating an improvement candidate that can actually modify a file. No such mechanism exists.

### AC-LIFE-010: Production restart resumes graph state from checkpoint
**STATUS: PARTIAL**

`src/life_kernel/checkpoint.py:23-67` creates `AsyncPostgresSaver` and `AsyncRedisSaver` properly. `src/core/main.py:217-223` attempts to create the postgres checkpointer. However:

```python
try:
    checkpointer = await create_postgres_checkpointer(_checkpointer_dsn)
except Exception as cp_err:
    logger.warning("postgres_checkpointer_unavailable", error=str(cp_err))
    checkpointer = None
```

- The checkpointer creation is wrapped in try/except and silently falls back to `None`
- When `checkpointer` is `None`, the graph compiles at line 756 of `graph.py` without checkpointing: `graph = builder.compile()`
- No verification test exists that restart recovery works
- No soak test has been run

---

## 3. LK Step Assessment

| Step | Status | Evidence |
|------|--------|----------|
| LK-001 Governance & vision sync | PARTIAL | Vision docs exist; AGENTS.md not verified in this pass |
| LK-002 LangGraph skeleton | PASS | `graph.py` compiles with StateGraph, conditional edges, checkpoint support |
| LK-003 World model persistence | PASS | `models.py` defines LifeMindStateModel, HeartbeatRecord, DomainMindState with proper SQLAlchemy ORM |
| LK-004 Hermes brain bridge | PASS | `hermes_brain.py` wraps AIAgent.run_conversation(), has think/think_with_tools, fallback, error handling |
| LK-005 Heartbeat service | PASS | `heartbeat.py` runs 6 intervals (1s/10s/30s/60s/5m/1h) with HARD STOP, recovery, dashboard publish |
| LK-006 Global life-mind graph | PARTIAL | Graph exists with 5 nodes but kg_adapter/memory_adapter never injected; idle_node is random |
| LK-007 Background cognition | PLACEHOLDER | All 6 loops in `cognition.py` write placeholder strings; real logic deferred |
| LK-008 Per-session graph | PLACEHOLDER | `session_graph.py` has SDLC nodes but they're phase-transition stubs; worktree/profile/thread are intent-only |
| LK-009 Discord dashboard | PASS | `dashboard_writer.py` + `discord_rest_client.py` + `log_channel.py` fully implement edit-not-spam dashboard + append-only log |
| LK-010 P16/P18 integration | FAIL | Adapters return mock data; never injected into graph state; real KG/memory substrates untouched |
| LK-011 Life sensors | PLACEHOLDER | `SensorRegistry` exists; `sensor_adapters.py` module is MISSING (imported in __init__.py but file does not exist) |
| LK-012 Email autonomy | PARTIAL | `EmailMind` with classification and policy exists; `send()` never calls real Gmail API (intentional v1-queue-only) |
| LK-013 Finance records | PARTIAL | `FinanceMind` with real record/classify/summarize/anomaly detection exists; not wired into graph/heartbeat |
| LK-014 Engineering deploy | PARTIAL | `EngineerMind` + `SSHDeployBackend` exist; default to dry-run/intent-only |
| LK-015 Self-improvement | PARTIAL | Scaffolding exists; all 4 generators return hardcoded strings; not wired into runtime |
| LK-016 Startup replacement | VOID | Life kernel starts in lifespan; daily ritual scheduler still exists at `src/loops/scheduler.py` |
| LK-017 Soak/audit/rollout | NOT STARTED | No evidence of soak, audit, or production rollout |

---

## 4. Gap Table

| ID | Severity | Title | Current State | Required State | Files | Vision Ref |
|----|----------|-------|---------------|----------------|-------|------------|
| gap-idle-random | critical | idle_node not world-state-driven | `random.choice` over 3 hardcoded strings (graph.py:463-468) | Self-directed task from world-state + P18 recall seeding | `src/life_kernel/graph.py`, `src/life_kernel/p18_adapter.py` | V-003, AC-LIFE-002 |
| gap-p16-p18-not-injected | critical | kg_adapter/memory_adapter never injected into graph state | `observe_node` checks `state.get("kg_adapter")` but neither is set by main.py:204-284 | Inject adapters during graph creation; wire real KGQueryEngine/RecallContextAssembler/recall_memories | `src/core/main.py`, `src/life_kernel/graph.py` | AC-LIFE-005, BD-005 |
| gap-p16-stub | critical | KGRecallAdapter returns mock data | `p16_adapter.py:63-99` returns hardcoded concepts with `_placeholder: True` | Call `src/knowledge_graph/query/engine.KGQueryEngine` or `context.RecallContextAssembler` | `src/life_kernel/p16_adapter.py`, `src/knowledge_graph/query/engine.py`, `src/knowledge_graph/query/context.py` | AC-LIFE-005 |
| gap-p18-stub | critical | MemoryRecallAdapter returns mock data | `p18_adapter.py:66-102` returns hardcoded memories with `_placeholder: True` | Call `src/memory/read_pipeline.recall_memories()` | `src/life_kernel/p18_adapter.py`, `src/memory/read_pipeline.py:755` | AC-LIFE-005 |
| gap-journal | high | No internal journal system | `LifeMindState` has audit_entries but no journal field (state.py:82-221); reflect_node creates audit (graph.py:389-397) but no reflective journal | Add `journal_entries` field to LifeMindState; write reflection entries with reasoning and lessons learned | `src/life_kernel/state.py`, `src/life_kernel/graph.py`, `src/life_kernel/models.py` | V-001 (Journal), AC-LIFE-008 |
| gap-self-improve-wiring | high | Self-improvement candidates not wired into runtime | `cognition.py:382` writes placeholder string; `heartbeat.py:551` has empty _heartbeat_1h; all 4 generators in self_improve.py return hardcoded strings | Wire ReflectionEvaluator into heartbeat 1h cycle; call HermesBrain for candidate generation | `src/life_kernel/self_improve.py`, `src/life_kernel/heartbeat.py`, `src/life_kernel/cognition.py` | AC-LIFE-009 |
| gap-session-graph-not-wired | high | Session SDLC graph never invoked | `session_graph.py` has 6-node SDLC graph but is never called from idle_node or act_node | idle_node should be able to spawn a session graph for a self-created task | `src/life_kernel/session_graph.py`, `src/life_kernel/graph.py` | AC-LIFE-003 |
| gap-decision-context-never-built | high | decision_context always returns p16/p18 unavailable | `graph.py:160-170` always takes the else branch because adapters not injected | DecisionContextBuilder should produce real enriched context from KG + memory | `src/life_kernel/decision_context.py`, `src/core/main.py` | AC-LIFE-005 |
| gap-heartbeat-10s-5m-1h-stubs | medium | 3 heartbeat intervals are log-only placeholders | `_heartbeat_10s:373` is a debug log; `_heartbeat_5m:530` is a debug log; `_heartbeat_1h:551` is a debug log | Implement stuck detection (10s), deep scan (5m), reflection batch (1h) | `src/life_kernel/heartbeat.py:373-571` | Benchmark section 9.2 |
| gap-cognition-all-placeholder | medium | All 6 background cognition loops write placeholder strings | `cognition.py:296-405` each produce `_make_observation("loop=X", content="Placeholder...", ...)` | Observer polls real sensors; critic runs Hermes analysis; curiosity generates real questions | `src/life_kernel/cognition.py` | Benchmark section 9.4 |
| gap-sensor-adapters-missing | medium | sensor_adapters.py module does not exist | `__init__.py` imports from `sensor_adapters` but the file is MISSING | Create sensor_adapters.py with real adapter stubs | `src/life_kernel/sensor_adapters.py` (new), `src/life_kernel/__init__.py:35-44` | LK-011 |
| gap-checkpointer-fallback | medium | Checkpointer failure silently falls back to None | `main.py:218-223` catches all exceptions and sets `checkpointer = None` | Need known baseline: if checkpointer fails, log clearly and possibly alert | `src/core/main.py:217-223` | AC-LIFE-010 |
| gap-email-real-send | low | EmailMind.send() never calls real Gmail API | `email_mind.py:151-205` returns `{"status": "queued"}` for low-risk email; never calls `src/gmail/` | Wire to Gmail service for actual low-risk send (intentional for v1 but gated for later) | `src/life_kernel/domain_minds/email_mind.py` | BD-010 (v1: queue only) |
| gap-finance-not-wired | low | FinanceMind not integrated into heartbeat or graph | `finance_mind.py` has real record/classify/summarize but is never instantiated or called by life_kernel | Wire FinanceMind into heartbeat 30s awareness refresh or observer loop | `src/life_kernel/domain_minds/finance_mind.py`, `src/life_kernel/heartbeat.py` | BD-011 |
| gap-no-checkpoint-restart-test | low | No verification of restart recovery | No test that would prove state survives restart | Add test: invoke graph with state, "restart", verify state loaded from checkpointer | (test files in `tests/life_kernel/`) | AC-LIFE-010 |

---

## 5. Risks

| Risk | Mitigation |
|------|------------|
| P16/P18 integration assumes adapters are near-trivial wiring but KG query requires async SQLAlchemy session, entity resolution, and consent checks -- substantial integration work | Start with a minimal wire: import `KGQueryEngine` with a session factory, call one query, return results. Defer entity resolution and consent for a follow-up. |
| Random idle_node means kernel appears "alive" but produces no meaningful self-directed work. This undermines the core autonomy claim. | Fix idle_node first: inject P18 recall results as seed context, then pass to HermesBrain for task proposal. Retain static fallback (random) only if brain unavailable. |
| DecisionContextBuilder depends on kg_adapter/memory_adapter injection path that doesn't exist. If both adapters are None it gets default stubs but stubs return mock data. | Fix injection in main.py first, then replace stub logic with real KG/Memory calls. |
| Heartbeat 10s/5m/1h stubs burn CPU doing nothing useful. The 5m and 1h intervals represent 2 of 3 "deep cognition" cycles. | Implement at minimum: 10s stuck detection (check phase transition timestamps), 1h reflection (wire ReflectionEvaluator, write journal entry). |
| Session graph (LK-008) is fully unwired. Self-created tasks from idle_node have no execution path. | After idle_node fix, wire session_graph.SessionGraph as a spawned subgraph from act_node when the task is an SDLC-type task. |
| journal_entries field missing from LifeMindState. AC-LIFE-008 cannot pass without it. | Add `journal_entries: Annotated[list[dict], add_journal_reducer]` to LifeMindState. Write in reflect_node when meaningful action occurred. |

---

## 6. Hard-Rejection Flags

| Flag | Status | Evidence |
|------|--------|----------|
| Uses raw LLMRouter.chat as primary brain | CLEAR | `hermes_brain.py:294` calls `AIAgent.run_conversation()`; graph uses `_safe_think()` wrapping `hermes_brain.think()` |
| HARD STOP removed or weakened | CLEAR | `heartbeat.py:254-324` has full Redis-based HARD STOP with recovery |
| "heartbeat" terminology lost | CLEAR | Used consistently |
| Secrets leaked in evidence | CLEAR | DashboardRenderer has secret patterns redaction; none observed |
| Governance blocks autonomy | NOT VERIFIED | AGENTS.md not read in this pass |
| P16 KG or P18 memory duplicated | CLEAR | Not duplicated -- not integrated either |
| Display-only autonomy violated | CLEAR | All graph actions are display-only per operator approval |
| sensor_adapters.py import broken | FAIL | `__init__.py:35-44` imports from `sensor_adapters` but the file does not exist. This will cause an ImportError if any of these classes are accessed. |

---

## 7. Concrete Recommendation for Implementation Phase

### Priority 0 (blocking -- fix first or nothing else works):

1. **Fix P16/P18 adapter stubs + injection** (AC-LIFE-005 critical): Replace `KGRecallAdapter.recall()` with a minimal wrapper around `KGQueryEngine` (just needs an async session factory). Replace `MemoryRecallAdapter.recall()` with a call to `recall_memories()`. In `main.py`, inject the constructed adapters into the initial state or pass them as graph constructor args.

2. **Fix idle_node to be world-state-driven** (AC-LIFE-002 critical): Before calling `random.choice`, check if any observation context exists. Inject P18 recall results as the seed. Pass a world-state summary to HermesBrain in `_make_brain_idle`. The static fallback should remain random only when brain unavailable.

### Priority 1 (core autonomy completeness):

3. **Add journal system** (AC-LIFE-008 high): Add `journal_entries` to `LifeMindState`. Write an entry in `reflect_node` when a meaningful action cycle completed (act_count > 0). Include: why the action was chosen, what happened, what was learned.

4. **Wire self-improvement into heartbeat** (AC-LIFE-009 high): Implement `_heartbeat_1h` to run `ReflectionEvaluator.evaluate()` on the current state, propose candidates, and log them. The candidates remain display-only but are no longer hardcoded strings.

5. **Stub-to-real for cognition loops** (LK-007 medium): At minimum, make observer loop call `SensorRegistry.sense_all()` when sensors are registered. Make memory loop call P18 recall.

### Priority 2 (production hardening):

6. **Wire session graph** (LK-008 medium): When idle_node creates a task of type "engineering", spawn a `SessionGraph` subgraph.

7. **Add checkpoint restart test** (AC-LIFE-010 medium): Write a test that invokes graph with state, re-creates from checkpointer, and verifies state matches.

8. **Fix sensor_adapters.py missing file** (hard-rejection): Create the file or remove the imports from `__init__.py`.

### Files to modify (ordered by criticality):
- `src/life_kernel/p16_adapter.py` -- replace stub with real KG call
- `src/life_kernel/p18_adapter.py` -- replace stub with real memory call
- `src/core/main.py` -- construct and inject adapters  
- `src/life_kernel/graph.py` -- fix idle_node randomization, add journal writing
- `src/life_kernel/state.py` -- add journal_entries field
- `src/life_kernel/heartbeat.py` -- implement _heartbeat_1h with ReflectionEvaluator
- `src/life_kernel/self_improve.py` -- make generators produce Hermes-driven candidates
- `src/life_kernel/cognition.py` -- replace placeholder loops with real logic
- `src/life_kernel/sensor_adapters.py` -- create file or cleanup imports

---

## 8. Memory Note Reconciliation

The memory note's "discord wiring not implemented" is **outdated**. Current code at `src/core/main.py:246-270` shows:

```python
_dashboard_channel_id = os.environ.get("LIFE_KERNEL_DASHBOARD_CHANNEL_ID", "")
_log_channel_id = os.environ.get("LIFE_KERNEL_LOG_CHANNEL_ID", "")
discord_rest = DiscordRestClient()
if _dashboard_channel_id and discord_rest.enabled:
    dashboard_writer = DashboardWriter(
        rest_client=discord_rest, renderer=DashboardRenderer(),
        redis_client=redis_client, channel_id=int(_dashboard_channel_id),
    )
    ...
```

Discord REST dashboard+log are properly wired via Option B (core-integrated REST publisher). `guinevere-discord.service` stays intentionally masked. The memory note should be updated to reflect the current state: "Discord wiring IMPLEMENTED -- Option B core-integrated REST publisher is live."

---

## 9. Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-24 | Gap Auditor | Initial plan-vs-code audit for P20 continuation pass |

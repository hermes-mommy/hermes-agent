# Architecture Audit — P20 Living Autonomy Continuation (Round 2)

| Field | Value |
|---|---|
| Auditor | Architecture (Round 2) |
| Scope | Graph topology, HermesBrain boundary, adapters registry, empty-state trap, goal dedup, journal recursion, recursion_limit, ReflectionEvaluator wiring |
| Commits | HEAD (wave-1 fixes: RUN-01/AUTO-06/DUX-01/SAF-02), HEAD~1 (MEM-01..06) |
| Date | 2026-06-24 |
| Verdict | **PASS_WITH_NOTES** |

## 1. Verdict

**PASS_WITH_NOTES.** All 10 wave-1 findings from round-1 audits are correctly fixed. The architecture is sound: graph topology is intact, HermesBrain.think is the only LLM path (no raw LLMRouter), _ADAPTERS registry is functional, recursion_limit=25 is set consistently across all graph invocations, and the ReflectionEvaluator wiring is architecturally correct. However, 3 new architectural issues were identified: (1) set_adapters docstring claims reset-first behavior that isn't implemented, (2) goal deduplication relies on fragile description matching because goal_id includes cycle_count, (3) route_from_decide has dead code checking for "hard_stop" that no node returns. None of these trigger hard rejection. Pre-existing issues from round-1 (goals field lacks reducer, journal missing source field, self-improvement uses hardcoded candidates) remain unaddressed but were out of scope for wave-1 fixes.

## 2. Executive Summary

The P20 Living Autonomy Kernel continuation satisfies every wave-1 fix requirement and maintains architectural integrity throughout the codebase. The critical wave-1 fixes verified in this round:

- **RUN-01**: `_heartbeat_1h` now correctly instantiates `ReflectionEvaluator(graph, graph_config, hermes_brain)` at `heartbeat.py:608-612`, fixing the TypeError that broke hourly self-improvement.
- **AUTO-06**: Heartbeat log now uses `c.category` instead of non-existent `candidate_type` at `heartbeat.py:623-624`.
- **DUX-01**: Lifecycle log line is truncated to 1900 chars before Discord write at `heartbeat.py:523-528`.
- **SAF-02**: Autonomous memory recall defaults to `safe_mode=True` (redacts Critical content) at `main.py:205`, operator opt-in via `LIFE_KERNEL_RAW_RECALL=1`.
- **MEM-01 through MEM-06**: All memory/adapter fixes verified (display_name, no datetime.utcnow, journal gate, engine disposal, docstrings, memory_status).

The graph topology remains correct: observe → decide → act/reflect/idle → END. The HARD STOP safety path is enforced non-LLM in `decide_node` before any brain consultation. The _ADAPTERS registry pattern (module-level storage because LangGraph checkpoints state as JSON) is architecturally sound. The recursion_limit=25 is set in all graph invocations (1s, 30s, 60s, 1h heartbeats). No regressions were introduced by the wave-1 fixes.

Three new architectural issues were found, all non-blocking: (1) `set_adapters` docstring/implementation mismatch, (2) goal deduplication fragility due to cycle_count in goal_id, (3) dead code in route_from_decide checking for "hard_stop" string that no node returns. These should be addressed before claiming full production readiness but do not prevent continued testing.

## 3. Wave-1 Fix Verification

### 3.1 RUN-01: ReflectionEvaluator Instantiation (VERIFIED ✅)

**Original issue**: `src/life_kernel/heartbeat.py:591-596` instantiated `ReflectionEvaluator()` with no arguments, but the class requires `(graph, graph_config, hermes_brain=None)` positional args per `self_improve.py:99-104`. This raised `TypeError` every hour, breaking AC-LIFE-009.

**Fix verification**: `heartbeat.py:608-612` now passes all required arguments:
```python
evaluator = ReflectionEvaluator(
    graph=self.graph,
    graph_config=graph_config,
    hermes_brain=self._hermes_brain,
)
```

The fix comment at line 601-603 explicitly references "RUN-01/DOC-02 fix". The graph_config dict at line 604-607 includes `recursion_limit: 25` for safety. ✅ **FIXED**

### 3.2 AUTO-06: Candidate Category Attribute (VERIFIED ✅)

**Original issue**: `heartbeat.py:602,611` referenced non-existent `candidate_type` attribute via `getattr(c, 'candidate_type', '?')`, logging '?' for every candidate.

**Fix verification**: `heartbeat.py:623-624` now correctly uses:
```python
categories = [
    str(getattr(c, "category", "?")) for c in candidates
]
```

The fix comment at line 620-622 explicitly references "AUTO-06 fix". The `ImprovementCandidate` class exposes `.category` (a `CandidateCategory` enum), not `candidate_type`. ✅ **FIXED**

### 3.3 DUX-01: Lifecycle Log Truncation (VERIFIED ✅)

**Original issue**: Discord rejects plain-text messages over 2000 chars. Long intent/focus values could push the lifecycle log line past the limit, causing Discord write failures.

**Fix verification**: `heartbeat.py:523-528` truncates before write:
```python
_DISCORD_LOG_MAX = 1900
if len(line) > _DISCORD_LOG_MAX:
    line = line[: _DISCORD_LOG_MAX - 3] + "..."
```

The fix comment at line 523-525 explicitly references "DUX-01 fix". The 1900-char limit leaves 100-char headroom for any wrapper. ✅ **FIXED**

### 3.4 SAF-02: Safe Mode for Autonomous Recall (VERIFIED ✅)

**Original issue**: `main.py:267` passed `safe_mode=False` to `recall_memories`, exposing raw Critical-classified episode content to autonomous brain prompts and Discord-visible status.

**Fix verification**: `main.py:189-205` now defaults to `safe_mode=True`:
```python
_life_raw_recall = os.environ.get("LIFE_KERNEL_RAW_RECALL", "0") == "1"

async def _life_recall_fn(...):
    return await _recall_memories(
        ...,
        safe_mode=not _life_raw_recall,
    )
```

The fix comment at line 189-194 explicitly references "SAF-02" and explains the opt-in design. Default is safe; operator sets `LIFE_KERNEL_RAW_RECALL=1` to opt into raw Critical content. ✅ **FIXED**

### 3.5 MEM-01: P16 Adapter display_name Read (VERIFIED ✅)

**Original issue**: P16 adapter object-branch didn't read `display_name` from KG entities.

**Fix verification**: `main.py:228` uses:
```python
"name": getattr(r, "display_name", None) or str(getattr(r, "entity_id", "")),
```

The adapter first tries `display_name`, falls back to `entity_id` if missing. ✅ **FIXED**

### 3.6 MEM-02: No datetime.utcnow Usage (VERIFIED ✅)

**Original issue**: Deprecated `datetime.utcnow()` usage in adapters.

**Fix verification**: `grep -n "datetime.utcnow" src/life_kernel/*.py` returns NO matches. All datetime usage is `datetime.now(timezone.utc)` or `datetime.now().isoformat()`. ✅ **FIXED**

### 3.7 MEM-03: Reflect Journal Gate (VERIFIED ✅)

**Original issue**: Reflect journal gate used stale `act_count` from state before reducer merge, causing false negatives on first post-boot cycle.

**Fix verification**: `graph.py:514-524` no longer gates on `act_count`:
```python
# A cycle is "meaningful" if the brain produced a decision/next-action or
# recall surfaced context. We intentionally do NOT gate on `act_count`
# here: it is read from state before this cycle's act_node reducer merges,
# so it is stale on the first post-boot cycle.
meaningful = (
    bool(last_decision)
    or bool(next_action)
    or bool(state.get("recalled_memories"))
    or bool(state.get("recalled_concepts"))
)
```

The comment at line 514-518 explicitly explains the fix. ✅ **FIXED**

### 3.8 MEM-04: Audit Journal Engine Disposal (VERIFIED ✅)

**Original issue**: PostgresAuditJournal creates a private engine pool that wasn't disposed on shutdown, leaking connections.

**Fix verification**: `main.py:389-397` disposes the engine:
```python
_audit_journal = getattr(app.state, "life_kernel_audit_journal", None)
if _audit_journal is not None:
    try:
        _aj_engine = getattr(_audit_journal, "_engine", None)
        if _aj_engine is not None:
            await _aj_engine.dispose()
            logger.info("life_kernel_audit_journal_engine_disposed")
```

The comment at line 387-388 explicitly references "MEM-04 fix". ✅ **FIXED**

### 3.9 MEM-05: Adapter Docstrings (VERIFIED ✅)

**Original issue**: Adapter modules lacked comprehensive docstrings.

**Fix verification**: Both adapters have module-level and class-level docstrings:
- `p16_adapter.py:1-50`: Comprehensive module docstring, `KGRecallAdapter` class docstring with Args/Attributes sections.
- `p18_adapter.py:1-70`: Comprehensive module docstring, `MemoryRecallAdapter` class docstring with Args/Attributes sections.

✅ **FIXED**

### 3.10 MEM-06: memory_status No Raw Content (VERIFIED ✅)

**Original issue**: `memory_status` field echoed raw memory content into Discord-visible dashboard.

**Fix verification**: `graph.py:223-232` uses counts only:
```python
top_con = recalled_concepts[0].get("name", "") if recalled_concepts else ""
memory_status = (
    f"{world_model_status}: {len(recalled_memories)} mem, {len(recalled_concepts)} kg"
    + (f" | top concept: {top_con}" if top_con else "")
)
```

Only the top KG concept NAME is exposed, never raw memory content. ✅ **FIXED**

## 4. New Findings

| ID | Severity | Title | File:Line | Detail | Recommendation |
|---|---|---|---|---|---|
| ARCH-01 | medium | set_adapters docstring claims reset-first but implementation doesn't match | `src/life_kernel/graph.py:562-580` | The docstring states "Resets the registry first so a graph built without adapters is truly headless (no stale adapters leak from a previous build)" but the function body just overwrites `_ADAPTERS` dict values without explicit reset. A separate `reset_adapters()` exists at line 583-588 but `set_adapters` doesn't call it. Passing None args would reset, but the docstring implies automatic reset before assignment which doesn't happen. This creates misleading documentation and potential test-isolation bugs if callers assume reset-first semantics. | Either update docstring to "Can be called with no args to reset" or have `set_adapters()` call `reset_adapters()` at the top of the function before assignments to match the documented contract. |
| ARCH-02 | medium | Goal deduplication fragile — goal_id includes cycle_count making it unique every idle cycle | `src/life_kernel/graph.py:662, 671-672` | Line 662: `new_goal['goal_id'] = f'self-directed-{cycle_count}'` generates a unique ID every cycle. Line 671-672: dedup checks `g.get("goal_id") == new_goal["goal_id"]` which will NEVER match because cycle_count increments. Dedup only works via description match, but descriptions include memory content (line 620: 'follow up on recalled context — {top_memory}') which varies, causing goal accumulation. This was flagged as AUTO-02 in round-1 but remains unaddressed. The `brain_idle` wrapper (line 825-856) further mutates the description after dedup, exacerbating drift risk. | Use a stable goal_id derived from a hash of the source memory/concept content, not cycle_count. Perform dedup AFTER brain enrichment, not before. Add a test asserting consecutive idle cycles with different memory content don't accumulate unbounded goals. |
| ARCH-03 | low | route_from_decide checks for 'hard_stop' decision but no node returns this value | `src/life_kernel/graph.py:957` | Line 957: `route_from_decide` checks `if decision == "hard_stop"` but `decide_node` (line 314-316) returns `{'decision': 'end'}` for HARD STOP, not 'hard_stop'. `reflect_node` (line 550) also returns 'end'. The 'hard_stop' check is dead code — it never matches. The routing still works because the default case (line 970-972) catches 'end' and routes to END, but the explicit check is misleading and suggests a design intent that was never implemented. | Remove the 'hard_stop' check (line 957-959) or update decide_node/reflect_node to return `{'decision': 'hard_stop'}` instead of 'end' if the distinction matters for logging/observability. Document that 'end' is the canonical HARD STOP routing token. |

## 5. Hard-Rejection Check

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Docs-only (no real code change) | **PASS** | Real code changes in `graph.py`, `state.py`, `journal.py`, `p16_adapter.py`, `p18_adapter.py`, `heartbeat.py`, `self_improve.py`, `main.py`. |
| 2 | Discord proof missing | **DEFERRED** | Code audit only; live Discord proof is a deployment-wave gate. |
| 3 | Raw `LLMRouter.chat` as brain path | **PASS** | Only one LLMRouter mention at `graph.py:874` in a docstring comment explaining `_safe_think` wrapper. Brain path is `HermesBrain.think()` via `_safe_think` (line 104-130). |
| 4 | Only health-check loops, no memory/daily-life | **PASS** | `observe_node` calls real P16/P18 recall adapters (line 193-209); `idle_node` is memory-driven (line 607-639); brain prompts include recall context (line 744-755). |
| 5 | Sub-agent no output file | **PASS** | This report is the output file. |
| 6 | Tests/audits skipped to pass | **PASS** | Local tests pass (420 passed, 7 skipped per round-1 reports). |
| 7 | Secrets in output | **PASS** | No secrets in diff or output; `DashboardRenderer._sanitize` redacts secrets; adapters log counts only. |
| 8 | PRODUCTION PASS w/o live proof | **PASS (not claimed)** | Verdict is `PASS_WITH_NOTES`; no production PASS claimed yet. |
| 9 | `world_model_available = False` placeholder | **PASS** | Removed; now derived from real adapter state at `graph.py:242`. |
| 10 | `idle_node` still uses `random.choice` | **PASS** | No `random.choice`; deterministic fallback by `cycle_count % len(fallbacks)` at line 638. |
| 11 | Adapters still return `_placeholder:True` | **PASS** | Adapters return real data or `_degraded: True` on failure; no `_placeholder` key. |
| 12 | HARD STOP regression | **PASS** | `decide_node` checks `hard_stop_requested` first (line 314) before any LLM call. `_heartbeat_1s` reads Redis flag and can recover stale state. |
| 13 | Other services disturbed | **N/A (not deployed)** | Code audit only; deploy canary is a later wave. |

**Hard-rejection verdict**: ✅ **NO VIOLATIONS**

## 6. What's GOOD (Architectural Strengths)

### 6.1 Graph Topology Intact

The 4-node cyclic graph is correctly implemented:
- `START → observe` (line 938)
- `observe → decide` (line 941)
- `decide → [act|reflect|idle|END]` conditional (line 944-983)
- `act → reflect` (line 986)
- `reflect → END` (line 991)
- `idle → END` (line 992)

The heartbeat re-invokes every 60s for the next cycle (`heartbeat.py:462-468`). State persists via checkpointer between invocations. The graph never recurses within a single invocation (each cycle completes at END).

### 6.2 HermesBrain.think Only (No Raw LLMRouter)

`grep -n LLMRouter src/life_kernel/*.py` returns ONE match at `graph.py:874` which is in a docstring comment explaining the `_safe_think` wrapper:
```python
# When ``hermes_brain`` is provided, decide/act/idle nodes are wrapped in
# LLM-enriched variants that call ``hermes_brain.think()`` (never raw
# ``LLMRouter.chat``) with a hard timeout and a fail-safe fallback to the
# static logic.
```

All brain invocations go through `_safe_think(hermes_brain, user_msg, system_prompt)` at line 104-130, which calls `hermes_brain.think()` with a 30-second timeout and fail-safe fallback. No raw LLMRouter.chat usage exists in the life_kernel codebase.

### 6.3 _ADAPTERS Registry Sound

The module-level `_ADAPTERS` registry (line 558) is architecturally correct:
```python
_ADAPTERS: dict[str, Any] = {"kg": None, "memory": None, "journal": None}
```

LangGraph checkpoints state as JSON and cannot hold live adapter objects (which have async methods, sessions, connections). The registry pattern stores adapters at module level so node functions can access them without threading through state. The `set_adapters()` function (line 562-580) registers adapters at graph creation time. A `reset_adapters()` utility (line 583-588) exists for test isolation.

### 6.4 Empty-State Trap Fixed

`decide_node` (line 343-345) routes to `idle` when goals/commitments/concerns are all empty:
```python
if len(state.get("goals", [])) == 0 and len(state.get("commitments", [])) == 0 and len(state.get("concerns", [])) == 0:
    logger.info("no active goals, commitments, or concerns - routing to idle for self-directed tasks")
    return {"decision": "idle"}
```

The `idle_node` (line 607-681) seeds a real self-directed goal into `state.goals` (AC-LIFE-002 / V-003), breaking the empty-state trap. The next 60s heartbeat invocation will have a goal to act on.

### 6.5 Reflect Journal No Block/Recurse

`reflect_node` (line 536-546) awaits `journal_writer.write_entry()` with fail-soft exception handling:
```python
try:
    entry = await journal_writer.write_entry(...)
    if entry:
        journal_update = {"journal_entries": [entry]}
except Exception as exc:  # noqa: BLE001 — fail-soft
    logger.warning("reflect_journal_failed", error_type=type(exc).__name__)
```

The journal write does not recursively invoke the graph. A slow DB write could block the reflect_node, but it's bounded by the graph's overall recursion_limit and fail-soft on exception. No GraphRecursionError risk.

### 6.6 recursion_limit=25 Set Consistently

All graph invocations set `recursion_limit: 25` in the config dict:
- `heartbeat.py:303` (_heartbeat_1s recovery path)
- `heartbeat.py:342` (_heartbeat_30s)
- `heartbeat.py:466` (_heartbeat_60s main cycle)
- `heartbeat.py:606` (_heartbeat_1h ReflectionEvaluator)

The limit is safe: the graph completes in 1-2 steps per invocation (observe → decide → act/idle → reflect → END). 25 is a conservative ceiling that prevents infinite loops without constraining normal operation.

### 6.7 ReflectionEvaluator Wiring Architecturally Correct

The fixed instantiation (line 608-612) passes all required arguments:
```python
evaluator = ReflectionEvaluator(
    graph=self.graph,
    graph_config=graph_config,
    hermes_brain=self._hermes_brain,
)
```

The `graph` is the compiled `CompiledStateGraph` instance stored in `HeartbeatService`. The `graph_config` includes the thread_id and recursion_limit. The `hermes_brain` is the same `HermesBrain` instance used by the main graph. This is architecturally sound — the evaluator can inspect kernel state and (in future) use the brain for candidate generation.

### 6.8 HARD STOP Safety Path Preserved

`decide_node` (line 314-316) checks `hard_stop_requested` FIRST before any LLM involvement:
```python
if state.get("hard_stop_requested", False):
    logger.warning("HARD_STOP requested - routing to END")
    return {"decision": "end"}
```

The `_heartbeat_1s` recovery path (heartbeat.py:254-358) reads the live Redis flag every second and can clear stale checkpoint state when the flag is absent. HARD STOP is a non-LLM override and can never be bypassed by brain decisions.

### 6.9 Fail-Soft Everywhere

- Adapter failures degrade to `_degraded: True` (observe_node line 198-200, 207-209)
- Brain timeouts fall back to static logic (_safe_think line 642-656)
- Journal write failures log warnings without crashing (reflect_node line 545-546)
- Dashboard publish failures never block the heartbeat (heartbeat.py:483-488)
- DB/engine failures in main.py leave the kernel headless but running

The kernel never crashes on a subsystem failure. Every external dependency is wrapped in try/except with fail-soft fallback.

## 7. Pre-Existing Issues (Out of Scope for Wave-1 but Worth Noting)

The following issues were flagged in round-1 but were NOT addressed by the wave-1 fixes (they were out of scope):

1. **RUN-04**: `goals` field has no Annotated reducer (state.py:145), using last-writer-wins. Works now because only idle_node writes goals, but fragile if multiple nodes start writing.

2. **SAF-03**: `journal.py:48-56` builds entry dict without "source" field. PostgresAuditJournal falls back to "unknown", making source-based filtering useless.

3. **AUTO-01**: `ReflectionEvaluator.evaluate()` (self_improve.py:128-165) returns hardcoded heuristic candidates, never uses `hermes_brain` despite storing it (line 103, 114). The self-improvement loop is not yet autonomous.

4. **RUN-03**: `observe_node` (graph.py:193-209) awaits KG and memory adapters serially, not concurrently. Should use `asyncio.gather` for better latency.

These should be addressed in a future wave but are not blockers for continued testing.

## 8. Verdict

**PASS_WITH_NOTES.** The P20 Living Autonomy Kernel continuation satisfies all wave-1 fix requirements and maintains architectural integrity. All 10 wave-1 findings are correctly fixed. The three new issues found (ARCH-01, ARCH-02, ARCH-03) are non-blocking but should be addressed before final production sign-off. No hard-rejection criteria are triggered. The kernel is ready for continued VPS testing and live Discord proof.

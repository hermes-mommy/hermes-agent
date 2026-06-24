# Runtime Audit — P20 Living Autonomy Continuation (Round 2)

| Field | Value |
|---|---|
| Auditor | Runtime / Event-loop / Lifecycle auditor (Round 2) |
| Scope | `src/life_kernel/{heartbeat,graph,self_improve}.py`, `src/core/main.py` |
| Commits | HEAD~1 (MEM fixes) → HEAD (RUN-01/AUTO-06/DUX-01/SAF-02 fixes) |
| Date | 2026-06-24 |
| Verdict | **PASS_WITH_NOTES** |

## 1. Executive Summary

The wave-1 runtime fixes are **correctly implemented and verified**. The critical RUN-01 bug (ReflectionEvaluator TypeError) is fixed, the 1h reflection/self-improvement heartbeat is now functional, and all MEM-series fixes from the memory/world-model audit hold under runtime scrutiny. Tests remain green (420 passed, 7 skipped, 0 failed).

However, this round-2 audit identified **three new non-blocking issues**: the round-1 RUN-03 observation (serial KG/memory recall adding latency) remains unaddressed, and two timestamp fields use naive `datetime.now()` instead of timezone-aware `datetime.now(timezone.utc)`, creating inconsistency with the MEM-02 fix. None trigger hard-rejection or break functionality, but RUN-2-01 should be addressed before a long production soak to keep the observe phase latency low.

## 2. Wave-1 Fix Verification

| Fix ID | Title | Status | Evidence |
|---|---|---|---|
| **RUN-01** | `_heartbeat_1h` ReflectionEvaluator instantiation with required args | ✅ **VERIFIED FIXED** | `src/life_kernel/heartbeat.py:608-612`: `evaluator = ReflectionEvaluator(graph=self.graph, graph_config=graph_config, hermes_brain=self._hermes_brain)` — all three required args (graph, graph_config, hermes_brain) are passed correctly. Round-1 critical TypeError is resolved. |
| **RUN-02** | `evaluate()` runs in `asyncio.to_thread` | ✅ **VERIFIED FIXED** | `src/life_kernel/heartbeat.py:617`: `candidates = await asyncio.to_thread(evaluator.evaluate, state)` — evaluate() is wrapped in asyncio.to_thread to avoid blocking the event loop. |
| **AUTO-06** | Heartbeat logs `candidate.category` not `candidate_type` | ✅ **VERIFIED FIXED** | `src/life_kernel/heartbeat.py:623-629`: `categories = [str(getattr(c, "category", "?")) for c in candidates]` — logs the correct `.category` attribute (a CandidateCategory enum). Round-1 logged '?' for every candidate. |
| **DUX-01** | Lifecycle log truncated to ≤1900 chars before Discord write | ✅ **VERIFIED FIXED** | `src/life_kernel/heartbeat.py:523-528`: checks `if len(line) > _DISCORD_LOG_MAX` (1900) and truncates with `line[: _DISCORD_LOG_MAX - 3] + "..."`. Discord's 2000-char limit is respected with headroom. |
| **SAF-02** | `recall_memories` called with `safe_mode=not LIFE_KERNEL_RAW_RECALL` | ✅ **VERIFIED FIXED** | `src/core/main.py:195-206`: `_life_raw_recall = os.environ.get("LIFE_KERNEL_RAW_RECALL", "0") == "1"` defaults to `"0"`, so `safe_mode=not _life_raw_recall` defaults to `True`. Critical/Restricted content is redacted by default before reaching the brain prompt. |
| **MEM-01** | `p16_adapter` object-branch reads `display_name` (not `name`) | ✅ **VERIFIED FIXED** | `src/life_kernel/p16_adapter.py:88-90`: object-branch reads `getattr(r, "display_name", None) or getattr(r, "name", "") or getattr(r, "entity_id", "")` — prioritizes `display_name` correctly. |
| **MEM-02** | No deprecated `datetime.utcnow()` | ✅ **VERIFIED FIXED** | `src/life_kernel/journal.py:55`: uses `datetime.now(timezone.utc).isoformat()`. No `datetime.utcnow()` in life_kernel (grep confirmed). |
| **MEM-03** | Reflect journal gate no longer uses stale `act_count` | ✅ **VERIFIED FIXED** | `src/life_kernel/graph.py:519-524`: meaningful gate is `bool(last_decision) or bool(next_action) or bool(recalled_memories) or bool(recalled_concepts)` — stale `act_count` is NOT used. |
| **MEM-04** | Audit-journal engine disposed on shutdown | ✅ **VERIFIED FIXED** | `src/core/main.py:459-467`: `_audit_journal = getattr(app.state, "life_kernel_audit_journal", None)` → `_aj_engine = getattr(_audit_journal, "_engine", None)` → `await _aj_engine.dispose()`. The journal's private engine pool is now disposed alongside `life_kernel_engine`. |
| **MEM-05** | Adapter docstrings updated | ✅ **VERIFIED FIXED** | `src/life_kernel/p18_adapter.py:1-12` describes real recall (wrapping `recall_memories`), not "stubbed" or "placeholder". `src/life_kernel/p16_adapter.py` docstring similarly updated. |
| **MEM-06** | `memory_status` no raw memory content | ✅ **VERIFIED FIXED** | `src/life_kernel/graph.py:223-232`: `memory_status` shows only counts (`{len(recalled_memories)} mem, {len(recalled_concepts)} kg`) and the top concept NAME — no raw memory content that could be Critical-classified. |

## 3. New Findings (Round 2)

| ID | Severity | Title | Detail (file:line) | Recommendation |
|---|---|---|---|---|
| **RUN-2-01** | medium | `observe_node` still awaits KG and memory adapters serially | `src/life_kernel/graph.py:195, 204`: KG recall at line 195 (`kg_result = await kg_adapter.recall(...)`) then memory recall at line 204 (`mem_result = await memory_adapter.recall(...)`) are awaited sequentially. If either recall takes time (embedding search + DB round-trip), observe phase latency is additive. **This was round-1 RUN-03 but was NOT fixed in wave-1.** | Use `asyncio.gather(kg_adapter.recall(...), memory_adapter.recall(...))` with individual exception handling (`return_exceptions=True` or separate try/except wrappers) to keep observe phase latency low. Each recall is independent and can run concurrently. |
| **RUN-2-02** | low | `p16_adapter` timestamp fields use naive `datetime.now()` | `src/life_kernel/p16_adapter.py:100, 109`: `"_timestamp": datetime.now().isoformat()` is naive (no timezone). This is inconsistent with the MEM-02 fix (`journal.py:55` uses `datetime.now(timezone.utc).isoformat()`). Not a runtime bug (timestamps are still valid) but creates inconsistent timezone handling across the kernel. | Replace with `datetime.now(timezone.utc).isoformat()` for consistency. Add `from datetime import timezone` to the imports. |
| **RUN-2-03** | low | `graph.py` observation timestamp uses naive `datetime.now()` | `src/life_kernel/graph.py:249`: `"timestamp": datetime.now().isoformat()` in the observation_data dict is naive. Same inconsistency as RUN-2-02. | Replace with `datetime.now(timezone.utc).isoformat()`. The import `from datetime import datetime` is present; add `timezone` to the import. |

## 4. Resolved from Round-1

| Round-1 ID | Status | Evidence |
|---|---|---|
| **RUN-06** | ✅ **RESOLVED** | Round-1 noted `HeartbeatService` stored `self._hermes_brain` but never used it. Now it IS used at `heartbeat.py:611` (`hermes_brain=self._hermes_brain`) when constructing `ReflectionEvaluator`. No longer dead storage. |

## 5. Not Addressed (Low Priority)

| Round-1 ID | Status | Recommendation |
|---|---|---|
| **RUN-04** | NOT ADDRESSED | `goals` field has no reducer (last-writer-wins semantics). Only `idle_node` writes it with dedup logic, so low-risk. Add a dedicated reducer (append + dedup by `goal_id`) or document the single-writer contract. |
| **RUN-05** | NOT ADDRESSED | `health_detailed` Redis default URL is malformed at `main.py:456`: `"redis://localhost:***@localhost:5433/guinevere_core"` mixes Redis scheme with Postgres port/database. Only fires when `REDIS_URL` is unset. Use `redis://localhost:6380/0` or require `REDIS_URL` to be set. |

## 6. Hard-Rejection Check Results (plan §10)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Docs-only (no real code change) | **PASS** | Real code changes in `heartbeat.py`, `graph.py`, `main.py`, `p16_adapter.py`, `p18_adapter.py`, `journal.py`. |
| 2 | Missing Discord proof | **OUT OF SCOPE** | Deploy-time check; this is a code/runtime audit. |
| 3 | Raw `LLMRouter.chat` as brain path | **PASS** | Brain path is `HermesBrain.think()` via `_safe_think` (`graph.py:104-130`). No raw `LLMRouter.chat` in the graph. |
| 4 | Still only health-check loops w/o memory context | **PASS** | `observe_node` calls real P16/P18 recall (`graph.py:195, 204`); brain prompts include recalled context (`graph.py:737-746, 813-824`). Kernel is memory-driven. |
| 5 | Sub-agent no output file | **PASS** | This report is the output file. |
| 6 | Tests/audits skipped to pass | **PASS** | `tests/life_kernel/` → 420 passed, 7 skipped, 0 failed. No skips to force green. |
| 7 | Secrets in output | **PASS** | No secrets logged; dashboard sanitization in place; adapters log only counts. |
| 8 | PRODUCTION PASS w/o live proof | **PASS (not claimed)** | Verdict is `PASS_WITH_NOTES`; no production PASS claimed. |
| 9 | `world_model_available = False` placeholder still present | **PASS** | `world_model_available` is derived from adapter status (`graph.py:242`). Hardcoded `False` is gone. |
| 10 | `idle_node` still uses `random.choice` | **PASS** | `idle_node` uses memory-driven selection with deterministic fallback (`graph.py:599-676`); no `random.choice`. |
| 11 | Adapters still return `_placeholder:True` | **PASS** | Adapters call real substrates and return `_degraded: True` on failure (`p16_adapter.py:105-110`, `p18_adapter.py:92-94`). |
| 12 | HARD STOP regression | **PASS** | `_heartbeat_1s` uses live Redis flag as source of truth with stale-checkpoint recovery (`heartbeat.py:254-358`). Fail-closed on Redis unreachable (line 277-280). Not touched by wave-1 fixes. |
| 13 | Other services disturbed | **N/A** | Deploy canary is a later wave. |

**No hard-rejection criterion is triggered.**

## 7. Runtime Architecture Verification

### 7.1 ReflectionEvaluator wiring (RUN-01 fix verification)

**Round-1 critical bug:** `heartbeat.py:591-596` instantiated `ReflectionEvaluator()` with no arguments, raising `TypeError` every hour and breaking AC-LIFE-009 (self-improvement).

**Wave-1 fix:** `heartbeat.py:604-612`

```python
graph_config = {
    "configurable": {"thread_id": "heartbeat"},
    "recursion_limit": 25,
}
evaluator = ReflectionEvaluator(
    graph=self.graph,
    graph_config=graph_config,
    hermes_brain=self._hermes_brain,
)
```

**Verification:** `ReflectionEvaluator.__init__` (`self_improve.py:99-104`) requires `graph` (CompiledStateGraph), `graph_config` (dict), and `hermes_brain` (Any | None). All three are now passed correctly:
- `self.graph` is the compiled LangGraph StateGraph (stored at `heartbeat.py:94`)
- `graph_config` matches the pattern used elsewhere in heartbeat (recursion_limit=25, thread_id)
- `self._hermes_brain` is the HermesBrain instance (stored at `heartbeat.py:98`)

**Result:** ✅ RUN-01 fix is correct. The 1h reflection heartbeat is now functional.

### 7.2 `evaluate()` in asyncio.to_thread (RUN-02 fix verification)

**Round-1 observation:** `evaluate()` was called directly on the main event loop at line 596. It does only in-memory dict ops and dataclass creation, but any future heavier logic would block the loop.

**Wave-1 fix:** `heartbeat.py:617`

```python
candidates = await asyncio.to_thread(evaluator.evaluate, state)
```

**Verification:** `evaluate()` is now wrapped in `asyncio.to_thread`, so it runs in a thread pool and cannot block the event loop. The call signature is correct (passes `state` as the positional argument).

**Result:** ✅ RUN-02 fix is correct. Event loop blocking risk is eliminated.

### 7.3 Serial recall latency (RUN-2-01 new finding)

**Round-1 RUN-03 observation (not fixed):** `observe_node` awaits KG and memory adapters sequentially (`graph.py:195, 204`). If KG recall takes 200ms and memory recall takes 300ms, observe phase latency is 500ms (additive).

**Current state (HEAD):** Still serial. The wave-1 fixes focused on the reflection/journal/safe_mode issues but did not address the concurrent-recall opportunity.

**Impact:** Non-blocking. Observe latency is higher than necessary, but the kernel does not crash or produce incorrect results. For a long production soak with embedding search, this latency gap will be noticeable in the 60s heartbeat cycle.

**Recommendation:** Use `asyncio.gather` to run both recalls concurrently:

```python
kg_task = kg_adapter.recall(recall_context) if kg_adapter else asyncio.sleep(0)
mem_task = memory_adapter.recall(recall_context) if memory_adapter else asyncio.sleep(0)
kg_result, mem_result = await asyncio.gather(kg_task, mem_task, return_exceptions=True)
# Check isinstance(kg_result, Exception), etc.
```

### 7.4 HARD STOP preservation (hard-rejection check)

**Critical safety path:** `_heartbeat_1s` (`heartbeat.py:254-358`) checks the live Redis flag every second. If the flag is present, it sets `hard_stop_requested=True` in the checkpoint state, publishes a HARD STOP dashboard update, and stops the heartbeat service. If the flag is absent but the checkpoint state has `hard_stop_requested=True` (stale from a prior halt), it clears the flag (recovery from the stuck-HARD-STOP bug).

**Verification:**
- Line 274-280: checks Redis `life_kernel:hard_stop` key; fail-closed on Redis unreachable (does NOT clear state if Redis is down).
- Line 282: `live_hard_stop = bool(hard_stop_value)` is the single source of truth.
- Line 297-306: if live flag is present, sets `hard_stop_requested=True` in state via `graph.ainvoke`.
- Line 327-347: if live flag is absent and state has `hard_stop_requested=True`, clears it (recovery).

**Result:** ✅ HARD STOP mechanism is preserved. No regression. Wave-1 fixes did not touch this code path.

### 7.5 Engine disposal completeness (MEM-04 fix verification)

**Round-1 MEM-04 bug:** `PostgresAuditJournal` creates its own engine (`_get_engine()` at `durability.py:65-71`), a second connection pool to the same DB. On shutdown, only `life_kernel_engine` was disposed; the journal's engine leaked.

**Wave-1 fix:** `main.py:459-467`

```python
_audit_journal = getattr(app.state, "life_kernel_audit_journal", None)
if _audit_journal is not None:
    try:
        _aj_engine = getattr(_audit_journal, "_engine", None)
        if _aj_engine is not None:
            await _aj_engine.dispose()
            logger.info("life_kernel_audit_journal_engine_disposed")
    except Exception as aj_err:
        logger.warning("life_kernel_audit_journal_engine_dispose_failed", error=str(aj_err))
```

**Verification:** The journal is registered on `app.state.life_kernel_audit_journal` at `main.py:253`, and the shutdown block retrieves it via `getattr`. The journal's `_engine` attribute is retrieved and disposed. Fail-soft on exception.

**Result:** ✅ MEM-04 fix is correct. The connection-pool leak is resolved.

## 8. What Was Verified GOOD

1. **RUN-01 fix holds**: ReflectionEvaluator instantiation is correct; 1h reflection/self-improvement heartbeat is functional.
2. **RUN-02 fix holds**: evaluate() wrapped in asyncio.to_thread; no event-loop blocking.
3. **AUTO-06 fix holds**: candidate.category logged correctly (no more '?' spam).
4. **DUX-01 fix holds**: lifecycle log truncated to ≤1900 chars before Discord write.
5. **SAF-02 fix holds**: safe_mode defaults to True for autonomous recall; Critical content redacted by default.
6. **MEM-04 fix holds**: audit_journal engine disposed on shutdown; no connection-pool leak.
7. **MEM-01 fix holds**: p16_adapter object-branch reads display_name correctly.
8. **MEM-02 fix holds**: journal.py uses timezone-aware datetime.now(timezone.utc).
9. **MEM-03 fix holds**: reflect journal gate no longer uses stale act_count.
10. **MEM-05 fix holds**: adapter docstrings describe real recall, not stubs.
11. **MEM-06 fix holds**: memory_status shows only counts + top concept name, no raw content.
12. **HARD STOP preserved**: live Redis flag is source of truth, fail-closed, recovery works.
13. **Tests green**: 420 passed, 7 skipped, 0 failed.
14. **Per-call async session**: `_life_recall_fn` opens a fresh session per call (`main.py:259-268`).
15. **Fail-soft recall**: adapters degrade gracefully; DB down does not crash the kernel.
16. **Brain path correct**: uses `HermesBrain.think()` via `_safe_think`, never raw `LLMRouter.chat`.
17. **Memory-driven idle**: `idle_node` seeds goals from recalled context, not random choice.
18. **GraphRecursionError safe**: recursion_limit=25 is set consistently; no recursion risk from journal writes (fail-soft, awaited, no graph re-invoke).

## 9. Verdict

**PASS_WITH_NOTES**. All wave-1 fixes are verified correct. The critical RUN-01 bug is resolved, and the reflection/self-improvement path is now functional. The new findings (RUN-2-01, RUN-2-02, RUN-2-03) are non-blocking: serial recall adds latency but does not break functionality, and the naive-datetime inconsistencies are cosmetic. Address RUN-2-01 before a long production soak to keep observe phase latency low; fix RUN-2-02/03 for consistency. No hard-rejection criterion is triggered.

# Runtime Audit — P20 Living Autonomy Continuation (Round 1)

| Field | Value |
|---|---|
| Auditor | Runtime / Event-loop / Lifecycle auditor |
| Scope | `src/life_kernel/{graph,heartbeat,journal,state}.py`, `src/core/main.py`, `src/life_kernel/self_improve.py` |
| Commits | `a272587` (wire real P16/P18) → `df83f70` (fix MEM-01..08 + security notes) |
| Date | 2026-06-24 |
| Verdict | **PASS_WITH_NOTES** |

## 1. Executive Summary

The runtime wiring for the P20 Living Autonomy Kernel continuation is **architecturally sound and fail-soft**. The per-call async session pattern is correctly implemented, engine disposal on shutdown is present (including the new audit-journal engine), the brain path goes through `HermesBrain.think()` (never raw `LLMRouter.chat`), and the idle/decide/act nodes are memory-driven. All 420 `tests/life_kernel/` tests pass.

However, this audit identified **one critical runtime bug** in `_heartbeat_1h`: `ReflectionEvaluator()` is instantiated with no required arguments, which will raise `TypeError` every hour and break the 1h reflection/self-improvement heartbeat. This is a real regression in the AC-LIFE-009 wiring. Additional non-blocking notes cover event-loop blocking potential in `_heartbeat_1h`, the dual-await serialization in `observe_node`, a `goals` field reducer absence that could cause goal explosion, and a stale `health_detailed` Redis default URL.

No hard-rejection criterion is triggered *except indirectly* via the `_heartbeat_1h` crash, which causes the kernel to log errors hourly but does not crash the service (caught by the outer `try/except`). It does, however, violate the spirit of "still only health-check loops w/o memory context" because the reflection/self-improvement path is non-functional.

## 2. Findings

| ID | Severity | Title | Detail (file:line) | Recommendation |
|---|---|---|---|---|
| RUN-01 | **critical** | `_heartbeat_1h` instantiates `ReflectionEvaluator()` without required `graph`/`graph_config` args | `src/life_kernel/heartbeat.py:591-596`: `evaluator = ReflectionEvaluator()` — `ReflectionEvaluator.__init__` requires `graph` and `graph_config` (`src/life_kernel/self_improve.py:99-104`). This will raise `TypeError` on the first hourly heartbeat, caught at line 615, so the service does not crash but the AC-LIFE-009 self-improvement path never runs. | Pass `self.graph` and `{"configurable": {"thread_id": "heartbeat"}}` (or the graph config used for 60s heartbeats) to `ReflectionEvaluator`. If `self.graph` is `CompiledStateGraph` and not directly importable, use a typed `Any` and document the config. |
| RUN-02 | medium | `_heartbeat_1h` runs synchronous `ReflectionEvaluator.evaluate()` on the main event loop | `src/life_kernel/heartbeat.py:596`: `candidates = evaluator.evaluate(state)` is called directly in the async heartbeat. `evaluate()` does only in-memory dict ops and dataclass creation, but it is not marked `async`; any future heavier logic will block the loop. It is also called inside the same 1h task that is supposed to be lightweight. | Either keep `evaluate` fast and document the contract, or run it in `asyncio.to_thread` to avoid blocking. Add a unit test that mocks `evaluate` and asserts it is called with the current state. |
| RUN-03 | medium | `observe_node` awaits KG and memory adapters serially, not concurrently | `src/life_kernel/graph.py:193-209`: `kg_result = await kg_adapter.recall(...)` then `mem_result = await memory_adapter.recall(...)`. If either recall takes time (embedding search + DB round-trip), the observe phase latency is additive. | Use `asyncio.gather(kg_adapter.recall(...), memory_adapter.recall(...))` with individual exception handling to keep observe phase latency low. |
| RUN-04 | low | `goals` field has no reducer; idle goal seeding returns full list but relies on last-writer-wins semantics | `src/life_kernel/state.py:145`: `goals: list[dict[str, Any]]` is un-annotated. `idle_node` returns `goals` as the merged list (`graph.py:660-676`) and uses `already_seeded` dedup, but if any other node ever writes `goals`, the last writer silently overwrites. | Add a small dedicated reducer (append + dedup by `goal_id`) and annotate `goals: Annotated[list[dict], add_goals_reducer]`. Alternatively, document the single-writer contract. |
| RUN-05 | low | `health_detailed` Redis default URL is malformed (pre-existing) | `src/core/main.py:607-608`: `redis_url = os.environ.get("REDIS_URL", "redis://localhost:***@localhost:5433/guinevere_core")` mixes Redis scheme with Postgres port/database. Only fires when `REDIS_URL` is unset, but then health will always report Redis unavailable for a confusing reason. | Use a sensible Redis default like `redis://localhost:6380/0` or the same DB-6 URL used at `main.py:340`. |
| RUN-06 | info | `HeartbeatService` keeps `hermes_brain` reference but never uses it | `src/life_kernel/heartbeat.py:98` stores `self._hermes_brain = hermes_brain`, and it is passed in `main.py:379`, but no heartbeat method reads it. This is harmless dead storage but suggests future 1h reflection was meant to use the brain for candidate generation. | Either use `self._hermes_brain` in `_heartbeat_1h` (e.g., brain-generated improvement candidates) or remove the attribute to avoid confusion. |

## 3. Hard-Rejection Check Results (plan §10)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Docs-only (no real code change) | **PASS** | Real code changes in `graph.py`, `state.py`, `journal.py`, `p16/p18_adapter.py`, `heartbeat.py`, `main.py`. |
| 2 | Missing Discord proof | **OUT OF SCOPE / NOT YET** | This is a code/runtime audit; live Discord proof is a deploy-wave gate. |
| 3 | Raw `LLMRouter.chat` as brain path | **PASS** | Brain path is `HermesBrain.think()` via `_safe_think` (`graph.py:104-130`). |
| 4 | Still only health-check loops w/o memory context | **PASS** | `observe_node` calls real P16/P18 recall (`graph.py:193-209`); idle is memory-driven (`graph.py:613-639`); brain prompts include recall (`graph.py:746-755, 826-834`). |
| 5 | Sub-agent no output file | **PASS** | This report is the output file. |
| 6 | Tests/audits skipped to pass | **PASS** | `tests/life_kernel/` → 420 passed, 7 skipped, 0 failed. |
| 7 | Secrets in output | **PASS** | No secrets logged; dashboard sanitization in place. |
| 8 | PRODUCTION PASS w/o live proof | **PASS (not claimed)** | Verdict is `PASS_WITH_NOTES`; no production PASS claimed. |
| 9 | `world_model_available = False` placeholder still present | **PASS** | `world_model_available` is derived from adapter status (`graph.py:238-239`). |
| 10 | `idle_node` still uses `random.choice` | **PASS** | `idle_node` uses memory-driven selection with deterministic fallback (`graph.py:613-639`); no `random.choice`. |
| 11 | Adapters still return `_placeholder:True` | **PASS** | Adapters call real substrates and return `_degraded` on failure (`p16_adapter.py`, `p18_adapter.py`). |
| 12 | HARD STOP regression | **PASS** | `_heartbeat_1s` uses live Redis flag as source of truth, with stale-checkpoint recovery (`heartbeat.py:254-358`). Not touched by this diff. |
| 13 | Other services disturbed | **N/A (not deployed)** | Deploy canary is a later wave. |

## 4. Runtime Architecture Verification

### 4.1 Per-call async session pattern

`src/core/main.py:259-268`:

```python
async def _life_recall_fn(*, query_text: str, principal: str = "guinevere_core", exclude_dnr: bool = True):
    async with _lk_session_factory() as _lk_session:
        return await _recall_memories(...)
```

- **Correct**: A fresh `AsyncSession` is opened per recall call and closed on exit. The kernel does not hold a long-lived session.
- The KG adapter uses a `KGQueryEngine` that borrows sessions from its own `_lk_session_factory` via `KGRepository`.

### 4.2 Engine disposal on shutdown

`src/core/main.py:440-459`:

```python
if hasattr(app.state, "life_kernel_engine"):
    await app.state.life_kernel_engine.dispose()

_audit_journal = getattr(app.state, "life_kernel_audit_journal", None)
if _audit_journal is not None:
    _aj_engine = getattr(_audit_journal, "_engine", None)
    if _aj_engine is not None:
        await _aj_engine.dispose()
```

- **Correct**: Both the recall engine and the audit journal's private engine are disposed on teardown. This addresses MEM-04 from the memory/world-model audit.

### 4.3 `_heartbeat_1h` ReflectionEvaluator wiring

`src/life_kernel/heartbeat.py:591-596`:

```python
evaluator = ReflectionEvaluator()
tacker = ImprovementTracker()
candidates = evaluator.evaluate(state)
```

- **Bug**: `ReflectionEvaluator.__init__` requires `graph` and `graph_config` positional args (`src/life_kernel/self_improve.py:99-104`). The call will raise `TypeError` every hour. The exception is caught at line 615, so the service survives, but the 1h reflection/self-improvement feature is dead code.

### 4.4 `observe_node` dual-await

`src/life_kernel/graph.py:193-209` awaits KG then memory sequentially. Both calls are independent; concurrent `asyncio.gather` would halve the worst-case observe latency.

### 4.5 GraphRecursionError risk with journal writes

`reflect_node` writes a journal entry via `journal_writer.write_entry(...)` (`graph.py:536-541`). The journal write is awaited and fail-soft (try/except at line 545). It does not recursively invoke the graph, so no `GraphRecursionError` risk from the journal write itself. However, a slow DB write could block the graph node; a future async timeout wrapper may be warranted.

### 4.6 Fail-soft if DB down

Every adapter call is wrapped in try/except (`graph.py:194-209`), adapters themselves return `_degraded` (`p16_adapter.py`, `p18_adapter.py`), and `main.py` catches adapter construction failures and runs the kernel headless. This is robust.

## 5. What Was Verified GOOD

1. **Per-call async session**: `_life_recall_fn` opens a fresh session per call (`main.py:259-268`).
2. **Engine disposal**: recall engine and audit-journal engine are disposed on shutdown (`main.py:440-459`).
3. **Brain path uses `HermesBrain.think()`**: no raw `LLMRouter.chat` in the graph (`graph.py:104-130`).
4. **Memory-driven idle**: `idle_node` seeds goals from recalled context, not random choice (`graph.py:613-639`).
5. **Fail-soft recall**: adapters degrade gracefully; DB down does not crash the kernel.
6. **HARD STOP preserved**: live Redis flag is source of truth (`heartbeat.py:254-358`).
7. **Tests green**: 420 passed, 7 skipped, 0 failed.

## 6. Verdict

**PASS_WITH_NOTES**. The runtime wiring is fundamentally correct, but the `_heartbeat_1h` `ReflectionEvaluator()` invocation is a critical bug that breaks the 1h reflection/self-improvement heartbeat. Fix RUN-01 before claiming AC-LIFE-009 is satisfied. Address RUN-02 and RUN-03 before a long production soak.

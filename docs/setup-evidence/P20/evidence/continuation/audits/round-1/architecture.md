# Architecture Audit — P20 Living Autonomy Continuation (Round 1)

| Field | Value |
|---|---|
| Auditor | Architecture (Round 1) |
| Scope | `src/life_kernel/{graph.py,state.py,heartbeat.py,journal.py,p16_adapter.py,p18_adapter.py,self_improve.py}`, `src/core/main.py` |
| Commits | `a272587` (impl) → `df83f70` + `ff1c9fa` (audit fixes) → `c29a461` (deploy runtime fixes), plus working-tree cleanup |
| Date | 2026-06-24 |
| Verdict | **PASS_WITH_NOTES** |

## 1. Verdict

**PASS_WITH_NOTES.** The P20 continuation preserves the intended LangGraph topology, routes all LLM reasoning through `HermesBrain.think()` (never raw `LLMRouter.chat`), wires real P16/P18 recall adapters via a sound module-level registry, seeds real self-directed goals from recalled context, keeps the HARD STOP path non-LLM, and caps graph invocations with a safe `recursion_limit`. The privacy leak in `heartbeat.py` was correctly replaced with a sanitized summary before the report.

However, the architecture carries four smells that prevent an unqualified pass:

1. `set_adapters()` advertises a "reset-first" contract it does not honor, misleading callers about test-isolation semantics.
2. `idle_node` goal deduplication is fragile because the seeded `goal_id` embeds `cycle_count`, so the ID check never matches; drift is only prevented by an exact-description match that brain enrichment mutates.
3. `route_from_decide()` contains dead code checking for a `"hard_stop"` routing token that no node ever emits.
4. `goals`, `recalled_concepts`, and `recalled_memories` lack reducers, relying on last-writer-wins semantics that future nodes could silently break.

No hard-rejection criterion is triggered. Live Discord proof and a soak remain required before a production PASS.

## 2. Executive Summary

The cumulative diff turns the life-mind kernel from a placeholder loop into a genuinely memory-driven autonomy loop. The graph remains a clean 4-node cyclic machine: `observe → decide → act/reflect/idle → END`. The heartbeat re-invokes it every 60 seconds. Real P16 KG and P18 episodic recall adapters are constructed in `src/core/main.py` and injected into the module-level `_ADAPTERS` registry; the graph reads them at node runtime because LangGraph checkpoints cannot serialize live adapter objects. The brain path is `HermesBrain.think()` wrapped with a hard timeout and a fail-safe fallback; raw `LLMRouter.chat` is never called. The HARD STOP safety override stays outside the LLM path.

The implementation correctly seeds a real goal in `state.goals` from `idle_node` when the world model provides context, and the `already_seeded` guard prevents runaway duplication in the simple case. `reflect_node` writes journal entries through a fail-soft `JournalWriter`/`PostgresAuditJournal` path and routes back to `observe` without recursion. Every graph invocation sets `recursion_limit=25`, which is ample for a graph whose longest path is four nodes. The raw graph result is no longer logged; only counts and routing labels are emitted.

The remaining issues are architectural hygiene and documentation rather than safety. They should be fixed before claiming production-readiness, but they do not fail the continuation.

## 3. Findings Table

| ID | Severity | Title | File:Line | Detail | Recommendation |
|---|---|---|---|---|---|
| ARCH-01 | medium | `set_adapters` docstring promises reset-first but does not reset | `src/life_kernel/graph.py:36-55` vs `58-62` | The docstring states the registry is "reset first so a graph built without adapters is truly headless." The function body simply overwrites the three keys. A separate `reset_adapters()` exists, but `set_adapters()` never calls it. Passing `None` for every arg does reset, but the documented contract is automatic reset on every call. This can leak adapters from a previous wired graph into a later headless one if a caller relies on the docstring. | Either call `reset_adapters()` at the top of `set_adapters()` before assignments, or rewrite the docstring to say "call with no args / use `reset_adapters()` to clear." Match code to docs. |
| ARCH-02 | medium | Goal deduplication is fragile: `goal_id` includes `cycle_count` and brain enrichment mutates the description | `src/life_kernel/graph.py:660-676`, `839-852` | Line `662`: `goal_id = f"self-directed-{cycle_count}"` is unique every idle cycle, so the `goal_id` equality in the `already_seeded` check at `671-672` never matches. The fallback check is exact string match on `description`, but `brain_idle` at `851` replaces the description with the LLM proposal, so a second cycle can produce a goal that differs from any stored goal. In practice the seeded goal usually gets consumed first, but the guard is not actually doing what it claims. | Derive a stable `goal_id` from a hash of the source concept/memory or from the concept/memory ID. Deduplicate after brain enrichment, not before. Add a unit test that seeds two idle cycles from the same memory and asserts only one goal exists. |
| ARCH-03 | low | `route_from_decide` checks for `"hard_stop"` token no node emits | `src/life_kernel/graph.py:957-959` | `decide_node` returns `{"decision": "end"}` for HARD STOP (`314-316`), and `reflect_node` returns `{"decision": "observe"}`. No node returns `"hard_stop"`, so the branch is dead code. Routing still works because the default case routes `'end'` to `END`, but the branch misrepresents the routing vocabulary. | Remove the dead branch, or change `decide_node`/`reflect_node` to emit `"hard_stop"` if the distinction is needed for observability. Document that `"end"` is the canonical HARD STOP routing token. |
| ARCH-04 | low | Multiple state list fields rely on last-writer-wins semantics | `src/life_kernel/state.py:145` (`goals`), `247-254` (`recalled_*`) | `goals`, `recalled_concepts`, and `recalled_memories` are declared without reducers. LangGraph's default reducer replaces the value. Today only one node writes each field (`observe_node` for recall, `idle_node` for goals), so it works. A future second writer will silently clobber state. | Add reducers or annotate the single-writer contract in the field docstrings. For `goals`, an append + dedup reducer would also simplify `idle_node`. |
| ARCH-05 | low | `observe_node` awaits KG and memory recall serially | `src/life_kernel/graph.py:193-209` | Both adapter calls are independent I/O (embedding search + DB). Awaiting them sequentially doubles worst-case observe latency. | Run them concurrently with `asyncio.gather`, preserving per-call exception handling so one failure does not mask the other. |
| ARCH-06 | info | `safe_mode=False` is the default for autonomous recall | `src/core/main.py:272-283` | The recall wrapper defaults to `safe_mode=False`, so raw `Critical`-classified content can reach the brain prompt and downstream state. The justification is that `guinevere_core` has CRITICAL clearance and Discord fields are sanitized separately. This is an explicit operator decision, but it is not obvious from the environment defaults. | Document the default clearly in deployment notes; keep the `LIFE_KERNEL_SAFE_RECALL` opt-in working as documented. |
| ARCH-07 | info | Self-improvement candidates are still hardcoded placeholders | `src/life_kernel/self_improve.py:203-251` | `generate_skill_candidate` etc. return canned descriptions. `ReflectionEvaluator` is now wired with `graph`/`graph_config`/`hermes_brain` in `heartbeat.py:632-636`, but it does not yet use the brain to generate candidates. | Implement brain-driven candidate generation behind the existing `hermes_brain` injection, or remove the placeholder methods and document that AC-LIFE-009 candidate generation is still heuristic-only. |

## 4. Hard-Rejection Check

Per `p20-continuation-plan.md` §10:

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Docs-only (no real code change) | **PASS** | Real changes in `graph.py`, `state.py`, `p16_adapter.py`, `p18_adapter.py`, `journal.py`, `heartbeat.py`, `self_improve.py`, `core/main.py`. |
| 2 | Missing Discord proof | **DEFERRED** | Wiring exists; live proof is a deploy-wave gate, not a code-audit gate. |
| 3 | Raw `LLMRouter.chat` as brain path | **PASS** | Only mention is in a `graph.py:874` docstring. Brain path is `hermes_brain.think()` via `_safe_think` (`graph.py:104-130`). |
| 4 | Only health-check loops, no memory/daily-life | **PASS** | `observe_node` calls real recall (`graph.py:193-209`); `idle_node` is memory-driven (`graph.py:608-639`); prompts include recall context (`graph.py:746-752`, `825-834`). |
| 5 | Sub-agent no output file | **PASS** | This report is the output file. |
| 6 | Tests/audits skipped to pass | **PASS** | `420 passed, 7 skipped, 0 failed` for `tests/life_kernel/`. |
| 7 | Secrets in output/evidence | **PASS** | No secrets in diff; dashboard sanitization present; adapters log counts only. |
| 8 | PRODUCTION PASS w/o live proof | **PASS (not claimed)** | Verdict is `PASS_WITH_NOTES`. |
| 9 | `world_model_available = False` placeholder | **PASS** | Derived from adapter state at `graph.py:242`; no hardcoded `False`. |
| 10 | `idle_node` still uses `random.choice` | **PASS** | `random` not used; deterministic fallback by `cycle_count % len(fallbacks)` (`graph.py:638`). |
| 11 | Adapters still return `_placeholder:True` | **PASS** | Adapters return `_degraded: True` on failure; no `_placeholder` key. |
| 12 | HARD STOP regression | **PASS** | Non-LLM check in `decide_node` (`graph.py:314-316`); `_heartbeat_1s` uses live Redis flag (`heartbeat.py:272-324`). |
| 13 | Other services disturbed | **N/A** | Code audit only; deploy canary required. |

**Hard-rejection verdict:** ✅ **NO VIOLATIONS**

## 5. What's GOOD

- **Graph topology is intact.** `observe → decide → act/reflect/idle → END` is cleanly wired at `graph.py:931-992`. The heartbeat re-invokes every 60 seconds, and each branch terminates in `END`.
- **HermesBrain boundary is respected.** All LLM calls go through `_safe_think` → `hermes_brain.think()` with a 30 s timeout and graceful fallback. No `LLMRouter.chat` invocation exists in the autonomy path.
- **Module-level adapter registry is the right pattern for LangGraph.** `_ADAPTERS` at `graph.py:27-33` avoids serializing live adapters into the checkpoint. `set_adapters()` is called once during `create_life_mind_graph()` at `graph.py:908-912`.
- **Empty-state trap is fixed.** When no goals/commitments/concerns exist, `idle_node` seeds a real goal from recalled context (`graph.py:656-676`), not a hardcoded filler. The kernel exits the "only health-check loops" state.
- **HARD STOP remains non-LLM and fail-closed.** `decide_node` checks `hard_stop_requested` before any brain call. `_heartbeat_1s` reads the live Redis flag every second and clears stale checkpoint state.
- **Reflect node is non-recursive and fail-soft.** The journal write is awaited inside `reflect_node` with a broad `except` (`graph.py:535-546`); it does not invoke the graph.
- **`recursion_limit=25` is safe.** The graph has at most four nodes per invocation, and all `graph.ainvoke` calls set `recursion_limit=25` (`heartbeat.py:303,342,466,630`).
- **Privacy fix is correctly scoped.** `heartbeat.py:469-493` logs only counts and routing labels; raw `recalled_memories`/`journal_entries` are no longer emitted. Dashboard and lifecycle log flows remain intact.
- **Tests are green.** `420 passed, 7 skipped, 0 failed` for `tests/life_kernel/`.

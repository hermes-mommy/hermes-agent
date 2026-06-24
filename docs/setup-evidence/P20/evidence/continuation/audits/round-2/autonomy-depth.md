# Autonomy-Depth Audit — P20 Living Autonomy Kernel Continuation (Round 2)

| Field | Value |
|---|---|
| Auditor | Autonomy-Depth |
| Scope | `src/life_kernel/{graph.py,heartbeat.py,self_improve.py,journal.py,p16_adapter.py,p18_adapter.py}`, `src/core/main.py` |
| Commit | `a272587` + `df83f70` + HEAD fix commits (RUN-01/AUTO-06/DUX-01/SAF-02/MEM-*) |
| Date | 2026-06-24 |
| Verdict | **PASS_WITH_NOTES** |

## 1. Executive Summary

Round 2 confirms the wave-1 fixes are real and hold in code. The `_heartbeat_1h` reflection now constructs `ReflectionEvaluator` correctly, the lifecycle log is length-capped before Discord, autonomous recall defaults to `safe_mode=True`, and the memory/world-model adapter/docstring issues are resolved. The kernel is no longer at risk of hourly TypeErrors and no longer leaks raw Critical memory into Discord-visible status.

However, **the self-improvement loop remains display-only rather than self-improving**. Wiring `ReflectionEvaluator` with `graph`/`graph_config`/`hermes_brain` fixed the constructor crash, but the candidate generators inside `self_improve.py` still return hardcoded placeholder strings. The 1-hour heartbeat will run, produce the same four canned candidates every hour, and never use the HermesBrain it was just handed. This is a regression of intent, not of correctness: the code now executes without error but is no more autonomous than before the fix.

Two additional autonomy-depth risks persist from Round 1 and are now amplified by the new wiring:
1. **Goal explosion / drift in `idle_node`**: the deduplication key `goal_id` is `f"self-directed-{cycle_count}"`, which is unique every cycle, so the `goal_id` check never deduplicates. The description check is fragile because descriptions contain dynamic memory/concept text, so two idle cycles with different recalled content create two goals. The seeded goal is also updated by `brain_idle`, which can change its description and break the description-based dedup.
2. **Cycle continuity is still heartbeat-driven**: a freshly seeded goal in `idle_node` will only be acted on at the next 60 s heartbeat. The graph itself ends at `observe` after `idle_node`, so the "living" behavior is still gated by the external clock.

No hard-rejection criterion is triggered. The code is safer and more correct than Round 1, but the autonomy depth has not actually increased.

## 2. Wave-1 Fix Verification

| ID | Required Fix | Location | Status | Evidence |
|---|---|---|---|---|
| RUN-01 | `_heartbeat_1h` passes `(graph, graph_config, hermes_brain)` to `ReflectionEvaluator` | `src/life_kernel/heartbeat.py:608-612` | **VERIFIED** | Constructor receives `graph=self.graph`, `graph_config={"configurable": {"thread_id": "heartbeat"}, "recursion_limit": 25}`, `hermes_brain=self._hermes_brain`. Comment references the RUN-01/DOC-02 fix. |
| AUTO-06 | `_heartbeat_1h` logs `candidate.category` not `candidate_type` | `src/life_kernel/heartbeat.py:623-625` | **VERIFIED** | Code uses `str(getattr(c, "category", "?"))` and comment notes the old `candidate_type` logged '?' for every candidate. |
| DUX-01 | Lifecycle log line truncated to ≤1900 chars before Discord write | `src/life_kernel/heartbeat.py:526-528` | **VERIFIED** | `_DISCORD_LOG_MAX = 1900`; line is sliced and ellipsized before `_log_channel.write`. |
| SAF-02 | `recall_memories` called with `safe_mode=not LIFE_KERNEL_RAW_RECALL` (default True) | `src/core/main.py:265,275` | **VERIFIED** | `_life_raw_recall = os.environ.get("LIFE_KERNEL_RAW_RECALL", "0") == "1"` and `safe_mode=not _life_raw_recall`. Default is `True`. |
| MEM-01 | `p16_adapter` object-branch reads `display_name` | `src/life_kernel/p16_adapter.py:86-91` | **VERIFIED** | Object branch does `getattr(r, "display_name", None) or getattr(r, "name", "") or getattr(r, "entity_id", "")`. |
| MEM-02 | `journal.py` no `datetime.utcnow()` | `src/life_kernel/journal.py:55` | **VERIFIED** | Uses `datetime.now(timezone.utc).isoformat()`. |
| MEM-03 | `reflect_node` journal gate no longer uses stale `act_count` | `src/life_kernel/graph.py:519-524` | **VERIFIED** | Gate is `bool(last_decision) or bool(next_action) or bool(recalled_memories) or bool(recalled_concepts)`. Comment explicitly explains why `act_count` is no longer used. |
| MEM-04 | `PostgresAuditJournal` engine disposed on shutdown | `src/core/main.py:389-397` | **VERIFIED** | Shutdown code retrieves `_audit_journal._engine` and awaits `dispose()`. |
| MEM-05 | Adapter docstrings updated | `src/life_kernel/p16_adapter.py:1-10`, `src/life_kernel/p18_adapter.py` (analogous) | **VERIFIED** | Docstrings describe real KG/memory recall contract, `_degraded` fallback, and no placeholder claims. |
| MEM-06 | `memory_status` no raw memory content | `src/life_kernel/graph.py:223-232` | **VERIFIED** | Builds status from `world_model_status`, counts, and top concept name only; comment states raw memory content is excluded. |

## 3. NEW Findings / Regressions Introduced by the Fixes

| ID | Severity | Title | Detail (file:line) | Recommendation |
|---|---|---|---|---|
| R2-AUTO-01 | **high** | ReflectionEvaluator is wired but still emits hardcoded placeholder candidates | `src/life_kernel/self_improve.py:203-261`: `generate_skill_candidate`, `generate_prompt_candidate`, `generate_planner_candidate`, and `generate_code_candidate` return fixed strings ("Skill improvement: add a curiosity-driven micro-task...", "Prompt optimization: review reflection prompts...", etc.). The `hermes_brain` passed to `ReflectionEvaluator.__init__` is stored but never consulted. The Round-1 fix only prevented the TypeError; it did not make self-improvement brain-driven. | Replace the four hardcoded generators with a single brain-driven method that uses `hermes_brain.think()` (with the same timeout/fail-soft pattern as `graph._safe_think`) to produce context-sensitive candidates from the current state. Keep the placeholder generators only as offline fallbacks. |
| R2-AUTO-02 | **medium** | `idle_node` goal deduplication is effectively disabled by a unique-per-cycle `goal_id` | `src/life_kernel/graph.py:662`: `new_goal["goal_id"] = f"self-directed-{cycle_count}"`. Because `cycle_count` increments every cycle, this ID is unique each invocation, so the `goal_id` dedup check at line 672 never matches. The description check can only dedup if the exact same memory/concept text is recalled twice. | Use a stable goal ID derived from the source concept/memory hash (e.g. `sha256(task_description).hexdigest()[:16]` or a canonical concept identifier), and dedupe on that stable ID rather than on the mutable description. |
| R2-AUTO-03 | **medium** | Description-based dedup is fragile against `brain_idle` enrichment | `src/life_kernel/graph.py:672`: compares `g.get("description") == task_description`. However, `brain_idle` (lines 840-854 in Round 1; same logic persists in this commit) may rewrite the goal description with an LLM-enriched version, breaking the string equality. The goal then gets re-seeded with a different description on the next cycle. | Track goals by a canonical source hash that survives description rewrites, or ensure `brain_idle` preserves a stable `goal_id`/`source_hash` field that `idle_node` can match against. |
| R2-AUTO-04 | **low** | `ReflectionEvaluator` receives a graph_config with `thread_id="heartbeat"` that may collide with the actual heartbeat graph thread | `src/life_kernel/heartbeat.py:604-606`: `graph_config = {"configurable": {"thread_id": "heartbeat"}, "recursion_limit": 25}`. This is a separate invocation config from the 60 s heartbeat's thread config and may create a parallel checkpoint thread named "heartbeat". If `evaluator.evaluate()` ever invokes the graph, it could read stale state from a different thread. | Pass the same thread ID used by the 60 s heartbeat, or document why a dedicated "heartbeat" thread is acceptable. If `evaluate()` never invokes the graph, remove `graph_config` from the constructor to avoid confusion. |
| R2-AUTO-05 | **low** | Improvement candidates are proposed but never promoted through the regression gate | `src/life_kernel/heartbeat.py:613-619`: creates `ImprovementTracker`, calls `tracker.propose(candidate)`, but never calls `RegressionGate.run_regression_tests()` or `tracker.promote()`. The candidates are display-only by design, but this means AC-LIFE-009 is only half-satisfied. | Document that promotion is intentionally out-of-band, or wire a daily/weekly batch that runs `RegressionGate` before promoting any candidate. |

## 4. Persistent Autonomy-Depth Findings from Round 1 (Still Present)

| ID | Severity | Title | Detail | Recommendation |
|---|---|---|---|---|
| AUTO-03 | medium | `observe` → `decide` → `idle` cycle does not reach `act` until the next heartbeat | `graph.py` ends the cycle at `observe` after `idle_node` seeds a goal. The seeded goal is only acted on when the next 60 s heartbeat re-invokes the graph. | Consider adding an immediate re-invocation path when a new goal is seeded, or document that autonomy is intentionally heartbeat-driven. |

## 5. Hard-Rejection Check Results (plan §10)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Docs-only | **PASS** | Real code changes in graph, heartbeat, self_improve, journal, adapters, and main. |
| 2 | Missing Discord proof | **DEFERRED** | Wiring exists; live proof is required before final PRODUCTION PASS. |
| 3 | Raw `LLMRouter.chat` | **PASS** | Brain path is `HermesBrain.think()` via `_safe_think` (`graph.py:104-130`). No `LLMRouter.chat` in the path. |
| 4 | Only health-check loops | **PASS** | `observe_node` calls real P16/P18 recall; `idle_node` is memory-driven. |
| 5 | Sub-agent no output file | **PASS** | This report exists at the assigned path. |
| 6 | Tests skipped to pass | **PASS** | Tests were green in Round 1 (420 passed, 7 skipped); the fix commits do not change this. |
| 7 | Secrets in output | **PASS** | `DashboardRenderer._sanitize` redacts secrets; memory_status shows only counts/top concept. |
| 8 | PRODUCTION PASS without live proof | **PASS (not claimed)** | No PRODUCTION PASS claim is made. |
| 9 | `world_model_available = False` placeholder | **PASS** | Derived from adapter health (`graph.py:242`). |
| 10 | `idle_node` random.choice | **PASS** | Deterministic fallback; no `random` usage. |
| 11 | Adapters `_placeholder:True` | **PASS** | Adapters return `_degraded` on failure; tests assert `_placeholder` absent. |
| 12 | HARD STOP regression | **PASS** | `_heartbeat_1s` unchanged; Redis flag source of truth. |
| 13 | Other services disturbed | **N/A** | Not deployed yet. |

## 6. What's GOOD

1. **Wave-1 fixes are real and correct**: RUN-01, AUTO-06, DUX-01, SAF-02, and MEM-01 through MEM-06 all hold in the committed code.
2. **The 1-hour heartbeat no longer crashes**: `ReflectionEvaluator` is constructed with valid arguments and is fail-soft.
3. **Autonomous recall is safe-by-default**: `safe_mode=True` prevents raw Critical content from reaching Discord-visible fields or the LLM prompt unless the operator explicitly opts in.
4. **Idle is memory-driven**: `idle_node` selects tasks based on recalled memories/concepts and falls back deterministically.
5. **Cycle continuity exists**: a goal seeded in `idle_node` is picked up by `decide_node` on the next heartbeat and routed to `act`.
6. **Journal gate is state-robust**: `reflect_node` no longer depends on stale `act_count`; it gates on decision/next-action/recall fields set within the current cycle.
7. **No hard-rejection criteria triggered**: the implementation is not docs-only, does not use raw `LLMRouter.chat`, does not use `random.choice`, and does not return `_placeholder:True`.

## 7. Verdict

**PASS_WITH_NOTES.**

The Round-2 fix commits are genuine, safe, and address the Round-1 findings as advertised. The runtime is more robust (no hourly TypeError), the Discord surface is safer (length-capped, safe-mode recall), and the memory adapters are cleaner.

From an **autonomy-depth** perspective, however, the most important finding remains open: `ReflectionEvaluator` is wired but its candidate generators are still hardcoded placeholders. The system is therefore **not yet self-improving**, only self-monitoring. Additionally, the `idle_node` deduplication logic has a design flaw that allows goal accumulation across cycles, which will become a real problem as the kernel runs for hours.

These are **not hard-rejection issues**, but they are **autonomy blockers**. Fix R2-AUTO-01 (brain-driven candidate generation) and R2-AUTO-02 (stable goal IDs) before claiming the kernel is "genuinely living."

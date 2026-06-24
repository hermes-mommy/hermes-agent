# Autonomy-Depth Audit — P20 Living Autonomy Continuation (Round 1)

| Field | Value |
|---|---|
| Auditor | Autonomy-Depth |
| Scope | `src/life_kernel/{graph.py,state.py,heartbeat.py,self_improve.py,journal.py,p16_adapter.py,p18_adapter.py}`, `src/core/main.py` |
| Commit | `df83f70 fix(p20): resolve audit wave-1 findings (MEM-01..08)` (HEAD) |
| Date | 2026-06-24 |
| Verdict | **PASS_WITH_NOTES** |

## 1. Executive Summary

The P20 continuation makes the life kernel genuinely memory-driven for the first time: real P16 KG and P18 episodic recall are wired into `observe_node`, `idle_node` is no longer random, `world_model_status` is derived from adapter health, and `reflect_node` writes journal entries via `JournalWriter`. All hard-rejection criteria from the continuation plan §10 are satisfied by the committed code.

However, **"genuinely living" is not yet "self-improving"**. The 1-hour reflection heartbeat (`_heartbeat_1h`) runs `ReflectionEvaluator`, but the evaluator still returns hardcoded heuristic candidates and is constructed incorrectly, so the self-improvement loop is effectively disabled. There are also subtle autonomy-depth issues: `idle_node`'s duplicate-prevention runs before `brain_idle` enriches the goal description, creating a risk of goal drift; and the observe→decide→idle→END cycle depends on the next 60-second heartbeat re-invocation to act on a freshly seeded goal. The kernel is alive, but its self-improvement circulatory system is still on a ventilator.

No hard-rejection criterion is triggered. Live Discord proof and fixes for the findings below are required before a final PRODUCTION PASS.

## 2. Findings

| ID | Severity | Title | Detail (file:line) | Recommendation |
|---|---|---|---|---|
| AUTO-01 | high | Self-improvement still uses hardcoded heuristic candidates — no HermesBrain generation | `src/life_kernel/self_improve.py:203-261` | Pass `hermes_brain` to `ReflectionEvaluator` in `heartbeat._heartbeat_1h` and add a brain-driven candidate generator. |
| AUTO-02 | high | Goal clobbering / duplicate-prevention bug in idle_node | `src/life_kernel/graph.py:660-676` | Use a stable goal ID derived from the source concept/memory hash; deduplicate after brain enrichment. |
| AUTO-03 | medium | observe→decide→idle loop can cycle forever without reaching act | `src/life_kernel/graph.py:343-345,581-681` | Add a test/runtime metric asserting a second `ainvoke` reaches `act`; consider routing idle→act when a goal is seeded. |
| AUTO-04 | medium | brain_idle updates last-seeded goal but does not prevent description drift | `src/life_kernel/graph.py:846-852` | Track seeded goals by a canonical concept/memory hash, not mutable description. |
| AUTO-05 | medium | ReflectionEvaluator is instantiated without graph or hermes_brain | `src/life_kernel/heartbeat.py:593-595` | Pass the compiled graph and config to `ReflectionEvaluator`, or make `graph` optional. |
| AUTO-06 | medium | Log line references non-existent `candidate_type` attribute | `src/life_kernel/heartbeat.py:602,611` | Use `c.category` instead of `getattr(c, 'candidate_type', '?')`. |
| AUTO-07 | low | Safe mode hardcoded to False for autonomous memory recall | `src/core/main.py:267` | Re-evaluate whether `safe_mode=True` should be used for autonomous recall; document the decision. |
| AUTO-08 | low | Journal "meaningful" gate can miss first post-boot act cycle | `src/life_kernel/graph.py:519-524` | Add an dedicated `action_taken_this_cycle` flag set by `act_node`, or document the trade-off. |
| AUTO-09 | info | Tests verify real wiring but do not exercise full brain path | `tests/life_kernel/test_continuation_integration.py` | Add a test with a mocked `HermesBrain` for decide/act/idle enrichment. |

## 3. Hard-Rejection Check Results (plan §10)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Docs-only (no real code change) | **PASS** | `state.py`, `journal.py`, `p16_adapter.py`, `p18_adapter.py`, `graph.py`, `heartbeat.py`, `self_improve.py`, and `core/main.py` all changed. |
| 2 | Discord proof missing | **DEFERRED** | Wiring exists (`main.py:344-368`, `heartbeat.py:477-488`). No live proof in this commit. |
| 3 | Raw `LLMRouter.chat` as brain path | **PASS** | Brain path is `hermes_brain.think()` via `_safe_think` (`graph.py:104-130`). No `LLMRouter.chat` in the brain path. |
| 4 | Only health-check loops, no memory/daily-life | **PASS** | `observe_node` calls real P16/P18 recall (`graph.py:193-209`); `idle_node` is memory-driven (`graph.py:607-639`). |
| 5 | Sub-agent no output file | **PASS** | This report is the output file. |
| 6 | Tests/audits skipped to pass | **PASS** | `tests/life_kernel/` passes 420, skips 7; no failures. |
| 7 | Secrets in output | **PASS** | `DashboardRenderer._sanitize` redacts secrets; adapters log counts only. |
| 8 | PRODUCTION PASS without live proof | **PASS (not claimed)** | No PRODUCTION PASS claim in the commit. |
| 9 | `world_model_available = False` placeholder | **PASS** | Derived from real adapter state (`graph.py:238-239`). |
| 10 | `idle_node` still uses `random.choice` | **PASS** | No `random.choice`; deterministic fallback by `cycle_count % len(fallbacks)`. |
| 11 | Adapters still return `_placeholder:True` | **PASS** | Adapters return `_degraded: True` on failure; tests assert `_placeholder` is absent. |
| 12 | HARD STOP regression | **PASS** | `_heartbeat_1s` unchanged; live Redis flag source of truth, stale-checkpoint recovery preserved. |
| 13 | Other services disturbed | **N/A (not deployed)** | Code audit only; deploy canary is later wave. |

## 4. What Was Verified GOOD

1. **Memory-driven idle is real**: `idle_node` uses `recalled_memories` and `recalled_concepts` to choose a self-directed task, falls back deterministically when no recall is available, and seeds a real goal in `state.goals` (`graph.py:607-681`).
2. **Goals persist across cycles**: `state.goals` has no reducer in LangGraph, so the node returns the full merged list and the seeded goal survives to the next heartbeat invocation.
3. **Brain prompts include recall context**: `_make_brain_decide`, `_make_brain_act`, and `_make_brain_idle` all embed `recalled_concepts` and `recalled_memories` in their prompts (`graph.py:737-824`).
4. **Journal writes after meaningful cycles**: `reflect_node` writes a journal entry when `last_autonomous_decision`, `next_planned_action`, `recalled_memories`, or `recalled_concepts` indicate a meaningful cycle (`graph.py:519-546`).
5. **ImprovementTracker.propose only stores; RegressionGate.promote is separate**: `ImprovementTracker.propose` sets status to `proposed` and stores the candidate (`self_improve.py:372-374`). `RegressionGate.promote` runs tests before setting status to `promoted` (`self_improve.py:335-349`). AC-LIFE-009 is structurally satisfied, though the candidates themselves are hardcoded.
6. **Fail-soft everywhere**: Adapter failures degrade to `_degraded`; DB/engine failures in `main.py` leave the kernel headless but running; brain timeouts fall back to static logic.
7. **Tests assert the autonomy-depth contract**: `test_continuation_integration.py` verifies idle goal creation, memory-driven idle observations, journal writes, and adapter injection.

## 5. Verdict

**PASS_WITH_NOTES.** The P20 Living Autonomy Kernel continuation satisfies every hard-rejection criterion in code. The kernel is genuinely memory-driven, no longer random, and journals after meaningful cycles. However, the self-improvement loop is not yet autonomous (AUTO-01, AUTO-05, AUTO-06), and there are subtle goal-drift and cycle-continuity risks (AUTO-02, AUTO-03, AUTO-04) that should be fixed before claiming the system is "genuinely living." Live Discord proof and a deploy canary remain required before a final PRODUCTION PASS.

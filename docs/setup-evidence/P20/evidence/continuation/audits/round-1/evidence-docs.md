# P20 Continuation — Evidence / Docs Round-1 Audit

| Field | Value |
|---|---|
| Auditor | evidence/docs auditor (sub-agent) |
| Date | 2026-06-24 |
| Scope | `docs/setup-evidence/P20/evidence/continuation/` research reports, continuation plan, and doc claims |
| Test command run | `python -m pytest tests/life_kernel/ -q --disable-warnings --tb=no -p no:logging` |
| Test result | **420 passed, 7 skipped, 0 failed** |
| Verdict | **PASS_WITH_NOTES** |

---

## 1. Verdict

**PASS_WITH_NOTES**.

The P20 continuation evidence package is substantive and internally consistent. The seven required research reports are non-empty and cite real file:line evidence. The continuation plan contains every required structural section (gap matrix, todo list, dependency map, parallelism map, files, deployment, rollback, verification scaffold, auditor matrix, hard-rejection criteria). No document falsely claims `P20 PRODUCTION PASS`; all statuses remain at `PASS HOLD` / `SOAK IN PROGRESS`. No literal secrets were found in the research reports. The test suite reports **420 passed, 7 skipped**, which is higher than the plan's documented baseline of 397 — the docs need a test-count update.

One real code bug was found during this audit: `_heartbeat_1h` instantiates `ReflectionEvaluator()` with no arguments, but `ReflectionEvaluator.__init__` requires `graph` and `graph_config` positional arguments. This will raise `TypeError` at runtime when the hourly reflection loop executes. This is a continuation-scope regression for AC-LIFE-009 and should be fixed before the next deploy wave.

---

## 2. Executive Summary

The evidence/docs dimension of the P20 continuation is in good shape. The research wave produced detailed, file-backed reports covering architecture, memory/KG integration, Discord-visible autonomy, daily-life domain minds, deploy/runtime safety, plan-vs-code gaps, and evidence consistency. The continuation plan is a complete implementation roadmap with clear hard-rejection gates.

The documentation is honest about status: it repeatedly states the kernel is **not** at `PRODUCTION PASS` and that a 24-hour clean soak is still pending. No forbidden patterns (`random.choice`, `world_model_available = False`, raw `LLMRouter.chat`, `_placeholder:True`) remain in the committed `src/life_kernel/` code path. The test suite passes at 420/7/0.

However, the plan's documented test count (397 passed) is now stale. More importantly, the `_heartbeat_1h` reflection wiring contains a clear runtime defect that will crash the hourly self-improvement loop. This is an evidence-audit finding because it is visible in the committed source and contradicts the plan's claim that `_heartbeat_1h` runs `ReflectionEvaluator`.

---

## 3. Findings Table

| ID | Severity | Title | Detail | File:line |
|---|---|---|---|---|
| DOC-01 | medium | Documented test count is stale | `p20-continuation-plan.md` and research reports cite the pre-continuation baseline `397 passed, 7 skipped`. The actual current suite reports `420 passed, 7 skipped, 0 failed`. | `docs/setup-evidence/P20/evidence/continuation/p20-continuation-plan.md:12,46` |
| DOC-02 | medium | `ReflectionEvaluator` called with wrong arity in `_heartbeat_1h` | `evaluator = ReflectionEvaluator()` has no required `graph`/`graph_config` arguments; `__init__` signature is `(graph, graph_config, hermes_brain=None)`. This will raise `TypeError` at runtime and breaks AC-LIFE-009 wiring. | `src/life_kernel/heartbeat.py:594` |
| DOC-03 | low | `candidate_type` attribute does not exist on `ImprovementCandidate` | `_heartbeat_1h` logs `getattr(c, "candidate_type", "?")`, but the dataclass field is named `category`. Logs will always show `"?"`. | `src/life_kernel/heartbeat.py:602,611` |
| DOC-04 | low | Research directory contains 12 files, not 7 | The continuation plan references 7 research reports, but the `research/` directory contains 12 files (5 additional audit reports). This is harmless but should be reconciled in the plan. | `docs/setup-evidence/P20/evidence/continuation/research/` |

---

## 4. Hard-Rejection Check

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Docs-only (no real code change) | PASS | Real code changes in `src/life_kernel/graph.py`, `p16_adapter.py`, `p18_adapter.py`, `state.py`, `journal.py`, `heartbeat.py`, `src/core/main.py`. |
| 2 | Missing Discord proof | DEFERRED | No live Discord proof is claimed in this round; plan explicitly defers live proof to T15. |
| 3 | Raw `LLMRouter.chat` as brain path | PASS | Brain path is `hermes_brain.think()` via `_safe_think`; only comment references `LLMRouter.chat` to reject it (`graph.py:874`). |
| 4 | Only health-check loops, no memory context | PASS | `observe_node` calls real P16/P18 recall; `idle_node` is recall-driven; prompts include recalled context. |
| 5 | Sub-agent has no output file | PASS | This report is the output file at the assigned path. |
| 6 | Tests/audits skipped to pass | PASS | Full suite: 420 passed, 7 skipped, 0 failed. |
| 7 | Secrets in output/evidence | PASS | No literal secrets, tokens, or credentials found in research reports. |
| 8 | PRODUCTION PASS without live proof | PASS | No document claims `P20 PRODUCTION PASS`; all statuses are `PASS HOLD` / `SOAK IN PROGRESS`. |
| 9 | `world_model_available = False` placeholder | PASS | `graph.py:242` derives `world_model_available` from real adapter status. |
| 10 | `idle_node` still uses `random.choice` | PASS | `idle_node` uses deterministic fallback by `cycle_count % 3`; `random.choice` only appears in comments. |
| 11 | Adapters still return `_placeholder:True` | PASS | `p16_adapter.py` and `p18_adapter.py` return real recall results or `_degraded`; no `_placeholder` key. |
| 12 | HARD STOP regression | PASS | Non-LLM HARD STOP path unchanged; `_heartbeat_1s` Redis check and recovery remain. |
| 13 | Other services disturbed | DEFERRED | Deploy wave not yet executed; `main.py` only restarts core. |

---

## 5. What's GOOD

1. **Research reports are substantive.** The seven required reports total over 3,100 lines and cite real file:line evidence. They are not boilerplate or empty.
2. **Continuation plan is complete.** All required sections are present: gap matrix, exact todo list, dependency map, parallelism map, files to modify, deployment plan, rollback plan, verification scaffold, auditor matrix, hard-rejection criteria, final allowed statuses, and research sources.
3. **Status is honest.** No document over-claims `PRODUCTION PASS`. The plan and research consistently state `PASS HOLD` / `SOAK IN PROGRESS`.
4. **No secrets in research output.** Grep for secret-like patterns returned only generic references to environment variables and redaction logic; no literal credentials.
5. **Test suite is green.** 420 passed, 7 skipped, 0 failed, confirming the continuation code does not break existing functionality.
6. **Hard-rejection code fixes hold.** `random.choice`, `world_model_available = False`, and `_placeholder:True` are absent from the committed `src/life_kernel/` code.
7. **Real P16/P18 wiring is present.** `main.py` builds per-call async recall callables, injects adapters into `create_life_mind_graph`, and disposes the engine on shutdown.
8. **Journal and self-improvement scaffolding is real.** `JournalWriter` wraps `PostgresAuditJournal`; `reflect_node` writes entries; `_heartbeat_1h` invokes `ReflectionEvaluator` (but with the wrong signature — see finding DOC-02).

---

## 6. Recommendations

1. **Fix `ReflectionEvaluator` instantiation in `_heartbeat_1h`** — pass the compiled graph and a config dict (e.g., `{"thread_id": "heartbeat"}`). Until this is fixed, the hourly reflection loop will crash on the first run.
2. **Update documented test count** from `397 passed` to `420 passed` in the continuation plan and any other evidence docs that repeat the stale number.
3. **Reconcile research file count** in the plan: either list all 12 files or clarify that 7 are primary research and 5 are derived audit reports.
4. **Add a unit test** that exercises `_heartbeat_1h` with a real graph to prevent the arity bug from regressing.

---

## 7. Conclusion

The evidence/docs dimension passes with notes. The research is thorough, the plan is complete, and the documentation is honest about status. The only material issue is the `_heartbeat_1h` `ReflectionEvaluator()` runtime defect, which is a code bug but is visible to this evidence/docs audit because it contradicts the plan's self-improvement wiring claims. Fixing it is required before the next deploy wave can claim AC-LIFE-009 is wired and before a final `P20 PRODUCTION PASS` can be considered.

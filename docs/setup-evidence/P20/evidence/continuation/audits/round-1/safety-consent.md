# Safety / Consent Audit — P20 Living Autonomy Kernel Continuation (Round 1)

| Field | Value |
|---|---|
| Auditor | Safety/consent auditor (adversarial) |
| Date | 2026-06-24 |
| Scope | Cumulative diff `HEAD~2..HEAD` on `src/life_kernel/` and `src/core/main.py` for the P20 continuation |
| Verdict | **PASS_WITH_NOTES** |
| Hard rejection triggered | No |

---

## 1. Verdict

**PASS_WITH_NOTES.**

The continuation satisfies every hard-rejection criterion in `p20-continuation-plan.md` §10 that can be verified from code and local tests. The safety architecture is sound: HARD STOP remains a non-LLM first check in `decide_node` and the heartbeat `_heartbeat_1s` path, the brain path uses `HermesBrain.think` (not raw `LLMRouter.chat`), idle is memory-driven without `random.choice`, adapters return real recall data rather than `_placeholder:True`, `world_model_available = False` is gone, and the act path is display-only (no `send`/`transfer`/`deploy` side effects). Tests pass (`420 passed, 7 skipped, 0 failed`).

Two notes remain: (1) `safe_mode=False` in `src/core/main.py:267` means raw `Critical`-classified memory content can reach the brain prompt and downstream dashboard fields — this is consistent with principal `guinevere_core` having `CRITICAL` clearance, but it should be an explicit operator decision and tracked; (2) `_heartbeat_1h` instantiates `ReflectionEvaluator()` with no arguments, but the class requires `(graph, graph_config, hermes_brain=None)` — the current code happens to pass tests because the test state mocks short-circuit before construction, but the instantiation is technically broken. This is a real bug.

---

## 2. Executive Summary

The P20 continuation wires real P16 KG recall (`KGQueryEngine.search_entities`) and P18 episodic recall (`recall_memories`) into the life-mind graph. `observe_node` populates `recalled_concepts`, `recalled_memories`, `world_model_status`, and a sanitized `memory_status`. `idle_node` now seeds a real self-directed goal from recalled context, and the brain prompts in `decide`/`act`/`idle` include recall context. `reflect_node` writes journal entries via `JournalWriter`/`PostgresAuditJournal`. The heartbeat runs `_heartbeat_1h` reflection and a narrative lifecycle log.

From a safety/consent perspective the implementation is largely correct. The most important checks — non-LLM HARD STOP, no raw LLM router as brain, display-only act path, and no raw memory echo in Discord-visible fields — all hold. The audit identifies one medium-severity bug (`ReflectionEvaluator` constructor mismatch), one low-severity consent decision (`safe_mode=False`), and several minor documentation/test notes.

---

## 3. Findings Table

| ID | Severity | Title | File:Line | Detail | Recommendation |
|---|---|---|---|---|---|
| SAF-01 | medium | `_heartbeat_1h` calls `ReflectionEvaluator()` with wrong constructor signature | `src/life_kernel/heartbeat.py:594` | `ReflectionEvaluator.__init__` requires `(graph, graph_config, hermes_brain=None)` (confirmed at runtime), but `_heartbeat_1h` calls `ReflectionEvaluator()` with no args. The existing test (`test_heartbeat_continuation.py`) passes only because `state` is mocked and the code path reaches the block, but in production the constructor will raise `TypeError`, the `except` block will swallow it, and self-improvement candidates will never be generated. | Fix the instantiation to pass the required graph/config, or update `ReflectionEvaluator` to have a no-arg default constructor. Add a unit test that asserts `candidates` are actually produced. |
| SAF-02 | low | Autonomous memory recall runs with `safe_mode=False` | `src/core/main.py:267` | `_life_recall_fn` passes `safe_mode=False` to `recall_memories`. With principal `guinevere_core` the classification ceiling is `CRITICAL`, so raw `Critical`-classified episode content is returned and embedded into the brain prompt (`graph.py:752-825`) and flows to `memory_status`. This is consistent with the principal's clearance, but means intimate/Critical memories can appear in the LLM prompt and (after dashboard sanitiser) in Discord-visible status. | Make `safe_mode` configurable via env var, default `True` for autonomous recall, so the operator opts in to raw Critical content rather than getting it by default. Document the decision either way. |
| SAF-03 | low | `journal.py` entry lacks `source` field expected by `PostgresAuditJournal.record` | `src/life_kernel/journal.py:47-55` | `JournalWriter.write_entry` builds an entry dict without a `source` key. `PostgresAuditJournal.record` falls back to `source = str(entry.get("source", "unknown"))`, so it stores `"unknown"`. The entry is still written, but filtering/auditing by source will be useless. | Add `"source": "life_kernel_journal"` to the journal entry dict. |
| SAF-04 | info | `_IDLE_SYSTEM_PROMPT` instructs display-only behavior but no runtime enforcement | `src/life_kernel/graph.py:82-89` | The prompt tells the brain "Keep it display-only — never propose real side-effects." There is no tool/API registration that would let the LLM execute side effects anyway, so the instruction is sufficient but unverified by a tool-use policy. | Consider adding an explicit `tools=None` or tool-use allowlist in `HermesBrain.think` for the autonomy path. |
| SAF-05 | info | `HardStopHandler` wiring is conditional on `set_hard_stop_handler` existing | `src/core/main.py:91-96` | The handler is wired only if `loop_manager.guardian` has the setter; otherwise it logs a warning and continues. This is fail-soft, but the operator may not notice that HARD STOP from other guardian paths is un-wired. | Log at warning level and surface in `/health/detailed` when the expected setter is missing so the gap is observable. |
| SAF-06 | info | `memory_status` uses counts + top concept name only | `src/life_kernel/graph.py:223-232` | The fix correctly avoids echoing raw memory content in Discord-visible status, satisfying MEM-06. Only `world_model_status`, counts, and the top KG concept name are exposed. | No action; keep as-is. |
| SAF-07 | info | `brain_idle` updates seeded goal to brain proposal | `src/life_kernel/graph.py:839-854` | The LLM-generated proposal replaces the static memory-driven goal description. Because the act path is display-only and no tools are invoked, this is acceptable. | No action. |

---

## 4. Hard-Rejection Check

| Criterion | Status | Evidence |
|---|---|---|
| Docs-only implementation | PASS | Real code changes in `graph.py`, `p16_adapter.py`, `p18_adapter.py`, `journal.py`, `state.py`, `heartbeat.py`, `self_improve.py`, `core/main.py`. |
| Missing Discord proof | NOT VERIFIED | No live Discord screenshot/dashboard in the diff; required before final PRODUCTION PASS. |
| Raw `LLMRouter.chat` as brain path | PASS | `graph.py` uses `hermes_brain.think()` via `_safe_think`; no `LLMRouter.chat` in the life_kernel path. |
| Only health-check loops, no memory context | PASS | `observe_node` calls real adapters and feeds recalled context into decide/act/idle prompts. |
| Sub-agent no output file | N/A | This audit produces the output file at the required path. |
| Tests skipped to pass | PASS | `420 passed, 7 skipped, 0 failed`; skipped tests are pre-existing environment-dependent markers. |
| Secrets in output/evidence | PASS | No secrets observed; dashboard sanitiser redacts keys/tokens. |
| PRODUCTION PASS without live proof | N/A | Verdict is `PASS_WITH_NOTES`; live proof still required for `P20 PRODUCTION PASS`. |
| `world_model_available = False` placeholder | PASS | Removed; `world_model_available` is now derived from adapter status (`graph.py:242`). |
| `idle_node` still uses `random.choice` | PASS | `random` is not imported; idle uses deterministic fallback by `cycle_count % len(fallbacks)` (`graph.py:638`). |
| Adapters still return `_placeholder:True` | PASS | Adapters return real concepts/memories or `_degraded`; no `_placeholder` key. |
| HARD STOP regression | PASS | `decide_node` checks `hard_stop_requested` first before any LLM call; `_heartbeat_1s` checks Redis flag every second and can recover stale state. |
| Other services disturbed | NOT VERIFIED | Local tests pass; deploy-undisturbed check requires live VPS verification. |

---

## 5. What's GOOD

- **Safety ordering is preserved**: `decide_node` checks `hard_stop_requested` at `graph.py:314` before the priority engine and well before any LLM involvement. `_make_brain_decide` runs the static engine first and only consults the brain when the static decision is `idle` (`graph.py:736-740`).
- **HARD STOP recovery is live**: `_heartbeat_1s` reads the Redis flag every second, clears stale `hard_stop_requested=True` checkpoint state when the flag is absent, and stops the service on live HARD STOP (`heartbeat.py:254-324`).
- **Recall respects DNR and principal**: `p18_adapter.recall` calls `recall_memories` with `principal="guinevere_core"`, `exclude_dnr=True` (`p18_adapter.py:80-83`), and the main recall wrapper passes the same values (`main.py:259-266`).
- **No side-effect execution in act path**: `act_node` only logs/plans; `brain_act` stores a proposal in `next_planned_action`. A `grep` for `send`/`transfer`/`deploy` in the act/brain path returns nothing.
- **Memory status no longer echoes raw content**: `memory_status` is built from counts and the top KG concept name only (`graph.py:223-232`), satisfying MEM-06.
- **Display-only v1 is enforced by architecture**: No tools are registered to the LLM; the worst an LLM output can do is populate state fields that the dashboard renders.
- **Journal writes are fail-soft**: `reflect_node` catches all journal exceptions and logs a warning without crashing the kernel (`graph.py:545-546`).
- **Test suite is green**: `420 passed, 7 skipped, 0 failed` for `tests/life_kernel/`. No tests are skipped to pass the audit.

---

## 6. Consent / Surveillance Notes

- **No consent/surveillance change**: The continuation does not introduce new sensor collection, surveillance hooks, or data-sharing paths beyond what already existed.
- **Journal content**: `JournalWriter.write_entry` stores `reasoning`, `lessons_learned`, `focus`, `cycle`, and `phase`. It does not include raw recalled memory content (`journal.py:46-56`). The `PostgresAuditJournal` table stores JSONB under `life_kernel.audit_journal`, a schema already used by domain minds.
- **DNR bypass risk**: `exclude_dnr=True` is passed explicitly, so DNR records are excluded. The only concern is `safe_mode=False`, which is a content-redaction choice rather than a consent bypass. Operator awareness is recommended.

---

## 7. Required Before PRODUCTION PASS

1. Fix `SAF-01` (`ReflectionEvaluator` constructor mismatch).
2. Resolve `SAF-02` (decide `safe_mode=True` default or document operator opt-in to raw Critical content).
3. Add `source` field to journal entries (`SAF-03`).
4. Provide live Discord proof showing memory-driven dashboard/log and that other guinevere-* services remain active.

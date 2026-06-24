# P20 Continuation — Evidence / Docs Round-2 Audit

| Field | Value |
|---|---|
| Auditor | evidence/docs auditor (sub-agent, round 2) |
| Date | 2026-06-24 |
| Scope | Round-1 audit fixes (HEAD~1 MEM-01..08 + HEAD RUN-01/AUTO-06/DUX-01/SAF-02); evidence package completeness; test count honesty |
| Test command run | `python -m pytest tests/life_kernel/ -q --disable-warnings --tb=no -p no:logging` |
| Test result | **420 passed, 7 skipped, 0 failed** |
| Verdict | **PASS** |

---

## 1. Verdict

**PASS**.

All wave-1 findings from the round-1 audits have been correctly fixed and verified in code. The test suite reports **420 passed, 7 skipped, 0 failed**. No document falsely claims `P20 PRODUCTION PASS`. No literal secrets appear in the round-1 audit reports. The round-1 audit package is complete and substantive (7 files). The only remaining documentation issue is that the continuation plan and several other P20 evidence documents still cite stale test counts (`397` or `390` passed instead of the current `420`), but this was already flagged in round 1 and does not block the wave-1 fix verification.

---

## 2. Executive Summary

This round-2 evidence/docs audit verifies that the fixes committed in response to the round-1 audit wave actually hold, and that no new regressions were introduced by those fixes.

- **Round-1 reports exist and are substantive**: 7 markdown reports in `docs/setup-evidence/P20/evidence/continuation/audits/round-1/`, totaling over 50 KB, with detailed findings tables, file:line citations, and hard-rejection checks.
- **Wave-1 fixes are verified in source**:
  - `ReflectionEvaluator` is now constructed with `graph`, `graph_config`, and `hermes_brain` (`src/life_kernel/heartbeat.py:608-612`) — fixes RUN-01/DOC-02/SAF-01.
  - Candidate logging uses `.category` (`heartbeat.py:623-625`) — fixes AUTO-06.
  - Lifecycle log line is truncated to ≤1900 characters (`heartbeat.py:523-528`) — fixes DUX-01.
  - Autonomous recall defaults to `safe_mode=True` unless `LIFE_KERNEL_RAW_RECALL=1` is set (`src/core/main.py:265-275`) — fixes SAF-02.
  - `p16_adapter` object-branch reads `display_name` (`src/life_kernel/p16_adapter.py:86-91`) — fixes MEM-01.
  - `journal.py` uses `datetime.now(timezone.utc)` (`src/life_kernel/journal.py:55`) — fixes MEM-02.
  - `reflect_node` journal gate no longer uses stale `act_count` (`src/life_kernel/graph.py:510-524`) — fixes MEM-03.
  - `PostgresAuditJournal` private engine is disposed on shutdown (`src/core/main.py:456-467`) — fixes MEM-04.
  - Adapter docstrings updated to describe real-recall contract (`src/life_kernel/p16_adapter.py:1-61`, `src/life_kernel/p18_adapter.py:1-64`) — fixes MEM-05.
  - `memory_status` no longer echoes raw memory content (`src/life_kernel/graph.py:223-232`) — fixes MEM-06.

No new hard-rejection criteria were introduced by the fixes. The only persistent documentation finding is the stale test count (`397` and `390` in older docs), which is a documentation hygiene issue rather than a code defect.

---

## 3. Wave-1 Fix Verification

| Finding | Status | Evidence in current HEAD |
|---|---|---|
| **RUN-01 / DOC-02 / SAF-01**: `_heartbeat_1h` `ReflectionEvaluator()` no-arg TypeError | **FIXED** | `src/life_kernel/heartbeat.py:608-612` passes `graph=self.graph`, `graph_config={...}`, `hermes_brain=self._hermes_brain`. |
| **AUTO-06**: `candidate_type` attribute missing, logged `?` | **FIXED** | `src/life_kernel/heartbeat.py:623-625` uses `getattr(c, "category", "?")`. |
| **DUX-01**: lifecycle log line could exceed Discord 2000-char limit | **FIXED** | `src/life_kernel/heartbeat.py:523-528` caps line at 1900 chars before writing. |
| **SAF-02**: autonomous recall used `safe_mode=False` by default | **FIXED** | `src/core/main.py:265-275` reads `LIFE_KERNEL_RAW_RECALL`; defaults to `safe_mode=True`. |
| **MEM-01**: `p16_adapter` object-branch read `name` instead of `display_name` | **FIXED** | `src/life_kernel/p16_adapter.py:86-91` now reads `display_name`, falls back to `name`, then `entity_id`. |
| **MEM-02**: `datetime.utcnow()` deprecation warning | **FIXED** | `src/life_kernel/journal.py:55` uses `datetime.now(timezone.utc).isoformat()`. |
| **MEM-03**: `reflect_node` journal gate used stale `act_count` | **FIXED** | `src/life_kernel/graph.py:510-524` drops `act_count` from the meaningful gate and uses `last_decision`, `next_action`, `recalled_memories`, `recalled_concepts`. |
| **MEM-04**: `PostgresAuditJournal` private engine not disposed on shutdown | **FIXED** | `src/core/main.py:456-467` disposes `_audit_journal._engine` during lifespan teardown. |
| **MEM-05**: adapter docstrings still claimed stub/placeholder behavior | **FIXED** | `src/life_kernel/p16_adapter.py:1-61` and `src/life_kernel/p18_adapter.py:1-64` now describe the real-recall contract. |
| **MEM-06**: `memory_status` echoed raw memory content | **FIXED** | `src/life_kernel/graph.py:223-232` now surfaces only counts + top KG concept name. |

---

## 4. NEW Findings Table (Regressions / Issues Introduced by Fixes)

| ID | Severity | Title | File:Line | Detail | Recommendation |
|---|---|---|---|---|---|
| EVD-01 | medium | Stale test count still present in continuation plan and older evidence docs | `docs/setup-evidence/P20/evidence/continuation/p20-continuation-plan.md:12,45,52,163,178,211`; `docs/setup-evidence/P20/evidence/continuation/research/evidence-consistency.md:13,73,76,120,136,152,179`; multiple `evidence/LK-017/`, `evidence/production-*` files | Round-1 audit (DOC-01) already flagged that docs cite `397 passed` (or even `390 passed`) while the actual suite now reports `420 passed, 7 skipped, 0 failed`. The wave-1 fixes did not update these numbers. This is non-blocking but undermines audit credibility. | Update the continuation plan baseline to `420 passed, 7 skipped, 0 failed` and reconcile all listed older evidence documents in Phase 9. |

**No other new issues were identified.** The fixes are surgical and do not introduce regressions in the hard-rejection criteria.

---

## 5. Hard-Rejection Check (Plan §10)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Docs-only implementation | **PASS** | Real code changes verified in `heartbeat.py`, `main.py`, `p16_adapter.py`, `p18_adapter.py`, `journal.py`, `graph.py`. |
| 2 | Missing Discord proof | **DEFERRED** | No live Discord proof claimed in this code-audit round; required for final `P20 PRODUCTION PASS`. |
| 3 | Raw `LLMRouter.chat` as brain path | **PASS** | Brain path remains `HermesBrain.think()` via `_safe_think` (`graph.py:104-130`). |
| 4 | Only health-check loops, no memory context | **PASS** | `observe_node` calls real P16/P18 recall (`graph.py:193-209`); `idle_node` is memory-driven (`graph.py:607-681`). |
| 5 | Sub-agent no output file | **PASS** | This report is written to the assigned path. |
| 6 | Tests/audits skipped to pass | **PASS** | `420 passed, 7 skipped, 0 failed`; no failures hidden. |
| 7 | Secrets in output/evidence | **PASS** | No literal secrets in round-1 audit reports; only env-var references and redaction-pattern descriptions. |
| 8 | PRODUCTION PASS without live proof | **PASS** | No document claims `P20 PRODUCTION PASS`; statuses remain `PASS HOLD` / `SOAK IN PROGRESS`. |
| 9 | `world_model_available = False` placeholder | **PASS** | Derived from adapter status (`graph.py:242`). |
| 10 | `idle_node` still uses `random.choice` | **PASS** | Deterministic fallback (`graph.py:633-638`). |
| 11 | Adapters still return `_placeholder:True` | **PASS** | Real recall or `_degraded`; no `_placeholder` key. |
| 12 | HARD STOP regression | **PASS** | Non-LLM HARD STOP preserved (`graph.py:314-316`, `heartbeat.py:254-358`). |
| 13 | Other services disturbed | **N/A** | Deploy canary is a later wave; not in scope for this evidence/docs audit. |

**Hard-rejection verdict:** NONE TRIGGERED.

---

## 6. What's GOOD

1. **Wave-1 fixes are real and verified in source.** Each round-1 finding maps to a concrete, cited code change.
2. **Test suite remains green.** `420 passed, 7 skipped, 0 failed` confirms no regressions.
3. **Status honesty is preserved.** No document over-claims `P20 PRODUCTION PASS`.
4. **No secrets in audit evidence.** Round-1 reports contain only env-var references and sanitized pattern descriptions.
5. **Round-1 audit package is substantive.** 7 detailed reports with file:line citations, hard-rejection checks, and recommendations.
6. **ReflectionEvaluator is no longer a no-arg crash.** The 1h self-improvement heartbeat is now structurally correct.
7. **Safe-by-default autonomous recall.** `safe_mode=True` unless the operator explicitly opts in via `LIFE_KERNEL_RAW_RECALL=1`.
8. **Discord log length safety.** Lifecycle log line is capped well below Discord's 2000-character limit.

---

## 7. Recommendations

1. **Update stale test counts** in `p20-continuation-plan.md` and the older evidence documents from `397` / `390` to `420 passed, 7 skipped, 0 failed` during Phase 9 finalization.
2. **Maintain the round-2 audit package.** As other round-2 specialist reports are written, ensure they also land in `docs/setup-evidence/P20/evidence/continuation/audits/round-2/`.
3. **Before final `P20 PRODUCTION PASS`:** complete the deploy wave, provide live Discord proof, and confirm the 24-hour clean soak.

---

## 8. Conclusion

The wave-1 fixes hold. The evidence/docs dimension passes round-2 audit with a single documentation-hygiene note (EVD-01). No new hard-rejection criteria were introduced, the test suite is green, and no production-pass overclaims exist.

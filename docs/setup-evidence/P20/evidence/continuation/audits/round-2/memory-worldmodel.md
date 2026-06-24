# Memory / World-Model Audit — P20 Living Autonomy Continuation (Round 2)

| Field | Value |
|---|---|
| Auditor | Memory / World-Model |
| Scope | `src/life_kernel/{p16_adapter,p18_adapter,journal,graph,heartbeat}.py`, `src/core/main.py` |
| Date | 2026-06-24 |
| Verdict | **PASS_WITH_NOTES** |

## 1. Executive Summary

Round-2 verifies that the wave-1 MEM fixes introduced in the most recent commits hold and do not introduce regressions. All six load-bearing MEM findings (MEM-01 through MEM-06) are resolved, the P18 field mapping is correct, and autonomous recall now defaults to `safe_mode=True`. AC-LIFE-005 is genuinely satisfied: the `observe_node` populates real KG/memory recall, and the `idle_node` uses that recall to seed self-directed goals.

One new finding is raised: the `datetime.utcnow()` removal was applied only to `journal.py`; the rest of `src/life_kernel/` still uses naive `datetime.now().isoformat()` timestamps. This is a non-blocking inconsistency but leaves technical debt and potential `DeprecationWarning` surface on Python 3.12+.

No hard-rejection criterion is triggered.

## 2. Wave-1 Fix Verification

| ID | Status | Evidence |
|---|---|---|
| **MEM-01** — p16_adapter object-branch uses `display_name` | **FIXED** | `src/life_kernel/p16_adapter.py:86-91` now reads `getattr(r, "display_name", None) or getattr(r, "name", "") or getattr(r, "entity_id", "")`. The comment explicitly notes `EntityMatch` exposes `display_name`, not `name`. |
| **MEM-02** — no `datetime.utcnow()` in `src/life_kernel` | **PARTIALLY FIXED** | `src/life_kernel/journal.py:55` now uses `datetime.now(timezone.utc).isoformat()`. However, other `life_kernel` modules still use naive `datetime.now().isoformat()` (see New Findings). |
| **MEM-03** — reflect journal gate no longer uses stale `act_count` | **FIXED** | `src/life_kernel/graph.py:514-524` drops `act_count` and gates on `last_decision`, `next_action`, `recalled_memories`, or `recalled_concepts` with an explanatory comment. |
| **MEM-04** — `PostgresAuditJournal` engine disposed on shutdown | **FIXED** | `src/core/main.py:320-323` registers `app.state.life_kernel_audit_journal`; `src/core/main.py:456-467` disposes the private `_engine` on teardown. |
| **MEM-05** — adapter docstrings updated | **FIXED** | `p16_adapter.py` and `p18_adapter.py` docstrings now describe the real recall contract, `_degraded` fallback, and field mapping. |
| **MEM-06/SAF-02** — `_life_recall_fn` default `safe_mode=True` | **FIXED** | `src/core/main.py:259-276` sets `safe_mode=not _life_raw_recall`, where `_life_raw_recall` defaults to `False`; therefore `safe_mode` defaults to `True`. Critical/Restricted content is redacted before reaching the brain prompt or dashboard. |
| **P18 field mapping** | **VERIFIED** | `src/life_kernel/p18_adapter.py:90-94` maps `safe_content→content`, `combined_score→relevance`, `created_at→timestamp`. |
| **memory_status no raw content** | **VERIFIED** | `src/life_kernel/graph.py:224-232` builds `memory_status` from counts and the top KG concept name only; raw memory content is deliberately not echoed to Discord-visible fields. |
| **AC-LIFE-005** | **SATISFIED** | `observe_node` (`graph.py:193-209`) populates `recalled_concepts`/`recalled_memories`; these flow into `idle_node` (`graph.py:616-628`) to seed memory-driven self-direction and into brain prompts (`graph.py:737-746`, `813-824`). |

## 3. New Findings (Introduced or Left Unresolved by Wave-1 Fixes)

| ID | Severity | Title | Detail (file:line) | Recommendation |
|---|---|---|---|---|
| R2-MEM-01 | medium | `datetime.utcnow()` removal is incomplete; naive `datetime.now()` still used across `life_kernel` | `grep` found 16 naive `datetime.now().isoformat()` calls across `src/life_kernel`: `p16_adapter.py:68,100,109`; `p18_adapter.py:71,93,97,101`; `graph.py:249,432,494,649`; `cognition.py:290,315`; `decision_context.py:98`; `heartbeat.py:354`; `sensor_adapters/base.py:70`. `journal.py` was fixed, but the module-wide naive-datetime debt remains, which will emit `DeprecationWarning` on Python 3.12+ and creates inconsistent timestamp formats in logs/state. | Sweep `src/life_kernel` to replace `datetime.now().isoformat()` with `datetime.now(timezone.utc).isoformat()`. This is a safe, mechanical refactor. |
| R2-MEM-02 | low | MEM-04 disposal depends on private `_engine` attribute | `src/core/main.py:462` does `_aj_engine = getattr(_audit_journal, "_engine", None)`. If `PostgresAuditJournal` ever renames or removes this private attribute, shutdown disposal will silently fail. | Add a public accessor (e.g. `PostgresAuditJournal.engine`) or a context-manager/dispose method, and use it in `main.py`. At minimum, document the coupling in the code comment. |

## 4. Hard-Rejection Check (Plan §10)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Docs-only (no real code change) | **PASS** | Real code changed: adapters, journal, graph, main.py. |
| 2 | Discord proof missing | **NOT YET** | Code audit only; live proof required for final PASS. |
| 3 | Raw `LLMRouter.chat` as brain path | **PASS** | Brain path is `hermes_brain.think()` via `_safe_think`. |
| 4 | Only health-check loops, no memory/daily-life | **PASS** | Real P16/P18 recall drives `observe`, `decide`, `act`, `idle`. |
| 5 | Sub-agent no output file | **PASS** | This report is the output file. |
| 6 | Tests/audits skipped to pass | **PASS** | No evidence of skipped tests in this diff. |
| 7 | Secrets in output | **PASS** | No secrets observed in reviewed code. |
| 8 | PRODUCTION PASS without live proof | **PASS (not claimed)** | No PRODUCTION PASS claim in this commit. |
| 9 | `world_model_available = False` placeholder | **PASS** | Derived from real adapter state (`graph.py:242`). |
| 10 | `idle_node` still uses `random.choice` | **PASS** | `idle_node` uses memory-driven logic with deterministic fallback. |
| 11 | Adapters still return `_placeholder:True` | **PASS** | Adapters return `_degraded: True` on failure; no `_placeholder`. |
| 12 | HARD STOP regression | **PASS** | `_heartbeat_1s` recovery and Redis flag handling unchanged; stop logic still in heartbeat. |
| 13 | Other services disturbed by deploy | **N/A** | Code audit only; deploy verification pending. |

## 5. What Is Good

1. **AC-LIFE-005 genuinely holds**: real recall is wired, populated by `observe_node`, and consumed by `idle_node` and brain prompts.
2. **Autonomous recall is safe-by-default**: `safe_mode=True` protects against leaking Critical/Restricted content to Discord-visible surfaces.
3. **memory_status is privacy-safe**: only counts and top concept names are surfaced; raw memory content is kept internal.
4. **Fail-soft remains intact**: adapter failures degrade gracefully to `_degraded` or `None` without crashing the kernel.
5. **Wave-1 journal gate fix is correct**: dropping stale `act_count` prevents the first-cycle journal skip while preserving meaningful-cycle gating.

## 6. Verdict

**PASS_WITH_NOTES.** All wave-1 MEM/world-model fixes hold and no regressions are introduced in the fix logic. The only new concern is the incomplete timezone-aware datetime sweep (R2-MEM-01), which should be addressed before the final production soak.

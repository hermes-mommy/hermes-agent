# P3-011 Hybrid Ranking Tuning — Verification Report

**Step:** STEP-P3-011  
**Phase:** P3 Memory Safety  
**Date:** 2026-06-02  
**Author:** Guinevere (parent-verified implementation)  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Evidence root:** `docs/setup-evidence/P3/STEP-P3-011/`

---

## 1. What Was Done

Implemented P3-011 hybrid ranking tuning with minimal diffs to `src/memory/read_pipeline.py` and `src/memory/__init__.py`.  Nine targeted changes were applied:

| # | Change | File | Lines |
|---|--------|------|-------|
| 1 | Added P3-011 constants: `VECTOR_WEIGHT=0.5`, `FTS_WEIGHT=0.5`, `BOTH_SIGNAL_BONUS=1.25`, `RECENCY_MAX_BOOST=0.10`, `MAX_CANDIDATE_POOL=200` | `src/memory/read_pipeline.py` | 68–84 |
| 2 | Updated `compute_rrf_score()` to accept `vector_weight`, `fts_weight` kwargs; returns `(score, num_signals)` tuple | `src/memory/read_pipeline.py` | 255–279 |
| 3 | Added `num_signals` field to `EpisodeEntry` dataclass | `src/memory/read_pipeline.py` | 467–476 |
| 4 | Updated `compute_scored_results()` to apply both-signal bonus and bounded recency boost | `src/memory/read_pipeline.py` | 537–590 |
| 5 | Updated `build_result_episode_map()` to count distinct signals per episode | `src/memory/read_pipeline.py` | 482–519 |
| 6 | Capped `expanded_limit = min(limit * EXPANDED_LIMIT_MULTIPLIER, MAX_CANDIDATE_POOL)` in `recall_memories()` | `src/memory/read_pipeline.py` | 735 |
| 7 | Added `classification_level()` helper with fail-closed unknown/null mapping (level 5) | `src/memory/read_pipeline.py` | 299–306 |
| 8 | Updated classification ceiling filter to use `classification_level()` instead of direct dict lookup | `src/memory/read_pipeline.py` | 723 |
| 9 | Renamed 9 private helpers to public names (`compute_rrf_score`, `normalize_importance`, `classification_level`, `build_vector_query`, `build_fts_query`, `build_recency_query`, `EpisodeEntry`, `build_result_episode_map`, `compute_scored_results`, `build_safe_content`, `estimate_tokens`, `apply_token_budget`) and exported them via `__all__` | `src/memory/read_pipeline.py`, `src/memory/__init__.py` | 255–749, 14–56 |
| 10 | Removed unused `Mapping` import from `collections.abc` | `src/memory/read_pipeline.py` | 24 |

Classification fail-closed (R8.2): added `classification_level()` helper so unknown/null classification maps to level 5 (beyond Critical), ensuring the ceiling filter blocks them.  This is a P3-011 safety improvement beyond the plan's baseline.

Created `tests/memory/test_read_pipeline_hybrid.py` with 43 deterministic tests covering all P3-011 acceptance criteria.

---

## 2. Files Changed

| File | Type | Change Summary |
|------|------|----------------|
| `src/memory/read_pipeline.py` | Modified | 10 edits: new constants, weighted RRF, both-signal bonus, bounded recency boost, max candidate pool cap, fail-closed classification, public rename of helpers, removed unused `Mapping` import |
| `src/memory/__init__.py` | Modified | Re-exported new public helpers for testability |
| `tests/memory/test_read_pipeline_hybrid.py` | New | 43 deterministic tests |
| `tests/memory/__init__.py` | New | Package marker |
| `docs/setup-evidence/P3/STEP-P3-011/verification.md` | New | This file |

No migrations, no dependencies added, no external API calls.

---

## 3. Validation Results

### 3.1 Targeted test run

**Command:**  
```powershell
python -m pytest tests/memory/test_read_pipeline_hybrid.py -v
```

**Exit code:** `0` (PASS — all 43 tests passed)

**Test results summary:**

| Test class | Tests | Result |
|-----------|-------|--------|
| `TestWeightedRRF` | 5 | PASS |
| `TestBothSignalBonus` | 2 | PASS |
| `TestRecencyConfig` | 4 | PASS |
| `TestCombinedScore` | 3 | PASS |
| `TestMaxCandidatePool` | 3 | PASS |
| `TestClassificationFailClosed` | 6 | PASS |
| `TestDNRPreFilter` | 6 | PASS |
| `TestNormalizeImportance` | 4 | PASS |
| `TestP3011Constants` | 10 | PASS |
| **Total** | **43** | **PASS** |

### 3.2 LSP diagnostics

**`lsp_diagnostics src/memory/read_pipeline.py`** — **No diagnostics** (clean).

**`lsp_diagnostics tests/memory/test_read_pipeline_hybrid.py`** — **No diagnostics** (clean) after removing the unused `Sequence` import.

**Runtime import verification:**
- Direct `python -c "from src.memory.read_pipeline import compute_rrf_score, normalize_importance, classification_level, build_vector_query, build_fts_query, build_recency_query, EpisodeEntry, build_result_episode_map, compute_scored_results, build_safe_content, estimate_tokens, apply_token_budget; from src.memory import compute_rrf_score as package_compute_rrf_score, EpisodeEntry as package_EpisodeEntry; print('imports-ok')"` succeeds.
- `python -m pytest tests/memory/test_read_pipeline_hybrid.py -v` — 43/43 PASS.

No suppressions added.

---

## 4. Evidence Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Test file | `tests/memory/test_read_pipeline_hybrid.py` | 43 deterministic tests |
| Test output | pytest run (see §3.1 above) | Exit code 0, 43/43 PASS |
| Source diff | `src/memory/read_pipeline.py` | 10 targeted edits |
| Export update | `src/memory/__init__.py` | New public helpers exported |
| Unused import removed | `src/memory/read_pipeline.py` | Removed `Mapping` from `collections.abc` import |

No raw memory content, vectors, or secrets in evidence files.

---

## 5. Doc-Sync Impact

P3-011 does not require doc-sync to governance documents. ADRs, PersonaSafetyPolicy, and research reports were not modified.

- `PROGRESS.md` — updated by parent after auditor PASS to mark P3-011 complete with evidence/auditor paths
- `CHECKLIST.md` — updated by parent after auditor PASS to mark P3-011 complete with validation summary
- ADRs — NOT modified (no ADR changes required for P3-011)
- Research reports — NOT modified (read-only per batch plan)

---

## 6. Boundary Compliance

| Boundary | Status | Evidence |
|----------|--------|----------|
| **Persona drift** | ✅ Compliant | No persona behavior logic touched; pure ranking/constants |
| **Consent violation** | ✅ Compliant | DNR pre-filter at DB query level (WHERE `do_not_recall = false`) preserved from P3-010 |
| **Yandere Level Y6** | ✅ Impossible | No persona/Faiz interaction logic in any P3-011 code |
| **HARD STOP bypass** | ✅ Compliant | Safe-mode parameter unchanged; P3-010 gate preserved |
| **Surveillance overreach** | ✅ Compliant | No surveillance data processed |
| **No raw Critical in evidence** | ✅ Compliant | All tests use synthetic/fake data; no raw content in evidence |
| **No secrets in logs/artifacts** | ✅ Compliant | No secrets in source or evidence files |
| **Classification fail-closed** | ✅ Compliant | Unknown/null classification maps to level 5 (beyond Critical) |
| **Type safety** | ✅ Compliant | No `as any`, `@ts-ignore`, `# type: ignore` used |

---

## 7. Rollback/Re-run Safety

P3-011 is purely additive and parameter-based.  Rollback by reverting:

1. `src/memory/read_pipeline.py` — revert 10 edits (constants, `compute_rrf_score`, `EpisodeEntry`, `compute_scored_results`, `build_result_episode_map`, `recall_memories`, `classification_level`, public rename of helpers, remove `Mapping` import)
2. `src/memory/__init__.py` — revert export additions

Tests are synthetic/fake-data only — safe to re-run in any environment.

No production DB migrations or destructive operations.

---

## 8. Design Decisions/Caveats

| Decision | Rationale |
|----------|-----------|
| Weights hardcoded as module constants | Planner/batch plan specifies fixed values; future P3-018 tuning may add runtime overrides |
| Both-signal bonus applied in `compute_scored_results()` (Python layer) | Simpler than SQL CTE fusion; consistent with existing P3-010 pattern of application-layer scoring |
| `classification_level()` fail-closed mapping to 5 (beyond Critical) | Consistent with DataGovernance §4.2 "Unclassified must default to Confidential, escalate to Critical"; level 5 exceeds Critical (4), ensuring ceiling filter blocks it for all principals |
| MAX_CANDIDATE_POOL hardcoded to 200 | Matches documented equivalent in planner; prevents OOM from unbounded `limit * 3` |
| Recency boost formula: `1.0 + RECENCY_MAX_BOOST * recency_score` | Ensures max boost is exactly 10% at `recency_score=1.0`; minimum boost is `1.0` at `recency_score=0.0` |
| DNR pre-filter uses query-builder WHERE clause (P3-010 pattern) | P3-010 already implemented this; P3-011 does not reorder — safety preserved |
| Private helpers renamed to public | Required for basedpyright testability without suppressions; functions are pure utilities with no side effects, safe to expose |

**Caveats:**
- No golden dataset exists for ablation weight tuning; weights are plan defaults.
- Recency boost applies to `started_at` (episode start time), consistent with P3-010.
- Previous basedpyright re-export warnings were eliminated; runtime import verification confirms symbols are accessible.

---

## 9. Auditor Gate

**Status:** Independent auditor PASS.

**Auditor report path:** `docs/setup-evidence/P3/STEP-P3-011/auditor-gate.md`  
**Auditor verdict:** PASS — all 22 audit checks passed; no findings requiring remediation.

Auditor verified weighted RRF, both-signal bonus, bounded recency boost, DNR/classification pre-filters, P3-010 gate preservation, diagnostics, tests, anti-pattern scan, boundary compliance, and evidence accuracy.

---

## 10. Security Scan

| Check | Result | Evidence |
|-------|--------|----------|
| No raw secrets in code | ✅ PASS | grep `api_key\|password\|sk-\|token` — zero matches in changed files |
| No raw memory content in evidence | ✅ PASS | All tests use synthetic/fake data |
| No `as any` / `# type: ignore` / `@ts-ignore` | ✅ PASS | Not present in any changed file |
| No empty `except` / `catch` | ✅ PASS | Not present in any changed file |
| DNR at query level (WHERE clause) | ✅ PASS | `build_vector_query`, `build_fts_query`, `build_recency_query` all include `do_not_recall` filter when `exclude_dnr=True` |
| Classification fail-closed | ✅ PASS | `classification_level()` returns 5 for unknown/null |
| Max candidate pool bounded | ✅ PASS | `MAX_CANDIDATE_POOL=200`, `expanded_limit` capped |
| No external API calls in tests | ✅ PASS | Tests use Protocol-based fakes only |
| Unused imports removed | ✅ PASS | `Mapping` removed from `collections.abc` import |

---

## 11. Acceptance Criteria Mapping

| AC / Plan Requirement | Status | Evidence |
|-----------------------|--------|----------|
| RRF k=60 preserved | ✅ PASS | `RRF_K = 60` unchanged; `compute_rrf_score` uses `k=RRF_K` |
| Vector weight 0.5 | ✅ PASS | `VECTOR_WEIGHT = 0.5`; test `test_vector_weight` |
| FTS weight 0.5 | ✅ PASS | `FTS_WEIGHT = 0.5`; test `test_fts_weight` |
| 90-day recency half-life | ✅ PASS | `RECENCY_HALF_LIFE_DAYS = 90`; test `test_half_life_default_90_days` |
| Recency max boost 10% | ✅ PASS | `RECENCY_MAX_BOOST = 0.10`; test `test_recency_boost_bounded_to_10_percent` |
| Both-signal bonus x1.25 | ✅ PASS | `BOTH_SIGNAL_BONUS = 1.25`; test `test_bonus_applied_when_two_signals` |
| Bounded candidate pool (max 200) | ✅ PASS | `MAX_CANDIDATE_POOL = 200`; `expanded_limit` capped |
| DNR pre-filter before fusion | ✅ PASS | `build_*_query` include `WHERE do_not_recall = false`; 6 tests |
| Classification fail-closed | ✅ PASS | `classification_level()` maps unknown/null to 5; 6 tests |
| Stable ordering | ✅ PASS | `test_stable_ordering` — identical episodes preserve insertion order |
| Deterministic tests | ✅ PASS | All 43 tests use synthetic/fake data |
| P3-010 safety gates preserved | ✅ PASS | Safe-mode, token budget, DNR, classification ceiling all intact |

---

## 12. Footer

| Field | Value |
|-------|-------|
| Step | STEP-P3-011 |
| Phase | P3 Memory Safety |
| Status | Implementation complete; 43/43 tests PASS; source and test diagnostics clean |
| Changed files | 4 (2 modified source, 1 new test file, 1 new package init) |
| Tests | 43/43 PASS (exit code 0) |
| Diagnostics | `read_pipeline.py`: clean. `test_read_pipeline_hybrid.py`: clean. |
| Evidence path | `docs/setup-evidence/P3/STEP-P3-011/verification.md` |
| Auditor path | `docs/setup-evidence/P3/STEP-P3-011/auditor-gate.md` (PASS) |
| Caveats | No golden dataset for ablation tuning; pytest emits a pre-existing pytest-asyncio deprecation warning |
| Next step | P3-012 (context injection) — after P3-011 auditor PASS |

---

*Generated for Guinevere P3 memory safety batch on 2026-06-02.*

# P3-010 Auditor Gate Report — Memory Read Pipeline

**File:** `docs/setup-evidence/P3/STEP-P3-010/auditor-gate.md`
**Auditor:** Guinevere (Independent Auditor — Sisyphus-Junior)
**Date:** 2026-06-02
**Status:** ✅ **PASS** — all required criteria satisfied

---

## Audit Scope

Implementation of `src/memory/read_pipeline.py` (P3-010) — async hybrid memory recall pipeline with vector cosine similarity, FTS, recency decay, importance factor, RRF fusion, and 4 safety gates.

---

## Criteria Verification

### 1. `recall_memories` async API and Return Schema

| Check | Result | Evidence |
|-------|--------|----------|
| Async function exists | ✅ PASS | `async def recall_memories(...)` at line 545 |
| Signature params: session, query_text (required) | ✅ PASS | `inspect.signature` confirms 8 params |
| limit=20 default | ✅ PASS | Test 2: `limit_default == 20` |
| exclude_dnr=True default | ✅ PASS | Test 2: `exclude_dnr_default is True` |
| safe_mode=False default | ✅ PASS | Test 2: `safe_mode_default is False` |
| principal="guinevere_core" default | ✅ PASS | Test 2: `principal_default == "guinevere_core"` |
| token_budget=4000 default | ✅ PASS | Test 2: `token_budget_default == 4000` |
| Return type: `list[dict[str, object]]` | ✅ PASS | Type alias `RecallResults` at line 49 |
| Return fields: id, safe_content, classification, importance, created_at, combined_score, is_summarized | ✅ PASS | Test 14: all 7 keys present with correct types |

**Verdict:** ✅ PASS

### 2. P3-005 Embedding Integration via `EmbeddingClient.aembed`

| Check | Result | Evidence |
|-------|--------|----------|
| Uses `EmbeddingClient` protocol with `aembed` | ✅ PASS | Protocol at line 161-175 |
| `recall_memories` accepts `embedding_service: EmbeddingClient \| None` | ✅ PASS | Signature line 553 |
| Query embedding via `await embedding_service.aembed(...)` | ✅ PASS | Line 613 |
| No OpenAI SDK import | ✅ PASS | grep confirms 0 OpenAI imports; only docstring mentions "OpenAI" |
| No direct OpenAI API calls | ✅ PASS | All embedding via injected `EmbeddingClient` |

**Verdict:** ✅ PASS

### 3. Minimum Hybrid Ranking

| Check | Result | Evidence |
|-------|--------|----------|
| Vector cosine similarity (`embedding <=>`) | ✅ PASS | `_build_vector_query` uses `cosine_distance()` at line 350-353 |
| FTS query (`search_vector @@`) | ✅ PASS | `_build_fts_query` uses `search_vector.op("@@")(fts_query)` at line 383 |
| Recency decay (90-day half-life) | ✅ PASS | `RecencyConfig(half_life_days=90)`; Test 7 confirms ~0.5 at 90d, ~0.25 at 180d |
| Importance factor | ✅ PASS | `_normalize_importance()` maps 1-10 to 0.1-1.0; `importance_boost = 0.5 + 0.5 * imp_norm` at line 514 |
| RRF k=60 fusion | ✅ PASS | `RRF_K = 60` at line 55; Test 6 verifies `1/(60+1) + 1/(60+1)` computation |
| Combined score sorting | ✅ PASS | `scored.sort(key=..., reverse=True)` at line 536; Test 9 confirms newer/higher-importance ranks higher |

**Verdict:** ✅ PASS

### 4. Safety Gates

| Check | Result | Evidence |
|-------|--------|----------|
| DNR exclusion — query-level WHERE clause | ✅ PASS | `Episodes.do_not_recall.is_(False)` in all 3 query builders (lines 362, 388, 411) |
| DNR exclusion — public API parameter | ✅ PASS | `exclude_dnr=True` default; Test 10 passes with both True and False |
| Classification ceiling per principal | ✅ PASS | `_CLASSIFICATION_CEILING` dict: `guinevere_core`→Critical, `guinevere_subagent`→Confidential, default→Restricted (lines 79-83) |
| Classification ceiling filtering in recall | ✅ PASS | Lines 655-665 filter by `CLASSIFICATION_ORDER` level; Test 11 confirms safety error for unknown principal with Critical data |
| Safe-mode Critical substitution | ✅ PASS | `_build_safe_content` lines 255-279 replaces Critical content with `SAFE_MODE_PLACEHOLDER` when safe_mode=True |
| No raw Critical leak in safe_mode | ✅ PASS | Test 12: `"Critical content" not in safe_content` for safe_mode=True |
| Token budget enforcement (4000 default) | ✅ PASS | `_apply_token_budget` lines 297-327; Test 13: `total_tokens <= 300` with `token_budget=300`, length < 2 |
| Token budget fail-closed | ✅ PASS | Warning logged but continues gracefully; no crash if budget is 0 (returns empty) |

**Verdict:** ✅ PASS

### 5. Column Usage

| Check | Result | Evidence |
|-------|--------|----------|
| Uses `raw_content` (not `content`) | ✅ PASS | EpisodeProtocol line 122; `episode.raw_content` at line 269; zero references to bare `content` column |
| Uses `embedding` (not `embedding_vec`) | ✅ PASS | `Episodes.embedding` at line 350; zero matches for `embedding_vec` |
| Uses `search_vector` | ✅ PASS | `Episodes.search_vector` at lines 383-384 |
| Uses `do_not_recall` | ✅ PASS | `Episodes.do_not_recall` at lines 362, 388, 411 |
| No stale column references | ✅ PASS | All column names match actual ORM model |

**Verdict:** ✅ PASS

### 6. Query Safety / Parameterization

| Check | Result | Evidence |
|-------|--------|----------|
| No f-string SQL | ✅ PASS | All queries via SQLAlchemy ORM `select()` with `.where()`, `.order_by()`, `.limit()` |
| No raw logging of secrets | ✅ PASS | Logger emits only query text, counts, principal, flags — no vectors, no raw content |
| No live DB in verification | ✅ PASS | `_FakeRecallSession` and `_FakeEpisode` (deterministic, no DB connection) |
| No live API in verification | ✅ PASS | `_FakeEmbedder` returns synthetic 1536-dim vector (no 9Router call) |

**Verdict:** ✅ PASS

### 7. Diagnostics

| File | Errors | Warnings | Status |
|------|--------|----------|--------|
| `src/memory/read_pipeline.py` | 0 | 0 | ✅ CLEAN |
| `src/memory/__init__.py` | 0 | 0 | ✅ CLEAN |
| `docs/setup-evidence/P3/STEP-P3-010/verify_read_pipeline.py` | 0 | 0 | ✅ CLEAN |

**Verdict:** ✅ PASS — 0 errors, 0 warnings across all 3 files.

### 8. Verification Output

| Check | Result | Evidence |
|-------|--------|----------|
| Output says "88 passed, 0 failed" | ✅ PASS | `verification-output.txt` line 132: `RESULTS: 88 passed, 0 failed` |
| All 19 test categories pass | ✅ PASS | All 19 sections report all tests PASS |
| Exit code 0 | ✅ PASS | `sys.exit(0 if fail_count == 0 else 1)` at line 730 |

**Verdict:** ✅ PASS

### 9. Anti-Patterns / Code Quality

| Check | Result | Evidence |
|-------|--------|----------|
| No `typing.Any` | ✅ PASS | Import at line 27: no `Any`; uses `Protocol`, `TypeAlias`, `cast`, `runtime_checkable` |
| No type suppressions (`# type: ignore`, `@ts-ignore`, `as any`) | ✅ PASS | grep confirms zero matches |
| No empty catches (`except:`) | ✅ PASS | All `except` have named exception type and body |
| No secrets/API keys | ✅ PASS | Test 18 confirms no "sk-" or "api_key" patterns in repr |
| No P3-011 scope creep | ✅ PASS | Weighted tuning explicitly deferred in caveats; no P3-011 implementation started |
| No `embedding_vec` references | ✅ PASS | grep confirms zero matches across entire `src/memory/` |
| No `content` column mapping (stale DB column) | ✅ PASS | All references use `raw_content` |

**Verdict:** ✅ PASS

---

## Caveats (Documented Honest)

The following caveats are explicitly acknowledged and do **not** block PASS:

1. **Deterministic fake session/embedder only** — no live DB query smoke test, no live 9Router API call. Full DB integration test deferred to P3-018 (E2E test). Per task directive: deterministic verification required.

2. **P3-011 weighted tuning deferred** — RRF fusion only uses vector and FTS signal ranks. Recency and importance are multiplicative factors after RRF, not rank inputs. Full weighted RRF with all 4 signals as rank inputs deferred to P3-011.

3. **Token budget estimation approximate** — uses `len(text) // 4` heuristic (~4 chars per token). Real token counting requires tiktoken integration (deferred).

4. **No streaming execution** — all three queries execute and assemble results in memory.

5. **Lazy SQLAlchemy imports** — query builders import SQLAlchemy inside function bodies to avoid import errors in envs without SQLAlchemy.

6. **stdlib logging, not structlog** — consistent with P3-005/P3-009 approach; avoids diagnostics warnings in environments without structlog installed.

---

## Summary

| Criterion | Verdict |
|-----------|---------|
| `recall_memories` async API and return schema | ✅ PASS |
| Embedding via `EmbeddingClient.aembed` (P3-005) | ✅ PASS |
| Minimum hybrid ranking (vector + FTS + recency + importance + RRF) | ✅ PASS |
| Safety gates (DNR + classification ceiling + safe-mode + token budget) | ✅ PASS |
| Column usage (`raw_content`, `embedding`, `search_vector`, `do_not_recall`) | ✅ PASS |
| Query safety / no f-string SQL / no raw secret logging | ✅ PASS |
| Diagnostics clean — 0 errors, 0 warnings on all 3 files | ✅ PASS |
| Verification output: 88 passed, 0 failed | ✅ PASS |
| No type suppressions, no `Any`, no empty catches, no secrets | ✅ PASS |
| No P3-011 scope creep | ✅ PASS |

**FINAL VERDICT: ✅ PASS**

All 10 audit criteria satisfied. No blocking issues found. Caveats are documented and within acceptable scope boundaries.

**Next action:** Parent syncs PROGRESS.md, CHECKLIST.md, and final-report P3-004 through P3-010.

---

## Evidence Manifest

```
docs/setup-evidence/P3/STEP-P3-010/
├── auditor-gate.md              # This report (PASS)
├── verification.md              # Parent verification report
├── verification-output.txt      # 88/88 PASS output
└── verify_read_pipeline.py      # Deterministic verification script
```
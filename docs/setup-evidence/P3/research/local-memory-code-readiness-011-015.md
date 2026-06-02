# P3-011 through P3-015 Local Code Readiness Report

**Date:** 2026-06-02  
**Author:** Guinevere (local code research)  
**Purpose:** Determine implementation readiness for P3-011..P3-015 before planner gate  
**Method:** Filesystem/code search — no external docs, no edits  
**Scope:** src/memory/, src/core/services/, alembic/, tests/, stepprompts/, docs/setup-evidence/P3/

---

## 0. Summary Verdict

**P3-011..P3-015 are implementation-ready with zero structural blockers.** P3-009 and P3-010 have already delivered the foundational hybrid ranking, DNR exclusion, classification ceiling, safe-mode content substitution, and token-budget enforcement. P3-011..P3-015 are increments on this existing foundation, not greenfield builds. The only missing artifact is a batch plan for this specific group and the consolidation module (P3-015). All dependency columns, safety infrastructure, logging patterns, test patterns, and protocol patterns are already proven.

---

## 1. Source File Inventory — Current State

### 1.1 src/memory/ — All 5 files exist, P3-009/010 complete

| File | Lines | Status | Key Exports |
|------|-------|--------|-------------|
| `src/memory/__init__.py` | 104 | COMPLETE | 32 public symbols re-exported |
| `src/memory/models.py` | 1208 | COMPLETE | 47 models across 12 schemas |
| `src/memory/embeddings.py` | 775 | COMPLETE (P3-005) | `EmbeddingService`, `embed()`, `aembed()`, `prepare_embedding_text()` |
| `src/memory/write_pipeline.py` | 359 | COMPLETE (P3-009) | `store_episode()`, `store_episode_batch()` |
| `src/memory/read_pipeline.py` | 733 | COMPLETE (P3-010) | `recall_memories()`, `RRF_K`, `RecencyConfig` |
| `src/memory/consolidation.py` | **MISSING** | New file for P3-015 | — |
| `src/memory/database.py` | **MISSING** | Optional convenience module | — |

### 1.2 Episodes Model — All DNR/Safety Columns Exist

| Column | Type | Status | Used By |
|--------|------|--------|---------|
| `id` | UUID | EXISTS | All |
| `raw_content` | Text | EXISTS | P3-009 write, P3-010 read, P3-014 safe-mode |
| `summary` | Text | EXISTS | P3-010 safe-mode substitution, P3-013 DNR summary |
| `embedding` | Vector(1536) | EXISTS | P3-010 vector search |
| `search_vector` | TSVECTOR (computed) | EXISTS | P3-010 FTS search |
| `do_not_recall` | Boolean (default: false) | EXISTS | P3-010 DNR exclusion, P3-013 toggle |
| `classification` | Text (ClassificationMetaMixin) | EXISTS | P3-010 ceiling, P3-014 safe-mode gate |
| `importance` | Integer (default: 5) | EXISTS | P3-010 ranking factor |
| `started_at` | TIMESTAMPTZ | EXISTS | P3-010 recency decay |
| `created_at` | TIMESTAMPTZ (ClassificationMetaMixin) | EXISTS | P3-010 result metadata |
| `tags` | ARRAY(Text) | EXISTS | Available for filtering |
| `related_ids` | ARRAY(UUID) | EXISTS | Cross-referencing |
| `episode_type` | Text | EXISTS | Available for type-specific logic |

**Critical finding:** The `do_not_recall` column IS present in the model (line 137-139 of `models.py`). This was flagged as missing in the earlier P3-004..010 readiness report (v1.0) but was subsequently added. All query builders (`_build_vector_query`, `_build_fts_query`, `_build_recency_query`) already include `WHERE do_not_recall = false`.

### 1.3 Classification Hierarchy — Fully Defined

In `src/memory/embeddings.py` (lines 101-115):

```
Public(0) < Internal(1) < Restricted(2) < Confidential(3) < Critical(4)
```

`CLASSIFICATION_ORDER` dict and `SAFE_FOR_EXTERNAL` set already exist.

### 1.4 src/core/services/ — HardStopHandler Available for P3-014

| File | Lines | Key API | Used By |
|------|-------|---------|---------|
| `src/core/services/hard_stop_handler.py` | 149 | `HardStopHandler.is_safe` property, `SafetyState.SAFE`, `get_guard_decision()` | P3-014 safe-mode memory gate |

The `HardStopHandler.is_safe` returns `bool` — directly integrable for P3-014's safe-mode memory gate decision.

### 1.5 Existing Tests — No Memory Tests

- 16 test files across `tests/discord/`, `tests/safety/`, `tests/smoke/`
- **No `tests/memory/` directory exists**
- Test pattern: `pytest` with `conftest.py`, Protocol-based dependency injection, `pytest-asyncio`
- P3-011..P3-015 will need test files created
- `pyproject.toml` configured: `testpaths = ["tests"]`, `pythonpath = ["src"]`

### 1.6 Alembic — No Migration Files

- `alembic/env.py` EXISTS — async + multi-schema, imports `src.memory.models.Base`
- `alembic/versions/` — **EMPTY** (no migration files generated yet)
- P3-011..P3-015 are application-layer only; no new DB migrations needed

---

## 2. Existing Code Path Inventory

### 2.1 `src/memory/read_pipeline.py` — Key Functions and Lines

| Line(s) | Function/Constant | Signature / Value | Relevance |
|---------|------------------|-------------------|-----------|
| 55 | `RRF_K` | `int = 60` | P3-011 tuning |
| 58 | `RECENCY_HALF_LIFE_DAYS` | `int = 90` | P3-011 category-specific half-lives |
| 61 | `EXPANDED_LIMIT_MULTIPLIER` | `int = 3` | P3-011 candidate pool sizing |
| 65 | `SAFE_MODE_PLACEHOLDER` | `str` | P3-014 safe-mode content |
| 69 | `DEFAULT_TOKEN_BUDGET` | `int = 4000` | P3-012 budget |
| 72 | `CHARS_PER_TOKEN` | `int = 4` | P3-012 token estimation |
| 79-89 | `_CLASSIFICATION_CEILING` | `dict[str, str]` | P3-014 ceiling expansion |
| 117-131 | `EpisodeProtocol` | Protocol | P3-011/014 may extend |
| 161-175 | `EmbeddingClient` | Protocol | Reusable |
| 183-216 | `RecencyConfig` | dataclass with `.score()` | P3-011 half-life expansion |
| 224-239 | `_compute_rrf_score()` | pure function | P3-011 weighted RRF |
| 242-247 | `_normalize_importance()` | pure function | P3-011 importance tuning |
| 255-279 | `_build_safe_content()` | pure function | **P3-014 PRIMARY** — expand to all classifications |
| 287-289 | `_estimate_tokens()` | pure function | P3-012 token estimation |
| 297-327 | `_apply_token_budget()` | pure function | P3-012 budget enforcement |
| 335-363 | `_build_vector_query()` | ORM query builder | P3-011 candidate expansion |
| 366-389 | `_build_fts_query()` | ORM query builder | P3-011 candidate expansion |
| 392-412 | `_build_recency_query()` | ORM query builder | P3-011 candidate expansion |
| 420-427 | `_EpisodeEntry` | dataclass | P3-011 ranking expansion |
| 434-474 | `_build_result_episode_map()` | pure function | P3-011 map expansion |
| 482-537 | `_compute_scored_results()` | pure function | **P3-011 PRIMARY** — weighted RRF, multi-signal bonus |
| 545-710 | `recall_memories()` | async main entry | **P3-013** DNR param, **P3-014** safe_mode param, **P3-011** new params |

### 2.2 `src/memory/write_pipeline.py` — Key Functions and Lines

| Line(s) | Function/Constant | Signature / Value | Relevance |
|---------|------------------|-------------------|-----------|
| 98-104 | `WritePipelineError`, `WritePipelineCriticalError` | Errors | P3-013 may reuse |
| 111-227 | `store_episode()` | async write | P3-013 DNR toggle nearby |
| 235-267 | `store_episode_batch()` | async batch | — |
| 275-285 | `_guard_critical()` | validation | Pattern for P3-013 DNR guard |
| 288-306 | `_compute_embedding()` | embedding helper | — |

### 2.3 `src/memory/models.py` — Key Episodes Model

| Line(s) | Column/Attribute | Relevance |
|---------|-----------------|-----------|
| 91-149 | `Episodes` class | All P3-011..015 |
| 137-139 | `do_not_recall` | P3-013 PRIMARY field |
| 132-136 | `search_vector` | P3-011 FTS |
| 129-131 | `embedding` | P3-011 vector |
| 140-142 | `importance` | P3-011 ranking |
| 114-116 | `started_at` | P3-011 recency |
| 152-207 | `SemanticFacts` | P3-015 consolidation target |
| 269-285 | `InnerJournal` | P3-015 consolidation |

### 2.4 `src/memory/embeddings.py` — Key Utilities

| Line(s) | Function/Constant | Relevance |
|---------|------------------|-----------|
| 101-105 | `PUBLIC`..`CRITICAL` constants | All P3 steps |
| 107-113 | `CLASSIFICATION_ORDER` | P3-011/P3-014 ceiling |
| 115 | `SAFE_FOR_EXTERNAL` | — |
| 206-268 | `prepare_embedding_text()` | — |
| 402-670 | `EmbeddingService` class | P3-011 embedding for vector search |
| 720-757 | `embed()`, `aembed()`, etc. | Convenience functions |

### 2.5 `src/core/services/hard_stop_handler.py` — Safety State

| Line(s) | Function/Property | Relevance |
|---------|------------------|-----------|
| 20-22 | `SafetyState` enum (NORMAL, SAFE) | P3-014 safe-mode state |
| 33-57 | `HardStopHandler` dataclass | P3-014 integration |
| 59-61 | `is_safe` property | **P3-014 PRIMARY integration point** |
| 63-77 | `check()` method | — |
| 125-149 | `get_guard_decision()` | — |

### 2.6 `src/core/services/prompt_loader.py`

| Line(s) | Function | Relevance |
|---------|----------|-----------|
| (not read in full) | `prompt_loader` module | P3-012 context injection integration point |

### 2.7 `src/core/main.py`

| Line(s) | Function | Relevance |
|---------|----------|-----------|
| 9-13 | `lifespan()` async context manager | **P3-015** scheduler startup/shutdown |
| 16-20 | FastAPI app creation | P3-015 integration |

---

## 3. Per-Step Readiness Assessment

### 3.1 P3-011: Hybrid Ranking (Enhancement)

**What StepPrompts says:** "Combines vector similarity + FTS + recency decay."

**What currently exists in `read_pipeline.py`:**

- **RRF fusion (k=60):** `_compute_rrf_score()` at line 224, `RRF_K = 60` at line 55
- **Recency decay:** `RecencyConfig.score()` at line 196 with 90-day half-life
- **Importance factor:** `_normalize_importance()` at line 242, applied as `importance_boost = 0.5 + 0.5 * imp_norm` at line 514
- **Combined scoring:** `_compute_scored_results()` at line 482 with formula: `combined = rrf_score * recency_score * importance_boost`
- **Multi-signal candidate pool:** `_build_result_episode_map()` at line 434 merges vector + FTS + recency

**Gaps / What to build:**
1. **Weighted RRF:** `_compute_rrf_score()` uses raw RRF (equal weight per signal). Add `w_vec`, `w_fts` parameters.
2. **Multi-signal bonus:** Add `1.0 + bonus * (num_signals - 1)` factor per ParadeDB pattern — need to track `num_signals` that found each episode in `_EpisodeEntry`.
3. **Category-specific half-lives:** `RecencyConfig` uses one global half-life (90 days). Add `episode_type` to half-life mapping: episodic=90, semantic_fact=180, procedural=365, etc.
4. **Evaluation harness:** Ablation test framework against golden dataset.
5. **Tunable parameters in `recall_memories()` signature.**

**Files likely touched:**
- `src/memory/read_pipeline.py` — primary changes
- `src/memory/__init__.py` — export new config types
- `tests/memory/test_read_pipeline_hybrid.py` — new test file

**Effort:** ~2-3h

---

### 3.2 P3-012: Context Injection

**What StepPrompts says:** "Top-k memories injected into system prompt before LLM call."

**What currently exists:**
1. **`prompt_loader.py`** — File-based prompt loading with safety validation. Does NOT currently inject memory context.
2. **Token budget:** `_apply_token_budget()` at line 297 of `read_pipeline.py`, `DEFAULT_TOKEN_BUDGET = 4000`.
3. **Research available:** `external-context-injection-token-budget.md` (533 lines) covers safety valve, degradation order, prompt position theory.

**Gaps / What to build:**
1. **Context assembler function:** Takes ranked memory results + system prompt + user query -> final prompt.
2. **Safety valve:** If memory tokens exceed budget, drop memory layer, inject system notice.
3. **OWASP/PCFI screening:** Scan retrieved memory for prompt-injection patterns before assembly.
4. **Observability:** Token count per layer, metadata-only logging, SHA-256 audit trail.
5. **Top-K default:** 3 memories (range 1-5), relevance threshold cosine >= 0.3.

**Files likely touched:**
- `src/memory/context_injection.py` — NEW
- `src/core/services/prompt_loader.py` — integration point
- `src/memory/read_pipeline.py` — budget signaling adjustments
- `tests/memory/test_context_injection.py` — new test file

**Dependencies:** P3-010 (ranked results), P3-011 (ranking quality)
**Effort:** ~3-4h

---

### 3.3 P3-013: Do-Not-Recall (Safety-Critical)

**What StepPrompts says:** "`UPDATE memory.episodes SET do_not_recall = true WHERE id = $1` blocks specific memories."

**What currently exists:**
1. **`do_not_recall` column:** `models.py` line 137-139 — `Boolean, nullable=False, server_default=text("false")`.
2. **DNR exclusion:** `exclude_dnr=True` default on `recall_memories()`. All query builders include `WHERE do_not_recall = false`.
3. **DNR in `store_episode()`:** `do_not_recall=False` default when creating episodes.
4. **Consent model:** `consent.consent_ledger` table exists in models.
5. **MemoryRecallEvalSpec §9.1:** 8-layer DNR enforcement chain defined.

**Gaps / What to build:**
1. **DNR toggle function:** `mark_dnr(episode_id: UUID, reason: str, principal: str)` — sets `do_not_recall = true`. Must be **zero-bypass**.
2. **DNR audit trail:** Log every DNR action via `audit.audit_trail` table or structured log.
3. **Post-query DNR verification:** Audit check after recall — verify no DNR records leaked.
4. **Consent ledger integration (Layer 1):** Cross-reference `consent.consent_ledger` for `MEMORY_DNR_MARKED` events.
5. **Discord `/memory-forget`:** Currently stub at `bot.py` line 47. Wire to `mark_dnr()`.
6. **DNR reversal guard:** Reversal requires explicit Faiz approval with full audit trail.

**Critical safety constraints:**
- DNR must be zero-bypass — no code path may return DNR-marked memory
- DNR exclusion is at query level (WHERE clause), not post-filter — verified in P3-010
- DNR reversal requires explicit Faiz approval with audit trail

**Files likely touched:**
- `src/memory/write_pipeline.py` — add `mark_dnr()` function (lines 111-227 vicinity)
- `src/memory/read_pipeline.py` — Layer 1 consent ledger check
- `src/discord/bot.py` — wire `/memory-forget` (currently stub at line 47)
- `src/discord/commands.py` — update `memory-forget` command handler
- `tests/memory/test_dnr.py` — new test file

**Dependencies:** P3-010 (DNR exclusion exists)
**Effort:** ~2-3h

---

### 3.4 P3-014: Safe-Mode Memory Gate (Safety-Critical)

**What StepPrompts says:** "During safe mode, only neutral summaries are injected, not raw emotional content."

**What currently exists:**
1. **`HardStopHandler.is_safe`:** `hard_stop_handler.py` line 60 — `return self.state == SafetyState.SAFE`.
2. **`recall_memories()` `safe_mode` param:** Line 551 — already accepts `safe_mode: bool = False`.
3. **`_build_safe_content()`:** Line 255 — replaces Critical raw content with placeholder when safe_mode=True.
4. **`SAFE_MODE_PLACEHOLDER`:** Line 65 — `"[Content redacted per safe-mode policy — Critical classification]"`.
5. **Classification ceiling:** Line 79-89 — `_CLASSIFICATION_CEILING` dict.

**Current gap in `_build_safe_content()`:**
```python
# Line 272 — only blocks Critical:
if safe_mode and episode.classification == CRITICAL:
    return SAFE_MODE_PLACEHOLDER, False
```
Must expand to return summaries for ALL classifications when safe-mode is active.

**Gaps / What to build:**
1. **Expand `_build_safe_content()`:** Safe-mode should return summary-only for ALL classifications, not just Critical. If no summary exists, return placeholder for Critical, return raw with warning flag for lower classes.
2. **Integrate `HardStopHandler.is_safe`:** `recall_memories()` must accept or auto-detect safe-mode state from the handler passed from agent loop.
3. **Neutral summary generation:** All episodes return summaries when safe-mode active.
4. **Memory injection guard (P3-012):** Context injection module must check safe-mode before injecting.
5. **Zero-tolerance enforcement:** Prometheus counter `guinevere_safe_mode_recall_violation_total`.

**Files likely touched:**
- `src/memory/read_pipeline.py` — expand `_build_safe_content()` (lines 255-279)
- `src/core/services/hard_stop_handler.py` — MAY add memory gate audit event
- `tests/memory/test_safe_mode_memory.py` — new test file

**Dependencies:** P3-010 (safe_mode param exists), HardStopHandler (exists, P1-021)
**Effort:** ~2-3h

---

### 3.5 P3-015: Memory Consolidation Job

**What StepPrompts says:** "Daily memory consolidation: aggregate episodic -> semantic memory."

**What currently exists:**
1. **`apscheduler>=3`:** `pyproject.toml` line 16 — already declared.
2. **`SemanticFacts` model:** `models.py` line 152 — `subject`, `predicate`, `object_val`, `confidence`, `source_episode`, `embedding`.
3. **`InnerJournal` model:** `models.py` line 269 — for daily journal entries.
4. **Episodes queryable by date:** `created_at` (ClassificationMetaMixin), `started_at`.
5. **FastAPI `lifespan`:** `src/core/main.py` lines 9-13 — async lifecycle manager.
6. **No existing scheduler infrastructure** exists in `src/`.

**Gaps / What to build:**
1. **Create `src/memory/consolidation.py`:** New module with `consolidate_daily()` async function.
2. **Consolidation logic:** Query yesterday's episodes, call LLM/prompt_loader to generate semantic facts, write to `SemanticFacts` via ORM or `store_episode` pattern.
3. **Contradiction detection:** Check existing `semantic_facts.contradicts_ids` before inserting.
4. **APScheduler integration:** Register cron job in FastAPI lifespan, shut down cleanly.
5. **Idempotency:** Skip dates already consolidated (check by `last_verified` or a flag).
6. **Error handling:** All exceptions caught and logged; job never crashes the application.

**Files likely touched:**
- `src/memory/consolidation.py` — NEW
- `src/core/main.py` — integrate scheduler into lifespan
- `src/memory/__init__.py` — export consolidation symbols
- `tests/memory/test_consolidation.py` — new test file

**Dependencies:** P3-014 (safe-mode awareness during consolidation of sensitive content)
**Effort:** ~3-4h

---

## 4. Dependency Map for P3-011 Through P3-015

```
P3-010 (read_pipeline.py)
  |
  +-- P3-011 (hybrid ranking enhancement — modifies read_pipeline.py)
  |
  +-- P3-012 (context injection — consumes read_pipeline.py output)
  |     |
  |     +-- P3-014 (safe-mode gate — read_pipeline.py + hard_stop_handler)
  |
  +-- P3-013 (DNR toggle — write_pipeline.py + discord + read_pipeline.py)
        |
        +-- P3-015 (consolidation — writes semantic_facts, benefits from DNR)
```

### Sequential Requirements
- P3-010 must be complete (PASS verified)
- P3-015 logically depends on P3-014 (safe-mode during consolidation)
- P3-012 logically depends on P3-014 (safe-mode must be enforced at injection time)

### Parallel Opportunities
- **P3-011 and P3-013** are fully independent (enhancing read vs. add DNR toggle)
- **P3-013 and P3-014** have some overlap (both touch read pipeline) — sequential recommended
- **P3-011 and P3-015** are fully independent

### Collision Scan — Shared Writers

| File | P3-011 | P3-012 | P3-013 | P3-014 | P3-015 |
|------|--------|--------|--------|--------|--------|
| `src/memory/read_pipeline.py` | PRIMARY | minor | minor | PRIMARY | — |
| `src/memory/write_pipeline.py` | — | — | PRIMARY | — | minor |
| `src/memory/__init__.py` | exports | exports | exports | exports | exports |
| `src/core/services/prompt_loader.py` | — | PRIMARY | — | minor | — |
| `src/core/main.py` | — | — | — | — | PRIMARY |
| `src/discord/bot.py` | — | — | PRIMARY | — | — |

**Shared writer conflict:** All five steps write to `src/memory/__init__.py`. Must be serialized or parent-owned.

---

## 5. Test Infrastructure Readiness

### Existing patterns to follow:
- `tests/safety/test_hard_stop_handler.py` — 248 lines, 11 test classes, `@pytest.mark.parametrize`, Protocol-based injection, deterministic
- P3-009 verification: 58 tests using `_FakeAsyncSession` and `_FakeEmbedder`
- P3-010 verification: 88 tests using `_FakeRecallSession` and `_FakeEmbedder` with protocol-based episodes

### For P3-011..P3-015, must create:
- `tests/memory/__init__.py` — new package
- `tests/memory/conftest.py` — shared fixtures (fake sessions, fake embedder, episode factory)
- `tests/memory/test_hybrid_ranking.py` — weighted RRF, multi-signal bonus, half-life configs
- `tests/memory/test_context_injection.py` — safety valve, budget enforcement, degradation order
- `tests/memory/test_dnr.py` — zero-bypass, toggle, audit trail, consent ledger
- `tests/memory/test_safe_mode.py` — HardStopHandler integration, all-class safe-mode
- `tests/memory/test_consolidation.py` — daily job, idempotency, contradiction detection

---

## 6. Acceptance Criteria Mapping

| AC ID | Description | P3 Step | Status |
|-------|-------------|---------|--------|
| AC-MEM-001 | PostgreSQL + Redis, no SQLite | P3-009/010 | COMPLIANT |
| AC-MEM-002 | Classification metadata on all records | P3-009/010 | COMPLIANT |
| AC-MEM-003 | Critical memory encrypted at rest | P3-009/010 | COMPLIANT |
| AC-MEM-004 | Minimum necessary recall (token budget) | P3-010, P3-011, P3-012 | P3-010 has 4K budget; P3-011/P3-012 enhance |
| AC-MEM-005 | Do-not-recall prevents LLM injection | P3-010, P3-013 | P3-010 DNR exclusion; P3-013 toggle + full enforcement |
| AC-MEM-006 | Recall quality evaluation | P3-011, P3-015 | Requires golden dataset for benchmarks |
| AC-DATA-001 | Classification metadata on all persistent data | P3-015 | Must ensure new consolidated facts have classification |
| AC-DATA-004 | LLM context uses minimum data | P3-012, P3-014 | Context injection + safe-mode gate |
| AC-SEC-002 | Sub-agents no Critical data access | P3-010, P3-014 | Classification ceiling + safe-mode |
| AC-SEC-003 | Secrets in SOPS+age only | All | Embedding keys from env (SOPS-decrypted) |

---

## 7. Implementation Constraints Summary

| Constraint | Detail | Source |
|------------|--------|--------|
| Column `embedding` (not `embedding_vec`) | Verified | `models.py` line 129 |
| Column `raw_content` (not `content`) | Verified | `models.py` line 128 |
| Column `do_not_recall` EXISTS | Boolean default false | `models.py` line 137-139 |
| Column `search_vector` EXISTS | Computed TSVECTOR | `models.py` line 132-136 |
| HardStopHandler.is_safe returns bool | Integration point | `hard_stop_handler.py` line 60 |
| APScheduler in dependencies | Available | `pyproject.toml` line 16 |
| FastAPI lifespan exists | For scheduler | `src/core/main.py` lines 9-13 |
| No `typing.Any` | Anti-pattern | AGENTS.md |
| No empty `except` | Anti-pattern | AGENTS.md |
| No raw content in logs | Verified P3-009/010 | Verification reports |
| No Structlog in memory modules (stdlib logging) | Pattern | P3-005, P3-009, P3-010 |
| No `tests/memory/` directory exists | Must create | Infra gap |
| No golden dataset exists | Must create for P3-011 eval | Research gap |
| No batch plan for P3-011..015 | Missing | Planner gate not complete |

---

## 8. Ready to Proceed Assessment

### Green (ready, no blockers)

| Item | Status |
|------|--------|
| P3-010 `recall_memories()` with hybrid ranking | COMPLETE |
| RRF k=60 fusion logic | COMPLETE |
| Recency decay (90d half-life) | COMPLETE |
| DNR exclusion at query level | COMPLETE |
| `do_not_recall` column in Episodes model | COMPLETE |
| Classification ceiling per principal | COMPLETE |
| Safe-mode content substitution (Critical only) | COMPLETE |
| Token budget enforcement (4K) | COMPLETE |
| HardStopHandler.is_safe property | COMPLETE |
| APScheduler in dependencies | COMPLETE |
| SemanticFacts model (consolidation target) | COMPLETE |
| FastAPI lifespan (scheduler startup) | COMPLETE |
| Embedding service (P3-005) | COMPLETE |
| Write pipeline (P3-009) | COMPLETE |
| P3-010 verification + auditor PASS | COMPLETE |
| Research: hybrid ranking, context injection, safety gates | COMPLETE |

### Yellow (need attention, not blockers)

| Item | Impact | Action Needed |
|------|--------|---------------|
| P3-011 weighted RRF not configurable | Tuning flexibility | Add weight params to `_compute_rrf_score()` |
| P3-011 category-specific half-lives missing | Recency accuracy | Add `episode_type` mapping to `RecencyConfig` |
| P3-011 no golden dataset | Evaluation blocked | Create golden dataset for benchmarks |
| P3-012 context injection module missing | Core feature | Create `context_injection.py` |
| P3-012 no OWASP/PCFI screening | Security gap | Add injection pattern scanning |
| P3-013 DNR toggle function missing | Core feature | Add `mark_dnr()` to write pipeline |
| P3-013 no consent ledger integration | Layer 1 DNR gap | Cross-reference `consent.consent_ledger` |
| P3-014 safe-mode only blocks Critical | Overly narrow | Expand to all classifications |
| P3-014 HardStopHandler not directly referenced | Integration gap | Pass `handler.is_safe` to `recall_memories()` |
| P3-015 `consolidation.py` missing | Core feature | Create file + APScheduler integration |
| No `tests/memory/` directory | Test infra gap | Create directory + `conftest.py` |
| StepPrompts P3-011..015 very brief | Spec ambiguity | Use existing research + P3-010 pattern |

### Red (blockers for this batch)

| Blocking Issue | Blocks | Resolution |
|----------------|--------|------------|
| **None** | — | All foundation steps (P3-004..010) are complete and verified |

---

## 9. Recommended Execution Order

Based on dependency analysis, collision scan, and safety priority:

1. **P3-013 (DNR toggle)** — Smallest diff, highest safety payoff. Adds `mark_dnr()` to write pipeline, wires Discord `/memory-forget`. Quick win, zero-bypass critical.
2. **P3-014 (safe-mode gate)** — Expand existing safe-mode to all classifications, integrate `HardStopHandler.is_safe`. Low-risk incremental change.
3. **P3-011 (hybrid ranking)** — Incremental enhancement. Weighted RRF, category-specific half-lives, multi-signal bonus. All pure additions, no refactors.
4. **P3-012 (context injection)** — New module. Consumes P3-010/P3-011 output. Highest novelty but fully researched.
5. **P3-015 (consolidation job)** — Independent new module with APScheduler. Depends on P3-014 for safe-mode awareness.

---

*End of research report.*

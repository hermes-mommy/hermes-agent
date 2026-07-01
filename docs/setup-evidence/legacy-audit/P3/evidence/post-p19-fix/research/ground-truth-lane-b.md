# Lane B — P3 Post-P19 Memory Fix: Ground Truth Report

**Date:** 2026-06-27
**Phase:** 0 — Ground Truth
**Author:** Guinevere (orchestrator)
**Source:** Direct inspection of source code, audit reports, P19 deploy evidence

---

## 1. Executive Summary

P3 memory system was implemented and verified (19/19 steps PASS). However, P19 (Multi-Project Context) was deployed to production on 2026-06-27 with `project_id` columns added to `memory.episodes` and `memory.semantic_facts`. The `semantic_facts.project_id` column is **NOT NULL**, but `consolidate_episodes_to_facts()` has **zero project awareness**. If the consolidation scheduler is enabled, it will crash with a NOT NULL constraint violation.

Additionally, the life_kernel recall path has **zero** references to `EmbeddingService` — memory recall uses `recall_memories()` but the embedding service is not wired, causing vector recall to be effectively dead for brain-driven memory retrieval.

---

## 2. BUG-008: CRITICAL — Consolidation has zero project_id awareness

### 2.1 Source Confirmation

**File:** `src/memory/consolidation.py`

- `consolidate_episodes_to_facts()` (line 275): Signature has NO `project_id` parameter.
- SemanticFacts construction (line 387-397): Creates `SemanticFacts(...)` without setting `project_id`.
- `_extract_facts_from_episode()` (line 559): Does not extract `project_id` from source episodes.
- `daily_consolidation_job()` (line 785): Wraps consolidation but passes no project context.

### 2.2 DB Schema Confirmation

**File:** `src/memory/models.py`

```python
# Episodes (line 160-166):
project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    UUID(as_uuid=True), nullable=True, comment="P19 project namespace"
)
project_scope: Mapped[str] = mapped_column(
    Text, nullable=False, server_default=text("'project'"),
    comment="P19 scope: 'project' or 'global'"
)

# SemanticFacts (line 218-273): Has project_id field (duplicated at line 190)
project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    UUID(as_uuid=True), nullable=True,
    comment="Project namespace UUID. NULL = global-scope entity visible from all projects.",
)
```

**CRITICAL:** The P19 migration made `semantic_facts.project_id` NOT NULL in production. The SQLAlchemy model shows `nullable=True` but the actual deployed DB in production has `NOT NULL` constraint. This is confirmed by the P19 post-deploy audit reports.

### 2.3 Impact

- Consolidation scheduler CANNOT be enabled without fixing this.
- If enabled, `SemanticFacts(...)` construction without `project_id` → NOT NULL constraint violation → crash.
- This is a **runtime blocker**.

### 2.4 Fix Required

1. Modify `consolidate_episodes_to_facts()` to accept and forward `project_id` from source episodes.
2. Extract `project_id` from each source episode in `_extract_facts_from_episode()`.
3. Set `project_id` + `project_scope` on each created `SemanticFacts`.
4. Handle episodes with NULL `project_id` (pre-P19 legacy data) by defaulting to the default project UUID.

---

## 3. BUG-003: store_episode_batch loses project_id

### 3.1 Source Confirmation

**File:** `src/memory/write_pipeline.py`

The `store_episode_batch()` function accepts episodes but does not populate `project_id` on the ORM objects. Confirmed by audit reports (BUG-003).

### 3.2 Fix Required

- `store_episode_batch()` must accept `project_id` parameter and set it on each episode.
- Default to the default project from P19 registry when not provided.

---

## 4. Life-Kernel Recall Path: embedding_service NOT wired

### 4.1 Source Confirmation

**File:** `src/core/main.py` (line 260-303)

The life_kernel recall adapter is wired in `main.py`:

```python
memory_adapter = MemoryRecallAdapter(memory_client=_life_recall_fn)
```

But `_life_recall_fn` calls `recall_memories()` WITHOUT passing `embedding_service`:

```python
async def _life_recall_fn(
    query_text: str,
    limit: int = 20,
    ...
) -> RecallResults:
    return await _recall_memories(
        session,
        query_text,
        limit=limit,
        exclude_dnr=True,
        safe_mode=_life_safe_recall,
        project_id=project_id,
        # NO embedding_service parameter!
    )
```

**File:** `src/life_kernel/` — grep for `EmbeddingService` returns **zero matches**.

### 4.2 Impact

- Vector recall is dead for brain-driven memory. Only FTS + recency signals work.
- The `recall_memories()` function gracefully falls back to keyword-only when `embedding_service is None`, but this means semantic (vector) similarity is completely absent from brain memory retrieval.
- This is a silent degradation — no error, just poor recall quality.

### 4.3 Fix Required

1. Import `EmbeddingService` in `main.py` (or life_kernel module).
2. Pass `embedding_service` to `recall_memories()` in the life_kernel recall adapter.
3. Handle the case where embedding service is unavailable (9Router down) gracefully — already handled by `recall_memories()` fallback.

---

## 5. Episodes embedding NULL — backfill/repair needed

### 5.1 Source Confirmation

**File:** `src/memory/models.py` (line 132-134)

```python
embedding: Mapped[Optional[list[float]]] = mapped_column(
    Vector(1536), nullable=True
)
```

The `embedding` column is nullable. Episodes that were stored before the embedding pipeline was active (or during P19 migration) have NULL embeddings.

### 5.2 Impact

- Episodes with NULL embeddings are excluded from vector search (`WHERE embedding IS NOT NULL` in `build_vector_query()`).
- These episodes can only be found via FTS or recency — not via semantic similarity.

### 5.3 Fix Required

- Create an idempotent, safe backfill job that:
  1. Queries episodes with NULL embedding and non-NULL raw_content.
  2. Computes embeddings via `EmbeddingService`.
  3. Updates the embedding column.
  4. Is idempotent (can be re-run safely).
  5. Has a batch size limit to avoid overwhelming the embedding API.
  6. Logs progress and can be resumed.

---

## 6. KG ORM stale mapping check

### 6.1 Source Confirmation

The KG code (`src/knowledge_graph/`) references `memory.kg_entities` and `memory.kg_edges` via raw SQL strings (not SQLAlchemy ORM models). There are NO ORM model classes for `kg_entities` or `kg_edges` in `src/memory/models.py`.

**Tables referenced in KG code:**
- `memory.kg_entities` — used extensively in raw SQL queries
- `memory.kg_edges` — used extensively in raw SQL queries

**In `src/memory/models.py`:** There is a `KnowledgeGraph` class (line 401-416) mapping to `memory.knowledge_graph` — this is a DIFFERENT table, not `kg_entities`/`kg_edges`.

### 6.2 Impact

- The KG module uses raw SQL strings, not ORM models. This works at runtime but means:
  - No ORM-level validation of schema
  - No Alembic migration tracking for KG tables
  - The `knowledge_graph` table in models.py is a stale/legacy table

### 6.3 Fix Required

- Add ORM models for `kg_entities` and `kg_edges` to `src/memory/models.py` (or a separate KG models file).
- Mark the legacy `knowledge_graph` table as deprecated.
- OR add an adapter/compatibility layer.

---

## 7. Consolidation Scheduler Status

### 7.1 Source Confirmation

**File:** `src/core/main.py` (lines 24-39)

```python
# P3-015 consolidation scheduler registration (optional — no DB by default)
# ...
# To activate the daily consolidation scheduler at runtime, inject an async
# session factory and call:
#   from apscheduler.schedulers.asyncio import AsyncIOScheduler
#   from src.memory.consolidation import register_consolidation_job
#   ...
```

The consolidation scheduler is **commented out** — it's never activated in production. This is correct given BUG-008, but the instructions for activation are present.

### 7.2 Fix Required

After BUG-008 is fixed, the scheduler can be activated. The activation code is already written (commented out in `main.py`), just needs uncommenting and verification.

---

## 8. DNR/Consent Boundary Status

### 8.1 Source Confirmation

**File:** `src/memory/consolidation.py` (lines 322-323)
```python
stmt = select(Episodes).where(Episodes.do_not_recall.is_(False))
```

**File:** `src/memory/read_pipeline.py` (line 562)
```python
if exclude_dnr:
    stmt = stmt.where(Episodes.do_not_recall.is_(False))
```

DNR (Do Not Recall) is enforced at the query level in both consolidation and recall. The consent boundary is preserved.

### 8.2 Status

- DNR boundary: **INTACT** — no fix needed.
- Classification ceiling: **INTACT** — enforced in `recall_memories()`.
- Safe-mode content substitution: **INTACT** — enforced in `build_safe_content()`.

---

## 9. P20 Regression Risk

### 9.1 Assessment

- P20 life_kernel is in EARLY PRODUCTION ACCEPTANCE (operator waived 24h soak).
- Memory recall is wired into the life-mind graph via `MemoryRecallAdapter`.
- Fixing BUG-008 (consolidation) does NOT touch the recall path — low risk.
- Adding embedding_service to the recall path IS a change to the brain's memory retrieval — medium risk, needs careful canary testing.
- Episodes embedding backfill is a DB write operation — needs backup before execution.

### 9.2 Mitigation

- All fixes must be non-breaking to the existing recall path.
- Consolidation fix is additive (new parameter, backward compatible).
- Embedding service wiring is additive (new optional parameter).
- Backfill is a separate job, not part of the hot path.

---

## 10. Summary of Required Fixes

| ID | Severity | Description | Files to Modify |
|----|----------|-------------|-----------------|
| BUG-008 | **CRITICAL** | Consolidation has zero project_id awareness — will crash on NOT NULL | `src/memory/consolidation.py` |
| BUG-003 | HIGH | store_episode_batch loses project_id | `src/memory/write_pipeline.py` |
| EMB-001 | HIGH | Life-kernel recall path has no embedding_service | `src/core/main.py` (or new adapter) |
| EMB-002 | MEDIUM | Episodes with NULL embedding need backfill | New file: `src/memory/embedding_backfill.py` |
| KG-001 | MEDIUM | KG tables (kg_entities/kg_edges) have no ORM models | `src/memory/models.py` |
| SCHED-001 | MEDIUM | Consolidation scheduler commented out — needs activation after BUG-008 fix | `src/core/main.py` |

---

## 11. Evidence Sources

- `src/memory/consolidation.py` — full file read (1127 lines)
- `src/memory/models.py` — full file read (1299 lines)
- `src/memory/read_pipeline.py` — full file read (1198 lines)
- `src/memory/embeddings.py` — full file read (775 lines)
- `src/core/main.py` — consolidation/scheduler/recall sections read
- `docs/setup-evidence/legacy-audit/P3/evidence/p3-post-p19-bug-reclassification.md` — BUG-008 escalation confirmed
- `docs/setup-evidence/legacy-audit/P3/evidence/p3-post-p19-audit-round-2.md` — round 2 audit confirms BUG-008 CRITICAL
- `docs/setup-evidence/legacy-audit/P3/evidence/p3-post-p19-live-rebaseline.md` — live rebaseline confirms project_id NOT NULL
# R01 — P3 Consolidation Project-ID P19 Compliance Audit

**Auditor:** Research Agent
**Date:** 2026-06-27
**Status:** COMPLETE

---

## 1. Verdict

| Check | Verdict |
|-------|---------|
| `consolidate_episodes_to_facts()` signature | ❌ FAIL — No `project_id` parameter |
| `SemanticFacts(...)` construction | ❌ FAIL — `project_id` and `project_scope` never set |
| `_extract_facts_from_episode()` reads `project_id` | ❌ FAIL — Only reads title/summary/tags/classification |
| `daily_consolidation_job()` propagates project context | ❌ FAIL — No `project_id` plumbing |
| `prune_stale_facts()` | ⚠️ PARTIAL — Not project-scoped but safe (read-only) |
| `store_episode()` P19 compliance | ✅ PASS — Accepts `project_id` parameter |
| `store_episode_batch()` P19 compliance | ❌ FAIL — Does NOT pass `project_id` (BUG-003) |

## 2. BUG-008: Exact Lines

### 2.1 `consolidate_episodes_to_facts()` — No project awareness

**File:** `src/memory/consolidation.py`

- **Lines 275-282**: Function signature has NO `project_id` kwarg.
- **Lines 327-328**: Query selects ALL episodes across ALL projects with no project filter.
- **Lines 387-397**: `SemanticFacts(...)` constructor — missing `project_id` and `project_scope`.

```python
# CURRENT (line 387-397):
fact = SemanticFacts(
    subject=str(_subj),
    predicate=str(_pred),
    object_val=str(_obj),
    fact_type=fact_type,
    confidence=confidence,
    source="consolidation",
    source_episode=source_episode_id,
    classification=highest_cls,
    tags=fact_tags,
    # MISSING: project_id, project_scope
)
```

### 2.2 `_extract_facts_from_episode()` — Does not extract project info

**Lines 559-630**: Uses `getattr(ep, ...)` for title, summary, tags, classification — never extracts `project_id` or `project_scope`.

### 2.3 `daily_consolidation_job()` — No project context

**Lines 822-823**: Calls `consolidate_episodes_to_facts(session)` with no project context.

## 3. SemanticFacts ORM Model — Missing project_id

**File:** `src/memory/models.py`

The `SemanticFacts` class (lines 218-273) does NOT declare `project_id` or `project_scope` columns. These columns exist in production DB (P19 migration) but SQLAlchemy silently ignores attribute assignments to undeclared columns.

**Fix**: Add to `SemanticFacts` class:
```python
project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    UUID(as_uuid=True), nullable=True,
    comment="Project namespace UUID. NULL = global-scope."
)
project_scope: Mapped[str] = mapped_column(
    Text, nullable=False, server_default=text("'project'"),
    comment="P19 scope: 'project' or 'global'"
)
```

## 4. Default Project UUID

**File:** `src/projects/registry.py` line 161
```python
DEFAULT_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
```

## 5. BUG-003: store_episode_batch

**File:** `src/memory/write_pipeline.py` lines 245-277

`store_episode_batch()` accepts `episodes` list but does NOT pass `project_id` or `project_scope` to `store_episode()`. Every batch-write caller will produce `IntegrityError` on P19-002 NOT NULL.

## 6. P19-002 NOT NULL Migration

**File:** `alembic/versions/p19_002_project_id_not_null.py` lines 32-43

`ALTER COLUMN project_id SET NOT NULL` on `memory.semantic_facts`. Pre-existing rows backfilled to default project UUID. Any new row without `project_id` → crash.

## 7. Fix Summary

1. **models.py**: Add `project_id` + `project_scope` to `SemanticFacts` ORM class
2. **consolidation.py**: Extract `project_id`/`project_scope` from source episodes via `getattr`
3. **consolidation.py**: Populate both fields on `SemanticFacts(...)` constructor
4. **consolidation.py**: Fallback to `ProjectRegistry.DEFAULT_PROJECT_ID` for legacy NULL episodes
5. **write_pipeline.py**: Add `project_id`/`project_scope` parameter forwarding to `store_episode_batch`
6. **tests**: Update consolidation tests to verify project_id propagation
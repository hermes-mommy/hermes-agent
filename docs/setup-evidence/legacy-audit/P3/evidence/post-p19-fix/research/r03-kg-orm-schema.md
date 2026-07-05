# R03 — KG ORM Models vs Live Schema Compatibility Audit

**Auditor:** Research Agent
**Date:** 2026-06-27
**Status:** COMPLETE

---

## 1. Verdict

| Check | Verdict |
|-------|---------|
| ORM models for `kg_entities` / `kg_edges` | ❌ NONE — All raw SQL |
| `KnowledgeGraph` ORM class in models.py | ❌ STALE — Maps to deprecated `memory.knowledge_graph` (renamed to `_legacy_knowledge_graph`) |
| Alembic migration for `kg_entities` / `kg_edges` | ❌ NONE — DDL in `migrations/p16_001_kg_schema.sql` only, untracked by Alembic |
| P19 adds project_id to KG tables | ❌ SKIPPED — P19-001 line 87 explicitly excludes kg_entities/kg_edges |
| KG ingestion propagates project_id | ❌ NO — `_ENTITY_UPSERT_SQL` and `_EDGE_INSERT_SQL` do not bind `project_id` |
| KG queries reference project_id column | ⚠️ PARTIAL — `query/engine.py` and `query/ppr.py` reference `e.project_id` but column doesn't exist in DDL |

## 2. The Stale `KnowledgeGraph` ORM Class

**File:** `src/memory/models.py` lines 401-416

```python
class KnowledgeGraph(Base, ClassificationMetaMixin):
    __tablename__ = "knowledge_graph"  # ← LEGACY table name
    __table_args__ = {"schema": "memory"}
    from_entity, relationship, to_entity, weight, context
```

This maps to the flat-triple table that `migrations/p16_001_kg_schema.sql` renamed to `_legacy_knowledge_graph` and revoked write privileges on. The ORM model is effectively dead.

## 3. Raw SQL References (30+ sites)

The KG module uses hand-written SQL strings throughout. Key files:

- `src/knowledge_graph/ingestion/pipeline.py` — `_ENTITY_UPSERT_SQL`, `_EDGE_INSERT_SQL`
- `src/knowledge_graph/query/engine.py` — recursive graph_walk CTE with `project_id` filter
- `src/knowledge_graph/query/ppr.py` — adjacency load with `project_id` filter
- `src/knowledge_graph/consent/manager.py` — UPDATE/REVOKE on `kg_entities`/`kg_edges`
- `src/knowledge_graph/resolution/canonical.py` — SELECT enumerating 25 columns
- `src/knowledge_graph/resolution/resolver.py` — merge/repoint/alias SQL

## 4. P19 Gap

`alembic/versions/p19_001_project_namespaces.py` line 87:
> memory.kg_entities / kg_edges / kg_consent_audit do not exist in current schema -- they will be added in a future P19 wave if needed.

P19 only adds `project_id` to the legacy `memory.knowledge_graph` table. The real KG tables are untouched.

## 5. project_id Query Mismatch

`query/engine.py` line 459 references `e.project_id` on `kg_edges` alias — but DDL has no such column. These queries would fail if the schema migrates to add project_id without also backfilling the column.

## 6. Recommended Fix (Option A — Add ORM Models)

1. Add `KGEntity` and `KGEdge` ORM classes to `src/memory/models.py`
2. Run Alembic migration to add `project_id` + `project_scope` to both tables
3. Backfill existing rows with default project UUID
4. Update ingestion pipeline to propagate `project_id` from `SemanticFact`
5. Remove or rename the legacy `KnowledgeGraph` ORM class
6. Add CI test that compiles raw SQL against live schema

## 7. Recommended Fix (Option B — Compatible Adapter)

1. Keep raw SQL but add adapter module `src/knowledge_graph/adapter.py`
2. Add Alembic migration for kg_entities/kg_edges
3. Drop legacy `KnowledgeGraph` ORM class
4. Update P19-001 to handle real KG tables
5. Audit all query sites for project_id correctness

## 8. Minimum Fix (Option C)

1. Add `project_id` + `project_scope` columns to `SemanticFacts` ORM (needed for BUG-008)
2. Add docstring banner noting KG is raw-SQL-only
3. Add CI test that SELECT FROM kg_entities/kg_edges compiles
4. File TODO for full ORM migration
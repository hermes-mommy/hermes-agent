# P19-004 — Pre-Existing KG Module/DB Drift (Deferred to P16)

**Date:** 2026-06-25
**Discovered by:** P19-004 real-DB isolation testing (parent verification)
**Operator decision:** Fix memory test in P19 scope; defer KG table-name reconciliation to P16 (Knowledge Graph). P19-012 prod deploy uses stamp + targeted ALTER (not full alembic upgrade).

## 1. The Drift

The `src/knowledge_graph/` module queries tables `memory.kg_entities`, `memory.kg_edges`, `memory.kg_consent_audit`, `memory.kg_episodes` — see:
- `src/knowledge_graph/consent/manager.py:56` — `KG_ENTITIES_TABLE = f"{KG_SCHEMA}.kg_entities"`
- `src/knowledge_graph/consent/manager.py:57` — `KG_EDGES_TABLE = f"{KG_SCHEMA}.kg_edges"`
- `src/knowledge_graph/consent/audit.py:296,312` — `FROM memory.kg_entities e`, `FROM memory.kg_edges e`
- `src/knowledge_graph/query/engine.py:475` — `FROM memory.kg_edges e`
- `src/knowledge_graph/ingestion/*` — references throughout

**But the actual migrated DB schema has a SINGLE table `memory.knowledge_graph`** (created in `alembic/versions/e401bb5fd274_initial_schema_47_tables.py:399`). **No migration creates `kg_entities` or `kg_edges`.** Verified via `grep -rln "kg_entities" alembic/versions/` → only `p19_001_project_namespaces.py` (which adds columns to non-existent tables — silent no-op via `IF NOT EXISTS`).

## 2. Production state

Production `guinevere_core` has **no `memory` or `knowledge_graph` schema at all** (0 rows in `information_schema.tables` for those schemas) and **no `ops.alembic_version` table** — it was provisioned via raw SQL, not the alembic chain. So the KG module has never run against a real migrated DB in production either. This is a pre-existing infra discrepancy, NOT caused by P19.

## 3. P19-004's position

P19-004's mandate was to thread `project_id` through the **existing** KG recall path. That work is **correct and verified**:
- `src/knowledge_graph/query/engine.py` — `KGQueryEngine.search_entities(..., project_id=None)` adds the `WHERE project_id = :pid OR project_scope = 'global'` filter (DATA-04).
- `src/knowledge_graph/query/ppr.py` — `_load_adjacency(..., project_id=None)` scopes the PPR walk (line 380: `OR project_scope = 'global'`).
- `src/knowledge_graph/query/context.py` — `RecallContextAssembler.assemble(..., project_id=None)`.
- `src/knowledge_graph/query/rrf_fusion.py` — `project_id` threaded for context.
- The real `memory.knowledge_graph` table now carries `project_id` + `project_scope` (P19-003 migration applied them — verified `SELECT column_name ... = 'knowledge_graph'` returns both).

So when P16 reconciles the KG table names (or the KG module is rewritten to use `memory.knowledge_graph`), the `project_id` filtering P19-004 added will work without further changes — the filter logic is table-name-agnostic.

## 4. Why deferred to P16

- P16 (Knowledge Graph) is `⏳ TBD` (unstarted) per PROGRESS.md. The KG module's table-name reconciliation is fundamentally a P16 schema/design decision: rename `memory.knowledge_graph` → `kg_entities`/`kg_edges` (split), or rewrite the KG module to use the single `knowledge_graph` table. Either is a KG-module-wide change touching the consent/audit boundary — P16's scope, not P19's.
- P19's contract is the `project_id` *dimension* (orthogonal namespace), not fixing the KG module's pre-existing table-name drift.
- The KG-isolation *test* (`tests/projects/test_kg_isolation.py`) is marked `pytest.skip` with this doc referenced, so it does not conflate with the memory-isolation proof (which passes, in P19 scope).

## 5. Evidence

- `tests/projects/test_kg_isolation.py` — `pytestmark = pytest.mark.skip(reason="PRE-EXISTING KG module/DB drift (deferred to P16)...")`. 4 tests skip cleanly.
- `tests/projects/test_memory_isolation.py` — 7 tests PASS against real Postgres (episodes isolation + DATA-03 DNR scoping).
- `tests/hermes/test_memory_bridge.py` — 17 tests PASS (P20 regression: `_memory_bridge.py` project_id threading did not break legacy behavior).

## 6. P16 handoff note

When P16 begins, it must:
1. Decide the canonical KG table shape (`kg_entities`+`kg_edges` split vs single `knowledge_graph`).
2. Add/reconcile the migration so the KG module's table names match the schema.
3. Un-skip `tests/projects/test_kg_isolation.py` (remove the `pytestmark` skip) and confirm DATA-04 entity isolation passes — the `project_id` filter P19-004 added is already in place.
4. Reconcile production `guinevere_core` (which has no `memory` schema) onto a real KG schema.

## 7. Footer

| Field | Value |
|---|---|
| Drift type | Pre-existing code/DB table-name mismatch (KG module) |
| Discovered by | P19-004 real-DB isolation testing |
| Caused by P19? | No |
| P19-004 project_id threading correct? | Yes (source-verified) |
| Resolution owner | P16 (Knowledge Graph) |
| Operator decision date | 2026-06-25 |

# P19 Research: Memory Namespace Partitioning

**Status:** ✅ COMPLETE
**Date:** 2026-06-25
**Author:** Guinevere (parent-authored from scout reports + direct reads)
**Scope:** How to partition Guinevere's memory + knowledge graph across multiple projects without cross-project memory leak.

---

## 1. Executive Summary

Guinevere's memory is **global today** — one pool of episodic/semantic/procedural memories and one knowledge graph, all in the `memory.*` PostgreSQL schema with no `project_id`. P19 must partition memory per project so recall in project A never surfaces memories written under project B, while keeping genuinely shared memories (persona facts, ADR knowledge, safety policies) accessible across all projects.

**Recommended design:** Add a nullable `project_id` column to every memory/KG table, default `default`, plus a `project_scope` discriminator (`global` vs `project`), and enforce isolation via application-layer WHERE clauses + a query-builder wrapper + unit tests asserting zero leak. Row-Level Security (RLS) is a defense-in-depth option, not the primary mechanism.

---

## 2. Current Memory Schema

### 2.1 Tables (in `memory.*` schema)
- `memory.episodes` — episodic memories. Has FSRS columns (tier, fsrs_state, last_reviewed_at, next_reviewed_at, retrievability, stability, difficulty), `search_vector` TSVECTOR, `do_not_recall` boolean (`src/memory/models.py`, migrations `65f863220922`, `3d41deeca703`).
- `memory.semantic_memories` — semantic facts.
- `memory.procedural_skills` — procedural skills, has `embedding vector(1536)` + ivfflat index (migration `p5_015_add_skill_embedding`).
- `memory.session_summaries` — session summaries (migration `p5_024`).
- `memory.kg_entities`, `memory.kg_edges`, `memory.kg_consent_audit` — knowledge graph (P16, migration `p16_001_kg_schema.sql`).

### 2.2 Project_id columns today
**None.** No memory or KG table has a `project_id` column. The `financial.transactions` table (`src/memory/models.py:605-625`) has an optional `project_id` but the finance plugin does not use it.

### 2.3 Principal hardcode
`src/life_kernel/p18_adapter.py:81` hardcodes `principal="guinevere_core"` for memory recall. `src/hermes/_memory_bridge.py:282` records only `channel: "guinevere-chat"` metadata, no project_id.

---

## 3. Current Memory Recall Flow

1. `hermes_conversational.py` calls `HermesMemoryBridge.recall_for_context(query, safe_mode, principal, limit, token_budget, kg_enabled)` (`_memory_bridge.py:93`).
2. `HermesMemoryBridge` calls `p18_adapter.recall(context)` and `p16_adapter.recall(context)`.
3. Adapters call `recall_memories()` (P18) and the KG query path `KGQueryEngine.search_entities` + `RecallContextAssembler.assemble` (P16, in `src/knowledge_graph/query/{engine,context}.py` with fusion in `rrf_fusion.py` + walk in `ppr.py`).
4. Queries use pgvector embedding similarity + metadata filters (`do_not_recall = false`, classification, etc.).
5. Results returned as `RecalledMemories` and `RecalledConcepts`.

**Leak vector:** A recall query today returns memories from ALL projects because there is no `project_id` filter.

---

## 4. Current Memory Write Path

1. `hermes_conversational.py` → `HermesMemoryBridge.store_conversation(user_message, assistant_response, user_id_hash, safe_mode)` (`_memory_bridge.py:216`).
2. `store_conversation` inserts an episode with metadata (`channel`, timestamps, etc.).
3. MEM-001..008 validation gates run (write-validation, safe-state check, secret-scanner, instruction-pattern quarantine) — documented in P21 plan §Global Constraints.
4. Embedding generated via `EmbeddingService`.

**Leak vector:** Stored episodes have no `project_id`, so they become part of the global pool.

---

## 5. Project-Partition Design Options

### 5.1 Option A: `project_id` column on every table (RECOMMENDED)
- Add nullable `project_id UUID` column to every memory/KG table.
- Add `project_scope TEXT NOT NULL DEFAULT 'project'` discriminator (`global` | `project`).
- Composite index `(project_id, created_at)` and `(project_id, embedding)` for vector queries.
- Application-layer WHERE clauses enforced by a `ProjectScopedMemoryStore` wrapper.
- Backfill existing rows: `project_id = <default-uuid>, project_scope = 'project'`.
- Pros: Simple, query-builder enforceable, minimal schema change.
- Cons: Isolation depends on application discipline (mitigated by wrapper + tests).

### 5.2 Option B: PostgreSQL schema per project (`memory_work.*`, `memory_personal.*`)
- One schema per project.
- Pros: DB-enforced isolation.
- Cons: DDL explosion (N schemas × M tables), migration complexity, dynamic schema names in queries.

### 5.3 Option C: Separate database per project
- Pros: Total isolation.
- Cons: Connection-pool explosion, cross-project queries impossible, operational overhead.

### 5.4 Option D: Namespace prefix on content (e.g., `[work] ...`)
- Hacky, leaky, not enforceable. **REJECTED.**

### 5.5 Recommendation
**Option A + defense-in-depth RLS (§7).** Option A is the only one that balances simplicity, queryability, and isolation for a single-user system with a bounded number of projects. RLS adds a hard DB-layer backstop.

---

## 6. Cross-Project Leak Vectors

| Vector | How leak happens | Prevention |
|---|---|---|
| Recall query | No `project_id` filter → global results | `WHERE project_id = ? OR project_scope = 'global'` enforced by wrapper |
| Embedding similarity | pgvector returns nearest regardless of project | Add `project_id` to vector query filter (pgvector supports pre-filter via partial index or composite) |
| Hardcoded principal | `principal="guinevere_core"` returns all | Pass `project_id` or `principal="guinevere:{project_id}"` to recall |
| Dashboard summary | Life-mind state rendered without project label | Per-project `LifeMindState` with `project_id` |
| Proactive voice brief (P21) | Voice brief recalls across projects | Voice brief uses current project's recall |
| KG entity resolution | Entity resolution merges entities across projects | Scope entity resolution by `project_id` (entity name can repeat across projects) |
| Session history | `hermes:session:{user_id}` is global | `hermes:session:{user_id}:{project_id}` |
| Background cognition | 6 loops write observations to global graph | Per-project `thread_id` + `project_id` in observation payload |

---

## 7. Leak Prevention Mechanisms

### 7.1 Application-layer wrapper (PRIMARY)
Create `src/projects/memory_store.py` with `ProjectScopedMemoryStore`:
- All recall/store goes through this class.
- Every query includes `WHERE project_id = :project_id OR project_scope = 'global'`.
- Unit tests assert: write to project A, recall from project B (with no global scope) → empty.

### 7.2 Row-Level Security (DEFENSE-IN-DEPTH)
```sql
ALTER TABLE memory.episodes ENABLE ROW LEVEL SECURITY;
CREATE POLICY project_isolation ON memory.episodes
  USING (project_scope = 'global' OR project_id = current_setting('app.current_project')::uuid);
```
- Requires `SET app.current_project = <uuid>` per DB connection/session.
- Global-scope rows are always visible (persona facts).
- Pros: Hard-enforced at DB layer; application bugs cannot leak.
- Cons: Requires connection-level state; complicates cross-project admin queries.

**Decision:** RLS is OPTIONAL for P19 MVP (enable behind a feature flag `project:rls_enabled`). The wrapper + tests are the primary mechanism. RLS can be enabled in a later hardening wave once the wrapper is proven.

### 7.3 Query-builder enforcement
- Replace raw SQL recall queries with a typed query builder that requires `project_id`.
- Static analysis / grep CI check: no `SELECT ... FROM memory.episodes` without `project_id` in WHERE.

### 7.4 Test patterns
- `test_memory_isolation_global_only`: global memories visible from any project.
- `test_memory_isolation_project_scoped`: project A memory NOT visible from project B recall.
- `test_memory_isolation_dnr_per_project`: DNR in project A does not affect project B.
- `test_kg_entity_isolation`: entity "user" in project A is distinct from "user" in project B.

---

## 8. Shared vs Project-Scoped Memory

### 8.1 Global-scope memory (shared across all projects)
- Persona memories (Faiz's preferences, relationship milestones, mood history).
- ADR knowledge, safety policies, governance docs.
- Operator profile (Faiz's identity, timezone, language).
- Cross-cutting procedural skills (how to run the agent loop, how to deploy).

These get `project_scope = 'global'` and are visible from every project.

### 8.2 Project-scoped memory
- Project-specific episodes (conversations in project X).
- Project-specific KG entities (project X's calendar events, tasks, notes).
- Project-specific decision context.

These get `project_scope = 'project'` and `project_id = <project>`.

### 8.3 Classification rule
At write time, the memory writer classifies each episode as `global` or `project` based on content + source. Default: `project` (fail-safe toward isolation). Explicit `global` only for persona/operator/ADR content.

---

## 9. Principal Model

### 9.1 Current: `principal="guinevere_core"` (hardcoded)
### 9.2 Proposed: dual-dimension
- Retain `principal="guinevere_core"` as the persona identity (shared).
- Add `project_id` as a separate column/dimension.
- Recall filters: `WHERE (project_scope = 'global' OR project_id = :project_id)`.
- This avoids renaming `principal` everywhere while adding project as an orthogonal filter.

### 9.3 Alternative: `principal="guinevere:{project_id}"`
- Encodes project into principal string.
- Pros: Single filter dimension.
- Cons: Breaks the "shared persona" model (persona is one, projects are many); harder to query global memories.
- **REJECTED** in favor of dual-dimension.

---

## 10. Backfill Strategy

1. Migration `p19_001` adds nullable `project_id UUID` + `project_scope TEXT DEFAULT 'project'` to all memory/KG tables.
2. Seed `projects.project_registry` with `default` project (id = a fixed UUID).
3. Backfill: `UPDATE memory.episodes SET project_id = <default-uuid>, project_scope = 'project' WHERE project_id IS NULL;` (batched).
4. Repeat for semantic_memories, procedural_skills, session_summaries, kg_entities, kg_edges.
5. Add composite indexes.
6. Make `project_id` NOT NULL (with DEFAULT) in a follow-up migration `p19_002`.
7. Idempotent: `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head` must work.

---

## 11. Do-Not-Recall Interaction

- `do_not_recall` is a per-row boolean.
- If a memory is DNR in project A, it is DNR **for project A's recall**.
- If the same conceptual memory exists in project B (separate row), project B's DNR is independent.
- For global-scope DNR (e.g., a sensitive persona memory): DNR applies to all projects (global recall blocked).
- `consent.memory.do_not_recall_override` scope: stays global (persona-level), per ConsentRevocationPolicy §9.

---

## 12. Consent Taxonomy Extension

- Current: `consent.memory.core` (global).
- P19 question: must it split into `consent.memory.{project_id}.core`?
- **Answer:** No. Consent for memory storage stays global (Faiz consents to Guinevere remembering him). What changes is the **query filter** (project-scoped recall), not consent.
- Exception: If a project has a specific data-class (e.g., project "work" handles client-confidential data), a project-scoped consent scope `consent.memory.project.work` can be added to gate that project's memory specifically. This is optional and project-specific, not a global split.

---

## 13. Hermes Memory Bridge Changes

`src/hermes/_memory_bridge.py`:
- `recall_for_context(query, safe_mode, principal, limit, token_budget, kg_enabled, project_id=None)` — add `project_id`.
- `store_conversation(user_message, assistant_response, user_id_hash, safe_mode, project_id=None)` — add `project_id`.
- When `project_id` is None, default to `default` project (backward-compatible).
- Episodes stored with `project_id` in metadata + column.

---

## 14. Embedding Model Impact

- Embeddings are content-derived (OpenAI `text-embedding-3-small`, 1536 dims).
- `project_id` is a metadata filter, NOT part of the embedding.
- No re-training needed.
- pgvector query: `ORDER BY embedding <=> :query_embedding LIMIT :k` with pre-filter on `project_id` (partial index or composite filter).
- Performance: composite index `(project_id, embedding)` or a partial ivfflat index per project (for large datasets).

---

## 15. Performance Impact

- Recall queries add one WHERE clause (`project_id = ?`) — negligible cost with composite index.
- Vector similarity: pgvector supports filtered ANN. For single-user scale (thousands of episodes), brute-force with filter is fine.
- Write path: one extra column write — negligible.
- Index size: composite indexes add modest storage.

---

## 16. Knowledge Graph Specifics (P16, ADR-050)

- `memory.kg_entities`: add `project_id`.
- `memory.kg_edges`: add `project_id`.
- Entity resolution: currently uses RCTE for entity clustering (ADR-050). P19 must scope entity resolution by `project_id` so an entity "Alice" in project "work" is distinct from "Alice" in project "personal".
- `memory.kg_consent_audit`: add `project_id` to consent audit rows.
- KG recall (`RecallContextAssembler.assemble()` in `src/knowledge_graph/query/context.py` + `KGQueryEngine.search_entities` in `query/engine.py`; fusion `query/rrf_fusion.py`; walk `query/ppr.py`): add `project_id` filter to all.

---

## 17. Hard Rejection Checks

1. **Namespace does not flow to memory/KG:** ✅ MITIGATED — `project_id` column on every memory/KG table + wrapper.
2. **Shared persona causes cross-project memory leak:** ✅ MITIGATED — global-scope memories are explicit; project-scoped default; wrapper enforces filter.
3. **Recall can surface other project's memories:** ✅ MITIGATED — `WHERE project_id = ? OR project_scope = 'global'` enforced + tests.

---

## 18. Conclusion

P19 partitions memory via Option A (`project_id` column + `project_scope` discriminator + application-layer wrapper + optional RLS). Existing data backfills to `default` project. Global memories (persona/ADR/safety) get `project_scope = 'global'` and remain shared. Project memories get `project_scope = 'project'` and are isolated by the wrapper's WHERE clause. Tests assert zero leak. RLS is an optional defense-in-depth backstop behind a feature flag.

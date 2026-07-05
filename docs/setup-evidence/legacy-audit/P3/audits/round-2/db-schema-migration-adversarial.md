# Adversarial DB Schema & Migration Drift Hunt (Wave-2)

**Date:** 2026-06-25
**Agent:** Wave-2 Adversarial Audit (read-only)
**Scope:** Hunt for schema/migration drift that wave-1 may have missed
**Read-only affirmation:** YES. No migrations run. No DB accessed. No secrets printed.

---

## (a) Migration Chain Linearity / Heads

The chain is **forked**, with one merge point. Here is the full trace:

```
None
  -> 2bed93fd1dd0 (baseline_init)
    -> e401bb5fd274 (initial_schema_47_tables)
      -> 65f863220922 (add_search_vector_do_not_recall)
        |                                          |
        +---> p5_extend_loops                       +---> 3d41deeca703 (p18_add_memory_tiers_fsrs)
              -> p5_add_loop_indexes                         |
                   -> p6_gamification_schema                  |
                      -> 7239fd4b3b5a (add_reviewer_action)   |
                           |                                  |
                           +------- f47a9c2e8b1d (MERGE) -----+
                                      (p5_012_extend_loop_instances)
                                        -> p5_015_add_skill_embedding
                                          -> p5_024 (add_session_summaries)
                                            -> p20_001_life_kernel_schema
                                              -> p19_001_project_namespaces
                                                -> p19_002_project_id_not_null  <-- SINGLE HEAD
```

**Key findings:**

1. **[MEDIUM]** The chain forks at `65f863220922` and merges at `f47a9c2e8b1d` via a tuple `down_revision = ("7239fd4b3b5a", "3d41deeca703")`. This is valid Alembic multi-head merge syntax, but it means the chain is NOT purely linear. Alembic `heads` command should report a single head (`p19_002_project_id_not_null`) after the merge.

2. **[COSMETIC]** `p5_015_add_skill_embedding` docstring says `Revises: 3d41deeca703` (line 5) but the code says `down_revision = "f47a9c2e8b1d"` (line 18). The code is authoritative; the docstring is stale.

3. **[LOW]** `alembic.ini` line 9 has a masked password `****` — handled correctly by env.py line 34 which substitutes at runtime. No secret leak.

4. **[MEDIUM]** The `alembic.ini` version_table_schema is `ops` (line 13), and `env.py` also sets `version_table_schema="ops"` (lines 54, 68). Consistent, but the gamification schema (p6) creates a `gamification` schema that is NOT listed in `env.py`'s `GUINEVERE_SCHEMAS` frozenset (lines 19-24). This means `alembic revision --autogenerate` will **ignore gamification tables entirely**.

---

## (b) ORM vs Migration DDL Drift

### FINDING 1: [CRITICAL] session_summaries missing 11 ClassificationMetaMixin columns

The ORM model `SessionSummary` (`src/memory/models.py:190`) inherits from `ClassificationMetaMixin`, which injects 12 columns (classification, purpose, source, retention_class, retention_until, access_policy, encryption_profile, deletion_state, key_id, key_version, created_at, updated_at). The model overrides `created_at`.

But the p5_024 migration DDL (`alembic/versions/p5_024_add_session_summaries.py:23-63`) creates session_summaries with only **7 columns**: id, session_id, summary_text, original_message_count, compacted_to_count, tokens_saved, created_at.

**Missing from DDL** (11 columns): classification (NOT NULL), purpose, source, retention_class (NOT NULL), retention_until, access_policy (NOT NULL), encryption_profile (NOT NULL), deletion_state (NOT NULL), key_id, key_version, updated_at (NOT NULL).

**Impact**: Any ORM INSERT to session_summaries will fail with PostgreSQL error `column "classification" of relation "session_summaries" does not exist`. The table is unusable through the ORM until a remediation migration adds these missing columns.

No subsequent migration (p19_001, p20_001, etc.) adds these missing columns.

### FINDING 2: [HIGH] 4 memory ORM models missing P19 project_id / project_scope columns

Migration p19_001 (`alembic/versions/p19_001_project_namespaces.py`) adds `project_id UUID` and/or `project_scope TEXT` to 5 memory tables. But only the `Episodes` ORM model (`src/memory/models.py:180-187`) declares these columns. The following 4 models do NOT:

| Table | project_id in DDL | project_scope in DDL | In ORM? |
|---|---|---|---|
| semantic_facts | p19_001:71 | p19_001:102 | NO |
| procedural_skills | p19_001:72 | p19_001:103 | NO |
| session_summaries | p19_001:73 | (not added) | NO |
| knowledge_graph | p19_001:74 | p19_001:104 | NO |

**Impact**: ORM queries on these 4 tables will not read, filter, or write project_id/project_scope. Data isolation between projects (P19's core purpose) is broken for these tables when accessed through the ORM. Alembic autogenerate would also want to DROP these columns since they are invisible to the ORM metadata.

### FINDING 3: [MEDIUM] procedural_skills missing embedding column in ORM

Migration p5_015 (`alembic/versions/p5_015_add_skill_embedding.py:24`) adds `embedding vector(1536)` to memory.procedural_skills. The ORM model `ProceduralSkills` (`src/memory/models.py:366-388`) has NO embedding column.

**Impact**: Vector similarity search on procedural skills is impossible through the ORM. The column exists in the DB but is invisible to SQLAlchemy.

### FINDING 4: [MEDIUM] loop_instances has 5 orphan DDL columns not in ORM

Migration p5_012 (`alembic/versions/p5_012_extend_loop_instances.py:26-32`) adds 7 columns to projects.loop_instances. The ORM model `LoopInstances` (`src/memory/models.py:719-758`) includes `status` and `retry_count` but is missing 5 columns:

- `checkpoint_data` (JSONB)
- `error_message` (TEXT)
- `phase` (SMALLINT)
- `phase_artifacts` (JSONB)
- `parent_loop_id` (VARCHAR(12))

**Impact**: Checkpoint/recovery data stored via raw SQL is invisible to ORM operations.

### FINDING 5: [MEDIUM] loop_instances.status type mismatch: VARCHAR(20) vs TEXT

DDL (p5_012:26) creates `status VARCHAR(20) DEFAULT 'pending'`. ORM (`src/memory/models.py:738`) declares `status: Mapped[str] = mapped_column(Text, nullable=False)`.

PostgreSQL `TEXT` has no length limit while `VARCHAR(20)` enforces 20 characters. ORM inserts with status strings longer than 20 characters will succeed at the ORM layer but fail at the DB constraint.

### FINDING 6: [LOW] episodes_started_at_idx defined in ORM but never created in DDL

The ORM defines `Index("episodes_started_at_idx", text("started_at DESC"))` at `src/memory/models.py:95`. No migration creates this index. TimescaleDB creates an implicit btree on the partitioning column `started_at` (ASC), but the explicit DESC index is missing.

---

## (c) HNSW Parameters

Both HNSW indexes specify `m = 16, ef_construction = 128`:

- Episodes: `alembic/versions/e401bb5fd274_initial_schema_47_tables.py:325` and `:1059` (duplicate, IF NOT EXISTS, idempotent)
- Semantic facts: `alembic/versions/e401bb5fd274_initial_schema_47_tables.py:480` and `:1060` (duplicate, IF NOT EXISTS, idempotent)

ORM models match: `src/memory/models.py:97-102` (episodes) and `src/memory/models.py:212-217` (semantic_facts) both specify `postgresql_with={"m": 16, "ef_construction": 128}`.

**pgvector extension**: NO migration contains `CREATE EXTENSION IF NOT EXISTS vector`. The extension must be pre-installed by DB admin or Docker init scripts. This is a deployment prerequisite, not tracked by Alembic.

**[LOW]** The procedural_skills embedding index (p5_015:27-32) uses **ivfflat** (`WITH (lists = 100)`) instead of HNSW. This is inconsistent with the project's standard (pgvector_config table at `src/memory/models.py:1237` declares `default_index_type = 'hnsw'`). ivfflat also requires a `SET ivfflat.probes` parameter at query time for recall tuning, which HNSW does not.

---

## (d) Vector Dimension

All vector columns use `vector(1536)`:

- `e401bb5fd274:301` — episodes.embedding: `VECTOR(dim=1536)`
- `e401bb5fd274:462` — semantic_facts.embedding: `VECTOR(dim=1536)`
- `p5_015:24` — procedural_skills.embedding: `vector(1536)` (raw SQL)
- ORM models: `Vector(1536)` at lines 132, 255

**No vector(384) MiniLM leftovers found anywhere.** Clean.

---

## (e) p19_001 Idempotency

Every DDL statement in p19_001 uses idempotent guards:

- `CREATE TABLE IF NOT EXISTS` (line 41)
- `INSERT ... ON CONFLICT (slug) DO NOTHING` (line 60-63)
- `ADD COLUMN IF NOT EXISTS` (lines 70-96)
- `CREATE INDEX IF NOT EXISTS` (lines 134-161)
- `UPDATE ... WHERE project_id IS NULL` (lines 110-127) — effectively idempotent on re-run
- `DROP INDEX IF EXISTS` + `CREATE UNIQUE INDEX IF NOT EXISTS` (lines 174-178) inside DO $$ block

**No non-idempotent operations found.** Safe to re-run.

---

## (f) p19_002 STUB — Deferred NOT NULL Isolation Hole

`alembic/versions/p19_002_project_id_not_null.py` is a **complete no-op** (line 34: `pass`). The upgrade function applies no constraints.

The stub comment (line 29-33) says NOT NULL will be applied in "P19-011 after backfill verification." However, **no p19_011 migration exists** in `alembic/versions/`.

**Consequences:**

1. `project_id` columns on all P19-scoped tables remain nullable indefinitely.
2. The ORM models declare `project_id: Mapped[Optional[uuid.UUID]]` with `nullable=True` — this is consistent with the current DDL state.
3. New rows inserted without specifying project_id will have `project_id = NULL`. The ORM does not set a default.
4. The backfill in p19_001 (lines 110-127) only covers existing rows.

**[HIGH]** The deferred NOT NULL means the P19 project isolation guarantee is incomplete. Until P19-011 is written and applied, there is no DB-level enforcement that new rows must belong to a project. Application code must handle this responsibility, which is fragile.

---

## (g) Table Count

**src/memory/models.py docstring** claims "47 tables across 12 schemas" (line 1).

Actual count in `src/memory/models.py`:

| Schema | Tables | Comment says |
|---|---|---|
| memory | 9 (episodes, session_summaries, semantic_facts, faiz_profile, emotional_events, inner_journal, faiz_predictions, procedural_skills, knowledge_graph) | "8 tables" (stale) |
| persona | 5 | 5 |
| surveillance | 4 | 4 |
| financial | 4 | 4 |
| projects | 4 | 4 |
| social | 3 | 3 |
| agents | 3 | 3 |
| consent | 3 | 3 |
| security | 3 | 3 |
| audit | 3 | 3 |
| ops | 4 | 4 |
| extensions | 3 | 3 |
| **Total** | **47** | **47** |

The comment on line 89 says "8 tables" for memory but there are 9 (SessionSummary was added by p5_024 but the comment was not updated). The total is 47, matching the claim.

**Additional tables NOT in src/memory/models.py:**

| Source | Schema | Tables | Count |
|---|---|---|---|
| `src/life_kernel/models.py` | life_kernel | life_mind_state, heartbeat_record, domain_mind_state | 3 |
| `src/gamification/models.py` | gamification | level_thresholds, skill_xp, agent_xp, xp_events, level_ups, xp_multipliers | 6 |
| p19_001 DDL (no ORM) | projects | project_registry | 1 |

**Grand total: 57 tables across 14 schemas.**

**[MEDIUM]** The `GUINEVERE_SCHEMAS` frozenset in `env.py:19-24` lists 13 schemas but **omits `gamification`**. This means `alembic revision --autogenerate` will never detect changes to the 6 gamification tables. If the gamification ORM models are modified, no migration will be produced automatically.

**[LOW]** `projects.project_registry` (created in p19_001:40-54) has no corresponding ORM model in any `models.py` file. It can only be accessed via raw SQL.

---

## Additional Findings

### FINDING 7: [MEDIUM] surveillance.events hypertable chunk interval conflict

In `e401bb5fd274`, the surveillance.events hypertable is created **twice** with different chunk intervals:

- Line 973: `INTERVAL '1 day'` (inside main table creation block)
- Line 1058: `INTERVAL '7 days'` (in P3-002 patch block)

Since `if_not_exists => TRUE` is used, the second call is a no-op. The **actual** chunk interval is **1 day**, not the intended 7 days. This increases chunk count by 7x and may affect TimescaleDB compression and retention policy effectiveness.

### FINDING 8: [MEDIUM] CommunicationLog FK: ondelete='SET NULL' with nullable=False

`src/memory/models.py:851-855` defines:
```python
contact_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("social.social_map.id", ondelete="SET NULL"),
    nullable=False,
)
```

The `ondelete='SET NULL'` action will attempt to set `contact_id` to NULL when the referenced `social_map` row is deleted. But `nullable=False` prevents this. PostgreSQL will raise a foreign key violation error at DELETE time. The ORM and DDL are consistent (`e401bb5fd274:943`), so the bug is in the schema design itself.

### FINDING 9: [LOW] pgvector extension not created by any migration

No migration contains `CREATE EXTENSION IF NOT EXISTS vector`. The extension is a hard prerequisite for the `vector` type and HNSW/ivfflat indexes. If the database is provisioned without this extension, the initial migration `e401bb5fd274` will fail.

### FINDING 10: [LOW] Duplicate create_hypertable calls

`e401bb5fd274` calls `create_hypertable` for audit_trail, transactions, episodes, and events twice each (lines 75, 262, 322, 973 in the main block, and lines 1055-1058 in the P3-002 patch block). All use `if_not_exists => TRUE` so this is idempotent but noisy.

---

## Status Verdict

**VERDICT: CONDITIONAL PASS WITH BLOCKING ISSUES**

The migration chain is structurally valid (single head, no orphan branches, idempotent P19 operations, no vector dimension drift). However, there are **2 blocking issues** and **6 significant drift findings**:

**BLOCKING:**
1. **session_summaries is broken at the ORM level** (CRITICAL) — 11 missing ClassificationMetaMixin columns make the table unusable through SQLAlchemy. A remediation migration is required before any ORM write to this table will succeed.
2. **P19 project isolation is incomplete** (HIGH) — 4 memory ORM models lack project_id/project_scope, meaning project-scoped data isolation does not apply to semantic_facts, procedural_skills, knowledge_graph, or session_summaries when accessed through the ORM. The deferred NOT NULL (P19-011) does not exist.

**SIGNIFICANT:**
- procedural_skills.embedding invisible to ORM
- 5 loop_instances columns invisible to ORM
- loop_instances.status type mismatch (VARCHAR(20) vs TEXT)
- gamification schema excluded from autogenerate
- surveillance.events chunk interval is 1 day (not 7 days)
- CommunicationLog FK will fail on parent DELETE
# P3 Memory Foundation — DB Schema & Migration Chain Audit

**Audit Metadata**
- **Date:** 2026-06-25
- **Agent:** Claude Code subagent (read-only)
- **Affirmation:** READ-ONLY. No migrations run, no DB touched, no secrets inspected.
- **Scope:** `src/memory/models.py`, `src/life_kernel/models.py`, `alembic/env.py`, all 14 migration files under `alembic/versions/`

---

## 1. Table and Schema Count Verification

**Claim (P3-002):** 12 schemas / 47 tables.

**Count from `src/memory/models.py`:**

| Schema | Tables | Count |
|--------|--------|-------|
| memory | episodes, session_summaries, semantic_facts, faiz_profile, emotional_events, inner_journal, faiz_predictions, procedural_skills, knowledge_graph | 9 |
| persona | persona_state, drift_log, mood_history, punishment_log, reward_log | 5 |
| surveillance | device_registry, events, ingestion_log, confrontation_block_log | 4 |
| financial | transactions, project_costs, monthly_reports, optimization_log | 4 |
| projects | tasks, loop_instances, agent_tasks, evidence_artifacts | 4 |
| social | social_map, client_contacts, communication_log | 3 |
| agents | subagent_registry, task_queue, execution_log | 3 |
| consent | consent_ledger, revocation_log, scope_registry | 3 |
| security | access_log, break_glass_log, secret_rotation_log | 3 |
| audit | audit_trail, evidence_register, compliance_check | 3 |
| ops | migration_log, backup_log, health_check, alert_history | 4 |
| extensions | pgvector_config, timescaledb_config, pgcrypto_config | 3 |

**Total: 12 schemas / 48 ORM classes with `__tablename__`** (48 because SessionSummary now included vs the original 47 claimed).

The docstring at `models.py:1` still says "47 tables across 12 schemas (P3-002)" — it is now one table out of date.

**Verdict:** VERIFIED (original 47 tables claim matches the historical scope; current ORM has 48 due to SessionSummary).

---

## 2. Migration Chain Map

Current HEAD: **p19_002_project_id_not_null** (STUB, no-op).

```
2bed93fd1dd0  (baseline_init — NOOP root anchor)
    |
    v
e401bb5fd274  (initial_schema_47_tables — 45 op.create_table + 4 hypertables
    |          + 2 HNSW indexes, retention policies)
    v
65f863220922  (add_search_vector_do_not_recall — search_vector COMPUTED +
    |          do_not_recall + GIN index)
    |
    +---> p5_extend_loops  ->  p5_add_loop_indexes  ->  p6_gamification_schema
    |                                                       |
    |                                                       v
    |                                                     7239fd4b3b5a
    |                                                       |
    |                                                       v
    |                                                      (merge parent)
    |
    +---> 3d41deeca703  (p18_add_memory_tiers_fsrs — 7 columns + index)
              |
              v
         f47a9c2e8b1d  (p5_012_extend_loop_instances — MERGE of both)
              |
              v
         p5_015_add_skill_embedding  (procedural_skills embedding + IVFFLAT)
              |
              v
         p5_024_add_session_summaries  (session_summaries table)
              |
              v
         p20_001_life_kernel_schema  (life_kernel: 3 tables, 3 indexes)
              |
              v
         p19_001_project_namespaces  (project_id + project_scope, project_registry)
              |
              v
         p19_002_project_id_not_null  (STUB no-op — *** HEAD ***)
```

### Key structural points

**Fork at 65f863220922.** Two branches diverge:
- Branch A: -> p5_extend_loops -> p5_add_loop_indexes -> p6_gamification_schema -> 7239fd4b3b5a
- Branch B: -> 3d41deeca703 (P18)

**Merge at f47a9c2e8b1d.** The migration file has `down_revision = ("7239fd4b3b5a", "3d41deeca703")` — a tuple specifying two parents. This is a correct Alembic merge migration. After this point the chain is linear to HEAD.

No multiple heads detected. No branch labels in use.

**MEDIUM:** The revision header comment in `p5_012_extend_loop_instances.py` (line 4) says `Revises: 3d41deeca703`, which is misleading — it should say `Revises: 7239fd4b3b5a, 3d41deeca703` to reflect the two-parent merge.

---

## 3. CRITICAL — Missing Btree Descending Indexes

Four btree indexes declared in `src/memory/models.py` `__table_args__` are **never created** by any migration's DDL:

| Index | Table (Schema) | models.py line | Created by any migration? |
|-------|----------------|---------------|------------------------|
| `episodes_started_at_idx` | memory.episodes | 94-95 | **NO** |
| `events_occurred_at_idx` | surveillance.events | 541 | **NO** |
| `transactions_occurred_at_idx` | financial.transactions | 618 | **NO** |
| `audit_trail_occurred_at_idx` | audit.audit_trail | 1081 | **NO** |

**Evidence in `src/memory/models.py`:**
- Line 94-95: `Index("episodes_started_at_idx", text("started_at DESC"))`
- Line 541: `Index("events_occurred_at_idx", text("occurred_at DESC"))`
- Line 618: `Index("transactions_occurred_at_idx", text("occurred_at DESC"))`
- Line 1081: `Index("audit_trail_occurred_at_idx", text("occurred_at DESC"))`

**Evidence of absence:** Grep across all 14 migration files for these index names returns zero matches. The initial migration `e401bb5fd274` creates hypertables for all four tables but never creates the DESC btree indexes.

While TimescaleDB automatically creates default chunk-level indexes on the time partition column, an explicit DESC index is significantly more efficient for `ORDER BY time DESC LIMIT N` — the most common query pattern for time-series retrieval. Without these indexes, queries on the time column may fall back to Seq Scan on the main table or require implicit chunk scans.

The prior P3 legacy audit (`docs/setup-evidence/legacy-audit/P3/db-schema-migration-chain-audit.md`, line 165) also flagged `episodes_started_at_idx` specifically.

---

## 4. HIGH — SessionSummary ClassificationMeta Columns Missing from Migration

**`src/memory/models.py:190`** declares `class SessionSummary(Base, ClassificationMetaMixin)`, which inherits 12 governance columns from `ClassificationMetaMixin` (lines 57-84): classification, purpose, source, retention_class, retention_until, access_policy, encryption_profile, deletion_state, key_id, key_version, created_at, updated_at.

However, `alembic/versions/p5_024_add_session_summaries.py` creates the table with only:
- id, session_id, summary_text, original_message_count, compacted_to_count, tokens_saved, created_at

The ClassificationMeta columns are **absent from the DDL**. If the live database was provisioned through `alembic upgrade` (not `metadata.create_all`), the session_summaries table lacks all governance metadata columns. An `alembic --autogenerate` check would produce a new migration to add these columns.

**Impact:** Any runtime code that accesses `session_summaries.classification` or other governance columns will receive a PostgreSQL column-not-found error. The `evidence_artifacts` table in the initial migration uses `Base` directly (not mixin), which is correct — but SessionSummary extends the mixin, and the migration does not reflect this.

---

## 5. HIGH — Column/Property Drift Between ORM and Live DB DDL

Comparing `models.py` against what the migrations create reveals columns that exist in the DB but have no ORM representation (the ORM query layer cannot see these columns unless accessed via raw SQL):

### Columns in DB DDL but NOT in ORM

| Table | Missing from ORM | Added by Migration |
|-------|-----------------|-------------------|
| memory.procedural_skills | embedding vector(1536) | p5_015_add_skill_embedding |
| memory.procedural_skills | project_id UUID | p19_001 |
| memory.procedural_skills | project_scope TEXT | p19_001 |
| memory.session_summaries | project_id UUID | p19_001 |
| memory.semantic_facts | project_id UUID | p19_001 |
| memory.semantic_facts | project_scope TEXT | p19_001 |
| memory.knowledge_graph | project_id UUID | p19_001 |
| memory.knowledge_graph | project_scope TEXT | p19_001 |
| projects.tasks | project_id UUID | p19_001 |
| projects.loop_instances | project_id UUID | p19_001 |
| projects.loop_instances | checkpoint_data JSONB | p5_012 |
| projects.loop_instances | error_message TEXT | p5_012 |
| projects.loop_instances | phase SMALLINT | p5_012 |
| projects.loop_instances | phase_artifacts JSONB | p5_012 |
| projects.loop_instances | parent_loop_id VARCHAR(12) | p5_012 |
| projects.agent_tasks | project_id UUID | p19_001 |
| audit.audit_trail | project_id UUID | p19_001 |
| consent.consent_ledger | project_id UUID | p19_001 |
| surveillance.events | project_id UUID | p19_001 |
| life_kernel.* (3 tables) | **No ORM classes exist** | p20_001 |
| gamification.* (6 tables) | **No ORM classes exist** | p6_gamification_schema |

The `procedural_skills.embedding` column is especially load-bearing — if any code path tries to do semantic search over procedural skills via the ORM, it will not find the embedding column.

Episodes is the **only** ORM class that has `project_id` and `project_scope` defined (lines 180-187). This means that P19 namespace isolation for ORM queries on everything except episodes must use raw SQL or dynamic column access.

---

## 6. HNSW Index DDL Verification

Both vector embedding indexes use HNSW with correct parameters:

| Index | Migration line | Parameters |
|-------|---------------|------------|
| `ix_episodes_embedding_hnsw` | e401bb5fd274:325, 1059 | `m=16, ef_construction=128, vector_cosine_ops` |
| `ix_semantic_facts_embedding_hnsw` | e401bb5fd274:480, 1060 | `m=16, ef_construction=128, vector_cosine_ops` |

These match the ORM declarations at `models.py:96-102` and `models.py:212-218`.

**COSMETIC:** Both HNSW indexes are created **twice** in `e401bb5fd274` (lines 325/480 and 1059/1060). `IF NOT EXISTS` makes this harmless but indicates the migration was manually edited rather than regenerated.

**LOW:** `p5_015_add_skill_embedding.py` adds a **IVFFLAT** index (not HNSW) on `procedural_skills.embedding` — this is acceptable for a smaller table but inconsistent with the HNSW pattern.

---

## 7. Vector Dimension Consistency

| Column | models.py | Migration DDL | Expected_DIMENSION | Match? |
|--------|-----------|--------------|-------------------|--------|
| episodes.embedding | `Vector(1536)` (line 132) | `VECTOR(dim=1536)` (e401bb5fd274:301) | 1536 | YES |
| semantic_facts.embedding | `Vector(1536)` (line 255) | `VECTOR(dim=1536)` (e401bb5fd274:462) | 1536 | YES |
| procedural_skills.embedding | Not in ORM | `vector(1536)` (p5_015:24) | 1536 | N/A |

**Verdict:** VERIFIED consistent.

---

## 8. FTS search_vector + do_not_recall

Migration `65f863220922` correctly adds:
- `search_vector TSVECTOR COMPUTED` with `setweight(to_tsvector('english', coalesce(title, '')), 'A') || setweight(to_tsvector('english', coalesce(summary, '')), 'B') || setweight(to_tsvector('english', coalesce(raw_content, '')), 'D')` — line 24
- `do_not_recall Boolean NOT NULL DEFAULT false` — line 25
- `ix_episodes_search_vector_gin` GIN index — line 26

ORM at `models.py:134-141` matches exactly.

**Verdict:** VERIFIED.

---

## 9. P18 Tiers / FSRS Columns

Migration `3d41deeca703` adds 7 columns + 1 index to `memory.episodes`. All columns match the ORM at `models.py:154-177`:
- tier, fsrs_state, last_reviewed_at, next_review_at, retrievability, stability, difficulty
- Index `ix_episodes_next_review_at` on next_review_at

**Verdict:** VERIFIED.

---

## 10. P19 Chain Placement After P20

`p19_001_project_namespaces.py` has `down_revision = 'p20_001_life_kernel_schema'` — meaning P19 migrations run AFTER P20. This is documented as intentional:
- p19_001 adds `project_id` to P20's life_kernel tables (life_mind_state, domain_mind_state, heartbeat_record)
- The comment at line 82 says "life_kernel.audit_journal does not exist in current schema -- skipping"

**LOW:** The reverse chronological ordering (P20 before P19 in the migration chain) is intentional but non-obvious. Documented in migration comments but not in any external ADR.

`p19_002_project_id_not_null` is a STUB no-op with an explicit comment (lines 27-33): NOT NULL is deferred to P19-011 after backfill verification.

---

## 11. Stale Dependency and Version Assumptions

- **pgvector:** HNSW index syntax requires pgvector >= 0.5.0. The dependency is imported in `e401bb5fd274` as `import pgvector` (line 13) but no version pin or minimum is documented.
- **TimescaleDB:** Hypertable creation and retention policies require TimescaleDB >= 2.0. No version pin documented.
- **pgcrypto:** `gen_random_uuid()` is used throughout. PostgreSQL 16 has built-in `gen_random_uuid()` so pgcrypto extension is NOT required — this is correct.
- **Alembic env:** `version_table_schema="ops"` places the alembic_version table in the `ops` schema — consistent.

**LOW:** No documented minimum versions for pgvector or TimescaleDB. Extension upgrades could break HNSW or hypertable DDL.

---

## 12. Schema Filter Gaps in env.py

`alembic/env.py` line 19-24 defines:
```python
GUINEVERE_SCHEMAS = frozenset({"memory", "persona", "surveillance", "financial",
    "projects", "social", "agents", "consent", "security", "audit", "ops",
    "extensions", "life_kernel"})
```

**LOW:** The `gamification` schema (created by `p6_gamification_schema.py`) is absent from this set. Future autogenerated migrations will silently ignore changes to gamification tables. The P6 migration works because it uses raw `op.execute()` and explicit `schema='gamification'`, bypassing the filter.

---

## 13. Default Life Kernel audit_journal Table

`src/core/main.py:324` creates `life_kernel.audit_journal` via `PostgresAuditJournal.__init__` at application startup using `CREATE TABLE IF NOT EXISTS`. This table is not represented in any ORM model or migration file. p19_001 explicitly notes this (line 82).

**MEDIUM:** The audit_journal table is created outside the migration system, at application startup. If the migration chain is ever reset or run in a new environment, this table depends on application startup code to exist. The migration chain does not represent the full runtime schema.

---

## 14. Duplicate Hypertable DDL in Initial Migration

`e401bb5fd274` creates hypertables twice for the same tables:

1. Inline (within `op.create_table` blocks): lines 75 (audit), 262 (transactions), 322 (episodes), 973 (events)
2. Manual patch section: lines 1055-1058

For `surveillance.events`, the inline block uses `INTERVAL '1 day'` (line 973) while the manual patch block uses `INTERVAL '7 days'` (line 1058). Since `if_not_exists => TRUE`, the second call is a no-op, meaning **surveillance.events effectively uses 1-day chunks**, not 7-day as the manual patch intended.

**LOW:** The other three tables have consistent intervals between the two sections. Only `surveillance.events` has a mismatched chunk interval.

---

## Status Verdict

**IMPLEMENTED WITH BUGS**

The core migration chain is structurally sound (convergent head, clean merge), and the key P3 claims (12 schemas, 47+ tables, HNSW indexes, FTS search_vector, do_not_recall, correct vector dimensions) are verified with real DDL. However, there are several defects:

### Finding Summary

| Severity | Count | Issues |
|----------|-------|--------|
| **CRITICAL** | 1 | Four btree DESC indexes defined in ORM missing from all migration DDL (episodes_started_at_idx, events_occurred_at_idx, transactions_occurred_at_idx, audit_trail_occurred_at_idx) |
| **HIGH** | 2 | (1) SessionSummary lacks ClassificationMetaMixin columns in migration DDL. (2) 19+ columns across 10+ tables exist in DB DDL but have no ORM representation (especially procedural_skills.embedding). |
| **MEDIUM** | 2 | (1) Life kernel audit_journal table created outside migration system. (2) Merge migration revision header comment misleading (only shows one parent). |
| **LOW** | 4 | (1) HNSW indexes created twice (harmless). (2) surveillance.events chunk interval mismatch (1d vs 7d). (3) gamification schema excluded from env.py filter. (4) No extension version requirements documented. |
| **COSMETIC** | 1 | models.py docstring stale (says 47 tables, has 48). |

### Recommendations (no fixes — for mama consideration)

1. **Create a single corrective migration** that adds the four missing DESC btree indexes and the ClassificationMetaMixin columns to session_summaries.
2. **Reconcile ORM with DDL** by adding ORM columns for all migration-created columns (procedural_skills.embedding, project_id/project_scope, loop_instances.checkpoint_data, etc.) or by adding explicit comments documenting intentional drift.
3. **Add ORM classes for life_kernel (3 tables)** to enable ORM access patterns if intended; otherwise, document the raw-SQL-only design.
4. **Fix the merge migration header comment** in p5_012_extend_loop_instances.py to accurately reflect the two-parent merge.
5. **Add gamification to GUINEVERE_SCHEMAS** in env.py if autogenerated diffing is ever needed.

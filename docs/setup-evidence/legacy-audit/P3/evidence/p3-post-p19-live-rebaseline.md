# P3 Post-P19 Live Rebaseline

**Date:** 2026-06-27
**Agent:** Read-only VPS reconciliation (parent, Opus 4.8)
**VPS:** faiz-prod-01, guinevere-core active (pid 2739223, started 2026-06-27 11:27:57 WIB)
**Repo on VPS:** /home/guinevere/code/guinevere (deployed, not a git repo)
**Previous report:** `p3-current-live-db-reconciliation-audit.md` (2026-06-26, **HISTORICAL PRE-P19 SNAPSHOT**)
**Read-only affirmation:** YES. No INSERT/UPDATE/DELETE/migration/restart/deploy. No raw memory printed. No secrets printed.

---

## 0. Supersession Notice

**The previous reconciliation report (`p3-current-live-db-reconciliation-audit.md`, dated 2026-06-26) is now a HISTORICAL PRE-P19 SNAPSHOT.** It was accurate when written but is stale because P19 production schema was deployed to the live database on 2026-06-27.

Every claim in the old report stating "P19 not deployed" or "0 project_id columns in memory schema" is **superseded** by this rebaseline.

---

## 1. P19 Production Deploy — Live DB Truth

### 1.1 Alembic Version State

**Source:** `SELECT version_num FROM ops.alembic_version ORDER BY version_num`

| Version | Status |
|---|---|
| p19_001_project_namespaces | DEPLOYED |
| p19_002_project_id_not_null | DEPLOYED (was STUB in local repo; P19 production deploy applied NOT NULL surgically) |
| p19_003_audit_chain_version | DEPLOYED |
| p20_001_life_kernel_schema | DEPLOYED |

All 4 versions stamped. P19 is fully deployed.

### 1.2 project_id Columns — Memory Schema

**Source:** `SELECT table_name, is_nullable, column_default FROM information_schema.columns WHERE table_schema='memory' AND column_name='project_id'`

| Table | Nullable | Default |
|---|---|---|
| episodes | NO | (backfilled to default project UUID) |
| kg_consent_audit | YES | — |
| kg_edges | YES | — |
| kg_entities | NO | (backfilled) |
| kg_episodes | YES | — |
| procedural_skills | NO | (backfilled) |
| semantic_facts | NO | (backfilled) |
| session_summaries | NO | (backfilled) |

**8 tables** with project_id in memory schema. **5 NOT NULL** (episodes, kg_entities, procedural_skills, semantic_facts, session_summaries). **3 nullable** (kg_consent_audit, kg_edges, kg_episodes — global-capable per ADR-052).

### 1.3 project_id Columns — All Schemas

**Source:** `SELECT table_schema, table_name, is_nullable FROM information_schema.columns WHERE column_name='project_id' AND table_schema NOT LIKE '_timescaledb%'`

| Schema | Table | Nullable |
|---|---|---|
| audit | audit_trail | YES |
| consent | consent_ledger | YES |
| financial | transactions | YES |
| life_kernel | domain_mind_state | NO |
| life_kernel | heartbeat_record | NO |
| life_kernel | life_mind_state | NO |
| memory | episodes | NO |
| memory | kg_consent_audit | YES |
| memory | kg_edges | YES |
| memory | kg_entities | NO |
| memory | kg_episodes | YES |
| memory | procedural_skills | NO |
| memory | semantic_facts | NO |
| memory | session_summaries | NO |
| projects | agent_tasks | NO |
| projects | loop_instances | NO |
| projects | tasks | NO |
| surveillance | events | YES |

**18 tables** with project_id across 7 schemas. **11 NOT NULL** (memory: 5, life_kernel: 3, projects: 3). **7 nullable** (global-capable: audit, consent, financial, memory kg_consent_audit/kg_edges/kg_episodes, surveillance).

### 1.4 project_scope Columns — Memory Schema

**Source:** `SELECT table_name, is_nullable, column_default FROM information_schema.columns WHERE table_schema='memory' AND column_name='project_scope'`

| Table | Nullable | Default |
|---|---|---|
| episodes | NO | 'project' |
| kg_entities | NO | 'project' |
| procedural_skills | NO | 'project' |
| semantic_facts | NO | 'project' |

**4 tables** with project_scope in memory schema. All NOT NULL DEFAULT 'project'.

### 1.5 projects.project_registry

**Source:** `\d projects.project_registry`

**EXISTS.** Columns: id (UUID PK), slug (TEXT NOT NULL UNIQUE), name (TEXT NOT NULL), status (TEXT NOT NULL DEFAULT 'active'), created_at, archived_at, metadata (JSONB), default_channel_id, dashboard_channel_id, log_channel_id, accent_color.

**Default project seeded:** `id=00000000-0000-0000-0000-000000000001, slug=default, name=Default Project, status=active`

### 1.6 P19 Composite Indexes

**Source:** `SELECT indexname FROM pg_indexes WHERE indexname LIKE '%project_id%' OR indexname LIKE '%chain_version%'`

**24 P19 indexes** created:
- `ix_episodes_project_id_created_at`, `ix_episodes_project_id_embedding` (btree + pgvector composite)
- `ix_semantic_facts_project_id_created_at`, `ix_semantic_facts_project_id_embedding`
- `ix_procedural_skills_project_id_created_at`, `ix_procedural_skills_project_id_embedding`
- `ix_session_summaries_project_id_created_at`
- `ix_kg_entities_project_id`
- `ix_kg_edges` (via kg_edges.source_fact_id — P16 KG)
- `ix_audit_trail_project_id_created_at`, `ix_audit_trail_chain_version`
- `ix_consent_ledger_project_id_created_at`
- `ix_events_project_id`
- `ix_heartbeat_record_project_id`
- `ix_life_mind_state_project_id`
- `ix_domain_mind_state_project_id_domain` (unique swap)
- `ix_agent_tasks_project_id_created_at`, `ix_loop_instances_project_id_created_at`, `ix_tasks_project_id_created_at`
- Plus timescaledb chunk copies for episodes

### 1.7 Feature Flag

**Status:** `feature:projects:enabled` = **OFF** (inert). P19 schema deployed but behavior byte-identical to P20. Operator must explicitly enable.

---

## 2. Memory System — Live DB State

### 2.1 Database State

| Metric | Value |
|---|---|
| Alembic versions | p19_001, p19_002, p19_003, p20_001 |
| pgvector version | 0.8.2 |
| TimescaleDB version | 2.27.1 |
| Memory schema base tables | 15 |
| Memory schema views | 3 (kg_active_edges, kg_active_entities, kg_same_as_pending_review) |
| Total memory objects | 18 |
| project_id columns (all schemas) | 18 tables |
| project_id NOT NULL | 11 tables |
| project_scope columns (memory) | 4 tables, all NOT NULL DEFAULT 'project' |
| P19 composite indexes | 24 |
| projects.project_registry | EXISTS, default project seeded |

### 2.2 Memory Data

| Metric | Value |
|---|---|
| Total episodes | 3 |
| Episodes with embedding | 0 (all NULL) |
| Episodes with DNR | 0 |
| Episodes by source | 3 discord_conversation |
| Episodes by classification | 3 Restricted |
| Episodes project_id | ALL backfilled to default project UUID |
| Semantic facts | 6 (created 2026-06-19, manual consolidation) |
| Semantic facts project_id | ALL backfilled to default project UUID |
| Session summaries | 0 rows (8 columns, project_id NOT NULL added by P19) |
| HNSW indexes | 3 (episodes, semantic_facts, kg_entities) |
| GIN FTS index | 1 (episodes search_vector) |
| DESC btree indexes | 4 confirmed existing (episodes_started_at_idx, audit_trail_occurred_at_idx, transactions_occurred_at_idx, events_occurred_at_idx) |

### 2.3 session_summaries — Updated Column List

**Source:** `SELECT column_name FROM information_schema.columns WHERE table_schema='memory' AND table_name='session_summaries' ORDER BY ordinal_position`

| # | Column | Type | Nullable | Notes |
|---|---|---|---|---|
| 1 | id | UUID | NO | PK |
| 2 | session_id | VARCHAR | NO | |
| 3 | summary_text | TEXT | NO | |
| 4 | original_message_count | INTEGER | YES | |
| 5 | compacted_to_count | INTEGER | YES | |
| 6 | tokens_saved | INTEGER | YES | |
| 7 | created_at | TIMESTAMPTZ | NO | |
| 8 | project_id | UUID | NO | **P19 ADDED** |

**Still missing from ClassificationMetaMixin (11 columns):** classification, purpose, source, retention_class, retention_until, access_policy, encryption_profile, deletion_state, key_id, key_version, updated_at.

### 2.4 Runtime State

| Component | Status |
|---|---|
| guinevere-core | Running (pid 2739223, started 2026-06-27 11:27 WIB) |
| Life-kernel heartbeat | Running (1s + 10s intervals) |
| KG ingestion cron | Running (03:30 ICT daily) |
| Consolidation scheduler | NOT running (commented out in main.py:23-38) |
| Decay sweep scheduler | NOT running (not wired) |
| Monthly report scheduler | Running |
| Manual consolidation | Ran once (2026-06-19, 6 facts produced) |
| Journalctl consolidation keywords | 0 (no cron-triggered runs) |
| Journalctl memory errors | 0 |
| P19 feature flag | OFF (inert) |
| knowledge_graph table | Does NOT exist (kg_entities/kg_edges used instead) |

### 2.5 Life-Kernel Recall Path

**Source:** `sed -n '270,290p' /home/guinevere/code/guinevere/src/core/main.py`

The life-kernel recall closure (`_life_recall_fn`) does NOT pass `embedding_service`. It relies on `recall_memories` default of `None`. The closure is wrapped by `MemoryRecallAdapter` and injected into the life-kernel graph. No embedding service is injected into the life-kernel recall path.

---

## 3. Findings Superseded by P19 Deploy

| Old Claim (from pre-P19 report) | New Truth (post-P19) |
|---|---|
| "P19 not deployed" | P19 IS deployed. 4 alembic versions stamped. |
| "0 project_id columns in memory schema" | 8 tables have project_id. 5 NOT NULL. |
| "0 project_scope columns anywhere" | 4 memory tables have project_scope, all NOT NULL DEFAULT 'project'. |
| "projects.project_registry does not exist" | EXISTS. Default project seeded. |
| "P19 not deployed; no project_id columns exist" | 18 project_id columns across 7 schemas. 11 NOT NULL. |
| "session_summaries has 7 columns" | 8 columns (project_id added by P19). Still missing 11 ClassificationMetaMixin columns. |
| "BUG-003 moot because P19 not deployed" | BUG-003 now a LIVE BUG — store_episode_batch still doesn't forward project_id. |
| "BUG-008 moot because P19 not deployed" | BUG-008 now a LIVE BUG — consolidation has zero project awareness despite project_id on semantic_facts. |
| "BUG-018 moot because P19 not deployed" | BUG-0018 partially live — project_id on kg_entities/kg_edges, but consolidation doesn't populate it. |
| "NEW-003 project_registry ORM missing" | Still true — no ORM model for project_registry. |

---

## 4. Findings Unchanged by P19

| Finding | Status |
|---|---|
| Consolidation scheduler commented out | UNCHANGED — still commented out, journalctl 0 keywords |
| All 3 episodes have NULL embedding | UNCHANGED — 3/3 embedding IS NULL |
| semantic_facts has 6 rows (manual) | UNCHANGED — 6 rows from 2026-06-19 |
| 0 DNR episodes | UNCHANGED — 0 episodes with do_not_recall=true |
| HNSW indexes | UNCHANGED — 3 indexes (episodes, semantic_facts, kg_entities) |
| knowledge_graph ORM stale | UNCHANGED — no memory.knowledge_graph table, kg_entities/kg_edges used |
| DNR pre-injection gate not wired | UNCHANGED — verify_recall_results_dnr_free still zero call sites |
| safe_mode not reaching life-kernel recall | UNCHANGED — _life_recall_fn still doesn't pass safe_mode |
| Life-kernel recall closure omits embedding_service | UNCHANGED — _life_recall_fn uses recall_memories default (None) |
| session_summaries missing 11 ClassificationMetaMixin columns | UNCHANGED — 8 columns now (was 7), still missing 11 |
| All 235 memory tests use FakeSession | UNCHANGED |
| Desc btree indexes exist on live DB | UNCHANGED — all 4 confirmed existing |

---

## 5. New Findings Post-P19

### NEW-P19-001 [HIGH]: project_id backfill on episodes — but episodes still have NULL embedding

All 3 episodes have `project_id` backfilled to the default project UUID. But all 3 still have `embedding IS NULL`. P19 added project scoping to the episodes but did not address the embedding gap (BUG-011). This means project-scoped recall is structurally possible but vector search remains non-functional for all production episodes.

### NEW-P19-002 [HIGH]: Consolidation now produces project-scoped-gap facts

With `project_id NOT NULL` on `semantic_facts`, any future consolidation run MUST provide a `project_id`. But `consolidate_episodes_to_facts()` has zero project awareness (BUG-008/GAP-009). If consolidation is enabled without fixing this, it will fail with a NOT NULL constraint violation on `project_id` — or default to NULL which is now disallowed.

**This is a new blocker for enabling the consolidation scheduler.** Before P19, consolidation could produce facts without project_id (nullable). After P19, `project_id NOT NULL` on semantic_facts means consolidation MUST provide a project_id or it will crash.

### NEW-P19-003 [MEDIUM]: P19 composite (project_id, embedding) indexes on memory tables

P19 created composite pgvector indexes: `ix_episodes_project_id_embedding`, `ix_semantic_facts_project_id_embedding`, `ix_procedural_skills_project_id_embedding`. These are btree indexes on `(project_id, embedding)` — not HNSW. The HNSW indexes remain separate. For project-scoped vector search to use HNSW, the planner must combine the HNSW index with a project_id filter. Performance impact unknown — never benchmarked (BUG-024).

### NEW-P19-004 [MEDIUM]: 3 views in memory schema (kg_active_edges, kg_active_entities, kg_same_as_pending_review)

The old report counted 18 "tables" — actually 15 base tables + 3 views. These views are P16 KG convenience views, not P19 additions. No impact on P3 memory.

### NEW-P19-005 [LOW]: knowledge_graph ORM still maps to non-existent table

This was flagged in the pre-P19 report and remains true. The `KnowledgeGraph` ORM class (models.py:391) maps to `__tablename__ = "knowledge_graph"` which doesn't exist on live DB. The actual KG is `kg_entities`/`kg_edges`.

---

## 6. Explicit Affirmation

This rebaseline was conducted entirely **read-only via SSH to the VPS**. No INSERT/UPDATE/DELETE, no alembic upgrade/downgrade, no service restart, no deploy, no raw memory content printed, no secrets printed. All `psql` commands were `SELECT`, `\d`, or `information_schema` queries.

**Output file:** `docs/setup-evidence/legacy-audit/P3/evidence/p3-post-p19-live-rebaseline.md`
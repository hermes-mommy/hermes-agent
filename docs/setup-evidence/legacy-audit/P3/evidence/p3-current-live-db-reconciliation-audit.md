# ⚠️ HISTORICAL PRE-P19 SNAPSHOT — SEE CURRENT REBASELINE

> **This report is a HISTORICAL PRE-P19 SNAPSHOT (dated 2026-06-26).**
> It is stale because P19 production schema was deployed on 2026-06-27.
> **Current live truth:** [`p3-post-p19-live-rebaseline.md`](p3-post-p19-live-rebaseline.md)
> **Bug reclassification:** [`p3-post-p19-bug-reclassification.md`](p3-post-p19-bug-reclassification.md)
> **Supersession details:** [`p3-historical-pre-p19-supersession-note.md`](p3-historical-pre-p19-supersession-note.md)

---

# P3 Current-Source + Live-DB Reconciliation Audit

**Date:** 2026-06-26
**Agent:** SSH VPS read-only reconciliation (Opus 4.8)
**VPS:** faiz-prod-01 (guinevere-core running, pid 806559, started 2026-06-25 08:26 WIB)
**Repo on VPS:** /home/guinevere/code/guinevere (deployed, not a git repo)
**Read-only affirmation:** YES. No INSERT/UPDATE/DELETE/migration/restart/deploy. No raw memory printed. No secrets printed. DB password was read from env but never echoed.

---

## 0. Executive Summary — The Single Most Important Finding

### Alembic: current = p20_001_life_kernel_schema, head = p19_002_project_id_not_null

**P19 migrations (p19_001 + p19_002) have NOT been deployed to the live database.**

This means:
- `project_id` and `project_scope` columns do NOT exist in memory schema / P19 target namespace tables (0 project_id columns in memory schema; 0 project_scope columns anywhere in the DB)
- **Exception:** `financial.transactions` has a `project_id` column (UUID) unrelated to P19 memory namespace — this is a pre-existing financial schema column, not a P19 addition
- `projects.project_registry` does NOT exist
- The entire P19 multi-project namespace layer is source-complete but NOT deployed
- HALF of the previous audit's CRITICAL/HIGH findings about P19 isolation are **moot on the live DB** — they are source-readiness issues for P19 deployment, not live-DB gaps

The migration chain is:
```
p20_001_life_kernel_schema  <-- CURRENT (live DB)
p19_001_project_namespaces   <-- NOT DEPLOYED
p19_002_project_id_not_null  <-- HEAD (STUB, NOT DEPLOYED)
```

This is architecturally correct: P20 was deployed before P19 because P20 is the living autonomy kernel that needed to be running. P19 deployment is pending.

---

## 1. Classification of Every CRITICAL Finding

### BUG-001: `verify_recall_results_dnr_free()` never called at runtime

**Status: CONFIRMED_CURRENT_SOURCE**

**Evidence:**
- VPS source at `/home/guinevere/code/guinevere/src/memory/dnr.py` matches local repo
- `verify_recall_results_dnr_free` is defined (line 385) and exported from `__init__.py` (line 81)
- Zero call sites in `src/` — confirmed by grep on VPS source
- Live DB: 0 DNR episodes exist (3 total, all `do_not_recall=false`), so no active DNR enforcement needed

**Live-DB context:** With 0 DNR episodes, the gate would not be exercised even if wired. Risk is dormant but real for future DNR use.

---

### BUG-002: Consolidation scheduler commented out in production startup

**Status: CONFIRMED_CURRENT_SOURCE + CONFIRMED_LIVE_DB — with nuance**

**Evidence:**
- VPS `main.py:23-38` matches local repo exactly — consolidation is commented out
- `register_consolidation_job` is defined in `consolidation.py:851` but never called
- `register_decay_job` is defined in `consolidation.py:1087` but never called
- **journalctl** for guinevere-core (last 5000 lines) shows ZERO consolidation/decay keywords
- **KG ingestion scheduler IS running** (main.py:167-201 wires `register_kg_ingestion_job`) — this proves the pattern works

**HOWEVER — The semantic_facts table has 6 rows, source=consolidation, created 2026-06-19:**

```
6 semantic_facts total, all source=consolidation, all created 2026-06-19 18:51:16+07
3 episodes -> 2 facts each (episodic_summary + key_insight)
```

This means consolidation was **run manually at least once** (on 2026-06-19), producing 6 facts from 3 episodes. The automated cron never ran, but a one-shot manual consolidation did produce output. This partially refutes the claim that "semantic_facts is empty" — it has 6 rows, all from a manual run.

**Revised verdict:** Consolidation is code-complete, tested, but **never automated**. A manual run on 2026-06-19 produced 6 semantic_facts. The scheduler remains commented out. The claim "semantic memory layer is entirely dormant" is **partially refuted** — it was manually exercised once.

---

### BUG-003: `store_episode_batch` loses project_id

**Status: SUPERSEDED_BY_P19_OR_LATER_CHANGE**

**Evidence:**
- P19 migrations NOT deployed → `project_id` columns do NOT exist in memory schema / P19 target namespace tables (exception: `financial.transactions.project_id` is unrelated to P19 memory namespace)
- Query: `SELECT column_name FROM information_schema.columns WHERE table_schema='memory' AND column_name IN ('project_id', 'project_scope')` → **0 rows returned**
- `store_episode_batch` on VPS source matches local — does not forward `project_id`
- This is a P19 source-readiness issue, not a live-DB bug

**Impact:** When P19 is deployed, `store_episode_batch` will need to forward `project_id`. Currently moot because P19 isn't deployed.

---

### BUG-004: SemanticFacts and KnowledgeGraph ORM lack project_id columns

**Status: SUPERSEDED_BY_P19_OR_LATER_CHANGE — with ORM table name mismatch**

**Evidence:**
- P19 NOT deployed → `project_id`/`project_scope` don't exist on live DB
- Live DB has no `memory.knowledge_graph` table at all
- The knowledge graph is `memory.kg_entities` + `memory.kg_edges` (18 memory tables total)
- The ORM model `KnowledgeGraph` (models.py:391) maps to a table name that doesn't exist on live DB
- There is a `memory._legacy_knowledge_graph` table (legacy)

**Additional finding:** The `KnowledgeGraph` ORM class in models.py appears to map to a table that was renamed to `kg_entities`/`kg_edges` during P16. The ORM model is stale — it doesn't match the live DB schema regardless of P19.

**Revised verdict:** This is a P16 schema-evolution issue (KG table was renamed/restructured) AND a P19 readiness issue. Not a live-DB blocker because P19 isn't deployed.

---

### BUG-005: Four btree DESC indexes declared in ORM missing from all migration DDL

**Status: REFUTED_BY_LIVE_DB**

**Evidence from live DB:**
```
schemaname    | tablename    | indexname
--------------+--------------+-----------------------------------------
memory        | episodes     | episodes_started_at_idx          ← EXISTS
audit         | audit_trail  | audit_trail_occurred_at_idx      ← EXISTS
financial     | transactions | transactions_occurred_at_idx     ← EXISTS
surveillance  | events       | events_occurred_at_idx           ← EXISTS
```

**ALL FOUR** claimed-missing indexes exist on the live database. TimescaleDB also created chunk-level copies:
```
_timescaledb_internal | _hyper_17_13_chunk | _hyper_17_13_chunk_episodes_started_at_idx
_timescaledb_internal | _hyper_17_14_chunk | _hyper_17_14_chunk_episodes_started_at_idx
```

**The previous audit was wrong.** The indexes exist on the live DB. They may have been created by TimescaleDB's automatic chunk index creation, or by a migration that the audit missed. Either way, the claim that "queries may fall back to Seq Scan" for these columns is **incorrect** — the indexes are present.

**Verdict:** This finding is **REFUTED** and should be removed from the bug register.

---

### BUG-006: DNR result dicts lack `do_not_recall` key — gate would not work even if called

**Status: CONFIRMED_CURRENT_SOURCE**

**Evidence:**
- VPS source `read_pipeline.py:769-777` matches local — `compute_scored_results` builds dicts with 7 keys, none of which is `do_not_recall`
- `dnr.py:406` checks `entry.get("do_not_recall")` which returns `None` for missing keys
- No change to source since previous audit

**Live-DB context:** 0 DNR episodes, so this cannot be tested live. Risk is dormant.

---

## 2. Classification of Every HIGH Finding

### BUG-007: safe_mode never reaches memory recall during HARD STOP in life-kernel

**Status: CONFIRMED_CURRENT_SOURCE**

**Evidence:**
- VPS `life_kernel/graph.py:262-264` — `observe_node` calls `memory_adapter.recall()` before `decide_node` checks HARD STOP
- VPS `life_kernel/p18_adapter.py:92-97` — adapter does not accept `safe_mode`
- VPS `main.py:272` — `_life_safe_recall` defaults to `False`
- Zero `safe_mode` references in `src/life_kernel/` on VPS
- Journalctl shows `heartbeat_10s_graph_health_check` every 10 seconds — life kernel is running, but no HARD STOP events have occurred

**Live-DB context:** Life kernel IS running (heartbeat every 1s/10s). The gap is real but has never been triggered because no HARD STOP event has occurred in production.

---

### BUG-008: Consolidation has zero project_id awareness

**Status: SUPERSEDED_BY_P19_OR_LATER_CHANGE**

**Evidence:**
- P19 NOT deployed → no `project_id` columns exist
- The 6 semantic_facts on live DB were created by manual consolidation on 2026-06-19 — all are global-scope (no project_id column to populate)
- VPS source `consolidation.py:275-282` matches local — no `project_id` parameter

---

### BUG-009: SessionSummary ClassificationMetaMixin columns missing from migration DDL

**Status: CONFIRMED_LIVE_DB**

**Evidence from live DB:**
```
\d memory.session_summaries shows only 7 columns:
id, session_id, summary_text, original_message_count, compacted_to_count, tokens_saved, created_at

Missing 11 ClassificationMetaMixin columns:
classification, purpose, source, retention_class, retention_until, access_policy,
encryption_profile, deletion_state, key_id, key_version, updated_at
```

**This is confirmed on the live DB.** The table is missing 11 governance columns that the ORM model expects. Any ORM INSERT to `session_summaries` would fail with a missing-column error.

**Impact:** This table is currently unused (no rows, no evidence of writes). The gap is real but dormant until the first `SessionSummary` write.

---

### BUG-010: 19+ columns across 10+ tables exist in DB DDL but have no ORM representation

**Status: REFUTED_BY_LIVE_DB (for P19 columns) + PARTIALLY CONFIRMED (for non-P19 columns)**

**Evidence:**
- P19 NOT deployed → project_id/project_scope don't exist on live DB → the P19-related column gap is moot
- However, `procedural_skills.embedding` vector(1536) DOES exist on live DB (p5_015 migration was deployed) but the ORM model `ProceduralSkills` (models.py:366-388) lacks it
- The `KnowledgeGraph` ORM class maps to a non-existent table name; the actual KG is `kg_entities` + `kg_edges`
- 18 tables in memory schema on live DB vs 9 ORM classes in models.py memory section

**Revised verdict:** The P19 columns don't exist on live DB (refuted). But there are genuine ORM-DB mismatches: `procedural_skills.embedding` invisible to ORM, `KnowledgeGraph` ORM stale, and 18 live tables vs 9 ORM memory classes.

---

### BUG-011: HermesMemoryBridge write path does not compute embeddings

**Status: CONFIRMED_CURRENT_SOURCE + CONFIRMED_LIVE_DB**

**Evidence from live DB:**
```
3 episodes total, all source=discord_conversation
has_embedding = 0, null_embedding = 3
All 3 episodes have embedding IS NULL
```

**This is the most impactful live-DB confirmed finding.** All 3 production episodes — written by the Hermes Discord conversational path — have `embedding=NULL`. Vector similarity search is completely non-functional for all production memory. The `EXPLAIN` output confirms `Seq Scan` because `WHERE embedding IS NOT NULL` filters to zero rows.

**HNSW EXPLAIN (read-only, no embedding data):**
```
Seq Scan on _hyper_17_13_chunk (cost=0.00..10.90 rows=90 width=32)
  Filter: (embedding IS NOT NULL)
Seq Scan on _hyper_17_14_chunk (cost=0.00..1.03 rows=3 width=32)
  Filter: (embedding IS NOT NULL)
```
HNSW indexes exist but are never used because no episodes have embeddings.

---

### BUG-012: Batch write lacks transaction atomicity

**Status: CONFIRMED_CURRENT_SOURCE**

**Evidence:** VPS source matches local. `store_episode_batch` iterates with individual `session.add()` + `session.flush()` per episode. No savepoint or transaction wrapping.

**Live-DB context:** `store_episode_batch` has never been called in production (only 3 episodes, all from `discord_conversation` via `HermesMemoryBridge.store_conversation`). Dormant.

---

### BUG-013: Query embedding dimension not validated before DB query

**Status: CONFIRMED_CURRENT_SOURCE**

**Evidence:** VPS source `read_pipeline.py:888-895` matches local. Broad `except Exception` catches dimension mismatch.

**Live-DB context:** The life-kernel recall closure (`main.py:274-283`) does not pass `embedding_service` at all (relies on `recall_memories` default of `None`). The life-kernel uses `MemoryRecallAdapter` wrapping a pre-bound `_life_recall_fn` closure. No embedding service is injected into the life-kernel recall path, so this code path is not exercised in production.

---

### BUG-014: No classification validation on write when embedding is skipped

**Status: CONFIRMED_CURRENT_SOURCE**

**Evidence:** VPS source matches. Only CRITICAL classification is validated. All 3 episodes have `classification=Restricted` (valid), so no validation gap has been triggered.

---

### BUG-015: Broad `except Exception` on embedding fallback masks configuration errors

**Status: CONFIRMED_CURRENT_SOURCE**

**Evidence:** VPS source `read_pipeline.py:891-895` matches local. The `except Exception` block catches all exception types and silently degrades to keyword-only search.

**Live-DB context:** The life-kernel recall closure (`main.py:274-283`) does not pass `embedding_service` (relies on default of `None`). The `_life_recall_fn` is wrapped by `MemoryRecallAdapter` and used by the life-kernel graph. No embedding service is injected, so this code path is not exercised in production.

---

### BUG-016: P3-007 benchmark executed on 20 rows — HNSW never exercised

**Status: DOC_STALE_ONLY**

**Evidence:**
- HNSW indexes exist on live DB (3 indexes confirmed: episodes, semantic_facts, kg_entities)
- 0 episodes with embeddings → HNSW indexes are present but empty
- The benchmark doc is a static snapshot; the infrastructure is real
- pgvector 0.8.2 confirmed on live DB

**Revised verdict:** The HNSW infrastructure is real and deployed. The benchmark was inadequate but the indexes exist. With 0 embeddings, no benchmark can be meaningful regardless. This is a doc-quality issue, not an implementation gap.

---

### BUG-017: All 235 memory tests use FakeSession/AsyncMock — no real DB E2E

**Status: CONFIRMED_CURRENT_SOURCE**

**Evidence:** VPS source matches local. No change since previous audit.

---

### BUG-018: KG facts leak across projects due to missing project_id

**Status: SUPERSEDED_BY_P19_OR_LATER_CHANGE**

**Evidence:**
- P19 NOT deployed → no project_id columns → no multi-project isolation → no cross-project leak possible
- Live DB has `kg_entities` and `kg_edges` tables, not `knowledge_graph`
- The ORM model `KnowledgeGraph` is stale regardless of P19

---

## 3. Live-DB Ground Truth Summary

### 3.1 Database State

| Metric | Value |
|---|---|
| Alembic current | p20_001_life_kernel_schema |
| Alembic head | p19_002_project_id_not_null (STUB) |
| Migrations behind head | 2 (p19_001, p19_002) |
| pgvector version | 0.8.2 |
| TimescaleDB version | 2.27.1 |
| PostgreSQL version | 16 (via systemd) |
| Total schemas | 27 (including _timescaledb, public, information_schema) |
| Application schemas | 19 |
| Total tables (application) | ~80+ across all schemas |
| Memory schema tables | 18 (including kg_entities, kg_edges, kg_episodes, _legacy_knowledge_graph) |

### 3.2 Memory Data

| Metric | Value |
|---|---|
| Total episodes | 3 |
| Episodes with embedding | 0 (all NULL) |
| Episodes with DNR | 0 |
| Episodes by source | 3 discord_conversation |
| Episodes by classification | 3 Restricted |
| Episodes by date | 3 created 2026-06-18 |
| Semantic facts | 6 (created 2026-06-19, manual consolidation) |
| Semantic facts by type | 3 episodic_summary, 3 key_insight |
| Semantic facts state | all active, all Restricted |
| Session summaries | 0 rows |
| HNSW indexes | 3 (episodes, semantic_facts, kg_entities) |
| GIN FTS index | 1 (episodes search_vector) |
| DESC btree indexes | 4 confirmed existing (all 4 claimed missing) |

### 3.3 Runtime State

| Component | Status |
|---|---|
| guinevere-core | Running (pid 806559, 16h uptime) |
| Life-kernel heartbeat | Running (1s + 10s intervals) |
| KG ingestion cron | Running (03:30 ICT daily) |
| Consolidation scheduler | NOT running (commented out) |
| Decay sweep scheduler | NOT running (not wired) |
| Monthly report scheduler | Running |
| Manual consolidation | Ran once (2026-06-19, 6 facts produced) |
| Journalctl consolidation evidence | None (no cron-triggered runs) |
| Journalctl memory errors | None |

### 3.4 P19 Deployment Status

| Item | Status |
|---|---|
| project_id columns in memory schema / P19 target namespace tables | 0 — NOT DEPLOYED (exception: `financial.transactions.project_id` exists, unrelated to P19 memory namespace) |
| project_scope columns in memory schema / P19 target namespace tables | 0 — NOT DEPLOYED (confirmed: 0 project_scope columns anywhere in the DB) |
| projects.project_registry | Does not exist — NOT DEPLOYED |
| P19 composite indexes | Do not exist — NOT DEPLOYED |
| P19 NOT NULL constraint | Not applied (p19_002 is STUB) |

---

## 4. Findings Classification Summary

### Confirmed on Live DB (CONFIRMED_CURRENT_SOURCE + CONFIRMED_LIVE_DB)

| ID | Severity | Finding | Live-DB Evidence |
|---|---|---|---|
| BUG-002 | CRITICAL | Consolidation scheduler never runs | Journalctl zero consolidation keywords; scheduler commented out in VPS source |
| BUG-009 | HIGH | SessionSummary missing 11 columns | `\d memory.session_summaries` shows only 7 columns |
| BUG-011 | HIGH | All episodes have NULL embedding | 3/3 episodes `embedding IS NULL`; EXPLAIN shows Seq Scan on empty vector column |

### Confirmed in Source but Not Exercised Live (CONFIRMED_CURRENT_SOURCE, dormant)

| ID | Severity | Finding | Why Dormant |
|---|---|---|---|
| BUG-001 | CRITICAL | verify_recall_results_dnr_free never called | 0 DNR episodes exist |
| BUG-006 | CRITICAL | Result dicts lack do_not_recall key | 0 DNR episodes exist |
| BUG-007 | HIGH | safe_mode never reaches life-kernel recall | No HARD STOP events in production |
| BUG-012 | HIGH | Batch write lacks atomicity | store_episode_batch never called |
| BUG-013 | HIGH | Query embedding dim not validated | Life-kernel recall does not pass embedding_service (defaults to None); MemoryRecallAdapter wraps bare _life_recall_fn |
| BUG-014 | HIGH | No classification validation on write | All 3 episodes have valid classification |
| BUG-015 | HIGH | Broad except Exception on embedding | Life-kernel recall does not pass embedding_service (defaults to None); MemoryRecallAdapter wraps bare _life_recall_fn |
| BUG-017 | HIGH | Tests all FakeSession | Test-only issue |

### Refuted by Live DB (REFUTED_BY_LIVE_DB)

| ID | Severity | Original Finding | Why Refuted |
|---|---|---|---|
| BUG-005 | CRITICAL | 4 btree DESC indexes missing | All 4 indexes confirmed existing on live DB |

### Superseded by P19 Not Deployed (SUPERSEDED_BY_P19_OR_LATER_CHANGE)

| ID | Severity | Original Finding | Why Moot |
|---|---|---|---|
| BUG-003 | CRITICAL | store_episode_batch loses project_id | P19 not deployed; no project_id columns exist |
| BUG-004 | CRITICAL | SemanticFacts/KG lack project_id | P19 not deployed; no project_id columns exist |
| BUG-008 | HIGH | Consolidation has zero project_id awareness | P19 not deployed |
| BUG-018 | HIGH | KG facts leak across projects | P19 not deployed; single-project environment |

### Doc-Only (DOC_STALE_ONLY)

| ID | Severity | Original Finding | Why Doc-Only |
|---|---|---|---|
| BUG-016 | HIGH | P3-007 benchmark 20 rows | HNSW indexes exist; 0 embeddings = nothing to benchmark |

---

## 5. New Findings from Live DB

### NEW-001 [HIGH]: knowledge_graph ORM model maps to non-existent table

**Evidence:** `models.py:391` defines `class KnowledgeGraph(Base, ClassificationMetaMixin)` with `__tablename__ = "knowledge_graph"`. The live DB has no `memory.knowledge_graph` table. The actual KG is `memory.kg_entities` (with ClassificationMetaMixin columns + HNSW index) and `memory.kg_edges` (with ClassificationMetaMixin columns). A legacy table `memory._legacy_knowledge_graph` exists.

**Impact:** Any ORM access via `KnowledgeGraph` class will fail with "relation does not exist." The P16 schema migration renamed/restructured the KG tables but the ORM model was not updated.

### NEW-002 [MEDIUM]: 18 memory schema tables on live DB vs 9 ORM classes in models.py memory section

**Evidence:** Live DB has: episodes, emotional_events, faiz_predictions, faiz_profile, inner_journal, kg_active_edges, kg_active_entities, kg_consent_audit, kg_edges, kg_entities, kg_episode_participants, kg_episodes, kg_same_as_edges, kg_same_as_pending_review, procedural_skills, semantic_facts, session_summaries, _legacy_knowledge_graph (18 tables). ORM models.py memory section has 9 classes.

**Impact:** 9 tables (mostly P16 KG tables) have no ORM representation. Access requires raw SQL.

### NEW-003 [LOW]: `projects.project_registry` ORM model missing

**Evidence:** The `projects.project_registry` table is created by `p19_001` migration. Since P19 is not deployed, the table doesn't exist on live DB. But even when P19 deploys, there is no ORM model for it in `src/memory/models.py` or any other models file.

---

## 6. Reconciliation of Previous Audit Velocity

### Findings That Were WRONG

| Claim | Reality |
|---|---|
| "semantic_facts is empty" | 6 rows exist, created by manual consolidation on 2026-06-19 |
| "all 4 btree DESC indexes missing" | All 4 exist on live DB |
| "P19 columns exist in DB but not in ORM" | P19 columns don't exist on live DB at all — P19 not deployed |
| "knowledge_graph table exists in memory schema" | Table was renamed to kg_entities/kg_edges |
| "47 tables across 12 schemas" | 18 memory tables alone; ~80+ total across 19 schemas |

### Findings That Were CORRECT

| Claim | Verification |
|---|---|
| Consolidation scheduler commented out | Confirmed on VPS source |
| All 3 episodes have NULL embedding | Confirmed on live DB |
| session_summaries missing 11 columns | Confirmed on live DB |
| DNR gate never called | Confirmed in VPS source |
| HARD STOP doesn't reach memory recall | Confirmed in VPS source |
| HNSW indexes exist | Confirmed on live DB (3 indexes) |
| 0 DNR episodes | Confirmed on live DB |
| All tests use FakeSession | Confirmed in VPS source |

---

## 7. Mama Audit Corrections

Corrections applied to the original reconciliation report per mama audit feedback:

1. **Line count:** File is 536 lines (content), ~26 KB. Original report claimed 513 lines (wc -l counts newlines; last line has no trailing newline). Corrected to 536 lines of content after Mama corrections.

2. **project_id scope:** Replaced absolute claims "project_id columns on any table = 0" with scoped claim: "0 project_id columns in memory schema / P19 target namespace tables." Added explicit exception: `financial.transactions.project_id` (UUID) exists on live DB, unrelated to P19 memory namespace.

3. **Life-kernel embedding_service claim:** Removed stale claim that life-kernel recall closure "passes `embedding_service=None`." The VPS source at `main.py:274-283` shows `_life_recall_fn` calls `_recall_memories` without passing `embedding_service` at all — it relies on the default of `None`. The `_life_recall_fn` is wrapped by `MemoryRecallAdapter` and injected into the life-kernel graph. Reclassified BUG-013 and BUG-015 dormant reasons accordingly.

4. **Confirmed live findings preserved:**
   - P19 not deployed: `ops.alembic_version=p20_001_life_kernel_schema`, local head=`p19_002_project_id_not_null`
   - 3/3 episodes `embedding IS NULL`
   - `semantic_facts` has 6 consolidation rows (manual run 2026-06-19)
   - `session_summaries` has 7 columns (missing 11 ClassificationMetaMixin)
   - 3 HNSW indexes exist (episodes, semantic_facts, kg_entities)
   - `knowledge_graph` ORM table name stale vs live `kg_entities`/`kg_edges`

5. **No DB mutation, no deploy, no restart, no source edit performed.** All corrections are report-only.

---

## 8. Final Status

**P3 RECONCILIATION REPORT FIXED — SOURCE FIXES STILL REQUIRE MAMA APPROVAL**

### What's Actually Broken on Live DB

| # | Finding | Severity | Impact |
|---|---|---|---|
| 1 | All 3 episodes have NULL embedding (main write path) | HIGH | Vector similarity search non-functional; recall is FTS-only |
| 2 | Consolidation never automated (manual run only) | HIGH | Semantic memory tier not maintained; 6 facts from 1 manual run |
| 3 | session_summaries missing 11 classification columns | HIGH | ORM writes to this table would fail |
| 4 | knowledge_graph ORM maps to non-existent table name | HIGH | ORM access broken; KG accessed via kg_entities/kg_edges |
| 5 | 18 memory tables vs 9 ORM classes | MEDIUM | 9 tables have no ORM representation |

### What's Dormant (Correct in Source, Not Exercised)

| # | Finding | Trigger |
|---|---|---|
| 6 | DNR pre-injection gate not wired | First DNR episode |
| 7 | HARD STOP doesn't reach memory recall | First HARD STOP event |
| 8 | Batch write lacks atomicity | First batch write call |
| 9 | Broad except on embedding fallback | First embedding service passed to life-kernel recall path |

### What Was Wrong in Previous Audit

| # | Finding | Correction |
|---|---|---|
| 10 | "4 btree DESC indexes missing" | All 4 exist on live DB |
| 11 | "P19 columns exist in DB" | P19 not deployed — no columns exist |
| 12 | "semantic_facts is empty" | 6 rows exist from manual run |

### What P19 Deployment Will Require (Source Readiness, Not Live-DB)

| # | Item | When |
|---|---|---|
| 13 | store_episode_batch must forward project_id | Before P19 deploy |
| 14 | SemanticFacts/KG ORM must add project_id | Before P19 deploy |
| 15 | Consolidation must gain project awareness | Before P19 deploy |
| 16 | P19-011 NOT NULL migration must be created | During P19 deployment |

---

## 9. Explicit Affirmation

This audit was conducted entirely **read-only via SSH to the VPS**. The following actions were NOT taken:

- No INSERT/UPDATE/DELETE on any database table
- No `alembic upgrade` or `alembic downgrade`
- No service restart, deploy, or systemctl mutation
- No raw memory content, personal data, or intimate content was printed
- No secret values, API keys, or passwords were printed (DB password was read from env but only used in PGPASSWORD environment variable, never echoed)
- All `psql` commands were `SELECT`, `\d` (describe), `EXPLAIN` (no ANALYZE execute), or `information_schema` queries
- No source code was edited on the VPS
- No docs were edited except this single output file

**Output file:** `docs/setup-evidence/legacy-audit/P3/evidence/p3-current-live-db-reconciliation-audit.md`

---

*Generated by P3 Live-DB Reconciliation Audit. READ-ONLY — no code, docs, or runtime modified except this output file.*
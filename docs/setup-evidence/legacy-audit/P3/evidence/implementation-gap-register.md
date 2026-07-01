# ⚠️ HISTORICAL PRE-P19 SNAPSHOT — SEE CURRENT RECLASSIFICATION

> **This register is a HISTORICAL PRE-P19 SNAPSHOT (dated 2026-06-25).**
> It is stale because P19 production schema was deployed on 2026-06-27.
> **Current reclassification:** [`p3-post-p19-bug-reclassification.md`](p3-post-p19-bug-reclassification.md)
> **Current live truth:** [`p3-post-p19-live-rebaseline.md`](p3-post-p19-live-rebaseline.md)

---

# P3 Implementation Gap Register

**Date:** 2026-06-25
**Agent:** Read-only audit synthesis
**Scope:** Every gap between claimed P3 completeness and actual implementation/runtime reality
**Read-only affirmation:** YES. No code modified. No DB accessed. No secrets printed.

---

## CRITICAL Gaps

| ID | Gap | Surface | Claimed | Actual | Downstream Impact | Severity |
|---|---|---|---|---|---|---|
| GAP-001 | Consolidation scheduler never runs | `src/core/main.py:22-38` (commented out) | P3-015 PASS | Dead code; `register_consolidation_job` never called | `semantic_facts` empty; P3 is single-tier (episodes only); KG ingestion cron is a no-op; P18 decay sweep also dead | [CRITICAL] |
| GAP-002 | DNR pre-injection gate dead code | `src/memory/dnr.py:385-418` (defined), `read_pipeline.py:769-777` (result dicts lack `do_not_recall` key) | DNR defense-in-depth | `verify_recall_results_dnr_free` never called in production; result dicts lack the key it checks | If SQL WHERE bypassed, DNR'd content reaches LLM with zero fallback | [CRITICAL] |
| GAP-003 | HARD STOP safe_mode never reaches life-kernel memory recall | `src/life_kernel/graph.py:262-264` (observe before decide), `src/core/main.py:272` (`_life_safe_recall=False` default) | HARD STOP protects memory | `observe_node` recalls with `safe_mode=False` before `decide_node` detects HARD STOP; raw content persists in checkpoint | Critical/Restricted content recalled during safety-critical moments; no redaction | [CRITICAL] |
| GAP-004 | SemanticFacts lack `do_not_recall` column → stale fact bypass | `src/memory/models.py:208-263`, `src/memory/consolidation.py:323` | DNR is absolute | DNR'd episode content survives in pre-consolidated semantic_facts indefinitely; no cascade tombstone | Temporal bypass: DNR mark after consolidation does not suppress existing facts | [CRITICAL] |
| GAP-005 | session_summaries ORM broken — 11 ClassificationMetaMixin columns missing from DDL | `src/memory/models.py:190` vs `alembic/versions/p5_024_add_session_summaries.py:23-63` | session_summaries usable | ORM INSERT fails with missing column error; no remediation migration exists | Any ORM write to session_summaries crashes | [CRITICAL] |
| GAP-006 | HermesMemoryBridge passes `embedding_service=None` → main write path produces episodes with NULL embedding | `src/hermes/_memory_bridge.py:279-301` | 5-signal RRF hybrid | Only FTS signal works for the primary write path; vector similarity is dead for all conversational episodes | Recall quality severely degraded; FTS-only search | [CRITICAL] |

## HIGH Gaps

| ID | Gap | Surface | Claimed | Actual | Downstream Impact | Severity |
|---|---|---|---|---|---|---|
| GAP-007 | 4 memory ORM models lack `project_id`/`project_scope` (P19 isolation broken) | `src/memory/models.py` — semantic_facts, procedural_skills, session_summaries, knowledge_graph lack columns | P19 project isolation | Columns exist in DB (p19_001 DDL) but invisible to ORM; KG recall leaks across projects | P19 multi-project isolation fails for semantic facts, skills, KG, summaries | [HIGH] |
| GAP-008 | `store_episode_batch` does not forward `project_id` to individual episodes | `src/memory/write_pipeline.py:260-277` | P19 batch writes scoped | All batch-written episodes are `project_id=NULL` (global scope) | Any P19 batch write loses project scope | [HIGH] |
| GAP-009 | `consolidate_episodes_to_facts` has zero project awareness | `src/memory/consolidation.py:275-497` | P19 consolidation scoped | No project_id filter on source episodes; no project_id on output facts; facts are global-scope | Cross-project fact leakage via consolidation | [HIGH] |
| GAP-010 | P19-011 NOT NULL migration does not exist | `alembic/versions/p19_002_project_id_not_null.py` (STUB no-op) | P19-011 will apply NOT NULL | No migration file exists; project_id remains nullable indefinitely | No DB-level project isolation enforcement | [HIGH] |
| GAP-011 | P18 decay sweep never wired | `src/memory/consolidation.py:1087-1127` (defined), never called in `main.py` | P18-002 active forgetting | `register_decay_job` is dead code; zero live call sites | FSRS scores never updated; active forgetting never triggers; episodes never archived | [HIGH] |
| GAP-012 | All 235 memory tests use FakeSession/AsyncMock; zero live-DB coverage | `tests/memory/test_*.py` | E2E verified | No test ever hits a real PostgreSQL database or embedding API | Integration bugs invisible to test suite; HNSW, FTS, pgvector never tested | [HIGH] |
| GAP-013 | `hard_stop_handler.is_safe` semantic appears inverted in prompt_loader | `src/core/services/prompt_loader.py:251-254` | safe_mode=True during hard stop | `resolved_safe_mode = bool(getattr(hard_stop_handler, "is_safe", False))` — `is_safe=True` means system is safe (normal mode), so safe_mode enables redaction; but during actual hard stop, `is_safe=False` → safe_mode=False → raw content | Redaction disabled during hard stop (inverse of intended) | [HIGH] |
| GAP-014 | KG knowledge graph enrichment bypasses safe_content pipeline | `src/hermes/_memory_bridge.py:166-192` | Safe content injection | KG results appended with `classification="Internal"` hardcoded; never processed through `build_safe_content` or classification ceiling | KG entity descriptions with sensitive content bypass all safety gates | [HIGH] |

## MEDIUM Gaps

| ID | Gap | Surface | Claimed | Actual | Downstream Impact | Severity |
|---|---|---|---|---|---|---|
| GAP-015 | Benchmark not reproducible — 20 rows, random vectors, HNSW bypassed, no pytest test | `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md` | P3-007 HNSW benchmark PASS | Seq Scan on 20 rows; no CI integration; no `pytest-benchmark`; manual shell scripts | Perf claims unvalidated; scaling unknown | [MEDIUM] |
| GAP-016 | `procedural_skills.embedding` column exists in DB but not in ORM | `alembic/versions/p5_015_add_skill_embedding.py:24` vs `src/memory/models.py:366-388` | ORM covers all columns | Column invisible to SQLAlchemy | Vector search on procedural skills impossible through ORM | [MEDIUM] |
| GAP-017 | 5 `loop_instances` columns exist in DB but not in ORM | `alembic/versions/p5_012_extend_loop_instances.py:26-32` vs `src/memory/models.py:719-758` | ORM parity | checkpoint_data, error_message, phase, phase_artifacts, parent_loop_id invisible to ORM | Checkpoint/recovery operations require raw SQL | [MEDIUM] |
| GAP-018 | `loop_instances.status` type mismatch: VARCHAR(20) vs TEXT | DDL: `VARCHAR(20)`, ORM: `Text` | DDL/ORM consistent | ORM allows >20 char status strings; PostgreSQL rejects them | ORM inserts with long status strings fail | [MEDIUM] |
| GAP-019 | `gamification` schema not in `GUINEVERE_SCHEMAS` → autogenerate ignores 6 gamification tables | `alembic/env.py:19-24` | All schemas tracked | gamification tables invisible to `alembic revision --autogenerate` | Schema drift on gamification tables undetected | [MEDIUM] |
| GAP-020 | `surveillance.events` chunk interval is 1 day (not 7 days) | `alembic/versions/e401bb5fd274_initial_schema_47_tables.py:973` vs `:1058` | 7-day chunks | First hypertable creation wins (1 day); second is no-op | 7x chunk count; affects TimescaleDB compression | [MEDIUM] |
| GAP-021 | `CommunicationLog` FK: `ondelete='SET NULL'` with `nullable=False` | `src/memory/models.py:851-855` | Clean FK | SET NULL fails on non-nullable column | FK violation on parent DELETE | [MEDIUM] |
| GAP-022 | `_is_safe_mode_blocked_content` tag serialization bug | `src/memory/read_pipeline.py:393-394` | Tag-aware blocking | `f"{tags_raw}".lower()` converts list/tuple/set to stringified Python repr; substring false positives | Over-blocking (safe direction) but fragile | [MEDIUM] |
| GAP-023 | No `content_hash` column on `semantic_facts` → O(n) dedup per fact | `src/memory/consolidation.py:648-668` | Deduplication works | Full-table scan + Python iteration; O(episodes * facts) | Consolidation performance degrades at scale | [MEDIUM] |

## LOW / COSMETIC Gaps

| ID | Gap | Surface | Claimed | Actual | Downstream Impact | Severity |
|---|---|---|---|---|---|---|
| GAP-024 | `p5_015_add_skill_embedding.py` docstring says `Revises: 3d41deeca703` but code says `down_revision = "f47a9c2e8b1d"` | `alembic/versions/p5_015_add_skill_embedding.py:5,18` | Correct docstring | Stale docstring; code is authoritative | Confusion for future maintainers | [COSMETIC] |
| GAP-025 | `models.py` memory schema comment says "8 tables" but there are 9 | `src/memory/models.py:89` | 8 tables | 9 tables (SessionSummary added by p5_024) | Comments stale | [COSMETIC] |
| GAP-026 | `projects.project_registry` has no ORM model | `alembic/versions/p19_001_project_namespaces.py:40-54` | ORM parity | Raw SQL access only | No ORM query support for project registry | [LOW] |
| GAP-027 | `episodes_started_at_idx` DESC index in ORM but never created in DDL | `src/memory/models.py:95` | Index present | Index invisible to query planner | Possible performance regression on DESC started_at queries | [LOW] |
| GAP-028 | `procedural_skills` uses ivfflat (not HNSW) — inconsistent with project standard | `alembic/versions/p5_015_add_skill_embedding.py:27-32` | HNSW everywhere | ivfflat with lists=100 | Requires `SET ivfflat.probes` at query time; different recall characteristics | [LOW] |
| GAP-029 | No `CREATE EXTENSION vector` in any migration | All migrations | Extension managed by Alembic | Extension must be pre-installed; deployment prerequisite undocumented | Initial migration fails on bare DB | [LOW] |
| GAP-030 | `prune_stale_facts` protection floor (0.7) = consolidated summary fact confidence (0.7) | `src/memory/consolidation.py:245, 601` | Safe pruning | Boundary-fragile: changing floor to 0.8 would prune summary facts | Pruning behavior fragile at threshold | [LOW] |

---

## Summary Counts

| Severity | Count |
|---|---|
| CRITICAL | 6 |
| HIGH | 8 |
| MEDIUM | 9 |
| LOW | 5 |
| COSMETIC | 2 |
| **TOTAL** | **30** |

---

## Status Verdict

**IMPLEMENTED WITH BUGS — 30 implementation gaps, 6 CRITICAL.**

P3 is substantially implemented in source code with well-designed architecture. However, the 6 CRITICAL gaps (scheduler never running, DNR gate dead code, HARD STOP not reaching memory, stale fact DNR bypass, session_summaries ORM broken, HermesMemoryBridge no-embedding write path) prevent P3 from being a clean "verified implemented" pass. These are not documentation gaps — they are actual runtime/liveness/correctness defects that affect the safety and functionality of the memory system in production.
# P3-004 through P3-010 Local Code Readiness Report

**Date:** 2026-06-02  
**Author:** Guinevere (local code research)  
**Purpose:** Determine implementation readiness for P3-004..P3-010 before planner gate  
**Method:** Filesystem/code search — no external docs, no edits  
**Scope:** src/memory/, src/core/, src/discord/, lembic/, 	ests/, pyproject.toml

---

## 1. Package/Module Layout — Current State

### 1.1 src/memory/ — Only 2 files (models exist, pipelines missing)

| File | Status | Content |
|---|---|---|
| src/memory/__init__.py | EXISTING — 1 line stub | # src/memory module |
| src/memory/models.py | COMPLETE — 1189 lines | 47 models across 12 schemas (P3-002) |
| src/memory/embeddings.py | **MISSING** | Required by P3-004/P3-005 |
| src/memory/write_pipeline.py | **MISSING** | Required by P3-009 |
| src/memory/read_pipeline.py | **MISSING** | Required by P3-010 |
| src/memory/consolidation.py | **MISSING** | Required by P3-015 |

### 1.2 src/core/ — FastAPI + services exist, no DB session factory

| Service | Status | Notes |
|---|---|---|
| main.py | EXISTS | FastAPI app with structlog, health/root endpoints |
| services/hard_stop_handler.py | EXISTS | SafetyState enum, HardStopHandler dataclass |
| services/llm_router.py | EXISTS | LLMRouter with httpx client, fallback chain |
| services/cost_tracker.py | EXISTS | Redis-based cost tracking (port 6380) |
| services/prompt_loader.py | EXISTS | File-based prompt loading with safety validation |
| services/__init__.py | EMPTY stub | — |
| models/__init__.py | EMPTY stub | — |
| config/__init__.py | EMPTY stub | No config module exists yet |
| pi/__init__.py | EMPTY stub | — |

### 1.3 src/discord/ — Bot commands exist, memory commands are stubs

- 14 files in src/discord/
- Memory slash commands (memory-search, memory-add, memory-forget, memory-export) registered as stubs returning "Coming in Phase 3" in ot.py lines 45-48
- /status shows DEGRADED_MEMORY = "⚠️ — (P3 not deployed)"

### 1.4 Other src/ Subpackages — All empty stubs

- src/financial/__init__.py — stub
- src/observability/__init__.py — stub
- src/mcp/__init__.py — stub
- src/surveillance/__init__.py — stub
- src/loops/__init__.py — stub
- src/persona/__init__.py — stub

### 1.5 lembic/

- lembic/env.py — EXISTS, async + multi-schema, imports src.memory.models.Base
- lembic/versions/ — EMPTY (no migration files generated yet)

### 1.6 	ests/

- 16 test files across 	ests/discord/, 	ests/safety/, 	ests/smoke/
- **NO memory tests exist** — no 	est_memory*.py found
- Test pattern: uses conftest.py per directory, protocol-based dependency injection
- Pytest config in pyproject.toml: 	estpaths = ["tests"], pythonpath = ["src"]

---

## 2. Column Naming — Critical Schema Reconciliation

### 2.1 embedding vs embedding_vec

| Source | Column Name | Type |
|---|---|---|
| Actual model (src/memory/models.py line 118) | **embedding** | Vector(1536) |
| HNSW index in model (line 91) | **embedding** | Uses embedding for HNSW |
| StepPrompts P3-006 line 6169 | embedding_vec | ector(1536) |
| StepPrompts P3-009 line 6233 | embedding_vec | Raw SQL insert |
| StepPrompts P3-010 line 2555-2558 | embedding_vec | Raw SQL query |
| MemorySchema v2.0 line 106 | embedding | ector(1536) (CREATE TABLE) |

**CONCLUSION: Actual model column is embedding, NOT embedding_vec. StepPrompts code snippets for P3-006/P3-009/P3-010 are stale and must be corrected.**

### 2.2 content vs aw_content

| Source | Column Name |
|---|---|
| Actual model (Episodes line 117) | **aw_content** |
| StepPrompts P3-008 line 6191 | content |
| StepPrompts P3-009 line 6232 | content |
| StepPrompts P3-010 line 6254 | content |
| StepPrompts P3-013/P3-014 | content (implied) |

**CONCLUSION: Actual model column is aw_content, NOT content. StepPrompts are stale.**

### 2.3 do_not_recall — Missing from model

| Source | Notes |
|---|---|
| Actual model (Episodes) | **DOES NOT EXIST** |
| StepPrompts P3-006 line 6175 | References do_not_recall in WHERE index |
| StepPrompts P3-010 line 6257 | References do_not_recall in query |
| StepPrompts P3-013 | DNR feature described |
| MemorySchema v2.0 | Not mentioned |

**CONCLUSION: do_not_recall must be added to the Episodes model as a new column (likely Boolean with server_default=text("false")).**

### 2.4 search_vector tsvector — Missing from model

| Source | Notes |
|---|---|
| Actual model (Episodes) | **DOES NOT EXIST** |
| StepPrompts P3-008 line 6189 | search_vector tsvector column |
| StepPrompts P3-008 line 6191 | 	o_tsvector('english', content) |

**CONCLUSION: search_vector must be added to Episodes model as Mapped[Optional[str]] mapped to TSVECTOR (custom type or Text with dialect type).**

### 2.5 classification — EXISTS in ClassificationMetaMixin

The ClassificationMetaMixin (line 50) provides:
- classification, purpose, source, etention_class, etention_until, ccess_policy, encryption_profile, deletion_state, key_id, key_version, created_at, updated_at

StepPrompts P3-009 references a classification column — this is provided by the mixin. The StepPrompts source column is also provided by the mixin (line 54).

### 2.6 Episodes Composite Primary Key

Actual model (lines 98-105): id UUID + started_at TIMESTAMPTZ as composite PK. This is a hypertable prerequisite — TimescaleDB requires time-based PK.

### 2.7 Missing: TimescaleDB hypertable declaration

The MemorySchema v2.0 §2.1 specifies hypertable conversion:
`sql
SELECT create_hypertable('memory.episodes', 'started_at');
`

The actual model class does NOT include any hypertable DDL logic. This must be handled in the migration script (StepPrompts P3-002 note says "DDL in migration").

---

## 3. Existing Patterns — What P3-004..P3-010 Must Follow

### 3.1 Logging Style

Two logging patterns exist:
- **core/ services**: structlog.get_logger() module-level (preferred for new memory modules)
- **discord/ modules**: logging.getLogger(__name__) 

The StepPrompts P3-004/P3-005/P3-009/P3-010 code snippets use structlog.get_logger() — correct, consistent with core services.

### 3.2 Async DB Patterns

- lembic/env.py: Uses sync_engine_from_config + syncpg — this is the only async DB pattern reference in codebase
- **NO AsyncSession factory, sessionmaker, or sync_session exists** anywhere in src/
- StepPrompts P3-009/P3-010 use raw db.execute()/db.fetch() — NOT SQLAlchemy ORM
- There is no existing DB utility module or helper

**GAP: P3-004..P3-010 will need either:**
1. A Database connection/session module (recommended — create src/memory/database.py)
2. Or use raw syncpg directly as StepPrompts suggest

The pyproject.toml includes both sqlalchemy[asyncio] and syncpg as dependencies.

### 3.3 Error Handling

- StepPrompts P3-009/P3-010 code has NO error handling
- Project standard (from AGENTS.md): no empty catches, no type suppression
- hard_stop_handler.py uses logger.warning + structured events — this is the pattern to follow

### 3.4 Imports/Exports

- src/memory/__init__.py is empty — new modules can add rom .embeddings import embed_text, embed_batch
- src/core/__init__.py is empty — services import directly from their modules

### 3.5 Database Connection Config

- Port: 5433 (Guinevere PostgreSQL, ADR-027)
- User: guinevere_core
- Password: via GUINEVERE_DB_PASSWORD env var (SOPS decrypted)
- Redis: port 6380
- Alembic env.py imports Base from src.memory.models

---

## 4. Missing Modules — P3-004 Through P3-010

### P3-004: src/memory/embeddings.py

Must create:
- embed_text(text: str) -> list[float] — single text embedding via 9Router
- embed_batch(texts: list[str]) -> list[list[float]] — batch embedding
- Fallback: SentenceTransformers ll-MiniLM-L6-v2 when 9Router unavailable
- Uses: openai SDK pointing to http://localhost:20128/v1
- Model: 	ext-embedding-3-small (1536 dimensions)
- **Col name constraint**: Must use column name embedding (not embedding_vec)

### P3-005: Embedding Pipeline (same file as P3-004)

- Verified by test: output dimensions == 1536

### P3-006: pgvector HNSW Index

- Already declared in Episodes.__table_args__ (lines 89-95) and SemanticFacts.__table_args__ (lines 137-143)
- Uses column name embedding with ector_cosine_ops, m=16, ef_construction=128
- **No ALTER TABLE ADD COLUMN needed** — column already exists
- **do_not_recall column does not exist** — must be added to model first
- Migration must add do_not_recall column if implementing the partial index

### P3-007: HNSW Parameter Tuning

- Benchmark-only step — no code change needed unless ef_search tuning
- Existing HNSW params: m=16, ef_construction=128

### P3-008: tsvector FTS Setup

- **search_vector column missing from Episodes model** — must be added
- Trigger function and trigger SQL must go in migration
- Update logic: 	o_tsvector('english', raw_content) (note: aw_content, not content)

### P3-009: src/memory/write_pipeline.py

Must create:
- store_episode(db, content, source, classification, importance, metadata) — async
- **SQL column fix**: Use embedding not embedding_vec, aw_content not content
- Uses structlog logger
- No db session infrastructure exists — either pass syncpg.Connection or create session module

### P3-010: src/memory/read_pipeline.py

Must create:
- ecall_memories(db, query, limit, exclude_dnr) — async
- **SQL column fix**: Use embedding not embedding_vec, aw_content not content, add do_not_recall filter
- Vector search: ORDER BY embedding <=> ::vector (not embedding_vec <=>)
- Return: ranked results with similarity score

---

## 5. Implementation Constraints Summary

| Constraint | Detail |
|---|---|
| Column embedding (not embedding_vec) | Model line 118 — all HNSW/SQL references must use embedding |
| Column aw_content (not content) | Model line 117 |
| Column do_not_recall does not exist | Must add to Episodes model |
| Column search_vector does not exist | Must add to Episodes model |
| No async session/DB factory exists | Must create or use raw asyncpg |
| No .env or config module | Must create or read from env vars |
| Logging: use structlog.get_logger() | Consistent with core services |
| Error handling: no empty catches | Follow AGENTS.md |
| Type safety: strict = true in mypy | No s any, no # type: ignore, no @ts-ignore |
| Tests: no existing memory tests | Must create test suite |
| Migration: alembic/versions/ empty | Migration must add new columns + indexes |
| Discord stubs reference P3 | _STUB_PHASE in ot.py maps to phase 3 |
| No migration files exist yet | P3-002 migration (initial_schema_47_tables) must be created first |

---

## 6. Dependency Map for P3-004 Through P3-010

`
P3-002 (47 models) ──→ P3-003 (verify migration) ──→ P3-004 (embeddings.py)
                                                          │
                                                          ▼
                                                    P3-005 (embed test)
                                                          │
                                                          ▼
                                              P3-006 (HNSW index via migration)
                                              P3-007 (tuning — benchmark only)
                                              P3-008 (tsvector via migration)
                                                          │
                                                          ▼
                                              P3-009 (write_pipeline.py)
                                              P3-010 (read_pipeline.py)
`

**Sequential requirements:**
- P3-004..P3-008 depend on P3-003 (migration verified)
- P3-006: must be a migration step (does not exist)
- P3-008: must be a migration step (does not exist)
- P3-009..P3-010 depend on P3-004 (embeddings exist)

**Parallel opportunities:**
- P3-004 and P3-008 are independent (embeddings.py vs migration)
- P3-009 and P3-010 are independent (write vs read)

---

## 7. Ready to Proceed Assessment

### Green (ready, no blockers)

| Item | Status |
|---|---|
| structlog available in dependencies | ✅ pyproject.toml line 19 |
| sqlalchemy[asyncio] + syncpg available | ✅ lines 10-11 |
| openai SDK installable | ✅ (P3-004 dependency) |
| Model Base and Episodes class exist | ✅ src/memory/models.py |
| embedding column type Vector(1536) | ✅ line 118 |
| HNSW index syntax in model | ✅ lines 89-95 |
| Alembic async env.py | ✅ lembic/env.py |
| Logging pattern (structlog) | ✅ consistent with core |
| Discord stub commands reference Phase 3 | ✅ ot.py _STUB_PHASE |

### Yellow (need attention, not blockers)

| Item | Impact | Action Needed |
|---|---|---|
| StepPrompts column names are stale (embedding_vec, content) | Must NOT follow StepPrompts SQL verbatim | Use actual model column names |
| No async session factory | P3-009/010 need DB connection pattern | Create src/memory/database.py or document pattern |
| do_not_recall column missing | P3-006/P3-010/P3-013 need it | Add to Episodes model + migration |
| search_vector column missing | P3-008 needs it | Add to Episodes model + migration |
| hypertable DDL not in model | Migration must add create_hypertable | Handle in migration script |

### Red (blockers for this batch)

| Blocking Issue | Blocks | Resolution |
|---|---|---|
| No migration files exist in lembic/versions/ | All P3 steps after model creation | Complete P3-002 migration first |
| P3-002 not yet verified via P3-003 | All P3-004..P3-010 | Complete P3-003 verification |

**Verdict: P3-004 through P3-010 are implementation-ready after P3-002/P3-003 complete, provided all column naming corrections and missing column additions are applied. The primary implementation work is creating new files (embeddings.py, write_pipeline.py, ead_pipeline.py), adding missing columns to the Episodes model (do_not_recall, search_vector), and correcting stale SQL references in StepPrompts code snippets.**

---

*End of research report.*

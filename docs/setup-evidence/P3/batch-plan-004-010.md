# P3 Batch Plan — Steps P3-004 through P3-010

**File:** `docs/setup-evidence/P3/batch-plan-004-010.md`
**Status:** Planning Gate — Binding for Implementation
**Date:** 2026-06-02
**Author:** Guinevere (Parent Orchestrator)
**Target Steps:** P3-004, P3-005, P3-006, P3-007, P3-008, P3-009, P3-010
**Phase:** P3 (Memory System) — batch 2 of ~6
**Previous Batch:** `docs/setup-evidence/P3/batch-plan-001-003.md`

---

## Loaded Skills and Why

| Skill | Reason |
|-------|--------|
| `ocs-delegation-gate` | Mandatory for category/task delegation discipline. This batch delegates 7 sequential implementation steps, each requiring explicit `load_skills` mapping, verification criteria, and one-subagent-per-step. |
| `ocs-markdown-autofix` | This planner file and all 7 evidence markdown files must pass markdownlint zero-errors. Enforces markdown table pipe safety, heading semantics, and list continuity. |

---

## Master Todo / Dependency Map

### Sequential Execution Mandate

User requires **strict sequential** step execution: step N+1 only after step N auditor PASS, even if steps are independently possible.

```
P3-004 (install deps, cache MiniLM)
  |
  v
P3-005 (create embeddings.py -- code only)
  |
  v
P3-006 (verify existing HNSW indexes only)
  |
  v
P3-007 (benchmark/smoke HNSW -- existing or rollback-only seed data)
  |
  v
P3-008 (add search_vector tsvector, GIN index, do_not_recall via migration)
  |
  v
P3-009 (create write_pipeline.py -- store_episode async)
  |
  v
P3-010 (create read_pipeline.py -- hybrid recall async)
```

### Dependency Table

| Step | Depends On | Required By | Risk | Effort |
|------|-----------|-------------|------|--------|
| P3-004 | P3-003 (PASS) | P3-005 | Low | ~30m |
| P3-005 | P3-004 | P3-009, P3-010 | Medium (consent gate) | ~2h |
| P3-006 | P3-005 (code only, not runtime) | P3-007 | Low (verification-first) | ~1.5h |
| P3-007 | P3-006 | P3-008 | Low | ~1h |
| P3-008 | P3-007 (sequential gate) | P3-009 (search_vector, do_not_recall) | Medium | ~1.5h |
| P3-009 | P3-005, P3-008, backup checkpoint | P3-010 | High (write path) | ~3h |
| P3-010 | P3-009, P3-005 | P3-011+ | High (read path) | ~4h |

### P3 Progress Impact

| Before | After |
|--------|-------|
| 3/19 (P3-001..003 PASS) | 10/19 (P3-001..010 complete) |
| $2/mo allocation | $2/mo allocation (embedding API amortized) |

---

## Planner Parallelism Decision

**Decision: STRICT SEQUENTIAL.** All 7 steps execute one after another. Step N+1 begins only after:
1. Step N implementation completes
2. Parent verifies all claimed files, diagnostics, and acceptance criteria
3. Independent auditor sub-agent writes auditor-gate report for step N
4. Auditor report = PASS
5. Evidence directory created with minimum schema

Rationale: User directive + P3-005 consent gate blocks downstream steps until resolved.

---

## Research Inputs

The following research reports were read and synthesized for this plan:

| Report | Path | Key Findings Used |
|--------|------|-------------------|
| Local Code Readiness | `docs/setup-evidence/P3/research/local-memory-code-readiness.md` | Column name mapping (embedding NOT embedding_vec; raw_content NOT content); missing do_not_recall and search_vector columns; no async session factory exists |
| Docs/ADR Constraints | `docs/setup-evidence/P3/research/docs-adr-step-constraints.md` | 7 conflict analyses (C-01 to C-07); default classification must be Restricted; ef_construction=128 per ADR-009 |
| Runtime Evidence Readiness | `docs/setup-evidence/P3/research/runtime-evidence-readiness.md` | P3-006 HNSW indexes already exist (verification-first); backup checkpoint 13159f70 confirmed; migration e401bb5fd274 is VPS truth |
| SentenceTransformers Model Selection | `docs/setup-evidence/P3/research/sentence-transformers-model-selection.md` | No 1536-dim local ST model exists; all-MiniLM-L6-v2 (384d) is cache evidence only, must NOT write to vector(1536) |
| OpenAI-Compatible Embedding API | `docs/setup-evidence/P3/research/openai-compatible-embedding-api.md` | 9Router-native HTTP client preferred over OpenAI SDK; dimension validation critical; never f-string SQL |
| pgvector HNSW Cosine | `docs/setup-evidence/P3/research/pgvector-hnsw-cosine.md` | HNSW with vector_cosine_ops requires `<=>` operator; ef_search=100; maintenance_work_mem for index build |
| Postgres FTS tsvector | `docs/setup-evidence/P3/research/postgres-fts-tsvector.md` | Use GENERATED ALWAYS AS STORED not trigger; setweight(A=title, B=summary, D=raw_content); GIN not GiST |
| Async Memory Pipeline Patterns | `docs/setup-evidence/P3/research/async-memory-pipeline-patterns.md` | SQLAlchemy AsyncSession pattern; one session per task; ThreadPoolExecutor for ST; RRF k=60 fusion |
| Hybrid Ranking Safety | `docs/setup-evidence/P3/research/hybrid-ranking-safety.md` | P3-010 minimum: RRF + recency + importance + DNR + classification ceiling + safe-mode gate |
| Oracle ADR-009 Model Review | `docs/setup-evidence/P3/research/oracle-adr009-model-selection-review.md` | APPROVED WITH CONDITIONS: Keep 1536 schema; 9Router-native client; fix 384-dim fallback; consent gate before P3-005 |

---

## Binding Decisions

| ID | Decision | Source | Rationale |
|----|----------|--------|-----------|
| BD-01 | Primary embedding: text-embedding-3-small 1536 via 9Router | ADR-009, Oracle Review | Schema locked at vector(1536); changing requires destructive table rebuild |
| BD-02 | Local ST all-MiniLM-L6-v2 is cache evidence only | Oracle Review, Model Selection | 384-dim cannot write to vector(1536); must not insert into embedding column |
| BD-03 | No direct OpenAI API calls | ADR-009, ADR-005 | All routing through 9Router; use native 9Router HTTP client |
| BD-04 | HNSW m=16, ef_construction=128 | ADR-009, models.py line 94 | Already in model; StepPrompts value 64 is stale |
| BD-05 | Query ef_search=100 | ADR-009, pgvector research | Within ADR-009 range (64-128) |
| BD-06 | Column is embedding, not embedding_vec | Actual model, Local Code Readiness | All SQL/ORM references use embedding |
| BD-07 | Column is raw_content, not content | Actual model, Local Code Readiness | StepPrompts SQL snippets are stale |
| BD-08 | P3-006 is verification-first | Runtime Evidence Readiness | HNSW indexes already exist from P3-002 migration |
| BD-09 | P3-008 adds search_vector tsvector generated + GIN | Postgres FTS Research | Use GENERATED ALWAYS AS STORED, not trigger |
| BD-10 | P3-008 adds do_not_recall boolean column | Local Code Readiness | Missing from model; needed for DNR filtering |
| BD-11 | Default classification for episodic: Restricted | DataGovernance | StepPrompts value Internal is incorrect; DataGovernance sec5 mandates Restricted |
| BD-12 | P3-010 minimum hybrid: vector+FTS+recency+importance+DNR/gates | Hybrid Ranking Safety, ADR-009 | Full weighted RRF deferred to P3-011 |
| BD-13 | Use 9Router-native HTTP client (httpx/aiohttp) | Oracle Review | Replace OpenAI SDK to enforce no-direct-OpenAI policy |
| BD-14 | Backup checkpoint 13159f70 required before P3-009 | Runtime Evidence | Each write pipeline execution must verify checkpoint exists |

---

## Consent-Safety Gate (Before P3-005)

### Issue

Embedding memory content (episodes, semantic facts, persona data) via 9Router to OpenRouter to OpenAI text-embedding-3-small API sends Restricted/Confidential classified data to an external provider for vectorization. Per DataGovernance Policy (sec 4.3) and PersonaSafetyPolicy (sec 12.2), this requires explicit Faiz acknowledgment.

### Gate Condition

**P3-005 IS BLOCKED** until Faiz explicitly acknowledges the privacy trade-off. Evidence must be written to:

`docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md`

Minimal evidence content:
- Faiz acknowledgment that Restricted/Confidential memory content will be sent to OpenAI embedding API via 9Router to OpenRouter
- Faiz acknowledgment that embedding APIs are stateless and OpenAI does not retain/train on API inputs
- Faiz consent or explicit override
- Date and method of acknowledgment (Discord DM, session message, or signed file)

### If No Consent Found in Existing Docs

**Action:** The parent orchestrator must ask Faiz directly via a question tool prompt before implementing P3-005. The plan marks P3-005 as blocked/pending until this consent evidence file exists.

### Execution Path If Consented

Once `faiz-consent-embedding-privacy.md` exists, unblock P3-005 and continue sequential execution.

### Execution Path If Denied

If Faiz denies external embedding processing:
1. Pivot to local-only embedding strategy
2. Create a superseding ADR (ADR-009-A) switching to local SentenceTransformers primary
3. Define new dimension (384 or 768)
4. Plan destructive table rebuild for vector(N) columns
5. This is a Large effort -- escalate to Faiz for re-prioritization

---

## Collision Scan

### Shared Writers

| Resource | Collision Risk | Mitigation |
|----------|---------------|------------|
| `src/memory/models.py` | P3-008 adds search_vector, do_not_recall | Parent reads model before P3-008; single owner (P3-008 sub-agent) adds columns; P3-006 verifier checks model consistency |
| `src/memory/__init__.py` | P3-005, P3-009, P3-010 add exports | All add to same file -- sequential execution prevents collision; single owner per step |
| `src/memory/embeddings.py` | P3-005 only | Single owner |
| `src/memory/write_pipeline.py` | P3-009 only | Single owner |
| `src/memory/read_pipeline.py` | P3-010 only | Single owner |
| Alembic migration files | P3-008 adds migration | Run on VPS where alembic/versions/ exists; single revision |
| PROGRESS.md | Parent updates after each step | Parent-only edit |
| CHECKLIST.md | Parent updates after each step | Parent-only edit |
| Evidence dirs | Each step writes to own `docs/setup-evidence/P3/STEP-P3-0NN/` | No collision -- unique path per step |

### Safety Boundary Docs

| Document | Rule |
|----------|------|
| ADR-009 | Read-only reference -- no edits |
| PersonaSafetyPolicy | Read-only -- P3-010 safe-mode gate must comply but not edit |
| DataGovernance Policy | Read-only -- classification defaults must comply |
| ConsentRevocationPolicy | Read-only -- DNR filter must comply |

---

## Pre-Step Aizanta Health and Resource Checks

Before EVERY implementation step, verify:

### Canonical Ports (Shared VPS)

| Service | Aizanta | Guinevere | Verification Command |
|---------|---------|-----------|---------------------|
| PostgreSQL | 5432 | **5433** | `pg_isready -h 127.0.0.1 -p 5432` (Aizanta OK); `pg_isready -h 127.0.0.1 -p 5433` (Guinevere OK) |
| PgBouncer | 5433 | **5434** | `pg_isready -h 127.0.0.1 -p 5434` |
| Redis | 6379 | **6380** | `redis-cli -p 6380 PING` (expects NOAUTH or PONG) |
| 9Router | N/A | **20128** | `curl -s http://localhost:20128/v1/models` (returns model list) |

### Aizanta Health Check

```bash
# Quick pre-step verification -- must PASS before any implementation
pg_isready -h 127.0.0.1 -p 5432
# Expected: 127.0.0.1:5432 - accepting connections
```

### Guinevere Service Check

```bash
# Verify required services are running before each step
systemctl is-active guinevere-core 2>/dev/null || docker ps --filter name=guinevere-postgres
```

### Resource Budget

- Guinevere cgroup: 8GB RAM / 2 CPU cores (guinevere.slice)
- Aizanta must not be affected: check `free -h` and `uptime` before each step
- Disk: at least 40GB free

---

## Implementation Design

### P3-004: Dependency Installation

**What:** Install `sentence-transformers` and required pip packages in the project venv. Download `all-MiniLM-L6-v2` model cache for offline warm-start.

**Key commands:**
```bash
uv pip install sentence-transformers>=3.0 openai
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('all-MiniLM-L6-v2')"
```

**Evidence:** Model directory exists at `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/`. Note: MiniLM is cache-only; 384-dim vectors must NOT be written to `vector(1536)` columns.

### P3-005: Embedding Pipeline (embeddings.py)

**What:** Create `src/memory/embeddings.py` with:
- `EmbeddingService` class using 9Router-native HTTP client (httpx), not OpenAI SDK
- `embed_text(text: str) -> list[float]` returning 1536-dim vectors
- `embed_batch(texts: list[str]) -> list[list[float]]` for batch
- Dimension validation (expects 1536, raises on mismatch)
- Tenacity retry with exponential backoff (6 attempts)
- Truncate input to 8000 chars
- structlog logging (no embedding data in logs)
- No direct OpenAI API key exposure

**Contract:** Import via `from src.memory.embeddings import EmbeddingService`. API key loaded from SOPS-decrypted env var (GUINEVERE_9ROUTER_API_KEY).

### P3-006: pgvector HNSW Index (Verification-First)

**What:**
1. Verify existing HNSW indexes from P3-002 exist on VPS via pg_indexes query
2. If missing, stop and report before creating indexes because `CREATE INDEX CONCURRENTLY` is CPU-intensive and requires resource approval/timing
3. Verify parameters via `pg_class.reloptions`
4. Verify `EXPLAIN (ANALYZE)` shows an index-eligible cosine query shape (`ORDER BY embedding <=> ... LIMIT N`); for tiny tables, document if planner chooses seq scan and include `enable_seqscan=off` debug evidence
5. Do not edit `models.py` in P3-006; `do_not_recall` is added with the P3-008 migration/model update

### P3-007: HNSW Parameter Tuning

**What:**
1. Run HNSW benchmark/smoke using existing rows if available; if no rows exist, insert rollback-only seed rows inside a controlled transaction or dedicated test cleanup path
2. Run benchmark: `SET hnsw.ef_search = 100; EXPLAIN ANALYZE SELECT ...`
3. Target: p95 < 200ms per CHECKLIST.md for HNSW-only smoke; document insufficient data volume if the database is too small for meaningful p95
4. Document ef_search sensitivity (40, 100, 200) vs recall vs latency

### P3-008: tsvector FTS + do_not_recall Migration

**What:**
1. Add `search_vector tsvector` GENERATED ALWAYS AS STORED column to Episodes model
2. Add `do_not_recall Boolean` column in both `models.py` and the new migration
3. Create GIN index on search_vector
4. Use `setweight(to_tsvector('english', coalesce(title, '')), 'A') || setweight(to_tsvector('english', coalesce(summary, '')), 'B') || setweight(to_tsvector('english', coalesce(raw_content, '')), 'D')`
5. Run migration on VPS via `alembic revision --autogenerate` then `alembic upgrade head`
6. Verify with FTS query returning true

### P3-009: Memory Write Pipeline (write_pipeline.py)

**What:** Create `src/memory/write_pipeline.py` with:
- Async `store_episode(session, content, source, classification='Restricted', importance=5, metadata=None) -> UUID`
- Generates 1536-dim embedding via EmbeddingService.aembed()
- Inserts into `memory.episodes` using SQLAlchemy ORM
- Classification default `Restricted` per DataGovernance
- Backup checkpoint guard: verify 13159f70 exists before write
- structlog logging
- Tenacity retry for transient DB errors

**Column mapping (corrected):** `raw_content` (not content), `embedding` (not embedding_vec).

### P3-010: Memory Read Pipeline (read_pipeline.py)

**What:** Create `src/memory/read_pipeline.py` with:
- Async `recall_memories(session, query_text, limit=20, exclude_dnr=True, safe_mode=False, principal='guinevere_core') -> list[dict]`
- Generates query embedding via EmbeddingService.aembed()
- Minimum hybrid: vector cosine (embedding <=>) + FTS (search_vector @@) + recency (exponential decay, 90d half-life) + importance factor
- Safety gates: DNR exclusion, classification ceiling per principal, safe-mode content substitution
- RRF fusion (k=60) for score combination
- Token budget enforcement (4,000 tokens per cycle)
- Returns: id, safe_content, classification, importance, created_at, combined_score, is_summarized
- NO direct OpenAI calls -- 9Router only
- structlog logging (no embedding vectors or raw content in logs)

---

## One-Subagent-Per-Step Delegation Assignments

### P3-004: Install Dependencies

| Field | Value |
|-------|-------|
| Sub-agent | explore agent (code+sys execution) |
| Task | Install sentence-transformers, openai pip packages; download all-MiniLM-L6-v2 cache |
| Expected Outcome | uv pip install succeeds; model cached at ~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/ |
| MUST DO | Install CPU-only torch; verify import; create evidence dir |
| MUST NOT DO | Write 384-dim vectors into any table; edit models.py; edit PROGRESS.md |
| Verification | `python -c "from sentence_transformers import SentenceTransformer; m=SentenceTransformer('all-MiniLM-L6-v2'); print(m.get_sentence_embedding_dimension())"` returns 384 |

### P3-005: Create Embedding Pipeline

| Field | Value |
|-------|-------|
| Sub-agent | hephaestus (code creation) |
| Task | Create src/memory/embeddings.py with EmbeddingService class; 9Router-native HTTP client |
| Expected Outcome | Working embed_text() returns 1536-dim vector; embed_batch() returns batch |
| MUST DO | Use httpx/aiohttp not OpenAI SDK; dimension validation; tenacity retry; structlog; 8000-char truncation |
| MUST NOT DO | Write to DB; edit models.py; expose API keys in logs; use as any or type ignores |
| Verification | `python -c "import sys; sys.path.insert(0,'src'); from src.memory.embeddings import EmbeddingService; e=EmbeddingService('http://localhost:20128/v1'); v=e.embed('test'); print(len(v))"` returns 1536 |
| Consent Gate | BLOCKED until faiz-consent-embedding-privacy.md exists |

### P3-006: Verify HNSW Indexes

| Field | Value |
|-------|-------|
| Sub-agent | DB verifier/executor |
| Task | Verify existing HNSW indexes on VPS and document index/query evidence |
| Expected Outcome | HNSW indexes confirmed with m=16 ef_construction=128 and vector_cosine_ops; no duplicate embedding_vec index exists |
| MUST DO | Connect only to Guinevere PG 5433; query pg_indexes/pg_class; capture EXPLAIN evidence; create evidence dir |
| MUST NOT DO | Drop/recreate existing indexes if they exist; change embedding column; edit models.py; touch Aizanta PG 5432 |
| Verification | `psql -d guinevere -c "SELECT indexdef FROM pg_indexes WHERE indexname LIKE '%hnsw%'"` shows correct params and no stale `embedding_vec` |

### P3-007: HNSW Benchmark

| Field | Value |
|-------|-------|
| Sub-agent | explore agent (benchmark execution) |
| Task | Insert test episodes; benchmark HNSW search with ef_search=40, 100, 200 |
| Expected Outcome | Benchmark report with ef_search sensitivity; p95 < 200ms recommendation |
| MUST DO | Use SET hnsw.ef_search; EXPLAIN ANALYZE; document results |
| MUST NOT DO | Edit source code; modify indexes; change production data |
| Verification | Benchmark report exists at docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md |

### P3-008: tsvector FTS Migration

| Field | Value |
|-------|-------|
| Sub-agent | hephaestus (model edit + migration) |
| Task | Add search_vector tsvector generated column + GIN index + do_not_recall column migration |
| Expected Outcome | New Alembic revision on VPS; search_vector populated; GIN index created; FTS query works |
| MUST DO | Use GENERATED ALWAYS AS STORED with setweight; create GIN index; use websearch_to_tsquery |
| MUST NOT DO | Use trigger approach; use content instead of raw_content; edit existing migration |
| Verification | `python -c "from src.memory.models import Episodes; print(hasattr(Episodes, 'search_vector'))"` True; `psql -d guinevere -c "SELECT to_tsvector('english','test') @@ to_tsquery('english','test')"` returns t |

### P3-009: Write Pipeline

| Field | Value |
|-------|-------|
| Sub-agent | hephaestus (code creation) |
| Task | Create src/memory/write_pipeline.py with store_episode() async function |
| Expected Outcome | store_episode writes to memory.episodes with embedding; returns UUID; backup checkpoint guard works |
| MUST DO | Use SQLAlchemy AsyncSession; 9Router-native embedding; classification=Restricted default; checkpoint guard; structlog; tenacity retry |
| MUST NOT DO | Use raw asyncpg without ORM; expose secrets; skip checkpoint guard; use as any |
| Verification | `psql -d guinevere -c "SELECT id FROM memory.episodes ORDER BY created_at DESC LIMIT 1"` returns UUID |

### P3-010: Read Pipeline

| Field | Value |
|-------|-------|
| Sub-agent | hephaestus (code creation) |
| Task | Create src/memory/read_pipeline.py with recall_memories() async function |
| Expected Outcome | Hybrid recall returns ranked results with DNR/classification/safe-mode gates |
| MUST DO | SQLAlchemy async; 9Router embedding; RRF fusion k=60; recency decay (90d); importance factor; DNR exclusion; classification ceiling; safe-mode substitution; 4K token budget |
| MUST NOT DO | Direct OpenAI; expose raw Critical content in safe-mode; skip DNR filter; use as any |
| Verification | `python -c "import sys; sys.path.insert(0,'src'); from src.memory.read_pipeline import recall_memories; print('OK')"` passes import |

---

## Rollback per Step

| Step | Rollback | Risk |
|------|----------|------|
| P3-004 | `uv pip uninstall sentence-transformers openai`; clear HF cache | Low -- stateless install |
| P3-005 | `git checkout src/memory/embeddings.py`; or delete file | Low -- file only, no DB changes |
| P3-006 | No source rollback expected; remove/annotate verification artifacts only if rerunning | Low -- verification only; no index drop |
| P3-007 | Delete benchmark evidence dir | Low -- read-only benchmark |
| P3-008 | `alembic downgrade -1` (drops search_vector, do_not_recall, GIN); revert models.py | Low -- DDL only, no data loss |
| P3-009 | `DELETE FROM memory.episodes` (test data); `git checkout src/memory/write_pipeline.py` | Low -- no production data yet |
| P3-010 | `git checkout src/memory/read_pipeline.py` | Low -- file only |

---

## Auditor Matrix per Step

| Step | Auditor Type | Report Path | Check Points | PASS Gate |
|------|-------------|-------------|--------------|-----------|
| P3-004 | Implementation auditor | `docs/setup-evidence/P3/STEP-P3-004/auditor-gate.md` | Packages installed correctly; model cached; no DB changes; no 384-dim writes; diagnostics clean | All checks PASS |
| P3-005 | Implementation auditor | `docs/setup-evidence/P3/STEP-P3-005/auditor-gate.md` | EmbeddingService exists; 9Router-native client (not OpenAI SDK); dimension validation; retry logic; no secrets in code; structlog usage; lsp_diagnostics clean | All checks PASS |
| P3-006 | DB implementation auditor | `docs/setup-evidence/P3/STEP-P3-006/auditor-gate.md` | HNSW indexes verified on VPS; m=16 ef_construction=128 confirmed; no stale embedding_vec references; no unintended model/schema edits; diagnostics clean | All checks PASS |
| P3-007 | Performance auditor | `docs/setup-evidence/P3/STEP-P3-007/auditor-gate.md` | Benchmark report exists; ef_search sensitivity documented; p95 recommendation made; no code changes | Report exists + plausible target |
| P3-008 | DB implementation auditor | `docs/setup-evidence/P3/STEP-P3-008/auditor-gate.md` | search_vector as GENERATED ALWAYS; GIN index created; setweight correct; raw_content used (not content); FTS query returns true; alembic migration valid; lsp_diagnostics clean | All checks PASS |
| P3-009 | Implementation auditor | `docs/setup-evidence/P3/STEP-P3-009/auditor-gate.md` | store_episode async; EmbeddingService integration; Restricted default; checkpoint guard; structlog; tenacity; no secrets; no type suppression; lsp_diagnostics clean | All checks PASS |
| P3-010 | Implementation auditor | `docs/setup-evidence/P3/STEP-P3-010/auditor-gate.md` | recall_memories async; hybrid (vec+FTS+recency+importance); RRF k=60; DNR exclusion; classification ceiling; safe-mode substitution; token budget; no direct OpenAI; lsp_diagnostics clean | All checks PASS |

### Re-Audit Protocol

If auditor returns NEEDS REVIEW or FAIL:
1. Document the finding
2. Parent fixes the issue
3. Re-audit via `task_id` continuation of the same auditor agent
4. Repeat until PASS or documented false-positive

---

## Evidence Minimum Schema

Every step must create a verification report at `docs/setup-evidence/P3/STEP-P3-0NN/verification.md` with these 12 sections:

| Section | Content |
|---------|---------|
| 1 — What Was Done | Brief description of the step |
| 2 — Files Changed | List of files created/modified |
| 3 — Validation Results | Commands run and their outputs |
| 4 — Evidence Artifacts | Paths to evidence files |
| 5 — Doc-Sync Impact | PROGRESS.md, CHECKLIST.md updates needed |
| 6 — Boundary Compliance | Boundary proof: no persona drift, no consent violation, no Y6, no HARD STOP bypass |
| 7 — Rollback / Re-run Safety | Rollback command and safety notes |
| 8 — Design Decisions / Caveats | Binding decisions applied, any deviations |
| 9 — Auditor Gate | Auditor report path and verdict |
| 10 — Security Scan | No secrets exposed, no type suppression, no empty catches |
| 11 — Acceptance Criteria Mapping | Which ACs are satisfied (AC-MEM-001, etc.) |
| 12 — Footer | Date, author, next action |

### Evidence Directories

| Step | Dir |
|------|-----|
| P3-004 | `docs/setup-evidence/P3/STEP-P3-004/` |
| P3-005 | `docs/setup-evidence/P3/STEP-P3-005/` |
| P3-006 | `docs/setup-evidence/P3/STEP-P3-006/` |
| P3-007 | `docs/setup-evidence/P3/STEP-P3-007/` |
| P3-008 | `docs/setup-evidence/P3/STEP-P3-008/` |
| P3-009 | `docs/setup-evidence/P3/STEP-P3-009/` |
| P3-010 | `docs/setup-evidence/P3/STEP-P3-010/` |

---

## Doc-Sync Requirements

After each step completes with PASS auditor:

1. **PROGRESS.md**: Mark step [x], update counter (e.g., 4/19), add step to completed list
2. **CHECKLIST.md**: Mark step verification in Section 5.2
3. **Evidence**: Write verification.md and auditor-gate.md in step evidence dir
4. **Cost tracking**: Update if embedding API costs change

---

## Caveats and Risk Notes

1. **P3-005 consent gate is a hard blocker.** Plan assumes Faiz will consent; if not, the entire batch replan is needed.
2. **Local Alembic gap:** Migration operations must run on VPS where alembic/versions/ exists. SSH access required for P3-008.
3. **9Router must be running** for P3-005 embedding tests and P3-009/P3-010 integration tests. Verify before each step.
4. **No production data yet.** All inserts in P3-009 write test episodes. No risk to real data.
5. **HNSW ef_construction discrepancy:** StepPrompts says 64, model says 128, ADR-009 says 128. Plan binds to 128. Any implementation using 64 will FAIL auditor.
6. **Column name corrections are critical.** Using `content` or `embedding_vec` in SQL will fail at runtime. Sub-agents must be explicitly warned.
7. **Budget is within $2/mo P3 allocation.** Embedding API calls via 9Router cost ~$0.02/1M tokens. At expected P3 volume, well within budget.

---

## Footer

### Execution Checklist

- [ ] P3-004 install + cache + verify
- [ ] P3-005 create embeddings.py (blocked until consent)
- [ ] P3-006 verify HNSW indexes
- [ ] P3-007 benchmark HNSW + report
- [ ] P3-008 add search_vector + GIN + migration
- [ ] P3-009 create write_pipeline.py
- [ ] P3-010 create read_pipeline.py

### Plan Sign-Off

| Role | Sign-Off |
|------|----------|
| Parent Orchestrator (Guinevere) | Plan written, binding decisions documented |
| Research Wave | 10/10 reports read and synthesized |
| ADR Compliance | ADR-009 primary binding; all deviations documented |
| Boundary Compliance | Consent gate documented; no HARD STOP bypass; no Y6 |
| Budget | Within $2/mo P3 allocation |

**Next action:** Execute P3-004 first after Aizanta health check PASS and timeline verification.
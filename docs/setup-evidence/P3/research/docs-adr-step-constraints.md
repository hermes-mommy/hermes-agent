# P3-004 through P3-010 — Research: Docs/ADR/Step/Tracker Constraints and Acceptance Criteria

**Date:** 2026-06-02  
**Author:** Guinevere (research wave)  
**Status:** Complete — single-file research report  

---

## 1. Source Documents Inspected

| Source | Path | Role |
|--------|------|------|
| PROGRESS.md | \PROGRESS.md\ | Phase/step tracker, cost, blockers |
| CHECKLIST.md | \CHECKLIST.md\ | Verification commands, acceptance criteria per step |
| StepPrompts.md | \stepprompts/StepPrompts.md\ (lines 6105–6271) | Per-step implementation instructions |
| IMPLEMENTATION_GUIDE.md | \docs/IMPLEMENTATION_GUIDE.md\ | System workflow, cost thresholds, shared VPS rules |
| ADR-009 | \dr/ADR-009-memory-recall-semantic-search-strategy.md\ | Embedding model, HNSW params, recall strategy |
| ADR-007 | \dr/ADR-007-memory-storage-backend-selection.md\ | Storage backend (PG + Redis, no SQLite) |
| ADR-008 | \dr/ADR-008-memory-encryption-key-management.md\ | Encryption, key hierarchy, Critical data |
| ADR-024 | \dr/ADR-024-data-governance-classification-policy.md\ | Data classification governance parent |
| ADR-Index | \docs/10-governance/17-ADR_Index_v1.0.md\ | 32 ADR register |
| PersonaSafetyPolicy | \docs/60-persona/60-PersonaSafetyPolicy_v1.0.md\ | Safe-word, distress, safe-mode recall restrictions |
| DataGovernance | \docs/30-data/30-DataGovernance_Classification_v1.0.md\ | Classification tiers, retention, minimization |
| ConsentRevocationPolicy | \docs/30-data/32-ConsentRevocationPolicy_v1.0.md\ | Consent ledger, revocation, do-not-recall |
| MemoryRecallEvalSpec | \docs/30-data/34-MemoryRecallEvaluationSpec_v1.0.md\ | Recall quality metrics, golden dataset, DNR enforcement |
| MemorySchema v2.0 | \docs/00-core/04-MemorySchema_v2.0.md\ | Schema definition, embedding columns, indexes |
| Batch Plan P3-001..003 | \docs/setup-evidence/P3/batch-plan-001-003.md\ | Prior planner decisions, schema reconciliation, HNSW binding |


## 2. Per-Step Analysis: P3-004 through P3-010

### 2.1 P3-004: SentenceTransformers Model Download

**StepPrompts content (lines 6121–6135):**
- Installs \sentence-transformers\ and \openai\ pip packages
- Prints \OpenAI SDK ready\ as verification
- **Primary:** \	ext-embedding-3-small\ (1536-dim) via 9Router → OpenRouter
- **Fallback:** \ll-MiniLM-L6-v2\ (384-dim) — local, free, auto-downloaded on first call

**CHECKLIST.md verification:**
\\\ash
ls ~/.cache/torch/sentence_transformers/  # embedding model downloaded
\\\

**No explicit \model download\ command.** SentenceTransformers auto-downloads \ll-MiniLM-L6-v2\ (~80MB) to \~/.cache/torch/sentence_transformers/\ on first \SentenceTransformer('all-MiniLM-L6-v2')\ call.

**Prerequisites:**
- P3-003 complete (migration verified)
- Phase 1 complete (9Router running on port 20128)
- Python environment with internet access to HuggingFace hub

**Cost impact:** \ (model download is free; pip installs are free)

**Evidence path:** \docs/setup-evidence/P3/STEP-P3-004/\ (not explicitly listed in StepPrompts but follows convention)

**ADR references:** ADR-009 (implied)

**Acceptance criteria:** None explicitly listed; CHECKLIST P3-004 step requires model directory to exist

---

### 2.2 P3-005: Embedding Pipeline

**StepPrompts content (lines 6137–6164):**
- Creates \src/memory/embeddings.py\ with:
  - \embed_text(text: str) -> list[float]\ — single text embedding, 1536-dim, truncates at 8000 chars
  - \embed_batch(texts: list[str]) -> list[list[float]]\ — batch embeddings
  - Uses OpenAI client via 9Router at \http://localhost:20128/v1\
  - Model: \	ext-embedding-3-small\

**CHECKLIST.md verification:**
\\\ash
python -c 'from guinevere.memory import embed; v=embed(\"test\"); print(len(v))'
# Expected: 1536
\\\

**IMPORTANT:** CHECKLIST.md uses import path \guinevere.memory.embed\, but StepPrompts creates \src.memory.embeddings.embed_text\. Path inconsistency — must be reconciled.

**Prerequisites:**
- P3-004 complete (packages installed)
- 9Router running on port 20128
- API key for embeddings (via 9Router → OpenRouter, not direct OpenAI)

**Cost impact:** ~\.02/1M tokens for \	ext-embedding-3-small\. Total P3 embedding cost: ~\/month.

**Embedding dimension lock:** pgvector enforces dimension at write time (ADR-009 §Implementation Notes). Using 1536 now means the dimension is locked for the lifetime of the database. Changing later requires table rebuild.

**Evidence path:** \docs/setup-evidence/P3/STEP-P3-005/embedding-test.txt\

---

### 2.3 P3-006: pgvector HNSW Index

**StepPrompts content (lines 6166–6177):**
- Adds \embedding_vec vector(1536)\ column to \memory.episodes\
- Creates HNSW index: \m=16, ef_construction=64\
- Creates supporting B-tree indexes on: source, created_at DESC, classification, do_not_recall (partial)

**CONFLICT: ADR-009 vs StepPrompts HNSW parameters**

| Parameter | StepPrompts P3-006 | ADR-009 (§Implementation Notes) | Batch Plan P3-001..003 |
|-----------|-------------------|--------------------------------|----------------------|
| m | 16 | 16 | 16 ✅ |
| ef_construction | **64** | **128–256** | **128** |
| ef_search (query) | Mentioned in P3-007 (ef_search=100) | 64–128 production, 128 eval | Not stated |

StepPrompts uses \ef_construction=64\, which is below ADR-009's recommended range of 128–256. The batch plan for P3-001..003 correctly binds to ADR-009's \ef_construction=128\. **This must be aligned.**

**Prerequisites:**
- P3-005 complete (embedding pipeline — though the column and index are DDL only and don't depend on runtime code)
- pgvector 0.8.2+ installed (P0-015)
- PostgreSQL with guinevere database

**Cost impact:** \

**Evidence path:** \docs/setup-evidence/P3/STEP-P3-006/hnsw-index.txt\

---

### 2.4 P3-007: HNSW Parameter Tuning

**StepPrompts content (lines 6179–6184):**
- Benchmark recall vs latency using \SET hnsw.ef_search = 100\
- Target: p95 < 2s with > 90% recall

**CHECKLIST.md verification:**
\\\ash
python -m guinevere.memory.benchmark --queries 100
# Expected: p95 < 200ms
\\\

**INCONSISTENCY:** StepPrompts target is \p95 < 2s\ but CHECKLIST.md target is \p95 < 200ms\ — a 10x difference.

**Prerequisites:**
- P3-006 complete (HNSW index exists)
- At least some test data in \memory.episodes\ (benchmark needs data to search)

**Cost impact:** \

**Evidence path:** Not explicitly listed; CHECKLIST verification log

---

### 2.5 P3-008: tsvector FTS Setup

**StepPrompts content (lines 6186–6199):**
- Adds \search_vector tsvector\ column to \memory.episodes\
- Creates GIN index on search_vector
- Backfills existing NULL search_vectors
- Creates trigger \	rg_episodes_search_vector\ for auto-update on INSERT/UPDATE

**CHECKLIST.md verification:**
\\\ash
to_tsvector('english', 'Guinevere remembers') @@ to_tsquery('english', 'remember')
# Expected: true
\\\

**Prerequisites:**
- P3-006 complete (or independent — FTS does not depend on HNSW)
- PostgreSQL with memory schema

**Cost impact:** \

**Evidence path:** \docs/setup-evidence/P3/STEP-P3-008/fts-test.txt\

---

### 2.6 P3-009: Memory Write Pipeline

**StepPrompts content (lines 6216–6238):**
- Creates \src/memory/write_pipeline.py\ with \store_episode()\:
  - Parameters: db, content, source, classification, importance, metadata
  - Generates embedding via \embed_text(content)\ from P3-005
  - Inserts into \memory.episodes\ with \embedding_vec::vector\ cast
  - Returns episode_id UUID

**CHECKLIST.md verification:**
\\\ash
psql -d guinevere -c \"SELECT id FROM memory.episodes ORDER BY created_at DESC LIMIT 1\"
# Expected: ID returned (non-empty)
\\\

**Classification requirement:** The \classification\ parameter defaults to \\"Internal\"\ in StepPrompts but the DataGovernance policy mandates episodic memory default to \Restricted\ and escalate to \Critical\ for intimate/safe-word content. **Conflict: default classification should be \Restricted\ not \Internal\.**

**Safety gate requirements (from PersonaSafetyPolicy + DataGovernance):**
- Safe-mode must prevent writing Critical raw emotional content
- Consent revocation must be checked before writing surveillance-derived content
- Classification metadata must be stored per DataGovernance §4.3

**Prerequisites:**
- P3-008 complete
- P3-005 complete (\embed_text()\ function)
- Database with \memory.episodes\ table

**Cost impact:** ~\.02/1M tokens per embedding API call (amortized as part of P3's \/month)

**Evidence path:** \docs/setup-evidence/P3/STEP-P3-009/\

---

### 2.7 P3-010: Memory Read Pipeline

**StepPrompts content (lines 6241–6262):**
- Creates \src/memory/read_pipeline.py\ with \ecall_memories()\:
  - Parameters: db, query, limit (default 20), exclude_dnr (default True)
  - Generates query embedding via \embed_text()\ from P3-005
  - pgvector cosine similarity search: \ORDER BY embedding_vec <=> \::vector\
  - Excludes \do_not_recall = true\ by default
  - Returns list of dicts with id, content, source, classification, importance, created_at, similarity

**CHECKLIST.md verification:**
\\\ash
python -c 'from guinevere.memory import recall; r=recall(\"Python\"); print(len(r))'
# Expected: > 0
\\\

**IMPORTANT:** CHECKLIST.md uses import path \guinevere.memory.recall\, but StepPrompts creates \src.memory.read_pipeline.recall_memories\. Path inconsistency — must be reconciled.

**Missing safety gates (required by downstream policies):**
- No safe-mode recall filter (required by PersonaSafetyPolicy + DataGovernance + MemoryRecallEvalSpec)
- No classification ceiling filter (required by DataGovernance)
- No token budget cap (4,000 tokens per cycle per ADR-009)
- No ranking beyond pure cosine similarity (no hybrid vector + FTS + recency — that's P3-011)
- No confidence/importance filter (required by MemorySchema)

**These gaps are expected — P3-010 is a basic MVP implementation.** P3-011 (hybrid ranking), P3-013 (DNR), and P3-014 (safe-mode gate) add the missing layers.

**Prerequisites:**
- P3-009 complete (write pipeline — need data to read)
- P3-005 complete (embedding function)
- Database with memory.episodes table populated

**Cost impact:** ~\.02/1M tokens per embedding API call

**Evidence path:** \docs/setup-evidence/P3/STEP-P3-010/\

---

## 3. Inter-Step Dependency Map

\\\
P3-004 (model/packages)
  │
  ▼
P3-005 (embedding pipeline code)
  │
  ├──▶ P3-006 (HNSW index — DDL, independent of runtime)
  ├──▶ P3-008 (FTS setup — DDL, independent of runtime)
  │
  ├──▶ P3-009 (write pipeline)
  │        │
  │        ▼
  │     P3-010 (read pipeline)
  │
  P3-007 (benchmark — needs index + data)
\\\

**Parallel opportunities:**
- P3-006 and P3-008 can run in parallel (both are DDL, no shared files)
- P3-007 requires P3-006 but can run parallel with P3-009/P3-010

**Sequential constraints:**
- P3-005 must come after P3-004
- P3-009 must come after P3-005
- P3-010 must come after P3-009
- P3-007 needs both index (P3-006) and data (P3-009)

---

## 4. Conflicts and Inconsistencies

### C-01: Embedding Model — ADR-009 vs User Intent (CRITICAL)

| Source | Stated Position |
|--------|----------------|
| ADR-009 §Implementation Notes | \Use OpenAI text-embedding-3-small with 1536 dimensions. Route through 9Router via OpenRouter backend. No direct OpenAI API calls unless a future ADR supersedes.\ |
| StepPrompts P3-004 | Primary: \	ext-embedding-3-small\ via 9Router (1536); Fallback: \ll-MiniLM-L6-v2\ local (384) |
| User context (Faiz) | \\"Planner model selection for local SentenceTransformers\"\ — suggests making local model primary |

**Impact:**
- If local SentenceTransformers becomes primary, pgvector column dimension must change from 1536 to 384 (ADR-009 warns: \pgvector enforces dimension at write time; changing models later requires table rebuild\)
- ADR-009 must be superseded or an exception must be documented
- The \embedding_vec vector(1536)\ column in MemorySchema v2.0 and the P3-005 pipeline assume 1536-dim

**Resolution options:**
1. **Keep ADR-009:** API-based text-embedding-3-small (1536-dim) primary, MiniLM fallback. StepPrompts P3-004 already matches this.
2. **Make local primary:** Change to MiniLM-L6-v2 (384-dim) primary. Requires: ADR-009 supersession, column type change to \ector(384)\, update P3-005 code.
3. **Add local primary but keep 1536:** Use a larger local model like \ll-mpnet-base-v2\ (768-dim) or \gte-large\ (1024-dim) — neither matches 1536. Still requires column change.

### C-02: HNSW ef_construction — StepPrompts vs ADR-009 (HIGH)

| Source | Value |
|--------|-------|
| StepPrompts P3-006 | \ef_construction = 64\ |
| ADR-009 §Implementation Notes | \ef_construction = 128–256\ (recommended for production) |
| Batch Plan P3-001..003 | Binds to ADR-009: \ef_construction = 128\ |

**Resolution:** Follow ADR-009 (128). StepPrompts value is outdated.

### C-03: p95 Latency Target — StepPrompts vs CHECKLIST.md (MEDIUM)

| Source | Target |
|--------|--------|
| StepPrompts P3-007 | p95 < 2s |
| CHECKLIST.md P3-007 | p95 < 200ms |

10x difference. The StepPrompts target (2s) is likely the full pipeline target (P3-019). The CHECKLIST target (200ms) matches HNSW-only search.

### C-04: Default Classification — StepPrompts vs DataGovernance (MEDIUM)

| Source | Value |
|--------|-------|
| StepPrompts P3-009 | \classification\ defaults to \\"Internal\"\ |
| DataGovernance §4.2 | Unclassified defaults to \Confidential\; memory type \episodic\ is \Restricted\ per §5 classification matrix |
| CHECKLIST.md P3 security check | \Records carry classification metadata (AC-MEM-002)\ |

**Resolution:** Change default classification to \Restricted\ for episodic memory, matching DataGovernance policy.

### C-05: Import Path — StepPrompts vs CHECKLIST.md (MEDIUM)

| Source | Path |
|--------|------|
| StepPrompts P3-005 | \src.memory.embeddings.embed_text()\ |
| CHECKLIST.md P3-005 | \guinevere.memory.embed()\ |
| StepPrompts P3-010 | \src.memory.read_pipeline.recall_memories()\ |
| CHECKLIST.md P3-010 | \guinevere.memory.recall()\ |

The \guinevere.memory\ package doesn't exist yet in the StepPrompts code. The CHECKLIST assumes a different module structure. Must align.

### C-06: HNSW Index Naming — StepPrompts vs MemorySchema (LOW)

StepPrompts uses \idx_episodes_embedding_hnsw\, while MemorySchema v2.0 shows \ivfflat\ (line 130). The MemorySchema is outdated — ADR-009 recommends HNSW over IVFFlat for production. Index name is cosmetic but consistent naming is preferred.

### C-07: Written Pipeline Location (LOW)

StepPrompts creates \src/memory/\ files, CHECKLIST expects \guinevere.memory\ package. The code base layout convention should be established before P3-005 implementation.

---

## 5. Prerequisites and Blockers

| Step | Prerequisites | Potential Blockers |
|------|--------------|-------------------|
| P3-004 | P3-003 ✅, Python venv, pip, internet to PyPI/HuggingFace | No internet during VPS deploy; HF rate limits |
| P3-005 | P3-004, 9Router running on port 20128, API key for embeddings | **C-01** unresolved model choice; CHECKLIST import path mismatch |
| P3-006 | PostgreSQL, pgvector, P3-005 (optional — DDL only) | **C-02** ef_construction value unclear |
| P3-007 | P3-006, test data in memory.episodes | **C-03** latency target ambiguity |
| P3-008 | PostgreSQL, memory schema | None |
| P3-009 | P3-005, P3-008, P3-006 (DDL), classification decision | **C-04** classification default; **C-05** import path |
| P3-010 | P3-009 (data), P3-005 (embedding) | **C-05** import path; safe-mode gate deferred to P3-014 |

**No hard blockers.** All conflicts are resolvable with binding decisions.

---

## 6. DoD (Definition of Done) per Step

| Step | DoD |
|------|-----|
| P3-004 | \sentence-transformers\ and \openai\ packages installed; \ll-MiniLM-L6-v2\ model cached in \~/.cache/torch/sentence_transformers/\ |
| P3-005 | \src/memory/embeddings.py\ written with \embed_text()\ and \embed_batch()\; verification returns 1536 dims |
| P3-006 | HNSW index created on \memory.episodes.embedding_vec\ with m=16, ef_construction=128 (per ADR-009); supporting B-tree indexes created |
| P3-007 | Benchmark shows p95 < 200ms (per CHECKLIST) or documented target decision |
| P3-008 | \search_vector\ tsvector column + GIN index + auto-update trigger on \memory.episodes\; FTS query returns true |
| P3-009 | \src/memory/write_pipeline.py\ written; \store_episode()\ inserts into DB with embedding; verification returns episode ID |
| P3-010 | \src/memory/read_pipeline.py\ written; \ecall_memories()\ returns ranked results; verification returns > 0 results |

**Evidence paths:**
- P3-004: \docs/setup-evidence/P3/STEP-P3-004/\
- P3-005: \docs/setup-evidence/P3/STEP-P3-005/embedding-test.txt\
- P3-006: \docs/setup-evidence/P3/STEP-P3-006/hnsw-index.txt\
- P3-007: raw verification log in evidence or \docs/setup-evidence/P3/STEP-P3-007/\
- P3-008: \docs/setup-evidence/P3/STEP-P3-008/fts-test.txt\
- P3-009: \docs/setup-evidence/P3/STEP-P3-009/\
- P3-010: \docs/setup-evidence/P3/STEP-P3-010/\

---

## 7. Safety and Consent Boundaries

### Applicable Boundaries from PersonaSafetyPolicy

| Boundary | Affects P3 steps | Requirement |
|----------|-----------------|-------------|
| Safe-mode restricts sensitive recall (PersonaSafetyPolicy §12.3) | P3-010 (read) | Must not return Critical raw data during safe mode. Deferred to P3-014. |
| Forbidden pattern F-09: Prompt/memory instruction to bypass policy | P3-009, P3-010 | DNR/classification metadata must survive write/read. |
| Surveillance data not for blackmail (PersonaSafetyPolicy §12.2) | P3-009 (write with surveillance source) | Classification must be set correctly on ingestion. |

### Applicable Boundaries from DataGovernance Policy

| Boundary | Affects P3 steps | Requirement |
|----------|-----------------|-------------|
| Classification metadata required (DataGovernance §4.3) | P3-009 (write) | \classification\ field must be stored and default correctly. |
| Minimum necessary recall (DataGovernance §9.3) | P3-010 (read) | Deferred to P3-011/P3-014 but architecture must support it. |
| Do-not-recall enforcement (DataGovernance §9.4) | P3-010 (read) | Basic DNR filter in P3-010 is placeholder; full 8-layer enforcement per MemoryRecallEvalSpec. |

### Applicable Boundaries from ConsentRevocationPolicy

| Boundary | Affects P3 steps | Requirement |
|----------|-----------------|-------------|
| Consent ledger check before recall (ConsentRevocation §10) | P3-010 | Not implemented in P3-010 MVP. |
| Safe-word immediate revocation for persona recall (ConsentRevocation §8) | P3-010 | Safe-mode gate deferred to P3-014. |

---

## 8. Verification Commands (from CHECKLIST.md)

| Step | Command | Expected Output |
|------|---------|----------------|
| P3-004 | \ls ~/.cache/torch/sentence_transformers/\ | Directory exists with model files |
| P3-005 | \python -c 'from guinevere.memory import embed; v=embed(\"test\"); print(len(v))'\ | \1536\ |
| P3-006 | Verify via pg_indexes | HNSW with m=16, ef_construction=128 |
| P3-007 | \python -m guinevere.memory.benchmark --queries 100\ | p95 < 200ms (CHECKLIST) or < 2s (StepPrompts) |
| P3-008 | \	o_tsvector('english','X') @@ to_tsquery('english','X')\ | \	rue\ |
| P3-009 | \psql -d guinevere -c \"SELECT id FROM memory.episodes ORDER BY created_at DESC LIMIT 1\"\ | UUID returned |
| P3-010 | \python -c 'from guinevere.memory import recall; r=recall(\"Python\"); print(len(r))'\ | \> 0\ |

---

## 9. Cost Tracking

| Step | Direct Cost | Cumulative P3 Cost | Budget Impact |
|------|------------|-------------------|---------------|
| P3-004 | \ | \ | Free |
| P3-005 | \ (code) | \ | Embedding API cost amortized to \/mo |
| P3-006 | \ | \ | Free |
| P3-007 | \ | \ | Free |
| P3-008 | \ | \ | Free |
| P3-009 | API cost per write | ~\.02/1M tokens | Part of \/mo |
| P3-010 | API cost per read | ~\.02/1M tokens | Part of \/mo |

**P3 monthly cost:** \/month (embeddings API) per PROGRESS.md.  
**Remaining P3 budget after P3-003:** \/month.  
**Budget OK:** P3-004 through P3-010 stay within the \/month allocation.

---

## 10. Tracker Update Requirements

After each step, the following must be updated:

1. **PROGRESS.md** — Mark step as [x] complete, update counters (currently 3/19 → 10/19 after this batch)
2. **CHECKLIST.md** — Mark step verification as [x] in Section 5.2
3. **Evidence directory** — Create \docs/setup-evidence/P3/STEP-P3-0NN/\ with verification outputs
4. **Cost if applicable** — Update if embedding API costs exceed expected rate

---

## 11. Rollback Plan

| Step | Rollback Command | Risk |
|------|-----------------|------|
| P3-004 | \pip uninstall -y sentence-transformers openai\ | Low — stateless |
| P3-005 | \m src/memory/embeddings.py\; git checkout | Low — file only |
| P3-006 | \DROP INDEX IF EXISTS idx_episodes_embedding_hnsw;\ | Low — DDL only |
| P3-007 | N/A — benchmark only | Low |
| P3-008 | \DROP TRIGGER IF EXISTS trg_episodes_search_vector; DROP INDEX IF EXISTS idx_episodes_fts; ALTER TABLE memory.episodes DROP COLUMN search_vector;\ | Low — DDL only |
| P3-009 | \DELETE FROM memory.episodes WHERE id = <test-id>; rm src/memory/write_pipeline.py;\ | Low — no production data |
| P3-010 | \m src/memory/read_pipeline.py;\ | Low — file only |

---

## 12. Summary of Binding Decisions Needed Before Implementation

| Decision ID | Issue | Options | Recommended |
|-------------|-------|---------|-------------|
| D-01 | Embedding model primary (C-01) | API: text-embedding-3-small (1536) vs Local: MiniLM-L6-v2 (384) | Keep ADR-009: API primary, MiniLM fallback. StepPrompts already reflects this. |
| D-02 | HNSW ef_construction (C-02) | 64 vs 128 vs 256 | 128 per ADR-009 and batch-plan precedent |
| D-03 | p95 latency target (C-03) | < 200ms vs < 2s | < 200ms per CHECKLIST — document as HNSW-only vs full pipeline |
| D-04 | Default classification (C-04) | \\"Internal\"\ vs \\"Restricted\"\ | \\"Restricted\"\ per DataGovernance §5 |
| D-05 | Module structure (C-05) | \src.memory.*\ vs \guinevere.memory.*\ | Follow StepPrompts (\src/memory/\) — P3 code lives in \src/memory/\ |
| D-06 | Local model download explicit step | Add explicit download command or rely on auto-download | Add explicit \sentence-transformers\ download in P3-004 |

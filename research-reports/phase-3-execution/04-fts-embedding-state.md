# FTS & Embedding State Assessment — Guinevere VPS

**Date**: 2026-06-05  
**VPS**: 100.94.104.22 (guinevere-vps)  
**Scope**: Phase 3 Memory Bridge — Search infrastructure readiness  
**Method**: READ-ONLY SSH probes (docker exec, psql, curl, grep) — no modifications

---

## 1. Environment Overview

| Component | Detail |
|---|---|
| PostgreSQL | 16.14 (Docker: `guinevere-postgres:16` with pgvector) |
| Database | `guinevere` (NOT `guinevere_memory` as originally assumed) |
| Schema namespace | `memory` (23 schemas total: memory, agents, persona, surveillance, etc.) |
| pgvector | v0.8.2 |
| TimescaleDB | v2.27.1 |
| 9Router | Next.js app on port 20128, process `node /usr/bin/9router` |
| Redis | Port 6380 |
| Code root | `/home/guinevere/code/guinevere/` |
| Python venv | `/home/guinevere/code/guinevere/.venv/` |

**Memory tables in `memory` schema:**

| Table | Rows | Has embedding? | Has FTS? |
|---|---|---|---|
| `episodes` | 0 | vector(1536) + HNSW index | tsvector `search_vector` + GIN index |
| `semantic_facts` | 0 | vector(1536) + HNSW index | **NO** |
| `emotional_events` | 0 | No | No |
| `faiz_predictions` | 0 | No | No |
| `faiz_profile` | 0 | No | No |
| `inner_journal` | 0 | No | No |
| `knowledge_graph` | 0 | No | No |
| `procedural_skills` | 0 | No | No |

> **Key finding**: All memory tables are empty (0 rows). Schema is fully deployed but no data has been ingested yet.

---

## 2. PostgreSQL Full-Text Search (FTS)

### 2.1 tsvector Column — `memory.episodes.search_vector`

The `episodes` table has a **generated** tsvector column with English dictionary and weighted fields:

```sql
search_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english'::regconfig, COALESCE(title, ''::text)), 'A') ||
    setweight(to_tsvector('english'::regconfig, COALESCE(summary, ''::text)), 'B') ||
    setweight(to_tsvector('english'::regconfig, COALESCE(raw_content, ''::text)), 'D')
) STORED
```

| Weight | Field | Purpose |
|---|---|---|
| A | `title` | Highest relevance |
| B | `summary` | Medium relevance |
| D | `raw_content` | Lowest relevance |

### 2.2 FTS Indexes

| Index | Table | Type | Definition |
|---|---|---|---|
| `ix_episodes_search_vector_gin` | episodes | GIN | `CREATE INDEX ... ON memory.episodes USING gin (search_vector)` |

### 2.3 Available Dictionaries

29 FTS configurations installed: `english`, `indonesian`, `simple`, `arabic`, `french`, `german`, `spanish`, `russian`, `hindi`, plus 19 more language-specific configs.

### 2.4 FTS Gap: semantic_facts

**The `semantic_facts` table has NO tsvector column and NO FTS index.** This means:
- Full-text queries cannot search semantic facts
- The hybrid search pipeline only covers episodes, not facts
- `semantic_facts.subject`, `predicate`, and `object_val` are text columns but not indexed for FTS

---

## 3. pgvector — Embedding Storage

### 3.1 Extension

```
pgvector v0.8.2 — installed and active
```

### 3.2 Vector Columns

| Table | Column | Type | Dimension |
|---|---|---|---|
| `memory.episodes` | `embedding` | `vector(1536)` | 1536 |
| `memory.semantic_facts` | `embedding` | `vector(1536)` | 1536 |

Both use **1536 dimensions** — matching OpenAI `text-embedding-3-small`.

### 3.3 HNSW Indexes

| Index | Table | Operator | m | ef_construction |
|---|---|---|---|---|
| `ix_episodes_embedding_hnsw` | episodes | `vector_cosine_ops` | 16 | 128 |
| `ix_semantic_facts_embedding_hnsw` | semantic_facts | `vector_cosine_ops` | 16 | 128 |

Both use **cosine similarity** as the distance metric. HNSW parameters are set for balanced recall/speed:
- `m=16`: moderate connectivity (higher = better recall, slower build)
- `ef_construction=128`: construction-time search depth

### 3.4 pgvector_config Table

The `extensions.pgvector_config` table exists but is **empty (0 rows)**. No custom HNSW ef_search or other tuning has been applied.

---

## 4. Embedding Generation Status

### 4.1 Current State

| Metric | episodes | semantic_facts |
|---|---|---|
| Total rows | 0 | 0 |
| With embedding | 0 | 0 |
| Missing embedding | 0 | 0 |
| Last embedded timestamp | NULL | NULL |
| Failed embeddings | 0 (no data) | 0 (no data) |

> **Status: EMPTY — No embeddings have been generated because no memory data exists in the database.**

### 4.2 Embedding Pipeline (Code-Level)

The embedding pipeline is fully implemented in `/home/guinevere/code/guinevere/src/memory/embeddings.py`:

- **Service**: `EmbeddingService` class using `httpx` (no OpenAI SDK — ADR-009 compliant)
- **Model**: `openai/text-embedding-3-small` (1536 dimensions)
- **Base URL**: `http://localhost:20128/v1` (9Router)
- **Retry**: Manual exponential backoff (max 6 retries, 60s timeout)
- **Privacy**: Classification-aware redaction (Critical = fail closed, Restricted = pattern redaction)
- **Logging**: Metadata-only (model, dimensions, duration — never raw text or vectors)

The `write_pipeline.py` calls `EmbeddingService.aembed()` optionally during episode/fact creation.

---

## 5. 9Router Status

### 5.1 Process

```
guinevere  627184  node /usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
```

- **Port**: 20128 (bound to `0.0.0.0`)
- **Uptime**: Since Jun 01 (4+ days)
- **Memory**: ~55MB RSS
- **Type**: Next.js web application (NOT a traditional REST API server)

### 5.2 Endpoint Responses

| Endpoint | Result | Detail |
|---|---|---|
| `GET /` | 307 redirect to `/dashboard` | Working |
| `GET /dashboard` | 200 HTML (Next.js UI) | 9Router management dashboard |
| `GET /health` | **404 Not Found** | No health endpoint exists |
| `GET /v1/models` | **Not tested** (timeout/empty in initial probe) | Needs investigation |
| `POST /v1/embeddings` | **Not tested** (timeout in probe) | The embedding endpoint path is unverified |
| `GET /api` | Returns `/api` (directory listing?) | Route exists but content unknown |

### 5.3 Critical Finding: API vs. UI Discrepancy

9Router is running as a **Next.js web dashboard**, not as a standalone API server. The `/health` endpoint returns 404 because the Next.js app doesn't have a health route. The embedding endpoint at `/v1/embeddings` is **assumed** by the code (`DEFAULT_BASE_URL = "http://localhost:20128/v1"`) but its actual availability is **UNVERIFIED**.

Potentially relevant: 9Router may expose an API at a different port or path than the dashboard. The research report from Phase 1 (`research-reports/P1/9router-api-endpoints.md`) should be consulted.

### 5.4 Port Summary

9Router is on **20128**, not 9000. Port 9000 has nothing listening.

---

## 6. SQLite / FTS5 Assessment

### 6.1 SQLite Databases on VPS

| Database | Location | Purpose |
|---|---|---|
| `state.db` | `/home/guinevere/.hermes/state.db` | Hermes session/message tracking |
| `kanban.db` | `/home/guinevere/.hermes/kanban.db` | Hermes task/work management |
| `grafana.db` | `/home/guinevere/data/grafana/grafana.db` | Grafana internal (inaccessible) |
| 16 cache files | `.mypy_cache/3.12/` | Python type checking cache |

### 6.2 FTS5 Assessment

**No FTS5 virtual tables exist in any SQLite database.** Both Hermes databases use standard SQLite tables without full-text search:

- `state.db`: `sessions`, `messages`, `sqlite_sequence`, `state_meta`, `schema_version`
- `kanban.db`: `tasks`, `task_links`, and other task management tables

All text search for Guinevere is handled by PostgreSQL (tsvector + pgvector), not SQLite FTS5.

---

## 7. Search Implementation in Code

### 7.1 Hybrid Search Architecture

The read pipeline (`read_pipeline.py`) implements a **dual-channel weighted RRF (Reciprocal Rank Fusion)** hybrid search:

```
┌─────────────────────────────────────────────────────┐
│                    Search Query                       │
├─────────────────────┬───────────────────────────────┤
│   Vector (pgvector) │   FTS (tsvector + GIN)         │
│   cosine_distance   │   plainto_tsquery('english')   │
│   <=> operator      │   @@ operator                  │
├─────────────────────┴───────────────────────────────┤
│          Weighted RRF Fusion                         │
│   VECTOR_WEIGHT = 0.5   FTS_WEIGHT = 0.5            │
│   BOOST_MULTIPLIER = 1.4 (when both match)           │
├──────────────────────────────────────────────────────┤
│          Recency Decay (90-day window)                │
│          Fallback: Recency-only for cold-start        │
└──────────────────────────────────────────────────────┘
```

### 7.2 Key Functions

| Function | File | Purpose |
|---|---|---|
| `build_vector_query()` | `read_pipeline.py` | pgvector cosine similarity search |
| `build_fts_query()` | `read_pipeline.py` | PostgreSQL FTS via `plainto_tsquery` |
| `build_recency_query()` | `read_pipeline.py` | Fallback time-decay ordering |
| `rrf_fusion()` | `read_pipeline.py` | Weighted reciprocal rank fusion |
| `EmbeddingService` | `embeddings.py` | httpx client for 9Router embeddings |

### 7.3 Search-Related Files

| File | Type |
|---|---|
| `src/memory/read_pipeline.py` | Core search/hybrid logic |
| `src/memory/models.py` | SQLAlchemy models (Vector, tsvector columns) |
| `src/memory/embeddings.py` | Embedding service client |
| `src/memory/write_pipeline.py` | Write path with optional embedding |
| `src/discord/cmd_memory_search.py` | Discord command for memory search |
| `src/hermes/memory_bridge.py` | Hermes integration bridge |

### 7.4 Model Definitions

**Episodes** (`models.py`):
```python
embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536))
search_vector: Mapped[Optional[str]] = mapped_column(
    TSVector(), 
    Computed("setweight(to_tsvector('english', coalesce(title, '')), 'A') || ...")
)
```

**SemanticFacts** (`models.py`):
```python
embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536))
# NO search_vector column
```

---

## 8. Gap Analysis

### 8.1 What's Working ✅

| Component | Status |
|---|---|
| PostgreSQL 16 with pgvector v0.8.2 | Operational |
| `episodes` schema: vector(1536) + HNSW index | Ready |
| `episodes` schema: tsvector + GIN index | Ready |
| `semantic_facts` schema: vector(1536) + HNSW index | Ready |
| 29 FTS dictionaries (english, indonesian, etc.) | Available |
| HNSW indexes configured (m=16, ef=128) | Deployed |
| EmbeddingService code (httpx, retry, privacy) | Implemented |
| Hybrid search pipeline (vector + FTS + recency) | Implemented |
| Weighted RRF fusion with boost | Implemented |
| Classification-aware embedding (Critical = fail closed) | Implemented |

### 8.2 What's Broken / Gaps ❌

| Gap | Severity | Detail |
|---|---|---|
| **9Router embedding endpoint unverified** | **HIGH** | `/health` returns 404. `/v1/embeddings` path unconfirmed. Code assumes it works but cannot be tested until data exists. |
| **No health endpoint on 9Router** | MEDIUM | Monitoring cannot detect 9Router failures. `/health` → 404. |
| **`semantic_facts` has no FTS** | MEDIUM | No tsvector column, no GIN index. Full-text queries cannot search semantic facts. |
| **All memory tables empty (0 rows)** | MEDIUM | No data ingested — neither FTS nor embedding can be validated end-to-end. |
| **No embedding generation history** | MEDIUM | Cannot assess success/failure rates or performance. |
| **No ef_search tuning** | LOW | `pgvector_config` table empty. Default ef_search=40 used. Could be optimized. |
| **9Router port mismatch in documentation** | LOW | Earlier research assumed port 9000; actual is 20128. |

### 8.3 What's Missing 🚧

| Missing Component | Needed For |
|---|---|
| Data ingestion pipeline (active) | Population of memory tables |
| 9Router embedding endpoint validation | Confirming `POST /v1/embeddings` works |
| 9Router model listing | Verifying available embedding models |
| FTS on `semantic_facts` | Full-text search across facts |
| ef_search optimization | Tuning HNSW search performance |
| Health monitoring for 9Router | Operational visibility |
| Embedding batch processing for backfill | Large-scale embedding generation |

---

## 9. Recommendations

### Immediate (Phase 3 execution)

1. **Validate 9Router embedding endpoint**: Test `POST http://localhost:20128/v1/embeddings` with a real API key configured in 9Router dashboard. The code is implemented but the endpoint's actual behavior is unverified.

2. **Check 9Router model routing**: Verify 9Router is configured with an OpenRouter API key and that `openai/text-embedding-3-small` (or equivalent) is routed correctly.

3. **Ingest test data**: Populate at least 1-2 episodes and semantic facts to validate the end-to-end embedding + search pipeline.

### Short-term

4. **Add FTS to semantic_facts**: Create a generated tsvector column on `subject || predicate || object_val` with a GIN index.

5. **Tune HNSW ef_search**: Set via `pgvector_config` table or `SET hnsw.ef_search = ...` for optimal recall/latency tradeoff.

6. **Add health endpoint to 9Router**: Either via a Next.js API route or a separate sidecar process.

### Schema Fix Notes

The original task assumed table names `episodic_memories` and `semantic_memories` in database `guinevere_memory`. The actual names are:

| Assumed | Actual |
|---|---|
| `guinevere_memory` database | `guinevere` database |
| `episodic_memories` table | `memory.episodes` |
| `semantic_memories` table | `memory.semantic_facts` |

All further work should use the correct schema-qualified names: `memory.episodes` and `memory.semantic_facts`.

---

## 10. Raw Command Reference

For future probes, the working psql invocation pattern is:

```bash
echo "SQL_STATEMENT;" | docker exec -i guinevere-postgres psql -U guinevere -d guinevere
```

Use `memory.episodes` and `memory.semantic_facts` with schema prefix.

9Router lives at:
```bash
curl http://localhost:20128/v1/embeddings -H "Content-Type: application/json" \
  -d '{"model":"openai/text-embedding-3-small","input":"test"}'
```

---

*Report generated via SSH probes. No modifications made to VPS. All commands are READ-ONLY.*
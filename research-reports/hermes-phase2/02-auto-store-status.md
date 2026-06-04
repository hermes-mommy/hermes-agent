# Auto-Store Pipeline Status Report — Hermes Phase 2 Research Agent 2

> **Date**: 2026-06-04
> **Agent**: Research Agent 2 (auto-store diagnostic)
> **Scope**: VPS live status of memory auto-store, embedding health, recall pipeline, FTS indexes

---

## Executive Summary

| Area | Status | Verdict |
|---|---|---|
| Auto-store trigger | Fires on every conversation | **BROKEN** — fails at embedding step |
| Episodes written to DB | 0 rows | **NEVER succeeded** |
| Embedding service | 400 Bad Request — no OpenAI credentials on 9Router | **CRITICALLY BROKEN** |
| Recall pipeline | Falls back to keyword/FTS on embedding failure | **BROKEN** — queries wrong DB name |
| FTS indexes | Present and well-structured | **HEALTHY but unused** (0 rows) |
| Schema & indexes | 31 columns, HNSW + GIN indexes | **HEALTHY** |

**Overall verdict: Auto-store pipeline is structurally complete but non-functional. Zero episodes have ever been written. Two blocking bugs prevent operation.**

---

## 1. Episode Counts by Source

```
 source | count | latest
--------+-------+--------
(0 rows)
```

**Finding**: The `memory.episodes` table contains **zero rows**. Auto-store has never successfully written a single episode to PostgreSQL.

---

## 2. Recent Episodes Detail

```
 id | source | classification | importance | episode_type | tags | title | created_at
----+--------+----------------+------------+--------------+------+-------+------------
(0 rows)
```

**Finding**: No episodes of any type exist. No Discord conversations, no manual additions, nothing.

---

## 3. Embedding Vector Status

```
 id | title | has_embedding | created_at
----+-------+---------------+------------
(0 rows)
```

**Finding**: No embeddings exist because no episodes exist. The `embedding` column (USER-DEFINED, vector type) is present in the schema but entirely empty.

---

## 4. Table Schema — `memory.episodes`

The schema is **complete and well-designed** with 31 columns:

| Column | Type | Purpose |
|---|---|---|
| id | uuid | Primary key (composite with started_at) |
| started_at / ended_at | timestamptz | Episode time range |
| episode_type | text | Type discriminator |
| title | text | Episode title |
| summary | text | Content summary |
| key_insights | jsonb | Structured insights |
| mood_at_start / mood_at_end | text | Emotional tracking |
| emotional_tone | text | Tone classification |
| faiz_behavior | jsonb | Behavioral observations |
| raw_content | text | Original content |
| **embedding** | **USER-DEFINED (vector)** | **1536-dim embedding vector** |
| importance | integer | Priority score |
| tags | ARRAY | Tag list |
| related_ids | ARRAY | Episode relationships |
| version | integer | Schema version |
| classification | text | Data classification level |
| purpose | text | Episode purpose |
| source | text | Origin source |
| retention_class / retention_until | text/timestamptz | Retention policy |
| access_policy | text | Access control |
| encryption_profile | text | Encryption config |
| deletion_state | text | Soft delete state |
| key_id / key_version | text/integer | Encryption key tracking |
| created_at / updated_at | timestamptz | Audit timestamps |
| **search_vector** | **tsvector** | **Full-text search vector** |
| do_not_recall | boolean | Recall suppression flag |

---

## 5. Error Log Analysis (Last 1 Hour)

### 5.1 Auto-Store Embedding Failure (CRITICAL — Blocking)

```
memory_auto_store_error error='API error (400): {"error":{"message":"No credentials for provider: openai","type":"invalid_request_error","code":"bad_request"}}' error_type=EmbeddingAPIError
```

**Repeated 5 times** in the last hour, once per conversation. This is the **root cause** of zero episodes.

**Root cause chain**:
1. `EmbeddingService` targets `http://localhost:20128/v1` (9Router local proxy)
2. Model: `openai/text-embedding-3-small`
3. API key loaded from env vars: `GUINEVERE_9ROUTER_API_KEY` or `OPENROUTER_API_KEY`
4. The 9Router proxy responds with: `"No credentials for provider: openai"`
5. 9Router does not have OpenAI API credentials configured for embedding requests
6. `store_episode()` fails inside the embedding step
7. Exception caught by auto-store's try/except — conversation continues normally, but nothing stored

### 5.2 Recall Pipeline — Wrong Database (CRITICAL — Blocking)

```
memory_recall_fallback error='database "guinevere_core" does not exist' error_type=InvalidCatalogNameError
```

When embedding fails for recall queries, the pipeline falls back to keyword/FTS search. The fallback also fails because it connects to database `guinevere_core` (the **user** name) instead of `guinevere` (the **database** name).

### 5.3 Recall Always Returns No Results

```
src.memory.read_pipeline [WARNING] embedding_fallback_keyword
src.memory.read_pipeline [INFO] recall_no_results
memory_recall_integrated query_length=30 safe_mode=False
```

Every recall attempt: embedding fails → keyword fallback → wrong DB → no results.

### 5.4 Embedding HTTP Error Pattern

```
httpx [INFO] HTTP Request: POST http://localhost:20128/v1/embeddings "HTTP/1.1 400 Bad Request"
```

Consistent 400 from the local 9Router proxy for all embedding requests.

---

## 6. FTS Index Status

### Indexes on `memory` Schema

| Index | Table | Type | Details |
|---|---|---|---|
| `pk_episodes` | episodes | UNIQUE btree | (id, started_at) |
| `episodes_started_at_idx` | episodes | btree | started_at DESC |
| **`ix_episodes_embedding_hnsw`** | **episodes** | **HNSW** | **embedding vector_cosine_ops, m=16, ef_construction=128** |
| **`ix_episodes_search_vector_gin`** | **episodes** | **GIN** | **search_vector** |
| `ix_semantic_facts_embedding_hnsw` | semantic_facts | HNSW | embedding vector_cosine_ops, m=16, ef_construction=128 |
| `ix_semantic_facts_source_episode` | semantic_facts | btree | source_episode |
| `pk_emotional_events` | emotional_events | UNIQUE btree | id |
| `pk_faiz_predictions` | faiz_predictions | UNIQUE btree | id |
| `pk_faiz_profile` | faiz_profile | UNIQUE btree | id |
| `pk_inner_journal` | inner_journal | UNIQUE btree | id |
| `pk_knowledge_graph` | knowledge_graph | UNIQUE btree | id |
| `pk_procedural_skills` | procedural_skills | UNIQUE btree | id |
| `uq_procedural_skills_skill_name` | procedural_skills | UNIQUE btree | skill_name |
| `pk_semantic_facts` | semantic_facts | UNIQUE btree | id |

**Finding**: Index infrastructure is production-ready. HNSW for vector similarity and GIN for full-text search are both present. The problem is purely at the application layer — no data flows in.

---

## 7. Auto-Store Code Analysis

**File**: `src/discord/conversational_handler.py`, lines 525-562

```python
# Step 12b: Auto-store conversation to memory
try:
    session_factory_fn = getattr(bot, "get_session_factory", None)
    session_factory = session_factory_fn() if session_factory_fn else None

    if session_factory is not None:
        from src.memory.write_pipeline import RESTRICTED, store_episode

        embedding_svc = _get_embedding_service()
        conversation_content = f"Faiz: {content}\nGuinevere: {response_text}"
        conversation_summary = content[:200]

        async with session_factory() as session:
            await store_episode(
                session=session,
                content=conversation_content,
                source="discord_conversation",
                classification=RESTRICTED,
                importance=3,
                summary=conversation_summary,
                episode_type="conversation",
                tags=["discord", "chat", "auto-store"],
                embedding_service=embedding_svc,
            )
        logger.info("memory_auto_store_success", ...)
    else:
        logger.info("memory_auto_store_skipped", reason="no_session_factory")
except Exception as exc:
    logger.warning("memory_auto_store_error", error=str(exc), error_type=type(exc).__name__)
```

**What it does**:
1. Gets the DB session factory from the bot object
2. Lazily initializes `EmbeddingService` singleton via `_get_embedding_service()`
3. Formats conversation as `"Faiz: {user_msg}\nGuinevere: {response}"`
4. Truncates user message to 200 chars as summary
5. Calls `store_episode()` with source=`discord_conversation`, classification=`Restricted`, importance=3, tags=`["discord", "chat", "auto-store"]`
6. Wraps everything in try/except — never crashes the conversation on memory failure (correct defensive pattern)

**Code quality**: The auto-store code is well-structured. The failure is entirely in the dependency chain (embedding service → 9Router credentials).

---

## 8. Embedding Service Configuration

**File**: `src/memory/embeddings.py`

| Config | Value |
|---|---|
| Base URL | `http://localhost:20128/v1` (local 9Router proxy) |
| Model | `openai/text-embedding-3-small` |
| Expected dimension | 1536 |
| Max input chars | 8000 |
| Timeout | 60s |
| Max retries | 6 |
| API key env vars | `GUINEVERE_9ROUTER_API_KEY`, `OPENROUTER_API_KEY` |

The service uses httpx (no OpenAI SDK dependency per ADR-009). It sends POST to `/v1/embeddings` on the local 9Router proxy with `Authorization: Bearer <key>`.

---

## 9. Assessment: What Works, What Doesn't

### Working

| Component | Status |
|---|---|
| DB schema (`memory.episodes`) | Complete, 31 columns |
| HNSW vector index | Present, configured (m=16, ef=128) |
| GIN FTS index | Present, configured |
| Auto-store trigger code | Correctly fires after each conversation |
| Error handling | Graceful — conversation never crashes |
| Session factory | Connected to correct database (`guinevere`) |
| Embedding service code | Well-implemented with retry, privacy guards, classification |

### Broken

| Component | Issue | Severity |
|---|---|---|
| **9Router OpenAI credentials** | 9Router proxy has no OpenAI API key configured for embedding provider | **CRITICAL** |
| **Recall DB name** | Recall fallback connects to `guinevere_core` (user) instead of `guinevere` (database) | **CRITICAL** |
| **Auto-store output** | 0 episodes written — complete data loss | **CRITICAL** |
| **Recall output** | Every recall returns no results | **CRITICAL** |

---

## 10. Recommendations for Phase 2

### P0 — Must Fix Before Phase 2 Proceeds

1. **Configure OpenAI credentials on 9Router**: The 9Router proxy at `localhost:20128` needs a valid OpenAI API key registered for the `openai` provider. This is the single fix that unblocks auto-store.
   - Verify: `curl -X POST http://localhost:20128/v1/embeddings -H "Authorization: Bearer <9router-key>" -H "Content-Type: application/json" -d '{"input":"test","model":"openai/text-embedding-3-small"}'`

2. **Fix recall database name**: The read pipeline's keyword fallback is connecting to database `guinevere_core` instead of `guinevere`. Check the DB connection string in `src/memory/read_pipeline.py` and any DATABASE_URL or connection config.

### P1 — Phase 2 Implementation Priorities

3. **Backfill embeddings**: Once 9Router credentials are fixed, run a batch job to generate embeddings for any existing episodes (currently 0, so no backfill needed now, but needed once auto-store starts producing data).

4. **Add embedding health check**: Auto-store should detect repeated embedding failures and log a single aggregated error rather than per-conversation failures. Consider a circuit breaker pattern.

5. **Recall pipeline resilience**: When embedding fails AND FTS fails, the system should still attempt basic text search on `raw_content` or `summary` columns as a last resort.

### P2 — Phase 2 Enhancements

6. **Monitoring integration**: Add Prometheus metrics for auto-store success/failure rates, embedding latency, and recall hit rates.

7. **Episode importance tuning**: Currently hardcoded to `importance=3` for all conversations. Consider dynamic importance based on conversation significance (emotional content, explicit memory requests, etc.).

8. **Deduplication**: Add duplicate detection — consecutive conversations about the same topic should update rather than create new episodes.

---

## Appendix: Raw Command Outputs

All SQL queries executed successfully against PostgreSQL on `127.0.0.1:5433`, database `guinevere`, user `guinevere_core`. Secrets decrypted via SOPS + age key at `/home/guinevere/secrets/age-key.txt`.

Journal logs from `journalctl -u guinevere-discord --since '1 hour ago'` with grep for `memory|embed|recall|auto.store|store_episode`.

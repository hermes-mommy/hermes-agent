# R02 — Embedding and Vector Recall Path Audit

**Auditor:** Guinevere (orchestrator)
**Date:** 2026-06-27
**Status:** COMPLETE
**Source:** Direct inspection of `src/memory/embeddings.py`, `src/memory/read_pipeline.py`, `src/core/main.py`

---

## 1. Verdict

| Check | Verdict |
|-------|---------|
| EmbeddingService exists and works | ✅ PASS — `src/memory/embeddings.py` (775 lines), sync + async API |
| `recall_memories()` accepts `embedding_service` | ✅ PASS — Optional parameter at line 797 |
| Graceful fallback when embedding_service is None | ✅ PASS — Keyword-only search (FTS + recency), no crash |
| Life-kernel recall path passes embedding_service | ❌ FAIL — `src/core/main.py` line 291: NO embedding_service |
| `life_kernel/` references EmbeddingService | ❌ FAIL — Zero references found |
| Episodes with NULL embedding handled | ⚠️ PARTIAL — Excluded from vector search, no backfill job |

---

## 2. The Missing Embedding Service

### 2.1 Exact location

**File:** `src/core/main.py` lines 260-303

```python
async def _life_recall_fn(
    query_text: str,
    limit: int = 20,
    ...
) -> RecallResults:
    return await _recall_memories(
        session,
        query_text,
        limit=limit,
        exclude_dnr=True,
        safe_mode=_life_safe_recall,
        project_id=project_id,
        # NO embedding_service parameter!
    )
```

### 2.2 Impact

When `embedding_service is None`:
- `recall_memories()` skips the vector query entirely (line 889-895)
- Only FTS + recency signals are used
- The `both_signal_bonus` (x1.25) is never applied since only FTS finds results
- Recall quality is degraded: semantic similarity is absent from brain memory retrieval

### 2.3 Fix

```python
from src.memory.embeddings import EmbeddingService

# In the life_kernel startup block (around line 260):
_embedding_service = EmbeddingService()

async def _life_recall_fn(
    query_text: str,
    limit: int = 20,
    ...
) -> RecallResults:
    return await _recall_memories(
        session,
        query_text,
        limit=limit,
        exclude_dnr=True,
        safe_mode=_life_safe_recall,
        project_id=project_id,
        embedding_service=_embedding_service,  # NEW
    )
```

The `EmbeddingService` constructor reads `GUINEVERE_9ROUTER_API_KEY` from environment. If unavailable, `aembed()` calls will fail gracefully (caught by `recall_memories` at line 893 — logs warning, falls back to keyword-only).

---

## 3. Episodes With NULL Embedding

### 3.1 Current behavior

`build_vector_query()` (line 551):
```python
stmt = select(Episodes).where(Episodes.embedding.isnot(None))
```

Episodes with NULL embedding are excluded from vector search. They can only be found via FTS or recency.

### 3.2 Backfill needed

Create `src/memory/embedding_backfill.py`:
1. Query episodes with NULL embedding and non-NULL raw_content
2. Compute embeddings via `EmbeddingService.aembed_batch()`
3. UPDATE embedding column
4. Idempotent: skip episodes that already have embeddings
5. Batch size: 50 episodes per API call
6. Progress logging: every 100 episodes
7. Graceful: if embedding API fails, log and continue

---

## 4. Recommended Fixes

1. **main.py**: Import `EmbeddingService`, create instance, pass to `_life_recall_fn`
2. **New file**: `src/memory/embedding_backfill.py` — idempotent backfill job
3. **Optional**: Add `embedding_backfill` to APScheduler as a one-shot or periodic job
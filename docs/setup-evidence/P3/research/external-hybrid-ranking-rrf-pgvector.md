# External Best-Practice Research: Hybrid Vector + FTS Retrieval Ranking (RRF + pgvector)

**P3-011 Context:** Produce ranked hybrid results with RRF k=60, vector weight, FTS weight, 90-day recency half-life, tests/evidence/tracker sync/auditor PASS. P3-010 already has a hybrid read pipeline but weighted RRF was deferred to P3-011.

**Date:** 2026-06-02  
**Sources:** pgvector official docs, PostgreSQL docs, Crunchy Data, OpenSearch RRF benchmarks, Cormack et al. (2009) SIGIR paper, Micelclaw production case study, BigData Boutique RRF guide, multiple production hybrid-search implementations.

---

## Table of Contents

1. [Reciprocal Rank Fusion — Foundation and k=60 Rationale](#1-reciprocal-rank-fusion--foundation-and-k60-rationale)
2. [Combining pgvector Cosine Distance with tsvector/ts_rank_cd](#2-combining-pgvector-cosine-distance-with-tsvectorts_rank_cd)
3. [Weighted RRF: Vector Weight vs FTS Weight](#3-weighted-rrf-vector-weight-vs-fts-weight)
4. [Recency Decay with 90-Day Half-Life](#4-recency-decay-with-90-day-half-life)
5. [Importance Scoring (Multi-Signal Bonus)](#5-importance-scoring-multi-signal-bonus)
6. [HNSW ef_search Tuning (64–128) and Index Performance](#6-hnsw-ef_search-tuning-64-128-and-index-performance)
7. [Full Hybrid Query Pattern (SQL CTE)](#7-full-hybrid-query-pattern-sql-cte)
8. [Deterministic Test Strategies](#8-deterministic-test-strategies)
9. [Recommended Parameters Summary](#9-recommended-parameters-summary)
10. [Implementation Cautions](#10-implementation-cautions)
11. [References](#11-references)

---

## 1. Reciprocal Rank Fusion — Foundation and k=60 Rationale

### 1.1 The Formula

Reciprocal Rank Fusion (RRF) was introduced by Cormack, Clarke, and Büttcher in their 2009 SIGIR paper *"Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"*. The formula:

```
RRF_score(d) = Σ_r 1 / (k + rank_r(d))
```

Where:
- `rank_r(d)` = 1-indexed position of document `d` in retriever `r`'s ranked list
- `k` = smoothing constant (default 60)
- Summed across all retrievers `r`

**Source:** [Cormack et al. 2009, SIGIR](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)

### 1.2 Why k=60

The constant `k` controls how aggressively top ranks are weighted. At `k=60`:

| Rank | Contribution | % of rank-1 contribution |
|------|-------------|--------------------------|
| 1    | 1/61 ≈ 0.01639 | 100% |
| 2    | 1/62 ≈ 0.01613 | 98.4% |
| 10   | 1/70 ≈ 0.01429 | 87.2% |
| 50   | 1/110 ≈ 0.00909 | 55.5% |
| 100  | 1/160 ≈ 0.00625 | 38.1% |

**Key insight:** The difference between rank 1 and rank 2 is tiny (~1.6%), while the difference between rank 1 and rank 50 is meaningful (~44.5%). This means:

- **No single retriever can dominate** by placing a document at #1 while another retriever ranks it poorly.
- **Consensus is rewarded:** A document at rank 3 in both lists beats a document at rank 1 in one list and rank 50 in the other.
- **The tail matters:** Even rank-100 contributes non-zero value, preventing documents from being completely silenced by one retriever.

**Source:** [Cormack et al. 2009 §3](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf); [Serghei's Blog — RRF Explained](https://blog.serghei.pl/posts/reciprocal-rank-fusion-explained/)

### 1.3 What the Benchmarks Show

The original paper ran RRF on three settings:

1. **Pilot (30 Wumpus configs, 4 TREC collections):** RRF consistently beat every individual configuration.
2. **TREC submissions (TREC 3, 5, 9, Robust):** RRF beat Condorcet in all four cases, CombMNZ in three.
3. **LETOR 3 (583,850 query-document pairs, 7 trained rankers):** RRF as a meta-ranker beat every individual learned method with `p < 0.003` — the best published result on LETOR 3 at the time.

**OpenSearch benchmarks (2025)** across 6 BEIR datasets found RRF scored ~3.86% lower on NDCG@10 vs tuned score normalization, but delivered:
- 1.62% p50 latency improvement
- 1.42% p90 latency improvement
- 0.78% p99 latency improvement
- No meaningful CPU difference

**Source:** [OpenSearch — Introducing RRF for Hybrid Search](https://opensearch.org/blog/introducing-reciprocal-rank-fusion-hybrid-search/); [Cormack et al. 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)

### 1.4 Why Not Score Normalization?

| Method | Problem |
|--------|---------|
| Min-max | Outlier scores compress all others into a narrow band |
| L2 normalization | Still dependent on score distribution per query |
| CombSUM/CombMNZ | Requires normalized scores; same fragility |

RRF avoids all of these by operating **only on rank positions** — the one universal language every retriever speaks.

### 1.5 Weighted RRF Variant

For cases where one retriever is known to be systematically stronger:

```
Weighted_RRF_score(d) = Σ_r w_r / (k + rank_r(d))
```

Where `w_r` is the per-retriever weight (summing to 1.0 for equal weighting, or asymmetric for biasing).

**Production note:** OpenSearch's normalization processor supports per-query weights; MongoDB's `$rankFusion` exposes `weights` per pipeline. For pgvector, this must be implemented in application code or SQL.

**Source:** [BigData Boutique — RRF Guide](https://bigdataboutique.com/blog/reciprocal-rank-fusion-how-it-works-and-when-to-use-it)

---

## 2. Combining pgvector Cosine Distance with tsvector/ts_rank_cd

### 2.1 The Two Distance Functions

| Function | Domain | Range | Direction |
|----------|--------|-------|-----------|
| `embedding <=> query` | pgvector cosine distance | [0, 2] | Lower = more similar |
| `ts_rank_cd(tsv, query)` | PostgreSQL FTS | [0, 1+] | Higher = more relevant |

**Critical:** These live on **different scales and directions**. Cosine distance is 0=identical, 2=opposite. ts_rank_cd is 0=irrelevant, unbounded positive. RRF handles this because it uses ranks, not raw scores.

### 2.2 Recommended: `ts_rank_cd` vs `ts_rank`

PostgreSQL offers two ranking functions:

| Function | Description | When to Use |
|----------|-------------|-------------|
| `ts_rank()` | Based on term frequency (tf) | General-purpose; sensitive to frequency |
| `ts_rank_cd()` | Cover density — considers proximity of query terms | **Recommended** for hybrid search because it rewards documents where query terms appear close together, which correlates better with semantic relevance |

**Recommendation:** Use `ts_rank_cd([tsv], [query], 32)` — the third argument `32` uses normalization option 32 (`rank/(rank+1)`), which clamps the raw score to `[0, 1)` and makes logged scores more interpretable.

```sql
ts_rank_cd(search_vector, plainto_tsquery('english', 'query text'), 32)
```

**Source:** [PostgreSQL Docs — Ranking Search Results](https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-RANKING)

### 2.3 tsvector Column: Generated vs Trigger

**Recommended pattern:** Use a `GENERATED ALWAYS` stored column for zero-maintenance:

```sql
ALTER TABLE messages
  ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(content, '')), 'B')
  ) STORED;

CREATE INDEX idx_messages_search ON messages USING GIN (search_vector);
```

**Weight assignment:**
- Weight `'A'`: title (highest importance)
- Weight `'B'`: content/body
- Weight `'C'`: tags/summary (not shown above but easy to add)

**Source:** [PostgreSQL Docs — Weighted tsvector](https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-MANIPULATE); [Lucas Pessamai — Hybrid Search with pgvector](https://dev.to/lpossamai/building-hybrid-search-for-rag-combining-pgvector-and-full-text-search-with-reciprocal-rank-fusion-6nk)

### 2.4 Full-Text Query Construction

| Query Parser | Use Case |
|-------------|----------|
| `plainto_tsquery('english', $q)` | Best default for user input — handles punctuation, converts to AND of terms |
| `phraseto_tsquery('english', $q)` | Forces phrase matching — use for exact-match queries |
| `websearch_to_tsquery('english', $q)` | Supports quoted phrases and `-` negation operators for advanced users |

**Recommendation:** Use `plainto_tsquery('english', ...)` as default. For multilingual data, use `'simple'` configuration instead of `'english'` to avoid stemming issues.

**Source:** [PostgreSQL Docs — tsquery](https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-PARSING-QUERIES)

---

## 3. Weighted RRF: Vector Weight vs FTS Weight

### 3.1 The Weighted RRF Formula

For P3-011, the recommended approach is a **weighted RRF** where vector and FTS contributions can be tuned independently:

```python
def weighted_rrf(
    vector_ranked: list[str],
    fts_ranked: list[str],
    vector_weight: float = 0.5,
    fts_weight: float = 0.5,
    k: int = 60
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for rank, doc_id in enumerate(vector_ranked, start=1):
        scores[doc_id] = scores.get(doc_id, 0) + vector_weight / (k + rank)
    for rank, doc_id in enumerate(fts_ranked, start=1):
        scores[doc_id] = scores.get(doc_id, 0) + fts_weight / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])
```

### 3.2 Weight Selection Guidance

| Scenario | Vector Weight | FTS Weight | Rationale |
|----------|--------------|------------|-----------|
| Balanced (default) | 0.5 | 0.5 | Equal trust; suitable for most corpora |
| Semantic-heavy | 0.6–0.7 | 0.3–0.4 | Technical docs where synonyms and paraphrasing matter |
| Keyword-heavy | 0.3–0.4 | 0.6–0.7 | Error codes, SKUs, legal doc IDs, identifiers |
| Recency-sensitive | base 0.5/0.5 + heat boost | | Heat acts as post-fusion tiebreaker |

**Key principle from production systems:** Start with equal weights (0.5/0.5) and only adjust after running an evaluation set. The equal-weight default is usually fine.

**Source:** [Micelclaw — Hybrid Search with RRF](https://micelclaw.com/blog/hybrid-search-rrf/); [BigData Boutique — RRF Guide](https://bigdataboutique.com/blog/reciprocal-rank-fusion-how-it-works-and-when-to-use-it)

### 3.3 SQL Implementation of Weighted RRF

```sql
WITH vector_results AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(query_embedding)s) AS rank
  FROM messages
  ORDER BY embedding <=> %(query_embedding)s
  LIMIT %(candidate_limit)s
),
fts_results AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_vector, query, 32) DESC) AS rank
  FROM messages, plainto_tsquery('english', %(query_text)s) query
  WHERE search_vector @@ query
  ORDER BY ts_rank_cd(search_vector, query, 32) DESC
  LIMIT %(candidate_limit)s
)
SELECT
  COALESCE(v.id, f.id) AS id,
  COALESCE(%(vector_weight)s / (%(k)s + v.rank), 0.0) +
  COALESCE(%(fts_weight)s / (%(k)s + f.rank), 0.0) AS rrf_score
FROM vector_results v
FULL OUTER JOIN fts_results f ON v.id = f.id
ORDER BY rrf_score DESC
LIMIT %(final_limit)s;
```

**Source:** [pgvector official hybrid search example](https://github.com/pgvector/pgvector-python/blob/master/examples/hybrid_search/rrf.py)

---

## 4. Recency Decay with 90-Day Half-Life

### 4.1 The Decay Function

A recency boost should **never override relevance**. It should act as a tiebreaker or gentle boost. Recommended approach:

```sql
recency_boost = POW(0.5, (EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0) / 90.0)
```

This gives:
- **Created today:** boost = 1.0
- **90 days old:** boost = 0.5 (half-life)
- **180 days old:** boost = 0.25
- **365 days old:** boost = 0.0625
- **720 days old:** boost ≈ 0.004

### 4.2 Integration with RRF

Two patterns from production:

**Pattern A: Post-fusion multiplier** (recommended for P3-011)

```sql
final_score = rrf_score * (1.0 + %(recency_boost_weight)s * recency_boost)
```

Where `recency_boost_weight` controls max impact (e.g., 0.1 = max 10% boost). This ensures recency never dominates — a highly relevant but old document easily beats a marginally relevant new one.

**Source:** [Micelclaw — Hybrid Search with RRF](https://micelclaw.com/blog/hybrid-search-rrf/)

**Pattern B: Pre-fusion rank modifier**

Some implementations modify ranks directly: `modified_rank = rank * (2 - recency_boost)`, which pushes newer documents higher in the list before RRF. This is more aggressive and only recommended when recency is a primary signal (e.g., news search).

**Recommendation for P3-011:** Use Pattern A with `recency_boost_weight = 0.1` (max 10% boost).

### 4.3 SQL Implementation

```sql
-- recency_boost calculated once and applied per row
-- recency_half_life_days = 90
-- recency_boost_weight = 0.1 (max 10% boost)

WITH vector_results AS (...),
fts_results AS (...),
rrf_scores AS (
  SELECT
    COALESCE(v.id, f.id) AS id,
    COALESCE(1.0 / (60 + v.rank), 0.0) +
    COALESCE(1.0 / (60 + f.rank), 0.0) AS rrf_score,
    m.created_at
  FROM vector_results v
  FULL OUTER JOIN fts_results f ON v.id = f.id
  JOIN messages m ON m.id = COALESCE(v.id, f.id)
)
SELECT
  id,
  rrf_score * (1.0 + 0.1 * POW(0.5, (EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0) / 90.0)) AS final_score
FROM rrf_scores
ORDER BY final_score DESC
LIMIT %(final_limit)s;
```

### 4.4 Importance Scoring

For an "importance" or "priority" signal (e.g., pinned messages, starred docs, author authority):

```sql
-- Importance as an additional multiplier or additive term
-- Recommended: importance_factor in range [0.8, 1.2]

final_score = rrf_score * recency_boost * importance_factor
```

Or as an additional weighted rank in the RRF sum (treat importance as a third "retriever"):

```
RRF_score(d) = w_vec/(k + vec_rank) + w_fts/(k + fts_rank) + w_imp * importance_factor
```

Where `importance_factor` is a normalized value (e.g., `0.8 + 0.4 * normalized_importance`).

### 4.5 Temporal Boost (Advanced)

From the Micelclaw production system — if the query mentions an entity with upcoming events within ±7 days:

```sql
temporal_boost = 1 + 0.15 * proximity  -- proximity ∈ [0, 1]
```

This is optional and only applicable when a knowledge graph or calendar data exists. Not required for P3-011 but noted for future enhancement.

---

## 5. Multi-Signal Bonus (Importance Scoring Variation)

From the Micelclaw production system — a result appearing in multiple independent signals gets a bonus:

| Signals that found this result | Multiplier |
|------------------------------|-----------|
| 1 signal only | ×1.00 |
| 2 signals | ×1.25 |
| 3 signals | ×1.50 |

This rewards results independently confirmed by multiple methods. For P3-011 (2 signals: vector + FTS), the relevant case is:

| Signals | Multiplier |
|---------|-----------|
| Vector only OR FTS only | ×1.00 |
| Both vector AND FTS | ×1.25 |

**Implementation:** Track which signals produced each candidate during deduplication. Apply the bonus after RRF computation:

```sql
CASE
  WHEN v.id IS NOT NULL AND f.id IS NOT NULL THEN rrf_score * 1.25  -- both signals
  ELSE rrf_score                                                     -- one signal
END AS boosted_score
```

**Source:** [Micelclaw — Hybrid Search with RRF](https://micelclaw.com/blog/hybrid-search-rrf/)

---

## 6. HNSW ef_search Tuning (64–128) and Index Performance

### 6.1 HNSW Parameters

| Parameter | Default | Recommended for P3-011 | Effect |
|-----------|---------|----------------------|--------|
| `m` | 16 | 16 | Max connections per graph layer |
| `ef_construction` | 64 | 64–128 | Build-time candidate list (higher = better recall, slower build) |
| `ef_search` | 40 | 64–128 | Query-time candidate list (higher = better recall, slower query) |

**Source:** [pgvector README — HNSW](https://github.com/pgvector/pgvector#hnsw)

### 6.2 ef_search: The Key Tuning Knob

`ef_search` controls how many candidates are explored during ANN search:

```sql
-- Per-query override (recommended)
BEGIN;
SET LOCAL hnsw.ef_search = 100;
SELECT ... ORDER BY embedding <=> %(query)s LIMIT 10;
COMMIT;

-- Session-level
SET hnsw.ef_search = 100;
```

**Guidelines:**
- `ef_search` must be ≥ your `LIMIT` value (otherwise you can't return enough results)
- For `LIMIT 10` with hybrid search: `ef_search = 64` is a safe minimum
- For `LIMIT 20–50`: `ef_search = 100–128`
- The recall-vs-speed curve flattens above `ef_search = 200` for most datasets
- A good production starting point is `ef_search = 100`

**Source:** [Crunchy Data — HNSW Indexes with pgvector](https://www.crunchydata.com/blog/hnsw-indexes-with-postgres-and-pgvector); [Neon — Optimize pgvector Search](https://neon.com/docs/ai/ai-vector-search-optimization)

### 6.3 Index Creation

```sql
CREATE INDEX idx_messages_embedding
  ON messages USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

For production, create indexes **after** loading initial data, and use `CONCURRENTLY`:

```sql
CREATE INDEX CONCURRENTLY idx_messages_embedding
  ON messages USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

**Source:** [pgvector README](https://github.com/pgvector/pgvector#indexing)

### 6.4 Memory and Performance

- HNSW index for 500K vectors at 1536 dims ≈ 8GB+ (expect ~5–8% improvement in latency per 2x ef_search increase)
- Set `maintenance_work_mem` high during index builds: `SET maintenance_work_mem = '8GB';`
- For datasets where HNSW index doesn't fit in memory, consider **binary quantization** with re-ranking:
  ```sql
  CREATE INDEX ON messages USING hnsw ((binary_quantize(embedding)::bit(1536)) bit_hamming_ops);
  -- Then re-rank by full-precision cosine:
  SELECT * FROM (
    SELECT * FROM messages ORDER BY binary_quantize(embedding)::bit(1536) <~> binary_quantize(%(query)s) LIMIT 50
  ) sub ORDER BY embedding <=> %(query)s LIMIT 10;
  ```

**Source:** [pgvector README — Binary Quantization](https://github.com/pgvector/pgvector#binary-quantization); [Crunchy Data — HNSW](https://www.crunchydata.com/blog/hnsw-indexes-with-postgres-and-pgvector)

### 6.5 Iterative Index Scans (pgvector 0.8.0+)

For queries with `WHERE` filters (e.g., workspace_id), enable iterative scans:

```sql
SET hnsw.iterative_scan = strict_order;  -- exact ordering
-- or
SET hnsw.iterative_scan = relaxed_order; -- better recall, slightly out of order
```

Also controls:
- `hnsw.max_scan_tuples` (default 20000) — max tuples to visit during iterative scan
- `hnsw.scan_mem_multiplier` (default 1) — memory multiplier as fraction of `work_mem`

**Source:** [pgvector README — Iterative Index Scans](https://github.com/pgvector/pgvector#iterative-index-scans)

---

## 7. Full Hybrid Query Pattern (SQL CTE)

### 7.1 Complete Combined Query

```sql
-- Parameters: query_embedding, query_text, k=60, vector_weight=0.5, fts_weight=0.5
-- candidate_limit=50, final_limit=10, recency_weight=0.1, half_life_days=90

WITH vector_results AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %(query_embedding)s) AS rank
  FROM messages
  ORDER BY embedding <=> %(query_embedding)s
  LIMIT %(candidate_limit)s
),
fts_results AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(search_vector, plainto_tsquery('english', %(query_text)s), 32) DESC) AS rank
  FROM messages
  WHERE search_vector @@ plainto_tsquery('english', %(query_text)s)
  ORDER BY ts_rank_cd(search_vector, plainto_tsquery('english', %(query_text)s), 32) DESC
  LIMIT %(candidate_limit)s
),
rrf_scores AS (
  SELECT
    COALESCE(v.id, f.id) AS id,
    (COALESCE(%(vector_weight)s / (%(k)s + v.rank), 0.0) +
     COALESCE(%(fts_weight)s / (%(k)s + f.rank), 0.0)) AS rrf_score,
    CASE WHEN v.id IS NOT NULL AND f.id IS NOT NULL THEN 1.25 ELSE 1.0 END AS multi_signal_bonus
  FROM vector_results v
  FULL OUTER JOIN fts_results f ON v.id = f.id
)
SELECT
  r.id,
  m.content,
  m.title,
  m.created_at,
  r.rrf_score * r.multi_signal_bonus *
    (1.0 + %(recency_weight)s * POW(0.5, (EXTRACT(EPOCH FROM (NOW() - m.created_at)) / 86400.0) / %(half_life_days)s)) AS final_score
FROM rrf_scores r
JOIN messages m ON m.id = r.id
ORDER BY final_score DESC
LIMIT %(final_limit)s;
```

### 7.2 Parallel Execution (Application Layer)

```python
import asyncio

async def hybrid_search(conn, query_text, query_embedding, k=60, candidate_limit=50, final_limit=10):
    async def run_vector():
        # Execute vector search SQL
        ...

    async def run_fts():
        # Execute FTS SQL
        ...

    vector_ids, fts_ids = await asyncio.gather(run_vector(), run_fts())
    fused = weighted_rrf(vector_ids, fts_ids, k=k)
    return fused[:final_limit]
```

The parallel execution reduces wall-clock time because vector search (HNSW) and FTS (GIN index scan) run independently in the database.

**Source:** [Lucas Pessamai — Hybrid Search with pgvector](https://dev.to/lpossamai/building-hybrid-search-for-rag-combining-pgvector-and-full-text-search-with-reciprocal-rank-fusion-6nk)

---

## 8. Deterministic Test Strategies

### 8.1 Why Determinism Matters

Hybrid ranking with ANN indexes is **non-deterministic by nature** — HNSW returns approximations that can vary between runs, especially with concurrent writes or index changes. Tests must control for this.

### 8.2 Strategy 1: Exact Search Mode (For Tests)

Use sequential scan (disable index) in test assertions:

```sql
BEGIN;
SET LOCAL enable_indexscan = off;   -- disable HNSW
SET LOCAL enable_seqscan = on;      -- force exact NN search
-- Run hybrid query
SELECT ...
COMMIT;
```

**Source:** [pgvector README — Monitoring](https://github.com/pgvector/pgvector#monitoring)

### 8.3 Strategy 2: Frozen Dataset

Pin test data to known content with fixed IDs and known embedding vectors:

```python
# Test fixtures with pre-computed embeddings
test_messages = [
    {"id": 1, "title": "Error E100", "content": "Error code E100: connection timeout", "created_at": "2026-05-01"},
    {"id": 2, "title": "Network Setup", "content": "Configure network for production deployment", "created_at": "2026-03-15"},
    {"id": 3, "title": "API Reference", "content": "API endpoint documentation for v2", "created_at": "2026-01-20"},
]

# Pre-compute embeddings once, reuse in tests
test_embeddings = {
    "error e100 connection timeout": [0.1, 0.2, ...],  # Known vector
    "network configuration": [0.3, 0.1, ...],
    "api documentation": [0.2, 0.5, ...],
}
```

### 8.4 Strategy 3: Fixed Recency Reference

For recency tests, freeze `NOW()` using a mock or parameter:

```python
# Instead of NOW(), pass a reference timestamp
recency_reference = datetime(2026, 6, 2)  # Fixed test date
```

In SQL, replace `NOW()` with `%(reference_ts)s::timestamptz` for testability.

### 8.5 Strategy 4: Snapshot Testing for Sorting

Test that the **relative ordering** of a known result set is stable:

```python
def test_hybrid_ranking_order():
    # Given: known messages + known query
    # When: hybrid search returns results
    results = hybrid_search("error connection timeout", top_k=5)
    ids = [r.id for r in results]
    
    # Then: document 1 (exact error match) should be in top 3
    # Note: not testing exact position (which depends on ANN approximation),
    # but testing that relevant documents are within expected range
    assert 1 in ids[:3], "Exact error match should rank high"
    assert len(ids) == 5
    assert ids == sorted(ids, key=lambda id: expected_scores[id], reverse=True)
```

### 8.5 Strategy 5: Recall@K Testing

For regression testing, measure recall on a known query set:

```python
def test_recall_at_10():
    queries = [
        ("error timeout", [1, 4]),
        ("api setup", [2, 3, 5]),
        ("network config", [3, 6]),
    ]
    for query, expected_ids in queries:
        results = hybrid_search(query, top_k=10)
        found_ids = {r.id for r in results}
        recall = len(set(expected_ids) & found_ids) / len(expected_ids)
        assert recall >= 0.8, f"Recall {recall} < 0.8 for query '{query}'"
```

### 8.6 Key Testing Principles

1. **Test with exact search** (disable HNSW) for deterministic score verification
2. **Test with ANN enabled** for recall/speed benchmarks (tolerate minor rank variation)
3. **Freeze time** for recency decay tests
4. **Pre-compute known embeddings** to avoid depending on external embedding APIs
5. **Test ordering stability**, not exact positions, when using ANN
6. **Benchmark recall@K** across a fixed evaluation set to detect regressions

---

## 9. Recommended Parameters Summary

| Parameter | Recommended Value | Rationale | Source |
|-----------|------------------|-----------|--------|
| RRF k | 60 | Original paper default; flat optimum across [20, 100] | Cormack 2009 |
| Vector weight | 0.5 | Start equal; tune only with eval data | Consensus |
| FTS weight | 0.5 | Start equal; tune only with eval data | Consensus |
| Candidate pool per retriever | 50 | Over-fetch 5x for better fusion signal | Lucas Pessamai |
| Final result count | 10 | Standard top-k for RAG | General |
| Recency half-life | 90 days | P3-011 requirement | P3-011 spec |
| Recency boost weight | 0.1 (max 10%) | Never dominates relevance | Micelclaw |
| Multi-signal bonus (both) | ×1.25 | Rewards consensus across signals | Micelclaw |
| HNSW m | 16 | Default; good for 1536-dim vectors | pgvector |
| HNSW ef_construction | 64–128 | Higher for offline build; 128 safer | Neon docs |
| HNSW ef_search | 100 (range: 64–128) | Good balance for LIMIT 10–50 | Crunchy Data |
| FTS ranking function | `ts_rank_cd(tsv, query, 32)` | Cover density + normalization | PostgreSQL docs |
| FTS query parser | `plainto_tsquery('english', $q)` | Handles free-form user input | PostgreSQL docs |
| tsvector weights | Title='A', Content='B' | Title matches get priority | PostgreSQL docs |

---

## 10. Implementation Cautions

### 10.1 Order of Operations

1. **Candidate pool size matters:** Pulling 20 from each retriever and fusing to 10 consistently outperforms pulling 10 from each. Over-fetch 3–5× the final limit.
2. **Deduplication:** Use `FULL OUTER JOIN` with `COALESCE` for IDs appearing in only one result set. Missing IDs get 0 contribution from that signal.
3. **NULL/empty handling:** If one retriever returns zero results (e.g., no FTS matches), the RRF formula still works — contributions from the empty retriever are 0.

### 10.2 Performance Risks

1. **HNSW ef_search too low:** If `ef_search < LIMIT`, queries may return fewer results than requested. Always ensure `ef_search >= LIMIT`.
2. **Sequential scan fallback:** If the HNSW index cannot service the query (complex WHERE clauses, joins), Postgres may fall back to sequential scan without an error. Use `EXPLAIN (ANALYZE, BUFFERS)` to verify index usage.
3. **CTE materialization:** Postgres may materialize CTEs unexpectedly. For performance, use `AS MATERIALIZED` on CTEs that should be computed once.
4. **Maintenance work memory:** Set `maintenance_work_mem` high during index builds to avoid dramatic slowdown.

### 10.3 Recency Decay Risks

1. **Never let recency override relevance:** A 90-day-old document should still outrank a today document if relevance is significantly higher. The `recency_boost_weight = 0.1` ensures this.
2. **Reference timestamp:** Use `NOW()` consistently. If records are bulk-inserted with past dates, newly created documents won't automatically get a recency boost — test this.
3. **Timezone:** Ensure `created_at` timestamps are in a consistent timezone (UTC recommended). `NOW()` returns the current transaction's start time.

### 10.4 Testing Risks

1. **Non-deterministic ANN:** HNSW results vary between runs. Always test with exact search (index disabled) for score assertions.
2. **Embedding API dependency:** If tests call an external embedding API, they may be slow, flaky, or cost money. Pre-compute embeddings in test fixtures.
3. **Frozen time:** Recency tests will drift over time if `NOW()` is used directly. Always inject a reference timestamp.

### 10.5 ADR-009 Compliance

**Do not call OpenAI or other embedding APIs directly from the application.** Embeddings must go via 9Router/OpenRouter backend only. For P3-011:
- Embedding retrieval during search must use the pre-computed embeddings stored in the database
- No embedding creation should occur during query time
- Test fixtures should use pre-computed embeddings

### 10.6 pgvector Version Compatibility

- **pgvector 0.5.0+:** HNSW indexes available
- **pgvector 0.7.0+:** Half-precision vectors (`halfvec`), binary quantization
- **pgvector 0.8.0+:** Iterative index scans for filtered queries
- Keep pgvector updated to at least 0.7.x for production use

---

## 11. References

### Primary Sources
1. Cormack, G. V., Clarke, C. L. A., Büttcher, S. (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods.* SIGIR '09. https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
2. pgvector official README — HNSW Indexes. https://github.com/pgvector/pgvector#hnsw
3. pgvector official hybrid search example (RRF + cross-encoder). https://github.com/pgvector/pgvector-python/blob/master/examples/hybrid_search/rrf.py
4. PostgreSQL Documentation — Text Search Controls. https://www.postgresql.org/docs/current/textsearch-controls.html

### Production Case Studies
5. Lucas Pessamai — *Building Hybrid Search for RAG: Combining pgvector and Full-Text Search with Reciprocal Rank Fusion.* https://dev.to/lpossamai/building-hybrid-search-for-rag-combining-pgvector-and-full-text-search-with-reciprocal-rank-fusion-6nk
6. Gabriel Anhaia — *Hybrid Search in 100 Lines: BM25 + pgvector with RRF Merge.* https://dev.to/gabrielanhaia/hybrid-search-in-100-lines-bm25-pgvector-with-rrf-merge-58cn
7. Micelclaw — *#08 — Hybrid search with RRF: combining pgvector, tsvector, and a knowledge graph in one query.* https://micelclaw.com/blog/hybrid-search-rrf/
8. Serghei's Blog — *Reciprocal Rank Fusion: the one-line algorithm behind hybrid search.* https://blog.serghei.pl/posts/reciprocal-rank-fusion-explained/

### Benchmarks and Tuning Guides
9. OpenSearch — *Introducing reciprocal rank fusion for hybrid search.* https://opensearch.org/blog/introducing-reciprocal-rank-fusion-hybrid-search/
10. Crunchy Data — *HNSW Indexes with Postgres and pgvector.* https://www.crunchydata.com/blog/hnsw-indexes-with-postgres-and-pgvector
11. Neon — *Optimize pgvector search.* https://neon.com/docs/ai/ai-vector-search-optimization
12. BigData Boutique — *Reciprocal Rank Fusion (RRF): How It Works and When to Use It.* https://bigdataboutique.com/blog/reciprocal-rank-fusion-how-it-works-and-when-to-use-it
13. MariaDB Docs — *Optimizing Hybrid Search Query with Reciprocal Rank Fusion (RRF).* https://mariadb.com/docs/server/reference/sql-structure/vectors/optimizing-hybrid-search-query-with-reciprocal-rank-fusion-rrf

### Related ADRs
14. ADR-009 — Embeddings go via 9Router/OpenRouter backend only (no direct OpenAI calls)

---

*End of research report — P3-011 external best-practice reference.*
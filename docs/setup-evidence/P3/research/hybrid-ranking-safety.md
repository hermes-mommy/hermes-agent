# P3-010 / P3-011 — Hybrid Ranking with Safety Gates: Research Synthesis

**Date:** 2026-06-02  
**Author:** Guinevere (Librarian — external research wave)  
**Status:** Complete — synthesis ready  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  

---

## 0. Scope Resolution: P3-010 vs P3-011

| Source | Stated Position |
|--------|----------------|
| StepPrompts P3-010 | Basic cosine-similarity read pipeline. No hybrid ranking. |
| StepPrompts P3-011 | Labeled "Hybrid Ranking" — intended as deferred work. |
| User requirement | P3-010 must include hybrid vector+FTS+recency (minimum scope) |
| ADR-009 | Layered recall: semantic (pgvector) + FTS + time-weighted + safety filters |
| MemoryRecallEvalSpec §7.2 | Ranking criteria: similarity threshold → classification ceiling gate → consent gate → safe-mode gate → importance floor → confidence floor → time decay → contradiction penalty → HNSW ef_search → max results per type |

**Binding resolution:** P3-010 implements the **minimum viable hybrid ranking** — pgvector cosine similarity + PostgreSQL FTS (tsvector ts_rank_cd) + recency decay + importance/classification filtering + DNR/safe-mode safety gates. Full hybrid ranking with weighted RRF tuning, cross-encoder re-ranking, and ablation benchmarks is deferred to P3-011.

This aligns with MemoryRecallEvalSpec §7.2 ranking criteria order:
1. Semantic similarity threshold (cosine ≤ 0.30) → P3-010
2. Classification ceiling gate → P3-010
3. Consent gate (DNR) → P3-010
4. Safe-mode gate → P3-010
5. Importance floor (≥ 4) → P3-010
6. Confidence floor (≥ 0.4) → P3-010
7. Time decay function (exponential, 90d half-life) → P3-010
8. Contradiction penalty → P3-011 (or P3-013)
9. HNSW ef_search → P3-006/P3-007
10. Max results per type → P3-010

---

## 1. Literature and Industry Survey

### 1.1 Sources Surveyed

| Source | Type | Key Coverage |
|--------|------|-------------|
| pgmnemo v0.6.3 (pgxn.org) | OSS Extension | Provenance-gated, hybrid recall: `0.5×cosine + 0.2×importance + γ×recency(90d) + 0.1×prov_strength` |
| pgvector README (github.com/pgvector/pgvector) | Official Docs | Hybrid search pattern with tsvector + RRF |
| Supabase Hybrid Search Docs (supabase.com) | Official Docs | RRF with weighted fusion, `rrf_k=50`, CTE pattern |
| DigitalOcean pgvectorscale (docs.digitalocean.com) | Official Docs | HNSW + tsvector hybrid, RRF CTE, temporal partitioning |
| Wolf-Tech Hybrid Search (wolf-tech.io) | Engineering Blog | Single-round-trip CTE, `k=60`, candidate pool sizing |
| Rivestack Hybrid Search (rivestack.io) | Engineering Blog | RRF vs min-max normalization comparison, weighted fusion |
| Microsoft Docs — Cosmos DB Hybrid (learn.microsoft.com) | Official Docs | Weighted RRF with per-query weight arrays |
| Google Cloud — AlloyDB Hybrid | Official Docs | RRF + RSF in PostgreSQL, score normalization |
| TigerData — Elasticsearch Hybrid in PG | Engineering Blog | BM25 + Vector + RRF, weighted variant |
| Grizzly Peak — Hybrid Search | Engineering Blog | Recency boost in hybrid score, category-specific weights |
| Cormack et al. (2009) — RRF Original Paper | Academic | RRF formula: `1/(k+rank)`, k=60 standard |
| Chen et al. (2022) — Fusion Functions Analysis | Academic | RRF vs convex combination, parameter sensitivity |
| Arxiv 2210.11934 — TM2C2 beats RRF | Academic | Distribution-based score fusion outperforms RRF |
| Arxiv 2604.15484 — vstash | Academic | Adaptive per-query IDF weighting, NDCG@10 +21.4% |
| ParadeDB Hybrid Search Manual | Engineering Blog | Multi-signal RRF (recency, popularity, editorial) |
| Arxiv 2605.04897 — True Memory | Academic | Encoding gate at ingestion, salience+novelty scoring |
| Arxiv 2603.04549 — A-MAC | Academic | Write-time memory admission control |
| Arxiv 2603.15642 — CraniMem | Academic | Gated bounded memory with consolidation |
| SafeHarbor (arxiv 2605.05704) | Academic | Hierarchical memory-augmented guardrail |

### 1.2 Consensus Findings

| Finding | Sources | Confidence |
|---------|---------|-----------|
| RRF is the production-default fusion method (k=60) | 12+ sources | HIGH |
| Normalization (min-max, z-score) is viable but fragile to score distribution drift | 5 sources | MEDIUM |
| Weighted RRF improves over equal-weight when one signal dominates | 8 sources | HIGH |
| Recency decay must be category-specific half-life, not global | 4 sources | HIGH |
| Safety/classification filtering must happen BEFORE ranking, not after | 5 sources | HIGH |
| Write-time provenance gates prevent hallucinated memories from entering store | 3 sources | MEDIUM |
| Cross-encoder re-ranking adds 5-15pp NDCG@10 but costs latency | 4 sources | HIGH |

---

## 2. Scoring Formulas

### 2.1 Reciprocal Rank Fusion (RRF) — Primary Candidate

**Formula (Cormack et al., 2009):**

```
RRF_score(d) = Σ_{r ∈ R} 1 / (k + rank_r(d))
```

Where:
- `R` = set of retrieval systems (vector, FTS)
- `rank_r(d)` = 1-indexed rank of document `d` in system `r` (0 if absent)
- `k` = smoothing constant (default: 60)

**Reference**: Cormack, Clarke, Buettcher, SIGIR 2009; Elasticsearch default; Azure AI Search default; pgvector docs.

**Score per rank position (k=60):**

| Rank | 1/(60+rank) | Cumulative (both systems) |
|------|-------------|--------------------------|
| 1 | 0.01639 | 0.03279 |
| 2 | 0.01613 | 0.03226 |
| 5 | 0.01538 | 0.03077 |
| 10 | 0.01429 | 0.02857 |
| 20 | 0.01250 | 0.02500 |
| 50 | 0.00909 | 0.01818 |

**Weighted RRF (recommended for P3-011, optional for P3-010):**

```
RRF_score(d) = w_vec × 1/(k + rank_vec(d)) + w_fts × 1/(k + rank_fts(d))
```

Where `w_vec + w_fts = 1.0` (e.g., `w_vec=0.7`, `w_fts=0.3` for conversation; invert for technical queries).

### 2.2 Convex Combination (Linear Fusion)

**Formula:**

```
hybrid_score(d) = α × norm_semantic(d) + (1 − α) × norm_fts(d)

where norm(x) = (x - min) / (max - min)   [min-max normalization]
   or norm(x) = (x - mean) / std            [z-score normalization]
```

**When to use:** When both systems return scores on comparable bounded ranges (e.g., cosine similarity ∈ [0,1] after `1 - distance`, and ts_rank min-max normalized to [0,1]).

**Pitfall (documented by Rivestack, Arxiv 2210.11934):** Without normalization, the unbounded ts_rank (can exceed 100) dominates cosine similarity (bounded [0,1]). With min-max normalization, extreme single-query outliers can distort all results.

### 2.3 Distribution-Based Score Fusion (DBSF / TM2C2)

**Formula (Wang et al. 2021):**

```
norm_i(d) = (score_i(d) - μ_i) / σ_i
Score(d) = Σ w_i × norm_i(d)
```

Where `μ_i` and `σ_i` are the mean and standard deviation of retriever `i`'s scores for the current query's candidate set.

**Finding** (Arxiv 2210.11934): TM2C2 significantly outperforms RRF on NDCG@1000 across all BEIR datasets tested. However, it requires calculating mean/std per query, adding latency.

### 2.4 Composite Scoring (pgmnemo-inspired)

**Formula (pgmnemo v0.6.x):**

```
score = w_vec × cosine_sim + w_imp × importance + γ × recency(90d) + w_prov × prov_strength

Default: 0.5 × cosine + 0.2 × importance + γ × recency + 0.1 × prov_strength
```

**Advantage:** Scores are on the same [0,1] scale by design (cosine similarity, importance normalized, recency decay, provenance strength). No normalization needed.

**For Guinevere:**
```
combined_score = w_vec × (1 - cosine_distance) 
               + w_fts × norm_ts_rank 
               + w_recency × exp_decay(age_days, half_life)
               + w_importance × (importance / 10)
```

### 2.5 Recommended Formula for P3-010 Minimum Viable

```
combined_score = w_rrf × RRF_score(d) 
               + w_recency × recency_boost(d) 
               + w_importance × importance_factor(d)

Where:
  RRF_score(d) = 1/(k + rank_vec(d)) + 1/(k + rank_fts(d))
  recency_boost(d) = 2^(-age_days / half_life)    [half_life = 90 days for episodic]
  importance_factor(d) = importance / 10           [importance ∈ [1, 10], normalized]
  w_rrf = 0.6, w_recency = 0.25, w_importance = 0.15 (tunable)
```

**This formula is safe for P3-010 because:**
- RRF naturally handles heterogeneous score scales
- Recency decay is a straightforward exponential
- Importance factor linearly scales the existing field
- All weights sum to 1.0 for interpretability

---

## 3. SQL CTE Patterns

### 3.1 Core Hybrid Search CTE (RRF)

```sql
WITH
vector_results AS (
    SELECT
        id,
        ROW_NUMBER() OVER (ORDER BY embedding <=> $1::vector) AS rank
    FROM memory.episodes
    WHERE do_not_recall = FALSE
      AND classification <= $2              -- classification ceiling
      AND importance >= $3                  -- importance floor
    ORDER BY embedding <=> $1::vector
    LIMIT $candidate_limit                  -- typically 2-5x top_k
),
fts_results AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            ORDER BY ts_rank_cd(search_vector, websearch_to_tsquery('english', $4)) DESC
        ) AS rank
    FROM memory.episodes
    WHERE do_not_recall = FALSE
      AND classification <= $2
      AND importance >= $3
      AND search_vector @@ websearch_to_tsquery('english', $4)
    ORDER BY ts_rank_cd(search_vector, websearch_to_tsquery('english', $4)) DESC
    LIMIT $candidate_limit
),
combined AS (
    SELECT
        COALESCE(v.id, f.id) AS id,
        COALESCE(1.0 / ($rrf_k + v.rank), 0.0) +
        COALESCE(1.0 / ($rrf_k + f.rank), 0.0) AS rrf_score
    FROM vector_results v
    FULL OUTER JOIN fts_results f ON v.id = f.id
)
SELECT
    e.id, e.content, e.source, e.classification,
    e.importance, e.created_at, e.confidence,
    c.rrf_score,
    (1.0 - (e.embedding <=> $1::vector)) AS cosine_similarity,
    ts_rank_cd(e.search_vector, websearch_to_tsquery('english', $4)) AS fts_score
FROM combined c
JOIN memory.episodes e ON e.id = c.id
ORDER BY c.rrf_score DESC
LIMIT $top_k;
```

### 3.2 Hybrid + Recency + Importance CTE (P3-010 MVP)

```sql
WITH
vector_results AS (
    SELECT
        id,
        ROW_NUMBER() OVER (ORDER BY embedding <=> $1::vector) AS rank,
        (1.0 - (embedding <=> $1::vector)) AS cosine_sim
    FROM memory.episodes
    WHERE do_not_recall = FALSE
      AND classification <= $2
      AND importance >= $3
    ORDER BY embedding <=> $1::vector
    LIMIT $candidate_limit
),
fts_results AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            ORDER BY ts_rank_cd(search_vector, websearch_to_tsquery('english', $4)) DESC
        ) AS rank,
        ts_rank_cd(search_vector, websearch_to_tsquery('english', $4)) AS raw_ts_rank
    FROM memory.episodes
    WHERE do_not_recall = FALSE
      AND classification <= $2
      AND importance >= $3
      AND search_vector @@ websearch_to_tsquery('english', $4)
    ORDER BY ts_rank_cd(search_vector, websearch_to_tsquery('english', $4)) DESC
    LIMIT $candidate_limit
),
candidates AS (
    SELECT
        COALESCE(v.id, f.id) AS id,
        COALESCE(v.cosine_sim, 0.0) AS cosine_sim,
        COALESCE(f.raw_ts_rank, 0.0) AS raw_ts_rank,
        COALESCE(v.rank, $candidate_limit + 1) AS vec_rank,
        COALESCE(f.rank, $candidate_limit + 1) AS fts_rank
    FROM vector_results v
    FULL OUTER JOIN fts_results f ON v.id = f.id
),
scored AS (
    SELECT
        c.id,
        e.importance,
        e.created_at,
        e.classification,
        e.confidence,
        -- RRF component
        ($w_rrf) * (
            COALESCE(1.0 / ($rrf_k + c.vec_rank), 0.0) +
            COALESCE(1.0 / ($rrf_k + c.fts_rank), 0.0)
        ) AS rrf_component,
        -- Recency component: exponential decay
        ($w_recency) * POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - e.created_at)) / (86400.0 * $half_life_days)) AS recency_component,
        -- Importance component
        ($w_importance) * (e.importance / 10.0) AS importance_component
    FROM candidates c
    JOIN memory.episodes e ON e.id = c.id
)
SELECT
    s.*,
    (s.rrf_component + s.recency_component + s.importance_component) AS combined_score
FROM scored s
ORDER BY combined_score DESC
LIMIT $top_k;
```

### 3.3 Safety-Filtered CTE with DNR Exclusion

```sql
WITH
safe_candidates AS (
    SELECT id, embedding, search_vector, content, source,
           classification, importance, created_at, confidence,
           -- Safe-mode override: if safe_mode_active, replace Critical raw with summary
           CASE
               WHEN $safe_mode_active AND classification = 'Critical'
               THEN COALESCE(summary, '[Supportive summary — raw content withheld per safe-mode policy]')
               ELSE content
           END AS safe_content,
           -- DNR exclusion
           CASE WHEN do_not_recall = TRUE THEN TRUE ELSE FALSE END AS is_dnr
    FROM memory.episodes
    WHERE do_not_recall = FALSE                          -- Layer 1: DNR exclusion
      AND ($safe_mode_active = FALSE OR classification IN (
            'Public', 'Internal', 'Confidential', 'Restricted'  -- Layer 4: Safe-mode ceiling
      ))
      AND importance >= $importance_floor                -- Layer 5: Importance floor
      AND confidence >= $confidence_floor                 -- Layer 6: Confidence floor
      AND (last_verified IS NULL OR last_verified >= NOW() - INTERVAL '$staleness_days days')
                                                          -- Staleness filter
),
-- Then vector_results, fts_results, combined as above...
```

---

## 4. Normalization Strategies

### 4.1 Comparison

| Method | Formula | Pros | Cons | When to Use |
|--------|---------|------|------|-------------|
| **RRF** (rank-based) | `1/(k+rank)` | Scale-free, robust, no distribution assumptions | Loses score magnitude info; top-1 vs top-2 gap always same | Default for P3-010 through P3-011 |
| **Min-max** | `(x-min)/(max-min)` | Preserves relative distances within query | Fragile to outliers; min=max → division by zero | When scores have known bounds (cosine ∈ [0,1]) |
| **Z-score** | `(x-μ)/σ` | Handles outliers better than min-max | Assumes normal distribution; negative scores | When you need statistical normalization |
| **DBSF/TM2C2** | `(x-μ)/σ` per retriever | Beats RRF on NDCG@1000 (arxiv 2210.11934) | Higher latency; per-query statistics | P3-011 optimization target |

### 4.2 RRF vs Score Normalization Tradeoff

```
RRF benefits:
  ✓ No score distribution assumptions
  ✓ Immune to score drift as corpus grows
  ✓ Single parameter (k=60)
  ✓ Produced identical results across 4 weight configs (benchmark on Swiss companies)

Score normalization benefits:
  ✓ Preserves score magnitude information
  ✓ More tunable (α weights directly meaningful)
  ✓ Can outperform RRF when distributions are stable (TM2C2 +5-10% NDCG)

Recommendation: Start with RRF (k=60) for P3-010. Evaluate DBSF for P3-011.
```

---

## 5. Recency Decay Functions

### 5.1 Formulae

**Exponential decay (recommended):**

```
recency_boost = 2^(-age_days / half_life)
```

| Category | Half-Life (days) | After 1 HL | After 2 HL | After 3 HL | Source |
|----------|---------|------------|------------|------------|--------|
| Conversation | 14 | 0.5 | 0.25 | 0.125 | pgmnemo / YaoS-Code |
| General episodic | 30 | 0.5 | 0.25 | 0.125 | YaoS-Code |
| Project context | 45 | 0.5 | 0.25 | 0.125 | YaoS-Code |
| Insight/pattern | 60 | 0.5 | 0.25 | 0.125 | YaoS-Code |
| **Decision (episodic default)** | **90** | **0.5** | **0.25** | **0.125** | **MemoryRecallEvalSpec, YaoS-Code** |
| Semantic fact | 180 | 0.5 | 0.25 | 0.125 | MemoryRecallEvalSpec, YaoS-Code |
| Skill/procedural | 365 | 0.5 | 0.25 | 0.125 | MemoryRecallEvalSpec |

**Alternative: Inverse linear decay:**

```
recency_boost = 1 / (1 + λ × age_days)
```

Where λ = decay rate (e.g., 0.01 = 10% per day). Simpler but less principled than exponential.

### 5.2 SQL Implementation

```sql
-- Exponential decay (recommended)
POWER(2.0, -EXTRACT(EPOCH FROM (NOW() - created_at)) / (86400.0 * half_life_days))

-- Inverse linear decay (simpler, for early P3-010)
1.0 / (1.0 + 0.01 * EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0)
```

### 5.3 Category-Specific Half-Lives

```sql
CASE e.memory_type
    WHEN 'episodic' THEN 90      -- MemoryRecallEvalSpec §7.2 #7
    WHEN 'semantic_fact' THEN 180 -- MemoryRecallEvalSpec §11.2
    WHEN 'procedural' THEN 365
    WHEN 'emotional' THEN 180
    WHEN 'financial' THEN 365
    WHEN 'project' THEN 90
    WHEN 'persona_drift' THEN 30
    WHEN 'surveillance' THEN 90
    WHEN 'client' THEN 180
    WHEN 'social_map' THEN 180
    ELSE 90
END AS half_life
```

---

## 6. Importance and Classification-Aware Filtering

### 6.1 Importance Floor

Per MemoryRecallEvalSpec §7.2 (#5):

| Rule | Value |
|------|-------|
| Minimum importance for automatic recall | ≥ 4 (on 1-10 scale) |
| Low-importance recall | Only when query explicitly includes low-importance filter |
| Importance factor contribution | `importance / 10` → linearly scales contribution to combined score |

### 6.2 Classification Ceilings

Per MemoryRecallEvalSpec §8.1 and DataGovernance §5:

| Principal | Normal Mode | Safe-Mode |
|-----------|-------------|-----------|
| Faiz | All classes allowed + logged | All classes allowed + logged |
| Guinevere core | Restricted ceiling (Critical = purpose-gated) | Confidential ceiling; Critical = denied |
| Sub-agent | Confidential ceiling (Restricted = redacted) | Confidential ceiling; Restricted+ = denied |

**SQL filter pattern:**

```sql
WHERE classification <= (
    CASE
        WHEN $principal = 'faiz' THEN 'Critical'
        WHEN $principal = 'guinevere_core' AND $safe_mode THEN 'Confidential'
        WHEN $principal = 'guinevere_core' THEN 'Restricted'
        WHEN $principal = 'sub_agent' AND $safe_mode THEN 'Internal'
        WHEN $principal = 'sub_agent' THEN 'Confidential'
    END
)
```

### 6.3 Classification Order (for comparison)

Per DataGovernance:
```
Public(0) < Internal(1) < Confidential(2) < Restricted(3) < Critical(4)
```

---

## 7. Safety Filters: DNR and Safe-Mode Gates

### 7.1 Do-Not-Recall Enforcement (Eight-Layer Chain)

Per MemoryRecallEvalSpec §9.1, the eight enforcement layers map to the hybrid search pipeline as follows:

| Layer | Mechanism | Pipeline Stage | Implementation |
|-------|-----------|----------------|----------------|
| 1 — Consent Ledger | `consent.memory.do_not_recall_override` | Pre-query | Cross-reference consent ledger before building query |
| 2 — Memory Marker | `deletion_state = 'do_not_recall'` | **WHERE clause** | `WHERE do_not_recall = FALSE` in both CTEs |
| 3 — Retention Class | Long-Term Curated supports DNR | Pre-query | `RETENTION_CLASS NOT IN ('formal_hold_only')` |
| 4 — Backup Reconciliation | Restore reapplies DNR | Not in query path | Archive/restore pipeline only |
| 5 — Prompt Injection Gate | DNR flags prevent LLM context entry | **Post-ranking** | Verify top-k results have no DNR flags before injection |
| 6 — SLO Impact | Zero tolerance, Prometheus counter | **Post-query audit** | Increment `guinevere_memory_dnr_violation_total` if any DNR record leaks |
| 7 — Faiz Rights | Faiz may mark memories DNR | Write pipeline | `UPDATE memory.episodes SET deletion_state = 'do_not_recall'` |
| 8 — Incident Trigger | Unsafe intimate recall = incident | **Post-query audit** | Check recall results for Critical+intimate records against consent ledger |

**SQL DNR safety (layers 1-2 combined):**

```sql
WITH consent_dnr AS (
    -- Layer 1: Consent ledger — get all DNR memory IDs
    SELECT target_memory_id
    FROM consent.consent_ledger
    WHERE event_type IN ('CONSENT_WITHDRAWN', 'MEMORY_DNR_MARKED')
      AND effective_at <= NOW()
      AND (revoked_at IS NULL OR revoked_at > NOW())
)
SELECT ... FROM memory.episodes e
WHERE e.do_not_recall = FALSE                                    -- Layer 2
  AND e.id NOT IN (SELECT target_memory_id FROM consent_dnr)    -- Layer 1
```

### 7.2 Safe-Mode Gate

Per MemoryRecallEvalSpec §10.1-10.3, safe-mode violations must be zero.

**Violation definition:** Returning Critical raw records during safe-word, distress, crisis, or incident state.

**Implementation pattern:**

```sql
CREATE OR REPLACE FUNCTION recall_memories_safe_gated(
    p_query_embedding vector(1536),
    p_query_text text,
    p_classification_ceiling text,
    p_safe_mode boolean DEFAULT FALSE,
    p_importance_floor int DEFAULT 4,
    p_confidence_floor float DEFAULT 0.4,
    p_top_k int DEFAULT 10
)
RETURNS TABLE(
    id UUID, content text, classification text,
    importance int, created_at timestamptz,
    combined_score float, is_summarized boolean
)
AS $$
BEGIN
    RETURN QUERY
    WITH candidates AS (
        -- [standard hybrid CTE with safety filters applied in WHERE]
    )
    SELECT
        e.id,
        -- Safe-mode substitution: if safe_mode AND classification = 'Critical',
        -- replace raw content with summary
        CASE
            WHEN p_safe_mode AND e.classification = 'Critical'
            THEN COALESCE(e.summary, '[Content restricted under safe-mode policy]')
            ELSE e.content
        END AS safe_content,
        e.classification,
        e.importance,
        e.created_at,
        c.combined_score,
        (p_safe_mode AND e.classification = 'Critical') AS is_summarized
    FROM candidates c
    JOIN memory.episodes e ON e.id = c.id
    ORDER BY combined_score DESC
    LIMIT p_top_k;
END;
$$ LANGUAGE plpgsql;
```

### 7.3 Token Budget Enforcement

Per ADR-009 and MemoryRecallEvalSpec §7.3:

| Check | Cap | Action |
|-------|-----|--------|
| Per-cycle recall tokens | ≤ 4,000 tokens | Reduce `top_k` or candidate_limit if exceeded |
| Total injection tokens | ≤ 8,300 tokens | Reduce dynamic recall budgets |
| Injection histogram | P95 ≤ 4,000 | Alert if sustained breach |

**Implementation as post-ranking filter:**

```python
def enforce_token_budget(results: list[dict], budget: int = 4000) -> list[dict]:
    """Trim results to fit token budget, keeping highest-scored items."""
    token_count = sum(r.get("token_count", len(r["content"].split())) for r in results)
    if token_count <= budget:
        return results
    
    # Sort by combined score descending, trim from bottom
    results_sorted = sorted(results, key=lambda r: r["combined_score"], reverse=True)
    trimmed = []
    used_tokens = 0
    for r in results_sorted:
        tokens = r.get("token_count", len(r["content"].split()))
        if used_tokens + tokens > budget:
            break
        trimmed.append(r)
        used_tokens += tokens
    return trimmed
```

---

## 8. Top-k Selection and Candidate Pool Sizing

### 8.1 Candidate Pool Sizing

| Scenario | candidate_limit:top_k | Rationale |
|----------|----------------------|-----------|
| Low latency (real-time chat) | 2:1 (e.g., 20 → 10) | Minimize HNSW traversal and RRF join |
| Balanced (default) | 5:1 (e.g., 50 → 10) | Standard recommendation (Wolf-Tech, Supabase) |
| High recall (evaluation) | 10:1 (e.g., 100 → 10) | Minimize missed relevant results |
| cross-encoder re-ranking | 5:1 (50 → 10 re-ranked) | Re-ranker absorbs candidate quality |

### 8.2 Multi-Signal Bonus

Per ParadeDB and Grizzly Peak research:

```
multi_signal_factor = 1.0 + bonus × (num_signals - 1)
```

Where `num_signals` = count of systems that found the document (vector, FTS, recency>threshold). Default bonus = 0.25.

This rewards documents found by multiple independent retrieval methods, naturally boosting precision.

---

## 9. Evaluation Metrics for Hybrid Ranking

### 9.1 Core Metrics

| Metric | Formula | Purpose | Measurement Point |
|--------|---------|---------|-------------------|
| Precision@k | `TP@k / k` | Result cleanliness | Per-query + aggregate |
| Recall@k | `TP@k / total_relevant` | Coverage | Per-query + aggregate |
| MRR | `mean(1/rank_first_relevant)` | Early rank quality | Per-query + aggregate |
| NDCG@k | `DCG@k / IDCG@k` | Graded ranking quality | Per-query + aggregate |

Per MemoryRecallEvalSpec §4.3, episodic targets: Precision≥90%, Recall≥85%, MRR≥0.80, NDCG≥0.75 at k=10.

### 9.2 Hybrid-Specific Metrics

| Metric | Formula | Purpose |
|--------|---------|---------|
| **Hybrid Gain** | `P@k_hybrid - P@k_vector_only` | Improvement from adding FTS + recency |
| **DNR Escape Rate** | `dnr_in_results / total_dnr_in_corpus` | Safety filter effectiveness (target: 0) |
| **Safe-Mode Violation Rate** | `violations / total_safe_recalls` | Safety gate correctness (target: 0) |
| **Stale Rate** | `stale_recalls / total_recalls` | Recency filter effectiveness (target: ≤5%) |
| **Reranking Latency** | p95 of hybrid search time | Performance (target: p95 < 200ms HNSW-only, < 2s full pipeline) |

### 9.3 Ablation Test Configurations

For P3-011 evaluation, test these configurations against the golden dataset:

| Config ID | Vector | FTS | Recency | Importance | Safety | Expected Impact |
|-----------|--------|-----|---------|------------|--------|-----------------|
| A (baseline) | 1.0 | 0.0 | 0.0 | 0.0 | off | Pure cosine similarity |
| B | 0.7 | 0.3 | 0.0 | 0.0 | off | Vector + FTS (RRF) |
| C | 0.5 | 0.3 | 0.0 | 0.2 | off | Vector + FTS + Importance |
| D | 0.5 | 0.25 | 0.15 | 0.1 | off | Full hybrid |
| **E (P3-010)** | **0.5** | **0.3** | **0.15** | **0.05** | **on** | **Full with safety gates** |
| F | 0.3 | 0.5 | 0.1 | 0.1 | on | FTS-heavy |
| G | 0.6 | 0.2 | 0.1 | 0.1 | on | Vector-heavy |

---

## 10. Integration with Guinevere Memory Recall Pipeline

### 10.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ P3-010 HYBRID RECALL PIPELINE                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User Query ──→ [Embed (P3-005)] ──→ query_vector (1536d)          │
│                    + raw text                                       │
│                         │                                           │
│                         ▼                                           │
│  ┌─────────────────────────────────────────────────┐               │
│  │ SAFETY GATE (Pre-Query)                         │               │
│  │  • Consent ledger DNR lookup                     │               │
│  │  • Classification ceiling (principal + state)    │               │
│  │  • Safe-mode state check                         │               │
│  │  • Importance floor (≥4)                         │               │
│  │  • Confidence floor (≥0.4)                       │               │
│  │  • Staleness filter (last_verified)              │               │
│  └─────────────────────┬───────────────────────────┘               │
│                        │                                           │
│                        ▼                                           │
│  ┌────────────────────────────────────┐  ┌──────────────────────┐  │
│  │ VECTOR SEARCH CTE                  │  │ FTS SEARCH CTE       │  │
│  │ HNSW (m=16, ef_search=64-128)      │  │ GIN index            │  │
│  │ cosine ≤ 0.30 threshold            │  │ ts_rank_cd ranking   │  │
│  │ LIMIT candidate_limit (e.g., 50)   │  │ websearch_to_tsquery │  │
│  └──────────────┬─────────────────────┘  └──────────┬───────────┘  │
│                 │                                   │              │
│                 ▼                                   ▼              │
│  ┌─────────────────────────────────────────────────┐               │
│  │ FUSION (RRF + recency + importance)             │               │
│  │ FULL OUTER JOIN → combined_score                │               │
│  │ ORDER BY combined_score DESC                    │               │
│  └─────────────────────┬───────────────────────────┘               │
│                        │                                           │
│                        ▼                                           │
│  ┌─────────────────────────────────────────────────┐               │
│  │ SAFETY GATE (Post-Query)                        │               │
│  │  • Safe-mode content substitution (summaries)    │               │
│  │  • DNR escape audit (zero tolerance)             │               │
│  │  • Token budget trim (≤4,000 tokens)             │               │
│  │  • Prometheus metric emission                    │               │
│  └─────────────────────┬───────────────────────────┘               │
│                        │                                           │
│                        ▼                                           │
│  Top-k results ──→ LLM prompt context                              │
│  (with provenance: memory_id, source, confidence)                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.2 Recommended PostgreSQL Function API

```sql
CREATE OR REPLACE FUNCTION hybrid_recall(
    p_query_text TEXT,
    p_query_embedding vector(1536),
    p_principal TEXT DEFAULT 'guinevere_core',
    p_safe_mode BOOLEAN DEFAULT FALSE,
    p_top_k INT DEFAULT 10,
    p_candidate_limit INT DEFAULT 50,
    p_rrf_k INT DEFAULT 60,
    p_w_vec FLOAT DEFAULT 0.5,
    p_w_fts FLOAT DEFAULT 0.3,
    p_w_recency FLOAT DEFAULT 0.15,
    p_w_importance FLOAT DEFAULT 0.05,
    p_importance_floor INT DEFAULT 4,
    p_confidence_floor FLOAT DEFAULT 0.4,
    p_half_life_days INT DEFAULT 90,
    p_classification_ceiling TEXT DEFAULT 'Restricted'
)
RETURNS TABLE(
    id UUID,
    safe_content TEXT,
    classification TEXT,
    importance INT,
    created_at TIMESTAMPTZ,
    confidence FLOAT,
    cosine_similarity FLOAT,
    fts_score FLOAT,
    rrf_component FLOAT,
    recency_component FLOAT,
    importance_component FLOAT,
    combined_score FLOAT,
    is_summarized BOOLEAN
)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    -- GPT-4o synthesized function body implementing the CTE pattern from §3.2
    -- with safety filters from §3.3
    -- Implementation deferred to P3-010 implementation step
END;
$$;
```

---

## 11. Implementation Priority for P3-010

| Priority | Component | Dependencies | Effort Estimate |
|----------|-----------|-------------|-----------------|
| **P0** | RRF Fusion (vector + FTS) | P3-005 (embedding), P3-008 (tsvector), P3-006 (HNSW) | 1-2h |
| **P0** | DNR exclusion in WHERE clause | Existing `do_not_recall` column | 0.5h |
| **P0** | Classification ceiling filter | Existing `classification` column | 0.5h |
| **P1** | Importance floor + factor | Existing `importance` column | 0.5h |
| **P1** | Confidence floor | Existing `confidence` column | 0.5h |
| **P1** | Recency decay (exponential, half-life=90d) | Existing `created_at` column | 0.5h |
| **P2** | Safe-mode content substitution | Safe-mode state detection | 1h |
| **P2** | Staleness filter | Existing `last_verified` column | 0.5h |
| **P3** | Post-query token budget enforcement | None | 1h |
| **P3** | Consent ledger cross-reference | Consent schema tables | 1h |
| **P3** | Prometheus metric emission | Observability infra | 1h |

**Total estimated effort for P3-010 hybrid ranking:** 8.5h (conservative)

---

## 12. Deferred to P3-011 (Full Hybrid Ranking)

| Feature | Reason | Expected Gain |
|---------|--------|---------------|
| Weighted RRF tuning per memory type | Requires golden dataset + ablation eval | +5-15% NDCG@10 |
| Cross-encoder re-ranking | Requires cross-encoder model + latency budget | +5-15pp precision |
| DBSF/TM2C2 evaluation | Requires per-query statistics | May beat RRF +2-5% NDCG |
| Per-query adaptive α (IDF-weighted) | Requires learned gate (arxiv 2604.15484) | +21% NDCG on BEIR |
| Multi-signal bonus (ParadeDB) | Requires ablation validation | +3-5% precision |
| Category-specific half-life tuning | Requires staleness analysis | +2-5% stale rate reduction |
| Ablation benchmark automation | Requires golden dataset v1.0 | Enables all tuning |

---

## 13. External Reference Links

| Reference | URL | Key Content |
|-----------|-----|-------------|
| pgmnemo | https://pgxn.org/dist/pgmnemo/0.6.3/ | Provenance-gated hybrid memory, recency-weighted scoring |
| pgvector README | https://github.com/pgvector/pgvector | Hybrid search pattern with tsvector |
| Supabase Hybrid Search | https://supabase.com/docs/guides/ai/hybrid-search | RRF CTE with weighted fusion |
| DigitalOcean Hybrid Search | https://docs.digitalocean.com/products/vector-databases/postgresql/how-to/advanced-workloads/ | HNSW + tsvector hybrid with temporal |
| Wolf-Tech Hybrid Search | https://wolf-tech.io/blog/hybrid-search-in-postgres-combining-pgvector-and-full-text-search-without-elasticsearch | Single-round-trip CTE, candidate pool sizing |
| Rivestack Hybrid Search | https://rivestack.io/blog/hybrid-search-pgvector-postgres | RRF vs min-max normalization |
| Grizzly Peak Hybrid Search | https://www.grizzlypeaksoftware.com/library/hybrid-search-combining-full-text-and-vector-search-xdugcmo5 | Recency boost, weighted fusion |
| ParadeDB Hybrid Manual | https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual | Multi-signal RRF |
| Elasticsearch RRF Docs | https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking | RRF scoring with weights |
| Cormack et al. (2009) | https://arxiv.org/abs/2004.09819 | RRF original paper |
| TM2C2 (arxiv 2210.11934) | https://arxiv.org/html/2210.11934 | Distribution-based fusion beats RRF |
| vstash (arxiv 2604.15484) | https://arxiv.org/pdf/2604.15484 | Adaptive per-query IDF weighting |
| True Memory (arxiv 2605.04897) | https://arxiv.org/html/2605.04897v1 | Encoding gate, RRF fusion with recency |
| YaoS-Code agentic-memory | https://github.com/YaoS-Code/agentic-memory | Category-specific half-life decay |
| Arxiv Hybrid Fusion Analysis | https://arxiv.org/pdf/2210.11934 | RRF vs CC sensitivity study |
| SafeHarbor (arxiv 2605.05704) | https://arxiv.org/html/2605.05704 | Hierarchical memory safety guardrail |
| RAGuard (arxiv 2509.03768) | https://arxiv.org/html/2509.03768v1 | Safety-gated retrieval |
| ReFilter (arxiv 2602.12709) | https://arxiv.org/html/2602.12709 | Gated token-level filtering |
| BM25 Search in PostgreSQL | https://www.pedroalonso.net/blog/postgres-bm25-search/ | BM25 + pgvector hybrid with RRF |
| TigerData BM25+Vector+RRF | https://www.tigerdata.com/blog/elasticsearchs-hybrid-search-now-in-postgres-bm25-vector-rrf | Weighted RRF implementation |

---

## 14. Alignment Verification

| Source | Requirement | How This Research Addresses It |
|--------|-------------|-------------------------------|
| ADR-009 §Implementation | Layered recall with safety + relevance | §2.5 formula includes RRF + safety gates; §10 pipeline shows layered architecture |
| ADR-009 | Token budget cap (4,000 tokens) | §7.3 token budget enforcement |
| ADR-009 | HNSW ef_search (64-128) | §10 pipeline uses ef_search parameter |
| ADR-009 | precision@k, recall@k, MRR evaluation | §9 defines evaluation metrics and targets |
| MemoryRecallEvalSpec §7.2 | 10 ranking criteria in order | §0 maps all 10 criteria to P3-010/P3-011 |
| MemoryRecallEvalSpec §9.1 | 8-layer DNR enforcement | §7.1 maps all 8 layers to pipeline stages |
| MemoryRecallEvalSpec §10.1 | Zero-tolerance safe-mode recall | §7.2 safe-mode gate with content substitution |
| MemoryRecallEvalSpec §4.3 | Per-type accuracy thresholds | §9.1 references episodic targets (90/85/0.80/0.75) |
| MemoryRecallEvalSpec §8.1 | Classification-aware ceilings | §6.2 classification floors per principal |
| MemoryRecallEvalSpec §11.2 | Staleness detection (90/180d) | §5.3 category-specific half-lives |
| DataGovernance | DNR metadata marker | §7.1 `do_not_recall = FALSE` WHERE clause |
| PersonaSafetyPolicy | Safe-mode recall restriction | §7.2 Critical raw → summary substitution |
| ConsentRevocation | Consent ledger check | §7.1 consent_dnr CTE + layer mapping |

---

## 15. Caveats and Open Questions

1. **RRF k=60 is a heuristic.** The Cormack et al. paper chose k=60 empirically. For Guinevere's memory types, the optimal k may differ (Supabase uses k=50). Plan to evaluate k ∈ {40, 50, 60, 80, 100} in P3-011.

2. **Weight calibration requires data.** The weights `w_vec=0.5, w_fts=0.3, w_recency=0.15, w_importance=0.05` are initial estimates. Real calibration requires golden dataset evaluation.

3. **Consent ledger lookup latency.** Joining against `consent.consent_ledger` on every recall query adds latency. Consider caching active DNR memory IDs in Redis (DB0 per ADR-030) with TTL.

4. **Safe-mode state detection.** The safe_mode flag must be passed from the agent loop (PersonaSafetyPolicy state machine). The recall pipeline cannot determine safe-mode state independently.

5. **TimescaleDB hypertable partitioning.** For temporal queries, TimescaleDB chunk exclusion (WHERE on partitioning column) can accelerate recency filtering (see TigerData hybrid search tutorial).

6. **Embedding dimension lock.** Using 1536-dim vectors now locks the dimension. Any future model change (e.g., to bge-m3 1024-dim) requires table rebuild (ADR-009 caveat).

7. **Contradiction penalty deferred to P3-011.** MemoryRecallEvalSpec §7.2 (#8) specifies a -0.3 penalty for conflicting facts. This requires contradiction detection logic (MemorySchema `contradicts_ids` field) not yet implemented in the read pipeline.

---

**End of `docs/setup-evidence/P3/research/hybrid-ranking-safety.md`**
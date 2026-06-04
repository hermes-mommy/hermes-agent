# Phase 3 Memory Bridge: Embedding Alternatives Research

**Date:** 2026-06-04  
**Context:** Phase 3 Memory Bridge migration. Critical gap G-B1: embeddings fail with HTTP 400 from 9Router (`localhost:20128/v1/embeddings`) for `openai/text-embedding-3-small`. Current system passes `embedding_service=None`.  
**Goal:** Determine 9Router embedding support status, identify viable alternatives, and define fallback strategies to unblock vector search.

---

## 1. 9Router Embedding Model Support Status

**Finding: 9Router FULLY supports embedding models.**  
9Router provides a dedicated OpenAI-compatible `/v1/embeddings` endpoint and explicitly supports routing embedding requests to multiple upstream providers.

**Supported Embedding Providers in 9Router:**
- OpenAI / OpenRouter
- Cohere
- Mistral
- NVIDIA
- Together AI
- Fireworks
- Voyage AI
- Jina AI
- Vercel AI Gateway (recently added via PR #1268)

**Evidence:**  
- [9Router SKILL.md - Embeddings Capability](https://github.com/decolua/9router/blob/master/skills/9router/SKILL.md) documents `curl $NINEROUTER_URL/v1/models/embedding` to discover available embedding models.
- [9Router PR #1268](https://github.com/decolua/9router/pull/1268) explicitly adds Vercel AI Gateway and OpenAI-compatible embedding provider routing.

### Why the HTTP 400 Error Occurs
The `400 Bad Request` for `openai/text-embedding-3-small` is **not** a lack of feature support. It is a configuration or routing mismatch. Common causes:
1. **Missing Provider Connection:** The 9Router dashboard does not have an active, authenticated connection to an embedding-capable provider (e.g., OpenRouter or OpenAI) with a valid API key.
2. **Model Alias Mismatch:** 9Router may not recognize `openai/text-embedding-3-small` unless it is explicitly mapped in the dashboard's model aliases or the upstream provider expects exactly that string (OpenRouter does, but the provider connection must be active).
3. **Missing `dimensions` Parameter:** Some upstream providers require the `dimensions: 1536` parameter to be explicitly passed in the request body, though OpenRouter typically handles this gracefully.

**Actionable Fix:** Open the 9Router dashboard (`http://localhost:20128/dashboard`), navigate to **Providers**, and ensure an OpenAI or OpenRouter connection is active with valid credentials. Verify the model alias `openai/text-embedding-3-small` is routable.

---

## 2. Current Schema Constraint: The 1536-Dimension Lock

**Critical Finding:** The existing PostgreSQL `pgvector` schema is strictly locked to **1536 dimensions** (`vector(1536)`).  
This matches OpenAI's `text-embedding-3-small` default output.

**Evidence:**  
- [`docs/setup-evidence/P3/STEP-P3-007/benchmark.sql`](C:\Users\faizz\guinevere\docs\setup-evidence\P3\STEP-P3-007\benchmark.sql): `ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536))`
- [`adr/ADR-009-memory-recall-semantic-search-strategy.md`](C:\Users\faizz\guinevere\adr\ADR-009-memory-recall-semantic-search-strategy.md): "Use OpenAI `text-embedding-3-small` with 1536 dimensions."

**Implication:** Switching to a local model like `all-MiniLM-L6-v2` (384d) or `bge-large-en-v1.5` (1024d) **cannot be done via a simple config change**. It requires:
- A destructive schema migration (dropping/recreating HNSW indexes).
- Re-embedding the entire existing memory corpus.
- Or, implementing a dimension projection/padding layer (see Section 5).

---

## 3. Viable Alternative Embedding Providers/Models

If 9Router routing remains broken, the following alternatives can supplement or replace it:

### Option A: Fix 9Router Routing (Recommended)
- **Provider:** OpenRouter → OpenAI `text-embedding-3-small`
- **Cost:** $0.02 / 1M tokens (~$0.06–$0.50/month at projected Guinevere volume).
- **Quality:** MTEB ~62.3, adequate multilingual (Indonesian/English) performance.
- **Action:** Configure 9Router dashboard with valid OpenRouter API key. No code changes required.

### Option B: Direct API Fallback (Bypass 9Router for Embeddings Only)
- **Provider:** Direct OpenAI API (`https://api.openai.com/v1`) or Direct OpenRouter API.
- **Cost:** Same as Option A.
- **Quality:** Identical to Option A.
- **Action:** Modify `EmbeddingConfig` in `src/memory/embeddings.py` to use a dedicated `OPENAI_API_KEY` and `base_url="https://api.openai.com/v1"` *only* for the embedding service, keeping LLM routing through 9Router intact.

### Option C: Local SentenceTransformers (Requires Schema Adaptation)
- **Model:** `BAAI/bge-large-en-v1.5` (1024d) or `nomic-embed-text-v1.5` (768d).
- **Cost:** $0 (compute only, requires GPU for production latency).
- **Quality:** MTEB ~63.6 (bge-large), competitive with OpenAI.
- **Action:** Requires implementing a **dimension projection matrix** to map 1024d/768d vectors to the existing 1536d schema, or accepting a schema migration. `all-MiniLM-L6-v2` (384d) is too low-quality for production semantic search and should be avoided unless strictly cache-only.

---

## 4. Quality, Latency, and Cost Comparison

| Model / Provider | Dimensions | Cost (per 1M tokens) | p50 Latency | MTEB Avg Score | Multilingual (ID/EN) |
|---|---|---|---|---|---|
| **OpenAI `text-embedding-3-small`** | 1536 | $0.02 | ~120ms (API) | ~62.3 | Good (adequate for RAG) |
| **OpenAI `text-embedding-3-large`** | 3072 (MRL) | $0.13 | ~180ms (API) | ~64.6 | Better, but 6.5x cost |
| **Local `bge-large-en-v1.5`** | 1024 | $0 (GPU compute) | ~15ms (GPU) | ~63.6 | Good (requires projection to 1536d) |
| **Local `all-MiniLM-L6-v2`** | 384 | $0 (CPU/GPU) | ~5-15ms (CPU) | ~56.3 | Poor (not recommended for production) |
| **Voyage `voyage-3-lite`** | 512 | $0.02 | ~100ms (API) | ~62.0 | Excellent multilingual |

**Key Takeaway:** `text-embedding-3-small` remains the optimal balance of cost, quality, and schema compatibility. Local models only become cost-effective at >20B tokens/month or when strict data residency (no external API calls) is mandated.

---

## 5. Embedding Fallback Strategies (Best Practices)

To achieve zero-downtime vector search, implement a **tiered fallback strategy**. Do not mix providers blindly, as cosine similarity becomes meaningless across different embedding spaces.

### Strategy 1: Provider Chain with Circuit Breaker (Recommended)
1. **Primary:** `openai/text-embedding-3-small` via 9Router.
2. **Fallback 1:** Direct OpenAI/OpenRouter API (bypasses 9Router routing layer).
3. **Fallback 2:** Local `bge-large-en-v1.5` with **query-side dimension projection**.

**Implementation Pattern:**
```python
class FallbackEmbeddingService:
    def __init__(self, primary, fallbacks: list):
        self.primary = primary
        self.fallbacks = fallbacks
        self.primary_unavailable = False

    async def aembed(self, text: str) -> list[float]:
        if self.primary_unavailable:
            return await self._try_fallbacks(text)
        try:
            return await self.primary.aembed(text)
        except (HTTPStatusError, TimeoutException):
            self.primary_unavailable = True
            return await self._try_fallbacks(text)

    async def _try_fallbacks(self, text: str) -> list[float]:
        for fallback in self.fallbacks:
            try:
                vec = await fallback.aembed(text)
                # If fallback dimension != 1536, apply projection matrix here
                return self._project_to_1536(vec, fallback.dimension)
            except Exception:
                continue
        raise RuntimeError("All embedding providers failed")
```

### Strategy 2: Query-Side Dimension Projection (For Local Fallbacks)
If falling back to a local model with different dimensions (e.g., 1024d), **do not re-embed the entire database**. Instead:
1. Keep the existing `pgvector` index in 1536d space.
2. When a fallback model generates a 1024d query vector, multiply it by a pre-trained **projection matrix** (`W`) to translate it into the 1536d space: `query_vec_1536 = query_vec_1024 @ W`.
3. This adds <1ms of local compute latency and preserves ~96%+ of baseline retrieval quality.
4. **Evidence:** [Schift Blog: The Embedding Failover Pattern](https://schift.io/blog/embedding-failover-pattern) demonstrates this exact pattern for zero-downtime provider failover.

### Strategy 3: Graceful Degradation to Keyword Search
If all embedding providers fail (e.g., total network outage), the system must fail closed to **FTS5 full-text search** rather than returning empty results. The `memory.semantic_facts` and `memory.episodes` tables should retain `tsvector` columns as a fallback retrieval mechanism.

---

## 6. Actionable Recommendations for Phase 3

1. **Immediate Fix (Unblock G-B1):**  
   Verify the 9Router dashboard has an active OpenRouter/OpenAI provider connection with a valid API key. Test via:  
   ```bash
   curl -X POST http://localhost:20128/v1/embeddings \
     -H "Authorization: Bearer <9router-key>" \
     -H "Content-Type: application/json" \
     -d '{"model": "openai/text-embedding-3-small", "input": "test", "dimensions": 1536}'
   ```
2. **Implement Fallback Wrapper:**  
   Update `src/memory/embeddings.py` to include the `FallbackEmbeddingService` pattern, with Direct OpenAI API as the first fallback.
3. **Do Not Migrate Schema Yet:**  
   Avoid switching to local SentenceTransformers models (384d/1024d) unless Faiz explicitly approves the destructive schema migration or the projection matrix implementation. The $0.02/1M token cost of `text-embedding-3-small` is negligible at current projected volumes.
4. **Consent Gate Verification:**  
   Ensure the privacy guardrails documented in [`docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md`](C:\Users\faizz\guinevere\docs\setup-evidence\P3\research\faiz-consent-embedding-privacy.md) are enforced: no raw Critical memory sent externally, Restricted memory redacted where feasible.

---

## 7. References & Evidence

- [9Router Embeddings Documentation](https://github.com/decolua/9router/blob/master/skills/9router/SKILL.md)
- [OpenRouter Embeddings API Reference](https://openrouter.ai/docs/api/reference/embeddings.mdx)
- [ADR-009: Memory Recall & Semantic Search Strategy](C:\Users\faizz\guinevere\adr\ADR-009-memory-recall-semantic-search-strategy.md)
- [Schift: The Embedding Failover Pattern](https://schift.io/blog/embedding-failover-pattern)
- [Guinevere Faiz Consent Embedding Privacy](C:\Users\faizz\guinevere\docs\setup-evidence\P3\research\faiz-consent-embedding-privacy.md)

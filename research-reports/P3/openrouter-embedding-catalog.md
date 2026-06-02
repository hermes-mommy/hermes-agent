# OpenRouter Embedding Model Catalog — Guinevere P3

**Date**: 2026-06-02  
**Author**: The Librarian (Guinevere research sub-agent)  
**Purpose**: Comprehensive catalog of all embedding models available on OpenRouter, for Guinevere P3 embedding model selection.  
**Context**: Guinevere memory system, VPS 15GB RAM / guinevere.slice 8GB, PostgreSQL pgvector 0.8.2 HNSW, mixed sensitive memory, primary language Indonesian+English, budget target ~$2/month, workload 3.3M embedding tokens/month, current MiniLM L6 cached 384-dim. ADR-009 currently says OpenAI text-embedding-3-small 1536 via 9Router/OpenRouter.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Model Catalog — Full Table](#model-catalog--full-table)
3. [Detailed Model Notes](#detailed-model-notes)
4. [Cost Analysis at 3.3M Tokens/Month](#cost-analysis-at-33m-tokensmonth)
5. [Privacy Path Notes](#privacy-path-notes)
6. [Dimension & Storage Implications](#dimension--storage-implications)
7. [Multilingual Support (Indonesian + English)](#multilingual-support-indonesian--english)
8. [Benchmark Context](#benchmark-context)
9. [Models NOT Available on OpenRouter (but requested)](#models-not-available-on-openrouter-but-requested)
10. [Key Insights for Guinevere](#key-insights-for-guinevere)
11. [Sources](#sources)

---

## Executive Summary

OpenRouter hosts **26+ embedding models** as of June 2026 across 15 model families. Pricing ranges from **free** (NVIDIA Nemotron Embed VL 1B V2) to **$0.20/M tokens** (Gemini Embedding 2). At 3.3M tokens/month, costs range from **$0.00/month** (free tier) to **$0.66/month** (most expensive).

Key standouts for Guinevere's constraints ($2/month budget, Indonesian+English, 8GB RAM, pgvector HNSW):

| Tier | Model | Cost/mo | Dims | Multilingual | Notes |
|------|-------|---------|------|-------------|-------|
| **Ultra-cheap** | Perplexity Embed V1 0.6B | $0.013 | 1024 (MRL) | Likely good | 92% of voyage-3.5 quality per benchmarks |
| **Best value** | Qwen3 Embedding 8B | $0.033 | 4096 (MRL) | Excellent (100+ langs) | #1 MTEB multilingual leaderboard |
| **Current ADR** | OpenAI text-embedding-3-small | $0.066 | 1536 | Good | Matches current ADR-009 |
| **Free** | NVIDIA Nemotron Embed VL 1B V2 | $0.00 | ? | English+vision | 131K context, multimodal |
| **Upgrade path** | Gemini Embedding 2 | $0.66 | 3072 (MRL) | Multilingual | Best quality, recent May 2026 |

---

## Model Catalog — Full Table

### Provider: Google

| # | OpenRouter Slug | Model Name | Dims | Context | Price/M | Released | MTEB | Multilingual |
|---|----------------|-----------|------|---------|---------|---------|------|-------------|
| 1 | `google/gemini-embedding-2` | Gemini Embedding 2 | 128-3072 (MRL) | 8K | $0.20 | May 20, 2026 | TBD (new) | Yes (multimodal: text+image+video+audio) |
| 2 | `google/gemini-embedding-2-preview` | Gemini Embedding 2 Preview | 128-3072 (MRL) | 8K | $0.20 | Apr 17, 2026 | TBD | Same as above |
| 3 | `google/gemini-embedding-001` | Gemini Embedding 001 | 128-3072 (MRL) | 20K* | $0.15 | Oct 31, 2025 | 68.17 @ 1536-dim | Yes — top of MTEB multilingual |

\* OpenRouter shows 20K context but Google official docs state 2,048 token input limit for gemini-embedding-001. This discrepancy requires verification.

### Provider: OpenAI

| # | OpenRouter Slug | Model Name | Dims | Context | Price/M | Released | MTEB | Multilingual |
|---|----------------|-----------|------|---------|---------|---------|------|-------------|
| 4 | `openai/text-embedding-3-large` | Text Embedding 3 Large | 3072 (MRL: 256-3072) | 8K | $0.13 | Oct 30, 2025 | ~64+ | Good |
| 5 | `openai/text-embedding-3-small` | Text Embedding 3 Small | 1536 (MRL: 256-1536) | 8K | $0.02 | Oct 30, 2025 | ~62+ | Good |
| 6 | `openai/text-embedding-ada-002` | Text Embedding Ada 002 | 1536 | 8K | $0.10 | Oct 30, 2025 | ~61 | Moderate (legacy) |

### Provider: Qwen (Alibaba)

| # | OpenRouter Slug | Model Name | Dims | Context | Price/M | Released | MTEB | Multilingual |
|---|----------------|-----------|------|---------|---------|---------|------|-------------|
| 7 | `qwen/qwen3-embedding-8b` | Qwen3 Embedding 8B | 4096 (MRL: 32-4096) | 32K | $0.01 | Oct 28, 2025 | **70.58** (MTEB multi #1) | Excellent — 100+ languages |
| 8 | `qwen/qwen3-embedding-4b` | Qwen3 Embedding 4B | 2560 (MRL: 32-2560) | 33K | $0.02 | Oct 28, 2025 | 69.45 | Excellent |
| 9 | `qwen/qwen3-embedding-0.6b` | Qwen3 Embedding 0.6B | 1024 (MRL: 32-1024) | 8K | Not listed | Nov 5, 2025 | 64.33 | Excellent |

### Provider: Perplexity

| # | OpenRouter Slug | Model Name | Dims | Context | Price/M | Released | MTEB | Multilingual |
|---|----------------|-----------|------|---------|---------|---------|------|-------------|
| 10 | `perplexity/pplx-embed-v1-4b` | Embed V1 4B | 2560 (MRL: 128-2560) | 32K | $0.03 | Mar 16, 2026 | ~high | Good (web-scale training) |
| 11 | `perplexity/pplx-embed-v1-0.6b` | Embed V1 0.6B | 1024 (MRL: 128-1024) | 32K | $0.004 | Mar 16, 2026 | 0.8604 nDCG@3* | Good |

\* Benchmark from ai-multiple.com independent evaluation — 92% of voyage-3.5 quality at 15x cheaper.

### Provider: NVIDIA

| # | OpenRouter Slug | Model Name | Dims | Context | Price/M | Released | MTEB | Multilingual |
|---|----------------|-----------|------|---------|---------|---------|------|-------------|
| 12 | `nvidia/llama-nemotron-embed-vl-1b-v2:free` | Llama Nemotron Embed VL 1B V2 | Not specified | 131K | **Free** | Feb 25, 2026 | N/A | Multimodal (text+image) |

### Provider: BAAI

| # | OpenRouter Slug | Model Name | Dims | Context | Price/M | Released | MTEB | Multilingual |
|---|----------------|-----------|------|---------|---------|---------|------|-------------|
| 13 | `baai/bge-m3` | BGE-M3 | 1024 | 8K | $0.01 | Nov 18, 2025 | Strong | Yes — true multilingual dense retrieval |
| 14 | `baai/bge-large-en-v1.5` | BGE Large EN v1.5 | 1024 | 8K | $0.01 | Nov 18, 2025 | Strong | English-only |
| 15 | `baai/bge-base-en-v1.5` | BGE Base EN v1.5 | 768 | 8K | $0.005 | Nov 18, 2025 | Moderate | English-only |

### Provider: Thenlper (Alibaba DAMO)

| # | OpenRouter Slug | Model Name | Dims | Context | Price/M | Released | MTEB | Multilingual |
|---|----------------|-----------|------|---------|---------|---------|------|-------------|
| 16 | `thenlper/gte-large` | GTE-Large | 1024 | 8K | $0.01 | Nov 18, 2025 | Strong | English |
| 17 | `thenlper/gte-base` | GTE-Base | 768 | 8K | $0.005 | Nov 18, 2025 | Moderate | English |

### Provider: Intfloat (Microsoft)

| # | OpenRouter Slug | Model Name | Dims | Context | Price/M | Released | MTEB | Multilingual |
|---|----------------|-----------|------|---------|---------|---------|------|-------------|
| 18 | `intfloat/multilingual-e5-large` | Multilingual E5 Large | 1024 | 8K | $0.01 | Nov 18, 2025 | Strong | Yes — 90+ languages |
| 19 | `intfloat/e5-large-v2` | E5 Large v2 | 1024 | 8K | $0.01 | Nov 18, 2025 | Strong | English |
| 20 | `intfloat/e5-base-v2` | E5 Base v2 | 768 | 8K | $0.005 | Nov 18, 2025 | Moderate | English |

### Provider: Sentence Transformers

| # | OpenRouter Slug | Model Name | Dims | Context | Price/M | Released | MTEB | Multilingual |
|---|----------------|-----------|------|---------|---------|---------|------|-------------|
| 21 | `sentence-transformers/all-MiniLM-L6-v2` | all-MiniLM-L6-v2 | **384** | 8K | $0.005 | Nov 18, 2025 | ~58 | English (current Guinevere) |
| 22 | `sentence-transformers/all-MiniLM-L12-v2` | all-MiniLM-L12-v2 | **384** | 8K | $0.005 | Nov 18, 2025 | ~59 | English |
| 23 | `sentence-transformers/paraphrase-MiniLM-L6-v2` | paraphrase-MiniLM-L6-v2 | **384** | 8K | $0.005 | Nov 18, 2025 | ~57 | English |
| 24 | `sentence-transformers/all-mpnet-base-v2` | all-mpnet-base-v2 | 768 | 8K | $0.005 | Nov 17, 2025 | ~61 | English |
| 25 | `sentence-transformers/multi-qa-mpnet-base-dot-v1` | multi-qa-mpnet-base-dot-v1 | 768 | 8K | $0.005 | Nov 18, 2025 | QA-optimized | English |

---

## Detailed Model Notes

### Gemini Embedding 2 (google/gemini-embedding-2)
- **Cost at 3.3M/mo**: $0.66
- **Privacy**: Data leaves VPS to Google via OpenRouter. OpenRouter's `provider.data_collection` can be set to `deny` to restrict providers that don't store data.
- **Key advantage**: Multimodal (text+image+video+audio+PDF), flexible dims 128-3072, auto-normalizes truncated dims
- **Latency**: Google is a mature provider; OpenRouter weighted avg input price ~$0.381/M indicating multiple provider tiers
- **Released**: May 20, 2026 — very new, limited MTEB data yet

### Gemini Embedding 2 Preview (google/gemini-embedding-2-preview)
- Same as above but preview label; available since Apr 17, 2026
- 3.52B weekly tokens on OpenRouter

### Gemini Embedding 001 (google/gemini-embedding-001)
- **Cost at 3.3M/mo**: $0.495
- **Context discrepancy**: OpenRouter says 20K; Google official docs say 2,048 token limit. OpenRouter may process differently or have different provider behavior.
- **MTEB**: 68.17 at 1536-dim, one of the highest on multilingual leaderboard
- **Note**: OpenRouter shows 20K context, which is significantly higher than Google's documented 2,048. This needs verification before relying on.

### Qwen3 Embedding 8B (qwen/qwen3-embedding-8b)
- **Cost at 3.3M/mo**: $0.033
- **The strongest value proposition**: #1 on MTEB multilingual leaderboard (70.58), 100+ languages, 32K context, MRL from 32 to 4096 dims, instruction-aware
- **Privacy**: Served via OpenRouter; data leaves VPS. Weights available on HuggingFace (Apache 2.0) — could self-host if RAM permits (8B params ~16GB, exceeds 8GB slice)
- **Weekly tokens**: 91.6B — very popular, well-provisioned
- **MRL**: Can reduce dims via dimensions parameter (32-4096)

### Qwen3 Embedding 4B (qwen/qwen3-embedding-4b)
- **Cost at 3.3M/mo**: $0.066
- 4B params, 2560 dim (MRL), 33K context
- MTEB 69.45 — very close to 8B quality

### Qwen3 Embedding 0.6B (qwen/qwen3-embedding-0.6b)
- No price listed on OpenRouter page (no active providers visible)
- 1024-dim, MRL, 32K context (OpenRouter shows 8K)
- MTEB 64.33 — decent for size

### Perplexity Embed V1 0.6B (perplexity/pplx-embed-v1-0.6b)
- **Cost at 3.3M/mo**: $0.013
- **Cheapest non-free model**: $0.004/M tokens — 0.66p of your $2 monthly budget
- 1024-dim with MRL (128-1024), supports INT8/BINARY quantization
- Independent benchmark: 0.8604 nDCG@3 (92% of voyage-3.5 quality)
- 32K context window
- 5.59B weekly tokens on OpenRouter

### Perplexity Embed V1 4B (perplexity/pplx-embed-v1-4b)
- **Cost at 3.3M/mo**: $0.099
- 2560-dim with MRL (128-2560), INT8/BINARY quantization
- 32K context
- Lower weekly usage (5.56B) vs 0.6B (5.59B) — surprising parity

### NVIDIA Llama Nemotron Embed VL 1B V2 (free)
- **Cost at 3.3M/mo**: $0.00
- 131K context — largest context window of any OpenRouter embedding model
- Multimodal: text+image understanding
- Free tier may have rate limits; OpenRouter free plan limited to 50 reqs/day
- NVIDIA provides infrastructure on OpenRouter

### OpenAI text-embedding-3-small
- **Cost at 3.3M/mo**: $0.066
- Current ADR-009 recommendation (1536-dim via 9Router/OpenRouter)
- 62.9B weekly tokens on OpenRouter — most popular embedding model
- Good multilingual support
- MRL: can reduce from 1536 to as low as 256

### OpenAI text-embedding-3-large
- **Cost at 3.3M/mo**: $0.429
- 3072-dim (MRL), 15B weekly tokens
- 6.5x more expensive than text-embedding-3-small
- Better quality but diminishing returns for the cost increase

### BAAI bge-m3
- **Cost at 3.3M/mo**: $0.033
- 1024-dim, 8K ctx, multilingual
- 8.88B weekly tokens — popular
- BGE-M3 supports dense + sparse + multi-vector retrieval natively

### Sentence Transformers (all current models)
- **all-MiniLM-L6-v2**: Current Guinevere model, 384-dim, $0.005/M → $0.0165/mo
- **all-mpnet-base-v2**: Upgrade path within Sentence Transformers family, 768-dim, same $0.005/M
- **multi-qa-mpnet-base-dot-v1**: 768-dim, optimized for QA retrieval

---

## Cost Analysis at 3.3M Tokens/Month

| Rank | Model | Price/M | Monthly Cost | % of $2 Budget |
|------|-------|---------|-------------|---------------|
| 1 | NVIDIA Nemotron Embed VL 1B V2 (free) | $0.000 | $0.000 | 0% |
| 2 | Perplexity Embed V1 0.6B | $0.004 | $0.013 | 0.7% |
| 3 | bge-base-en-v1.5 / GTE-Base / E5-Base-v2 / MiniLM family / all-mpnet-base-v2 | $0.005 | $0.017 | 0.8% |
| 4 | Qwen3 Embedding 8B / bge-m3 / multilingual-e5-large / e5-large-v2 / gte-large / bge-large-en-v1.5 | $0.01 | $0.033 | 1.7% |
| 5 | text-embedding-3-small | $0.02 | $0.066 | 3.3% |
| 6 | Perplexity Embed V1 4B | $0.03 | $0.099 | 5.0% |
| 7 | text-embedding-ada-002 | $0.10 | $0.33 | 16.5% |
| 8 | text-embedding-3-large | $0.13 | $0.429 | 21.5% |
| 9 | Gemini Embedding 001 | $0.15 | $0.495 | 24.8% |
| 10 | Gemini Embedding 2 / 2 Preview | $0.20 | $0.66 | 33.0% |

**Even the most expensive model (Gemini Embedding 2 at $0.66/mo) fits within the $2 budget.** All models are affordable at 3.3M tokens/month.

---

## Privacy Path Notes

**All OpenRouter embedding models route data through OpenRouter's API, meaning data leaves your VPS.**

Key privacy considerations:

| Factor | Detail |
|--------|--------|
| **OpenRouter data collection** | Pay-as-you-go plan: data may be stored non-transiently. Use `provider.data_collection: "deny"` to restrict. |
| **Provider data policies** | Varies — Google, OpenAI, Mistral, Perplexity, NVIDIA all have different data retention policies |
| **Self-hostable alternatives** | Qwen3 Embedding (Apache 2.0), BGE (MIT), GTE, E5 — could run locally but 8GB RAM limits 8B models |
| **pgvector setup** | All vectors stored in PostgreSQL pgvector on VPS — no change |
| **9Router/OpenRouter relay** | Current architecture uses 9Router as relay to OpenRouter; no architectural change needed |

**Sensitive memory implications**: If Guinevere stores sensitive/personal memories, the embedding provider sees the text content during encoding. For maximum privacy, self-hosting a model like bge-m3 (1.5GB) or all-MiniLM-L6-v2 (90MB) on the VPS would keep data entirely local (but this contradicts the OpenRouter API approach).

---

## Dimension & Storage Implications

Storage for pgvector HNSW index at 3.3M tokens (estimated memory footprint):

| Dims | Float32 per vector | Approx index size at 10K vectors | Relative to current (384) |
|------|-------------------|--------------------------------|--------------------------|
| 384 (current) | 1,536 bytes | ~30 MB | 1x |
| 768 | 3,072 bytes | ~60 MB | 2x |
| 1024 | 4,096 bytes | ~80 MB | 2.7x |
| 1536 | 6,144 bytes | ~120 MB | 4x |
| 2560 | 10,240 bytes | ~200 MB | 6.7x |
| 3072 | 12,288 bytes | ~240 MB | 8x |
| 4096 | 16,384 bytes | ~320 MB | 10.7x |

With 8GB RAM in guinevere.slice, even 4096-dim at 10K vectors (~320MB) is manageable. **Dimension is not a constraint** for this workload. However, higher dims increase query latency for HNSW index builds.

---

## Multilingual Support (Indonesian + English)

Guinevere's primary languages are Indonesian and English. Model suitability:

| Tier | Models | Indonesian Support | Notes |
|------|--------|-------------------|-------|
| **Excellent** | Qwen3 Embedding series (0.6B/4B/8B), BGE-M3, Multilingual-E5-Large | Native support in training | Qwen3 Embedding 8B #1 on MTEB multilingual; trained on 100+ languages |
| **Good** | Gemini Embedding 2/001, Perplexity Embed V1, OpenAI text-embedding-3-small/large | General multilingual capability | Good cross-lingual transfer |
| **English only** | BGE-base/large-en-v1.5, GTE-Base/Large, E5-Base/Large-v2, all Sentence Transformers | Poor for Indonesian | Stick to English-only content |

**Recommendation**: If Indonesian memory content is significant, prioritize multilingual models (Qwen3, BGE-M3, Multilingual-E5-Large, Gemini, Perplexity).

---

## Benchmark Context

### MTEB Multilingual Leaderboard (key scores)

| Model | MTEB Score | Source |
|-------|-----------|--------|
| Qwen3 Embedding 8B | **70.58** | Official Qwen blog (June 2025) |
| Qwen3 Embedding 4B | **69.45** | Official Qwen blog |
| Gemini Embedding 001 (1536-dim) | **68.17** | Google AI docs |
| Qwen3 Embedding 0.6B | **64.33** | Official Qwen blog |
| text-embedding-3-large | ~64 | OpenAI (estimated) |
| text-embedding-3-small | ~62 | OpenAI (estimated) |

### Independent Benchmark (ai-multiple.com, Apr 2026)

| Model | nDCG@3 (avg across 3 domains) | Price/M |
|-------|-------------------------------|---------|
| Perplexity Embed V1 0.6B | **0.8604** | $0.004 |
| text-embedding-3-large | 0.855 (estimated from chart) | $0.13 |
| text-embedding-3-small | ~0.84 | $0.02 |
| Qwen3 Embedding 8B | ~0.87 (close to Voyage) | $0.01 |

*Perplexity Embed V1 0.6B beats text-embedding-3-large on CUAD, loses slightly on TechQA, ties on MedRAG — at 32.5x lower cost.*

---

## Models NOT Available on OpenRouter (but requested)

These models from the requirement list are **not available** on OpenRouter as of June 2026:

| Model | OpenRouter Status | Alternative Access |
|-------|------------------|-------------------|
| `mistral/mistral-embed-2312` | **Not available** — returns 404 | Mistral API directly or self-host |
| `mistral/codestral-embed-2505` | **Not available** — returns 404 | Mistral API directly (code-specific embedder) |

These models would require direct API integration with Mistral rather than going through OpenRouter.

---

## Key Insights for Guinevere

### Cost-Efficiency Sweet Spots

1. **Ultra-cheap + Good quality**: Perplexity Embed V1 0.6B ($0.013/mo) — 1024-dim MRL, 32K ctx, beats many larger models per independent benchmarks
2. **Best quality for cost**: Qwen3 Embedding 8B ($0.033/mo) — #1 MTEB multilingual, 4096-dim MRL, 100+ languages, instruction-aware
3. **Current ADR match**: OpenAI text-embedding-3-small ($0.066/mo) — matches ADR-009, proven at scale (62.9B weekly tokens)
4. **Free tier**: NVIDIA Nemotron Embed VL 1B V2 ($0.00/mo) — 131K ctx, multimodal, free but may have rate limits

### Upgrade Considerations vs Current MiniLM L6 (384-dim)

- Moving from 384 to **768-dim** (all-mpnet-base-v2, GTE-Base, E5-Base, bge-base): +100% storage, +$0.0005/mo cost — minor impact
- Moving to **1024-dim** (bge-m3, multilingual-e5-large, GTE-Large, Perplexity 0.6B): +167% storage, still cheap
- Moving to **1536-dim** (text-embedding-3-small): +300% storage, $0.066/mo — matches current ADR
- Moving to **4096-dim** (Qwen3 Embedding 8B): +967% storage, $0.033/mo — still affordable

### ADR-009 Implications

ADR-009 currently specifies `openai/text-embedding-3-small` 1536-dim via 9Router/OpenRouter. If a different model is selected:
- Change OpenRouter model slug in 9Router config
- Regenerate all existing embeddings (schema migration from 384/1536 to target dims)
- Update ADR-009 with new model + rationale
- Possible pgvector index rebuild

### Privacy Data Flow

```
User memory text → Guinevere → 9Router → OpenRouter → Provider API
                                                         ↓
                                          Provider sees text during encoding
                                                         ↓
                                          Vector returned → pgvector (VPS)
```

For sensitive memory, consider:
- Self-hosting a small model (bge-base-en-v1.5 ~500MB, MiniLM L6 ~90MB) — eliminates data egress
- Using OpenRouter's `provider.data_collection: "deny"` flag
- Chunking sensitive content differently

### Recommendation Caveats

**This catalog does NOT make a final recommendation.** The selection requires:
1. ADR review (ADR-009 scope and willingness to update)
2. Schema impact analysis (384-dim → target dim migration)
3. Possibly A/B testing on real Guinevere memory data
4. Budget confirmation ($2/month target is easily met by any model in this catalog)
5. Privacy risk assessment for sensitive memory content

---

## Sources

### OpenRouter Model Pages (directly fetched, June 2026)
- [OpenRouter Embedding Collection](https://openrouter.ai/collections/embedding-models)
- [OpenRouter Models Page](https://openrouter.ai/models) (26 embedding models listed)
- [Gemini Embedding 2](https://openrouter.ai/google/gemini-embedding-2)
- [Gemini Embedding 2 Preview](https://openrouter.ai/google/gemini-embedding-2-preview)
- [Gemini Embedding 001](https://openrouter.ai/google/gemini-embedding-001)
- [Text Embedding 3 Small](https://openrouter.ai/openai/text-embedding-3-small)
- [Text Embedding 3 Large](https://openrouter.ai/openai/text-embedding-3-large)
- [Text Embedding Ada 002](https://openrouter.ai/openai/text-embedding-ada-002)
- [Qwen3 Embedding 8B](https://openrouter.ai/qwen/qwen3-embedding-8b)
- [Qwen3 Embedding 4B](https://openrouter.ai/qwen/qwen3-embedding-4b)
- [Qwen3 Embedding 0.6B](https://openrouter.ai/qwen/qwen3-embedding-0.6b)
- [Perplexity Embed V1 0.6B](https://openrouter.ai/perplexity/pplx-embed-v1-0.6b)
- [Perplexity Embed V1 4B](https://openrouter.ai/perplexity/pplx-embed-v1-4b)
- [NVIDIA Llama Nemotron Embed VL 1B V2 (free)](https://openrouter.ai/nvidia/llama-nemotron-embed-vl-1b-v2:free)
- [BAAI bge-m3](https://openrouter.ai/baai/bge-m3)
- [BAAI bge-base-en-v1.5](https://openrouter.ai/baai/bge-base-en-v1.5)
- [BAAI bge-large-en-v1.5](https://openrouter.ai/baai/bge-large-en-v1.5)
- [Thenlper GTE-Base](https://openrouter.ai/thenlper/gte-base)
- [Thenlper GTE-Large](https://openrouter.ai/thenlper/gte-large)
- [Intfloat E5-Base-v2](https://openrouter.ai/intfloat/e5-base-v2)
- [Intfloat E5-Large-v2](https://openrouter.ai/intfloat/e5-large-v2)
- [Intfloat Multilingual-E5-Large](https://openrouter.ai/intfloat/multilingual-e5-large)
- [Sentence Transformers all-MiniLM-L6-v2](https://openrouter.ai/sentence-transformers/all-minilm-l6-v2)
- [Sentence Transformers all-MiniLM-L12-v2](https://openrouter.ai/sentence-transformers/all-minilm-l12-v2)
- [Sentence Transformers paraphrase-MiniLM-L6-v2](https://openrouter.ai/sentence-transformers/paraphrase-minilm-l6-v2)
- [Sentence Transformers all-mpnet-base-v2](https://openrouter.ai/sentence-transformers/all-mpnet-base-v2)
- [Sentence Transformers multi-qa-mpnet-base-dot-v1](https://openrouter.ai/sentence-transformers/multi-qa-mpnet-base-dot-v1)

### Vendor Official Docs
- [Google Gemini Embedding docs](https://ai.google.dev/gemini-api/docs/embeddings)
- [Perplexity Embedding API docs](https://docs.perplexity.ai/docs/embeddings/standard-embeddings)
- [Qwen3 Embedding blog post](https://qwenlm.github.io/blog/qwen3-embedding/)
- [Qwen3 Embedding HuggingFace](https://huggingface.co/Qwen/Qwen3-Embedding-8B)

### Benchmark Sources
- [ai-multiple.com embedding model benchmark (Apr 2026)](https://aimultiple.com/embedding-models)
- [MTEB Leaderboard (via Qwen3 Embedding paper, arXiv 2506.05176)](https://arxiv.org/pdf/2506.05176)

---

*End of catalog. No recommendation made pending ADR-009 review and schema impact analysis.*
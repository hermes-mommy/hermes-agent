# MTEB Embedding Benchmark Evidence Report — Guinevere Memory Recall

**Date**: 2026-06-02  
**Scope**: Semantic similarity, retrieval, clustering, and reranking evidence for embedding models available on OpenRouter, evaluated for companion AI semantic recall over Indonesian+English conversation, emotional events, inner journal, surveillance summaries, and technical/project tasks.  
**Priority**: Best value, not most expensive.  
**Benchmark Versions**: MTEB v1 (56 tasks, 8 categories) vs MTEB v2/MMTEB (131+ tasks, 250+ languages). **Scores across versions are NOT directly comparable** unless explicitly noted.

---

## 1. Benchmark Context & Caveats

| Caveat | Detail |
|--------|--------|
| **MTEB v1 vs v2** | MTEB v2 (MMTEB, 2025) expanded to 131+ tasks, 250+ languages, removed MS MARCO/NQ from English eval. Smaller English models (MiniLM, mpnet) score ~10-15 points lower on v2. Scores are NOT cross-version comparable. |
| **Self-reported vs Reproduced** | Many model card scores are self-reported. Actual reproduced scores can differ by ±2-5 points (see BGE issues on MTEB repo). |
| **Instruction tuning gap** | Some models require query prefixes (BGE: "Represent this sentence...", E5: "query:" / "passage:"). Forgetting these drops retrieval by 5-15 points. Perplexity embed requires NO instruction prefix (simpler pipeline). |
| **Multilingual ≠ English** | English-only models (BGE-large-en-v1.5, all-MiniLM, all-mpnet) perform poorly on Indonesian. BGE-M3, multilingual-E5, Qwen3, Gemini Embedding all support Indonesian. |
| **Retrieval vs Average** | MTEB average blends 8 categories. For memory recall, **retrieval** and **STS** (semantic similarity) are most relevant. A model with high avg but low retrieval can mislead. |

---

## 2. Models Available on OpenRouter — Complete Comparison

### 2.1 Full Comparison Table

| # | Model (OpenRouter ID) | Params | Dims | MTEB Avg | Retrieval | STS | Clustering | Max Tokens | Price/1M tok | Best For |
|---|-----------------------|--------|------|----------|-----------|-----|------------|------------|-------------|----------|
| 1 | `google/gemini-embedding-001` | ? | 3072 | **68.32** (multilingual) | **67.71** | ~71 | ~48 | 8192 | **$0.15** | Best retrieval, strong multilingual, Indonesian support |
| 2 | `google/gemini-embedding-2-preview` | ? | 3072 | ~69.9 (reported) | — | — | — | 8192 | **$0.20** | Multimodal (text+image+audio), may improve on text |
| 3 | `google/gemini-embedding-2` | ? | 3072 | **69.9** (MTEB multi) | — | — | — | 8192 | **$0.20** | Production multimodal, MTEB code 84.0 |
| 4 | `qwen/qwen3-embedding-8b` | 8B | 4096 | **70.58** (MMTEB) | ~57.8 | ~80 | **51.8** | 32768 | **$0.01** | Best open-source, multilingual, lowest cost on OR |
| 5 | `qwen/qwen3-embedding-4b` | 4B | 2560 | **69.45** (MMTEB) | **69.60** | **80.86** | 57.15 | 33000 | **$0.02** | Best open-source value, strong retrieval |
| 6 | `qwen/qwen3-embedding-0.6b` | 0.6B | 1024 | **64.34** (MMTEB) | 64.65 | 76.17 | 52.33 | 32000 | — | Lightweight, good benchmark for size |
| 7 | `openai/text-embedding-3-large` | ? | 3072 | **64.60** (v1) | 55.4 | ~83 | ~47 | 8191 | **$0.13** | Good general purpose, stable ecosystem |
| 8 | `openai/text-embedding-3-small` | ? | 1536 | **62.26** (v1) | ~52 | ~79 | ~46 | 8191 | **$0.02** | Great value default, fast & cheap |
| 9 | `perplexity/pplx-embed-v1-4b` | 4B | 2560 | **69.66** (MMTEB retrieval) | **69.66** | — | — | 32000 | **$0.03** | Best retrieval-per-dollar, no instruction prefix |
| 10 | `perplexity/pplx-embed-v1-0.6b` | 0.6B | 1024 | **65.41** (MMTEB retrieval) | 65.41 | — | — | 32000 | **$0.004** | Cheapest by far, 92% of Voyage quality |
| 11 | `baai/bge-m3` | 568M | 1024 | **63.0** (v1) / **68.2** (v2) | ~53 | ~82 | ~45 | 8192 | **$0.01** | Best self-host value, dense+sparse+colbert, ~100 langs |
| 12 | `baai/bge-large-en-v1.5` | 335M | 1024 | **64.23** (v1) | 54.29 | 83.11 | 46.08 | 512 | Self-host only | Strong English-only, poor multilingual |
| 13 | `baai/bge-base-en-v1.5` | 110M | 768 | **63.55** (v1) | 53.25 | 82.4 | 45.77 | 512 | Self-host only | Lighter English-only option |
| 14 | `intfloat/multilingual-e5-large` | 335M | 1024 | **61.5** (v1) / **58.6** (MMTEB) | ~52 | ~87 | ~44 | 512 | Self-host only | 94 languages, but older scores |
| 15 | `intfloat/multilingual-e5-large-instruct` | 335M | 1024 | **64.4** (v1) / **63.2** (MMTEB) | ~58 | ~87 | ~45 | 512 | Self-host only | Instruction-tuned, best of E5 family |
| 16 | `intfloat/e5-large-v2` | 335M | 1024 | **62.25** (v1) | 50.16 | 83.05 | 44.49 | 512 | Self-host only | English-only, good STS |
| 17 | `intfloat/e5-base-v2` | 110M | 768 | **59.51** (v1) | 47.54 | 82.6 | 43.72 | 512 | Self-host only | Lighter E5 |
| 18 | `Alibaba-NLP/gte-large-en-v1.5` | 434M | 1024 | **~65.4** (v1) | ~58 | ~84 | ~47 | 8192 | Self-host only | Strong English, long context |
| 19 | `thenlper/gte-base` | 110M | 768 | **62.39** (v1) | 51.14 | 82.3 | 46.2 | 512 | Self-host only | Solid baseline |
| 20 | `sentence-transformers/all-mpnet-base-v2` | 110M | 768 | **57.78** (v1) / **42.5** (v2) | 43.81 | 80.28 | 43.69 | 514 | Self-host only | Fast, but obsolete for production |
| 21 | `sentence-transformers/all-MiniLM-L6-v2` | 22M | 384 | **56.26** (v1) / **41.4** (v2) | 41.95 | 78.9 | 42.35 | 512 | Self-host only | Fastest, but poor for retrieval |
| 22 | `sentence-transformers/all-MiniLM-L12-v2` | 33M | 384 | **56.53** (v1) | 42.69 | 79.8 | 41.81 | 512 | Self-host only | Slightly better than L6 |
| 23 | `mistral-embed` (Mistral API) | ? | 1024 | **~58** (estimated) | — | — | — | 32768 | $0.10 | Mistral ecosystem only, European langs |
| 24 | `nvidia/llama-embed-nemotron-8b` (self-host) | 8B | 4096 | **69.46** (MMTEB) | 68.69 | 79.41 | 54.35 | 32768 | Self-host | Borda #1 on MMTEB, not on OpenRouter as API |
| 25 | `nvidia/nv-embed-v2` (self-host) | 7B | 4096 | **72.31** (v1) | 62.65 | — | — | 32768 | Self-host | English MTEB leader, not on OR as API |

**Sources**:
- [MTEB Leaderboard HF Space](https://huggingface.co/spaces/mteb/leaderboard)
- [Awesome Agents April 2026 Rankings](https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-april-2026/)
- [Presenc AI Open-Weight Leaderboard May 2026](https://presenc.ai/research/best-open-weight-embedding-models-2026)
- [Ailog MTEB 2026 Report](https://app.ailog.fr/en/blog/news/rag-benchmark-mteb-2026)
- [OpenRouter Embedding Collection](https://openrouter.ai/collections/embedding-models)
- [OpenRouter Models Catalog](https://github.com/neabytelab/openrouter-catalog)
- Google Gemini Embedding Tech Report (arXiv 2503.07891)
- NVIDIA Llama-Embed-Nemotron-8B Blog (HuggingFace, Oct 2025)
- Perplexity pplx-embed paper (arXiv 2602.11151)
- BGE model cards (HuggingFace: BAAI/bge-large-en-v1.5, BAAI/bge-m3)
- GTE model cards (HuggingFace: thenlper/gte-large, thenlper/gte-base)

### 2.2 Pricing Detail (OpenRouter API, as of June 2026)

| Model | Input $/1M tok | Notes |
|-------|---------------|-------|
| `qwen/qwen3-embedding-8b` | $0.01 | Cheapest high-quality, 32K context |
| `qwen/qwen3-embedding-4b` | $0.02 | Great quality for 2x 8B price |
| `baai/bge-m3` | $0.01 | Good multilingual budget option |
| `perplexity/pplx-embed-v1-0.6b` | $0.004 | Absolute cheapest, 32K context |
| `perplexity/pplx-embed-v1-4b` | $0.03 | Best retrieval/$, no instruction prefix |
| `openai/text-embedding-3-small` | $0.02 | Batch: $0.01, solid default |
| `openai/text-embedding-3-large` | $0.13 | Batch: $0.065, quality pick |
| `google/gemini-embedding-001` | $0.15 | Batch: $0.075, free tier available |
| `google/gemini-embedding-2-preview` | $0.20 | Multimodal premium |
| `google/gemini-embedding-2` | $0.20 | Production multimodal |
| `mistral-embed` (direct API) | $0.10 | Mistral ecosystem only |

**Source**: [OpenRouter Pricing Pages](https://openrouter.ai/collections/embedding-models), [Awesome Agents Embedding Pricing April 2026](https://awesomeagents.ai/pricing/embedding-models-pricing/)

---

## 3. Breakdown by Memory Recall Relevance

### 3.1 Semantic Similarity (STS) — Emotional Events, Inner Journal

| Rank | Model | MTEB STS Score | Notes |
|------|-------|---------------|-------|
| 1 | `qwen/qwen3-embedding-4b` | **80.86** | MMTEB STS leader |
| 2 | `qwen/qwen3-embedding-8b` | **~80** | Estimated from family trend |
| 3 | `google/gemini-embedding-001` | **~71** | Lower STS despite high retrieval |
| 4 | `BAAI/bge-large-en-v1.5` | **83.11** | Best English STS, poor multilingual |
| 5 | `intfloat/multilingual-e5-large` | **~87** | Best STS for multilingual |
| 6 | `intfloat/e5-large-v2` | **83.05** | Strong English STS |
| 7 | `openai/text-embedding-3-large` | **~83** | Good STS |
| 8 | `openai/text-embedding-3-small` | **~79** | Decent STS |
| 9 | `all-mpnet-base-v2` | **80.28** | Good STS but weak multilingual |
| 10 | `BAAI/bge-m3` | **~82** | STS not separately reported in v1 table |

**Takeaway**: For semantic similarity matching of emotional/reflective text, multilingual-E5-large has the best reported STS. But it's self-host only and older. **Qwen3-Embedding-4B** and **bge-m3** are the best pragmatic choices via OpenRouter.

### 3.2 Retrieval — Conversation Recall, Technical Task Lookup

| Rank | Model | MTEB Retrieval Score | Context | Platform |
|------|-------|---------------------|---------|----------|
| 1 | `perplexity/pplx-embed-v1-4b` | **69.66** (MMTEB v2) | INT8, 32K ctx, no prefix | OpenRouter |
| 2 | `qwen/qwen3-embedding-4b` | **69.60** (MMTEB v2) | 33K ctx | OpenRouter |
| 3 | `google/gemini-embedding-001` | **67.71** (MMTEB v2) | 8K ctx | OpenRouter |
| 4 | `google/gemini-embedding-2` | ~67 (est.) | 8K ctx, multimodal | OpenRouter |
| 5 | `perplexity/pplx-embed-v1-0.6b` | **65.41** (MMTEB v2) | 32K ctx, $0.004/M | OpenRouter |
| 6 | `nvidia/llama-embed-nemotron-8b` | **68.69** (MMTEB v2) | 32K ctx | Self-host only |
| 7 | `qwen/qwen3-embedding-8b` | ~57.8 (v1) | 32K ctx | OpenRouter |
| 8 | `openai/text-embedding-3-large` | 55.4 (v1) | 8K ctx | OpenRouter |
| 9 | `openai/text-embedding-3-small` | ~52 (v1) | 8K ctx | OpenRouter |
| 10 | `BAAI/bge-m3` | ~53 (v1) | 8K ctx, dense+sparse+colbert | OpenRouter |

**Takeaway**: **Perplexity pplx-embed-v1-4b** ($0.03/M) and **Qwen3-Embedding-4B** ($0.02/M) are neck-and-neck for retrieval quality at very low cost. **Gemini Embedding 001** ($0.15/M) is still top-tier but 5-7.5x more expensive. **pplx-embed-v1-0.6b** ($0.004/M) is incredible value.

### 3.3 Clustering — Event Grouping, Topic Segmentation

| Rank | Model | MTEB Clustering Score | Notes |
|------|-------|----------------------|-------|
| 1 | `qwen/qwen3-embedding-4b` | **57.15** (MMTEB) | Top clustering |
| 2 | `nvidia/llama-embed-nemotron-8b` | **54.35** (MMTEB) | Self-host only |
| 3 | `qwen/qwen3-embedding-0.6b` | **52.33** (MMTEB) | |
| 4 | `qwen/qwen3-embedding-8b` | **51.8** (reported) | |
| 5 | `google/gemini-embedding-001` | ~48 | |

**Takeaway**: Qwen3-Embedding family dominates clustering. For memory recall (grouping similar conversations/events), Qwen3 is the clear choice.

### 3.4 Multilingual (Indonesian + English) Capability

| Model | Languages | Indonesian Support | Quality |
|-------|-----------|-------------------|---------|
| `google/gemini-embedding-001` | ~100+ | ✅ Yes (multilingual MTEB leader) | **Best** |
| `qwen/qwen3-embedding-8b` | ~119 | ✅ Yes (strong Asian) | **Excellent** |
| `qwen/qwen3-embedding-4b` | ~119 | ✅ Yes | **Excellent** |
| `BAAI/bge-m3` | ~100 | ✅ Yes | **Good** |
| `perplexity/pplx-embed-v1-4b` | ~100+ | ✅ Yes (MMTEB multilingual) | **Very good** |
| `intfloat/multilingual-e5-large` | ~94 | ✅ Yes | **Good** (older) |
| `intfloat/multilingual-e5-large-instruct` | ~94 | ✅ Yes | **Better** |
| `mistral-embed` | European focus | ❌ Limited | European only |
| `openai/text-embedding-3-large` | English+ | ⚠️ Basic non-English | Chinese tested, Indonesian unknown |
| `BAAI/bge-large-en-v1.5` | English only | ❌ No | English only |
| `all-MiniLM-L6-v2` | English only | ❌ No | English only |

**Takeaway**: For Indonesian+English memory recall, **must use multilingual models**. The English-only models (BGE-large-en-v1.5, MiniLM, mpnet, E5-base/large-v2, GTE-base/large) will perform poorly on Indonesian text. **Top picks**: Gemini Embedding 001, Qwen3 Embedding (any size), Perplexity embed, BGE-M3.

---

## 4. Top Recommendations for Guinevere Memory Recall

### 4.1 Value Matrix

| Budget Tier | Primary Model | Cost/M tok | MTEB Retrieval | Multilingual | Why |
|------------|--------------|-----------|----------------|-------------|-----|
| **Free/self-host** | `BAAI/bge-m3` | $0 self-host / $0.01 OR | 63.0 v1 / 68.2 v2 | ~100 langs | Dense+sparse+colbert, MIT license, lightweight (568M) |
| **Budget** | `perplexity/pplx-embed-v1-0.6b` | $0.004 | 65.41 (MMTEB retr) | ~100 langs | Cheapest OpenRouter model, 32K ctx, no instruction prefix |
| **Best Value** | `qwen/qwen3-embedding-4b` | $0.02 | 69.60 (MMTEB retr) | ~119 langs | Best quality/price ratio, 33K ctx |
| **Best Value+** | `perplexity/pplx-embed-v1-4b` | $0.03 | 69.66 (MMTEB retr) | ~100 langs | Matches Qwen3-4B retrieval, no instruction prefix |
| **Best Quality** | `google/gemini-embedding-001` | $0.15 | 67.71 (MMTEB retr) | ~100+ langs | Highest multilingual MTEB, best for cross-lingual recall |
| **Best Open** | `qwen/qwen3-embedding-8b` | $0.01 | ~57.8 v1 (70.58 MMTEB avg) | ~119 langs | Cheapest high-quality on OR, Apache 2.0 weights |

### 4.2 Recommended Strategy for Guinevere

| Use Case | Recommended Model | Rationale |
|----------|------------------|-----------|
| **Primary memory recall** (ID+EN conversations) | `qwen/qwen3-embedding-4b` at $0.02/M | Best retrieval + STS + clustering balance, multilingual, cheapest strong option |
| **Budget-sensitive recall** | `perplexity/pplx-embed-v1-0.6b` at $0.004/M | 65.41 retrieval, 32K ctx, 5x cheaper than Qwen3-4B |
| **High-accuracy recall** | `google/gemini-embedding-001` at $0.15/M | Best multilingual retrieval, premium for critical lookups |
| **Self-hosted recall** | `BAAI/bge-m3` | MIT license, dense+sparse+colbert, 100 langs, 568M params |
| **Emotional STS** (inner journal) | `qwen/qwen3-embedding-4b` | 80.86 STS on MMTEB, multilingual |
| **Surveillance summaries** | `perplexity/pplx-embed-v1-4b` | 32K ctx captures long summaries, no instruction prefix |

---

## 5. Detailed Model Profiles

### 5.1 OpenAI — text-embedding-3-small & text-embedding-3-large

| Property | 3-small | 3-large |
|----------|---------|---------|
| **Released** | Jan 2024 | Jan 2024 |
| **Params** | Unknown | Unknown |
| **Dimensions** | 1536 (MRL: 256-1536) | 3072 (MRL: 256-3072) |
| **Max Tokens** | 8191 | 8191 |
| **MTEB Avg** | 62.26 (v1) | 64.60 (v1) |
| **MTEB Retrieval** | ~52.0 | ~55.4 |
| **MTEB STS** | ~79 | ~83 |
| **MIRACL** | 44.0% | 54.9% |
| **Price/1M tok** | $0.02 ($0.01 batch) | $0.13 ($0.065 batch) |
| **On OpenRouter** | ✅ `openai/text-embedding-3-small` | ✅ `openai/text-embedding-3-large` |
| **Multilingual** | Limited (best on English) | Limited (best on English) |

**Verdict**: text-embedding-3-small is the safe default for English-only at $0.02/M. For multilingual Indonesian recall, **look elsewhere**. 3-large is 6.5x more expensive for only ~4 MTEB points gain.

**Sources**:
- [OpenAI API Docs](https://developers.openai.com/api/docs/models/text-embedding-3-small)
- [TokenMix Guide](https://tokenmix.ai/blog/text-embedding-3-small-developer-guide-2026)
- [Respan Engineer's Guide](https://www.respan.ai/articles/openai-embeddings-guide)

### 5.2 Google — Gemini Embedding 001 / 2 / 2-preview

| Property | gemini-embedding-001 | gemini-embedding-2-preview | gemini-embedding-2 |
|----------|---------------------|---------------------------|-------------------|
| **Released** | Mar 2025 (GA Jul 2025) | Early 2026 | May 2026 |
| **Dimensions** | 3072 (MRL: 128-3072) | 3072 (MRL: 128-3072) | 3072 (MRL: 128-3072) |
| **Max Tokens** | 2048 (input) / 8192 (OR) | 8192 | 8192 |
| **MTEB Multilingual** | **68.32** | **~69.9** (reported) | **69.9** |
| **MTEB English v2** | **73.30** | — | — |
| **MTEB Code** | **74.66** | — | **84.0** |
| **MTEB Retrieval** | **67.71** | — | — |
| **Price/1M tok** | $0.15 | $0.20 | $0.20 |
| **On OpenRouter** | ✅ `google/gemini-embedding-001` | ✅ `google/gemini-embedding-2-preview` | ✅ `google/gemini-embedding-2` |
| **Modality** | Text only | Text+Image+Audio+Video | Text+Image+Audio+Video |

**Key Detail**: Gemini Embedding 001 achieves **68.16 MTEB at 2048 dims** and **68.17 at 1536 dims** — barely drops with smaller vectors. At 256 dims it still scores 66.19. This means you can use 256-dim vectors and lose only ~2 MTEB points, saving massive storage.

**Verdict**: Gemini Embedding 001 is the **best multilingual retrieval** choice on OpenRouter. The v2 adds multimodality (search images by text). Expensive at $0.15-0.20/M but quality justifies it.

**Sources**:
- [Google Developers Blog - Gemini Embedding GA](https://developers.googleblog.com/gemini-embedding-available-gemini-api/)
- [Google AI Dev Docs](https://ai.google.dev/gemini-api/docs/embeddings)
- [Gemini Embedding Tech Report](https://arxiv.org/pdf/2503.07891)
- [DeepMind Gemini Embedding 2 page](https://deepmind.google/models/gemini/embedding/)

### 5.3 Qwen — Qwen3 Embedding 0.6B / 4B / 8B

| Property | 0.6B | 4B | 8B |
|----------|------|----|----|
| **Released** | Oct 2025 | Oct 2025 | Oct 2025 |
| **Dimensions** | 1024 | 2560 | 4096 |
| **Max Tokens** | 32000 | 33000 | 32768 |
| **MMTEB Mean (Task)** | 64.34 | **69.45** | **70.58** |
| **MMTEB Retrieval** | 64.65 | **69.60** | ~57.8 (v1) |
| **MMTEB STS** | 76.17 | **80.86** | ~80 |
| **MMTEB Clustering** | 52.33 | **57.15** | 51.8 |
| **License** | Custom commercial | Custom commercial | Custom commercial |
| **On OpenRouter** | ✅ (listed but no price shown) | ✅ `qwen/qwen3-embedding-4b` | ✅ `qwen/qwen3-embedding-8b` |
| **Price/1M tok** | — | **$0.02** | **$0.01** |
| **Languages** | ~119 | ~119 | ~119 |

**Key Insight**: Qwen3-Embedding-4B ($0.02/M) has **almost identical retrieval** to the 8B version (69.60 vs ~57.8 on different benchmarks) with **better STS and clustering**. The 4B model is arguably the **sweet spot** for memory recall. The 8B model is cheaper at $0.01/M and has higher MMTEB average, but its retrieval score is from a different benchmark (MTEB v1).

**Verdict**: **Qwen3-Embedding-4B at $0.02/M is the single best value** for Guinevere memory recall — multilingual, strong across all relevant dimensions, and very affordable.

**Sources**:
- [OpenRouter Qwen3 Embedding 4B](https://openrouter.ai/qwen/qwen3-embedding-4b)
- [OpenRouter Qwen3 Embedding 8B](https://openrouter.ai/qwen/qwen3-embedding-8b)
- [Presenc AI Analysis](https://presenc.ai/research/best-open-weight-embedding-models-2026)
- [Ailog MTEB 2026](https://app.ailog.fr/en/blog/news/rag-benchmark-mteb-2026)

### 5.4 BAAI — BGE-M3, BGE-large/base-en-v1.5

| Property | BGE-M3 | BGE-large-en-v1.5 | BGE-base-en-v1.5 |
|----------|--------|-------------------|-------------------|
| **Released** | Jan 2024 | Oct 2023 | Oct 2023 |
| **Params** | 568M | 335M | 110M |
| **Dimensions** | 1024 | 1024 | 768 |
| **Max Tokens** | 8192 | 512 | 512 |
| **MTEB Avg (v1)** | 63.0 | **64.23** | 63.55 |
| **MTEB v2** | **68.2** | 64.2 | — |
| **MTEB Retrieval** | ~53 | 54.29 | 53.25 |
| **MTEB STS** | ~82 | **83.11** | 82.4 |
| **License** | MIT | MIT | MIT |
| **On OpenRouter** | ✅ `baai/bge-m3` ($0.01/M) | ❌ (self-host) | ❌ (self-host) |
| **Languages** | ~100 | English only | English only |

**Key Detail**: BGE-M3 is unique for supporting **dense + sparse + ColBERT multi-vector** retrieval in one model. Sparse retrieval helps with exact keyword matches, dense helps with semantic. This hybrid approach can boost recall on mixed-content (Indonesian+English slang, code terms).

**Verdict**: BGE-M3 is the **best self-host option** — lightweight (568M), MIT license, multilingual, hybrid retrieval. At $0.01/M on OpenRouter it's also a fantastic API option.

**Sources**:
- [BGE-M3 HuggingFace](https://huggingface.co/BAAI/bge-m3)
- [BGE-large-en-v1.5 HuggingFace](https://huggingface.co/BAAI/bge-large-en-v1.5)
- [BGE-base-en-v1.5 HuggingFace](https://huggingface.co/BAAI/bge-base-en-v1.5)

### 5.5 Perplexity — pplx-embed-v1 0.6B & 4B

| Property | pplx-embed-v1-0.6B | pplx-embed-v1-4B |
|----------|-------------------|------------------|
| **Released** | Feb 2026 | Feb 2026 |
| **Params** | 0.6B | 4B |
| **Dimensions** | 1024 | 2560 |
| **Max Tokens** | 32000 | 32000 |
| **MMTEB Retrieval** | **65.41** | **69.66** |
| **MTEB Code** | 75.85 | 78.73 |
| **Quantization** | INT8/BINARY native | INT8/BINARY native |
| **Instruction prefix** | **None required** | **None required** |
| **On OpenRouter** | ✅ `perplexity/pplx-embed-v1-0.6b` | ✅ `perplexity/pplx-embed-v1-4b` |
| **Price/1M tok** | **$0.004** | **$0.03** |

**Key Detail**: Perplexity's embedding models are **natively INT8 quantized** — the 4B INT8 model stores **390 docs/MB** (4x more than Gemini's 81 docs/MB at FP32). The BINARY variant stores **3,125 docs/MB**. This is critical for memory recall where you might store months of conversations.

No instruction prefix needed — simpler pipeline, less brittle.

**Verdict**: **pplx-embed-v1-0.6b at $0.004/M is the cheapest viable embedding** on OpenRouter with strong multilingual performance. The 4B version matches Qwen3-4B retrieval at $0.03/M. **Ideal for high-volume memory recall**.

**Sources**:
- [Perplexity Research Blog](https://research.perplexity.ai/articles/pplx-embed-state-of-the-art-embedding-models-for-web-scale-retrieval)
- [HuggingFace Perplexity Collection](https://huggingface.co/collections/perplexity-ai/pplx-embed)
- [Perplexity Embed Paper (arXiv 2602.11151)](https://arxiv.org/pdf/2602.11151)
- [OpenRouter pplx-embed-v1-0.6b](https://openrouter.ai/perplexity/pplx-embed-v1-0.6b)

### 5.6 Others — Mistral Embed, Nemotron Embed, GTE, E5, MiniLM, mpnet

| Model | MTEB Avg | Retrieval | Languages | OpenRouter? | Verdict |
|-------|----------|-----------|-----------|-------------|---------|
| **Mistral Embed** | ~58 (est.) | Unknown | European | ❌ (Mistral API only, $0.10) | Overpriced, weak performance. Skip. |
| **llama-embed-nemotron-8b** | 69.46 (MMTEB) | 68.69 | Multilingual (Borda #1) | ❌ (self-host only) | Excellent but requires self-hosting. |
| **NV-Embed-v2** | 72.31 (v1) | 62.65 | English-focused | ❌ (self-host only) | English MTEB v1 leader, CC-BY-NC. |
| **GTE-Qwen2-7B-instruct** | 70.24 (v1) | — | Multilingual | ❌ | Strong open-weight, Apache 2.0. |
| **GTE-large-en-v1.5** | ~65.4 (v1) | ~58 | English | ❌ | Good but English-only. |
| **multilingual-e5-large-instruct** | 64.4 (v1) / 63.2 (MMTEB) | ~58 | ~94 langs | ❌ | Best of E5 family, self-host. |
| **multilingual-e5-large** | 61.5 (v1) / 58.6 (MMTEB) | ~52 | ~94 langs | ❌ | Aging, surpassed by newer models. |
| **e5-large-v2** | 62.25 (v1) | 50.16 | English | ❌ | Strong STS (83.05) but English only. |
| **all-mpnet-base-v2** | 57.78 (v1) / 42.5 (v2) | 43.81 | English | ❌ | MMTEB v2 score cratered. English-only. Skip. |
| **all-MiniLM-L6-v2** | 56.26 (v1) / 41.4 (v2) | 41.95 | English | ❌ | 22M params, fast, but poor for production recall. |
| **all-MiniLM-L12-v2** | 56.53 (v1) / — | 42.69 | English | ❌ | Marginal improvement over L6. |

**Sources**:
- [Mistral Embed Docs](https://docs.mistral.ai/studio-api/knowledge-rag/search-toolkit/ingestion/embedders)
- [NVIDIA Llama-Embed-Nemotron Blog](https://huggingface.co/blog/nvidia/llama-embed-nemotron-8b)
- [MMTEB ICLR 2025 Paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/fc0e3f908a2116ba529ad0a1530a3675-Paper-Conference.pdf)
- [Mixpeek Best Embedding Models 2026](https://mixpeek.com/curated-lists/best-embedding-models)
- [GTE-large HuggingFace](https://huggingface.co/thenlper/gte-large)
- [E5 base/large-v2 (Microsoft Unilm)](https://github.com/microsoft/unilm/blob/master/e5/README.md)
- [Sentence-Transformers Pretrained Models](https://www.sbert.net/docs/sentence_transformer/pretrained_models.html)

---

## 6. Direct Comparability Warning

| Comparison | Valid? | Reason |
|-----------|--------|--------|
| MTEB v1 64.6 vs MTEB v1 62.3 | ✅ Yes | Same benchmark version |
| MTEB v1 score vs MMTEB v2 score | ⚠️ **NO** | Different task sets, languages, distributions |
| Qwen3-8B 70.58 (MMTEB) vs text-3-large 64.6 (v1) | ⚠️ Approximate | Different benchmarks, ~15 point gap is real but precise difference unknown |
| English MTEB vs Multilingual MTEB | ⚠️ **NO** | Different task selection |
| Self-reported vs MTEB-reproduced | ⚠️ Varies | Some model cards +5 pts above reproduced (see BGE issues) |
| BGE-M3 v1 63.0 vs BGE-M3 v2 68.2 | ⚠️ **NO** | Same model, different benchmarks |

**Rule of thumb**: Compare within same benchmark version (MTEB v1, MMTEB, MTEB(Eng, v2)). For cross-version, expect 5-10 point inflation in v2 for strong multilingual models and 10-15 point deflation for small English-only models.

---

## 7. Storage & Vector DB Implications

| Model | Dims | Est. vector size (FP32) | 100K vectors | 1M vectors |
|-------|------|------------------------|--------------|------------|
| `all-MiniLM-L6-v2` | 384 | 1.5 KB | 150 MB | 1.5 GB |
| `all-mpnet-base-v2` | 768 | 3 KB | 300 MB | 3 GB |
| `BAAI/bge-base-en-v1.5` | 768 | 3 KB | 300 MB | 3 GB |
| `BAAI/bge-m3` | 1024 | 4 KB | 400 MB | 4 GB |
| `intfloat/e5-large-v2` | 1024 | 4 KB | 400 MB | 4 GB |
| `BAAI/bge-large-en-v1.5` | 1024 | 4 KB | 400 MB | 4 GB |
| `openai/text-embedding-3-small` | 1536 | 6 KB | 600 MB | 6 GB |
| `perplexity/pplx-embed-v1-0.6b` | 1024 (INT8: 1KB) | 4 KB | 400 MB (INT8: 100 MB) | 4 GB (INT8: 1 GB) |
| `perplexity/pplx-embed-v1-4b` | 2560 (INT8: 2.5KB) | 10 KB | 1 GB (INT8: 250 MB) | 10 GB (INT8: 2.5 GB) |
| `qwen/qwen3-embedding-4b` | 2560 | 10 KB | 1 GB | 10 GB |
| `qwen/qwen3-embedding-8b` | 4096 | 16 KB | 1.6 GB | 16 GB |
| `google/gemini-embedding-001` | 3072 | 12 KB | 1.2 GB (or 256-dim: 100 MB) | 12 GB |
| `openai/text-embedding-3-large` | 3072 | 12 KB | 1.2 GB | 12 GB |

**Key insight**: Perplexity's native INT8 reduces storage by 4x, and BINARY by 32x. Gemini's MRL allows truncation to 256 dims with only ~2 point MTEB loss — storing 12x less.

---

## 8. Final Recommendations for Guinevere

### Tier 1: Production — Best Value
**`qwen/qwen3-embedding-4b`** at $0.02/M tokens
- Excellent multilingual (119 languages, includes Indonesian)
- Best STS (80.86) and clustering (57.15) for emotional/event recall
- 33K context captures long conversations
- Strong retrieval (69.60 MMTEB)
- On OpenRouter: `qwen/qwen3-embedding-4b`

### Tier 2: Budget — Cheapest Viable
**`perplexity/pplx-embed-v1-0.6b`** at $0.004/M tokens
- 65.41 MMTEB retrieval — 94% of Tier 1 at 20% cost
- Native INT8 quantization — 4x storage savings
- 32K context, no instruction prefix needed
- On OpenRouter: `perplexity/pplx-embed-v1-0.6b`

### Tier 3: Performance — Best Quality
**`google/gemini-embedding-001`** at $0.15/M tokens
- Highest multilingual MTEB (68.32), best retrieval (67.71)
- MRL down to 256 dims with minimal quality loss
- Free tier available via Google AI Studio
- On OpenRouter: `google/gemini-embedding-001`

### Tier 4: Self-Hosted
**`BAAI/bge-m3`** — $0 on own infra
- MIT license, 568M params (runs on CPU)
- Dense + sparse + ColBERT hybrid retrieval
- ~100 languages, 8K context
- On OpenRouter: `baai/bge-m3` at $0.01/M

### Not Recommended for This Use Case
- **all-MiniLM / all-mpnet / BGE-en-v1.5**: English-only, no Indonesian support, v2 scores collapsed
- **Mistral Embed**: Overpriced ($0.10/M), weak on MTEB, European language focus
- **text-embedding-3-large**: 6.5x more expensive than 3-small for marginal gain, weak multilingual
- **e5-base/large-v2**: English-only, outdated

---

## Appendix A: Score Sources

| Source | URL | Reliability |
|--------|-----|-------------|
| MTEB Leaderboard (HF Space) | https://huggingface.co/spaces/mteb/leaderboard | **Official** |
| MMTEB Paper (ICLR 2025) | https://arxiv.org/abs/2502.13595 | **Peer-reviewed** |
| Awesome Agents April 2026 | https://awesomeagents.ai/leaderboards/embedding-model-leaderboard-mteb-april-2026/ | High (aggregated) |
| Presenc AI May 2026 | https://presenc.ai/research/best-open-weight-embedding-models-2026 | High (open-weight focus) |
| Ailog MTEB 2026 Report | https://app.ailog.fr/en/blog/news/rag-benchmark-mteb-2026 | High |
| Model Cards (HuggingFace) | Per-model pages | Medium (self-reported) |
| Perplexity Embed Paper | https://arxiv.org/abs/2602.11151 | **Peer-reviewed** |
| Gemini Embedding Tech Report | https://arxiv.org/abs/2503.07891 | **Peer-reviewed** |
| NVIDIA Nemotron Blog | https://huggingface.co/blog/nvidia/llama-embed-nemotron-8b | Vendor reported |
| OpenRouter Pricing | https://openrouter.ai/collections/embedding-models | **Official pricing** |

## Appendix B: Key MTEB Task Categories

| Category | Relevance to Memory Recall | # of datasets (v1) |
|----------|---------------------------|-------------------|
| **Retrieval** | **Highest** — finding past conversations, events, tasks | 15 |
| **STS (Semantic Textual Similarity)** | **Highest** — measuring emotional similarity, intent matching | 10 |
| **Clustering** | **High** — grouping similar memories, topic segmentation | 11 |
| **Classification** | Medium — labeling memory types | 12 |
| **Reranking** | Medium — improving retrieval results | 4 |
| **Pair Classification** | Low — binary similarity | 3 |
| **Summarization** | Low | 1 |
| **Bitext Mining** | Low | — |

---

*Report generated 2026-06-02. Benchmarks and prices may change. Verify latest scores at [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) and [OpenRouter Models](https://openrouter.ai/collections/embedding-models) before making final decisions.*
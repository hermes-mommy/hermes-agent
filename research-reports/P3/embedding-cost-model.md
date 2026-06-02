# P3 Embedding Cost Model — OpenRouter

> **Date**: 2026-06-02
> **Scope**: All OpenRouter embedding models, exact cost at Guinevere P3 workload
> **Author**: Guinevere (Librarian)
> **Status**: Complete

---

## Workload Basis

| Component | Daily Count | Tokens/Op | Daily Tokens | Monthly Tokens |
|---|---|---|---|---|
| Memory writes | 500 | 200 | 100,000 | 3,000,000 |
| Recall queries | 200 | 50 | 10,000 | 300,000 |
| **Total** | **700 ops** | — | **110,000** | **3,300,000** |

> **Formula**: `cost/month = price_per_1M × 3.3`

Query embedding tokens (50 tokens/recall) are included in the recall total above.

---

## Complete Model Catalog (by price, ascending)

Prices sourced from OpenRouter model pages on 2026-06-02. Embedding models charge input tokens only (no output tokens).

### FREE ($0.00/M tokens)

| Model | Provider | Context | Notes |
|---|---|---|---|
| `nvidia/llama-nemotron-embed-vl-1b-v2:free` | NVIDIA | 131K | Multimodal (text+image) embed. Not found on main model page but confirmed via `/pricing` endpoint. Free tier from NVIDIA. |

**Cost at 3.3M/month: $0.00** — 100% under $2 budget.

> **Caveat**: Free models may have rate limits (NVIDIA free tier: 50 reqs/day on OpenRouter free plan). Not recommended for production without upgrade.

---

### $0.004/M tokens

| Model | Provider | Context | Dimensions | Language |
|---|---|---|---|---|
| `perplexity/pplx-embed-v1-0.6b` | Perplexity | 32K | 768? | English |

**Cost at 3.3M/month**: $0.004 × 3.3 = **$0.013**

**Budget fit**: 99.4% of $2 budget remaining.

**Source**: [openrouter.ai/perplexity/pplx-embed-v1-0.6b](https://openrouter.ai/perplexity/pplx-embed-v1-0.6b)

---

### $0.005/M tokens

| Model | Provider | Context | Dimensions | Language |
|---|---|---|---|---|
| `baai/bge-base-en-v1.5` | BAAI | 8K | 768 | **English only** |
| `intfloat/e5-base-v2` | Intfloat | 8K | 768 | **English only** |

**Cost at 3.3M/month**: $0.005 × 3.3 = **$0.017**

**Budget fit**: 99.2% of $2 budget remaining.

**Source**: [bge-base-en-v1.5](https://openrouter.ai/baai/bge-base-en-v1.5), [e5-base-v2](https://openrouter.ai/intfloat/e5-base-v2)

> **Note**: English-only models are poor candidates for Guinevere's multilingual workload.

---

### $0.01/M tokens

| Model | Provider | Context | Dimensions | Language |
|---|---|---|---|---|
| `qwen/qwen3-embedding-8b` | Qwen (Alibaba) | **32K** | 1024/1792/3584 | **Multilingual** ⭐ |
| `baai/bge-m3` | BAAI | 8K | 1024 | **Multilingual** |
| `thenlper/gte-large` | Thenlper | 8K | 1024 | English |
| `intfloat/multilingual-e5-large` | Intfloat | 8K | 1024 | **90+ languages** |

**Cost at 3.3M/month**: $0.01 × 3.3 = **$0.033**

**Budget fit**: 98.3% of $2 budget remaining.

**Source**: [qwen3-embedding-8b](https://openrouter.ai/qwen/qwen3-embedding-8b), [bge-m3](https://openrouter.ai/baai/bge-m3), [gte-large](https://openrouter.ai/thenlper/gte-large), [multilingual-e5-large](https://openrouter.ai/intfloat/multilingual-e5-large)

---

### $0.02/M tokens

| Model | Provider | Context | Dimensions | Language |
|---|---|---|---|---|
| `openai/text-embedding-3-small` | OpenAI | 8K | 1536 | Multilingual |
| `qwen/qwen3-embedding-4b` | Qwen (Alibaba) | **33K** | ? | **Multilingual** |

**Cost at 3.3M/month**: $0.02 × 3.3 = **$0.066**

**Budget fit**: 96.7% of $2 budget remaining.

**Source**: [text-embedding-3-small](https://openrouter.ai/openai/text-embedding-3-small), [qwen3-embedding-4b](https://openrouter.ai/qwen/qwen3-embedding-4b)

---

### $0.03/M tokens

| Model | Provider | Context | Dimensions | Language |
|---|---|---|---|---|
| `perplexity/pplx-embed-v1-4b` | Perplexity | 32K | ? | English |

**Cost at 3.3M/month**: $0.03 × 3.3 = **$0.099**

**Budget fit**: 95.1% of $2 budget remaining.

**Source**: [openrouter.ai/perplexity/pplx-embed-v1-4b](https://openrouter.ai/perplexity/pplx-embed-v1-4b)

---

### $0.10/M tokens

| Model | Provider | Context | Dimensions | Language |
|---|---|---|---|---|
| `mistralai/mistral-embed-2312` | Mistral | 8K | 1024 | Multilingual |
| `openai/text-embedding-ada-002` | OpenAI | 8K | 1536 | Multilingual (Legacy) |

**Cost at 3.3M/month**: $0.10 × 3.3 = **$0.33**

**Budget fit**: 83.5% of $2 budget remaining.

**Source**: [mistral-embed-2312](https://openrouter.ai/mistralai/mistral-embed-2312), [text-embedding-ada-002](https://openrouter.ai/openai/text-embedding-ada-002)

---

### $0.13/M tokens

| Model | Provider | Context | Dimensions | Language |
|---|---|---|---|---|
| `openai/text-embedding-3-large` | OpenAI | 8K | 3072 | Multilingual |

**Cost at 3.3M/month**: $0.13 × 3.3 = **$0.429**

**Budget fit**: 78.6% of $2 budget remaining.

**Source**: [openrouter.ai/openai/text-embedding-3-large](https://openrouter.ai/openai/text-embedding-3-large)

---

### $0.15/M tokens

| Model | Provider | Context | Dimensions | Language |
|---|---|---|---|---|
| `google/gemini-embedding-001` | Google | **20K** | 768/1024/1536 | **MTEB Multilingual #1** |

**Cost at 3.3M/month**: $0.15 × 3.3 = **$0.495**

**Budget fit**: 75.3% of $2 budget remaining.

**Source**: [openrouter.ai/google/gemini-embedding-001](https://openrouter.ai/google/gemini-embedding-001)

---

### $0.20/M tokens

| Model | Provider | Context | Dimensions | Language |
|---|---|---|---|---|
| `google/gemini-embedding-2` | Google | 8K | 128–3072 | **Multimodal** (text+image) |
| `google/gemini-embedding-2-preview` | Google | 8K | 128–3072 | **Multimodal** (text+image) |

**Cost at 3.3M/month**: $0.20 × 3.3 = **$0.66**

**Budget fit**: 67% of $2 budget remaining.

**Source**: [gemini-embedding-2](https://openrouter.ai/google/gemini-embedding-2), [gemini-embedding-2-preview](https://openrouter.ai/google/gemini-embedding-2-preview)

---

### Models Not Priced on OpenRouter

| Model | Status |
|---|---|
| `qwen/qwen3-embedding-0.6b` | Listed on OR but no price displayed. Likely self-hosted or check `/pricing` page. |

---

## Sensitivity Table

### Monthly Cost by Price Tier

| Price $/1M | 1.5M/mo | **3.3M/mo** (P3) | 10M/mo | Budget fit @3.3M |
|---|---|---|---|---|
| **Free** | $0.00 | **$0.00** | $0.00 | 100% ✅ |
| **$0.004** | $0.006 | **$0.013** | $0.04 | 99.4% ✅ |
| **$0.005** | $0.008 | **$0.017** | $0.05 | 99.2% ✅ |
| **$0.01** | $0.015 | **$0.033** | $0.10 | 98.3% ✅ |
| **$0.02** | $0.030 | **$0.066** | $0.20 | 96.7% ✅ |
| **$0.03** | $0.045 | **$0.099** | $0.30 | 95.1% ✅ |
| **$0.10** | $0.150 | **$0.330** | $1.00 | 83.5% ✅ |
| **$0.13** | $0.195 | **$0.429** | $1.30 | 78.6% ✅ |
| **$0.15** | $0.225 | **$0.495** | $1.50 | 75.3% ✅ |
| **$0.20** | $0.300 | **$0.660** | $2.00 | 67.0% ⚠️ |

> **✅** = well under $2 budget. **⚠️** = at 10M/mo, $0.20/M models hit exactly $2.00/month.

### Executive Summary

**Every single model on OpenRouter fits well within the $2/month budget at P3 scale (3.3M tokens/month).**

- Even the most expensive model (`gemini-embedding-2` at $0.20/M) costs only **$0.66/month** — 67% of budget remains.
- The ADR-baseline model (`text-embedding-3-small` at $0.02/M) costs **$0.066/month** — 96.7% budget remaining.
- At 10M tokens/month (3× P3 scale), all models through $0.13/M remain under $1.50. Only $0.20/M models approach $2.00.

---

## Value Assessment — "Most Worth It" for Guinevere P3

Since cost is essentially negligible for P3 scale (< $1/month for all models), the decision should be driven by **quality, multilingual capability, and context length** rather than price.

### Tier 1 — Best Value Multilingual (Strongly Recommended)

| Model | Price/mo | Why |
|---|---|---|
| **`qwen/qwen3-embedding-8b`** | **$0.033/mo** | Half the price of text-embedding-3-small, 32K context (4× larger), Qwen models excel at multilingual/Asian language tasks. Output dimensions: 1024 (default), 1792, or 3584. Released Oct 2025, mature. |
| **`intfloat/multilingual-e5-large`** | **$0.033/mo** | Same price, 90+ languages, 1024-dim. Strong multilingual MTEB scores. |

### Tier 2 — ADR Baseline (Safe Choice)

| Model | Price/mo | Why |
|---|---|---|
| **`openai/text-embedding-3-small`** | **$0.066/mo** | ADR baseline. 1536-dim, well-documented, broad integration support. Good but not best multilingual. 8K context. |

### Tier 3 — Premium Multilingual (Highest Quality)

| Model | Price/mo | Why |
|---|---|---|
| **`google/gemini-embedding-001`** | **$0.495/mo** | Consistently top of MTEB Multilingual leaderboard. 20K context (2.5× text-embedding-3-small). Flexible dimensions (768/1024/1536). |
| **`openai/text-embedding-3-large`** | **$0.429/mo** | 3072-dim (best for high-precision retrieval). Strong English + good multilingual. |

### Tier 4 — Multimodal (if needed later)

| Model | Price/mo | Why |
|---|---|---|
| **`google/gemini-embedding-2`** | **$0.66/mo** | Only multimodal embedding on OR. Text+image in unified space. Still **well under $2 budget**. |

---

## Recommendation

**Primary**: `qwen/qwen3-embedding-8b` at **$0.01/M ($0.033/mo)**
- Best price-to-quality ratio for multilingual
- 32K context (4× text-embedding-3-small's 8K)
- Flexible output dimensions
- Qwen series consistently strong on non-English tasks

**Secondary (fallback/ADR compliance)**: `openai/text-embedding-3-small` at **$0.02/M ($0.066/mo)**

**Premium upgrade**: `google/gemini-embedding-001` at **$0.15/M ($0.495/mo)** if MTEB multilingual benchmarks matter most.

**Bottom line**: All models cost < $1/month at P3 scale. Pick on quality, not price.

---

## Sources

All prices verified from OpenRouter model pages:

| Model | URL |
|---|---|
| text-embedding-3-small | https://openrouter.ai/openai/text-embedding-3-small |
| text-embedding-3-large | https://openrouter.ai/openai/text-embedding-3-large |
| text-embedding-ada-002 | https://openrouter.ai/openai/text-embedding-ada-002 |
| gemini-embedding-001 | https://openrouter.ai/google/gemini-embedding-001 |
| gemini-embedding-2 | https://openrouter.ai/google/gemini-embedding-2 |
| gemini-embedding-2-preview | https://openrouter.ai/google/gemini-embedding-2-preview |
| qwen3-embedding-8b | https://openrouter.ai/qwen/qwen3-embedding-8b |
| qwen3-embedding-4b | https://openrouter.ai/qwen/qwen3-embedding-4b |
| qwen3-embedding-0.6b | https://openrouter.ai/qwen/qwen3-embedding-0.6b |
| pplx-embed-v1-0.6b | https://openrouter.ai/perplexity/pplx-embed-v1-0.6b |
| pplx-embed-v1-4b | https://openrouter.ai/perplexity/pplx-embed-v1-4b |
| bge-base-en-v1.5 | https://openrouter.ai/baai/bge-base-en-v1.5 |
| bge-m3 | https://openrouter.ai/baai/bge-m3 |
| gte-large | https://openrouter.ai/thenlper/gte-large |
| e5-base-v2 | https://openrouter.ai/intfloat/e5-base-v2 |
| multilingual-e5-large | https://openrouter.ai/intfloat/multilingual-e5-large |
| mistral-embed-2312 | https://openrouter.ai/mistralai/mistral-embed-2312 |
| llama-nemotron-embed-vl-1b-v2:free | https://openrouter.ai/nvidia/llama-nemotron-embed-vl-1b-v2:free/pricing |
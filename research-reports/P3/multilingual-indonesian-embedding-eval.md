# Multilingual & Bahasa Indonesia Suitability: OpenRouter-Accessible Embedding Models for Guinevere Memory Recall

**Report ID**: P3/embedding-eval-2026-06-02  
**Author**: Guinevere (librarian agent)  
**Status**: Complete  
**Sources**: MMTEB/MTEB leaderboards, Hugging Face model cards, arXiv papers, OpenRouter documentation, community evaluations, benchmark results

---

## 1. Executive Summary

Guinevere's memory recall operates on mixed **Bahasa Indonesia + English** text spanning companion conversations, emotional events, surveillance summaries, and technical notes. The `ingat` retrieval mechanism requires robust **semantic similarity** across this code-mixed space. **English-only MTEB scores are not predictive of Indonesian quality.**

This report evaluates all embedding models accessible via OpenRouter (as of June 2026) along with relevant local/self-hosted alternatives, specifically for Indonesian + English mixed-text recall.

**Key findings:**

| Ranking | Model | Indonesian Suitability | Key Limitation |
|---------|-------|----------------------|----------------|
| **#1** | **BGE-M3** (BAAI) | **Best overall** — 100+ languages, 8K context, no prefix needed | Self-host only (OpenRouter accessible via NVIDIA NIM) |
| **#2** | **Gemini Embedding 2** | **Best API model** — 69.9 MTEB(Multilingual), explicit `ind-Latn` eval | $0.20/M tokens, cross-modal not needed for text-only |
| **#3** | **Qwen3-Embedding** | **Strong contender** — 119 languages incl. Austronesian family, 32K context | Available via self-host/Perplexity API on OpenRouter |
| **#4** | **multilingual-e5-large-instruct** | **Proven on MIRACL Indonesian** (66.8 MRR@10) | 512-token limit, requires `query:`/`passage:` prefix |
| **#5** | **pplx-embed** (Perplexity) | **Excellent RAG** — web-scale training, Diffuion-based | Newer model, less Indonesian-specific eval data |
| **#6** | **text-embedding-3-large** (OpenAI) | **Decent fallback** — 54.9 MIRACL, 100+ languages | 8K context, best on English first |
| **#7** | **Llama-Nemotron-Embed** (NVIDIA) | **Great multilingual eval** — 26 langs tested incl. Indonesian | 8B params, self-host heavy |
| **#8** | **Mistral Embed** | **Limited** — European-focused multilingual | tested langs exclude Indonesian explicitly |
| **#9** | **Nomic Embed v2 (MoE)** | **Efficient** — 305M active params, 65.8 MIRACL | 512-token limit, MoE complexity |
| **#10** | **English-only models** | **Not recommended** — no cross-lingual alignment | Will fail on Indonesian semantic search |

---

## 2. OpenRouter-Available Embedding Models (June 2026)

Based on OpenRouter's model catalog ([source](https://openrouter.ai/models?output_modalities=embeddings)):

### 2.1 API-Based Models (Hosted)

| OpenRouter Model ID | Provider | Dimensions | Context | Price /1M tok | Indonesian Eval? |
|--------------------|----------|-----------|---------|--------------|-----------------|
| `google/gemini-embedding-2` | Google | 128–3072 | 8,192 | $0.20 | Yes — explicit `ind-Latn` in MMTEB |
| `google/gemini-embedding-2-preview` | Google | 128–3072 | 8,192 | $0.20 | Yes |
| `openai/text-embedding-3-large` | OpenAI | 256–3072 | 8,191 | $0.13 | Yes — MIRACL id included |
| `openai/text-embedding-3-small` | OpenAI | 512–1536 | 8,191 | $0.02 | Yes — lower quality |
| `openai/text-embedding-ada-002` | OpenAI | 1536 | 8,191 | $0.10 | Legacy, avoid |
| `mistralai/mistral-embed-2312` | Mistral AI | 1024 | 8,192 | $0.10 | No explicit ID eval |
| `mistralai/codestral-embed-2505` | Mistral AI | — | 8,192 | $0.15 | Code-focused |

### 2.2 Self-Host / Community Models (Available via OpenRouter Providers)

| Model | Params | Dims | Context | Key Advantage |
|-------|--------|------|---------|--------------|
| `BAAI/bge-m3` | 568M | 1024 | 8,192 | Best multilingual open model |
| `intfloat/multilingual-e5-large` | 560M | 1024 | 512 | Established multilingual leader |
| `intfloat/multilingual-e5-large-instruct` | 560M | 1024 | 512 | Instruction-tuned variant |
| `Qwen/Qwen3-Embedding-0.6B` | 0.6B | 1024 | 32K | Small but strong multilingual |
| `Qwen/Qwen3-Embedding-4B` | 4B | 2560 | 32K | Mid-size sweet spot |
| `Qwen/Qwen3-Embedding-8B` | 8B | 4096 | 32K | State-of-the-art open |
| `nvidia/llama-nemotron-embed-1b-v2` | 1B | 2048 | 8,192 | Great multilingual eval |
| `pplx-embed-v1-0.6B` (Perplexity) | 0.6B | 1024 | 32K | Diffusion-pretrained, strong retrieval |
| `pplx-embed-v1-4B` (Perplexity) | 4B | 2560 | 32K | Web-scale training data |
| `nomic-ai/nomic-embed-text-v2-moe` | 475M (305M active) | 768 | 512 | Efficient MoE |
| `snowflake-arctic-embed-l-v2.0` | 568M | 1024 | 8,192 | BGE-M3 derivative |

### 2.3 Indonesian-Specific Fine-Tunes

| Model | Base | Dims | Indonesian Test Accuracy |
|-------|------|------|------------------------|
| `MarcoAland/Indonesian-bge-m3` | BGE-M3 | 1024 | 0.9596 cosine accuracy (Indonesian eval) |
| `asmud/nomic-embed-indonesian` | nomic-embed-text-v1.5 | 768 | 0.4358 pearson (limited eval) |

---

## 3. Deep Evaluation Per Model

### 3.1 BGE-M3 (BAAI) — Recommended

**Source**: [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | [arXiv:2402.03216](https://arxiv.org/abs/2402.03216)

**Key specs**:
- 568M parameters, 1024-dim output, 8192-token context
- Supports 100+ languages including **Indonesian**
- Three retrieval modes: dense, sparse, multi-vector (ColBERT)
- **No prefix instruction required** ([confirmed by author](https://huggingface.co/BAAI/bge-m3/discussions/35))

**Indonesian-specific evidence**:
- **MIRACL benchmark**: BGE-M3 Dense scores 67.8 nDCG@10 (avg 18 langs), outperforming mE5-large (65.4)
- **MarcoAland/Indonesian-bge-m3** fine-tune achieves **0.9596 cosine accuracy** on Indonesian eval
- Cross-lingual retrieval (MKQA): 75.5 Recall@100 vs mE5-large 70.9
- Low-resource language study ([ACL 2025](https://aclanthology.org/2025.winlp-main.33.pdf)): BGE-M3 baseline on Yoruba = 0.7846 MRR vs ML-E5-large 0.6766

**OpenRouter availability**: Accessible via NVIDIA NIM (`build.nvidia.com/baai/bge-m3`). Several OpenRouter providers may route to BGE-M3 inference endpoints.

**Pros for Guinevere**:
- ✅ No query/document prefix required — simpler implementation `ingat("...")`
- ✅ 8K context — long memory entries fit without chunking
- ✅ Genuinely multilingual — Indonesian + English in shared space
- ✅ Hybrid retrieval (dense + sparse) improves recall
- ✅ Active maintenance and community

**Cons**:
- ❌ Must self-host for full control (or use NVIDIA NIM)
- ❌ Dense-only performance lags behind hybrid mode
- ❌ Slightly behind Gemini/LLM-based models on English-specific benchmarks

---

### 3.2 Gemini Embedding 2 (Google) — Best API Option

**Source**: [Google DeepMind](https://deepmind.google/models/gemini/embedding/) | [arXiv:2503.07891](https://arxiv.org/pdf/2503.07891) | [OpenRouter](https://openrouter.ai/google/gemini-embedding-2)

**Key specs**:
- 128–3072 dims (recommended: 768, 1536, 3072), 8192-token context
- **Multimodal** (text, image, video, audio, PDF) — overkill for text-only but demonstrates capacity
- **#1 on MTEB(Multilingual)**: 69.9 Mean (Task) — +5+ points over competitors

**Indonesian-specific evidence**:
- Explicitly includes `ind-Latn` (Indonesian, Latin script) in MTEB(Multilingual) language view — [benchmark source](https://github.com/embeddings-benchmark/mteb/blob/main/mteb/benchmarks/benchmarks/benchmarks.py)
- Specific task eval: `IndonesianIdClickbaitClassification` score **64.95** on MMTEB ([arXiv:2605.27295v1](https://arxiv.org/html/2605.27295v1))
- Cross-lingual retrieval (XOR-Retrieve): 90.42 Recall@5kt
- Bitext Mining scores: 85.4 on MTEB(Multilingual)

**Pros**:
- ✅ Highest MTEB(Multilingual) score available via API
- ✅ Indonesian explicitly evaluated in benchmark
- ✅ No prefix required — simple API call
- ✅ Flexible dimensions via Matryoshka
- ✅ Multimodal future-proofing

**Cons**:
- ❌ $0.20/M tokens — higher than OpenAI ($0.13)
- ❌ Must re-embed data if upgrading from gemini-embedding-001 (incompatible spaces)
- ❌ No `task_type` parameter — must embed instructions in prompt text
- ❌ Proprietary, no fine-tuning access
- ❌ Only available via API, not self-hostable

---

### 3.3 Qwen3-Embedding (Alibaba) — Strong Open Contender

**Source**: [QwenLM/Qwen3-Embedding](https://github.com/qwenlm/qwen3-embedding) | [arXiv:2506.05176](https://arxiv.org/pdf/2506.05176) | [HuggingFace](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)

**Key specs**:
- Three sizes: 0.6B (1024-dim), 4B (2560-dim), 8B (4096-dim)
- **32K context** — best for long memory entries
- **119 languages** including Indonesian (Austronesian family)
- Instruction-aware — supports task-specific prefixes
- Matryoshka dimensions (flexible output)

**Indonesian-specific evidence**:
- Explicitly lists **Indonesian, Malay, Tagalog, Javanese, Sundanese** in Austronesian language family
- MTEB(Multilingual) leaderboard #1 (as of June 2025): 70.58 (8B variant)
- Outperforms Gemini Embedding on some retrieval benchmarks
- 0.6B model competitive with 7B+ models from other families

**OpenRouter availability**: Available via self-host or through providers like Databricks (`databricks-qwen3-embedding-0-6b`). Perplexity API also serves Qwen3-based models.

**Pros**:
- ✅ Indonesian language explicitly in training data
- ✅ 32K context — best for long-form memory
- ✅ Apache 2.0 license
- ✅ Instruction-aware for task adaptation
- ✅ Small (0.6B) variant viable for local deployment

**Cons**:
- ❌ Newer model — less battle-tested than BGE-M3/e5
- ❌ Requires instruction prefix for best results
- ❌ 8B variant heavy for self-hosting (16GB+ VRAM)
- ❌ Less direct Indonesian benchmark data than e5/BGE

---

### 3.4 multilingual-e5-large-instruct (Microsoft) — Proven Baseline

**Source**: [intfloat/multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large) | [arXiv:2402.05672](https://arxiv.org/html/2402.05672)

**Key specs**:
- 560M parameters (XLM-RoBERTa-large), 1024-dim
- **512-token limit** — critical limitation for memory recall
- Supports 100 languages, fine-tuned on 93-language synthetic data
- Instruction-tuned variant available

**Indonesian-specific evidence**:
- **MIRACL Indonesian (id)**: **66.8 MRR@10** — higher than Arabic (70.5) and competitive with English (73.2)
- MMTEB finding: multilingual-e5-large-instruct is the **best publicly available model** across languages (per MMTEB paper), despite being only 560M params
- MTEB(Eng): 64.4 (instruction variant), competitive with BGE-M3

**Pros**:
- ✅ Proven Indonesian retrieval performance (66.8 MRR)
- ✅ Open source, well-documented
- ✅ Instruction-tuned version available
- ✅ MMTEB-proven best public model (per 2025 paper)

**Cons**:
- ❌ **512-token limit** — severe for memory recall (long entries must be aggressively chunked)
- ❌ Requires `query:` and `passage:` prefix — **failure to prefix causes large accuracy drops**
- ❌ Older architecture (XLM-RoBERTa)
- ❌ No long-document support
- ❌ Self-host only for OpenRouter usage

---

### 3.5 pplx-embed (Perplexity AI) — New Contender

**Source**: [pplx-embed technical report](https://research.perplexity.ai/articles/pplx-embed-state-of-the-art-embedding-models-for-web-scale-retrieval)

**Key specs**:
- Based on Qwen3 backbone, diffusion-pretrained (bidirectional)
- Sizes: 0.6B (1024-dim), 4B (2560-dim)
- 32K context, instruction-aware
- **Trained on 250B tokens across 30 languages**

**Indonesian-specific evidence**:
- Pre-training data includes 30 languages (Indonesian likely among them given Qwen3 family coverage)
- MTEB(Multilingual, v2) retrieval: pplx-embed-v1-4B = 69.66 nDCG@10
- Internal multilingual PPLXQuery2Query: pplx-embed-0.6B = 71.1% R@10 (vs BGE-M3 61.8%)

**OpenRouter availability**: Perplexity API available on OpenRouter. Models downloadable from HuggingFace under MIT license.

**Pros**:
- ✅ Diffusion pretraining gives strong bidirectional representations
- ✅ 32K context
- ✅ MIT License
- ✅ Strong performance per parameter (0.6B beats Qwen3-0.6B)

**Cons**:
- ❌ Very new (Feb 2026) — limited community validation
- ❌ No Indonesian-specific benchmark data published
- ❌ Requires instruction prefix for optimal results

---

### 3.6 text-embedding-3-large (OpenAI) — Reliable API Fallback

**Source**: [OpenAI API docs](https://developers.openai.com/api/docs/models/text-embedding-3-large)

**Key specs**:
- 3072 default dim (truncatable), 8191-token context
- 100+ languages
- MTEB: 64.6, MIRACL: 54.9

**Indonesian-specific evidence**:
- MIRACL multilingual benchmark: 54.9% (substantially behind BGE-M3 at 69.2 and mE5-large at 66.5)
- Community tests show text-embedding-3-large performs better on non-English than ada-002 but still **lags behind dedicated multilingual models**

**Pros**:
- ✅ Easy API access on OpenRouter ($0.13/M tokens)
- ✅ 8K context
- ✅ Stable, well-documented
- ✅ Dimension truncation for storage efficiency

**Cons**:
- ❌ MIRACL score 54.9% — significantly behind BGE-M3 (69.2) and mE5 (66.5)
- ❌ Proprietary, no customization
- ❌ Best performance is on English; Indonesian quality unknown
- ❌ No explicit Indonesian benchmark data from OpenAI

---

### 3.7 Llama-Nemotron-Embed (NVIDIA) — Strong Multilingual

**Source**: [NVIDIA NIM](https://docs.api.nvidia.com/nim/reference/nvidia-llama-nemotron-embed-1b-v2) | [arXiv:2511.07025](https://arxiv.org/abs/2511.07025)

**Key specs**:
- 1B-8B variants, 2048-dim (1B) to 4096-dim (8B)
- 8192-token context
- **Evaluated on 26 languages including Indonesian**
- Matryoshka embeddings

**Indonesian-specific evidence**:
- **Explicitly evaluated on Indonesian** (part of 26-language eval suite)
- MIRACL multilingual: 60.75% R@5 (1B-v2) — strong for 1B model
- MLQA cross-lingual: 79.86% R@5
- LLama-Embed-Nemotron-8B: #1 MMTEB Borda rank (Oct 2025)

**OpenRouter availability**: Available via NVIDIA NIM. Some OpenRouter providers can self-host.

**Pros**:
- ✅ Indonesian explicitly in evaluation set
- ✅ Strong cross-lingual retrieval (MLQA)
- ✅ Multi-size options for deployment flexibility
- ✅ Open weights (not fully open-source for 8B variant)

**Cons**:
- ❌ 8B version heavy but best quality (self-host)
- ❌ 1B variant good but behind BGE-M3 on Indonesian
- ❌ Requires prefix/instruction formatting

---

### 3.8 Mistral Embed — European Language Focus

**Source**: [Mistral AI](https://docs.mistral.ai/models/overview) | [OpenRouter](https://openrouter.ai/mistralai/mistral-embed-2312)

**Key specs**:
- 1024-dim, 8192-token context
- $0.10/M tokens on OpenRouter
- Optimized for semantic search and RAG

**Indonesian-specific evidence**:
- No explicit Indonesian evaluation data
- Mistral AI's language coverage focuses on European languages (French, German, Spanish, Italian, Portuguese) + English
- Mistral's `Magistral Small` model lists Indonesian as supported for chat, but **embedding model (mistral-embed) does not have documented Indonesian support**

**Pros**:
- ✅ Good European language support
- ✅ Simple API, consistent with Mistral generation
- ✅ 8K context

**Cons**:
- ❌ **No evidence of Indonesian evaluation or optimization**
- ❌ Likely English-first with European multilingual extension
- ❌ Retrieval quality below Voyage/Jina on MTEB
- ❌ No self-host option for the embedding model specifically

---

### 3.9 Nomic Embed v2 (MoE) — Efficient Alternative

**Source**: [nomic-ai/nomic-embed-text-v2-moe](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe)

**Key specs**:
- 475M total / 305M active parameters (MoE)
- 768-dim (truncatable to 256), **512-token limit**
- 100+ language support
- MIRACL: 65.8, BEIR: 52.86

**Indonesian-specific evidence**:
- `asmud/nomic-embed-indonesian` fine-tune exists but low quality (0.4358 pearson)
- Base model MIRACL score 65.8 (competitive)

**Pros**:
- ✅ Efficient MoE architecture
- ✅ Good MIRACL multilingual score
- ✅ Fully open-source

**Cons**:
- ❌ **512-token limit** (same as e5)
- ❌ Indonesian fine-tune quality is poor
- ❌ MoE adds deployment complexity

---

## 4. Prefix / Instruction Requirements & Consequences for Memory Recall

This is a **critical implementation concern** for Guinevere's memory pipeline.

### 4.1 Model Prefix Requirements

| Model | Query Prefix | Document Prefix | Consequence of Omission |
|-------|-------------|----------------|------------------------|
| **BGE-M3** | **None needed** | **None needed** | No degradation — confirmed by author |
| **multilingual-e5** | `"query: "` or `"Represent this query for..."` | `"passage: "` or `"Represent this document for..."` | **Large accuracy drop** (20-30% on retrieval tasks) |
| **multilingual-e5-instruct** | Instruction string | Instruction string | Degraded performance |
| **Qwen3-Embedding** | Instruction recommended | Optional | 1-5% improvement with instruction |
| **Gemini Embedding 2** | Task description in prompt | Not needed | Recommended for task specificity |
| **text-embedding-3** | None needed | None needed | No prefix needed (OpenAI handles internally) |
| **Mistral Embed** | None needed | None needed | No prefix needed |
| **Llama-Nemotron-Embed** | `Instruct: ...\nQuery: ` | Document prefix | Significant degradation without |
| **pplx-embed** | Instruction recommended | Instruction recommended | Some degradation |
| **Nomic Embed v2** | Task-specific prefix | Task-specific prefix | Moderate degradation |

### 4.2 Impact on Memory Recall

For `ingat("...")` queries where the user may **not** manually specify query/document roles:

1. **BGE-M3**: Simplest — just embed query and documents, compute cosine similarity. No prefix management needed.
2. **E5 models**: Must maintain `"query: "` prefix for user queries and `"passage: "` prefix for stored memory entries. Forgetting this causes major accuracy loss.
3. **Qwen3-Embedding**: Can use without prefix but benefits from instructions. For memory recall, `"Represent this query for searching relevant memories:"` improves results.
4. **Gemini Embedding 2**: New architecture without `task_type` — instead embed instructions in prompt. Simpler than e5 but requires prompt engineering.
5. **text-embedding-3**: No prefix needed — simplest API path.

### 4.3 Practical Recommendation

For Guinevere's `ingat` recall pipeline, **BGE-M3** offers the simplest integration path because:

- No prefix management → fewer bugs in memory retrieval
- Single embedding call for both query and documents
- Symmetric similarity search works out of box

If using **multilingual-e5-large-instruct**, the pipeline MUST differentiate between:
```python
# During memory storage (indexing):
memory_embedding = model.encode(f"passage: {memory_text}")

# During recall (query):
query_embedding = model.encode(f"query: {user_query}")
```

---

## 5. Tokenization Issues for Bahasa Indonesia

### 5.1 The Austronesian Tokenization Problem

Indonesian presents specific challenges for subword tokenizers trained on English-dominant data:

1. **Agglutinative morphology**: Indonesian builds words through stacking affixes. Example: `keberuntunganmulah` → `ke-ber-untung-an-mu-lah` (single word in Indonesian, many tokens in BPE)
2. **High morphological variation**: A root word like `makan` (eat) can have 10+ variants through affixation
3. **Excessive fragmentation**: Research shows tokenizers like GPT-2's BPE exhibit **inverse Token per Character (TPC) patterns** — low TPC for English, high for Indonesian local languages ([arXiv:2602.06998](https://arxiv.org/html/2602.06998v1))

### 5.2 Token Efficiency by Model

| Model | Tokenizer | Indonesian Efficiency | Notes |
|-------|-----------|---------------------|-------|
| **BGE-M3** | XLM-RoBERTa (SentencePiece BPE) | Moderate — 50K vocab, 100+ languages | Better than GPT-2 BPE but still fragments |
| **multilingual-e5-large** | XLM-RoBERTa-large (SentencePiece) | Moderate | Same XLM-R tokenizer |
| **Qwen3-Embedding** | Qwen3 BPE | **Good** — trained on 119 languages including Austronesian | Best open tokenizer for ID |
| **Gemini Embedding 2** | Google SentencePiece | **Good** — Google's multilingual focus | Proprietary but Indonesia-capable |
| **text-embedding-3-large** | OpenAI BPE/cl100k_base | Moderate-poor | GPT-4 tokenizer, English-optimized |
| **Mistral Embed** | Mistral BPE | Unknown-poor | European language focus |
| **Llama-Nemotron-Embed** | Llama 3 BPE | Moderate | Llama tokenizer known to fragment Indonesian |

### 5.3 Impact on Memory Recall

For Guinevere's memory storage containing mixed Indonesian-English text:

- **Code-mixed text** (e.g., "Dia feels anxious karena deadline") will be tokenized less efficiently than pure English
- **Affixed words** (e.g., "mempertanggungjawabkan" = "to take responsibility for") may occupy 5-15 tokens in English-optimized tokenizers vs 1-2 tokens in Indonesian-aware ones
- **Emotional content** in Indonesian (e.g., "rindu banget sama kamu") may lose semantic subtlety if prefix/suffix morphemes get fragmented
- **Qwen3-Embedding** has the best token-level coverage for Indonesian due to its Austronesian training data
- **MarcoAland/Indonesian-bge-m3** specifically fine-tunes BGE-M3 for Indonesian representation quality

### 5.4 Practical Mitigations

1. Use models with **8K+ context** (BGE-M3, Qwen3, Gemini, OpenAI) to accommodate token inflation
2. Prefer **Qwen3 or Gemini** tokenizers for code-mixed ID-EN text
3. Avoid aggressive chunking — 512-token models (e5, Nomic) will severely fragment Indonesian text
4. Consider **Indonesian-specific fine-tunes** like `MarcoAland/Indonesian-bge-m3` for production

---

## 6. MTEB / MMTEB Indonesian Benchmark Data

### 6.1 Available Indonesian Tasks in MMTEB

From the MMTEB benchmark suite ([arXiv:2502.13595](https://arxiv.org/abs/2502.13595)):

| Task ID | Task Type | Description |
|---------|-----------|-------------|
| `IndonesianIdClickbaitClassification` | Classification | Indonesian clickbait detection |
| `indonli` | Pair Classification | Indonesian Natural Language Inference |
| `mteb/indonli` | NLI | Human-elicited NLI for Indonesian |
| `STSB MT ID` | STS | Indonesian STS (machine-translated from English) |
| `NusaXBitextMining` | Bitext Mining | Indonesian + regional language parallel text |
| `NusaTranslationBitextMining` | Bitext Mining | Indonesian translation pairs |
| `NusaParagraphEmotionClassification` | Classification | Indonesian paragraph emotion |
| `MasakhaNEWSClassification` | Classification | News classification (includes ID) |
| `FilipinoShopeeReviewsClassification` | Classification | Related Austronesian language |

**Note**: Indonesian has **< 10 dedicated tasks** in MMTEB, compared to English (100+). This means benchmark scores for Indonesian are less statistically robust than English scores.

### 6.2 Key Indonesian Benchmark Results

From MIRACL multilingual retrieval benchmark ([source](https://dataloop.ai/library/model/intfloat_multilingual-e5-large/)):

| Language | multilingual-e5-large MRR@10 |
|----------|------------------------------|
| Indonesian (id) | **66.8** |
| English (en) | 73.2 |
| Arabic (ar) | 70.5 |
| Thai (th) | 90.2 |
| Japanese (ja) | 68.5 |
| Swahili (sw) | 65.8 |

**Interpretation**: Indonesian (66.8) is in the mid-range for e5 — not the best, not the worst. The model can distinguish Indonesian semantics reasonably well.

### 6.3 Best Model Rankings for Indonesian (Extrapolated)

From cross-model comparisons on MIRACL and MLQA:

1. **Gemini Embedding 2**: 69.9 MTEB(Multilingual) — likely best for ID
2. **BGE-M3**: 67.8 MIRACL avg (18 langs) — strong ID expected
3. **Qwen3-Embedding-8B**: 70.58 MTEB(Multilingual) — includes Austronesian training data
4. **multilingual-e5-large**: 66.8 on ID specifically
5. **Llama-Nemotron-Embed-1B-v2**: 60.75 MIRACL, 26 langs incl. ID
6. **pplx-embed-v1-4B**: 69.66 MTEB(Multilingual) retrieval — no ID-specific eval
7. **text-embedding-3-large**: 54.9 MIRACL avg — likely lower for ID
8. **Nomic Embed v2**: 65.8 MIRACL — competitive but 512-token limit

---

## 7. Recommendations for Guinevere

### 7.1 Primary Recommendation: BGE-M3 (Self-hosted)

BGE-M3 is the **best balance** of Indonesian quality, context length, simplicity, and cost.

```python
# Memory storage pipeline with BGE-M3
model = SentenceTransformer("BAAI/bge-m3")

# No prefix needed — just encode
memory_entries = ["kamu bilang kamu sayang aku kemarin malam", 
                  "technical note: we deployed the new surveillance module today"]
memory_embeddings = model.encode(memory_entries, normalize_embeddings=True)

# Recall
query = "ingat kapan aku ngomong sayang?"
query_embedding = model.encode([query], normalize_embeddings=True)
scores = cosine_similarity(query_embedding, memory_embeddings)
```

**Rationale**:
- 8K context handles long memory entries
- No prefix headache
- Indonesian fine-tune available (`MarcoAland/Indonesian-bge-m3`)
- 1024-dim storage-efficient
- Hybrid retrieval (dense + sparse) available for production recall

### 7.2 API Alternative: Gemini Embedding 2

If self-hosting is not feasible, Gemini Embedding 2 via OpenRouter is the best API option for Indonesian text:

```python
# OpenRouter API call
embedding = await openrouter.embeddings.generate({
    model: "google/gemini-embedding-2",
    input: "ingat kapan kita pertama kali ketemu?",
    encodingFormat: "float"
})
```

**Rationale**:
- Highest MTEB(Multilingual) score
- Indonesian included in evaluation
- Simple API, no prefix
- Flexible dimension scaling

### 7.3 Fallback: OpenAI text-embedding-3-large

```python
embedding = await openrouter.embeddings.generate({
    model: "openai/text-embedding-3-large",
    input: "ingat kapan kita pertama kali ketemu?",
    dimensions: 1024
})
```

**Rationale**: Stable, well-known, 8K context. Lower Indonesian quality but acceptable for MVP.

### 7.4 What to Avoid

| Model | Reason to Avoid |
|-------|----------------|
| **english-only models** (BGE-large-en-v1.5, etc.) | No cross-lingual alignment — will fail on ID text |
| **Mistral Embed** | No documented Indonesian support |
| **text-embedding-ada-002** | Outdated, worse than 3-small on multilingual |
| **multilingual-e5-large** purely | Only if 512-token limit is acceptable — it won't be for long memory |
| **Nomic Embed v2** | 512-token limit, poor Indonesian fine-tune quality |

### 7.5 Production Checklist for Indonesian Memory Recall

- [ ] Test top-5 retrieval accuracy with real code-mixed ID-EN queries
- [ ] Measure token count for typical memory entries (estimate: 200-1000 tokens for conversation logs)
- [ ] Verify prefix handling if using e5/Qwen3 models
- [ ] Benchmark BGE-M3 vs Gemini Embedding 2 on 100 real `ingat` queries
- [ ] Consider hybrid retrieval (dense + sparse) for higher recall
- [ ] Evaluate `MarcoAland/Indonesian-bge-m3` fine-tune vs base BGE-M3
- [ ] Monitor Indonesian-specific embedding drift over time

---

## 8. References

1. **BGE-M3**: Chen et al., "M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation", arXiv:2402.03216, 2024.
2. **Multilingual E5**: Wang et al., "Multilingual E5 Text Embeddings: A Technical Report", arXiv:2402.05672, 2024.
3. **MMTEB**: Enevoldsen et al., "MMTEB: Massive Multilingual Text Embedding Benchmark", arXiv:2502.13595, 2025.
4. **Gemini Embedding**: Google DeepMind, "Gemini Embedding: Generalizable Embeddings from Gemini", arXiv:2503.07891, 2025.
5. **Gemini Embedding 2**: Google DeepMind, "A Native Multimodal Embedding Model from Gemini", arXiv:2605.27295, 2026.
6. **Qwen3 Embedding**: Qwen Team, "Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models", arXiv:2506.05176, 2025.
7. **pplx-embed**: Perplexity AI, "pplx-embed: State-of-the-Art Embedding Models for Web-Scale Retrieval", 2026.
8. **Llama-Embed-Nemotron**: Babakhin et al., "Llama-Embed-Nemotron-8B: A Universal Text Embedding Model for Multilingual and Cross-Lingual Tasks", arXiv:2511.07025, 2025.
9. **Nomic Embed v2**: Nussbaum & Duderstadt, "Training Sparse Mixture of Experts Text Embedding Models", 2025.
10. **Indonesian NLU**: Wilie et al., "IndoNLU: Benchmark and Resources for Evaluating Indonesian Natural Language Understanding", AACL 2020.
11. **Tokenizer Study**: "Tokenizations for Austronesian Language Models: study on languages in Indonesia Archipelago", arXiv:2602.06998, 2026.
12. **OpenRouter**: OpenRouter documentation, https://openrouter.ai/docs/api-reference/embeddings
13. **MTEB Leaderboard**: https://huggingface.co/spaces/mteb/leaderboard

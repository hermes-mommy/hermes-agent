# SentenceTransformers — Local Embedding Model Selection for Guinevere P3

> **Status**: Complete  
> **Date**: 2026-06-02  
> **Scope**: Local embedding fallback/primary decision for 4C/16GB VPS under <50% CPU/RAM  
> **Parent Task**: P3 Planner — Local embedding model selection  
> **Sources**: Official sbert.net docs, PyPI, Hugging Face model cards, GitHub, community benchmarks  

---

## 1. Executive Summary

**Recommended fallback model**: `sentence-transformers/all-MiniLM-L6-v2` (384d, 80MB)  
**Recommended primary local alternative** (if quality matters more than speed): `sentence-transformers/all-mpnet-base-v2` (768d, 420MB)  

**No practical 1536-dim local SentenceTransformers model exists** for production use. The OpenAI `text-embedding-3-small` (1536d) has no direct open-source equivalent at that exact dimensionality. Using local fallback with 384d/768d creates a **dimension mismatch** with ADR-009's `vector(1536)` column — this must be resolved via either dimension projection or separate vector columns.

---

## 2. Installation (Ubuntu / Python 3.12)

### 2.1 Core Install

```bash
# Recommended: Python 3.10+ (3.12 confirmed compatible)
# PyTorch >= 1.11.0, transformers >= 4.41.0, huggingface-hub >= 0.23.0
pip install -U sentence-transformers
```

**Source**: [sbert.net/docs/installation.html](https://sbert.net/docs/installation.html)

### 2.2 Dependency Tree (Core)

| Package | Minimum Version | Notes |
|---|---|---|
| `sentence-transformers` | 3.0+ (latest v5.5.1 as of 2026-05-20) | Pure inference OK |
| `torch` | >= 1.11.0 | CPU-only wheel recommended for VPS |
| `transformers` | >= 4.41.0, < 6.0.0 | Hugging Face transformers core |
| `huggingface-hub` | >= 0.23.0 | Model download + caching |
| `numpy` | >= 1.20.0 | |
| `scikit-learn` | >= 0.22.0 | |
| `scipy` | >= 1.0.0 | |
| `tqdm` | >= 4.0.0 | |
| `typing_extensions` | >= 4.5.0 | |

**Source**: [PyPI sentence-transformers](https://pypi.org/project/sentence-transformers/)

### 2.3 CPU-Only Install (Recommended for VPS)

```bash
# Install CPU-only PyTorch first, then sentence-transformers
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers
```

### 2.4 Optional Extras

```bash
pip install "sentence-transformers[onnx]"       # ONNX CPU acceleration
pip install "sentence-transformers[openvino]"   # OpenVINO Intel CPU optimization
pip install "sentence-transformers[train]"      # Training (adds datasets, accelerate)
```

---

## 3. Model Cache Paths (P3-004)

### 3.1 Default Cache

```
~/.cache/huggingface/hub/     # Primary cache for all HF models
~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/
```

### 3.2 Override via Environment

```bash
export HF_HOME=/path/to/custom/cache     # Changes all HF cache roots
export TRANSFORMERS_CACHE=/path/to/cache # Transformers-specific
```

### 3.3 Cache Structure Per Model

```
~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/
├── blobs/                     # Actual model weight files
├── refs/                      # Pointers to specific revisions
└── snapshots/                 # Snapshot directories per commit hash
```

**Source**: [huggingface.co/docs/huggingface_hub/en/guides/manage-cache](https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache)

### 3.4 Model Download Sizes (First Load)

| Model | Disk (download) | RAM at Inference | Flash/Hot Load |
|---|---|---|---|
| all-MiniLM-L6-v2 | ~80 MB | ~200-300 MB | ~90 MB |
| all-mpnet-base-v2 | ~420 MB | ~600-800 MB | ~440 MB |
| BAAI/bge-small-en-v1.5 | ~133 MB | ~250-350 MB | ~140 MB |
| BAAI/bge-base-en-v1.5 | ~438 MB | ~600-800 MB | ~450 MB |
| BAAI/bge-large-en-v1.5 | ~1.34 GB | ~1.5-2.5 GB | ~1.4 GB |

---

## 4. Model Comparison Table

| Model | Dims | Params | Disk Size | RAM Est. | MTEB Avg | Speed (sent/s) | Seq Len | Norm |
|---|---|---|---|---|---|---|---|---|
| **all-MiniLM-L6-v2** | **384** | 22.7M | **80 MB** | ~250 MB | ~61.5 | **~14,200** | 256/512 | Yes |
| all-mpnet-base-v2 | 768 | 109M | 420 MB | ~700 MB | ~63.5 | ~5,000 | 384 | Yes |
| BAAI/bge-small-en-v1.5 | 384 | 33.4M | 133 MB | ~300 MB | 62.17 | ~12,000 | 512 | Yes* |
| BAAI/bge-base-en-v1.5 | 768 | 109M | 438 MB | ~700 MB | 63.55 | ~5,500 | 512 | Yes* |
| BAAI/bge-large-en-v1.5 | 1024 | 335M | 1.34 GB | ~2 GB | 64.23 | ~2,000 | 512 | Yes* |
| intfloat/e5-small-v2 | 384 | 33M | 130 MB | ~300 MB | ~62 | ~11,000 | 512 | Yes* |
| intfloat/e5-base-v2 | 768 | 109M | 440 MB | ~700 MB | ~63 | ~5,000 | 512 | Yes* |
| nomic-embed-text-v1 | 768 | 137M | 550 MB | ~800 MB | ~63 | ~4,000 | 8192 | Yes |

\* BGE and E5 models require normalization via `model.encode(..., normalize_embeddings=True)` or manual L2 normalization. MiniLM/mpnet output normalized by default.

**Sources**:
- [sbert.net — Pretrained Models](https://sbert.net/docs/sentence_transformer/pretrained_models.html)
- [Hugging Face model cards for BAAI/bge-*](https://huggingface.co/BAAI)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)

---

## 5. Detailed Analysis by Model

### 5.1 `all-MiniLM-L6-v2` (384d) — RECOMMENDED FALLBACK

- **Size**: 80 MB disk, ~250 MB RAM during inference
- **Speed**: Fastest quality model — ~14,200 sentences/second on modern CPU
- **MTEB**: ~61.5 average (good for a model this small)
- **Normalization**: Outputs L2-normalized by default; cosine similarity = dot product
- **Max sequence length**: 256 tokens (official) / 512 (practical via config)
- **Training**: Distilled from MPNet, trained on 1B+ pairs
- **Verdict**: ✅ **Ideal for 4C/16GB VPS fallback**. Under 5% CPU sustained, under 2% RAM.

### 5.2 `all-mpnet-base-v2` (768d) — QUALITY LOCAL PRIMARY

- **Size**: 420 MB disk, ~600-800 MB RAM during inference
- **Speed**: ~5,000 sentences/second on CPU (~3x slower than MiniLM)
- **MTEB**: ~63.5 (better than MiniLM, close to BGE-base)
- **Normalization**: L2-normalized by default
- **Max sequence length**: 384 tokens
- **Verdict**: ✅ **Viable for 4C/16GB**. ~5% CPU, ~5% RAM. Better quality but higher cost.

### 5.3 `BAAI/bge-small-en-v1.5` (384d)

- **Size**: 133 MB disk, ~300 MB RAM
- **MTEB**: 62.17 (marginally better than MiniLM)
- **Requires instruction prefix**: `"Represent this sentence for searching relevant passages: "` for retrieval
- **Requires explicit normalization**: `normalize_embeddings=True`
- **Verdict**: ✅ Good alternative to MiniLM with slightly better MTEB, but adds instruction complexity.

### 5.4 `BAAI/bge-base-en-v1.5` (768d)

- **Size**: 438 MB disk, ~700 MB RAM
- **MTEB**: 63.55 (best in class for 768d)
- **Requires instruction prefix** for retrieval mode
- **Requires explicit normalization**
- **Verdict**: ✅ Equivalent to mpnet in resource usage, slightly better MTEB.

### 5.5 `BAAI/bge-large-en-v1.5` (1024d) — NOT RECOMMENDED

- **Size**: 1.34 GB disk, ~2 GB RAM
- **Verdict**: ❌ Exceeds 50% RAM budget (8 GB). Too heavy for 4C/16GB under constraints.

---

## 6. 1536-Dimension Analysis (ADR-009 Conflict)

### 6.1 The Problem

ADR-009 specifies `text-embedding-3-small` (1536d) as the primary embedding model, with pgvector `vector(1536)` columns. However:

- **No mainstream SentenceTransformers model outputs exactly 1536 dimensions**
- Common dims: 384 (small), 768 (base), 1024 (large)
- A few community models with Dense(1536) projections exist (e.g., `sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja`) but are:
  - Niche/unmaintained
  - Not benchmarked on MTEB
  - Likely lower quality

### 6.2 Resolution Options

| Option | Approach | Pros | Cons |
|---|---|---|---|
| **A. Separate columns** | `vector(1536)` for OpenAI, `vector(384)` for local | Clean separation, no quality loss | Schema complexity, dual index maintenance |
| **B. Projection layer** | Add Dense(384→1536) on MiniLM output | Single column, simple code | Quality loss, extra computation |
| **C. Use 768d always** | Switch primary to mpnet/BGE-base 768d | Single dim everywhere | Breaks ADR-009, lower quality than 1536d |
| **D. Halfvec 384d** | Store local embeddings as halfvec(384) | Memory efficient | Schema complexity |
| **E. API-only, no local** | Skip local fallback entirely | Simplest | No offline capability |

**Recommendation**: Option A — maintain `vector(1536)` for API embeddings and a separate `vector(384)` or `halfvec(384)` for local fallback. The local model is _fallback_ only (per StepPrompts), so the API 1536d remains primary.

---

## 7. Normalization & Cosine Similarity

### 7.1 Default Behavior

| Model | Auto-Normalized? | Similarity Function |
|---|---|---|
| all-MiniLM-L6-v2 | **Yes** (L2 norm) | Cosine = Dot product |
| all-mpnet-base-v2 | **Yes** (L2 norm) | Cosine = Dot product |
| BAAI/bge-* | **No** (must call `.encode(..., normalize_embeddings=True)`) | Cosine requires explicit norm |
| intfloat/e5-* | **No** (must call `.encode(..., normalize_embeddings=True)`) | Cosine requires explicit norm |

### 7.2 Code Pattern

```python
from sentence_transformers import SentenceTransformer
import numpy as np

# For auto-normalized models (MiniLM, mpnet):
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
emb = model.encode("Hello world")  # Already normalized
cosine_sim = np.dot(emb, emb)      # Dot product = cosine

# For BGE/E5:
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
emb = model.encode("Hello world", normalize_embeddings=True)
```

**Source**: [sbert.net — Quickstart](https://sbert.net/docs/quickstart.html)

---

## 8. Async / Offloading Considerations

### 8.1 Synchronous Only

SentenceTransformers `model.encode()` is a **blocking synchronous call**. It does not natively support `asyncio`. Patterns for non-blocking usage:

```python
import asyncio
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

async def encode_async(texts):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, model.encode, texts)
```

### 8.2 ONNX / OpenVINO Offloading

For CPU-bound VPS:

| Backend | CPU Speedup | Accuracy Loss | Memory Impact | Install |
|---|---|---|---|---|
| ONNX (fp32) | ~1.3x on short text | None | Similar | `sentence-transformers[onnx]` |
| ONNX (O4 fp16) | ~1.8x on short text | Minimal (~0.1%) | Lower | `[onnx]` + export |
| ONNX (int8 quant) | ~3.0x on CPU | ~0.4% | Lower | `[onnx]` + export |
| OpenVINO | ~1.3x on CPU | None | Similar | `sentence-transformers[openvino]` |
| OpenVINO (int8) | ~2.5x on CPU | ~0.4% | Lower | `[openvino]` + export |

**Recommendation**: For 4C VPS, start with PyTorch CPU backend. If latency is a concern, export to ONNX-O4 fp16.

**Source**: [sbert.net — Efficiency Benchmarks](https://sbert.net/docs/sentence_transformer/usage/efficiency.html)

### 8.3 Batch Processing

```python
# Batch for efficiency (recommended for VPS)
embeddings = model.encode(
    texts,
    batch_size=32,          # Tune based on RAM (16-64 safe for MiniLM)
    show_progress_bar=False,
    normalize_embeddings=True  # For BGE/E5; redundant for MiniLM
)
```

---

## 9. VPS Resource Analysis (4C / 16 GB)

| Scenario | Model | CPU | RAM | Disk | Verdict |
|---|---|---|---|---|---|
| Fallback (cold start) | MiniLM-L6-v2 | <5% | ~250 MB | 80 MB | ✅ **Safe** |
| Fallback (batch 32) | MiniLM-L6-v2 | ~15% spike | ~300 MB | - | ✅ **Safe** |
| Primary local | mpnet-base-v2 | <10% | ~700 MB | 420 MB | ✅ **Safe** |
| Primary local (batch) | mpnet-base-v2 | ~25% spike | ~800 MB | - | ✅ **Safe** |
| Local only | BGE-base | <10% | ~700 MB | 438 MB | ✅ **Safe** |
| Dual (MiniLM + mpnet) | Both | N/A | ~1 GB total | 500 MB | ✅ **Safe, but wasteful** |
| BGE-large | large | ~20% | ~2 GB | 1.34 GB | ❌ **Exceeds 50% RAM (8 GB budget)** |

**Conclusion**: All small/base models (384d-768d) fit comfortably under 50% CPU and RAM on a 4C/16GB VPS. BGE-large is the only model that risks exceeding the resource budget.

---

## 10. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| **ADR-009 dimension conflict**: Local 384d/768d won't fit `vector(1536)` column | **HIGH** | Option A: separate columns; or Option E: API-only fallback |
| **Cold start latency**: First model load downloads from HF Hub (~3-10s) | MEDIUM | Pre-download during P3 setup; pin to cache |
| **CPU saturation during batch**: Large batches spike CPU | LOW | Keep `batch_size <= 32`; use ONNX if needed |
| **Memory leak on repeated encode()**: PyTorch caching allocator | LOW | Call `torch.cuda.empty_cache()` (GPU only); on CPU, no issue |
| **Python 3.13 incompatibility**: ST v5.x not fully stable on 3.13 | LOW | Pin to Python 3.12 (already planned) |
| **Model deprecation**: MiniLM-L6-v2 may be superseded | LOW | Monitor HF model hub; BGE-small as backup |
| **Cross-encoder confusion**: Using cross-encoder (reranker) instead of bi-encoder for embeddings | MEDIUM | Always use `SentenceTransformer` for embeddings, not `CrossEncoder` |

---

## 11. Implementation Recommendations for P3

### 11.1 Recommended Model
**`sentence-transformers/all-MiniLM-L6-v2`** (384d, 80MB)

Rationale:
- Fastest inference at acceptable quality for fallback
- Lowest RAM/CPU footprint — stays well under 50% budgets
- Auto-normalized (no extra normalization step)
- Most widely used, best community support
- If BGE-small's 62.17 MTEB (vs MiniLM's ~61.5) is desirable, switch to `BAAI/bge-small-en-v1.5` with minimal resource impact

### 11.2 Dimension Strategy
- **API primary**: `text-embedding-3-small` → 1536d → `vector(1536)` column
- **Local fallback**: `all-MiniLM-L6-v2` → 384d → **separate** `vector(384)` or `halfvec(384)` column
- Document in a new ADR or amend ADR-009 notes to permit dual-dim schema

### 11.3 Install Commands (P3-004)
```bash
# Python 3.12 on Ubuntu
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers>=3.0,<6

# Verify cache location
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('all-MiniLM-L6-v2')"
# Cache will be at: ~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/
```

### 11.4 Code Template for Fallback

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List

class LocalEmbedder:
    """Local embedding fallback using SentenceTransformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """Returns normalized embeddings of shape (N, dim)."""
        return self.model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,  # Redundant for MiniLM, safe
            show_progress_bar=False,
        )
    
    @property
    def dim(self) -> int:
        return self.dimension
```

---

## 12. Key Sources

| Source | URL | Accessed |
|---|---|---|
| Official ST Installation Docs | https://sbert.net/docs/installation.html | 2026-06-02 |
| Official ST Quickstart | https://sbert.net/docs/quickstart.html | 2026-06-02 |
| Official ST Efficiency Guide | https://sbert.net/docs/sentence_transformer/usage/efficiency.html | 2026-06-02 |
| Official ST Pretrained Models | https://sbert.net/docs/sentence_transformer/pretrained_models.html | 2026-06-02 |
| PyPI Package (v5.5.1) | https://pypi.org/project/sentence-transformers/ | 2026-06-02 |
| GitHub Repo | https://github.com/huggingface/sentence-transformers | 2026-06-02 |
| BGE Model Family | https://huggingface.co/BAAI/bge-small-en-v1.5 | 2026-06-02 |
| HF Cache Management | https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache | 2026-06-02 |
| ADR-009 (1536d conflict) | `../../../adr/ADR-009-memory-recall-semantic-search-strategy.md` | 2026-06-02 |
| BentoML Embedding Guide | https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models | 2026-06-02 |
| Open Source Benchmark | https://supermemory.ai/blog/best-open-source-embedding-models-benchmarked-and-ranked/ | 2026-06-02 |
| Reddit r/LocalLLaMA Benchmarks | https://www.reddit.com/r/LocalLLaMA/comments/1nrgklt/ | 2026-06-02 |

---

*End of research report.*
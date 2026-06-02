# Research: OpenAI-Compatible Embedding API Patterns

**Date:** 2026-06-02
**Phase:** P3 (Memory)
**Context:** ADR-009 — Memory Recall & Semantic Search Strategy
**Binding Note:** OpenAI `text-embedding-3-small` (1536 dimensions) via 9Router/OpenRouter backend, no direct OpenAI unless future ADR supersedes.

---

## 1. OpenAI Python SDK Client Architecture

### 1.1 Dual Client Pattern

The `openai` Python SDK (v1.x+, requires Python 3.8+) provides two client classes:

| Client | Import | Usage |
|--------|--------|-------|
| `OpenAI` | `from openai import OpenAI` | Synchronous, blocking |
| `AsyncOpenAI` | `from openai import AsyncOpenAI` | Asynchronous, `await`-based |

Both share the same interface for `embeddings.create()`. The async variant is powered by `httpx.AsyncClient` under the hood.

**Source:** [openai/openai-python README — Async usage](https://github.com/openai/openai-python/blob/main/README.md#async-usage)

### 1.2 Embeddings Endpoint Signature

```python
# From openai-python v1.x, src/openai/resources/embeddings.py
async def create(
    self,
    *,
    input: Union[str, SequenceNotStr[str], Iterable[int], Iterable[Iterable[int]]],
    model: Union[str, EmbeddingModel],
    dimensions: int | Omit = omit,
    encoding_format: Literal["float", "base64"] | Omit = omit,
    user: str | Omit = omit,
    extra_headers: Headers | None = None,
    extra_query: Query | None = None,
    extra_body: Body | None = None,
    timeout: float | httpx.Timeout | None | NotGiven = not_given,
) -> CreateEmbeddingResponse:
```

**Source:** [openai-python embeddings.py — `AsyncEmbeddings.create()`](https://github.com/openai/openai-python/blob/5e8f09c2/src/openai/resources/embeddings.py#L79-L192)

**Key constraints:**
- Max 8191 tokens per input string
- Max 2048 inputs per request
- Max 300,000 tokens summed across all inputs in a single request
- Input cannot be an empty string

### 1.3 Default Encoding: base64

The SDK sends `encoding_format="base64"` by default and decodes to `list[float]` client-side. If NumPy is installed, it uses `np.frombuffer()` for faster decoding. This is transparent — `response.data[0].embedding` is always `list[float]`.

**Source:** [openai-python embeddings.py — base64 post-parser](https://github.com/openai/openai-python/blob/5e8f09c2/src/openai/resources/embeddings.py#L152-L170)

---

## 2. Base URL / Local Router Pattern

### 2.1 Standard Configuration

The SDK accepts `base_url` at construction time, which routes all requests to a custom endpoint instead of `https://api.openai.com/v1`:

```python
from openai import OpenAI, AsyncOpenAI

# Synchronous client
client = OpenAI(
    base_url="http://localhost:20128/v1",  # 9Router local endpoint
    api_key="<from-sops>",                 # Falls back to OPENAI_API_KEY env var
    max_retries=3,
    timeout=30.0,
)

# Asynchronous client
aclient = AsyncOpenAI(
    base_url="http://localhost:20128/v1",
    api_key="<from-sops>",
    max_retries=3,
    timeout=30.0,
)
```

**Source:** [openai-python README — Configuring the HTTP client](https://github.com/openai/openai-python/blob/main/README.md#configuring-the-http-client)

### 2.2 9Router Binding (ADR-009)

From ADR-009 (2026-05-30):

> **Embedding model:** Use OpenAI `text-embedding-3-small` with 1536 dimensions. Route through 9Router via OpenRouter backend, consistent with ADR-005. No direct OpenAI API calls unless a future ADR explicitly supersedes this routing policy.

From StepPrompts P3-005 (current project reference):

```python
client = OpenAI(base_url="http://localhost:20128/v1")  # Via 9Router
```

**Source:** [StepPrompts.md — P3-005 Embedding Pipeline](https://github.com/faiz/guinevere/blob/main/stepprompts/StepPrompts.md#L6145)

### 2.3 Environment Variable Pattern

The SDK also reads `OPENAI_BASE_URL` from the environment. Resolution order:
1. Explicit `base_url` kwarg
2. `OPENAI_API_BASE` (LangChain reads this)
3. `OPENAI_BASE_URL` (underlying `openai` SDK client reads this)

```bash
# .env or systemd EnvironmentFile
OPENAI_BASE_URL=http://localhost:20128/v1
OPENAI_API_KEY=sk-...
```

**Source:** [openai-python README — Configuring](https://github.com/openai/openai-python/blob/main/README.md#configuring-the-http-client)

### 2.4 No Direct Key Exposure

When routing through 9Router/OpenRouter:
- The 9Router API key is stored via SOPS+age (never in code or env without encryption)
- The client is initialized with `base_url` pointing to the local 9Router endpoint
- The 9Router handles upstream OpenAI key resolution
- Never expose the OpenAI upstream key in Guinevere application code

---

## 3. Async Patterns

### 3.1 Basic Async Usage

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://localhost:20128/v1",
    api_key="sk-...",
)

async def embed_single(text: str) -> list[float]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
```

**Source:** [Mintlify OpenAI docs — Async Usage](https://www.mintlify.com/openai/openai-python/api/embeddings/create)

### 3.2 Async Batch with asyncio.gather

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(base_url="http://localhost:20128/v1", api_key="...")

async def embed_many(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts via batch API (single request)."""
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=[t[:8000] for t in texts],
    )
    return [d.embedding for d in response.data]
```

### 3.3 Best Practice: Combined Sync+Async Client

```python
from openai import OpenAI, AsyncOpenAI

class EmbeddingClient:
    """Dual sync/async embedding client for 9Router-routed embeddings."""

    def __init__(self, base_url: str, api_key: str | None = None,
                 max_retries: int = 3, timeout: float = 30.0):
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )
        self.aclient = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )

    def embed(self, text: str) -> list[float]:
        """Synchronous single-text embedding."""
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],
        )
        return response.data[0].embedding

    async def aembed(self, text: str) -> list[float]:
        """Asynchronous single-text embedding."""
        response = await self.aclient.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding."""
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=[t[:8000] for t in texts],
        )
        return [d.embedding for d in response.data]

    async def aembed_batch(self, texts: list[str]) -> list[list[float]]:
        """Asynchronous batch embedding."""
        response = await self.aclient.embeddings.create(
            model="text-embedding-3-small",
            input=[t[:8000] for t in texts],
        )
        return [d.embedding for d in response.data]
```

**Pattern source:** [apache/hugegraph-ai — OpenAIEmbedding](https://github.com/apache/incubator-hugegraph-ai/blob/4dd6a164/hugegraph-llm/src/hugegraph_llm/models/embeddings/openai.py)

---

## 4. Retries, Backoff, and Timeout

### 4.1 SDK Built-in Retry

The `openai` SDK has **built-in retry** with exponential backoff:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | 2 | Max retry attempts (0 to disable) |
| Timeout | 10 minutes | Per-request timeout |
| Backoff strategy | Exponential + jitter | `min(0.5 * 2^n, 8.0) * jitter` (75-100% range) |

**Retried errors:** Connection errors, 408 (Request Timeout), 409 (Conflict), 429 (Rate Limit), ≥500 (Internal Server Error)

**Source:** [openai-python README — Retries](https://github.com/openai/openai-python/blob/main/README.md#retries)

### 4.2 Configuration

```python
from openai import OpenAI, AsyncOpenAI
import httpx

# Default: 2 retries, 10-minute timeout
client = OpenAI(
    base_url="http://localhost:20128/v1",
    max_retries=3,           # Override default (2)
    timeout=30.0,            # Per-request timeout in seconds
)

# Granular timeout via httpx.Timeout
client = OpenAI(
    timeout=httpx.Timeout(60.0, read=5.0, write=10.0, connect=2.0),
)

# Per-request override
client.with_options(max_retries=5, timeout=10.0).embeddings.create(
    model="text-embedding-3-small",
    input="test",
)
```

**Source:** [openai-python README — Timeouts](https://github.com/openai/openai-python/blob/main/README.md#timeouts)

### 4.3 Tenacity Decorator (Production Recommended)

The OpenAI Cookbook recommends `tenacity` for explicit retry logic with longer backoff:

```python
from tenacity import retry, stop_after_attempt, wait_random_exponential
from openai import OpenAI

client = OpenAI(base_url="http://localhost:20128/v1", api_key="...")

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(6),
    before_sleep=lambda retry_state: logger.info(
        "Embedding API retry", attempt=retry_state.attempt_number,
        wait=retry_state.next_action.sleep,
    ),
)
def get_embedding_with_retry(text: str) -> list[float]:
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-3-small",
    )
    return response.data[0].embedding
```

**Source:** [openai-cookbook — Using embeddings notebook](https://github.com/openai/openai-cookbook/blob/main/examples/Using_embeddings.ipynb)

### 4.4 Async Tenacity

```python
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
from openai import AsyncOpenAI, RateLimitError, APIStatusError

aclient = AsyncOpenAI(base_url="http://localhost:20128/v1", api_key="...")

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(6),
    retry=retry_if_exception_type((RateLimitError, APIStatusError)),
    before_sleep=lambda retry_state: logger.warning(
        "Async embedding retry", attempt=retry_state.attempt_number,
    ),
)
async def aget_embedding(text: str) -> list[float]:
    response = await aclient.embeddings.create(
        input=[text],
        model="text-embedding-3-small",
    )
    return response.data[0].embedding
```

### 4.5 Important: Timeout × Retries Interaction

Per-request `timeout` applies to **each individual attempt**. A request with `max_retries=2` and `timeout=30` could take up to `3 × 30 + backoff` seconds. Plan your total latency budget accordingly.

**Source:** [DeepWiki — openai-python error handling](https://deepwiki.com/openai/openai-python/3.4-error-handling-and-retry-logic)

---

## 5. Batching Strategy

### 5.1 API Limits Reference

| Limit | Value | Notes |
|-------|-------|-------|
| Max inputs per request | 2048 | Array length cap |
| Max tokens per input | 8191 | text-embedding-3-small |
| Max total tokens per request | 300,000 | Sum across all inputs |
| Default batch size (ADR-009) | 100 | OpenAI recommendation |
| Embedding dimension | 1536 | text-embedding-3-small |

**Source:** [Mintlify OpenAI — Create Embedding](https://www.mintlify.com/openai/openai-python/api/embeddings/create)

### 5.2 Token-Aware Batch Splitting

```python
import tiktoken

encoder = tiktoken.encoding_for_model("text-embedding-3-small")

def batch_inputs(texts: list[str], max_tokens: int = 8000, max_count: int = 100):
    """Split texts into token-aware batches for embedding API."""
    batch, batch_tokens = [], 0
    for text in texts:
        tokens = len(encoder.encode(text))
        if batch and (batch_tokens + tokens > max_tokens or len(batch) >= max_count):
            yield batch
            batch, batch_tokens = [], 0
        batch.append(text)
        batch_tokens += tokens
    if batch:
        yield batch

def embed_corpus(texts: list[str], model: str = "text-embedding-3-small",
                 dims: int = 1536) -> list[list[float]]:
    """Embed a large corpus with token-aware batching."""
    all_vectors: list[list[float]] = []
    for batch in batch_inputs(texts):
        response = client.embeddings.create(
            model=model, input=batch, dimensions=dims,
        )
        all_vectors.extend(item.embedding for item in response.data)
    return all_vectors
```

**Source:** [Respan — OpenAI Embeddings Engineer's Guide 2026](https://www.respan.ai/articles/openai-embeddings-guide)

### 5.3 Truncation Rule

Always truncate input text to 8000 characters (well under the 8191 token limit):

```python
def safe_input(text: str, max_chars: int = 8000) -> str:
    """Truncate input to safe length for embedding API."""
    return text[:max_chars]
```

**Source:** [StepPrompts.md — P3-005](https://github.com/faiz/guinevere/blob/main/stepprompts/StepPrompts.md#L6151)

---

## 6. Dimension Validation

### 6.1 Verification at Runtime

```python
EXPECTED_DIMS = 1536  # text-embedding-3-small

def validate_embedding(embedding: list[float]) -> None:
    """Validate embedding dimension matches expected value."""
    if len(embedding) != EXPECTED_DIMS:
        raise ValueError(
            f"Embedding dimension mismatch: expected {EXPECTED_DIMS}, "
            f"got {len(embedding)}. Check the model and router configuration."
        )

# Usage
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="test",
)
embedding = response.data[0].embedding
validate_embedding(embedding)  # Raises on mismatch
```

### 6.2 Production Dimension Check Pattern

```python
import structlog

logger = structlog.get_logger()

class DimensionMismatchError(ValueError):
    """Raised when embedding dimension does not match expected value."""
    pass

def verify_embedding_dimensions(
    embedding: list[float],
    expected: int = 1536,
    model_name: str = "text-embedding-3-small",
) -> None:
    """Verify embedding dimensions and log any mismatch."""
    actual = len(embedding)
    if actual != expected:
        logger.error(
            "embedding_dimension_mismatch",
            expected=expected,
            actual=actual,
            model=model_name,
        )
        raise DimensionMismatchError(
            f"Model '{model_name}' returned {actual}-dim embedding, "
            f"expected {expected}. pgvector column is locked to {expected}."
        )
    logger.debug("embedding_dimension_ok", dimensions=actual, model=model_name)
```

### 6.3 Why Dimension Validation Matters

From ADR-009:

> **Dimension lock:** pgvector enforces dimension at write time; changing models later requires table rebuild.

PostgreSQL pgvector columns are locked to a specific dimension (e.g., `vector(1536)`). Inserting a 3072-dim or 512-dim vector will fail at the database level. Validate before writing.

---

## 7. Local Embedding Fallback (Dimension-Mismatch Safe)

### 7.1 Fallback Architecture

When the 9Router/OpenRouter embedding endpoint is unavailable, fall back to a local embedding model that produces **the same 1536 dimensions**:

```python
from openai import OpenAI, AsyncOpenAI
import structlog

logger = structlog.get_logger()
EXPECTED_DIMS = 1536

class EmbeddingService:
    """Embedding service with remote-first + local fallback (1536-dim safe)."""

    def __init__(
        self,
        remote_base_url: str,
        api_key: str | None = None,
        local_fallback_model: str = "BAAI/bge-base-en-v1.5",  # 768-dim — needs adapter
    ):
        self.remote_client = OpenAI(
            base_url=remote_base_url,
            api_key=api_key,
            max_retries=3,
            timeout=30.0,
        )
        self._local_backend: "LocalEmbedder | None" = None
        self.local_fallback_model = local_fallback_model

    async def aembed(self, text: str) -> list[float]:
        """Async embed with automatic fallback on failure."""
        try:
            response = await self.aclient.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],
            )
            embedding = response.data[0].embedding
            self._validate_dims(embedding)
            return embedding
        except Exception as exc:
            logger.warning("remote_embedding_failed, falling back to local",
                           error=str(exc))
            return await self._local_embed(text)

    async def _local_embed(self, text: str) -> list[float]:
        """Fallback to local embedding, ensuring 1536-dim output."""
        if self._local_backend is None:
            self._local_backend = LocalEmbedder(model=self.local_fallback_model)
        embedding = await self._local_backend.embed(text)
        self._validate_dims(embedding)
        return embedding

    def _validate_dims(self, embedding: list[float]) -> None:
        if len(embedding) != EXPECTED_DIMS:
            raise DimensionMismatchError(
                f"Expected {EXPECTED_DIMS}-dim, got {len(embedding)}-dim. "
                "pgvector is locked to 1536. Cannot write mismatched embedding."
            )
```

### 7.2 Critical Fallback Rule

**The fallback model MUST output 1536 dimensions** to match the pgvector `vector(1536)` column. Common local models and their dimensions:

| Model | Dimensions | Compatible? |
|-------|-----------|-------------|
| `text-embedding-3-small` (OpenAI) | 1536 | ✅ Default |
| `text-embedding-3-large` (OpenAI) | 3072 | ❌ (use `dimensions=1536` via API param) |
| `BAAI/bge-small-en-v1.5` | 384 | ❌ |
| `BAAI/bge-base-en-v1.5` | 768 | ❌ |
| `BAAI/bge-large-en-v1.5` | 1024 | ❌ |
| `intfloat/multilingual-e5-small` | 384 | ❌ |
| `nomic-embed-text-v1.5` | 768 | ❌ |
| Local sentence-transformers with adapter | 1536 | ✅ If explicitly configured |

**If no local model matches 1536 dimensions**, either:
1. Configure `dimensions=1536` on models that support it (text-embedding-3-large)
2. Use a projection layer to map local embeddings to 1536 dimensions
3. Block writes to pgvector until the remote endpoint recovers (safest)

### 7.3 Dimension Adaptation (if needed)

```python
import numpy as np

def adapt_dimensions(embedding: list[float], target: int = 1536) -> list[float]:
    """Pad or truncate embedding to match target dimension.
    
    NOTE: This is a lossy operation. Prefer native 1536-dim models.
    Only use as emergency fallback when dimensions don't match.
    """
    current = len(embedding)
    if current == target:
        return embedding
    if current > target:
        # Truncate and re-normalize
        arr = np.array(embedding[:target])
        arr = arr / np.linalg.norm(arr)
        return arr.tolist()
    # Pad with zeros and re-normalize
    arr = np.pad(embedding, (0, target - current), mode='constant')
    arr = arr / np.linalg.norm(arr)
    return arr.tolist()
```

**Source:** [OpenAI embeddings guide — manual dimension change with L2 normalization](https://developers.openai.com/api/docs/guides/embeddings#changing-dimensions)

---

## 8. Safe Logging Practices

### 8.1 What to Log vs What NOT to Log

| Log | Don't Log |
|-----|-----------|
| Model name, dimensions, token count | Full embedding vectors (>6KB each) |
| Request duration, batch size | API keys, bearer tokens |
| HTTP status, error type | Raw request/response bodies |
| Truncated error message (first 200 chars) | User content (if privacy-sensitive) |
| Retry count, fallback triggered | Database connection strings |

### 8.2 Structured Logging with structlog

```python
import structlog
import time

logger = structlog.get_logger()

async def embed_safe(text: str, client: AsyncOpenAI) -> list[float]:
    """Embed with safe structured logging."""
    start = time.monotonic()
    try:
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],
        )
        embedding = response.data[0].embedding
        duration = time.monotonic() - start

        logger.info(
            "embedding_success",
            model="text-embedding-3-small",
            dimensions=len(embedding),
            duration_ms=round(duration * 1000),
            input_length=len(text),
            total_tokens=response.usage.total_tokens if hasattr(response, 'usage') else None,
        )
        return embedding
    except Exception as exc:
        duration = time.monotonic() - start
        logger.error(
            "embedding_failed",
            model="text-embedding-3-small",
            duration_ms=round(duration * 1000),
            error_type=type(exc).__name__,
            error_msg=str(exc)[:200],  # Truncated
        )
        raise

# NEVER log this:
# logger.info("embedding_vector", vector=embedding)  # ❌ 1536 floats
# logger.info("api_key", key=client.api_key)          # ❌ credential leak
```

### 8.3 API Key Redaction

```python
import re

def redact_api_key(key: str | None) -> str:
    """Redact API key for safe logging, showing only first 4 chars."""
    if key is None:
        return "<none>"
    return f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "<short-key>"

# Usage in structured log
logger.info("embedding_client_init", api_key_redacted=redact_api_key(api_key))
```

---

## 9. Production Embedding Pipeline (Complete Pattern)

### 9.1 Full Implementation

```python
"""Production embedding pipeline for Guinevere memory system.

ADR-009 Binding:
- Model: text-embedding-3-small
- Dimensions: 1536
- Router: 9Router via OpenRouter backend at localhost:20128/v1
- No direct OpenAI API calls unless a future ADR supersedes this.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from openai import AsyncOpenAI, OpenAI, RateLimitError, APIStatusError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

logger = structlog.get_logger()

EXPECTED_EMBEDDING_DIMS: int = 1536
EMBEDDING_MODEL: str = "text-embedding-3-small"
MAX_INPUT_CHARS: int = 8000
DEFAULT_BATCH_SIZE: int = 100  # ADR-009 recommendation
DEFAULT_TIMEOUT: float = 30.0
DEFAULT_MAX_RETRIES: int = 3


class DimensionMismatchError(ValueError):
    """Embedding dimension does not match expected value."""
    pass


class EmbeddingPipeline:
    """Embedding pipeline with async support, retry, dimension validation, and safe logging."""

    def __init__(
        self,
        base_url: str = "http://localhost:20128/v1",
        api_key: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )
        self.aclient = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout,
        )
        logger.info(
            "embedding_pipeline_init",
            model=EMBEDDING_MODEL,
            expected_dims=EXPECTED_EMBEDDING_DIMS,
            base_url=base_url,
        )

    # --- Single Embedding ---

    def embed(self, text: str) -> list[float]:
        """Generate 1536-dim embedding for a single text (sync)."""
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text[:MAX_INPUT_CHARS],
        )
        embedding = response.data[0].embedding
        self._validate(embedding)
        return embedding

    async def aembed(self, text: str) -> list[float]:
        """Generate 1536-dim embedding for a single text (async)."""
        response = await self.aclient.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text[:MAX_INPUT_CHARS],
        )
        embedding = response.data[0].embedding
        self._validate(embedding)
        return embedding

    # --- Batch Embedding ---

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (sync, single request)."""
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[t[:MAX_INPUT_CHARS] for t in texts],
        )
        embeddings = [d.embedding for d in response.data]
        for emb in embeddings:
            self._validate(emb)
        return embeddings

    async def aembed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (async, single request)."""
        response = await self.aclient.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[t[:MAX_INPUT_CHARS] for t in texts],
        )
        embeddings = [d.embedding for d in response.data]
        for emb in embeddings:
            self._validate(emb)
        return embeddings

    # --- Retry Wrapper (tenacity) ---

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception_type((RateLimitError, APIStatusError)),
        before_sleep=lambda rs: logger.warning(
            "embedding_retry",
            attempt=rs.attempt_number,
            wait_seconds=rs.next_action.sleep if rs.next_action else None,
        ),
    )
    def embed_with_backoff(self, text: str) -> list[float]:
        """Single embedding with explicit tenacity retry."""
        return self.embed(text)

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception_type((RateLimitError, APIStatusError)),
        before_sleep=lambda rs: logger.warning(
            "embedding_retry_async",
            attempt=rs.attempt_number,
        ),
    )
    async def aembed_with_backoff(self, text: str) -> list[float]:
        """Single embedding with explicit tenacity retry (async)."""
        return await self.aembed(text)

    # --- Validation ---

    def _validate(self, embedding: list[float]) -> None:
        """Ensure embedding dimension matches pgvector column."""
        actual = len(embedding)
        if actual != EXPECTED_EMBEDDING_DIMS:
            logger.error(
                "embedding_dimension_mismatch",
                expected=EXPECTED_EMBEDDING_DIMS,
                actual=actual,
                model=EMBEDDING_MODEL,
            )
            raise DimensionMismatchError(
                f"Expected {EXPECTED_EMBEDDING_DIMS}-dim embedding, got {actual}. "
                "pgvector column is vector(1536) — cannot write mismatched data."
            )
```

### 9.2 Usage

```python
# Initialize
pipe = EmbeddingPipeline(
    base_url="http://localhost:20128/v1",
    api_key=load_from_sops("nine_router_api_key"),
)

# Sync single
vec = pipe.embed("Hello world")                   # list[float], len=1536

# Async single
vec = await pipe.aembed("Hello world")             # list[float], len=1536

# Sync batch
vecs = pipe.embed_batch(["Hello", "World"])        # list[list[float]]

# Async with tenacity retry
vec = await pipe.aembed_with_backoff("Hello")      # 6 retries, exponential backoff
```

---

## 10. Source References

| Source | URL |
|--------|-----|
| OpenAI Embeddings API Guide | https://developers.openai.com/api/docs/guides/embeddings |
| OpenAI Python SDK README | https://github.com/openai/openai-python/blob/main/README.md |
| openai-python embeddings.py (source) | https://github.com/openai/openai-python/blob/5e8f09c2/src/openai/resources/embeddings.py |
| openai-python _client.py (source) | https://github.com/openai/openai-python/blob/main/src/openai/_client.py |
| openai-python _base_client.py (retry logic) | https://github.com/openai/openai-python/blob/722d3fff/src/openai/_base_client.py |
| OpenAI Cookbook — Using embeddings | https://github.com/openai/openai-cookbook/blob/main/examples/Using_embeddings.ipynb |
| OpenAI Cookbook — embeddings_utils.py | https://github.com/openai/openai-cookbook/blob/a46b4185/examples/utils/embeddings_utils.py |
| Apache HugeGraph AI — OpenAIEmbedding | https://github.com/apache/incubator-hugegraph-ai/blob/4dd6a164/hugegraph-llm/src/hugegraph_llm/models/embeddings/openai.py |
| LangChain OpenAIEmbeddings docs | https://reference.langchain.com/python/langchain-openai/embeddings/base/OpenAIEmbeddings |
| LocalEmbed — OpenAI-compatible local server | https://github.com/heshinth/LocalEmbed |
| Respan — Embeddings Engineer's Guide (2026) | https://www.respan.ai/articles/openai-embeddings-guide |
| Local AI Master — Local vs OpenAI Embeddings (2026) | https://localaimaster.com/blog/local-vs-openai-embeddings |
| OpenAI Rate Limit Handling Guide | https://developers.openai.com/cookbook/examples/how_to_handle_rate_limits |
| DeepWiki — openai-python error handling | https://deepwiki.com/openai/openai-python/3.4-error-handling-and-retry-logic |
| vLLM — OpenAI-compatible server embeddings | https://docs.vllm.ai/en/v0.8.3/serving/openai_compatible_server.html |
| ADR-009 — Memory Recall & Semantic Search Strategy | `adr/ADR-009-memory-recall-semantic-search-strategy.md` |
| StepPrompts P3-005 — Embedding Pipeline | `stepprompts/StepPrompts.md` (lines 6137-6164) |

---

## 11. Binding Decisions Summary

| Decision | Value | Source |
|----------|-------|--------|
| Embedding model | `text-embedding-3-small` | ADR-009 |
| Dimensions | 1536 | ADR-009 |
| Router path | 9Router via OpenRouter backend | ADR-009 + ADR-005 |
| Base URL | `http://localhost:20128/v1` | StepPrompts P3-005 |
| Direct OpenAI calls | ❌ Prohibited unless future ADR supersedes | ADR-009 |
| pgvector dimension lock | `vector(1536)` — cannot change without table rebuild | ADR-009 |
| Batch limit | 100 per call (recommended) | ADR-009 |
| Retry strategy | SDK default (2 retries) + tenacity (6 retries) recommended | ADR-009 + cookbook |
| Local fallback | Must output 1536 dimensions to match pgvector | ADR-009 constraint |
| API key origin | SOPS + age encrypted secrets | ADR-015 |
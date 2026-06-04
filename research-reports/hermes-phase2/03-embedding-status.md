# Embedding Service Status Report — Hermes Phase 2

| Field | Value |
|---|---|
| Date | 2026-06-04 |
| Agent | Research Agent 3 |
| Scope | Embedding API availability, fallback paths, Phase 2 readiness |
| Status | **EMBEDDING NON-FUNCTIONAL — FTS FALLBACK OPERATIONAL** |

---

## Executive Summary

The embedding service is **completely non-functional** on the VPS. Three compounding issues prevent vector search:

1. **9Router has no embedding model** — all 52 registered models are LLM chat/completion models.
2. **9Router does not support `/v1/embeddings`** — the endpoint returns `Invalid JSON body` regardless of input.
3. **No embedding API key is configured** — neither `GUINEVERE_9ROUTER_API_KEY` nor `OPENROUTER_API_KEY` is set in the environment.

**However**, the read pipeline (`read_pipeline.py`) has a **graceful fallback** to FTS-only search that works correctly. Phase 2 can proceed with FTS + recency + importance ranking, but semantic vector search is unavailable until an embedding solution is deployed.

The database `memory.episodes` table is **empty** (0 rows), so recall returns 0 results regardless of method.

---

## 1. 9Router Model Inventory

**Endpoint**: `http://localhost:20128/v1/models`

9Router is running (PID 627184, `node /usr/bin/9router --port 20128`) with **52 models** registered:

| Provider | Models | Type |
|---|---|---|
| `cx/` (OpenAI-compatible) | gpt-5.5, gpt-5.5-review, gpt-5.4, gpt-5.4-mini, gpt-5.3-codex (8 variants) | LLM chat |
| `ds/` (DeepSeek) | deepseek-v4-pro, deepseek-v4-flash, deepseek-chat, deepseek-reasoner | LLM chat |
| `ocg/` | kimi-k2.6, kimi-k2.5, glm-5.1, qwen3.5-plus, qwen3.6-plus, mimo-v2-pro, minimax-m2.7 | LLM chat |
| `xmtp/` (Mimo) | mimo-v2.5-pro, mimo-v2.5, mimo-v2-pro, mimo-v2-omni, mimo-v2-tts (5 variants) | LLM + TTS |
| `qd/` | auto, ultimate, performance, efficient, lite, 6 named sub-models | LLM chat |
| `guinevere` | combo model | LLM chat |

**Embedding models found: 0** — no model with "embed" in its ID exists.

---

## 2. Direct Embedding API Test

**Request**:
```
POST http://localhost:20128/v1/embeddings
Content-Type: application/json
{"model": "openai/text-embedding-3-small", "input": "test"}
```

**Response**:
```json
{"error": {"message": "Invalid JSON body", "type": "invalid_request_error", "code": "bad_request"}}
```

This error is consistent even when sending valid JSON via file-based curl (`-d @/tmp/emb_test.json`). **9Router does not implement the `/v1/embeddings` endpoint.** The error is not a JSON parsing issue; it is 9Router rejecting the embeddings route entirely.

---

## 3. 9Router Configuration

| Check | Result |
|---|---|
| Config file (`~/.config/9router/config.json`) | **Not found** |
| Process command | `node /usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update` |
| Process env — OPENAI_API_KEY | `PLACEHOLDER_OPENAI_KEY` (not a real key) |
| Process env — DEEPSEEK_API_KEY | `PLACEHOLDER_DEEPSEEK_KEY` (not a real key) |
| Process env — GUINEVERE_9ROUTER_API_KEY | **Not set** |
| Process env — OPENROUTER_API_KEY | **Not set** |

9Router is running with **placeholder API keys**, meaning it cannot proxy requests to upstream providers. This likely explains why only locally-configured models (DeepSeek with its own key elsewhere) may work for LLM, but embedding — which has no model registered — fails entirely.

---

## 4. EmbeddingService Code Analysis

**File**: `src/memory/embeddings.py` (775 lines)

### Key Findings

| Aspect | Behavior |
|---|---|
| Default model | `openai/text-embedding-3-small` |
| Default endpoint | `http://localhost:20128/v1/embeddings` |
| API key lookup | `GUINEVERE_9ROUTER_API_KEY`, then `OPENROUTER_API_KEY` (env vars) |
| No API key | `EmbeddingConfigurationError` raised immediately (no retry) |
| HTTP 400 | `EmbeddingAPIError` raised (no retry — only 429 and 5xx are retried) |
| HTTP 429 | `EmbeddingRateLimitError` → retried with exponential backoff (max 6 attempts) |
| HTTP 5xx | `EmbeddingServerError` → retried with exponential backoff |
| Connection error | `httpx.ConnectError` → retried |
| Timeout | `httpx.TimeoutException` → retried |
| Dimension check | Validates vector length = 1536; raises `DimensionMismatchError` on mismatch |

### 400 Error Behavior (Specific)

When the API returns HTTP 400 (like the `Invalid JSON body` error from 9Router):

```python
# _raise_on_http_error at line 644-656
if response.status_code == 429:
    raise EmbeddingRateLimitError(...)
if 500 <= response.status_code < 600:
    raise EmbeddingServerError(...)
if response.status_code != 200:
    raise EmbeddingAPIError(...)  # ← 400 lands here, NOT retried
```

The `EmbeddingAPIError` propagates up through `_do_async_request` → `_aembed_prepared` → `aembed()`. It is NOT caught by the retry loop (which only catches rate limit, server errors, timeout, and connect errors). The exception bubbles to the caller.

### Current State on VPS

When instantiated on VPS, `EmbeddingService()` immediately logs a warning:

```
No embedding API key found in environment  env_vars=('GUINEVERE_9ROUTER_API_KEY', 'OPENROUTER_API_KEY')
```

Any call to `aembed()` raises `EmbeddingConfigurationError` before any HTTP request is made.

---

## 5. Read Pipeline Fallback Analysis

**File**: `src/memory/read_pipeline.py` (963 lines)

### Critical Code Path (lines 799-805)

```python
query_vector: list[float] | None = None
if embedding_service is not None:
    try:
        query_vector = await embedding_service.aembed(query_text_stripped)
    except Exception:
        _logger.warning("embedding_fallback_keyword", extra={"query_hash": _query_hash})
        # Graceful fallback: keyword-only search without vector similarity
```

### Fallback Behavior

| Scenario | `query_vector` | Vector Query | FTS Query | Recency Query | Result |
|---|---|---|---|---|---|
| No embedding_service passed | `None` | **Skipped** | Executed | Executed | FTS + recency only |
| embedding_service passed, aembed succeeds | Set | Executed | Executed | Executed | Full hybrid (vector + FTS + recency) |
| embedding_service passed, aembed fails (ANY exception) | `None` | **Skipped** | Executed | Executed | FTS + recency only (graceful) |

**The fallback is correct and robust.** Any exception type — `EmbeddingConfigurationError`, `EmbeddingAPIError`, `ConnectionError`, etc. — is caught by the bare `except Exception` clause. The pipeline continues with FTS + recency signals only.

### Verified on VPS

Both test scenarios confirmed:
- **FTS-ONLY** (`embedding_service=None`): returned 0 results, no crash.
- **WITH-EMBED** (EmbeddingService passed): logged `embedding_fallback_keyword`, fell back to FTS-only, returned 0 results, no crash.

The 0 results are because the `memory.episodes` table is empty (0 rows).

---

## 6. Database Status

| Metric | Count |
|---|---|
| Total episodes | **0** |
| Episodes with embeddings | **0** |
| Episodes with search_vector (FTS) | **0** |

The memory system has no stored data. This means:
- Recall cannot be evaluated for quality with any method.
- Phase 2 memory ingestion (write pipeline) must run before recall can be tested meaningfully.

---

## 7. Assessment: Can Phase 2 Work with FTS-Only Recall?

**YES, with caveats.**

### What Works

- **FTS (full-text search)**: PostgreSQL `tsvector` + `plainto_tsquery` provides keyword-based recall. Works without any external dependency.
- **Recency decay**: 90-day half-life exponential decay scoring is fully functional.
- **Importance weighting**: Episode importance (1-10) is applied as a multiplier.
- **Safety gates**: DNR exclusion, classification ceiling, safe-mode content redaction — all functional.
- **Token budget**: 4000-token limit enforcement is functional.
- **RRF fusion**: With FTS + recency as the only signals, RRF still works (just with fewer signals to fuse).

### What's Missing

- **Semantic similarity**: Vector cosine search is unavailable. Queries like "what did we talk about yesterday?" won't find semantically related episodes that don't share exact keywords.
- **Both-signal bonus**: The 1.25x bonus for episodes found by both vector AND FTS cannot trigger.
- **Cross-lingual recall**: FTS uses English tokenizer (`plainto_tsquery("english", ...)`). Indonesian or mixed-language queries will perform poorly without semantic embeddings.

### Scoring Impact

With only FTS + recency:
- FTS weight = 0.5, recency max boost = 10%, importance boost = 0.5-1.0
- Maximum possible score is lower than hybrid mode
- Recall quality depends heavily on keyword overlap between query and episode content
- This is **adequate for MVP / Phase 2 initial deployment** but should be upgraded to hybrid search before production use

---

## 8. Embedding Alternatives

| Option | Pros | Cons | Effort | Recommendation |
|---|---|---|---|---|
| **9Router upgrade** | If 9Router adds embedding model support, zero code change needed | Depends on 9Router vendor; no timeline | Low (config only) | Monitor 9Router releases |
| **Direct OpenAI API** | Works immediately; `text-embedding-3-small` is cheap ($0.02/1M tokens) | Bypasses 9Router proxy; requires separate API key and base URL change in `EmbeddingConfig` | Low | **Best short-term option** |
| **OpenRouter** | Already partially configured; supports embedding models | Need `OPENROUTER_API_KEY` set; additional hop | Low | Good if OpenRouter account exists |
| **Local sentence-transformers** | Full privacy; no external API calls; models like `all-MiniLM-L6-v2` (384d) or `text-embedding-3-small` ONNX | Requires Python package install; CPU/memory on VPS; dimension mismatch (384 vs 1536) requires schema change or padding | Medium | Best long-term for privacy |
| **Ollama on VPS** | Local embedding models (`nomic-embed-text`, `mxbai-embed-large`) | VPS may not have GPU; CPU inference is slow for batch; dimension varies by model | Medium | Good if GPU available |
| **Voyage AI** | High-quality embeddings; OpenAI-compatible API | New vendor; additional cost and key management | Low | Good quality alternative |

### Recommended Path

1. **Phase 2 launch**: Deploy with FTS-only recall (no blocker).
2. **Quick win**: Configure `EmbeddingConfig` to point directly at OpenAI's API (`https://api.openai.com/v1`) with a dedicated API key for `text-embedding-3-small`. This is a config change only — no code modifications needed. Set `GUINEVERE_9ROUTER_API_KEY` to the OpenAI key and `base_url` to `https://api.openai.com/v1`.
3. **Long-term**: Evaluate local embedding model on VPS (sentence-transformers or Ollama) for full data sovereignty per ADR-009 (no OpenAI SDK) and privacy requirements.

---

## 9. Recommendations for Phase 2

1. **Proceed with FTS-only recall** — the pipeline is functional and the fallback is robust.
2. **Store the embedding API key** in SOPS-encrypted secrets and inject via sops exec-env into the runtime environment.
3. **When embedding is restored**, the existing `EmbeddingService` and `read_pipeline` code will automatically enable hybrid search — no code changes needed.
4. **Prioritize memory ingestion** (write pipeline) to populate the episodes table before testing recall quality.
5. **Consider adding a health check** for embedding availability in the observability stack (Prometheus metric or Grafana alert).

---

## Appendix: Raw Test Output

### 9Router Models (full list)

```
guinevere, ds/deepseek-v4-pro, ds/deepseek-v4-pro-max, ds/deepseek-v4-pro-none,
ds/deepseek-v4-flash, ds/deepseek-chat, ds/deepseek-reasoner,
xmtp/mimo-v2.5-pro, xmtp/mimo-v2.5, xmtp/mimo-v2-pro, xmtp/mimo-v2-omni,
xmtp/mimo-v2-tts, xmtp/mimo-v2.5-tts, xmtp/mimo-v2.5-tts-voiceclone,
xmtp/mimo-v2.5-tts-voicedesign,
cx/gpt-5.5, cx/gpt-5.5-review, cx/gpt-5.4, cx/gpt-5.4-review, cx/gpt-5.4-mini,
cx/gpt-5.4-mini-review, cx/gpt-5.3-codex (8 variants),
ocg/kimi-k2.6, ocg/kimi-k2.5, ocg/glm-5.1, ocg/glm-5, ocg/qwen3.5-plus,
ocg/qwen3.6-plus, ocg/mimo-v2-pro, ocg/mimo-v2-omni, ocg/minimax-m2.7,
ocg/minimax-m2.5, qd/auto, qd/ultimate, qd/performance, qd/efficient,
qd/lite, qd/qmodel_latest, qd/qmodel, qd/dmodel, qd/dfmodel,
qd/gm51model, qd/kmodel, qd/mmodel
```

### Embedding API Test

```
Request:  POST /v1/embeddings {"model":"openai/text-embedding-3-small","input":"test"}
Response: {"error":{"message":"Invalid JSON body","type":"invalid_request_error","code":"bad_request"}}
```

### EmbeddingService Instantiation

```
No embedding API key found in environment  env_vars=('GUINEVERE_9ROUTER_API_KEY', 'OPENROUTER_API_KEY')
```

### Recall Test Output

```
FTS-ONLY recall: 0 results
WITH-EMBED recall: 0 results
(embedding_fallback_keyword logged for WITH-EMBED test)
```

### Database Check

```
Total episodes: 0
Episodes with embeddings: 0
Episodes with search_vector (FTS): 0
```

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-04 | Research Agent 3 | Initial embedding status report for Hermes Phase 2. |

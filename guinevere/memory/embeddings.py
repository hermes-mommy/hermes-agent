"""Embedding pipeline for Guinevere memory system — P3-005.

Uses 9Router-native HTTP client (httpx) for text-embedding-3-small via
OpenRouter-compatible path. No direct OpenAI SDK usage per ADR-009.

Logging uses stdlib ``logging`` with a small structured wrapper for LSP-clean
diagnostics. Retry uses a manual exponential-backoff loop instead of tenacity
to avoid import-resolution warnings in environments where tenacity is not
installed. Both structlog and tenacity remain declared in ``pyproject.toml``
for production deployment (other modules may still use them).

Privacy guards:
- Critical classification: raw text rejected, fails closed with CriticalEmbeddingError
  unless caller provides explicit sanitized_summary via prepare_embedding_text()
- Restricted classification: deterministic redaction of sensitive patterns before send
- Logs only metadata: model, dimensions, classification, redaction_applied, duration/error
- Never logs raw text, vector values, or secrets
"""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeAlias

import httpx

# ---------------------------------------------------------------------------
# Structured logger (stdlib-based, structlog-compatible surface)
# ---------------------------------------------------------------------------


class _Logger:
    """Thin structured logger wrapping stdlib logging.

    Provides ``info``, ``warning``, and ``bind`` methods compatible with a
    subset of structlog's interface.  All log calls emit through stdlib
    ``logging.getLogger(name)`` so production deployments using structlog
    elsewhere are unaffected.
    """

    def __init__(self, name: str, **bound_fields: object) -> None:
        self._impl: logging.Logger = logging.getLogger(name)
        self._fields: dict[str, object] = dict(bound_fields)

    def bind(self, **kwargs: object) -> _Logger:
        """Return a new _Logger with additional bound fields."""
        merged: dict[str, object] = dict(self._fields)
        merged.update(kwargs)
        new = _Logger.__new__(_Logger)
        new._impl = self._impl
        new._fields = merged
        return new

    def info(self, msg: str, **kwargs: object) -> None:
        """Log at INFO level."""
        self._log(logging.INFO, msg, kwargs)

    def warning(self, msg: str, **kwargs: object) -> None:
        """Log at WARNING level."""
        self._log(logging.WARNING, msg, kwargs)

    def _log(self, level: int, msg: str, extra: dict[str, object]) -> None:
        ctx: dict[str, object] = dict(self._fields)
        ctx.update(extra)
        if ctx:
            pairs = " ".join(f"{k}={v}" for k, v in ctx.items())
            self._impl.log(level, "%s  %s", msg, pairs)
        else:
            self._impl.log(level, "%s", msg)


_logger = _Logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:20128/v1"
DEFAULT_MODEL = "openai/text-embedding-3-small"
EXPECTED_DIMENSION = 1536
MAX_INPUT_CHARS = 8000
DEFAULT_TIMEOUT_S = 60.0
MAX_RETRIES = 6

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Vector: TypeAlias = list[float]
EmbeddingBatch: TypeAlias = list[Vector]

# ---------------------------------------------------------------------------
# Classification hierarchy (ascending sensitivity)
# ---------------------------------------------------------------------------

PUBLIC = "Public"
INTERNAL = "Internal"
RESTRICTED = "Restricted"
CONFIDENTIAL = "Confidential"
CRITICAL = "Critical"

CLASSIFICATION_ORDER: dict[str, int] = {
    PUBLIC: 0,
    INTERNAL: 1,
    RESTRICTED: 2,
    CONFIDENTIAL: 3,
    CRITICAL: 4,
}

SAFE_FOR_EXTERNAL: set[str] = {PUBLIC, INTERNAL, RESTRICTED, CONFIDENTIAL}


# ---------------------------------------------------------------------------
# Custom Errors
# ---------------------------------------------------------------------------


class EmbeddingError(Exception):
    """Base error for embedding pipeline."""


class CriticalEmbeddingError(EmbeddingError):
    """Raised when raw Critical text is passed without explicit sanitization."""


class RestrictedRedactionError(EmbeddingError):
    """Raised when Restricted text cannot be safely redacted."""


class DimensionMismatchError(EmbeddingError):
    """Raised when embedding API returns unexpected vector dimension."""


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when embedding service is misconfigured (e.g., missing API key)."""


class EmbeddingAPIError(EmbeddingError):
    """Raised on non-retryable API errors (auth, bad request, etc.)."""


class EmbeddingRateLimitError(EmbeddingError):
    """Raised on HTTP 429 — will be retried."""


class EmbeddingServerError(EmbeddingError):
    """Raised on HTTP 5xx — will be retried."""


# ---------------------------------------------------------------------------
# Sensitive-pattern redaction (for Restricted / Confidential classification)
# ---------------------------------------------------------------------------

_REDACTION_PATTERNS: list[tuple[str, str]] = [
    (r"\b(sk-)[a-zA-Z0-9_-]{20,}\b", r"\1...<redacted>"),
    (r"\b(sk-proj-)[a-zA-Z0-9_-]{20,}\b", r"\1...<redacted>"),
    (r"\b(Bearer\s+)[a-zA-Z0-9._-]{20,}", r"\1<redacted>"),
    (r"\b[\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}\b", "<email-redacted>"),
    (
        r"\b\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{3,10}\b",
        "<phone-redacted>",
    ),
    (
        r"(https?://[^\s]+)(?:api[_-]?key|token|secret|password|auth)=[^\s&]+",
        r"\1<credential-redacted>",
    ),
    (r"\b[a-fA-F0-9]{40,}\b", "<hash-redacted>"),
]


def _redact_sensitive(text: str) -> tuple[str, bool]:
    """Apply deterministic redaction of sensitive patterns.

    Returns ``(redacted_text, redaction_applied)``.
    """
    redacted = text
    applied = False
    for pattern, replacement in _REDACTION_PATTERNS:
        new_text, count = re.subn(pattern, replacement, redacted)
        if count > 0:
            applied = True
            redacted = new_text
    return redacted, applied


# ---------------------------------------------------------------------------
# Privacy preprocessing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreparedText:
    """Result of privacy preprocessing on input text."""

    text: str
    classification: str
    redaction_applied: bool
    is_sanitized_summary: bool = False


def prepare_embedding_text(
    text: str,
    classification: str = RESTRICTED,
    *,
    sanitized_summary: str | None = None,
) -> PreparedText:
    """Prepare text for external embedding with privacy guards.

    Parameters
    ----------
    text:
        Raw memory text to embed.
    classification:
        Data classification level (Public, Internal, Restricted, Confidential, Critical).
    sanitized_summary:
        Optional pre-sanitized summary to use instead of raw text for Critical
        classification. Must be provided if classification is Critical.

    Returns
    -------
    PreparedText with processed text and metadata.

    Raises
    ------
    CriticalEmbeddingError
        If classification is Critical and no sanitized_summary is provided.
    ValueError
        If classification is unknown.
    """
    _validate_classification(classification)

    if classification == CRITICAL:
        if sanitized_summary is not None and sanitized_summary.strip():
            return PreparedText(
                text=_truncate_text(sanitized_summary.strip()),
                classification=CRITICAL,
                redaction_applied=False,
                is_sanitized_summary=True,
            )
        raise CriticalEmbeddingError(
            "Cannot send raw " + CRITICAL + " text externally. "
            + "Provide a sanitized_summary or skip embedding."
        )

    if classification not in SAFE_FOR_EXTERNAL:
        raise ValueError(
            "Unknown classification: " + classification + ". "
            + "Expected one of " + str(sorted(CLASSIFICATION_ORDER.keys()))
        )

    processed = _truncate_text(text)

    if classification in (CONFIDENTIAL, RESTRICTED):
        processed, redaction_applied = _redact_sensitive(processed)
    else:
        redaction_applied = False

    return PreparedText(
        text=processed,
        classification=classification,
        redaction_applied=redaction_applied,
        is_sanitized_summary=False,
    )


def _truncate_text(text: str) -> str:
    """Truncate text to MAX_INPUT_CHARS."""
    if len(text) > MAX_INPUT_CHARS:
        return text[:MAX_INPUT_CHARS]
    return text


def _validate_classification(classification: str) -> None:
    """Validate classification is known."""
    if classification not in CLASSIFICATION_ORDER:
        raise ValueError(
            "Unknown classification: " + classification + ". "
            + "Expected one of " + str(sorted(CLASSIFICATION_ORDER.keys()))
        )


# ---------------------------------------------------------------------------
# Embedding config
# ---------------------------------------------------------------------------


@dataclass
class EmbeddingConfig:
    """Configuration for the embedding service.

    The API key is loaded from environment at runtime and is never
    serialised or logged.
    """

    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    expected_dimension: int = EXPECTED_DIMENSION
    max_input_chars: int = MAX_INPUT_CHARS
    timeout_seconds: float = DEFAULT_TIMEOUT_S
    max_retries: int = MAX_RETRIES

    # Environment variable names, tried in order
    api_key_env_vars: tuple[str, ...] = (
        "GUINEVERE_9ROUTER_API_KEY",
        "OPENROUTER_API_KEY",
    )

    # Stored at runtime, never logged
    _api_key: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        """Load API key from environment on construction."""
        for var in self.api_key_env_vars:
            value = os.environ.get(var)
            if value:
                object.__setattr__(self, "_api_key", value)
                return
        _logger.warning("No embedding API key found in environment", env_vars=self.api_key_env_vars)

    @property
    def api_key(self) -> str:
        """Return the loaded API key. Empty string if none found."""
        return self._api_key

    @property
    def embed_url(self) -> str:
        """Full URL for the embeddings endpoint."""
        base = self.base_url.rstrip("/")
        return f"{base}/embeddings"


# ---------------------------------------------------------------------------
# Response parser (isolates response.json() Any)
# ---------------------------------------------------------------------------


from typing import cast as _cast


def _parse_embedding_response(response: httpx.Response) -> list[list[float]]:
    """Parse a 200 embedding API response and return validated vectors.

    Raises ``EmbeddingAPIError`` on malformed structure.
    """
    # cast tells pyright expected shapes; isinstance guards validate at runtime.
    # The response body is typed as dict[str, object] so all .get() calls return
    # ``object | None``, requiring explicit isinstance checks before use.
    body = _cast(dict[str, object], response.json())
    raw_data: object = body.get("data")
    if not isinstance(raw_data, list):
        raise EmbeddingAPIError("Response 'data' is missing or not a list")
    items = _cast(list[dict[str, object]], raw_data)
    vectors: list[list[float]] = []
    for entry in items:
        raw_embedding: object = entry.get("embedding")
        if not isinstance(raw_embedding, list):
            raise EmbeddingAPIError("Embedding entry is not a list")
        vectors.append(_cast(list[float], raw_embedding))
    return vectors


# ---------------------------------------------------------------------------
# Retry helper (manual loop, no tenacity dependency)
# ---------------------------------------------------------------------------


def _call_with_retry(
    fn: Callable[[], list[list[float]]],
    max_retries: int = MAX_RETRIES,
) -> list[list[float]]:
    """Call *fn* with exponential-backoff retry on transient errors.

    Retried exception types:
        EmbeddingRateLimitError, EmbeddingServerError,
        httpx.TimeoutException, httpx.ConnectError
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except (EmbeddingRateLimitError, EmbeddingServerError, httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                wait = min(30.0, 2.0 ** attempt)
                time.sleep(wait)
    if last_exc is not None:
        raise last_exc
    # Should never reach here (fn either returns or raises)
    raise EmbeddingError("Retry loop exhausted without exception (unreachable)")


# ---------------------------------------------------------------------------
# Embedding Service
# ---------------------------------------------------------------------------


class EmbeddingService:
    """9Router-native embedding service with privacy guards and retry logic.

    Uses httpx for all HTTP communication. Never imports or uses OpenAI SDK.

    Typical usage::

        service = EmbeddingService()
        vector = service.embed("Hello world", classification="Restricted")
        batch = service.embed_batch(["a", "b"], classification="Public")
    """

    _config: EmbeddingConfig
    _http_client: httpx.Client
    _log: _Logger

    def __init__(
        self,
        config: EmbeddingConfig | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._config = config or EmbeddingConfig()
        self._http_client = http_client or httpx.Client(
            timeout=httpx.Timeout(self._config.timeout_seconds),
        )
        self._log = _logger.bind(
            model=self._config.model,
            expected_dimension=self._config.expected_dimension,
        )

    # ------------------------------------------------------------------
    # Public sync API
    # ------------------------------------------------------------------

    def embed(
        self,
        text: str,
        classification: str = RESTRICTED,
        *,
        sanitized_summary: str | None = None,
    ) -> Vector:
        """Embed a single text string.

        Parameters
        ----------
        text:
            Text to embed.
        classification:
            Data classification level.
        sanitized_summary:
            Pre-sanitized summary for Critical classification.

        Returns
        -------
        Vector of length ``expected_dimension`` (default 1536).
        """
        prepared = prepare_embedding_text(text, classification, sanitized_summary=sanitized_summary)
        return self._embed_prepared(prepared)

    def embed_batch(
        self,
        texts: list[str],
        classification: str = RESTRICTED,
    ) -> EmbeddingBatch:
        """Embed a batch of texts under the same classification.

        Each text goes through privacy preprocessing individually.
        """
        prepared_list = [prepare_embedding_text(t, classification) for t in texts]
        return self._embed_batch_prepared(prepared_list)

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def aembed(
        self,
        text: str,
        classification: str = RESTRICTED,
        *,
        sanitized_summary: str | None = None,
    ) -> Vector:
        """Async single-text embedding."""
        prepared = prepare_embedding_text(text, classification, sanitized_summary=sanitized_summary)
        return await self._aembed_prepared(prepared)

    async def aembed_batch(
        self,
        texts: list[str],
        classification: str = RESTRICTED,
    ) -> EmbeddingBatch:
        """Async batch embedding."""
        prepared_list = [prepare_embedding_text(t, classification) for t in texts]
        return await self._aembed_batch_prepared(prepared_list)

    # ------------------------------------------------------------------
    # Internal: sync HTTP request
    # ------------------------------------------------------------------

    def _do_sync_request(self, texts: list[str]) -> list[list[float]]:
        """Execute one sync HTTP request to the embedding API."""
        api_key = self._config.api_key
        if not api_key:
            raise EmbeddingConfigurationError(
                "No API key available. Set GUINEVERE_9ROUTER_API_KEY "
                + "or OPENROUTER_API_KEY in environment."
            )
        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, object] = {
            "model": self._config.model,
            "input": texts,
        }
        try:
            response = self._http_client.post(
                self._config.embed_url,
                headers=headers,
                json=payload,
            )
        except httpx.TimeoutException:
            self._log.warning("embedding_request_timeout")
            raise
        except httpx.ConnectError:
            self._log.warning("embedding_connection_error")
            raise
        self._raise_on_http_error(response)
        return _parse_embedding_response(response)

    def _embed_prepared(self, prepared: PreparedText) -> Vector:
        """Embed a single PreparedText."""
        vectors = self._do_sync_texts([prepared.text])
        vector = vectors[0]
        self._validate_vector(vector)
        self._log.info(
            "embedding_success",
            classification=prepared.classification,
            redaction_applied=prepared.redaction_applied,
            char_count=len(prepared.text),
        )
        return vector

    def _embed_batch_prepared(self, prepared_list: list[PreparedText]) -> EmbeddingBatch:
        """Embed multiple PreparedTexts in one API call."""
        texts = [p.text for p in prepared_list]
        vectors = self._do_sync_texts(texts)
        for v in vectors:
            self._validate_vector(v)
        if prepared_list:
            p = prepared_list[0]
            self._log.info(
                "embedding_batch_success",
                batch_size=len(prepared_list),
                classification=p.classification,
                redaction_applied=p.redaction_applied,
            )
        return vectors

    def _do_sync_texts(self, texts: list[str]) -> list[list[float]]:
        """Send texts to API with retry."""
        return _call_with_retry(lambda: self._do_sync_request(texts))

    def _validate_vector(self, vector: list[float]) -> None:
        """Validate vector has expected dimension (1536)."""
        if len(vector) != self._config.expected_dimension:
            raise DimensionMismatchError(
                "Expected dimension " + str(self._config.expected_dimension)
                + ", got " + str(len(vector)) + ". Model: " + self._config.model
            )

    # ------------------------------------------------------------------
    # Internal: async HTTP request
    # ------------------------------------------------------------------

    async def _do_async_request(self, texts: list[str]) -> list[list[float]]:
        """Execute one async HTTP request to the embedding API."""
        api_key = self._config.api_key
        if not api_key:
            raise EmbeddingConfigurationError(
                "No API key available. Set GUINEVERE_9ROUTER_API_KEY "
                + "or OPENROUTER_API_KEY in environment."
            )
        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, object] = {
            "model": self._config.model,
            "input": texts,
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._config.timeout_seconds)
        ) as client:
            try:
                response = await client.post(
                    self._config.embed_url,
                    headers=headers,
                    json=payload,
                )
            except httpx.TimeoutException:
                self._log.warning("aembedding_request_timeout")
                raise
            except httpx.ConnectError:
                self._log.warning("aembedding_connection_error")
                raise
        self._raise_on_http_error(response)
        return _parse_embedding_response(response)

    async def _aembed_prepared(self, prepared: PreparedText) -> Vector:
        """Async single PreparedText embedding."""
        vectors = await self._do_async_texts([prepared.text])
        vector = vectors[0]
        self._validate_vector(vector)
        self._log.info(
            "aembedding_success",
            classification=prepared.classification,
            redaction_applied=prepared.redaction_applied,
            char_count=len(prepared.text),
        )
        return vector

    async def _aembed_batch_prepared(self, prepared_list: list[PreparedText]) -> EmbeddingBatch:
        """Async batch embedding."""
        texts = [p.text for p in prepared_list]
        vectors = await self._do_async_texts(texts)
        for v in vectors:
            self._validate_vector(v)
        if prepared_list:
            p = prepared_list[0]
            self._log.info(
                "aembedding_batch_success",
                batch_size=len(prepared_list),
                classification=p.classification,
                redaction_applied=p.redaction_applied,
            )
        return vectors

    async def _do_async_texts(self, texts: list[str]) -> list[list[float]]:
        """Send texts to API with retry (async)."""
        return await _acall_with_retry(lambda: self._do_async_request(texts))

    @staticmethod
    def _raise_on_http_error(response: httpx.Response) -> None:
        """Check HTTP status and raise appropriate embedding error."""
        if response.status_code == 429:
            raise EmbeddingRateLimitError(f"Rate limited: {response.text[:200]}")
        if 500 <= response.status_code < 600:
            raise EmbeddingServerError(
                f"Server error ({response.status_code}): {response.text[:200]}"
            )
        if response.status_code != 200:
            raise EmbeddingAPIError(
                f"API error ({response.status_code}): {response.text[:200]}"
            )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http_client.close()

    def __enter__(self) -> EmbeddingService:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Async retry helper
# ---------------------------------------------------------------------------


async def _acall_with_retry(
    fn: Callable[[], Awaitable[list[list[float]]]],
    max_retries: int = MAX_RETRIES,
) -> list[list[float]]:
    """Async variant of ``_call_with_retry``."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            result = await fn()
            return result
        except (EmbeddingRateLimitError, EmbeddingServerError, httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                wait = min(30.0, 2.0 ** attempt)
                await _async_sleep(wait)
    if last_exc is not None:
        raise last_exc
    raise EmbeddingError("Async retry loop exhausted without exception (unreachable)")


async def _async_sleep(seconds: float) -> None:
    """Sleep without ``asyncio`` import at module level."""
    import asyncio

    await asyncio.sleep(seconds)


# ---------------------------------------------------------------------------
# Convenience sync functions
# ---------------------------------------------------------------------------

_default_service: EmbeddingService | None = None


def _get_default_service() -> EmbeddingService:
    """Get or create the default EmbeddingService singleton."""
    global _default_service
    if _default_service is None:
        _default_service = EmbeddingService()
    return _default_service


def embed(
    text: str,
    classification: str = RESTRICTED,
    *,
    sanitized_summary: str | None = None,
) -> Vector:
    """Convenience function: embed a single text using default service."""
    svc = _get_default_service()
    return svc.embed(text, classification, sanitized_summary=sanitized_summary)


def embed_batch(
    texts: list[str],
    classification: str = RESTRICTED,
) -> EmbeddingBatch:
    """Convenience function: embed a batch using default service."""
    svc = _get_default_service()
    return svc.embed_batch(texts, classification)


async def aembed(
    text: str,
    classification: str = RESTRICTED,
    *,
    sanitized_summary: str | None = None,
) -> Vector:
    """Convenience async function: embed a single text."""
    svc = _get_default_service()
    return await svc.aembed(text, classification, sanitized_summary=sanitized_summary)


async def aembed_batch(
    texts: list[str],
    classification: str = RESTRICTED,
) -> EmbeddingBatch:
    """Convenience async function: embed a batch."""
    svc = _get_default_service()
    return await svc.aembed_batch(texts, classification)


# ---------------------------------------------------------------------------
# Module-level cleanup
# ---------------------------------------------------------------------------

import atexit


def _cleanup_default_service() -> None:
    """Close default service on interpreter exit."""
    global _default_service
    if _default_service is not None:
        _default_service.close()
        _default_service = None


_ = atexit.register(_cleanup_default_service)
"""F07: In-process rate-limit middleware for Guinevere's FastAPI app.

Avoids the ``slowapi`` dependency (which is NOT installed in this repo).
Backed by a dict of ``(key -> deque[float timestamps])`` with capped dict
size + per-key tail-cleanup so long-running processes don't leak memory.

Limits (enforced at app startup via the module-level constants):
    GET                                     60 req / 60 s  keyed by client IP
    POST/PUT/DELETE/PATCH                   10 req / 60 s  keyed by API key
                                                   (X-Guinevere-API-Key; fallback IP)
    POST /api/v1/integrations/dry-run        5 req / 60 s  keyed by API key

Returns HTTP 429 + ``Retry-After`` header when exceeded.
Internal observability endpoints (``/metrics``, ``/health``, ``/``) are exempt.
"""

from __future__ import annotations

import time as _time
from collections import deque as _deque
from typing import Any

import structlog
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

from src.core.api.auth import API_KEY_HEADER

logger = structlog.get_logger(__name__)

_RATE_WINDOW_SECONDS: int = 60
_RATE_LIMIT_GET: int = 60
_RATE_LIMIT_MUTATE: int = 10
_RATE_LIMIT_DRY_RUN: int = 5
_DRY_RUN_PATH: str = "/api/v1/integrations/dry-run"
_RATE_LIMIT_MAX_KEYS: int = 10_000  # cap dict size (LIFO eviction)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket-style per-key rate limiter (in-memory dict of deques).

    Key strategy:
      - ``POST /integrations/dry-run`` mutations -> keyed by API key (fallback IP).
      - Other mutations (POST/PUT/DELETE/PATCH) -> keyed by API key (fallback IP).
      - Reads -> keyed by client IP.

    Returns HTTP 429 + ``Retry-After`` header (seconds until the oldest
    in-window timestamp expires) when exceeded. Internal observability
    endpoints (``/metrics``, ``/health``, ``/``) are exempt.
    """

    def __init__(self, app: Any) -> None:  # noqa: ANN401 — FastAPI signature
        super().__init__(app)
        # ``_buckets[key] = deque[float timestamps_in_window]``.
        self._buckets: dict[str, _deque] = {}

    @staticmethod
    def _client_ip(request: StarletteRequest) -> str:
        # ``client`` may be None for some ASGI transports; fall back to peer.
        client = request.client
        if client is not None and getattr(client, "host", None):
            return str(client.host)
        return "unknown"

    @classmethod
    def _key_for_request(cls, request: StarletteRequest) -> str:
        # Read raw header — do NOT verify here. Verification is the auth
        # dependency's job in the route layer; rate-limit just buckets.
        api_key = request.headers.get(API_KEY_HEADER) or request.headers.get(
            API_KEY_HEADER.lower()
        )
        if api_key:
            return f"key:{api_key}"
        return f"ip:{cls._client_ip(request)}"

    def _bucket_for(
        self, request: StarletteRequest, method: str, path: str,
    ) -> tuple[str, int]:
        is_mutation = method in ("POST", "PUT", "DELETE", "PATCH")
        if path == _DRY_RUN_PATH and is_mutation:
            return RateLimitMiddleware._key_for_request(request), _RATE_LIMIT_DRY_RUN
        if is_mutation:
            return RateLimitMiddleware._key_for_request(request), _RATE_LIMIT_MUTATE
        return (
            f"ip:{RateLimitMiddleware._client_ip(request)}",
            _RATE_LIMIT_GET,
        )

    def _evict_if_oversize(self) -> None:
        """Drop an arbitrary entry if dict exceeds cap. Bounded O(1)."""
        if len(self._buckets) > _RATE_LIMIT_MAX_KEYS:
            try:
                self._buckets.popitem()
            except KeyError:
                pass

    async def dispatch(
        self,
        request: StarletteRequest,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Allow internal/observability endpoints through unmetered.
        path = request.url.path
        if path.startswith("/metrics") or path in ("/health", "/"):
            return await call_next(request)

        key, limit = self._bucket_for(request, request.method, path)
        now = _time.monotonic()
        window_start = now - _RATE_WINDOW_SECONDS

        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _deque()
            self._buckets[key] = bucket
            self._evict_if_oversize()

        # Drop expired timestamps from the left; cheap amortized.
        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        if len(bucket) >= limit:
            # Compute Retry-After (seconds until oldest in-window expires).
            retry_after = max(
                1, int(bucket[0]) + _RATE_WINDOW_SECONDS - int(now) + 1
            )
            logger.info(
                "rate_limit_exceeded",
                path=path,
                method=request.method,
                key_kind=key.split(":", 1)[0],
                limit=limit,
                retry_after=retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": limit,
                    "window_seconds": _RATE_WINDOW_SECONDS,
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        return await call_next(request)

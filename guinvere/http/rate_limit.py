"""In-process rate-limit middleware for Guinevere's FastAPI app.

Ported from ``guinvere/core/api/rate_limit.py`` (149 lines).

Deque-based, self-contained — no ``slowapi`` dependency.  Exempt paths:
``/metrics``, ``/health``, ``/health/ready``, ``/health/agent``, ``/``.
"""

from __future__ import annotations

import time
from collections import deque

import structlog
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from guinevere.http.auth import API_KEY_HEADER

logger = structlog.get_logger(__name__)

_RATE_WINDOW_SECONDS: int = 60
_RATE_LIMIT_GET: int = 60
_RATE_LIMIT_MUTATE: int = 10
_RATE_LIMIT_DRY_RUN: int = 5
_DRY_RUN_PATH: str = "/api/v1/integrations/dry-run"
_RATE_LIMIT_MAX_KEYS: int = 10_000

_EXEMPT_PREFIXES: tuple[str, ...] = ("/metrics", "/health")
_EXEMPT_EXACT: frozenset[str] = frozenset({"/"})


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket-style per-key rate limiter (in-memory dict of deques).

    Key strategy:
      - ``POST /integrations/dry-run`` -> keyed by API key (fallback IP).
      - Other mutations (POST/PUT/DELETE/PATCH) -> keyed by API key (fallback IP).
      - Reads -> keyed by client IP.

    Returns HTTP 429 + ``Retry-After`` header when exceeded.
    Observability endpoints (``/metrics``, ``/health*``, ``/``) are exempt.
    """

    def __init__(self, app: object) -> None:
        super().__init__(app)
        self._buckets: dict[str, deque[float]] = {}

    @staticmethod
    def _client_ip(request: Request) -> str:
        client = request.client
        if client is not None and getattr(client, "host", None):
            return str(client.host)
        return "unknown"

    @classmethod
    def _key_for_request(cls, request: Request) -> str:
        api_key = request.headers.get(API_KEY_HEADER) or request.headers.get(
            API_KEY_HEADER.lower(),
        )
        if api_key:
            return f"key:{api_key}"
        return f"ip:{cls._client_ip(request)}"

    def _bucket_for(
        self,
        request: Request,
        method: str,
        path: str,
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
        """Drop an arbitrary entry if dict exceeds cap.  Bounded O(1)."""
        if len(self._buckets) > _RATE_LIMIT_MAX_KEYS:
            try:
                self._buckets.popitem()
            except KeyError:
                pass

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        path = request.url.path

        # Allow observability endpoints through unmetered.
        if path in _EXEMPT_EXACT or path.startswith(_EXEMPT_PREFIXES):
            return await call_next(request)

        key, limit = self._bucket_for(request, request.method, path)
        now = time.monotonic()
        window_start = now - _RATE_WINDOW_SECONDS

        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = deque()
            self._buckets[key] = bucket
            self._evict_if_oversize()

        # Drop expired timestamps from the left; cheap amortised.
        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = max(
                1, int(bucket[0]) + _RATE_WINDOW_SECONDS - int(now) + 1,
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

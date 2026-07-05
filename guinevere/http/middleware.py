"""Prometheus request-count and latency middleware.

Ported from ``guinevere/core/main.py`` L856-897.

Thin wrapper around ``BaseHTTPMiddleware`` that records
``guinevere_requests_total`` (Counter) and ``guinevere_request_duration_seconds``
(Histogram) per method+endpoint+status.
"""

from __future__ import annotations

import time

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_REQUESTS_TOTAL = Counter(
    "guinevere_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
_REQUEST_DURATION = Histogram(
    "guinevere_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Track request count and duration for Prometheus scraping."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        method = request.method
        endpoint = request.url.path
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        _REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status=str(response.status_code),
        ).inc()
        _REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)
        return response

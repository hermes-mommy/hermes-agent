"""MCP Context7 Tool — Library documentation lookup via Context7 REST API.

Provides ``register_tools(mcp: FastMCP) -> None`` to register two tools:

- ``context7_resolve`` — resolve a library name to a Context7 library ID.
- ``context7_query`` — query documentation for a resolved library.

API endpoints:
    GET /api/v2/libs/search  — search libraries by name
    GET /api/v2/context       — retrieve documentation context

Auth: ``AuthLevel.READ_AUTO`` (no approval needed, read-only).
Cost: Free tier (1000 calls/month) — call count tracked in Redis DB5.
Cache: In-memory LRU dict to minimise API calls and stay within quota.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date
from typing import TYPE_CHECKING, Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.mcp.auth import AuthLevel, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://context7.com/api"
_SEARCH_PATH = "/v2/libs/search"
_CONTEXT_PATH = "/v2/context"
_TIMEOUT_SECONDS = 15.0
_CACHE_MAX_SIZE = 256
_RETRY_MAX_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class Context7Error(Exception):
    """Base exception for Context7 API errors."""


class LibraryNotFoundError(Context7Error):
    """Raised when a library cannot be found in Context7."""


class RateLimitExceededError(Context7Error):
    """Raised when the Context7 rate limit (HTTP 429) is hit."""


# ---------------------------------------------------------------------------
# HTTP helper with tenacity retries
# ---------------------------------------------------------------------------


@retry(
    stop=stop_after_attempt(_RETRY_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.TransportError),
    reraise=True,
)
async def _api_get(
    client: httpx.AsyncClient,
    path: str,
    params: dict[str, str],
) -> Any:
    """Perform a GET request with retry on transport errors.

    Raises ``RateLimitExceededError`` on 429 and ``httpx.HTTPStatusError``
    on other non-2xx responses.
    """
    response = await client.get(path, params=params)

    if response.status_code == 429:
        logger.warning("context7_rate_limited", path=path)
        raise RateLimitExceededError(
            "Context7 rate limit exceeded (429). Retry later or use cached results."
        )

    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# In-memory LRU cache for library resolution
# ---------------------------------------------------------------------------

_resolve_cache: dict[str, dict[str, str]] = {}


def _cache_key(library_name: str, query: str) -> str:
    """Build a normalised cache key for library resolution."""
    return f"{library_name.lower()}:{query.lower()}"


def _cache_get(library_name: str, query: str) -> dict[str, str] | None:
    """Return a cached resolution result, or *None* on miss."""
    key = _cache_key(library_name, query)
    result = _resolve_cache.get(key)
    if result is not None:
        # Move to end (most-recently used) by re-inserting.
        del _resolve_cache[key]
        _resolve_cache[key] = result
        logger.debug("context7_cache_hit", key=key)
    return result


def _cache_set(library_name: str, query: str, result: dict[str, str]) -> None:
    """Store a resolution result, evicting the LRU entry if over limit."""
    key = _cache_key(library_name, query)
    if key in _resolve_cache:
        del _resolve_cache[key]
    elif len(_resolve_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_resolve_cache))
        del _resolve_cache[oldest_key]
    _resolve_cache[key] = result
    logger.debug("context7_cache_set", key=key, size=len(_resolve_cache))


def cache_clear() -> None:
    """Clear the resolution cache (useful for testing)."""
    _resolve_cache.clear()


def cache_size() -> int:
    """Return the current number of cached entries."""
    return len(_resolve_cache)


# ---------------------------------------------------------------------------
# Redis cost tracking (best-effort, never blocks tool execution)
# ---------------------------------------------------------------------------


def _track_cost_sync() -> None:
    """Increment the daily call counter in Redis DB5.

    Runs synchronously — designed to be called via ``asyncio.to_thread``.
    """
    import redis as redis_lib

    client = redis_lib.Redis(
        host="localhost",
        port=6380,
        db=5,
        username="guinevere_core",
        password=os.environ.get("REDIS_PASSWORD", ""),
        decode_responses=True,
        socket_timeout=3.0,
    )
    today = date.today().isoformat()
    key = f"tool:cost:context7:{today}"
    client.incr(key)
    client.expire(key, 86400 * 2)  # TTL: 2 days
    client.close()
    logger.debug("context7_cost_tracked", key=key)


async def _track_cost() -> None:
    """Increment the daily call counter (best-effort, fire-and-forget)."""
    try:
        await asyncio.to_thread(_track_cost_sync)
    except (ConnectionError, OSError, TimeoutError) as exc:
        logger.warning("context7_cost_tracking_failed", error=str(exc))
    except ImportError:
        logger.warning("context7_redis_unavailable")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def context7_resolve(
    library_name: str, query: str = ""
) -> dict[str, str]:
    """Resolve a library name to a Context7 library ID.

    Args:
        library_name: Name of the library to search for (e.g., "react").
        query: Optional context query for relevance ranking.

    Returns:
        Dict with keys: id, name, description, total_snippets,
        trust_score, benchmark_score.  On failure, contains an
        ``error`` key with a ``suggestion``.
    """
    # Check cache first to save API calls.
    cached = _cache_get(library_name, query)
    if cached is not None:
        return cached

    logger.info("context7_resolve", library_name=library_name, query=query)

    params: dict[str, str] = {"libraryName": library_name}
    if query:
        params["query"] = query

    try:
        async with httpx.AsyncClient(
            base_url=_BASE_URL, timeout=_TIMEOUT_SECONDS
        ) as client:
            data = await _api_get(client, _SEARCH_PATH, params)
    except RateLimitExceededError:
        logger.warning(
            "context7_resolve_rate_limited", library_name=library_name
        )
        return {
            "error": "rate_limited",
            "suggestion": "Rate limit exceeded. Try again later.",
        }
    except httpx.HTTPStatusError as exc:
        logger.error(
            "context7_resolve_http_error",
            library_name=library_name,
            status=exc.response.status_code,
        )
        return {
            "error": "http_error",
            "status_code": str(exc.response.status_code),
            "suggestion": "Context7 API returned an error. Check the library name.",
        }
    except httpx.TransportError as exc:
        logger.error(
            "context7_resolve_transport_error",
            library_name=library_name,
            error=str(exc),
        )
        return {
            "error": "network_error",
            "suggestion": (
                "Network error contacting Context7. "
                "Check connectivity and retry."
            ),
        }

    # Parse results — API returns {"results": [...]}
    results: list[dict[str, Any]] = (
        data.get("results", []) if isinstance(data, dict) else data
    )
    if not results:
        logger.info("context7_resolve_not_found", library_name=library_name)
        return {
            "error": "not_found",
            "suggestion": (
                f"No library found for '{library_name}'. Try a different name."
            ),
        }

    best = results[0]
    resolved: dict[str, str] = {
        "id": str(best.get("id", "")),
        "name": str(best.get("title", "")),
        "description": str(best.get("description", "")),
        "total_snippets": str(best.get("totalSnippets", 0)),
        "trust_score": str(best.get("trustScore", 0)),
        "benchmark_score": str(best.get("benchmarkScore", 0)),
    }

    _cache_set(library_name, query, resolved)
    await _track_cost()

    logger.info(
        "context7_resolved", library_id=resolved["id"], name=resolved["name"]
    )
    return resolved


async def context7_query(
    library_id: str, query: str
) -> dict[str, object]:
    """Query documentation for a resolved library.

    Args:
        library_id: Context7 library ID (e.g., "/facebook/react").
        query: Natural language question about the library.

    Returns:
        Dict with keys: library_id, query, context.
        On failure, contains an ``error`` key with a ``suggestion``.
    """
    logger.info("context7_query", library_id=library_id, query=query)

    params: dict[str, str] = {
        "libraryId": library_id,
        "query": query,
        "type": "json",
    }

    try:
        async with httpx.AsyncClient(
            base_url=_BASE_URL, timeout=_TIMEOUT_SECONDS
        ) as client:
            data = await _api_get(client, _CONTEXT_PATH, params)
    except RateLimitExceededError:
        logger.warning("context7_query_rate_limited", library_id=library_id)
        return {
            "error": "rate_limited",
            "library_id": library_id,
            "suggestion": "Rate limit exceeded. Try again later.",
        }
    except httpx.HTTPStatusError as exc:
        logger.error(
            "context7_query_http_error",
            library_id=library_id,
            status=exc.response.status_code,
        )
        return {
            "error": "http_error",
            "library_id": library_id,
            "status_code": exc.response.status_code,
            "suggestion": "Context7 API returned an error.",
        }
    except httpx.TransportError as exc:
        logger.error(
            "context7_query_transport_error",
            library_id=library_id,
            error=str(exc),
        )
        return {
            "error": "network_error",
            "library_id": library_id,
            "suggestion": (
                "Network error contacting Context7. "
                "Check connectivity and retry."
            ),
        }

    await _track_cost()

    result: dict[str, object] = {
        "library_id": library_id,
        "query": query,
        "context": data,
    }

    logger.info("context7_query_complete", library_id=library_id)
    return result


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register Context7 tools on the MCP server.

    Adds two tools:

    - ``context7_resolve`` — resolve library name to Context7 ID.
    - ``context7_query`` — query documentation for a resolved library.

    Both are gated with ``AuthLevel.READ_AUTO`` (no approval needed).
    """

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="context7_resolve")
    async def _context7_resolve(
        library_name: str, query: str = ""
    ) -> dict[str, str]:
        """Resolve a library name to a Context7 library ID.

        Args:
            library_name: Name of the library (e.g., "react", "fastapi").
            query: Optional context for relevance ranking.

        Returns:
            Dict with library metadata or error info.
        """
        return await context7_resolve(library_name, query)

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="context7_query")
    async def _context7_query(
        library_id: str, query: str
    ) -> dict[str, object]:
        """Query documentation for a resolved Context7 library.

        Args:
            library_id: Context7 library ID (e.g., "/facebook/react").
            query: Natural language question about the library.

        Returns:
            Dict with documentation context.
        """
        return await context7_query(library_id, query)

    logger.info("context7_tools_registered")

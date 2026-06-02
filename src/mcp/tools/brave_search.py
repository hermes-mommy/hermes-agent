"""Brave Search MCP Tool — Web search via Brave Search API.

Provides a FastMCP-registered tool that queries the Brave Search API
and returns structured web results.  Cost is tracked per-query in
Redis DB 5.
"""

from __future__ import annotations

import os
from datetime import date
from typing import TYPE_CHECKING

import httpx
import redis
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
# Constants
# ---------------------------------------------------------------------------

_API_URL = "https://api.search.brave.com/res/v1/web/search"
_COST_PER_SEARCH: float = 0.01
_REDIS_KEY_PREFIX = "tool:cost:brave_search"


# ---------------------------------------------------------------------------
# Configuration error
# ---------------------------------------------------------------------------


class BraveSearchConfigError(Exception):
    """Raised when Brave Search configuration is missing or invalid."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    """Return the Brave API key from the environment, or raise."""
    key = os.environ.get("BRAVE_API_KEY")
    if not key:
        raise BraveSearchConfigError(
            "BRAVE_API_KEY environment variable is required."
        )
    return key


def _get_redis_client() -> redis.Redis:
    """Build a Redis client for cost tracking (DB 5)."""
    return redis.Redis(
        host="localhost",
        port=6380,
        db=5,
        username="guinevere_core",
        password=os.environ.get("REDIS_PASSWORD", ""),
        decode_responses=True,
    )


def _record_cost(client: redis.Redis) -> None:
    """Increment the daily cost counter in Redis."""
    today = date.today().isoformat()
    key = f"{_REDIS_KEY_PREFIX}:{today}"
    client.incrbyfloat(key, _COST_PER_SEARCH)
    logger.debug(
        "brave_search_cost_recorded", key=key, cost=_COST_PER_SEARCH
    )


# ---------------------------------------------------------------------------
# HTTP fetch (retried)
# ---------------------------------------------------------------------------


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.ConnectError),
    reraise=True,
)
async def _fetch_search(
    query: str, count: int, api_key: str
) -> list[dict[str, str]]:
    """Call the Brave Search API and return parsed results.

    Retries on ``httpx.ConnectError`` up to 3 times with exponential
    backoff.  ``HTTPStatusError`` is NOT retried.
    """
    headers = {
        "X-Subscription-Token": api_key,
        "Accept": "application/json",
    }
    params = {"q": query, "count": str(count)}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    results: list[dict[str, str]] = []
    web = data.get("web", {})
    for item in web.get("results", []):
        results.append(
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "description": str(item.get("description", "")),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Public tool
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="brave_search")
async def brave_search(query: str, count: int = 5) -> list[dict[str, str]]:
    """Search the web via Brave Search API.

    Returns a list of dicts with ``title``, ``url``, and ``description``
    keys.  Returns an empty list on HTTP errors.  Raises on connection
    errors after retries are exhausted.
    """
    api_key = _get_api_key()
    r = _get_redis_client()

    try:
        results = await _fetch_search(query, count, api_key)
    except httpx.HTTPStatusError as exc:
        logger.error(
            "brave_search_http_error",
            status=exc.response.status_code,
            query=query,
        )
        return []
    except httpx.ConnectError as exc:
        logger.error(
            "brave_search_connect_error",
            query=query,
            error=str(exc),
        )
        raise

    _record_cost(r)
    logger.info(
        "brave_search_completed", query=query, result_count=len(results)
    )
    return results


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register the brave_search tool with the FastMCP server."""
    mcp.tool()(brave_search)
    logger.info("brave_search_tool_registered")

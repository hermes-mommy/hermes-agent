"""Exa Search — AI-powered semantic search via Exa with $5/day budget cap.

Provides the ``exa_search`` MCP tool which queries the Exa AI search API
with automatic daily budget enforcement through Redis DB5 counters.

Cost model (FinOps v1.1):
    - Per-request cost: ~$0.007
    - Daily burst cap: $5/day
    - Monthly throttle trigger: $3/month
    - Average monthly spend: ~$1/month
"""

from __future__ import annotations

import os
from datetime import date

import httpx
import redis.asyncio as aioredis
import structlog
from mcp.server.fastmcp import FastMCP
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from guinvere.mcp.auth import AuthLevel, require_approval

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXA_API_URL = "https://api.exa.ai/search"
_COST_PER_REQUEST: float = 0.007
_DAILY_CAP: float = 5.0
_REDIS_KEY_PREFIX = "tool:cost:exa"
_REDIS_TTL_SECONDS = 172800  # 2 days — ensures cleanup while preserving data


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BudgetExceeded(Exception):
    """Raised when daily spending cap is reached."""


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    """Return the Exa API key from environment or raise ConfigurationError."""
    key = os.environ.get("EXA_API_KEY")
    if not key:
        raise ConfigurationError(
            "EXA_API_KEY environment variable is required"
        )
    return key


def _get_redis() -> aioredis.Redis:
    """Return an async Redis client connected to DB5."""
    return aioredis.Redis(
        host="localhost",
        port=6380,
        db=5,
        username="guinevere_core",
        password=os.environ.get("REDIS_PASSWORD", ""),
        decode_responses=True,
    )


def _daily_cost_key() -> str:
    """Return the Redis key for today's Exa cost counter."""
    return f"{_REDIS_KEY_PREFIX}:{date.today().isoformat()}"


async def _check_budget(redis_client: aioredis.Redis) -> None:
    """Check daily cap *before* making the API call.

    Raises:
        BudgetExceeded: If current daily spend >= $5.00.
    """
    key = _daily_cost_key()
    current_raw: str | None = await redis_client.get(key)
    current: float = float(current_raw) if current_raw else 0.0

    if current >= _DAILY_CAP:
        logger.warning(
            "exa_budget_exceeded",
            current_spend=current,
            daily_cap=_DAILY_CAP,
        )
        raise BudgetExceeded(
            f"Daily budget cap reached: ${current:.4f} >= ${_DAILY_CAP:.2f}"
        )


async def _record_cost(redis_client: aioredis.Redis, cost: float) -> None:
    """Record API call cost via Redis pipeline with INCRBYFLOAT."""
    key = _daily_cost_key()
    pipe = redis_client.pipeline()
    pipe.incrbyfloat(key, cost)
    pipe.expire(key, _REDIS_TTL_SECONDS)
    await pipe.execute()
    logger.debug("exa_cost_recorded", cost=cost, key=key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.TransportError),
    reraise=True,
)
async def _call_exa_api(
    client: httpx.AsyncClient,
    query: str,
    num_results: int,
    api_key: str,
) -> list[dict[str, str]]:
    """Call the Exa search API with automatic retries on transport errors."""
    response = await client.post(
        _EXA_API_URL,
        json={"query": query, "numResults": num_results},
        headers={"x-api-key": api_key},
    )
    response.raise_for_status()
    data: dict[str, object] = response.json()
    raw_obj: object = data.get("results", [])
    raw_results: list[dict[str, object]] = (
        raw_obj if isinstance(raw_obj, list) else []
    )
    return [
        {
            "title": str(item.get("title", "")),
            "url": str(item.get("url", "")),
            "snippet": str(item.get("text", "")),
        }
        for item in raw_results
    ]


# ---------------------------------------------------------------------------
# MCP Tool
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="exa_search")
async def exa_search(
    query: str, num_results: int = 10
) -> list[dict[str, str]]:
    """AI-powered semantic search via Exa. $5/day cap enforced."""
    api_key = _get_api_key()
    redis_client = _get_redis()

    try:
        # Budget check BEFORE API call
        await _check_budget(redis_client)

        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await _call_exa_api(
                client, query, num_results, api_key
            )

        # Record cost AFTER successful call
        await _record_cost(redis_client, _COST_PER_REQUEST)

        logger.info(
            "exa_search_completed",
            query_preview=query[:50],
            result_count=len(results),
        )
        return results

    except BudgetExceeded:
        raise
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            logger.warning("exa_rate_limited", status_code=429)
            return []
        logger.error(
            "exa_http_error",
            status_code=exc.response.status_code,
            error=str(exc),
        )
        raise
    except httpx.TransportError as exc:
        logger.error("exa_transport_error", error=str(exc))
        raise
    finally:
        await redis_client.aclose()


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register the ``exa_search`` tool with a FastMCP server."""
    mcp.tool()(exa_search)

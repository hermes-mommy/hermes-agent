"""Hybrid Web Search — Brave primary with Exa fallback.

Provides the ``websearch`` MCP tool which tries Brave Search first
(fast, $0.01/search) and falls back to Exa (semantic, $0.007/request,
$5/day cap) when Brave fails or returns empty results.

Fallback triggers:
    - Empty results from primary
    - HTTP errors (connection, status, transport)
    - Redis errors (cost tracking failure)
    - Rate limiting
    - Budget exceeded (Exa daily cap)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import redis
import structlog

from src.mcp.auth import AuthLevel, require_approval
from src.mcp.tools.brave_search import brave_search
from src.mcp.tools.exa_search import BudgetExceeded, exa_search

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Public tool
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="websearch")
async def websearch(
    query: str,
    count: int = 5,
    prefer: str = "brave",
) -> dict[str, Any]:
    """Hybrid web search: tries Brave first, falls back to Exa.

    Args:
        query: Search query string.
        count: Number of results to return (default 5).
        prefer: Preferred provider (``"brave"`` or ``"exa"``, default ``"brave"``).

    Returns:
        Dict with keys:

        - ``results``: list of search result dicts.
        - ``source``: ``"brave"``, ``"exa"``, or ``"none"``.
        - ``fallback_used``: bool indicating if fallback was triggered.
        - ``error``: (optional) error message if both failed.
    """
    if prefer == "exa":
        primary_name = "exa"
        fallback_name = "brave"
    else:
        primary_name = "brave"
        fallback_name = "exa"

    # --- Try primary provider ------------------------------------------------
    try:
        if primary_name == "brave":
            results = await brave_search(query, count)
        else:
            results = await exa_search(query, num_results=count)

        if results:
            return {
                "results": results,
                "source": primary_name,
                "fallback_used": False,
            }

        logger.info("websearch.primary_empty", query=query, provider=primary_name)

    except BudgetExceeded:
        logger.warning(
            "websearch.primary_budget_exceeded",
            query=query,
            provider=primary_name,
        )
    except (httpx.HTTPError, redis.RedisError) as exc:
        logger.warning(
            "websearch.primary_failed",
            error=str(exc),
            query=query,
            provider=primary_name,
        )
    except Exception as exc:
        logger.warning(
            "websearch.primary_unexpected_error",
            error=str(exc),
            error_type=type(exc).__name__,
            query=query,
            provider=primary_name,
        )

    # --- Fallback to secondary provider ------------------------------------
    try:
        if fallback_name == "exa":
            results = await exa_search(query, num_results=count)
        else:
            results = await brave_search(query, count)

        return {
            "results": results,
            "source": fallback_name,
            "fallback_used": True,
        }

    except BudgetExceeded:
        logger.error(
            "websearch.fallback_budget_exceeded",
            query=query,
            provider=fallback_name,
        )
        return {
            "results": [],
            "source": "none",
            "fallback_used": True,
            "error": "budget_exceeded",
        }
    except (httpx.HTTPError, redis.RedisError) as exc:
        logger.error(
            "websearch.both_failed",
            error=str(exc),
            query=query,
        )
        return {
            "results": [],
            "source": "none",
            "fallback_used": True,
            "error": str(exc),
        }
    except Exception as exc:
        logger.error(
            "websearch.both_unexpected_error",
            error=str(exc),
            error_type=type(exc).__name__,
            query=query,
        )
        return {
            "results": [],
            "source": "none",
            "fallback_used": True,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register the websearch tool with the FastMCP server."""
    mcp.tool()(websearch)
    logger.info("websearch_tool_registered")

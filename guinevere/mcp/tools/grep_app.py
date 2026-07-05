"""grep.app MCP Tool — Code search across GitHub via grep.app API.

Provides a FastMCP-registered tool that queries the public grep.app API
and returns structured code search results.  No authentication is
required and cost is $0.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from guinevere.mcp.auth import AuthLevel, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_URL = "https://grep.app/api/search"
_TIMEOUT_SECONDS: float = 15.0


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_hits(data: dict[str, Any]) -> list[dict[str, str]]:
    """Parse the grep.app JSON response into structured results.

    Each result dict contains:
    - ``repo``: repository name (e.g. ``owner/repo``)
    - ``branch``: branch name
    - ``path``: file path within the repository
    - ``lines``: semicolon-separated ``line_number:content`` pairs
    """
    results: list[dict[str, str]] = []

    hits_container = data.get("hits", {})
    if not isinstance(hits_container, dict):
        return results

    raw_hits = hits_container.get("hits", [])
    if not isinstance(raw_hits, list):
        return results

    for hit in raw_hits:
        if not isinstance(hit, dict):
            continue

        repo_obj = hit.get("repo", {})
        if not isinstance(repo_obj, dict):
            continue

        repo_name = _extract_raw(repo_obj, "repo")
        branch_name = _extract_raw(repo_obj, "branch")
        path_value = _extract_raw(repo_obj, "path")

        content_obj = hit.get("content", {})
        if not isinstance(content_obj, dict):
            continue

        line_entries = content_obj.get("lines", [])
        if not isinstance(line_entries, list):
            continue

        formatted_lines: list[str] = []
        for line_obj in line_entries:
            if not isinstance(line_obj, dict):
                continue
            num = line_obj.get("num", 0)
            line_text = str(line_obj.get("line", ""))
            formatted_lines.append(f"{num}:{line_text}")

        results.append(
            {
                "repo": repo_name,
                "branch": branch_name,
                "path": path_value,
                "lines": "; ".join(formatted_lines),
            }
        )

    return results


def _extract_raw(container: dict[str, Any], key: str) -> str:
    """Extract a ``raw`` string value from a nested dict structure."""
    inner = container.get(key, {})
    if isinstance(inner, dict):
        return str(inner.get("raw", ""))
    return str(inner)


# ---------------------------------------------------------------------------
# HTTP fetch (retried)
# ---------------------------------------------------------------------------


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(httpx.ConnectError),
    reraise=True,
)
async def _fetch_search(
    query: str,
    language: list[str] | None,
    repo: str | None,
    use_regexp: bool,
    match_case: bool,
) -> list[dict[str, str]]:
    """Call the grep.app API and return parsed results.

    Retries on ``httpx.ConnectError`` up to 2 times with exponential
    backoff.  ``HTTPStatusError`` is NOT retried.
    """
    params: dict[str, str] = {
        "q": query,
        "regexp": "true" if use_regexp else "false",
        "case": "true" if match_case else "false",
    }

    if language:
        for idx, lang in enumerate(language):
            params[f"filters[lang][{idx}]"] = lang

    if repo:
        params["filters[repo][0]"] = repo

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        response = await client.get(_API_URL, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()

    return _parse_hits(data)


# ---------------------------------------------------------------------------
# Public tool
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="grep_app_search")
async def grep_app_search(
    query: str,
    language: list[str] | None = None,
    repo: str | None = None,
    use_regexp: bool = False,
    match_case: bool = True,
) -> list[dict[str, str]]:
    """Search for real-world code patterns across GitHub via grep.app.

    Args:
        query: The code pattern to search for.
        language: Optional list of programming languages to filter by.
        repo: Optional repository filter (e.g. ``owner/repo``).
        use_regexp: Whether to treat the query as a regular expression.
        match_case: Whether the search should be case-sensitive.

    Returns:
        A list of dicts with ``repo``, ``branch``, ``path``, and ``lines``
        keys.  Returns an empty list on errors or when no results are found.
    """
    try:
        results = await _fetch_search(
            query=query,
            language=language,
            repo=repo,
            use_regexp=use_regexp,
            match_case=match_case,
        )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "grep_app_http_error",
            status=exc.response.status_code,
            query=query,
        )
        return []
    except httpx.ConnectError as exc:
        logger.error(
            "grep_app_connect_error",
            query=query,
            error=str(exc),
        )
        return []
    except httpx.HTTPError as exc:
        logger.error(
            "grep_app_request_error",
            query=query,
            error=str(exc),
        )
        return []

    logger.info(
        "grep_app_search_completed",
        query=query,
        result_count=len(results),
    )
    return results


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register the grep_app_search tool with the FastMCP server."""
    mcp.tool()(grep_app_search)
    logger.info("grep_app_search_tool_registered")

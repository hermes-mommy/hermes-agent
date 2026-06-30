"""MCP Tools — GitHub API operations.

Provides tools for interacting with the GitHub REST API via ``httpx``,
with auth-level gating, rate-limit awareness, and retry logic.

Auth levels:
    - Read operations (list repos, get file, search code) → ``READ_AUTO``
    - Write operations (create issue, create PR) → ``WRITE_NOTIFY``

Error handling:
    - 401 → ``ConfigurationError`` (invalid PAT)
    - 403 → rate-limit info logged, error raised
    - 404 → empty result returned
    - 5xx → retried with exponential backoff (tenacity)
"""

from __future__ import annotations

import base64
import os
from typing import TYPE_CHECKING, Any

import httpx
import structlog
import tenacity

from guinvere.mcp.auth import AuthLevel, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

_GITHUB_API_BASE = "https://api.github.com"
_TIMEOUT_SECONDS = 15.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GitHubToolError(Exception):
    """Base exception for GitHub tool errors."""


class ConfigurationError(GitHubToolError):
    """Raised when required configuration (e.g. GITHUB_PAT) is missing."""


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


def _build_client() -> httpx.AsyncClient:
    """Create an ``httpx.AsyncClient`` configured for the GitHub API."""
    pat = os.environ.get("GITHUB_PAT", "")
    return httpx.AsyncClient(
        base_url=_GITHUB_API_BASE,
        timeout=_TIMEOUT_SECONDS,
        headers={
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_pat() -> str:
    """Return ``GITHUB_PAT`` from environment or raise ``ConfigurationError``."""
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        raise ConfigurationError(
            "GITHUB_PAT environment variable is not set or empty."
        )
    return pat


def _parse_rate_limit_headers(response: httpx.Response) -> dict[str, str]:
    """Extract and log GitHub rate-limit headers from *response*."""
    remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
    reset = response.headers.get("X-RateLimit-Reset", "unknown")
    logger.info(
        "github_rate_limit",
        remaining=remaining,
        reset=reset,
    )
    return {"remaining": remaining, "reset": reset}


def _handle_response_error(response: httpx.Response, operation: str) -> None:
    """Inspect *response* status and raise appropriate typed errors.

    - 401 → ``ConfigurationError``
    - 403 → ``httpx.HTTPStatusError`` (rate-limited / forbidden)
    - 404 → no-op (caller returns empty result)
    - Other 4xx/5xx → ``httpx.HTTPStatusError``
    """
    _parse_rate_limit_headers(response)

    if response.status_code == 401:
        logger.error("github_auth_failed", operation=operation)
        raise ConfigurationError(
            f"GitHub API returned 401 for '{operation}'. "
            "Check GITHUB_PAT validity."
        )

    if response.status_code == 403:
        logger.warning("github_rate_limited", operation=operation)
        response.raise_for_status()
        return

    if response.status_code == 404:
        logger.warning("github_not_found", operation=operation)
        return

    response.raise_for_status()


def _is_retryable_error(exc: BaseException) -> bool:
    """Return ``True`` if *exc* represents a retryable transient error."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="github_list_repos")
@tenacity.retry(
    retry=tenacity.retry_if_exception(_is_retryable_error),
    wait=tenacity.wait_exponential(multiplier=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
async def github_list_repos(owner: str) -> list[dict[str, str]]:
    """List repositories for an owner. Auth: READ_AUTO."""
    _ensure_pat()
    async with _build_client() as client:
        response = await client.get(f"/users/{owner}/repos")
        if response.status_code == 404:
            _parse_rate_limit_headers(response)
            return []
        _handle_response_error(response, "list_repos")
        result: list[dict[str, str]] = response.json()
        return result


@require_approval(AuthLevel.READ_AUTO, tool_name="github_get_file")
@tenacity.retry(
    retry=tenacity.retry_if_exception(_is_retryable_error),
    wait=tenacity.wait_exponential(multiplier=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
async def github_get_file(owner: str, repo: str, path: str) -> str:
    """Get file contents from a repo. Auth: READ_AUTO."""
    _ensure_pat()
    async with _build_client() as client:
        response = await client.get(f"/repos/{owner}/{repo}/contents/{path}")
        if response.status_code == 404:
            _parse_rate_limit_headers(response)
            return ""
        _handle_response_error(response, "get_file")
        data: dict[str, Any] = response.json()
        content_b64: str = data.get("content", "")
        return base64.b64decode(content_b64).decode("utf-8")


@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="github_create_issue")
@tenacity.retry(
    retry=tenacity.retry_if_exception(_is_retryable_error),
    wait=tenacity.wait_exponential(multiplier=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
async def github_create_issue(
    owner: str, repo: str, title: str, body: str
) -> dict[str, object]:
    """Create an issue. Auth: WRITE_NOTIFY."""
    _ensure_pat()
    async with _build_client() as client:
        response = await client.post(
            f"/repos/{owner}/{repo}/issues",
            json={"title": title, "body": body},
        )
        _handle_response_error(response, "create_issue")
        result: dict[str, object] = response.json()
        return result


@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="github_create_pr")
@tenacity.retry(
    retry=tenacity.retry_if_exception(_is_retryable_error),
    wait=tenacity.wait_exponential(multiplier=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
async def github_create_pr(
    owner: str, repo: str, title: str, head: str, base: str
) -> dict[str, object]:
    """Create a pull request. Auth: WRITE_NOTIFY."""
    _ensure_pat()
    async with _build_client() as client:
        response = await client.post(
            f"/repos/{owner}/{repo}/pulls",
            json={"title": title, "head": head, "base": base},
        )
        _handle_response_error(response, "create_pr")
        result: dict[str, object] = response.json()
        return result


@require_approval(AuthLevel.READ_AUTO, tool_name="github_search_code")
@tenacity.retry(
    retry=tenacity.retry_if_exception(_is_retryable_error),
    wait=tenacity.wait_exponential(multiplier=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
)
async def github_search_code(query: str) -> list[dict[str, str]]:
    """Search code across GitHub. Auth: READ_AUTO."""
    _ensure_pat()
    async with _build_client() as client:
        response = await client.get("/search/code", params={"q": query})
        if response.status_code == 404:
            _parse_rate_limit_headers(response)
            return []
        _handle_response_error(response, "search_code")
        data: dict[str, Any] = response.json()
        items: list[dict[str, str]] = data.get("items", [])
        return items


# ---------------------------------------------------------------------------
# Registration entry-point
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register all GitHub tools on the given FastMCP server."""
    mcp.tool()(github_list_repos)
    mcp.tool()(github_get_file)
    mcp.tool()(github_create_issue)
    mcp.tool()(github_create_pr)
    mcp.tool()(github_search_code)

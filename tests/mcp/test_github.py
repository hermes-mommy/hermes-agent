"""Tests for MCP GitHub tools — mocked httpx, no live API calls."""

from __future__ import annotations

import asyncio
import base64
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.mcp.tools.github import (  # noqa: E402
    ConfigurationError,
    GitHubToolError,
    github_create_issue,
    github_get_file,
    github_list_repos,
    github_search_code,
    register_tools,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int,
    json_data: object = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Build a lightweight ``httpx.Response`` for testing."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        headers=headers or {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1700000000",
        },
        request=httpx.Request("GET", "https://api.github.com/test"),
    )


def _mock_client(responses: list[httpx.Response]) -> AsyncMock:
    """Return an ``AsyncMock`` that yields *responses* from ``__aenter__``.

    The mock client's ``get`` / ``post`` methods return the first (and only)
    response from the list, which covers the common single-request-per-tool
    pattern used in these tests.
    """
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    if responses:
        mock.get = AsyncMock(return_value=responses[0])
        mock.post = AsyncMock(return_value=responses[0])
    return mock


# ============================================================================
# TestGitHubListRepos
# ============================================================================


class TestGitHubListRepos:
    """Tests for ``github_list_repos``."""

    def test_returns_repo_list(self) -> None:
        """Successful response returns a list of repo dicts."""
        repos = [
            {"name": "repo-a", "full_name": "owner/repo-a"},
            {"name": "repo-b", "full_name": "owner/repo-b"},
        ]
        response = _make_response(200, json_data=repos)

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"GITHUB_PAT": "test-pat"}),
                patch(
                    "src.mcp.tools.github._build_client",
                    return_value=_mock_client([response]),
                ),
            ):
                result = await github_list_repos("octocat")
                assert isinstance(result, list)
                assert len(result) == 2
                assert result[0]["name"] == "repo-a"

        asyncio.run(_run())

    def test_returns_empty_on_404(self) -> None:
        """404 response returns an empty list."""
        response = _make_response(404)

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"GITHUB_PAT": "test-pat"}),
                patch(
                    "src.mcp.tools.github._build_client",
                    return_value=_mock_client([response]),
                ),
            ):
                result = await github_list_repos("nonexistent")
                assert result == []

        asyncio.run(_run())


# ============================================================================
# TestGitHubGetFile
# ============================================================================


class TestGitHubGetFile:
    """Tests for ``github_get_file``."""

    def test_decodes_base64_content(self) -> None:
        """File content is base64-decoded and returned as a string."""
        original = "Hello, Guinevere!"
        encoded = base64.b64encode(original.encode("utf-8")).decode("utf-8")
        response = _make_response(200, json_data={"content": encoded})

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"GITHUB_PAT": "test-pat"}),
                patch(
                    "src.mcp.tools.github._build_client",
                    return_value=_mock_client([response]),
                ),
            ):
                result = await github_get_file("owner", "repo", "README.md")
                assert result == original

        asyncio.run(_run())

    def test_returns_empty_string_on_404(self) -> None:
        """404 response returns an empty string."""
        response = _make_response(404)

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"GITHUB_PAT": "test-pat"}),
                patch(
                    "src.mcp.tools.github._build_client",
                    return_value=_mock_client([response]),
                ),
            ):
                result = await github_get_file("owner", "repo", "missing.txt")
                assert result == ""

        asyncio.run(_run())


# ============================================================================
# TestGitHubCreateIssue
# ============================================================================


class TestGitHubCreateIssue:
    """Tests for ``github_create_issue``."""

    def test_returns_created_issue(self) -> None:
        """Successful creation returns the issue dict."""
        issue_data = {
            "id": 42,
            "number": 7,
            "title": "Bug report",
            "state": "open",
        }
        response = _make_response(201, json_data=issue_data)

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"GITHUB_PAT": "test-pat"}),
                patch(
                    "src.mcp.tools.github._build_client",
                    return_value=_mock_client([response]),
                ),
            ):
                result = await github_create_issue(
                    "owner", "repo", "Bug report", "Details here."
                )
                assert result["number"] == 7
                assert result["title"] == "Bug report"

        asyncio.run(_run())


# ============================================================================
# TestGitHubSearchCode
# ============================================================================


class TestGitHubSearchCode:
    """Tests for ``github_search_code``."""

    def test_returns_search_items(self) -> None:
        """Successful search returns the items list."""
        search_data = {
            "total_count": 1,
            "items": [
                {"name": "config.py", "path": "src/config.py"},
            ],
        }
        response = _make_response(200, json_data=search_data)

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"GITHUB_PAT": "test-pat"}),
                patch(
                    "src.mcp.tools.github._build_client",
                    return_value=_mock_client([response]),
                ),
            ):
                result = await github_search_code("repo:owner/repo config")
                assert len(result) == 1
                assert result[0]["name"] == "config.py"

        asyncio.run(_run())


# ============================================================================
# TestGitHubAuthError
# ============================================================================


class TestGitHubAuthError:
    """Tests for 401 and missing-PAT error handling."""

    def test_401_raises_configuration_error(self) -> None:
        """A 401 response raises ``ConfigurationError``."""
        response = _make_response(401, json_data={"message": "Bad credentials"})

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"GITHUB_PAT": "invalid-pat"}),
                patch(
                    "src.mcp.tools.github._build_client",
                    return_value=_mock_client([response]),
                ),
            ):
                with pytest.raises(ConfigurationError, match="401"):
                    await github_list_repos("octocat")

        asyncio.run(_run())

    def test_missing_pat_raises_configuration_error(self) -> None:
        """Missing GITHUB_PAT raises ``ConfigurationError``."""

        async def _run() -> None:
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("GITHUB_PAT", None)
                with pytest.raises(ConfigurationError, match="GITHUB_PAT"):
                    await github_list_repos("octocat")

        asyncio.run(_run())


# ============================================================================
# TestGitHubRateLimitHeaders
# ============================================================================


class TestGitHubRateLimitHeaders:
    """Tests for rate-limit header parsing."""

    def test_rate_limit_headers_logged(self) -> None:
        """X-RateLimit-Remaining and X-RateLimit-Reset are parsed without error."""
        response = _make_response(
            200,
            json_data=[],
            headers={
                "X-RateLimit-Remaining": "4998",
                "X-RateLimit-Reset": "1700001234",
            },
        )

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"GITHUB_PAT": "test-pat"}),
                patch(
                    "src.mcp.tools.github._build_client",
                    return_value=_mock_client([response]),
                ),
            ):
                result = await github_list_repos("octocat")
                assert isinstance(result, list)

        asyncio.run(_run())


# ============================================================================
# TestGitHubExceptions
# ============================================================================


class TestGitHubExceptions:
    """Tests for exception hierarchy."""

    def test_configuration_error_is_github_tool_error(self) -> None:
        """``ConfigurationError`` is a subclass of ``GitHubToolError``."""
        assert issubclass(ConfigurationError, GitHubToolError)

    def test_configuration_error_is_exception(self) -> None:
        """``ConfigurationError`` is a subclass of ``Exception``."""
        assert issubclass(ConfigurationError, Exception)

    def test_configuration_error_message(self) -> None:
        """``ConfigurationError`` preserves its message."""
        msg = "PAT is invalid"
        exc = ConfigurationError(msg)
        assert str(exc) == msg


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Tests for the ``register_tools`` entry-point."""

    def test_register_tools_calls_mcp_tool(self) -> None:
        """``register_tools`` registers exactly 5 tools on the server."""
        registered: list[str] = []

        class FakeMCP:
            """Minimal FastMCP stub for registration testing."""

            def tool(self) -> "FakeMCP":
                return self

            def __call__(self, func: object) -> object:
                name = getattr(func, "__name__", "unknown")
                registered.append(name)
                return func

        fake_mcp: Any = FakeMCP()
        register_tools(fake_mcp)
        assert len(registered) == 5
        assert "github_list_repos" in registered
        assert "github_create_issue" in registered

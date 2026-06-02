"""Tests for Hybrid Websearch — Brave primary with Exa fallback."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.mcp.tools.exa_search import BudgetExceeded
from src.mcp.tools.websearch import register_tools, websearch


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def brave_results() -> list[dict[str, str]]:
    """Sample Brave search results."""
    return [
        {
            "title": "Brave Result 1",
            "url": "https://example.com/1",
            "description": "First Brave result",
        },
    ]


@pytest.fixture()
def exa_results() -> list[dict[str, str]]:
    """Sample Exa search results."""
    return [
        {
            "title": "Exa Result 1",
            "url": "https://example.com/exa1",
            "snippet": "First Exa result",
        },
    ]


# ============================================================================
# TestWebsearch
# ============================================================================


class TestWebsearch:
    """Test hybrid websearch fallback logic."""

    @pytest.mark.asyncio
    async def test_primary_brave_success(
        self, brave_results: list[dict[str, str]]
    ) -> None:
        """Brave returns results -> no fallback."""
        with patch(
            "src.mcp.tools.websearch.brave_search", new_callable=AsyncMock
        ) as mock_brave:
            mock_brave.return_value = brave_results
            result = await websearch("test query")
            assert result["source"] == "brave"
            assert result["fallback_used"] is False
            assert result["results"] == brave_results

    @pytest.mark.asyncio
    async def test_primary_empty_fallback_to_exa(
        self, exa_results: list[dict[str, str]]
    ) -> None:
        """Brave returns empty -> fallback to Exa."""
        with (
            patch(
                "src.mcp.tools.websearch.brave_search",
                new_callable=AsyncMock,
            ) as mock_brave,
            patch(
                "src.mcp.tools.websearch.exa_search",
                new_callable=AsyncMock,
            ) as mock_exa,
        ):
            mock_brave.return_value = []
            mock_exa.return_value = exa_results
            result = await websearch("test query")
            assert result["source"] == "exa"
            assert result["fallback_used"] is True
            assert result["results"] == exa_results

    @pytest.mark.asyncio
    async def test_primary_error_fallback_to_exa(
        self, exa_results: list[dict[str, str]]
    ) -> None:
        """Brave raises error -> fallback to Exa."""
        with (
            patch(
                "src.mcp.tools.websearch.brave_search",
                new_callable=AsyncMock,
            ) as mock_brave,
            patch(
                "src.mcp.tools.websearch.exa_search",
                new_callable=AsyncMock,
            ) as mock_exa,
        ):
            mock_brave.side_effect = Exception("Brave API down")
            mock_exa.return_value = exa_results
            result = await websearch("test query")
            assert result["source"] == "exa"
            assert result["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_both_budget_exceeded(self) -> None:
        """Both services budget exceeded -> return empty with error."""
        with (
            patch(
                "src.mcp.tools.websearch.brave_search",
                new_callable=AsyncMock,
            ) as mock_brave,
            patch(
                "src.mcp.tools.websearch.exa_search",
                new_callable=AsyncMock,
            ) as mock_exa,
        ):
            mock_brave.side_effect = Exception("Rate limited")
            mock_exa.side_effect = BudgetExceeded("Daily cap reached")
            result = await websearch("test query")
            assert result["source"] == "none"
            assert result["fallback_used"] is True
            assert result["error"] == "budget_exceeded"
            assert result["results"] == []

    @pytest.mark.asyncio
    async def test_both_failed_generic_error(self) -> None:
        """Both services fail with generic errors -> return empty with error."""
        with (
            patch(
                "src.mcp.tools.websearch.brave_search",
                new_callable=AsyncMock,
            ) as mock_brave,
            patch(
                "src.mcp.tools.websearch.exa_search",
                new_callable=AsyncMock,
            ) as mock_exa,
        ):
            mock_brave.side_effect = OSError("Network error")
            mock_exa.side_effect = OSError("Network error")
            result = await websearch("test query")
            assert result["source"] == "none"
            assert result["fallback_used"] is True
            assert "error" in result
            assert result["results"] == []

    @pytest.mark.asyncio
    async def test_prefer_exa_uses_exa_first(
        self, exa_results: list[dict[str, str]]
    ) -> None:
        """prefer='exa' -> Exa is primary."""
        with (
            patch(
                "src.mcp.tools.websearch.brave_search",
                new_callable=AsyncMock,
            ) as mock_brave,
            patch(
                "src.mcp.tools.websearch.exa_search",
                new_callable=AsyncMock,
            ) as mock_exa,
        ):
            mock_exa.return_value = exa_results
            result = await websearch("test query", prefer="exa")
            assert result["source"] == "exa"
            assert result["fallback_used"] is False
            mock_brave.assert_not_called()

    @pytest.mark.asyncio
    async def test_count_parameter_passed_through(
        self, brave_results: list[dict[str, str]]
    ) -> None:
        """count parameter passed to underlying search functions."""
        with patch(
            "src.mcp.tools.websearch.brave_search", new_callable=AsyncMock
        ) as mock_brave:
            mock_brave.return_value = brave_results
            await websearch("test query", count=10)
            mock_brave.assert_called_once_with("test query", 10)

    @pytest.mark.asyncio
    async def test_prefer_exa_fallback_to_brave(
        self, brave_results: list[dict[str, str]]
    ) -> None:
        """prefer='exa' with Exa empty -> fallback to Brave."""
        with (
            patch(
                "src.mcp.tools.websearch.brave_search",
                new_callable=AsyncMock,
            ) as mock_brave,
            patch(
                "src.mcp.tools.websearch.exa_search",
                new_callable=AsyncMock,
            ) as mock_exa,
        ):
            mock_exa.return_value = []
            mock_brave.return_value = brave_results
            result = await websearch("test query", prefer="exa")
            assert result["source"] == "brave"
            assert result["fallback_used"] is True
            assert result["results"] == brave_results

    @pytest.mark.asyncio
    async def test_brave_http_error_triggers_fallback(
        self, exa_results: list[dict[str, str]]
    ) -> None:
        """Brave raises httpx.HTTPError -> fallback to Exa."""
        import httpx

        with (
            patch(
                "src.mcp.tools.websearch.brave_search",
                new_callable=AsyncMock,
            ) as mock_brave,
            patch(
                "src.mcp.tools.websearch.exa_search",
                new_callable=AsyncMock,
            ) as mock_exa,
        ):
            mock_brave.side_effect = httpx.HTTPError("Connection timeout")
            mock_exa.return_value = exa_results
            result = await websearch("test query")
            assert result["source"] == "exa"
            assert result["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_brave_redis_error_triggers_fallback(
        self, exa_results: list[dict[str, str]]
    ) -> None:
        """Brave raises redis.RedisError -> fallback to Exa."""
        import redis

        with (
            patch(
                "src.mcp.tools.websearch.brave_search",
                new_callable=AsyncMock,
            ) as mock_brave,
            patch(
                "src.mcp.tools.websearch.exa_search",
                new_callable=AsyncMock,
            ) as mock_exa,
        ):
            mock_brave.side_effect = redis.RedisError("Redis connection failed")
            mock_exa.return_value = exa_results
            result = await websearch("test query")
            assert result["source"] == "exa"
            assert result["fallback_used"] is True


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Tests for the register_tools function."""

    def test_register_tools_calls_mcp_tool(self) -> None:
        """register_tools calls mcp.tool() to register the function."""
        from unittest.mock import MagicMock

        mock_mcp = MagicMock()
        mock_decorator = MagicMock(return_value=lambda f: f)
        mock_mcp.tool.return_value = mock_decorator
        register_tools(mock_mcp)
        mock_mcp.tool.assert_called_once()
        mock_decorator.assert_called_once()

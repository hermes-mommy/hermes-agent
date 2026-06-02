"""Tests for Brave Search MCP Tool — mocked httpx and Redis."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.mcp.tools.brave_search import (
    BraveSearchConfigError,
    _fetch_search,
    _get_api_key,
    _record_cost,
    brave_search,
    register_tools,
)


# ============================================================================
# TestGetApiKey
# ============================================================================


class TestGetApiKey:
    """Tests for the _get_api_key helper."""

    def test_returns_key_when_set(self) -> None:
        """Returns the API key when BRAVE_API_KEY is present."""
        with patch.dict(os.environ, {"BRAVE_API_KEY": "test-key-123"}):
            assert _get_api_key() == "test-key-123"

    def test_raises_when_missing(self) -> None:
        """Raises BraveSearchConfigError when BRAVE_API_KEY is absent."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("BRAVE_API_KEY", None)
            with pytest.raises(BraveSearchConfigError):
                _get_api_key()

    def test_raises_when_empty(self) -> None:
        """Raises BraveSearchConfigError when BRAVE_API_KEY is empty."""
        with patch.dict(os.environ, {"BRAVE_API_KEY": ""}):
            with pytest.raises(BraveSearchConfigError):
                _get_api_key()


# ============================================================================
# TestBraveSearch
# ============================================================================


class TestBraveSearch:
    """Tests for the brave_search tool function."""

    def test_success(self) -> None:
        """Returns parsed results on successful API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Test Title",
                        "url": "https://test.com",
                        "description": "A test result",
                    },
                    {
                        "title": "Another",
                        "url": "https://another.com",
                        "description": "Another result",
                    },
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"BRAVE_API_KEY": "test-key"}),
                patch("src.mcp.tools.brave_search._get_redis_client") as mock_redis,
                patch(
                    "httpx.AsyncClient.get",
                    new=AsyncMock(return_value=mock_response),
                ),
            ):
                mock_redis.return_value = MagicMock()
                results = await brave_search("test query")
                assert len(results) == 2
                assert results[0]["title"] == "Test Title"
                assert results[0]["url"] == "https://test.com"
                assert results[1]["title"] == "Another"

        asyncio.run(_run())

    def test_http_error_returns_empty(self) -> None:
        """Returns empty list on HTTP status errors (4xx/5xx)."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limited", request=MagicMock(), response=mock_response
        )

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"BRAVE_API_KEY": "test-key"}),
                patch("src.mcp.tools.brave_search._get_redis_client"),
                patch(
                    "httpx.AsyncClient.get",
                    new=AsyncMock(return_value=mock_response),
                ),
            ):
                results = await brave_search("test query")
                assert results == []

        asyncio.run(_run())

    def test_connect_error_raises(self) -> None:
        """Raises ConnectError after retries are exhausted."""
        async def _run() -> None:
            with (
                patch.dict(os.environ, {"BRAVE_API_KEY": "test-key"}),
                patch("src.mcp.tools.brave_search._get_redis_client"),
                patch(
                    "httpx.AsyncClient.get",
                    new=AsyncMock(
                        side_effect=httpx.ConnectError("Connection refused")
                    ),
                ),
                patch("asyncio.sleep", new=AsyncMock()),
            ):
                with pytest.raises(httpx.ConnectError):
                    await brave_search("test query")

        asyncio.run(_run())

    def test_missing_api_key_raises(self) -> None:
        """Raises BraveSearchConfigError when API key is missing."""
        async def _run() -> None:
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("BRAVE_API_KEY", None)
                with pytest.raises(BraveSearchConfigError):
                    await brave_search("test query")

        asyncio.run(_run())

    def test_cost_tracking_called(self) -> None:
        """Verifies Redis cost tracking is called on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_response.raise_for_status = MagicMock()

        async def _run() -> None:
            mock_redis_instance = MagicMock()
            with (
                patch.dict(os.environ, {"BRAVE_API_KEY": "test-key"}),
                patch(
                    "src.mcp.tools.brave_search._get_redis_client",
                    return_value=mock_redis_instance,
                ),
                patch(
                    "httpx.AsyncClient.get",
                    new=AsyncMock(return_value=mock_response),
                ),
            ):
                await brave_search("test query")
                mock_redis_instance.incrbyfloat.assert_called_once()

        asyncio.run(_run())

    def test_empty_results(self) -> None:
        """Returns empty list when API returns no results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_response.raise_for_status = MagicMock()

        async def _run() -> None:
            with (
                patch.dict(os.environ, {"BRAVE_API_KEY": "test-key"}),
                patch("src.mcp.tools.brave_search._get_redis_client") as mock_redis,
                patch(
                    "httpx.AsyncClient.get",
                    new=AsyncMock(return_value=mock_response),
                ),
            ):
                mock_redis.return_value = MagicMock()
                results = await brave_search("test query")
                assert results == []

        asyncio.run(_run())


# ============================================================================
# TestRecordCost
# ============================================================================


class TestRecordCost:
    """Tests for the _record_cost helper."""

    def test_incrbyfloat_called_with_correct_key(self) -> None:
        """Redis incrbyfloat is called with the correct key and amount."""
        mock_client = MagicMock()
        _record_cost(mock_client)
        mock_client.incrbyfloat.assert_called_once()
        call_args = mock_client.incrbyfloat.call_args
        key = call_args[0][0]
        assert key.startswith("tool:cost:brave_search:")
        assert call_args[0][1] == 0.01

    def test_key_includes_date(self) -> None:
        """Redis key includes today's date in ISO format."""
        from datetime import date

        mock_client = MagicMock()
        _record_cost(mock_client)
        call_args = mock_client.incrbyfloat.call_args
        key = call_args[0][0]
        today = date.today().isoformat()
        assert today in key


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Tests for the register_tools function."""

    def test_register_tools_calls_mcp_tool(self) -> None:
        """register_tools calls mcp.tool() to register the function."""
        mock_mcp = MagicMock()
        mock_decorator = MagicMock(return_value=lambda f: f)
        mock_mcp.tool.return_value = mock_decorator
        register_tools(mock_mcp)
        mock_mcp.tool.assert_called_once()
        mock_decorator.assert_called_once()


# ============================================================================
# TestFetchSearchRetry
# ============================================================================


class TestFetchSearchRetry:
    """Tests for the retry behavior of _fetch_search."""

    def test_retries_on_connect_error_then_succeeds(self) -> None:
        """Retries on ConnectError and succeeds on third attempt."""
        call_count = 0

        async def mock_get(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection refused")
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"web": {"results": []}}
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        async def _run() -> None:
            with (
                patch("httpx.AsyncClient.get", side_effect=mock_get),
                patch("asyncio.sleep", new=AsyncMock()),
            ):
                results = await _fetch_search("test", 5, "test-key")
                assert results == []
                assert call_count == 3

        asyncio.run(_run())

    def test_exhausts_retries_on_connect_error(self) -> None:
        """Raises ConnectError after all 3 retry attempts fail."""
        async def _run() -> None:
            with (
                patch(
                    "httpx.AsyncClient.get",
                    new=AsyncMock(
                        side_effect=httpx.ConnectError("Connection refused")
                    ),
                ),
                patch("asyncio.sleep", new=AsyncMock()),
            ):
                with pytest.raises(httpx.ConnectError):
                    await _fetch_search("test", 5, "test-key")

        asyncio.run(_run())

    def test_no_retry_on_http_error(self) -> None:
        """Does not retry on HTTPStatusError (raises immediately)."""
        call_count = 0

        async def mock_get(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_resp
            )
            return mock_resp

        async def _run() -> None:
            with patch("httpx.AsyncClient.get", side_effect=mock_get):
                with pytest.raises(httpx.HTTPStatusError):
                    await _fetch_search("test", 5, "test-key")
                assert call_count == 1

        asyncio.run(_run())

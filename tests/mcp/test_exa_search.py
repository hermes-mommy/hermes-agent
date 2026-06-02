"""Tests for Exa Search MCP tool — budget cap, API calls, error handling."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Set required env vars BEFORE importing the module under test.
os.environ.setdefault("EXA_API_KEY", "test-exa-key-for-unit-tests")

from src.mcp.tools.exa_search import (  # noqa: E402
    BudgetExceeded,
    ConfigurationError,
    _COST_PER_REQUEST,
    _DAILY_CAP,
    _REDIS_KEY_PREFIX,
    _call_exa_api,
    _check_budget,
    _daily_cost_key,
    _get_api_key,
    _record_cost,
    exa_search,
    register_tools,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_redis(
    get_return_value: str | None = None,
) -> tuple[AsyncMock, MagicMock]:
    """Create a mock async Redis client with pipeline support."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=get_return_value)
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[True, True])
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)
    mock_redis.aclose = AsyncMock()
    return mock_redis, mock_pipe


def _make_exa_response(results: list[dict[str, str]]) -> dict[str, object]:
    """Build a fake Exa API response payload."""
    return {
        "results": [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "text": r.get("snippet", ""),
            }
            for r in results
        ],
    }


# ============================================================================
# TestBudgetExceeded
# ============================================================================


class TestBudgetExceeded:
    """Tests for the ``BudgetExceeded`` exception class."""

    def test_is_exception(self) -> None:
        assert issubclass(BudgetExceeded, Exception)

    def test_preserves_message(self) -> None:
        exc = BudgetExceeded("cap reached: $5.00")
        assert str(exc) == "cap reached: $5.00"


# ============================================================================
# TestConfigurationError
# ============================================================================


class TestConfigurationError:
    """Tests for the ``ConfigurationError`` exception class."""

    def test_is_exception(self) -> None:
        assert issubclass(ConfigurationError, Exception)

    def test_missing_api_key_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("EXA_API_KEY", None)
            with pytest.raises(ConfigurationError, match="EXA_API_KEY"):
                _get_api_key()

    def test_present_api_key_returns(self) -> None:
        with patch.dict(os.environ, {"EXA_API_KEY": "my-secret-key"}):
            assert _get_api_key() == "my-secret-key"


# ============================================================================
# TestDailyCostKey
# ============================================================================


class TestDailyCostKey:
    """Tests for the Redis key format."""

    def test_key_format(self) -> None:
        today = date.today().isoformat()
        expected = f"{_REDIS_KEY_PREFIX}:{today}"
        assert _daily_cost_key() == expected


# ============================================================================
# TestCheckBudget
# ============================================================================


class TestCheckBudget:
    """Tests for the pre-API-call budget check."""

    def test_passes_when_no_prior_spend(self) -> None:
        """No existing key means $0 spend — should pass."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value=None)
            await _check_budget(mock_redis)

        asyncio.run(_run())

    def test_passes_at_boundary(self) -> None:
        """$4.999 is below $5 cap — should pass."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value="4.999")
            await _check_budget(mock_redis)

        asyncio.run(_run())

    def test_raises_at_cap(self) -> None:
        """$5.000 meets the cap — should raise BudgetExceeded."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value="5.0")
            with pytest.raises(BudgetExceeded, match="Daily budget cap"):
                await _check_budget(mock_redis)

        asyncio.run(_run())

    def test_raises_above_cap(self) -> None:
        """$6.50 exceeds the cap — should raise BudgetExceeded."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value="6.50")
            with pytest.raises(BudgetExceeded):
                await _check_budget(mock_redis)

        asyncio.run(_run())


# ============================================================================
# TestRecordCost
# ============================================================================


class TestRecordCost:
    """Tests for the post-API-call cost recording via pipeline."""

    def test_incrbyfloat_called(self) -> None:
        """INCRBYFLOAT is used to record the cost."""

        async def _run() -> None:
            mock_redis, mock_pipe = _make_mock_redis()
            await _record_cost(mock_redis, _COST_PER_REQUEST)

            mock_pipe.incrbyfloat.assert_called_once()
            call_args = mock_pipe.incrbyfloat.call_args
            assert call_args[0][0] == _daily_cost_key()
            assert call_args[0][1] == _COST_PER_REQUEST

        asyncio.run(_run())

    def test_pipeline_execute_called(self) -> None:
        """Pipeline execute is called to commit the cost."""

        async def _run() -> None:
            mock_redis, mock_pipe = _make_mock_redis()
            await _record_cost(mock_redis, _COST_PER_REQUEST)
            mock_pipe.execute.assert_called_once()

        asyncio.run(_run())

    def test_expire_set_on_key(self) -> None:
        """TTL is set on the cost key for cleanup."""

        async def _run() -> None:
            mock_redis, mock_pipe = _make_mock_redis()
            await _record_cost(mock_redis, _COST_PER_REQUEST)
            mock_pipe.expire.assert_called_once()

        asyncio.run(_run())


# ============================================================================
# TestExaSearchSuccess
# ============================================================================


class TestExaSearchSuccess:
    """Tests for successful search flow."""

    def test_returns_parsed_results(self) -> None:
        """Successful search returns parsed title/url/snippet dicts."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value=None)
            expected = [
                {"title": "Test", "url": "https://ex.com", "snippet": "body"},
            ]

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=AsyncMock(return_value=expected),
                ),
            ):
                results = await exa_search(query="test query")

            assert results == expected

        asyncio.run(_run())

    def test_default_num_results(self) -> None:
        """Default num_results=10 is passed to the API."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value=None)
            mock_api = AsyncMock(return_value=[])

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=mock_api,
                ),
            ):
                await exa_search(query="test")

            call_kwargs = mock_api.call_args
            assert call_kwargs[0][2] == 10  # num_results positional arg

        asyncio.run(_run())

    def test_cost_recorded_after_success(self) -> None:
        """Cost is recorded via pipeline after successful API call."""

        async def _run() -> None:
            mock_redis, mock_pipe = _make_mock_redis(get_return_value=None)

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=AsyncMock(return_value=[]),
                ),
            ):
                await exa_search(query="test")

            mock_pipe.incrbyfloat.assert_called_once()

        asyncio.run(_run())

    def test_redis_closed_in_finally(self) -> None:
        """Redis connection is closed even on success."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value=None)

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=AsyncMock(return_value=[]),
                ),
            ):
                await exa_search(query="test")

            mock_redis.aclose.assert_called_once()

        asyncio.run(_run())


# ============================================================================
# TestExaSearchBudgetCap
# ============================================================================


class TestExaSearchBudgetCap:
    """Tests for $5/day cap enforcement in the full search flow."""

    def test_cap_enforced_at_5_dollars(self) -> None:
        """When Redis shows $5.00, search raises BudgetExceeded."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value="5.0")

            with patch(
                "src.mcp.tools.exa_search._get_redis",
                return_value=mock_redis,
            ):
                with pytest.raises(BudgetExceeded):
                    await exa_search(query="test")

        asyncio.run(_run())

    def test_boundary_4_999_passes(self) -> None:
        """$4.999 is below cap — search proceeds."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value="4.999")

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=AsyncMock(return_value=[]),
                ),
            ):
                results = await exa_search(query="test")

            assert isinstance(results, list)

        asyncio.run(_run())

    def test_budget_exceeded_message_contains_amounts(self) -> None:
        """BudgetExceeded message includes current spend and cap."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value="5.123")

            with patch(
                "src.mcp.tools.exa_search._get_redis",
                return_value=mock_redis,
            ):
                with pytest.raises(BudgetExceeded, match=r"\$5\.12.*\$5\.00"):
                    await exa_search(query="test")

        asyncio.run(_run())

    def test_no_api_call_when_budget_exceeded(self) -> None:
        """API is NOT called when budget is already exceeded."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value="5.0")
            mock_api = AsyncMock(return_value=[])

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=mock_api,
                ),
            ):
                with pytest.raises(BudgetExceeded):
                    await exa_search(query="test")

            mock_api.assert_not_called()

        asyncio.run(_run())


# ============================================================================
# TestExaSearchErrorHandling
# ============================================================================


class TestExaSearchErrorHandling:
    """Tests for HTTP and transport error handling."""

    def test_429_returns_empty_list(self) -> None:
        """HTTP 429 (rate limit) returns empty list, not an error."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value=None)
            mock_response = MagicMock()
            mock_response.status_code = 429
            error = httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=MagicMock(),
                response=mock_response,
            )

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=AsyncMock(side_effect=error),
                ),
            ):
                results = await exa_search(query="test")

            assert results == []

        asyncio.run(_run())

    def test_other_http_error_raises(self) -> None:
        """Non-429 HTTP errors propagate to the caller."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value=None)
            mock_response = MagicMock()
            mock_response.status_code = 500
            error = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=MagicMock(),
                response=mock_response,
            )

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=AsyncMock(side_effect=error),
                ),
            ):
                with pytest.raises(httpx.HTTPStatusError):
                    await exa_search(query="test")

        asyncio.run(_run())

    def test_transport_error_raises(self) -> None:
        """Transport errors (after retries exhausted) propagate."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value=None)
            error = httpx.ConnectError("Connection refused")

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=AsyncMock(side_effect=error),
                ),
            ):
                with pytest.raises(httpx.ConnectError):
                    await exa_search(query="test")

        asyncio.run(_run())

    def test_redis_closed_on_error(self) -> None:
        """Redis connection is closed even when errors occur."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis(get_return_value=None)
            mock_response = MagicMock()
            mock_response.status_code = 500
            error = httpx.HTTPStatusError(
                "500", request=MagicMock(), response=mock_response
            )

            with (
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
                patch(
                    "src.mcp.tools.exa_search._call_exa_api",
                    new=AsyncMock(side_effect=error),
                ),
            ):
                with pytest.raises(httpx.HTTPStatusError):
                    await exa_search(query="test")

            mock_redis.aclose.assert_called_once()

        asyncio.run(_run())

    def test_missing_api_key_raises_configuration_error(self) -> None:
        """Missing EXA_API_KEY raises ConfigurationError."""

        async def _run() -> None:
            mock_redis, _ = _make_mock_redis()

            with (
                patch.dict(os.environ, {}, clear=True),
                patch(
                    "src.mcp.tools.exa_search._get_redis",
                    return_value=mock_redis,
                ),
            ):
                os.environ.pop("EXA_API_KEY", None)
                with pytest.raises(ConfigurationError, match="EXA_API_KEY"):
                    await exa_search(query="test")

        asyncio.run(_run())


# ============================================================================
# TestCallExaApi
# ============================================================================


class TestCallExaApi:
    """Tests for the raw API call function."""

    def test_parses_results(self) -> None:
        """Response JSON is parsed into title/url/snippet dicts."""

        async def _run() -> None:
            mock_response = MagicMock()
            mock_response.json.return_value = _make_exa_response(
                [{"title": "Hello", "url": "https://x.com", "snippet": "world"}]
            )
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            results = await _call_exa_api(
                mock_client, "test", 10, "fake-key"
            )

            assert len(results) == 1
            assert results[0]["title"] == "Hello"
            assert results[0]["url"] == "https://x.com"
            assert results[0]["snippet"] == "world"

        asyncio.run(_run())

    def test_sends_correct_headers(self) -> None:
        """API key is sent via x-api-key header."""

        async def _run() -> None:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            await _call_exa_api(mock_client, "query", 5, "my-api-key")

            call_kwargs = mock_client.post.call_args
            assert call_kwargs[1]["headers"]["x-api-key"] == "my-api-key"

        asyncio.run(_run())

    def test_sends_correct_payload(self) -> None:
        """Request body includes query and numResults."""

        async def _run() -> None:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            await _call_exa_api(mock_client, "my search", 3, "key")

            call_kwargs = mock_client.post.call_args
            payload = call_kwargs[1]["json"]
            assert payload["query"] == "my search"
            assert payload["numResults"] == 3

        asyncio.run(_run())

    def test_empty_results_returns_empty_list(self) -> None:
        """API returning no results yields an empty list."""

        async def _run() -> None:
            mock_response = MagicMock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            results = await _call_exa_api(mock_client, "test", 10, "key")
            assert results == []

        asyncio.run(_run())


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Tests for the ``register_tools`` entry-point."""

    def test_registers_with_mcp(self) -> None:
        """register_tools calls mcp.tool() to register exa_search."""
        mock_mcp = MagicMock()
        mock_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_decorator

        register_tools(mock_mcp)

        mock_mcp.tool.assert_called_once()
        mock_decorator.assert_called_once()

    def test_callable(self) -> None:
        """register_tools is callable with a FastMCP argument."""
        assert callable(register_tools)


# ============================================================================
# TestConstants
# ============================================================================


class TestConstants:
    """Tests for module-level constants."""

    def test_cost_per_request(self) -> None:
        assert _COST_PER_REQUEST == 0.007

    def test_daily_cap(self) -> None:
        assert _DAILY_CAP == 5.0

    def test_redis_key_prefix(self) -> None:
        assert _REDIS_KEY_PREFIX == "tool:cost:exa"

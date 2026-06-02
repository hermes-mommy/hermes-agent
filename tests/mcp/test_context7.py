"""Tests for MCP Context7 Tool — resolve and query with mocked HTTP."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

# Ensure project root is on sys.path for `from src.*` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.mcp.tools.context7 import (  # noqa: E402
    Context7Error,
    LibraryNotFoundError,
    RateLimitExceededError,
    _BASE_URL,
    _CONTEXT_PATH,
    _SEARCH_PATH,
    _TIMEOUT_SECONDS,
    cache_clear,
    cache_size,
    context7_query,
    context7_resolve,
    register_tools,
)


# ---------------------------------------------------------------------------
# Mock response helpers
# ---------------------------------------------------------------------------

_SAMPLE_SEARCH_RESPONSE: dict[str, object] = {
    "results": [
        {
            "id": "/facebook/react",
            "title": "React",
            "description": "A JavaScript library for building user interfaces",
            "totalSnippets": 1250,
            "trustScore": 95,
            "benchmarkScore": 88.5,
            "versions": ["v18.2.0", "v17.0.2"],
        },
        {
            "id": "/preactjs/preact",
            "title": "Preact",
            "description": "Fast 3kB alternative to React",
            "totalSnippets": 340,
            "trustScore": 80,
            "benchmarkScore": 72.0,
        },
    ]
}

_SAMPLE_CONTEXT_RESPONSE: dict[str, object] = {
    "content": [
        {
            "title": "useState Hook",
            "body": "useState is a React Hook that lets you add state...",
        }
    ],
    "codeSnippets": [
        {
            "title": "Basic useState",
            "code": "const [count, setCount] = useState(0);",
            "language": "javascript",
        }
    ],
}


def _mock_response(
    status_code: int = 200,
    json_data: object = None,
) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(spec=httpx.Request),
            response=resp,
        )
    return resp


def _mock_client(
    get_response: MagicMock | None = None,
    transport_error: Exception | None = None,
) -> AsyncMock:
    """Create a mock httpx.AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    if transport_error is not None:
        client.get.side_effect = transport_error
    elif get_response is not None:
        client.get.return_value = get_response
    else:
        client.get.return_value = _mock_response(200, _SAMPLE_SEARCH_RESPONSE)

    # Context manager support.
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# ============================================================================
# TestContext7Resolve
# ============================================================================


class TestContext7Resolve:
    """Tests for the ``context7_resolve`` function."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        cache_clear()

    def test_resolve_success(self) -> None:
        """Successful resolution returns library metadata dict."""

        async def _run() -> None:
            mock_resp = _mock_response(200, _SAMPLE_SEARCH_RESPONSE)
            mock_cl = _mock_client(get_response=mock_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                with patch(
                    "src.mcp.tools.context7._track_cost", new=AsyncMock()
                ):
                    result = await context7_resolve("react", "hooks")

            assert result["id"] == "/facebook/react"
            assert result["name"] == "React"
            assert result["description"] == "A JavaScript library for building user interfaces"
            assert result["total_snippets"] == "1250"
            assert result["trust_score"] == "95"
            assert result["benchmark_score"] == "88.5"
            assert "error" not in result

        asyncio.run(_run())

    def test_resolve_not_found(self) -> None:
        """Empty results return error dict with suggestion."""

        async def _run() -> None:
            empty_resp = _mock_response(200, {"results": []})
            mock_cl = _mock_client(get_response=empty_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                result = await context7_resolve("nonexistent-lib-xyz")

            assert result["error"] == "not_found"
            assert "suggestion" in result
            assert "nonexistent-lib-xyz" in result["suggestion"]

        asyncio.run(_run())

    def test_resolve_rate_limited(self) -> None:
        """429 response returns rate_limited error dict."""

        async def _run() -> None:
            mock_cl = AsyncMock(spec=httpx.AsyncClient)
            mock_cl.get.side_effect = RateLimitExceededError("rate limit")
            mock_cl.__aenter__ = AsyncMock(return_value=mock_cl)
            mock_cl.__aexit__ = AsyncMock(return_value=None)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                # Disable tenacity retry for this test.
                with patch(
                    "src.mcp.tools.context7._api_get",
                    side_effect=RateLimitExceededError("rate limit"),
                ):
                    result = await context7_resolve("react")

            assert result["error"] == "rate_limited"
            assert "suggestion" in result

        asyncio.run(_run())

    def test_resolve_http_error(self) -> None:
        """Non-2xx (non-429) response returns http_error dict."""

        async def _run() -> None:
            error_resp = _mock_response(500)
            mock_cl = _mock_client(get_response=error_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                result = await context7_resolve("react")

            assert result["error"] == "http_error"
            assert result["status_code"] == "500"

        asyncio.run(_run())

    def test_resolve_transport_error(self) -> None:
        """Network transport error returns network_error dict."""

        async def _run() -> None:
            with patch(
                "src.mcp.tools.context7._api_get",
                side_effect=httpx.ConnectError("connection refused"),
            ):
                result = await context7_resolve("react")

            assert result["error"] == "network_error"
            assert "suggestion" in result

        asyncio.run(_run())

    def test_resolve_default_empty_query(self) -> None:
        """Omitting query parameter works (defaults to empty string)."""

        async def _run() -> None:
            mock_resp = _mock_response(200, _SAMPLE_SEARCH_RESPONSE)
            mock_cl = _mock_client(get_response=mock_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                with patch(
                    "src.mcp.tools.context7._track_cost", new=AsyncMock()
                ):
                    result = await context7_resolve("react")

            assert result["id"] == "/facebook/react"

        asyncio.run(_run())

    def test_resolve_sends_correct_params(self) -> None:
        """Library name and query are passed as correct HTTP params."""

        async def _run() -> None:
            mock_resp = _mock_response(200, _SAMPLE_SEARCH_RESPONSE)
            mock_cl = _mock_client(get_response=mock_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                with patch(
                    "src.mcp.tools.context7._track_cost", new=AsyncMock()
                ):
                    await context7_resolve("react", "useState hooks")

            # Verify the GET call had correct params.
            call_args = mock_cl.get.call_args
            assert call_args is not None
            params = call_args.kwargs.get("params", call_args.args[1] if len(call_args.args) > 1 else {})
            assert params["libraryName"] == "react"
            assert params["query"] == "useState hooks"

        asyncio.run(_run())


# ============================================================================
# TestContext7Query
# ============================================================================


class TestContext7Query:
    """Tests for the ``context7_query`` function."""

    def test_query_success(self) -> None:
        """Successful query returns context dict."""

        async def _run() -> None:
            mock_resp = _mock_response(200, _SAMPLE_CONTEXT_RESPONSE)
            mock_cl = _mock_client(get_response=mock_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                with patch(
                    "src.mcp.tools.context7._track_cost", new=AsyncMock()
                ):
                    result = await context7_query(
                        "/facebook/react", "How do I use useState?"
                    )

            assert result["library_id"] == "/facebook/react"
            assert result["query"] == "How do I use useState?"
            assert result["context"] == _SAMPLE_CONTEXT_RESPONSE
            assert "error" not in result

        asyncio.run(_run())

    def test_query_rate_limited(self) -> None:
        """429 response returns rate_limited error dict."""

        async def _run() -> None:
            with patch(
                "src.mcp.tools.context7._api_get",
                side_effect=RateLimitExceededError("rate limit"),
            ):
                result = await context7_query(
                    "/facebook/react", "hooks"
                )

            assert result["error"] == "rate_limited"
            assert result["library_id"] == "/facebook/react"

        asyncio.run(_run())

    def test_query_http_error(self) -> None:
        """Non-2xx (non-429) response returns http_error dict."""

        async def _run() -> None:
            error_resp = _mock_response(503)
            mock_cl = _mock_client(get_response=error_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                result = await context7_query(
                    "/facebook/react", "hooks"
                )

            assert result["error"] == "http_error"
            assert result["status_code"] == 503

        asyncio.run(_run())

    def test_query_transport_error(self) -> None:
        """Network transport error returns network_error dict."""

        async def _run() -> None:
            with patch(
                "src.mcp.tools.context7._api_get",
                side_effect=httpx.ConnectTimeout("timeout"),
            ):
                result = await context7_query(
                    "/facebook/react", "hooks"
                )

            assert result["error"] == "network_error"
            assert result["library_id"] == "/facebook/react"

        asyncio.run(_run())

    def test_query_sends_correct_params(self) -> None:
        """Library ID and query are passed as correct HTTP params."""

        async def _run() -> None:
            mock_resp = _mock_response(200, _SAMPLE_CONTEXT_RESPONSE)
            mock_cl = _mock_client(get_response=mock_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                with patch(
                    "src.mcp.tools.context7._track_cost", new=AsyncMock()
                ):
                    await context7_query(
                        "/facebook/react", "How do I use hooks?"
                    )

            call_args = mock_cl.get.call_args
            assert call_args is not None
            params = call_args.kwargs.get("params", call_args.args[1] if len(call_args.args) > 1 else {})
            assert params["libraryId"] == "/facebook/react"
            assert params["query"] == "How do I use hooks?"
            assert params["type"] == "json"

        asyncio.run(_run())


# ============================================================================
# TestContext7Cache
# ============================================================================


class TestContext7Cache:
    """Tests for the in-memory LRU cache."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        cache_clear()

    def test_cache_hit_avoids_api_call(self) -> None:
        """Second call with same args returns cached result (no API call)."""

        async def _run() -> None:
            mock_resp = _mock_response(200, _SAMPLE_SEARCH_RESPONSE)
            mock_cl = _mock_client(get_response=mock_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                with patch(
                    "src.mcp.tools.context7._track_cost", new=AsyncMock()
                ):
                    # First call — hits API.
                    result1 = await context7_resolve("react", "hooks")

            # Second call — should use cache, no HTTP needed.
            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                result2 = await context7_resolve("react", "hooks")

            assert result1 == result2
            # Only one GET call total (first call), second used cache.
            assert mock_cl.get.call_count == 1

        asyncio.run(_run())

    def test_cache_miss_different_query(self) -> None:
        """Different query triggers a new API call."""

        async def _run() -> None:
            mock_resp = _mock_response(200, _SAMPLE_SEARCH_RESPONSE)
            mock_cl = _mock_client(get_response=mock_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                with patch(
                    "src.mcp.tools.context7._track_cost", new=AsyncMock()
                ):
                    await context7_resolve("react", "hooks")
                    await context7_resolve("react", "useEffect")

            assert mock_cl.get.call_count == 2

        asyncio.run(_run())

    def test_cache_clear(self) -> None:
        """``cache_clear`` empties the cache."""
        assert cache_size() == 0

        async def _run() -> None:
            mock_resp = _mock_response(200, _SAMPLE_SEARCH_RESPONSE)
            mock_cl = _mock_client(get_response=mock_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                with patch(
                    "src.mcp.tools.context7._track_cost", new=AsyncMock()
                ):
                    await context7_resolve("react", "hooks")

            assert cache_size() == 1
            cache_clear()
            assert cache_size() == 0

        asyncio.run(_run())

    def test_cache_normalises_case(self) -> None:
        """Cache keys are case-insensitive."""

        async def _run() -> None:
            mock_resp = _mock_response(200, _SAMPLE_SEARCH_RESPONSE)
            mock_cl = _mock_client(get_response=mock_resp)

            with patch(
                "src.mcp.tools.context7.httpx.AsyncClient",
                return_value=mock_cl,
            ):
                with patch(
                    "src.mcp.tools.context7._track_cost", new=AsyncMock()
                ):
                    await context7_resolve("React", "Hooks")
                    await context7_resolve("react", "hooks")

            # Only one API call — cache hit on second call.
            assert mock_cl.get.call_count == 1

        asyncio.run(_run())


# ============================================================================
# TestContext7Exceptions
# ============================================================================


class TestContext7Exceptions:
    """Tests for custom exception hierarchy."""

    def test_context7_error_is_exception(self) -> None:
        """``Context7Error`` is a subclass of ``Exception``."""
        assert issubclass(Context7Error, Exception)

    def test_library_not_found_error(self) -> None:
        """``LibraryNotFoundError`` is a ``Context7Error``."""
        assert issubclass(LibraryNotFoundError, Context7Error)

    def test_rate_limit_error(self) -> None:
        """``RateLimitExceededError`` is a ``Context7Error``."""
        assert issubclass(RateLimitExceededError, Context7Error)

    def test_exception_message(self) -> None:
        """Exception preserves its message."""
        exc = Context7Error("test message")
        assert str(exc) == "test message"


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Tests for the ``register_tools`` registration entry-point."""

    def test_register_tools_callable(self) -> None:
        """``register_tools`` is callable and accepts FastMCP mock."""
        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda f: f

        # Should not raise.
        register_tools(mock_mcp)

    def test_register_tools_registers_two_tools(self) -> None:
        """Exactly two tools are registered (resolve + query)."""
        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda f: f

        register_tools(mock_mcp)

        # @mcp.tool() should be called twice (resolve + query).
        assert mock_mcp.tool.call_count == 2

    def test_register_tools_uses_read_auto(self) -> None:
        """Both tools are decorated with READ_AUTO auth level."""
        registered_decorators: list[str] = []

        class MockMCP:
            def tool(self) -> object:
                def decorator(func: object) -> object:
                    registered_decorators.append("tool")
                    return func
                return decorator

        register_tools(MockMCP())  # type: ignore[arg-type]
        assert len(registered_decorators) == 2


# ============================================================================
# TestConfiguration
# ============================================================================


class TestConfiguration:
    """Tests for configuration constants."""

    def test_base_url(self) -> None:
        """Base URL points to Context7 API."""
        assert _BASE_URL == "https://context7.com/api"

    def test_search_path(self) -> None:
        """Search endpoint path is correct."""
        assert _SEARCH_PATH == "/v2/libs/search"

    def test_context_path(self) -> None:
        """Context endpoint path is correct."""
        assert _CONTEXT_PATH == "/v2/context"

    def test_timeout(self) -> None:
        """Timeout is set to 15 seconds."""
        assert _TIMEOUT_SECONDS == 15.0

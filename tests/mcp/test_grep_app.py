"""Tests for grep.app MCP Tool — mocked httpx responses."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.mcp.tools.grep_app import (
    _fetch_search,
    _parse_hits,
    grep_app_search,
    register_tools,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_RESPONSE: dict[str, object] = {
    "hits": {
        "hits": [
            {
                "repo": {
                    "repo": {"raw": "owner/my-repo"},
                    "branch": {"raw": "main"},
                    "path": {"raw": "src/app.py"},
                },
                "content": {
                    "lines": [
                        {"num": 10, "line": "def hello():"},
                        {"num": 11, "line": "    return 'world'"},
                    ],
                },
            },
            {
                "repo": {
                    "repo": {"raw": "other/project"},
                    "branch": {"raw": "develop"},
                    "path": {"raw": "lib/utils.py"},
                },
                "content": {
                    "lines": [
                        {"num": 42, "line": "hello = True"},
                    ],
                },
            },
        ],
    },
}

_EMPTY_RESPONSE: dict[str, object] = {"hits": {"hits": []}}


def _mock_response(
    json_data: dict[str, object],
    status_code: int = 200,
) -> MagicMock:
    """Build a mock httpx.Response."""
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


# ============================================================================
# TestParseHits
# ============================================================================


class TestParseHits:
    """Tests for the _parse_hits response parser."""

    def test_parses_multiple_results(self) -> None:
        """Correctly parses multiple hit entries."""
        results = _parse_hits(_SAMPLE_RESPONSE)
        assert len(results) == 2
        assert results[0]["repo"] == "owner/my-repo"
        assert results[0]["branch"] == "main"
        assert results[0]["path"] == "src/app.py"
        assert "10:def hello():" in results[0]["lines"]
        assert "11:    return 'world'" in results[0]["lines"]

    def test_second_result(self) -> None:
        """Second result is parsed correctly."""
        results = _parse_hits(_SAMPLE_RESPONSE)
        assert results[1]["repo"] == "other/project"
        assert results[1]["branch"] == "develop"
        assert results[1]["path"] == "lib/utils.py"
        assert results[1]["lines"] == "42:hello = True"

    def test_empty_hits(self) -> None:
        """Returns empty list when no hits."""
        results = _parse_hits(_EMPTY_RESPONSE)
        assert results == []

    def test_missing_hits_key(self) -> None:
        """Returns empty list when 'hits' key is absent."""
        results = _parse_hits({})
        assert results == []

    def test_hits_not_dict(self) -> None:
        """Returns empty list when 'hits' is not a dict."""
        results = _parse_hits({"hits": "invalid"})
        assert results == []

    def test_inner_hits_not_list(self) -> None:
        """Returns empty list when inner hits is not a list."""
        results = _parse_hits({"hits": {"hits": "not-a-list"}})
        assert results == []

    def test_malformed_hit_skipped(self) -> None:
        """Malformed individual hit entries are skipped gracefully."""
        data: dict[str, object] = {
            "hits": {
                "hits": [
                    "not-a-dict",
                    {"repo": "not-a-dict", "content": {}},
                    {
                        "repo": {
                            "repo": {"raw": "good/repo"},
                            "branch": {"raw": "main"},
                            "path": {"raw": "file.py"},
                        },
                        "content": {"lines": [{"num": 1, "line": "ok"}]},
                    },
                ],
            },
        }
        results = _parse_hits(data)
        assert len(results) == 1
        assert results[0]["repo"] == "good/repo"

    def test_missing_content_lines(self) -> None:
        """Hit with missing lines produces empty lines string."""
        data: dict[str, object] = {
            "hits": {
                "hits": [
                    {
                        "repo": {
                            "repo": {"raw": "owner/repo"},
                            "branch": {"raw": "main"},
                            "path": {"raw": "test.py"},
                        },
                        "content": {},
                    },
                ],
            },
        }
        results = _parse_hits(data)
        assert len(results) == 1
        assert results[0]["lines"] == ""


# ============================================================================
# TestGrepAppSearch
# ============================================================================


class TestGrepAppSearch:
    """Tests for the grep_app_search tool function."""

    def test_success_returns_results(self) -> None:
        """Returns parsed results on a successful API call."""
        mock_resp = _mock_response(_SAMPLE_RESPONSE)

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ):
                results = await grep_app_search("hello")
                assert len(results) == 2
                assert results[0]["repo"] == "owner/my-repo"
                assert results[1]["repo"] == "other/project"

        asyncio.run(_run())

    def test_empty_results_returns_empty_list(self) -> None:
        """Returns empty list when API returns no hits."""
        mock_resp = _mock_response(_EMPTY_RESPONSE)

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ):
                results = await grep_app_search("nonexistent_pattern")
                assert results == []

        asyncio.run(_run())

    def test_language_filter_included(self) -> None:
        """Language filter parameters are passed to the API."""
        mock_resp = _mock_response(_EMPTY_RESPONSE)

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ) as mock_get:
                await grep_app_search("query", language=["Python", "Go"])
                call_kwargs = mock_get.call_args
                params = call_kwargs.kwargs.get(
                    "params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
                )
                assert params["filters[lang][0]"] == "Python"
                assert params["filters[lang][1]"] == "Go"

        asyncio.run(_run())

    def test_repo_filter_included(self) -> None:
        """Repo filter parameter is passed to the API."""
        mock_resp = _mock_response(_EMPTY_RESPONSE)

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ) as mock_get:
                await grep_app_search("query", repo="owner/repo")
                call_kwargs = mock_get.call_args
                params = call_kwargs.kwargs.get(
                    "params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
                )
                assert params["filters[repo][0]"] == "owner/repo"

        asyncio.run(_run())

    def test_regex_mode(self) -> None:
        """use_regexp=True sets the regexp parameter correctly."""
        mock_resp = _mock_response(_EMPTY_RESPONSE)

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ) as mock_get:
                await grep_app_search("def.*test", use_regexp=True)
                call_kwargs = mock_get.call_args
                params = call_kwargs.kwargs.get(
                    "params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
                )
                assert params["regexp"] == "true"

        asyncio.run(_run())

    def test_regex_default_false(self) -> None:
        """use_regexp defaults to False."""
        mock_resp = _mock_response(_EMPTY_RESPONSE)

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ) as mock_get:
                await grep_app_search("query")
                call_kwargs = mock_get.call_args
                params = call_kwargs.kwargs.get(
                    "params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
                )
                assert params["regexp"] == "false"

        asyncio.run(_run())

    def test_http_error_returns_empty(self) -> None:
        """Returns empty list on HTTP status errors."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_resp
        )

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ):
                results = await grep_app_search("query")
                assert results == []

        asyncio.run(_run())

    def test_connect_error_returns_empty(self) -> None:
        """Returns empty list after connect errors exhaust retries."""
        async def _run() -> None:
            with (
                patch(
                    "httpx.AsyncClient.get",
                    new=AsyncMock(
                        side_effect=httpx.ConnectError("Connection refused"),
                    ),
                ),
                patch("asyncio.sleep", new=AsyncMock()),
            ):
                results = await grep_app_search("query")
                assert results == []

        asyncio.run(_run())

    def test_generic_http_error_returns_empty(self) -> None:
        """Returns empty list on generic httpx.HTTPError."""
        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(
                    side_effect=httpx.ReadTimeout("Read timed out"),
                ),
            ):
                results = await grep_app_search("query")
                assert results == []

        asyncio.run(_run())

    def test_match_case_default_true(self) -> None:
        """match_case defaults to True."""
        mock_resp = _mock_response(_EMPTY_RESPONSE)

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ) as mock_get:
                await grep_app_search("query")
                call_kwargs = mock_get.call_args
                params = call_kwargs.kwargs.get(
                    "params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
                )
                assert params["case"] == "true"

        asyncio.run(_run())

    def test_match_case_false(self) -> None:
        """match_case=False sets case parameter correctly."""
        mock_resp = _mock_response(_EMPTY_RESPONSE)

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ) as mock_get:
                await grep_app_search("query", match_case=False)
                call_kwargs = mock_get.call_args
                params = call_kwargs.kwargs.get(
                    "params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
                )
                assert params["case"] == "false"

        asyncio.run(_run())

    def test_combined_filters(self) -> None:
        """All filters can be combined in a single request."""
        mock_resp = _mock_response(_SAMPLE_RESPONSE)

        async def _run() -> None:
            with patch(
                "httpx.AsyncClient.get",
                new=AsyncMock(return_value=mock_resp),
            ) as mock_get:
                results = await grep_app_search(
                    "pattern",
                    language=["TypeScript"],
                    repo="vercel/next.js",
                    use_regexp=True,
                    match_case=False,
                )
                call_kwargs = mock_get.call_args
                params = call_kwargs.kwargs.get(
                    "params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
                )
                assert params["q"] == "pattern"
                assert params["regexp"] == "true"
                assert params["case"] == "false"
                assert params["filters[lang][0]"] == "TypeScript"
                assert params["filters[repo][0]"] == "vercel/next.js"
                assert len(results) == 2

        asyncio.run(_run())


# ============================================================================
# TestFetchSearchRetry
# ============================================================================


class TestFetchSearchRetry:
    """Tests for the retry behavior of _fetch_search."""

    def test_retries_on_connect_error_then_succeeds(self) -> None:
        """Retries on ConnectError and succeeds on second attempt."""
        call_count = 0

        async def mock_get(
            *args: object, **kwargs: object
        ) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection refused")
            return _mock_response(_EMPTY_RESPONSE)

        async def _run() -> None:
            with (
                patch("httpx.AsyncClient.get", side_effect=mock_get),
                patch("asyncio.sleep", new=AsyncMock()),
            ):
                results = await _fetch_search(
                    "test", None, None, False, True
                )
                assert results == []
                assert call_count == 2

        asyncio.run(_run())

    def test_exhausts_retries_on_connect_error(self) -> None:
        """Raises ConnectError after all retry attempts fail."""
        async def _run() -> None:
            with (
                patch(
                    "httpx.AsyncClient.get",
                    new=AsyncMock(
                        side_effect=httpx.ConnectError("Connection refused"),
                    ),
                ),
                patch("asyncio.sleep", new=AsyncMock()),
            ):
                with pytest.raises(httpx.ConnectError):
                    await _fetch_search("test", None, None, False, True)

        asyncio.run(_run())

    def test_no_retry_on_http_error(self) -> None:
        """Does not retry on HTTPStatusError (raises immediately)."""
        call_count = 0

        async def mock_get(
            *args: object, **kwargs: object
        ) -> MagicMock:
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
                    await _fetch_search("test", None, None, False, True)
                assert call_count == 1

        asyncio.run(_run())


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

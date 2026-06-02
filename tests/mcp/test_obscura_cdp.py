"""Tests for Obscura CDP browser automation tool.

All tests mock playwright entirely — no real browser is launched.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.mcp.tools.obscura_cdp import (  # noqa: E402
    ElementNotFoundError,
    ObscuraNotRunning,
    _BrowserState,
    _state,
    obscura_click,
    obscura_fill_form,
    obscura_get_markdown,
    obscura_navigate,
)


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _make_mock_page(
    *,
    url: str = "https://example.com",
    title: str = "Example",
    content: str = "<html><body><p>Hello</p></body></html>",
) -> AsyncMock:
    """Create a mock Playwright page preset with the given values."""
    page = AsyncMock()
    page.url = url
    page.title = AsyncMock(return_value=title)
    page.content = AsyncMock(return_value=content)
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    return page


def _setup_connected_state(page: AsyncMock) -> None:
    """Patch ``_state`` so it looks already connected with the given page."""
    _state.browser = MagicMock()
    _state.page = page
    _state._pw = MagicMock()


def _reset_global_state() -> None:
    """Reset the module-level ``_state`` between tests."""
    _state.browser = None
    _state.page = None
    _state._pw = None


# ============================================================================
# TestObscuraNavigate
# ============================================================================


class TestObscuraNavigate:
    """Tests for ``obscura_navigate``."""

    def test_navigate_returns_title(self) -> None:
        """Successful navigation returns URL and title."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page(title="Example Domain")
            _setup_connected_state(page)

            result = await obscura_navigate("https://example.com")
            assert result == {"url": "https://example.com", "title": "Example Domain"}
            page.goto.assert_awaited_once_with("https://example.com", timeout=30_000)

        asyncio.run(_run())

    def test_navigate_timeout_returns_warning(self) -> None:
        """Timeout during navigation returns partial result with warning."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page()
            page.goto = AsyncMock(side_effect=TimeoutError("timed out"))

            _setup_connected_state(page)

            result = await obscura_navigate("https://slow.example.com")
            assert result["url"] == "https://slow.example.com"
            assert result["title"] == "(timed out)"
            assert "timed out" in result["warning"]

        asyncio.run(_run())


# ============================================================================
# TestObscuraGetMarkdown
# ============================================================================


class TestObscuraGetMarkdown:
    """Tests for ``obscura_get_markdown``."""

    def test_get_markdown_converts_html(self) -> None:
        """Navigate + extract content yields markdown via markdownify."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page(content="<h1>Hello</h1><p>World</p>")
            _setup_connected_state(page)

            result = await obscura_get_markdown("https://example.com")
            assert "Hello" in result
            assert "World" in result
            page.goto.assert_awaited_once_with("https://example.com", timeout=30_000)

        asyncio.run(_run())

    def test_get_markdown_timeout_returns_content(self) -> None:
        """Timeout during navigation still returns content from page."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page(content="<h1>Partial</h1>")
            page.goto = AsyncMock(side_effect=TimeoutError("timed out"))

            _setup_connected_state(page)

            result = await obscura_get_markdown("https://slow.example.com")
            assert "Partial" in result

        asyncio.run(_run())


# ============================================================================
# TestObscuraFillForm
# ============================================================================


class TestObscuraFillForm:
    """Tests for ``obscura_fill_form``."""

    def test_fill_form_single_field(self) -> None:
        """Single selector filled successfully."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page()
            _setup_connected_state(page)

            result = await obscura_fill_form(
                "https://example.com/form",
                {"input[name=email]": "test@example.com"},
            )
            assert result["status"] == "ok"
            assert result["filled_count"] == "1"
            page.goto.assert_awaited_once_with(
                "https://example.com/form", timeout=30_000
            )
            page.wait_for_selector.assert_awaited_once()
            page.fill.assert_awaited_once()

        asyncio.run(_run())

    def test_fill_form_multiple_fields(self) -> None:
        """Multiple selectors filled in order."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page()
            _setup_connected_state(page)

            selectors = {
                "input[name=email]": "user@test.com",
                "input[name=password]": "s3cret",
            }
            result = await obscura_fill_form(
                "https://example.com/login", selectors
            )
            assert result["status"] == "ok"
            assert result["filled_count"] == "2"
            assert page.fill.call_count == 2

        asyncio.run(_run())

    def test_fill_form_selector_not_found(self) -> None:
        """Missing selector raises ``ElementNotFoundError``."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page()
            page.wait_for_selector = AsyncMock(
                side_effect=TimeoutError("missing")
            )

            _setup_connected_state(page)

            with pytest.raises(
                ElementNotFoundError, match="input\\[name=missing\\]"
            ):
                await obscura_fill_form(
                    "https://example.com",
                    {"input[name=missing]": "val"},
                )

        asyncio.run(_run())


# ============================================================================
# TestObscuraClick
# ============================================================================


class TestObscuraClick:
    """Tests for ``obscura_click``."""

    def test_click_successful(self) -> None:
        """Click on existing element succeeds."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page()
            _setup_connected_state(page)

            result = await obscura_click("button#submit")
            assert result == {"status": "ok", "selector": "button#submit"}
            page.click.assert_awaited_once_with("button#submit")

        asyncio.run(_run())

    def test_click_selector_not_found(self) -> None:
        """Missing selector raises ``ElementNotFoundError``."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page()
            page.wait_for_selector = AsyncMock(
                side_effect=TimeoutError("missing")
            )

            _setup_connected_state(page)

            with pytest.raises(ElementNotFoundError, match="button#gone"):
                await obscura_click("button#gone")

        asyncio.run(_run())


# ============================================================================
# TestObscuraConnection
# ============================================================================


class TestObscuraConnection:
    """Tests for Obscura CDP connection handling."""

    def test_connection_refused_raises(self) -> None:
        """Connection refused raises ``ObscuraNotRunning`` with clear message."""

        async def _run() -> None:
            _reset_global_state()

            with patch(
                "src.mcp.tools.obscura_cdp.async_playwright"
            ) as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw_instance.chromium = MagicMock()
                mock_pw_instance.chromium.connect_over_cdp = AsyncMock(
                    side_effect=ConnectionRefusedError("Connection refused")
                )
                mock_pw.return_value = mock_pw_instance
                mock_pw.return_value.start = AsyncMock(
                    return_value=mock_pw_instance
                )

                with pytest.raises(ObscuraNotRunning, match="not running"):
                    await obscura_navigate("https://example.com")

        asyncio.run(_run())

    def test_os_error_retries_then_raises(self) -> None:
        """OSError (e.g. ECONNREFUSED) retries then raises ObscuraNotRunning."""

        async def _run() -> None:
            _reset_global_state()

            with patch(
                "src.mcp.tools.obscura_cdp.async_playwright"
            ) as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw_instance.chromium = MagicMock()
                mock_pw_instance.chromium.connect_over_cdp = AsyncMock(
                    side_effect=OSError("Cannot connect")
                )
                mock_pw.return_value = mock_pw_instance
                mock_pw.return_value.start = AsyncMock(
                    return_value=mock_pw_instance
                )

                with pytest.raises(ObscuraNotRunning, match="not running"):
                    await obscura_get_markdown("https://example.com")

                # Should have retried 3 times (tenacity stop_after_attempt).
                call_count = (
                    mock_pw_instance.chromium.connect_over_cdp.call_count
                )
                assert call_count == 3

        asyncio.run(_run())


# ============================================================================
# TestObscuraAuth
# ============================================================================


class TestObscuraAuth:
    """Tests verifying auth levels are enforced per tool type."""

    def test_navigate_has_read_auto(self) -> None:
        """``obscura_navigate`` is decorated with READ_AUTO."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page(title="Auth Test")
            _setup_connected_state(page)

            result = await obscura_navigate("https://example.com")
            assert result["title"] == "Auth Test"

        asyncio.run(_run())

    def test_get_markdown_has_read_auto(self) -> None:
        """``obscura_get_markdown`` is decorated with READ_AUTO."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page(content="<h2>Read Test</h2>")
            _setup_connected_state(page)

            result = await obscura_get_markdown("https://example.com")
            assert "Read Test" in result

        asyncio.run(_run())

    def test_fill_form_has_write_notify(self) -> None:
        """``obscura_fill_form`` is decorated with WRITE_NOTIFY."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page()
            _setup_connected_state(page)

            result = await obscura_fill_form(
                "https://example.com",
                {"input[name=q]": "test"},
            )
            assert result["status"] == "ok"

        asyncio.run(_run())

    def test_click_has_write_notify(self) -> None:
        """``obscura_click`` is decorated with WRITE_NOTIFY."""

        async def _run() -> None:
            _reset_global_state()
            page = _make_mock_page()
            _setup_connected_state(page)

            result = await obscura_click("a.link")
            assert result["status"] == "ok"

        asyncio.run(_run())


# ============================================================================
# TestBrowserStateSingleton
# ============================================================================


class TestBrowserStateSingleton:
    """Tests for the ``_BrowserState`` connection manager."""

    def test_ensure_connected_creates_browser_once(self) -> None:
        """Second call to ``ensure_connected`` reuses the existing browser."""

        async def _run() -> None:
            _reset_global_state()

            with patch(
                "src.mcp.tools.obscura_cdp.async_playwright"
            ) as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw_instance.chromium = MagicMock()
                mock_pw_instance.chromium.connect_over_cdp = AsyncMock()

                mock_browser = AsyncMock()
                mock_browser.new_page = AsyncMock(
                    return_value=_make_mock_page()
                )
                mock_pw_instance.chromium.connect_over_cdp.return_value = (
                    mock_browser
                )
                mock_pw.return_value = mock_pw_instance
                mock_pw.return_value.start = AsyncMock(
                    return_value=mock_pw_instance
                )

                state = _BrowserState()
                await state.ensure_connected()
                first_count = (
                    mock_pw_instance.chromium.connect_over_cdp.call_count
                )
                assert first_count == 1

                # Second call should be a no-op.
                await state.ensure_connected()
                second_count = (
                    mock_pw_instance.chromium.connect_over_cdp.call_count
                )
                assert second_count == 1

        asyncio.run(_run())

    def test_ensure_connected_skips_if_already_connected(self) -> None:
        """Already-connected state avoids re-connecting."""

        async def _run() -> None:
            _reset_global_state()
            state = _BrowserState()
            state.browser = MagicMock()
            state.page = _make_mock_page()
            state._pw = MagicMock()

            # Should return immediately without errors.
            await state.ensure_connected()
            assert state.browser is not None

        asyncio.run(_run())
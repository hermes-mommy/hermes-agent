"""Tests for P6 BrowserBackend -- CDP via Playwright connect_over_cdp.

Every test uses MOCKED Playwright objects (no live browser calls).
One test per action. Fail-soft verified for dispatch errors.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure guinevere package is importable (in-repo layout)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from guinevere.tools.backends.browser import BrowserBackend


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def backend():
    """Fresh BrowserBackend with Playwright connection already mocked."""
    be = BrowserBackend()
    return be


@pytest.fixture
def mock_page():
    """A MagicMock that looks like a Playwright Page with async methods."""
    page = AsyncMock()
    page.url = "https://example.com/test"
    page.title = AsyncMock(return_value="Example Domain")
    page.content = AsyncMock(return_value="<html><body><h1>Example</h1></body></html>")
    page.evaluate = AsyncMock(return_value="")
    page.goto = AsyncMock()
    page.mouse = MagicMock()
    page.mouse.click = AsyncMock()
    page.keyboard = MagicMock()
    page.keyboard.type = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\nFAKE_PNG")
    page.locator = MagicMock()
    page.query_selector = AsyncMock(return_value=MagicMock())
    return page


@pytest.fixture
def mock_browser(mock_page):
    """Mock Playwright Browser returned by connect_over_cdp."""
    context = AsyncMock()
    context.pages = [mock_page]
    browser = AsyncMock()
    browser.contexts = [context]
    return browser


@pytest.fixture
def mock_playwright_cls(mock_browser):
    """Patch async_playwright() context manager to return mock browser.

    Yields the mock_browser so tests can adjust page-level mocks.
    """
    pw_instance = AsyncMock()
    pw_instance.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

    pw_cm = AsyncMock()
    pw_cm.__aenter__ = AsyncMock(return_value=pw_instance)
    pw_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("guinevere.tools.backends.browser.async_playwright", return_value=pw_cm):
        yield mock_browser


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async coroutine in a fresh event loop (test isolation)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# RED: one test per action
# ---------------------------------------------------------------------------


class TestNavigate:
    def test_navigate_sends_goto(self, backend, mock_playwright_cls, mock_page):
        result = _run(backend.dispatch("navigate", {"url": "https://example.com"}))
        assert result["ok"] is True
        assert result["url"] == "https://example.com"
        mock_page.goto.assert_awaited_once_with("https://example.com")

    def test_navigate_missing_url(self, backend, mock_playwright_cls):
        result = _run(backend.dispatch("navigate", {}))
        assert result["ok"] is False
        assert "url" in result["error"].lower()


class TestGetHtml:
    def test_get_html_returns_content(self, backend, mock_playwright_cls, mock_page):
        result = _run(backend.dispatch("get_html", {}))
        assert result["ok"] is True
        assert "<html>" in result["html"]
        mock_page.content.assert_awaited_once()


class TestGetMarkdown:
    def test_get_markdown_calls_evaluate(self, backend, mock_playwright_cls, mock_page):
        mock_page.evaluate = AsyncMock(return_value="# Example\n\nHello world")
        result = _run(backend.dispatch("get_markdown", {}))
        assert result["ok"] is True
        assert result["markdown"] == "# Example\n\nHello world"
        mock_page.evaluate.assert_awaited()


class TestGetText:
    def test_get_text_returns_inner_text(self, backend, mock_playwright_cls, mock_page):
        mock_page.evaluate = AsyncMock(return_value="Example\nHello world")
        result = _run(backend.dispatch("get_text", {}))
        assert result["ok"] is True
        assert "Example" in result["text"]
        mock_page.evaluate.assert_awaited()


class TestScroll:
    def test_scroll_down(self, backend, mock_playwright_cls, mock_page):
        mock_page.evaluate = AsyncMock(return_value=None)
        result = _run(backend.dispatch("scroll", {"direction": "down", "amount": 500}))
        assert result["ok"] is True
        assert result["direction"] == "down"
        mock_page.evaluate.assert_awaited()

    def test_scroll_up(self, backend, mock_playwright_cls, mock_page):
        mock_page.evaluate = AsyncMock(return_value=None)
        result = _run(backend.dispatch("scroll", {"direction": "up", "amount": 300}))
        assert result["ok"] is True
        assert result["direction"] == "up"

    def test_scroll_default_direction(self, backend, mock_playwright_cls, mock_page):
        mock_page.evaluate = AsyncMock(return_value=None)
        result = _run(backend.dispatch("scroll", {}))
        assert result["ok"] is True
        assert result["direction"] == "down"


class TestClick:
    def test_click_at_coordinates(self, backend, mock_playwright_cls, mock_page):
        result = _run(backend.dispatch("click", {"x": 100, "y": 200}))
        assert result["ok"] is True
        mock_page.mouse.click.assert_awaited_once_with(100, 200)

    def test_click_missing_coords(self, backend, mock_playwright_cls):
        result = _run(backend.dispatch("click", {}))
        assert result["ok"] is False
        assert "x" in result["error"].lower() or "y" in result["error"].lower()


class TestClickSelector:
    def test_click_selector(self, backend, mock_playwright_cls, mock_page):
        loc = AsyncMock()
        loc.click = AsyncMock()
        mock_page.locator.return_value = loc
        result = _run(backend.dispatch("click_selector", {"selector": "button#submit"}))
        assert result["ok"] is True
        assert result["selector"] == "button#submit"
        mock_page.locator.assert_called_once_with("button#submit")
        loc.click.assert_awaited_once()

    def test_click_selector_not_found(self, backend, mock_playwright_cls, mock_page):
        loc = AsyncMock()
        loc.click = AsyncMock(side_effect=Exception("element not found"))
        mock_page.locator.return_value = loc
        result = _run(backend.dispatch("click_selector", {"selector": "#nonexistent"}))
        assert result["ok"] is False


class TestTypeInto:
    def test_type_into_selector(self, backend, mock_playwright_cls, mock_page):
        loc = AsyncMock()
        loc.fill = AsyncMock()
        mock_page.locator.return_value = loc
        result = _run(backend.dispatch("type_into", {"selector": "input#name", "text": "Hermes"}))
        assert result["ok"] is True
        assert result["selector"] == "input#name"
        mock_page.locator.assert_called_once_with("input#name")
        loc.fill.assert_awaited_once_with("Hermes")

    def test_type_into_missing_text(self, backend, mock_playwright_cls, mock_page):
        loc = AsyncMock()
        loc.fill = AsyncMock()
        mock_page.locator.return_value = loc
        result = _run(backend.dispatch("type_into", {"selector": "input"}))
        assert result["ok"] is True
        loc.fill.assert_awaited_once_with("")


class TestScreenshot:
    def test_screenshot_returns_base64(self, backend, mock_playwright_cls, mock_page):
        result = _run(backend.dispatch("screenshot", {}))
        assert result["ok"] is True
        assert result["format"] == "png"
        assert isinstance(result["screenshot_b64"], str)
        assert len(result["screenshot_b64"]) > 0
        mock_page.screenshot.assert_awaited()

    def test_screenshot_full_page(self, backend, mock_playwright_cls, mock_page):
        result = _run(backend.dispatch("screenshot", {"full_page": True}))
        assert result["ok"] is True
        call_kwargs = mock_page.screenshot.call_args
        assert call_kwargs[1].get("full_page") is True or (len(call_kwargs[0]) > 0)


class TestGetTitle:
    def test_get_title(self, backend, mock_playwright_cls, mock_page):
        result = _run(backend.dispatch("get_title", {}))
        assert result["ok"] is True
        assert result["title"] == "Example Domain"
        mock_page.title.assert_awaited_once()


# ---------------------------------------------------------------------------
# Edge cases & fail-soft
# ---------------------------------------------------------------------------


class TestFailSoft:
    def test_unknown_action_returns_error(self, backend, mock_playwright_cls):
        result = _run(backend.dispatch("nonexistent_action", {}))
        assert result["ok"] is False
        assert "unknown" in result["error"].lower()

    def test_dispatch_never_raises(self, backend, mock_playwright_cls, mock_page):
        """dispatch must never propagate exceptions to caller."""
        mock_page.content = AsyncMock(side_effect=RuntimeError("browser crashed"))
        result = _run(backend.dispatch("get_html", {}))
        assert result["ok"] is False
        assert "browser crashed" in result["error"]


class TestActionsCatalogue:
    def test_actions_count(self, backend):
        actions = backend.actions()
        assert len(actions) == 10

    def test_name_is_browser(self, backend):
        assert backend.name == "browser"

    def test_is_available(self, backend):
        assert backend.is_available() is True

    def test_action_names(self, backend):
        names = {a.name for a in backend.actions()}
        expected = {
            "navigate", "get_html", "get_markdown", "get_text",
            "scroll", "click", "click_selector", "type_into",
            "screenshot", "get_title",
        }
        assert names == expected

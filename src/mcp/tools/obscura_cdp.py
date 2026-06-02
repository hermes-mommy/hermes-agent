"""MCP Obscura CDP Tool — Browser automation via Obscura CDP + Playwright.

Provides ``register_tools(mcp: FastMCP) -> None`` to register
navigate, markdown extraction, form-fill, and click operations,
each gated with the appropriate ``AuthLevel``.

Architecture per ADR-033:
    - Obscura CDP server: ``obscura serve --port 9222 --stealth --workers 2``
    - Client: ``playwright.chromium.connect_over_cdp("ws://127.0.0.1:9222")``
    - Content extraction: ``page.content()`` + ``markdownify``
    - No ``page.screenshot()`` — Obscura has no pixel rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog
from markdownify import markdownify as md_convert
from playwright.async_api import Browser, Page, async_playwright
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from src.mcp.auth import AuthLevel, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CDP_URL: str = "ws://127.0.0.1:9222"
_RETRY_ATTEMPTS: int = 3
_RETRY_WAIT_SECONDS: float = 2.0
_PAGE_TIMEOUT_MS: int = 30_000

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ObscuraNotRunning(Exception):
    """Raised when the Obscura CDP server is unreachable."""


class ElementNotFoundError(Exception):
    """Raised when a DOM selector matches no elements."""


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------


@dataclass
class _BrowserState:
    """Holds the lazily-initialised Playwright browser and page references.

    Created once on first use and reused across tool invocations.
    The ``playwright`` instance is kept alive for the server's lifetime.
    """

    browser: Browser | None = None
    page: Page | None = field(default=None, init=False)

    _pw: Any = field(default=None, init=False)

    async def ensure_connected(self) -> None:
        """Connect to the Obscura CDP server if not already connected.

        Uses tenacity for automatic retry on connection failures.
        """
        if self.browser is not None:
            return

        @retry(
            stop=stop_after_attempt(_RETRY_ATTEMPTS),
            wait=wait_fixed(_RETRY_WAIT_SECONDS),
            retry=retry_if_exception_type((ConnectionRefusedError, OSError)),
            reraise=True,
        )
        async def _connect() -> None:
            logger.info("obscura_connecting", cdp_url=_CDP_URL)
            self._pw = await async_playwright().start()
            self.browser = await self._pw.chromium.connect_over_cdp(_CDP_URL)
            self.page = await self.browser.new_page()
            logger.info("obscura_connected", cdp_url=_CDP_URL)

        try:
            await _connect()
        except Exception as exc:
            logger.error("obscura_connection_failed", cdp_url=_CDP_URL, error=str(exc))
            raise ObscuraNotRunning(
                (
                    f"Obscura CDP server is not running on {_CDP_URL}. "
                    f"Start it with: obscura serve --port 9222 --stealth --workers 2"
                )
            ) from exc


_state = _BrowserState()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def obscura_navigate(url: str) -> dict[str, str]:
    """Navigate to *url* and return the page title and URL.

    Auth: READ_AUTO.
    """
    await _state.ensure_connected()
    assert _state.page is not None

    try:
        await _state.page.goto(url, timeout=_PAGE_TIMEOUT_MS)
        title = await _state.page.title()
    except Exception:
        logger.warning("obscura_navigate_timeout", url=url)
        return {
            "url": url,
            "title": "(timed out)",
            "warning": "Page load timed out — partial content may be available via obscura_get_markdown.",
        }

    logger.info("obscura_navigate", url=url, title=title)
    return {"url": url, "title": title}


async def obscura_get_markdown(url: str) -> str:
    """Navigate to *url* and return the page content as Markdown.

    Uses ``page.content()`` then ``markdownify`` for HTML→Markdown conversion.
    Auth: READ_AUTO.
    """
    await _state.ensure_connected()
    assert _state.page is not None

    try:
        await _state.page.goto(url, timeout=_PAGE_TIMEOUT_MS)
    except Exception:
        logger.warning("obscura_get_markdown_timeout", url=url)

    raw_html: str = await _state.page.content()
    md_text: str = md_convert(raw_html, heading_style="ATX")

    logger.info("obscura_get_markdown", url=url, chars=len(md_text))
    return md_text


async def obscura_fill_form(url: str, selectors: dict[str, str]) -> dict[str, str]:
    """Navigate to *url* and fill form fields from *selectors* mapping.

    *selectors* is a ``{css_selector: value}`` dict.
    Auth: WRITE_NOTIFY.
    """
    await _state.ensure_connected()
    assert _state.page is not None

    await _state.page.goto(url, timeout=_PAGE_TIMEOUT_MS)

    filled: list[str] = []
    for sel, val in selectors.items():
        try:
            await _state.page.wait_for_selector(sel, timeout=10_000)
            await _state.page.fill(sel, val)
            filled.append(sel)
        except Exception:
            logger.error("obscura_fill_form_selector_missing", selector=sel, url=url)
            raise ElementNotFoundError(
                f"Selector '{sel}' not found on page {url}"
            ) from None

    logger.info("obscura_fill_form", url=url, filled=len(filled))
    return {"status": "ok", "filled_count": str(len(filled)), "selectors": ",".join(filled)}


async def obscura_click(selector: str) -> dict[str, str]:
    """Click the element matching *selector* on the current page.

    The page must already be navigated (via ``obscura_navigate`` or
    ``obscura_get_markdown``) before calling this function.
    Auth: WRITE_NOTIFY.
    """
    await _state.ensure_connected()
    assert _state.page is not None

    try:
        await _state.page.wait_for_selector(selector, timeout=10_000)
        await _state.page.click(selector)
    except Exception:
        url = _state.page.url if _state.page else "unknown"
        logger.error("obscura_click_selector_missing", selector=selector, url=url)
        raise ElementNotFoundError(
            f"Selector '{selector}' not found. Current page: {url}"
        ) from None

    logger.info("obscura_click", selector=selector)
    return {"status": "ok", "selector": selector}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register Obscura CDP browser tools on the MCP server.

    Adds four tools:
      - ``obscura_navigate`` — READ_AUTO
      - ``obscura_get_markdown`` — READ_AUTO
      - ``obscura_fill_form`` — WRITE_NOTIFY
      - ``obscura_click`` — WRITE_NOTIFY
    """

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="obscura_navigate")
    async def _obscura_navigate(url: str) -> dict[str, str]:
        return await obscura_navigate(url)

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="obscura_get_markdown")
    async def _obscura_get_markdown(url: str) -> str:
        return await obscura_get_markdown(url)

    @mcp.tool()
    @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="obscura_fill_form")
    async def _obscura_fill_form(url: str, selectors: dict[str, str]) -> dict[str, str]:
        return await obscura_fill_form(url, selectors)

    @mcp.tool()
    @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="obscura_click")
    async def _obscura_click(selector: str) -> dict[str, str]:
        return await obscura_click(selector)

    logger.info("obscura_cdp_tools_registered")
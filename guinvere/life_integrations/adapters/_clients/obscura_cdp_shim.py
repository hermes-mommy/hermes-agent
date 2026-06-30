"""P22 obscura CDP client shim — wraps ``playwright.async_api`` over a CDP endpoint.

The P22 ``BrowserIntegrationAdapter`` calls instance methods:
- ``await self._browser.navigate(url)`` → returns dict-like with ``url``+``title``
- ``await self._browser.get_markdown(url)`` → returns a markdown string
- ``await self._browser.fill_form(url, selector, value)`` → writes a field value
- ``await self._browser.click(url, selector)`` → clicks an element

The real Guinevere browser backend is ``playwright.async_api.async_playwright``,
connected over the Chrome DevTools Protocol (CDP) to a local Chromium running
with ``--remote-debugging-port=9222``. No API key — CDP is local socket only.

This shim holds ``cdp_url`` (default ``ws://127.0.0.1:9222``) and lazily
constructs ``playwright`` + ``browser`` + ``page`` on first ``_ensure`` call.
Subsequent calls reuse the same ``Page`` instance — single-owner per shim.

The shim is fail-closed: if ``async_playwright().start()`` or any subsequent
connect step raises, the underlying exception propagates (no fake PASS).
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_GOTO_TIMEOUT_MS: int = 30_000


class ObscuraCdpShim:
    """Async wrapper over a CDP-attached Chromium page (``Option B`` lifecycle).

    Lifecycle:
        * ``__init__`` records ``cdp_url`` but does not import or connect.
        * First call to ``_ensure()`` lazily imports ``playwright``, starts the
          driver, connects over CDP, opens a page.
        * Subsequent ``navigate`` / ``get_markdown`` calls reuse the page.
        * ``close()`` stops the driver and clears state (for tests + lifecycle).

    CDP requires no API key — the websocket URL is local-only and is the
    canonical configuration surface for ``obscura`` (browser tool).
    """

    def __init__(self, cdp_url: str = "ws://127.0.0.1:9222") -> None:
        """Record ``cdp_url``. Lazy import on first ``_ensure()`` call.

        Args:
            cdp_url: WebSocket URL of the CDP endpoint (no API key needed).
        """
        self._cdp_url = cdp_url
        self._pw: Any | None = None
        self._browser: Any | None = None
        self._page: Any | None = None

    async def _ensure(self) -> None:
        """Lazily construct (and cache) ``playwright`` + ``browser`` + ``page``.

        Idempotent — repeated calls reuse the existing ``Page``. The lazy
        import step is intentional: avoid pulling in ``playwright`` at
        adapter-wiring time so import-time remains deterministic.
        """
        if self._page is not None:
            return
        from playwright.async_api import async_playwright

        logger.info(
            "p22.browser.obscura.connecting",
            cdp_url=self._cdp_url,
        )
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.connect_over_cdp(self._cdp_url)
        self._page = await self._browser.new_page()
        logger.info("p22.browser.obscura.ready")

    async def navigate(self, url: str) -> dict[str, str]:
        """Navigate to *url* and return ``{"url": ..., "title": ...}``."""
        await self._ensure()
        await self._page.goto(url, timeout=_GOTO_TIMEOUT_MS)
        title = await self._page.title()
        logger.info("p22.browser.obscura.navigate", url=url, title=title)
        return {"url": url, "title": title}

    async def get_markdown(self, url: str) -> str:
        """Navigate to *url* and return page content as ATX-flavoured Markdown."""
        await self._ensure()
        await self._page.goto(url, timeout=_GOTO_TIMEOUT_MS)
        from markdownify import markdownify

        content = await self._page.content()
        md = markdownify(content, heading_style="ATX")
        logger.info(
            "p22.browser.obscura.get_markdown",
            url=url,
            length=len(md),
        )
        return md

    async def fill_form(
        self, url: str, selector: str, value: str
    ) -> dict[str, Any]:
        """Navigate to *url* and fill ``value`` into the ``selector`` element.

        Returns ``{"filled": True, "url": url, "selector": selector}``.
        L2 (write) action — caller is responsible for reversibility metadata.
        """
        await self._ensure()
        await self._page.goto(url, timeout=_GOTO_TIMEOUT_MS)
        await self._page.fill(selector, value)
        logger.info(
            "p22.browser.obscura.fill_form",
            url=url,
            selector=selector,
        )
        return {"filled": True, "url": url, "selector": selector}

    async def click(self, url: str, selector: str) -> dict[str, Any]:
        """Navigate to *url* and click the element matched by ``selector``.

        Returns ``{"clicked": True, "url": url, "selector": selector}``.
        L2 (write) action.
        """
        await self._ensure()
        await self._page.goto(url, timeout=_GOTO_TIMEOUT_MS)
        await self._page.click(selector)
        logger.info(
            "p22.browser.obscura.click",
            url=url,
            selector=selector,
        )
        return {"clicked": True, "url": url, "selector": selector}

    async def close(self) -> None:
        """Stop the playwright driver and reset cached state.

        Safe to call multiple times — no-op if never connected.
        """
        if self._pw is not None:
            await self._pw.stop()
        self._pw = None
        self._browser = None
        self._page = None
        logger.info("p22.browser.obscura.closed")

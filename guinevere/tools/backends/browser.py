"""M8 Browser backend -- CDP via Playwright connect_over_cdp.

Ported from: P22 browser_adapter.py, P23 browser_executor (Section 4.1),
MCP obscura_cdp.py.

10 actions: 5 L1 READ, 5 L2 WRITE.
Connects to the existing guinevere-obscura CDP server at localhost:9222.
Uses Playwright async API (connect_over_cdp) for full browser control.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from playwright.async_api import async_playwright  # noqa: F811 — module-level for mock.patch

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)

# CDP endpoint for guinevere-obscura
_CDP_URL = "http://localhost:9222"


class BrowserBackend(ToolBackend):
    """Browser/research backend (CDP via Playwright, L1/L2).

    Actions: navigate, get_html, get_markdown, get_text, scroll,
    click, click_selector, type_into, screenshot, get_title.

    Connects lazily to the running guinevere-obscura CDP server.
    All dispatch calls are fail-soft (never raise to caller).
    """

    @property
    def name(self) -> str:
        return "browser"

    def actions(self) -> list[Action]:
        return [
            Action("navigate", ActionTier.L1_READ, description="Navigate to URL"),
            Action("get_html", ActionTier.L1_READ, description="Get page HTML"),
            Action("get_markdown", ActionTier.L1_READ, description="Page as markdown"),
            Action("get_text", ActionTier.L1_READ, description="Get visible text"),
            Action("scroll", ActionTier.L2_WRITE, description="Scroll page"),
            Action("click", ActionTier.L2_WRITE, description="Click at coordinates"),
            Action("click_selector", ActionTier.L2_WRITE, description="Click element by selector"),
            Action("type_into", ActionTier.L2_WRITE, description="Type text into element"),
            Action("screenshot", ActionTier.L1_READ, description="Capture page screenshot"),
            Action("get_title", ActionTier.L1_READ, description="Get page title"),
        ]

    def is_available(self) -> bool:
        return True  # Playwright + CDP server assumed available

    # -- lazy connection ----------------------------------------------------

    async def _ensure_connected(self) -> Any:
        """Lazily connect to CDP and return the active page.

        Reuses existing connection if already established.
        """
        if self._page is not None:
            return self._page

        self._playwright_cm = async_playwright()
        pw = await self._playwright_cm.__aenter__()
        self._browser = await pw.chromium.connect_over_cdp(_CDP_URL)
        # Get the first existing context+page (obscura has one open)
        if self._browser.contexts and self._browser.contexts[0].pages:
            self._page = self._browser.contexts[0].pages[0]
        else:
            context = await self._browser.new_context()
            self._page = await context.new_page()
        return self._page

    def __init__(self) -> None:
        self._playwright_cm: Any = None
        self._browser: Any = None
        self._page: Any = None

    # -- dispatch -----------------------------------------------------------

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a browser action via CDP/Playwright.

        All actions perform real I/O against the running browser.
        Errors are caught and returned as ``{"ok": False, "error": ...}``
        (fail-soft -- never raise to caller).
        """
        action_lower = action.lower()

        try:
            page = await self._ensure_connected()

            # -- L1 READ actions ------------------------------------------

            if action_lower == "navigate":
                url = args.get("url", "")
                if not url:
                    return {"ok": False, "action": action, "error": "url is required"}
                await page.goto(url)
                return {"ok": True, "action": action, "url": url, "title": await page.title()}

            if action_lower == "get_html":
                html = await page.content()
                return {"ok": True, "action": action, "html": html}

            if action_lower == "get_markdown":
                # Simple HTML-to-markdown via JS Turndown-like extraction
                md = await page.evaluate(
                    """() => {
                    function toMd(el, depth) {
                        if (!el) return '';
                        const tag = el.tagName ? el.tagName.toLowerCase() : '';
                        const txt = (el.textContent || '').trim();
                        if (['script','style','noscript'].includes(tag)) return '';
                        if (tag.match(/^h[1-6]$/)) {
                            const level = parseInt(tag[1]);
                            return '#'.repeat(level) + ' ' + txt + '\\n\\n';
                        }
                        if (tag === 'p') return txt + '\\n\\n';
                        if (tag === 'br') return '\\n';
                        if (tag === 'a') return '[' + txt + '](' + (el.href||'') + ')';
                        if (tag === 'img') return '![' + (el.alt||'') + '](' + (el.src||'') + ')';
                        if (tag === 'li') return '- ' + txt + '\\n';
                        if (tag === 'code' && el.parentNode && el.parentNode.tagName.toLowerCase() === 'pre') {
                            return '```\\n' + txt + '\\n```\\n';
                        }
                        if (tag === 'code') return '`' + txt + '`';
                        if (tag === 'strong' || tag === 'b') return '**' + txt + '**';
                        if (tag === 'em' || tag === 'i') return '*' + txt + '*';
                        if (tag === 'blockquote') return '> ' + txt + '\\n';
                        if (tag === 'table') {
                            const rows = Array.from(el.querySelectorAll('tr'));
                            return rows.map(r => {
                                const cells = Array.from(r.querySelectorAll('th,td'));
                                return '| ' + cells.map(c => c.textContent.trim()).join(' | ') + ' |';
                            }).join('\\n') + '\\n\\n';
                        }
                        let out = '';
                        for (const child of el.childNodes) {
                            if (child.nodeType === 3) { out += child.textContent; }
                            else if (child.nodeType === 1) { out += toMd(child, depth+1); }
                        }
                        return out;
                    }
                    return toMd(document.body, 0).trim();
                }"""
                )
                return {"ok": True, "action": action, "markdown": md}

            if action_lower == "get_text":
                text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                return {"ok": True, "action": action, "text": text}

            if action_lower == "screenshot":
                full_page = bool(args.get("full_page", False))
                raw = await page.screenshot(full_page=full_page)
                b64 = base64.b64encode(raw).decode("ascii")
                return {"ok": True, "action": action, "screenshot_b64": b64, "format": "png", "bytes": len(raw)}

            if action_lower == "get_title":
                title = await page.title()
                return {"ok": True, "action": action, "title": title}

            # -- L2 WRITE actions -----------------------------------------

            if action_lower == "scroll":
                direction = args.get("direction", "down")
                amount = args.get("amount", 500)
                delta = amount if direction == "down" else -amount
                await page.evaluate(f"window.scrollBy(0, {delta})")
                return {"ok": True, "action": action, "direction": direction, "amount": amount}

            if action_lower == "click":
                x = args.get("x")
                y = args.get("y")
                if x is None or y is None:
                    return {"ok": False, "action": action, "error": "x and y coordinates are required"}
                await page.mouse.click(x, y)
                return {"ok": True, "action": action, "x": x, "y": y}

            if action_lower == "click_selector":
                selector = args.get("selector", "")
                if not selector:
                    return {"ok": False, "action": action, "error": "selector is required"}
                await page.locator(selector).click()
                return {"ok": True, "action": action, "selector": selector}

            if action_lower == "type_into":
                selector = args.get("selector", "")
                text = args.get("text", "")
                if not selector:
                    return {"ok": False, "action": action, "error": "selector is required"}
                await page.locator(selector).fill(text)
                return {"ok": True, "action": action, "selector": selector, "text": text}

            # -- unknown action -------------------------------------------
            return {"ok": False, "error": f"unknown browser action: {action}"}

        except Exception as exc:
            logger.error("browser dispatch failed action=%s: %s", action, exc, exc_info=True)
            return {"ok": False, "action": action, "error": str(exc)}

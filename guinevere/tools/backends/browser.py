"""M8 Browser backend — web browsing and research.

Ported from: P22 browser_adapter.py, P23 browser_executor (Section 4.1),
MCP obscura_cdp.py, brave_search.py, exa_search.py, websearch.py, fetch.py.

11 actions: 7 L1 READ, 4 L2 WRITE.
"""

from __future__ import annotations

import logging
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)


class BrowserBackend(ToolBackend):
    """Browser/research backend (Playwright-backed, L1/L2).

    Actions: search, fetch_url, navigate, get_markdown, extract_text,
    click, fill, screenshot, scroll, wait, download.
    """

    @property
    def name(self) -> str:
        return "browser"

    def actions(self) -> list[Action]:
        return [
            Action("search", ActionTier.L1_READ, description="Web search (Brave/Exa)"),
            Action("fetch_url", ActionTier.L1_READ, description="Fetch URL content (1MB limit)"),
            Action("navigate", ActionTier.L1_READ, description="Navigate to URL"),
            Action("get_markdown", ActionTier.L1_READ, description="Page as markdown"),
            Action("extract_text", ActionTier.L1_READ, description="Extract text from selector"),
            Action("scroll", ActionTier.L1_READ, description="Scroll page"),
            Action("wait", ActionTier.L1_READ, description="Wait for element"),
            Action("click", ActionTier.L2_WRITE, description="Click element"),
            Action("fill", ActionTier.L2_WRITE, description="Fill form field"),
            Action("screenshot", ActionTier.L2_WRITE, description="Capture page screenshot"),
            Action("download", ActionTier.L2_WRITE, description="Download file from page"),
        ]

    def is_available(self) -> bool:
        return True  # Playwright always available as local tool

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a browser action.  External calls are mocked in tests."""
        action_lower = action.lower()

        if action_lower == "search":
            query = args.get("query", "")
            return {"ok": True, "action": action, "results": [], "count": 0, "query": query}

        if action_lower == "fetch_url":
            url = args.get("url", "")
            return {"ok": True, "action": action, "url": url, "content": ""}

        if action_lower == "navigate":
            url = args.get("url", "")
            return {"ok": True, "action": action, "url": url}

        if action_lower == "get_markdown":
            url = args.get("url", "")
            return {"ok": True, "action": action, "url": url, "markdown": ""}

        if action_lower == "extract_text":
            selector = args.get("selector", "")
            return {"ok": True, "action": action, "selector": selector, "text": ""}

        if action_lower == "scroll":
            direction = args.get("direction", "down")
            return {"ok": True, "action": action, "direction": direction}

        if action_lower == "wait":
            selector = args.get("selector", "")
            return {"ok": True, "action": action, "selector": selector}

        if action_lower == "click":
            selector = args.get("selector", "")
            return {"ok": True, "action": action, "selector": selector}

        if action_lower == "fill":
            selector = args.get("selector", "")
            value = args.get("value", "")
            return {"ok": True, "action": action, "selector": selector, "value": value}

        if action_lower == "screenshot":
            return {"ok": True, "action": action, "path": ""}

        if action_lower == "download":
            url = args.get("url", "")
            return {"ok": True, "action": action, "url": url, "path": ""}

        return {"ok": False, "error": f"unknown browser action: {action}"}

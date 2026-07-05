"""P22 fetch client shim — wraps ``guinevere.mcp.tools.fetch.fetch_url`` as instance protocol.

The P22 ``BrowserIntegrationAdapter`` calls instance methods:
- ``await self._fetch.fetch(url, format=...)``

The real Guinevere fetcher is a module-level function in
``guinevere.mcp.tools.fetch`` (``fetch_url(url, format="markdown")``) that returns a
dict containing ``url``, ``title``, ``content``, ``content_length``,
``content_type``, and an optional ``warning``.

This shim holds an optional ``fetch_fn`` callable. When wired (``fetch_fn`` is
provided), the shim forwards the awaited call. When ``None`` (the default —
honest CONFIG_MISSING for callers that haven't supplied a test fake), the
shim does **not** lazy-import on ``__init__``; the real import happens only
inside ``fetch()`` on first call (lazy import preserves import-time
determinism and avoids pulling in httpx/markdownify at adapter-wiring time).

The shim is fail-closed: if no ``fetch_fn`` is wired and the underlying
``fetch_url`` raises, the shim surfaces the underlying error (no fake PASS).
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

import structlog

logger = structlog.get_logger(__name__)

# Type alias: an async callable taking (url, format) and returning a dict.
FetchFn = Callable[[str, str], Awaitable[dict[str, str]]]


class FetchClientShim:
    """Instance wrapper around ``guinevere.mcp.tools.fetch.fetch_url``.

    Usage:
        shim = FetchClientShim(fetch_fn=my_async_fetch)  # test fake wired
        # or
        shim = FetchClientShim()  # lazy-imports fetch_url on first call

    The shim normalises the call signature to ``fetch(url, format)`` (matches
    the protocol the browser adapter expects) and returns
    ``{"content": content, "url": url}`` so the adapter can pull content + URL
    out of a uniform shape regardless of the underlying fetcher's return dict.
    """

    def __init__(self, fetch_fn: FetchFn | None = None) -> None:
        """Initialize with an optional ``fetch_fn`` (None = lazy import).

        Args:
            fetch_fn: Async callable ``(url, format) -> dict`` used as the
                fetch backend for testing/dependency injection. ``None`` defers
                import to the first ``fetch()`` call.
        """
        self._fetch = fetch_fn

    async def fetch(self, url: str, format: str = "markdown") -> dict[str, str]:
        """Fetch *url* as ``format`` ("markdown" or "text").

        Returns a small mapping with ``content`` and ``url`` so the caller does
        not need to know the wider shape of the underlying fetcher's dict.
        Logs a single ``p22.browser.fetch.*`` event per call.
        """
        if self._fetch is None:
            from guinevere.mcp.tools.fetch import fetch_url

            content = await fetch_url(url, format=format)
        else:
            content = await self._fetch(url, format=format)

        logger.info(
            "p22.browser.fetch.complete",
            url=url,
            format=format,
            content_length=len(content.get("content", "")),
        )
        return {"content": content, "url": url}

"""MCP Fetch Tool — Web content retrieval with HTML-to-Markdown conversion.

Fetches a URL via HTTP(S), converts HTML content to Markdown using
``markdownify``, and returns structured metadata.  Enforces URL-scheme
validation, 1 MB response-size limits, and transient-error retries.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx
import structlog
from markdownify import markdownify as md
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from guinevere.mcp.auth import AuthLevel, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

_MAX_CONTENT_BYTES: int = 1_048_576  # 1 MB
_TIMEOUT_SECONDS: float = 30.0
_MAX_REDIRECTS: int = 5
_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_url(url: str) -> None:
    """Raise ``ValueError`` if *url* uses a disallowed scheme."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme '{scheme}' is not allowed. "
            f"Only http:// and https:// are permitted."
        )


def _is_transient(exc: BaseException) -> bool:
    """Return *True* for errors worth retrying (timeout, connection, 5xx)."""
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_transient),
    reraise=True,
)
async def _fetch_with_retry(url: str) -> httpx.Response:
    """Perform an HTTP GET with redirect following and retry on transient errors."""
    async with httpx.AsyncClient(
        timeout=_TIMEOUT_SECONDS,
        follow_redirects=True,
        max_redirects=_MAX_REDIRECTS,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response


def _extract_title(html: str) -> str:
    """Return the ``<title>`` text from *html*, or empty string."""
    match = _TITLE_RE.search(html)
    return match.group(1).strip() if match else ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="fetch_url")
async def fetch_url(url: str, format: str = "markdown") -> dict[str, str]:
    """Fetch a URL and return content as Markdown or plain text.

    Args:
        url: The URL to fetch.  Must use ``http://`` or ``https://``.
        format: ``"markdown"`` (default) converts HTML to Markdown;
            ``"text"`` strips HTML tags for plain text.

    Returns:
        Dict with keys ``url``, ``title``, ``content``, ``content_length``,
        ``content_type``, and optionally ``warning``.

    Raises:
        ValueError: If the URL scheme is not HTTP(S).
        httpx.TimeoutException: If the request times out after retries.
    """
    _validate_url(url)

    try:
        response = await _fetch_with_retry(url)
    except httpx.TimeoutException as exc:
        logger.error("fetch_timeout", url=url, error=str(exc))
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "fetch_http_error",
            url=url,
            status_code=exc.response.status_code,
            error=str(exc),
        )
        return {
            "url": url,
            "title": "",
            "content": (
                f"HTTP error {exc.response.status_code}: "
                f"{exc.response.reason_phrase}"
            ),
            "content_length": "0",
            "content_type": exc.response.headers.get("content-type", ""),
        }

    content_type = response.headers.get("content-type", "")
    raw_text = response.text
    original_size = len(response.content)

    # --- Size-limit enforcement -----------------------------------------
    warning = ""
    if original_size > _MAX_CONTENT_BYTES:
        # Truncate by bytes first, then decode safely.
        truncated_bytes = response.content[:_MAX_CONTENT_BYTES]
        raw_text = truncated_bytes.decode("utf-8", errors="replace")
        warning = (
            f"Response exceeded 1MB limit ({original_size} bytes). "
            f"Content has been truncated."
        )
        logger.warning(
            "fetch_content_truncated",
            url=url,
            original_size=original_size,
        )

    # --- Content conversion --------------------------------------------
    title = ""
    content: str

    if "text/html" in content_type:
        # Remove script/style blocks entirely before conversion.
        cleaned_html = _SCRIPT_STYLE_RE.sub("", raw_text)
        title = _extract_title(cleaned_html)
        if format == "markdown":
            content = md(cleaned_html, strip=["img"])
        else:
            content = _TAG_RE.sub("", cleaned_html)
    else:
        content = raw_text
        if "text/html" not in content_type and format != "markdown":
            # Non-HTML content returned as-is regardless of format.
            pass

    result: dict[str, str] = {
        "url": url,
        "title": title,
        "content": content,
        "content_length": str(len(content)),
        "content_type": content_type,
    }
    if warning:
        result["warning"] = warning

    logger.info(
        "fetch_complete",
        url=url,
        content_type=content_type,
        content_length=len(content),
    )
    return result


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register the ``fetch_url`` tool with the FastMCP server."""
    mcp.tool(name="fetch_url")(fetch_url)

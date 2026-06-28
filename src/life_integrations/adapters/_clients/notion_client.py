"""P22 Notion client — direct httpx wrapper for the Notion REST v1 API.

Bridges ``src.life_integrations.adapters.notion_adapter.NotionIntegrationAdapter``
to the Notion REST surface at ``https://api.notion.com/v1``.  Auth header is
``Authorization: Bearer <token>`` + required ``Notion-Version: 2026-03-11``
for all calls.

This is the "no SDK" substrate path — fork-compat (P24), keeps every
integration symmetrical (``discord``, ``github``, ``notion``, ``telegram``)
under direct httpx so the audit-writer shim has full visibility into
429/529 responses and their ``Retry-After`` metadata.

Security: the token is stored on the instance only to drive outbound
``Authorization`` headers.  It MUST NOT appear in any log line, response
body echo, or exception message.  ``structlog`` emits only method + status
+ Notion-Version (sanity check) — never the bearer secret.

Rate limit: Notion quotas ~3 req/sec average; burst-tolerant.  Responses
with 429/529 carry a ``Retry-After`` integer (seconds).  This client
honours ``Retry-After`` with capped exponential backoff (max 3 retries),
then raises ``RateLimitExceededError``.

Fail-closed: a constructor call with an empty token (or ``None``) raises
``ConfigurationMissingError`` immediately — we never fake Ok from a
missing-tokens adapter.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import structlog

from src.life_integrations.errors import (
    ConfigurationMissingError,
    ProviderError,
    RateLimitExceededError,
)

logger = structlog.get_logger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"

# Notion API version pinned per P22 research §2.10.  Multi-source databases
# raise validation_error on legacy versions — this version is current as of
# 2026-03-11 per the official upgrade trail.
DEFAULT_NOTION_VERSION = "2026-03-11"

# Retry policy: 429 (rate limit) and 529 (overloaded) are transient.
# Token auth / capability errors (401/403) are NOT retried — they are
# deterministic and fail-fast up to the adapter.
_RETRIABLE_STATUSES: frozenset[int] = frozenset({429, 529})
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 30.0


class NotionClient:
    """Async httpx wrapper for the Notion REST v1 API.

    Authentication: ``Authorization: Bearer <token>`` + ``Notion-Version``.
    On 429/529 the client honours ``Retry-After`` (seconds) with capped
    exponential backoff (1s → 2s → 4s, max 30s, 3 attempts total).

    Public surface (one per documented action, see §2.2-§2.6 of the
    ``github-notion-telegram-full-access.md`` research):

        ``search(query)``
        ``retrieve_page(page_id)``
        ``create_page(parent, properties, children=[])``
        ``update_page(page_id, properties)``
        ``append_blocks(block_id, children)``
        ``archive_page(page_id)``
        ``health()``
    """

    def __init__(
        self,
        token: str,
        notion_version: str = DEFAULT_NOTION_VERSION,
        timeout: float = 30.0,
    ) -> None:
        """Initialise with the integration token.

        Args:
            token: Notion integration token (``ntn_`` or ``secret_`` prefix).
            notion_version: API version to pin on every outbound request.
            timeout: httpx client timeout in seconds.

        Raises:
            ConfigurationMissingError: if the token is empty / falsy.
        """
        if not token or not isinstance(token, str) or not token.strip():
            logger.error(
                "p22.notion.client.config_missing",
                reason="integration token empty",
            )
            raise ConfigurationMissingError(
                "Notion client: integration token empty — CONFIG_MISSING "
                "(sec-notion-integration-token not provisioned)"
            )

        # Note: the token itself is intentionally NOT bound to the logger
        # context.  Only Notion-Version is logged for sanity-check.
        self._token = token
        self._notion_version = notion_version
        self._timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": self._notion_version,
            "Content-Type": "application/json",
        }

        logger.info(
            "p22.notion.client.init",
            notion_version=self._notion_version,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Internal transport
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request against the Notion API with retry.

        Retries on 429/529 with ``Retry-After`` honoured.  Other non-2xx
        responses raise ``ProviderError`` with sanitised status + body.
        """
        url = f"{NOTION_API_BASE}{path}"

        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=self._headers,
                        json=body,
                        params=params,
                    )
            except httpx.HTTPError as exc:
                # Transport-level failure (DNS, TLS, read timeout).  Log
                # by type only — never echo the bearer header.
                logger.warning(
                    "p22.notion.client.transport_error",
                    method=method,
                    path=path,
                    error_type=type(exc).__name__,
                )
                if attempt >= _MAX_RETRIES:
                    raise ProviderError(
                        provider="notion",
                        status=0,
                        message=f"transport_error: {type(exc).__name__}",
                    ) from exc
                await asyncio.sleep(_INITIAL_BACKOFF_SECONDS * (2 ** attempt))
                continue

            status = response.status_code

            # Retriable transient — honour Retry-After, then bounded backoff.
            if status in _RETRIABLE_STATUSES:
                retry_after = _parse_retry_after(response)
                sleep_seconds = (
                    retry_after
                    if retry_after is not None
                    else _INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                )
                sleep_seconds = min(sleep_seconds, _MAX_BACKOFF_SECONDS)
                logger.warning(
                    "p22.notion.client.rate_limited",
                    method=method,
                    path=path,
                    status=status,
                    retry_after=retry_after,
                    sleep_seconds=sleep_seconds,
                    attempt=attempt,
                )
                if attempt >= _MAX_RETRIES:
                    raise RateLimitExceededError(
                        provider="notion",
                        retry_after=retry_after,
                    )
                await asyncio.sleep(sleep_seconds)
                continue

            # 2xx — parse JSON and return.  Note: when no JSON body is
            # present (204, empty), return an empty dict.
            if 200 <= status < 300:
                try:
                    payload = response.json()
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.warning(
                        "p22.notion.client.parse_empty",
                        method=method,
                        path=path,
                        status=status,
                        error_type=type(exc).__name__,
                    )
                    return {}
                logger.info(
                    "p22.notion.client.ok",
                    method=method,
                    path=path,
                    status=status,
                )
                return payload if isinstance(payload, dict) else {}

            # Non-retriable HTTP error.
            try:
                err_body = response.json()
            except (json.JSONDecodeError, ValueError):
                err_body = {"message": response.text[:200] if response.text else ""}
            logger.warning(
                "p22.notion.client.http_error",
                method=method,
                path=path,
                status=status,
                provider_message=str(err_body.get("message", ""))[:200],
            )
            raise ProviderError(
                provider="notion",
                status=status,
                message=str(err_body.get("message", ""))[:200],
            )

        # Unreachable, but keep mypy happy.
        raise ProviderError(
            provider="notion",
            status=0,
            message="retry loop exited without success",
        )

    # ------------------------------------------------------------------
    # Public API surface (per notion_adapter contract)
    # ------------------------------------------------------------------

    async def search(
        self, query: str, page_size: int = 20
    ) -> list[dict[str, Any]]:
        """POST /v1/search — search pages & databases the integration can see."""
        # Empty query is allowed by Notion; returns "all accessible".  We
        # still package it for the request body.
        body = {"query": query, "page_size": page_size}
        payload = await self._request("POST", "/search", body=body)
        results = payload.get("results", [])
        return results if isinstance(results, list) else []

    async def retrieve_page(self, page_id: str) -> dict[str, Any]:
        """GET /v1/pages/{id} — fetch a page's properties."""
        return await self._request("GET", f"/pages/{page_id}")

    async def create_page(
        self,
        parent: dict[str, Any],
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """POST /v1/pages — create a page.

        ``parent`` shape: ``{"page_id": "..."}`` | ``{"data_source_id": "..."}``
        | ``{"workspace": True}`` (the latter only for OAuth public integ).
        ``children`` is optional; Notion accepts ≤100 blocks per request.
        """
        body: dict[str, Any] = {
            "parent": parent,
            "properties": properties,
        }
        if children:
            body["children"] = children
        return await self._request("POST", "/pages", body=body)

    async def update_page(
        self, page_id: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """PATCH /v1/pages/{id} — update page properties."""
        return await self._request(
            "PATCH", f"/pages/{page_id}", body={"properties": properties}
        )

    async def append_blocks(
        self, block_id: str, children: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """PATCH /v1/blocks/{id}/children — append child blocks."""
        return await self._request(
            "PATCH", f"/blocks/{block_id}/children", body={"children": children}
        )

    async def archive_page(self, page_id: str) -> dict[str, Any]:
        """PATCH /v1/pages/{id} with ``in_trash: true`` — soft archive.

        Reversible: a follow-up PATCH with ``in_trash: False`` restores the
        page from trash.  Per Notion 2026-03-11, ``archived`` is no longer
        accepted — only ``in_trash`` (docs/reference/trash-page).
        """
        return await self._request(
            "PATCH", f"/pages/{page_id}", body={"in_trash": True}
        )

    async def health(self) -> bool:
        """GET /v1/users/me — bool probe used by the adapter health_check.

        Returns True on 200 (token valid + Integration active),
        False on any error (401, 403, 404, transport failure).
        Never raises — health probes must be defensive.
        """
        try:
            await self._request("GET", "/users/me")
        except ProviderError as exc:
            logger.warning(
                "p22.notion.client.health.http_error", status=exc.status
            )
            return False
        except RateLimitExceededError:
            # Don't fail health on rate limit — the probe still succeeded
            # in reaching the API.  The 429 was returned because we already
            # exhausted retries, which itself implies prior OK traffic.
            return True
        return True


def _parse_retry_after(response: httpx.Response) -> int | None:
    """Extract ``Retry-After`` integer seconds from a response.

    Returns ``None`` if the header is absent or non-integer.
    """
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except ValueError:
        return None

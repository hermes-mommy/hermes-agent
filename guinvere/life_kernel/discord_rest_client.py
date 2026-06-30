"""Async Discord REST API client for the Living Autonomy Kernel.

Implements the Option-B "core-integrated REST publisher" architecture: the
life kernel publishes its dashboard and lifecycle log to Discord via plain
HTTPS REST calls (POST / PATCH / GET) instead of a discord.py gateway.

Why not the gateway:
  - The standalone ``guinevere-discord.service`` is intentionally masked
    (P2-022: "Hermes Gateway handles Discord now"). Re-opening a gateway
    session in the core would risk same-token session collision and would
    couple the web server's event loop to Discord gateway reconnects.
  - The dashboard + log use case is purely *outbound* status publishing; no
    gateway events (messages/reactions/commands) are needed, so a
    persistent WebSocket is unnecessary overhead.

Security:
  - The bot token is read from the ``DISCORD_BOT_TOKEN`` environment variable
    once, stored only on the instance as an Authorization header, and is
    **never** logged, never placed in exceptions, never written to state.
  - All response bodies are treated as opaque; only message ``id`` fields are
    extracted and persisted.

Reliability:
  - Every request is wrapped in ``tenacity`` exponential backoff that retries
    on 5xx and 429 (Too Many Requests). 4xx (non-429) responses are *not*
    retried — they indicate a config/auth problem that retrying will not fix.
  - A hard ``timeout`` is set on every request so a hung Discord never blocks
    the heartbeat (the 1s safety heartbeat especially).
  - The caller (DashboardWriter / DiscordLogChannel) treats any failure as
    fail-soft: log a warning and continue, never raise into the heartbeat.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

_DISCORD_API = "https://discord.com/api/v10"
# Never let a single Discord call hang the heartbeat. The 1s safety heartbeat
# relies on every network round-trip being bounded.
_DEFAULT_TIMEOUT = 10.0
_MAX_ATTEMPTS = 4


class DiscordRestError(Exception):
    """Raised when a Discord REST call fails after all retries.

    The exception message deliberately contains only the HTTP status and a
    short Discord error code — never the request body, headers, or token.
    Callers should catch this and fail-soft.
    """


class DiscordRestClient:
    """Async Discord REST client backed by ``httpx.AsyncClient``.

    A single shared ``httpx.AsyncClient`` is used for connection pooling. The
    client is safe to share across the dashboard writer and log channel.

    Args:
        bot_token: Discord bot token. If ``None``, read from
            ``DISCORD_BOT_TOKEN``. If absent entirely the client is created
            in a disabled state (all calls fail-soft) so the core can boot in
            environments without Discord configured.
        timeout: Per-request timeout in seconds.
    """

    def __init__(
        self,
        bot_token: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        token = bot_token if bot_token is not None else os.environ.get("DISCORD_BOT_TOKEN", "")
        self._token: str = token
        self._timeout: float = timeout
        self._enabled: bool = bool(token)
        self._client: httpx.AsyncClient | None = None
        if not self._enabled:
            # Deliberately do NOT log the absence at INFO repeatedly; the
            # caller logs once at startup. Fail-soft path handles the rest.
            logger.warning("discord_rest_client_disabled_no_token")

    @property
    def enabled(self) -> bool:
        """Whether the client has a token and can make real calls."""
        return self._enabled

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create the underlying ``httpx.AsyncClient``.

        Created on first use (not in ``__init__``) so the client can be
        instantiated outside a running event loop (e.g. during FastAPI
        lifespan setup before the loop is ready).
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=_DISCORD_API,
                timeout=httpx.Timeout(self._timeout),
                headers={
                    "Authorization": f"Bot {self._token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a single Discord REST request with retry + fail-soft.

        Retries on 5xx and 429. Raises :class:`DiscordRestError` on terminal
        failure (non-retryable 4xx, or retries exhausted). Never returns a
        partial/invalid body — only parsed JSON dicts.
        """
        if not self._enabled:
            raise DiscordRestError("discord_rest_client_disabled_no_token")

        client = await self._ensure_client()

        @retry(
            stop=stop_after_attempt(_MAX_ATTEMPTS),
            wait=wait_exponential(min=1, max=8),
            retry=retry_if_exception_type(
                (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException)
            ),
            reraise=True,
        )
        async def _do() -> dict[str, Any]:
            response = await client.request(method, url, json=json)
            # 429 is retryable (rate limited). httpx raises on 4xx by default
            # only if raise_for_status is called; we handle status manually so
            # we can distinguish 429 (retry) from other 4xx (terminal).
            if response.status_code == 429:
                # tenacity will retry because we raise HTTPStatusError.
                raise httpx.HTTPStatusError("rate limited (429)", request=response.request, response=response)
            if 500 <= response.status_code < 600:
                raise httpx.HTTPStatusError(
                    f"discord {response.status_code}",
                    request=response.request,
                    response=response,
                )
            if response.status_code >= 400:
                # Non-retryable client error (auth, perms, bad channel id).
                # Surface a short code, never the body (may echo our payload).
                code = self._extract_error_code(response)
                raise DiscordRestError(
                    f"discord {method} {url} -> {response.status_code} code={code}"
                )
            if response.status_code == 204 or not response.content:
                return {"_status": response.status_code}
            return response.json()

        try:
            return await _do()
        except RetryError as exc:  # pragma: no cover - tenacity reraises
            raise DiscordRestError(f"discord {method} {url} retries exhausted") from exc
        except DiscordRestError:
            raise
        except (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException) as exc:
            raise DiscordRestError(f"discord {method} {url} transport error: {type(exc).__name__}") from exc

    @staticmethod
    def _extract_error_code(response: httpx.Response) -> str:
        """Extract Discord's ``code`` field from an error response.

        Discord error bodies look like ``{"message": "...", "code": 50013}``.
        We return only the code (a public, non-secret value) for diagnostics.
        """
        try:
            body = response.json()
            return str(body.get("code", "?"))
        except Exception:
            logger.debug("failed_to_extract_discord_error_code", exc_info=True)
            return "?"

    async def send_message(
        self,
        channel_id: int | str,
        content: str | None = None,
        embed: dict[str, Any] | None = None,
        embeds: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """POST a message to a channel. Returns ``{"id": message_id, ...}``.

        Args:
            channel_id: Target channel snowflake.
            content: Plain-text content (optional if embeds given).
            embed: A single embed dict (convenience; wrapped into ``embeds``).
            embeds: A list of embed dicts (max 10 per Discord).

        Raises:
            DiscordRestError: on terminal failure.
        """
        payload: dict[str, Any] = {}
        if content is not None:
            payload["content"] = content
        if embed is not None:
            payload["embeds"] = [embed]
        if embeds is not None:
            payload["embeds"] = embeds
        return await self._request("POST", f"/channels/{channel_id}/messages", json=payload)

    async def edit_message(
        self,
        channel_id: int | str,
        message_id: int | str,
        content: str | None = None,
        embed: dict[str, Any] | None = None,
        embeds: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """PATCH an existing message (edit-not-spam). Returns the patched body.

        Used by the DashboardWriter to update the single dashboard message
        in place rather than posting a new one each cycle.
        """
        payload: dict[str, Any] = {}
        if content is not None:
            payload["content"] = content
        if embed is not None:
            payload["embeds"] = [embed]
        if embeds is not None:
            payload["embeds"] = embeds
        return await self._request(
            "PATCH", f"/channels/{channel_id}/messages/{message_id}", json=payload
        )

    async def get_recent_messages(
        self, channel_id: int | str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """GET recent messages from a channel (for dashboard recovery).

        Used at startup to find an existing bot-authored dashboard message
        so we PATCH it instead of creating a duplicate.
        """
        result = await self._request("GET", f"/channels/{channel_id}/messages?limit={limit}")
        if isinstance(result, list):
            return result
        return []

    async def get_channel(self, channel_id: int | str) -> dict[str, Any]:
        """GET channel metadata (used for permissions verification)."""
        return await self._request("GET", f"/channels/{channel_id}")

    async def close(self) -> None:
        """Close the underlying httpx client. Safe to call multiple times."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

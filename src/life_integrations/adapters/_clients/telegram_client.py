"""P22 Telegram Bot API httpx client.

Thin async httpx wrapper for the Telegram Bot API
(https://core.telegram.org/bots/api).

Auth model: token is **embedded in the URL path** — NOT in an
``Authorization`` header. Telegram rejects ``Authorization`` headers; the
canonical auth header for outbound integrations is NONE. The bot token is
embedded as ``https://api.telegram.org/bot<TOKEN>/<METHOD>``.

Rate limiting: Telegram bans bots that exceed ``1 message / second per
same chat`` (and 30/sec globally). When the bot exceeds it, Telegram
returns HTTP 429 with ``parameters.retry_after`` (seconds). The client
must:

1. enforce a per-chat throttle (1 message/second per chat) locally, and
2. respect ``parameters.retry_after`` from a 429 response.

Secret hygiene: the bot token is treated as a SOPS secret; it is never
logged. The URL paths carry the token (``/bot<TOKEN>/...``) so log lines
must NOT record full URLs; only the method name, status code, and chat_id
are emitted.

Methods implemented (mirror of ``telegram_adapter.py`` action surface):

* ``get_updates()``                          — POST ``/getUpdates``
* ``send_message(chat_id, text)``            — POST ``/sendMessage``
* ``edit_message(chat_id, msg_id, text)``    — POST ``/editMessageText``
* ``delete_message(chat_id, msg_id)``        — POST ``/deleteMessage``
* ``copy_message(from_chat_id, msg_id, to_chat_id)`` — POST ``/copyMessage``
* ``send_photo(chat_id, photo, ...)``        — POST ``/sendPhoto``
* ``send_document(chat_id, document, ...)``  — POST ``/sendDocument``
* ``health()``                               — GET  ``/getMe``  → bool

Fail-closed: empty token raises ``ConfigurationMissingError`` rather than
silently succeeding.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx
import structlog

from src.life_integrations.errors import (
    ConfigurationMissingError,
    ProviderError,
    RateLimitExceededError,
)

logger = structlog.get_logger(__name__)


# Disable httpx's own INFO-level URL logging — it would emit the FULL URL
# (with bot token embedded in the path) on every request, defeating the
# secret-hygiene contract of this client. The ``httpx`` logger is a real
# stdlib logger owned by httpx; raising its level to WARNING suppresses
# these lines while preserving error reporting for real transport faults.
logging.getLogger("httpx").setLevel(logging.WARNING)


# Minimum delay between consecutive messages sent to the same chat.
# Telegram enforces 1 msg/sec/chat globally; local throttling prevents
# the first round-trip 429 in moderate traffic.
_PER_CHAT_INTERVAL_SECONDS: float = 1.05  # tiny slack above 1.0s floor


class TelegramClient:
    """Async httpx client for the Telegram Bot API.

    Args:
        token: Bot token ``<bot_id>:<35-char-auth>``. Must be non-empty.
        timeout: HTTP timeout (seconds). Defaults to 30.0.
        base_url: Override for the API base. Defaults to the canonical
            ``https://api.telegram.org`` — overridden ONLY in tests.

    Raises:
        ConfigurationMissingError: at construction time if ``token`` is
            empty/None after stripping. Fail-closed; no fake success.
    """

    # Log key prefix for all client events (matches p22.* convention).
    LOG_PREFIX = "p22.telegram.client"

    def __init__(
        self,
        token: str | None = None,
        timeout: float = 30.0,
        base_url: str = "https://api.telegram.org",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if token is None or not isinstance(token, str) or not token.strip():
            raise ConfigurationMissingError(
                "Telegram bot token missing — CONFIG_MISSING "
                "(sec-telegram-bot-token not provisioned)"
            )
        # The token lives in the URL path; no ``Authorization`` header.
        self._token: str = token.strip()
        self._timeout: float = timeout
        self._base_url: str = base_url.rstrip("/")
        # Per-chat throttle: last-sent timestamp per chat_id.
        self._last_send_at: dict[int | str, float] = {}
        self._throttle_lock = asyncio.Lock()
        # Reuse a single AsyncClient per instance — httpx recommends
        # holding one client for connection pooling. Tests inject a
        # pre-built client bound to ``httpx.MockTransport``; in
        # production, ``client`` is None and we build one here.
        self._client: httpx.AsyncClient = (
            client if client is not None
            else httpx.AsyncClient(timeout=self._timeout)
        )
        self._owns_client: bool = client is None

    # -----------------------------------------------------------------
    # URL helpers — token lives ONLY in the path; never logged.
    # -----------------------------------------------------------------
    def _method_url(self, method: str) -> str:
        """Build the canonical Bot API URL: ``<base>/bot<TOKEN>/<METHOD>``.

        Note: this URL contains the token in its path. Do NOT log it.
        """
        return f"{self._base_url}/bot{self._token}/{method}"

    def _safe_log_extra(
        self,
        method: str,
        chat_id: int | str | None = None,
    ) -> dict[str, Any]:
        """Build a structlog ``extra`` mapping safe to log.

        The full URL (which contains the token) is never returned by this
        helper; only the method name and chat_id, which are NOT secrets.
        """
        return {"method": method, "chat_id": chat_id}

    async def _throttle_chat(self, chat_id: int | str) -> None:
        """Local per-chat throttle: enforce ≥1s spacing between messages.

        Telegram's 1 msg/sec/chat limit is a server-side floor; we mirror
        it locally so well-behaved clients never round-trip just to learn
        they were throttled. ``429 + retry_after`` still wins if the bot
        shares a chat with another bot / polling loop that races us.
        """
        async with self._throttle_lock:
            now = time.monotonic()
            last = self._last_send_at.get(chat_id)
            if last is not None:
                wait = _PER_CHAT_INTERVAL_SECONDS - (now - last)
                if wait > 0:
                    await asyncio.sleep(wait)
                    now = time.monotonic()
            self._last_send_at[chat_id] = now

    @staticmethod
    def _safe_json(resp: httpx.Response) -> dict[str, Any]:
        """Parse JSON leniently; return ``{}`` on bad payload."""
        try:
            parsed = resp.json()
        except (ValueError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    async def _post_method(
        self,
        method: str,
        body: dict[str, Any],
        *,
        chat_id: int | str | None = None,
    ) -> dict[str, Any]:
        """POST to ``<base>/bot<TOKEN>/<method>`` with a JSON body.

        Args:
            method: Telegram Bot API method name (e.g. ``sendMessage``).
            body: JSON-serialisable request body.
            chat_id: Optional chat identifier for per-chat throttling.

        Returns:
            The ``result`` field of the Telegram response envelope as a
            ``dict``; some methods (e.g. ``getUpdates``) return a list —
            those callers branch on the returned value's type.

        Raises:
            RateLimitExceededError: on HTTP 429; ``retry_after`` is read
                from ``parameters.retry_after`` (Telegram spec).
            ProviderError: on any other non-200 response or transport error.
        """
        if chat_id is not None:
            await self._throttle_chat(chat_id)
        url = self._method_url(method)
        try:
            resp = await self._client.post(url, json=body)
        except httpx.HTTPError as exc:
            logger.warning(
                f"{self.LOG_PREFIX}.transport_error",
                **self._safe_log_extra(method, chat_id),
                error=str(exc),
            )
            raise ProviderError(
                provider="telegram",
                status=0,
                message=f"transport error: {exc}",
            ) from exc

        if resp.status_code == 429:
            data = self._safe_json(resp)
            retry_after_raw = data.get("parameters", {}).get("retry_after")
            try:
                retry_after = int(retry_after_raw) if retry_after_raw is not None else None
            except (TypeError, ValueError):
                retry_after = None
            logger.warning(
                f"{self.LOG_PREFIX}.rate_limited",
                **self._safe_log_extra(method, chat_id),
                retry_after=retry_after,
            )
            raise RateLimitExceededError(provider="telegram", retry_after=retry_after)

        if resp.status_code != 200:
            data = self._safe_json(resp)
            description = data.get("description", resp.text)
            error_code = data.get("error_code", resp.status_code)
            logger.warning(
                f"{self.LOG_PREFIX}.non_200",
                **self._safe_log_extra(method, chat_id),
                status_code=resp.status_code,
                # ``description`` is the Telegram API string (safe).
                description=description,
            )
            raise ProviderError(
                provider="telegram",
                status=resp.status_code,
                message=f"{error_code}: {description}",
            )

        data = self._safe_json(resp)
        if not data.get("ok", False):
            description = data.get("description", "ok=false without description")
            logger.error(
                f"{self.LOG_PREFIX}.ok_false",
                **self._safe_log_extra(method, chat_id),
                description=description,
            )
            raise ProviderError(
                provider="telegram",
                status=resp.status_code,
                message=description,
            )
        result = data.get("result")
        logger.info(
            f"{self.LOG_PREFIX}.ok",
            **self._safe_log_extra(method, chat_id),
        )
        # ``_post_method`` returns a dict-shaped result; for ``getUpdates``
        # (which returns a list) the callers use the ``_post_method_list``
        # variant.
        return result if isinstance(result, dict) else {}

    async def _post_method_list(
        self,
        method: str,
        body: dict[str, Any],
            *,
        chat_id: int | str | None = None,
    ) -> list[dict[str, Any]]:
        """Variant of ``_post_method`` for endpoints returning a list
        (``getUpdates``). Same throttling, error, and logging behavior; the
        full response body is what callers want when ``result`` is a list.
        """
        if chat_id is not None:
            await self._throttle_chat(chat_id)
        url = self._method_url(method)
        try:
            resp = await self._client.post(url, json=body)
        except httpx.HTTPError as exc:
            logger.warning(
                f"{self.LOG_PREFIX}.transport_error",
                **self._safe_log_extra(method, chat_id),
                error=str(exc),
            )
            raise ProviderError(
                provider="telegram",
                status=0,
                message=f"transport error: {exc}",
            ) from exc

        if resp.status_code == 429:
            data = self._safe_json(resp)
            retry_after_raw = data.get("parameters", {}).get("retry_after")
            try:
                retry_after = int(retry_after_raw) if retry_after_raw is not None else None
            except (TypeError, ValueError):
                retry_after = None
            logger.warning(
                f"{self.LOG_PREFIX}.rate_limited",
                **self._safe_log_extra(method, chat_id),
                retry_after=retry_after,
            )
            raise RateLimitExceededError(provider="telegram", retry_after=retry_after)

        if resp.status_code != 200:
            data = self._safe_json(resp)
            description = data.get("description", resp.text)
            error_code = data.get("error_code", resp.status_code)
            logger.warning(
                f"{self.LOG_PREFIX}.non_200",
                **self._safe_log_extra(method, chat_id),
                status_code=resp.status_code,
                description=description,
            )
            raise ProviderError(
                provider="telegram",
                status=resp.status_code,
                message=f"{error_code}: {description}",
            )

        data = self._safe_json(resp)
        if not data.get("ok", False):
            description = data.get("description", "ok=false without description")
            logger.error(
                f"{self.LOG_PREFIX}.ok_false",
                **self._safe_log_extra(method, chat_id),
                description=description,
            )
            raise ProviderError(
                provider="telegram",
                status=resp.status_code,
                message=description,
            )
        result = data.get("result")
        logger.info(
            f"{self.LOG_PREFIX}.ok",
            **self._safe_log_extra(method, chat_id),
        )
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []

    async def _get_method(self, method: str) -> dict[str, Any]:
        """GET to ``<base>/bot<TOKEN>/<method>`` — used by ``health()``."""
        url = self._method_url(method)
        try:
            resp = await self._client.get(url)
        except httpx.HTTPError as exc:
            logger.warning(
                f"{self.LOG_PREFIX}.transport_error",
                method=method,
                error=str(exc),
            )
            return {}
        if resp.status_code != 200:
            return {}
        data = self._safe_json(resp)
        if not data.get("ok", False):
            return {}
        return data if isinstance(data, dict) else {}

    # -----------------------------------------------------------------
    # Public API surface — mirror of telegram_adapter action names.
    # -----------------------------------------------------------------
    async def get_updates(
        self,
        *,
        timeout: int = 25,
        limit: int = 100,
        offset: int | None = None,
        allowed_updates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Long-poll for pending updates (L1)."""
        body: dict[str, Any] = {"timeout": timeout, "limit": limit}
        if offset is not None:
            body["offset"] = offset
        if allowed_updates is not None:
            body["allowed_updates"] = allowed_updates
        return await self._post_method_list("getUpdates", body)

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        *,
        parse_mode: str | None = None,
        reply_to_message_id: int | None = None,
        disable_notification: bool | None = None,
    ) -> int:
        """Send ``text`` to ``chat_id``; returns the new ``message_id`` (L2)."""
        if chat_id is None:
            raise ConfigurationMissingError("send_message requires chat_id")
        body: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode is not None:
            body["parse_mode"] = parse_mode
        if reply_to_message_id is not None:
            body["reply_to_message_id"] = reply_to_message_id
        if disable_notification is not None:
            body["disable_notification"] = disable_notification
        result = await self._post_method("sendMessage", body, chat_id=chat_id)
        if "message_id" not in result:
            raise ProviderError(
                provider="telegram",
                status=200,
                message="sendMessage response missing message_id",
            )
        return int(result["message_id"])

    async def edit_message(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Edit a previously-sent message (L2)."""
        if chat_id is None or message_id is None:
            raise ConfigurationMissingError("edit_message requires chat_id and message_id")
        body: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": int(message_id),
            "text": text,
        }
        if parse_mode is not None:
            body["parse_mode"] = parse_mode
        if reply_markup is not None:
            body["reply_markup"] = reply_markup
        result = await self._post_method("editMessageText", body, chat_id=chat_id)
        return result

    async def delete_message(
        self,
        chat_id: int | str,
        message_id: int,
    ) -> bool:
        """Delete a message (L3 — requires pre-delete snapshot upstream)."""
        if chat_id is None or message_id is None:
            raise ConfigurationMissingError("delete_message requires chat_id and message_id")
        body = {"chat_id": chat_id, "message_id": int(message_id)}
        await self._post_method("deleteMessage", body, chat_id=chat_id)
        # Telegram returns True on successful delete.
        return True

    async def copy_message(
        self,
        from_chat_id: int | str,
        message_id: int,
        to_chat_id: int | str,
    ) -> int:
        """Copy a message from one chat to another (used for archive snapshots).

        Returns the NEW ``message_id`` in ``to_chat_id``.
        """
        if from_chat_id is None or message_id is None or to_chat_id is None:
            raise ConfigurationMissingError(
                "copy_message requires from_chat_id, message_id, and to_chat_id"
            )
        body = {
            "chat_id": to_chat_id,
            "from_chat_id": from_chat_id,
            "message_id": int(message_id),
        }
        result = await self._post_method("copyMessage", body, chat_id=to_chat_id)
        if "message_id" not in result:
            raise ProviderError(
                provider="telegram",
                status=200,
                message="copyMessage response missing message_id",
            )
        return int(result["message_id"])

    async def send_photo(
        self,
        chat_id: int | str,
        photo: str | bytes,
        *,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> int:
        """Send a photo to ``chat_id``; returns its ``message_id`` (L2).

        ``photo`` may be a ``file_id``, an HTTP URL, or raw bytes
        (submitted as a string for now — multipart upgrade is out of scope
        for this client; the adapter signature is
        ``send_photo(chat_id, photo, caption=...)``).
        """
        if chat_id is None or photo is None:
            raise ConfigurationMissingError("send_photo requires chat_id and photo")
        body: dict[str, Any] = {"chat_id": chat_id, "photo": photo}
        if caption is not None:
            body["caption"] = caption
        if parse_mode is not None:
            body["parse_mode"] = parse_mode
        result = await self._post_method("sendPhoto", body, chat_id=chat_id)
        if "message_id" not in result:
            raise ProviderError(
                provider="telegram",
                status=200,
                message="sendPhoto response missing message_id",
            )
        return int(result["message_id"])

    async def send_document(
        self,
        chat_id: int | str,
        document: str | bytes,
        *,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> int:
        """Send a document to ``chat_id``; returns its ``message_id`` (L2)."""
        if chat_id is None or document is None:
            raise ConfigurationMissingError("send_document requires chat_id and document")
        body: dict[str, Any] = {"chat_id": chat_id, "document": document}
        if caption is not None:
            body["caption"] = caption
        if parse_mode is not None:
            body["parse_mode"] = parse_mode
        result = await self._post_method("sendDocument", body, chat_id=chat_id)
        if "message_id" not in result:
            raise ProviderError(
                provider="telegram",
                status=200,
                message="sendDocument response missing message_id",
            )
        return int(result["message_id"])

    async def health(self) -> bool:
        """Health probe: GET /getMe → True iff HTTP 200 and ok=true."""
        data = await self._get_method("getMe")
        return bool(data.get("ok", False))

    async def aclose(self) -> None:
        """Release the underlying ``httpx.AsyncClient``.

        Only the client built by this instance is closed; passing in a
        pre-built ``client`` (e.g. via tests) keeps ownership with the
        caller — those tests manage their own teardown.
        """
        if self._owns_client:
            try:
                await self._client.aclose()
            except Exception:
                # Best-effort shutdown; never raise.
                pass

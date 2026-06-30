"""Telegram channel adapter — synthesized rewrite.

Combines:
- guinvere/life_integrations/adapters/telegram_adapter.py (integration adapter
  pattern, action dispatch, CONFIG_MISSING, pre-delete snapshot)
- guinvere/life_integrations/adapters/_clients/telegram_client.py (httpx Bot API
  client, per-chat throttle, 429 retry_after, token-in-URL auth model)
- Hermes gateway/platforms/telegram.py (send_message cross-channel tool
  pattern, topic/thread references)

Stripped: BaseIntegrationAdapter dependency,
BaseIntegrationAdapter dependency.  Replaced with ChannelSender protocol.

CONFIG_MISSING: when sec-telegram-bot-token is not provisioned (D2).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from .._bridge import ChannelSender, SendResult

logger = structlog.get_logger(__name__)

# Suppress httpx INFO logging — URL paths contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

_PER_CHAT_INTERVAL_SECONDS: float = 1.05  # Telegram: 1 msg/sec/chat

# ---- CONFIG_MISSING detection ----


def _check_config() -> list[str]:
    """Check if Telegram config is provisioned."""
    import os

    reasons: list[str] = []
    # Try multiple env var names (SOPS pattern + direct).
    token = (
        os.environ.get("SEC_TELEGRAM_BOT_TOKEN", "")
        or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    ).strip()
    if not token:
        reasons.append("Telegram bot token not provisioned (sec-telegram-bot-token)")
    return reasons


# ---- Envelope DTOs ----


@dataclass(frozen=True, slots=True)
class TelegramMessageEnvelope:
    """Normalized inbound Telegram payload."""

    message_id: int
    chat_id: int | str
    sender_id: int | None
    sender_name: str | None
    text: str
    timestamp: datetime
    chat_type: str = "private"  # private, group, supergroup, channel
    reply_to_message_id: int | None = None
    media_type: str | None = None
    media_file_id: str | None = None
    caption: str | None = None

    @property
    def is_text(self) -> bool:
        return bool(self.text.strip())

    @property
    def is_group(self) -> bool:
        return self.chat_type in ("group", "supergroup", "channel")

    def validate(self) -> None:
        if not self.message_id:
            raise ValueError("message_id must not be zero")
        if not self.chat_id:
            raise ValueError("chat_id must not be empty")


@dataclass(frozen=True, slots=True)
class TelegramDeliveryEnvelope:
    """Normalized outbound Telegram payload."""

    chat_id: int | str
    text: str
    parse_mode: str | None = None
    reply_to_message_id: int | None = None
    disable_notification: bool = False

    def validate(self) -> None:
        if not self.chat_id:
            raise ValueError("chat_id must not be empty")
        if not self.text:
            raise ValueError("text must not be empty")


# ---- httpx Bot API client (ported from _clients/telegram_client.py) ----


class TelegramClient:
    """Async httpx client for the Telegram Bot API.

    Auth: token embedded in URL path (/bot<TOKEN>/METHOD) — NOT in an
    Authorization header (Telegram rejects them).

    Rate limiting: per-chat throttle (1.05s minimum) + 429 retry_after.

    Secret hygiene: bot token is never logged. Only method name, status
    code, and chat_id are emitted.
    """

    LOG_PREFIX = "guinevere.telegram.client"

    def __init__(
        self,
        token: str,
        timeout: float = 30.0,
        base_url: str = "https://api.telegram.org",
        client: Any | None = None,
    ) -> None:
        if not token or not token.strip():
            raise ValueError(
                "Telegram bot token missing — CONFIG_MISSING "
                "(sec-telegram-bot-token not provisioned)"
            )
        self._token: str = token.strip()
        self._timeout = timeout
        self._base_url = base_url.rstrip("/")
        self._last_send_at: dict[int | str, float] = {}
        self._throttle_lock = asyncio.Lock()
        self._owns_client = client is None
        # Lazy httpx import to avoid dependency when not needed.
        try:
            import httpx
            self._client: Any = client or httpx.AsyncClient(timeout=self._timeout)
        except ImportError:
            self._client = None

    def _method_url(self, method: str) -> str:
        """Build URL: <base>/bot<TOKEN>/<METHOD>.  Do NOT log this URL."""
        return f"{self._base_url}/bot{self._token}/{method}"

    def _safe_log_extra(
        self,
        method: str,
        chat_id: int | str | None = None,
    ) -> dict[str, Any]:
        return {"method": method, "chat_id": chat_id}

    async def _throttle_chat(self, chat_id: int | str) -> None:
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
    def _safe_json(resp: Any) -> dict[str, Any]:
        try:
            parsed = resp.json()
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    async def _post_method(
        self,
        method: str,
        body: dict[str, Any],
        *,
        chat_id: int | str | None = None,
    ) -> dict[str, Any]:
        """POST to /bot<TOKEN>/<method>.  Returns the 'result' dict."""
        if self._client is None:
            raise RuntimeError("httpx not available — cannot make Telegram API calls")
        if chat_id is not None:
            await self._throttle_chat(chat_id)
        url = self._method_url(method)
        try:
            resp = await self._client.post(url, json=body)
        except Exception as exc:
            logger.warning(
                f"{self.LOG_PREFIX}.transport_error",
                **self._safe_log_extra(method, chat_id),
                error=str(exc),
            )
            raise RuntimeError(f"Telegram transport error: {exc}") from exc

        if resp.status_code == 429:
            data = self._safe_json(resp)
            retry_after = data.get("parameters", {}).get("retry_after")
            logger.warning(
                f"{self.LOG_PREFIX}.rate_limited",
                **self._safe_log_extra(method, chat_id),
                retry_after=retry_after,
            )
            if retry_after is not None:
                await asyncio.sleep(int(retry_after) + 1)
                # Single retry after rate-limit wait.
                resp = await self._client.post(url, json=body)
                if resp.status_code == 200:
                    data = self._safe_json(resp)
                    result = data.get("result")
                    return result if isinstance(result, dict) else {}
            raise RuntimeError(f"Telegram rate limited (429), retry_after={retry_after}")

        if resp.status_code != 200:
            data = self._safe_json(resp)
            description = data.get("description", resp.text)
            raise RuntimeError(f"Telegram API error {resp.status_code}: {description}")

        data = self._safe_json(resp)
        if not data.get("ok", False):
            raise RuntimeError(f"Telegram ok=false: {data.get('description', 'unknown')}")
        result = data.get("result")
        logger.info(f"{self.LOG_PREFIX}.ok", **self._safe_log_extra(method, chat_id))
        return result if isinstance(result, dict) else {}

    async def _post_method_list(
        self,
        method: str,
        body: dict[str, Any],
        *,
        chat_id: int | str | None = None,
    ) -> list[dict[str, Any]]:
        """Variant for endpoints returning a list (getUpdates)."""
        if self._client is None:
            raise RuntimeError("httpx not available")
        if chat_id is not None:
            await self._throttle_chat(chat_id)
        url = self._method_url(method)
        try:
            resp = await self._client.post(url, json=body)
        except Exception as exc:
            logger.warning(f"{self.LOG_PREFIX}.transport_error", method=method, error=str(exc))
            raise RuntimeError(f"Telegram transport error: {exc}") from exc

        if resp.status_code != 200:
            data = self._safe_json(resp)
            raise RuntimeError(f"Telegram API error {resp.status_code}: {data.get('description', '')}")

        data = self._safe_json(resp)
        if not data.get("ok", False):
            raise RuntimeError(f"Telegram ok=false: {data.get('description', '')}")
        result = data.get("result")
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []

    async def get_updates(
        self,
        *,
        timeout: int = 25,
        limit: int = 100,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Long-poll for pending updates (L1)."""
        body: dict[str, Any] = {"timeout": timeout, "limit": limit}
        if offset is not None:
            body["offset"] = offset
        return await self._post_method_list("getUpdates", body)

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        *,
        parse_mode: str | None = None,
        reply_to_message_id: int | None = None,
    ) -> int:
        """Send text to chat_id; returns new message_id (L2)."""
        body: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode is not None:
            body["parse_mode"] = parse_mode
        if reply_to_message_id is not None:
            body["reply_to_message_id"] = reply_to_message_id
        result = await self._post_method("sendMessage", body, chat_id=chat_id)
        msg_id = result.get("message_id")
        if msg_id is None:
            raise RuntimeError("sendMessage response missing message_id")
        return int(msg_id)

    async def edit_message(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        """Edit a previously-sent message (L2)."""
        body: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": int(message_id),
            "text": text,
        }
        if parse_mode is not None:
            body["parse_mode"] = parse_mode
        return await self._post_method("editMessageText", body, chat_id=chat_id)

    async def delete_message(self, chat_id: int | str, message_id: int) -> bool:
        """Delete a message (L3)."""
        body = {"chat_id": chat_id, "message_id": int(message_id)}
        await self._post_method("deleteMessage", body, chat_id=chat_id)
        return True

    async def copy_message(
        self,
        from_chat_id: int | str,
        message_id: int,
        to_chat_id: int | str,
    ) -> int:
        """Copy a message (for archive snapshots). Returns new message_id."""
        body = {
            "chat_id": to_chat_id,
            "from_chat_id": from_chat_id,
            "message_id": int(message_id),
        }
        result = await self._post_method("copyMessage", body, chat_id=to_chat_id)
        msg_id = result.get("message_id")
        if msg_id is None:
            raise RuntimeError("copyMessage response missing message_id")
        return int(msg_id)

    async def send_photo(
        self,
        chat_id: int | str,
        photo: str,
        *,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> int:
        """Send a photo (L2). Photo can be file_id, URL, or bytes."""
        body: dict[str, Any] = {"chat_id": chat_id, "photo": photo}
        if caption is not None:
            body["caption"] = caption
        if parse_mode is not None:
            body["parse_mode"] = parse_mode
        result = await self._post_method("sendPhoto", body, chat_id=chat_id)
        msg_id = result.get("message_id")
        if msg_id is None:
            raise RuntimeError("sendPhoto response missing message_id")
        return int(msg_id)

    async def send_document(
        self,
        chat_id: int | str,
        document: str,
        *,
        caption: str | None = None,
    ) -> int:
        """Send a document (L2)."""
        body: dict[str, Any] = {"chat_id": chat_id, "document": document}
        if caption is not None:
            body["caption"] = caption
        result = await self._post_method("sendDocument", body, chat_id=chat_id)
        msg_id = result.get("message_id")
        if msg_id is None:
            raise RuntimeError("sendDocument response missing message_id")
        return int(msg_id)

    async def health(self) -> bool:
        """Health probe: GET /getMe -> True if ok=true."""
        if self._client is None:
            return False
        try:
            resp = await self._client.get(self._method_url("getMe"))
            if resp.status_code != 200:
                return False
            data = self._safe_json(resp)
            return bool(data.get("ok", False))
        except Exception as e:
            logger.debug(f"{self.LOG_PREFIX}.health_error", error=str(e))
            return False

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.debug(f"{self.LOG_PREFIX}.aclose_error", error=str(e))


# ---- Main adapter ----


class TelegramAdapter(ChannelSender):
    """Telegram channel adapter (httpx Bot API).

    Preserves core channel logic from two source implementations:
    - Bot API client (token-in-URL, per-chat throttle, 429 retry_after,
      safe logging)
    - Integration adapter (send/edit/delete/get_updates + media + copy)
    - Pre-delete snapshot via copyMessage for archive
    - Envelope DTOs (inbound + outbound)

    Stripped: BaseIntegrationAdapter dependency,
    BasePlatformAdapter, python-telegram-bot dependency.

    CONFIG_MISSING: when sec-telegram-bot-token is not provisioned (D2).
    """

    def __init__(self) -> None:
        self._config_missing_reasons = _check_config()
        self._client: TelegramClient | None = None
        self._archive_chat_id: int | str | None = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Telegram Bot API client if token is available."""
        if self._config_missing_reasons:
            return
        import os

        token = (
            os.environ.get("SEC_TELEGRAM_BOT_TOKEN", "")
            or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        ).strip()
        if token:
            try:
                self._client = TelegramClient(token=token)
            except Exception as exc:
                logger.warning("telegram_client_init_failed", error=str(exc))

    @property
    def channel_id(self) -> str:
        return "telegram"

    @property
    def is_config_missing(self) -> bool:
        return bool(self._config_missing_reasons)

    @property
    def config_missing_reasons(self) -> list[str]:
        return list(self._config_missing_reasons)

    @property
    def client(self) -> TelegramClient | None:
        return self._client

    async def health_check(self) -> bool:
        """Check Telegram connectivity."""
        if self._client is None:
            return False
        return await self._client.health()

    async def send_message(
        self,
        target: str,
        body: str,
        **kwargs: Any,
    ) -> SendResult:
        """Send a Telegram message (L2 action).

        Args:
            target: Chat ID.
            body: Message text.
            **kwargs: parse_mode, reply_to_message_id, etc.

        Returns:
            SendResult with success/failure.
        """
        if self.is_config_missing:
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=target,
                error=f"CONFIG_MISSING: {'; '.join(self._config_missing_reasons)}",
            )
        if self._client is None:
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=target,
                error="Telegram client not initialized",
            )

        try:
            chat_id = int(target) if target.lstrip("-").isdigit() else target
            message_id = await self._client.send_message(
                chat_id,
                body,
                parse_mode=kwargs.get("parse_mode"),
                reply_to_message_id=kwargs.get("reply_to_message_id"),
            )
            return SendResult(
                success=True,
                channel=self.channel_id,
                target=target,
                message_id=str(message_id),
            )
        except Exception as exc:
            logger.error("telegram send_message failed: %s", exc, exc_info=True)
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=target,
                error=str(exc),
            )

    async def edit_message(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
    ) -> SendResult:
        """Edit a Telegram message (L2 action)."""
        if self.is_config_missing or self._client is None:
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=str(chat_id),
                error="CONFIG_MISSING or client not initialized",
            )
        try:
            await self._client.edit_message(chat_id, message_id, text, parse_mode=parse_mode)
            return SendResult(
                success=True,
                channel=self.channel_id,
                target=str(chat_id),
                message_id=str(message_id),
            )
        except Exception as exc:
            logger.error("telegram edit_message failed: %s", exc, exc_info=True)
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=str(chat_id),
                error=str(exc),
            )

    async def delete_message(self, chat_id: int | str, message_id: int) -> SendResult:
        """Delete a Telegram message with pre-delete snapshot (L3 action).

        If archive_chat_id is set, copies the message before deleting.
        """
        if self.is_config_missing or self._client is None:
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=str(chat_id),
                error="CONFIG_MISSING or client not initialized",
            )
        try:
            # Pre-delete snapshot via copyMessage.
            snapshot_id: int | None = None
            if self._archive_chat_id is not None:
                try:
                    snapshot_id = await self._client.copy_message(
                        chat_id, message_id, self._archive_chat_id,
                    )
                    logger.info(
                        "telegram_pre_delete_snapshot",
                        chat_id=chat_id,
                        message_id=message_id,
                        snapshot_id=snapshot_id,
                    )
                except Exception as exc:
                    logger.warning(
                        "telegram_snapshot_failed",
                        error=str(exc),
                        message_id=message_id,
                    )

            await self._client.delete_message(chat_id, message_id)
            return SendResult(
                success=True,
                channel=self.channel_id,
                target=str(chat_id),
                message_id=str(message_id),
            )
        except Exception as exc:
            logger.error("telegram delete_message failed: %s", exc, exc_info=True)
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=str(chat_id),
                error=str(exc),
            )

    async def get_updates(
        self,
        *,
        timeout: int = 25,
        limit: int = 100,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get pending updates via long-polling (L1 action)."""
        if self._client is None:
            return []
        try:
            return await self._client.get_updates(
                timeout=timeout, limit=limit, offset=offset,
            )
        except Exception as exc:
            logger.warning("telegram_get_updates_failed", error=str(exc))
            return []

    async def send_photo(
        self,
        chat_id: int | str,
        photo: str,
        *,
        caption: str | None = None,
    ) -> SendResult:
        """Send a photo (L2 action)."""
        if self.is_config_missing or self._client is None:
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=str(chat_id),
                error="CONFIG_MISSING or client not initialized",
            )
        try:
            message_id = await self._client.send_photo(chat_id, photo, caption=caption)
            return SendResult(
                success=True,
                channel=self.channel_id,
                target=str(chat_id),
                message_id=str(message_id),
            )
        except Exception as exc:
            logger.error("telegram send_photo failed: %s", exc, exc_info=True)
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=str(chat_id),
                error=str(exc),
            )

    async def send_document(
        self,
        chat_id: int | str,
        document: str,
        *,
        caption: str | None = None,
    ) -> SendResult:
        """Send a document (L2 action)."""
        if self.is_config_missing or self._client is None:
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=str(chat_id),
                error="CONFIG_MISSING or client not initialized",
            )
        try:
            message_id = await self._client.send_document(chat_id, document, caption=caption)
            return SendResult(
                success=True,
                channel=self.channel_id,
                target=str(chat_id),
                message_id=str(message_id),
            )
        except Exception as exc:
            logger.error("telegram send_document failed: %s", exc, exc_info=True)
            return SendResult(
                success=False,
                channel=self.channel_id,
                target=str(chat_id),
                error=str(exc),
            )

    async def aclose(self) -> None:
        """Release resources."""
        if self._client is not None:
            await self._client.aclose()

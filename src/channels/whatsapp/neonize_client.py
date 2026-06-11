from __future__ import annotations

"""Neonize client wrapper and event lifecycle for P11 Wave 1."""

import asyncio
import hashlib
from collections.abc import Awaitable, Callable, Coroutine
from concurrent.futures import Future
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import redis.asyncio as aioredis
import structlog
from neonize import NewClient
from neonize.events import (
    ConnectedEv,
    ConnectFailureEv,
    DisconnectedEv,
    Event,
    KeepAliveTimeoutEv,
    LoggedOutEv,
    MessageEv,
    PairStatusEv,
)
from neonize.utils.jid import JID, build_jid

from .auth import AuthMethod, SessionState, WhatsAppAuthManager, build_whatsapp_redis_client
from .reconnection import ReconnectionHandler

logger = structlog.get_logger()


class EventType(StrEnum):
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PAIR_SUCCESS = "pair_success"
    PAIR_FAILED = "pair_failed"
    RECONNECT_ATTEMPT = "reconnect_attempt"
    RECONNECT_EXHAUSTED = "reconnect_exhausted"
    ERROR = "error"


@dataclass(slots=True)
class WhatsAppEvent:
    event_type: EventType
    timestamp: datetime
    jid_hash: str | None = None
    message_type: str = "unknown"
    byte_length: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


MessageHandler = Callable[[WhatsAppEvent], Coroutine[Any, Any, None] | None]
QrHandler = Callable[[bytes], None]
PairCodeHandler = Callable[[str, bool], None]


class NeonizeClient:
    def __init__(
        self,
        *,
        name: str = "guinevere-whatsapp",
        redis_client: aioredis.Redis | None = None,
        auth_manager: WhatsAppAuthManager | None = None,
    ) -> None:
        self._redis: aioredis.Redis = redis_client or build_whatsapp_redis_client()
        self._auth: WhatsAppAuthManager = auth_manager or WhatsAppAuthManager(redis_client=self._redis)
        self._database_path: str = str(self._auth.session_dir / "neonize.db")
        self._client: NewClient = NewClient(self._database_path, uuid=name)
        self._message_handlers: list[MessageHandler] = []
        self._qr_handler: QrHandler | None = None
        self._paircode_handler: PairCodeHandler | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._reconnect: ReconnectionHandler = ReconnectionHandler(
            redis_client=self._redis,
            reconnect_callback=self._attempt_reconnect,
        )
        self._register_handlers(self._client.event)

    @property
    def client(self) -> NewClient:
        return self._client

    @property
    def is_connected(self) -> bool:
        return bool(getattr(self._client, "is_connected", False))

    @property
    def is_logged_in(self) -> bool:
        return bool(getattr(self._client, "is_logged_in", False))

    def set_qr_handler(self, handler: QrHandler) -> None:
        self._qr_handler = handler

    def set_paircode_handler(self, handler: PairCodeHandler) -> None:
        self._paircode_handler = handler

    def add_message_handler(self, handler: MessageHandler) -> None:
        self._message_handlers.append(handler)

    async def connect(self) -> None:
        self._loop = asyncio.get_running_loop()
        _ = await self._auth.ensure_runtime_dir()
        await asyncio.to_thread(self._client.connect)

    async def disconnect(self) -> None:
        await asyncio.to_thread(self._client.disconnect)

    async def stop(self) -> None:
        await asyncio.to_thread(self._client.stop)

    async def pair_phone(
        self,
        phone_number: str,
        *,
        show_push_notification: bool = False,
    ) -> str:
        return await self._auth.generate_pairing_code(
            self._client,
            phone_number,
            show_push_notification=show_push_notification,
        )

    async def send_text(self, phone_number: str, body: str) -> Any:
        jid = build_jid(phone_number)
        response = await asyncio.to_thread(self._client.send_message, jid, body)
        self._reconnect.record_sent()
        return response

    async def send_chat_presence(self, jid: JID, state: Any, media: Any) -> str:
        return await asyncio.to_thread(self._client.send_chat_presence, jid, state, media)

    async def send_presence(self, presence: Any) -> None:
        await asyncio.to_thread(self._client.send_presence, presence)

    async def close(self) -> None:
        await self._auth.close()
        await self._redis.aclose()

    def _register_handlers(self, event_bus: Event) -> None:
        event_bus.qr(self._on_qr)
        event_bus.paircode(self._on_paircode)
        event_bus(ConnectedEv)(self._on_connected)
        event_bus(DisconnectedEv)(self._on_disconnected)
        event_bus(ConnectFailureEv)(self._on_connect_failure)
        event_bus(KeepAliveTimeoutEv)(self._on_keepalive_timeout)
        event_bus(MessageEv)(self._on_message)
        event_bus(PairStatusEv)(self._on_pair_status)
        event_bus(LoggedOutEv)(self._on_logged_out)

    def _schedule(self, coro: Coroutine[Any, Any, Any]) -> Future[Any] | asyncio.Task[Any] | None:
        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(coro)
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                logger.warning("whatsapp_event_without_running_loop")
                coro.close()
                return None
            return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _on_qr(self, _: NewClient, data_qr: bytes) -> None:
        logger.info("whatsapp_qr_emitted", size_bytes=len(data_qr))
        if self._qr_handler is not None:
            self._qr_handler(data_qr)
        self._schedule(self._auth.update_state(SessionState.PAIRING, auth_method=AuthMethod.QR_SCAN))

    def _on_paircode(self, _: NewClient, code: str, connected: bool) -> None:
        logger.info("whatsapp_paircode_emitted", connected=connected)
        if self._paircode_handler is not None:
            self._paircode_handler(code, connected)

    def _on_connected(self, _: NewClient, message: ConnectedEv) -> None:
        status = getattr(message, "status", None)
        logger.info("whatsapp_connected_event", status=status)
        self._schedule(self._handle_connected())

    def _on_disconnected(self, _: NewClient, message: DisconnectedEv) -> None:
        status = getattr(message, "status", None)
        logger.warning("whatsapp_disconnected_event", status=status)
        self._schedule(self._reconnect.on_disconnected(str(status)))

    def _on_connect_failure(self, _: NewClient, message: ConnectFailureEv) -> None:
        reason = getattr(message, "Reason", None)
        detail = getattr(message, "Message", None)
        logger.warning("whatsapp_connect_failure_event", reason=reason, detail=detail)
        self._schedule(self._reconnect.on_disconnected(f"connect_failure:{reason}:{detail}"))

    def _on_keepalive_timeout(self, _: NewClient, message: KeepAliveTimeoutEv) -> None:
        error_count = getattr(message, "ErrorCount", None)
        last_success = getattr(message, "LastSuccess", None)
        logger.warning(
            "whatsapp_keepalive_timeout_event",
            error_count=error_count,
            last_success=last_success,
        )
        self._schedule(self._reconnect.on_disconnected("keepalive_timeout"))

    def _on_logged_out(self, _: NewClient, message: LoggedOutEv) -> None:
        logger.warning("whatsapp_logged_out_event", message_type=type(message).__name__)
        self._schedule(self._reconnect.on_disconnected("logged_out"))

    def _on_pair_status(self, _: NewClient, message: PairStatusEv) -> None:
        status = getattr(message, "Status", None)
        error = getattr(message, "Error", None)
        business_name = getattr(message, "BusinessName", None)
        logger.info(
            "whatsapp_pair_status_event",
            status=status,
            error=error,
            business_name=business_name,
        )
        self._schedule(self._handle_pair_status(status=status, error=error))

    def _on_message(self, _: NewClient, message: MessageEv) -> None:
        event = self._normalize_message_event(message)
        self._reconnect.record_received()
        logger.info(
            "whatsapp_message_event",
            jid_hash=event.jid_hash,
            message_type=event.message_type,
            byte_length=event.byte_length,
        )
        for handler in self._message_handlers:
            result = handler(event)
            if asyncio.iscoroutine(result):
                self._schedule(result)

    async def _handle_connected(self) -> None:
        metadata = await self._auth.mark_phone_online()
        await self._reconnect.mark_session_age(metadata.paired_at)
        await self._reconnect.on_connected()

    async def _handle_pair_status(self, *, status: Any, error: Any) -> None:
        normalized_status = str(status or "").lower()
        numeric_status: int | None
        try:
            numeric_status = int(status) if status is not None else None
        except (TypeError, ValueError):
            numeric_status = None

        if numeric_status == 2 or any(token in normalized_status for token in ["paired", "connected", "success"]):
            _ = await self._auth.update_state(SessionState.PAIRED)
            _ = await self._auth.mark_phone_online()
            return

        if numeric_status == 1 or error:
            _ = await self._auth.update_state(
                SessionState.ERROR,
                error=str(error) if error else f"pair_status={status}",
            )

    async def _attempt_reconnect(self) -> bool:
        try:
            if self.is_connected:
                await self.disconnect()
            await self.connect()
            return self.is_connected or self.is_logged_in
        except Exception as exc:  # noqa: BLE001
            logger.warning("whatsapp_reconnect_attempt_exception", error=str(exc))
            return False

    def _normalize_message_event(self, message: MessageEv) -> WhatsAppEvent:
        info = getattr(message, "Info", None)
        raw_jid = self._extract_sender_jid(info)
        chat_jid = self._extract_chat_jid(info) or raw_jid
        timestamp = self._extract_timestamp(info)
        body = self._extract_body(message)
        message_type = self._extract_message_type(message)
        push_name = self._optional_str(getattr(info, "Pushname", None))
        message_id = self._optional_str(getattr(info, "ID", None))
        raw_bytes = getattr(message, "Raw", b"")
        if isinstance(raw_bytes, str):
            raw_bytes = raw_bytes.encode("utf-8", errors="ignore")
        byte_length = len(raw_bytes) if isinstance(raw_bytes, (bytes, bytearray)) else 0
        return WhatsAppEvent(
            event_type=EventType.MESSAGE_RECEIVED,
            timestamp=timestamp,
            jid_hash=self._hash_jid(raw_jid) if raw_jid else None,
            message_type=message_type,
            byte_length=byte_length,
            metadata={
                "retry_count": getattr(message, "RetryCount", None),
                "raw_jid": raw_jid,
                "chat_jid": chat_jid,
                "message_id": message_id,
                "body": body,
                "push_name": push_name,
                "timestamp": timestamp,
                "media_type": None if message_type == "message" else message_type,
                "media_size_bytes": byte_length if byte_length > 0 else None,
            },
        )

    def _extract_message_type(self, message: MessageEv) -> str:
        payload = getattr(message, "Message", None)
        if getattr(message, "IsDocumentWithCaption", False) or getattr(payload, "documentMessage", None):
            return "document"
        if getattr(message, "IsLottieSticker", False) or getattr(payload, "stickerMessage", None):
            return "sticker"
        if getattr(payload, "imageMessage", None):
            return "image"
        if getattr(payload, "audioMessage", None):
            return "audio"
        if getattr(payload, "videoMessage", None):
            return "video"
        if getattr(payload, "contactMessage", None):
            return "contact"
        if getattr(payload, "locationMessage", None) or getattr(payload, "liveLocationMessage", None):
            return "location"
        if getattr(message, "IsViewOnce", False) or getattr(message, "IsViewOnceV2", False):
            return "view_once"
        if payload is not None:
            return "message"
        return "unknown"

    def _extract_sender_jid(self, info: Any) -> str | None:
        if info is None:
            return None
        source = getattr(info, "MessageSource", None)
        candidates = []
        if source is not None:
            candidates.extend(
                [
                    getattr(source, "SenderAlt", None),
                    getattr(source, "RecipientAlt", None),
                    getattr(source, "Sender", None),
                    getattr(source, "Chat", None),
                ]
            )
        candidates.extend(
            [
                getattr(info, "SenderAlt", None),
                getattr(info, "RecipientAlt", None),
                getattr(info, "Sender", None),
                getattr(info, "Chat", None),
            ]
        )
        return self._prefer_personal_jid(*candidates)

    def _extract_chat_jid(self, info: Any) -> str | None:
        if info is None:
            return None
        source = getattr(info, "MessageSource", None)
        candidates = []
        if source is not None:
            candidates.extend(
                [
                    getattr(source, "Chat", None),
                    getattr(source, "RecipientAlt", None),
                    getattr(source, "SenderAlt", None),
                    getattr(source, "Sender", None),
                ]
            )
        candidates.extend(
            [
                getattr(info, "Chat", None),
                getattr(info, "RecipientAlt", None),
                getattr(info, "SenderAlt", None),
                getattr(info, "Sender", None),
            ]
        )
        return self._prefer_personal_jid(*candidates)

    def _prefer_personal_jid(self, *candidates: Any) -> str | None:
        personal: list[str] = []
        fallback: list[str] = []
        for candidate in candidates:
            jid = self._jid_to_string(candidate)
            if not jid:
                continue
            if jid.endswith("@s.whatsapp.net"):
                personal.append(jid)
            else:
                fallback.append(jid)
        if personal:
            return personal[0]
        if fallback:
            return fallback[0]
        return None

    def _jid_to_string(self, candidate: Any) -> str | None:
        if candidate is None:
            return None
        user = self._optional_str(getattr(candidate, "User", ""))
        server = self._optional_str(getattr(candidate, "Server", ""))
        if user and server:
            return f"{user}@{server}"
        return None

    def _first_valid_jid(self, *candidates: Any) -> str | None:
        for candidate in candidates:
            jid = self._jid_to_string(candidate)
            if jid:
                return jid
        return None

    def _extract_timestamp(self, info: Any) -> datetime:
        timestamp = getattr(info, "Timestamp", None) if info is not None else None
        if timestamp is None:
            return datetime.now(UTC)
        try:
            return datetime.fromtimestamp(int(timestamp), tz=UTC)
        except (TypeError, ValueError, OSError):
            return datetime.now(UTC)

    def _extract_body(self, message: MessageEv) -> str:
        payload = getattr(message, "Message", None)
        if payload is None:
            return ""
        for candidate in (
            self._optional_str(getattr(payload, "conversation", None)),
            self._optional_str(getattr(getattr(payload, "extendedTextMessage", None), "text", None)),
            self._optional_str(getattr(getattr(payload, "imageMessage", None), "caption", None)),
            self._optional_str(getattr(getattr(payload, "videoMessage", None), "caption", None)),
            self._optional_str(getattr(getattr(payload, "documentWithCaptionMessage", None), "caption", None)),
            self._optional_str(getattr(getattr(payload, "documentMessage", None), "caption", None)),
        ):
            if candidate:
                return candidate
        return ""

    def _optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _hash_jid(self, raw_jid: str) -> str:
        return hashlib.sha256(raw_jid.encode("utf-8")).hexdigest()[:12]

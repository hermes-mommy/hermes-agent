from __future__ import annotations

"""WhatsApp ingress / egress adapter for P11 Wave 2.

This module is the only place where downstream code deals directly with
Neonize-style event payloads. All downstream consumers receive canonical
`WhatsAppMessageEnvelope` / `WhatsAppDeliveryEnvelope` DTOs instead.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Any

import structlog
from neonize.proto import Neonize_pb2 as pb

from .envelope import (
    WhatsAppDeliveryEnvelope,
    WhatsAppMessageEnvelope,
    ensure_utc_timestamp,
    normalize_jid,
    safe_int,
    to_jid,
)
from .neonize_client import NeonizeClient, WhatsAppEvent

logger = structlog.get_logger()

_COMPOSING = getattr(pb, "_CHATPRESENCE_CHATPRESENCE").values_by_name["COMPOSING"].number
_PAUSED = getattr(pb, "_CHATPRESENCE_CHATPRESENCE").values_by_name["PAUSED"].number
_TEXT_MEDIA = getattr(pb, "_CHATPRESENCE_CHATPRESENCEMEDIA").values_by_name["TEXT"].number
_READ_RECEIPT = getattr(pb, "_RECEIPT_RECEIPTTYPE").values_by_name["READ"].number


InboundHandler = Callable[[WhatsAppMessageEnvelope], Any | Awaitable[Any]]


class WhatsAppIngressEgressAdapter:
    """Flat WhatsApp-specific adapter layer.

    Responsibilities:
    - normalize inbound WA events into canonical envelopes
    - silently ignore group traffic at ingress
    - provide simple outbound send semantics with presence/read markers
    - isolate downstream code from Neonize event/proto details
    """

    def __init__(self, client: NeonizeClient, *, max_typing_seconds: float = 5.0) -> None:
        self._client: NeonizeClient = client
        self._max_typing_seconds: float = max_typing_seconds
        self._client.add_message_handler(self._on_whatsapp_event)
        self._inbound_handlers: list[InboundHandler] = []

    def add_inbound_handler(self, handler: InboundHandler) -> None:
        self._inbound_handlers.append(handler)

    async def _on_whatsapp_event(self, event: WhatsAppEvent) -> None:
        envelope = self.from_whatsapp_event(event)
        if envelope is None:
            return

        # Download image bytes for image messages via Neonize.
        if envelope.media_type == "image":
            raw_e2e = event.metadata.get("raw_e2e_message")
            if raw_e2e is not None:
                try:
                    image_bytes: bytes = await asyncio.to_thread(
                        self._client.client.download_any, raw_e2e,
                    )
                    if image_bytes:
                        envelope = replace(envelope, image_bytes=image_bytes)
                        logger.info(
                            "whatsapp_image_downloaded",
                            message_id=envelope.message_id,
                            size_bytes=len(image_bytes),
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "whatsapp_image_download_failed",
                        message_id=envelope.message_id,
                        error=str(exc),
                    )

        for handler in self._inbound_handlers:
            result = handler(envelope)
            if asyncio.iscoroutine(result):
                await result

    def from_whatsapp_event(self, event: WhatsAppEvent) -> WhatsAppMessageEnvelope | None:
        raw_jid = str(event.metadata.get("raw_jid") or "").strip()
        if not raw_jid:
            logger.warning("whatsapp_event_missing_raw_jid")
            return None

        chat_jid = str(event.metadata.get("chat_jid") or raw_jid).strip()
        is_group = chat_jid.endswith("@g.us")
        if is_group:
            logger.info("whatsapp_group_message_ignored", chat_jid=chat_jid)
            return None

        body = str(event.metadata.get("body") or "")
        push_name = self._optional_str(event.metadata.get("push_name"))
        reply_to_id = self._optional_str(event.metadata.get("reply_to_id"))
        message_id = self._optional_str(event.metadata.get("message_id")) or self._derive_message_id(event)
        media_type = self._optional_str(event.metadata.get("media_type"))
        media_size_bytes = safe_int(event.metadata.get("media_size_bytes"))

        envelope = WhatsAppMessageEnvelope(
            sender_jid_hash=event.jid_hash or self._client._hash_jid(raw_jid),
            sender_raw_jid=raw_jid,
            message_id=message_id,
            timestamp=ensure_utc_timestamp(event.metadata.get("timestamp") or event.timestamp),
            body=body,
            chat_jid=chat_jid,
            is_group=is_group,
            reply_to_id=reply_to_id,
            push_name=push_name,
            media_type=media_type,
            media_size_bytes=media_size_bytes,
        )
        envelope.validate()
        return envelope

    async def send(self, delivery: WhatsAppDeliveryEnvelope, *, source_message: WhatsAppMessageEnvelope | None = None) -> Any:
        delivery.validate()
        target_jid = to_jid(delivery.target_jid)
        phone_number = normalize_jid(target_jid)
        jid_proto = self._build_target_jid(phone_number)

        await self._send_typing(jid_proto, composing=True)
        await asyncio.sleep(self._natural_delay(delivery.body))
        try:
            response = await self._client.send_text(phone_number, delivery.body)
        finally:
            await self._send_typing(jid_proto, composing=False)

        if source_message is not None:
            await self._mark_read(source_message)
        return response

    async def send_text(self, jid: str, body: str, *, reply_to_id: str | None = None) -> Any:
        envelope = WhatsAppDeliveryEnvelope(target_jid=jid, body=body, reply_to_id=reply_to_id)
        return await self.send(envelope)

    def _build_target_jid(self, phone_number: str) -> Any:
        user = normalize_jid(phone_number)
        return pb.JID(User=user, Server="s.whatsapp.net")

    async def _send_typing(self, jid: Any, *, composing: bool) -> None:
        state = _COMPOSING if composing else _PAUSED
        try:
            _ = await self._client.send_chat_presence(jid, state, _TEXT_MEDIA)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "whatsapp_presence_send_failed",
                composing=composing,
                error=str(exc),
            )

    async def _mark_read(self, source_message: WhatsAppMessageEnvelope) -> None:
        try:
            chat_jid = self._jid_from_string(source_message.chat_jid)
            sender_jid = self._jid_from_string(source_message.sender_raw_jid)
            await asyncio.to_thread(
                self._client.client.mark_read,
                source_message.message_id,
                chat=chat_jid,
                sender=sender_jid,
                receipt=_READ_RECEIPT,
                timestamp=int(source_message.timestamp.timestamp()),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("whatsapp_mark_read_failed", error=str(exc))

    def _jid_from_string(self, jid: str) -> Any:
        normalized = to_jid(jid)
        user, server = normalized.split("@", 1)
        if ":" in user:
            user, _device = user.split(":", 1)
        return pb.JID(User=user, Server=server)

    def _derive_message_id(self, event: WhatsAppEvent) -> str:
        metadata_id = self._optional_str(event.metadata.get("server_id"))
        if metadata_id:
            return metadata_id
        ts = int(event.timestamp.timestamp())
        return f"wa-{event.jid_hash or 'unknown'}-{ts}"

    def _natural_delay(self, body: str) -> float:
        if not body:
            return 0.25
        chars = max(len(body), 1)
        return min(max(chars / 40.0, 0.25), self._max_typing_seconds)

    def _optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

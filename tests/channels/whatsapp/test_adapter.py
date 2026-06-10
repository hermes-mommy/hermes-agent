from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.channels.whatsapp.adapter import WhatsAppIngressEgressAdapter
from src.channels.whatsapp.envelope import WhatsAppDeliveryEnvelope, WhatsAppMessageEnvelope
from src.channels.whatsapp.neonize_client import EventType, WhatsAppEvent


class DummyClient:
    def __init__(self) -> None:
        self.handlers = []
        self.sent: list[tuple[str, str]] = []
        self.presence: list[tuple[object, object, object]] = []
        self._mark_read_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.client = SimpleNamespace(mark_read=self._mark_read)

    def add_message_handler(self, handler):
        self.handlers.append(handler)

    async def send_text(self, phone_number: str, body: str):
        self.sent.append((phone_number, body))
        return {"phone_number": phone_number, "body": body}

    async def send_chat_presence(self, jid, state, media):
        self.presence.append((jid, state, media))
        return "ok"

    def _hash_jid(self, raw_jid: str) -> str:
        return "hash-" + raw_jid.split("@", 1)[0]

    def _mark_read(self, *args, **kwargs):
        self._mark_read_calls.append((args, kwargs))
        return None


@pytest.mark.asyncio
async def test_adapter_registers_itself_and_normalizes_event() -> None:
    client = DummyClient()
    adapter = WhatsAppIngressEgressAdapter(client)

    assert len(client.handlers) == 1

    event = WhatsAppEvent(
        event_type=EventType.MESSAGE_RECEIVED,
        timestamp=datetime.now(UTC),
        jid_hash="hash-628123",
        message_type="image",
        byte_length=10,
        metadata={
            "raw_jid": "628123@s.whatsapp.net",
            "chat_jid": "628123@s.whatsapp.net",
            "message_id": "wamid-1",
            "body": "hello",
            "push_name": "Faiz",
            "reply_to_id": "wamid-0",
            "media_type": "image",
            "media_size_bytes": 10,
        },
    )

    envelope = adapter.from_whatsapp_event(event)
    assert envelope is not None
    assert isinstance(envelope, WhatsAppMessageEnvelope)
    assert envelope.sender_raw_jid == "628123@s.whatsapp.net"
    assert envelope.body == "hello"
    assert envelope.media_type == "image"
    assert envelope.media_size_bytes == 10


def test_group_messages_are_ignored() -> None:
    client = DummyClient()
    adapter = WhatsAppIngressEgressAdapter(client)
    event = WhatsAppEvent(
        event_type=EventType.MESSAGE_RECEIVED,
        timestamp=datetime.now(UTC),
        jid_hash="hash-group",
        message_type="message",
        byte_length=0,
        metadata={
            "raw_jid": "628123@s.whatsapp.net",
            "chat_jid": "120363999999@g.us",
            "message_id": "wamid-1",
            "body": "hello",
        },
    )

    assert adapter.from_whatsapp_event(event) is None


@pytest.mark.asyncio
async def test_send_uses_presence_and_mark_read() -> None:
    client = DummyClient()
    adapter = WhatsAppIngressEgressAdapter(client, max_typing_seconds=0.0)
    source = WhatsAppMessageEnvelope(
        sender_jid_hash="hash-628123",
        sender_raw_jid="628123@s.whatsapp.net",
        message_id="wamid-1",
        timestamp=datetime.now(UTC),
        body="hello",
        chat_jid="628123@s.whatsapp.net",
        is_group=False,
    )
    delivery = WhatsAppDeliveryEnvelope(target_jid="628123", body="reply")

    result = await adapter.send(delivery, source_message=source)

    assert result == {"phone_number": "628123", "body": "reply"}
    assert client.sent == [("628123", "reply")]
    assert len(client.presence) == 2
    assert len(client._mark_read_calls) == 1

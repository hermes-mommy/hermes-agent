from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.channels.whatsapp.envelope import WhatsAppMessageEnvelope
from src.channels.whatsapp.router import WhatsAppRouter


class DummyBridge:
    async def process(self, envelope: WhatsAppMessageEnvelope) -> str:
        return f"bridge:{envelope.body}"

    async def invoke(self, envelope: WhatsAppMessageEnvelope):
        from src.channels.whatsapp.bridge import HermesResult

        return HermesResult(response_text=f"bridge:{envelope.body}", metadata={}, user_id="u", system_prompt="p")


class DummyCommands:
    async def handle(self, command_name: str, command_args: list[str], envelope: WhatsAppMessageEnvelope) -> str:
        return f"cmd:{command_name}:{','.join(command_args)}:{envelope.sender_raw_jid}"


class DummyFormatter:
    def format(self, raw_response: str) -> list[str]:
        return [raw_response]


class DummyAdapter:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send(self, delivery, *, source_message=None):
        self.sent.append((delivery.target_jid, delivery.body))
        return {"ok": True}


class DummyPresence:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []

    async def start_typing(self, jid: str) -> None:
        self.started.append(jid)

    async def stop_typing(self, jid: str) -> None:
        self.stopped.append(jid)


@pytest.fixture
def envelope() -> WhatsAppMessageEnvelope:
    return WhatsAppMessageEnvelope(
        sender_jid_hash="abc123",
        sender_raw_jid="628123456789@s.whatsapp.net",
        message_id="mid-1",
        timestamp=datetime.now(UTC),
        body="hello",
        chat_jid="628123456789@s.whatsapp.net",
        is_group=False,
        sender_identity="Faiz",
    )


@pytest.mark.asyncio
async def test_router_routes_conversation(envelope: WhatsAppMessageEnvelope) -> None:
    adapter = DummyAdapter()
    presence = DummyPresence()
    router = WhatsAppRouter(
        bridge=DummyBridge(),
        commands=DummyCommands(),
        formatter=DummyFormatter(),
        adapter=adapter,
        presence=presence,
    )

    chunks = await router.route(envelope)

    assert chunks == ["bridge:hello"]
    assert adapter.sent == [("628123456789@s.whatsapp.net", "bridge:hello")]
    assert presence.started == ["628123456789@s.whatsapp.net"]
    assert presence.stopped == ["628123456789@s.whatsapp.net"]


@pytest.mark.asyncio
async def test_router_routes_command() -> None:
    adapter = DummyAdapter()
    presence = DummyPresence()
    router = WhatsAppRouter(
        bridge=DummyBridge(),
        commands=DummyCommands(),
        formatter=DummyFormatter(),
        adapter=adapter,
        presence=presence,
    )
    envelope = WhatsAppMessageEnvelope(
        sender_jid_hash="abc123",
        sender_raw_jid="628123456789@s.whatsapp.net",
        message_id="mid-1",
        timestamp=datetime.now(UTC),
        body="/status extra",
        chat_jid="628123456789@s.whatsapp.net",
        is_group=False,
        sender_identity="Faiz",
    )

    chunks = await router.route(envelope)

    assert chunks == ["cmd:status:extra:628123456789@s.whatsapp.net"]
    assert adapter.sent == [("628123456789@s.whatsapp.net", "cmd:status:extra:628123456789@s.whatsapp.net")]

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.channels.whatsapp.presence import TypingIndicator


class DummyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, object]] = []
        self.client = SimpleNamespace()

    async def send_chat_presence(self, jid, state, media):
        self.calls.append((jid, state, media))
        return "ok"


@pytest.mark.asyncio
async def test_presence_start_stop_private_jid() -> None:
    client = DummyClient()
    presence = TypingIndicator(client, watchdog_seconds=999)

    await presence.start_typing("628123")
    await presence.stop_typing("628123")

    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_presence_ignores_group_jid() -> None:
    client = DummyClient()
    presence = TypingIndicator(client)

    await presence.start_typing("120363999999@g.us")
    await presence.stop_typing("120363999999@g.us")

    assert client.calls == []

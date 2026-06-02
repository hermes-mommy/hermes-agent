import sys
import types
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "discord" not in sys.modules:
    discord_stub = types.ModuleType("discord")
    setattr(
        discord_stub,
        "utils",
        types.SimpleNamespace(
            get=lambda iterable, **attrs: next(
                (
                    item
                    for item in iterable
                    if all(getattr(item, key, None) == value for key, value in attrs.items())
                ),
                None,
            )
        ),
    )
    sys.modules["discord"] = discord_stub

from src.discord.notifications import (
    NotificationEmbedData,
    _build_notification_data,
    send_alert,
)


class DummyChannel:
    def __init__(self, name: str) -> None:
        self.name = name
        self.send = AsyncMock(return_value=None)


class DummyBot:
    def __init__(self, channels: list[DummyChannel]) -> None:
        self._channels = channels

    def get_all_channels(self):
        return self._channels


@pytest.mark.parametrize(
    "sev,channel,color,ping,thread,tone_snippet",
    [
        ("SEV0", "system-health", 0xDC2626, True, True, "Urgent, neutral, no persona"),
        ("SEV1", "system-health", 0xCA8A04, False, False, "Alert, neutral"),
        ("SEV2", "cost-tracker", 0xCA8A04, False, False, "Informational"),
        ("SEV3", "guinevere-status", 0x6B21A8, False, False, "Status update"),
        ("SEV4", "audit-log", 0x6B7280, False, False, "Audit record"),
    ],
)
def test_build_notification_data_routes_each_sev(sev, channel, color, ping, thread, tone_snippet):
    data = _build_notification_data(sev, "Title", "Description", now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc))
    assert data.sev == sev
    assert data.channel_name == channel
    assert data.color == color
    assert data.ping_faiz is ping
    assert data.create_thread is thread
    assert tone_snippet in " | ".join(f.value for f in data.fields)
    assert data.title == f"[{sev}] Title"
    assert data.description == "Description"
    assert data.footer_text == "Guinevere de Baroque • System Alert"
    assert data.timestamp.endswith("WIB")


def test_build_notification_data_sev2_contains_budget_detail():
    data = _build_notification_data("SEV2", "Budget", "Over budget", now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc))
    assert any(field.name == "Budget Detail" for field in data.fields)


def test_build_notification_data_sev4_contains_timestamp_field():
    data = _build_notification_data("SEV4", "Audit", "Record", now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc))
    assert any(field.name == "Timestamp" for field in data.fields)


@pytest.mark.asyncio
async def test_send_alert_success_sev0_mentions_and_threads(monkeypatch):
    channel = DummyChannel("system-health")
    bot = DummyBot([channel])
    monkeypatch.setenv("GUINEVERE_FAIZ_MENTION", "<@123456789>")
    with patch("src.discord.notifications.to_discord_embed", return_value=Mock()) as build_embed:
        ok = await send_alert(bot, "SEV0", "Critical", "Down")
    assert ok is True
    build_embed.assert_called_once()
    channel.send.assert_awaited_once()
    await_args = channel.send.await_args
    assert await_args is not None
    kwargs = await_args.kwargs
    assert kwargs["content"] == "<@123456789>"
    assert kwargs.get("thread_name") is None


@pytest.mark.asyncio
async def test_send_alert_success_sev4_uses_audit_log_channel(monkeypatch):
    channel = DummyChannel("audit-log")
    bot = DummyBot([channel])
    monkeypatch.delenv("GUINEVERE_FAIZ_MENTION", raising=False)
    monkeypatch.delenv("FAIZ_MENTION", raising=False)
    with patch("src.discord.notifications.to_discord_embed", return_value=Mock()):
        ok = await send_alert(bot, "SEV4", "Audit", "Logged")
    assert ok is True
    await_args = channel.send.await_args
    assert await_args is not None
    kwargs = await_args.kwargs
    assert kwargs["content"].endswith("WIB")


@pytest.mark.asyncio
async def test_send_alert_channel_not_found_fails_soft():
    bot = DummyBot([])
    with patch("src.discord.notifications.to_discord_embed", return_value=Mock()):
        ok = await send_alert(bot, "SEV3", "Missing", "No channel")
    assert ok is False


@pytest.mark.asyncio
async def test_send_alert_invalid_sev_fails_soft():
    bot = DummyBot([DummyChannel("system-health")])
    with patch("src.discord.notifications.to_discord_embed", return_value=Mock()):
        ok = await send_alert(bot, "SEVX", "Bad", "Bad")
    assert ok is False


def test_notification_dataclass_is_frozen():
    with pytest.raises(FrozenInstanceError):
        data = NotificationEmbedData(title="A", description="B", color=1)
        data.title = "C"  # type: ignore[misc]  # frozen → FrozenInstanceError


def test_notification_text_has_no_persona_language():
    data = _build_notification_data("SEV1", "System Notice", "Plain description", now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc))
    text = " ".join([data.title, data.description, data.footer_text] + [f"{f.name} {f.value}" for f in data.fields])
    banned = ["mommy", "darling", "sayang", "punishment", "yandere", "persona"]
    assert not any(word in text.lower() for word in banned)

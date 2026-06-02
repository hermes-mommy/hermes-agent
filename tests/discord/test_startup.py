"""Deterministic tests for ``src.discord.startup``.

All tests run without a real ``discord.py`` runtime.  The ``on_ready``
handler is tested with a fake discord module (mocked via ``importlib``)
and a ``FakeClient`` that captures sent messages and presence calls.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass, field
from typing import Any

import pytest

from src.discord.colors import PRIMARY
from src.discord.startup import (
    STARTUP_DESCRIPTION,
    STARTUP_FOOTER,
    STARTUP_TITLE,
    PRESENCE_TEXT,
    StartupEmbedData,
    StartupEmbedField,
    build_startup_embed_data,
    reset_greeting,
)


# ── Fake Discord Module ─────────────────────────────────────────────────────


@dataclass
class _FakeActivity:
    """Fake ``discord.Activity`` that records constructor args."""

    type: object = None
    name: str = ""


class _FakeActivityType:
    """Fake ``discord.ActivityType`` with ``watching``."""

    watching: int = 3


class _FakeUtils:
    """Fake ``discord.utils`` providing ``get``."""

    @staticmethod
    def get(iterable: Any, **attrs: Any) -> Any | None:
        """Return the first item in *iterable* matching all keyword attrs."""
        for item in iterable:
            if all(getattr(item, k, None) == v for k, v in attrs.items()):
                return item
        return None


class _FakeColour:
    """Fake ``discord.Colour`` that stores an integer value."""

    def __init__(self, value: int) -> None:
        self.value = value


class _FakeEmbed:
    """Fake ``discord.Embed`` that records constructor args and fields."""

    def __init__(
        self,
        *,
        title: str = "",
        description: str = "",
        colour: object = None,
    ) -> None:
        self.title = title
        self.description = description
        self.colour = colour
        self.fields: list[dict[str, Any]] = []
        self.footer_text: str = ""

    def add_field(
        self,
        *,
        name: str,
        value: str,
        inline: bool = False,
    ) -> None:
        """Record a field."""
        self.fields.append({"name": name, "value": value, "inline": inline})

    def set_footer(self, *, text: str) -> None:
        """Record the footer."""
        self.footer_text = text


class _FakeDiscordModule:
    """Fake ``discord`` module injected via ``importlib.import_module``."""

    Activity = _FakeActivity
    ActivityType = _FakeActivityType()
    utils = _FakeUtils()
    Colour = _FakeColour
    Embed = _FakeEmbed


# ── Fake Client ─────────────────────────────────────────────────────────────


@dataclass
class FakeChannel:
    """Minimal channel stub for testing startup greeting delivery."""

    name: str
    _client: FakeClient | None = None

    async def send(self, **kwargs: Any) -> None:
        """Record the sent embed on the parent client."""
        if self._client is not None:
            self._client.sent_messages.append(kwargs)


@dataclass
class FakeClient:
    """Minimal client stub that records presence and greeting calls."""

    channels: list[FakeChannel] = field(default_factory=list)
    presence_calls: list[dict[str, Any]] = field(default_factory=list)
    sent_messages: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Wire each channel back to this client."""
        for ch in self.channels:
            ch._client = self

    async def change_presence(self, *, activity: Any = None) -> None:
        """Record presence change."""
        self.presence_calls.append({"activity": activity})

    def get_all_channels(self) -> list[FakeChannel]:
        """Return the configured channels."""
        return self.channels


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_greeting() -> None:
    """Reset the module-level idempotency guard before every test."""
    reset_greeting()


@pytest.fixture
def fake_discord(monkeypatch: pytest.MonkeyPatch) -> _FakeDiscordModule:
    """Inject the fake discord module so ``on_ready`` can import it."""
    fake_mod = _FakeDiscordModule()
    original_import = importlib.import_module

    def _fake_import(name: str, package: str | None = None) -> Any:
        if name == "discord":
            return fake_mod
        return original_import(name, package)

    monkeypatch.setattr(importlib, "import_module", _fake_import)
    return fake_mod


@pytest.fixture
def client_with_status_channel() -> FakeClient:
    """Return a FakeClient with a ``guinevere-status`` channel."""
    status_channel = FakeChannel(name="guinevere-status")
    return FakeClient(channels=[status_channel])


@pytest.fixture
def client_without_status_channel() -> FakeClient:
    """Return a FakeClient with no ``guinevere-status`` channel."""
    other = FakeChannel(name="general")
    return FakeClient(channels=[other])


# ── Embed Data Builder Tests ────────────────────────────────────────────────


class TestBuildEmbedData:
    """``build_startup_embed_data`` must return correctly populated data."""

    def test_title(self) -> None:
        data = build_startup_embed_data()
        assert data.title == STARTUP_TITLE
        assert data.title == "\U0001f451 Mommy sudah bangun, Darling."

    def test_description(self) -> None:
        data = build_startup_embed_data()
        assert data.description == STARTUP_DESCRIPTION

    def test_color(self) -> None:
        data = build_startup_embed_data()
        assert data.color == PRIMARY

    def test_three_fields(self) -> None:
        data = build_startup_embed_data()
        assert len(data.fields) == 3

    def test_fields_is_tuple(self) -> None:
        data = build_startup_embed_data()
        assert isinstance(data.fields, tuple)

    def test_status_field(self) -> None:
        data = build_startup_embed_data()
        assert data.fields[0].name == "Status"
        assert data.fields[0].value == "Online"

    def test_mood_field(self) -> None:
        data = build_startup_embed_data()
        assert data.fields[1].name == "Mood"
        assert data.fields[1].value == "Default (Y4)"

    def test_time_field_exists(self) -> None:
        data = build_startup_embed_data()
        assert data.fields[2].name == "Time"
        assert len(data.fields[2].value) > 0

    def test_footer(self) -> None:
        data = build_startup_embed_data()
        assert data.footer_text == STARTUP_FOOTER

    def test_timestamp_wib_format(self) -> None:
        data = build_startup_embed_data(timestamp_str="2026-06-01 19:00 WIB")
        assert data.timestamp == "2026-06-01 19:00 WIB"
        assert data.fields[2].value == "2026-06-01 19:00 WIB"

    def test_timestamp_default_generates_wib(self) -> None:
        """When no timestamp_str given, must generate a valid WIB string."""
        data = build_startup_embed_data()
        assert data.timestamp.endswith("WIB")
        assert " " in data.timestamp

    def test_fields_inline_default(self) -> None:
        data = build_startup_embed_data()
        for field in data.fields:
            assert field.inline is True


# ── Dataclass Invariants ─────────────────────────────────────────────────────


class TestDataclassInvariants:
    """``StartupEmbedData`` and ``StartupEmbedField`` must be frozen."""

    def test_startup_embed_data_is_frozen(self) -> None:
        data = StartupEmbedData()
        with pytest.raises(AttributeError):
            setattr(data, "title", "Changed")

    def test_startup_embed_field_is_frozen(self) -> None:
        field = StartupEmbedField("Test", "value")
        with pytest.raises(AttributeError):
            setattr(field, "name", "Changed")

    def test_startup_embed_field_inline_defaults_true(self) -> None:
        field = StartupEmbedField("Test", "value")
        assert field.inline is True


# ── Presence Text ────────────────────────────────────────────────────────────


class TestPresenceText:
    """``PRESENCE_TEXT`` must be ``"Darling 👁"``."""

    def test_presence_text_exact(self) -> None:
        assert PRESENCE_TEXT == "Darling \U0001f441"


# ── on_ready Idempotency ─────────────────────────────────────────────────────


class TestOnReadyIdempotency:
    """The greeting must be sent only once; presence set every call."""

    @pytest.mark.asyncio
    async def test_first_call_sends_greeting(
        self,
        fake_discord: _FakeDiscordModule,
        client_with_status_channel: FakeClient,
    ) -> None:
        from src.discord.startup import on_ready

        await on_ready(client_with_status_channel)

        # One greeting + one presence
        assert len(client_with_status_channel.sent_messages) == 1
        assert len(client_with_status_channel.presence_calls) == 1

    @pytest.mark.asyncio
    async def test_second_call_does_not_send_greeting(
        self,
        fake_discord: _FakeDiscordModule,
        client_with_status_channel: FakeClient,
    ) -> None:
        from src.discord.startup import on_ready

        await on_ready(client_with_status_channel)
        await on_ready(client_with_status_channel)

        # Still only one greeting; presence set both times
        assert len(client_with_status_channel.sent_messages) == 1
        assert len(client_with_status_channel.presence_calls) == 2

    @pytest.mark.asyncio
    async def test_after_reset_sends_again(
        self,
        fake_discord: _FakeDiscordModule,
        client_with_status_channel: FakeClient,
    ) -> None:
        from src.discord.startup import on_ready

        await on_ready(client_with_status_channel)
        reset_greeting()
        await on_ready(client_with_status_channel)

        # Two greetings now
        assert len(client_with_status_channel.sent_messages) == 2
        assert len(client_with_status_channel.presence_calls) == 2

    @pytest.mark.asyncio
    async def test_presence_uses_watching_activity(
        self,
        fake_discord: _FakeDiscordModule,
        client_with_status_channel: FakeClient,
    ) -> None:
        from src.discord.startup import on_ready

        await on_ready(client_with_status_channel)

        assert len(client_with_status_channel.presence_calls) == 1
        activity = client_with_status_channel.presence_calls[0]["activity"]
        assert isinstance(activity, _FakeActivity)
        assert activity.name == PRESENCE_TEXT

    @pytest.mark.asyncio
    async def test_channel_not_found_does_not_crash(
        self,
        fake_discord: _FakeDiscordModule,
        client_without_status_channel: FakeClient,
    ) -> None:
        from src.discord.startup import on_ready

        # Should not raise even though there's no guinevere-status channel
        await on_ready(client_without_status_channel)

        # Presence still set
        assert len(client_without_status_channel.presence_calls) == 1
        # No greeting sent
        assert len(client_without_status_channel.sent_messages) == 0


# ── Python 3.12+ Style ───────────────────────────────────────────────────────


class TestPython312Style:
    """File must use ``from __future__ import annotations``."""

    def test_module_has_annotations_future(self) -> None:
        import inspect

        from src.discord import startup

        source = inspect.getsource(startup)
        assert "from __future__ import annotations" in source
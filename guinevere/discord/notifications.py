"""Discord notification routing for SEV alerts in Guinevere.

Provides deterministic alert routing with protocol-typed Discord access,
frozen dataclass payloads, and dynamic ``importlib`` conversion patterns
aligned with the other Discord command modules.
"""

from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Iterable, Protocol, cast, runtime_checkable

from .colors import ALERT, NEUTRAL, PRIMARY, WARNING

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for notification routing failures."""

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""

FOOTER_TEXT: Final[str] = "Guinevere de Baroque • System Alert"
"""Footer text for all notification embeds."""

SEV0_CHANNEL: Final[str] = "system-health"
SEV1_CHANNEL: Final[str] = "system-health"
SEV2_CHANNEL: Final[str] = "cost-tracker"
SEV3_CHANNEL: Final[str] = "guinevere-status"
SEV4_CHANNEL: Final[str] = "audit-log"

# ChannelConfig key mapping — SEV levels → ChannelConfig attribute names.
# All notification severities route to the 'notifications' channel.
SEV_CHANNEL_CONFIG_KEY: Final[str] = "notifications"
"""ChannelConfig attribute name used for direct ID lookup of SEV channels."""

SEV0_TONE: Final[str] = "Urgent, neutral, no persona"
SEV1_TONE: Final[str] = "Alert, neutral"
SEV2_TONE: Final[str] = "Informational"
SEV3_TONE: Final[str] = "Status update"
SEV4_TONE: Final[str] = "Audit record"

SEV0_COLOR: Final[int] = ALERT
SEV1_COLOR: Final[int] = WARNING
SEV2_COLOR: Final[int] = WARNING
SEV3_COLOR: Final[int] = PRIMARY
SEV4_COLOR: Final[int] = NEUTRAL

SEV_MATRIX: Final[dict[str, tuple[str, int, str, bool]]] = {
    "SEV0": (SEV0_CHANNEL, SEV0_COLOR, SEV0_TONE, True),
    "SEV1": (SEV1_CHANNEL, SEV1_COLOR, SEV1_TONE, False),
    "SEV2": (SEV2_CHANNEL, SEV2_COLOR, SEV2_TONE, False),
    "SEV3": (SEV3_CHANNEL, SEV3_COLOR, SEV3_TONE, False),
    "SEV4": (SEV4_CHANNEL, SEV4_COLOR, SEV4_TONE, False),
}


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used for notifications."""

    def set_footer(self, *, text: str) -> None:
        ...

    def set_author(self, *, name: str) -> None:
        ...


class DiscordEmbedFactory(Protocol):
    """Callable protocol for ``discord.Embed(...)`` constructor."""

    def __call__(self, *, title: str, description: str, colour: object) -> DiscordEmbedProtocol:
        ...


class DiscordColourFactory(Protocol):
    """Callable protocol for ``discord.Colour(...)`` constructor."""

    def __call__(self, value: int) -> object:
        ...


class DiscordTextChannelProtocol(Protocol):
    """Protocol for a Discord text channel used by alert routing."""

    name: str

    async def send(self, **kwargs: object) -> object:
        ...


class DiscordBotProtocol(Protocol):
    """Subset of a Discord bot needed for alert routing."""

    def get_all_channels(self) -> Iterable[DiscordTextChannelProtocol]:
        ...


class DiscordChannelQueryProtocol(Protocol):
    """Subset of ``discord.utils`` used for channel lookup."""

    def get(self, iterable: object, **attrs: object) -> object | None:
        ...


class DiscordEmbedModule(Protocol):
    """Subset of ``discord`` module for embed construction and lookup."""

    Embed: DiscordEmbedFactory
    Colour: DiscordColourFactory
    utils: DiscordChannelQueryProtocol


@dataclass(frozen=True)
class NotificationEmbedField:
    """A single notification detail field."""

    name: str
    value: str
    inline: bool = False


@dataclass(frozen=True)
class NotificationEmbedData:
    """Deterministic embed payload for a SEV alert."""

    title: str
    description: str
    color: int
    footer_text: str = FOOTER_TEXT
    timestamp: str = ""
    fields: tuple[NotificationEmbedField, ...] = ()
    ping_faiz: bool = False
    create_thread: bool = False
    channel_name: str = ""
    sev: str = ""


def _get_discord_embed_module() -> DiscordEmbedModule:
    mod = importlib.import_module("discord")
    return cast(DiscordEmbedModule, cast(object, mod))


def _format_wib_timestamp(dt: datetime) -> str:
    return dt.astimezone(WIB).strftime("%Y-%m-%d %H:%M WIB")


def _normalize_sev(sev: str) -> str:
    return sev.strip().upper()


def _build_title(sev: str, title: str) -> str:
    return f"[{sev}] {title}"


def _build_notification_data(
    sev: str,
    title: str,
    description: str,
    *,
    now: datetime | None = None,
) -> NotificationEmbedData:
    normalized = _normalize_sev(sev)
    channel_name, color, tone, ping_faiz = SEV_MATRIX[normalized]
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    fields = (
        NotificationEmbedField("Severity", normalized),
        NotificationEmbedField("Channel", f"#{channel_name}"),
        NotificationEmbedField("Tone", tone),
    )
    if normalized == "SEV2":
        fields = fields + (NotificationEmbedField("Budget Detail", "See budget tracker for cost impact."),)
    if normalized == "SEV4":
        fields = fields + (NotificationEmbedField("Timestamp", _format_wib_timestamp(ref)),)
    return NotificationEmbedData(
        title=_build_title(normalized, title),
        description=description,
        color=color,
        footer_text=FOOTER_TEXT,
        timestamp=_format_wib_timestamp(ref),
        fields=fields,
        ping_faiz=ping_faiz,
        create_thread=normalized == "SEV0",
        channel_name=channel_name,
        sev=normalized,
    )


def to_discord_embed(data: NotificationEmbedData) -> DiscordEmbedProtocol:
    d = _get_discord_embed_module()
    embed = d.Embed(title=data.title, description=data.description, colour=d.Colour(data.color))
    for field in data.fields:
        add_field = getattr(embed, "add_field", None)
        if callable(add_field):
            add_field(name=field.name, value=field.value, inline=field.inline)
    embed.set_footer(text=data.footer_text)
    return embed


async def send_alert(
    bot: DiscordBotProtocol,
    sev: str,
    title: str,
    description: str,
    channel_config: object = None,
    **kwargs: object,
) -> bool:
    """Send a SEV alert to the appropriate Discord channel.

    Uses ``channel_config`` for direct channel ID resolution via
    ``ChannelConfig.notifications``.  All notification severities route
    to the notifications channel.

    Args:
        bot: The Discord bot instance.
        sev: Severity level (e.g. "SEV0", "SEV1").
        title: Alert title.
        description: Alert description.
        channel_config: Optional ``ChannelConfig`` instance for direct
            channel ID resolution.  If not provided, reads
            ``bot.channel_config``.
        **kwargs: Additional keyword arguments (e.g. ``thread_name``).

    Returns:
        ``True`` if the alert was sent successfully.
    """
    try:
        normalized = _normalize_sev(sev)
        if normalized not in SEV_MATRIX:
            raise ValueError(f"Unsupported severity: {sev}")
        data = _build_notification_data(normalized, title, description)

        cfg = channel_config or getattr(bot, "channel_config", None)
        channel = None

        # Direct ID lookup via ChannelConfig
        if cfg is not None:
            ch_id = getattr(cfg, SEV_CHANNEL_CONFIG_KEY, None)
            if isinstance(ch_id, int):
                get_channel_fn = getattr(bot, "get_channel", None)
                if get_channel_fn is not None:
                    channel = get_channel_fn(ch_id)

        if channel is None:
            logger.error("Notification channel not found for %s", normalized)
            return False

        embed = to_discord_embed(data)
        send_kwargs: dict[str, object] = {"embed": embed}
        if data.ping_faiz:
            mention = os.getenv("GUINEVERE_FAIZ_MENTION") or os.getenv("FAIZ_MENTION")
            if mention:
                send_kwargs["content"] = mention
        if normalized == "SEV4":
            send_kwargs.setdefault("content", data.timestamp)
        if kwargs.get("thread_name"):
            send_kwargs["thread_name"] = kwargs["thread_name"]
        await channel.send(**send_kwargs)
        if normalized in ("SEV0", "SEV1"):
            from .gotify_fallback import send_fallback as _send_gotify

            await _send_gotify(title, description, normalized)
        return True
    except Exception as exc:
        logger.error("Failed to send %s alert: %s", sev, exc, exc_info=True)
        return False


import discord  # noqa: E402  # isort: skip

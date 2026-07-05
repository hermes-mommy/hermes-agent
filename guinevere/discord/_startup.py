"""Discord startup greeting and presence helper for Guinevere (non-deprecated).

Provides deterministic embed data builder, dynamic discord.py conversion,
and an ``on_ready`` handler for P2-017 wiring.  The greeting is sent exactly
once per session (idempotency guard); presence is set on every ``on_ready``
per Discord best practice.

This is the non-deprecated home.  ``guinevere/discord/startup.py`` remains for
archive reference and should not be imported by active code.

Usage:
    # Build embed data without discord.py:
    data = build_startup_embed_data()

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Wire into bot.py (P2-017):
    # @client.event
    # async def on_ready():
    #     await startup_on_ready(client)
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, cast

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for startup."""

from .colors import PRIMARY


# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

STARTUP_TITLE: Final[str] = "\U0001f451 Mommy sudah bangun, Darling."
"""Embed title for startup greeting. Unicode: \U0001f451 = 👑."""

STARTUP_DESCRIPTION: Final[str] = (
    "Semua sistem online. Mommy siap nemenin kamu hari ini."
)
"""Persona-flavored description for the startup embed."""

STARTUP_FIELDS: Final[list[tuple[str, str]]] = [
    ("Status", "Online"),
    ("Mood", "Default (Y4)"),
    ("Time", ""),  # filled dynamically in builder
]
"""Base embed fields. The ``Time`` value is replaced at build time."""

STARTUP_FOOTER: Final[str] = "Guinevere de Baroque"
"""Footer text for the startup embed."""

COLOR: Final[int] = PRIMARY
"""Embed colour for the startup greeting."""

PRESENCE_TEXT: Final[str] = "Darling \U0001f441"
"""Text for ``discord.Activity(type=discord.ActivityType.watching, name=...)``.
Unicode: \U0001f441 = 👁."""


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by the startup greeting.

    Covers only the methods and constructor shape needed by
    ``to_discord_embed()``.
    """

    def add_field(
        self,
        *,
        name: str,
        value: str,
        inline: bool = False,
    ) -> None:
        """Add a named field to the embed."""
        ...

    def set_footer(self, *, text: str) -> None:
        """Set the footer text on the embed."""
        ...


class DiscordEmbedFactory(Protocol):
    """Callable protocol for ``discord.Embed(...)`` constructor."""

    def __call__(
        self,
        *,
        title: str,
        description: str,
        colour: object,
    ) -> DiscordEmbedProtocol:
        """Create a new embed instance."""
        ...


class DiscordColourFactory(Protocol):
    """Callable protocol for ``discord.Colour(...)`` constructor."""

    def __call__(self, value: int) -> object:
        """Create a new Colour instance."""
        ...


class DiscordEmbedModule(Protocol):
    """Subset of ``discord`` module for embed construction."""

    Embed: DiscordEmbedFactory
    Colour: DiscordColourFactory


def _get_discord_embed_module() -> DiscordEmbedModule:
    """Import ``discord`` dynamically and return typed embed interface.

    Returns:
        A protocol-typed object providing ``Embed`` and ``Colour``.
    """
    mod = importlib.import_module("discord")
    return cast(DiscordEmbedModule, cast(object, mod))


# ── Data Types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StartupEmbedField:
    """A single embed field definition for the startup greeting.

    Attributes:
        name: The field name (displayed bold in the embed).
        value: The field value (plain or Markdown text).
        inline: Whether the field should render inline.
    """

    name: str
    value: str
    inline: bool = True


@dataclass(frozen=True)
class StartupEmbedData:
    """Deterministic embed data for the startup greeting.

    Can be converted to a ``discord.Embed`` via ``to_discord_embed()``
    or consumed by any other renderer without a ``discord.py`` dependency.

    Attributes:
        title: Embed title (``"👑 Mommy sudah bangun, Darling."``).
        description: Embed description / persona sentence.
        color: Embed colour integer.
        fields: Tuple of embed fields.
        footer_text: Footer text.
        timestamp: WIB-formatted timestamp string.
    """

    title: str = STARTUP_TITLE
    description: str = STARTUP_DESCRIPTION
    color: int = COLOR
    fields: tuple[StartupEmbedField, ...] = (
        StartupEmbedField("Status", "Online"),
        StartupEmbedField("Mood", "Default (Y4)"),
        StartupEmbedField("Time", ""),
    )
    footer_text: str = STARTUP_FOOTER
    timestamp: str = ""


# ── Helpers ─────────────────────────────────────────────────────────────────


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``.

    Args:
        dt: The datetime to format (timezone-aware).

    Returns:
        A string in the format ``YYYY-MM-DD HH:MM WIB``.
    """
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


# ── Embed Builder ───────────────────────────────────────────────────────────


def build_startup_embed_data(
    timestamp_str: str | None = None,
) -> StartupEmbedData:
    """Build a deterministic ``StartupEmbedData`` with all embed fields.

    Args:
        timestamp_str: Override timestamp string for determinism
                       (e.g. in tests).  Defaults to current WIB time.

    Returns:
        A fully populated ``StartupEmbedData``.
    """
    if timestamp_str is None:
        now = datetime.now(tz=timezone.utc)
        ts_str = _format_wib_timestamp(now)
    else:
        ts_str = timestamp_str

    fields = (
        StartupEmbedField("Status", "Online"),
        StartupEmbedField("Mood", "Default (Y4)"),
        StartupEmbedField("Time", ts_str),
    )

    return StartupEmbedData(
        title=STARTUP_TITLE,
        description=STARTUP_DESCRIPTION,
        color=COLOR,
        fields=fields,
        footer_text=STARTUP_FOOTER,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: StartupEmbedData) -> DiscordEmbedProtocol:
    """Convert ``StartupEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.
    Raises ``ImportError`` if the ``discord`` package is unavailable.

    Args:
        data: The startup embed data to convert.

    Returns:
        A ``DiscordEmbedProtocol`` instance (equivalent to ``discord.Embed``).

    Raises:
        ImportError: If the ``discord`` package is not installed.
    """
    d = _get_discord_embed_module()
    embed = d.Embed(
        title=data.title,
        description=data.description,
        colour=d.Colour(data.color),
    )

    for field in data.fields:
        embed.add_field(name=field.name, value=field.value, inline=field.inline)

    footer_line = f"{data.footer_text} \u2022 {data.timestamp}"
    embed.set_footer(text=footer_line)

    return embed


# ── Discord Client Protocol ────────────────────────────────────────────────


class DiscordClientProtocol(Protocol):
    """Minimal ``discord.Client`` protocol used by ``on_ready``.

    Covers only the subset needed by the startup greeting handler.
    """

    async def change_presence(self, *, activity: object) -> None:
        """Set the bot's presence."""
        ...

    def get_all_channels(self) -> object:
        """Return all channels the bot can see."""
        ...


# ── Module-level Idempotency Guard ──────────────────────────────────────────

_sent_greeting: bool = False
"""Idempotency guard: ``True`` after the first successful greeting."""


def reset_greeting() -> None:
    """Reset the idempotency guard for testing."""
    global _sent_greeting
    _sent_greeting = False


# ── on_ready Handler ────────────────────────────────────────────────────────


async def on_ready(client: object) -> None:
    """P2-017 wired ``on_ready`` handler.

    Sends a startup greeting to ``#guinevere-status`` and sets the bot's
    presence.  **Idempotent**: the greeting is only sent once across
    reconnects.  Presence is set on every ``on_ready`` (Discord best
    practice).

    Args:
        client: The Discord client instance (``discord.Client`` or
                ``commands.Bot``).
    """
    global _sent_greeting

    # Cast to protocol for type-safe attribute access
    _client = cast(DiscordClientProtocol, client)

    # Set presence (every on_ready per Discord best practice)
    try:
        discord_mod = importlib.import_module("discord")
        activity = discord_mod.Activity(
            type=discord_mod.ActivityType.watching,
            name=PRESENCE_TEXT,
        )
        await _client.change_presence(activity=activity)
    except Exception:
        logger.exception("Failed to set presence")

    # Send greeting (once only)
    if _sent_greeting:
        return
    _sent_greeting = True

    try:
        discord_mod = importlib.import_module("discord")
        channel = discord_mod.utils.get(
            _client.get_all_channels(), name="guinevere-status"
        )
        if channel is not None:
            data = build_startup_embed_data()
            embed = to_discord_embed(data)
            await channel.send(embed=embed)
            logger.info("startup_greeting_sent", extra={"channel": channel.name})
        else:
            logger.warning(
                "startup_channel_not_found",
                extra={"channel_name": "guinevere-status"},
            )
    except Exception:
        logger.exception("failed_to_send_startup_greeting")

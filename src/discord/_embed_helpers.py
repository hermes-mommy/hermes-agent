"""Shared Discord embed protocols, dataclasses, and helper functions.

Provides DRY abstractions reused across all ``cmd_*.py`` modules in the
Guinevere Discord package.  Each command module imports Protocol classes,
the embed factory, and interaction helpers from here instead of
duplicating them.

5-part pattern elements provided:
1. Protocol classes for discord.Embed, Interaction, Response, Followup.
2. Dataclass ``EmbedField`` and ``EmbedData`` for deterministic embeds.
3. ``build_embed()`` and ``to_discord_embed()`` converters.
4. Async interaction helpers: ``defer_ephemeral``, ``followup_send``,
   ``send_denied``.
5. ``get_option_value`` for slash-command option extraction.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, cast, runtime_checkable

# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""

FOOTER_TEXT: Final[str] = "Guinevere de Baroque"


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol."""

    def add_field(self, *, name: str, value: str, inline: bool = False) -> None:
        """Add a named field to the embed."""
        ...

    def set_footer(self, *, text: str) -> None:
        """Set the footer text on the embed."""
        ...


class DiscordEmbedFactory(Protocol):
    """Callable protocol for ``discord.Embed(...)``."""

    def __call__(
        self, *, title: str, description: str, colour: object
    ) -> DiscordEmbedProtocol:
        """Create a new embed instance."""
        ...


class DiscordColourFactory(Protocol):
    """Callable protocol for ``discord.Colour(...)``."""

    def __call__(self, value: int) -> object:
        """Create a new Colour instance."""
        ...


class DiscordEmbedModule(Protocol):
    """Subset of ``discord`` module for embed construction."""

    Embed: DiscordEmbedFactory
    Colour: DiscordColourFactory


def get_discord_module() -> DiscordEmbedModule:
    """Import ``discord`` dynamically and return typed embed interface."""
    mod = importlib.import_module("discord")
    return cast(DiscordEmbedModule, cast(object, mod))


# ── Discord Interaction Protocols ──────────────────────────────────────────


@runtime_checkable
class DiscordResponseProtocol(Protocol):
    """Protocol for ``discord.Interaction.response``."""

    async def defer(self, *, ephemeral: bool = False) -> None:
        """Defer the interaction response."""
        ...

    def is_done(self) -> bool:
        """Return True if the interaction has been responded to."""
        ...

    async def send_message(self, **kwargs: object) -> None:
        """Send an initial interaction response."""
        ...


@runtime_checkable
class DiscordFollowupProtocol(Protocol):
    """Protocol for ``discord.Interaction.followup``."""

    async def send(self, **kwargs: object) -> None:
        """Send a followup message."""
        ...


@runtime_checkable
class DiscordUserProtocol(Protocol):
    """Protocol for ``discord.User`` / ``discord.Member``."""

    @property
    def id(self) -> int:
        """User ID."""
        ...

    @property
    def display_name(self) -> str:
        """Display name."""
        ...


@runtime_checkable
class DiscordInteractionProtocol(Protocol):
    """Protocol for ``discord.Interaction``."""

    response: DiscordResponseProtocol
    followup: DiscordFollowupProtocol
    user: DiscordUserProtocol


# ── Data Types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EmbedField:
    """A single embed field definition."""

    name: str
    value: str
    inline: bool = False


@dataclass(frozen=True)
class EmbedData:
    """Deterministic embed data for any command.

    Attributes:
        title: Embed title.
        description: Embed description.
        color: Embed colour integer.
        fields: Tuple of embed fields.
        footer_text: Left footer text.
        footer_icon: Right footer icon / label.
        timestamp: WIB-formatted timestamp string.
    """

    title: str
    description: str
    color: int
    fields: tuple[EmbedField, ...] = ()
    footer_text: str = FOOTER_TEXT
    footer_icon: str = ""
    timestamp: str = ""


# ── Helpers ─────────────────────────────────────────────────────────────────


def format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def now_wib_str() -> str:
    """Return current UTC time formatted as WIB string."""
    return format_wib_timestamp(datetime.now(tz=timezone.utc))


def get_option_value(interaction: object, option_name: str) -> str | None:
    """Extract a slash command option value from the interaction.

    Args:
        interaction: The Discord interaction object.
        option_name: The name of the option to extract.

    Returns:
        The option value as a string, or None if not found.
    """
    data = getattr(interaction, "data", None)
    if data is None:
        return None
    options: list[dict[str, object]] = (
        data.get("options", []) if isinstance(data, dict) else []
    )
    for opt in options:
        if opt.get("name") == option_name:
            return str(opt.get("value", ""))
    return None


# ── Embed Builder ───────────────────────────────────────────────────────────


def to_discord_embed(data: EmbedData) -> DiscordEmbedProtocol:
    """Convert ``EmbedData`` to a ``discord.Embed`` object."""
    d = get_discord_module()
    embed = d.Embed(
        title=data.title,
        description=data.description,
        colour=d.Colour(data.color),
    )

    for field in data.fields:
        embed.add_field(name=field.name, value=field.value, inline=field.inline)

    parts = [data.footer_text]
    if data.timestamp:
        parts.append(data.timestamp)
    if data.footer_icon:
        parts.append(data.footer_icon)
    embed.set_footer(text=" \u2022 ".join(parts))

    return embed


# ── Interaction Helpers ─────────────────────────────────────────────────────


async def send_denied(interaction: object) -> None:
    """Send an ephemeral denial message to a non-Faiz user."""
    if not isinstance(interaction, DiscordInteractionProtocol):
        return

    if interaction.response.is_done():
        await interaction.followup.send(
            content="Hanya Faiz yang bisa menggunakan Mommy.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            content="Hanya Faiz yang bisa menggunakan Mommy.",
            ephemeral=True,
        )


async def defer_ephemeral(interaction: object) -> None:
    """Defer the interaction response ephemerally."""
    if not isinstance(interaction, DiscordInteractionProtocol):
        return

    await interaction.response.defer(ephemeral=True)


async def followup_send(
    interaction: object,
    embed: object | None = None,
    content: str | None = None,
    file: object | None = None,
) -> None:
    """Send a followup message (ephemeral).

    Args:
        interaction: The Discord ``Interaction``.
        embed: Optional embed object.
        content: Optional plain text content.
        file: Optional file attachment.
    """
    if not isinstance(interaction, DiscordInteractionProtocol):
        return

    kwargs: dict[str, object] = {"ephemeral": True}
    if content is not None:
        kwargs["content"] = content
    if embed is not None:
        kwargs["embed"] = embed
    if file is not None:
        kwargs["file"] = file

    await interaction.followup.send(**kwargs)


__all__ = [
    "WIB",
    "FOOTER_TEXT",
    "DiscordEmbedProtocol",
    "DiscordEmbedFactory",
    "DiscordColourFactory",
    "DiscordEmbedModule",
    "DiscordResponseProtocol",
    "DiscordFollowupProtocol",
    "DiscordUserProtocol",
    "DiscordInteractionProtocol",
    "EmbedField",
    "EmbedData",
    "get_discord_module",
    "format_wib_timestamp",
    "now_wib_str",
    "get_option_value",
    "to_discord_embed",
    "send_denied",
    "defer_ephemeral",
    "followup_send",
]

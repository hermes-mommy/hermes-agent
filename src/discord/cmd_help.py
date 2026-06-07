"""Discord /help command implementation for Guinevere.

Provides deterministic embed data builder and discord.py callback helpers.
The embed lists all 33 slash commands grouped by their 7 categories,
following DiscordUXSpec v1.0 \u00a72.5 with one field per category.

Usage:
    # Build embed data without discord.py:
    data = build_help_embed_data()

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as callback:
    # tree.command(name="help", description="...")(help_callback)
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, cast, runtime_checkable

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for cmd_help. Used in the broad exception handler."""

from .colors import PRIMARY


# \u2500\u2500 Timezone \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# \u2500\u2500 Constants \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

HELP_TITLE: Final[str] = "\U0001f4d6 Guinevere Command Guide"
"""Embed title for /help. Unicode: \U0001f4d6 = \U0001f4d6."""

HELP_DESCRIPTION: Final[str] = (
    "Semua command Mommy yang tersedia, Darling. Kalau bingung, bilang aja."
)
"""Persona-flavored description for the help embed."""

FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
"""Left footer text for the help embed."""

FOOTER_ICON: Final[str] = "\u2728"
"""Right footer icon for the help embed. Unicode: \u2728 = \u2728."""

CATEGORY_SEPARATOR: Final[str] = " \u007c "
"""Separator string between command names in a category field value."""

_CATEGORY_DISPLAY: Final[dict[str, str]] = {
    "core": "Core \U0001f3e0",
    "loop": "Loop \U0001f504",
    "memory": "Memory \U0001f9e0",
    "surveillance": "Surveillance \U0001f441",
    "finance": "Finance \U0001f4b0",
    "system": "System \u2699",
    "admin": "Admin \U0001f6e0",
}
"""Maps canonical category keys to display names with emoji."""


# \u2500\u2500 Discord Embed Protocol \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/help``.

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


# \u2500\u2500 Discord Interaction Protocols \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


@runtime_checkable
class DiscordResponseProtocol(Protocol):
    """Protocol for ``discord.Interaction.response``.

    Covers only the subset needed by ``/help``: defer, is_done,
    and send_message (for non-deferred initial replies).
    """

    async def defer(self, *, ephemeral: bool = False) -> None:
        """Defer the interaction response, allowing followup later."""
        ...

    def is_done(self) -> bool:
        """Return True if the interaction has already been responded to."""
        ...

    async def send_message(self, **kwargs: object) -> None:
        """Send an initial interaction response."""
        ...


@runtime_checkable
class DiscordFollowupProtocol(Protocol):
    """Protocol for ``discord.Interaction.followup``."""

    async def send(self, **kwargs: object) -> None:
        """Send a followup message (usable after defer)."""
        ...


@runtime_checkable
class DiscordInteractionProtocol(Protocol):
    """Protocol for ``discord.Interaction``.

    Exposes the ``response`` and ``followup`` attributes needed
    by the ``/help`` callback helpers.
    """

    response: DiscordResponseProtocol
    followup: DiscordFollowupProtocol


# \u2500\u2500 Data Types \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


@dataclass(frozen=True)
class HelpEmbedData:
    """Deterministic embed data for the ``/help`` command.

    Can be converted to a ``discord.Embed`` via ``to_discord_embed()``
    or consumed by any other renderer without a ``discord.py`` dependency.

    Attributes:
        title: Embed title (``"\\U0001f4d6 Guinevere Command Guide"``).
        description: Embed description / persona sentence.
        color: Embed colour integer (``PRIMARY`` / ``0x6B21A8``).
        categories: Dict of category keys to command-name tuples.
        footer_text: Left footer text.
        footer_icon: Right footer icon / label.
        timestamp: WIB-formatted timestamp string.
    """

    title: str = HELP_TITLE
    description: str = HELP_DESCRIPTION
    color: int = PRIMARY
    categories: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {"core": ("status", "mood", "help", "safeword")}
    )
    footer_text: str = FOOTER_TEXT
    footer_icon: str = FOOTER_ICON
    timestamp: str = ""


# \u2500\u2500 Helpers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``.

    Args:
        dt: The datetime to format (timezone-aware).

    Returns:
        A string in the format ``YYYY-MM-DD HH:MM WIB``.
    """
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def _build_category_field_name(key: str) -> str:
    """Return the display field name for a category key.

    Args:
        key: Canonical category key (e.g. ``"core"``, ``"loop"``).

    Returns:
        The display name with emoji, or the key itself if unknown.
    """
    return _CATEGORY_DISPLAY.get(key, key.capitalize())


def _build_category_field_value(commands: tuple[str, ...]) -> str:
    """Return the display field value for a tuple of command names.

    Args:
        commands: The command names in the category.

    Returns:
        Command names joined with `` \\| `` separator.
    """
    return CATEGORY_SEPARATOR.join(commands)


def _compute_command_count(categories: dict[str, tuple[str, ...]]) -> int:
    """Return the total number of commands across all categories.

    Args:
        categories: Dict of category keys to command-name tuples.

    Returns:
        The sum of all command-tuple lengths.
    """
    return sum(len(cmds) for cmds in categories.values())


# \u2500\u2500 Embed Builder \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


def build_help_embed_data(
    categories: dict[str, tuple[str, ...]] | None = None,
) -> HelpEmbedData:
    """Build a deterministic ``HelpEmbedData`` with all 7 category fields.

    Command names are read from ``command_categories()`` in
    ``src.discord.commands`` when ``categories`` is ``None``.

    Args:
        categories: Override category dict for determinism (e.g. in tests).
                    Defaults to ``command_categories()``.

    Returns:
        A fully populated ``HelpEmbedData``.
    """
    from src.hermes_plugins.command_catalog import command_categories

    cats = categories if categories is not None else command_categories()
    ref = datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)

    return HelpEmbedData(
        title=HELP_TITLE,
        description=HELP_DESCRIPTION,
        color=PRIMARY,
        categories=cats,
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


# \u2500\u2500 discord.py Conversion \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


def to_discord_embed(data: HelpEmbedData) -> DiscordEmbedProtocol:
    """Convert ``HelpEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.
    Raises ``ImportError`` if the ``discord`` package is unavailable.

    Each category in ``data.categories`` is rendered as a separate
    embed field with non-inline layout (one per row).

    Args:
        data: The help embed data to convert.

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

    cmd_count = _compute_command_count(data.categories)
    for key, commands in data.categories.items():
        field_name = _build_category_field_name(key)
        field_value = _build_category_field_value(commands)
        embed.add_field(name=field_name, value=field_value, inline=False)

    footer_line = (
        f"{data.footer_text} \u2022 {data.timestamp} \u2022 "
        f"{data.footer_icon} {cmd_count} Commands"
    )
    embed.set_footer(text=footer_line)

    return embed


# \u2500\u2500 Discord Interaction Callback \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


async def help_callback(interaction: object) -> None:
    """Handle a ``/help`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, builds the help embed, and sends it as a followup.
    If any embedding step fails, a graceful degraded fallback message
    is sent rather than crashing the entire command.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await _send_denied(interaction)
        return

    await _defer_ephemeral(interaction)

    try:
        data = build_help_embed_data()
        embed = to_discord_embed(data)
        await _followup_send(interaction, embed=embed)
    except Exception:
        logger.exception("help_callback: failed to build or send help embed")
        await _followup_send(
            interaction,
            content="\u26a0\ufe0f Mommy's command guide is temporarily unavailable.",
        )


# \u2500\u2500 Internal Interaction Helpers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


async def _send_denied(interaction: object) -> None:
    """Send an ephemeral denial message to a non-Faiz user.

    Uses ``isinstance`` checks with ``@runtime_checkable`` protocols
    to verify the interaction object shape before accessing members.
    Does not silence exceptions; if the send fails the exception
    propagates naturally (caught by the discord.py framework).

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
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


async def _defer_ephemeral(interaction: object) -> None:
    """Defer the interaction response ephemerally.

    Args:
        interaction: The Discord ``Interaction`` to defer.
    """
    if not isinstance(interaction, DiscordInteractionProtocol):
        return

    await interaction.response.defer(ephemeral=True)


async def _followup_send(
    interaction: object,
    embed: object | None = None,
    content: str | None = None,
) -> None:
    """Send a followup message (ephemeral).

    Args:
        interaction: The Discord ``Interaction``.
        embed: Optional embed object (e.g. ``DiscordEmbedProtocol``).
        content: Optional plain text content.
    """
    if not isinstance(interaction, DiscordInteractionProtocol):
        return

    kwargs: dict[str, object] = {"ephemeral": True}
    if content is not None:
        kwargs["content"] = content
    if embed is not None:
        kwargs["embed"] = embed

    await interaction.followup.send(**kwargs)
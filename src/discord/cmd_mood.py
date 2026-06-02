"""Discord /mood command implementation for Guinevere.

Provides deterministic embed data builder and discord.py callback helpers.
Degraded placeholders are used for subsystems not yet deployed (P3/P4/P5).
The embed follows DiscordUXSpec v1.0 §2.5 with 6 mood fields.

Usage:
    # Build embed data without discord.py:
    data = build_mood_embed_data()

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as callback:
    # tree.command(name="mood", description="...")(mood_callback)
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, cast, runtime_checkable

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for cmd_mood. Used in the broad exception handler."""

from .colors import PRIMARY, color_for_mood


# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

MOOD_TITLE: Final[str] = "\U0001f9e0 Mood Analysis"
"""Embed title for /mood. Unicode: \U0001f9e0 = 🧠."""

MOOD_DESCRIPTION: Final[str] = (
    "Mommy lagi baik-baik aja, Darling. Kamu nggak perlu khawatir."
)
"""Persona-flavored description for the mood embed (normal persona mode)."""

FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\U0001f9e0 Mood"

# Emoji maps for mood display names
_MOOD_EMOJI: Final[dict[str, str]] = {
    "content": "\U0001f60a",
    "pleased": "\U0001f929",
    "disappointed": "\U0001f61e",
    "angry": "\U0001f620",
    "silent": "\U0001f910",
}
"""Mood name to single-emoji mapping."""

_MOOD_LABEL: Final[dict[str, str]] = {
    "content": "Content",
    "pleased": "Pleased",
    "disappointed": "Disappointed",
    "angry": "Angry",
    "silent": "Silent",
}
"""Mood name to display label mapping."""

# Degraded placeholders for unavailable subsystems (P3/P4/P5)
DEGRADED_UNDERTONE: Final[str] = (
    "\u26a0\ufe0f \u2014 Undertone analysis (P3 not deployed)"
)
DEGRADED_HISTORY: Final[str] = (
    "\u26a0\ufe0f \u2014 24h history (P4 not deployed)"
)
DEGRADED_TRIGGERS: Final[str] = (
    "\u26a0\ufe0f \u2014 Trigger tracking (P3 not deployed)"
)
DEGRADED_STREAK: Final[str] = (
    "\u26a0\ufe0f \u2014 Streak tracking (P4 not deployed)"
)
DEGRADED_FORECAST: Final[str] = (
    "\u26a0\ufe0f \u2014 Mood forecast (P5 not deployed)"
)

DEFAULT_MOOD: Final[str] = "content"
"""Default mood name used when no mood subsystem is available."""


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/mood``.

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


# ── Discord Interaction Protocols ──────────────────────────────────────────


@runtime_checkable
class DiscordResponseProtocol(Protocol):
    """Protocol for ``discord.Interaction.response``.

    Covers only the subset needed by ``/mood``: defer, is_done,
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
    by the ``/mood`` callback helpers.
    """

    response: DiscordResponseProtocol
    followup: DiscordFollowupProtocol


# ── Data Types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MoodEmbedField:
    """A single embed field definition.

    Attributes:
        name: The field name (displayed bold in the embed).
        value: The field value (plain or Markdown text).
        inline: Whether the field should render inline.
    """

    name: str
    value: str
    inline: bool = False


@dataclass(frozen=True)
class MoodEmbedData:
    """Deterministic embed data for the ``/mood`` command.

    Can be converted to a ``discord.Embed`` via ``to_discord_embed()``
    or consumed by any other renderer without a ``discord.py`` dependency.

    Attributes:
        title: Embed title (``"🧠 Mood Analysis"``).
        description: Embed description / persona sentence.
        color: Embed colour integer (dynamic per mood).
        fields: Tuple of 6 embed fields.
        footer_text: Left footer text.
        footer_icon: Right footer icon / label.
        timestamp: WIB-formatted timestamp string.
    """

    title: str = MOOD_TITLE
    description: str = MOOD_DESCRIPTION
    color: int = PRIMARY
    fields: tuple[MoodEmbedField, ...] = (
        MoodEmbedField("Current Mood", "\U0001f60a Content"),
        MoodEmbedField("Undertone", DEGRADED_UNDERTONE),
        MoodEmbedField("24h History", DEGRADED_HISTORY),
        MoodEmbedField("Recent Triggers", DEGRADED_TRIGGERS),
        MoodEmbedField("Streak", DEGRADED_STREAK),
        MoodEmbedField("Forecast", DEGRADED_FORECAST),
    )
    footer_text: str = FOOTER_TEXT
    footer_icon: str = FOOTER_ICON
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


def display_for_mood(mood: str) -> str:
    """Return a display string like ``"😊 Content"`` for a mood name.

    Args:
        mood: A lowercase mood name (e.g. ``"content"``, ``"angry"``).

    Returns:
        An emoji + label string, or ``"😊 Content"`` if unknown.
    """
    emoji = _MOOD_EMOJI.get(mood, "\U0001f60a")
    label = _MOOD_LABEL.get(mood, "Content")
    return f"{emoji} {label}"


# ── Embed Builder ───────────────────────────────────────────────────────────


def build_mood_embed_data(
    now: datetime | None = None,
    mood: str = DEFAULT_MOOD,
) -> MoodEmbedData:
    """Build a deterministic ``MoodEmbedData`` with all 6 embed fields.

    Degraded placeholders are used for subsystems not yet deployed
    (P3 Memory, P4 Persona, P5 Agent Loop).

    Args:
        now: Override timestamp for determinism (e.g. in tests).
             Defaults to ``datetime.now(timezone.utc)``.
        mood: Override mood name for display and color computation.
              Defaults to ``"content"``.

    Returns:
        A fully populated ``MoodEmbedData``.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)
    dynamic_color = color_for_mood(mood)
    current_display = display_for_mood(mood)

    fields = (
        MoodEmbedField("Current Mood", current_display),
        MoodEmbedField("Undertone", DEGRADED_UNDERTONE),
        MoodEmbedField("24h History", DEGRADED_HISTORY),
        MoodEmbedField("Recent Triggers", DEGRADED_TRIGGERS),
        MoodEmbedField("Streak", DEGRADED_STREAK),
        MoodEmbedField("Forecast", DEGRADED_FORECAST),
    )

    return MoodEmbedData(
        title=MOOD_TITLE,
        description=MOOD_DESCRIPTION,
        color=dynamic_color,
        fields=fields,
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: MoodEmbedData) -> DiscordEmbedProtocol:
    """Convert ``MoodEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.
    Raises ``ImportError`` if the ``discord`` package is unavailable.

    Args:
        data: The mood embed data to convert.

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

    footer_line = (
        f"{data.footer_text} \u2022 {data.timestamp} \u2022 {data.footer_icon}"
    )
    embed.set_footer(text=footer_line)

    return embed


# ── Discord Interaction Callback ────────────────────────────────────────────


async def mood_callback(interaction: object) -> None:
    """Handle a ``/mood`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, builds the mood embed, and sends it as a followup.
    If any embedding step fails, a graceful degraded fallback message
    is sent rather than crashing the entire command.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await _send_denied(interaction)
        return

    await _defer_ephemeral(interaction)

    try:
        data = build_mood_embed_data()
        embed = to_discord_embed(data)
        await _followup_send(interaction, embed=embed)
    except Exception:
        logger.exception("mood_callback: failed to build or send mood embed")
        await _followup_send(
            interaction,
            content="\u26a0\ufe0f Mommy's mood analysis is temporarily unavailable.",
        )


# ── Internal Interaction Helpers ────────────────────────────────────────────


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
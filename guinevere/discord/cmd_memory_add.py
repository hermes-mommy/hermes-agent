"""Discord /memory-add command implementation for Guinevere.

Provides deterministic embed data builder and discord.py callback helpers.
Stores a manual memory note via the write pipeline and confirms with an embed.

Usage:
    # Build embed data without discord.py:
    data = build_memory_add_embed_data(episode_id, note)

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as callback:
    # tree.command(name="memory-add", description="...")(memory_add_callback)
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, cast, runtime_checkable

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for cmd_memory_add. Used in the broad exception handler."""

from .colors import SUCCESS


# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

ADD_TITLE: Final[str] = "\U0001f4dd Memory Stored"
ADD_DESCRIPTION: Final[str] = (
    "Mommy simpan catatannya, Darling. Aman sama Mommy."
)
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\u2728 Content"
MAX_NOTE_PREVIEW: Final[int] = 200


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/memory-add``.

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

    Covers only the subset needed by ``/memory-add``: defer, is_done,
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
    by the ``/memory-add`` callback helpers.
    """

    response: DiscordResponseProtocol
    followup: DiscordFollowupProtocol


# ── Data Types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MemoryAddEmbedField:
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
class MemoryAddEmbedData:
    """Deterministic embed data for the ``/memory-add`` command.

    Can be converted to a ``discord.Embed`` via ``to_discord_embed()``
    or consumed by any other renderer without a ``discord.py`` dependency.

    Attributes:
        title: Embed title.
        description: Embed description / persona sentence.
        color: Embed colour integer.
        fields: Tuple of confirmation fields.
        footer_text: Left footer text.
        footer_icon: Right footer icon / label.
        timestamp: WIB-formatted timestamp string.
    """

    title: str = ADD_TITLE
    description: str = ADD_DESCRIPTION
    color: int = SUCCESS
    fields: tuple[MemoryAddEmbedField, ...] = ()
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


def _get_option_value(interaction: object, option_name: str) -> str | None:
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


def build_memory_add_embed_data(
    episode_id: str,
    note: str,
    classification: str = "Restricted",
    *,
    now: datetime | None = None,
) -> MemoryAddEmbedData:
    """Build embed data confirming a stored memory episode.

    Args:
        episode_id: The UUID string of the newly created episode.
        note: The original note text (will be truncated for preview).
        classification: Data classification level used for storage.
        now: Override timestamp for determinism (e.g. in tests).
             Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        A fully populated ``MemoryAddEmbedData``.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)

    note_preview = (
        note[:MAX_NOTE_PREVIEW] + "..." if len(note) > MAX_NOTE_PREVIEW else note
    )
    episode_short = episode_id[:8]

    fields = (
        MemoryAddEmbedField("Note Preview", note_preview),
        MemoryAddEmbedField("Classification", classification),
        MemoryAddEmbedField("Episode ID", episode_short),
    )

    return MemoryAddEmbedData(
        title=ADD_TITLE,
        description=ADD_DESCRIPTION,
        color=SUCCESS,
        fields=fields,
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: MemoryAddEmbedData) -> DiscordEmbedProtocol:
    """Convert ``MemoryAddEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.
    Raises ``ImportError`` if the ``discord`` package is unavailable.

    Args:
        data: The memory add embed data to convert.

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


async def memory_add_callback(interaction: object) -> None:
    """Handle a ``/memory-add`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, extracts the note option, calls the write pipeline,
    builds the confirmation embed, and sends it as a followup.
    If any step fails, a graceful degraded fallback message is sent
    rather than crashing the entire command.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await _send_denied(interaction)
        return

    await _defer_ephemeral(interaction)

    try:
        note = _get_option_value(interaction, "note")
        if not note:
            await _followup_send(
                interaction,
                content="Catatannya tidak boleh kosong, Darling.",
            )
            return

        client = getattr(interaction, "client", None)
        session_factory_fn = (
            getattr(client, "get_session_factory", None)
            if client is not None
            else None
        )
        if session_factory_fn is None:
            await _followup_send(
                interaction,
                content=(
                    "\u26a0\ufe0f Memory add is temporarily unavailable. "
                    "Database not configured."
                ),
            )
            return

        session_factory = session_factory_fn()
        if session_factory is None:
            await _followup_send(
                interaction,
                content=(
                    "\u26a0\ufe0f Memory add is temporarily unavailable. "
                    "Database not configured."
                ),
            )
            return

        from guinevere.memory.embeddings import EmbeddingService
        from guinevere.memory.write_pipeline import store_episode

        embedding_service = EmbeddingService()

        async with session_factory() as session:
            episode_uuid = await store_episode(
                session,
                note,
                source="discord_manual",
                classification="Restricted",
                importance=5,
                episode_type="conversation",
                embedding_service=embedding_service,
            )

        data = build_memory_add_embed_data(
            episode_id=str(episode_uuid),
            note=note,
        )
        embed = to_discord_embed(data)
        await _followup_send(interaction, embed=embed)
    except Exception as exc:
        logger.exception("memory_add_callback")
        from guinevere.memory.write_pipeline import WritePipelineCriticalError

        if isinstance(exc, WritePipelineCriticalError):
            await _followup_send(
                interaction,
                content=(
                    "\u26a0\ufe0f Critical classification memories require "
                    "a summary. This note cannot be stored as-is."
                ),
            )
        else:
            await _followup_send(
                interaction,
                content=(
                    "\u26a0\ufe0f Memory add is temporarily unavailable."
                ),
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

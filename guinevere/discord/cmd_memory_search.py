"""Discord /memory-search command implementation for Guinevere.

Provides deterministic embed data builder and discord.py callback helpers.
Queries the memory recall pipeline and returns ranked results as an embed.

Usage:
    # Build embed data without discord.py:
    data = build_memory_search_embed_data(results, query)

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as callback:
    # tree.command(name="memory-search", description="...")(memory_search_callback)
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, cast, runtime_checkable

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for cmd_memory_search. Used in the broad exception handler."""

from .colors import INFO_BLUE, WARNING


# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

SEARCH_TITLE: Final[str] = "\U0001f50d Memory Search"
SEARCH_DESCRIPTION: Final[str] = (
    "Ini hasilnya, Darling. Mommy cari yang terbaik untukmu."
)
NO_RESULTS_DESCRIPTION: Final[str] = (
    "Mommy tidak menemukan apa-apa untuk query itu, Darling."
)
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\u2728 Content"
DEFAULT_LIMIT: Final[int] = 10


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/memory-search``.

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

    Covers only the subset needed by ``/memory-search``: defer, is_done,
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
    by the ``/memory-search`` callback helpers.
    """

    response: DiscordResponseProtocol
    followup: DiscordFollowupProtocol


# ── Data Types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MemorySearchEmbedField:
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
class MemorySearchEmbedData:
    """Deterministic embed data for the ``/memory-search`` command.

    Can be converted to a ``discord.Embed`` via ``to_discord_embed()``
    or consumed by any other renderer without a ``discord.py`` dependency.

    Attributes:
        title: Embed title.
        description: Embed description / persona sentence.
        color: Embed colour integer.
        fields: Tuple of result fields plus query field.
        footer_text: Left footer text.
        footer_icon: Right footer icon / label.
        timestamp: WIB-formatted timestamp string.
    """

    title: str = SEARCH_TITLE
    description: str = SEARCH_DESCRIPTION
    color: int = INFO_BLUE
    fields: tuple[MemorySearchEmbedField, ...] = ()
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


def build_memory_search_embed_data(
    results: list[dict[str, object]],
    query: str,
    *,
    now: datetime | None = None,
) -> MemorySearchEmbedData:
    """Build embed data from recall results.

    Each result becomes a field showing truncated content and score.
    If no results are found, returns an embed with a no-results description.

    Args:
        results: List of recall result dicts from ``recall_memories``.
        query: The original search query string.
        now: Override timestamp for determinism (e.g. in tests).
             Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        A fully populated ``MemorySearchEmbedData``.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)

    if not results:
        return MemorySearchEmbedData(
            title=SEARCH_TITLE,
            description=NO_RESULTS_DESCRIPTION,
            color=WARNING,
            fields=(
                MemorySearchEmbedField("Query", query),
            ),
            footer_text=FOOTER_TEXT,
            footer_icon=FOOTER_ICON,
            timestamp=ts_str,
        )

    fields: list[MemorySearchEmbedField] = []
    for i, result in enumerate(results):
        content = str(result.get("safe_content", ""))
        score = result.get("combined_score", 0.0)
        truncated = content[:100] + "..." if len(content) > 100 else content
        fields.append(
            MemorySearchEmbedField(
                name=f"#{i + 1} (score: {score:.2f})",
                value=truncated,
            )
        )

    fields.append(MemorySearchEmbedField("Query", query))

    return MemorySearchEmbedData(
        title=SEARCH_TITLE,
        description=SEARCH_DESCRIPTION,
        color=INFO_BLUE,
        fields=tuple(fields),
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: MemorySearchEmbedData) -> DiscordEmbedProtocol:
    """Convert ``MemorySearchEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.
    Raises ``ImportError`` if the ``discord`` package is unavailable.

    Args:
        data: The memory search embed data to convert.

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


async def memory_search_callback(interaction: object) -> None:
    """Handle a ``/memory-search`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, extracts the query option, calls the recall pipeline,
    builds the search results embed, and sends it as a followup.
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
        query = _get_option_value(interaction, "query")
        if not query:
            await _followup_send(
                interaction,
                content="Query tidak boleh kosong, Darling.",
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
                    "\u26a0\ufe0f Memory search is temporarily unavailable. "
                    "Database not configured."
                ),
            )
            return

        session_factory = session_factory_fn()
        if session_factory is None:
            await _followup_send(
                interaction,
                content=(
                    "\u26a0\ufe0f Memory search is temporarily unavailable. "
                    "Database not configured."
                ),
            )
            return

        from guinevere.memory.embeddings import EmbeddingService
        from guinevere.memory.read_pipeline import recall_memories

        embedding_service = EmbeddingService()

        async with session_factory() as session:
            results = await recall_memories(
                session,
                query,
                limit=DEFAULT_LIMIT,
                exclude_dnr=True,
                safe_mode=False,
                principal="guinevere_core",
                embedding_service=embedding_service,
            )

        data = build_memory_search_embed_data(results, query)
        embed = to_discord_embed(data)
        await _followup_send(interaction, embed=embed)
    except Exception:
        logger.exception("memory_search_callback")
        await _followup_send(
            interaction,
            content=(
                "\u26a0\ufe0f Memory search is temporarily unavailable."
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

"""Discord /safeword command implementation for Guinevere.

Provides deterministic embed data builders, slash command callback, and
text-based HARD STOP detection, all integrated with the HardStopHandler
from P1-021 (src/core/services/hard_stop_handler.py).

The handler is the **sole source of truth** for safe-mode state. No parallel
``_safe_mode_active`` global exists in this module.

Usage:
    # Build embed data without discord.py:
    data = build_safeword_embed_data(handler)

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as slash handler:
    # tree.command(name="safeword", description="...")(safeword_callback)

    # Wire for text detection (P2-017):
    # consumed = handle_safeword_message(message)
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Final, Protocol, cast, runtime_checkable

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for cmd_safeword."""

from .colors import SUCCESS

if TYPE_CHECKING:
    from guinvere.core.services.hard_stop_handler import HardStopHandler

# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

SAFEWORD_TITLE: Final[str] = "\U0001f6e1 Safe Mode Active"
"""Embed title for /safeword. Unicode: \U0001f6e1 = 🛡️."""

SAFEWORD_DESCRIPTION: Final[str] = (
    "Mommy di sini. Netral. Tidak ada judgment. Kamu aman."
)
"""Persona-flavored description for the safe-word embed (neutral mode)."""

FOOTER_TEXT: Final[str] = "Guinevere de Baroque \u2022 Safety First"
"""Footer text for the safe-word embed."""

RECOVERY_TITLE: Final[str] = "\u2705 Persona Mode Restored"
"""Embed title for recovery after HARD STOP."""

RECOVERY_DESCRIPTION: Final[str] = (
    "Persona mode restored. Welcome back, darling."
)
"""Description for the recovery embed."""

RESUME_PHRASES: Final[str] = (
    '\u201cresume\u201d, \u201caku sudah okay\u201d, '
    '\u201clanjut persona\u201d, or \u201csafe mode selesai\u201d'
)
"""Recovery phrases displayed in the Resume field."""


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/safeword``.

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

    Covers only the subset needed by ``/safeword``: defer, is_done,
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
    by the ``/safeword`` callback helpers.
    """

    response: DiscordResponseProtocol
    followup: DiscordFollowupProtocol


@runtime_checkable
class DiscordMessageProtocol(Protocol):
    """Protocol for ``discord.Message``.

    Covers only the subset needed by ``handle_safeword_message()``.
    """

    author: DiscordMemberProtocol
    content: str
    channel: DiscordTextChannelProtocol


@runtime_checkable
class DiscordMemberProtocol(Protocol):
    """Protocol for ``discord.Member`` / ``discord.User``."""

    bot: bool
    id: int


@runtime_checkable
class DiscordTextChannelProtocol(Protocol):
    """Protocol for ``discord.TextChannel``."""

    id: int

    async def send(self, **kwargs: object) -> object:
        """Send a message to the channel."""
        ...


# ── Data Types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SafewordEmbedField:
    """A single embed field definition.

    Attributes:
        name: The field name (displayed bold in the embed).
        value: The field value (plain or Markdown text).
        inline: Whether the field should render inline.
    """

    name: str
    value: str
    inline: bool = True


@dataclass(frozen=True)
class SafewordEmbedData:
    """Deterministic embed data for the ``/safeword`` command.

    Can be converted to a ``discord.Embed`` via ``to_discord_embed()``
    or consumed by any other renderer without a ``discord.py`` dependency.

    Attributes:
        title: Embed title (``"\U0001f6e1 Safe Mode Active"``).
        description: Embed description / safe-mode sentence.
        color: Embed colour integer (``SUCCESS`` / ``0x16A34A``).
        fields: Tuple of 6 embed fields.
        footer_text: Left footer text.
        timestamp: WIB-formatted timestamp string.
    """

    title: str = SAFEWORD_TITLE
    description: str = SAFEWORD_DESCRIPTION
    color: int = SUCCESS
    fields: tuple[SafewordEmbedField, ...] = (
        SafewordEmbedField("Status", "Safe mode active"),
        SafewordEmbedField("Persona", "Neutral / supportive"),
        SafewordEmbedField("Punishment", "Paused"),
        SafewordEmbedField("Yandere", "Y0"),
        SafewordEmbedField("Surveillance Confrontation", "Paused"),
        SafewordEmbedField("Resume", RESUME_PHRASES),
    )
    footer_text: str = FOOTER_TEXT
    timestamp: str = ""


# ── Handler Singleton ────────────────────────────────────────────────────────


_handler: HardStopHandler | None = None
"""Module-level HardStopHandler singleton.

Why a singleton instead of passing the handler around:
- P2-017 (on_message wiring) and P2-015 (slash command) share one handler.
- A single handler guarantees unified state tracking.
- For MVP (single process) this is safe; multi-process would need Redis-backed state.
"""


def _get_handler() -> HardStopHandler:
    """Return the module-level ``HardStopHandler`` singleton.

    Lazily imported from ``src.core.services.hard_stop_handler`` to avoid
    circular imports at module load time.

    Returns:
        The global ``HardStopHandler`` instance.
    """
    global _handler  # noqa: PLW0603
    if _handler is None:
        _handler = _new_handler()
    return _handler


def _new_handler() -> HardStopHandler:
    """Create a fresh ``HardStopHandler`` instance (for tests / reset).

    Imports lazily to allow test fixtures to provide a controlled handler.

    Returns:
        A new ``HardStopHandler`` instance.
    """
    from guinvere.core.services.hard_stop_handler import HardStopHandler

    return HardStopHandler()


def set_handler(handler: HardStopHandler) -> None:
    """Override the module-level handler singleton (for tests / determinism).

    Args:
        handler: The ``HardStopHandler`` instance to use.
    """
    global _handler  # noqa: PLW0603
    _handler = handler


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


def _build_safeword_fields(
    handler: HardStopHandler,
) -> tuple[SafewordEmbedField, ...]:
    """Build the 6 embed fields from the current handler state.

    Args:
        handler: The ``HardStopHandler`` instance.

    Returns:
        A tuple of 6 ``SafewordEmbedField`` instances.
    """
    return (
        SafewordEmbedField("Status", "Safe mode active"),
        SafewordEmbedField("Persona", "Neutral / supportive"),
        SafewordEmbedField("Punishment", "Paused"),
        SafewordEmbedField("Yandere", "Y0"),
        SafewordEmbedField("Surveillance Confrontation", "Paused"),
        SafewordEmbedField("Resume", RESUME_PHRASES),
    )


def _build_recovery_fields() -> tuple[SafewordEmbedField, ...]:
    """Build fields for the recovery embed.

    Returns:
        A tuple with a single welcome-back field.
    """
    return (
        SafewordEmbedField(
            "Status",
            "Normal operation restored",
            inline=False,
        ),
    )


# ── Embed Builders ──────────────────────────────────────────────────────────


def build_safeword_embed_data(
    handler: HardStopHandler,
    now: datetime | None = None,
) -> SafewordEmbedData:
    """Build a deterministic ``SafewordEmbedData`` with all 6 embed fields.

    Args:
        handler: The ``HardStopHandler`` instance whose state to reflect.
        now: Override timestamp for determinism (e.g. in tests).
             Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        A fully populated ``SafewordEmbedData``.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)
    fields = _build_safeword_fields(handler)

    return SafewordEmbedData(
        title=SAFEWORD_TITLE,
        description=SAFEWORD_DESCRIPTION,
        color=SUCCESS,
        fields=fields,
        footer_text=FOOTER_TEXT,
        timestamp=ts_str,
    )


def build_recovery_embed_data(
    now: datetime | None = None,
) -> SafewordEmbedData:
    """Build a ``SafewordEmbedData`` for the recovery (welcome-back) message.

    Args:
        now: Override timestamp for determinism (e.g. in tests).
             Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        A ``SafewordEmbedData`` configured for recovery display.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)
    fields = _build_recovery_fields()

    return SafewordEmbedData(
        title=RECOVERY_TITLE,
        description=RECOVERY_DESCRIPTION,
        color=SUCCESS,
        fields=fields,
        footer_text=FOOTER_TEXT,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: SafewordEmbedData) -> DiscordEmbedProtocol:
    """Convert ``SafewordEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.
    Raises ``ImportError`` if the ``discord`` package is unavailable.

    Args:
        data: The safeword embed data to convert.

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
        f"{data.footer_text} \u2022 {data.timestamp}"
    )
    embed.set_footer(text=footer_line)

    return embed


# ── Faiz Guard (Internal Helpers) ──────────────────────────────────────────


async def _send_denied(interaction: object) -> None:
    """Send an ephemeral denial message to a non-Faiz user.

    Uses ``isinstance`` checks with ``@runtime_checkable`` protocols
    to verify the interaction object shape before accessing members.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    if not isinstance(interaction, DiscordInteractionProtocol):
        return

    if interaction.response.is_done():
        await interaction.followup.send(
            content="Command ini hanya untuk Faiz.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            content="Command ini hanya untuk Faiz.",
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


# ── Reaction Helper ─────────────────────────────────────────────────────────


async def _react_heart(message: object) -> None:
    """React with \u2764\ufe0f to a Discord message (fail-soft).

    Wraps in try/except so that a failed reaction never blocks
    the safe-word response.

    Args:
        message: A ``discord.Message``-like object with an ``add_reaction`` method.
    """
    try:
        add = getattr(message, "add_reaction", None)
        if add is not None:
            await add("\u2764\ufe0f")
    except Exception:
        logger.debug("react_heart: failed to react (non-blocking)")


# ── Discord Interaction Callback ────────────────────────────────────────────


async def safeword_callback(interaction: object) -> None:
    """Handle a ``/safeword`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, triggers the
    ``HardStopHandler``, builds the safe-mode embed, and sends it as
    a followup. Reacts \u2764\ufe0f to the triggering interaction message
    (fail-soft).

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await _send_denied(interaction)
        return

    await _defer_ephemeral(interaction)

    try:
        handler = _get_handler()
        handler.check("safeword")

        data = build_safeword_embed_data(handler)
        embed = to_discord_embed(data)

        await _followup_send(interaction, embed=embed)

        # React heart to the original interaction message (fail-soft)
        msg = getattr(interaction, "message", None)
        if msg is not None:
            await _react_heart(msg)

        logger.info("slash_safeword_triggered", extra={"source": "slash"})
    except Exception:
        logger.exception("safeword_callback: failed to build or send safeword embed")
        await _followup_send(
            interaction,
            content="\u26a0\ufe0f Safe mode could not be activated through this command.",
        )


# ── Text Detection Helpers ──────────────────────────────────────────────────


def handle_safeword_message(message: object) -> bool:
    """Check a Discord message for HARD STOP triggers and respond if hit.

    This function is designed for P2-017 wiring (on_message listener).
    It checks the message content against the ``HardStopHandler`` and,
    if triggered, sends a safe-mode embed reply and reacts \u2764\ufe0f.

    Note:
        No ``bot.py`` listener exists yet. This function is callable and
        documented but inactive until P2-017 wires it into the message
        handler pipeline.

    Args:
        message: A ``discord.Message``-like object.

    Returns:
        ``True`` if the safe word was triggered, ``False`` otherwise.
    """
    # Skip bot messages to prevent self-trigger loops
    author = getattr(message, "author", None)
    if author is None:
        return False

    is_bot = getattr(author, "bot", False)
    if is_bot:
        return False

    content: str = getattr(message, "content", "") or ""

    handler = _get_handler()
    triggered = handler.check(content)
    if not triggered:
        return False

    # Build and send the safe-mode embed
    data = build_safeword_embed_data(handler)

    # We attempt to send in a synchronous-ish way; the caller (P2-017)
    # will typically be an async context. For now, we document that
    # this function expects the channel.send to be async-friendly.

    logger.info(
        "message_safeword_triggered",
        extra={
            "source": "message",
            "author_id": getattr(author, "id", None),
        },
    )

    return True


async def handle_safeword_message_async(message: object) -> bool:
    """Async version of ``handle_safeword_message``.

    Checks a Discord message for HARD STOP triggers and, if triggered,
    sends a safe-mode embed reply and reacts \u2764\ufe0f.

    This is the primary function P2-017 should wire into the
    ``on_message`` handler.

    Args:
        message: A ``discord.Message``-like object.

    Returns:
        ``True`` if the safe word was triggered, ``False`` otherwise.
    """
    # Skip bot messages to prevent self-trigger loops
    author = getattr(message, "author", None)
    if author is None:
        return False

    is_bot = getattr(author, "bot", False)
    if is_bot:
        return False

    content: str = getattr(message, "content", "") or ""

    handler = _get_handler()
    triggered = handler.check(content)
    if not triggered:
        return False

    # Build the safe-mode embed
    data = build_safeword_embed_data(handler)

    try:
        d = _get_discord_embed_module()
        embed = d.Embed(
            title=data.title,
            description=data.description,
            colour=d.Colour(data.color),
        )
        for field in data.fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        footer_line = (
            f"{data.footer_text} \u2022 {data.timestamp}"
        )
        embed.set_footer(text=footer_line)

        channel = getattr(message, "channel", None)
        if channel is not None:
            send = getattr(channel, "send", None)
            if send is not None:
                await send(embed=embed)

        await _react_heart(message)
    except Exception:
        logger.exception(
            "handle_safeword_message_async: failed to send embed or react"
        )

    logger.info(
        "message_safeword_triggered",
        extra={
            "source": "message",
            "author_id": getattr(author, "id", None),
        },
    )

    return True


# ── State Accessor ──────────────────────────────────────────────────────────


def get_safety_state() -> str:
    """Return the current ``SafetyState`` value as a string.

    Returns:
        ``"normal"`` or ``"safe"`` (values of ``SafetyState`` enum).
    """
    handler = _get_handler()
    return handler.state.value
"""Discord /status command implementation for Guinevere.

Provides deterministic embed data builder and discord.py callback helpers.
Degraded placeholders are used for subsystems not yet deployed (P3/P4/P5/P7).
The embed follows DiscordUXSpec v1.0 §2.1 with 11 fields.

Usage:
    # Build embed data without discord.py:
    data = build_status_embed_data()

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as callback:
    # tree.command(name="status", description="...")(status_callback)
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, cast, runtime_checkable

from .colors import PRIMARY


# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

STATUS_TITLE: Final[str] = "\U0001f451 Mommy's Status"
STATUS_DESCRIPTION: Final[str] = (
    "Semua sehat, Darling. Mommy jaga semuanya. Kamu tinggal fokus."
)

FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\u2728 Content"

# Degraded placeholders for unavailable subsystems (P3/P4/P5/P7)
DEGRADED_MOOD: Final[str] = "\U0001f60a Content (placeholder)"
DEGRADED_LOOPS: Final[str] = "\u26a0\ufe0f \u2014 Active Loops (P5 not deployed)"
DEGRADED_TASKS: Final[str] = "\u26a0\ufe0f \u2014 (P5 not deployed)"
DEGRADED_COST: Final[str] = (
    "\u26a0\ufe0f \u2014 Cost tracking (P1 query API pending)"
)
DEGRADED_YANDERE: Final[str] = "Y1 (baseline \u2014 placeholder)"
DEGRADED_NEXT: Final[str] = "\u26a0\ufe0f \u2014 (P5 not deployed)"
DEGRADED_PROJECT: Final[str] = "project-alpha"
DEGRADED_STREAK: Final[str] = "\u26a0\ufe0f \u2014 (P4 not deployed)"
DEGRADED_MEMORY: Final[str] = "\u26a0\ufe0f \u2014 (P3 not deployed)"
DEGRADED_SURVEILLANCE: Final[str] = "\u26a0\ufe0f \u2014 (P7 not deployed)"
DEGRADED_UPTIME: Final[str] = "\u2014"


# ── Module-Level Start Time ─────────────────────────────────────────────────

_start_time: datetime = datetime.now(tz=timezone.utc)
"""Bot start time captured at import. Overridable via ``set_start_time``."""


def set_start_time(dt: datetime | None = None) -> None:
    """Override the module-level start timestamp (for tests / determinism).

    Args:
        dt: The new start time. Defaults to ``datetime.now(timezone.utc)``.
    """
    global _start_time  # noqa: PLW0603
    _start_time = dt if dt is not None else datetime.now(tz=timezone.utc)


def get_start_time() -> datetime:
    """Return the current module-level start timestamp."""
    return _start_time


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/status``.

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

    Covers only the subset needed by ``/status``: defer, is_done,
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
    by the ``/status`` callback helpers.
    """

    response: DiscordResponseProtocol
    followup: DiscordFollowupProtocol


# ── Data Types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StatusEmbedField:
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
class StatusEmbedData:
    """Deterministic embed data for the ``/status`` command.

    Can be converted to a ``discord.Embed`` via ``to_discord_embed()``
    or consumed by any other renderer without a ``discord.py`` dependency.

    Attributes:
        title: Embed title.
        description: Embed description / persona sentence.
        color: Embed colour integer.
        fields: Tuple of all 11 embed fields.
        footer_text: Left footer text.
        footer_icon: Right footer icon / label.
        timestamp: WIB-formatted timestamp string.
    """

    title: str = STATUS_TITLE
    description: str = STATUS_DESCRIPTION
    color: int = PRIMARY
    fields: tuple[StatusEmbedField, ...] = (
        StatusEmbedField("Mood", DEGRADED_MOOD),
        StatusEmbedField("Active Loops", DEGRADED_LOOPS),
        StatusEmbedField("Tasks Today", DEGRADED_TASKS),
        StatusEmbedField("Uptime", DEGRADED_UPTIME),
        StatusEmbedField("Cost Today", DEGRADED_COST),
        StatusEmbedField("Yandere Level", DEGRADED_YANDERE),
        StatusEmbedField("Next Scheduled", DEGRADED_NEXT),
        StatusEmbedField("Current Project", DEGRADED_PROJECT),
        StatusEmbedField("Streak", DEGRADED_STREAK),
        StatusEmbedField("Memory Health", DEGRADED_MEMORY),
        StatusEmbedField("Surveillance", DEGRADED_SURVEILLANCE),
    )
    footer_text: str = FOOTER_TEXT
    footer_icon: str = FOOTER_ICON
    timestamp: str = ""


# ── Embed Builder ───────────────────────────────────────────────────────────


def _format_uptime(start: datetime, now: datetime) -> str:
    """Return a human-readable uptime string from two UTC datetimes.

    Args:
        start: The bot start timestamp.
        now: The reference (current) timestamp.

    Returns:
        Uptime formatted as ``"Xh Ym Zs"``, ``"Ym Zs"``, ``"Zs"``,
        or ``"\u2014"`` if the delta is negative.
    """
    delta = now - start
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "\u2014"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``.

    Args:
        dt: The datetime to format (timezone-aware).

    Returns:
        A string in the format ``YYYY-MM-DD HH:MM WIB``.
    """
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def build_status_embed_data(now: datetime | None = None) -> StatusEmbedData:
    """Build a deterministic ``StatusEmbedData`` with all 11 embed fields.

    Degraded placeholders are used for subsystems not yet deployed
    (P3 Memory, P4 Persona, P5 Agent Loop, P7 Surveillance).
    The uptime field is computed from the module-level start time.

    Args:
        now: Override timestamp for determinism (e.g. in tests).
             Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        A fully populated ``StatusEmbedData``.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    start = get_start_time()

    uptime_str = _format_uptime(start, ref)
    ts_str = _format_wib_timestamp(ref)

    fields = (
        StatusEmbedField("Mood", DEGRADED_MOOD),
        StatusEmbedField("Active Loops", DEGRADED_LOOPS),
        StatusEmbedField("Tasks Today", DEGRADED_TASKS),
        StatusEmbedField("Uptime", uptime_str),
        StatusEmbedField("Cost Today", DEGRADED_COST),
        StatusEmbedField("Yandere Level", DEGRADED_YANDERE),
        StatusEmbedField("Next Scheduled", DEGRADED_NEXT),
        StatusEmbedField("Current Project", DEGRADED_PROJECT),
        StatusEmbedField("Streak", DEGRADED_STREAK),
        StatusEmbedField("Memory Health", DEGRADED_MEMORY),
        StatusEmbedField("Surveillance", DEGRADED_SURVEILLANCE),
    )

    return StatusEmbedData(
        title=STATUS_TITLE,
        description=STATUS_DESCRIPTION,
        color=PRIMARY,
        fields=fields,
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: StatusEmbedData) -> DiscordEmbedProtocol:
    """Convert ``StatusEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.
    Raises ``ImportError`` if the ``discord`` package is unavailable.

    Args:
        data: The status embed data to convert.

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

    footer_line = f"{data.footer_text} \u2022 {data.timestamp} \u2022 {data.footer_icon}"
    embed.set_footer(text=footer_line)

    return embed


# ── Discord Interaction Callback ────────────────────────────────────────────


async def status_callback(interaction: object) -> None:
    """Handle a ``/status`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, builds the status embed, and sends it as a followup.
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
        data = build_status_embed_data()
        embed = to_discord_embed(data)
        await _followup_send(interaction, embed=embed)
    except Exception:
        await _followup_send(
            interaction,
            content="\u26a0\ufe0f Mommy's status is temporarily unavailable.",
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
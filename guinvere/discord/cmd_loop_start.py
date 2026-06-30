"""Discord /loop-start command implementation for Guinevere.

Starts a supervised Guinevere work loop via the internal API and confirms
with a styled embed.

Usage:
    # Build embed data without discord.py:
    data = build_loop_start_embed_data(loop_id, goal, status, priority)

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as callback:
    # tree.command(name="loop-start", description="...")(loop_start_callback)
"""

from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, cast, runtime_checkable

import httpx

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for cmd_loop_start."""

from .colors import SUCCESS


# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

LOOP_START_TITLE: Final[str] = "\U0001f504 Loop Started"
LOOP_START_DESCRIPTION: Final[str] = (
    "Mommy mulai kerja, Darling. Tunggu hasilnya ya~"
)
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\u2728 Content"
API_BASE_URL: Final[str] = "http://localhost:8000"
LOOPS_ENDPOINT: Final[str] = "/api/v1/loops"


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/loop-start``."""

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
    """Protocol for ``discord.Interaction.response``."""

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
    """Protocol for ``discord.Interaction``."""

    response: DiscordResponseProtocol
    followup: DiscordFollowupProtocol


# ── Data Types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LoopStartEmbedField:
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
class LoopStartEmbedData:
    """Deterministic embed data for the ``/loop-start`` command.

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

    title: str = LOOP_START_TITLE
    description: str = LOOP_START_DESCRIPTION
    color: int = SUCCESS
    fields: tuple[LoopStartEmbedField, ...] = ()
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


def build_loop_start_embed_data(
    loop_id: str,
    goal: str,
    status: str = "running",
    priority: str = "normal",
    *,
    now: datetime | None = None,
) -> LoopStartEmbedData:
    """Build embed data confirming a started work loop.

    Args:
        loop_id: The UUID string of the newly created loop.
        goal: The original goal text for the loop.
        status: Current loop status (e.g. "running", "queued").
        priority: Loop priority level.
        now: Override timestamp for determinism (e.g. in tests).
             Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        A fully populated ``LoopStartEmbedData``.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)

    loop_id_short = loop_id[:8]

    fields = (
        LoopStartEmbedField("Goal", goal),
        LoopStartEmbedField("Loop ID", loop_id_short, inline=True),
        LoopStartEmbedField("Status", status, inline=True),
        LoopStartEmbedField("Priority", priority, inline=True),
    )

    return LoopStartEmbedData(
        title=LOOP_START_TITLE,
        description=LOOP_START_DESCRIPTION,
        color=SUCCESS,
        fields=fields,
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: LoopStartEmbedData) -> DiscordEmbedProtocol:
    """Convert ``LoopStartEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.

    Args:
        data: The loop start embed data to convert.

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


async def loop_start_callback(interaction: object) -> None:
    """Handle a ``/loop-start`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, extracts the goal option, calls the internal API to
    start a loop, builds the confirmation embed, and sends it as a followup.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await _send_denied(interaction)
        return

    await _defer_ephemeral(interaction)

    try:
        goal = _get_option_value(interaction, "goal")
        if not goal:
            await _followup_send(
                interaction,
                content="Goal tidak boleh kosong, Darling.",
            )
            return

        api_key = os.environ.get("GUINEVERE_API_KEY")
        if not api_key:
            await _followup_send(
                interaction,
                content=(
                    "\u26a0\ufe0f GUINEVERE_API_KEY is not set. "
                    "Ask Faiz to configure it."
                ),
            )
            return
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}{LOOPS_ENDPOINT}",
                json={"task": goal, "priority": "normal"},
                headers={"X-Guinevere-API-Key": api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()

        loop_id = str(result.get("loop_id", result.get("id", "unknown")))
        status = str(result.get("status", "running"))
        priority = str(result.get("priority", "normal"))

        data = build_loop_start_embed_data(
            loop_id=loop_id,
            goal=goal,
            status=status,
            priority=priority,
        )
        embed = to_discord_embed(data)
        await _followup_send(interaction, embed=embed)
    except httpx.HTTPStatusError as exc:
        logger.exception("loop_start_callback http_error")
        await _followup_send(
            interaction,
            content=(
                f"\u26a0\ufe0f API returned {exc.response.status_code}. "
                "Loop gagal dimulai, Darling."
            ),
        )
    except httpx.RequestError as exc:
        logger.exception("loop_start_callback request_error")
        await _followup_send(
            interaction,
            content=(
                "\u26a0\ufe0f Tidak bisa menghubungi API internal. "
                "Coba lagi nanti ya, Darling."
            ),
        )
    except Exception:
        logger.exception("loop_start_callback unexpected_error")
        await _followup_send(
            interaction,
            content=(
                "\u26a0\ufe0f Terjadi kesalahan tak terduga. "
                "Mommy log untuk investigasi."
            ),
        )


# ── Internal Interaction Helpers ────────────────────────────────────────────


async def _send_denied(interaction: object) -> None:
    """Send an ephemeral denial message to a non-Faiz user.

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

"""Discord /loop-stop command implementation for Guinevere.

Stops one or all active Guinevere work loops via the internal API and confirms
with a styled embed.

Usage:
    # Build embed data without discord.py:
    data = build_loop_stop_embed_data(loop_id, phase, status)

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as callback:
    # tree.command(name="loop-stop", description="...")(loop_stop_callback)
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
"""Module-level logger for cmd_loop_stop."""

from .colors import WARNING


# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

LOOP_STOP_TITLE: Final[str] = "\u23f9\ufe0f Loop Stopped"
LOOP_STOP_DESCRIPTION: Final[str] = (
    "Mommy berhenti, Darling. Kalau mau lanjut lagi, bilang aja."
)
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\u2728 Content"
API_BASE_URL: Final[str] = "http://localhost:8000"
LOOPS_ENDPOINT: Final[str] = "/api/v1/loops"


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/loop-stop``."""

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
class LoopStopEmbedField:
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
class LoopStopEmbedData:
    """Deterministic embed data for the ``/loop-stop`` command.

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

    title: str = LOOP_STOP_TITLE
    description: str = LOOP_STOP_DESCRIPTION
    color: int = WARNING
    fields: tuple[LoopStopEmbedField, ...] = ()
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


def build_loop_stop_embed_data(
    loop_id: str,
    phase: str = "unknown",
    status: str = "cancelled",
    *,
    now: datetime | None = None,
) -> LoopStopEmbedData:
    """Build embed data confirming a stopped work loop.

    Args:
        loop_id: The UUID string of the stopped loop.
        phase: Previous phase before cancellation.
        status: Final status after cancellation.
        now: Override timestamp for determinism (e.g. in tests).
             Defaults to ``datetime.now(timezone.utc)``.

    Returns:
        A fully populated ``LoopStopEmbedData``.
    """
    ref = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref)

    loop_id_short = loop_id[:8]

    fields = (
        LoopStopEmbedField("Loop ID", loop_id_short, inline=True),
        LoopStopEmbedField("Previous Phase", phase, inline=True),
        LoopStopEmbedField("Status", status, inline=True),
    )

    return LoopStopEmbedData(
        title=LOOP_STOP_TITLE,
        description=LOOP_STOP_DESCRIPTION,
        color=WARNING,
        fields=fields,
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: LoopStopEmbedData) -> DiscordEmbedProtocol:
    """Convert ``LoopStopEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.

    Args:
        data: The loop stop embed data to convert.

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


# ── API Helpers ─────────────────────────────────────────────────────────────


async def _cancel_loop(client: httpx.AsyncClient, api_key: str, loop_id: str) -> dict[str, object]:
    """Cancel a single loop via the API.

    Args:
        client: An ``httpx.AsyncClient`` instance.
        api_key: The Guinevere API key.
        loop_id: The loop UUID to cancel.

    Returns:
        The JSON response from the cancellation endpoint.

    Raises:
        httpx.HTTPError: On API or network failure.
    """
    response = await client.post(
        f"{API_BASE_URL}{LOOPS_ENDPOINT}/{loop_id}/cancel",
        headers={"X-Guinevere-API-Key": api_key},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


async def _list_active_loops(client: httpx.AsyncClient, api_key: str) -> list[dict[str, object]]:
    """List all active (running/queued) loops via the API.

    Args:
        client: An ``httpx.AsyncClient`` instance.
        api_key: The Guinevere API key.

    Returns:
        A list of loop dicts that are currently active.
    """
    response = await client.get(
        f"{API_BASE_URL}{LOOPS_ENDPOINT}",
        headers={"X-Guinevere-API-Key": api_key},
        timeout=10.0,
    )
    response.raise_for_status()
    body: dict[str, object] = response.json()
    loops_data = body.get("loops", [])
    return [
        loop for loop in loops_data
        if loop.get("status") in ("running", "queued")
    ]


# ── Discord Interaction Callback ────────────────────────────────────────────


async def loop_stop_callback(interaction: object) -> None:
    """Handle a ``/loop-stop`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, extracts the optional ``loop_id`` option, cancels the
    target loop (or all active loops if no loop_id given) via the internal
    API, builds a confirmation embed, and sends it as a followup.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await _send_denied(interaction)
        return

    await _defer_ephemeral(interaction)

    try:
        loop_id = _get_option_value(interaction, "loop_id")
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
            cancelled: list[dict[str, object]] = []

            if loop_id:
                # Cancel a single specific loop
                result = await _cancel_loop(client, api_key, loop_id)
                cancelled.append(result)
            else:
                # Cancel all active loops
                active_loops = await _list_active_loops(client, api_key)
                if not active_loops:
                    await _followup_send(
                        interaction,
                        content="Tidak ada loop yang sedang aktif, Darling.",
                    )
                    return
                for active in active_loops:
                    lid = str(active.get("loop_id", active.get("id", "unknown")))
                    result = await _cancel_loop(client, api_key, lid)
                    cancelled.append(result)

        if not cancelled:
            await _followup_send(
                interaction,
                content="Loop berhasil dihentikan, tapi datanya kosong. Cek nanti ya.",
            )
            return

        # Build embed for the first cancelled loop (single most relevant)
        first = cancelled[0]
        lid = str(first.get("loop_id", first.get("id", "unknown")))
        phase = str(first.get("phase", "unknown"))
        status = str(first.get("status", "cancelled"))

        data = build_loop_stop_embed_data(
            loop_id=lid,
            phase=phase,
            status=status,
        )
        embed = to_discord_embed(data)

        if loop_id or len(cancelled) == 1:
            await _followup_send(interaction, embed=embed)
        else:
            # Multiple loops stopped — add a count note
            await _followup_send(
                interaction,
                embed=embed,
                content=f"Semua {len(cancelled)} loop aktif dihentikan.",
            )
    except httpx.HTTPStatusError as exc:
        logger.exception("loop_stop_callback http_error")
        await _followup_send(
            interaction,
            content=(
                f"\u26a0\ufe0f API returned {exc.response.status_code}. "
                "Loop gagal dihentikan, Darling."
            ),
        )
    except httpx.RequestError as exc:
        logger.exception("loop_stop_callback request_error")
        await _followup_send(
            interaction,
            content=(
                "\u26a0\ufe0f Tidak bisa menghubungi API internal. "
                "Coba lagi nanti ya, Darling."
            ),
        )
    except Exception:
        logger.exception("loop_stop_callback unexpected_error")
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
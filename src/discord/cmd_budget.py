"""Discord /budget command implementation for Guinevere (P8-018).

Shows or updates the monthly budget cap.  When ``action`` is ``view``
(default), displays current cap, spend, remaining, and percentage used.
When ``action`` is ``set``, updates the ``budget:monthly_cap`` key in
Redis DB5.

Usage:
    # Build embed data without discord.py:
    data = build_budget_embed_data()

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as callback:
    # tree.command(name="budget", description="...")(budget_callback)
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final, Protocol, cast, runtime_checkable

import redis

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for cmd_budget."""

from .colors import FINANCE


# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

BUDGET_TITLE: Final[str] = "\U0001f4b3 Budget Status"
"""Embed title for /budget. Unicode: \U0001f4b3 = 💳."""

BUDGET_DESCRIPTION: Final[str] = (
    "Mommy jaga budget biar nggak boros, Darling."
)
"""Persona-flavored description for the budget embed."""

BUDGET_SET_TITLE: Final[str] = "\u2705 Budget Updated"
"""Title for the budget-set confirmation embed."""

BUDGET_SET_DESCRIPTION: Final[str] = (
    "Budget cap sudah diupdate, Darling. Mommy tetap hemat."
)
"""Description for the budget-set confirmation embed."""

FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\U0001f4b3 Budget"

DEFAULT_ACTION: Final[str] = "view"
VALID_ACTIONS: Final[frozenset[str]] = frozenset({"view", "set"})

DEFAULT_MONTHLY_CAP: Final[float] = 30.0


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/budget``."""

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
    """Import ``discord`` dynamically and return typed embed interface."""
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
class BudgetEmbedField:
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
class BudgetEmbedData:
    """Deterministic embed data for the ``/budget`` command.

    Can be converted to a ``discord.Embed`` via ``to_discord_embed()``
    or consumed by any other renderer without a ``discord.py`` dependency.

    Attributes:
        title: Embed title.
        description: Embed description / persona sentence.
        color: Embed colour integer (teal / FINANCE).
        fields: Tuple of budget status fields.
        footer_text: Left footer text.
        footer_icon: Right footer icon / label.
        timestamp: WIB-formatted timestamp string.
    """

    title: str = BUDGET_TITLE
    description: str = BUDGET_DESCRIPTION
    color: int = FINANCE
    fields: tuple[BudgetEmbedField, ...] = ()
    footer_text: str = FOOTER_TEXT
    footer_icon: str = FOOTER_ICON
    timestamp: str = ""


# ── Helpers ─────────────────────────────────────────────────────────────────


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``."""
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


def _safe_float(raw: object) -> float:
    """Convert a Redis value to float, returning 0.0 on failure."""
    if raw is None:
        return 0.0
    try:
        return float(str(raw))
    except (ValueError, TypeError):
        return 0.0


def _format_currency(amount: float) -> str:
    """Format a float as a currency string."""
    return f"${amount:.2f}"


def _get_status_emoji(status: str) -> str:
    """Return an emoji for a budget status string."""
    status_map: dict[str, str] = {
        "NORMAL": "\u2705",
        "NORMAL_ALERT": "\U0001f7e1",
        "WARNING": "\u26a0\ufe0f",
        "CRITICAL": "\U0001f6a8",
        "HARD_STOP": "\U0001f6d1",
    }
    return status_map.get(status, "\u2753")


def _build_progress_bar(percentage: float, width: int = 10) -> str:
    """Build a text progress bar.

    Args:
        percentage: Percentage value (0-100+).
        width: Total bar width in characters.

    Returns:
        A string like ``"████░░░░░░"`` representing the percentage.
    """
    filled = min(int(percentage / 100 * width), width)
    empty = width - filled
    return "\u2588" * filled + "\u2591" * empty


# ── Redis Data Retrieval ────────────────────────────────────────────────────


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for budget data retrieval.

    Returns:
        A ``redis.Redis`` instance connected to DB5.
    """
    from src.core.services.cost_tracker import CostTracker

    tracker = CostTracker()
    return cast(redis.Redis, cast(object, tracker.redis))


def _get_budget_status(r: redis.Redis) -> dict[str, float | str]:
    """Read budget status from Redis.

    Args:
        r: Redis client instance.

    Returns:
        Dict with keys: current_month, monthly_cap, remaining,
        percent_used, status.
    """
    current = _safe_float(r.get("cost:current_month"))
    cap_raw = r.get("budget:monthly_cap")
    cap = _safe_float(cap_raw) if cap_raw is not None else DEFAULT_MONTHLY_CAP
    remaining = max(cap - current, 0.0)
    percent_used = (current / cap * 100) if cap > 0 else 0.0

    # Determine status based on ratio
    ratio = current / cap if cap > 0 else 1.0
    if ratio >= 1.0:
        status = "HARD_STOP"
    elif ratio >= 0.833:
        status = "CRITICAL"
    elif ratio >= 0.5:
        status = "WARNING"
    elif current >= 1.0:
        status = "NORMAL_ALERT"
    else:
        status = "NORMAL"

    return {
        "current_month": current,
        "monthly_cap": cap,
        "remaining": remaining,
        "percent_used": percent_used,
        "status": status,
    }


def _set_budget_cap(r: redis.Redis, amount: float) -> None:
    """Set the monthly budget cap in Redis.

    Args:
        r: Redis client instance.
        amount: New monthly cap value in USD.
    """
    r.set("budget:monthly_cap", str(amount))
    logger.info("budget_cap_updated to %.2f", amount)


# ── Embed Builder ───────────────────────────────────────────────────────────


def build_budget_embed_data(
    *,
    now: datetime | None = None,
) -> BudgetEmbedData:
    """Build deterministic embed data for the /budget view action.

    Reads budget data from Redis DB5 and constructs fields for cap,
    current spend, remaining, percentage, and status.

    Args:
        now: Override timestamp for determinism (e.g. in tests).

    Returns:
        A fully populated ``BudgetEmbedData``.
    """
    ref_dt = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref_dt)

    r = _get_redis_client()
    status = _get_budget_status(r)

    current = float(status["current_month"])
    cap = float(status["monthly_cap"])
    remaining = float(status["remaining"])
    percent = float(status["percent_used"])
    alert_status = str(status["status"])

    status_emoji = _get_status_emoji(alert_status)
    progress = _build_progress_bar(percent)

    fields: list[BudgetEmbedField] = []

    fields.append(
        BudgetEmbedField(
            name="\U0001f4b0 Monthly Cap",
            value=_format_currency(cap),
            inline=True,
        )
    )
    fields.append(
        BudgetEmbedField(
            name="\U0001f4b5 Current Spend",
            value=_format_currency(current),
            inline=True,
        )
    )
    fields.append(
        BudgetEmbedField(
            name="\U0001f4b3 Remaining",
            value=_format_currency(remaining),
            inline=True,
        )
    )
    fields.append(
        BudgetEmbedField(
            name="\U0001f4ca Usage",
            value=f"{progress} {percent:.1f}%",
            inline=False,
        )
    )
    fields.append(
        BudgetEmbedField(
            name="Status",
            value=f"{status_emoji} {alert_status}",
            inline=True,
        )
    )

    return BudgetEmbedData(
        title=BUDGET_TITLE,
        description=BUDGET_DESCRIPTION,
        color=FINANCE,
        fields=tuple(fields),
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


def build_budget_set_embed_data(
    new_cap: float,
    *,
    now: datetime | None = None,
) -> BudgetEmbedData:
    """Build embed data for the /budget set confirmation.

    Args:
        new_cap: The newly set monthly cap value.
        now: Override timestamp for determinism.

    Returns:
        A ``BudgetEmbedData`` confirming the update.
    """
    ref_dt = now if now is not None else datetime.now(tz=timezone.utc)
    ts_str = _format_wib_timestamp(ref_dt)

    r = _get_redis_client()
    current = _safe_float(r.get("cost:current_month"))
    remaining = max(new_cap - current, 0.0)
    percent = (current / new_cap * 100) if new_cap > 0 else 0.0

    fields: list[BudgetEmbedField] = [
        BudgetEmbedField(
            name="\U0001f4b0 New Monthly Cap",
            value=_format_currency(new_cap),
            inline=True,
        ),
        BudgetEmbedField(
            name="\U0001f4b5 Current Spend",
            value=_format_currency(current),
            inline=True,
        ),
        BudgetEmbedField(
            name="\U0001f4b3 Remaining",
            value=_format_currency(remaining),
            inline=True,
        ),
        BudgetEmbedField(
            name="\U0001f4ca Usage",
            value=f"{_build_progress_bar(percent)} {percent:.1f}%",
            inline=False,
        ),
    ]

    return BudgetEmbedData(
        title=BUDGET_SET_TITLE,
        description=BUDGET_SET_DESCRIPTION,
        color=FINANCE,
        fields=tuple(fields),
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: BudgetEmbedData) -> DiscordEmbedProtocol:
    """Convert ``BudgetEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.

    Args:
        data: The budget embed data to convert.

    Returns:
        A ``DiscordEmbedProtocol`` instance (equivalent to ``discord.Embed``).
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


async def budget_callback(interaction: object) -> None:
    """Handle a ``/budget`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, and either shows the current budget status or updates
    the monthly cap based on the ``action`` and ``amount`` options.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await _send_denied(interaction)
        return

    await _defer_ephemeral(interaction)

    try:
        action_raw = _get_option_value(interaction, "action")
        action = action_raw if action_raw and action_raw in VALID_ACTIONS else DEFAULT_ACTION

        if action == "set":
            amount_raw = _get_option_value(interaction, "amount")
            if amount_raw is None:
                await _followup_send(
                    interaction,
                    content=(
                        "\u26a0\ufe0f Parameter ``amount`` diperlukan untuk "
                        "action ``set``, Darling."
                    ),
                )
                return

            try:
                amount = float(amount_raw)
            except (ValueError, TypeError):
                await _followup_send(
                    interaction,
                    content="\u26a0\ufe0f Amount harus berupa angka, Darling.",
                )
                return

            if amount <= 0:
                await _followup_send(
                    interaction,
                    content="\u26a0\ufe0f Amount harus lebih besar dari 0, Darling.",
                )
                return

            r = _get_redis_client()
            _set_budget_cap(r, amount)

            data = build_budget_set_embed_data(amount)
            embed = to_discord_embed(data)
            await _followup_send(interaction, embed=embed)
        else:
            # Default: view
            data = build_budget_embed_data()
            embed = to_discord_embed(data)
            await _followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("budget_callback_failed")
        await _followup_send(
            interaction,
            content="\u26a0\ufe0f Budget status is temporarily unavailable.",
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

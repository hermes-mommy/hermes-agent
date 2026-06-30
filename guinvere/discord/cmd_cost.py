"""Discord /cost command implementation for Guinevere (P8-017).

Shows LLM cost usage for a configurable period (today, week, month).
Reads from Redis DB5 via CostTracker and builds a deterministic embed
with total spend, per-model breakdown, per-tool breakdown, 3-day trend,
and projected month-end spend.

Usage:
    # Build embed data without discord.py:
    data = build_cost_embed_data(period="today")

    # Convert to discord.Embed (requires discord.py installed):
    embed = to_discord_embed(data)

    # Use as callback:
    # tree.command(name="cost", description="...")(cost_callback)
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Final, Protocol, cast, runtime_checkable

import redis

logger: logging.Logger = logging.getLogger(__name__)
"""Module-level logger for cmd_cost."""

from .colors import PRIMARY


# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))
"""Asia/Bangkok/WIB timezone offset (+07:00)."""


# ── Constants ───────────────────────────────────────────────────────────────

COST_TITLE: Final[str] = "\U0001f4b0 Cost Report"
"""Embed title for /cost. Unicode: \U0001f4b0 = 💰."""

COST_DESCRIPTION: Final[str] = (
    "Ini pengeluaran kita, Darling. Mommy jaga supaya tetap hemat."
)
"""Persona-flavored description for the cost embed."""

FOOTER_TEXT: Final[str] = "Guinevere de Baroque"
FOOTER_ICON: Final[str] = "\U0001f4b0 FinOps"

DEFAULT_PERIOD: Final[str] = "today"
VALID_PERIODS: Final[frozenset[str]] = frozenset({"today", "week", "month"})


# ── Discord Embed Protocol ──────────────────────────────────────────────────


class DiscordEmbedProtocol(Protocol):
    """Minimal ``discord.Embed`` protocol used by ``/cost``."""

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
class CostEmbedField:
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
class CostEmbedData:
    """Deterministic embed data for the ``/cost`` command.

    Can be converted to a ``discord.Embed`` via ``to_discord_embed()``
    or consumed by any other renderer without a ``discord.py`` dependency.

    Attributes:
        title: Embed title.
        description: Embed description / persona sentence.
        color: Embed colour integer (purple / PRIMARY).
        fields: Tuple of cost report fields.
        footer_text: Left footer text.
        footer_icon: Right footer icon / label.
        timestamp: WIB-formatted timestamp string.
    """

    title: str = COST_TITLE
    description: str = COST_DESCRIPTION
    color: int = PRIMARY
    fields: tuple[CostEmbedField, ...] = ()
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


# ── Redis Data Retrieval ────────────────────────────────────────────────────


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for cost data retrieval.

    Returns:
        A ``redis.Redis`` instance connected to DB5.
    """
    from guinvere.core.services.cost_tracker import CostTracker

    tracker = CostTracker()
    return cast(redis.Redis, cast(object, tracker.redis))


def _get_period_total(r: redis.Redis, period: str, ref: date) -> float:
    """Get total cost for the specified period.

    Args:
        r: Redis client instance.
        period: One of ``"today"``, ``"week"``, ``"month"``.
        ref: Reference date for period calculation.

    Returns:
        Total cost as a float.
    """
    if period == "today":
        return _safe_float(r.get("cost:current_day"))

    if period == "week":
        total = 0.0
        for i in range(7):
            day = ref - timedelta(days=i)
            key = f"cost:daily:{day.isoformat()}"
            total += _safe_float(r.get(key))
        return total

    # period == "month"
    return _safe_float(r.get("cost:current_month"))


def _get_model_breakdown(r: redis.Redis) -> list[tuple[str, float]]:
    """Get per-model cost breakdown from Redis.

    Args:
        r: Redis client instance.

    Returns:
        List of (model_name, cost) tuples sorted by cost descending.
    """
    models: list[tuple[str, float]] = []
    try:
        for key in r.scan_iter(match="cost:by_model:*"):
            model_name = key.removeprefix("cost:by_model:")
            cost = _safe_float(r.get(key))
            if cost > 0:
                models.append((model_name, cost))
    except Exception:
        logger.warning("cost_model_breakdown_scan_failed")
    models.sort(key=lambda item: item[1], reverse=True)
    return models


def _get_tool_breakdown(r: redis.Redis, ref: date) -> list[tuple[str, float]]:
    """Get per-tool cost breakdown for today from Redis.

    Args:
        r: Redis client instance.
        ref: Reference date.

    Returns:
        List of (tool_name, cost) tuples sorted by cost descending.
    """
    tools: list[tuple[str, float]] = []
    today_str = ref.isoformat()
    pattern = f"tool:cost:*:{today_str}"
    try:
        for key in r.scan_iter(match=pattern):
            suffix = key.removeprefix("tool:cost:")
            if suffix.startswith("total:"):
                continue
            parts = suffix.rsplit(":", 1)
            if len(parts) != 2:
                continue
            tool_name = parts[0]
            cost = _safe_float(r.get(key))
            if cost > 0:
                tools.append((tool_name, cost))
    except Exception:
        logger.warning("cost_tool_breakdown_scan_failed")
    tools.sort(key=lambda item: item[1], reverse=True)
    return tools


def _get_3day_trend(r: redis.Redis, ref: date) -> list[tuple[str, float]]:
    """Get the 3-day cost trend.

    Args:
        r: Redis client instance.
        ref: Reference date.

    Returns:
        List of (date_str, cost) tuples in chronological order.
    """
    trend: list[tuple[str, float]] = []
    for i in range(2, -1, -1):
        day = ref - timedelta(days=i)
        key = f"cost:daily:{day.isoformat()}"
        cost = _safe_float(r.get(key))
        trend.append((day.strftime("%b %d"), cost))
    return trend


def _get_projected_month_end(r: redis.Redis, ref: date) -> float:
    """Project month-end spend based on daily average so far.

    Args:
        r: Redis client instance.
        ref: Reference date.

    Returns:
        Projected total spend for the month.
    """
    monthly_so_far = _safe_float(r.get("cost:current_month"))
    day_of_month = ref.day
    if day_of_month <= 0:
        return monthly_so_far
    import calendar

    days_in_month = calendar.monthrange(ref.year, ref.month)[1]
    daily_avg = monthly_so_far / day_of_month
    projected = daily_avg * days_in_month
    return projected


def _format_currency(amount: float) -> str:
    """Format a float as a currency string."""
    return f"${amount:.4f}"


def _format_trend_bar(trend: list[tuple[str, float]]) -> str:
    """Format trend data as a visual text block.

    Args:
        trend: List of (label, cost) tuples.

    Returns:
        Multi-line string showing trend bars.
    """
    if not trend:
        return "\u2014"
    max_cost = max(cost for _, cost in trend) if trend else 0.0
    lines: list[str] = []
    for label, cost in trend:
        if max_cost > 0:
            bar_len = int((cost / max_cost) * 10)
        else:
            bar_len = 0
        bar = "\u2588" * max(bar_len, 1) if cost > 0 else "\u2591"
        lines.append(f"`{label}` {bar} {_format_currency(cost)}")
    return "\n".join(lines)


# ── Embed Builder ───────────────────────────────────────────────────────────


def build_cost_embed_data(
    period: str = DEFAULT_PERIOD,
    *,
    now: datetime | None = None,
) -> CostEmbedData:
    """Build deterministic embed data for the /cost command.

    Reads cost data from Redis DB5 and constructs fields for total spend,
    per-model breakdown, per-tool breakdown, 3-day trend, and projected
    month-end.

    Args:
        period: One of ``"today"``, ``"week"``, ``"month"``.
        now: Override timestamp for determinism (e.g. in tests).

    Returns:
        A fully populated ``CostEmbedData``.
    """
    ref_dt = now if now is not None else datetime.now(tz=timezone.utc)
    ref_date = ref_dt.date() if hasattr(ref_dt, "date") else date.today()
    ts_str = _format_wib_timestamp(ref_dt)

    if period not in VALID_PERIODS:
        period = DEFAULT_PERIOD

    r = _get_redis_client()

    # Total for period
    total = _get_period_total(r, period, ref_date)

    # Per-model breakdown (top 5)
    models = _get_model_breakdown(r)[:5]

    # Per-tool breakdown (top 5)
    tools = _get_tool_breakdown(r, ref_date)[:5]

    # 3-day trend
    trend = _get_3day_trend(r, ref_date)

    # Projected month-end
    projected = _get_projected_month_end(r, ref_date)

    # Monthly total for context
    monthly_total = _safe_float(r.get("cost:current_month"))

    # Build fields
    fields: list[CostEmbedField] = []

    period_label = period.capitalize()
    fields.append(
        CostEmbedField(
            name=f"\U0001f4b5 {period_label} Spend",
            value=_format_currency(total),
            inline=True,
        )
    )
    fields.append(
        CostEmbedField(
            name="\U0001f4c5 Month to Date",
            value=_format_currency(monthly_total),
            inline=True,
        )
    )
    fields.append(
        CostEmbedField(
            name="\U0001f4c8 Projected Month-End",
            value=_format_currency(projected),
            inline=True,
        )
    )

    # Model breakdown
    if models:
        model_lines = [
            f"`{name}` — {_format_currency(cost)}" for name, cost in models
        ]
        fields.append(
            CostEmbedField(
                name="\U0001f916 Per-Model Breakdown",
                value="\n".join(model_lines),
                inline=False,
            )
        )
    else:
        fields.append(
            CostEmbedField(
                name="\U0001f916 Per-Model Breakdown",
                value="No model costs recorded yet.",
                inline=False,
            )
        )

    # Tool breakdown
    if tools:
        tool_lines = [
            f"`{name}` — {_format_currency(cost)}" for name, cost in tools
        ]
        fields.append(
            CostEmbedField(
                name="\U0001f527 Per-Tool Breakdown",
                value="\n".join(tool_lines),
                inline=False,
            )
        )
    else:
        fields.append(
            CostEmbedField(
                name="\U0001f527 Per-Tool Breakdown",
                value="No tool costs recorded today.",
                inline=False,
            )
        )

    # 3-day trend
    trend_text = _format_trend_bar(trend)
    fields.append(
        CostEmbedField(
            name="\U0001f4ca 3-Day Trend",
            value=trend_text,
            inline=False,
        )
    )

    return CostEmbedData(
        title=COST_TITLE,
        description=COST_DESCRIPTION,
        color=PRIMARY,
        fields=tuple(fields),
        footer_text=FOOTER_TEXT,
        footer_icon=FOOTER_ICON,
        timestamp=ts_str,
    )


# ── discord.py Conversion ───────────────────────────────────────────────────


def to_discord_embed(data: CostEmbedData) -> DiscordEmbedProtocol:
    """Convert ``CostEmbedData`` to a ``discord.Embed`` object.

    Uses dynamic ``importlib`` so that this function can be imported
    and pass static analysis even when ``discord`` is not installed.

    Args:
        data: The cost embed data to convert.

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


async def cost_callback(interaction: object) -> None:
    """Handle a ``/cost`` interaction.

    Enforces Faiz-only access via ``is_faiz_interaction``, defers
    ephemerally, extracts the period option, builds the cost embed
    from Redis data, and sends it as a followup.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await _send_denied(interaction)
        return

    await _defer_ephemeral(interaction)

    try:
        period_raw = _get_option_value(interaction, "period")
        period = period_raw if period_raw and period_raw in VALID_PERIODS else DEFAULT_PERIOD

        data = build_cost_embed_data(period=period)
        embed = to_discord_embed(data)
        await _followup_send(interaction, embed=embed)
    except Exception:
        logger.exception("cost_callback_failed")
        await _followup_send(
            interaction,
            content="\u26a0\ufe0f Cost report is temporarily unavailable.",
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

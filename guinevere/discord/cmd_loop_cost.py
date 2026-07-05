"""Discord /loop-cost command implementation for Guinevere (P5-018).

Aggregates cost-related statistics from completed loop instances,
including total loops, completed/failed counts, success rate, and an
estimated cost breakdown read from result_summary JSONB when available.

Usage:
    /loop-cost
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from .colors import FINANCE, NEUTRAL
from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()


# ── Constants ───────────────────────────────────────────────────────────────

COST_TITLE: str = "\U0001f4b8 Loop Cost"
COST_EMPTY: str = "No cost data available yet."
FOOTER_ICON: str = "\U0001f4b8 Loop Cost"


@dataclass(frozen=True)
class LoopCostStats:
    """Aggregated loop cost statistics."""

    total: int
    completed: int
    failed: int
    success_rate: float
    avg_cost: float
    total_cost: float


# ── Database Operation ──────────────────────────────────────────────────────


async def _fetch_loop_cost_stats(session_factory: Any) -> LoopCostStats | None:
    """Aggregate loop cost statistics from the database.

    Args:
        session_factory: Async SQLAlchemy session factory.

    Returns:
        LoopCostStats or None if no completed loops exist.
    """
    from sqlalchemy import text

    stats: LoopCostStats | None = None
    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT "
                "  COUNT(*) AS total, "
                "  COUNT(*) FILTER (WHERE status = 'completed') AS completed, "
                "  COUNT(*) FILTER (WHERE status = 'failed') AS failed, "
                "  COALESCE(AVG("
                "    COALESCE((result_summary ->> 'cost_usd')::float, 0.0)"
                "  ), 0.0) AS avg_cost, "
                "  COALESCE(SUM("
                "    COALESCE((result_summary ->> 'cost_usd')::float, 0.0)"
                "  ), 0.0) AS total_cost "
                "FROM projects.loop_instances"
            )
        )
        row = result.mappings().first()
        if row is None:
            return None

        total = int(row["total"] or 0)
        completed = int(row["completed"] or 0)
        failed = int(row["failed"] or 0)
        success_rate = (completed / total * 100.0) if total > 0 else 0.0
        avg_cost = float(row["avg_cost"] or 0.0)
        total_cost = float(row["total_cost"] or 0.0)

        stats = LoopCostStats(
            total=total,
            completed=completed,
            failed=failed,
            success_rate=round(success_rate, 2),
            avg_cost=round(avg_cost, 4),
            total_cost=round(total_cost, 4),
        )
    return stats


# ── Embed Builder ───────────────────────────────────────────────────────────


def _build_embed_data(stats: LoopCostStats | None) -> EmbedData:
    """Build embed data from loop cost statistics."""

    ts = now_wib_str()

    if stats is None or stats.total == 0:
        return EmbedData(
            title=COST_TITLE,
            description=COST_EMPTY,
            color=NEUTRAL,
            fields=(),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields = (
        EmbedField("Total Loops", str(stats.total), inline=True),
        EmbedField("Completed", str(stats.completed), inline=True),
        EmbedField("Failed", str(stats.failed), inline=True),
        EmbedField("Success Rate", f"{stats.success_rate:.2f}%", inline=True),
        EmbedField("Avg Cost / Loop", f"${stats.avg_cost:.4f}", inline=True),
        EmbedField("Total Cost", f"${stats.total_cost:.4f}", inline=True),
    )

    return EmbedData(
        title=COST_TITLE,
        description="Cost breakdown for completed loop instances.",
        color=FINANCE,
        fields=fields,
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


# ── Callback ─────────────────────────────────────────────────────────────────


async def loop_cost_callback(interaction: Any) -> None:
    """Handle a ``/loop-cost`` interaction.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        bot = getattr(interaction, "client", None)
        if bot is None or not hasattr(bot, "get_session_factory"):
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Database session not available.",
            )
            return

        session_factory = bot.get_session_factory()
        if session_factory is None:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Database URL not configured.",
            )
            return

        stats = await _fetch_loop_cost_stats(session_factory)
        data = _build_embed_data(stats)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception as exc:
        logger.exception("loop_cost_callback_failed", exc=exc)
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Loop cost data is temporarily unavailable.",
        )


__all__ = ["loop_cost_callback"]

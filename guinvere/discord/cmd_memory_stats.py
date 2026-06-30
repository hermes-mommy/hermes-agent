"""Discord /memory-stats command implementation for Guinevere (P18).

Shows tier distribution counts, average retrievability, decay stats,
and FSRS statistics across all memory episodes.

Usage:
    /memory-stats
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from .colors import INFO_BLUE
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

STATS_TITLE: str = "\U0001f4ca Memory Stats"
STATS_DESC: str = "Distribusi tier memori dan statistik FSRS Mommy."
STATS_FAIL_DESC: str = "Gagal mengambil statistik memori."
FOOTER_ICON: str = "\U0001f4ca Memory Stats"


@dataclass(frozen=True)
class MemoryStats:
    """Aggregated memory statistics."""

    working_count: int
    episodic_count: int
    semantic_count: int
    avg_retrievability: float
    due_for_review: int
    avg_stability: float
    total: int


# ── Database Operation ──────────────────────────────────────────────────────


async def _fetch_memory_stats(session_factory: Any) -> MemoryStats | None:
    """Query Episodes table and aggregate tier/FSRS statistics.

    Args:
        session_factory: Async SQLAlchemy session factory.

    Returns:
        MemoryStats or None on failure.
    """
    try:
        from sqlalchemy import text

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT "
                    "  COUNT(*) FILTER (WHERE tier = 'working') AS working_count, "
                    "  COUNT(*) FILTER (WHERE tier = 'episodic') AS episodic_count, "
                    "  COUNT(*) FILTER (WHERE tier = 'semantic') AS semantic_count, "
                    "  COALESCE(AVG(retrievability), 0.0) AS avg_retrievability, "
                    "  COUNT(*) FILTER (WHERE next_review_at IS NOT NULL "
                    "    AND next_review_at <= NOW()) AS due_for_review, "
                    "  COALESCE(AVG(stability), 0.0) AS avg_stability, "
                    "  COUNT(*) AS total "
                    "FROM memory.episodes"
                )
            )
            row = result.fetchone()
            if row is None:
                return None

            return MemoryStats(
                working_count=row[0],
                episodic_count=row[1],
                semantic_count=row[2],
                avg_retrievability=round(float(row[3]), 4),
                due_for_review=row[4],
                avg_stability=round(float(row[5]), 2),
                total=row[6],
            )
    except Exception:
        logger.exception("memory_stats_db_error")
        return None


# ── Embed Builder ───────────────────────────────────────────────────────────


def _build_embed_data(stats: MemoryStats | None) -> EmbedData:
    """Build embed data from memory stats."""
    ts = now_wib_str()

    if stats is None:
        return EmbedData(
            title=STATS_TITLE,
            description=STATS_FAIL_DESC,
            color=INFO_BLUE,
            fields=(EmbedField(
                name="\u274c Error",
                value="Could not retrieve memory statistics.",
                inline=False,
            ),),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields = (
        EmbedField(
            name="\U0001f7e2 Working",
            value=str(stats.working_count),
            inline=True,
        ),
        EmbedField(
            name="\U0001f535 Episodic",
            value=str(stats.episodic_count),
            inline=True,
        ),
        EmbedField(
            name="\U0001f7e3 Semantic",
            value=str(stats.semantic_count),
            inline=True,
        ),
        EmbedField(
            name="\U0001f4c8 Avg Retrievability",
            value=f"{stats.avg_retrievability:.4f}",
            inline=True,
        ),
        EmbedField(
            name="\u23f0 Due for Review",
            value=str(stats.due_for_review),
            inline=True,
        ),
        EmbedField(
            name="\U0001f4cf Avg Stability",
            value=f"{stats.avg_stability:.2f}d",
            inline=True,
        ),
        EmbedField(
            name="\U0001f4cb Total Memories",
            value=str(stats.total),
            inline=False,
        ),
        EmbedField(
            name="\U0001f552 Timestamp",
            value=ts,
            inline=False,
        ),
    )
    return EmbedData(
        title=STATS_TITLE,
        description=STATS_DESC,
        color=INFO_BLUE,
        fields=fields,
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


# ── Callback ────────────────────────────────────────────────────────────────


async def memory_stats_callback(interaction: Any) -> None:
    """Handle a ``/memory-stats`` interaction.

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

        stats = await _fetch_memory_stats(session_factory)
        data = _build_embed_data(stats)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("memory_stats_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Memory stats are temporarily unavailable.",
        )


__all__ = ["memory_stats_callback"]

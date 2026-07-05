"""Discord /memory-schedule command implementation for Guinevere (P18).

Shows upcoming FSRS review schedule broken down by time buckets
(1h, 6h, 24h, 7d, 30d) with per-tier counts.

Usage:
    /memory-schedule
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

SCHEDULE_TITLE: str = "\U0001f4c5 Memory Schedule"
SCHEDULE_DESC: str = "Jadwal review FSRS Mommy untuk 30 hari ke depan."
SCHEDULE_FAIL_DESC: str = "Gagal mengambil jadwal review memori."
FOOTER_ICON: str = "\U0001f4c5 FSRS Schedule"


@dataclass(frozen=True)
class ScheduleBucket:
    """A time bucket with per-tier counts."""

    label: str
    working: int
    episodic: int
    semantic: int
    total: int


@dataclass(frozen=True)
class ScheduleData:
    """Aggregated review schedule across time buckets."""

    buckets: tuple[ScheduleBucket, ...]
    total_due: int


# ── Database Operation ──────────────────────────────────────────────────────


async def _fetch_schedule(session_factory: Any) -> ScheduleData | None:
    """Query Episodes for upcoming review schedule.

    Groups episodes with next_review_at into time buckets.

    Args:
        session_factory: Async SQLAlchemy session factory.

    Returns:
        ScheduleData or None on failure.
    """
    try:
        from sqlalchemy import text

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT "
                    "  tier, "
                    "  COUNT(*) FILTER (WHERE next_review_at <= NOW() + INTERVAL '1 hour') AS b_1h, "
                    "  COUNT(*) FILTER (WHERE next_review_at > NOW() + INTERVAL '1 hour' "
                    "    AND next_review_at <= NOW() + INTERVAL '6 hours') AS b_6h, "
                    "  COUNT(*) FILTER (WHERE next_review_at > NOW() + INTERVAL '6 hours' "
                    "    AND next_review_at <= NOW() + INTERVAL '24 hours') AS b_24h, "
                    "  COUNT(*) FILTER (WHERE next_review_at > NOW() + INTERVAL '24 hours' "
                    "    AND next_review_at <= NOW() + INTERVAL '7 days') AS b_7d, "
                    "  COUNT(*) FILTER (WHERE next_review_at > NOW() + INTERVAL '7 days' "
                    "    AND next_review_at <= NOW() + INTERVAL '30 days') AS b_30d "
                    "FROM memory.episodes "
                    "WHERE next_review_at IS NOT NULL "
                    "  AND next_review_at <= NOW() + INTERVAL '30 days' "
                    "GROUP BY tier"
                )
            )
            rows = result.fetchall()

            # Accumulate per-bucket totals across tiers
            totals = {"b_1h": 0, "b_6h": 0, "b_24h": 0, "b_7d": 0, "b_30d": 0}
            tier_data: dict[str, dict[str, int]] = {
                "working": {"b_1h": 0, "b_6h": 0, "b_24h": 0, "b_7d": 0, "b_30d": 0},
                "episodic": {"b_1h": 0, "b_6h": 0, "b_24h": 0, "b_7d": 0, "b_30d": 0},
                "semantic": {"b_1h": 0, "b_6h": 0, "b_24h": 0, "b_7d": 0, "b_30d": 0},
            }

            for row in rows:
                tier_name = str(row[0]) if row[0] else "working"
                if tier_name not in tier_data:
                    tier_name = "working"
                tier_data[tier_name]["b_1h"] = int(row[1])
                tier_data[tier_name]["b_6h"] = int(row[2])
                tier_data[tier_name]["b_24h"] = int(row[3])
                tier_data[tier_name]["b_7d"] = int(row[4])
                tier_data[tier_name]["b_30d"] = int(row[5])
                for k in totals:
                    totals[k] += int(row[1 + list(totals.keys()).index(k)])

            bucket_defs = (
                ("\u23f1\ufe0f Next 1h", "b_1h"),
                ("\u23f0 Next 6h", "b_6h"),
                ("\U0001f4c5 Next 24h", "b_24h"),
                ("\U0001f4c6 Next 7d", "b_7d"),
                ("\U0001f4c6 Next 30d", "b_30d"),
            )

            buckets = []
            for label, key in bucket_defs:
                w = tier_data["working"][key]
                e = tier_data["episodic"][key]
                s = tier_data["semantic"][key]
                buckets.append(ScheduleBucket(
                    label=label,
                    working=w,
                    episodic=e,
                    semantic=s,
                    total=w + e + s,
                ))

            total_due = sum(b.total for b in buckets)
            return ScheduleData(buckets=tuple(buckets), total_due=total_due)

    except Exception:
        logger.exception("memory_schedule_db_error")
        return None


# ── Embed Builder ───────────────────────────────────────────────────────────


def _build_embed_data(data: ScheduleData | None) -> EmbedData:
    """Build embed data from schedule data."""
    ts = now_wib_str()

    if data is None:
        return EmbedData(
            title=SCHEDULE_TITLE,
            description=SCHEDULE_FAIL_DESC,
            color=INFO_BLUE,
            fields=(EmbedField(
                name="\u274c Error",
                value="Could not retrieve review schedule.",
                inline=False,
            ),),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields_list: list[EmbedField] = []
    for bucket in data.buckets:
        value = (
            f"Working: {bucket.working} | "
            f"Episodic: {bucket.episodic} | "
            f"Semantic: {bucket.semantic} | "
            f"**Total: {bucket.total}**"
        )
        fields_list.append(EmbedField(name=bucket.label, value=value, inline=False))

    fields_list.append(EmbedField(
        name="\U0001f4cb Total Due (30d)",
        value=str(data.total_due),
        inline=True,
    ))
    fields_list.append(EmbedField(
        name="\U0001f552 Timestamp",
        value=ts,
        inline=False,
    ))

    return EmbedData(
        title=SCHEDULE_TITLE,
        description=SCHEDULE_DESC,
        color=INFO_BLUE,
        fields=tuple(fields_list),
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


# ── Callback ────────────────────────────────────────────────────────────────


async def memory_schedule_callback(interaction: Any) -> None:
    """Handle a ``/memory-schedule`` interaction.

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

        schedule = await _fetch_schedule(session_factory)
        data = _build_embed_data(schedule)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("memory_schedule_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Memory schedule is temporarily unavailable.",
        )


__all__ = ["memory_schedule_callback"]

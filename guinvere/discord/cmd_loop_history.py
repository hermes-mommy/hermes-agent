"""Discord /loop-history command implementation for Guinevere (P5-018).

Shows recent loop history with optional limit parameter. Results are
paginated into numbered chunks pages when more than 5 rows are returned.

Usage:
    /loop-history [limit]
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from .colors import INFO_BLUE, NEUTRAL
from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    get_option_value,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()


# ── Constants ───────────────────────────────────────────────────────────────

HISTORY_TITLE: str = "\U0001f504 Loop History"
HISTORY_EMPTY: str = "No loop history found."
FOOTER_ICON: str = "\U0001f504 Loop History"
DEFAULT_LIMIT: int = 5
MAX_LIMIT: int = 20
PAGE_SIZE: int = 5


@dataclass(frozen=True)
class LoopHistoryRow:
    """A single loop history row for display."""

    loop_id: str
    task: str
    goal: str
    status: str
    phase: int
    started_at: datetime
    completed_at: datetime | None

    @property
    def duration(self) -> str:
        """Return a human-friendly duration string."""

        start = self.started_at
        end = self.completed_at if self.completed_at else datetime.now(timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        delta = end - start
        total_seconds = max(int(delta.total_seconds()), 0)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m {seconds}s"
        return f"{minutes}m {seconds}s"


# ── Database Operation ──────────────────────────────────────────────────────


async def _fetch_loop_history(
    session_factory: Any,
    limit: int,
) -> list[LoopHistoryRow]:
    """Query the latest loop history rows ordered by started_at DESC.

    Args:
        session_factory: Async SQLAlchemy session factory.
        limit: Maximum number of rows to fetch.

    Returns:
        A list of loop history rows.
    """
    from sqlalchemy import text

    rows: list[LoopHistoryRow] = []
    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT "
                "  COALESCE(result_summary ->> 'loop_id', id::text) AS loop_id, "
                "  COALESCE(result_summary ->> 'task', '') AS task, "
                "  COALESCE(result_summary ->> 'goal', goal) AS goal, "
                "  status, "
                "  COALESCE(phase, 1) AS phase, "
                "  started_at, "
                "  completed_at "
                "FROM projects.loop_instances "
                "ORDER BY started_at DESC "
                "LIMIT :limit"
            ),
            {"limit": limit},
        )
        for row in result.mappings().all():
            started_at = row["started_at"]
            completed_at = row["completed_at"]
            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at)
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at)
            rows.append(
                LoopHistoryRow(
                    loop_id=row["loop_id"] or "",
                    task=row["task"] or "",
                    goal=row["goal"] or "",
                    status=row["status"] or "unknown",
                    phase=int(row["phase"] or 1),
                    started_at=started_at if started_at else datetime.now(timezone.utc),
                    completed_at=completed_at if completed_at else None,
                )
            )
    return rows


# ── Embed Builder ───────────────────────────────────────────────────────────


def _format_ts(dt: datetime | None) -> str:
    """Format a datetime for display."""

    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M")


def _build_embeds(rows: list[LoopHistoryRow]) -> list[EmbedData]:
    """Build one or more embed data objects, paginated by PAGE_SIZE."""

    ts = now_wib_str()

    if not rows:
        return [
            EmbedData(
                title=HISTORY_TITLE,
                description=HISTORY_EMPTY,
                color=NEUTRAL,
                fields=(),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
        ]

    embeds: list[EmbedData] = []
    total_pages = (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE
    for page_index in range(total_pages):
        start = page_index * PAGE_SIZE
        end = start + PAGE_SIZE
        page_rows = rows[start:end]
        fields: list[EmbedField] = []
        for idx, row in enumerate(page_rows, start=start + 1):
            loop_id_short = (row.loop_id or "")[:8] or "unknown"
            task = row.task[:50] if row.task else "(no task)"
            goal = row.goal[:60] if row.goal else "(no goal)"
            fields.append(
                EmbedField(
                    name=f"{idx}. `{loop_id_short}` — {row.status.upper()}",
                    value=(
                        f"**Task:** {task}\n"
                        f"**Goal:** {goal}\n"
                        f"**Phase:** {row.phase}/7\n"
                        f"**Started:** {_format_ts(row.started_at)}\n"
                        f"**Completed:** {_format_ts(row.completed_at)}\n"
                        f"**Duration:** {row.duration}"
                    ),
                    inline=False,
                )
            )

        embeds.append(
            EmbedData(
                title=HISTORY_TITLE,
                description=f"Page {page_index + 1} of {total_pages} — {len(rows)} total",
                color=INFO_BLUE,
                fields=tuple(fields),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
        )

    return embeds


# ── Callback ─────────────────────────────────────────────────────────────────


async def loop_history_callback(interaction: Any) -> None:
    """Handle a ``/loop-history`` interaction.

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

        limit_value = get_option_value(interaction, "limit")
        try:
            limit = int(limit_value) if limit_value else DEFAULT_LIMIT
        except ValueError:
            limit = DEFAULT_LIMIT
        limit = max(1, min(limit, MAX_LIMIT))

        rows = await _fetch_loop_history(session_factory, limit)
        embeds = _build_embeds(rows)
        for idx, data in enumerate(embeds):
            embed = to_discord_embed(data)
            if idx == 0:
                await followup_send(interaction, embed=embed)
            else:
                await followup_send(interaction, embed=embed)

    except Exception as exc:
        logger.exception("loop_history_callback_failed", exc=exc)
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Loop history is temporarily unavailable.",
        )


__all__ = ["loop_history_callback"]

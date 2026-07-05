"""Discord /loop-status command implementation for Guinevere (P5-018).

Shows the last 10 loop instances with their current status, phase, and
a short task summary. Colours indicate status: running (yellow),
completed (green), failed (red), and other states (neutral).

Usage:
    /loop-status
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from .colors import ALERT, NEUTRAL, SUCCESS, WARNING
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

STATUS_TITLE: str = "\U0001f504 Loop Status"
STATUS_EMPTY: str = "No active loops found."
FOOTER_ICON: str = "\U0001f504 Loop Status"
MAX_ROWS: int = 10


@dataclass(frozen=True)
class LoopStatusRow:
    """A single loop status row for display."""

    loop_id: str
    task: str
    phase: int
    status: str
    started_at: datetime


# ── Database Operation ──────────────────────────────────────────────────────


async def _fetch_recent_loops(session_factory: Any) -> list[LoopStatusRow]:
    """Query the latest loop instances ordered by started_at descending.

    Args:
        session_factory: Async SQLAlchemy session factory.

    Returns:
        A list of the most recent loop rows (up to MAX_ROWS).
    """
    from sqlalchemy import text

    rows: list[LoopStatusRow] = []
    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT "
                "  COALESCE(result_summary ->> 'loop_id', id::text) AS loop_id, "
                "  COALESCE(result_summary ->> 'task', '') AS task, "
                "  COALESCE(phase, 1) AS phase, "
                "  status, "
                "  started_at "
                "FROM projects.loop_instances "
                "ORDER BY started_at DESC "
                "LIMIT :limit"
            ),
            {"limit": MAX_ROWS},
        )
        for row in result.mappings().all():
            started_at = row["started_at"]
            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at)
            rows.append(
                LoopStatusRow(
                    loop_id=row["loop_id"] or "",
                    task=row["task"] or "",
                    phase=int(row["phase"] or 1),
                    status=row["status"] or "unknown",
                    started_at=started_at if started_at else datetime.now(timezone.utc),
                )
            )
    return rows


# ── Embed Builder ───────────────────────────────────────────────────────────


def _status_color(status: str) -> int:
    """Return an embed colour for a loop status."""

    status_lower = status.lower()
    if status_lower == "running":
        return WARNING
    if status_lower == "completed":
        return SUCCESS
    if status_lower == "failed":
        return ALERT
    return NEUTRAL


def _build_embed_data(rows: list[LoopStatusRow]) -> EmbedData:
    """Build embed data from loop status rows."""

    ts = now_wib_str()

    if not rows:
        return EmbedData(
            title=STATUS_TITLE,
            description=STATUS_EMPTY,
            color=NEUTRAL,
            fields=(),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields: list[EmbedField] = []
    for row in rows:
        loop_id = row.loop_id[:8] if row.loop_id else "unknown"
        task = row.task[:50] if row.task else "(no task)"
        started = row.started_at.strftime("%Y-%m-%d %H:%M")
        fields.append(
            EmbedField(
                name=f"`{loop_id}` — {row.status.upper()}",
                value=(
                    f"**Task:** {task}\n"
                    f"**Phase:** {row.phase}/7\n"
                    f"**Started:** {started}"
                ),
                inline=False,
            )
        )

    return EmbedData(
        title=STATUS_TITLE,
        description=f"Showing last {len(rows)} loop(s).",
        color=_status_color(rows[0].status),
        fields=tuple(fields),
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


# ── Callback ─────────────────────────────────────────────────────────────────


async def loop_status_callback(interaction: Any) -> None:
    """Handle a ``/loop-status`` interaction.

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

        rows = await _fetch_recent_loops(session_factory)
        data = _build_embed_data(rows)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception as exc:
        logger.exception("loop_status_callback_failed", exc=exc)
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Loop status is temporarily unavailable.",
        )


__all__ = ["loop_status_callback"]

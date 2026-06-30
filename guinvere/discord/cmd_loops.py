"""Discord /loops command implementation for Guinevere (RG-014).

Lists all active and recent loops via LoopManager.

Usage:
    /loops
"""

from __future__ import annotations

from typing import Any

import structlog

from .colors import PRIMARY
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

TITLE: str = "\U0001f504 Active Loops"
DESC_EMPTY: str = "Tidak ada loop aktif saat ini, Darling."
FOOTER_ICON: str = "\U0001f504 Loop"


async def _get_all_loops() -> list[dict[str, Any]]:
    """Get all active loops from LoopManager."""
    try:
        from guinvere.loops.manager import LoopManager

        manager = LoopManager()
        return await manager.list_loops()
    except Exception:
        logger.exception("loops_list_failed")
        return []


def _build_embed_data(loops: list[dict[str, Any]]) -> EmbedData:
    """Build embed data from loop list."""
    ts = now_wib_str()

    if not loops:
        return EmbedData(
            title=TITLE,
            description=DESC_EMPTY,
            color=PRIMARY,
            fields=(),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields: list[EmbedField] = []
    for loop in loops[:10]:  # Limit to 10 for embed field limit
        loop_id = loop.get("loop_id", "unknown")
        status = loop.get("status", "unknown")
        phase = loop.get("current_phase", "unknown")
        task = loop.get("task", "")[:50]

        # Truncate task for display
        task_display = task if task else "(no task)"
        fields.append(
            EmbedField(
                name=f"`{loop_id}`",
                value=(
                    f"Status: {status}\n"
                    f"Phase: {phase}\n"
                    f"Task: {task_display}"
                ),
                inline=False,
            )
        )

    return EmbedData(
        title=TITLE,
        description=f"{len(loops)} loop(s) aktif.",
        color=PRIMARY,
        fields=tuple(fields),
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


async def loops_callback(interaction: Any) -> None:
    """Handle a ``/loops`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        loops = await _get_all_loops()
        data = _build_embed_data(loops)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("loops_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Loops list is temporarily unavailable.",
        )


__all__ = ["loops_callback"]

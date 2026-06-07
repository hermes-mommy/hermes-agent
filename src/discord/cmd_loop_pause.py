"""Discord /loop-pause command implementation for Guinevere (RG-014).

Pauses an active loop via LoopManager.

Usage:
    /loop-pause loop_id:str
"""

from __future__ import annotations

from typing import Any

import structlog

from .colors import WARNING
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

TITLE_OK: str = "\u23f8\ufe0f Loop Paused"
TITLE_FAIL: str = "\u274c Loop Not Found"
FOOTER_ICON: str = "\U0001f504 Loop"


async def loop_pause_callback(interaction: Any) -> None:
    """Handle a ``/loop-pause`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        loop_id = get_option_value(interaction, "loop_id")
        if not loop_id:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Parameter ``loop_id`` diperlukan, Darling.",
            )
            return

        from src.loops.manager import LoopManager

        manager = LoopManager()
        state = manager.active_loops.get(loop_id)

        ts = now_wib_str()

        if state is None:
            data = EmbedData(
                title=TITLE_FAIL,
                description=f"Loop ``{loop_id}`` tidak ditemukan.",
                color=WARNING,
                fields=(
                    EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
        else:
            state.pause()
            logger.info("loop_paused", loop_id=loop_id)

            data = EmbedData(
                title=TITLE_OK,
                description=f"Loop ``{loop_id}`` sudah di-pause.",
                color=WARNING,
                fields=(
                    EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
                    EmbedField(
                        name="Phase",
                        value=str(state.current_phase),
                        inline=True,
                    ),
                    EmbedField(name="Status", value="Paused", inline=True),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )

        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("loop_pause_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Loop pause is temporarily unavailable.",
        )


__all__ = ["loop_pause_callback"]

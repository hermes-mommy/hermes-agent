"""Discord /loop-resume command implementation for Guinevere (RG-014).

Resumes a paused loop via LoopManager.

Usage:
    /loop-resume loop_id:str
"""

from __future__ import annotations

from typing import Any

import structlog

from .colors import SUCCESS
from ._embed_helpers import (
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

TITLE_OK: str = "\u25b6\ufe0f Loop Resumed"
TITLE_FAIL: str = "\u274c Loop Not Found"
TITLE_NOT_PAUSED: str = "\u26a0\ufe0f Loop Not Paused"
FOOTER_ICON: str = "\U0001f504 Loop"


async def loop_resume_callback(interaction: Any) -> None:
    """Handle a ``/loop-resume`` interaction."""
    from .commands import is_faiz_interaction

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
        from src.loops.state_machine import LoopStatus

        manager = LoopManager()
        state = manager.active_loops.get(loop_id)

        ts = now_wib_str()

        if state is None:
            data = EmbedData(
                title=TITLE_FAIL,
                description=f"Loop ``{loop_id}`` tidak ditemukan.",
                color=SUCCESS,
                fields=(
                    EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
        elif state.status != LoopStatus.PAUSED:
            data = EmbedData(
                title=TITLE_NOT_PAUSED,
                description=(
                    f"Loop ``{loop_id}`` tidak dalam status paused "
                    f"(current: {state.status.value})."
                ),
                color=SUCCESS,
                fields=(
                    EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
                    EmbedField(
                        name="Status", value=state.status.value, inline=True
                    ),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
        else:
            state.resume()
            logger.info("loop_resumed", loop_id=loop_id)

            data = EmbedData(
                title=TITLE_OK,
                description=f"Loop ``{loop_id}`` dilanjutkan.",
                color=SUCCESS,
                fields=(
                    EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
                    EmbedField(
                        name="Phase",
                        value=str(state.current_phase),
                        inline=True,
                    ),
                    EmbedField(name="Status", value="Running", inline=True),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )

        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("loop_resume_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Loop resume is temporarily unavailable.",
        )


__all__ = ["loop_resume_callback"]

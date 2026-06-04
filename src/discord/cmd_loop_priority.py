"""Discord /loop-priority command implementation for Guinevere (RG-014).

Sets the priority for a Guinevere work loop.

Usage:
    /loop-priority loop_id:str priority:str  (choices: low, normal, high, critical)
"""

from __future__ import annotations

from typing import Any

import structlog

from .colors import PRIMARY
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

TITLE_OK: str = "\u2705 Loop Priority Updated"
TITLE_FAIL: str = "\u274c Loop Not Found"
FOOTER_ICON: str = "\U0001f504 Loop"

VALID_PRIORITIES: frozenset[str] = frozenset({"low", "normal", "high", "critical"})
PRIORITY_EMOJI: dict[str, str] = {
    "low": "\U0001f7e2",
    "normal": "\U0001f535",
    "high": "\U0001f7e0",
    "critical": "\U0001f534",
}


async def loop_priority_callback(interaction: Any) -> None:
    """Handle a ``/loop-priority`` interaction."""
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        # Support both "loop_id" and "loop" option names
        loop_id = get_option_value(interaction, "loop_id")
        if not loop_id:
            loop_id = get_option_value(interaction, "loop")
        if not loop_id:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Parameter ``loop_id`` diperlukan, Darling.",
            )
            return

        priority_raw = get_option_value(interaction, "priority")
        priority = priority_raw.lower() if priority_raw else ""

        if priority not in VALID_PRIORITIES:
            await followup_send(
                interaction,
                content=(
                    f"\u26a0\ufe0f Priority harus salah satu dari: "
                    f"low, normal, high, critical."
                ),
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
                color=PRIMARY,
                fields=(
                    EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
        else:
            # Update priority on state machine (informational field)
            if hasattr(state, "priority"):
                state.priority = priority
            logger.info("loop_priority_set", loop_id=loop_id, priority=priority)

            emoji = PRIORITY_EMOJI.get(priority, "\u2728")
            data = EmbedData(
                title=TITLE_OK,
                description=f"Priority loop ``{loop_id}`` diubah.",
                color=PRIMARY,
                fields=(
                    EmbedField(name="Loop ID", value=f"`{loop_id}`", inline=True),
                    EmbedField(
                        name="Priority",
                        value=f"{emoji} {priority.capitalize()}",
                        inline=True,
                    ),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )

        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("loop_priority_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Loop priority is temporarily unavailable.",
        )


__all__ = ["loop_priority_callback"]

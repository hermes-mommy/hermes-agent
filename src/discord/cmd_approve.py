"""Discord /approve command implementation for Guinevere (RG-012).

Approves a pending MCP tool request by tool_name.

Usage:
    /approve tool_name:str
"""

from __future__ import annotations

from typing import Any

import structlog

from .colors import SUCCESS
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

TITLE: str = "\u2705 Tool Approved"
DESC: str = "Tool sudah di-approve, Darling."
FOOTER_ICON: str = "\U0001f510 Auth"


async def approve_callback(interaction: Any) -> None:
    """Handle a ``/approve`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        tool_name = get_option_value(interaction, "tool_name")
        if not tool_name:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Parameter ``tool_name`` diperlukan, Darling.",
            )
            return

        from src.mcp.auth import approve, _pending_approvals

        if tool_name not in _pending_approvals:
            await followup_send(
                interaction,
                content=(
                    f"\u26a0\ufe0f Tidak ada pending approval untuk "
                    f"``{tool_name}``."
                ),
            )
            return

        approve(tool_name)
        logger.info("tool_approved", tool_name=tool_name)

        ts = now_wib_str()
        fields = (
            EmbedField(name="\U0001f527 Tool", value=f"`{tool_name}`", inline=True),
            EmbedField(name="\u2705 Status", value="Approved", inline=True),
        )
        data = EmbedData(
            title=TITLE,
            description=DESC,
            color=SUCCESS,
            fields=fields,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("approve_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Approve failed. Try again.",
        )


__all__ = ["approve_callback"]

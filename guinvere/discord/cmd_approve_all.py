"""Discord /approve-all command implementation for Guinevere (RG-012).

Approves all pending MCP tool requests.

Usage:
    /approve-all
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
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()

TITLE: str = "\u2705 All Tools Approved"
DESC: str = "Semua pending tools sudah di-approve, Darling."
NO_PENDING_DESC: str = "Tidak ada pending approval saat ini, Darling."
FOOTER_ICON: str = "\U0001f510 Auth"


async def approve_all_callback(interaction: Any) -> None:
    """Handle a ``/approve-all`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        from guinvere.mcp.auth import approve, _pending_approvals

        pending_names = list(_pending_approvals.keys())

        if not pending_names:
            ts = now_wib_str()
            data = EmbedData(
                title=TITLE,
                description=NO_PENDING_DESC,
                color=SUCCESS,
                fields=(),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            embed = to_discord_embed(data)
            await followup_send(interaction, embed=embed)
            return

        for name in pending_names:
            approve(name)

        logger.info("all_tools_approved", count=len(pending_names))

        ts = now_wib_str()
        name_list = "\n".join(f"\u2022 `{n}`" for n in pending_names)
        fields = (
            EmbedField(name="\U0001f4cb Approved", value=name_list, inline=False),
            EmbedField(
                name="\U0001f4ca Count", value=str(len(pending_names)), inline=True
            ),
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
        logger.exception("approve_all_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Approve-all failed. Try again.",
        )


__all__ = ["approve_all_callback"]

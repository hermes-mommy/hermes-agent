"""Discord /new command — clears Hermes conversation session for the caller.

Resets multi-turn conversation history stored in Redis DB4, giving the
user a fresh conversation context.  Faiz-only.

Usage:
    /new
"""

from __future__ import annotations

from typing import Any, Final

import structlog

from .colors import SUCCESS
from ._embed_helpers import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()

TITLE: Final[str] = "\U0001f504 Session Baru"
DESC: Final[str] = "Session conversation sudah di-reset, sayang~ \U0001f49b"
FOOTER_ICON: Final[str] = "\U0001f4ac Conversation"


async def new_session_callback(interaction: Any) -> None:
    """Handle a ``/new`` interaction — clear Hermes session for the caller."""
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        from src.hermes import get_adapter

        adapter = get_adapter()
        user_id = str(interaction.user.id)
        await adapter.clear_session(user_id)
        logger.info(
            "hermes_session_cleared",
            user_id_hash=user_id[:8],
        )

        ts = now_wib_str()
        fields: tuple[EmbedField, ...] = (
            EmbedField(name="Status", value="\u2705 History cleared", inline=True),
            EmbedField(
                name="Next message",
                value="Mulai dari awal, Darling~",
                inline=True,
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

    except Exception as exc:
        logger.exception("new_session_callback_failed", error=str(exc))
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Gagal reset session. Coba lagi ya, sayang.",
        )


__all__ = ["new_session_callback"]

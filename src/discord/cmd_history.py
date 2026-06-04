"""Discord /history command — shows recent Hermes conversation turns.

Retrieves the last N turns from the caller's Hermes session (Redis DB4)
and formats them as a Discord embed.  Faiz-only.

Usage:
    /history
"""

from __future__ import annotations

from typing import Any, Final

import structlog

from .colors import PERSONA
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

TITLE: Final[str] = "\U0001f4dc Conversation History"
DESC: Final[str] = "Ini percakapan terakhir kita, sayang~"
FOOTER_ICON: Final[str] = "\U0001f4ac Conversation"

MAX_DISPLAY_TURNS: Final[int] = 10
"""Maximum number of turns to display in the embed."""

MAX_FIELD_VALUE_LENGTH: Final[int] = 1024
"""Discord embed field value length limit."""


def _truncate(text: str, max_len: int = 200) -> str:
    """Truncate *text* to *max_len* characters with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


async def history_callback(interaction: Any) -> None:
    """Handle a ``/history`` interaction — show last conversation turns."""
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        from src.hermes import get_adapter

        adapter = get_adapter()
        user_id = str(interaction.user.id)
        history = await adapter.get_history(user_id, limit=MAX_DISPLAY_TURNS)

        if not history:
            ts = now_wib_str()
            data = EmbedData(
                title=TITLE,
                description="Belum ada percakapan, sayang. Kirim pesan dulu~ \U0001f49b",
                color=PERSONA,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            embed = to_discord_embed(data)
            await followup_send(interaction, embed=embed)
            return

        # Build embed fields from history
        fields: list[EmbedField] = []
        turn_num = 0

        for i in range(0, len(history), 2):
            user_msg = history[i] if i < len(history) else None
            assistant_msg = history[i + 1] if i + 1 < len(history) else None

            if user_msg is None:
                break

            turn_num += 1
            user_text = _truncate(str(user_msg.get("content", "")))
            assistant_text = _truncate(
                str(assistant_msg.get("content", "")) if assistant_msg else "..."
            )

            fields.append(
                EmbedField(
                    name=f"Turn {turn_num}",
                    value=f"**Faiz:** {user_text}\n**Guinevere:** {assistant_text}",
                    inline=False,
                )
            )

        # Cap at 25 fields (Discord limit)
        if len(fields) > 25:
            fields = fields[-25:]

        ts = now_wib_str()
        turn_count = len(history) // 2
        data = EmbedData(
            title=TITLE,
            description=f"{DESC}\n\n**{turn_count}** turns tercatat.",
            color=PERSONA,
            fields=tuple(fields),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception as exc:
        logger.exception("history_callback_failed", error=str(exc))
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Gagal load history. Coba lagi ya, sayang.",
        )


__all__ = ["history_callback"]

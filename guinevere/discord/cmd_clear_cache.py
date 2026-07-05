"""Discord /clear-cache command implementation for Guinevere (RG-013).

Flushes Redis DB0 (rate limits + persona state cache).

SAFETY: Requires ``confirm=True`` — no execution without explicit
operator confirmation.

Usage:
    /clear-cache confirm:bool
"""

from __future__ import annotations

from typing import Any

import redis
import structlog

from .colors import INFO_BLUE, ALERT
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

TITLE_OK: str = "\u2705 Cache Cleared"
TITLE_SKIP: str = "\u26a0\ufe0f Cache Clear Skipped"
FOOTER_ICON: str = "\U0001f6e0\ufe0f Admin"


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for DB0 (rate limits + persona cache)."""
    return redis.Redis(host="localhost", port=6380, db=0, decode_responses=False)


async def clear_cache_callback(interaction: Any) -> None:
    """Handle a ``/clear-cache`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        confirm_raw = get_option_value(interaction, "confirm")
        confirm = confirm_raw is not None and confirm_raw.lower() in (
            "true",
            "1",
            "yes",
        )

        ts = now_wib_str()

        if not confirm:
            data = EmbedData(
                title=TITLE_SKIP,
                description=(
                    "Cache clear dibatalkan. Set ``confirm=True`` "
                    "untuk melanjutkan, Darling."
                ),
                color=ALERT,
                fields=(),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            embed = to_discord_embed(data)
            await followup_send(interaction, embed=embed)
            return

        r = _get_redis_client()
        key_count = r.dbsize()
        r.flushdb()
        logger.info("cache_cleared", keys_cleared=key_count)

        fields = (
            EmbedField(name="DB", value="DB0", inline=True),
            EmbedField(
                name="Keys Cleared", value=str(key_count), inline=True
            ),
            EmbedField(name="Status", value="\u2705 Flushed", inline=True),
        )
        data = EmbedData(
            title=TITLE_OK,
            description="Redis DB0 sudah di-flush, Darling.",
            color=INFO_BLUE,
            fields=fields,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("clear_cache_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Clear cache is temporarily unavailable.",
        )


__all__ = ["clear_cache_callback"]

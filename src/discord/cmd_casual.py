"""Discord /casual command implementation for Guinevere (RG-012).

Switches interaction mode to casual in Redis.

Usage:
    /casual
"""

from __future__ import annotations

from typing import Any

import redis
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

TITLE: str = "\U0001f33f Casual Mode"
DESC: str = "Mommy santai dulu ya, Darling~"
FOOTER_ICON: str = "\U0001f9e0 Persona"

REDIS_KEY: str = "persona:interaction_mode"


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for persona state (DB0)."""
    return redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)


async def casual_callback(interaction: Any) -> None:
    """Handle a ``/casual`` interaction."""
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        r = _get_redis_client()
        r.set(REDIS_KEY, "casual")
        logger.info("casual_mode_set")

        ts = now_wib_str()
        fields = (
            EmbedField(name="Mode", value="\U0001f33f Casual", inline=True),
        )
        data = EmbedData(
            title=TITLE,
            description=DESC,
            color=PERSONA,
            fields=fields,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("casual_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Casual mode gagal di-set.",
        )


__all__ = ["casual_callback"]

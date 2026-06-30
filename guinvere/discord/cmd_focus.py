"""Discord /focus command implementation for Guinevere (RG-012).

Sets the persona focus mode (deep, normal, relaxed) in Redis.

Usage:
    /focus mode:str  (choices: deep, normal, relaxed)
"""

from __future__ import annotations

from typing import Any, cast

import redis
import structlog

from .colors import PERSONA
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

TITLE: str = "\U0001f3af Focus Mode Set"
DESC: str = "Mode fokus sudah diganti, Darling."
FOOTER_ICON: str = "\U0001f9e0 Persona"

REDIS_KEY: str = "persona:focus_mode"
VALID_MODES: frozenset[str] = frozenset({"deep", "normal", "relaxed"})
MODE_EMOJI: dict[str, str] = {
    "deep": "\U0001f525",
    "normal": "\u26a1",
    "relaxed": "\U0001f33f",
}


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for persona state (DB0)."""
    return redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)


async def focus_callback(interaction: Any) -> None:
    """Handle a ``/focus`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        mode_raw = get_option_value(interaction, "mode")
        mode = mode_raw.lower() if mode_raw else ""

        if mode not in VALID_MODES:
            await followup_send(
                interaction,
                content=(
                    f"\u26a0\ufe0f Mode harus salah satu dari: "
                    f"`deep`, `normal`, `relaxed`."
                ),
            )
            return

        r = _get_redis_client()
        r.set(REDIS_KEY, mode)
        logger.info("focus_mode_set", mode=mode)

        emoji = MODE_EMOJI.get(mode, "\u2728")
        ts = now_wib_str()
        fields = (
            EmbedField(name="Mode", value=f"{emoji} {mode.capitalize()}", inline=True),
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
        logger.exception("focus_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Focus mode gagal di-set.",
        )


__all__ = ["focus_callback"]

"""Discord /reward command implementation for Guinevere (RG-012).

Records a reward event with optional reason.

SAFETY: Must stay within Y4-Y5 boundary.  No excessive escalation.

Usage:
    /reward reason:str
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis
import structlog

from .colors import ACHIEVEMENT
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

TITLE: str = "\U0001f381 Reward Recorded"
DESC: str = "Reward sudah dicatat, Darling. Mommy senang~"
FOOTER_ICON: str = "\U0001f389 Reward"

REDIS_KEY: str = "persona:reward_log"
MAX_LOG_ENTRIES: int = 50


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for persona state (DB0)."""
    return redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)


def _log_reward(r: redis.Redis, reason: str) -> None:
    """Append a reward event to Redis log."""
    entry = {
        "reason": reason,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    raw = r.get(REDIS_KEY)
    log: list[dict[str, str]] = []
    if raw:
        try:
            log = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            log = []
    log.append(entry)
    if len(log) > MAX_LOG_ENTRIES:
        log = log[-MAX_LOG_ENTRIES:]
    r.set(REDIS_KEY, json.dumps(log))


async def reward_callback(interaction: Any) -> None:
    """Handle a ``/reward`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        reason_raw = get_option_value(interaction, "reason")
        reason = reason_raw or ""

        if not reason:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Parameter ``reason`` diperlukan, Darling.",
            )
            return

        r = _get_redis_client()
        _log_reward(r, reason)
        logger.info("reward_recorded", reason=reason[:50])

        ts = now_wib_str()
        fields = (
            EmbedField(name="\U0001f381 Reason", value=reason, inline=False),
            EmbedField(
                name="\U0001f6e1\ufe0f Boundary",
                value="Y4-Y5 safe range",
                inline=True,
            ),
        )
        data = EmbedData(
            title=TITLE,
            description=DESC,
            color=ACHIEVEMENT,
            fields=fields,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("reward_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Reward recording failed.",
        )


__all__ = ["reward_callback"]

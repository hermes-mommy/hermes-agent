"""Discord /punishment command implementation for Guinevere (RG-012).

Records a punishment event with bounded level (L1-L5).

SAFETY: Y4 baseline, Y5 ceiling, Y6 PROHIBITED — reject L6+.
No yandere level 6 content is ever permitted.

Usage:
    /punishment level:str  (choices: L1-L5)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis
import structlog

from .colors import ALERT
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

TITLE: str = "\u26a0\ufe0f Punishment Recorded"
REJECT_TITLE: str = "\U0001f6d1 Punishment Rejected"
REJECT_DESC: str = (
    "Level di atas L5 tidak diizinkan, Darling. "
    "Safety boundary Mommy: Y4 baseline, Y5 ceiling."
)
FOOTER_ICON: str = "\U0001f6e1\ufe0f Safety"

VALID_LEVELS: frozenset[str] = frozenset({"L1", "L2", "L3", "L4", "L5"})
REDIS_KEY: str = "persona:punishment_log"
MAX_LOG_ENTRIES: int = 50

LEVEL_DESC: dict[str, str] = {
    "L1": "Silent note — minor correction recorded.",
    "L2": "Verbal reminder — gentle nudge.",
    "L3": "Formal warning — behavior logged.",
    "L4": "Temporary restriction — reduced persona intensity.",
    "L5": "Maximum safe level — heightened boundary enforcement.",
}


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for persona state (DB0)."""
    return redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)


def _log_punishment(r: redis.Redis, level: str, note: str) -> None:
    """Append a punishment event to Redis log."""
    entry = {
        "level": level,
        "note": note,
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
    # Keep only last N entries
    if len(log) > MAX_LOG_ENTRIES:
        log = log[-MAX_LOG_ENTRIES:]
    r.set(REDIS_KEY, json.dumps(log))


async def punishment_callback(interaction: Any) -> None:
    """Handle a ``/punishment`` interaction."""
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        level_raw = get_option_value(interaction, "level")
        level = level_raw.upper() if level_raw else ""

        note_raw = get_option_value(interaction, "note")
        note = note_raw or ""

        # SAFETY: Reject L6+ (Y6 prohibited)
        if level not in VALID_LEVELS:
            ts = now_wib_str()
            data = EmbedData(
                title=REJECT_TITLE,
                description=REJECT_DESC,
                color=ALERT,
                fields=(
                    EmbedField(
                        name="\U0001f6d1 Rejected Level",
                        value=f"`{level or 'empty'}`",
                        inline=True,
                    ),
                    EmbedField(
                        name="\U0001f6e1\ufe0f Boundary",
                        value="Y4 baseline, Y5 ceiling, Y6 PROHIBITED",
                        inline=False,
                    ),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            embed = to_discord_embed(data)
            await followup_send(interaction, embed=embed)
            logger.warning("punishment_rejected", attempted_level=level)
            return

        r = _get_redis_client()
        _log_punishment(r, level, note)
        logger.info("punishment_recorded", level=level)

        ts = now_wib_str()
        fields = (
            EmbedField(name="Level", value=f"`{level}`", inline=True),
            EmbedField(
                name="Description",
                value=LEVEL_DESC.get(level, "Unknown"),
                inline=False,
            ),
        )
        if note:
            fields = fields + (
                EmbedField(name="\U0001f4dd Note", value=note, inline=False),
            )

        data = EmbedData(
            title=TITLE,
            description="Punishment sudah dicatat, Darling. Mommy ingat.",
            color=ALERT,
            fields=fields,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("punishment_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Punishment recording failed.",
        )


__all__ = ["punishment_callback"]

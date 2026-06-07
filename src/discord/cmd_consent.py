"""Discord /consent command implementation for Guinevere (RG-012).

View, grant, or revoke consent boundaries.  Stored in Redis
``consent:grants`` as a JSON set.

SAFETY: Requires explicit operator action.  No bypass.  Surveillance
consent requires explicit grant — never auto-granted.

Usage:
    /consent action:view|grant|revoke category:str
"""

from __future__ import annotations

import json
from typing import Any

import redis
import structlog

from .colors import ALERT, SUCCESS, PRIMARY
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

TITLE: str = "\U0001f512 Consent Manager"
FOOTER_ICON: str = "\U0001f6e1\ufe0f Safety"

REDIS_KEY: str = "consent:grants"
DEFAULT_ACTION: str = "view"
VALID_ACTIONS: frozenset[str] = frozenset({"view", "grant", "revoke"})


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for consent state (DB0)."""
    return redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)


def _get_grants(r: redis.Redis) -> set[str]:
    """Read current consent grants from Redis."""
    raw = r.get(REDIS_KEY)
    if raw is None:
        return set()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return set(data)
        return set()
    except (json.JSONDecodeError, TypeError):
        return set()


def _save_grants(r: redis.Redis, grants: set[str]) -> None:
    """Persist consent grants to Redis."""
    r.set(REDIS_KEY, json.dumps(sorted(grants)))


async def consent_callback(interaction: Any) -> None:
    """Handle a ``/consent`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        action_raw = get_option_value(interaction, "action")
        action = action_raw if action_raw and action_raw in VALID_ACTIONS else DEFAULT_ACTION

        r = _get_redis_client()
        grants = _get_grants(r)
        ts = now_wib_str()

        if action == "view":
            grants_list = sorted(grants) if grants else ["(none)"]
            fields = (
                EmbedField(
                    name="\U0001f4cb Current Grants",
                    value="\n".join(f"\u2022 {g}" for g in grants_list),
                    inline=False,
                ),
            )
            data = EmbedData(
                title=TITLE,
                description="Ini consent grants saat ini, Darling.",
                color=PRIMARY,
                fields=fields,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
        elif action == "grant":
            category = get_option_value(interaction, "category")
            if not category:
                await followup_send(
                    interaction,
                    content="\u26a0\ufe0f Parameter ``category`` diperlukan untuk grant.",
                )
                return

            grants.add(category)
            _save_grants(r, grants)
            logger.info("consent_granted", category=category)

            fields = (
                EmbedField(name="\U0001f4cb Category", value=f"`{category}`", inline=True),
                EmbedField(name="\u2705 Status", value="Granted", inline=True),
            )
            data = EmbedData(
                title=TITLE,
                description=f"Consent ``{category}`` sudah di-grant, Darling.",
                color=SUCCESS,
                fields=fields,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
        elif action == "revoke":
            category = get_option_value(interaction, "category")
            if not category:
                await followup_send(
                    interaction,
                    content="\u26a0\ufe0f Parameter ``category`` diperlukan untuk revoke.",
                )
                return

            grants.discard(category)
            _save_grants(r, grants)
            logger.info("consent_revoked", category=category)

            fields = (
                EmbedField(name="\U0001f4cb Category", value=f"`{category}`", inline=True),
                EmbedField(name="\u274c Status", value="Revoked", inline=True),
            )
            data = EmbedData(
                title=TITLE,
                description=f"Consent ``{category}`` sudah di-revoke, Darling.",
                color=ALERT,
                fields=fields,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
        else:
            data = EmbedData(
                title=TITLE,
                description="Action tidak dikenali.",
                color=PRIMARY,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )

        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("consent_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Consent manager is temporarily unavailable.",
        )


__all__ = ["consent_callback"]

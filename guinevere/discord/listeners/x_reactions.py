"""Discord ``on_reaction_add`` listener for X Poster notification handling.

Detects reactions on X Poster notification messages in the configured
#x-dashboard channel and forwards ❌⏸️▶️ to the X Poster service HTTP API
on ``127.0.0.1:8097``.
"""

from __future__ import annotations

import os
from typing import Final

import discord
import httpx
import structlog

logger = structlog.get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

_XPOSTER_API_BASE: Final[str] = "http://127.0.0.1:8097"
"""Base URL for the X Poster service HTTP API."""

_TIMEOUT: Final[float] = 10.0
"""HTTP request timeout in seconds."""

# Emojis forwarded to the X Poster service
_REACTION_CANCEL: Final[str] = "\u274c"       # ❌
_REACTION_HOLD: Final[str] = "\u23f8\ufe0f"   # ⏸️
_REACTION_RESUME: Final[str] = "\u25b6\ufe0f" # ▶️

_SUPPORTED_EMOJIS: Final[frozenset[str]] = frozenset({
    _REACTION_CANCEL,
    _REACTION_HOLD,
    _REACTION_RESUME,
})

_ACTION_MAP: Final[dict[str, str]] = {
    _REACTION_CANCEL: "cancel",
    _REACTION_HOLD: "hold",
    _REACTION_RESUME: "resume",
}


def _resolve_dashboard_channel_id() -> int:
    """Read the target #x-dashboard channel ID from env."""
    raw = os.environ.get("X_POSTER_DASHBOARD_CHANNEL_ID", "")
    if raw:
        return int(raw)
    return 0  # Fallback to 0 if not set (will never match)


def _resolve_owner_user_id() -> int:
    """Read the owner (Faiz) user ID from env."""
    raw = os.environ.get("X_POSTER_OWNER_USER_ID", "1146639950654214264")
    return int(raw)


async def _forward_reaction(
    message_id: int,
    user_id: int,
    emoji: str,
) -> bool:
    """POST the reaction to the X Poster service post-reaction endpoint.

    Returns ``True`` on success (HTTP 2xx), ``False`` otherwise.
    """
    url = f"{_XPOSTER_API_BASE}/api/post-reaction"
    payload = {
        "message_id": str(message_id),
        "user_id": str(user_id),
        "emoji": emoji,
        "action": _ACTION_MAP.get(emoji, "unknown"),
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            if response.status_code < 300:
                logger.info(
                    "x_poster.reaction_forwarded",
                    message_id=message_id,
                    emoji=emoji,
                    action=_ACTION_MAP.get(emoji),
                    status=response.status_code,
                )
                return True
            logger.warning(
                "x_poster.reaction_forward_failed",
                message_id=message_id,
                emoji=emoji,
                status=response.status_code,
                body=response.text[:300],
            )
            return False
    except httpx.RequestError as exc:
        logger.warning(
            "x_poster.reaction_forward_error",
            message_id=message_id,
            emoji=emoji,
            error=str(exc),
        )
        return False
    except Exception:
        logger.exception(
            "x_poster.reaction_forward_unexpected",
            message_id=message_id,
            emoji=emoji,
        )
        return False


async def on_x_poster_reaction_add(
    reaction: discord.Reaction,
    user: discord.User | discord.Member,
) -> None:
    """Handle ``on_reaction_add`` for X Poster notification messages.

    Forwarded to the API only when:
      - The reaction was added in the configured #x-dashboard channel.
      - The reacting user is the configured X Poster owner.
      - The emoji is one of the supported emojis.
    """
    # ── Channel guard ─────────────────────────────────────────────────
    channel = reaction.message.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        return

    target_channel_id = _resolve_dashboard_channel_id()
    if target_channel_id and channel.id != target_channel_id:
        return

    # ── Owner-only guard ──────────────────────────────────────────────
    owner_id = _resolve_owner_user_id()
    if user.id != owner_id:
        logger.debug(
            "x_poster.reaction_not_owner",
            user_id=user.id,
            channel_id=channel.id,
        )
        return

    # ── Emoji guard ───────────────────────────────────────────────────
    emoji_str = str(reaction.emoji)
    if emoji_str not in _SUPPORTED_EMOJIS:
        return

    # ── Bot self-reaction guard ───────────────────────────────────────
    if user.bot:
        return

    logger.info(
        "x_poster.reaction_detected",
        message_id=reaction.message.id,
        emoji=emoji_str,
        user_id=user.id,
        channel_id=channel.id,
    )

    _ = await _forward_reaction(
        message_id=reaction.message.id,
        user_id=user.id,
        emoji=emoji_str,
    )


__all__ = [
    "on_x_poster_reaction_add",
]
"""Discord ``on_reaction_add`` listener for Gmail draft-approval handling.

Detects reactions on Gmail notification/approval messages in the
configured #gmail channel and forwards ✅❌✏️ to the draft approval
pipeline and 📖🚫 for notification actions — all via the Gmail
service HTTP API on ``127.0.0.1:8096``.
"""

from __future__ import annotations

import os
from typing import Final

import discord
import httpx
import structlog

logger = structlog.get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

_GMAIL_API_BASE: Final[str] = "http://127.0.0.1:8096"
"""Base URL for the Gmail service HTTP API."""

_TIMEOUT: Final[float] = 10.0
"""HTTP request timeout in seconds."""

# Emojis forwarded to the draft approval pipeline
_REACTION_APPROVE: Final[str] = "\u2705"       # ✅
_REACTION_REJECT: Final[str] = "\u274c"        # ❌
_REACTION_EDIT: Final[str] = "\u270f\ufe0f"    # ✏️

# Emojis forwarded as notification actions (Redis only)
_REACTION_MARK_READ: Final[str] = "\U0001f4d6"  # 📖
_REACTION_IGNORE: Final[str] = "\U0001f6ab"     # 🚫

_SUPPORTED_EMOJIS: Final[frozenset[str]] = frozenset({
    _REACTION_APPROVE,
    _REACTION_REJECT,
    _REACTION_EDIT,
    _REACTION_MARK_READ,
    _REACTION_IGNORE,
})


def _resolve_gmail_channel_id() -> int:
    """Read the target #gmail channel ID from env.

    Falls back to the canonical Guinevere guild #gmail channel.
    """
    raw = os.environ.get("GMAIL_TARGET_CHANNEL_ID", "")
    if raw:
        return int(raw)
    return 1515062963705221130


def _resolve_owner_user_id() -> int:
    """Read the owner (Faiz) user ID from env."""
    raw = os.environ.get("GMAIL_OWNER_USER_ID", "")
    if raw:
        return int(raw)
    return 1146639950654214264


async def _forward_reaction(
    message_id: int,
    user_id: int,
    emoji: str,
) -> bool:
    """POST the reaction to the Gmail service approval-reaction endpoint.

    Returns ``True`` on success (HTTP 2xx), ``False`` otherwise.
    """
    url = f"{_GMAIL_API_BASE}/api/approval-reaction"
    payload = {
        "message_id": str(message_id),
        "user_id": str(user_id),
        "emoji": emoji,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            if response.status_code < 300:
                logger.info(
                    "gmail.reaction_forwarded",
                    message_id=message_id,
                    emoji=emoji,
                    status=response.status_code,
                )
                return True
            logger.warning(
                "gmail.reaction_forward_failed",
                message_id=message_id,
                emoji=emoji,
                status=response.status_code,
                body=response.text[:300],
            )
            return False
    except httpx.RequestError as exc:
        logger.warning(
            "gmail.reaction_forward_error",
            message_id=message_id,
            emoji=emoji,
            error=str(exc),
        )
        return False
    except Exception:
        logger.exception(
            "gmail.reaction_forward_unexpected",
            message_id=message_id,
            emoji=emoji,
        )
        return False


async def on_gmail_reaction_add(
    reaction: discord.Reaction,
    user: discord.User | discord.Member,
) -> None:
    # pylint: disable=too-many-return-statements
    """Handle ``on_reaction_add`` for Gmail notification messages.

    Forwarded to the API only when:
      - The reaction was added in the configured #gmail channel.
      - The reacting user is the configured Gmail owner.
      - The emoji is one of the supported emojis.
    """
    # ── Channel guard ─────────────────────────────────────────────────
    channel = reaction.message.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        return

    target_channel_id = _resolve_gmail_channel_id()
    if channel.id != target_channel_id:
        return

    # ── Owner-only guard ──────────────────────────────────────────────
    owner_id = _resolve_owner_user_id()
    if user.id != owner_id:
        logger.debug(
            "gmail.reaction_not_owner",
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
        "gmail.reaction_detected",
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
    "on_gmail_reaction_add",
]
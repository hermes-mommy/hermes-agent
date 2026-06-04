"""Discord /memory-forget command implementation for Guinevere (RG-010).

Marks a memory as DNR (Do Not Recall) by UUID.  Uses the async session
factory from bot to update the ``memories`` table.

Usage:
    /memory-forget memory_id:str
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from .colors import PRIMARY
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


# ── Constants ───────────────────────────────────────────────────────────────

FORGET_TITLE: str = "\U0001f9e0 Memory Forget"
FORGET_OK_DESC: str = "Memory sudah ditandai DNR, Darling. Tidak akan di-recall lagi."
FORGET_FAIL_DESC: str = "Memory ID tidak ditemukan atau gagal diproses."
FOOTER_ICON: str = "\U0001f9e0 Memory"


@dataclass(frozen=True)
class ForgetResult:
    """Result of a memory-forget operation."""

    memory_id: str
    success: bool
    error: str | None = None


# ── Database Operation ──────────────────────────────────────────────────────


async def _mark_memory_dnr(session_factory: Any, memory_id: str) -> ForgetResult:
    """Mark a memory row as DNR in the database.

    Args:
        session_factory: Async SQLAlchemy session factory.
        memory_id: UUID of the memory to mark.

    Returns:
        ForgetResult indicating success or failure.
    """
    try:
        from sqlalchemy import text

        async with session_factory() as session:
            result = await session.execute(
                text(
                    "UPDATE memories SET dnr = true, updated_at = NOW() "
                    "WHERE id = :mid RETURNING id"
                ),
                {"mid": memory_id},
            )
            row = result.fetchone()
            await session.commit()

            if row is not None:
                logger.info("memory_forget_success", memory_id=memory_id)
                return ForgetResult(memory_id=memory_id, success=True)
            else:
                logger.warning("memory_forget_not_found", memory_id=memory_id)
                return ForgetResult(
                    memory_id=memory_id, success=False, error="Memory ID not found."
                )
    except Exception as exc:
        logger.exception("memory_forget_db_error", memory_id=memory_id)
        return ForgetResult(memory_id=memory_id, success=False, error=str(exc))


# ── Embed Builder ───────────────────────────────────────────────────────────


def _build_embed_data(result: ForgetResult) -> EmbedData:
    """Build embed data from a forget result."""
    ts = now_wib_str()

    if result.success:
        fields = (
            EmbedField(name="\U0001f4cb Memory ID", value=f"`{result.memory_id}`", inline=True),
            EmbedField(name="\u2705 Status", value="Marked DNR", inline=True),
            EmbedField(name="\U0001f552 Timestamp", value=ts, inline=False),
        )
        return EmbedData(
            title=FORGET_TITLE,
            description=FORGET_OK_DESC,
            color=PRIMARY,
            fields=fields,
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields = (
        EmbedField(name="\U0001f4cb Memory ID", value=f"`{result.memory_id}`", inline=True),
        EmbedField(name="\u274c Error", value=result.error or "Unknown error", inline=False),
    )
    return EmbedData(
        title=FORGET_TITLE,
        description=FORGET_FAIL_DESC,
        color=PRIMARY,
        fields=fields,
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


# ── Callback ────────────────────────────────────────────────────────────────


async def memory_forget_callback(interaction: Any) -> None:
    """Handle a ``/memory-forget`` interaction.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        memory_id = get_option_value(interaction, "memory_id")
        if not memory_id:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Parameter ``memory_id`` diperlukan, Darling.",
            )
            return

        # Get session factory from bot instance
        bot = getattr(interaction, "client", None)
        if bot is None or not hasattr(bot, "get_session_factory"):
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Database session not available.",
            )
            return

        session_factory = bot.get_session_factory()
        if session_factory is None:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f Database URL not configured.",
            )
            return

        result = await _mark_memory_dnr(session_factory, memory_id)
        data = _build_embed_data(result)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("memory_forget_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Memory forget is temporarily unavailable.",
        )


__all__ = ["memory_forget_callback"]

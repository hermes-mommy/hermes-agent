"""Hermes command plugin — /memory-forget.

Migrated from src/discord/cmd_memory_forget.py for Phase 2 Discord migration.
Marks a memory as DNR (Do Not Recall) by UUID. Uses the async session
factory to update the ``memories`` table directly (this is the ONLY memory
command that touches PostgreSQL directly — only for DNR flagging).

Original: 182 lines | Migrated: preserves DNR marking logic.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))
FORGET_TITLE: str = "\U0001f9e0 Memory Forget"


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``2026-06-01 15:30 WIB``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def _get_arg(ctx: Any, name: str) -> str | None:
    """Extract argument from Hermes context (dict-style args)."""
    args = getattr(ctx, "args", None)
    if args is None:
        return None
    if isinstance(args, dict):
        val = args.get(name)
        return str(val) if val else None
    return None


def _render_forget_result(
    memory_id: str,
    success: bool,
    error: str | None,
    now: datetime,
) -> str:
    """Render memory-forget result as markdown."""
    ts_str = _format_wib_timestamp(now)

    if success:
        return (
            f"## {FORGET_TITLE}\n\n"
            "Memory sudah ditandai DNR, Darling. Tidak akan di-recall lagi.\n\n"
            f"*{ts_str} WIB*\n\n"
            f"\U0001f4cb **Memory ID:** `{memory_id}`\n"
            "\u2705 **Status:** Marked DNR"
        )

    return (
        f"## {FORGET_TITLE}\n\n"
        "Memory ID tidak ditemukan atau gagal diproses.\n\n"
        f"*{ts_str} WIB*\n\n"
        f"\U0001f4cb **Memory ID:** `{memory_id}`\n"
        f"\u274c **Error:** {error or 'Unknown error'}"
    )


def register(ctx: Any) -> None:
    """Register /memory-forget with Hermes."""

    @ctx.register_command(
        "memory-forget",
        description="Request deletion of a Guinevere memory item.",
    )
    async def handle(context: Any) -> str:
        try:
            memory_id = _get_arg(context, "memory_id")
            if not memory_id:
                return (
                    "\u26a0\ufe0f Parameter `memory_id` diperlukan, "
                    "Darling."
                )

            session_factory = getattr(ctx, "session_factory", None)
            if session_factory is None:
                return (
                    "\u26a0\ufe0f Database session not available."
                )

            try:
                from sqlalchemy import text

                async with session_factory() as session:
                    result = await session.execute(
                        text(
                            "UPDATE memories SET dnr = true, "
                            "updated_at = NOW() "
                            "WHERE id = :mid RETURNING id"
                        ),
                        {"mid": memory_id},
                    )
                    row = result.fetchone()
                    await session.commit()

                    if row is not None:
                        logger.info(
                            "memory_forget_success",
                            extra={"memory_id": memory_id},
                        )
                        now = datetime.now(tz=timezone.utc)
                        return _render_forget_result(
                            memory_id=memory_id,
                            success=True,
                            error=None,
                            now=now,
                        )
                    else:
                        logger.warning(
                            "memory_forget_not_found",
                            extra={"memory_id": memory_id},
                        )
                        now = datetime.now(tz=timezone.utc)
                        return _render_forget_result(
                            memory_id=memory_id,
                            success=False,
                            error="Memory ID not found.",
                            now=now,
                        )
            except Exception as db_exc:
                logger.exception(
                    "memory_forget_db_error",
                    extra={
                        "memory_id": memory_id,
                        "error": str(db_exc),
                    },
                )
                now = datetime.now(tz=timezone.utc)
                return _render_forget_result(
                    memory_id=memory_id,
                    success=False,
                    error=str(db_exc),
                    now=now,
                )

        except Exception as exc:
            logger.exception(
                "memory_forget_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Memory forget is temporarily unavailable."
            )
"""Hermes command plugin — /loop-pause.

Migrated from src/discord/cmd_loop_pause.py for Phase 2 Discord migration.
Pauses an active loop via LoopManager state machine.

Original: 103 lines | Migrated: preserves LoopManager.pause() logic.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))


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


def register(ctx: Any) -> None:
    """Register /loop-pause with Hermes."""

    @ctx.register_command(
        "loop-pause",
        description="Pause the active Guinevere work loop.",
    )
    async def handle(context: Any) -> str:
        try:
            loop_id = _get_arg(context, "loop_id")
            if not loop_id:
                return (
                    "\u26a0\ufe0f Parameter `loop_id` diperlukan, "
                    "Darling."
                )

            from guinvere.loops.manager import LoopManager

            manager = LoopManager()
            state = manager.active_loops.get(loop_id)

            ts_str = _format_wib_timestamp(
                datetime.now(tz=timezone.utc)
            )

            if state is None:
                return (
                    f"## \u274c Loop Not Found\n\n"
                    f"Loop `{loop_id}` tidak ditemukan.\n\n"
                    f"*{ts_str} WIB*\n\n"
                    f"**Loop ID:** `{loop_id}`"
                )

            state.pause()
            logger.info("loop_paused", extra={"loop_id": loop_id})

            return (
                "## \u23f8\ufe0f Loop Paused\n\n"
                f"Loop `{loop_id}` sudah di-pause.\n\n"
                f"*{ts_str} WIB*\n\n"
                f"**Loop ID:** `{loop_id}`\n"
                f"**Phase:** `{state.current_phase}`\n"
                f"**Status:** `Paused`"
            )

        except Exception as exc:
            logger.exception(
                "loop_pause_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Loop pause is temporarily unavailable."
            )
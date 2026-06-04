"""Hermes command plugin — /loop-resume.

Migrated from src/discord/cmd_loop_resume.py for Phase 2 Discord migration.
Resumes a paused loop via LoopManager state machine with status validation.

Original: 122 lines | Migrated: preserves LoopManager.resume() + PAUSED check.
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
    """Register /loop-resume with Hermes."""

    @ctx.register_command(
        "loop-resume",
        description="Resume a paused Guinevere work loop.",
    )
    async def handle(context: Any) -> str:
        try:
            loop_id = _get_arg(context, "loop_id")
            if not loop_id:
                return (
                    "\u26a0\ufe0f Parameter `loop_id` diperlukan, "
                    "Darling."
                )

            from src.loops.manager import LoopManager
            from src.loops.state_machine import LoopStatus

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

            if state.status != LoopStatus.PAUSED:
                return (
                    "## \u26a0\ufe0f Loop Not Paused\n\n"
                    f"Loop `{loop_id}` tidak dalam status paused "
                    f"(current: `{state.status.value}`).\n\n"
                    f"*{ts_str} WIB*\n\n"
                    f"**Loop ID:** `{loop_id}`\n"
                    f"**Status:** `{state.status.value}`"
                )

            state.resume()
            logger.info("loop_resumed", extra={"loop_id": loop_id})

            return (
                "## \u25b6\ufe0f Loop Resumed\n\n"
                f"Loop `{loop_id}` dilanjutkan.\n\n"
                f"*{ts_str} WIB*\n\n"
                f"**Loop ID:** `{loop_id}`\n"
                f"**Phase:** `{state.current_phase}`\n"
                f"**Status:** `Running`"
            )

        except Exception as exc:
            logger.exception(
                "loop_resume_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Loop resume is temporarily unavailable."
            )
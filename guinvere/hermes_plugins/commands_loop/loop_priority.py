"""Hermes command plugin — /loop-priority.

Migrated from src/discord/cmd_loop_priority.py for Phase 2 Discord migration.
Sets the priority for a Guinevere work loop via LoopManager. Preserves
priority validation (low/normal/high/critical) with emoji display.

Original: 129 lines | Migrated: preserves priority update logic.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))
VALID_PRIORITIES: frozenset[str] = frozenset(
    {"low", "normal", "high", "critical"}
)
PRIORITY_EMOJI: dict[str, str] = {
    "low": "\U0001f7e2",
    "normal": "\U0001f535",
    "high": "\U0001f7e0",
    "critical": "\U0001f534",
}


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
    """Register /loop-priority with Hermes."""

    @ctx.register_command(
        "loop-priority",
        description="Set the priority for a Guinevere work loop.",
    )
    async def handle(context: Any) -> str:
        try:
            # Support both "loop_id" and "loop" option names
            loop_id = _get_arg(context, "loop_id")
            if not loop_id:
                loop_id = _get_arg(context, "loop")
            if not loop_id:
                return (
                    "\u26a0\ufe0f Parameter `loop_id` diperlukan, "
                    "Darling."
                )

            priority_raw = _get_arg(context, "priority")
            priority = priority_raw.lower() if priority_raw else ""

            if priority not in VALID_PRIORITIES:
                return (
                    "\u26a0\ufe0f Priority harus salah satu dari: "
                    "low, normal, high, critical."
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

            if hasattr(state, "priority"):
                setattr(state, "priority", priority)
            logger.info(
                "loop_priority_set",
                extra={"loop_id": loop_id, "priority": priority},
            )

            emoji = PRIORITY_EMOJI.get(priority, "\u2728")
            return (
                "## \u2705 Loop Priority Updated\n\n"
                f"Priority loop `{loop_id}` diubah.\n\n"
                f"*{ts_str} WIB*\n\n"
                f"**Loop ID:** `{loop_id}`\n"
                f"**Priority:** {emoji} {priority.capitalize()}"
            )

        except Exception as exc:
            logger.exception(
                "loop_priority_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Loop priority is temporarily unavailable."
            )
"""Hermes command plugin — /loops.

Migrated from src/discord/cmd_loops.py for Phase 2 Discord migration.
Lists current and recent Guinevere work loops via LoopManager.list_loops().

Original: 114 lines | Migrated: preserves LoopManager.list_loops() logic.
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


async def _get_all_loops() -> list[dict[str, Any]]:
    """Get all active loops from LoopManager."""
    try:
        from guinvere.loops.manager import LoopManager

        manager = LoopManager()
        return await manager.list_loops()
    except Exception:
        logger.exception("loops_list_failed")
        return []


def _render_loops(loops: list[dict[str, Any]], now: datetime) -> str:
    """Render loop list as markdown."""
    ts_str = _format_wib_timestamp(now)

    if not loops:
        return (
            "## \U0001f504 Active Loops\n\n"
            "Tidak ada loop aktif saat ini, Darling.\n\n"
            f"*{ts_str} WIB*"
        )

    lines: list[str] = [
        "## \U0001f504 Active Loops",
        "",
        f"{len(loops)} loop(s) aktif.",
        "",
        f"*{ts_str} WIB*",
        "",
    ]

    for loop in loops[:10]:
        loop_id = loop.get("loop_id", "unknown")
        status = loop.get("status", "unknown")
        phase = loop.get("current_phase", "unknown")
        task = loop.get("task", "")[:50] or "(no task)"
        lines.append(f"### `{loop_id}`")
        lines.append(f"- **Status:** `{status}`")
        lines.append(f"- **Phase:** `{phase}`")
        lines.append(f"- **Task:** {task}")
        lines.append("")

    return "\n".join(lines)


def register(ctx: Any) -> None:
    """Register /loops with Hermes."""

    @ctx.register_command(
        "loops",
        description="List current and recent Guinevere work loops.",
    )
    async def handle(context: Any) -> str:
        try:
            loops = await _get_all_loops()
            now = datetime.now(tz=timezone.utc)
            return _render_loops(loops, now)

        except Exception as exc:
            logger.exception(
                "loops_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Loops list is temporarily unavailable."
            )
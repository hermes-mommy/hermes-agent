"""Hermes command plugin — /history.

Migrated from src/discord/cmd_history.py for Phase 2 Discord migration.
Shows recent Hermes conversation turns from Redis DB4.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Final



logger = logging.getLogger(__name__)

# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))

# ── Constants ───────────────────────────────────────────────────────────────

TITLE: Final[str] = "\U0001f4dc Conversation History"
DESC: Final[str] = "Ini percakapan terakhir kita, sayang~"
FOOTER_ICON: Final[str] = "\U0001f4ac Conversation"
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"

MAX_DISPLAY_TURNS: Final[int] = 10


# ── Helpers ─────────────────────────────────────────────────────────────────


def _truncate(text: str, max_len: int = 200) -> str:
    """Truncate *text* to *max_len* characters with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


# ── Plugin Registration ─────────────────────────────────────────────────────


def register(ctx: Any) -> None:
    """Register /history command with Hermes plugin context."""

    @ctx.register_command(
        "history",
        description="Show recent conversation turns with Mommy.",
    )
    async def handle(context: Any) -> str:
        """Handle /history invocation — show last conversation turns."""
        try:
            from src.hermes.adapter import get_adapter

            adapter = get_adapter()
            user_id = str(getattr(context, "user_id", ""))
            history = await adapter.get_history(user_id, limit=MAX_DISPLAY_TURNS)
            ref = datetime.now(tz=timezone.utc)
            ts_str = _format_wib_timestamp(ref)

            if not history:
                lines: list[str] = [
                    f"# {TITLE}",
                    "",
                    "Belum ada percakapan, sayang. Kirim pesan dulu~ \U0001f49b",
                    "",
                    f"\u2014 {FOOTER_TEXT} \u2022 {ts_str} \u2022 {FOOTER_ICON}",
                ]
                return "\n".join(lines)

            # Build turn entries
            turn_lines: list[str] = [
                f"# {TITLE}",
                "",
                f"{DESC}",
                "",
            ]

            turn_num = 0
            for i in range(0, len(history), 2):
                user_msg = history[i] if i < len(history) else None
                assistant_msg = history[i + 1] if i + 1 < len(history) else None

                if user_msg is None:
                    break

                turn_num += 1
                user_text = _truncate(str(user_msg.get("content", "")))
                assistant_text = _truncate(
                    str(assistant_msg.get("content", "")) if assistant_msg else "..."
                )

                turn_lines.append(f"### Turn {turn_num}")
                turn_lines.append(f"**Faiz:** {user_text}")
                turn_lines.append(f"**Guinevere:** {assistant_text}")
                turn_lines.append("")

            turn_count = len(history) // 2
            footer = (
                f"\u2014 {FOOTER_TEXT} \u2022 {ts_str} \u2022 "
                f"{FOOTER_ICON} \u2022 {turn_count} turns"
            )
            turn_lines.append(footer)
            return "\n".join(turn_lines)

        except Exception as exc:
            logger.exception(
                "history_command_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return (
                "\u26a0\ufe0f Gagal load history. "
                "Coba lagi ya, sayang. \U0001f49b"
            )
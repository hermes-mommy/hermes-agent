"""Hermes command plugin — /new.

Migrated from guinevere/discord/cmd_new_session.py for Phase 2 Discord migration.
Clears Hermes conversation session for the caller via Redis DB4.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Final

logger = logging.getLogger(__name__)

# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final[timezone] = timezone(timedelta(hours=7))

# ── Constants ───────────────────────────────────────────────────────────────

TITLE: Final[str] = "\U0001f504 Session Baru"
DESC: Final[str] = "Session conversation sudah di-reset, sayang~ \U0001f49b"
FOOTER_ICON: Final[str] = "\U0001f4ac Conversation"
FOOTER_TEXT: Final[str] = "Guinevere de Baroque"


# ── Helpers ─────────────────────────────────────────────────────────────────


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


# ── Plugin Registration ─────────────────────────────────────────────────────


def register(ctx: Any) -> None:
    """Register /new command with Hermes plugin context."""

    @ctx.register_command(
        "new",
        description="Reset conversation history and start fresh.",
    )
    async def handle(context: Any) -> str:
        """Handle /new invocation — clear Hermes session for the caller."""
        try:
            from guinevere.hermes.adapter import get_adapter

            adapter = get_adapter()
            user_id = str(getattr(context, "user_id", ""))
            await adapter.clear_session(user_id)
            logger.info(
                "hermes_session_cleared",
                extra={"user_id_prefix": user_id[:8] if user_id else "unknown"},
            )

            ref = datetime.now(tz=timezone.utc)
            ts_str = _format_wib_timestamp(ref)

            lines: list[str] = [
                f"# {TITLE}",
                "",
                DESC,
                "",
                "| Field | Value |",
                "|---|---|",
                "| Status | \u2705 History cleared |",
                "| Next message | Mulai dari awal, Darling~ |",
                "",
                f"\u2014 {FOOTER_TEXT} \u2022 {ts_str} \u2022 {FOOTER_ICON}",
            ]
            return "\n".join(lines)

        except Exception as exc:
            logger.exception(
                "new_session_command_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return (
                "\u26a0\ufe0f Gagal reset session. "
                "Coba lagi ya, sayang. \U0001f49b"
            )
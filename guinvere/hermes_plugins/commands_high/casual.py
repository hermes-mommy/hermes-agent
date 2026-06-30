"""Hermes command plugin — /casual.

Migrated from guinvere/discord/cmd_casual.py for Phase 2 Discord migration.
Switches interaction mode to casual in Redis DB0.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Final

import redis

logger = logging.getLogger(__name__)

# ── Timezone ────────────────────────────────────────────────────────────────

WIB: Final = timezone(timedelta(hours=7))

# ── Constants ───────────────────────────────────────────────────────────────

TITLE: str = "\U0001f33f Casual Mode"
DESC: str = "Mommy santai dulu ya, Darling~"
FOOTER_ICON: str = "\U0001f9e0 Persona"
FOOTER_TEXT: str = "Guinevere de Baroque"
REDIS_KEY: str = "persona:interaction_mode"

# ── Redis ───────────────────────────────────────────────────────────────────


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for persona state (DB0)."""
    return redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _format_wib_timestamp(dt: datetime) -> str:
    """Format a datetime as ``"2026-06-01 15:30 WIB"``."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


# ── Plugin Registration ─────────────────────────────────────────────────────


def register(ctx: Any) -> None:
    """Register /casual command with Hermes plugin context."""

    @ctx.register_command(
        "casual",
        description="Switch Guinevere into lighter casual mode.",
    )
    async def handle(context: Any) -> str:
        """Handle /casual invocation."""
        try:
            r = _get_redis_client()
            r.set(REDIS_KEY, "casual")
            logger.info("casual_mode_set")

            ref = datetime.now(tz=timezone.utc)
            ts_str = _format_wib_timestamp(ref)

            lines: list[str] = [
                f"# {TITLE}",
                "",
                DESC,
                "",
                "| Field | Value |",
                "|---|---|",
                "| Mode | \U0001f33f Casual |",
                "",
                f"\u2014 {FOOTER_TEXT} \u2022 {ts_str} \u2022 {FOOTER_ICON}",
            ]
            return "\n".join(lines)

        except Exception as exc:
            logger.exception(
                "casual_command_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return (
                "\u26a0\ufe0f Casual mode gagal di-set. "
                "Coba lagi ya, Darling."
            )
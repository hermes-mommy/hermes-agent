"""Hermes command plugin — /clear-cache.

Migrated from src/discord/cmd_clear_cache.py for Phase 2 Discord migration.
Flushes Redis DB0 (rate limits + persona state cache).

SAFETY: Requires confirm=True — no execution without explicit
operator confirmation.

Original: 110 lines | Migrated: preserves Redis DB0 flush + confirm gate.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import redis

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


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for DB0 (rate limits + persona cache)."""
    return redis.Redis(
        host="localhost", port=6380, db=0, decode_responses=False
    )


def register(ctx: Any) -> None:
    """Register /clear-cache with Hermes."""

    @ctx.register_command(
        "clear-cache",
        description="Request a guarded cache clear operation.",
    )
    async def handle(context: Any) -> str:
        try:
            confirm_raw = _get_arg(context, "confirm")
            confirm = confirm_raw is not None and confirm_raw.lower() in (
                "true",
                "1",
                "yes",
            )

            ts_str = _format_wib_timestamp(
                datetime.now(tz=timezone.utc)
            )

            if not confirm:
                return (
                    "## \u26a0\ufe0f Cache Clear Skipped\n\n"
                    f"*{ts_str} WIB*\n\n"
                    "Cache clear dibatalkan. Set `confirm=True` "
                    "untuk melanjutkan, Darling."
                )

            r = _get_redis_client()
            key_count = r.dbsize()
            r.flushdb()
            logger.info(
                "cache_cleared", extra={"keys_cleared": key_count}
            )

            return (
                "## \u2705 Cache Cleared\n\n"
                f"*{ts_str} WIB*\n\n"
                "Redis DB0 sudah di-flush, Darling.\n\n"
                f"**DB:** DB0\n"
                f"**Keys Cleared:** {key_count}\n"
                f"**Status:** \u2705 Flushed"
            )

        except Exception as exc:
            logger.exception(
                "clear_cache_failed",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Clear cache is temporarily unavailable."
            )
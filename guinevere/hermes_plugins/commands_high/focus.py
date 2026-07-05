"""Hermes command plugin — /focus.

Migrated from guinevere/discord/cmd_focus.py for Phase 2 Discord migration.
Sets the persona focus mode (deep, normal, relaxed) in Redis DB0.
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

TITLE: str = "\U0001f3af Focus Mode Set"
DESC: str = "Mode fokus sudah diganti, Darling."
FOOTER_ICON: str = "\U0001f9e0 Persona"
FOOTER_TEXT: str = "Guinevere de Baroque"
REDIS_KEY: str = "persona:focus_mode"
VALID_MODES: frozenset[str] = frozenset({"deep", "normal", "relaxed"})
MODE_EMOJI: dict[str, str] = {
    "deep": "\U0001f525",
    "normal": "\u26a1",
    "relaxed": "\U0001f33f",
}


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
    """Register /focus command with Hermes plugin context."""

    @ctx.register_command(
        "focus",
        description="Switch Guinevere into focused engineering mode.",
    )
    async def handle(context: Any) -> str:
        """Handle /focus invocation.

        Expects context.options to contain a "mode" key (Hermes-style option passing).
        """
        try:
            # Extract mode from Hermes context options
            options: dict[str, str] = getattr(context, "options", {}) or {}
            mode_raw = options.get("mode", "")
            mode = mode_raw.lower() if mode_raw else ""

            if mode not in VALID_MODES:
                return (
                    "\u26a0\ufe0f Mode harus salah satu dari: "
                    "`deep`, `normal`, `relaxed`."
                )

            r = _get_redis_client()
            r.set(REDIS_KEY, mode)
            logger.info("focus_mode_set", extra={"mode": mode})

            emoji = MODE_EMOJI.get(mode, "\u2728")
            ref = datetime.now(tz=timezone.utc)
            ts_str = _format_wib_timestamp(ref)

            lines: list[str] = [
                f"# {TITLE}",
                "",
                DESC,
                "",
                "| Field | Value |",
                "|---|---|",
                f"| Mode | {emoji} {mode.capitalize()} |",
                "",
                f"\u2014 {FOOTER_TEXT} \u2022 {ts_str} \u2022 {FOOTER_ICON}",
            ]
            return "\n".join(lines)

        except Exception as exc:
            logger.exception(
                "focus_command_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return (
                "\u26a0\ufe0f Focus mode gagal di-set. "
                "Coba lagi ya, Darling."
            )
"""Hermes command plugin — /loop-start.

Migrated from guinevere/discord/cmd_loop_start.py for Phase 2 Discord migration.
Starts a supervised Guinevere work loop via the internal API (localhost:8000)
and returns a markdown confirmation.

Original: 462 lines | Migrated: preserves HTTP API call + error handling.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))
API_BASE_URL: str = "http://localhost:8000"
LOOPS_ENDPOINT: str = "/api/v1/loops"


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


def _render_start_result(
    loop_id: str,
    goal: str,
    status: str,
    priority: str,
    now: datetime,
) -> str:
    """Render loop-start confirmation as markdown."""
    ts_str = _format_wib_timestamp(now)
    loop_id_short = loop_id[:8]

    return (
        "## \U0001f504 Loop Started\n\n"
        "Mommy mulai kerja, Darling. Tunggu hasilnya ya~\n\n"
        f"*{ts_str} WIB*\n\n"
        f"**Goal:** {goal}\n"
        f"**Loop ID:** `{loop_id_short}`\n"
        f"**Status:** `{status}`\n"
        f"**Priority:** `{priority}`"
    )


def register(ctx: Any) -> None:
    """Register /loop-start with Hermes."""

    @ctx.register_command(
        "loop-start",
        description="Start a supervised Guinevere work loop.",
    )
    async def handle(context: Any) -> str:
        try:
            goal = _get_arg(context, "goal")
            if not goal:
                return "\u26a0\ufe0f Goal tidak boleh kosong, Darling."

            api_key = os.environ.get("GUINEVERE_API_KEY")
            if not api_key:
                return (
                    "\u26a0\ufe0f GUINEVERE_API_KEY is not set. "
                    "Ask Faiz to configure it."
                )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_BASE_URL}{LOOPS_ENDPOINT}",
                    json={"task": goal, "priority": "normal"},
                    headers={"X-Guinevere-API-Key": api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                result = response.json()

            loop_id = str(
                result.get("loop_id", result.get("id", "unknown"))
            )
            status = str(result.get("status", "running"))
            priority = str(result.get("priority", "normal"))

            now = datetime.now(tz=timezone.utc)
            return _render_start_result(
                loop_id=loop_id,
                goal=goal,
                status=status,
                priority=priority,
                now=now,
            )

        except httpx.HTTPStatusError as exc:
            logger.exception(
                "loop_start_http_error",
                extra={"status": exc.response.status_code},
            )
            return (
                f"\u26a0\ufe0f API returned {exc.response.status_code}. "
                "Loop gagal dimulai, Darling."
            )
        except httpx.RequestError as exc:
            logger.exception(
                "loop_start_request_error",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Tidak bisa menghubungi API internal. "
                "Coba lagi nanti ya, Darling."
            )
        except Exception as exc:
            logger.exception(
                "loop_start_unexpected_error",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Terjadi kesalahan tak terduga. "
                "Mommy log untuk investigasi."
            )
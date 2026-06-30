"""Hermes command plugin — /loop-stop.

Migrated from guinvere/discord/cmd_loop_stop.py for Phase 2 Discord migration.
Stops one or all active Guinevere work loops via the internal API
(localhost:8000) and returns a markdown confirmation.

Original: 532 lines | Migrated: preserves cancel + list-active API logic.
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


def _render_stop_result(
    loop_id: str,
    phase: str,
    status: str,
    count: int,
    now: datetime,
) -> str:
    """Render loop-stop confirmation as markdown."""
    ts_str = _format_wib_timestamp(now)
    loop_id_short = loop_id[:8]
    count_note = (
        f"\n\n**Note:** Semua {count} loop aktif dihentikan."
        if count > 1
        else ""
    )

    return (
        "## \u23f9\ufe0f Loop Stopped\n\n"
        "Mommy berhenti, Darling. Kalau mau lanjut lagi, bilang aja.\n\n"
        f"*{ts_str} WIB*\n\n"
        f"**Loop ID:** `{loop_id_short}`\n"
        f"**Previous Phase:** `{phase}`\n"
        f"**Status:** `{status}`"
        f"{count_note}"
    )


async def _cancel_loop(
    client: httpx.AsyncClient,
    api_key: str,
    loop_id: str,
) -> dict[str, object]:
    """Cancel a single loop via the API."""
    response = await client.post(
        f"{API_BASE_URL}{LOOPS_ENDPOINT}/{loop_id}/cancel",
        headers={"X-Guinevere-API-Key": api_key},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


async def _list_active_loops(
    client: httpx.AsyncClient,
    api_key: str,
) -> list[dict[str, object]]:
    """List all active (running/queued) loops via the API."""
    response = await client.get(
        f"{API_BASE_URL}{LOOPS_ENDPOINT}",
        headers={"X-Guinevere-API-Key": api_key},
        timeout=10.0,
    )
    response.raise_for_status()
    body: dict[str, object] = response.json()
    loops_data: object = body.get("loops", [])
    if not isinstance(loops_data, list):
        return []
    return [
        loop
        for loop in loops_data
        if isinstance(loop, dict)
        and loop.get("status") in ("running", "queued")
    ]


def register(ctx: Any) -> None:
    """Register /loop-stop with Hermes."""

    @ctx.register_command(
        "loop-stop",
        description="Stop the active Guinevere work loop safely.",
    )
    async def handle(context: Any) -> str:
        try:
            loop_id = _get_arg(context, "loop_id")
            api_key = os.environ.get("GUINEVERE_API_KEY")
            if not api_key:
                return (
                    "\u26a0\ufe0f GUINEVERE_API_KEY is not set. "
                    "Ask Faiz to configure it."
                )

            async with httpx.AsyncClient() as client:
                cancelled: list[dict[str, object]] = []

                if loop_id:
                    result = await _cancel_loop(client, api_key, loop_id)
                    cancelled.append(result)
                else:
                    active_loops = await _list_active_loops(
                        client, api_key
                    )
                    if not active_loops:
                        return (
                            "Tidak ada loop yang sedang aktif, Darling."
                        )
                    for active in active_loops:
                        lid = str(
                            active.get(
                                "loop_id", active.get("id", "unknown")
                            )
                        )
                        result = await _cancel_loop(client, api_key, lid)
                        cancelled.append(result)

            if not cancelled:
                return (
                    "Loop berhasil dihentikan, tapi datanya kosong. "
                    "Cek nanti ya."
                )

            first = cancelled[0]
            lid = str(first.get("loop_id", first.get("id", "unknown")))
            phase = str(first.get("phase", "unknown"))
            status = str(first.get("status", "cancelled"))

            now = datetime.now(tz=timezone.utc)
            return _render_stop_result(
                loop_id=lid,
                phase=phase,
                status=status,
                count=len(cancelled),
                now=now,
            )

        except httpx.HTTPStatusError as exc:
            logger.exception(
                "loop_stop_http_error",
                extra={"status": exc.response.status_code},
            )
            return (
                f"\u26a0\ufe0f API returned {exc.response.status_code}. "
                "Loop gagal dihentikan, Darling."
            )
        except httpx.RequestError as exc:
            logger.exception(
                "loop_stop_request_error",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Tidak bisa menghubungi API internal. "
                "Coba lagi nanti ya, Darling."
            )
        except Exception as exc:
            logger.exception(
                "loop_stop_unexpected_error",
                extra={"error": str(exc)},
            )
            return (
                "\u26a0\ufe0f Terjadi kesalahan tak terduga. "
                "Mommy log untuk investigasi."
            )
"""Discord slash commands for X Auto Poster integration.

Commands that call the X Poster service API via HTTP:

- ``/x-list [state=pending]`` — show queued posts
- ``/x-status`` — service status + queue depth + session health
- ``/x-cancel <post_id>`` — cancel a pending post
- ``/x-hold <post_id>`` — hold a pending post
- ``/x-resume <post_id>`` — resume a held post
- ``/x-retry-failed`` — retry all failed posts
- ``/x-dryrun <post_id>`` — test post without publishing

All commands are Faiz-only. The X Poster service runs as a separate systemd
process and exposes these operations on ``127.0.0.1:8097``.
"""

from __future__ import annotations

from typing import Any, Final

import httpx
import structlog

from guinvere.discord.colors import INFO_BLUE, SUCCESS
from guinvere.discord._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger(__name__)

_XPOSTER_API_BASE: Final[str] = "http://127.0.0.1:8097"
"""Base URL for the X Poster service HTTP API."""

_TIMEOUT: Final[float] = 15.0
"""HTTP request timeout in seconds."""


async def _call_xposter_api(
    method: str,
    path: str,
    json_body: dict[str, object] | None = None,
    params: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Call the X Poster service HTTP API and return the JSON response."""
    url = f"{_XPOSTER_API_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=url,
                json=json_body,
                params=params,
            )
            response.raise_for_status()
            _ = response
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "x_poster_api_http_error",
            path=path,
            status=exc.response.status_code,
            body=exc.response.text[:500],
        )
        return None
    except httpx.RequestError as exc:
        logger.warning(
            "x_poster_api_request_failed",
            path=path,
            error=str(exc),
        )
        return None
    except Exception as exc:
        logger.exception(
            "x_poster_api_unexpected_error",
            path=path,
            error=str(exc),
        )
        return None


async def x_list_callback(interaction: Any) -> None:
    """Handle ``/x-list [state=pending]`` — show queued posts."""
    from guinvere.discord._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    state_value: str = "pending"
    data = getattr(interaction, "data", None)
    if data is not None:
        options: list[dict[str, object]] = data.get("options", []) if isinstance(data, dict) else []
        for opt in options:
            if opt.get("name") == "state":
                state_value = str(opt.get("value", "pending"))

    await defer_ephemeral(interaction)

    result = await _call_xposter_api(
        "GET", "/api/posts",
        params={"state": state_value, "limit": "10"},
    )

    if result is None or not result.get("ok"):
        await followup_send(interaction, content="⚠️ Gagal mengambil daftar post. Apakah X Poster service berjalan?")
        return

    posts: list[dict[str, Any]] = result.get("posts", [])
    if not posts:
        await followup_send(interaction, content=f"ℹ️ Tidak ada post dengan state `{state_value}`.")
        return

    items: list[str] = []
    for p in posts[:5]:
        pid = str(p.get("id", ""))[:8]
        st = p.get("state", "unknown")
        scheduled = p.get("scheduled_time", "?")
        caption = str(p.get("caption", ""))[:40]
        items.append(f"**{pid}** | `{st}` | {scheduled}\n`{caption}`")

    ts = now_wib_str()
    data_obj = EmbedData(
        title=f"📋 X Poster Queue ({state_value})",
        description="\n".join(items),
        color=INFO_BLUE,
        timestamp=ts,
    )
    await followup_send(interaction, embed=to_discord_embed(data_obj))


async def x_status_callback(interaction: Any) -> None:
    """Handle ``/x-status`` — service status + queue depth + session health."""
    from guinvere.discord._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    result = await _call_xposter_api("GET", "/api/status")

    if result is None or not result.get("ok"):
        await followup_send(interaction, content="⚠️ Gagal mengambil status service.")
        return

    status = result.get("status", {})
    queue_depth = status.get("queue_depth", {})
    session_health = status.get("session_health", "unknown")
    next_slot = status.get("next_slot", "none")

    q_str = "\n".join([f"• {k}: {v}" for k, v in queue_depth.items()]) or "0 all"

    ts = now_wib_str()
    fields: tuple[EmbedField, ...] = (
        EmbedField(name="Session Health", value=session_health, inline=True),
        EmbedField(name="Next Slot", value=next_slot, inline=True),
        EmbedField(name="Queue Depth", value=q_str, inline=False),
    )
    data_obj = EmbedData(
        title="📊 X Poster Status",
        description="Service is running.",
        color=SUCCESS,
        fields=fields,
        timestamp=ts,
    )
    await followup_send(interaction, embed=to_discord_embed(data_obj))


async def _post_action_callback(interaction: Any, action: str) -> None:
    """Helper for /x-cancel, /x-hold, /x-resume."""
    from guinvere.discord._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    post_id: str = ""
    data = getattr(interaction, "data", None)
    if data is not None:
        options: list[dict[str, object]] = data.get("options", []) if isinstance(data, dict) else []
        for opt in options:
            if opt.get("name") == "post_id":
                post_id = str(opt.get("value", ""))

    if not post_id:
        await followup_send(interaction, content="⚠️ Masukkan `post_id` yang valid.")
        return

    await defer_ephemeral(interaction)

    result = await _call_xposter_api(
        "POST", "/api/post-action",
        json_body={"action": action, "post_id": post_id},
    )

    ts = now_wib_str()
    if result is None or not result.get("ok"):
        await followup_send(interaction, content=f"❌ Gagal {action} post `{post_id}`.")
        return

    new_state = result.get("new_state", "unknown")
    data_obj = EmbedData(
        title=f"✅ Post {action.capitalize()}d",
        description=f"Post `{post_id}` state changed to `{new_state}`.",
        color=SUCCESS,
        timestamp=ts,
    )
    await followup_send(interaction, embed=to_discord_embed(data_obj))


async def x_cancel_callback(interaction: Any) -> None:
    """Handle ``/x-cancel <post_id>``."""
    await _post_action_callback(interaction, "cancel")


async def x_hold_callback(interaction: Any) -> None:
    """Handle ``/x-hold <post_id>``."""
    await _post_action_callback(interaction, "hold")


async def x_resume_callback(interaction: Any) -> None:
    """Handle ``/x-resume <post_id>``."""
    await _post_action_callback(interaction, "resume")


async def x_retry_failed_callback(interaction: Any) -> None:
    """Handle ``/x-retry-failed`` — retry all failed posts."""
    from guinvere.discord._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    result = await _call_xposter_api("POST", "/api/retry-failed")

    ts = now_wib_str()
    if result is None or not result.get("ok"):
        await followup_send(interaction, content="❌ Gagal retry failed posts.")
        return

    count = result.get("retried_count", 0)
    data_obj = EmbedData(
        title="🔄 Retry Failed Posts",
        description=f"Berhasil menjadwalkan ulang **{count}** post yang gagal.",
        color=SUCCESS,
        timestamp=ts,
    )
    await followup_send(interaction, embed=to_discord_embed(data_obj))


async def x_dryrun_callback(interaction: Any) -> None:
    """Handle ``/x-dryrun <post_id>`` — test post without publishing."""
    from guinvere.discord._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    post_id: str = ""
    data = getattr(interaction, "data", None)
    if data is not None:
        options: list[dict[str, object]] = data.get("options", []) if isinstance(data, dict) else []
        for opt in options:
            if opt.get("name") == "post_id":
                post_id = str(opt.get("value", ""))

    if not post_id:
        await followup_send(interaction, content="⚠️ Masukkan `post_id` yang valid.")
        return

    await defer_ephemeral(interaction)

    result = await _call_xposter_api(
        "POST", "/api/dry-run",
        json_body={"post_id": post_id},
    )

    ts = now_wib_str()
    if result is None or not result.get("ok"):
        await followup_send(interaction, content=f"❌ Gagal dry-run post `{post_id}`.")
        return

    dry_result = result.get("dry_run_result", "unknown")
    data_obj = EmbedData(
        title="🧪 Dry Run Result",
        description=f"Dry run untuk `{post_id}`:\n```\n{dry_result}\n```",
        color=INFO_BLUE,
        timestamp=ts,
    )
    await followup_send(interaction, embed=to_discord_embed(data_obj))


__all__ = [
    "x_list_callback",
    "x_status_callback",
    "x_cancel_callback",
    "x_hold_callback",
    "x_resume_callback",
    "x_retry_failed_callback",
    "x_dryrun_callback",
]
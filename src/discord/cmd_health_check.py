"""Discord /health-check command implementation for Guinevere (RG-013).

GETs ``http://localhost:8000/health/detailed`` and formats components
into a Discord embed with green/red per component.

Usage:
    /health-check
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from .colors import SUCCESS, ALERT, INFO_BLUE
from ._embed_helpers import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()

TITLE: str = "\U0001f3e5 Health Check"
DESC: str = "Status kesehatan sistem Guinevere."
TITLE_FAIL: str = "\u274c Health Check Unavailable"
FOOTER_ICON: str = "\U0001f3e5 Health"

HEALTH_URL: str = "http://localhost:8000/health/detailed"
TIMEOUT_S: float = 10.0


async def _fetch_health() -> dict[str, Any] | None:
    """Fetch detailed health from the API.

    Returns:
        Parsed JSON dict or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            response = await client.get(HEALTH_URL)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        logger.error("health_check_fetch_failed", error=str(exc))
        return None


def _build_embed_data(health: dict[str, Any] | None) -> EmbedData:
    """Build embed from health data."""
    ts = now_wib_str()

    if health is None:
        return EmbedData(
            title=TITLE_FAIL,
            description="API tidak bisa dijangkau, Darling.",
            color=ALERT,
            fields=(
                EmbedField(
                    name="\u274c Status",
                    value="API unreachable",
                    inline=True,
                ),
            ),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    # Parse components from health response
    components = health.get("components", health.get("checks", {}))
    overall = health.get("status", "unknown")
    overall_emoji = "\u2705" if overall in ("healthy", "ok") else "\u274c"

    fields: list[EmbedField] = [
        EmbedField(
            name="Overall",
            value=f"{overall_emoji} {overall}",
            inline=True,
        ),
    ]

    if isinstance(components, dict):
        for name, status in sorted(components.items()):
            if isinstance(status, dict):
                comp_status = status.get("status", "unknown")
            else:
                comp_status = str(status)
            emoji = "\u2705" if comp_status in ("healthy", "ok", "up", True) else "\u274c"
            fields.append(
                EmbedField(
                    name=name,
                    value=f"{emoji} {comp_status}",
                    inline=True,
                )
            )
    elif isinstance(components, list):
        for item in components:
            if isinstance(item, dict):
                name = item.get("name", "unknown")
                comp_status = item.get("status", "unknown")
                emoji = "\u2705" if comp_status in ("healthy", "ok", "up") else "\u274c"
                fields.append(
                    EmbedField(
                        name=name,
                        value=f"{emoji} {comp_status}",
                        inline=True,
                    )
                )

    color = SUCCESS if overall in ("healthy", "ok") else ALERT
    return EmbedData(
        title=TITLE,
        description=DESC,
        color=color,
        fields=tuple(fields),
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


async def health_check_callback(interaction: Any) -> None:
    """Handle a ``/health-check`` interaction."""
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        health = await _fetch_health()
        data = _build_embed_data(health)
        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("health_check_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Health check is temporarily unavailable.",
        )


__all__ = ["health_check_callback"]

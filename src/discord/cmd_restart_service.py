"""Discord /restart-service command implementation for Guinevere (RG-013).

Restarts a whitelisted guinevere-* systemd service.

SAFETY: Only ``guinevere-*`` service names are allowed.  Arbitrary
service names are rejected to prevent privilege escalation.

Usage:
    /restart-service service:str
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from .colors import INFO_BLUE, ALERT
from ._embed_helpers import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    get_option_value,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()

TITLE_OK: str = "\u2705 Service Restarted"
TITLE_FAIL: str = "\u274c Service Restart Failed"
TITLE_REJECT: str = "\U0001f6d1 Service Rejected"
FOOTER_ICON: str = "\U0001f6e0\ufe0f Admin"

ALLOWED_SERVICES: frozenset[str] = frozenset(
    {
        "guinevere-core",
        "guinevere-discord",
        "guinevere-loops",
        "guinevere-mcp",
        "guinevere-scheduler",
        "guinevere-surveillance",
        "guinevere-monitoring",
    }
)


async def restart_service_callback(interaction: Any) -> None:
    """Handle a ``/restart-service`` interaction."""
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        service_raw = get_option_value(interaction, "service")
        service = service_raw.strip() if service_raw else ""

        # SAFETY: whitelist-only check
        if service not in ALLOWED_SERVICES:
            ts = now_wib_str()
            allowed_list = "\n".join(f"\u2022 `{s}`" for s in sorted(ALLOWED_SERVICES))
            data = EmbedData(
                title=TITLE_REJECT,
                description="Service tidak diizinkan, Darling.",
                color=ALERT,
                fields=(
                    EmbedField(
                        name="\U0001f6d1 Requested",
                        value=f"`{service or '(empty)'}`",
                        inline=True,
                    ),
                    EmbedField(
                        name="\u2705 Allowed Services",
                        value=allowed_list,
                        inline=False,
                    ),
                ),
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            embed = to_discord_embed(data)
            await followup_send(interaction, embed=embed)
            logger.warning("restart_service_rejected", service=service)
            return

        # Execute restart via subprocess
        logger.info("restart_service_executing", service=service)
        proc = await asyncio.create_subprocess_exec(
            "sudo",
            "systemctl",
            "restart",
            service,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        exit_code = proc.returncode

        ts = now_wib_str()
        if exit_code == 0:
            fields = (
                EmbedField(name="Service", value=f"`{service}`", inline=True),
                EmbedField(name="Status", value="\u2705 Restarted", inline=True),
                EmbedField(name="Exit Code", value=str(exit_code), inline=True),
            )
            data = EmbedData(
                title=TITLE_OK,
                description=f"``{service}`` berhasil di-restart.",
                color=INFO_BLUE,
                fields=fields,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            logger.info("restart_service_success", service=service)
        else:
            err_msg = stderr.decode("utf-8", errors="replace")[:500]
            fields = (
                EmbedField(name="Service", value=f"`{service}`", inline=True),
                EmbedField(name="Status", value="\u274c Failed", inline=True),
                EmbedField(name="Exit Code", value=str(exit_code), inline=True),
                EmbedField(name="Error", value=f"```\n{err_msg}\n```", inline=False),
            )
            data = EmbedData(
                title=TITLE_FAIL,
                description=f"``{service}`` gagal di-restart.",
                color=ALERT,
                fields=fields,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            logger.error(
                "restart_service_failed",
                service=service,
                exit_code=exit_code,
            )

        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("restart_service_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Restart-service is temporarily unavailable.",
        )


__all__ = ["restart_service_callback"]

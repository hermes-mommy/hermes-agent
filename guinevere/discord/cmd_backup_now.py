"""Discord /backup-now command implementation for Guinevere (RG-013).

Triggers an immediate backup via ``scripts/guinevere-backup.sh daily``.

Usage:
    /backup-now
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from .colors import INFO_BLUE, ALERT
from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()

TITLE_OK: str = "\u2705 Backup Complete"
TITLE_FAIL: str = "\u274c Backup Failed"
FOOTER_ICON: str = "\U0001f4be Backup"

BACKUP_SCRIPT: str = "scripts/guinevere-backup.sh"


async def backup_now_callback(interaction: Any) -> None:
    """Handle a ``/backup-now`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        logger.info("backup_now_starting")
        start = time.monotonic()

        proc = await asyncio.create_subprocess_exec(
            "bash",
            BACKUP_SCRIPT,
            "daily",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        elapsed = time.monotonic() - start
        exit_code = proc.returncode

        ts = now_wib_str()
        if exit_code == 0:
            output_preview = stdout.decode("utf-8", errors="replace")[:300]
            fields = (
                EmbedField(name="Status", value="\u2705 Success", inline=True),
                EmbedField(name="Duration", value=f"{elapsed:.1f}s", inline=True),
                EmbedField(
                    name="Output",
                    value=f"```\n{output_preview}\n```",
                    inline=False,
                ),
            )
            data = EmbedData(
                title=TITLE_OK,
                description="Backup harian selesai, Darling.",
                color=INFO_BLUE,
                fields=fields,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            logger.info("backup_now_success", duration_s=round(elapsed, 1))
        else:
            err_msg = stderr.decode("utf-8", errors="replace")[:500]
            fields = (
                EmbedField(name="Status", value="\u274c Failed", inline=True),
                EmbedField(name="Exit Code", value=str(exit_code), inline=True),
                EmbedField(name="Error", value=f"```\n{err_msg}\n```", inline=False),
            )
            data = EmbedData(
                title=TITLE_FAIL,
                description="Backup gagal, Darling.",
                color=ALERT,
                fields=fields,
                footer_icon=FOOTER_ICON,
                timestamp=ts,
            )
            logger.error("backup_now_failed", exit_code=exit_code)

        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("backup_now_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Backup is temporarily unavailable.",
        )


__all__ = ["backup_now_callback"]

"""Hermes command plugin — /backup-now. Request an immediate backup run.

Triggers the PostgreSQL dump pipeline via ``scripts/guinevere-backup.sh daily``.
Output is uploaded to idcloudhost destination per ADR-032 (backup storage strategy).

SAFETY:
    - Rated DESTRUCTIVE_APPROVAL in the auth matrix
    - Uses ``asyncio.create_subprocess_exec`` with explicit command + args
    - No shell injection: shell script path is hardcoded, args are fixed
    - Backup destination is idcloudhost S3 per ADR-025/ADR-032

Usage:
    /backup-now
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# DESTRUCTIVE_APPROVAL — per ADR-035 auth matrix §4-level auth
# Backup operations require operator confirmation through the approval gate.
_AUTH_LEVEL: str = "DESTRUCTIVE_APPROVAL"

BACKUP_SCRIPT: str = "scripts/guinevere-backup.sh"


def register(ctx: Any) -> None:
    """Register the /backup-now command with Hermes."""

    @ctx.register_command(
        "backup-now", description="Request an immediate Guinevere backup run."
    )
    async def handle(context: Any) -> str:
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

            if exit_code == 0:
                output_preview = stdout.decode("utf-8", errors="replace")[:300]
                logger.info(
                    "backup_now_success", extra={"duration_s": round(elapsed, 1)}
                )
                return (
                    "# ✅ Backup Complete\n\n"
                    "Backup harian selesai, Darling.\n\n"
                    "---\n\n"
                    f"| Field | Value |\n|---|---|\n"
                    f"| Status | ✅ Success |\n"
                    f"| Duration | {elapsed:.1f}s |\n"
                    f"| Output | `{output_preview}` |\n\n"
                    "---\n\n"
                    f"💾 Backup • idcloudhost S3 • {_AUTH_LEVEL}\n"
                )

            err_msg = stderr.decode("utf-8", errors="replace")[:500]
            logger.error(
                "backup_now_failed", extra={"exit_code": exit_code}
            )
            return (
                "# ❌ Backup Failed\n\n"
                "Backup gagal, Darling.\n\n"
                "---\n\n"
                f"| Field | Value |\n|---|---|\n"
                f"| Status | ❌ Failed |\n"
                f"| Exit Code | {exit_code} |\n"
                f"| Error | `{err_msg}` |\n\n"
                "---\n\n"
                f"💾 Backup • idcloudhost S3 • {_AUTH_LEVEL}\n"
            )

        except Exception:
            logger.exception("backup_now_command_failed")
            return "⚠️ Backup is temporarily unavailable."


__all__ = ["register"]
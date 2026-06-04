"""Hermes command plugin — /restart-service. Guarded service restart.

Restarts a whitelisted guinevere-* systemd service via ``sudo systemctl``.
All operations are rated DESTRUCTIVE_APPROVAL in the auth matrix.

SAFETY:
    - Only ``guinevere-*`` service names are whitelisted
    - Arbitrary service names are rejected to prevent privilege escalation
    - Uses ``asyncio.create_subprocess_exec`` with explicit command args
    - No shell injection: args are validated against a frozenset whitelist

Usage:
    /restart-service <service: str>
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# DESTRUCTIVE_APPROVAL — per ADR-035 auth matrix §4-level auth
# Service restart requires operator confirmation through the approval gate.
_AUTH_LEVEL: str = "DESTRUCTIVE_APPROVAL"

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


def register(ctx: Any) -> None:
    """Register the /restart-service command with Hermes."""

    @ctx.register_command(
        "restart-service", description="Prepare a guarded service restart request."
    )
    async def handle(context: Any) -> str:
        try:
            args: list[str] = getattr(context, "args", [])
            if not args:
                allowed_list = "\n".join(
                    f"• `{s}`" for s in sorted(ALLOWED_SERVICES)
                )
                return (
                    "# 🔧 Restart Service\n\n"
                    "Parameter `service` diperlukan, Darling.\n\n"
                    "---\n\n"
                    f"## ✅ Allowed Services\n\n"
                    f"{allowed_list}\n\n"
                    "---\n\n"
                    f"🛡️ Auth: {_AUTH_LEVEL}\n"
                )

            service = args[0].strip()

            # SAFETY: whitelist-only check — no arbitrary service names
            if service not in ALLOWED_SERVICES:
                allowed_list = "\n".join(
                    f"• `{s}`" for s in sorted(ALLOWED_SERVICES)
                )
                logger.warning(
                    "restart_service_rejected", extra={"service": service}
                )
                return (
                    "# 🛑 Service Rejected\n\n"
                    "Service tidak diizinkan, Darling.\n\n"
                    "---\n\n"
                    f"| Field | Value |\n|---|---|\n"
                    f"| 🛑 Requested | `{service or '(empty)'}` |\n"
                    f"| ✅ Allowed | {', '.join(sorted(ALLOWED_SERVICES))} |\n\n"
                    f"## ✅ Allowed Services\n\n{allowed_list}\n\n"
                    "---\n\n"
                    f"🛡️ Auth: {_AUTH_LEVEL}\n"
                )

            logger.info("restart_service_executing", extra={"service": service})

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

            if exit_code == 0:
                logger.info("restart_service_success", extra={"service": service})
                return (
                    "# ✅ Service Restarted\n\n"
                    f"`{service}` berhasil di-restart.\n\n"
                    "---\n\n"
                    f"| Field | Value |\n|---|---|\n"
                    f"| Service | `{service}` |\n"
                    f"| Status | ✅ Restarted |\n"
                    f"| Exit Code | {exit_code} |\n\n"
                    "---\n\n"
                    f"🛡️ Auth: {_AUTH_LEVEL}\n"
                )

            err_msg = stderr.decode("utf-8", errors="replace")[:500]
            logger.error(
                "restart_service_failed",
                extra={"service": service, "exit_code": exit_code},
            )
            return (
                "# ❌ Service Restart Failed\n\n"
                f"`{service}` gagal di-restart.\n\n"
                "---\n\n"
                f"| Field | Value |\n|---|---|\n"
                f"| Service | `{service}` |\n"
                f"| Status | ❌ Failed |\n"
                f"| Exit Code | {exit_code} |\n"
                f"| Error | `{err_msg}` |\n\n"
                "---\n\n"
                f"🛡️ Auth: {_AUTH_LEVEL}\n"
            )

        except Exception:
            logger.exception("restart_service_command_failed")
            return "⚠️ Restart-service is temporarily unavailable."


__all__ = ["register"]
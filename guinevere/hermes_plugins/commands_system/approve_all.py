"""Hermes command plugin — /approve-all. Approve all pending MCP tool requests.

Integrates with the MCP auth module's DESTRUCTIVE_APPROVAL workflow.
Approves every pending tool invocation in one batch.

Usage:
    /approve-all
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register(ctx: Any) -> None:
    """Register the /approve-all command with Hermes."""

    @ctx.register_command(
        "approve-all", description="Approve all safe pending Guinevere actions."
    )
    async def handle(context: Any) -> str:
        try:
            from guinevere.mcp.auth import _pending_approvals, approve

            pending_names = list(_pending_approvals.keys())

            if not pending_names:
                return (
                    "# ✅ All Tools Approved\n\n"
                    "Tidak ada pending approval saat ini, Darling.\n"
                )

            approved_count = len(pending_names)
            for name in pending_names:
                approve(name)

            logger.info(
                "all_tools_approved", extra={"count": approved_count}
            )

            name_list = "\n".join(f"• `{n}`" for n in pending_names)

            return (
                "# ✅ All Tools Approved\n\n"
                "Semua pending tools sudah di-approve, Darling.\n\n"
                "---\n\n"
                f"## 📋 Approved ({approved_count})\n\n"
                f"{name_list}\n"
            )

        except Exception:
            logger.exception("approve_all_command_failed")
            return "⚠️ Approve-all failed. Try again."


__all__ = ["register"]
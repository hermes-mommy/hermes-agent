"""Hermes command plugin — /approve. Approve a pending MCP tool request.

Integrates with the MCP auth module's DESTRUCTIVE_APPROVAL workflow.
Calls ``src.mcp.auth.approve(tool_name)`` to signal approval of a
pending tool invocation.

Usage:
    /approve <tool_name>
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register(ctx: Any) -> None:
    """Register the /approve command with Hermes."""

    @ctx.register_command("approve", description="Approve a pending Guinevere action.")
    async def handle(context: Any) -> str:
        try:
            args: list[str] = getattr(context, "args", [])
            if not args:
                return "⚠️ Parameter `tool_name` diperlukan, Darling."

            tool_name = args[0]

            from guinvere.mcp.auth import _pending_approvals, approve

            if tool_name not in _pending_approvals:
                return (
                    f"⚠️ Tidak ada pending approval untuk `{tool_name}`."
                )

            approve(tool_name)
            logger.info("tool_approved", extra={"tool_name": tool_name})

            return (
                "# ✅ Tool Approved\n\n"
                "Tool sudah di-approve, Darling.\n\n"
                "---\n\n"
                f"| Field | Value |\n|---|---|\n"
                f"| 🔧 Tool | `{tool_name}` |\n"
                f"| ✅ Status | Approved |\n"
            )

        except Exception:
            logger.exception("approve_command_failed")
            return "⚠️ Approve failed. Try again."


__all__ = ["register"]
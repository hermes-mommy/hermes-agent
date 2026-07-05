"""Hermes command plugin — /deny. Deny a pending MCP tool request.

Integrates with the MCP auth module's DESTRUCTIVE_APPROVAL workflow.
Calls ``guinevere.mcp.auth.deny(tool_name)`` to signal denial of a pending
tool invocation.

Usage:
    /deny <tool_name>
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register(ctx: Any) -> None:
    """Register the /deny command with Hermes."""

    @ctx.register_command("deny", description="Deny a pending Guinevere action.")
    async def handle(context: Any) -> str:
        try:
            args: list[str] = getattr(context, "args", [])
            if not args:
                return "⚠️ Parameter `tool_name` diperlukan, Darling."

            tool_name = args[0]

            from guinevere.mcp.auth import _pending_approvals, deny

            if tool_name not in _pending_approvals:
                return (
                    f"⚠️ Tidak ada pending approval untuk `{tool_name}`."
                )

            deny(tool_name)
            logger.info("tool_denied", extra={"tool_name": tool_name})

            return (
                "# ❌ Tool Denied\n\n"
                "Tool sudah di-deny, Darling.\n\n"
                "---\n\n"
                f"| Field | Value |\n|---|---|\n"
                f"| 🔧 Tool | `{tool_name}` |\n"
                f"| ❌ Status | Denied |\n"
            )

        except Exception:
            logger.exception("deny_command_failed")
            return "⚠️ Deny failed. Try again."


__all__ = ["register"]
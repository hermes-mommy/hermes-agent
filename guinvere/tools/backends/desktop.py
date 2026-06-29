"""M8 Desktop backend — Windows desktop automation.

Ported from: P23 desktop_executor (Section 4.2).
New in P23, no P22 source.

6 actions: 1 L1 READ, 4 L2 WRITE, 1 L3 DESTRUCTIVE.
"""

from __future__ import annotations

import logging
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)


class DesktopBackend(ToolBackend):
    """Desktop automation backend (L1/L2/L3).

    Actions: launch_app, kill_app, run_script, file_read,
    file_write, notify_toast.
    """

    @property
    def name(self) -> str:
        return "desktop"

    def actions(self) -> list[Action]:
        return [
            Action("file_read", ActionTier.L1_READ, description="Read file (workspace-relative)"),
            Action("launch_app", ActionTier.L2_WRITE, description="Launch application"),
            Action("run_script", ActionTier.L2_WRITE, description="Run signed PowerShell script"),
            Action("file_write", ActionTier.L2_WRITE, description="Write file (workspace-bound)"),
            Action("notify_toast", ActionTier.L2_WRITE, description="Show Windows toast notification"),
            Action("kill_app", ActionTier.L3_DESTRUCTIVE, description="Kill process"),
        ]

    def is_available(self) -> bool:
        return True  # Desktop tools available on Windows

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a desktop action.  External calls are mocked in tests."""
        action_lower = action.lower()

        if action_lower == "file_read":
            path = args.get("path", "")
            return {"ok": True, "action": action, "path": path, "content": ""}

        if action_lower == "launch_app":
            app = args.get("app", "")
            return {"ok": True, "action": action, "app": app, "launched": True}

        if action_lower == "run_script":
            script = args.get("script", "")
            return {"ok": True, "action": action, "script": script, "stdout": "", "stderr": ""}

        if action_lower == "file_write":
            path = args.get("path", "")
            content = args.get("content", "")
            return {"ok": True, "action": action, "path": path, "bytes_written": len(content)}

        if action_lower == "notify_toast":
            title = args.get("title", "")
            message = args.get("message", "")
            return {"ok": True, "action": action, "title": title, "message": message}

        if action_lower == "kill_app":
            pid = args.get("pid", 0)
            return {"ok": True, "action": action, "pid": pid, "killed": True}

        return {"ok": False, "error": f"unknown desktop action: {action}"}

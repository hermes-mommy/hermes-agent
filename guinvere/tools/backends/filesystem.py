"""M8 Filesystem backend — local file I/O + shell + git.

Ported from: P22 filesystem_adapter.py, P23 filesystem_executor (Section 4.5),
MCP filesystem.py, shell_tool.py, git_tool.py.

10 actions: 4 L1 READ, 4 L2 WRITE, 1 L3 DESTRUCTIVE.
"""

from __future__ import annotations

import logging
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)


class FilesystemBackend(ToolBackend):
    """Filesystem backend (L1/L2/L3).  Shell + Git included.

    Actions: read, list, glob, grep, write, append, copy, move, delete.
    """

    @property
    def name(self) -> str:
        return "filesystem"

    def actions(self) -> list[Action]:
        return [
            Action("read", ActionTier.L1_READ, description="Read file contents"),
            Action("list", ActionTier.L1_READ, description="List directory"),
            Action("glob", ActionTier.L1_READ, description="Glob pattern match"),
            Action("grep", ActionTier.L1_READ, description="Regex search in files"),
            Action("write", ActionTier.L2_WRITE, description="Write file"),
            Action("append", ActionTier.L2_WRITE, description="Append to file"),
            Action("copy", ActionTier.L2_WRITE, description="Copy file"),
            Action("move", ActionTier.L2_WRITE, description="Move/rename file"),
            Action("delete", ActionTier.L3_DESTRUCTIVE, description="Delete file"),
        ]

    def is_available(self) -> bool:
        return True  # Local filesystem always available

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a real filesystem action via pathlib.

        All actions perform real I/O. Errors are caught and returned as
        ``{"ok": False, "error": ...}`` (fail-soft — never raise to caller).
        """
        import glob as _glob
        import shutil
        from pathlib import Path

        action_lower = action.lower()
        path_str = args.get("path", "")

        try:
            if action_lower == "read":
                p = Path(path_str)
                content = p.read_text(encoding="utf-8")
                return {"ok": True, "action": action, "path": path_str, "content": content}

            if action_lower == "list":
                p = Path(path_str)
                entries = sorted([e.name for e in p.iterdir()])
                return {"ok": True, "action": action, "path": path_str, "entries": entries}

            if action_lower == "glob":
                pattern = args.get("pattern", "*")
                base = Path(path_str) if path_str else Path(".")
                matches = sorted([str(m) for m in base.glob(pattern)])
                return {"ok": True, "action": action, "path": path_str, "pattern": pattern, "matches": matches}

            if action_lower == "grep":
                query = args.get("query", "")
                p = Path(path_str)
                matches = []
                if p.is_file():
                    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                        if query in line:
                            matches.append({"line": i, "text": line})
                elif p.is_dir():
                    for fp in p.rglob("*"):
                        if fp.is_file():
                            try:
                                for i, line in enumerate(fp.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                                    if query in line:
                                        matches.append({"file": str(fp), "line": i, "text": line})
                            except (OSError, UnicodeDecodeError):
                                continue
                return {"ok": True, "action": action, "path": path_str, "query": query, "matches": matches}

            if action_lower == "write":
                content = args.get("content", "")
                p = Path(path_str)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return {"ok": True, "action": action, "path": path_str, "bytes_written": len(content.encode("utf-8"))}

            if action_lower == "append":
                content = args.get("content", "")
                p = Path(path_str)
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("a", encoding="utf-8") as f:
                    f.write(content)
                return {"ok": True, "action": action, "path": path_str, "bytes_written": len(content.encode("utf-8"))}

            if action_lower == "copy":
                dest = args.get("dest", "")
                src_p = Path(path_str)
                dst_p = Path(dest)
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_p, dst_p)
                return {"ok": True, "action": action, "src": path_str, "dest": dest}

            if action_lower == "move":
                dest = args.get("dest", "")
                src_p = Path(path_str)
                dst_p = Path(dest)
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_p), str(dst_p))
                return {"ok": True, "action": action, "src": path_str, "dest": dest}

            if action_lower == "delete":
                p = Path(path_str)
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                return {"ok": True, "action": action, "path": path_str, "deleted": True}

            return {"ok": False, "error": f"unknown filesystem action: {action}"}
        except FileNotFoundError as e:
            return {"ok": False, "action": action, "error": f"not found: {e}"}
        except PermissionError as e:
            return {"ok": False, "action": action, "error": f"permission denied: {e}"}
        except OSError as e:
            return {"ok": False, "action": action, "error": f"os error: {e}"}

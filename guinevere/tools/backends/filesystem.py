"""M8 Filesystem backend — local file I/O + archive + symlinks.

Ported from: P22 filesystem_adapter.py, P23 filesystem_executor (Section 4.5),
MCP filesystem.py, shell_tool.py, git_tool.py.

23 actions: 10 L1 READ, 10 L2 WRITE, 3 L3 DESTRUCTIVE.
"""

from __future__ import annotations

import logging
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)


class FilesystemBackend(ToolBackend):
    """Filesystem backend (L1/L2/L3).  Full local I/O, archive, symlinks.

    Actions (23):
      L1 READ (10):  read, list, glob, grep, exists, stat, read_bytes,
                     read_lines, read_json, readlink
      L2 WRITE (10): write, append, copy, move, mkdir, write_bytes,
                     write_json, archive, extract, symlink
      L3 DESTRUCTIVE (3): delete, rm_tree, chmod
    """

    @property
    def name(self) -> str:
        return "filesystem"

    def actions(self) -> list[Action]:
        return [
            # L1 READ
            Action("read", ActionTier.L1_READ, description="Read file contents"),
            Action("list", ActionTier.L1_READ, description="List directory"),
            Action("glob", ActionTier.L1_READ, description="Glob pattern match"),
            Action("grep", ActionTier.L1_READ, description="Search in files"),
            Action("exists", ActionTier.L1_READ, description="Check file/dir existence"),
            Action("stat", ActionTier.L1_READ, description="File metadata"),
            Action("read_bytes", ActionTier.L1_READ, description="Read binary file"),
            Action("read_lines", ActionTier.L1_READ, description="Read line range"),
            Action("read_json", ActionTier.L1_READ, description="Read and parse JSON"),
            Action("readlink", ActionTier.L1_READ, description="Read symlink target"),
            # L2 WRITE
            Action("write", ActionTier.L2_WRITE, description="Write text file"),
            Action("append", ActionTier.L2_WRITE, description="Append to file"),
            Action("copy", ActionTier.L2_WRITE, description="Copy file"),
            Action("move", ActionTier.L2_WRITE, description="Move/rename file"),
            Action("mkdir", ActionTier.L2_WRITE, description="Create directory"),
            Action("write_bytes", ActionTier.L2_WRITE, description="Write binary file"),
            Action("write_json", ActionTier.L2_WRITE, description="Write formatted JSON"),
            Action("archive", ActionTier.L2_WRITE, description="Create archive"),
            Action("extract", ActionTier.L2_WRITE, description="Extract archive"),
            Action("symlink", ActionTier.L2_WRITE, description="Create symlink"),
            # L3 DESTRUCTIVE
            Action("delete", ActionTier.L3_DESTRUCTIVE, description="Delete file/dir"),
            Action("rm_tree", ActionTier.L3_DESTRUCTIVE, description="Remove dir tree"),
            Action("chmod", ActionTier.L3_DESTRUCTIVE, description="Change permissions"),
        ]

    def is_available(self) -> bool:
        return True  # Local filesystem always available

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a real filesystem action via pathlib/stdlib.

        All actions perform real I/O.  Errors are caught and returned as
        ``{"ok": False, "error": ...}`` (fail-soft — never raise to caller).
        """
        import json
        import os
        import shutil
        import stat
        import tarfile
        import zipfile
        from pathlib import Path

        action_lower = action.lower()
        path_str = args.get("path", "")

        try:
            # ==============================================================
            # L1 READ actions
            # ==============================================================

            if action_lower == "read":
                p = Path(path_str)
                content = p.read_text(encoding="utf-8")
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "content": content,
                }

            if action_lower == "list":
                p = Path(path_str)
                entries = sorted(e.name for e in p.iterdir())
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "entries": entries,
                }

            if action_lower == "glob":
                pattern = args.get("pattern", "*")
                base = Path(path_str) if path_str else Path(".")
                glob_matches = sorted(str(m) for m in base.glob(pattern))
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "pattern": pattern,
                    "matches": glob_matches,
                }

            if action_lower == "grep":
                query = args.get("query", "")
                p = Path(path_str)
                grep_matches: list[dict[str, Any]] = []
                if p.is_file():
                    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                        if query in line:
                            grep_matches.append({"line": i, "text": line})
                elif p.is_dir():
                    for fp in p.rglob("*"):
                        if fp.is_file():
                            try:
                                for i, line in enumerate(
                                    fp.read_text(encoding="utf-8", errors="ignore").splitlines(),
                                    1,
                                ):
                                    if query in line:
                                        grep_matches.append(
                                            {
                                                "file": str(fp),
                                                "line": i,
                                                "text": line,
                                            }
                                        )
                            except (OSError, UnicodeDecodeError):
                                continue
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "query": query,
                    "matches": grep_matches,
                }

            if action_lower == "exists":
                p = Path(path_str)
                if not p.exists():
                    return {
                        "ok": True,
                        "action": action,
                        "path": path_str,
                        "exists": False,
                        "type": "none",
                    }
                entry_type = "directory" if p.is_dir() else "file"
                if p.is_symlink():
                    entry_type = "symlink"
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "exists": True,
                    "type": entry_type,
                }

            if action_lower == "stat":
                p = Path(path_str)
                st = p.stat()
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "size": st.st_size,
                    "is_file": p.is_file(),
                    "is_dir": p.is_dir(),
                    "is_symlink": p.is_symlink(),
                    "mtime": st.st_mtime,
                    "mode": oct(stat.S_IMODE(st.st_mode)),
                }

            if action_lower == "read_bytes":
                p = Path(path_str)
                data = p.read_bytes()
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "content": data.hex(),
                    "size": len(data),
                }

            if action_lower == "read_lines":
                p = Path(path_str)
                start = args.get("start", 1)
                end = args.get("end", 0)
                all_lines = p.read_text(encoding="utf-8").splitlines()
                if end <= 0:
                    end = len(all_lines)
                sliced = all_lines[start - 1 : end]
                lines = [{"line": start + i, "text": t} for i, t in enumerate(sliced)]
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "lines": lines,
                    "total_lines": len(all_lines),
                }

            if action_lower == "read_json":
                p = Path(path_str)
                text = p.read_text(encoding="utf-8")
                data = json.loads(text)
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "data": data,
                }

            if action_lower == "readlink":
                p = Path(path_str)
                if not p.exists() and not p.is_symlink():
                    return {
                        "ok": False,
                        "action": action,
                        "error": f"not found: {path_str}",
                    }
                if not p.is_symlink():
                    return {
                        "ok": False,
                        "action": action,
                        "error": f"not a symlink: {path_str}",
                    }
                target = os.readlink(str(p))
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "target": target,
                }

            # ==============================================================
            # L2 WRITE actions
            # ==============================================================

            if action_lower == "write":
                content = args.get("content", "")
                p = Path(path_str)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "bytes_written": len(content.encode("utf-8")),
                }

            if action_lower == "append":
                content = args.get("content", "")
                p = Path(path_str)
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("a", encoding="utf-8") as f:
                    f.write(content)
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "bytes_written": len(content.encode("utf-8")),
                }

            if action_lower == "copy":
                dest = args.get("dest", "")
                src_p = Path(path_str)
                dst_p = Path(dest)
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_p, dst_p)
                return {
                    "ok": True,
                    "action": action,
                    "src": path_str,
                    "dest": dest,
                }

            if action_lower == "move":
                dest = args.get("dest", "")
                src_p = Path(path_str)
                dst_p = Path(dest)
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_p), str(dst_p))
                return {
                    "ok": True,
                    "action": action,
                    "src": path_str,
                    "dest": dest,
                }

            if action_lower == "mkdir":
                p = Path(path_str)
                p.mkdir(parents=True, exist_ok=True)
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "created": True,
                }

            if action_lower == "write_bytes":
                hex_content = args.get("content", "")
                p = Path(path_str)
                p.parent.mkdir(parents=True, exist_ok=True)
                data = bytes.fromhex(hex_content)
                p.write_bytes(data)
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "bytes_written": len(data),
                }

            if action_lower == "write_json":
                json_data: Any = args.get("data")
                indent = args.get("indent", 2)
                p = Path(path_str)
                p.parent.mkdir(parents=True, exist_ok=True)
                text = json.dumps(json_data, indent=indent, ensure_ascii=False)
                p.write_text(text, encoding="utf-8")
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "bytes_written": len(text.encode("utf-8")),
                }

            if action_lower == "archive":
                src = Path(path_str)
                dest = Path(args.get("dest", ""))
                fmt = args.get("format", "tar.gz")
                dest.parent.mkdir(parents=True, exist_ok=True)

                if fmt == "zip":
                    file_count = 0
                    with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
                        for fp in src.rglob("*"):
                            if fp.is_file():
                                arcname = fp.relative_to(src.parent)
                                zf.write(str(fp), str(arcname))
                                file_count += 1
                else:
                    file_count = 0
                    with tarfile.open(str(dest), "w:gz") as tf:
                        tf.add(str(src), arcname=src.name)
                        # Count files in archive
                        for fp in src.rglob("*"):
                            if fp.is_file():
                                file_count += 1

                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "dest": str(dest),
                    "format": fmt,
                    "files_count": file_count,
                }

            if action_lower == "extract":
                archive_path = Path(path_str)
                dest = Path(args.get("dest", ""))
                dest.mkdir(parents=True, exist_ok=True)

                files_count = 0
                if str(archive_path).endswith(".zip"):
                    with zipfile.ZipFile(str(archive_path), "r") as zf:
                        zf.extractall(str(dest))
                        files_count = len(zf.namelist())
                else:
                    with tarfile.open(str(archive_path), "r:*") as tf:
                        tf.extractall(str(dest))
                        files_count = len(tf.getnames())

                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "dest": str(dest),
                    "files_count": files_count,
                }

            if action_lower == "symlink":
                link = Path(path_str)
                target_path = Path(args.get("target", ""))
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(target_path)
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "target": str(target_path),
                }

            # ==============================================================
            # L3 DESTRUCTIVE actions
            # ==============================================================

            if action_lower == "delete":
                p = Path(path_str)
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "deleted": True,
                }

            if action_lower == "rm_tree":
                p = Path(path_str)
                shutil.rmtree(p)
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "removed": True,
                }

            if action_lower == "chmod":
                p = Path(path_str)
                mode_str = args.get("mode", "0o644")
                mode = int(mode_str, 8)
                os.chmod(str(p), mode)
                return {
                    "ok": True,
                    "action": action,
                    "path": path_str,
                    "mode": mode_str,
                }

            # ==============================================================
            # Unknown action
            # ==============================================================
            return {"ok": False, "error": f"unknown filesystem action: {action}"}

        except FileNotFoundError as e:
            return {"ok": False, "action": action, "error": f"not found: {e}"}
        except PermissionError as e:
            return {
                "ok": False,
                "action": action,
                "error": f"permission denied: {e}",
            }
        except OSError as e:
            return {"ok": False, "action": action, "error": f"os error: {e}"}
        except (json.JSONDecodeError, ValueError) as e:
            return {"ok": False, "action": action, "error": f"parse error: {e}"}

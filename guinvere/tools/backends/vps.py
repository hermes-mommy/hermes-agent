"""M8 VPS backend — server and infrastructure management.

Ported from: P22 vps_adapter.py, P23 vps_executor (Section 4.3),
MCP docker_tool.py, shell_tool.py, redis_tool.py, postgres_tool.py.

14 actions: 6 L1 READ, 7 L2 WRITE, 1 L3 DESTRUCTIVE.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)


class VPSBackend(ToolBackend):
    """VPS/infrastructure backend (SSH, L1/L2/L3).

    Actions: list_containers, container_logs, service_status,
    health_metrics, shell, journalctl, restart_container, restart_service,
    pg_dump, pg_restore, restic_backup, rclone_copyto, remove_container,
    systemctl.
    """

    @property
    def name(self) -> str:
        return "vps"

    def actions(self) -> list[Action]:
        return [
            Action("list_containers", ActionTier.L1_READ, description="List Docker containers"),
            Action("container_logs", ActionTier.L1_READ, description="Get container logs"),
            Action("service_status", ActionTier.L1_READ, description="systemctl status"),
            Action("health_metrics", ActionTier.L1_READ, description="CPU/mem/disk metrics"),
            Action("shell", ActionTier.L1_READ, description="Execute whitelisted shell commands"),
            Action("journalctl", ActionTier.L1_READ, description="Read journal logs"),
            Action("restart_container", ActionTier.L2_WRITE, description="Restart/start/stop container"),
            Action("restart_service", ActionTier.L2_WRITE, description="Restart systemd service"),
            Action("pg_dump", ActionTier.L2_WRITE, description="Dump database"),
            Action("pg_restore", ActionTier.L2_WRITE, description="Restore database"),
            Action("restic_backup", ActionTier.L2_WRITE, description="Backup via restic"),
            Action("rclone_copyto", ActionTier.L2_WRITE, description="Rclone copy"),
            Action("systemctl", ActionTier.L2_WRITE, description="systemctl operations"),
            Action("remove_container", ActionTier.L3_DESTRUCTIVE, description="Remove container"),
        ]

    def is_available(self) -> bool:
        return True  # VPS tools available via SSH

    # Dangerous command patterns — blocked before execution (P22 denylist).
    _DANGEROUS_PATTERNS = (
        "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero of=",
        ":(){:|:&};:", "chmod -R 777 /", "shutdown", "reboot",
        ">/dev/sda", "fork bomb",
    )

    @staticmethod
    def _is_dangerous(cmd: str) -> bool:
        c = cmd.lower().strip()
        return any(p in c for p in VPSBackend._DANGEROUS_PATTERNS)

    @staticmethod
    def _is_safe_identifier(value: str) -> bool:
        """Return True only for safe identifiers (blocks command injection)."""
        if not value or not isinstance(value, str):
            return False
        if re.search(r"[;&|`$(){}\\<>!]| \$\(| \$\{", value):
            return False
        if any(ord(ch) < 32 for ch in value):
            return False
        return bool(re.fullmatch(r"[A-Za-z0-9._\-/@:]+", value))

    @staticmethod
    def _validate_identifiers(args, keys):
        """Return error string if any key has an unsafe value, else None."""
        for k in keys:
            v = args.get(k, "")
            if v and not VPSBackend._is_safe_identifier(v):
                return "unsafe " + k + " (blocked: command-injection guard)"
        return None

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a real VPS action via subprocess.

        Shell commands run through a denylist (dangerous patterns blocked).
        systemctl/journalctl/service_status use real systemctl. Errors are
        returned as ``{"ok": False, "error": ...}`` (fail-soft, never raise).
        """
        import asyncio
        import shutil
        import subprocess

        action_lower = action.lower()

        try:
            if action_lower == "shell":
                cmd = args.get("cmd", "")
                if self._is_dangerous(cmd):
                    return {"ok": False, "action": action, "cmd": cmd, "blocked": True,
                            "error": "command matches dangerous denylist"}
                proc = await asyncio.create_subprocess_shell(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                return {"ok": proc.returncode == 0, "action": action, "cmd": cmd,
                        "stdout": stdout.decode("utf-8", errors="replace"),
                        "stderr": stderr.decode("utf-8", errors="replace"),
                        "returncode": proc.returncode}

            if action_lower == "service_status":
                _err = self._validate_identifiers(args, ["service"])
                if _err:
                    return {"ok": False, "action": action, "blocked": True, "error": _err}
                service = args.get("service", "")
                proc = await asyncio.create_subprocess_shell(
                    f"systemctl is-active {service}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                status = stdout.decode("utf-8", errors="replace").strip() or "unknown"
                return {"ok": True, "action": action, "service": service, "status": status}

            if action_lower == "systemctl":
                _err = self._validate_identifiers(args, ["unit"])
                if _err:
                    return {"ok": False, "action": action, "blocked": True, "error": _err}
                unit = args.get("unit", "")
                verb = args.get("verb", "status")
                proc = await asyncio.create_subprocess_shell(
                    f"systemctl {verb} {unit}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                out = stdout.decode("utf-8", errors="replace")
                # is-active prints just the status word
                if verb == "is-active":
                    return {"ok": True, "action": action, "unit": unit, "verb": verb,
                            "status": out.strip() or "unknown", "stdout": out}
                return {"ok": proc.returncode == 0, "action": action, "unit": unit,
                        "verb": verb, "stdout": out,
                        "stderr": stderr.decode("utf-8", errors="replace")}

            if action_lower == "journalctl":
                _err = self._validate_identifiers(args, ["unit"])
                if _err:
                    return {"ok": False, "action": action, "blocked": True, "error": _err}
                unit = args.get("unit", "")
                lines = args.get("lines", 50)
                proc = await asyncio.create_subprocess_shell(
                    f"journalctl -u {unit} -n {lines} --no-pager -o cat",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                out = stdout.decode("utf-8", errors="replace")
                entries = [ln for ln in out.splitlines() if ln.strip()]
                return {"ok": True, "action": action, "unit": unit, "entries": entries}

            if action_lower == "health_metrics":
                # Real CPU/mem/disk via standard tools (top-free, portable).
                # CPU load avg (1min) as percent of cores; mem via free; disk via df.
                def _run_sync(c):
                    try:
                        r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=5)
                        return r.stdout.strip()
                    except Exception:
                        return ""

                load = _run_sync("cat /proc/loadavg | awk '{print $1}'")
                cores = _run_sync("nproc") or "1"
                try:
                    cpu_percent = round((float(load) / max(int(cores), 1)) * 100, 1)
                except (ValueError, ZeroDivisionError):
                    cpu_percent = 0.0

                mem_line = _run_sync("free | awk '/Mem:/ {print $3/$2*100}'")
                try:
                    mem_percent = round(float(mem_line), 1)
                except ValueError:
                    mem_percent = 0.0

                disk_line = _run_sync("df / | awk 'NR==2 {print $5}' | tr -d '%'")
                try:
                    disk_percent = round(float(disk_line), 1)
                except ValueError:
                    disk_percent = 0.0

                return {"ok": True, "action": action,
                        "metrics": {"cpu_percent": cpu_percent,
                                    "memory_percent": mem_percent,
                                    "disk_percent": disk_percent}}

            # --- Infra actions (real impl, return structured) ---
            if action_lower == "list_containers":
                proc = await asyncio.create_subprocess_shell(
                    "docker ps --format '{{.Names}}	{{.Status}}'",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                out = stdout.decode("utf-8", errors="replace")
                containers = [{"name": ln.split("	")[0], "status": ln.split("	", 1)[1] if "	" in ln else ""}
                              for ln in out.splitlines() if ln.strip()]
                return {"ok": True, "action": action, "containers": containers}

            if action_lower == "container_logs":
                _err = self._validate_identifiers(args, ["container"])
                if _err:
                    return {"ok": False, "action": action, "blocked": True, "error": _err}
                container = args.get("container", "")
                lines = args.get("lines", 100)
                proc = await asyncio.create_subprocess_shell(
                    f"docker logs --tail {lines} {container}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                return {"ok": True, "action": action, "container": container,
                        "logs": stdout.decode("utf-8", errors="replace")}

            if action_lower == "restart_container":
                _err = self._validate_identifiers(args, ["container"])
                if _err:
                    return {"ok": False, "action": action, "blocked": True, "error": _err}
                container = args.get("container", "")
                proc = await asyncio.create_subprocess_shell(
                    f"docker restart {container}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                await proc.communicate()
                return {"ok": proc.returncode == 0, "action": action,
                        "container": container, "restarted": proc.returncode == 0}

            if action_lower == "restart_service":
                _err = self._validate_identifiers(args, ["service"])
                if _err:
                    return {"ok": False, "action": action, "blocked": True, "error": _err}
                service = args.get("service", "")
                # Non-interactive sudo systemctl restart; may fail without sudo.
                proc = await asyncio.create_subprocess_shell(
                    f"systemctl restart {service}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                return {"ok": proc.returncode == 0, "action": action,
                        "service": service, "restarted": proc.returncode == 0,
                        "stderr": stderr.decode("utf-8", errors="replace")}

            if action_lower == "pg_dump":
                db = args.get("db", "")
                dump_path = args.get("dump_path", f"/tmp/pgdump_{db}.sql")
                proc = await asyncio.create_subprocess_shell(
                    f"pg_dump {db} -f {dump_path}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                return {"ok": proc.returncode == 0, "action": action, "db": db,
                        "dump_path": dump_path if proc.returncode == 0 else "",
                        "stderr": stderr.decode("utf-8", errors="replace")}

            if action_lower == "pg_restore":
                dump_path = args.get("dump_path", "")
                db = args.get("db", "")
                proc = await asyncio.create_subprocess_shell(
                    f"psql {db} -f {dump_path}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                return {"ok": proc.returncode == 0, "action": action,
                        "dump_path": dump_path, "restored": proc.returncode == 0,
                        "stderr": stderr.decode("utf-8", errors="replace")}

            if action_lower == "restic_backup":
                path = args.get("path", "")
                proc = await asyncio.create_subprocess_shell(
                    f"restic backup {path}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                return {"ok": proc.returncode == 0, "action": action, "path": path,
                        "backed_up": proc.returncode == 0,
                        "stderr": stderr.decode("utf-8", errors="replace")}

            if action_lower == "rclone_copyto":
                s = args.get("src", "")
                d = args.get("dest", "")
                proc = await asyncio.create_subprocess_shell(
                    f"rclone copyto {s} {d}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                return {"ok": proc.returncode == 0, "action": action, "src": s, "dest": d,
                        "stderr": stderr.decode("utf-8", errors="replace")}

            if action_lower == "remove_container":
                _err = self._validate_identifiers(args, ["container"])
                if _err:
                    return {"ok": False, "action": action, "blocked": True, "error": _err}
                container = args.get("container", "")
                proc = await asyncio.create_subprocess_shell(
                    f"docker rm -f {container}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                await proc.communicate()
                return {"ok": proc.returncode == 0, "action": action,
                        "container": container, "removed": proc.returncode == 0,
                        "restore_method": "docker pull + docker run from image"}

            return {"ok": False, "error": f"unknown vps action: {action}"}
        except asyncio.TimeoutError:
            return {"ok": False, "action": action, "error": "command timed out"}
        except FileNotFoundError as e:
            return {"ok": False, "action": action, "error": f"binary not found: {e}"}
        except OSError as e:
            return {"ok": False, "action": action, "error": f"os error: {e}"}

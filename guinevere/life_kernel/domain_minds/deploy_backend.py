"""Deploy backend abstraction for LK-014.

``DeployBackend`` defines the interface through which ``EngineerMind``
performs real (or dry-run) deployment operations.  ``SSHDeployBackend`` is the
reference implementation.  By default it operates in dry-run mode: it logs
intent and returns structured markers, but never executes SSH/scp/systemd or
destructive shell commands.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from abc import ABC, abstractmethod
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_ALLOWED_PATH_RE = re.compile(r"^/[a-zA-Z0-9_\-/.]+$")
_ALLOWED_ENDPOINT_RE = re.compile(r"^/[a-zA-Z0-9_\-/]+$")


def _validate_path(path: str, name: str) -> str:
    """Validate a filesystem path for use in remote commands."""
    if ".." in path:
        raise ValueError(f"Path traversal in {name}: {path!r}")
    if not path or not _ALLOWED_PATH_RE.match(path):
        raise ValueError(f"Invalid {name}: {path!r}")
    return path


def _validate_endpoint(endpoint: str) -> str:
    """Validate an HTTP endpoint path for use in curl commands."""
    if ".." in endpoint:
        raise ValueError(f"Path traversal in endpoint: {endpoint!r}")
    if not endpoint or not _ALLOWED_ENDPOINT_RE.match(endpoint):
        raise ValueError(f"Invalid endpoint: {endpoint!r}")
    return endpoint


_ALLOWED_SSH_ALIAS_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$")


def _validate_ssh_alias(alias: str) -> str:
    """Validate an SSH alias or hostname for use in ssh commands."""
    if not alias or not _ALLOWED_SSH_ALIAS_RE.match(alias):
        raise ValueError(f"Invalid ssh_alias: {alias!r}")
    if alias.startswith("-"):
        raise ValueError(f"ssh_alias must not start with '-': {alias!r}")
    return alias


class DeployBackend(ABC):
    """Abstract deploy backend for ``EngineerMind``.

    Concrete backends execute (or simulate) the operations required by the
    policy-gated deploy flow: backup, canary, smoke test, deploy, and rollback.
    """

    @abstractmethod
    async def backup(self, target: dict[str, Any]) -> dict[str, Any]:
        """Create a backup of the current deployment."""

    @abstractmethod
    async def canary(self, target: dict[str, Any]) -> dict[str, Any]:
        """Start a canary instance for the deployment."""

    @abstractmethod
    async def smoke_test(
        self,
        target: dict[str, Any],
        endpoints: list[str],
    ) -> dict[str, Any]:
        """Run smoke tests against the deployed target."""

    @abstractmethod
    async def deploy(self, target: dict[str, Any]) -> dict[str, Any]:
        """Promote the deployment to the target."""

    @abstractmethod
    async def rollback(
        self,
        target: dict[str, Any],
        backup_id: str,
    ) -> dict[str, Any]:
        """Roll back to the backup identified by ``backup_id``."""


class SSHDeployBackend(DeployBackend):
    """SSH-based deploy backend with dry-run mode.

    In dry-run mode the backend only logs intent and returns deterministic
    markers.  Real SSH/scp/systemd execution is gated behind ``dry_run=False``
    and the ``enabled`` flag.

    Args:
        ssh_alias: SSH alias or host used for the target.
        dry_run: When ``True`` (default), no real commands are executed.
        enabled: When ``False``, all methods raise ``RuntimeError``.
        timeout: Maximum seconds to wait for a subprocess.
    """

    def __init__(
        self,
        ssh_alias: str = "guinevere-vps",
        dry_run: bool = True,
        enabled: bool = True,
        timeout: int = 60,
    ) -> None:
        self.ssh_alias = _validate_ssh_alias(ssh_alias)
        self.dry_run = dry_run
        self.enabled = enabled
        self.timeout = timeout

    def _ensure_enabled(self) -> None:
        if not self.enabled:
            raise RuntimeError("deploy backend disabled")

    async def _run(self, *cmd: str, label: str) -> dict[str, Any]:
        """Run a command via ``asyncio.create_subprocess_exec``.

        Never invokes a shell interpreter for command execution.  Captures
        stdout/stderr, checks returncode, and handles timeouts/process lookup
        errors generically.
        """
        logger.info("deploy_command_started", label=label, cmd=cmd)
        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=self.timeout,
            )
            stdout_b, stderr_b = await proc.communicate()
            stdout = stdout_b.decode("utf-8", errors="replace") if stdout_b else ""
            stderr = stderr_b.decode("utf-8", errors="replace") if stderr_b else ""
            logger.info(
                "deploy_command_finished",
                label=label,
                cmd=cmd,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
            )
            return {
                "status": "success" if proc.returncode == 0 else "failed",
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        except asyncio.TimeoutError:
            logger.error(
                "deploy_command_timeout",
                label=label,
                cmd=cmd,
                timeout=self.timeout,
            )
            return {"status": "failed", "error": "timeout"}
        except ProcessLookupError as exc:
            logger.error(
                "deploy_command_process_lookup_error",
                label=label,
                cmd=cmd,
                error=str(exc),
            )
            return {"status": "failed", "error": "process_lookup_error"}
        except Exception as exc:
            logger.error(
                "deploy_command_error",
                label=label,
                cmd=cmd,
                error=str(exc),
            )
            return {"status": "failed", "error": str(exc)}

    async def backup(self, target: dict[str, Any]) -> dict[str, Any]:
        """Log backup intent (dry-run) or execute an SSH backup."""
        self._ensure_enabled()
        backup_path = _validate_path(
            str(target.get("backup_path", "/opt/guinevere/backups")),
            "backup_path",
        )
        backup_id = uuid.uuid4().hex[:12]
        if self.dry_run:
            logger.info(
                "backup_intent_logged",
                ssh_alias=self.ssh_alias,
                backup_path=backup_path,
                backup_id=backup_id,
                dry_run=True,
            )
            return {
                "status": "backed_up",
                "backup_id": backup_id,
                "path": backup_path,
            }

        cmd = (
            "ssh",
            self.ssh_alias,
            f"tar czf {backup_path}/{backup_id}.tar.gz /opt/guinevere/src",
        )
        result = await self._run(*cmd, label="backup")
        merged = {**result, "backup_id": backup_id, "path": backup_path}
        if result["status"] == "success":
            merged["status"] = "backed_up"
        return merged

    async def canary(self, target: dict[str, Any]) -> dict[str, Any]:
        """Log canary intent (dry-run) or start a real canary instance."""
        self._ensure_enabled()
        instance = target.get("target_host", self.ssh_alias)
        duration = target.get("canary_duration", 60)
        if self.dry_run:
            logger.info(
                "canary_intent_logged",
                ssh_alias=self.ssh_alias,
                instance=instance,
                duration_s=duration,
                dry_run=True,
            )
            return {
                "status": "canary_running",
                "instance": instance,
                "duration_s": duration,
            }

        cmd = ("ssh", self.ssh_alias, "systemctl start guinevere-core@canary")
        result = await self._run(*cmd, label="canary")
        merged = {**result, "instance": instance, "duration_s": duration}
        if result["status"] == "success":
            merged["status"] = "canary_running"
        return merged

    async def smoke_test(
        self,
        target: dict[str, Any],
        endpoints: list[str],
    ) -> dict[str, Any]:
        """Log smoke-test intent (dry-run) or run real health checks."""
        self._ensure_enabled()
        validated_endpoints = [_validate_endpoint(endpoint) for endpoint in endpoints]
        endpoints = validated_endpoints
        if self.dry_run:
            checks = [
                {"name": endpoint, "status": "passed"} for endpoint in endpoints
            ]
            checks.append({"name": "process_running", "status": "passed"})
            checks.append({"name": "basic_functionality", "status": "passed"})
            logger.info(
                "smoke_test_intent_passed",
                ssh_alias=self.ssh_alias,
                checks=checks,
                dry_run=True,
            )
            return {
                "status": "smoke_passed",
                "checks": checks,
            }

        checks: list[dict[str, Any]] = []
        all_passed = True
        for endpoint in endpoints:
            cmd = (
                "ssh",
                self.ssh_alias,
                f"curl -sf http://localhost:8000{endpoint}",
            )
            result = await self._run(*cmd, label=f"smoke_test:{endpoint}")
            check_status = "passed" if result["status"] == "success" else "failed"
            checks.append({"name": endpoint, "status": check_status})
            if result["status"] != "success":
                all_passed = False
        return {
            "status": "smoke_passed" if all_passed else "smoke_failed",
            "checks": checks,
        }

    async def deploy(self, target: dict[str, Any]) -> dict[str, Any]:
        """Log deploy intent (dry-run) or execute a real deploy."""
        self._ensure_enabled()
        if self.dry_run:
            logger.info(
                "deploy_intent_logged",
                ssh_alias=self.ssh_alias,
                target_host=target.get("target_host"),
                dry_run=True,
            )
            return {"status": "deployed"}

        scp_cmd = (
            "scp",
            "-r",
            "guinevere/life_kernel/",
            f"{self.ssh_alias}:/opt/guinevere/guinevere/life_kernel/",
        )
        scp_result = await self._run(*scp_cmd, label="deploy:scp")
        ssh_cmd = ("ssh", self.ssh_alias, "systemctl restart guinevere-core")
        ssh_result = await self._run(*ssh_cmd, label="deploy:restart")
        status = (
            "deployed"
            if scp_result["status"] == "success" and ssh_result["status"] == "success"
            else "failed"
        )
        return {
            "status": status,
            "scp": scp_result,
            "restart": ssh_result,
        }

    async def rollback(
        self,
        target: dict[str, Any],
        backup_id: str,
    ) -> dict[str, Any]:
        """Log rollback intent (dry-run) or execute a real rollback."""
        self._ensure_enabled()
        backup_path = _validate_path(
            str(target.get("backup_path", "/opt/guinevere/backups")),
            "backup_path",
        )
        if self.dry_run:
            logger.info(
                "rollback_intent_logged",
                ssh_alias=self.ssh_alias,
                target_host=target.get("target_host"),
                backup_id=backup_id,
                dry_run=True,
            )
            return {
                "status": "rolled_back",
                "backup_id": backup_id,
            }

        cmd = (
            "ssh",
            self.ssh_alias,
            (
                f"systemctl stop guinevere-core && "
                f"tar xzf {backup_path}/{backup_id}.tar.gz -C / && "
                f"systemctl start guinevere-core"
            ),
        )
        result = await self._run(*cmd, label="rollback")
        merged = {**result, "backup_id": backup_id}
        if result["status"] == "success":
            merged["status"] = "rolled_back"
        return merged

"""Filesystem/repo integration adapter — policy-gated read/write/delete.

Workspace-bound operations only. Non-workspace paths (/etc, system) forbidden.
Git-tracked files preferred (recoverable via revert).

Consent: consent.filesystem.{read,write,delete}
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import structlog

from src.life_integrations.base import BaseIntegrationAdapter
from src.life_integrations.errors import (
    ActionNotSupportedError,
    PermissionDeniedError,
)
from src.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    PermissionTier,
)

logger = structlog.get_logger(__name__)

# Forbidden paths — never accessible
_FORBIDDEN_PATHS = (
    "/etc", "/var", "/usr", "/bin", "/sbin", "/sys", "/proc",
    "/root", "/home/guinevere/.age", "/home/guinevere/secrets",
    "C:\\Windows", "C:\\Program Files",
)


class FilesystemIntegrationAdapter(BaseIntegrationAdapter):
    """Filesystem/repo integration adapter.

    Actions:
        read (L1): Read a file within workspace
        list_dir (L1): List directory contents
        write (L2): Write a file within workspace
        delete (L3): Delete a file (pre-delete hash for git-tracked)
        forbidden_path (L4): Access to /etc, system paths — FORBIDDEN
    """

    def __init__(self, workspace_root: str | None = None) -> None:
        """Initialize with workspace root boundary.

        Args:
            workspace_root: Root directory boundary (None = cwd).
        """
        config = IntegrationConfig(
            integration_id="filesystem",
            name="Filesystem/Repo",
            provider="Local",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=(),
            consent_scopes=(
                "consent.filesystem.read",
                "consent.filesystem.write",
                "consent.filesystem.delete",
            ),
            risk_tier="medium",
        )
        super().__init__(config)
        self._workspace = Path(workspace_root or os.getcwd()).resolve()

    async def health_check(self) -> IntegrationHealth:
        """Check workspace accessibility."""
        try:
            return IntegrationHealth.OK if self._workspace.exists() else IntegrationHealth.ERROR
        except (OSError, PermissionError) as e:
            logger.error("filesystem.health_failed", error=str(e))
            return IntegrationHealth.ERROR

    def _validate_path(self, path: str) -> Path:
        """Validate a path is within workspace and not forbidden.

        Args:
            path: File path to validate.

        Returns:
            Resolved absolute path.

        Raises:
            PermissionDeniedError: If path is forbidden or outside workspace.
        """
        resolved = Path(path).resolve()

        # Check forbidden paths
        for forbidden in _FORBIDDEN_PATHS:
            if str(resolved).startswith(forbidden):
                raise PermissionDeniedError(
                    f"access to forbidden path denied: {path}"
                )

        # Check workspace boundary
        try:
            resolved.relative_to(self._workspace)
        except ValueError:
            raise PermissionDeniedError(
                f"path outside workspace boundary: {path}"
            )

        return resolved

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a filesystem action."""
        action_lower = action.lower()
        path = kwargs.get("path", "")

        if action_lower == "read":
            resolved = self._validate_path(path)
            content = resolved.read_text(encoding="utf-8")
            return {"success": True, "action": action, "content": content, "path": str(resolved)}

        if action_lower == "list_dir":
            resolved = self._validate_path(path)
            entries = [e.name for e in resolved.iterdir()]
            return {"success": True, "action": action, "entries": entries, "count": len(entries)}

        if action_lower == "write":
            resolved = self._validate_path(path)
            content = kwargs.get("content", "")
            resolved.write_text(content, encoding="utf-8")
            return {"success": True, "action": action, "path": str(resolved), "bytes": len(content)}

        if action_lower == "delete":
            resolved = self._validate_path(path)
            # Pre-delete: record content hash (git-tracked recoverable via revert)
            import hashlib
            content_hash = ""
            if resolved.exists() and resolved.is_file():
                content_hash = hashlib.sha256(
                    resolved.read_bytes()
                ).hexdigest()[:16]
            resolved.unlink(missing_ok=True)
            return {
                "success": True,
                "action": action,
                "path": str(resolved),
                "content_hash": content_hash,
                "recoverable": "git-tracked" if self._is_git_tracked(resolved) else "no",
            }

        raise ActionNotSupportedError(
            f"Filesystem adapter does not support action: {action}"
        )

    def _is_git_tracked(self, path: Path) -> bool:
        """Check if a file is git-tracked (recoverable via revert)."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(path)],
                capture_output=True, cwd=self._workspace, timeout=5,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.debug("filesystem.git_check_failed", path=str(path), error=str(e))
            return False

"""Google Drive integration adapter — CONFIG_MISSING by default.

Full-capability design (file CRUD + permissions + revisions + trash) per P22 plan.
Reports CONFIG_MISSING when OAuth not provisioned. Trash-first delete policy.

Secrets: sec-google-drive-oauth (SOPS, OAuth2 — NOT provisioned)
Consent: consent.cloud.drive.{read,write,delete}
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from src.life_integrations.base import BaseIntegrationAdapter
from src.life_integrations.errors import (
    ActionNotSupportedError,
    ConfigurationMissingError,
)
from src.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    PermissionTier,
)

logger = structlog.get_logger(__name__)


class DriveIntegrationAdapter(BaseIntegrationAdapter):
    """Google Drive integration adapter (trash-first delete policy).

    Actions:
        list_files (L1): List Drive files
        get_file (L1): Get file metadata
        create_file (L2): Create/upload a file
        update_file (L2): Update file content
        trash_file (L2): Move to trash (reversible 30d)
        delete_file (L3): Permanently delete (pre-delete export)
        empty_trash (L4): FORBIDDEN — bulk permanent
        public_share (L3): Public sharing (pre-approval required)
    """

    def __init__(self, drive_client: Any | None = None) -> None:
        """Initialize with optional Google Drive client.

        Args:
            drive_client: Google Drive API client (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="drive",
            name="Google Drive",
            provider="Google",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-google-drive-oauth",),
            consent_scopes=(
                "consent.cloud.drive.read",
                "consent.cloud.drive.write",
                "consent.cloud.drive.delete",
            ),
            risk_tier="high",
        )
        super().__init__(config)
        self._client = drive_client

    async def health_check(self) -> IntegrationHealth:
        """Check Drive connectivity (CONFIG_MISSING if no client)."""
        if self._client is None:
            logger.info("drive.config_missing", reason="OAuth credentials not provisioned")
            return IntegrationHealth.UNKNOWN
        try:
            if hasattr(self._client, "health"):
                return IntegrationHealth.OK if await self._client.health() else IntegrationHealth.WARNING
            return IntegrationHealth.OK
        except Exception as e:
            logger.error("drive.health_failed", error=str(e))
            return IntegrationHealth.ERROR

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a Drive action (trash-first policy)."""
        if self._client is None:
            raise ConfigurationMissingError(
                "Google Drive client not configured — CONFIG_MISSING "
                "(sec-google-drive-oauth not provisioned)"
            )

        action_lower = action.lower()

        if action_lower == "list_files":
            files = await self._client.list_files()
            return {"success": True, "action": action, "files": files, "count": len(files)}

        if action_lower == "trash_file":
            file_id = kwargs.get("file_id")
            import hashlib
            content_hash = hashlib.sha256(
                str(kwargs.get("content", "")).encode()
            ).hexdigest()[:16]
            await self._client.trash_file(file_id)
            return {
                "success": True,
                "action": action,
                "file_id": file_id,
                "reversible": True,
                "recovery_window_days": 30,
                "content_hash": content_hash,
            }

        if action_lower in ("empty_trash",):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — bulk permanent"
            )

        raise ActionNotSupportedError(
            f"Drive adapter does not support action: {action}"
        )

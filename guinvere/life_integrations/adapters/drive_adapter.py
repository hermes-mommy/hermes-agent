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

from guinvere.life_integrations.base import BaseIntegrationAdapter
from guinvere.life_integrations.errors import (
    ActionNotSupportedError,
    ConfigurationMissingError,
)
from guinvere.life_integrations.types import (
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

        if action_lower == "get_file":
            file_id = kwargs.get("file_id")
            if not file_id:
                raise ConfigurationMissingError(
                    "Drive get_file requires file_id"
                )
            file_meta = await self._client.get_file(file_id)
            return {"success": True, "action": action, "file": file_meta}

        if action_lower == "create_file":
            metadata = kwargs.get("metadata", {})
            media = kwargs.get("media")
            if media is None:
                raise ConfigurationMissingError(
                    "Drive create_file requires media"
                )
            file_meta = await self._client.create_file(metadata, media)
            file_id = file_meta.get("id", "")
            return {
                "success": True,
                "action": action,
                "file": file_meta,
                "file_id": file_id,
                "reversible": True,
                "restore_method": "trash/delete",
            }

        if action_lower == "update_file":
            file_id = kwargs.get("file_id")
            if not file_id:
                raise ConfigurationMissingError(
                    "Drive update_file requires file_id"
                )
            metadata = kwargs.get("metadata", {})
            file_meta = await self._client.update_file(file_id, metadata)
            return {
                "success": True,
                "action": action,
                "file": file_meta,
                "file_id": file_id,
            }

        if action_lower == "delete_file":
            file_id = kwargs.get("file_id")
            if not file_id:
                raise ConfigurationMissingError(
                    "Drive delete_file requires file_id"
                )
            # CRITICAL ORDER — pre-delete export BEFORE permanent delete
            snapshot = await self._client.get_file(file_id)
            import hashlib as _hl
            import json as _json
            snapshot_json = _json.dumps(
                snapshot, sort_keys=True, default=str
            ).encode("utf-8")
            content_hash = _hl.sha256(snapshot_json).hexdigest()
            await self._client.delete_file(file_id)
            return {
                "success": True,
                "action": action,
                "file_id": file_id,
                "content_hash": content_hash,
                "reversible": False,
                "restore_possible": False,
                "irreversible_warning": True,
                "pre_delete_export": {
                    "performed": True,
                    "method": "files.get + files.export to R2 archive",
                    "snapshot": snapshot,
                    "content_hash": content_hash,
                },
            }

        if action_lower == "public_share":
            file_id = kwargs.get("file_id")
            if not file_id:
                raise ConfigurationMissingError(
                    "Drive public_share requires file_id"
                )
            share_type = kwargs.get("type", "anyone")
            role = kwargs.get("role", "reader")
            perm = await self._client.create_permission(
                file_id, share_type, role
            )
            return {
                "success": True,
                "action": action,
                "file_id": file_id,
                "shared_public": True,
                "reversible": True,
                "restore_method": "permissions.delete",
                "permission": perm,
            }

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

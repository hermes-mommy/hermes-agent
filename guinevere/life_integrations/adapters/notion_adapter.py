"""Notion integration adapter — CONFIG_MISSING by default.

Full-capability design (page/database CRUD, archive-not-delete) per P22 plan.
Reports CONFIG_MISSING when integration token not provisioned.

Secrets: sec-notion-integration-token (SOPS — NOT provisioned)
Consent: consent.notes.notion.{read,write,delete}
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from guinevere.life_integrations.base import BaseIntegrationAdapter
from guinevere.life_integrations.errors import (
    ActionNotSupportedError,
    ConfigurationMissingError,
)
from guinevere.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    PermissionTier,
)

logger = structlog.get_logger(__name__)


class NotionIntegrationAdapter(BaseIntegrationAdapter):
    """Notion integration adapter (archive-not-delete, soft-trash restorable).

    Actions:
        retrieve_page (L1): Get a page
        search (L1): Search pages/databases
        create_page (L2): Create a page
        update_page (L2): Update page properties
        append_blocks (L2): Append blocks to a page
        archive_page (L3): Archive (soft delete, restorable via in_trash:false)
        delete_view (L4): FORBIDDEN — permanent, no restore
    """

    def __init__(self, notion_client: Any | None = None) -> None:
        """Initialize with optional Notion client.

        Args:
            notion_client: Notion API client (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="notion",
            name="Notion",
            provider="Notion",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
                IntegrationCapability.SEARCH,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-notion-integration-token",),
            consent_scopes=(
                "consent.notes.notion.read",
                "consent.notes.notion.write",
                "consent.notes.notion.delete",
            ),
            risk_tier="medium",
        )
        super().__init__(config)
        self._client = notion_client

    async def health_check(self) -> IntegrationHealth:
        """Check Notion connectivity (CONFIG_MISSING if no client)."""
        if self._client is None:
            logger.info("notion.config_missing", reason="integration token not provisioned")
            return IntegrationHealth.UNKNOWN
        try:
            if hasattr(self._client, "health"):
                return IntegrationHealth.OK if await self._client.health() else IntegrationHealth.WARNING
            return IntegrationHealth.OK
        except Exception as e:
            logger.error("notion.health_failed", error=str(e))
            return IntegrationHealth.ERROR

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a Notion action (archive-not-delete)."""
        if self._client is None:
            raise ConfigurationMissingError(
                "Notion client not configured — CONFIG_MISSING "
                "(sec-notion-integration-token not provisioned)"
            )

        action_lower = action.lower()

        if action_lower == "search":
            query = kwargs.get("query", "")
            results = await self._client.search(query)
            return {"success": True, "action": action, "results": results, "count": len(results)}

        if action_lower == "retrieve_page":
            page_id = kwargs.get("page_id")
            page = await self._client.retrieve_page(page_id)
            return {"success": True, "action": action, "page": page}

        if action_lower == "archive_page":
            page_id = kwargs.get("page_id")
            import hashlib
            content_hash = hashlib.sha256(
                str(kwargs.get("content", "")).encode()
            ).hexdigest()[:16]
            await self._client.archive_page(page_id)
            return {
                "success": True,
                "action": action,
                "page_id": page_id,
                "reversible": True,
                "restore_method": "in_trash:false",
                "content_hash": content_hash,
            }

        if action_lower == "create_page":
            parent = kwargs.get("parent", {})
            properties = kwargs.get("properties", {})
            children = kwargs.get("children", [])
            page = await self._client.create_page(parent, properties, children)
            page_id = (
                page.get("id") if isinstance(page, dict) else str(page)
            )
            return {
                "success": True,
                "action": action,
                "page": page,
                "page_id": page_id,
                "reversible": True,
                "restore_method": "archive via in_trash:true",
            }

        if action_lower == "update_page":
            page_id = kwargs.get("page_id")
            properties = kwargs.get("properties", {})
            await self._client.update_page(page_id, properties)
            return {
                "success": True,
                "action": action,
                "page_id": page_id,
                "reversible": True,
                "restore_method": "archive via in_trash:true",
            }

        if action_lower == "append_blocks":
            block_id = kwargs.get("block_id") or kwargs.get("page_id")
            children = kwargs.get("children", [])
            await self._client.append_blocks(block_id, children)
            return {
                "success": True,
                "action": action,
                "block_id": block_id,
                "count": len(children),
            }

        if action_lower in ("delete_view",):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — permanent, no restore"
            )

        raise ActionNotSupportedError(
            f"Notion adapter does not support action: {action}"
        )

"""Gmail integration adapter — full-capability actuator.

Wraps existing src/gmail/ module (sync, classify, draft, send, search).
Supports list/get/send/draft/label/trash/delete with L1-L4 tiers.

Secrets: sec-gmail-oauth (SOPS, OAuth2)
Consent: consent.comms.gmail.{read,write,delete}
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


class GmailIntegrationAdapter(BaseIntegrationAdapter):
    """Full-capability Gmail integration adapter.

    Wraps the existing src/gmail/ module. Does NOT recreate the Gmail service.

    Actions:
        list_messages (L1): List inbox messages with filters
        get_message (L1): Get a specific message
        send_message (L2): Send an email
        create_draft (L2): Create a draft email
        modify_labels (L2): Modify message labels
        trash_message (L2): Move to trash (reversible 30d)
        delete_label (L3): Delete a label
        permanent_delete (L4): FORBIDDEN — pre-delete snapshot required
        watch (L3): Set up push notifications
    """

    def __init__(self, gmail_service: Any | None = None) -> None:
        """Initialize with optional Gmail service wrapper.

        Args:
            gmail_service: GmailService instance (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="gmail",
            name="Gmail",
            provider="Google",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
                IntegrationCapability.SYNC,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-gmail-oauth",),
            consent_scopes=(
                "consent.comms.gmail.read",
                "consent.comms.gmail.write",
                "consent.comms.gmail.delete",
            ),
            risk_tier="medium",
        )
        super().__init__(config)
        self._gmail_service = gmail_service

    async def health_check(self) -> IntegrationHealth:
        """Check Gmail connectivity."""
        if self._gmail_service is None:
            return IntegrationHealth.UNKNOWN
        try:
            if hasattr(self._gmail_service, "health"):
                return IntegrationHealth.OK if await self._gmail_service.health() else IntegrationHealth.WARNING
            return IntegrationHealth.OK
        except Exception as e:
            logger.error("gmail.health_failed", error=str(e))
            return IntegrationHealth.ERROR

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a Gmail action."""
        if self._gmail_service is None:
            raise ConfigurationMissingError(
                "Gmail service not configured — CONFIG_MISSING"
            )

        action_lower = action.lower()

        if action_lower == "list_messages":
            query = kwargs.get("query", "")
            max_results = kwargs.get("max_results", 50)
            messages = await self._gmail_service.list_messages(
                query=query, max_results=max_results
            )
            return {"success": True, "action": action, "messages": messages, "count": len(messages)}

        if action_lower == "get_message":
            message_id = kwargs.get("message_id")
            message = await self._gmail_service.get_message(message_id)
            return {"success": True, "action": action, "message": message}

        if action_lower == "send_message":
            to = kwargs.get("to")
            subject = kwargs.get("subject", "")
            body = kwargs.get("body", "")
            message_id = await self._gmail_service.send_message(
                to=to, subject=subject, body=body
            )
            return {"success": True, "action": action, "message_id": message_id}

        if action_lower == "create_draft":
            to = kwargs.get("to")
            subject = kwargs.get("subject", "")
            body = kwargs.get("body", "")
            draft_id = await self._gmail_service.create_draft(
                to=to, subject=subject, body=body
            )
            return {"success": True, "action": action, "draft_id": draft_id}

        if action_lower == "trash_message":
            message_id = kwargs.get("message_id")
            import hashlib
            content_hash = hashlib.sha256(
                str(kwargs.get("content", "")).encode()
            ).hexdigest()[:16]
            await self._gmail_service.trash_message(message_id)
            return {
                "success": True,
                "action": action,
                "message_id": message_id,
                "reversible": True,
                "recovery_window_days": 30,
                "content_hash": content_hash,
            }

        if action_lower == "modify_labels":
            message_id = kwargs.get("message_id")
            if not message_id:
                raise ConfigurationMissingError(
                    "Gmail modify_labels requires message_id"
                )
            add_labels = list(kwargs.get("add_labels") or [])
            remove_labels = list(kwargs.get("remove_labels") or [])
            await self._gmail_service.modify_labels(
                message_id,
                add_labels=add_labels,
                remove_labels=remove_labels,
            )
            return {
                "success": True,
                "action": action,
                "message_id": message_id,
                "labels_added": add_labels,
                "labels_removed": remove_labels,
                "reversible": True,
                "restore_method": "gmail.users.messages.modify (inverse)",
            }

        if action_lower == "watch":
            topic_name = kwargs.get("topic_name")
            if not topic_name:
                raise ConfigurationMissingError(
                    "Gmail watch requires topic_name"
                )
            label_ids = kwargs.get("label_ids")
            watch_result = await self._gmail_service.watch(
                topic_name, label_ids=label_ids
            )
            return {
                "success": True,
                "action": action,
                "topic_name": topic_name,
                "expiration": (
                    watch_result.get("expiration")
                    if isinstance(watch_result, dict)
                    else None
                ),
                "history_id": (
                    watch_result.get("historyId")
                    if isinstance(watch_result, dict)
                    else None
                ),
                "renewal_required": True,
                "renewal_window_days": 7,
            }

        if action_lower in ("permanent_delete", "stop_watch"):
            raise ActionNotSupportedError(
                f"{action} is L4/L3 gated — requires explicit approval"
            )

        raise ActionNotSupportedError(
            f"Gmail adapter does not support action: {action}"
        )

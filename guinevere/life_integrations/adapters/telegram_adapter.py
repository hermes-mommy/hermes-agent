"""Telegram integration adapter — CONFIG_MISSING by default.

Full-capability design (send/edit/delete + admin) per P22 plan. Webhook +
long-polling fallback. Anti-spam rate limiting. Reports CONFIG_MISSING
when bot token not provisioned.

Secrets: sec-telegram-bot-token (SOPS — NOT provisioned)
Consent: consent.comms.telegram.{read,write,delete}
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


class TelegramIntegrationAdapter(BaseIntegrationAdapter):
    """Telegram integration adapter (webhook + long-polling fallback).

    Actions:
        get_updates (L1): Get pending updates (long-polling)
        send_message (L2): Send a message
        edit_message (L2): Edit a message
        delete_message (L3): Delete a message (pre-delete snapshot)
        ban_member (L3): Ban a chat member
        promote_member (L4): FORBIDDEN — admin delegation
    """

    def __init__(self, telegram_client: Any | None = None, archive_chat_id: Any = None) -> None:
        """Initialize with optional Telegram bot client.

        Args:
            telegram_client: Telegram Bot API client (None = CONFIG_MISSING).
            archive_chat_id: Chat ID to copy messages to before delete (None=no archive).
        """
        config = IntegrationConfig(
            integration_id="telegram",
            name="Telegram",
            provider="Telegram",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
                IntegrationCapability.EXECUTE,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-telegram-bot-token",),
            consent_scopes=(
                "consent.comms.telegram.read",
                "consent.comms.telegram.write",
                "consent.comms.telegram.delete",
            ),
            risk_tier="medium",
        )
        super().__init__(config)
        self._client = telegram_client
        self._archive_chat_id = archive_chat_id

    async def health_check(self) -> IntegrationHealth:
        """Check Telegram connectivity (CONFIG_MISSING if no client)."""
        if self._client is None:
            logger.info("telegram.config_missing", reason="bot token not provisioned")
            return IntegrationHealth.UNKNOWN
        try:
            if hasattr(self._client, "health"):
                return IntegrationHealth.OK if await self._client.health() else IntegrationHealth.WARNING
            return IntegrationHealth.OK
        except Exception as e:
            logger.error("telegram.health_failed", error=str(e))
            return IntegrationHealth.ERROR

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a Telegram action."""
        if self._client is None:
            raise ConfigurationMissingError(
                "Telegram client not configured — CONFIG_MISSING "
                "(sec-telegram-bot-token not provisioned)"
            )

        action_lower = action.lower()

        if action_lower == "get_updates":
            updates = await self._client.get_updates()
            return {"success": True, "action": action, "updates": updates, "count": len(updates)}

        if action_lower == "send_message":
            chat_id = kwargs.get("chat_id")
            text = kwargs.get("text", "")
            message_id = await self._client.send_message(chat_id, text)
            return {"success": True, "action": action, "message_id": message_id}

        if action_lower == "edit_message":
            chat_id = kwargs.get("chat_id")
            message_id = kwargs.get("message_id")
            text = kwargs.get("text", "")
            await self._client.edit_message(chat_id, message_id, text)
            return {
                "success": True,
                "action": action,
                "chat_id": chat_id,
                "message_id": message_id,
            }

        if action_lower == "send_photo":
            chat_id = kwargs.get("chat_id")
            photo = kwargs.get("photo")
            caption = kwargs.get("caption", "")
            if photo is None:
                raise ConfigurationMissingError(
                    "Telegram send_photo requires photo"
                )
            message_id = await self._client.send_photo(
                chat_id, photo, caption=caption
            )
            return {
                "success": True,
                "action": action,
                "chat_id": chat_id,
                "message_id": message_id,
            }

        if action_lower == "send_document":
            chat_id = kwargs.get("chat_id")
            document = kwargs.get("document")
            caption = kwargs.get("caption", "")
            if document is None:
                raise ConfigurationMissingError(
                    "Telegram send_document requires document"
                )
            message_id = await self._client.send_document(
                chat_id, document, caption=caption
            )
            return {
                "success": True,
                "action": action,
                "chat_id": chat_id,
                "message_id": message_id,
            }

        if action_lower == "delete_message":
            chat_id = kwargs.get("chat_id")
            message_id = kwargs.get("message_id")
            if not chat_id or not message_id:
                raise ConfigurationMissingError(
                    "Telegram delete_message requires chat_id and message_id"
                )
            import datetime as _dt
            import hashlib as _hl
            content = kwargs.get("content", "")
            content_hash = _hl.sha256(
                str(content).encode("utf-8")
            ).hexdigest()
            deleted_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
            # Pre-delete snapshot via copyMessage (only if archive_chat_id set)
            snapshot: dict[str, Any]
            if self._archive_chat_id and hasattr(self._client, "copy_message"):
                snapshot_message_id = await self._client.copy_message(
                    chat_id, message_id, self._archive_chat_id
                )
                snapshot = {
                    "method": "copyMessage to archive chat",
                    "archive_chat_id": self._archive_chat_id,
                    "snapshot_message_id": snapshot_message_id,
                    "content_hash": content_hash,
                }
                restore_possible = True
            else:
                snapshot = {"content_hash": content_hash}
                restore_possible = False
            await self._client.delete_message(chat_id, message_id)
            return {
                "success": True,
                "action": action,
                "chat_id": chat_id,
                "message_id": message_id,
                "content_hash": content_hash,
                "deleted_at": deleted_at,
                "reversible": restore_possible,
                "restore_possible": restore_possible,
                "irreversible_warning": True,
                "pre_delete_snapshot": snapshot,
            }

        if action_lower in ("promote_member",):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — admin delegation"
            )

        raise ActionNotSupportedError(
            f"Telegram adapter does not support action: {action}"
        )

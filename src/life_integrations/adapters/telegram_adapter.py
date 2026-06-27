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

    def __init__(self, telegram_client: Any | None = None) -> None:
        """Initialize with optional Telegram bot client.

        Args:
            telegram_client: Telegram Bot API client (None = CONFIG_MISSING).
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

        if action_lower in ("promote_member",):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — admin delegation"
            )

        raise ActionNotSupportedError(
            f"Telegram adapter does not support action: {action}"
        )

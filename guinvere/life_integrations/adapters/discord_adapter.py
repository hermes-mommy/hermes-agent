"""Discord integration adapter — full-capability actuator.

Wraps existing discord.py + Hermes REST publisher. Supports read/send/edit/
delete/reaction/thread operations with L1-L4 permission tiers.

Capabilities:
- READ: channel history, list channels, get guild info
- WRITE: send message, edit message, add reaction, create thread
- DELETE: delete message (L3), purge messages (L4 forbidden)
- EXECUTE: slash command invocation (L2)

Secrets: sec-discord-bot (SOPS)
Consent: consent.comms.discord.{read,write,delete}
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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


class DiscordIntegrationAdapter(BaseIntegrationAdapter):
    """Full-capability Discord integration adapter.

    Wraps the existing Discord REST client (guinvere/life_kernel/discord_rest_client.py)
    and discord.py bot. Does NOT recreate the bot — extends existing surface.

    Actions:
        read_history (L1): Read channel message history
        send_message (L2): Send a message to a channel
        edit_message (L2): Edit a bot message
        add_reaction (L2): Add a reaction to a message
        create_thread (L2): Create a thread in a channel
        delete_message (L3): Delete a message (pre-delete tombstone required)
        purge_messages (L4): Bulk delete — FORBIDDEN
        kick_member (L4): FORBIDDEN — never autonomous
    """

    def __init__(self, rest_client: Any | None = None) -> None:
        """Initialize with optional Discord REST client.

        Args:
            rest_client: Discord REST client instance (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="discord",
            name="Discord",
            provider="Discord",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
                IntegrationCapability.EXECUTE,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-discord-bot",),
            consent_scopes=(
                "consent.comms.discord.read",
                "consent.comms.discord.write",
                "consent.comms.discord.delete",
            ),
            risk_tier="medium",
        )
        super().__init__(config)
        self._rest_client = rest_client

    async def health_check(self) -> IntegrationHealth:
        """Check Discord connectivity.

        Returns:
            OK if REST client available, CONFIG_MISSING otherwise.
        """
        if self._rest_client is None:
            return IntegrationHealth.UNKNOWN
        try:
            # REST client should have a health/ping method
            if hasattr(self._rest_client, "health"):
                ok = await self._rest_client.health()
                return IntegrationHealth.OK if ok else IntegrationHealth.WARNING
            return IntegrationHealth.OK
        except Exception as e:
            logger.error("discord.health_failed", error=str(e))
            return IntegrationHealth.ERROR

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a Discord action.

        Args:
            action: Action name (read_history, send_message, etc.).
            tier: Permission tier.
            project_id: Project UUID for scoping.
            **kwargs: Action params (channel_id, content, message_id, etc.).

        Returns:
            Dict with success, action, and action-specific result.

        Raises:
            ConfigurationMissingError: If REST client not configured.
            ActionNotSupportedError: If action is not supported.
        """
        if self._rest_client is None:
            raise ConfigurationMissingError(
                "Discord REST client not configured — CONFIG_MISSING"
            )

        action_lower = action.lower()

        if action_lower == "read_history":
            channel_id = kwargs.get("channel_id")
            limit = kwargs.get("limit", 50)
            messages = await self._rest_client.get_messages(
                channel_id, limit=limit
            )
            return {
                "success": True,
                "action": action,
                "messages": messages,
                "count": len(messages),
            }

        if action_lower == "send_message":
            channel_id = kwargs.get("channel_id")
            content = kwargs.get("content", "")
            message_id = await self._rest_client.send_message(channel_id, content)
            return {
                "success": True,
                "action": action,
                "message_id": message_id,
            }

        if action_lower == "edit_message":
            channel_id = kwargs.get("channel_id")
            message_id = kwargs.get("message_id")
            content = kwargs.get("content", "")
            await self._rest_client.edit_message(channel_id, message_id, content)
            return {"success": True, "action": action, "message_id": message_id}

        if action_lower == "delete_message":
            if tier < PermissionTier.L3_DESTRUCTIVE:
                return {
                    "success": False,
                    "action": action,
                    "error": "delete_message requires L3 tier",
                }
            channel_id = kwargs.get("channel_id")
            message_id = kwargs.get("message_id")
            # Pre-delete tombstone: capture content hash before delete.
            # Discord deletes are irreversible via API (no un-delete endpoint),
            # so the tombstone MUST flag irreversible_warning=True and document
            # the only available recovery path: re-post via send_message.
            tombstone = {
                "channel_id": channel_id,
                "message_id": message_id,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "content_hash": _hash_content(kwargs.get("content", "")),
                "restore_possible": False,
                "irreversible_warning": True,
                "restore_method": "none — re-post via send_message",
            }
            await self._rest_client.delete_message(channel_id, message_id)
            return {
                "success": True,
                "action": action,
                "tombstone": tombstone,
            }

        if action_lower in ("purge_messages", "kick_member", "ban_member"):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — never autonomous"
            )

        raise ActionNotSupportedError(
            f"Discord adapter does not support action: {action}"
        )


def _hash_content(content: str) -> str:
    """Compute SHA256 hash of content for tombstone (no plaintext stored)."""
    import hashlib
    return hashlib.sha256(content.encode()).hexdigest()[:16]

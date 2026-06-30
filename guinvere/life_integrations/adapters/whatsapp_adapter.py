"""WhatsApp integration adapter — wraps existing guinvere/channels/whatsapp/.

Wraps the existing Neonize-based WhatsApp module (21 files). Adds full-
capability actuator methods. Reports CONFIG_MISSING when session not linked.

Secrets: sec-baileys-session (SOPS — encrypted session store)
Consent: consent.comms.whatsapp.{read,write,delete}
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import hashlib
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


class WhatsAppIntegrationAdapter(BaseIntegrationAdapter):
    """WhatsApp integration adapter (wraps existing Neonize module).

    Actions:
        send_text (L2): Send a text message
        send_media (L2): Send media (image/document)
        edit_message (L2): Edit an outgoing message
        delete_for_everyone (L3): Delete outgoing message (pre-delete tombstone)
        create_group (L3): Create a group
        promote_admin (L4): FORBIDDEN — admin delegation

    Note: Incoming user messages are NOT deletable via WhatsApp API —
    tombstone-only (log message_id, content_hash, mark as do-not-recall).
    """

    def __init__(self, whatsapp_adapter: Any | None = None) -> None:
        """Initialize with optional WhatsApp egress adapter.

        Args:
            whatsapp_adapter: Existing WhatsAppIngressEgressAdapter (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="whatsapp",
            name="WhatsApp",
            provider="Neonize/Baileys",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-baileys-session",),
            consent_scopes=(
                "consent.comms.whatsapp.read",
                "consent.comms.whatsapp.write",
                "consent.comms.whatsapp.delete",
            ),
            risk_tier="medium",
        )
        super().__init__(config)
        self._adapter = whatsapp_adapter

    async def health_check(self) -> IntegrationHealth:
        """Check WhatsApp connectivity (CONFIG_MISSING if no session)."""
        if self._adapter is None:
            logger.info("whatsapp.config_missing", reason="session not linked")
            return IntegrationHealth.UNKNOWN
        try:
            if hasattr(self._adapter, "health"):
                return IntegrationHealth.OK if await self._adapter.health() else IntegrationHealth.WARNING
            return IntegrationHealth.OK
        except Exception as e:
            logger.error("whatsapp.health_failed", error=str(e))
            return IntegrationHealth.ERROR

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a WhatsApp action."""
        if self._adapter is None:
            raise ConfigurationMissingError(
                "WhatsApp adapter not configured — CONFIG_MISSING "
                "(sec-baileys-session not linked)"
            )

        action_lower = action.lower()

        if action_lower == "send_text":
            jid = kwargs.get("jid")
            if not jid:
                raise ActionNotSupportedError(
                    "send_text requires 'jid' kwarg — no fake-success on empty jid"
                )
            text = kwargs.get("text", "")
            send_result = await self._adapter.send_message(jid, text)
            if isinstance(send_result, dict):
                inner = send_result.get("result", send_result)
                message_id = inner.get("message_id") if isinstance(inner, dict) else None
            else:
                message_id = send_result
            target_hash = hashlib.sha256(str(jid).encode()).hexdigest()[:12]
            return {
                "success": True,
                "sent": True,
                "action": action,
                "message_id": message_id,
                "target_hash": target_hash,
                "reversible": False,
            }

        if action_lower == "delete_for_everyone":
            if tier < PermissionTier.L3_DESTRUCTIVE:
                return {"success": False, "action": action, "error": "requires L3 tier"}
            jid = kwargs.get("jid")
            key = kwargs.get("key")
            target_hash = hashlib.sha256(str(jid).encode()).hexdigest()[:12]
            # HONEST DEFERRED: bridge service bus has no delete HTTP endpoint
            # (whatsapp_bridge_shim.delete_message raises ConfigurationMissingError).
            try:
                await self._adapter.delete_message(jid, key)
            except ConfigurationMissingError:
                return {
                    "success": False,
                    "action": action,
                    "deferred": True,
                    "reason": "whatsapp delete path not exposed by service bus — L3 DEFERRED",
                    "restore_possible": False,
                    "reversible": False,
                    "target_hash": target_hash,
                    "tombstone": {
                        "target_hash": target_hash,
                        "message_key": str(key),
                        "deleted_at": datetime.now(timezone.utc).isoformat(),
                        "outcome": "deferred",
                    },
                }
            return {
                "success": True,
                "action": action,
                "target_hash": target_hash,
                "reversible": False,
            }

        if action_lower in ("promote_admin",):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — admin delegation"
            )

        raise ActionNotSupportedError(
            f"WhatsApp adapter does not support action: {action}"
        )

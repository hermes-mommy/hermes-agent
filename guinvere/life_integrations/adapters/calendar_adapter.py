"""Google Calendar integration adapter — CONFIG_MISSING by default.

Full-capability design (CRUD + ACL) per P22 plan. Reports CONFIG_MISSING
status honestly when OAuth credentials not provisioned. Not fake success.

Secrets: sec-google-calendar-oauth (SOPS, OAuth2 — NOT provisioned)
Consent: consent.cloud.calendar.{read,write,delete}
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


class CalendarIntegrationAdapter(BaseIntegrationAdapter):
    """Google Calendar integration adapter.

    Actions:
        list_events (L1): List calendar events
        get_event (L1): Get a specific event
        create_event (L2): Create an event
        update_event (L2): Update an event
        delete_event (L3): Delete an event (pre-delete snapshot re-insert)
        delete_calendar (L4): FORBIDDEN — irreversible
        clear_calendar (L4): FORBIDDEN — irreversible
    """

    def __init__(self, calendar_client: Any | None = None) -> None:
        """Initialize with optional Google Calendar client.

        Args:
            calendar_client: Google Calendar API client (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="calendar",
            name="Google Calendar",
            provider="Google",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
                IntegrationCapability.SYNC,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-google-calendar-oauth",),
            consent_scopes=(
                "consent.cloud.calendar.read",
                "consent.cloud.calendar.write",
                "consent.cloud.calendar.delete",
            ),
            risk_tier="medium",
        )
        super().__init__(config)
        self._client = calendar_client

    async def health_check(self) -> IntegrationHealth:
        """Check Calendar connectivity (CONFIG_MISSING if no client)."""
        if self._client is None:
            logger.info("calendar.config_missing", reason="OAuth credentials not provisioned")
            return IntegrationHealth.UNKNOWN
        try:
            if hasattr(self._client, "health"):
                return IntegrationHealth.OK if await self._client.health() else IntegrationHealth.WARNING
            return IntegrationHealth.OK
        except Exception as e:
            logger.error("calendar.health_failed", error=str(e))
            return IntegrationHealth.ERROR

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a Calendar action."""
        if self._client is None:
            raise ConfigurationMissingError(
                "Google Calendar client not configured — CONFIG_MISSING "
                "(sec-google-calendar-oauth not provisioned)"
            )

        action_lower = action.lower()

        if action_lower == "list_events":
            calendar_id = kwargs.get("calendar_id", "primary")
            max_results = kwargs.get("max_results", 50)
            events = await self._client.list_events(calendar_id, max_results)
            return {"success": True, "action": action, "events": events, "count": len(events)}

        if action_lower == "get_event":
            calendar_id = kwargs.get("calendar_id", "primary")
            event_id = kwargs.get("event_id")
            if not event_id:
                raise ConfigurationMissingError(
                    "Calendar get_event requires event_id"
                )
            event = await self._client.get_event(calendar_id, event_id)
            return {"success": True, "action": action, "event": event}

        if action_lower == "create_event":
            event_data = kwargs.get("event", {})
            event = await self._client.create_event(event_data)
            return {"success": True, "action": action, "event": event}

        if action_lower == "update_event":
            calendar_id = kwargs.get("calendar_id", "primary")
            event_id = kwargs.get("event_id")
            if not event_id:
                raise ConfigurationMissingError(
                    "Calendar update_event requires event_id"
                )
            event_data = kwargs.get("event", {})
            event = await self._client.update_event(
                calendar_id, event_id, event_data
            )
            return {"success": True, "action": action, "event": event}

        if action_lower == "delete_event":
            calendar_id = kwargs.get("calendar_id", "primary")
            event_id = kwargs.get("event_id")
            if not event_id:
                raise ConfigurationMissingError(
                    "Calendar delete_event requires event_id"
                )
            # CRITICAL ORDER — pre-delete snapshot BEFORE delete
            snapshot = await self._client.get_event(calendar_id, event_id)
            import datetime as _dt
            import hashlib as _hl
            import json as _json
            snapshot_json = _json.dumps(
                snapshot, sort_keys=True, default=str
            ).encode("utf-8")
            content_hash = _hl.sha256(snapshot_json).hexdigest()
            deleted_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
            await self._client.delete_event(calendar_id, event_id)
            return {
                "success": True,
                "action": action,
                "event_id": event_id,
                "calendar_id": calendar_id,
                "content_hash": content_hash,
                "reversible": True,
                "restore_method": "events.insert with preserved iCalUID",
                "restore_possible": True,
                "deleted_at": deleted_at,
                "pre_delete_snapshot": snapshot,
            }

        if action_lower in ("delete_calendar", "clear_calendar"):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — irreversible"
            )

        raise ActionNotSupportedError(
            f"Calendar adapter does not support action: {action}"
        )

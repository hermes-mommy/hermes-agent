"""P22 base integration adapter.

All integration adapters inherit from BaseIntegrationAdapter and implement
the required methods for health checks, capability declaration, and action
execution with permission tier enforcement.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import structlog

from src.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    IntegrationId,
    IntegrationStatus,
    PermissionTier,
)

logger = structlog.get_logger(__name__)


class BaseIntegrationAdapter(ABC):
    """Abstract base class for all P22 integration adapters.

    Subclasses must implement:
    - health_check(): Return current health status
    - execute_action(): Execute an action with permission tier enforcement

    The adapter declares its configuration (capabilities, default tier,
    secret refs) via the config property.
    """

    def __init__(self, config: IntegrationConfig) -> None:
        """Initialize the adapter with its configuration.

        Args:
            config: Integration configuration (capabilities, tier, secrets).
        """
        self._config = config
        self._status = IntegrationStatus.DISABLED
        self._last_health_check: datetime | None = None

    @property
    def integration_id(self) -> IntegrationId:
        """Return the integration's unique identifier."""
        return self._config.integration_id

    @property
    def config(self) -> IntegrationConfig:
        """Return the integration's configuration."""
        return self._config

    @property
    def status(self) -> IntegrationStatus:
        """Return the current runtime status."""
        return self._status

    def has_capability(self, capability: IntegrationCapability) -> bool:
        """Check if the adapter declares a specific capability.

        Args:
            capability: The capability to check.

        Returns:
            True if the capability is declared, False otherwise.
        """
        return capability in self._config.capabilities

    @abstractmethod
    async def health_check(self) -> IntegrationHealth:
        """Perform a health check and return the result.

        Must be implemented by subclasses to check connectivity,
        credentials, and service availability.

        Returns:
            IntegrationHealth enum value (OK, WARNING, ERROR, UNKNOWN).
        """
        ...

    @abstractmethod
    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute an action with permission tier enforcement.

        Must be implemented by subclasses. The implementation must:
        1. Verify the action is allowed for the given tier
        2. Check consent if tier >= L2
        3. Check HARD STOP if tier >= L2
        4. Execute the action
        5. Return structured result

        Args:
            action: Action name (e.g., "send_message", "create_issue").
            tier: Permission tier required for this action.
            project_id: Optional project UUID for scoping.
            **kwargs: Action-specific parameters.

        Returns:
            Dict with at least: {"success": bool, "action": str, ...}

        Raises:
            PermissionError: If tier is L4 or consent/HARD STOP blocks.
            NotImplementedError: If action is not supported.
        """
        ...

    async def check_status(self) -> IntegrationStatus:
        """Update and return the current runtime status.

        Performs a health check and updates internal status based on:
        - Health check result
        - Consent status (if applicable)
        - HARD STOP flag (if applicable)

        Returns:
            Updated IntegrationStatus enum value.
        """
        health = await self.health_check()
        self._last_health_check = datetime.now(timezone.utc)

        if health == IntegrationHealth.OK:
            self._status = IntegrationStatus.HEALTHY
        elif health == IntegrationHealth.ERROR:
            self._status = IntegrationStatus.DEGRADED
        elif health == IntegrationHealth.WARNING:
            self._status = IntegrationStatus.DEGRADED
        elif health == IntegrationHealth.UNKNOWN:
            # UNKNOWN = client not wired / credentials absent. Honest
            # CONFIG_MISSING — never collapse into HEALTHY (would be fake PASS).
            self._status = IntegrationStatus.CONFIG_MISSING
        else:
            self._status = IntegrationStatus.DISABLED

        return self._status

    def get_audit_context(self) -> dict[str, Any]:
        """Return context for audit logging.

        Returns:
            Dict with integration metadata for audit trail.
        """
        return {
            "integration_id": self.integration_id,
            "provider": self._config.provider,
            "status": self._status.value,
            "capabilities": [c.value for c in self._config.capabilities],
            "default_tier": self._config.default_tier.name,
            "last_health_check": (
                self._last_health_check.isoformat()
                if self._last_health_check
                else None
            ),
        }

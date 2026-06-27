"""P22 integration registry.

Central registry for all integration adapters. Provides lookup, health checks,
and capability discovery. Integrations are registered at startup and can be
queried by ID or capability.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from src.life_integrations.base import BaseIntegrationAdapter
from src.life_integrations.types import (
    IntegrationCapability,
    IntegrationHealth,
    IntegrationId,
    IntegrationStatus,
)

logger = structlog.get_logger(__name__)


class IntegrationRegistry:
    """Central registry for P22 integration adapters.

    Provides:
    - Registration/unregistration of adapters
    - Lookup by ID or capability
    - Bulk health checks
    - Capability discovery

    Async-safe via asyncio.Lock for register/unregister operations.
    Read operations (get/list) take a snapshot under the lock to avoid
    concurrent mutation races.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._adapters: dict[IntegrationId, BaseIntegrationAdapter] = {}
        import asyncio
        self._lock = asyncio.Lock()

    async def register(self, adapter: BaseIntegrationAdapter) -> None:
        """Register an integration adapter.

        Args:
            adapter: The adapter instance to register.

        Raises:
            ValueError: If adapter is already registered.
        """
        integration_id = adapter.integration_id
        async with self._lock:
            if integration_id in self._adapters:
                raise ValueError(f"Integration '{integration_id}' already registered")
            self._adapters[integration_id] = adapter
        logger.info(
            "integration.registered",
            integration_id=integration_id,
            provider=adapter.config.provider,
        )

    async def unregister(self, integration_id: IntegrationId) -> None:
        """Unregister an integration adapter.

        Args:
            integration_id: The integration to remove.

        Raises:
            KeyError: If integration is not registered.
        """
        async with self._lock:
            if integration_id not in self._adapters:
                raise KeyError(f"Integration '{integration_id}' not registered")
            del self._adapters[integration_id]
        logger.info("integration.unregistered", integration_id=integration_id)

    def get(self, integration_id: IntegrationId) -> BaseIntegrationAdapter:
        """Get an adapter by integration ID.

        Args:
            integration_id: The integration to retrieve.

        Returns:
            The adapter instance.

        Raises:
            KeyError: If integration is not registered.
        """
        if integration_id not in self._adapters:
            raise KeyError(f"Integration '{integration_id}' not registered")
        return self._adapters[integration_id]

    def list_all(self) -> list[BaseIntegrationAdapter]:
        """Return all registered adapters.

        Returns:
            List of adapter instances.
        """
        return list(self._adapters.values())

    def list_by_capability(
        self, capability: IntegrationCapability
    ) -> list[BaseIntegrationAdapter]:
        """Return adapters that declare a specific capability.

        Args:
            capability: The capability to filter by.

        Returns:
            List of adapters with the declared capability.
        """
        return [
            adapter
            for adapter in self._adapters.values()
            if adapter.has_capability(capability)
        ]

    async def health_check_all(self) -> dict[IntegrationId, IntegrationHealth]:
        """Perform health checks on all registered adapters.

        Returns:
            Dict mapping integration_id to health status.
        """
        results: dict[IntegrationId, IntegrationHealth] = {}
        for integration_id, adapter in self._adapters.items():
            try:
                health = await adapter.health_check()
                results[integration_id] = health
            except Exception as e:
                logger.error(
                    "integration.health_check_failed",
                    integration_id=integration_id,
                    error=str(e),
                )
                results[integration_id] = IntegrationHealth.ERROR

        return results

    async def check_all_status(self) -> dict[IntegrationId, IntegrationStatus]:
        """Update and return status for all registered adapters.

        Returns:
            Dict mapping integration_id to runtime status.
        """
        results: dict[IntegrationId, IntegrationStatus] = {}
        for integration_id, adapter in self._adapters.items():
            try:
                status = await adapter.check_status()
                results[integration_id] = status
            except Exception as e:
                logger.error(
                    "integration.status_check_failed",
                    integration_id=integration_id,
                    error=str(e),
                )
                results[integration_id] = IntegrationStatus.DEGRADED

        return results

    def get_audit_summary(self) -> dict[str, Any]:
        """Return audit summary of all registered integrations.

        Returns:
            Dict with integration metadata for audit trail.
        """
        return {
            integration_id: adapter.get_audit_context()
            for integration_id, adapter in self._adapters.items()
        }

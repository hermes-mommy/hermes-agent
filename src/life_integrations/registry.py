"""P22 integration registry.

Central registry for all integration adapters. Provides lookup, health checks,
and capability discovery. Integrations are registered at startup and can be
queried by ID or capability.
"""

from __future__ import annotations

import asyncio
import threading
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

    Writes (register/unregister) are async under both asyncio.Lock and
    threading.Lock to serialize mutation. Reads (get/list_all/
    list_by_capability/get_audit_summary) are sync and snapshot under
    threading.Lock to prevent concurrent-mutation races. Callers may call
    reads without `await` and will receive a consistent snapshot.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._adapters: dict[IntegrationId, BaseIntegrationAdapter] = {}
        self._lock = asyncio.Lock()
        # F23: sync-readers (get/list_all/...) take a snapshot under this
        # non-blocking threading.Lock; writers hold it briefly around the
        # dict mutation so readers never observe a half-mutated state.
        self._read_lock = threading.Lock()
        # A5: runtime checkers for capability_matrix (None = fail-closed).
        self._consent_checker: Any = None
        self._hard_stop_checker: Any = None

    def set_runtime_checkers(
        self,
        consent_checker: Any = None,
        hard_stop_checker: Any = None,
    ) -> None:
        """Inject consent + hard-stop checkers for capability_matrix (A5)."""
        self._consent_checker = consent_checker
        self._hard_stop_checker = hard_stop_checker

    async def capability_matrix(
        self,
    ) -> "dict[IntegrationId, dict[str, tuple[Any, Any]]]":
        """Per-adapter x per-action readiness matrix (A5). Never fakes HEALTHY."""
        from src.life_integrations.permissions import SemanticActionClassifier

        matrix: dict[IntegrationId, dict[str, tuple[Any, Any]]] = {}
        classifier = SemanticActionClassifier()
        for integration_id, adapter in self._adapters.items():
            actions_map: dict[str, tuple[Any, Any]] = {}
            for action in adapter._known_actions():
                classification = classifier.classify(
                    provider=integration_id, action=action,
                )
                status = await adapter._resolve_runtime_status(
                    action,
                    classification.tier,
                    consent_checker=self._consent_checker,
                    hard_stop_checker=self._hard_stop_checker,
                )
                actions_map[action] = (classification.tier, status)
            matrix[integration_id] = actions_map
        return matrix

    async def register(self, adapter: BaseIntegrationAdapter) -> None:
        """Register an integration adapter.

        Args:
            adapter: The adapter instance to register.

        Raises:
            ValueError: If adapter is already registered.
        """
        integration_id = adapter.integration_id
        async with self._lock:
            with self._read_lock:
                if integration_id in self._adapters:
                    raise ValueError(
                        f"Integration '{integration_id}' already registered"
                    )
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
            with self._read_lock:
                if integration_id not in self._adapters:
                    raise KeyError(
                        f"Integration '{integration_id}' not registered"
                    )
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
        with self._read_lock:
            if integration_id not in self._adapters:
                raise KeyError(
                    f"Integration '{integration_id}' not registered"
                )
            return self._adapters[integration_id]

    def list_all(self) -> list[BaseIntegrationAdapter]:
        """Return all registered adapters.

        Returns:
            List of adapter instances (snapshot at call time).
        """
        with self._read_lock:
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
        with self._read_lock:
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
        with self._read_lock:
            return {
                integration_id: adapter.get_audit_context()
                for integration_id, adapter in self._adapters.items()
            }

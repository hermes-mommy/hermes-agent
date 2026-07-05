"""P22 scheduler — background integration health polling.

Runs periodic health checks on all registered integrations. Non-blocking,
respects HARD STOP, and integrates with P20's heartbeat awareness cycle
(30s hook) without modifying P20 closed files.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from guinevere.life_integrations.registry import IntegrationRegistry
from guinevere.life_integrations.types import IntegrationHealth, IntegrationStatus

logger = structlog.get_logger(__name__)


class IntegrationScheduler:
    """Background health-check scheduler for P22 integrations.

    Runs a periodic loop that:
    1. Checks health of all registered integrations
    2. Updates runtime status
    3. Logs status changes
    4. Respects cancellation (HARD STOP)

    Does NOT modify P20 heartbeat.py — runs as an independent async task
    that P20's 30s awareness hook can query.
    """

    def __init__(
        self,
        registry: IntegrationRegistry,
        interval_seconds: int = 30,
    ) -> None:
        """Initialize the scheduler.

        Args:
            registry: Integration registry to poll.
            interval_seconds: Health check interval (default 30s, matches P20).
        """
        self._registry = registry
        self._interval = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_status: dict[str, IntegrationStatus] = {}

    async def start(self) -> None:
        """Start the background health-check loop."""
        if self._running:
            logger.warning("scheduler.already_running")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("scheduler.started", interval=self._interval)

    async def stop(self) -> None:
        """Stop the background loop gracefully."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("scheduler.stopped")

    async def _loop(self) -> None:
        """Main health-check loop."""
        while self._running:
            try:
                await self._check_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("scheduler.loop_error", error=str(e))

            await asyncio.sleep(self._interval)

    async def _check_once(self) -> None:
        """Perform one round of health checks."""
        statuses = await self._registry.check_all_status()

        # Log status changes
        for integration_id, status in statuses.items():
            prev = self._last_status.get(integration_id)
            if prev != status:
                logger.info(
                    "scheduler.status_change",
                    integration_id=integration_id,
                    previous=prev.value if prev else None,
                    current=status.value,
                )
                self._last_status[integration_id] = status

    def get_status_summary(self) -> dict[str, str]:
        """Return a snapshot of all integration statuses.

        Returns:
            Dict mapping integration_id to status string.
        """
        return {
            iid: status.value for iid, status in self._last_status.items()
        }

    async def check_once_now(self) -> dict[str, IntegrationHealth]:
        """Perform an immediate health check (for P20 30s hook).

        Returns:
            Dict mapping integration_id to health status.
        """
        return await self._registry.health_check_all()

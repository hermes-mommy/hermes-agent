"""Environment Monitor — service health and system resource monitoring.

P5-025: Monitors service health (Redis, PostgreSQL, 9Router, Discord) and
system resources (CPU, memory, disk) to drive 4-level graceful degradation.
"""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import Callable


logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Service health constants
# ---------------------------------------------------------------------------
REDIS_HOST = "localhost"
REDIS_PORT = 6380
REDIS_DB = 2

POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5433

N9ROUTER_HOST = "localhost"
N9ROUTER_PORT = 20128


@dataclass(frozen=True)
class ServiceStatus:
    """Immutable status of a single service."""

    name: str
    healthy: bool
    latency_ms: float | None
    error: str | None


@dataclass(frozen=True)
class SystemResources:
    """Immutable snapshot of system resource usage."""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_loops: int


@dataclass(frozen=True)
class EnvironmentSnapshot:
    """Immutable snapshot of entire environment state."""

    timestamp: datetime
    services: list[ServiceStatus]
    resources: SystemResources
    degradation_level: int  # 0=full, 1=minor, 2=major, 3=critical


class EnvironmentMonitor:
    """Monitors service health and system resources.

    Checks services every 60 seconds by default, updates degradation level
    based on health and resource usage, and caches last snapshot for fast
    reads by Discord commands.

    Degradation levels:
        0 = All services healthy, resources normal
        1 = Non-critical service down, resources >70%
        2 = Critical service degraded, resources >85%
        3 = Multiple critical services down, resources >95%
    """

    def __init__(self, check_interval: int = 60) -> None:
        """Initialize environment monitor.

        Args:
            check_interval: Seconds between health checks (default: 60).
        """
        self.check_interval = check_interval
        self._last_snapshot: EnvironmentSnapshot | None = None
        self._lock = asyncio.Lock()

    async def check_all(self) -> EnvironmentSnapshot:
        """Run full environment health check.

        Returns:
            EnvironmentSnapshot with service health, resources, and
            calculated degradation level.
        """
        async with self._lock:
            logger.info("environment_check_starting")

            # 1. Check service health
            services = await self._check_services()

            # 2. Check system resources
            resources = self._check_system_resources()

            # 3. Calculate degradation level
            degradation = self._calculate_degradation(services, resources)

            snapshot = EnvironmentSnapshot(
                timestamp=datetime.now(),
                services=services,
                resources=resources,
                degradation_level=degradation,
            )

            self._last_snapshot = snapshot
            logger.info(
                "environment_check_complete",
                degradation_level=degradation,
                healthy_services=sum(1 for s in services if s.healthy),
                total_services=len(services),
                cpu=resources.cpu_percent,
                memory=resources.memory_percent,
                disk=resources.disk_percent,
            )

            return snapshot

    async def check_service(self, name: str, host: str, port: int) -> ServiceStatus:
        """Check single TCP service health.

        Args:
            name: Service name for logging.
            host: Hostname or IP address.
            port: Port number to check.

        Returns:
            ServiceStatus with healthy flag and latency.
        """
        start_time = asyncio.get_event_loop().time()
        try:
            # Use asyncio.open_connection for non-blocking TCP check
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0,
            )
            writer.close()
            await writer.wait_closed()

            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            logger.debug("service_check_passed", service=name, latency_ms=latency_ms)
            return ServiceStatus(name=name, healthy=True, latency_ms=latency_ms, error=None)

        except asyncio.TimeoutError:
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.warning("service_check_timeout", service=name, latency_ms=latency_ms)
            return ServiceStatus(name=name, healthy=False, latency_ms=latency_ms, error="timeout")

        except Exception as exc:
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.warning("service_check_failed", service=name, latency_ms=latency_ms, error=str(exc))
            return ServiceStatus(name=name, healthy=False, latency_ms=latency_ms, error=str(exc))

    async def _check_services(self) -> list[ServiceStatus]:
        """Check all services concurrently.

        Services to check:
            - Redis (DB2, localhost:6380)
            - PostgreSQL (localhost:5433)
            - 9Router (localhost:20128)
            - Discord (requires bot.is_ready() if available)

        Returns:
            List of ServiceStatus for all services.
        """
        # Get bot instance if available for Discord check
        bot = self._get_discord_bot()

        # Run all service checks in parallel
        tasks = [
            self.check_service("redis", REDIS_HOST, REDIS_PORT),
            self.check_service("postgresql", POSTGRES_HOST, POSTGRES_PORT),
            self.check_service("9router", N9ROUTER_HOST, N9ROUTER_PORT),
        ]

        if bot is not None:
            tasks.append(self._check_discord_service(bot))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return only valid results
        services: list[ServiceStatus] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("service_check_exception", error=str(result))
                continue
            if isinstance(result, ServiceStatus):
                services.append(result)

        return services

    async def _check_discord_service(self, bot: object) -> ServiceStatus:
        """Check Discord bot readiness.

        Args:
            bot: Discord bot instance with is_ready() method.

        Returns:
            ServiceStatus for Discord service.
        """
        try:
            # Check if bot is ready
            is_ready = getattr(bot, "is_ready", lambda: False)()
            if is_ready:
                return ServiceStatus(name="discord", healthy=True, latency_ms=None, error=None)
            else:
                return ServiceStatus(name="discord", healthy=False, latency_ms=None, error="not_ready")
        except Exception as exc:
            return ServiceStatus(name="discord", healthy=False, latency_ms=None, error=str(exc))

    def _check_system_resources(self) -> SystemResources:
        """Check system resource usage.

        Uses psutil for CPU, memory, and disk metrics.
        Gracefully falls back if psutil is not available.

        Returns:
            SystemResources snapshot.
        """
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent

            # Get active loop count from LoopManager if available
            active_loops = self._get_active_loop_count()

            return SystemResources(
                cpu_percent=cpu,
                memory_percent=memory,
                disk_percent=disk,
                active_loops=active_loops,
            )
        except ImportError:
            logger.warning("psutil_not_available", error="psutil not installed")
            return SystemResources(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                active_loops=0,
            )
        except Exception as exc:
            logger.error("system_resources_check_failed", error=str(exc))
            return SystemResources(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                active_loops=0,
            )

    def _calculate_degradation(
        self,
        services: list[ServiceStatus],
        resources: SystemResources,
    ) -> int:
        """Calculate 4-level degradation level.

        Rules:
            0 = All services healthy, resources <=70%
            1 = Non-critical service down, resources >70%
            2 = Critical service degraded, resources >85%
            3 = Multiple critical services down, resources >95%

        Args:
            services: List of service status.
            resources: System resource usage.

        Returns:
            Degradation level (0-3).
        """
        # Critical services: postgresql, 9router
        # Non-critical: redis, discord
        critical_services = [s for s in services if s.name in ["postgresql", "9router"]]
        non_critical_services = [s for s in services if s.name in ["redis", "discord"]]

        critical_healthy = sum(1 for s in critical_services if s.healthy)
        non_critical_healthy = sum(1 for s in non_critical_services if s.healthy)

        # Determine degradation level
        if resources.memory_percent > 95:
            return 3  # Critical resources, ignore service health

        if critical_healthy < len(critical_services) and resources.memory_percent > 85:
            return 2  # Critical service degraded + high resources

        if non_critical_healthy < len(non_critical_services) and resources.memory_percent > 70:
            return 1  # Non-critical service down + high resources

        if critical_healthy < len(critical_services):
            return 2  # Critical service down, resources normal

        if non_critical_healthy < len(non_critical_services):
            return 1  # Non-critical service down, resources normal

        return 0  # All healthy, resources normal

    def _get_active_loop_count(self) -> int:
        """Get count of active loops from LoopManager.

        Returns:
            Number of active loops, or 0 if unavailable.
        """
        try:
            from guinevere.loops.manager import LoopManager

            # Try to get loop_manager from app state (assumes this method is called
            # from FastAPI app context)
            loop_manager = self._get_loop_manager()
            if loop_manager is not None:
                loops = loop_manager.list_loops()
                return len(loops)

            return 0
        except Exception as exc:
            logger.debug("active_loop_count_unavailable", error=str(exc))
            return 0

    def _get_loop_manager(self) -> object | None:
        """Get LoopManager instance.

        This is a placeholder that should be wired from FastAPI app state
        in production. Returns None if not available.

        Returns:
            LoopManager instance or None.
        """
        try:
            # In production, this would be accessed via app.state.loop_manager
            # For now, return None to avoid import errors
            return None
        except Exception:
            return None

    def _get_discord_bot(self) -> object | None:
        """Get Discord bot instance.

        This is a placeholder that should be wired from FastAPI app state
        in production. Returns None if not available.

        Returns:
            Discord bot instance or None.
        """
        try:
            # In production, this would be accessed via app.state.discord_bot
            # For now, return None to avoid import errors
            return None
        except Exception:
            return None

    def get_last_snapshot(self) -> EnvironmentSnapshot | None:
        """Get cached last snapshot.

        Returns:
            Last EnvironmentSnapshot or None if not yet initialized.
        """
        return self._last_snapshot
"""VPS/system health integration adapter.

Wraps existing docker_tool.py + shell_tool.py for system health metrics,
service status, and container management with L1-L4 tiers.

Secrets: sec-postgres-core, sec-redis-auth (existing)
Consent: consent.ops.vps.{read,write,delete}
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

# Allowlist of systemd service names — prevents shell injection via the
# `service` argument. Only guinevere-* services + core infra are restartable.
_ALLOWED_SERVICES = frozenset({
    "guinevere-core", "guinevere-discord", "guinevere-9router",
    "guinevere-loops", "guinevere-scheduler", "guinevere-mcp",
    "guinevere-surveillance", "guinevere-monitoring",
    "guinevere-wearable-sync", "guinevere-wearable-analysis",
    "guinevere-health", "postgresql", "redis", "pgbouncer",
    "caddy", "tailscaled", "cloudflared",
})


def _validate_service_name(service: str) -> str:
    """Validate a systemd service name against the allowlist.

    Args:
        service: Service name to validate.

    Returns:
        The validated service name.

    Raises:
        PermissionDeniedError: If service is not in the allowlist (shell
            injection prevention).
    """
    from src.life_integrations.errors import PermissionDeniedError
    # Reject any service with shell metacharacters or spaces
    if not service or not service.replace("-", "").replace("_", "").isalnum():
        raise PermissionDeniedError(
            f"invalid service name (shell injection risk): {service!r}"
        )
    if service not in _ALLOWED_SERVICES:
        raise PermissionDeniedError(
            f"service '{service}' not in allowlist — restart denied"
        )
    return service


class VPSIntegrationAdapter(BaseIntegrationAdapter):
    """VPS/system health integration adapter.

    Actions:
        list_containers (L1): List running Docker containers
        container_logs (L1): Get container logs
        service_status (L1): systemctl status for a service
        health_metrics (L1): CPU/memory/disk metrics
        restart_container (L2): Restart a container
        restart_service (L2/L3): Restart systemd service (L3 if stateful)
        remove_container (L3): Remove a container (pre-commit snapshot)
        system_prune (L4): FORBIDDEN
    """

    def __init__(
        self,
        docker_client: Any | None = None,
        shell_client: Any | None = None,
    ) -> None:
        """Initialize with optional Docker and shell clients.

        Args:
            docker_client: Docker client wrapper (None = CONFIG_MISSING).
            shell_client: Shell client wrapper (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="vps",
            name="VPS System Health",
            provider="Docker/Systemd",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
                IntegrationCapability.EXECUTE,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-postgres-core", "sec-redis-auth"),
            consent_scopes=(
                "consent.ops.vps.read",
                "consent.ops.vps.write",
                "consent.ops.vps.delete",
            ),
            risk_tier="high",
        )
        super().__init__(config)
        self._docker = docker_client
        self._shell = shell_client

    async def health_check(self) -> IntegrationHealth:
        """Check VPS connectivity."""
        if self._docker is None and self._shell is None:
            return IntegrationHealth.UNKNOWN
        return IntegrationHealth.OK

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a VPS action."""
        action_lower = action.lower()

        if action_lower == "list_containers":
            if self._docker is None:
                raise ConfigurationMissingError("Docker client not configured")
            containers = await self._docker.list_containers()
            return {"success": True, "action": action, "containers": containers}

        if action_lower == "service_status":
            if self._shell is None:
                raise ConfigurationMissingError("Shell client not configured")
            service = kwargs.get("service", "")
            _validate_service_name(service)
            status = await self._shell.run(f"systemctl status {service}")
            return {"success": True, "action": action, "status": status}

        if action_lower == "health_metrics":
            metrics = await self._get_health_metrics()
            return {"success": True, "action": action, "metrics": metrics}

        if action_lower == "restart_service":
            if self._shell is None:
                raise ConfigurationMissingError("Shell client not configured")
            service = kwargs.get("service", "")
            _validate_service_name(service)
            # Stateful services (postgres, redis) require L3
            stateful = service in ("postgresql", "redis", "pgbouncer")
            if stateful and tier < PermissionTier.L3_DESTRUCTIVE:
                return {
                    "success": False,
                    "action": action,
                    "error": f"restart of stateful service '{service}' requires L3",
                }
            await self._shell.run(f"systemctl restart {service}")
            return {"success": True, "action": action, "service": service}

        if action_lower in ("system_prune", "docker_rm_all"):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — never autonomous"
            )

        raise ActionNotSupportedError(
            f"VPS adapter does not support action: {action}"
        )

    async def _get_health_metrics(self) -> dict[str, Any]:
        """Get CPU/memory/disk health metrics."""
        import shutil
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = shutil.disk_usage("/")
        return {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_available_mb": mem.available / (1024 * 1024),
            "disk_percent": disk.used / disk.total * 100,
            "disk_free_gb": disk.free / (1024 ** 3),
        }

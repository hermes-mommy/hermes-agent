"""VPS/system health integration adapter.

Wraps existing docker_tool.py + shell_tool.py for system health metrics,
service status, and container management with L1-L4 tiers.

Secrets: sec-postgres-core, sec-redis-auth (existing)
Consent: consent.ops.vps.{read,write,delete}

P22.3 adds:
  * ``restart_container`` (L2) — delegates to docker_client.restart_container.
  * ``remove_container`` (L3) — pre-delete ``docker commit`` snapshot
    before invoking docker_client.remove_container. The snapshot is
    the ONLY recovery path because ``docker rm`` is irreversible on
    running state. A failed commit still triggers the delete, but the
    snapshot dict is recorded and ``reversible`` is honest (False).
  * ``system_prune`` / ``docker_rm_all`` remain L4 FORBIDDEN.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
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

# Container-name alphabet for restart/remove. Matches docker_tool's
# _CONTAINER_NAME_RE but enforced here too so the adapter rejects hostile
# input even if the shim is mocked out.
_CONTAINER_NAME_RE_STR = r"^[a-zA-Z0-9][a-zA-Z0-9_.\-]*$"


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


def _validate_container_id(container_id: str) -> str:
    """Validate a container identifier (name or short ID).

    Args:
        container_id: Container id/name to validate.

    Returns:
        The validated container id.

    Raises:
        PermissionDeniedError: If container_id does not match the safe name
            alphabet (defence in depth — primary guard is the docker_tool).
    """
    import re

    from src.life_integrations.errors import PermissionDeniedError

    if not container_id or not re.match(_CONTAINER_NAME_RE_STR, container_id):
        raise PermissionDeniedError(
            f"invalid container_id (shell injection risk): {container_id!r}"
        )
    return container_id


def _snapshot_content_hash(
    container_id: str,
    image_id: str,
    snapshot_image: str | None,
    captured_at: _dt.datetime,
) -> str:
    """Compute a SHA-256 hex digest for the pre-delete snapshot.

    The hash is deterministic given the inputs (container_id, image_id,
    snapshot image ID if committed, and the ISO-8601 timestamp the adapter
    recorded at snapshot time). 64-hex character digest.

    Args:
        container_id: Container ID the snapshot belongs to.
        image_id: Image id from ``docker inspect`` (``Config.Image``).
        snapshot_image: Snapshot image id (``None`` if commit failed).
        captured_at: Adapter-recorded snapshot timestamp.

    Returns:
        64-character lowercase hex SHA-256 digest.
    """
    payload = "|".join([
        str(container_id),
        str(image_id or ""),
        str(snapshot_image or ""),
        captured_at.isoformat(),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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

        if action_lower == "restart_container":
            # L2 (and higher) allowed. L1 must NOT silently restart.
            container_id = kwargs.get("container_id", "")
            if not container_id:
                raise ConfigurationMissingError(
                    "container_id is required for restart_container"
                )
            if self._docker is None:
                raise ConfigurationMissingError(
                    "Docker client not configured for restart_container"
                )
            _validate_container_id(container_id)
            await self._docker.restart_container(container_id)
            return {
                "success": True,
                "action": action,
                "container_id": container_id,
                "restarted": True,
                "reversible": True,
            }

        if action_lower == "remove_container":
            # L3 minimum (destructive). Pre-delete docker commit snapshot is
            # the ONLY recovery path because docker rm is irreversible on
            # running state. A failed commit still triggers the delete,
            # but the snapshot dict is recorded and ``reversible`` is False.
            container_id = kwargs.get("container_id", "")
            if not container_id:
                raise ConfigurationMissingError(
                    "container_id is required for remove_container"
                )
            if self._docker is None:
                raise ConfigurationMissingError(
                    "Docker client not configured for remove_container"
                )
            _validate_container_id(container_id)

            # Snapshot step (load-bearing order): get_container FIRST to
            # capture the source image_id, THEN commit to capture the
            # filesystem state of the running container, THEN remove.
            inspect = await self._docker.get_container(container_id)
            image_id = ""
            try:
                image_id = str(inspect.get("Config", {}).get("Image", "") or "")
            except (AttributeError, TypeError):
                image_id = ""

            captured_at = _dt.datetime.now(_dt.timezone.utc)
            commit_result = await self._docker.commit(container_id)
            committed = bool(commit_result.get("committed", False))
            snapshot_image = (
                str(commit_result.get("image_id", "") or "")
                if committed
                else None
            )

            content_hash = _snapshot_content_hash(
                container_id=container_id,
                image_id=image_id,
                snapshot_image=snapshot_image,
                captured_at=captured_at,
            )

            snapshot: dict[str, Any] = {
                "method": "docker commit",
                "committed": committed,
                "snapshot_image": snapshot_image,
                "image_id": image_id,
                "content_hash": content_hash,
                "captured_at": captured_at.isoformat(),
                "stderr": str(commit_result.get("stderr", "") or ""),
            }

            # Now (and only now) remove the container.
            await self._docker.remove_container(container_id)

            if committed:
                return {
                    "success": True,
                    "action": action,
                    "container_id": container_id,
                    "image_id": image_id,
                    "snapshot_image": snapshot_image,
                    "content_hash": content_hash,
                    "reversible": True,
                    "restore_method": "docker pull + docker run from image",
                    "restore_possible": True,
                    "irreversible_warning": False,
                    "pre_delete_snapshot": snapshot,
                }
            # Commit failed — delete still happened, but restore is
            # impossible. Adapter must NOT lie about reversibility.
            return {
                "success": True,
                "action": action,
                "container_id": container_id,
                "image_id": image_id,
                "snapshot_image": None,
                "content_hash": content_hash,
                "reversible": False,
                "restore_method": (
                    "commit failed — restore not possible via docker pull + "
                    "docker run from image"
                ),
                "restore_possible": False,
                "irreversible_warning": True,
                "pre_delete_snapshot": snapshot,
            }

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

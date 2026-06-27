"""P22 project context — P19 namespace propagation.

Wraps P19's ProjectRegistry to provide project_id resolution for all
P22 integration actions. Every action carries project_id for scoping.

Uses identifier template: p22:<domain>:<provider>:<resource-id>
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)

# Default project UUID (matches P19 canonical default)
DEFAULT_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class ProjectRegistryProtocol(Protocol):
    """Protocol for P19 ProjectRegistry (minimal surface)."""

    async def get(self, project_id: uuid.UUID) -> Any: ...
    async def resolve(self, slug: str) -> Any: ...
    async def list_active(self) -> list[Any]: ...


class ProjectContext:
    """Project context resolver for P22 integration actions.

    Provides:
    - Default project fallback (DEFAULT_PROJECT_ID)
    - Slug-to-UUID resolution via P19 registry
    - Resource identifier construction (p22:<domain>:<provider>:<id>)

    Usage:
        ctx = ProjectContext(registry=p19_registry)
        project_id = await ctx.resolve_or_default("guinevere")
        resource_id = ctx.build_resource_id("calendar", "google", "primary")
    """

    def __init__(self, registry: ProjectRegistryProtocol | None = None) -> None:
        """Initialize with optional P19 registry.

        Args:
            registry: P19 ProjectRegistry (optional). If None, all actions
                use DEFAULT_PROJECT_ID (legacy single-project mode).
        """
        self._registry = registry

    @property
    def default_project_id(self) -> uuid.UUID:
        """Return the canonical default project UUID."""
        return DEFAULT_PROJECT_ID

    async def resolve_or_default(
        self, slug_or_id: str | uuid.UUID | None
    ) -> uuid.UUID:
        """Resolve a slug/UUID to project_id, falling back to default.

        Args:
            slug_or_id: Project slug (str), UUID, or None for default.

        Returns:
            Resolved project UUID (or DEFAULT_PROJECT_ID if unresolved).
        """
        if slug_or_id is None:
            return DEFAULT_PROJECT_ID

        if isinstance(slug_or_id, uuid.UUID):
            return slug_or_id

        # Try to parse as UUID string
        try:
            return uuid.UUID(slug_or_id)
        except (ValueError, AttributeError):
            pass

        # Resolve as slug via P19 registry
        if self._registry is not None:
            try:
                project = await self._registry.resolve(slug_or_id)
                return project.project_id
            except Exception as e:
                logger.warning(
                    "project_context.resolve_failed",
                    slug=slug_or_id,
                    error=str(e),
                )

        return DEFAULT_PROJECT_ID

    def build_resource_id(
        self,
        domain: str,
        provider: str,
        resource_id: str,
        project_slug: str | None = None,
    ) -> str:
        """Build a P22 namespace-qualified resource identifier.

        Format: [<project>:]p22:<domain>:<provider>:<resource-id>

        Args:
            domain: Integration domain (calendar, tasks, notes, comms).
            provider: Provider name (google, github, notion).
            resource_id: Resource identifier (primary, daily-journal).
            project_slug: Optional project slug prefix (post-P19).

        Returns:
            Namespace-qualified resource identifier.
        """
        base = f"p22:{domain}:{provider}:{resource_id}"
        if project_slug and project_slug != "default":
            return f"{project_slug}:{base}"
        return base

    async def log_namespace_switch(
        self,
        from_namespace: str,
        to_namespace: str,
        actor: str = "agent:guinevere",
    ) -> dict[str, Any]:
        """Log a namespace switch event (audit requirement).

        Args:
            from_namespace: Previous namespace.
            to_namespace: New namespace.
            actor: Who initiated the switch.

        Returns:
            Dict with switch metadata for audit trail.
        """
        correlation_id = str(uuid.uuid4())
        logger.info(
            "project.namespace_switch",
            from_namespace=from_namespace,
            to_namespace=to_namespace,
            actor=actor,
            correlation_id=correlation_id,
        )
        return {
            "from_namespace": from_namespace,
            "to_namespace": to_namespace,
            "actor": actor,
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

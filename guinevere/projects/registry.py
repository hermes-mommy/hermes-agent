"""ProjectRegistry — central service for project lifecycle management.

The registry is a **pure data service**: it validates operations and
produces audit events but does **not** enforce authentication (auth is
applied at the Discord command layer, P19-007).

Usage::

    registry = ProjectRegistry(store=my_store, audit_writer=my_writer)
    pid = await registry.create("my-project", name="My Project")
    project = await registry.get(pid)
    projects = await registry.list()
    await registry.archive(pid, audit_writer=my_writer)

Design notes
------------
* Every ``create`` and ``archive`` call produces an audit event via the
  injected ``audit_writer`` callback, making the registry testable without
  a live database.
* The registry supports an in-memory store for unit tests (see
  :class:`InMemoryProjectStore`) so tests never need Postgres.
* The ``default`` project (UUID ``00000000-0000-0000-0000-000000000001``)
  is seeded at construction time and cannot be archived.
"""

from __future__ import annotations

import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from guinevere.projects.exceptions import (
    InvalidProjectSlugError,
    ProjectAlreadyExistsError,
    ProjectArchivedError,
    ProjectNotFoundError,
)
from guinevere.projects.types import Project, ProjectId, ProjectScope, ProjectStatus

# ── Default project UUID ──────────────────────────────────────────────

_DEFAULT_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
"""Fixed UUID for the canonical default project."""

# ── Slug validation ───────────────────────────────────────────────────

_SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9_-]{0,62}[a-z0-9])?$")
"""Slug must be lowercase alphanumeric with hyphens/underscores, 1-64 chars."""


def _validate_slug(slug: str) -> None:
    if not _SLUG_PATTERN.match(slug):
        raise InvalidProjectSlugError(slug)


# ── Audit writer protocol ─────────────────────────────────────────────


class AuditWriter(Protocol):
    """Protocol for the audit-writer dependency.

    The registry calls ``write_event`` on every mutating operation so that
    audit events are produced regardless of the underlying store.  Tests
    can provide a mock that records calls instead of writing to Postgres.
    """

    async def write_event(
        self,
        event_type: str,
        loop_id: str,
        data: dict[str, Any],
    ) -> Any: ...


# ── Abstract store ────────────────────────────────────────────────────


class ProjectStore(ABC):
    """Abstract persistence layer for the project registry.

    Implementations can back onto PostgreSQL (production), in-memory dicts
    (unit tests), or SQLite (integration tests).
    """

    @abstractmethod
    async def create(self, project: Project) -> None: ...

    @abstractmethod
    async def get(self, project_id: ProjectId) -> Project | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Project | None: ...

    @abstractmethod
    async def list_all(self) -> list[Project]: ...

    @abstractmethod
    async def update(self, project: Project) -> None: ...

    @abstractmethod
    async def delete(self, project_id: ProjectId) -> None: ...


# ── In-memory store (for tests / dev) ─────────────────────────────────


class InMemoryProjectStore(ProjectStore):
    """Store that keeps projects in a plain dict.

    Useful for unit tests and local development without Postgres.
    """

    def __init__(self) -> None:
        self._projects: dict[ProjectId, Project] = {}
        self._slugs: dict[str, ProjectId] = {}

    async def create(self, project: Project) -> None:
        self._projects[project.project_id] = project
        self._slugs[project.slug] = project.project_id

    async def get(self, project_id: ProjectId) -> Project | None:
        return self._projects.get(project_id)

    async def get_by_slug(self, slug: str) -> Project | None:
        pid = self._slugs.get(slug)
        if pid is None:
            return None
        return self._projects.get(pid)

    async def list_all(self) -> list[Project]:
        return list(self._projects.values())

    async def update(self, project: Project) -> None:
        self._projects[project.project_id] = project
        self._slugs[project.slug] = project.project_id

    async def delete(self, project_id: ProjectId) -> None:
        proj = self._projects.pop(project_id, None)
        if proj is not None:
            self._slugs.pop(proj.slug, None)


# ── Registry ──────────────────────────────────────────────────────────


class ProjectRegistry:
    """Central project lifecycle service.

    Parameters
    ----------
    store:
        Persistence backend (``InMemoryProjectStore`` for tests, SQLAlchemy
        store for production — the latter is introduced in P19-003).
    audit_writer:
        Callable that writes an audit event on every mutating operation.
        Must satisfy the :class:`AuditWriter` protocol.
    """

    DEFAULT_PROJECT_ID: ProjectId = _DEFAULT_PROJECT_ID
    """Fixed UUID for the canonical ``default`` project."""

    def __init__(
        self,
        store: ProjectStore,
        audit_writer: AuditWriter | None = None,
    ) -> None:
        self._store = store
        self._audit_writer = audit_writer
        self._seeded: bool = False

    async def _ensure_default_seeded(self) -> None:
        """Lazily seed the default project on the first operation."""
        if self._seeded:
            return
        existing = await self._store.get(self.DEFAULT_PROJECT_ID)
        if existing is None:
            now = datetime.now(timezone.utc)
            default = Project(
                project_id=self.DEFAULT_PROJECT_ID,
                slug="default",
                name="Default Project",
                status="active",
                project_scope="global",
                description="Default project for backward-compatible unscoped data.",
                created_at=now,
                metadata={"p19": {"is_default": True}},
            )
            await self._store.create(default)
        self._seeded = True

    # ── Public API ────────────────────────────────────────────────────

    async def create(
        self,
        slug: str,
        *,
        name: str | None = None,
        description: str | None = None,
        project_scope: ProjectScope = "project",
        metadata: dict[str, Any] | None = None,
        default_channel_id: str | None = None,
        dashboard_channel_id: str | None = None,
        log_channel_id: str | None = None,
        accent_color: str | None = None,
        audit_writer: AuditWriter | None = None,
    ) -> Project:
        """Create a new project and return it.

        Parameters
        ----------
        slug:
            Unique human-readable identifier (lowercase kebab).
        name:
            Display name (defaults to ``slug``).
        description:
            Optional description.
        project_scope:
            Visibility scope (default ``project``).
        metadata:
            Arbitrary JSON-serialisable metadata.
        default_channel_id, dashboard_channel_id, log_channel_id:
            Discord channel bindings.
        accent_color:
            Optional hex colour for embeds.
        audit_writer:
            Optional per-call audit writer override.  Falls back to the
            instance-level writer if omitted.

        Returns
        -------
        Project
            The newly-created project.

        Raises
        ------
        InvalidProjectSlugError
            Slug does not match naming rules.
        ProjectAlreadyExistsError
            A project with this slug already exists.
        """
        await self._ensure_default_seeded()

        _validate_slug(slug)

        existing = await self._store.get_by_slug(slug)
        if existing is not None:
            raise ProjectAlreadyExistsError(slug)

        now = datetime.now(timezone.utc)
        project_id = uuid.uuid4()
        project = Project(
            project_id=project_id,
            slug=slug,
            name=name or slug,
            status="active",
            project_scope=project_scope,
            description=description,
            created_at=now,
            metadata=metadata or {},
            default_channel_id=default_channel_id,
            dashboard_channel_id=dashboard_channel_id,
            log_channel_id=log_channel_id,
            accent_color=accent_color,
        )

        await self._store.create(project)
        await self._write_audit(
            "project.created",
            {"project_id": str(project_id), "slug": slug},
            audit_writer=audit_writer,
        )

        return project

    async def get(self, project_id: ProjectId) -> Project:
        """Retrieve a project by UUID.

        Raises
        ------
        ProjectNotFoundError
            No project matches the given UUID.
        """
        await self._ensure_default_seeded()
        project = await self._store.get(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))
        return project

    async def resolve(self, slug: str) -> Project:
        """Resolve a slug to its :class:`Project`.

        Raises
        ------
        ProjectNotFoundError
            No project matches the given slug.
        InvalidProjectSlugError
            Slug format is invalid.
        """
        _validate_slug(slug)
        await self._ensure_default_seeded()
        project = await self._store.get_by_slug(slug)
        if project is None:
            raise ProjectNotFoundError(slug)
        return project

    async def list(self) -> list[Project]:
        """Return all projects (including archived)."""
        await self._ensure_default_seeded()
        return await self._store.list_all()

    async def list_active(self) -> list[Project]:
        """Return only active and paused projects (not archived)."""
        all_projects = await self.list()
        return [p for p in all_projects if p.status != "archived"]

    async def archive(
        self,
        project_id: ProjectId,
        *,
        audit_writer: AuditWriter | None = None,
    ) -> Project:
        """Archive a project (set status to ``archived``).

        The default project **cannot** be archived.

        Parameters
        ----------
        project_id:
            UUID of the project to archive.
        audit_writer:
            Optional per-call audit writer override.

        Returns
        -------
        Project
            The archived project (with status ``archived`` and
            ``archived_at`` set).

        Raises
        ------
        ProjectNotFoundError
            No project matches the given UUID.
        ProjectArchivedError
            Attempting to archive the default project.
        """
        await self._ensure_default_seeded()

        if project_id == self.DEFAULT_PROJECT_ID:
            raise ProjectArchivedError(str(project_id))

        project = await self.get(project_id)
        if project.status == "archived":
            # Idempotent — already archived.
            return project

        now = datetime.now(timezone.utc)
        archived = project.model_copy(
            update={
                "status": "archived",
                "archived_at": now,
            }
        )
        await self._store.update(archived)
        await self._write_audit(
            "project.archived",
            {"project_id": str(project_id), "slug": project.slug},
            audit_writer=audit_writer,
        )

        return archived

    # ── Internal helpers ──────────────────────────────────────────────

    async def _write_audit(
        self,
        event_type: str,
        data: dict[str, Any],
        audit_writer: AuditWriter | None = None,
    ) -> None:
        """Write an audit event through the available writer.

        Precedence: per-call writer > instance-level writer.
        """
        writer = audit_writer or self._audit_writer
        if writer is None:
            return  # No writer configured — silently skip (acceptable for
            # deployments that do not require audit).
        await writer.write_event(
            event_type=event_type,
            loop_id="projects",
            data=data,
        )

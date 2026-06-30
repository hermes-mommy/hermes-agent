# src/projects module
"""Project registry — domain models, registry service, and typed identifiers.

This package implements P19-002: the central project registry that owns
project identity, lifecycle (create/list/archive/resolve), and the canonical
default project (UUID ``00000000-0000-0000-0000-000000000001``).

Sub-packages and callers must import ``projects.project_registry`` (not
the deprecated alias) to discover active project context.
"""

from __future__ import annotations

from guinvere.projects.exceptions import (
    InvalidProjectSlugError,
    ProjectAlreadyExistsError,
    ProjectArchivedError,
    ProjectNotFoundError,
)
from guinvere.projects.registry import ProjectRegistry
from guinvere.projects.types import Project, ProjectId, ProjectScope, ProjectStatus

__all__ = [
    "InvalidProjectSlugError",
    "Project",
    "ProjectAlreadyExistsError",
    "ProjectArchivedError",
    "ProjectId",
    "ProjectNotFoundError",
    "ProjectRegistry",
    "ProjectScope",
    "ProjectStatus",
]

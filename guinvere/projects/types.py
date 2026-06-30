"""Domain types for the project registry — ProjectId, Project, ProjectStatus, ProjectScope.

``ProjectId`` is a :class:`uuid.UUID` newtype used everywhere the project
registry's public API expects a project identifier.  The canonical default
project UUID (``00000000-0000-0000-0000-000000000001``) lives in
:attr:`ProjectRegistry.DEFAULT_PROJECT_ID`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Type aliases ──────────────────────────────────────────────────────

ProjectId = uuid.UUID
"""UUID identifying a project within the registry.

Usage::

    pid: ProjectId = uuid.UUID("00000000-0000-0000-0000-000000000001")
    registry.get(pid)
"""

ProjectStatus = Literal["active", "paused", "archived"]
"""Lifecycle status of a project.

* ``active`` — normal operation.
* ``paused`` — autonomous work suspended; switchable, but no background
  cognition runs.
* ``archived`` — read-only; cannot be switched to.
"""

ProjectScope = Literal["global", "project"]
"""Visibility scope for project-scoped data.

* ``global`` — visible from every project (persona, safety policies, ADRs).
* ``project`` — visible from the owning project only.
"""

# ── Pydantic model ────────────────────────────────────────────────────


class Project(BaseModel):
    """Canonical representation of a single project in the registry.

    Instantiated from database rows by :class:`ProjectRegistry` and returned
    to callers (Discord command layer, session init, dashboard).

    The model is frozen so callers cannot accidentally mutate a shared
    reference.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    project_id: ProjectId = Field(
        ...,
        description="UUID primary key (fixed ``00000000-...-0001`` for default).",
    )
    slug: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-z0-9]([a-z0-9_-]{0,62}[a-z0-9])?$",
        description="Human-readable unique identifier (lowercase kebab).",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Display name for UIs and logging.",
    )
    status: ProjectStatus = Field(
        default="active",
        description="Lifecycle status.",
    )
    project_scope: ProjectScope = Field(
        default="project",
        description="Visibility boundary for the project's data.",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the project's purpose.",
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp of project creation.",
    )
    archived_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the project was archived (NULL when active/paused).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary JSON metadata (retention policy, integration config, etc.).",
    )
    default_channel_id: str | None = Field(
        default=None,
        description="Discord channel ID for default project binding.",
    )
    dashboard_channel_id: str | None = Field(
        default=None,
        description="Per-project dashboard Discord channel (nullable).",
    )
    log_channel_id: str | None = Field(
        default=None,
        description="Per-project log Discord channel (nullable).",
    )
    accent_color: str | None = Field(
        default=None,
        description="Optional hex colour for Discord embeds (e.g., ``#5865F2``).",
    )

"""Domain exceptions for the project registry.

Every public error is a typed subclass so callers can catch exactly the
failure they expect without relying on bare ``except`` or string matching.
"""

from __future__ import annotations


class ProjectNotFoundError(LookupError):
    """Raised when a project ID or slug does not match any known project.

    Attributes:
        identifier: The UUID or slug that was not found.
    """

    def __init__(self, identifier: str) -> None:
        self.identifier: str = identifier
        super().__init__(f"Project not found: {identifier!r}")


class ProjectAlreadyExistsError(ValueError):
    """Raised when attempting to create a project whose slug is already taken.

    Attributes:
        slug: The duplicate slug.
    """

    def __init__(self, slug: str) -> None:
        self.slug: str = slug
        super().__init__(f"Project already exists: {slug!r}")


class ProjectArchivedError(RuntimeError):
    """Raised when an operation targets an archived project.

    Attributes:
        project_id: The archived project's UUID.
    """

    def __init__(self, project_id: str) -> None:
        self.project_id: str = project_id
        super().__init__(f"Project is archived: {project_id!r}")


class InvalidProjectSlugError(ValueError):
    """Raised when a slug does not meet the naming rules.

    Rules: lowercase alphanumeric, hyphens, underscores; 1-64 chars; must
    not start or end with a separator.

    Attributes:
        slug: The invalid slug.
    """

    def __init__(self, slug: str) -> None:
        self.slug: str = slug
        super().__init__(
            f"Invalid project slug: {slug!r}. "
            "Must be 1-64 lowercase alphanumeric characters, "
            "hyphens or underscores, not starting/ending with a separator."
        )

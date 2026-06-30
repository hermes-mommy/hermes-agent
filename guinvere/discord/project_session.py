"""Active project session state for P19-007.

Module-level mutable state tracking the currently active project UUID.
Defaults to the canonical default project (``00000000-0000-0000-0000-000000000001``).

Thread-safe for async use: no locks needed because Discord event loop
is single-threaded per shard.
"""

from __future__ import annotations

import uuid

_DEFAULT_PROJECT_ID: str = "00000000-0000-0000-0000-000000000001"

_active_project_id: str = _DEFAULT_PROJECT_ID


def get_active_project_id() -> str:
    """Return the currently active project UUID string."""
    return _active_project_id


def set_active_project_id(project_id: str) -> None:
    """Set the active project UUID string."""
    global _active_project_id  # noqa: PLW0603
    _active_project_id = project_id


def reset_active_project_id() -> None:
    """Reset to the default project (for testing)."""
    global _active_project_id  # noqa: PLW0603
    _active_project_id = _DEFAULT_PROJECT_ID


def get_default_project_id() -> str:
    """Return the canonical default project UUID string."""
    return _DEFAULT_PROJECT_ID


__all__ = [
    "get_active_project_id",
    "set_active_project_id",
    "reset_active_project_id",
    "get_default_project_id",
]

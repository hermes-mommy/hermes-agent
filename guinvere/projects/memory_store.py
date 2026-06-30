"""ProjectScopedMemoryStore — memory/KG partition wrapper for P19.

This wrapper enforces project-isolated queries on episodic memory,
semantic memory, and knowledge graph stores.  Every recall and store
operation injects a ``WHERE project_id = :pid OR project_scope = 'global'``
filter so that project-scoped data is never visible from another project
while global-scope data (persona facts, ADRs, safety policies) remains
visible from every project.

When ``project_id`` is ``None`` (default), the wrapper is transparent:
it delegates to the underlying store/pipeline without adding any filter.
This preserves the legacy P20 global behavior byte-for-byte.

Design
------
* Thread-safe: the wrapper holds no mutable state beyond the reference
  to the underlying client.
* Zero-copy for ``project_id=None``: the wrapper returns the underlying
  callable or result unchanged when no project filter is needed.
* Feature-flag compatible: the caller's ``feature:projects:enabled``
  flag determines whether ``project_id`` is populated; when the flag is
  OFF (current default), ``project_id`` is always ``None`` and the
  wrapper is a pass-through.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

from guinvere.projects.types import ProjectId

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def scope_recall_callable(
    recall_fn: Callable[..., Any],
    *,
    project_id: ProjectId | None = None,
) -> Callable[..., Any]:
    """Wrap a ``recall_memories``-like callable so it injects ``project_id``.

    When ``project_id`` is ``None``, the original callable is returned
    unchanged (zero-copy pass-through).  When set, the wrapper adds
    ``project_id=project_id`` to every call's keyword arguments.

    The wrapped callable must accept ``project_id: Optional[UUID]`` as a
    keyword argument (as the P19-004 modifications to
    :func:`src.memory.read_pipeline.recall_memories` do).
    """
    if project_id is None:
        return recall_fn

    async def _scoped_recall(*args: Any, **kwargs: Any) -> Any:
        kwargs["project_id"] = project_id
        return await recall_fn(*args, **kwargs)

    return _scoped_recall


def scope_store_callable(
    store_fn: Callable[..., Any],
    *,
    project_id: ProjectId | None = None,
    project_scope: str = "project",
) -> Callable[..., Any]:
    """Wrap a ``store_episode``-like callable to inject ``project_id``.

    When ``project_id`` is ``None``, the original callable is returned
    unchanged.  When set, the wrapper adds ``project_id=project_id`` and
    ``project_scope=project_scope`` to every call's keyword arguments.
    """
    if project_id is None:
        return store_fn

    async def _scoped_store(*args: Any, **kwargs: Any) -> Any:
        kwargs["project_id"] = project_id
        kwargs["project_scope"] = project_scope
        return await store_fn(*args, **kwargs)

    return _scoped_store


class ProjectScopedMemoryStore:
    """Thin wrapper that enforces project isolation over memory/KG stores.

    The wrapper is *zero-copy* when ``project_id`` is ``None`` (legacy
    global mode): ``recall`` and ``store`` simply delegate to the
    underlying callables with no overhead.

    Usage::

        store = ProjectScopedMemoryStore()
        # Legacy (global) path — no filter.
        results = await store.recall(recall_memories, session, "query")
        # Project-scoped path.
        results = await store.recall(
            recall_memories, session, "query",
            project_id=uuid.UUID("..."),
        )
    """

    # ------------------------------------------------------------------
    # Recall
    # ------------------------------------------------------------------

    @staticmethod
    async def recall(
        recall_fn: Callable[..., Any],
        *args: Any,
        project_id: ProjectId | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a recall operation with optional project scoping.

        Parameters
        ----------
        recall_fn:
            The underlying recall callable (e.g.
            :func:`src.memory.read_pipeline.recall_memories`).
        project_id:
            When set, the recall is scoped to episodes whose
            ``project_id == project_id OR project_scope == 'global'``.
            When ``None`` (default), no project filter is applied
            (legacy global behavior).
        """
        scoped = scope_recall_callable(recall_fn, project_id=project_id)
        return await scoped(*args, **kwargs)

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    @staticmethod
    async def store(
        store_fn: Callable[..., Any],
        *args: Any,
        project_id: ProjectId | None = None,
        project_scope: str = "project",
        **kwargs: Any,
    ) -> Any:
        """Execute a store operation with optional project tagging.

        Parameters
        ----------
        store_fn:
            The underlying store callable (e.g.
            :func:`src.memory.write_pipeline.store_episode`).
        project_id:
            When set, the stored episode is tagged with this project UUID.
            When ``None`` (default), no project tag is applied and the
            episode is effectively global.
        project_scope:
            ``"global"`` = visible from every project; ``"project"``
            (default) = isolated to the owning project.  Only meaningful
            when ``project_id`` is also set.
        """
        scoped = scope_store_callable(
            store_fn,
            project_id=project_id,
            project_scope=project_scope,
        )
        return await scoped(*args, **kwargs)


__all__ = [
    "ProjectScopedMemoryStore",
    "scope_recall_callable",
    "scope_store_callable",
]

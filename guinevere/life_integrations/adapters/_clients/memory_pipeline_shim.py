"""P22 memory pipeline shims — wrap module-level memory functions as instance protocol.

The P22 ``MemoryIntegrationAdapter`` calls instance methods:
- ``await self._write.store_episode(content=..., classification=..., project_id=...)``
- ``await self._read.recall_memories(query=..., limit=..., project_id=...)``

The real Guinevere memory pipelines are module-level functions in
``guinevere.memory.write_pipeline`` / ``guinevere.memory.read_pipeline`` that require a
SQLAlchemy ``AsyncSession`` as the first positional argument. Guinevere's
canonical session provider is ``guinevere.memory.db.get_async_session`` (an
``@asynccontextmanager`` yielding a session, commit-on-success/rollback-on-error).

These shims hold a reference to a session provider (defaulting to
``get_async_session``), open a session per call, and forward to the module
functions — preserving ``project_id`` propagation (P19/ADR-052).

A small ``KGQueryShim`` exposes ``.query(query, project_id=...)`` by delegating
to ``KGQueryEngine.search_entities`` (the real engine has no ``query`` method;
it exposes ``traverse``/``search_entities``/``neighborhood``).

Fail-closed: if no session provider wired, methods raise
``ConfigurationMissingError`` rather than silently no-op (no fake PASS).
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

import structlog

from guinevere.life_integrations.errors import ConfigurationMissingError

logger = structlog.get_logger(__name__)

# Type alias: an async context manager callable yielding an AsyncSession.
SessionProvider = Callable[[], Any]


class MemoryWritePipelineShim:
    """Instance wrapper around ``guinevere.memory.write_pipeline.store_episode``."""

    def __init__(self, session_provider: SessionProvider | None = None) -> None:
        """Initialize with a session provider (or None => CONFIG_MISSING).

        Args:
            session_provider: async-context-manager callable yielding an
                ``AsyncSession`` (e.g. ``guinevere.memory.db.get_async_session``).
        """
        self._session_provider = session_provider

    async def store_episode(
        self,
        *,
        content: str,
        classification: str = "Restricted",
        project_id: uuid.UUID | None = None,
        source: str = "p22-integration",
        **kwargs: Any,
    ) -> uuid.UUID:
        """Forward to ``write_pipeline.store_episode`` with a fresh session."""
        if self._session_provider is None:
            raise ConfigurationMissingError(
                "memory write pipeline: no session provider wired"
            )
        from guinevere.memory.write_pipeline import store_episode

        async with self._session_provider() as session:
            return await store_episode(
                session,
                content,
                source=source,
                classification=classification,
                project_id=project_id,
                **kwargs,
            )

    async def store_fact(
        self,
        *,
        subject: str,
        predicate: str,
        object: str,
        classification: str = "Restricted",
        project_id: uuid.UUID | None = None,
        source: str = "p22-integration",
        **kwargs: Any,
    ) -> uuid.UUID:
        """Store a semantic fact (C9). Forwards to the semantic_facts ORM row."""
        if self._session_provider is None:
            raise ConfigurationMissingError(
                "memory write pipeline: no session provider wired for store_fact"
            )
        if not subject or not predicate or not object:
            raise ConfigurationMissingError(
                "store_fact requires subject, predicate, and object kwargs"
            )
        from sqlalchemy import text as _sa_text

        async with self._session_provider() as session:
            fact_id = uuid.uuid4()
            await session.execute(
                _sa_text(
                    "INSERT INTO memory.semantic_facts "
                    "(id, subject, predicate, object, classification, "
                    "source, project_id) VALUES "
                    "(:id, :subject, :predicate, :object, :classification, "
                    ":source, :project_id)"
                ),
                {
                    "id": str(fact_id),
                    "subject": subject,
                    "predicate": predicate,
                    "object": object,
                    "classification": classification,
                    "source": source,
                    "project_id": str(project_id) if project_id else None,
                },
            )
            await session.commit()
            return fact_id

    async def mark_dnr(
        self,
        *,
        episode_id: uuid.UUID | str,
        reason: str = "",
        principal: str = "guinevere_core",
        **kwargs: Any,
    ) -> uuid.UUID | None:
        """Forward to ``guinevere.memory.dnr.mark_memory_dnr`` (A2).

        The real ``mark_memory_dnr`` accepts ``memory_id``; the adapter passes
        ``episode_id`` which we map to ``memory_id``. ``mark_memory_dnr``
        enforces an authorization whitelist — the DNR safety boundary is
        preserved (not bypassed).
        """
        if self._session_provider is None:
            raise ConfigurationMissingError(
                "memory write pipeline: no session provider wired for mark_dnr"
            )
        if not episode_id:
            raise ConfigurationMissingError(
                "memory mark_dnr: episode_id is required"
            )
        from guinevere.memory.dnr import mark_memory_dnr

        async with self._session_provider() as session:
            return await mark_memory_dnr(
                session,
                memory_id=episode_id,
                reason=reason,
                principal=principal,
                **kwargs,
            )


class MemoryReadPipelineShim:
    """Instance wrapper around ``guinevere.memory.read_pipeline.recall_memories``."""

    def __init__(self, session_provider: SessionProvider | None = None) -> None:
        self._session_provider = session_provider

    async def recall_memories(
        self,
        *,
        query: str,
        limit: int = 20,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Forward to ``read_pipeline.recall_memories`` with a fresh session."""
        if self._session_provider is None:
            raise ConfigurationMissingError(
                "memory read pipeline: no session provider wired"
            )
        from guinevere.memory.read_pipeline import recall_memories

        async with self._session_provider() as session:
            results = await recall_memories(
                session,
                query,
                limit=limit,
                project_id=project_id,
                **kwargs,
            )
            # recall_memories returns RecallResults (may not be a list); adapter
            # does len(results) — ensure len() works, else wrap.
            return results


class KGQueryShim:
    """Expose ``.query(query, project_id=...)`` by delegating to KGQueryEngine.search_entities.

    The real ``KGQueryEngine`` has ``search_entities(query, *, limit, project_id)``
    but no ``query`` method. The P22 memory adapter calls ``self._kg.query(...)``.
    This shim bridges the naming gap.
    """

    def __init__(self, kg_engine: Any | None = None, limit: int = 20) -> None:
        self._engine = kg_engine
        self._limit = limit

    async def query(
        self,
        query: str,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        """Delegate to ``KGQueryEngine.search_entities``."""
        if self._engine is None:
            raise ConfigurationMissingError(
                "memory kg engine: no KGQueryEngine wired"
            )
        results = await self._engine.search_entities(
            query,
            limit=kwargs.get("limit", self._limit),
            project_id=project_id,
        )
        return results

"""World Model — entity graph for the Life Kernel.

Provides a lightweight in-memory entity graph with add/query/remove
operations.  Entities are typed dictionaries with a required ``kind``
and ``id`` field.  Relations are directed edges with a ``relation``
label.

Ported from guinevere/life_kernel/graph.py (42KB) — graph query logic only.
LangGraph-specific scaffolding (nodes, edges, StateGraph) is replaced
by plain Python data structures suitable for local-only runtime (D2).

P20 invariant: fail-soft on missing PG/Redis — in-memory fallback.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class WorldModel:
    """In-memory entity graph with async access.

    Thread-safe via ``asyncio.Lock``.  All public methods are ``async``
    so callers never block the event loop.

    Entities:
        ``{"id": str, "kind": str, ...extra}``

    Relations:
        ``{"source": str, "target": str, "relation": str}``
    """

    def __init__(self) -> None:
        self._entities: dict[str, dict[str, Any]] = {}
        self._relations: list[dict[str, str]] = []
        self._lock = asyncio.Lock()

    # --- entity CRUD ---------------------------------------------------------

    async def add_entity(self, entity: dict[str, Any]) -> str:
        """Add an entity to the graph.  Returns the entity id.

        Args:
            entity: Must contain ``kind`` and ``id`` keys.

        Raises:
            ValueError: If ``kind`` or ``id`` is missing.
        """
        eid = entity.get("id")
        kind = entity.get("kind")
        if not eid:
            eid = str(uuid.uuid4())
            entity = {**entity, "id": eid}
        if not kind:
            raise ValueError("Entity must have a 'kind' field")

        async with self._lock:
            self._entities[eid] = {**entity, "_updated": datetime.now(timezone.utc).isoformat()}
            logger.debug("entity_added", entity_id=eid, kind=kind)
        return eid

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity by id, or ``None``."""
        async with self._lock:
            return self._entities.get(entity_id)

    async def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and its relations.  Returns ``True`` if found."""
        async with self._lock:
            if entity_id not in self._entities:
                return False
            del self._entities[entity_id]
            self._relations = [
                r for r in self._relations
                if r["source"] != entity_id and r["target"] != entity_id
            ]
            logger.debug("entity_removed", entity_id=entity_id)
            return True

    async def update_entity(self, entity_id: str, **fields: Any) -> bool:
        """Update an entity's fields.  Returns ``True`` if found."""
        async with self._lock:
            entity = self._entities.get(entity_id)
            if entity is None:
                return False
            entity.update(fields)
            entity["_updated"] = datetime.now(timezone.utc).isoformat()
            return True

    # --- relation CRUD -------------------------------------------------------

    async def add_relation(
        self, source: str, target: str, relation: str
    ) -> None:
        """Add a directed relation between two entities."""
        async with self._lock:
            self._relations.append(
                {"source": source, "target": target, "relation": relation}
            )
            logger.debug(
                "relation_added",
                source=source,
                target=target,
                relation=relation,
            )

    async def get_relations(
        self,
        entity_id: str | None = None,
        relation: str | None = None,
    ) -> list[dict[str, str]]:
        """Query relations filtered by entity and/or relation label."""
        async with self._lock:
            results = self._relations
            if entity_id is not None:
                results = [
                    r for r in results
                    if r["source"] == entity_id or r["target"] == entity_id
                ]
            if relation is not None:
                results = [r for r in results if r["relation"] == relation]
            return list(results)

    # --- graph queries -------------------------------------------------------

    async def query_entities(
        self,
        kind: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query entities with optional kind filter and pagination."""
        async with self._lock:
            if kind is not None:
                matches = [e for e in self._entities.values() if e.get("kind") == kind]
            else:
                matches = list(self._entities.values())
            return matches[offset : offset + limit]

    async def count_entities(self, kind: str | None = None) -> int:
        """Count entities, optionally filtered by kind."""
        async with self._lock:
            if kind is not None:
                return sum(1 for e in self._entities.values() if e.get("kind") == kind)
            return len(self._entities)

    async def count_relations(self, entity_id: str | None = None) -> int:
        """Count relations, optionally for a specific entity."""
        async with self._lock:
            if entity_id is not None:
                return sum(
                    1 for r in self._relations
                    if r["source"] == entity_id or r["target"] == entity_id
                )
            return len(self._relations)

    async def get_neighbors(
        self,
        entity_id: str,
        relation: str | None = None,
        direction: str = "outgoing",
    ) -> list[str]:
        """Get neighbor entity ids for a given entity.

        Args:
            entity_id: Source entity.
            relation: Optional relation label filter.
            direction: ``"outgoing"``, ``"incoming"``, or ``"both"``.
        """
        async with self._lock:
            neighbor_ids: list[str] = []
            for r in self._relations:
                if relation and r["relation"] != relation:
                    continue
                if direction in ("outgoing", "both") and r["source"] == entity_id:
                    neighbor_ids.append(r["target"])
                if direction in ("incoming", "both") and r["target"] == entity_id:
                    neighbor_ids.append(r["source"])
            return neighbor_ids

    # --- health check --------------------------------------------------------

    async def health(self) -> bool:
        """Return ``True`` — the in-memory graph is always available."""
        return True

    # --- snapshot ------------------------------------------------------------

    async def snapshot(self) -> dict[str, Any]:
        """Return a snapshot of the graph (entities + relations counts)."""
        async with self._lock:
            return {
                "entity_count": len(self._entities),
                "relation_count": len(self._relations),
                "kinds": list({e.get("kind", "?") for e in self._entities.values()}),
            }

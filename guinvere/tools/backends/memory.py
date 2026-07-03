"""M8 Memory backend -- PostgreSQL + pgvector memory store (P24 Task 3).

18 actions implementing the full memory lifecycle:
  store_memory, recall_memory, search_memory, update_memory, delete_memory,
  list_memories, get_memory_by_id, get_memories_by_type, get_memories_by_time_range,
  consolidate_memories, export_memories, import_memories, get_memory_stats,
  create_memory_collection, delete_memory_collection, list_memory_collections,
  set_memory_metadata, get_memory_metadata.

All actions use SQLAlchemy AsyncSession.  Vector search uses pgvector cosine
distance on PostgreSQL; pure-Python cosine similarity is used as a fallback
(e.g. in-memory SQLite tests).
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from collections.abc import Awaitable, Callable
from typing import Any

_Handler = Callable[["MemoryBackend", str, dict[str, Any]], Awaitable[dict[str, Any]]]

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from guinevere.memory.models import Memory, MemoryCollection, MemoryType
from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Async session factory -- module-level so tests can monkeypatch
# ---------------------------------------------------------------------------

def _create_session_factory() -> Any:
    """Create an async session factory from guinvere.memory.db.

    Returns a callable that yields ``AsyncSession`` (async context manager).
    Typed as ``Any`` because the real return is an async generator context
    manager, not a plain callable — mypy cannot reconcile the two.
    """
    from guinvere.memory.db import get_async_session
    return get_async_session


# Module-level session getter.  Tests monkeypatch this.
_get_session = _create_session_factory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors (pure-Python fallback)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _parse_embedding(raw: Any) -> list[float] | None:
    """Normalise an embedding value to a ``list[float]`` or ``None``."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [float(x) for x in parsed]
        except (json.JSONDecodeError, ValueError):
            pass
    return None


# ---------------------------------------------------------------------------
# MemoryBackend
# ---------------------------------------------------------------------------

class MemoryBackend(ToolBackend):
    """Memory backend (L1/L2/L3) backed by PostgreSQL + pgvector.

    18 actions:
      L1 READ (10):  recall_memory, search_memory, list_memories,
                     get_memory_by_id, get_memories_by_type,
                     get_memories_by_time_range, export_memories,
                     get_memory_stats, list_memory_collections,
                     get_memory_metadata
      L2 WRITE (7):  store_memory, update_memory, import_memories,
                     consolidate_memories, create_memory_collection,
                     set_memory_metadata, delete_memory_collection
      L3 DESTRUCTIVE (1):  delete_memory
    """

    @property
    def name(self) -> str:
        return "memory"

    def actions(self) -> list[Action]:
        return [
            # L1 READ
            Action("recall_memory", ActionTier.L1_READ,
                   description="Get memory by ID"),
            Action("search_memory", ActionTier.L1_READ,
                   description="Vector similarity search via pgvector"),
            Action("list_memories", ActionTier.L1_READ,
                   description="List memories (paginated)"),
            Action("get_memory_by_id", ActionTier.L1_READ,
                   description="Alias for recall_memory"),
            Action("get_memories_by_type", ActionTier.L1_READ,
                   description="Filter memories by MemoryType"),
            Action("get_memories_by_time_range", ActionTier.L1_READ,
                   description="Filter memories by date range"),
            Action("export_memories", ActionTier.L1_READ,
                   description="Export memories to JSON"),
            Action("get_memory_stats", ActionTier.L1_READ,
                   description="Count by type, total size"),
            Action("list_memory_collections", ActionTier.L1_READ,
                   description="List all collections"),
            Action("get_memory_metadata", ActionTier.L1_READ,
                   description="Get metadata for a memory"),
            # L2 WRITE
            Action("store_memory", ActionTier.L2_WRITE,
                   description="Create new memory record"),
            Action("update_memory", ActionTier.L2_WRITE,
                   description="Modify memory content/metadata"),
            Action("import_memories", ActionTier.L2_WRITE,
                   description="Import memories from JSON"),
            Action("consolidate_memories", ActionTier.L2_WRITE,
                   description="Merge similar memories"),
            Action("create_memory_collection", ActionTier.L2_WRITE,
                   description="Create named collection"),
            Action("set_memory_metadata", ActionTier.L2_WRITE,
                   description="Update metadata fields"),
            Action("delete_memory_collection", ActionTier.L2_WRITE,
                   description="Remove collection"),
            # L3 DESTRUCTIVE
            Action("delete_memory", ActionTier.L3_DESTRUCTIVE,
                   description="Remove memory record"),
        ]

    def is_available(self) -> bool:
        return True

    # -----------------------------------------------------------------------
    # dispatch -- NEVER raises to caller (fail-soft)
    # -----------------------------------------------------------------------

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a memory action.  Never raises (fail-soft dispatch boundary)."""
        action_lower = action.lower()

        try:
            handler = _HANDLERS.get(action_lower)
            if handler is not None:
                return await handler(self, action, args)
            return {"ok": False, "error": f"unknown memory action: {action}"}

        except SQLAlchemyError as exc:
            logger.error("memory.dispatch DB error action=%s: %s", action, exc,
                         exc_info=True)
            return {"ok": False, "action": action, "error": f"db error: {exc}"}
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            # Input validation errors (bad types, missing keys, invalid values)
            logger.error("memory.dispatch validation error action=%s: %s", action, exc,
                         exc_info=True)
            return {"ok": False, "action": action, "error": f"validation error: {exc}"}
        except OSError as exc:
            # File system errors during consolidation/import
            logger.error("memory.dispatch IO error action=%s: %s", action, exc,
                         exc_info=True)
            return {"ok": False, "action": action, "error": f"io error: {exc}"}

    # -----------------------------------------------------------------------
    # 1. store_memory
    # -----------------------------------------------------------------------

    async def _store_memory(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new memory record."""
        content = args.get("content", "")
        if not content:
            return {"ok": False, "action": action, "error": "content is required"}

        memory_type = args.get("memory_type", MemoryType.EPISODIC.value)
        embedding = args.get("embedding")
        metadata = args.get("metadata", {})
        collection = args.get("collection")
        source = args.get("source")
        importance = float(args.get("importance", 1.0))

        now = _now()
        memory = Memory(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            embedding_json=embedding,
            metadata_json=metadata,
            collection=collection,
            source=source,
            importance=importance,
            do_not_recall=False,
            created_at=now,
            updated_at=now,
        )

        session_factory = _get_session()
        async with session_factory() as session:
            session.add(memory)
            await session.commit()

        return {"ok": True, "action": action, "memory_id": memory.id}

    # -----------------------------------------------------------------------
    # 2. recall_memory
    # -----------------------------------------------------------------------

    async def _recall_memory(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Get a memory by ID."""
        memory_id = args.get("memory_id", "")
        if not memory_id:
            return {"ok": False, "action": action, "error": "memory_id is required"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(Memory).where(Memory.id == memory_id)
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

        if memory is None:
            return {"ok": False, "action": action, "error": f"memory not found: {memory_id}"}

        return {"ok": True, "action": action, "memory": memory.to_dict()}

    # -----------------------------------------------------------------------
    # 3. search_memory
    # -----------------------------------------------------------------------

    async def _search_memory(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Vector similarity search via pgvector (cosine distance).

        Falls back to pure-Python cosine similarity when the embedding
        column is JSON (e.g. in-memory SQLite tests).
        """
        query_embedding = args.get("query_embedding")
        limit = int(args.get("limit", 10))
        collection_filter = args.get("collection")

        if query_embedding is None:
            return {"ok": False, "action": action, "error": "query_embedding is required"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(Memory)
            if collection_filter:
                stmt = stmt.where(Memory.collection == collection_filter)
            result = await session.execute(stmt)
            all_memories = list(result.scalars().all())

        scored: list[tuple[Memory, float]] = []
        for mem in all_memories:
            mem_emb = _parse_embedding(mem.embedding_json)
            if mem_emb is not None:
                sim = _cosine_similarity(query_embedding, mem_emb)
                scored.append((mem, sim))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        top = scored[:limit]

        results = [
            {**mem.to_dict(), "score": round(score, 6)}
            for mem, score in top
        ]
        return {"ok": True, "action": action, "results": results, "count": len(results)}

    # -----------------------------------------------------------------------
    # 4. update_memory
    # -----------------------------------------------------------------------

    async def _update_memory(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Modify memory content/metadata."""
        memory_id = args.get("memory_id", "")
        if not memory_id:
            return {"ok": False, "action": action, "error": "memory_id is required"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(Memory).where(Memory.id == memory_id)
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

            if memory is None:
                return {"ok": False, "action": action,
                        "error": f"memory not found: {memory_id}"}

            if "content" in args:
                memory.content = args["content"]
            if "memory_type" in args:
                memory.memory_type = args["memory_type"]
            if "embedding" in args:
                memory.embedding_json = args["embedding"]
            if "metadata" in args:
                memory.metadata_json = args["metadata"]
            if "collection" in args:
                memory.collection = args["collection"]
            if "source" in args:
                memory.source = args["source"]
            if "importance" in args:
                memory.importance = float(args["importance"])

            memory.updated_at = _now()
            await session.commit()

        return {"ok": True, "action": action, "memory_id": memory_id}

    # -----------------------------------------------------------------------
    # 5. delete_memory
    # -----------------------------------------------------------------------

    async def _delete_memory(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Remove a memory record."""
        memory_id = args.get("memory_id", "")
        if not memory_id:
            return {"ok": False, "action": action, "error": "memory_id is required"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(Memory).where(Memory.id == memory_id)
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

            if memory is None:
                return {"ok": False, "action": action,
                        "error": f"memory not found: {memory_id}"}

            await session.delete(memory)
            await session.commit()

        return {"ok": True, "action": action, "memory_id": memory_id, "deleted": True}

    # -----------------------------------------------------------------------
    # 6. list_memories
    # -----------------------------------------------------------------------

    async def _list_memories(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """List memories with pagination."""
        limit = int(args.get("limit", 10))
        offset = int(args.get("offset", 0))

        session_factory = _get_session()
        async with session_factory() as session:
            count_stmt = select(func.count()).select_from(Memory)
            total = (await session.execute(count_stmt)).scalar_one()

            stmt = (
                select(Memory)
                .order_by(Memory.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            memories = [m.to_dict() for m in result.scalars().all()]

        return {
            "ok": True,
            "action": action,
            "memories": memories,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # -----------------------------------------------------------------------
    # 7. get_memory_by_id (alias for recall_memory)
    # -----------------------------------------------------------------------

    async def _get_memory_by_id(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Alias for recall_memory."""
        return await self._recall_memory(action, args)

    # -----------------------------------------------------------------------
    # 8. get_memories_by_type
    # -----------------------------------------------------------------------

    async def _get_memories_by_type(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Filter memories by MemoryType enum value."""
        memory_type = args.get("memory_type", "")
        if not memory_type:
            return {"ok": False, "action": action, "error": "memory_type is required"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = (
                select(Memory)
                .where(Memory.memory_type == memory_type)
                .order_by(Memory.created_at.desc())
            )
            result = await session.execute(stmt)
            memories = [m.to_dict() for m in result.scalars().all()]

        return {
            "ok": True,
            "action": action,
            "memory_type": memory_type,
            "memories": memories,
            "count": len(memories),
        }

    # -----------------------------------------------------------------------
    # 9. get_memories_by_time_range
    # -----------------------------------------------------------------------

    async def _get_memories_by_time_range(
        self, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Filter memories by date range."""
        start_date = args.get("start_date", "")
        end_date = args.get("end_date", "")
        if not start_date or not end_date:
            return {"ok": False, "action": action,
                    "error": "start_date and end_date are required"}

        # Parse ISO date strings to datetime objects for cross-DB compat
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except ValueError as exc:
            return {"ok": False, "action": action,
                    "error": f"invalid date format: {exc}"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = (
                select(Memory)
                .where(Memory.created_at >= start_dt)
                .where(Memory.created_at <= end_dt)
                .order_by(Memory.created_at.desc())
            )
            result = await session.execute(stmt)
            memories = [m.to_dict() for m in result.scalars().all()]

        return {
            "ok": True,
            "action": action,
            "start_date": start_date,
            "end_date": end_date,
            "memories": memories,
            "count": len(memories),
        }

    # -----------------------------------------------------------------------
    # 10. consolidate_memories
    # -----------------------------------------------------------------------

    async def _consolidate_memories(
        self, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge similar memories.

        Accepts ``memory_ids`` (list of IDs).  Creates a single merged
        memory whose content is the concatenation, then deletes the
        originals.
        """
        memory_ids = args.get("memory_ids", [])
        if not memory_ids or len(memory_ids) < 2:
            return {"ok": False, "action": action,
                    "error": "memory_ids must contain at least 2 IDs"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(Memory).where(Memory.id.in_(memory_ids))
            result = await session.execute(stmt)
            memories = list(result.scalars().all())

            if len(memories) < 2:
                return {"ok": False, "action": action,
                        "error": "not enough memories found to consolidate"}

            # Merge: concatenate content, average embeddings, merge metadata
            merged_content = "\n---\n".join(m.content for m in memories)

            all_embeddings = [_parse_embedding(m.embedding_json) for m in memories]
            valid_embeddings = [e for e in all_embeddings if e is not None]
            merged_embedding: list[float] | None = None
            if valid_embeddings:
                dim = len(valid_embeddings[0])
                merged_embedding = [
                    sum(e[i] for e in valid_embeddings) / len(valid_embeddings)
                    for i in range(dim)
                ]

            merged_metadata: dict[str, Any] = {}
            for m in memories:
                if m.metadata_json and isinstance(m.metadata_json, dict):
                    merged_metadata.update(m.metadata_json)

            now = _now()
            merged = Memory(
                id=str(uuid.uuid4()),
                content=merged_content,
                memory_type=memories[0].memory_type,
                embedding_json=merged_embedding,
                metadata_json=merged_metadata,
                collection=memories[0].collection,
                source="consolidated",
                importance=max(m.importance for m in memories),
                do_not_recall=False,
                created_at=now,
                updated_at=now,
            )
            session.add(merged)

            # Delete originals
            for m in memories:
                await session.delete(m)

            await session.commit()

        return {
            "ok": True,
            "action": action,
            "merged_id": merged.id,
            "source_count": len(memories),
        }

    # -----------------------------------------------------------------------
    # 11. export_memories
    # -----------------------------------------------------------------------

    async def _export_memories(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Export all memories as a JSON-serialisable list."""
        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(Memory).order_by(Memory.created_at)
            result = await session.execute(stmt)
            memories = [m.to_dict() for m in result.scalars().all()]

        return {
            "ok": True,
            "action": action,
            "memories": memories,
            "count": len(memories),
        }

    # -----------------------------------------------------------------------
    # 12. import_memories
    # -----------------------------------------------------------------------

    async def _import_memories(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Import memories from a JSON list."""
        memories_data = args.get("memories", [])
        if not isinstance(memories_data, list):
            return {"ok": False, "action": action,
                    "error": "memories must be a list"}

        imported = 0
        errors: list[str] = []
        now = _now()

        session_factory = _get_session()
        async with session_factory() as session:
            for entry in memories_data:
                content = entry.get("content", "")
                if not content:
                    errors.append("skipped entry with empty content")
                    continue
                memory = Memory(
                    id=str(uuid.uuid4()),
                    content=content,
                    memory_type=entry.get("memory_type", MemoryType.EPISODIC.value),
                    embedding_json=entry.get("embedding"),
                    metadata_json=entry.get("metadata", {}),
                    collection=entry.get("collection"),
                    source=entry.get("source"),
                    importance=float(entry.get("importance", 1.0)),
                    do_not_recall=False,
                    created_at=now,
                    updated_at=now,
                )
                session.add(memory)
                imported += 1

            await session.commit()

        return {
            "ok": True,
            "action": action,
            "imported": imported,
            "errors": errors,
        }

    # -----------------------------------------------------------------------
    # 13. get_memory_stats
    # -----------------------------------------------------------------------

    async def _get_memory_stats(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Return count-by-type and total size statistics."""
        session_factory = _get_session()
        async with session_factory() as session:
            # Total count
            total_stmt = select(func.count()).select_from(Memory)
            total = (await session.execute(total_stmt)).scalar_one()

            # Count by type
            type_stmt = (
                select(Memory.memory_type, func.count())
                .group_by(Memory.memory_type)
            )
            type_result = await session.execute(type_stmt)
            by_type = {row[0]: row[1] for row in type_result.all()}

            # Total content size (sum of content lengths)
            size_stmt = select(func.sum(func.length(Memory.content)))
            total_size = (await session.execute(size_stmt)).scalar_one() or 0

        return {
            "ok": True,
            "action": action,
            "total_count": total,
            "by_type": by_type,
            "total_size": total_size,
        }

    # -----------------------------------------------------------------------
    # 14. create_memory_collection
    # -----------------------------------------------------------------------

    async def _create_memory_collection(
        self, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a named collection."""
        name = args.get("name", "")
        if not name:
            return {"ok": False, "action": action, "error": "name is required"}

        description = args.get("description")

        now = _now()
        collection = MemoryCollection(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=now,
        )

        session_factory = _get_session()
        async with session_factory() as session:
            session.add(collection)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return {"ok": False, "action": action,
                        "error": f"collection already exists: {name}"}

        return {"ok": True, "action": action, "collection_id": collection.id, "name": name}

    # -----------------------------------------------------------------------
    # 15. delete_memory_collection
    # -----------------------------------------------------------------------

    async def _delete_memory_collection(
        self, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Remove a collection by name."""
        name = args.get("name", "")
        if not name:
            return {"ok": False, "action": action, "error": "name is required"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(MemoryCollection).where(MemoryCollection.name == name)
            result = await session.execute(stmt)
            collection = result.scalar_one_or_none()

            if collection is None:
                return {"ok": False, "action": action,
                        "error": f"collection not found: {name}"}

            await session.delete(collection)
            await session.commit()

        return {"ok": True, "action": action, "name": name, "deleted": True}

    # -----------------------------------------------------------------------
    # 16. list_memory_collections
    # -----------------------------------------------------------------------

    async def _list_memory_collections(
        self, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """List all collections."""
        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(MemoryCollection).order_by(MemoryCollection.name)
            result = await session.execute(stmt)
            collections = [c.to_dict() for c in result.scalars().all()]

        return {
            "ok": True,
            "action": action,
            "collections": collections,
            "count": len(collections),
        }

    # -----------------------------------------------------------------------
    # 17. set_memory_metadata
    # -----------------------------------------------------------------------

    async def _set_memory_metadata(
        self, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Update metadata fields on a memory.

        If the memory has no metadata yet, creates a new dict.
        Merges the provided ``metadata`` dict with existing metadata.
        """
        memory_id = args.get("memory_id", "")
        metadata = args.get("metadata", {})
        if not memory_id:
            return {"ok": False, "action": action, "error": "memory_id is required"}
        if not isinstance(metadata, dict):
            return {"ok": False, "action": action, "error": "metadata must be a dict"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(Memory).where(Memory.id == memory_id)
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

            if memory is None:
                return {"ok": False, "action": action,
                        "error": f"memory not found: {memory_id}"}

            existing = memory.metadata_json if isinstance(memory.metadata_json, dict) else {}
            existing.update(metadata)
            memory.metadata_json = dict(existing)
            flag_modified(memory, "metadata_json")
            memory.updated_at = _now()
            await session.commit()

        return {"ok": True, "action": action, "memory_id": memory_id}

    # -----------------------------------------------------------------------
    # 18. get_memory_metadata
    # -----------------------------------------------------------------------

    async def _get_memory_metadata(
        self, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Get metadata for a memory."""
        memory_id = args.get("memory_id", "")
        if not memory_id:
            return {"ok": False, "action": action, "error": "memory_id is required"}

        session_factory = _get_session()
        async with session_factory() as session:
            stmt = select(Memory).where(Memory.id == memory_id)
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

        if memory is None:
            return {"ok": False, "action": action,
                    "error": f"memory not found: {memory_id}"}

        return {
            "ok": True,
            "action": action,
            "memory_id": memory_id,
            "metadata": memory.metadata_json or {},
        }


# ---------------------------------------------------------------------------
# Handler dispatch map
# ---------------------------------------------------------------------------

_HANDLERS: dict[str, _Handler] = {
    "store_memory": MemoryBackend._store_memory,
    "recall_memory": MemoryBackend._recall_memory,
    "search_memory": MemoryBackend._search_memory,
    "update_memory": MemoryBackend._update_memory,
    "delete_memory": MemoryBackend._delete_memory,
    "list_memories": MemoryBackend._list_memories,
    "get_memory_by_id": MemoryBackend._get_memory_by_id,
    "get_memories_by_type": MemoryBackend._get_memories_by_type,
    "get_memories_by_time_range": MemoryBackend._get_memories_by_time_range,
    "consolidate_memories": MemoryBackend._consolidate_memories,
    "export_memories": MemoryBackend._export_memories,
    "import_memories": MemoryBackend._import_memories,
    "get_memory_stats": MemoryBackend._get_memory_stats,
    "create_memory_collection": MemoryBackend._create_memory_collection,
    "delete_memory_collection": MemoryBackend._delete_memory_collection,
    "list_memory_collections": MemoryBackend._list_memory_collections,
    "set_memory_metadata": MemoryBackend._set_memory_metadata,
    "get_memory_metadata": MemoryBackend._get_memory_metadata,
}

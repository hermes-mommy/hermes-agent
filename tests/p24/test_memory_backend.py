"""Tests for MemoryBackend -- P24 Task 3: PostgreSQL+pgvector memory actions.

18 actions, 3+ tests per action, 54+ tests total.
Uses in-memory SQLite via aiosqlite for fast, isolated testing.
All external dependencies (pgvector, Redis) are avoided -- pure SQLAlchemy async.
"""
from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from guinevere.memory.models import Base, Memory, MemoryCollection, MemoryType
from guinevere.tools.backends.memory import MemoryBackend


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite async engine with all tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(db_engine):
    """Create a session factory bound to the test engine."""
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def backend():
    return MemoryBackend()


@pytest.fixture
def patch_session(monkeypatch, session_factory):
    """Monkeypatch the memory backend's session factory to use the test DB."""
    import guinevere.tools.backends.memory as mod

    @asynccontextmanager
    async def _test_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    monkeypatch.setattr(mod, "_get_session", lambda: _test_session)
    return session_factory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_embedding(dim: int = 8) -> list[float]:
    """Return a small sample embedding for tests."""
    return [0.1 * i for i in range(dim)]


def _other_embedding(dim: int = 8) -> list[float]:
    """Return a different embedding (orthogonal to _sample_embedding)."""
    return [1.0 - 0.1 * i for i in range(dim)]


async def _seed_memory(session_factory, **overrides) -> str:
    """Insert a test memory and return its ID."""
    memory_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    defaults = {
        "id": memory_id,
        "content": "test memory content",
        "memory_type": MemoryType.EPISODIC.value,
        "embedding_json": _sample_embedding(),
        "metadata_json": {"source": "test"},
        "collection": None,
        "source": "test",
        "importance": 1.0,
        "do_not_recall": False,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    async with session_factory() as session:
        session.add(Memory(**defaults))
        await session.commit()
    return memory_id


# ===========================================================================
# 1. store_memory (3 tests)
# ===========================================================================

class TestStoreMemory:
    async def test_store_with_all_fields(self, backend, patch_session):
        result = await backend.dispatch("store_memory", {
            "content": "I learned a new algorithm",
            "memory_type": MemoryType.SEMANTIC.value,
            "embedding": _sample_embedding(),
            "metadata": {"topic": "algorithms"},
            "collection": "cs-notes",
            "source": "study",
            "importance": 2.5,
        })
        assert result["ok"] is True
        assert result["action"] == "store_memory"
        assert "memory_id" in result
        assert len(result["memory_id"]) == 36  # UUID format

    async def test_store_minimal(self, backend, patch_session):
        result = await backend.dispatch("store_memory", {
            "content": "hello world",
        })
        assert result["ok"] is True
        assert "memory_id" in result

    async def test_store_empty_content_returns_error(self, backend, patch_session):
        result = await backend.dispatch("store_memory", {"content": ""})
        assert result["ok"] is False
        assert "content is required" in result["error"]

    async def test_store_missing_content_returns_error(self, backend, patch_session):
        result = await backend.dispatch("store_memory", {})
        assert result["ok"] is False
        assert "content is required" in result["error"]


# ===========================================================================
# 2. recall_memory (3 tests)
# ===========================================================================

class TestRecallMemory:
    async def test_recall_existing(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory)
        result = await backend.dispatch("recall_memory", {"memory_id": mid})
        assert result["ok"] is True
        assert result["memory"]["id"] == mid
        assert result["memory"]["content"] == "test memory content"

    async def test_recall_not_found(self, backend, patch_session):
        result = await backend.dispatch("recall_memory", {
            "memory_id": "nonexistent-id-000",
        })
        assert result["ok"] is False
        assert "memory not found" in result["error"]

    async def test_recall_missing_id(self, backend, patch_session):
        result = await backend.dispatch("recall_memory", {})
        assert result["ok"] is False
        assert "memory_id is required" in result["error"]

    async def test_recall_returns_all_fields(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory, source="unit_test")
        result = await backend.dispatch("recall_memory", {"memory_id": mid})
        assert result["ok"] is True
        mem = result["memory"]
        assert "memory_type" in mem
        assert "created_at" in mem
        assert "updated_at" in mem
        assert mem["source"] == "unit_test"


# ===========================================================================
# 3. search_memory (3 tests)
# ===========================================================================

class TestSearchMemory:
    async def test_search_returns_ranked_results(self, backend, patch_session, session_factory):
        await _seed_memory(session_factory, content="cats are cute",
                           embedding_json=[1.0, 0.0, 0.0])
        await _seed_memory(session_factory, content="dogs are loyal",
                           embedding_json=[0.0, 1.0, 0.0])
        await _seed_memory(session_factory, content="cats purr loudly",
                           embedding_json=[0.9, 0.1, 0.0])

        result = await backend.dispatch("search_memory", {
            "query_embedding": [1.0, 0.0, 0.0],
            "limit": 10,
        })
        assert result["ok"] is True
        assert result["count"] == 3
        # First result should be closest to [1,0,0]
        assert result["results"][0]["score"] >= result["results"][-1]["score"]

    async def test_search_respects_limit(self, backend, patch_session, session_factory):
        for i in range(5):
            await _seed_memory(session_factory, content=f"memory {i}",
                               embedding_json=[float(i), 0.0, 0.0])
        result = await backend.dispatch("search_memory", {
            "query_embedding": [0.0, 0.0, 0.0],
            "limit": 2,
        })
        assert result["ok"] is True
        assert result["count"] == 2

    async def test_search_missing_embedding(self, backend, patch_session):
        result = await backend.dispatch("search_memory", {"limit": 5})
        assert result["ok"] is False
        assert "query_embedding" in result["error"]

    async def test_search_empty_database(self, backend, patch_session):
        result = await backend.dispatch("search_memory", {
            "query_embedding": [1.0, 0.0],
        })
        assert result["ok"] is True
        assert result["count"] == 0

    async def test_search_by_collection(self, backend, patch_session, session_factory):
        await _seed_memory(session_factory, content="in alpha",
                           collection="alpha", embedding_json=[1.0, 0.0])
        await _seed_memory(session_factory, content="in beta",
                           collection="beta", embedding_json=[1.0, 0.0])

        result = await backend.dispatch("search_memory", {
            "query_embedding": [1.0, 0.0],
            "collection": "alpha",
        })
        assert result["ok"] is True
        assert result["count"] == 1
        assert result["results"][0]["collection"] == "alpha"


# ===========================================================================
# 4. update_memory (3 tests)
# ===========================================================================

class TestUpdateMemory:
    async def test_update_content(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory)
        result = await backend.dispatch("update_memory", {
            "memory_id": mid,
            "content": "updated content",
        })
        assert result["ok"] is True
        # Verify
        recall = await backend.dispatch("recall_memory", {"memory_id": mid})
        assert recall["memory"]["content"] == "updated content"

    async def test_update_multiple_fields(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory)
        result = await backend.dispatch("update_memory", {
            "memory_id": mid,
            "content": "new content",
            "memory_type": MemoryType.SEMANTIC.value,
            "importance": 5.0,
            "source": "updated",
        })
        assert result["ok"] is True
        recall = await backend.dispatch("recall_memory", {"memory_id": mid})
        assert recall["memory"]["memory_type"] == MemoryType.SEMANTIC.value
        assert recall["memory"]["importance"] == 5.0

    async def test_update_not_found(self, backend, patch_session):
        result = await backend.dispatch("update_memory", {
            "memory_id": "nonexistent",
            "content": "x",
        })
        assert result["ok"] is False
        assert "memory not found" in result["error"]

    async def test_update_missing_id(self, backend, patch_session):
        result = await backend.dispatch("update_memory", {"content": "x"})
        assert result["ok"] is False
        assert "memory_id is required" in result["error"]


# ===========================================================================
# 5. delete_memory (3 tests)
# ===========================================================================

class TestDeleteMemory:
    async def test_delete_existing(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory)
        result = await backend.dispatch("delete_memory", {"memory_id": mid})
        assert result["ok"] is True
        assert result["deleted"] is True
        # Verify gone
        recall = await backend.dispatch("recall_memory", {"memory_id": mid})
        assert recall["ok"] is False

    async def test_delete_not_found(self, backend, patch_session):
        result = await backend.dispatch("delete_memory", {
            "memory_id": "nonexistent",
        })
        assert result["ok"] is False
        assert "memory not found" in result["error"]

    async def test_delete_missing_id(self, backend, patch_session):
        result = await backend.dispatch("delete_memory", {})
        assert result["ok"] is False
        assert "memory_id is required" in result["error"]


# ===========================================================================
# 6. list_memories (3 tests)
# ===========================================================================

class TestListMemories:
    async def test_list_empty(self, backend, patch_session):
        result = await backend.dispatch("list_memories", {})
        assert result["ok"] is True
        assert result["memories"] == []
        assert result["total"] == 0

    async def test_list_with_items(self, backend, patch_session, session_factory):
        for i in range(3):
            await _seed_memory(session_factory, content=f"item {i}")
        result = await backend.dispatch("list_memories", {})
        assert result["ok"] is True
        assert result["total"] == 3
        assert len(result["memories"]) == 3

    async def test_list_pagination(self, backend, patch_session, session_factory):
        for i in range(5):
            await _seed_memory(session_factory, content=f"item {i}")
        result = await backend.dispatch("list_memories", {"limit": 2, "offset": 1})
        assert result["ok"] is True
        assert result["total"] == 5
        assert len(result["memories"]) == 2

    async def test_list_returns_all_fields(self, backend, patch_session, session_factory):
        await _seed_memory(session_factory)
        result = await backend.dispatch("list_memories", {})
        mem = result["memories"][0]
        assert "id" in mem
        assert "content" in mem
        assert "memory_type" in mem
        assert "created_at" in mem


# ===========================================================================
# 7. get_memory_by_id (3 tests)
# ===========================================================================

class TestGetMemoryById:
    async def test_get_by_id(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory, content="hello from alias")
        result = await backend.dispatch("get_memory_by_id", {"memory_id": mid})
        assert result["ok"] is True
        assert result["memory"]["content"] == "hello from alias"

    async def test_get_by_id_not_found(self, backend, patch_session):
        result = await backend.dispatch("get_memory_by_id", {
            "memory_id": "missing",
        })
        assert result["ok"] is False

    async def test_get_by_id_missing_id(self, backend, patch_session):
        result = await backend.dispatch("get_memory_by_id", {})
        assert result["ok"] is False
        assert "memory_id is required" in result["error"]


# ===========================================================================
# 8. get_memories_by_type (3 tests)
# ===========================================================================

class TestGetMemoriesByType:
    async def test_filter_by_type(self, backend, patch_session, session_factory):
        await _seed_memory(session_factory, content="ep1",
                           memory_type=MemoryType.EPISODIC.value)
        await _seed_memory(session_factory, content="sem1",
                           memory_type=MemoryType.SEMANTIC.value)
        await _seed_memory(session_factory, content="ep2",
                           memory_type=MemoryType.EPISODIC.value)

        result = await backend.dispatch("get_memories_by_type", {
            "memory_type": MemoryType.EPISODIC.value,
        })
        assert result["ok"] is True
        assert result["count"] == 2
        assert all(m["memory_type"] == "episodic" for m in result["memories"])

    async def test_filter_by_type_no_results(self, backend, patch_session, session_factory):
        await _seed_memory(session_factory, content="x",
                           memory_type=MemoryType.EPISODIC.value)
        result = await backend.dispatch("get_memories_by_type", {
            "memory_type": MemoryType.PROCEDURAL.value,
        })
        assert result["ok"] is True
        assert result["count"] == 0

    async def test_filter_by_type_missing(self, backend, patch_session):
        result = await backend.dispatch("get_memories_by_type", {})
        assert result["ok"] is False
        assert "memory_type is required" in result["error"]


# ===========================================================================
# 9. get_memories_by_time_range (3 tests)
# ===========================================================================

class TestGetMemoriesByTimeRange:
    async def test_filter_by_range(self, backend, patch_session, session_factory):
        now = datetime.now(timezone.utc)
        await _seed_memory(session_factory, content="recent",
                           created_at=now)
        await _seed_memory(session_factory, content="old",
                           created_at=now - timedelta(days=30))

        start = (now - timedelta(hours=1)).isoformat()
        end = (now + timedelta(hours=1)).isoformat()
        result = await backend.dispatch("get_memories_by_time_range", {
            "start_date": start,
            "end_date": end,
        })
        assert result["ok"] is True
        assert result["count"] == 1
        assert result["memories"][0]["content"] == "recent"

    async def test_filter_range_no_results(self, backend, patch_session, session_factory):
        now = datetime.now(timezone.utc)
        await _seed_memory(session_factory, content="x", created_at=now)
        far_future = (now + timedelta(days=365)).isoformat()
        result = await backend.dispatch("get_memories_by_time_range", {
            "start_date": far_future,
            "end_date": far_future,
        })
        assert result["ok"] is True
        assert result["count"] == 0

    async def test_filter_range_missing_dates(self, backend, patch_session):
        result = await backend.dispatch("get_memories_by_time_range", {
            "start_date": "2025-01-01",
        })
        assert result["ok"] is False
        assert "start_date and end_date" in result["error"]


# ===========================================================================
# 10. consolidate_memories (3 tests)
# ===========================================================================

class TestConsolidateMemories:
    async def test_consolidate_two(self, backend, patch_session, session_factory):
        m1 = await _seed_memory(session_factory, content="first part",
                                embedding_json=[1.0, 0.0])
        m2 = await _seed_memory(session_factory, content="second part",
                                embedding_json=[0.0, 1.0])

        result = await backend.dispatch("consolidate_memories", {
            "memory_ids": [m1, m2],
        })
        assert result["ok"] is True
        assert result["source_count"] == 2
        assert "merged_id" in result
        # Verify originals deleted
        r1 = await backend.dispatch("recall_memory", {"memory_id": m1})
        assert r1["ok"] is False

    async def test_consolidate_insufficient_ids(self, backend, patch_session):
        result = await backend.dispatch("consolidate_memories", {
            "memory_ids": ["only-one"],
        })
        assert result["ok"] is False
        assert "at least 2" in result["error"]

    async def test_consolidate_empty_ids(self, backend, patch_session):
        result = await backend.dispatch("consolidate_memories", {
            "memory_ids": [],
        })
        assert result["ok"] is False

    async def test_consolidate_preserves_max_importance(
        self, backend, patch_session, session_factory
    ):
        m1 = await _seed_memory(session_factory, content="a", importance=2.0)
        m2 = await _seed_memory(session_factory, content="b", importance=5.0)
        result = await backend.dispatch("consolidate_memories", {
            "memory_ids": [m1, m2],
        })
        assert result["ok"] is True
        recall = await backend.dispatch("recall_memory", {
            "memory_id": result["merged_id"],
        })
        assert recall["memory"]["importance"] == 5.0


# ===========================================================================
# 11. export_memories (3 tests)
# ===========================================================================

class TestExportMemories:
    async def test_export_empty(self, backend, patch_session):
        result = await backend.dispatch("export_memories", {})
        assert result["ok"] is True
        assert result["memories"] == []
        assert result["count"] == 0

    async def test_export_with_items(self, backend, patch_session, session_factory):
        await _seed_memory(session_factory, content="a")
        await _seed_memory(session_factory, content="b")
        result = await backend.dispatch("export_memories", {})
        assert result["ok"] is True
        assert result["count"] == 2
        assert isinstance(result["memories"], list)
        # Verify serialisable
        json.dumps(result["memories"])

    async def test_export_fields_present(self, backend, patch_session, session_factory):
        await _seed_memory(session_factory, content="x",
                           metadata_json={"k": "v"})
        result = await backend.dispatch("export_memories", {})
        mem = result["memories"][0]
        assert "id" in mem
        assert "content" in mem
        assert "memory_type" in mem
        assert "embedding" in mem
        assert "metadata" in mem


# ===========================================================================
# 12. import_memories (3 tests)
# ===========================================================================

class TestImportMemories:
    async def test_import_basic(self, backend, patch_session):
        result = await backend.dispatch("import_memories", {
            "memories": [
                {"content": "imported 1", "memory_type": "semantic"},
                {"content": "imported 2", "metadata": {"tag": "x"}},
            ],
        })
        assert result["ok"] is True
        assert result["imported"] == 2
        assert result["errors"] == []

    async def test_import_skips_empty_content(self, backend, patch_session):
        result = await backend.dispatch("import_memories", {
            "memories": [
                {"content": "valid"},
                {"content": ""},
                {"metadata": {"no": "content"}},
            ],
        })
        assert result["ok"] is True
        assert result["imported"] == 1
        assert len(result["errors"]) == 2

    async def test_import_empty_list(self, backend, patch_session):
        result = await backend.dispatch("import_memories", {
            "memories": [],
        })
        assert result["ok"] is True
        assert result["imported"] == 0

    async def test_import_invalid_type(self, backend, patch_session):
        result = await backend.dispatch("import_memories", {
            "memories": "not a list",
        })
        assert result["ok"] is False
        assert "memories must be a list" in result["error"]

    async def test_import_verifies_stored(self, backend, patch_session, session_factory):
        await backend.dispatch("import_memories", {
            "memories": [{"content": "verify me"}],
        })
        result = await backend.dispatch("list_memories", {})
        assert result["total"] == 1
        assert result["memories"][0]["content"] == "verify me"


# ===========================================================================
# 13. get_memory_stats (3 tests)
# ===========================================================================

class TestGetMemoryStats:
    async def test_stats_empty(self, backend, patch_session):
        result = await backend.dispatch("get_memory_stats", {})
        assert result["ok"] is True
        assert result["total_count"] == 0
        assert result["by_type"] == {}

    async def test_stats_counts_by_type(self, backend, patch_session, session_factory):
        await _seed_memory(session_factory, content="ep",
                           memory_type=MemoryType.EPISODIC.value)
        await _seed_memory(session_factory, content="sem",
                           memory_type=MemoryType.SEMANTIC.value)
        await _seed_memory(session_factory, content="ep2",
                           memory_type=MemoryType.EPISODIC.value)

        result = await backend.dispatch("get_memory_stats", {})
        assert result["ok"] is True
        assert result["total_count"] == 3
        assert result["by_type"]["episodic"] == 2
        assert result["by_type"]["semantic"] == 1

    async def test_stats_reports_size(self, backend, patch_session, session_factory):
        await _seed_memory(session_factory, content="hello")
        await _seed_memory(session_factory, content="world!")
        result = await backend.dispatch("get_memory_stats", {})
        assert result["ok"] is True
        assert result["total_size"] == len("hello") + len("world!")


# ===========================================================================
# 14. create_memory_collection (3 tests)
# ===========================================================================

class TestCreateMemoryCollection:
    async def test_create_collection(self, backend, patch_session):
        result = await backend.dispatch("create_memory_collection", {
            "name": "project-alpha",
            "description": "Alpha project notes",
        })
        assert result["ok"] is True
        assert result["name"] == "project-alpha"
        assert "collection_id" in result

    async def test_create_duplicate_collection(self, backend, patch_session):
        await backend.dispatch("create_memory_collection", {"name": "dup"})
        result = await backend.dispatch("create_memory_collection", {"name": "dup"})
        assert result["ok"] is False
        assert "already exists" in result["error"]

    async def test_create_collection_missing_name(self, backend, patch_session):
        result = await backend.dispatch("create_memory_collection", {})
        assert result["ok"] is False
        assert "name is required" in result["error"]


# ===========================================================================
# 15. delete_memory_collection (3 tests)
# ===========================================================================

class TestDeleteMemoryCollection:
    async def test_delete_collection(self, backend, patch_session):
        await backend.dispatch("create_memory_collection", {"name": "to-delete"})
        result = await backend.dispatch("delete_memory_collection", {
            "name": "to-delete",
        })
        assert result["ok"] is True
        assert result["deleted"] is True

    async def test_delete_not_found(self, backend, patch_session):
        result = await backend.dispatch("delete_memory_collection", {
            "name": "nonexistent",
        })
        assert result["ok"] is False
        assert "collection not found" in result["error"]

    async def test_delete_missing_name(self, backend, patch_session):
        result = await backend.dispatch("delete_memory_collection", {})
        assert result["ok"] is False
        assert "name is required" in result["error"]


# ===========================================================================
# 16. list_memory_collections (3 tests)
# ===========================================================================

class TestListMemoryCollections:
    async def test_list_empty(self, backend, patch_session):
        result = await backend.dispatch("list_memory_collections", {})
        assert result["ok"] is True
        assert result["collections"] == []
        assert result["count"] == 0

    async def test_list_with_items(self, backend, patch_session):
        await backend.dispatch("create_memory_collection", {"name": "alpha"})
        await backend.dispatch("create_memory_collection", {"name": "beta"})
        result = await backend.dispatch("list_memory_collections", {})
        assert result["ok"] is True
        assert result["count"] == 2
        names = {c["name"] for c in result["collections"]}
        assert names == {"alpha", "beta"}

    async def test_list_returns_fields(self, backend, patch_session):
        await backend.dispatch("create_memory_collection", {
            "name": "gamma", "description": "test",
        })
        result = await backend.dispatch("list_memory_collections", {})
        c = result["collections"][0]
        assert "id" in c
        assert "name" in c
        assert "description" in c
        assert "created_at" in c


# ===========================================================================
# 17. set_memory_metadata (3 tests)
# ===========================================================================

class TestSetMemoryMetadata:
    async def test_set_metadata_new(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory, metadata_json=None)
        result = await backend.dispatch("set_memory_metadata", {
            "memory_id": mid,
            "metadata": {"key": "value", "count": 42},
        })
        assert result["ok"] is True
        # Verify
        meta = await backend.dispatch("get_memory_metadata", {"memory_id": mid})
        assert meta["metadata"]["key"] == "value"
        assert meta["metadata"]["count"] == 42

    async def test_set_metadata_merge(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory, metadata_json={"a": 1, "b": 2})
        result = await backend.dispatch("set_memory_metadata", {
            "memory_id": mid,
            "metadata": {"b": 99, "c": 3},
        })
        assert result["ok"] is True
        meta = await backend.dispatch("get_memory_metadata", {"memory_id": mid})
        assert meta["metadata"]["a"] == 1
        assert meta["metadata"]["b"] == 99
        assert meta["metadata"]["c"] == 3

    async def test_set_metadata_not_found(self, backend, patch_session):
        result = await backend.dispatch("set_memory_metadata", {
            "memory_id": "missing",
            "metadata": {"x": 1},
        })
        assert result["ok"] is False
        assert "memory not found" in result["error"]

    async def test_set_metadata_missing_id(self, backend, patch_session):
        result = await backend.dispatch("set_memory_metadata", {
            "metadata": {"x": 1},
        })
        assert result["ok"] is False
        assert "memory_id is required" in result["error"]


# ===========================================================================
# 18. get_memory_metadata (3 tests)
# ===========================================================================

class TestGetMemoryMetadata:
    async def test_get_metadata(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory, metadata_json={"foo": "bar"})
        result = await backend.dispatch("get_memory_metadata", {
            "memory_id": mid,
        })
        assert result["ok"] is True
        assert result["metadata"]["foo"] == "bar"

    async def test_get_metadata_empty(self, backend, patch_session, session_factory):
        mid = await _seed_memory(session_factory, metadata_json=None)
        result = await backend.dispatch("get_memory_metadata", {
            "memory_id": mid,
        })
        assert result["ok"] is True
        assert result["metadata"] == {}

    async def test_get_metadata_not_found(self, backend, patch_session):
        result = await backend.dispatch("get_memory_metadata", {
            "memory_id": "missing",
        })
        assert result["ok"] is False
        assert "memory not found" in result["error"]

    async def test_get_metadata_missing_id(self, backend, patch_session):
        result = await backend.dispatch("get_memory_metadata", {})
        assert result["ok"] is False
        assert "memory_id is required" in result["error"]


# ===========================================================================
# Integration / cross-cutting tests
# ===========================================================================

class TestActionCatalogue:
    def test_name(self, backend):
        assert backend.name == "memory"

    def test_is_available(self, backend):
        assert backend.is_available() is True

    def test_action_count(self, backend):
        actions = backend.actions()
        assert len(actions) == 18

    def test_action_names_unique(self, backend):
        names = [a.name for a in backend.actions()]
        assert len(names) == len(set(names))

    def test_find_action(self, backend):
        assert backend.find_action("store_memory") is not None
        assert backend.find_action("nonexistent") is None

    def test_l3_actions(self, backend):
        l3 = [a.name for a in backend.actions()
              if a.label.value == "L3"]
        assert "delete_memory" in l3

    def test_l2_actions(self, backend):
        l2 = [a.name for a in backend.actions()
              if a.label.value == "L2"]
        assert "store_memory" in l2
        assert "create_memory_collection" in l2

    def test_l1_actions(self, backend):
        l1 = [a.name for a in backend.actions()
              if a.label.value == "L1"]
        assert "recall_memory" in l1
        assert "search_memory" in l1


class TestFailSoft:
    async def test_unknown_action(self, backend, patch_session):
        result = await backend.dispatch("nonexistent_xyz", {})
        assert result["ok"] is False
        assert "error" in result

    async def test_dispatch_never_raises(self, backend, patch_session):
        """dispatch() must NEVER raise to caller."""
        result = await backend.dispatch("recall_memory", {"bad_key": [1]})
        assert isinstance(result, dict)
        assert "ok" in result

    async def test_all_actions_return_dict(self, backend, patch_session):
        """Every action returns a dict with 'ok' key."""
        for action in backend.actions():
            result = await backend.dispatch(action.name, {})
            assert isinstance(result, dict), f"{action.name} did not return dict"
            assert "ok" in result, f"{action.name} missing 'ok' key"


class TestMemoryType:
    def test_all_enum_values(self):
        values = {e.value for e in MemoryType}
        assert "episodic" in values
        assert "semantic" in values
        assert "procedural" in values
        assert "working" in values
        assert "emotional" in values
        assert "relationship" in values

    def test_enum_count(self):
        assert len(MemoryType) == 6

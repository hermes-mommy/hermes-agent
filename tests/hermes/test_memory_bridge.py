"""Unit tests for HermesMemoryBridge — Phase 2."""
from __future__ import annotations

import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# Prevent transitive import failure from src/hermes/__init__.py -> session_adapter
_FAKE_MODULES = ("run_agent", "redis", "redis.asyncio")
for _mod in _FAKE_MODULES:
    sys.modules.setdefault(_mod, MagicMock())

import pytest

from src.hermes.memory_bridge import HermesMemoryBridge  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class MockAsyncSession:
    """Fake async session for context manager protocol."""

    async def __aenter__(self) -> MockAsyncSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def commit(self) -> None:
        """No-op commit for store_conversation() to call."""


def make_session_factory() -> MagicMock:
    """Returns a callable that returns an async context manager."""
    session = MockAsyncSession()
    return MagicMock(return_value=session)


# ---------------------------------------------------------------------------
# TestRecallForContext
# ---------------------------------------------------------------------------


class TestRecallForContext:
    """Tests for HermesMemoryBridge.recall_for_context()."""

    @pytest.mark.asyncio
    @patch("src.memory.read_pipeline.recall_memories", new_callable=AsyncMock)
    async def test_recall_returns_results(
        self, mock_recall: AsyncMock,
    ) -> None:
        """Mock recall_memories to return list of dicts. Bridge returns them."""
        expected = [
            {
                "id": "abc-123",
                "safe_content": "remember this",
                "classification": "Internal",
                "importance": 5,
                "created_at": "2026-01-01",
                "combined_score": 0.85,
                "is_summarized": False,
            },
        ]
        mock_recall.return_value = expected

        bridge = HermesMemoryBridge(make_session_factory())
        results = await bridge.recall_for_context("test query")

        assert results == expected
        assert len(results) == 1

    @pytest.mark.asyncio
    @patch("src.memory.read_pipeline.recall_memories", new_callable=AsyncMock)
    async def test_recall_empty_query_returns_empty(
        self, mock_recall: AsyncMock,
    ) -> None:
        """Empty query triggers ReadPipelineQueryError — bridge returns []."""
        from src.memory.read_pipeline import ReadPipelineQueryError  # noqa: PLC0415

        mock_recall.side_effect = ReadPipelineQueryError(
            "query_text must be non-empty for memory recall"
        )

        bridge = HermesMemoryBridge(make_session_factory())
        results = await bridge.recall_for_context("")

        assert results == []

    @pytest.mark.asyncio
    async def test_recall_db_error_returns_empty(self) -> None:
        """Session factory raising Exception — bridge returns []."""
        factory = MagicMock(side_effect=RuntimeError("DB connection lost"))

        bridge = HermesMemoryBridge(factory)
        results = await bridge.recall_for_context("any query")

        assert results == []

    @pytest.mark.asyncio
    @patch("src.memory.read_pipeline.recall_memories", new_callable=AsyncMock)
    async def test_recall_passes_safe_mode(
        self, mock_recall: AsyncMock,
    ) -> None:
        """Verify safe_mode=True is forwarded to recall_memories."""
        mock_recall.return_value = []

        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.recall_for_context("query", safe_mode=True)

        kwargs = mock_recall.call_args[1]
        assert kwargs["safe_mode"] is True

    @pytest.mark.asyncio
    @patch("src.memory.read_pipeline.recall_memories", new_callable=AsyncMock)
    async def test_recall_passes_principal(
        self, mock_recall: AsyncMock,
    ) -> None:
        """Verify custom principal is forwarded to recall_memories."""
        mock_recall.return_value = []

        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.recall_for_context("query", principal="custom_agent")

        kwargs = mock_recall.call_args[1]
        assert kwargs["principal"] == "custom_agent"

    @pytest.mark.asyncio
    @patch("src.memory.read_pipeline.recall_memories", new_callable=AsyncMock)
    async def test_recall_passes_limit_and_budget(
        self, mock_recall: AsyncMock,
    ) -> None:
        """Verify limit=5 and token_budget=800 forwarded to recall_memories."""
        mock_recall.return_value = []

        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.recall_for_context("query", limit=5, token_budget=800)

        kwargs = mock_recall.call_args[1]
        assert kwargs["limit"] == 5
        assert kwargs["token_budget"] == 800

    @pytest.mark.asyncio
    @patch("src.memory.read_pipeline.recall_memories", new_callable=AsyncMock)
    async def test_recall_without_embedding_service(
        self, mock_recall: AsyncMock,
    ) -> None:
        """Bridge created with embedding_service=None passes it through."""
        mock_recall.return_value = []

        bridge = HermesMemoryBridge(
            make_session_factory(), embedding_service=None,
        )
        await bridge.recall_for_context("query")

        kwargs = mock_recall.call_args[1]
        assert kwargs["embedding_service"] is None


# ---------------------------------------------------------------------------
# TestStoreConversation
# ---------------------------------------------------------------------------


class TestStoreConversation:
    """Tests for HermesMemoryBridge.store_conversation()."""

    @pytest.mark.asyncio
    @patch("src.memory.write_pipeline.RESTRICTED", "TEST_RESTRICTED")
    @patch("src.memory.write_pipeline.store_episode", new_callable=AsyncMock)
    async def test_store_returns_episode_id(
        self, mock_store: AsyncMock,
    ) -> None:
        """Mock store_episode returns UUID — bridge returns its str form."""
        test_uuid = uuid.uuid4()
        mock_store.return_value = test_uuid

        bridge = HermesMemoryBridge(make_session_factory())
        result = await bridge.store_conversation(
            "hello", "hi there", "user_hash_123",
        )

        assert result == str(test_uuid)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_store_db_error_returns_none(self) -> None:
        """Session factory raising Exception — bridge returns None."""
        factory = MagicMock(side_effect=RuntimeError("DB connection lost"))

        bridge = HermesMemoryBridge(factory)
        result = await bridge.store_conversation(
            "hello", "hi", "hash123",
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("src.memory.write_pipeline.RESTRICTED", "TEST_RESTRICTED")
    @patch("src.memory.write_pipeline.store_episode", new_callable=AsyncMock)
    async def test_store_uses_restricted_classification(
        self, mock_store: AsyncMock,
    ) -> None:
        """Verify classification=RESTRICTED is passed to store_episode."""
        mock_store.return_value = uuid.uuid4()

        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.store_conversation("hello", "hi", "hash")

        kwargs = mock_store.call_args[1]
        assert kwargs["classification"] == "TEST_RESTRICTED"

    @pytest.mark.asyncio
    @patch("src.memory.write_pipeline.RESTRICTED", "TEST_RESTRICTED")
    @patch("src.memory.write_pipeline.store_episode", new_callable=AsyncMock)
    async def test_store_formats_content_correctly(
        self, mock_store: AsyncMock,
    ) -> None:
        """Verify content is formatted as 'Faiz: {msg}\\nGuinevere: {resp}'."""
        mock_store.return_value = uuid.uuid4()

        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.store_conversation("hello", "hi there", "hash")

        kwargs = mock_store.call_args[1]
        assert kwargs["content"] == "Faiz: hello\nGuinevere: hi there"

    @pytest.mark.asyncio
    @patch("src.memory.write_pipeline.RESTRICTED", "TEST_RESTRICTED")
    @patch("src.memory.write_pipeline.store_episode", new_callable=AsyncMock)
    async def test_store_includes_user_hash_in_tags(
        self, mock_store: AsyncMock,
    ) -> None:
        """Verify tags include 'user:{user_id_hash}'."""
        mock_store.return_value = uuid.uuid4()

        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.store_conversation("hello", "hi", "my_hash_abc")

        kwargs = mock_store.call_args[1]
        assert "user:my_hash_abc" in kwargs["tags"]

    @pytest.mark.asyncio
    @patch("src.memory.write_pipeline.RESTRICTED", "TEST_RESTRICTED")
    @patch("src.memory.write_pipeline.store_episode", new_callable=AsyncMock)
    async def test_store_includes_metadata(
        self, mock_store: AsyncMock,
    ) -> None:
        """Verify metadata dict has channel, user_hash, response_length, safe_mode."""
        mock_store.return_value = uuid.uuid4()

        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.store_conversation("hello", "hi", "hash")

        kwargs = mock_store.call_args[1]
        expected_metadata = {
            "channel": "guinevere-chat",
            "user_hash": "hash",
            "response_length": 2,
            "safe_mode": False,
        }
        assert kwargs["metadata"] == expected_metadata

    @pytest.mark.asyncio
    @patch("src.memory.write_pipeline.RESTRICTED", "TEST_RESTRICTED")
    @patch("src.memory.write_pipeline.store_episode", new_callable=AsyncMock)
    async def test_store_title_truncated(
        self, mock_store: AsyncMock,
    ) -> None:
        """Verify title is user_message[:100]."""
        mock_store.return_value = uuid.uuid4()

        long_msg = "x" * 150
        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.store_conversation(long_msg, "hi", "hash")

        kwargs = mock_store.call_args[1]
        assert kwargs["title"] == long_msg[:100]
        assert len(kwargs["title"]) == 100

    @pytest.mark.asyncio
    @patch("src.memory.write_pipeline.RESTRICTED", "TEST_RESTRICTED")
    @patch("src.memory.write_pipeline.store_episode", new_callable=AsyncMock)
    async def test_store_summary_truncated(
        self, mock_store: AsyncMock,
    ) -> None:
        """Verify summary includes both user + assistant keywords for FTS."""
        mock_store.return_value = uuid.uuid4()

        long_msg = "x" * 300
        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.store_conversation(long_msg, "hi", "hash")

        kwargs = mock_store.call_args[1]
        # Summary now includes both user and assistant text
        assert "Faiz:" in kwargs["summary"]
        assert "Guinevere: hi" in kwargs["summary"]
        assert len(kwargs["summary"]) <= 300


# ---------------------------------------------------------------------------
# TestExtractKeyFacts
# ---------------------------------------------------------------------------


class TestExtractKeyFacts:
    """Tests for HermesMemoryBridge.extract_key_facts()."""

    @pytest.mark.asyncio
    async def test_extract_returns_empty_list(self) -> None:
        """Phase 2 stub always returns []."""
        bridge = HermesMemoryBridge(make_session_factory())
        result = await bridge.extract_key_facts("some conversation text")

        assert result == []
        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch("src.hermes.memory_bridge._logger")
    async def test_extract_logs_invocation(self, mock_logger: MagicMock) -> None:
        """Verify logger.info is called with the stub message."""
        bridge = HermesMemoryBridge(make_session_factory())
        await bridge.extract_key_facts("test conv")

        mock_logger.info.assert_called_once()
        call_args, call_kwargs = mock_logger.info.call_args
        assert call_args[0] == "bridge_extract_key_facts_stub"
        assert call_kwargs["extra"]["conversation_length"] == 9
"""Unit tests for the P18 Memory recall adapter (LK-010, continuation).

The continuation rewrote MemoryRecallAdapter.recall() to call a real
recall_fn (src.memory.read_pipeline.recall_memories) when injected, and to
return ``_degraded: True`` with empty results when no client is available
(instead of returning hardcoded mock ``_placeholder`` data).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

from src.life_kernel.p18_adapter import MemoryRecallAdapter


def _make_recall_result(content: str, score: float = 0.9) -> dict[str, Any]:
    """Build one recall_memories result dict (real shape)."""
    return {
        "id": f"ep-{content[:6]}",
        "safe_content": content,
        "classification": "Public",
        "importance": 5,
        "created_at": datetime.now(timezone.utc),
        "combined_score": score,
        "is_summarized": False,
    }


class TestMemoryRecallAdapterDegraded:
    """Without a real recall_fn the adapter must degrade, not mock."""

    async def test_no_client_returns_degraded(self) -> None:
        adapter = MemoryRecallAdapter()
        result = await adapter.recall({"query": "anything"})

        assert result["_degraded"] is True
        assert result["memories"] == []
        assert result["count"] == 0
        # Must NOT carry the old placeholder flag
        assert result.get("_placeholder") is None

    async def test_degraded_includes_timestamp(self) -> None:
        adapter = MemoryRecallAdapter()
        result = await adapter.recall({})

        assert "_timestamp" in result
        assert result["_degraded"] is True

    def test_default_client_is_none(self) -> None:
        adapter = MemoryRecallAdapter()
        assert adapter.memory_client is None


class TestMemoryRecallAdapterReal:
    """With a real recall_fn injected the adapter must return real data."""

    async def test_real_recall_returns_memories(self) -> None:
        recall_fn = AsyncMock(return_value=[_make_recall_result("finance review", 0.9)])
        adapter = MemoryRecallAdapter(memory_client=recall_fn)

        result = await adapter.recall({"query": "finance"})

        assert result["count"] == 1
        assert result["memories"][0]["content"] == "finance review"
        assert result["memories"][0]["relevance"] == 0.9
        # Real recall must NOT set _placeholder or _degraded
        assert result.get("_placeholder") is None
        assert result.get("_degraded") is None
        recall_fn.assert_awaited_once()

    async def test_real_recall_passes_query_text(self) -> None:
        recall_fn = AsyncMock(return_value=[_make_recall_result("x")])
        adapter = MemoryRecallAdapter(memory_client=recall_fn)

        await adapter.recall({"query": "email priority"})

        call_kwargs = recall_fn.await_args.kwargs
        assert call_kwargs["query_text"] == "email priority"
        assert call_kwargs["principal"] == "guinevere_core"
        assert call_kwargs["exclude_dnr"] is True

    async def test_real_recall_handles_empty_results(self) -> None:
        recall_fn = AsyncMock(return_value=[])
        adapter = MemoryRecallAdapter(memory_client=recall_fn)

        result = await adapter.recall({"query": "nothing"})

        assert result["count"] == 0
        assert result["memories"] == []
        assert result.get("_degraded") is None

    async def test_real_recall_failure_degrades(self) -> None:
        recall_fn = AsyncMock(side_effect=RuntimeError("DB down"))
        adapter = MemoryRecallAdapter(memory_client=recall_fn)

        result = await adapter.recall({"query": "test"})

        assert result["_degraded"] is True
        assert result["memories"] == []
        # Kernel must not crash on recall failure
        assert result["count"] == 0

    async def test_real_recall_count_matches(self) -> None:
        recall_fn = AsyncMock(
            return_value=[_make_recall_result("a"), _make_recall_result("b")]
        )
        adapter = MemoryRecallAdapter(memory_client=recall_fn)

        result = await adapter.recall({"query": "q"})

        assert result["count"] == len(result["memories"]) == 2


class TestMemoryRecallAdapterSync:
    def test_adapter_instantiation(self) -> None:
        adapter = MemoryRecallAdapter()
        assert isinstance(adapter, MemoryRecallAdapter)

    def test_adapter_stores_client_reference(self) -> None:
        dummy = object()
        adapter = MemoryRecallAdapter(memory_client=dummy)
        assert adapter.memory_client is dummy


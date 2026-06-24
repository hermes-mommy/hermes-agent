"""Unit tests for the P16 Knowledge Graph recall adapter (LK-010, continuation).

The continuation rewrote KGRecallAdapter.recall() to call a real recall_fn
(wrapping src.knowledge_graph.query) when injected, and to return
``_degraded: True`` with empty results when no client is available — instead
of returning hardcoded mock ``_placeholder`` data.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from src.life_kernel.p16_adapter import KGRecallAdapter


def _make_concept(name: str, relevance: float = 0.9) -> dict[str, Any]:
    return {"name": name, "relevance": relevance, "source": "p16"}


class TestKGRecallAdapterDegraded:
    """Without a real recall_fn the adapter must degrade, not mock."""

    async def test_no_client_returns_degraded(self) -> None:
        adapter = KGRecallAdapter()
        result = await adapter.recall({"query": "anything"})

        assert result["_degraded"] is True
        assert result["concepts"] == []
        assert result["count"] == 0
        assert result.get("_placeholder") is None

    async def test_degraded_includes_timestamp(self) -> None:
        adapter = KGRecallAdapter()
        result = await adapter.recall({})

        assert "_timestamp" in result
        assert result["_degraded"] is True

    def test_default_client_is_none(self) -> None:
        adapter = KGRecallAdapter()
        assert adapter.kg_client is None


class TestKGRecallAdapterReal:
    """With a real recall_fn injected the adapter must return real data."""

    async def test_real_recall_returns_concepts(self) -> None:
        recall_fn = AsyncMock(return_value=[_make_concept("finance_tracking", 0.92)])
        adapter = KGRecallAdapter(kg_client=recall_fn)

        result = await adapter.recall({"query": "finance"})

        assert result["count"] == 1
        assert result["concepts"][0]["name"] == "finance_tracking"
        assert result["concepts"][0]["relevance"] == 0.92
        assert result.get("_placeholder") is None
        assert result.get("_degraded") is None
        recall_fn.assert_awaited_once()

    async def test_real_recall_passes_query_text(self) -> None:
        recall_fn = AsyncMock(return_value=[_make_concept("x")])
        adapter = KGRecallAdapter(kg_client=recall_fn)

        await adapter.recall({"query": "email priority"})

        call_kwargs = recall_fn.await_args.kwargs
        assert call_kwargs["query_text"] == "email priority"

    async def test_real_recall_handles_empty_results(self) -> None:
        recall_fn = AsyncMock(return_value=[])
        adapter = KGRecallAdapter(kg_client=recall_fn)

        result = await adapter.recall({"query": "nothing"})

        assert result["count"] == 0
        assert result["concepts"] == []
        assert result.get("_degraded") is None

    async def test_real_recall_failure_degrades(self) -> None:
        recall_fn = AsyncMock(side_effect=RuntimeError("KG down"))
        adapter = KGRecallAdapter(kg_client=recall_fn)

        result = await adapter.recall({"query": "test"})

        assert result["_degraded"] is True
        assert result["concepts"] == []
        assert result["count"] == 0

    async def test_real_recall_count_matches(self) -> None:
        recall_fn = AsyncMock(return_value=[_make_concept("a"), _make_concept("b")])
        adapter = KGRecallAdapter(kg_client=recall_fn)

        result = await adapter.recall({"query": "q"})

        assert result["count"] == len(result["concepts"]) == 2


class TestKGRecallAdapterSync:
    def test_adapter_instantiation(self) -> None:
        adapter = KGRecallAdapter()
        assert isinstance(adapter, KGRecallAdapter)

    def test_adapter_stores_client_reference(self) -> None:
        dummy = object()
        adapter = KGRecallAdapter(kg_client=dummy)
        assert adapter.kg_client is dummy

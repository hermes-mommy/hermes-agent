"""Unit tests for the Living Autonomy Kernel decision context builder (LK-010)."""

from __future__ import annotations

from src.life_kernel.decision_context import DecisionContextBuilder
from src.life_kernel.p16_adapter import KGRecallAdapter
from src.life_kernel.p18_adapter import MemoryRecallAdapter
from src.life_kernel.state import LifeMindState


class TestDecisionContextBuilder:
    """Test suite for DecisionContextBuilder."""

    async def test_build_returns_required_keys(self) -> None:
        """Builder must return a dict with the required top-level keys."""
        builder = DecisionContextBuilder()
        state: LifeMindState = {"observations": [], "decision_context": {}}
        result = await builder.build(state)

        assert "kg_concepts" in result
        assert "memory_signals" in result
        assert "enriched_context" in result
        assert "source_timestamp" in result

    async def test_build_uses_latest_observation_as_seed(self) -> None:
        """Builder should use the most recent observation as the recall seed."""
        builder = DecisionContextBuilder()
        state: LifeMindState = {
            "observations": [{"content": "goal planning"}],
            "decision_context": {},
        }
        result = await builder.build(state)
        enriched = result["enriched_context"]

        assert enriched["seed"] == {"content": "goal planning"}

    async def test_build_enriched_context_contains_summaries(self) -> None:
        """Enriched context must contain kg_summary and memory_summary."""
        builder = DecisionContextBuilder()
        state: LifeMindState = {"observations": [], "decision_context": {}}
        result = await builder.build(state)
        enriched = result["enriched_context"]

        assert "kg_summary" in enriched
        assert "memory_summary" in enriched
        assert "top_concepts" in enriched["kg_summary"]
        assert "top_memories" in enriched["memory_summary"]
        assert "count" in enriched["kg_summary"]
        assert "count" in enriched["memory_summary"]

    async def test_build_kg_concepts_is_list(self) -> None:
        """kg_concepts must be a list of concept dicts."""
        builder = DecisionContextBuilder()
        state: LifeMindState = {"observations": [], "decision_context": {}}
        result = await builder.build(state)

        assert isinstance(result["kg_concepts"], list)
        for concept in result["kg_concepts"]:
            assert "name" in concept
            assert "relevance" in concept

    async def test_build_memory_signals_is_list(self) -> None:
        """memory_signals must be a list of memory dicts."""
        builder = DecisionContextBuilder()
        state: LifeMindState = {"observations": [], "decision_context": {}}
        result = await builder.build(state)

        assert isinstance(result["memory_signals"], list)
        for memory in result["memory_signals"]:
            assert "content" in memory
            assert "relevance" in memory

    async def test_build_source_timestamp_is_iso_string(self) -> None:
        """source_timestamp should be a non-empty ISO timestamp string."""
        builder = DecisionContextBuilder()
        state: LifeMindState = {"observations": [], "decision_context": {}}
        result = await builder.build(state)

        assert isinstance(result["source_timestamp"], str)
        assert len(result["source_timestamp"]) > 0

    async def test_build_does_not_mutate_state(self) -> None:
        """Builder must not mutate the provided state."""
        builder = DecisionContextBuilder()
        original: LifeMindState = {
            "observations": [{"content": "seed"}],
            "decision_context": {"key": "value"},
        }
        state_copy: LifeMindState = {
            "observations": [{"content": "seed"}],
            "decision_context": {"key": "value"},
        }
        await builder.build(state_copy)

        assert state_copy == original

    async def test_build_with_custom_adapters(self) -> None:
        """Builder should use injected adapters and produce expected structure.

        Uses real recall_fn-backed adapters (mock callables) to verify the
        builder forwards to them and aggregates results — replacing the old
        placeholder-mock contract.
        """
        from unittest.mock import AsyncMock

        kg_adapter = KGRecallAdapter(
            kg_client=AsyncMock(return_value=[
                {"name": "concept_a", "relevance": 0.9, "source": "p16"},
            ])
        )
        memory_adapter = MemoryRecallAdapter(
            memory_client=AsyncMock(return_value=[
                {"content": "memory_a", "relevance": 0.8, "timestamp": "2026-06-24T00:00:00Z"},
            ])
        )
        builder = DecisionContextBuilder(
            kg_adapter=kg_adapter,
            memory_adapter=memory_adapter,
        )
        state: LifeMindState = {"observations": [], "decision_context": {}}
        result = await builder.build(state)

        assert len(result["kg_concepts"]) > 0
        assert len(result["memory_signals"]) > 0
        assert result["enriched_context"]["kg_summary"]["count"] == len(
            result["kg_concepts"]
        )
        assert result["enriched_context"]["memory_summary"]["count"] == len(
            result["memory_signals"]
        )

    async def test_build_handles_non_dict_observation(self) -> None:
        """Builder should handle observations that are not dicts."""
        builder = DecisionContextBuilder()
        state: LifeMindState = {
            "observations": ["unexpected string"],  # type: ignore[list-item]
            "decision_context": {},
        }
        result = await builder.build(state)

        assert "kg_concepts" in result
        assert "memory_signals" in result

    async def test_default_adapters_created_when_none_provided(self) -> None:
        """Builder should create default adapters if none are supplied."""
        builder = DecisionContextBuilder()

        assert isinstance(builder.kg_adapter, KGRecallAdapter)
        assert isinstance(builder.memory_adapter, MemoryRecallAdapter)


class TestDecisionContextBuilderExports:
    """Synchronous checks for builder class exports."""

    def test_decision_context_builder_importable(self) -> None:
        """DecisionContextBuilder should be importable from life_kernel."""
        from src.life_kernel import DecisionContextBuilder as ImportedBuilder

        assert ImportedBuilder is DecisionContextBuilder

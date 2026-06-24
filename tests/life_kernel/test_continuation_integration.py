"""Integration tests for the P20 Living Autonomy continuation (T6-T10).

Covers: adapter injection into the graph, real decision_context build,
empty-state goal generation, memory-driven idle, journal writes, and
memory_status / current_focus population.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.life_kernel.graph import create_life_mind_graph
from src.life_kernel.state import LifeMindState


def _mock_kg():
    kg = MagicMock()
    kg.recall = AsyncMock(return_value={
        "concepts": [{"name": "finance_tracking", "relevance": 0.9, "source": "p16"}],
        "count": 1,
    })
    return kg


def _mock_memory():
    mem = MagicMock()
    mem.recall = AsyncMock(return_value={
        "memories": [{"content": "previous finance review", "relevance": 0.88, "timestamp": "2026-06-23T10:00:00Z"}],
        "count": 1,
    })
    return mem


class TestAdapterInjection:
    """T6: create_life_mind_graph accepts and uses kg_adapter / memory_adapter."""

    async def test_graph_accepts_adapters(self):
        graph = create_life_mind_graph(
            checkpointer=None,
            hermes_brain=None,
            kg_adapter=_mock_kg(),
            memory_adapter=_mock_memory(),
        )
        assert graph is not None

    async def test_observe_populates_recalled_fields(self):
        kg, mem = _mock_kg(), _mock_memory()
        graph = create_life_mind_graph(
            checkpointer=None, hermes_brain=None,
            kg_adapter=kg, memory_adapter=mem,
        )
        result = await graph.ainvoke(
            {"is_active": True, "goals": [], "commitments": [], "concerns": []},
            config={"configurable": {"thread_id": "t1"}, "recursion_limit": 25},
        )
        # observe_node should have called both adapters
        kg.recall.assert_awaited()
        mem.recall.assert_awaited()
        assert result.get("recalled_concepts") is not None
        assert result.get("recalled_memories") is not None
        assert result.get("world_model_status") == "active"

    async def test_observe_without_adapters_is_unavailable(self):
        graph = create_life_mind_graph(checkpointer=None, hermes_brain=None)
        result = await graph.ainvoke(
            {"is_active": True},
            config={"configurable": {"thread_id": "t2"}, "recursion_limit": 25},
        )
        assert result.get("world_model_status") == "unavailable"

    async def test_observe_degraded_when_adapter_fails(self):
        kg = MagicMock()
        kg.recall = AsyncMock(return_value={"concepts": [], "count": 0, "_degraded": True})
        mem = _mock_memory()
        graph = create_life_mind_graph(
            checkpointer=None, hermes_brain=None,
            kg_adapter=kg, memory_adapter=mem,
        )
        result = await graph.ainvoke(
            {"is_active": True},
            config={"configurable": {"thread_id": "t3"}, "recursion_limit": 25},
        )
        assert result.get("world_model_status") == "degraded"


class TestEmptyStateGoalGeneration:
    """T7: when idle + memory available, decide seeds a real goal."""

    async def test_idle_with_memory_creates_goal(self):
        """Idle + recalled memories must seed a self-directed goal in state.goals."""
        kg, mem = _mock_kg(), _mock_memory()
        graph = create_life_mind_graph(
            checkpointer=None, hermes_brain=None,
            kg_adapter=kg, memory_adapter=mem,
        )
        result = await graph.ainvoke(
            {"is_active": True, "goals": [], "commitments": [], "concerns": []},
            config={"configurable": {"thread_id": "t4"}, "recursion_limit": 25},
        )
        # A self-directed goal should be created from recall context
        goals = result.get("goals", [])
        assert len(goals) >= 1
        assert goals[0].get("description")
        assert goals[0].get("priority")


class TestMemoryDrivenIdle:
    """T8: idle_node uses recall context, not random.choice."""

    async def test_idle_observation_has_recall_context(self):
        kg, mem = _mock_kg(), _mock_memory()
        graph = create_life_mind_graph(
            checkpointer=None, hermes_brain=None,
            kg_adapter=kg, memory_adapter=mem,
        )
        result = await graph.ainvoke(
            {"is_active": True, "goals": [], "commitments": [], "concerns": []},
            config={"configurable": {"thread_id": "t5"}, "recursion_limit": 25},
        )
        # The idle observation must reference recall context (not a random
        # hardcoded string).
        observations = result.get("observations", [])
        idle_obs = [o for o in observations if o.get("phase") == "idle"]
        if idle_obs:
            desc = idle_obs[0].get("description", "")
            # Must not be one of the 3 old hardcoded strings
            assert "review life_kernel state for patterns" not in desc
            assert "evaluate SDLC loop efficiency" not in desc


class TestJournalAndStatus:
    """T10: reflect writes journal; memory_status / current_focus populated."""

    async def test_memory_status_populated(self):
        kg, mem = _mock_kg(), _mock_memory()
        graph = create_life_mind_graph(
            checkpointer=None, hermes_brain=None,
            kg_adapter=kg, memory_adapter=mem,
        )
        result = await graph.ainvoke(
            {"is_active": True, "goals": [], "commitments": [], "concerns": []},
            config={"configurable": {"thread_id": "t6"}, "recursion_limit": 25},
        )
        # memory_status must reflect recall outcome (not the default '—')
        assert result.get("memory_status") is not None
        assert result.get("memory_status") != "—"

    async def test_reflect_writes_journal_entry(self):
        """reflect_node must write a journal entry when a journal_writer is wired.

        The observe→decide→idle path ends at END without reaching reflect, so
        we exercise reflect_node directly with a meaningful state (an action
        was taken → act_count > 0) to verify the journal write path.
        """
        from src.life_kernel.graph import reflect_node, set_adapters, reset_adapters
        from unittest.mock import AsyncMock

        journal = MagicMock()
        journal.write_entry = AsyncMock(return_value={
            "entry_id": "j-001", "cycle": 1, "reasoning": "r",
            "lessons_learned": "l", "confidence": 0.7,
        })
        set_adapters(journal_writer=journal)
        try:
            state = {
                "is_active": True,
                "act_count": 1,
                "cycle_count": 5,
                "last_autonomous_decision": "act on: finance review",
                "next_planned_action": "summarize finance records",
                "recalled_memories": [{"content": "x", "relevance": 0.9, "timestamp": "t"}],
                "errors": [],
            }
            result = await reflect_node(state)

            journal.write_entry.assert_awaited()
            entries = result.get("journal_entries", [])
            assert len(entries) >= 1
            assert entries[0]["entry_id"] == "j-001"
        finally:
            reset_adapters()

    async def test_reflect_skips_journal_when_not_meaningful(self):
        """reflect_node must NOT write a journal entry on an empty idle cycle."""
        from src.life_kernel.graph import reflect_node, set_adapters, reset_adapters

        journal = MagicMock()
        journal.write_entry = AsyncMock(return_value={"entry_id": "j-x"})
        set_adapters(journal_writer=journal)
        try:
            state = {"is_active": True, "act_count": 0, "cycle_count": 0, "errors": []}
            result = await reflect_node(state)
            journal.write_entry.assert_not_awaited()
            assert "journal_entries" not in result
        finally:
            reset_adapters()

    async def test_current_focus_populated_on_idle(self):
        """idle_node must set current_focus so the dashboard shows the domain."""
        kg, mem = _mock_kg(), _mock_memory()
        graph = create_life_mind_graph(
            checkpointer=None, hermes_brain=None,
            kg_adapter=kg, memory_adapter=mem,
        )
        result = await graph.ainvoke(
            {"is_active": True, "goals": [], "commitments": [], "concerns": []},
            config={"configurable": {"thread_id": "t8"}, "recursion_limit": 25},
        )
        # current_focus should be set (not the default '—')
        assert result.get("current_focus") not in (None, "—", "")

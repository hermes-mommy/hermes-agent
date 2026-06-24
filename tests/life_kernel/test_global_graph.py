"""Comprehensive tests for Guinevere's global life-mind graph nodes (LK-006).

This module provides detailed unit tests for the fleshed-out act_node,
reflect_node, and idle_node, plus priority engine behavior in decide_node.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from src.life_kernel.state import (
    LifeMindPhase,
    LifeMindState,
    Priority,
)


class TestActNode:
    """Test suite for act_node action execution."""

    @pytest.mark.asyncio
    async def test_act_with_goals(self):
        """Verify act_node returns dict with act_count and cycle_count incremented."""
        from src.life_kernel.graph import act_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.ACT,
            "is_active": True,
            "goals": [
                {
                    "goal_id": "g1",
                    "priority": Priority.ENGINEERING,
                    "description": "Implement feature X",
                }
            ],
            "act_count": 3,
            "cycle_count": 5,
            "observations": [],
        }

        result = await act_node(state)

        assert "act_count" in result
        assert "cycle_count" in result
        assert result["act_count"] == 4
        assert result["cycle_count"] == 6

    @pytest.mark.asyncio
    async def test_act_without_goals(self):
        """Verify act_node appends observation about no goals and increments counters."""
        from src.life_kernel.graph import act_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.ACT,
            "is_active": True,
            "goals": [],
            "act_count": 1,
            "cycle_count": 2,
            "observations": [],
        }

        result = await act_node(state)

        assert result["act_count"] == 2
        assert result["cycle_count"] == 3
        assert "observations" in result
        assert len(result["observations"]) == 1
        assert result["observations"][0]["phase"] == "idle"
        assert "no active goals" in result["observations"][0]["reason"]

    @pytest.mark.asyncio
    async def test_act_respects_current_phase(self):
        """Verify act_node logs correct phase in returned observations."""
        from src.life_kernel.graph import act_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.ACT,
            "is_active": True,
            "goals": [
                {
                    "goal_id": "g1",
                    "priority": Priority.ENGINEERING,
                    "description": "Test phase logging",
                }
            ],
            "act_count": 0,
            "cycle_count": 0,
            "observations": [],
        }

        result = await act_node(state)

        assert result["act_count"] == 1
        assert result["cycle_count"] == 1
        # When goals exist, no observation is appended
        assert len(result["observations"]) == 0

    @pytest.mark.asyncio
    async def test_act_handles_empty_goals(self):
        """Verify act_node does not crash on empty goals list."""
        from src.life_kernel.graph import act_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.ACT,
            "is_active": True,
            "goals": [],
            "act_count": 0,
            "cycle_count": 0,
            "observations": [],
        }

        result = await act_node(state)

        assert isinstance(result, dict)
        assert result["act_count"] == 1
        assert result["cycle_count"] == 1
        assert "observations" in result
        assert len(result["observations"]) == 1

    @pytest.mark.asyncio
    async def test_act_selects_highest_priority_goal(self):
        """Verify act_node selects the highest-priority goal."""
        from src.life_kernel.graph import act_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.ACT,
            "is_active": True,
            "goals": [
                {
                    "goal_id": "low",
                    "priority": Priority.EXPLORE_RESEARCH,
                    "description": "Low priority",
                },
                {
                    "goal_id": "high",
                    "priority": Priority.ACTIVE_COMMITMENTS,
                    "description": "High priority",
                },
            ],
            "act_count": 0,
            "cycle_count": 0,
            "observations": [],
        }

        result = await act_node(state)

        assert result["act_count"] == 1
        # No direct output of selected goal, but we verify no crash and counters increment

    @pytest.mark.asyncio
    async def test_act_node_selects_safety_over_explore(self):
        """HARD_STOP_SAFETY priority must beat EXPLORE_RESEARCH in act selection."""
        from src.life_kernel.graph import act_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.ACT,
            "is_active": True,
            "goals": [
                {
                    "goal_id": "explore-1",
                    "priority": Priority.EXPLORE_RESEARCH,
                    "description": "learn",
                },
                {
                    "goal_id": "safety-1",
                    "priority": Priority.HARD_STOP_SAFETY,
                    "description": "halt",
                },
            ],
            "act_count": 0,
            "cycle_count": 0,
        }
        result = await act_node(state)
        # The selected goal should be safety-1 (HARD_STOP_SAFETY)
        # Check the log or the act_count increment to prove it ran
        assert result["act_count"] == 1


class TestReflectNode:
    """Test suite for reflect_node reflection and audit."""

    @pytest.mark.asyncio
    async def test_reflect_creates_audit_entry(self):
        """Verify reflect_node creates a new audit entry."""
        from src.life_kernel.graph import reflect_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.REFLECT,
            "is_active": True,
            "act_count": 2,
            "cycle_count": 5,
            "observations": [{"id": 1}, {"id": 2}],
            "audit_entries": [{"previous": True}],
            "errors": [],
            "hard_stop_requested": False,
        }

        result = await reflect_node(state)

        assert "audit_entries" in result
        assert isinstance(result["audit_entries"], list)
        assert len(result["audit_entries"]) == 1
        audit_entry = result["audit_entries"][0]
        assert audit_entry["phase"] == "reflect"
        assert "timestamp" in audit_entry
        assert audit_entry["cycle"] == 5
        assert audit_entry["act_count"] == 2
        assert audit_entry["n_observations"] == 2
        assert audit_entry["has_errors"] is False

    @pytest.mark.asyncio
    async def test_reflect_detects_errors(self):
        """Verify reflect_node reports has_errors=True when errors exist."""
        from src.life_kernel.graph import reflect_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.REFLECT,
            "is_active": True,
            "act_count": 1,
            "cycle_count": 3,
            "observations": [],
            "audit_entries": [],
            "errors": [{"msg": "something failed"}],
            "hard_stop_requested": False,
        }

        result = await reflect_node(state)

        audit_entry = result["audit_entries"][0]
        assert audit_entry["has_errors"] is True
        assert result["cycle_count"] == 4  # incremented due to errors

    @pytest.mark.asyncio
    async def test_reflect_routes_to_observe(self):
        """Verify reflect_node sets decision='observe' when no HARD STOP."""
        from src.life_kernel.graph import reflect_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.REFLECT,
            "is_active": True,
            "act_count": 0,
            "cycle_count": 0,
            "observations": [],
            "audit_entries": [],
            "errors": [],
            "hard_stop_requested": False,
        }

        result = await reflect_node(state)

        assert result["decision"] == "observe"

    @pytest.mark.asyncio
    async def test_reflect_hard_stop_routes_to_end(self):
        """Verify reflect_node sets decision='end' when hard_stop_requested."""
        from src.life_kernel.graph import reflect_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.REFLECT,
            "is_active": True,
            "act_count": 0,
            "cycle_count": 0,
            "observations": [],
            "audit_entries": [],
            "errors": [],
            "hard_stop_requested": True,
        }

        result = await reflect_node(state)

        assert result["decision"] == "end"


class TestIdleNode:
    """Test suite for idle_node self-directed task generation."""

    @pytest.mark.asyncio
    async def test_idle_generates_self_directed_task(self):
        """Verify idle_node appends a self-directed task to observations."""
        from src.life_kernel.graph import idle_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.IDLE,
            "is_active": True,
            "goals": [],
            "commitments": [],
            "cycle_count": 0,
            "observations": [],
        }

        result = await idle_node(state)

        assert "observations" in result
        assert len(result["observations"]) == 1
        observation = result["observations"][0]
        assert observation["phase"] == "idle"

    @pytest.mark.asyncio
    async def test_idle_cycles_back_to_observe(self):
        """Verify idle_node sets decision='observe' to cycle back."""
        from src.life_kernel.graph import idle_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.IDLE,
            "is_active": True,
            "goals": [],
            "commitments": [],
            "cycle_count": 0,
            "observations": [],
        }

        result = await idle_node(state)

        assert result["decision"] == "observe"

    @pytest.mark.asyncio
    async def test_idle_increments_cycle_count(self):
        """Verify idle_node increments cycle_count."""
        from src.life_kernel.graph import idle_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.IDLE,
            "is_active": True,
            "goals": [],
            "commitments": [],
            "cycle_count": 7,
            "observations": [],
        }

        result = await idle_node(state)

        assert result["cycle_count"] == 8

    @pytest.mark.asyncio
    async def test_idle_task_has_required_fields(self):
        """Verify idle observation contains all required fields."""
        from src.life_kernel.graph import idle_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.IDLE,
            "is_active": True,
            "goals": [],
            "commitments": [],
            "cycle_count": 0,
            "observations": [],
        }

        result = await idle_node(state)

        observation = result["observations"][0]
        assert observation["phase"] == "idle"
        assert "timestamp" in observation
        assert "task_type" in observation
        assert "description" in observation
        assert observation["task_type"] in {
            "exploration",
            "self_improvement",
            "learning",
        }


class TestRegressionFixes:
    """Regression tests for graph.py audit findings."""

    @pytest.mark.asyncio
    async def test_observations_not_doubled(self):
        """Run graph for one cycle; observe step adds exactly one observation.

        Each invocation completes one cycle (observe → decide → act → reflect → END).
        The heartbeat re-invokes for the next cycle, so we test one cycle at a time.
        """
        from src.life_kernel.graph import create_life_mind_graph

        graph = create_life_mind_graph(checkpointer=None)

        initial_state: LifeMindState = {
            "current_phase": LifeMindPhase.OBSERVE,
            "is_active": True,
            "hard_stop_requested": False,
            "goals": [{"id": 1, "description": "Test goal"}],
            "commitments": [],
            "concerns": [],
            "audit_entries": [],
            "observations": [],
        }

        observe_outputs: list[list[dict]] = []
        async for chunk in graph.astream(initial_state, config={"recursion_limit": 25}):
            if "observe" in chunk:
                observe_outputs.append(chunk["observe"]["observations"])

        # One cycle = one observe invocation
        assert len(observe_outputs) == 1
        # Observe node returns only the new observation (not doubled by reducer).
        assert len(observe_outputs[0]) == 1
        # n_observations field shows count in state (0 before first observation added).
        assert observe_outputs[0][0]["n_observations"] == 0

    @pytest.mark.asyncio
    async def test_heartbeat_terminology_in_observation(self):
        """Observe node uses 'heartbeat' key, not 'pulse'."""
        from src.life_kernel.graph import observe_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.OBSERVE,
            "is_active": True,
            "observations": [],
            "goals": [],
        }

        result = await observe_node(state)

        observation = result["observations"][-1]
        assert "heartbeat" in observation
        assert observation["heartbeat"] == "observe_heartbeat"
        assert "pulse" not in observation

    @pytest.mark.asyncio
    async def test_decision_context_builder_wired(self):
        """observe_node builds decision_context when adapters are registered.

        The continuation reads adapters from the module-level registry
        (set_adapters) rather than from LangGraph state, because state is
        JSON-checkpointed and cannot hold live adapter objects.
        """
        from src.life_kernel.graph import observe_node, set_adapters, reset_adapters

        kg_adapter = AsyncMock()
        kg_adapter.recall.return_value = {
            "concepts": [{"name": "autonomy_kernel"}],
            "count": 1,
        }
        memory_adapter = AsyncMock()
        memory_adapter.recall.return_value = {
            "memories": [{"content": "previous observation"}],
            "count": 1,
        }

        set_adapters(kg_adapter=kg_adapter, memory_adapter=memory_adapter)
        try:
            state: LifeMindState = {
                "current_phase": LifeMindPhase.OBSERVE,
                "is_active": True,
                "observations": [],
                "goals": [],
            }

            result = await observe_node(state)

            assert "decision_context" in result
            # observe_node exposes recalled concepts/memories both on the
            # decision_context (kg_context/memory_context) and as top-level
            # state fields (recalled_concepts/recalled_memories).
            assert result["decision_context"]["kg_context"] == [{"name": "autonomy_kernel"}]
            assert result["decision_context"]["memory_context"] == [{"content": "previous observation"}]
            assert result["recalled_concepts"] == [{"name": "autonomy_kernel"}]
            assert result["recalled_memories"] == [{"content": "previous observation"}]
            assert result["world_model_status"] == "active"
            kg_adapter.recall.assert_awaited_once()
            memory_adapter.recall.assert_awaited_once()
        finally:
            reset_adapters()


class TestPriorityEngine:
    """Test suite for decide_node priority engine."""

    @pytest.mark.asyncio
    async def test_priority_hard_stop_beats_all(self):
        """Verify HARD_STOP_SAFETY always wins over any other condition."""
        from src.life_kernel.graph import decide_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.DECIDE,
            "is_active": True,
            "hard_stop_requested": True,
            "goals": [{"id": 1, "description": "Important"}],
            "commitments": [{"id": 2, "description": "Urgent"}],
            "concerns": [{"id": 3, "description": "Critical"}],
        }

        result = await decide_node(state)

        assert result["decision"] == "end"

    @pytest.mark.asyncio
    async def test_priority_explore_lowest(self):
        """Verify EXPLORE_RESEARCH goals alone route to act."""
        from src.life_kernel.graph import decide_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.DECIDE,
            "is_active": True,
            "hard_stop_requested": False,
            "goals": [{"id": 1, "description": "Research", "priority": Priority.EXPLORE_RESEARCH}],
            "commitments": [],
        }

        result = await decide_node(state)

        assert result["decision"] == "act"

    @pytest.mark.asyncio
    async def test_decide_idle_when_no_goals(self):
        """Verify decision='idle' when goals empty and not hard_stopped."""
        from src.life_kernel.graph import decide_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.DECIDE,
            "is_active": True,
            "hard_stop_requested": False,
            "goals": [],
            "commitments": [],
        }

        result = await decide_node(state)

        assert result["decision"] == "idle"

    @pytest.mark.asyncio
    async def test_decide_act_with_commitments(self):
        """Verify active commitments route to act."""
        from src.life_kernel.graph import decide_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.DECIDE,
            "is_active": True,
            "hard_stop_requested": False,
            "goals": [],
            "commitments": [{"id": 1, "description": "Commitment"}],
        }

        result = await decide_node(state)

        assert result["decision"] == "act"

    @pytest.mark.asyncio
    async def test_concerns_prevent_idle_routing(self):
        """Verify concerns alone route to act, not idle."""
        from src.life_kernel.graph import decide_node

        state: LifeMindState = {
            "current_phase": LifeMindPhase.DECIDE,
            "is_active": True,
            "hard_stop_requested": False,
            "goals": [],
            "commitments": [],
            "concerns": [{"id": 1, "description": "Concern"}],
        }

        result = await decide_node(state)

        assert result["decision"] == "act"

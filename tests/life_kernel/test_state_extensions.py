"""Tests for LifeMindState journal and recall field extensions (T1).

These verify the new state fields needed for the P20 Living Autonomy
continuation: journal_entries, recalled_concepts, recalled_memories,
and world_model_status.
"""

from src.life_kernel.state import (
    LifeMindState,
    add_journal_reducer,
)


def test_add_journal_reducer_appends():
    """add_journal_reducer must append new entries to existing."""
    left = [{"entry_id": "j001", "reasoning": "first"}]
    right = [{"entry_id": "j002", "reasoning": "second"}]
    result = add_journal_reducer(left, right)
    assert len(result) == 2
    assert result[0]["entry_id"] == "j001"
    assert result[1]["entry_id"] == "j002"


def test_add_journal_reducer_caps_at_1000():
    """add_journal_reducer must cap at 1000 most recent entries."""
    left = [{"entry_id": f"old-{i}"} for i in range(1000)]
    right = [{"entry_id": "new"}]
    result = add_journal_reducer(left, right)
    assert len(result) == 1000
    # Most recent (the new entry) must be retained
    assert result[-1]["entry_id"] == "new"
    # Oldest dropped
    assert result[0]["entry_id"] != "old-0"


def test_life_mind_state_has_journal_entries_field():
    """LifeMindState must accept journal_entries field."""
    state: LifeMindState = {
        "journal_entries": [
            {
                "entry_id": "j001",
                "timestamp": "2026-06-24T12:00:00Z",
                "cycle": 100,
                "reasoning": "Chose to review finance records",
                "lessons_learned": "Pattern matching improves recall",
                "confidence": 0.85,
            }
        ]
    }
    assert "journal_entries" in state
    assert len(state["journal_entries"]) == 1
    assert state["journal_entries"][0]["entry_id"] == "j001"


def test_life_mind_state_has_recalled_concepts_field():
    """LifeMindState must accept recalled_concepts from P16 KG."""
    state: LifeMindState = {
        "recalled_concepts": [
            {"name": "finance_tracking", "relevance": 0.92, "source": "p16"},
            {"name": "email_priority", "relevance": 0.87, "source": "p16"},
        ]
    }
    assert "recalled_concepts" in state
    assert len(state["recalled_concepts"]) == 2
    assert state["recalled_concepts"][0]["name"] == "finance_tracking"


def test_life_mind_state_has_recalled_memories_field():
    """LifeMindState must accept recalled_memories from P18."""
    state: LifeMindState = {
        "recalled_memories": [
            {"content": "Previous finance review", "relevance": 0.88, "timestamp": "2026-06-23T10:00:00Z"},
            {"content": "Email pattern observed", "relevance": 0.81, "timestamp": "2026-06-23T11:00:00Z"},
        ]
    }
    assert "recalled_memories" in state
    assert len(state["recalled_memories"]) == 2


def test_life_mind_state_has_world_model_status_field():
    """LifeMindState must track world model availability."""
    state: LifeMindState = {"world_model_status": "active"}
    assert state["world_model_status"] == "active"


def test_life_mind_state_world_model_status_values():
    """world_model_status must accept active/degraded/unavailable."""
    for value in ("active", "degraded", "unavailable"):
        state: LifeMindState = {"world_model_status": value}
        assert state["world_model_status"] == value

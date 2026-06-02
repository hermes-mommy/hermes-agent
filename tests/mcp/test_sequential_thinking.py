"""Tests for Sequential Thinking MCP Tool — chain-of-thought reasoning."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from src.mcp.tools.sequential_thinking import (
    SessionNotFoundError,
    Thought,
    ThinkingSession,
    _sessions,
    add_thought,
    branch_thought,
    create_session,
    finalize_session,
    get_session,
    register_tools,
    revise_thought,
    sequential_think,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _clear_sessions() -> Generator[None]:
    """Clear in-memory session storage before and after each test."""
    _sessions.clear()
    yield
    _sessions.clear()


# ============================================================================
# TestDataModel
# ============================================================================


class TestDataModel:
    """Verify frozen dataclass properties of Thought and ThinkingSession."""

    def test_thought_is_frozen(self) -> None:
        """Thought instances cannot be mutated."""
        t = Thought(thought_number=1, content="hello")
        with pytest.raises(AttributeError):
            t.content = "changed"  # type: ignore[misc]

    def test_thought_defaults(self) -> None:
        """Optional fields default correctly."""
        t = Thought(thought_number=1, content="test")
        assert t.is_revision is False
        assert t.revises_thought is None
        assert t.branch_from_thought is None
        assert t.branch_id is None

    def test_session_is_frozen(self) -> None:
        """ThinkingSession instances cannot be mutated."""
        s = ThinkingSession(topic="t", total_thoughts=3, thoughts=())
        with pytest.raises(AttributeError):
            s.topic = "other"  # type: ignore[misc]

    def test_session_defaults(self) -> None:
        """needs_more_thoughts defaults to False."""
        s = ThinkingSession(topic="t", total_thoughts=5, thoughts=())
        assert s.needs_more_thoughts is False


# ============================================================================
# TestCreateSession
# ============================================================================


class TestCreateSession:
    """Tests for create_session."""

    def test_creates_and_returns_uuid(self) -> None:
        """Returns a non-empty session ID string."""
        sid = create_session("test topic")
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_session_stored(self) -> None:
        """Created session is retrievable via get_session."""
        sid = create_session("my topic", initial_estimate=10)
        session = get_session(sid)
        assert session.topic == "my topic"
        assert session.total_thoughts == 10
        assert session.thoughts == ()
        assert session.needs_more_thoughts is True

    def test_default_estimate(self) -> None:
        """Default initial_estimate is 5."""
        sid = create_session("default test")
        session = get_session(sid)
        assert session.total_thoughts == 5

    def test_multiple_sessions_independent(self) -> None:
        """Two sessions do not share state."""
        sid1 = create_session("topic-a")
        sid2 = create_session("topic-b")
        add_thought(sid1, "thought A", True, 1)
        s1 = get_session(sid1)
        s2 = get_session(sid2)
        assert len(s1.thoughts) == 1
        assert len(s2.thoughts) == 0


# ============================================================================
# TestAddThought
# ============================================================================


class TestAddThought:
    """Tests for add_thought."""

    def test_appends_thought(self) -> None:
        """Thought is appended to the session."""
        sid = create_session("add test")
        updated = add_thought(sid, "first thought", True, 1)
        assert len(updated.thoughts) == 1
        assert updated.thoughts[0].content == "first thought"
        assert updated.thoughts[0].thought_number == 1

    def test_updates_needs_more_thoughts(self) -> None:
        """next_needed flag is reflected in the session."""
        sid = create_session("flag test")
        updated = add_thought(sid, "done", False, 1)
        assert updated.needs_more_thoughts is False

    def test_updates_total_thoughts(self) -> None:
        """total_thoughts grows when thought_number exceeds it."""
        sid = create_session("grow test", initial_estimate=3)
        updated = add_thought(sid, "big thought", True, 7)
        assert updated.total_thoughts == 7

    def test_sequential_numbering(self) -> None:
        """Multiple thoughts maintain sequential numbering."""
        sid = create_session("seq test")
        add_thought(sid, "one", True, 1)
        add_thought(sid, "two", True, 2)
        updated = add_thought(sid, "three", False, 3)
        assert len(updated.thoughts) == 3
        assert [t.thought_number for t in updated.thoughts] == [1, 2, 3]

    def test_session_not_found_raises(self) -> None:
        """Referencing a missing session raises SessionNotFoundError."""
        with pytest.raises(SessionNotFoundError):
            add_thought("nonexistent", "oops", True, 1)


# ============================================================================
# TestBranchThought
# ============================================================================


class TestBranchThought:
    """Tests for branch_thought."""

    def test_creates_branch(self) -> None:
        """Branch thought is created with correct metadata."""
        sid = create_session("branch test")
        add_thought(sid, "original", True, 1)
        updated = branch_thought(sid, from_thought=1, content="branch idea")

        assert len(updated.thoughts) == 2
        branch = updated.thoughts[1]
        assert branch.branch_from_thought == 1
        assert branch.branch_id is not None
        assert len(branch.branch_id) > 0
        assert branch.content == "branch idea"

    def test_branch_gets_next_number(self) -> None:
        """Branch thought receives the next sequential number."""
        sid = create_session("branch num test")
        add_thought(sid, "a", True, 1)
        add_thought(sid, "b", True, 2)
        updated = branch_thought(sid, from_thought=1, content="branch")
        assert updated.thoughts[-1].thought_number == 3

    def test_branch_session_not_found(self) -> None:
        """Branching on missing session raises SessionNotFoundError."""
        with pytest.raises(SessionNotFoundError):
            branch_thought("nope", from_thought=1, content="x")


# ============================================================================
# TestReviseThought
# ============================================================================


class TestReviseThought:
    """Tests for revise_thought."""

    def test_revises_existing(self) -> None:
        """Revision updates content and sets revision metadata."""
        sid = create_session("revise test")
        add_thought(sid, "original content", True, 1)
        updated = revise_thought(sid, thought_number=1, new_content="revised content")

        revised = updated.thoughts[0]
        assert revised.content == "revised content"
        assert revised.is_revision is True
        assert revised.revises_thought == 1

    def test_revision_of_nonexistent_creates_new(self) -> None:
        """Revising a non-existent thought creates a new thought."""
        sid = create_session("revise missing test")
        add_thought(sid, "only thought", True, 1)
        updated = revise_thought(sid, thought_number=99, new_content="phantom revision")

        assert len(updated.thoughts) == 2
        new_thought = updated.thoughts[1]
        assert new_thought.content == "phantom revision"
        assert new_thought.is_revision is True
        assert new_thought.revises_thought == 99

    def test_revision_session_not_found(self) -> None:
        """Revising on missing session raises SessionNotFoundError."""
        with pytest.raises(SessionNotFoundError):
            revise_thought("missing", thought_number=1, new_content="x")


# ============================================================================
# TestGetSession
# ============================================================================


class TestGetSession:
    """Tests for get_session."""

    def test_returns_existing(self) -> None:
        """Returns the correct session."""
        sid = create_session("get test")
        session = get_session(sid)
        assert session.topic == "get test"

    def test_raises_on_missing(self) -> None:
        """Raises SessionNotFoundError for unknown IDs."""
        with pytest.raises(SessionNotFoundError, match="not found"):
            get_session("does-not-exist")


# ============================================================================
# TestFinalizeSession
# ============================================================================


class TestFinalizeSession:
    """Tests for finalize_session."""

    def test_returns_formatted_summary(self) -> None:
        """Summary includes topic, all thoughts, and conclusion."""
        sid = create_session("finalize test")
        add_thought(sid, "step one", True, 1)
        add_thought(sid, "step two", False, 2)
        summary = finalize_session(sid, "the answer is 42")

        assert "Topic: finalize test" in summary
        assert "Thought 1: step one" in summary
        assert "Thought 2: step two" in summary
        assert "Conclusion: the answer is 42" in summary

    def test_session_removed_after_finalize(self) -> None:
        """Session is deleted from storage after finalization."""
        sid = create_session("cleanup test")
        finalize_session(sid, "done")
        with pytest.raises(SessionNotFoundError):
            get_session(sid)

    def test_summary_includes_branch_annotations(self) -> None:
        """Branch and revision annotations appear in the summary."""
        sid = create_session("annotated test")
        add_thought(sid, "original", True, 1)
        branch_thought(sid, from_thought=1, content="branch")
        revise_thought(sid, thought_number=1, new_content="revised original")
        summary = finalize_session(sid, "done")

        assert "branch from #1" in summary
        assert "revises #1" in summary

    def test_finalize_session_not_found(self) -> None:
        """Finalizing missing session raises SessionNotFoundError."""
        with pytest.raises(SessionNotFoundError):
            finalize_session("nope", "conclusion")


# ============================================================================
# TestSequentialThink (MCP tool function)
# ============================================================================


class TestSequentialThink:
    """Tests for the async sequential_think MCP tool function."""

    def test_records_thought(self) -> None:
        """Records a thought and returns metadata dict."""
        result = asyncio.run(
            sequential_think(
                thought="first idea",
                thought_number=1,
                total_thoughts=5,
            )
        )
        assert result["thought_number"] == 1
        assert result["total_thoughts"] == 5
        assert result["next_thought_needed"] is True
        assert result["thoughts_recorded"] == 1

    def test_multiple_thoughts_accumulate(self) -> None:
        """Multiple calls accumulate thoughts in the default session."""
        asyncio.run(
            sequential_think(thought="a", thought_number=1, total_thoughts=3)
        )
        result = asyncio.run(
            sequential_think(thought="b", thought_number=2, total_thoughts=3)
        )
        assert result["thoughts_recorded"] == 2

    def test_auto_creates_default_session(self) -> None:
        """Default session is auto-created on first invocation."""
        assert len(_sessions) == 0
        asyncio.run(
            sequential_think(thought="init", thought_number=1, total_thoughts=5)
        )
        assert len(_sessions) == 1

    def test_revision_metadata(self) -> None:
        """Revision flags are recorded in the thought."""
        asyncio.run(
            sequential_think(thought="original", thought_number=1, total_thoughts=5)
        )
        result = asyncio.run(
            sequential_think(
                thought="revised",
                thought_number=2,
                total_thoughts=5,
                is_revision=True,
                revises_thought=1,
            )
        )
        assert result["thoughts_recorded"] == 2

    def test_branch_metadata(self) -> None:
        """Branch metadata is passed through correctly."""
        asyncio.run(
            sequential_think(thought="main", thought_number=1, total_thoughts=5)
        )
        result = asyncio.run(
            sequential_think(
                thought="branch",
                thought_number=2,
                total_thoughts=5,
                branch_from_thought=1,
                branch_id="test-branch",
            )
        )
        assert result["thoughts_recorded"] == 2

    def test_total_thoughts_grows(self) -> None:
        """total_thoughts expands when thought_number exceeds current value."""
        result = asyncio.run(
            sequential_think(thought="big", thought_number=10, total_thoughts=3)
        )
        assert result["total_thoughts"] == 10


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Tests for register_tools entry-point."""

    def test_registers_tool(self) -> None:
        """register_tools calls mcp.tool() at least once."""
        mock_mcp = MagicMock()
        mock_decorator = MagicMock(return_value=lambda f: f)
        mock_mcp.tool.return_value = mock_decorator
        register_tools(mock_mcp)
        mock_mcp.tool.assert_called_once()

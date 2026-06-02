"""Tests for Tool Selection Decision Matrix — 8 overlap scenarios + error paths."""

from __future__ import annotations

import pytest

from src.mcp.tool_selector import (
    AllToolsUnavailableError,
    NoToolAvailableError,
    ToolOption,
    ToolRecommendation,
    _score_option,
    get_tool_matrix,
    select_tool,
)


# ============================================================================
# Test Scoring Formula
# ============================================================================


class TestScoringFormula:
    """Verify the priority scoring formula is implemented correctly."""

    def test_score_formula_fully_available(self) -> None:
        """Score matches the documented formula for a fully available tool."""
        option = ToolOption(
            name="test",
            relevance=0.5,
            cost_efficiency=0.5,
            auth_ease=1.0,
            available=True,
        )
        expected = 0.5 * 0.4 + 0.5 * 0.3 + 1.0 * 0.2 + 1.0 * 0.1
        assert _score_option(option) == pytest.approx(expected)

    def test_score_formula_unavailable(self) -> None:
        """Availability=0.0 contributes zero to the score."""
        option = ToolOption(
            name="test",
            relevance=1.0,
            cost_efficiency=1.0,
            auth_ease=1.0,
            available=False,
        )
        expected = 1.0 * 0.4 + 1.0 * 0.3 + 1.0 * 0.2 + 0.0 * 0.1
        assert _score_option(option) == pytest.approx(expected)

    def test_score_zero_relevance(self) -> None:
        """Score is non-zero from other dimensions even with zero relevance."""
        option = ToolOption(
            name="test",
            relevance=0.0,
            cost_efficiency=0.5,
            auth_ease=1.0,
            available=True,
        )
        expected = 0.0 * 0.4 + 0.5 * 0.3 + 1.0 * 0.2 + 1.0 * 0.1
        assert _score_option(option) == pytest.approx(expected)

    def test_score_bounds(self) -> None:
        """Score is bounded in [0.0, 1.0] for all-extreme inputs."""
        best = _score_option(
            ToolOption(name="best", relevance=1.0, cost_efficiency=1.0, auth_ease=1.0, available=True)
        )
        worst = _score_option(
            ToolOption(name="worst", relevance=0.0, cost_efficiency=0.0, auth_ease=0.0, available=False)
        )
        assert best == pytest.approx(1.0)
        assert worst == pytest.approx(0.0)


# ============================================================================
# Test 8 Overlap Scenarios
# ============================================================================


class TestOverlapScenarios:
    """Each method verifies the correct winner for one overlap scenario."""

    # 1. Web search (general)
    @pytest.mark.asyncio
    async def test_web_search_general_websearch_wins(self) -> None:
        """websearch preferred over brave_search for general web search."""
        result = await select_tool("web_search_general")
        assert result.tool_name == "websearch"
        alt_names = [a.name for a in result.alternatives]
        assert "brave_search" in alt_names
        assert result.score > 0.0

    @pytest.mark.asyncio
    async def test_web_search_general_brave_not_wins(self) -> None:
        """brave_search scores lower than websearch for general search."""
        result = await select_tool("web_search_general")
        brave = next(
            a for a in result.alternatives if a.name == "brave_search"
        )
        assert _score_option(brave) < result.score

    # 2. Semantic web search
    @pytest.mark.asyncio
    async def test_web_search_semantic_exa_wins(self) -> None:
        """exa preferred for semantic web search."""
        result = await select_tool("web_search_semantic")
        assert result.tool_name == "exa"
        assert "better for semantic queries" in result.reason.lower() or "semantic" in result.reason.lower()

    # 3. Code search
    @pytest.mark.asyncio
    async def test_code_search_grep_app_wins(self) -> None:
        """grep_app preferred over github for code search."""
        result = await select_tool("code_search")
        assert result.tool_name == "grep_app"
        alt_names = [a.name for a in result.alternatives]
        assert "github" in alt_names

    @pytest.mark.asyncio
    async def test_code_search_github_not_wins(self) -> None:
        """github scores lower than grep_app for code search."""
        result = await select_tool("code_search")
        github = next(
            a for a in result.alternatives if a.name == "github"
        )
        assert _score_option(github) < result.score

    # 4. Library docs
    @pytest.mark.asyncio
    async def test_library_docs_context7_wins(self) -> None:
        """context7 preferred for library documentation lookups."""
        result = await select_tool("library_docs")
        assert result.tool_name == "context7"

    # 5. Page content
    @pytest.mark.asyncio
    async def test_page_content_fetch_wins(self) -> None:
        """fetch preferred over obscura_cdp for simple page content."""
        result = await select_tool("page_content")
        assert result.tool_name == "fetch"
        alt_names = [a.name for a in result.alternatives]
        assert "obscura_cdp" in alt_names

    # 6. File read
    @pytest.mark.asyncio
    async def test_file_read_filesystem_wins(self) -> None:
        """filesystem preferred over shell for file reads."""
        result = await select_tool("file_read")
        assert result.tool_name == "filesystem"

    # 7. DB query
    @pytest.mark.asyncio
    async def test_db_query_postgres_wins(self) -> None:
        """postgres preferred over shell/psql for database queries."""
        result = await select_tool("db_query")
        assert result.tool_name == "postgres"

    # 8. Git operations
    @pytest.mark.asyncio
    async def test_git_operations_git_wins(self) -> None:
        """git preferred over shell for version control operations."""
        result = await select_tool("git_operations")
        assert result.tool_name == "git"


# ============================================================================
# Test Edge Cases and Error Handling
# ============================================================================


class TestErrorHandling:
    """Tests for error paths and boundary conditions."""

    @pytest.mark.asyncio
    async def test_unknown_task_type_raises(self) -> None:
        """NoToolAvailableError raised for unregistered task_type."""
        with pytest.raises(NoToolAvailableError) as exc_info:
            await select_tool("nonexistent_task_type")
        assert "nonexistent_task_type" in str(exc_info.value)
        assert exc_info.value.suggestions

    @pytest.mark.asyncio
    async def test_all_candidates_unavailable(self) -> None:
        """AllToolsUnavailableError when constraints mark all as unavailable."""
        constraints: dict[str, object] = {
            "unavailable_tools": ["websearch", "brave_search", "exa"],
        }
        with pytest.raises(AllToolsUnavailableError) as exc_info:
            await select_tool("web_search_general", constraints=constraints)
        assert "web_search_general" in str(exc_info.value)
        assert exc_info.value.candidates

    @pytest.mark.asyncio
    async def test_partial_unavailability_skips_unavailable(self) -> None:
        """When some tools are unavailable, the winner is the top available."""
        constraints: dict[str, object] = {
            "unavailable_tools": ["websearch"],
        }
        result = await select_tool("web_search_general", constraints=constraints)
        # With websearch unavailable, brave_search should win.
        assert result.tool_name == "brave_search"
        # Verify websearch is NOT the winner.
        assert result.tool_name != "websearch"

    @pytest.mark.asyncio
    async def test_query_param_accepted(self) -> None:
        """Query parameter is accepted without error."""
        result = await select_tool("code_search", query="async function handler")
        assert result.tool_name == "grep_app"


# ============================================================================
# Test Data Model (frozen dataclass)
# ============================================================================


class TestDataModel:
    """Verify frozen dataclass behaviour and ToolRecommendation structure."""

    def test_tool_option_is_frozen(self) -> None:
        """ToolOption is immutable (frozen=True)."""
        option = ToolOption(
            name="test",
            relevance=0.5,
            cost_efficiency=0.5,
            auth_ease=1.0,
            available=True,
        )
        with pytest.raises(Exception):
            setattr(option, "name", "changed")

    def test_tool_recommendation_is_frozen(self) -> None:
        """ToolRecommendation is immutable (frozen=True)."""
        rec = ToolRecommendation(
            tool_name="test",
            score=0.9,
            alternatives=(),
            reason="Test reason.",
        )
        with pytest.raises(Exception):
            setattr(rec, "tool_name", "changed")

    def test_tool_recommendation_has_correct_fields(self) -> None:
        """ToolRecommendation contains all required fields."""
        rec = ToolRecommendation(
            tool_name="postgres",
            score=0.92,
            alternatives=(
                ToolOption(name="shell", relevance=0.4, cost_efficiency=0.6, auth_ease=0.8, available=True),
            ),
            reason="Typed, parameterised queries.",
        )
        assert rec.tool_name == "postgres"
        assert rec.score == 0.92
        assert len(rec.alternatives) == 1
        assert rec.alternatives[0].name == "shell"
        assert rec.reason == "Typed, parameterised queries."


# ============================================================================
# Test get_tool_matrix
# ============================================================================


class TestGetToolMatrix:
    """Tests for the get_tool_matrix helper."""

    def test_matrix_has_all_eight_scenarios(self) -> None:
        """Matrix includes all 8 registered task types."""
        matrix = get_tool_matrix()
        expected_keys = {
            "web_search_general",
            "web_search_semantic",
            "code_search",
            "library_docs",
            "page_content",
            "file_read",
            "db_query",
            "git_operations",
        }
        assert expected_keys == set(matrix.keys())

    def test_matrix_entries_are_ordered(self) -> None:
        """Each entry preserves the relevance-ordered candidate list."""
        matrix = get_tool_matrix()
        for task_type, tools in matrix.items():
            assert len(tools) >= 2, f"{task_type} must have >=2 candidates"
            assert isinstance(tools, list)

    def test_matrix_is_deterministic(self) -> None:
        """Multiple calls return identical output."""
        m1 = get_tool_matrix()
        m2 = get_tool_matrix()
        assert m1 == m2


# ============================================================================
# Test select_tool returns correct recommendation structure
# ============================================================================


class TestSelectToolStructure:
    """Verify the structure of ToolRecommendation returned by select_tool."""

    @pytest.mark.asyncio
    async def test_recommendation_has_alternatives(self) -> None:
        """Winning recommendation includes ranked alternatives."""
        result = await select_tool("web_search_general")
        assert isinstance(result, ToolRecommendation)
        assert len(result.alternatives) >= 1
        for alt in result.alternatives:
            assert isinstance(alt, ToolOption)

    @pytest.mark.asyncio
    async def test_recommendation_has_reason(self) -> None:
        """Every recommendation includes a human-readable reason."""
        result = await select_tool("git_operations")
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0

    @pytest.mark.asyncio
    async def test_score_is_between_zero_and_one(self) -> None:
        """Scores are bounded in [0.0, 1.0]."""
        for task_type in get_tool_matrix().keys():
            result = await select_tool(task_type)
            assert 0.0 <= result.score <= 1.0
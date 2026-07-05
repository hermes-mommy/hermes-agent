"""Tool Selection Decision Matrix — Optimal tool routing for overlapping capabilities.

When multiple tools can satisfy the same task, this module computes a priority
score across four weighted dimensions and returns the best tool with
alternatives ranked below it.

The 8 overlap scenarios covered:

* Web search (general) → ``websearch`` (hybrid fallback built-in)
* Web search (semantic) → ``exa`` (semantic-query optimised)
* Code search → ``grep_app`` (purpose-built for code)
* Library docs → ``context7`` (structured doc lookup)
* Page content → ``fetch`` (lighter for simple fetches)
* File read → ``filesystem`` (purpose-built, safer)
* DB query → ``postgres`` (typed, parameterised, safer)
* Git operations → ``git`` (auth-level granularity)
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0)
# ---------------------------------------------------------------------------

_RELEVANCE_WEIGHT: float = 0.4
_COST_EFFICIENCY_WEIGHT: float = 0.3
_AUTH_EASE_WEIGHT: float = 0.2
_AVAILABILITY_WEIGHT: float = 0.1


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class NoToolAvailableError(Exception):
    """Raised when no tool matches the requested task type."""

    task_type: str
    suggestions: list[str]

    def __init__(self, task_type: str, suggestions: list[str] | None = None) -> None:
        self.task_type = task_type
        self.suggestions = suggestions or []
        message = (
            f"No tool registered for task_type='{task_type}'."
        )
        if self.suggestions:
            message += f" Try one of: {', '.join(self.suggestions)}"
        super().__init__(message)


class AllToolsUnavailableError(Exception):
    """Raised when all candidate tools for a task are unavailable."""

    task_type: str
    candidates: list[str]

    def __init__(self, task_type: str, candidates: list[str]) -> None:
        self.task_type = task_type
        self.candidates = candidates
        super().__init__(
            f"All candidates for task_type='{task_type}' are unavailable: "
            f"{', '.join(candidates)}"
        )


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolOption:
    """A candidate tool with weighted scoring dimensions.

    All scores are in [0.0, 1.0].
    """

    name: str
    relevance: float  # How well the tool fits the task.
    cost_efficiency: float  # Cost-effectiveness relative to peers.
    auth_ease: float  # 1.0 = READ_AUTO, 0.0 = FORBIDDEN.
    available: bool


@dataclass(frozen=True)
class ToolRecommendation:
    """Final recommendation with score, alternatives, and rationale."""

    tool_name: str
    score: float
    alternatives: tuple[ToolOption, ...]
    reason: str


# ---------------------------------------------------------------------------
# Scoring formula
# ---------------------------------------------------------------------------


def _score_option(option: ToolOption) -> float:
    """Compute priority score for a single tool option.

    Formula:
        (relevance * 0.4) + (cost_efficiency * 0.3) +
        (auth_ease * 0.2) + (availability * 0.1)

    The availability component is ``available`` cast to float (1.0 or 0.0).
    """
    availability_value: float = 1.0 if option.available else 0.0
    return (
        option.relevance * _RELEVANCE_WEIGHT
        + option.cost_efficiency * _COST_EFFICIENCY_WEIGHT
        + option.auth_ease * _AUTH_EASE_WEIGHT
        + availability_value * _AVAILABILITY_WEIGHT
    )


# ---------------------------------------------------------------------------
# Decision matrix — task_type → list of ToolOption
# ---------------------------------------------------------------------------


_DECISION_MATRIX: dict[str, list[ToolOption]] = {
    # 1. General web search
    "web_search_general": [
        ToolOption(name="websearch", relevance=0.85, cost_efficiency=0.60, auth_ease=1.0, available=True),
        ToolOption(name="brave_search", relevance=0.70, cost_efficiency=0.50, auth_ease=1.0, available=True),
        ToolOption(name="exa", relevance=0.60, cost_efficiency=0.50, auth_ease=1.0, available=True),
    ],
    # 2. Semantic web search
    "web_search_semantic": [
        ToolOption(name="exa", relevance=0.95, cost_efficiency=0.50, auth_ease=1.0, available=True),
        ToolOption(name="websearch", relevance=0.75, cost_efficiency=0.60, auth_ease=1.0, available=True),
    ],
    # 3. Code search
    "code_search": [
        ToolOption(name="grep_app", relevance=0.95, cost_efficiency=0.80, auth_ease=1.0, available=True),
        ToolOption(name="github", relevance=0.60, cost_efficiency=0.50, auth_ease=1.0, available=True),
    ],
    # 4. Library docs
    "library_docs": [
        ToolOption(name="context7", relevance=0.95, cost_efficiency=0.90, auth_ease=1.0, available=True),
        ToolOption(name="fetch", relevance=0.40, cost_efficiency=0.60, auth_ease=1.0, available=True),
    ],
    # 5. Page content fetching
    "page_content": [
        ToolOption(name="fetch", relevance=0.85, cost_efficiency=0.90, auth_ease=1.0, available=True),
        ToolOption(name="obscura_cdp", relevance=0.70, cost_efficiency=0.40, auth_ease=1.0, available=True),
    ],
    # 6. File read
    "file_read": [
        ToolOption(name="filesystem", relevance=0.95, cost_efficiency=0.90, auth_ease=1.0, available=True),
        ToolOption(name="shell", relevance=0.50, cost_efficiency=0.70, auth_ease=0.80, available=True),
    ],
    # 7. Database query
    "db_query": [
        ToolOption(name="postgres", relevance=0.95, cost_efficiency=0.85, auth_ease=1.0, available=True),
        ToolOption(name="shell", relevance=0.40, cost_efficiency=0.60, auth_ease=0.80, available=True),
    ],
    # 8. Git operations
    "git_operations": [
        ToolOption(name="git", relevance=0.95, cost_efficiency=0.85, auth_ease=1.0, available=True),
        ToolOption(name="shell", relevance=0.45, cost_efficiency=0.70, auth_ease=0.80, available=True),
    ],
}

# Human-readable rationales for winning tools (used in ToolRecommendation).
_WIN_RATIONALES: dict[str, str] = {
    "websearch": "Hybrid search with Brave primary + Exa fallback, built-in resilience.",
    "exa": "Purpose-built for semantic queries with higher result relevance.",
    "grep_app": "Specialised code-search engine indexing millions of public repos.",
    "context7": "Structured documentation lookup with version-aware API references.",
    "fetch": "Lightweight HTTP fetch ideal for simple page-content extraction.",
    "filesystem": "Dedicated file-I/O tool with access controls; safer than raw shell.",
    "postgres": "Typed, parameterised queries with connection pooling; safer than psql.",
    "git": "Granular auth-level controls and structured output for version-control ops.",
}

# Fallback suggestions when a task_type is not in the matrix.
_SUGGESTIONS: dict[str, list[str]] = {
    "web_search": ["web_search_general", "web_search_semantic"],
    "search": ["web_search_general", "code_search"],
    "docs": ["library_docs", "page_content"],
    "database": ["db_query"],
    "version_control": ["git_operations"],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def select_tool(
    task_type: str,
    query: str = "",
    constraints: dict[str, object] | None = None,
) -> ToolRecommendation:
    """Select the optimal tool for a given task type.

    Args:
        task_type: One of the registered task-type keys (e.g. ``"web_search_general"``).
        query: Optional free-text description for future ranking hints.
        constraints: Optional runtime overrides (availability, budget, etc.).

    Returns:
        A ``ToolRecommendation`` with the winning tool, its score, ranked
        alternatives, and a human-readable reason.

    Raises:
        NoToolAvailableError: When *task_type* is not registered in the matrix.
        AllToolsUnavailableError: When every candidate for the task is unavailable.
    """
    _ = query  # reserved for future relevance hints
    logger.debug("select_tool_entry", task_type=task_type)

    candidates = _DECISION_MATRIX.get(task_type)

    if candidates is None:
        suggestions = _SUGGESTIONS.get(task_type, list(_DECISION_MATRIX.keys()))
        logger.warning(
            "tool_selector_no_match",
            task_type=task_type,
            suggestions=suggestions,
        )
        raise NoToolAvailableError(task_type, suggestions=suggestions)

    # Apply runtime constraint overrides if provided.
    if constraints:
        candidates = _apply_constraints(candidates, constraints)

    # Score every candidate.
    scored: list[tuple[ToolOption, float]] = [
        (option, _score_option(option)) for option in candidates
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    # Check all-unavailable.
    available = [pair for pair in scored if pair[0].available]
    if not available:
        logger.warning(
            "tool_selector_all_unavailable",
            task_type=task_type,
            candidates=[pair[0].name for pair in scored],
        )
        raise AllToolsUnavailableError(
            task_type, [pair[0].name for pair in scored]
        )

    winner_option, winner_score = available[0]

    # Collect ranked alternatives (all other options, preserving score order).
    alternatives: list[ToolOption] = [
        option for option, _score in scored if option.name != winner_option.name
    ]

    reason = _WIN_RATIONALES.get(winner_option.name, f"Best match for '{task_type}'.")

    logger.info(
        "tool_selector_result",
        task_type=task_type,
        winner=winner_option.name,
        score=round(winner_score, 4),
        alternatives=[a.name for a in alternatives],
    )

    return ToolRecommendation(
        tool_name=winner_option.name,
        score=winner_score,
        alternatives=tuple(alternatives),
        reason=reason,
    )


def get_tool_matrix() -> dict[str, list[str]]:
    """Return the full tool selection decision matrix.

    Each key is a task type and each value is the ordered list of
    candidate tool names (highest relevance first).
    """
    result: dict[str, list[str]] = {}
    for task_type, options in _DECISION_MATRIX.items():
        result[task_type] = [o.name for o in options]
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_constraints(
    candidates: list[ToolOption],
    constraints: dict[str, object],
) -> list[ToolOption]:
    """Apply runtime constraints to a candidate list.

    Supported constraints:

    * ``"unavailable_tools": list[str]`` — mark these tools as unavailable.

    Returns a new list with updated ``available`` flags.
    """
    raw = constraints.get("unavailable_tools", [])
    unavailable: list[str]
    if isinstance(raw, list):
        unavailable = [str(t) for t in raw]
    else:
        unavailable = []
    applied: list[ToolOption] = []
    for option in candidates:
        if option.name in unavailable:
            applied.append(
                ToolOption(
                    name=option.name,
                    relevance=option.relevance,
                    cost_efficiency=option.cost_efficiency,
                    auth_ease=option.auth_ease,
                    available=False,
                )
            )
        else:
            applied.append(option)
    return applied
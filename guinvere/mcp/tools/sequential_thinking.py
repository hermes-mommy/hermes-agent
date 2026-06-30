"""MCP Sequential Thinking Tool — Chain-of-thought reasoning.

Provides structured chain-of-thought reasoning for complex problem
decomposition with thought numbering, branching, and revision support.

Each thinking session is an immutable sequence of :class:`Thought` records
stored in a frozen :class:`ThinkingSession` dataclass.  Sessions are
ephemeral and kept in an in-memory dict (no persistence).

Auth level: READ_AUTO (pure computation, no side effects).
Cost: LLM tokens only (tracked by caller, not this tool).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import structlog

from guinvere.mcp.auth import AuthLevel, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# In-memory session storage (ephemeral, per-process)
# ---------------------------------------------------------------------------

_sessions: dict[str, "ThinkingSession"] = {}

# Key used by the top-level ``sequential_think`` MCP tool when no explicit
# session management is required.
_DEFAULT_SESSION_KEY: str = "__default__"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Thought:
    """A single reasoning step within a thinking session."""

    thought_number: int
    content: str
    is_revision: bool = False
    revises_thought: int | None = None
    branch_from_thought: int | None = None
    branch_id: str | None = None


@dataclass(frozen=True)
class ThinkingSession:
    """Immutable snapshot of a chain-of-thought session."""

    topic: str
    total_thoughts: int
    thoughts: tuple[Thought, ...]
    needs_more_thoughts: bool = False


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class SessionNotFoundError(Exception):
    """Raised when a referenced session does not exist."""


# ---------------------------------------------------------------------------
# Internal session helpers
# ---------------------------------------------------------------------------


def _get_session_or_raise(session_id: str) -> ThinkingSession:
    """Return the session for *session_id* or raise :class:`SessionNotFoundError`."""
    try:
        return _sessions[session_id]
    except KeyError:
        raise SessionNotFoundError(
            f"Thinking session '{session_id}' not found."
        ) from None


def create_session(topic: str, initial_estimate: int = 5) -> str:
    """Create a new thinking session and return its unique ID.

    Args:
        topic: Short description of the reasoning topic.
        initial_estimate: Expected number of thoughts (advisory only).

    Returns:
        A UUID string identifying the new session.
    """
    session_id = str(uuid.uuid4())
    _sessions[session_id] = ThinkingSession(
        topic=topic,
        total_thoughts=initial_estimate,
        thoughts=(),
        needs_more_thoughts=True,
    )
    logger.info(
        "thinking_session_created",
        session_id=session_id,
        topic=topic,
        initial_estimate=initial_estimate,
    )
    return session_id


def add_thought(
    session_id: str,
    content: str,
    next_needed: bool,
    thought_number: int,
) -> ThinkingSession:
    """Append a new thought to an existing session.

    Logs a warning if *thought_number* exceeds the session's
    ``total_thoughts + 5`` but still records the thought.

    Returns:
        The updated :class:`ThinkingSession`.
    """
    session = _get_session_or_raise(session_id)

    if thought_number > session.total_thoughts + 5:
        logger.warning(
            "thought_number_exceeds_estimate",
            session_id=session_id,
            thought_number=thought_number,
            total_thoughts=session.total_thoughts,
        )

    thought = Thought(thought_number=thought_number, content=content)
    updated = replace(
        session,
        thoughts=(*session.thoughts, thought),
        total_thoughts=max(session.total_thoughts, thought_number),
        needs_more_thoughts=next_needed,
    )
    _sessions[session_id] = updated
    logger.debug(
        "thought_added",
        session_id=session_id,
        thought_number=thought_number,
    )
    return updated


def branch_thought(
    session_id: str,
    from_thought: int,
    content: str,
) -> ThinkingSession:
    """Create a branching thought from an existing thought number.

    The new thought receives the next sequential number and a fresh
    ``branch_id``.

    Returns:
        The updated :class:`ThinkingSession`.
    """
    session = _get_session_or_raise(session_id)
    next_number = len(session.thoughts) + 1
    branch_id = uuid.uuid4().hex[:8]

    thought = Thought(
        thought_number=next_number,
        content=content,
        branch_from_thought=from_thought,
        branch_id=branch_id,
    )
    updated = replace(
        session,
        thoughts=(*session.thoughts, thought),
        total_thoughts=max(session.total_thoughts, next_number),
    )
    _sessions[session_id] = updated
    logger.debug(
        "thought_branched",
        session_id=session_id,
        from_thought=from_thought,
        branch_id=branch_id,
    )
    return updated


def revise_thought(
    session_id: str,
    thought_number: int,
    new_content: str,
) -> ThinkingSession:
    """Revise an existing thought in-place.

    If the target *thought_number* does not exist, logs a warning and
    records the revision as a **new** thought instead.

    Returns:
        The updated :class:`ThinkingSession`.
    """
    session = _get_session_or_raise(session_id)

    # Find the last thought with this number (handles duplicates gracefully).
    matching_indices = [
        i
        for i, t in enumerate(session.thoughts)
        if t.thought_number == thought_number
    ]

    if not matching_indices:
        logger.warning(
            "revision_target_not_found",
            session_id=session_id,
            thought_number=thought_number,
        )
        # Record as a new thought with revision metadata.
        next_number = len(session.thoughts) + 1
        new_thought = Thought(
            thought_number=next_number,
            content=new_content,
            is_revision=True,
            revises_thought=thought_number,
        )
        updated = replace(
            session,
            thoughts=(*session.thoughts, new_thought),
            total_thoughts=max(session.total_thoughts, next_number),
        )
    else:
        idx = matching_indices[-1]
        revised = replace(
            session.thoughts[idx],
            content=new_content,
            is_revision=True,
            revises_thought=thought_number,
        )
        thoughts_list = list(session.thoughts)
        thoughts_list[idx] = revised
        updated = replace(session, thoughts=tuple(thoughts_list))

    _sessions[session_id] = updated
    logger.debug(
        "thought_revised",
        session_id=session_id,
        thought_number=thought_number,
    )
    return updated


def get_session(session_id: str) -> ThinkingSession:
    """Retrieve a thinking session by ID.

    Raises:
        SessionNotFoundError: If the session does not exist.
    """
    return _get_session_or_raise(session_id)


def finalize_session(session_id: str, conclusion: str) -> str:
    """Finalize a session and return a formatted summary.

    The session is removed from in-memory storage after finalization.

    Returns:
        A multi-line string summarising all thoughts and the conclusion.
    """
    session = _get_session_or_raise(session_id)

    lines: list[str] = [f"Topic: {session.topic}", ""]
    for t in session.thoughts:
        label = f"Thought {t.thought_number}"
        annotations: list[str] = []
        if t.is_revision:
            annotations.append(f"revises #{t.revises_thought}")
        if t.branch_from_thought is not None:
            annotations.append(f"branch from #{t.branch_from_thought}")
        if annotations:
            label += f" ({', '.join(annotations)})"
        lines.append(f"{label}: {t.content}")

    lines.append("")
    lines.append(f"Conclusion: {conclusion}")

    summary = "\n".join(lines)

    del _sessions[session_id]
    logger.info(
        "thinking_session_finalized",
        session_id=session_id,
        thought_count=len(session.thoughts),
    )
    return summary


# ---------------------------------------------------------------------------
# MCP tool function
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="sequential_thinking")
async def sequential_think(
    thought: str,
    thought_number: int,
    total_thoughts: int,
    next_thought_needed: bool = True,
    is_revision: bool = False,
    revises_thought: int | None = None,
    branch_from_thought: int | None = None,
    branch_id: str | None = None,
) -> dict[str, object]:
    """Record a thinking step in the chain-of-thought.

    Automatically creates a default session on first invocation.
    Returns metadata about the current state of the reasoning chain.
    """
    # Auto-create default session if absent.
    if _DEFAULT_SESSION_KEY not in _sessions:
        _sessions[_DEFAULT_SESSION_KEY] = ThinkingSession(
            topic="sequential-thinking",
            total_thoughts=total_thoughts,
            thoughts=(),
            needs_more_thoughts=True,
        )
        logger.info("default_session_auto_created")

    session = _sessions[_DEFAULT_SESSION_KEY]

    # Warn if thought number significantly exceeds estimate.
    if thought_number > session.total_thoughts + 5:
        logger.warning(
            "thought_number_exceeds_estimate",
            thought_number=thought_number,
            total_thoughts=session.total_thoughts,
        )

    # Warn if revision targets a non-existent thought.
    if is_revision and revises_thought is not None:
        existing = [
            t for t in session.thoughts if t.thought_number == revises_thought
        ]
        if not existing:
            logger.warning(
                "revision_target_not_found_in_default",
                revises_thought=revises_thought,
            )

    new_thought = Thought(
        thought_number=thought_number,
        content=thought,
        is_revision=is_revision,
        revises_thought=revises_thought,
        branch_from_thought=branch_from_thought,
        branch_id=branch_id,
    )

    updated = replace(
        session,
        thoughts=(*session.thoughts, new_thought),
        total_thoughts=max(session.total_thoughts, thought_number, total_thoughts),
        needs_more_thoughts=next_thought_needed,
    )
    _sessions[_DEFAULT_SESSION_KEY] = updated

    logger.info(
        "sequential_think_recorded",
        thought_number=thought_number,
        total_thoughts=updated.total_thoughts,
        thoughts_recorded=len(updated.thoughts),
    )

    return {
        "thought_number": thought_number,
        "total_thoughts": updated.total_thoughts,
        "next_thought_needed": next_thought_needed,
        "thoughts_recorded": len(updated.thoughts),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register the sequential thinking tool on the MCP server.

    Adds a single tool ``sequential_thinking`` gated with
    ``AuthLevel.READ_AUTO`` (pure computation, no side effects).
    """
    mcp.tool(name="sequential_thinking")(sequential_think)

    logger.info("sequential_thinking_tool_registered")

"""Per-session LangGraph state machine for Guinevere's Living Autonomy Kernel.

This module implements LK-008: a per-session subgraph that manages the SDLC
lifecycle of an individual engineering session. Each session receives a unique
thread_id and an isolated SessionState. Worktree, profile, and Discord thread
managers are placeholders for real integrations in later LK tickets.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from guinevere.life_kernel.state import SessionState

logger = structlog.get_logger(__name__)


class SessionGraph:
    """Factory for per-session LangGraph subgraphs.

    Each instance represents a single engineering session. The graph encodes the
    SDLC cycle: plan → execute → validate → (audit) → document → complete.
    """

    def __init__(self, session_id: str, project_id: str | None = None) -> None:
        """Initialize a session graph descriptor.

        Args:
            session_id: Unique identifier for the session.
            project_id: Optional project namespace. When set, the thread_id
                becomes ``session-{project_id}-{session_id}-{uuid}``,
                providing per-project checkpoint isolation.
        """
        self.session_id = session_id
        self.project_id = project_id
        self.thread_id = self._generate_thread_id()

    def _generate_thread_id(self) -> str:
        """Generate a unique thread_id for LangGraph checkpointing.

        P19 Multi-Project Context: when ``project_id`` is set, the thread_id
        includes the project namespace so per-project checkpoints do not
        collide.
        """
        if self.project_id:
            return f"session-{self.project_id}-{self.session_id}-{uuid.uuid4().hex}"
        return f"session-{self.session_id}-{uuid.uuid4().hex}"

    @classmethod
    def create_session_graph(cls, session_id: str, project_id: str | None = None) -> tuple[CompiledStateGraph[SessionState], str]:
        """Create a fresh compiled StateGraph for the given session.

        Args:
            session_id: Unique identifier for the session.
            project_id: Optional project namespace for scoped thread_id.

        Returns:
            A tuple of (compiled_state_graph, thread_id).
        """
        instance = cls(session_id, project_id=project_id)
        return instance._build_graph(), instance.thread_id  # noqa: SLF001

    def _build_graph(self) -> CompiledStateGraph[SessionState]:
        """Build and compile the session SDLC StateGraph."""
        builder = StateGraph(SessionState)

        builder.add_node("plan", _plan_node)
        builder.add_node("execute", _execute_node)
        builder.add_node("validate", _validate_node)
        builder.add_node("audit", _audit_node)
        builder.add_node("document", _document_node)
        builder.add_node("complete", _complete_node)

        builder.add_edge(START, "plan")
        builder.add_edge("plan", "execute")
        builder.add_edge("execute", "validate")
        builder.add_conditional_edges(
            "validate",
            _route_from_validate,
            {"audit": "audit", "execute": "execute", "document": "document"},
        )
        builder.add_edge("audit", "document")
        builder.add_edge("document", "complete")
        builder.add_edge("complete", END)

        return builder.compile()


async def _plan_node(state: SessionState) -> dict[str, Any]:
    """Transition session from PLANNING to READY.

    Args:
        state: Current session state.

    Returns:
        State update dict with new sdlc_phase and logged plan step.
    """
    session_id = state.get("session_id", "unknown")
    logger.info(
        "plan_node_entry",
        session_id=session_id,
        current_phase=state.get("sdlc_phase"),
    )
    return {
        "sdlc_phase": "READY",
        "context": {
            **state.get("context", {}),
            "plan_logged": True,
            "planned_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def _execute_node(state: SessionState) -> dict[str, Any]:
    """Transition session from READY through EXECUTING to COMPLETED.

    This is a placeholder for the real execution engine implemented in LK-014.

    Args:
        state: Current session state.

    Returns:
        State update dict with new sdlc_phase.
    """
    session_id = state.get("session_id", "unknown")
    current_phase = state.get("sdlc_phase", "PLANNING")

    if current_phase == "READY":
        next_phase = "EXECUTING"
    else:
        next_phase = "COMPLETED"

    logger.info(
        "execute_node_entry",
        session_id=session_id,
        current_phase=current_phase,
        next_phase=next_phase,
    )

    return {
        "sdlc_phase": next_phase,
        "context": {
            **state.get("context", {}),
            "executed": True,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def _validate_node(state: SessionState) -> dict[str, Any]:
    """Run validation checks and route to audit or back to execution.

    Placeholder validation always passes unless the session context explicitly
    requests a re-run via ``force_validation_failure``.

    Args:
        state: Current session state.

    Returns:
        State update dict with new sdlc_phase.
    """
    session_id = state.get("session_id", "unknown")
    ctx = state.get("context", {})

    force_failure = ctx.get("force_validation_failure", False)

    if force_failure:
        logger.info(
            "validate_node_failure",
            session_id=session_id,
            reason="forced_validation_failure",
        )
        return {
            "sdlc_phase": "EXECUTING",
            "context": {
                **ctx,
                "validated": False,
                "validation_failure_count": ctx.get("validation_failure_count", 0) + 1,
            },
        }

    logger.info(
        "validate_node_success",
        session_id=session_id,
    )
    return {
        "sdlc_phase": "AUDIT",
        "context": {
            **ctx,
            "validated": True,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def _audit_node(state: SessionState) -> dict[str, Any]:
    """Placeholder auditor gate for the session.

    Args:
        state: Current session state.

    Returns:
        State update dict moving phase to DOCUMENT.
    """
    session_id = state.get("session_id", "unknown")
    logger.info(
        "audit_node_entry",
        session_id=session_id,
    )
    return {
        "sdlc_phase": "DOCUMENT",
        "context": {
            **state.get("context", {}),
            "audited": True,
            "audited_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def _document_node(state: SessionState) -> dict[str, Any]:
    """Placeholder documentation sync node for the session.

    Args:
        state: Current session state.

    Returns:
        State update dict moving phase to DONE.
    """
    session_id = state.get("session_id", "unknown")
    logger.info(
        "document_node_entry",
        session_id=session_id,
    )
    return {
        "sdlc_phase": "DONE",
        "context": {
            **state.get("context", {}),
            "documented": True,
            "documented_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def _complete_node(state: SessionState) -> dict[str, Any]:
    """Mark the session as completed.

    Args:
        state: Current session state.

    Returns:
        State update dict with final phase and completion timestamp.
    """
    session_id = state.get("session_id", "unknown")
    logger.info(
        "complete_node_entry",
        session_id=session_id,
    )
    return {
        "sdlc_phase": "DONE",
        "context": {
            **state.get("context", {}),
            "completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def _route_from_validate(state: SessionState) -> str:
    """Conditional router after validate_node.

    Args:
        state: Current session state.

    Returns:
        Name of the next node.
    """
    phase = state.get("sdlc_phase", "AUDIT")
    if phase == "EXECUTING":
        return "execute"
    if phase == "DOCUMENT":
        return "document"
    return "audit"


class SessionWorktree:
    """Placeholder worktree manager for per-session git isolation.

    Real git worktree creation/cleanup will be implemented in LK-014.
    """

    def __init__(self, session_id: str) -> None:
        """Initialize the worktree manager for a session.

        Args:
            session_id: Unique identifier for the session.
        """
        self.session_id = session_id
        self.worktree_path: str | None = None

    def create(self, worktree_path: str) -> str:
        """Record intent to create an isolated git worktree for the session.

        Args:
            worktree_path: Target path for the worktree.

        Returns:
            The recorded worktree path.
        """
        self.worktree_path = worktree_path
        logger.info(
            "session_worktree_create_intent",
            session_id=self.session_id,
            worktree_path=worktree_path,
        )
        return worktree_path

    def cleanup(self) -> None:
        """Record intent to clean up the session's git worktree."""
        logger.info(
            "session_worktree_cleanup_intent",
            session_id=self.session_id,
            worktree_path=self.worktree_path,
        )


@dataclass
class SessionProfile:
    """Session-specific configuration profile."""

    session_id: str
    sdlc_phase: str
    worktree_path: str | None
    discord_thread_id: str | None
    created_at: datetime
    config: dict[str, Any] = field(default_factory=dict)


class SessionProfileManager:
    """In-memory manager for session profiles.

    Production persistence will be added when the living kernel integrates with
    the PostgreSQL backend.
    """

    def __init__(self) -> None:
        """Initialize an profile manager backed by an in-memory store."""
        self._profiles: dict[str, SessionProfile] = {}

    def create_profile(self, session_id: str) -> SessionProfile:
        """Create a new session profile.

        Args:
            session_id: Unique identifier for the session.

        Returns:
            The created session profile.
        """
        profile = SessionProfile(
            session_id=session_id,
            sdlc_phase="PLANNING",
            worktree_path=None,
            discord_thread_id=None,
            created_at=datetime.now(timezone.utc),
            config={},
        )
        self._profiles[session_id] = profile
        logger.info("session_profile_created", session_id=session_id)
        return profile

    def get_profile(self, session_id: str) -> SessionProfile | None:
        """Retrieve an existing session profile.

        Args:
            session_id: Unique identifier for the session.

        Returns:
            The session profile if found, otherwise None.
        """
        return self._profiles.get(session_id)

    def list_active_profiles(self) -> list[SessionProfile]:
        """List all currently stored session profiles.

        Returns:
            List of active session profiles.
        """
        return list(self._profiles.values())


class DiscordThreadManager:
    """Placeholder Discord thread manager for per-session communication.

    Real Discord.py integration will be implemented in LK-011.
    """

    def __init__(self) -> None:
        """Initialize the placeholder Discord thread manager."""
        self._threads: dict[str, dict[str, Any]] = {}

    def create_thread(self, session_id: str, channel_id: str) -> str:
        """Record intent to create a Discord thread for a session.

        Args:
            session_id: Unique identifier for the session.
            channel_id: Discord channel identifier.

        Returns:
            A synthetic thread_id for the placeholder thread.
        """
        thread_id = f"discord-thread-{session_id}-{uuid.uuid4().hex[:8]}"
        self._threads[thread_id] = {
            "session_id": session_id,
            "channel_id": channel_id,
            "messages": [],
            "closed": False,
        }
        logger.info(
            "discord_thread_create_intent",
            session_id=session_id,
            channel_id=channel_id,
            thread_id=thread_id,
        )
        return thread_id

    def post_update(self, thread_id: str, message: str) -> bool:
        """Record intent to post a message to a Discord thread.

        Args:
            thread_id: Identifier of the thread.
            message: Message content to post.

        Returns:
            True if the update was recorded.
        """
        if thread_id not in self._threads:
            logger.warning("discord_thread_not_found", thread_id=thread_id)
            return False
        self._threads[thread_id]["messages"].append(message)
        logger.info(
            "discord_thread_post_intent",
            thread_id=thread_id,
            message=message,
        )
        return True

    def close_thread(self, thread_id: str) -> bool:
        """Record intent to close a Discord thread.

        Args:
            thread_id: Identifier of the thread.

        Returns:
            True if the thread was closed.
        """
        if thread_id not in self._threads:
            logger.warning("discord_thread_not_found", thread_id=thread_id)
            return False
        self._threads[thread_id]["closed"] = True
        logger.info("discord_thread_close_intent", thread_id=thread_id)
        return True

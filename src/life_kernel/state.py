"""TypedDict state schemas for Guinevere's Living Autonomy Kernel.

This module defines the core state structures used by the LangGraph StateGraph
for the 24/7 autonomous AI companion kernel. State is structured as TypedDict with
controlled updates via Annotated reducers.
"""

from __future__ import annotations

from typing import Annotated, Any, NotRequired, TypedDict
from enum import StrEnum


class LifeMindPhase(StrEnum):
    """Execution phases for the autonomous AI companion kernel.

    The kernel cycles through these phases in order: observe → decide → act → reflect.
    Each phase represents a distinct cognitive activity in the autonomous loop.
    """

    OBSERVE = "observe"
    DECIDE = "decide"
    ACT = "act"
    REFLECT = "reflect"
    IDLE = "idle"
    HARD_STOPPED = "hard_stopped"


class Priority(StrEnum):
    """Autonomy priority levels for task scheduling.

    Higher priority values take precedence over lower values. This enum defines
    the 8-level priority hierarchy used by the autonomous kernel.
    """

    HARD_STOP_SAFETY = "hard_stop_safety"
    KEEP_ALIVE = "keep_alive"
    PROTECT_SECRETS = "protect_secrets"
    URGENT_DAILY = "urgent_daily"
    ACTIVE_COMMITMENTS = "active_commitments"
    IMPROVE_AUTONOMY = "improve_autonomy"
    ENGINEERING = "engineering"
    EXPLORE_RESEARCH = "explore_research"


def add_observations_reducer(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append new observations to the observations list, capping at 100 most recent.

    This reducer ensures the observations list does not grow unbounded. Only the
    most recent 100 observations are retained, providing a sliding window of recent
    awareness data.

    Args:
        left: Existing observations list.
        right: New observations to append.

    Returns:
        Combined observations list with at most 100 most recent entries.
    """
    combined = left + right
    return combined[-100:] if len(combined) > 100 else combined


def add_audit_reducer(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append audit entries to the audit trail, capping at 500 entries.

    This reducer maintains a bounded audit trail for compliance and debugging.
    Only the most recent 500 audit entries are retained, providing a historical
    record without excessive storage.

    Args:
        left: Existing audit entries list.
        right: New audit entries to append.

    Returns:
        Combined audit entries list with at most 500 most recent entries.
    """
    combined = left + right
    return combined[-500:] if len(combined) > 500 else combined

def add_journal_reducer(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append journal entries, capping at 1000 most recent entries.

    This reducer maintains a bounded reflective journal for self-awareness and
    learning (AC-LIFE-008). Only the most recent 1000 journal entries are
    retained, providing a historical record of Guinevere's reasoning without
    unbounded growth.

    Args:
        left: Existing journal entries.
        right: New journal entries to append.

    Returns:
        Combined journal entries with at most 1000 most recent entries.
    """
    combined = left + right
    return combined[-1000:] if len(combined) > 1000 else combined


class LifeMindState(TypedDict, total=False):
    """Global state for the autonomous AI companion kernel.

    This TypedDict represents the complete state of the living autonomy kernel,
    including observations, decision context, goals, commitments, concerns, and
    execution metadata. The state is managed by LangGraph and checkpointed for
    persistence and recovery.
    """

    observations: Annotated[list[dict[str, Any]], add_observations_reducer]
    """List of recent observations from sensors and world state.

    Each observation is a dict containing timestamp, source, and data. The reducer
    caps this list at 100 most recent entries to prevent unbounded growth.
    """

    decision_context: dict[str, Any]
    """Current decision context including world model, goals, and concerns.

    This dictionary provides the reasoning context for decision-making, including
    the current world model, active goals, pending concerns, and other relevant
    context for autonomous action selection.
    """

    current_phase: LifeMindPhase
    """Current execution phase of the autonomous kernel.

    The kernel cycles through: observe → decide → act → reflect. This field tracks
    the current phase for logging, debugging, and conditional routing.
    """

    is_active: bool
    """Whether the autonomous kernel is currently running.

    When False, the kernel is paused or stopped. This flag controls whether the
    observe→decide→act→reflect cycle executes.
    """

    last_heartbeat: str
    """ISO 8601 timestamp of the last heartbeat.

    Used for health monitoring and recovery. The heartbeat indicates when the
    kernel last executed a cycle.
    """

    goals: list[dict[str, Any]]
    """Active goals for the autonomous companion.

    Each goal is a dict with fields: goal_id, priority, description, deadline,
    and status. The kernel prioritizes and schedules actions to achieve these goals.
    """

    commitments: list[dict[str, Any]]
    """Pending commitments and obligations.

    These represent promises or obligations that must be fulfilled, such as
    responding to messages, completing tasks, or maintaining specific behaviors.
    """

    concerns: list[dict[str, Any]]
    """Active concerns that require attention or resolution.

    Concerns represent potential issues, risks, or areas of concern that the kernel
    should monitor and address as part of autonomous management.
    """

    current_focus: NotRequired[str]
    """Current focus area for the autonomous kernel.

    Optional field indicating which domain or area the kernel is currently focusing
    on, such as engineering, comms, health, or self-improvement.
    """

    hard_stop_requested: bool
    """HARD STOP flag — indicates a request to immediately halt the kernel.

    When True, the kernel routes to END immediately, pausing all autonomous
    operations. This is the highest-priority safety mechanism in the autonomy
    hierarchy.
    """

    session_count: int
    """Number of active sessions.

    Tracks the count of concurrent sessions that the kernel is managing or aware
    of.
    """

    audit_entries: Annotated[list[dict[str, Any]], add_audit_reducer]
    """Audit trail entries for compliance and debugging.

    Each entry contains timestamp, event_type, details, and other metadata. The
    reducer caps this list at 500 entries to maintain bounded audit storage.
    """

    decision: NotRequired[str]
    """Decision output from decide_node for routing.

    This field stores the decision made by the decide_node as a normal string
    value ("act", "idle", "reflect", "hard_stop") instead of using Command
    objects. This allows route_from_decide conditional edges to properly map
    decisions to next nodes.
    """

    act_count: int
    """Number of actions executed in the current cycle.

    Incremented by act_node on each action execution. Used by reflect_node
    for cycle auditing and anomaly detection.
    """

    cycle_count: int
    """Total number of observe→decide→act→reflect cycles completed.

    Incremented by reflect_node on each full cycle completion. Provides a
    monotonic counter for cycle-based auditing.
    """

    errors: list[dict[str, Any]]
    """Errors detected during the current cycle.

    Each error is a dict with timestamp, source node, error message, and
    context. Used by reflect_node for anomaly detection and audit trail.
    """

    kg_adapter: NotRequired[Any]
    """Optional P16 Knowledge Graph recall adapter injected via config/context."""

    memory_adapter: NotRequired[Any]
    """Optional P18 Memory recall adapter injected via config/context."""

    # P20 Discord-Visible Autonomy — fields for dashboard display
    # These are set by graph nodes (decide/act/idle) and read by DashboardRenderer
    last_autonomous_decision: NotRequired[str]
    last_action_result: NotRequired[str]
    next_planned_action: NotRequired[str]
    memory_status: NotRequired[str]
    uptime_start: NotRequired[str]

    # P20 Continuation — real recall + journal fields
    journal_entries: Annotated[list[dict[str, Any]], add_journal_reducer]
    """Reflective journal entries for self-awareness (AC-LIFE-008).

    Each entry: {entry_id, timestamp, cycle, reasoning, lessons_learned, confidence}.
    Capped at 1000 entries by add_journal_reducer.
    """

    recalled_concepts: NotRequired[list[dict[str, Any]]]
    """P16 KG concepts recalled for current decision context.

    Each concept: {name, relevance, source}. Populated by observe_node
    via DecisionContextBuilder when kg_adapter is available.
    """

    recalled_memories: NotRequired[list[dict[str, Any]]]
    """P18 episodic memories recalled for current decision context.

    Each memory: {id, safe_content, combined_score, classification, created_at}.
    Populated by observe_node via DecisionContextBuilder.
    """

    world_model_status: NotRequired[str]
    """Status of world model (P16/P18): 'active', 'degraded', or 'unavailable'."""

class SessionState(TypedDict, total=False):
    """State for individual sessions managed by the autonomous kernel.

    This TypedDict represents the state of a specific session, including its
    SDLC phase, pending and completed tasks, context, and memory references.
    Sessions are managed by domain minds and contribute to the global life mind.
    """

    session_id: str
    """Unique identifier for the session.

    Each session has a unique ID for tracking, logging, and checkpointing.
    """

    sdlc_phase: str
    """Current SDLC phase of the session.

    Tracks the session's progress through its lifecycle: planning, execution,
    review, or completion.
    """

    pending_tasks: list[dict[str, Any]]
    """Tasks pending execution in this session.

    Each task is a dict with fields: task_id, priority, description, assigned_to,
    and deadline.
    """

    completed_tasks: list[dict[str, Any]]
    """Tasks completed in this session.

    Each task is a dict with fields: task_id, completed_at, result, and status.
    """

    context: dict[str, Any]
    """Context specific to this session.

    Contains session-specific data such as user preferences, task parameters,
    and other contextual information.
    """

    memory_refs: list[str]
    """Memory reference IDs for long-term memory storage.

    References to memory entries created or updated by this session.
    """
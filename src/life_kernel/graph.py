"""LangGraph StateGraph skeleton for Guinevere's Living Autonomy Kernel.

This module implements the 4-node cyclic graph: observe → decide → act → reflect → observe.
The kernel uses LangGraph for state management, checkpointing, and autonomous execution.
"""

from __future__ import annotations

import asyncio
from typing import Any
from datetime import datetime

import structlog

from src.life_kernel.state import (
    LifeMindPhase,
    LifeMindState,
    Priority,
)

logger = structlog.get_logger(__name__)

# Safety + cost guardrails for LLM-driven autonomy.
_HERMES_THINK_TIMEOUT = 30.0
_VALID_DECISIONS = {"act", "reflect", "idle", "end", "observe"}

# Module-level registry for the real KG/memory adapters. Set by
# create_life_mind_graph() so the module-level node functions (observe_node,
# decide_node, idle_node, reflect_node) can access the injected adapters
# without threading them through LangGraph state (which is JSON-serialised
# by the checkpointer and cannot hold live adapter objects). When None the
# kernel runs headless (pre-continuation behaviour).
_ADAPTERS: dict[str, Any] = {"kg": None, "memory": None, "journal": None}


def set_adapters(
    kg_adapter: Any | None = None,
    memory_adapter: Any | None = None,
    journal_writer: Any | None = None,
) -> None:
    """Register real KG/memory adapters + journal writer for the node functions.

    Called by create_life_mind_graph() at construction time. The adapters
    are held in a module-level registry because LangGraph checkpoints
    state as JSON and cannot serialise live adapter objects — so the
    nodes read them from here, not from state.

    Resets the registry first so a graph built without adapters is truly
    headless (no stale adapters leak from a previous build in the same
    process — important for test isolation and for a headless fallback
    graph after a prior wired graph).
    """
    _ADAPTERS["kg"] = kg_adapter
    _ADAPTERS["memory"] = memory_adapter
    _ADAPTERS["journal"] = journal_writer


def reset_adapters() -> None:
    """Clear the adapter registry (used by tests for isolation)."""
    _ADAPTERS["kg"] = None
    _ADAPTERS["memory"] = None
    _ADAPTERS["journal"] = None

# System prompt for the autonomy router. The brain must return EXACTLY one of
# the valid decision tokens so we can map it onto a graph edge. It is
# explicitly told NOT to override HARD STOP — that safety path is enforced
# non-LLM in decide_node before the brain is ever consulted.
_DECIDE_SYSTEM_PROMPT = (
    "You are Guinevere's autonomous life router. Given the kernel's current "
    "goals, commitments, concerns and observations, decide the single next "
    "phase. Respond with EXACTLY one word from: act, reflect, idle, observe. "
    "Never output anything else. You do not control safety: HARD STOP is "
    "enforced outside this call."
)

_ACT_SYSTEM_PROMPT = (
    "You are Guinevere's act planner. Given the highest-priority goal, "
    "describe a concrete next action in ONE short sentence. Do not execute "
    "anything; you only propose. Be specific but terse."
)

_IDLE_SYSTEM_PROMPT = (
    "You are Guinevere's self-direction engine. The operator is silent and "
    "there is no pending work. Propose ONE self-directed agenda item that "
    "keeps you usefully alive and improving (review recent observations, "
    "evaluate a process, consolidate a learning, or plan a small "
    "self-improvement). Reply with a short label and a one-sentence "
    "description. Keep it display-only — never propose real side-effects."
)


def _extract_brain_text(result: dict[str, Any] | None) -> str:
    """Pull the assistant's text out of a HermesBrain.think() result.

    The brain returns ``{"final_response": "..."}`` on success or a fallback
    dict on failure. We normalize to a stripped string; callers validate it.
    """
    if not isinstance(result, dict):
        return ""
    text = result.get("final_response", "")
    return str(text).strip() if text else ""


async def _safe_think(
    hermes_brain: Any | None,
    user_message: str,
    system_prompt: str,
    *,
    timeout: float = _HERMES_THINK_TIMEOUT,
) -> str:
    """Call ``hermes_brain.think()`` with a hard timeout and fail-safe fallback.

    Returns the assistant's text, or "" if the brain is unavailable, times
    out, or errors. The kernel never stalls on the LLM: any failure degrades
    gracefully to the existing static logic in the calling node.
    """
    if hermes_brain is None:
        return ""
    try:
        result = await asyncio.wait_for(
            hermes_brain.think(user_message=user_message, system_prompt=system_prompt),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning("hermes_brain_think_timeout", timeout=timeout)
        return ""
    except Exception as exc:  # noqa: BLE001 — brain must never crash the kernel
        logger.warning("hermes_brain_think_error", error_type=type(exc).__name__)
        return ""
    return _extract_brain_text(result)


async def observe_node(state: LifeMindState) -> dict[str, Any]:
    """Collect observation data and compile context from world state.

    Reads current state, checks world model availability, and compiles an observation
    dict that captures the kernel's awareness at this moment.

    Args:
        state: Current kernel state.

    Returns:
        Dict with updated observations list and observation data.
    """
    logger.info(
        "observe_node_entry",
        current_phase=state.get("current_phase"),
        is_active=state.get("is_active", False),
        last_heartbeat=state.get("last_heartbeat"),
    )

    # Determine heartbeat rhythm from phase (placeholder for P19 heartbeat integration)
    phase = state.get("current_phase", LifeMindPhase.OBSERVE)
    heartbeat_map = {
        LifeMindPhase.OBSERVE: "observe_heartbeat",
        LifeMindPhase.DECIDE: "decide_heartbeat",
        LifeMindPhase.ACT: "act_heartbeat",
        LifeMindPhase.REFLECT: "reflect_heartbeat",
        LifeMindPhase.IDLE: "idle_heartbeat",
        LifeMindPhase.HARD_STOPPED: "hard_stop_heartbeat",
    }
    heartbeat_type = heartbeat_map.get(phase, "unknown_heartbeat")

    # Build decision context from the REAL P16 KG + P18 memory adapters
    # (LK-010 continuation). Adapters are read from the module-level registry
    # (set by create_life_mind_graph) because LangGraph checkpoints state as
    # JSON and cannot hold live adapter objects. Fail-soft: any adapter error
    # degrades gracefully — the kernel never crashes on recall.
    kg_adapter = _ADAPTERS.get("kg")
    memory_adapter = _ADAPTERS.get("memory")

    recalled_concepts: list[dict[str, Any]] = []
    recalled_memories: list[dict[str, Any]] = []
    world_model_status = "unavailable"
    memory_status = "—"

    if kg_adapter is None and memory_adapter is None:
        world_model_status = "unavailable"
        decision_context = {
            "p16_available": False,
            "p18_available": False,
            "kg_context": None,
            "memory_context": None,
        }
    else:
        # Seed the recall query from the current focus / latest observation.
        query_text = str(state.get("current_focus", "")) or "autonomous life observation"
        recall_context = {"query": query_text, "content": query_text}

        kg_degraded = False
        mem_degraded = False

        if kg_adapter is not None:
            try:
                kg_result = await kg_adapter.recall(recall_context)
                recalled_concepts = kg_result.get("concepts", [])
                kg_degraded = bool(kg_result.get("_degraded"))
            except Exception as exc:  # noqa: BLE001 — fail-soft
                logger.warning("observe_kg_recall_failed", error_type=type(exc).__name__)
                kg_degraded = True

        if memory_adapter is not None:
            try:
                mem_result = await memory_adapter.recall(recall_context)
                recalled_memories = mem_result.get("memories", [])
                mem_degraded = bool(mem_result.get("_degraded"))
            except Exception as exc:  # noqa: BLE001 — fail-soft
                logger.warning("observe_memory_recall_failed", error_type=type(exc).__name__)
                mem_degraded = True

        if kg_degraded or mem_degraded:
            world_model_status = "degraded"
        else:
            world_model_status = "active"

        decision_context = {
            "p16_available": kg_adapter is not None and not kg_degraded,
            "p18_available": memory_adapter is not None and not mem_degraded,
            "kg_context": recalled_concepts,
            "memory_context": recalled_memories,
        }

        # Build a concise memory_status string for the Discord dashboard.
        # We surface COUNTS and the top KG concept NAME only — never raw
        # memory content, which may be Critical-classified and must not land
        # in a Discord-visible field. Raw memories stay in state for the
        # brain (which has CRITICAL clearance) but are not echoed here.
        top_con = recalled_concepts[0].get("name", "") if recalled_concepts else ""
        memory_status = (
            f"{world_model_status}: {len(recalled_memories)} mem, {len(recalled_concepts)} kg"
            + (f" | top concept: {top_con}" if top_con else "")
        )

    logger.debug(
        "observe_world_model",
        world_model_status=world_model_status,
        n_recalled_concepts=len(recalled_concepts),
        n_recalled_memories=len(recalled_memories),
    )

    # world_model_available is now derived from real adapter status, not hardcoded.
    world_model_available = world_model_status == "active"

    # Compile observation dict
    observations = state.get("observations", [])
    observation_data = {
        "phase": phase,
        "heartbeat": heartbeat_type,
        "timestamp": datetime.now().isoformat(),
        "n_observations": len(observations),
        "n_goals": len(state.get("goals", [])),
        "n_commitments": len(state.get("commitments", [])),
        "n_concerns": len(state.get("concerns", [])),
        "world_model_available": world_model_available,
        "world_model_status": world_model_status,
        "is_active": state.get("is_active", False),
    }

    # Append observation to observations list
    updated_observations = [observation_data]

    logger.debug(
        "observe_node_complete",
        observations_count=len(updated_observations),
        observation_data=observation_data,
    )

    return {
        "observations": updated_observations,
        "decision_context": decision_context,
        "recalled_concepts": recalled_concepts,
        "recalled_memories": recalled_memories,
        "world_model_status": world_model_status,
        "memory_status": memory_status,
    }


async def decide_node(state: LifeMindState) -> dict[str, Any]:
    """Priority engine that ranks possible actions and returns routing decision.

    Evaluates the current state against the autonomy priority hierarchy and decides
    which phase to execute next. Priority levels (highest to lowest):
    - HARD_STOP_SAFETY: Immediate halt
    - KEEP_ALIVE: Survival and recovery
    - PROTECT_SECRETS: Security and privacy
    - URGENT_DAILY: Daily life operations
    - ACTIVE_COMMITMENTS: Active obligations
    - IMPROVE_AUTONOMY: Self-improvement
    - ENGINEERING: Project work
    - EXPLORE: Research and exploration

    Args:
        state: Current kernel state.

    Returns:
        Dict with "decision" field containing routing decision ("act", "reflect", "idle", "end").
    """
    logger.info(
        "decide_node_entry",
        current_phase=state.get("current_phase"),
        is_active=state.get("is_active", False),
        hard_stop_requested=state.get("hard_stop_requested", False),
        goals_count=len(state.get("goals", [])),
        commitments_count=len(state.get("commitments", [])),
        concerns_count=len(state.get("concerns", [])),
    )

    # Priority hierarchy constants
    PRIORITY_URGENT_DAILY = 4
    PRIORITY_ACTIVE_COMMITMENTS = 5
    PRIORITY_ENGINEERING = 7

    # Check for hard stop request (highest priority)
    if state.get("hard_stop_requested", False):
        logger.warning("HARD_STOP requested - routing to END")
        return {"decision": "end"}

    # Check if kernel is inactive
    if not state.get("is_active", False):
        logger.info("kernel not active - routing to idle for self-directed tasks")
        return {"decision": "idle"}

    # Priority-based action selection
    highest_priority = 0
    action = "reflect"

    # Check for active commitments (PRIORITY_ACTIVE_COMMITMENTS)
    if len(state.get("commitments", [])) > 0:
        highest_priority = max(highest_priority, PRIORITY_ACTIVE_COMMITMENTS)
        action = "act"

    # Check for active goals (PRIORITY_ENGINEERING)
    if len(state.get("goals", [])) > 0:
        highest_priority = max(highest_priority, PRIORITY_ENGINEERING)
        action = "act"

    # Check for concerns (PRIORITY_URGENT_DAILY)
    if len(state.get("concerns", [])) > 0:
        highest_priority = max(highest_priority, PRIORITY_URGENT_DAILY)
        action = "act"

    # If no active goals, commitments, or concerns, route to idle for self-directed tasks
    if len(state.get("goals", [])) == 0 and len(state.get("commitments", [])) == 0 and len(state.get("concerns", [])) == 0:
        logger.info("no active goals, commitments, or concerns - routing to idle for self-directed tasks")
        return {"decision": "idle"}

    # Log action selection
    logger.info(
        "action_selected",
        highest_priority=highest_priority,
        action=action,
        goals_count=len(state.get("goals", [])),
        commitments_count=len(state.get("commitments", [])),
    )

    return {"decision": action}


async def act_node(state: LifeMindState) -> dict[str, Any]:
    """Execute autonomous actions based on goals and priorities.

    Reads goals from state, identifies highest-priority goal (by Priority enum),
    logs action intent, and increments cycle counters. If no goals exist,
    logs info and appends idle observation. Domain minds hook in LK-012/013/014.

    Args:
        state: Current kernel state.

    Returns:
        Dict with act_count, cycle_count, and optional observation.
    """
    logger.info(
        "act_node_entry",
        current_phase=state.get("current_phase"),
        goals_count=len(state.get("goals", [])),
    )

    # Read state fields
    goals = state.get("goals", [])
    act_count = state.get("act_count", 0)
    cycle_count = state.get("cycle_count", 0)
    new_observations: list[dict[str, Any]] = []

    # If goals exist, identify highest-priority goal
    if goals:
        # Priority enum ordering: HARD_STOP_SAFETY=8 highest, EXPLORE_RESEARCH=1 lowest
        # Since enum values are strings, we sort by their position in the enum
        priority_order = {
            Priority.HARD_STOP_SAFETY: 8,
            Priority.KEEP_ALIVE: 7,
            Priority.PROTECT_SECRETS: 6,
            Priority.URGENT_DAILY: 5,
            Priority.ACTIVE_COMMITMENTS: 4,
            Priority.IMPROVE_AUTONOMY: 3,
            Priority.ENGINEERING: 2,
            Priority.EXPLORE_RESEARCH: 1,
        }

        # Sort goals by priority (highest first)
        sorted_goals = sorted(
            goals,
            key=lambda g: priority_order.get(g.get("priority", Priority.IMPROVE_AUTONOMY), 6),
            reverse=True,
        )

        highest_priority_goal = sorted_goals[0]
        logger.info(
            "act_node_selected_goal",
            goal_id=highest_priority_goal.get("goal_id"),
            priority=highest_priority_goal.get("priority"),
            description=highest_priority_goal.get("description"),
        )

        # Log action intent
        logger.info(
            "life_kernel.act",
            phase=state.get("current_phase"),
            goal_id=highest_priority_goal.get("goal_id"),
            priority=highest_priority_goal.get("priority"),
            description=highest_priority_goal.get("description"),
        )
    else:
        # No active goals — idle cycle
        logger.info(
            "act_node_no_goals",
            phase=state.get("current_phase"),
            reason="no active goals — idle cycle",
        )
        # Append idle observation
        observation: dict[str, Any] = {
            "phase": "idle",
            "timestamp": datetime.now().isoformat(),
            "reason": "no active goals — idle cycle",
        }
        new_observations = [observation]

    # Increment counters
    act_count += 1
    cycle_count += 1

    logger.debug(
        "act_node_complete",
        act_count=act_count,
        cycle_count=cycle_count,
    )

    return {"act_count": act_count, "cycle_count": cycle_count, "observations": new_observations}


async def reflect_node(state: LifeMindState) -> dict[str, Any]:
    """Perform self-reflection and audit of kernel execution.

    Reads act_count, cycle_count, and errors from state. Creates audit entry
    with phase, timestamp, cycle count, act count, and error status.
    Detects anomalies (errors list non-empty, act_count grows without reflection).
    Generates memory placeholder for LK-010 integration. If hard_stop_requested,
    sets decision="end". Otherwise, sets decision="observe" to cycle continues.
    If errors exist, increments cycle_count and logs structured error summary.

    Args:
        state: Current kernel state.

    Returns:
        Dict with audit_entries, decision, and optional cycle_count increment.
    """
    logger.info(
        "reflect_node_entry",
        current_phase=state.get("current_phase"),
        act_count=state.get("act_count", 0),
        cycle_count=state.get("cycle_count", 0),
        audit_count=len(state.get("audit_entries", [])),
        errors_count=len(state.get("errors", [])),
    )

    # Read state fields
    act_count = state.get("act_count", 0)
    cycle_count = state.get("cycle_count", 0)
    observations = state.get("observations", [])
    errors = state.get("errors", [])
    hard_stop_requested = state.get("hard_stop_requested", False)

    # Detect anomalies
    has_errors = len(errors) > 0
    if has_errors:
        logger.warning(
            "reflect_node_anomalies_detected",
            error_count=len(errors),
            recent_errors=errors[-3:],  # Log last 3 errors
        )

    # Create audit entry
    audit_entry: dict[str, Any] = {
        "phase": "reflect",
        "timestamp": datetime.now().isoformat(),
        "cycle": cycle_count,
        "act_count": act_count,
        "n_observations": len(observations),
        "has_errors": has_errors,
        "is_active": state.get("is_active", False),
    }

    # Append audit entry (using reducer)
    audit_entries = [audit_entry]

    # AC-LIFE-008: write a reflective journal entry after a meaningful cycle.
    # A cycle is "meaningful" if a self-directed task was created (idle ran)
    # or an action was taken (act_count advanced) or recall surfaced context.
    # Fail-soft: journal failure never crashes the kernel.
    journal_update: dict[str, Any] = {}
    journal_writer = _ADAPTERS.get("journal")
    last_decision = state.get("last_autonomous_decision", "")
    next_action = state.get("next_planned_action", "")
    # A cycle is "meaningful" if the brain produced a decision/next-action or
    # recall surfaced context. We intentionally do NOT gate on `act_count`
    # here: it is read from state before this cycle's act_node reducer merges,
    # so it is stale on the first post-boot cycle. The decision/next-action
    # and recall fields are set by observe/decide/act/idle within this cycle
    # and are reliable signals.
    meaningful = (
        bool(last_decision)
        or bool(next_action)
        or bool(state.get("recalled_memories"))
        or bool(state.get("recalled_concepts"))
    )
    if journal_writer is not None and meaningful and not hard_stop_requested:
        reasoning = (
            f"Cycle {cycle_count}: {last_decision or 'idle cycle'}. "
            f"Next: {next_action or 'n/a'}."
        )
        lessons = (
            f"Recalled {len(state.get('recalled_memories', []))} memories, "
            f"{len(state.get('recalled_concepts', []))} KG concepts. "
            f"Errors: {len(errors)}."
        )
        try:
            entry = await journal_writer.write_entry(
                state=state,
                reasoning=reasoning,
                lessons_learned=lessons,
                confidence=0.7 if not has_errors else 0.4,
            )
            if entry:
                journal_update = {"journal_entries": [entry]}
                logger.info("reflect_journal_written", entry_id=entry.get("entry_id"))
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("reflect_journal_failed", error_type=type(exc).__name__)

    # Determine decision
    if hard_stop_requested:
        decision = "end"
        logger.info("reflect_node_hard_stop_routed_to_end")
    else:
        decision = "observe"
        logger.info("reflect_node_routed_to_observe")

    # If errors exist, increment cycle_count to prevent infinite loops
    if has_errors:
        cycle_count += 1
        logger.info(
            "reflect_node_error_handling",
            cycle_count_incremented=cycle_count,
        )

    logger.debug(
        "reflect_node_complete",
        audit_entry=audit_entry,
        decision=decision,
        cycle_count=cycle_count,
    )

    result: dict[str, Any] = {
        "audit_entries": audit_entries,
        "decision": decision,
        "cycle_count": cycle_count,
    }
    if journal_update:
        result.update(journal_update)
    return result


async def idle_node(state: LifeMindState) -> dict[str, Any]:
    """Create self-directed tasks when kernel has no work (AUTONOMY ENGINE).

    Generates exploration, self-improvement, and learning tasks when no goals
    or commitments exist. This is how the kernel stays alive when Faiz is silent
    (V-003 autonomy principle). Appends ONE task to observations list with
    phase, timestamp, task_type, and description. Sets decision="observe" to
    cycle back. Increments cycle_count.

    Args:
        state: Current kernel state.

    Returns:
        Dict with observations, decision, and cycle_count.
    """
    logger.info(
        "idle_node_entry",
        current_phase=state.get("current_phase"),
        is_active=state.get("is_active", False),
        goals_count=len(state.get("goals", [])),
        commitments_count=len(state.get("commitments", [])),
    )

    # Read state fields
    cycle_count = state.get("cycle_count", 0)
    observations = state.get("observations", [])

    # Memory-driven self-directed task (AC-LIFE-002 / V-003). Instead of
    # random.choice over hardcoded strings, derive the agenda item from the
    # recalled KG concepts + P18 memories populated by observe_node. When no
    # recall is available, fall back to a deterministic (non-random) default
    # so the kernel still stays alive without repeating the same stale string.
    recalled_concepts = state.get("recalled_concepts", []) or []
    recalled_memories = state.get("recalled_memories", []) or []

    if recalled_memories:
        top_memory = recalled_memories[0].get("content", "")[:120]
        task_type = "memory_driven"
        task_description = (
            f"Self-directed: follow up on recalled context — {top_memory}"
        )
    elif recalled_concepts:
        top_concept = recalled_concepts[0].get("name", "")
        task_type = "concept_driven"
        task_description = (
            f"Self-directed: explore knowledge-graph concept '{top_concept}' "
            "for actionable insight"
        )
    else:
        # Deterministic fallback (NOT random) when the world model is
        # unavailable. Rotates by cycle_count so consecutive idle cycles
        # vary without RNG.
        fallbacks = [
            ("self_improvement", "Self-directed: review recent autonomous decisions for improvement candidates"),
            ("exploration", "Self-directed: survey current world-state for emerging concerns"),
            ("learning", "Self-directed: consolidate a learning from the last reflection cycle"),
        ]
        task_type, task_description = fallbacks[cycle_count % len(fallbacks)]

    logger.info(
        "idle_node_generated_task",
        task_type=task_type,
        description=task_description,
    )

    # Append task to observations
    observation: dict[str, Any] = {
        "phase": "idle",
        "timestamp": datetime.now().isoformat(),
        "task_type": task_type,
        "description": task_description,
    }

    observations = [observation]

    # AC-LIFE-002: seed a REAL self-directed goal into state.goals so the
    # next decide_node has concrete work to act on (not just a display
    # label). The goal is memory/concept-driven. ``goals`` has no reducer,
    # so we return the full merged list (existing + new) to avoid clobbering.
    existing_goals = list(state.get("goals", []) or [])
    new_goal = {
        "goal_id": f"self-directed-{cycle_count}",
        "priority": Priority.IMPROVE_AUTONOMY,
        "description": task_description,
        "deadline": None,
        "status": "pending",
        "source": "idle_node",
    }
    # Only seed if there is no identical pending self-directed goal already
    # (prevents goal explosion across idle cycles).
    already_seeded = any(
        g.get("goal_id") == new_goal["goal_id"] or g.get("description") == task_description
        for g in existing_goals
    )
    if not already_seeded:
        existing_goals.append(new_goal)

    # Set decision to observe to cycle back
    decision = "observe"

    # Increment cycle_count
    cycle_count += 1

    logger.debug(
        "idle_node_complete",
        task_type=task_type,
        description=task_description,
        decision=decision,
        cycle_count=cycle_count,
        goals_count=len(existing_goals),
    )

    return {
        "observations": observations,
        "decision": decision,
        "cycle_count": cycle_count,
        "goals": existing_goals,
        "current_focus": task_description[:80],
        "next_planned_action": task_description[:200],
        "last_autonomous_decision": "self-directed task (memory-driven)",
    }


def _normalize_decision(raw: str) -> str:
    """Map a HermesBrain decision token onto a valid graph decision.

    The brain is asked to return exactly one of ``act/reflect/idle/observe``.
    We lowercase, take the first word, and validate; anything unexpected
    (including the empty fallback string) returns "" so the caller falls back
    to the static priority engine. We intentionally never map a brain token
    to ``"end"`` — HARD STOP routing to END is reserved for the non-LLM safety
    path in ``decide_node`` and can never be reached via the brain.
    """
    if not raw:
        return ""
    token = raw.strip().lower().split()[0] if raw.strip() else ""
    # Strip trailing punctuation the model might add.
    token = token.strip(".,:;")
    if token in _VALID_DECISIONS and token != "end":
        return token
    return ""


def _make_brain_decide(hermes_brain: Any) -> Any:
    """Build an LLM-enriched decide node that wraps the static decide_node.

    Safety ordering is preserved: the static decide_node runs first (it owns
    the HARD STOP check and the priority engine), and only when it would
    otherwise route to ``idle`` (no goals/commitments/concerns, kernel active)
    do we consult the brain for a possibly smarter choice. If the brain is
    unavailable, times out, or returns nonsense, the static ``idle`` decision
    stands — the kernel never stalls and never bypasses safety.
    """

    async def brain_decide(state: LifeMindState) -> dict[str, Any]:
        result = await decide_node(state)
        # Only augment the "idle" branch — the static engine is authoritative
        # for HARD STOP and any concrete work (act/reflect).
        if result.get("decision") != "idle":
            return result
        goals = state.get("goals", [])
        commitments = state.get("commitments", [])
        concerns = state.get("concerns", [])
        # Feed recalled memory/KG context into the decide prompt (AC-LIFE-005)
        # so the brain's routing is memory-informed, not blind to world-state.
        recalled_concepts = state.get("recalled_concepts", []) or []
        recalled_memories = state.get("recalled_memories", []) or []
        user_msg = (
            f"Goals: {goals}. Commitments: {commitments}. Concerns: {concerns}. "
            f"Observations: {len(state.get('observations', []))}. "
            f"Recalled KG concepts: {[c.get('name') for c in recalled_concepts[:5]]}. "
            f"Recalled memories: {[m.get('content', '')[:60] for m in recalled_memories[:5]]}. "
            f"Cycle: {state.get('cycle_count', 0)}. "
            "Decide the next phase: act, reflect, idle, or observe."
        )
        raw = await _safe_think(hermes_brain, user_msg, _DECIDE_SYSTEM_PROMPT)
        brain_decision = _normalize_decision(raw)
        if brain_decision and brain_decision != "idle":
            logger.info("decide_brain_override", brain_decision=brain_decision)
            result["decision"] = brain_decision
        result["last_autonomous_decision"] = brain_decision or "idle"
        return result

    return brain_decide


def _make_brain_act(hermes_brain: Any) -> Any:
    """Build an LLM-enriched act node: static selection + brain-proposed plan.

    The static act_node selects the highest-priority goal and increments
    counters (authoritative). We then ask the brain to *propose* a concrete
    next action for that goal — display-only metadata stored on the state for
    the dashboard. The brain never executes side effects.
    """

    async def brain_act(state: LifeMindState) -> dict[str, Any]:
        result = await act_node(state)
        goals = state.get("goals", [])
        if not goals:
            result.setdefault("last_action_result", "no active goals — idle cycle")
            result.setdefault("next_planned_action", "await self-directed task")
            return result
        priority_order = {
            Priority.HARD_STOP_SAFETY: 8, Priority.KEEP_ALIVE: 7,
            Priority.PROTECT_SECRETS: 6, Priority.URGENT_DAILY: 5,
            Priority.ACTIVE_COMMITMENTS: 4, Priority.IMPROVE_AUTONOMY: 3,
            Priority.ENGINEERING: 2, Priority.EXPLORE_RESEARCH: 1,
        }
        top = sorted(
            goals,
            key=lambda g: priority_order.get(g.get("priority", Priority.IMPROVE_AUTONOMY), 6),
            reverse=True,
        )[0]
        user_msg = (
            f"Goal: {top.get('description', '?')} (priority={top.get('priority')}). "
            "Propose ONE concrete next action in a single short sentence."
        )
        proposal = await _safe_think(hermes_brain, user_msg, _ACT_SYSTEM_PROMPT)
        result["last_autonomous_decision"] = f"act on: {top.get('description', '?')}"
        result["last_action_result"] = "planned (display-only)"
        result["next_planned_action"] = proposal or "static: execute highest-priority goal"
        return result

    return brain_act


def _make_brain_idle(hermes_brain: Any) -> Any:
    """Build an LLM-enriched idle node for proactive self-directed tasks.

    When Faiz is silent and there is no pending work, the brain generates a
    self-directed agenda item (display-only). This is the proactive-autonomy
    engine (requirement #4): the kernel stays visibly alive with its own
    agenda instead of idling silently. If the brain is unavailable, the
    static idle_node's random task selection stands.
    """

    async def brain_idle(state: LifeMindState) -> dict[str, Any]:
        result = await idle_node(state)
        # Feed the recalled KG concepts + P18 memories into the brain prompt
        # so the self-directed agenda is memory-driven (AC-LIFE-005), not a
        # generic filler question.
        recalled_concepts = state.get("recalled_concepts", []) or []
        recalled_memories = state.get("recalled_memories", []) or []
        concept_names = [c.get("name", "") for c in recalled_concepts[:5]]
        memory_summaries = [m.get("content", "")[:80] for m in recalled_memories[:5]]
        user_msg = (
            "The operator is silent and there is no pending work. "
            f"Recent KG concepts: {concept_names}. "
            f"Recent memories: {memory_summaries}. "
            "Propose ONE self-directed agenda item grounded in this recalled "
            "context to stay usefully alive. Reply with a short label and a "
            "one-sentence description."
        )
        proposal = await _safe_think(hermes_brain, user_msg, _IDLE_SYSTEM_PROMPT)
        if proposal:
            # The brain's proposal becomes the description of the seeded goal
            # (already created by idle_node) — update it so the goal is
            # brain-grounded rather than the static memory-string.
            result["last_autonomous_decision"] = "self-directed task (brain-grounded)"
            result["next_planned_action"] = proposal[:200]
            observations = result.get("observations", [])
            if observations:
                observations[0] = {
                    **observations[0],
                    "description": proposal[:200],
                    "brain_generated": True,
                }
            # Update the seeded goal description to the brain proposal.
            goals = result.get("goals", [])
            if goals:
                goals[-1] = {**goals[-1], "description": proposal[:200], "brain_generated": True}
                result["goals"] = goals
            result["current_focus"] = proposal[:80]
        return result

    return brain_idle


def create_life_mind_graph(
    checkpointer: Any | None = None,
    hermes_brain: Any | None = None,
    kg_adapter: Any | None = None,
    memory_adapter: Any | None = None,
    journal_writer: Any | None = None,
) -> Any:
    """Create the LangGraph StateGraph for the autonomous kernel.

    Builds a 4-node cyclic graph: observe → decide → act/reflect/idle → END,
    re-invoked every 60s by the heartbeat. Supports optional checkpointing
    via LangGraph and optional LLM-driven autonomy via ``hermes_brain``.

    When ``hermes_brain`` is provided, decide/act/idle nodes are wrapped in
    LLM-enriched variants that call ``hermes_brain.think()`` (never raw
    ``LLMRouter.chat``) with a hard timeout and a fail-safe fallback to the
    static logic. The HARD STOP safety path remains a non-LLM override and is
    always checked first. When ``hermes_brain`` is ``None`` (tests, or when
    the brain failed to initialize), the original static nodes are used
    unchanged.

    When ``kg_adapter`` / ``memory_adapter`` are provided, observe_node
    calls the real P16/P18 recall substrates and populates
    ``recalled_concepts`` / ``recalled_memories`` / ``world_model_status``
    (LK-010 / AC-LIFE-005). Adapters are registered in a module-level
    registry (not state) because LangGraph checkpoints state as JSON and
    cannot hold live adapter objects.

    Args:
        checkpointer: Optional LangGraph checkpointer for persistence.
        hermes_brain: Optional ``HermesBrain`` instance for LLM-driven
            autonomy. May be ``None``.
        kg_adapter: Optional real KGRecallAdapter for P16 KG recall.
        memory_adapter: Optional real MemoryRecallAdapter for P18 recall.
        journal_writer: Optional JournalWriter for persistent journal entries.

    Returns:
        Compiled LangGraph StateGraph with checkpointing support.
    """
    logger.info(
        "create_life_mind_graph",
        checkpointer=checkpointer is not None,
        hermes_brain=hermes_brain is not None,
        kg_adapter=kg_adapter is not None,
        memory_adapter=memory_adapter is not None,
        journal_writer=journal_writer is not None,
    )

    # Register real adapters so the module-level node functions can use them.
    set_adapters(
        kg_adapter=kg_adapter,
        memory_adapter=memory_adapter,
        journal_writer=journal_writer,
    )

    from langgraph.graph import StateGraph, START, END

    # Build StateGraph with LifeMindState
    builder = StateGraph(LifeMindState)

    # Choose LLM-enriched nodes when a brain is available; otherwise the
    # static nodes (which are also the unit-test surface).
    if hermes_brain is not None:
        decide_fn = _make_brain_decide(hermes_brain)
        act_fn = _make_brain_act(hermes_brain)
        idle_fn = _make_brain_idle(hermes_brain)
    else:
        decide_fn = decide_node
        act_fn = act_node
        idle_fn = idle_node

    # Add nodes
    builder.add_node("observe", observe_node)
    builder.add_node("decide", decide_fn)
    builder.add_node("act", act_fn)
    builder.add_node("reflect", reflect_node)
    builder.add_node("idle", idle_fn)

    # Add edges from START
    builder.add_edge(START, "observe")

    # Add edges from observe
    builder.add_edge("observe", "decide")

# Add conditional edge from decide
    def route_from_decide(state: LifeMindState) -> str:
        """Route from decide based on decision field.

        Reads the "decision" field from state and returns the appropriate next node
        or END for hard_stop.

        Args:
            state: Current kernel state.

        Returns:
            Next node name or END constant.
        """
        decision = state.get("decision")
        if decision == "hard_stop":
            logger.info("hard_stop decision - routing to END")
            return END
        elif decision == "idle":
            logger.info("idle decision - routing to idle node")
            return "idle"
        elif decision == "act":
            logger.info("act decision - routing to act")
            return "act"
        elif decision == "reflect":
            logger.info("reflect decision - routing to reflect")
            return "reflect"
        else:
            # Default: route to END if decision is missing or unknown
            logger.warning("unknown decision - defaulting to END")
            return END

    builder.add_conditional_edges(
        "decide",
        route_from_decide,
        {
            "act": "act",
            "reflect": "reflect",
            "idle": "idle",
            END: END,
        },
    )

    # Add edge from act to reflect (action triggers reflection)
    builder.add_edge("act", "reflect")

    # Each invocation completes one cycle (observe → decide → act/reflect/idle).
    # The heartbeat re-invokes every 60s for the next cycle.
    # State persists via checkpointer between invocations.
    builder.add_edge("reflect", END)
    builder.add_edge("idle", END)

    # Compile with optional checkpointer
    if checkpointer is not None:
        logger.info("compiling graph with checkpointer")
        graph = builder.compile(checkpointer=checkpointer)
    else:
        logger.info("compiling graph without checkpointer")
        graph = builder.compile()

    logger.info("life_mind_graph_created", node_count=len(graph.nodes))

    return graph

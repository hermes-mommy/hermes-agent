"""Phase registry — maps LoopPhase to handler classes and legacy run functions.

Provides two access patterns:

1. **Class-based (new)**: ``HANDLER_CLASSES`` maps each phase to its handler
   class. Use ``create_phase_handler(phase, llm_router, cost_tracker)`` to
   instantiate with LLM injection for real autonomous execution.

2. **Function-based (legacy)**: ``PHASE_REGISTRY`` maps each phase to a
   backward-compatible ``run()`` function that creates a handler without
   LLM router (fallback template mode). Used by the current ``LoopManager``.

Exactly 7 entries (one per SDLC phase, excluding the COMPLETE terminal).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from guinvere.loops.state_machine import LoopPhase

from guinvere.loops.phases.base import PhaseArtifact, TokenUsage, BasePhaseHandler

# ── Handler class imports (new pattern) ──────────────────────────────
from guinvere.loops.phases.research import ResearchHandler
from guinvere.loops.phases.plan_delegate import PlanDelegateHandler
from guinvere.loops.phases.delegate import DelegateHandler
from guinvere.loops.phases.execute import ExecuteHandler
from guinvere.loops.phases.validate_audit import ValidateAuditHandler
from guinvere.loops.phases.update_docs import UpdateDocsHandler
from guinvere.loops.phases.setup_evidence import SetupEvidenceHandler

# ── Legacy run function imports (backward compat) ────────────────────
from guinvere.loops.phases.research import run as research_run
from guinvere.loops.phases.plan_delegate import run as plan_delegate_run
from guinvere.loops.phases.delegate import run as delegate_run
from guinvere.loops.phases.execute import run as execute_run
from guinvere.loops.phases.validate_audit import run as validate_audit_run
from guinvere.loops.phases.update_docs import run as update_docs_run
from guinvere.loops.phases.setup_evidence import run as setup_evidence_run

logger = structlog.get_logger()

# ── Class-based registry (new pattern) ───────────────────────────────
HANDLER_CLASSES: dict[LoopPhase, type[BasePhaseHandler]] = {
    LoopPhase.RESEARCH: ResearchHandler,
    LoopPhase.PLAN_AND_DELEGATE: PlanDelegateHandler,
    LoopPhase.DELEGATE: DelegateHandler,
    LoopPhase.EXECUTE: ExecuteHandler,
    LoopPhase.VALIDATE_AND_AUDIT: ValidateAuditHandler,
    LoopPhase.UPDATE_DOCUMENTS: UpdateDocsHandler,
    LoopPhase.SETUP_EVIDENCE: SetupEvidenceHandler,
}


def create_phase_handler(
    phase: LoopPhase,
    llm_router: Any | None = None,
    cost_tracker: Any | None = None,
) -> BasePhaseHandler:
    """Instantiate a handler class for *phase* with optional LLM injection.

    Args:
        phase: The SDLC phase to create a handler for.
        llm_router: Optional LLMRouter instance for real LLM-powered execution.
            If None, the handler falls back to static template mode.
        cost_tracker: Optional LoopCostTracker for cost attribution.

    Returns:
        An instantiated handler ready to call ``.execute(loop_id, task, goal)``.

    Raises:
        KeyError: If *phase* has no registered handler (e.g. COMPLETE).
    """
    if phase not in HANDLER_CLASSES:
        raise KeyError(
            f"No handler class registered for phase {phase.name} "
            f"(value={phase.value}). "
            f"Registered phases: {', '.join(p.name for p in HANDLER_CLASSES)}"
        )
    handler_cls = HANDLER_CLASSES[phase]
    return handler_cls(llm_router=llm_router, cost_tracker=cost_tracker)


# ── Legacy function-based registry (backward compat) ─────────────────
PHASE_REGISTRY: dict[LoopPhase, Callable[..., Awaitable[str]]] = {
    LoopPhase.RESEARCH: research_run,
    LoopPhase.PLAN_AND_DELEGATE: plan_delegate_run,
    LoopPhase.DELEGATE: delegate_run,
    LoopPhase.EXECUTE: execute_run,
    LoopPhase.VALIDATE_AND_AUDIT: validate_audit_run,
    LoopPhase.UPDATE_DOCUMENTS: update_docs_run,
    LoopPhase.SETUP_EVIDENCE: setup_evidence_run,
}


def get_phase_handler(phase: LoopPhase) -> Callable[..., Awaitable[str]]:
    """Return the legacy async run function for *phase*.

    This is the backward-compatible accessor used by the current
    ``LoopManager``. For LLM-powered execution, use
    :func:`create_phase_handler` instead.

    Raises:
        KeyError: If *phase* has no registered handler (e.g. COMPLETE).
    """
    if phase not in PHASE_REGISTRY:
        raise KeyError(
            f"No handler registered for phase {phase.name} (value={phase.value}). "
            f"Registered phases: {', '.join(p.name for p in PHASE_REGISTRY)}"
        )
    return PHASE_REGISTRY[phase]


__all__ = [
    "HANDLER_CLASSES",
    "create_phase_handler",
    "PHASE_REGISTRY",
    "get_phase_handler",
    "PhaseArtifact",
    "TokenUsage",
    "BasePhaseHandler",
    "ResearchHandler",
    "PlanDelegateHandler",
    "DelegateHandler",
    "ExecuteHandler",
    "ValidateAuditHandler",
    "UpdateDocsHandler",
    "SetupEvidenceHandler",
]

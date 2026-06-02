"""Phase registry — maps LoopPhase to its async handler function.

Exactly 7 entries (one per SDLC phase, excluding the COMPLETE terminal).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from src.loops.state_machine import LoopPhase

from src.loops.phases.research import run as research_run
from src.loops.phases.plan_delegate import run as plan_delegate_run
from src.loops.phases.delegate import run as delegate_run
from src.loops.phases.execute import run as execute_run
from src.loops.phases.validate_audit import run as validate_audit_run
from src.loops.phases.update_docs import run as update_docs_run
from src.loops.phases.setup_evidence import run as setup_evidence_run

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
    """Return the async handler for *phase*.

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
    "PHASE_REGISTRY",
    "get_phase_handler",
]

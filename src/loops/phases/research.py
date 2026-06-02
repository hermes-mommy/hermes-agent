"""Phase 1 — Research: gather context, dependencies, and risks.

Produces a ``research-report.md`` artifact with placeholder template
sections.  Real LLM-powered research will be injected in a later wave.
"""

from __future__ import annotations

import structlog

from src.loops.state_machine import LoopPhase

logger = structlog.get_logger()

_PHASE = LoopPhase.RESEARCH
_PHASE_NAME = "Research"


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Execute the Research phase and return markdown artifact content.

    The caller is responsible for persisting the returned string via
    :func:`src.loops.artifacts.write_artifact`.
    """
    logger.info(
        "phase.research.start",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        task=task,
        goal=goal,
    )

    goal_section = f"\n**Goal:** {goal}\n" if goal else ""

    artifact = f"""\
# Research Report

**Loop:** `{loop_id}`
**Phase:** {_PHASE_NAME} (Phase {_PHASE.value})
**Task:** {task}
{goal_section}
---

## Objective

<!-- Summarise what this loop aims to achieve and the scope of research. -->

_{task}_

## Findings

<!-- Key discoveries from codebase exploration, documentation review, and external research. -->

- *No findings recorded yet — placeholder for LLM-powered research.*

## Dependencies

<!-- Libraries, services, modules, or external systems this task depends on. -->

| Dependency | Type | Status |
|---|---|---|
| *pending* | — | — |

## Risks

<!-- Identified risks, unknowns, or blockers. -->

- *No risks identified yet.*

## Recommendations

<!-- Actionable recommendations based on research findings. -->

1. *Pending research completion.*
"""

    logger.info(
        "phase.research.complete",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        artifact_length=len(artifact),
    )

    return artifact

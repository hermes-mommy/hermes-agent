"""Phase 2 — Plan & Delegate: decompose the task and assign sub-agents.

Produces a ``plan.md`` artifact with task breakdown, sub-agent
assignment, dependency map, and parallelism plan.
"""

from __future__ import annotations

import structlog

from src.loops.state_machine import LoopPhase

logger = structlog.get_logger()

_PHASE = LoopPhase.PLAN_AND_DELEGATE
_PHASE_NAME = "Plan & Delegate"


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Execute the Plan & Delegate phase and return markdown artifact content.

    The caller is responsible for persisting the returned string via
    :func:`src.loops.artifacts.write_artifact`.
    """
    logger.info(
        "phase.plan_delegate.start",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        task=task,
        goal=goal,
    )

    goal_section = f"\n**Goal:** {goal}\n" if goal else ""

    artifact = f"""\
# Plan

**Loop:** `{loop_id}`
**Phase:** {_PHASE_NAME} (Phase {_PHASE.value})
**Task:** {task}
{goal_section}
---

## Task Breakdown

<!-- Atomic sub-steps derived from the parent task. -->

| # | Sub-Step | Description | Est. Complexity |
|---|---|---|---|
| 1 | *pending* | — | — |

## Sub-Agent Assignment

<!-- Pasukan Mommy assignments: which sub-agent handles which sub-step. -->

| Sub-Agent | Sub-Step | Skills Loaded | Priority |
|---|---|---|---|
| *pending* | — | — | — |

## Dependency Map

<!-- Directed acyclic graph of sub-step dependencies. -->

```
(sub-step dependency graph placeholder)
```

## Parallelism Plan

<!-- Which sub-steps can execute concurrently vs. sequentially. -->

- **Parallel:** *none determined yet*
- **Sequential:** *all sub-steps default to sequential until planner confirms independence*
"""

    logger.info(
        "phase.plan_delegate.complete",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        artifact_length=len(artifact),
    )

    return artifact

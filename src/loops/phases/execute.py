"""Phase 4 — Execute: sub-agents carry out their assigned work.

Produces an ``execution-log.md`` artifact capturing results, changed
files, test outcomes, and any errors encountered.
"""

from __future__ import annotations

import structlog

from src.loops.state_machine import LoopPhase

logger = structlog.get_logger()

_PHASE = LoopPhase.EXECUTE
_PHASE_NAME = "Execute"


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Execute the Execute phase and return markdown artifact content.

    The caller is responsible for persisting the returned string via
    :func:`src.loops.artifacts.write_artifact`.
    """
    logger.info(
        "phase.execute.start",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        task=task,
        goal=goal,
    )

    goal_section = f"\n**Goal:** {goal}\n" if goal else ""

    artifact = f"""\
# Execution Log

**Loop:** `{loop_id}`
**Phase:** {_PHASE_NAME} (Phase {_PHASE.value})
**Task:** {task}
{goal_section}
---

## Execution Results

<!-- Outcomes from each sub-agent's work. -->

| Sub-Agent | Sub-Step | Result | Duration |
|---|---|---|---|
| *pending* | — | — | — |

## Files Changed

<!-- Files created, modified, or deleted during execution. -->

| File Path | Action | Lines Changed |
|---|---|---|
| *pending* | — | — |

## Test Results

<!-- Automated test outcomes (unit, integration, lint). -->

| Test Suite | Passed | Failed | Skipped | Exit Code |
|---|---|---|---|---|
| *pending* | — | — | — | — |

## Errors Encountered

<!-- Errors, warnings, or blockers surfaced during execution. -->

- *No errors recorded yet.*
"""

    logger.info(
        "phase.execute.complete",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        artifact_length=len(artifact),
    )

    return artifact

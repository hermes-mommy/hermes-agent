"""Phase 3 — Delegate: spawn Pasukan Mommy sub-agents with task contracts.

Produces a ``delegation-manifest.md`` artifact listing every spawned
sub-agent, their task contracts, and expected outputs.
"""

from __future__ import annotations

import structlog

from src.loops.state_machine import LoopPhase

logger = structlog.get_logger()

_PHASE = LoopPhase.DELEGATE
_PHASE_NAME = "Delegate"


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Execute the Delegate phase and return markdown artifact content.

    The caller is responsible for persisting the returned string via
    :func:`src.loops.artifacts.write_artifact`.
    """
    logger.info(
        "phase.delegate.start",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        task=task,
        goal=goal,
    )

    goal_section = f"\n**Goal:** {goal}\n" if goal else ""

    artifact = f"""\
# Delegation Manifest

**Loop:** `{loop_id}`
**Phase:** {_PHASE_NAME} (Phase {_PHASE.value})
**Task:** {task}
{goal_section}
---

## Sub-Agents Spawned

<!-- Pasukan Mommy (Mommy's troops) dispatched for this loop. -->

| # | Sub-Agent ID | Type | Status | Assigned Sub-Step |
|---|---|---|---|---|
| 1 | *pending* | — | — | — |

## Task Contracts

<!-- Explicit contracts: TASK, EXPECTED OUTCOME, MUST DO, MUST NOT DO, CONTEXT. -->

### Sub-Agent 1 — *pending*

- **TASK:** —
- **EXPECTED OUTCOME:** —
- **REQUIRED TOOLS:** —
- **MUST DO:** —
- **MUST NOT DO:** —
- **CONTEXT:** —

## Expected Outputs

<!-- File paths, artifacts, or structured reports each sub-agent must produce. -->

| Sub-Agent | Output Path | Format | Required |
|---|---|---|---|
| *pending* | — | — | — |
"""

    logger.info(
        "phase.delegate.complete",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        artifact_length=len(artifact),
    )

    return artifact

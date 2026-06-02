"""Phase 7 — Setup Evidence: compile the complete evidence package.

Produces an ``evidence-final.md`` artifact aggregating all phase
artifacts, validation results, and acceptance criteria mapping.
"""

from __future__ import annotations

import structlog

from src.loops.state_machine import LoopPhase

logger = structlog.get_logger()

_PHASE = LoopPhase.SETUP_EVIDENCE
_PHASE_NAME = "Setup Evidence"


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Execute the Setup Evidence phase and return markdown artifact content.

    The caller is responsible for persisting the returned string via
    :func:`src.loops.artifacts.write_artifact`.
    """
    logger.info(
        "phase.setup_evidence.start",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        task=task,
        goal=goal,
    )

    goal_section = f"\n**Goal:** {goal}\n" if goal else ""

    artifact = f"""\
# Evidence Package — Final

**Loop:** `{loop_id}`
**Phase:** {_PHASE_NAME} (Phase {_PHASE.value})
**Task:** {task}
{goal_section}
---

## What Was Done

<!-- Summary of all work completed across all phases. -->

- *Pending compilation from phase artifacts.*

## Files Changed

<!-- Consolidated list of all files created, modified, or deleted. -->

| File Path | Action | Phase |
|---|---|---|
| *pending* | — | — |

## Validation Results

<!-- Aggregated verification and audit outcomes. -->

| Check | Verdict | Source Phase |
|---|---|---|
| LSP diagnostics | *pending* | Validate & Audit |
| Tests pass | *pending* | Validate & Audit |
| Auditor gate | *pending* | Validate & Audit |
| Safety boundaries | *pending* | Validate & Audit |

## Evidence Artifacts

<!-- List of all artifacts produced during this loop. -->

| Phase | Artifact | Path |
|---|---|---|
| Research | `research-report.md` | *pending* |
| Plan & Delegate | `plan.md` | *pending* |
| Delegate | `delegation-manifest.md` | *pending* |
| Execute | `execution-log.md` | *pending* |
| Validate & Audit | `validation-report.md` | *pending* |
| Update Documents | `doc-sync-report.md` | *pending* |
| Setup Evidence | `evidence-final.md` | *this file* |

## Acceptance Criteria

<!-- Mapping of task acceptance criteria to evidence. -->

| Criterion | Met | Evidence |
|---|---|---|
| *pending* | — | — |
"""

    logger.info(
        "phase.setup_evidence.complete",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        artifact_length=len(artifact),
    )

    return artifact

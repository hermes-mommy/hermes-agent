"""Phase 5 — Validate & Audit: parent verification and independent auditor gate.

Produces a ``validation-report.md`` artifact with verification results,
diagnostics, test outcomes, and auditor gate status.
"""

from __future__ import annotations

import structlog

from src.loops.state_machine import LoopPhase

logger = structlog.get_logger()

_PHASE = LoopPhase.VALIDATE_AND_AUDIT
_PHASE_NAME = "Validate & Audit"


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Execute the Validate & Audit phase and return markdown artifact content.

    The caller is responsible for persisting the returned string via
    :func:`src.loops.artifacts.write_artifact`.
    """
    logger.info(
        "phase.validate_audit.start",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        task=task,
        goal=goal,
    )

    goal_section = f"\n**Goal:** {goal}\n" if goal else ""

    artifact = f"""\
# Validation Report

**Loop:** `{loop_id}`
**Phase:** {_PHASE_NAME} (Phase {_PHASE.value})
**Task:** {task}
{goal_section}
---

## Parent Verification

<!-- Parent agent verification checklist. -->

| Check | Status | Notes |
|---|---|---|
| Claimed files exist | *pending* | — |
| LSP diagnostics clean | *pending* | — |
| Tests pass | *pending* | — |
| DoD satisfied | *pending* | — |
| Evidence paths valid | *pending* | — |
| Safety boundaries preserved | *pending* | — |

## Diagnostics

<!-- LSP / type-checker / linter output summary. -->

```
(pending diagnostic output)
```

## Test Results

<!-- Deterministic verification command results. -->

| Command | Exit Code | Output Summary |
|---|---|---|
| *pending* | — | — |

## Auditor Gate

<!-- Independent auditor findings and verdict. -->

| Auditor | Verdict | Findings |
|---|---|---|
| *pending* | — | — |

**Overall Verdict:** *PENDING*
"""

    logger.info(
        "phase.validate_audit.complete",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        artifact_length=len(artifact),
    )

    return artifact

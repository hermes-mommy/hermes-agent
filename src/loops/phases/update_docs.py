"""Phase 6 — Update Documents: synchronise documentation and cross-references.

Produces a ``doc-sync-report.md`` artifact listing documentation
changes, cross-reference updates, and index modifications.
"""

from __future__ import annotations

import structlog

from src.loops.state_machine import LoopPhase

logger = structlog.get_logger()

_PHASE = LoopPhase.UPDATE_DOCUMENTS
_PHASE_NAME = "Update Documents"


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Execute the Update Documents phase and return markdown artifact content.

    The caller is responsible for persisting the returned string via
    :func:`src.loops.artifacts.write_artifact`.
    """
    logger.info(
        "phase.update_docs.start",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        task=task,
        goal=goal,
    )

    goal_section = f"\n**Goal:** {goal}\n" if goal else ""

    artifact = f"""\
# Doc-Sync Report

**Loop:** `{loop_id}`
**Phase:** {_PHASE_NAME} (Phase {_PHASE.value})
**Task:** {task}
{goal_section}
---

## Docs Updated

<!-- Documentation files created or modified during this loop. -->

| Document | Action | Section | Summary |
|---|---|---|---|
| *pending* | — | — | — |

## Cross-References

<!-- Cross-reference links that were added, updated, or verified. -->

| Source Doc | Target Doc | Link Type | Status |
|---|---|---|---|
| *pending* | — | — | — |

## Index Updates

<!-- Master index files (docs/README.md, ADR-Index, evidence indexes) updated. -->

| Index File | Entries Added | Entries Modified | Status |
|---|---|---|---|
| *pending* | — | — | — |
"""

    logger.info(
        "phase.update_docs.complete",
        loop_id=loop_id,
        phase=_PHASE_NAME,
        artifact_length=len(artifact),
    )

    return artifact

"""Phase 7 — Setup Evidence: compile the complete evidence package.

Produces an ``evidence-final.md`` artifact aggregating all phase
artifacts, validation results, and acceptance criteria mapping.

Extends :class:`BasePhaseHandler` with LLM-powered evidence
compilation using the :class:`SystemPromptBuilder` for prompt
construction and the injected ``LLMRouter`` for the actual call.

When no LLM router is available (fallback mode), returns the original
static template as a graceful degradation path.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from guinvere.loops.phases.base import BasePhaseHandler, PhaseArtifact, TokenUsage
from guinvere.loops.prompts import build_system_prompt, PHASE_NAMES
from guinvere.loops.context import LoopContext

logger = structlog.get_logger()

_PHASE = 7
_PHASE_NAME = PHASE_NAMES.get(_PHASE, "Setup Evidence")


class SetupEvidenceHandler(BasePhaseHandler):
    """Phase 7 handler — produces the per-task evidence artifact.

    Uses the LLM router (injected via the parent constructor) to
    produce a final evidence report covering:

    1. **What was done** — summary of all phases
    2. **Files changed** — consolidated list with paths and actions
    3. **Validation results** — LSP diagnostics, tests, auditor gate
    4. **Audit reports** — pass/fail per auditor with evidence links
    5. **Rollback plan** — how to revert if needed
    6. **Acceptance criteria mapping** — criterion-to-evidence trace
    7. **Security scan results** — secrets, type-safety, error handling
    8. **Design decisions and caveats** — context for future readers

    Falls back to a static template when ``self._llm_router`` is
    ``None`` (graceful degradation for setups without an LLM backend).
    """

    async def _execute(
        self,
        loop_id: str,
        task: str,
        goal: str,
    ) -> PhaseArtifact:
        """Execute the Setup Evidence phase.

        Args:
            loop_id: 12-character hex loop identifier.
            task: Human-readable task description.
            goal: Optional goal string.

        Returns:
            A :class:`PhaseArtifact` with the evidence-final report as
            markdown content, phase=7, and token usage metadata when
            an LLM call was made.
        """
        logger.info(
            "setup_evidence_handler.execute.start",
            loop_id=loop_id,
            task=task,
            has_goal=bool(goal),
        )

        # ── Fallback: no LLM router, return template ──────────────
        if self._llm_router is None:
            logger.warning(
                "setup_evidence_handler.no_llm_router",
                loop_id=loop_id,
                fallback="template",
            )
            content = self._build_fallback_artifact(loop_id, task, goal)
            return PhaseArtifact(
                content=content,
                phase=_PHASE,
                token_usage=None,
                metadata={"fallback": True},
            )

        # ── Build LoopContext for prompt builder ───────────────────
        ctx = LoopContext(
            loop_id=loop_id,
            task=task,
            goal=goal,
            phase=_PHASE,
            created_at=datetime.now(timezone.utc),
        )

        # ── Construct the 3-tier system prompt ─────────────────────
        system_prompt = build_system_prompt(ctx=ctx)

        # ── Build the user message ─────────────────────────────────
        goal_section = f"Goal: {goal}\n\n" if goal else ""
        user_msg = (
            "Produce the final evidence artifact for this loop. "
            "The evidence must be a complete, auditable record.\n\n"
            f"Task: {task}\n\n"
            f"{goal_section}"
            "Include the following sections:\n"
            "1. **What was done** — summary of all phases executed\n"
            "2. **Files changed** — consolidated table with file "
            "paths, action (created/modified/deleted), and owning "
            "phase\n"
            "3. **Validation results** — LSP diagnostics outcome, "
            "test suite results, auditor gate verdicts\n"
            "4. **Audit reports** — per-auditor pass/fail with "
            "evidence links and fix history\n"
            "5. **Rollback plan** — step-by-step instructions to "
            "revert the change\n"
            "6. **Acceptance criteria mapping** — table mapping "
            "each criterion to the evidence that proves it is met\n"
            "7. **Security scan results** — secrets scan, type-"
            "safety check, error-handling review\n"
            "8. **Design decisions and caveats** — rationale for "
            "technical choices and known limitations"
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]

        # ── Make the LLM call ────────────────────────────────────
        result = await self._call_llm(
            messages=messages,
            task_type="CORE_REASONING",
            max_tokens=4096,
            loop_id=loop_id,
        )

        # ── Extract token usage ──────────────────────────────────
        usage = result.get("usage", {})
        model = result.get("model", "unknown")
        token_usage = TokenUsage(
            model=model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            cost_usd=0.0,
        )

        # ── Format the LLM output into a structured artifact ──────
        raw_content = result.get("content", "")
        artifact_content = self._format_llm_output(
            content=raw_content,
            loop_id=loop_id,
            task=task,
            goal=goal,
        )

        logger.info(
            "setup_evidence_handler.execute.complete",
            loop_id=loop_id,
            model=model,
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
            total_tokens=token_usage.total_tokens,
        )

        return PhaseArtifact(
            content=artifact_content,
            phase=_PHASE,
            token_usage=token_usage,
            metadata={
                "llm_model": model,
                "has_goal": bool(goal),
            },
        )

    # ── Internal helpers ──────────────────────────────────────────

    @staticmethod
    def _build_fallback_artifact(
        loop_id: str,
        task: str,
        goal: str,
    ) -> str:
        """Build the static template artifact when no LLM is available."""
        goal_section = f"\n**Goal:** {goal}\n" if goal else ""

        return (
            f"# Evidence Package — Final\n\n"
            f"**Loop:** `{loop_id}`\n"
            f"**Phase:** {_PHASE_NAME} (Phase {_PHASE})\n"
            f"**Task:** {task}\n"
            f"{goal_section}"
            f"---\n\n"
            f"## What Was Done\n\n"
            f"- *Pending compilation from phase artifacts.*\n\n"
            f"## Files Changed\n\n"
            f"| File Path | Action | Phase |\n"
            f"|---|---|---|\n"
            f"| *pending* | — | — |\n\n"
            f"## Validation Results\n\n"
            f"| Check | Verdict | Source Phase |\n"
            f"|---|---|---|\n"
            f"| LSP diagnostics | *pending* | Validate & Audit |\n"
            f"| Tests pass | *pending* | Validate & Audit |\n"
            f"| Auditor gate | *pending* | Validate & Audit |\n"
            f"| Safety boundaries | *pending* | Validate & Audit |\n\n"
            f"## Evidence Artifacts\n\n"
            f"| Phase | Artifact | Path |\n"
            f"|---|---|---|\n"
            f"| Research | `research-report.md` | *pending* |\n"
            f"| Plan & Delegate | `plan.md` | *pending* |\n"
            f"| Delegate | `delegation-manifest.md` | *pending* |\n"
            f"| Execute | `execution-log.md` | *pending* |\n"
            f"| Validate & Audit | `validation-report.md` | *pending* |\n"
            f"| Update Documents | `doc-sync-report.md` | *pending* |\n"
            f"| Setup Evidence | `evidence-final.md` | *this file* |\n\n"
            f"## Acceptance Criteria\n\n"
            f"| Criterion | Met | Evidence |\n"
            f"|---|---|---|\n"
            f"| *pending* | — | — |\n"
        )

    @staticmethod
    def _format_llm_output(
        content: str,
        loop_id: str,
        task: str,
        goal: str,
    ) -> str:
        """Wrap raw LLM output in the structured evidence artifact.

        The LLM response is placed under an ``## LLM Response``
        section so the artifact remains self-contained markdown.
        This is the terminal phase — no downstream consumer parses
        the output programmatically, but the section structure
        aids human review.
        """
        goal_section = f"\n**Goal:** {goal}\n" if goal else ""

        return (
            f"# Evidence Package — Final\n\n"
            f"**Loop:** `{loop_id}`\n"
            f"**Phase:** {_PHASE_NAME} (Phase {_PHASE})\n"
            f"**Task:** {task}\n"
            f"{goal_section}"
            f"---\n\n"
            f"## LLM Response\n\n"
            f"{content}\n"
        )


# ── Backward-compatible entry point ─────────────────────────────────


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Backward-compatible entry point used by :data:`PHASE_REGISTRY`.

    Constructs a :class:`SetupEvidenceHandler` **without** an LLM
    router (since ``PHASE_REGISTRY`` callers do not inject one). This
    means the fallback template is returned. Callers that want real
    LLM evidence compilation should instantiate
    :class:`SetupEvidenceHandler` directly with an ``llm_router``
    and call :meth:`SetupEvidenceHandler.execute`.

    Args:
        loop_id: 12-character hex loop identifier.
        task: Human-readable task description.
        goal: Optional goal string.

    Returns:
        Markdown artifact content as a plain string (matches the
        original ``run()`` contract).
    """
    handler = SetupEvidenceHandler(llm_router=None, cost_tracker=None)
    return await handler.execute(loop_id=loop_id, task=task, goal=goal)


__all__ = [
    "SetupEvidenceHandler",
    "run",
]

"""Phase 6 — Update Documents: synchronise documentation and cross-references.

Produces a ``doc-sync-report.md`` artifact listing documentation
changes, cross-reference updates, and index modifications.

Extends :class:`BasePhaseHandler` with LLM-powered document sync
using the :class:`SystemPromptBuilder` for prompt construction and
the injected ``LLMRouter`` for the actual call.

When no LLM router is available (fallback mode), returns the original
static template as a graceful degradation path.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from guinevere.loops.phases.base import BasePhaseHandler, PhaseArtifact, TokenUsage
from guinevere.loops.prompts import build_system_prompt, PHASE_NAMES
from guinevere.loops.context import LoopContext

logger = structlog.get_logger()

_PHASE = 6
_PHASE_NAME = PHASE_NAMES.get(_PHASE, "Update Documents")


class UpdateDocsHandler(BasePhaseHandler):
    """Phase 6 handler — synchronises documentation affected by the change.

    Uses the LLM router (injected via the parent constructor) to produce
    a structured doc-sync report identifying:

    1. **CHANGELOG entries** — what changed and why
    2. **ADR references** — affected decision records
    3. **API documentation** — endpoints, schemas, parameters
    4. **README updates** — user-facing docs that need revision
    5. **Cross-reference validation** — broken links, stale indexes

    Falls back to a static template when ``self._llm_router`` is
    ``None`` (graceful degradation for setups without an LLM backend).
    """

    async def _execute(
        self,
        loop_id: str,
        task: str,
        goal: str,
    ) -> PhaseArtifact:
        """Execute the Update Documents phase.

        Args:
            loop_id: 12-character hex loop identifier.
            task: Human-readable task description.
            goal: Optional goal string.

        Returns:
            A :class:`PhaseArtifact` with the doc-sync report as
            markdown content, phase=6, and token usage metadata when
            an LLM call was made.
        """
        logger.info(
            "update_docs_handler.execute.start",
            loop_id=loop_id,
            task=task,
            has_goal=bool(goal),
        )

        # ── Fallback: no LLM router, return template ──────────────
        if self._llm_router is None:
            logger.warning(
                "update_docs_handler.no_llm_router",
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
            "Update all documentation affected by this task. "
            "Produce a structured doc-sync report.\n\n"
            f"Task: {task}\n\n"
            f"{goal_section}"
            "List all documents that need updating:\n"
            "1. **CHANGELOG entries** — summarise what changed and why\n"
            "2. **ADR references** — affected architecture decision "
            "records with exact section citations\n"
            "3. **API documentation** — endpoints, schemas, parameters "
            "that must be revised\n"
            "4. **README updates** — user-facing docs, getting-started "
            "guides, or configuration examples\n"
            "5. **Cross-reference validation** — broken links, stale "
            "index entries, or missing evidence path references\n"
            "Provide exact file paths and sections to update."
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
            "update_docs_handler.execute.complete",
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
            f"# Doc-Sync Report\n\n"
            f"**Loop:** `{loop_id}`\n"
            f"**Phase:** {_PHASE_NAME} (Phase {_PHASE})\n"
            f"**Task:** {task}\n"
            f"{goal_section}"
            f"---\n\n"
            f"## Docs Updated\n\n"
            f"| Document | Action | Section | Summary |\n"
            f"|---|---|---|---|\n"
            f"| *pending* | — | — | — |\n\n"
            f"## Cross-References\n\n"
            f"| Source Doc | Target Doc | Link Type | Status |\n"
            f"|---|---|---|---|\n"
            f"| *pending* | — | — | — |\n\n"
            f"## Index Updates\n\n"
            f"| Index File | Entries Added | Entries Modified | Status |\n"
            f"|---|---|---|---|\n"
            f"| *pending* | — | — | — |\n"
        )

    @staticmethod
    def _format_llm_output(
        content: str,
        loop_id: str,
        task: str,
        goal: str,
    ) -> str:
        """Wrap raw LLM output in the structured doc-sync artifact.

        The LLM response is placed under an ``## LLM Response``
        section so the artifact remains self-contained markdown.
        Downstream phases (Setup Evidence) read and aggregate this
        content.
        """
        goal_section = f"\n**Goal:** {goal}\n" if goal else ""

        return (
            f"# Doc-Sync Report\n\n"
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

    Constructs an :class:`UpdateDocsHandler` **without** an LLM router
    (since ``PHASE_REGISTRY`` callers do not inject one). This means
    the fallback template is returned. Callers that want real LLM
    document sync should instantiate :class:`UpdateDocsHandler`
    directly with an ``llm_router`` and call
    :meth:`UpdateDocsHandler.execute`.

    Args:
        loop_id: 12-character hex loop identifier.
        task: Human-readable task description.
        goal: Optional goal string.

    Returns:
        Markdown artifact content as a plain string (matches the
        original ``run()`` contract).
    """
    handler = UpdateDocsHandler(llm_router=None, cost_tracker=None)
    return await handler.execute(loop_id=loop_id, task=task, goal=goal)


__all__ = [
    "UpdateDocsHandler",
    "run",
]

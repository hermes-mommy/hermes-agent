"""Phase 1 — Research: gather context via LLM, surface dependencies and risks.

Extends :class:`BasePhaseHandler` with LLM-powered research using the
:class:`SystemPromptBuilder` for prompt construction and the injected
``LLMRouter`` for the actual call.

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

_PHASE = 1
_PHASE_NAME = PHASE_NAMES.get(_PHASE, "Research")


class ResearchHandler(BasePhaseHandler):
    """Phase 1 handler — gathers context via LLM-powered research.

    Produces a structured markdown report covering objective, key
    findings, dependency table, risks, and recommendations.

    Falls back to a static template when ``self._llm_router`` is
    ``None`` (graceful degradation for setups without an LLM
    backend).
    """

    async def _execute(
        self,
        loop_id: str,
        task: str,
        goal: str,
    ) -> PhaseArtifact:
        """Execute the Research phase and return a structured artifact.

        Args:
            loop_id: 12-character hex loop identifier.
            task: Human-readable task description.
            goal: Optional goal string.

        Returns:
            A :class:`PhaseArtifact` with the research report as
            markdown content, phase=1, and token usage metadata when
            an LLM call was made.
        """
        logger.info(
            "research_handler.execute.start",
            loop_id=loop_id,
            task=task,
            has_goal=bool(goal),
        )

        # ── Fallback: no LLM router, return template ──────────────
        if self._llm_router is None:
            logger.warning(
                "research_handler.no_llm_router",
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
            "Research the following task and produce a structured "
            "research report.\n\n"
            f"Task: {task}\n\n"
            f"{goal_section}"
            "Include: Objective, Key Findings, Dependencies (table), "
            "Risks, and Recommendations."
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

        # ── Parse and structure the LLM response ─────────────────
        raw_content = result.get("content", "")
        artifact_content = self._format_llm_output(
            content=raw_content,
            loop_id=loop_id,
            task=task,
            goal=goal,
        )

        logger.info(
            "research_handler.execute.complete",
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
            f"# Research Report\n\n"
            f"**Loop:** `{loop_id}`\n"
            f"**Phase:** {_PHASE_NAME} (Phase {_PHASE})\n"
            f"**Task:** {task}\n"
            f"{goal_section}"
            f"---\n\n"
            f"## Objective\n\n"
            f"_{task}_\n\n"
            f"## Findings\n\n"
            f"- _Findings pending — LLM router not available._\n\n"
            f"## Dependencies\n\n"
            f"| Dependency | Type | Status |\n"
            f"|---|---|---|\n"
            f"| _pending_ | — | — |\n\n"
            f"## Risks\n\n"
            f"- _No risks identified yet._\n\n"
            f"## Recommendations\n\n"
            f"1. _Pending research completion._\n"
        )

    @staticmethod
    def _format_llm_output(
        content: str,
        loop_id: str,
        task: str,
        goal: str,
    ) -> str:
        """Wrap the raw LLM output in a structured research artifact.

        The LLM response is placed under a ``## LLM Response`` section
        so the artifact remains self-contained markdown. Downstream
        phases (Plan & Delegate, Delegate, etc.) read and parse this
        content.
        """
        goal_section = f"\n**Goal:** {goal}\n" if goal else ""

        return (
            f"# Research Report\n\n"
            f"**Loop:** `{loop_id}`\n"
            f"**Phase:** {_PHASE_NAME} (Phase {_PHASE})\n"
            f"**Task:** {task}\n"
            f"{goal_section}"
            f"---\n\n"
            f"## Objective\n\n"
            f"_{task}_\n\n"
            f"## LLM Response\n\n"
            f"{content}\n"
        )


# ── Backward-compatible entry point ─────────────────────────────────


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Backward-compatible entry point used by :data:`PHASE_REGISTRY`.

    Constructs a :class:`ResearchHandler` **without** an LLM router
    (since ``PHASE_REGISTRY`` callers do not inject one). This means
    the fallback template is returned. Callers that want real LLM
    research should instantiate :class:`ResearchHandler` directly
    with an ``llm_router`` and call :meth:`ResearchHandler.execute`.

    Args:
        loop_id: 12-character hex loop identifier.
        task: Human-readable task description.
        goal: Optional goal string.

    Returns:
        Markdown artifact content as a plain string (matches the
        original ``run()`` contract).
    """
    handler = ResearchHandler(llm_router=None, cost_tracker=None)
    return await handler.execute(loop_id=loop_id, task=task, goal=goal)


__all__ = [
    "ResearchHandler",
    "run",
]

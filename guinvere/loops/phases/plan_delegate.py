"""Phase 2 — Plan & Delegate: synthesize research into execution plan.

Produces a markdown artifact with task breakdown, sub-agent
assignment, dependency map, and verification scaffold.
"""

from __future__ import annotations

import structlog

from guinvere.loops.context import LoopContextBuilder
from guinvere.loops.prompts import build_system_prompt
from guinvere.loops.phases.base import BasePhaseHandler, PhaseArtifact, TokenUsage

logger = structlog.get_logger()


class PlanDelegateHandler(BasePhaseHandler):
    """Phase 2 — Plan & Delegate handler.

    Synthesises research output into an executable plan with atomic
    sub-steps, dependency map, risk assessment, and per-step
    verification scaffold. Uses ``self._call_llm`` for LLM-backed
    plan generation. Falls back to a template when *llm_router* is
    ``None``.
    """

    async def _execute(self, loop_id: str, task: str, goal: str) -> PhaseArtifact:
        """Execute the Plan & Delegate phase.

        Args:
            loop_id: Unique loop identifier (12-char hex).
            task: Human-readable task description.
            goal: Optional goal string for plan generation.

        Returns:
            PhaseArtifact with the plan markdown content.
        """
        # Graceful fallback when no LLM router is injected.
        if self._llm_router is None:
            logger.warning(
                "plan_delegate_handler.no_llm_router",
                loop_id=loop_id,
                fallback="template",
            )
            content = (
                f"# Execution Plan\n\n"
                f"**Loop:** `{loop_id}`\n"
                f"**Task:** {task}\n\n"
                f"_Plan pending — LLM router not available._"
            )
            return PhaseArtifact(
                content=content,
                phase=2,
                token_usage=None,
                metadata={"fallback": True},
            )

        # Build LoopContext for prompt generation.
        ctx = (
            LoopContextBuilder()
            .set_loop_id(loop_id)
            .set_task(task)
            .set_goal(goal)
            .set_phase(2)
            .build()
        )

        system_prompt = build_system_prompt(ctx=ctx)

        goal_block = f"\n\n## Goal\n\n{goal}\n\n" if goal else "\n"

        user_msg = (
            f"Based on the research phase, create an execution plan for this task.\n\n"
            f"## Task\n\n{task}\n\n"
            f"{goal_block}"
            f"## Requirements\n\n"
            f"1. **Atomic sub-steps** — each independently verifiable and owned "
            f"by one sub-agent\n"
            f"2. **Dependencies** — declare which steps must finish before others "
            f"begin\n"
            f"3. **Estimated effort** — rough complexity per step "
            f"(low / medium / high)\n"
            f"4. **Risk assessment** — flag risky steps, unknowns, or blockers\n"
            f"5. **Verification scaffold** — for each step, specify the exact "
            f"acceptance test, expected files, forbidden patterns, and required "
            f"commands that prove it is done\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]

        result = await self._call_llm(
            messages,
            task_type="CORE_REASONING",
            max_tokens=4096,
            loop_id=loop_id,
        )

        content: str = result.get("content", "")
        usage: dict = result.get("usage", {})
        model: str = result.get("model", "unknown")

        token_usage = TokenUsage(
            model=model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            cost_usd=0.0,
        )

        logger.info(
            "plan_delegate_handler.complete",
            loop_id=loop_id,
            content_length=len(content),
            model=model,
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
        )

        return PhaseArtifact(
            content=content,
            phase=2,
            token_usage=token_usage,
            metadata={"model": model},
        )


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Backward-compatible standalone entry point.

    Instantiates ``PlanDelegateHandler`` without an LLM router so the
    fallback template is returned. Callers that need LLM-backed plan
    generation should instantiate the handler directly:

    .. code-block:: python

        handler = PlanDelegateHandler(llm_router=router, cost_tracker=tracker)
        artifact = await handler.execute(loop_id, task, goal)
    """
    handler = PlanDelegateHandler(llm_router=None, cost_tracker=None)
    return await handler.execute(loop_id=loop_id, task=task, goal=goal)

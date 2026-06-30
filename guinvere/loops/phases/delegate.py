"""Phase 3 — Delegate: hand off sub-steps to sub-agents via TaskContract.

Produces a ``delegation-manifest.md`` artifact listing every spawned
sub-agent, their task contracts, and expected outputs.

Rewrite of the original template stub into an LLM-powered
:class:`DelegateHandler` that extends :class:`BasePhaseHandler`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from guinvere.loops.context import LoopContext
from guinvere.loops.phases.base import BasePhaseHandler, PhaseArtifact, TokenUsage
from guinvere.loops.prompts import build_system_prompt

logger = structlog.get_logger()

_PHASE = 3
_PHASE_NAME = "Delegate"

# Maximum allowed length for input strings. Beyond this the handler
# truncates with a logged warning rather than silently passing giant
# payloads to the LLM.
_MAX_TASK_LENGTH: int = 32_000
_MAX_GOAL_LENGTH: int = 8_000

# LLM call parameters
_DEFAULT_MAX_TOKENS: int = 4096
_DEFAULT_TASK_TYPE: str = "CORE_REASONING"

# User-message template rendered in the LLM-powered path. Kept as a
# module-level constant so it can be independently tested or overridden
# without touching the method body.
_DELEGATE_USER_TEMPLATE: str = (
    "Delegate the execution plan to appropriate sub-agents.\n\n"
    "Task: {task}\n\n"
    "Goal: {goal}\n\n"
    "For each sub-step, specify:\n"
    "1. Sub-agent type (explore, implement, verify, etc.)\n"
    "2. Task contract (scope, acceptance criteria, forbidden patterns)\n"
    "3. Expected output path\n"
    "4. Dependencies on other sub-steps"
)


class DelegateHandler(BasePhaseHandler):
    """Phase 3 — Delegate: spawn sub-agents with task contracts.

    Calls the LLM router (when available) to produce a delegation
    manifest in markdown. Falls back to a static template when the
    router is not injected.

    Constructor injection
    ---------------------
    *llm_router* : ``LLMRouter | None``
    *cost_tracker* : ``LoopCostTracker | None``

    Usage
    -----
    ::

        handler = DelegateHandler(llm_router=router, cost_tracker=tracker)
        artifact = await handler.execute(loop_id, task, goal)
        markdown = artifact.content
    """

    async def _execute(self, loop_id: str, task: str, goal: str) -> PhaseArtifact:
        """Produce a delegation-manifest artifact.

        When ``self._llm_router`` is *None*, emits a static placeholder
        so the calling manager can still progress through the loop.

        Args:
            loop_id: 12-character hex loop identifier.
            task: Human-readable task description.
            goal: Optional goal string for plan-generation context.

        Returns:
            A :class:`PhaseArtifact` with phase=3, the delegation
            manifest as markdown content, and token usage metadata
            (when the LLM path was taken).
        """
        # ---------- input validation ----------
        if not loop_id or len(loop_id) != 12:
            logger.error(
                "delegate_handler.invalid_loop_id",
                loop_id=loop_id,
                reason="expected 12-char hex string",
            )
            raise ValueError(
                f"loop_id must be a 12-character string; got {loop_id!r}"
            )

        if not task or not task.strip():
            logger.error(
                "delegate_handler.empty_task",
                loop_id=loop_id,
                reason="task must be non-empty",
            )
            raise ValueError("task must be a non-empty string.")

        if len(task) > _MAX_TASK_LENGTH:
            logger.warning(
                "delegate_handler.task_truncated",
                loop_id=loop_id,
                original_length=len(task),
                max_length=_MAX_TASK_LENGTH,
            )
            task = task[:_MAX_TASK_LENGTH]

        if len(goal) > _MAX_GOAL_LENGTH:
            logger.warning(
                "delegate_handler.goal_truncated",
                loop_id=loop_id,
                original_length=len(goal),
                max_length=_MAX_GOAL_LENGTH,
            )
            goal = goal[:_MAX_GOAL_LENGTH]

        # ---------- fallback: no LLM router injected ----------
        if self._llm_router is None:
            logger.warning(
                "delegate_handler.no_llm_router",
                loop_id=loop_id,
                fallback="template",
            )
            content = self._build_fallback_manifest(loop_id, task, goal)
            return PhaseArtifact(
                content=content,
                phase=_PHASE,
                token_usage=None,
                metadata={
                    "fallback": True,
                    "reason": "llm_router_not_injected",
                },
            )

        # ---------- LLM-powered path ----------
        ctx = LoopContext(
            loop_id=loop_id,
            task=task,
            goal=goal,
            phase=_PHASE,
            created_at=datetime.now(timezone.utc),
        )
        system_prompt = build_system_prompt(ctx=ctx)

        user_msg = _DELEGATE_USER_TEMPLATE.format(task=task, goal=goal)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]

        # Attempt the LLM call with a single retry on empty/error response.
        result: dict[str, Any] | None = None
        for attempt in (1, 2):
            try:
                result = await self._call_llm(
                    messages,
                    task_type=_DEFAULT_TASK_TYPE,
                    max_tokens=_DEFAULT_MAX_TOKENS,
                    loop_id=loop_id,
                )
                content_candidate: str = (result or {}).get("content", "")
                if content_candidate.strip():
                    break
                logger.warning(
                    "delegate_handler.retry_empty",
                    loop_id=loop_id,
                    attempt=attempt,
                )
            except RuntimeError as rte:
                logger.warning(
                    "delegate_handler.llm_runtime_error",
                    loop_id=loop_id,
                    attempt=attempt,
                    error=str(rte),
                )
                result = None
            except Exception as exc:
                logger.warning(
                    "delegate_handler.llm_call_failed",
                    loop_id=loop_id,
                    attempt=attempt,
                    error=str(exc),
                )
                result = None

        # ---------- build response ----------
        if result is None:
            logger.warning(
                "delegate_handler.fallback_after_llm_failure",
                loop_id=loop_id,
            )
            content = self._build_fallback_manifest(loop_id, task, goal)
            return PhaseArtifact(
                content=content,
                phase=_PHASE,
                token_usage=None,
                metadata={
                    "fallback": True,
                    "reason": "llm_call_failed_after_retry",
                },
            )

        usage = result.get("usage", {})
        token_usage = TokenUsage(
            model=result.get("model", "unknown"),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            cost_usd=0.0,
        )

        llm_content: str = result.get("content", "")
        if not llm_content.strip():
            logger.warning(
                "delegate_handler.empty_llm_response_after_retry",
                loop_id=loop_id,
                fallback="template",
            )
            content = self._build_fallback_manifest(loop_id, task, goal)
        else:
            content = llm_content

        logger.info(
            "delegate_handler.complete",
            loop_id=loop_id,
            llm_used=True,
            content_length=len(content),
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
        )

        return PhaseArtifact(
            content=content,
            phase=_PHASE,
            token_usage=token_usage,
            metadata={
                "llm_used": True,
                "model": token_usage.model,
            },
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_fallback_manifest(loop_id: str, task: str, goal: str) -> str:
        """Return a static delegation-manifest template.

        Used when the LLM router is unavailable, returns empty output,
        or the LLM call fails after the configured retry count.
        """
        goal_section = f"\n**Goal:** {goal}\n" if goal else ""

        return f"""\
# Delegation Manifest

**Loop:** `{loop_id}`
**Phase:** {_PHASE_NAME} (Phase {_PHASE})
**Task:** {task}{goal_section}
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


# ------------------------------------------------------------------
# Module-level convenience (backward-compatible with PHASE_REGISTRY)
# ------------------------------------------------------------------


async def run(loop_id: str, task: str, goal: str = "") -> str:
    """Execute the Delegate phase and return markdown artifact content.

    The caller is responsible for persisting the returned string via
    :func:`guinvere.loops.artifacts.write_artifact`.

    This function constructs a :class:`DelegateHandler` **without** an
    LLM router, which means it uses the static fallback template. When
    the ``LoopManager`` is upgraded to inject the router, callers
    should instantiate :class:`DelegateHandler` directly::

        handler = DelegateHandler(llm_router=router, cost_tracker=tracker)
        content = await handler.execute(loop_id, task, goal)

    Args:
        loop_id: 12-character hex loop identifier.
        task: Human-readable task description for this loop.
        goal: Optional goal string for plan-generation context.

    Returns:
        The markdown artifact content as a plain string.
    """
    handler = DelegateHandler()
    return await handler.execute(loop_id, task, goal)

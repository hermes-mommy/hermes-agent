"""ReAct-style conversation loop — dynamic LLM-driven task execution.

Replaces the static 7-phase pipeline with a reasoning-acting loop that
alternates between:

1. **REASON** — Send current context + message history to LLM, get response.
2. **ACT** — If the response includes tool calls, execute them via the
   injected ``tool_executor`` callable.
3. **OBSERVE** — Append tool results to the message history as ``tool``-role
   messages.
4. **REPEAT** — Return to step 1 until the task is complete, the budget is
   exhausted, or the maximum number of turns is reached.

The loop is **tool-executor-agnostic**: it accepts tool execution as a
``Callable[[str, str], Awaitable[str]]`` and never imports from
``src.mcp`` or ``src.core`` directly. This keeps the module testable in
isolation with a mock executor.

Construction injection:
    - ``llm_router``: any object with an async ``chat`` method returning
      ``{content: str, usage: {...}, tool_calls: [...] | None}``.
    - ``budget``: ``IterationBudget`` instance for turn/token/cost limits.
    - ``system_prompt_builder``: ``SystemPromptBuilder`` (or duck-typed
      equivalent with a ``build`` method).
    - ``tool_executor``: optional async callable ``(tool_name, args_json) -> str``.

Usage::

    loop = ConversationLoop(llm_router=router, budget=budget, builder=builder)
    result = await loop.run(ctx=ctx, task="Deploy release", goal="Zero-downtime")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import structlog

from guinvere.loops.context import LoopContext

logger = structlog.get_logger()


@dataclass(frozen=True)
class ToolCallRecord:
    """Immutable record of a single tool invocation within the loop.

    Captures the tool name, serialised arguments, result string,
    wall-clock duration (milliseconds), and success/failure flag.
    """

    tool_name: str
    arguments: str
    result: str
    duration_ms: float
    success: bool


@dataclass(frozen=True)
class ConversationResult:
    """Immutable result produced by one ``ConversationLoop.run`` call.

    Fields
    ------
    final_response:
        The last LLM response content, or an explanatory message when the
        loop terminated abnormally.
    turns_used:
        Number of REASON-ACT-OBSERVE iterations completed.
    total_input_tokens:
        Sum of ``input_tokens`` across every LLM call in this loop.
    total_output_tokens:
        Sum of ``output_tokens`` across every LLM call.
    total_cost_usd:
        Cumulative estimated USD cost. Accurate only when the router
        returns meaningful ``usage.cost_usd`` values.
    tool_calls:
        Chronological list of every tool call made during the loop.
    status:
        One of ``"complete"``, ``"budget_exhausted"``, ``"max_turns"``,
        or ``"error"``.
    error:
        Diagnostic error string, set only when ``status == "error"``.
    """

    final_response: str
    turns_used: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    status: str = "complete"
    error: str | None = None


# ── Completion markers ──────────────────────────────────────────────
# The LLM can use any of these (case-insensitive) to signal that the
# task is finished. Markers are deliberately broad — the loop favours
# one extra turn over a false-positive completion.
_COMPLETION_MARKERS: tuple[str, ...] = (
    "task complete",
    "task completed",
    "i've completed",
    "i have completed",
    "done.",
    "all done",
    "finished.",
    "[COMPLETE]",
    "STATUS: COMPLETE",
)


class ConversationLoop:
    """ReAct-style conversation loop for autonomous task execution.

    The loop owns the message history and drives turn-by-turn reasoning
    by calling the injected ``llm_router.chat`` method. Tool calls in
    the LLM response trigger execution via ``tool_executor``, and the
    results are appended as ``tool``-role messages before the next turn.

    The loop is **not** safe to reuse concurrently — each ``run`` call
    constructs its own message list internally.
    """

    def __init__(
        self,
        llm_router: Any,
        budget: Any,  # IterationBudget
        system_prompt_builder: Any,  # SystemPromptBuilder
        tool_executor: Callable[..., Awaitable[str]] | None = None,
        max_turns: int = 50,
    ) -> None:
        if max_turns < 1:
            raise ValueError(f"max_turns must be >= 1, got {max_turns}")

        self._llm_router = llm_router
        self._budget = budget
        self._builder = system_prompt_builder
        self._tool_executor = tool_executor
        self._max_turns = max_turns

        logger.debug(
            "conversation_loop.initialized",
            max_turns=max_turns,
            has_tool_executor=tool_executor is not None,
        )

    # ── Public API ──────────────────────────────────────────────────

    async def run(
        self,
        ctx: LoopContext,
        task: str,
        goal: str = "",
        memories: list[dict[str, Any]] | None = None,
        kg_facts: list[str] | None = None,
        available_tools: list[str] | None = None,
    ) -> ConversationResult:
        """Run the ReAct loop until completion or budget exhaustion.

        Args:
            ctx: Frozen :class:`LoopContext` for this loop session.
            task: The task description to execute.
            goal: Optional high-level goal string.
            memories: Optional list of recalled memory dicts.
            kg_facts: Optional list of knowledge-graph fact strings.
            available_tools: Optional list of tool names the LLM may
                call. Passed to the system prompt builder so the LLM
                knows what tools are available.

        Returns:
            A :class:`ConversationResult` with the final state.
        """
        # Build initial system prompt.
        system_prompt = self._builder.build(
            ctx,
            memories=memories,
            kg_facts=kg_facts,
            available_tools=available_tools,
        )

        # Initialise message history.
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task}\n\nGoal: {goal}"},
        ]

        tool_calls: list[ToolCallRecord] = []
        total_input: int = 0
        total_output: int = 0
        total_cost: float = 0.0
        last_content: str = ""

        logger.info(
            "conversation_loop.started",
            loop_id=ctx.loop_id,
            task=task,
            max_turns=self._max_turns,
        )

        for turn in range(1, self._max_turns + 1):
            # ── Budget check ────────────────────────────────────────
            if self._budget.exhausted():
                logger.warning(
                    "conversation_loop.budget_exhausted",
                    loop_id=ctx.loop_id,
                    turn=turn,
                )
                return ConversationResult(
                    final_response="Budget exhausted. Cannot continue.",
                    turns_used=turn - 1,
                    total_input_tokens=total_input,
                    total_output_tokens=total_output,
                    total_cost_usd=total_cost,
                    tool_calls=tool_calls,
                    status="budget_exhausted",
                )

            # ── REASON: Call LLM ────────────────────────────────────
            try:
                result = await self._llm_router.chat(
                    messages=messages,
                    task_type="CORE_REASONING",
                    max_tokens=4096,
                )
            except Exception as exc:
                logger.error(
                    "conversation_loop.llm_error",
                    loop_id=ctx.loop_id,
                    turn=turn,
                    error=str(exc),
                )
                return ConversationResult(
                    final_response=f"LLM call failed: {exc}",
                    turns_used=turn,
                    total_input_tokens=total_input,
                    total_output_tokens=total_output,
                    total_cost_usd=total_cost,
                    tool_calls=tool_calls,
                    status="error",
                    error=str(exc),
                )

            # Extract response content and usage.
            content: str = result.get("content", "")
            usage: dict[str, Any] = result.get("usage", {})
            input_tokens: int = usage.get("input_tokens", 0)
            output_tokens: int = usage.get("output_tokens", 0)
            cost_this_call: float = usage.get("cost_usd", 0.0)
            total_input += input_tokens
            total_output += output_tokens
            total_cost += cost_this_call
            last_content = content

            # Record cost via budget.
            await self._budget.consume_turn(
                tokens=input_tokens + output_tokens,
                cost_usd=cost_this_call,
            )

            tool_calls_in_response: list[dict[str, Any]] | None = result.get(
                "tool_calls"
            )

            # ── ACT: Execute tool calls if present ──────────────────
            if tool_calls_in_response and self._tool_executor:
                # Append assistant message with tool calls.
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": content,
                }
                assistant_msg["tool_calls"] = tool_calls_in_response
                messages.append(assistant_msg)

                for tc in tool_calls_in_response:
                    tool_name: str = tc.get("name", "unknown")
                    tool_args: str = tc.get("arguments", "{}")

                    start = time.monotonic()
                    try:
                        tool_result: str = await self._tool_executor(
                            tool_name, tool_args
                        )
                        duration: float = (time.monotonic() - start) * 1000
                        success: bool = True
                    except Exception as exc:
                        tool_result = f"Tool execution failed: {exc}"
                        duration = (time.monotonic() - start) * 1000
                        success = False

                    record = ToolCallRecord(
                        tool_name=tool_name,
                        arguments=tool_args,
                        result=tool_result,
                        duration_ms=round(duration, 1),
                        success=success,
                    )
                    tool_calls.append(record)

                    logger.debug(
                        "conversation_loop.tool_call",
                        loop_id=ctx.loop_id,
                        turn=turn,
                        tool_name=tool_name,
                        duration_ms=round(duration, 1),
                        success=success,
                    )

                    # OBSERVE: Append tool result.
                    messages.append(
                        {
                            "role": "tool",
                            "content": tool_result,
                            "name": tool_name,
                        }
                    )

                # Continue loop — LLM will see tool results next turn.
                continue

            # ── No tool calls — check completion ────────────────────
            if self._is_task_complete(content, task):
                logger.info(
                    "conversation_loop.complete",
                    loop_id=ctx.loop_id,
                    turn=turn,
                    total_turns=turn,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    tool_calls_made=len(tool_calls),
                )
                return ConversationResult(
                    final_response=content,
                    turns_used=turn,
                    total_input_tokens=total_input,
                    total_output_tokens=total_output,
                    total_cost_usd=total_cost,
                    tool_calls=tool_calls,
                    status="complete",
                )

            # Append assistant response and continue.
            messages.append({"role": "assistant", "content": content})

        # ── Max turns reached without completion ────────────────────
        logger.warning(
            "conversation_loop.max_turns",
            loop_id=ctx.loop_id,
            max_turns=self._max_turns,
            input_tokens=total_input,
            output_tokens=total_output,
        )
        return ConversationResult(
            final_response=last_content
            if last_content
            else "Max turns reached without completion.",
            turns_used=self._max_turns,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cost_usd=total_cost,
            tool_calls=tool_calls,
            status="max_turns",
        )

    # ── Internal helpers ────────────────────────────────────────────

    @staticmethod
    def _is_task_complete(response: str, task: str) -> bool:
        """Heuristic check if the LLM response indicates task completion.

        Checks for explicit completion markers in the response text.
        Does **not** make an LLM call for this check — that would be
        too expensive per turn.

        The check is case-insensitive and looks for the markers defined
        in the module-level ``_COMPLETION_MARKERS`` tuple. This is a
        simple substring match intentionally: false negatives (missing a
        completion) cost one extra LLM turn, whereas false positives
        would truncate the loop early.
        """
        lower: str = response.lower().strip()

        for marker in _COMPLETION_MARKERS:
            if marker in lower:
                logger.debug(
                    "conversation_loop.completion_marker_detected",
                    marker=marker,
                )
                return True

        return False


# ── Module-level convenience ────────────────────────────────────────


async def run_conversation(
    llm_router: Any,
    budget: Any,
    ctx: LoopContext,
    task: str,
    goal: str = "",
    **kwargs: Any,
) -> ConversationResult:
    """Module-level convenience wrapper for a single conversation run.

    Constructs a default :class:`SystemPromptBuilder`, wires it into a
    :class:`ConversationLoop`, and invokes ``loop.run()`` with the given
    arguments.

    Use this when you do not need a custom ``system_prompt_builder`` or
    ``tool_executor``. Pass those via ``**kwargs`` if needed::

        result = await run_conversation(
            llm_router=router,
            budget=budget,
            ctx=ctx,
            task="Hello world",
            tool_executor=my_executor,
        )

    Args:
        llm_router: LLM router with an async ``chat`` method.
        budget: :class:`IterationBudget` instance.
        ctx: Frozen :class:`LoopContext`.
        task: Task description for the LLM.
        goal: Optional goal string.
        **kwargs: Forwarded to :class:`ConversationLoop` constructor
            (e.g. ``tool_executor``, ``max_turns``, or overrides for
            ``system_prompt_builder``).

    Returns:
        A :class:`ConversationResult` with the loop outcome.
    """
    from guinvere.loops.prompts import SystemPromptBuilder

    builder: SystemPromptBuilder = kwargs.pop(
        "system_prompt_builder", SystemPromptBuilder()
    )
    tool_executor: Callable[..., Awaitable[str]] | None = kwargs.pop(
        "tool_executor", None
    )
    max_turns: int = kwargs.pop("max_turns", 50)

    loop = ConversationLoop(
        llm_router=llm_router,
        budget=budget,
        system_prompt_builder=builder,
        tool_executor=tool_executor,
        max_turns=max_turns,
    )
    return await loop.run(
        ctx=ctx,
        task=task,
        goal=goal,
        memories=kwargs.pop("memories", None),
        kg_facts=kwargs.pop("kg_facts", None),
        available_tools=kwargs.pop("available_tools", None),
    )


__all__ = [
    "ConversationLoop",
    "ConversationResult",
    "ToolCallRecord",
    "run_conversation",
]

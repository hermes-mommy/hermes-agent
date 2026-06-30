"""Background Review Fork — daemon asyncio.Task for post-loop skill/memory review.

Mirrors the Hermes Agent pattern. Idle-triggered LLM review of tool usage
patterns with structured JSON suggestions. Tool whitelist via injected executor.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class ReviewSuggestion:
    """A single suggestion from the background review fork.

    suggestion_type, description, confidence, action_taken, action_result.
    """
    suggestion_type: str
    description: str
    confidence: float
    action_taken: bool = False
    action_result: str | None = None


@dataclass(frozen=True)
class ReviewForkResult:
    """Immutable result of a completed review fork run.

    suggestions, turns_used, total_tokens, status, error.
    """
    suggestions: list[ReviewSuggestion]
    turns_used: int
    total_tokens: int
    status: str
    error: str | None = None


_REVIEW_SYSTEM_PROMPT: str = (
    "You are a skill and memory review assistant for an autonomous agent system. "
    "Analyse the following tool usage summary and produce a JSON array of suggestions. "
    'Each suggestion must have keys: "type" (one of skill_improve, memory_consolidate, new_skill), '
    '"description" (brief explanation), "confidence" (0.0-1.0). '
    "Return ONLY valid JSON array — no markdown fences, no commentary. "
    "If no suggestions, return []."
)

class BackgroundReviewFork:
    """Daemon asyncio task for post-loop skill/memory review.

    Runs after idle_threshold_s of inactivity. LLM prompt parses JSON suggestions;
    approved actions executed via tool_executor. Cancelled on restart or HARD STOP.
    """

    def __init__(self, llm_router: Any,
                 tool_executor: Callable[..., Awaitable[str]] | None = None,
                 idle_threshold_s: float = 7200.0, max_fork_turns: int = 10,
                 hard_stop_checker: Callable[[], bool] | None = None) -> None:
        if idle_threshold_s < 0:
            raise ValueError(f"idle_threshold_s must be >= 0, got {idle_threshold_s}")
        if max_fork_turns < 1:
            raise ValueError(f"max_fork_turns must be >= 1, got {max_fork_turns}")
        self._llm_router: Any = llm_router
        self._tool_executor: Callable[..., Awaitable[str]] | None = tool_executor
        self._idle_threshold_s: float = idle_threshold_s
        self._max_fork_turns: int = max_fork_turns
        self._task: asyncio.Task[ReviewForkResult] | None = None
        self._cancelled: bool = False
        self._last_activity: float = time.monotonic()
        self._hard_stop_checker: Callable[[], bool] = hard_stop_checker or (lambda: False)

        logger.info("review_fork.initialized", idle_threshold_s=idle_threshold_s,
                     max_fork_turns=max_fork_turns, has_tool_executor=tool_executor is not None,
                     has_hard_stop_checker=hard_stop_checker is not None)

    def mark_activity(self) -> None:
        """Reset idle timer. Called by parent loop each turn."""
        self._last_activity = time.monotonic()

    @property
    def is_idle(self) -> bool:
        """True if idle threshold exceeded."""
        return (time.monotonic() - self._last_activity) >= self._idle_threshold_s

    async def start(self) -> None:
        """Start fork if idle. No-op if already running."""
        if self._task is not None and not self._task.done():
            logger.debug("review_fork.already_running")
            return
        if not self.is_idle:
            logger.debug("review_fork.not_idle_yet")
            return
        if self._hard_stop_checker():
            logger.warning("review_fork.hard_stop_prevented_start")
            return
        self._cancelled = False
        self._task = asyncio.create_task(self._run_fork())
        logger.info("review_fork.started")

    async def cancel(self) -> None:
        """Cancel running fork. Safe when no fork active."""
        self._cancelled = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("review_fork.cancelled")

    @property
    def is_running(self) -> bool:
        """Fork task is active."""
        return self._task is not None and not self._task.done()

    async def _run_fork(self) -> ReviewForkResult:
        """Run the review fork logic."""
        if self._cancelled:
            return ReviewForkResult(suggestions=[], turns_used=0, total_tokens=0, status="cancelled")
        if self._hard_stop_checker():
            logger.warning("review_fork.hard_stop_cancelled_during_run")
            return ReviewForkResult(suggestions=[], turns_used=0, total_tokens=0, status="cancelled")

        turns_used: int = 0
        total_tokens_est: int = 0
        suggestions: list[ReviewSuggestion] = []

        try:
            response_text: str = await self._call_llm(
                await self._build_review_prompt("No tool usage data available.")
            )
            turns_used += 1
            total_tokens_est += len(response_text) // 4
            if self._cancelled:
                return ReviewForkResult(suggestions=[], turns_used=turns_used,
                                        total_tokens=total_tokens_est, status="cancelled")

            parsed: list[dict[str, Any]] = self._parse_suggestions(response_text)

            for item in parsed:
                suggestion = ReviewSuggestion(
                    suggestion_type=item.get("type", "skill_improve"),
                    description=item.get("description", ""),
                    confidence=float(item.get("confidence", 0.5)),
                )
                if self._tool_executor is not None and turns_used < self._max_fork_turns:
                    try:
                        action_result: str = await self._execute_suggestion(suggestion)
                        turns_used += 1
                        total_tokens_est += len(action_result) // 4
                        suggestion = ReviewSuggestion(
                            suggestion_type=suggestion.suggestion_type,
                            description=suggestion.description,
                            confidence=suggestion.confidence,
                            action_taken=True, action_result=action_result,
                        )
                    except Exception as exc:
                        logger.exception("review_fork.suggestion_failed",
                                        suggestion_type=suggestion.suggestion_type, exc_info=True)
                        suggestion = ReviewSuggestion(
                            suggestion_type=suggestion.suggestion_type,
                            description=suggestion.description,
                            confidence=suggestion.confidence,
                            action_taken=False, action_result=f"Error: {exc}",
                        )
                suggestions.append(suggestion)

            logger.info("review_fork.completed", suggestion_count=len(suggestions), turns_used=turns_used)
            return ReviewForkResult(suggestions=suggestions, turns_used=turns_used,
                                    total_tokens=total_tokens_est, status="complete")

        except asyncio.CancelledError:
            logger.info("review_fork.cancelled_during_run")
            return ReviewForkResult(suggestions=suggestions, turns_used=turns_used,
                                    total_tokens=total_tokens_est, status="cancelled")
        except Exception as exc:
            logger.error("review_fork.error", error=str(exc))
            return ReviewForkResult(suggestions=suggestions, turns_used=turns_used,
                                    total_tokens=total_tokens_est, status="error", error=str(exc))

    async def _build_review_prompt(self, tool_usage_summary: str) -> str:
        """Assemble review prompt sections."""
        return "\n".join([
            "## Tool Usage Review",
            "",
            "Analyse the following tool usage patterns and identify:",
            "- Skills that could be improved or optimised",
            "- Memory entries that should be consolidated or pruned",
            "- New skills that would benefit the agent",
            "",
            "### Tool Usage Summary",
            "",
            tool_usage_summary,
            "",
            "Return ONLY a valid JSON array of suggestion objects. "
            "Each object must have keys: type, description, confidence. "
            "If no suggestions, return [].",
        ])

    async def _call_llm(self, prompt: str) -> str:
        """Send review prompt to LLM router, extract text response."""
        if self._cancelled:
            return "[]"

        response: dict[str, Any] = await self._llm_router.chat(
            messages=[
                {"role": "system", "content": _REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            task_type="CORE_REASONING",
            max_tokens=1024,
        )
        content = response.get("content", "") if isinstance(response, dict) else str(response)
        if not content:
            raise RuntimeError("LLM returned empty content during review fork")
        return content

    def _parse_suggestions(self, raw: str) -> list[dict[str, Any]]:
        """Parse LLM response: strip fences, JSON load, return [] on failure."""
        text: str = raw.strip()
        for prefix in ("```json", "```"):
            if text.startswith(prefix):
                end_idx: int = text.rfind("```")
                if end_idx > len(prefix):
                    text = text[len(prefix):end_idx].strip()
                else:
                    text = text[len(prefix):].strip()
                break
        if not text:
            return []

        try:
            parsed: Any = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("review_fork.parse_failure", raw_preview=text[:200])
            return []

        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("suggestions", "recommendations", "items"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
        logger.warning("review_fork.unexpected_structure", type_str=type(parsed).__name__)
        return []

    async def _execute_suggestion(self, suggestion: ReviewSuggestion) -> str:
        """Map suggestion type to tool call, execute via tool_executor."""
        if self._tool_executor is None:
            raise RuntimeError("No tool_executor configured for review fork")

        if suggestion.suggestion_type == "new_skill":
            tool_name: str = "skill_update"
            tool_args: dict[str, Any] = {"action": "create", "name": suggestion.description,
                                          "confidence": suggestion.confidence}
        elif suggestion.suggestion_type == "memory_consolidate":
            tool_name = "memory_add"
            tool_args = {"content": suggestion.description, "source": "review_fork", "priority": "low"}
        else:
            tool_name = "skill_update"
            tool_args = {"action": "improve", "description": suggestion.description,
                          "confidence": suggestion.confidence}

        return await self._tool_executor(tool_name, tool_args)


def create_review_fork(
    llm_router: Any,
    tool_executor: Callable[..., Awaitable[str]] | None = None,
    hard_stop_checker: Callable[[], bool] | None = None,
    **kwargs: Any,
) -> BackgroundReviewFork:
    """Factory function for BackgroundReviewFork."""
    return BackgroundReviewFork(llm_router=llm_router, tool_executor=tool_executor,
                                hard_stop_checker=hard_stop_checker, **kwargs)

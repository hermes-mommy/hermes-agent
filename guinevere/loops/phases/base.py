"""Base handler infrastructure for the 7-phase SDLC loop.

Provides:
- TokenUsage: frozen dataclass for per-call token accounting.
- PhaseArtifact: frozen dataclass wrapping markdown output + metadata.
- BasePhaseHandler: abstract base class that all 7 phase handlers extend.

Every concrete handler inherits logging, timing, cost side-channel, and
the ``_call_llm`` helper from ``BasePhaseHandler``.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class TokenUsage:
    """Per-call token consumption and cost.

    Constructed inside ``_call_llm`` or manually by the handler when the
    LLM response does not flow through the standard path.
    """

    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass(frozen=True)
class PhaseArtifact:
    """Immutable result produced by a single phase execution.

    The ``content`` field holds the markdown artifact that is returned
    to the caller. ``token_usage`` is consumed via the cost-tracker
    side-channel, **not** through the public return value of
    ``BasePhaseHandler.execute()``.
    """

    content: str  # markdown artifact
    phase: int  # 1-7
    token_usage: TokenUsage | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BasePhaseHandler(ABC):
    """Abstract base for all phase handlers.

    Subclasses MUST implement ``_execute()``. The public ``execute()``
    method wraps ``_execute()`` with logging, timing, and cost tracking.

    Constructor injection
    ---------------------
    *llm_router* : ``LLMRouter | None``
        When *None*, the handler cannot make LLM calls (``_call_llm``
        raises ``RuntimeError``).
    *cost_tracker* : ``LoopCostTracker | None``
        When *None*, token-usage side-channel recording is a no-op.
    """

    def __init__(
        self,
        llm_router: Any | None = None,
        cost_tracker: Any | None = None,
    ) -> None:
        self._llm_router = llm_router
        self._cost_tracker = cost_tracker

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute(self, loop_id: str, task: str, goal: str) -> PhaseArtifact:
        """Subclass implements this. Returns a ``PhaseArtifact``."""
        ...

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def execute(self, loop_id: str, task: str, goal: str = "") -> str:
        """Public entry — wraps ``_execute()`` with logging + timing.

        Returns the artifact content as ``str`` (backward-compatible with
        the current ``manager.py`` call pattern). Token usage is recorded
        via the **cost-tracker side-channel**, not through the return
        value.
        """
        phase_name = self.__class__.__name__
        logger.info("phase.start", loop_id=loop_id, handler=phase_name, task=task)

        start = time.monotonic()
        artifact = await self._execute(loop_id, task, goal)
        elapsed = time.monotonic() - start

        # Record cost via side-channel (not through return value)
        if artifact.token_usage is not None and self._cost_tracker is not None:
            try:
                self._cost_tracker.record_loop_cost(
                    loop_id=loop_id,
                    model=artifact.token_usage.model,
                    input_tokens=artifact.token_usage.input_tokens,
                    output_tokens=artifact.token_usage.output_tokens,
                    cost_per_1k_input=artifact.token_usage.cost_per_1k_input,
                    cost_per_1k_output=artifact.token_usage.cost_per_1k_output,
                )
            except Exception as cost_err:
                logger.warning(
                    "phase.cost_record_failed",
                    loop_id=loop_id,
                    error=str(cost_err),
                )

        logger.info(
            "phase.complete",
            loop_id=loop_id,
            handler=phase_name,
            elapsed_s=round(elapsed, 2),
            has_token_usage=artifact.token_usage is not None,
        )

        return artifact.content

    # ------------------------------------------------------------------
    # Protected helpers
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        task_type: str = "CORE_REASONING",
        max_tokens: int = 4096,
        loop_id: str = "",
    ) -> dict[str, Any]:
        """Protected LLM call with budget + cost tracking.

        Returns the ``LLMRouter.chat()`` result dict with keys:

        - ``content`` : str — the response text
        - ``usage`` : dict with ``input_tokens``, ``output_tokens``,
          ``total_tokens``
        - ``model`` : str

        Raises ``RuntimeError`` if ``llm_router`` was not injected.
        """
        if self._llm_router is None:
            raise RuntimeError(
                f"LLMRouter not injected into {self.__class__.__name__}. "
                "Cannot make LLM calls without a router."
            )

        result = await self._llm_router.chat(
            messages=messages,
            task_type=task_type,
            max_tokens=max_tokens,
        )

        # Extract usage for TokenUsage construction
        usage = result.get("usage", {})
        token_usage = TokenUsage(
            model=result.get("model", "unknown"),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            cost_usd=0.0,  # Calculated by caller if needed
        )

        logger.debug(
            "phase.llm_call",
            loop_id=loop_id,
            handler=self.__class__.__name__,
            model=token_usage.model,
            input_tokens=token_usage.input_tokens,
            output_tokens=token_usage.output_tokens,
        )

        return result

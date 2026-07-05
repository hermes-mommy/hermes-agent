"""Hermes Brain Bridge — LK-004.

This module provides the ``HermesBrain`` class that wraps AIAgent for
life_kernel decision-making. It's the brain of the living autonomy kernel.

The bridge calls Hermes for ALL autonomous reasoning: decisions, planning,
reflection, self-improvement. HermesBrain is NOT Discord-specific — it's the
kernel's brain for life autonomy.

Usage::

    from guinevere.life_kernel.hermes_brain import HermesBrain, HermesBrainError

    brain = HermesBrain(llm_config={
        "base_url": "https://api.9router.com/v1",
        "model": "gpt-5.5",
        "provider": "openai",
        "api_key": "sk-...",
    })

    result = await brain.think(
        user_message="What should I do today?",
        system_prompt="You are an autonomous decision-making agent.",
        conversation_history=[...],
    )
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


# ── Configuration Dataclass ────────────────────────────────────────────────────

@dataclass(frozen=True)
class HermesBrainConfig:
    """Configuration dataclass for Hermes brain bridge.

    This dataclass provides type-safe configuration for the Hermes brain
    bridge. The __init__ method accepts both dict and HermesBrainConfig
    instances for backwards compatibility.

    Attributes:
        base_url: Base URL for the LLM API (e.g., "https://api.9router.com/v1").
        model: Model name to use (e.g., "gpt-5.5").
        provider: LLM provider name (e.g., "openai").
        api_key: API key for authentication.
        max_iterations: Maximum reasoning iterations (default: 5).

    Example:
        >>> config = HermesBrainConfig(
        ...     base_url="https://api.9router.com/v1",
        ...     model="gpt-5.5",
        ...     provider="openai",
        ...     api_key="sk-...",
        ... )
    """
    base_url: str
    model: str
    provider: str
    api_key: str
    max_iterations: int = 5


# ── Lazy AIAgent import ────────────────────────────────────────────────────
# Module-level import of run_agent breaks test collection in environments
# where the run_agent dependency tree is incomplete (e.g. missing browser_tool
# plugin). The AIAgent class is loaded lazily when an agent instance is first
# needed, and can be fully replaced via agent_factory for testing.


def _load_aiagent() -> Any:
    """Lazily import and return the AIAgent class.

    Returns:
        The AIAgent class from run_agent.

    Raises:
        ImportError: If run_agent is not installed.
    """
    from run_agent import AIAgent  # noqa: PLC0415 — intentional lazy import

    return AIAgent


def _default_agent_factory(**kwargs: Any) -> Any:
    """Default agent factory: lazily import AIAgent and construct an instance.

    Matches the agent_factory contract (``factory(base_url=..., model=..., ...)
    -> agent``): it is called with the AIAgent constructor keyword arguments
    and returns a configured AIAgent instance. Tests inject a MagicMock with
    the same call signature.

    The brain uses Hermes native memory + kernel context files (full persona
    SOUL context) so Guinevere reasons with her complete identity. Token cost
    is operator-approved as unlimited.

    Returns:
        A configured AIAgent instance.
    """
    AIAgent = _load_aiagent()
    return AIAgent(**kwargs)


# ── Constants ────────────────────────────────────────────────────────────────

MAX_ITERATIONS: int = 5
"""Maximum reasoning iterations for complex decisions."""

QUIET_MODE: bool = True
"""Suppress excessive LLM output."""


# ── Custom Exception ─────────────────────────────────────────────────────────

class HermesBrainError(Exception):
    """Raised when Hermes brain bridge encounters a fatal error.

    This exception is raised when:
    - LLM API call fails
    - Invalid response format
    - Critical configuration error

    The exception includes context for debugging but never exposes secrets.
    """

    def __init__(self, message: str, error: Exception | None = None) -> None:
        """Initialise HermesBrainError with context.

        Args:
            message: Human-readable error description.
            error: Optional underlying exception for debugging.
        """
        super().__init__(message)
        self.message = message
        self.error = error
        logger.error(
            "hermes_brain_error",
            error_message=message,
            error_type=type(error).__name__ if error else None,
        )


# ── Main Class ───────────────────────────────────────────────────────────────

class HermesBrain:
    """AIAgent wrapper for life_kernel autonomous reasoning.

    Manages AIAgent instance for the kernel's decision-making brain.
    Hermes native memory is ENABLED (connects to Guinevere's P18 memory).
    Kernel context files are ENABLED (world context for decisions).

    This is the brain of the living autonomy kernel — NOT Discord-specific.

    The AIAgent class is imported lazily to avoid breaking test collection
    in environments where the run_agent dependency tree is incomplete.
    Tests can inject a mock agent via the ``agent_factory`` parameter.
    """

    def __init__(
        self,
        llm_config: dict[str, Any] | HermesBrainConfig,
        agent_factory: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        """Initialise Hermes brain bridge with LLM configuration.

        Args:
            llm_config: Either a dict with keys ``base_url``, ``model``,
                ``provider``, ``api_key`` OR a ``HermesBrainConfig`` instance.
                The ``max_iterations`` key is optional in dict form.
            agent_factory: Optional factory for creating AIAgent instances.
                When None (default), uses the lazy ``_load_aiagent`` import.
                Inject a ``MagicMock`` factory in tests.

        Raises:
            HermesBrainError: If required keys missing from llm_config.
        """
        # Normalize config to dict for backwards compatibility
        if isinstance(llm_config, HermesBrainConfig):
            self._llm_config = {
                "base_url": llm_config.base_url,
                "model": llm_config.model,
                "provider": llm_config.provider,
                "api_key": llm_config.api_key,
                "max_iterations": llm_config.max_iterations,
            }
        else:
            self._llm_config = dict(llm_config)  # Ensure we have a dict

        required_keys = {"base_url", "model", "provider"}
        missing = required_keys - self._llm_config.keys()
        if missing:
            raise HermesBrainError(
                f"Missing required LLM config keys: {', '.join(sorted(missing))}",
            )

        self._agent_factory = agent_factory or _default_agent_factory
        self._agent_instance: Any = None  # Lazy-init — use self.agent property
        logger.info(
            "hermes_brain_init",
            model=self._llm_config["model"],
            provider=self._llm_config["provider"],
        )

    @property
    def agent(self) -> Any:
        """Get or create AIAgent instance (lazy import + caching).

        Returns:
            Configured AIAgent instance with tools enabled.

        Raises:
            HermesBrainError: If agent creation fails.
        """
        if self._agent_instance is None:
            try:
                # agent_factory is a callable with the AIAgent constructor
                # signature (base_url=, model=, provider=, ...). In production
                # the default (_default_agent_factory) lazily imports AIAgent and
                # forwards the kwargs; tests inject a MagicMock with the same
                # call signature. Called with the full constructor kwargs.
                self._agent_instance = self._agent_factory(
                    base_url=self._llm_config["base_url"],
                    model=self._llm_config["model"],
                    provider=self._llm_config["provider"],
                    api_key=self._llm_config.get("api_key", ""),
                    skip_memory=False,  # ENABLE memory for kernel context
                    skip_context_files=False,  # ENABLE kernel world context
                    quiet_mode=QUIET_MODE,
                    max_iterations=MAX_ITERATIONS,
                    enabled_toolsets=["core", "web"],  # Kernel needs web + core tools
                    disabled_toolsets=["dangerous", "system"],  # Safety guardrails
                )
            except Exception as exc:
                logger.error(
                    "aiagent_create_failed_detail",
                    exc_type=type(exc).__name__,
                    exc_str=str(exc)[:500],
                    has_9router_key=bool(__import__("os").environ.get("9ROUTER_API_KEY")),
                    has_guinevere_key=bool(__import__("os").environ.get("GUINEVERE_9ROUTER_API_KEY")),
                )
                raise HermesBrainError(
                    "Failed to create AIAgent instance",
                    error=exc,
                ) from exc

        return self._agent_instance

    async def think(
        self,
        user_message: str,
        system_prompt: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Execute autonomous reasoning via AIAgent.

        This is the main decision-making entry point for the kernel.
        Calls AIAgent.run_conversation() for ALL autonomous reasoning.

        Args:
            user_message: The user's input or kernel's query.
            system_prompt: System prompt defining the agent's role.
            conversation_history: Optional conversation history for context.

        Returns:
            Dict with keys:
                - ``final_response`` (str): The assistant's reasoning/output.
                - ``input_tokens`` (int): Tokens consumed from context.
                - ``output_tokens`` (int): Tokens generated.
                - ``total_tokens`` (int): Total tokens used.
                - ``model`` (str): Model name used.
                - ``estimated_cost_usd`` (float): Estimated API cost.

        Raises:
            HermesBrainError: If reasoning fails or returns invalid data.
        """
        if not user_message or not system_prompt:
            raise HermesBrainError(
                "user_message and system_prompt are required",
            )

        history = conversation_history or []

        try:
            result: dict[str, Any] = await asyncio.to_thread(
                self.agent.run_conversation,
                user_message=user_message,
                system_message=system_prompt,
                conversation_history=history,
            )
        except Exception as exc:
            logger.error(
                "hermes_brain_think_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return self._fallback_response(str(exc))

        # Validate response structure
        if not isinstance(result, dict):
            logger.error("hermes_brain_invalid_response_type", type=type(result).__name__)
            return self._fallback_response(
                "AIAgent.run_conversation() must return a dict",
            )

        required_fields = {
            "final_response",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "model",
            "estimated_cost_usd",
        }
        missing = required_fields - result.keys()
        if missing:
            logger.error(
                "hermes_brain_missing_fields",
                missing=sorted(missing),
            )
            return self._fallback_response(
                f"Missing required fields from AIAgent response: {', '.join(sorted(missing))}",
            )

        # Log usage
        logger.info(
            "hermes_brain_think_complete",
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            total_tokens=result["total_tokens"],
            model=result["model"],
            estimated_cost_usd=result["estimated_cost_usd"],
        )

        return result

    def _fallback_response(self, error_message: str) -> dict[str, Any]:
        """Return a safe fallback response when Hermes is unavailable.

        Instead of raising, returns a structured fallback dict so the kernel
        can continue autonomous operation during LLM outages or errors.

        Args:
            error_message: Human-readable error description.

        Returns:
            Fallback dict with the same structure as a successful response,
            plus an ``error`` key for caller detection.
        """
        logger.warning(
            "hermes_brain_fallback_used",
            error_message=error_message,
        )
        return {
            "final_response": f"[Hermes fallback] {error_message}",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "model": self._llm_config.get("model", "unknown"),
            "estimated_cost_usd": 0.0,
            "error": error_message,
        }

    async def think_with_tools(
        self,
        user_message: str,
        system_prompt: str,
        tools: list[Any] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Execute autonomous reasoning with tool execution.

        Variant of ``think()`` that passes tools to the agent.

        Args:
            user_message: The user's input or kernel's query.
            system_prompt: System prompt defining the agent's role.
            tools: Optional list of tools to enable.
            conversation_history: Optional conversation history for context.

        Returns:
            Dict with same structure as ``think()``.

        Raises:
            HermesBrainError: If reasoning fails or returns invalid data.
        """
        if not user_message or not system_prompt:
            raise HermesBrainError(
                "user_message and system_prompt are required",
            )

        history = conversation_history or []

        try:
            result: dict[str, Any] = await asyncio.to_thread(
                self.agent.run_conversation,
                user_message=user_message,
                system_message=system_prompt,
                conversation_history=history,
                tools=tools,
            )
        except Exception as exc:
            logger.error(
                "hermes_brain_think_with_tools_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return self._fallback_response(f"Tool-based reasoning failed: {exc}")

        # Validate response structure (same as think())
        if not isinstance(result, dict):
            logger.error("hermes_brain_invalid_response_type", type=type(result).__name__)
            return self._fallback_response(
                "AIAgent.run_conversation() must return a dict",
            )

        required_fields = {
            "final_response",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "model",
            "estimated_cost_usd",
        }
        missing = required_fields - result.keys()
        if missing:
            logger.error(
                "hermes_brain_missing_fields",
                missing=sorted(missing),
            )
            return self._fallback_response(
                f"Missing required fields from AIAgent response: {', '.join(sorted(missing))}",
            )

        logger.info(
            "hermes_brain_think_with_tools_complete",
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            total_tokens=result["total_tokens"],
            model=result["model"],
            estimated_cost_usd=result["estimated_cost_usd"],
        )

        return result

    async def dispose(self) -> None:
        """Cleanup AIAgent resources.

        This method closes the underlying AIAgent instance if it exists.
        It's safe to call multiple times.
        """
        if self._agent_instance is not None:
            # AIAgent doesn't have explicit close() method,
            # but we can clear the reference to free resources
            self._agent_instance = None
            logger.info("hermes_brain_disposed")
"""LLM Router — Routes requests to appropriate models via 9Router.

Phase 6 primary is ``ds/deepseek-v4-flash`` through 9Router at
``http://localhost:20128/v1``. All HTTP traffic must stay on 9Router; no
direct provider endpoints are permitted.

Cost tracking is mandatory: every successful LLM response flows through
``CostTracker.record_cost`` before the result is returned to the caller.
A cost-tracking failure is *fail-closed* — it raises
``RuntimeError("LLM cost tracking failed")`` and is **not** swallowed by
the provider-fallback chain.

Metrics are emitted for every call attempt:
- ``hermes_llm_calls_total{model,status}`` — per-attempt count.
- ``hermes_llm_latency_seconds`` — per-successful-call latency.
- ``hermes_llm_cost_usd_total`` — per-successful-call cost.
- ``hermes_fallback_activations_total`` — per-fallback-chain transition.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from enum import Enum

import httpx
import structlog

from guinevere.core.services.cost_tracker import CostTracker
from guinevere.core.services.llm_metrics import (
    observe_call,
    observe_cost,
    observe_fallback,
    observe_latency,
)

logger = structlog.get_logger()


# Matches a trailing SSE ``[DONE]`` marker, with or without a space after
# the colon.  Anchored to end-of-string so legitimate streaming payloads
# (e.g. ``data: {...}``) are left untouched.
_SSE_DONE_RE = re.compile(r"data:\s*\[DONE\]\s*$")


def _strip_sse_done(raw: str) -> str:
    """Strip a trailing ``data: [DONE]`` / ``data:[DONE]`` marker.

    9Router v0.4.66+ may append the SSE termination marker to
    non-streaming responses, which breaks ``json.loads``. This helper
    removes both ``data: [DONE]`` and ``data:[DONE]`` variants.
    """
    return _SSE_DONE_RE.sub("", raw).rstrip()


class TaskType(Enum):
    CORE_REASONING = "core"       # Phase 6 primary: ds/deepseek-v4-flash
    SUB_AGENT = "sub_agent"       # ds/deepseek-v4-flash
    FALLBACK = "fallback"         # guinevere combo / graceful degradation


@dataclass
class ModelConfig:
    name: str
    base_url: str
    max_tokens: int
    temperature: float
    cost_per_1k_input: float
    cost_per_1k_output: float


# Phase 6 pricing (USD per 1K tokens). cx/gpt-5.5 is kept as a reference
# pricing snapshot because it is registered as a known-degraded provider
# in 9Router; it is **not** the Phase 6 primary.
PRICING = {
    "cx/gpt-5.5": {"input_per_1k": 0.005, "output_per_1k": 0.03},
    "ds/deepseek-v4-flash": {"input_per_1k": 0.00014, "output_per_1k": 0.00028},
    "guinevere": {"input_per_1k": 0.00014, "output_per_1k": 0.00028},
}


MODELS: dict[TaskType, ModelConfig] = {
    # 9Router uses namespaced model IDs: cx/ (OpenAI Codex), ds/
    # (DeepSeek), etc. ``guinevere`` is the 9Router combo model (no
    # namespace prefix).
    TaskType.CORE_REASONING: ModelConfig(
        name="ds/deepseek-v4-flash",
        base_url="http://localhost:20128/v1",
        # DeepSeek V4 allocates a chunk of max_tokens for reasoning
        # tokens, so a small max_tokens leaves zero budget for actual
        # content.
        max_tokens=8192,
        temperature=0.5,
        cost_per_1k_input=PRICING["ds/deepseek-v4-flash"]["input_per_1k"],
        cost_per_1k_output=PRICING["ds/deepseek-v4-flash"]["output_per_1k"],
    ),
    TaskType.SUB_AGENT: ModelConfig(
        name="ds/deepseek-v4-flash",
        base_url="http://localhost:20128/v1",
        max_tokens=8192,
        temperature=0.5,
        cost_per_1k_input=PRICING["ds/deepseek-v4-flash"]["input_per_1k"],
        cost_per_1k_output=PRICING["ds/deepseek-v4-flash"]["output_per_1k"],
    ),
    TaskType.FALLBACK: ModelConfig(
        name="guinevere",
        base_url="http://localhost:20128/v1",
        max_tokens=8192,
        temperature=0.5,
        cost_per_1k_input=PRICING["guinevere"]["input_per_1k"],
        cost_per_1k_output=PRICING["guinevere"]["output_per_1k"],
    ),
}


class LLMRouter:
    """Routes LLM requests through 9Router with a 3-tier fallback chain.

    Every successful response is recorded by ``CostTracker``. A
    cost-tracking failure is treated as a hard error and re-raised as
    ``RuntimeError("LLM cost tracking failed")`` — the provider-fallback
    chain must not swallow accounting failures.
    """

    def __init__(self, cost_tracker: CostTracker | None = None):
        self.client: httpx.AsyncClient = httpx.AsyncClient(timeout=60.0)
        # Phase 6: CostTracker is mandatory. Callers may inject a
        # pre-configured tracker (e.g. for tests) but the production
        # default wires the canonical Redis DB5 tracker.
        self.cost_tracker: CostTracker = cost_tracker if cost_tracker is not None else CostTracker()

    async def chat(
        self,
        messages: list[dict[str, object]],
        task_type: TaskType = TaskType.CORE_REASONING,
        max_tokens: int | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        """Send a chat completion request with automatic fallback.

        Provider/HTTP/JSON errors trigger the next link in the fallback
        chain. Cost-tracking failures are **not** recoverable via
        fallback and propagate as ``RuntimeError``.
        """
        fallback_chain: list[TaskType]
        if task_type == TaskType.SUB_AGENT:
            fallback_chain = [TaskType.SUB_AGENT, TaskType.FALLBACK]
        else:
            fallback_chain = [task_type, TaskType.SUB_AGENT, TaskType.FALLBACK]

        last_provider_error: BaseException | None = None
        result: dict[str, object] | None = None
        chosen_config: ModelConfig | None = None
        duration: float = 0.0  # set in the success path; 0.0 here keeps the type checker happy

        for idx, model_type in enumerate(fallback_chain):
            config = MODELS[model_type]
            # Provider / HTTP / JSON errors are caught and the chain
            # continues. The `try` block is intentionally narrow so the
            # cost-tracking call below is NOT inside it.
            try:
                request_body: dict[str, object] = {
                    "model": config.name,
                    "messages": messages,
                    "max_tokens": max_tokens or config.max_tokens,
                    "temperature": config.temperature,
                }
                request_body.update(kwargs)
                start_time = time.monotonic()
                response = await self.client.post(
                    f"{config.base_url}/chat/completions",
                    json=request_body,
                )
                _ = response.raise_for_status()
                # Robust SSE strip — handles both ``data: [DONE]`` and
                # ``data:[DONE]`` trailing markers.
                raw = _strip_sse_done(response.text)
                result = json.loads(raw)
                chosen_config = config
                duration = time.monotonic() - start_time
                break
            except Exception as e:
                last_provider_error = e
                observe_call(config.name, "error")
                # If there is a next model in the chain, this is a
                # fallback activation.
                if idx < len(fallback_chain) - 1:
                    next_config = MODELS[fallback_chain[idx + 1]]
                    observe_fallback(config.name, next_config.name)
                logger.warning(
                    "llm_fallback",
                    model=config.name,
                    error=str(e),
                )
                continue

        if result is None or chosen_config is None:
            # All provider attempts exhausted.
            if last_provider_error is not None:
                raise RuntimeError("All LLM providers failed") from last_provider_error
            raise RuntimeError("All LLM providers failed")

        # --- Cost tracking (fail-closed) ---------------------------------
        # Extracted from the provider try/except so a CostTracker error
        # cannot be masked as a provider failure and silently fall
        # through to the next model.
        raw_usage = result.get("usage", {})
        usage: dict[str, object] = raw_usage if isinstance(raw_usage, dict) else {}
        prompt_raw = usage.get("prompt_tokens", 0)
        completion_raw = usage.get("completion_tokens", 0)
        prompt_tokens = int(prompt_raw) if isinstance(prompt_raw, (int, float)) else 0
        completion_tokens = int(completion_raw) if isinstance(completion_raw, (int, float)) else 0

        # Compute cost here for metrics and CostTracker consistency.
        cost_usd = (
            prompt_tokens / 1000 * chosen_config.cost_per_1k_input
            + completion_tokens / 1000 * chosen_config.cost_per_1k_output
        )

        try:
            self.cost_tracker.record_cost(
                model=chosen_config.name,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                cost_per_1k_input=chosen_config.cost_per_1k_input,
                cost_per_1k_output=chosen_config.cost_per_1k_output,
            )
        except Exception as cost_err:
            logger.error(
                "llm_cost_tracking_failed",
                model=chosen_config.name,
                error=str(cost_err),
            )
            raise RuntimeError("LLM cost tracking failed") from cost_err

        # --- Prometheus metrics (success path) ---------------------------
        observe_call(chosen_config.name, "success")
        observe_latency(chosen_config.name, duration)
        observe_cost(chosen_config.name, cost_usd)

        logger.info(
            "llm_request",
            model=chosen_config.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(cost_usd, 6),
        )
        return result

    async def close(self) -> None:
        await self.client.aclose()

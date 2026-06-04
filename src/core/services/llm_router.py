"""LLM Router - Routes requests to appropriate models based on task type."""
import json
import re

import httpx
import structlog
from enum import Enum
from typing import Optional, Union
from dataclasses import dataclass

logger = structlog.get_logger()

class TaskType(Enum):
    CORE_REASONING = "core"       # GPT-5.5
    SUB_AGENT = "sub_agent"       # DeepSeek V4 Flash
    FALLBACK = "fallback"         # Guinevere combo / graceful degradation

@dataclass
class ModelConfig:
    name: str
    base_url: str
    max_tokens: int
    temperature: float
    cost_per_1k_input: float
    cost_per_1k_output: float

MODELS = {
    # 9Router uses namespaced model IDs: cx/ (OpenAI Codex), ds/ (DeepSeek), etc.
    # ``guinevere`` is the 9Router combo model (no namespace prefix).
    TaskType.CORE_REASONING: ModelConfig(
        name="cx/gpt-5.5",
        base_url="http://localhost:20128/v1",
        max_tokens=16384,
        temperature=0.7,
        cost_per_1k_input=0.0025,
        cost_per_1k_output=0.01,
    ),
    TaskType.SUB_AGENT: ModelConfig(
        name="ds/deepseek-v4-flash",
        base_url="http://localhost:20128/v1",
        # DeepSeek V4 allocates a chunk of max_tokens for reasoning tokens,
        # so a small max_tokens leaves zero budget for actual content.
        max_tokens=8192,
        temperature=0.5,
        cost_per_1k_input=0.0001,
        cost_per_1k_output=0.0002,
    ),
    TaskType.FALLBACK: ModelConfig(
        name="guinevere",
        base_url="http://localhost:20128/v1",
        max_tokens=8192,
        temperature=0.5,
        cost_per_1k_input=0.0001,
        cost_per_1k_output=0.0002,
    ),
}

class LLMRouter:
    """Routes LLM requests based on task type with fallback chain."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def chat(self, messages: list[dict], task_type: TaskType = TaskType.CORE_REASONING,
                   max_tokens: Optional[int] = None, **kwargs) -> dict:
        """Send chat completion request with automatic fallback."""
        fallback_chain = [task_type, TaskType.SUB_AGENT, TaskType.FALLBACK]
        if task_type == TaskType.SUB_AGENT:
            fallback_chain = [TaskType.SUB_AGENT, TaskType.FALLBACK]
        
        for model_type in fallback_chain:
            config: Union[ModelConfig, None] = None
            try:
                config = MODELS[model_type]
                response = await self.client.post(
                    f"{config.base_url}/chat/completions",
                    json={
                        "model": config.name,
                        "messages": messages,
                        "max_tokens": max_tokens or config.max_tokens,
                        "temperature": config.temperature,
                        **kwargs,
                    }
                )
                response.raise_for_status()
                # 9Router v0.4.66 appends SSE termination marker to
                # non-streaming responses — strip it before JSON parse.
                raw = response.text
                raw = re.sub(r"data: \[DONE\]\s*$", "", raw)
                result = json.loads(raw)
                logger.info("llm_request", model=config.name,
                           tokens=result.get("usage", {}).get("total_tokens", 0))
                return result
            except Exception as e:
                model_name = config.name if config else model_type.value
                logger.warning("llm_fallback", model=model_name, error=str(e),
                               next_model=fallback_chain[fallback_chain.index(model_type)+1].value
                               if fallback_chain.index(model_type)+1 < len(fallback_chain) else "none")
                continue
        
        raise RuntimeError("All LLM providers failed")
    
    async def close(self):
        await self.client.aclose()
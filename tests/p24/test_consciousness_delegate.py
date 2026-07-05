"""P5 Tests — consciousness delegates to Hermes AIAgent (single brain).

Operator intent (locked): consciousness loop must DELEGATE to Hermes AIAgent,
NOT call LLM itself. _self_prompt() calls agent.chat() (returns str), not
llm_router.chat() (returns dict).

These tests verify the delegate contract:
  - _self_prompt accepts an agent with .chat(message)->str signature
  - _self_prompt returns the str content directly (no dict .get("content"))
  - system+user messages are combined into the agent prompt
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import pytest


class _FakeAIAgent:
    """Fake agent mimicking AIAgent.chat(message) -> str contract.

    Records the message it received and returns a canned string.
    This is a test double for the real Hermes AIAgent (which talks to 9router).
    """

    def __init__(self, response: str = "delegate-pong") -> None:
        self.response = response
        self.call_count = 0
        self.last_message: str | None = None

    def chat(self, message: str, stream_callback: Any = None) -> str:
        self.call_count += 1
        self.last_message = message
        return self.response


@pytest.mark.asyncio
async def test_self_prompt_delegates_to_agent_chat_and_returns_str() -> None:
    """_self_prompt calls agent.chat() and returns the str response directly.

    Before P5: _self_prompt called llm_router.chat(messages, task_type, max_tokens)
    which returned a dict, and extracted .get("content", "").
    After P5: _self_prompt calls agent.chat(message) which returns str.
    """
    from guinevere.consciousness.substrates import _self_prompt

    agent = _FakeAIAgent(response="conscious-thought-from-brain")

    result = await _self_prompt(
        agent,
        system_msg="You are a consciousness substrate.",
        user_msg="What is your current state?",
        max_tokens=64,
    )

    # Contract: agent.chat was called (delegate, not direct LLM)
    assert agent.call_count == 1, f"expected 1 agent.chat call, got {agent.call_count}"
    # Contract: result is the str directly (not dict extraction)
    assert isinstance(result, str), f"expected str, got {type(result).__name__}"
    assert result == "conscious-thought-from-brain"
    # Contract: system + user combined into the agent prompt
    assert "consciousness substrate" in agent.last_message
    assert "current state" in agent.last_message


@pytest.mark.asyncio
async def test_self_prompt_returns_empty_string_on_agent_failure() -> None:
    """If agent.chat raises, _self_prompt must not crash the substrate.

    Consciousness substrates run at second/minute cadence; a single failed
    self-prompt must degrade to empty thought, not kill the substrate.
    """
    from guinevere.consciousness.substrates import _self_prompt

    class _ExplodingAgent:
        def chat(self, message: str, stream_callback: Any = None) -> str:
            raise RuntimeError("9router down")

    agent = _ExplodingAgent()

    result = await _self_prompt(
        agent,
        system_msg="sys",
        user_msg="usr",
        max_tokens=32,
    )

    assert result == "", f"expected empty string on failure, got {result!r}"

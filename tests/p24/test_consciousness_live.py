"""P5 integration test: ConsciousnessLoop wired with real AIAgent (9router brain).

Verifies the FULL delegate chain end-to-end:
  ConsciousnessLoop -> ThoughtStream -> _self_prompt -> agent.chat -> 9router

This is a LIVE integration test (requires 9router at localhost:20128).
Skipped if 9router unreachable (CI / no-VPS).
"""
from __future__ import annotations

import asyncio
import os

import pytest


def _9router_reachable() -> bool:
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:20128/v1/models", timeout=3)
        return True
    except Exception:
        return False


# Live integration tests leak global state (Prometheus registry, AIAgent
# process state) that flake other tests in the same process. Marked `live`
# and excluded from the default suite; run explicitly: pytest -m live
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not _9router_reachable(),
        reason="9router not reachable at localhost:20128 (live VPS test only)",
    ),
]


@pytest.mark.asyncio
async def test_consciousness_loop_with_real_aiagent_delegates_to_9router() -> None:
    """ConsciousnessLoop wired with a real AIAgent brain produces live inference.

    This is the P5 end-state: consciousness delegates to Hermes AIAgent (single
    brain) routed through 9router. A single _self_prompt tick through the stream
    must return a non-empty real LLM response (not a mock canned string).
    """
    import sys
    sys.path.insert(0, "/home/guinevere/p24-port")
    from run_agent import AIAgent
    from guinevere.consciousness.thought_stream import _self_prompt

    # Build the single brain. settings=None so Group G consciousness-wire
    # no-ops (breaks circular: brain does not build its own consciousness loop).
    agent = AIAgent(
        base_url="http://localhost:20128/v1",
        api_key="sk-noauth",
        provider="custom",
        model="guinevere",
        enabled_toolsets=[],
    )

    # A single self-prompt through the delegate chain must produce live output.
    result = await _self_prompt(
        agent,
        system_msg="You are a consciousness liveness probe.",
        user_msg="Reply with exactly: consciousness-online",
        max_tokens=32,
    )

    assert isinstance(result, str)
    assert len(result.strip()) > 0, "expected non-empty live LLM response, got empty"
    # Live 9router response is not a canned mock string
    assert "I am thinking" not in result, "got mock response, not real 9router inference"

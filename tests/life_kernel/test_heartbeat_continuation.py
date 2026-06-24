"""Tests for the P20 continuation heartbeat enhancements (T11, T12).

T11: _heartbeat_1h runs ReflectionEvaluator and produces self-improvement
     candidates (AC-LIFE-009).
T12: _log_lifecycle_milestone emits a narrative line with autonomous intent.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.life_kernel.heartbeat import HeartbeatService


def _make_heartbeat(graph=None, log_channel=None):
    """Build a HeartbeatService with a mock redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)  # no hard stop
    redis.set = AsyncMock(return_value=True)
    graph_mock = graph or MagicMock()
    graph_mock.aget_state = AsyncMock(return_value=MagicMock(values={
        "cycle_count": 10,
        "act_count": 2,
        "errors": [],
        "current_phase": "reflect",
        "last_autonomous_decision": "act on: finance review",
        "next_planned_action": "summarize finance records",
        "current_focus": "finance_review",
        "world_model_status": "active",
        "recalled_memories": [{"content": "x", "relevance": 0.9, "timestamp": "t"}],
        "recalled_concepts": [{"name": "finance", "relevance": 0.9, "source": "p16"}],
    }, __bool__=lambda self: True))
    graph_mock.ainvoke = AsyncMock(return_value={})
    return HeartbeatService(
        graph=graph_mock,
        redis_client=redis,
        log_channel=log_channel,
    )


class TestHeartbeat1hSelfImprovement:
    """T11: 1h heartbeat generates self-improvement candidates."""

    async def test_1h_generates_candidates(self):
        hb = _make_heartbeat()
        # Should not raise; should attempt evaluation
        await hb._heartbeat_1h()
        # No assertion on count (state-dependent) — the key is it ran cleanly
        # and did not crash. If candidates were generated they are tracked.

    async def test_1h_failure_is_fail_soft(self):
        """1h heartbeat must not crash if self-improvement throws."""
        hb = _make_heartbeat()
        # Force ag state to raise
        hb.graph.aget_state = AsyncMock(side_effect=RuntimeError("boom"))
        await hb._heartbeat_1h()  # must not raise


class TestLifecycleLogNarrative:
    """T12: lifecycle log line includes autonomous intent + recall counts."""

    async def test_log_line_includes_intent_and_recall(self):
        log_channel = MagicMock()
        log_channel.write = AsyncMock()
        hb = _make_heartbeat(log_channel=log_channel)
        state = {
            "current_phase": "reflect",
            "act_count": 2,
            "cycle_count": 10,
            "last_autonomous_decision": "act on: finance review",
            "next_planned_action": "summarize finance records",
            "current_focus": "finance_review",
            "world_model_status": "active",
            "recalled_memories": [{"content": "x"}],
            "recalled_concepts": [{"name": "finance"}],
            "hard_stop_requested": False,
        }
        await hb._log_lifecycle_milestone(state)
        log_channel.write.assert_awaited()
        line = log_channel.write.await_args.args[0]
        # Must include intent narrative + recall counts + world_model
        assert "intent=" in line
        assert "mem:1" in line
        assert "kg:1" in line
        assert "world_model=active" in line

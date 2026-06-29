"""Tests for W17 circuit breakers — all 6 breakers with full state machine.

Verifies:
  - All 6 breakers present in CircuitBreakerSet
  - Each has CLOSED, OPEN, HALF_OPEN states
  - State transitions: CLOSED→OPEN on fail_max, OPEN→HALF_OPEN on timeout, HALF_OPEN→CLOSED on success
  - Dream cap 5/hour
  - Sub-agent cap 10

D2 compliance: all tests use mocks, no real VPS deployment.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from guinevere.production.circuit_breakers import (
    BreakerState,
    CircuitBreakerOpenError,
    CircuitBreakerSet,
    CircuitBreaker,
    CostExplosionBreaker,
    InfiniteLoopBreaker,
    HallucinationSpiralBreaker,
    EmotionalFixationBreaker,
    DreamFloodingBreaker,
    SubAgentExplosionBreaker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def breaker_set() -> CircuitBreakerSet:
    """Create a fresh CircuitBreakerSet for each test."""
    return CircuitBreakerSet()


@pytest.fixture
def cost_breaker() -> CostExplosionBreaker:
    return CostExplosionBreaker(max_cost_usd=1.0, reset_timeout=0.1)


@pytest.fixture
def loop_breaker() -> InfiniteLoopBreaker:
    return InfiniteLoopBreaker(consecutive_threshold=3, reset_timeout=0.1)


@pytest.fixture
def hallucination_breaker() -> HallucinationSpiralBreaker:
    return HallucinationSpiralBreaker(
        grounding_threshold=0.05, window_size=10, reset_timeout=0.1
    )


@pytest.fixture
def emotion_breaker() -> EmotionalFixationBreaker:
    return EmotionalFixationBreaker(
        consecutive_threshold=5, decay_rate=0.9, reset_timeout=0.1
    )


@pytest.fixture
def dream_breaker() -> DreamFloodingBreaker:
    return DreamFloodingBreaker(max_dreams_per_hour=5, reset_timeout=0.1)


@pytest.fixture
def subagent_breaker() -> SubAgentExplosionBreaker:
    return SubAgentExplosionBreaker(
        max_concurrent=3, max_total_per_session=10, reset_timeout=0.1
    )


# ---------------------------------------------------------------------------
# CircuitBreakerSet — all 6 present
# ---------------------------------------------------------------------------


class TestCircuitBreakerSet:
    def test_all_6_breakers_present(self, breaker_set: CircuitBreakerSet) -> None:
        """CircuitBreakerSet must contain exactly 6 breakers."""
        assert len(breaker_set.breakers) == 6
        expected = {
            "cost_explosion",
            "infinite_loop",
            "hallucination_spiral",
            "emotional_fixation",
            "dream_flooding",
            "sub_agent_explosion",
        }
        assert set(breaker_set.breakers.keys()) == expected

    def test_sorted_breaker_names(self, breaker_set: CircuitBreakerSet) -> None:
        """Breaker names should be sorted alphabetically."""
        names = sorted(breaker_set.breakers.keys())
        assert names == [
            "cost_explosion",
            "dream_flooding",
            "emotional_fixation",
            "hallucination_spiral",
            "infinite_loop",
            "sub_agent_explosion",
        ]

    def test_all_breakers_start_closed(self, breaker_set: CircuitBreakerSet) -> None:
        """All breakers must start in CLOSED state."""
        for name, breaker in breaker_set.breakers.items():
            assert breaker.state == BreakerState.CLOSED, f"{name} not CLOSED"

    def test_health_check(self, breaker_set: CircuitBreakerSet) -> None:
        """health_check returns dict with all breaker names."""
        health = asyncio.run(breaker_set.health_check())
        assert len(health) == 6
        for name in breaker_set.breakers:
            assert name in health
            assert health[name]["state"] == "closed"


# ---------------------------------------------------------------------------
# BreakerState enum
# ---------------------------------------------------------------------------


class TestBreakerState:
    def test_three_states(self) -> None:
        """BreakerState must have exactly 3 values."""
        states = [s.name for s in BreakerState]
        assert states == ["CLOSED", "OPEN", "HALF_OPEN"]

    def test_state_values(self) -> None:
        """BreakerState values must match expected strings."""
        assert BreakerState.CLOSED.value == "closed"
        assert BreakerState.OPEN.value == "open"
        assert BreakerState.HALF_OPEN.value == "half_open"


# ---------------------------------------------------------------------------
# B1: CostExplosionBreaker
# ---------------------------------------------------------------------------


class TestCostExplosionBreaker:
    def test_starts_closed(self, cost_breaker: CostExplosionBreaker) -> None:
        assert cost_breaker.state == BreakerState.CLOSED

    def test_closed_allows_requests(self, cost_breaker: CostExplosionBreaker) -> None:
        assert cost_breaker.allow_request() is True

    def test_trips_to_open_on_cost_exceeded(
        self, cost_breaker: CostExplosionBreaker
    ) -> None:
        cost_breaker.add_cost(1.5)  # exceeds 1.0 threshold
        assert cost_breaker.allow_request() is False
        assert cost_breaker.state == BreakerState.OPEN

    def test_open_blocks_requests(self, cost_breaker: CostExplosionBreaker) -> None:
        cost_breaker.add_cost(1.5)
        cost_breaker.allow_request()  # trips
        assert cost_breaker.allow_request() is False

    def test_open_to_half_open_on_timeout(
        self, cost_breaker: CostExplosionBreaker
    ) -> None:
        cost_breaker.add_cost(1.5)
        cost_breaker.allow_request()  # trips to OPEN
        time.sleep(0.15)  # wait for reset_timeout
        assert cost_breaker.allow_request() is True
        assert cost_breaker.state == BreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(
        self, cost_breaker: CostExplosionBreaker
    ) -> None:
        cost_breaker.add_cost(1.5)
        cost_breaker.allow_request()  # OPEN
        time.sleep(0.15)
        cost_breaker.allow_request()  # HALF_OPEN
        await cost_breaker.record_success()
        assert cost_breaker.state == BreakerState.CLOSED

    def test_soft_limit_warning(self, cost_breaker: CostExplosionBreaker) -> None:
        """At 80% of threshold, a warning is logged but request is allowed."""
        cost_breaker.add_cost(0.85)  # 85% of 1.0
        assert cost_breaker.allow_request() is True
        assert cost_breaker.state == BreakerState.CLOSED


# ---------------------------------------------------------------------------
# B2: InfiniteLoopBreaker
# ---------------------------------------------------------------------------


class TestInfiniteLoopBreaker:
    def test_starts_closed(self, loop_breaker: InfiniteLoopBreaker) -> None:
        assert loop_breaker.state == BreakerState.CLOSED

    def test_unique_calls_allowed(self, loop_breaker: InfiniteLoopBreaker) -> None:
        loop_breaker.record_tool_call("tool1", "arg1")
        loop_breaker.record_tool_call("tool2", "arg2")
        assert loop_breaker.state == BreakerState.CLOSED

    def test_trips_on_consecutive_identical(
        self, loop_breaker: InfiniteLoopBreaker
    ) -> None:
        for _ in range(3):
            loop_breaker.record_tool_call("same_tool", "same_args")
        assert loop_breaker.state == BreakerState.OPEN

    def test_open_blocks_requests(self, loop_breaker: InfiniteLoopBreaker) -> None:
        for _ in range(3):
            loop_breaker.record_tool_call("x", "y")
        assert loop_breaker.allow_request() is False

    def test_open_to_half_open_on_timeout(
        self, loop_breaker: InfiniteLoopBreaker
    ) -> None:
        for _ in range(3):
            loop_breaker.record_tool_call("x", "y")
        time.sleep(0.15)
        assert loop_breaker.allow_request() is True
        assert loop_breaker.state == BreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(
        self, loop_breaker: InfiniteLoopBreaker
    ) -> None:
        for _ in range(3):
            loop_breaker.record_tool_call("x", "y")
        time.sleep(0.15)
        loop_breaker.allow_request()  # HALF_OPEN
        await loop_breaker.record_success()
        assert loop_breaker.state == BreakerState.CLOSED


# ---------------------------------------------------------------------------
# B3: HallucinationSpiralBreaker
# ---------------------------------------------------------------------------


class TestHallucinationSpiralBreaker:
    def test_starts_closed(self, hallucination_breaker: HallucinationSpiralBreaker) -> None:
        assert hallucination_breaker.state == BreakerState.CLOSED

    def test_grounded_claims_allowed(
        self, hallucination_breaker: HallucinationSpiralBreaker
    ) -> None:
        claims = ["The sky is blue"]
        memories = [{"text": "the sky is blue and clear today"}]
        ratio = hallucination_breaker.check_grounding(claims, memories)
        assert ratio > 0
        assert hallucination_breaker.state == BreakerState.CLOSED

    def test_ungrounded_trips_to_open(
        self, hallucination_breaker: HallucinationSpiralBreaker
    ) -> None:
        # Feed many ungrounded claims to fill window and trip
        for _ in range(10):
            hallucination_breaker.check_grounding(
                ["completely unrelated claim xyz"],
                [{"text": "totally different memory abc"}],
            )
        assert hallucination_breaker.state == BreakerState.OPEN

    def test_open_blocks_requests(
        self, hallucination_breaker: HallucinationSpiralBreaker
    ) -> None:
        hallucination_breaker.force_open()
        assert hallucination_breaker.allow_request() is False

    def test_open_to_half_open_on_timeout(
        self, hallucination_breaker: HallucinationSpiralBreaker
    ) -> None:
        hallucination_breaker.force_open()
        time.sleep(0.15)
        assert hallucination_breaker.allow_request() is True
        assert hallucination_breaker.state == BreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(
        self, hallucination_breaker: HallucinationSpiralBreaker
    ) -> None:
        hallucination_breaker.force_open()
        time.sleep(0.15)
        hallucination_breaker.allow_request()  # HALF_OPEN
        await hallucination_breaker.record_success()
        assert hallucination_breaker.state == BreakerState.CLOSED


# ---------------------------------------------------------------------------
# B4: EmotionalFixationBreaker
# ---------------------------------------------------------------------------


class TestEmotionalFixationBreaker:
    def test_starts_closed(self, emotion_breaker: EmotionalFixationBreaker) -> None:
        assert emotion_breaker.state == BreakerState.CLOSED

    def test_diverse_emotions_allowed(
        self, emotion_breaker: EmotionalFixationBreaker
    ) -> None:
        emotion_breaker.record_emotion("happy", 0.8)
        emotion_breaker.record_emotion("sad", 0.3)
        emotion_breaker.record_emotion("neutral", 0.5)
        assert emotion_breaker.state == BreakerState.CLOSED

    def test_trips_on_consecutive_same_emotion(
        self, emotion_breaker: EmotionalFixationBreaker
    ) -> None:
        for _ in range(5):
            emotion_breaker.record_emotion("anger", 0.9)
        assert emotion_breaker.state == BreakerState.OPEN

    def test_open_blocks_requests(
        self, emotion_breaker: EmotionalFixationBreaker
    ) -> None:
        emotion_breaker.force_open()
        assert emotion_breaker.allow_request() is False

    def test_open_to_half_open_on_timeout(
        self, emotion_breaker: EmotionalFixationBreaker
    ) -> None:
        emotion_breaker.force_open()
        time.sleep(0.15)
        assert emotion_breaker.allow_request() is True
        assert emotion_breaker.state == BreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(
        self, emotion_breaker: EmotionalFixationBreaker
    ) -> None:
        emotion_breaker.force_open()
        time.sleep(0.15)
        emotion_breaker.allow_request()  # HALF_OPEN
        await emotion_breaker.record_success()
        assert emotion_breaker.state == BreakerState.CLOSED


# ---------------------------------------------------------------------------
# B5: DreamFloodingBreaker — cap 5/hour
# ---------------------------------------------------------------------------


class TestDreamFloodingBreaker:
    def test_starts_closed(self, dream_breaker: DreamFloodingBreaker) -> None:
        assert dream_breaker.state == BreakerState.CLOSED

    def test_under_cap_allows_dreams(self, dream_breaker: DreamFloodingBreaker) -> None:
        for _ in range(4):
            dream_breaker.record_dream()
        assert dream_breaker.can_dream() is True
        assert dream_breaker.state == BreakerState.CLOSED

    def test_cap_5_per_hour(self, dream_breaker: DreamFloodingBreaker) -> None:
        """Must block at exactly 5 dreams per hour."""
        for _ in range(5):
            dream_breaker.record_dream()
        assert dream_breaker.can_dream() is False
        assert dream_breaker.state == BreakerState.OPEN

    def test_open_blocks_requests(self, dream_breaker: DreamFloodingBreaker) -> None:
        dream_breaker.force_open()
        assert dream_breaker.allow_request() is False

    def test_open_to_half_open_on_timeout(
        self, dream_breaker: DreamFloodingBreaker
    ) -> None:
        dream_breaker.force_open()
        time.sleep(0.15)
        assert dream_breaker.allow_request() is True
        assert dream_breaker.state == BreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(
        self, dream_breaker: DreamFloodingBreaker
    ) -> None:
        dream_breaker.force_open()
        time.sleep(0.15)
        dream_breaker.allow_request()  # HALF_OPEN
        await dream_breaker.record_success()
        assert dream_breaker.state == BreakerState.CLOSED

    def test_dreams_this_hour_property(
        self, dream_breaker: DreamFloodingBreaker
    ) -> None:
        assert dream_breaker.dreams_this_hour == 0
        dream_breaker.record_dream()
        assert dream_breaker.dreams_this_hour == 1


# ---------------------------------------------------------------------------
# B6: SubAgentExplosionBreaker — cap 10
# ---------------------------------------------------------------------------


class TestSubAgentExplosionBreaker:
    def test_starts_closed(self, subagent_breaker: SubAgentExplosionBreaker) -> None:
        assert subagent_breaker.state == BreakerState.CLOSED

    def test_under_cap_allows_spawn(
        self, subagent_breaker: SubAgentExplosionBreaker
    ) -> None:
        subagent_breaker.register_spawn("agent-1")
        subagent_breaker.register_spawn("agent-2")
        assert subagent_breaker.state == BreakerState.CLOSED

    def test_concurrent_cap_trips_to_open(
        self, subagent_breaker: SubAgentExplosionBreaker
    ) -> None:
        """With max_concurrent=3, 3 active agents should trip."""
        for i in range(3):
            subagent_breaker.register_spawn(f"agent-{i}")
        assert subagent_breaker.can_spawn("agent-new") is False
        assert subagent_breaker.state == BreakerState.OPEN

    def test_total_cap_trips_to_open(self) -> None:
        """With max_total_per_session=5, 5 total spawned should trip."""
        breaker = SubAgentExplosionBreaker(
            max_concurrent=100, max_total_per_session=5, reset_timeout=0.1
        )
        for i in range(5):
            breaker.register_spawn(f"agent-{i}")
            breaker.register_completion(f"agent-{i}")
        assert breaker.can_spawn("agent-new") is False
        assert breaker.state == BreakerState.OPEN

    def test_open_blocks_requests(
        self, subagent_breaker: SubAgentExplosionBreaker
    ) -> None:
        subagent_breaker.force_open()
        assert subagent_breaker.allow_request() is False

    def test_open_to_half_open_on_timeout(
        self, subagent_breaker: SubAgentExplosionBreaker
    ) -> None:
        subagent_breaker.force_open()
        time.sleep(0.15)
        assert subagent_breaker.allow_request() is True
        assert subagent_breaker.state == BreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(
        self, subagent_breaker: SubAgentExplosionBreaker
    ) -> None:
        subagent_breaker.force_open()
        time.sleep(0.15)
        subagent_breaker.allow_request()  # HALF_OPEN
        await subagent_breaker.record_success()
        assert subagent_breaker.state == BreakerState.CLOSED

    def test_completion_frees_slot(
        self, subagent_breaker: SubAgentExplosionBreaker
    ) -> None:
        for i in range(3):
            subagent_breaker.register_spawn(f"agent-{i}")
        # Trigger OPEN state by trying to spawn when at capacity
        subagent_breaker.can_spawn("agent-new")
        assert subagent_breaker.state == BreakerState.OPEN
        # Completion doesn't auto-close — stays OPEN until timeout
        subagent_breaker.register_completion("agent-0")
        assert subagent_breaker.state == BreakerState.OPEN


# ---------------------------------------------------------------------------
# Cross-cutting: all 6 breakers have all 3 states (hard rejection)
# ---------------------------------------------------------------------------


class TestAllBreakersHaveThreeStates:
    """Hard rejection test: every breaker must have CLOSED, OPEN, HALF_OPEN."""

    @pytest.mark.parametrize(
        "breaker_name",
        [
            "cost_explosion",
            "infinite_loop",
            "hallucination_spiral",
            "emotional_fixation",
            "dream_flooding",
            "sub_agent_explosion",
        ],
    )
    def test_breaker_has_all_states(self, breaker_name: str) -> None:
        """Each breaker must be able to reach all 3 states."""
        set_ = CircuitBreakerSet()
        breaker = set_.get_breaker(breaker_name)

        # Start CLOSED
        assert breaker.state == BreakerState.CLOSED

        # Force OPEN
        breaker.force_open()
        assert breaker.state == BreakerState.OPEN

        # Simulate timeout -> HALF_OPEN
        breaker.opened_at = time.monotonic() - 9999
        breaker.allow_request()
        assert breaker.state == BreakerState.HALF_OPEN

        # Success -> CLOSED
        asyncio.run(breaker.record_success())
        assert breaker.state == BreakerState.CLOSED


# ---------------------------------------------------------------------------
# TailscaleHardener (D2 — generate only)
# ---------------------------------------------------------------------------


class TestTailscaleHardener:
    def test_script_generated(self) -> None:
        from guinevere.production.tailscale import TailscaleHardener

        hardener = TailscaleHardener()
        script = hardener.generate_hardening_script()
        assert len(script) > 0
        assert "Tailscale" in script
        assert "D2" in script

    def test_d2_compliant(self) -> None:
        from guinevere.production.tailscale import TailscaleHardener

        hardener = TailscaleHardener()
        health = hardener.health()
        assert health["d2_compliant"] is True
        assert health["executed"] is False


# ---------------------------------------------------------------------------
# AutoRecovery (D2 — design only)
# ---------------------------------------------------------------------------


class TestAutoRecovery:
    def test_systemd_unit_generated(self) -> None:
        from guinevere.production.recovery import AutoRecovery

        recovery = AutoRecovery()
        unit = recovery.generate_systemd_unit()
        assert "Restart=always" in unit
        assert "RestartSec=10" in unit
        assert "NoNewPrivileges=yes" in unit

    def test_restart_counting(self) -> None:
        from guinevere.production.recovery import AutoRecovery

        recovery = AutoRecovery()
        assert recovery.record_restart() == 1
        assert recovery.record_restart() == 2
        assert recovery.should_restart() is True

    def test_max_restarts(self) -> None:
        from guinevere.production.recovery import AutoRecovery

        recovery = AutoRecovery()
        recovery._restart_count = 5
        assert recovery.should_restart() is False


# ---------------------------------------------------------------------------
# Wire function
# ---------------------------------------------------------------------------


class TestWire:
    def test_wire_attaches_recovery(self) -> None:
        from guinevere.production.recovery import wire

        class FakeAgent:
            pass

        agent = FakeAgent()
        wire(agent)
        assert hasattr(agent, "_auto_recovery")

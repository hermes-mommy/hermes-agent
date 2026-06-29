"""W6 Tests — Consciousness Loop (M3).

Tests:
  - loop starts and runs 7 substrates (mock)
  - 7 substrates present in registry
  - mock self-prompt tick produces a thought
  - failure isolation (one substrate crashing does not kill others)
  - on_session_start / on_session_end hooks fire

D3: MockLLMRouter only — NO real LLM calls.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest


# ── MockLLMRouter (D3) ──────────────────────────────────────


class MockLLMRouter:
    """Deterministic mock LLM router for D3 testing.

    Returns a canned response for every chat() call.
    Tracks call count for assertions.
    """

    def __init__(self, response: str = '{"thought": "I am alive."}') -> None:
        self.response = response
        self.call_count = 0
        self.last_messages: list[dict[str, str]] = []

    async def chat(
        self,
        messages: list[dict[str, str]],
        task_type: str = "CORE_REASONING",
        max_tokens: int = 256,
    ) -> dict[str, Any]:
        """Return the canned response."""
        self.call_count += 1
        self.last_messages = messages
        return {
            "content": self.response,
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "model": "mock-llm",
        }


# ── fixtures ────────────────────────────────────────────────


@pytest.fixture
def mock_router() -> MockLLMRouter:
    return MockLLMRouter()


@pytest.fixture
def loop(mock_router: MockLLMRouter) -> Any:
    """Create a ConsciousnessLoop with mock router."""
    from guinevere.consciousness.loop import ConsciousnessLoop

    return ConsciousnessLoop(llm_router=mock_router)


# ── tests ───────────────────────────────────────────────────


class TestConsciousnessImports:
    """Verify all required imports resolve."""

    def test_import_loop_and_state(self) -> None:
        from guinevere.consciousness import ConsciousnessLoop, ConsciousnessState

        assert ConsciousnessLoop is not None
        assert ConsciousnessState is not None

    def test_import_infra(self) -> None:
        from guinevere.consciousness.infra import (
            AuditWriter,
            IterationBudget,
            ReflectionExtractor,
            TestingGate,
        )

        assert AuditWriter is not None
        assert IterationBudget is not None
        assert ReflectionExtractor is not None
        assert TestingGate is not None


class TestConsciousnessLoop:
    """Core ConsciousnessLoop behaviour."""

    def test_seven_substrates_present(self, loop: Any) -> None:
        """The loop must have exactly 7 substrates."""
        assert len(loop.substrate_names) == 7

    def test_substrate_names_match_adr063(self, loop: Any) -> None:
        """Substrate names must match the ADR-063 specification."""
        expected = {
            "heartbeat",
            "active_cognition",
            "reflection",
            "strategic_planning",
            "dreaming",
            "metacognition",
            "emotion_driven",
        }
        assert set(loop.substrate_names) == expected

    def test_loop_starts_and_stops(self, loop: Any) -> None:
        """Loop starts via run(), can be stopped via on_session_end()."""

        async def _test() -> None:
            loop.on_session_start(session_id="test-start-stop")
            assert loop.is_running

            # Start the loop as a task.
            run_task = asyncio.create_task(loop.run())

            # Give substrates a moment to start.
            await asyncio.sleep(0.2)

            # Stop the loop.
            loop.on_session_end()
            run_task.cancel()
            try:
                await run_task
            except asyncio.CancelledError:
                pass

            assert not loop.is_running

        asyncio.run(_test())

    def test_substrate_statuses_update(self, loop: Any) -> None:
        """Substrate statuses should update during execution."""

        async def _test() -> None:
            loop.on_session_start(session_id="test-statuses")
            run_task = asyncio.create_task(loop.run())
            await asyncio.sleep(0.3)

            # At least some substrates should have been active.
            statuses = loop.state.substrate_statuses
            # After a tick, heartbeat should have been running.
            # (It may have returned to IDLE by now, but it was set.)
            assert "heartbeat" in statuses

            loop.on_session_end()
            run_task.cancel()
            try:
                await run_task
            except asyncio.CancelledError:
                pass

        asyncio.run(_test())


class TestSelfPrompting:
    """Test that mock self-prompting produces thoughts."""

    def test_mock_self_prompt_produces_thought(self, loop: Any, mock_router: MockLLMRouter) -> None:
        """A tick of the heartbeat substrate should produce a recorded thought."""

        async def _test() -> None:
            loop.on_session_start(session_id="test-thought")
            run_task = asyncio.create_task(loop.run())
            await asyncio.sleep(0.5)  # Heartbeat ticks every 1s

            # The mock router should have been called.
            assert mock_router.call_count > 0

            # Thoughts should have been recorded.
            thoughts = loop.state.recent_thoughts(5)
            assert len(thoughts) > 0

            loop.on_session_end()
            run_task.cancel()
            try:
                await run_task
            except asyncio.CancelledError:
                pass

        asyncio.run(_test())


class TestFailureIsolation:
    """Test that one substrate crashing does not kill others."""

    def test_crashing_substrate_does_not_kill_others(self, mock_router: MockLLMRouter) -> None:
        """If active_cognition raises, heartbeat and others keep running."""

        async def _test() -> None:
            from guinevere.consciousness.loop import ConsciousnessLoop
            from guinevere.consciousness.state import SubstrateStatus

            cl = ConsciousnessLoop(llm_router=mock_router)

            # Monkey-patch active_cognition to always raise.
            # Registry entries are zero-arg partials, so replacement must also be zero-arg.
            async def _crashing_cognition() -> None:
                raise RuntimeError("Simulated cognition crash")

            # Replace in registry.
            cl._registry["active_cognition"] = _crashing_cognition

            cl.on_session_start(session_id="test-failure-isolation")
            run_task = asyncio.create_task(cl.run())
            await asyncio.sleep(0.5)  # Let substrates run.

            # active_cognition should be FAILED.
            assert cl.state.substrate_statuses["active_cognition"] == SubstrateStatus.FAILED

            # heartbeat should still be running (not failed).
            assert cl.state.substrate_statuses["heartbeat"] != SubstrateStatus.FAILED

            # metacognition should still be running (not failed).
            assert cl.state.substrate_statuses["metacognition"] != SubstrateStatus.FAILED

            # The loop should still be running (not crashed).
            assert cl.is_running

            cl.on_session_end()
            run_task.cancel()
            try:
                await run_task
            except asyncio.CancelledError:
                pass

        asyncio.run(_test())


class TestSessionHooks:
    """Test on_session_start / on_session_end lifecycle."""

    def test_on_session_start_sets_state(self, loop: Any) -> None:
        """on_session_start should initialise the state."""
        loop.on_session_start(session_id="test-hook-start")
        assert loop.state.started_at is not None
        assert loop.state.session_id == "test-hook-start"
        assert loop.is_running

    def test_on_session_end_clears_state(self, loop: Any) -> None:
        """on_session_end should signal shutdown."""
        loop.on_session_start(session_id="test-hook-end")
        assert loop.is_running
        loop.on_session_end()
        assert not loop.is_running

    def test_full_lifecycle(self, loop: Any, mock_router: MockLLMRouter) -> None:
        """Full start -> run -> end lifecycle without errors."""

        async def _test() -> None:
            loop.on_session_start(session_id="test-full-lifecycle")
            run_task = asyncio.create_task(loop.run())
            await asyncio.sleep(0.3)

            assert mock_router.call_count > 0
            assert loop.is_running

            loop.on_session_end()
            run_task.cancel()
            try:
                await run_task
            except asyncio.CancelledError:
                pass

            assert not loop.is_running

        asyncio.run(_test())


class TestAffectVector:
    """Test AffectVector EWMA updates."""

    def test_ewma_update(self) -> None:
        from guinevere.consciousness.state import AffectVector

        av = AffectVector()
        assert av.valence == 0.0

        av.ewma_update({"valence": 0.8, "curiosity": 1.0}, lam=0.3)
        # valence: 0.3 * 0.8 + 0.7 * 0.0 = 0.24
        assert abs(av.valence - 0.24) < 0.01
        # curiosity: 0.3 * 1.0 + 0.7 * 0.5 = 0.65
        assert abs(av.curiosity - 0.65) < 0.01

    def test_as_dict(self) -> None:
        from guinevere.consciousness.state import AffectVector

        av = AffectVector()
        d = av.as_dict()
        assert "valence" in d
        assert "arousal" in d
        assert len(d) == 6


class TestDreamJournal:
    """Test DreamJournalEntry and ConsciousnessState."""

    def test_add_dream_entry(self) -> None:
        from guinevere.consciousness.state import (
            ConsciousnessState,
            DreamJournalEntry,
        )
        from datetime import datetime, timezone

        state = ConsciousnessState()
        entry = DreamJournalEntry(
            timestamp=datetime.now(timezone.utc),
            scenario="What if I had rested?",
            counterfactual="I would have been more creative",
            insight="Rest fuels creativity",
        )
        state.add_dream_entry(entry)
        assert len(state.dream_journal) == 1
        assert state.dream_journal[0].insight == "Rest fuels creativity"

    def test_dream_journal_capped_at_50(self) -> None:
        from guinevere.consciousness.state import (
            ConsciousnessState,
            DreamJournalEntry,
        )
        from datetime import datetime, timezone

        state = ConsciousnessState()
        for i in range(60):
            state.add_dream_entry(
                DreamJournalEntry(
                    timestamp=datetime.now(timezone.utc),
                    scenario=f"scenario-{i}",
                    counterfactual=f"cf-{i}",
                    insight=f"insight-{i}",
                )
            )
        assert len(state.dream_journal) == 50


class TestSnapshot:
    """Test ConsciousnessState.snapshot()."""

    def test_snapshot_returns_dict(self) -> None:
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        snap = state.snapshot()
        assert "affect" in snap
        assert "self_story" in snap
        assert "substrate_statuses" in snap
        assert "thought_count" in snap

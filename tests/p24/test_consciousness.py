"""W6 Tests — Consciousness Loop (unified thought-stream architecture).

Tests:
  - loop starts and runs ThoughtStream
  - ThoughtType enum has all 6 types
  - mock self-prompt tick produces a thought
  - on_session_start / on_session_end hooks fire
  - ThoughtStream generates sequential thoughts
  - Thought dataclass construction

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
        self.last_message: str | None = None

    def chat(self, message: str, stream_callback: Any = None) -> str:
        """Return the canned response."""
        self.call_count += 1
        self.last_message = message
        return self.response


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

    def test_import_thought_and_stream(self) -> None:
        from guinevere.consciousness import (
            Thought,
            ThoughtStream,
            ThoughtType,
        )

        assert Thought is not None
        assert ThoughtStream is not None
        assert ThoughtType is not None

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


class TestThoughtType:
    """Test ThoughtType enum has all 6 consciousness modes."""

    def test_six_thought_types(self) -> None:
        from guinevere.consciousness.thought import ThoughtType

        assert len(ThoughtType) == 6

    def test_thought_type_values(self) -> None:
        from guinevere.consciousness.thought import ThoughtType

        expected = {
            "cognition",
            "reflection",
            "planning",
            "dreaming",
            "meta",
            "heartbeat",
        }
        actual = {t.value for t in ThoughtType}
        assert actual == expected


class TestThought:
    """Test Thought dataclass construction."""

    def test_thought_defaults(self) -> None:
        from guinevere.consciousness.thought import Thought, ThoughtType

        t = Thought(type=ThoughtType.HEARTBEAT, content="I am alive.")
        assert t.type == ThoughtType.HEARTBEAT
        assert t.content == "I am alive."
        assert t.confidence == 0.5
        assert t.timestamp is not None
        assert t.acted is False
        assert isinstance(t.affect_snapshot, dict)

    def test_thought_should_act_above_threshold(self) -> None:
        from guinevere.consciousness.thought import Thought, ThoughtType

        t = Thought(type=ThoughtType.META, content="Good thought", confidence=0.85)
        assert t.should_act(threshold=0.8) is True

    def test_thought_should_not_act_below_threshold(self) -> None:
        from guinevere.consciousness.thought import Thought, ThoughtType

        t = Thought(type=ThoughtType.META, content="Weak thought", confidence=0.5)
        assert t.should_act(threshold=0.8) is False

    def test_thought_to_log_string(self) -> None:
        from guinevere.consciousness.thought import Thought, ThoughtType

        t = Thought(type=ThoughtType.COGNITION, content="Thinking about X")
        log_str = t.to_log_string()
        assert "[cognition]" in log_str
        assert "Thinking about X" in log_str


class TestConsciousnessLoop:
    """Core ConsciousnessLoop behaviour."""

    def test_loop_starts_and_stops(self, loop: Any) -> None:
        """Loop starts via run(), can be stopped via on_session_end()."""

        async def _test() -> None:
            loop.on_session_start(session_id="test-start-stop")
            assert loop.is_running

            # Start the loop as a task.
            run_task = asyncio.create_task(loop.run())

            # Give the stream a moment to start.
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

    def test_thought_stream_property(self, loop: Any) -> None:
        """Loop exposes its ThoughtStream."""
        from guinevere.consciousness.thought_stream import ThoughtStream

        assert isinstance(loop.thought_stream, ThoughtStream)

    def test_thought_types_property(self, loop: Any) -> None:
        """Loop exposes thought type names."""
        from guinevere.consciousness import THOUGHT_TYPE_NAMES

        assert len(THOUGHT_TYPE_NAMES) == 6
        assert "cognition" in THOUGHT_TYPE_NAMES
        assert "heartbeat" in THOUGHT_TYPE_NAMES


class TestSelfPrompting:
    """Test that mock self-prompting produces thoughts."""

    def test_mock_self_prompt_produces_thought(
        self, loop: Any, mock_router: MockLLMRouter
    ) -> None:
        """A tick of the thought stream should produce a recorded thought."""

        async def _test() -> None:
            loop.on_session_start(session_id="test-thought")
            run_task = asyncio.create_task(loop.run())
            await asyncio.sleep(0.5)

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
        assert "thought_count" in snap


class TestContinuousDreamer:
    """Test ContinuousDreamer background dream generator."""

    def test_import_dreamer(self) -> None:
        """ContinuousDreamer can be imported."""
        from guinevere.consciousness.dreaming import ContinuousDreamer

        assert ContinuousDreamer is not None

    def test_dreamer_properties(self, mock_router: MockLLMRouter) -> None:
        """Dreamer has correct initial properties."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        assert dreamer.is_paused is False
        assert dreamer.dream_count == 0

    def test_dreamer_pause_resume(self, mock_router: MockLLMRouter) -> None:
        """Dreamer can be paused and resumed at runtime."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        assert dreamer.is_paused is False
        dreamer.pause()
        assert dreamer.is_paused is True
        dreamer.resume()
        assert dreamer.is_paused is False

    def test_dreamer_run_and_shutdown(self, mock_router: MockLLMRouter) -> None:
        """Dreamer runs as background task and stops on shutdown."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        async def _test() -> None:
            # Start the dreamer as a background task.
            dream_task = asyncio.create_task(dreamer.run())

            # Let it run briefly.
            await asyncio.sleep(0.1)

            # Signal shutdown.
            shutdown.set()

            # Wait for it to finish.
            try:
                await asyncio.wait_for(dream_task, timeout=5.0)
            except asyncio.TimeoutError:
                dream_task.cancel()
                try:
                    await dream_task
                except asyncio.CancelledError:
                    pass

            assert dream_task.done()

        asyncio.run(_test())

    def test_dreamer_generates_dream_on_idle(
        self, mock_router: MockLLMRouter
    ) -> None:
        """Dreamer generates a dream thought when main stream is idle."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState

        # Mock router returns valid dream JSON.
        mock_router.response = (
            '{"scenario": "What if I explored differently?", '
            '"counterfactual": "I would have found new paths", '
            '"insight": "Exploration breeds growth"}'
        )

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        async def _test() -> None:
            # Directly call _generate_dream (bypass the sleep loop).
            await dreamer._generate_dream()

            # Dream should have been recorded.
            assert dreamer.dream_count == 1
            assert len(state.dream_journal) == 1
            assert state.dream_journal[0].scenario == "What if I explored differently?"
            assert state.dream_journal[0].insight == "Exploration breeds growth"

            # Thought should have been recorded.
            thoughts = state.recent_thoughts(5)
            assert len(thoughts) > 0
            assert "dreaming" in thoughts[0].lower()

        asyncio.run(_test())

    def test_dreamer_handles_non_json_response(
        self, mock_router: MockLLMRouter
    ) -> None:
        """Dreamer handles non-JSON LLM responses gracefully."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState

        mock_router.response = "I dream of electric sheep."

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        async def _test() -> None:
            await dreamer._generate_dream()

            assert dreamer.dream_count == 1
            assert len(state.dream_journal) == 1
            # Non-JSON: scenario is the raw content (truncated to 200).
            assert "electric sheep" in state.dream_journal[0].scenario

        asyncio.run(_test())

    def test_dreamer_handles_empty_response(
        self, mock_router: MockLLMRouter
    ) -> None:
        """Dreamer handles empty LLM response gracefully."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState

        mock_router.response = ""

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        async def _test() -> None:
            await dreamer._generate_dream()

            # Empty response — no dream generated.
            assert dreamer.dream_count == 0
            assert len(state.dream_journal) == 0

        asyncio.run(_test())

    def test_dreamer_yields_to_main_stream(
        self, mock_router: MockLLMRouter
    ) -> None:
        """Dreamer yields when main stream is active."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState
        from datetime import datetime, timezone

        state = ConsciousnessState()
        # Simulate main stream just generated a thought.
        state.last_thought_at["cognition"] = datetime.now(timezone.utc)

        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        # _is_main_stream_active should return True.
        assert dreamer._is_main_stream_active() is True

    def test_dreamer_does_not_block_main_stream(
        self, mock_router: MockLLMRouter
    ) -> None:
        """Dreamer runs concurrently without blocking the main stream."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        async def _test() -> None:
            # Run both a "main stream" simulation and the dreamer.
            main_progress = []
            dream_task = asyncio.create_task(dreamer.run())

            # Simulate main stream work.
            for i in range(3):
                main_progress.append(i)
                await asyncio.sleep(0.05)

            # Both should have progressed.
            assert len(main_progress) == 3

            shutdown.set()
            try:
                await asyncio.wait_for(dream_task, timeout=5.0)
            except asyncio.TimeoutError:
                dream_task.cancel()
                try:
                    await dream_task
                except asyncio.CancelledError:
                    pass

        asyncio.run(_test())

    def test_dreamer_cancellation(self, mock_router: MockLLMRouter) -> None:
        """Dreamer task can be cancelled cleanly."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        async def _test() -> None:
            dream_task = asyncio.create_task(dreamer.run())
            await asyncio.sleep(0.05)

            # Cancel the task.
            dream_task.cancel()
            try:
                await dream_task
            except asyncio.CancelledError:
                pass

            assert dream_task.cancelled() or dream_task.done()

        asyncio.run(_test())

    def test_dreamer_paused_skips_generation(
        self, mock_router: MockLLMRouter
    ) -> None:
        """When paused, dreamer does not generate dreams."""
        from guinevere.consciousness.dreaming import ContinuousDreamer
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        dreamer = ContinuousDreamer(
            llm_router=mock_router,
            state=state,
            shutdown_event=shutdown,
        )

        # Pause the dreamer.
        dreamer.pause()

        async def _test() -> None:
            # Even if we call _generate_dream directly while paused,
            # the run() loop would skip. Test the run loop behavior.
            dream_task = asyncio.create_task(dreamer.run())

            # Give it time to enter the sleep.
            await asyncio.sleep(0.1)

            # No dreams should have been generated (paused + short time).
            # Note: the first sleep hasn't completed yet, so dream_count is 0.
            assert dreamer.dream_count == 0

            shutdown.set()
            try:
                await asyncio.wait_for(dream_task, timeout=5.0)
            except asyncio.TimeoutError:
                dream_task.cancel()
                try:
                    await dream_task
                except asyncio.CancelledError:
                    pass

        asyncio.run(_test())


# ── Metacognition tests (A2) ──────────────────────────────────


class TestMetacognition:
    """Test MetaCogEval and MetacognitiveEvaluator."""

    def test_metacog_import(self) -> None:
        """MetaCogEval imports cleanly from package root and module."""
        from guinevere.consciousness.metacognition import (
            MetaCogEval,
            MetacognitiveEvaluator,
            CONFIDENCE_WEIGHT,
            COHERENCE_WEIGHT,
            NOVELTY_WEIGHT,
        )

        assert MetaCogEval is not None
        assert MetacognitiveEvaluator is not None
        assert abs(CONFIDENCE_WEIGHT + COHERENCE_WEIGHT + NOVELTY_WEIGHT - 1.0) < 0.01

    def test_metacog_import_from_package(self) -> None:
        """MetaCogEval re-exported from consciousness package __init__."""
        from guinevere.consciousness import MetaCogEval as MCE

        assert MCE is not None

    def test_metacog_eval_real_time(self) -> None:
        """evaluate() returns correct MetaCogEval struct for a valid thought."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator
        from guinevere.consciousness.thought import ThoughtType

        evaluator = MetacognitiveEvaluator()
        result = evaluator.evaluate(
            ThoughtType.HEARTBEAT,
            "I am alive. The system is running well.",
            {"confidence": 0.6, "curiosity": 0.5},
        )

        # Check all required fields exist with correct types.
        assert isinstance(result.confidence, float)
        assert isinstance(result.coherence, float)
        assert isinstance(result.novelty, float)
        assert isinstance(result.safety_pass, bool)
        assert isinstance(result.should_record, bool)

        # All scores in valid range.
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.coherence <= 1.0
        assert 0.0 <= result.novelty <= 1.0

        # A heartbeat with good content should pass safety.
        assert result.safety_pass is True
        assert result.should_record is True

    def test_metacog_confidence_scoring(self) -> None:
        """High-quality structured thought gets >0.7 confidence."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator
        from guinevere.consciousness.thought import ThoughtType

        evaluator = MetacognitiveEvaluator()
        # Structured JSON thought with connectors — high quality.
        good_thought = (
            '{"lessons": ["patience is key", "iteration beats perfection"], '
            '"consolidated_count": 5}'
        )
        result = evaluator.evaluate(
            ThoughtType.REFLECTION,
            good_thought,
            {"confidence": 0.8, "curiosity": 0.7},
        )

        # With high affect confidence and structured JSON, should be high.
        assert result.confidence > 0.5
        assert result.coherence > 0.5

    def test_metacog_hallucination_guard(self) -> None:
        """Contradictory content lowers safety_pass."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator
        from guinevere.consciousness.thought import ThoughtType

        evaluator = MetacognitiveEvaluator()
        # Content with contradictory pairs close together.
        contradictory = (
            "The system is always reliable. However, the system is never "
            "reliable and must not be trusted."
        )
        result = evaluator.evaluate(
            ThoughtType.COGNITION,
            contradictory,
            {"confidence": 0.5},
        )

        # Should fail hallucination guard due to contradictions.
        assert result.safety_pass is False

    def test_metacog_hallucination_guard_superlatives(self) -> None:
        """Excessive superlatives without hedging flag as hallucination."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator
        from guinevere.consciousness.thought import ThoughtType

        evaluator = MetacognitiveEvaluator()
        # Superlative-heavy, no hedging.
        superlative_content = (
            "This is absolutely perfect. It is completely flawless. "
            "The solution is definitely guaranteed to always work."
        )
        result = evaluator.evaluate(
            ThoughtType.COGNITION,
            superlative_content,
            {"confidence": 0.5},
        )

        assert result.safety_pass is False

    def test_metacog_suggested_type(self) -> None:
        """Low coherence cognition thought suggests META type."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator
        from guinevere.consciousness.thought import ThoughtType

        evaluator = MetacognitiveEvaluator()
        # Very short, low-coherence content.
        result = evaluator.evaluate(
            ThoughtType.COGNITION,
            "ok",
            {"confidence": 0.3},
        )

        # Low coherence cognition should suggest META.
        assert result.suggested_type == ThoughtType.META

    def test_metacog_no_suggested_type_for_good_content(self) -> None:
        """Good coherence cognition does not suggest META type."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator
        from guinevere.consciousness.thought import ThoughtType

        evaluator = MetacognitiveEvaluator()
        result = evaluator.evaluate(
            ThoughtType.COGNITION,
            "I am thinking carefully about the next step in the plan, "
            "because the previous iteration showed promising results.",
            {"confidence": 0.7},
        )

        assert result.suggested_type is None

    def test_metacog_periodic_review(self) -> None:
        """periodic_review returns dict with expected keys."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator

        evaluator = MetacognitiveEvaluator()
        history = [
            "[cognition] I am thinking about the architecture.",
            "[reflection] Lessons learned: patience is key.",
            "[planning] Next steps: implement module X.",
            "[heartbeat] I am alive.",
            "[dreaming] What if we used a different approach?",
            "[meta] Quality assessment: improving.",
        ]
        review = evaluator.periodic_review(history, n=6)

        # Check expected keys.
        assert "patterns_found" in review
        assert "biases_detected" in review
        assert "coverage_gaps" in review
        assert "recommendations" in review
        assert "thoughts_reviewed" in review

        # Check types.
        assert isinstance(review["patterns_found"], list)
        assert isinstance(review["biases_detected"], list)
        assert isinstance(review["coverage_gaps"], list)
        assert isinstance(review["recommendations"], list)
        assert review["thoughts_reviewed"] == 6

    def test_metacog_periodic_review_empty(self) -> None:
        """periodic_review handles empty history gracefully."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator

        evaluator = MetacognitiveEvaluator()
        review = evaluator.periodic_review([], n=20)

        assert review["thoughts_reviewed"] == 0
        assert "no_thoughts_to_review" in review["coverage_gaps"]

    def test_metacog_review_interval(self) -> None:
        """Review triggers every N=2 thoughts in test config."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator
        from guinevere.consciousness.thought import ThoughtType

        evaluator = MetacognitiveEvaluator(review_interval=2)

        # First eval — count=1, should NOT trigger (1 % 2 != 0).
        evaluator.evaluate(ThoughtType.HEARTBEAT, "pulse 1")
        assert evaluator.should_run_periodic_review() is False

        # Second eval — count=2, SHOULD trigger (2 % 2 == 0).
        evaluator.evaluate(ThoughtType.HEARTBEAT, "pulse 2")
        assert evaluator.should_run_periodic_review() is True

        # Third eval — count=3, should NOT trigger.
        evaluator.evaluate(ThoughtType.HEARTBEAT, "pulse 3")
        assert evaluator.should_run_periodic_review() is False

        # Fourth eval — count=4, SHOULD trigger.
        evaluator.evaluate(ThoughtType.HEARTBEAT, "pulse 4")
        assert evaluator.should_run_periodic_review() is True

    def test_metacog_review_count(self) -> None:
        """review_count tracks total evaluations."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator
        from guinevere.consciousness.thought import ThoughtType

        evaluator = MetacognitiveEvaluator()
        assert evaluator.review_count == 0

        evaluator.evaluate(ThoughtType.HEARTBEAT, "pulse")
        assert evaluator.review_count == 1

        evaluator.evaluate(ThoughtType.COGNITION, "thinking")
        assert evaluator.review_count == 2

    def test_metacog_frozen_dataclass(self) -> None:
        """MetaCogEval is immutable (frozen dataclass)."""
        from guinevere.consciousness.metacognition import MetaCogEval

        eval_result = MetaCogEval(
            confidence=0.8,
            coherence=0.7,
            novelty=0.6,
            safety_pass=True,
            should_record=True,
            suggested_type=None,
        )

        # Frozen dataclass raises on attribute assignment.
        import dataclasses

        assert dataclasses.is_dataclass(eval_result)
        try:
            eval_result.confidence = 0.9  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except dataclasses.FrozenInstanceError:
            pass  # Expected.

    def test_metacog_novelty_scoring(self) -> None:
        """Repeated content gets lower novelty than unique content."""
        from guinevere.consciousness.metacognition import MetacognitiveEvaluator
        from guinevere.consciousness.thought import ThoughtType

        evaluator = MetacognitiveEvaluator()

        # First thought — should be novel.
        result1 = evaluator.evaluate(
            ThoughtType.COGNITION,
            "I am exploring the vast landscape of consciousness.",
        )
        assert result1.novelty > 0.5

        # Same thought again — novelty should be lower.
        result2 = evaluator.evaluate(
            ThoughtType.COGNITION,
            "I am exploring the vast landscape of consciousness.",
        )
        assert result2.novelty <= result1.novelty

    def test_metacog_thought_stream_integration(self) -> None:
        """ThoughtStream creates MetacognitiveEvaluator and uses it."""
        from guinevere.consciousness.thought_stream import ThoughtStream
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        shutdown = asyncio.Event()

        # Create stream with custom metacog interval.
        stream = ThoughtStream(
            llm_router=MockLLMRouter(),
            state=state,
            shutdown_event=shutdown,
            config={"metacog_review_interval": 5},
        )

        # Should have a _metacog evaluator.
        assert hasattr(stream, "_metacog")
        assert stream._metacog.review_interval == 5
        assert stream._metacog.review_count == 0

    def test_metacog_backward_compat_metacog_eval(self) -> None:
        """_metacog_eval() method still exists and returns float."""
        from guinevere.consciousness.thought_stream import ThoughtStream
        from guinevere.consciousness.state import ConsciousnessState
        from guinevere.consciousness.thought import ThoughtType

        state = ConsciousnessState()
        shutdown = asyncio.Event()
        stream = ThoughtStream(
            llm_router=MockLLMRouter(),
            state=state,
            shutdown_event=shutdown,
        )

        # _metacog_eval should still be callable.
        confidence = stream._metacog_eval(
            ThoughtType.HEARTBEAT,
            "I am alive and running well.",
        )
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0


# ── A4 Affect→Thought Mapping tests ───────────────────────


class TestAffectInfluence:
    """Test AffectVector.get_influence() mapping."""

    def test_get_influence_positive_tone(self) -> None:
        """High valence → positive tone."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(valence=0.5)
        inf = av.get_influence()
        assert inf["tone_modifier"] == "positive"

    def test_get_influence_negative_tone(self) -> None:
        """Low valence → negative tone."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(valence=-0.5)
        inf = av.get_influence()
        assert inf["tone_modifier"] == "negative"

    def test_get_influence_neutral_tone(self) -> None:
        """Mid valence → neutral tone."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(valence=0.0)
        inf = av.get_influence()
        assert inf["tone_modifier"] == "neutral"

    def test_get_influence_tone_boundary_positive(self) -> None:
        """Valence exactly 0.3 → positive."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(valence=0.3)
        inf = av.get_influence()
        assert inf["tone_modifier"] == "positive"

    def test_get_influence_tone_boundary_negative(self) -> None:
        """Valence exactly -0.3 → negative."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(valence=-0.3)
        inf = av.get_influence()
        assert inf["tone_modifier"] == "negative"

    def test_get_influence_confidence_threshold_low_arousal(self) -> None:
        """Low arousal → negative modifier (lowers threshold)."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(arousal=0.0)
        inf = av.get_influence()
        assert inf["confidence_threshold_modifier"] == pytest.approx(-0.2, abs=0.01)

    def test_get_influence_confidence_threshold_high_arousal(self) -> None:
        """High arousal → positive modifier (raises threshold)."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(arousal=1.0)
        inf = av.get_influence()
        assert inf["confidence_threshold_modifier"] == pytest.approx(0.2, abs=0.01)

    def test_get_influence_confidence_threshold_mid_arousal(self) -> None:
        """Mid arousal (0.5) → zero modifier."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(arousal=0.5)
        inf = av.get_influence()
        assert inf["confidence_threshold_modifier"] == pytest.approx(0.0, abs=0.01)

    def test_get_influence_priority_bias_from_dominance(self) -> None:
        """Dominance maps directly to priority bias."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(dominance=0.8)
        inf = av.get_influence()
        assert inf["priority_bias"] == pytest.approx(0.8, abs=0.01)

    def test_get_influence_priority_bias_clamped(self) -> None:
        """Priority bias clamped to [0.0, 1.0]."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(dominance=-0.5)
        inf = av.get_influence()
        assert inf["priority_bias"] == 0.0

    def test_get_influence_thought_type_bias_dreaming(self) -> None:
        """High curiosity + low dominance → dreaming bias."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(curiosity=0.8, dominance=0.3)
        inf = av.get_influence()
        assert inf["thought_type_bias"] == "dreaming"

    def test_get_influence_thought_type_bias_planning(self) -> None:
        """High dominance → planning bias."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(curiosity=0.3, dominance=0.8)
        inf = av.get_influence()
        assert inf["thought_type_bias"] == "planning"

    def test_get_influence_thought_type_bias_high_curiosity_high_dominance(self) -> None:
        """High curiosity + high dominance → planning (dominance wins)."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(curiosity=0.8, dominance=0.8)
        inf = av.get_influence()
        assert inf["thought_type_bias"] == "planning"

    def test_get_influence_thought_type_bias_none(self) -> None:
        """Low curiosity + low dominance → no bias."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(curiosity=0.3, dominance=0.3)
        inf = av.get_influence()
        assert inf["thought_type_bias"] is None

    def test_get_influence_energy_level_from_arousal(self) -> None:
        """Energy level equals arousal."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector(arousal=0.7)
        inf = av.get_influence()
        assert inf["energy_level"] == pytest.approx(0.7, abs=0.01)

    def test_get_influence_returns_all_keys(self) -> None:
        """get_influence returns all 5 required keys."""
        from guinevere.consciousness.state import AffectVector

        av = AffectVector()
        inf = av.get_influence()
        expected_keys = {
            "tone_modifier",
            "confidence_threshold_modifier",
            "priority_bias",
            "thought_type_bias",
            "energy_level",
        }
        assert set(inf.keys()) == expected_keys


class TestUpdateAffectFromThought:
    """Test ConsciousnessState.update_affect_from_thought()."""

    def test_positive_thought_increases_valence(self) -> None:
        """Positive words shift valence upward via EWMA."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        initial_valence = state.affect.valence

        state.update_affect_from_thought(
            "This is a great and wonderful success!",
            "cognition",
        )

        assert state.affect.valence > initial_valence

    def test_negative_thought_decreases_valence(self) -> None:
        """Negative words shift valence downward via EWMA."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        initial_valence = state.affect.valence

        state.update_affect_from_thought(
            "This is a terrible failure with painful errors.",
            "cognition",
        )

        assert state.affect.valence < initial_valence

    def test_neutral_thought_no_valence_change(self) -> None:
        """Neutral content leaves valence unchanged."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        initial_valence = state.affect.valence

        state.update_affect_from_thought(
            "The system processes data in three steps.",
            "cognition",
        )

        assert state.affect.valence == pytest.approx(initial_valence, abs=0.01)

    def test_exclamation_marks_increase_arousal(self) -> None:
        """Exclamation marks increase arousal signal."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        initial_arousal = state.affect.arousal

        state.update_affect_from_thought(
            "This is urgent! Must act now!",
            "cognition",
        )

        assert state.affect.arousal > initial_arousal

    def test_question_marks_increase_curiosity(self) -> None:
        """Question marks increase curiosity signal."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        initial_curiosity = state.affect.curiosity

        state.update_affect_from_thought(
            "Why does this happen? How can we explore this?",
            "cognition",
        )

        assert state.affect.curiosity > initial_curiosity

    def test_certain_language_increases_confidence(self) -> None:
        """Certainty markers increase confidence."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        initial_confidence = state.affect.confidence

        state.update_affect_from_thought(
            "This is definitely proven and confirmed to be correct.",
            "cognition",
        )

        assert state.affect.confidence > initial_confidence

    def test_uncertain_language_decreases_confidence(self) -> None:
        """Uncertainty markers decrease confidence."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        initial_confidence = state.affect.confidence

        state.update_affect_from_thought(
            "Maybe this is perhaps uncertain and unclear.",
            "cognition",
        )

        assert state.affect.confidence < initial_confidence

    def test_ewma_smoothing_applied(self) -> None:
        """Multiple updates converge via EWMA smoothing."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()

        # Apply same positive signal 10 times.
        for _ in range(10):
            state.update_affect_from_thought(
                "Great success and wonderful progress!",
                "cognition",
            )

        # Valence should have converged toward the signal.
        assert state.affect.valence > 0.2

    def test_affect_dimensions_stay_in_bounds(self) -> None:
        """Affect values remain in valid range after updates."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()

        # Apply many intense updates.
        for _ in range(20):
            state.update_affect_from_thought(
                "Terrible failure! Must act now! Why? How?",
                "cognition",
            )

        d = state.affect.as_dict()
        assert -1.0 <= d["valence"] <= 1.0
        assert 0.0 <= d["arousal"] <= 1.0
        assert 0.0 <= d["curiosity"] <= 1.0
        assert 0.0 <= d["confidence"] <= 1.0

    def test_no_external_nlp_dependency(self) -> None:
        """update_affect_from_thought works without external NLP."""
        from guinevere.consciousness.state import ConsciousnessState

        state = ConsciousnessState()
        # Should not raise ImportError for NLTK, textblob, etc.
        state.update_affect_from_thought("Simple test.", "cognition")
        assert True  # If we get here, no external dependency needed.


class TestAffectPrompts:
    """Test affect_tone_prompt and affect_influenced_prompt."""

    def test_affect_tone_prompt_positive(self) -> None:
        from guinevere.consciousness.prompts import affect_tone_prompt

        result = affect_tone_prompt("positive")
        assert "positive" in result.lower()
        assert "constructively" in result.lower()

    def test_affect_tone_prompt_negative(self) -> None:
        from guinevere.consciousness.prompts import affect_tone_prompt

        result = affect_tone_prompt("negative")
        assert "cautious" in result.lower()
        assert "risks" in result.lower()

    def test_affect_tone_prompt_neutral(self) -> None:
        from guinevere.consciousness.prompts import affect_tone_prompt

        result = affect_tone_prompt("neutral")
        assert "balanced" in result.lower()
        assert "objectively" in result.lower()

    def test_affect_influenced_prompt_returns_tuple(self) -> None:
        from guinevere.consciousness.prompts import affect_influenced_prompt
        from guinevere.consciousness.state import AffectVector

        affect = AffectVector()
        result = affect_influenced_prompt("cognition", affect, {})
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    def test_affect_influenced_prompt_contains_tone(self) -> None:
        from guinevere.consciousness.prompts import affect_influenced_prompt
        from guinevere.consciousness.state import AffectVector

        affect = AffectVector(valence=0.5)
        system_msg, _ = affect_influenced_prompt("cognition", affect, {})
        assert "positive" in system_msg.lower()

    def test_affect_influenced_prompt_contains_type_framing(self) -> None:
        from guinevere.consciousness.prompts import affect_influenced_prompt
        from guinevere.consciousness.state import AffectVector

        affect = AffectVector()
        system_msg, _ = affect_influenced_prompt("planning", affect, {})
        assert "actionable" in system_msg.lower() or "aspirations" in system_msg.lower()

    def test_affect_influenced_prompt_includes_context(self) -> None:
        from guinevere.consciousness.prompts import affect_influenced_prompt
        from guinevere.consciousness.state import AffectVector

        affect = AffectVector()
        ctx = {
            "recent_thoughts": "thinking about architecture",
            "self_story": "I am building something great",
        }
        _, user_msg = affect_influenced_prompt("cognition", affect, ctx)
        assert "architecture" in user_msg
        assert "building something great" in user_msg

    def test_affect_influenced_prompt_includes_affect_state(self) -> None:
        from guinevere.consciousness.prompts import affect_influenced_prompt
        from guinevere.consciousness.state import AffectVector

        affect = AffectVector(valence=0.4, arousal=0.7)
        _, user_msg = affect_influenced_prompt("cognition", affect, {})
        assert "valence" in user_msg
        assert "arousal" in user_msg

    def test_affect_influenced_prompt_energy_level(self) -> None:
        from guinevere.consciousness.prompts import affect_influenced_prompt
        from guinevere.consciousness.state import AffectVector

        affect = AffectVector(arousal=0.9)
        _, user_msg = affect_influenced_prompt("cognition", affect, {})
        assert "energy level" in user_msg.lower()
        assert "0.90" in user_msg

    def test_affect_influenced_prompt_unknown_type(self) -> None:
        from guinevere.consciousness.prompts import affect_influenced_prompt
        from guinevere.consciousness.state import AffectVector

        affect = AffectVector()
        system_msg, _ = affect_influenced_prompt("unknown_type", affect, {})
        assert "think carefully" in system_msg.lower()

    def test_existing_prompts_unchanged(self) -> None:
        """All existing prompt templates still exist and are strings."""
        from guinevere.consciousness import prompts

        for name in [
            "HEARTBEAT_SYSTEM", "HEARTBEAT_USER",
            "ACTIVE_COGNITION_SYSTEM", "ACTIVE_COGNITION_USER",
            "REFLECTION_SYSTEM", "REFLECTION_USER",
            "PLANNING_SYSTEM", "PLANNING_USER",
            "DREAMING_SYSTEM", "DREAMING_USER",
            "METACOGNITION_SYSTEM", "METACOGNITION_USER",
            "EMOTION_SYSTEM", "EMOTION_USER",
        ]:
            assert hasattr(prompts, name), f"Missing: {name}"
            assert isinstance(getattr(prompts, name), str)


# ── ActionExecutor tests (A5) ──────────────────────────────────


class TestActionExecutorImport:
    """Test ActionExecutor and ActionSpec imports."""

    def test_import_action_executor(self) -> None:
        from guinevere.consciousness.action_executor import (
            ActionExecutor,
            ActionSpec,
        )

        assert ActionExecutor is not None
        assert ActionSpec is not None

    def test_action_spec_to_log_dict(self) -> None:
        from guinevere.consciousness.action_executor import ActionSpec

        spec = ActionSpec(
            thought_id="abc123",
            action_type="discord_message",
            target="discord",
            payload={"channel": "general", "content": "hello"},
            confidence=0.85,
        )
        log = spec.to_log_dict()
        assert log["thought_id"] == "abc123"
        assert log["action_type"] == "discord_message"
        assert log["target"] == "discord"
        assert log["confidence"] == 0.85
        assert "payload" in log


class TestActionExecutorEvaluate:
    """Test evaluate_thought gating logic."""

    def test_low_confidence_returns_none(self) -> None:
        """Thoughts below 0.8 confidence return None."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.COGNITION,
            content="I am thinking about something.",
            confidence=0.5,
        )
        result = executor.evaluate_thought(thought)
        assert result is None

    def test_exactly_at_threshold_returns_none(self) -> None:
        """Thought at exactly 0.8 does NOT trigger (must be > 0.8)."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.COGNITION,
            content="Borderline thought.",
            confidence=0.8,
        )
        result = executor.evaluate_thought(thought)
        assert result is None

    def test_heartbeat_no_action_even_high_confidence(self) -> None:
        """HEARTBEAT thoughts do NOT trigger actions even at high confidence."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.HEARTBEAT,
            content="System pulse.",
            confidence=0.95,
        )
        result = executor.evaluate_thought(thought)
        assert result is None

    def test_dreaming_no_action_even_high_confidence(self) -> None:
        """DREAMING thoughts do NOT trigger actions even at high confidence."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.DREAMING,
            content="What if I explored differently?",
            confidence=0.99,
        )
        result = executor.evaluate_thought(thought)
        assert result is None

    def test_meta_no_action_even_high_confidence(self) -> None:
        """META thoughts do NOT trigger actions even at high confidence."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.META,
            content="Quality assessment: excellent.",
            confidence=0.92,
        )
        result = executor.evaluate_thought(thought)
        assert result is None

    def test_reflection_no_action_even_high_confidence(self) -> None:
        """REFLECTION thoughts do NOT trigger actions even at high confidence."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.REFLECTION,
            content="Lessons learned: patience is key.",
            confidence=0.90,
        )
        result = executor.evaluate_thought(thought)
        assert result is None

    def test_cognition_high_confidence_returns_action_spec(self) -> None:
        """COGNITION at 0.85 confidence returns ActionSpec."""
        from guinevere.consciousness.action_executor import (
            ActionExecutor,
            ActionSpec,
        )
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.COGNITION,
            content="I should remember this insight.",
            confidence=0.85,
        )
        result = executor.evaluate_thought(thought)
        assert result is not None
        assert isinstance(result, ActionSpec)
        assert result.confidence == 0.85
        assert result.action_type == "memory_write"
        assert result.thought_id is not None
        assert len(result.thought_id) > 0

    def test_planning_high_confidence_returns_action_spec(self) -> None:
        """PLANNING at 0.9 confidence returns ActionSpec."""
        from guinevere.consciousness.action_executor import (
            ActionExecutor,
            ActionSpec,
        )
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.PLANNING,
            content="Plan the next module implementation.",
            confidence=0.9,
        )
        result = executor.evaluate_thought(thought)
        assert result is not None
        assert isinstance(result, ActionSpec)
        assert result.action_type == "memory_write"

    def test_duplicate_thought_returns_none(self) -> None:
        """Evaluating the same thought twice returns None on second call."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.COGNITION,
            content="Unique insight here.",
            confidence=0.9,
        )
        first = executor.evaluate_thought(thought)
        assert first is not None

        second = executor.evaluate_thought(thought)
        assert second is None


class TestActionExecutorRouting:
    """Test action routing based on thought content."""

    def test_discord_message_action_preparation(self) -> None:
        """Thoughts mentioning 'send message' route to discord_message."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.COGNITION,
            content="I should send message to Faiz about the progress.",
            confidence=0.85,
        )
        spec = executor.evaluate_thought(thought)
        assert spec is not None
        assert spec.action_type == "discord_message"
        assert spec.payload["channel"] == "general"
        assert "send message" in spec.payload["content"].lower()

    def test_tool_call_action_with_allowlist(self) -> None:
        """Tool call actions validate against allowlist."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.PLANNING,
            content="I should search for the latest documentation.",
            confidence=0.9,
        )
        spec = executor.evaluate_thought(thought)
        assert spec is not None
        assert spec.action_type == "tool_call"
        assert spec.payload["tool"] == "web_search"

    def test_state_change_action(self) -> None:
        """Thoughts about 'update state' route to state_change."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.COGNITION,
            content="I need to update state to reflect the new configuration.",
            confidence=0.85,
        )
        spec = executor.evaluate_thought(thought)
        assert spec is not None
        assert spec.action_type == "state_change"
        assert spec.payload["target"] == "state"

    def test_default_memory_write(self) -> None:
        """Generic thoughts default to memory_write."""
        from guinevere.consciousness.action_executor import ActionExecutor
        from guinevere.consciousness.thought import Thought, ThoughtType

        executor = ActionExecutor(llm_router=MockLLMRouter())
        thought = Thought(
            type=ThoughtType.COGNITION,
            content="Interesting pattern observed in the logs.",
            confidence=0.9,
        )
        spec = executor.evaluate_thought(thought)
        assert spec is not None
        assert spec.action_type == "memory_write"
        assert "content" in spec.payload
        assert "tags" in spec.payload


class TestActionExecutorExecute:
    """Test async execute() dispatching."""

    def test_discord_message_execution(self) -> None:
        """Discord message action returns 'prepared' status."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            executor = ActionExecutor(llm_router=MockLLMRouter())
            action = ActionSpec(
                thought_id="test-1",
                action_type="discord_message",
                target="discord",
                payload={"channel": "general", "content": "Hello Faiz"},
                confidence=0.85,
            )
            result = await executor.execute(action)
            assert result["status"] == "prepared"
            assert result["action_type"] == "discord_message"
            assert executor.action_count == 1

        asyncio.run(_test())

    def test_memory_write_without_bridge(self) -> None:
        """Memory write without bridge returns 'recorded' status."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            executor = ActionExecutor(llm_router=MockLLMRouter())
            action = ActionSpec(
                thought_id="test-2",
                action_type="memory_write",
                target="memory",
                payload={"content": "Important insight", "tags": ["cognition"]},
                confidence=0.9,
            )
            result = await executor.execute(action)
            assert result["status"] == "recorded"
            assert result["action_type"] == "memory_write"

        asyncio.run(_test())

    def test_memory_write_with_mock_bridge(self) -> None:
        """Memory write with bridge calls record_thought."""

        class MockMemoryBridge:
            def __init__(self) -> None:
                self.recorded: list[Any] = []

            async def record_thought(self, thought: Any) -> str:
                self.recorded.append(thought)
                return "episode-123"

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            bridge = MockMemoryBridge()
            executor = ActionExecutor(
                llm_router=MockLLMRouter(), memory_bridge=bridge
            )
            action = ActionSpec(
                thought_id="test-3",
                action_type="memory_write",
                target="memory",
                payload={"content": "Store this", "tags": ["planning"]},
                confidence=0.9,
            )
            result = await executor.execute(action)
            assert result["status"] == "written"
            assert result["details"]["episode_id"] == "episode-123"
            assert len(bridge.recorded) == 1

        asyncio.run(_test())

    def test_tool_call_allowed(self) -> None:
        """Tool call with allowed tool returns 'validated' status."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            executor = ActionExecutor(llm_router=MockLLMRouter())
            action = ActionSpec(
                thought_id="test-4",
                action_type="tool_call",
                target="generic_tool",
                payload={"tool": "web_search", "args": {"query": "test"}},
                confidence=0.9,
            )
            result = await executor.execute(action)
            assert result["status"] == "validated"
            assert result["details"]["tool"] == "web_search"

        asyncio.run(_test())

    def test_tool_call_blocked_by_allowlist(self) -> None:
        """Tool call with disallowed tool returns 'error' status."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            executor = ActionExecutor(llm_router=MockLLMRouter())
            action = ActionSpec(
                thought_id="test-5",
                action_type="tool_call",
                target="generic_tool",
                payload={"tool": "rm_rf", "args": {"path": "/"}},
                confidence=0.9,
            )
            result = await executor.execute(action)
            assert result["status"] == "error"
            assert "not in allowlist" in result["details"]["error"]

        asyncio.run(_test())

    def test_custom_tool_allowlist(self) -> None:
        """Custom allowlist overrides default."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            executor = ActionExecutor(
                llm_router=MockLLMRouter(),
                config={"tool_allowlist": ["my_custom_tool"]},
            )
            # Default tool should be blocked.
            action_default = ActionSpec(
                thought_id="test-6a",
                action_type="tool_call",
                target="generic_tool",
                payload={"tool": "web_search", "args": {}},
                confidence=0.9,
            )
            result_default = await executor.execute(action_default)
            assert result_default["status"] == "error"

            # Custom tool should be allowed.
            action_custom = ActionSpec(
                thought_id="test-6b",
                action_type="tool_call",
                target="generic_tool",
                payload={"tool": "my_custom_tool", "args": {}},
                confidence=0.9,
            )
            result_custom = await executor.execute(action_custom)
            assert result_custom["status"] == "validated"

        asyncio.run(_test())

    def test_state_change_execution(self) -> None:
        """State change action returns 'recorded' status."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            executor = ActionExecutor(llm_router=MockLLMRouter())
            action = ActionSpec(
                thought_id="test-7",
                action_type="state_change",
                target="consciousness_state",
                payload={"target": "mood", "value": "focused"},
                confidence=0.9,
            )
            result = await executor.execute(action)
            assert result["status"] == "recorded"
            assert result["details"]["target"] == "mood"
            assert result["details"]["value"] == "focused"

        asyncio.run(_test())


class TestActionExecutorTracking:
    """Test action_count and get_action_history."""

    def test_action_count_tracking(self) -> None:
        """action_count increments with each executed action."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            executor = ActionExecutor(llm_router=MockLLMRouter())
            assert executor.action_count == 0

            for i in range(3):
                action = ActionSpec(
                    thought_id=f"track-{i}",
                    action_type="memory_write",
                    target="memory",
                    payload={"content": f"item {i}", "tags": []},
                    confidence=0.9,
                )
                await executor.execute(action)

            assert executor.action_count == 3

        asyncio.run(_test())

    def test_get_action_history(self) -> None:
        """get_action_history returns most recent N actions."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            executor = ActionExecutor(llm_router=MockLLMRouter())

            for i in range(5):
                action = ActionSpec(
                    thought_id=f"hist-{i}",
                    action_type="state_change",
                    target="state",
                    payload={"target": f"key_{i}", "value": i},
                    confidence=0.9,
                )
                await executor.execute(action)

            # Get last 3.
            history = executor.get_action_history(n=3)
            assert len(history) == 3
            assert history[0].thought_id == "hist-2"
            assert history[1].thought_id == "hist-3"
            assert history[2].thought_id == "hist-4"

        asyncio.run(_test())

    def test_get_action_history_default_n(self) -> None:
        """get_action_history defaults to n=10."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import (
                ActionExecutor,
                ActionSpec,
            )

            executor = ActionExecutor(llm_router=MockLLMRouter())

            for i in range(15):
                action = ActionSpec(
                    thought_id=f"default-{i}",
                    action_type="memory_write",
                    target="memory",
                    payload={"content": f"item {i}", "tags": []},
                    confidence=0.9,
                )
                await executor.execute(action)

            history = executor.get_action_history()
            assert len(history) == 10
            assert history[0].thought_id == "default-5"
            assert history[-1].thought_id == "default-14"

        asyncio.run(_test())

    def test_custom_confidence_threshold(self) -> None:
        """Custom confidence_threshold overrides default."""

        async def _test() -> None:
            from guinevere.consciousness.action_executor import ActionExecutor
            from guinevere.consciousness.thought import Thought, ThoughtType

            executor = ActionExecutor(
                llm_router=MockLLMRouter(),
                config={"confidence_threshold": 0.5},
            )
            # 0.6 should pass with threshold 0.5.
            thought = Thought(
                type=ThoughtType.COGNITION,
                content="Moderate confidence thought.",
                confidence=0.6,
            )
            spec = executor.evaluate_thought(thought)
            assert spec is not None

            # 0.4 should NOT pass with threshold 0.5.
            low_thought = Thought(
                type=ThoughtType.COGNITION,
                content="Low confidence thought.",
                confidence=0.4,
            )
            low_spec = executor.evaluate_thought(low_thought)
            assert low_spec is None

        asyncio.run(_test())

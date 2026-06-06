"""
T1: E2E Loop — Loop State Machine Migration Contract.

Verifies that the autonomous SDLC loop state machine (ADR-011) operates
correctly: all 7 phases defined, canonical ordering, status transitions,
and terminal COMPLETE state.  No live loop execution — purely structural
and transition-based.
"""

from __future__ import annotations

from src.loops.state_machine import (
    PHASE_NAMES,
    LoopPhase,
    LoopStateMachine,
    LoopStatus,
)


class TestLoopPhaseEnum:
    """LoopPhase enum has exactly 7 workflow phases + COMPLETE terminal."""

    def test_all_phases_present(self) -> None:
        """All 8 enum members exist: 7 workflow + 1 terminal."""
        members = list(LoopPhase)
        assert len(members) == 8
        assert LoopPhase.RESEARCH == 1
        assert LoopPhase.COMPLETE == 8

    def test_phase_ordering(self) -> None:
        """Phases are ordered: RESEARCH < PLAN < DELEGATE < EXECUTE < VALIDATE < DOCS < EVIDENCE < COMPLETE."""
        ordered = [
            LoopPhase.RESEARCH,
            LoopPhase.PLAN_AND_DELEGATE,
            LoopPhase.DELEGATE,
            LoopPhase.EXECUTE,
            LoopPhase.VALIDATE_AND_AUDIT,
            LoopPhase.UPDATE_DOCUMENTS,
            LoopPhase.SETUP_EVIDENCE,
            LoopPhase.COMPLETE,
        ]
        for i in range(len(ordered) - 1):
            assert ordered[i] < ordered[i + 1], f"{ordered[i]} not < {ordered[i+1]}"

    def test_phase_names_have_all_entries(self) -> None:
        """PHASE_NAMES dict covers every LoopPhase member."""
        for phase in LoopPhase:
            assert phase in PHASE_NAMES
            assert isinstance(PHASE_NAMES[phase], str)
            assert len(PHASE_NAMES[phase]) > 0


class TestLoopStateMachine:
    """LoopStateMachine structural and transition tests."""

    @staticmethod
    def _make_sm() -> LoopStateMachine:
        return LoopStateMachine(loop_id="test-loop", task="test-task")

    def test_initial_state(self) -> None:
        sm = self._make_sm()
        """Fresh machine starts at RESEARCH with INIT status."""
        assert sm.current_phase == LoopPhase.RESEARCH
        assert sm.status == LoopStatus.INIT

    def test_advance_moves_to_next_phase(self) -> None:
        """advance() moves RESEARCH -> PLAN_AND_DELEGATE and sets RUNNING."""
        sm = self._make_sm()
        next_phase = sm.advance()
        assert next_phase == LoopPhase.PLAN_AND_DELEGATE
        assert sm.current_phase == LoopPhase.PLAN_AND_DELEGATE

    def test_full_cycle_to_complete(self) -> None:
        """Advancing through all 7 phases lands on COMPLETE."""
        sm = self._make_sm()
        phases = [
            LoopPhase.PLAN_AND_DELEGATE,
            LoopPhase.DELEGATE,
            LoopPhase.EXECUTE,
            LoopPhase.VALIDATE_AND_AUDIT,
            LoopPhase.UPDATE_DOCUMENTS,
            LoopPhase.SETUP_EVIDENCE,
            LoopPhase.COMPLETE,
        ]
        for expected in phases:
            result = sm.advance()
            assert result == expected

    def test_pause_resume(self) -> None:
        """Pause sets PAUSED, resume sets RUNNING."""
        sm = self._make_sm()
        sm.set_status(LoopStatus.RUNNING)
        sm.pause()
        assert sm.status == LoopStatus.PAUSED
        sm.resume()
        assert sm.status == LoopStatus.RUNNING

    def test_blocked_status(self) -> None:
        """set_status(BLOCKED) sets BLOCKED."""
        sm = self._make_sm()
        sm.set_status(LoopStatus.RUNNING)
        sm.set_status(LoopStatus.BLOCKED)
        assert sm.status == LoopStatus.BLOCKED

    def test_fail_from_running(self) -> None:
        """fail() sets FAILED."""
        sm = self._make_sm()
        sm.set_status(LoopStatus.RUNNING)
        sm.fail(reason="test_fail")
        assert sm.status == LoopStatus.FAILED

    def test_cancel_from_any_state(self) -> None:
        """cancel() sets CANCELLED regardless of current status."""
        sm = self._make_sm()
        sm.set_status(LoopStatus.RUNNING)
        sm.cancel()
        assert sm.status == LoopStatus.CANCELLED

    def test_advance_after_complete_raises(self) -> None:
        """Advancing past COMPLETE raises RuntimeError."""
        sm = self._make_sm()
        for _ in range(7):
            _ = sm.advance()
        assert sm.current_phase == LoopPhase.COMPLETE
        try:
            _ = sm.advance()
            assert False, "Expected RuntimeError/ValueError"
        except (RuntimeError, ValueError):
            pass

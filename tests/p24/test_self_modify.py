"""Tests for M10 Self-Modification (W14).

Covers:
  - T1/T2 auto-promote (mock, no restart)
  - T3 society-voted (mock DAO)
  - T4 founder 2/2 (both sign -> execute, one -> pending)
  - T5 abolished (raises TierAbolishedError)
  - Ratchet prevents downgrade
  - mutation.py filename (NOT ladder.py)
  - C11 stale import fix verification
"""

from __future__ import annotations

import os

import pytest

from guinevere.self_modify import (
    MutabilityTier,
    MutationEngine,
    PromotionResult,
    RatchetFloor,
    RatchetViolationError,
    TierAbolishedError,
    restart_required,
    wire,
)
from guinevere.self_modify.mutation import MutationStatus


# ── T1/T2 auto-promote ──────────────────────────────────────────────────


class TestT1T2AutoPromote:
    """T1 and T2 auto-promote with no restart required."""

    def test_t1_auto_promote_no_restart(self) -> None:
        """T1 auto-promotes and does not require restart."""
        engine = MutationEngine()
        result = engine.promote(
            MutabilityTier.T1,
            "persona.word_choice",
            {"description": "Warm up greeting style"},
        )
        assert result.status == MutationStatus.PROMOTED
        assert result.restart_required is False
        assert result.tier == MutabilityTier.T1

    def test_t2_auto_promote_no_restart(self) -> None:
        """T2 auto-promotes and does not require restart."""
        engine = MutationEngine()
        result = engine.promote(
            MutabilityTier.T2,
            "tool.usage_pattern",
            {"description": "Prefer structured output for summaries"},
        )
        assert result.status == MutationStatus.PROMOTED
        assert result.restart_required is False
        assert result.tier == MutabilityTier.T2

    def test_t1_with_floors_updates_ratchet(self) -> None:
        """T1 with floors updates the ratchet tracker."""
        engine = MutationEngine()
        floors = {"safety": 0.9, "autonomy": 0.8, "alignment": 0.7, "capability": 0.5}
        result = engine.promote(
            MutabilityTier.T1,
            "persona.greeting",
            {"description": "Warmer greeting", "floors": floors},
        )
        assert result.status == MutationStatus.PROMOTED
        assert engine.ratchet.floors["safety"] == 0.9
        assert engine.ratchet.floors["autonomy"] == 0.8

    def test_t1_drift_score_below_threshold_rejected(self) -> None:
        """T1 with drift_score < 0.68 is rejected."""
        engine = MutationEngine()
        result = engine.promote(
            MutabilityTier.T1,
            "persona.style",
            {"description": "Test", "drift_score": 0.5},
        )
        assert result.status == MutationStatus.REJECTED
        assert result.drift_score == 0.5
        assert "below threshold" in result.reason


# ── T3 society-voted ─────────────────────────────────────────────────────


class TestT3SocietyVoted:
    """T3 requires society vote via DAO (M7)."""

    def test_t3_pending_vote(self) -> None:
        """T3 returns PENDING_VOTE status (delegated to DAO)."""
        engine = MutationEngine()
        result = engine.promote(
            MutabilityTier.T3,
            "skill.new_coding_assistant",
            {"description": "Add code review skill"},
        )
        assert result.status == MutationStatus.PENDING_VOTE
        assert result.restart_required is True
        assert result.tier == MutabilityTier.T3

    def test_t3_request_stored(self) -> None:
        """T3 mutation request is stored in the engine."""
        engine = MutationEngine()
        result = engine.promote(
            MutabilityTier.T3,
            "skill.data_viz",
            {"description": "Data visualization skill"},
        )
        req = engine.get_request(result.request_id)
        assert req is not None
        assert req.status == MutationStatus.PENDING_VOTE

    def test_t3_restart_required(self) -> None:
        """T3 always requires restart."""
        assert restart_required(MutabilityTier.T3) is True


# ── T4 founder 2/2 ───────────────────────────────────────────────────────


class TestT4FounderAck:
    """T4 requires founder 2/2 multisig (Guin + Pharsa)."""

    def test_t4_pending_founder_ack(self) -> None:
        """T4 returns PENDING_FOUNDER_ACK status."""
        engine = MutationEngine()
        result = engine.promote(
            MutabilityTier.T4,
            "alignment.safety_boundary",
            {"description": "Update safety boundary"},
        )
        assert result.status == MutationStatus.PENDING_FOUNDER_ACK
        assert result.restart_required is True
        assert result.tier == MutabilityTier.T4

    def test_t4_request_stored(self) -> None:
        """T4 mutation request is stored in the engine."""
        engine = MutationEngine()
        result = engine.promote(
            MutabilityTier.T4,
            "lineage.sub_agent_rules",
            {"description": "Update sub-agent lineage rules"},
        )
        req = engine.get_request(result.request_id)
        assert req is not None
        assert req.status == MutationStatus.PENDING_FOUNDER_ACK

    def test_t4_restart_required(self) -> None:
        """T4 always requires restart."""
        assert restart_required(MutabilityTier.T4) is True


# ── T5 abolished ─────────────────────────────────────────────────────────


class TestT5Abolished:
    """T5 is abolished post-P36 (marker only, raises error)."""

    def test_t5_raises_tier_abolished_error(self) -> None:
        """T5 raises TierAbolishedError."""
        engine = MutationEngine()
        with pytest.raises(TierAbolishedError) as exc_info:
            engine.promote(
                MutabilityTier.T5,
                "agents_md",
                {"description": "Update AGENTS.md"},
            )
        assert "T5" in str(exc_info.value)
        assert "abolished" in str(exc_info.value).lower()

    def test_t5_error_has_tier_attribute(self) -> None:
        """TierAbolishedError carries the tier name."""
        with pytest.raises(TierAbolishedError) as exc_info:
            engine = MutationEngine()
            engine.promote(MutabilityTier.T5, "x", {})
        assert exc_info.value.tier == "T5"

    def test_t5_restart_required_is_true(self) -> None:
        """Even though T5 is abolished, restart_required returns True for consistency."""
        assert restart_required(MutabilityTier.T5) is True


# ── Ratchet gate ─────────────────────────────────────────────────────────


class TestRatchetGate:
    """Ratchet prevents floor downgrade (ADR-061)."""

    def test_ratchet_allows_higher_floors(self) -> None:
        """Ratchet allows proposed floors >= current floors."""
        ratchet = RatchetFloor({"safety": 0.8, "autonomy": 0.7, "alignment": 0.6, "capability": 0.5})
        ratchet.check({"safety": 0.9, "autonomy": 0.8, "alignment": 0.7, "capability": 0.6})
        # Should not raise

    def test_ratchet_rejects_lower_floor(self) -> None:
        """Ratchet rejects any proposed floor below the current floor."""
        ratchet = RatchetFloor({"safety": 0.9})
        with pytest.raises(RatchetViolationError) as exc_info:
            ratchet.check({"safety": 0.8})
        assert "safety" in str(exc_info.value)
        assert exc_info.value.floor == "safety"

    def test_ratchet_rejects_partial_downgrade(self) -> None:
        """Ratchet rejects even if only one floor is lowered."""
        ratchet = RatchetFloor({
            "safety": 0.9, "autonomy": 0.8, "alignment": 0.7, "capability": 0.5,
        })
        with pytest.raises(RatchetViolationError):
            ratchet.check({
                "safety": 0.95, "autonomy": 0.85, "alignment": 0.65, "capability": 0.6,
            })

    def test_ratchet_update_only_increases(self) -> None:
        """Ratchet update only increases floors, never decreases."""
        ratchet = RatchetFloor({"safety": 0.8})
        ratchet.update({"safety": 0.7})
        assert ratchet.floors["safety"] == 0.8  # unchanged

    def test_ratchet_update_increases(self) -> None:
        """Ratchet update increases floor when proposed is higher."""
        ratchet = RatchetFloor({"safety": 0.8})
        ratchet.update({"safety": 0.9})
        assert ratchet.floors["safety"] == 0.9

    def test_engine_ratchet_blocks_promote(self) -> None:
        """Engine promotes fail when ratchet is violated."""
        engine = MutationEngine(ratchet=RatchetFloor({"safety": 0.9}))
        with pytest.raises(RatchetViolationError):
            engine.promote(
                MutabilityTier.T1,
                "test",
                {"floors": {"safety": 0.5}},
            )


# ── Wire function ────────────────────────────────────────────────────────


class TestWire:
    """wire() attaches MutationEngine to agent."""

    def test_wire_creates_engine_on_agent(self) -> None:
        """wire(agent) attaches engine as agent._mutation_engine."""

        class FakeAgent:
            pass

        agent = FakeAgent()
        engine = wire(agent)
        assert isinstance(engine, MutationEngine)
        assert agent._mutation_engine is engine


# ── Filename verification (C18) ──────────────────────────────────────────


class TestFilenameC18:
    """C18: File MUST be named mutation.py, NOT ladder.py."""

    def test_mutation_py_exists(self) -> None:
        """mutation.py exists in guinevere/self_modify/."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "guinevere", "self_modify", "mutation.py",
        )
        assert os.path.isfile(path), f"mutation.py not found at {os.path.abspath(path)}"

    def test_ladder_py_does_not_exist(self) -> None:
        """ladder.py does NOT exist (C18 correction)."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "guinevere", "self_modify", "ladder.py",
        )
        assert not os.path.isfile(path), "ladder.py must not exist (C18)"


# ── C11 stale import fix ────────────────────────────────────────────────


class TestC11StaleImports:
    """C11: No stale 'from src.loops' imports in guinevere/self_modify/."""

    def test_no_src_loops_imports(self) -> None:
        """guinevere/self_modify/ does not import from src.loops."""
        self_modify_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "guinevere", "self_modify",
        )
        for fname in os.listdir(self_modify_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(self_modify_dir, fname)
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            assert "from src.loops" not in content, (
                f"Stale 'from src.loops' import found in {fname}"
            )


# ── Module-level imports ─────────────────────────────────────────────────


class TestImports:
    """Verify public API is importable."""

    def test_import_mutation_engine(self) -> None:
        from guinevere.self_modify import MutationEngine
        assert MutationEngine is not None

    def test_import_mutability_tier(self) -> None:
        from guinevere.self_modify import MutabilityTier
        tiers = [t.name for t in MutabilityTier]
        assert "T1" in tiers
        assert "T2" in tiers
        assert "T3" in tiers
        assert "T4" in tiers
        assert "T5" in tiers

    def test_import_wire(self) -> None:
        from guinevere.self_modify import wire
        assert callable(wire)

    def test_import_promote_module(self) -> None:
        from guinevere.self_modify.promote import PromotionEngine
        assert PromotionEngine is not None


# ── PromotionEngine (promote.py) ─────────────────────────────────────────


class TestPromotionEngine:
    """Tests for compositional-drift promotion engine."""

    @pytest.mark.asyncio
    async def test_promote_on_high_successes_and_good_drift(self) -> None:
        from guinevere.self_modify.promote import PromotionEngine, DriftCheckResult
        from datetime import datetime, timezone

        engine = PromotionEngine()
        drift = DriftCheckResult(
            passed=True, cos_sim=0.92, flagged_categories=[], details="OK",
            checked_at=datetime.now(timezone.utc),
        )
        decision = await engine.decide_promotion("c1", success_count=5, failure_count=1, drift_result=drift)
        assert decision.action == "promote"

    @pytest.mark.asyncio
    async def test_reject_on_drift_failure(self) -> None:
        from guinevere.self_modify.promote import PromotionEngine, DriftCheckResult
        from datetime import datetime, timezone

        engine = PromotionEngine()
        drift = DriftCheckResult(
            passed=False, cos_sim=0.5, flagged_categories=[], details="Below threshold",
            checked_at=datetime.now(timezone.utc),
        )
        decision = await engine.decide_promotion("c2", success_count=10, failure_count=0, drift_result=drift)
        assert decision.action == "reject"

    @pytest.mark.asyncio
    async def test_demote_on_high_failure_ratio(self) -> None:
        from guinevere.self_modify.promote import PromotionEngine, DriftCheckResult
        from datetime import datetime, timezone

        engine = PromotionEngine()
        drift = DriftCheckResult(
            passed=True, cos_sim=0.95, flagged_categories=[], details="OK",
            checked_at=datetime.now(timezone.utc),
        )
        decision = await engine.decide_promotion("c3", success_count=1, failure_count=10, drift_result=drift)
        assert decision.action == "demote"

    @pytest.mark.asyncio
    async def test_hold_on_insufficient_data(self) -> None:
        from guinevere.self_modify.promote import PromotionEngine, DriftCheckResult
        from datetime import datetime, timezone

        engine = PromotionEngine()
        drift = DriftCheckResult(
            passed=True, cos_sim=0.95, flagged_categories=[], details="OK",
            checked_at=datetime.now(timezone.utc),
        )
        decision = await engine.decide_promotion("c4", success_count=1, failure_count=1, drift_result=drift)
        assert decision.action == "hold"

    def test_cosine_similarity_identical(self) -> None:
        from guinevere.self_modify.promote import _cosine_similarity
        v = [1.0, 2.0, 3.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-9

    def test_cosine_similarity_orthogonal(self) -> None:
        from guinevere.self_modify.promote import _cosine_similarity
        assert abs(_cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9

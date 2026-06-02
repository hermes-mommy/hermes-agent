"""
P4-006: Reward Tiers Engine — Deterministic Unit Tests

Tests the five-tier reward system (T1–T5): enum values, REWARD_CONFIG,
calculate_tier thresholds, should_reward logic, award state tracking,
error hierarchy, and edge cases.  100% deterministic, zero network calls.
"""
from __future__ import annotations

import pytest

from src.persona.reward_engine import (
    MAX_QUALITY_SCORE,
    MAX_STREAK_BONUS,
    MIN_QUALITY_SCORE,
    MIN_REWARD_THRESHOLD,
    REWARD_CONFIG,
    STREAK_BONUS_PER_STREAK,
    TIER_THRESHOLDS,
    InvalidQualityScoreError,
    InvalidTierError,
    RewardConfigEntry,
    RewardEngine,
    RewardError,
    RewardResult,
    RewardTier,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def engine() -> RewardEngine:
    """Return a fresh RewardEngine instance."""
    return RewardEngine()


@pytest.fixture
def all_tiers() -> list[RewardTier]:
    """Return all five RewardTier members."""
    return [
        RewardTier.T1_ACKNOWLEDGMENT,
        RewardTier.T2_VERBAL_PRAISE,
        RewardTier.T3_AFFECTIONATE,
        RewardTier.T4_CELEBRATORY,
        RewardTier.T5_DEEP_APPRECIATION,
    ]


# ============================================================
# RewardTier Enum
# ============================================================


class TestRewardTierEnum:
    """Verify all 5 reward tiers exist with correct integer values."""

    def test_t1_value(self) -> None:
        assert RewardTier.T1_ACKNOWLEDGMENT == 1
        assert RewardTier.T1_ACKNOWLEDGMENT.value == 1

    def test_t2_value(self) -> None:
        assert RewardTier.T2_VERBAL_PRAISE == 2
        assert RewardTier.T2_VERBAL_PRAISE.value == 2

    def test_t3_value(self) -> None:
        assert RewardTier.T3_AFFECTIONATE == 3
        assert RewardTier.T3_AFFECTIONATE.value == 3

    def test_t4_value(self) -> None:
        assert RewardTier.T4_CELEBRATORY == 4
        assert RewardTier.T4_CELEBRATORY.value == 4

    def test_t5_value(self) -> None:
        assert RewardTier.T5_DEEP_APPRECIATION == 5
        assert RewardTier.T5_DEEP_APPRECIATION.value == 5

    def test_all_five_tiers_exist(self, all_tiers: list[RewardTier]) -> None:
        assert len(all_tiers) == 5
        assert len(RewardTier) == 5

    def test_tier_is_int_enum(self) -> None:
        """RewardTier inherits from IntEnum — works as an integer."""
        assert isinstance(RewardTier.T1_ACKNOWLEDGMENT, int)
        assert RewardTier.T1_ACKNOWLEDGMENT + 1 == 2

    def test_tier_ordering(self) -> None:
        """T1 < T2 < T3 < T4 < T5."""
        assert RewardTier.T1_ACKNOWLEDGMENT < RewardTier.T2_VERBAL_PRAISE
        assert RewardTier.T2_VERBAL_PRAISE < RewardTier.T3_AFFECTIONATE
        assert RewardTier.T3_AFFECTIONATE < RewardTier.T4_CELEBRATORY
        assert RewardTier.T4_CELEBRATORY < RewardTier.T5_DEEP_APPRECIATION

    def test_tier_comparison_operators(self) -> None:
        """IntEnum supports full comparison semantics."""
        assert RewardTier.T5_DEEP_APPRECIATION > RewardTier.T1_ACKNOWLEDGMENT
        assert RewardTier.T3_AFFECTIONATE >= RewardTier.T3_AFFECTIONATE
        assert RewardTier.T1_ACKNOWLEDGMENT <= RewardTier.T2_VERBAL_PRAISE


# ============================================================
# REWARD_CONFIG
# ============================================================


class TestRewardConfig:
    """Verify REWARD_CONFIG covers all tiers with correct structure."""

    def test_all_tiers_have_config(self, all_tiers: list[RewardTier]) -> None:
        for tier in all_tiers:
            assert tier in REWARD_CONFIG, f"Missing REWARD_CONFIG entry for {tier}"

    def test_config_entry_is_frozen(self) -> None:
        """RewardConfigEntry should be frozen (immutable)."""
        entry = REWARD_CONFIG[RewardTier.T1_ACKNOWLEDGMENT]
        with pytest.raises(AttributeError):
            setattr(entry, "name", "Changed")

    def test_config_entry_has_required_fields(
        self, all_tiers: list[RewardTier]
    ) -> None:
        for tier in all_tiers:
            entry = REWARD_CONFIG[tier]
            assert isinstance(entry.name, str) and len(entry.name) > 0
            assert isinstance(entry.description, str) and len(entry.description) > 0
            assert isinstance(entry.trigger_conditions, list)
            assert len(entry.trigger_conditions) > 0
            assert isinstance(entry.message_templates, list)
            assert len(entry.message_templates) > 0

    def test_t1_name(self) -> None:
        assert REWARD_CONFIG[RewardTier.T1_ACKNOWLEDGMENT].name == "Acknowledgment"

    def test_t2_name(self) -> None:
        assert REWARD_CONFIG[RewardTier.T2_VERBAL_PRAISE].name == "Verbal Praise"

    def test_t3_name(self) -> None:
        assert REWARD_CONFIG[RewardTier.T3_AFFECTIONATE].name == "Affectionate"

    def test_t4_name(self) -> None:
        assert REWARD_CONFIG[RewardTier.T4_CELEBRATORY].name == "Celebratory"

    def test_t5_name(self) -> None:
        assert REWARD_CONFIG[RewardTier.T5_DEEP_APPRECIATION].name == "Deep Appreciation"

    def test_message_templates_are_non_empty_strings(
        self, all_tiers: list[RewardTier]
    ) -> None:
        for tier in all_tiers:
            for template in REWARD_CONFIG[tier].message_templates:
                assert isinstance(template, str) and len(template.strip()) > 0


# ============================================================
# RewardEngine.calculate_tier()
# ============================================================


class TestCalculateTier:
    """Tier calculation from quality_score + streak_bonus."""

    def test_t5_at_max_quality_no_streak(self, engine: RewardEngine) -> None:
        assert engine.calculate_tier(1.0, 0) == RewardTier.T5_DEEP_APPRECIATION

    def test_t5_with_high_quality_and_streak(self, engine: RewardEngine) -> None:
        # 0.95 + 0.05*0 = 0.95 >= 0.95 → T5
        assert engine.calculate_tier(0.95, 0) == RewardTier.T5_DEEP_APPRECIATION

    def test_t4_celebratory(self, engine: RewardEngine) -> None:
        # 0.80 + 0 = 0.80 >= 0.80 → T4
        assert engine.calculate_tier(0.80, 0) == RewardTier.T4_CELEBRATORY

    def test_t3_affectionate(self, engine: RewardEngine) -> None:
        # 0.60 + 0 = 0.60 >= 0.60 → T3
        assert engine.calculate_tier(0.60, 0) == RewardTier.T3_AFFECTIONATE

    def test_t2_verbal_praise(self, engine: RewardEngine) -> None:
        # 0.40 + 0 = 0.40 >= 0.40 → T2
        assert engine.calculate_tier(0.40, 0) == RewardTier.T2_VERBAL_PRAISE

    def test_t1_acknowledgment(self, engine: RewardEngine) -> None:
        # 0.20 + 0 = 0.20 >= 0.20 → T1
        assert engine.calculate_tier(0.20, 0) == RewardTier.T1_ACKNOWLEDGMENT

    def test_below_t1_threshold_returns_t1(self, engine: RewardEngine) -> None:
        # 0.05 + 0 = 0.05 < 0.20 → floor is T1
        assert engine.calculate_tier(0.05, 0) == RewardTier.T1_ACKNOWLEDGMENT

    def test_zero_quality_returns_t1(self, engine: RewardEngine) -> None:
        assert engine.calculate_tier(0.0, 0) == RewardTier.T1_ACKNOWLEDGMENT

    # -- streak bonus effects ----

    def test_streak_bumps_tier_up(self, engine: RewardEngine) -> None:
        # 0.75 + 0.05*1 = 0.80 >= 0.80 → T4 (was T3 without streak)
        assert engine.calculate_tier(0.75, 1) == RewardTier.T4_CELEBRATORY

    def test_streak_of_4_adds_0_20(self, engine: RewardEngine) -> None:
        # 0.55 + 0.20 = 0.75 < 0.80 → T3
        assert engine.calculate_tier(0.55, 4) == RewardTier.T3_AFFECTIONATE

    def test_streak_of_6_adds_0_30_capped(self, engine: RewardEngine) -> None:
        # 0.50 + 0.30 (capped) = 0.80 >= 0.80 → T4
        assert engine.calculate_tier(0.50, 6) == RewardTier.T4_CELEBRATORY

    def test_streak_of_100_capped_at_0_30(self, engine: RewardEngine) -> None:
        # 0.65 + 0.30 (capped) = 0.95 >= 0.95 → T5
        assert engine.calculate_tier(0.65, 100) == RewardTier.T5_DEEP_APPRECIATION

    def test_streak_does_not_exceed_1_0(self, engine: RewardEngine) -> None:
        # 0.90 + 0.30 (capped) = 1.0 → T5
        assert engine.calculate_tier(0.90, 10) == RewardTier.T5_DEEP_APPRECIATION

    def test_negative_streak_treated_as_zero(self, engine: RewardEngine) -> None:
        # negative streak → bonus = 0, quality 0.40 → T2
        assert engine.calculate_tier(0.40, -5) == RewardTier.T2_VERBAL_PRAISE

    # -- invalid inputs ----

    def test_quality_above_1_raises(self, engine: RewardEngine) -> None:
        with pytest.raises(InvalidQualityScoreError):
            engine.calculate_tier(1.1, 0)

    def test_quality_below_0_raises(self, engine: RewardEngine) -> None:
        with pytest.raises(InvalidQualityScoreError):
            engine.calculate_tier(-0.1, 0)

    def test_quality_negative_large_raises(self, engine: RewardEngine) -> None:
        with pytest.raises(InvalidQualityScoreError):
            engine.calculate_tier(-10.0, 0)

    # -- boundary precision ----

    def test_just_below_t4_threshold(self, engine: RewardEngine) -> None:
        # 0.799 + 0 = 0.799 < 0.80 → T3
        assert engine.calculate_tier(0.799, 0) == RewardTier.T3_AFFECTIONATE

    def test_just_below_t5_threshold(self, engine: RewardEngine) -> None:
        # 0.949 + 0 = 0.949 < 0.95 → T4
        assert engine.calculate_tier(0.949, 0) == RewardTier.T4_CELEBRATORY

    def test_exact_boundary_t2(self, engine: RewardEngine) -> None:
        assert engine.calculate_tier(0.40, 0) == RewardTier.T2_VERBAL_PRAISE

    def test_exact_boundary_t3(self, engine: RewardEngine) -> None:
        assert engine.calculate_tier(0.60, 0) == RewardTier.T3_AFFECTIONATE


# ============================================================
# RewardEngine.should_reward()
# ============================================================


class TestShouldReward:
    """should_reward decision — always allowed, no safe_mode check."""

    def test_completed_task_with_good_quality(self, engine: RewardEngine) -> None:
        assert engine.should_reward(task_completion=True, quality=0.5, streak=0) is True

    def test_incomplete_task_no_reward(self, engine: RewardEngine) -> None:
        assert engine.should_reward(task_completion=False, quality=0.9, streak=5) is False

    def test_completed_task_with_zero_quality_low_streak(self, engine: RewardEngine) -> None:
        # effective = 0.0 + 0 = 0.0 < 0.10 → no reward
        assert engine.should_reward(task_completion=True, quality=0.0, streak=0) is False

    def test_completed_task_with_low_quality_but_streak(self, engine: RewardEngine) -> None:
        # effective = 0.0 + 0.10 = 0.10 >= 0.10 → reward
        assert engine.should_reward(task_completion=True, quality=0.0, streak=2) is True

    def test_completed_task_with_minimum_quality(self, engine: RewardEngine) -> None:
        # effective = 0.10 + 0 = 0.10 >= 0.10 → reward
        assert engine.should_reward(task_completion=True, quality=0.10, streak=0) is True

    def test_below_minimum_threshold(self, engine: RewardEngine) -> None:
        # effective = 0.05 + 0 = 0.05 < 0.10 → no reward
        assert engine.should_reward(task_completion=True, quality=0.05, streak=0) is False

    def test_high_quality_always_rewards(self, engine: RewardEngine) -> None:
        assert engine.should_reward(task_completion=True, quality=1.0, streak=0) is True

    def test_reward_allowed_during_safe_mode(self, engine: RewardEngine) -> None:
        """Rewards are always allowed — this test documents the invariant.

        The engine has no awareness of safe-mode; it simply evaluates inputs.
        This is by design per PersonaDoc v3.0.
        """
        # Even in safe_mode context, should_reward returns True
        assert engine.should_reward(task_completion=True, quality=0.5, streak=0) is True

    def test_reward_allowed_during_distress(self, engine: RewardEngine) -> None:
        """Rewards are never suppressed by distress — invariant documented."""
        assert engine.should_reward(task_completion=True, quality=0.8, streak=2) is True


# ============================================================
# RewardEngine.award()
# ============================================================


class TestAward:
    """Award method — issues reward and tracks state."""

    def test_award_returns_reward_result(self, engine: RewardEngine) -> None:
        result = engine.award(
            tier=RewardTier.T3_AFFECTIONATE,
            reason="Great code review",
            streak_count=2,
        )
        assert isinstance(result, RewardResult)
        assert result.tier == RewardTier.T3_AFFECTIONATE
        assert result.reason == "Great code review"
        assert result.streak_count == 2
        assert isinstance(result.message, str) and len(result.message) > 0

    def test_award_updates_current_tier(self, engine: RewardEngine) -> None:
        engine.award(RewardTier.T4_CELEBRATORY, "Sprint done", 5)
        assert engine.get_current_tier() == RewardTier.T4_CELEBRATORY

    def test_award_increments_total(self, engine: RewardEngine) -> None:
        assert engine.total_rewards_awarded == 0
        engine.award(RewardTier.T1_ACKNOWLEDGMENT, "done", 0)
        assert engine.total_rewards_awarded == 1
        engine.award(RewardTier.T2_VERBAL_PRAISE, "well done", 1)
        assert engine.total_rewards_awarded == 2

    def test_award_updates_last_reason(self, engine: RewardEngine) -> None:
        engine.award(RewardTier.T1_ACKNOWLEDGMENT, "task 1", 0)
        assert engine.last_reason == "task 1"
        engine.award(RewardTier.T5_DEEP_APPRECIATION, "extraordinary", 10)
        assert engine.last_reason == "extraordinary"

    def test_award_invalid_type_raises(self, engine: RewardEngine) -> None:
        invalid_tier: object = 99
        with pytest.raises(InvalidTierError):
            engine.award(tier=invalid_tier, reason="bad", streak_count=0)  # pyright: ignore[reportArgumentType]

    def test_award_all_tiers(self, engine: RewardEngine, all_tiers: list[RewardTier]) -> None:
        """Each tier can be awarded without error."""
        for tier in all_tiers:
            result = engine.award(tier, f"test {tier.name}", 0)
            assert result.tier == tier

    def test_reward_result_config_property(self, engine: RewardEngine) -> None:
        result = engine.award(RewardTier.T2_VERBAL_PRAISE, "test", 0)
        config = result.config
        assert isinstance(config, RewardConfigEntry)
        assert config.name == "Verbal Praise"


# ============================================================
# RewardEngine.get_current_tier()
# ============================================================


class TestGetCurrentTier:
    """Current tier accessor."""

    def test_initial_tier_is_t1(self, engine: RewardEngine) -> None:
        assert engine.get_current_tier() == RewardTier.T1_ACKNOWLEDGMENT

    def test_tier_changes_after_award(self, engine: RewardEngine) -> None:
        engine.award(RewardTier.T5_DEEP_APPRECIATION, "big win", 20)
        assert engine.get_current_tier() == RewardTier.T5_DEEP_APPRECIATION

    def test_tier_tracks_last_award(self, engine: RewardEngine) -> None:
        engine.award(RewardTier.T5_DEEP_APPRECIATION, "first", 0)
        engine.award(RewardTier.T2_VERBAL_PRAISE, "second", 0)
        assert engine.get_current_tier() == RewardTier.T2_VERBAL_PRAISE


# ============================================================
# Error Hierarchy
# ============================================================


class TestErrorHierarchy:
    """Custom exception classes follow proper inheritance."""

    def test_reward_error_is_exception(self) -> None:
        assert issubclass(RewardError, Exception)

    def test_invalid_quality_is_reward_error(self) -> None:
        assert issubclass(InvalidQualityScoreError, RewardError)

    def test_invalid_tier_is_reward_error(self) -> None:
        assert issubclass(InvalidTierError, RewardError)

    def test_raise_invalid_quality(self) -> None:
        with pytest.raises(InvalidQualityScoreError):
            raise InvalidQualityScoreError("quality must be in [0, 1]")

    def test_raise_invalid_tier(self) -> None:
        with pytest.raises(InvalidTierError):
            raise InvalidTierError("not a valid tier")

    def test_catch_as_base_error(self) -> None:
        """Both subclasses catch as RewardError."""
        with pytest.raises(RewardError):
            raise InvalidQualityScoreError("test")
        with pytest.raises(RewardError):
            raise InvalidTierError("test")


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    """Boundary conditions and invariants."""

    def test_streak_bonus_constants(self) -> None:
        """Streak bonus constants are consistent."""
        assert STREAK_BONUS_PER_STREAK == 0.05
        assert MAX_STREAK_BONUS == 0.30
        # 6 streaks = 0.30 cap (use approx for IEEE 754)
        assert 6 * STREAK_BONUS_PER_STREAK == pytest.approx(MAX_STREAK_BONUS)

    def test_quality_bounds_constants(self) -> None:
        assert MIN_QUALITY_SCORE == 0.0
        assert MAX_QUALITY_SCORE == 1.0

    def test_min_reward_threshold_constant(self) -> None:
        assert MIN_REWARD_THRESHOLD == 0.10

    def test_tier_thresholds_cover_all_tiers(
        self, all_tiers: list[RewardTier]
    ) -> None:
        for tier in all_tiers:
            assert tier in TIER_THRESHOLDS

    def test_tier_thresholds_are_descending(self) -> None:
        """Higher tiers have strictly higher thresholds."""
        assert (
            TIER_THRESHOLDS[RewardTier.T5_DEEP_APPRECIATION]
            > TIER_THRESHOLDS[RewardTier.T4_CELEBRATORY]
            > TIER_THRESHOLDS[RewardTier.T3_AFFECTIONATE]
            > TIER_THRESHOLDS[RewardTier.T2_VERBAL_PRAISE]
            > TIER_THRESHOLDS[RewardTier.T1_ACKNOWLEDGMENT]
        )

    def test_engine_fresh_state(self, engine: RewardEngine) -> None:
        assert engine.total_rewards_awarded == 0
        assert engine.last_reason == ""
        assert engine.get_current_tier() == RewardTier.T1_ACKNOWLEDGMENT

    def test_calculate_tier_idempotent(self, engine: RewardEngine) -> None:
        """Calling calculate_tier does not mutate engine state."""
        tier1 = engine.calculate_tier(0.85, 3)
        tier2 = engine.calculate_tier(0.85, 3)
        assert tier1 == tier2
        assert engine.total_rewards_awarded == 0  # no award was made

    def test_should_reward_does_not_mutate(self, engine: RewardEngine) -> None:
        """should_reward is a pure check — no state mutation."""
        engine.should_reward(True, 0.9, 5)
        assert engine.total_rewards_awarded == 0
        assert engine.get_current_tier() == RewardTier.T1_ACKNOWLEDGMENT

    def test_quality_exactly_1_with_max_streak(self, engine: RewardEngine) -> None:
        # 1.0 + 0.30 = 1.0 (clamped) → T5
        assert engine.calculate_tier(1.0, 6) == RewardTier.T5_DEEP_APPRECIATION

    def test_full_lifecycle(self, engine: RewardEngine) -> None:
        """Simulate a full reward lifecycle: check → calculate → award."""
        quality = 0.85
        streak = 3

        assert engine.should_reward(True, quality, streak) is True

        tier = engine.calculate_tier(quality, streak)
        # 0.85 + 0.15 = 1.0 → T5
        assert tier == RewardTier.T5_DEEP_APPRECIATION

        result = engine.award(tier, "Perfect sprint", streak)
        assert result.tier == RewardTier.T5_DEEP_APPRECIATION
        assert engine.get_current_tier() == RewardTier.T5_DEEP_APPRECIATION
        assert engine.total_rewards_awarded == 1
        assert engine.last_reason == "Perfect sprint"

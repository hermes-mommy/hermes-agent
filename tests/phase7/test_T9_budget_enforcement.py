"""
T9: Budget Enforcement — Cost Tracking and Budget Limit Contract Tests.

Verifies budget enforcement mechanics: BudgetConfig structure,
BudgetEnforcer initialization, cost tracking, and limit checks.
Uses mocked Redis to avoid live DB dependencies.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

from src.mcp.budget import BudgetConfig, BudgetEnforcer, BudgetStatus
from src.mcp.cost import ToolCostTracker
from src.loops.cost import LoopCostTracker


class TestBudgetConfig:
    """BudgetConfig properly structures budget limits."""

    def test_budget_config_has_limits(self) -> None:
        """BudgetConfig defines daily, monthly, and hard stop limits."""
        cfg = BudgetConfig(
            exa_daily_cap=0.10,
            brave_daily_cap=0.05,
            global_daily_cap=0.20,
            monthly_warning=0.50,
            monthly_critical=1.00,
            monthly_hard_stop=2.00,
            monthly_absolute_cap=3.00,
        )
        assert cfg.exa_daily_cap == 0.10
        assert cfg.global_daily_cap == 0.20
        assert cfg.monthly_warning == 0.50
        assert cfg.monthly_hard_stop == 2.00
        assert cfg.monthly_absolute_cap == 3.00

    def test_budget_config_defaults(self) -> None:
        """BudgetConfig with no args has sensible defaults."""
        cfg = BudgetConfig()
        assert cfg.global_daily_cap > 0
        assert cfg.monthly_absolute_cap > cfg.monthly_hard_stop

    def test_budget_status_constructs(self) -> None:
        """BudgetStatus is a dataclass with status fields."""
        status = BudgetStatus(
            tool="test",
            daily_spent=0.05,
            daily_cap=0.20,
            monthly_spent=0.50,
            alert_level="normal",
            fallback_active=False,
        )
        assert status.tool == "test"
        assert status.daily_spent == 0.05
        assert status.alert_level == "normal"
        assert status.fallback_active is False

    def test_budget_status_critical(self) -> None:
        """BudgetStatus can represent a critical budget state."""
        status = BudgetStatus(
            tool="test",
            daily_spent=0.95,
            daily_cap=0.20,
            monthly_spent=5.00,
            alert_level="critical",
            fallback_active=True,
        )
        assert status.alert_level == "critical"
        assert status.fallback_active is True


class _FakePipeline:
    """Typed pipeline result for the Redis mock."""

    def execute(self) -> None:
        return None


class _FakeRedis:
    """Fully typed Redis mock with concrete attributes."""

    def __init__(self) -> None:
        self._pipeline: _FakePipeline = _FakePipeline()

    def pipeline(self) -> _FakePipeline:
        return self._pipeline

    def scan_iter(self) -> Iterator[str]:
        return iter([])


class TestBudgetEnforcer:
    """BudgetEnforcer with mocked Redis (no live dependency)."""

    @staticmethod
    def _mock_redis() -> _FakeRedis:
        return _FakeRedis()

    def test_enforcer_initializes(self) -> None:
        """BudgetEnforcer can be instantiated with mocked Redis."""
        with patch("redis.Redis", return_value=self._mock_redis()):
            enforcer = BudgetEnforcer()
        assert enforcer is not None

    def test_enforcer_with_custom_config(self) -> None:
        """BudgetEnforcer accepts custom BudgetConfig."""
        cfg = BudgetConfig(global_daily_cap=0.50, monthly_absolute_cap=5.00)
        with patch("redis.Redis", return_value=self._mock_redis()):
            enforcer = BudgetEnforcer(config=cfg)
        assert enforcer is not None

    def test_enforcer_delegates_to_config(self) -> None:
        """BudgetEnforcer.config is the passed BudgetConfig instance."""
        cfg = BudgetConfig(global_daily_cap=0.99, monthly_absolute_cap=9.99)
        with patch("redis.Redis", return_value=self._mock_redis()):
            enforcer = BudgetEnforcer(config=cfg)
        assert enforcer.config.global_daily_cap == 0.99
        assert enforcer.config.monthly_absolute_cap == 9.99


class TestCostTracker:
    """CostTracker structural tests (no live LLM calls)."""

    def test_tool_cost_tracker_initializes(self) -> None:
        """ToolCostTracker can be instantiated."""
        tracker = ToolCostTracker()
        assert tracker is not None


class TestLoopCostTracker:
    """LoopCostTracker structural tests."""

    def test_loop_cost_tracker_initializes(self) -> None:
        """LoopCostTracker can be instantiated (fail-soft on Redis error)."""
        tracker = LoopCostTracker()
        assert tracker is not None

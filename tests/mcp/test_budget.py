"""Tests for BudgetEnforcer — mocked Redis, no real MCP dependencies."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import RedisError

from src.mcp.budget import BudgetConfig, BudgetEnforcer, BudgetStatus
from src.mcp.tools.exa_search import BudgetExceeded


# ============================================================================
# Fixtures
# ============================================================================


def _make_redis_get(redis_mock: MagicMock, overrides: dict[str, str | None]) -> None:
    """Configure redis.get to return values from *overrides*; default to None."""
    def side_effect(key: str) -> str | None:
        return overrides.get(key)
    redis_mock.get.side_effect = side_effect


@pytest.fixture
def mock_redis() -> MagicMock:
    """Fully-mocked redis.Redis with pipeline support."""
    r = MagicMock()
    r.pipeline.return_value = MagicMock()
    r.pipeline.return_value.execute.return_value = None
    r.scan_iter.return_value = iter([])
    return r


@pytest.fixture
def enforcer(mock_redis: MagicMock) -> BudgetEnforcer:
    """BudgetEnforcer with mocked Redis and default config."""
    with patch("redis.Redis", return_value=mock_redis):
        return BudgetEnforcer()


@pytest.fixture
def enforcer_custom_config(mock_redis: MagicMock) -> BudgetEnforcer:
    """BudgetEnforcer with a custom BudgetConfig (lower caps for testing)."""
    cfg = BudgetConfig(
        exa_daily_cap=0.10,
        brave_daily_cap=0.05,
        global_daily_cap=0.20,
        monthly_warning=0.50,
        monthly_critical=1.00,
        monthly_hard_stop=2.00,
        monthly_absolute_cap=3.00,
    )
    with patch("redis.Redis", return_value=mock_redis):
        return BudgetEnforcer(config=cfg)


# ============================================================================
# Test scenarios from the scaffold
# ============================================================================


class TestExaCapTriggersBraveFallback:
    """Scenario 1: Exa $5/day cap triggers Brave fallback."""

    @pytest.mark.asyncio
    async def test_allows_when_under_cap(self, enforcer: BudgetEnforcer, mock_redis: MagicMock) -> None:
        """At $4.99 spent, an additional $0.01 call should pass."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "4.99",
            "cost:current_month": "4.99",
        })

        status = await enforcer.check_budget("exa")
        assert status.alert_level == "WARNING"  # monthly > $3
        assert status.daily_spent == 4.99
        assert status.daily_cap == 5.0

    @pytest.mark.asyncio
    async def test_raises_budget_exceeded_at_cap(self, enforcer: BudgetEnforcer, mock_redis: MagicMock) -> None:
        """At $5.00 spent, check_budget raises BudgetExceeded."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "5.00",
            "cost:current_month": "5.00",
            "tool:cost:total:2026-06-03": "5.00",
        })

        with pytest.raises(BudgetExceeded, match="Daily cap reached"):
            await enforcer.check_budget("exa")

    @pytest.mark.asyncio
    async def test_fallback_returns_brave_search(self, enforcer: BudgetEnforcer, mock_redis: MagicMock) -> None:
        """When Exa is over budget, get_fallback_tool returns brave_search."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "5.01",
            "cost:current_month": "5.01",
        })

        fallback = await enforcer.get_fallback_tool("exa")
        assert fallback == "brave_search"

    @pytest.mark.asyncio
    async def test_fallback_returns_none_when_also_over_budget(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """When Brave is also over budget, get_fallback_tool returns None."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "5.01",
            "tool:cost:brave_search:2026-06-03": "3.00",
            "cost:current_month": "5.01",
        })

        fallback = await enforcer.get_fallback_tool("exa")
        assert fallback is None


class TestMonthlyCapBlocksAll:
    """Scenario 2: Monthly $30 cap blocks all paid tools."""

    @pytest.mark.asyncio
    async def test_brave_search_blocked_at_monthly_cap(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """At $30.00 monthly, even brave_search raises BudgetExceeded."""
        _make_redis_get(mock_redis, {
            "tool:cost:brave_search:2026-06-03": "0.01",
            "cost:current_month": "30.00",
        })

        with pytest.raises(BudgetExceeded, match="Monthly absolute cap reached"):
            await enforcer.check_budget("brave_search")

    @pytest.mark.asyncio
    async def test_exa_blocked_at_monthly_cap(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """At $30.00 monthly, exa raises BudgetExceeded too."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
            "cost:current_month": "30.00",
        })

        with pytest.raises(BudgetExceeded, match="Monthly absolute cap reached"):
            await enforcer.check_budget("exa")

    @pytest.mark.asyncio
    async def test_fallback_blocked_at_monthly_cap(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """When monthly cap is reached, get_fallback_tool returns None."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "6.00",
            "cost:current_month": "30.00",
        })

        fallback = await enforcer.get_fallback_tool("exa")
        assert fallback is None


class TestMonthlyWarning:
    """Scenario 3: Monthly $3 warning triggers Discord alert (alert_level)."""

    @pytest.mark.asyncio
    async def test_warning_at_3_dollars(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """At $3.10 monthly, alert_level is WARNING."""
        _make_redis_get(mock_redis, {
            "tool:cost:brave_search:2026-06-03": "0.50",
            "cost:current_month": "3.10",
        })

        status = await enforcer.check_budget("brave_search")
        assert status.alert_level == "WARNING"

    @pytest.mark.asyncio
    async def test_critical_at_15_dollars(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """At $15.00 monthly, alert_level is CRITICAL."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
            "cost:current_month": "15.00",
        })

        status = await enforcer.check_budget("exa")
        assert status.alert_level == "CRITICAL"

    @pytest.mark.asyncio
    async def test_hard_stop_at_25_dollars(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """At $25.00 monthly, alert_level is HARD_STOP but call still passes if under daily cap."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "0.50",
            "cost:current_month": "25.00",
        })

        status = await enforcer.check_budget("exa")
        # HARD_STOP alert level when monthly >= 25, but call may still pass if not at $30
        assert status.alert_level == "HARD_STOP"

    @pytest.mark.asyncio
    async def test_get_monthly_status_shows_warning(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """get_monthly_status returns WARNING alert_level at $3.10."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
            "tool:cost:brave_search:2026-06-03": "0.50",
            "cost:current_month": "3.10",
        })
        mock_redis.scan_iter.return_value = iter([
            "tool:cost:exa:2026-06-03",
            "tool:cost:brave_search:2026-06-03",
        ])

        statuses = await enforcer.get_monthly_status()
        for name, status in statuses.items():
            assert status.alert_level == "WARNING", f"{name} should be WARNING"
            assert status.monthly_spent == 3.10


class TestGlobalDailyEmergencyCap:
    """Scenario 4: Global $10/day emergency cap."""

    @pytest.mark.asyncio
    async def test_all_tools_blocked_at_global_cap(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """When total daily spend reaches $10, all tools raise BudgetExceeded."""
        _make_redis_get(mock_redis, {
            "tool:cost:brave_search:2026-06-03": "1.00",
            "tool:cost:total:2026-06-03": "10.00",
            "cost:current_month": "10.00",
        })

        with pytest.raises(BudgetExceeded, match="Global daily emergency cap reached"):
            await enforcer.check_budget("brave_search")

    @pytest.mark.asyncio
    async def test_raises_even_when_per_tool_under_cap(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """Global cap blocks even when the specific tool is under its own cap."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "0.01",
            "tool:cost:total:2026-06-03": "10.00",
            "cost:current_month": "10.00",
        })

        with pytest.raises(BudgetExceeded, match="Global daily emergency cap reached"):
            await enforcer.check_budget("exa")


# ============================================================================
# Test record_and_check
# ============================================================================


class TestRecordAndCheck:
    """record_and_check records cost then checks budget."""

    @pytest.mark.asyncio
    async def test_records_and_passes_when_under_budget(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """Recording a small cost passes when under all caps."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "0.10",
            "cost:current_month": "0.10",
        })

        status = await enforcer.record_and_check("exa", 0.007)
        assert status.alert_level == "NORMAL"

        # Verify pipeline was called for recording.
        mock_redis.pipeline.assert_called()

    @pytest.mark.asyncio
    async def test_records_then_raises_when_cap_exceeded(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """Recording pushes daily spend over cap → BudgetExceeded.

        *record_and_check* calls *check_budget* after writing via pipeline,
        so the Redis GET mock must return the *post-increment* value ($5.002).
        """
        _state: dict[str, str | None] = {
            "tool:cost:exa:2026-06-03": "5.002",  # post-increment
            "tool:cost:total:2026-06-03": "5.002",
            "cost:current_month": "5.002",
        }
        mock_redis.get.side_effect = lambda k: _state.get(k)

        with pytest.raises(BudgetExceeded):
            await enforcer.record_and_check("exa", 0.007)

        mock_redis.pipeline.assert_called()

    @pytest.mark.asyncio
    async def test_records_pipeline_includes_monthly_key(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """record_and_check pipeline increments cost:current_month."""
        _make_redis_get(mock_redis, {
            "tool:cost:brave_search:2026-06-03": "0.01",
            "cost:current_month": "0.50",
        })
        mock_pipe = mock_redis.pipeline.return_value

        await enforcer.record_and_check("brave_search", 0.01)

        # Check that incrbyfloat was called on cost:current_month.
        calls = [c[0][0] for c in mock_pipe.incrbyfloat.call_args_list]
        assert "cost:current_month" in calls

    @pytest.mark.asyncio
    async def test_graceful_on_redis_pipeline_error(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """When Redis pipeline fails, check still runs."""
        mock_redis.pipeline.side_effect = RedisError("connection lost")
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
            "cost:current_month": "1.00",
        })

        status = await enforcer.record_and_check("exa", 0.007)
        assert status.tool == "exa"


# ============================================================================
# Test get_fallback_tool
# ============================================================================


class TestGetFallbackTool:
    """Fallback routing logic."""

    @pytest.mark.asyncio
    async def test_no_fallback_when_under_cap(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """When Exa is under budget, no fallback needed."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
            "cost:current_month": "1.00",
        })

        fallback = await enforcer.get_fallback_tool("exa")
        assert fallback is None

    @pytest.mark.asyncio
    async def test_brave_search_has_no_fallback(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """Brave has no fallback — returns None even when over budget."""
        _make_redis_get(mock_redis, {
            "tool:cost:brave_search:2026-06-03": "3.50",
            "cost:current_month": "5.00",
        })

        fallback = await enforcer.get_fallback_tool("brave_search")
        assert fallback is None

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_none(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """An unrecognized tool has no fallback."""
        _make_redis_get(mock_redis, {
            "tool:cost:unknown:2026-06-03": "99.00",
            "cost:current_month": "1.00",
        })

        fallback = await enforcer.get_fallback_tool("unknown")
        assert fallback is None


# ============================================================================
# Test get_monthly_status
# ============================================================================


class TestGetMonthlyStatus:
    """Monthly status aggregation."""

    @pytest.mark.asyncio
    async def test_returns_status_for_known_tools(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """get_monthly_status returns BudgetStatus for exa and brave_search."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "2.00",
            "tool:cost:brave_search:2026-06-03": "1.00",
            "cost:current_month": "3.00",
        })
        mock_redis.scan_iter.return_value = iter([
            "tool:cost:exa:2026-06-03",
            "tool:cost:brave_search:2026-06-03",
        ])

        statuses = await enforcer.get_monthly_status()
        assert "exa" in statuses
        assert "brave_search" in statuses
        assert statuses["exa"].daily_spent == 2.00
        assert statuses["brave_search"].daily_spent == 1.00

    @pytest.mark.asyncio
    async def test_monthly_spent_consistent_across_tools(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """All tools share the same monthly_spent in status."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
            "tool:cost:brave_search:2026-06-03": "0.50",
            "cost:current_month": "18.50",
        })
        mock_redis.scan_iter.return_value = iter([
            "tool:cost:exa:2026-06-03",
            "tool:cost:brave_search:2026-06-03",
        ])

        statuses = await enforcer.get_monthly_status()
        for status in statuses.values():
            assert status.monthly_spent == 18.50

    @pytest.mark.asyncio
    async def test_scans_for_all_daily_tools(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """Uses SCAN to discover all tools tracked today."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
            "tool:cost:brave_search:2026-06-03": "2.00",
            "tool:cost:github:2026-06-03": "0.00",
            "tool:cost:total:2026-06-03": "3.00",  # must be excluded
            "cost:current_month": "3.00",
        })
        mock_redis.scan_iter.return_value = iter([
            "tool:cost:exa:2026-06-03",
            "tool:cost:brave_search:2026-06-03",
            "tool:cost:github:2026-06-03",
            "tool:cost:total:2026-06-03",
        ])

        statuses = await enforcer.get_monthly_status()
        assert "total" not in statuses
        assert "exa" in statuses
        assert "brave_search" in statuses
        assert "github" in statuses

    @pytest.mark.asyncio
    async def test_returns_empty_on_redis_scan_error(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """Returns only known tools when SCAN fails."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
            "cost:current_month": "1.00",
        })
        mock_redis.scan_iter.side_effect = RedisError("scan error")

        statuses = await enforcer.get_monthly_status()
        assert "exa" in statuses
        assert "brave_search" in statuses


# ============================================================================
# Test frozen dataclasses
# ============================================================================


class TestBudgetConfigIsFrozen:
    """BudgetConfig must be immutable."""

    def test_cannot_set_attr(self) -> None:
        cfg = BudgetConfig()
        with pytest.raises(FrozenInstanceError):
            cfg.exa_daily_cap = 10.0  # type: ignore[misc]

    def test_defaults_match_spec(self) -> None:
        cfg = BudgetConfig()
        assert cfg.exa_daily_cap == 5.0
        assert cfg.brave_daily_cap == 3.0
        assert cfg.global_daily_cap == 10.0
        assert cfg.monthly_warning == 3.0
        assert cfg.monthly_critical == 15.0
        assert cfg.monthly_hard_stop == 25.0
        assert cfg.monthly_absolute_cap == 30.0


class TestBudgetStatusIsFrozen:
    """BudgetStatus must be immutable."""

    def test_cannot_set_attr(self) -> None:
        status = BudgetStatus(
            tool="exa",
            daily_spent=5.0,
            daily_cap=5.0,
            monthly_spent=10.0,
            alert_level="WARNING",
            fallback_active=True,
        )
        with pytest.raises(FrozenInstanceError):
            status.daily_spent = 1.0  # type: ignore[misc]


# ============================================================================
# Test BudgetExceeded is imported (not redefined)
# ============================================================================


def test_budget_exceeded_is_from_exa_search() -> None:
    """Verify BudgetExceeded in budget.py comes from src.mcp.tools.exa_search."""
    from src.mcp.tools.exa_search import BudgetExceeded as ExaBudgetExceeded

    # They should be the same class.
    from src.mcp.budget import BudgetExceeded  # check re-export

    assert BudgetExceeded is ExaBudgetExceeded


# ============================================================================
# Test structlog usage (no import logging, no print)
# ============================================================================


def test_no_logging_or_print_in_budget_module() -> None:
    """The budget module uses structlog, not stdlib logging or print."""
    import inspect
    import src.mcp.budget as budget_module

    source = inspect.getsource(budget_module)
    assert "import logging" not in source
    # print() should not appear outside comments/docstrings.
    lines = [l for l in source.splitlines() if "print(" in l and not l.strip().startswith("#")]
    assert len(lines) == 0, f"print() found: {lines}"


# ============================================================================
# Test BudgetStatus fields match spec
# ============================================================================


def test_budget_status_fields() -> None:
    """BudgetStatus has the expected fields with correct types."""
    status = BudgetStatus(
        tool="brave_search",
        daily_spent=2.50,
        daily_cap=3.0,
        monthly_spent=12.0,
        alert_level="WARNING",
        fallback_active=False,
    )
    assert status.tool == "brave_search"
    assert status.daily_spent == 2.50
    assert status.daily_cap == 3.0
    assert status.monthly_spent == 12.0
    assert status.alert_level == "WARNING"
    assert status.fallback_active is False

    # alert_level should be one of the four valid strings.
    valid_levels = {"NORMAL", "WARNING", "CRITICAL", "HARD_STOP"}
    assert status.alert_level in valid_levels


# ============================================================================
# Brave soft-cap warning (in check_budget)
# ============================================================================


class TestBraveSoftCap:
    """Brave at 80 % logs a soft-cap warning but does not block."""

    @pytest.mark.asyncio
    async def test_allows_at_80_percent(self, enforcer: BudgetEnforcer, mock_redis: MagicMock) -> None:
        """At 80 % of Brave cap ($2.40 / $3.00), call still passes."""
        _make_redis_get(mock_redis, {
            "tool:cost:brave_search:2026-06-03": "2.40",
            "cost:current_month": "2.40",
        })

        status = await enforcer.check_budget("brave_search")
        assert status.daily_spent == 2.40
        assert status.alert_level == "NORMAL"

    @pytest.mark.asyncio
    async def test_raises_at_cap(self, enforcer: BudgetEnforcer, mock_redis: MagicMock) -> None:
        """At $3.00, Brave raises BudgetExceeded."""
        _make_redis_get(mock_redis, {
            "tool:cost:brave_search:2026-06-03": "3.00",
            "cost:current_month": "3.00",
        })

        with pytest.raises(BudgetExceeded, match="Daily cap reached"):
            await enforcer.check_budget("brave_search")


# ============================================================================
# Test Redis error resilience
# ============================================================================


class TestRedisErrorResilience:
    """Budget enforcement handles Redis errors gracefully."""

    @pytest.mark.asyncio
    async def test_daily_read_error_defaults_to_zero(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """When Redis.get fails for daily key, daily_spent is treated as 0.0."""
        mock_redis.get.side_effect = RedisError("connection refused")

        status = await enforcer.check_budget("exa")
        assert status.daily_spent == 0.0

    @pytest.mark.asyncio
    async def test_monthly_read_error_defaults_to_zero(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """When Redis.get fails for monthly key, monthly_spent is treated as 0.0."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
        })
        mock_redis.get.side_effect = lambda key: "1.00" if "exa" in str(key) else RedisError("fail")

        # side_effect that raises is tricky — let's use explicit overrides instead
        mock_redis.get.reset_mock()
        def get_side(key: str) -> str | None:
            if "cost:current_month" in str(key):
                raise RedisError("monthly fetch failed")
            if "exa" in str(key):
                return "1.00"
            return None
        mock_redis.get.side_effect = get_side

        status = await enforcer.check_budget("exa")
        assert status.monthly_spent == 0.0
        assert status.daily_spent == 1.00


# ============================================================================
# Test BudgetConfig customisation
# ============================================================================


class TestCustomBudgetConfig:
    """Custom BudgetConfig allows different thresholds."""

    @pytest.mark.asyncio
    async def test_custom_caps_are_used(
        self, enforcer_custom_config: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """Custom config caps are enforced instead of defaults."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "0.055",
            "cost:current_month": "0.055",
        })

        # Under custom exa cap ($0.10) → passes.
        status = await enforcer_custom_config.check_budget("exa")
        assert status.daily_cap == 0.10

    @pytest.mark.asyncio
    async def test_custom_exa_cap_blocks(
        self, enforcer_custom_config: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """Custom Exa cap of $0.10 blocks at $0.10."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "0.10",
            "cost:current_month": "0.10",
        })

        with pytest.raises(BudgetExceeded, match="Daily cap reached"):
            await enforcer_custom_config.check_budget("exa")

    @pytest.mark.asyncio
    async def test_custom_monthly_stops_at_3_dollars(
        self, enforcer_custom_config: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """Custom monthly_absolute_cap of $3.00 blocks at $3.00."""
        _make_redis_get(mock_redis, {
            "tool:cost:brave_search:2026-06-03": "0.01",
            "cost:current_month": "3.00",
        })

        with pytest.raises(BudgetExceeded, match="Monthly absolute cap reached"):
            await enforcer_custom_config.check_budget("brave_search")


# ============================================================================
# Test check_budget returns BudgetStatus (not just raises)
# ============================================================================


class TestBudgetStatusReturnValue:
    """verify check_budget returns a valid BudgetStatus when passed."""

    @pytest.mark.asyncio
    async def test_status_contains_all_fields(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """BudgetStatus has all expected fields."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.25",
            "cost:current_month": "8.00",
        })

        status = await enforcer.check_budget("exa")
        assert isinstance(status, BudgetStatus)
        assert status.tool == "exa"
        assert status.daily_spent == 1.25
        assert status.daily_cap == 5.0
        assert status.monthly_spent == 8.00
        assert status.alert_level == "WARNING"
        assert status.fallback_active is False


# ============================================================================
# Test alert_level string values
# ============================================================================


class TestAlertLevel:
    """alert_level strings match the four spec values."""

    @pytest.mark.asyncio
    async def test_normal_when_under_all_caps(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """NORMAL when spend is under all thresholds."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "0.50",
            "cost:current_month": "1.00",
        })

        status = await enforcer.check_budget("exa")
        assert status.alert_level == "NORMAL"

    @pytest.mark.asyncio
    async def test_warning_when_monthly_at_3(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """WARNING when monthly >= $3."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "0.50",
            "cost:current_month": "3.00",
        })

        status = await enforcer.check_budget("exa")
        assert status.alert_level == "WARNING"

    @pytest.mark.asyncio
    async def test_critical_when_monthly_at_15(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """CRITICAL when monthly >= $15."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "1.00",
            "cost:current_month": "15.00",
        })

        status = await enforcer.check_budget("exa")
        assert status.alert_level == "CRITICAL"

    @pytest.mark.asyncio
    async def test_hard_stop_when_monthly_at_25(
        self, enforcer: BudgetEnforcer, mock_redis: MagicMock
    ) -> None:
        """HARD_STOP when monthly >= $25 (but absolute block at $30)."""
        _make_redis_get(mock_redis, {
            "tool:cost:exa:2026-06-03": "0.50",
            "cost:current_month": "25.00",
        })

        status = await enforcer.check_budget("exa")
        assert status.alert_level == "HARD_STOP"
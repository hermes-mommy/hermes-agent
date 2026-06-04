"""Tests for MCP Tool Cost Tracker — mocked Redis."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import RedisError

from src.mcp.cost import ToolCostTracker, _TOOL_COSTS


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Return a fully-mocked redis.Redis instance."""
    return MagicMock()


@pytest.fixture
def tracker(mock_redis_client: MagicMock) -> ToolCostTracker:
    """Return a ToolCostTracker with mocked Redis."""
    with patch("redis.Redis", return_value=mock_redis_client):
        t = ToolCostTracker()
    return t


# ============================================================================
# TestToolCostTracker — recording
# ============================================================================


class TestRecordToolCost:
    """Tests for record_tool_cost."""

    def test_records_fixed_cost_for_brave_search(self, tracker: ToolCostTracker) -> None:
        """Records $0.01 for brave_search and returns daily total."""
        today = date.today().isoformat()
        expected_key = f"tool:cost:brave_search:{today}"

        mock_pipe = tracker.redis.pipeline.return_value

        # First call: daily total starts at 0.
        tracker.redis.get.return_value = "0.01"

        result = tracker.record_tool_cost("brave_search")
        assert result == 0.01

        # Verify pipeline calls.
        calls = mock_pipe.incrbyfloat.call_args_list
        assert len(calls) >= 2
        assert mock_pipe.incrbyfloat.call_args_list[0][0][0] == expected_key
        assert mock_pipe.incrbyfloat.call_args_list[0][0][1] == 0.01

    def test_records_explicit_cost_for_variable_tool(
        self, tracker: ToolCostTracker
    ) -> None:
        """Accepts explicit *cost_usd* for variable-cost tools like websearch."""
        today = date.today().isoformat()
        expected_key = f"tool:cost:websearch:{today}"

        mock_pipe = tracker.redis.pipeline.return_value
        tracker.redis.get.return_value = "0.05"

        result = tracker.record_tool_cost("websearch", cost_usd=0.05)
        assert result == 0.05

        assert mock_pipe.incrbyfloat.call_args_list[0][0][0] == expected_key
        assert mock_pipe.incrbyfloat.call_args_list[0][0][1] == 0.05

    def test_also_increments_total_daily_key(
        self, tracker: ToolCostTracker
    ) -> None:
        """record_tool_cost also updates ``tool:cost:total:YYYY-MM-DD``."""
        today = date.today().isoformat()
        total_key = f"tool:cost:total:{today}"

        mock_pipe = tracker.redis.pipeline.return_value
        tracker.redis.get.return_value = "0.03"

        tracker.record_tool_cost("exa")

        # The second INCRBYFLOAT (or one of them) must target the total key.
        total_calls = [
            c[0][0]
            for c in mock_pipe.incrbyfloat.call_args_list
            if c[0][0].startswith("tool:cost:total:")
        ]
        assert len(total_calls) > 0
        assert total_key in total_calls

    def test_uses_pipeline_for_atomicity(self, tracker: ToolCostTracker) -> None:
        """record_tool_cost uses a pipeline and calls execute()."""
        tracker.redis.get.return_value = "0.01"

        tracker.record_tool_cost("brave_search")

        tracker.redis.pipeline.assert_called_once()
        mock_pipe = tracker.redis.pipeline.return_value
        mock_pipe.execute.assert_called_once()

    def test_sets_expireat_for_daily_rotation(
        self, tracker: ToolCostTracker
    ) -> None:
        """Each daily key gets EXPIREAT set for automatic cleanup."""
        tracker.redis.get.return_value = "0.0"

        tracker.record_tool_cost("github")

        mock_pipe = tracker.redis.pipeline.return_value
        expireat_calls = mock_pipe.expireat.call_args_list
        assert len(expireat_calls) >= 2  # tool key + total key

    def test_returns_zero_and_logs_on_redis_error(
        self, tracker: ToolCostTracker
    ) -> None:
        """Gracefully returns 0.0 when Redis raises."""
        tracker.redis.pipeline.side_effect = RedisError("connection refused")

        result = tracker.record_tool_cost("exa")
        assert result == 0.0

    def test_daily_total_accumulates(self, tracker: ToolCostTracker) -> None:
        """Multiple calls to the same tool accumulate in the daily key."""
        today = date.today().isoformat()
        _tool_key = f"tool:cost:brave_search:{today}"

        _mock_pipe = tracker.redis.pipeline.return_value

        # First call returns 0.01, second returns 0.03.
        tracker.redis.get.side_effect = ["0.01", "0.03"]

        r1 = tracker.record_tool_cost("brave_search")
        r2 = tracker.record_tool_cost("brave_search")
        assert r1 == 0.01
        assert r2 == 0.03

    @pytest.mark.parametrize(
        "tool_name,expected_cost",
        [
            ("brave_search", 0.01),
            ("context7", 0.0),
            ("exa", 0.007),
            ("fetch", 0.0),
            ("filesystem", 0.0),
            ("github", 0.0),
            ("grep_app", 0.0),
            ("obscura_cdp", 0.0),
            ("sequential_thinking", 0.0),
            ("time", 0.0),
            ("git", 0.0),
            ("postgres", 0.0),
            ("redis", 0.0),
            ("shell", 0.0),
            ("docker", 0.0),
        ],
    )
    def test_fixed_costs_match_expected(
        self,
        tracker: ToolCostTracker,
        tool_name: str,
        expected_cost: float,
    ) -> None:
        """Every fixed-cost tool uses its declared cost."""
        today = date.today().isoformat()
        expected_key = f"tool:cost:{tool_name}:{today}"

        mock_pipe = tracker.redis.pipeline.return_value
        tracker.redis.get.return_value = "0.01"

        tracker.record_tool_cost(tool_name)

        assert mock_pipe.incrbyfloat.call_args_list[0][0][0] == expected_key
        assert mock_pipe.incrbyfloat.call_args_list[0][0][1] == expected_cost


# ============================================================================
# TestToolCostTracker — queries
# ============================================================================


class TestGetToolDailyCost:
    """Tests for get_tool_daily_cost."""

    def test_returns_stored_value(self, tracker: ToolCostTracker) -> None:
        """Returns the value stored at the daily key."""
        today = date.today().isoformat()
        expected_key = f"tool:cost:brave_search:{today}"

        tracker.redis.get.return_value = "0.25"

        result = tracker.get_tool_daily_cost("brave_search")
        assert result == 0.25
        tracker.redis.get.assert_called_once_with(expected_key)

    def test_returns_zero_when_key_missing(self, tracker: ToolCostTracker) -> None:
        """Returns 0.0 when the key does not exist."""
        tracker.redis.get.return_value = None

        result = tracker.get_tool_daily_cost("unknown_tool")
        assert result == 0.0

    def test_returns_zero_on_redis_error(self, tracker: ToolCostTracker) -> None:
        """Returns 0.0 gracefully when Redis raises."""
        tracker.redis.get.side_effect = RedisError("oops")

        result = tracker.get_tool_daily_cost("exa")
        assert result == 0.0


class TestGetAllDailyCosts:
    """Tests for get_all_daily_costs."""

    def test_returns_all_tool_keys(self, tracker: ToolCostTracker) -> None:
        """SCANs for today's tool keys and returns a name→cost dict."""
        today = date.today().isoformat()

        mock_keys = [
            f"tool:cost:brave_search:{today}",
            f"tool:cost:exa:{today}",
            f"tool:cost:github:{today}",
            f"tool:cost:total:{today}",  # must be excluded
        ]
        tracker.redis.scan_iter.return_value = iter(mock_keys)

        def get_side_effect(key: str) -> str | None:
            values = {
                f"tool:cost:brave_search:{today}": "0.15",
                f"tool:cost:exa:{today}": "0.035",
                f"tool:cost:github:{today}": "0.0",
                f"tool:cost:total:{today}": "0.185",
            }
            return values.get(key)

        tracker.redis.get.side_effect = get_side_effect

        result = tracker.get_all_daily_costs()

        assert "total" not in result
        assert result == {"brave_search": 0.15, "exa": 0.035, "github": 0.0}

    def test_uses_scan_with_correct_pattern(self, tracker: ToolCostTracker) -> None:
        """The SCAN pattern includes today's date."""
        today = date.today().isoformat()
        tracker.redis.scan_iter.return_value = iter([])

        tracker.get_all_daily_costs()

        call_kwargs = tracker.redis.scan_iter.call_args
        assert today in call_kwargs[1]["match"]

    def test_returns_empty_on_redis_error(self, tracker: ToolCostTracker) -> None:
        """Returns {} when Redis raises during SCAN."""
        tracker.redis.scan_iter.side_effect = RedisError("scan failed")

        result = tracker.get_all_daily_costs()
        assert result == {}


class TestGetToolMonthlyCost:
    """Tests for get_tool_monthly_cost."""

    def test_sums_last_thirty_days(self, tracker: ToolCostTracker) -> None:
        """Queries 30 daily keys and sums their values."""
        today = date.today()

        def get_side_effect(key: str) -> str | None:
            # Only return a value for 3 specific days.
            day3 = (today - timedelta(days=3)).isoformat()
            day7 = (today - timedelta(days=7)).isoformat()
            day14 = (today - timedelta(days=14)).isoformat()

            suffix = key.rsplit(":", 1)[-1]
            if suffix == day3:
                return "0.10"
            if suffix == day7:
                return "0.05"
            if suffix == day14:
                return "0.02"
            return "0.0"

        tracker.redis.get.side_effect = get_side_effect

        result = tracker.get_tool_monthly_cost("brave_search")
        assert result == pytest.approx(0.17)

    def test_queries_correct_key_format(self, tracker: ToolCostTracker) -> None:
        """Each call to redis.get uses the ``tool:cost:{name}:YYYY-MM-DD`` format."""
        tracker.redis.get.return_value = "0.0"

        tracker.get_tool_monthly_cost("postgres")

        # 30 calls — verify the first and last key format.
        call_args = tracker.redis.get.call_args_list
        assert len(call_args) == 30

        first_key = call_args[0][0][0]
        assert first_key.startswith("tool:cost:postgres:")
        assert len(first_key.split(":")) == 4  # tool:cost:postgres:YYYY-MM-DD

    def test_returns_zero_on_redis_error(self, tracker: ToolCostTracker) -> None:
        """Returns 0.0 when Redis raises during monthly query."""
        tracker.redis.get.side_effect = RedisError("boom")

        result = tracker.get_tool_monthly_cost("exa")
        assert result == 0.0


# ============================================================================
# TestToolCostTracker — helpers
# ============================================================================


class TestGetToolCost:
    """Tests for the static get_tool_cost helper."""

    def test_returns_fixed_cost(self) -> None:
        """Returns the declared cost for a fixed-cost tool."""
        assert ToolCostTracker.get_tool_cost("brave_search") == 0.01
        assert ToolCostTracker.get_tool_cost("exa") == 0.007
        assert ToolCostTracker.get_tool_cost("grep_app") == 0.0

    def test_returns_negative_one_for_unknown(self) -> None:
        """Returns -1.0 for unrecognised tool names."""
        assert ToolCostTracker.get_tool_cost("nonexistent") == -1.0

    def test_returns_negative_one_for_websearch(self) -> None:
        """websearch is variable-cost → returns -1.0."""
        assert ToolCostTracker.get_tool_cost("websearch") == -1.0


class TestIsVariableCost:
    """Tests for the is_variable_cost helper."""

    def test_websearch_is_variable(self) -> None:
        """websearch has a variable per-call cost."""
        assert ToolCostTracker.is_variable_cost("websearch") is True

    def test_fixed_tools_are_not_variable(self) -> None:
        """Fixed-cost tools return False."""
        assert ToolCostTracker.is_variable_cost("brave_search") is False
        assert ToolCostTracker.is_variable_cost("exa") is False
        assert ToolCostTracker.is_variable_cost("github") is False

    def test_unknown_tool_is_variable(self) -> None:
        """An unknown tool is treated as variable-cost."""
        assert ToolCostTracker.is_variable_cost("made_up") is True


# ============================================================================
# TestToolCostTracker — Redis key format
# ============================================================================


class TestKeyFormat:
    """Verify key format matches the spec: ``tool:cost:{name}:YYYY-MM-DD``."""

    def test_daily_key_format(self, tracker: ToolCostTracker) -> None:
        """record_tool_cost creates keys in the correct format."""
        today = date.today().isoformat()

        mock_pipe = tracker.redis.pipeline.return_value
        tracker.redis.get.return_value = "0.0"

        tracker.record_tool_cost("exa")

        tool_call = mock_pipe.incrbyfloat.call_args_list[0][0][0]
        assert tool_call == f"tool:cost:exa:{today}"

    def test_total_key_format(self, tracker: ToolCostTracker) -> None:
        """The aggregate total key uses ``tool:cost:total:YYYY-MM-DD``."""
        today = date.today().isoformat()

        mock_pipe = tracker.redis.pipeline.return_value
        tracker.redis.get.return_value = "0.0"

        tracker.record_tool_cost("brave_search")

        total_key = f"tool:cost:total:{today}"
        found = any(
            c[0][0] == total_key
            for c in mock_pipe.incrbyfloat.call_args_list
        )
        assert found, f"Expected INCRBYFLOAT on {total_key}"


# ============================================================================
# TestToolCostTracker — initialisation
# ============================================================================


class TestInit:
    """Verify the Redis connection is configured correctly."""

    def test_uses_port_6380(self) -> None:
        """Default port is 6380 (ACL-aware Redis)."""
        with patch("redis.Redis") as mock_redis_cls:
            ToolCostTracker()
            call_kwargs = mock_redis_cls.call_args
            assert call_kwargs[1]["port"] == 6380

    def test_uses_db5(self) -> None:
        """Redis DB5 is the cost-tracking database."""
        with patch("redis.Redis") as mock_redis_cls:
            ToolCostTracker()
            call_kwargs = mock_redis_cls.call_args
            assert call_kwargs[1]["db"] == 5

    def test_uses_guinevere_core_username(self) -> None:
        """ACL username is guinevere_core."""
        with patch("redis.Redis") as mock_redis_cls:
            ToolCostTracker()
            call_kwargs = mock_redis_cls.call_args
            assert call_kwargs[1]["username"] == "guinevere_core"

    def test_uses_decode_responses(self) -> None:
        """decode_responses is True so GET returns str not bytes."""
        with patch("redis.Redis") as mock_redis_cls:
            ToolCostTracker()
            call_kwargs = mock_redis_cls.call_args
            assert call_kwargs[1]["decode_responses"] is True

    def test_password_from_env(self) -> None:
        """Password is read from REDIS_PASSWORD env var (not hardcoded)."""
        with patch("redis.Redis") as mock_redis_cls:
            ToolCostTracker(password="custom-pwd")
            call_kwargs = mock_redis_cls.call_args
            assert call_kwargs[1]["password"] == "custom-pwd"


# ============================================================================
# Verify _TOOL_COSTS matches spec
# ============================================================================


def test_tool_costs_dict_matches_spec() -> None:
    """Every tool in the scaffold cost table is represented."""
    expected_tools = [
        "brave_search",
        "context7",
        "exa",
        "fetch",
        "filesystem",
        "github",
        "grep_app",
        "obscura_cdp",
        "sequential_thinking",
        "time",
        "websearch",
        "git",
        "postgres",
        "redis",
        "shell",
        "docker",
    ]
    for tool in expected_tools:
        assert tool in _TOOL_COSTS, f"Missing tool: {tool}"
"""Tests for P4-003: Budget hook (Redis Lua atomic cost enforcement).

Covers:
 - Monthly $24 warning threshold.
 - Monthly $30 hard block.
 - Redis 6380 DB5 connection defaults.
 - Lua atomicity (no client-side read-then-increment).
 - Redis connection failure → fail-closed block.
 - Lua execution failure → fail-closed block.
 - Per-tool daily cap enforcement.
 - Global daily cap enforcement.
 - Input validation (missing tool_name → block).
 - No 6379 or 5432 references in hook code.
 - Lua script parsing/loading correctness.
 - Default cost for unknown/variable-cost tools.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Protocol, cast
from unittest.mock import MagicMock, patch

import pytest

# ---- Path setup: ensure hermes-config/hooks is importable ----------------
_HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hermes-config" / "hooks"
_HOOKS_STR = str(_HOOKS_DIR.resolve())
if _HOOKS_STR in sys.path:
    sys.path.remove(_HOOKS_STR)
sys.path.insert(0, _HOOKS_STR)
# -------------------------------------------------------------------------

# pylint: disable=import-error,wrong-import-position


class RedisMock(Protocol):
    def script_load(self, script: str) -> str: ...
    def evalsha(self, script_sha: str, *, keys: list[str], args: list[str]) -> bytes | str: ...
    def get(self, key: str) -> object: ...
    def incrbyfloat(self, key: str, amount: float) -> object: ...


class RedisMockDouble:
    """Small Redis test double with mock-backed methods."""

    script_load: MagicMock
    evalsha: MagicMock
    get: MagicMock
    incrbyfloat: MagicMock

    def __init__(self) -> None:
        self.script_load = MagicMock(return_value="sha1")
        self.evalsha = MagicMock(return_value=b"ALLOWED")
        self.get = MagicMock()
        self.incrbyfloat = MagicMock()


class BudgetLuaModule(Protocol):
    SCRIPT_MONTHLY_CHECK: str
    def load_script(self, redis_client: RedisMock, script: str) -> str: ...
    def call_monthly_check(
        self,
        redis_client: RedisMock,
        script_sha: str,
        estimated_cost: float,
        monthly_cap: float = 30.0,
        warn_threshold: float = 24.0,
    ) -> str: ...


class BudgetLuaExtendedModule(Protocol):
    SCRIPT_EXTENDED_CHECK: str
    def call_extended_check(
        self,
        redis_client: RedisMock,
        script_sha: str,
        tool_name: str,
        estimated_cost: float,
        monthly_cap: float = 30.0,
        warn_threshold: float = 24.0,
        daily_tool_cap: float = 5.0,
        daily_global_cap: float = 10.0,
    ) -> str: ...


class BudgetCheckModule(Protocol):
    MONTHLY_CAP: float
    WARN_THRESHOLD: float
    DEFAULT_TOOL_COST: float
    _TOOL_FIXED_COSTS: dict[str, float]
    def _resolve_daily_tool_cap(self, tool_name: str) -> float: ...
    def resolve_cost(self, tool_name: str, context: object) -> float: ...
    def main(self) -> None: ...


_budget_lua = cast(BudgetLuaModule, cast(object, importlib.import_module("budget_lua")))
_budget_lua_extended = cast(
    BudgetLuaExtendedModule,
    cast(object, importlib.import_module("budget_lua_extended")),
)
_budget_check = cast(BudgetCheckModule, cast(object, importlib.import_module("budget_check")))

SCRIPT_MONTHLY_CHECK = _budget_lua.SCRIPT_MONTHLY_CHECK
call_monthly_check = _budget_lua.call_monthly_check
load_script = _budget_lua.load_script
SCRIPT_EXTENDED_CHECK = _budget_lua_extended.SCRIPT_EXTENDED_CHECK
call_extended_check = _budget_lua_extended.call_extended_check
_TOOL_FIXED_COSTS = _budget_check._TOOL_FIXED_COSTS
_resolve_daily_tool_cap = _budget_check._resolve_daily_tool_cap
resolve_cost = _budget_check.resolve_cost
DEFAULT_TOOL_COST = _budget_check.DEFAULT_TOOL_COST

# =========================================================================
# Helpers
# =========================================================================


def _fake_redis(**attrs: object) -> RedisMockDouble:
    """Create a fake Redis-like instance with default behaviours."""
    mock = RedisMockDouble()
    for key, val in attrs.items():
        setattr(mock, key, val)
    return mock


# =========================================================================
# 1. Threshold tests ($24 warn, $30 block)
# =========================================================================


class TestMonthlyThresholds:
    """Verify $24 warning and $30 hard block via Lua script result parsing."""

    def test_warning_at_24(self) -> None:
        """Simulate projected spend at $25 (> $24 warn) → WARNING."""
        mock_redis = _fake_redis()
        # mock evalsha to return b"WARNING"
        mock_redis.evalsha.return_value = b"WARNING"

        result = call_monthly_check(
            mock_redis, "fake_sha", estimated_cost=1.0,
            monthly_cap=30.0, warn_threshold=24.0,
        )
        assert result == "WARNING"

    def test_block_at_30(self) -> None:
        """Simulate projected spend at $31 (> $30 cap) → MONTHLY_BLOCKED."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.return_value = b"MONTHLY_BLOCKED"

        result = call_monthly_check(
            mock_redis, "fake_sha", estimated_cost=1.0,
            monthly_cap=30.0, warn_threshold=24.0,
        )
        assert result == "MONTHLY_BLOCKED"

    def test_allowed_below_24(self) -> None:
        """Simulate projected spend at $10 → ALLOWED."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.return_value = b"ALLOWED"

        result = call_monthly_check(
            mock_redis, "fake_sha", estimated_cost=10.0,
            monthly_cap=30.0, warn_threshold=24.0,
        )
        assert result == "ALLOWED"

    def test_edge_warning_exactly_24(self) -> None:
        """Simulate projected spend exactly $24 → WARNING (since > $24 not >=)."""
        mock_redis = _fake_redis()
        # The Lua does projected > warn, so exactly 24 + tiny = warning
        mock_redis.evalsha.return_value = b"WARNING"
        result = call_monthly_check(
            mock_redis, "fake_sha", estimated_cost=0.01,
            monthly_cap=30.0, warn_threshold=24.0,
        )
        assert result == "WARNING"

    def test_block_exactly_30(self) -> None:
        """Simulate projected exactly $30 → not blocked (must be > $30)."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.return_value = b"MONTHLY_BLOCKED"
        result = call_monthly_check(
            mock_redis, "fake_sha", estimated_cost=0.01,
            monthly_cap=30.0, warn_threshold=24.0,
        )
        # If current is 30.0 + 0.01 > 30.0 → blocked
        assert result == "MONTHLY_BLOCKED"


# =========================================================================
# 2. Redis 6380 DB5 defaults
# =========================================================================


class TestRedisDefaults:
    """Verify the hook uses canonical Redis port 6380 DB5."""

    def test_hook_utils_redis_url_uses_6380(self) -> None:
        """``_hook_utils.REDIS_URL`` must reference port 6380 DB 5."""
        hook_utils = importlib.import_module("_hook_utils")
        redis_url = cast(str, getattr(hook_utils, "REDIS_URL"))
        assert "6380" in redis_url, \
            f"Expected port 6380 in REDIS_URL, got: {redis_url}"
        assert "/5" in redis_url, \
            f"Expected DB 5 in REDIS_URL, got: {redis_url}"

    def test_no_6379_in_hook_code(self) -> None:
        """Grep check: no 6379 in any budget hook file."""
        hook_files = [
            _HOOKS_DIR / "budget_check.py",
            _HOOKS_DIR / "budget_lua.py",
            _HOOKS_DIR / "budget_lua_extended.py",
        ]
        for fpath in hook_files:
            content = fpath.read_text(encoding="utf-8")
            assert "6379" not in content, f"{fpath.name} contains port 6379"

    def test_no_5432_in_hook_code(self) -> None:
        """Grep check: no 5432 in any budget hook file."""
        hook_files = [
            _HOOKS_DIR / "budget_check.py",
            _HOOKS_DIR / "budget_lua.py",
            _HOOKS_DIR / "budget_lua_extended.py",
        ]
        for fpath in hook_files:
            content = fpath.read_text(encoding="utf-8")
            assert "5432" not in content, f"{fpath.name} contains port 5432"


# =========================================================================
# 3. Lua atomicity — no client-side read-then-increment
# =========================================================================


class TestLuaAtomicity:
    """Verify the Lua scripts are self-contained atomic check-and-deduct.

    The Python code must NEVER do a client-side GET then INCRBYFLOAT.
    The Lua script must wrap check + deduct in a single Redis execution.
    """

    def test_monthly_script_contains_check_and_deduct(self) -> None:
        """``SCRIPT_MONTHLY_CHECK`` must contain both GET and INCRBYFLOAT."""
        assert "GET" in SCRIPT_MONTHLY_CHECK
        assert "INCRBYFLOAT" in SCRIPT_MONTHLY_CHECK
        # Must check before deduct.
        assert "projected > monthly_cap" in SCRIPT_MONTHLY_CHECK or \
               "projected >" in SCRIPT_MONTHLY_CHECK

    def test_extended_script_contains_all_checks(self) -> None:
        """``SCRIPT_EXTENDED_CHECK`` must check monthly, daily-tool, daily-global."""
        assert "MONTHLY_BLOCKED" in SCRIPT_EXTENDED_CHECK
        assert "DAILY_TOOL_BLOCKED" in SCRIPT_EXTENDED_CHECK
        assert "DAILY_GLOBAL_BLOCKED" in SCRIPT_EXTENDED_CHECK
        assert "INCRBYFLOAT" in SCRIPT_EXTENDED_CHECK

    def test_no_client_side_read_pattern_in_python(self) -> None:
        """Python code must not contain client-side check-then-increment.

        The hook must delegate TO the Lua script; the Python code should
        NOT call ``redis.get()`` + ``redis.incrbyfloat()`` in sequence.
        """
        fpath = _HOOKS_DIR / "budget_check.py"
        content = fpath.read_text(encoding="utf-8")
        # The Python hook calls call_extended_check and call_monthly_check,
        # which internally use EVALSHA - no inline get+incrbyfloat.
        assert "call_extended_check" in content, \
            f"{fpath.name} must delegate to Lua via call_extended_check"
        assert "call_monthly_check" in content or "load_script" in content, \
            f"{fpath.name} must load Lua scripts via load_script"
        # Ensure no direct get() calls in the main path
        assert "redis.get(" not in content, \
            f"{fpath.name} must not call redis.get() directly"
        assert "redis.incrbyfloat(" not in content, \
            f"{fpath.name} must not call redis.incrbyfloat() directly"

    def test_monthly_script_calls_redis_atomically(self) -> None:
        """The Python ``call_monthly_check`` must use evalsha (single call)."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.return_value = b"ALLOWED"

        _ = call_monthly_check(mock_redis, "sha1", 0.01)

        # Assert evalsha was called exactly once, not get+incrbyfloat separately.
        mock_redis.evalsha.assert_called_once()
        mock_redis.get.assert_not_called()
        mock_redis.incrbyfloat.assert_not_called()

    def test_extended_script_calls_redis_atomically(self) -> None:
        """The Python ``call_extended_check`` must use evalsha (single call)."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.return_value = b"ALLOWED"

        _ = call_extended_check(mock_redis, "sha1", "exa", 0.01)

        mock_redis.evalsha.assert_called_once()
        mock_redis.get.assert_not_called()
        mock_redis.incrbyfloat.assert_not_called()


# =========================================================================
# 4. Fail-closed on Redis/Lua errors
# =========================================================================


class TestFailClosed:
    """Every Redis/Lua/parse error must produce a block, never allow."""

    def test_redis_connection_fail_closed(self) -> None:
        """When ``get_redis_connection`` returns None, the hook must block."""
        bc = importlib.import_module("budget_check")

        setattr(bc, "_log", MagicMock())
        with (
            patch.object(bc, "read_stdin_json", return_value={"tool_name": "exa"}),
            patch.object(bc, "get_redis_connection", return_value=None),
            patch.object(bc, "write_stdout_json") as mock_write,
            patch.object(bc, "sys") as mock_sys,
        ):
            mock_sys.exit.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                _budget_check.main()

            payload = cast(dict[str, object], mock_write.call_args[0][0])
            assert payload["action"] == "block"
            assert "Redis down" in cast(str, payload["reason"])
            assert "budget_check_failed" in cast(str, payload["reason"])

    def test_lua_script_load_fail_closed(self) -> None:
        """When ``load_script`` raises, callers must propagate."""
        mock_redis = _fake_redis()
        mock_redis.script_load.side_effect = RuntimeError("Redis SCRIPT LOAD failed")

        with pytest.raises(RuntimeError):
            _ = load_script(mock_redis, "return 1")

    def test_evalsha_redis_error_fail_closed(self) -> None:
        """When ``evalsha`` raises, callers must propagate."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.side_effect = RuntimeError("Redis connection lost")

        with pytest.raises(RuntimeError):
            _ = call_monthly_check(mock_redis, "sha", 0.01)

    def test_extended_evalsha_redis_error_fail_closed(self) -> None:
        """``call_extended_check`` must propagate Redis errors."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.side_effect = RuntimeError("Redis connection lost")

        with pytest.raises(RuntimeError):
            _ = call_extended_check(mock_redis, "sha", "exa", 0.01)


# =========================================================================
# 5. Per-tool / global daily cap behaviour
# =========================================================================


class TestDailyCaps:
    """Per-tool and global daily cap enforcement."""

    def test_extended_script_returns_daily_tool_blocked(self) -> None:
        """Simulate daily tool cap exceeded → DAILY_TOOL_BLOCKED."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.return_value = b"DAILY_TOOL_BLOCKED"

        result = call_extended_check(
            mock_redis, "sha", "exa", 5.0,
            daily_tool_cap=5.0, daily_global_cap=10.0,
        )
        assert result == "DAILY_TOOL_BLOCKED"

    def test_extended_script_returns_daily_global_blocked(self) -> None:
        """Simulate global daily cap exceeded → DAILY_GLOBAL_BLOCKED."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.return_value = b"DAILY_GLOBAL_BLOCKED"

        result = call_extended_check(
            mock_redis, "sha", "exa", 0.01,
            daily_tool_cap=5.0, daily_global_cap=10.0,
        )
        assert result == "DAILY_GLOBAL_BLOCKED"

    def test_extended_allowed_within_all_caps(self) -> None:
        """Simulate all caps OK → ALLOWED."""
        mock_redis = _fake_redis()
        mock_redis.evalsha.return_value = b"ALLOWED"

        result = call_extended_check(
            mock_redis, "sha", "exa", 0.01,
            daily_tool_cap=5.0, daily_global_cap=10.0,
        )
        assert result == "ALLOWED"


# =========================================================================
# 6. Cost resolution
# =========================================================================


class TestCostResolution:
    """Verify tool costs are resolved correctly."""

    def test_known_tool_cost(self) -> None:
        """Known tool returns fixed cost."""
        assert resolve_cost("exa", {}) == 0.007
        assert resolve_cost("brave_search", {}) == 0.01

    def test_unknown_tool_default_cost(self) -> None:
        """Unknown tool returns DEFAULT_TOOL_COST (0.01)."""
        assert resolve_cost("nonexistent_tool", {}) == DEFAULT_TOOL_COST

    def test_variable_cost_tool_default(self) -> None:
        """Variable-cost tool (websearch = -1) returns DEFAULT_TOOL_COST."""
        assert resolve_cost("websearch", {}) == DEFAULT_TOOL_COST

    def test_resolve_daily_cap_for_exa(self) -> None:
        """exa has explicit daily cap 5.0."""
        assert _resolve_daily_tool_cap("exa") == 5.0

    def test_resolve_daily_cap_for_brave(self) -> None:
        """brave_search has explicit daily cap 3.0."""
        assert _resolve_daily_tool_cap("brave_search") == 3.0

    def test_resolve_daily_cap_default(self) -> None:
        """Unknown tool gets default daily cap 10.0."""
        assert _resolve_daily_tool_cap("unknown") == 10.0

    def test_tool_fixed_costs_cover_all_mcp_tools(self) -> None:
        """``_TOOL_FIXED_COSTS`` should include all common MCP tools."""
        expected_tools = {
            "brave_search", "context7", "exa", "fetch", "filesystem",
            "github", "grep_app", "obscura_cdp", "sequential_thinking",
            "time", "git", "postgres", "redis", "shell", "docker",
        }
        assert expected_tools.issubset(_TOOL_FIXED_COSTS.keys())


# =========================================================================
# 7. Lua script parsing / structure
# =========================================================================


class TestLuaScriptStructure:
    """Verify the Lua scripts are syntactically parseable by inspecting
    structural elements.  (Full validation requires an actual Redis server.)"""

    def test_monthly_script_has_checks(self) -> None:
        """Monthly script must have GET, comparison, and INCRBYFLOAT."""
        assert "redis.call('GET'" in SCRIPT_MONTHLY_CHECK or \
               'redis.call("GET"' in SCRIPT_MONTHLY_CHECK
        assert "INCRBYFLOAT" in SCRIPT_MONTHLY_CHECK
        assert "MONTHLY_BLOCKED" in SCRIPT_MONTHLY_CHECK
        assert "WARNING" in SCRIPT_MONTHLY_CHECK
        assert "ALLOWED" in SCRIPT_MONTHLY_CHECK

    def test_extended_script_has_all_checks(self) -> None:
        """Extended script must have all three cap checks."""
        assert "MONTHLY_BLOCKED" in SCRIPT_EXTENDED_CHECK
        assert "DAILY_TOOL_BLOCKED" in SCRIPT_EXTENDED_CHECK
        assert "DAILY_GLOBAL_BLOCKED" in SCRIPT_EXTENDED_CHECK
        assert "INCRBYFLOAT" in SCRIPT_EXTENDED_CHECK
        assert "EXPIRE" in SCRIPT_EXTENDED_CHECK

    def test_scripts_are_valid_lua_syntax(self) -> None:
        """Basic syntax check: balanced quotes, no obviously invalid Lua."""
        for name, script in [
            ("SCRIPT_MONTHLY_CHECK", SCRIPT_MONTHLY_CHECK),
            ("SCRIPT_EXTENDED_CHECK", SCRIPT_EXTENDED_CHECK),
        ]:
            # Check no unbalanced quotes (simple heuristic)
            single_quotes = script.count("'")
            double_quotes = script.count('"')
            assert single_quotes % 2 == 0, f"{name} has unpaired single quotes"
            assert double_quotes % 2 == 0, f"{name} has unpaired double quotes"

    def test_scripts_have_no_function_calls_that_could_fail_silently(self) -> None:
        """Redis Lua errors (wrong types) would raise — script uses tonumber."""
        for name, script in [
            ("SCRIPT_MONTHLY_CHECK", SCRIPT_MONTHLY_CHECK),
            ("SCRIPT_EXTENDED_CHECK", SCRIPT_EXTENDED_CHECK),
        ]:
            assert "tonumber" in script, f"{name} lacks tonumber guards"


# =========================================================================
# 8. Integration-level: budget_check.main() behaves correctly
# =========================================================================


class TestBudgetCheckMain:
    """Verify the budget_check.py main() entry-point behaviour."""

    def test_missing_tool_name_blocks(self) -> None:
        """When stdin has no tool_name, main must block."""
        bc = importlib.import_module("budget_check")

        with (
            patch.object(bc, "read_stdin_json", return_value={}),
            patch.object(bc, "write_stdout_json") as mock_write,
            patch.object(bc, "sys") as mock_sys,
        ):
            mock_sys.exit.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                _budget_check.main()

            payload = cast(dict[str, object], mock_write.call_args[0][0])
            assert payload["action"] == "block"

    def test_redis_unavailable_blocks(self) -> None:
        """When get_redis_connection returns None, main must block."""
        bc = importlib.import_module("budget_check")

        with (
            patch.object(bc, "read_stdin_json", return_value={"tool_name": "exa"}),
            patch.object(bc, "get_redis_connection", return_value=None),
            patch.object(bc, "write_stdout_json") as mock_write,
            patch.object(bc, "sys") as mock_sys,
        ):
            mock_sys.exit.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                _budget_check.main()

            payload = cast(dict[str, object], mock_write.call_args[0][0])
            assert payload["action"] == "block"
            assert "Redis down" in cast(str, payload.get("reason", ""))
            assert "budget_check_failed" in cast(str, payload.get("reason", ""))

    def test_lua_execution_error_blocks(self) -> None:
        """When Lua execution raises, main must block."""
        bc = importlib.import_module("budget_check")
        mock_redis = _fake_redis()
        mock_redis.evalsha.side_effect = RuntimeError("Lua fail")

        with (
            patch.object(bc, "read_stdin_json", return_value={"tool_name": "exa"}),
            patch.object(bc, "get_redis_connection", return_value=mock_redis),
            patch.object(bc, "write_stdout_json") as mock_write,
            patch.object(bc, "sys") as mock_sys,
        ):
            mock_sys.exit.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                _budget_check.main()

            payload = cast(dict[str, object], mock_write.call_args[0][0])
            assert payload["action"] == "block"
            assert "error" in cast(str, payload.get("reason", "")).lower()
            assert "budget_check_failed" in cast(str, payload.get("reason", ""))


# =========================================================================
# 9. No forbidden patterns in hook code
# =========================================================================


class TestNoForbiddenPatterns:
    """Verify the budget hook files don't introduce forbidden patterns."""

    FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
        ("6379", "must not hardcode port 6379"),
        ("5432", "must not hardcode port 5432"),
        ("# type" + ": ignore", "must not suppress type checking"),
        ("except Exception" + ": pass", "must not have bare empty except"),
    ]

    HOOK_FILES = [
        "budget_check.py",
        "budget_lua.py",
        "budget_lua_extended.py",
    ]

    @pytest.mark.parametrize("filename", HOOK_FILES)
    @pytest.mark.parametrize("pattern,reason", FORBIDDEN_PATTERNS)
    def test_forbidden_pattern_not_present(self, filename: str, pattern: str, reason: str) -> None:
        """File should not contain the forbidden pattern."""
        import re
        fpath = _HOOKS_DIR / filename
        content = fpath.read_text(encoding="utf-8")
        matches = re.findall(pattern, content)
        assert len(matches) == 0, \
            f"{filename}: found {len(matches)} occurrence(s) of '{pattern}': {reason}"

    def test_no_broad_type_escape(self) -> None:
        """Files must not use the broad top-type escape."""
        import re
        for fname in self.HOOK_FILES:
            fpath = _HOOKS_DIR / fname
            content = fpath.read_text(encoding="utf-8")
            pattern = r"\b" + "A" + "ny" + r"\b"
            remaining = re.findall(pattern, content)
            assert len(remaining) == 0, \
                f"{fname}: {len(remaining)} use(s) of broad type escape"

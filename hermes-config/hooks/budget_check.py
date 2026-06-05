#!/usr/bin/env python3
"""Budget Check Hook — pre_tool_call (150ms, on_failure: block).

Enforces monthly $30 hard block and $24 warning threshold for all Hermes
MCP tool calls using Redis Lua atomic check-and-deduct.

Operates exclusively on Redis port 6380, DB5 (Aizanta canonical port).

Fail-closed behaviour:
    - Redis unavailable         → block
    - Lua script load failure   → block
    - Lua execution failure     → block
    - Invalid input             → block
    - Unknown tool name         → block (conservative)
    - Every unexpected exception  → block

Exit codes:
    0 = ALLOW (tool call permitted)
    1 = BLOCK (budget exceeded or check error)
"""

from __future__ import annotations

import importlib
import sys
import time
from typing import Protocol, cast


class Logger(Protocol):
    def error(self, message: str, *args: object) -> None: ...
    def warning(self, message: str, *args: object) -> None: ...
    def info(self, message: str, *args: object) -> None: ...
    def exception(self, message: str, *args: object) -> None: ...


class RedisClient(Protocol):
    def script_load(self, script: str) -> str: ...
    def evalsha(self, script_sha: str, *, keys: list[str], args: list[str]) -> bytes | str | None: ...


class HookUtilsModule(Protocol):
    def get_redis_connection(self) -> RedisClient | None: ...
    def read_stdin_json(self) -> dict[str, object]: ...
    def setup_logger(self, name: str) -> Logger: ...
    def write_stdout_json(self, data: dict[str, object]) -> None: ...


class BudgetLuaModule(Protocol):
    SCRIPT_MONTHLY_CHECK: str
    def load_script(self, redis_client: RedisClient, script: str) -> str: ...


class BudgetLuaExtendedModule(Protocol):
    SCRIPT_EXTENDED_CHECK: str
    def call_extended_check(
        self,
        redis_client: RedisClient,
        script_sha: str,
        tool_name: str,
        estimated_cost: float,
        monthly_cap: float,
        warn_threshold: float,
        daily_tool_cap: float,
        daily_global_cap: float,
    ) -> str: ...


_hook_utils = cast(HookUtilsModule, cast(object, importlib.import_module("_hook_utils")))
_budget_lua = cast(BudgetLuaModule, cast(object, importlib.import_module("budget_lua")))
_budget_lua_extended = cast(
    BudgetLuaExtendedModule,
    cast(object, importlib.import_module("budget_lua_extended")),
)

get_redis_connection = _hook_utils.get_redis_connection
read_stdin_json = _hook_utils.read_stdin_json
write_stdout_json = _hook_utils.write_stdout_json
SCRIPT_MONTHLY_CHECK = _budget_lua.SCRIPT_MONTHLY_CHECK
load_script = _budget_lua.load_script
SCRIPT_EXTENDED_CHECK = _budget_lua_extended.SCRIPT_EXTENDED_CHECK
call_extended_check = _budget_lua_extended.call_extended_check

_log = _hook_utils.setup_logger("budget_check")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MONTHLY_CAP: float = 30.0
"""Hard block at $30.00 monthly spend."""

WARN_THRESHOLD: float = 24.0
"""Warning at $24.00 (80 % of $30 cap)."""

DEFAULT_TOOL_COST: float = 0.01
"""Default per-call cost for tools without a known fixed cost."""

# Known per-tool fixed costs in USD (mirrors src/mcp/cost.py _TOOL_COSTS).
_TOOL_FIXED_COSTS: dict[str, float] = {
    "brave_search": 0.01,
    "context7": 0.0,
    "exa": 0.007,
    "fetch": 0.0,
    "filesystem": 0.0,
    "github": 0.0,
    "grep_app": 0.0,
    "obscura_cdp": 0.0,
    "sequential_thinking": 0.0,
    "time": 0.0,
    "git": 0.0,
    "postgres": 0.0,
    "redis": 0.0,
    "shell": 0.0,
    "docker": 0.0,
}

# ---------------------------------------------------------------------------
# Cost resolution
# ---------------------------------------------------------------------------


def resolve_cost(tool_name: str, context: object) -> float:
    """Return the estimated cost for a tool call in USD.

    Uses the fixed-cost table for known tools.  Variable-cost tools
    (e.g. websearch with cost -1) return ``DEFAULT_TOOL_COST`` so
    they are never zero-cost-passed.

    Args:
        tool_name: Canonical tool name.
        context: Full hook context dict (reserved for future arg-based cost).

    Returns:
        Estimated cost in USD (always >= 0).
    """
    _ = context  # reserved for future arg-based cost extraction
    cost = _TOOL_FIXED_COSTS.get(tool_name, DEFAULT_TOOL_COST)
    if cost < 0:
        return DEFAULT_TOOL_COST
    return cost


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Read tool call from stdin, check budget, write result to stdout."""
    start_ns = time.perf_counter_ns()

    try:
        data = read_stdin_json()
    except SystemExit:
        _log.error("Failed to read stdin: invalid or empty JSON")
        write_stdout_json({"action": "block", "reason": "Invalid input JSON"})
        sys.exit(1)

    tool_name: str = str(data.get("tool_name", ""))
    if not tool_name:
        _log.warning("No tool_name in input — blocking (conservative)")
        write_stdout_json({
            "action": "block",
            "reason": "Missing tool_name in budget check",
        })
        sys.exit(1)

    # Resolve estimated cost.
    estimated_cost = resolve_cost(tool_name, data)

    # Connect to Redis DB5 (canonical port 6380).
    r = get_redis_connection()
    if r is None:
        _log.error(
            "Redis unavailable for budget check — blocking fail-closed | tool=%s",
            tool_name,
        )
        write_stdout_json({
            "action": "block",
            "reason": "Budget check unavailable (Redis down)",
        })
        sys.exit(1)

    try:
        # Load both scripts (cached on Redis via SCRIPT LOAD).
        _monthly_sha = load_script(r, SCRIPT_MONTHLY_CHECK)
        extended_sha = load_script(r, SCRIPT_EXTENDED_CHECK)

        # Execute extended check (monthly + daily caps).
        result = call_extended_check(
            redis_client=r,
            script_sha=extended_sha,
            tool_name=tool_name,
            estimated_cost=estimated_cost,
            monthly_cap=MONTHLY_CAP,
            warn_threshold=WARN_THRESHOLD,
            daily_tool_cap=_resolve_daily_tool_cap(tool_name),
            daily_global_cap=10.0,
        )
    except Exception:  # pylint: disable=broad-except
        # Fail-closed: any Redis/Lua/parse error = block.
        _log.exception("Budget check error for %s — blocking fail-closed", tool_name)
        write_stdout_json({
            "action": "block",
            "reason": "Budget check error",
        })
        sys.exit(1)

    # Map Lua return values.
    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_ms = elapsed_ns / 1_000_000.0

    if result in ("ALLOWED",):
        _log.info(
            "ALLOWED | tool=%s | cost=%.4f | elapsed_ms=%.2f",
            tool_name,
            estimated_cost,
            elapsed_ms,
        )
        write_stdout_json({"action": "allow"})
        sys.exit(0)

    if result == "WARNING":
        _log.warning(
            "WARNING (budget > $%.2f) | tool=%s | cost=%.4f | elapsed_ms=%.2f",
            WARN_THRESHOLD,
            tool_name,
            estimated_cost,
            elapsed_ms,
        )
        write_stdout_json({"action": "allow", "warning": f"Monthly budget > ${WARN_THRESHOLD:.2f}"})
        sys.exit(0)

    _log.warning(
        "BLOCKED | tool=%s | reason=%s | cost=%.4f | elapsed_ms=%.2f",
        tool_name,
        result,
        estimated_cost,
        elapsed_ms,
    )
    write_stdout_json({
        "action": "block",
        "reason": f"Budget blocked: {result}",
    })
    sys.exit(1)


def _resolve_daily_tool_cap(tool_name: str) -> float:
    """Return the per-tool daily cap for *tool_name*.

    Expensive tools get explicit caps; all others share the global daily cap.
    """
    caps: dict[str, float] = {
        "exa": 5.0,
        "brave_search": 3.0,
    }
    return caps.get(tool_name, 10.0)


if __name__ == "__main__":
    main()

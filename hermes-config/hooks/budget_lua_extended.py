"""Extended Redis Lua scripts for Hermes budget with per-tool and global daily caps.

Extends the monthly-only check from ``budget_lua`` with additional per-tool
daily caps and a global daily cap enforce atomically in a single Redis Lua
execution.

Keys:
    KEYS[1]  = ``cost:current_month``          —  monthly running total
    KEYS[2]  = ``tool:cost:{name}:YYYY-MM-DD`` —  per-tool daily spend
    KEYS[3]  = ``cost:daily:YYYY-MM-DD``       —  global daily spend

Args:
    ARGV[1]  = estimated cost
    ARGV[2]  = monthly cap (default 30.00)
    ARGV[3]  = warn threshold (default 24.00)
    ARGV[4]  = per-tool daily cap (e.g. 5.0 for exa)
    ARGV[5]  = global daily cap (default 10.0)

Return values:
    ``"ALLOWED"``              — within all budgets, cost deducted
    ``"WARNING"``              — monthly above warn threshold, still deducted
    ``"MONTHLY_BLOCKED"``      — projected monthly would exceed cap
    ``"DAILY_TOOL_BLOCKED"``   — per-tool daily cap would be exceeded
    ``"DAILY_GLOBAL_BLOCKED"``  — global daily cap would be exceeded

All three keys are checked BEFORE any deduction.  Keys 2 and 3 get a 48-hour
TTL after the first write so they self-clean even if the caller forgets.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Final, Protocol


class RedisClient(Protocol):
    def evalsha(self, script_sha: str, *, keys: list[str], args: list[str]) -> bytes | str | None: ...


_log = logging.getLogger("hermes.hooks.budget_lua_extended")

# ---------------------------------------------------------------------------
# Lua: monthly + per-tool daily + global daily (extended)
# ---------------------------------------------------------------------------
SCRIPT_EXTENDED_CHECK: Final[str] = """
local estimated = tonumber(ARGV[1])
local monthly_cap = tonumber(ARGV[2])
local warn_threshold = tonumber(ARGV[3])
local daily_tool_cap = tonumber(ARGV[4])
local daily_global_cap = tonumber(ARGV[5])

local monthly = tonumber(redis.call('GET', KEYS[1]) or '0')
local daily_tool = tonumber(redis.call('GET', KEYS[2]) or '0')
local daily_global = tonumber(redis.call('GET', KEYS[3]) or '0')

-- Check all three caps BEFORE any deduction (atomic).
if (monthly + estimated) > monthly_cap then
    return 'MONTHLY_BLOCKED'
end
if (daily_tool + estimated) > daily_tool_cap then
    return 'DAILY_TOOL_BLOCKED'
end
if (daily_global + estimated) > daily_global_cap then
    return 'DAILY_GLOBAL_BLOCKED'
end

-- All caps OK — deduct atomically.
redis.call('INCRBYFLOAT', KEYS[1], estimated)
redis.call('INCRBYFLOAT', KEYS[2], estimated)
redis.call('INCRBYFLOAT', KEYS[3], estimated)

-- Set 48-hour TTL for daily keys so they self-clean even on script exit.
redis.call('EXPIRE', KEYS[2], 172800)
redis.call('EXPIRE', KEYS[3], 172800)

local projected = monthly + estimated
if projected > warn_threshold then
    return 'WARNING'
end
return 'ALLOWED'
"""


def call_extended_check(
    redis_client: RedisClient,
    script_sha: str,
    tool_name: str,
    estimated_cost: float,
    monthly_cap: float = 30.0,
    warn_threshold: float = 24.0,
    daily_tool_cap: float = 5.0,
    daily_global_cap: float = 10.0,
) -> str:
    """Execute the extended budget check Lua script via EVALSHA.

    Builds the daily key names from *tool_name* and today's date, then
    calls the Lua script with all three keys and five arguments.

    Args:
        redis_client: Connected ``redis.Redis`` instance.
        script_sha: SHA1 of the pre-loaded ``SCRIPT_EXTENDED_CHECK``.
        tool_name: Canonical tool name (e.g. ``"exa"``, ``"brave_search"``).
        estimated_cost: Cost to check and deduct in USD.
        monthly_cap: Monthly hard stop limit.
        warn_threshold: Monthly warning threshold.
        daily_tool_cap: Per-tool daily cap.
        daily_global_cap: Global daily cap across all tools.

    Returns:
        One of ``"ALLOWED"``, ``"WARNING"``, ``"MONTHLY_BLOCKED"``,
        ``"DAILY_TOOL_BLOCKED"``, ``"DAILY_GLOBAL_BLOCKED"``.

    Raises:
        ``RedisError`` on Redis failure — callers must treat as block.
    """
    today = date.today().isoformat()

    keys = [
        "cost:current_month",
        f"tool:cost:{tool_name}:{today}",
        f"cost:daily:{today}",
    ]
    args = [
        str(estimated_cost),
        str(monthly_cap),
        str(warn_threshold),
        str(daily_tool_cap),
        str(daily_global_cap),
    ]

    try:
        raw: bytes | str | None = redis_client.evalsha(script_sha, keys=keys, args=args)
    except Exception:
        _log.exception("Redis EVALSHA failed for extended budget check")
        raise

    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw or ""

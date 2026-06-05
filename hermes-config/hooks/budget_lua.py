"""Redis Lua scripts for atomic Hermes budget checking.

Provides Lua source strings and loading/calling utilities for atomic
check-and-deduct budget enforcement in Redis DB5.  Every script executes
atomically on the Redis server — there is no client-side read-then-increment
pattern.

Monthly budget:
    - Warning threshold: $24.00 (80 % of $30 cap)
    - Hard block: $30.00
    - Key: ``cost:current_month``

Per-tool daily and global daily caps are handled by the extended module
``budget_lua_extended``.

Usage::

    from hermes_config.hooks.budget_lua import (
        SCRIPT_MONTHLY_CHECK,
        load_script,
        call_monthly_check,
    )

    r = redis.Redis(host="localhost", port=6380, db=5)
    sha = load_script(r, SCRIPT_MONTHLY_CHECK)
    result = call_monthly_check(r, sha, estimated_cost=0.01)
    # result -> b"ALLOWED" | b"WARNING" | b"MONTHLY_BLOCKED"
"""

from __future__ import annotations

import logging
from typing import Final, Protocol


class RedisClient(Protocol):
    def script_load(self, script: str) -> str: ...
    def evalsha(self, script_sha: str, *, keys: list[str], args: list[str]) -> bytes | str | None: ...


_log = logging.getLogger("hermes.hooks.budget_lua")

# ---------------------------------------------------------------------------
# Lua: monthly check only (no daily caps)
# ---------------------------------------------------------------------------
# KEYS[1]  = "cost:current_month"  —  monthly running total (float)
# ARGV[1]  = estimated cost        —  cost to add in USD
# ARGV[2]  = monthly cap           —  hard stop (default 30.00)
# ARGV[3]  = warn threshold        —  warning level (default 24.00)
#
# Return values (as Redis bulk string):
#   "ALLOWED"         —  within budget, cost deducted
#   "WARNING"         -  within cap but above warn threshold, cost deducted
#   "MONTHLY_BLOCKED" -  projected spend would exceed cap, NOT deducted
#
# The script does a SINGLE atomic check-and-deduct:
#   1. Read current monthly total
#   2. Compute projected = current + estimated
#   3. If projected > cap → return BLOCKED (do NOT deduct)
#   4. Otherwise → INCRBYFLOAT (deduct) and return status
# ---------------------------------------------------------------------------
SCRIPT_MONTHLY_CHECK: Final[str] = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
local estimated = tonumber(ARGV[1])
local monthly_cap = tonumber(ARGV[2])
local warn_threshold = tonumber(ARGV[3])

local projected = current + estimated

if projected > monthly_cap then
    return 'MONTHLY_BLOCKED'
end

redis.call('INCRBYFLOAT', KEYS[1], estimated)

if projected > warn_threshold then
    return 'WARNING'
end

return 'ALLOWED'
"""


def load_script(redis_client: RedisClient, script: str) -> str:
    """Load a Lua *script* into Redis and return its SHA1 hash.

    Uses ``SCRIPT LOAD`` (not ``EVAL``) so the script is cached on the
    server and subsequent calls use ``EVALSHA`` for minimal overhead.

    Args:
        redis_client: Connected ``redis.Redis`` instance.
        script: Lua source string.

    Returns:
        SHA1 hex digest of the loaded script.

    Raises:
        ``RedisError`` if the script cannot be loaded.
    """
    return redis_client.script_load(script)


def call_monthly_check(
    redis_client: RedisClient,
    script_sha: str,
    estimated_cost: float,
    monthly_cap: float = 30.0,
    warn_threshold: float = 24.0,
) -> str:
    """Execute the monthly budget check Lua script via EVALSHA.

    Args:
        redis_client: Connected ``redis.Redis`` instance.
        script_sha: SHA1 of the pre-loaded ``SCRIPT_MONTHLY_CHECK``.
        estimated_cost: Cost to check and deduct in USD.
        monthly_cap: Hard stop limit (default 30.0).
        warn_threshold: Warning threshold (default 24.0).

    Returns:
        ``"ALLOWED"``, ``"WARNING"``, or ``"MONTHLY_BLOCKED"``.

    Raises:
        ``RedisError`` on Redis connection/execution failure — callers
        MUST treat any exception as a block signal (fail-closed).
    """
    try:
        raw: bytes | str | None = redis_client.evalsha(
            script_sha,
            keys=["cost:current_month"],
            args=[str(estimated_cost), str(monthly_cap), str(warn_threshold)],
        )
    except Exception:
        _log.exception("Redis EVALSHA failed for monthly budget check")
        raise

    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw or ""

"""MCP Tool Cost Tracker — Per-tool cost tracking in Redis DB5.

Tracks costs per individual MCP tool call, with daily key rotation,
aggregate totals, and monthly roll-up queries.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import redis
import structlog
from redis.exceptions import RedisError

logger = structlog.get_logger()

# Redis key prefixes.
_KEY_PREFIX = "tool:cost"

# Tool call costs in USD — fixed costs (variable tools marked with None).
_TOOL_COSTS: dict[str, float] = {
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
    "websearch": -1.0,  # Variable cost — callers pass explicit cost.
    "git": 0.0,
    "postgres": 0.0,
    "redis": 0.0,
    "shell": 0.0,
    "docker": 0.0,
}


class ToolCostTracker:
    """Per-tool cost tracking in Redis DB5.

    Records each MCP tool call with its known cost. Daily keys are
    rotated with automatic expiry.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6380,
        db: int = 5,
        password: str | None = None,
    ) -> None:
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            username="guinevere_core",
            password=password or os.environ.get("REDIS_PASSWORD", ""),
            decode_responses=True,
        )

        logger.info(
            "tool_cost_tracker.initialized",
            host=host,
            port=port,
            db=db,
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_tool_cost(tool_name: str) -> float:
        """Return the known per-call cost for *tool_name*.

        Returns -1.0 for variable-cost tools (callers must provide an
        explicit cost).
        """
        return _TOOL_COSTS.get(tool_name, -1.0)

    @staticmethod
    def is_variable_cost(tool_name: str) -> bool:
        """Return True when *tool_name* has a variable per-call cost."""
        return _TOOL_COSTS.get(tool_name, -1.0) == -1.0

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_tool_cost(
        self,
        tool_name: str,
        cost_usd: float | None = None,
    ) -> float:
        """Record cost for a single tool call. Returns new daily total.

        If *cost_usd* is None the fixed cost from ``_TOOL_COSTS`` is
        used.  Variable-cost tools (e.g. ``websearch``) must pass an
        explicit value.

        Keys:
            ``tool:cost:{tool_name}:YYYY-MM-DD`` — per-tool daily
            ``tool:cost:total:YYYY-MM-DD``       — aggregate daily
        """
        if cost_usd is None:
            cost_usd = _TOOL_COSTS.get(tool_name, 0.0)

        today = date.today().isoformat()
        tool_key = f"{_KEY_PREFIX}:{tool_name}:{today}"
        total_key = f"{_KEY_PREFIX}:total:{today}"

        # EXPIREAT at end-of-day + 7-day grace period (midnight UTC).
        tomorrow = date.today() + timedelta(days=7)
        expire_ts = int(
            datetime(tomorrow.year, tomorrow.month, tomorrow.day).timestamp()
        )

        try:
            pipe = self.redis.pipeline()

            pipe.incrbyfloat(tool_key, cost_usd)
            pipe.expireat(tool_key, expire_ts)

            pipe.incrbyfloat(total_key, cost_usd)
            pipe.expireat(total_key, expire_ts)

            pipe.execute()

            daily_total = float(str(self.redis.get(tool_key) or "0"))
        except RedisError as e:
            logger.error(
                "tool_cost.record_failed",
                tool_name=tool_name,
                cost_usd=cost_usd,
                error=str(e),
            )
            return 0.0

        logger.info(
            "tool_cost_tracker.recorded",
            tool_name=tool_name,
            cost_usd=cost_usd,
            daily_total=daily_total,
        )

        return daily_total

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_tool_daily_cost(self, tool_name: str) -> float:
        """Return the current daily cost for *tool_name*."""
        today = date.today().isoformat()
        tool_key = f"{_KEY_PREFIX}:{tool_name}:{today}"

        try:
            raw = str(self.redis.get(tool_key) or "0")
            return float(raw)
        except (RedisError, ValueError) as e:
            logger.error(
                "tool_cost.fetch_tool_failed",
                tool_name=tool_name,
                error=str(e),
            )
            return 0.0

    def get_all_daily_costs(self) -> dict[str, float]:
        """Return daily costs for all tools from today's keys (SCAN).

        Only per-tool keys are returned — the ``total`` key is excluded.
        """
        today = date.today().isoformat()
        pattern = f"{_KEY_PREFIX}:*:{today}"

        result: dict[str, float] = {}

        try:
            for key in self.redis.scan_iter(match=pattern):
                # Parse tool name from key: "tool:cost:{name}:YYYY-MM-DD"
                # Skip the aggregate total key.
                suffix = key.removeprefix(f"{_KEY_PREFIX}:")
                if suffix.startswith("total:"):
                    continue
                # key format ensures at least two colons remain.
                name_parts = suffix.rsplit(":", 1)
                if len(name_parts) != 2:
                    continue
                tool_name = name_parts[0]

                raw_val = self.redis.get(key)
                result[tool_name] = float(str(raw_val or "0"))
        except RedisError as e:
            logger.error(
                "tool_cost.fetch_all_failed",
                error=str(e),
            )
            return {}

        logger.debug(
            "tool_cost_tracker.all_costs_queried",
            today=today,
            tool_count=len(result),
        )

        return result

    def get_tool_monthly_cost(self, tool_name: str) -> float:
        """Return the monthly total for *tool_name* (sum of last 30 days).

        Queries the last 30 calendar days (including today) and sums
        their daily keys.  Days without a key are treated as 0.0.
        """
        today = date.today()
        total = 0.0

        try:
            for offset in range(30):
                day = today - timedelta(days=offset)
                tool_key = f"{_KEY_PREFIX}:{tool_name}:{day.isoformat()}"
                raw_val = self.redis.get(tool_key)
                total += float(str(raw_val or "0"))
        except RedisError as e:
            logger.error(
                "tool_cost.monthly_fetch_failed",
                tool_name=tool_name,
                error=str(e),
            )
            return 0.0

        logger.debug(
            "tool_cost_tracker.monthly_queried",
            tool_name=tool_name,
            total=total,
        )

        return total
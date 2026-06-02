"""Budget Enforcer — MCP tool budget caps with fallback logic.

Enforces daily spending caps per tool, a global daily emergency cap,
and monthly spending alerts. Implements automatic fallback routing:
Exa over budget → Brave, Brave over budget → no fallback (throttle).

Redis key format (DB5):
    ``tool:cost:{tool_name}:YYYY-MM-DD``  — per-tool daily spend
    ``tool:cost:total:YYYY-MM-DD``       — aggregate daily spend
    ``cost:current_month``               — running monthly total
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

import redis
import structlog
from redis.exceptions import RedisError

from src.mcp.tools.exa_search import BudgetExceeded

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BudgetConfig:
    """Immutable budget thresholds for all MCP tools."""

    exa_daily_cap: float = 5.0
    brave_daily_cap: float = 3.0
    global_daily_cap: float = 10.0
    monthly_warning: float = 3.0
    monthly_critical: float = 15.0
    monthly_hard_stop: float = 25.0
    monthly_absolute_cap: float = 30.0


@dataclass(frozen=True)
class BudgetStatus:
    """Immutable snapshot of a single tool's budget state."""

    tool: str
    daily_spent: float
    daily_cap: float
    monthly_spent: float
    alert_level: str  # "NORMAL", "WARNING", "CRITICAL", "HARD_STOP"
    fallback_active: bool


# ---------------------------------------------------------------------------
# Budget Enforcer
# ---------------------------------------------------------------------------

_FALLBACK_MAP: dict[str, str | None] = {
    "exa": "brave_search",
    "brave_search": None,
}


class BudgetEnforcer:
    """Budget enforcement for MCP tools.

    Reads per-tool daily spend and global monthly spend from Redis DB5
    and enforces caps with automatic fallback routing.
    """

    def __init__(self, config: BudgetConfig | None = None) -> None:
        self.config = config or BudgetConfig()
        self.redis = redis.Redis(
            host="localhost",
            port=6380,
            db=5,
            username="guinevere_core",
            password=os.environ.get("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        logger.info(
            "budget_enforcer.initialized",
            config=self.config,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check_budget(self, tool_name: str) -> BudgetStatus:
        """Check budget status for *tool_name* before an API call.

        Returns a ``BudgetStatus`` snapshot.  Raises ``BudgetExceeded``
        when the daily cap or the monthly absolute cap has been reached.
        """
        daily_spent = self._get_daily_spend(tool_name)
        monthly_spent = self._get_monthly_spend()
        daily_cap = self._daily_cap_for(tool_name)
        alert_level = self._compute_alert_level(monthly_spent, daily_spent, daily_cap)

        status = BudgetStatus(
            tool=tool_name,
            daily_spent=daily_spent,
            daily_cap=daily_cap,
            monthly_spent=monthly_spent,
            alert_level=alert_level,
            fallback_active=False,
        )

        # Monthly absolute cap blocks everything.
        if monthly_spent >= self.config.monthly_absolute_cap:
            msg = (
                f"Monthly absolute cap reached: "
                f"${monthly_spent:.2f} >= ${self.config.monthly_absolute_cap:.2f}"
            )
            logger.warning("budget.monthly_cap_exceeded", tool=tool_name, monthly_spent=monthly_spent)
            raise BudgetExceeded(msg)

        # Global daily emergency cap.
        global_daily = self._get_global_daily_spend()
        if global_daily >= self.config.global_daily_cap:
            msg = (
                f"Global daily emergency cap reached: "
                f"${global_daily:.2f} >= ${self.config.global_daily_cap:.2f}"
            )
            logger.warning("budget.global_cap_exceeded", tool=tool_name, global_daily=global_daily)
            raise BudgetExceeded(msg)

        # Per-tool daily cap.
        if daily_spent >= daily_cap:
            msg = (
                f"Daily cap reached for {tool_name}: "
                f"${daily_spent:.4f} >= ${daily_cap:.2f}"
            )
            logger.warning("budget.daily_cap_exceeded", tool=tool_name, daily_spent=daily_spent, daily_cap=daily_cap)
            raise BudgetExceeded(msg)

        # Soft-cap warning for Brave at 80 %.
        if tool_name == "brave_search" and daily_cap > 0:
            pct = daily_spent / daily_cap
            if pct >= 0.8:
                logger.warning(
                    "budget.brave_soft_cap_warning",
                    tool=tool_name,
                    daily_spent=daily_spent,
                    daily_cap=daily_cap,
                    percent_used=pct * 100,
                )

        logger.debug("budget.check_passed", tool=tool_name, alert_level=alert_level)
        return status

    async def get_fallback_tool(self, tool_name: str) -> str | None:
        """Return the fallback tool for *tool_name* if available.

        Returns ``None`` when no fallback exists or the fallback itself
        is also over budget.
        """
        # Only return fallback when the primary tool's daily cap has been
        # breached AND the monthly absolute cap hasn't been reached.
        daily_spent = self._get_daily_spend(tool_name)
        monthly_spent = self._get_monthly_spend()
        daily_cap = self._daily_cap_for(tool_name)

        # Monthly absolute cap blocks everything — no fallback.
        if monthly_spent >= self.config.monthly_absolute_cap:
            logger.info("budget.no_fallback_monthly_cap", tool=tool_name, monthly_spent=monthly_spent)
            return None

        # Only route to fallback when actually over budget.
        if daily_spent < daily_cap:
            logger.debug("budget.no_fallback_under_cap", tool=tool_name, daily_spent=daily_spent)
            return None

        fallback = _FALLBACK_MAP.get(tool_name)
        if fallback is None:
            logger.info("budget.no_fallback_available", tool=tool_name)
            return None

        # Check that the fallback itself isn't also over budget.
        fb_daily = self._get_daily_spend(fallback)
        fb_cap = self._daily_cap_for(fallback)
        if fb_daily >= fb_cap:
            logger.warning(
                "budget.fallback_also_exceeded",
                tool=tool_name,
                fallback=fallback,
                fallback_daily=fb_daily,
            )
            return None

        logger.info("budget.fallback_active", tool=tool_name, fallback=fallback)
        return fallback

    async def get_monthly_status(self) -> dict[str, BudgetStatus]:
        """Return budget status for all known tools this month."""
        monthly_spent = self._get_monthly_spend()
        statuses: dict[str, BudgetStatus] = {}

        tool_names = list(_FALLBACK_MAP.keys())
        # Also include any tools tracked in today's daily keys.
        all_daily = self._get_all_daily_spends()
        for seen in all_daily:
            if seen not in tool_names and seen != "total":
                tool_names.append(seen)

        for tool_name in tool_names:
            daily_spent = all_daily.get(tool_name, self._get_daily_spend(tool_name))
            daily_cap = self._daily_cap_for(tool_name)
            alert_level = self._compute_alert_level(monthly_spent, daily_spent, daily_cap)

            statuses[tool_name] = BudgetStatus(
                tool=tool_name,
                daily_spent=daily_spent,
                daily_cap=daily_cap,
                monthly_spent=monthly_spent,
                alert_level=alert_level,
                fallback_active=(
                    daily_spent >= daily_cap and _FALLBACK_MAP.get(tool_name) is not None
                ),
            )

        logger.debug(
            "budget.monthly_status",
            monthly_spent=monthly_spent,
            tool_count=len(statuses),
        )
        return statuses

    async def record_and_check(self, tool_name: str, cost: float) -> BudgetStatus:
        """Record a cost for *tool_name* and immediately check budget.

        This is the primary entry-point: costs are recorded first, then
        budget is checked.  If the *new* spend exceeds a cap,
        ``BudgetExceeded`` is raised.

        Returns a ``BudgetStatus`` snapshot when the call is within budget.
        """
        # Record the cost.
        today = date.today().isoformat()
        tool_key = f"tool:cost:{tool_name}:{today}"
        total_key = f"tool:cost:total:{today}"

        try:
            pipe = self.redis.pipeline()
            pipe.incrbyfloat(tool_key, cost)
            pipe.incrbyfloat(total_key, cost)
            pipe.incrbyfloat("cost:current_month", cost)
            pipe.execute()
        except RedisError as exc:
            logger.error(
                "budget.record_failed",
                tool_name=tool_name,
                cost=cost,
                error=str(exc),
            )
            # If we cannot record, we still check — defensive approach.
            pass

        logger.info(
            "budget.cost_recorded",
            tool=tool_name,
            cost=cost,
        )

        # Immediately check budget post-recording.
        return await self.check_budget(tool_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _daily_cap_for(self, tool_name: str) -> float:
        """Return the daily spending cap for *tool_name*."""
        caps: dict[str, float] = {
            "exa": self.config.exa_daily_cap,
            "brave_search": self.config.brave_daily_cap,
        }
        return caps.get(tool_name, self.config.global_daily_cap)

    def _compute_alert_level(
        self,
        monthly_spent: float,
        daily_spent: float,
        daily_cap: float,
    ) -> str:
        """Determine the alert level from current spend."""
        if monthly_spent >= self.config.monthly_hard_stop:
            return "HARD_STOP"
        if monthly_spent >= self.config.monthly_critical:
            return "CRITICAL"
        if monthly_spent >= self.config.monthly_warning:
            return "WARNING"
        if daily_spent >= daily_cap:
            return "WARNING"
        return "NORMAL"

    def _get_daily_spend(self, tool_name: str) -> float:
        """Read the current daily spend for *tool_name* from Redis."""
        today = date.today().isoformat()
        tool_key = f"tool:cost:{tool_name}:{today}"
        try:
            raw = self.redis.get(tool_key)
            return float(str(raw)) if raw is not None else 0.0
        except (RedisError, ValueError) as exc:
            logger.error(
                "budget.read_daily_failed",
                tool=tool_name,
                key=tool_key,
                error=str(exc),
            )
            return 0.0

    def _get_global_daily_spend(self) -> float:
        """Read the aggregate daily spend from Redis."""
        today = date.today().isoformat()
        total_key = f"tool:cost:total:{today}"
        try:
            raw = self.redis.get(total_key)
            return float(str(raw)) if raw is not None else 0.0
        except (RedisError, ValueError) as exc:
            logger.error(
                "budget.read_global_failed",
                key=total_key,
                error=str(exc),
            )
            return 0.0

    def _get_monthly_spend(self) -> float:
        """Read the running monthly total from Redis."""
        try:
            raw = self.redis.get("cost:current_month")
            return float(str(raw)) if raw is not None else 0.0
        except (RedisError, ValueError) as exc:
            logger.error(
                "budget.read_monthly_failed",
                error=str(exc),
            )
            return 0.0

    def _get_all_daily_spends(self) -> dict[str, float]:
        """Return daily spends for all tools tracked today."""
        today = date.today().isoformat()
        pattern = f"tool:cost:*:{today}"
        result: dict[str, float] = {}

        try:
            for key in self.redis.scan_iter(match=pattern):
                suffix = key.removeprefix("tool:cost:")
                if suffix.startswith("total:"):
                    continue
                parts = suffix.rsplit(":", 1)
                if len(parts) != 2:
                    continue
                name = parts[0]
                raw = self.redis.get(key)
                result[name] = float(str(raw)) if raw is not None else 0.0
        except RedisError as exc:
            logger.error("budget.scan_all_failed", error=str(exc))

        return result
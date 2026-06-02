"""Cost Tracker — Monitors LLM spend against budget (ACL-aware Redis)."""
import os
import redis
import structlog
from datetime import date, datetime

logger = structlog.get_logger()


class CostTracker:
    """Track LLM costs across models with budget enforcement."""

    def __init__(self, host: str = "localhost", port: int = 6380, db: int = 5,
                 username: str = "guinevere_core", password: str | None = None,
                 decode_responses: bool = True):
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            username=username,
            password=password or os.environ.get("REDIS_PASSWORD", ""),
            decode_responses=decode_responses,
        )

    def record_cost(self, model: str, input_tokens: int, output_tokens: int,
                    cost_per_1k_input: float, cost_per_1k_output: float):
        """Record LLM usage cost for a single call."""
        cost = (input_tokens / 1000 * cost_per_1k_input +
                output_tokens / 1000 * cost_per_1k_output)

        today = date.today().isoformat()
        month = date.today().strftime("%Y-%m")

        pipe = self.redis.pipeline()
        pipe.incrbyfloat("cost:current_month", cost)
        pipe.incrbyfloat("cost:current_day", cost)
        pipe.incrbyfloat(f"cost:by_model:{model}", cost)
        pipe.incrbyfloat(f"cost:daily:{today}", cost)
        pipe.incrbyfloat(f"cost:monthly:{month}", cost)
        pipe.execute()

        logger.info("cost_recorded", model=model, cost=cost,
                    monthly_total=self.redis.get("cost:current_month"))

    def check_budget(self) -> dict:
        """Return budget status with alert level."""
        current = float(self.redis.get("cost:current_month") or 0)
        cap = float(self.redis.get("budget:monthly_cap") or 30)

        return {
            "current_month": current,
            "monthly_cap": cap,
            "remaining": cap - current,
            "percent_used": (current / cap * 100) if cap > 0 else 0,
            "status": self._get_status(current, cap),
        }

    def _get_status(self, current: float, cap: float) -> str:
        ratio = current / cap if cap > 0 else 1
        if ratio >= 1.0:
            return "HARD_STOP"
        if ratio >= 0.833:
            return "CRITICAL"
        if ratio >= 0.5:
            return "WARNING"
        if current >= 1.0:
            return "NORMAL_ALERT"
        return "NORMAL"
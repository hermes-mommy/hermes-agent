"""Loop Cost Tracker — per-loop cost tracking using Redis DB5.

Records LLM token usage and costs per loop instance, with per-model
breakdown. Integrates with the global CostTracker for aggregate tracking.
"""

from __future__ import annotations

import os
from datetime import date

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
import structlog

from guinevere.core.services.cost_tracker import CostTracker

logger = structlog.get_logger()

# Redis key prefixes.
_KEY_PREFIX = "loop:cost"


class LoopCostTracker:
    """Per-loop cost tracking using Redis DB5."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6380,
        db: int = 5,
    ) -> None:
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            username="guinevere_core",
            password=os.environ.get("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        self._global_tracker = CostTracker(
            host=host,
            port=port,
            db=db,
            username="guinevere_core",
            password=os.environ.get("REDIS_PASSWORD", ""),
        )

        logger.info(
            "loop_cost_tracker.initialized",
            host=host,
            port=port,
            db=db,
        )

    def record_loop_cost(
        self,
        loop_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_per_1k_input: float,
        cost_per_1k_output: float,
    ) -> float:
        """Record cost for a specific loop and update global tracking.

        Args:
            loop_id: The loop instance ID.
            model: The LLM model used.
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens consumed.
            cost_per_1k_input: Cost per 1000 input tokens.
            cost_per_1k_output: Cost per 1000 output tokens.

        Returns:
            The total cost accumulated for this loop.
        """
        cost = (input_tokens / 1000 * cost_per_1k_input) + (
            output_tokens / 1000 * cost_per_1k_output
        )

        loop_key = f"{_KEY_PREFIX}:{loop_id}"
        model_key = f"{_KEY_PREFIX}:{loop_id}:by_model:{model}"

        try:
            pipe = self.redis.pipeline()

            # Per-loop totals.
            pipe.incrbyfloat(loop_key, cost)
            pipe.hincrby(loop_key, "calls", 1)
            pipe.hincrby(loop_key, "input_tokens", input_tokens)
            pipe.hincrby(loop_key, "output_tokens", output_tokens)

            # Per-loop per-model breakdown.
            pipe.incrbyfloat(model_key, cost)
            pipe.hincrby(model_key, "calls", 1)
            pipe.hincrby(model_key, "input_tokens", input_tokens)
            pipe.hincrby(model_key, "output_tokens", output_tokens)

            # Track loop in current month set for aggregate queries.
            month = date.today().strftime("%Y-%m")
            pipe.sadd(f"{_KEY_PREFIX}:month:{month}", loop_id)

            pipe.execute()

            total = float(self.redis.get(loop_key) or 0)
        except RedisError as e:
            logger.error(
                "loop_cost.record_failed",
                loop_id=loop_id,
                error=str(e),
            )
            return 0.0

        # Also record in global CostTracker for aggregate tracking.
        try:
            self._global_tracker.record_cost(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_per_1k_input=cost_per_1k_input,
                cost_per_1k_output=cost_per_1k_output,
            )
        except RedisError as e:
            logger.error(
                "loop_cost.global_record_failed",
                loop_id=loop_id,
                error=str(e),
            )

        logger.info(
            "loop_cost_tracker.recorded",
            loop_id=loop_id,
            model=model,
            cost=cost,
            total_loop_cost=total,
        )

        return total

    def get_loop_cost(self, loop_id: str) -> dict[str, object]:
        """Return total cost breakdown for a loop.

        Args:
            loop_id: The loop to query.

        Returns:
            Dict with total_cost, total_calls, total_input_tokens,
            total_output_tokens, and per-model breakdown.
        """
        loop_key = f"{_KEY_PREFIX}:{loop_id}"

        try:
            total_cost_str = self.redis.get(loop_key)
            total_cost = float(total_cost_str) if total_cost_str else 0.0

            # Read aggregate counters.
            calls = int(self.redis.hget(loop_key, "calls") or 0)
            input_tokens = int(self.redis.hget(loop_key, "input_tokens") or 0)
            output_tokens = int(self.redis.hget(loop_key, "output_tokens") or 0)

            # Scan for per-model keys.
            model_pattern = f"{_KEY_PREFIX}:{loop_id}:by_model:*"
            model_costs: dict[str, float] = {}

            for key in self.redis.scan_iter(match=model_pattern):
                model_name = key.split(":by_model:")[-1]
                model_cost_str = self.redis.get(key)
                model_costs[model_name] = (
                    float(model_cost_str) if model_cost_str else 0.0
                )
        except RedisError as e:
            logger.error(
                "loop_cost.fetch_failed",
                loop_id=loop_id,
                error=str(e),
            )
            return {
                "loop_id": loop_id,
                "total_cost": 0.0,
                "total_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "by_model": {},
            }

        result = {
            "loop_id": loop_id,
            "total_cost": total_cost,
            "total_calls": calls,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "by_model": model_costs,
        }

        logger.debug(
            "loop_cost_tracker.loop_cost_queried",
            loop_id=loop_id,
            total_cost=total_cost,
        )

        return result

    def get_all_loop_costs(self) -> dict[str, float]:
        """Return all loop costs for the current month.

        Returns:
            Dict mapping loop_id to total cost for the current month.
        """
        month = date.today().strftime("%Y-%m")
        month_key = f"{_KEY_PREFIX}:month:{month}"

        try:
            loop_ids = self.redis.smembers(month_key)
            result: dict[str, float] = {}

            for loop_id in loop_ids:
                loop_key = f"{_KEY_PREFIX}:{loop_id}"
                cost_str = self.redis.get(loop_key)
                result[loop_id] = float(cost_str) if cost_str else 0.0
        except RedisError as e:
            logger.error(
                "loop_cost.fetch_all_failed",
                error=str(e),
            )
            return {}

        logger.debug(
            "loop_cost_tracker.all_costs_queried",
            month=month,
            loop_count=len(result),
        )

        return result

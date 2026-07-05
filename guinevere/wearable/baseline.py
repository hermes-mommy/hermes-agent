"""28-day rolling baseline calculator with warmup state machine.

Stages: insufficient (0-3d) → provisional (4-14d) → stabilizing (15-28d) → stable (28d+) → rebaseline (>7d gap).
Persisted to health.baseline_state. Metric-specific: each metric has independent baseline.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import sqrt
from statistics import fmean

import asyncpg
from pydantic import BaseModel, Field
from structlog.stdlib import BoundLogger, get_logger

from guinevere.wearable.models import BaselineStage, HealthMetricType

logger: BoundLogger = get_logger(__name__)


@dataclass(slots=True)
class BaselineResult:
    metric: HealthMetricType
    stage: BaselineStage
    baseline_value: float | None
    stddev: float | None
    confidence: float
    data_points: int
    first_data_at: datetime | None
    last_data_at: datetime | None
    owner_id: str
    device_id: str


class BaselineState(BaseModel):
    metric: HealthMetricType
    device_id: str
    owner_id: str
    stage: BaselineStage
    baseline_value: float | None = None
    stddev: float | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    data_points: int = Field(default=0, ge=0)
    first_data_at: datetime | None = None
    last_data_at: datetime | None = None
    updated_at: datetime | None = None


_METRIC_READERS: dict[HealthMetricType, tuple[str, str, str]] = {
    HealthMetricType.HEART_RATE: ("health.heart_rate", "bpm", "time"),
    HealthMetricType.STEPS: ("health.daily_activity", "steps", "date"),
    HealthMetricType.SPO2: ("health.spo2", "spo2_pct", "time"),
    HealthMetricType.STRESS: ("health.stress", "score", "time"),
    HealthMetricType.SLEEP: ("health.sleep_sessions", "COALESCE(efficiency_pct, total_s / 60.0)", "start_time"),
    HealthMetricType.ACTIVITY: ("health.daily_activity", "steps", "date"),
}


def _mean_stddev(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        return fmean(values), 0.0
    mean_value = fmean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return mean_value, sqrt(variance)


def _confidence_for_stage(stage: BaselineStage, data_points: int) -> float:
    if stage is BaselineStage.INSUFFICIENT:
        return 0.0 if data_points < 3 else min(0.2, 0.05 * data_points)
    if stage is BaselineStage.PROVISIONAL:
        return min(0.5, 0.3 + min(0.2, data_points / 100))
    if stage is BaselineStage.STABILIZING:
        return min(0.8, 0.6 + min(0.2, data_points / 200))
    if stage is BaselineStage.STABLE:
        return min(1.0, 0.9 + min(0.1, data_points / 500))
    return 0.0


class BaselineCalculator:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None
        self._window_days = 28
        self._min_points = 3

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=5)
        return self._pool

    @asynccontextmanager
    async def _connection(self):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            yield conn

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def compute_baseline(self, metric: HealthMetricType, owner_id: str, device_id: str) -> BaselineState:
        existing = await self.get_baseline(metric, owner_id, device_id)
        try:
            result = await self._load_metric_values(metric, owner_id, device_id)
        except Exception as exc:  # noqa: BLE001 - log and degrade gracefully
            logger.warning("baseline_metric_query_failed", metric=metric.value, owner_id=owner_id, device_id=device_id, error=str(exc))
            return self._build_insufficient(metric, owner_id, device_id, None, None, 0)

        values, first_data_at, last_data_at = result
        if not values:
            return self._build_insufficient(metric, owner_id, device_id, None, None, 0)

        if existing and existing.last_data_at and last_data_at and (last_data_at - existing.last_data_at) > timedelta(days=7):
            logger.info("baseline_rebaseline_gap_detected", metric=metric.value, owner_id=owner_id, device_id=device_id)
            return self._build_insufficient(metric, owner_id, device_id, first_data_at, last_data_at, len(values))

        stage = self._stage_for_values(values, first_data_at, last_data_at)
        mean_value, stddev = _mean_stddev(values)
        confidence = _confidence_for_stage(stage, len(values))
        if len(values) < self._min_points:
            stage = BaselineStage.INSUFFICIENT
            mean_value = None
            stddev = None
            confidence = 0.0

        state = BaselineState(
            metric=metric,
            device_id=device_id,
            owner_id=owner_id,
            stage=stage,
            baseline_value=mean_value,
            stddev=stddev,
            confidence=confidence,
            data_points=len(values),
            first_data_at=first_data_at,
            last_data_at=last_data_at,
            updated_at=datetime.now(UTC),
        )
        await self.persist_baseline(state)
        return state

    def _build_insufficient(
        self,
        metric: HealthMetricType,
        owner_id: str,
        device_id: str,
        first_data_at: datetime | None,
        last_data_at: datetime | None,
        data_points: int,
    ) -> BaselineState:
        return BaselineState(
            metric=metric,
            device_id=device_id,
            owner_id=owner_id,
            stage=BaselineStage.INSUFFICIENT,
            baseline_value=None,
            stddev=None,
            confidence=0.0,
            data_points=data_points,
            first_data_at=first_data_at,
            last_data_at=last_data_at,
            updated_at=datetime.now(UTC),
        )

    def _stage_for_values(
        self,
        values: list[float],
        first_data_at: datetime | None,
        last_data_at: datetime | None,
    ) -> BaselineStage:
        if not values or first_data_at is None or last_data_at is None:
            return BaselineStage.INSUFFICIENT
        active_days = max(1, (last_data_at.date() - first_data_at.date()).days + 1)
        if active_days <= 3:
            return BaselineStage.INSUFFICIENT
        if active_days <= 14:
            return BaselineStage.PROVISIONAL
        if active_days < self._window_days:
            return BaselineStage.STABILIZING
        return BaselineStage.STABLE

    async def _load_metric_values(
        self,
        metric: HealthMetricType,
        owner_id: str,
        device_id: str,
    ) -> tuple[list[float], datetime | None, datetime | None]:
        table, value_expr, time_col = _METRIC_READERS[metric]
        since = datetime.now(UTC) - timedelta(days=self._window_days)
        query = f"""
            SELECT {value_expr} AS value, {time_col} AS ts
            FROM {table}
            WHERE owner_id = $1
              AND device_id = $2
              AND {time_col} >= $3
            ORDER BY {time_col} ASC
        """
        async with self._connection() as conn:
            rows = await conn.fetch(query, owner_id, device_id, since)

        values: list[float] = []
        first_data_at: datetime | None = None
        last_data_at: datetime | None = None
        for row in rows:
            raw_value = row["value"]
            if raw_value is None:
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            values.append(value)
            ts = row["ts"]
            if isinstance(ts, datetime):
                first_data_at = first_data_at or ts
                last_data_at = ts
        return values, first_data_at, last_data_at

    async def persist_baseline(self, state: BaselineState) -> None:
        query = """
            INSERT INTO health.baseline_state (
                metric, device_id, stage, baseline_value, data_points,
                first_data_at, last_data_at, updated_at, owner_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8)
            ON CONFLICT (metric, device_id, owner_id)
            DO UPDATE SET
                stage = EXCLUDED.stage,
                baseline_value = EXCLUDED.baseline_value,
                data_points = EXCLUDED.data_points,
                first_data_at = EXCLUDED.first_data_at,
                last_data_at = EXCLUDED.last_data_at,
                updated_at = EXCLUDED.updated_at
        """
        async with self._connection() as conn:
            await conn.execute(
                query,
                state.metric.value,
                state.device_id,
                state.stage.value,
                state.baseline_value,
                state.data_points,
                state.first_data_at,
                state.last_data_at,
                state.owner_id,
            )

    async def get_baseline(self, metric: HealthMetricType, owner_id: str, device_id: str) -> BaselineState | None:
        query = """
            SELECT metric, device_id, owner_id, stage, baseline_value, data_points,
                   first_data_at, last_data_at, updated_at
            FROM health.baseline_state
            WHERE metric = $1 AND owner_id = $2 AND device_id = $3
        """
        async with self._connection() as conn:
            row = await conn.fetchrow(query, metric.value, owner_id, device_id)
        if row is None:
            return None
        return BaselineState(
            metric=metric,
            device_id=str(row["device_id"]),
            owner_id=str(row["owner_id"]),
            stage=BaselineStage(str(row["stage"])),
            baseline_value=row["baseline_value"],
            stddev=None,
            confidence=_confidence_for_stage(BaselineStage(str(row["stage"])), int(row["data_points"])),
            data_points=int(row["data_points"]),
            first_data_at=row["first_data_at"],
            last_data_at=row["last_data_at"],
            updated_at=row["updated_at"],
        )

    async def compute_all_baselines(self, owner_id: str, device_id: str) -> dict[HealthMetricType, BaselineState]:
        baselines: dict[HealthMetricType, BaselineState] = {}
        for metric in HealthMetricType:
            baselines[metric] = await self.compute_baseline(metric, owner_id, device_id)
        return baselines


__all__ = ["BaselineCalculator", "BaselineResult", "BaselineState"]

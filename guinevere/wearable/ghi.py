"""Global Health Index (GHI) scorer with dynamic weight rebalance.

Computes a 0-100 GHI score from 4 pillars:
- Sleep (40%): sleep duration + quality
- Cardio (20%): heart rate + resting HR
- Activity (20%): steps + distance
- Recovery (20%): stress + HRV

Features:
- Dynamic weight rebalance when metrics unavailable
- Confidence model (0-1) based on data availability and baseline stability
- Suppression rule: <2 pillars with data → GHI suppressed
- Penalty cap: -15% per pillar max
- Exponential decay over 3 days for stale data
- Tiers: Excellent ≥85, Good ≥70, Fair ≥55, Poor ≥40, Critical <40
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import exp
from statistics import fmean
from typing import cast

import asyncpg
import structlog

from .baseline import BaselineResult
from .models import BaselineStage, GHITier, HealthMetricType

logger = structlog.get_logger(__name__)

DEFAULT_WEIGHTS: dict[str, float] = {
    "sleep": 0.4,
    "cardio": 0.2,
    "activity": 0.2,
    "recovery": 0.2,
}

_PILLAR_TO_METRICS: dict[str, tuple[HealthMetricType, ...]] = {
    "sleep": (HealthMetricType.SLEEP,),
    "cardio": (HealthMetricType.HEART_RATE,),
    "activity": (HealthMetricType.STEPS, HealthMetricType.ACTIVITY),
    "recovery": (HealthMetricType.STRESS,),
}


@dataclass(slots=True)
class PillarScore:
    score: float | None
    confidence: float
    data_present: bool
    sample_age_days: float | None


@dataclass(slots=True)
class GHIScoreResult:
    """Internal GHI computation result. Distinct from models.GHIScoreResult (DB persistence model)."""
    score: float
    confidence: float
    tier: GHITier
    sleep_score: float | None
    cardio_score: float | None
    activity_score: float | None
    recovery_score: float | None
    weights: dict[str, float]
    suppressed: bool
    computed_at: datetime
    owner_id: str
    device_id: str


class GHIScorer:
    def __init__(self, database_url: str) -> None:
        self._database_url: str = database_url
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._database_url, min_size=1, max_size=5)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def compute_ghi(self, owner_id: str, device_id: str, date: date) -> GHIScoreResult:
        baselines = await self._fetch_baselines(owner_id, device_id)
        pillar_data = await self._fetch_pillar_data(owner_id, device_id, date)

        pillar_scores: dict[str, PillarScore] = {}
        for pillar in DEFAULT_WEIGHTS:
            pillar_scores[pillar] = self._compute_pillar_score(pillar, pillar_data.get(pillar), baselines.get(pillar))

        available_pillars = [pillar for pillar, result in pillar_scores.items() if result.data_present and result.score is not None]
        if len(available_pillars) < 2:
            result = GHIScoreResult(
                score=0.0,
                confidence=0.0,
                tier=GHITier.CRITICAL,
                sleep_score=pillar_scores["sleep"].score,
                cardio_score=pillar_scores["cardio"].score,
                activity_score=pillar_scores["activity"].score,
                recovery_score=pillar_scores["recovery"].score,
                weights={},
                suppressed=True,
                computed_at=datetime.now(UTC),
                owner_id=owner_id,
                device_id=device_id,
            )
            await self.persist_ghi(result)
            return result

        weights = self._rebalance_weights(available_pillars)
        weighted_scores = []
        for pillar in available_pillars:
            pillar_score = pillar_scores[pillar].score
            if pillar_score is not None:
                weighted_scores.append(pillar_score * weights[pillar])
        raw_score = float(sum(weighted_scores))
        confidence = float(sum(float(pillar_scores[pillar].confidence) * weights[pillar] for pillar in available_pillars))
        score = max(0.0, min(100.0, raw_score))
        tier = self._tier_for_score(score)

        result = GHIScoreResult(
            score=score,
            confidence=max(0.0, min(1.0, confidence)),
            tier=tier,
            sleep_score=pillar_scores["sleep"].score,
            cardio_score=pillar_scores["cardio"].score,
            activity_score=pillar_scores["activity"].score,
            recovery_score=pillar_scores["recovery"].score,
            weights=weights,
            suppressed=False,
            computed_at=datetime.now(UTC),
            owner_id=owner_id,
            device_id=device_id,
        )
        await self.persist_ghi(result)
        return result

    def _rebalance_weights(self, available_pillars: list[str]) -> dict[str, float]:
        if len(available_pillars) < 2:
            return {}
        weight = 1.0 / len(available_pillars)
        return {pillar: weight for pillar in available_pillars}

    def _tier_for_score(self, score: float) -> GHITier:
        if score >= 85:
            return GHITier.EXCELLENT
        if score >= 70:
            return GHITier.GOOD
        if score >= 55:
            return GHITier.FAIR
        if score >= 40:
            return GHITier.POOR
        return GHITier.CRITICAL

    async def _fetch_baselines(self, owner_id: str, device_id: str) -> dict[str, BaselineResult | None]:
        query = """
            SELECT metric, stage, baseline_value, stddev, confidence, data_points, first_data_at, last_data_at, owner_id, device_id
            FROM health.baseline_state
            WHERE owner_id = $1 AND device_id = $2
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, owner_id, device_id)

        baselines: dict[str, BaselineResult | None] = {pillar: None for pillar in DEFAULT_WEIGHTS}
        for row in rows:
            metric = str(row["metric"])
            pillar = self._pillar_for_metric(metric)
            if pillar is None:
                continue
            baseline_metric = HealthMetricType(metric)
            baselines[pillar] = BaselineResult(
                metric=baseline_metric,
                stage=cast(BaselineStage, row["stage"]),
                baseline_value=self._as_float(row["baseline_value"]),
                stddev=self._as_float(row["stddev"]),
                confidence=float(row["confidence"]),
                data_points=int(row["data_points"]),
                first_data_at=cast(datetime | None, row["first_data_at"]),
                last_data_at=cast(datetime | None, row["last_data_at"]),
                owner_id=str(row["owner_id"]),
                device_id=str(row["device_id"]),
            )
        return baselines

    async def _fetch_pillar_data(self, owner_id: str, device_id: str, day: date) -> dict[str, dict[str, object] | None]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            sleep_row = await conn.fetchrow(
                """
                SELECT sleep_date, total_s, efficiency_pct, end_time
                FROM health.sleep_sessions
                WHERE owner_id = $1 AND device_id = $2 AND sleep_date = $3
                ORDER BY start_time DESC
                LIMIT 1
                """,
                owner_id,
                device_id,
                day,
            )
            activity_row = await conn.fetchrow(
                """
                SELECT date, steps, distance_m
                FROM health.daily_activity
                WHERE owner_id = $1 AND device_id = $2 AND date = $3
                """,
                owner_id,
                device_id,
                day,
            )
            heart_row = await conn.fetchrow(
                """
                SELECT time, bpm, resting_bpm
                FROM health.heart_rate
                WHERE owner_id = $1 AND device_id = $2 AND time::date = $3
                ORDER BY time DESC
                LIMIT 1
                """,
                owner_id,
                device_id,
                day,
            )
            stress_rows = await conn.fetch(
                """
                SELECT time, score
                FROM health.stress
                WHERE owner_id = $1 AND device_id = $2 AND time::date = $3
                ORDER BY time ASC
                """,
                owner_id,
                device_id,
                day,
            )
            hrv_row = await conn.fetchrow(
                """
                SELECT time, value
                FROM health.hrv
                WHERE owner_id = $1 AND device_id = $2 AND time::date = $3
                ORDER BY time DESC
                LIMIT 1
                """,
                owner_id,
                device_id,
                day,
            )

        return {
            "sleep": self._row_to_dict(sleep_row),
            "activity": self._row_to_dict(activity_row),
            "cardio": self._row_to_dict(heart_row),
            "recovery": {
                "stress_rows": stress_rows,
                "hrv_row": self._row_to_dict(hrv_row),
            },
        }

    def _compute_pillar_score(
        self,
        pillar: str,
        data: dict[str, object] | None,
        baseline: BaselineResult | None,
    ) -> PillarScore:
        if data is None:
            return PillarScore(score=None, confidence=0.0, data_present=False, sample_age_days=None)

        score = 0.0
        confidence = baseline.confidence if baseline is not None else 0.0
        sample_age_days = self._sample_age_days(data)
        decay = exp(-(sample_age_days / 3.0)) if sample_age_days is not None and sample_age_days > 3 else 1.0

        if pillar == "sleep":
            total_s = self._as_float(data.get("total_s"))
            efficiency_pct = self._as_float(data.get("efficiency_pct"))
            if total_s is None:
                return PillarScore(score=None, confidence=0.0, data_present=False, sample_age_days=sample_age_days)
            score = min(100.0, (total_s / 480.0) * 100.0)
            if total_s < 360:
                score = max(0.0, score - 15.0)
            if efficiency_pct is not None:
                score = min(100.0, score * (0.5 + (efficiency_pct / 200.0)))
            score *= decay
        elif pillar == "cardio":
            bpm = self._as_float(data.get("bpm"))
            resting_bpm = self._as_float(data.get("resting_bpm"))
            baseline_hr = baseline.baseline_value if baseline is not None and baseline.baseline_value is not None else resting_bpm
            if bpm is None and resting_bpm is None:
                return PillarScore(score=None, confidence=0.0, data_present=False, sample_age_days=sample_age_days)
            current_hr = resting_bpm if resting_bpm is not None else bpm
            if current_hr is None:
                return PillarScore(score=None, confidence=0.0, data_present=False, sample_age_days=sample_age_days)
            if baseline_hr is None:
                baseline_hr = current_hr
            score = max(0.0, 100.0 - abs(current_hr - baseline_hr))
            if abs(current_hr - baseline_hr) > 10:
                score = max(0.0, score - 15.0)
            score *= decay
        elif pillar == "activity":
            steps = self._as_float(data.get("steps"))
            if steps is None:
                return PillarScore(score=None, confidence=0.0, data_present=False, sample_age_days=sample_age_days)
            baseline_steps = baseline.baseline_value if baseline is not None and baseline.baseline_value is not None else steps
            score = min(100.0, (steps / max(baseline_steps, 1.0)) * 100.0)
            score *= decay
        elif pillar == "recovery":
            stress_rows_obj = data.get("stress_rows")
            stress_rows = cast(list[object], stress_rows_obj) if isinstance(stress_rows_obj, list) else []
            stress_values: list[float] = []
            for row in stress_rows:
                row_record = cast(asyncpg.Record, row)
                value = self._as_float(row_record["score"])
                if value is not None:
                    stress_values.append(value)
            if not stress_values:
                return PillarScore(score=None, confidence=0.0, data_present=False, sample_age_days=sample_age_days)
            avg_stress = fmean(stress_values)
            score = max(0.0, 100.0 - avg_stress)
            baseline_stress = baseline.baseline_value if baseline is not None and baseline.baseline_value is not None else avg_stress
            if avg_stress > baseline_stress * 1.3:
                score = max(0.0, score - 15.0)
            hrv_row_obj = data.get("hrv_row")
            hrv_row = hrv_row_obj if isinstance(hrv_row_obj, dict) else None
            if hrv_row is not None:
                hrv_value = self._as_float(hrv_row.get("value"))
                if hrv_value is not None:
                    score = min(100.0, score + min(10.0, hrv_value / 10.0))
            score *= decay
        else:
            return PillarScore(score=None, confidence=0.0, data_present=False, sample_age_days=sample_age_days)

        score = max(0.0, min(100.0, score))
        return PillarScore(score=score, confidence=max(0.0, min(1.0, confidence)), data_present=True, sample_age_days=sample_age_days)

    def _pillar_for_metric(self, metric: str) -> str | None:
        for pillar, metrics in _PILLAR_TO_METRICS.items():
            if metric in {item.value for item in metrics}:
                return pillar
        return None

    def _sample_age_days(self, data: dict[str, object]) -> float | None:
        timestamps: list[datetime] = []
        for value in data.values():
            if isinstance(value, dict):
                for nested in value.values():
                    if isinstance(nested, datetime):
                        timestamps.append(nested)
            elif isinstance(value, datetime):
                timestamps.append(value)
        if not timestamps:
            return None
        latest = max(timestamps)
        return max(0.0, (datetime.now(UTC) - latest).total_seconds() / 86400.0)

    def _row_to_dict(self, row: asyncpg.Record | None) -> dict[str, object] | None:
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}

    def _as_float(self, value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value))
        except (TypeError, ValueError):
            return None

    async def persist_ghi(self, result: GHIScoreResult) -> None:
        query = """
            INSERT INTO health.ghi_daily (
                date, device_id, ghi_score, confidence, sleep_score,
                cardio_score, activity_score, recovery_score, tier, owner_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (date, device_id, owner_id)
            DO UPDATE SET
                ghi_score = EXCLUDED.ghi_score,
                confidence = EXCLUDED.confidence,
                sleep_score = EXCLUDED.sleep_score,
                cardio_score = EXCLUDED.cardio_score,
                activity_score = EXCLUDED.activity_score,
                recovery_score = EXCLUDED.recovery_score,
                tier = EXCLUDED.tier
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                query,
                result.computed_at.date(),
                result.device_id,
                result.score,
                result.confidence,
                result.sleep_score,
                result.cardio_score,
                result.activity_score,
                result.recovery_score,
                result.tier.value,
                result.owner_id,
            )

    async def get_ghi_history(self, owner_id: str, device_id: str, days: int = 30) -> list[GHIScoreResult]:
        query = """
            SELECT date, device_id, ghi_score, confidence, sleep_score, cardio_score,
                   activity_score, recovery_score, tier, owner_id
            FROM health.ghi_daily
            WHERE owner_id = $1 AND device_id = $2 AND date >= (CURRENT_DATE - $3)
            ORDER BY date DESC
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, owner_id, device_id, days)

        history: list[GHIScoreResult] = []
        for row in rows:
            history.append(
                GHIScoreResult(
                    score=float(row["ghi_score"]),
                    confidence=float(row["confidence"]),
                    tier=GHITier(row["tier"]),
                    sleep_score=self._as_float(row["sleep_score"]),
                    cardio_score=self._as_float(row["cardio_score"]),
                    activity_score=self._as_float(row["activity_score"]),
                    recovery_score=self._as_float(row["recovery_score"]),
                    weights={},
                    suppressed=False,
                    computed_at=datetime.combine(row["date"], datetime.min.time(), tzinfo=UTC),
                    owner_id=str(row["owner_id"]),
                    device_id=str(row["device_id"]),
                )
            )
        return history

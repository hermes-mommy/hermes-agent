"""Per-metric anomaly detection engine.

Uses metric-specific thresholds (not ±20% universal). Handles persistence requirements
(1 reading ≠ anomaly — must persist N consecutive readings or exceed threshold by margin).
Assigns SEV levels matching the alert severity matrix. Logs to health.anomaly_events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from uuid import UUID

import asyncpg
import structlog

from guinevere.wearable.models import AlertSeverity, AnomalyEvent, HealthMetricType, NormalizedHealthSample

logger = structlog.get_logger(__name__)


@runtime_checkable
class BaselineResultProtocol(Protocol):
    """Structural baseline contract used when guinevere.wearable.baseline is unavailable."""

    metric: HealthMetricType | str
    stage: object
    baseline_value: float | None
    data_points: int


BaselineLike = BaselineResultProtocol


@dataclass(frozen=True, slots=True)
class SeverityRule:
    min_consecutive: int
    threshold_pct: float | None = None
    threshold_abs_min: float | None = None
    threshold_abs_max: float | None = None
    sev: AlertSeverity = AlertSeverity.SEV3
    description: str = ""


@dataclass(frozen=True, slots=True)
class AnomalyThreshold:
    name: str
    unit: str
    severity_rules: list[SeverityRule] = field(default_factory=list)


METRIC_THRESHOLDS: dict[HealthMetricType, AnomalyThreshold] = {
    HealthMetricType.HEART_RATE: AnomalyThreshold(
        name="heart_rate",
        unit="bpm",
        severity_rules=[
            SeverityRule(min_consecutive=3, threshold_abs_max=130, sev=AlertSeverity.SEV0, description="sustained high heart rate"),
            SeverityRule(min_consecutive=3, threshold_abs_min=40, sev=AlertSeverity.SEV1, description="low resting heart rate"),
            SeverityRule(min_consecutive=3, threshold_abs_min=-5, threshold_abs_max=5, sev=AlertSeverity.SEV2, description="resting heart rate deviation from baseline"),
        ],
    ),
    HealthMetricType.STEPS: AnomalyThreshold(
        name="daily_activity",
        unit="steps",
        severity_rules=[
            SeverityRule(min_consecutive=2, threshold_pct=-40.0, sev=AlertSeverity.SEV2, description="activity down 40% from baseline"),
            SeverityRule(min_consecutive=2, threshold_abs_min=0, threshold_abs_max=0, sev=AlertSeverity.SEV2, description="zero steps for an active baseline"),
        ],
    ),
    HealthMetricType.SPO2: AnomalyThreshold(
        name="spo2",
        unit="%",
        severity_rules=[
            SeverityRule(min_consecutive=2, threshold_abs_min=90, sev=AlertSeverity.SEV0, description="urgent low oxygen saturation"),
            SeverityRule(min_consecutive=2, threshold_abs_min=92, sev=AlertSeverity.SEV1, description="high concern oxygen saturation"),
            SeverityRule(min_consecutive=2, threshold_abs_min=94, sev=AlertSeverity.SEV2, description="wellness caution oxygen saturation"),
        ],
    ),
    HealthMetricType.STRESS: AnomalyThreshold(
        name="stress",
        unit="score",
        severity_rules=[
            SeverityRule(min_consecutive=3, threshold_pct=50.0, sev=AlertSeverity.SEV1, description="stress elevated 50% above baseline"),
            SeverityRule(min_consecutive=3, threshold_pct=30.0, sev=AlertSeverity.SEV2, description="stress elevated 30% above baseline"),
        ],
    ),
    HealthMetricType.SLEEP: AnomalyThreshold(
        name="sleep_sessions",
        unit="minutes",
        severity_rules=[
            SeverityRule(min_consecutive=2, threshold_abs_max=120, sev=AlertSeverity.SEV1, description="sleep duration under 2 hours"),
            SeverityRule(min_consecutive=2, threshold_abs_max=240, sev=AlertSeverity.SEV2, description="sleep duration under 4 hours"),
            SeverityRule(min_consecutive=3, threshold_abs_max=240, sev=AlertSeverity.SEV1, description="three consecutive poor nights"),
        ],
    ),
}


_INSFFICIENT_STAGE_NAMES = {"insufficient"}


class AnomalyDetector:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def _ensure_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._database_url, min_size=1, max_size=5)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def detect_anomalies(
        self,
        metric: HealthMetricType,
        baseline: BaselineLike,
        samples: list[NormalizedHealthSample],
        owner_id: str,
        device_id: str,
    ) -> list[AnomalyEvent]:
        if not samples:
            logger.info("anomaly_detection_empty_samples", metric=metric.value)
            return []

        threshold = METRIC_THRESHOLDS.get(metric)
        if threshold is None:
            logger.error("anomaly_threshold_missing", metric=metric.value)
            return []

        if self._is_insufficient_baseline(baseline):
            logger.info("insufficient baseline for %s", metric.value)
            return []

        baseline_value = self._baseline_value(baseline)
        if baseline_value is None:
            logger.info("insufficient baseline for %s", metric.value)
            return []

        events: list[AnomalyEvent] = []
        sorted_samples = sorted(samples, key=lambda s: s.timestamp)
        matching_rules = threshold.severity_rules
        for idx, sample in enumerate(sorted_samples):
            rule, deviation = self._evaluate_sample(metric, sample, baseline_value, matching_rules)
            if rule is None:
                continue
            consecutive = self._count_consecutive(sorted_samples, idx, metric, baseline_value, rule)
            if consecutive < rule.min_consecutive:
                continue
            events.append(
                AnomalyEvent(
                    time=sample.timestamp,
                    device_id=device_id,
                    owner_id=owner_id,
                    metric=metric.value,
                    severity=rule.sev,
                    value=sample.value,
                    baseline=baseline_value,
                    deviation=deviation,
                    description=rule.description or self._default_description(metric, sample.value, baseline_value),
                    alert_sent=False,
                )
            )
        return events

    async def detect_all_metrics(
        self,
        baselines: dict[HealthMetricType, BaselineLike],
        samples: list[NormalizedHealthSample],
        owner_id: str,
        device_id: str,
    ) -> list[AnomalyEvent]:
        if not samples:
            logger.info("anomaly_detection_no_samples")
            return []

        grouped: dict[HealthMetricType, list[NormalizedHealthSample]] = {}
        for sample in samples:
            grouped.setdefault(sample.metric_type, []).append(sample)

        events: list[AnomalyEvent] = []
        for metric, metric_samples in grouped.items():
            baseline = baselines.get(metric)
            if baseline is None:
                logger.info("insufficient baseline for %s", metric.value)
                continue
            events.extend(await self.detect_anomalies(metric, baseline, metric_samples, owner_id, device_id))
        return events

    async def persist_anomalies(self, events: list[AnomalyEvent]) -> int:
        if not events:
            return 0
        pool = await self._ensure_pool()
        query = """
            INSERT INTO health.anomaly_events
                (time, device_id, metric, severity, value, baseline, deviation, description, alert_sent, owner_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        records = [
            (
                event.time,
                self._as_uuid(event.device_id),
                event.metric,
                event.severity.value,
                event.value,
                event.baseline,
                event.deviation,
                event.description,
                event.alert_sent,
                self._as_uuid(event.owner_id),
            )
            for event in events
        ]
        async with pool.acquire() as conn:
            await conn.executemany(query, records)
        return len(records)

    def _evaluate_sample(
        self,
        metric: HealthMetricType,
        sample: NormalizedHealthSample,
        baseline_value: float,
        rules: list[SeverityRule],
    ) -> tuple[SeverityRule | None, float | None]:
        if metric is HealthMetricType.HEART_RATE:
            for rule in rules:
                if rule.threshold_abs_max is not None and sample.value > rule.threshold_abs_max:
                    return rule, sample.value - baseline_value
                if rule.threshold_abs_min is not None and sample.value < rule.threshold_abs_min:
                    return rule, baseline_value - sample.value
                if rule.threshold_abs_min is not None and rule.threshold_abs_max is not None and not (rule.threshold_abs_min <= sample.value <= rule.threshold_abs_max):
                    return rule, abs(sample.value - baseline_value)
            return None, None

        if metric is HealthMetricType.STEPS:
            for rule in rules:
                if rule.threshold_pct is not None and baseline_value > 0:
                    pct_delta = ((sample.value - baseline_value) / baseline_value) * 100.0
                    if pct_delta <= rule.threshold_pct:
                        return rule, abs(pct_delta)
                if rule.threshold_abs_min == 0 and rule.threshold_abs_max == 0 and sample.value == 0 and baseline_value > 0:
                    return rule, baseline_value
            return None, None

        if metric is HealthMetricType.SPO2:
            for rule in rules:
                if rule.threshold_abs_min is not None and sample.value < rule.threshold_abs_min:
                    return rule, baseline_value - sample.value
            return None, None

        if metric is HealthMetricType.STRESS:
            for rule in rules:
                if rule.threshold_pct is not None and baseline_value > 0:
                    pct_delta = ((sample.value - baseline_value) / baseline_value) * 100.0
                    if pct_delta >= rule.threshold_pct:
                        return rule, pct_delta
            return None, None

        if metric is HealthMetricType.SLEEP:
            for rule in rules:
                if rule.threshold_abs_max is not None and sample.value < rule.threshold_abs_max:
                    return rule, baseline_value - sample.value
            return None, None

        return None, None

    def _count_consecutive(
        self,
        samples: list[NormalizedHealthSample],
        start_index: int,
        metric: HealthMetricType,
        baseline_value: float,
        rule: SeverityRule,
    ) -> int:
        count = 0
        for sample in samples[start_index:]:
            matched, _ = self._evaluate_sample(metric, sample, baseline_value, [rule])
            if matched is None:
                break
            count += 1
        return count

    @staticmethod
    def _baseline_value(baseline: BaselineLike) -> float | None:
        value = getattr(baseline, "baseline_value", None)
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _is_insufficient_baseline(baseline: BaselineLike) -> bool:
        stage = getattr(baseline, "stage", None)
        stage_value = getattr(stage, "value", stage)
        return str(stage_value) in _INSFFICIENT_STAGE_NAMES

    @staticmethod
    def _default_description(metric: HealthMetricType, value: float, baseline_value: float) -> str:
        return f"{metric.value} anomaly: value={value:.2f}, baseline={baseline_value:.2f}"

    @staticmethod
    def _as_uuid(value: str) -> UUID:
        return UUID(value)


__all__ = [
    "AnomalyDetector",
    "AnomalyThreshold",
    "SeverityRule",
    "METRIC_THRESHOLDS",
]

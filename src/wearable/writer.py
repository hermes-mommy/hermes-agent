"""TimescaleDB writer for wearable health data.

Consumes NormalizedHealthSample records and upserts them into the appropriate
TimescaleDB hypertables. Uses asyncpg for high-throughput async writes.
Handles per-metric routing, upsert conflict resolution, and batch processing.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

import asyncpg
import structlog
from prometheus_client import Counter

from src.wearable.encryption import encrypt_health_record
from src.wearable.health_consent import check_metric_consent
from src.wearable.models import HealthMetricType, NormalizedHealthSample

logger = structlog.get_logger(__name__)

wearable_db_writes_total = Counter(
    "wearable_db_writes_total",
    "Total wearable database write attempts",
    ["table", "status"],
)
wearable_db_write_errors_total = Counter(
    "wearable_db_write_errors_total",
    "Total wearable database write errors",
    ["table"],
)
wearable_consent_blocked_total = Counter(
    "wearable_consent_blocked_total",
    "Total wearable samples blocked by consent gate",
    ["metric"],
)


@dataclass(slots=True)
class WriteResult:
    inserted: int = 0
    updated: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def add(self, other: WriteResult) -> None:
        self.inserted += other.inserted
        self.updated += other.updated
        self.failed += other.failed
        self.errors.extend(other.errors)


class HealthIngestionWriter:
    _METRIC_TABLE_MAP: dict[HealthMetricType, str] = {
        HealthMetricType.HEART_RATE: "health.heart_rate",
        HealthMetricType.STEPS: "health.daily_activity",
        HealthMetricType.ACTIVITY: "health.daily_activity",
        HealthMetricType.SPO2: "health.spo2",
        HealthMetricType.STRESS: "health.stress",
        HealthMetricType.SLEEP: "health.sleep_sessions",
    }

    def __init__(self, database_url: str, batch_size: int = 100) -> None:
        self._database_url = database_url
        self._batch_size = batch_size
        self._pool: asyncpg.Pool | None = None
        self._METRIC_UPSERT_MAP: dict[HealthMetricType, Callable[[list[NormalizedHealthSample]], Awaitable[int]]] = {
            HealthMetricType.HEART_RATE: self._upsert_heart_rate,
            HealthMetricType.STEPS: self._upsert_daily_activity,
            HealthMetricType.ACTIVITY: self._upsert_daily_activity,
            HealthMetricType.SPO2: self._upsert_spo2,
            HealthMetricType.STRESS: self._upsert_stress,
            HealthMetricType.SLEEP: self._upsert_sleep,
        }

    async def _ensure_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._database_url, min_size=1, max_size=10)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def write_samples(self, samples: list[NormalizedHealthSample]) -> WriteResult:
        if not samples:
            return WriteResult()

        result = WriteResult()
        for start in range(0, len(samples), self._batch_size):
            batch = samples[start : start + self._batch_size]
            batch_result = await self._write_batch(batch)
            result.add(batch_result)
        return result

    async def _write_batch(self, samples: list[NormalizedHealthSample]) -> WriteResult:
        result = WriteResult()
        grouped: dict[HealthMetricType, list[NormalizedHealthSample]] = {}
        for sample in samples:
            grouped.setdefault(sample.metric_type, []).append(sample)

        for metric_type, metric_samples in grouped.items():
            table = self._METRIC_TABLE_MAP.get(metric_type)
            if table is None:
                msg = f"unsupported_metric_type:{metric_type.value}"
                logger.warning("wearable_write_unsupported_metric", metric_type=metric_type.value)
                result.failed += len(metric_samples)
                result.errors.append(msg)
                wearable_db_write_errors_total.labels(table="unknown").inc(len(metric_samples))
                continue

            upsert = self._METRIC_UPSERT_MAP.get(metric_type)
            if upsert is None:
                msg = f"missing_upsert_handler:{metric_type.value}"
                logger.error("wearable_write_missing_handler", metric_type=metric_type.value)
                result.failed += len(metric_samples)
                result.errors.append(msg)
                wearable_db_write_errors_total.labels(table=table).inc(len(metric_samples))
                continue

            # Consent gate (fail-closed)
            try:
                consent = await check_metric_consent(metric_type)
            except Exception as exc:
                logger.error("consent_gate_failure", error=str(exc), metric_type=metric_type.value)
                result.failed += len(metric_samples)
                result.errors.append(f"consent_gate_failure:{metric_type.value}")
                wearable_db_write_errors_total.labels(table=table).inc(len(metric_samples))
                continue

            if not consent.allowed:
                logger.info("sample_consent_blocked", metric=metric_type, scope=consent.scope, count=len(metric_samples))
                wearable_consent_blocked_total.labels(metric=metric_type.value).inc(len(metric_samples))
                continue

            # Encrypt sensitive fields
            encrypted_samples: list[NormalizedHealthSample] = []
            for sample in metric_samples:
                record: dict[str, object] = {
                    "device_id": sample.device_id,
                    "owner_id": sample.owner_id,
                    "metadata": dict(sample.metadata),
                }
                encrypted = encrypt_health_record(record, fields=("device_id", "owner_id", "metadata"))
                encrypted_sample = sample.model_copy(update={
                    "device_id": str(encrypted["device_id"]),
                    "owner_id": str(encrypted["owner_id"]),
                })
                encrypted_samples.append(encrypted_sample)

            try:
                changed = await upsert(encrypted_samples)
                result.inserted += changed
                wearable_db_writes_total.labels(table=table, status="ok").inc(changed)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "wearable_write_failed",
                    metric_type=metric_type.value,
                    table=table,
                    sample_count=len(metric_samples),
                )
                result.failed += len(metric_samples)
                error_text = f"{table}:{metric_type.value}:{exc}"
                result.errors.append(error_text)
                wearable_db_write_errors_total.labels(table=table).inc(len(metric_samples))
        return result

    @staticmethod
    def _as_uuid(value: str) -> UUID:
        return UUID(value)

    @staticmethod
    def _round_smallint(value: float) -> int:
        return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    async def _upsert_heart_rate(self, samples: list[NormalizedHealthSample]) -> int:
        pool = await self._ensure_pool()
        query = """
            INSERT INTO health.heart_rate (time, device_id, bpm, resting_bpm, source, confidence, owner_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (time, device_id, owner_id) DO UPDATE
            SET bpm = EXCLUDED.bpm,
                resting_bpm = EXCLUDED.resting_bpm,
                source = EXCLUDED.source,
                confidence = EXCLUDED.confidence
        """
        records: list[tuple[Any, ...]] = []
        for sample in samples:
            bpm = self._round_smallint(sample.value)
            resting_bpm = None
            if sample.metadata.get("resting_bpm") is not None:
                resting_bpm = self._round_smallint(float(sample.metadata["resting_bpm"]))
            records.append((sample.timestamp, self._as_uuid(sample.device_id), bpm, resting_bpm, sample.source.value, sample.confidence, self._as_uuid(sample.owner_id)))
        async with pool.acquire() as conn:
            await conn.executemany(query, records)
        return len(records)

    async def _upsert_daily_activity(self, samples: list[NormalizedHealthSample]) -> int:
        pool = await self._ensure_pool()
        query = """
            INSERT INTO health.daily_activity (date, steps, active_min, calories, distance_m, source, device_id, owner_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (date, device_id, owner_id) DO UPDATE
            SET steps = EXCLUDED.steps,
                active_min = EXCLUDED.active_min,
                calories = EXCLUDED.calories,
                distance_m = EXCLUDED.distance_m,
                source = EXCLUDED.source
        """
        records: list[tuple[Any, ...]] = []
        for sample in samples:
            sample_date = sample.timestamp.date()
            steps = self._round_smallint(sample.value)
            active_min = int(sample.metadata["active_min"]) if sample.metadata.get("active_min") is not None else None
            calories = int(sample.metadata["calories"]) if sample.metadata.get("calories") is not None else None
            distance_m = float(sample.metadata["distance_m"]) if sample.metadata.get("distance_m") is not None else None
            records.append((sample_date, steps, active_min, calories, distance_m, sample.source.value, self._as_uuid(sample.device_id), self._as_uuid(sample.owner_id)))
        async with pool.acquire() as conn:
            await conn.executemany(query, records)
        return len(records)

    async def _upsert_spo2(self, samples: list[NormalizedHealthSample]) -> int:
        pool = await self._ensure_pool()
        query = """
            INSERT INTO health.spo2 (time, device_id, spo2_pct, source, owner_id)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (time, device_id, owner_id) DO UPDATE
            SET spo2_pct = EXCLUDED.spo2_pct,
                source = EXCLUDED.source
        """
        records: list[tuple[Any, ...]] = [
            (sample.timestamp, self._as_uuid(sample.device_id), float(sample.value), sample.source.value, self._as_uuid(sample.owner_id))
            for sample in samples
        ]
        async with pool.acquire() as conn:
            await conn.executemany(query, records)
        return len(records)

    async def _upsert_stress(self, samples: list[NormalizedHealthSample]) -> int:
        pool = await self._ensure_pool()
        query = """
            INSERT INTO health.stress (time, device_id, score, source, owner_id)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (time, device_id, owner_id) DO UPDATE
            SET score = EXCLUDED.score,
                source = EXCLUDED.source
        """
        records: list[tuple[Any, ...]] = [
            (sample.timestamp, self._as_uuid(sample.device_id), self._round_smallint(sample.value), sample.source.value, self._as_uuid(sample.owner_id))
            for sample in samples
        ]
        async with pool.acquire() as conn:
            await conn.executemany(query, records)
        return len(records)

    async def _upsert_sleep(self, samples: list[NormalizedHealthSample]) -> int:
        pool = await self._ensure_pool()
        query = """
            INSERT INTO health.sleep_sessions (
                device_id, sleep_date, start_time, end_time, total_s, deep_s, rem_s, light_s, awake_s, efficiency_pct, source, owner_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (sleep_date, device_id, owner_id) DO UPDATE
            SET start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                total_s = EXCLUDED.total_s,
                deep_s = EXCLUDED.deep_s,
                rem_s = EXCLUDED.rem_s,
                light_s = EXCLUDED.light_s,
                awake_s = EXCLUDED.awake_s,
                efficiency_pct = EXCLUDED.efficiency_pct,
                source = EXCLUDED.source
        """
        records: list[tuple[Any, ...]] = []
        for sample in samples:
            md = sample.metadata
            sleep_date = date.fromisoformat(md["sleep_date"]) if md.get("sleep_date") is not None else sample.timestamp.date()
            records.append(
                (
                    self._as_uuid(sample.device_id),
                    sleep_date,
                    sample.timestamp,
                    sample.timestamp,
                    int(md["total_s"]) if md.get("total_s") is not None else None,
                    int(md["deep_s"]) if md.get("deep_s") is not None else None,
                    int(md["rem_s"]) if md.get("rem_s") is not None else None,
                    int(md["light_s"]) if md.get("light_s") is not None else None,
                    int(md["awake_s"]) if md.get("awake_s") is not None else None,
                    float(md["efficiency_pct"]) if md.get("efficiency_pct") is not None else None,
                    sample.source.value,
                    self._as_uuid(sample.owner_id),
                )
            )
        async with pool.acquire() as conn:
            await conn.executemany(query, records)
        return len(records)

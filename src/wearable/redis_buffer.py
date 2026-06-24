"""Redis buffer for wearable health data ingestion pipeline.

Mirrors the surveillance pipeline pattern: push to Redis list → consumer picks up → TimescaleDB.
Uses Redis DB2 (same as surveillance) with separate key namespace `wearable:health:*`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import redis
import structlog

from src.wearable.models import NormalizedHealthSample

logger = structlog.get_logger(__name__)

wearable_samples_pushed_total = None
wearable_buffer_length = None
wearable_samples_dead_lettered_total = None


class WearableBuffer:
    """Redis DB2-backed wearable health sample buffer."""

    def __init__(self, redis_url: str, db: int = 2, max_buffer_size: int = 10000) -> None:
        self._redis = redis.Redis.from_url(redis_url, db=db, decode_responses=True)
        self._ingest_key = "wearable:health:ingest"
        self._dead_letter_key = "wearable:health:dead_letter"
        self._cursor_prefix = "wearable:health:cursor"
        self._max_buffer_size = max_buffer_size

    def push_samples(self, samples: list[NormalizedHealthSample]) -> int:
        pushed = 0
        try:
            pipe = self._redis.pipeline()
            for sample in samples:
                pipe.rpush(self._ingest_key, sample.model_dump_json())
            if samples:
                pipe.llen(self._ingest_key)
            results = pipe.execute()
            if samples:
                pushed = len(samples)
                current_length = int(results[-1]) if results else 0
                if wearable_samples_pushed_total is not None:
                    wearable_samples_pushed_total.inc(pushed)
                if wearable_buffer_length is not None:
                    wearable_buffer_length.set(current_length)
                logger.info("wearable_buffer_push_samples", pushed=pushed, buffer_length=current_length)
            return pushed
        except Exception as exc:  # noqa: BLE001
            logger.exception("wearable_buffer_push_samples_failed", error=str(exc), sample_count=len(samples))
            return 0

    def pop_batch(self, batch_size: int = 100) -> list[NormalizedHealthSample]:
        try:
            raw_items = self._redis.lpop(self._ingest_key, batch_size)
            if raw_items is None:
                items = []
            elif isinstance(raw_items, str):
                items = [raw_items]
            else:
                items = [item.decode() if isinstance(item, bytes) else str(item) for item in raw_items]

            samples: list[NormalizedHealthSample] = []
            for raw_item in items:
                try:
                    samples.append(NormalizedHealthSample.model_validate_json(raw_item))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("wearable_buffer_bad_json", error=str(exc))
            if wearable_buffer_length is not None:
                wearable_buffer_length.set(self.buffer_length())
            logger.info("wearable_buffer_pop_batch", requested=batch_size, returned=len(samples))
            return samples
        except Exception as exc:  # noqa: BLE001
            logger.exception("wearable_buffer_pop_batch_failed", error=str(exc), batch_size=batch_size)
            return []

    def buffer_length(self) -> int:
        try:
            return int(self._redis.llen(self._ingest_key))
        except Exception as exc:  # noqa: BLE001
            logger.exception("wearable_buffer_length_failed", error=str(exc))
            return 0

    def push_dead_letter(self, sample: NormalizedHealthSample, reason: str) -> None:
        payload = {
            "sample": json.loads(sample.model_dump_json()),
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self._redis.rpush(self._dead_letter_key, json.dumps(payload, default=str))
            if wearable_samples_dead_lettered_total is not None:
                wearable_samples_dead_lettered_total.inc()
            logger.warning("wearable_buffer_dead_lettered", reason=reason, metric_type=sample.metric_type.value)
        except Exception as exc:  # noqa: BLE001
            logger.exception("wearable_buffer_dead_letter_failed", error=str(exc), reason=reason)

    def get_cursor(self, owner_id: str) -> datetime | None:
        key = f"{self._cursor_prefix}:{owner_id}"
        try:
            raw_value = self._redis.get(key)
            if not raw_value:
                return None
            return datetime.fromisoformat(raw_value.decode() if isinstance(raw_value, bytes) else raw_value)
        except Exception as exc:  # noqa: BLE001
            logger.exception("wearable_buffer_get_cursor_failed", error=str(exc), owner_id=owner_id)
            return None

    def set_cursor(self, owner_id: str, ts: datetime) -> None:
        key = f"{self._cursor_prefix}:{owner_id}"
        try:
            self._redis.set(key, ts.astimezone(timezone.utc).isoformat())
            logger.info("wearable_buffer_cursor_updated", owner_id=owner_id, timestamp=ts.isoformat())
        except Exception as exc:  # noqa: BLE001
            logger.exception("wearable_buffer_set_cursor_failed", error=str(exc), owner_id=owner_id)

"""Wearable health sync entrypoint.

Orchestrates: Consent Gate → Data Source (Mi Fitness / Gadgetbridge) → Normalizer → Redis Buffer.
Called by systemd timer (guinevere-wearable-sync.timer) every 30 minutes.
Can also be invoked manually: python -m src.wearable.sync
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import structlog

from src.wearable.health_consent import check_all_metrics_consent

logger = structlog.get_logger(__name__)


async def _sync_mi_fitness(config: "WearableConfig", granted_metrics: set) -> None:
    """Run the Mi Fitness Cloud sync path."""
    from src.wearable.mi_fitness_client import MiFitnessClient
    from src.wearable.models import DateRange
    from src.wearable.normalizer import normalize_fetch_result
    from src.wearable.redis_buffer import WearableBuffer

    client = MiFitnessClient(config)
    buffer = WearableBuffer(redis_url=f"redis://{config.redis_host}:{config.redis_port}/2")

    await client.authenticate()

    cursor = buffer.get_cursor(config.wearable_owner_id)
    end_ts = datetime.now(timezone.utc)
    start_ts = cursor or (end_ts - timedelta(hours=config.wearable_sync_lookback_hours))
    date_range = DateRange(start=start_ts.date(), end=end_ts.date())

    fetch_result = await client.fetch_metrics(date_range)

    # Per-metric consent filter
    skipped_metrics: list[str] = []
    filtered_metrics = {}
    for metric_name, metric_result in fetch_result.metrics.items():
        if metric_result.metric in granted_metrics:
            filtered_metrics[metric_name] = metric_result
        else:
            skipped_metrics.append(metric_name)
            logger.info("metric_consent_skipped", metric=metric_name)
    fetch_result.metrics = filtered_metrics

    payload = normalize_fetch_result(fetch_result, config.wearable_device_id, config.wearable_owner_id)
    buffered_count = buffer.push_samples(payload.samples)
    buffer.set_cursor(config.wearable_owner_id, end_ts)

    logger.info(
        "wearable_health_sync_completed",
        data_source="mi_fitness",
        metrics_fetched=len(fetch_result.metrics),
        metrics_skipped_consent=len(skipped_metrics),
        samples_normalized=len(payload.samples),
        samples_buffered=buffered_count,
        device_id=config.wearable_device_id,
        owner_id=config.wearable_owner_id,
    )


def _sync_gadgetbridge(config: "WearableConfig", granted_metrics: set) -> None:
    """Run the Gadgetbridge SQLite sync path (sync, no network)."""
    from pathlib import Path

    from src.wearable.gadgetbridge_client import parse_gadgetbridge_db
    from src.wearable.normalizer import normalize_gadgetbridge_result
    from src.wearable.redis_buffer import WearableBuffer

    db_path = Path(config.gadgetbridge_db_path)
    buffer = WearableBuffer(redis_url=f"redis://{config.redis_host}:{config.redis_port}/2")

    cursor = buffer.get_cursor(config.wearable_owner_id)
    since = cursor  # None means parse everything

    result = parse_gadgetbridge_db(
        db_path=db_path,
        device_id=config.gadgetbridge_device_name or config.wearable_device_id,
        since=since,
    )

    # Per-metric consent filter
    skipped_metrics: list[str] = []
    filtered_samples = []
    for sample in result.samples:
        if sample.metric_type in granted_metrics:
            filtered_samples.append(sample)
        else:
            if sample.metric_type.value not in skipped_metrics:
                skipped_metrics.append(sample.metric_type.value)
                logger.info("metric_consent_skipped", metric=sample.metric_type.value)

    payload = normalize_gadgetbridge_result(
        samples=filtered_samples,
        device_id=config.gadgetbridge_device_name or config.wearable_device_id,
        owner_id=config.wearable_owner_id,
    )
    buffered_count = buffer.push_samples(payload.samples)
    buffer.set_cursor(config.wearable_owner_id, datetime.now(timezone.utc))

    logger.info(
        "wearable_health_sync_completed",
        data_source="gadgetbridge",
        tables_parsed=len(result.tables_parsed),
        metrics_skipped_consent=len(skipped_metrics),
        samples_normalized=len(payload.samples),
        samples_buffered=buffered_count,
        device_id=config.gadgetbridge_device_name or config.wearable_device_id,
        owner_id=config.wearable_owner_id,
    )


async def health_sync() -> None:
    start_time = datetime.now(timezone.utc)
    try:
        from src.wearable.config import get_wearable_config

        config = get_wearable_config()

        # Consent gate — runs BEFORE authenticate/fetch/push
        consent_results = await check_all_metrics_consent()
        if not any(result.allowed for result in consent_results.values()):
            logger.warning("sync_blocked_all_consent_revoked")
            return

        granted_metrics = {metric for metric, result in consent_results.items() if result.allowed}

        if config.wearable_data_source == "gadgetbridge":
            _sync_gadgetbridge(config, granted_metrics)
        elif config.wearable_data_source == "mi_fitness":
            await _sync_mi_fitness(config, granted_metrics)
        else:
            raise ValueError(f"Unknown data source: {config.wearable_data_source}")

        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info("wearable_sync_cycle_completed", data_source=config.wearable_data_source, duration_sec=duration_sec)
    except Exception as exc:  # noqa: BLE001
        logger.exception("wearable_health_sync_failed", error=str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    try:
        asyncio.run(health_sync())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("wearable_health_sync_fatal", error=str(exc))
        sys.exit(1)
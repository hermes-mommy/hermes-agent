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

from guinevere.wearable.health_consent import check_all_metrics_consent

logger = structlog.get_logger(__name__)


def _filter_samples_by_consent(
    samples: list, granted_metrics: set[str]
) -> tuple[list, list[str]]:
    """Filter normalized samples by per-metric consent.

    Returns a tuple of (allowed_samples, skipped_metric_names).
    Each metric type is logged at most once.
    """
    skipped: list[str] = []
    filtered: list = []
    for sample in samples:
        if sample.metric_type in granted_metrics:
            filtered.append(sample)
        else:
            if sample.metric_type.value not in skipped:
                skipped.append(sample.metric_type.value)
                logger.info("metric_consent_skipped", metric=sample.metric_type.value)
    return filtered, skipped


def _build_redis_url(config: "WearableConfig", db: int = 2) -> str:
    """Build Redis URL with password authentication if configured."""
    password = config.redis_password
    if password:
        return f"redis://:{password}@{config.redis_host}:{config.redis_port}/{db}"
    return f"redis://{config.redis_host}:{config.redis_port}/{db}"


async def _sync_mi_fitness(config: "WearableConfig", granted_metrics: set) -> None:
    """Run the Mi Fitness Cloud sync path."""
    from guinevere.wearable.mi_fitness_client import MiFitnessClient
    from guinevere.wearable.models import DateRange
    from guinevere.wearable.normalizer import normalize_fetch_result
    from guinevere.wearable.redis_buffer import WearableBuffer

    client = MiFitnessClient(config)
    buffer = WearableBuffer(redis_url=_build_redis_url(config))

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

    from guinevere.wearable.gadgetbridge_client import parse_gadgetbridge_db
    from guinevere.wearable.normalizer import normalize_gadgetbridge_result
    from guinevere.wearable.redis_buffer import WearableBuffer

    db_path = Path(config.gadgetbridge_db_path)
    buffer = WearableBuffer(redis_url=_build_redis_url(config))

    cursor = buffer.get_cursor(config.wearable_owner_id)
    since = cursor  # None means parse everything

    result = parse_gadgetbridge_db(
        db_path=db_path,
        device_id=config.gadgetbridge_device_name or config.wearable_device_id,
        since=since,
    )

    # Per-metric consent filter
    filtered_samples, skipped_metrics = _filter_samples_by_consent(
        list(result.samples), granted_metrics
    )

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


def _sync_health_connect(config: "WearableConfig", granted_metrics: set) -> None:
    """Run the Health Connect JSON export sync path (sync, local file).

    Reads the Health Connect JSON export file at
    ``config.health_connect_json_path``, parses it with the stored per-owner
    cursor as the lower bound (``since``), normalizes the raw samples,
    filters by per-metric consent, and pushes the remaining samples to the
    Redis DB2 ingest buffer. The cursor is then advanced to
    ``parse_result.export_timestamp``.

    On a missing export file the sync is skipped with a warning log — the
    Android ``HealthConnectExport`` service may not have produced an
    export yet. On a parse error the sync is skipped with an error log
    and the cursor is not advanced, so the next run retries the same
    file. The Redis push is internal-exception-safe; buffer failures are
    logged inside the buffer and do not fail the sync.
    """
    from guinevere.wearable.errors import HealthConnectFileNotFoundError, HealthConnectParseError
    from guinevere.wearable.health_connect_client import parse_health_connect_export
    from guinevere.wearable.normalizer import normalize_health_connect_result
    from guinevere.wearable.redis_buffer import WearableBuffer

    buffer = WearableBuffer(redis_url=_build_redis_url(config))

    cursor = buffer.get_cursor(config.wearable_owner_id)

    logger.info(
        "health_connect_sync_started",
        path=config.health_connect_json_path,
        cursor=cursor.isoformat() if cursor is not None else None,
        device_id=config.health_connect_device_name or config.wearable_device_id,
    )

    try:
        parse_result = parse_health_connect_export(
            json_path=config.health_connect_json_path,
            since=cursor,
        )
    except HealthConnectFileNotFoundError as exc:
        logger.warning(
            "health_connect_file_not_found",
            path=config.health_connect_json_path,
            error=str(exc),
        )
        return
    except HealthConnectParseError as exc:
        logger.error(
            "health_connect_parse_failed",
            path=config.health_connect_json_path,
            error=str(exc),
        )
        return

    device_id = config.health_connect_device_name or config.wearable_device_id

    normalized = normalize_health_connect_result(
        result=parse_result,
        device_id=device_id,
        owner_id=config.wearable_owner_id,
    )

    filtered_samples, skipped_metrics = _filter_samples_by_consent(normalized, granted_metrics)
    buffered_count = buffer.push_samples(filtered_samples)

    # _coerce_export_timestamp falls back to datetime.utcnow() (naive) when
    # the export file omits the export_timestamp field. Normalize to UTC so
    # buffer.set_cursor can apply astimezone() without raising.
    export_ts = parse_result.export_timestamp
    if export_ts.tzinfo is None:
        export_ts = export_ts.replace(tzinfo=timezone.utc)
    buffer.set_cursor(config.wearable_owner_id, export_ts)

    logger.info(
        "health_connect_sync_completed",
        samples_parsed=len(parse_result.samples),
        samples_normalized=len(normalized),
        samples_buffered=buffered_count,
        metrics_skipped_consent=len(skipped_metrics),
        export_timestamp=export_ts.isoformat(),
        device_id=device_id,
        owner_id=config.wearable_owner_id,
    )


async def health_sync() -> None:
    start_time = datetime.now(timezone.utc)
    try:
        from guinevere.wearable.config import get_wearable_config

        config = get_wearable_config()

        # Consent gate — runs BEFORE authenticate/fetch/push
        consent_results = await check_all_metrics_consent()
        if not any(result.allowed for result in consent_results.values()):
            logger.warning("sync_blocked_all_consent_revoked")
            return

        granted_metrics = {metric for metric, result in consent_results.items() if result.allowed}

        if config.wearable_data_source == "health_connect":
            _sync_health_connect(config, granted_metrics)
        elif config.wearable_data_source == "gadgetbridge":
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
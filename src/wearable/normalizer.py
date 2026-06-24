"""Data normalizer — converts raw Mi Fitness API responses to unified health models.

Pure functions, no side effects. Each metric type has its own extractor function.
The main entry point is `normalize_fetch_result()` which processes all metrics
in a FetchResult and produces a HealthMetricPayload.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import structlog
from structlog.stdlib import BoundLogger

from src.wearable.models import FetchResult, HealthMetricPayload, HealthMetricType, MetricResult, MetricSource, MetricStatus, NormalizedHealthSample

logger: BoundLogger = structlog.get_logger(__name__)


def normalize_fetch_result(fetch_result: FetchResult, device_id: str, owner_id: str) -> HealthMetricPayload:
    samples: list[NormalizedHealthSample] = []
    metrics_available: list[HealthMetricType] = []
    metrics_unavailable: list[HealthMetricType] = []

    for metric_name, metric_result in fetch_result.metrics.items():
        try:
            metric = HealthMetricType(metric_name)
        except ValueError:
            logger.warning("unknown_metric_in_fetch_result", metric_name=metric_name)
            continue

        if metric_result.status != MetricStatus.AVAILABLE:
            metrics_unavailable.append(metric)
            continue

        extractor = _EXTRACTOR_MAP.get(metric)
        if extractor is None:
            logger.warning("missing_extractor_for_metric", metric=metric.value)
            metrics_unavailable.append(metric)
            continue

        raw_payload = _metric_result_to_raw_data(metric_result)
        extracted = extractor(raw_payload)
        if extracted:
            metrics_available.append(metric)
            samples.extend(_tag_samples(extracted, device_id, owner_id))
        else:
            metrics_unavailable.append(metric)
            logger.warning("metric_extracted_no_samples", metric=metric.value)

    return HealthMetricPayload(
        sync_timestamp=fetch_result.timestamp,
        device_id=device_id,
        owner_id=owner_id,
        source=MetricSource.MI_FITNESS_CLOUD,
        samples=samples,
        metrics_available=metrics_available,
        metrics_unavailable=metrics_unavailable,
    )


def _extract_heart_rate(raw_data: dict[str, Any]) -> list[NormalizedHealthSample]:
    return _extract_samples(raw_data, HealthMetricType.HEART_RATE, default_unit="bpm")


def _extract_steps(raw_data: dict[str, Any]) -> list[NormalizedHealthSample]:
    return _extract_samples(raw_data, HealthMetricType.STEPS, default_unit="steps")


def _extract_spo2(raw_data: dict[str, Any]) -> list[NormalizedHealthSample]:
    return _extract_samples(raw_data, HealthMetricType.SPO2, default_unit="%")


def _extract_stress(raw_data: dict[str, Any]) -> list[NormalizedHealthSample]:
    return _extract_samples(raw_data, HealthMetricType.STRESS, default_unit="score")


def _extract_sleep(raw_data: dict[str, Any]) -> list[NormalizedHealthSample]:
    return _extract_samples(raw_data, HealthMetricType.SLEEP, default_unit="minutes")


def _extract_activity(raw_data: dict[str, Any]) -> list[NormalizedHealthSample]:
    return _extract_samples(raw_data, HealthMetricType.ACTIVITY, default_unit="score")


_EXTRACTOR_MAP: dict[HealthMetricType, Callable[[dict[str, Any]], list[NormalizedHealthSample]]] = {
    HealthMetricType.HEART_RATE: _extract_heart_rate,
    HealthMetricType.STEPS: _extract_steps,
    HealthMetricType.SPO2: _extract_spo2,
    HealthMetricType.STRESS: _extract_stress,
    HealthMetricType.SLEEP: _extract_sleep,
    HealthMetricType.ACTIVITY: _extract_activity,
}


def _metric_result_to_raw_data(metric_result: MetricResult) -> dict[str, Any]:
    raw_samples = []
    for sample in metric_result.samples:
        raw_samples.append(
            {
                "timestamp": sample.timestamp.isoformat(),
                "value": sample.value,
                "unit": sample.unit,
                "confidence": sample.confidence,
                **sample.metadata,
            }
        )
    return {"samples": raw_samples}


def _extract_samples(raw_data: dict[str, Any], metric_type: HealthMetricType, default_unit: str) -> list[NormalizedHealthSample]:
    raw_samples = raw_data.get("samples") or raw_data.get("items") or raw_data.get("data") or []
    if not isinstance(raw_samples, list):
        raw_samples = [raw_samples]

    normalized: list[NormalizedHealthSample] = []
    for sample in raw_samples:
        parsed = _parse_sample(sample, metric_type, default_unit)
        if parsed is not None:
            normalized.append(parsed)
    return normalized


def _parse_sample(sample: Any, metric_type: HealthMetricType, default_unit: str) -> NormalizedHealthSample | None:
    if not isinstance(sample, dict):
        logger.warning("normalizer_skipping_non_dict_sample", metric=metric_type.value)
        return None

    timestamp = sample.get("timestamp") or sample.get("time") or sample.get("ts")
    value = sample.get("value") or sample.get("count") or sample.get("steps") or sample.get("rate")
    if timestamp is None or value is None:
        logger.warning("normalizer_missing_fields", metric=metric_type.value, keys=sorted(sample.keys()))
        return None

    try:
        parsed_timestamp = _parse_datetime(timestamp)
        parsed_value = float(value)
    except (TypeError, ValueError) as exc:
        logger.warning("normalizer_invalid_sample", metric=metric_type.value, error=str(exc))
        return None

    confidence = sample.get("confidence", 1.0)
    try:
        parsed_confidence = float(confidence)
    except (TypeError, ValueError):
        parsed_confidence = 1.0

    return NormalizedHealthSample(
        metric_type=metric_type,
        timestamp=parsed_timestamp,
        device_id="",
        owner_id="",
        value=parsed_value,
        unit=str(sample.get("unit") or default_unit),
        source=MetricSource.MI_FITNESS_CLOUD,
        confidence=parsed_confidence,
        metadata={k: str(v) for k, v in sample.items() if k not in {"timestamp", "time", "ts", "value", "count", "steps", "rate", "unit", "confidence"}},
    )


def _tag_samples(samples: list[NormalizedHealthSample], device_id: str, owner_id: str) -> list[NormalizedHealthSample]:
    return [sample.model_copy(update={"device_id": device_id, "owner_id": owner_id, "source": MetricSource.MI_FITNESS_CLOUD}) for sample in samples]


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    raise ValueError(f"Unsupported timestamp type: {type(value).__name__}")


# ── Gadgetbridge Normalizer ────────────────────────────────────────────────────


def normalize_gadgetbridge_result(
    samples: list,  # GadgetbridgeRawSample from gadgetbridge_client
    device_id: str,
    owner_id: str,
) -> HealthMetricPayload:
    """Convert Gadgetbridge raw samples to NormalizedHealthSample list.

    Gadgetbridge samples are already typed (GadgetbridgeRawSample with metric_type,
    timestamp, value, unit, raw_kind, metadata). This function converts them to
    the pipeline's unified NormalizedHealthSample format and tags with device_id/owner_id.
    """
    from src.wearable.gadgetbridge_client import GadgetbridgeRawSample

    normalized: list[NormalizedHealthSample] = []
    metrics_available: list[HealthMetricType] = []

    for raw in samples:
        if not isinstance(raw, GadgetbridgeRawSample):
            logger.warning("normalize_gadgetbridge_skipping_non_sample", type=type(raw).__name__)
            continue

        try:
            sample = NormalizedHealthSample(
                metric_type=raw.metric_type,
                timestamp=raw.timestamp,
                device_id=device_id,
                owner_id=owner_id,
                value=raw.value,
                unit=raw.unit,
                source=MetricSource.GADGETBRIDGE,
                confidence=1.0,
                metadata=raw.metadata,
            )
            normalized.append(sample)
            if raw.metric_type not in metrics_available:
                metrics_available.append(raw.metric_type)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "normalize_gadgetbridge_sample_failed",
                metric=raw.metric_type.value if hasattr(raw.metric_type, "value") else str(raw.metric_type),
                error=str(exc),
            )

    return HealthMetricPayload(
        sync_timestamp=datetime.now(timezone.utc),
        device_id=device_id,
        owner_id=owner_id,
        source=MetricSource.GADGETBRIDGE,
        samples=normalized,
        metrics_available=metrics_available,
        metrics_unavailable=[],
    )

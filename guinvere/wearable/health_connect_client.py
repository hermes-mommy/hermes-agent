"""Health Connect JSON export parser for wearable health data.

Parses JSON files produced by the Kotlin ``HealthConnectExport`` Android
app, flattening per-metric records into a uniform stream of
:class:`HealthConnectRawSample` instances keyed off ``start_time`` so
downstream normalizers can treat Health Connect and Gadgetbridge exports
uniformly. Pure sync; the parser never raises from a per-record path --
malformed records are logged and skipped.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from structlog.stdlib import BoundLogger

from guinvere.wearable.errors import (
    HealthConnectFileNotFoundError,
    HealthConnectParseError,
)
from guinvere.wearable.models import MetricSource

logger: BoundLogger = structlog.get_logger(__name__)

_METRIC_KEYS: tuple[str, ...] = (
    "heart_rate", "steps", "spo2", "sleep", "active_calories",
)


@dataclass(slots=True, frozen=True)
class HealthConnectRawSample:
    """A single raw sample extracted from a Health Connect JSON export.

    For metrics whose source record carries a window (``start_time`` /
    ``end_time``) both timestamps are preserved; for instantaneous metrics
    such as SpO2, ``end_time`` is ``None``.
    """

    metric_type: str
    start_time: datetime
    end_time: datetime | None
    value: float
    unit: str
    device_manufacturer: str = ""
    device_model: str = ""
    data_origin: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class HealthConnectParseResult:
    """Result of parsing a Health Connect JSON export file."""

    samples: tuple[HealthConnectRawSample, ...]
    export_timestamp: datetime
    device_manufacturer: str
    device_model: str
    sdk_version: str
    source: MetricSource = MetricSource.HEALTH_CONNECT


def parse_health_connect_export(
    json_path: str | Path, since: datetime | None = None
) -> HealthConnectParseResult:
    """Parse a Health Connect JSON export file.

    ``since`` filters samples to those whose ``start_time`` is on or after
    the cutoff (inclusive); ``None`` returns all samples. Raises
    :class:`HealthConnectFileNotFoundError` if the file is missing, or
    :class:`HealthConnectParseError` if the file is not valid JSON or is
    missing the top-level ``records`` key.
    """
    path = Path(json_path)
    if not path.is_file():
        raise HealthConnectFileNotFoundError(
            f"Health Connect JSON export not found at {path}", metric=None
        )
    file_size = path.stat().st_size
    logger.info(
        "health_connect_file_loaded",
        path=str(path),
        file_size_bytes=file_size,
        since=since.isoformat() if since is not None else None,
    )

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HealthConnectParseError(
            f"Could not read Health Connect export at {path}: {exc}", metric=None
        ) from exc
    try:
        payload: object = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HealthConnectParseError(
            f"Health Connect export at {path} is not valid JSON: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})",
            metric=None,
        ) from exc
    if not isinstance(payload, dict):
        raise HealthConnectParseError(
            f"Health Connect export at {path} must be a JSON object, "
            f"got {type(payload).__name__}",
            metric=None,
        )
    records_obj = payload.get("records")
    if not isinstance(records_obj, dict):
        raise HealthConnectParseError(
            f"Health Connect export at {path} is missing required key "
            f"'records' or it is not a JSON object",
            metric=None,
        )

    source_info = _extract_source_info(payload)
    samples = _parse_all_records(records_obj, source_info, since)
    export_ts = _coerce_export_timestamp(payload.get("export_timestamp"))
    result = HealthConnectParseResult(
        samples=tuple(samples),
        export_timestamp=export_ts,
        device_manufacturer=source_info["device_manufacturer"],
        device_model=source_info["device_model"],
        sdk_version=source_info["sdk_version"],
    )
    logger.info(
        "health_connect_parse_complete",
        path=str(path),
        total_samples=len(result.samples),
        export_timestamp=result.export_timestamp.isoformat(),
    )
    return result


def _extract_source_info(payload: dict[str, object]) -> dict[str, str]:
    """Pull the top-level device + SDK metadata out of the export payload."""
    device_obj = payload.get("device")
    manufacturer = model = ""
    if isinstance(device_obj, dict):
        raw = device_obj.get("manufacturer")
        if isinstance(raw, str):
            manufacturer = raw
        raw = device_obj.get("model")
        if isinstance(raw, str):
            model = raw
    raw_sdk = payload.get("sdk_version")
    raw_origin = payload.get("data_origin")
    return {
        "device_manufacturer": manufacturer,
        "device_model": model,
        "sdk_version": raw_sdk if isinstance(raw_sdk, str) else "",
        "data_origin": raw_origin if isinstance(raw_origin, str) else "",
    }


def _coerce_export_timestamp(value: object) -> datetime:
    """Best-effort coercion of the top-level export timestamp."""
    parsed = _parse_iso_timestamp(value)
    return parsed if parsed is not None else datetime.now(timezone.utc)


def _parse_all_records(
    records_obj: dict[str, object],
    source_info: dict[str, str],
    since: datetime | None,
) -> list[HealthConnectRawSample]:
    """Dispatch every per-metric record list through its type-specific parser."""
    dispatch = {
        "heart_rate": _parse_heart_rate,
        "steps": _parse_steps,
        "spo2": _parse_spo2,
        "sleep": _parse_sleep,
        "active_calories": _parse_active_calories,
    }
    samples: list[HealthConnectRawSample] = []
    for metric_type, parser in dispatch.items():
        raw_records = records_obj.get(metric_type)
        if raw_records is None:
            continue
        if not isinstance(raw_records, list):
            logger.warning(
                "health_connect_records_invalid_shape",
                metric_type=metric_type,
                expected="list",
                actual=type(raw_records).__name__,
            )
            continue
        parsed = parser(raw_records, source_info)
        filtered = _filter_since(parsed, since)
        samples.extend(filtered)
        logger.info(
            "health_connect_records_parsed",
            metric_type=metric_type,
            parsed=len(parsed),
            kept=len(filtered),
        )
    return samples


def _filter_since(
    samples: list[HealthConnectRawSample], since: datetime | None
) -> list[HealthConnectRawSample]:
    """Drop samples whose ``start_time`` is strictly before ``since``."""
    if since is None:
        return samples
    return [s for s in samples if s.start_time >= since]


def _parse_iso_timestamp(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp produced by Kotlin ``Instant.toString``.

    Handles both ``2024-01-15T10:30:00Z`` and ``2024-01-15T10:30:00.000Z``.
    """
    if not isinstance(value, str):
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _safe_float(value: object) -> float | None:
    """Best-effort float coercion; returns ``None`` on failure or null input."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _skip_record(metric_type: str, index: int, reason: str, **extra: Any) -> None:
    """Emit a structured warning for a skipped record."""
    logger.warning(
        "health_connect_record_skipped", metric_type=metric_type, index=index,
        reason=reason, **extra,
    )


def _skip_sample(
    metric_type: str, record_index: int, sample_index: int, reason: str
) -> None:
    """Emit a structured warning for a skipped inner sample."""
    logger.warning(
        "health_connect_sample_skipped",
        metric_type=metric_type,
        record_index=record_index,
        sample_index=sample_index,
        reason=reason,
    )


def _resolve_record_context(
    record: dict[str, object], source_info: dict[str, str]
) -> tuple[str, str, str, dict[str, object]]:
    """Resolve per-record device + metadata, falling back to the export-level info."""
    manufacturer = source_info["device_manufacturer"]
    model = source_info["device_model"]
    data_origin = source_info["data_origin"]
    metadata: dict[str, object] = {}
    raw_metadata = record.get("metadata")
    if isinstance(raw_metadata, dict):
        metadata = dict(raw_metadata)
        raw = raw_metadata.get("dataOrigin")
        if isinstance(raw, str) and raw:
            data_origin = raw
        raw_device = raw_metadata.get("device")
        if isinstance(raw_device, dict):
            raw = raw_device.get("manufacturer")
            if isinstance(raw, str) and raw:
                manufacturer = raw
            raw = raw_device.get("model")
            if isinstance(raw, str) and raw:
                model = raw
    return manufacturer, model, data_origin, metadata


def _parse_heart_rate(
    records: list[object], source_info: dict[str, str]
) -> list[HealthConnectRawSample]:
    """Flatten heart-rate records; each nested ``samples`` entry becomes a sample."""
    samples: list[HealthConnectRawSample] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _skip_record("heart_rate", index, "not_a_dict")
            continue
        start_time = _parse_iso_timestamp(record.get("start_time"))
        end_time = _parse_iso_timestamp(record.get("end_time"))
        if start_time is None:
            _skip_record("heart_rate", index, "missing_or_invalid_start_time")
            continue
        raw_samples = record.get("samples")
        if not isinstance(raw_samples, list):
            _skip_record("heart_rate", index, "samples_missing")
            continue
        mfr, mdl, origin, metadata = _resolve_record_context(record, source_info)
        for sample_index, raw in enumerate(raw_samples):
            if not isinstance(raw, dict):
                _skip_sample("heart_rate", index, sample_index, "not_a_dict")
                continue
            sample_time = _parse_iso_timestamp(raw.get("time")) or start_time
            bpm = _safe_float(raw.get("bpm"))
            if bpm is None:
                _skip_sample("heart_rate", index, sample_index, "invalid_bpm")
                continue
            samples.append(
                HealthConnectRawSample(
                    metric_type="heart_rate", start_time=sample_time,
                    end_time=end_time, value=bpm, unit="bpm",
                    device_manufacturer=mfr, device_model=mdl,
                    data_origin=origin, metadata=metadata,
                )
            )
    return samples


def _parse_steps(
    records: list[object], source_info: dict[str, str]
) -> list[HealthConnectRawSample]:
    """Parse step-count records (one sample per record)."""
    return _parse_window_metrics(records, source_info, "steps", "count", "count")


def _parse_spo2(
    records: list[object], source_info: dict[str, str]
) -> list[HealthConnectRawSample]:
    """Parse SpO2 records; each is instantaneous (``end_time`` is ``None``)."""
    samples: list[HealthConnectRawSample] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _skip_record("spo2", index, "not_a_dict")
            continue
        timestamp = _parse_iso_timestamp(record.get("time"))
        if timestamp is None:
            _skip_record("spo2", index, "missing_or_invalid_time")
            continue
        percentage = _safe_float(record.get("percentage"))
        if percentage is None:
            _skip_record("spo2", index, "invalid_percentage")
            continue
        mfr, mdl, origin, metadata = _resolve_record_context(record, source_info)
        samples.append(
            HealthConnectRawSample(
                metric_type="spo2", start_time=timestamp, end_time=None,
                value=percentage, unit="%", device_manufacturer=mfr,
                device_model=mdl, data_origin=origin, metadata=metadata,
            )
        )
    return samples


def _parse_sleep(
    records: list[object], source_info: dict[str, str]
) -> list[HealthConnectRawSample]:
    """Parse sleep records; each nested ``stages`` entry becomes a sample."""
    samples: list[HealthConnectRawSample] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _skip_record("sleep", index, "not_a_dict")
            continue
        mfr, mdl, origin, metadata = _resolve_record_context(record, source_info)
        raw_stages = record.get("stages")
        if not isinstance(raw_stages, list):
            _skip_record("sleep", index, "stages_missing")
            continue
        for stage_index, raw in enumerate(raw_stages):
            if not isinstance(raw, dict):
                _skip_sample("sleep", index, stage_index, "not_a_dict")
                continue
            stage_start = _parse_iso_timestamp(raw.get("start"))
            stage_value = _safe_float(raw.get("stage"))
            if stage_start is None or stage_value is None:
                _skip_sample("sleep", index, stage_index, "invalid_stage")
                continue
            stage_end = _parse_iso_timestamp(raw.get("end"))
            stage_meta = dict(metadata)
            stage_meta["sleep_stage_code"] = int(stage_value)
            samples.append(
                HealthConnectRawSample(
                    metric_type="sleep", start_time=stage_start, end_time=stage_end,
                    value=stage_value, unit="stage", device_manufacturer=mfr,
                    device_model=mdl, data_origin=origin, metadata=stage_meta,
                )
            )
    return samples


def _parse_active_calories(
    records: list[object], source_info: dict[str, str]
) -> list[HealthConnectRawSample]:
    """Parse active-calories records (one sample per record)."""
    return _parse_window_metrics(
        records, source_info, "active_calories", "kilocalories", "kcal"
    )


def _parse_window_metrics(
    records: list[object],
    source_info: dict[str, str],
    metric_type: str,
    value_key: str,
    unit: str,
) -> list[HealthConnectRawSample]:
    """Build samples for metrics whose record carries ``start_time``/``end_time``+value."""
    samples: list[HealthConnectRawSample] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _skip_record(metric_type, index, "not_a_dict")
            continue
        start_time = _parse_iso_timestamp(record.get("start_time"))
        if start_time is None:
            _skip_record(metric_type, index, "missing_or_invalid_start_time")
            continue
        end_time = _parse_iso_timestamp(record.get("end_time"))
        value = _safe_float(record.get(value_key))
        if value is None:
            _skip_record(metric_type, index, f"invalid_{value_key}")
            continue
        mfr, mdl, origin, metadata = _resolve_record_context(record, source_info)
        samples.append(
            HealthConnectRawSample(
                metric_type=metric_type, start_time=start_time, end_time=end_time,
                value=value, unit=unit, device_manufacturer=mfr, device_model=mdl,
                data_origin=origin, metadata=metadata,
            )
        )
    return samples

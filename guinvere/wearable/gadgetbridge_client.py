"""Gadgetbridge SQLite database parser for wearable health data.

Parses the Gadgetbridge SQLite export file to extract health metrics.
The database is named 'Gadgetbridge' (no extension) and contains
Huami/Xiaomi wearable data in proprietary table schemas. Tables are
heterogeneous: older tables (MI_BAND_ACTIVITY_SAMPLE) record timestamps
in seconds while newer Huami tables use milliseconds. This module
introspects each table to detect the timestamp unit and the actual
column set before extracting samples.

Pure sync functions — no async, no side effects, no network calls.
The parser never raises from a per-table parse path: failures are
recorded as warnings and the caller receives a best-effort result.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import structlog
from structlog.stdlib import BoundLogger

from guinvere.wearable.errors import (
    GadgetbridgeEmptyExportError,
    GadgetbridgeFileNotFoundError,
    GadgetbridgeSchemaMismatchError,
    SQLiteParseError,
)
from guinvere.wearable.models import HealthMetricType

logger: BoundLogger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Threshold separating seconds-since-epoch from milliseconds-since-epoch.
# Seconds from 2001 to 2286 stay below 10^10; milliseconds since 1970
# comfortably exceed 10^12 for any modern Gadgetbridge export.
_TIMESTAMP_THRESHOLD = 1_000_000_000_000

# Huami / Mi Band RAW_KIND codes that denote a sleep-related sample.
# 112 = light sleep start, 120 = light sleep, 121 = deep sleep,
# 122 = REM sleep, 249 = awake (during a sleep tracking window).
_SLEEP_RAW_KINDS: frozenset[int] = frozenset({112, 120, 121, 122, 249})

# Maps RAW_KIND codes to a human-readable stage label for sample metadata.
_SLEEP_KIND_MAP: dict[int, str] = {
    112: "light_sleep_start",
    120: "light_sleep",
    121: "deep_sleep",
    122: "rem_sleep",
    249: "awake",
}

# Known Gadgetbridge table name prefixes and the metric they map to.
# A value of None means "known but not a standard HealthMetricType";
# such tables are introspected and logged but emit no samples.
_KNOWN_TABLE_PATTERNS: dict[str, HealthMetricType | None] = {
    "MI_BAND_ACTIVITY_SAMPLE": HealthMetricType.ACTIVITY,
    "HUAMI_HEART_RATE": HealthMetricType.HEART_RATE,
    "HUAMI_SPO2_SAMPLE": HealthMetricType.SPO2,
    "HUAMI_STRESS_SAMPLE": HealthMetricType.STRESS,
    "HUAMI_EXTENDED_ACTIVITY_SAMPLE": HealthMetricType.ACTIVITY,
    "HUAMI_PAI_SAMPLE": None,
}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GadgetbridgeRawSample:
    """A single raw sample extracted from a Gadgetbridge table.

    The sample preserves the source shape so downstream normalizers can
    decide how to convert it into a NormalizedHealthSample (Pydantic).
    """

    metric_type: HealthMetricType
    timestamp: datetime
    value: float
    unit: str
    raw_kind: int | None = None  # Activity table sleep decoding
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class GadgetbridgeParseResult:
    """Result of parsing a Gadgetbridge SQLite export."""

    timestamp: datetime  # Parse completion time
    device_id: str
    samples: list[GadgetbridgeRawSample] = field(default_factory=list)
    tables_found: list[str] = field(default_factory=list)
    tables_parsed: list[str] = field(default_factory=list)
    metrics_available: list[HealthMetricType] = field(default_factory=list)
    metrics_unavailable: list[HealthMetricType] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_gadgetbridge_db(
    db_path: str | Path,
    device_id: str = "",
    since: datetime | None = None,
) -> GadgetbridgeParseResult:
    """Parse a Gadgetbridge SQLite export file.

    Args:
        db_path: Path to the Gadgetbridge SQLite file (typically ``Gadgetbridge``).
        device_id: Device identifier to tag samples with.
        since: Only return samples at or after this timestamp (UTC, inclusive).

    Returns:
        GadgetbridgeParseResult with extracted samples, discovered tables,
        and per-metric availability.

    Raises:
        GadgetbridgeFileNotFoundError: If the file does not exist.
        SQLiteParseError: If the file cannot be opened as a SQLite database.
        GadgetbridgeSchemaMismatchError: If no recognized tables are present.
        GadgetbridgeEmptyExportError: If recognized tables exist but contain
            no rows.
    """
    path = Path(db_path)
    if not path.is_file():
        raise GadgetbridgeFileNotFoundError(
            f"Gadgetbridge database not found at {path}",
            metric=None,
        )

    logger.info(
        "gadgetbridge_parse_started",
        db_path=str(path),
        device_id=device_id,
        since=since.isoformat() if since is not None else None,
    )

    try:
        conn = sqlite3.connect(str(path))
    except sqlite3.OperationalError as exc:
        logger.error("gadgetbridge_open_failed", db_path=str(path), error=str(exc))
        raise SQLiteParseError(
            f"Could not open {path} as a SQLite database: {exc}",
            metric=None,
        ) from exc

    try:
        tables = _introspect_tables(conn)
        matched = _match_known_tables(tables)
        logger.info(
            "gadgetbridge_tables_discovered",
            count=len(tables),
            names=tables,
            matched=list(matched.keys()),
        )

        if not matched:
            raise GadgetbridgeSchemaMismatchError(
                f"No recognized Gadgetbridge tables found in {path}. "
                f"Discovered tables: {tables}",
                metric=None,
            )

        result = GadgetbridgeParseResult(
            timestamp=datetime.now(timezone.utc),
            device_id=device_id,
            tables_found=list(matched.keys()),
        )

        for table_name, metric_type in matched.items():
            _dispatch_table(
                conn=conn,
                table_name=table_name,
                metric_type=metric_type,
                since=since,
                result=result,
            )

        if not result.tables_parsed:
            raise GadgetbridgeEmptyExportError(
                f"Gadgetbridge export at {path} has recognized tables "
                f"but none returned rows",
                metric=None,
            )

        _finalize_metrics(result)

        logger.info(
            "gadgetbridge_parse_completed",
            db_path=str(path),
            total_samples=len(result.samples),
            metrics_available=[m.value for m in result.metrics_available],
            metrics_unavailable=[m.value for m in result.metrics_unavailable],
            warnings=len(result.warnings),
        )
        return result
    finally:
        try:
            conn.close()
        except sqlite3.OperationalError as exc:
            logger.warning("gadgetbridge_close_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Introspection helpers
# ---------------------------------------------------------------------------


def _introspect_tables(conn: sqlite3.Connection) -> list[str]:
    """Query ``sqlite_master`` for the list of user tables."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [row[0] for row in cursor.fetchall()]


def _match_known_tables(
    tables: list[str],
) -> dict[str, HealthMetricType | None]:
    """Match discovered tables against the known Gadgetbridge patterns.

    Returns a dict keyed by the discovered table name (preserving
    ``sqlite_master`` casing) with the metric type it maps to.
    """
    matched: dict[str, HealthMetricType | None] = {}
    for table in tables:
        upper = table.upper()
        for pattern, metric in _KNOWN_TABLE_PATTERNS.items():
            if upper.startswith(pattern):
                matched[table] = metric
                break
    return matched


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return the set of column names for ``table``."""
    cursor = conn.execute(f'PRAGMA table_info("{_safe_identifier(table)}")')
    return {row[1] for row in cursor.fetchall()}


def _safe_identifier(name: str) -> str:
    """Escape a SQLite identifier (table or column name) for safe interpolation."""
    return name.replace('"', '""')


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------


def _detect_timestamp_unit(raw_ts: int | float) -> str:
    """Detect whether a timestamp is seconds-since-epoch or milliseconds.

    Gadgetbridge tables are heterogeneous: MI_BAND_ACTIVITY_SAMPLE uses
    seconds; HUAMI_* tables use milliseconds. The 10^12 threshold cleanly
    separates the two because milliseconds since 1970 are always > 10^12
    for any realistic wearable export, while seconds-since-epoch stay
    well below that for any value < year 2286.
    """
    if abs(float(raw_ts)) > _TIMESTAMP_THRESHOLD:
        return "ms"
    return "s"


def _normalize_timestamp(raw_ts: int | float) -> datetime:
    """Convert a raw Gadgetbridge timestamp to a UTC ``datetime``."""
    unit = _detect_timestamp_unit(raw_ts)
    if unit == "ms":
        return datetime.fromtimestamp(float(raw_ts) / 1000.0, tz=timezone.utc)
    return datetime.fromtimestamp(float(raw_ts), tz=timezone.utc)


def _is_sleep_sample(raw_kind: int | None) -> bool:
    """Return ``True`` if ``raw_kind`` encodes a sleep-related stage."""
    return raw_kind is not None and raw_kind in _SLEEP_RAW_KINDS


def _passes_since_filter(
    ts: datetime,
    since: datetime | None,
) -> bool:
    """Return ``True`` if ``ts`` is on or after the ``since`` cutoff."""
    if since is None:
        return True
    return ts >= since


# ---------------------------------------------------------------------------
# Per-table dispatch
# ---------------------------------------------------------------------------


def _dispatch_table(
    conn: sqlite3.Connection,
    table_name: str,
    metric_type: HealthMetricType | None,
    since: datetime | None,
    result: GadgetbridgeParseResult,
) -> None:
    """Run the appropriate per-table parser, catching all failures."""
    upper = table_name.upper()
    try:
        if upper.startswith("MI_BAND_ACTIVITY_SAMPLE"):
            samples = _parse_activity_table(conn, table_name, since)
        elif upper.startswith("HUAMI_HEART_RATE"):
            samples = _parse_heart_rate_table(conn, table_name, since)
        elif upper.startswith("HUAMI_SPO2_SAMPLE"):
            samples = _parse_spo2_table(conn, table_name, since)
        elif upper.startswith("HUAMI_STRESS_SAMPLE"):
            samples = _parse_stress_table(conn, table_name, since)
        elif upper.startswith("HUAMI_EXTENDED_ACTIVITY_SAMPLE"):
            samples = _parse_extended_activity_table(conn, table_name, since)
        elif upper.startswith("HUAMI_PAI_SAMPLE"):
            _log_pai_summary(conn, table_name)
            return
        else:
            # Matched by _match_known_tables but no dispatcher — defensive.
            result.warnings.append(f"No parser for matched table {table_name}")
            logger.warning(
                "gadgetbridge_table_dispatcher_missing",
                table=table_name,
            )
            return
    except sqlite3.DatabaseError as exc:
        warning = f"Failed to parse table {table_name}: {exc}"
        result.warnings.append(warning)
        logger.warning(
            "gadgetbridge_table_parse_failed",
            table=table_name,
            error=str(exc),
        )
        return
    except (KeyError, TypeError, ValueError) as exc:
        warning = f"Unexpected shape in table {table_name}: {exc}"
        result.warnings.append(warning)
        logger.warning(
            "gadgetbridge_table_parse_failed",
            table=table_name,
            error=str(exc),
        )
        return

    if samples:
        result.samples.extend(samples)
        result.tables_parsed.append(table_name)
        logger.info(
            "gadgetbridge_table_parsed",
            table=table_name,
            sample_count=len(samples),
        )
    else:
        # Empty result is not an error — just note it and move on.
        logger.info("gadgetbridge_table_empty", table=table_name)


def _log_pai_summary(conn: sqlite3.Connection, table_name: str) -> None:
    """Log a PAI table's row count without emitting standard samples.

    PAI (Personal Activity Intelligence) is not represented in
    ``HealthMetricType``; we record its presence for diagnostics only.
    """
    try:
        cursor = conn.execute(f'SELECT COUNT(*) FROM "{_safe_identifier(table_name)}"')
        row_count = int(cursor.fetchone()[0])
    except sqlite3.DatabaseError as exc:
        logger.warning(
            "gadgetbridge_table_parse_failed",
            table=table_name,
            error=str(exc),
        )
        return
    logger.info(
        "gadgetbridge_table_logged_no_metric",
        table=table_name,
        row_count=row_count,
        reason="PAI is not a standard HealthMetricType",
    )


# ---------------------------------------------------------------------------
# Activity table parser (MI_BAND_ACTIVITY_SAMPLE)
# ---------------------------------------------------------------------------


def _parse_activity_table(
    conn: sqlite3.Connection,
    table: str,
    since: datetime | None,
) -> list[GadgetbridgeRawSample]:
    """Parse ``MI_BAND_ACTIVITY_SAMPLE`` rows.

    A single row may encode one or more of: sleep stage, step count,
    heart rate sample, or activity intensity. We emit a sample per
    non-zero measurement to preserve the multi-metric nature of the
    source row.
    """
    columns = _table_columns(conn, table)
    required = {"TIMESTAMP"}
    if not required.issubset(columns):
        logger.warning(
            "gadgetbridge_activity_missing_columns",
            table=table,
            required=sorted(required),
            present=sorted(columns),
        )
        return []

    samples: list[GadgetbridgeRawSample] = []
    cursor = conn.execute(f'SELECT * FROM "{_safe_identifier(table)}"')
    row: sqlite3.Row
    for row in cursor:
        sample = _row_to_activity_sample(row, columns, since)
        if sample is not None:
            samples.extend(sample)
    return samples


def _row_to_activity_sample(
    row: sqlite3.Row,
    columns: set[str],
    since: datetime | None,
) -> list[GadgetbridgeRawSample] | None:
    """Convert one activity row to zero or more raw samples."""
    raw_ts = row["TIMESTAMP"]
    if raw_ts is None:
        return None
    try:
        timestamp = _normalize_timestamp(int(raw_ts))
    except (TypeError, ValueError, OSError, OverflowError):
        return None
    if not _passes_since_filter(timestamp, since):
        return None

    raw_kind = _safe_int(row["RAW_KIND"]) if "RAW_KIND" in columns else None
    samples: list[GadgetbridgeRawSample] = []

    if _is_sleep_sample(raw_kind):
        # Each activity row is a one-minute window; emit 1 minute per sleep sample.
        kind_label = _SLEEP_KIND_MAP.get(raw_kind or 0, "unknown") if raw_kind is not None else "unknown"
        samples.append(
            GadgetbridgeRawSample(
                metric_type=HealthMetricType.SLEEP,
                timestamp=timestamp,
                value=1.0,
                unit="minutes",
                raw_kind=raw_kind,
                metadata={"stage": kind_label},
            )
        )
        return samples

    if "STEPS" in columns:
        steps = _safe_float(row["STEPS"])
        if steps is not None and steps > 0:
            samples.append(
                GadgetbridgeRawSample(
                    metric_type=HealthMetricType.STEPS,
                    timestamp=timestamp,
                    value=steps,
                    unit="steps",
                )
            )

    if "HEART_RATE" in columns:
        hr = _safe_float(row["HEART_RATE"])
        if hr is not None and hr > 0:
            samples.append(
                GadgetbridgeRawSample(
                    metric_type=HealthMetricType.HEART_RATE,
                    timestamp=timestamp,
                    value=hr,
                    unit="bpm",
                )
            )

    if "RAW_INTENSITY" in columns:
        intensity = _safe_float(row["RAW_INTENSITY"])
        if intensity is not None and intensity > 0:
            samples.append(
                GadgetbridgeRawSample(
                    metric_type=HealthMetricType.ACTIVITY,
                    timestamp=timestamp,
                    value=intensity,
                    unit="intensity",
                )
            )

    return samples or None


# ---------------------------------------------------------------------------
# Heart rate, SpO2, stress parsers
# ---------------------------------------------------------------------------


def _parse_heart_rate_table(
    conn: sqlite3.Connection,
    table: str,
    since: datetime | None,
) -> list[GadgetbridgeRawSample]:
    """Parse ``HUAMI_HEART_RATE`` (and ``HUAMI_HEART_RATE_AUTO/MANUAL``)."""
    columns = _table_columns(conn, table)
    if "TIMESTAMP" not in columns or "HEART_RATE" not in columns:
        logger.warning(
            "gadgetbridge_heart_rate_missing_columns",
            table=table,
            present=sorted(columns),
        )
        return []
    return _generic_metric_table(
        conn=conn,
        table=table,
        since=since,
        metric_type=HealthMetricType.HEART_RATE,
        timestamp_col="TIMESTAMP",
        value_col="HEART_RATE",
        unit="bpm",
    )


def _parse_spo2_table(
    conn: sqlite3.Connection,
    table: str,
    since: datetime | None,
) -> list[GadgetbridgeRawSample]:
    """Parse ``HUAMI_SPO2_SAMPLE``."""
    columns = _table_columns(conn, table)
    if "TIMESTAMP" not in columns or "SPO2" not in columns:
        logger.warning(
            "gadgetbridge_spo2_missing_columns",
            table=table,
            present=sorted(columns),
        )
        return []
    return _generic_metric_table(
        conn=conn,
        table=table,
        since=since,
        metric_type=HealthMetricType.SPO2,
        timestamp_col="TIMESTAMP",
        value_col="SPO2",
        unit="%",
    )


def _parse_stress_table(
    conn: sqlite3.Connection,
    table: str,
    since: datetime | None,
) -> list[GadgetbridgeRawSample]:
    """Parse ``HUAMI_STRESS_SAMPLE``."""
    columns = _table_columns(conn, table)
    if "TIMESTAMP" not in columns or "STRESS" not in columns:
        logger.warning(
            "gadgetbridge_stress_missing_columns",
            table=table,
            present=sorted(columns),
        )
        return []
    return _generic_metric_table(
        conn=conn,
        table=table,
        since=since,
        metric_type=HealthMetricType.STRESS,
        timestamp_col="TIMESTAMP",
        value_col="STRESS",
        unit="score",
    )


def _parse_extended_activity_table(
    conn: sqlite3.Connection,
    table: str,
    since: datetime | None,
) -> list[GadgetbridgeRawSample]:
    """Parse ``HUAMI_EXTENDED_ACTIVITY_SAMPLE``.

    Emits a STEPS sample per row. Other columns (DISTANCE, CALORIES)
    are out of scope for ``HealthMetricType`` but are preserved in
    metadata when present.
    """
    columns = _table_columns(conn, table)
    if "TIMESTAMP" not in columns or "STEPS" not in columns:
        logger.warning(
            "gadgetbridge_extended_activity_missing_columns",
            table=table,
            present=sorted(columns),
        )
        return []

    samples: list[GadgetbridgeRawSample] = []
    cursor = conn.execute(f'SELECT * FROM "{_safe_identifier(table)}"')
    for row in cursor:
        raw_ts = row["TIMESTAMP"]
        if raw_ts is None:
            continue
        try:
            timestamp = _normalize_timestamp(int(raw_ts))
        except (TypeError, ValueError, OSError, OverflowError):
            continue
        if not _passes_since_filter(timestamp, since):
            continue

        steps = _safe_float(row["STEPS"])
        if steps is None or steps <= 0:
            continue

        metadata: dict[str, str] = {}
        distance = _safe_float(row["DISTANCE"]) if "DISTANCE" in columns else None
        if distance is not None:
            metadata["distance"] = f"{distance}"
        calories = _safe_float(row["CALORIES"]) if "CALORIES" in columns else None
        if calories is not None:
            metadata["calories"] = f"{calories}"

        samples.append(
            GadgetbridgeRawSample(
                metric_type=HealthMetricType.STEPS,
                timestamp=timestamp,
                value=steps,
                unit="steps",
                metadata=metadata,
            )
        )
    return samples


# ---------------------------------------------------------------------------
# Generic metric-table helper
# ---------------------------------------------------------------------------


def _generic_metric_table(
    conn: sqlite3.Connection,
    table: str,
    since: datetime | None,
    metric_type: HealthMetricType,
    timestamp_col: str,
    value_col: str,
    unit: str,
) -> list[GadgetbridgeRawSample]:
    """Parse a simple (TIMESTAMP, value_col) table into raw samples."""
    samples: list[GadgetbridgeRawSample] = []
    safe_table = _safe_identifier(table)
    cursor = conn.execute(
        f'SELECT "{_safe_identifier(timestamp_col)}", '
        f'"{_safe_identifier(value_col)}" FROM "{safe_table}"'
    )
    for raw_ts, raw_value in cursor:
        if raw_ts is None or raw_value is None:
            continue
        try:
            timestamp = _normalize_timestamp(int(raw_ts))
        except (TypeError, ValueError, OSError, OverflowError):
            continue
        if not _passes_since_filter(timestamp, since):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        samples.append(
            GadgetbridgeRawSample(
                metric_type=metric_type,
                timestamp=timestamp,
                value=value,
                unit=unit,
            )
        )
    return samples


# ---------------------------------------------------------------------------
# Finalization helpers
# ---------------------------------------------------------------------------


def _finalize_metrics(result: GadgetbridgeParseResult) -> None:
    """Populate metrics_available / metrics_unavailable on ``result``."""
    all_metrics = list(HealthMetricType)
    seen: set[HealthMetricType] = {sample.metric_type for sample in result.samples}
    result.metrics_available = sorted(seen, key=lambda m: m.value)
    result.metrics_unavailable = sorted(
        (m for m in all_metrics if m not in seen),
        key=lambda m: m.value,
    )


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------


def _safe_int(value: object) -> int | None:
    """Best-effort int coercion; returns ``None`` on failure or null input."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: object) -> float | None:
    """Best-effort float coercion; returns ``None`` on failure or null input."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

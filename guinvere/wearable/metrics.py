"""Wearable Health Observability — Prometheus metrics for the health pipeline.

P14-015: Exposes Prometheus metric families for the wearable health pipeline,
enabling Grafana dashboarding and alerting.

Metric families
---------------
- ``guinevere_wearable_sync_total{status}`` — counter of sync runs by status.
- ``guinevere_wearable_sync_duration_seconds`` — histogram of sync duration.
- ``guinevere_wearable_metrics_ingested_total{metric_type}`` — counter of metrics written.
- ``guinevere_wearable_metrics_dropped_total{reason}`` — counter of metrics dropped.
- ``guinevere_wearable_api_latency_seconds{endpoint}`` — histogram of API latency.
- ``guinevere_wearable_api_errors_total{error_type}`` — counter of API errors.
- ``guinevere_wearable_ghi_score`` — gauge of latest GHI score.
- ``guinevere_wearable_ghi_tier`` — gauge of latest GHI tier (1=excellent..5=critical).
- ``guinevere_wearable_anomalies_total{severity}`` — counter of anomaly events.
- ``guinevere_wearable_alerts_sent_total{severity}`` — counter of alerts dispatched.
- ``guinevere_wearable_baseline_stage{metric_type}`` — gauge of baseline warmup stage.
- ``guinevere_wearable_consent_checks_total{result}`` — counter of consent gate checks.

Naming convention
-----------------
Follows the ``guinevere_`` prefix established by ``src/core/main.py``.
The ``wearable_`` sub-prefix isolates health pipeline metrics.
"""

from __future__ import annotations

import structlog
from prometheus_client import Counter, Gauge, Histogram

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Sync metrics
# ---------------------------------------------------------------------------

SYNC_TOTAL = Counter(
    "guinevere_wearable_sync_total",
    "Total wearable sync runs by status",
    ["status"],
)

SYNC_DURATION_SECONDS = Histogram(
    "guinevere_wearable_sync_duration_seconds",
    "Duration of wearable sync runs in seconds",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

# ---------------------------------------------------------------------------
# Ingestion metrics
# ---------------------------------------------------------------------------

METRICS_INGESTED_TOTAL = Counter(
    "guinevere_wearable_metrics_ingested_total",
    "Total health metrics written to TimescaleDB by metric type",
    ["metric_type"],
)

METRICS_DROPPED_TOTAL = Counter(
    "guinevere_wearable_metrics_dropped_total",
    "Total health metrics dropped by reason",
    ["reason"],
)

# ---------------------------------------------------------------------------
# API metrics
# ---------------------------------------------------------------------------

API_LATENCY_SECONDS = Histogram(
    "guinevere_wearable_api_latency_seconds",
    "Latency of Mi Fitness Cloud API calls in seconds",
    ["endpoint"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

API_ERRORS_TOTAL = Counter(
    "guinevere_wearable_api_errors_total",
    "Total Mi Fitness Cloud API errors by error type",
    ["error_type"],
)

# ---------------------------------------------------------------------------
# GHI metrics
# ---------------------------------------------------------------------------

GHI_SCORE = Gauge(
    "guinevere_wearable_ghi_score",
    "Latest Guinevere Health Index score (0-100)",
)

GHI_TIER = Gauge(
    "guinevere_wearable_ghi_tier",
    "Latest GHI tier as numeric (1=excellent, 2=good, 3=fair, 4=poor, 5=critical)",
)

# ---------------------------------------------------------------------------
# Analysis metrics
# ---------------------------------------------------------------------------

ANOMALIES_TOTAL = Counter(
    "guinevere_wearable_anomalies_total",
    "Total anomaly events detected by severity",
    ["severity"],
)

ALERTS_SENT_TOTAL = Counter(
    "guinevere_wearable_alerts_sent_total",
    "Total health alerts dispatched by severity",
    ["severity"],
)

BASELINE_STAGE = Gauge(
    "guinevere_wearable_baseline_stage",
    "Baseline warmup stage per metric type (0=insufficient..4=stable)",
    ["metric_type"],
)

# ---------------------------------------------------------------------------
# Consent metrics
# ---------------------------------------------------------------------------

CONSENT_CHECKS_TOTAL = Counter(
    "guinevere_wearable_consent_checks_total",
    "Total wearable consent gate checks by result",
    ["result"],
)

# ---------------------------------------------------------------------------
# Observer helpers
# ---------------------------------------------------------------------------


def observe_sync_start() -> None:
    """Log sync start event."""
    logger.debug("wearable_sync_start")


def observe_sync_end(status: str, duration: float) -> None:
    """Record sync completion.

    Args:
        status: ``"success"``, ``"failure"``, or ``"timeout"``.
        duration: Sync duration in seconds.
    """
    SYNC_TOTAL.labels(status=status).inc()
    SYNC_DURATION_SECONDS.observe(duration)
    logger.debug("wearable_sync_end", status=status, duration=round(duration, 2))


def observe_metrics_ingested(metric_type: str, count: int = 1) -> None:
    """Increment the metrics-ingested counter.

    Args:
        metric_type: Health metric type (e.g. ``"heart_rate"``, ``"spo2"``).
        count: Number of metrics ingested (default 1).
    """
    METRICS_INGESTED_TOTAL.labels(metric_type=metric_type).inc(count)


def observe_metrics_dropped(reason: str, count: int = 1) -> None:
    """Increment the metrics-dropped counter.

    Args:
        reason: Drop reason (e.g. ``"consent_denied"``, ``"invalid"``, ``"duplicate"``).
        count: Number of metrics dropped (default 1).
    """
    METRICS_DROPPED_TOTAL.labels(reason=reason).inc(count)


def observe_api_latency(endpoint: str, duration: float) -> None:
    """Record API call latency.

    Args:
        endpoint: API endpoint name (e.g. ``"fetch_activity"``, ``"fetch_sleep"``).
        duration: API call duration in seconds.
    """
    API_LATENCY_SECONDS.labels(endpoint=endpoint).observe(duration)


def observe_api_error(error_type: str) -> None:
    """Increment the API error counter.

    Args:
        error_type: Error type (e.g. ``"auth"``, ``"rate_limit"``, ``"circuit_breaker"``).
    """
    API_ERRORS_TOTAL.labels(error_type=error_type).inc()
    logger.warning("wearable_api_error", error_type=error_type)


def observe_ghi(score: float, tier: int) -> None:
    """Record latest GHI score and tier.

    Args:
        score: GHI score (0-100).
        tier: GHI tier as integer (1=excellent, 2=good, 3=fair, 4=poor, 5=critical).
    """
    GHI_SCORE.set(score)
    GHI_TIER.set(tier)
    logger.debug("wearable_ghi_updated", score=round(score, 1), tier=tier)


def observe_anomaly(severity: str) -> None:
    """Increment the anomaly counter.

    Args:
        severity: Anomaly severity (e.g. ``"info"``, ``"warning"``, ``"critical"``).
    """
    ANOMALIES_TOTAL.labels(severity=severity).inc()


def observe_alert_sent(severity: str) -> None:
    """Increment the alerts-sent counter.

    Args:
        severity: Alert severity level.
    """
    ALERTS_SENT_TOTAL.labels(severity=severity).inc()


def observe_baseline_stage(metric_type: str, stage: int) -> None:
    """Set the baseline warmup stage for a metric type.

    Args:
        metric_type: Health metric type.
        stage: Warmup stage (0=insufficient, 1=provisional, 2=stabilizing, 3=stable, 4=rebaseline).
    """
    BASELINE_STAGE.labels(metric_type=metric_type).set(stage)


def observe_consent_check(result: str) -> None:
    """Increment the consent check counter.

    Args:
        result: Check result (``"granted"`` or ``"denied"``).
    """
    CONSENT_CHECKS_TOTAL.labels(result=result).inc()
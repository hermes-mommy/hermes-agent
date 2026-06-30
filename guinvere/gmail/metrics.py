from __future__ import annotations

"""Canonical Gmail Prometheus metrics surface."""

from prometheus_client import Counter, Gauge, Histogram
import structlog

_logger = structlog.get_logger(__name__)


GMAIL_CONNECTED = Gauge(
    "gmail_connected",
    "OAuth connection state: 1=connected, 0=disconnected",
)

GMAIL_EMAILS_RECEIVED_TOTAL = Counter(
    "gmail_emails_received_total",
    "Total emails received since process start",
    ["category"],
)

GMAIL_EMAILS_CLASSIFIED_TOTAL = Counter(
    "gmail_emails_classified_total",
    "Total emails classified since process start",
    ["category", "tier"],
)

GMAIL_EMAILS_NOTIFIED_TOTAL = Counter(
    "gmail_emails_notified_total",
    "Total email notifications sent since process start",
    ["category"],
)

GMAIL_DRAFTS_CREATED_TOTAL = Counter(
    "gmail_drafts_created_total",
    "Total drafts created since process start",
)

GMAIL_DRAFTS_APPROVED_TOTAL = Counter(
    "gmail_drafts_approved_total",
    "Total drafts approved by Faiz since process start",
)

GMAIL_DRAFTS_REJECTED_TOTAL = Counter(
    "gmail_drafts_rejected_total",
    "Total drafts rejected by Faiz since process start",
)

GMAIL_INJECTION_DETECTED_TOTAL = Counter(
    "gmail_injection_detected_total",
    "Total injection attempts detected since process start",
    ["type"],
)

GMAIL_SECRETS_DETECTED_TOTAL = Counter(
    "gmail_secrets_detected_total",
    "Total secrets detected in emails since process start",
    ["secret_type"],
)

GMAIL_API_QUOTA_USAGE = Gauge(
    "gmail_api_quota_usage",
    "Current API quota usage (units/min)",
)

GMAIL_OAUTH_TOKEN_AGE_SECONDS = Gauge(
    "gmail_oauth_token_age_seconds",
    "Age of current OAuth token in seconds",
)

GMAIL_PROCESSING_LATENCY_SECONDS = Histogram(
    "gmail_processing_latency_seconds",
    "Email processing latency",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")),
)

GMAIL_WATCH_ACTIVE = Gauge(
    "gmail_watch_active",
    "Whether Gmail watch/push is active: 1=active, 0=inactive",
)


def set_connected(connected: bool) -> None:
    GMAIL_CONNECTED.set(1 if connected else 0)


def record_email_received(category: str) -> None:
    GMAIL_EMAILS_RECEIVED_TOTAL.labels(category=category).inc()


def record_email_classified(category: str, tier: int) -> None:
    GMAIL_EMAILS_CLASSIFIED_TOTAL.labels(
        category=category, tier=str(tier),
    ).inc()


def record_notification_sent(category: str) -> None:
    GMAIL_EMAILS_NOTIFIED_TOTAL.labels(category=category).inc()


def record_draft_created() -> None:
    GMAIL_DRAFTS_CREATED_TOTAL.inc()


def record_draft_approved() -> None:
    GMAIL_DRAFTS_APPROVED_TOTAL.inc()


def record_draft_rejected() -> None:
    GMAIL_DRAFTS_REJECTED_TOTAL.inc()


def record_injection_detected(injection_type: str) -> None:
    GMAIL_INJECTION_DETECTED_TOTAL.labels(type=injection_type).inc()


def record_secret_detected(secret_type: str) -> None:
    GMAIL_SECRETS_DETECTED_TOTAL.labels(secret_type=secret_type).inc()


def set_quota_usage(units: float) -> None:
    GMAIL_API_QUOTA_USAGE.set(max(units, 0.0))


def set_token_age(seconds: float) -> None:
    GMAIL_OAUTH_TOKEN_AGE_SECONDS.set(max(seconds, 0.0))


def observe_processing_latency(seconds: float) -> None:
    GMAIL_PROCESSING_LATENCY_SECONDS.observe(seconds)


def set_watch_active(active: bool) -> None:
    GMAIL_WATCH_ACTIVE.set(1 if active else 0)


def start_metrics_server(port: int = 9101) -> None:
    """Start the Prometheus metrics HTTP endpoint on *port*.
    Binds to 127.0.0.1 only. Idempotent on same port.
    """
    from prometheus_client import start_http_server
    start_http_server(addr="127.0.0.1", port=port)
    _logger.info("gmail.metrics_server_started", port=port)

from __future__ import annotations

"""P11-021 — Canonical WhatsApp Prometheus metrics surface."""

from prometheus_client import Counter, Gauge, Histogram

DEFAULT_DEVICE = "faiz"

WHATSAPP_CONNECTED = Gauge(
    "whatsapp_connected",
    "WhatsApp connection state: 1=connected, 0=disconnected/reconnecting/failed",
    ["device"],
)
WHATSAPP_SESSION_AGE_SECONDS = Gauge(
    "whatsapp_session_age_seconds",
    "Age of current WhatsApp session in seconds",
    ["device"],
)
WHATSAPP_MESSAGES_RECEIVED_TOTAL = Counter(
    "whatsapp_messages_received_total",
    "Total WhatsApp messages received since process start",
    ["device"],
)
WHATSAPP_MESSAGES_SENT_TOTAL = Counter(
    "whatsapp_messages_sent_total",
    "Total WhatsApp messages sent since process start",
    ["device"],
)
WHATSAPP_RECONNECT_ATTEMPTS_TOTAL = Counter(
    "whatsapp_reconnect_attempts_total",
    "Total WhatsApp reconnection attempts since process start",
    ["device", "reason"],
)
WHATSAPP_RATE_LIMIT_HITS_TOTAL = Counter(
    "whatsapp_rate_limit_hits_total",
    "Total WhatsApp rate limit violations since process start",
    ["device", "window"],
)
WHATSAPP_RESPONSE_LATENCY_SECONDS = Histogram(
    "whatsapp_response_latency_seconds",
    "Time from WhatsApp message received to AI response sent",
    ["device"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")),
)


def set_connected(connected: bool, *, device: str = DEFAULT_DEVICE) -> None:
    WHATSAPP_CONNECTED.labels(device=device).set(1 if connected else 0)


def set_session_age(seconds: float, *, device: str = DEFAULT_DEVICE) -> None:
    WHATSAPP_SESSION_AGE_SECONDS.labels(device=device).set(max(seconds, 0.0))


def record_received(*, device: str = DEFAULT_DEVICE) -> None:
    WHATSAPP_MESSAGES_RECEIVED_TOTAL.labels(device=device).inc()


def record_sent(*, device: str = DEFAULT_DEVICE) -> None:
    WHATSAPP_MESSAGES_SENT_TOTAL.labels(device=device).inc()


def record_reconnect_attempt(reason: str, *, device: str = DEFAULT_DEVICE) -> None:
    WHATSAPP_RECONNECT_ATTEMPTS_TOTAL.labels(device=device, reason=reason).inc()


def record_rate_limit_hit(window: str, *, device: str = DEFAULT_DEVICE) -> None:
    WHATSAPP_RATE_LIMIT_HITS_TOTAL.labels(device=device, window=window).inc()


def observe_response_latency(seconds: float, *, device: str = DEFAULT_DEVICE) -> None:
    WHATSAPP_RESPONSE_LATENCY_SECONDS.labels(device=device).observe(seconds)

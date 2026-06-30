"""Windows Daemon Observability — Prometheus metrics for the surveillance pipeline.

P15-011: Exposes Prometheus metric families for the Windows daemon
surveillance pipeline, enabling Grafana dashboarding and alerting.

Metric families
---------------
- ``guinevere_windows_connected`` — gauge: 1 when daemon connected, 0 otherwise.
- ``guinevere_windows_events_received_total{event_type}`` — counter of received events.
- ``guinevere_windows_events_dropped_total{reason}`` — counter of dropped events.
- ``guinevere_windows_reconnects_total`` — counter of WebSocket reconnect attempts.
- ``guinevere_windows_command_latency_seconds{command}`` — histogram of command processing latency.

Integration with ``windows_consent``
-------------------------------------
Call :func:`wire_consent_hook` once during application startup to connect
the dropped-event counter to the ``windows_consent.set_dropped_event_hook``
seam (P15-009).  After wiring, every consent-gated drop automatically
increments the ``guinevere_windows_events_dropped_total`` counter with
the appropriate ``reason`` label.

Example startup sequence::

    from guinvere.observability.windows_metrics import wire_consent_hook
    wire_consent_hook()

Naming convention
-----------------
Follows the ``guinevere_`` prefix established by ``src/core/main.py``
(``guinevere_requests_total``, ``guinevere_request_duration_seconds``).
The ``windows_`` sub-prefix isolates daemon metrics from core API metrics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from prometheus_client import Counter, Gauge, Histogram

if TYPE_CHECKING:
    from guinvere.surveillance.windows_consent import WindowsConsentDecision

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Metric families
# ---------------------------------------------------------------------------

WINDOWS_CONNECTED = Gauge(
    "guinevere_windows_connected",
    "Whether the Windows daemon is currently connected (1=connected, 0=disconnected)",
)

WINDOWS_EVENTS_RECEIVED_TOTAL = Counter(
    "guinevere_windows_events_received_total",
    "Total Windows daemon surveillance events received, by event type",
    ["event_type"],
)

WINDOWS_EVENTS_DROPPED_TOTAL = Counter(
    "guinevere_windows_events_dropped_total",
    "Total Windows daemon surveillance events dropped, by reason",
    ["reason"],
)

WINDOWS_RECONNECTS_TOTAL = Counter(
    "guinevere_windows_reconnects_total",
    "Total WebSocket reconnection attempts from the Windows daemon",
)

WINDOWS_COMMAND_LATENCY_SECONDS = Histogram(
    "guinevere_windows_command_latency_seconds",
    "Latency of Windows daemon command processing in seconds",
    ["command"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
)

# ---------------------------------------------------------------------------
# Observer helpers
# ---------------------------------------------------------------------------


def set_connected(connected: bool) -> None:
    """Set the daemon connection gauge.

    Args:
        connected: ``True`` sets gauge to 1 (connected),
                   ``False`` sets gauge to 0 (disconnected).
    """
    WINDOWS_CONNECTED.set(1 if connected else 0)
    logger.debug(
        "windows_metrics_connected",
        connected=connected,
    )


def observe_event_received(event_type: str) -> None:
    """Increment the events-received counter for *event_type*.

    Call this when a Windows daemon event is accepted through the
    WebSocket handler and passes the consent gate.

    Args:
        event_type: The Windows event type (e.g. ``"active_window"``,
                    ``"idle_time"``, ``"screenshot"``, ``"notification"``).
    """
    WINDOWS_EVENTS_RECEIVED_TOTAL.labels(event_type=event_type).inc()


def observe_event_dropped(reason: str) -> None:
    """Increment the events-dropped counter for *reason*.

    Call this when a Windows daemon event is dropped for any reason
    (consent denied, safe mode, buffer failure, etc.).

    Args:
        reason: Short label for the drop reason.
    """
    WINDOWS_EVENTS_DROPPED_TOTAL.labels(reason=reason).inc()


def observe_reconnect() -> None:
    """Increment the WebSocket reconnect counter.

    Call this each time the Windows daemon WebSocket connection is
    re-established after a disconnect.
    """
    WINDOWS_RECONNECTS_TOTAL.inc()


def observe_command_latency(command: str, seconds: float) -> None:
    """Record a latency observation for a Windows daemon command.

    Args:
        command: The command name (e.g. ``"pause"``, ``"resume"``,
                 ``"status"``).
        seconds: The processing duration in seconds.
    """
    WINDOWS_COMMAND_LATENCY_SECONDS.labels(command=command).observe(seconds)


# ---------------------------------------------------------------------------
# Consent hook wiring (P15-009 integration)
# ---------------------------------------------------------------------------

_consent_hook_wired: bool = False


def _consent_drop_hook(decision: WindowsConsentDecision) -> None:
    """Prometheus hook for ``windows_consent.set_dropped_event_hook``.

    Increments the dropped-events counter with the decision's reason.
    This function is registered via :func:`wire_consent_hook` and should
    not be called directly.
    """
    observe_event_dropped(decision.reason)


def wire_consent_hook() -> bool:
    """Wire the dropped-event Prometheus counter to the consent gate hook.

    Registers :func:`_consent_drop_hook` as the dropped-event callback
    on ``src.surveillance.windows_consent``.  After calling this, every
    consent-gated drop automatically increments
    ``guinevere_windows_events_dropped_total``.

    Safe to call multiple times; subsequent calls are no-ops.

    Returns:
        ``True`` if the hook was wired (or already wired), ``False`` if
        the consent module could not be imported.
    """
    global _consent_hook_wired  # noqa: PLW0603
    if _consent_hook_wired:
        return True

    try:
        from guinvere.surveillance.windows_consent import set_dropped_event_hook

        set_dropped_event_hook(_consent_drop_hook)
        _consent_hook_wired = True
        logger.info("windows_metrics_consent_hook_wired")
        return True
    except Exception:
        logger.exception("windows_metrics_consent_hook_wire_failed")
        return False


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "WINDOWS_COMMAND_LATENCY_SECONDS",
    "WINDOWS_CONNECTED",
    "WINDOWS_EVENTS_DROPPED_TOTAL",
    "WINDOWS_EVENTS_RECEIVED_TOTAL",
    "WINDOWS_RECONNECTS_TOTAL",
    "observe_command_latency",
    "observe_event_dropped",
    "observe_event_received",
    "observe_reconnect",
    "set_connected",
    "wire_consent_hook",
]

"""LLM Routing Metrics — Prometheus metric families for Phase 6.

Exposes the following metrics on ``localhost:9191/metrics``:

- ``hermes_llm_calls_total{model,status}`` — counter of LLM calls.
- ``hermes_llm_latency_seconds`` — histogram of call duration.
- ``hermes_llm_cost_usd_total`` — accumulated cost in USD.
- ``hermes_fallback_activations_total`` — fallback chain activations.
- ``hermes_safety_blocks_total{gate,reason}`` — counter of safety blocks.
- ``hermes_session_count`` — gauge of active Hermes sessions.
- ``hermes_message_count_total{direction}`` — counter of messages by direction.

.. note::
   ``hermes_gateway_up`` is intentionally **not** defined here.  Ownership of
   the gateway-liveness metric belongs to the real Hermes Agent process, not
   the core/FastAPI metrics server (port 9191).  Defining it here would
   falsely represent gateway process health.

The HTTP server runs in a background daemon thread and is started via
:func:`start_llm_metrics_server`.
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# ---------------------------------------------------------------------------
# Metric families
# ---------------------------------------------------------------------------

LLM_CALLS_TOTAL = Counter(
    "guinevere_llm_calls_total",
    "Total LLM calls, partitioned by model and status",
    ["model", "status"],
)

LLM_LATENCY_SECONDS = Histogram(
    "guinevere_llm_latency_seconds",
    "Latency of LLM calls in seconds",
    ["model"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")),
)

LLM_COST_USD_TOTAL = Counter(
    "guinevere_llm_cost_usd_total",
    "Total LLM cost in USD",
    ["model"],
)

FALLBACK_ACTIVATIONS_TOTAL = Counter(
    "guinevere_fallback_activations_total",
    "Total fallback activations, partitioned by from_model and to_model",
    ["from_model", "to_model"],
)

SAFETY_BLOCKS_TOTAL = Counter(
    "guinevere_safety_blocks_total",
    "Total safety blocks, partitioned by gate and reason",
    ["gate", "reason"],
)

SESSION_COUNT = Gauge(
    "guinevere_session_count",
    "Current number of active Hermes sessions tracked by the safety plugin",
)

MESSAGE_COUNT_TOTAL = Counter(
    "guinevere_message_count_total",
    "Total messages processed, partitioned by direction",
    ["direction"],
)

# ---------------------------------------------------------------------------
# Guard to prevent starting the HTTP server more than once
# ---------------------------------------------------------------------------
_metrics_server_started: bool = False


def start_llm_metrics_server(port: int = 9191) -> None:
    """Start the Prometheus HTTP server on ``port`` (default 9191).

    The server runs in a background daemon thread and shuts down
    automatically when the process exits.  Safe to call multiple times;
    subsequent calls are no-ops.
    """
    global _metrics_server_started  # noqa: PLW0603
    if not _metrics_server_started:
        try:
            _ = start_http_server(port, addr="127.0.0.1")
            _metrics_server_started = True
        except OSError:
            # Port already bound by another uvicorn worker — metrics server
            # is per-process, not shared. Skip gracefully instead of crashing.
            _metrics_server_started = True


# ---------------------------------------------------------------------------
# Observer helpers
# ---------------------------------------------------------------------------


def observe_call(model: str, status: str) -> None:
    """Increment the call counter for *model* with *status*.

    *status* is typically ``"success"`` or ``"error"``.
    """
    LLM_CALLS_TOTAL.labels(model=model, status=status).inc()


def observe_latency(model: str, seconds: float) -> None:
    """Record a latency observation for *model*."""
    LLM_LATENCY_SECONDS.labels(model=model).observe(seconds)


def observe_cost(model: str, cost_usd: float) -> None:
    """Accumulate cost in USD for *model*."""
    LLM_COST_USD_TOTAL.labels(model=model).inc(cost_usd)


def observe_fallback(from_model: str, to_model: str) -> None:
    """Record a fallback activation from *from_model* to *to_model*."""
    FALLBACK_ACTIVATIONS_TOTAL.labels(from_model=from_model, to_model=to_model).inc()


def observe_safety_block(gate: str, reason: str) -> None:
    """Increment the safety blocks counter for *gate* with *reason*.

    *gate* is the safety gate identifier (e.g. ``"G01"``).
    *reason* is a short description of the block reason.
    """
    SAFETY_BLOCKS_TOTAL.labels(gate=gate, reason=reason).inc()


def set_session_count(count: int) -> None:
    """Set the current Hermes session count gauge to *count*."""
    SESSION_COUNT.set(count)


def observe_message(direction: str) -> None:
    """Increment the message counter for *direction*.

    *direction* is typically ``"incoming"``, ``"outgoing"``,
    ``"tool_call"``, or ``"tool_result"``.
    """
    MESSAGE_COUNT_TOTAL.labels(direction=direction).inc()

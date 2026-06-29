"""Prometheus metric families for the M17 circuit-breaker-adjacent metrics.

Defines 6 metric families: cost, thoughts, dreams, subagents, emotions, memory.
All metrics are registered on import. Consumers expose /metrics via W4's
FastAPI server.

Grafana is external (consumes /metrics endpoint). No Grafana code here.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy Prometheus imports — fail-soft if prometheus_client not installed
# ---------------------------------------------------------------------------

try:
    from prometheus_client import Counter, Gauge, Histogram, Info, REGISTRY

    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    logger.warning(
        "prometheus_client_not_installed",
        extra={"detail": "Metrics will be no-ops until prometheus_client is installed"},
    )


# ---------------------------------------------------------------------------
# Metric definitions — registered on import
# ---------------------------------------------------------------------------

if _PROMETHEUS_AVAILABLE:
    # 1. Cost tracking
    METRIC_COST_TOTAL = Counter(
        "guinevere_cost_cents_total",
        "Total cost in cents",
        ["model", "operation"],
    )
    METRIC_COST_PER_REQUEST = Histogram(
        "guinevere_cost_cents_per_request",
        "Cost per request in cents",
        ["model"],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0],
    )

    # 2. Thoughts (inner monologue / reasoning)
    METRIC_THOUGHTS_TOTAL = Counter(
        "guinevere_thoughts_total",
        "Total thoughts generated",
        ["persona", "type"],
    )
    METRIC_THOUGHT_DURATION = Histogram(
        "guinevere_thought_duration_seconds",
        "Time spent generating thoughts",
        ["persona"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )

    # 3. Dreams (offline consolidation)
    METRIC_DREAMS_TOTAL = Counter(
        "guinevere_dreams_total",
        "Total dream/consolidation cycles",
        ["persona", "status"],
    )
    METRIC_DREAM_DURATION = Histogram(
        "guinevere_dream_duration_seconds",
        "Dream cycle duration",
        ["persona"],
        buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    )

    # 4. Sub-agents
    METRIC_SUBAGENTS_ACTIVE = Gauge(
        "guinevere_subagents_active",
        "Currently active sub-agents",
        ["type"],
    )
    METRIC_SUBAGENTS_TOTAL = Counter(
        "guinevere_subagents_total",
        "Total sub-agent invocations",
        ["type", "status"],
    )

    # 5. Emotions
    METRIC_EMOTIONS_CURRENT = Gauge(
        "guinevere_emotions_current",
        "Current emotional state value",
        ["emotion"],
    )
    METRIC_EMOTIONS_TRANSITIONS = Counter(
        "guinevere_emotions_transitions_total",
        "Total emotion transitions",
        ["from_emotion", "to_emotion"],
    )

    # 6. Memory
    METRIC_MEMORY_ITEMS = Gauge(
        "guinevere_memory_items",
        "Number of items in memory store",
        ["tier"],
    )
    METRIC_MEMORY_OPERATIONS = Counter(
        "guinevere_memory_operations_total",
        "Total memory operations",
        ["operation", "tier"],
    )

    METRIC_SYSTEM_INFO = Info(
        "guinevere_system",
        "System information",
    )

    logger.info("prometheus_metrics_registered", metric_count=14)
else:
    # No-op stubs when prometheus_client is not installed
    METRIC_COST_TOTAL = None
    METRIC_COST_PER_REQUEST = None
    METRIC_THOUGHTS_TOTAL = None
    METRIC_THOUGHT_DURATION = None
    METRIC_DREAMS_TOTAL = None
    METRIC_DREAM_DURATION = None
    METRIC_SUBAGENTS_ACTIVE = None
    METRIC_SUBAGENTS_TOTAL = None
    METRIC_EMOTIONS_CURRENT = None
    METRIC_EMOTIONS_TRANSITIONS = None
    METRIC_MEMORY_ITEMS = None
    METRIC_MEMORY_OPERATIONS = None
    METRIC_SYSTEM_INFO = None


def is_available() -> bool:
    """Return True if prometheus_client is installed and metrics are live."""
    return _PROMETHEUS_AVAILABLE


__all__ = [
    "is_available",
    "METRIC_COST_TOTAL",
    "METRIC_COST_PER_REQUEST",
    "METRIC_THOUGHTS_TOTAL",
    "METRIC_THOUGHT_DURATION",
    "METRIC_DREAMS_TOTAL",
    "METRIC_DREAM_DURATION",
    "METRIC_SUBAGENTS_ACTIVE",
    "METRIC_SUBAGENTS_TOTAL",
    "METRIC_EMOTIONS_CURRENT",
    "METRIC_EMOTIONS_TRANSITIONS",
    "METRIC_MEMORY_ITEMS",
    "METRIC_MEMORY_OPERATIONS",
    "METRIC_SYSTEM_INFO",
]

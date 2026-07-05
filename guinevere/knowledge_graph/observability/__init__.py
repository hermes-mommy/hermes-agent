"""Knowledge Graph observability — metrics, structured logging, and tracing.

Public surface
--------------
- :class:`KGMetrics` — singleton Prometheus registry for all KG metric
  families. Safe to use even when ``prometheus_client`` is not installed
  (every call becomes a thread-safe no-op).
- :func:`get_kg_logger` — factory for stdlib loggers in the
  ``guinevere.kg.*`` namespace.
- :class:`KGTraceContext` — lightweight async-safe tracer built on
  :mod:`contextvars`; no external APM dependency.

Supporting types (also re-exported) include :class:`KGLogContext`,
:func:`log_kg_operation`, :class:`KGTraceSpan`, :func:`get_current_span`,
and :data:`HAS_PROMETHEUS`.

Stability
---------
This module is a hard dependency for every other KG submodule. It must
never raise, and every public function must remain a total operation
on bad input.
"""

from guinevere.knowledge_graph.observability.logger import (
    KGLogContext,
    get_kg_logger,
    log_kg_operation,
)
from guinevere.knowledge_graph.observability.metrics import HAS_PROMETHEUS, KGMetrics
from guinevere.knowledge_graph.observability.tracer import (
    KGTraceContext,
    KGTraceSpan,
    get_current_span,
)

__all__ = [
    # Metrics
    "HAS_PROMETHEUS",
    "KGMetrics",
    # Logger
    "KGLogContext",
    "get_kg_logger",
    "log_kg_operation",
    # Tracer
    "KGTraceContext",
    "KGTraceSpan",
    "get_current_span",
]

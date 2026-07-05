"""Knowledge Graph observability — lightweight operation tracing.

A self-contained tracer built on :mod:`contextvars` (no OpenTelemetry, no
APM sidecar, no extra dependencies). Each :class:`KGTraceContext` call
produces a :class:`KGTraceSpan` carrying a trace id, a span id, and a
monotonic duration. Finished spans are forwarded to the
:data:`guinevere_kg_query_duration_seconds` histogram so they show up
alongside the other KG metrics.

Async-safety
------------
The active span lives in a :class:`contextvars.ContextVar`, so nested
``async`` / ``await`` boundaries and ``concurrent.futures`` propagations
inherit the right span automatically. There is no global mutable state
outside the ``ContextVar`` itself.

Failure model
-------------
Every public method is total: an internal exception during metric export is
caught and logged at DEBUG; the caller never sees it. The tracer must not
be a source of failure for the rest of the KG pipeline.
"""

from __future__ import annotations

import logging
import secrets
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import ClassVar, Final

logger = logging.getLogger(__name__)

# Active span slot. ``default=None`` means "no span in this context".
_active_span: ContextVar[KGTraceSpan | None] = ContextVar(
    "guinevere_kg_active_span",
    default=None,
)

_TRACE_ID_BYTES: Final[int] = 16  # 128 bits — matches W3C trace-context
_SPAN_ID_BYTES: Final[int] = 8  # 64 bits — matches W3C trace-context


def _new_trace_id() -> str:
    """Return a fresh 32-character hex trace id (W3C-compatible length)."""
    return secrets.token_hex(_TRACE_ID_BYTES)


def _new_span_id() -> str:
    """Return a fresh 16-character hex span id (W3C-compatible length)."""
    return secrets.token_hex(_SPAN_ID_BYTES)


# ---------------------------------------------------------------------------
# Span
# ---------------------------------------------------------------------------


@dataclass
class KGTraceSpan:
    """Single in-flight or completed operation span.

    Attributes:
        trace_id: 32-char hex identifier shared by every span in the same
            logical trace (created lazily on the outermost ``start_operation``).
        span_id: 16-char hex identifier unique to this span within the trace.
        operation: Short verb-noun label for the operation
            (e.g. ``"query_expand"``, ``"entity_resolve"``).
        start_time: Monotonic clock value captured at span start.
        end_time: Monotonic clock value at :meth:`finish`; ``None`` while
            the span is still in flight.
        tags: Free-form key-value annotations captured at start or finish.
        status: One of ``"ok"``, ``"error"``, or ``"degraded"``. Defaults
            to ``"ok"``; call :meth:`finish` with another value to override.
        duration_ms: Wall-clock duration in milliseconds, populated by
            :meth:`finish`. ``None`` until then.
    """

    trace_id: str
    span_id: str
    operation: str
    start_time: float
    end_time: float | None = None
    tags: dict[str, object] = field(default_factory=dict)
    status: str = "ok"
    duration_ms: float | None = None

    def finish(self, status: str = "ok", **fields: object) -> None:
        """Mark the span finished. Idempotent: second calls are no-ops.

        Args:
            status: Final status — typically ``"ok"``, ``"error"``, or
                ``"degraded"``.
            **fields: Additional key-value annotations to merge into
                :attr:`tags`. Useful for recording per-span attributes
                (``result_count``, ``error_class``, etc.) at finish time.
        """
        if self.end_time is not None:
            # Already finalized — keep the first result to avoid skewing
            # the recorded duration.
            return
        self.end_time = time.monotonic()
        self.status = status
        self.duration_ms = round((self.end_time - self.start_time) * 1000.0, 3)
        if fields:
            self.tags.update(fields)
        # Clear the active slot only if it still points at us. A nested
        # span that finished earlier may have already restored the parent.
        if _active_span.get() is self:
            _active_span.set(None)

    @property
    def finished(self) -> bool:
        """``True`` once :meth:`finish` has run."""
        return self.end_time is not None


# ---------------------------------------------------------------------------
# Tracer
# ---------------------------------------------------------------------------


class KGTraceContext:
    """Tracer for KG operations.

    Use :meth:`start_operation` to open a span, then :meth:`end_span` to
    close it. Spans automatically record to the query-duration histogram
    (the primary cardinality-bearing latency signal) and the active span
    is available anywhere downstream via :func:`get_current_span`.

    Typical usage::

        tracer = KGTraceContext()
        with_tracer_block = tracer.start_operation("query_expand", hop_count=2)
        try:
            result = do_work()
            tracer.end_span(span, status="ok", result_count=len(result))
        except Exception as exc:
            tracer.end_span(span, status="error", error_class=type(exc).__name__)
            raise
    """

    # Default operation label used for spans that have no ``operation``.
    _DEFAULT_OPERATION: ClassVar[str] = "kg_operation"

    def start_operation(self, operation: str, **tags: object) -> KGTraceSpan:
        """Open a new span and make it the active span in this context.

        Args:
            operation: Short verb-noun label for the operation.
            **tags: Initial annotations attached to the span. Values must
                be JSON-serializable primitives or simple containers.

        Returns:
            The newly created :class:`KGTraceSpan`. Always non-``None``.
        """
        op = operation or self._DEFAULT_OPERATION
        # Inherit the parent's trace_id so the new span is part of the same
        # logical trace. Span id is always unique.
        parent = _active_span.get()
        trace_id = parent.trace_id if parent is not None else _new_trace_id()
        span = KGTraceSpan(
            trace_id=trace_id,
            span_id=_new_span_id(),
            operation=op,
            start_time=time.monotonic(),
            tags=dict(tags),
        )
        _active_span.set(span)
        return span

    def end_span(
        self,
        span: KGTraceSpan,
        *,
        status: str = "ok",
        **fields: object,
    ) -> None:
        """Close a span and record it to the query-duration histogram.

        Args:
            span: The :class:`KGTraceSpan` returned by
                :meth:`start_operation`.
            status: Final status — ``"ok"``, ``"error"``, or ``"degraded"``.
            **fields: Extra annotations to merge into ``span.tags`` (e.g.
                ``result_count=42``, ``error_class="TimeoutError"``).
        """
        span.finish(status, **fields)
        # Forward to the metrics histogram. Failures here are absorbed so the
        # tracer never breaks the calling code path.
        if span.duration_ms is not None:
            self._record_to_metrics(span)

    @staticmethod
    def _record_to_metrics(span: KGTraceSpan) -> None:
        """Push the finished span into the query-duration histogram.

        Imported lazily so :mod:`guinevere.knowledge_graph.observability.metrics`
        can in turn depend on the logger without creating a cycle.
        """
        try:
            # Local import keeps the import graph acyclic; metrics.py never
            # imports from this module.
            from guinevere.knowledge_graph.observability.metrics import KGMetrics

            duration_seconds = (span.duration_ms or 0.0) / 1000.0
            hop_count_raw = span.tags.get("hop_count", 0)
            try:
                hop_count_int = int(hop_count_raw) if hop_count_raw is not None else 0
            except (TypeError, ValueError):
                hop_count_int = 0
            KGMetrics.get_instance().observe_query_duration(
                query_type=span.operation,
                hop_count=hop_count_int,
                duration=duration_seconds,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(
                "kg_trace_metric_record_failed",
                extra={"span_id": span.span_id, "error": str(exc)},
            )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def get_current_span() -> KGTraceSpan | None:
    """Return the active :class:`KGTraceSpan` in the current context.

    Returns:
        The active span, or ``None`` if no span is open. Safe to call from
        any coroutine or thread that has not opened its own context.
    """
    return _active_span.get()


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "KGTraceContext",
    "KGTraceSpan",
    "get_current_span",
]

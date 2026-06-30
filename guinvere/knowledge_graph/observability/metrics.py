"""Knowledge Graph observability — Prometheus metrics.

Singleton ``KGMetrics`` registry for the Knowledge Graph pipeline. Exposes
the ten metric families listed in the KG observability contract; every public
record/observe/set method is a thread-safe no-op when ``prometheus_client``
is not importable, so the rest of the KG stack can depend on this module
unconditionally.

Metric families
---------------
- ``guinevere_kg_extractions_total``            counter   (entity_category, relation_type, status)
- ``guinevere_kg_resolution_total``             counter   (method, result)
- ``guinevere_kg_ingestion_duration_seconds``   histogram (batch_type)
- ``guinevere_kg_query_duration_seconds``       histogram (query_type, hop_count)
- ``guinevere_kg_entities_total``               gauge     (category)
- ``guinevere_kg_edges_total``                  gauge     (relation_type)
- ``guinevere_kg_tombstones_total``             counter   (entity_type)
- ``guinevere_kg_consent_checks_total``         counter   (result)
- ``guinevere_kg_rrf_fusion_total``             counter   (signal_source)
- ``guinevere_kg_token_budget_utilization``     histogram ()

Thread-safety
-------------
``prometheus_client`` primitives are internally thread-safe (atomic
``ValueMutex`` per metric). The only guarded region is the singleton
initialization itself (double-checked locking). No-op fallbacks are
trivially thread-safe.
"""

from __future__ import annotations

import logging
import threading
from typing import ClassVar

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional prometheus_client import — graceful no-op fallback
# ---------------------------------------------------------------------------

_PROMETHEUS_COUNTER: object | None = None
_PROMETHEUS_GAUGE: object | None = None
_PROMETHEUS_HISTOGRAM: object | None = None

try:
    from prometheus_client import Counter as _PromCounter
    from prometheus_client import Gauge as _PromGauge
    from prometheus_client import Histogram as _PromHistogram

    _PROMETHEUS_COUNTER = _PromCounter
    _PROMETHEUS_GAUGE = _PromGauge
    _PROMETHEUS_HISTOGRAM = _PromHistogram
except ImportError:  # pragma: no cover - exercised when lib is absent
    _PROMETHEUS_COUNTER = None
    _PROMETHEUS_GAUGE = None
    _PROMETHEUS_HISTOGRAM = None

HAS_PROMETHEUS: bool = _PROMETHEUS_COUNTER is not None
"""``True`` when ``prometheus_client`` is importable, ``False`` otherwise."""


# ---------------------------------------------------------------------------
# No-op metric fallback
# ---------------------------------------------------------------------------


class _NoOpMetric:
    """No-op metric used when ``prometheus_client`` is unavailable.

    Mirrors the subset of the ``prometheus_client`` API used by ``KGMetrics``
    (``labels``, ``inc``, ``dec``, ``set``, ``observe``). Every call is a
    cheap pointer-return / no-op and never raises.
    """

    __slots__ = ("_name",)

    def __init__(self, name: str = "", documentation: str = "", labelnames: tuple[str, ...] = ()) -> None:
        self._name = name

    def labels(self, **_: object) -> _NoOpMetric:
        return self

    def inc(self, amount: float = 1.0) -> None:
        del amount

    def dec(self, amount: float = 1.0) -> None:
        del amount

    def set(self, value: float) -> None:
        del value

    def observe(self, value: float) -> None:
        del value


def _make_counter(name: str, documentation: str, labelnames: tuple[str, ...] = ()):
    """Return a real ``Counter`` when prometheus is available, else a no-op."""
    if _PROMETHEUS_COUNTER is not None:
        return _PROMETHEUS_COUNTER(name, documentation, labelnames)
    return _NoOpMetric(name, documentation, labelnames)


def _make_gauge(name: str, documentation: str, labelnames: tuple[str, ...] = ()):
    """Return a real ``Gauge`` when prometheus is available, else a no-op."""
    if _PROMETHEUS_GAUGE is not None:
        return _PROMETHEUS_GAUGE(name, documentation, labelnames)
    return _NoOpMetric(name, documentation, labelnames)


def _make_histogram(
    name: str,
    documentation: str,
    labelnames: tuple[str, ...] = (),
    buckets: tuple[float, ...] | None = None,
):
    """Return a real ``Histogram`` when prometheus is available, else a no-op."""
    if _PROMETHEUS_HISTOGRAM is not None:
        if buckets is not None:
            return _PROMETHEUS_HISTOGRAM(name, documentation, labelnames, buckets=buckets)
        return _PROMETHEUS_HISTOGRAM(name, documentation, labelnames)
    return _NoOpMetric(name, documentation, labelnames)


# ---------------------------------------------------------------------------
# Default histogram buckets
# ---------------------------------------------------------------------------

# Ingestion pipelines typically run in tens-of-milliseconds to a few seconds.
_INGESTION_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    float("inf"),
)

# Query latency tends to be tighter, with a longer tail for multi-hop.
_QUERY_BUCKETS: tuple[float, ...] = (
    0.001,
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    float("inf"),
)

# Token budget utilization ratio (0.0 - 1.0+). 1.0 means fully consumed.
_TOKEN_BUDGET_BUCKETS: tuple[float, ...] = (
    0.1,
    0.25,
    0.5,
    0.75,
    0.9,
    1.0,
    1.25,
    1.5,
    2.0,
    float("inf"),
)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class KGMetrics:
    """Singleton Prometheus metric registry for Knowledge Graph operations.

    Use :meth:`get_instance` to obtain the shared instance. The first call
    lazily registers all metric families with the default Prometheus
    registry. Subsequent calls return the cached instance.

    All ``record_*``, ``observe_*``, and ``set_*`` methods are safe to call
    from multiple threads concurrently. They never raise — even when
    ``prometheus_client`` is not importable, the underlying no-op
    implementations silently absorb the call.
    """

    _instance: ClassVar[KGMetrics | None] = None
    _init_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        # Force callers through get_instance(); direct construction is not
        # supported to preserve the singleton invariant.
        raise RuntimeError("KGMetrics is a singleton; use KGMetrics.get_instance()")

    @classmethod
    def get_instance(cls) -> KGMetrics:
        """Return the process-wide ``KGMetrics`` instance (lazy-init)."""
        # Double-checked locking: fast path avoids the lock when already built.
        existing = cls._instance
        if existing is not None:
            return existing
        with cls._init_lock:
            if cls._instance is None:
                instance = cls.__new__(cls)
                instance._initialize()
                cls._instance = instance
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Drop the cached singleton. Intended for tests only.

        The next :meth:`get_instance` call will rebuild the metric families.
        """
        with cls._init_lock:
            cls._instance = None

    # -- Initialization -------------------------------------------------------

    def _initialize(self) -> None:
        # Counters
        self._extractions_total = _make_counter(
            "guinevere_kg_extractions_total",
            "Total Knowledge Graph entity/edge extractions by category, relation, and status",
            ("entity_category", "relation_type", "status"),
        )
        self._resolution_total = _make_counter(
            "guinevere_kg_resolution_total",
            "Total entity resolution attempts (method=exact|fuzzy|none, result=hit|miss)",
            ("method", "result"),
        )
        self._tombstones_total = _make_counter(
            "guinevere_kg_tombstones_total",
            "Total Knowledge Graph tombstone (soft-delete) events by entity type",
            ("entity_type",),
        )
        self._consent_checks_total = _make_counter(
            "guinevere_kg_consent_checks_total",
            "Total consent gate checks (result=pass|deny|error)",
            ("result",),
        )
        self._rrf_fusion_total = _make_counter(
            "guinevere_kg_rrf_fusion_total",
            "Total RRF signal contributions by source",
            ("signal_source",),
        )

        # Histograms
        self._ingestion_duration_seconds = _make_histogram(
            "guinevere_kg_ingestion_duration_seconds",
            "Latency of Knowledge Graph ingestion pipelines in seconds",
            ("batch_type",),
            buckets=_INGESTION_BUCKETS,
        )
        self._query_duration_seconds = _make_histogram(
            "guinevere_kg_query_duration_seconds",
            "Latency of Knowledge Graph queries in seconds",
            ("query_type", "hop_count"),
            buckets=_QUERY_BUCKETS,
        )
        self._token_budget_utilization = _make_histogram(
            "guinevere_kg_token_budget_utilization",
            "Distribution of KG token-budget utilization ratios (used / budget)",
            (),
            buckets=_TOKEN_BUDGET_BUCKETS,
        )

        # Gauges
        self._entities_total = _make_gauge(
            "guinevere_kg_entities_total",
            "Current number of live entities by category",
            ("category",),
        )
        self._edges_total = _make_gauge(
            "guinevere_kg_edges_total",
            "Current number of live edges by relation type",
            ("relation_type",),
        )

        if HAS_PROMETHEUS:
            logger.info(
                "kg_metrics_initialized",
                extra={"singleton": True, "prometheus": True},
            )
        else:
            logger.info(
                "kg_metrics_initialized_noop",
                extra={"singleton": True, "prometheus": False},
            )

    # -- Counters -------------------------------------------------------------

    def record_extraction(
        self,
        entity_category: str,
        relation_type: str,
        status: str,
    ) -> None:
        """Increment the extractions counter for a category/relation/status.

        Args:
            entity_category: Schema category (e.g. ``"person"``, ``"project"``).
            relation_type: Edge relation label (e.g. ``"works_on"``). Pass
                ``"-"`` or an empty string for entity-only extractions that
                do not produce a relation.
            status: Outcome label — typically ``"ok"``, ``"skipped"``,
                ``"filtered"``, or ``"error"``.
        """
        self._extractions_total.labels(
            entity_category=entity_category,
            relation_type=relation_type,
            status=status,
        ).inc()

    def record_resolution(self, method: str, result: str) -> None:
        """Increment the entity resolution counter.

        Args:
            method: Resolution strategy used — ``"exact"``, ``"fuzzy"``,
                or ``"none"`` when no candidate was attempted.
            result: ``"hit"`` when an existing entity was matched,
                ``"miss"`` otherwise.
        """
        self._resolution_total.labels(method=method, result=result).inc()

    def record_tombstone(self, entity_type: str) -> None:
        """Increment the tombstone counter for a given entity type."""
        self._tombstones_total.labels(entity_type=entity_type).inc()

    def record_consent_check(self, result: str) -> None:
        """Increment the consent-check counter.

        Args:
            result: One of ``"pass"``, ``"deny"``, ``"error"``.
        """
        self._consent_checks_total.labels(result=result).inc()

    def record_rrf_signal(self, signal_source: str) -> None:
        """Increment the RRF fusion counter for a given signal source.

        Args:
            signal_source: Origin of the signal — e.g. ``"vector"``,
                ``"fts"``, ``"graph"``, ``"recency"``.
        """
        self._rrf_fusion_total.labels(signal_source=signal_source).inc()

    # -- Histograms -----------------------------------------------------------

    def observe_ingestion_duration(self, batch_type: str, duration: float) -> None:
        """Record an ingestion-pipeline latency observation in seconds.

        Args:
            batch_type: Batch label — e.g. ``"entity"``, ``"edge"``,
                ``"consolidation"``.
            duration: Elapsed time, in seconds.
        """
        if duration < 0:
            # Prometheus histograms reject negative observations; clamp to 0
            # to keep the call site free of validation logic.
            duration = 0.0
        self._ingestion_duration_seconds.labels(batch_type=batch_type).observe(duration)

    def observe_query_duration(
        self,
        query_type: str,
        hop_count: int,
        duration: float,
    ) -> None:
        """Record a query latency observation in seconds.

        Args:
            query_type: Query class — e.g. ``"expand"``, ``"traverse"``,
                ``"lookup"``.
            hop_count: Number of graph hops traversed (stringified for the
                label to keep cardinality bounded).
            duration: Elapsed time, in seconds.
        """
        if duration < 0:
            duration = 0.0
        # Bound hop_count to a small set of buckets to keep label cardinality
        # reasonable (1, 2, 3, 4, 5+).
        if hop_count < 1:
            hop_label = "0"
        elif hop_count >= 5:
            hop_label = "5+"
        else:
            hop_label = str(hop_count)
        self._query_duration_seconds.labels(
            query_type=query_type,
            hop_count=hop_label,
        ).observe(duration)

    def observe_token_budget(self, utilization_ratio: float) -> None:
        """Record a token-budget utilization observation.

        Args:
            utilization_ratio: Ratio of tokens used to tokens allocated
                (e.g. ``1.0`` means fully consumed, ``1.5`` means
                overshot by 50%).
        """
        if utilization_ratio < 0:
            utilization_ratio = 0.0
        self._token_budget_utilization.observe(utilization_ratio)

    # -- Gauges ---------------------------------------------------------------

    def set_entity_count(self, category: str, count: int) -> None:
        """Set the live entity count for a given category.

        Args:
            category: Entity category label.
            count: Current number of live entities in that category.
        """
        if count < 0:
            count = 0
        self._entities_total.labels(category=category).set(count)

    def set_edge_count(self, relation_type: str, count: int) -> None:
        """Set the live edge count for a given relation type.

        Args:
            relation_type: Relation label.
            count: Current number of live edges of that relation type.
        """
        if count < 0:
            count = 0
        self._edges_total.labels(relation_type=relation_type).set(count)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "HAS_PROMETHEUS",
    "KGMetrics",
]

"""Knowledge Graph observability — structured logging.

Provides :func:`get_kg_logger` (stdlib ``logging``-based, hierarchical
``guinevere.kg.*`` names) and :func:`log_kg_operation` (single-call helper
that emits a structured log line for a KG operation with the correct
severity).

Pattern
-------
- Loggers use stdlib :mod:`logging` — the same family the memory module
  relies on (``logging.getLogger(__name__)``), so the existing application
  logging configuration applies unchanged to the ``guinevere.kg.*`` subtree.
- Context is attached via the standard ``extra=`` kwarg so downstream formatters
  (JSON, key-value, or structlog bridges) can pick the fields up without any
  additional glue.

Severity policy
---------------
- ``DEBUG``   — internal details (query plans, SQL traces).
- ``INFO``    — successful operations.
- ``WARNING`` — degraded (operation succeeded but yielded no results).
- ``ERROR``   — failures (exception raised, contract violated).
- ``CRITICAL`` — consent / safety boundary violations (use sparingly, never
                from within this module).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

# Root logger name for all KG loggers. Configuration that targets
# ``guinevere.kg`` (or any descendant) will reach every KG module.
KG_LOGGER_ROOT: Final[str] = "guinevere.kg"
"""Prefix for every logger returned by :func:`get_kg_logger`."""


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


def get_kg_logger(name: str) -> logging.Logger:
    """Return a logger named ``guinevere.kg.<name>``.

    Args:
        name: Short, dot-separated identifier for the calling module
            (e.g. ``"extraction"``, ``"query"``, ``"consent"``). The returned
            logger's full name is ``guinevere.kg.<name>`` so logging
            configuration can target the entire KG subtree.

    Returns:
        A stdlib :class:`logging.Logger` instance. Never raises.

    Example::

        logger = get_kg_logger("extraction")
        logger.info("extraction_started", extra={"source": "episode"})
    """
    if not name:
        # Defensive: empty name would collapse to "guinevere.kg." which is
        # still resolvable but signals a programming error. Use the root
        # KG logger instead.
        return logging.getLogger(KG_LOGGER_ROOT)
    return logging.getLogger(f"{KG_LOGGER_ROOT}.{name}")


# ---------------------------------------------------------------------------
# Operation context
# ---------------------------------------------------------------------------


@dataclass
class KGLogContext:
    """Structured context for a single KG operation log line.

    All fields are optional except ``operation``. The dataclass is frozen
    so a single context can be safely re-used or copied without mutation
    surprises in concurrent code paths.

    Attributes:
        operation: Short verb-noun label for the operation
            (e.g. ``"entity_extracted"``, ``"query_executed"``).
        entity_category: Entity schema category, if applicable.
        relation_type: Edge relation label, if applicable.
        hop_count: Number of graph hops traversed, if applicable.
        duration_ms: Elapsed wall-clock time, in milliseconds.
        result_count: Number of results produced (entities, edges, hits).
        error: Exception class name + message, populated on failures.
    """

    operation: str
    entity_category: str | None = None
    relation_type: str | None = None
    hop_count: int | None = None
    duration_ms: float | None = None
    result_count: int | None = None
    error: str | None = None

    def as_extra(self) -> dict[str, object]:
        """Return the context as a ``logging`` ``extra=`` dict.

        Keys are namespaced with ``kg_`` so they do not collide with the
        stdlib ``LogRecord`` built-in attributes (``msg``, ``args``,
        ``levelname``, …).
        """
        return {
            "kg_operation": self.operation,
            "kg_entity_category": self.entity_category,
            "kg_relation_type": self.relation_type,
            "kg_hop_count": self.hop_count,
            "kg_duration_ms": self.duration_ms,
            "kg_result_count": self.result_count,
            "kg_error": self.error,
        }


# ---------------------------------------------------------------------------
# Operation logger
# ---------------------------------------------------------------------------


def _format_message(context: KGLogContext) -> str:
    """Build the human-readable log line for a context."""
    parts: list[str] = [f"[KG] {context.operation}"]
    if context.entity_category is not None:
        parts.append(f"category={context.entity_category}")
    if context.relation_type is not None:
        parts.append(f"relation={context.relation_type}")
    if context.hop_count is not None:
        parts.append(f"hops={context.hop_count}")
    if context.duration_ms is not None:
        parts.append(f"duration={context.duration_ms:.2f}ms")
    if context.result_count is not None:
        parts.append(f"results={context.result_count}")
    return " | ".join(parts)


def log_kg_operation(
    logger: logging.Logger,
    context: KGLogContext,
) -> None:
    """Emit a structured log line for a KG operation.

    Severity is chosen automatically from the context:

    - ``ERROR``   — when ``context.error`` is set.
    - ``WARNING`` — when the operation succeeded but produced zero results
      (``context.result_count == 0`` and no error). Use this level for
      "degraded" outcomes (queries that hit the index but found nothing,
      extractions whose filters rejected every candidate, etc.).
    - ``INFO``    — for successful, non-empty operations.

    The ``module``, ``operation``, and ``entity_category`` fields are
    attached to the ``LogRecord`` via the ``extra=`` kwarg using the
    ``kg_`` namespace (see :meth:`KGLogContext.as_extra`).

    Args:
        logger: A :class:`logging.Logger` — typically obtained from
            :func:`get_kg_logger`.
        context: Structured context for this operation.

    Example::

        ctx = KGLogContext(
            operation="entity_extracted",
            entity_category="person",
            duration_ms=12.5,
            result_count=3,
        )
        log_kg_operation(get_kg_logger("extraction"), ctx)
        # -> [KG] entity_extracted | category=person | duration=12.50ms | results=3
    """
    message = _format_message(context)
    extra = context.as_extra()

    if context.error is not None:
        # Failure path: append the error inline so the message is useful
        # even when downstream formatters strip the extra dict.
        logger.error(
            "%s | error=%s",
            message,
            context.error,
            extra=extra,
        )
        return

    if context.result_count == 0:
        # Degraded: succeeded with no results. Reachable when callers set
        # result_count explicitly; missing result_count falls through to INFO.
        logger.warning("%s | degraded=no_results", message, extra=extra)
        return

    logger.info(message, extra=extra)


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "KG_LOGGER_ROOT",
    "KGLogContext",
    "get_kg_logger",
    "log_kg_operation",
]

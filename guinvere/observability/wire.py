"""Wire observability (Sentry + Prometheus) into Hermes agent runtime.

Parent calls this from agent_init.py (appends-only Group G block). We do NOT
edit agent_init.py.

Rewritten to the REAL observability API:
  - init_sentry(*, environment=, release=) -> bool  (sentry.py:180); DSN from
    env SENTRY_DSN. NOT (dsn=, traces_sample_rate=).
  - Metrics are METRIC_* objects (metrics.py), conditionally None when
    prometheus_client is absent. LLM_CALL_COUNTER/LLM_TOKEN_COUNTER/AGENT_UPTIME
    do NOT exist — we reuse METRIC_COST_TOTAL / METRIC_SYSTEM_INFO and expose
    is_available().

No new config sections: there is NO ObservabilityConfig model in
GuinevereConfig. We read environment/release from env and the existing
agent settings where possible, with getattr guards and early-return.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def wire(agent: Any) -> None:
    """Initialize Sentry error tracking and attach Prometheus metrics.

    No-op (logged) when settings absent or when neither subsystem can init.
    Never raises — observability is optional at agent boot.
    """
    settings = getattr(agent, "_guinevere_settings", None)
    if settings is None:
        logger.info("observability.wire.skipped no guinevere settings")
        return

    # No observability config section; read env-driven knobs. init_sentry
    # reads SENTRY_DSN itself and is fail-soft (returns False if unset).
    environment = os.environ.get("GUINEVERE_ENV", "production")
    release = os.environ.get("GUINEVERE_RELEASE", "unknown")

    sentry_ok = False
    try:
        from guinevere.observability.sentry import init_sentry

        sentry_ok = init_sentry(environment=environment, release=release)
    except (ImportError, AttributeError, RuntimeError, ValueError) as exc:
        logger.warning("observability.wire.sentry_failed %s", exc)

    agent._sentry_initialized = sentry_ok

    # Attach the existing Prometheus metric objects as a dict for runtime use.
    try:
        from guinevere.observability import metrics as _metrics_mod

        agent._metrics = {
            "cost_total": getattr(_metrics_mod, "METRIC_COST_TOTAL", None),
            "thoughts_total": getattr(_metrics_mod, "METRIC_THOUGHTS_TOTAL", None),
            "system_info": getattr(_metrics_mod, "METRIC_SYSTEM_INFO", None),
            "subagents_active": getattr(_metrics_mod, "METRIC_SUBAGENTS_ACTIVE", None),
            "prometheus_available": _metrics_mod.is_available(),
        }
    except (ImportError, AttributeError) as exc:
        logger.warning("observability.wire.metrics_failed %s", exc)
        agent._metrics = {}

    # Stamp system_info once at boot if the metric object is live. The metric
    # may be None (prometheus_client absent) or a prometheus.Info; we guard the
    # .info() call so a missing/None object does not crash boot.
    system_info = agent._metrics.get("system_info") if agent._metrics else None
    info_call = getattr(system_info, "info", None) if system_info is not None else None
    if callable(info_call):
        try:
            info_call({"environment": environment, "release": release})
        except (AttributeError, ValueError, RuntimeError, TypeError) as exc:
            logger.debug("observability.system_info.stamp_failed %s", exc)

    logger.info(
        "observability.wire.ok sentry=%s metrics=%d",
        sentry_ok,
        len(agent._metrics) if agent._metrics else 0,
    )

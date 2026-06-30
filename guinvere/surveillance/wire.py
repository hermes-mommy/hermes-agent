"""Wire surveillance buffer into Hermes agent runtime.

Parent calls this from agent_init.py (appends-only Group G block). We do NOT
edit agent_init.py.

Rewritten to the REAL surveillance API (buffer.py):
  SurveillanceBuffer is a Protocol — use create_buffer(host, port, password)
  or NullBuffer(). The push method is async push_event(event_dict) -> bool.

No new config sections: there is NO SurveillanceConfig model in
GuinevereConfig. We read connection details from agent._guinevere_settings.redis
(the existing RedisConfig) and the SENTRY/REDIS env, with getattr guards and
early-return if unavailable. Surveillance itself is consent-gated upstream
(AGENTS.md §2.1); this wire only attaches the buffer, it does not enable
surveillance capture without the consent/safety boundary.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def wire(agent: Any) -> None:
    """Attach a surveillance buffer to the agent for LLM-event capture.

    No-op (logged) when settings or the redis config is absent, or when
    buffer construction fails. Never raises — surveillance is optional and
    must not destabilize agent boot.
    """
    settings = getattr(agent, "_guinevere_settings", None)
    if settings is None:
        logger.info("surveillance.wire.skipped no guinevere settings")
        return

    # No dedicated surveillance section; reuse the existing RedisConfig if present.
    redis_cfg = getattr(settings, "redis", None)
    host = getattr(redis_cfg, "host", "localhost") if redis_cfg else "localhost"
    port = getattr(redis_cfg, "port", 6380) if redis_cfg else 6380
    password = getattr(redis_cfg, "password", None) if redis_cfg else None

    try:
        from guinevere.surveillance.buffer import create_buffer

        buffer = create_buffer(host=host, port=port, password=password)
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        logger.warning("surveillance.wire.buffer_failed %s", exc)
        agent._surveillance_buffer = None
        return

    agent._surveillance_buffer = buffer

    # Capture hook: push an LLM-call event dict into the buffer.
    async def post_llm_hook(event: dict[str, Any]) -> None:
        """Capture LLM call metadata after each turn (best-effort)."""
        try:
            await buffer.push_event(event)
        except (ConnectionError, TimeoutError, ValueError, KeyError) as exc:
            logger.warning("surveillance.hook.drop %s", exc)
        except RuntimeError as exc:
            logger.debug("surveillance.hook.runtime %s", exc)

    agent._surveillance_hook = post_llm_hook
    logger.info("surveillance.wire.ok buffer=%s", type(buffer).__name__)

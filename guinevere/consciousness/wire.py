"""Wire consciousness loop into Hermes agent runtime.

Parent calls this from agent_init.py (appends-only Group G block). We do NOT
edit agent_init.py. Fail-soft: any import/construction failure is logged and
the agent simply lacks the consciousness loop attribute.

Rewritten to the REAL ConsciousnessLoop API (loop.py:63):
  ConsciousnessLoop(llm_router=, settings=)  — NOT (agent, config=…).
  stop via on_session_end(); run() is async.

No new config sections: ConsciousnessConfig already exists in GuinevereConfig
(config/models.py:184). We read it via agent._guinevere_settings.consciousness
with getattr guards and early-return if absent/disabled.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def wire(agent: Any) -> None:
    """Attach a ConsciousnessLoop to the agent and spawn its asyncio task.

    No-op (logged) when settings, the consciousness config section, or the
    feature flag is absent/disabled.
    """
    settings = getattr(agent, "_guinevere_settings", None)
    if settings is None:
        logger.info("consciousness.wire.skipped no guinevere settings")
        return

    consciousness_cfg = getattr(settings, "consciousness", None)
    if consciousness_cfg is None:
        logger.info("consciousness.wire.skipped no consciousness config section")
        return

    if not getattr(consciousness_cfg, "enabled", True):
        logger.info("consciousness.wire.skipped disabled in config")
        return

    # Build the loop against the real API: llm_router + settings. The loop
    # reads its own config from settings.consciousness internally (loop.py:87).
    llm_router = getattr(agent, "_llm_router", None) or getattr(agent, "llm_router", None)
    try:
        from guinevere.consciousness.loop import ConsciousnessLoop

        loop = ConsciousnessLoop(llm_router=llm_router, settings=settings)
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        logger.warning("consciousness.wire.construction_failed %s", exc)
        agent._consciousness_loop = None
        agent._consciousness_task = None
        return

    # Start the session and spawn run() as a background asyncio task.
    try:
        loop.on_session_start()
        task = asyncio.create_task(loop.run(), name="consciousness-loop")
    except RuntimeError as exc:
        # No running event loop in this context — cannot spawn the task.
        logger.warning("consciousness.wire.spawn_failed %s", exc)
        agent._consciousness_loop = loop
        agent._consciousness_task = None
        return

    agent._consciousness_loop = loop
    agent._consciousness_task = task

    # Graceful stop: the agent runtime (or W4 lifespan) calls this on shutdown.
    def _stop_consciousness() -> None:
        try:
            loop.on_session_end()
        except (RuntimeError, AttributeError) as exc:
            logger.warning("consciousness.stop_failed %s", exc)
        if not task.done():
            task.cancel()

    # Attach a named shutdown hook; the agent runtime may consult a list of
    # such hooks. We set it as an attribute (convention from existing wire()s).
    agent._consciousness_stop = _stop_consciousness

    logger.info("consciousness.wire.ok task=%s", task.get_name())

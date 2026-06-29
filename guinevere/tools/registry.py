"""M8 Tool Registry — auto-discovery, registration, and ``wire()``.

The parent owns the agent_init.py append; this module exposes ``wire(agent)``
which the parent will invoke inside a Group D try/except block.

Discovery pattern: instantiates all 9 backends from ``guinevere.tools.backends.*``
and registers them in the singleton ``ToolRegistry``.
"""

from __future__ import annotations

import logging
from typing import Any

from guinevere.tools.tool_backend import ToolBackend, ToolRegistry, discover_backends

logger = logging.getLogger(__name__)


def register_all(registry: ToolRegistry | None = None) -> ToolRegistry:
    """Discover and register all 9 backends in the given (or singleton) registry."""
    reg = registry or ToolRegistry.instance()
    for backend in discover_backends():
        reg.register(backend)
    return reg


def wire(agent: Any) -> None:
    """Fail-soft wire for agent_init.py Group D.

    Attaches ``_tool_registry`` to the agent.  Downstream modules
    (system_prompt.py, executor dispatch, etc.) read this attribute.
    A missing or broken tool module never aborts ``init_agent``.
    """
    try:
        reg = register_all()
        agent._tool_registry = reg
        total_actions = sum(len(b.actions()) for b in reg.backends())
        logger.info(
            "tools.wire ok backends=%d actions=%d",
            len(reg.backends()),
            total_actions,
        )
    except Exception as exc:
        logger.warning("tools.wire failed: %s", exc)
        agent._tool_registry = None

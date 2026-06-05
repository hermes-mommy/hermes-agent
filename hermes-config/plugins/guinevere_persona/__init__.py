"""PersonaPlugin — Dynamic persona state injection for Hermes Agent.

This plugin reads Guinevere's dynamic persona state from Redis DB5
and injects it into the LLM prompt context **without** modifying the
static SOUL.md constitution.

Registration entry point called by Hermes plugin loader.
"""

from __future__ import annotations

from typing import Protocol

import structlog

from src.hermes.plugins.persona_plugin import PersonaPlugin

logger = structlog.get_logger(__name__)


class PluginContext(Protocol):
    """Minimal duck-typed protocol for hermes-agent's PluginContext."""

    def register_hook(self, hook_name: str, callback: object) -> None: ...


def register(ctx: PluginContext) -> None:
    """Register PersonaPlugin hooks with hermes-agent.

    Called by Hermes plugin loader via ``register(ctx)`` when it
    discovers the ``guinevere_persona`` plugin package.

    Registers 4 hooks:
        - ``pre_llm_call``: Inject persona state into prompt.
        - ``post_llm_call``: Observational logging.
        - ``pre_tool_call``: Observational pass-through.
        - ``on_session_start``: Session initialisation logging.
    """
    plugin = PersonaPlugin()

    ctx.register_hook("pre_llm_call", plugin.pre_llm_call)
    ctx.register_hook("post_llm_call", plugin.post_llm_call)
    ctx.register_hook("pre_tool_call", plugin.pre_tool_call)
    ctx.register_hook("on_session_start", plugin.on_session_start)

    logger.info(
        "guinevere_persona_plugin_registered",
        hook_count=4,
        hooks=[
            "pre_llm_call",
            "post_llm_call",
            "pre_tool_call",
            "on_session_start",
        ],
        description="Dynamic persona state injection from Redis DB5",
    )

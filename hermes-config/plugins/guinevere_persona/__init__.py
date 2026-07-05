"""PersonaPlugin — Dynamic persona state injection for Hermes Agent.

This plugin reads Guinevere's dynamic persona state from Redis DB5
and injects it into the LLM prompt context **without** modifying the
static SOUL.md constitution.

Registration entry point called by Hermes plugin loader.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


HookCallback = Callable[..., object | None]


class PersonaPluginRuntime(Protocol):
    """Runtime hook surface exposed by ``guinevere/hermes/plugins/persona_plugin.py``."""

    def pre_llm_call(self, **kwargs: object) -> object | None: ...

    def post_llm_call(self, **kwargs: object) -> object | None: ...

    def pre_tool_call(self, **kwargs: object) -> object | None: ...

    def on_session_start(self, **kwargs: object) -> object | None: ...


def _load_persona_plugin_class() -> type[PersonaPluginRuntime]:
    """Load PersonaPlugin without importing the parent ``src.hermes`` package.

    The project package currently has a pre-existing package-level import caveat
    in ``guinevere/hermes/__init__.py``. Hermes runtime only needs this plugin module,
    so load it directly from the repository path.
    """
    # P24: load from fork p24-port/guinevere/ (not legacy code/guinevere/src/).
    # src/ removed in P24 cleanup; persona_plugin lives in guinevere/hermes/plugins/.
    repo_root = Path(os.environ.get("GUINEVERE_REPO_ROOT", "/home/guinevere/p24-port"))
    plugin_path = repo_root / "guinevere" / "hermes" / "plugins" / "persona_plugin.py"
    spec = importlib.util.spec_from_file_location("guinevere_persona_runtime", plugin_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load PersonaPlugin from {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plugin_class = getattr(module, "PersonaPlugin", None)
    if not isinstance(plugin_class, type):
        raise RuntimeError("PersonaPlugin class not found in runtime module")
    return plugin_class


class PluginContext(Protocol):
    """Minimal duck-typed protocol for hermes-agent's PluginContext."""

    def register_hook(self, hook_name: str, callback: HookCallback) -> None: ...


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
    plugin_class = _load_persona_plugin_class()
    plugin = plugin_class()

    ctx.register_hook("pre_llm_call", plugin.pre_llm_call)
    ctx.register_hook("post_llm_call", plugin.post_llm_call)
    ctx.register_hook("pre_tool_call", plugin.pre_tool_call)
    ctx.register_hook("on_session_start", plugin.on_session_start)

    logger.info(
        "guinevere_persona_plugin_registered %s",
        {
            "hook_count": 4,
            "hooks": [
                "pre_llm_call",
                "post_llm_call",
                "pre_tool_call",
                "on_session_start",
            ],
            "description": "Dynamic persona state injection from Redis DB5",
        },
    )

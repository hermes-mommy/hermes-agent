"""Auth overlay plugin — fail-closed MCP auth enforcement.

This plugin imports Python ``src.mcp.auth_matrix`` as the sole runtime auth
source, normalises Hermes/native/MCP tool names to canonical matrix tool+operation
pairs, enforces all four ``AuthLevel`` values, and persists destructive approval
requests in Redis DB5 with a 5-minute TTL.

Architecture::

    pre_tool_call hook ──► AuthOverlayPlugin.pre_tool_call()
                              │
                              ├─► normalize_tool_name() → (canonical_tool, operation)
                              ├─► get_auth_level(canonical_tool, operation)
                              │
                              ├─► READ_AUTO            → allow (return None)
                              ├─► WRITE_NOTIFY         → NotifyHandler.send() → allow
                              ├─► DESTRUCTIVE_APPROVAL → ApprovalHandler.request() → block
                              │                              └─ Redis DB5, TTL=300
                              └─► FORBIDDEN            → ForbiddenHandler.block()
                                                              → block (return dict)

On any unexpected exception the plugin returns a fail-closed block action.
"""

from __future__ import annotations

from typing import Protocol, cast

import structlog

from .auth_handler import AuthOverlayPlugin


class Logger(Protocol):
    """Subset of structlog logger methods used by this module."""

    def info(self, event: str, **kwargs: object) -> None: ...


logger = cast(Logger, structlog.get_logger(__name__))


class PluginContext(Protocol):
    """Minimal duck-typed protocol for hermes-agent's PluginContext."""

    def register_hook(self, hook_name: str, callback: object) -> None: ...


def register(ctx: PluginContext) -> None:
    """Register the auth overlay plugin's pre_tool_call hook with hermes-agent.

    Called by the Hermes plugin loader via ``register(ctx)``.
    """
    plugin = AuthOverlayPlugin()
    ctx.register_hook("pre_tool_call", plugin.pre_tool_call)
    logger.info("auth_overlay_plugin_registered")

"""Hermes plugin — Memory commands (S3.2).

Commands: /memory-search, /memory-add, /memory-forget, /memory-export.

Migrated from guinevere/discord/cmd_memory_*.py for Phase 2 Discord migration.
Uses HermesMemoryBridge (guinevere/hermes/memory_bridge.py) for all memory operations.
"""

from __future__ import annotations

import logging
from typing import Any

from .memory_search import register as _register_search
from .memory_add import register as _register_add
from .memory_forget import register as _register_forget
from .memory_export import register as _register_export

logger = logging.getLogger(__name__)

__all__ = ["register"]


def register(ctx: Any) -> None:
    """Register all memory commands with the Hermes plugin context."""
    _register_search(ctx)
    _register_add(ctx)
    _register_forget(ctx)
    _register_export(ctx)
    logger.info("commands_memory: 4 commands registered.")
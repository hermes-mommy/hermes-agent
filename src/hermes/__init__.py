"""Hermes Session Adapter — Phase 1.

Handles per-user AIAgent session management with Redis DB4 storage.
All safety guards remain in conversational_handler.py — NEVER inside Hermes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .session_adapter import HermesSessionAdapter
from .memory_bridge import HermesMemoryBridge

if TYPE_CHECKING:
    pass

_adapter_instance: HermesSessionAdapter | None = None


def get_adapter() -> HermesSessionAdapter:
    """Return the shared HermesSessionAdapter singleton.

    Creates lazily on first call. Used by conversational_handler.py,
    slash commands, and any other module that needs Hermes access.

    Returns:
        The shared HermesSessionAdapter instance.
    """
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = HermesSessionAdapter(
            redis_client=None,
            llm_config={
                "base_url": "http://localhost:20128/v1",
                "model": "ds/deepseek-v4-flash",
                "provider": "9router",
                "api_key": "sk-local",
            },
        )
    return _adapter_instance


__all__ = ["HermesSessionAdapter", "HermesMemoryBridge", "get_adapter"]

"""Shared HermesSessionAdapter accessor — moved from ``__init__.py``.

Provides the ``get_adapter()`` singleton factory that was previously
exported from ``guinvere.hermes``.  Importing this module does **not** pull
in deprecated ``session_adapter`` or ``memory_bridge`` at package-init
time; the ``HermesSessionAdapter`` import is deferred to the first
``get_adapter()`` call, preserving the same lazy-init semantics.

The production class lives in ``._session_adapter`` (the non-deprecated
replacement for ``session_adapter.py`` which is slated for archive).

Usage::

    from guinvere.hermes.adapter import get_adapter

    adapter = get_adapter()
    await adapter.send_message(...)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redis.asyncio import Redis

if TYPE_CHECKING:
    from ._session_adapter import HermesSessionAdapter

_adapter_instance: "HermesSessionAdapter | None" = None


def get_adapter() -> "HermesSessionAdapter":
    """Return the shared HermesSessionAdapter singleton.

    Creates lazily on first call. Used by conversational_handler.py,
    slash commands, and any other module that needs Hermes access.

    Returns:
        The shared HermesSessionAdapter instance.
    """
    global _adapter_instance
    if _adapter_instance is None:
        from ._session_adapter import HermesSessionAdapter

        _adapter_instance = HermesSessionAdapter(
            redis_client=Redis(),
            llm_config={
                "base_url": "http://localhost:20128/v1",
                "model": "ds/deepseek-v4-flash",
                "provider": "9router",
                "api_key": "sk-local",
            },
        )
    return _adapter_instance

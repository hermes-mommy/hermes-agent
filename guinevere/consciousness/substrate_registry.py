"""Substrate Registry — maps substrate names to their coroutines.

Replaces ``guinevere/loops/phases/__init__.py`` PHASE_REGISTRY.
The consciousness loop iterates this registry at startup to
spawn one asyncio.Task per substrate.

Substrates are module-level async functions in ``substrates.py``
that accept ``(self: ConsciousnessLoop)``.  This registry binds
the loop instance via ``functools.partial`` so each entry is a
zero-argument awaitable.
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, Callable, Coroutine

if TYPE_CHECKING:
    from guinevere.consciousness.loop import ConsciousnessLoop

from guinevere.consciousness.substrates import (
    substrate_active_cognition,
    substrate_dreaming,
    substrate_emotion_driven,
    substrate_heartbeat,
    substrate_metacognition,
    substrate_reflection,
    substrate_strategic_planning,
)

# Map substrate name → module-level function.
_SUBSTRATE_FUNCTIONS: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {
    "heartbeat": substrate_heartbeat,
    "active_cognition": substrate_active_cognition,
    "reflection": substrate_reflection,
    "strategic_planning": substrate_strategic_planning,
    "dreaming": substrate_dreaming,
    "metacognition": substrate_metacognition,
    "emotion_driven": substrate_emotion_driven,
}

# Substrate name → bound-method reference (set at loop construction time).
# The registry is populated by build_registry().
SUBSTRATE_REGISTRY: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}


def build_registry(loop: ConsciousnessLoop) -> dict[str, Callable[..., Coroutine[Any, Any, None]]]:
    """Build the substrate registry from a ConsciousnessLoop instance.

    Returns a dict of name → zero-arg async callable (bound via partial).
    Also stores it globally in SUBSTRATE_REGISTRY for introspection.
    """
    registry: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}
    for name, fn in _SUBSTRATE_FUNCTIONS.items():
        # functools.partial binds the loop instance as the first arg.
        registry[name] = functools.partial(fn, loop)

    SUBSTRATE_REGISTRY.clear()
    SUBSTRATE_REGISTRY.update(registry)
    return registry

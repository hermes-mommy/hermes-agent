"""Hermes plugins package — Guinevere runtime plugin bridge.

This package contains Hermes-agent plugins that extend the core
agent loop with Guinevere-specific behavior:

- ``persona_plugin``: Dynamic persona state injection via Redis DB5.
  Injects mood, yandere level, punishment state, and last interaction
  timestamp into the pre-LLM prompt without modifying SOUL.md.

All plugins follow the Hermes v0.15.2 ``register(ctx)`` pattern
and degrade gracefully when dependencies are unavailable.
"""

from __future__ import annotations

__all__: list[str] = []

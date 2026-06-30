"""Hermes Session Adapter — Phase 1.

Handles per-user AIAgent session management with Redis DB4 storage.
All safety guards remain in conversational_handler.py — NEVER inside Hermes.

.. deprecated::
    The ``get_adapter()`` accessor has been moved to
    ``src.hermes.adapter``.  Import directly::

        from guinvere.hermes.adapter import get_adapter

This package no longer imports ``session_adapter`` or ``memory_bridge``
at init time.
"""

from __future__ import annotations

"""Hermes plugin — Loop commands (S3.3).

Commands: /loop-start, /loop-stop, /loop-pause, /loop-resume,
         /loops, /loop-priority, /evidence.

Migrated from guinevere/discord/cmd_loop_*.py for Phase 2 Discord migration.
Preserves loop orchestrator API calls (localhost:8000), state transitions,
and priority queue operations.
"""

from __future__ import annotations

import logging
from typing import Any

from .loop_start import register as _register_start
from .loop_stop import register as _register_stop
from .loop_pause import register as _register_pause
from .loop_resume import register as _register_resume
from .loops import register as _register_loops
from .loop_priority import register as _register_priority
from .evidence import register as _register_evidence

logger = logging.getLogger(__name__)

__all__ = ["register"]


def register(ctx: Any) -> None:
    """Register all loop commands with the Hermes plugin context."""
    _register_start(ctx)
    _register_stop(ctx)
    _register_pause(ctx)
    _register_resume(ctx)
    _register_loops(ctx)
    _register_priority(ctx)
    _register_evidence(ctx)
    logger.info("commands_loop: 7 commands registered.")
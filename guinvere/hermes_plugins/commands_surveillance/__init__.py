"""Hermes plugin — Surveillance commands (S3.4).

Commands: /surveillance-status, /surveillance-pause, /surveillance-resume,
         /clear-cache.

Migrated from src/discord/cmd_surveillance_*.py for Phase 2 Discord migration.
Preserves consent-bound surveillance operations: consent check before any
data access, no raw surveillance data in logs, audit trail for state changes.
"""

from __future__ import annotations

import logging
from typing import Any

from .surveillance_status import register as _register_status
from .surveillance_pause import register as _register_pause
from .surveillance_resume import register as _register_resume
from .clear_cache import register as _register_clear_cache

logger = logging.getLogger(__name__)

__all__ = ["register"]


def register(ctx: Any) -> None:
    """Register all surveillance commands with the Hermes plugin context."""
    _register_status(ctx)
    _register_pause(ctx)
    _register_resume(ctx)
    _register_clear_cache(ctx)
    logger.info("commands_surveillance: 4 commands registered.")
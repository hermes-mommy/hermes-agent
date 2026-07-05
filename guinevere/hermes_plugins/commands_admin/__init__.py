"""Hermes plugin — commands_admin. Admin command group (S3.7).

Provides /restart-service, /backup-now, /health-check commands for
system-level operations routed through the DESTRUCTIVE_APPROVAL auth gate.
"""

from __future__ import annotations

__all__: list[str] = []
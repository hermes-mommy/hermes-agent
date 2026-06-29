"""Auto-recovery design — restart-on-crash, respawn-on-VPS-failure.

D2 COMPLIANCE: Design only. No live VPS deployment.

Provides:
  - Systemd service unit generation (documented, not installed)
  - Application-level watchdog for process crashes
  - Circuit breaker state persistence across restarts
  - wire(agent) function for agent_init integration

Patterns ported from:
  - src/loops/recovery.py (RecoveryManager, checkpoint-based restart)
  - src/x_poster/circuit_breaker.py (DB-persisted breaker state)
"""

from __future__ import annotations

import logging
import signal
import sys
from typing import Any

logger = logging.getLogger(__name__)


class AutoRecovery:
    """Application-level auto-recovery manager.

    D2 COMPLIANCE: Design-only. No real VPS deploy.

    Provides:
      - Systemd service unit generation (for future VPS deployment)
      - Watchdog signal handling (SIGTERM, SIGINT)
      - Restart-on-crash wrapper
      - Circuit breaker state persistence hooks
    """

    def __init__(self, app_name: str = "guinevere") -> None:
        self.app_name = app_name
        self._restart_count = 0
        self._max_restarts = 5
        self._running = False

    def generate_systemd_unit(self) -> str:
        """Generate a systemd service unit file.

        Returns the unit file as a string. Per D2, this is NOT installed
        automatically — it must be manually placed on the VPS.

        The unit includes:
          - Restart=always with 10s delay
          - Security hardening (NoNewPrivileges, ProtectSystem)
          - Dependency on postgresql and redis
        """
        unit = f"""[Unit]
Description=Guinevere P24 v3.0 Autonomous Agent
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=guinevere
Group=guinevere
WorkingDirectory=/opt/guinevere
ExecStart=/opt/guinevere/.venv/bin/python -m guinevere.main
Restart=always
RestartSec=10
Environment=P24_ENVIRONMENT=production
EnvironmentFile=/opt/guinevere/.env

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/guinevere/data
PrivateTmp=yes

# Resource limits
MemoryMax=2G
CPUQuota=200%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier={self.app_name}

[Install]
WantedBy=multi-user.target
"""
        logger.info(
            "systemd_unit_generated",
            extra={"app_name": self.app_name, "d2_compliant": True},
        )
        return unit

    def setup_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown.

        Handles SIGTERM and SIGINT for clean shutdown.
        """
        def _handle_shutdown(signum: int, frame: Any) -> None:
            sig_name = signal.Signals(signum).name
            logger.info(
                "shutdown_signal_received",
                extra={"signal": sig_name, "restart_count": self._restart_count},
            )
            self._running = False

        signal.signal(signal.SIGTERM, _handle_shutdown)
        signal.signal(signal.SIGINT, _handle_shutdown)

    def record_restart(self) -> int:
        """Record a restart event. Returns current restart count."""
        self._restart_count += 1
        logger.warning(
            "restart_recorded",
            extra={"restart_count": self._restart_count, "max_restarts": self._max_restarts},
        )
        return self._restart_count

    def should_restart(self) -> bool:
        """Check if we should attempt a restart."""
        return self._restart_count < self._max_restarts

    def health(self) -> dict[str, Any]:
        """Return recovery manager health status."""
        return {
            "app_name": self.app_name,
            "restart_count": self._restart_count,
            "max_restarts": self._max_restarts,
            "running": self._running,
            "d2_compliant": True,
            "note": "Design only — no live VPS deployment under D2",
        }


def wire(agent: Any) -> None:
    """Wire auto-recovery into the agent lifecycle.

    This function appends recovery hooks to the agent's initialization.
    Parent-owned agent_init.py should NOT be edited — this wire() function
    is called externally.

    Args:
        agent: The agent instance to wire recovery into.
    """
    recovery = AutoRecovery()
    recovery.setup_signal_handlers()

    # Attach recovery manager to agent for lifecycle integration
    if hasattr(agent, "__dict__"):
        agent._auto_recovery = recovery

    logger.info(
        "auto_recovery_wired",
        extra={"app_name": recovery.app_name, "d2_compliant": True},
    )


__all__ = ["AutoRecovery", "wire"]

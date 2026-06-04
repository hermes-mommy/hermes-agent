"""Hermes command plugin — /health-check. Run Guinevere service health checks.

Probes the Hermes health endpoint (``http://localhost:8000/health/detailed``)
and formats component statuses as a markdown report with pass/fail indicators.

Checks include:
    - Hermes Agent health
    - PostgreSQL connectivity
    - Redis (DB0-DB5) connectivity
    - 9Router reachability

Usage:
    /health-check
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

HEALTH_URL: str = "http://localhost:8000/health/detailed"
TIMEOUT_S: float = 10.0


async def _fetch_health() -> dict[str, Any] | None:
    """Fetch detailed health from the Hermes API.

    Returns:
        Parsed JSON dict or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            response = await client.get(HEALTH_URL)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        logger.error("health_check_fetch_failed", extra={"error": str(exc)})
        return None


def _status_emoji(status: str) -> str:
    """Return ✅ for healthy/ok/up, ❌ otherwise."""
    return "✅" if status in ("healthy", "ok", "up", "True") else "❌"


def _build_report(health: dict[str, Any] | None) -> str:
    """Build markdown health report from API response."""
    if health is None:
        return (
            "# ❌ Health Check Unavailable\n\n"
            "API tidak bisa dijangkau, Darling.\n\n"
            "---\n\n"
            "| Component | Status |\n|---|---|\n"
            "| ❌ API | Unreachable |\n\n"
            "---\n\n"
            "🏥 Health • Guinevere de Baroque\n"
        )

    components = health.get("components", health.get("checks", {}))
    overall = str(health.get("status", "unknown"))
    overall_emoji = "✅" if overall in ("healthy", "ok") else "❌"

    lines: list[str] = [
        "# 🏥 Health Check",
        "",
        "Status kesehatan sistem Guinevere.",
        "",
        "---",
        "",
        "| Component | Status |",
        "|---|---|",
        f"| Overall | {overall_emoji} {overall} |",
    ]

    if isinstance(components, dict):
        for name, status in sorted(components.items()):
            if isinstance(status, dict):
                comp_status = str(status.get("status", "unknown"))
            else:
                comp_status = str(status)
            emoji = _status_emoji(comp_status)
            lines.append(f"| {name} | {emoji} {comp_status} |")

    elif isinstance(components, list):
        for item in components:
            if isinstance(item, dict):
                name = str(item.get("name", "unknown"))
                comp_status = str(item.get("status", "unknown"))
                emoji = _status_emoji(comp_status)
                lines.append(f"| {name} | {emoji} {comp_status} |")

    lines.extend([
        "",
        "---",
        "🏥 Health • Guinevere de Baroque",
    ])

    return "\n".join(lines)


def register(ctx: Any) -> None:
    """Register the /health-check command with Hermes."""

    @ctx.register_command(
        "health-check", description="Run Guinevere service health checks."
    )
    async def handle(context: Any) -> str:
        try:
            health = await _fetch_health()
            return _build_report(health)
        except Exception:
            logger.exception("health_check_command_failed")
            return "⚠️ Health check is temporarily unavailable."


__all__ = ["register"]
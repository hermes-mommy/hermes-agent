"""Hermes command plugin — /cost-alert. Show or update cost alert threshold.

View or set the cost alert threshold stored in Redis DB5.
When current month spend exceeds the threshold, cost alert fires.

Usage:
    /cost-alert [action: view|set] [threshold: float]  # default: view
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import redis

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))
VALID_ACTIONS: frozenset[str] = frozenset({"view", "set"})
DEFAULT_ACTION: str = "view"
DEFAULT_THRESHOLD: float = 10.0

REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6380
REDIS_DB: int = 5
REDIS_KEY: str = "cost:alert_threshold"


def _redis() -> redis.Redis:
    """Return a Redis client for DB5."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


def _safe_float(raw: object) -> float:
    """Convert a Redis value to float, returning 0.0 on failure."""
    if raw is None:
        return 0.0
    try:
        return float(str(raw))
    except (ValueError, TypeError):
        return 0.0


def _format_wib(dt: datetime) -> str:
    """Format datetime as WIB timestamp string."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def _get_threshold(r: redis.Redis) -> float:
    """Read current alert threshold from Redis."""
    raw = r.get(REDIS_KEY)
    if raw is None:
        return DEFAULT_THRESHOLD
    try:
        return float(str(raw))
    except (ValueError, TypeError):
        return DEFAULT_THRESHOLD


def _get_current_spend(r: redis.Redis) -> float:
    """Read current month spend from Redis."""
    return _safe_float(r.get("cost:current_month"))


def build_view_report(threshold: float, current_spend: float) -> str:
    """Build a markdown report showing current alert threshold status."""
    now = datetime.now(tz=timezone.utc)
    ts_str = _format_wib(now)
    ratio = (current_spend / threshold * 100) if threshold > 0 else 0.0

    lines: list[str] = [
        "# 🚨 Cost Alert Threshold",
        "",
        "Ini threshold alert kita, Darling.",
        "",
        "---",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| 💰 Threshold | ${threshold:.2f} |",
        f"| 💵 Current Spend | ${current_spend:.4f} |",
        f"| 📊 Usage | {ratio:.1f}% |",
        "",
        "---",
        f"Guinevere de Baroque • {ts_str} • 💰 FinOps",
    ]

    return "\n".join(lines)


def build_set_report(new_threshold: float, current_spend: float) -> str:
    """Build a markdown confirmation report after setting a new threshold."""
    now = datetime.now(tz=timezone.utc)
    ts_str = _format_wib(now)

    lines: list[str] = [
        "# ✅ Cost Alert Updated",
        "",
        "Alert threshold sudah diupdate, Darling.",
        "",
        "---",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| 💰 New Threshold | ${new_threshold:.2f} |",
        f"| 💵 Current Spend | ${current_spend:.4f} |",
        "",
        "---",
        f"Guinevere de Baroque • {ts_str} • 💰 FinOps",
    ]

    return "\n".join(lines)


def register(ctx: Any) -> None:
    """Register the /cost-alert command with Hermes."""

    @ctx.register_command(
        "cost-alert", description="Show or update Guinevere cost alert thresholds."
    )
    async def handle(context: Any) -> str:
        try:
            args: list[str] = getattr(context, "args", [])
            action = args[0] if args and args[0] in VALID_ACTIONS else DEFAULT_ACTION

            r = _redis()

            if action == "set":
                if len(args) < 2:
                    return "⚠️ Parameter `threshold` diperlukan untuk action `set`."

                try:
                    threshold = float(args[1])
                except (ValueError, TypeError):
                    return "⚠️ Threshold harus berupa angka, Darling."

                if threshold <= 0:
                    return "⚠️ Threshold harus lebih besar dari 0."

                r.set(REDIS_KEY, str(threshold))
                logger.info("cost_alert_threshold_set", extra={"threshold": threshold})
                current = _get_current_spend(r)
                return build_set_report(threshold, current)

            threshold = _get_threshold(r)
            current = _get_current_spend(r)
            return build_view_report(threshold, current)

        except Exception:
            logger.exception("cost_alert_command_failed")
            return "⚠️ Cost alert is temporarily unavailable."


__all__ = ["register"]